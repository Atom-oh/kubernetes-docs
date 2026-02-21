# Grafana Loki 퀴즈

Grafana Loki에 대한 이해도를 테스트하는 퀴즈입니다.

---

1. Loki가 Elasticsearch보다 비용 효율적인 주된 이유는?

   - A) 더 빠른 쿼리 성능
   - B) 로그 콘텐츠 대신 레이블만 인덱싱
   - C) 더 나은 압축 알고리즘 사용
   - D) 클라우드 네이티브 설계

<details>
<summary>정답 보기</summary>

**정답: B) 로그 콘텐츠 대신 레이블만 인덱싱**

**설명:**
Loki는 로그 콘텐츠를 인덱싱하지 않고 메타데이터(레이블)만 인덱싱합니다. 이로 인해 인덱스 크기가 크게 줄어들고, 저렴한 객체 스토리지(S3 등)를 활용할 수 있어 Elasticsearch 대비 10배 이상 저렴한 운영이 가능합니다.

</details>

---

2. Loki 아키텍처에서 로그 데이터를 메모리에 버퍼링하고 스토리지에 저장하는 컴포넌트는?

   - A) Distributor
   - B) Querier
   - C) Ingester
   - D) Compactor

<details>
<summary>정답 보기</summary>

**정답: C) Ingester**

**설명:**
Ingester는 Distributor로부터 받은 로그 데이터를 메모리에 버퍼링(청크 생성)하고, WAL을 관리하며, 스토리지로 청크를 플러시합니다. 또한 실시간 쿼리를 서빙하는 역할도 합니다.

</details>

---

3. 프로덕션 EKS 환경에서 권장되는 Loki 배포 모드는?

   - A) Monolithic 모드
   - B) Simple Scalable 모드
   - C) Microservices 모드
   - D) Standalone 모드

<details>
<summary>정답 보기</summary>

**정답: B) Simple Scalable 모드**

**설명:**
Simple Scalable 모드는 읽기/쓰기 경로를 분리하여 확장성을 제공하면서도 Microservices 모드보다 운영이 간단합니다. 일일 로그량 100GB ~ 10TB 규모의 대부분의 프로덕션 EKS 클러스터에 적합합니다.

</details>

---

4. LogQL에서 에러 로그의 초당 발생 비율을 계산하는 올바른 쿼리는?

   - A) `count({app="nginx"} |= "error")`
   - B) `rate({app="nginx"} |= "error" [5m])`
   - C) `sum({app="nginx"} |= "error")`
   - D) `avg({app="nginx"} |= "error" [5m])`

<details>
<summary>정답 보기</summary>

**정답: B) `rate({app="nginx"} |= "error" [5m])`**

**설명:**
`rate()` 함수는 지정된 시간 범위 동안의 초당 로그 라인 수를 계산합니다. `[5m]`은 5분 범위를 의미합니다. `count()`는 메트릭 쿼리에서 사용되지 않고, `sum()`과 `avg()`는 단독으로 이렇게 사용되지 않습니다.

</details>

---

5. Loki 라벨 설계에서 피해야 할 높은 카디널리티 라벨의 예시는?

   - A) namespace
   - B) app
   - C) pod_name
   - D) environment

<details>
<summary>정답 보기</summary>

**정답: C) pod_name**

**설명:**
pod_name은 수천 개의 고유 값을 가질 수 있어 높은 카디널리티 라벨입니다. 높은 카디널리티 라벨은 스트림 수를 급격히 증가시켜 인덱스 크기와 메모리 사용량을 늘립니다. namespace, app, environment는 일반적으로 수십 개 이하의 값을 가지므로 적절합니다.

</details>

---

6. EKS에서 Loki S3 백엔드 접근에 권장되는 인증 방식은?

   - A) Access Key ID/Secret Access Key
   - B) IAM Roles for Service Accounts (IRSA)
   - C) EC2 Instance Profile
   - D) AWS STS AssumeRole

<details>
<summary>정답 보기</summary>

**정답: B) IAM Roles for Service Accounts (IRSA)**

**설명:**
IRSA는 Kubernetes 서비스 계정에 IAM 역할을 연결하는 방식으로, Access Key를 코드나 설정에 저장하지 않아도 됩니다. 보안적으로 가장 권장되는 방식이며, EKS 환경에서 네이티브로 지원됩니다.

</details>

---

7. LogQL에서 JSON 로그를 파싱한 후 특정 필드 값으로 필터링하는 올바른 문법은?

   - A) `{app="api"} | json | level="error"`
   - B) `{app="api"} | json | filter level="error"`
   - C) `{app="api"} | json | where level="error"`
   - D) `{app="api"} | json | select level="error"`

<details>
<summary>정답 보기</summary>

**정답: A) `{app="api"} | json | level="error"`**

**설명:**
LogQL에서 JSON 파싱 후 레이블 필터는 `| 필드명="값"` 형식으로 작성합니다. `filter`, `where`, `select`는 LogQL 문법이 아닙니다.

</details>

---

8. Loki Compactor의 주요 역할이 아닌 것은?

   - A) 작은 청크들을 큰 청크로 병합
   - B) 보존 정책 적용 (데이터 삭제)
   - C) 클라이언트로부터 로그 수신
   - D) 인덱스 최적화

<details>
<summary>정답 보기</summary>

**정답: C) 클라이언트로부터 로그 수신**

**설명:**
클라이언트로부터 로그를 수신하는 것은 Distributor의 역할입니다. Compactor는 백그라운드에서 저장된 데이터를 최적화하고, 보존 정책에 따라 오래된 데이터를 삭제하는 역할을 합니다.

</details>

---

9. Loki에서 "rate limit exceeded" 에러 발생 시 조정해야 할 설정은?

   - A) max_streams_per_user
   - B) ingestion_rate_mb, ingestion_burst_size_mb
   - C) max_query_parallelism
   - D) chunk_idle_period

<details>
<summary>정답 보기</summary>

**정답: B) ingestion_rate_mb, ingestion_burst_size_mb**

**설명:**
"rate limit exceeded" 에러는 로그 수집 속도가 제한을 초과했을 때 발생합니다. `ingestion_rate_mb`(초당 최대 수집량)와 `ingestion_burst_size_mb`(버스트 허용량)를 증가시켜 해결할 수 있습니다.

</details>

---

10. Loki 성능 튜닝에서 Ingester의 `chunk_idle_period` 설정의 의미는?

    - A) 청크가 생성된 후 삭제까지의 시간
    - B) 유휴 스트림이 플러시되기까지 대기하는 시간
    - C) 쿼리 타임아웃 시간
    - D) 로그 보존 기간

<details>
<summary>정답 보기</summary>

**정답: B) 유휴 스트림이 플러시되기까지 대기하는 시간**

**설명:**
`chunk_idle_period`는 스트림에 새 로그가 들어오지 않을 때 해당 청크를 스토리지로 플러시하기 전까지 대기하는 시간입니다. 값을 줄이면 메모리 사용량이 감소하지만 작은 청크가 많이 생성될 수 있습니다.

</details>
