# 在 EKS 上构建 Agentic AI 平台

> **支持版本**: EKS 1.31+, vLLM 0.6+, Karpenter 1.0+
> **最后更新**: February 23, 2026

Agentic AI（智能体 AI）不止于简单的问答，它能够自主制定计划、使用工具，并通过迭代实现目标。本章介绍如何在 EKS 上构建生产级 Agentic AI 平台。

## 1. Agentic AI 平台概述

### 什么是 Agentic AI？

Agentic AI 是一种具备以下特征的自主 AI 系统：

```mermaid
flowchart TD
    subgraph AgenticAI [Agentic AI Characteristics]
        Planning[Autonomous Planning]
        Execution[Tool-based Execution]
        Iteration[Iterative Improvement]
        Memory[State and Memory Management]
    end

    subgraph Workflow [Workflow]
        Goal[Goal Setting] --> Plan[Planning]
        Plan --> Execute[Execution]
        Execute --> Evaluate[Evaluation]
        Evaluate --> |Improvement Needed| Plan
        Evaluate --> |Complete| Result[Return Result]
    end

    Planning --> Plan
    Execution --> Execute
    Iteration --> Evaluate
    Memory --> Execute

    classDef agentNode fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef workflowNode fill:#FF9900,stroke:#333,stroke-width:1px,color:black;

    class Planning,Execution,Iteration,Memory agentNode;
    class Goal,Plan,Execute,Evaluate,Result workflowNode;
```

1. **自主规划**：将复杂任务拆解为子任务，并确定执行顺序。
2. **基于工具的执行**：使用包括外部 API、数据库和代码执行器在内的多种工具。
3. **迭代式改进**：评估执行结果，并根据需要修改计划。
4. **状态管理**：为长时间运行的任务维护状态和记忆。

### 为什么需要 Kubernetes

Kubernetes 为 Agentic AI 平台提供以下核心能力：

| 需求 | Kubernetes 解决方案 |
|-------------|---------------------|
| GPU 编排 | Device Plugin, GPU Operator, MIG |
| 自动扩缩容 | HPA, VPA, Karpenter |
| 多租户隔离 | Namespace, NetworkPolicy, ResourceQuota |
| 高可用性 | ReplicaSet, PodDisruptionBudget |
| Service Mesh | Istio, Gateway API |
| 成本优化 | Spot instances, Node consolidation |

### 四个关键技术挑战

构建 Agentic AI 平台时需要解决的关键挑战：

```mermaid
flowchart LR
    subgraph Challenges [Key Technical Challenges]
        GPU[1. GPU Resource Management]
        LLM[2. Multi-LLM Integration]
        Workflow[3. Workflow Orchestration]
        Cost[4. Real-time Cost Optimization]
    end

    GPU --> |Fragmentation, Sharing, Scheduling| GPUSolution[MIG, Time-Slicing, Karpenter]
    LLM --> |Routing, Fallback, Load Balancing| LLMSolution[LiteLLM, Inference Gateway]
    Workflow --> |State Management, Branching, Error Handling| WorkflowSolution[LangGraph, Kagent]
    Cost --> |Caching, Batching, Tiering| CostSolution[Langfuse, Prompt Cache]

    classDef challenge fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef solution fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;

    class GPU,LLM,Workflow,Cost challenge;
    class GPUSolution,LLMSolution,WorkflowSolution,CostSolution solution;
```

---

## 2. GPU 基础设施配置

### GPU 实例类型比较

AWS 上可用的主要 GPU 实例类型：

| 实例 | GPU | GPU 内存 | 用例 | 每小时成本（按需） |
|----------|-----|------------|----------|------------------------|
| **p5.48xlarge** | 8x H100 | 640GB | 大规模训练、超大模型推理 | ~$98.32 |
| **p4d.24xlarge** | 8x A100 | 320GB | 分布式训练、70B+ 模型推理 | ~$32.77 |
| **g5.xlarge** | 1x A10G | 24GB | 中小型模型推理 | ~$1.01 |
| **g5.48xlarge** | 8x A10G | 192GB | 多模型服务 | ~$16.29 |
| **g6.xlarge** | 1x L4 | 24GB | 高性价比推理 | ~$0.80 |
| **g6.48xlarge** | 8x L4 | 192GB | 大规模推理集群 | ~$13.35 |
| **inf2.xlarge** | 1x Inferentia2 | 32GB | AWS 优化推理 | ~$0.76 |

### Multi-Instance GPU (MIG) 配置

NVIDIA A100/H100 GPU 可以通过 MIG 进行物理分区，以隔离多个工作负载。

#### MIG 配置文件（A100 80GB 参考）

| 配置文件 | GPU 内存 | SM 数量 | 用例 |
|---------|-----------|----------|----------|
| 1g.10gb | 10GB | 14 | 小模型推理、开发 |
| 2g.20gb | 20GB | 28 | 7B 模型推理 |
| 3g.40gb | 40GB | 42 | 13B 模型推理 |
| 4g.40gb | 40GB | 56 | 大批量推理 |
| 7g.80gb | 80GB | 98 | 70B 模型、训练 |

#### NVIDIA GPU Operator 部署

```yaml
# gpu-operator-values.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: gpu-operator-config
  namespace: gpu-operator
data:
  mig.strategy: "mixed"  # single or mixed
---
apiVersion: helm.toolkit.fluxcd.io/v2
kind: HelmRelease
metadata:
  name: gpu-operator
  namespace: gpu-operator
spec:
  interval: 10m
  chart:
    spec:
      chart: gpu-operator
      version: "v24.9.0"
      sourceRef:
        kind: HelmRepository
        name: nvidia
        namespace: flux-system
  values:
    operator:
      defaultRuntime: containerd
    mig:
      strategy: mixed
    devicePlugin:
      enabled: true
      config:
        name: time-slicing-config
        default: any
    gfd:
      enabled: true
    dcgmExporter:
      enabled: true
      serviceMonitor:
        enabled: true
```

```bash
# GPU Operator installation
helm repo add nvidia https://helm.ngc.nvidia.com/nvidia
helm repo update

helm install gpu-operator nvidia/gpu-operator \
  --namespace gpu-operator \
  --create-namespace \
  --values gpu-operator-values.yaml

# Check MIG configuration
kubectl get nodes -l nvidia.com/mig.capable=true \
  -o jsonpath='{range .items[*]}{.metadata.name}: {.status.allocatable}{"\n"}{end}'
```

#### MIG 分区配置

```yaml
# mig-config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: mig-parted-config
  namespace: gpu-operator
data:
  config.yaml: |
    version: v1
    mig-configs:
      # Development environment: Small partitions for many users
      development:
        - devices: [0]
          mig-enabled: true
          mig-devices:
            "1g.10gb": 7

      # Production: Medium-sized partitions
      production-inference:
        - devices: [0]
          mig-enabled: true
          mig-devices:
            "2g.20gb": 3
            "1g.10gb": 1

      # Large models: Full GPU usage
      large-model:
        - devices: [0]
          mig-enabled: true
          mig-devices:
            "7g.80gb": 1
```

### Time-Slicing 配置

对于不支持 MIG 的 GPU（A10G、L4 等），Time-Slicing 允许共享 GPU。

```yaml
# time-slicing-config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: time-slicing-config
  namespace: gpu-operator
data:
  any: |
    version: v1
    flags:
      migStrategy: none
    sharing:
      timeSlicing:
        renameByDefault: false
        failRequestsGreaterThanOne: false
        resources:
          - name: nvidia.com/gpu
            replicas: 4  # Split one GPU into 4
---
# Apply Time-Slicing to node
apiVersion: v1
kind: Node
metadata:
  name: gpu-node-1
  labels:
    nvidia.com/device-plugin.config: time-slicing-config
```

#### MIG 与 Time-Slicing 比较

| 特性 | MIG | Time-Slicing |
|----------------|-----|--------------|
| **隔离级别** | 硬件隔离（内存、SM） | 软件隔离（时间分片） |
| **支持的 GPU** | A100, H100 | 所有 NVIDIA GPU |
| **内存保证** | 有保证 | 共享（可能发生争用） |
| **开销** | 低 | 上下文切换开销 |
| **灵活性** | 需要重新配置 | 可动态调整 |
| **用例** | 生产、多租户 | 开发、批处理 |

### Karpenter NodePool 配置

```yaml
# gpu-nodepool.yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: gpu-inference
spec:
  template:
    metadata:
      labels:
        workload-type: inference
    spec:
      requirements:
        - key: kubernetes.io/arch
          operator: In
          values: ["amd64"]
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["on-demand", "spot"]
        - key: node.kubernetes.io/instance-type
          operator: In
          values:
            - g5.xlarge
            - g5.2xlarge
            - g5.4xlarge
            - g6.xlarge
            - g6.2xlarge
        - key: "karpenter.k8s.aws/instance-gpu-count"
          operator: Gt
          values: ["0"]
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: gpu-nodes
      taints:
        - key: nvidia.com/gpu
          value: "true"
          effect: NoSchedule
  limits:
    nvidia.com/gpu: 100
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 5m
    budgets:
      - nodes: "20%"
---
apiVersion: karpenter.k8s.aws/v1
kind: EC2NodeClass
metadata:
  name: gpu-nodes
spec:
  amiFamily: AL2023
  role: KarpenterNodeRole-${CLUSTER_NAME}
  subnetSelectorTerms:
    - tags:
        karpenter.sh/discovery: ${CLUSTER_NAME}
  securityGroupSelectorTerms:
    - tags:
        karpenter.sh/discovery: ${CLUSTER_NAME}
  blockDeviceMappings:
    - deviceName: /dev/xvda
      ebs:
        volumeSize: 200Gi
        volumeType: gp3
        iops: 10000
        throughput: 500
        deleteOnTermination: true
  tags:
    Environment: production
    Workload: ai-inference
```

---

## 3. 模型服务（vLLM）

### vLLM 架构

vLLM 通过以下核心技术提供高性能 LLM 推理：

```mermaid
flowchart TD
    subgraph vLLM [vLLM Core Technologies]
        PagedAttention[PagedAttention]
        ContinuousBatching[Continuous Batching]
        PrefixCaching[Prefix Caching]
        ChunkedPrefill[Chunked Prefill]
    end

    subgraph Benefits [Performance Benefits]
        Memory[Memory Efficiency 95%+]
        Throughput[Throughput 24x Improvement]
        Latency[Latency Minimization]
        Context[Long Context Support]
    end

    PagedAttention --> Memory
    ContinuousBatching --> Throughput
    PrefixCaching --> Latency
    ChunkedPrefill --> Context

    classDef techNode fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef benefitNode fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;

    class PagedAttention,ContinuousBatching,PrefixCaching,ChunkedPrefill techNode;
    class Memory,Throughput,Latency,Context benefitNode;
```

### vLLM Deployment 配置

```yaml
# vllm-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vllm-llama3-70b
  namespace: ai-inference
  labels:
    app: vllm
    model: llama3-70b
spec:
  replicas: 2
  selector:
    matchLabels:
      app: vllm
      model: llama3-70b
  template:
    metadata:
      labels:
        app: vllm
        model: llama3-70b
    spec:
      nodeSelector:
        workload-type: inference
      tolerations:
        - key: nvidia.com/gpu
          operator: Equal
          value: "true"
          effect: NoSchedule
      containers:
        - name: vllm
          image: vllm/vllm-openai:v0.6.4
          ports:
            - containerPort: 8000
              name: http
          env:
            - name: HUGGING_FACE_HUB_TOKEN
              valueFrom:
                secretKeyRef:
                  name: huggingface-token
                  key: token
            - name: VLLM_ATTENTION_BACKEND
              value: "FLASH_ATTN"
          args:
            - "--model"
            - "meta-llama/Meta-Llama-3-70B-Instruct"
            - "--tensor-parallel-size"
            - "4"
            - "--gpu-memory-utilization"
            - "0.95"
            - "--max-model-len"
            - "8192"
            - "--enable-prefix-caching"
            - "--enable-chunked-prefill"
            - "--max-num-batched-tokens"
            - "32768"
            - "--trust-remote-code"
          resources:
            requests:
              nvidia.com/gpu: 4
              memory: "200Gi"
              cpu: "32"
            limits:
              nvidia.com/gpu: 4
              memory: "250Gi"
              cpu: "48"
          readinessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 300
            periodSeconds: 10
            timeoutSeconds: 5
            failureThreshold: 3
          livenessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 600
            periodSeconds: 30
            timeoutSeconds: 10
            failureThreshold: 3
          volumeMounts:
            - name: model-cache
              mountPath: /root/.cache/huggingface
            - name: shm
              mountPath: /dev/shm
      volumes:
        - name: model-cache
          persistentVolumeClaim:
            claimName: model-cache-pvc
        - name: shm
          emptyDir:
            medium: Memory
            sizeLimit: 64Gi
---
apiVersion: v1
kind: Service
metadata:
  name: vllm-llama3-70b
  namespace: ai-inference
spec:
  selector:
    app: vllm
    model: llama3-70b
  ports:
    - port: 8000
      targetPort: 8000
      name: http
  type: ClusterIP
```

### 性能优化设置

#### Tensor Parallelism

将大型模型分布到多个 GPU 上：

```yaml
# Recommended settings by model size
# 7B model: 1 GPU
# 13B model: 1-2 GPU
# 70B model: 4 GPU (A100) or 8 GPU (A10G)
# 405B model: 8 GPU (H100)

args:
  - "--tensor-parallel-size"
  - "4"  # Adjust to match GPU count
```

#### KV Cache 管理

```yaml
args:
  # Allocate 95% of GPU memory to KV cache
  - "--gpu-memory-utilization"
  - "0.95"

  # Block size setting (default: 16)
  - "--block-size"
  - "16"

  # Swap space setting (CPU memory)
  - "--swap-space"
  - "32"  # In GB
```

#### Prefix Caching

针对重复系统提示词的缓存：

```yaml
args:
  - "--enable-prefix-caching"

# Effect: Reduces Time To First Token (TTFT) by 50-80%
# for requests using identical system prompts
```

#### Chunked Prefill

长上下文处理优化：

```yaml
args:
  - "--enable-chunked-prefill"
  - "--max-num-batched-tokens"
  - "32768"

# Effect: Stabilizes response latency for workloads
# with mixed long and short prompts
```

### 模型服务模式

#### 单模型 Pod

```yaml
# Simplest pattern: One Pod serving one model
spec:
  containers:
    - name: vllm
      args:
        - "--model"
        - "meta-llama/Meta-Llama-3-8B-Instruct"
```

#### 使用 llm-d 的解耦服务

分离 Prefill 和 Decode 以进行优化：

```yaml
# llm-d-prefill.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: llm-d-prefill
spec:
  replicas: 2
  template:
    spec:
      containers:
        - name: llm-d
          image: llm-d/prefill:latest
          args:
            - "--role"
            - "prefill"
            - "--model"
            - "meta-llama/Meta-Llama-3-70B-Instruct"
          resources:
            requests:
              nvidia.com/gpu: 4
---
# llm-d-decode.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: llm-d-decode
spec:
  replicas: 4
  template:
    spec:
      containers:
        - name: llm-d
          image: llm-d/decode:latest
          args:
            - "--role"
            - "decode"
            - "--prefill-endpoint"
            - "http://llm-d-prefill:8000"
          resources:
            requests:
              nvidia.com/gpu: 2
```

---

## 4. Inference Gateway

### 基于 Gateway API 的 AI 工作负载路由

扩展 Kubernetes Gateway API，以高效路由 AI 推理工作负载。

### Kgateway + InferencePool 架构

```mermaid
flowchart TD
    Client[Client] --> Gateway[Gateway]
    Gateway --> HTTPRoute[HTTPRoute]
    HTTPRoute --> InferencePool[InferencePool]

    subgraph Pool [InferencePool]
        EP1[vLLM Pod 1]
        EP2[vLLM Pod 2]
        EP3[vLLM Pod 3]
    end

    InferencePool --> EndpointPicker[Endpoint Picker]
    EndpointPicker --> |least-loaded| EP1
    EndpointPicker --> |prefix-aware| EP2

    classDef gatewayNode fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef poolNode fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;

    class Gateway,HTTPRoute gatewayNode;
    class EP1,EP2,EP3,InferencePool poolNode;
```

#### InferencePool CRD

```yaml
# inferencepool.yaml
apiVersion: inference.networking.x-k8s.io/v1alpha1
kind: InferencePool
metadata:
  name: llama3-pool
  namespace: ai-inference
spec:
  targetPortNumber: 8000
  selector:
    matchLabels:
      app: vllm
      model: llama3-70b
  endpointPickerConfig:
    # Load balancing strategy
    extensionRef:
      name: prefix-aware-picker
      group: inference.networking.x-k8s.io
      kind: EndpointPicker
---
apiVersion: inference.networking.x-k8s.io/v1alpha1
kind: EndpointPicker
metadata:
  name: prefix-aware-picker
  namespace: ai-inference
spec:
  type: PrefixAware
  config:
    # Prefix cache hit rate optimization
    prefixHashBuckets: 1024
    fallbackStrategy: LeastLoaded
    loadMetric: pending_requests
---
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: llama3-route
  namespace: ai-inference
spec:
  parentRefs:
    - name: ai-gateway
      namespace: ai-inference
  rules:
    - matches:
        - path:
            type: PathPrefix
            value: /v1/chat/completions
          headers:
            - name: x-model
              value: llama3-70b
      backendRefs:
        - group: inference.networking.x-k8s.io
          kind: InferencePool
          name: llama3-pool
          port: 8000
```

### LiteLLM 集成网关

LiteLLM 将多种 LLM 提供商统一到单一 API 之下。

```yaml
# litellm-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: litellm-gateway
  namespace: ai-gateway
spec:
  replicas: 3
  selector:
    matchLabels:
      app: litellm
  template:
    metadata:
      labels:
        app: litellm
    spec:
      containers:
        - name: litellm
          image: ghcr.io/berriai/litellm:main-v1.55.0
          ports:
            - containerPort: 4000
          env:
            - name: LITELLM_MASTER_KEY
              valueFrom:
                secretKeyRef:
                  name: litellm-secrets
                  key: master-key
            - name: DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: litellm-secrets
                  key: database-url
          volumeMounts:
            - name: config
              mountPath: /app/config.yaml
              subPath: config.yaml
          resources:
            requests:
              cpu: "2"
              memory: "4Gi"
            limits:
              cpu: "4"
              memory: "8Gi"
      volumes:
        - name: config
          configMap:
            name: litellm-config
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: litellm-config
  namespace: ai-gateway
data:
  config.yaml: |
    model_list:
      # Internal vLLM endpoints
      - model_name: llama3-70b
        litellm_params:
          model: openai/meta-llama/Meta-Llama-3-70B-Instruct
          api_base: http://vllm-llama3-70b.ai-inference:8000/v1
          api_key: dummy
        model_info:
          max_tokens: 8192
          input_cost_per_token: 0.0000001
          output_cost_per_token: 0.0000003

      - model_name: llama3-8b
        litellm_params:
          model: openai/meta-llama/Meta-Llama-3-8B-Instruct
          api_base: http://vllm-llama3-8b.ai-inference:8000/v1
          api_key: dummy
        model_info:
          max_tokens: 8192
          input_cost_per_token: 0.00000005
          output_cost_per_token: 0.00000015

      # External providers (for fallback)
      - model_name: gpt-4o
        litellm_params:
          model: gpt-4o
          api_key: os.environ/OPENAI_API_KEY
        model_info:
          max_tokens: 128000
          input_cost_per_token: 0.000005
          output_cost_per_token: 0.000015

      - model_name: claude-3-5-sonnet
        litellm_params:
          model: anthropic/claude-3-5-sonnet-20241022
          api_key: os.environ/ANTHROPIC_API_KEY
        model_info:
          max_tokens: 200000
          input_cost_per_token: 0.000003
          output_cost_per_token: 0.000015

    # Routing settings
    router_settings:
      routing_strategy: usage-based-routing-v2
      enable_pre_call_checks: true
      redis_host: redis.ai-gateway
      redis_port: 6379

    # Fallback settings
    litellm_settings:
      fallbacks:
        - model: llama3-70b
          fallback_models:
            - gpt-4o
            - claude-3-5-sonnet

      # Retry settings
      num_retries: 3
      request_timeout: 300

      # Cost tracking
      success_callback: ["langfuse"]
      failure_callback: ["langfuse"]
---
apiVersion: v1
kind: Service
metadata:
  name: litellm-gateway
  namespace: ai-gateway
spec:
  selector:
    app: litellm
  ports:
    - port: 4000
      targetPort: 4000
  type: ClusterIP
```

#### LiteLLM 使用示例

```python
# litellm_client.py
from openai import OpenAI

# Using LiteLLM gateway
client = OpenAI(
    api_key="sk-litellm-master-key",
    base_url="http://litellm-gateway.ai-gateway:4000/v1"
)

# Call internal model (automatic routing)
response = client.chat.completions.create(
    model="llama3-70b",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Explain Kubernetes in simple terms."}
    ],
    max_tokens=500
)

print(response.choices[0].message.content)

# Automatic fallback to external providers if needed
# (llama3-70b failure -> gpt-4o -> claude-3-5-sonnet in order)
```

---

## 5. RAG 数据层

### Milvus 向量数据库

Milvus 是用于大规模向量搜索的开源数据库。

#### Milvus Operator 部署

```bash
# Install Milvus Operator
helm repo add milvus https://zilliztech.github.io/milvus-helm
helm repo update

helm install milvus-operator milvus/milvus-operator \
  --namespace milvus-system \
  --create-namespace
```

```yaml
# milvus-cluster.yaml
apiVersion: milvus.io/v1beta1
kind: Milvus
metadata:
  name: milvus-cluster
  namespace: ai-data
spec:
  mode: cluster
  dependencies:
    etcd:
      inCluster:
        values:
          replicaCount: 3
          persistence:
            enabled: true
            size: 50Gi
    pulsar:
      inCluster:
        values:
          components:
            autorecovery: false
          proxy:
            replicaCount: 2
          broker:
            replicaCount: 2
    storage:
      inCluster:
        values:
          mode: distributed
          fullnameOverride: milvus-minio
          persistence:
            enabled: true
            size: 500Gi
  components:
    # Query Node - Vector search processing
    queryNode:
      replicas: 3
      resources:
        requests:
          cpu: "4"
          memory: "16Gi"
        limits:
          cpu: "8"
          memory: "32Gi"

    # Index Node - Index building (GPU accelerated)
    indexNode:
      replicas: 2
      resources:
        requests:
          cpu: "4"
          memory: "16Gi"
          nvidia.com/gpu: 1
        limits:
          cpu: "8"
          memory: "32Gi"
          nvidia.com/gpu: 1

    # Data Node - Data processing
    dataNode:
      replicas: 2
      resources:
        requests:
          cpu: "2"
          memory: "8Gi"
        limits:
          cpu: "4"
          memory: "16Gi"

    # Proxy - API gateway
    proxy:
      replicas: 2
      serviceType: ClusterIP
      resources:
        requests:
          cpu: "2"
          memory: "4Gi"
        limits:
          cpu: "4"
          memory: "8Gi"
  config:
    common:
      gracefulTime: 30000
    queryNode:
      gracefulTime: 30000
```

#### Collection Schema 设计

```python
# milvus_schema.py
from pymilvus import (
    connections, Collection, FieldSchema,
    CollectionSchema, DataType, utility
)

# Connect to Milvus
connections.connect(
    alias="default",
    host="milvus-cluster-proxy.ai-data",
    port="19530"
)

# Document collection schema
fields = [
    FieldSchema(name="id", dtype=DataType.VARCHAR, max_length=64, is_primary=True),
    FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=65535),
    FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=1536),
    FieldSchema(name="metadata", dtype=DataType.JSON),
    FieldSchema(name="created_at", dtype=DataType.INT64),
]

schema = CollectionSchema(
    fields=fields,
    description="Document embeddings for RAG"
)

# Create collection
collection = Collection(
    name="documents",
    schema=schema,
    using="default"
)

# Create index
index_params = {
    "metric_type": "COSINE",
    "index_type": "HNSW",  # Or GPU_IVF_FLAT for GPU acceleration
    "params": {
        "M": 16,
        "efConstruction": 256
    }
}

collection.create_index(
    field_name="embedding",
    index_params=index_params
)

# Load collection
collection.load()
```

#### 索引类型比较

| 索引类型 | 特性 | 内存使用 | 搜索速度 | 用例 |
|-----------|----------------|--------------|--------------|----------|
| **FLAT** | 精确搜索 | 高 | 慢 | 小规模、准确性优先 |
| **IVF_FLAT** | 基于聚类 | 中 | 快 | 通用用途 |
| **HNSW** | 基于图 | 高 | 非常快 | 大规模、速度优先 |
| **GPU_IVF_FLAT** | GPU 加速 | 中 | 非常快 | 超大规模、GPU 使用 |
| **SCANN** | 基于量化 | 低 | 快 | 内存受限环境 |

### 文档摄取流水线

```yaml
# document-ingestion-job.yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: document-ingestion
  namespace: ai-data
spec:
  template:
    spec:
      containers:
        - name: ingestion
          image: ai-platform/document-ingestion:latest
          env:
            - name: S3_BUCKET
              value: "my-documents-bucket"
            - name: MILVUS_HOST
              value: "milvus-cluster-proxy.ai-data"
            - name: EMBEDDING_MODEL
              value: "text-embedding-3-large"
            - name: OPENAI_API_KEY
              valueFrom:
                secretKeyRef:
                  name: openai-credentials
                  key: api-key
          resources:
            requests:
              cpu: "4"
              memory: "16Gi"
            limits:
              cpu: "8"
              memory: "32Gi"
          volumeMounts:
            - name: temp-storage
              mountPath: /tmp/documents
      volumes:
        - name: temp-storage
          emptyDir:
            sizeLimit: 100Gi
      restartPolicy: OnFailure
```

#### 分块策略实现

```python
# chunking_strategies.py
from langchain.text_splitter import (
    RecursiveCharacterTextSplitter,
    TokenTextSplitter
)
from langchain_experimental.text_splitter import SemanticChunker
from langchain_openai import OpenAIEmbeddings

# 1. Fixed-size chunking
def fixed_chunking(text: str, chunk_size: int = 1000, overlap: int = 200):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=overlap,
        separators=["\n\n", "\n", ".", "!", "?", ",", " ", ""]
    )
    return splitter.split_text(text)

# 2. Token-based chunking (LLM context window optimization)
def token_chunking(text: str, chunk_size: int = 512, overlap: int = 50):
    splitter = TokenTextSplitter(
        encoding_name="cl100k_base",  # GPT-4 tokenizer
        chunk_size=chunk_size,
        chunk_overlap=overlap
    )
    return splitter.split_text(text)

# 3. Semantic chunking (context preservation optimization)
def semantic_chunking(text: str):
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    splitter = SemanticChunker(
        embeddings=embeddings,
        breakpoint_threshold_type="percentile",
        breakpoint_threshold_amount=95
    )
    return splitter.split_text(text)

# Recommendation: Choose strategy by document type
CHUNKING_STRATEGIES = {
    "code": {"strategy": "fixed", "chunk_size": 2000, "overlap": 400},
    "documentation": {"strategy": "semantic"},
    "chat_logs": {"strategy": "fixed", "chunk_size": 500, "overlap": 100},
    "default": {"strategy": "token", "chunk_size": 512, "overlap": 50}
}
```

### RAG 工作流

```python
# rag_workflow.py
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_milvus import Milvus
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate

# Vector store connection
embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
vectorstore = Milvus(
    embedding_function=embeddings,
    collection_name="documents",
    connection_args={
        "host": "milvus-cluster-proxy.ai-data",
        "port": "19530"
    }
)

# RAG prompt template
RAG_PROMPT = PromptTemplate(
    template="""Answer the question using the following context.
If you cannot find the answer in the context, say "No information available."

Context:
{context}

Question: {question}

Answer:""",
    input_variables=["context", "question"]
)

# LLM setup (using LiteLLM gateway)
llm = ChatOpenAI(
    model="llama3-70b",
    openai_api_base="http://litellm-gateway.ai-gateway:4000/v1",
    openai_api_key="sk-litellm-master-key",
    temperature=0.1
)

# RAG chain configuration
qa_chain = RetrievalQA.from_chain_type(
    llm=llm,
    chain_type="stuff",
    retriever=vectorstore.as_retriever(
        search_type="mmr",
        search_kwargs={"k": 5, "fetch_k": 20}
    ),
    chain_type_kwargs={"prompt": RAG_PROMPT},
    return_source_documents=True
)

# Execute query
result = qa_chain.invoke({"query": "How does Pod scheduling work in Kubernetes?"})
print(result["result"])
```

---

## 6. AI Agent 部署（Kagent）

### Kagent 概述

Kagent 是一种 Kubernetes-native 的 AI Agent 生命周期管理工具。

```mermaid
flowchart TD
    subgraph Kagent [Kagent Architecture]
        Controller[Kagent Controller]
        CRD[Agent CRD]
        Runtime[Agent Runtime]
    end

    subgraph Agent [AI Agent]
        LLM[LLM Backend]
        Tools[Tool Set]
        Memory[Memory Store]
        State[State Management]
    end

    Controller --> CRD
    CRD --> Runtime
    Runtime --> Agent

    LLM --> |Inference| Runtime
    Tools --> |Execution| Runtime
    Memory --> |Store/Query| Runtime
    State --> |Management| Runtime

    classDef kagentNode fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef agentNode fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;

    class Controller,CRD,Runtime kagentNode;
    class LLM,Tools,Memory,State agentNode;
```

### Agent CRD 定义

```yaml
# agent-crd.yaml
apiVersion: kagent.dev/v1alpha1
kind: Agent
metadata:
  name: research-agent
  namespace: ai-agents
spec:
  # LLM backend settings
  llm:
    provider: litellm
    model: llama3-70b
    endpoint: http://litellm-gateway.ai-gateway:4000/v1
    temperature: 0.7
    maxTokens: 4096

  # Agent system prompt
  systemPrompt: |
    You are a research assistant that helps users find and analyze information.
    You have access to the following tools:
    - web_search: Search the web for information
    - document_search: Search internal documents
    - calculator: Perform calculations

    Always cite your sources and provide accurate information.

  # Tool definitions
  tools:
    - name: web_search
      type: http
      spec:
        url: http://search-api.tools:8080/search
        method: POST
        headers:
          Content-Type: application/json

    - name: document_search
      type: milvus
      spec:
        host: milvus-cluster-proxy.ai-data
        port: 19530
        collection: documents
        topK: 5

    - name: calculator
      type: python
      spec:
        code: |
          def calculate(expression: str) -> str:
              return str(eval(expression))

  # Memory settings
  memory:
    type: redis
    config:
      host: redis.ai-agents
      port: 6379
      ttl: 3600

  # Resource limits
  resources:
    requests:
      cpu: "500m"
      memory: "512Mi"
    limits:
      cpu: "2"
      memory: "2Gi"

  # Scaling settings
  replicas: 2
  autoscaling:
    enabled: true
    minReplicas: 2
    maxReplicas: 10
    targetCPUUtilization: 70
```

### LangGraph 工作流编排

使用 LangGraph 实现复杂 AI 工作流。

```python
# langgraph_workflow.py
from typing import TypedDict, Annotated, Sequence
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolExecutor
import operator

# State definition
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    current_step: str
    iteration: int
    max_iterations: int
    tools_output: dict

# LLM setup
llm = ChatOpenAI(
    model="llama3-70b",
    openai_api_base="http://litellm-gateway.ai-gateway:4000/v1",
    openai_api_key="sk-litellm-master-key"
)

# Node functions
def planner(state: AgentState) -> AgentState:
    """Node that creates task plans"""
    messages = state["messages"]

    planning_prompt = """Based on the user's request, create a step-by-step plan.
    Format your response as a numbered list of steps."""

    response = llm.invoke(messages + [HumanMessage(content=planning_prompt)])

    return {
        "messages": [response],
        "current_step": "execute",
        "iteration": state["iteration"]
    }

def executor(state: AgentState) -> AgentState:
    """Node that executes plans"""
    messages = state["messages"]

    execution_prompt = """Execute the current step of the plan.
    If you need to use a tool, specify the tool and parameters."""

    response = llm.invoke(messages + [HumanMessage(content=execution_prompt)])

    return {
        "messages": [response],
        "current_step": "evaluate",
        "iteration": state["iteration"]
    }

def evaluator(state: AgentState) -> AgentState:
    """Node that evaluates results"""
    messages = state["messages"]

    evaluation_prompt = """Evaluate the execution result.
    Respond with either:
    - COMPLETE: if the task is fully done
    - CONTINUE: if more steps are needed
    - RETRY: if the current step needs to be retried"""

    response = llm.invoke(messages + [HumanMessage(content=evaluation_prompt)])

    return {
        "messages": [response],
        "current_step": "route",
        "iteration": state["iteration"] + 1
    }

def router(state: AgentState) -> str:
    """Router that determines next step"""
    last_message = state["messages"][-1].content.upper()

    if state["iteration"] >= state["max_iterations"]:
        return "end"

    if "COMPLETE" in last_message:
        return "end"
    elif "RETRY" in last_message:
        return "execute"
    else:
        return "plan"

# Graph construction
workflow = StateGraph(AgentState)

# Add nodes
workflow.add_node("plan", planner)
workflow.add_node("execute", executor)
workflow.add_node("evaluate", evaluator)

# Add edges
workflow.set_entry_point("plan")
workflow.add_edge("plan", "execute")
workflow.add_edge("execute", "evaluate")
workflow.add_conditional_edges(
    "evaluate",
    router,
    {
        "plan": "plan",
        "execute": "execute",
        "end": END
    }
)

# Compile graph
app = workflow.compile()

# Execute
initial_state = {
    "messages": [HumanMessage(content="Research the latest trends in Kubernetes security")],
    "current_step": "plan",
    "iteration": 0,
    "max_iterations": 5,
    "tools_output": {}
}

result = app.invoke(initial_state)
```

### 多 Agent 协作模式

#### Supervisor 模式

```python
# supervisor_pattern.py
from langgraph.graph import StateGraph, END
from typing import TypedDict, Literal

class SupervisorState(TypedDict):
    messages: list
    next_agent: str
    task_status: dict

def supervisor(state: SupervisorState) -> SupervisorState:
    """Supervisor that delegates tasks to appropriate agents"""

    supervisor_prompt = """You are a supervisor managing a team of agents:
    - researcher: Finds and analyzes information
    - coder: Writes and reviews code
    - writer: Creates documentation and reports

    Based on the current task, decide which agent should handle it next.
    Respond with the agent name or 'FINISH' if the task is complete."""

    response = llm.invoke(state["messages"] + [HumanMessage(content=supervisor_prompt)])
    next_agent = response.content.strip().lower()

    return {
        "messages": state["messages"] + [response],
        "next_agent": next_agent
    }

def researcher(state: SupervisorState) -> SupervisorState:
    """Information gathering agent"""
    research_response = llm.invoke(
        state["messages"] +
        [HumanMessage(content="Research the topic and provide findings.")]
    )
    return {"messages": state["messages"] + [research_response]}

def coder(state: SupervisorState) -> SupervisorState:
    """Coding agent"""
    code_response = llm.invoke(
        state["messages"] +
        [HumanMessage(content="Write or review code for the task.")]
    )
    return {"messages": state["messages"] + [code_response]}

def writer(state: SupervisorState) -> SupervisorState:
    """Documentation agent"""
    write_response = llm.invoke(
        state["messages"] +
        [HumanMessage(content="Create documentation or a report.")]
    )
    return {"messages": state["messages"] + [write_response]}

def route_to_agent(state: SupervisorState) -> Literal["researcher", "coder", "writer", "end"]:
    next_agent = state["next_agent"]
    if next_agent == "finish":
        return "end"
    return next_agent

# Graph construction
supervisor_graph = StateGraph(SupervisorState)

supervisor_graph.add_node("supervisor", supervisor)
supervisor_graph.add_node("researcher", researcher)
supervisor_graph.add_node("coder", coder)
supervisor_graph.add_node("writer", writer)

supervisor_graph.set_entry_point("supervisor")

supervisor_graph.add_conditional_edges(
    "supervisor",
    route_to_agent,
    {
        "researcher": "researcher",
        "coder": "coder",
        "writer": "writer",
        "end": END
    }
)

# Return to supervisor after each agent completes
for agent in ["researcher", "coder", "writer"]:
    supervisor_graph.add_edge(agent, "supervisor")

multi_agent_app = supervisor_graph.compile()
```

---

## 7. 监控与运维

### Langfuse GenAI 可观测性

Langfuse 是面向 LLM 应用的可观测性平台。

```yaml
# langfuse-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: langfuse
  namespace: ai-monitoring
spec:
  replicas: 2
  selector:
    matchLabels:
      app: langfuse
  template:
    metadata:
      labels:
        app: langfuse
    spec:
      containers:
        - name: langfuse
          image: langfuse/langfuse:latest
          ports:
            - containerPort: 3000
          env:
            - name: DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: langfuse-secrets
                  key: database-url
            - name: NEXTAUTH_SECRET
              valueFrom:
                secretKeyRef:
                  name: langfuse-secrets
                  key: nextauth-secret
            - name: NEXTAUTH_URL
              value: "https://langfuse.example.com"
            - name: SALT
              valueFrom:
                secretKeyRef:
                  name: langfuse-secrets
                  key: salt
          resources:
            requests:
              cpu: "1"
              memory: "2Gi"
            limits:
              cpu: "2"
              memory: "4Gi"
---
apiVersion: v1
kind: Service
metadata:
  name: langfuse
  namespace: ai-monitoring
spec:
  selector:
    app: langfuse
  ports:
    - port: 3000
      targetPort: 3000
  type: ClusterIP
```

#### Langfuse 集成代码

```python
# langfuse_integration.py
from langfuse import Langfuse
from langfuse.decorators import observe, langfuse_context
from openai import OpenAI

# Initialize Langfuse client
langfuse = Langfuse(
    public_key="pk-lf-xxx",
    secret_key="sk-lf-xxx",
    host="http://langfuse.ai-monitoring:3000"
)

client = OpenAI(
    api_key="sk-litellm-master-key",
    base_url="http://litellm-gateway.ai-gateway:4000/v1"
)

@observe()
def rag_query(user_query: str, user_id: str = None) -> str:
    """Track RAG queries with Langfuse"""

    # Set user ID
    langfuse_context.update_current_trace(
        user_id=user_id,
        tags=["rag", "production"]
    )

    # Document retrieval (tracked as separate span)
    with langfuse_context.observe(name="document_retrieval") as span:
        documents = search_documents(user_query)
        span.update(
            input={"query": user_query},
            output={"doc_count": len(documents)},
            metadata={"retrieval_method": "mmr"}
        )

    # LLM call
    with langfuse_context.observe(name="llm_generation") as span:
        response = client.chat.completions.create(
            model="llama3-70b",
            messages=[
                {"role": "system", "content": "Answer based on the context."},
                {"role": "user", "content": f"Context: {documents}\n\nQuestion: {user_query}"}
            ],
            max_tokens=1000
        )

        answer = response.choices[0].message.content

        # Track token usage and cost
        span.update(
            input={"messages": messages},
            output={"response": answer},
            usage={
                "input": response.usage.prompt_tokens,
                "output": response.usage.completion_tokens,
                "total": response.usage.total_tokens
            },
            metadata={
                "model": "llama3-70b",
                "temperature": 0.7
            }
        )

    return answer

# Collect feedback
def collect_feedback(trace_id: str, score: float, comment: str = None):
    """Record user feedback to Langfuse"""
    langfuse.score(
        trace_id=trace_id,
        name="user_feedback",
        value=score,
        comment=comment
    )
```

### GPU 监控（DCGM）

```yaml
# dcgm-exporter.yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: dcgm-exporter
  namespace: gpu-monitoring
spec:
  selector:
    matchLabels:
      app: dcgm-exporter
  template:
    metadata:
      labels:
        app: dcgm-exporter
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
          securityContext:
            privileged: true
          volumeMounts:
            - name: pod-resources
              mountPath: /var/lib/kubelet/pod-resources
      volumes:
        - name: pod-resources
          hostPath:
            path: /var/lib/kubelet/pod-resources
---
apiVersion: v1
kind: Service
metadata:
  name: dcgm-exporter
  namespace: gpu-monitoring
  labels:
    app: dcgm-exporter
spec:
  selector:
    app: dcgm-exporter
  ports:
    - port: 9400
      targetPort: 9400
      name: metrics
  clusterIP: None
---
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: dcgm-exporter
  namespace: gpu-monitoring
spec:
  selector:
    matchLabels:
      app: dcgm-exporter
  endpoints:
    - port: metrics
      interval: 15s
```

#### 关键 GPU 指标

| 指标 | 描述 | 阈值 |
|--------|-------------|-----------|
| `DCGM_FI_DEV_GPU_UTIL` | GPU 利用率 | > 80% 正常 |
| `DCGM_FI_DEV_MEM_COPY_UTIL` | 内存带宽利用率 | > 70% 警惕 |
| `DCGM_FI_DEV_FB_USED` | 帧缓冲使用量 | 建议 < 95% |
| `DCGM_FI_DEV_GPU_TEMP` | GPU 温度 | 建议 < 85C |
| `DCGM_FI_DEV_POWER_USAGE` | 功耗 | 低于 TDP 的 90% |
| `DCGM_FI_DEV_SM_CLOCK` | SM 时钟速度 | 保持默认 |

### 成本优化策略

#### 1. Prompt Caching

```python
# prompt_caching.py
import hashlib
import redis

redis_client = redis.Redis(host="redis.ai-cache", port=6379)

def get_cached_response(prompt: str, model: str) -> str | None:
    """Retrieve cached response"""
    cache_key = hashlib.sha256(f"{model}:{prompt}".encode()).hexdigest()
    cached = redis_client.get(cache_key)
    return cached.decode() if cached else None

def cache_response(prompt: str, model: str, response: str, ttl: int = 3600):
    """Cache response"""
    cache_key = hashlib.sha256(f"{model}:{prompt}".encode()).hexdigest()
    redis_client.setex(cache_key, ttl, response)

def query_with_cache(prompt: str, model: str = "llama3-70b") -> str:
    """Query with caching"""
    # Check cache
    cached = get_cached_response(prompt, model)
    if cached:
        return cached

    # LLM call
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}]
    )
    result = response.choices[0].message.content

    # Cache result
    cache_response(prompt, model, result)
    return result
```

#### 2. 分层模型选择

```python
# tiered_model_selection.py
from enum import Enum

class TaskComplexity(Enum):
    SIMPLE = "simple"      # Classification, extraction, simple QA
    MODERATE = "moderate"  # Summarization, translation, general conversation
    COMPLEX = "complex"    # Analysis, reasoning, code generation

MODEL_TIERS = {
    TaskComplexity.SIMPLE: {
        "model": "llama3-8b",
        "cost_per_1k_tokens": 0.0001
    },
    TaskComplexity.MODERATE: {
        "model": "llama3-70b",
        "cost_per_1k_tokens": 0.0005
    },
    TaskComplexity.COMPLEX: {
        "model": "gpt-4o",
        "cost_per_1k_tokens": 0.01
    }
}

def classify_task_complexity(task: str) -> TaskComplexity:
    """Classify task complexity (using lightweight model)"""
    classification_prompt = f"""Classify the complexity of this task as SIMPLE, MODERATE, or COMPLEX:
    Task: {task}

    SIMPLE: Classification, extraction, simple QA
    MODERATE: Summarization, translation, general conversation
    COMPLEX: Analysis, reasoning, code generation

    Respond with only the classification."""

    response = client.chat.completions.create(
        model="llama3-8b",  # Use small model for classification
        messages=[{"role": "user", "content": classification_prompt}],
        max_tokens=10
    )

    classification = response.choices[0].message.content.strip().upper()
    return TaskComplexity[classification]

def execute_with_optimal_model(task: str) -> str:
    """Execute task with optimal model"""
    complexity = classify_task_complexity(task)
    model_config = MODEL_TIERS[complexity]

    response = client.chat.completions.create(
        model=model_config["model"],
        messages=[{"role": "user", "content": task}]
    )

    return response.choices[0].message.content
```

#### 3. 批处理

```yaml
# batch-processing-job.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: batch-inference
  namespace: ai-batch
spec:
  schedule: "0 2 * * *"  # Daily at 2 AM
  jobTemplate:
    spec:
      template:
        spec:
          containers:
            - name: batch-processor
              image: ai-platform/batch-processor:latest
              env:
                - name: BATCH_SIZE
                  value: "100"
                - name: MODEL
                  value: "llama3-70b"
                - name: QUEUE_URL
                  value: "redis://redis.ai-batch:6379/0"
              resources:
                requests:
                  cpu: "4"
                  memory: "8Gi"
          restartPolicy: OnFailure
```

#### 4. Spot Instance 使用

```yaml
# spot-nodepool.yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: gpu-spot
spec:
  template:
    spec:
      requirements:
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["spot"]
        - key: node.kubernetes.io/instance-type
          operator: In
          values:
            - g5.xlarge
            - g5.2xlarge
            - g6.xlarge
      taints:
        - key: spot-instance
          value: "true"
          effect: NoSchedule
  limits:
    nvidia.com/gpu: 50
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 1m
```

---

## 8. 评估与质量管理

### Ragas 框架

Ragas 是用于评估 RAG 系统质量的框架。

```python
# ragas_evaluation.py
from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_precision,
    context_recall,
    answer_correctness
)
from datasets import Dataset

# Construct evaluation dataset
eval_data = {
    "question": [
        "What is a Kubernetes Pod?",
        "How does HPA work?"
    ],
    "answer": [
        "A Pod is the smallest deployable computing unit in Kubernetes.",
        "HPA automatically adjusts the number of Pods based on CPU utilization."
    ],
    "contexts": [
        ["A Pod is a group of one or more containers.", "Pods have shared storage and network."],
        ["HPA monitors metrics.", "It scales based on configured thresholds."]
    ],
    "ground_truth": [
        "A Pod is the smallest deployable computing unit that can be created and managed in Kubernetes.",
        "HPA automatically adjusts the number of workload replicas based on observed metrics (CPU, memory, etc.)."
    ]
}

dataset = Dataset.from_dict(eval_data)

# Run evaluation
results = evaluate(
    dataset,
    metrics=[
        faithfulness,        # Is the answer faithful to context
        answer_relevancy,    # Is the answer relevant to question
        context_precision,   # Is retrieved context precise
        context_recall,      # Was all necessary context retrieved
        answer_correctness   # Does answer match ground truth
    ]
)

print(results)
# {'faithfulness': 0.92, 'answer_relevancy': 0.88, 'context_precision': 0.85, ...}
```

#### 自动化评估流水线

```yaml
# ragas-evaluation-cronjob.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: ragas-evaluation
  namespace: ai-qa
spec:
  schedule: "0 6 * * *"  # Daily at 6 AM
  jobTemplate:
    spec:
      template:
        spec:
          containers:
            - name: evaluator
              image: ai-platform/ragas-evaluator:latest
              env:
                - name: EVAL_DATASET_PATH
                  value: "s3://ai-datasets/eval/golden-set.json"
                - name: RAG_ENDPOINT
                  value: "http://rag-api.ai-inference:8000"
                - name: LANGFUSE_HOST
                  value: "http://langfuse.ai-monitoring:3000"
                - name: MIN_FAITHFULNESS
                  value: "0.85"
                - name: MIN_RELEVANCY
                  value: "0.80"
              resources:
                requests:
                  cpu: "2"
                  memory: "4Gi"
          restartPolicy: OnFailure
```

### A/B 测试

```yaml
# ab-testing-config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: ab-testing-config
  namespace: ai-inference
data:
  config.yaml: |
    experiments:
      - name: llama3-70b-vs-gpt4o
        traffic_split:
          variant_a:
            model: llama3-70b
            weight: 80
          variant_b:
            model: gpt-4o
            weight: 20
        metrics:
          - latency_p99
          - user_satisfaction
          - cost_per_query
        duration_days: 14

      - name: chunk-size-experiment
        traffic_split:
          variant_a:
            chunk_size: 512
            weight: 50
          variant_b:
            chunk_size: 1024
            weight: 50
        metrics:
          - context_precision
          - answer_relevancy
        duration_days: 7
```

---

## 9. 核心技术栈摘要

| 技术 | 用途 | 关键特性 |
|-----------|---------|--------------|
| **Kagent** | AI Agent 生命周期 | 基于 CRD 的 Agent 管理、自动扩缩容 |
| **Kgateway** | Inference Gateway | InferencePool、Prefix-aware 路由 |
| **Milvus** | 向量数据库 | 大规模向量搜索、GPU 加速索引 |
| **Ragas** | RAG 评估 | 忠实度、相关性、准确性指标 |
| **LiteLLM** | LLM 集成网关 | Provider 抽象、fallback、成本跟踪 |
| **LangGraph** | 工作流编排 | 状态管理、条件分支、错误处理 |
| **Langfuse** | GenAI 可观测性 | 请求追踪、成本分析、反馈收集 |
| **vLLM** | 高性能推理 | PagedAttention、连续批处理、prefix caching |
| **Karpenter** | Node 供应 | GPU Node 自动扩缩容、Spot 管理 |
| **DCGM** | GPU 监控 | 利用率、温度、功耗指标 |

---

## 10. 后续步骤

### 练习测验

要验证你对 Agentic AI 平台的理解，请完成以下测验：
- [Agentic AI 平台测验](../quizzes/ai-ml/08-agentic-ai-platform-quiz.md)

### 相关文档

- [vLLM Deployment 详细指南](./02-vllm-deployment.md) - 详细的 vLLM 安装与优化
- [AI/ML 工作负载](./01-ai-ml-workloads.md) - Kubernetes 中的 AI/ML 工作负载管理

### 参考资料

- [EKS 上的 AI](https://awslabs.github.io/ai-on-eks/) - 在 EKS 上部署 AI/ML 工作负载的 AWS 指南与示例
- [vLLM 官方文档](https://docs.vllm.ai/)
- [LangGraph 文档](https://langchain-ai.github.io/langgraph/)
- [Milvus 文档](https://milvus.io/docs)
- [Langfuse 文档](https://langfuse.com/docs)
- [NVIDIA GPU Operator](https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/)
- [AI 的 Gateway API](https://gateway-api.sigs.k8s.io/)
