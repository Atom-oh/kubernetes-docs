# 관측성 최적화 퀴즈

> **지원 버전**: Amazon EKS 1.29+, OpenTelemetry 0.90+
> **마지막 업데이트**: 2026년 2월 22일

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
Grafana Loki는 레이블 기반 인덱싱을 사용하여 전문 검색 인덱스 없이도 빠른 필터링을 제공합니다. 로그 데이터를 S3와 같은 오브젝트 스토리지에 저장하므로 저장 비용이 매우 저렴합니다(S3: $0.023/GB/월). OpenSearch는 전문 검색에 강하지만 인덱스 스토리지 비용이 높고, CloudWatch Logs는 수집 비용($0.50/GB)이 상대적으로 높습니다.

</details>

3. 로그 에이전트 중 메모리 사용량이 가장 적고 C 언어로 작성되어 EKS에서 네이티브로 지원되는 것은?
   - A) Fluentd
   - B) Fluent Bit
   - C) Vector
   - D) Logstash

<details>
<summary>정답 보기</summary>

**정답: B) Fluent Bit**

**설명:**
Fluent Bit은 C 언어로 작성되어 약 15MB의 매우 적은 메모리를 사용합니다. Fluentd(~60MB, Ruby/C)나 Vector(~30MB, Rust)에 비해 가볍고, 최대 ~200K msg/s의 높은 처리량을 제공합니다. AWS는 Fluent Bit을 EKS용 로그 수집기로 공식 권장하며, aws-for-fluent-bit 이미지를 제공합니다.

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
카디널리티는 고유한 시계열(time series)의 수를 의미합니다. Pod UID, 타임스탬프, 요청 ID 등 고유한 값을 레이블로 사용하면 레이블 조합이 무한히 증가하여 시계열 수가 폭발적으로 늘어납니다. 이는 Prometheus의 메모리 사용량 급증과 쿼리 성능 저하를 유발합니다. relabel_configs에서 pod_template_hash, controller_revision_hash 같은 레이블을 제거하는 것이 권장됩니다.

</details>

5. OpenTelemetry Collector의 Tail Sampling 전략에서 에러가 있는 트레이스를 100% 유지하는 정책 유형은?
   - A) probabilistic
   - B) latency
   - C) status_code
   - D) string_attribute

<details>
<summary>정답 보기</summary>

**정답: C) status_code**

**설명:**
Tail Sampling은 트레이스가 완료된 후 전체 트레이스 정보를 기반으로 샘플링 결정을 내립니다. `status_code` 정책은 트레이스의 상태 코드(OK, ERROR)를 기준으로 샘플링합니다. `status_codes: [ERROR]`로 설정하면 에러가 포함된 트레이스를 100% 유지합니다. 이는 문제 분석에 중요한 트레이스를 놓치지 않으면서 전체 데이터 볼륨을 줄이는 효과적인 전략입니다.

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
eBPF(extended Berkeley Packet Filter)는 리눅스 커널에서 안전하게 프로그램을 실행하여 시스템 호출, 네트워크 패킷 등을 관찰합니다. 전통적인 계측 방식은 SDK 추가와 코드 수정, 재배포가 필요하지만, eBPF는 커널 레벨에서 투명하게 동작하므로 애플리케이션 변경 없이 모니터링이 가능합니다. 또한 언어 종속성이 없어 어떤 언어로 작성된 애플리케이션이든 동일하게 계측됩니다.

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
Cilium Hubble은 eBPF 기반 CNI인 Cilium의 관측성 컴포넌트입니다. Hubble은 클러스터 내 모든 네트워크 흐름을 실시간으로 관찰하며, DNS 요청, TCP 연결, HTTP 트래픽 등을 분석합니다. `hubble observe` 명령으로 특정 서비스로의 트래픽을 필터링하거나 드롭된 패킷을 분석할 수 있습니다. 서비스 맵 시각화와 네트워크 정책 검증에 유용합니다.

</details>

8. Kepler(Kubernetes Efficient Power Level Exporter)가 측정하는 주요 지표는?
   - A) CPU 온도
   - B) 네트워크 대역폭
   - C) 에너지 소비량(줄/와트)
   - D) 디스크 I/O 대기 시간

<details>
<summary>정답 보기</summary>

**정답: C) 에너지 소비량(줄/와트)**

**설명:**
Kepler는 eBPF를 사용하여 컨테이너와 Pod의 에너지 소비를 측정하는 CNCF 프로젝트입니다. `kepler_container_joules_total` 메트릭으로 에너지 소비량(줄)을, `rate(kepler_container_joules_total[5m]) * 1000`으로 전력 소비(와트)를 계산할 수 있습니다. 이를 통해 네임스페이스나 Pod별 에너지 사용량을 분석하고 친환경 컴퓨팅 목표를 달성하는 데 활용합니다.

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
에러 버짓은 SLO에서 파생되는 개념으로, 허용되는 오류의 총량입니다. 예를 들어 99.9% 가용성 SLO는 0.1%의 에러 버짓을 의미합니다. 30일 기준으로 약 43분의 다운타임이 허용됩니다. 에러 버짓이 소진되면 새로운 기능 배포를 중단하고 안정성 개선에 집중해야 합니다. `1 - (1 - sli:availability:ratio) / (1 - 0.999)` 표현식으로 남은 에러 버짓 비율을 계산합니다.

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

2. OpenTelemetry에서 트레이스가 완료된 후 전체 트레이스 정보를 기반으로 샘플링 결정을 내리는 방식을 무엇이라고 하나요?

<details>
<summary>정답 보기</summary>

**정답:** Tail Sampling (테일 샘플링)

**설명:**
Tail Sampling은 트레이스의 모든 스팬이 도착한 후 샘플링 결정을 내립니다. 이는 트레이스 시작 시점에 결정하는 Head Sampling(확률적 샘플링)과 대비됩니다. Tail Sampling의 장점은 에러가 있거나 지연 시간이 긴 트레이스만 선택적으로 유지할 수 있다는 것입니다. 단, 결정을 내리기 전까지 모든 스팬을 메모리에 보관해야 하므로 `decision_wait`와 `num_traces` 설정이 중요합니다.

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
VictoriaMetrics 클러스터 모드는 세 가지 구성 요소로 이루어집니다. vminsert는 메트릭 수집 및 분산을, vmselect는 쿼리 처리를, vmstorage는 실제 메트릭 데이터 저장을 담당합니다. vmstorage는 여러 인스턴스로 수평 확장이 가능하며, 복제 기능을 통해 고가용성을 제공합니다. 이러한 분리된 아키텍처 덕분에 수집, 저장, 쿼리 워크로드를 독립적으로 스케일링할 수 있습니다.

</details>

5. 로그/메트릭 저장 비용을 절감하기 위해 오래된 데이터를 S3 Glacier와 같은 저비용 스토리지로 이동하는 전략을 무엇이라고 하나요?

<details>
<summary>정답 보기</summary>

**정답:** Tiered Storage (계층화 저장) 또는 계층형 스토리지

**설명:**
계층화 저장 전략은 데이터의 중요도와 접근 빈도에 따라 다른 스토리지 티어에 저장합니다. 최근 데이터는 고성능 스토리지(SSD, EBS)에, 중기 데이터는 S3 Standard-IA에, 장기 보관 데이터는 S3 Glacier Deep Archive에 저장합니다. 이를 통해 70-90%의 저장 비용을 절감할 수 있습니다. Loki, Tempo 등 오브젝트 스토리지 기반 솔루션은 이러한 전략을 기본적으로 지원합니다.

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
    Exclude  log ^.*DEBUG.*$
    Exclude  log ^.*TRACE.*$
```

또는 정규표현식을 활용한 방식:
```ini
[FILTER]
    Name     grep
    Match    *
    Exclude  log (DEBUG|TRACE)
```

**설명:**
Fluent Bit의 grep 필터는 정규표현식을 사용하여 로그를 필터링합니다. `Exclude` 지시어는 패턴과 일치하는 로그를 제외합니다. 프로덕션 환경에서 DEBUG/TRACE 로그를 필터링하면 로그 볼륨을 40-60% 줄일 수 있어 저장 비용이 크게 절감됩니다. 단, 트러블슈팅이 필요한 특정 서비스에서는 선별적으로 DEBUG 로그를 활성화할 수 있습니다.

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

3. OpenTelemetry Collector에서 에러 트레이스는 100%, 1초 이상 지연된 트레이스는 100%, 나머지는 10%만 샘플링하는 tail_sampling 프로세서 설정을 작성하세요.

<details>
<summary>정답 보기</summary>

**정답:**
```yaml
processors:
  tail_sampling:
    decision_wait: 10s
    num_traces: 100000
    policies:
      # 에러가 있는 트레이스는 100% 유지
      - name: errors-policy
        type: status_code
        status_code:
          status_codes: [ERROR]

      # 1초 이상 지연된 트레이스는 100% 유지
      - name: slow-traces-policy
        type: latency
        latency:
          threshold_ms: 1000

      # 나머지는 10%만 샘플링
      - name: default-policy
        type: probabilistic
        probabilistic:
          sampling_percentage: 10
```

**설명:**
Tail Sampling 정책은 순서대로 평가되며, 하나라도 일치하면 트레이스가 유지됩니다. `decision_wait`는 트레이스 완료를 기다리는 시간으로, 모든 스팬이 도착할 충분한 시간이 필요합니다. `num_traces`는 메모리에 보관할 최대 트레이스 수입니다. 이 설정으로 에러와 성능 문제 분석에 중요한 트레이스는 유지하면서 전체 데이터 볼륨을 약 90% 줄일 수 있습니다.

</details>

---

## 심화 문제

1. 대규모 EKS 클러스터(500+ 노드)에서 관측성 스택의 고가용성을 확보하기 위한 아키텍처를 설계하세요. 수집, 저장, 쿼리 계층별로 어떤 구성 요소를 어떻게 배치해야 하는지 설명하세요.

<details>
<summary>정답 보기</summary>

**정답:**

**수집 계층 (Data Collection):**
- Fluent Bit: 각 노드에 DaemonSet으로 배포 (메모리 100-200Mi 제한)
- OTel Collector: DaemonSet으로 배포, 앞단에 로드밸런서 배치
- 수집기 이중화: 각 AZ에 최소 2개 이상의 Collector 인스턴스

**저장 계층 (Storage):**
- 로그: Loki Simple Scalable 모드
  - Write 경로: 2+ 레플리카 (AZ 분산)
  - Read 경로: 2+ 레플리카 (쿼리 부하 분산)
  - 백엔드: S3 (내구성 99.999999999%)

- 메트릭: VictoriaMetrics 클러스터 또는 AMP
  - vminsert: 2+ 레플리카 (쓰기 부하 분산)
  - vmstorage: 3+ 레플리카 (복제 팩터 2)
  - vmselect: 2+ 레플리카 (읽기 부하 분산)

- 트레이스: Grafana Tempo
  - Distributor: 2+ 레플리카
  - Ingester: 3+ 레플리카 (WAL 활성화)
  - 백엔드: S3

**쿼리 계층 (Query):**
- Grafana: 2+ 레플리카, 외부 PostgreSQL/MySQL로 세션 저장
- 캐싱: Redis/Memcached로 쿼리 결과 캐싱

**핵심 고려사항:**
1. 모든 Stateful 컴포넌트는 다중 AZ 배포
2. 공유 스토리지로 S3 활용 (단일 장애점 제거)
3. Prometheus 샤딩 (3-5개 샤드) + Remote Write로 중앙 저장소 오프로드
4. PodDisruptionBudget으로 롤링 업데이트 시 가용성 보장

</details>

2. 월 $5,000의 관측성 비용이 발생하는 환경에서 품질을 유지하면서 50% 비용 절감을 달성하기 위한 최적화 전략을 제시하세요. 로깅, 메트릭, 트레이싱 각 영역별로 구체적인 방법을 설명하세요.

<details>
<summary>정답 보기</summary>

**정답:**

**로깅 최적화 (예상 절감: $1,500-2,000)**

1. **로그 레벨 필터링** (40-60% 절감)
   - DEBUG/TRACE 로그 프로덕션 환경에서 제외
   - 구현: Fluent Bit grep 필터로 `Exclude log (DEBUG|TRACE)`

2. **샘플링 적용** (30-50% 절감)
   - 고빈도 로그(액세스 로그, 헬스체크)에 10% 샘플링
   - 구현: Fluent Bit throttle 필터 `Rate 10, Window 60`

3. **보존 기간 최적화** (20-40% 절감)
   - 프로덕션: 14일, 개발/스테이징: 7일
   - 중요 로그만 장기 보관 (S3 Glacier로 이동)

4. **저장소 전환** (50-70% 절감)
   - CloudWatch Logs ($0.50/GB 수집) -> Loki + S3 ($0.023/GB 저장)

**메트릭 최적화 (예상 절감: $500-800)**

1. **카디널리티 관리**
   - 불필요한 레이블 제거 (pod_template_hash, controller_revision_hash)
   - 메트릭 드롭: `go_.*`, `promhttp_.*` 등 내부 메트릭 제외

2. **스크랩 간격 조정**
   - 중요 메트릭: 15s, 일반 메트릭: 30s-60s
   - 히스토그램 버킷 제한 (불필요한 le 값 제거)

3. **Recording Rules 활용**
   - 자주 사용되는 집계 쿼리 미리 계산
   - 원본 고해상도 데이터 조기 삭제 (7일 -> 3일)

4. **저장소 전환**
   - 자체 Prometheus -> VictoriaMetrics (7배 압축률)
   - 또는 AMP 활용 (운영 부담 제거, 비용 예측 가능)

**트레이싱 최적화 (예상 절감: $500-1,000)**

1. **Tail Sampling 적용** (80-90% 절감)
   - 에러/느린 트레이스: 100% 유지
   - 정상 트레이스: 5-10%만 샘플링

2. **저장소 전환**
   - X-Ray ($5/백만 트레이스) -> Tempo + S3 (저장 비용만)

3. **보존 기간 최적화**
   - 상세 트레이스: 7일
   - 집계 데이터: 30일

**종합 예상 절감: $2,500-3,800 (50-76%)**

핵심은 중요도 기반 계층화입니다. 모든 데이터를 동등하게 취급하지 않고, 문제 분석에 필요한 데이터는 유지하면서 나머지는 적극적으로 줄입니다.

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
