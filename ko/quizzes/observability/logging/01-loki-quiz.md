# Grafana Loki 퀴즈

> **마지막 업데이트**: 2026년 9월 13일

[가이드](../../../observability/logging/01-loki.md)의 Loki3.7.7/chart18.12.1 예제를 기준으로 합니다.

---

1. TSDB·청크 모델에서 Loki가 주로 인덱싱하는 것은?

   - A) 모든 로그 라인의 모든 단어
   - B) 스트림 레이블
   - C) Request ID만
   - D) 타임스탬프만

<details>
<summary>정답 보기</summary>

**정답: B**

레이블로 스캔할 스트림을 좁힙니다. 고정10배 비용 우위나 파싱·청크 조회 비용 제거를 입증하지는 않습니다.

</details>

---

2. 로그 스트림을 버퍼링하고 활성화된 WAL을 기록하며 청크를 플러시하는 컴포넌트는?

   - A) Distributor
   - B) Query frontend
   - C) Ingester
   - D) Index gateway

<details>
<summary>정답 보기</summary>

**정답: C**

Ingester는 최근 데이터 조회도 제공합니다. WAL에는 영속 저장소가 필요하며 그 자체로 무손실·HA를 보장하지 않습니다.

</details>

---

3. 이 장에서 확인한 현재 배포 가이드와 일치하는 설명은?

   - A) SSD는 모든 운영 EKS의 영구 기본값이다
   - B) Pod3개면3AZ장애내성이 보장된다
   - C) SingleBinary만 chart18.12.1의 모드 이름이다
   - D) SSD는 폐기 예정이며 운영 확장·HA 가이드는 명시적 운영 계획과 Distributed를 권장한다

<details>
<summary>정답 보기</summary>

**정답: D**

SSD는 Loki4.0에서 제거될 예정입니다. 용량·가용성은 고정GB/일 표가 아니라 워크로드·저장소·토폴로지·장애 처리 검증에 달려 있습니다.

</details>

---

4. 최근5분의 일치하는 에러 로그 라인을 초당 속도로 계산하는 쿼리는?

   - A) `rate({app="nginx"} |= "error" [5m])`
   - B) `count({app="nginx"} |= "error")`
   - C) `sum({app="nginx"} |= "error")`
   - D) `increase(count_over_time({app="nginx"}[5m]))`

<details>
<summary>정답 보기</summary>

**정답: A**

이는 스트림별 로그 라인 속도이며 자동으로 HTTP 요청 에러 비율이 되지 않습니다. LogQL count 벡터 집계는 존재하지만 B는 필요한 메트릭 벡터 입력을 제공하지 않습니다.

</details>

---

5. 조사에 고유 request ID가 필요할 때 더 적절한 출발점은?

   - A) 모든 request ID를 인덱싱
   - B) 필요한 ID를 접근·개인정보 통제 아래 로그 본문 또는 structured metadata에 보관
   - C) Cluster·namespace 레이블을 모두 제거
   - D) 총스트림 수는 항상 레이블 cardinality의 곱이라고 가정

<details>
<summary>정답 보기</summary>

**정답: B**

높은 cardinality의 인덱스 값은 많은 스트림을 만들 수 있습니다. Structured metadata는 정보 삭제 기능이 아니며 cardinality의 곱은 관측 조합의 상한입니다.

</details>

---

6. 이 장의 IRSA 예제에서 ServiceAccount 소유권을 일관되게 유지하는 방법은?

   - A) eksctl과 Helm이 같은 ServiceAccount를 각각 생성
   - B) Helm values에 S3 access key 저장
   - C) eksctl --role-only로 역할만 만들고 Helm이 대응 annotation의 ServiceAccount를 생성
   - D) 모든 노드에 버킷 정책을 주고 인증 비활성화

<details>
<summary>정답 보기</summary>

**정답: C**

역할 신뢰는 정확한 OIDC provider, audience와 namespace/service-account subject에 일치해야 합니다. 플랫폼·SDK 조건을 충족하면 Pod Identity도 선택할 수 있습니다.

</details>

---

7. JSON 필드를 필터링하고 파싱 오류를 제외하는 쿼리는?

   - A) `{app="api"} | json | level="error" | __error__=""`
   - B) `{app="api"} | json | where level="error"`
   - C) `{app="api"} | json | select level="error"`
   - D) `{app="api"} | json | filter level="error"`

<details>
<summary>정답 보기</summary>

**정답: A**

LogQL은 파싱 뒤 레이블 필터 stage를 사용합니다. Unwrap한 숫자 메트릭은 변환 오류도 제외하도록 오류 필터를 unwrap 뒤에 둡니다.

</details>

---

8. 이 TSDB 배포에서 Compactor의 역할은?

   - A) Gateway 사용자 인증
   - B) 모든 클라이언트 push 요청 수신
   - C) 모든 로그를 수집31일 후 정확히 삭제 보장
   - D) 인덱스 파일을 압축·병합하고 보존 기능 활성화 시 표시된 청크를 비동기 삭제

<details>
<summary>정답 보기</summary>

**정답: D**

일반적인 작은 로그 청크 병합기가 아닙니다. 호환 스키마·인덱스 주기, 보존 활성화, 삭제 요청 저장소와 영속 marker 상태가 필요합니다.31일은 정책 예시입니다.

</details>

---

9. 수집429 응답 후 먼저 해야 할 일은?

   - A) 용량 측정 없이 모든 제한 증가
   - B) 테넌트 byte rate/burst·스트림별 rate·활성 스트림 제한을 구분하고 용량·클라이언트 재시도 확인
   - C) 쿼리 timeout만 증가
   - D) 모든 제한을 영구 비활성화

<details>
<summary>정답 보기</summary>

**정답: B**

수집 rate·burst 제한은 limits_config 아래에 있습니다. 제한 증가는 백엔드를 과부하시킬 수 있으며 재시도에는 backoff와 제한된 손실·버퍼 정책이 필요합니다.

</details>

---

10. chunk_idle_period와 /flush에 대한 올바른 설명은?

   - A) 둘 다 읽기 전용 상태 endpoint이다
   - B) chunk_idle_period는 로그 보존 기간이다
   - C) chunk_idle_period는 유휴 플러시 시점을 제어하고 POST /flush는 실제 플러시를 실행한다
   - D) chunk_idle_period를 줄이면 총비용이 항상 감소한다

<details>
<summary>정답 보기</summary>

**정답: C**

유휴 시간이 짧으면 작은 청크·객체 요청이 늘 수 있습니다. Flush는 상태 점검이 아니며 readiness도 전체 영속성을 증명하지 않습니다.

</details>
