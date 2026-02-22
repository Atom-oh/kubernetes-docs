# Observability 실습 Part 6: 분산 추적 분석 퀴즈

> **마지막 업데이트**: 2025년 2월

이 퀴즈는 Observability 실습 Part 6의 분산 추적 분석에 대한 이해도를 테스트합니다.

---

1. TraceQL의 기본 문법과 span 필터링 방법으로 올바른 것은?
   - A) SQL과 동일한 문법을 사용한다
   - B) 중괄호 `{ }` 안에 span 속성 조건을 작성하여 필터링한다 (예: `{ span.http.method = "GET" }`)
   - C) JSON 형식으로 쿼리를 작성한다
   - D) 정규표현식만 지원한다
<details>
<summary>정답 보기</summary>

**정답: B) 중괄호 `{ }` 안에 span 속성 조건을 작성하여 필터링한다 (예: `{ span.http.method = "GET" }`)**

**설명:**
TraceQL은 Grafana Tempo의 트레이스 쿼리 언어입니다. 기본 구문은 `{ <조건> }` 형식이며, span 속성을 필터링합니다. `span.<attribute>`로 span 속성에 접근하고, `resource.<attribute>`로 리소스 속성에 접근합니다. 비교 연산자(=, !=, >, <, =~), 논리 연산자(&&, ||)를 지원합니다. 예: `{ span.http.status_code >= 400 && resource.service.name = "api" }`

</details>

---

2. 다음 TraceQL 쿼리 `{ span.http.status_code >= 500 }`의 의미는?
   - A) HTTP 상태 코드가 정확히 500인 span을 검색한다
   - B) HTTP 상태 코드가 500 이상(5xx 에러)인 모든 span을 포함하는 트레이스를 검색한다
   - C) 500개의 span을 검색한다
   - D) HTTP 요청 시간이 500ms 이상인 span을 검색한다
<details>
<summary>정답 보기</summary>

**정답: B) HTTP 상태 코드가 500 이상(5xx 에러)인 모든 span을 포함하는 트레이스를 검색한다**

**설명:**
이 TraceQL 쿼리는 `http.status_code` 속성이 500 이상인 span을 검색합니다. 이는 5xx 서버 에러(500 Internal Server Error, 502 Bad Gateway, 503 Service Unavailable 등)를 의미합니다. 조건에 맞는 span이 포함된 전체 트레이스가 반환되어, 에러가 발생한 요청의 전체 흐름을 분석할 수 있습니다.

</details>

---

3. Tempo Service Graph에서 에러율/지연이 높은 엣지를 식별하는 방법은?
   - A) 로그를 직접 검색해야 한다
   - B) 서비스 간 연결을 시각화한 그래프에서 에러율은 빨간색 강조, 지연은 엣지 두께나 레이블로 표시된다
   - C) 별도의 대시보드를 만들어야 한다
   - D) Service Graph는 에러 정보를 제공하지 않는다
<details>
<summary>정답 보기</summary>

**정답: B) 서비스 간 연결을 시각화한 그래프에서 에러율은 빨간색 강조, 지연은 엣지 두께나 레이블로 표시된다**

**설명:**
Tempo Service Graph는 분산 시스템의 서비스 간 의존성을 시각화합니다. 각 노드는 서비스를 나타내고, 엣지는 서비스 간 호출을 나타냅니다. 에러율이 높은 엣지는 빨간색으로 표시되고, 지연 시간은 엣지 레이블이나 두께로 나타납니다. 이를 통해 시스템의 병목 지점이나 문제가 있는 서비스 간 연결을 빠르게 식별할 수 있습니다.

</details>

---

4. Span 타임라인(Waterfall View)에서 병목 구간을 식별하는 기법은?
   - A) span 수를 세어 가장 많은 span이 있는 서비스를 찾는다
   - B) 각 span의 시작/종료 시간과 duration을 시각적으로 분석하여 가장 오래 걸린 span이나 직렬화된 호출 체인을 찾는다
   - C) 알파벳 순으로 서비스를 정렬한다
   - D) 가장 먼저 시작된 span이 항상 병목이다
<details>
<summary>정답 보기</summary>

**정답: B) 각 span의 시작/종료 시간과 duration을 시각적으로 분석하여 가장 오래 걸린 span이나 직렬화된 호출 체인을 찾는다**

**설명:**
Waterfall View는 트레이스 내 span들을 시간순으로 시각화합니다. 병목을 찾으려면 (1) 가장 긴 duration을 가진 span 확인, (2) 부모 span 대비 자식 span의 비율 분석, (3) 순차 실행되는 호출 체인(병렬화 가능 여부) 확인, (4) 대기 시간(gap)이 긴 구간 식별을 수행합니다. 넓은 막대가 긴 처리 시간을, 연속된 좁은 막대가 순차 호출을 나타냅니다.

</details>

---

5. Grafana에서 Loki 데이터소스에 Tempo로 연결하는 TraceID derived field를 설정하는 방법은?
   - A) Tempo 설정에서 구성한다
   - B) Loki 데이터소스 설정에서 Derived fields를 추가하고, 로그에서 TraceID를 추출하는 정규표현식과 Tempo 데이터소스 링크를 설정한다
   - C) 별도의 플러그인을 설치해야 한다
   - D) 자동으로 설정된다
<details>
<summary>정답 보기</summary>

**정답: B) Loki 데이터소스 설정에서 Derived fields를 추가하고, 로그에서 TraceID를 추출하는 정규표현식과 Tempo 데이터소스 링크를 설정한다**

**설명:**
Grafana의 Loki 데이터소스 설정에서 Derived fields를 구성합니다. Name(예: TraceID), Regex(예: `traceId=(\w+)` 또는 `"trace_id":"([^"]+)"`), Internal link를 활성화하고 Tempo 데이터소스를 선택합니다. 이후 로그 탐색 시 TraceID가 클릭 가능한 링크로 표시되어 해당 트레이스로 바로 이동할 수 있습니다.

</details>

---

6. Tempo에서 Loki로 연결하는 Span → Logs 기능의 동작 방식은?
   - A) Tempo가 자동으로 로그를 생성한다
   - B) 트레이스 뷰에서 span을 선택하면 해당 span의 TraceID, SpanID, 시간 범위를 기반으로 Loki에서 관련 로그를 쿼리한다
   - C) 로그가 Tempo에 저장된다
   - D) 수동으로 로그를 검색해야 한다
<details>
<summary>정답 보기</summary>

**정답: B) 트레이스 뷰에서 span을 선택하면 해당 span의 TraceID, SpanID, 시간 범위를 기반으로 Loki에서 관련 로그를 쿼리한다**

**설명:**
Tempo 데이터소스 설정에서 "Trace to logs" 기능을 활성화하고 Loki 데이터소스를 연결합니다. 트레이스 뷰에서 span을 클릭하면 "Logs for this span" 링크가 표시됩니다. 클릭 시 span의 TraceID, 서비스 이름, 시간 범위를 기반으로 Loki 쿼리가 자동 생성되어 해당 span 실행 중 발생한 로그를 확인할 수 있습니다.

</details>

---

7. Exemplar를 통한 메트릭 → 트레이스 드릴다운 동작 원리로 올바른 것은?
   - A) Exemplar는 로그를 저장한다
   - B) 메트릭 데이터 포인트에 TraceID를 첨부하여, 메트릭 그래프에서 해당 시점의 실제 트레이스로 바로 이동할 수 있게 한다
   - C) Exemplar는 메트릭을 삭제한다
   - D) Grafana에서만 사용할 수 있다
<details>
<summary>정답 보기</summary>

**정답: B) 메트릭 데이터 포인트에 TraceID를 첨부하여, 메트릭 그래프에서 해당 시점의 실제 트레이스로 바로 이동할 수 있게 한다**

**설명:**
Exemplar는 메트릭 샘플에 TraceID를 첨부하는 OpenMetrics 기능입니다. 예를 들어 히스토그램의 특정 버킷에 해당하는 요청의 TraceID가 저장됩니다. Grafana 그래프에서 Exemplar를 활성화하면 데이터 포인트에 작은 마커가 표시되고, 클릭 시 해당 TraceID의 트레이스로 이동합니다. 이를 통해 "p99 지연이 급증한 시점의 실제 요청"을 바로 분석할 수 있습니다.

</details>

---

8. RED 메트릭 대시보드의 Rate, Errors, Duration 각각의 의미는?
   - A) Rate는 CPU 사용률, Errors는 메모리 에러, Duration은 디스크 I/O 시간
   - B) Rate는 초당 요청 수, Errors는 실패한 요청의 비율, Duration은 요청 처리 시간(지연)
   - C) Rate는 네트워크 속도, Errors는 패킷 손실, Duration은 연결 시간
   - D) 세 메트릭은 모두 동일한 의미이다
<details>
<summary>정답 보기</summary>

**정답: B) Rate는 초당 요청 수, Errors는 실패한 요청의 비율, Duration은 요청 처리 시간(지연)**

**설명:**
RED 메트릭은 서비스 수준 모니터링의 표준 프레임워크입니다. Rate(처리량)는 서비스가 처리하는 초당 요청 수로 부하를 나타냅니다. Errors(에러율)는 실패한 요청의 비율(예: 5xx 응답)로 신뢰성을 나타냅니다. Duration(지연)은 요청 처리 시간(보통 p50, p95, p99 백분위수)으로 사용자 경험을 나타냅니다. 이 세 메트릭으로 서비스 건강 상태를 종합적으로 파악합니다.

</details>

---

9. SLI/SLO 대시보드에서 가용성 99.9%와 p99 < 500ms 게이지를 설정하는 방법은?
   - A) 수동으로 값을 입력해야 한다
   - B) 가용성은 성공 요청 비율을 계산하는 PromQL을, p99 지연은 히스토그램 quantile 함수를 사용하여 게이지 패널에 표시한다
   - C) SLO는 설정할 수 없다
   - D) 별도의 SLO 도구를 구매해야 한다
<details>
<summary>정답 보기</summary>

**정답: B) 가용성은 성공 요청 비율을 계산하는 PromQL을, p99 지연은 히스토그램 quantile 함수를 사용하여 게이지 패널에 표시한다**

**설명:**
가용성 SLI는 `sum(rate(http_requests_total{status!~"5.."}[30d])) / sum(rate(http_requests_total[30d])) * 100`으로 계산합니다. p99 지연 SLI는 `histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))`를 사용합니다. Grafana 게이지 패널에서 임계값(99.9%, 500ms)을 설정하고 색상 구간을 정의하면 SLO 달성 여부를 시각적으로 확인할 수 있습니다. 에러 버짓도 함께 표시하면 더욱 효과적입니다.

</details>

---

10. 분산 추적에서 DB 쿼리 Span의 `db.system` 및 `db.statement` 속성 활용 방법은?
    - A) 이 속성들은 보안상 사용하지 않는다
    - B) `db.system`으로 데이터베이스 종류(mysql, postgresql 등)를 식별하고, `db.statement`로 실행된 SQL 쿼리를 확인하여 느린 쿼리를 분석한다
    - C) 이 속성들은 자동으로 생성되지 않는다
    - D) 로그에서만 확인할 수 있다
<details>
<summary>정답 보기</summary>

**정답: B) `db.system`으로 데이터베이스 종류(mysql, postgresql 등)를 식별하고, `db.statement`로 실행된 SQL 쿼리를 확인하여 느린 쿼리를 분석한다**

**설명:**
OpenTelemetry 시맨틱 컨벤션에서 DB span은 표준 속성을 가집니다. `db.system`은 데이터베이스 종류(mysql, postgresql, redis, mongodb 등)를 나타냅니다. `db.statement`는 실행된 쿼리 문자열을 포함합니다. `db.name`은 데이터베이스 이름, `db.operation`은 작업 유형(SELECT, INSERT 등)을 나타냅니다. 트레이스에서 오래 걸린 DB span을 찾고 `db.statement`를 확인하여 최적화가 필요한 쿼리를 식별합니다.

</details>
