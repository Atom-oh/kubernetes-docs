# Agentic AI 플랫폼 on EKS 퀴즈

이 퀴즈는 Amazon EKS에서 Agentic AI 플랫폼을 구축하기 위한 GPU 관리(MIG/Time-Slicing), vLLM 추론 서버, Inference Gateway, RAG(검색 증강 생성), Kagent, LangGraph, Langfuse 관측성에 대한 이해를 테스트합니다.

## 퀴즈 개요
- GPU 리소스 관리 (MIG, Time-Slicing)
- vLLM 추론 서버 배포 및 최적화
- Kubernetes Gateway API 및 Inference Gateway
- RAG 아키텍처 및 구현
- Kagent (Kubernetes AI Agent)
- LangGraph 워크플로우 오케스트레이션
- Langfuse를 통한 LLM 관측성

## 객관식 문제

### 1. vLLM의 PagedAttention 기술이 해결하는 주요 문제는 무엇인가요?

A. 모델 학습 속도 향상
B. GPU 메모리 단편화로 인한 비효율적인 메모리 사용
C. 네트워크 지연 시간 감소
D. 모델 파라미터 압축

<details>
<summary>정답 보기</summary>

**정답: B. GPU 메모리 단편화로 인한 비효율적인 메모리 사용**

**설명:**
vLLM의 PagedAttention은 KV(Key-Value) 캐시를 페이지 단위로 관리하여 GPU 메모리 단편화 문제를 해결합니다. 이를 통해 동일한 GPU 메모리에서 2-4배 더 많은 요청을 동시에 처리할 수 있습니다.

**PagedAttention 작동 원리:**
- KV 캐시를 고정 크기 블록(페이지)으로 분할
- 비연속적인 메모리 공간 활용 가능
- 동적 메모리 할당/해제로 단편화 방지

```yaml
# vLLM 배포 예시
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
          - "0.9"  # 90% GPU 메모리 활용
        resources:
          limits:
            nvidia.com/gpu: 1
```

**PagedAttention 이점:**
- 메모리 효율성 2-4배 향상
- 처리량(Throughput) 2-4배 증가
- 더 긴 컨텍스트 길이 지원

</details>

### 2. Inference Gateway의 주요 역할로 올바르지 않은 것은?

A. 다중 LLM 백엔드로의 트래픽 라우팅
B. 요청 속도 제한(Rate Limiting)
C. 모델 학습(Training) 작업 관리
D. 로드 밸런싱 및 페일오버

<details>
<summary>정답 보기</summary>

**정답: C. 모델 학습(Training) 작업 관리**

**설명:**
Inference Gateway는 추론(Inference) 요청의 라우팅, 로드 밸런싱, 속도 제한 등을 담당합니다. 모델 학습은 별도의 시스템(예: Kubeflow, Ray)에서 관리합니다.

**Inference Gateway 핵심 기능:**
- 다중 모델 백엔드 라우팅
- 요청 속도 제한 및 쿼터 관리
- A/B 테스팅 및 카나리 배포
- 인증/인가 처리
- 메트릭 수집 및 모니터링

```yaml
# Gateway API를 사용한 Inference Gateway 구성
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

### 3. RAG(Retrieval-Augmented Generation) 아키텍처에서 Vector Database의 역할은?

A. LLM 모델 가중치 저장
B. 문서 임베딩 벡터 저장 및 유사도 검색
C. 사용자 인증 정보 관리
D. API 요청 로깅

<details>
<summary>정답 보기</summary>

**정답: B. 문서 임베딩 벡터 저장 및 유사도 검색**

**설명:**
Vector Database는 문서를 임베딩 모델로 변환한 벡터를 저장하고, 쿼리 벡터와 유사한 문서를 빠르게 검색합니다. 이를 통해 LLM이 관련 컨텍스트를 참조하여 더 정확한 응답을 생성합니다.

**RAG 파이프라인:**
```
[문서] → [임베딩 모델] → [Vector DB]
           ↑
[쿼리] → [임베딩 모델] → [유사도 검색] → [관련 문서] → [LLM] → [응답]
```

```yaml
# Kubernetes에서 Qdrant Vector DB 배포
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

**주요 Vector Database:**
- Qdrant, Milvus, Pinecone
- PostgreSQL + pgvector
- Elasticsearch (Dense Vector)

</details>

### 4. LangGraph의 주요 특징으로 올바른 것은?

A. 단순 선형 체인만 지원
B. 상태 기반 그래프 워크플로우와 순환(Cycle) 지원
C. 단일 LLM만 사용 가능
D. 메모리 기능 미지원

<details>
<summary>정답 보기</summary>

**정답: B. 상태 기반 그래프 워크플로우와 순환(Cycle) 지원**

**설명:**
LangGraph는 LangChain 기반의 그래프 워크플로우 프레임워크로, 복잡한 AI 에이전트 로직을 상태 기반 그래프로 구현할 수 있습니다. 순환(Cycle)을 지원하여 반복적인 의사결정 루프를 구현할 수 있습니다.

**LangGraph 핵심 개념:**
- **StateGraph**: 상태를 관리하는 그래프 구조
- **Node**: 개별 처리 단계 (LLM 호출, 도구 실행 등)
- **Edge**: 노드 간 전이 조건
- **Cycle**: 조건부 반복 (예: 자기 반성 루프)

```python
# LangGraph 에이전트 예시
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated

class AgentState(TypedDict):
    messages: list
    next_action: str

def call_llm(state: AgentState) -> AgentState:
    # LLM 호출 로직
    return {"messages": state["messages"] + [response]}

def call_tool(state: AgentState) -> AgentState:
    # 도구 실행 로직
    return {"messages": state["messages"] + [tool_result]}

def should_continue(state: AgentState) -> str:
    if "FINAL_ANSWER" in state["messages"][-1]:
        return "end"
    return "tool"

# 그래프 구성
workflow = StateGraph(AgentState)
workflow.add_node("agent", call_llm)
workflow.add_node("tool", call_tool)
workflow.add_edge("tool", "agent")  # 도구 실행 후 다시 에이전트로
workflow.add_conditional_edges(
    "agent",
    should_continue,
    {"tool": "tool", "end": END}
)
workflow.set_entry_point("agent")

app = workflow.compile()
```

</details>

### 5. Langfuse에서 추적하는 주요 메트릭이 아닌 것은?

A. 토큰 사용량
B. 응답 지연 시간(Latency)
C. GPU 온도
D. LLM 호출 비용

<details>
<summary>정답 보기</summary>

**정답: C. GPU 온도**

**설명:**
Langfuse는 LLM 애플리케이션의 관측성(Observability) 도구로, 토큰 사용량, 지연 시간, 비용 등 LLM 특화 메트릭을 추적합니다. GPU 온도는 인프라 레벨 메트릭으로 DCGM이나 Prometheus에서 수집합니다.

**Langfuse 주요 기능:**
- Trace 기반 LLM 호출 추적
- 토큰 사용량 및 비용 분석
- 프롬프트 버전 관리
- 사용자 피드백 수집
- 품질 평가(Evaluation)

```yaml
# Langfuse Kubernetes 배포
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
# Python에서 Langfuse 통합
from langfuse import Langfuse

langfuse = Langfuse(
    public_key="pk-...",
    secret_key="sk-...",
    host="https://langfuse.internal.svc"
)

# LLM 호출 추적
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

### 6. Kagent의 주요 목적은 무엇인가요?

A. Kubernetes 클러스터 모니터링
B. AI 에이전트가 Kubernetes API와 상호작용하여 클러스터 관리 자동화
C. 컨테이너 이미지 빌드
D. 네트워크 정책 관리

<details>
<summary>정답 보기</summary>

**정답: B. AI 에이전트가 Kubernetes API와 상호작용하여 클러스터 관리 자동화**

**설명:**
Kagent는 AI 에이전트가 Kubernetes 클러스터를 이해하고 관리할 수 있게 해주는 프레임워크입니다. 자연어 명령을 Kubernetes API 호출로 변환하고, 클러스터 상태를 분석하여 자동화된 운영을 가능하게 합니다.

**Kagent 기능:**
- 자연어 기반 클러스터 관리
- kubectl 명령어 자동 생성 및 실행
- 트러블슈팅 자동화
- 리소스 최적화 권장

```yaml
# Kagent CRD 예시
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
# Kagent 사용 예시
from kagent import KubernetesAgent

agent = KubernetesAgent(
    llm=ChatOpenAI(model="gpt-4"),
    kubeconfig="/path/to/kubeconfig"
)

# 자연어로 클러스터 관리
response = agent.run(
    "production 네임스페이스에서 OOMKilled로 재시작된 Pod를 찾아서 "
    "메모리 limit을 2배로 늘려주세요"
)
```

</details>

### 7. GPU Time-Slicing과 MIG를 함께 사용할 때의 이점은?

A. 단순히 GPU 수가 두 배로 증가
B. MIG 파티션 내에서 추가적인 Time-Slicing으로 더 세밀한 리소스 분할
C. 메모리 용량이 자동으로 확장
D. 네트워크 대역폭 증가

<details>
<summary>정답 보기</summary>

**정답: B. MIG 파티션 내에서 추가적인 Time-Slicing으로 더 세밀한 리소스 분할**

**설명:**
MIG로 물리적으로 격리된 GPU 인스턴스를 생성한 후, 각 MIG 인스턴스 내에서 Time-Slicing을 적용하면 더 많은 워크로드를 수용할 수 있습니다.

**MIG + Time-Slicing 조합:**
```
A100 GPU (40GB)
├── MIG 3g.20gb (인스턴스 1) - 20GB
│   ├── Time-Slice 1 (추론 워크로드 A)
│   └── Time-Slice 2 (추론 워크로드 B)
├── MIG 3g.20gb (인스턴스 2) - 20GB
│   ├── Time-Slice 1 (추론 워크로드 C)
│   └── Time-Slice 2 (추론 워크로드 D)
```

```yaml
# MIG + Time-Slicing 설정
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
        # MIG 인스턴스에 Time-Slicing 적용
        - name: nvidia.com/mig-3g.20gb
          replicas: 2
```

**이점:**
- MIG의 메모리 격리 + Time-Slicing의 유연성
- 더 많은 소형 추론 워크로드 수용
- QoS 보장과 활용률 향상의 균형

</details>

### 8. vLLM의 Continuous Batching이 제공하는 이점은?

A. 배치 크기가 고정됨
B. 새로운 요청이 기존 배치에 동적으로 추가되어 GPU 활용률 향상
C. 단일 요청만 처리
D. CPU에서만 실행됨

<details>
<summary>정답 보기</summary>

**정답: B. 새로운 요청이 기존 배치에 동적으로 추가되어 GPU 활용률 향상**

**설명:**
Continuous Batching(연속 배칭)은 기존의 정적 배칭과 달리, 진행 중인 배치에 새로운 요청을 동적으로 추가하고 완료된 요청은 즉시 제거합니다. 이를 통해 GPU 활용률을 극대화합니다.

**정적 배칭 vs 연속 배칭:**
```
# 정적 배칭 (기존 방식)
[요청1, 요청2, 요청3] → 모든 요청 완료까지 대기 → 결과 반환
(짧은 요청도 긴 요청이 끝날 때까지 대기)

# 연속 배칭 (vLLM)
[요청1, 요청2, 요청3]
  ↓ 요청1 완료, 즉시 반환
[요청2, 요청3, 요청4 추가]
  ↓ 요청2 완료, 즉시 반환
[요청3, 요청4, 요청5 추가]
...
```

```python
# vLLM 서버 연속 배칭 설정
from vllm import LLM, SamplingParams

llm = LLM(
    model="meta-llama/Llama-2-7b-chat-hf",
    tensor_parallel_size=1,
    max_num_batched_tokens=4096,  # 배치당 최대 토큰
    max_num_seqs=256,  # 동시 처리 시퀀스 수
)
```

**이점:**
- GPU 유휴 시간 최소화
- 평균 응답 시간 감소
- 처리량 2-4배 향상

</details>

### 9. RAG 시스템에서 Chunk Size를 결정할 때 고려해야 할 요소가 아닌 것은?

A. 임베딩 모델의 최대 토큰 수
B. LLM의 컨텍스트 윈도우 크기
C. GPU 온도 임계값
D. 문서의 의미적 단위(문단, 섹션)

<details>
<summary>정답 보기</summary>

**정답: C. GPU 온도 임계값**

**설명:**
Chunk Size는 문서를 분할하는 크기로, 임베딩 모델의 토큰 제한, LLM 컨텍스트 크기, 문서의 의미적 구조를 고려해야 합니다. GPU 온도는 인프라 관련 사항으로 Chunk Size와 관련이 없습니다.

**Chunk Size 결정 요소:**
1. **임베딩 모델 제한**: 보통 512-8192 토큰
2. **LLM 컨텍스트**: 검색된 청크들 + 질문 + 응답이 컨텍스트 내에 들어와야 함
3. **의미적 완결성**: 청크가 의미 있는 정보를 담아야 함
4. **검색 정확도**: 너무 크면 노이즈, 너무 작으면 컨텍스트 부족

```python
# LangChain에서 청킹 전략
from langchain.text_splitter import RecursiveCharacterTextSplitter

# 기본 청킹
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,      # 청크 크기
    chunk_overlap=200,    # 청크 간 오버랩
    separators=["\n\n", "\n", ".", " "]
)

# 시맨틱 청킹 (의미 기반)
from langchain_experimental.text_splitter import SemanticChunker
from langchain_openai import OpenAIEmbeddings

semantic_splitter = SemanticChunker(
    OpenAIEmbeddings(),
    breakpoint_threshold_type="percentile"
)
```

**권장 Chunk Size:**
- 일반 문서: 500-1000 토큰
- 기술 문서: 1000-2000 토큰
- 코드: 함수/클래스 단위

</details>

### 10. EKS에서 vLLM을 오토스케일링할 때 가장 적합한 메트릭은?

A. CPU 사용률
B. 메모리 사용률
C. GPU 사용률 또는 요청 큐 길이
D. 네트워크 트래픽

<details>
<summary>정답 보기</summary>

**정답: C. GPU 사용률 또는 요청 큐 길이**

**설명:**
LLM 추론은 GPU 집약적 작업이므로 GPU 사용률이나 vLLM의 요청 큐 길이(대기 중인 요청 수)를 기준으로 스케일링하는 것이 가장 효과적입니다.

```yaml
# KEDA를 사용한 vLLM 오토스케일링
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
  # Prometheus 메트릭 기반
  - type: prometheus
    metadata:
      serverAddress: http://prometheus:9090
      metricName: vllm_num_requests_waiting
      threshold: "10"  # 대기 요청 10개 이상이면 스케일 아웃
      query: |
        sum(vllm_num_requests_waiting{service="vllm"})

  # GPU 사용률 기반
  - type: prometheus
    metadata:
      serverAddress: http://prometheus:9090
      metricName: gpu_utilization
      threshold: "80"
      query: |
        avg(DCGM_FI_DEV_GPU_UTIL{kubernetes_pod_name=~"vllm.*"})

---
# HPA 대안 (GPU 메트릭)
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

**vLLM 주요 메트릭:**
- `vllm_num_requests_running`: 현재 처리 중인 요청
- `vllm_num_requests_waiting`: 대기 중인 요청
- `vllm_gpu_cache_usage_perc`: KV 캐시 사용률

</details>

## 단답형 문제

### 1. vLLM에서 KV Cache의 역할은 무엇인가요?

<details>
<summary>정답 보기</summary>

**정답:** 이전에 생성된 토큰의 Key-Value 텐서를 저장하여 새 토큰 생성 시 재계산을 방지하고 추론 속도를 향상시킵니다.

**설명:**
Transformer 모델에서 새 토큰을 생성할 때마다 이전 모든 토큰에 대한 Attention을 계산해야 합니다. KV Cache는 이미 계산된 Key-Value를 저장하여 중복 계산을 방지합니다.

```
# KV Cache 없이
토큰1 생성: [토큰1] 계산
토큰2 생성: [토큰1, 토큰2] 전체 재계산
토큰3 생성: [토큰1, 토큰2, 토큰3] 전체 재계산
...

# KV Cache 사용
토큰1 생성: [토큰1] 계산 → KV 캐시 저장
토큰2 생성: 캐시된 KV + [토큰2] 계산 → 캐시 업데이트
토큰3 생성: 캐시된 KV + [토큰3] 계산 → 캐시 업데이트
```

**vLLM의 PagedAttention:**
KV Cache를 페이지 단위로 관리하여 메모리 단편화 방지

</details>

### 2. Langfuse에서 "Trace"와 "Span"의 관계를 설명하세요.

<details>
<summary>정답 보기</summary>

**정답:**
- **Trace**: 하나의 완전한 LLM 작업 흐름 (예: 사용자 질문부터 최종 응답까지)
- **Span**: Trace 내의 개별 작업 단위 (예: LLM 호출, 도구 실행, 검색)

Trace는 여러 Span을 포함하는 최상위 컨테이너입니다.

```
Trace: "사용자 질문 처리"
├── Span: "임베딩 생성" (50ms)
├── Span: "벡터 검색" (100ms)
├── Span: "컨텍스트 구성" (10ms)
└── Span: "LLM 호출" (2000ms)
    └── Span: "토큰 스트리밍" (1800ms)
```

```python
# Langfuse에서 Trace/Span 생성
trace = langfuse.trace(
    name="qa-pipeline",
    user_id="user-123"
)

# Span 추가
retrieval_span = trace.span(name="retrieval")
# 검색 로직...
retrieval_span.end()

llm_span = trace.span(name="llm-generation")
# LLM 호출...
llm_span.end(output=response)
```

</details>

### 3. RAG에서 "Hybrid Search"가 의미하는 것은 무엇인가요?

<details>
<summary>정답 보기</summary>

**정답:** 키워드 기반 검색(BM25 등)과 벡터 유사도 검색(Dense Retrieval)을 결합하여 검색 품질을 향상시키는 방법입니다.

**Hybrid Search 장점:**
- 키워드 검색: 정확한 용어 매칭에 강함
- 벡터 검색: 의미적 유사성에 강함
- 결합: 두 가지 장점 활용

```python
# Hybrid Search 예시 (Qdrant)
from qdrant_client import QdrantClient
from qdrant_client.models import SparseVector, SearchRequest

client = QdrantClient(host="qdrant", port=6333)

# Hybrid 검색 실행
results = client.search_batch(
    collection_name="documents",
    requests=[
        # Dense (벡터) 검색
        SearchRequest(
            vector=query_embedding,
            limit=10,
        ),
        # Sparse (키워드) 검색
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

# 결과 융합 (RRF - Reciprocal Rank Fusion)
final_results = reciprocal_rank_fusion(
    results[0], results[1],
    k=60
)
```

</details>

### 4. LangGraph에서 "Checkpoint"의 역할은 무엇인가요?

<details>
<summary>정답 보기</summary>

**정답:** 그래프 실행 중간 상태를 저장하여 워크플로우 중단/재개, 시간 여행(time-travel) 디버깅, 장기 실행 에이전트의 상태 관리를 가능하게 합니다.

**Checkpoint 활용:**
```python
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import StateGraph

# Checkpoint 저장소 설정
memory = SqliteSaver.from_conn_string(":memory:")

# 그래프에 Checkpoint 연결
app = workflow.compile(checkpointer=memory)

# 실행 (자동으로 체크포인트 저장)
config = {"configurable": {"thread_id": "user-123"}}
result = app.invoke(input_state, config)

# 특정 체크포인트로 복원
history = list(app.get_state_history(config))
past_state = history[-2]  # 이전 상태로 복원
```

**Checkpoint 사용 사례:**
- 장기 실행 에이전트의 상태 저장
- 사용자별 대화 컨텍스트 유지
- 디버깅: 특정 시점으로 돌아가 재실행
- 장애 복구: 중단된 워크플로우 재개

</details>

### 5. vLLM의 `--tensor-parallel-size` 옵션의 의미는 무엇인가요?

<details>
<summary>정답 보기</summary>

**정답:** 모델을 여러 GPU에 분할하여 병렬로 추론을 실행하는 텐서 병렬화 수준을 지정합니다. 큰 모델을 단일 GPU 메모리에 로드할 수 없을 때 사용합니다.

**Tensor Parallelism:**
```
# 단일 GPU (tensor-parallel-size=1)
GPU 0: [전체 모델 레이어]

# 2-way Tensor Parallelism (tensor-parallel-size=2)
GPU 0: [레이어의 절반] ←→ GPU 1: [레이어의 나머지 절반]
(각 GPU에서 병렬 계산 후 결과 통신)

# 4-way Tensor Parallelism (tensor-parallel-size=4)
GPU 0-3: 각각 레이어의 1/4 담당
```

```bash
# vLLM 실행 예시
python -m vllm.entrypoints.openai.api_server \
  --model meta-llama/Llama-2-70b-chat-hf \
  --tensor-parallel-size 4 \
  --gpu-memory-utilization 0.9
```

**요구사항:**
- NVLink 또는 고속 GPU 인터커넥트 권장
- GPU 수는 2의 거듭제곱 권장 (1, 2, 4, 8)
- 모든 GPU가 동일한 유형이어야 함

</details>

## 실습 문제

### 1. vLLM을 EKS에 배포하는 Deployment YAML을 작성하세요.
- 모델: meta-llama/Llama-2-7b-chat-hf
- GPU: 1개 (nvidia.com/gpu)
- 메모리 활용률: 90%
- OpenAI 호환 API 엔드포인트 노출

<details>
<summary>정답 보기</summary>

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

**테스트 명령어:**
```bash
# 서비스 확인
kubectl get pods -l app=vllm
kubectl logs -f deployment/vllm-llama2-7b

# API 테스트
kubectl port-forward svc/vllm-llama2-7b 8000:8000

curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "meta-llama/Llama-2-7b-chat-hf",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

</details>

### 2. Langfuse를 Kubernetes에 배포하고 Python 애플리케이션에서 LLM 호출을 추적하는 코드를 작성하세요.

<details>
<summary>정답 보기</summary>

```yaml
# Langfuse Kubernetes 배포
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
# Python 애플리케이션에서 Langfuse 통합
from langfuse import Langfuse
from langfuse.decorators import observe, langfuse_context
import openai

# Langfuse 클라이언트 초기화
langfuse = Langfuse(
    public_key="pk-lf-...",
    secret_key="sk-lf-...",
    host="http://langfuse.default.svc.cluster.local:3000"
)

# 데코레이터를 사용한 자동 추적
@observe()
def rag_pipeline(user_query: str) -> str:
    """RAG 파이프라인 전체 추적"""

    # 검색 단계 추적
    context = retrieve_context(user_query)

    # LLM 호출 추적
    response = generate_response(user_query, context)

    return response

@observe()
def retrieve_context(query: str) -> list:
    """벡터 검색 추적"""
    langfuse_context.update_current_observation(
        metadata={"retriever": "qdrant", "top_k": 5}
    )

    # 실제 검색 로직
    results = vector_db.search(query, limit=5)

    langfuse_context.update_current_observation(
        output={"num_results": len(results)}
    )
    return results

@observe(as_type="generation")
def generate_response(query: str, context: list) -> str:
    """LLM 생성 추적"""

    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": f"Context: {context}\n\nQuestion: {query}"}
    ]

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=messages
    )

    # 토큰 사용량 기록
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

# 사용 예시
if __name__ == "__main__":
    result = rag_pipeline("What is Kubernetes?")
    print(result)

    # Langfuse에 플러시 (비동기 전송 완료 대기)
    langfuse.flush()
```

</details>

### 3. LangGraph를 사용하여 RAG 기반 Q&A 에이전트의 워크플로우 그래프를 구현하세요.
- 노드: retrieve(검색), grade(관련성 평가), generate(응답 생성), rewrite(쿼리 재작성)
- 관련 문서가 없으면 쿼리를 재작성하여 다시 검색

<details>
<summary>정답 보기</summary>

```python
from typing import TypedDict, List, Annotated
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import Qdrant
from langchain.prompts import ChatPromptTemplate

# 상태 정의
class RAGState(TypedDict):
    question: str
    documents: List[str]
    generation: str
    relevance_score: float
    retry_count: int

# LLM 및 검색기 초기화
llm = ChatOpenAI(model="gpt-4", temperature=0)
embeddings = OpenAIEmbeddings()
vectorstore = Qdrant(
    client=qdrant_client,
    collection_name="docs",
    embeddings=embeddings
)
retriever = vectorstore.as_retriever(search_kwargs={"k": 5})

# 노드 함수 정의
def retrieve(state: RAGState) -> RAGState:
    """문서 검색"""
    print(f"🔍 Retrieving documents for: {state['question']}")

    docs = retriever.get_relevant_documents(state["question"])
    return {
        **state,
        "documents": [doc.page_content for doc in docs]
    }

def grade_documents(state: RAGState) -> RAGState:
    """문서 관련성 평가"""
    print("📊 Grading document relevance...")

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
    """응답 생성"""
    print("✍️ Generating response...")

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
    """쿼리 재작성"""
    print("🔄 Rewriting query...")

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

# 라우팅 함수
def should_continue(state: RAGState) -> str:
    """관련성에 따른 라우팅 결정"""

    # 최대 재시도 횟수 체크
    if state.get("retry_count", 0) >= 2:
        print("⚠️ Max retries reached, generating with available docs")
        return "generate"

    # 관련성 점수 체크
    if state["relevance_score"] >= 0.7:
        print("✅ Documents are relevant, proceeding to generate")
        return "generate"
    else:
        print("❌ Documents not relevant enough, rewriting query")
        return "rewrite"

# 그래프 구성
workflow = StateGraph(RAGState)

# 노드 추가
workflow.add_node("retrieve", retrieve)
workflow.add_node("grade", grade_documents)
workflow.add_node("generate", generate)
workflow.add_node("rewrite", rewrite_query)

# 엣지 추가
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
workflow.add_edge("rewrite", "retrieve")  # 재작성 후 다시 검색
workflow.add_edge("generate", END)

# 컴파일
app = workflow.compile()

# 실행 예시
if __name__ == "__main__":
    initial_state = {
        "question": "How does Kubernetes handle pod scheduling?",
        "documents": [],
        "generation": "",
        "relevance_score": 0.0,
        "retry_count": 0
    }

    result = app.invoke(initial_state)
    print(f"\n📝 Final Answer:\n{result['generation']}")
```

**그래프 시각화:**
```
┌─────────────┐
│   START     │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  retrieve   │◄──────────────┐
└──────┬──────┘               │
       │                      │
       ▼                      │
┌─────────────┐               │
│    grade    │               │
└──────┬──────┘               │
       │                      │
       ▼                      │
   ┌───────┐                  │
   │ score │                  │
   │ >=0.7?│                  │
   └───┬───┘                  │
      /│\                     │
     / │ \                    │
    /  │  \                   │
   ▼   │   ▼                  │
 Yes   │   No                 │
   │   │   │                  │
   ▼   │   ▼                  │
┌──────┴───────┐     ┌────────┴────┐
│   generate   │     │   rewrite   │
└──────┬───────┘     └─────────────┘
       │
       ▼
┌─────────────┐
│    END      │
└─────────────┘
```

</details>

## 심화 문제

### 1. 금융 회사에서 실시간 고객 상담 AI 에이전트를 구축하려고 합니다. vLLM, RAG, LangGraph, Langfuse를 통합한 프로덕션 레벨의 아키텍처를 설계하세요. 고가용성, 응답 품질 모니터링, 비용 최적화 전략을 포함해야 합니다.

<details>
<summary>정답 보기</summary>

**금융 고객 상담 AI 에이전트 아키텍처**

**1. 전체 아키텍처:**

```
┌─────────────────────────────────────────────────────────────────┐
│                        EKS Cluster                               │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                 Inference Gateway (Istio)                │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐      │   │
│  │  │ Rate Limit  │  │   A/B Test  │  │   Auth      │      │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘      │   │
│  └──────────────────────────┬──────────────────────────────┘   │
│                             │                                    │
│  ┌──────────────────────────▼──────────────────────────────┐   │
│  │                   LangGraph Agent                        │   │
│  │  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐      │   │
│  │  │Intent│→ │ RAG  │→ │Check │→ │Action│→ │Reply │      │   │
│  │  └──────┘  └──────┘  └──────┘  └──────┘  └──────┘      │   │
│  └─────────────────────────────────────────────────────────┘   │
│                             │                                    │
│  ┌──────────────────────────▼──────────────────────────────┐   │
│  │                  Backend Services                        │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐              │   │
│  │  │  vLLM    │  │  Qdrant  │  │ Langfuse │              │   │
│  │  │ (HA x3) │  │  (HA x3) │  │          │              │   │
│  │  └──────────┘  └──────────┘  └──────────┘              │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

**2. 고가용성 vLLM 배포:**

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
        ports:
        - containerPort: 8000
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 120
          periodSeconds: 10
          failureThreshold: 3
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 180
          periodSeconds: 30

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

**3. LangGraph 에이전트 워크플로우:**

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

# 인텐트 분류
def classify_intent(state: FinanceAgentState) -> FinanceAgentState:
    """고객 문의 인텐트 분류"""
    intents = ["balance_inquiry", "transaction_history",
               "card_issue", "loan_inquiry", "complaint", "general"]

    # LLM을 통한 인텐트 분류
    intent = llm_classify(state["message"], intents)

    # Langfuse 추적
    langfuse.span(name="intent_classification", output={"intent": intent})

    return {**state, "intent": intent}

# RAG 기반 컨텍스트 검색
def retrieve_context(state: FinanceAgentState) -> FinanceAgentState:
    """금융 상품/정책 문서 검색"""

    # 인텐트별 특화 검색
    collection = intent_to_collection.get(state["intent"], "general")

    docs = qdrant_client.search(
        collection_name=collection,
        query_vector=embed(state["message"]),
        limit=5
    )

    # 규정 준수 문서 항상 포함
    compliance_docs = get_compliance_docs(state["intent"])

    return {**state, "context": docs + compliance_docs}

# 컴플라이언스 체크
def compliance_check(state: FinanceAgentState) -> FinanceAgentState:
    """금융 규정 준수 여부 확인"""

    # 민감 정보 검출
    if contains_sensitive_info(state["message"]):
        state["requires_human"] = True

    # 고위험 작업 검출
    if state["intent"] in ["loan_inquiry", "card_issue"]:
        state["requires_human"] = needs_human_approval(state)

    return state

# 액션 실행
def execute_action(state: FinanceAgentState) -> FinanceAgentState:
    """금융 서비스 API 호출"""

    actions = []

    if state["intent"] == "balance_inquiry":
        balance = banking_api.get_balance(state["user_id"])
        actions.append({"type": "balance_check", "result": balance})

    elif state["intent"] == "transaction_history":
        history = banking_api.get_transactions(state["user_id"], limit=10)
        actions.append({"type": "transaction_fetch", "result": history})

    return {**state, "actions_taken": actions}

# 응답 생성
def generate_response(state: FinanceAgentState) -> FinanceAgentState:
    """고객 응답 생성"""

    prompt = finance_response_prompt.format(
        intent=state["intent"],
        context=state["context"],
        actions=state["actions_taken"],
        message=state["message"]
    )

    response = vllm_client.chat.completions.create(
        model="meta-llama/Llama-2-70b-chat-hf",
        messages=[{"role": "user", "content": prompt}]
    )

    # Langfuse에 응답 품질 로깅
    langfuse.generation(
        name="customer_response",
        model="llama-2-70b",
        input=prompt,
        output=response.choices[0].message.content,
        metadata={"intent": state["intent"], "user_id": state["user_id"]}
    )

    return {**state, "response": response.choices[0].message.content}

# 라우팅 함수
def route_by_compliance(state: FinanceAgentState) -> str:
    if state.get("requires_human"):
        return "human_handoff"
    return "execute_action"

# 그래프 구성
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

# 체크포인트 (대화 컨텍스트 유지)
memory = SqliteSaver.from_conn_string("postgresql://...")
app = workflow.compile(checkpointer=memory)
```

**4. 응답 품질 모니터링 (Langfuse):**

```yaml
# Langfuse 품질 평가 작업
apiVersion: batch/v1
kind: CronJob
metadata:
  name: langfuse-evaluation
spec:
  schedule: "0 * * * *"  # 매시간
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: evaluator
            image: finance-ai/evaluator:latest
            env:
            - name: LANGFUSE_HOST
              value: "http://langfuse:3000"
            command:
            - python
            - -c
            - |
              from langfuse import Langfuse

              langfuse = Langfuse()

              # 최근 1시간 트레이스 가져오기
              traces = langfuse.get_traces(
                  filter={"start_time": {"gte": "1h"}}
              )

              # 품질 평가
              for trace in traces:
                  score = evaluate_response(trace)
                  langfuse.score(
                      trace_id=trace.id,
                      name="quality_score",
                      value=score
                  )

              # 낮은 품질 응답 알림
              low_quality = [t for t in traces if t.scores.get("quality_score", 1) < 0.7]
              if low_quality:
                  send_alert(f"Low quality responses: {len(low_quality)}")
```

**5. 비용 최적화:**

```yaml
# KEDA 기반 스케일링
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: vllm-scaler
spec:
  scaleTargetRef:
    name: vllm-finance-agent
  minReplicaCount: 2   # 최소 HA 유지
  maxReplicaCount: 10
  triggers:
  - type: prometheus
    metadata:
      serverAddress: http://prometheus:9090
      metricName: vllm_request_queue_size
      threshold: "20"
      query: |
        sum(vllm_num_requests_waiting{service="vllm-finance"})

  # 업무 시간 외 스케일 다운
  - type: cron
    metadata:
      timezone: Asia/Seoul
      start: "0 22 * * *"  # 22:00
      end: "0 8 * * *"     # 08:00
      desiredReplicas: "2"

---
# Spot 인스턴스 활용 (배치 분석용)
apiVersion: karpenter.sh/v1alpha5
kind: Provisioner
metadata:
  name: finance-spot
spec:
  requirements:
  - key: karpenter.sh/capacity-type
    operator: In
    values: ["spot"]
  - key: node.kubernetes.io/instance-type
    operator: In
    values: ["g5.12xlarge", "g5.24xlarge"]
  limits:
    resources:
      nvidia.com/gpu: 8
```

**비용 절감 예상:**
- Spot 인스턴스: 온디맨드 대비 60-70% 절감
- 시간대별 스케일링: 야간 비용 50% 절감
- 모델 양자화: 동일 성능에서 GPU 50% 절감
- 캐싱 레이어: 반복 쿼리 처리 비용 30% 절감

</details>

### 2. AI 스타트업에서 다양한 LLM 모델(GPT-4, Claude, Llama, Mistral)을 통합 관리하는 멀티 모델 추론 플랫폼을 EKS에 구축하려고 합니다. Inference Gateway, 모델 라우팅, A/B 테스팅, 비용 최적화 전략을 포함한 플랫폼을 설계하세요.

<details>
<summary>정답 보기</summary>

**멀티 모델 추론 플랫폼 설계**

**1. 아키텍처 개요:**

```
                    ┌─────────────────────────────────┐
                    │     Inference Gateway (Kong)     │
                    │  ┌───────┐ ┌───────┐ ┌───────┐  │
                    │  │Rate   │ │A/B    │ │Cost   │  │
                    │  │Limit  │ │Router │ │Track  │  │
                    │  └───────┘ └───────┘ └───────┘  │
                    └──────────────┬──────────────────┘
                                   │
           ┌───────────────────────┼───────────────────────┐
           │                       │                       │
           ▼                       ▼                       ▼
    ┌──────────────┐      ┌──────────────┐      ┌──────────────┐
    │ OpenAI Proxy │      │ Anthropic    │      │    vLLM      │
    │   (GPT-4)    │      │  (Claude)    │      │ (Llama/Mist) │
    └──────────────┘      └──────────────┘      └──────────────┘
           │                       │                       │
           └───────────────────────┼───────────────────────┘
                                   │
                           ┌───────▼───────┐
                           │   Langfuse    │
                           │  Observability│
                           └───────────────┘
```

**2. Inference Gateway 구성 (Kong):**

```yaml
# Kong Gateway 배포
apiVersion: apps/v1
kind: Deployment
metadata:
  name: kong-inference-gateway
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: kong
        image: kong:3.4
        env:
        - name: KONG_DATABASE
          value: "off"
        - name: KONG_DECLARATIVE_CONFIG
          value: "/etc/kong/kong.yml"
        volumeMounts:
        - name: kong-config
          mountPath: /etc/kong
      volumes:
      - name: kong-config
        configMap:
          name: kong-config

---
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
      - name: request-transformer
        config:
          add:
            headers:
            - "Authorization: Bearer $(OPENAI_API_KEY)"

    # Anthropic Claude
    - name: anthropic-claude
      url: https://api.anthropic.com
      routes:
      - name: claude-route
        paths:
        - /v1/claude
      plugins:
      - name: rate-limiting
        config:
          minute: 100

    # Self-hosted vLLM (Llama/Mistral)
    - name: vllm-llama
      url: http://vllm-llama:8000
      routes:
      - name: llama-route
        paths:
        - /v1/llama

    - name: vllm-mistral
      url: http://vllm-mistral:8000
      routes:
      - name: mistral-route
        paths:
        - /v1/mistral

    # 통합 엔드포인트 (스마트 라우팅)
    - name: unified-inference
      url: http://model-router:8080
      routes:
      - name: unified-route
        paths:
        - /v1/chat/completions
```

**3. 스마트 모델 라우터:**

```python
# model_router.py
from fastapi import FastAPI, Request
from pydantic import BaseModel
from typing import Optional
import httpx
import asyncio

app = FastAPI()

# 모델별 설정
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
        """비용 최적화 라우팅"""
        candidates = [
            model for model, config in MODEL_CONFIG.items()
            if config["latency_p99"] <= max_latency
        ]
        return min(candidates, key=lambda m: MODEL_CONFIG[m]["cost_per_1k_input"])

    @staticmethod
    def quality_optimized(task_type: str) -> str:
        """품질 최적화 라우팅"""
        if task_type in ["reasoning", "coding"]:
            return "gpt-4"
        elif task_type in ["analysis", "safety"]:
            return "claude-3-opus"
        return "llama-70b"

    @staticmethod
    def latency_optimized(max_latency: int = 1000) -> str:
        """지연시간 최적화 라우팅"""
        candidates = [
            model for model, config in MODEL_CONFIG.items()
            if config["latency_p99"] <= max_latency
        ]
        return candidates[0] if candidates else "mistral-7b"

@app.post("/v1/chat/completions")
async def route_completion(request: Request):
    body = await request.json()

    # 라우팅 힌트 추출
    routing_hint = request.headers.get("X-Routing-Strategy", "balanced")
    task_type = request.headers.get("X-Task-Type", "general")
    max_latency = int(request.headers.get("X-Max-Latency", "5000"))

    # 모델 선택
    if routing_hint == "cost":
        model = RoutingStrategy.cost_optimized(task_type, max_latency)
    elif routing_hint == "quality":
        model = RoutingStrategy.quality_optimized(task_type)
    elif routing_hint == "latency":
        model = RoutingStrategy.latency_optimized(max_latency)
    else:
        # Balanced: 품질과 비용의 균형
        model = "llama-70b"

    # 선택된 모델로 요청 전달
    config = MODEL_CONFIG[model]

    async with httpx.AsyncClient() as client:
        response = await client.post(
            config["endpoint"],
            json=body,
            headers={"Authorization": f"Bearer {get_api_key(model)}"}
        )

    # 비용 추적
    track_cost(model, body, response.json())

    return response.json()
```

**4. A/B 테스팅 구성:**

```yaml
# Istio VirtualService를 통한 A/B 테스팅
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: model-ab-test
spec:
  hosts:
  - inference.internal
  http:
  # A/B 테스트: GPT-4 vs Claude for reasoning tasks
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

  # A/B 테스트: Llama vs Mistral for general tasks
  - match:
    - headers:
        x-task-type:
          exact: "general"
    route:
    - destination:
        host: vllm-llama
      weight: 70
      headers:
        response:
          add:
            x-model-variant: "llama-control"
    - destination:
        host: vllm-mistral
      weight: 30
      headers:
        response:
          add:
            x-model-variant: "mistral-treatment"

---
# A/B 테스트 결과 수집
apiVersion: v1
kind: ConfigMap
metadata:
  name: ab-test-config
data:
  experiments.yaml: |
    experiments:
    - name: reasoning-model-comparison
      start_date: "2024-01-01"
      end_date: "2024-01-31"
      variants:
        - name: gpt4-control
          model: gpt-4
          traffic_percentage: 50
        - name: claude-treatment
          model: claude-3-opus
          traffic_percentage: 50
      metrics:
        - name: quality_score
          type: primary
        - name: latency_p99
          type: guardrail
          threshold: 5000
        - name: cost_per_request
          type: secondary
```

**5. 비용 최적화 전략:**

```python
# cost_optimizer.py
from dataclasses import dataclass
from typing import Dict
import asyncio

@dataclass
class ModelCost:
    input_cost: float  # per 1K tokens
    output_cost: float
    fixed_cost: float = 0  # GPU 비용 등

class CostOptimizer:
    def __init__(self):
        self.model_costs = {
            "gpt-4": ModelCost(0.03, 0.06),
            "gpt-3.5-turbo": ModelCost(0.0015, 0.002),
            "claude-3-opus": ModelCost(0.015, 0.075),
            "claude-3-sonnet": ModelCost(0.003, 0.015),
            "llama-70b": ModelCost(0.001, 0.002, fixed_cost=2.5),  # GPU 시간당
            "mistral-7b": ModelCost(0.0005, 0.001, fixed_cost=0.5),
        }

        # 모델별 품질 점수 (1-10)
        self.quality_scores = {
            "gpt-4": 9.5,
            "gpt-3.5-turbo": 7.5,
            "claude-3-opus": 9.0,
            "claude-3-sonnet": 8.0,
            "llama-70b": 8.5,
            "mistral-7b": 7.0,
        }

    def estimate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """요청 비용 추정"""
        cost = self.model_costs[model]
        return (
            (input_tokens / 1000) * cost.input_cost +
            (output_tokens / 1000) * cost.output_cost
        )

    def select_model(
        self,
        task_complexity: str,  # simple, medium, complex
        budget_per_request: float,
        min_quality: float = 7.0
    ) -> str:
        """예산 내 최적 모델 선택"""

        # 태스크별 예상 토큰
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

        # 품질/비용 비율이 가장 높은 모델 선택
        if not candidates:
            return "mistral-7b"  # Fallback to cheapest

        return max(candidates, key=lambda x: x[2] / x[1])[0]

    def cascade_strategy(self, prompt: str) -> Dict:
        """캐스케이드 전략: 저비용 모델 먼저, 실패 시 고비용 모델"""
        return {
            "primary": "mistral-7b",
            "fallback_chain": ["llama-70b", "gpt-3.5-turbo", "gpt-4"],
            "confidence_threshold": 0.8
        }

# Kubernetes CronJob으로 비용 리포트 생성
"""
apiVersion: batch/v1
kind: CronJob
metadata:
  name: cost-report
spec:
  schedule: "0 9 * * 1"  # 매주 월요일 9시
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: reporter
            image: cost-reporter:latest
            command:
            - python
            - -c
            - |
              from langfuse import Langfuse
              import pandas as pd

              langfuse = Langfuse()

              # 지난 주 사용량 집계
              traces = langfuse.get_traces(
                  filter={"start_time": {"gte": "7d"}}
              )

              # 모델별 비용 계산
              costs = {}
              for trace in traces:
                  model = trace.metadata.get("model")
                  usage = trace.usage
                  cost = calculate_cost(model, usage)
                  costs[model] = costs.get(model, 0) + cost

              # Slack 리포트 전송
              send_slack_report(costs)
"""
```

**6. 통합 모니터링:**

```yaml
# Grafana 대시보드 설정
apiVersion: v1
kind: ConfigMap
metadata:
  name: grafana-dashboards
data:
  multi-model-dashboard.json: |
    {
      "title": "Multi-Model Inference Platform",
      "panels": [
        {
          "title": "Model Usage Distribution",
          "type": "piechart",
          "targets": [{
            "expr": "sum(inference_requests_total) by (model)"
          }]
        },
        {
          "title": "Cost per Model (Daily)",
          "type": "timeseries",
          "targets": [{
            "expr": "sum(rate(inference_cost_total[1d])) by (model)"
          }]
        },
        {
          "title": "Latency by Model (P99)",
          "type": "timeseries",
          "targets": [{
            "expr": "histogram_quantile(0.99, sum(rate(inference_latency_bucket[5m])) by (model, le))"
          }]
        },
        {
          "title": "Quality Score by Model",
          "type": "gauge",
          "targets": [{
            "expr": "avg(langfuse_quality_score) by (model)"
          }]
        },
        {
          "title": "A/B Test Results",
          "type": "table",
          "targets": [{
            "expr": "ab_test_conversion_rate"
          }]
        }
      ]
    }
```

**비용 최적화 결과 예상:**
- 스마트 라우팅으로 30-50% 비용 절감
- 캐스케이드 전략으로 품질 유지하며 20% 추가 절감
- Self-hosted 모델 활용으로 API 비용 80% 절감
- A/B 테스팅으로 최적 모델 조합 발견

</details>
