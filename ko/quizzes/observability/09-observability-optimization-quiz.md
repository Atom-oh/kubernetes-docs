# 관측성 최적화 퀴즈

> **검증 예제 버전**: Prometheus 3.14.0 · OTel Collector Contrib 0.160.0

> **마지막 업데이트**: 2026년 9월 13일

이 퀴즈는 EKS 관측성 최적화 가이드에 대한 이해도를 테스트합니다. 로깅, 메트릭, 트레이싱의 3대 축과 eBPF 기반 모니터링, 비용 최적화 전략을 다룹니다.

---

## 객관식 문제

1. 관측성 3대 축 중 "왜 느린가?"라는 질문에 가장 적합한 데이터 유형은?
   - A) 로깅 (Logging)
   - B) 메트릭 (Metrics)
   - C) 트레이싱 (Tracing)
   - D) 이벤트 (Events)

<details>
<summary>정답 보기</summary>

**정답: C) 트레이싱 (Tracing)**

**설명:**
관측성의 3대 축은 각각 다른 유형의 질문에 답합니다. 로깅은 "무엇이 일어났나?"에, 메트릭은 "시스템이 정상인가?"에, 트레이싱은 "왜 느린가?"에 답합니다. 트레이싱은 요청 흐름을 추적하여 인과관계를 파악하고 병목 지점을 분석하는 데 최적화되어 있습니다. 분산 시스템에서 여러 서비스를 거치는 요청의 지연 시간을 분석할 때 트레이싱이 필수적입니다.

</details>

2. 로그 저장소 중 레이블 기반 빠른 필터링이 강점이며 오브젝트 스토리지(S3)를 활용하여 비용 효율이 높은 솔루션은?
   - A) CloudWatch Logs
   - B) OpenSearch
   - C) Loki
   - D) ClickHouse

<details>
<summary>정답 보기</summary>

**정답: C) Loki**

**설명:**
Loki는 라벨 기반 인덱스와 오브젝트 스토리지를 사용하지만 실제 비용에는 compute·cache·object request·조회·운영이 포함됩니다. Region·수집량·보존·가용성 요구를 맞춰 비교하며 S3 저장 단가만으로 전체 비용이 저렴하다고 단정하지 않습니다.

</details>

3. C 언어로 작성되었으며 EKS의 로그 수집에 사용할 수 있는 에이전트는?
   - A) Fluentd
   - B) Fluent Bit
   - C) Vector
   - D) Logstash

<details>
<summary>정답 보기</summary>

**정답: B) Fluent Bit**

**설명:**
Fluent Bit은 C 기반 수집기이며 AWS 배포에도 사용할 수 있습니다. 메모리와 처리량은 버전·parser·record 크기·buffering·하드웨어에 따라 달라지므로 고정된 15 MB 또는 200K msg/s를 보장하지 않습니다.

</details>

4. Prometheus에서 카디널리티(Cardinality) 폭발의 주요 원인으로 올바른 것은?
   - A) 스크랩 간격이 너무 길 때
   - B) Pod UID나 타임스탬프를 레이블로 사용할 때
   - C) Recording Rules를 너무 많이 사용할 때
   - D) Remote Write를 활성화할 때

<details>
<summary>정답 보기</summary>

**정답: B) Pod UID나 타임스탬프를 레이블로 사용할 때**

**설명:**
요청 ID·timestamp 등 계속 달라지는 라벨은 시계열을 증가시킵니다. 원천에서 제한하고 남은 라벨의 고유성을 검증합니다. labeldrop은 집계가 아니므로 중복 시계열을 만들 수 있고 relabel_configs와 metric_relabel_configs의 처리 시점도 다릅니다.

</details>

5. OpenTelemetry Collector의 Tail Sampling 전략에서 수신한 trace에서 ERROR 상태 span을 선택하는 정책 유형은?
   - A) probabilistic
   - B) latency
   - C) status_code
   - D) string_attribute

<details>
<summary>정답 보기</summary>

**정답: C) status_code**

**설명:**
status_code의 ERROR 정책은 sampler가 수신한 오류 span을 기준으로 선택합니다. 같은 trace의 affinity, decision_wait, buffer, 늦은 span, 상위 단계의 head sampling 때문에 모든 오류 요청이 반드시 보존되는 것은 아닙니다.

</details>

6. eBPF 기반 모니터링의 가장 큰 장점은?
   - A) 더 많은 메트릭 유형을 수집할 수 있다
   - B) 코드 수정 없이 애플리케이션을 계측할 수 있다
   - C) 메트릭 저장 비용이 절감된다
   - D) 쿼리 성능이 향상된다

<details>
<summary>정답 보기</summary>

**정답: B) 코드 수정 없이 애플리케이션을 계측할 수 있다**

**설명:**
지원 kernel·runtime·protocol에서는 소스 변경을 줄일 수 있습니다. 모든 언어·TLS 라이브러리·업무 span을 동일하게 관찰하는 것은 아닙니다. 권한·overhead·민감 payload를 검토하며 SDK 자동 계측도 소스 변경 없이 사용할 수 있는 경우가 있습니다.

</details>

7. Cilium Hubble의 주요 용도로 올바른 것은?
   - A) 컨테이너 리소스 사용량 모니터링
   - B) 네트워크 흐름 관찰 및 분석
   - C) 로그 수집 및 저장
   - D) 분산 트레이싱 백엔드

<details>
<summary>정답 보기</summary>

**정답: B) 네트워크 흐름 관찰 및 분석**

**설명:**
Hubble은 호환되는 Cilium 환경의 네트워크 flow를 관찰합니다. L7 가시성은 지원 protocol과 proxy/policy 설정 등에 따라 달라집니다. 모든 flow나 앱 분산 추적을 보장하지 않으며 실제 기능 범위를 확인합니다.

</details>

8. Kepler(Kubernetes Efficient Power Level Exporter)가 측정하는 주요 지표는?
   - A) CPU 온도
   - B) 네트워크 대역폭
   - C) 에너지(줄)와 전력(와트)
   - D) 디스크 I/O 대기 시간

<details>
<summary>정답 보기</summary>

**정답: C) 에너지(줄)와 전력(와트)**

**설명:**
Kepler 0.10+의 구조와 metric은 과거 0.7과 다릅니다. 0.11.4의 kepler_pod_cpu_watts는 전력 gauge이고 kepler_pod_cpu_joules_total의 rate는 J/s=W입니다. 1000을 곱하면 mW이며 host hardware 접근과 attribution 지원을 확인해야 합니다.

</details>

9. OpenCost/KubeCost에서 팀별 비용 추적을 위해 권장되는 방법은?
   - A) 팀별로 별도의 Kubernetes 클러스터 생성
   - B) 네임스페이스와 Pod에 cost-center, team 등의 레이블 표준화
   - C) 각 팀에 별도의 AWS 계정 할당
   - D) 리소스 쿼터(ResourceQuota)만 설정

<details>
<summary>정답 보기</summary>

**정답: B) 네임스페이스와 Pod에 cost-center, team 등의 레이블 표준화**

**설명:**
OpenCost는 Kubernetes 레이블을 기반으로 비용을 할당합니다. 네임스페이스와 Pod에 `cost-center`, `team`, `environment` 등의 레이블을 일관되게 적용하면, OpenCost API를 통해 `aggregate=label:team`과 같이 팀별 비용을 조회할 수 있습니다. 이 방식은 기존 클러스터 구조를 유지하면서 세밀한 비용 분석과 차지백(chargeback)을 가능하게 합니다.

</details>

10. SLO(Service Level Objective) 기반 모니터링에서 "에러 버짓(Error Budget)"의 의미는?
    - A) 모니터링 시스템 운영에 할당된 예산
    - B) SLO 목표를 벗어나도 허용되는 오류의 양
    - C) 알림 발송에 드는 비용
    - D) 로그 저장에 사용할 수 있는 스토리지 용량

<details>
<summary>정답 보기</summary>

**정답: B) SLO 목표를 벗어나도 허용되는 오류의 양**

**설명:**
요청 기반 99.9% SLO의 허용 오류는 정의한 기간의 전체 요청×0.001입니다. 시간 기반 SLI의 downtime과 혼동하지 않습니다. 30일 잔여 버짓에는 30일 요청 가중 오류율이 필요하며 최근 5분 ratio로 대체할 수 없습니다.

</details>

---

## 단답형 문제

1. Prometheus에서 복잡한 쿼리를 미리 계산하여 저장함으로써 대시보드 쿼리 성능을 개선하는 기능의 이름은 무엇인가요?

<details>
<summary>정답 보기</summary>

**정답:** Recording Rules (레코딩 룰)

**설명:**
Recording Rules는 PromQL 표현식을 주기적으로 평가하여 결과를 새로운 시계열로 저장합니다. 예를 들어 `record: node:cpu_utilization:ratio`로 노드별 CPU 사용률을 미리 계산해 두면, 대시보드에서 복잡한 쿼리를 실행하는 대신 이 메트릭을 직접 조회하여 빠른 응답을 받을 수 있습니다. PrometheusRule CRD의 `record` 필드를 사용하여 정의합니다.

</details>

2. OpenTelemetry에서 일정 시간 수신한 span을 모아 요청 결과에 따라 샘플링하는 방식을 무엇이라고 하나요?

<details>
<summary>정답 보기</summary>

**정답:** Tail Sampling (테일 샘플링)

**설명:**
기본 trace-complete 모드는 decision_wait 동안 수신한 span으로 결정합니다. 모든 span의 도착이나 요청 완료를 보증하지 않으므로 trace ID affinity·buffer·late span·재시작·상위 sampling을 함께 검토합니다.

</details>

3. 메트릭 데이터 포인트에 트레이스 ID를 연결하여 메트릭에서 트레이스로 직접 이동할 수 있게 하는 Prometheus의 기능은 무엇인가요?

<details>
<summary>정답 보기</summary>

**정답:** Exemplars (익젬플러)

**설명:**
Exemplars는 메트릭 샘플에 추가 컨텍스트(주로 traceID)를 첨부하는 기능입니다. 히스토그램이나 카운터 메트릭에 exemplar를 추가하면, Grafana에서 메트릭 그래프의 특정 지점을 클릭하여 해당 시점의 트레이스로 바로 이동할 수 있습니다. 이를 통해 "이 시점에 지연 시간이 급증한 이유"를 트레이스에서 분석할 수 있어 관측성 데이터 간의 상관관계 분석이 용이해집니다.

</details>

4. VictoriaMetrics 클러스터 모드에서 메트릭 데이터 저장을 담당하는 구성 요소의 이름은 무엇인가요?

<details>
<summary>정답 보기</summary>

**정답:** vmstorage

**설명:**
vmstorage가 저장을 담당합니다. 여러 인스턴스를 만드는 것만으로 자동 복제가 완성되지는 않으며 replication factor, vminsert/vmselect 설정, query 중복 제거, 실패 시 동작을 맞춰 검증해야 합니다.

</details>

5. 로그/메트릭 저장 비용을 절감하기 위해 오래된 데이터를 S3 Glacier와 같은 저비용 스토리지로 이동하는 전략을 무엇이라고 하나요?

<details>
<summary>정답 보기</summary>

**정답:** Tiered Storage (계층화 저장) 또는 계층형 스토리지

**설명:**
계층화는 접근 빈도·복구 시간·보존 요구를 기준으로 합니다. Loki/Tempo 활성 block을 Glacier로 이동하면 조회가 깨질 수 있어 backend 호환성과 복구를 검증하거나 별도 아카이브를 설계합니다. 고정 절감률을 보장하지 않습니다.

</details>

---

## 실습 문제

1. Fluent Bit에서 DEBUG와 TRACE 레벨 로그를 필터링하여 제외하는 설정을 작성하세요.

<details>
<summary>정답 보기</summary>

**정답:**
```ini
[FILTER]
    Name     grep
    Match    *
    Exclude  level ^(DEBUG|TRACE)$
```

**설명:**
파싱된 level 필드에 ^(DEBUG|TRACE)$를 적용하면 임의 본문의 단어로 중요한 로그를 지우는 일을 피할 수 있습니다. 실제 drop과 장애 조사 영향을 측정하며 일정한 40~60% 절감을 보장하지 않습니다.

</details>

2. 서비스별 HTTP 에러율이 5%를 초과하고 5분 동안 지속될 때 경고를 발생시키는 PrometheusRule을 작성하세요.

<details>
<summary>정답 보기</summary>

**정답:**
```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: http-error-rate-alert
  namespace: monitoring
spec:
  groups:
    - name: slo.alerts
      rules:
        - alert: HighHTTPErrorRate
          expr: |
            sum by (service) (
              rate(http_requests_total{status=~"5.."}[5m])
            )
            /
            sum by (service) (
              rate(http_requests_total[5m])
            )
            > 0.05
          for: 5m
          labels:
            severity: warning
          annotations:
            summary: "서비스 {{ $labels.service }}의 HTTP 에러율이 5%를 초과했습니다"
            description: "현재 에러율: {{ $value | humanizePercentage }}"
```

**설명:**
이 알림 규칙은 서비스별로 5XX 상태 코드 비율을 계산합니다. `status=~"5.."`는 정규표현식으로 500-599 상태 코드를 매칭합니다. `for: 5m`은 조건이 5분간 지속될 때만 알림을 발생시켜 일시적 스파이크로 인한 거짓 알림을 방지합니다. `sum by (service)`를 사용하여 각 서비스별로 독립적인 알림이 발생합니다.

</details>

3. OpenTelemetry Collector에서 에러 트레이스는 100%, 1초 초과 지연된 트레이스는 100%, 나머지는 10%만 샘플링하는 tail_sampling 프로세서 설정을 작성하세요.

<details>
<summary>정답 보기</summary>

**정답:**
```yaml
processors:
  tail_sampling:
    decision_wait: 2s
    num_traces: 1000
    maximum_trace_size_bytes: 1048576
    policies:
    - name: errors
      type: status_code
      status_code:
        status_codes:
        - ERROR
    - name: slow
      type: latency
      latency:
        threshold_ms: 1000
    - name: baseline
      type: probabilistic
      probabilistic:
        sampling_percentage: 10
```

**설명:**
이 positive policy 조합은 수신한 오류·느린 trace를 유지하고 나머지에 확률 정책을 적용합니다. Buffer·affinity·late span 제한은 남습니다. 전체 중 오류·느린 trace 비중에 따라 보존율이 달라지므로 90% 절감을 단정하지 않습니다. Drop/composite 정책까지 첫 일치 규칙으로 일반화하지 않습니다.

</details>

---

## 심화 문제

1. 대규모 EKS 클러스터(500+ 노드)에서 관측성 스택의 고가용성을 확보하기 위한 아키텍처를 설계하세요. 수집, 저장, 쿼리 계층별로 어떤 구성 요소를 어떻게 배치해야 하는지 설명하세요.

<details>
<summary>정답 보기</summary>

**정답:**

노드 수만으로 replica 수를 결정하지 않습니다. 노드 로그 agent와 gateway를 분리하고 tail sampling에는 trace ID affinity를 적용합니다. 수집 buffer·backpressure와 장애 시 drop을 측정합니다. 현재 Loki/Tempo 모드의 복제·quorum·AZ 조건, VictoriaMetrics의 명시적 replication과 query 중복 제거, AMP quota·retention을 확인합니다. Prometheus replicas×shards만큼 PVC·메모리를 배정하고 shard query를 병합합니다. Grafana는 공유 PostgreSQL/MySQL과 별도 Alerting HA를 구성하며 쿼리 cache는 지원 edition을 확인합니다. PDB나 S3 내구성만으로 전체 가용성을 보장하지 않고 각 계층의 실패·복구를 시험합니다.

</details>

2. 월 $5,000의 관측성 비용이 발생하는 환경에서 품질을 유지하면서 50% 비용 절감을 달성하기 위한 최적화 전략을 제시하세요. 로깅, 메트릭, 트레이싱 각 영역별로 구체적인 방법을 설명하세요.

<details>
<summary>정답 보기</summary>

**정답:**

월 $5,000과 50% 절감은 이 문제의 가상 기준과 목표입니다. 실제 수집·저장·scan·compute·운영 비용으로 나누어 상위 항목부터 개선합니다. 파싱된 로그 level 필터, 요청 단위 확률 sampling, 안전한 metric/bucket 관리, tail sampling, 보존 기간을 각각 작은 범위에서 시험합니다. Throttle은 10% sampler가 아니고 recording rule 자체가 원본 보존 정책을 바꾸지 않습니다. 같은 Region·가용성·쿼리·retention을 갖춘 전체 비용으로 저장소를 비교합니다. 절감률은 서로 중첩되므로 합산하지 말고 전후 청구액·수집 손실·SLO coverage·장애 조사 성공률로 판단합니다. 목표 달성을 보장할 수 없다면 데이터와 다음 실험을 제시합니다.

</details>

---

**점수 계산:**
- 18-20개 정답: 우수 (관측성 전문가 수준)
- 14-17개 정답: 양호 (실무 적용 가능)
- 10-13개 정답: 보통 (추가 학습 권장)
- 6-9개 정답: 기초 (기본 개념 복습 필요)
- 0-5개 정답: 미흡 (전체 내용 재학습 필요)

---

**관련 학습 자료:**
- [EKS 관측성 최적화 가이드](../../observability/09-observability-optimization.md)
