# AI/ML Best Practices Quiz

This quiz tests your understanding of AI/ML best practices on Amazon EKS, including benchmarking, container optimization, GPU selection, networking, storage, observability, and cost optimization.

## Quiz Questions

### 1. What does TTFT (Time to First Token) measure in LLM inference benchmarking?

A) The total time to generate all tokens in a response
B) The time from request submission to the first token being generated
C) The average time between consecutive tokens
D) The number of tokens generated per second

<details>
<summary>Show Answer</summary>

**Answer: B) The time from request submission to the first token being generated**

**Explanation:**
TTFT (Time to First Token) measures the latency from when a request is submitted to when the first token of the response is generated. This metric is critical for user experience as it determines how quickly users see the beginning of a response.

The formula is: `TTFT = t_first_token - t_request`

Key points about TTFT:
- Directly impacts perceived responsiveness of the application
- Should be < 500ms for interactive applications
- Affected by model loading, prompt processing (prefill), and queue depth
- Higher TTFT indicates potential issues with GPU memory, batch size, or system load

Other metrics:
- ITL (Inter-Token Latency): Time between consecutive tokens
- TPS (Tokens Per Second): Generation speed
- E2E Latency: Total time from request to complete response

</details>

### 2. Which container startup optimization technique provides the highest reduction in cold start time?

A) Multi-stage Docker builds alone
B) Model artifact decoupling alone
C) Combined approach (decoupling + multi-stage + prefetching + SOCI)
D) Using smaller base images only

<details>
<summary>Show Answer</summary>

**Answer: C) Combined approach (decoupling + multi-stage + prefetching + SOCI)**

**Explanation:**
The combined approach provides the highest reduction in cold start time, achieving 80-95% improvement compared to naive implementations.

Cold start optimization comparison:

| Technique | Startup Reduction |
|-----------|-------------------|
| Model decoupling | 50-70% |
| Multi-stage builds | 30-50% |
| SOCI snapshotter | 60-80% |
| Image prefetching | 70-90% |
| **Combined approach** | **80-95%** |

The combined approach works by:
1. **Model decoupling**: Separates large model weights from container images
2. **Multi-stage builds**: Reduces image size by excluding build dependencies
3. **SOCI snapshotter**: Enables lazy pulling so containers start before full image download
4. **Image prefetching**: Pre-pulls images during node bootstrap

For AI/ML images that can be 10-50GB, this combination can reduce startup from 5-15 minutes to under 1 minute.

</details>

### 3. Which GPU instance family is best suited for large-scale distributed training requiring high-bandwidth inter-node communication?

A) G5 (NVIDIA A10G)
B) G6 (NVIDIA L4)
C) P5 (NVIDIA H100)
D) Inf2 (AWS Inferentia2)

<details>
<summary>Show Answer</summary>

**Answer: C) P5 (NVIDIA H100)**

**Explanation:**
P5 instances with NVIDIA H100 GPUs are best suited for large-scale distributed training because they offer:

- **8x NVIDIA H100 GPUs** with 80GB HBM3 memory each
- **3200 Gbps EFA networking** - essential for distributed training
- **NVLink 4.0** for high-bandwidth GPU-to-GPU communication within the node
- **192 vCPUs and 2048GB memory** for data preprocessing

Comparison for distributed training:

| Instance | GPUs | GPU Memory | Network | Training Suitability |
|----------|------|------------|---------|---------------------|
| G5 | 1-8 A10G | 24GB | 100 Gbps | Small/medium models |
| G6 | 1-8 L4 | 24GB | 100 Gbps | Inference focus |
| P4d | 8 A100 | 40-80GB | 400 Gbps EFA | Large-scale training |
| **P5** | **8 H100** | **80GB** | **3200 Gbps EFA** | **Frontier models** |
| Inf2 | 1-12 Inferentia2 | 32GB | 100 Gbps | Inference only |

The P5's 3200 Gbps EFA bandwidth is 8x that of P4d, making it ideal for training jobs where gradient synchronization across nodes is the bottleneck.

</details>

### 4. What is the primary purpose of EFA (Elastic Fabric Adapter) in distributed AI/ML training?

A) To increase GPU memory capacity
B) To provide low-latency, high-bandwidth inter-node communication
C) To enable GPU time-sharing
D) To accelerate model inference

<details>
<summary>Show Answer</summary>

**Answer: B) To provide low-latency, high-bandwidth inter-node communication**

**Explanation:**
EFA (Elastic Fabric Adapter) is a network interface for Amazon EC2 instances that enables high-performance computing (HPC) and machine learning applications to achieve the inter-node communication performance of on-premises HPC clusters.

Key benefits of EFA for distributed training:
1. **OS-bypass capability**: Allows applications to communicate directly with the network adapter, reducing latency
2. **High bandwidth**: Up to 3200 Gbps on P5 instances
3. **Low latency**: Sub-microsecond latencies for collective operations
4. **NCCL optimization**: Works with AWS OFI NCCL plugin for optimized GPU-to-GPU communication

EFA configuration requirements:
```yaml
resources:
  limits:
    vpc.amazonaws.com/efa: 4  # Request EFA devices
```

NCCL environment variables for EFA:
```bash
export FI_PROVIDER=efa
export FI_EFA_USE_DEVICE_RDMA=1
export NCCL_ALGO=Ring,Tree
```

EFA is essential for:
- Multi-node distributed training with frameworks like PyTorch DDP, Horovod
- Large model training with tensor/pipeline parallelism
- Any workload where gradient synchronization is a bottleneck

</details>

### 5. When should you use FSx for Lustre instead of EFS for AI/ML workloads?

A) When you need shared access from multiple pods
B) When training datasets exceed 10TB and require high throughput
C) When storing model checkpoints temporarily
D) When running inference workloads with small models

<details>
<summary>Show Answer</summary>

**Answer: B) When training datasets exceed 10TB and require high throughput**

**Explanation:**
FSx for Lustre is the optimal choice for large training datasets (>10TB) that require high throughput, while EFS is better for smaller datasets and shared model storage.

Storage selection guide:

| Use Case | Recommended Storage | Reasoning |
|----------|---------------------|-----------|
| Training datasets <500GB | EBS gp3 | Single node, cost-effective |
| Training datasets 500GB-10TB | EFS | Multi-node read, moderate throughput |
| **Training datasets >10TB** | **FSx Lustre** | **Parallel filesystem, TB/s throughput** |
| Shared model weights | EFS | ReadWriteMany, caching |
| Temporary checkpoints | Instance store | Lowest latency, ephemeral |
| Long-term model storage | S3 | Cost-effective, durable |

FSx for Lustre advantages:
- Throughput up to 1+ TB/s (vs EFS's ~1-3 GB/s)
- Sub-millisecond latencies
- Direct S3 integration with `s3ImportPath`
- Parallel filesystem designed for HPC workloads

```yaml
# FSx Lustre for large datasets
storageClassName: fsx-lustre-sc
parameters:
  perUnitStorageThroughput: "250"  # MB/s per TiB
  s3ImportPath: s3://training-data  # Transparent S3 access
```

</details>

### 6. Which DCGM metric should you monitor to detect GPU thermal throttling?

A) DCGM_FI_DEV_GPU_UTIL
B) DCGM_FI_DEV_FB_USED
C) DCGM_FI_DEV_GPU_TEMP
D) DCGM_FI_DEV_XID_ERRORS

<details>
<summary>Show Answer</summary>

**Answer: C) DCGM_FI_DEV_GPU_TEMP**

**Explanation:**
DCGM_FI_DEV_GPU_TEMP monitors GPU temperature in Celsius, which is the primary indicator for detecting thermal throttling conditions.

Key GPU metrics and their purposes:

| Metric | Purpose | Alert Threshold |
|--------|---------|-----------------|
| **DCGM_FI_DEV_GPU_TEMP** | **Thermal monitoring** | **>80C warning, >90C critical** |
| DCGM_FI_DEV_GPU_UTIL | Compute utilization | >95% sustained |
| DCGM_FI_DEV_FB_USED | Memory usage | >95% of total |
| DCGM_FI_DEV_SM_CLOCK | Clock frequency (throttling detection) | Below baseline |
| DCGM_FI_DEV_POWER_USAGE | Power consumption | Near TDP limit |
| DCGM_FI_DEV_XID_ERRORS | Hardware errors | Any increase |

Thermal throttling detection:
```yaml
# Alert rule for thermal issues
- alert: GPUHighTemperature
  expr: DCGM_FI_DEV_GPU_TEMP > 80
  for: 5m
  labels:
    severity: warning

- alert: GPUCriticalTemperature
  expr: DCGM_FI_DEV_GPU_TEMP > 90
  for: 1m
  labels:
    severity: critical
```

When temperature exceeds thresholds, GPUs automatically reduce clock speeds (thermal throttling), impacting training and inference performance.

</details>

### 7. What is the recommended approach for using Spot instances with GPU inference workloads?

A) Never use Spot instances for inference
B) Use Spot only for training, On-Demand for inference
C) Use Spot with graceful termination handling and topology spread
D) Use Spot without any special configuration

<details>
<summary>Show Answer</summary>

**Answer: C) Use Spot with graceful termination handling and topology spread**

**Explanation:**
Spot instances can provide 60-90% cost savings for stateless inference workloads when properly configured with graceful termination handling and availability considerations.

Best practices for Spot inference:

1. **Graceful termination handling**:
```yaml
spec:
  terminationGracePeriodSeconds: 120
  containers:
  - lifecycle:
      preStop:
        exec:
          command: ["/bin/sh", "-c", "curl -X POST localhost:8000/drain; sleep 30"]
```

2. **Topology spread for availability**:
```yaml
topologySpreadConstraints:
- maxSkew: 2
  topologyKey: topology.kubernetes.io/zone
  whenUnsatisfiable: ScheduleAnyway
```

3. **Mixed capacity types**:
```yaml
affinity:
  nodeAffinity:
    preferredDuringSchedulingIgnoredDuringExecution:
    - weight: 100
      preference:
        matchExpressions:
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["spot"]
    - weight: 50
      preference:
        matchExpressions:
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["on-demand"]
```

Spot is suitable for inference because:
- Inference pods are typically stateless
- Multiple replicas provide redundancy
- 2-minute interruption warning allows graceful drainage

</details>

### 8. What is the formula for calculating Inter-Token Latency (ITL)?

A) `t_last_token - t_request`
B) `(t_last_token - t_first_token) / (n_tokens - 1)`
C) `n_tokens / total_generation_time`
D) `t_first_token - t_request`

<details>
<summary>Show Answer</summary>

**Answer: B) `(t_last_token - t_first_token) / (n_tokens - 1)`**

**Explanation:**
Inter-Token Latency (ITL) measures the average time between consecutive tokens during generation. The formula is:

`ITL = (t_last_token - t_first_token) / (n_tokens - 1)`

Where:
- `t_last_token`: Timestamp when the last token was generated
- `t_first_token`: Timestamp when the first token was generated
- `n_tokens`: Total number of tokens generated
- We divide by `(n_tokens - 1)` because we're measuring intervals between tokens

ITL importance:
- Determines streaming quality for chat applications
- Target: < 50ms for smooth user experience
- Higher ITL indicates GPU memory pressure or compute bottlenecks

Other metric formulas:
- **TTFT**: `t_first_token - t_request` (time to first token)
- **TPS**: `n_tokens / total_generation_time` (tokens per second)
- **E2E Latency**: `t_complete - t_request` (end-to-end)

Example calculation:
- First token at 500ms, last token at 2500ms, 50 tokens generated
- ITL = (2500 - 500) / (50 - 1) = 2000 / 49 = ~41ms

</details>

### 9. Which test scenario is most appropriate for finding the maximum throughput of an LLM inference service?

A) Baseline test
B) Saturation test
C) Real dataset test
D) Long context test

<details>
<summary>Show Answer</summary>

**Answer: B) Saturation test**

**Explanation:**
The saturation test is specifically designed to find the maximum throughput by incrementally increasing concurrency until latency degrades, revealing the system's capacity limits.

Test scenario comparison:

| Scenario | Purpose | Configuration |
|----------|---------|---------------|
| Baseline | Establish single-request performance | Concurrency=1, 100 requests |
| **Saturation** | **Find throughput limits** | **Concurrency=[1,5,10,20,50,100]** |
| Production | Validate real-world performance | Variable prompts, realistic load |
| Real dataset | Test with actual data patterns | ShareGPT or domain data |
| Long context | Test context window handling | 4K-128K token prompts |

Saturation test configuration:
```yaml
saturation:
  description: "Find maximum throughput"
  concurrency: [1, 5, 10, 20, 50, 100]  # Incrementally increase
  num_requests: 500
  prompt_length: 256
  max_tokens: 512
```

What saturation test reveals:
- Throughput vs latency curve
- Point where latency starts degrading
- Whether system is GPU-bound, memory-bound, or CPU-bound
- Optimal operating concurrency level

The goal is to find the "knee" of the curve where throughput plateaus while latency remains acceptable.

</details>

### 10. What is the purpose of SOCI (Seekable OCI) snapshotter for AI/ML containers?

A) To compress container images
B) To enable lazy pulling so containers can start before full image download
C) To encrypt container images
D) To share images between nodes

<details>
<summary>Show Answer</summary>

**Answer: B) To enable lazy pulling so containers can start before full image download**

**Explanation:**
SOCI (Seekable OCI) snapshotter enables lazy loading of container images, allowing containers to start before the entire image is downloaded. This is particularly valuable for large AI/ML images (10-50GB).

How SOCI works:
1. Creates an index of the container image layers
2. Downloads only the metadata and essential layers initially
3. Fetches remaining layers on-demand as the application accesses files
4. Container can start with only ~10-20% of image downloaded

Benefits for AI/ML:
- 60-80% reduction in container startup time
- Particularly effective for images with large, rarely-accessed layers
- Works best when model weights are accessed after container startup

SOCI setup:
```bash
# Create SOCI index for an image
soci create \
  --ref public.ecr.aws/myrepo/vllm:latest \
  --platform linux/amd64

# Push the index to registry
soci push \
  --ref public.ecr.aws/myrepo/vllm:latest
```

Combined with other optimizations:
- Model decoupling (50-70%)
- Multi-stage builds (30-50%)
- SOCI snapshotter (60-80%)
- Image prefetching (70-90%)

SOCI is most effective when the container runtime supports it (containerd with SOCI plugin) and images are stored in compatible registries (Amazon ECR).

</details>

### 11. Which Karpenter consolidation policy setting prevents node disruption during business hours?

A) consolidationPolicy: WhenEmpty
B) consolidateAfter: 0
C) budgets with schedule and nodes: "0"
D) weight: 0

<details>
<summary>Show Answer</summary>

**Answer: C) budgets with schedule and nodes: "0"**

**Explanation:**
Karpenter's disruption budgets with schedule and `nodes: "0"` prevent any node consolidation during specified time windows, typically business hours.

Configuration example:
```yaml
disruption:
  consolidationPolicy: WhenEmptyOrUnderutilized
  consolidateAfter: 5m

  budgets:
  # No consolidation during business hours
  - nodes: "0"
    schedule: "0 9-17 * * 1-5"  # 9 AM to 5 PM, Mon-Fri
    duration: 8h

  # Allow 30% consolidation during off-peak
  - nodes: "30%"
```

Budget parameters:
- `nodes`: Maximum number/percentage of nodes that can be disrupted
- `schedule`: Cron expression for when budget applies
- `duration`: How long the budget is active after schedule triggers

Why this matters for AI/ML:
- GPU nodes are expensive and disruption causes cold starts
- Inference latency spikes during node replacement
- Training jobs may lose progress if checkpointing isn't frequent
- Business hours typically have highest traffic

Other consolidation settings:
- `consolidationPolicy: WhenEmpty`: Only consolidate completely empty nodes
- `consolidationPolicy: WhenEmptyOrUnderutilized`: Also consolidate underutilized
- `consolidateAfter`: Delay before consolidation (e.g., 5m)

</details>

### 12. What is the recommended method for managing HuggingFace and NGC API keys in Kubernetes?

A) Hardcode in Dockerfile
B) Pass as environment variables in pod spec
C) Use External Secrets Operator with AWS Secrets Manager
D) Store in ConfigMap

<details>
<summary>Show Answer</summary>

**Answer: C) Use External Secrets Operator with AWS Secrets Manager**

**Explanation:**
External Secrets Operator (ESO) with AWS Secrets Manager provides secure, centralized secret management with automatic rotation and auditing capabilities.

Why ESO is recommended:
1. **Centralized management**: Secrets stored in AWS Secrets Manager
2. **Automatic sync**: ESO automatically updates Kubernetes secrets
3. **Rotation support**: Secrets can be rotated without redeploying pods
4. **Audit trail**: AWS CloudTrail logs all secret access
5. **IAM integration**: Fine-grained access control with IRSA

Configuration example:
```yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: model-registry-secrets
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: aws-secretsmanager
    kind: ClusterSecretStore
  target:
    name: model-registry-credentials
  data:
  - secretKey: HUGGING_FACE_HUB_TOKEN
    remoteRef:
      key: ai-ml/huggingface-token
      property: token
  - secretKey: NGC_API_KEY
    remoteRef:
      key: ai-ml/ngc-api-key
      property: key
```

Why other options are problematic:
- **Hardcoded in Dockerfile**: Secrets exposed in image layers
- **Environment variables in pod spec**: Visible in kubectl describe
- **ConfigMap**: Not encrypted, visible to anyone with read access

Security best practices:
- Use IRSA for service account authentication
- Enable encryption at rest in Secrets Manager
- Implement least-privilege access policies
- Rotate secrets regularly

</details>

### 13. For a 30B parameter model inference workload with a medium budget, which GPU instance type is most appropriate?

A) g5.xlarge (1x A10G, 24GB)
B) g5.4xlarge (1x A10G, 24GB)
C) g5.12xlarge (4x A10G, 96GB total)
D) p4d.24xlarge (8x A100, 640GB total)

<details>
<summary>Show Answer</summary>

**Answer: C) g5.12xlarge (4x A10G, 96GB total)**

**Explanation:**
A 30B parameter model requires approximately 60GB of GPU memory for FP16 inference (2 bytes per parameter), making g5.12xlarge with 4x A10G GPUs (96GB total) the appropriate choice for medium budget.

Memory calculation:
- 30B parameters x 2 bytes (FP16) = 60GB minimum
- With KV cache overhead: ~70-80GB recommended
- g5.12xlarge: 4 x 24GB = 96GB (sufficient with margin)

Instance selection guide:

| Model Size | Memory Needed | Recommended Instance | Budget |
|------------|---------------|---------------------|--------|
| <7B | 14GB | g5.xlarge | Low |
| 7-13B | 26GB | g5.2xlarge | Low-Medium |
| 13-30B | 60GB | g5.4xlarge (quantized) or g5.12xlarge | Medium |
| **30B** | **60GB** | **g5.12xlarge (4x A10G)** | **Medium** |
| 30-70B | 140GB | g5.12xlarge + tensor parallel | Medium-High |
| >70B | 280GB+ | p4d.24xlarge | High |

Why g5.12xlarge for 30B:
- 4-way tensor parallelism distributes model across GPUs
- Each GPU holds ~15GB of model weights
- Remaining memory available for KV cache
- More cost-effective than P4d for inference

P4d.24xlarge would work but is overkill for 30B inference and significantly more expensive.

</details>

### 14. Which vLLM metric indicates that the system may start rejecting requests due to memory pressure?

A) vllm:num_requests_running
B) vllm:time_to_first_token_seconds
C) vllm:gpu_cache_usage_perc
D) vllm:request_success_total

<details>
<summary>Show Answer</summary>

**Answer: C) vllm:gpu_cache_usage_perc**

**Explanation:**
`vllm:gpu_cache_usage_perc` measures KV (Key-Value) cache utilization. When this metric approaches 100%, vLLM cannot accept new requests because there's no memory available for storing attention states.

KV cache importance:
- Stores computed attention keys and values for each token
- Grows with sequence length and batch size
- When full, vLLM must either preempt running requests or reject new ones

Alert configuration:
```yaml
- alert: vLLMKVCacheFull
  expr: vllm:gpu_cache_usage_perc > 0.95
  for: 5m
  labels:
    severity: critical
  annotations:
    summary: "vLLM KV cache nearly full"
    description: "KV cache usage above 95%, requests may be rejected"
```

What to do when KV cache is full:
1. Reduce `--max-num-seqs` (concurrent sequences)
2. Reduce `--max-model-len` (maximum sequence length)
3. Enable chunked prefill
4. Scale horizontally (add more replicas)
5. Use larger GPU instances

Other vLLM metrics:
- `vllm:num_requests_running`: Current concurrent requests
- `vllm:num_requests_waiting`: Queue depth
- `vllm:time_to_first_token_seconds`: TTFT latency
- `vllm:gpu_prefix_cache_hit_rate`: Caching efficiency

</details>

### 15. What is the primary benefit of using placement groups with cluster strategy for distributed training?

A) Reduced EC2 instance costs
B) Automatic load balancing
C) Lowest network latency between nodes
D) Increased GPU memory

<details>
<summary>Show Answer</summary>

**Answer: C) Lowest network latency between nodes**

**Explanation:**
Cluster placement groups place instances physically close together within a single Availability Zone, minimizing network latency and maximizing bandwidth for inter-node communication.

Cluster placement group benefits:
1. **Lowest latency**: Instances on same network spine
2. **Maximum bandwidth**: Full bisection bandwidth available
3. **Consistent performance**: Reduced network jitter
4. **EFA optimization**: Best EFA performance requires cluster placement

Configuration:
```bash
# Create cluster placement group
aws ec2 create-placement-group \
  --group-name training-cluster-pg \
  --strategy cluster

# Karpenter configuration
apiVersion: karpenter.k8s.aws/v1
kind: EC2NodeClass
spec:
  tags:
    aws:ec2:placement-group: training-cluster-pg
```

Placement group strategies:

| Strategy | Use Case | Latency | Availability |
|----------|----------|---------|--------------|
| **Cluster** | **Distributed training** | **Lowest** | **Single AZ** |
| Spread | High availability | Higher | Multi-AZ |
| Partition | Large deployments | Medium | Multi-rack |

Why cluster strategy for training:
- NCCL all-reduce operations are latency-sensitive
- Gradient synchronization happens frequently (every batch)
- Even small latency increases compound across thousands of iterations
- P4d/P5 instances achieve best EFA performance in cluster placement

Trade-off: Cluster placement groups are limited to a single AZ, reducing availability. For training, this is acceptable because:
- Training jobs can checkpoint and restart
- Lower latency improves training time more than redundancy helps

</details>
