# Linkerd 트래픽 관리 퀴즈

2026년 9월 11일 검토한 [트래픽 관리 가이드](../../../service-mesh/linkerd/03-traffic-management.md)를 기준으로 합니다.

### 1. ServiceProfile에서 route별로 설정할 수 없는 것은?

- A. 타임아웃
- B. 재시도 가능 여부
- C. 로드 밸런서 알고리즘
- D. 경로 조건

<details>
<summary>정답 및 설명</summary>

**정답: C**

**설명:** ServiceProfile route는 timeout, isRetryable, method/path 조건을 지정할 수 있지만 로드 밸런싱 알고리즘을 선택하지 않습니다. 그렇다고 범용적인 전역 알고리즘 전환 스위치가 있다는 뜻도 아닙니다.

</details>

### 2. Linkerd의 HTTP 로드 밸런싱을 설명하는 것은?

- A. 엄격한 round robin
- B. 항상 connection 수가 가장 적은 endpoint 선택
- C. 지연 시간을 고려하는 EWMA 동작
- D. 지연 시간 정보 없이 항상 무작위 선택

<details>
<summary>정답 및 설명</summary>

**정답: C**

**설명:** EWMA는 적합하고 지연 시간이 낮은 후보를 선호하지만 모든 요청이 전체 endpoint 중 표시된 최저 점수를 선택한다고 보장하지 않습니다. HTTP는 요청 단위, TCP는 connection 단위로 분산합니다.

</details>

### 3. 이전 TrafficSplit 리소스를 정의하는 사양은?

- A. CNCF
- B. SMI (Service Mesh Interface)
- C. OpenAPI
- D. gRPC

<details>
<summary>정답 및 설명</summary>

**정답: B**

**설명:** TrafficSplit은 SMI 리소스입니다. Linkerd TrafficSplit/linkerd-smi는 사용 중단 대상이며 별도의 extension/CRD가 필요합니다. 유지되는 가이드는 새 구성에 지원되는 Gateway API HTTPRoute를 사용합니다. 이전 리소스를 적용하는 것만으로 extension이 설치되지는 않습니다.

</details>

### 4. ServiceProfile retryRatio:0.2가 재시도 예산에 제공하는 것은?

- A. 모든 요청 흐름의 정확히 20%를 반드시 재시도
- B. 실패한 요청 중 20%만 재시도 가능
- C. 원래 요청에 비례한 허용량이며 minRetriesPerSecond는 별도로 더해짐
- D. 20초마다 예산 초기화

<details>
<summary>정답 및 설명</summary>

**정답: C**

**설명:** minRetriesPerSecond가 별도 허용량을 더하므로 전체 재시도의 엄격한 20% 상한이 아닙니다. ttl은 lookback/보존 구간이며 주기적인 초기화가 아닙니다. 실제 재시도는 대상 조건, buffering, deadline에도 제한됩니다.

</details>

### 5. 다음 중 ServiceProfile에 필요한 애플리케이션 작업을 단독으로 추론할 수 없는 입력은?

- A. OpenAPI 사양
- B. Tap으로 관찰한 실제 트래픽
- C. Protobuf service 정의
- D. Kubernetes Service selector와 port 목록

<details>
<summary>정답 및 설명</summary>

**정답: D**

**설명:** CLI는 OpenAPI/protobuf 생성, Viz는 tap 기반 생성을 지원합니다. 짧은 Service 이름과 -n을 사용하며 tap 명령에도 위치 인수 Service가 필요합니다. 샘플 트래픽이 전체 API 목록은 아니므로 생성된 조건과 재시도 안전성을 검토합니다.

</details>

### 6. Backend 가중치에 대한 올바른 설명은?

- A. 합계가 반드시 100
- B. 합계가 반드시 1
- C. 유효한 음수 아닌 상대 가중치와 사용 가능한 양의 합계가 필요하며 90/10과 9/1은 같은 비율
- D. 음수 가중치와 합계 0도 항상 동작

<details>
<summary>정답 및 설명</summary>

**정답: C**

**설명:** 가중치는 선택한 리소스 schema와 backend 유효성을 따르는 상대값입니다. 합계가 100일 필요는 없고 짧은 구간의 정확한 요청 수를 보장하지 않습니다. 새 예제는 HTTPRoute이며 TrafficSplit은 이전 SMI 경로입니다.

</details>

### 7. HTTPRoute의 요청 match 필드가 아닌 것은?

- A. HTTP header
- B. HTTP path
- C. HTTP method
- D. Source IP

<details>
<summary>정답 및 설명</summary>

**정답: D**

**설명:** HTTPRoute는 header/path/method 조건을 지원합니다. Cookie header의 Exact match는 개별 cookie가 아니라 header 전체를 비교합니다. Caller가 지정한 cohort/debug header는 인가가 아닙니다. 주소 제한에는 적합한 network/security policy를 사용합니다.

</details>

### 8. 가이드의 custom Linkerd Flagger MetricTemplate이 사용하는 provider는?

- A. Kubernetes Metrics Server
- B. Prometheus
- C. 정의하지 않은 InfluxDB Service
- D. 필수 Datadog backend

<details>
<summary>정답 및 설명</summary>

**정답: B**

**설명:** 예제는 namespace/deployment/direction 범위를 명시하여 Linkerd Viz Prometheus에 질의합니다. Flagger는 다른 provider도 지원합니다. 예제는 gatewayapi:v1 router와 custom metric 이름을 사용하며 Flagger 1.45.0의 meshProvider:linkerd는 여전히 이전 SMI router를 선택합니다.

</details>

### 9. 일치하는 ServiceProfile route의 isRetryable:false가 의미하는 것은?

- A. 모든 일치 요청 실패
- B. 해당 route에서 ServiceProfile의 재시도 기능을 사용하지 않음
- C. 모든 timeout 정책 무시
- D. Route 비활성화

<details>
<summary>정답 및 설명</summary>

**정답: B**

**설명:** 요청 자체는 정상 전달될 수 있습니다. Client/SDK/다른 proxy의 재시도는 막지 않습니다. 현재 annotation 경로의 limit:0은 edge-26.9.1에서 신뢰할 수 있는 비활성화 스위치가 아닙니다. Service 기본값에 retry를 두지 않고 의도한 읽기 route에만 활성화합니다.

</details>

### 10. Linkerd HTTP circuit breaking을 설정하는 방식은?

- A. 자동 설치되는 CircuitBreaker CRD
- B. Service의 failure-accrual annotation을 명시적으로 활성화
- C. 항상 기본 적용되는 connection 실패 5회 규칙
- D. 주기적인 synthetic readiness probe 루프

<details>
<summary>정답 및 설명</summary>

**정답: B**

**설명:** Failure accrual은 기본 비활성이며 해당 Service의 ServiceProfile과 함께 사용할 수 없습니다. Consecutive 정책의 기본값은 지원되는 응답 실패 7회입니다. 복구 probation은 backoff 후 실제 애플리케이션 요청을 사용하며 주기적인 synthetic probe가 아닙니다.

</details>

### 11. Multicluster mirror Service로 표현된 export 서비스에 client가 명시적으로 요청하는 방법은?

- A. 가상의 TrafficMirror CRD 적용
- B. 필요한 연결과 정책을 갖춘 뒤 mirror Service DNS 호출
- C. 모든 local 요청이 자동 복제됨
- D. Mirror Service는 호출할 수 없음

<details>
<summary>정답 및 설명</summary>

**정답: B**

**설명:** Multicluster service mirroring은 원격 서비스의 discovery/routing을 제공합니다. 해당 DNS 호출은 요청을 원격으로 보내며 shadow test용 복제를 자동 수행하지 않습니다. Request mirroring은 별도 기능으로 선택한 구현과 버전의 지원 여부를 확인해야 합니다.

</details>

### 12. ServiceProfile route에서 timeout을 생략하면?

- A. 자동으로 5초 profile timeout 적용
- B. 해당 ServiceProfile 필드에 의한 timeout이 없음
- C. 즉시 실패
- D. 다른 모든 계층의 timeout도 제거

<details>
<summary>정답 및 설명</summary>

**정답: B**

**설명:** 해당 필드는 route timeout을 추가하지 않지만 애플리케이션, client, transport, proxy, load balancer의 제한은 남을 수 있습니다. 전체 시간이 무제한이라는 보장이 아닙니다. Streaming deadline과 취소 동작은 애플리케이션에 맞게 설계합니다.

</details>
