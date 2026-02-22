# Observability 실습 Part 3: MSA 배포 및 카나리 퀴즈

> **마지막 업데이트**: 2025년 2월

이 퀴즈는 Observability 실습 Part 3의 MSA 배포 및 카나리 배포에 대한 이해도를 테스트합니다.

---

1. ArgoCD ApplicationSet의 Generator 중 멀티 클러스터 배포에 가장 적합한 것은?
   - A) List Generator
   - B) Git Generator
   - C) Cluster Generator
   - D) Matrix Generator만 사용
<details>
<summary>정답 보기</summary>

**정답: C) Cluster Generator**

**설명:**
Cluster Generator는 ArgoCD에 등록된 클러스터 목록을 기반으로 Application을 자동 생성합니다. 새 클러스터가 등록되면 자동으로 해당 클러스터에 Application이 생성되어 멀티 클러스터 배포에 이상적입니다. List Generator는 정적 목록을 사용하고, Git Generator는 Git 저장소 구조를 기반으로 합니다. Matrix Generator는 여러 Generator를 조합할 때 사용합니다.

</details>

---

2. ArgoCD의 App-of-Apps 패턴을 사용하는 주요 장점은?
   - A) 단일 Application으로 모든 워크로드를 배포할 수 있다
   - B) 루트 Application이 하위 Application들을 선언적으로 관리하여 계층적 구조와 의존성 관리가 가능하다
   - C) Git 저장소 없이 배포할 수 있다
   - D) 수동 동기화만 지원한다
<details>
<summary>정답 보기</summary>

**정답: B) 루트 Application이 하위 Application들을 선언적으로 관리하여 계층적 구조와 의존성 관리가 가능하다**

**설명:**
App-of-Apps 패턴에서 루트 Application은 다른 Application 리소스들을 포함하는 디렉토리를 가리킵니다. 이를 통해 전체 플랫폼을 하나의 진입점에서 관리할 수 있고, 환경별(dev, staging, prod) 구성을 쉽게 분리할 수 있습니다. 또한 Sync Wave를 사용하여 Application 간 배포 순서를 제어할 수 있습니다.

</details>

---

3. Karpenter NodePool 설정에서 weight와 limits의 역할로 올바른 것은?
   - A) weight는 노드 수를 제한하고, limits는 우선순위를 결정한다
   - B) weight는 여러 NodePool 간 우선순위를 결정하고, limits는 NodePool이 프로비저닝할 수 있는 최대 리소스를 제한한다
   - C) 두 설정은 동일한 기능을 수행한다
   - D) weight는 필수이고, limits는 선택 사항이다
<details>
<summary>정답 보기</summary>

**정답: B) weight는 여러 NodePool 간 우선순위를 결정하고, limits는 NodePool이 프로비저닝할 수 있는 최대 리소스를 제한한다**

**설명:**
Karpenter에서 weight는 여러 NodePool이 있을 때 어떤 NodePool을 우선적으로 사용할지 결정합니다(높은 weight가 우선). limits는 해당 NodePool이 프로비저닝할 수 있는 최대 CPU, 메모리, GPU 등의 리소스 상한을 설정합니다. 이를 통해 비용 최적화된 인스턴스 타입을 우선 사용하거나, 특정 워크로드의 리소스 사용량을 제한할 수 있습니다.

</details>

---

4. KEDA ScaledObject에서 SQS 트리거를 사용할 때 스케일링 기준이 되는 메트릭은?
   - A) SQS 메시지 크기
   - B) SQS 대기열의 메시지 수(ApproximateNumberOfMessages) 또는 처리 시간
   - C) SQS 비용
   - D) SQS 리전
<details>
<summary>정답 보기</summary>

**정답: B) SQS 대기열의 메시지 수(ApproximateNumberOfMessages) 또는 처리 시간**

**설명:**
KEDA의 SQS 스케일러는 주로 `ApproximateNumberOfMessages`(대기 중인 메시지 수)를 기준으로 Pod를 스케일링합니다. 또한 `ApproximateNumberOfMessagesNotVisible`(처리 중인 메시지), `ApproximateAgeOfOldestMessage`(가장 오래된 메시지 대기 시간) 등의 메트릭도 사용할 수 있습니다. queueLength 파라미터로 Pod당 처리할 메시지 수를 지정하여 스케일링 동작을 조정합니다.

</details>

---

5. OpenTelemetry의 auto-instrumentation과 manual instrumentation의 차이점으로 올바른 것은?
   - A) Auto-instrumentation은 성능이 더 좋다
   - B) Auto-instrumentation은 코드 수정 없이 에이전트가 자동으로 계측하고, manual instrumentation은 SDK를 사용해 개발자가 직접 span을 생성한다
   - C) Manual instrumentation만 트레이스를 생성할 수 있다
   - D) 두 방식은 동시에 사용할 수 없다
<details>
<summary>정답 보기</summary>

**정답: B) Auto-instrumentation은 코드 수정 없이 에이전트가 자동으로 계측하고, manual instrumentation은 SDK를 사용해 개발자가 직접 span을 생성한다**

**설명:**
Auto-instrumentation은 Java agent, Python auto-instrumentation 등을 통해 애플리케이션 코드 수정 없이 HTTP 요청, 데이터베이스 쿼리 등을 자동으로 계측합니다. Manual instrumentation은 OTel SDK를 사용하여 개발자가 비즈니스 로직의 특정 부분에 커스텀 span과 속성을 추가합니다. 실제로는 두 방식을 함께 사용하여 자동 계측으로 기본 커버리지를 확보하고, 필요한 곳에 수동 계측을 추가합니다.

</details>

---

6. Java 서비스에서 OpenTelemetry auto-instrumentation을 적용하는 방법은?
   - A) 애플리케이션 코드에 OTel SDK 의존성을 추가한다
   - B) JVM 시작 시 `-javaagent:opentelemetry-javaagent.jar` 옵션으로 에이전트를 로드한다
   - C) Kubernetes Annotation만 추가하면 된다
   - D) 별도의 sidecar 컨테이너를 배포한다
<details>
<summary>정답 보기</summary>

**정답: B) JVM 시작 시 `-javaagent:opentelemetry-javaagent.jar` 옵션으로 에이전트를 로드한다**

**설명:**
Java에서 OTel auto-instrumentation은 Java agent 방식을 사용합니다. JVM 시작 시 `-javaagent:opentelemetry-javaagent.jar` 옵션을 추가하면 에이전트가 바이트코드를 조작하여 HTTP 클라이언트, 데이터베이스 드라이버, 프레임워크 등을 자동으로 계측합니다. Kubernetes에서는 OTel Operator의 Instrumentation CRD를 사용하여 Pod annotation 기반으로 자동 주입을 설정할 수도 있습니다.

</details>

---

7. Argo Rollouts의 Canary 전략에서 AnalysisTemplate의 역할은?
   - A) 카나리 Pod의 리소스를 관리한다
   - B) 배포 중 메트릭을 쿼리하여 카나리 버전의 성공/실패를 자동으로 판단한다
   - C) Git 저장소와 동기화한다
   - D) 네트워크 정책을 설정한다
<details>
<summary>정답 보기</summary>

**정답: B) 배포 중 메트릭을 쿼리하여 카나리 버전의 성공/실패를 자동으로 판단한다**

**설명:**
AnalysisTemplate은 Argo Rollouts의 자동화된 카나리 분석을 정의합니다. Prometheus, Datadog 등에서 메트릭을 쿼리하고, 성공 조건(예: 에러율 < 1%)을 평가하여 카나리 배포를 계속 진행할지 롤백할지 자동으로 결정합니다. 이를 통해 수동 개입 없이 안전한 점진적 배포가 가능합니다.

</details>

---

8. 다음 PromQL 쿼리의 의미로 올바른 것은?
```
sum(rate(http_requests_total{status=~"2.."}[5m])) / sum(rate(http_requests_total[5m]))
```
   - A) 총 요청 수를 계산한다
   - B) 최근 5분간 2xx 응답의 비율(성공률)을 계산한다
   - C) 5xx 에러율을 계산한다
   - D) 평균 응답 시간을 계산한다
<details>
<summary>정답 보기</summary>

**정답: B) 최근 5분간 2xx 응답의 비율(성공률)을 계산한다**

**설명:**
이 쿼리는 두 부분으로 구성됩니다. 분자는 `status=~"2.."` (정규표현식으로 200-299 상태 코드)인 요청의 초당 비율이고, 분모는 모든 요청의 초당 비율입니다. 둘을 나누면 성공률(0~1 사이 값)이 계산됩니다. Argo Rollouts의 AnalysisTemplate에서 이런 쿼리를 사용하여 카나리 버전의 성공률이 임계값 이상인지 검증합니다.

</details>

---

9. Argo Rollouts에서 카나리 배포 중 AnalysisRun이 FAIL 상태가 되면 어떤 일이 발생하는가?
   - A) 배포가 일시 중지되고 수동 개입을 기다린다
   - B) Rollout이 자동으로 이전 안정 버전으로 롤백된다
   - C) 카나리 트래픽 비율이 증가한다
   - D) 아무 일도 발생하지 않는다
<details>
<summary>정답 보기</summary>

**정답: B) Rollout이 자동으로 이전 안정 버전으로 롤백된다**

**설명:**
AnalysisRun이 FAIL 상태가 되면 Argo Rollouts는 자동으로 롤백을 수행합니다. 카나리 ReplicaSet이 스케일 다운되고, 안정(stable) ReplicaSet이 전체 트래픽을 처리하게 됩니다. 이것이 Progressive Delivery의 핵심 가치로, 메트릭 기반으로 문제를 감지하면 자동으로 안전한 상태로 복구하여 사용자 영향을 최소화합니다.

</details>

---

10. OpenTelemetry SDK에서 Context Propagation (W3C TraceContext)의 중요성은?
    - A) 로그 형식을 표준화한다
    - B) 서비스 간 호출에서 TraceID와 SpanID를 HTTP 헤더로 전달하여 분산 트레이스를 연결한다
    - C) 메트릭 수집 성능을 향상시킨다
    - D) 데이터베이스 연결을 관리한다
<details>
<summary>정답 보기</summary>

**정답: B) 서비스 간 호출에서 TraceID와 SpanID를 HTTP 헤더로 전달하여 분산 트레이스를 연결한다**

**설명:**
W3C TraceContext는 분산 추적을 위한 표준 HTTP 헤더 형식입니다. `traceparent` 헤더에 TraceID, SpanID, 샘플링 플래그가 포함되어 서비스 간 호출 시 전파됩니다. 이를 통해 여러 마이크로서비스에 걸친 요청이 하나의 트레이스로 연결되어, 전체 요청 흐름을 시각화하고 병목 지점을 파악할 수 있습니다. Context Propagation 없이는 각 서비스의 트레이스가 분리되어 상관관계를 파악할 수 없습니다.

</details>
