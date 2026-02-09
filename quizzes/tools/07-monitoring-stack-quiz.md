# 모니터링 스택 퀴즈

이 퀴즈는 Kubernetes 모니터링 스택 (VictoriaMetrics, Prometheus, Grafana)에 대한 이해도를 테스트합니다.

## 객관식 문제

1. Prometheus의 메트릭 수집 방식으로 올바른 것은?
   - A) 애플리케이션이 Prometheus 서버로 메트릭을 푸시(Push)한다
   - B) Prometheus가 타겟에서 HTTP를 통해 메트릭을 스크랩(Pull)한다
   - C) 에이전트가 메트릭을 수집하여 중앙 서버로 전송한다
   - D) 메트릭이 이벤트 기반으로 실시간 스트리밍된다

<details>

<summary>정답 보기</summary>

**정답: B) Prometheus가 타겟에서 HTTP를 통해 메트릭을 스크랩(Pull)한다**

**설명:**
Prometheus는 풀(Pull) 기반 메트릭 수집 방식을 사용합니다. Prometheus 서버가 설정된 스크랩 간격(scrape_interval)에 따라 각 타겟의 /metrics 엔드포인트에 HTTP 요청을 보내 메트릭을 수집합니다. 이 방식은 서비스 디스커버리와 잘 통합되며, 타겟의 상태를 직접 확인할 수 있는 장점이 있습니다. 단, 단기 작업(short-lived jobs)의 경우 Pushgateway를 통해 푸시 방식도 지원합니다.
</details>

2. VictoriaMetrics가 Prometheus보다 우수한 점으로 올바르지 않은 것은?
   - A) 더 높은 데이터 압축률
   - B) 더 빠른 쿼리 성능
   - C) PromQL과 완전히 다른 새로운 쿼리 언어 사용
   - D) 수평적 확장을 위한 클러스터 모드 지원

<details>

<summary>정답 보기</summary>

**정답: C) PromQL과 완전히 다른 새로운 쿼리 언어 사용**

**설명:**
VictoriaMetrics는 Prometheus와 완전히 호환되는 PromQL을 지원합니다. 따라서 기존 Prometheus 환경에서 VictoriaMetrics로 마이그레이션할 때 기존 쿼리와 대시보드를 그대로 사용할 수 있습니다. VictoriaMetrics의 실제 장점은 Prometheus 대비 최대 7배 더 효율적인 데이터 압축, 최대 20배 빠른 쿼리 성능, 그리고 vmcluster를 통한 수평적 확장성입니다.
</details>

3. kube-state-metrics의 역할로 올바른 것은?
   - A) 노드의 CPU, 메모리, 디스크 사용량 수집
   - B) Kubernetes API 객체의 상태를 메트릭으로 변환
   - C) 컨테이너 런타임의 메트릭 수집
   - D) 네트워크 트래픽 모니터링

<details>

<summary>정답 보기</summary>

**정답: B) Kubernetes API 객체의 상태를 메트릭으로 변환**

**설명:**
kube-state-metrics는 Kubernetes API 서버를 모니터링하여 다양한 Kubernetes 객체(Deployment, Pod, Node, Service 등)의 상태를 Prometheus 메트릭 형식으로 변환합니다. 예를 들어 kube_pod_status_phase, kube_deployment_spec_replicas, kube_node_status_condition 등의 메트릭을 제공합니다. 노드의 시스템 리소스(CPU, 메모리 등)는 node-exporter가 담당합니다.
</details>

4. Prometheus Operator의 ServiceMonitor CRD의 주요 용도는?
   - A) Kubernetes 서비스를 자동으로 생성한다
   - B) 모니터링할 서비스 엔드포인트를 선언적으로 정의한다
   - C) 서비스 메시의 트래픽을 라우팅한다
   - D) 서비스의 헬스체크를 수행한다

<details>

<summary>정답 보기</summary>

**정답: B) 모니터링할 서비스 엔드포인트를 선언적으로 정의한다**

**설명:**
ServiceMonitor는 Prometheus Operator가 제공하는 CRD(Custom Resource Definition)로, 어떤 Kubernetes 서비스에서 메트릭을 수집할지 선언적으로 정의합니다. ServiceMonitor에서 레이블 셀렉터로 대상 서비스를 선택하고, 스크랩 간격, 메트릭 경로, 포트 등을 지정합니다. Prometheus Operator가 이를 감지하여 Prometheus의 스크랩 설정을 자동으로 업데이트합니다.
</details>

5. Alertmanager의 groupBy 설정의 목적은?
   - A) 알림을 특정 수신자에게만 보내기 위해
   - B) 동일한 특성을 가진 알림을 묶어서 중복 알림을 줄이기 위해
   - C) 알림의 우선순위를 결정하기 위해
   - D) 알림 메시지의 형식을 지정하기 위해

<details>

<summary>정답 보기</summary>

**정답: B) 동일한 특성을 가진 알림을 묶어서 중복 알림을 줄이기 위해**

**설명:**
Alertmanager의 groupBy 설정은 지정된 레이블(예: alertname, job, namespace)이 같은 알림들을 하나의 그룹으로 묶습니다. 예를 들어 groupBy: ['alertname', 'namespace']로 설정하면, 같은 네임스페이스에서 발생한 같은 종류의 알림들이 하나의 알림 메시지로 묶여 전송됩니다. 이를 통해 대규모 장애 시 알림 폭풍(alert storm)을 방지하고 수신자의 피로도를 줄일 수 있습니다.
</details>

6. Grafana에서 대시보드 프로비저닝(Provisioning)의 이점은?
   - A) 대시보드를 수동으로 생성할 필요가 없어진다
   - B) 대시보드 설정을 코드로 관리하여 GitOps 방식으로 배포할 수 있다
   - C) 대시보드의 성능이 향상된다
   - D) 사용자 인증이 간소화된다

<details>

<summary>정답 보기</summary>

**정답: B) 대시보드 설정을 코드로 관리하여 GitOps 방식으로 배포할 수 있다**

**설명:**
Grafana의 대시보드 프로비저닝은 JSON 파일이나 ConfigMap으로 정의된 대시보드를 Grafana가 자동으로 로드하는 기능입니다. 이를 통해 대시보드 설정을 버전 관리 시스템(Git)에서 관리하고, CI/CD 파이프라인을 통해 일관되게 배포할 수 있습니다. 여러 환경(개발, 스테이징, 프로덕션)에 동일한 대시보드를 자동으로 배포하고, 변경 이력을 추적할 수 있는 장점이 있습니다.
</details>

7. VictoriaMetrics 클러스터 모드의 구성 요소 중 쿼리 처리를 담당하는 것은?
   - A) vminsert
   - B) vmstorage
   - C) vmselect
   - D) vmagent

<details>

<summary>정답 보기</summary>

**정답: C) vmselect**

**설명:**
VictoriaMetrics 클러스터 모드는 세 가지 주요 구성 요소로 이루어집니다. vminsert는 메트릭 수집 및 분산을 담당하고, vmstorage는 실제 메트릭 데이터를 저장합니다. vmselect는 사용자의 PromQL 쿼리를 처리하고, 여러 vmstorage 노드에서 데이터를 검색하여 결과를 집계합니다. 이러한 분리된 아키텍처 덕분에 각 구성 요소를 독립적으로 확장할 수 있습니다.
</details>

8. Node Exporter가 수집하는 메트릭 유형으로 올바르지 않은 것은?
   - A) CPU 사용률
   - B) 파일시스템 사용량
   - C) Kubernetes Pod 상태
   - D) 네트워크 인터페이스 통계

<details>

<summary>정답 보기</summary>

**정답: C) Kubernetes Pod 상태**

**설명:**
Node Exporter는 리눅스/유닉스 시스템의 하드웨어 및 OS 수준 메트릭을 수집하는 Prometheus 익스포터입니다. CPU, 메모리, 디스크, 네트워크 등 노드의 시스템 리소스 메트릭을 수집합니다. Kubernetes Pod 상태 메트릭(예: Pod 개수, 상태, 재시작 횟수 등)은 kube-state-metrics가 Kubernetes API를 통해 수집합니다.
</details>

## 단답형 문제

9. PromQL에서 최근 5분간 HTTP 요청의 초당 평균 비율을 계산하는 함수는 무엇인가요?

<details>

<summary>정답 보기</summary>

**정답:**
`rate()` 함수입니다.

**설명:**
PromQL에서 `rate()` 함수는 Counter 타입 메트릭의 시간당 변화율을 계산합니다. 예를 들어 `rate(http_requests_total[5m])`는 최근 5분간 HTTP 요청의 초당 평균 비율을 반환합니다. rate() 함수는 Counter 리셋을 자동으로 처리하며, 시계열 데이터의 시작과 끝점을 보간하여 정확한 비율을 계산합니다. 유사한 함수로 `irate()`는 마지막 두 샘플만 사용하여 순간 비율을 계산합니다.
</details>

10. Prometheus에서 Recording Rule을 사용하는 주요 이유 두 가지를 설명하세요.

<details>

<summary>정답 보기</summary>

**정답:**
1. **쿼리 성능 최적화**: 복잡하고 자주 사용되는 쿼리를 미리 계산하여 저장함으로써 대시보드나 알림 쿼리의 응답 시간을 단축합니다.
2. **리소스 효율성**: 동일한 복잡한 쿼리가 여러 번 실행되는 것을 방지하여 Prometheus 서버의 CPU와 메모리 사용량을 줄입니다.

**설명:**
Recording Rule은 PrometheusRule CRD의 `record` 필드를 사용하여 정의합니다. 예를 들어 `job:http_requests_total:rate5m`이라는 이름으로 `sum(rate(http_requests_total[5m])) by (job)`을 미리 계산해 둘 수 있습니다. 이렇게 하면 대시보드에서 이 메트릭을 직접 쿼리하여 빠른 응답을 받을 수 있고, 특히 장기간 데이터를 조회할 때 성능 이점이 큽니다.
</details>

11. Alertmanager의 `for` 필드 (예: for: 5m)의 역할을 설명하세요.

<details>

<summary>정답 보기</summary>

**정답:**
`for` 필드는 알림이 실제로 발송되기 전에 조건이 지속되어야 하는 시간을 지정합니다.

**설명:**
`for: 5m`으로 설정된 알림 규칙은 알림 조건이 5분 동안 연속으로 충족되어야만 "firing" 상태로 전환되어 Alertmanager로 전송됩니다. 이 기간 동안 알림은 "pending" 상태로 유지됩니다. 이 설정은 일시적인 스파이크나 플래핑(flapping)으로 인한 거짓 알림을 방지하는 데 중요합니다. 예를 들어 CPU 사용률이 잠깐 90%를 초과했다가 바로 정상화되면 알림이 발생하지 않습니다.
</details>

12. vmagent의 역할과 Prometheus에서 Remote Write를 사용하는 이유를 설명하세요.

<details>

<summary>정답 보기</summary>

**정답:**
vmagent는 메트릭을 수집하여 VictoriaMetrics(또는 다른 원격 저장소)로 전달하는 경량 에이전트입니다. Remote Write는 수집된 메트릭을 원격 시계열 데이터베이스로 전송하는 프로토콜입니다.

**설명:**
vmagent는 Prometheus의 스크랩 설정과 호환되면서도 더 적은 리소스를 사용합니다. Remote Write를 사용하는 주요 이유:
1. **장기 저장**: Prometheus의 로컬 스토리지 제한을 극복하고 장기 데이터 보존
2. **고가용성**: 여러 Prometheus/vmagent 인스턴스의 데이터를 중앙 집중화
3. **확장성**: VictoriaMetrics 클러스터로 대규모 메트릭 처리
4. **분리된 아키텍처**: 수집과 저장을 분리하여 각각 독립적으로 확장
</details>

## 실습 문제

13. 5XX HTTP 오류율이 10% 이상일 때 발생하는 PrometheusRule을 작성하세요. (10분 동안 지속 시 critical 알림)

<details>

<summary>정답 보기</summary>

**정답:**
```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: http-error-rate-alert
  namespace: monitoring
  labels:
    release: prometheus
spec:
  groups:
  - name: http-alerts
    rules:
    - alert: HighHTTPErrorRate
      expr: |
        sum(rate(http_requests_total{status=~"5.."}[5m]))
        /
        sum(rate(http_requests_total[5m]))
        > 0.1
      for: 10m
      labels:
        severity: critical
      annotations:
        summary: "High HTTP 5XX error rate detected"
        description: "HTTP 5XX error rate is above 10% (current value: {{ $value | printf \"%.2f\" }}%)"
```

**설명:**
이 PrometheusRule은 5XX 상태 코드를 가진 HTTP 요청의 비율을 전체 HTTP 요청 대비로 계산합니다. `status=~"5.."`는 정규표현식으로 500-599 상태 코드를 매칭합니다. `for: 10m`은 이 조건이 10분 동안 지속될 때만 알림을 발생시킵니다. release: prometheus 레이블은 Prometheus Operator가 이 규칙을 감지하도록 합니다.
</details>

14. 애플리케이션의 메트릭을 Prometheus가 수집하도록 ServiceMonitor를 작성하세요. (app: myapp 레이블, 포트: metrics, 경로: /metrics, 간격: 30초)

<details>

<summary>정답 보기</summary>

**정답:**
```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: myapp-monitor
  namespace: monitoring
  labels:
    release: prometheus
spec:
  selector:
    matchLabels:
      app: myapp
  namespaceSelector:
    matchNames:
    - default
    - production
  endpoints:
  - port: metrics
    path: /metrics
    interval: 30s
    scheme: http
    relabelings:
    - sourceLabels: [__meta_kubernetes_pod_name]
      targetLabel: pod
    - sourceLabels: [__meta_kubernetes_namespace]
      targetLabel: namespace
```

**설명:**
ServiceMonitor는 selector로 대상 서비스를 선택하고, endpoints에서 스크랩 설정을 정의합니다. namespaceSelector로 모니터링할 네임스페이스를 지정할 수 있습니다. relabelings를 통해 Kubernetes 메타데이터(파드 이름, 네임스페이스)를 메트릭 레이블로 추가할 수 있어 쿼리와 알림에서 유용하게 사용됩니다. release: prometheus 레이블이 Prometheus의 serviceMonitorSelector와 일치해야 합니다.
</details>

15. Grafana 데이터 소스로 VictoriaMetrics와 Prometheus를 모두 추가하는 ConfigMap을 작성하세요.

<details>

<summary>정답 보기</summary>

**정답:**
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: grafana-datasources
  namespace: monitoring
  labels:
    grafana_datasource: "true"
data:
  datasources.yaml: |-
    apiVersion: 1
    datasources:
    - name: Prometheus
      type: prometheus
      url: http://prometheus-operated:9090
      access: proxy
      isDefault: true
      editable: false
      jsonData:
        timeInterval: "15s"
        httpMethod: POST
    - name: VictoriaMetrics
      type: prometheus
      url: http://victoria-metrics-single-server:8428
      access: proxy
      isDefault: false
      editable: false
      jsonData:
        timeInterval: "15s"
        httpMethod: POST
    - name: VictoriaMetrics-LongTerm
      type: prometheus
      url: http://victoria-metrics-cluster-vmselect:8481/select/0/prometheus
      access: proxy
      isDefault: false
      editable: false
      jsonData:
        timeInterval: "1m"
```

**설명:**
Grafana의 데이터 소스 프로비저닝은 ConfigMap을 통해 선언적으로 관리됩니다. VictoriaMetrics는 Prometheus API와 호환되므로 type을 prometheus로 설정합니다. 단일 노드 VictoriaMetrics는 8428 포트를, 클러스터 모드의 vmselect는 8481 포트를 사용합니다. isDefault: true로 설정된 데이터 소스가 새 대시보드에서 기본으로 선택됩니다. httpMethod: POST는 긴 쿼리에서 URL 길이 제한을 피하기 위해 권장됩니다.
</details>

---

**점수 계산:**
- 13-15개 정답: 우수 (모니터링 스택 전문가 수준)
- 10-12개 정답: 양호 (실무 적용 가능)
- 7-9개 정답: 보통 (추가 학습 권장)
- 4-6개 정답: 기초 (기본 개념 복습 필요)
- 0-3개 정답: 미흡 (전체 내용 재학습 필요)
