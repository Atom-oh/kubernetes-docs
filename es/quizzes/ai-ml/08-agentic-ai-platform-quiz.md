# Cuestionario sobre la plataforma de Agentic AI en EKS

Este cuestionario evalúa tu comprensión sobre la creación de plataformas de Agentic AI en Amazon EKS, incluyendo la gestión de GPU (MIG/Time-Slicing), el servidor de inferencia vLLM, Inference Gateway, RAG (Retrieval-Augmented Generation), Kagent, LangGraph y la observabilidad con Langfuse.

## Resumen del cuestionario
- Gestión de recursos de GPU (MIG, Time-Slicing)
- Despliegue y optimización del servidor de inferencia vLLM
- Kubernetes Gateway API e Inference Gateway
- Arquitectura e implementación de RAG
- Kagent (Kubernetes AI Agent)
- Orquestación de workflows con LangGraph
- Observabilidad de LLM con Langfuse

## Preguntas de opción múltiple

### 1. ¿Qué problema principal resuelve la tecnología PagedAttention de vLLM?

A. Entrenamiento de modelos más rápido
B. Uso ineficiente de memoria debido a la fragmentación de memoria de GPU
C. Latencia de red reducida
D. Compresión de parámetros del modelo

<details>
<summary>Ver respuesta</summary>

**Respuesta: B. Uso ineficiente de memoria debido a la fragmentación de memoria de GPU**

**Explicación:**
PagedAttention de vLLM gestiona la caché KV (Key-Value) en unidades de página para resolver problemas de fragmentación de memoria de GPU. Esto permite procesar de 2 a 4 veces más solicitudes de forma concurrente con la misma memoria de GPU.

**Cómo funciona PagedAttention:**
- Divide la caché KV en bloques de tamaño fijo (páginas)
- Permite usar espacio de memoria no contiguo
- Evita la fragmentación mediante asignación/desasignación dinámica de memoria

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

**Beneficios de PagedAttention:**
- Mejora de 2 a 4 veces en la eficiencia de memoria
- Aumento de 2 a 4 veces en el throughput
- Soporte para longitudes de contexto más largas

</details>

### 2. ¿Cuál NO es un rol principal de un Inference Gateway?

A. Enrutamiento de tráfico a múltiples backends de LLM
B. Limitación de tasa de solicitudes
C. Gestión de trabajos de entrenamiento de modelos
D. Balanceo de carga y failover

<details>
<summary>Ver respuesta</summary>

**Respuesta: C. Gestión de trabajos de entrenamiento de modelos**

**Explicación:**
Inference Gateway maneja el enrutamiento, el balanceo de carga y la limitación de tasa para solicitudes de inferencia. El entrenamiento de modelos lo gestionan sistemas separados (por ejemplo, Kubeflow, Ray).

**Características principales de Inference Gateway:**
- Enrutamiento de backends multi-modelo
- Limitación de tasa de solicitudes y gestión de cuotas
- Pruebas A/B y despliegues canary
- Manejo de autenticación/autorización
- Recolección de métricas y monitoreo

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

### 3. ¿Cuál es el rol de una Vector Database en la arquitectura RAG (Retrieval-Augmented Generation)?

A. Almacenar pesos de modelos LLM
B. Almacenar vectores de embeddings de documentos y realizar búsqueda por similitud
C. Gestionar información de autenticación de usuarios
D. Registrar solicitudes de API

<details>
<summary>Ver respuesta</summary>

**Respuesta: B. Almacenar vectores de embeddings de documentos y realizar búsqueda por similitud**

**Explicación:**
Una Vector Database almacena vectores convertidos desde documentos mediante modelos de embeddings y busca rápidamente documentos similares a los vectores de consulta. Esto permite que los LLM hagan referencia a contexto relevante y generen respuestas más precisas.

**Pipeline de RAG:**
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

**Vector Databases populares:**
- Qdrant, Milvus, Pinecone
- PostgreSQL + pgvector
- Elasticsearch (Dense Vector)

</details>

### 4. ¿Cuál es la característica clave de LangGraph?

A. Solo admite cadenas lineales simples
B. Workflows de grafos basados en estado con soporte para ciclos
C. Solo puede usar un único LLM
D. Sin soporte de memoria

<details>
<summary>Ver respuesta</summary>

**Respuesta: B. Workflows de grafos basados en estado con soporte para ciclos**

**Explicación:**
LangGraph es un framework de workflow de grafos basado en LangChain que permite implementar lógica compleja de agentes de AI como grafos basados en estado. Admite ciclos para implementar bucles iterativos de toma de decisiones.

**Conceptos principales de LangGraph:**
- **StateGraph**: Estructura de grafo que gestiona el estado
- **Node**: Pasos individuales de procesamiento (llamadas a LLM, ejecución de herramientas, etc.)
- **Edge**: Condiciones de transición entre nodos
- **Cycle**: Bucles condicionales (por ejemplo, bucles de autorreflexión)

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

### 5. ¿Cuál NO es una métrica rastreada por Langfuse?

A. Uso de tokens
B. Latencia de respuesta
C. Temperatura de GPU
D. Costo de llamadas a LLM

<details>
<summary>Ver respuesta</summary>

**Respuesta: C. Temperatura de GPU**

**Explicación:**
Langfuse es una herramienta de observabilidad para aplicaciones LLM que rastrea métricas específicas de LLM, como uso de tokens, latencia y costo. La temperatura de GPU es una métrica de nivel de infraestructura recopilada por DCGM o Prometheus.

**Características principales de Langfuse:**
- Seguimiento de llamadas a LLM basado en trazas
- Análisis de uso y costo de tokens
- Gestión de versiones de prompts
- Recolección de feedback de usuarios
- Evaluación de calidad

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

### 6. ¿Cuál es el propósito principal de Kagent?

A. Monitoreo de clusters Kubernetes
B. Permitir que agentes de AI interactúen con la Kubernetes API para la gestión automatizada de clusters
C. Construcción de imágenes de contenedores
D. Gestión de políticas de red

<details>
<summary>Ver respuesta</summary>

**Respuesta: B. Permitir que agentes de AI interactúen con la Kubernetes API para la gestión automatizada de clusters**

**Explicación:**
Kagent es un framework que permite a los agentes de AI comprender y gestionar clusters Kubernetes. Convierte comandos en lenguaje natural en llamadas a la Kubernetes API y permite operaciones automatizadas mediante el análisis del estado del cluster.

**Características de Kagent:**
- Gestión de clusters basada en lenguaje natural
- Generación y ejecución automática de comandos kubectl
- Automatización de troubleshooting
- Recomendaciones de optimización de recursos

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

### 7. ¿Cuál es el beneficio de usar GPU Time-Slicing junto con MIG?

A. Simplemente duplica el número de GPU
B. Time-Slicing adicional dentro de particiones MIG para una división de recursos más fina
C. Expansión automática de la capacidad de memoria
D. Mayor ancho de banda de red

<details>
<summary>Ver respuesta</summary>

**Respuesta: B. Time-Slicing adicional dentro de particiones MIG para una división de recursos más fina**

**Explicación:**
Después de crear instancias de GPU físicamente aisladas con MIG, aplicar Time-Slicing dentro de cada instancia MIG permite acomodar más workloads.

**Combinación MIG + Time-Slicing:**
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

**Beneficios:**
- Aislamiento de memoria de MIG + flexibilidad de Time-Slicing
- Acomoda más workloads de inferencia pequeños
- Equilibrio entre garantía de QoS y mejora de utilización

</details>

### 8. ¿Qué beneficio aporta Continuous Batching de vLLM?

A. Tamaño de batch fijo
B. Nuevas solicitudes agregadas dinámicamente a batches existentes para mejorar la utilización de GPU
C. Solo procesamiento de una única solicitud
D. Se ejecuta solo en CPU

<details>
<summary>Ver respuesta</summary>

**Respuesta: B. Nuevas solicitudes agregadas dinámicamente a batches existentes para mejorar la utilización de GPU**

**Explicación:**
Continuous Batching, a diferencia del batching estático, agrega dinámicamente nuevas solicitudes a batches en curso y elimina inmediatamente las solicitudes completadas. Esto maximiza la utilización de GPU.

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

**Beneficios:**
- Minimiza el tiempo inactivo de GPU
- Reduce el tiempo medio de respuesta
- Mejora de 2 a 4 veces en el throughput

</details>

### 9. ¿Cuál NO es un factor a considerar al determinar el Chunk Size en sistemas RAG?

A. Tokens máximos del modelo de embeddings
B. Tamaño de la ventana de contexto del LLM
C. Umbral de temperatura de GPU
D. Unidades semánticas de los documentos (párrafos, secciones)

<details>
<summary>Ver respuesta</summary>

**Respuesta: C. Umbral de temperatura de GPU**

**Explicación:**
Chunk Size es el tamaño para dividir documentos y debe considerar los límites de tokens del modelo de embeddings, el tamaño de contexto del LLM y la estructura semántica de los documentos. La temperatura de GPU está relacionada con la infraestructura y no tiene relación con Chunk Size.

**Factores de Chunk Size:**
1. **Límites del modelo de embeddings**: Normalmente 512-8192 tokens
2. **Contexto del LLM**: Los chunks recuperados + la pregunta + la respuesta deben caber en el contexto
3. **Completitud semántica**: Los chunks deben contener información significativa
4. **Precisión de búsqueda**: Demasiado grande = ruido, demasiado pequeño = falta de contexto

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

**Tamaños de Chunk recomendados:**
- Documentos generales: 500-1000 tokens
- Documentos técnicos: 1000-2000 tokens
- Código: unidades de función/clase

</details>

### 10. ¿Cuál es la métrica más adecuada para autoscaling de vLLM en EKS?

A. Utilización de CPU
B. Utilización de memoria
C. Utilización de GPU o longitud de la cola de solicitudes
D. Tráfico de red

<details>
<summary>Ver respuesta</summary>

**Respuesta: C. Utilización de GPU o longitud de la cola de solicitudes**

**Explicación:**
La inferencia de LLM es intensiva en GPU, por lo que escalar según la utilización de GPU o la longitud de la cola de solicitudes de vLLM (solicitudes pendientes) es lo más efectivo.

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

**Métricas clave de vLLM:**
- `vllm_num_requests_running`: Solicitudes en procesamiento actualmente
- `vllm_num_requests_waiting`: Solicitudes en espera
- `vllm_gpu_cache_usage_perc`: Utilización de la caché KV

</details>

## Preguntas de respuesta corta

### 1. ¿Cuál es el rol de KV Cache en vLLM?

<details>
<summary>Ver respuesta</summary>

**Respuesta:** Almacena tensores Key-Value de tokens generados previamente para evitar recálculos al generar nuevos tokens, mejorando la velocidad de inferencia.

**Explicación:**
En modelos Transformer, generar cada nuevo token requiere calcular atención sobre todos los tokens anteriores. KV Cache almacena Key-Values ya calculados para evitar computación redundante.

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

**PagedAttention de vLLM:**
Gestiona KV Cache en unidades de página para evitar la fragmentación de memoria

</details>

### 2. Explica la relación entre "Trace" y "Span" en Langfuse.

<details>
<summary>Ver respuesta</summary>

**Respuesta:**
- **Trace**: Un workflow LLM completo (por ejemplo, desde la pregunta del usuario hasta la respuesta final)
- **Span**: Unidad individual de trabajo dentro de un Trace (por ejemplo, llamada a LLM, ejecución de herramienta, búsqueda)

Trace es el contenedor de nivel superior que incluye múltiples Spans.

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

### 3. ¿Qué significa "Hybrid Search" en RAG?

<details>
<summary>Ver respuesta</summary>

**Respuesta:** Un método que combina búsqueda basada en palabras clave (BM25, etc.) con búsqueda por similitud vectorial (Dense Retrieval) para mejorar la calidad de búsqueda.

**Beneficios de Hybrid Search:**
- Búsqueda por palabras clave: fuerte en coincidencias exactas de términos
- Búsqueda vectorial: fuerte en similitud semántica
- Combinada: aprovecha ambas ventajas

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

### 4. ¿Cuál es el rol de "Checkpoint" en LangGraph?

<details>
<summary>Ver respuesta</summary>

**Respuesta:** Guarda el estado intermedio durante la ejecución del grafo para permitir pausar/reanudar workflows, depuración con time-travel y gestión del estado de agentes de larga duración.

**Uso de Checkpoint:**
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

**Casos de uso de Checkpoint:**
- Guardar estado para agentes de larga duración
- Mantener contexto de conversación por usuario
- Depuración: volver a un punto específico y reejecutar
- Recuperación ante fallos: reanudar workflows interrumpidos

</details>

### 5. ¿Qué significa la opción `--tensor-parallel-size` en vLLM?

<details>
<summary>Ver respuesta</summary>

**Respuesta:** Especifica el nivel de paralelismo de tensores para dividir el modelo entre múltiples GPU para inferencia paralela. Se usa cuando modelos grandes no pueden cargarse en la memoria de una sola GPU.

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

**Requisitos:**
- Se recomienda NVLink o interconexión GPU de alta velocidad
- Se recomienda un recuento de GPU en potencias de 2 (1, 2, 4, 8)
- Todas las GPU deben ser del mismo tipo

</details>

## Ejercicios prácticos

### 1. Escribe un YAML de Deployment para desplegar vLLM en EKS.
- Modelo: meta-llama/Llama-2-7b-chat-hf
- GPU: 1 (nvidia.com/gpu)
- Utilización de memoria: 90%
- Exponer endpoint de API compatible con OpenAI

<details>
<summary>Ver respuesta</summary>

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

**Comandos de prueba:**
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

### 2. Despliega Langfuse en Kubernetes y escribe código Python para rastrear llamadas a LLM.

<details>
<summary>Ver respuesta</summary>

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

### 3. Implementa un grafo de workflow de agente de preguntas y respuestas basado en RAG usando LangGraph.
- Nodos: retrieve (búsqueda), grade (evaluación de relevancia), generate (generación de respuesta), rewrite (reescritura de consulta)
- Si no se encuentran documentos relevantes, reescribe la consulta y busca de nuevo

<details>
<summary>Ver respuesta</summary>

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

**Visualización del grafo:**
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

## Preguntas avanzadas

### 1. Una empresa financiera quiere crear un agente de AI de consulta de clientes en tiempo real. Diseña una arquitectura de nivel de producción que integre vLLM, RAG, LangGraph y Langfuse. Incluye alta disponibilidad, monitoreo de calidad de respuestas y estrategias de optimización de costos.

<details>
<summary>Ver respuesta</summary>

**Arquitectura de agente de AI para consulta de clientes financieros**

**1. Arquitectura general:**

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

**2. Deployment de vLLM de alta disponibilidad:**

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

**3. Workflow del agente LangGraph:**

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

**4. Monitoreo de calidad de respuestas (Langfuse):**

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

**5. Optimización de costos:**

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

**Ahorros de costos esperados:**
- Instancias Spot: 60-70% de ahorro frente a on-demand
- Escalado basado en tiempo: 50% de ahorro fuera de horario
- Cuantización de modelos: 50% de ahorro de GPU con el mismo rendimiento
- Capa de caché: 30% de ahorro en consultas repetidas

</details>

### 2. Una startup de AI quiere crear una plataforma de inferencia multi-modelo en EKS para gestionar varios modelos LLM (GPT-4, Claude, Llama, Mistral). Diseña una plataforma que incluya Inference Gateway, enrutamiento de modelos, pruebas A/B y estrategias de optimización de costos.

<details>
<summary>Ver respuesta</summary>

**Diseño de plataforma de inferencia multi-modelo**

**1. Resumen de la arquitectura:**

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

**2. Configuración de Inference Gateway (Kong):**

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

**3. Enrutador inteligente de modelos:**

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

**4. Configuración de pruebas A/B:**

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

**5. Estrategia de optimización de costos:**

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

**Resultados esperados de optimización de costos:**
- Enrutamiento inteligente: 30-50% de ahorro de costos
- Estrategia de cascada: 20% adicional de ahorro mientras se mantiene la calidad
- Modelos self-hosted: 80% de ahorro en costos de API
- Pruebas A/B: descubrir combinaciones óptimas de modelos

</details>
