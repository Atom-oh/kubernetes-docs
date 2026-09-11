# Istio 퀴즈

> **검토일**: 2026년 9월 11일 · 예제 검증: Istio 1.31.0 / Argo Rollouts 1.10.0

[유지 관리되는 Istio 가이드](../../service-mesh/istio/README.md)를 다루는 퀴즈입니다. 호환성은 [설치 가이드](../../service-mesh/istio/01-installation.md)에서 확인하세요. Kubernetes 최소 버전 하나는 지원 매트릭스가 아닙니다. 예제는 학습 보조이며 운영 배포 검증을 거치지 않았습니다. Namespace, hostname, identity와 backend endpoint는 검증한 실제 값으로 바꾸세요.

## 문제 1: 서비스 메시 기본 개념

<details>
<summary>서비스 메시란 무엇이며 주요 기능은?</summary>

서비스 메시는 서비스 통신을 인프라 수준에서 제어하고 관찰합니다. 라우팅·로드 밸런싱, 명시적으로 예산을 정한 retry·timeout, workload identity·전송 보안, 인가, 메트릭, access log와 tracing 통합을 제공합니다.

Istio의 sidecar와 ambient는 L4/L7 기능과 정책 부착 방식이 다릅니다. 많은 제어가 비즈니스 로직 변경 없이 가능하지만 trace context 전파, 정상 종료와 영속 멱등성에는 애플리케이션이 참여해야 합니다. 메시가 비멱등 retry를 자동으로 안전하게 만들거나 모든 관측 backend를 설치하지는 않습니다.

</details>

## 문제 2: Istio 아키텍처

<details>
<summary>컨트롤 플레인과 데이터 플레인의 역할은?</summary>

- **Istiod**는 Service·설정 상태를 감시하고 설정을 변환·배포합니다. CRD 객체의 영속 저장은 Kubernetes가 담당합니다. Workload 인증서 발급·갱신에는 구성한 CA 통합을 사용합니다.
- **Sidecar 모드**는 등록된 애플리케이션 Pod 옆에서 Envoy가 캡처한 트래픽을 처리합니다.
- **Ambient 모드**는 노드별 ztunnel의 L4 전송·identity와 지원되는 L7 기능용 선택적 Envoy waypoint를 사용합니다.
- **Gateway**는 선택한 ingress/egress 경로를 처리합니다. Deployment/controller와 라우팅 설정 객체는 별개입니다.

“모든 트래픽을 가로챈다”는 주장은 제외 경로, 프로토콜과 enrollment 확인이 필요합니다. 보편적인 85% 절감은 없습니다. 실제 proxy 수, request·limit, 사용량, waypoint 용량, 노드 수용과 운영 비용을 비교해야 합니다. [아키텍처](../../service-mesh/istio/03-architecture.md)와 [ambient 리소스 모델](../../service-mesh/istio/advanced/01-ambient-mode.md)을 참고하세요.

</details>

## 문제 3: 트래픽 관리 및 Argo Rollouts 통합

<details>
<summary>Istio 라우팅과 Argo 분석을 어떻게 canary 배포에 결합하나요?</summary>

Argo가 이름을 지정한 Istio HTTP route의 가중치와 stable/canary backend 선택을 관리합니다. Rollout에는 selector, Pod template, 실제 Service, namespace enrollment와 대응 VirtualService도 필요합니다. 다음은 [전체 롤아웃 가이드](../../service-mesh/istio/advanced/08-argo-rollouts.md)의 host 기반 예제에서 **Rollout.spec 아래에 넣는 조각**일 뿐입니다:

```yaml
strategy:
  canary:
    stableService: test-stable
    canaryService: test-canary
    maxSurge: 1
    maxUnavailable: 0
    trafficRouting:
      istio:
        virtualService:
          name: test
          routes:
          - primary
    steps:
    - setWeight: 10
    - pause:
        duration: 5m
    - analysis:
        templates:
        - templateName: success-rate
        args:
        - name: service-name
          value: test-canary
        - name: namespace
          value: rollouts-demo
    - setWeight: 50
    - pause:
        duration: 5m
    - analysis:
        templates:
        - templateName: success-rate
        args:
        - name: service-name
          value: test-canary
        - name: namespace
          value: rollouts-demo
    - setWeight: 80
    - pause:
        duration: 5m
    - analysis:
        templates:
        - templateName: success-rate
        args:
        - name: service-name
          value: test-canary
        - name: namespace
          value: rollouts-demo
```

다음 success-rate template은 유한한 검사이며 **canary Service**의 요청량과 HTTP 가용성을 확인합니다. 양쪽 프록시를 중복 집계하지 않도록 한쪽 reporter만 사용합니다:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: success-rate
  namespace: rollouts-demo
spec:
  args:
  - name: service-name
  - name: namespace
  metrics:
  - name: request-volume
    interval: 30s
    successCondition: len(result) == 1 && !isNaN(result[0]) && !isInf(result[0]) && result[0] >= 20
    failureLimit: 0
    provider:
      prometheus:
        address: http://prometheus.istio-system.svc.cluster.local:9090
        query: sum(increase(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}"}[2m]))
    count: 5
  - name: http-availability
    interval: 30s
    successCondition: len(result) == 1 && !isNaN(result[0]) && !isInf(result[0]) && result[0] >= 0.95
    failureLimit: 0
    provider:
      prometheus:
        address: http://prometheus.istio-system.svc.cluster.local:9090
        query: |-
          (sum(rate(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}",response_code!~"5..|0"}[2m])) or vector(0))
          /
          sum(rate(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}"}[2m]))
    count: 5
```

Prometheus backend와 대상 proxy scrape가 구성되어 있어야 합니다. 이 sidecar 예시는 source-reporter HTTP 메트릭과 실제 canary 트래픽을 전제합니다. Ambient L4 경로만으로 해당 L7 측정값이 생기지는 않습니다.

Argo의 Prometheus 결과는 배열이므로 길이 확인 후 result[0]을 검사합니다. Empty, NaN과 infinity가 통과하면 안 됩니다. 분자의 0 fallback은 전부 실패한 트래픽을 처리하고, 요청량 gate는 트래픽 0·누락을 정상으로 판단하지 않게 합니다. 여기의 “가용성”은 5xx와 code 0을 제외하며 업무 성공이나 2xx 응답만의 비율이 아닙니다.

이전 scalar result >= 0.95, provider address 누락, 없는 latency template과 불완전한 Rollout은 완전한 자동화 예제가 아니었습니다. failureLimit은 **허용 실패 수**이므로 2이면 두 번까지 허용하고 세 번째에 실패합니다. 이 예시는 0입니다. 반응 시간은 측정 간격, controller reconciliation과 route 전파에 따라 달라지며 즉시 rollback을 보장하지 않습니다.

</details>

## 문제 4: 보안 기능

<details>
<summary>mTLS, 인가와 JWT 검증은 어떻게 다른가요?</summary>

PeerAuthentication은 수신 workload mTLS를 제어하며 client의 송신 TLS 정책이 아닙니다. 다음 namespace 정책은 호출자가 STRICT 준비를 마친 상황을 가정합니다. Mesh root namespace에 두면 더 넓은 범위에 영향을 줍니다:

```yaml
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: default
  namespace: app
spec:
  mtls:
    mode: STRICT
```

**Sidecar에 등록된** backend Pod에서는 다음 정책으로 frontend workload identity, 검증된 JWT와 허용된 GET 경로를 함께 요구합니다:

```yaml
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: backend-default-deny
  namespace: app
spec:
  selector:
    matchLabels:
      app: backend
---
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: backend-read
  namespace: app
spec:
  selector:
    matchLabels:
      app: backend
  action: ALLOW
  rules:
  - from:
    - source:
        principals:
        - cluster.local/ns/app/sa/frontend
        requestPrincipals:
        - '*'
    to:
    - operation:
        methods:
        - GET
        paths:
        - /api/*
---
apiVersion: security.istio.io/v1
kind: RequestAuthentication
metadata:
  name: backend-jwt
  namespace: app
spec:
  selector:
    matchLabels:
      app: backend
  jwtRules:
  - issuer: https://auth.example.com
    jwksUri: https://auth.example.com/.well-known/jwks.json
    audiences:
    - backend-api
```

첫 정책은 선택한 backend의 빈 **ALLOW** 정책입니다. ALLOW 규칙이 맞을 때까지 default-deny로 동작하며 뒤의 허용을 덮어쓰는 명시적 DENY action이 아닙니다. 다른 ALLOW 정책이 접근을 넓힐 수 있으므로 전체 정책을 검토해야 합니다.

RequestAuthentication은 제공된 JWT를 검증하지만 단독으로는 JWT 없는 요청도 허용합니다. 여기서 검증된 JWT를 필수로 만드는 것은 requestPrincipals 조건입니다. Issuer, JWKS URL과 audience는 실제 provider로 바꿀 예시 값입니다. Workload principal과 JWT principal은 다른 identity입니다.

Ambient L7 정책은 지원되는 waypoint 부착이 필요합니다. Sidecar selector 기반 HTTP 정책을 ztunnel에 그대로 적용하지 마세요. targetRefs, 마이그레이션과 신뢰 경계는 [보안 가이드](../../service-mesh/istio/security/README.md)를 참고하세요.

</details>

## 문제 5: Gateway 및 Ingress

<details>
<summary>Gateway TLS 종료와 애플리케이션 라우팅은 어떻게 구성하나요?</summary>

다음은 Kubernetes Gateway API가 아닌 **Istio Gateway** 예제입니다. Gateway Deployment, 일치하는 Pod label과 Service port가 먼저 있어야 합니다. 앱은 bookinfo, gateway workload와 credential은 istio-ingress에 있습니다:

```yaml
apiVersion: networking.istio.io/v1
kind: Gateway
metadata:
  name: bookinfo-gateway
  namespace: istio-ingress
spec:
  selector:
    istio: ingressgateway
  servers:
  - port:
      number: 443
      name: https
      protocol: HTTPS
    tls:
      mode: SIMPLE
      credentialName: bookinfo-secret
    hosts:
    - bookinfo.example.com
  - port:
      number: 80
      name: http
      protocol: HTTP
    hosts:
    - bookinfo.example.com
    tls:
      httpsRedirect: true
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: bookinfo
  namespace: bookinfo
spec:
  hosts:
  - bookinfo.example.com
  gateways:
  - istio-ingress/bookinfo-gateway
  http:
  - route:
    - destination:
        host: productpage.bookinfo.svc.cluster.local
        port:
          number: 9080
    timeout: 10s
    retries:
      attempts: 0
```

SIMPLE이 downstream TLS를 종료하므로 VirtualService는 HTTP routing을 사용합니다. HTTP listener는 허용한 예시 domain만 redirect합니다. 쓰기를 포함한 모든 route retry를 명시적으로 껐습니다. 소유한 domain과 실제 namespace/Service/selector로 바꿔 사용하세요.

```bash
kubectl -n istio-ingress create secret tls bookinfo-secret \
  --key=bookinfo.key \
  --cert=bookinfo-fullchain.pem
```

기존 인증서·키를 Secret으로 묶는 명령이며 인증서를 발급하거나 client trust를 구성하지 않습니다. SAN, chain, 만료와 gateway credential 접근을 확인하세요. Kubernetes Gateway API는 다른 스키마의 GatewayClass/Gateway/HTTPRoute 부착과 controller 상태를 사용합니다.

</details>

## 문제 6: 관찰성 도구

<details>
<summary>Telemetry 구성 요소는 무엇을 측정하고 무엇을 설정해야 하나요?</summary>

Prometheus는 메트릭을 수집하고 Grafana는 dashboard를 표시하며 Kiali는 구성된 telemetry와 mesh 상태를 사용합니다. Jaeger 같은 tracing backend는 설정한 provider/collector가 보낸 trace를 저장합니다. Istio default profile이 자동 설치하는 도구들이 아닙니다.

다음 query는 app의 reviews에 대해 source reporter 한쪽을 선택합니다. Latency 출력은 **초**, traffic은 **초당 요청 수**, error는 5xx와 code 0을 포함합니다:

```promql
# latency
histogram_quantile(0.95, sum by (le) (rate(istio_request_duration_milliseconds_bucket{reporter="source",destination_service_name="reviews",destination_service_namespace="app"}[5m]))) / 1000

# traffic
sum(rate(istio_requests_total{reporter="source",destination_service_name="reviews",destination_service_namespace="app"}[5m]))

# error
(sum(rate(istio_requests_total{reporter="source",destination_service_name="reviews",destination_service_namespace="app",response_code=~"5..|0"}[5m])) or vector(0)) / sum(rate(istio_requests_total{reporter="source",destination_service_name="reviews",destination_service_namespace="app"}[5m]))

# cpu
sum(rate(container_cpu_usage_seconds_total{namespace="app",container="istio-proxy",pod!=""}[5m]))
```

CPU query는 가상의 istio-proxy Pod 이름이 아니라 **container** label을 선택합니다. 결과는 소비한 CPU core이며 단독으로 포화율을 뜻하지 않습니다. Limit·capacity와 throttling도 비교해야 하며 해당 kubelet/cAdvisor 메트릭이 필요합니다. 분모가 없거나 트래픽이 0이면 no-data/NaN이며 정상의 증거가 아닙니다. Error 분자의 0 fallback은 양수인 total이 있을 때만 오류율 0을 의미합니다.

Tracing에는 실제 OTLP gRPC receiver와 이름 있는 provider를 구성하고 Telemetry에서 선택합니다:

```yaml
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  meshConfig:
    enableTracing: true
    extensionProviders:
    - name: otel
      opentelemetry:
        service: otel-collector.observability.svc.cluster.local
        port: 4317
---
apiVersion: telemetry.istio.io/v1
kind: Telemetry
metadata:
  name: tracing
  namespace: app
spec:
  tracing:
  - providers:
    - name: otel
    randomSamplingPercentage: 1.0
```

IstioOperator는 istioctl 설치 입력이며 collector나 Jaeger를 배포하지 않습니다. 1% sampling은 예시이고 애플리케이션 context 전파가 필요합니다. Backend protocol, 보존과 sampling 비용을 확인하고 변경하세요.

Dashboard 명령은 설치되어 탐색할 수 있는 backend에 연결할 뿐입니다:

```bash
istioctl dashboard kiali
istioctl dashboard prometheus
istioctl dashboard grafana
istioctl dashboard jaeger
```

</details>

## 문제 7: Ambient Mode

<details>
<summary>Ambient와 sidecar 모드는 어떻게 다른가요?</summary>

| 항목 | Sidecar | Ambient |
|---|---|---|
| 배치 | 등록된 앱 Pod 옆의 Envoy | 노드별 ztunnel과 선택한 waypoint |
| L4 전송 | Workload proxy | ztunnel/HBONE |
| L7 기능 | 지원되는 Envoy 기능·API 범위 | 적절한 waypoint와 지원되는 부착·API 필요 |
| 리소스 | Pod 수, workload와 설정에 따라 다름 | 노드, waypoint 배포·용량과 workload에 따라 다름 |
| 도입 | 대상 Pod 주입·재생성 | CNI·enrollment 전제. 기존 sidecar 전환에는 통제된 rollout 필요 |
| 성능 | 실제 workload 측정 | L4/L7 경로를 분리 측정. 일정한 성능 우위·절감률 없음 |

[Ambient 설치·마이그레이션 가이드](../../service-mesh/istio/advanced/01-ambient-mode.md)를 따르세요. 임의의 공유 설치에 profile=ambient를 적용하고 default에 label을 붙이는 것은 완전한 마이그레이션 절차가 아닙니다. CNI 호환, NetworkPolicy/HBONE, 충돌하는 sidecar label, waypoint 기능과 실제 enrollment를 확인해야 합니다.

```bash
kubectl get namespace app --show-labels
istioctl ztunnel-config workloads -n istio-system
```

이 읽기 명령은 workload를 등록하거나 L7 정책을 검증하지 않습니다. Service·Pod 수와 고정된 “노드당 50MB”만으로 사용량·절감을 예측할 수 없습니다.

</details>

## 문제 8: 복원력 패턴

<details>
<summary>Outlier detection, connection pool 제한과 rate limiting의 차이는?</summary>

Outlier detection은 관측 실패에 따라 비정상 endpoint를 제외합니다. Connection pool circuit breaker는 연결, 대기 요청, 활성 요청 같은 리소스를 제한하며 초당 요청 quota가 아닙니다.

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews
  namespace: app
spec:
  host: reviews.app.svc.cluster.local
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 100
      http:
        http1MaxPendingRequests: 50
        http2MaxRequests: 100
    outlierDetection:
      consecutive5xxErrors: 5
      interval: 30s
      baseEjectionTime: 30s
      maxEjectionPercent: 50
```

현재 필드는 consecutive5xxErrors입니다. 연속 실패 검사는 inline으로 작동할 수 있어 interval이 모든 제외 전에 30초 기다린다는 뜻은 아닙니다. 반복 제외에서 baseEjectionTime이 증가할 수 있으며 proxy별 endpoint·capacity 동작이 중요합니다. maxEjectionPercent를 전체 가용성 보장으로 해석하면 안 됩니다.

9080의 **sidecar inbound** HTTP listener에 적용하는 다음 local token bucket은 초기 burst 100개, 초당 token 10개 보충의 예시입니다:

```yaml
apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata:
  name: reviews-local-rate-limit
  namespace: app
spec:
  workloadSelector:
    labels:
      app: reviews
  configPatches:
  - applyTo: HTTP_FILTER
    match:
      context: SIDECAR_INBOUND
      listener:
        portNumber: 9080
        filterChain:
          filter:
            name: envoy.filters.network.http_connection_manager
            subFilter:
              name: envoy.filters.http.router
    patch:
      operation: INSERT_BEFORE
      value:
        name: envoy.filters.http.local_ratelimit
        typed_config:
          '@type': type.googleapis.com/envoy.extensions.filters.http.local_ratelimit.v3.LocalRateLimit
          stat_prefix: http_local_rate_limiter
          token_bucket:
            max_tokens: 100
            tokens_per_fill: 10
            fill_interval: 1s
          filter_enabled:
            runtime_key: local_rate_limit_enabled
            default_value:
              numerator: 100
              denominator: HUNDRED
          filter_enforced:
            runtime_key: local_rate_limit_enforced
            default_value:
              numerator: 100
              denominator: HUNDRED
```

Type URL, workload/listener/router match와 enable/enforce 비율이 이 예제의 필수 구성입니다. Bucket만 있고 활성화·적용되지 않으면 실제 제한이 아닙니다. 기본적으로 proxy process별 제한이라 replica 수에 따라 전체 용량이 늘며 메시 전역 quota가 아닙니다. Waypoint EnvoyFilter는 지원되지 않습니다. 전역 제한에는 rate-limit service와 일치하는 descriptor가 필요합니다. [Rate limiting](../../service-mesh/istio/resilience/02-rate-limiting.md)을 참고하세요.

</details>

## 문제 9: EKS Locality Load Balancing

<details>
<summary>Locality 선호는 무엇을 제공하며 무엇을 보장하지 않나요?</summary>

Locality는 endpoint/source 토폴로지 정보로 적절한 목적지를 선호합니다. 다음은 앞의 reviews DestinationRule을 **대체**하며 outlier detection과 region/zone 우선순위를 사용합니다:

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews
  namespace: app
spec:
  host: reviews.app.svc.cluster.local
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 100
      http:
        http1MaxPendingRequests: 50
        http2MaxRequests: 100
    outlierDetection:
      consecutive5xxErrors: 5
      interval: 30s
      baseEjectionTime: 30s
      maxEjectionPercent: 50
    loadBalancer:
      localityLbSetting:
        enabled: true
        failoverPriority:
        - topology.kubernetes.io/region
        - topology.kubernetes.io/zone
```

하나의 locality 설정에서 distribute와 failover 또는 failoverPriority를 혼합하면 안 됩니다. 80/20 distribute는 정상일 때도 20%를 원격으로 보내며 “장애 때만 원격”이 아닙니다. Failover에는 발견되고 연결 가능한 endpoint와 충분한 용량이 필요합니다. Service 선택에서 제외되거나 registry에 없는 원격 AZ·cluster로 갈 수 없습니다.

```bash
kubectl get nodes -L topology.kubernetes.io/region,topology.kubernetes.io/zone
```

실제 label과 proxy endpoint locality를 확인하세요. AWS 계정 사이에서 AZ 이름이 다를 수 있으므로 물리적 zone 비교에는 적절한 AZ ID 매핑을 사용합니다. 비용은 트래픽 양과 실제 EC2/load-balancer/network 경로에 따라 달라집니다. Locality 활성화만으로 보편적인 $0.01/GB 요율, 고정 지연이나 85% 절감이 나오지는 않습니다.

</details>

## 문제 10: Amazon EKS 통합 및 모범 사례

<details>
<summary>EKS에 Istio를 설치·운영하기 전에 무엇을 확인해야 하나요?</summary>

1. 정확한 Istio/Kubernetes/EKS 지원 교집합과 고정한 CLI/chart를 사용하세요. 기본 제공 production profile은 없습니다. 설치 소유 도구를 통해 검토한 Helm/istioctl 설정을 사용합니다.
2. Load balancer controller를 구분하세요. AWS Load Balancer Controller, EKS Auto Mode와 기존 provisioning은 소유·설정이 다릅니다. Service selector·port를 실제 gateway와 맞추고 NLB 또는 gateway의 TLS 종료 위치를 결정합니다. 평문을 TLS listener로 보내거나 의도하지 않은 이중 TLS를 만들지 마세요.
3. AWS API를 호출하는 load balancer controller·telemetry collector 같은 구성 요소에 권한을 부여합니다. Envoy가 트래픽을 전달한다는 이유만으로 IAM role이 필요하지는 않습니다. IRSA 또는 지원되는 EKS Pod Identity의 trust·permission을 구성해야 하며 annotation 하나로 끝나지 않습니다.
4. 필요한 방향의 네트워크 경로만 허용하세요. Proxy intercept port는 security group에 무차별 노출할 목록이 아닙니다. 실제 webhook/xDS, health check와 ingress/ambient 경로를 고려합니다.
5. Workload 근거로 Istiod/proxy를 크기 조정하고 scheduling·가용 용량을 준비하세요. PDB는 일부 자발적 disruption을 다루며 replica 수만으로 zone 분산이나 모든 장애 보호를 보장하지 않습니다.
6. Metrics, logs와 tracing을 각각 구성하세요. Fluent Bit cloudwatch_logs output 조각만으로 Container Insights나 완전한 CRI input/parser/IAM/log-stream pipeline이 되지는 않습니다.

Control-plane HPA와 proxy request/limit의 설치 입력 예시입니다:

```yaml
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  components:
    pilot:
      k8s:
        resources:
          requests:
            cpu: 500m
            memory: 2Gi
        hpaSpec:
          minReplicas: 3
          maxReplicas: 5
  values:
    global:
      proxy:
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 500m
            memory: 1Gi
```

Replica 3–5개와 수량은 운영 검증된 sizing이 아닙니다. HPA metric, 배치와 가용 용량을 확인하세요. Ambient와 설정 scope의 효과는 실제 resource·billing 측정으로 평가하며 보편적인 85% 또는 30–50% 절감은 없습니다.

전체 절차는 [AWS 통합](../../service-mesh/istio/04-aws-integration.md)과 [모범 사례](../../service-mesh/istio/best-practices.md)를 참고하세요.

</details>

## 보너스 문제: Progressive Delivery

<details>
<summary>Progressive delivery 분석의 유용성과 한계는 무엇인가요?</summary>

완전한 rollout에는 실제 라우팅 대상, stable 용량, 명시적인 분석 인자와 유한하고 의미 있는 측정 정책이 필요합니다. 다음은 canary Service의 요청량, HTTP 가용성과 P95 latency를 검사하는 template입니다:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: comprehensive-analysis
  namespace: rollouts-demo
spec:
  args:
  - name: service-name
  - name: namespace
  metrics:
  - name: request-volume
    interval: 30s
    successCondition: len(result) == 1 && !isNaN(result[0]) && !isInf(result[0]) && result[0] >= 20
    failureLimit: 0
    provider:
      prometheus:
        address: http://prometheus.istio-system.svc.cluster.local:9090
        query: sum(increase(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}"}[2m]))
    count: 5
  - name: http-availability
    interval: 30s
    successCondition: len(result) == 1 && !isNaN(result[0]) && !isInf(result[0]) && result[0] >= 0.99
    failureLimit: 0
    provider:
      prometheus:
        address: http://prometheus.istio-system.svc.cluster.local:9090
        query: |-
          (sum(rate(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}",response_code!~"5..|0"}[2m])) or vector(0))
          /
          sum(rate(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}"}[2m]))
    count: 5
  - name: latency-p95
    interval: 30s
    successCondition: len(result) == 1 && !isNaN(result[0]) && !isInf(result[0]) && result[0] <= 0.5
    failureLimit: 0
    provider:
      prometheus:
        address: http://prometheus.istio-system.svc.cluster.local:9090
        query: |-
          histogram_quantile(0.95,
            sum by (le) (rate(istio_request_duration_milliseconds_bucket{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}"}[2m]))
          ) / 1000
    count: 5
  - name: http-error-rate
    interval: 30s
    successCondition: len(result) == 1 && !isNaN(result[0]) && !isInf(result[0]) && result[0] <= 0.01
    failureLimit: 0
    provider:
      prometheus:
        address: http://prometheus.istio-system.svc.cluster.local:9090
        query: |-
          (sum(rate(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}",response_code=~"5..|0"}[2m])) or vector(0))
          /
          sum(rate(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}"}[2m]))
    count: 5
```

완전한 Rollout의 일치하는 analysis step에서 참조하세요. 빠진 selector/template/Service를 대신하지 않습니다. 임계값은 예시이며 query selector, 단위, 트래픽 양과 업무 SLO가 일치해야 합니다.

실패 측정, provider error, inconclusive, abort와 이전 revision 재배포는 서로 다른 상태입니다. AnalysisRun/Rollout 상태를 확인하고 모두 즉시 rollback으로 부르지 마세요. Abort가 DB 쓰기나 애플리케이션 부작용을 되돌리지도 않습니다. Controller 간격, stable backend 가용성과 설정 전파가 복구를 제한합니다.

자동화는 반복 판단을 줄일 수 있지만 metric gate가 보편적인 안전한 배포나 사람의 진단 불필요를 입증하지는 않습니다. 무트래픽, 메트릭 누락, 전부 실패, NaN/infinity와 복구를 검사하세요. [전체 롤아웃 가이드](../../service-mesh/istio/advanced/08-argo-rollouts.md)에 주변 리소스와 검증 경계가 있습니다.

</details>

## 자기 점검

11개 답변으로 복습할 주제를 찾으세요. 높은 퀴즈 점수는 운영 준비의 증거가 아닙니다. 설정 검토와 통제된 환경의 실습 검증을 함께 수행해야 합니다.

## 학습 자료

- [유지 관리되는 Istio 문서](../../service-mesh/istio/README.md)
- [Istio 공식 문서](https://istio.io/latest/docs/)
- [Argo Rollouts Istio 통합](https://argo-rollouts.readthedocs.io/en/stable/features/traffic-management/istio/)
- [Argo 분석 의미](https://argo-rollouts.readthedocs.io/en/stable/features/analysis/)
- [Prometheus instant query 결과](https://argo-rollouts.readthedocs.io/en/stable/analysis/prometheus/)
- [Istio TLS 설정](https://istio.io/latest/docs/ops/configuration/traffic-management/tls-configuration/)
- [Istio API 참조](https://istio.io/latest/docs/reference/config/)
