# AI/ML Best Practices on EKS

> **Last Updated**: September 12, 2026
> **Baselines**: inference-perf0.6.1 / SOCI0.15.0 / Karpenter1.14.1 / External Secrets2.10.0

Evaluate improvements using latency, success rate, throughput, cost and recovery for the same workload. A GPU, snapshotter or sharing feature does not guarantee a fixed speedup or savings percentage.

![Benchmarking, startup optimization, devices, networking/storage, observability, cost and security evaluated with measurements and recovery checks.](../.gitbook/assets/en-ai-ml-07-ai-ml-best-practices-0.png)

[View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-07-ai-ml-best-practices-0.html)

## Benchmarking LLM Inference

![Distinct measurement windows for first output, token intervals, end-to-end latency and aggregate throughput/goodput.](../.gitbook/assets/en-ai-ml-07-ai-ml-best-practices-1.png)

[View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-07-ai-ml-best-practices-1.html)

| Metric | Definition and caveats |
| --- | --- |
| TTFT | Send-to-first **nonempty output** received; the first HTTP/SSE frame need not contain a token |
| ITL | Inter-token/chunk intervals; a network chunk may contain multiple tokens |
| TPOT | Tool-defined average after the first token; undefined for one or fewer output tokens |
| E2E | Request-to-completion time; record queue, network and postprocessing boundaries |
| Request throughput | Successful completed requests / specified measurement window |
| Token throughput | Sum of output tokens in the window / time, not an unweighted mean of request TPS |
| Goodput | Rate of requests satisfying success and latency SLO criteria |

With actual token timestamps, mean ITL is(last-first token time)/(tokens-1). Nonstreaming responses cannot measure actual TTFT/ITL. Specify tokenizer, empty/single-token output, failures and warmup exclusions.500ms/50ms are not universal SLOs.

### inference-perf and GenAI-Perf

inference-perf is a Kubernetes SIGs/wg-serving benchmark tool. The inspected PyPI package is0.6.1, while its Git tag's pyproject still says0.5.0; this metadata discrepancy is recorded. The actual CLI uses --config_file or structured options such as --server.type, not the former benchmark --endpoint --prompt-length interface.

This **internal mock** configuration does not call a model server. The actual0.6.1 CLI completed three requests with one worker. Mock token counts are zero and TTFT/TPOT are null, so these are not model-performance results.

```yaml
api:
  type: chat
  streaming: false
data:
  type: mock
load:
  type: concurrent
  stages:
    - concurrency_level: 1
      num_requests: 3
  num_workers: 1
  worker_max_concurrency: 1
  base_seed: 17
server:
  type: mock
  base_url: http://127.0.0.1:8000
report:
  request_lifecycle:
    summary: true
    per_stage: true
    per_request: true
storage:
  local_storage:
    path: ./benchmark-fixture-results
```

```bash
inference-perf --config_file benchmark-fixture.yaml
```

Before switching to a real endpoint, verify server/API types, model aliases, streaming, tokenizer and authentication. Configuration may contain secret headers and merged configuration is logged, so validate credential delivery/redaction. Preserve output files, raw requests/responses and failures, respecting dataset privacy and usage permissions.

Constant/Poisson rate measures arrivals per second; concurrent load controls concurrency. Equal numeric settings are not equivalent. Test a single-request baseline, bounded load ramps, bursts and realistic distributions. A saturation curve alone does not prove a CPU/GPU/memory bottleneck; inspect profiling, queues, networking and client capacity.

Use GenAI-Perf0.0.16's audited [profile/endpoint/service/token options](04-inference-frameworks.md), not invented --backend vllm combinations. GPU metrics need separate collection; check load-generator CPU/network limits. Benchmark Jobs need verified images, configuration keys, PVCs, deadlines and retry semantics that account for duplicate load.

## Container Startup Optimization

![Measure Pod placement, image fetch/unpack, container startup, model loading and readiness separately.](../.gitbook/assets/en-ai-ml-07-ai-ml-best-practices-2.png)

[View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-07-ai-ml-best-practices-2.html)

Measure image transfer, unpacking, model download/loading and readiness separately. Unsourced“always5–15minutes” and“80–95%savings” tables were removed.45GB/1Gbps≈360seconds is only idealized transfer arithmetic, excluding compressed size, protocol, disk and concurrency overhead—not a measured pull time.

External model artifacts may reduce image changes/pulls but add download and cache-management costs. Prepared images can be appropriate in some environments. Initialization must propagate failures and verify revision, checksums and completion. The former S3 sync followed by a successful echo could mask download failure and was removed.

Multi-stage builds must align Python interpreter/ABI and CUDA/runtime libraries, including executables/shared libraries. Do not assume Ubuntu22.04 python3.11 and pip3 use the same interpreter or copy only site-packages. Use supported distribution packages/wheels and test imports/entrypoints inside the image. Prefer read-only root filesystems with explicit writable cache/tmp/model mounts.

### SOCI0.15

SOCI supports lazy image loading, but benefits may shrink when startup immediately reads all weights/libraries. Having an index does not configure CRI to use the SOCI snapshotter. Verify containerd/CRI integration, image/index digests and registry compatibility. The unverified privileged DaemonSet exposing host containerd sockets was removed.

Version0.15 create/push take positional image references, not --ref. Current getting-started uses convert to create SOCI-enabled images. Standalone mode processes local OCI layouts without containerd or sudo.

```bash
soci convert --standalone --format oci-dir input-oci-layout output-soci-layout
```

Inputs must be OCI layouts, not ordinary docker-save tarballs. Conversion may fail if every layer is smaller than min-layer-size. This audit converted one synthetic layer with explicit min-layer-size=0 and verified eight blob digests. No container startup benchmark was run. Preserve the converted image/index together when publishing.

### Bottlerocket Bootstrap

In1.64, `bootstrap-containers.<name>.user-data` is **base64 data**, consumed as a file by the bootstrap container. Plain shell text in settings is not automatically executed. The source image must be real and correctly use host image stores/namespaces. A static images-prefetched=true label is not evidence of success.

mode=once becomes off after execution. Failure of essential=true stops boot; false permits failure, so align the setting with readiness needs. allowed-unsafe-sysctls is not a privileged-container switch. Include prefetch's effect on node preparation time in measurements.

## GPU, Neuron and Storage Selection

Parameters×bytes is only the weight lower bound. Include architecture-aware KV cache, activations, workspace, communication buffers, fragmentation and sharding constraints.13B FP16 weights≈26GB do not fit24GB;70B FP16≈140GB exceeds four24GB GPUs combined. More host CPUs do not enlarge unchanged GPU VRAM.

Distinguish p4d.24xlarge8×40GB from p4de8×80GB A100s. G5g uses Arm/T4G; verify image/kernel architecture. See the [audited Inf2 table](04-inference-frameworks.md) for inf2.48xlarge192vCPUs/768GiB host RAM,12chips/24NeuronCores/384GiB HBM. A family name such as P5 does not fix GPU counts across every size. Recheck available generations, regions, quotas and prices when choosing.

LoRA reduces trainable adapter state but retains base weights/activations and differs from QLoRA. Do not use a function that assumes most LoRA models fit24GB. Measure peak memory, latency, throughput and restarts.

Do not select storage solely by a10TB dataset cutoff. Compare access patterns, concurrency, metadata, latency, semantics, durability and cost. Current general gp3 documentation lists baseline3000IOPS/125MiB/s and maximum80000IOPS/2000MiB/s, subject to size/IOPS/instance constraints; Outposts differs. Historical16000IOPS/1GB/s limits are not universally current.

Use the [infrastructure guide](06-ai-infrastructure.md) for EFS Elastic throughput, FSx/CSI/S3 associations and Mountpoint POSIX limits. S3 has neither infinite throughput nor fixed latency; EFS is not universally slower than FSx. Instance store/tmpfs are ephemeral. GPU KV cache normally resides in GPU memory, not automatically in SSD/tmpfs.

### Model Cache Verification

A config.json file does not prove weights finished downloading. Verify **all files** against a trusted release manifest/revision before exposing immutable read-only storage. Prevent concurrent downloader races and partially written files.

This local validator performs no downloads/deletion. Tests cover complete files, wrong revisions, partial/missing weights, traversal and external symlinks. Manifest trust and post-verification immutability remain separate requirements.

```python
from pathlib import Path
import hashlib
import re


def verify_model_cache(root, manifest, expected_revision):
    """Verify files against a separately trusted release manifest; no downloads/deletion."""
    root = Path(root).resolve(strict=True)
    if manifest.get("revision") != expected_revision:
        raise ValueError("Model revision mismatch")
    files = manifest.get("files")
    if not isinstance(files, dict) or not files:
        raise ValueError("Empty or invalid release manifest")
    for relative, expected_hash in files.items():
        name = Path(relative)
        if name.is_absolute() or ".." in name.parts or not name.parts:
            raise ValueError("Unsafe manifest path")
        if not isinstance(expected_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_hash):
            raise ValueError("Invalid SHA256")
        target = (root / name).resolve(strict=True)
        if not target.is_relative_to(root) or not target.is_file():
            raise ValueError("File escapes the cache or is not a regular file")
        digest = hashlib.sha256()
        with target.open("rb") as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(chunk)
        if digest.hexdigest() != expected_hash:
            raise ValueError("Incomplete or corrupt model file: " + relative)
    return root
```

Checkpoints need optimizer/RNG/data-cursor and shard state as in the [training/recovery example](05-model-training.md). Do not delete prior valid copies before transfer, checksums and completion manifests succeed. The old ls/xargs rm -rf loop confused directory contents with checkpoint paths and attempted deletion through a read-only mount; it was removed. Delaying the first sync30minutes or omitting termination flushing increases lost-work exposure.

## Networking and Scheduling

EFA improves communication for suitable workloads; it is not required for every DDP execution. Verify interfaces, same-AZ placement, driver/libfabric/aws-ofi-nccl, Pod resources, security groups and actual transport. RAID0/subnet tags do not enable it. Avoid unverified NCCL_TIMEOUT and blindly copied Ring/Simple/IB_DISABLE settings. torchrun --nnodes counts nodes, not total-process WORLD_SIZE.

Use Karpenter1.14.1's actual placementGroupSelector. An aws:ec2:placement-group tag is not the placement API, and aws: is not a user-tag namespace. This **schema example** requires approved AMI/subnet/SG/role identifiers and an existing placement group. The example specifies amiFamily AL2023, so the replacement must be a validated EKS AL2023 AMI, not an AMI for another OS. It does not complete EFA networkInterfaces configuration.

```yaml
apiVersion: karpenter.k8s.aws/v1
kind: EC2NodeClass
metadata:
  name: prepared-gpu-class
spec:
  role: REPLACE_WITH_APPROVED_NODE_ROLE
  amiSelectorTerms:
  - id: ami-0123456789abcdef0
  subnetSelectorTerms:
  - id: subnet-0123456789abcdef0
  securityGroupSelectorTerms:
  - id: sg-0123456789abcdef0
  placementGroupSelector:
    name: prepared-training-placement-group
  amiFamily: AL2023
```

### Disruption Budgets and Spot

This budget applies Monday–Friday **09:00–17:00UTC**. The old0 9-17 * * 1-5 started an eight-hour window every hour through17:00, extending protection until01:00the next day. Concurrent budgets use the stricter restriction and do not automatically follow local timezones.

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: reviewed-gpu-pool
spec:
  template:
    spec:
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: prepared-gpu-class
      requirements:
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - on-demand
        - spot
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 5m
    budgets:
    - nodes: '0'
      schedule: 0 9 * * 1-5
      duration: 8h
    - nodes: 30%
```

budgets.nodes=0 limits voluntary disruption, not Spot interruptions, node failures or forceful expiration. Spot-only requirements are mandatory, not a preference with on-demand fallback. ScheduleAnyway topology spread is soft; verify actual replicas, capacity and AZ distribution.

terminationGracePeriodSeconds=120 does not guarantee EC2 grants120seconds. Test gateway readiness/draining, endpoint propagation, SIGTERM, active streams, retries and duplicates through real termination. Do not invent a vLLM /drain API. Inference caches, sessions and TP groups carry state/restart costs.

## Observability and Cost

Use [current vLLM metrics](02-vllm-deployment.md) and [DCGM rules](06-ai-infrastructure.md). KV occupancy is vllm:kv_cache_usage_perc, not the old gpu_cache_usage_perc. Observe queues/preemption and backend behavior rather than assuming full cache immediately rejects requests. Derive prefix-hit ratios from current hit/query counters with zero-denominator handling.

DCGM FB_USED/FREE are MiB gauges; XID_ERRORS is the last code. Avoid nonexistent FB_TOTAL or increase() on gauges. Temperature alone does not prove thermal throttling; compare clocks, power, throttle reasons and workload. Match Prometheus labels/histogram aggregation, and use valid subquery syntax for avg_over_time over expressions.

VPA Off provides CPU/memory recommendations, not automatic GPU-instance selection. The former rightsizing script inspected only the first series and compared0–1ratios with50/90; it was removed. Inspect peaks, queues, SLOs and recovery after removal across workloads.

Record savings using actual region/OS/purchase terms, utilization, idle/failure time, storage, transfer and operations. Spot/Savings Plans/RI differ in discounts and capacity guarantees. Avoid fixed60–90% tables or adding optimization savings percentages. Make commitment-purchase decisions separately using measured baselines and variability.

## Model Access and Secret Management

S3 ListBucket and GetObject use bucket/object ARNs and supported condition keys respectively. General-purpose buckets can use bucket-tag conditions such as aws:ResourceTag/Environment after ABAC is explicitly enabled. ABAC is disabled by default: verify bucket status, trusted tag-administration permissions, identity/bucket policies and action/resource pairing rather than copying the tag condition alone. Enablement does not create the required Allow or override other Deny policies. Verify trust-bound ServiceAccount namespace/name, SDK credential chains and actual request identity. vLLM does not automatically download every S3 model URI.

The inspected ESO2.10.0 CRD **serves v1**, with v1beta1 served=false. This example references an already approved same-namespace SecretStore. Prepare remote keys, permissions, rotation and target lifecycle separately.

```yaml
apiVersion: external-secrets.io/v1
kind: ExternalSecret
metadata:
  name: model-download-token
  namespace: ai-ml
spec:
  refreshPolicy: Periodic
  refreshInterval: 1h
  secretStoreRef:
    name: approved-secrets-manager
    kind: SecretStore
  target:
    name: model-download-credential
    creationPolicy: Owner
  data:
  - secretKey: token
    remoteRef:
      key: approved/model-download
      property: token
```

Mount Kubernetes Secrets as volumes and have applications reread files when needed. subPath mounts do not receive automatic updates; environment variables or values read only at startup do not reload automatically. ESO refresh is not upstream credential issuance/rotation itself. Verify provider rotation, Secret access and application reload separately.

CloudTrail Secrets Manager API records do not capture every application read of a local Secret file. Do not claim kubectl describe generally prints SecretKeyRef values, but environment delivery still exposes process/debugging surfaces and differs from a file-credential policy. Never print real secrets in examples/logs.

NetworkPolicy requires CNI enforcement. Verify selector AND/OR semantics, default namespace-name labels and both TCP/UDP DNS. The10.0.0.0/8 health-check opening and“internet443means S3-only” rule were removed. With prepared models, restrict runtime egress to necessary paths and distinguish inference/management APIs at the gateway.

Audit logs should capture user/workload identity, model revision, action, outcome and request ID, redacting prompts/secrets as appropriate. Parsing containerd CRI logs as Docker or retaining only lines containing request can lose audit events. Verify actual collectors, parsers, IAM, buffers, retention and delivery failures—not just a ConfigMap.

## Verification Scope

All original guide/quiz prose and87unique code blocks were reviewed. Validation includes three native inference-perf mock requests, SOCI local OCI conversion, six cache cases, three Karpenter/ESO schemas and cron arithmetic. No GPU/real-model benchmark, container-startup measurement, host SOCI installation, cloud resource or secret provider was executed.

## References

- [inference-perf0.6.1](https://github.com/kubernetes-sigs/inference-perf/tree/v0.6.1)
- [SOCI0.15 CLI](https://github.com/awslabs/soci-snapshotter/blob/v0.15.0/docs/cli-usage.md)
- [Bottlerocket1.64 bootstrap settings](https://bottlerocket.dev/en/os/1.64.x/api/settings/bootstrap-containers/)
- [Karpenter1.14.1 CRDs](https://github.com/aws/karpenter-provider-aws/tree/v1.14.1/pkg/apis/crds)
- [Karpenter disruption](https://karpenter.sh/docs/concepts/disruption/)
- [ESO2.10 ExternalSecret CRD](https://github.com/external-secrets/external-secrets/blob/helm-chart-2.10.0/config/crds/bases/external-secrets.io_externalsecrets.yaml)
- [Kubernetes Secret updates](https://kubernetes.io/docs/concepts/configuration/secret/)
- [S3 general-purpose bucket ABAC enablement](https://docs.aws.amazon.com/AmazonS3/latest/userguide/buckets-tagging-enable-abac.html)
- [EBS gp3 performance](https://docs.aws.amazon.com/ebs/latest/userguide/general-purpose.html)

## Quiz

[AI/ML Best Practices Quiz](../quizzes/ai-ml/07-ai-ml-best-practices-quiz.md)
