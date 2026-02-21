# Observability 분석 방법 퀴즈

> **관련 문서**: [Observability 분석 방법](../../ops/08-observability-analysis.md)

## 객관식 문제

### 1. Loki LogQL에서 로그 라인에서 특정 패턴을 추출하기 위해 사용하는 파서는 무엇인가요?

- A) rate()
- B) json, logfmt, pattern, regexp
- C) sum()
- D) histogram_quantile()

<details>
<summary>정답 보기</summary>

**정답: B) json, logfmt, pattern, regexp**

**설명:**
LogQL에서 로그 라인에서 데이터를 추출하기 위해 다양한 파서를 사용합니다. `| json`은 JSON 로그를, `| logfmt`는 key=value 형식을, `| pattern`은 패턴 매칭을, `| regexp`는 정규표현식을 사용합니다. 추출된 레이블은 필터링이나 집계에 사용할 수 있습니다.

</details>

### 2. Tempo에서 Trace ID를 기반으로 특정 트레이스를 조회할 때 사용하는 TraceQL 구문은 무엇인가요?

- A) {span.trace_id="..."}
- B) trace:ID
- C) 직접 Trace ID를 검색창에 입력
- D) SELECT * FROM traces WHERE id="..."

<details>
<summary>정답 보기</summary>

**정답: C) 직접 Trace ID를 검색창에 입력**

**설명:**
Grafana Tempo에서 특정 트레이스를 조회할 때는 Trace ID를 검색창에 직접 입력합니다. TraceQL은 트레이스 검색과 필터링에 사용되지만, 특정 ID로 조회할 때는 ID를 직접 입력하는 것이 가장 간단합니다. Tempo UI나 Grafana Explore에서 지원됩니다.

</details>

### 3. Prometheus에서 RPS(Requests Per Second)를 계산하기 위한 PromQL 함수는 무엇인가요?

- A) count()
- B) rate() 또는 irate()
- C) sum()
- D) avg()

<details>
<summary>정답 보기</summary>

**정답: B) rate() 또는 irate()**

**설명:**
rate() 함수는 지정된 시간 범위에서 카운터 메트릭의 초당 평균 증가율을 계산합니다. 예: `rate(http_requests_total[5m])`는 5분 동안의 평균 RPS입니다. irate()는 마지막 두 데이터 포인트만 사용하여 순간 변화율을 계산하며 더 민감합니다.

</details>

### 4. 로그, 메트릭, 트레이스를 연결하여 분석할 때 공통으로 사용되는 식별자는 무엇인가요?

- A) Pod Name
- B) Trace ID
- C) Namespace
- D) Container ID

<details>
<summary>정답 보기</summary>

**정답: B) Trace ID**

**설명:**
Trace ID는 분산 시스템에서 하나의 요청이 여러 서비스를 거치는 동안 동일하게 전파됩니다. 로그에 Trace ID를 포함시키면 해당 요청의 로그만 필터링할 수 있고, Prometheus Exemplar를 통해 메트릭에서 트레이스로 연결할 수 있습니다.

</details>

### 5. LogQL에서 시간당 에러 로그 수를 계산하는 쿼리의 올바른 형태는 무엇인가요?

- A) {app="myapp"} |= "error"
- B) count_over_time({app="myapp"} |= "error" [1h])
- C) rate({app="myapp"} |= "error")
- D) sum({app="myapp"} |= "error")

<details>
<summary>정답 보기</summary>

**정답: B) count_over_time({app="myapp"} |= "error" [1h])**

**설명:**
`count_over_time()`은 지정된 시간 범위 내의 로그 라인 수를 계산합니다. `{app="myapp"} |= "error" [1h]`는 1시간 동안 "error"를 포함하는 로그를 선택하고, count_over_time이 그 수를 반환합니다. 이를 통해 에러 발생 추이를 파악할 수 있습니다.

</details>

### 6. Prometheus Exemplar의 주요 용도는 무엇인가요?

- A) 메트릭 저장 최적화
- B) 메트릭 데이터 포인트에 Trace ID를 연결하여 트레이스로 이동
- C) 알림 전송
- D) 메트릭 집계

<details>
<summary>정답 보기</summary>

**정답: B) 메트릭 데이터 포인트에 Trace ID를 연결하여 트레이스로 이동**

**설명:**
Exemplar는 히스토그램이나 카운터 메트릭의 특정 데이터 포인트에 샘플 Trace ID를 첨부합니다. Grafana에서 메트릭 그래프의 특정 지점을 클릭하면 해당 시점의 실제 요청 트레이스로 바로 이동할 수 있어 문제 원인 분석이 빨라집니다.

</details>

### 7. TraceQL에서 특정 서비스의 500 에러 트레이스를 찾는 쿼리는 무엇인가요?

- A) {status=error}
- B) {resource.service.name="api" && status=error}
- C) SELECT * FROM traces WHERE error=true
- D) error:500

<details>
<summary>정답 보기</summary>

**정답: B) {resource.service.name="api" && status=error}**

**설명:**
TraceQL에서 `{}`안에 조건을 지정합니다. `resource.service.name`은 서비스 이름을, `status=error`는 에러 상태를 필터링합니다. `&&`로 여러 조건을 AND 결합할 수 있습니다. 이를 통해 특정 서비스의 에러 트레이스만 효과적으로 찾을 수 있습니다.

</details>

### 8. RED Method에서 R, E, D는 각각 무엇을 의미하나요?

- A) Reliability, Efficiency, Durability
- B) Rate, Errors, Duration
- C) Request, Event, Data
- D) Read, Execute, Delete

<details>
<summary>정답 보기</summary>

**정답: B) Rate, Errors, Duration**

**설명:**
RED Method는 서비스 모니터링의 핵심 지표입니다. Rate(초당 요청 수), Errors(에러 비율), Duration(응답 시간/지연)을 측정합니다. 이 세 가지 지표로 서비스의 전반적인 상태를 파악할 수 있으며, 마이크로서비스 환경에서 널리 사용됩니다.

</details>

### 9. Grafana에서 로그와 메트릭을 같은 대시보드에서 연관 분석할 때 사용하는 기능은 무엇인가요?

- A) Alerting
- B) Data Link 또는 Explore
- C) Provisioning
- D) Annotation

<details>
<summary>정답 보기</summary>

**정답: B) Data Link 또는 Explore**

**설명:**
Grafana의 Data Link 기능을 사용하면 메트릭 패널에서 특정 시점을 클릭했을 때 해당 시간대의 로그를 Loki에서 조회하도록 연결할 수 있습니다. Explore 모드에서는 메트릭, 로그, 트레이스를 동시에 조회하고 시간을 동기화하여 연관 분석이 가능합니다.

</details>

### 10. USE Method에서 U, S, E는 각각 무엇을 의미하나요?

- A) Update, Select, Execute
- B) Utilization, Saturation, Errors
- C) User, System, Environment
- D) Upload, Storage, Event

<details>
<summary>정답 보기</summary>

**정답: B) Utilization, Saturation, Errors**

**설명:**
USE Method는 리소스 모니터링 방법론입니다. Utilization(사용률: 리소스가 얼마나 사용되는지), Saturation(포화도: 대기열 길이나 지연), Errors(에러: 에러 이벤트 수)를 측정합니다. CPU, 메모리, 디스크, 네트워크 같은 시스템 리소스 분석에 효과적입니다.

</details>
