# Outlier Detection

> **Reviewed**: September 11, 2026 · Istio 1.31. Independent sidecar examples; create the stated namespaces and real workloads/endpoints before testing. Same-host examples are alternatives. Values are illustrative and have not been load-tested.

Outlier Detection is a form of the Circuit Breaker pattern that automatically detects abnormally behaving service instances and removes them from the traffic pool.

## Table of Contents

1. [Overview](#overview)
2. [How It Works](#how-it-works)
3. [Basic Configuration](#basic-configuration)
4. [Advanced Configuration](#advanced-configuration)
5. [Protecting External Services (ServiceEntry)](#protecting-external-services-serviceentry)
6. [Practical Examples](#practical-examples)
7. [Monitoring](#monitoring)
8. [Troubleshooting](#troubleshooting)

## Overview

Outlier detection is passive and local to each observing proxy. With HTTP visibility, it counts qualifying upstream responses and/or local connection failures. It does not use a DestinationRule latency threshold or send periodic recovery probes. Ejection changes that proxy’s load-balancing eligibility; it does not delete a Pod or repair the service.


### Key Features

1. **Detection**: Counts configured consecutive HTTP or transport failures.
2. **Ejection**: Excludes a host if the ejection limit and enforcement allow it.
3. **Re-entry**: Makes the host eligible again after its ejection period; actual recovery still needs successful traffic.

## How It Works

### Outlier Detection Process

A success resets the relevant consecutive-error sequence. A qualifying failure reaching the threshold can trigger ejection inline, without waiting for `interval`. The ejection duration grows with repeated ejections (base duration × multiplier, capped by Envoy); this is not a fixed 30-second probe or exponential doubling.


### Detection Methods

| Method | Description | Use Scenario |
|--------|-------------|--------------|
| **Consecutive Errors** | Detect consecutive 5xx errors | Application crash |
| **Gateway Errors** | Detect 502, 503, 504 errors | Service overload |
| **Connection Failures** | Detect TCP connection failures | Network issues |
| **Latency** | Not a DestinationRule outlier threshold | Observe latency; set application/route timeouts separately |

## Basic Configuration

### Consecutive Error Based Detection

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews-outlier
  namespace: default
spec:
  host: reviews
  trafficPolicy:
    outlierDetection:
      consecutive5xxErrors: 5
      interval: 30s
      baseEjectionTime: 30s
      maxEjectionPercent: 50
      minHealthPercent: 0
```

### Key Parameter Descriptions

#### consecutive5xxErrors
- **Description**: Threshold for consecutive error occurrences
- **Default**: 5
- **Illustrative tuning range**: 3-10 (depending on service characteristics)

```yaml
# Sensitive service (fast detection)
consecutive5xxErrors: 3

# General service
---
consecutive5xxErrors: 5

# Lenient setting (prevent false positives)
---
consecutive5xxErrors: 10
```

#### interval
- **Description**: Periodic ejection sweep interval; consecutive-error detection runs inline
- **Default**: 10s
- **Illustrative tuning range**: 10s-60s

```yaml
# Fast detection (high load)
interval: 10s

# General case
---
interval: 30s

# Stable service
---
interval: 60s
```

#### baseEjectionTime
- **Description**: Minimum time an instance is ejected
- **Default**: 30s
- **Illustrative tuning range**: 30s-300s

```yaml
# Fast recovery attempt
baseEjectionTime: 30s

# General case
---
baseEjectionTime: 60s

# Cautious recovery
---
baseEjectionTime: 300s
```

#### maxEjectionPercent
- **Description**: Maximum percentage of instances that can be ejected simultaneously
- **Default**: 10%
- **Illustrative tuning range**: 10%-50%

```yaml
# Conservative (stability first)
maxEjectionPercent: 10

# Balanced setting
---
maxEjectionPercent: 30

# Aggressive (quality first)
---
maxEjectionPercent: 50
```

## Advanced Configuration

### Gateway Error Based Detection

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews-gateway-errors
  namespace: default
spec:
  host: reviews
  trafficPolicy:
    outlierDetection:
      consecutiveGatewayErrors: 3
      interval: 10s
      baseEjectionTime: 60s
      maxEjectionPercent: 50
      minHealthPercent: 0
```

### Healthy-Pool Panic Threshold

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews-panic-threshold-example
  namespace: default
spec:
  host: reviews
  trafficPolicy:
    outlierDetection:
      consecutive5xxErrors: 5
      interval: 30s
      baseEjectionTime: 30s
      minHealthPercent: 50
      maxEjectionPercent: 30
```

`minHealthPercent: 50` is a fail-open/panic choice: below the healthy-host threshold, the proxy can use unhealthy hosts as well. It is not a minimum request count, healthy-capacity guarantee or split-brain prevention. The Istio default is0; other examples use0 to disable this panic threshold. The ejection cap does not make remaining endpoints healthy.

### Connection Failure Based Detection

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews-connection-errors
  namespace: default
spec:
  host: reviews
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 100
      http:
        http1MaxPendingRequests: 10
        maxRequestsPerConnection: 2
    outlierDetection:
      consecutiveLocalOriginFailures: 5
      interval: 10s
      baseEjectionTime: 30s
      maxEjectionPercent: 50
      splitExternalLocalOriginErrors: true
      minHealthPercent: 0
```

### Success Rate Based Detection (Advanced)

Envoy has statistical success-rate detection, with minimum host/request-volume and deviation parameters; it is not simply “below95%.” The Istio1.31 DestinationRule API does not expose `enforcingConsecutiveErrors`/`enforcingSuccessRate` or those statistical thresholds. The [released implementation](https://github.com/istio/istio/blob/1.31.0/pilot/pkg/networking/core/cluster_traffic_policy.go) explicitly disables success-rate enforcement. `splitExternalLocalOriginErrors` separates error classes; it is not a minimum request count. Use the supported consecutive-error fields here. Advanced EnvoyFilter changes require version-specific configuration and runtime validation.

## Protecting External Services (ServiceEntry)

Register external APIs or legacy systems as ServiceEntry and apply Outlier Detection to prevent failure propagation.

### External API Protection Architecture

![An application pod's Envoy sidecar applies outlier detection to three external API instances registered as a ServiceEntry, continuing to send traffic to the two healthy instances while ejecting the one returning errors.](../../../.gitbook/assets/en-service-mesh-istio-resilience-01-outlier-detection-2.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-resilience-01-outlier-detection-2.html)

These HTTP-aware external API examples require the application to call **HTTP port80** and the sidecar to originate TLS to target443. They set SNI/SAN and use the proxy OS trust store; mount an appropriate CA bundle for a private CA. Application-to-sidecar traffic is plaintext, so this is unsuitable when that hop must also be encrypted. For application-originated HTTPS, use passthrough without another SIMPLE TLS layer; Envoy then sees transport failures, not HTTP status/latency or HTTP retry rules. Verify enrollment, routing and certificate validation before sending credentials. Hosts/IPs below are examples, not provisioned services; substitute authorized endpoints.

### Example 1: Single External API (DNS Based)

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: external-payment-api
  namespace: payment
spec:
  hosts:
  - api.payment-provider.com
  resolution: DNS
  ports:
  - number: 80
    name: http
    protocol: HTTP
    targetPort: 443
  location: MESH_EXTERNAL
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: external-payment-api
  namespace: payment
spec:
  host: api.payment-provider.com
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 100
        connectTimeout: 3s
      http:
        http1MaxPendingRequests: 50
        http2MaxRequests: 100
        maxRequestsPerConnection: 10
        maxRetries: 3
    outlierDetection:
      consecutive5xxErrors: 3
      consecutiveGatewayErrors: 2
      interval: 10s
      baseEjectionTime: 30s
      maxEjectionPercent: 50
      splitExternalLocalOriginErrors: true
      consecutiveLocalOriginFailures: 3
      minHealthPercent: 0
    portLevelSettings:
    - port:
        number: 80
      tls:
        mode: SIMPLE
        sni: api.payment-provider.com
        subjectAltNames:
        - api.payment-provider.com
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: external-payment-api
  namespace: payment
spec:
  hosts:
  - api.payment-provider.com
  http:
  - name: no-retries
    route:
    - destination:
        host: api.payment-provider.com
        port:
          number: 80
    retries:
      attempts: 0
    timeout: 5s
```

**Usage Example**:
```go
package payment

import (
    "bytes"
    "context"
    "fmt"
    "io"
    "net/http"
    "time"
)

var paymentClient = &http.Client{
    Timeout: 5 * time.Second,
    CheckRedirect: func(req *http.Request, via []*http.Request) error {
        return http.ErrUseLastResponse
    },
}

// payload, authentication and payment-provider idempotency are application concerns.
// Requires the port80-to443 sidecar TLS-origination policy above.
func processPayment(ctx context.Context, payload []byte) error {
    req, err := http.NewRequestWithContext(ctx, http.MethodPost,
        "http://api.payment-provider.com/v1/charge", bytes.NewReader(payload))
    if err != nil { return err }
    req.Header.Set("Content-Type", "application/json")
    resp, err := paymentClient.Do(req)
    if err != nil { return fmt.Errorf("payment transport failed: %w", err) }
    defer resp.Body.Close()
    _, _ = io.Copy(io.Discard, io.LimitReader(resp.Body, 1<<20))
    if resp.StatusCode < 200 || resp.StatusCode >= 300 {
        return fmt.Errorf("payment endpoint returned HTTP %d", resp.StatusCode)
    }
    return nil
}
```

Outlier detection affects later host selection; it does not retry or deduplicate a payment. The VirtualService explicitly disables mesh retries. A DNS name may expose only one Envoy host; ejection does not guarantee another provider endpoint exists. A transport error does not establish whether the remote transaction committed.

### Example 2: Multiple External API Endpoints

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: external-weather-api
  namespace: weather
spec:
  hosts:
  - weather.api.com
  resolution: STATIC
  ports:
  - number: 80
    name: http
    protocol: HTTP
    targetPort: 443
  location: MESH_EXTERNAL
  endpoints:
  - address: 203.0.113.10
    labels:
      region: us-east-1
    locality: us-east-1
  - address: 203.0.113.20
    labels:
      region: us-west-2
    locality: us-west-2
  - address: 203.0.113.30
    labels:
      region: eu-central-1
    locality: eu-central-1
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: external-weather-api
  namespace: weather
spec:
  host: weather.api.com
  trafficPolicy:
    loadBalancer:
      simple: LEAST_REQUEST
    connectionPool:
      tcp:
        maxConnections: 50
        connectTimeout: 5s
      http:
        http1MaxPendingRequests: 20
        maxRequestsPerConnection: 5
    outlierDetection:
      consecutive5xxErrors: 5
      consecutiveGatewayErrors: 3
      consecutiveLocalOriginFailures: 5
      interval: 30s
      baseEjectionTime: 60s
      maxEjectionPercent: 33
      splitExternalLocalOriginErrors: true
      minHealthPercent: 0
    portLevelSettings:
    - port:
        number: 80
      tls:
        mode: SIMPLE
        sni: weather.api.com
        subjectAltNames:
        - weather.api.com
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: external-weather-api
  namespace: weather
spec:
  hosts:
  - weather.api.com
  http:
  - name: no-retries
    route:
    - destination:
        host: weather.api.com
        port:
          number: 80
    retries:
      attempts: 0
    timeout: 5s
```

The three documentation IPs represent members of one upstream pool. `maxEjectionPercent` is a pool cap, not “one per region.” Labels are metadata; `locality` provides topology. Rounding, discovered host count and current ejections affect what is actually removed.

### Example 3: Legacy Database Protection

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: legacy-postgres
  namespace: database
spec:
  hosts:
  - legacy-db.company.internal
  resolution: DNS
  ports:
  - number: 5432
    name: tcp-postgres
    protocol: TCP
  location: MESH_EXTERNAL
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: legacy-postgres
  namespace: database
spec:
  host: legacy-db.company.internal
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 50
        connectTimeout: 10s
    outlierDetection:
      consecutive5xxErrors: 10
      consecutiveLocalOriginFailures: 5
      interval: 60s
      baseEjectionTime: 300s
      maxEjectionPercent: 20
      splitExternalLocalOriginErrors: true
      minHealthPercent: 0
```

This TCP example observes connection/transport failures, not SQL errors, locks or query latency. Ensure the ServiceEntry unambiguously identifies the destination; shared TCP ports may need DNS capture/VIP design. It does not elect a writable database primary or make replica failover safe.

### Example 4: External API with Retry

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: external-geocoding-api
  namespace: location
spec:
  hosts:
  - maps.googleapis.com
  resolution: DNS
  ports:
  - number: 80
    name: http
    protocol: HTTP
    targetPort: 443
  location: MESH_EXTERNAL
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: external-geocoding-api
  namespace: location
spec:
  hosts:
  - maps.googleapis.com
  http:
  - name: writes-no-retry
    match:
    - method:
        regex: ^(POST|PUT|PATCH|DELETE)$
    route:
    - destination:
        host: maps.googleapis.com
        port:
          number: 80
    retries:
      attempts: 0
    timeout: 5s
  - timeout: 5s
    retries:
      attempts: 3
      perTryTimeout: 2s
      retryOn: gateway-error,connect-failure,refused-stream
    route:
    - destination:
        host: maps.googleapis.com
        port:
          number: 80
    name: idempotent-reads
    match:
    - method:
        regex: ^(GET|HEAD|OPTIONS)$
  - name: other-methods-no-retry
    route:
    - destination:
        host: maps.googleapis.com
        port:
          number: 80
    retries:
      attempts: 0
    timeout: 5s
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: external-geocoding-api
  namespace: location
spec:
  host: maps.googleapis.com
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 100
        connectTimeout: 3s
      http:
        http1MaxPendingRequests: 50
        maxRequestsPerConnection: 10
        maxRetries: 3
    outlierDetection:
      consecutive5xxErrors: 3
      consecutiveGatewayErrors: 2
      consecutiveLocalOriginFailures: 3
      interval: 10s
      baseEjectionTime: 30s
      maxEjectionPercent: 50
      splitExternalLocalOriginErrors: true
      minHealthPercent: 0
    portLevelSettings:
    - port:
        number: 80
      tls:
        mode: SIMPLE
        sni: maps.googleapis.com
        subjectAltNames:
        - maps.googleapis.com
```

The geocoding example only retries matched idempotent reads. Call the HTTP port80 path so the proxy can see the method; HTTPS passthrough cannot use this HTTP policy. Three retries plus the initial attempt do not all fit if every attempt lasts2s within the5s total timeout.

### Example 5: External Service with Rate Limiting

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: external-rate-limited-api
  namespace: api
spec:
  hosts:
  - api.third-party.com
  resolution: DNS
  ports:
  - number: 80
    name: http
    protocol: HTTP
    targetPort: 443
  location: MESH_EXTERNAL
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: ratelimit-config
  namespace: api
data:
  config.yaml: "domain: external-api-ratelimit\ndescriptors:\n- key: destination_cluster\n  value: outbound|80||api.third-party.com\n  rate_limit:\n    unit: second\n    requests_per_unit: 100\n"
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: external-rate-limited-api
  namespace: api
spec:
  host: api.third-party.com
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 100
      http:
        http1MaxPendingRequests: 50
        http2MaxRequests: 100
        maxRequestsPerConnection: 10
    outlierDetection:
      consecutive5xxErrors: 3
      consecutiveGatewayErrors: 2
      interval: 10s
      baseEjectionTime: 60s
      maxEjectionPercent: 50
      splitExternalLocalOriginErrors: true
      consecutiveLocalOriginFailures: 3
      minHealthPercent: 0
    portLevelSettings:
    - port:
        number: 80
      tls:
        mode: SIMPLE
        sni: api.third-party.com
        subjectAltNames:
        - api.third-party.com
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: external-rate-limited-api
  namespace: api
spec:
  hosts:
  - api.third-party.com
  http:
  - name: no-retries
    route:
    - destination:
        host: api.third-party.com
        port:
          number: 80
    retries:
      attempts: 0
    timeout: 5s
```

The ConfigMap is only a rate-limit-service configuration fragment. It must be mounted in a running compatible service with its backing store, outbound Envoy rate-limit filter and matching `destination_cluster` descriptor. Alone it enforces nothing. Gateway errors are502/503/504, not429; standard5xx detection does not treat429 as a gateway error. Ejection time is not synchronized with the provider’s quota reset. Prefer quota-aware handling and Retry-After/application backoff to ejecting every healthy quota-limited host.

### External Service Outlier Detection Best Practices

#### 1. Distinguish Error Types

```yaml
outlierDetection:
  # Gateway errors (502, 503, 504)
  consecutiveGatewayErrors: 2  # Detect quickly

  # 5xx errors (500, 501, etc.)
  consecutive5xxErrors: 3

  # Local errors (timeout, connection failure)
  consecutiveLocalOriginFailures: 3

  # Track local and remote errors separately
  splitExternalLocalOriginErrors: true
```

**Important**: When setting `splitExternalLocalOriginErrors: true`:
- **Local Origin Failures**: Connection timeout/reset/refusal attributed to an upstream host; DNS resolution failure may leave no host to eject
- **Upstream Failures**: 5xx errors returned by external API

These are counted separately for more accurate detection.

#### 2. Timeout Configuration

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: external-api
  namespace: default
spec:
  hosts:
  - api.external.com
  location: MESH_EXTERNAL
  resolution: DNS
  ports:
  - number: 80
    name: http
    protocol: HTTP
    targetPort: 443
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: external-api
  namespace: default
spec:
  hosts:
  - api.external.com
  http:
  - name: writes-no-retry
    match:
    - method:
        regex: ^(POST|PUT|PATCH|DELETE)$
    route:
    - destination:
        host: api.external.com
        port:
          number: 80
    retries:
      attempts: 0
    timeout: 5s
  - timeout: 5s
    retries:
      attempts: 3
      perTryTimeout: 2s
      retryOn: gateway-error,connect-failure,refused-stream
    route:
    - destination:
        host: api.external.com
        port:
          number: 80
    name: idempotent-reads
    match:
    - method:
        regex: ^(GET|HEAD|OPTIONS)$
  - name: other-methods-no-retry
    route:
    - destination:
        host: api.external.com
        port:
          number: 80
    retries:
      attempts: 0
    timeout: 5s
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: external-api
  namespace: default
spec:
  host: api.external.com
  trafficPolicy:
    connectionPool:
      tcp:
        connectTimeout: 3s
    outlierDetection:
      consecutiveLocalOriginFailures: 3
      splitExternalLocalOriginErrors: true
      minHealthPercent: 0
    portLevelSettings:
    - port:
        number: 80
      tls:
        mode: SIMPLE
        sni: api.external.com
        subjectAltNames:
        - api.external.com
```

#### 3. External Service Monitoring

```promql
# Outlier Detection metrics
# 1. Ejected external endpoints
envoy_cluster_outlier_detection_ejections_active{
  namespace="default", cluster_name=~"outbound.*api\\.external\\.com.*"
}

# 2. Local errors (timeout, connection failure)
rate(envoy_cluster_upstream_rq_timeout{
  namespace="default", cluster_name=~"outbound.*api\\.external\\.com.*"
}[5m])

# 3. External API 5xx errors
rate(istio_requests_total{
  reporter="source", source_workload_namespace="default",
  destination_service="api.external.com",
  response_code=~"5.."
}[5m])

# 4. External API response time
histogram_quantile(0.95,
  sum(rate(istio_request_duration_milliseconds_bucket{
    reporter="source", source_workload_namespace="default",
    destination_service="api.external.com"
  }[5m])) by (le)
)
```

#### 4. Alert Configuration

This is a Prometheus rule-file fragment, not a Kubernetes resource. Mount/select it in Prometheus (or wrap groups in a selected PrometheusRule). Thresholds require traffic-volume, no-data and scrape-health handling; they are not validated SLOs. Latency below is milliseconds and rates are per second.


```yaml
# Prometheus Alert Rules
groups:
- name: external_api_alerts
  interval: 1m
  rules:
  # High external API error rate
  - alert: ExternalAPIHighErrorRate
    expr: |
      (sum(rate(istio_requests_total{
        reporter="source", source_workload_namespace="default",
        destination_service=~".*external.*",
        response_code=~"5.."
      }[5m])) by (destination_service)
      /
      sum(rate(istio_requests_total{
        reporter="source", source_workload_namespace="default",
        destination_service=~".*external.*"
      }[5m])) by (destination_service))
      * 100 > 5
    for: 2m
    labels:
      severity: warning
    annotations:
      summary: "High error rate for external API {{ $labels.destination_service }}"
      description: "Error rate is {{ $value }}%"

  # External API instance ejected
  - alert: ExternalAPIInstanceEjected
    expr: |
      envoy_cluster_outlier_detection_ejections_active{
        namespace="default", cluster_name=~"outbound.*external.*"
      } > 0
    for: 1m
    labels:
      severity: warning
    annotations:
      summary: "External API instance ejected"
      description: "{{ $value }} instances ejected from {{ $labels.cluster_name }}"

  # Increased external API timeouts
  - alert: ExternalAPIHighTimeout
    expr: |
      rate(envoy_cluster_upstream_rq_timeout{
        namespace="default", cluster_name=~"outbound.*external.*"
      }[5m]) > 0.1
    for: 2m
    labels:
      severity: warning
    annotations:
      summary: "High timeout rate for external API"
      description: "Timeout rate is {{ $value }} req/s"
```

#### 5. Troubleshooting

Run diagnostics on the calling proxy. The connectivity command requires curl in an authorized application/test container and a real read-only health endpoint; executing curl inside `istio-proxy` can bypass the application traffic path. These generic monitoring queries refer to the separate `default`/`api.external.com` example; adjust scope for the other examples.


```bash
# 1. Check ServiceEntry
kubectl get serviceentry -A
kubectl describe serviceentry external-api -n <namespace>

# 2. Verify DestinationRule application
istioctl proxy-config clusters <pod-name> -n <namespace> --fqdn api.external.com -o json | \
  jq '.[] | {name: .name, outlierDetection: .outlierDetection}'

# 3. Test external API connection
kubectl exec <client-pod> -n default -c <app-container> -- \
  curl --max-time 5 -v http://api.external.com/health

# 4. Check Envoy statistics
istioctl x envoy-stats <pod-name> -n <namespace> --output prom | grep "outbound.*external"

# 5. Outlier Detection status
istioctl x envoy-stats <pod-name> -n <namespace> --type clusters
```

### External Service Failure Scenarios

#### Scenario 1: Temporary External API Failure

```yaml
# Configuration: Fast detection and recovery
outlierDetection:
  consecutive5xxErrors: 3           # 3 consecutive errors
  consecutiveGatewayErrors: 2    # 2 gateway errors
  interval: 10s                  # Evaluate every 10 seconds
  baseEjectionTime: 30s          # Recovery attempt after 30 seconds
  maxEjectionPercent: 50         # Maximum 50% ejection
```

**Expected behavior, subject to effective limits**:

1. Qualifying502/503 responses count toward the gateway threshold.
2. Reaching two consecutive gateway failures can eject the host if enforcement/cap permit it.
3. The host becomes eligible after its ejection period; no active probe is configured here.
4. Repeated ejections increase the duration using Envoy’s multiplier/cap. Returning to the pool does not prove the provider recovered.

#### Scenario 2: Complete External API Down

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: external-api-ha
  namespace: default
spec:
  hosts:
  - api.external.com
  resolution: STATIC
  endpoints:
  - address: 203.0.113.10
    labels:
      tier: primary
  - address: 203.0.113.20
    labels:
      tier: secondary
  - address: 203.0.113.30
    labels:
      tier: tertiary
  ports:
  - number: 80
    name: http
    protocol: HTTP
    targetPort: 443
  location: MESH_EXTERNAL
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: external-api-ha
  namespace: default
spec:
  host: api.external.com
  trafficPolicy:
    outlierDetection:
      consecutive5xxErrors: 3
      consecutiveLocalOriginFailures: 3
      interval: 10s
      baseEjectionTime: 60s
      maxEjectionPercent: 66
      minHealthPercent: 0
      splitExternalLocalOriginErrors: true
    portLevelSettings:
    - port:
        number: 80
      tls:
        mode: SIMPLE
        sni: api.external.com
        subjectAltNames:
        - api.external.com
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: external-api-ha
  namespace: default
spec:
  hosts:
  - api.external.com
  http:
  - name: no-retries
    route:
    - destination:
        host: api.external.com
        port:
          number: 80
    retries:
      attempts: 0
    timeout: 5s
```

**Interpretation**:

The three endpoints are members of one pool. `tier: primary/secondary/tertiary` labels do not define failover priorities; normal load balancing can select any eligible endpoint. A failed endpoint may be ejected locally and another selected, but an entirely failed external service cannot be repaired by routing. `minHealthPercent: 0` disables panic use of unhealthy hosts; the percentage cap does not guarantee one healthy survivor. Use explicitly designed locality priorities or an application/provider failover mechanism if ordered failover is required. The documentation IPs must be replaced before any connectivity test.

## Practical Examples

### Example 1: Microservice Chain

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: backend-outlier
  namespace: default
spec:
  host: backend
  trafficPolicy:
    outlierDetection:
      consecutive5xxErrors: 3
      interval: 10s
      baseEjectionTime: 30s
      maxEjectionPercent: 50
      minHealthPercent: 0
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: database-outlier
  namespace: default
spec:
  host: database
  trafficPolicy:
    outlierDetection:
      consecutive5xxErrors: 10
      interval: 60s
      baseEjectionTime: 300s
      maxEjectionPercent: 20
      minHealthPercent: 0
```

### Example 2: Use with Canary Deployment

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: reviews-canary
  namespace: default
spec:
  hosts:
  - reviews
  http:
  - route:
    - destination:
        host: reviews
        subset: v1
      weight: 90
    - destination:
        host: reviews
        subset: v2
      weight: 10
    retries:
      attempts: 0
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews
  namespace: default
spec:
  host: reviews
  subsets:
  - name: v1
    labels:
      version: v1
  - name: v2
    labels:
      version: v2
    trafficPolicy:
      outlierDetection:
        consecutive5xxErrors: 3
        interval: 10s
        baseEjectionTime: 60s
        maxEjectionPercent: 100
        minHealthPercent: 0
```

Ejecting every v2 endpoint does not move its10% route weight to v1. Requests selected for an empty canary subset can fail; a rollout controller must change the route weight/rollback based on observed health. The workload labels must match both subsets.

### Example 3: Multi-Region Deployment

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: api-multi-region
  namespace: default
spec:
  host: api
  trafficPolicy:
    loadBalancer:
      localityLbSetting:
        enabled: true
        distribute:
        - from: us-east-1/*
          to:
            us-east-1/*: 80
            us-west-2/*: 20
    outlierDetection:
      consecutive5xxErrors: 10
      interval: 60s
      baseEjectionTime: 120s
      maxEjectionPercent: 30
      minHealthPercent: 0
```

This80/20 policy intentionally sends traffic to both healthy regions. It is not standby failover and requires actual region-locality metadata, cross-region connectivity and capacity. A region name alone does not create a multi-cluster mesh.

### Example 4: Connection Pool + Outlier Detection

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews-full-protection
  namespace: default
spec:
  host: reviews
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 100
      http:
        http1MaxPendingRequests: 50
        http2MaxRequests: 100
        maxRequestsPerConnection: 2
    outlierDetection:
      consecutive5xxErrors: 5
      consecutiveGatewayErrors: 3
      interval: 30s
      baseEjectionTime: 30s
      maxEjectionPercent: 50
      minHealthPercent: 0
```

## Monitoring

### Prometheus Metrics

Enable optional proxy statistics and scrape labels as described in the [resilience overview](README.md#resilience-metrics). These examples preserve each proxy’s `pod`/`cluster_name`; summing ejections across callers does not count distinct server Pods. The released Istio bootstrap uses `cluster_name`; verify labels after your collector relabeling. `enforced_*` counters count actual ejections, while `detected_*` can increase when ejection is blocked by a cap.

```promql
# Current ejections, not a cumulative event counter
envoy_cluster_outlier_detection_ejections_active{namespace="default"}

# Enforced ejection events per second
rate(envoy_cluster_outlier_detection_ejections_enforced_total{namespace="default"}[5m])

# Percentage of the total observed pool, excluding zero-size pools
100 * envoy_cluster_outlier_detection_ejections_active{namespace="default"} /
(envoy_cluster_membership_total{namespace="default"} > 0)

rate(envoy_cluster_outlier_detection_ejections_enforced_consecutive_5xx{namespace="default"}[5m])
rate(envoy_cluster_outlier_detection_ejections_enforced_consecutive_gateway_failure{namespace="default"}[5m])
rate(envoy_cluster_outlier_detection_ejections_enforced_consecutive_local_origin_failure{namespace="default"}[5m])
```

### Grafana Dashboard Example

Save this dashboard object using the [dashboard file provisioning](../observability/04-dashboards.md) workflow. It expects datasource UID `prometheus` and actual `namespace`/`pod`/`cluster_name` labels. A ConfigMap alone does not load dashboards.

```json
{
  "uid": "istio-outlier-detection",
  "title": "Istio Outlier Detection",
  "panels": [
    {
      "id": 1,
      "title": "Ejected Hosts",
      "type": "timeseries",
      "datasource": {
        "type": "prometheus",
        "uid": "prometheus"
      },
      "targets": [
        {
          "expr": "envoy_cluster_outlier_detection_ejections_active{namespace=\"default\"}",
          "legendFormat": "{{pod}} / {{cluster_name}}",
          "refId": "A"
        }
      ],
      "gridPos": {
        "x": 0,
        "y": 0,
        "w": 24,
        "h": 8
      },
      "fieldConfig": {
        "defaults": {
          "unit": "short"
        }
      }
    },
    {
      "id": 2,
      "title": "Enforced Ejections per Second",
      "type": "timeseries",
      "datasource": {
        "type": "prometheus",
        "uid": "prometheus"
      },
      "targets": [
        {
          "expr": "rate(envoy_cluster_outlier_detection_ejections_enforced_total{namespace=\"default\"}[5m])",
          "legendFormat": "{{pod}} / {{cluster_name}}",
          "refId": "A"
        }
      ],
      "gridPos": {
        "x": 0,
        "y": 8,
        "w": 24,
        "h": 8
      },
      "fieldConfig": {
        "defaults": {
          "unit": "short"
        }
      }
    },
    {
      "id": 3,
      "title": "Ejected Pool Percentage",
      "type": "timeseries",
      "datasource": {
        "type": "prometheus",
        "uid": "prometheus"
      },
      "targets": [
        {
          "expr": "100 * envoy_cluster_outlier_detection_ejections_active{namespace=\"default\"} / (envoy_cluster_membership_total{namespace=\"default\"} > 0)",
          "legendFormat": "{{pod}} / {{cluster_name}}",
          "refId": "A"
        }
      ],
      "gridPos": {
        "x": 0,
        "y": 16,
        "w": 24,
        "h": 8
      },
      "fieldConfig": {
        "defaults": {
          "unit": "percent"
        }
      }
    }
  ],
  "time": {
    "from": "now-1h",
    "to": "now"
  },
  "refresh": "30s"
}
```

### Real-time Monitoring

```bash
# Check Envoy statistics
istioctl x envoy-stats <pod-name> -n <namespace> --output prom | grep outlier

# Key metrics:
# envoy_cluster_outlier_detection_ejections_active: Currently ejected instances
# envoy_cluster_outlier_detection_ejections_enforced_total: Total ejection count
# envoy_cluster_outlier_detection_ejections_enforced_consecutive_5xx: Ejections due to 5xx errors
```

### Verify in Kiali

```bash
# Access Kiali
istioctl dashboard kiali

# Things to check:
# 1. Graph → Select service → Traffic tab
# 2. Graph health is aggregate telemetry, not every caller proxy’s ejection state
# 3. Check Outlier Detection metrics
```

## Troubleshooting

### Outlier Detection Not Working

```bash
# 1. Check DestinationRule
kubectl get destinationrule -n <namespace>
kubectl describe destinationrule <name> -n <namespace>

# 2. Check Envoy cluster configuration
istioctl proxy-config clusters <pod-name> -n <namespace> --fqdn <service-fqdn> -o json | \
  jq '.[] | .outlierDetection'

# 3. Check Envoy logs
kubectl logs -n <namespace> <pod-name> -c istio-proxy | grep outlier

# 4. Validate control-plane configuration (istiod does not perform per-proxy ejections)
istioctl analyze -n <namespace>
```

### Too Many Instances Being Ejected

Inspect enforced/detected/overflow counters, remaining capacity and actual error types before changing thresholds. Increase a consecutive-error threshold if the application can tolerate the observed failures; reduce the cap only with an explicit availability tradeoff. Increasing `interval` does not delay inline consecutive-error ejection.

```yaml
# DestinationRule trafficPolicy fragment; illustrative values
outlierDetection:
  consecutive5xxErrors: 10
  interval: 30s
  baseEjectionTime: 30s
  maxEjectionPercent: 30
  minHealthPercent: 0
```

### No Healthy Upstream Hosts

This is not database split-brain. Check readiness, discovery, routing, endpoint health and caller-local ejections. Setting `minHealthPercent: 50` may fail open to unhealthy hosts; it does not restore them. A 100%-ejected canary subset may require route rollback. Use effective endpoint/cluster state, not only DestinationRule YAML or a Kiali icon.

### Recovery Too Slow After Ejection

Review repeated-ejection history and Envoy's effective duration cap. Reducing `baseEjectionTime` may make traffic retry an unhealthy host sooner; it is not a repair. Active health checking is a separate feature and is not enabled by this DestinationRule.

### False Positives from Temporary Errors

Distinguish connection failures from application failures and check whether retries amplify them. A5xx may be an intentional response, while a slow successful response alone is not a latency-based outlier. Scope rollout and verify the changed proxy config; default logs need not contain outlier events.

## Best Practices

### 1. Configuration by Service Type

```yaml
# Critical service (fast detection)
outlierDetection:
  consecutive5xxErrors: 3
  interval: 10s
  baseEjectionTime: 30s
  maxEjectionPercent: 50

# General service
---
outlierDetection:
  consecutive5xxErrors: 5
  interval: 30s
  baseEjectionTime: 60s
  maxEjectionPercent: 30

# Stable service (lenient settings)
---
outlierDetection:
  consecutive5xxErrors: 10
  interval: 60s
  baseEjectionTime: 120s
  maxEjectionPercent: 20
```

### 2. Combine with Connection Pool When Needed

```yaml
# Independent limits; size against measured caller/endpoint capacity
trafficPolicy:
  connectionPool:
    tcp:
      maxConnections: 100
    http:
      http1MaxPendingRequests: 50
  outlierDetection:
    consecutive5xxErrors: 5
    interval: 30s
```

### 3. Choose Panic Behavior Deliberately

`minHealthPercent: 0` is the Istio default and disables the unhealthy-host panic threshold. Nonzero values allow an availability-versus-isolation tradeoff; they are not a guarantee that some hosts remain healthy. Connection-pool circuit breaking and outlier detection are independent controls.

### 4. Gradual Rollout

Collect a baseline, verify effective mesh/namespace/workload policy, then apply a measured setting to an isolated test cohort and expand only after validation. Do not use `maxEjectionPercent: 0` as a monitor-only switch: in the [Istio1.31 implementation](https://github.com/istio/istio/blob/1.31.0/pilot/pkg/networking/core/cluster_traffic_policy.go), only values greater than0 set Envoy's field, so0 leaves Envoy's default rather than disabling ejection. Omitted settings can also inherit a mesh default. Observe actual enforced events and remaining endpoints before wider rollout.

### 5. Monitoring and Alerting

```yaml
# Prometheus Alerting Rule
groups:
- name: istio_outlier_detection
  rules:
  - alert: HighEjectionRate
    expr: rate(envoy_cluster_outlier_detection_ejections_enforced_total{namespace="default"}[5m]) > 0.1
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High outlier ejection rate"
      description: "{{ $labels.cluster_name }} has enforced ejection rate > 0.1 events/s"
```

## References

- [Istio Outlier Detection](https://istio.io/latest/docs/reference/config/networking/destination-rule/#OutlierDetection)
- [Envoy Outlier Detection](https://www.envoyproxy.io/docs/envoy/latest/intro/arch_overview/upstream/outlier)
- [Circuit Breaking](https://istio.io/latest/docs/tasks/traffic-management/circuit-breaking/)
