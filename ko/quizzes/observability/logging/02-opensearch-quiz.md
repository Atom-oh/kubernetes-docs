# Amazon OpenSearch Service 퀴즈

> **마지막 업데이트**: 2026년 9월 13일

[가이드](../../../observability/logging/02-opensearch.md)의 관리형 도메인·수집 예제를 기준으로 합니다.

---

1. OpenSearch와 Amazon OpenSearch Service를 올바르게 구분한 설명은?

   - A) 모든 Elasticsearch client/plugin이 계속 호환됨
   - B) AWS가 모든 upstream 릴리스를 즉시 지원함
   - C) OpenSearch는 Apache 2.0 프로젝트이며 관리형 서비스는 선택된 엔진 버전을 지원함
   - D) Kibana 호스팅만 제공하는 서비스임

<details>
<summary>정답 보기</summary>

**정답: C**

Elasticsearch 7.10 계열에서 시작했어도 모든 호환성이 보장되지는 않습니다. AWS 지원 버전과 실제 client/plugin을 확인합니다. 기존 2.11도 2027년 11월 7일까지 표준 지원 대상입니다.

</details>

---

2. 전용 cluster-manager를 구성했을 때 클러스터 상태와 샤드 배치를 관리하는 역할은?

   - A) 전용 cluster-manager node
   - B) UltraWarm 저장소
   - C) Cold 저장소
   - D) 로그 수집기

<details>
<summary>정답 보기</summary>

**정답: A**

AWS 설정 필드는 여전히 dedicated_master 이름을 사용합니다. 관리자 개수와 데이터 replica 수는 별개이며 zone awareness만으로 Multi-AZ with Standby가 켜지지 않습니다.

</details>

---

3. 기존 UltraWarm과 cold 저장소에 대한 올바른 설명은?

   - A) UltraWarm은 모든 데이터를 EBS에만 저장함
   - B) 둘 다 S3 기반이며 cold 인덱스는 UltraWarm에 연결한 뒤 조회함
   - C) 모든 워크로드에서 정확히 75% 절감됨
   - D) 모든 인스턴스·엔진 조합에서 두 계층을 지원함

<details>
<summary>정답 보기</summary>

**정답: B**

Hot→UltraWarm→cold 정책에는 서비스 사전 조건과 이동 용량이 필요합니다. 비용·조회 지연은 워크로드에 따라 달라지며 계층 이름이 고정 절감률을 보장하지 않습니다.

</details>

---

4. 관리형 OpenSearch Service의 cold 인덱스를 삭제하는 ISM action은?

   - A) 모든 계층에서 delete
   - B) force_merge
   - C) warm_migration
   - D) cold_delete

<details>
<summary>정답 보기</summary>

**정답: D**

관리형 cold에는 cold_delete가 필요합니다. Action 객체마다 작업 하나를 두며 비동기로 실행됩니다. 예제의 인덱스 나이 7/30/90일은 이벤트별 정확한 보존 시간을 보장하지 않습니다.

</details>

---

5. Fluent Bit 직접 전송과 Amazon Data Firehose는 어떻게 비교해야 하는가?

   - A) Firehose가 항상 가장 저렴함
   - B) Fluent Bit 직접 전송은 AWS 인증을 할 수 없음
   - C) 운영 요건·스키마·buffer/retry/backup·접근·실측 비용을 비교함
   - D) 둘 다 동일한 Kubernetes metadata를 자동 생성함

<details>
<summary>정답 보기</summary>

**정답: C**

Firehose도 역할·연결·호환 레코드가 필요합니다. Backup mode는 FailedDocumentsOnly로 선택하며 prefix 이름을 failed/로 정하는 것만으로 선택되지 않습니다.

</details>

---

6. DLS와 FLS의 차이를 올바르게 설명한 것은?

   - A) DLS는 문서를, FLS는 반환 필드를 제한하며 전체 역할·신뢰된 metadata도 중요함
   - B) FLS가 Kubernetes namespace를 자동 인증함
   - C) URI 기반 IAM만으로 bulk body의 모든 인덱스를 제한함
   - D) 보안 그룹 규칙이 문서 수준 읽기 권한을 부여함

<details>
<summary>정답 보기</summary>

**정답: A**

가이드는 신뢰된 kubernetes.namespace_name을 사용합니다. 제한 역할을 추가해도 기존의 더 넓은 권한이 자동 취소되지는 않습니다. FLS는 허용된 message 내부의 민감한 문자열을 가리거나 저장·백업 데이터를 삭제하지 않습니다.

</details>

---

7. 문자열의 정확한 매칭과 일반적인 필드 집계에 사용하는 mapping type은?

   - A) subfield 없는 text
   - B) keyword
   - C) OpenSearch type인 LowCardinality
   - D) mapping 없는 필드만

<details>
<summary>정답 보기</summary>

**정답: B**

Keyword는 분석되는 text 및 ClickHouse LowCardinality와 다릅니다. 여러 keyword·숫자 집계는 컬럼형 doc values를 사용하므로 항상 모든 _source 문서 전체를 스캔하지 않습니다.

</details>

---

8. Logstash_Format On, prefix logs-production인 Fluent Bit 예제는 어디로 쓰는가?

   - A) 항상 rollover alias
   - B) 자동으로 Serverless collection
   - C) 분리된 cold 인덱스에 직접
   - D) 날짜 기반 logs-production-YYYY.MM.DD 인덱스

<details>
<summary>정답 보기</summary>

**정답: D**

Alias가 존재한다고 자동 사용하지 않습니다. 가이드는 날짜 경로와 rollover-logs-*를 분리합니다. 후자에는 rollover alias 설정, 번호가 붙은 인덱스와 write alias가 필요합니다.

</details>

---

9. Mapping된 최근 1시간 error 로그를 필터링하는 Query DSL은?

   - A) `{"query":{"match":{"app.level":"error","time":"1h"}}}`
   - B) `{"filter":{"app.level":"error","time":"last-hour"}}`
   - C) `{"query":{"bool":{"filter":[{"term":{"app.level":"error"}},{"range":{"@timestamp":{"gte":"now-1h"}}}]}}}`
   - D) `{"query":{"where":{"level":"error"}}}`

<details>
<summary>정답 보기</summary>

**정답: C**

예제 mapping은 앱 필드를 app 아래에 두고 @timestamp를 사용합니다. Filter context에서 relevance scoring 없이 정확한 keyword 조건과 시간 범위를 결합합니다.

</details>

---

10. 로그 워크로드에 OpenSearch·Loki·ClickHouse를 선택하는 적절한 근거는?

   - A) 보편적인 100GB/일 전환 기준
   - B) 모든 조직의 쿼리 구성이 같다는 주장
   - C) 고정 3–5배 비용·60–80% 절감 공식
   - D) 대표 쿼리와 보존·내구성·권한·운영 역량·실측 비용

<details>
<summary>정답 보기</summary>

**정답: D**

인덱싱·쿼리 모델과 운영 절충이 다릅니다. 같은 요건으로 비교하고 이전·정합성·롤백을 검증합니다. 제품 선택만으로 규정 준수나 최저 비용이 자동 달성되지 않습니다.

</details>
