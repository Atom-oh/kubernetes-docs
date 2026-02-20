# 로그 수집기 비교 퀴즈

로그 수집기(FluentBit, Promtail, Alloy, OTEL Collector)에 대한 이해도를 테스트하는 퀴즈입니다.

---

1. 다음 로그 수집기 중 메모리 사용량이 가장 적은 것은?

   - A) Promtail
   - B) FluentBit
   - C) Grafana Alloy
   - D) OpenTelemetry Collector

<details>
<summary>정답 보기</summary>

**정답: B) FluentBit**

**설명:**
FluentBit은 C로 작성되어 메모리 사용량이 약 10-50MB로 가장 적습니다. 나머지는 Go로 작성되어 약 50-100MB의 메모리를 사용합니다.

</details>

---

2. FluentBit 설정에서 Kubernetes 메타데이터(namespace, pod_name 등)를 로그에 추가하는 FILTER는?

   - A) [FILTER] Name modify
   - B) [FILTER] Name kubernetes
   - C) [FILTER] Name parser
   - D) [FILTER] Name record_modifier

<details>
<summary>정답 보기</summary>

**정답: B) [FILTER] Name kubernetes**

**설명:**
FluentBit의 `kubernetes` 필터는 Kubernetes API를 통해 파드, 네임스페이스, 레이블 등의 메타데이터를 자동으로 로그에 추가합니다.

</details>

---

3. Promtail의 주요 제한사항은?

   - A) JSON 파싱 미지원
   - B) Loki 외 다른 목적지로 전송 불가
   - C) Kubernetes 환경에서 사용 불가
   - D) 멀티라인 로그 처리 불가

<details>
<summary>정답 보기</summary>

**정답: B) Loki 외 다른 목적지로 전송 불가**

**설명:**
Promtail은 Grafana Loki 전용 에이전트로 설계되어, OpenSearch, CloudWatch 등 다른 목적지로의 전송을 지원하지 않습니다. 다중 목적지가 필요하면 FluentBit이나 OTEL Collector를 사용해야 합니다.

</details>

---

4. Grafana Alloy의 설정 언어는?

   - A) YAML
   - B) JSON
   - C) River (HCL 유사)
   - D) INI

<details>
<summary>정답 보기</summary>

**정답: C) River (HCL 유사)**

**설명:**
Grafana Alloy는 River라는 HCL(HashiCorp Configuration Language)과 유사한 설정 언어를 사용합니다. YAML보다 더 표현력이 풍부하고 재사용 가능한 컴포넌트를 정의할 수 있습니다.

</details>

---

5. OpenTelemetry Collector의 파이프라인 구성 요소 순서는?

   - A) Processors → Receivers → Exporters
   - B) Receivers → Exporters → Processors
   - C) Receivers → Processors → Exporters
   - D) Exporters → Processors → Receivers

<details>
<summary>정답 보기</summary>

**정답: C) Receivers → Processors → Exporters**

**설명:**
OTEL Collector 파이프라인은 Receivers(데이터 수신) → Processors(데이터 처리/변환) → Exporters(데이터 전송) 순서로 구성됩니다.

</details>

---

6. FluentBit에서 복잡한 로그 처리 로직을 구현하기 위해 사용할 수 있는 스크립팅 언어는?

   - A) Python
   - B) JavaScript
   - C) Lua
   - D) Ruby

<details>
<summary>정답 보기</summary>

**정답: C) Lua**

**설명:**
FluentBit은 Lua 스크립팅을 지원하여 복잡한 로그 처리 로직(필드 변환, 조건부 처리, 민감 정보 마스킹 등)을 구현할 수 있습니다. `[FILTER] Name lua` 필터를 사용합니다.

</details>

---

7. Promtail 설정에서 특정 로그를 제외하는 pipeline_stages 설정은?

   - A) stage.filter
   - B) stage.drop
   - C) stage.exclude
   - D) stage.ignore

<details>
<summary>정답 보기</summary>

**정답: B) stage.drop**

**설명:**
Promtail의 `stage.drop`은 정규식이나 조건에 맞는 로그 라인을 제외합니다. 예: `expression: "healthcheck|readiness"`로 헬스체크 로그를 제외할 수 있습니다.

</details>

---

8. AWS 환경에서 CloudWatch Logs와 OpenSearch 모두에 로그를 전송해야 할 때 가장 적합한 수집기는?

   - A) Promtail
   - B) FluentBit
   - C) Grafana Alloy
   - D) Logstash

<details>
<summary>정답 보기</summary>

**정답: B) FluentBit**

**설명:**
FluentBit은 `cloudwatch_logs`와 `opensearch` 출력 플러그인을 모두 네이티브로 지원합니다. AWS에서 제공하는 `aws-for-fluent-bit` 이미지로 쉽게 배포할 수 있습니다. Promtail과 Alloy는 Loki에 최적화되어 있습니다.

</details>

---

9. OpenTelemetry Collector에서 메모리 사용량을 제한하는 processor는?

   - A) batch
   - B) memory_limiter
   - C) resource
   - D) filter

<details>
<summary>정답 보기</summary>

**정답: B) memory_limiter**

**설명:**
`memory_limiter` processor는 OTEL Collector의 메모리 사용량을 모니터링하고, 설정된 한계에 도달하면 데이터 수집을 일시 중단하여 OOM을 방지합니다.

</details>

---

10. 기존 Promtail 환경에서 메트릭과 트레이스도 함께 수집해야 할 때 권장되는 마이그레이션 대상은?

    - A) FluentBit
    - B) Logstash
    - C) Grafana Alloy
    - D) Filebeat

<details>
<summary>정답 보기</summary>

**정답: C) Grafana Alloy**

**설명:**
Grafana Alloy는 Promtail의 후속 프로젝트로, Promtail의 모든 기능을 포함하면서 메트릭(Prometheus)과 트레이스(Tempo)도 수집할 수 있습니다. Promtail 설정을 River 문법으로 쉽게 마이그레이션할 수 있습니다.

</details>
