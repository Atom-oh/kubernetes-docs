# Amazon OpenSearch Service 퀴즈

Amazon OpenSearch Service에 대한 이해도를 테스트하는 퀴즈입니다.

---

1. Amazon OpenSearch Service의 기반이 되는 오픈소스 프로젝트는?

   - A) Apache Solr
   - B) Elasticsearch 7.10 포크
   - C) Apache Lucene 단독
   - D) Splunk 오픈소스 버전

<details>
<summary>정답 보기</summary>

**정답: B) Elasticsearch 7.10 포크**

**설명:**
OpenSearch는 2021년 AWS가 Elasticsearch 7.10을 Apache 2.0 라이선스로 포크하여 만든 오픈소스 프로젝트입니다. Elastic의 라이선스 변경(SSPL)에 대응하여 시작되었습니다.

</details>

---

2. OpenSearch 클러스터에서 인덱스 메타데이터 관리와 클러스터 상태 관리를 담당하는 노드 유형은?

   - A) Data Node
   - B) Master Node
   - C) UltraWarm Node
   - D) Coordinating Node

<details>
<summary>정답 보기</summary>

**정답: B) Master Node**

**설명:**
Master Node는 클러스터 상태 관리, 인덱스 생성/삭제, 샤드 할당 결정 등 클러스터 관리 작업을 담당합니다. 프로덕션 환경에서는 전용 마스터 노드 3개를 권장합니다.

</details>

---

3. OpenSearch에서 비용 효율적인 읽기 전용 스토리지 티어는?

   - A) Hot Storage
   - B) Warm Storage
   - C) UltraWarm
   - D) Standard Storage

<details>
<summary>정답 보기</summary>

**정답: C) UltraWarm**

**설명:**
UltraWarm은 S3 기반의 읽기 전용 스토리지 티어로, Hot 스토리지(EBS) 대비 약 75% 저렴합니다. 자주 조회하지 않는 과거 로그 데이터 저장에 적합합니다.

</details>

---

4. ISM(Index State Management) 정책의 주요 목적은?

   - A) 인덱스 보안 설정 관리
   - B) 인덱스 라이프사이클 자동화 (롤오버, 삭제 등)
   - C) 인덱스 쿼리 최적화
   - D) 인덱스 복제 설정

<details>
<summary>정답 보기</summary>

**정답: B) 인덱스 라이프사이클 자동화 (롤오버, 삭제 등)**

**설명:**
ISM 정책은 인덱스의 라이프사이클을 자동으로 관리합니다. 인덱스 롤오버, Hot→UltraWarm→Cold 전환, 보존 기간 후 삭제 등을 자동화할 수 있습니다.

</details>

---

5. OpenSearch에 로그를 수집하는 방법 중 가장 비용 효율적이고 관리가 용이한 방식은?

   - A) Logstash on EC2
   - B) FluentBit DaemonSet + 직접 전송
   - C) Kinesis Data Firehose
   - D) Lambda 함수

<details>
<summary>정답 보기</summary>

**정답: C) Kinesis Data Firehose**

**설명:**
Kinesis Data Firehose는 완전관리형 서비스로 버퍼링, 압축, 배치 처리를 자동으로 수행합니다. S3 백업, 오류 처리가 내장되어 있어 운영 부담이 적고, 대규모 로그 수집에 비용 효율적입니다.

</details>

---

6. OpenSearch Fine-Grained Access Control(FGAC)에서 특정 네임스페이스의 로그만 접근 가능하도록 제한하는 기능은?

   - A) Field-Level Security (FLS)
   - B) Document-Level Security (DLS)
   - C) Index-Level Security
   - D) Cluster-Level Security

<details>
<summary>정답 보기</summary>

**정답: B) Document-Level Security (DLS)**

**설명:**
Document-Level Security(DLS)는 특정 조건을 만족하는 문서만 접근할 수 있도록 제한합니다. 예를 들어 `kubernetes.namespace: "team-a"` 조건으로 특정 팀의 로그만 볼 수 있게 설정할 수 있습니다.

</details>

---

7. OpenSearch 인덱스 템플릿에서 `LowCardinality` 대신 사용하는 Elasticsearch/OpenSearch의 문자열 최적화 타입은?

   - A) text
   - B) keyword
   - C) analyzed_string
   - D) compact_string

<details>
<summary>정답 보기</summary>

**정답: B) keyword**

**설명:**
OpenSearch에서 카디널리티가 낮은 문자열 필드(namespace, level 등)는 `keyword` 타입을 사용합니다. `text` 타입은 전문 검색용으로 분석(tokenize)되고, `keyword`는 정확한 매칭과 집계에 최적화됩니다.

</details>

---

8. OpenSearch 비용 최적화를 위한 스토리지 티어링 순서로 올바른 것은?

   - A) Cold → UltraWarm → Hot
   - B) Hot → Cold → UltraWarm
   - C) Hot → UltraWarm → Cold
   - D) UltraWarm → Hot → Cold

<details>
<summary>정답 보기</summary>

**정답: C) Hot → UltraWarm → Cold**

**설명:**
데이터는 먼저 Hot 스토리지(EBS)에 저장되어 빠른 쿼리를 지원하고, 시간이 지나면 UltraWarm(읽기 전용)으로, 더 오래되면 Cold Storage(S3)로 이동합니다. 이 순서대로 비용이 감소합니다.

</details>

---

9. OpenSearch 쿼리에서 특정 시간 범위의 에러 로그를 검색하는 올바른 Query DSL은?

   - A) `{"query": {"match": {"level": "error", "time": "1h"}}}`
   - B) `{"query": {"bool": {"must": [{"match": {"level": "error"}}, {"range": {"@timestamp": {"gte": "now-1h"}}}]}}}`
   - C) `{"filter": {"level": "error", "time": "> now-1h"}}`
   - D) `{"search": {"level": "error", "since": "1h"}}`

<details>
<summary>정답 보기</summary>

**정답: B) `{"query": {"bool": {"must": [{"match": {"level": "error"}}, {"range": {"@timestamp": {"gte": "now-1h"}}}]}}}`**

**설명:**
OpenSearch Query DSL에서 여러 조건을 조합할 때는 `bool` 쿼리를 사용합니다. `must` 배열에 `match`(텍스트 매칭)와 `range`(시간 범위)를 함께 지정합니다.

</details>

---

10. OpenSearch와 Loki 비교 시, OpenSearch가 더 적합한 사용 사례는?

    - A) 비용 최적화가 최우선인 스타트업
    - B) 전문 검색과 복잡한 분석 쿼리가 필요한 경우
    - C) 기존 Grafana 스택과의 통합
    - D) 단순한 로그 필터링만 필요한 경우

<details>
<summary>정답 보기</summary>

**정답: B) 전문 검색과 복잡한 분석 쿼리가 필요한 경우**

**설명:**
OpenSearch는 Lucene 기반의 강력한 전문 검색(Full-text Search) 기능과 복잡한 집계 쿼리를 지원합니다. 보안 분석(SIEM), 규정 준수, 복잡한 로그 분석이 필요한 경우에 적합합니다. 비용 최적화나 단순 필터링은 Loki가 더 적합합니다.

</details>
