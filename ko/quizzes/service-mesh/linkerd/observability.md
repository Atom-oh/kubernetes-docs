# Linkerd 관찰성 퀴즈

2026년 9월 11일 검토한 [관찰성 가이드](../../../service-mesh/linkerd/05-observability.md)를 기준으로 합니다.

### 1. Linkerd의 핵심 HTTP 서비스 지표 세 가지에 속하지 않는 것은?

- A. 성공률
- B. 요청률
- C. 지연 시간
- D. CPU 사용률

<details>
<summary>정답 및 설명</summary>

**정답: D**

**설명:** Proxy가 분류한 성공률, 요청률, 지연 시간이 세 가지입니다. CPU/용량은 추가 운영 정보이며 proxy나 다른 수집기가 process/resource 지표를 노출할 수 없다는 뜻은 아닙니다. Opaque TCP에서 HTTP 지표가 자동 생성되지는 않습니다.

</details>

### 2. 표준 linkerd viz stat 표의 열이 아닌 것은?

- A. SUCCESS
- B. RPS
- C. LATENCY_P99
- D. ERROR_TYPE

<details>
<summary>정답 및 설명</summary>

**정답: D**

**설명:** 선택한 버전은 MESHED, SUCCESS, RPS, percentile, TCP_CONN을 표시합니다. Wide는 proxy 버전이 아니라 transport byte rate를 추가합니다. 오류 조사에는 정책, Tap, 로그, 적합한 지표를 함께 사용합니다.

</details>

### 3. linkerd viz tap이 제공하는 것은?

- A. 전체 network packet capture
- B. 지원되는 요청의 실시간 관찰 stream
- C. Proxy 정책 자동 변경
- D. 인증서 갱신

<details>
<summary>정답 및 설명</summary>

**정답: B**

**설명:** Tap은 제한된 트래픽 관찰이며 전체 감사가 아닙니다. max-rps는 관찰률을 제한하고 전체 애플리케이션 트래픽을 조절하지 않습니다. 현재 --from/--show-headers flag는 없으므로 지원되는 selector를 사용하고 요청 metadata 접근을 보호합니다.

</details>

### 4. 이전 ServiceProfile의 route 이름 정의로 얻는 것은?

- A. Disk I/O 집계
- B. Route별 지표
- C. 자동으로 완성되는 distributed trace
- D. 모든 method의 필수 재시도

<details>
<summary>정답 및 설명</summary>

**정답: B**

**설명:** ServiceProfile은 route 지표와 viz routes 조회를 지원합니다. 호환성 인터페이스이며 현재 outbound HTTPRoute 신뢰성 설정보다 우선할 수 있습니다. 관찰 목적으로 추가하면서 위험한 재시도를 활성화하거나 기존 정책을 덮어쓰지 않도록 해야 합니다.

</details>

### 5. 가이드에서 기존 기본 Viz Prometheus에 local 접근하는 방법은?

- A. 인증 없는 NodePort 노출
- B. Public LoadBalancer 생성
- C. Loopback에 bind한 kubectl port-forward
- D. Public URL이 있다고 가정

<details>
<summary>정답 및 설명</summary>

**정답: C**

**설명:** 기존 Prometheus Service를 127.0.0.1로 전달합니다. Prometheus 설치나 공개 인증을 설정하는 명령이 아닙니다. 다른 workload에서 접근할 때도 network/Linkerd 인가가 필요합니다.

</details>

### 6. 애플리케이션 예제에서 사용하는 W3C trace context는?

- A. x-request-id와 Authorization
- B. x-b3-traceid와 x-b3-spanid
- C. traceparent와 tracestate
- D. x-linkerd-proxy와 Cookie

<details>
<summary>정답 및 설명</summary>

**정답: C**

**설명:** Linkerd는 W3C와 B3를 지원하고 둘 다 있으면 W3C를 우선합니다. x-request-id는 상관관계 ID이며 필수 trace 형식이 아닙니다. Header 전파만으로 application span이나 sampling/export가 생기지 않으므로 해당 작업에는 적합한 tracing library를 사용합니다.

</details>

### 7. linkerd viz top이 요약하는 것은?

- A. CPU 사용량 순 Pod
- B. Tap으로 관찰한 실시간 요청 path/route
- C. 모든 과거 오류 메시지
- D. 최신 container 로그

<details>
<summary>정답 및 설명</summary>

**정답: B**

**설명:** top은 sampling/rate 제한과 지원되는 조건을 적용한 live traffic을 요약합니다. hide-sources는 header가 아니라 source 열을 제어합니다. 보존된 Prometheus 지표나 전체 요청 감사를 대체하지 않습니다.

</details>

### 8. Proxy 진단 로그 수준을 바꾸는 annotation은?

- A. config.linkerd.io/log-level
- B. config.linkerd.io/proxy-log-level
- C. linkerd.io/proxy-log
- D. proxy.linkerd.io/log-level

<details>
<summary>정답 및 설명</summary>

**정답: B**

**설명:** proxy-log-level은 진단 filter, proxy-log-format은 진단 형식을 정합니다. HTTP access log는 config.linkerd.io/access-log:json 또는 apache로 별도 활성화합니다. 일부 Pod template은 patch/fragment이며 완전한 Deployment가 아닙니다.

</details>

### 9. 구간별 성공 비율을 올바르게 계산하는 방법은?

- A. Rate 없이 누적 success/total counter를 나눔
- B. 가상의 success_total counter 사용
- C. 같은 범위의 성공 response rate를 total rate로 나누고 success 누락과 양의 total을 처리
- D. 가상의 success_rate 지표 평균

<details>
<summary>정답 및 설명</summary>

**정답: C**

**설명:** 하나의 의도한 관찰 방향과 workload/cluster 범위를 사용합니다. 전체 실패여서 success series가 없어도 비율은 0이어야 하며 누락/무트래픽이 100% 성공이 되면 안 됩니다. Proxy HTTP 분류는 400도 성공으로 볼 수 있으므로 business SLI를 의도적으로 맞춥니다.

</details>

### 10. 현재 tracing 구성에서 Jaeger의 역할은?

- A. Kubernetes metrics discovery 대체
- B. Application access log만 집계
- C. 별도로 관리하는 backend로 distributed trace 수집/저장/조회
- D. 자동 트래픽 분할

<details>
<summary>정답 및 설명</summary>

**정답: C**

**설명:** Linkerd-Jaeger extension은 2.19에서 제거되었습니다. 현재는 OpenTelemetry 호환 collector와 예제 chart 경로에서의 mesh identity를 설정합니다. Backend UI만으로 application/proxy span의 수신이나 완전한 trace가 입증되지는 않습니다.

</details>

### 11. Viz를 container 로그 viewer로 가정하지 않고 kubectl logs나 로그 시스템으로 확인할 정보는?

- A. Workload topology
- B. Deployment 지표
- C. Pod container 로그
- D. ServiceProfile route 지표

<details>
<summary>정답 및 설명</summary>

**정답: C**

**설명:** Viz는 workload/traffic, topology, Tap 조회를 제공합니다. 진단/access log는 별도 데이터입니다. 이러한 조회를 수행해도 원인, 수정, 검증이 필요하며 문제가 자동 해결되지는 않습니다.

</details>

### 12. Browser에서 접근 가능한 기존 외부 Grafana에 Viz를 연결하는 설정은?

- A. grafana.external:true
- B. grafana.externalUrl:https://grafana.example.com/
- C. grafana.enabled:false
- D. monitoring:external

<details>
<summary>정답 및 설명</summary>

**정답: B**

**설명:** 현재 Viz는 Grafana를 설치하지 않습니다. externalUrl은 외부 링크이고 grafana.url은 추가 root/subpath 설정이 필요한 cluster 내부 reverse-proxy 방식입니다. 어느 쪽도 Grafana 생성, datasource 구성, Prometheus 접근 허용을 대신하지 않습니다.

</details>
