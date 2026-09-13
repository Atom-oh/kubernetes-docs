# Inference Frameworks for LLM Serving

> **Last Updated**: September 12, 2026
> **Scope**: Official releases, APIs, charts and local checks; no GPU/Neuron model execution.

Select inference engines, distributed execution layers, Kubernetes controllers and provider gateways separately. “OpenAI-compatible” does not mean identical endpoints, fields, streaming, tool calls or authentication.

## Inference Framework Landscape

![The distinct roles of inference engines, distributed serving, Kubernetes operations and provider gateways.](../.gitbook/assets/en-ai-ml-04-inference-frameworks-0.png)

[View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-04-inference-frameworks-0.html)

| Component | Inspected baseline | Selection checks |
| --- | --- | --- |
| NIM LLM/VLM | 2.0.12 documentation; separate 3.0 offering | Model, profile, hardware, support agreement and backend |
| Dynamo | 1.4.2 | Aggregated/disaggregated serving, KV transfer, planner and controller |
| AIBrix | 0.7.0 | Envoy Gateway, adapter/controller and autoscaling |
| SGLang | 0.5.19 | Model, grammar backend, device and measured workload |
| vLLM / Ray Serve | vLLM 0.29.0 / Ray 2.58.0 / KubeRay 1.7.0 | Individually validated image/model/controller combinations |
| TGI | 3.3.7; maintenance mode | Existing-system maintenance and migration planning |
| Ollama | 0.34.0 | Local API access, model storage and preparation |
| LiteLLM | 1.100.1 | Provider adaptation, authentication, fallback and cost instrumentation |
| Neuron | SDK 2.32.0; Helm 1.10.0 | Instance-specific plugin/compiler/driver compatibility |

Avoid a universal yes/no feature matrix. Dynamo planning and vLLM/SGLang disaggregation, CPU and GGUF support depend on release, backend and hardware. Adapter loading and model aliases are not tenant authentication boundaries.

## NVIDIA NIM

Check container, model profile, GPU compatibility and support agreement together. NIM Operator 3.1.2 is separate from the LLM/VLM 2.0.12 containers. The inspected 2.0.12 release documents vLLM 0.27.1; NIM does not always use TensorRT-LLM. Do not treat the Dynamo-based 3.0 offering as the same deployment path as 2.0.

![An approved entry path serves NIM requests, with prepared model caching and separate metrics collection.](../.gitbook/assets/en-ai-ml-04-inference-frameworks-1.png)

[View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-04-inference-frameworks-1.html)

### Deployment Preparation and Profiles

Use the [GPU guide](01-ai-ml-workloads.md) for AMI, driver/toolkit and device-plugin requirements. Always enabling driver installation can conflict with a provider AMI. Check Karpenter NodePool/EC2NodeClass, actual schedulable CPU/RAM/GPU resources and device counts. An eight-GPU Pod cannot fit a one/four-GPU node, and Custom AMIs need explicit EKS bootstrap configuration.

Use NIM_MODEL_PROFILE with a supported profile ID/name from the container's profile list. Do not assume the old NIM_MANIFEST_PROFILE or invented vllm-bf16-tp8 string is valid. Record image digest, model revision, profile, drivers and actual verification together.

NGC image-pull and runtime model-download credentials serve different roles. The documented NGC_API_KEY environment path does not satisfy a file-only credential policy. Use an approved prepared-model path or a verified credential adapter; never put actual keys in shell arguments or source. An internal Service alone does not authenticate inference requests.

Avoid sharing one EBS RWO PVC between replicas on different nodes. Choose per-replica storage/local caches or an appropriate shared filesystem, and test download failure, storage performance, startup probes and rollout. Models are not universally embedded in images, and caches do not automatically synchronize with FSx/S3.

### Metrics and GenAI-Perf

The inspected NIM 2.0.12 documentation exposes `/v1/metrics`, passing through native vLLM backend metrics. Inspect actual names, units and labels instead of copying invented nim_* names or `/metrics`. A Grafana ConfigMap needs the corresponding datasource/sidecar and Prometheus scraping. Do not display seconds unchanged in a millisecond panel.

Define workload-specific SLOs for TTFT, ITL, end-to-end latency, successful throughput and queueing. With uniform token intervals, the approximation is `TTFT + (output tokens - 1) × ITL`, plus separate network/postprocessing overhead. Targets such as 500ms or GPU80% are not universal health standards.

GenAI-Perf 0.0.16 uses the profile subcommand and synthetic-input-tokens-mean/output-tokens-mean options. The following command would load a prepared internal endpoint and was not executed in this audit. Prepare perf_analyzer, tokenizer and other distribution dependencies first.

```bash
genai-perf profile   --endpoint-type chat   --service-kind openai   --url http://127.0.0.1:8000   --model approved-model-alias   --concurrency 2   --synthetic-input-tokens-mean 128   --output-tokens-mean 64   --num-prompts 20   --profile-export-file profile_export.json
```

Do not assume analyze is only JSON postprocessing: sweep settings can perform additional profiling. Keep raw requests, failures, tokenizer, warmup, concurrency and model/backend revisions. GPU utilization needs actual metrics collection.

## NVIDIA Dynamo

The official 1.4.2 Kubernetes path uses the Dynamo platform, DynamoGraphDeployment (DGD) and DynamoGraphDeploymentRequest (DGDR). It is not implemented by the former invented dynamo-router/dynamo-worker images, KV_CACHE_HOST and arbitrary router YAML. A DGDR requests profiling and DGD creation; it is not a read-only inspection.

![Dynamo frontend, configured workers and KV transfer, with controller/planner managing deployment and capacity.](../.gitbook/assets/en-ai-ml-04-inference-frameworks-2.png)

[View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-04-inference-frameworks-2.html)

### Actual DGD Structure

This **schema-checked configuration** adapts the official 1.4.2 v1beta1 aggregated example for a public model and bounded execution settings. It requires the platform/controller, namespace, GPU, model access and networking. Pin model/image digests and verify actual hardware before deployment; no model was executed in this audit.

```yaml
apiVersion: nvidia.com/v1beta1
kind: DynamoGraphDeployment
metadata:
  name: vllm-agg
  namespace: dynamo-system
spec:
  components:
  - name: Frontend
    podTemplate:
      spec:
        containers:
        - image: nvcr.io/nvidia/ai-dynamo/vllm-runtime:1.4.2
          name: main
          resources:
            requests:
              cpu: 250m
              memory: 512Mi
            limits:
              cpu: '1'
              memory: 2Gi
    replicas: 1
    type: frontend
  - name: VllmDecodeWorker
    podTemplate:
      spec:
        containers:
        - args:
          - --model
          - Qwen/Qwen3-0.6B
          - --max-model-len
          - '2048'
          - --max-num-seqs
          - '8'
          command:
          - python3
          - -m
          - dynamo.vllm
          image: nvcr.io/nvidia/ai-dynamo/vllm-runtime:1.4.2
          name: main
          resources:
            limits:
              nvidia.com/gpu: '1'
              cpu: '4'
              memory: 12Gi
            requests:
              ephemeral-storage: 2Gi
              cpu: '2'
              memory: 4Gi
          workingDir: /workspace/examples/backends/vllm
    replicas: 1
    type: worker
```

Disaggregation requires compatible prefill/decode roles, KV connectors/formats, model revisions and networking. Arbitrary mixtures of backends or GPUs are not automatically interoperable. KV-aware routing balances locality and load; a fixed0.7/0.3 formula is not a universal implementation. Redis is not the mandatory KV tensor store for all Dynamo deployments.

The inspected platform chart's cluster-wide operator manages CRDs through a crd-apply init container. upgradeCRD=false selects external management; it does not remove the CRD requirement. Check planner, discovery, NATS/etcd, Grove/KAI and other release-specific settings. Chart rendering does not verify CRD application, authorization or live discovery.

## AIBrix

Version0.7.0 uses Envoy Gateway, a gateway plugin, controller-manager and metadata services. KubeRay is optional for Ray-based capabilities. The former standalone aibrix-registry server and /v1/lora/register API are not the inspected0.7.0 installation path.

### ModelAdapter and PodAutoscaler

Actual ModelAdapter fields include baseModel, podSelector and artifactURL. Omitting replicas loads the adapter on all matching Pods;1 selects one Pod; other values are rejected. Replace the example bucket/revision and base model with approved values. Verify controller download permissions, runtime compatibility, adapter capacity/lifecycle and tenant authorization separately.

```yaml
apiVersion: model.aibrix.ai/v1alpha1
kind: ModelAdapter
metadata:
  name: support-lora
  namespace: ai-inference
spec:
  baseModel: approved-base-model
  podSelector:
    matchLabels:
      model.aibrix.ai/name: approved-base-model
  artifactURL: s3://REPLACE_WITH_APPROVED_BUCKET/adapters/support/REVISION/
  replicas: 1
```

PodAutoscaler0.7.0 uses metricsSources and HPA/KPA/APA strategies, not an arbitrary autoscaler ConfigMap. This CPU example requires metrics-server, workload CPU requests and the controller. It does not validate GPU queue-based scaling. Avoid competing scaler owners for the same target.

```yaml
apiVersion: autoscaling.aibrix.ai/v1alpha1
kind: PodAutoscaler
metadata:
  name: model-cpu
  namespace: ai-inference
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: prepared-model-server
  minReplicas: 1
  maxReplicas: 3
  scalingStrategy: HPA
  metricsSources:
  - metricSourceType: resource
    targetMetric: cpu
    targetValue: '70'
```

## Ray Serve Integration

Use the audited [Ray Serve](ray/04-ray-serve.md) and [KubeRay](ray/02-kuberay-operator.md) APIs. KubeRay reconciliation, Ray worker autoscaling and Serve replica autoscaling have different roles. Do not use RayCluster as a normal Deployment HPA scale target or guess generated cluster/Serve Service names and selectors.

Code and dependencies must reach execution workers, not just the head. user_config does not automatically change constructor arguments; implement the appropriate reconfigure path. A compatible API needs the actual chat template, streaming, cancellation, finish reasons, usage and errors. Concatenating role strings and ignoring stream=true is insufficient. The old Ray2.9/operator1.1 examples and unconditional trust_remote_code=True were removed.

## SGLang

Version0.5.19 RadixAttention reuses KV for common prefixes; arbitrary overlapping middle substrings are not interchangeable cached prefixes. Model, KV format and access policies must match. Current grammar backends include default XGrammar and alternatives Outlines/Llguidance. “Always10x faster because of compressed FSM” is not a general conclusion.

![SGLang APIs/runtime, common-prefix KV caching and the selected grammar backend.](../.gitbook/assets/en-ai-ml-04-inference-frameworks-3.png)

[View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-04-inference-frameworks-3.html)

### Structured Request Example

This client assumes an approved gateway supporting SGLang's json_schema request shape. It checks normal completion and output shape. Validation uses a local HTTP fixture with synthetic responses and failure cases; it does not measure model accuracy. JSON validity does not establish factual correctness or tool authorization.

```python
from pathlib import Path
import json
from urllib.request import Request, urlopen

# Existing private gateway and a scoped credential mounted as a file.
base_url = "https://inference.example.internal/v1"
credential = Path("/run/secrets/inference/token").read_text().strip()
payload = {
    "model": "approved-model-alias",
    "messages": [{"role": "user", "content": "Return the city Seoul and country Korea."}],
    "temperature": 0,
    "max_tokens": 128,
    "response_format": {
        "type": "json_schema",
        "json_schema": {
            "name": "location",
            "schema": {
                "type": "object",
                "properties": {"city": {"type": "string"}, "country": {"type": "string"}},
                "required": ["city", "country"],
                "additionalProperties": False,
            },
        },
    },
}
request = Request(
    base_url + "/chat/completions",
    data=json.dumps(payload).encode(),
    headers={"Content-Type": "application/json", "Authorization": "Bearer " + credential},
    method="POST",
)
with urlopen(request, timeout=30) as response:
    result = json.load(response)
choice = result["choices"][0]
if choice["finish_reason"] != "stop":
    raise RuntimeError("Generation did not complete normally")
location = json.loads(choice["message"]["content"])
if set(location) != {"city", "country"} or not all(isinstance(v, str) for v in location.values()):
    raise ValueError("Unexpected output shape")
print(location)
```

SGLang's function/system/user/assistant/gen DSL APIs remain in this release. Declaring a function does not run inference: connect a prepared RuntimeEndpoint/backend and execute it. Verify Torch, FlashInfer and hardware compatibility during installation. This audit did not install the full GPU SDK or connect the DSL to a model.

## Hugging Face TGI

The official repository declares **maintenance mode**; the latest inspected release is3.3.7(December19,2025). It accepts minor fixes, documentation and maintenance and directs new engine adoption toward vLLM/SGLang and others. It is no longer a generic default recommendation for a new project. Validate model, template, streaming, metrics and SLO compatibility when migrating existing deployments.

Adding --quantize=awq does not automatically produce AWQ weights from an ordinary model. Use a supported model prepared in that format. Floating tags, missing gated-model credentials and short liveness deadlines undermine reproducibility and successful startup.

## Ollama

In0.34.0, pulling a model and serving it are separate operations. A postStart hook with sleep10 does not ensure readiness. Prestage approved models or use a separate preparation procedure with health checks, bounded retries and failure handling. Record mutable model tags and storage permissions.

The local Ollama API does not provide user authentication; put authorization and path controls in front before exposing it. A server bound only to Pod localhost cannot be reached through its Service. OLLAMA_HOST changes the listening scope, not authentication. Scope model-management and inference endpoints separately.

A Modelfile defines the base model, system prompt and generation settings; it does not train a model or build a Kubernetes image. Verify CPU/GPU support per model size, device and backend instead of assuming large-scale multitenancy.

## LiteLLM

Use the audited1.100.1 Router configuration in the [Agentic AI guide](03-agentic-ai-platform.md). A provider gateway is a different layer from an inference engine. Calling an alias gpt-4-equivalent does not establish equivalent quality. Fallback must first satisfy allowed-provider and data-egress policies.

Wire the actual configuration file into the proxy command and configure client credentials, DB/Redis and callbacks as needed. A dummy key or ClusterIP is not authentication; drop_params=true can remove meaningful request conditions. Distinguish requests, success, failure, retries and cache costs.

## AWS Neuron and Inferentia2

Distinguish chips, NeuronCores and host RAM/HBM. Each Inferentia2 chip has two NeuronCore-v2 cores and32GiB HBM.

| Instance | Chips | NeuronCores-v2 | Device HBM (GiB) | Host RAM (GiB) | vCPU |
| --- | --- | --- | --- | --- | --- |
| inf2.xlarge | 1 | 2 | 32 | 16 | 4 |
| inf2.8xlarge | 1 | 2 | 32 | 128 | 32 |
| inf2.24xlarge | 6 | 12 | 192 | 384 | 96 |
| inf2.48xlarge | 12 | 24 | 384 | 768 | 192 |

### Device Allocation and Plugin Paths

aws.amazon.com/neuron allocates **whole devices**; aws.amazon.com/neuroncore allocates **cores**. The former inf2.xlarge example requested neuron:2, eight CPUs and24Gi RAM on a node with one device, four vCPUs and16Gi RAM; it cannot schedule. NEURON_RT_VISIBLE_CORES selects runtime scope and does not create unallocated devices. Check precedence with NUM_CORES and logical-core policy against the chosen release.

The inspected official Helm1.10.0 includes device-plugin, scheduler and node-problem-detector options. Inspect rendered DaemonSets, hostPaths, RBAC and recovery behavior before installation. This command only generates local output.

```bash
helm template neuron-audit oci://public.ecr.aws/neuron/neuron-helm-chart   --version 1.10.0 --namespace kube-system --include-crds > neuron-rendered.yaml
```

SDK2.32.0 documents two separate paths: **NxD Inference plugin0.5.x with vLLM0.16 for Inf2/Trn1/Trn2**, and the **new vLLM Neuron beta0.24.0.1.1.0 for Trn2/Trn3 only**. The detailed NxD guide still shows0.5.0/SDK2.29 while the overview shows0.5.3; verify the chosen plugin tag, DLC and exact dependencies. Installing the newest beta on Inf2 or adding pip install to an old2.18 DLC is not compatibility validation.

Neuron compilation requires supported model implementations, shape/batch/sequence buckets, TP, compiler/SDK, hardware and cache artifacts. Calling torch_neuronx.trace on a generic Transformers model with an unused tp_degree dictionary does not implement distributed causal-LM serving. Compiler output files and tokenizer directories are different artifacts. No compiler or Neuron instance was executed in this audit.

## Performance, Cost and Operations

The unsourced A100 ranking table and fixed40–70% savings claims were removed. Compare the same model/revision/precision, input/output-token distribution, concurrency, success rate, SLO, warmup and dated prices. One million requests/day over30days is30million requests: a hypothetical monthly48,000 dollars is1.60 dollars per1,000 requests. The previous0.80 figure was arithmetically wrong; this illustration is not current AWS pricing.

Regress actual payloads, templates, streaming, usage and failure behavior when changing engines. Distinguish sharded model groups from independent replicas, and check whether StatefulSet ordered readiness blocks mutually waiting workers. StatefulSet alone does not configure TP/PP, rendezvous or NCCL.

Compare local caches, EBS, EFS and FSx using model size, restart/download concurrency, authorization and cost. EFS is not universally slower than FSx, and historical gp3 limits are not current guarantees. Refer to the [GPU/storage examples](01-ai-ml-workloads.md).

Before operations, test authentication, TLS, management paths, probes, placement, quotas, a single scaler owner, metrics units, pinned model revisions, cache lifecycle, rollout/rollback and interruption recovery in the actual environment.

## Verification Scope

Checks cover official charts/CRDs, actual SDK/CLI source, local HTTP request/failure fixtures, Markdown and images. No GPU/Neuron model execution, throughput/cost measurements, cloud deployment or model download was performed. Schema/chart success does not establish admission, authorization, model compatibility or production readiness.

## References

- [NIM 2.0 release notes](https://docs.nvidia.com/nim/large-language-models/2.0.12/about-nim-llm/release-notes.html)
- [NIM configuration](https://docs.nvidia.com/nim/large-language-models/2.0.12/reference/environment-variables.html)
- [NIM observability](https://docs.nvidia.com/nim/large-language-models/2.0.12/reference/logging-and-observability.html)
- [Dynamo 1.4.2](https://github.com/ai-dynamo/dynamo/tree/v1.4.2)
- [AIBrix 0.7.0](https://github.com/aibrix/aibrix/tree/v0.7.0)
- [SGLang 0.5.19 structured output](https://github.com/sgl-project/sglang/blob/v0.5.19/docs/docs/advanced_features/structured_outputs.mdx)
- [TGI maintenance notice](https://github.com/huggingface/text-generation-inference)
- [Ollama 0.34.0](https://github.com/ollama/ollama/tree/v0.34.0)
- [GenAI-Perf 0.0.16](https://pypi.org/project/genai-perf/0.0.16/)
- [Neuron SDK 2.32.0 inference paths](https://github.com/aws-neuron/aws-neuron-sdk/blob/v2.32.0/libraries/vllm-neuron/neuron-inference-overview.rst)
- [Inf2 architecture](https://awsdocs-neuron.readthedocs-hosted.com/en/latest/about-neuron/arch/neuron-hardware/inf2-arch.html)
- [Neuron Kubernetes components](https://github.com/aws-neuron/neuron-helm-charts)

## Quiz

[Inference Frameworks Quiz](../quizzes/ai-ml/04-inference-frameworks-quiz.md)
