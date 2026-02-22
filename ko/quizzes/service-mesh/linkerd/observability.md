# Linkerd 관찰성 퀴즈

이 퀴즈는 Linkerd 관찰성 기능에 대한 이해를 테스트합니다.

## 퀴즈 문제

### 1. Linkerd가 자동으로 수집하는 골든 메트릭이 아닌 것은?

A. 성공률
B. 요청률 (RPS)
C. 지연 시간
D. CPU 사용률

<details>
<summary>정답 및 설명</summary>

**정답: D. CPU 사용률**

**설명:**
Linkerd는 세 가지 골든 메트릭을 자동 수집합니다: 성공률, 요청률(RPS), 지연 시간(p50, p95, p99). CPU 사용률은 Kubernetes 메트릭으로 별도 수집해야 합니다.

</details>

### 2. `linkerd viz stat` 명령어의 출력에 포함되지 않는 것은?

A. SUCCESS (성공률)
B. RPS (요청률)
C. LATENCY_P99
D. ERROR_TYPE (오류 유형)

<details>
<summary>정답 및 설명</summary>

**정답: D. ERROR_TYPE (오류 유형)**

**설명:**
`linkerd viz stat`은 MESHED, SUCCESS, RPS, LATENCY_P50/P95/P99를 보여줍니다. 오류 유형은 `linkerd viz tap`이나 로그에서 확인해야 합니다.

</details>

### 3. `linkerd viz tap` 명령어의 용도는?

A. 네트워크 패킷 캡처
B. 실시간 요청 스트림 확인
C. 프록시 설정 변경
D. 인증서 갱신

<details>
<summary>정답 및 설명</summary>

**정답: B. 실시간 요청 스트림 확인**

**설명:**
`linkerd viz tap`은 실시간으로 요청을 스트리밍하여 보여줍니다. 요청 메서드, 경로, 상태 코드, 지연 시간, mTLS 상태 등을 확인할 수 있습니다.

</details>

### 4. ServiceProfile을 정의하면 추가로 얻을 수 있는 메트릭은?

A. Pod 리소스 사용량
B. 라우트별 메트릭
C. 네트워크 대역폭
D. 디스크 I/O

<details>
<summary>정답 및 설명</summary>

**정답: B. 라우트별 메트릭**

**설명:**
ServiceProfile을 정의하면 라우트별(예: GET /api/users, POST /api/orders) 성공률, 요청률, 지연 시간 메트릭을 수집할 수 있습니다. `linkerd viz routes` 명령으로 확인합니다.

</details>

### 5. Viz 확장의 Prometheus에 접근하는 기본 방법은?

A. NodePort 서비스
B. LoadBalancer 서비스
C. kubectl port-forward
D. 공개 URL

<details>
<summary>정답 및 설명</summary>

**정답: C. kubectl port-forward**

**설명:**
Viz의 Prometheus는 ClusterIP 서비스로 배포됩니다. `kubectl port-forward -n linkerd-viz svc/prometheus 9090:9090`으로 접근합니다. 보안상 외부 노출은 권장되지 않습니다.

</details>

### 6. 분산 추적을 위해 애플리케이션이 전파해야 하는 헤더가 아닌 것은?

A. x-b3-traceid
B. x-request-id
C. x-linkerd-proxy
D. x-b3-spanid

<details>
<summary>정답 및 설명</summary>

**정답: C. x-linkerd-proxy**

**설명:**
분산 추적에 필요한 헤더: x-request-id, x-b3-traceid, x-b3-spanid, x-b3-parentspanid, x-b3-sampled, b3 등. x-linkerd-proxy는 존재하지 않는 헤더입니다.

</details>

### 7. `linkerd viz top` 명령어가 보여주는 것은?

A. 가장 많은 리소스를 사용하는 Pod
B. 가장 활발한 요청 경로
C. 상위 오류 메시지
D. 최신 로그 항목

<details>
<summary>정답 및 설명</summary>

**정답: B. 가장 활발한 요청 경로**

**설명:**
`linkerd viz top`은 실시간으로 가장 활발한 요청 경로를 보여줍니다. Source, Destination, Method, Path, Count, Latency, Success Rate 등을 표시합니다.

</details>

### 8. 프록시 로그 레벨을 설정하는 어노테이션은?

A. config.linkerd.io/log-level
B. config.linkerd.io/proxy-log-level
C. linkerd.io/proxy-log
D. proxy.linkerd.io/log-level

<details>
<summary>정답 및 설명</summary>

**정답: B. config.linkerd.io/proxy-log-level**

**설명:**
`config.linkerd.io/proxy-log-level` 어노테이션으로 프록시 로그 레벨을 설정합니다. 예: "warn,linkerd=info,linkerd_proxy=debug"

</details>

### 9. Prometheus에서 Linkerd 성공률을 계산하는 올바른 쿼리는?

A. `sum(response_total{classification="success"}) / sum(response_total)`
B. `rate(success_total[5m]) / rate(request_total[5m])`
C. `sum(rate(response_total{classification="success"}[5m])) / sum(rate(response_total[5m]))`
D. `avg(success_rate)`

<details>
<summary>정답 및 설명</summary>

**정답: C. `sum(rate(response_total{classification="success"}[5m])) / sum(rate(response_total[5m]))`**

**설명:**
성공률은 성공 응답 rate를 전체 응답 rate로 나눕니다. rate() 함수로 시간 범위 내 초당 비율을 계산하고 sum()으로 집계합니다.

</details>

### 10. Jaeger 확장의 주요 기능은?

A. 메트릭 수집
B. 로그 집계
C. 분산 추적
D. 트래픽 분할

<details>
<summary>정답 및 설명</summary>

**정답: C. 분산 추적**

**설명:**
Jaeger 확장은 분산 추적을 제공합니다. 여러 서비스를 거치는 요청의 전체 경로를 시각화하고 각 단계의 지연 시간을 분석할 수 있습니다.

</details>

### 11. linkerd viz dashboard 명령어가 제공하지 않는 뷰는?

A. Topology (토폴로지)
B. Deployments
C. Pod Logs (Pod 로그)
D. Routes

<details>
<summary>정답 및 설명</summary>

**정답: C. Pod Logs (Pod 로그)**

**설명:**
Viz 대시보드는 Namespace, Deployments, Pods, TCP, Routes, Topology, Tap 뷰를 제공합니다. Pod 로그는 kubectl logs나 별도 로그 시스템에서 확인해야 합니다.

</details>

### 12. 외부 Grafana와 연동 시 Viz 설치 옵션은?

A. `--set grafana.external=true`
B. `--set grafana.enabled=false`
C. `--set grafana.url=external`
D. `--set monitoring=external`

<details>
<summary>정답 및 설명</summary>

**정답: B. `--set grafana.enabled=false`**

**설명:**
외부 Grafana를 사용할 때는 Viz의 내장 Grafana를 비활성화합니다. `helm install linkerd-viz linkerd/linkerd-viz --set grafana.enabled=false` 또는 values 파일에서 설정합니다.

</details>
