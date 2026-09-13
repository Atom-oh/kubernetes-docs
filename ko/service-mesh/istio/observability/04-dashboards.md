# Istio 대시보드

> **검토 기준**: Istio 1.31. Kiali 호환성 범위는 아래에 별도로 명시합니다.
> **마지막 업데이트**: 2026년 9월 11일

Grafana·Kiali·Prometheus로 설정한 텔레메트리를 조회합니다. 예제는 공식 자료·오프라인 검증에 근거한 실습 설정이며 실제 배포·운영 부하 검증은 수행하지 않았습니다. 백엔드 가용성·인증·네임스페이스 권한·스토리지·버전 호환성이 전제 조건입니다.

## 목차

1. [대시보드 개요](#대시보드-개요)
2. [Kiali](#kiali)
3. [Grafana 대시보드](#grafana-대시보드)
4. [Prometheus](#prometheus)
5. [커스텀 대시보드 생성](#커스텀-대시보드-생성)
6. [대시보드 통합](#대시보드-통합)
7. [모범 사례](#모범-사례)

## 대시보드 개요

### 관찰성 스택 아키텍처

Kiali는 Kubernetes API에서 Istio 리소스를 읽고 Prometheus를 조회합니다. Istiod는 Kiali에 설정을 push하는 대신 프록시를 구성합니다. Grafana는 설정된 메트릭·로그·추적 백엔드를 조회하며 Prometheus는 프록시 메트릭을 스크레이프하고 collector는 로그·span을 전달합니다. 추적 애플리케이션은 context를 전파해야 합니다.

### 도구별 용도

| 도구 | 주요 용도 | 데이터 소스 |
|------|----------|------------|
| **Kiali** | 서비스 토폴로지, 트래픽 분석, 구성 검증 | Prometheus, Istio Config |
| **Grafana** | 메트릭 시각화, 알림, 로그 분석 | Prometheus, Loki, Tempo |
| **Prometheus** | 메트릭 수집 및 쿼리 | Envoy, istiod |
| **Jaeger** | 분산 추적 분석 | Envoy spans |

## Kiali

<p align="center">
  <img src="https://istio.io/latest/docs/tasks/observability/kiali/kiali-graph.png" alt="Kiali Service Graph" width="900">
</p>

Kiali는 Istio 서비스 메시를 위한 **관찰성 콘솔**입니다. 서비스 토폴로지를 실시간으로 시각화하고, 트래픽 흐름을 분석하며, Istio 구성을 검증합니다.

### Kiali의 핵심 가치

1. **서비스 그래프 시각화**: 마이크로서비스 간의 관계와 트래픽 흐름을 직관적으로 표현
2. **실시간 모니터링**: 요청률, 에러율, 응답시간을 실시간으로 확인
3. **구성 검증**: VirtualService, DestinationRule 등의 Istio CRD 오류 감지
4. **mTLS 상태 확인**: 서비스 간 mTLS 적용 여부를 시각적으로 확인
5. **분산 추적 통합**: Jaeger와 연동하여 서비스 그래프에서 바로 트레이스 확인

### 설치 예제와 호환성

Kiali 2.31.0과 operator는 2026년 8월 23일에 릴리스되었습니다. 공개 호환성 표는 현재 Istio 1.30에 Kiali 2.26 이상, Istio 1.29에 Kiali 2.21 이상을 명시하지만 **Istio 1.31을 아직 명시적으로 나열하지 않습니다**. 아래는 문서화된 호환 Istio 환경을 위한 Kiali 2.31 설정 예제입니다. 1.31 조합은 최신 maintainer 안내와 대표 실습으로 확인해야 하며 버전 번호가 같거나 최신이라는 사실만으로 호환성이 증명되지 않습니다. 예제를 따르기 위해 기존 메시를 임의로 다운그레이드하지 않습니다.

#### 1. Kiali Operator 설치

```bash
helm repo add kiali https://kiali.org/helm-charts
helm repo update kiali
helm install kiali-operator kiali/kiali-operator \
  --namespace kiali-operator --create-namespace --version 2.31.0
kubectl get pods -n kiali-operator
```

#### 2. 범위가 제한된 조회 전용 Kiali CR 생성

Istio 메트릭을 가진 접근 가능한 Prometheus가 먼저 있어야 하며 Service 이름이 다르면 URL을 맞춥니다. 뒤의 Prometheus Operator 예제는 `istio-system`에 `prometheus` Service를 정의합니다. Operator는 Kiali 자신의 네임스페이스와 discovery selector가 선택한 네임스페이스에 접근을 부여합니다. `cluster_wide_access: false`에서는 서버에 클러스터 전체 권한 대신 네임스페이스 권한을 생성하며 사용자 RBAC는 표시 범위를 더 제한할 수 있습니다.

```yaml
apiVersion: kiali.io/v1alpha1
kind: Kiali
metadata:
  name: kiali
  namespace: istio-system
spec:
  deployment:
    cluster_wide_access: false
    discovery_selectors:
      default:
      - matchExpressions:
        - key: kubernetes.io/metadata.name
          operator: In
          values:
          - default
          - app
          - production
    view_only_mode: true
    replicas: 1
    resources:
      requests:
        cpu: 100m
        memory: 256Mi
      limits:
        cpu: 500m
        memory: 1Gi
  auth:
    strategy: token
  external_services:
    prometheus:
      url: http://prometheus.istio-system.svc.cluster.local:9090
    grafana:
      enabled: false
    tracing:
      enabled: false
```

`kiali-cr.yaml`로 저장해 적용하고 reconciliation 전에 대상 애플리케이션 네임스페이스를 준비합니다. Kiali는 Istio discovery selector를 자동 상속하지 않습니다. 기존 `accessible_namespaces` 필드는 Kiali 2.0에서 제거되었습니다. Grafana·추적 연동은 endpoint·자격 증명·호환성을 구성할 때까지 비활성화했습니다.

```bash
kubectl apply -f kiali-cr.yaml
kubectl get kiali,pods -n istio-system
kubectl port-forward -n istio-system svc/kiali 20001:20001
```

외부 접근은 유지보수되는 ingress/gateway, TLS 인증서, 인증, 브라우저에서 접근 가능한 URL을 별도로 구성합니다. 이 예제는 ingress controller·cert-manager issuer·공개 endpoint를 설치하지 않습니다. Proxy-status 기능은 istiod debug API에 의존할 수 있으며 의도적으로 비활성화했다면 `external_services.istio.istio_api_enabled: false`와 기능 제한을 적용합니다.

### Kiali 접속

Port-forward 후 `http://localhost:20001`을 엽니다. Token 인증은 Kubernetes ServiceAccount 토큰과 해당 계정의 네임스페이스 권한을 사용합니다. 의도한 RBAC를 가진 전용 viewer 신원을 사용하며 Kiali server/operator ServiceAccount를 편의상 관리자 로그인에 사용하지 않습니다. 계정과 RoleBinding을 먼저 준비했다면 다음처럼 토큰을 발급할 수 있습니다:

```bash
kubectl create token kiali-viewer -n default --duration=1h
```

실제 토큰 수명은 API server가 결정합니다. Token 전략은 단일 클러스터를 지원합니다. 멀티 클러스터·OIDC에는 문서화된 인증 설정·등록한 redirect URI·네임스페이스 인가가 필요하며 client ID와 issuer URL만으로 운영 구성이 완성되지 않습니다. [Kiali 전제 조건](https://kiali.io/docs/installation/installation-guide/prerequisites/)과 [네임스페이스 관리](https://kiali.io/docs/configuration/namespace-management/)를 참고하세요.

### Kiali 주요 기능

#### 1. 서비스 그래프 (Graph)

**Overview**:
- 네임스페이스별 서비스 토폴로지 시각화
- 트래픽 흐름 및 요청률(RPS) 표시
- 에러율 및 응답 시간 시각화
- 버전별 트래픽 분산 확인

Traffic animation은 선택한 시간 범위·갱신 주기의 집계 트래픽을 시각화합니다. 패킷 캡처나 요청당 점 하나를 의미하지 않으므로 정량 분석에는 엣지 메트릭을 사용합니다.

**그래프 뷰 타입**:

| 뷰 타입 | 설명 | 사용 시나리오 |
|---------|------|--------------|
| **App Graph** | 애플리케이션 단위 | 서비스 간 의존성 파악 |
| **Versioned App Graph** | 버전별 애플리케이션 | 카나리 배포 모니터링 |
| **Workload Graph** | 워크로드 단위 | Deployment/StatefulSet 레벨 분석 |
| **Service Graph** | 서비스 단위 | Kubernetes Service 중심 뷰 |

**그래프 필터 옵션**:

```yaml
# Edge 레이블 표시
- Request percentage: 트래픽 분산율 (%)
- Request rate: 요청률 (RPS)
- Response time: 선택한 지연 통계
- Throughput: 처리량 (bytes/sec)

# Display 옵션
- Traffic Animation: 실시간 트래픽 흐름
- Service Nodes: 서비스 노드 표시
- Traffic Distribution: 버전별 트래픽 분산
- Security: mTLS 잠금 아이콘
- Circuit Breakers: Circuit breaker 상태
- Virtual Services: VirtualService 아이콘
```

**Find/Hide 기능**:
```
# 느린 엣지 찾기
Find: response time > 1s
Expression: rt > 1000

# 상태가 좋지 않은 노드 찾기
Find: unhealthy nodes
Expression: ! healthy

# 특정 서비스 숨기기
Hide: kube-system namespace
```

#### 2. 애플리케이션 뷰 (Applications)

각 애플리케이션의 상세 정보:

- **Overview**: 전체 상태 요약
- **Traffic**: 인바운드/아웃바운드 트래픽 메트릭
  - Request volume (RPS)
  - Request duration (P50, P95, P99)
  - Request size / Response size
- **Inbound Metrics**: 들어오는 트래픽 분석
  - Source workloads
  - Request protocols (HTTP/gRPC/TCP)
  - Response codes
- **Outbound Metrics**: 나가는 트래픽 분석
  - Destination services
  - Response times
  - Error rates

#### 3. 워크로드 뷰 (Workloads)

Deployment, StatefulSet 등 워크로드별 상세 정보:

- **Pods**: 파드 목록 및 상태
- **Services**: 연결된 Service 목록
- **Logs**: 실시간 파드 로그 (Envoy + 애플리케이션)
- **Metrics**: 워크로드 메트릭
  - Request volume
  - Duration (P50/P95/P99)
  - Error rate
- **Traces**: Jaeger 연동 분산 추적
- **Envoy**: Envoy 설정 확인
  - Clusters
  - Listeners
  - Routes
  - Bootstrap config

#### 4. 서비스 뷰 (Services)

Kubernetes Service별 상세 정보:

- **Overview**: 서비스 메타데이터
- **Traffic**: 트래픽 메트릭
- **Inbound Metrics**: 클라이언트별 요청 분석
- **Traces**: 서비스 호출 추적

#### 5. Istio 구성 검증 (Istio Config)

Kiali는 사용 가능한 클러스터 상태로 지원되는 Istio 리소스를 검사합니다. 조회 전용 예제는 설정을 볼 수 있으며 편집에는 별도 인가 권한이 필요합니다. 녹색 표시는 구현된 검사를 통과했다는 뜻이며 실행 중 정확성을 보장하지 않습니다.

**검증 대상**:
- VirtualService
- DestinationRule
- Gateway
- ServiceEntry
- Sidecar
- PeerAuthentication
- RequestAuthentication
- AuthorizationPolicy
- Telemetry

**검증 수준**:

| 아이콘 | 수준 | 설명 |
|--------|------|------|
| ✅ | Valid | 사용 가능한 검사를 통과함 |
| ⚠️ | Warning | 잠재적 문제 (권장사항 위반) |
| ❌ | Error | 설정 오류 감지(API는 수락할 수 있음) |

**검증 예제: KIA1107, Subset Not Found**

`default` 네임스페이스에서 짧은 host `reviews`는 `reviews.default.svc.cluster.local`로 해석되므로 두 표기만으로 host 불일치가 되지 않습니다. KIA0101은 AuthorizationPolicy에서 참조한 네임스페이스가 없다는 의미입니다. 아래의 의도적인 오류 예제는 `v1`만 정의하고 `v2`로 라우팅합니다:

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: reviews
  namespace: default
spec:
  hosts:
  - reviews.default.svc.cluster.local
  http:
  - route:
    - destination:
        host: reviews.default.svc.cluster.local
        subset: v2
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews
  namespace: default
spec:
  host: reviews.default.svc.cluster.local
  subsets:
  - name: v1
    labels:
      version: v1
```

참조한 subset과 일치하는 service endpoint를 배포하거나 의도한 기존 subset으로 라우팅합니다. 두 Bookinfo 버전이 존재한다면 다음 DestinationRule이 두 레이블을 정의합니다:

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews
  namespace: default
spec:
  host: reviews.default.svc.cluster.local
  subsets:
  - name: v1
    labels:
      version: v1
  - name: v2
    labels:
      version: v2
```

Kubernetes는 의미상 라우팅 오류가 있는 매니페스트도 수락할 수 있으므로 설정 경고·오류가 API admission 실패와 같은 뜻은 아닙니다.

#### 6. 보안 (Security)

**mTLS 상태 확인**

그래프 보안 표시를 선택한 트래픽 시간 범위·실제 PeerAuthentication과 함께 확인합니다. mTLS가 관측됐다고 평문이 금지됐다는 뜻은 아닙니다. PERMISSIVE에서도 관측 시간 동안 전부 암호화될 수 있습니다. 트래픽·메트릭 부재가 보안을 증명하지 않으며 정책 표시만으로 인가 효과가 보장되지 않습니다. 설정과 허용·거부 요청으로 확인합니다.

**보안 대시보드**:
- Namespace별 mTLS 상태
- PeerAuthentication 정책 적용 현황
- AuthorizationPolicy 효과

#### 7. 분산 추적 통합 (Distributed Tracing)

Kiali는 Jaeger와 통합되어 서비스 그래프에서 바로 trace를 확인할 수 있습니다.

**사용 방법**:
1. 그래프에서 서비스 노드 클릭
2. "View Traces" 링크 클릭
3. Jaeger UI로 자동 이동하여 해당 서비스의 trace 확인

**Trace 상세 정보**:
- Span duration (각 서비스 처리 시간)
- 계측된 span 속성·event(헤더는 자동으로 모두 수집되지 않음)
- 에러 상세 내용
- Service dependency 맵

### Kiali 고급 기능

#### Traffic Shifting 시각화

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: reviews-canary
  namespace: default
spec:
  hosts:
  - reviews.default.svc.cluster.local
  http:
  - route:
    - destination:
        host: reviews.default.svc.cluster.local
        subset: v1
      weight: 90
    - destination:
        host: reviews.default.svc.cluster.local
        subset: v2
      weight: 10
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews
  namespace: default
spec:
  host: reviews.default.svc.cluster.local
  subsets:
  - name: v1
    labels:
      version: v1
  - name: v2
    labels:
      version: v2
```

설정 가중치는 90/10이며 Kiali는 선택한 시간 범위의 관측 요청률을 표시합니다. 표본 변동·오류·라우팅 조건으로 관측 비율은 달라질 수 있습니다. 두 subset에 일치하는 endpoint가 있어야 합니다.

**Canary 배포 모니터링**:
- 설정 가중치 90/10과 비교한 버전별 관측 요청률
- 버전별 에러율 비교
- 버전별 응답 시간 (P50, P95, P99)
- 실시간 트래픽 애니메이션으로 분산 확인

#### Namespace 격리 및 접근 제어

같은 Kiali 인스턴스의 대안 selector 설정이며 범위가 겹치는 추가 배포가 아닙니다. Cluster-wide access를 끄면 server 접근을 `team-a`와 자신의 컨트롤 플레인 네임스페이스로 제한하며 사용자 RBAC도 적용됩니다. OpenID 설정은 별도 인증 작업이고 현재 Keycloak 기본 경로는 사용자 지정 `/auth` prefix가 없는 한 `/realms/...`입니다.

```yaml
apiVersion: kiali.io/v1alpha1
kind: Kiali
metadata:
  name: kiali
  namespace: istio-system
spec:
  deployment:
    cluster_wide_access: false
    discovery_selectors:
      default:
      - matchLabels:
          kubernetes.io/metadata.name: team-a
    view_only_mode: true
    replicas: 1
    resources:
      requests:
        cpu: 100m
        memory: 256Mi
      limits:
        cpu: 500m
        memory: 1Gi
  auth:
    strategy: token
```

## Grafana 대시보드

### 공식 Istio 대시보드

다음은 제목만이 아니라 다운로드한 **Istio1.31.0 리비전**으로 확인한 목록입니다. 설치한 Istio에 맞는 리비전을 선택하고 import 시 Prometheus datasource를 지정합니다. 최신 리비전이 이전 메시와 자동 호환되지는 않습니다.

| 대시보드 | ID | 확인한 리비전 | 범위 |
|---|---:|---:|---|
| Istio Mesh | 7639 | 330 | 전체 트래픽·성공/4xx/5xx·워크로드 개요·컴포넌트 버전 |
| Istio Service | 7636 | 329 | Client/server 요청량·지연·크기·TCP·송신/수신 워크로드 |
| Istio Workload | 7630 | 330 | 워크로드 inbound/outbound HTTP·TCP 메트릭 |
| Istio Performance | 11829 | 329 | Proxy/istiod vCPU·메모리·디스크·전송량·goroutine |
| Istio Control Plane | 7645 | 329 | 자원·xDS push/오류/시간·검증/주입 webhook |
| Istio Wasm Extension | 13277 | 287 | Wasm VM/runtime/cache/원격 로딩 상태 |
| Istio Ztunnel | 21306 | 97 | Ambient L4 연결·바이트·DNS·xDS·프로세스 자원 |

Service 대시보드의 `service` 변수는 서비스 host이며1.31 리비전은 일반 `namespace` 대신 `srcns`/`dstns` 필터를 가집니다. Workload 대시보드는 `namespace`·`workload`를 사용합니다. 링크 구성 전에 다운로드한 리비전의 변수를 확인합니다. ID7636·11829·13277은 각각 **Service·Performance·Wasm**이며 Workload·일반 Mesh·Gateway가 아닙니다.

Grafana dashboard UI에서 import하고 datasource를 선택합니다. 새 테스트 환경은 Istio 버전에 고정한 `samples/addons/grafana.yaml` 번들을 사용할 수 있지만 운영 보안 구성이 아닙니다. 기존 배포는 두 번째 Grafana를 설치하지 말고 해당 provisioning 방식을 사용합니다.

### 커뮤니티 Loki 대시보드14876

확인한 항목은 **Grafana Loki Dashboard for Istio Service Mesh** 리비전3입니다. 특정 Envoy 텍스트 형식의 `pattern` parser, `status_code`·`req_id` 필드, datasource/label/job/instance 변수를 사용합니다. 요청/상태 수·바이트·최근 요청·지연·방문자/경로/user-agent 요약 패널이 있으며 mTLS 보안을 입증하거나 기존 문서가 주장한 모든 패널을 제공하지는 않습니다.

```bash
curl -fL -o istio-loki-dashboard.json \
  https://grafana.com/api/dashboards/14876/revisions/3/download
```

파일을 검토한 뒤 UI에서 import하고 Loki datasource를 연결합니다. 레이블 있는 ConfigMap만으로 datasource 입력이 치환되거나 loader가 설치되지는 않습니다. 이 커뮤니티 리비전은 본 가이드의 JSON 제공자·Alloy 레이블과 직접 호환되지 않습니다. 해당 형식에는 [로깅 장의 검증된 대시보드·쿼리](03-logging.md)를 사용하거나 parser·필드·레이블을 명시적으로 맞춥니다. 로그 통계는 보관된 로그를 나타내며 필터링·샘플링으로 편향될 수 있습니다.

### 메트릭 알림 규칙

다음은 Grafana 관리 알림 provisioning이 아닌 **Prometheus Operator PrometheusRule**입니다. Grafana 관리 규칙은 query-data·condition·UID 형식이므로 그 방식을 쓰면 Grafana에서 구성하고 지원되는 형식으로 export합니다. 아래 Operator 예제는 `istio-system` 규칙을 선택합니다. 임계치는 SLO·트래픽량에 맞출 예시이며 HTTP5xx만으로 gRPC·애플리케이션 실패가 모두 정의되지는 않습니다.

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: istio-alerts
  namespace: istio-system
spec:
  groups:
  - name: istio-service-alerts
    rules:
    - alert: HighErrorRate
      expr: sum by (destination_service_name, destination_service_namespace) (rate(istio_requests_total{reporter="destination",response_code=~"5.."}[5m]))
        / sum by (destination_service_name, destination_service_namespace) (rate(istio_requests_total{reporter="destination"}[5m]))
        > 0.05
      for: 2m
      labels:
        severity: warning
      annotations:
        summary: High HTTP error fraction for {{ $labels.destination_service_name }}
        description: Error fraction is {{ $value | humanizePercentage }}
    - alert: HighLatency
      expr: histogram_quantile(0.95, sum by (destination_service_name, destination_service_namespace,
        le) (rate(istio_request_duration_milliseconds_bucket{reporter="destination"}[5m]))) > 1000
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: P95 HTTP duration exceeds1000ms
    - alert: UpstreamOverflow
      expr: sum by (destination_service_name, destination_service_namespace) (rate(istio_requests_total{response_flags=~".*UO.*",reporter="source"}[5m]))
        > 0
      for: 1m
      labels:
        severity: warning
      annotations:
        summary: Source proxy reports upstream overflow
    - alert: PlaintextMeshTraffic
      expr: sum by (source_workload, source_workload_namespace, destination_workload, destination_workload_namespace)
        (rate(istio_requests_total{connection_security_policy="none",reporter="destination"}[5m])) > 0
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: Observed plaintext traffic; inspect intended PeerAuthentication
```

에러 표현식을 비율로 유지하므로 `humanizePercentage`가 올바르게 표시합니다. 대상에 도달하지 못하는 upstream overflow는 source reporter를 사용합니다. 평문 메트릭 부재는 STRICT 강제의 증거가 아닙니다.

## Prometheus

### Prometheus Operator 실습 설정

별도로 설치된 호환 Prometheus Operator·CRD와 EKS EC2 노드의 정상 `gp3` StorageClass(다른 플랫폼은 해당 class)를 전제합니다. Operator 설치·EBS 프로비저닝·운영 스토리지/HA 설계까지 제공하는 예제는 아닙니다. CPU·메모리·스토리지 값은 예시이며 기존 Prometheus와 중복 스크레이프하지 않습니다.

아래 ServiceMonitor·PodMonitor·PrometheusRule selector는 기본적으로 이 CR의 네임스페이스에 있는 리소스를 모두 선택하므로 기존 잘못된 레이블 조건 없이 [메트릭 장](01-metrics.md)의 monitor를 포함합니다. Monitor 리소스 선택과 각 monitor가 검색할 워크로드 네임스페이스는 별도 설정입니다. RBAC는 Kubernetes 대상 검색용이며 추가 scrape 유형에는 다른 권한이 필요할 수 있습니다.

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: prometheus-istio
  namespace: istio-system
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: prometheus-istio-discovery
rules:
- apiGroups:
  - ''
  resources:
  - services
  - endpoints
  - pods
  verbs:
  - get
  - list
  - watch
- apiGroups:
  - discovery.k8s.io
  resources:
  - endpointslices
  verbs:
  - get
  - list
  - watch
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: prometheus-istio-discovery
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: prometheus-istio-discovery
subjects:
- kind: ServiceAccount
  name: prometheus-istio
  namespace: istio-system
---
apiVersion: monitoring.coreos.com/v1
kind: Prometheus
metadata:
  name: istio
  namespace: istio-system
spec:
  replicas: 1
  retention: 15d
  retentionSize: 50GB
  serviceAccountName: prometheus-istio
  podMetadata:
    labels:
      monitoring-stack: istio
  serviceMonitorSelector: {}
  podMonitorSelector: {}
  ruleSelector: {}
  resources:
    requests:
      cpu: 1000m
      memory: 4Gi
    limits:
      cpu: 2000m
      memory: 8Gi
  storage:
    volumeClaimTemplate:
      spec:
        accessModes:
        - ReadWriteOnce
        resources:
          requests:
            storage: 100Gi
        storageClassName: gp3
---
apiVersion: v1
kind: Service
metadata:
  name: prometheus
  namespace: istio-system
spec:
  selector:
    monitoring-stack: istio
  ports:
  - name: http
    port: 9090
    targetPort: 9090
  type: ClusterIP
```

장기 저장은 목적지를 배포·보호한 뒤 remote-write 설정을 병합합니다. 아래 URL은 `observability`의 VictoriaMetrics Service를 가정하므로 실제 백엔드에 맞춥니다. Prometheus replica2개는 같은 대상을 수집하므로 원격 저장소의 HA·중복 제거 설계와 replica 레이블이 필요합니다. `replicas`를2로 바꾸는 것만으로 원격 집계가 정확해지지는 않습니다. 대상 환경에서 영속성·장애 동작·용량을 검증합니다.

```yaml
spec:
  remoteWrite:
  - url: http://victoria-metrics.observability.svc.cluster.local:8428/api/v1/write
    queueConfig:
      capacity: 10000
      maxShards: 5
      minShards: 1
      maxSamplesPerSend: 5000
```

### Prometheus Query 예제

#### Golden Signals

지연 단위는 밀리초입니다. 포화도 예제는 활성 연결 수와 breaker 상태 gauge이며 자동 사용률 분모로 쓸 표준 `cx_max` 메트릭은 없습니다.

```promql
# 1. Latency (지연시간)
histogram_quantile(0.95,
  sum(rate(istio_request_duration_milliseconds_bucket{
    reporter="destination"
  }[5m])) by (destination_service_name, destination_service_namespace, le)
)

# 2. Traffic (트래픽)
sum(rate(istio_requests_total{reporter="destination"}[1m])) by (destination_service_name, destination_service_namespace)

# 3. Errors (에러율)
sum(rate(istio_requests_total{response_code=~"5..", reporter="destination"}[5m])) by (destination_service_name, destination_service_namespace)
/
sum(rate(istio_requests_total{reporter="destination"}[5m])) by (destination_service_name, destination_service_namespace)
* 100

# 4. Saturation (포화도)
envoy_cluster_upstream_cx_active
envoy_cluster_circuit_breakers_default_cx_open
```

## 커스텀 대시보드 생성

### Grafana Dashboard JSON 템플릿

Import·파일 provisioning용 classic dashboard 객체입니다. 기존 `prometheus` datasource UID가 필요합니다. 모든 패널에 namespace·service 필터를 적용하고 송신자 표에는 source namespace도 보존합니다.

```json
{
  "title": "Custom Istio Service Dashboard",
  "tags": [
    "istio",
    "custom"
  ],
  "timezone": "browser",
  "version": 1,
  "panels": [
    {
      "id": 1,
      "title": "Request Rate",
      "type": "timeseries",
      "gridPos": {
        "h": 8,
        "w": 12,
        "x": 0,
        "y": 0
      },
      "targets": [
        {
          "expr": "sum(rate(istio_requests_total{reporter=\"destination\",destination_service_namespace=\"$namespace\",destination_service_name=\"$service\"}[5m])) by (response_code)",
          "legendFormat": "{{ response_code }}",
          "refId": "A",
          "datasource": {
            "type": "prometheus",
            "uid": "prometheus"
          }
        }
      ],
      "fieldConfig": {
        "defaults": {
          "color": {
            "mode": "palette-classic"
          },
          "custom": {
            "drawStyle": "line",
            "lineInterpolation": "linear",
            "fillOpacity": 10
          },
          "unit": "reqps"
        }
      },
      "datasource": {
        "type": "prometheus",
        "uid": "prometheus"
      }
    },
    {
      "id": 2,
      "title": "P95 Latency",
      "type": "gauge",
      "gridPos": {
        "h": 8,
        "w": 6,
        "x": 12,
        "y": 0
      },
      "targets": [
        {
          "expr": "histogram_quantile(0.95, sum(rate(istio_request_duration_milliseconds_bucket{reporter=\"destination\",destination_service_namespace=\"$namespace\",destination_service_name=\"$service\"}[5m])) by (le))",
          "refId": "A",
          "datasource": {
            "type": "prometheus",
            "uid": "prometheus"
          }
        }
      ],
      "fieldConfig": {
        "defaults": {
          "unit": "ms",
          "thresholds": {
            "mode": "absolute",
            "steps": [
              {
                "value": 0,
                "color": "green"
              },
              {
                "value": 500,
                "color": "yellow"
              },
              {
                "value": 1000,
                "color": "red"
              }
            ]
          },
          "max": 2000
        }
      },
      "options": {
        "showThresholdLabels": true,
        "showThresholdMarkers": true
      },
      "datasource": {
        "type": "prometheus",
        "uid": "prometheus"
      }
    },
    {
      "id": 3,
      "title": "Error Rate",
      "type": "stat",
      "gridPos": {
        "h": 8,
        "w": 6,
        "x": 18,
        "y": 0
      },
      "targets": [
        {
          "expr": "sum(rate(istio_requests_total{reporter=\"destination\",destination_service_namespace=\"$namespace\",destination_service_name=\"$service\", response_code=~\"5..\"}[5m])) / sum(rate(istio_requests_total{reporter=\"destination\",destination_service_namespace=\"$namespace\",destination_service_name=\"$service\"}[5m])) * 100",
          "refId": "A",
          "datasource": {
            "type": "prometheus",
            "uid": "prometheus"
          }
        }
      ],
      "fieldConfig": {
        "defaults": {
          "unit": "percent",
          "thresholds": {
            "mode": "absolute",
            "steps": [
              {
                "value": 0,
                "color": "green"
              },
              {
                "value": 1,
                "color": "yellow"
              },
              {
                "value": 5,
                "color": "red"
              }
            ]
          }
        }
      },
      "datasource": {
        "type": "prometheus",
        "uid": "prometheus"
      }
    },
    {
      "id": 4,
      "title": "Request by Source",
      "type": "table",
      "gridPos": {
        "h": 8,
        "w": 12,
        "x": 0,
        "y": 8
      },
      "targets": [
        {
          "expr": "sum(rate(istio_requests_total{reporter=\"destination\",destination_service_namespace=\"$namespace\",destination_service_name=\"$service\"}[5m])) by (source_workload, source_workload_namespace, response_code)",
          "format": "table",
          "instant": true,
          "refId": "A",
          "datasource": {
            "type": "prometheus",
            "uid": "prometheus"
          }
        }
      ],
      "transformations": [
        {
          "id": "organize",
          "options": {
            "excludeByName": {
              "Time": true
            },
            "indexByName": {
              "source_workload": 0,
              "response_code": 1,
              "Value": 2
            },
            "renameByName": {
              "source_workload": "Source",
              "response_code": "Code",
              "Value": "RPS"
            }
          }
        }
      ],
      "datasource": {
        "type": "prometheus",
        "uid": "prometheus"
      }
    },
    {
      "id": 5,
      "title": "Upstream Overflow and Retry Exhaustion",
      "type": "timeseries",
      "gridPos": {
        "h": 8,
        "w": 12,
        "x": 12,
        "y": 8
      },
      "targets": [
        {
          "expr": "sum(rate(istio_requests_total{reporter=\"source\",destination_service_namespace=\"$namespace\",destination_service_name=\"$service\", response_flags=~\".*UO.*\"}[5m]))",
          "legendFormat": "Upstream overflow",
          "refId": "A",
          "datasource": {
            "type": "prometheus",
            "uid": "prometheus"
          }
        },
        {
          "expr": "sum(rate(istio_requests_total{reporter=\"source\",destination_service_namespace=\"$namespace\",destination_service_name=\"$service\", response_flags=~\".*URX.*\"}[5m]))",
          "legendFormat": "Retry/connect attempts exhausted",
          "refId": "B",
          "datasource": {
            "type": "prometheus",
            "uid": "prometheus"
          }
        }
      ],
      "datasource": {
        "type": "prometheus",
        "uid": "prometheus"
      }
    }
  ],
  "templating": {
    "list": [
      {
        "name": "namespace",
        "type": "query",
        "query": "label_values(istio_requests_total, destination_service_namespace)",
        "datasource": {
          "type": "prometheus",
          "uid": "prometheus"
        },
        "current": {
          "selected": true,
          "text": "default",
          "value": "default"
        },
        "multi": false
      },
      {
        "name": "service",
        "type": "query",
        "query": "label_values(istio_requests_total{destination_service_namespace=\"$namespace\"}, destination_service_name)",
        "datasource": {
          "type": "prometheus",
          "uid": "prometheus"
        },
        "current": {},
        "multi": false
      }
    ]
  },
  "time": {
    "from": "now-1h",
    "to": "now"
  },
  "refresh": "30s",
  "uid": "custom-istio-service"
}
```

### 대시보드 파일 Provisioning

위 완전한 JSON 객체를 `custom-istio-service.json`으로 저장합니다. Provisioning 파일에 생략 기호나 HTTP API의 `{ "dashboard": ... }` wrapper를 넣지 않습니다.

```bash
kubectl create configmap grafana-dashboard-custom-istio \
  --from-file=custom-istio-service.json -n observability \
  --dry-run=client -o yaml | kubectl apply -f -
```

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: grafana-istio-provider
  namespace: observability
data:
  istio.yaml: |
    apiVersion: 1
    providers:
    - name: istio
      orgId: 1
      folder: Istio
      type: file
      disableDeletion: false
      editable: false
      options:
        path: /var/lib/grafana/istio-dashboards
```

기존 Grafana Deployment·Helm 값에 다음 마운트를 병합하고 이미지·자격 증명·스토리지·probe·다른 컨테이너를 유지합니다. 컨테이너 이름은 실제 배포와 맞아야 합니다. `subPath`로 마운트한 provider 파일이 바뀌면 대상 파드의 순차 교체가 필요합니다. 이미 dashboard sidecar를 구성했다면 그 차트 설정을 따릅니다. `grafana_dashboard` 레이블만으로 loader가 설치·구성되지는 않습니다.

```yaml
spec:
  template:
    spec:
      containers:
      - name: grafana
        volumeMounts:
        - name: istio-dashboards
          mountPath: /var/lib/grafana/istio-dashboards
          readOnly: true
        - name: istio-provider
          mountPath: /etc/grafana/provisioning/dashboards/istio.yaml
          subPath: istio.yaml
          readOnly: true
      volumes:
      - name: istio-dashboards
        configMap:
          name: grafana-dashboard-custom-istio
      - name: istio-provider
        configMap:
          name: grafana-istio-provider
```

## 대시보드 통합

### Kiali → Grafana·추적 링크

앞의 Kiali CR에 병합할 선택적 조각입니다. `internal_url`은 Kiali server, `external_url`은 사용자 브라우저에서 접근 가능해야 합니다. Kiali는 Grafana API에 인증하고 정확한 dashboard 이름을 찾아야 합니다. Kiali가 지원하는 Secret 참조로 자격 증명과 필요한 사설 CA 신뢰를 구성합니다. 이 조각은 자격 증명·공개 endpoint를 생성하지 않습니다.

```yaml
spec:
  external_services:
    grafana:
      enabled: true
      internal_url: http://grafana.observability.svc.cluster.local:3000
      external_url: https://grafana.example.com
      datasource_uid: prometheus
      dashboards:
      - name: Istio Service Dashboard
        variables:
          datasource: var-datasource
          service: var-service
      - name: Istio Workload Dashboard
        variables:
          datasource: var-datasource
          namespace: var-namespace
          workload: var-workload
```

추적 장의 Jaeger HTTP query endpoint는 현재 `external_services.tracing` 아래에 설정하고16686 포트에는 `use_grpc: false`를 사용합니다. 활성화 전에 백엔드/API 호환성·인증을 검증합니다. OAuth2 주입은 HTTP transport에서만 지원됩니다. Jaeger·Tempo는 선택적인 별도 연동입니다. Kiali custom dashboard는 고유 schema이며 Grafana JSON을 `external_services.custom_dashboards` 목록으로 넣을 수 없습니다.

```yaml
spec:
  external_services:
    tracing:
      enabled: true
      provider: jaeger
      internal_url: http://jaeger-query.observability.svc.cluster.local:16686
      external_url: https://jaeger.example.com
      use_grpc: false
```

### Grafana → Jaeger 링크

기존 Prometheus datasource에 exemplar 매핑을 병합합니다. 이름은 실제 exemplar 레이블(일반적으로 `trace_id`)과 일치하고 `jaeger`는 기존 datasource UID여야 합니다. 이 설정이 exemplar를 생성하지는 않습니다.

```yaml
# Prometheus 데이터소스 설정
apiVersion: v1
kind: ConfigMap
metadata:
  name: grafana-datasources
data:
  prometheus.yaml: |
    apiVersion: 1
    datasources:
    - name: Prometheus
      type: prometheus
      jsonData:
        exemplarTraceIdDestinations:
        - datasourceUid: jaeger
          name: trace_id
```

### Loki → Tempo 통합

다음 필드를 기존 Loki datasource에 병합합니다. 실제 `trace_id` 로그 필드, 활성화된 추적, Tempo에 보관된 동일 trace가 필요합니다. `request_id`는 trace ID가 아닙니다.

```yaml
# Loki 데이터소스 설정
apiVersion: 1
datasources:
- name: Loki
  type: loki
  jsonData:
    derivedFields:
    - datasourceUid: tempo
      matcherRegex: '"trace_id"\s*:\s*"([0-9a-fA-F]{32})"'
      name: TraceID
      url: '$${__value.raw}'
      urlDisplayLabel: 'View Trace'
```

## 모범 사례

### 1. 대시보드 조직

```
Grafana 폴더 구조:
├── Istio/
│   ├── Overview/
│   │   ├── Istio Mesh Dashboard
│   │   └── Istio Control Plane Dashboard
│   ├── Services/
│   │   ├── Istio Service Dashboard
│   │   └── Custom Service Dashboards
│   ├── Workloads/
│   │   └── Istio Workload Dashboard
│   ├── Gateways/
│   │   └── Istio Gateway Dashboard
│   └── Logs/
│       ├── Loki Istio Dashboard (#14876)
│       └── Access Log Analysis
```

### 2. 변수 사용

모든 대시보드에 일관된 변수 사용:

```json
{
  "templating": {
    "list": [
      {"name": "datasource", "type": "datasource"},
      {"name": "namespace", "type": "query"},
      {"name": "service", "type": "query"},
      {"name": "workload", "type": "query"},
      {"name": "interval", "type": "interval", "auto": true}
    ]
  }
}
```

### 3. Alert 관리

- **계층별 알림**: Critical (PagerDuty) → Warning (Slack) → Info (Email)
- **Alert Grouping**: 서비스별, 네임스페이스별 그룹화
- **Silencing Rules**: 유지보수 중 알림 음소거

### 4. 성능 최적화

```ini
# Grafana 설정
[dashboards]
min_refresh_interval = 10s

[panels]
disable_sanitize_html = false

[dataproxy]
timeout = 30
```

**쿼리 최적화**:
- Recording Rules 사용하여 자주 사용하는 쿼리 사전 계산
- Prometheus rate 범위는 `$__rate_interval`, 쿼리 step·bucket은 `$__interval` 사용
- 초당 비율은 `rate()`, 구간 합계는 `increase()`를 사용하며 둘 다 counter reset을 처리함

### 5. 접근 제어

다음은 익명 접근·가입 비활성화와 기본 Viewer 조직 역할 설정이며 완전한 리소스별 RBAC 정책이 아닙니다. 외부 노출 전에 Kubernetes Secret·Grafana의 문서화된 비밀 처리 방식으로 기존 배포의 관리자 자격 증명을 구성합니다. 이 ConfigMap만으로 비밀번호가 설정되지는 않습니다.

```yaml
# Grafana authentication and default organization role
apiVersion: v1
kind: ConfigMap
metadata:
  name: grafana-config
data:
  grafana.ini: |
    [auth]
    disable_login_form = false

    [auth.anonymous]
    enabled = false

    [auth.basic]
    enabled = true

    [users]
    allow_sign_up = false
    auto_assign_org = true
    auto_assign_org_role = Viewer

    [security]
    admin_user = admin
```

### 6. 백업 및 복구

Provisioning된 dashboard·datasource 파일을 백업하고 UI 관리 dashboard는 지원되는 Grafana UI/API로 export합니다. 전체 복구에는 애플리케이션 일관성을 보장하는 Grafana DB·설정·plugin 백업도 필요합니다. `grafana-cli admin export-dashboard` 명령은 없습니다.

Prometheus snapshot은 `promtool tsdb snapshot`이 아닌 admin HTTP API를 사용합니다. 보호된 유지보수 endpoint에 API를 의도적으로 활성화해야 합니다. 대상 Prometheus 파드를 localhost로 port-forward한 뒤의 유지보수 예제입니다:

```bash
curl -fsS -X POST http://localhost:9090/api/v1/admin/tsdb/snapshot
```

응답은 server 데이터 디렉터리 아래 snapshot 디렉터리 이름을 반환합니다. 완료된 snapshot을 백업 목적지로 복사해야 하며 같은 디스크의 snapshot은 독립 백업이 아닙니다. 복원·보존·remote-write 복구는 별도로 검증합니다. 이 문서 감사에서는 백업·배포 작업을 실행하지 않았습니다.

## 참고 자료

### 공식 문서
- [Kiali Documentation](https://kiali.io/docs/)
- [Istio Observability](https://istio.io/latest/docs/tasks/observability/)
- [Grafana Dashboards](https://grafana.com/grafana/dashboards/)
- [Prometheus Operator](https://prometheus-operator.dev/)

### 커뮤니티 대시보드
- [Grafana Loki Dashboard for Istio (#14876)](https://grafana.com/grafana/dashboards/14876)
- [Istio Workload Dashboard (#7630)](https://grafana.com/grafana/dashboards/7630)
- [Istio Performance Dashboard (#11829)](https://grafana.com/grafana/dashboards/11829)
- [Istio Wasm Extension Dashboard (#13277)](https://grafana.com/grafana/dashboards/13277)

### 참고 자료
- [Kiali Architecture](https://kiali.io/docs/architecture/architecture/)
- [Grafana Best Practices](https://grafana.com/docs/grafana/latest/best-practices/)
- [Prometheus Query Examples](https://prometheus.io/docs/prometheus/latest/querying/examples/)
