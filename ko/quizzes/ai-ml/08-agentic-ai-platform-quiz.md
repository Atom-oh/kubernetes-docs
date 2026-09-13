# Agentic AI 플랫폼 on EKS 퀴즈

현재 API·실행 경계·검증 한계를 확인하는 20문항입니다.

## 1. PagedAttention이 주로 개선하는 것은 무엇인가요?

<details>
<summary>정답 및 설명</summary>

KV cache 블록 관리와 메모리 낭비입니다. 가중치 압축이나 고정된2–4배 처리량을 보장하지 않습니다.
</details>

## 2. Inference Gateway와 학습 실행기의 역할은 어떻게 다른가요?

<details>
<summary>정답 및 설명</summary>

Gateway는 지원 구현·plugin에 따라 추론 요청의 라우팅·접근·제한을 처리합니다. 학습 실행은 Trainer·Ray 등 별도 경로이며 gateway 설치만으로 모든 보안·A/B 기능이 활성화되지 않습니다.
</details>

## 3. RAG 벡터 저장소에서 반드시 맞춰야 할 것은 무엇인가요?

<details>
<summary>정답 및 설명</summary>

실제 embedding 차원·모델 revision·normalization·metric과 ingestion/query 조건을 맞춰야 합니다. tenant 필드만 추가해서는 격리되지 않으며 인증된 접근 범위의 filter를 서버에서 강제해야 합니다.
</details>

## 4. LangGraph가 제공하는 제어 모델은 무엇인가요?

<details>
<summary>정답 및 설명</summary>

상태 기반 node·edge·조건 분기·순환입니다. 그래프가 존재한다고 도구 실행·상태 영속성·재시도 한도가 자동 구현되지는 않습니다.
</details>

## 5. Langfuse와 DCGM의 관측 범위는 어떻게 다른가요?

<details>
<summary>정답 및 설명</summary>

Langfuse는 계측한 호출·trace·usage·평가를, DCGM은 장치 메트릭을 다룹니다. token 비용 추정은 청구서가 아니며 GPU 온도 같은 인프라 측정과 구분합니다.
</details>

## 6. Kagent 0.10.1의 Agent 예제는 어떤 API 구조를 사용하나요?

<details>
<summary>정답 및 설명</summary>

kagent.dev/v1alpha2의 spec.type과 declarative/BYO 구조입니다. declarative.modelConfig와 McpServer/Agent tool 참조를 사용하며 top-level llm·임의 python/eval 도구·가짜 permissions 필드를 만들지 않습니다.
</details>

## 7. MIG 내부 time-slicing은 어떤 격리를 보장하나요?

<details>
<summary>정답 및 설명</summary>

서로 다른 MIG instance의 격리와 같은 instance 내부 공유를 구분해야 합니다. 같은 instance의 time-slice 사용자 사이에 새 메모리·장애 격리나 비례 compute 보장은 생기지 않습니다.
</details>

## 8. Continuous batching은 요청이 절대 대기하지 않는다는 뜻인가요?

<details>
<summary>정답 및 설명</summary>

아닙니다. scheduler가 단계별로 요청을 편입하지만 token budget·KV cache·동시성·queue 조건에 따라 기다릴 수 있습니다. 성능 향상은 실제 workload에서 측정해야 합니다.
</details>

## 9. Chunk size 1000을 언제1000token이라고 해석할 수 있나요?

<details>
<summary>정답 및 설명</summary>

선택한 splitter가 해당 tokenizer 기준 token 길이를 사용하는 경우입니다. RecursiveCharacterTextSplitter의 기본 길이는 문자 수입니다. embedding·LLM 한도와 의미 단위·recall을 함께 평가해야 합니다.
</details>

## 10. vLLM autoscaling에서 확인할 것은 무엇인가요?

<details>
<summary>정답 및 설명</summary>

실제 vllm: 메트릭 이름, model/Pod label, adapter, queue·latency 신호와 하나의 scaling owner입니다. GPU allocation은 utilization이 아니며 HPA와 KEDA를 같은 replica의 경쟁 owner로 두면 안 됩니다.
</details>

## 11. KV cache는 무엇을 저장하나요?

<details>
<summary>정답 및 설명</summary>

앞선 token의 Key/Value 표현을 저장해 반복 계산을 줄입니다. 전체 응답 cache와 다르며 GQA/MQA·sliding window 등에 따라 메모리 산식도 달라집니다.
</details>

## 12. 현재 Langfuse의 Trace와 Span은 어떻게 다루나요?

<details>
<summary>정답 및 설명</summary>

같은 trace context에서 start_as_current_observation으로 하위 span/generation을 생성하고 usage_details 등을 기록합니다. 이전 trace()/generation() 메서드는 검토한 SDK 4.15.2에 없습니다. 비밀·원문 데이터 기록 범위도 정해야 합니다.
</details>

## 13. Hybrid search가 두 번의 검색 호출만으로 완성되지 않는 이유는 무엇인가요?

<details>
<summary>정답 및 설명</summary>

dense·sparse 결과의 RRF 또는 score fusion, 동일한 접근 filter, 중복 처리와 recall 평가가 필요합니다. 결과 score를 무조건 같은 척도로 더하면 안 됩니다.
</details>

## 14. SqliteSaver 사용에서 원래 예제가 잘못된 부분은 무엇인가요?

<details>
<summary>정답 및 설명</summary>

from_conn_string은 context manager로 사용해야 합니다. :memory:는 영구 저장소가 아니고 PostgreSQL DSN은 SqliteSaver 대상이 아닙니다. history 항목을 읽기만 해서는 replay/resume하지 않으며 thread_id도 사용자 인증을 대신하지 않습니다.
</details>

## 15. TP와 PP의 분할 단위는 무엇인가요?

<details>
<summary>정답 및 설명</summary>

TP는 레이어 내부 텐서 연산을, PP는 레이어 구간을 나눕니다. 무조건2의 거듭제곱이나 고정 모델 크기별GPU 수로 결정하지 말고 architecture·backend·통신·메모리를 확인해야 합니다.
</details>

## 16. 실습: 현재 vLLM 배포를 구성할 때 무엇을 검증하나요?

<details>
<summary>정답 및 설명</summary>

[vLLM 가이드](../../ai-ml/02-vllm-deployment.md)의 고정 image/model revision, GPU·cache·startupProbe와 ClusterIP 예제를 기준으로 namespace·driver·장치 조건을 준비합니다. 실제 모델 호출 없이 스키마가 통과했다는 사실을 성능·가용성 검증으로 바꾸지 않습니다.
</details>

## 17. 실습: Langfuse 배포와 Python 계측에서 무엇을 확인하나요?

<details>
<summary>정답 및 설명</summary>

[본문](../../ai-ml/03-agentic-ai-platform.md)의 현재 SDK 예제를 사용하고 파일 credential, span 연결, flush/shutdown을 확인합니다. chart 2.1.0에는 web/worker·Postgres·Valkey·오브젝트 저장소·ClickHouse와 Operator 선행 조건이 있습니다. 기본 Secret 환경 전달은 파일 전용 정책과 다릅니다.
</details>

## 18. 실습: RAG 재검색이 실패해도 끝없이 반복하거나 무근거 답변을 만들지 않으려면 어떻게 하나요?

<details>
<summary>정답 및 설명</summary>

원래 질문과 search_query를 분리하고 retry count와 recursion limit을 정합니다. 근거가 있으면 generate, 재시도 한도 내면 rewrite, 끝까지 없으면 abstain으로 종료합니다. 본문의 실제 LangGraph 예제는 이 경로와 SQLite 재접속을 로컬 callback으로 검증했습니다.
</details>

## 19. 심화: 금융 상담용 agent의 안전한 경계는 무엇인가요?

<details>
<summary>정답 및 설명</summary>

인증된 tenant/account 범위, retrieval 권한, provider egress 정책, 도구 최소 권한·멱등성·승인, 민감정보 최소 기록과 감사·사람 전달을 설계합니다. requires_human이 이미 true라면 후속 분기가 false로 덮어쓰지 않게 결합해야 합니다. compliance_check라는 함수명이나 LLM 판단만으로 법규 준수가 보장되지는 않습니다.
</details>

## 20. 심화: 멀티모델 라우팅·A/B·비용 최적화를 어떻게 검증하나요?

<details>
<summary>정답 및 설명</summary>

provider별 adapter와 credential을 사용하고 허용 모델·예산·품질 제약을 만족하는 후보가 없으면 거절합니다. 안정된 A/B 배정과 실제 라우팅 consumer, 측정된 guardrail 지표가 필요합니다. cache key는 tenant·권한·모델·검색 revision 등을 포함하고, 추정 비용에 router 호출·재시도·cache·GPU 고정비를 포함합니다. 임의 절감률은 실측 결과가 아닙니다.
</details>

[본문으로 돌아가기](../../ai-ml/03-agentic-ai-platform.md)
