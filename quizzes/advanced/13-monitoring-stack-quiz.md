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
