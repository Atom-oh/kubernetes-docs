# Cilium Service Mesh 관측성 퀴즈

Cilium 1.20.1/Hubble CLI 1.19.4 기준입니다. 검증한 명령, 메트릭 정의와 제한은 [관측성 본문](../../../service-mesh/cilium-service-mesh/04-observability.md)을 참고하세요.

### 1. Hubble의 주요 구성 요소가 아닌 것은?

- **A.** Hubble Observer
- **B.** Hubble Relay
- **C.** Hubble Router
- **D.** Hubble UI

<details>
<summary>정답 및 설명</summary>

**정답: C. Hubble Router**

Hubble의 관련 구성 요소는 Observer, Relay, UI와 CLI입니다. Observer·메트릭 처리는 Cilium에 내장되고 Relay는 연결된 서버를 집계합니다. Hubble Router는 이 아키텍처의 구성 요소 이름이 아닙니다.

</details>

### 2. Hubble CLI에서 HTTP 트래픽만 필터링하여 관찰하는 명령은?

- **A.** hubble observe --type http
- **B.** hubble observe --protocol http
- **C.** hubble observe --filter http
- **D.** hubble observe --layer http

<details>
<summary>정답 및 설명</summary>

**정답: B. hubble observe --protocol http**

이미 존재하는 HTTP 관찰 결과를 필터링합니다. L7 검사를 활성화하거나 임의 TLS를 복호화하지는 않습니다. 지원되는 L7 정책·프록시 경로와 트래픽이 먼저 관찰을 제공해야 합니다.

</details>

### 3. Hubble 메트릭을 Prometheus에서 수집하기 위해 values.yaml에서 활성화해야 하는 설정은?

- **A.** hubble.prometheus.enabled: true
- **B.** hubble.metrics.enabled
- **C.** hubble.export.prometheus: true
- **D.** prometheus.hubble: true

<details>
<summary>정답 및 설명</summary>

**정답: B. hubble.metrics.enabled**

hubble.metrics.enabled로 dns·httpV2 등의 handler를 선택합니다. 실제 Prometheus 수집에는 정상 discovery·scraping, ServiceMonitor를 사용할 경우 Operator CRD·컨트롤러, 일치하는 selector가 필요합니다. ServiceMonitor 생성만으로 수집을 입증하지는 못합니다.

</details>

### 4. Golden Signals 모니터링의 네 가지 지표가 아닌 것은?

- **A.** Latency (지연 시간)
- **B.** Traffic (처리량)
- **C.** Availability (가용성)
- **D.** Saturation (포화도)

<details>
<summary>정답 및 설명</summary>

**정답: C. Availability (가용성)**

네 가지 이름은 지연 시간, 트래픽, 오류와 포화도입니다. 가용성에는 여전히 명시적인 SLI가 필요하며 일부 HTTP5xx 관찰만으로 완전히 추론할 수는 없습니다.

</details>

### 5. 추가 원인 분석을 위해 먼저 거부된 flow를 선택하는 명령은?

- **A.** hubble observe --denied
- **B.** hubble observe --verdict DROPPED
- **C.** hubble observe --blocked
- **D.** hubble observe --policy-denied

<details>
<summary>정답 및 설명</summary>

**정답: B. hubble observe --verdict DROPPED**

DROPPED에는 여러 원인이 포함됩니다. 보고된 정책 거부 drop에는 --drop-reason-desc POLICY_DENIED를 추가하고 L7·애플리케이션 실패는 별도로 확인하세요. FORWARDED는 데이터패스 관찰이지 업무 성공의 증거가 아닙니다.

</details>

### 6. HTTP P99 지연 시간을 측정하기 위한 PromQL 쿼리에서 사용하는 함수는?

- **A.** avg()
- **B.** histogram_quantile()
- **C.** rate()
- **D.** sum()

<details>
<summary>정답 및 설명</summary>

**정답: B. histogram_quantile()**

histogram_quantile은 histogram에서 백분위수를 추정합니다. 워크로드 집계에는 le와 선택한 cluster·namespace·workload 레이블을 유지해 호환되는 bucket rate를 먼저 합친 뒤 quantile을 계산합니다. 인스턴스별 백분위수 평균과 다릅니다.

</details>

### 7. Hubble UI에서 제공하는 주요 기능이 아닌 것은?

- **A.** 서비스 맵 (Service Map)
- **B.** 흐름 타임라인 (Flow Timeline)
- **C.** 자동 스케일링 (Auto Scaling)
- **D.** 네임스페이스 필터 (Namespace Filter)

<details>
<summary>정답 및 설명</summary>

**정답: C. 자동 스케일링 (Auto Scaling)**

UI는 관찰된 관계와 flow 상세 정보를 필터와 함께 표시하며 워크로드를 자동 확장하지 않습니다. 조용하거나 지원하지 않는 경로, 누락된 메타데이터 때문에 맵에 빈 부분이 생길 수 있습니다.

</details>

### 8. httpV2에서 관찰된 HTTP5xx 비율은 어떻게 계산해야 하나요?

- **A.** rate 없이 누적 오류·요청 카운터를 나눔
- **B.** 범위가 일치하는 5xx 응답 rate를 total rate로 나누고 누락·0을 처리
- **C.** 메트릭 시리즈 개수를 셈
- **D.** 자동 제공되는 hubble_http_error_rate gauge 조회

<details>
<summary>정답 및 설명</summary>

**정답: B. 범위가 일치하는 5xx 응답 rate를 total rate로 나누고 누락·0을 처리**

httpV2의 hubble_http_requests_total은 status를 포함하고 응답 이벤트로 갱신됩니다. 분자·분모의 집계와 관찰 경계를 일치시키세요. 5xx 분자가 없으면 존재하는 total에 대해서만 0을 채우고, 관찰이 없으면 없는 상태로 남기며, 0인 total은 비율에서 제외합니다.

</details>

### 9. Hubble에서 특정 서비스로 향하는 트래픽만 관찰하는 옵션은?

- **A.** --destination-service
- **B.** --to-service
- **C.** --target-service
- **D.** --svc

<details>
<summary>정답 및 설명</summary>

**정답: B. --to-service**

Service 필터는 namespace를 포함한 이름 prefix와 Service·ClusterIP 메타데이터를 사용합니다. --from-service가 해당 Service 뒤의 Pod가 보낸 호출을 일반적으로 선택하지는 않습니다. 호출자는 workload·Pod·label 필터로 선택하며 namespace를 생략하면 default입니다.

</details>

### 10. 계측된 BPF 맵의 사용 압력을 보고하는 문서화된 메트릭은?

- **A.** cilium_ct_usage
- **B.** cilium_bpf_map_pressure
- **C.** cilium_connections_total
- **D.** cilium_datapath_conntrack_active / cilium_datapath_conntrack_max

<details>
<summary>정답 및 설명</summary>

**정답: B. cilium_bpf_map_pressure**

cilium_bpf_map_pressure는 계측된 BPF 맵의 사용 압력을 보고하고 일부 맵에는 보고 임계값이 있습니다. 모든 CT 맵이 포함된다는 증거는 아닙니다. 문서화된 CT GC-entry 메트릭도 GC 시점의 값이며 기존의 존재하지 않는 active/max 쌍이 아닙니다.

</details>

### 11. Hubble의 출력을 JSON 형식으로 받으려면 어떤 옵션을 사용해야 하나요?

- **A.** --format json
- **B.** -o json
- **C.** --json
- **D.** --output-type json

<details>
<summary>정답 및 설명</summary>

**정답: B. -o json**

json과 jsonpb는 별칭입니다. Protobuf JSON은 latency_ns 같은 64비트 값을 문자열로 인코딩하므로 jq 숫자 비교 전에 변환해야 합니다. dict·compact·table 표시 형식도 지원합니다.

</details>

### 12. OpenTelemetry Collector로 Hubble flow 로그를 수집하는 지원 경로는?

- **A.** chart의 hubble.export.opentelemetry 활성화
- **B.** Hubble 파일 내보내기와 filelog receiver를 사용한 뒤 지원 log exporter로 전달
- **C.** 모든 flow를 자동으로 분산 trace로 변환
- **D.** 제거된 jaeger exporter로 flow 로그 수집

<details>
<summary>정답 및 설명</summary>

**정답: B. Hubble 파일 내보내기와 filelog receiver를 사용한 뒤 지원 log exporter로 전달**

Cilium 1.20.1은 flow 로그의 파일 내보내기를 문서화합니다. Filelog receiver로 해당 파일을 수집하고 OTLP/HTTP 등의 지원 exporter로 Loki에 로그를 보낼 수 있습니다. 메트릭·애플리케이션 trace는 별도 수집 경로를 사용하며 기존 Hubble opentelemetry values나 제거된 Collector jaeger/loki exporter로 대체되는 것은 아닙니다.

</details>
