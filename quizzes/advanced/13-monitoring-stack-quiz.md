# 모니터링 스택 퀴즈

이 퀴즈는 Kubernetes 환경에서의 모니터링 스택(Prometheus, Grafana, VictoriaMetrics 등)에 대한 이해를 테스트합니다.

## 퀴즈 문제

### 1. Prometheus의 주요 목적은 무엇인가요?

A. 로그 수집 및 분석  
B. 시계열 데이터 수집 및 저장을 통한 모니터링 및 알림  
C. 분산 추적 시스템 구현  
D. 네트워크 패킷 분석  

<details>
<summary>정답 및 설명</summary>

**정답: B. 시계열 데이터 수집 및 저장을 통한 모니터링 및 알림**

**설명:**
Prometheus의 주요 목적은 시계열 데이터 수집 및 저장을 통한 모니터링 및 알림입니다. Prometheus는 메트릭 기반 모니터링 시스템으로, 시스템과 서비스의 다양한 메트릭을 수집하고 저장하며, 이를 기반으로 쿼리, 시각화, 알림을 제공합니다. 특히 Kubernetes 환경에서 널리 사용되며, CNCF(Cloud Native Computing Foundation)의 졸업 프로젝트 중 하나입니다.

**Prometheus의 주요 특징:**

1. **풀 기반 메트릭 수집**: 타겟 시스템에서 메트릭을 주기적으로 가져옵니다.
2. **강력한 쿼리 언어(PromQL)**: 수집된 데이터를 쿼리하고 분석하기 위한 유연한 쿼리 언어를 제공합니다.
3. **다차원 데이터 모델**: 메트릭 이름과 키-값 쌍의 레이블로 시계열 데이터를 식별합니다.
4. **내장 알림 관리자**: 정의된 조건에 따라 알림을 생성하고 관리합니다.
5. **그래프 및 대시보드**: 내장된 표현식 브라우저와 Grafana 통합을 통한 시각화를 제공합니다.
6. **서비스 디스커버리**: Kubernetes, Consul 등의 서비스 디스커버리 메커니즘과 통합됩니다.

**Prometheus 아키텍처:**

```
                   ┌─────────────────┐
                   │  Alertmanager   │
                   └─────────────────┘
                           ▲
                           │ 알림
                           │
┌─────────────┐      ┌─────────────────┐      ┌─────────────────┐
│  Exporters  │─────▶│    Prometheus    │─────▶│     Grafana     │
└─────────────┘      └─────────────────┘      └─────────────────┘
                           │
                           ▼
                   ┌─────────────────┐
                   │  Storage        │
                   └─────────────────┘
```

**Prometheus 주요 구성 요소:**

1. **Prometheus 서버**: 메트릭을 수집하고 저장하는 핵심 구성 요소입니다.
2. **Exporters**: 다양한 시스템(MySQL, Redis, HAProxy 등)의 메트릭을 Prometheus 형식으로 변환하여 노출합니다.
3. **Alertmanager**: 알림을 처리하고 중복 제거, 그룹화, 라우팅 등을 수행합니다.
4. **Pushgateway**: 단기 작업의 메트릭을 임시로 저장합니다.
5. **클라이언트 라이브러리**: 애플리케이션에서 직접 메트릭을 노출하기 위한 라이브러리입니다.

**Prometheus 데이터 모델:**

Prometheus는 다음과 같은 형식의 시계열 데이터를 저장합니다:
```
<metric_name>{<label_name>=<label_value>, ...} <value> [<timestamp>]
```

예시:
```
http_requests_total{method="GET", endpoint="/api/users", status="200"} 1027 1627984323
```

**PromQL 예시:**

1. **단순 쿼리**:
```
http_requests_total
```

2. **필터링**:
```
http_requests_total{method="GET", status="200"}
```

3. **집계**:
```
sum(rate(http_requests_total{method="GET"}[5m])) by (endpoint)
```

4. **알림 규칙**:
```
groups:
- name: example
  rules:
  - alert: HighRequestLatency
    expr: http_request_duration_seconds{quantile="0.9"} > 1
    for: 10m
    labels:
      severity: warning
    annotations:
      summary: "High request latency on {{ $labels.instance }}"
      description: "{{ $labels.instance }} has a 90th percentile latency of {{ $value }} seconds"
```

**Kubernetes에서의 Prometheus 배포:**

Prometheus는 일반적으로 Kubernetes에서 다음과 같은 방법으로 배포됩니다:

1. **수동 배포**: Kubernetes 매니페스트를 사용하여 직접 배포
2. **Helm 차트**: Prometheus 커뮤니티에서 제공하는 Helm 차트 사용
3. **Prometheus Operator**: 커스텀 리소스를 통한 선언적 관리
4. **kube-prometheus-stack**: Prometheus, Alertmanager, Grafana 등을 포함한 통합 스택

**Prometheus의 한계:**

1. **장기 스토리지**: 장기 데이터 보존에는 최적화되어 있지 않습니다.
2. **수평적 확장성**: 기본적으로 단일 노드로 설계되어 있어 대규모 환경에서는 제한이 있습니다.
3. **풀 모델 제한**: 일부 환경에서는 풀 모델이 적합하지 않을 수 있습니다.

이러한 한계를 극복하기 위해 Thanos, Cortex, VictoriaMetrics 등의 솔루션이 사용됩니다.

**다른 옵션들의 문제점:**
- A. 로그 수집 및 분석: 이는 주로 Elasticsearch, Loki 등의 역할입니다.
- C. 분산 추적 시스템 구현: 이는 Jaeger, Zipkin 등의 역할입니다.
- D. 네트워크 패킷 분석: 이는 Wireshark, tcpdump 등의 역할입니다.
</details>

### 2. Grafana의 주요 목적은 무엇인가요?

A. 메트릭 수집 및 저장  
B. 로그 수집 및 저장  
C. 데이터 시각화 및 대시보드 생성  
D. 알림 관리 및 라우팅  

<details>
<summary>정답 및 설명</summary>

**정답: C. 데이터 시각화 및 대시보드 생성**

**설명:**
Grafana의 주요 목적은 데이터 시각화 및 대시보드 생성입니다. Grafana는 다양한 데이터 소스(Prometheus, Elasticsearch, InfluxDB, MySQL 등)에서 데이터를 가져와 시각적으로 표현하고, 대화형 대시보드를 생성할 수 있는 오픈 소스 플랫폼입니다. 특히 시계열 데이터 시각화에 강점이 있으며, 모니터링, 분석, 알림 기능을 통합하여 제공합니다.

**Grafana의 주요 특징:**

1. **다양한 데이터 소스 지원**: Prometheus, Elasticsearch, InfluxDB, MySQL, PostgreSQL 등 다양한 데이터 소스와 연결할 수 있습니다.
2. **풍부한 시각화 옵션**: 그래프, 히트맵, 테이블, 게이지, 파이 차트 등 다양한 시각화 패널을 제공합니다.
3. **대화형 대시보드**: 드래그 앤 드롭 인터페이스로 사용자 정의 대시보드를 쉽게 생성할 수 있습니다.
4. **알림 기능**: 메트릭이 특정 임계값을 초과할 때 알림을 생성할 수 있습니다.
5. **사용자 관리**: 역할 기반 접근 제어(RBAC)를 통한 세분화된 권한 관리를 제공합니다.
6. **플러그인 시스템**: 커뮤니티에서 개발한 다양한 플러그인을 통해 기능을 확장할 수 있습니다.
7. **어노테이션**: 타임라인에 이벤트를 표시하여 메트릭 변화와 이벤트를 연관시킬 수 있습니다.

**Grafana 아키텍처:**

```
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│  Data Sources   │─────▶│     Grafana     │─────▶│     Users       │
│  (Prometheus,   │      │                 │      │                 │
│   Elasticsearch,│      │                 │      │                 │
│   etc.)         │      │                 │      │                 │
└─────────────────┘      └─────────────────┘      └─────────────────┘
                                │
                                ▼
                         ┌─────────────────┐
                         │   Dashboards    │
                         │   & Alerts      │
                         └─────────────────┘
```

**Grafana 주요 구성 요소:**

1. **데이터 소스**: 데이터를 가져오는 원본 시스템(Prometheus, Elasticsearch 등)입니다.
2. **대시보드**: 여러 패널로 구성된 시각화 화면입니다.
3. **패널**: 개별 시각화 요소(그래프, 테이블 등)입니다.
4. **쿼리 편집기**: 데이터 소스별 쿼리를 작성하는 인터페이스입니다.
5. **알림 규칙**: 특정 조건이 충족될 때 알림을 트리거하는 규칙입니다.
6. **사용자 및 팀**: 대시보드 접근 권한을 관리하는 단위입니다.
7. **플러그인**: 데이터 소스, 패널, 앱 등을 확장하는 구성 요소입니다.

**Grafana 대시보드 예시:**

Kubernetes 클러스터 모니터링을 위한 대시보드는 다음과 같은 패널을 포함할 수 있습니다:

1. **노드 리소스 사용량**: CPU, 메모리, 디스크 사용량을 보여주는 그래프
2. **파드 상태**: 실행 중, 대기 중, 실패한 파드 수를 보여주는 게이지
3. **컨테이너 리소스 사용량**: 컨테이너별 CPU 및 메모리 사용량을 보여주는 테이블
4. **네트워크 트래픽**: 인바운드 및 아웃바운드 네트워크 트래픽을 보여주는 그래프
5. **API 서버 지연 시간**: API 서버 요청 지연 시간을 보여주는 히트맵
6. **알림 상태**: 현재 활성화된 알림을 보여주는 상태 패널

**Grafana 데이터 소스 구성 예시:**

Prometheus 데이터 소스 구성:
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: grafana-datasources
  namespace: monitoring
data:
  prometheus.yaml: |-
    apiVersion: 1
    datasources:
    - name: Prometheus
      type: prometheus
      url: http://prometheus-server.monitoring.svc.cluster.local
      access: proxy
      isDefault: true
```

**Grafana 알림 구성 예시:**

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: grafana-notification-channels
  namespace: monitoring
data:
  notification-channels.yaml: |-
    apiVersion: 1
    notifiers:
    - name: Slack
      type: slack
      uid: slack1
      org_id: 1
      is_default: true
      settings:
        url: https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX
        recipient: "#alerts"
        mentionUsers: ""
        mentionGroups: ""
        mentionChannel: ""
```

**Kubernetes에서의 Grafana 배포:**

Grafana는 일반적으로 Kubernetes에서 다음과 같은 방법으로 배포됩니다:

1. **수동 배포**: Kubernetes 매니페스트를 사용하여 직접 배포
2. **Helm 차트**: Grafana 커뮤니티에서 제공하는 Helm 차트 사용
3. **kube-prometheus-stack**: Prometheus, Alertmanager, Grafana 등을 포함한 통합 스택
4. **Grafana Operator**: 커스텀 리소스를 통한 선언적 관리

**Grafana의 발전:**

최근 Grafana는 단순한 시각화 도구를 넘어 다음과 같은 기능을 통합하고 있습니다:

1. **Grafana Loki**: 로그 집계 시스템
2. **Grafana Tempo**: 분산 추적 시스템
3. **Grafana Mimir**: 대규모 Prometheus 메트릭 저장소
4. **Grafana Alerting**: 통합 알림 시스템
5. **Grafana Dashboard as Code**: 대시보드를 코드로 관리

이러한 통합을 통해 Grafana는 모니터링, 로깅, 추적을 아우르는 통합 관찰성 플랫폼으로 발전하고 있습니다.

**다른 옵션들의 문제점:**
- A. 메트릭 수집 및 저장: 이는 주로 Prometheus, InfluxDB 등의 역할입니다.
- B. 로그 수집 및 저장: 이는 주로 Elasticsearch, Loki 등의 역할입니다.
- D. 알림 관리 및 라우팅: 이는 주로 Alertmanager의 역할이지만, Grafana도 알림 기능을 제공합니다.
</details>
### 3. VictoriaMetrics의 주요 장점은 무엇인가요?

A. 더 나은 시각화 기능  
B. 더 강력한 알림 기능  
C. 높은 성능과 효율적인 스토리지 사용  
D. 더 많은 데이터 소스 지원  

<details>
<summary>정답 및 설명</summary>

**정답: C. 높은 성능과 효율적인 스토리지 사용**

**설명:**
VictoriaMetrics의 주요 장점은 높은 성능과 효율적인 스토리지 사용입니다. VictoriaMetrics는 Prometheus와 호환되는 시계열 데이터베이스로, 대규모 모니터링 환경에서 Prometheus의 한계를 극복하기 위해 설계되었습니다. 특히 높은 수집 속도, 효율적인 스토리지 사용, 우수한 쿼리 성능을 제공하여 대규모 클러스터 모니터링에 적합합니다.

**VictoriaMetrics의 주요 특징:**

1. **높은 수집 속도**: Prometheus보다 더 높은 초당 샘플 수집 속도를 제공합니다.
2. **효율적인 스토리지**: 고유한 압축 알고리즘을 사용하여 Prometheus보다 최대 10배 적은 스토리지를 사용합니다.
3. **수평적 확장성**: 클러스터 모드에서 수평적으로 확장할 수 있습니다.
4. **Prometheus 호환성**: Prometheus API와 호환되어 기존 도구와 쉽게 통합됩니다.
5. **다중 테넌시**: 여러 테넌트의 데이터를 격리하여 저장할 수 있습니다.
6. **장기 데이터 보존**: 장기간 메트릭 데이터를 효율적으로 저장할 수 있습니다.
7. **고가용성**: 클러스터 모드에서 고가용성을 제공합니다.

**VictoriaMetrics 아키텍처:**

VictoriaMetrics는 단일 노드 모드와 클러스터 모드를 지원합니다:

1. **단일 노드 모드**:
```
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│  Prometheus     │─────▶│  VictoriaMetrics │─────▶│     Grafana     │
│  (remote_write) │      │                 │      │                 │
└─────────────────┘      └─────────────────┘      └─────────────────┘
```

2. **클러스터 모드**:
```
                         ┌─────────────────┐
                         │  vminsert       │
┌─────────────────┐      │  (수집 서비스)   │      ┌─────────────────┐
│  Prometheus     │─────▶│                 │─────▶│    vmstorage    │
│  (remote_write) │      └─────────────────┘      │  (스토리지 서비스) │
└─────────────────┘                               └─────────────────┘
                                                         │
                         ┌─────────────────┐            │
                         │    vmselect     │◀───────────┘
┌─────────────────┐      │  (쿼리 서비스)   │
│     Grafana     │◀─────│                 │
└─────────────────┘      └─────────────────┘
```

**VictoriaMetrics 구성 요소:**

1. **단일 노드 모드**:
   - **victoria-metrics**: 메트릭 수집, 저장, 쿼리를 처리하는 단일 바이너리

2. **클러스터 모드**:
   - **vminsert**: 수집된 메트릭을 처리하고 vmstorage로 전달합니다.
   - **vmstorage**: 메트릭 데이터를 저장합니다.
   - **vmselect**: 저장된 데이터에 대한 쿼리를 처리합니다.

**Prometheus와 VictoriaMetrics 비교:**

| 특성 | Prometheus | VictoriaMetrics |
|------|------------|-----------------|
| 스토리지 효율성 | 기본 | 최대 10배 더 효율적 |
| 수집 성능 | 좋음 | 매우 좋음 |
| 쿼리 성능 | 좋음 | 매우 좋음 |
| 수평적 확장성 | 제한적 | 우수함 (클러스터 모드) |
| 장기 데이터 보존 | 제한적 | 우수함 |
| 다중 테넌시 | 없음 | 지원 |
| 메모리 사용량 | 높음 | 낮음 |
| 호환성 | 기준 | Prometheus 호환 |

**Kubernetes에서 VictoriaMetrics 배포:**

1. **단일 노드 모드**:
```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: victoria-metrics
  namespace: monitoring
spec:
  serviceName: victoria-metrics
  replicas: 1
  selector:
    matchLabels:
      app: victoria-metrics
  template:
    metadata:
      labels:
        app: victoria-metrics
    spec:
      containers:
      - name: victoria-metrics
        image: victoriametrics/victoria-metrics:v1.83.1
        args:
          - "--storageDataPath=/storage"
          - "--retentionPeriod=1y"
        ports:
        - containerPort: 8428
          name: http
        volumeMounts:
        - name: storage
          mountPath: /storage
  volumeClaimTemplates:
  - metadata:
      name: storage
    spec:
      accessModes: [ "ReadWriteOnce" ]
      resources:
        requests:
          storage: 50Gi
```

2. **Prometheus remote_write 구성**:
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: prometheus-config
  namespace: monitoring
data:
  prometheus.yml: |
    global:
      scrape_interval: 15s
    
    remote_write:
      - url: "http://victoria-metrics.monitoring.svc.cluster.local:8428/api/v1/write"
    
    scrape_configs:
      - job_name: 'kubernetes-apiservers'
        kubernetes_sd_configs:
        - role: endpoints
        # ... 기타 구성 ...
```

**VictoriaMetrics 사용 사례:**

1. **대규모 클러스터 모니터링**: 수천 개의 노드와 수만 개의 파드가 있는 클러스터 모니터링
2. **장기 데이터 보존**: 규정 준수나 트렌드 분석을 위한 장기 메트릭 데이터 저장
3. **다중 클러스터 모니터링**: 여러 Kubernetes 클러스터의 메트릭을 중앙에서 수집 및 분석
4. **다중 테넌트 환경**: 여러 팀이나 고객의 메트릭을 격리하여 저장
5. **비용 최적화**: 스토리지 비용을 절감하면서 고성능 모니터링 구현

**VictoriaMetrics의 추가 기능:**

1. **vmagent**: 메트릭 수집 및 전달을 위한 경량 에이전트
2. **vmalert**: Prometheus 호환 알림 규칙 평가 엔진
3. **vmbackup/vmrestore**: 백업 및 복원 도구
4. **vmauth**: 다중 테넌시를 위한 인증 프록시
5. **vmctl**: 다른 시계열 데이터베이스에서 데이터 마이그레이션 도구

**다른 옵션들의 문제점:**
- A. 더 나은 시각화 기능: 시각화는 주로 Grafana의 역할이며, VictoriaMetrics는 데이터 저장에 중점을 둡니다.
- B. 더 강력한 알림 기능: 알림은 주로 Alertmanager의 역할이며, VictoriaMetrics는 vmalert를 통해 Prometheus 호환 알림을 제공합니다.
- D. 더 많은 데이터 소스 지원: 데이터 소스 통합은 주로 Grafana의 역할이며, VictoriaMetrics는 Prometheus 호환 데이터 형식에 중점을 둡니다.
</details>

### 4. Prometheus Operator의 주요 목적은 무엇인가요?

A. Prometheus 서버의 성능 최적화  
B. Prometheus 쿼리 언어(PromQL) 확장  
C. Kubernetes에서 Prometheus 스택의 선언적 관리 자동화  
D. Prometheus와 Grafana 간의 통합 개선  

<details>
<summary>정답 및 설명</summary>

**정답: C. Kubernetes에서 Prometheus 스택의 선언적 관리 자동화**

**설명:**
Prometheus Operator의 주요 목적은 Kubernetes에서 Prometheus 스택의 선언적 관리를 자동화하는 것입니다. Prometheus Operator는 Kubernetes의 커스텀 리소스 정의(CRD)를 사용하여 Prometheus, Alertmanager, ServiceMonitor 등의 구성 요소를 선언적으로 관리할 수 있게 해주는 컨트롤러입니다. 이를 통해 Prometheus 스택의 배포, 구성, 관리를 Kubernetes 네이티브 방식으로 수행할 수 있습니다.

**Prometheus Operator의 주요 특징:**

1. **선언적 관리**: Kubernetes 매니페스트를 통해 Prometheus 스택을 선언적으로 정의하고 관리합니다.
2. **자동화된 구성**: ServiceMonitor, PodMonitor 등을 통해 모니터링 대상을 자동으로 구성합니다.
3. **버전 관리**: Prometheus, Alertmanager 등의 버전을 쉽게 관리할 수 있습니다.
4. **고가용성 설정**: Prometheus 및 Alertmanager의 고가용성 구성을 쉽게 설정할 수 있습니다.
5. **동적 구성 업데이트**: 구성 변경 시 자동으로 관련 구성 요소를 업데이트합니다.
6. **통합 모니터링 스택**: kube-prometheus-stack을 통해 Prometheus, Alertmanager, Grafana 등을 통합 관리할 수 있습니다.

**Prometheus Operator 아키텍처:**

```
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│  Kubernetes API │◀─────│  Prometheus     │─────▶│  Prometheus     │
│  Server         │      │  Operator       │      │  Instances      │
└─────────────────┘      └─────────────────┘      └─────────────────┘
                                │                         │
                                │                         │
                                ▼                         ▼
                         ┌─────────────────┐      ┌─────────────────┐
                         │  ServiceMonitor │      │  Alertmanager   │
                         │  PodMonitor     │      │  Instances      │
                         │  PrometheusRule │      │                 │
                         └─────────────────┘      └─────────────────┘
```

**Prometheus Operator 주요 커스텀 리소스:**

1. **Prometheus**: Prometheus 서버 인스턴스를 정의합니다.
2. **Alertmanager**: Alertmanager 인스턴스를 정의합니다.
3. **ServiceMonitor**: 서비스 레이블을 기반으로 모니터링 대상을 자동으로 구성합니다.
4. **PodMonitor**: 파드 레이블을 기반으로 모니터링 대상을 자동으로 구성합니다.
5. **PrometheusRule**: Prometheus 규칙(recording rules, alerting rules)을 정의합니다.
6. **AlertmanagerConfig**: Alertmanager 구성을 정의합니다.
7. **ThanosRuler**: Thanos Ruler 인스턴스를 정의합니다(선택 사항).

**Prometheus 커스텀 리소스 예시:**
```yaml
apiVersion: monitoring.coreos.com/v1
kind: Prometheus
metadata:
  name: prometheus
  namespace: monitoring
spec:
  serviceAccountName: prometheus
  replicas: 2
  version: v2.35.0
  serviceMonitorSelector:
    matchLabels:
      team: frontend
  ruleSelector:
    matchLabels:
      role: alert-rules
  alerting:
    alertmanagers:
    - namespace: monitoring
      name: alertmanager
      port: web
  resources:
    requests:
      memory: 400Mi
    limits:
      memory: 2Gi
  retention: 15d
  storage:
    volumeClaimTemplate:
      spec:
        storageClassName: standard
        resources:
          requests:
            storage: 50Gi
```

**ServiceMonitor 예시:**
```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: example-app
  namespace: monitoring
  labels:
    team: frontend
spec:
  selector:
    matchLabels:
      app: example-app
  endpoints:
  - port: web
    interval: 30s
    path: /metrics
  namespaceSelector:
    matchNames:
    - default
```

**PrometheusRule 예시:**
```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: example-rules
  namespace: monitoring
  labels:
    role: alert-rules
spec:
  groups:
  - name: example
    rules:
    - alert: HighRequestLatency
      expr: http_request_duration_seconds{job="example-app"} > 1
      for: 10m
      labels:
        severity: warning
      annotations:
        summary: "High request latency on {{ $labels.instance }}"
        description: "{{ $labels.instance }} has a 90th percentile latency of {{ $value }} seconds"
```

**Alertmanager 예시:**
```yaml
apiVersion: monitoring.coreos.com/v1
kind: Alertmanager
metadata:
  name: alertmanager
  namespace: monitoring
spec:
  replicas: 3
  version: v0.24.0
  configSecret: alertmanager-config
  storage:
    volumeClaimTemplate:
      spec:
        storageClassName: standard
        resources:
          requests:
            storage: 10Gi
```

**kube-prometheus-stack:**

Prometheus Operator는 종종 kube-prometheus-stack(이전의 prometheus-operator Helm 차트)을 통해 배포됩니다. 이 스택은 다음 구성 요소를 포함합니다:

1. **Prometheus Operator**: 모니터링 스택의 관리를 자동화합니다.
2. **Prometheus**: 메트릭을 수집하고 저장합니다.
3. **Alertmanager**: 알림을 처리하고 라우팅합니다.
4. **node-exporter**: 노드 수준 메트릭을 수집합니다.
5. **kube-state-metrics**: Kubernetes 객체 메트릭을 수집합니다.
6. **Grafana**: 메트릭을 시각화합니다.
7. **기본 대시보드 및 알림 규칙**: Kubernetes 모니터링을 위한 사전 구성된 대시보드와 알림 규칙을 제공합니다.

**Helm을 사용한 kube-prometheus-stack 배포:**
```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
helm install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace \
  --set grafana.adminPassword=admin
```

**Prometheus Operator의 이점:**

1. **GitOps 호환성**: 모니터링 구성을 코드로 관리할 수 있습니다.
2. **자동화된 검색**: 서비스 및 파드 레이블을 기반으로 모니터링 대상을 자동으로 검색합니다.
3. **구성 간소화**: 복잡한 Prometheus 구성을 Kubernetes 네이티브 방식으로 관리할 수 있습니다.
4. **확장성**: 여러 Prometheus 인스턴스를 쉽게 관리할 수 있습니다.
5. **고가용성**: Prometheus 및 Alertmanager의 고가용성 구성을 쉽게 설정할 수 있습니다.
6. **통합 모니터링**: Kubernetes 클러스터 모니터링을 위한 통합 솔루션을 제공합니다.

**다른 옵션들의 문제점:**
- A. Prometheus 서버의 성능 최적화: Prometheus Operator는 성능 최적화보다는 관리 자동화에 중점을 둡니다.
- B. Prometheus 쿼리 언어(PromQL) 확장: Prometheus Operator는 PromQL을 확장하지 않습니다.
- D. Prometheus와 Grafana 간의 통합 개선: Prometheus Operator는 두 시스템 간의 통합보다는 Kubernetes에서의 관리에 중점을 둡니다.
</details>
### 5. Prometheus의 'PromQL'에서 'rate()' 함수의 주요 목적은 무엇인가요?

A. 메트릭의 절대값 계산  
B. 메트릭의 평균값 계산  
C. 카운터 메트릭의 초당 평균 증가율 계산  
D. 메트릭의 최대값 계산  

<details>
<summary>정답 및 설명</summary>

**정답: C. 카운터 메트릭의 초당 평균 증가율 계산**

**설명:**
Prometheus의 'PromQL'에서 'rate()' 함수의 주요 목적은 카운터 메트릭의 초당 평균 증가율을 계산하는 것입니다. 카운터 메트릭은 시간이 지남에 따라 단조롭게 증가하는 값(예: 총 요청 수, 총 오류 수 등)을 나타내며, rate() 함수는 이러한 카운터 메트릭의 변화율을 계산하여 초당 평균 증가량을 반환합니다. 이는 시스템의 현재 활동 수준을 이해하는 데 매우 유용합니다.

**rate() 함수의 작동 방식:**

1. **시간 범위 지정**: rate() 함수는 시간 범위 벡터를 인자로 받습니다(예: `rate(http_requests_total[5m])`).
2. **증가량 계산**: 지정된 시간 범위 내에서 각 시계열의 증가량을 계산합니다.
3. **초당 평균 계산**: 증가량을 시간 범위의 초 수로 나누어 초당 평균 증가율을 계산합니다.
4. **카운터 리셋 처리**: 카운터가 리셋된 경우(예: 서비스 재시작)에도 올바른 결과를 제공합니다.

**rate() 함수 사용 예시:**

1. **HTTP 요청 속도 계산**:
```
rate(http_requests_total[5m])
```
이 쿼리는 지난 5분 동안의 초당 평균 HTTP 요청 수를 계산합니다.

2. **오류율 계산**:
```
rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m])
```
이 쿼리는 지난 5분 동안의 HTTP 5xx 오류 비율을 계산합니다.

3. **CPU 사용률 계산**:
```
rate(node_cpu_seconds_total{mode!="idle"}[5m])
```
이 쿼리는 지난 5분 동안의 초당 평균 CPU 사용 시간을 계산합니다.

4. **네트워크 트래픽 계산**:
```
rate(node_network_receive_bytes_total[5m])
```
이 쿼리는 지난 5분 동안의 초당 평균 네트워크 수신 바이트를 계산합니다.

**rate() vs irate():**

Prometheus는 rate() 외에도 유사한 함수인 irate()를 제공합니다:

- **rate()**: 지정된 시간 범위 내의 모든 데이터 포인트를 사용하여 평균 증가율을 계산합니다. 더 부드러운 그래프를 제공하며, 일반적인 트렌드를 파악하는 데 유용합니다.
- **irate()**: 지정된 시간 범위 내의 마지막 두 데이터 포인트만 사용하여 순간 증가율을 계산합니다. 급격한 변화를 더 잘 포착하며, 실시간 모니터링에 유용합니다.

```
# 지난 5분 동안의 평균 증가율
rate(http_requests_total[5m])

# 지난 5분 내 마지막 두 데이터 포인트 기반 순간 증가율
irate(http_requests_total[5m])
```

**rate() 함수 사용 시 고려 사항:**

1. **시간 범위 선택**: 너무 짧은 시간 범위는 노이즈가 많을 수 있고, 너무 긴 시간 범위는 급격한 변화를 놓칠 수 있습니다.
2. **스크래핑 간격**: rate() 함수는 최소한 두 개의 데이터 포인트가 필요하므로, 시간 범위는 스크래핑 간격의 최소 2배 이상이어야 합니다.
3. **카운터 리셋**: rate() 함수는 카운터 리셋을 자동으로 처리하지만, 너무 자주 리셋되는 경우 정확도가 떨어질 수 있습니다.
4. **집계**: rate() 함수를 먼저 적용한 후 sum()과 같은 집계 함수를 적용해야 합니다(예: `sum(rate(http_requests_total[5m]))`).

**rate() 함수를 사용한 알림 규칙 예시:**

```yaml
groups:
- name: example
  rules:
  - alert: HighRequestRate
    expr: sum(rate(http_requests_total[5m])) by (instance) > 100
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High request rate on {{ $labels.instance }}"
      description: "{{ $labels.instance }} is receiving more than 100 requests per second for the last 5 minutes."
```

**rate() 함수와 함께 사용되는 다른 PromQL 함수:**

1. **sum()**: 여러 시계열의 값을 합산합니다.
   ```
   sum(rate(http_requests_total[5m])) by (instance)
   ```

2. **avg()**: 여러 시계열의 평균을 계산합니다.
   ```
   avg(rate(http_requests_total[5m])) by (job)
   ```

3. **max()**: 여러 시계열 중 최대값을 찾습니다.
   ```
   max(rate(http_requests_total[5m])) by (instance)
   ```

4. **topk()**: 상위 k개의 시계열을 선택합니다.
   ```
   topk(3, rate(http_requests_total[5m]))
   ```

**다른 옵션들의 문제점:**
- A. 메트릭의 절대값 계산: 이는 abs() 함수의 역할입니다.
- B. 메트릭의 평균값 계산: 이는 avg() 함수의 역할입니다.
- D. 메트릭의 최대값 계산: 이는 max() 함수의 역할입니다.
</details>

### 6. Kubernetes 모니터링에서 'kube-state-metrics'의 주요 목적은 무엇인가요?

A. 노드 수준 시스템 메트릭 수집  
B. Kubernetes API 객체 상태에 대한 메트릭 생성  
C. 컨테이너 리소스 사용량 메트릭 수집  
D. 클러스터 네트워크 트래픽 모니터링  

<details>
<summary>정답 및 설명</summary>

**정답: B. Kubernetes API 객체 상태에 대한 메트릭 생성**

**설명:**
Kubernetes 모니터링에서 'kube-state-metrics'의 주요 목적은 Kubernetes API 객체 상태에 대한 메트릭을 생성하는 것입니다. kube-state-metrics는 Kubernetes API 서버를 감시하고 Deployment, Node, Pod, Service 등과 같은 다양한 Kubernetes 객체의 상태 정보를 메트릭으로 변환합니다. 이러한 메트릭은 클러스터의 전반적인 상태와 건강 상태를 모니터링하는 데 중요한 정보를 제공합니다.

**kube-state-metrics의 주요 특징:**

1. **객체 상태 메트릭**: Kubernetes 객체의 상태 정보를 메트릭으로 변환합니다.
2. **리소스 중심**: 리소스 사용량이 아닌 객체 상태에 중점을 둡니다.
3. **읽기 전용**: Kubernetes API 서버에서 정보를 읽기만 하고 변경하지 않습니다.
4. **상태 기반**: 현재 상태를 반영하는 게이지 메트릭을 주로 생성합니다.
5. **Prometheus 호환**: Prometheus 형식의 메트릭을 노출합니다.

**kube-state-metrics vs node-exporter:**

kube-state-metrics와 node-exporter는 서로 다른 유형의 메트릭을 수집합니다:

- **kube-state-metrics**: Kubernetes API 객체 상태에 대한 메트릭을 생성합니다.
- **node-exporter**: 노드 수준의 시스템 메트릭(CPU, 메모리, 디스크, 네트워크 등)을 수집합니다.

**kube-state-metrics vs metrics-server:**

kube-state-metrics와 metrics-server도 서로 다른 목적을 가지고 있습니다:

- **kube-state-metrics**: 모니터링 및 알림을 위한 다양한 Kubernetes 객체 상태 메트릭을 제공합니다.
- **metrics-server**: HPA(Horizontal Pod Autoscaler)와 같은 Kubernetes 자동 스케일링 기능을 위한 리소스 메트릭(CPU, 메모리 사용량)을 제공합니다.

**kube-state-metrics가 제공하는 주요 메트릭:**

1. **Pod 관련 메트릭**:
   - `kube_pod_status_phase`: 파드의 현재 단계(Running, Pending, Failed 등)
   - `kube_pod_container_status_waiting_reason`: 컨테이너가 대기 중인 이유
   - `kube_pod_container_status_restarts_total`: 컨테이너 재시작 횟수

2. **Deployment 관련 메트릭**:
   - `kube_deployment_status_replicas`: 디플로이먼트의 현재 레플리카 수
   - `kube_deployment_status_replicas_available`: 사용 가능한 레플리카 수
   - `kube_deployment_spec_replicas`: 원하는 레플리카 수

3. **Node 관련 메트릭**:
   - `kube_node_status_condition`: 노드 상태 조건(Ready, DiskPressure 등)
   - `kube_node_spec_unschedulable`: 노드가 스케줄 불가능으로 표시되었는지 여부
   - `kube_node_status_capacity`: 노드의 리소스 용량

4. **PersistentVolume 관련 메트릭**:
   - `kube_persistentvolume_status_phase`: 영구 볼륨의 현재 단계
   - `kube_persistentvolumeclaim_status_phase`: 영구 볼륨 클레임의 현재 단계

5. **기타 리소스 메트릭**:
   - `kube_service_info`: 서비스 정보
   - `kube_namespace_status_phase`: 네임스페이스 상태
   - `kube_job_status_succeeded`: 작업 성공 여부
   - `kube_cronjob_status_active`: 활성 크론잡 수

**kube-state-metrics 배포:**

kube-state-metrics는 일반적으로 Kubernetes 클러스터에 다음과 같이 배포됩니다:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: kube-state-metrics
  namespace: monitoring
spec:
  replicas: 1
  selector:
    matchLabels:
      app: kube-state-metrics
  template:
    metadata:
      labels:
        app: kube-state-metrics
    spec:
      serviceAccountName: kube-state-metrics
      containers:
      - name: kube-state-metrics
        image: registry.k8s.io/kube-state-metrics/kube-state-metrics:v2.7.0
        ports:
        - name: http-metrics
          containerPort: 8080
        - name: telemetry
          containerPort: 8081
        readinessProbe:
          httpGet:
            path: /healthz
            port: 8080
          initialDelaySeconds: 5
          timeoutSeconds: 5
```

**kube-state-metrics 사용 사례:**

1. **클러스터 상태 모니터링**: 노드, 파드, 디플로이먼트 등의 상태를 모니터링합니다.
2. **리소스 할당 모니터링**: 요청된 리소스와 할당된 리소스를 비교합니다.
3. **워크로드 상태 모니터링**: 디플로이먼트, 스테이트풀셋, 데몬셋 등의 상태를 모니터링합니다.
4. **스토리지 상태 모니터링**: 영구 볼륨 및 영구 볼륨 클레임의 상태를 모니터링합니다.
5. **작업 성공 여부 모니터링**: 작업 및 크론잡의 성공 여부를 모니터링합니다.

**kube-state-metrics를 사용한 알림 규칙 예시:**

```yaml
groups:
- name: kubernetes-state
  rules:
  - alert: KubePodCrashLooping
    expr: rate(kube_pod_container_status_restarts_total{job="kube-state-metrics"}[5m]) * 60 * 5 > 0
    for: 15m
    labels:
      severity: warning
    annotations:
      summary: "Pod {{ $labels.namespace }}/{{ $labels.pod }} is crash looping"
      description: "Pod {{ $labels.namespace }}/{{ $labels.pod }} is restarting {{ $value }} times / 5 minutes"

  - alert: KubeDeploymentReplicasMismatch
    expr: kube_deployment_spec_replicas{job="kube-state-metrics"} != kube_deployment_status_replicas_available{job="kube-state-metrics"}
    for: 15m
    labels:
      severity: warning
    annotations:
      summary: "Deployment {{ $labels.namespace }}/{{ $labels.deployment }} has replica mismatch"
      description: "Deployment {{ $labels.namespace }}/{{ $labels.deployment }} has {{ $value }} unavailable replicas"
```

**kube-state-metrics 대시보드:**

Grafana에서는 kube-state-metrics 데이터를 시각화하는 다양한 대시보드 템플릿을 제공합니다:

1. **Kubernetes Cluster Status**: 클러스터 전반적인 상태를 보여주는 대시보드
2. **Kubernetes Deployment Status**: 디플로이먼트 상태를 보여주는 대시보드
3. **Kubernetes Pod Status**: 파드 상태를 보여주는 대시보드
4. **Kubernetes Capacity Planning**: 리소스 용량 계획을 위한 대시보드

**다른 옵션들의 문제점:**
- A. 노드 수준 시스템 메트릭 수집: 이는 node-exporter의 역할입니다.
- C. 컨테이너 리소스 사용량 메트릭 수집: 이는 cAdvisor(kubelet에 내장) 또는 metrics-server의 역할입니다.
- D. 클러스터 네트워크 트래픽 모니터링: 이는 네트워크 모니터링 도구(예: Cilium Hubble, Calico)의 역할입니다.
</details>
### 7. Prometheus Alertmanager의 주요 목적은 무엇인가요?

A. 메트릭 수집 및 저장  
B. 알림 중복 제거, 그룹화, 라우팅 및 알림 전송  
C. 메트릭 시각화 및 대시보드 생성  
D. 메트릭 쿼리 및 분석  

<details>
<summary>정답 및 설명</summary>

**정답: B. 알림 중복 제거, 그룹화, 라우팅 및 알림 전송**

**설명:**
Prometheus Alertmanager의 주요 목적은 알림 중복 제거, 그룹화, 라우팅 및 알림 전송입니다. Alertmanager는 Prometheus 서버에서 생성된 알림을 처리하고, 중복 알림을 제거하며, 관련 알림을 그룹화하고, 다양한 알림 채널(이메일, Slack, PagerDuty 등)로 라우팅하는 역할을 담당합니다. 이를 통해 알림 피로를 줄이고 효과적인 알림 관리를 가능하게 합니다.

**Alertmanager의 주요 특징:**

1. **알림 중복 제거**: 동일한 알림이 여러 번 발생하는 경우 중복을 제거합니다.
2. **알림 그룹화**: 관련된 알림을 하나의 그룹으로 묶어 알림 폭주를 방지합니다.
3. **알림 라우팅**: 알림의 특성에 따라 다양한 수신자에게 라우팅합니다.
4. **알림 억제**: 특정 알림이 발생하면 관련된 다른 알림을 억제합니다.
5. **알림 사일런싱**: 특정 기간 동안 알림을 일시적으로 중지합니다.
6. **다양한 알림 채널**: 이메일, Slack, PagerDuty, WebHook 등 다양한 알림 채널을 지원합니다.
7. **고가용성**: 여러 Alertmanager 인스턴스를 클러스터링하여 고가용성을 제공합니다.

**Alertmanager 아키텍처:**

```
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│   Prometheus    │─────▶│  Alertmanager   │─────▶│  알림 채널      │
│   (알림 규칙)    │      │  (알림 처리)    │      │  (이메일, Slack 등)│
└─────────────────┘      └─────────────────┘      └─────────────────┘
```

**Alertmanager 구성 예시:**

```yaml
global:
  resolve_timeout: 5m
  smtp_smarthost: 'smtp.example.org:587'
  smtp_from: 'alertmanager@example.org'
  smtp_auth_username: 'alertmanager'
  smtp_auth_password: 'password'

route:
  group_by: ['alertname', 'cluster', 'service']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
  receiver: 'team-emails'
  routes:
  - match:
      severity: critical
    receiver: 'pagerduty'
  - match:
      severity: warning
    receiver: 'slack'

receivers:
- name: 'team-emails'
  email_configs:
  - to: 'team@example.org'

- name: 'pagerduty'
  pagerduty_configs:
  - service_key: '<pagerduty-service-key>'

- name: 'slack'
  slack_configs:
  - api_url: '<slack-webhook-url>'
    channel: '#alerts'
    text: "{{ range .Alerts }}{{ .Annotations.description }}\n{{ end }}"

inhibit_rules:
- source_match:
    severity: 'critical'
  target_match:
    severity: 'warning'
  equal: ['alertname', 'cluster', 'service']
```

**Alertmanager 주요 구성 요소:**

1. **global**: 전역 설정(SMTP 서버, Slack API URL 등)을 정의합니다.
2. **route**: 알림 라우팅 트리를 정의합니다.
   - **group_by**: 알림을 그룹화하는 레이블을 지정합니다.
   - **group_wait**: 첫 번째 알림 발생 후 그룹의 초기 알림을 보내기 전 대기 시간입니다.
   - **group_interval**: 동일한 그룹에 대한 후속 알림 간의 간격입니다.
   - **repeat_interval**: 동일한 알림을 반복하는 간격입니다.
   - **receiver**: 기본 수신자를 지정합니다.
   - **routes**: 하위 라우팅 규칙을 정의합니다.
3. **receivers**: 알림을 수신할 채널(이메일, Slack, PagerDuty 등)을 정의합니다.
4. **inhibit_rules**: 알림 억제 규칙을 정의합니다.
5. **time_intervals**: 알림 사일런싱을 위한 시간 간격을 정의합니다.

**알림 라우팅 예시:**

```yaml
route:
  receiver: 'default-receiver'
  group_by: ['alertname', 'job']
  routes:
  - match:
      service: 'frontend'
    receiver: 'frontend-team'
  - match:
      service: 'backend'
    receiver: 'backend-team'
  - match_re:
      service: 'database|cache'
    receiver: 'db-team'
  - match:
      severity: 'critical'
    receiver: 'pagerduty'
    continue: true
```

이 예시에서:
- 'service=frontend' 레이블이 있는 알림은 'frontend-team' 수신자에게 라우팅됩니다.
- 'service=backend' 레이블이 있는 알림은 'backend-team' 수신자에게 라우팅됩니다.
- 'service=database' 또는 'service=cache' 레이블이 있는 알림은 'db-team' 수신자에게 라우팅됩니다.
- 'severity=critical' 레이블이 있는 알림은 'pagerduty' 수신자에게 라우팅되며, 'continue=true'로 인해 다른 라우팅 규칙도 계속 평가됩니다.

**알림 그룹화 예시:**

```yaml
route:
  group_by: ['alertname', 'cluster', 'service']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
```

이 예시에서:
- 'alertname', 'cluster', 'service' 레이블이 동일한 알림은 하나의 그룹으로 묶입니다.
- 첫 번째 알림 발생 후 30초 동안 대기한 후 그룹의 초기 알림을 보냅니다.
- 동일한 그룹에 대한 후속 알림은 5분 간격으로 보냅니다.
- 동일한 알림은 4시간마다 반복해서 보냅니다.

**알림 억제 예시:**

```yaml
inhibit_rules:
- source_match:
    alertname: 'NodeDown'
    severity: 'critical'
  target_match:
    alertname: 'PodNotScheduled'
  equal: ['cluster', 'namespace']
```

이 예시에서:
- 'NodeDown' 알림이 'critical' 심각도로 발생하면, 동일한 'cluster'와 'namespace' 레이블을 가진 'PodNotScheduled' 알림은 억제됩니다.

**알림 사일런싱 예시:**

Alertmanager UI 또는 API를 통해 특정 알림을 일시적으로 중지할 수 있습니다:

```json
{
  "matchers": [
    {
      "name": "service",
      "value": "database",
      "isRegex": false
    }
  ],
  "startsAt": "2023-07-22T10:00:00Z",
  "endsAt": "2023-07-22T12:00:00Z",
  "createdBy": "admin",
  "comment": "Database maintenance"
}
```

**Alertmanager 고가용성:**

Alertmanager는 여러 인스턴스를 클러스터링하여 고가용성을 제공할 수 있습니다:

```yaml
apiVersion: monitoring.coreos.com/v1
kind: Alertmanager
metadata:
  name: alertmanager
  namespace: monitoring
spec:
  replicas: 3
  version: v0.24.0
  configSecret: alertmanager-config
```

**Prometheus 알림 규칙 예시:**

```yaml
groups:
- name: example
  rules:
  - alert: HighRequestLatency
    expr: http_request_duration_seconds{quantile="0.9"} > 1
    for: 10m
    labels:
      severity: warning
    annotations:
      summary: "High request latency on {{ $labels.instance }}"
      description: "{{ $labels.instance }} has a 90th percentile latency of {{ $value }} seconds"
```

**다른 옵션들의 문제점:**
- A. 메트릭 수집 및 저장: 이는 Prometheus 서버의 역할입니다.
- C. 메트릭 시각화 및 대시보드 생성: 이는 Grafana의 역할입니다.
- D. 메트릭 쿼리 및 분석: 이는 Prometheus 서버의 PromQL 기능의 역할입니다.
</details>

### 8. Kubernetes 모니터링에서 'node-exporter'의 주요 목적은 무엇인가요?

A. 노드 수준 시스템 메트릭(CPU, 메모리, 디스크 등) 수집  
B. Kubernetes API 객체 상태에 대한 메트릭 생성  
C. 컨테이너 수준 메트릭 수집  
D. 애플리케이션 수준 메트릭 수집  

<details>
<summary>정답 및 설명</summary>

**정답: A. 노드 수준 시스템 메트릭(CPU, 메모리, 디스크 등) 수집**

**설명:**
Kubernetes 모니터링에서 'node-exporter'의 주요 목적은 노드 수준 시스템 메트릭(CPU, 메모리, 디스크 등)을 수집하는 것입니다. node-exporter는 Prometheus 에코시스템의 일부로, Linux 시스템의 하드웨어 및 OS 수준 메트릭을 노출하는 데 특화된 익스포터입니다. Kubernetes 클러스터에서는 일반적으로 DaemonSet으로 배포되어 모든 노드에서 실행되며, 각 노드의 시스템 메트릭을 수집합니다.

**node-exporter의 주요 특징:**

1. **하드웨어 메트릭**: CPU, 메모리, 디스크, 네트워크 등의 하드웨어 메트릭을 수집합니다.
2. **OS 메트릭**: 파일 시스템, 네트워크 스택, 시스템 로드 등의 OS 수준 메트릭을 수집합니다.
3. **확장성**: 다양한 수집기(collector)를 통해 수집할 메트릭을 선택할 수 있습니다.
4. **플랫폼 독립성**: Linux 시스템에서 실행되며, Kubernetes 외부에서도 사용할 수 있습니다.
5. **Prometheus 호환성**: Prometheus 형식의 메트릭을 노출합니다.

**node-exporter가 수집하는 주요 메트릭:**

1. **CPU 메트릭**:
   - `node_cpu_seconds_total`: CPU 모드별(user, system, idle 등) 사용 시간
   - `node_load1`, `node_load5`, `node_load15`: 1분, 5분, 15분 평균 시스템 로드

2. **메모리 메트릭**:
   - `node_memory_MemTotal_bytes`: 총 메모리 크기
   - `node_memory_MemFree_bytes`: 사용 가능한 메모리
   - `node_memory_MemAvailable_bytes`: 실제로 사용 가능한 메모리
   - `node_memory_Buffers_bytes`, `node_memory_Cached_bytes`: 버퍼 및 캐시 메모리

3. **디스크 메트릭**:
   - `node_filesystem_size_bytes`: 파일 시스템 크기
   - `node_filesystem_free_bytes`: 파일 시스템 여유 공간
   - `node_disk_io_time_seconds_total`: 디스크 I/O 시간
   - `node_disk_read_bytes_total`, `node_disk_written_bytes_total`: 디스크 읽기/쓰기 바이트

4. **네트워크 메트릭**:
   - `node_network_receive_bytes_total`, `node_network_transmit_bytes_total`: 네트워크 수신/전송 바이트
   - `node_network_receive_packets_total`, `node_network_transmit_packets_total`: 네트워크 수신/전송 패킷
   - `node_network_receive_errs_total`, `node_network_transmit_errs_total`: 네트워크 수신/전송 오류

5. **기타 시스템 메트릭**:
   - `node_time_seconds`: 시스템 시간
   - `node_boot_time_seconds`: 시스템 부팅 시간
   - `node_filefd_allocated`: 할당된 파일 디스크립터 수
   - `node_filesystem_files`: 파일 시스템의 총 inode 수

**node-exporter 배포:**

Kubernetes에서 node-exporter는 일반적으로 DaemonSet으로 배포됩니다:

```yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: node-exporter
  namespace: monitoring
  labels:
    app: node-exporter
spec:
  selector:
    matchLabels:
      app: node-exporter
  template:
    metadata:
      labels:
        app: node-exporter
    spec:
      hostNetwork: true
      hostPID: true
      containers:
      - name: node-exporter
        image: prom/node-exporter:v1.3.1
        args:
        - --path.procfs=/host/proc
        - --path.sysfs=/host/sys
        - --path.rootfs=/host/root
        - --collector.filesystem.ignored-mount-points=^/(dev|proc|sys|var/lib/docker/.+)($|/)
        - --collector.filesystem.ignored-fs-types=^(autofs|binfmt_misc|cgroup|configfs|debugfs|devpts|devtmpfs|fusectl|hugetlbfs|mqueue|overlay|proc|procfs|pstore|rpc_pipefs|securityfs|sysfs|tracefs)$
        ports:
        - name: metrics
          containerPort: 9100
        volumeMounts:
        - name: proc
          mountPath: /host/proc
          readOnly: true
        - name: sys
          mountPath: /host/sys
          readOnly: true
        - name: root
          mountPath: /host/root
          readOnly: true
      volumes:
      - name: proc
        hostPath:
          path: /proc
      - name: sys
        hostPath:
          path: /sys
      - name: root
        hostPath:
          path: /
```

**node-exporter 서비스:**

node-exporter를 Prometheus가 스크래핑할 수 있도록 서비스를 생성합니다:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: node-exporter
  namespace: monitoring
  labels:
    app: node-exporter
  annotations:
    prometheus.io/scrape: "true"
    prometheus.io/port: "9100"
spec:
  ports:
  - name: metrics
    port: 9100
    targetPort: metrics
  selector:
    app: node-exporter
  clusterIP: None
```

**Prometheus 스크래핑 구성:**

```yaml
scrape_configs:
  - job_name: 'node-exporter'
    kubernetes_sd_configs:
    - role: endpoints
    relabel_configs:
    - source_labels: [__meta_kubernetes_service_label_app]
      regex: node-exporter
      action: keep
    - source_labels: [__meta_kubernetes_endpoint_node_name]
      target_label: instance
```

**node-exporter 메트릭을 사용한 PromQL 쿼리 예시:**

1. **CPU 사용률**:
```
100 - (avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)
```

2. **메모리 사용률**:
```
100 * (1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)
```

3. **디스크 사용률**:
```
100 * (1 - node_filesystem_free_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"})
```

4. **네트워크 트래픽**:
```
rate(node_network_receive_bytes_total{device="eth0"}[5m])
```

**node-exporter 대시보드:**

Grafana에서는 node-exporter 데이터를 시각화하는 다양한 대시보드 템플릿을 제공합니다:

1. **Node Exporter Full**: 노드의 모든 메트릭을 포괄적으로 보여주는 대시보드
2. **Node Exporter Dashboard**: 주요 시스템 메트릭을 보여주는 간결한 대시보드
3. **Kubernetes Nodes**: Kubernetes 노드 메트릭을 보여주는 대시보드

**node-exporter 알림 규칙 예시:**

```yaml
groups:
- name: node-alerts
  rules:
  - alert: HighCPULoad
    expr: 100 - (avg by(instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100) > 80
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High CPU load on {{ $labels.instance }}"
      description: "{{ $labels.instance }} has a CPU load of {{ $value }}%"
  
  - alert: HighMemoryUsage
    expr: 100 * (1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) > 90
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High memory usage on {{ $labels.instance }}"
      description: "{{ $labels.instance }} has memory usage of {{ $value }}%"
  
  - alert: DiskSpaceFilling
    expr: 100 * (1 - node_filesystem_free_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"}) > 85
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "Disk space filling on {{ $labels.instance }}"
      description: "{{ $labels.instance }} has {{ $value }}% disk usage"
```

**다른 옵션들의 문제점:**
- B. Kubernetes API 객체 상태에 대한 메트릭 생성: 이는 kube-state-metrics의 역할입니다.
- C. 컨테이너 수준 메트릭 수집: 이는 cAdvisor(kubelet에 내장)의 역할입니다.
- D. 애플리케이션 수준 메트릭 수집: 이는 애플리케이션 자체 또는 애플리케이션별 익스포터의 역할입니다.
</details>
