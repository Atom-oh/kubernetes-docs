# OpenTelemetry 퀴즈

OpenTelemetry에 대한 이해도를 테스트하는 퀴즈입니다.

---

1. OpenTelemetry가 지원하는 세 가지 신호(Signal)는?
   - A) Logs, Metrics, Events
   - B) Traces, Metrics, Logs
   - C) Spans, Counters, Logs
   - D) Traces, Alerts, Logs

<details>
<summary>정답 보기</summary>

**정답: B) Traces, Metrics, Logs**

**설명:**
OpenTelemetry는 관측성의 세 가지 핵심 신호인 Traces(분산 추적), Metrics(메트릭), Logs(로그)를 표준화합니다. 이 세 가지 신호를 통합적으로 수집하고 상관분석할 수 있어, 시스템의 전체적인 관측성을 확보할 수 있습니다.

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

4. OTEL Collector의 tail_sampling 프로세서가 head-based 샘플링보다 유리한 경우는?
   - A) 리소스 사용량을 최소화해야 할 때
   - B) 오류나 지연이 있는 요청을 놓치지 않아야 할 때
   - C) 구현이 간단해야 할 때
   - D) 샘플링 결정을 빠르게 해야 할 때

<details>
<summary>정답 보기</summary>

**정답: B) 오류나 지연이 있는 요청을 놓치지 않아야 할 때**

**설명:**
Tail-based 샘플링은 요청이 완료된 후 결과(오류, 지연 등)를 보고 샘플링 여부를 결정합니다. 이를 통해 중요한 요청(오류 발생, 응답 시간 초과)을 놓치지 않습니다. 반면 head-based 샘플링은 요청 시작 시점에 결정하므로 구현이 간단하고 리소스 사용량이 적지만, 중요한 요청을 놓칠 수 있습니다.

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
Resource는 텔레메트리 데이터를 생성하는 엔티티(서비스, 호스트, 컨테이너 등)를 식별하는 메타데이터입니다. service.name, service.version, deployment.environment 같은 속성을 포함하여 데이터의 출처를 명확히 합니다. 이 정보는 모든 텔레메트리 데이터에 자동으로 첨부됩니다.

</details>

---

6. EKS에서 OTEL Collector 배포 패턴 중 가장 리소스 효율적인 것은?
   - A) Sidecar 패턴
   - B) DaemonSet 패턴
   - C) Gateway 패턴
   - D) Deployment 패턴

<details>
<summary>정답 보기</summary>

**정답: B) DaemonSet 패턴**

**설명:**
DaemonSet 패턴은 각 노드에 하나의 Collector만 실행하므로 리소스 효율적입니다. Sidecar 패턴은 각 Pod마다 Collector를 실행하여 리소스 오버헤드가 큽니다. Gateway 패턴은 중앙 집중식이지만 단일 장애점이 될 수 있습니다. 일반적으로 DaemonSet으로 수집하고 Gateway로 처리/전송하는 조합이 권장됩니다.

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
OpenTelemetry Operator는 `instrumentation.opentelemetry.io/inject-{language}` 형식의 annotation을 사용합니다. 언어별로 inject-java, inject-python, inject-nodejs, inject-dotnet, inject-go 등을 사용합니다. 이 annotation이 있는 Pod에 자동으로 계측 에이전트가 주입됩니다.

</details>

---

8. OTEL Collector 설정에서 memory_limiter 프로세서의 역할은?
   - A) 데이터 압축
   - B) 메모리 부족 시 데이터 손실 방지
   - C) 캐시 관리
   - D) 네트워크 버퍼 관리

<details>
<summary>정답 보기</summary>

**정답: B) 메모리 부족 시 데이터 손실 방지**

**설명:**
memory_limiter 프로세서는 Collector의 메모리 사용량을 모니터링하고 제한합니다. 메모리 사용량이 limit_mib에 도달하면 새 데이터 수신을 거부하여 OOM(Out of Memory)으로 인한 데이터 손실을 방지합니다. spike_limit_mib는 갑작스러운 메모리 증가에 대한 버퍼를 제공합니다.

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
W3C Trace Context의 traceparent 헤더는 `version-trace_id-parent_id-trace_flags` 형식으로 구성됩니다. version은 형식 버전, trace_id는 전체 추적 식별자, parent_id는 부모 스팬 ID, trace_flags는 샘플링 플래그입니다. span-name은 Span 내부에 저장되며 전파 헤더에 포함되지 않습니다.

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
OTEL Collector의 pipeline 설정에서 exporters 배열에 여러 exporter를 나열하면 동일한 데이터가 모든 백엔드로 전송됩니다. 예: `exporters: [otlp/tempo, awsxray, datadog]`. 이를 통해 하나의 Collector로 여러 관측성 백엔드를 동시에 사용할 수 있습니다.

</details>

---
