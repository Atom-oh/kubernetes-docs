# EKS Hybrid Nodes GPU Integration Quiz

> **Related Document**: [GPU Integration](../../eks-hybrid-nodes/05-gpu-integration.md)

## Multiple Choice Questions

### 1. What is the key characteristic of NVIDIA GPU Multi-Instance GPU (MIG) technology?

A. Combines multiple GPUs into one
B. Splits a single GPU into multiple physically isolated instances
C. Only shares GPU memory
D. Software-level time-slicing

<details>
<summary>Show Answer</summary>

**Answer: B. Splits a single GPU into multiple physically isolated instances**

**Explanation:**
MIG (Multi-Instance GPU) partitions GPUs like NVIDIA A100 and H100 into up to 7 physically isolated instances. Each instance has independent memory, cache, and compute resources.

**MIG vs Time-Slicing Comparison:**

| Feature | MIG | Time-Slicing |
|---------|-----|--------------|
| Isolation Level | Physical (complete isolation) | Time-based (software) |
| Memory Isolation | Complete isolation | Shared |
| Supported GPUs | A100, H100 | All NVIDIA GPUs |
| QoS Guarantee | Yes | No |

```yaml
# MIG Resource Request
apiVersion: v1
kind: Pod
metadata:
  name: gpu-pod
spec:
  containers:
  - name: cuda-app
    image: nvidia/cuda:12.0-runtime
    resources:
      limits:
        nvidia.com/mig-1g.5gb: 1
```

</details>

### 2. What does "1g.5gb" mean in NVIDIA GPU MIG configuration?

A. 1GB memory, 5 GPU cores
B. 1 GPU Instance (1 compute slice), 5GB GPU memory
C. 1 GPU, 5GB system memory
D. 1 second per 5GB throughput

<details>
<summary>Show Answer</summary>

**Answer: B. 1 GPU Instance (1 compute slice), 5GB GPU memory**

**Explanation:**
MIG instance name format: `<compute-slices>g.<memory-size>gb`

- **1g**: 1 compute slice
- **5gb**: 5GB GPU memory

**A100 MIG Profile Examples:**
- `1g.5gb`: 1 compute slice, 5GB memory (max 7)
- `2g.10gb`: 2 compute slices, 10GB memory (max 3)
- `3g.20gb`: 3 compute slices, 20GB memory (max 2)
- `4g.40gb`: 4 compute slices, 40GB memory (max 1)
- `7g.40gb`: 7 compute slices, 40GB memory (full GPU)

```bash
# Check MIG instances
nvidia-smi mig -lgi
```

</details>

### 3. What is the expected behavior when oversubscription occurs in GPU Time-Slicing?

A. Complete GPU task failure
B. Performance degradation due to context switching
C. Automatic GPU addition
D. Automatic memory expansion

<details>
<summary>Show Answer</summary>

**Answer: B. Performance degradation due to context switching**

**Explanation:**
Time-Slicing allows multiple workloads to share a single GPU on a time-division basis. When oversubscription occurs, frequent context switching causes performance degradation.

```yaml
# GPU Time-Slicing Configuration
apiVersion: v1
kind: ConfigMap
metadata:
  name: device-plugin-config
  namespace: nvidia-device-plugin
data:
  config.yaml: |
    version: v1
    sharing:
      timeSlicing:
        resources:
        - name: nvidia.com/gpu
          replicas: 4  # Split 1 GPU into 4
```

**Time-Slicing Considerations:**
- Memory is shared, so OOM can occur
- Suitable for inference workloads
- MIG or dedicated GPUs recommended for training
- Proper replicas count setting is important

</details>

### 4. What is the main advantage of Dynamic Resource Allocation (DRA)?

A. Only supports static resource allocation
B. Supports all devices without vendor-specific plugins
C. Flexible request/allocation mechanism for custom resources
D. Only manages CPU and memory

<details>
<summary>Show Answer</summary>

**Answer: C. Flexible request/allocation mechanism for custom resources**

**Explanation:**
DRA (Dynamic Resource Allocation), introduced in Kubernetes 1.26, provides a more flexible request and allocation mechanism for custom resources like GPUs, FPGAs, and network devices.

**Core DRA Components:**
- **ResourceClass**: Defines resource types provided by drivers
- **ResourceClaim**: Request for resources
- **ResourceClaimTemplate**: Reusable claim template

```yaml
# Using DRA in Pod
apiVersion: v1
kind: Pod
metadata:
  name: gpu-workload
spec:
  containers:
  - name: cuda-app
    resources:
      claims:
      - name: gpu
  resourceClaims:
  - name: gpu
    source:
      resourceClaimTemplateName: gpu-claim-template
```

</details>

### 5. What condition must be met for a ResourceClaim status to become "Bound" in DRA (Dynamic Resource Allocation)?

A. Claim creation only
B. Driver allocates resources and Pod is scheduled
C. Pod terminates
D. Claim is deleted

<details>
<summary>Show Answer</summary>

**Answer: B. Driver allocates resources and Pod is scheduled**

**Explanation:**
ResourceClaim status flow:

1. **Pending**: Claim created, not yet allocated
2. **Allocated**: Driver completed resource allocation
3. **Bound**: Bound to Pod and in use

```yaml
# Check ResourceClaim Status
kubectl get resourceclaim gpu-claim -o yaml

# Expected output
status:
  allocation:
    resourceHandles:
    - driverName: gpu.nvidia.com
      data: '{"gpu":"GPU-abc123"}'
  reservedFor:
  - name: gpu-workload
    uid: xxx-xxx-xxx
```

</details>

### 6. What is the main role of NVIDIA GPU Operator?

A. GPU hardware manufacturing
B. Automatic management of GPU drivers, runtimes, and plugins in Kubernetes
C. GPU performance testing only
D. GPU purchase and delivery management

<details>
<summary>Show Answer</summary>

**Answer: B. Automatic management of GPU drivers, runtimes, and plugins in Kubernetes**

**Explanation:**
NVIDIA GPU Operator automatically manages GPU infrastructure in Kubernetes:

- NVIDIA driver installation/updates
- NVIDIA Container Toolkit installation
- NVIDIA Device Plugin deployment
- GPU monitoring (DCGM Exporter)
- MIG management

```bash
# Install GPU Operator (Helm)
helm repo add nvidia https://helm.ngc.nvidia.com/nvidia
helm install gpu-operator nvidia/gpu-operator \
  --namespace gpu-operator \
  --create-namespace
```

```yaml
# GPU Operator Custom Configuration
apiVersion: nvidia.com/v1
kind: ClusterPolicy
metadata:
  name: cluster-policy
spec:
  driver:
    enabled: true
    version: "535.104.12"
  toolkit:
    enabled: true
  devicePlugin:
    enabled: true
  mig:
    strategy: mixed
```

</details>

### 7. What is the main difference between H100 and H200 GPUs?

A. H200 has less memory capacity than H100
B. H200 provides HBM3e memory with higher bandwidth than H100
C. H200 does not support MIG
D. H200 is not for data centers

<details>
<summary>Show Answer</summary>

**Answer: B. H200 provides HBM3e memory with higher bandwidth than H100**

**Explanation:**
H200 is the successor to H100, providing an improved memory system:

| Feature | H100 | H200 |
|---------|------|------|
| Memory Type | HBM3 | HBM3e |
| Memory Capacity | 80GB | 141GB |
| Memory Bandwidth | 3.35TB/s | 4.8TB/s |
| MIG Support | Yes (up to 7) | Yes (up to 7) |
| LLM Inference | Excellent | Optimized |

```yaml
# H200 Node Selection
apiVersion: v1
kind: Pod
spec:
  nodeSelector:
    nvidia.com/gpu.product: "NVIDIA-H200"
  containers:
  - name: llm
    resources:
      limits:
        nvidia.com/gpu: 1
```

H200 shows excellent performance especially in large language model (LLM) inference due to its memory capacity and bandwidth.

</details>

