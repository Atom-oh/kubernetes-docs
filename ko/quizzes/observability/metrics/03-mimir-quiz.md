# Grafana Mimir 퀴즈

Grafana Mimir에 대한 이해도를 테스트하는 퀴즈입니다.

---

1. Grafana Mimir의 주요 스토리지 백엔드는?
   - A) 로컬 SSD만 지원
   - B) 객체 스토리지 (S3, GCS, Azure Blob)
   - C) NFS 공유 스토리지
   - D) 블록 스토리지만 지원

<details>
<summary>정답 보기</summary>

**정답: B) 객체 스토리지 (S3, GCS, Azure Blob)**

**설명:**
Grafana Mimir는 객체 스토리지를 필수로 사용합니다. S3, Google Cloud Storage, Azure Blob Storage 등을 지원하며, 이를 통해 무제한 확장성과 비용 효율적인 장기 저장을 제공합니다. 로컬 스토리지는 Ingester의 WAL과 임시 데이터에만 사용됩니다.

</details>

---

2. Mimir 아키텍처에서 Distributor의 역할은?
   - A) 데이터 장기 저장
   - B) 쓰기 요청의 첫 진입점, 테넌트 검증 및 샘플 분배
   - C) 쿼리 결과 캐싱
   - D) 블록 컴팩션

<details>
<summary>정답 보기</summary>

**정답: B) 쓰기 요청의 첫 진입점, 테넌트 검증 및 샘플 분배**

**설명:**
Distributor는 쓰기 요청의 첫 번째 진입점으로, 테넌트 ID 검증, 시계열 검증, 해시 링 기반 Ingester 분배, 레플리케이션 팩터에 따른 복제 등을 담당합니다. 상태가 없는(stateless) 컴포넌트로 수평 확장이 용이합니다.

</details>

---

3. Mimir에서 멀티테넌시를 구현하는 방법은?
   - A) 테넌트별 별도 클러스터 운영
   - B) X-Scope-OrgID 헤더로 테넌트 식별
   - C) IP 주소 기반 테넌트 분리
   - D) 네임스페이스별 테넌트 분리

<details>
<summary>정답 보기</summary>

**정답: B) X-Scope-OrgID 헤더로 테넌트 식별**

**설명:**
Mimir는 HTTP 헤더 `X-Scope-OrgID`를 통해 테넌트를 식별합니다. Prometheus의 remote_write 설정에 이 헤더를 추가하면 각 테넌트의 데이터가 격리됩니다. 테넌트별로 별도의 제한(limits)을 설정할 수 있으며, 데이터는 객체 스토리지에서 테넌트별 경로로 분리됩니다.

</details>

---

4. Mimir의 Ingester가 객체 스토리지에 블록을 업로드하는 이유는?
   - A) 실시간 쿼리 성능 향상
   - B) 메모리에서 디스크로 데이터를 영구 저장
   - C) 알림 규칙 저장
   - D) 대시보드 설정 백업

<details>
<summary>정답 보기</summary>

**정답: B) 메모리에서 디스크로 데이터를 영구 저장**

**설명:**
Ingester는 수신한 시계열 데이터를 먼저 메모리에 저장하고, 주기적으로(기본 2시간) TSDB 블록을 생성하여 객체 스토리지에 업로드합니다. 이를 통해 데이터가 영구적으로 저장되며, Ingester 장애 시에도 데이터 손실을 최소화합니다.

</details>

---

5. Mimir의 Compactor 역할로 올바른 것은?
   - A) 실시간 쿼리 처리
   - B) 작은 블록을 큰 블록으로 병합 및 중복 제거
   - C) 메트릭 수집
   - D) 알림 전송

<details>
<summary>정답 보기</summary>

**정답: B) 작은 블록을 큰 블록으로 병합 및 중복 제거**

**설명:**
Compactor는 객체 스토리지의 작은 블록들을 큰 블록으로 병합(compaction)하고, 중복 데이터를 제거하며, 보존 정책에 따라 오래된 데이터를 삭제합니다. 이를 통해 쿼리 성능이 향상되고 스토리지 비용이 절감됩니다.

</details>

---

6. Mimir의 Query-frontend가 제공하는 기능이 아닌 것은?
   - A) 대규모 쿼리 분할
   - B) 결과 캐싱
   - C) 데이터 저장
   - D) 쿼리 재시도

<details>
<summary>정답 보기</summary>

**정답: C) 데이터 저장**

**설명:**
Query-frontend는 쿼리 최적화와 캐싱을 담당하는 상태 없는 컴포넌트입니다. 대규모 쿼리를 작은 쿼리로 분할하고, 결과를 캐싱하며, 실패한 쿼리를 재시도합니다. 데이터 저장은 Ingester(단기)와 객체 스토리지(장기)가 담당합니다.

</details>

---

7. Mimir와 VictoriaMetrics 비교 시 Mimir의 특징으로 올바른 것은?
   - A) 로컬 디스크만 사용 가능
   - B) 운영 복잡성이 더 낮음
   - C) 객체 스토리지 필수, 엔터프라이즈급 멀티테넌시
   - D) MetricsQL 쿼리 언어 사용

<details>
<summary>정답 보기</summary>

**정답: C) 객체 스토리지 필수, 엔터프라이즈급 멀티테넌시**

**설명:**
Mimir는 객체 스토리지를 필수로 사용하며, 네이티브 멀티테넌시를 제공하여 엔터프라이즈 환경에 적합합니다. VictoriaMetrics는 로컬 디스크도 지원하고 운영이 더 단순하지만, Mimir는 Grafana 에코시스템과의 통합이 우수합니다.

</details>

---

8. Mimir에서 Store-gateway의 역할은?
   - A) 메트릭 수집
   - B) 객체 스토리지의 블록을 캐싱하고 과거 데이터 쿼리 처리
   - C) 알림 규칙 평가
   - D) 테넌트 인증

<details>
<summary>정답 보기</summary>

**정답: B) 객체 스토리지의 블록을 캐싱하고 과거 데이터 쿼리 처리**

**설명:**
Store-gateway는 객체 스토리지에 저장된 블록의 인덱스와 청크를 캐싱하고, 과거 데이터에 대한 쿼리를 처리합니다. Querier는 최근 데이터는 Ingester에서, 과거 데이터는 Store-gateway에서 조회하여 병합합니다.

</details>

---

9. Mimir에서 `compactor_blocks_retention_period` 설정의 역할은?
   - A) 메모리 캐시 보존 기간
   - B) 블록 데이터의 보존 기간 설정
   - C) 로그 보존 기간
   - D) 알림 히스토리 보존 기간

<details>
<summary>정답 보기</summary>

**정답: B) 블록 데이터의 보존 기간 설정**

**설명:**
`compactor_blocks_retention_period`는 Compactor가 블록을 보존하는 기간을 설정합니다. 예를 들어, `365d`로 설정하면 1년 이상 된 블록이 삭제됩니다. 이 설정을 통해 스토리지 비용을 관리하고 규정 준수 요구사항을 충족할 수 있습니다.

</details>

---

10. Mimir 고가용성 구성 시 권장사항으로 올바르지 않은 것은?
    - A) Ingester 최소 3개 복제본, zone-aware 복제
    - B) Store-gateway 최소 2개 복제본
    - C) 모든 컴포넌트를 단일 가용 영역에 배치
    - D) memcached를 사용한 캐싱 활성화

<details>
<summary>정답 보기</summary>

**정답: C) 모든 컴포넌트를 단일 가용 영역에 배치**

**설명:**
고가용성을 위해서는 컴포넌트를 여러 가용 영역(AZ)에 분산 배치해야 합니다. Mimir는 zone-aware 복제를 지원하여 Ingester를 여러 AZ에 분산할 수 있습니다. 단일 AZ에 배치하면 해당 AZ 장애 시 전체 서비스가 중단됩니다.

</details>
