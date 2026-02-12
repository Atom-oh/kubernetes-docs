# Agentic AI Platform on EKS Quiz

This quiz tests your understanding of building Agentic AI platforms on Amazon EKS, including GPU management (MIG/Time-Slicing), vLLM inference server, Inference Gateway, RAG (Retrieval-Augmented Generation), Kagent, LangGraph, and Langfuse observability.

## Quiz Overview
- GPU Resource Management (MIG, Time-Slicing)
- vLLM Inference Server Deployment and Optimization
- Kubernetes Gateway API and Inference Gateway
- RAG Architecture and Implementation
- Kagent (Kubernetes AI Agent)
- LangGraph Workflow Orchestration
- LLM Observability with Langfuse

## Multiple Choice Questions

### 1. What main problem does vLLM's PagedAttention technology solve?

A. Faster model training
B. Inefficient memory usage due to GPU memory fragmentation
C. Reduced network latency
D. Model parameter compression

<details>
<summary>View Answer</summary>

**Answer: B. Inefficient memory usage due to GPU memory fragmentation**

**Explanation:**
vLLM's PagedAttention manages KV (Key-Value) cache in page units to solve GPU memory fragmentation issues. This allows 2-4x more requests to be processed concurrently with the same GPU memory.

**How PagedAttention Works:**
- Splits KV cache into fixed-size blocks (pages)
- Enables use of non-contiguous memory space
- Prevents fragmentation through dynamic memory allocation/deallocation

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

**PagedAttention Benefits:**
- 2-4x memory efficiency improvement
- 2-4x throughput increase
- Support for longer context lengths

</details>

### 2. Which is NOT a primary role of an Inference Gateway?

A. Traffic routing to multiple LLM backends
B. Request rate limiting
C. Managing model training jobs
D. Load balancing and failover

<details>
<summary>View Answer</summary>

**Answer: C. Managing model training jobs**

**Explanation:**
Inference Gateway handles routing, load balancing, and rate limiting for inference requests. Model training is managed by separate systems (e.g., Kubeflow, Ray).

**Core Inference Gateway Features:**
- Multi-model backend routing
- Request rate limiting and quota management
- A/B testing and canary deployments
- Authentication/authorization handling
- Metrics collection and monitoring

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

### 3. What is the role of a Vector Database in RAG (Retrieval-Augmented Generation) architecture?

A. Storing LLM model weights
B. Storing document embedding vectors and similarity search
C. Managing user authentication information
D. API request logging

<details>
<summary>View Answer</summary>

**Answer: B. Storing document embedding vectors and similarity search**

**Explanation:**
Vector Database stores vectors converted from documents using embedding models and quickly searches for documents similar to query vectors. This enables LLMs to reference relevant context and generate more accurate responses.

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

**Popular Vector Databases:**
- Qdrant, Milvus, Pinecone
- PostgreSQL + pgvector
- Elasticsearch (Dense Vector)

</details>

### 4. What is the key feature of LangGraph?

A. Only supports simple linear chains
B. State-based graph workflows with cycle support
C. Can only use a single LLM
D. No memory support

<details>
<summary>View Answer</summary>

**Answer: B. State-based graph workflows with cycle support**

**Explanation:**
LangGraph is a graph workflow framework based on LangChain that allows implementing complex AI agent logic as state-based graphs. It supports cycles for implementing iterative decision-making loops.

**Core LangGraph Concepts:**
- **StateGraph**: Graph structure that manages state
- **Node**: Individual processing steps (LLM calls, tool execution, etc.)
- **Edge**: Transition conditions between nodes
- **Cycle**: Conditional loops (e.g., self-reflection loops)

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

### 5. Which is NOT a metric tracked by Langfuse?

A. Token usage
B. Response latency
C. GPU temperature
D. LLM call cost

<details>
<summary>View Answer</summary>

**Answer: C. GPU temperature**

**Explanation:**
Langfuse is an observability tool for LLM applications that tracks LLM-specific metrics like token usage, latency, and cost. GPU temperature is an infrastructure-level metric collected by DCGM or Prometheus.

**Main Langfuse Features:**
- Trace-based LLM call tracking
- Token usage and cost analysis
- Prompt version management
- User feedback collection
- Quality evaluation

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

### 6. What is the primary purpose of Kagent?

A. Kubernetes cluster monitoring
B. Enabling AI agents to interact with Kubernetes API for automated cluster management
C. Container image building
D. Network policy management

<details>
<summary>View Answer</summary>

**Answer: B. Enabling AI agents to interact with Kubernetes API for automated cluster management**

**Explanation:**
Kagent is a framework that allows AI agents to understand and manage Kubernetes clusters. It converts natural language commands to Kubernetes API calls and enables automated operations by analyzing cluster state.

**Kagent Features:**
- Natural language-based cluster management
- Automatic kubectl command generation and execution
- Troubleshooting automation
- Resource optimization recommendations

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

### 7. What is the benefit of using GPU Time-Slicing together with MIG?

A. Simply doubles the number of GPUs
B. Additional Time-Slicing within MIG partitions for finer resource division
C. Automatic memory capacity expansion
D. Increased network bandwidth

<details>
<summary>View Answer</summary>

**Answer: B. Additional Time-Slicing within MIG partitions for finer resource division**

**Explanation:**
After creating physically isolated GPU instances with MIG, applying Time-Slicing within each MIG instance allows accommodating more workloads.

**MIG + Time-Slicing Combination:**
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

**Benefits:**
- MIG's memory isolation + Time-Slicing's flexibility
- Accommodate more small inference workloads
- Balance between QoS guarantee and utilization improvement

</details>

### 8. What benefit does vLLM's Continuous Batching provide?

A. Fixed batch size
B. New requests dynamically added to existing batches for improved GPU utilization
C. Single request processing only
D. Runs only on CPU

<details>
<summary>View Answer</summary>

**Answer: B. New requests dynamically added to existing batches for improved GPU utilization**

**Explanation:**
Continuous Batching, unlike static batching, dynamically adds new requests to in-progress batches and immediately removes completed requests. This maximizes GPU utilization.

**Static Batching vs Continuous Batching:**
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

**Benefits:**
- Minimize GPU idle time
- Reduce average response time
- 2-4x throughput improvement

</details>

### 9. Which is NOT a factor to consider when determining Chunk Size in RAG systems?

A. Maximum tokens of embedding model
B. LLM context window size
C. GPU temperature threshold
D. Semantic units of documents (paragraphs, sections)

<details>
<summary>View Answer</summary>

**Answer: C. GPU temperature threshold**

**Explanation:**
Chunk Size is the size for splitting documents and should consider embedding model token limits, LLM context size, and semantic structure of documents. GPU temperature is infrastructure-related and unrelated to Chunk Size.

**Chunk Size Factors:**
1. **Embedding model limits**: Usually 512-8192 tokens
2. **LLM context**: Retrieved chunks + question + response must fit in context
3. **Semantic completeness**: Chunks should contain meaningful information
4. **Search accuracy**: Too large = noise, too small = lacking context

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

**Recommended Chunk Sizes:**
- General documents: 500-1000 tokens
- Technical documents: 1000-2000 tokens
- Code: Function/class units

</details>

### 10. What is the most appropriate metric for autoscaling vLLM in EKS?

A. CPU utilization
B. Memory utilization
C. GPU utilization or request queue length
D. Network traffic

<details>
<summary>View Answer</summary>

**Answer: C. GPU utilization or request queue length**

**Explanation:**
LLM inference is GPU-intensive, so scaling based on GPU utilization or vLLM's request queue length (pending requests) is most effective.

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

**Key vLLM Metrics:**
- `vllm_num_requests_running`: Currently processing requests
- `vllm_num_requests_waiting`: Waiting requests
- `vllm_gpu_cache_usage_perc`: KV cache utilization

</details>

## Short Answer Questions

### 1. What is the role of KV Cache in vLLM?

<details>
<summary>View Answer</summary>

**Answer:** Stores Key-Value tensors from previously generated tokens to avoid recomputation when generating new tokens, improving inference speed.

**Explanation:**
In Transformer models, generating each new token requires computing attention over all previous tokens. KV Cache stores already computed Key-Values to prevent redundant computation.

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

**vLLM's PagedAttention:**
Manages KV Cache in page units to prevent memory fragmentation

</details>

### 2. Explain the relationship between "Trace" and "Span" in Langfuse.

<details>
<summary>View Answer</summary>

**Answer:**
- **Trace**: A complete LLM workflow (e.g., from user question to final response)
- **Span**: Individual unit of work within a Trace (e.g., LLM call, tool execution, search)

Trace is the top-level container that includes multiple Spans.

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

### 3. What does "Hybrid Search" mean in RAG?

<details>
<summary>View Answer</summary>

**Answer:** A method that combines keyword-based search (BM25, etc.) with vector similarity search (Dense Retrieval) to improve search quality.

**Hybrid Search Benefits:**
- Keyword search: Strong at exact term matching
- Vector search: Strong at semantic similarity
- Combined: Leverages both advantages

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

### 4. What is the role of "Checkpoint" in LangGraph?

<details>
<summary>View Answer</summary>

**Answer:** Saves intermediate state during graph execution to enable workflow pause/resume, time-travel debugging, and long-running agent state management.

**Checkpoint Usage:**
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

**Checkpoint Use Cases:**
- Save state for long-running agents
- Maintain per-user conversation context
- Debugging: Go back to specific point and re-execute
- Failure recovery: Resume interrupted workflows

</details>

### 5. What does the `--tensor-parallel-size` option in vLLM mean?

<details>
<summary>View Answer</summary>

**Answer:** Specifies the tensor parallelism level for splitting the model across multiple GPUs for parallel inference. Used when large models cannot be loaded into a single GPU's memory.

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

**Requirements:**
- NVLink or high-speed GPU interconnect recommended
- Power of 2 GPU count recommended (1, 2, 4, 8)
- All GPUs must be the same type

</details>

## Hands-on Exercises

### 1. Write a Deployment YAML to deploy vLLM on EKS.
- Model: meta-llama/Llama-2-7b-chat-hf
- GPU: 1 (nvidia.com/gpu)
- Memory utilization: 90%
- Expose OpenAI-compatible API endpoint

<details>
<summary>View Answer</summary>

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

**Test Commands:**
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

### 2. Deploy Langfuse to Kubernetes and write Python code to track LLM calls.

<details>
<summary>View Answer</summary>

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

### 3. Implement a RAG-based Q&A agent workflow graph using LangGraph.
- Nodes: retrieve (search), grade (relevance evaluation), generate (response generation), rewrite (query rewriting)
- If no relevant documents found, rewrite query and search again

<details>
<summary>View Answer</summary>

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

## Advanced Questions

### 1. A financial company wants to build a real-time customer consultation AI agent. Design a production-level architecture integrating vLLM, RAG, LangGraph, and Langfuse. Include high availability, response quality monitoring, and cost optimization strategies.

<details>
<summary>View Answer</summary>

**Financial Customer Consultation AI Agent Architecture**

**1. Overall Architecture:**

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

**Expected Cost Savings:**
- Spot instances: 60-70% savings vs on-demand
- Time-based scaling: 50% savings during off-hours
- Model quantization: 50% GPU savings at same performance
- Caching layer: 30% savings on repeat queries

</details>

### 2. An AI startup wants to build a multi-model inference platform on EKS to manage various LLM models (GPT-4, Claude, Llama, Mistral). Design a platform including Inference Gateway, model routing, A/B testing, and cost optimization strategies.

<details>
<summary>View Answer</summary>

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

**Expected Cost Optimization Results:**
- Smart routing: 30-50% cost savings
- Cascade strategy: Additional 20% savings while maintaining quality
- Self-hosted models: 80% savings on API costs
- A/B testing: Discover optimal model combinations

</details>
