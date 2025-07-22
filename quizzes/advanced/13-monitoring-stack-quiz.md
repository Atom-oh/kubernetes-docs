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
