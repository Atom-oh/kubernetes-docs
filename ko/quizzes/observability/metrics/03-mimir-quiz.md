# Grafana Mimir 퀴즈

기준: Mimir 3.2.1 / chart 6.2.0. 현재 구조·identity·저장과 검증 한계를 확인합니다.

## 1. 운영 Mimir 블록 저장소로 사용하는 백엔드는 무엇인가요?

- A. 로컬 SSD만 지원
- B. S3, GCS, Azure Blob, Swift 등의 객체 스토리지
- C. NFS만 지원
- D. 메모리 캐시만 지원

<details>
<summary>정답 보기</summary>

**정답: B. S3, GCS, Azure Blob, Swift 등의 객체 스토리지**

운영 구성은 적합한 외부 객체 스토리지를 사용합니다. 로컬 개발용 filesystem backend도 있지만 이를 공유 운영 객체 저장소로 해석하면 안 됩니다. Ingester의 로컬 TSDB/WAL과 Kafka 저장소의 영속성·복구 조건은 별도입니다.

</details>

## 2. Ingest-storage 아키텍처에서 distributor의 역할은 무엇인가요?

- A. 장기 블록을 전부 직접 저장
- B. 쓰기를 검증하고 Kafka에 레코드 기록
- C. 모든 쿼리를 결과 캐시에서 반환
- D. TSDB 블록 compaction

<details>
<summary>정답 보기</summary>

**정답: B. 쓰기를 검증하고 Kafka에 레코드 기록**

Distributor는 쓰기를 검증·제한하고 Kafka 파티션으로 나눠 기록합니다. 성공 응답은 설정한 내구성 조건에 따른 Kafka 쓰기 성공에 의존하며 S3 블록 업로드를 기다리지 않습니다. Ingester quorum에 직접 쓰는 것은 classic 경로입니다.

</details>

## 3. 신뢰하지 않는 호출자의 테넌트 선택을 어떻게 보호해야 하나요?

- A. Client가 X-Scope-OrgID 값을 자유롭게 선택
- B. 신뢰한 gateway가 인증·권한을 확인하고 tenant header 설정
- C. 객체 key prefix만 사용
- D. namespace 이름만으로 HTTP 인증된 것으로 처리

<details>
<summary>정답 보기</summary>

**정답: B. 신뢰한 gateway가 인증·권한을 확인하고 tenant header 설정**

X-Scope-OrgID는 테넌트 식별자이지 자격 증명이 아닙니다. 신뢰한 gateway가 호출자와 테넌트의 관계를 강제하고 외부 header를 덮어써야 합니다. Basic-auth username 매핑도 proxy의 명시적 정책이 필요하며 백엔드 우회 접근도 제한해야 합니다.

</details>

## 4. Ingester가 TSDB 블록을 객체 스토리지에 업로드하는 이유는 무엇인가요?

- A. 모든 로컬 영속성을 없애기 위해
- B. 장기 블록 저장과 블록 쿼리 접근을 제공하기 위해
- C. Grafana 대시보드를 백업하기 위해
- D. 응답한 모든 샘플이 모든 장애에서 보존되도록 보장하기 위해

<details>
<summary>정답 보기</summary>

**정답: B. 장기 블록 저장과 블록 쿼리 접근을 제공하기 위해**

Ingester는 로컬 TSDB/WAL을 유지하고 주기적으로 블록을 업로드합니다. Store-gateway로 인계하는 동안 로컬 보존 범위가 겹칩니다. Kafka 쓰기 응답, ingester 소비, 객체 업로드는 다른 단계이며 복구에는 영속성·보존·장애 조건이 필요합니다.

</details>

## 5. Compactor가 담당하는 작업은 무엇인가요?

- A. 모든 애플리케이션 endpoint scrape
- B. 블록 병합, 복제 샘플 중복 제거와 보존 정리
- C. 모든 테넌트 인증
- D. downsampling_enabled로 원시 시계열 자동 다운샘플링

<details>
<summary>정답 보기</summary>

**정답: B. 블록 병합, 복제 샘플 중복 제거와 보존 정리**

Compaction은 블록을 합치고 replica의 중복 샘플을 제거합니다. 보존 정리는 비동기입니다. compactor.downsampling_enabled라는 가짜 옵션을 사용하면 안 되며 recording rule도 원시 데이터를 자동 삭제하지 않고 파생 시계열을 만듭니다.

</details>

## 6. Query-frontend의 역할이 아닌 것은 무엇인가요?

- A. 지원 쿼리 분할·shard
- B. 쿼리 결과 캐시 사용
- C. 원본 장기 TSDB 블록 영구 저장
- D. 쿼리 응답 병합

<details>
<summary>정답 보기</summary>

**정답: C. 원본 장기 TSDB 블록 영구 저장**

Frontend는 작업을 계획·캐시하고 결과를 합쳐 반환합니다. Scheduler가 작업을 대기시키고 querier가 필요한 데이터를 조회합니다. Metadata나 chunk cache 적중이 완전한 쿼리 답을 뜻하지 않으며 step alignment는 요청 timestamp와 PromQL conformance를 바꿀 수 있습니다.

</details>

## 7. VictoriaMetrics와의 비교로 올바른 것은 무엇인가요?

- A. Mimir에는 filesystem backend가 전혀 없음
- B. Grafana를 사용하면 Mimir가 항상 더 빠름
- C. 스토리지 구조·쿼리 의미·테넌트 권한·복구·실측 비용을 비교
- D. VictoriaMetrics는 테넌트를 지원하지 않음

<details>
<summary>정답 보기</summary>

**정답: C. 스토리지 구조·쿼리 의미·테넌트 권한·복구·실측 비용을 비교**

두 제품 모두 인증·권한 경계가 필요합니다. Mimir 운영 블록 저장과 검토한 VictoriaMetrics 로컬 저장 구조는 운영 조건이 다릅니다. 출처 없는 압축률 순위나 ecosystem 선호만으로 성능·비용 우위를 판단할 수 없습니다.

</details>

## 8. Store-gateway가 제공하는 기능은 무엇인가요?

- A. 애플리케이션 메트릭 수집
- B. 객체 스토리지·index header·설정한 cache를 통한 블록 조회
- C. 자동 테넌트 인증
- D. Kafka broker 복제

<details>
<summary>정답 보기</summary>

**정답: B. 객체 스토리지·index header·설정한 cache를 통한 블록 조회**

Querier는 store-gateway의 블록과 ingester의 최근 데이터를 조회하며 블록 인계 중 범위가 겹칠 수 있습니다. Cache/index metadata 재사용은 일부 작업을 줄이지만 모든 쿼리가 chunk 읽기 없이 끝나는 것은 아닙니다.

</details>

## 9. compactor_blocks_retention_period는 무엇을 제어하나요?

- A. 메모리 캐시 만료만 제어
- B. Compactor가 적용하는 장기 블록 보존 정책
- C. Kafka topic 보존
- D. 물리 삭제·규정 준수의 정확한 시한

<details>
<summary>정답 보기</summary>

**정답: B. Compactor가 적용하는 장기 블록 보존 정책**

실제 제거에는 블록 시간 범위, scan·삭제 mark와 deletion_delay가 영향을 줍니다. 로컬 TSDB와 Kafka 보존은 별도입니다. S3 versioning·Object Lock·백업도 완전 삭제에 영향을 주므로 365d 설정만으로 규정 준수를 보장할 수 없습니다.

</details>

## 10. 가용성 구성에서 타당하지 않은 가정은 무엇인가요?

- A. Kafka 내구성과 복구를 별도로 검증
- B. zone selector를 실제 배치 가능한 노드와 일치
- C. 모든 것을 한 AZ에 배치하고 AZ 장애 내성을 보장한다고 주장
- D. Ingester 파티션 coverage·store-gateway replica·rollout 의존성을 검토

<details>
<summary>정답 보기</summary>

**정답: C. 모든 것을 한 AZ에 배치하고 AZ 장애 내성을 보장한다고 주장**

논리적 zone이 실제 배치는 아닙니다. 예제는 선택한 세 zone에 ingester/store-gateway 각각 총3개를 렌더링하지만 broker topology·PVC·용량·queue·rollout과 나머지 컴포넌트도 검증해야 합니다. Cache 중복성과 compactor 하나가 전체 HA를 보장하지 않습니다.

</details>

[본문으로 돌아가기](../../../observability/metrics/03-mimir.md)
