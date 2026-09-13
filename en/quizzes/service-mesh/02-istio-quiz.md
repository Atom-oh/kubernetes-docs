# Istio Quiz

> **Last Updated**: September 11, 2026 · Example checks: Istio 1.31.0 / Argo Rollouts 1.10.0

This quiz covers the [maintained Istio guides](../../service-mesh/istio/README.md). Compatibility belongs in the [installation guide](../../service-mesh/istio/01-installation.md); a generic Kubernetes minimum is not a support matrix. Examples are learning aids, not production-tested deployments. Replace illustrative namespaces, hostnames, identities and backend endpoints with verified inputs.

## Question 1: Service Mesh Basic Concepts

<details>
<summary>What is a service mesh and what are its main features?</summary>

A service mesh adds infrastructure-level control and observation of service communication. Its capabilities include routing/load balancing, explicitly budgeted retries/timeouts, workload identity and transport security, authorization, metrics, access logs and tracing integration.

Istio offers sidecar and ambient data planes with different L4/L7 capabilities and policy attachment. Many controls do not require business-logic changes, but applications still participate in trace-context propagation, graceful shutdown and durable idempotency. A mesh does not automatically make non-idempotent retries safe or install every observability backend.

</details>

## Question 2: Istio Architecture

<details>
<summary>What are the control-plane and data-plane roles?</summary>

- **Istiod** watches service/configuration state, translates configuration and distributes it to proxies. Kubernetes persists CRD objects. Workload certificate issuance/renewal uses Istiod's configured CA integration.
- **Sidecar mode** uses Envoy alongside each enrolled application Pod for its intercepted traffic.
- **Ambient mode** uses node-level ztunnel for L4 transport/identity and optional Envoy waypoints for supported L7 features.
- **Gateways** handle selected ingress/egress paths. Their Deployment/controller is separate from a routing configuration resource.

“All traffic is intercepted” needs verification of exclusions, protocols and enrollment. There is no universal 85% resource reduction: compare actual proxy counts, requests/limits, usage, waypoint capacity, node packing and operational cost. See [architecture](../../service-mesh/istio/03-architecture.md) and the [ambient resource model](../../service-mesh/istio/advanced/01-ambient-mode.md).

</details>

## Question 3: Traffic Management and Argo Rollouts Integration

<details>
<summary>How do Istio routing and Argo analysis combine for a canary rollout?</summary>

Argo changes weights on a named Istio HTTP route while maintaining stable/canary backend selection. A Rollout also needs a selector, Pod template, real Services, namespace enrollment and the corresponding VirtualService. The following is **only a fragment under Rollout.spec**, using the host-based example in the [complete rollout guide](../../service-mesh/istio/advanced/08-argo-rollouts.md):

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

The named success-rate template below is finite. It checks both request volume and HTTP availability for the **canary Service**, using one reporter side to avoid counting both proxies:

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

The Prometheus backend must exist and scrape the relevant proxies. The sidecar example expects source-reporter HTTP metrics and real canary traffic; an ambient L4 path alone does not provide those L7 measurements.

Argo's Prometheus result is an array, so conditions inspect result[0] only after checking its length. Empty, NaN and infinite results must not pass. The numerator's zero fallback handles all-failure traffic, while the volume gate prevents zero/missing traffic being declared healthy. “Availability” here excludes 5xx and code 0; it is not a guarantee of business success or 2xx-only responses.

The old scalar result >= 0.95, omitted provider address, missing latency template and incomplete Rollout were not a complete automation recipe. failureLimit counts **allowed failures**: 2 allows two and fails on the third; this example uses 0. Actual reaction time depends on measurement intervals, controller reconciliation and route propagation, not an immediate rollback promise.

</details>

## Question 4: Security Features

<details>
<summary>How do mTLS, authorization and JWT validation differ?</summary>

PeerAuthentication controls accepted inbound workload mTLS. It does not make the client's outbound TLS policy. The following namespace policy assumes callers have been prepared for STRICT; placing it in the mesh root namespace would have a wider effect:

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

For **sidecar-enrolled** backend Pods, these policies require the frontend workload identity, a validated JWT and an allowed GET path together:

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

The first policy is an empty **ALLOW** policy for the selected backend, giving default-deny behavior until an ALLOW rule matches. It is not an explicit DENY action that overrides the subsequent allow. Other matching ALLOW policies can widen access, so review the complete policy set.

RequestAuthentication validates a supplied JWT but alone accepts requests without one. The requestPrincipals condition is what makes a validated JWT necessary here. The issuer, JWKS URL and audience are placeholders for a real provider. Workload principal and JWT principal are different identities.

L7 policies in ambient require supported waypoint attachment; do not copy a sidecar selector-based HTTP policy to ztunnel. See the [security guides](../../service-mesh/istio/security/README.md) for targetRefs, migration and trust boundaries.

</details>

## Question 5: Gateway and Ingress

<details>
<summary>How are gateway TLS termination and application routing configured?</summary>

This example uses **Istio Gateway**, not Kubernetes Gateway API. The gateway Deployment, matching Pod labels and Service ports must already be configured. The app runs in bookinfo, while the gateway workload and credential are in istio-ingress:

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

SIMPLE terminates downstream TLS, after which the VirtualService uses HTTP routing. The HTTP listener redirects only the admitted example domain. The route explicitly disables retries, including writes. Replace the owned domain and actual namespace/Service/selector values before use.

```bash
kubectl -n istio-ingress create secret tls bookinfo-secret \
  --key=bookinfo.key \
  --cert=bookinfo-fullchain.pem
```

This packages an existing certificate/key; it does not issue a certificate or establish client trust. Check SANs, chain, expiry and the gateway's credential access. Kubernetes Gateway API uses GatewayClass/Gateway/HTTPRoute attachment and controller status instead of this resource schema.

</details>

## Question 6: Observability Tools

<details>
<summary>What do the telemetry components measure, and what must be configured?</summary>

Prometheus collects metrics; Grafana renders dashboards; Kiali uses configured telemetry and mesh state; a tracing backend such as Jaeger stores traces sent through the configured provider/collector. These are integrations, not tools automatically installed by the Istio default profile.

The following queries select one source-reporter stream for reviews in app. The latency output is **seconds**, traffic is **requests/second**, and errors include 5xx plus code 0:

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

The CPU query selects the **container** label, not a fictitious Pod name containing istio-proxy. Its result is CPU cores consumed, not by itself a saturation percentage; compare limits/capacity and throttling. It needs the corresponding kubelet/cAdvisor metrics. Empty/zero-traffic denominators produce no-data/NaN states rather than proof of health; the error numerator fallback means 0 only when a positive total exists.

For tracing, configure an actual OTLP gRPC receiver and a named provider, then select it with Telemetry:

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

The IstioOperator block is istioctl installation input. It does not deploy the collector or Jaeger. The 1% sampling value is illustrative, not a universal target; applications must propagate context. Inspect backend protocols, retention and sampling costs before changing them.

Dashboard commands only connect to installed, discoverable backends:

```bash
istioctl dashboard kiali
istioctl dashboard prometheus
istioctl dashboard grafana
istioctl dashboard jaeger
```

</details>

## Question 7: Ambient Mode

<details>
<summary>How does ambient differ from sidecar mode?</summary>

| Aspect | Sidecar | Ambient |
|---|---|---|
| Placement | Envoy alongside each enrolled app Pod | Node-level ztunnel plus selected waypoints |
| L4 transport | Workload proxy | ztunnel/HBONE |
| L7 features | Supported Envoy features and API scope | Require an appropriate waypoint and supported attachment/API |
| Resources | Depends on Pod count, workload and configuration | Depends on nodes, waypoint deployment/capacity and workload |
| Adoption | Injection/recreation of intended Pods | CNI and enrollment prerequisites; migration from existing sidecars still needs a controlled rollout |
| Performance | Measure the actual workload | Measure L4 and L7 paths separately; no fixed superiority or savings percentage |

Use the [ambient installation/migration guide](../../service-mesh/istio/advanced/01-ambient-mode.md). Applying profile=ambient to an arbitrary shared installation and labeling default is not a safe complete migration procedure. Check CNI compatibility, NetworkPolicy/HBONE, conflicting sidecar labels, waypoint features and effective enrollment.

```bash
kubectl get namespace app --show-labels
istioctl ztunnel-config workloads -n istio-system
```

These read-only checks do not themselves enroll workloads or prove L7 policy enforcement. Service count, Pod count and a fixed “50MB per node” are not sufficient to predict usage or savings.

</details>

## Question 8: Resilience Patterns

<details>
<summary>How do outlier detection, connection-pool limits and rate limiting differ?</summary>

Outlier detection ejects unhealthy endpoints based on observed failures; connection-pool circuit breakers bound selected resources such as connections, pending requests or active requests. They do not impose a requests-per-second quota.

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

consecutive5xxErrors is the current field. Consecutive-failure detection can act inline; interval is not a promise to wait 30 seconds before every ejection. baseEjectionTime can increase on repeat ejections, and per-proxy endpoint/capacity behavior matters. A maxEjectionPercent value should not be read as a global availability guarantee.

For a **sidecar inbound** HTTP listener on 9080, this illustrative local token bucket has an initial burst capacity 100 and refills 10 tokens per second:

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

The type URL, workload/listener/router match, and enable/enforce fractions are required parts of this example. A bucket that is configured but not enabled/enforced is not an effective limit. The limit is local to a proxy process by default, so replicas multiply aggregate capacity; it is not a mesh-global quota. Waypoint EnvoyFilter use is unsupported. Global limits require a rate-limit service and matching descriptors; see [rate limiting](../../service-mesh/istio/resilience/02-rate-limiting.md).

</details>

## Question 9: Locality Load Balancing on EKS

<details>
<summary>What does locality preference provide, and what does it not guarantee?</summary>

Locality uses endpoint/source topology information to prefer suitable destinations. This **alternative** to the earlier reviews DestinationRule uses region/zone priority with outlier detection:

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

Do not combine distribute with failover or failoverPriority in one locality setting. An 80/20 distribute rule intentionally sends 20% remotely while healthy; it is not “remote only on failure.” Failover needs reachable, discovered endpoints and enough capacity. It cannot reach a remote AZ/cluster excluded by Service selection or absent from the registry.

```bash
kubectl get nodes -L topology.kubernetes.io/region,topology.kubernetes.io/zone
```

Verify the actual labels and proxy endpoint locality. AZ names can differ across AWS accounts; use appropriate AZ-ID mapping when comparing physical zones across accounts. Cost depends on traffic volume and the exact EC2/load-balancer/network path; neither a universal $0.01/GB rule, fixed latency nor 85% savings follows from enabling locality.

</details>

## Question 10: Amazon EKS Integration and Best Practices

<details>
<summary>What must be checked before installing or operating Istio on EKS?</summary>

1. Use the exact supported Istio/Kubernetes/EKS intersection and a pinned CLI/chart. There is no built-in production profile. Use reviewed Helm/istioctl configuration through the installation's owner.
2. Identify the load balancer controller: AWS Load Balancer Controller, EKS Auto Mode and legacy provisioning use different ownership/settings. Match Service selectors/ports to the actual gateway. Decide TLS termination at the NLB or gateway; do not accidentally send plaintext to a TLS listener or add unintended double TLS.
3. Scope AWS permissions to the component calling AWS APIs, such as the load balancer controller or telemetry collector. Envoy does not need an IAM role merely to forward traffic. Configure trust and permissions for IRSA or supported EKS Pod Identity integration; an annotation alone is not a complete setup.
4. Open only required directional network paths. Proxy interception ports are not a list to expose indiscriminately in security groups. Include webhook/xDS, health checks and the actual ingress/ambient paths where relevant.
5. Size Istiod/proxies from workload evidence and provide scheduling/availability capacity. PDBs address selected voluntary disruptions; replica count alone does not ensure zone diversity or protect against all failures.
6. Configure metrics, logs and tracing separately. A Fluent Bit cloudwatch_logs output fragment alone is not Container Insights or a complete CRI-input/parser/IAM/log-stream pipeline.

An illustrative installation input for control-plane HPA and proxy requests/limits is:

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

The 3–5 replicas and resource quantities are examples, not validated production sizing. Check HPA metrics, placement and available capacity. Assess ambient and configuration scoping with actual resource/billing measurements; there is no general 85% or 30–50% saving guarantee.

Use the [AWS integration guide](../../service-mesh/istio/04-aws-integration.md) and [best practices](../../service-mesh/istio/best-practices.md) for complete procedures.

</details>

## Bonus Question: Progressive Delivery

<details>
<summary>What makes progressive-delivery analysis useful, and where are its limits?</summary>

A complete rollout needs real routing targets, stable capacity, explicit analysis arguments and a finite, meaningful measurement policy. The following template extends the canary Service example with request volume, HTTP availability and P95 latency:

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

Reference this template from a matching analysis step in a complete Rollout. It is not a replacement for the missing selector/template/Services of an incomplete Rollout example. Thresholds are illustrative; query selectors, units, traffic volume and the business SLO must agree.

An unsuccessful measurement, provider error, inconclusive result, abort and subsequent deployment of a previous revision are distinct states. Inspect AnalysisRun/Rollout status; do not call them all instantaneous rollback. An abort cannot undo database writes or other application side effects. Controller intervals, availability of the stable backend and configuration propagation bound recovery.

Automation can reduce repetitive decisions, but no metric gate establishes universal safe deployment or guarantees that human diagnosis is unnecessary. Test no-traffic, missing-series, all-failure, NaN/infinite and recovery cases. The [complete rollout guide](../../service-mesh/istio/advanced/08-argo-rollouts.md) contains the surrounding resources and validation boundaries.

</details>

## Self-assessment

Use the 11 answers to identify topics to revisit. A high quiz score is not evidence of production operational readiness; include configuration review and hands-on validation in a controlled environment.

## Learning Resources

- [Maintained Istio documentation](../../service-mesh/istio/README.md)
- [Istio official documentation](https://istio.io/latest/docs/)
- [Argo Rollouts Istio integration](https://argo-rollouts.readthedocs.io/en/stable/features/traffic-management/istio/)
- [Argo analysis semantics](https://argo-rollouts.readthedocs.io/en/stable/features/analysis/)
- [Prometheus instant query results](https://argo-rollouts.readthedocs.io/en/stable/analysis/prometheus/)
- [Istio TLS configuration](https://istio.io/latest/docs/ops/configuration/traffic-management/tls-configuration/)
- [Istio API reference](https://istio.io/latest/docs/reference/config/)
