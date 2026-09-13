# Observability Lab Part 6 퀴즈

> **마지막 업데이트**: 2026년 9월 13일

1. 전체 trace 시간과 개별 span 시간은 어떻게 구분하는가?
   - A) 둘 다 항상 같은 값
   - B) trace:duration과 span:duration
   - C) span.duration은 항상 intrinsic이다
   - D) 로그 줄 수로 계산한다

<details>
<summary>정답 보기</summary>

**정답: B) trace:duration과 span:duration**

명시적인 intrinsic은 콜론을 사용하며 span.은 속성 scope입니다.

</details>

---

2. 현재 HTTP 서버 오류 속성 query는?
   - A) { order by status desc }
   - B) { span.http.response.status_code >= 500 }
   - C) { duration > p99 }
   - D) { select 500 }

<details>
<summary>정답 보기</summary>

**정답: B) { span.http.response.status_code >= 500 }**

SDK가 이전 http.status_code를 보내면 실제 데이터를 확인하고 구버전 query를 별도로 사용합니다.

</details>

---

3. A >> B는 무엇을 찾는가?
   - A) A 이전 시간의 모든 로그
   - B) A span의 descendant인 B span
   - C) A와 B의 평균
   - D) B의 부모가 무조건 A와 같은 span

<details>
<summary>정답 보기</summary>

**정답: B) A span의 descendant인 B span**

서비스 아래 DB 작업을 찾을 때 서비스 selector를 왼쪽, DB selector를 오른쪽에 둡니다.

</details>

---

4. 문서의 SQL식 order by/limit를 대체하는 방법은?
   - A) 그대로 실행
   - B) 유효한 TraceQL과 Grafana 검색 정렬·limit 설정
   - C) Prometheus에 보내기
   - D) DB 비밀번호를 query에 추가

<details>
<summary>정답 보기</summary>

**정답: B) 유효한 TraceQL과 Grafana 검색 정렬·limit 설정**

Tempo3.0.3 실제 parser는 이전 sort/order by/limit 예제를 거부합니다.

</details>

---

5. Service graph에 필요한 것은?
   - A) Tempo 설치만
   - B) 연결된 span, service-graphs processor, metrics 저장소, datasource 연결
   - C) trace ID를 로그 label로만 저장
   - D) 수동으로 빨간 노드 그리기

<details>
<summary>정답 보기</summary>

**정답: B) 연결된 span, service-graphs processor, metrics 저장소, datasource 연결**

ingestion과 graph용 metrics 전달을 따로 검증해야 합니다.

</details>

---

6. 1.8초 DB span에서 바로 확정할 수 있는 것은?
   - A) 인덱스가 반드시 없다
   - B) 관측한 작업 시간이 길다는 사실; 원인은 추가 증거가 필요
   - C) 네트워크는 정상이다
   - D) 부모 span과 시간을 모두 합해도 된다

<details>
<summary>정답 보기</summary>

**정답: B) 관측한 작업 시간이 길다는 사실; 원인은 추가 증거가 필요**

lock·pool·네트워크·query plan 등을 확인하고 겹친 span의 이중 계산을 피합니다.

</details>

---

7. Grafana provisioning의 derived field link 표현식은?
   - A) 모든 $ 변수를 envsubst로 제거
   - B) $${__value.raw}로 provisioning 치환을 escape
   - C) trace ID를 모든 stream label에 추가
   - D) 시간 범위를 LogQL SQL절로 추가

<details>
<summary>정답 보기</summary>

**정답: B) $${__value.raw}로 provisioning 치환을 escape**

실제 trace ID 필드명·datasource UID도 일치해야 합니다.

</details>

---

8. Exemplar로 이동한 요청은?
   - A) 반드시 정확한 p99 경계 요청
   - B) 집계에 연결된 대표 관측값이며 trace가 보존되어 있어야 한다
   - C) 모든 요청의 복사본
   - D) trace sampling과 무관하게 항상 조회 가능

<details>
<summary>정답 보기</summary>

**정답: B) 집계에 연결된 대표 관측값이며 trace가 보존되어 있어야 한다**

sampling·retention 때문에 exemplar ID와 trace availability가 다를 수 있습니다.

</details>

---

9. 실습 첫날의 [30d] query가 증명하는 것은?
   - A) 30일 SLO 달성
   - B) 실제 존재하는 관측값만 집계하며 30일 기록을 만들지 않는다
   - C) 100% availability
   - D) error budget이 무한대

<details>
<summary>정답 보기</summary>

**정답: B) 실제 존재하는 관측값만 집계하며 30일 기록을 만들지 않는다**

기간·분모·missing/no-traffic를 함께 기록합니다.

</details>

---

10. 현재 DB 속성과 데이터 보호의 올바른 조합은?
   - A) db.statement가 영원히 유일한 표준
   - B) db.system.name/db.query.text를 실제 SDK 기준으로 확인하고 query를 sanitize
   - C) 비밀번호까지 전부 저장
   - D) 속성 이름만 바꾸면 모든 구버전 데이터도 바뀐다

<details>
<summary>정답 보기</summary>

**정답: B) db.system.name/db.query.text를 실제 SDK 기준으로 확인하고 query를 sanitize**

구버전 속성은 여전히 데이터에 존재할 수 있으며 migration과 민감정보 처리는 별도입니다.

</details>

---

[본문으로 돌아가기](../../../labs/observability/06-distributed-tracing-lab.md)
