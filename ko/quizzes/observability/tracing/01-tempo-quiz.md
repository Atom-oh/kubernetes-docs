# Grafana Tempo 퀴즈

Grafana Tempo에 대한 이해도를 테스트하는 퀴즈입니다.

---

1. Grafana Tempo의 가장 큰 특징은 무엇인가요?
   - A) 모든 데이터를 인덱싱하여 빠른 검색 제공
   - B) TraceID 기반 저장으로 인덱싱 비용 제거
   - C) 실시간 스트리밍 처리
   - D) 자동 이상 탐지 기능

<details>
<summary>정답 보기</summary>

**정답: B) TraceID 기반 저장으로 인덱싱 비용 제거**

**설명:**
Tempo는 추적 데이터를 인덱싱하지 않고 TraceID만으로 데이터를 저장하고 검색합니다. 이로 인해 대규모 추적 데이터를 저비용으로 저장할 수 있습니다. 다른 추적 시스템들은 다양한 필드를 인덱싱하여 검색 성능을 높이지만, 이는 스토리지 비용 증가로 이어집니다.

</details>

---

2. Tempo 아키텍처에서 추적 데이터를 수신하고 유효성을 검사하는 컴포넌트는?
   - A) Ingester
   - B) Querier
   - C) Distributor
   - D) Compactor

<details>
<summary>정답 보기</summary>

**정답: C) Distributor**

**설명:**
Distributor는 다양한 형식(Jaeger, Zipkin, OTLP 등)의 추적 데이터를 수신하고 유효성을 검사합니다. 검증된 데이터는 해시 기반으로 적절한 Ingester로 분배됩니다. Ingester는 데이터를 버퍼링하고 저장하며, Querier는 검색을 담당합니다.

</details>

---

3. TraceQL에서 오류 상태의 스팬만 조회하는 올바른 쿼리는?
   - A) `{ error = true }`
   - B) `{ status = error }`
   - C) `{ span.error = 1 }`
   - D) `{ state = "ERROR" }`

<details>
<summary>정답 보기</summary>

**정답: B) { status = error }**

**설명:**
TraceQL에서 오류 스팬을 필터링할 때는 `{ status = error }` 구문을 사용합니다. status 필드는 ok, error, unset 값을 가질 수 있으며, 이는 OpenTelemetry의 SpanStatus와 매핑됩니다.

</details>

---

4. Tempo에서 S3를 백엔드 스토리지로 사용할 때 권장되는 AWS 인증 방식은?
   - A) 환경 변수에 Access Key 저장
   - B) Secret에 자격 증명 저장
   - C) IRSA (IAM Roles for Service Accounts)
   - D) EC2 Instance Profile

<details>
<summary>정답 보기</summary>

**정답: C) IRSA (IAM Roles for Service Accounts)**

**설명:**
EKS 환경에서는 IRSA를 사용하는 것이 권장됩니다. IRSA는 Kubernetes ServiceAccount에 IAM 역할을 연결하여 Pod 수준에서 세분화된 권한 관리가 가능합니다. 정적 자격 증명을 저장하는 것보다 보안적으로 우수하며, 자격 증명 로테이션이 자동으로 처리됩니다.

</details>

---

5. Tempo의 Metrics Generator가 생성하는 메트릭 유형이 아닌 것은?
   - A) Service Graph 메트릭
   - B) Span 메트릭
   - C) Log 메트릭
   - D) RED 메트릭 (Rate, Error, Duration)

<details>
<summary>정답 보기</summary>

**정답: C) Log 메트릭**

**설명:**
Tempo의 Metrics Generator는 추적 데이터에서 Service Graph 메트릭과 Span 메트릭(RED 메트릭 포함)을 생성합니다. 이 메트릭들은 Prometheus로 전송되어 서비스 맵 시각화와 성능 모니터링에 사용됩니다. Log 메트릭은 Loki에서 생성되며 Tempo의 범위가 아닙니다.

</details>

---

6. Tempo Distributed 모드에서 데이터 내구성을 위해 여러 Ingester에 복제본을 유지하는 기능의 이름은?
   - A) Sharding
   - B) Replication Factor
   - C) Partitioning
   - D) Mirroring

<details>
<summary>정답 보기</summary>

**정답: B) Replication Factor**

**설명:**
Replication Factor는 각 추적 데이터를 몇 개의 Ingester에 복제할지 결정합니다. 예를 들어 replication_factor=3이면 각 추적이 3개의 Ingester에 저장되어 하나의 Ingester가 실패해도 데이터 손실이 없습니다. 이는 Tempo의 고가용성 구성에서 중요한 설정입니다.

</details>

---

7. Grafana에서 Tempo와 Loki를 연동하여 Trace-to-Log 상관분석을 구현할 때 필요한 설정은?
   - A) 동일한 네임스페이스에 배포
   - B) derivedFields 설정으로 TraceID 추출
   - C) 동일한 S3 버킷 사용
   - D) 동일한 레이블 사용

<details>
<summary>정답 보기</summary>

**정답: B) derivedFields 설정으로 TraceID 추출**

**설명:**
Loki 데이터 소스 설정에서 derivedFields를 구성하여 로그에서 TraceID를 추출하고 Tempo로 링크를 생성합니다. 정규식 패턴으로 TraceID를 매칭하고, 해당 값을 Tempo 데이터 소스로 연결하면 로그에서 바로 관련 추적을 조회할 수 있습니다.

</details>

---

8. Tempo에서 Compactor의 역할로 올바른 것은?
   - A) 실시간 쿼리 처리
   - B) 추적 데이터 수신 및 분배
   - C) 저장된 블록 압축 및 보존 정책 적용
   - D) 메모리 버퍼 관리

<details>
<summary>정답 보기</summary>

**정답: C) 저장된 블록 압축 및 보존 정책 적용**

**설명:**
Compactor는 Object Storage에 저장된 추적 블록들을 압축하고 최적화합니다. 또한 block_retention 설정에 따라 오래된 데이터를 삭제하는 보존 정책을 적용합니다. Compactor는 일반적으로 단일 인스턴스로 실행되며, 클러스터당 하나만 활성화됩니다.

</details>

---

9. TraceQL에서 서비스 A에서 서비스 B로의 호출 패턴을 찾는 쿼리는?
   - A) `{ resource.service.name = "A" } AND { resource.service.name = "B" }`
   - B) `{ resource.service.name = "A" } >> { resource.service.name = "B" }`
   - C) `{ resource.service.name = "A" } -> { resource.service.name = "B" }`
   - D) `{ resource.service.name = "A" } | { resource.service.name = "B" }`

<details>
<summary>정답 보기</summary>

**정답: B) { resource.service.name = "A" } >> { resource.service.name = "B" }**

**설명:**
TraceQL에서 `>>` 연산자는 구조적 매칭을 수행하여 첫 번째 조건의 스팬이 두 번째 조건의 스팬의 조상(ancestor)인 경우를 찾습니다. 이를 통해 서비스 간 호출 패턴을 분석할 수 있습니다. `>` 연산자는 직접적인 부모-자식 관계만 매칭합니다.

</details>

---

10. Tempo 성능 최적화를 위한 권장 설정이 아닌 것은?
    - A) max_block_duration을 30분으로 설정
    - B) Memcached를 캐시로 사용
    - C) 모든 속성을 인덱싱
    - D) Query Frontend에서 쿼리 샤딩 활성화

<details>
<summary>정답 보기</summary>

**정답: C) 모든 속성을 인덱싱**

**설명:**
Tempo의 핵심 설계 원칙은 인덱싱을 최소화하여 비용을 절감하는 것입니다. 모든 속성을 인덱싱하면 Tempo의 장점이 사라지고 스토리지 비용이 크게 증가합니다. 대신 max_block_duration 최적화, 캐시 사용, 쿼리 샤딩 등으로 성능을 향상시킵니다.

</details>

---
