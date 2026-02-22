# Linkerd 트래픽 관리 퀴즈

이 퀴즈는 Linkerd 트래픽 관리에 대한 이해를 테스트합니다.

## 퀴즈 문제

### 1. ServiceProfile에서 라우트별로 설정할 수 없는 것은?

A. 타임아웃
B. 재시도 가능 여부
C. 로드밸런서 알고리즘
D. 경로 조건

<details>
<summary>정답 및 설명</summary>

**정답: C. 로드밸런서 알고리즘**

**설명:**
ServiceProfile은 라우트별로 타임아웃, 재시도 가능 여부(isRetryable), 경로 조건(method, pathRegex)을 설정할 수 있습니다. 로드밸런서 알고리즘은 Linkerd 전역 설정이며 EWMA가 사용됩니다.

</details>

### 2. Linkerd가 사용하는 로드 밸런싱 알고리즘은?

A. Round Robin
B. Least Connections
C. EWMA (Exponentially Weighted Moving Average)
D. Random

<details>
<summary>정답 및 설명</summary>

**정답: C. EWMA (Exponentially Weighted Moving Average)**

**설명:**
Linkerd는 EWMA 알고리즘을 사용하여 응답 지연 시간이 빠른 엔드포인트를 선호합니다. 실시간으로 엔드포인트 상태에 적응하고 느린 엔드포인트로의 트래픽을 자동으로 감소시킵니다.

</details>

### 3. TrafficSplit이 따르는 표준 사양은?

A. CNCF
B. SMI (Service Mesh Interface)
C. OpenAPI
D. gRPC

<details>
<summary>정답 및 설명</summary>

**정답: B. SMI (Service Mesh Interface)**

**설명:**
TrafficSplit은 SMI(Service Mesh Interface) 표준을 따르는 CRD입니다. SMI는 서비스 메시의 공통 인터페이스를 정의하여 다양한 메시 구현 간 호환성을 제공합니다.

</details>

### 4. 재시도 예산(retryBudget)의 retryRatio가 0.2일 때 의미하는 것은?

A. 모든 요청의 20%만 재시도
B. 실패한 요청의 20%만 재시도
C. 원래 요청 대비 최대 20% 추가 재시도 허용
D. 20초마다 재시도 예산 리셋

<details>
<summary>정답 및 설명</summary>

**정답: C. 원래 요청 대비 최대 20% 추가 재시도 허용**

**설명:**
retryRatio 0.2는 원래 요청 수 대비 최대 20%의 추가 재시도를 허용합니다. 예: 100개 요청 중 최대 20개의 추가 재시도 가능. 이는 재시도로 인한 과부하를 방지합니다.

</details>

### 5. ServiceProfile을 자동 생성하는 방법이 아닌 것은?

A. OpenAPI/Swagger 스펙에서 생성
B. 실제 트래픽 탭에서 생성
C. Protobuf 정의에서 생성
D. Kubernetes Service에서 자동 생성

<details>
<summary>정답 및 설명</summary>

**정답: D. Kubernetes Service에서 자동 생성**

**설명:**
ServiceProfile은 `linkerd profile --open-api`, `linkerd viz profile --tap`, `linkerd profile --proto` 명령으로 생성할 수 있습니다. Kubernetes Service에서 자동 생성되지 않으며 명시적으로 정의해야 합니다.

</details>

### 6. 카나리 배포 시 TrafficSplit의 backends 가중치 합계는?

A. 반드시 100이어야 함
B. 반드시 1이어야 함
C. 어떤 값이든 상관없음 (비율로 계산)
D. 반드시 1000이어야 함

<details>
<summary>정답 및 설명</summary>

**정답: C. 어떤 값이든 상관없음 (비율로 계산)**

**설명:**
TrafficSplit의 가중치는 상대적 비율로 계산됩니다. weight: 90과 weight: 10은 weight: 9와 weight: 1과 동일합니다. 합계가 100일 필요는 없습니다.

</details>

### 7. HTTPRoute(Gateway API)에서 지원하지 않는 라우팅 조건은?

A. 헤더 기반 라우팅
B. 경로 기반 라우팅
C. 쿠키 기반 라우팅
D. 소스 IP 기반 라우팅

<details>
<summary>정답 및 설명</summary>

**정답: D. 소스 IP 기반 라우팅**

**설명:**
HTTPRoute는 헤더, 경로, 메서드, 쿠키(헤더를 통해) 기반 라우팅을 지원합니다. 소스 IP 기반 라우팅은 L7 라우팅 범위를 벗어나며 NetworkPolicy나 다른 메커니즘으로 처리됩니다.

</details>

### 8. Flagger와 Linkerd 통합 시 사용되는 메트릭 서버는?

A. Metrics Server
B. Prometheus
C. InfluxDB
D. Datadog

<details>
<summary>정답 및 설명</summary>

**정답: B. Prometheus**

**설명:**
Flagger는 Linkerd Viz의 Prometheus에서 메트릭(성공률, 지연 시간 등)을 가져와 카나리 분석을 수행합니다. Flagger 설치 시 `--set metricsServer=http://prometheus.linkerd-viz:9090`으로 연결합니다.

</details>

### 9. ServiceProfile의 isRetryable이 false인 라우트에서 발생하는 것은?

A. 모든 요청이 실패함
B. 재시도가 발생하지 않음
C. 타임아웃이 무시됨
D. 라우트가 비활성화됨

<details>
<summary>정답 및 설명</summary>

**정답: B. 재시도가 발생하지 않음**

**설명:**
isRetryable: false는 해당 라우트의 요청이 실패해도 재시도하지 않음을 의미합니다. POST 요청처럼 멱등성이 없는 작업에 적합합니다. 요청 자체는 정상적으로 처리됩니다.

</details>

### 10. 서킷 브레이커(Circuit Breaker) 패턴이 Linkerd에서 구현되는 방식은?

A. Circuit Breaker CRD
B. Failure Accrual
C. Rate Limiter
D. Timeout Policy

<details>
<summary>정답 및 설명</summary>

**정답: B. Failure Accrual**

**설명:**
Linkerd는 failure accrual을 통해 서킷 브레이커 패턴을 구현합니다. 연속 실패 시 해당 엔드포인트를 일시적으로 제외하고, 지수 백오프로 재시도하며, 성공 시 정상 상태로 복귀합니다.

</details>

### 11. 트래픽 분할 없이 미러 서비스로 트래픽을 보내는 방법은?

A. TrafficMirror CRD 사용
B. 직접 미러 서비스 DNS 호출
C. 자동으로 모든 트래픽이 미러링됨
D. Linkerd는 트래픽 미러링을 지원하지 않음

<details>
<summary>정답 및 설명</summary>

**정답: B. 직접 미러 서비스 DNS 호출**

**설명:**
Linkerd 자체는 Istio의 트래픽 미러링 같은 기능이 없습니다. 다중 클러스터의 미러 서비스(예: web-west)는 직접 DNS로 호출하거나 TrafficSplit으로 가중치를 설정해야 합니다.

</details>

### 12. ServiceProfile 타임아웃이 설정되지 않은 라우트의 동작은?

A. 기본 5초 타임아웃 적용
B. 타임아웃 없음 (무제한)
C. 요청이 즉시 실패
D. 전역 타임아웃 적용

<details>
<summary>정답 및 설명</summary>

**정답: B. 타임아웃 없음 (무제한)**

**설명:**
ServiceProfile에서 timeout이 지정되지 않은 라우트는 타임아웃 없이 무제한으로 대기합니다. 스트리밍이나 장시간 작업에 적합하지만, 일반적으로 타임아웃을 명시적으로 설정하는 것이 권장됩니다.

</details>
