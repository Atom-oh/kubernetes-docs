# Outlier Detection

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

Outlier Detection automatically removes instances in the following situations:

```mermaid
flowchart TB
    Request[Client Request]

    subgraph LoadBalancer["Load Balancer"]
        LB[Envoy Proxy<br/>Outlier Detection]
    end

    subgraph HealthyPods["Healthy Pods"]
        P1[Pod 1<br/>Response Time: 50ms<br/>Error Rate: 0%]
        P2[Pod 2<br/>Response Time: 60ms<br/>Error Rate: 1%]
    end

    subgraph UnhealthyPods["Unhealthy Pods"]
        P3[Pod 3<br/>Response Time: 5000ms<br/>Error Rate: 80%]
    end

    Request --> LB
    LB -->|Send Traffic| P1
    LB -->|Send Traffic| P2
    LB -.->|Ejected| P3

    P3 -.->|Recovery Attempt After 30s| LB

    %% Style definitions
    classDef request fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;
    classDef lb fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef healthy fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef unhealthy fill:#FF6B6B,stroke:#333,stroke-width:1px,color:white;

    %% Class applications
    class Request request;
    class LB lb;
    class P1,P2 healthy;
    class P3 unhealthy;
```

### Key Features

1. **Automatic Detection**: Automatically monitors error rate, latency, and response failures
2. **Automatic Ejection**: Automatically removes from traffic when threshold is exceeded
3. **Automatic Recovery**: Automatically attempts recovery after a set time

## How It Works

### Outlier Detection Process

```mermaid
flowchart LR
    Start[Request Start]
    Check{Check for<br/>Errors}
    Count[Increment<br/>Error Count]
    Threshold{Threshold<br/>Exceeded?}
    Eject[Eject<br/>Instance]
    Normal[Normal<br/>Processing]
    Wait[Wait Period]
    Retry[Recovery<br/>Attempt]

    Start --> Check
    Check -->|Error| Count
    Check -->|Success| Normal
    Count --> Threshold
    Threshold -->|Yes| Eject
    Threshold -->|No| Normal
    Eject --> Wait
    Wait --> Retry
    Retry --> Start

    %% Style definitions
    classDef start fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;
    classDef process fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef decision fill:#F8B52A,stroke:#333,stroke-width:1px,color:black;
    classDef eject fill:#FF6B6B,stroke:#333,stroke-width:1px,color:white;

    %% Class applications
    class Start start;
    class Check,Threshold decision;
    class Count,Wait,Retry process;
    class Eject eject;
    class Normal process;
```

### Detection Methods

| Method | Description | Use Scenario |
|--------|-------------|--------------|
| **Consecutive Errors** | Detect consecutive 5xx errors | Application crash |
| **Gateway Errors** | Detect 502, 503, 504 errors | Service overload |
| **Connection Failures** | Detect TCP connection failures | Network issues |
| **Latency** | Response time threshold exceeded | Performance degradation |

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
      # Consecutive error threshold
      consecutiveErrors: 5

      # Analysis interval (evaluate every 30 seconds)
      interval: 30s

      # Ejection time (30 seconds)
      baseEjectionTime: 30s

      # Maximum ejection percentage (50%)
      maxEjectionPercent: 50

      # Minimum request count (evaluate only when 10+ requests)
      minHealthPercent: 50
```

### Key Parameter Descriptions

#### consecutiveErrors
- **Description**: Threshold for consecutive error occurrences
- **Default**: 5
- **Recommended**: 3-10 (depending on service characteristics)

```yaml
# Sensitive service (fast detection)
consecutiveErrors: 3

# General service
consecutiveErrors: 5

# Lenient setting (prevent false positives)
consecutiveErrors: 10
```

#### interval
- **Description**: Outlier Detection analysis interval
- **Default**: 10s
- **Recommended**: 10s-60s

```yaml
# Fast detection (high load)
interval: 10s

# General case
interval: 30s

# Stable service
interval: 60s
```

#### baseEjectionTime
- **Description**: Minimum time an instance is ejected
- **Default**: 30s
- **Recommended**: 30s-300s

```yaml
# Fast recovery attempt
baseEjectionTime: 30s

# General case
baseEjectionTime: 60s

# Cautious recovery
baseEjectionTime: 300s
```

#### maxEjectionPercent
- **Description**: Maximum percentage of instances that can be ejected simultaneously
- **Default**: 10%
- **Recommended**: 10%-50%

```yaml
# Conservative (stability first)
maxEjectionPercent: 10

# Balanced setting
maxEjectionPercent: 30

# Aggressive (quality first)
maxEjectionPercent: 50
```

## Advanced Configuration

### Gateway Error Based Detection

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews-gateway-errors
spec:
  host: reviews
  trafficPolicy:
    outlierDetection:
      # Consecutive gateway errors
      consecutiveGatewayErrors: 3

      # Respond sensitively to 502, 503, 504 errors
      interval: 10s
      baseEjectionTime: 60s

      # Eject faster for gateway errors
      maxEjectionPercent: 50
```

### Split Brain Prevention

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews-split-brain-safe
spec:
  host: reviews
  trafficPolicy:
    outlierDetection:
      consecutiveErrors: 5
      interval: 30s
      baseEjectionTime: 30s

      # Maintain minimum healthy instance percentage
      minHealthPercent: 50

      # Limit maximum ejection percentage
      maxEjectionPercent: 30
```

**Important**: Use `minHealthPercent` and `maxEjectionPercent` together to prevent all instances from being ejected.

### Connection Failure Based Detection

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews-connection-errors
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
      # Detect consecutive connection failures
      consecutiveLocalOriginFailures: 5

      interval: 10s
      baseEjectionTime: 30s
      maxEjectionPercent: 50
```

### Success Rate Based Detection (Advanced)

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews-success-rate
spec:
  host: reviews
  trafficPolicy:
    outlierDetection:
      # Minimum requests needed for analysis
      splitExternalLocalOriginErrors: true

      # Success rate threshold (eject if below 95%)
      consecutiveErrors: 5
      interval: 30s
      baseEjectionTime: 60s

      # Minimum request count
      enforcingConsecutiveErrors: 100
      enforcingSuccessRate: 100
```

## Protecting External Services (ServiceEntry)

Register external APIs or legacy systems as ServiceEntry and apply Outlier Detection to prevent failure propagation.

### External API Protection Architecture

```mermaid
flowchart LR
    subgraph "Kubernetes Cluster"
        App[Application Pod]
        Envoy[Envoy Proxy<br/>Outlier Detection]
    end

    subgraph "External Services"
        API1[External API<br/>Instance 1<br/>Healthy]
        API2[External API<br/>Instance 2<br/>Errors]
        API3[External API<br/>Instance 3<br/>Healthy]
    end

    App --> Envoy
    Envoy -->|Send Traffic| API1
    Envoy -.->|Ejected| API2
    Envoy -->|Send Traffic| API3

    %% Style definitions
    classDef k8sComponent fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef external fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef unhealthy fill:#FF6B6B,stroke:#333,stroke-width:1px,color:white;

    %% Class applications
    class App,Envoy k8sComponent;
    class API1,API3 external;
    class API2 unhealthy;
```

### Example 1: Single External API (DNS Based)

```yaml
# Register external REST API service
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: external-payment-api
  namespace: payment
spec:
  hosts:
  - api.payment-provider.com

  # DNS-based load balancing
  resolution: DNS

  # HTTPS port
  ports:
  - number: 443
    name: https
    protocol: HTTPS

  # External service
  location: MESH_EXTERNAL
---
# Apply Outlier Detection
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: external-payment-api
  namespace: payment
spec:
  host: api.payment-provider.com

  trafficPolicy:
    # TLS configuration
    tls:
      mode: SIMPLE

    # Connection Pool (Circuit Breaker)
    connectionPool:
      tcp:
        maxConnections: 100
        connectTimeout: 3s
      http:
        http1MaxPendingRequests: 50
        http2MaxRequests: 100
        maxRequestsPerConnection: 10
        maxRetries: 3

    # Outlier Detection
    outlierDetection:
      # Detect external API quickly
      consecutiveErrors: 3
      consecutiveGatewayErrors: 2

      # Evaluate every 10 seconds
      interval: 10s

      # Eject for 30 seconds
      baseEjectionTime: 30s

      # Allow up to 50% ejection
      maxEjectionPercent: 50

      # Also detect local errors (timeout, connection failure)
      splitExternalLocalOriginErrors: true
      consecutiveLocalOriginFailures: 3
```

**Usage Example**:
```go
// Go application code
func processPayment(ctx context.Context, amount float64) error {
    // Istio automatically routes to api.payment-provider.com
    // On error, automatically retries to another instance
    resp, err := http.Post(
        "https://api.payment-provider.com/v1/charge",
        "application/json",
        bytes.NewBuffer(paymentData),
    )

    if err != nil {
        // Outlier Detection triggers after 3 consecutive errors
        return fmt.Errorf("payment failed: %w", err)
    }

    return nil
}
```

### Example 2: Multiple External API Endpoints

```yaml
# External API endpoints across multiple regions
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: external-weather-api
  namespace: weather
spec:
  hosts:
  - weather.api.com

  # Static IP address specification
  resolution: STATIC

  ports:
  - number: 443
    name: https
    protocol: HTTPS

  location: MESH_EXTERNAL

  # Multiple endpoints
  endpoints:
  - address: 203.0.113.10
    labels:
      region: us-east-1
  - address: 203.0.113.20
    labels:
      region: us-west-2
  - address: 203.0.113.30
    labels:
      region: eu-central-1
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: external-weather-api
  namespace: weather
spec:
  host: weather.api.com

  trafficPolicy:
    tls:
      mode: SIMPLE

    # Load balancer configuration
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
      # Adjust for external API characteristics
      consecutiveErrors: 5
      consecutiveGatewayErrors: 3
      consecutiveLocalOriginFailures: 5

      interval: 30s
      baseEjectionTime: 60s

      # Eject up to 1 per region
      maxEjectionPercent: 33  # 1 out of 3

      splitExternalLocalOriginErrors: true
```

### Example 3: Legacy Database Protection

```yaml
# External PostgreSQL database
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
      # Detect database cautiously
      consecutiveErrors: 10

      # TCP connection failure detection
      consecutiveLocalOriginFailures: 5

      interval: 60s
      baseEjectionTime: 300s  # 5 minutes

      # Be conservative for database
      maxEjectionPercent: 20

      splitExternalLocalOriginErrors: true
```

### Example 4: External API with Retry

```yaml
# External RESTful API
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
  - number: 443
    name: https
    protocol: HTTPS

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
  - timeout: 5s
    retries:
      attempts: 3
      perTryTimeout: 2s
      retryOn: 5xx,reset,connect-failure,refused-stream
    route:
    - destination:
        host: maps.googleapis.com
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: external-geocoding-api
  namespace: location
spec:
  host: maps.googleapis.com

  trafficPolicy:
    tls:
      mode: SIMPLE

    connectionPool:
      tcp:
        maxConnections: 100
        connectTimeout: 3s
      http:
        http1MaxPendingRequests: 50
        maxRequestsPerConnection: 10
        maxRetries: 3

    outlierDetection:
      # Fast detection
      consecutiveErrors: 3
      consecutiveGatewayErrors: 2
      consecutiveLocalOriginFailures: 3

      interval: 10s
      baseEjectionTime: 30s
      maxEjectionPercent: 50

      # Track local errors (timeout, connection failure) separately
      splitExternalLocalOriginErrors: true
```

### Example 5: External Service with Rate Limiting

```yaml
# External API with Rate Limiting
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
  - number: 443
    name: https
    protocol: HTTPS

  location: MESH_EXTERNAL
---
# Rate Limiting configuration
apiVersion: v1
kind: ConfigMap
metadata:
  name: ratelimit-config
  namespace: api
data:
  config.yaml: |
    domain: external-api-ratelimit
    descriptors:
    - key: destination_cluster
      value: outbound|443||api.third-party.com
      rate_limit:
        unit: second
        requests_per_unit: 100
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: external-rate-limited-api
  namespace: api
spec:
  host: api.third-party.com

  trafficPolicy:
    tls:
      mode: SIMPLE

    connectionPool:
      tcp:
        maxConnections: 100
      http:
        http1MaxPendingRequests: 50
        http2MaxRequests: 100
        maxRequestsPerConnection: 10

    outlierDetection:
      # Detect quickly when rate limit exceeded
      consecutiveErrors: 3
      consecutiveGatewayErrors: 2  # 429 Too Many Requests

      interval: 10s
      baseEjectionTime: 60s  # Wait for rate limit reset
      maxEjectionPercent: 50

      splitExternalLocalOriginErrors: true
      consecutiveLocalOriginFailures: 3
```

### External Service Outlier Detection Best Practices

#### 1. Distinguish Error Types

```yaml
outlierDetection:
  # Gateway errors (502, 503, 504)
  consecutiveGatewayErrors: 2  # Detect quickly

  # 5xx errors (500, 501, etc.)
  consecutiveErrors: 3

  # Local errors (timeout, connection failure)
  consecutiveLocalOriginFailures: 3

  # Track local and remote errors separately
  splitExternalLocalOriginErrors: true
```

**Important**: When setting `splitExternalLocalOriginErrors: true`:
- **Local Origin Failures**: Connection timeout, DNS failure, connection refused
- **Upstream Failures**: 5xx errors returned by external API

These are counted separately for more accurate detection.

#### 2. Timeout Configuration

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: external-api
spec:
  hosts:
  - api.external.com
  http:
  - timeout: 5s  # Overall request timeout
    retries:
      attempts: 3
      perTryTimeout: 2s  # Per-retry timeout
    route:
    - destination:
        host: api.external.com
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: external-api
spec:
  host: api.external.com
  trafficPolicy:
    connectionPool:
      tcp:
        connectTimeout: 3s  # TCP connection timeout
    outlierDetection:
      consecutiveLocalOriginFailures: 3  # Timeout also counts
      splitExternalLocalOriginErrors: true
```

#### 3. External Service Monitoring

```promql
# Outlier Detection metrics
# 1. Ejected external endpoints
envoy_cluster_outlier_detection_ejections_active{
  cluster_name=~"outbound.*api\\.external\\.com.*"
}

# 2. Local errors (timeout, connection failure)
rate(envoy_cluster_upstream_rq_timeout{
  cluster_name=~"outbound.*api\\.external\\.com.*"
}[5m])

# 3. External API 5xx errors
rate(istio_requests_total{
  destination_service="api.external.com",
  response_code=~"5.."
}[5m])

# 4. External API response time
histogram_quantile(0.95,
  sum(rate(istio_request_duration_milliseconds_bucket{
    destination_service="api.external.com"
  }[5m])) by (le)
)
```

#### 4. Alert Configuration

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
        destination_service=~".*external.*",
        response_code=~"5.."
      }[5m])) by (destination_service)
      /
      sum(rate(istio_requests_total{
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
        cluster_name=~"outbound.*external.*"
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
        cluster_name=~"outbound.*external.*"
      }[5m]) > 0.1
    for: 2m
    labels:
      severity: warning
    annotations:
      summary: "High timeout rate for external API"
      description: "Timeout rate is {{ $value }} req/s"
```

#### 5. Troubleshooting

```bash
# 1. Check ServiceEntry
kubectl get serviceentry -A
kubectl describe serviceentry external-api -n <namespace>

# 2. Verify DestinationRule application
istioctl proxy-config clusters <pod-name> -n <namespace> --fqdn api.external.com -o json | \
  jq '.[] | {name: .name, outlierDetection: .outlierDetection}'

# 3. Test external API connection
kubectl exec -it <pod-name> -n <namespace> -c istio-proxy -- \
  curl -v https://api.external.com/health

# 4. Check Envoy statistics
kubectl exec -it <pod-name> -n <namespace> -c istio-proxy -- \
  curl localhost:15000/stats/prometheus | grep "outbound.*external"

# 5. Outlier Detection status
kubectl exec -it <pod-name> -n <namespace> -c istio-proxy -- \
  curl localhost:15000/clusters | grep -A 20 "outbound|443||api.external.com"
```

### External Service Failure Scenarios

#### Scenario 1: Temporary External API Failure

```yaml
# Configuration: Fast detection and recovery
outlierDetection:
  consecutiveErrors: 3           # 3 consecutive errors
  consecutiveGatewayErrors: 2    # 2 gateway errors
  interval: 10s                  # Evaluate every 10 seconds
  baseEjectionTime: 30s          # Recovery attempt after 30 seconds
  maxEjectionPercent: 50         # Maximum 50% ejection
```

**Result**:
1. External API returns 502/503 errors
2. Immediate ejection after 2 consecutive errors
3. Automatic recovery attempt after 30 seconds
4. If recovery fails, eject for another 30 seconds (exponential backoff)

#### Scenario 2: Complete External API Down

```yaml
# Configuration: Failover to multiple endpoints
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: external-api-ha
spec:
  hosts:
  - api.external.com
  resolution: STATIC
  endpoints:
  - address: 203.0.113.10    # Primary
    labels:
      tier: primary
  - address: 203.0.113.20    # Secondary
    labels:
      tier: secondary
  - address: 203.0.113.30    # Tertiary
    labels:
      tier: tertiary
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: external-api-ha
spec:
  host: api.external.com
  trafficPolicy:
    outlierDetection:
      consecutiveErrors: 3
      consecutiveLocalOriginFailures: 3
      interval: 10s
      baseEjectionTime: 60s
      maxEjectionPercent: 66  # Allow ejecting up to 2 out of 3
      minHealthPercent: 33    # Keep at least 1
```

**Result**:
1. Primary endpoint down → Ejected
2. Traffic automatically moves to Secondary
3. If Secondary also fails, moves to Tertiary
4. Primary automatically re-included after 60 seconds when recovered

## Practical Examples

### Example 1: Microservice Chain

```yaml
# Frontend → Backend → Database
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: backend-outlier
spec:
  host: backend
  trafficPolicy:
    outlierDetection:
      # Fast detection for backend service
      consecutiveErrors: 3
      interval: 10s
      baseEjectionTime: 30s
      maxEjectionPercent: 50
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: database-outlier
spec:
  host: database
  trafficPolicy:
    outlierDetection:
      # Cautious detection for database
      consecutiveErrors: 10
      interval: 60s
      baseEjectionTime: 300s
      maxEjectionPercent: 20
```

### Example 2: Use with Canary Deployment

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: reviews-canary
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
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews
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
      # Strict detection for canary version
      outlierDetection:
        consecutiveErrors: 3
        interval: 10s
        baseEjectionTime: 60s
        maxEjectionPercent: 100  # Allow full ejection for canary
```

### Example 3: Multi-Region Deployment

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: api-multi-region
spec:
  host: api
  trafficPolicy:
    loadBalancer:
      localityLbSetting:
        enabled: true
        distribute:
        - from: us-east-1/*
          to:
            "us-east-1/*": 80
            "us-west-2/*": 20

    outlierDetection:
      # Be more lenient for cross-region
      consecutiveErrors: 10
      interval: 60s
      baseEjectionTime: 120s
      maxEjectionPercent: 30
```

### Example 4: Connection Pool + Outlier Detection

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews-full-protection
spec:
  host: reviews
  trafficPolicy:
    # Connection Pool (Circuit Breaker)
    connectionPool:
      tcp:
        maxConnections: 100
      http:
        http1MaxPendingRequests: 50
        http2MaxRequests: 100
        maxRequestsPerConnection: 2

    # Outlier Detection
    outlierDetection:
      consecutiveErrors: 5
      consecutiveGatewayErrors: 3
      interval: 30s
      baseEjectionTime: 30s
      maxEjectionPercent: 50
      minHealthPercent: 50
```

## Monitoring

### Prometheus Metrics

```yaml
# Grafana Dashboard Prometheus queries

# 1. Number of ejected instances
envoy_cluster_outlier_detection_ejections_active

# 2. Total ejection count
rate(envoy_cluster_outlier_detection_ejections_total[5m])

# 3. Ejection percentage
(envoy_cluster_outlier_detection_ejections_active
 /
 envoy_cluster_membership_healthy) * 100

# 4. Ejections due to consecutive 5xx errors
rate(envoy_cluster_outlier_detection_ejections_consecutive_5xx[5m])

# 5. Ejections due to gateway errors
rate(envoy_cluster_outlier_detection_ejections_consecutive_gateway_failure[5m])
```

### Grafana Dashboard Example

```json
{
  "dashboard": {
    "title": "Istio Outlier Detection",
    "panels": [
      {
        "title": "Ejected Instances",
        "targets": [
          {
            "expr": "envoy_cluster_outlier_detection_ejections_active",
            "legendFormat": "{{cluster_name}}"
          }
        ]
      },
      {
        "title": "Ejection Rate",
        "targets": [
          {
            "expr": "rate(envoy_cluster_outlier_detection_ejections_total[5m])",
            "legendFormat": "{{cluster_name}}"
          }
        ]
      },
      {
        "title": "Ejection Percentage",
        "targets": [
          {
            "expr": "(envoy_cluster_outlier_detection_ejections_active / envoy_cluster_membership_healthy) * 100",
            "legendFormat": "{{cluster_name}}"
          }
        ]
      }
    ]
  }
}
```

### Real-time Monitoring

```bash
# Check Envoy statistics
kubectl exec -n <namespace> <pod-name> -c istio-proxy -- \
  curl localhost:15000/stats/prometheus | grep outlier

# Key metrics:
# envoy_cluster_outlier_detection_ejections_active: Currently ejected instances
# envoy_cluster_outlier_detection_ejections_total: Total ejection count
# envoy_cluster_outlier_detection_ejections_consecutive_5xx: Ejections due to 5xx errors
```

### Verify in Kiali

```bash
# Access Kiali
istioctl dashboard kiali

# Things to check:
# 1. Graph → Select service → Traffic tab
# 2. Unhealthy instances shown in red
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

# 4. Check Pilot logs
kubectl logs -n istio-system -l app=istiod | grep outlier
```

### Too Many Instances Being Ejected

```yaml
# Solution 1: Adjust maxEjectionPercent
outlierDetection:
  maxEjectionPercent: 30  # Reduce from 50 to 30

# Solution 2: Increase consecutiveErrors
outlierDetection:
  consecutiveErrors: 10  # Increase from 5 to 10

# Solution 3: Increase interval
outlierDetection:
  interval: 60s  # Increase from 30s to 60s
```

### Split Brain (All Instances Ejected)

```yaml
# Solution: Set minHealthPercent
outlierDetection:
  consecutiveErrors: 5
  interval: 30s
  baseEjectionTime: 30s
  maxEjectionPercent: 50
  minHealthPercent: 50  # Keep at least 50%
```

### Recovery Too Slow After Ejection

```yaml
# Solution: Decrease baseEjectionTime
outlierDetection:
  baseEjectionTime: 15s  # Reduce from 30s to 15s
```

### False Positives from Temporary Errors

```yaml
# Solution: Increase consecutiveErrors + interval
outlierDetection:
  consecutiveErrors: 10  # Increase threshold
  interval: 60s          # Increase analysis interval
```

## Best Practices

### 1. Configuration by Service Type

```yaml
# Critical service (fast detection)
outlierDetection:
  consecutiveErrors: 3
  interval: 10s
  baseEjectionTime: 30s
  maxEjectionPercent: 50

# General service
outlierDetection:
  consecutiveErrors: 5
  interval: 30s
  baseEjectionTime: 60s
  maxEjectionPercent: 30

# Stable service (lenient settings)
outlierDetection:
  consecutiveErrors: 10
  interval: 60s
  baseEjectionTime: 120s
  maxEjectionPercent: 20
```

### 2. Always Use with Connection Pool

```yaml
# Always use with Connection Pool
trafficPolicy:
  connectionPool:
    tcp:
      maxConnections: 100
    http:
      http1MaxPendingRequests: 50
  outlierDetection:
    consecutiveErrors: 5
    interval: 30s
```

### 3. Set Minimum Health Percentage

```yaml
# Prevent Split Brain
outlierDetection:
  minHealthPercent: 50  # Keep at least 50%
  maxEjectionPercent: 30
```

### 4. Gradual Rollout

```yaml
# Phase 1: Observation mode (no ejection)
outlierDetection:
  consecutiveErrors: 5
  interval: 30s
  baseEjectionTime: 30s
  maxEjectionPercent: 0  # No ejection

# Phase 2: Minor ejection
outlierDetection:
  maxEjectionPercent: 10

# Phase 3: Normal operation
outlierDetection:
  maxEjectionPercent: 30
```

### 5. Monitoring and Alerting

```yaml
# Prometheus Alerting Rule
groups:
- name: istio_outlier_detection
  rules:
  - alert: HighEjectionRate
    expr: rate(envoy_cluster_outlier_detection_ejections_total[5m]) > 0.1
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High outlier ejection rate"
      description: "{{ $labels.cluster_name }} has ejection rate > 0.1 req/s"
```

## References

- [Istio Outlier Detection](https://istio.io/latest/docs/reference/config/networking/destination-rule/#OutlierDetection)
- [Envoy Outlier Detection](https://www.envoyproxy.io/docs/envoy/latest/intro/arch_overview/upstream/outlier)
- [Circuit Breaking](https://istio.io/latest/docs/tasks/traffic-management/circuit-breaking/)
