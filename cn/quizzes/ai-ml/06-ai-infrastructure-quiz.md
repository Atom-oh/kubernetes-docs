# EKS 上的 AI 基础设施测验

本测验用于检验你对 Amazon EKS 上 AI/ML 基础设施模式的理解，包括 JARK Stack、Dynamic Resource Allocation，以及用于 AI workloads 的生产平台。

## 测验问题

### 1. 在 EKS 上的 AI/ML 基础设施语境中，JARK Stack 代表什么？

A) Java, Ansible, Redis, Kafka
B) JupyterHub, Argo Workflows, Ray, Karpenter
C) Jenkins, Airflow, RabbitMQ, Kubernetes
D) JupyterLab, Apache Spark, Ray, Kubeflow

<details>
<summary>显示答案</summary>

**答案： B) JupyterHub, Argo Workflows, Ray, Karpenter**

**解释：**
JARK Stack 是 EKS 上完整的 AI/ML 开发环境，包括：

- **JupyterHub**：支持 GPU 的 notebook 配置文件的多用户交互式开发环境
- **Argo Workflows**：基于 DAG 的 workflows 的 ML pipeline 编排
- **Ray (KubeRay)**：用于训练、调优和服务的统一分布式计算
- **Karpenter**：支持 GPU 和 Neuron 的快速、具成本效益的 node 预置

该 stack 提供了数据科学家和 ML 工程师在 Kubernetes 上开发、训练和部署 ML models 所需的一切。

</details>

### 2. 在企业环境中，JupyterHub on EKS 常用哪种身份验证方法？

A) 存储在 ConfigMaps 中的基本用户名/密码
B) 基于 SSH key 的身份验证
C) Amazon Cognito with OAuth
D) Kubernetes ServiceAccount tokens

<details>
<summary>显示答案</summary>

**答案： C) Amazon Cognito with OAuth**

**解释：**
Amazon Cognito with OAuth 是企业环境中 JupyterHub on EKS 推荐的身份验证方法，原因包括：

1. **Single Sign-On (SSO)**：与企业 identity providers（SAML、OIDC）集成
2. **Multi-factor Authentication**：支持 MFA 以增强安全性
3. **User Management**：集中式用户管理和访问控制
4. **Scalability**：可随用户群扩展的托管服务
5. **Compliance**：有助于满足安全合规要求

配置示例：
```python
c.JupyterHub.authenticator_class = 'oauthenticator.generic.GenericOAuthenticator'
c.GenericOAuthenticator.oauth_callback_url = 'https://jupyter.example.com/hub/oauth_callback'
c.GenericOAuthenticator.authorize_url = 'https://your-domain.auth.us-west-2.amazoncognito.com/oauth2/authorize'
```

</details>

### 3. 在 Kubernetes 上的 Ray 中，Ray Head node 的用途是什么？

A) 存储所有训练数据和 model weights
B) 协调 cluster、运行 dashboard，并管理 worker 调度
C) 专门执行所有 GPU 计算
D) 仅处理外部 API requests

<details>
<summary>显示答案</summary>

**答案： B) 协调 cluster、运行 dashboard，并管理 worker 调度**

**解释：**
Ray Head node 作为 Ray cluster 的中央协调器：

1. **Global Control Store (GCS)**：管理 cluster metadata 和 state
2. **Dashboard**：运行 Ray dashboard 以进行监控和调试（port 8265）
3. **Client Connections**：接受来自 Ray clients 的连接（port 10001）
4. **Scheduling**：协调 workers 之间的 task 和 actor 调度
5. **Autoscaling**：与 KubeRay autoscaler 配合扩展 worker groups

Head node 通常不会自行运行计算密集型 workloads，这些 workloads 会根据 resource requirements（CPU、GPU、memory）分发到 worker nodes。

```yaml
headGroupSpec:
  rayStartParams:
    dashboard-host: '0.0.0.0'
    block: 'true'
```

</details>

### 4. 与传统 Kubernetes device plugins 相比，Dynamic Resource Allocation (DRA) 在 GPU 调度方面的主要优势是什么？

A) DRA 检测 GPU 硬件更快
B) DRA 支持细粒度 GPU 共享（MIG、MPS、time-slicing）和拓扑感知调度
C) DRA 需要更少的内存开销
D) DRA 仅适用于 NVIDIA GPUs

<details>
<summary>显示答案</summary>

**答案： B) DRA 支持细粒度 GPU 共享（MIG、MPS、time-slicing）和拓扑感知调度**

**解释：**
Dynamic Resource Allocation (DRA) 提供了传统 device plugins 无法提供的能力：

| 功能 | 传统 Device Plugin | DRA |
|---------|--------------------------|-----|
| GPU 分配 | 仅整块 GPU | 分数化（MIG、MPS、time-slice） |
| 拓扑感知 | 有限 | 感知 NVLink/IMEX |
| 共享模式 | 基本 time-slicing | MIG、MPS、time-slicing、exclusive |
| Resource Claims | 静态 | 带约束的动态分配 |
| Multi-GPU 调度 | 独立 | 受拓扑约束 |

DRA 使用 ResourceClaims 和 ResourceSlices 来提供：
- 细粒度 GPU memory 分区（MIG profiles，如 3g.20gb）
- 通过 MPS 共享 CUDA context
- 用于开发 workloads 的 time-slicing
- 用于 NVLink 连接 GPUs 的拓扑感知调度

这对于拥有 72 个互联 GPUs 的 P6e-GB200 UltraServers 至关重要。

</details>

### 5. 哪种 GPU 共享策略在 workloads 之间提供最强隔离？

A) Time-Slicing
B) MPS (Multi-Process Service)
C) MIG (Multi-Instance GPU)
D) Exclusive mode

<details>
<summary>显示答案</summary>

**答案： C) MIG (Multi-Instance GPU)**

**解释：**
在 GPU 共享策略中，MIG 在允许共享的同时提供最强隔离：

| 策略 | 隔离级别 | 工作方式 |
|----------|----------------|--------------|
| **Exclusive** | 完全（不共享） | 每块 GPU 一个 workload |
| **MIG** | 强（硬件） | 硬件分区的 GPU instances |
| **MPS** | 中等 | 带 thread limits 的共享 CUDA context |
| **Time-Slicing** | 弱 | workloads 之间进行 context switching |

MIG（适用于 A100/H100 GPUs）提供：
- **Hardware Isolation**：每个 MIG instance 都有专用的 SM units、memory 和 cache
- **Fault Isolation**：一个 instance 中的错误不会影响其他 instance
- **QoS Guarantees**：每个 instance 具有可预测的性能
- **Memory Protection**：独立的 memory spaces 防止数据泄露

A100 80GB 的 MIG profiles 示例：
- `7g.80gb` - 完整 GPU
- `3g.40gb` - 半块 GPU（2 个 instances）
- `1g.10gb` - 1/7 GPU（7 个 instances）

</details>

### 6. 完整 DRA 支持所需的最低 NVIDIA GPU Operator 版本是什么？

A) v22.9.0
B) v23.6.0
C) v24.3.0
D) v25.3.0

<details>
<summary>显示答案</summary>

**答案： D) v25.3.0**

**解释：**
完整的 Dynamic Resource Allocation (DRA) 支持需要 NVIDIA GPU Operator v25.3.0 或更高版本。此版本包括：

1. **DRA Driver**：用于 GPU resource management 的原生 DRA driver
2. **ResourceSlice Support**：公开 GPU topology information
3. **Sharing Configuration**：通过 DRA 配置 MIG、MPS 和 time-slicing
4. **CEL Expressions**：使用 Common Expression Language 选择 device

启用 DRA 的配置：
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

早期版本仅支持传统 device plugin 模式，不具备 DRA 提供的细粒度控制。

</details>

### 7. 在 Agents on EKS 平台中，Langfuse 的用途是什么？

A) 用于存储 embeddings 的 vector database
B) Source control 和 CI/CD pipelines
C) LLM observability、tracing 和 monitoring
D) Tool discovery 和 registration

<details>
<summary>显示答案</summary>

**答案： C) LLM observability、tracing 和 monitoring**

**解释：**
Langfuse 是一个开源 LLM observability platform，提供：

1. **Tracing**：LLM interactions 的端到端 traces
2. **Prompt Management**：对 prompts 进行版本控制和管理
3. **Evaluation**：对 LLM outputs 进行评分和评估
4. **Analytics**：使用指标、latency 和 cost tracking
5. **Debugging**：识别 LLM chains 和 agents 中的问题

在 Agents on EKS 平台架构中：
- **GitLab**：Source control 和 CI/CD
- **Langfuse**：LLM observability 和 tracing
- **Milvus**：用于 RAG 的 vector database
- **MCP Gateway**：Tool discovery 和 registration

集成示例：
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

### 8. 对于 EKS 上高吞吐量 distributed training workloads，推荐哪种存储解决方案？

A) Amazon EBS gp3 volumes
B) 采用 standard performance mode 的 Amazon EFS
C) Amazon FSx for Lustre
D) Amazon S3 with Mountpoint

<details>
<summary>显示答案</summary>

**答案： C) Amazon FSx for Lustre**

**解释：**
Amazon FSx for Lustre 是高吞吐量 distributed training 的推荐存储解决方案，原因包括：

1. **High Throughput**：每 TiB storage 可达 1000+ MB/s
2. **Low Latency**：metadata operations 的亚毫秒级延迟
3. **S3 Integration**：与 S3 的原生 data repository integration
4. **Parallel Access**：针对 parallel file system workloads 优化
5. **POSIX Compliance**：为 ML frameworks 提供完整 POSIX 支持

AI/ML 的存储比较：

| 存储 | 吞吐量 | 使用场景 |
|---------|------------|----------|
| EFS | 最高 10 GB/s | 共享 notebooks、model storage |
| FSx Lustre | 最高 1+ TB/s | Distributed training、HPC |
| S3 + Mountpoint | 可变 | 冷数据、checkpoints |
| EBS gp3 | 最高 1 GB/s | Single-node workloads |

FSx for Lustre 配置：
```yaml
parameters:
  deploymentType: PERSISTENT_2
  perUnitStorageThroughput: "500"  # MB/s per TiB
  dataCompressionType: LZ4
  s3ImportPath: s3://ml-datasets
```

</details>

### 9. EFA (Elastic Fabric Adapter) 在 AI/ML workloads 中用于什么？

A) 加密 GPU nodes 上的静态数据
B) 用于 multi-node distributed training 的高带宽、低延迟网络
C) 管理 GPU memory allocation
D) 对 workloads 到外部服务的访问进行身份验证

<details>
<summary>显示答案</summary>

**答案： B) 用于 multi-node distributed training 的高带宽、低延迟网络**

**解释：**
Elastic Fabric Adapter (EFA) 是 AWS 面向 HPC 和 ML workloads 的高性能 network interface：

1. **High Bandwidth**：最高可达 3200 Gbps（带 16x EFA 的 trn1n.32xlarge）
2. **Low Latency**：为 collective operations 提供一致的低延迟
3. **OS Bypass**：绕过 kernel 的直接硬件访问
4. **NCCL Integration**：针对 NVIDIA Collective Communications Library 优化

支持 EFA 的 AI/ML instances：
- `p4d.24xlarge`: 4x 400 Gbps EFA
- `p5.48xlarge`: 32x 400 Gbps EFA
- `trn1.32xlarge`: 8x 800 Gbps EFA
- `trn1n.32xlarge`: 16x 1600 Gbps EFA

EFA 与 NCCL 配合使用的环境变量：
```yaml
env:
- name: FI_PROVIDER
  value: "efa"
- name: FI_EFA_USE_DEVICE_RDMA
  value: "1"
- name: NCCL_ALGO
  value: "Ring,Tree"
```

Resource request：
```yaml
resources:
  limits:
    vpc.amazonaws.com/efa: 4
```

</details>

### 10. 哪个 Prometheus metric 表示需要立即关注的 GPU memory exhaustion？

A) DCGM_FI_DEV_GPU_UTIL > 80
B) DCGM_FI_DEV_GPU_TEMP > 70
C) DCGM_FI_DEV_FB_USED / (DCGM_FI_DEV_FB_USED + DCGM_FI_DEV_FB_FREE) > 0.95
D) DCGM_FI_DEV_SM_CLOCK < 1000

<details>
<summary>显示答案</summary>

**答案： C) DCGM_FI_DEV_FB_USED / (DCGM_FI_DEV_FB_USED + DCGM_FI_DEV_FB_FREE) > 0.95**

**解释：**
此 metric 计算 GPU frame buffer（memory）utilization 百分比。当它超过 95% 时，GPU 几乎耗尽内存：

用于 GPU monitoring 的关键 DCGM metrics：

| Metric | 描述 | 临界阈值 |
|--------|-------------|-------------------|
| `DCGM_FI_DEV_FB_USED` | 已用 frame buffer memory | - |
| `DCGM_FI_DEV_FB_FREE` | 空闲 frame buffer memory | - |
| `DCGM_FI_DEV_GPU_UTIL` | GPU compute utilization | <20%（利用不足） |
| `DCGM_FI_DEV_GPU_TEMP` | GPU temperature | >85C（过热） |
| `DCGM_FI_DEV_XID_ERRORS` | Hardware error count | >0（硬件问题） |

Memory exhaustion 的 alert rule：
```yaml
- alert: GPUMemoryExhausted
  expr: (DCGM_FI_DEV_FB_USED / (DCGM_FI_DEV_FB_USED + DCGM_FI_DEV_FB_FREE)) * 100 > 95
  for: 5m
  labels:
    severity: critical
  annotations:
    summary: "GPU memory nearly exhausted"
```

Memory exhaustion 的原因：
- OOM (Out of Memory) 错误
- Training job 失败
- Inference request 被拒绝

</details>

### 11. Karpenter 的 consolidation 功能对于 GPU workloads 的用途是什么？

A) 将多个 GPUs 合并为一个虚拟 GPU
B) 将训练 checkpoints 合并为单个文件
C) 对 workloads 进行 bin-pack，并移除利用率不足的 nodes 以节省成本
D) 汇总多个 GPU pods 的日志

<details>
<summary>显示答案</summary>

**答案： C) 对 workloads 进行 bin-pack，并移除利用率不足的 nodes 以节省成本**

**解释：**
Karpenter 的 consolidation 功能通过以下方式优化 cluster 成本：

1. **Bin-Packing**：将 workloads 移动到更少且利用率更高的 nodes
2. **Node Removal**：终止空闲或利用率不足的 nodes
3. **Right-Sizing**：用更合适的 instance types 替换 nodes
4. **Cost Reduction**：最大限度减少闲置 GPU resources

Consolidation policies：
```yaml
disruption:
  consolidationPolicy: WhenEmptyOrUnderutilized
  consolidateAfter: 5m
```

- **WhenEmpty**：仅 consolidation 完全为空的 nodes
- **WhenEmptyOrUnderutilized**：consolidate 空闲或利用率不足的 nodes

对于 GPU workloads，consolidation 非常关键，因为：
- GPU instances 成本很高（$3-30+/hour）
- 利用率不足的 GPUs 会造成显著成本浪费
- Training jobs 通常会完成并留下闲置 nodes

最佳实践：
- 对开发环境使用较短的 `consolidateAfter`（5m）
- 对生产训练使用更长的时间段（30m）
- 设置适当的 `limits` 以防止失控扩展

</details>

### 12. 在 DRA 中，ResourceSlice 用于什么？

A) 在 containers 之间划分 CPU resources
B) 表示 node 上可用的 GPU resources 及其 topology
C) 为不同 workloads 切分 network bandwidth
D) 分区 storage volumes

<details>
<summary>显示答案</summary>

**答案： B) 表示 node 上可用的 GPU resources 及其 topology**

**解释：**
ResourceSlice 是一个 DRA resource，用于表示可用 devices 及其 topology：

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

ResourceSlice 提供：
1. **Device Inventory**：列出 node 上所有可用 devices
2. **Attributes**：GPU model、memory、capabilities
3. **Topology Information**：NVLink connections、NUMA node、NVSwitch
4. **Capacity**：用于调度的可用 resources

Scheduler 使用 ResourceSlices 来：
- 查找具备所需 GPU types 的 nodes
- 调度拓扑感知的 multi-GPU workloads
- 确保 NVLink 连接的 GPUs 被一起分配

</details>

### 13. Agents on EKS 平台中的哪个组件为 RAG (Retrieval-Augmented Generation) 提供 vector storage？

A) GitLab
B) Langfuse
C) Milvus
D) MCP Gateway

<details>
<summary>显示答案</summary>

**答案： C) Milvus**

**解释：**
Milvus 是一个面向 AI applications 优化的开源 vector database：

1. **Vector Storage**：存储高维 embedding vectors
2. **Similarity Search**：快速 approximate nearest neighbor (ANN) search
3. **GPU Acceleration**：query 和 index nodes 可以使用 GPUs
4. **Scalability**：用于大规模 deployments 的分布式架构

使用 Milvus 的 RAG 架构：
```
User Query → Embedding Model → Milvus (vector search) → Retrieved Context → LLM → Response
```

EKS 上的 Milvus 配置：
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

Agent 集成：
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

### 14. 处理 distributed training 期间 GPU node failures 的推荐方法是什么？

A) 手动从头重启 training
B) 使用 checkpointing，并采用像 Ray Train 这样的 fault-tolerant training frameworks
C) 增加 GPU replicas 的数量以防止 failures
D) 仅使用 on-demand instances 以避免 interruptions

<details>
<summary>显示答案</summary>

**答案： B) 使用 checkpointing，并采用像 Ray Train 这样的 fault-tolerant training frameworks**

**解释：**
使用 fault-tolerant frameworks 进行 checkpointing 是推荐方法，原因包括：

1. **Automatic Recovery**：training 从最后一个 checkpoint 恢复
2. **Cost Efficiency**：支持使用更便宜的 Spot instances
3. **Scalability**：处理动态 cluster size 变化
4. **Progress Preservation**：最大限度减少丢失的 compute time

带 checkpointing 的 Ray Train：
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

### 15. Agents on EKS 平台中 MCP Gateway 的用途是什么？

A) 在 microservices 之间路由 traffic
B) 管理 container image registries
C) 为 AI agents 提供 tool discovery 和 registration
D) 加密 pods 之间的 communication

<details>
<summary>显示答案</summary>

**答案： C) 为 AI agents 提供 tool discovery 和 registration**

**解释：**
MCP (Model Context Protocol) Gateway 为 AI agents 提供 tool discovery 和 management：

1. **Tool Registry**：可用 tools/functions 的中央 registry
2. **Discovery**：自动发现 Kubernetes 中的 tools
3. **Routing**：将 tool calls 路由到合适的 backends
4. **Authentication**：基于 OIDC 的 access control
5. **Rate Limiting**：防止 tool abuse

MCP Gateway 配置：
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

Agent 集成：
```python
# Agent discovers and uses tools via MCP Gateway
env:
- name: MCP_GATEWAY_URL
  value: "http://mcp-gateway.mcp-gateway.svc.cluster.local:8080"
```

MCP 使 agents 能够：
- 动态发现可用 tools
- 调用 external APIs 和 services
- 访问 databases 和 file systems
- 执行 code 和 commands

</details>

---

## 总结

本测验涵盖了 EKS 上 AI infrastructure 的关键概念：

- **JARK Stack**：JupyterHub + Argo Workflows + Ray + Karpenter，用于完整 ML environments
- **Dynamic Resource Allocation**：使用 MIG、MPS 和 time-slicing 的细粒度 GPU 调度
- **Agents Platform**：GitLab + Langfuse + Milvus + MCP Gateway，用于 AI agent development
- **Storage**：EFS 用于共享，FSx Lustre 用于高吞吐量训练
- **Networking**：EFA 用于 multi-node distributed training
- **Monitoring**：用于 GPU observability 的 DCGM metrics 和 Prometheus alerts

有关更多详细信息，请参阅 [AI Infrastructure on EKS](../../ai-ml/06-ai-infrastructure.md) 文档。
