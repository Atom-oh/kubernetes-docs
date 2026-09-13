# OpenTelemetry 퀴즈

> **마지막 업데이트**: 2026년 9월 13일

OpenTelemetry에 대한 이해도를 테스트하는 퀴즈입니다.

---

1. 이 문서에서 중점적으로 다루는 세 가지 핵심 신호는?
   - A) Logs, Metrics, Events
   - B) Traces, Metrics, Logs
   - C) Spans, Counters, Logs
   - D) Traces, Alerts, Logs

<details>
<summary>정답 보기</summary>

**정답: B) Traces, Metrics, Logs**

**설명:**
이 문서는 traces·metrics·logs를 중점적으로 다룹니다. OpenTelemetry는 profiling 지원도 개발하며 신호·컴포넌트·언어별 안정성이 다릅니다. Exporter 세 개를 켜는 것만으로 상관관계가 만들어지지는 않으며 일관된 Resource 속성과 컨텍스트 전파가 필요합니다.

</details>

---

2. OpenTelemetry Collector의 구성 요소 순서로 올바른 것은?
   - A) Processors → Receivers → Exporters
   - B) Exporters → Processors → Receivers
   - C) Receivers → Processors → Exporters
   - D) Receivers → Exporters → Processors

<details>
<summary>정답 보기</summary>

**정답: C) Receivers → Processors → Exporters**

**설명:**
OTEL Collector의 파이프라인은 Receivers(데이터 수신) → Processors(데이터 처리/변환) → Exporters(백엔드 전송) 순서로 구성됩니다. Receivers는 다양한 형식의 데이터를 수신하고, Processors는 배치 처리, 필터링, 속성 추가 등을 수행하며, Exporters는 처리된 데이터를 목적지로 전송합니다.

</details>

---

3. OpenTelemetry에서 자동 계측(Auto-instrumentation)의 장점이 아닌 것은?
   - A) 코드 변경 없이 계측 가능
   - B) 빠른 도입
   - C) 세밀한 비즈니스 로직 추적
   - D) 일관된 메타데이터

<details>
<summary>정답 보기</summary>

**정답: C) 세밀한 비즈니스 로직 추적**

**설명:**
자동 계측은 코드 변경 없이 HTTP, 데이터베이스, 메시지 큐 등 일반적인 라이브러리 호출을 자동으로 추적합니다. 하지만 비즈니스 로직 내의 세부적인 작업이나 커스텀 메트릭은 수동 계측이 필요합니다. 자동 계측과 수동 계측을 함께 사용하는 것이 일반적입니다.

</details>

---

4. Head-based 샘플링과 비교해 Collector의 tail_sampling 프로세서가 유용한 경우는?
   - A) 리소스 사용량을 최소화해야 할 때
   - B) 관측한 span 상태와 소요 시간을 샘플링 결정에 반영할 때
   - C) 구현이 간단해야 할 때
   - D) 샘플링 결정을 빠르게 해야 할 때

<details>
<summary>정답 보기</summary>

**정답: B) 관측한 span 상태와 소요 시간을 샘플링 결정에 반영할 때**

**설명:**
Collector 0.160.0의 기본 `trace-complete` 전략은 결정 타이머가 동작할 때까지 모은 span을 평가합니다. 이름만으로 요청이나 trace의 완료가 보장되지는 않습니다. Head sampling에서 이미 버린 span은 복구할 수 없으며 늦은 도착·용량 한도·재시도·라우팅 변경도 보존 결과에 영향을 줍니다. 상태를 유지하는 tail sampling에는 같은 trace의 span을 동일 sampling Collector로 보내는 구성이 필요하며 모든 오류·지연 요청의 보존을 보장하지 않습니다.

</details>

---

5. OpenTelemetry SDK에서 Resource의 역할은?
   - A) 네트워크 연결 관리
   - B) 텔레메트리 데이터를 생성하는 엔티티 식별
   - C) 데이터 압축
   - D) 인증 토큰 관리

<details>
<summary>정답 보기</summary>

**정답: B) 텔레메트리 데이터를 생성하는 엔티티 식별**

**설명:**
Resource는 `service.name`, `service.version`, `deployment.environment.name` 등으로 텔레메트리 생산자를 식별합니다. 구성한 SDK/provider가 전송 데이터에 연결하며 Kubernetes·클라우드·사용자 지정 신원 속성은 해당 설정이나 detector가 필요합니다. 모든 속성을 자동으로 알아내는 것은 아닙니다.

</details>

---

6. 배치 대상인 각 노드에 보통 Collector 하나를 실행하는 Kubernetes 워크로드는?
   - A) Sidecar 패턴
   - B) DaemonSet 패턴
   - C) Gateway 패턴
   - D) Deployment 패턴

<details>
<summary>정답 보기</summary>

**정답: B) DaemonSet 패턴**

**설명:**
DaemonSet은 selector·taint·스케줄링 조건을 충족하는 각 노드에 Pod를 배치하며 EKS Fargate에서는 지원되지 않습니다. Sidecar는 앱 Pod를 공유하고 gateway는 여러 replica로 구성할 수도 있는 중앙 계층입니다. 실제 신호량·노드/Pod 수·격리·가용성·상태 유지 처리 요구를 비교해야 하며 항상 가장 효율적인 패턴은 없습니다. DaemonSet 앞의 ClusterIP Service도 자동으로 같은 노드에 연결하지 않습니다.

</details>

---

7. OpenTelemetry Operator를 사용한 자동 계측 주입에서 Pod에 적용하는 annotation은?
   - A) `otel.io/inject: "true"`
   - B) `instrumentation.opentelemetry.io/inject-java: "true"`
   - C) `opentelemetry.io/auto: "enabled"`
   - D) `trace.otel.io/enabled: "true"`

<details>
<summary>정답 보기</summary>

**정답: B) instrumentation.opentelemetry.io/inject-java: "true"**

**설명:**
Operator는 언어별 injection annotation을 사용합니다. Deployment에서는 `spec.template.metadata.annotations`에 넣고 올바른 namespace의 기존 Instrumentation 리소스를 참조합니다. 정상 webhook과 지원되는 언어·runtime 설정도 필요합니다. 기존 Pod를 소급 계측하지 않으며 Go 등 언어별 전제 조건은 별도로 검토해야 합니다.

</details>

---

8. OTEL Collector 설정에서 memory_limiter 프로세서의 역할은?
   - A) 데이터 압축
   - B) 설정한 메모리 임계값 초과 시 backpressure 적용
   - C) 캐시 관리
   - D) 네트워크 버퍼 관리

<details>
<summary>정답 보기</summary>

**정답: B) 설정한 메모리 임계값 초과 시 backpressure 적용**

**설명:**
`limit_mib`는 hard limit이고 soft limit은 `limit_mib - spike_limit_mib`입니다. Soft limit을 넘으면 재시도 가능한 오류로 데이터를 거부하고 hard limit을 넘으면 GC도 강제합니다. 앞단의 재시도·backpressure 처리가 없으면 거부한 데이터는 손실될 수 있습니다. 컨테이너 메모리 한도 아래에 여유를 두어야 하며 durable storage나 절대적인 OOM·손실 방지 보장은 아닙니다.

</details>

---

9. OpenTelemetry의 W3C Trace Context 표준에서 traceparent 헤더의 구성 요소가 아닌 것은?
   - A) version
   - B) trace-id
   - C) parent-id
   - D) span-name

<details>
<summary>정답 보기</summary>

**정답: D) span-name**

**설명:**
OpenTelemetry는 W3C Trace Context 표준을 사용합니다. `traceparent`에는 version·trace ID·parent ID·trace flags가 있으며 parent ID는 전송하는 span을 식별하고 flags에는 sampled bit가 포함됩니다. Span 이름은 이 헤더에 없으며 컨텍스트 전파만으로 span이 기록·전송되는 것도 아닙니다.

</details>

---

10. OTEL Collector에서 다중 백엔드로 데이터를 전송할 때 pipeline 설정 방법은?
    - A) 각 백엔드마다 별도의 Collector 실행
    - B) exporters 배열에 여러 exporter 나열
    - C) 하나의 exporter에 여러 endpoint 설정
    - D) fanout 프로세서 사용

<details>
<summary>정답 보기</summary>

**정답: B) exporters 배열에 여러 exporter 나열**

**설명:**
Pipeline의 신호를 지원하며 실제 구성한 exporter를 나열합니다. 예를 들어 해당 컴포넌트를 포함한 배포판의 traces는 `exporters: [otlp/tempo, awsxray, datadog]`로 보낼 수 있습니다. 여러 백엔드에 대한 원자적 트랜잭션은 아니므로 exporter 오류·queue·재시도·변환·백엔드 수락 여부에 따라 실제 보존 결과가 달라질 수 있습니다.

</details>

---

[본문으로 돌아가기](../../../observability/tracing/03-opentelemetry.md)
