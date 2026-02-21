# ClickHouse for Log Analytics 퀴즈

ClickHouse 로그 분석에 대한 이해도를 테스트하는 퀴즈입니다.

---

1. ClickHouse가 로그 분석에서 높은 성능을 보이는 주된 이유는?

   - A) 행 기반(Row-based) 저장 방식
   - B) 컬럼 기반(Column-based) 저장 방식
   - C) 문서 기반(Document-based) 저장 방식
   - D) 키-값(Key-Value) 저장 방식

<details>
<summary>정답 보기</summary>

**정답: B) 컬럼 기반(Column-based) 저장 방식**

**설명:**
ClickHouse는 컬럼 기반 데이터베이스로, 분석 쿼리(특정 컬럼만 스캔)에 최적화되어 있습니다. 동일한 데이터 타입이 연속 저장되어 압축률도 높고, 벡터화된 쿼리 실행이 가능합니다.

</details>

---

2. ClickHouse 클러스터에서 데이터 복제와 분산 쿼리 조정을 위해 사용하는 컴포넌트는?

   - A) Kafka
   - B) Redis
   - C) ZooKeeper/ClickHouse Keeper
   - D) etcd

<details>
<summary>정답 보기</summary>

**정답: C) ZooKeeper/ClickHouse Keeper**

**설명:**
ClickHouse 클러스터는 ZooKeeper 또는 ClickHouse Keeper를 사용하여 복제본 간 데이터 동기화, 분산 DDL 실행, 리더 선출 등을 조정합니다. ClickHouse Keeper는 ZooKeeper의 ClickHouse 전용 대안입니다.

</details>

---

3. ClickHouse 테이블 엔진 중 복제를 지원하며 로그 저장에 가장 적합한 것은?

   - A) MergeTree
   - B) ReplicatedMergeTree
   - C) Log
   - D) Memory

<details>
<summary>정답 보기</summary>

**정답: B) ReplicatedMergeTree**

**설명:**
ReplicatedMergeTree는 MergeTree의 모든 기능(정렬, 파티셔닝, TTL 등)에 복제 기능을 추가한 엔진입니다. 프로덕션 로그 저장에서 고가용성을 위해 권장됩니다.

</details>

---

4. ClickHouse에서 카디널리티가 낮은 문자열 컬럼(예: level, namespace)에 사용하는 최적화 타입은?

   - A) String
   - B) FixedString
   - C) LowCardinality(String)
   - D) Enum

<details>
<summary>정답 보기</summary>

**정답: C) LowCardinality(String)**

**설명:**
LowCardinality(String)은 고유 값이 적은(~10,000개 이하) 문자열 컬럼에 사용합니다. 내부적으로 딕셔너리 인코딩을 사용하여 저장 공간과 쿼리 성능을 최적화합니다.

</details>

---

5. ClickHouse 로그 테이블 설계에서 `ORDER BY` 절에 지정하는 컬럼 순서의 원칙은?

   - A) 알파벳 순서
   - B) 컬럼 크기 순서 (작은 것 먼저)
   - C) 자주 필터링하는 컬럼 먼저
   - D) 생성 시간 순서

<details>
<summary>정답 보기</summary>

**정답: C) 자주 필터링하는 컬럼 먼저**

**설명:**
ClickHouse의 ORDER BY는 데이터 정렬 및 인덱스 생성에 영향을 줍니다. 자주 WHERE 절에서 필터링하는 컬럼을 앞에 배치하면 쿼리 시 더 적은 데이터를 스캔합니다. 예: `ORDER BY (namespace, service, timestamp)`

</details>

---

6. ClickHouse에서 대규모 데이터를 빠르게 분석할 때 사용하는 샘플링 기법의 문법은?

   - A) `LIMIT RANDOM 10%`
   - B) `SAMPLE 0.1`
   - C) `WHERE rand() < 0.1`
   - D) `TABLESAMPLE (10 PERCENT)`

<details>
<summary>정답 보기</summary>

**정답: B) `SAMPLE 0.1`**

**설명:**
ClickHouse의 `SAMPLE` 절은 데이터의 일부만 스캔하여 빠른 근사 분석을 수행합니다. `SAMPLE 0.1`은 10%의 데이터만 읽습니다. 결과에 적절한 배수를 곱하여 전체 추정값을 얻습니다.

</details>

---

7. ClickHouse에 로그를 수집할 때 Kafka를 중간에 두는 주된 이유는?

   - A) 데이터 암호화
   - B) 버퍼링 및 피크 트래픽 처리
   - C) 데이터 압축
   - D) 쿼리 최적화

<details>
<summary>정답 보기</summary>

**정답: B) 버퍼링 및 피크 트래픽 처리**

**설명:**
Kafka는 메시지 큐로서 피크 트래픽 시 로그를 버퍼링하고, ClickHouse가 일정한 속도로 데이터를 소비할 수 있게 합니다. 또한 ClickHouse 장애 시 데이터 손실을 방지합니다.

</details>

---

8. ClickHouse SQL에서 JSON 필드 값을 추출하는 함수는?

   - A) JSON_EXTRACT()
   - B) JSONExtractString(), JSONExtractFloat()
   - C) parseJSON()
   - D) getJSON()

<details>
<summary>정답 보기</summary>

**정답: B) JSONExtractString(), JSONExtractFloat()**

**설명:**
ClickHouse는 `JSONExtractString(json, 'field')`, `JSONExtractFloat(json, 'field')` 등의 함수로 JSON 필드를 추출합니다. 타입별로 다른 함수를 사용합니다.

</details>

---

9. ClickHouse 테이블에서 오래된 데이터를 자동 삭제하는 기능은?

   - A) AUTO_DELETE
   - B) RETENTION_POLICY
   - C) TTL (Time To Live)
   - D) EXPIRE_AFTER

<details>
<summary>정답 보기</summary>

**정답: C) TTL (Time To Live)**

**설명:**
ClickHouse의 TTL 기능은 특정 기간이 지난 데이터를 자동으로 삭제하거나 다른 스토리지(예: S3)로 이동합니다. 예: `TTL date + INTERVAL 90 DAY DELETE`

</details>

---

10. ClickHouse와 Grafana 연동 시 사용하는 데이터소스 플러그인은?

    - A) grafana-mysql-datasource
    - B) grafana-clickhouse-datasource
    - C) grafana-sql-datasource
    - D) grafana-olap-datasource

<details>
<summary>정답 보기</summary>

**정답: B) grafana-clickhouse-datasource**

**설명:**
Grafana에서 ClickHouse를 연동하려면 `grafana-clickhouse-datasource` 플러그인을 설치합니다. 이 플러그인을 통해 SQL 쿼리로 ClickHouse 데이터를 시각화하고 대시보드를 구성할 수 있습니다.

</details>
