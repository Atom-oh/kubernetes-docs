# Inference Frameworks Quiz

15questions on current APIs and execution boundaries.

## 1. What does NIM provide, and what must be verified?

<details>
<summary>Answer and explanation</summary>

Model/device-oriented containers and profiles. NIM is not always TensorRT-LLM; verify container/model revisions, supported devices, support agreement, authentication, cache and metrics.
</details>

## 2. What is Dynamo disaggregated serving?

<details>
<summary>Answer and explanation</summary>

Separate prefill and decode workers connected by compatible KV transfer. Model, KV format, backend, device and networking must agree; speed or cost improvements are workload-dependent.
</details>

## 3. How is a LoRA adapter declared in AIBrix0.7.0?

<details>
<summary>Answer and explanation</summary>

Use ModelAdapter with baseModel, podSelector and artifactURL. Omitted replicas means all matching Pods;1 means one Pod; other values are unsupported. Adapter names do not authenticate tenants.
</details>

## 4. Which controller and scaling layers operate Ray Serve on Kubernetes?

<details>
<summary>Answer and explanation</summary>

KubeRay reconciles Ray resources; Ray autoscaling adjusts workers and Serve autoscaling adjusts serving replicas. Do not treat RayCluster as an ordinary Deployment HPA target.
</details>

## 5. How should Inf2 cost and hardware be evaluated?

<details>
<summary>Answer and explanation</summary>

Measure the same model, SLO, successful throughput and dated prices. Each chip has2cores/32GiB HBM. inf2.24xlarge has6chips/12cores/192GiB HBM;48xlarge has12/24/384GiB. Host RAM is separate.
</details>

## 6. How do TTFT, ITL and end-to-end latency differ?

<details>
<summary>Answer and explanation</summary>

TTFT measures time to first token; ITL measures subsequent token intervals. Uniform-interval approximation is TTFT+(output tokens-1)×ITL plus separate overhead. Use workload-specific SLOs and actual units.
</details>

## 7. What does Dynamo KV-aware routing consider?

<details>
<summary>Answer and explanation</summary>

Cache locality and worker load. A fixed0.7/0.3 formula or decode-only cache assumption is not universal; inspect the actual backend and routing policy.
</details>

## 8. What should be checked before installing the Neuron device plugin?

<details>
<summary>Answer and explanation</summary>

Render a pinned official chart and inspect drivers, RBAC/hostPaths, enabled components and actual DaemonSets. neuron allocates whole devices; neuroncore allocates cores.
</details>

## 9. What is the AIBrix autoscaler configuration shape?

<details>
<summary>Answer and explanation</summary>

PodAutoscaler uses scaleTargetRef, metricsSources and HPA/KPA/APA strategies. A controller and actual metrics source are required; a ConfigMap or GPU request alone does not scale workloads.
</details>

## 10. What are NGC/profile roles and credential boundaries?

<details>
<summary>Answer and explanation</summary>

Identify supported models, images and profiles. NIM_MODEL_PROFILE must use an actual profile ID/name. Distinguish image-pull from runtime-download credentials; secret environment delivery does not satisfy a file-only policy.
</details>

## 11. Does multiple-backend support imply arbitrary mixing?

<details>
<summary>Answer and explanation</summary>

No. Validate the chosen vLLM/SGLang/TensorRT-LLM, device, connector, model and KV format. Matching model names alone do not establish prefill/decode interoperability.
</details>

## 12. How should model caching be selected?

<details>
<summary>Answer and explanation</summary>

Compare local/EBS/EFS/FSx using size, revision, restart/download concurrency, authorization and cost. Do not share one RWO EBS PVC across nodes; embedding models in an image can be appropriate under specific constraints.
</details>

## 13. What matters in GenAI-Perf commands and results?

<details>
<summary>Answer and explanation</summary>

Version0.0.16 uses profile and synthetic-input-tokens-mean/output-tokens-mean. analyze can run additional sweep load. Preserve raw results, failures, warmup and tokenizer; GPU utilization needs configured collection.
</details>

## 14. Does StatefulSet alone implement distributed vLLM?

<details>
<summary>Answer and explanation</summary>

No. Stable names can help, but rank, rendezvous, TP/PP, model and communication need explicit configuration. Check ordered-readiness deadlocks; other controllers may also be appropriate.
</details>

## 15. How does NEURON_RT_VISIBLE_CORES relate to Kubernetes allocation?

<details>
<summary>Answer and explanation</summary>

It selects runtime cores and does not create unallocated devices. inf2.xlarge has one device, so neuron:2 cannot schedule. Distinguish SDK2.32 NxD for Inf2 from the new Trn2/3 beta path.
</details>

[Return to guide](../../ai-ml/04-inference-frameworks.md)
