# ClickHouse for Log Analytics 퀴즈

> **마지막 업데이트**: 2026년 9월 13일

1. 컬럼 저장이 분석 로그 쿼리에 도움이 되는 이유는?

   - A) 항상 모든 필드를 읽는다
   - B) 필요한 컬럼을 읽고 반복 값을 압축할 수 있다
   - C) 고정 압축률을 보장한다
   - D) 스키마 설계가 필요 없어진다

<details>
<summary>정답 보기</summary>

**정답: B) 필요한 컬럼을 읽고 반복 값을 압축할 수 있다**

효과는 데이터·sort key·쿼리에 따라 다릅니다. 가이드가 10:1 압축이나 고정 처리량을 보장하지는 않습니다.

</details>

---

2. 이 설계에서 Keeper/ZooKeeper의 역할은?

   - A) 모든 분산 SELECT 실행
   - B) 모든 로그 행 저장
   - C) Replicated table과 분산 DDL 조정
   - D) Collector 대체

<details>
<summary>정답 보기</summary>

**정답: C) Replicated table과 분산 DDL 조정**

분산 쿼리는 ClickHouse query initiator와 Distributed 테이블이 처리합니다. Keeper는 query router가 아닙니다.

</details>

---

3. MergeTree 저장에 replication을 추가하는 engine은?

   - A) ReplicatedMergeTree
   - B) Memory
   - C) Buffer
   - D) Distributed만 사용

<details>
<summary>정답 보기</summary>

**정답: A) ReplicatedMergeTree**

Replica에는 coordination·독립된 영속 저장소·장애 도메인 설계가 필요합니다. Replication만으로 무조건적인 HA가 보장되지는 않습니다.

</details>

---

4. 반복되는 namespace나 severity 값에 검토할 타입은?

   - A) 항상 FixedString(255)
   - B) LowCardinality(String)
   - C) 각 로그 메시지마다 고유 integer
   - D) 압축하지 않은 String만

<details>
<summary>정답 보기</summary>

**정답: B) LowCardinality(String)**

반복 값에 dictionary encoding이 도움이 될 수 있습니다. 고정 distinct-value 상한 대신 dictionary 크기와 query 동작을 측정합니다.

</details>

---

5. 로그 테이블의 ORDER BY는 어떻게 정하는가?

   - A) 알파벳 순서
   - B) 필드 생성 시각
   - C) 선택도 높은 필터·locality·대표 query 기준
   - D) 쿼리와 무관하게 항상 timestamp를 마지막에

<details>
<summary>정답 보기</summary>

**정답: C) 선택도 높은 필터·locality·대표 query 기준**

Key는 정렬과 index pruning에 영향을 줍니다. 자주 조회하는 컬럼이라는 이유만으로 최선의 순서가 정해지지는 않습니다.

</details>

---

6. SAMPLE 0.1을 사용하기 전에 필요한 조건은?

   - A) 모든 테이블이 자동 지원
   - B) 테이블 행이 정확히 10개
   - C) 항상 정확히 10%의 행 반환
   - D) 호환되는 MergeTree sampling expression을 정의하고 primary key에 포함

<details>
<summary>정답 보기</summary>

**정답: D) 호환되는 MergeTree sampling expression을 정의하고 primary key에 포함**

기본 로그 테이블에는 SAMPLE BY가 없습니다. 별도 sample_demo가 필요한 설계를 보여줍니다. 결정적인 sampling-key 구간에 유한한 행의 정확히 10%가 포함되는 것은 아닙니다.

</details>

---

7. 설정 조건에 따라 Kafka가 제공하는 것은?

   - A) 메모리 Buffer를 거쳐도 exactly-once 보장
   - B) Burst buffering과 retention 안의 replay
   - C) 모든 parser 오류 자동 제거
   - D) 장애 중 무제한 저장

<details>
<summary>정답 보기</summary>

**정답: B) Burst buffering과 retention 안의 replay**

Retention·acknowledgement·replication·용량·offset commit·downstream insert를 검증해야 합니다. 메모리 Buffer는 crash 때 확인 응답한 데이터도 잃을 수 있습니다.

</details>

---

8. 선택적인 response_time_ms에 nullable JSON 추출을 사용하는 이유는?

   - A) 없는 측정값을 0ms 요청으로 집계하지 않기 위해
   - B) 모든 로그가 HTTP 요청이므로
   - C) JSON 검증이 필요 없어지므로
   - D) 서버 시계를 변경하기 위해

<details>
<summary>정답 보기</summary>

**정답: A) 없는 측정값을 0ms 요청으로 집계하지 않기 위해**

JSONType으로 boolean·숫자 문자열을 먼저 제외하고 nullable 숫자를 추출합니다. Nullable 추출만으로는 해당 값이 숫자로 변환될 수 있습니다. Count·percentile은 측정된 이벤트로 계산합니다.

</details>

---

9. TTL TO VOLUME에 필요한 조건과 보장은?

   - A) S3 bucket과 IAM role 생성
   - B) 모든 행을 정확한 시각에 삭제
   - C) 이미 선택한 storage policy가 필요하며 background 작업은 비동기
   - D) Cold part를 독립 Parquet backup으로 만듦

<details>
<summary>정답 보기</summary>

**정답: C) 이미 선택한 storage policy가 필요하며 background 작업은 비동기**

TTL이 policy나 cloud 권한을 만들지는 않습니다. Cold table storage와 별도로 검증한 Parquet archive는 소유권·복구 의미가 다릅니다.

</details>

---

10. ClickHouse 기반 Grafana 알림은 어떻게 만드는가?

   - A) clickhouse_custom_query Prometheus metric을 임의로 만듦
   - B) grafana-clickhouse-datasource의 숫자 SQL 결과와 Grafana Alerting 사용
   - C) 모든 dashboard에 관리 계정 사용
   - D) 로그가 없으면 정상이라고 판단

<details>
<summary>정답 보기</summary>

**정답: B) grafana-clickhouse-datasource의 숫자 SQL 결과와 Grafana Alerting 사용**

제한된 read-only 계정·검증하는 TLS·필요한 timeout 설정 권한을 사용합니다. 입력이 없어도 집계가 0일 수 있으므로 수집 상태를 따로 관찰합니다.

</details>

---

[본문으로 돌아가기](../../../observability/logging/04-clickhouse.md)
