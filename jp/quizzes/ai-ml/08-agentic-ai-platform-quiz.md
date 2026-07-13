# EKS 上の Agentic AI Platform クイズ

このクイズでは、Amazon EKS 上で Agentic AI platform を構築するための理解を確認します。対象には、GPU 管理 (MIG/Time-Slicing)、vLLM inference server、Inference Gateway、RAG (Retrieval-Augmented Generation)、Kagent、LangGraph、Langfuse observability が含まれます。

## クイズ概要
- GPU Resource Management (MIG, Time-Slicing)
- vLLM Inference Server Deployment と Optimization
- Kubernetes Gateway API と Inference Gateway
- RAG Architecture と Implementation
- Kagent (Kubernetes AI Agent)
- LangGraph Workflow Orchestration
- Langfuse による LLM Observability

## 選択問題

### 1. vLLM の PagedAttention technology は主にどの問題を解決しますか？

A. より高速な model training
B. GPU memory fragmentation による非効率な memory usage
C. network latency の低減
D. model parameter compression

<details>
<summary>答えを表示</summary>

**答え: B. GPU memory fragmentation による非効率な memory usage**

**解説:**
vLLM の PagedAttention は、KV (Key-Value) cache を page 単位で管理し、GPU memory fragmentation の問題を解決します。これにより、同じ GPU memory で 2-4 倍多くの request を同時に処理できます。

**PagedAttention の仕組み:**
- KV cache を固定サイズの blocks (pages) に分割する
- 連続していない memory space の使用を可能にする
- dynamic memory allocation/deallocation により fragmentation を防ぐ

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

**PagedAttention のメリット:**
- memory efficiency が 2-4 倍向上
- throughput が 2-4 倍増加
- より長い context length のサポート

</details>

### 2. Inference Gateway の主要な役割ではないものはどれですか？

A. 複数の LLM backend への traffic routing
B. request rate limiting
C. model training jobs の管理
D. load balancing と failover

<details>
<summary>答えを表示</summary>

**答え: C. model training jobs の管理**

**解説:**
Inference Gateway は、inference request の routing、load balancing、rate limiting を処理します。Model training は別の systems (例: Kubeflow、Ray) によって管理されます。

**Inference Gateway の主な機能:**
- multi-model backend routing
- request rate limiting と quota management
- A/B testing と canary deployments
- authentication/authorization handling
- metrics collection と monitoring

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

### 3. RAG (Retrieval-Augmented Generation) architecture における Vector Database の役割は何ですか？

A. LLM model weights を保存する
B. document embedding vectors を保存し similarity search を行う
C. user authentication information を管理する
D. API request logging

<details>
<summary>答えを表示</summary>

**答え: B. document embedding vectors を保存し similarity search を行う**

**解説:**
Vector Database は、embedding models を使って documents から変換された vectors を保存し、query vectors に類似した documents を高速に検索します。これにより、LLM は関連する context を参照して、より正確な response を生成できます。

**RAG Pipeline:**
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

**代表的な Vector Databases:**
- Qdrant, Milvus, Pinecone
- PostgreSQL + pgvector
- Elasticsearch (Dense Vector)

</details>

### 4. LangGraph の重要な特徴は何ですか？

A. simple linear chains のみをサポートする
B. cycle support を備えた state-based graph workflows
C. 単一の LLM しか使用できない
D. memory support がない

<details>
<summary>答えを表示</summary>

**答え: B. cycle support を備えた state-based graph workflows**

**解説:**
LangGraph は LangChain をベースにした graph workflow framework で、複雑な AI agent logic を state-based graph として実装できます。反復的な decision-making loop を実装するための cycles をサポートします。

**LangGraph の主要概念:**
- **StateGraph**: state を管理する graph structure
- **Node**: 個別の processing steps (LLM calls、tool execution など)
- **Edge**: nodes 間の transition conditions
- **Cycle**: conditional loops (例: self-reflection loops)

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

### 5. Langfuse が追跡する metric ではないものはどれですか？

A. Token usage
B. Response latency
C. GPU temperature
D. LLM call cost

<details>
<summary>答えを表示</summary>

**答え: C. GPU temperature**

**解説:**
Langfuse は LLM applications 向けの observability tool で、token usage、latency、cost など LLM-specific metrics を追跡します。GPU temperature は DCGM や Prometheus によって収集される infrastructure-level metric です。

**Langfuse の主な機能:**
- Trace-based LLM call tracking
- token usage と cost analysis
- prompt version management
- user feedback collection
- quality evaluation

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

### 6. Kagent の主な目的は何ですか？

A. Kubernetes cluster monitoring
B. AI agents が automated cluster management のために Kubernetes API と対話できるようにすること
C. container image building
D. network policy management

<details>
<summary>答えを表示</summary>

**答え: B. AI agents が automated cluster management のために Kubernetes API と対話できるようにすること**

**解説:**
Kagent は、AI agents が Kubernetes clusters を理解して管理できるようにする framework です。natural language commands を Kubernetes API calls に変換し、cluster state を分析して automated operations を可能にします。

**Kagent の機能:**
- natural language-based cluster management
- automatic kubectl command generation と execution
- troubleshooting automation
- resource optimization recommendations

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

### 7. GPU Time-Slicing を MIG と一緒に使用する利点は何ですか？

A. 単純に GPUs の数を 2 倍にする
B. MIG partitions 内で追加の Time-Slicing を行い、より細かく resource を分割できる
C. memory capacity の automatic expansion
D. network bandwidth の増加

<details>
<summary>答えを表示</summary>

**答え: B. MIG partitions 内で追加の Time-Slicing を行い、より細かく resource を分割できる**

**解説:**
MIG で物理的に分離された GPU instances を作成した後、各 MIG instance 内で Time-Slicing を適用すると、より多くの workloads を収容できます。

**MIG + Time-Slicing の組み合わせ:**
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

**メリット:**
- MIG の memory isolation + Time-Slicing の flexibility
- より多くの small inference workloads を収容
- QoS guarantee と utilization improvement の balance

</details>

### 8. vLLM の Continuous Batching はどのような benefit を提供しますか？

A. fixed batch size
B. 新しい request を existing batches に動的に追加して GPU utilization を向上させる
C. single request processing のみ
D. CPU 上でのみ実行される

<details>
<summary>答えを表示</summary>

**答え: B. 新しい request を existing batches に動的に追加して GPU utilization を向上させる**

**解説:**
Continuous Batching は static batching と異なり、新しい requests を進行中の batches に動的に追加し、完了した requests を即座に削除します。これにより GPU utilization を最大化します。

**Static Batching と Continuous Batching:**
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

**メリット:**
- GPU idle time を最小化
- average response time を短縮
- throughput が 2-4 倍向上

</details>

### 9. RAG systems で Chunk Size を決定する際に考慮すべき factor ではないものはどれですか？

A. embedding model の maximum tokens
B. LLM context window size
C. GPU temperature threshold
D. documents の semantic units (paragraphs, sections)

<details>
<summary>答えを表示</summary>

**答え: C. GPU temperature threshold**

**解説:**
Chunk Size は documents を分割する size であり、embedding model の token limits、LLM context size、documents の semantic structure を考慮する必要があります。GPU temperature は infrastructure 関連であり、Chunk Size とは無関係です。

**Chunk Size の要因:**
1. **Embedding model limits**: 通常 512-8192 tokens
2. **LLM context**: retrieved chunks + question + response が context に収まる必要がある
3. **Semantic completeness**: chunks は意味のある information を含むべき
4. **Search accuracy**: 大きすぎる = noise、小さすぎる = context 不足

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

**推奨される Chunk Sizes:**
- 一般 documents: 500-1000 tokens
- technical documents: 1000-2000 tokens
- Code: Function/class units

</details>

### 10. EKS で vLLM を autoscaling するために最も適切な metric は何ですか？

A. CPU utilization
B. Memory utilization
C. GPU utilization または request queue length
D. Network traffic

<details>
<summary>答えを表示</summary>

**答え: C. GPU utilization または request queue length**

**解説:**
LLM inference は GPU-intensive であるため、GPU utilization または vLLM の request queue length (pending requests) に基づく scaling が最も効果的です。

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

**主な vLLM Metrics:**
- `vllm_num_requests_running`: 現在処理中の requests
- `vllm_num_requests_waiting`: 待機中の requests
- `vllm_gpu_cache_usage_perc`: KV cache utilization

</details>

## 短答問題

### 1. vLLM における KV Cache の役割は何ですか？

<details>
<summary>答えを表示</summary>

**答え:** 以前に生成された tokens の Key-Value tensors を保存し、新しい tokens を生成するときの recomputation を避けて inference speed を向上させます。

**解説:**
Transformer models では、新しい token を生成するたびに、すべての previous tokens に対する attention を計算する必要があります。KV Cache は、すでに計算済みの Key-Values を保存して redundant computation を防ぎます。

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

**vLLM の PagedAttention:**
KV Cache を page 単位で管理し、memory fragmentation を防ぎます

</details>

### 2. Langfuse における「Trace」と「Span」の関係を説明してください。

<details>
<summary>答えを表示</summary>

**答え:**
- **Trace**: 完全な LLM workflow (例: user question から final response まで)
- **Span**: Trace 内の個別の work unit (例: LLM call、tool execution、search)

Trace は複数の Spans を含む top-level container です。

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

### 3. RAG における「Hybrid Search」とは何ですか？

<details>
<summary>答えを表示</summary>

**答え:** keyword-based search (BM25 など) と vector similarity search (Dense Retrieval) を組み合わせ、search quality を向上させる方法です。

**Hybrid Search のメリット:**
- Keyword search: exact term matching に強い
- Vector search: semantic similarity に強い
- Combined: 両方の利点を活用できる

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

### 4. LangGraph における「Checkpoint」の役割は何ですか？

<details>
<summary>答えを表示</summary>

**答え:** graph execution 中の intermediate state を保存し、workflow の pause/resume、time-travel debugging、long-running agent の state management を可能にします。

**Checkpoint の使用:**
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

**Checkpoint のユースケース:**
- long-running agents の state を保存
- user ごとの conversation context を維持
- Debugging: 特定の point に戻って re-execute する
- Failure recovery: interrupted workflows を再開する

</details>

### 5. vLLM の `--tensor-parallel-size` option は何を意味しますか？

<details>
<summary>答えを表示</summary>

**答え:** model を複数 GPUs に分割して parallel inference するための tensor parallelism level を指定します。large models が単一 GPU の memory に loading できない場合に使用します。

**Tensor Parallelism:**
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

**要件:**
- NVLink または high-speed GPU interconnect を推奨
- 2 のべき乗の GPU count を推奨 (1, 2, 4, 8)
- すべての GPUs が同じ type である必要がある

</details>

## ハンズオン演習

### 1. EKS 上に vLLM を deploy する Deployment YAML を書いてください。
- Model: meta-llama/Llama-2-7b-chat-hf
- GPU: 1 (nvidia.com/gpu)
- Memory utilization: 90%
- OpenAI-compatible API endpoint を公開

<details>
<summary>答えを表示</summary>

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

**テストコマンド:**
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

### 2. Kubernetes に Langfuse を deploy し、LLM calls を追跡する Python code を書いてください。

<details>
<summary>答えを表示</summary>

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

### 3. LangGraph を使用して RAG-based Q&A agent workflow graph を実装してください。
- Nodes: retrieve (search), grade (relevance evaluation), generate (response generation), rewrite (query rewriting)
- relevant documents が見つからない場合は、query を rewrite して再度 search する

<details>
<summary>答えを表示</summary>

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

**Graph Visualization:**
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

## 発展問題

### 1. ある金融会社が real-time customer consultation AI agent を構築したいと考えています。vLLM、RAG、LangGraph、Langfuse を統合する production-level architecture を設計してください。high availability、response quality monitoring、cost optimization strategies を含めてください。

<details>
<summary>答えを表示</summary>

**金融 Customer Consultation AI Agent Architecture**

**1. 全体 Architecture:**

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

**2. High-Availability vLLM Deployment:**

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

**3. LangGraph Agent Workflow:**

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

**4. Response Quality Monitoring (Langfuse):**

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

**5. Cost Optimization:**

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

**想定される Cost Savings:**
- Spot instances: on-demand と比較して 60-70% の savings
- time-based scaling: off-hours 中に 50% の savings
- model quantization: 同じ performance で 50% の GPU savings
- caching layer: repeat queries で 30% の savings

</details>

### 2. ある AI startup が、さまざまな LLM models (GPT-4、Claude、Llama、Mistral) を管理する multi-model inference platform を EKS 上に構築したいと考えています。Inference Gateway、model routing、A/B testing、cost optimization strategies を含む platform を設計してください。

<details>
<summary>答えを表示</summary>

**Multi-Model Inference Platform Design**

**1. Architecture Overview:**

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

**2. Inference Gateway Configuration (Kong):**

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

**3. Smart Model Router:**

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

**4. A/B Testing Configuration:**

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

**5. Cost Optimization Strategy:**

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

**想定される Cost Optimization Results:**
- Smart routing: 30-50% の cost savings
- Cascade strategy: quality を維持しながら追加で 20% の savings
- Self-hosted models: API costs を 80% 削減
- A/B testing: optimal model combinations を発見

</details>
