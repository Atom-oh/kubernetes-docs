# AI Infrastructure on EKS Quiz

This quiz tests your understanding of AI/ML infrastructure patterns on Amazon EKS, including the JARK Stack, Dynamic Resource Allocation, and production platforms for AI workloads.

## Quiz Questions

### 1. What does JARK Stack stand for in the context of AI/ML infrastructure on EKS?

A) Java, Ansible, Redis, Kafka
B) JupyterHub, Argo Workflows, Ray, Karpenter
C) Jenkins, Airflow, RabbitMQ, Kubernetes
D) JupyterLab, Apache Spark, Ray, Kubeflow

<details>
<summary>Show Answer</summary>

**Answer: B) JupyterHub, Argo Workflows, Ray, Karpenter**

**Explanation:**
The JARK Stack is a complete AI/ML development environment on EKS consisting of:

- **JupyterHub**: Multi-user interactive development environment with GPU-enabled notebook profiles
- **Argo Workflows**: ML pipeline orchestration with DAG-based workflows
- **Ray (KubeRay)**: Unified distributed computing for training, tuning, and serving
- **Karpenter**: Fast, cost-effective node provisioning with GPU and Neuron support

This stack provides everything needed for data scientists and ML engineers to develop, train, and deploy ML models on Kubernetes.

</details>

### 2. Which authentication method is commonly used with JupyterHub on EKS for enterprise environments?

A) Basic username/password stored in ConfigMaps
B) SSH key-based authentication
C) Amazon Cognito with OAuth
D) Kubernetes ServiceAccount tokens

<details>
<summary>Show Answer</summary>

**Answer: C) Amazon Cognito with OAuth**

**Explanation:**
Amazon Cognito with OAuth is the recommended authentication method for JupyterHub on EKS in enterprise environments because:

1. **Single Sign-On (SSO)**: Integrates with corporate identity providers (SAML, OIDC)
2. **Multi-factor Authentication**: Supports MFA for enhanced security
3. **User Management**: Centralized user management and access control
4. **Scalability**: Managed service that scales with your user base
5. **Compliance**: Helps meet security compliance requirements

Configuration example:
```python
c.JupyterHub.authenticator_class = 'oauthenticator.generic.GenericOAuthenticator'
c.GenericOAuthenticator.oauth_callback_url = 'https://jupyter.example.com/hub/oauth_callback'
c.GenericOAuthenticator.authorize_url = 'https://your-domain.auth.us-west-2.amazoncognito.com/oauth2/authorize'
```

</details>

### 3. In Ray on Kubernetes, what is the purpose of the Ray Head node?

A) To store all training data and model weights
B) To coordinate the cluster, run the dashboard, and manage worker scheduling
C) To perform all GPU computations exclusively
D) To handle external API requests only

<details>
<summary>Show Answer</summary>

**Answer: B) To coordinate the cluster, run the dashboard, and manage worker scheduling**

**Explanation:**
The Ray Head node serves as the central coordinator for the Ray cluster:

1. **Global Control Store (GCS)**: Manages cluster metadata and state
2. **Dashboard**: Runs the Ray dashboard for monitoring and debugging (port 8265)
3. **Client Connections**: Accepts connections from Ray clients (port 10001)
4. **Scheduling**: Coordinates task and actor scheduling across workers
5. **Autoscaling**: Works with KubeRay autoscaler to scale worker groups

The Head node typically does not run compute-intensive workloads itself - those are distributed to worker nodes based on resource requirements (CPU, GPU, memory).

```yaml
headGroupSpec:
  rayStartParams:
    dashboard-host: '0.0.0.0'
    block: 'true'
```

</details>

### 4. What is the primary advantage of Dynamic Resource Allocation (DRA) over traditional Kubernetes device plugins for GPU scheduling?

A) DRA is faster at detecting GPU hardware
B) DRA enables fine-grained GPU sharing (MIG, MPS, time-slicing) and topology-aware scheduling
C) DRA requires less memory overhead
D) DRA only works with NVIDIA GPUs

<details>
<summary>Show Answer</summary>

**Answer: B) DRA enables fine-grained GPU sharing (MIG, MPS, time-slicing) and topology-aware scheduling**

**Explanation:**
Dynamic Resource Allocation (DRA) provides capabilities that traditional device plugins cannot offer:

| Feature | Traditional Device Plugin | DRA |
|---------|--------------------------|-----|
| GPU Allocation | Whole GPU only | Fractional (MIG, MPS, time-slice) |
| Topology Awareness | Limited | NVLink/IMEX aware |
| Sharing Modes | Basic time-slicing | MIG, MPS, time-slicing, exclusive |
| Resource Claims | Static | Dynamic with constraints |
| Multi-GPU Scheduling | Independent | Topology-constrained |

DRA uses ResourceClaims and ResourceSlices to provide:
- Fine-grained GPU memory partitioning (MIG profiles like 3g.20gb)
- CUDA context sharing via MPS
- Time-slicing for development workloads
- Topology-aware scheduling for NVLink-connected GPUs

This is essential for P6e-GB200 UltraServers with 72 interconnected GPUs.

</details>

### 5. Which GPU sharing strategy provides the strongest isolation between workloads?

A) Time-Slicing
B) MPS (Multi-Process Service)
C) MIG (Multi-Instance GPU)
D) Exclusive mode

<details>
<summary>Show Answer</summary>

**Answer: C) MIG (Multi-Instance GPU)**

**Explanation:**
Among the GPU sharing strategies, MIG provides the strongest isolation while still allowing sharing:

| Strategy | Isolation Level | How It Works |
|----------|----------------|--------------|
| **Exclusive** | Full (no sharing) | One workload per GPU |
| **MIG** | Strong (hardware) | Hardware-partitioned GPU instances |
| **MPS** | Medium | Shared CUDA context with thread limits |
| **Time-Slicing** | Weak | Context switching between workloads |

MIG (available on A100/H100 GPUs) provides:
- **Hardware Isolation**: Each MIG instance has dedicated SM units, memory, and cache
- **Fault Isolation**: Errors in one instance don't affect others
- **QoS Guarantees**: Predictable performance per instance
- **Memory Protection**: Separate memory spaces prevent data leakage

Example MIG profiles for A100 80GB:
- `7g.80gb` - Full GPU
- `3g.40gb` - Half GPU (2 instances)
- `1g.10gb` - 1/7 GPU (7 instances)

</details>

### 6. What is the minimum NVIDIA GPU Operator version required for full DRA support?

A) v22.9.0
B) v23.6.0
C) v24.3.0
D) v25.3.0

<details>
<summary>Show Answer</summary>

**Answer: D) v25.3.0**

**Explanation:**
NVIDIA GPU Operator v25.3.0 or later is required for full Dynamic Resource Allocation (DRA) support. This version includes:

1. **DRA Driver**: Native DRA driver for GPU resource management
2. **ResourceSlice Support**: Exposes GPU topology information
3. **Sharing Configuration**: MIG, MPS, and time-slicing via DRA
4. **CEL Expressions**: Device selection using Common Expression Language

Configuration with DRA enabled:
```yaml
draDriver:
  enabled: true
  version: "v0.1.0"
  config:
    sharing:
      mps:
        enabled: true
      timeSlicing:
        enabled: true
      mig:
        enabled: true
        strategy: mixed
```

Earlier versions only support traditional device plugin mode without the fine-grained control DRA provides.

</details>

### 7. In the Agents on EKS platform, what is the purpose of Langfuse?

A) Vector database for storing embeddings
B) Source control and CI/CD pipelines
C) LLM observability, tracing, and monitoring
D) Tool discovery and registration

<details>
<summary>Show Answer</summary>

**Answer: C) LLM observability, tracing, and monitoring**

**Explanation:**
Langfuse is an open-source LLM observability platform that provides:

1. **Tracing**: End-to-end traces of LLM interactions
2. **Prompt Management**: Version and manage prompts
3. **Evaluation**: Score and evaluate LLM outputs
4. **Analytics**: Usage metrics, latency, and cost tracking
5. **Debugging**: Identify issues in LLM chains and agents

In the Agents on EKS platform architecture:
- **GitLab**: Source control and CI/CD
- **Langfuse**: LLM observability and tracing
- **Milvus**: Vector database for RAG
- **MCP Gateway**: Tool discovery and registration

Integration example:
```python
from langfuse import Langfuse

langfuse = Langfuse(
    public_key="pk-xxx",
    secret_key="sk-xxx",
    host="https://langfuse.agents.example.com"
)

# Trace LLM calls
trace = langfuse.trace(name="customer-support-agent")
```

</details>

### 8. Which storage solution is recommended for high-throughput distributed training workloads on EKS?

A) Amazon EBS gp3 volumes
B) Amazon EFS with standard performance mode
C) Amazon FSx for Lustre
D) Amazon S3 with Mountpoint

<details>
<summary>Show Answer</summary>

**Answer: C) Amazon FSx for Lustre**

**Explanation:**
Amazon FSx for Lustre is the recommended storage solution for high-throughput distributed training because:

1. **High Throughput**: Up to 1000+ MB/s per TiB of storage
2. **Low Latency**: Sub-millisecond latencies for metadata operations
3. **S3 Integration**: Native data repository integration with S3
4. **Parallel Access**: Optimized for parallel file system workloads
5. **POSIX Compliance**: Full POSIX support for ML frameworks

Storage comparison for AI/ML:

| Storage | Throughput | Use Case |
|---------|------------|----------|
| EFS | Up to 10 GB/s | Shared notebooks, model storage |
| FSx Lustre | Up to 1+ TB/s | Distributed training, HPC |
| S3 + Mountpoint | Variable | Cold data, checkpoints |
| EBS gp3 | 1 GB/s max | Single-node workloads |

FSx for Lustre configuration:
```yaml
parameters:
  deploymentType: PERSISTENT_2
  perUnitStorageThroughput: "500"  # MB/s per TiB
  dataCompressionType: LZ4
  s3ImportPath: s3://ml-datasets
```

</details>

### 9. What is EFA (Elastic Fabric Adapter) used for in AI/ML workloads?

A) Encrypting data at rest on GPU nodes
B) High-bandwidth, low-latency networking for multi-node distributed training
C) Managing GPU memory allocation
D) Authenticating workloads to external services

<details>
<summary>Show Answer</summary>

**Answer: B) High-bandwidth, low-latency networking for multi-node distributed training**

**Explanation:**
Elastic Fabric Adapter (EFA) is AWS's high-performance network interface for HPC and ML workloads:

1. **High Bandwidth**: Up to 3200 Gbps (trn1n.32xlarge with 16x EFA)
2. **Low Latency**: Consistent low-latency for collective operations
3. **OS Bypass**: Direct hardware access bypassing the kernel
4. **NCCL Integration**: Optimized for NVIDIA Collective Communications Library

EFA-supported instances for AI/ML:
- `p4d.24xlarge`: 4x 400 Gbps EFA
- `p5.48xlarge`: 32x 400 Gbps EFA
- `trn1.32xlarge`: 8x 800 Gbps EFA
- `trn1n.32xlarge`: 16x 1600 Gbps EFA

Environment variables for EFA with NCCL:
```yaml
env:
- name: FI_PROVIDER
  value: "efa"
- name: FI_EFA_USE_DEVICE_RDMA
  value: "1"
- name: NCCL_ALGO
  value: "Ring,Tree"
```

Resource request:
```yaml
resources:
  limits:
    vpc.amazonaws.com/efa: 4
```

</details>

### 10. Which Prometheus metric indicates GPU memory exhaustion that requires immediate attention?

A) DCGM_FI_DEV_GPU_UTIL > 80
B) DCGM_FI_DEV_GPU_TEMP > 70
C) DCGM_FI_DEV_FB_USED / (DCGM_FI_DEV_FB_USED + DCGM_FI_DEV_FB_FREE) > 0.95
D) DCGM_FI_DEV_SM_CLOCK < 1000

<details>
<summary>Show Answer</summary>

**Answer: C) DCGM_FI_DEV_FB_USED / (DCGM_FI_DEV_FB_USED + DCGM_FI_DEV_FB_FREE) > 0.95**

**Explanation:**
This metric calculates GPU frame buffer (memory) utilization percentage. When it exceeds 95%, the GPU is nearly out of memory:

Key DCGM metrics for GPU monitoring:

| Metric | Description | Critical Threshold |
|--------|-------------|-------------------|
| `DCGM_FI_DEV_FB_USED` | Used frame buffer memory | - |
| `DCGM_FI_DEV_FB_FREE` | Free frame buffer memory | - |
| `DCGM_FI_DEV_GPU_UTIL` | GPU compute utilization | <20% (underutilized) |
| `DCGM_FI_DEV_GPU_TEMP` | GPU temperature | >85C (overheating) |
| `DCGM_FI_DEV_XID_ERRORS` | Hardware error count | >0 (hardware issue) |

Alert rule for memory exhaustion:
```yaml
- alert: GPUMemoryExhausted
  expr: (DCGM_FI_DEV_FB_USED / (DCGM_FI_DEV_FB_USED + DCGM_FI_DEV_FB_FREE)) * 100 > 95
  for: 5m
  labels:
    severity: critical
  annotations:
    summary: "GPU memory nearly exhausted"
```

Memory exhaustion causes:
- OOM (Out of Memory) errors
- Training job failures
- Inference request rejections

</details>

### 11. What is the purpose of Karpenter's consolidation feature for GPU workloads?

A) To merge multiple GPUs into a single virtual GPU
B) To combine training checkpoints into a single file
C) To bin-pack workloads and remove underutilized nodes for cost savings
D) To consolidate logs from multiple GPU pods

<details>
<summary>Show Answer</summary>

**Answer: C) To bin-pack workloads and remove underutilized nodes for cost savings**

**Explanation:**
Karpenter's consolidation feature optimizes cluster costs by:

1. **Bin-Packing**: Moving workloads to fewer, more utilized nodes
2. **Node Removal**: Terminating empty or underutilized nodes
3. **Right-Sizing**: Replacing nodes with more appropriate instance types
4. **Cost Reduction**: Minimizing idle GPU resources

Consolidation policies:
```yaml
disruption:
  consolidationPolicy: WhenEmptyOrUnderutilized
  consolidateAfter: 5m
```

- **WhenEmpty**: Only consolidate completely empty nodes
- **WhenEmptyOrUnderutilized**: Consolidate empty or underused nodes

For GPU workloads, consolidation is critical because:
- GPU instances are expensive ($3-30+/hour)
- Underutilized GPUs waste significant cost
- Training jobs often complete, leaving idle nodes

Best practices:
- Use shorter `consolidateAfter` for development (5m)
- Use longer periods for production training (30m)
- Set appropriate `limits` to prevent runaway scaling

</details>

### 12. In DRA, what is a ResourceSlice used for?

A) To divide CPU resources among containers
B) To represent available GPU resources and their topology on a node
C) To slice network bandwidth for different workloads
D) To partition storage volumes

<details>
<summary>Show Answer</summary>

**Answer: B) To represent available GPU resources and their topology on a node**

**Explanation:**
ResourceSlice is a DRA resource that represents available devices and their topology:

```yaml
apiVersion: resource.k8s.io/v1alpha3
kind: ResourceSlice
metadata:
  name: gb200-nvl72-node-1
spec:
  nodeName: p6e-gb200-node-1
  pool:
    name: gb200-pool
    generation: 1
    resourceSliceCount: 1
  driver: gpu.nvidia.com
  devices:
  - name: gpu-0
    basic:
      attributes:
        gpu.nvidia.com/product: "NVIDIA-GB200"
        gpu.nvidia.com/memory: "192Gi"
        gpu.nvidia.com/nvlink.version: "5.0"
        gpu.nvidia.com/nvswitch.connected: "true"
```

ResourceSlice provides:
1. **Device Inventory**: Lists all available devices on a node
2. **Attributes**: GPU model, memory, capabilities
3. **Topology Information**: NVLink connections, NUMA node, NVSwitch
4. **Capacity**: Available resources for scheduling

The scheduler uses ResourceSlices to:
- Find nodes with required GPU types
- Schedule topology-aware multi-GPU workloads
- Ensure NVLink-connected GPUs are allocated together

</details>

### 13. Which component in the Agents on EKS platform provides vector storage for RAG (Retrieval-Augmented Generation)?

A) GitLab
B) Langfuse
C) Milvus
D) MCP Gateway

<details>
<summary>Show Answer</summary>

**Answer: C) Milvus**

**Explanation:**
Milvus is an open-source vector database optimized for AI applications:

1. **Vector Storage**: Stores high-dimensional embedding vectors
2. **Similarity Search**: Fast approximate nearest neighbor (ANN) search
3. **GPU Acceleration**: Query and index nodes can use GPUs
4. **Scalability**: Distributed architecture for large-scale deployments

RAG architecture with Milvus:
```
User Query → Embedding Model → Milvus (vector search) → Retrieved Context → LLM → Response
```

Milvus configuration on EKS:
```yaml
queryNode:
  replicas: 2
  resources:
    requests:
      nvidia.com/gpu: "1"  # GPU-accelerated search

indexNode:
  replicas: 2
  resources:
    requests:
      nvidia.com/gpu: "1"  # GPU-accelerated indexing
```

Agent integration:
```python
from pymilvus import connections, Collection

connections.connect(host="milvus.milvus.svc.cluster.local", port="19530")
collection = Collection("knowledge_base")

# Search for similar documents
results = collection.search(
    data=[query_embedding],
    anns_field="embedding",
    param={"metric_type": "IP", "params": {"nprobe": 10}},
    limit=5
)
```

</details>

### 14. What is the recommended approach for handling GPU node failures during distributed training?

A) Manually restart the training from scratch
B) Use checkpointing with fault-tolerant training frameworks like Ray Train
C) Increase the number of GPU replicas to prevent failures
D) Use only on-demand instances to avoid interruptions

<details>
<summary>Show Answer</summary>

**Answer: B) Use checkpointing with fault-tolerant training frameworks like Ray Train**

**Explanation:**
Checkpointing with fault-tolerant frameworks is the recommended approach because:

1. **Automatic Recovery**: Training resumes from the last checkpoint
2. **Cost Efficiency**: Enables use of cheaper Spot instances
3. **Scalability**: Handles dynamic cluster size changes
4. **Progress Preservation**: Minimizes lost compute time

Ray Train with checkpointing:
```python
from ray.train.torch import TorchTrainer
from ray.train import Checkpoint, ScalingConfig

def train_loop_per_worker():
    # Load from checkpoint if available
    checkpoint = ray.train.get_checkpoint()
    if checkpoint:
        with checkpoint.as_directory() as checkpoint_dir:
            model.load_state_dict(torch.load(f"{checkpoint_dir}/model.pt"))

    for epoch in range(epochs):
        # Training logic
        train_epoch()

        # Save checkpoint
        with tempfile.TemporaryDirectory() as temp_dir:
            torch.save(model.state_dict(), f"{temp_dir}/model.pt")
            ray.train.report(
                {"loss": loss},
                checkpoint=Checkpoint.from_directory(temp_dir)
            )

trainer = TorchTrainer(
    train_loop_per_worker,
    scaling_config=ScalingConfig(
        num_workers=4,
        use_gpu=True,
    ),
    run_config=ray.train.RunConfig(
        checkpoint_config=ray.train.CheckpointConfig(
            num_to_keep=3,
            checkpoint_frequency=10,
        )
    )
)
```

</details>

### 15. What is the purpose of the MCP Gateway in the Agents on EKS platform?

A) To route traffic between microservices
B) To manage container image registries
C) To provide tool discovery and registration for AI agents
D) To encrypt communication between pods

<details>
<summary>Show Answer</summary>

**Answer: C) To provide tool discovery and registration for AI agents**

**Explanation:**
MCP (Model Context Protocol) Gateway provides tool discovery and management for AI agents:

1. **Tool Registry**: Central registry of available tools/functions
2. **Discovery**: Automatic discovery of tools in Kubernetes
3. **Routing**: Routes tool calls to appropriate backends
4. **Authentication**: OIDC-based access control
5. **Rate Limiting**: Prevents tool abuse

MCP Gateway configuration:
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: mcp-gateway-config
data:
  config.yaml: |
    registry:
      type: kubernetes
      kubernetes:
        namespace: mcp-tools
        label_selector: "mcp.anthropic.com/tool=true"

    discovery:
      enabled: true
      interval: 30s
      endpoints:
      - name: kubernetes
        type: kubernetes
        config:
          namespaces: ["mcp-tools", "ai-agents"]
```

Agent integration:
```python
# Agent discovers and uses tools via MCP Gateway
env:
- name: MCP_GATEWAY_URL
  value: "http://mcp-gateway.mcp-gateway.svc.cluster.local:8080"
```

MCP enables agents to:
- Discover available tools dynamically
- Call external APIs and services
- Access databases and file systems
- Execute code and commands

</details>

---

## Summary

This quiz covered key concepts in AI infrastructure on EKS:

- **JARK Stack**: JupyterHub + Argo Workflows + Ray + Karpenter for complete ML environments
- **Dynamic Resource Allocation**: Fine-grained GPU scheduling with MIG, MPS, and time-slicing
- **Agents Platform**: GitLab + Langfuse + Milvus + MCP Gateway for AI agent development
- **Storage**: EFS for sharing, FSx Lustre for high-throughput training
- **Networking**: EFA for multi-node distributed training
- **Monitoring**: DCGM metrics and Prometheus alerts for GPU observability

For more details, refer to the [AI Infrastructure on EKS](../../ai-ml/06-ai-infrastructure.md) documentation.
