# EKS 上的 Agentic AI 平台测验

本测验用于检验你对在 Amazon EKS 上构建 Agentic AI 平台的理解，包括 GPU 管理（MIG/Time-Slicing）、vLLM inference server、Inference Gateway、RAG（Retrieval-Augmented Generation）、Kagent、LangGraph 和 Langfuse observability。

## 测验概览
- GPU 资源管理（MIG、Time-Slicing）
- vLLM Inference Server 部署与优化
- Kubernetes Gateway API 和 Inference Gateway
- RAG 架构与实现
- Kagent（Kubernetes AI Agent）
- LangGraph 工作流编排
- 使用 Langfuse 进行 LLM Observability

## 选择题

### 1. vLLM 的 PagedAttention 技术主要解决什么问题？

A. 更快的模型训练
B. 由于 GPU 内存碎片化导致的内存使用低效
C. 降低网络延迟
D. 模型参数压缩

<details>
<summary>查看答案</summary>

**答案：B. 由于 GPU 内存碎片化导致的内存使用低效**

**解释：**
vLLM 的 PagedAttention 以页面为单位管理 KV（Key-Value）cache，用于解决 GPU 内存碎片化问题。这使得在相同 GPU 内存下可以并发处理 2-4 倍更多的请求。

**PagedAttention 的工作方式：**
- 将 KV cache 拆分为固定大小的块（页面）
- 支持使用非连续内存空间
- 通过动态内存分配/释放防止碎片化

```yaml
# vLLM Deployment Example
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vllm-server
spec:
  template:
    spec:
      containers:
      - name: vllm
        image: vllm/vllm-openai:latest
        args:
          - "--model"
          - "meta-llama/Llama-2-7b-chat-hf"
          - "--tensor-parallel-size"
          - "1"
          - "--gpu-memory-utilization"
          - "0.9"  # 90% GPU memory utilization
        resources:
          limits:
            nvidia.com/gpu: 1
```

**PagedAttention 的优势：**
- 内存效率提升 2-4 倍
- 吞吐量提升 2-4 倍
- 支持更长的上下文长度

</details>

### 2. 以下哪一项不是 Inference Gateway 的主要职责？

A. 将流量路由到多个 LLM 后端
B. 请求速率限制
C. 管理模型训练任务
D. 负载均衡和故障转移

<details>
<summary>查看答案</summary>

**答案：C. 管理模型训练任务**

**解释：**
Inference Gateway 负责处理推理请求的路由、负载均衡和速率限制。模型训练由独立系统管理（例如 Kubeflow、Ray）。

**Inference Gateway 核心功能：**
- 多模型后端路由
- 请求速率限制和配额管理
- A/B 测试和 Canary 部署
- 认证/授权处理
- 指标收集和监控

```yaml
# Inference Gateway Configuration with Gateway API
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: inference-gateway
spec:
  gatewayClassName: istio
  listeners:
  - name: http
    port: 80
    protocol: HTTP

---
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: llm-routes
spec:
  parentRefs:
  - name: inference-gateway
  rules:
  - matches:
    - path:
        type: PathPrefix
        value: /v1/chat/completions
    backendRefs:
    - name: vllm-llama
      port: 8000
      weight: 80
    - name: vllm-mistral
      port: 8000
      weight: 20
```

</details>

### 3. Vector Database 在 RAG（Retrieval-Augmented Generation）架构中的作用是什么？

A. 存储 LLM 模型权重
B. 存储文档嵌入向量并进行相似度搜索
C. 管理用户认证信息
D. 记录 API 请求日志

<details>
<summary>查看答案</summary>

**答案：B. 存储文档嵌入向量并进行相似度搜索**

**解释：**
Vector Database 存储使用 embedding 模型从文档转换得到的向量，并快速搜索与查询向量相似的文档。这使 LLM 能够引用相关上下文并生成更准确的响应。

**RAG Pipeline：**
```
[Document] -> [Embedding Model] -> [Vector DB]
               ^
[Query] -> [Embedding Model] -> [Similarity Search] -> [Relevant Docs] -> [LLM] -> [Response]
```

```yaml
# Deploying Qdrant Vector DB in Kubernetes
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: qdrant
spec:
  serviceName: qdrant
  replicas: 1
  template:
    spec:
      containers:
      - name: qdrant
        image: qdrant/qdrant:latest
        ports:
        - containerPort: 6333
          name: http
        - containerPort: 6334
          name: grpc
        volumeMounts:
        - name: storage
          mountPath: /qdrant/storage
  volumeClaimTemplates:
  - metadata:
      name: storage
    spec:
      accessModes: ["ReadWriteOnce"]
      resources:
        requests:
          storage: 100Gi
```

**常见 Vector Database：**
- Qdrant、Milvus、Pinecone
- PostgreSQL + pgvector
- Elasticsearch（Dense Vector）

</details>

### 4. LangGraph 的关键特性是什么？

A. 只支持简单的线性链
B. 支持循环的基于状态的图工作流
C. 只能使用单个 LLM
D. 不支持内存

<details>
<summary>查看答案</summary>

**答案：B. 支持循环的基于状态的图工作流**

**解释：**
LangGraph 是基于 LangChain 的图工作流框架，允许将复杂的 AI agent 逻辑实现为基于状态的图。它支持循环，可用于实现迭代式决策循环。

**LangGraph 核心概念：**
- **StateGraph**：管理状态的图结构
- **Node**：单个处理步骤（LLM 调用、工具执行等）
- **Edge**：节点之间的转换条件
- **Cycle**：条件循环（例如自我反思循环）

```python
# LangGraph Agent Example
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated

class AgentState(TypedDict):
    messages: list
    next_action: str

def call_llm(state: AgentState) -> AgentState:
    # LLM call logic
    return {"messages": state["messages"] + [response]}

def call_tool(state: AgentState) -> AgentState:
    # Tool execution logic
    return {"messages": state["messages"] + [tool_result]}

def should_continue(state: AgentState) -> str:
    if "FINAL_ANSWER" in state["messages"][-1]:
        return "end"
    return "tool"

# Build graph
workflow = StateGraph(AgentState)
workflow.add_node("agent", call_llm)
workflow.add_node("tool", call_tool)
workflow.add_edge("tool", "agent")  # Return to agent after tool execution
workflow.add_conditional_edges(
    "agent",
    should_continue,
    {"tool": "tool", "end": END}
)
workflow.set_entry_point("agent")

app = workflow.compile()
```

</details>

### 5. 以下哪项不是 Langfuse 跟踪的指标？

A. Token 使用量
B. 响应延迟
C. GPU 温度
D. LLM 调用成本

<details>
<summary>查看答案</summary>

**答案：C. GPU 温度**

**解释：**
Langfuse 是面向 LLM 应用的 observability 工具，用于跟踪 LLM 专属指标，例如 token 使用量、延迟和成本。GPU 温度是由 DCGM 或 Prometheus 收集的基础设施级指标。

**Langfuse 主要功能：**
- 基于 Trace 的 LLM 调用跟踪
- Token 使用量和成本分析
- Prompt 版本管理
- 用户反馈收集
- 质量评估

```yaml
# Langfuse Kubernetes Deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: langfuse
spec:
  template:
    spec:
      containers:
      - name: langfuse
        image: langfuse/langfuse:latest
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
        ports:
        - containerPort: 3000
```

```python
# Langfuse Integration in Python
from langfuse import Langfuse

langfuse = Langfuse(
    public_key="pk-...",
    secret_key="sk-...",
    host="https://langfuse.internal.svc"
)

# Track LLM call
trace = langfuse.trace(name="chat-completion")
generation = trace.generation(
    name="llm-call",
    model="llama-2-7b",
    input={"messages": [...]},
    output=response,
    usage={"input_tokens": 150, "output_tokens": 200}
)
```

</details>

### 6. Kagent 的主要目的是什么？

A. Kubernetes 集群监控
B. 使 AI agent 能够与 Kubernetes API 交互，以实现自动化集群管理
C. 构建容器镜像
D. 管理网络策略

<details>
<summary>查看答案</summary>

**答案：B. 使 AI agent 能够与 Kubernetes API 交互，以实现自动化集群管理**

**解释：**
Kagent 是一个允许 AI agent 理解并管理 Kubernetes 集群的框架。它将自然语言命令转换为 Kubernetes API 调用，并通过分析集群状态实现自动化运维。

**Kagent 功能：**
- 基于自然语言的集群管理
- 自动生成并执行 kubectl 命令
- 故障排查自动化
- 资源优化建议

```yaml
# Kagent CRD Example
apiVersion: kagent.dev/v1alpha1
kind: Agent
metadata:
  name: cluster-operator
spec:
  llm:
    provider: openai
    model: gpt-4
  tools:
    - name: kubectl
      permissions:
        - apiGroups: ["*"]
          resources: ["*"]
          verbs: ["get", "list", "watch", "create", "update", "patch"]
    - name: prometheus
      endpoint: http://prometheus:9090
  systemPrompt: |
    You are a Kubernetes cluster operator.
    Analyze cluster state and help users manage their workloads.
```

```python
# Kagent Usage Example
from kagent import KubernetesAgent

agent = KubernetesAgent(
    llm=ChatOpenAI(model="gpt-4"),
    kubeconfig="/path/to/kubeconfig"
)

# Manage cluster with natural language
response = agent.run(
    "Find Pods in the production namespace that restarted due to OOMKilled "
    "and double their memory limits"
)
```

</details>

### 7. 将 GPU Time-Slicing 与 MIG 一起使用有什么好处？

A. 简单地将 GPU 数量翻倍
B. 在 MIG 分区内进一步进行 Time-Slicing，实现更细粒度的资源划分
C. 自动扩展内存容量
D. 增加网络带宽

<details>
<summary>查看答案</summary>

**答案：B. 在 MIG 分区内进一步进行 Time-Slicing，实现更细粒度的资源划分**

**解释：**
通过 MIG 创建物理隔离的 GPU 实例后，在每个 MIG 实例内应用 Time-Slicing 可以容纳更多工作负载。

**MIG + Time-Slicing 组合：**
```
A100 GPU (40GB)
+-- MIG 3g.20gb (Instance 1) - 20GB
|   +-- Time-Slice 1 (Inference Workload A)
|   +-- Time-Slice 2 (Inference Workload B)
+-- MIG 3g.20gb (Instance 2) - 20GB
    +-- Time-Slice 1 (Inference Workload C)
    +-- Time-Slice 2 (Inference Workload D)
```

```yaml
# MIG + Time-Slicing Configuration
apiVersion: v1
kind: ConfigMap
metadata:
  name: nvidia-device-plugin-config
data:
  config.yaml: |
    version: v1
    flags:
      migStrategy: mixed
    sharing:
      timeSlicing:
        resources:
        # Apply Time-Slicing to MIG instances
        - name: nvidia.com/mig-3g.20gb
          replicas: 2
```

**优势：**
- MIG 的内存隔离 + Time-Slicing 的灵活性
- 容纳更多小型推理工作负载
- 在 QoS 保证和利用率提升之间取得平衡

</details>

### 8. vLLM 的 Continuous Batching 提供什么优势？

A. 固定批大小
B. 将新请求动态添加到现有批次中，以提高 GPU 利用率
C. 仅处理单个请求
D. 只在 CPU 上运行

<details>
<summary>查看答案</summary>

**答案：B. 将新请求动态添加到现有批次中，以提高 GPU 利用率**

**解释：**
Continuous Batching 不同于静态批处理，它会将新请求动态添加到正在处理的批次中，并立即移除已完成的请求。这可以最大化 GPU 利用率。

**Static Batching 与 Continuous Batching：**
```
# Static Batching (Traditional)
[Request1, Request2, Request3] -> Wait for all to complete -> Return results
(Even short requests wait for long ones to finish)

# Continuous Batching (vLLM)
[Request1, Request2, Request3]
  | Request1 complete, return immediately
[Request2, Request3, Request4 added]
  | Request2 complete, return immediately
[Request3, Request4, Request5 added]
...
```

```python
# vLLM Server Continuous Batching Configuration
from vllm import LLM, SamplingParams

llm = LLM(
    model="meta-llama/Llama-2-7b-chat-hf",
    tensor_parallel_size=1,
    max_num_batched_tokens=4096,  # Max tokens per batch
    max_num_seqs=256,  # Concurrent sequences
)
```

**优势：**
- 最小化 GPU 空闲时间
- 降低平均响应时间
- 吞吐量提升 2-4 倍

</details>

### 9. 在 RAG 系统中确定 Chunk Size 时，以下哪项不是需要考虑的因素？

A. Embedding 模型的最大 token 数
B. LLM 上下文窗口大小
C. GPU 温度阈值
D. 文档的语义单元（段落、章节）

<details>
<summary>查看答案</summary>

**答案：C. GPU 温度阈值**

**解释：**
Chunk Size 是拆分文档的大小，应考虑 embedding 模型的 token 限制、LLM 上下文大小以及文档的语义结构。GPU 温度属于基础设施相关指标，与 Chunk Size 无关。

**Chunk Size 因素：**
1. **Embedding 模型限制**：通常为 512-8192 tokens
2. **LLM 上下文**：检索到的 chunks + 问题 + 响应必须能放入上下文
3. **语义完整性**：Chunks 应包含有意义的信息
4. **搜索准确性**：过大 = 噪声，过小 = 缺少上下文

```python
# Chunking Strategy in LangChain
from langchain.text_splitter import RecursiveCharacterTextSplitter

# Basic chunking
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,      # Chunk size
    chunk_overlap=200,    # Overlap between chunks
    separators=["\n\n", "\n", ".", " "]
)

# Semantic chunking (meaning-based)
from langchain_experimental.text_splitter import SemanticChunker
from langchain_openai import OpenAIEmbeddings

semantic_splitter = SemanticChunker(
    OpenAIEmbeddings(),
    breakpoint_threshold_type="percentile"
)
```

**推荐 Chunk Size：**
- 通用文档：500-1000 tokens
- 技术文档：1000-2000 tokens
- 代码：函数/class 单元

</details>

### 10. 在 EKS 中对 vLLM 进行 autoscaling 时，最合适的指标是什么？

A. CPU 利用率
B. 内存利用率
C. GPU 利用率或请求队列长度
D. 网络流量

<details>
<summary>查看答案</summary>

**答案：C. GPU 利用率或请求队列长度**

**解释：**
LLM 推理是 GPU 密集型的，因此基于 GPU 利用率或 vLLM 请求队列长度（等待中的请求）进行扩缩容最有效。

```yaml
# vLLM Autoscaling with KEDA
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: vllm-scaledobject
spec:
  scaleTargetRef:
    name: vllm-deployment
  minReplicaCount: 1
  maxReplicaCount: 10
  triggers:
  # Prometheus metric-based
  - type: prometheus
    metadata:
      serverAddress: http://prometheus:9090
      metricName: vllm_num_requests_waiting
      threshold: "10"  # Scale out if 10+ waiting requests
      query: |
        sum(vllm_num_requests_waiting{service="vllm"})

  # GPU utilization-based
  - type: prometheus
    metadata:
      serverAddress: http://prometheus:9090
      metricName: gpu_utilization
      threshold: "80"
      query: |
        avg(DCGM_FI_DEV_GPU_UTIL{kubernetes_pod_name=~"vllm.*"})

---
# HPA Alternative (GPU metrics)
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: vllm-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: vllm-deployment
  minReplicas: 1
  maxReplicas: 10
  metrics:
  - type: External
    external:
      metric:
        name: vllm_requests_waiting
      target:
        type: AverageValue
        averageValue: "5"
```

**关键 vLLM 指标：**
- `vllm_num_requests_running`：当前正在处理的请求
- `vllm_num_requests_waiting`：等待中的请求
- `vllm_gpu_cache_usage_perc`：KV cache 利用率

</details>

## 简答题

### 1. KV Cache 在 vLLM 中的作用是什么？

<details>
<summary>查看答案</summary>

**答案：** 存储先前生成 token 的 Key-Value 张量，以避免生成新 token 时重新计算，从而提升推理速度。

**解释：**
在 Transformer 模型中，生成每个新 token 都需要对所有先前 token 计算 attention。KV Cache 存储已经计算好的 Key-Values，以避免冗余计算。

```
# Without KV Cache
Token1 generation: Compute [Token1]
Token2 generation: Recompute entire [Token1, Token2]
Token3 generation: Recompute entire [Token1, Token2, Token3]
...

# With KV Cache
Token1 generation: Compute [Token1] -> Save to KV Cache
Token2 generation: Cached KV + Compute [Token2] -> Update cache
Token3 generation: Cached KV + Compute [Token3] -> Update cache
```

**vLLM 的 PagedAttention：**
以页面为单位管理 KV Cache，以防止内存碎片化

</details>

### 2. 解释 Langfuse 中 “Trace” 和 “Span” 的关系。

<details>
<summary>查看答案</summary>

**答案：**
- **Trace**：完整的 LLM 工作流（例如从用户问题到最终响应）
- **Span**：Trace 内的单个工作单元（例如 LLM 调用、工具执行、搜索）

Trace 是包含多个 Span 的顶层容器。

```
Trace: "User Question Processing"
+-- Span: "Embedding Generation" (50ms)
+-- Span: "Vector Search" (100ms)
+-- Span: "Context Building" (10ms)
+-- Span: "LLM Call" (2000ms)
    +-- Span: "Token Streaming" (1800ms)
```

```python
# Creating Trace/Span in Langfuse
trace = langfuse.trace(
    name="qa-pipeline",
    user_id="user-123"
)

# Add Span
retrieval_span = trace.span(name="retrieval")
# Retrieval logic...
retrieval_span.end()

llm_span = trace.span(name="llm-generation")
# LLM call...
llm_span.end(output=response)
```

</details>

### 3. RAG 中的 “Hybrid Search” 是什么意思？

<details>
<summary>查看答案</summary>

**答案：** 一种将基于关键词的搜索（BM25 等）与向量相似度搜索（Dense Retrieval）结合起来，以提升搜索质量的方法。

**Hybrid Search 的优势：**
- 关键词搜索：擅长精确术语匹配
- 向量搜索：擅长语义相似性
- 组合：同时利用两者优势

```python
# Hybrid Search Example (Qdrant)
from qdrant_client import QdrantClient
from qdrant_client.models import SparseVector, SearchRequest

client = QdrantClient(host="qdrant", port=6333)

# Execute Hybrid search
results = client.search_batch(
    collection_name="documents",
    requests=[
        # Dense (vector) search
        SearchRequest(
            vector=query_embedding,
            limit=10,
        ),
        # Sparse (keyword) search
        SearchRequest(
            vector=SparseVector(
                indices=bm25_indices,
                values=bm25_values
            ),
            limit=10,
            using="bm25"
        )
    ]
)

# Result fusion (RRF - Reciprocal Rank Fusion)
final_results = reciprocal_rank_fusion(
    results[0], results[1],
    k=60
)
```

</details>

### 4. LangGraph 中 “Checkpoint” 的作用是什么？

<details>
<summary>查看答案</summary>

**答案：** 在图执行过程中保存中间状态，以支持工作流暂停/恢复、time-travel debugging，以及长时间运行的 agent 状态管理。

**Checkpoint 用法：**
```python
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import StateGraph

# Setup Checkpoint storage
memory = SqliteSaver.from_conn_string(":memory:")

# Connect Checkpoint to graph
app = workflow.compile(checkpointer=memory)

# Execute (automatically saves checkpoints)
config = {"configurable": {"thread_id": "user-123"}}
result = app.invoke(input_state, config)

# Restore to specific checkpoint
history = list(app.get_state_history(config))
past_state = history[-2]  # Restore to previous state
```

**Checkpoint 使用场景：**
- 为长时间运行的 agents 保存状态
- 维护每个用户的对话上下文
- 调试：回到特定点并重新执行
- 故障恢复：恢复中断的工作流

</details>

### 5. vLLM 中的 `--tensor-parallel-size` 选项是什么意思？

<details>
<summary>查看答案</summary>

**答案：** 指定 tensor parallelism 级别，用于将模型拆分到多个 GPU 上进行并行推理。当大模型无法加载到单个 GPU 内存中时使用。

**Tensor Parallelism：**
```
# Single GPU (tensor-parallel-size=1)
GPU 0: [All model layers]

# 2-way Tensor Parallelism (tensor-parallel-size=2)
GPU 0: [Half of layers] <-> GPU 1: [Other half of layers]
(Parallel computation on each GPU, then communicate results)

# 4-way Tensor Parallelism (tensor-parallel-size=4)
GPU 0-3: Each handles 1/4 of layers
```

```bash
# vLLM Execution Example
python -m vllm.entrypoints.openai.api_server \
  --model meta-llama/Llama-2-70b-chat-hf \
  --tensor-parallel-size 4 \
  --gpu-memory-utilization 0.9
```

**要求：**
- 建议使用 NVLink 或高速 GPU 互连
- 建议 GPU 数量为 2 的幂（1、2、4、8）
- 所有 GPU 必须为相同类型

</details>

## 动手练习

### 1. 编写 Deployment YAML，在 EKS 上部署 vLLM。
- Model：meta-llama/Llama-2-7b-chat-hf
- GPU：1（nvidia.com/gpu）
- 内存利用率：90%
- 暴露兼容 OpenAI 的 API endpoint

<details>
<summary>查看答案</summary>

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vllm-llama2-7b
  labels:
    app: vllm
    model: llama2-7b
spec:
  replicas: 1
  selector:
    matchLabels:
      app: vllm
      model: llama2-7b
  template:
    metadata:
      labels:
        app: vllm
        model: llama2-7b
    spec:
      containers:
      - name: vllm
        image: vllm/vllm-openai:latest
        args:
          - "--model"
          - "meta-llama/Llama-2-7b-chat-hf"
          - "--host"
          - "0.0.0.0"
          - "--port"
          - "8000"
          - "--tensor-parallel-size"
          - "1"
          - "--gpu-memory-utilization"
          - "0.9"
          - "--max-model-len"
          - "4096"
        ports:
        - containerPort: 8000
          name: http
        resources:
          limits:
            nvidia.com/gpu: 1
            memory: "32Gi"
          requests:
            nvidia.com/gpu: 1
            memory: "24Gi"
            cpu: "4"
        env:
        - name: HUGGING_FACE_HUB_TOKEN
          valueFrom:
            secretKeyRef:
              name: hf-token
              key: token
        volumeMounts:
        - name: model-cache
          mountPath: /root/.cache/huggingface
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 120
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 60
          periodSeconds: 10
      volumes:
      - name: model-cache
        persistentVolumeClaim:
          claimName: vllm-model-cache
      nodeSelector:
        nvidia.com/gpu.product: NVIDIA-A100-SXM4-40GB
      tolerations:
      - key: nvidia.com/gpu
        operator: Exists
        effect: NoSchedule

---
apiVersion: v1
kind: Service
metadata:
  name: vllm-llama2-7b
spec:
  selector:
    app: vllm
    model: llama2-7b
  ports:
  - port: 8000
    targetPort: 8000
    name: http
  type: ClusterIP

---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: vllm-model-cache
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 50Gi
  storageClassName: gp3

---
apiVersion: v1
kind: Secret
metadata:
  name: hf-token
type: Opaque
stringData:
  token: "hf_your_token_here"
```

**测试命令：**
```bash
# Check service
kubectl get pods -l app=vllm
kubectl logs -f deployment/vllm-llama2-7b

# API test
kubectl port-forward svc/vllm-llama2-7b 8000:8000

curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "meta-llama/Llama-2-7b-chat-hf",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

</details>

### 2. 将 Langfuse 部署到 Kubernetes，并编写 Python 代码来跟踪 LLM 调用。

<details>
<summary>查看答案</summary>

```yaml
# Langfuse Kubernetes Deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: langfuse
spec:
  replicas: 1
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
          value: "http://langfuse.default.svc.cluster.local:3000"
        - name: SALT
          valueFrom:
            secretKeyRef:
              name: langfuse-secrets
              key: salt
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"

---
apiVersion: v1
kind: Service
metadata:
  name: langfuse
spec:
  selector:
    app: langfuse
  ports:
  - port: 3000
    targetPort: 3000

---
apiVersion: v1
kind: Secret
metadata:
  name: langfuse-secrets
type: Opaque
stringData:
  database-url: "postgresql://langfuse:password@postgres:5432/langfuse"
  nextauth-secret: "your-nextauth-secret-here"
  salt: "your-salt-here"

---
# PostgreSQL for Langfuse
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
spec:
  serviceName: postgres
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
      - name: postgres
        image: postgres:15
        env:
        - name: POSTGRES_USER
          value: langfuse
        - name: POSTGRES_PASSWORD
          value: password
        - name: POSTGRES_DB
          value: langfuse
        ports:
        - containerPort: 5432
        volumeMounts:
        - name: data
          mountPath: /var/lib/postgresql/data
  volumeClaimTemplates:
  - metadata:
      name: data
    spec:
      accessModes: ["ReadWriteOnce"]
      resources:
        requests:
          storage: 10Gi
```

```python
# Langfuse Integration in Python Application
from langfuse import Langfuse
from langfuse.decorators import observe, langfuse_context
import openai

# Initialize Langfuse client
langfuse = Langfuse(
    public_key="pk-lf-...",
    secret_key="sk-lf-...",
    host="http://langfuse.default.svc.cluster.local:3000"
)

# Automatic tracking with decorators
@observe()
def rag_pipeline(user_query: str) -> str:
    """Track entire RAG pipeline"""

    # Track retrieval step
    context = retrieve_context(user_query)

    # Track LLM call
    response = generate_response(user_query, context)

    return response

@observe()
def retrieve_context(query: str) -> list:
    """Track vector search"""
    langfuse_context.update_current_observation(
        metadata={"retriever": "qdrant", "top_k": 5}
    )

    # Actual search logic
    results = vector_db.search(query, limit=5)

    langfuse_context.update_current_observation(
        output={"num_results": len(results)}
    )
    return results

@observe(as_type="generation")
def generate_response(query: str, context: list) -> str:
    """Track LLM generation"""

    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": f"Context: {context}\n\nQuestion: {query}"}
    ]

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=messages
    )

    # Log token usage
    langfuse_context.update_current_observation(
        usage={
            "input": response.usage.prompt_tokens,
            "output": response.usage.completion_tokens,
            "total": response.usage.total_tokens
        },
        model="gpt-4",
        input=messages,
        output=response.choices[0].message.content
    )

    return response.choices[0].message.content

# Usage example
if __name__ == "__main__":
    result = rag_pipeline("What is Kubernetes?")
    print(result)

    # Flush to Langfuse (wait for async send completion)
    langfuse.flush()
```

</details>

### 3. 使用 LangGraph 实现基于 RAG 的 Q&A agent 工作流图。
- Nodes：retrieve（搜索）、grade（相关性评估）、generate（响应生成）、rewrite（查询重写）
- 如果未找到相关文档，则重写查询并再次搜索

<details>
<summary>查看答案</summary>

```python
from typing import TypedDict, List, Annotated
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import Qdrant
from langchain.prompts import ChatPromptTemplate

# State definition
class RAGState(TypedDict):
    question: str
    documents: List[str]
    generation: str
    relevance_score: float
    retry_count: int

# Initialize LLM and retriever
llm = ChatOpenAI(model="gpt-4", temperature=0)
embeddings = OpenAIEmbeddings()
vectorstore = Qdrant(
    client=qdrant_client,
    collection_name="docs",
    embeddings=embeddings
)
retriever = vectorstore.as_retriever(search_kwargs={"k": 5})

# Node function definitions
def retrieve(state: RAGState) -> RAGState:
    """Document retrieval"""
    print(f"Retrieving documents for: {state['question']}")

    docs = retriever.get_relevant_documents(state["question"])
    return {
        **state,
        "documents": [doc.page_content for doc in docs]
    }

def grade_documents(state: RAGState) -> RAGState:
    """Evaluate document relevance"""
    print("Grading document relevance...")

    grading_prompt = ChatPromptTemplate.from_template("""
    You are a grader assessing relevance of a retrieved document to a user question.

    Document: {document}
    Question: {question}

    Give a relevance score from 0 to 1. Return only the number.
    """)

    scores = []
    for doc in state["documents"]:
        response = llm.invoke(
            grading_prompt.format(document=doc, question=state["question"])
        )
        scores.append(float(response.content.strip()))

    avg_score = sum(scores) / len(scores) if scores else 0

    return {
        **state,
        "relevance_score": avg_score
    }

def generate(state: RAGState) -> RAGState:
    """Generate response"""
    print("Generating response...")

    generation_prompt = ChatPromptTemplate.from_template("""
    Answer the question based only on the following context:

    Context: {context}

    Question: {question}

    Answer:
    """)

    context = "\n\n".join(state["documents"])
    response = llm.invoke(
        generation_prompt.format(context=context, question=state["question"])
    )

    return {
        **state,
        "generation": response.content
    }

def rewrite_query(state: RAGState) -> RAGState:
    """Rewrite query"""
    print("Rewriting query...")

    rewrite_prompt = ChatPromptTemplate.from_template("""
    The original question didn't retrieve relevant documents.
    Rewrite the question to be more specific and searchable.

    Original question: {question}

    Rewritten question:
    """)

    response = llm.invoke(
        rewrite_prompt.format(question=state["question"])
    )

    return {
        **state,
        "question": response.content.strip(),
        "retry_count": state.get("retry_count", 0) + 1
    }

# Routing function
def should_continue(state: RAGState) -> str:
    """Routing decision based on relevance"""

    # Check max retry count
    if state.get("retry_count", 0) >= 2:
        print("Max retries reached, generating with available docs")
        return "generate"

    # Check relevance score
    if state["relevance_score"] >= 0.7:
        print("Documents are relevant, proceeding to generate")
        return "generate"
    else:
        print("Documents not relevant enough, rewriting query")
        return "rewrite"

# Build graph
workflow = StateGraph(RAGState)

# Add nodes
workflow.add_node("retrieve", retrieve)
workflow.add_node("grade", grade_documents)
workflow.add_node("generate", generate)
workflow.add_node("rewrite", rewrite_query)

# Add edges
workflow.set_entry_point("retrieve")
workflow.add_edge("retrieve", "grade")
workflow.add_conditional_edges(
    "grade",
    should_continue,
    {
        "generate": "generate",
        "rewrite": "rewrite"
    }
)
workflow.add_edge("rewrite", "retrieve")  # Search again after rewrite
workflow.add_edge("generate", END)

# Compile
app = workflow.compile()

# Execution example
if __name__ == "__main__":
    initial_state = {
        "question": "How does Kubernetes handle pod scheduling?",
        "documents": [],
        "generation": "",
        "relevance_score": 0.0,
        "retry_count": 0
    }

    result = app.invoke(initial_state)
    print(f"\nFinal Answer:\n{result['generation']}")
```

**图可视化：**
```
+-------------+
|   START     |
+------+------+
       |
       v
+-------------+
|  retrieve   |<--------------+
+------+------+               |
       |                      |
       v                      |
+-------------+               |
|    grade    |               |
+------+------+               |
       |                      |
       v                      |
   +-------+                  |
   | score |                  |
   | >=0.7?|                  |
   +---+---+                  |
      /|\                     |
     / | \                    |
    /  |  \                   |
   v   |   v                  |
 Yes   |   No                 |
   |   |   |                  |
   v   |   v                  |
+------+-------+     +--------+----+
|   generate   |     |   rewrite   |
+------+-------+     +-------------+
       |
       v
+-------------+
|    END      |
+-------------+
```

</details>

## 高级问题

### 1. 一家金融公司希望构建一个实时客户咨询 AI agent。请设计一个集成 vLLM、RAG、LangGraph 和 Langfuse 的生产级架构。包含高可用、响应质量监控和成本优化策略。

<details>
<summary>查看答案</summary>

**金融客户咨询 AI Agent 架构**

**1. 整体架构：**

```
+-------------------------------------------------------------+
|                        EKS Cluster                           |
|  +-----------------------------------------------------+   |
|  |                 Inference Gateway (Istio)            |   |
|  |  +-------------+  +-------------+  +-------------+  |   |
|  |  | Rate Limit  |  |   A/B Test  |  |   Auth      |  |   |
|  |  +-------------+  +-------------+  +-------------+  |   |
|  +---------------------------+--------------------------+   |
|                             |                               |
|  +--------------------------v---------------------------+   |
|  |                   LangGraph Agent                    |   |
|  |  +------+  +------+  +------+  +------+  +------+  |   |
|  |  |Intent|->| RAG  |->|Check |->|Action|->|Reply |  |   |
|  |  +------+  +------+  +------+  +------+  +------+  |   |
|  +-----------------------------------------------------+   |
|                             |                               |
|  +--------------------------v---------------------------+   |
|  |                  Backend Services                    |   |
|  |  +----------+  +----------+  +----------+          |   |
|  |  |  vLLM    |  |  Qdrant  |  | Langfuse |          |   |
|  |  | (HA x3) |  |  (HA x3) |  |          |          |   |
|  |  +----------+  +----------+  +----------+          |   |
|  +-----------------------------------------------------+   |
+-------------------------------------------------------------+
```

**2. 高可用 vLLM Deployment：**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vllm-finance-agent
spec:
  replicas: 3
  selector:
    matchLabels:
      app: vllm-finance
  template:
    metadata:
      labels:
        app: vllm-finance
    spec:
      topologySpreadConstraints:
      - maxSkew: 1
        topologyKey: topology.kubernetes.io/zone
        whenUnsatisfiable: DoNotSchedule
        labelSelector:
          matchLabels:
            app: vllm-finance
      containers:
      - name: vllm
        image: vllm/vllm-openai:latest
        args:
          - "--model"
          - "meta-llama/Llama-2-70b-chat-hf"
          - "--tensor-parallel-size"
          - "2"
          - "--gpu-memory-utilization"
          - "0.85"
          - "--max-num-batched-tokens"
          - "8192"
        resources:
          limits:
            nvidia.com/gpu: 2
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 120
          periodSeconds: 10
          failureThreshold: 3

---
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: vllm-pdb
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: vllm-finance
```

**3. LangGraph Agent 工作流：**

```python
from typing import TypedDict, Literal
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver

class FinanceAgentState(TypedDict):
    user_id: str
    session_id: str
    message: str
    intent: str
    context: list
    response: str
    actions_taken: list
    requires_human: bool

# Intent Classification
def classify_intent(state: FinanceAgentState) -> FinanceAgentState:
    """Classify customer inquiry intent"""
    intents = ["balance_inquiry", "transaction_history",
               "card_issue", "loan_inquiry", "complaint", "general"]

    # Intent classification via LLM
    intent = llm_classify(state["message"], intents)

    # Langfuse tracking
    langfuse.span(name="intent_classification", output={"intent": intent})

    return {**state, "intent": intent}

# RAG-based Context Retrieval
def retrieve_context(state: FinanceAgentState) -> FinanceAgentState:
    """Search financial product/policy documents"""

    # Intent-specific search
    collection = intent_to_collection.get(state["intent"], "general")

    docs = qdrant_client.search(
        collection_name=collection,
        query_vector=embed(state["message"]),
        limit=5
    )

    # Always include compliance documents
    compliance_docs = get_compliance_docs(state["intent"])

    return {**state, "context": docs + compliance_docs}

# Compliance Check
def compliance_check(state: FinanceAgentState) -> FinanceAgentState:
    """Check regulatory compliance"""

    # Detect sensitive information
    if contains_sensitive_info(state["message"]):
        state["requires_human"] = True

    # Detect high-risk actions
    if state["intent"] in ["loan_inquiry", "card_issue"]:
        state["requires_human"] = needs_human_approval(state)

    return state

# Build graph
workflow = StateGraph(FinanceAgentState)
workflow.add_node("classify", classify_intent)
workflow.add_node("retrieve", retrieve_context)
workflow.add_node("compliance", compliance_check)
workflow.add_node("execute_action", execute_action)
workflow.add_node("generate", generate_response)
workflow.add_node("human_handoff", escalate_to_human)

workflow.set_entry_point("classify")
workflow.add_edge("classify", "retrieve")
workflow.add_edge("retrieve", "compliance")
workflow.add_conditional_edges(
    "compliance",
    route_by_compliance,
    {"execute_action": "execute_action", "human_handoff": "human_handoff"}
)
workflow.add_edge("execute_action", "generate")
workflow.add_edge("generate", END)
workflow.add_edge("human_handoff", END)

# Checkpoint (maintain conversation context)
memory = SqliteSaver.from_conn_string("postgresql://...")
app = workflow.compile(checkpointer=memory)
```

**4. 响应质量监控（Langfuse）：**

```yaml
# Langfuse Quality Evaluation Job
apiVersion: batch/v1
kind: CronJob
metadata:
  name: langfuse-evaluation
spec:
  schedule: "0 * * * *"  # Every hour
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: evaluator
            image: finance-ai/evaluator:latest
            command:
            - python
            - -c
            - |
              from langfuse import Langfuse

              langfuse = Langfuse()

              # Get traces from last hour
              traces = langfuse.get_traces(
                  filter={"start_time": {"gte": "1h"}}
              )

              # Quality evaluation
              for trace in traces:
                  score = evaluate_response(trace)
                  langfuse.score(
                      trace_id=trace.id,
                      name="quality_score",
                      value=score
                  )

              # Alert for low quality responses
              low_quality = [t for t in traces if t.scores.get("quality_score", 1) < 0.7]
              if low_quality:
                  send_alert(f"Low quality responses: {len(low_quality)}")
```

**5. 成本优化：**

```yaml
# KEDA-based Scaling
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: vllm-scaler
spec:
  scaleTargetRef:
    name: vllm-finance-agent
  minReplicaCount: 2   # Maintain minimum HA
  maxReplicaCount: 10
  triggers:
  - type: prometheus
    metadata:
      metricName: vllm_request_queue_size
      threshold: "20"
      query: |
        sum(vllm_num_requests_waiting{service="vllm-finance"})

  # Scale down outside business hours
  - type: cron
    metadata:
      timezone: America/Los_Angeles
      start: "0 22 * * *"  # 22:00
      end: "0 8 * * *"     # 08:00
      desiredReplicas: "2"
```

**预期成本节省：**
- Spot instances：相比按需实例节省 60-70%
- 基于时间的扩缩容：非营业时间节省 50%
- 模型量化：在相同性能下节省 50% GPU
- 缓存层：对重复查询节省 30%

</details>

### 2. 一家 AI 初创公司希望在 EKS 上构建多模型推理平台，用于管理各种 LLM 模型（GPT-4、Claude、Llama、Mistral）。请设计一个包含 Inference Gateway、模型路由、A/B 测试和成本优化策略的平台。

<details>
<summary>查看答案</summary>

**多模型推理平台设计**

**1. 架构概览：**

```
                    +-------------------------------+
                    |     Inference Gateway (Kong)  |
                    |  +-------+ +-------+ +------+ |
                    |  |Rate   | |A/B    | |Cost  | |
                    |  |Limit  | |Router | |Track | |
                    |  +-------+ +-------+ +------+ |
                    +---------------+---------------+
                                   |
           +-----------------------+------------------------+
           |                       |                        |
           v                       v                        v
    +--------------+      +--------------+      +--------------+
    | OpenAI Proxy |      | Anthropic    |      |    vLLM      |
    |   (GPT-4)    |      |  (Claude)    |      | (Llama/Mist) |
    +--------------+      +--------------+      +--------------+
           |                       |                       |
           +-----------------------+-----------------------+
                                   |
                           +-------v-------+
                           |   Langfuse    |
                           |  Observability|
                           +---------------+
```

**2. Inference Gateway 配置（Kong）：**

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: kong-config
data:
  kong.yml: |
    _format_version: "3.0"

    services:
    # OpenAI GPT-4
    - name: openai-gpt4
      url: https://api.openai.com
      routes:
      - name: gpt4-route
        paths:
        - /v1/gpt4
      plugins:
      - name: rate-limiting
        config:
          minute: 100
          policy: redis

    # Anthropic Claude
    - name: anthropic-claude
      url: https://api.anthropic.com
      routes:
      - name: claude-route
        paths:
        - /v1/claude

    # Self-hosted vLLM (Llama/Mistral)
    - name: vllm-llama
      url: http://vllm-llama:8000
      routes:
      - name: llama-route
        paths:
        - /v1/llama

    # Unified endpoint (smart routing)
    - name: unified-inference
      url: http://model-router:8080
      routes:
      - name: unified-route
        paths:
        - /v1/chat/completions
```

**3. 智能模型 Router：**

```python
# model_router.py
from fastapi import FastAPI, Request
import httpx

app = FastAPI()

MODEL_CONFIG = {
    "gpt-4": {
        "endpoint": "https://api.openai.com/v1/chat/completions",
        "cost_per_1k_input": 0.03,
        "cost_per_1k_output": 0.06,
        "latency_p99": 2000,
        "capabilities": ["reasoning", "coding", "creative"]
    },
    "claude-3-opus": {
        "endpoint": "https://api.anthropic.com/v1/messages",
        "cost_per_1k_input": 0.015,
        "cost_per_1k_output": 0.075,
        "latency_p99": 3000,
        "capabilities": ["reasoning", "analysis", "safety"]
    },
    "llama-70b": {
        "endpoint": "http://vllm-llama:8000/v1/chat/completions",
        "cost_per_1k_input": 0.001,
        "cost_per_1k_output": 0.002,
        "latency_p99": 1500,
        "capabilities": ["general", "multilingual"]
    },
    "mistral-7b": {
        "endpoint": "http://vllm-mistral:8000/v1/chat/completions",
        "cost_per_1k_input": 0.0005,
        "cost_per_1k_output": 0.001,
        "latency_p99": 500,
        "capabilities": ["general", "fast"]
    }
}

class RoutingStrategy:
    @staticmethod
    def cost_optimized(task_type: str, max_latency: int = 5000) -> str:
        """Cost-optimized routing"""
        candidates = [
            model for model, config in MODEL_CONFIG.items()
            if config["latency_p99"] <= max_latency
        ]
        return min(candidates, key=lambda m: MODEL_CONFIG[m]["cost_per_1k_input"])

    @staticmethod
    def quality_optimized(task_type: str) -> str:
        """Quality-optimized routing"""
        if task_type in ["reasoning", "coding"]:
            return "gpt-4"
        elif task_type in ["analysis", "safety"]:
            return "claude-3-opus"
        return "llama-70b"

    @staticmethod
    def latency_optimized(max_latency: int = 1000) -> str:
        """Latency-optimized routing"""
        candidates = [
            model for model, config in MODEL_CONFIG.items()
            if config["latency_p99"] <= max_latency
        ]
        return candidates[0] if candidates else "mistral-7b"

@app.post("/v1/chat/completions")
async def route_completion(request: Request):
    body = await request.json()

    # Extract routing hints
    routing_hint = request.headers.get("X-Routing-Strategy", "balanced")
    task_type = request.headers.get("X-Task-Type", "general")
    max_latency = int(request.headers.get("X-Max-Latency", "5000"))

    # Select model
    if routing_hint == "cost":
        model = RoutingStrategy.cost_optimized(task_type, max_latency)
    elif routing_hint == "quality":
        model = RoutingStrategy.quality_optimized(task_type)
    elif routing_hint == "latency":
        model = RoutingStrategy.latency_optimized(max_latency)
    else:
        model = "llama-70b"  # Balanced default

    # Forward request to selected model
    config = MODEL_CONFIG[model]

    async with httpx.AsyncClient() as client:
        response = await client.post(
            config["endpoint"],
            json=body,
            headers={"Authorization": f"Bearer {get_api_key(model)}"}
        )

    # Track cost
    track_cost(model, body, response.json())

    return response.json()
```

**4. A/B 测试配置：**

```yaml
# A/B Testing with Istio VirtualService
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: model-ab-test
spec:
  hosts:
  - inference.internal
  http:
  # A/B Test: GPT-4 vs Claude for reasoning tasks
  - match:
    - headers:
        x-task-type:
          exact: "reasoning"
    route:
    - destination:
        host: openai-proxy
        subset: gpt4
      weight: 50
      headers:
        response:
          add:
            x-model-variant: "gpt4-control"
    - destination:
        host: anthropic-proxy
        subset: claude
      weight: 50
      headers:
        response:
          add:
            x-model-variant: "claude-treatment"

  # A/B Test: Llama vs Mistral for general tasks
  - match:
    - headers:
        x-task-type:
          exact: "general"
    route:
    - destination:
        host: vllm-llama
      weight: 70
    - destination:
        host: vllm-mistral
      weight: 30
```

**5. 成本优化策略：**

```python
class CostOptimizer:
    def __init__(self):
        self.model_costs = {
            "gpt-4": ModelCost(0.03, 0.06),
            "gpt-3.5-turbo": ModelCost(0.0015, 0.002),
            "claude-3-opus": ModelCost(0.015, 0.075),
            "claude-3-sonnet": ModelCost(0.003, 0.015),
            "llama-70b": ModelCost(0.001, 0.002, fixed_cost=2.5),
            "mistral-7b": ModelCost(0.0005, 0.001, fixed_cost=0.5),
        }

        self.quality_scores = {
            "gpt-4": 9.5,
            "gpt-3.5-turbo": 7.5,
            "claude-3-opus": 9.0,
            "claude-3-sonnet": 8.0,
            "llama-70b": 8.5,
            "mistral-7b": 7.0,
        }

    def select_model(
        self,
        task_complexity: str,
        budget_per_request: float,
        min_quality: float = 7.0
    ) -> str:
        """Select optimal model within budget"""

        token_estimates = {
            "simple": (500, 200),
            "medium": (1000, 500),
            "complex": (2000, 1000)
        }

        input_tokens, output_tokens = token_estimates[task_complexity]

        candidates = []
        for model, cost in self.model_costs.items():
            estimated_cost = self.estimate_cost(model, input_tokens, output_tokens)
            quality = self.quality_scores[model]

            if estimated_cost <= budget_per_request and quality >= min_quality:
                candidates.append((model, estimated_cost, quality))

        # Select model with best quality/cost ratio
        if not candidates:
            return "mistral-7b"  # Fallback to cheapest

        return max(candidates, key=lambda x: x[2] / x[1])[0]

    def cascade_strategy(self, prompt: str) -> Dict:
        """Cascade: Try low-cost model first, fallback to high-cost on failure"""
        return {
            "primary": "mistral-7b",
            "fallback_chain": ["llama-70b", "gpt-3.5-turbo", "gpt-4"],
            "confidence_threshold": 0.8
        }
```

**预期成本优化结果：**
- 智能路由：节省 30-50% 成本
- Cascade 策略：在保持质量的同时额外节省 20%
- 自托管模型：节省 80% API 成本
- A/B 测试：发现最优模型组合

</details>
