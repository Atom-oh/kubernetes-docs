# Prometheus 퀴즈

Prometheus에 대한 이해도를 테스트하는 퀴즈입니다.

---

1. Prometheus의 데이터 수집 방식은?
   - A) Push 기반 - 애플리케이션이 메트릭을 전송
   - B) Pull 기반 - Prometheus가 타겟에서 메트릭을 스크랩
   - C) 스트리밍 기반 - 실시간 데이터 스트림
   - D) 배치 기반 - 주기적 파일 전송

<details>
<summary>정답 보기</summary>

**정답: B) Pull 기반 - Prometheus가 타겟에서 메트릭을 스크랩**

**설명:**
Prometheus는 Pull 기반 메트릭 수집 시스템으로, HTTP를 통해 타겟의 /metrics 엔드포인트에서 주기적으로 메트릭을 스크랩합니다. 이 방식의 장점은 중앙에서 수집 대상과 주기를 제어할 수 있고, 타겟의 가용성을 자동으로 감지할 수 있다는 것입니다.

</details>

---

2. PromQL에서 최근 5분간의 HTTP 요청 rate를 계산하는 올바른 쿼리는?
   - A) `rate(http_requests_total, 5m)`
   - B) `rate(http_requests_total[5m])`
   - C) `increase(http_requests_total[5m])`
   - D) `avg(http_requests_total[5m])`

<details>
<summary>정답 보기</summary>

**정답: B) `rate(http_requests_total[5m])`**

**설명:**
`rate()` 함수는 Counter 메트릭의 초당 평균 증가율을 계산합니다. 범위 벡터는 대괄호 `[]` 안에 시간을 지정합니다. `increase()`는 총 증가량을 반환하고, `avg()`는 평균값을 계산하는 집계 함수입니다. `rate(http_requests_total[5m])`은 5분 동안의 초당 요청 수를 계산합니다.

</details>

---

3. Prometheus Operator에서 ServiceMonitor의 역할은?
   - A) Prometheus 서버를 배포한다
   - B) 알림 규칙을 정의한다
   - C) 모니터링할 서비스와 스크랩 설정을 정의한다
   - D) Grafana 대시보드를 생성한다

<details>
<summary>정답 보기</summary>

**정답: C) 모니터링할 서비스와 스크랩 설정을 정의한다**

**설명:**
ServiceMonitor는 Prometheus Operator의 CRD로, Kubernetes 서비스를 모니터링하기 위한 스크랩 설정을 선언적으로 정의합니다. 대상 서비스 선택자, 엔드포인트, 스크랩 간격, 레이블 재작성 등을 설정할 수 있습니다. PrometheusRule은 알림 규칙을, Prometheus CRD는 서버 배포를 담당합니다.

</details>

---

4. histogram_quantile 함수에 대한 설명으로 올바른 것은?
   - A) Summary 메트릭에서만 사용할 수 있다
   - B) Histogram 버킷에서 분위수를 계산한다
   - C) 정확한 분위수 값을 반환한다
   - D) Counter 메트릭의 변화율을 계산한다

<details>
<summary>정답 보기</summary>

**정답: B) Histogram 버킷에서 분위수를 계산한다**

**설명:**
`histogram_quantile()`은 Histogram 버킷 데이터에서 분위수를 계산합니다. 예를 들어, `histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))`은 p95 지연시간을 계산합니다. 버킷 경계에 따른 근사값을 반환하며, 정확한 분위수를 원하면 Summary를 사용해야 합니다.

</details>

---

5. kube-prometheus-stack Helm 차트에 포함되지 않는 컴포넌트는?
   - A) Prometheus Operator
   - B) Grafana
   - C) VictoriaMetrics
   - D) Alertmanager

<details>
<summary>정답 보기</summary>

**정답: C) VictoriaMetrics**

**설명:**
kube-prometheus-stack은 Prometheus Operator, Prometheus, Alertmanager, Grafana, kube-state-metrics, node-exporter 등을 포함하는 Helm 차트입니다. VictoriaMetrics는 별도의 프로젝트로, victoria-metrics-k8s-stack 차트를 통해 설치합니다.

</details>

---

6. Prometheus에서 Remote Write의 주요 용도는?
   - A) 로컬 스토리지 성능 향상
   - B) 장기 메트릭 저장소로 데이터 전송
   - C) 실시간 알림 전송
   - D) Grafana 대시보드 동기화

<details>
<summary>정답 보기</summary>

**정답: B) 장기 메트릭 저장소로 데이터 전송**

**설명:**
Remote Write는 Prometheus가 수집한 메트릭을 외부 시스템(VictoriaMetrics, Mimir, AMP, Cortex 등)으로 전송하는 기능입니다. Prometheus의 로컬 스토리지는 보존 기간과 확장성에 제한이 있어, 장기 저장이 필요한 경우 Remote Write를 통해 전용 저장소로 데이터를 전송합니다.

</details>

---

7. PrometheusRule CRD에서 `for` 필드의 역할은?
   - A) 규칙 평가 간격 설정
   - B) 알림 발화 전 조건 유지 시간 설정
   - C) 알림 재전송 간격 설정
   - D) 메트릭 보존 기간 설정

<details>
<summary>정답 보기</summary>

**정답: B) 알림 발화 전 조건 유지 시간 설정**

**설명:**
PrometheusRule의 `for` 필드는 알림 조건이 충족된 후 실제로 알림이 발화되기까지 대기하는 시간을 설정합니다. 예를 들어, `for: 5m`은 조건이 5분 동안 지속되어야 알림이 발화됩니다. 이를 통해 일시적인 스파이크로 인한 불필요한 알림을 방지할 수 있습니다.

</details>

---

8. PromQL에서 `predict_linear` 함수의 용도는?
   - A) 현재 값의 절대값 계산
   - B) 선형 회귀 기반 미래 값 예측
   - C) 시계열 데이터 정렬
   - D) 레이블 값 변환

<details>
<summary>정답 보기</summary>

**정답: B) 선형 회귀 기반 미래 값 예측**

**설명:**
`predict_linear(v range-vector, t scalar)`는 선형 회귀를 사용하여 미래 값을 예측합니다. 예를 들어, `predict_linear(node_filesystem_avail_bytes[6h], 24*60*60) < 0`은 현재 추세로 24시간 후 디스크 공간이 소진될지 예측합니다. 용량 계획과 사전 경고에 유용합니다.

</details>

---

9. Alertmanager의 `groupBy` 설정의 역할은?
   - A) 알림을 특정 그룹에만 전송
   - B) 알림을 지정된 레이블로 그룹화
   - C) 알림 우선순위 설정
   - D) 알림 중복 제거

<details>
<summary>정답 보기</summary>

**정답: B) 알림을 지정된 레이블로 그룹화**

**설명:**
`groupBy`는 알림을 지정된 레이블 기준으로 그룹화하여 하나의 알림으로 묶어 전송합니다. 예를 들어, `groupBy: ['alertname', 'namespace']`는 같은 alertname과 namespace를 가진 알림을 그룹화합니다. 이를 통해 알림 폭주를 방지하고 관련 알림을 함께 확인할 수 있습니다.

</details>

---

10. Prometheus TSDB에서 WAL(Write-Ahead Log)의 역할은?
    - A) 쿼리 캐싱
    - B) 데이터 손실 방지를 위한 선행 기록
    - C) 알림 히스토리 저장
    - D) 대시보드 설정 저장

<details>
<summary>정답 보기</summary>

**정답: B) 데이터 손실 방지를 위한 선행 기록**

**설명:**
WAL(Write-Ahead Log)은 데이터가 메모리에서 디스크 블록으로 완전히 기록되기 전에 먼저 순차적으로 기록되는 로그입니다. Prometheus가 비정상 종료되어도 WAL을 통해 데이터를 복구할 수 있어 데이터 손실을 방지합니다. 이는 데이터베이스에서 일반적으로 사용되는 내구성 보장 메커니즘입니다.

</details>
