# Cilium Service Mesh 관찰성 퀴즈

이 퀴즈는 Hubble, 메트릭 수집, 서비스 맵, Golden Signals 모니터링, OpenTelemetry 통합에 대한 이해를 테스트합니다.

## 퀴즈 문제

### 1. Hubble의 주요 구성 요소가 아닌 것은?

A. Hubble Observer
B. Hubble Relay
C. Hubble Router
D. Hubble UI

<details>
<summary>정답 및 설명</summary>

**정답: C. Hubble Router**

**설명:**
Hubble의 주요 구성 요소는 Hubble Observer(Cilium Agent에 내장), Hubble Relay(클러스터 전체 흐름 집계), Hubble UI(시각화 대시보드), Hubble CLI(명령줄 인터페이스)입니다. Hubble Router는 존재하지 않는 구성 요소입니다.

</details>

### 2. Hubble CLI에서 HTTP 트래픽만 필터링하여 관찰하는 명령은?

A. hubble observe --type http
B. hubble observe --protocol http
C. hubble observe --filter http
D. hubble observe --layer http

<details>
<summary>정답 및 설명</summary>

**정답: B. hubble observe --protocol http**

**설명:**
`hubble observe --protocol http` 명령을 사용하여 HTTP 프로토콜 트래픽만 필터링할 수 있습니다. 다른 프로토콜(tcp, dns 등)도 동일한 방식으로 필터링 가능합니다.

</details>

### 3. Hubble 메트릭을 Prometheus에서 수집하기 위해 values.yaml에서 활성화해야 하는 설정은?

A. hubble.prometheus.enabled: true
B. hubble.metrics.enabled
C. hubble.export.prometheus: true
D. prometheus.hubble: true

<details>
<summary>정답 및 설명</summary>

**정답: B. hubble.metrics.enabled**

**설명:**
Hubble 메트릭을 활성화하려면 hubble.metrics.enabled 아래에 수집할 메트릭 유형(dns, drop, tcp, flow, http 등)을 리스트로 지정합니다. 또한 serviceMonitor.enabled: true로 설정하면 Prometheus Operator가 자동으로 스크래핑합니다.

</details>

### 4. Golden Signals 모니터링의 네 가지 지표가 아닌 것은?

A. Latency (지연 시간)
B. Traffic (처리량)
C. Availability (가용성)
D. Saturation (포화도)

<details>
<summary>정답 및 설명</summary>

**정답: C. Availability (가용성)**

**설명:**
Google SRE에서 정의한 네 가지 Golden Signals는 Latency(지연 시간), Traffic(처리량), Errors(오류율), Saturation(포화도)입니다. Availability는 Golden Signals에 포함되지 않으며, Errors 지표를 통해 간접적으로 측정됩니다.

</details>

### 5. Hubble에서 정책에 의해 거부된 트래픽을 관찰하는 올바른 명령은?

A. hubble observe --denied
B. hubble observe --verdict DROPPED
C. hubble observe --blocked
D. hubble observe --policy-denied

<details>
<summary>정답 및 설명</summary>

**정답: B. hubble observe --verdict DROPPED**

**설명:**
`--verdict DROPPED` 옵션을 사용하여 네트워크 정책에 의해 거부된 트래픽을 필터링합니다. 반대로 `--verdict FORWARDED`는 허용된 트래픽을 보여줍니다.

</details>

### 6. HTTP P99 지연 시간을 측정하기 위한 PromQL 쿼리에서 사용하는 함수는?

A. avg()
B. histogram_quantile()
C. rate()
D. sum()

<details>
<summary>정답 및 설명</summary>

**정답: B. histogram_quantile()**

**설명:**
P99 지연 시간 같은 백분위수 메트릭은 histogram_quantile() 함수를 사용합니다. 예: `histogram_quantile(0.99, rate(hubble_http_request_duration_seconds_bucket[5m]))`. 여기서 0.99는 99번째 백분위수를 의미합니다.

</details>

### 7. Hubble UI에서 제공하는 주요 기능이 아닌 것은?

A. 서비스 맵 (Service Map)
B. 흐름 타임라인 (Flow Timeline)
C. 자동 스케일링 (Auto Scaling)
D. 네임스페이스 필터 (Namespace Filter)

<details>
<summary>정답 및 설명</summary>

**정답: C. 자동 스케일링 (Auto Scaling)**

**설명:**
Hubble UI는 서비스 맵, 흐름 타임라인, 네임스페이스 필터, verdict 필터, 개별 흐름의 L7 상세 정보를 제공합니다. 자동 스케일링은 관찰성 기능이 아니라 워크로드 관리 기능입니다.

</details>

### 8. Cilium에서 HTTP 오류율을 계산하는 PromQL 쿼리의 올바른 형태는?

A. hubble_http_errors_total / hubble_http_requests_total
B. sum(rate(hubble_http_responses_total{status=~"5.."}[5m])) / sum(rate(hubble_http_responses_total[5m]))
C. count(hubble_http_errors) / count(hubble_http_requests)
D. hubble_http_error_rate

<details>
<summary>정답 및 설명</summary>

**정답: B. sum(rate(hubble_http_responses_total{status=~"5.."}[5m])) / sum(rate(hubble_http_responses_total[5m]))**

**설명:**
HTTP 오류율은 5xx 응답 수를 전체 응답 수로 나누어 계산합니다. rate() 함수로 초당 비율을 계산하고, status 레이블 필터(status=~"5..")로 서버 오류만 선택합니다.

</details>

### 9. Hubble에서 특정 서비스로 향하는 트래픽만 관찰하는 옵션은?

A. --destination-service
B. --to-service
C. --target-service
D. --svc

<details>
<summary>정답 및 설명</summary>

**정답: B. --to-service**

**설명:**
`hubble observe --to-service <service-name>` 명령을 사용하여 특정 서비스로 향하는 트래픽을 필터링합니다. 반대로 `--from-service`는 특정 서비스에서 나가는 트래픽을 필터링합니다.

</details>

### 10. Cilium에서 연결 추적 테이블 사용률을 모니터링하는 메트릭은?

A. cilium_ct_usage
B. cilium_datapath_conntrack_active
C. cilium_connections_total
D. cilium_ct_table_size

<details>
<summary>정답 및 설명</summary>

**정답: B. cilium_datapath_conntrack_active**

**설명:**
cilium_datapath_conntrack_active 메트릭은 현재 활성 연결 수를 나타냅니다. cilium_datapath_conntrack_max와 함께 사용하여 연결 추적 테이블 사용률을 계산할 수 있습니다.

</details>

### 11. Hubble의 출력을 JSON 형식으로 받으려면 어떤 옵션을 사용해야 하나요?

A. --format json
B. -o json
C. --json
D. --output-type json

<details>
<summary>정답 및 설명</summary>

**정답: B. -o json**

**설명:**
`hubble observe -o json` 명령을 사용하여 JSON 형식의 출력을 받을 수 있습니다. 이는 jq와 같은 도구로 파이프하여 추가 처리하는 데 유용합니다.

</details>

### 12. OpenTelemetry Collector와 Hubble을 통합할 때 사용하는 프로토콜은?

A. HTTP REST API
B. OTLP (OpenTelemetry Protocol)
C. Prometheus Remote Write
D. StatsD

<details>
<summary>정답 및 설명</summary>

**정답: B. OTLP (OpenTelemetry Protocol)**

**설명:**
Hubble은 OpenTelemetry Protocol(OTLP)을 사용하여 OpenTelemetry Collector로 흐름 데이터를 내보낼 수 있습니다. 이를 통해 Jaeger, Prometheus, Loki 등 다양한 백엔드로 데이터를 라우팅할 수 있습니다.

</details>
