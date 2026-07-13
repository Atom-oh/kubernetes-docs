# EKS 上的 AI/ML 最佳实践

> **支持的版本**: Kubernetes 1.31, 1.32, 1.33
> **最后更新**: February 25, 2026

本指南涵盖在 Amazon EKS 上运行 AI/ML 工作负载的全面最佳实践，包括基准测试、容器优化、GPU 选择、网络、存储、可观测性、成本优化和安全性。

## 概述

要在 Kubernetes 上高效运行 AI/ML 工作负载，需要在多个维度上进行周密考虑：

```mermaid
flowchart TD
    subgraph BestPractices [AI/ML Best Practices on EKS]
        Benchmarking[Benchmarking & Performance]
        Container[Container Optimization]
        GPU[GPU Selection]
        Network[Networking]
        Storage[Storage]
        Observability[Observability]
        Cost[Cost Optimization]
        Security[Security]
    end

    subgraph Outcomes [Expected Outcomes]
        Performance[High Performance]
        Efficiency[Resource Efficiency]
        Reliability[Reliability]
        CostSavings[Cost Savings]
    end

    Benchmarking --> Performance
    Container --> Performance
    GPU --> Performance
    Network --> Performance
    Storage --> Performance
    Observability --> Reliability
    Cost --> CostSavings
    Security --> Reliability
    Container --> Efficiency
    GPU --> Efficiency

    classDef practiceNode fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef outcomeNode fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;

    class Benchmarking,Container,GPU,Network,Storage,Observability,Cost,Security practiceNode;
    class Performance,Efficiency,Reliability,CostSavings outcomeNode;
    class BestPractices,Outcomes default;
```

## LLM 推理基准测试

基准测试对于理解 LLM 推理服务的性能特征至关重要。适当的基准测试可以帮助你在扩展、资源分配和优化方面做出明智决策。

### 关键性能指标

理解关键指标对于评估 LLM 推理性能非常重要：

```mermaid
flowchart LR
    subgraph Metrics [LLM Inference Metrics]
        TTFT[TTFT<br/>Time to First Token]
        ITL[ITL<br/>Inter-Token Latency]
        TPS[TPS<br/>Tokens Per Second]
        E2E[E2E Latency<br/>End-to-End]
        Throughput[Throughput<br/>Requests/sec]
    end

    subgraph UserExperience [User Experience Impact]
        Responsiveness[Perceived Responsiveness]
        Streaming[Streaming Quality]
        Capacity[System Capacity]
    end

    TTFT --> Responsiveness
    ITL --> Streaming
    TPS --> Streaming
    E2E --> Responsiveness
    Throughput --> Capacity

    classDef metricNode fill:#FF9900,stroke:#333,stroke-width:1px,color:black;
    classDef uxNode fill:#326CE5,stroke:#333,stroke-width:1px,color:white;

    class TTFT,ITL,TPS,E2E,Throughput metricNode;
    class Responsiveness,Streaming,Capacity uxNode;
```

| 指标 | 描述 | 公式 | 目标范围 |
|--------|-------------|---------|--------------|
| **TTFT** | 从请求到生成第一个 token 的时间 | `t_first_token - t_request` | 交互式应用 < 500ms |
| **ITL** | 连续 token 之间的平均时间 | `(t_last_token - t_first_token) / (n_tokens - 1)` | 流式输出平滑时 < 50ms |
| **TPS** | 每个请求每秒生成的 token 数 | `n_tokens / total_generation_time` | 良好 UX > 20 TPS |
| **E2E 延迟** | 从请求到完整响应的总时间 | `t_complete - t_request` | 取决于输出长度 |
| **吞吐量** | 每秒处理的请求数 | `total_requests / time_window` | 在延迟 SLO 内最大化 |

### 基准测试工具

#### inference-perf 工具

AI on EKS 提供的 `inference-perf` 工具具备全面的基准测试能力：

```bash
# Install inference-perf
pip install inference-perf

# Basic benchmark against vLLM endpoint
inference-perf benchmark \
  --endpoint http://vllm-service:8000/v1/completions \
  --model meta-llama/Llama-3.1-8B-Instruct \
  --num-requests 1000 \
  --concurrency 10 \
  --prompt-length 128 \
  --max-tokens 256
```

不同测试场景的配置：

```yaml
# benchmark-config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: inference-perf-config
data:
  config.yaml: |
    endpoint:
      url: http://vllm-service:8000/v1/completions
      model: meta-llama/Llama-3.1-8B-Instruct

    scenarios:
      baseline:
        description: "Single request baseline"
        concurrency: 1
        num_requests: 100
        prompt_length: 128
        max_tokens: 256

      saturation:
        description: "Find maximum throughput"
        concurrency: [1, 5, 10, 20, 50, 100]
        num_requests: 500
        prompt_length: 256
        max_tokens: 512

      production:
        description: "Simulate production traffic"
        concurrency: 20
        num_requests: 10000
        prompt_distribution: "zipf"
        prompt_length_range: [64, 2048]
        max_tokens_range: [128, 1024]

      real_dataset:
        description: "Use real conversation data"
        dataset: "ShareGPT"
        num_requests: 5000
        concurrency: 15
```

#### NVIDIA GenAI-Perf 工具

要获取详细的 GPU 级指标，请使用 NVIDIA 的 GenAI-Perf：

```bash
# Install GenAI-Perf (part of Triton Inference Server)
pip install genai-perf

# Run benchmark with detailed GPU metrics
genai-perf profile \
  --model llama-3-8b \
  --backend vllm \
  --endpoint localhost:8000 \
  --concurrency 10 \
  --request-count 1000 \
  --streaming \
  --output-format json \
  --profile-export-file results.json
```

### 测试场景

| 场景 | 目的 | 配置 | 需要关注的关键指标 |
|----------|---------|---------------|----------------------|
| **基线** | 建立单请求性能基线 | Concurrency=1, 100 个请求 | TTFT, ITL, E2E 延迟 |
| **饱和度** | 找出吞吐量限制 | 逐步增加 concurrency，直到延迟下降 | 吞吐量与延迟曲线 |
| **生产仿真** | 验证真实世界性能 | 可变 prompt、真实的 concurrency | P50/P95/P99 延迟 |
| **真实数据集** | 使用实际对话模式进行测试 | ShareGPT 或领域特定数据 | Token 分布分析 |
| **长上下文** | 测试上下文窗口处理 | 4K-128K token prompt | 内存使用、TTFT 扩展情况 |
| **突发流量** | 测试自动扩展响应 | 从 10 到 100 concurrency 的峰值 | 扩容时间、错误率 |

### 用于基准测试的 Kubernetes Job

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: llm-benchmark
  namespace: ai-ml
spec:
  template:
    spec:
      containers:
      - name: benchmark
        image: public.ecr.aws/ai-on-eks/inference-perf:latest
        command:
        - inference-perf
        - benchmark
        - --config
        - /config/benchmark-config.yaml
        - --output
        - /results/benchmark-results.json
        volumeMounts:
        - name: config
          mountPath: /config
        - name: results
          mountPath: /results
        resources:
          requests:
            cpu: "2"
            memory: 4Gi
          limits:
            cpu: "4"
            memory: 8Gi
      volumes:
      - name: config
        configMap:
          name: inference-perf-config
      - name: results
        persistentVolumeClaim:
          claimName: benchmark-results-pvc
      restartPolicy: Never
  backoffLimit: 3
```

### 解读结果

```bash
# Sample benchmark output analysis
{
  "summary": {
    "total_requests": 1000,
    "successful_requests": 998,
    "failed_requests": 2,
    "total_duration_sec": 120.5,
    "requests_per_second": 8.3
  },
  "latency": {
    "ttft_ms": {
      "p50": 245,
      "p95": 512,
      "p99": 890,
      "mean": 298
    },
    "itl_ms": {
      "p50": 32,
      "p95": 48,
      "p99": 72,
      "mean": 35
    },
    "e2e_ms": {
      "p50": 2450,
      "p95": 4200,
      "p99": 6800,
      "mean": 2780
    }
  },
  "throughput": {
    "tokens_per_second": 1245,
    "tokens_per_request_mean": 150
  }
}
```

**性能指南**：
- TTFT P95 > 1s：考虑 prefill 优化或 batch size 调优
- ITL P95 > 100ms：检查 GPU 内存压力，考虑更小的 batch size
- 高 concurrency 下吞吐量下降：GPU 内存或计算受限
- 延迟方差较高：检查是否存在 noisy neighbor 或热节流

## 容器启动优化

AI/ML 容器由于镜像体积较大且需要加载模型，面临独特的冷启动挑战。

### 冷启动时间线分析

```mermaid
sequenceDiagram
    participant Scheduler as K8s Scheduler
    participant Kubelet as Kubelet
    participant Registry as Container Registry
    participant Container as Container Runtime
    participant App as AI/ML Application

    Note over Scheduler,App: Total Cold Start Time: 5-15 minutes for large AI/ML images

    Scheduler->>Kubelet: Pod Scheduled
    Note over Kubelet: Node Selection: ~100ms

    Kubelet->>Registry: Pull Image Request
    Note over Registry,Kubelet: Image Pull: 2-10 minutes<br/>(10-50GB images)
    Registry-->>Kubelet: Image Layers

    Kubelet->>Container: Create Container
    Note over Container: Container Creation: ~5s

    Container->>App: Start Process
    Note over App: Model Loading: 1-5 minutes<br/>(Load weights into GPU memory)

    App-->>Container: Ready
    Note over App: Health Check Pass: ~30s
```

### 镜像大小拆解

典型 AI/ML 容器镜像组成：

| 组件 | 大小范围 | 优化潜力 |
|-----------|------------|------------------------|
| Base OS (Ubuntu/Debian) | 100-500MB | 使用 slim/distroless |
| CUDA Runtime | 2-4GB | 使用仅 runtime 的镜像 |
| Python + 依赖 | 1-3GB | Multi-stage build |
| ML Framework (PyTorch/TensorFlow) | 2-5GB | 使用优化构建 |
| 模型权重 | 5-100GB+ | 与镜像解耦 |
| **总计** | **10-115GB** | **目标：5-10GB** |

### 策略 1：解耦模型工件

将模型权重与容器镜像分离：

```yaml
# Pod with model loaded from S3 at startup
apiVersion: v1
kind: Pod
metadata:
  name: llm-inference
spec:
  initContainers:
  # Download model from S3 before main container starts
  - name: model-downloader
    image: amazon/aws-cli:latest
    command:
    - sh
    - -c
    - |
      aws s3 sync s3://models-bucket/llama-3-8b /models/llama-3-8b \
        --only-show-errors
      echo "Model download complete"
    volumeMounts:
    - name: model-storage
      mountPath: /models
    env:
    - name: AWS_REGION
      value: us-west-2
    resources:
      requests:
        cpu: "2"
        memory: 4Gi

  containers:
  - name: vllm
    image: vllm/vllm-openai:v0.6.0  # Slim image without models
    args:
    - --model
    - /models/llama-3-8b
    - --tensor-parallel-size
    - "1"
    volumeMounts:
    - name: model-storage
      mountPath: /models
    resources:
      limits:
        nvidia.com/gpu: 1

  volumes:
  - name: model-storage
    emptyDir:
      sizeLimit: 50Gi

  # Use EFS for shared model caching across nodes
  # - name: model-storage
  #   persistentVolumeClaim:
  #     claimName: models-efs-pvc
```

### 策略 2：Multi-Stage Build

优化 Dockerfile 以获得最小 runtime 镜像：

```dockerfile
# Build stage - includes all build dependencies
FROM nvidia/cuda:12.4.0-devel-ubuntu22.04 AS builder

RUN apt-get update && apt-get install -y \
    python3.11 python3.11-dev python3-pip git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY requirements.txt .
RUN pip3 install --no-cache-dir --target=/install \
    -r requirements.txt

# Runtime stage - minimal dependencies only
FROM nvidia/cuda:12.4.0-runtime-ubuntu22.04 AS runtime

# Install only runtime Python (no dev packages)
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.11 python3.11-distutils \
    && rm -rf /var/lib/apt/lists/* \
    && ln -s /usr/bin/python3.11 /usr/bin/python

# Copy installed packages from builder
COPY --from=builder /install /usr/local/lib/python3.11/dist-packages

# Copy application code only
COPY src/ /app/
WORKDIR /app

# Non-root user for security
RUN useradd -m -u 1000 appuser
USER appuser

ENTRYPOINT ["python", "serve.py"]
```

镜像大小对比：

| 方法 | 镜像大小 | 拉取时间 (1Gbps) |
|----------|------------|-------------------|
| 朴素方式（所有内容在一个镜像中） | 45GB | ~6 分钟 |
| Multi-stage build | 12GB | ~1.5 分钟 |
| Multi-stage + 外部模型 | 5GB | ~40 秒 |

### 策略 3：containerd Snapshotter

使用 SOCI (Seekable OCI) snapshotter 进行延迟拉取：

```yaml
# Install SOCI snapshotter on EKS nodes
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: soci-snapshotter-installer
  namespace: kube-system
spec:
  selector:
    matchLabels:
      app: soci-snapshotter
  template:
    metadata:
      labels:
        app: soci-snapshotter
    spec:
      hostPID: true
      hostNetwork: true
      containers:
      - name: installer
        image: public.ecr.aws/soci-workshop/soci-snapshotter:latest
        securityContext:
          privileged: true
        volumeMounts:
        - name: containerd-config
          mountPath: /etc/containerd
        - name: containerd-socket
          mountPath: /run/containerd
      volumes:
      - name: containerd-config
        hostPath:
          path: /etc/containerd
      - name: containerd-socket
        hostPath:
          path: /run/containerd
```

为镜像生成 SOCI index：

```bash
# Create SOCI index for faster lazy loading
soci create \
  --ref public.ecr.aws/myrepo/vllm:latest \
  --platform linux/amd64

# Push the index to ECR
soci push \
  --ref public.ecr.aws/myrepo/vllm:latest
```

### 策略 4：Bottlerocket 上的镜像预取

配置 Bottlerocket 进行镜像预取：

```toml
# bottlerocket-settings.toml
[settings.container-registry]
# Pre-pull images on node startup
[settings.container-registry.credentials]
[settings.container-registry.credentials."public.ecr.aws"]

# Configure image pre-caching
[settings.kubernetes]
# Allow privileged containers for GPU workloads
allowed-unsafe-sysctls = ["net.core.*"]

[settings.bootstrap-containers.prefetch-images]
source = "public.ecr.aws/bottlerocket/bottlerocket-bootstrap-prefetch:latest"
mode = "once"
essential = false
user-data = """
#!/bin/bash
# Pre-fetch AI/ML images during node bootstrap
ctr images pull public.ecr.aws/myrepo/vllm:v0.6.0
ctr images pull public.ecr.aws/nvidia/cuda:12.4.0-runtime-ubuntu22.04
"""
```

带预取的 Karpenter NodePool：

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: gpu-inference
spec:
  template:
    spec:
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: gpu-bottlerocket
      requirements:
      - key: node.kubernetes.io/instance-type
        operator: In
        values: ["g5.xlarge", "g5.2xlarge", "g5.4xlarge"]
      - key: karpenter.sh/capacity-type
        operator: In
        values: ["on-demand", "spot"]
---
apiVersion: karpenter.k8s.aws/v1
kind: EC2NodeClass
metadata:
  name: gpu-bottlerocket
spec:
  amiSelectorTerms:
  - alias: bottlerocket@latest

  # Custom user data for image prefetching
  userData: |
    [settings.bootstrap-containers.prefetch]
    source = "public.ecr.aws/myrepo/image-prefetcher:latest"
    mode = "once"
    essential = false

    [settings.kubernetes.node-labels]
    "ai-ml/images-prefetched" = "true"
```

### 冷启动优化总结

| 技术 | 启动时间缩短 | 实施难度 |
|-----------|-------------------|----------------------|
| 模型解耦 | 50-70% | 中 |
| Multi-stage build | 30-50% | 低 |
| SOCI snapshotter | 60-80% | 中 |
| 镜像预取 | 70-90% | 低 |
| 组合方法 | 80-95% | 高 |

## GPU Instance 选择指南

选择合适的 GPU instance type 对于具有成本效益的 AI/ML 工作负载至关重要。

### GPU Instance 对比

| Instance 系列 | GPU 类型 | GPU 内存 | GPU 数量 | vCPU | 内存 | 网络 | 使用场景 | 成本层级 |
|-----------------|----------|------------|------|------|--------|---------|-----------|-----------|
| **G5** | NVIDIA A10G | 24GB | 1-8 | 4-192 | 16-768GB | 最高 100 Gbps | 推理、fine-tuning | $$ |
| **G5g** | NVIDIA T4G | 16GB | 1-2 | 4-64 | 8-256GB | 最高 25 Gbps | 成本高效的推理 | $ |
| **G6** | NVIDIA L4 | 24GB | 1-8 | 4-192 | 16-768GB | 最高 100 Gbps | 推理、视频 | $$ |
| **G6e** | NVIDIA L40S | 48GB | 1-8 | 8-384 | 32-1536GB | 最高 100 Gbps | 大模型推理 | $$$ |
| **P4d** | NVIDIA A100 | 40GB | 8 | 96 | 1152GB | 400 Gbps EFA | 大规模训练 | $$$$ |
| **P4de** | NVIDIA A100 | 80GB | 8 | 96 | 1152GB | 400 Gbps EFA | LLM 训练 | $$$$ |
| **P5** | NVIDIA H100 | 80GB | 8 | 192 | 2048GB | 3200 Gbps EFA | 前沿模型训练 | $$$$$ |
| **P5e** | NVIDIA H200 | 141GB | 8 | 192 | 2048GB | 3200 Gbps EFA | 最大规模模型 | $$$$$ |
| **Trn1** | AWS Trainium | 32GB | 1-16 | 8-128 | 32-512GB | 最高 800 Gbps | 训练（优化） | $$$ |
| **Inf2** | AWS Inferentia2 | 32GB | 1-12 | 4-96 | 16-384GB | 最高 100 Gbps | 推理（优化） | $$ |

### 基于工作负载的选择指南

```yaml
# Workload requirements to instance mapping
workload_selection:

  small_model_inference:  # Models < 7B parameters
    recommended:
      - g5.xlarge       # 1x A10G, cost-effective
      - g6.xlarge       # 1x L4, newer generation
      - inf2.xlarge     # 1x Inferentia2, best price/perf
    requirements:
      gpu_memory: "8-16GB"
      throughput: "10-50 req/s"
      latency: "< 500ms P95"

  medium_model_inference:  # Models 7B-30B parameters
    recommended:
      - g5.4xlarge      # 1x A10G 24GB
      - g6e.2xlarge     # 1x L40S 48GB
      - inf2.8xlarge    # 1x Inferentia2
    requirements:
      gpu_memory: "24-48GB"
      throughput: "5-20 req/s"
      latency: "< 1s P95"

  large_model_inference:  # Models 30B-70B parameters
    recommended:
      - g5.12xlarge     # 4x A10G (tensor parallel)
      - g6e.12xlarge    # 4x L40S
      - p4d.24xlarge    # 8x A100 (for 70B+)
    requirements:
      gpu_memory: "80-320GB"
      throughput: "1-10 req/s"
      latency: "< 3s P95"

  distributed_training:  # Multi-node training
    recommended:
      - p4d.24xlarge    # 8x A100, EFA
      - p5.48xlarge     # 8x H100, EFA
      - trn1.32xlarge   # 16x Trainium
    requirements:
      interconnect: "EFA required"
      gpu_memory: "320GB+ per node"
      scaling: "2-64+ nodes"

  fine_tuning:  # LoRA, QLoRA, full fine-tuning
    recommended:
      - g5.4xlarge      # Small models, LoRA
      - g5.12xlarge     # Medium models
      - p4d.24xlarge    # Large models, full fine-tune
    requirements:
      gpu_memory: "24-640GB"
      training_time: "hours to days"
```

### Instance 选择决策树

```python
def select_gpu_instance(model_size_b, workload_type, budget):
    """
    Select optimal GPU instance based on requirements.

    Args:
        model_size_b: Model size in billions of parameters
        workload_type: 'inference', 'training', 'fine_tuning'
        budget: 'low', 'medium', 'high'
    """

    # Memory estimation (rough): 2 bytes per param for FP16
    required_memory_gb = model_size_b * 2

    if workload_type == 'inference':
        if model_size_b <= 7:
            return 'g5.xlarge' if budget == 'low' else 'g6.xlarge'
        elif model_size_b <= 13:
            return 'g5.2xlarge' if budget == 'low' else 'g6e.2xlarge'
        elif model_size_b <= 30:
            return 'g5.4xlarge' if budget != 'high' else 'g6e.4xlarge'
        elif model_size_b <= 70:
            return 'g5.12xlarge'  # 4-way tensor parallel
        else:
            return 'p4d.24xlarge'  # 8-way tensor parallel

    elif workload_type == 'training':
        if model_size_b <= 7:
            return 'g5.12xlarge'
        elif model_size_b <= 30:
            return 'p4d.24xlarge'
        else:
            return 'p5.48xlarge'  # Multi-node required

    elif workload_type == 'fine_tuning':
        # LoRA reduces memory by ~10x
        if budget == 'low':
            return 'g5.xlarge'  # LoRA on most models
        else:
            return 'g5.4xlarge'  # Full fine-tune small models
```

## 网络最佳实践

高性能网络对于分布式 AI/ML 工作负载至关重要。

### 分布式训练的 EFA 设置

Elastic Fabric Adapter (EFA) 提供低延迟、高带宽网络，是多节点训练所必需的：

```yaml
# EFA-enabled node configuration
apiVersion: karpenter.k8s.aws/v1
kind: EC2NodeClass
metadata:
  name: efa-training-nodes
spec:
  amiSelectorTerms:
  - alias: al2023@latest

  # EFA requires placement groups for optimal performance
  subnetSelectorTerms:
  - tags:
      karpenter.sh/discovery: my-cluster
      network/efa-enabled: "true"

  # Instance store for fast local scratch
  instanceStorePolicy: RAID0

  blockDeviceMappings:
  - deviceName: /dev/xvda
    ebs:
      volumeSize: 200Gi
      volumeType: gp3
      iops: 10000
      throughput: 500

  userData: |
    #!/bin/bash
    # Install EFA driver
    curl -O https://efa-installer.amazonaws.com/aws-efa-installer-latest.tar.gz
    tar -xf aws-efa-installer-latest.tar.gz
    cd aws-efa-installer && ./efa_installer.sh -y

    # Verify EFA installation
    fi_info -p efa
---
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: efa-training
spec:
  template:
    spec:
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: efa-training-nodes
      requirements:
      - key: node.kubernetes.io/instance-type
        operator: In
        values: ["p4d.24xlarge", "p5.48xlarge"]
      - key: karpenter.sh/capacity-type
        operator: In
        values: ["on-demand"]
      taints:
      - key: nvidia.com/gpu
        value: "true"
        effect: NoSchedule
```

### NCCL 配置

针对 EFA 的 NVIDIA Collective Communication Library (NCCL) 优化：

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: nccl-config
  namespace: ai-ml
data:
  nccl-env.sh: |
    # EFA-optimized NCCL settings
    export NCCL_DEBUG=INFO
    export NCCL_DEBUG_SUBSYS=ALL

    # Use EFA for inter-node communication
    export FI_PROVIDER=efa
    export FI_EFA_USE_DEVICE_RDMA=1
    export FI_EFA_FORK_SAFE=1

    # Optimize for P4d/P5 instances
    export NCCL_ALGO=Ring,Tree
    export NCCL_PROTO=Simple

    # Network interface selection
    export NCCL_SOCKET_IFNAME=eth0
    export NCCL_IB_DISABLE=1

    # Buffer sizes for large models
    export NCCL_BUFFSIZE=8388608
    export NCCL_P2P_NET_CHUNKSIZE=524288

    # Timeout settings
    export NCCL_TIMEOUT=1800

    # AWS OFI NCCL plugin
    export LD_LIBRARY_PATH=/opt/amazon/efa/lib:$LD_LIBRARY_PATH
    export FI_EFA_ENABLE_SHM_TRANSFER=1
---
apiVersion: v1
kind: Pod
metadata:
  name: distributed-training
spec:
  containers:
  - name: trainer
    image: my-training-image:latest
    command: ["/bin/bash", "-c"]
    args:
    - |
      source /config/nccl-env.sh
      torchrun --nproc_per_node=8 \
               --nnodes=$WORLD_SIZE \
               --node_rank=$RANK \
               --master_addr=$MASTER_ADDR \
               --master_port=29500 \
               train.py
    volumeMounts:
    - name: nccl-config
      mountPath: /config
    - name: shm
      mountPath: /dev/shm
    resources:
      limits:
        nvidia.com/gpu: 8
        vpc.amazonaws.com/efa: 4  # Request EFA devices
  volumes:
  - name: nccl-config
    configMap:
      name: nccl-config
  - name: shm
    emptyDir:
      medium: Memory
      sizeLimit: 64Gi
```

### Placement Group

配置 placement group 以获得最佳网络性能：

```yaml
# Cluster placement group for distributed training
apiVersion: karpenter.k8s.aws/v1
kind: EC2NodeClass
metadata:
  name: training-cluster-pg
spec:
  # ... other config ...

  # Use cluster placement group for lowest latency
  tags:
    aws:ec2:placement-group: training-cluster-pg
---
# Create placement group via AWS CLI
# aws ec2 create-placement-group \
#   --group-name training-cluster-pg \
#   --strategy cluster \
#   --tag-specifications 'ResourceType=placement-group,Tags=[{Key=Purpose,Value=ai-training}]'
```

### GPU 流量的 Security Group 规则

```yaml
# Security group configuration for distributed training
# Apply via Terraform or CloudFormation

security_group_rules:
  # Allow all traffic within placement group
  - type: ingress
    from_port: 0
    to_port: 65535
    protocol: tcp
    self: true
    description: "Intra-cluster communication"

  # NCCL communication ports
  - type: ingress
    from_port: 29500
    to_port: 29600
    protocol: tcp
    self: true
    description: "PyTorch distributed training"

  # EFA traffic (requires specific rules)
  - type: ingress
    from_port: 0
    to_port: 0
    protocol: "-1"  # All protocols
    self: true
    description: "EFA traffic"
```

### 推理端点的 Network Policy

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: llm-inference-policy
  namespace: ai-ml
spec:
  podSelector:
    matchLabels:
      app: llm-inference
  policyTypes:
  - Ingress
  - Egress

  ingress:
  # Allow traffic from API gateway
  - from:
    - namespaceSelector:
        matchLabels:
          name: api-gateway
    ports:
    - protocol: TCP
      port: 8000

  # Allow health checks from kubelet
  - from:
    - ipBlock:
        cidr: 10.0.0.0/8
    ports:
    - protocol: TCP
      port: 8000

  egress:
  # Allow DNS
  - to:
    - namespaceSelector: {}
    ports:
    - protocol: UDP
      port: 53

  # Allow S3 access for model downloads
  - to:
    - ipBlock:
        cidr: 0.0.0.0/0
    ports:
    - protocol: TCP
      port: 443
```

## 存储最佳实践

选择合适的存储解决方案会显著影响 AI/ML 工作负载性能。

### 存储选择指南

| 存储类型 | 吞吐量 | 延迟 | 容量 | 使用场景 | 成本 |
|--------------|------------|---------|----------|-----------|------|
| **Instance Store** | 最高 7.5 GB/s | < 1ms | 最高 7.6TB | 临时空间、checkpoint | 已包含 |
| **EBS gp3** | 最高 1 GB/s | 1-2ms | 最高 16TB | Boot、小型数据集 | $ |
| **EBS io2** | 最高 4 GB/s | < 1ms | 最高 64TB | 高 IOPS 需求 | $$$ |
| **EFS** | Bursting/Provisioned | 2-5ms | 无限制 | 共享模型、数据集 | $$ |
| **FSx Lustre** | 最高 1+ TB/s | < 1ms | PB 级 | 大型训练数据集 | $$$ |
| **S3** | 几乎无限 | 50-100ms | 无限制 | 模型工件、归档 | $ |

### 每种存储类型的使用场景

```yaml
# Storage decision matrix
storage_recommendations:

  model_weights:
    primary: EFS  # Shared across pods
    alternative: S3 + init container download
    reasoning: |
      - Models need to be accessible from multiple pods
      - EFS provides shared access with caching
      - S3 is cheaper but requires download time

  training_datasets:
    small: EBS gp3  # < 500GB, single node
    medium: EFS  # 500GB-10TB, multi-node read
    large: FSx Lustre  # > 10TB, high throughput
    reasoning: |
      - FSx Lustre provides parallel filesystem
      - Can link directly to S3 for data loading

  checkpoints:
    training: Instance store  # Fast, temporary
    persistent: S3  # Long-term storage
    reasoning: |
      - Checkpoints are written frequently during training
      - Instance store provides lowest latency
      - Periodic sync to S3 for durability

  inference_cache:
    kv_cache: Instance store or tmpfs
    model_cache: EFS or local EBS
    reasoning: |
      - KV cache is ephemeral, needs lowest latency
      - Model cache benefits from persistence
```

### 模型缓存策略

```yaml
# PVC for shared model cache
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: model-cache-efs
  namespace: ai-ml
spec:
  accessModes:
  - ReadWriteMany  # Shared across all inference pods
  storageClassName: efs-sc
  resources:
    requests:
      storage: 500Gi
---
# Model cache sidecar
apiVersion: v1
kind: Pod
metadata:
  name: llm-inference
spec:
  initContainers:
  # Check cache, download if missing
  - name: model-cache-check
    image: amazon/aws-cli:latest
    command:
    - sh
    - -c
    - |
      MODEL_PATH="/models/llama-3-8b"
      if [ ! -f "$MODEL_PATH/config.json" ]; then
        echo "Model not in cache, downloading..."
        aws s3 sync s3://models/llama-3-8b $MODEL_PATH
      else
        echo "Model found in cache"
      fi
    volumeMounts:
    - name: model-cache
      mountPath: /models

  containers:
  - name: vllm
    image: vllm/vllm-openai:latest
    args:
    - --model
    - /models/llama-3-8b
    volumeMounts:
    - name: model-cache
      mountPath: /models
      readOnly: true  # Read-only for inference
    resources:
      limits:
        nvidia.com/gpu: 1

  volumes:
  - name: model-cache
    persistentVolumeClaim:
      claimName: model-cache-efs
```

### 训练的 Checkpoint 管理

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: checkpoint-manager
data:
  checkpoint-sync.sh: |
    #!/bin/bash
    # Sync checkpoints to S3 periodically

    LOCAL_CKPT_DIR="/scratch/checkpoints"
    S3_CKPT_PATH="s3://training-checkpoints/${JOB_NAME}"
    SYNC_INTERVAL=1800  # 30 minutes

    while true; do
      sleep $SYNC_INTERVAL

      # Find newest checkpoint
      LATEST=$(ls -t $LOCAL_CKPT_DIR/checkpoint-* 2>/dev/null | head -1)

      if [ -n "$LATEST" ]; then
        echo "Syncing $LATEST to S3..."
        aws s3 cp --recursive $LATEST $S3_CKPT_PATH/$(basename $LATEST)

        # Keep only last 3 local checkpoints
        ls -t $LOCAL_CKPT_DIR/checkpoint-* | tail -n +4 | xargs rm -rf
      fi
    done
---
apiVersion: v1
kind: Pod
metadata:
  name: training-job
spec:
  containers:
  - name: trainer
    image: training-image:latest
    volumeMounts:
    - name: scratch
      mountPath: /scratch
    env:
    - name: CHECKPOINT_DIR
      value: /scratch/checkpoints

  - name: checkpoint-sync
    image: amazon/aws-cli:latest
    command: ["/scripts/checkpoint-sync.sh"]
    volumeMounts:
    - name: scratch
      mountPath: /scratch
      readOnly: true
    - name: scripts
      mountPath: /scripts
    env:
    - name: JOB_NAME
      valueFrom:
        fieldRef:
          fieldPath: metadata.name

  volumes:
  - name: scratch
    emptyDir:
      medium: Memory  # Or use instance store
      sizeLimit: 100Gi
  - name: scripts
    configMap:
      name: checkpoint-manager
      defaultMode: 0755
```

### FSx for Lustre 设置

```yaml
# StorageClass for FSx Lustre
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: fsx-lustre-sc
provisioner: fsx.csi.aws.com
parameters:
  subnetId: subnet-0123456789abcdef0
  securityGroupIds: sg-0123456789abcdef0
  deploymentType: PERSISTENT_2
  perUnitStorageThroughput: "250"  # MB/s per TiB
  dataCompressionType: LZ4

  # Link to S3 for transparent data access
  s3ImportPath: s3://training-data
  s3ExportPath: s3://training-data
  autoImportPolicy: NEW_CHANGED_DELETED
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: training-data-fsx
spec:
  accessModes:
  - ReadWriteMany
  storageClassName: fsx-lustre-sc
  resources:
    requests:
      storage: 2400Gi  # Minimum 1.2TiB, increments of 2.4TiB
```

## AI/ML 可观测性

全面的可观测性对于大规模运行 AI/ML 工作负载至关重要。

### NVIDIA DCGM Exporter 设置

部署 DCGM exporter 以获取 GPU 指标：

```yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: dcgm-exporter
  namespace: monitoring
spec:
  selector:
    matchLabels:
      app: dcgm-exporter
  template:
    metadata:
      labels:
        app: dcgm-exporter
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "9400"
    spec:
      nodeSelector:
        nvidia.com/gpu.present: "true"
      tolerations:
      - key: nvidia.com/gpu
        operator: Exists
        effect: NoSchedule

      containers:
      - name: dcgm-exporter
        image: nvcr.io/nvidia/k8s/dcgm-exporter:3.3.5-3.4.0-ubuntu22.04
        ports:
        - containerPort: 9400
          name: metrics
        env:
        - name: DCGM_EXPORTER_LISTEN
          value: ":9400"
        - name: DCGM_EXPORTER_KUBERNETES
          value: "true"
        - name: DCGM_EXPORTER_COLLECTORS
          value: "/etc/dcgm-exporter/dcp-metrics-included.csv"
        securityContext:
          runAsNonRoot: false
          runAsUser: 0
          capabilities:
            add: ["SYS_ADMIN"]
        volumeMounts:
        - name: pod-resources
          mountPath: /var/lib/kubelet/pod-resources
          readOnly: true
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 500m
            memory: 512Mi

      volumes:
      - name: pod-resources
        hostPath:
          path: /var/lib/kubelet/pod-resources
---
apiVersion: v1
kind: Service
metadata:
  name: dcgm-exporter
  namespace: monitoring
  labels:
    app: dcgm-exporter
spec:
  type: ClusterIP
  ports:
  - port: 9400
    targetPort: 9400
    name: metrics
  selector:
    app: dcgm-exporter
```

### GPU 指标收集

需要监控的关键 GPU 指标：

```yaml
# ServiceMonitor for Prometheus Operator
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: dcgm-exporter
  namespace: monitoring
spec:
  selector:
    matchLabels:
      app: dcgm-exporter
  endpoints:
  - port: metrics
    interval: 15s
    path: /metrics
---
# PrometheusRule for GPU alerts
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: gpu-alerts
  namespace: monitoring
spec:
  groups:
  - name: gpu.rules
    rules:
    # GPU utilization alerts
    - alert: GPUHighUtilization
      expr: DCGM_FI_DEV_GPU_UTIL > 95
      for: 10m
      labels:
        severity: warning
      annotations:
        summary: "GPU {{ $labels.gpu }} utilization above 95%"
        description: "GPU utilization has been above 95% for 10 minutes"

    # GPU memory alerts
    - alert: GPUMemoryAlmostFull
      expr: (DCGM_FI_DEV_FB_USED / DCGM_FI_DEV_FB_TOTAL) > 0.95
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "GPU {{ $labels.gpu }} memory usage above 95%"

    # GPU temperature alerts
    - alert: GPUHighTemperature
      expr: DCGM_FI_DEV_GPU_TEMP > 80
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "GPU {{ $labels.gpu }} temperature above 80C"

    - alert: GPUCriticalTemperature
      expr: DCGM_FI_DEV_GPU_TEMP > 90
      for: 1m
      labels:
        severity: critical
      annotations:
        summary: "GPU {{ $labels.gpu }} temperature critical (>90C)"

    # GPU errors
    - alert: GPUXidErrors
      expr: increase(DCGM_FI_DEV_XID_ERRORS[5m]) > 0
      labels:
        severity: critical
      annotations:
        summary: "GPU {{ $labels.gpu }} XID errors detected"
```

### 关键 GPU 指标参考

| 指标 | 描述 | 告警阈值 |
|--------|-------------|-----------------|
| `DCGM_FI_DEV_GPU_UTIL` | GPU 计算利用率 % | 持续 > 95% |
| `DCGM_FI_DEV_MEM_COPY_UTIL` | 内存复制利用率 % | 持续 > 90% |
| `DCGM_FI_DEV_FB_USED` | 已使用的帧缓冲内存（字节） | 超过总量的 95% |
| `DCGM_FI_DEV_GPU_TEMP` | GPU 温度（摄氏度） | > 80C warning，> 90C critical |
| `DCGM_FI_DEV_POWER_USAGE` | 功耗（瓦特） | 接近 TDP 限制 |
| `DCGM_FI_DEV_SM_CLOCK` | SM 时钟频率 (MHz) | 节流检测 |
| `DCGM_FI_DEV_XID_ERRORS` | XID 错误计数 | 任何增加 |
| `DCGM_FI_DEV_NVLINK_BANDWIDTH_TOTAL` | NVLink 带宽 | 低于预期 |

### 模型服务指标

```yaml
# vLLM metrics configuration
apiVersion: v1
kind: ConfigMap
metadata:
  name: vllm-metrics-config
data:
  prometheus.yaml: |
    # vLLM exposes metrics at /metrics endpoint
    # Key metrics to monitor:

    # Request metrics
    # - vllm:num_requests_running - Current running requests
    # - vllm:num_requests_waiting - Queued requests
    # - vllm:request_success_total - Successful requests
    # - vllm:request_prompt_tokens_total - Input tokens processed
    # - vllm:request_generation_tokens_total - Output tokens generated

    # Latency metrics
    # - vllm:time_to_first_token_seconds - TTFT histogram
    # - vllm:time_per_output_token_seconds - ITL histogram
    # - vllm:e2e_request_latency_seconds - End-to-end latency

    # GPU metrics
    # - vllm:gpu_cache_usage_perc - KV cache utilization
    # - vllm:gpu_prefix_cache_hit_rate - Prefix caching efficiency

    # Batch metrics
    # - vllm:num_preemptions_total - Request preemptions
    # - vllm:iteration_tokens_total - Tokens per iteration
---
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: vllm-alerts
  namespace: ai-ml
spec:
  groups:
  - name: vllm.rules
    rules:
    - alert: vLLMHighQueueDepth
      expr: vllm:num_requests_waiting > 50
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "vLLM request queue depth high"
        description: "More than 50 requests waiting for processing"

    - alert: vLLMHighTTFT
      expr: histogram_quantile(0.95, rate(vllm:time_to_first_token_seconds_bucket[5m])) > 2
      for: 10m
      labels:
        severity: warning
      annotations:
        summary: "vLLM TTFT P95 exceeds 2 seconds"

    - alert: vLLMKVCacheFull
      expr: vllm:gpu_cache_usage_perc > 0.95
      for: 5m
      labels:
        severity: critical
      annotations:
        summary: "vLLM KV cache nearly full"
        description: "KV cache usage above 95%, requests may be rejected"
```

### Grafana Dashboard 配置

```json
{
  "dashboard": {
    "title": "AI/ML Workloads Overview",
    "panels": [
      {
        "title": "GPU Utilization by Node",
        "type": "timeseries",
        "targets": [
          {
            "expr": "DCGM_FI_DEV_GPU_UTIL",
            "legendFormat": "{{node}}-GPU{{gpu}}"
          }
        ]
      },
      {
        "title": "GPU Memory Usage",
        "type": "gauge",
        "targets": [
          {
            "expr": "DCGM_FI_DEV_FB_USED / DCGM_FI_DEV_FB_TOTAL * 100",
            "legendFormat": "{{node}}-GPU{{gpu}}"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "thresholds": {
              "steps": [
                {"color": "green", "value": 0},
                {"color": "yellow", "value": 70},
                {"color": "red", "value": 90}
              ]
            }
          }
        }
      },
      {
        "title": "Inference Latency (TTFT P95)",
        "type": "timeseries",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(vllm:time_to_first_token_seconds_bucket[5m]))",
            "legendFormat": "{{pod}}"
          }
        ]
      },
      {
        "title": "Requests Per Second",
        "type": "stat",
        "targets": [
          {
            "expr": "sum(rate(vllm:request_success_total[5m]))",
            "legendFormat": "Total RPS"
          }
        ]
      },
      {
        "title": "Tokens Per Second",
        "type": "timeseries",
        "targets": [
          {
            "expr": "sum(rate(vllm:request_generation_tokens_total[5m]))",
            "legendFormat": "Generation TPS"
          }
        ]
      },
      {
        "title": "GPU Temperature",
        "type": "timeseries",
        "targets": [
          {
            "expr": "DCGM_FI_DEV_GPU_TEMP",
            "legendFormat": "{{node}}-GPU{{gpu}}"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "custom": {
              "thresholdsStyle": {
                "mode": "line"
              }
            },
            "thresholds": {
              "steps": [
                {"color": "green", "value": 0},
                {"color": "yellow", "value": 75},
                {"color": "red", "value": 85}
              ]
            }
          }
        }
      }
    ]
  }
}
```

## 成本优化

实施成本优化策略可以显著降低 AI/ML 基础设施成本。

### 用于推理的 Spot Instances

```yaml
# Karpenter NodePool with Spot for inference
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: inference-spot
spec:
  template:
    spec:
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: inference-ec2
      requirements:
      - key: node.kubernetes.io/instance-type
        operator: In
        values:
        - g5.xlarge
        - g5.2xlarge
        - g6.xlarge
        - g6.2xlarge
      - key: karpenter.sh/capacity-type
        operator: In
        values: ["spot"]  # Prefer Spot
      - key: kubernetes.io/arch
        operator: In
        values: ["amd64"]

      taints:
      - key: nvidia.com/gpu
        value: "true"
        effect: NoSchedule

  # Disruption settings for Spot
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 1m
    budgets:
    - nodes: "20%"  # Allow 20% of nodes to be disrupted

  limits:
    cpu: 1000
    memory: 4000Gi
    nvidia.com/gpu: 100
---
# Pod configuration for graceful Spot termination
apiVersion: v1
kind: Pod
metadata:
  name: inference-pod
spec:
  terminationGracePeriodSeconds: 120  # Handle Spot interruption
  containers:
  - name: inference
    image: vllm/vllm-openai:latest
    lifecycle:
      preStop:
        exec:
          command:
          - /bin/sh
          - -c
          - |
            # Drain requests gracefully
            curl -X POST localhost:8000/drain
            sleep 30
```

### Karpenter Consolidation 策略

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: gpu-workloads
spec:
  template:
    spec:
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: gpu-nodes
      requirements:
      - key: node.kubernetes.io/instance-type
        operator: In
        values:
        - g5.xlarge
        - g5.2xlarge
        - g5.4xlarge
        - g5.8xlarge
        - g5.12xlarge
      - key: karpenter.sh/capacity-type
        operator: In
        values: ["spot", "on-demand"]

  disruption:
    # Consolidate underutilized nodes
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 5m

    # Budget to prevent disruption during peak hours
    budgets:
    - nodes: "0"
      schedule: "0 9-17 * * 1-5"  # No consolidation during business hours
      duration: 8h
    - nodes: "30%"  # Allow 30% during off-peak

  # Weight for cost optimization
  weight: 100  # Higher weight = preferred for scheduling
```

### Right-Sizing 建议

```yaml
# VPA for inference workloads
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: llm-inference-vpa
  namespace: ai-ml
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: llm-inference
  updatePolicy:
    updateMode: "Off"  # Recommendation only
  resourcePolicy:
    containerPolicies:
    - containerName: inference
      minAllowed:
        cpu: "2"
        memory: 8Gi
      maxAllowed:
        cpu: "16"
        memory: 64Gi
      controlledResources: ["cpu", "memory"]
      controlledValues: RequestsAndLimits
---
# Script to analyze GPU utilization and recommend right-sizing
apiVersion: v1
kind: ConfigMap
metadata:
  name: rightsizing-analysis
data:
  analyze.sh: |
    #!/bin/bash
    # Query Prometheus for GPU utilization

    echo "=== GPU Right-Sizing Analysis ==="

    # Average GPU utilization over last 7 days
    GPU_UTIL=$(curl -s "http://prometheus:9090/api/v1/query" \
      --data-urlencode 'query=avg_over_time(DCGM_FI_DEV_GPU_UTIL[7d])' \
      | jq -r '.data.result[0].value[1]')

    # Average GPU memory utilization
    GPU_MEM=$(curl -s "http://prometheus:9090/api/v1/query" \
      --data-urlencode 'query=avg_over_time((DCGM_FI_DEV_FB_USED/DCGM_FI_DEV_FB_TOTAL)[7d])' \
      | jq -r '.data.result[0].value[1]')

    echo "Average GPU Utilization: ${GPU_UTIL}%"
    echo "Average GPU Memory: ${GPU_MEM}%"

    # Recommendations
    if (( $(echo "$GPU_UTIL < 30" | bc -l) )); then
      echo "RECOMMENDATION: Consider smaller GPU instance or GPU sharing"
    elif (( $(echo "$GPU_UTIL > 90" | bc -l) )); then
      echo "RECOMMENDATION: Consider larger GPU instance or scale out"
    fi

    if (( $(echo "$GPU_MEM < 50" | bc -l) )); then
      echo "RECOMMENDATION: Consider instance with less GPU memory"
    elif (( $(echo "$GPU_MEM > 90" | bc -l) )); then
      echo "RECOMMENDATION: Consider instance with more GPU memory"
    fi
```

### 成本对比和 Savings Plans

| 策略 | 典型节省 | 实施复杂度 | 最适合 |
|----------|-----------------|---------------------------|----------|
| Spot Instances | 60-90% | 中 | 无状态推理 |
| Savings Plans (1yr) | 30-40% | 低 | 基线容量 |
| Savings Plans (3yr) | 50-60% | 低 | 稳定工作负载 |
| Reserved Instances | 40-70% | 中 | 可预测使用量 |
| Karpenter Consolidation | 20-40% | 低 | 可变工作负载 |
| GPU Sharing (MIG/MPS) | 30-50% | 高 | 小模型 |
| Right-sizing | 20-50% | 中 | 过度预置 |

```yaml
# Example cost optimization deployment strategy
apiVersion: apps/v1
kind: Deployment
metadata:
  name: llm-inference-cost-optimized
spec:
  replicas: 10
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 2
      maxUnavailable: 1
  template:
    spec:
      # Topology spread for availability
      topologySpreadConstraints:
      - maxSkew: 2
        topologyKey: topology.kubernetes.io/zone
        whenUnsatisfiable: ScheduleAnyway
        labelSelector:
          matchLabels:
            app: llm-inference

      # Prefer Spot, fallback to On-Demand
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

      containers:
      - name: inference
        resources:
          requests:
            nvidia.com/gpu: 1
            cpu: "4"
            memory: 16Gi
          limits:
            nvidia.com/gpu: 1
            cpu: "8"
            memory: 32Gi
```

## 安全注意事项

部署 AI/ML 工作负载时，安全性至关重要，尤其是处理敏感数据或高价值模型的工作负载。

### 模型访问控制

```yaml
# IRSA for S3 model access
apiVersion: v1
kind: ServiceAccount
metadata:
  name: model-loader
  namespace: ai-ml
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/ModelLoaderRole
---
# IAM policy for model access (apply via Terraform)
# {
#   "Version": "2012-10-17",
#   "Statement": [
#     {
#       "Effect": "Allow",
#       "Action": [
#         "s3:GetObject",
#         "s3:ListBucket"
#       ],
#       "Resource": [
#         "arn:aws:s3:::models-bucket",
#         "arn:aws:s3:::models-bucket/*"
#       ],
#       "Condition": {
#         "StringEquals": {
#           "aws:ResourceTag/Environment": "production"
#         }
#       }
#     }
#   ]
# }
---
# Pod with IRSA
apiVersion: v1
kind: Pod
metadata:
  name: inference-pod
spec:
  serviceAccountName: model-loader
  containers:
  - name: inference
    image: vllm/vllm-openai:latest
    # AWS SDK will automatically use IRSA credentials
```

### API Key 的 Secrets Management

```yaml
# External Secrets Operator for HuggingFace/NGC tokens
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: model-registry-secrets
  namespace: ai-ml
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: aws-secretsmanager
    kind: ClusterSecretStore
  target:
    name: model-registry-credentials
    creationPolicy: Owner
  data:
  - secretKey: HUGGING_FACE_HUB_TOKEN
    remoteRef:
      key: ai-ml/huggingface-token
      property: token
  - secretKey: NGC_API_KEY
    remoteRef:
      key: ai-ml/ngc-api-key
      property: key
---
# Pod using external secrets
apiVersion: v1
kind: Pod
metadata:
  name: model-downloader
spec:
  containers:
  - name: downloader
    image: python:3.11-slim
    command: ["python", "download_model.py"]
    env:
    - name: HUGGING_FACE_HUB_TOKEN
      valueFrom:
        secretKeyRef:
          name: model-registry-credentials
          key: HUGGING_FACE_HUB_TOKEN
    - name: NGC_API_KEY
      valueFrom:
        secretKeyRef:
          name: model-registry-credentials
          key: NGC_API_KEY
    securityContext:
      readOnlyRootFilesystem: true
      runAsNonRoot: true
      runAsUser: 1000
      allowPrivilegeEscalation: false
      capabilities:
        drop: ["ALL"]
```

### 推理端点的 Network Policies

```yaml
# Strict network policy for LLM inference
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: llm-inference-strict
  namespace: ai-ml
spec:
  podSelector:
    matchLabels:
      app: llm-inference
  policyTypes:
  - Ingress
  - Egress

  ingress:
  # Only allow from API gateway namespace
  - from:
    - namespaceSelector:
        matchLabels:
          name: api-gateway
      podSelector:
        matchLabels:
          app: gateway
    ports:
    - protocol: TCP
      port: 8000

  # Allow Prometheus scraping
  - from:
    - namespaceSelector:
        matchLabels:
          name: monitoring
      podSelector:
        matchLabels:
          app: prometheus
    ports:
    - protocol: TCP
      port: 8000

  egress:
  # DNS resolution
  - to:
    - namespaceSelector: {}
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - protocol: UDP
      port: 53

  # Block all other egress (models should be pre-loaded)
  # Add specific rules if external API calls are needed
---
# Pod Security Standards
apiVersion: v1
kind: Pod
metadata:
  name: secure-inference
spec:
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
    runAsGroup: 1000
    fsGroup: 1000
    seccompProfile:
      type: RuntimeDefault

  containers:
  - name: inference
    image: vllm/vllm-openai:latest
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: false  # vLLM needs write access
      capabilities:
        drop: ["ALL"]

    volumeMounts:
    - name: model-cache
      mountPath: /models
      readOnly: true
    - name: tmp
      mountPath: /tmp
    - name: cache
      mountPath: /.cache

  volumes:
  - name: model-cache
    persistentVolumeClaim:
      claimName: models-pvc
      readOnly: true
  - name: tmp
    emptyDir:
      sizeLimit: 10Gi
  - name: cache
    emptyDir:
      sizeLimit: 5Gi
```

### 模型访问的审计日志记录

```yaml
# CloudWatch logging for model access audit
apiVersion: v1
kind: ConfigMap
metadata:
  name: fluent-bit-config
  namespace: logging
data:
  fluent-bit.conf: |
    [SERVICE]
        Parsers_File parsers.conf

    [INPUT]
        Name              tail
        Tag               inference.access
        Path              /var/log/containers/llm-inference*.log
        Parser            docker
        Mem_Buf_Limit     50MB
        Skip_Long_Lines   On

    [FILTER]
        Name              grep
        Match             inference.access
        Regex             log .*"request".*

    [OUTPUT]
        Name              cloudwatch_logs
        Match             inference.access
        region            us-west-2
        log_group_name    /eks/ai-ml/inference-audit
        log_stream_prefix inference-
        auto_create_group true
```

## 参考资料

- [AI on EKS - Best Practices and Blueprints](https://awslabs.github.io/ai-on-eks/)
- [NVIDIA GPU Operator Documentation](https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/overview.html)
- [Amazon EKS Best Practices Guide - AI/ML](https://aws.github.io/aws-eks-best-practices/machine-learning/)
- [vLLM Documentation](https://docs.vllm.ai/)
- [NVIDIA DCGM Documentation](https://docs.nvidia.com/datacenter/dcgm/latest/)
- [Karpenter Documentation](https://karpenter.sh/)
- [EFA User Guide](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/efa.html)
- [FSx for Lustre User Guide](https://docs.aws.amazon.com/fsx/latest/LustreGuide/)

---

**测验**：通过 [AI/ML 最佳实践测验](../quizzes/ai-ml/07-ai-ml-best-practices-quiz.md) 测试你的理解
