# Circuit Breaker

Circuit Breaker automatically isolates failing services to prevent cascading failures.

## Table of Contents

1. [Why Circuit Breaker?](#why-circuit-breaker)
2. [Circuit Breaker Overview](#circuit-breaker-overview)
3. [Connection Pool Settings](#connection-pool-settings)
4. [Outlier Detection](#outlier-detection)
5. [Combination with Retry Policy](#combination-with-retry-policy)
6. [Practical Examples](#practical-examples)
7. [External Service Circuit Breaker](#external-service-circuit-breaker)
8. [Monitoring and Debugging](#monitoring-and-debugging)
9. [Important Considerations](#important-considerations)
10. [Best Practices](#best-practices)

## Why Circuit Breaker?

### Preventing Cascading Failures

In microservice architecture, it prevents failures from one service from propagating to other services.

![Flowchart contrasting a microservice chain without a circuit breaker, where Service A's slow response and timeouts cascade into failures at Service B, C, and D, against the same chain with a circuit breaker, where Service B fast-fails and enters an open circuit while Service C and D continue operating normally.](../../../.gitbook/assets/en-service-mesh-istio-traffic-management-07-circuit-breaker-0.png)

### Key Benefits

| Problem | Without Circuit Breaker | With Circuit Breaker |
|---------|------------------------|----------------------|
| **Response Time** | Wait until timeout (30s+) | Immediate failure (1ms) |
| **Resource Usage** | Thread/connection exhaustion | Resource protection |
| **Failure Propagation** | Cascading failures occur | Failure isolation |
| **Recovery Time** | Manual intervention required | Automatic recovery attempts |

## Circuit Breaker Overview

![State machine showing the circuit breaker cycling from Closed (all requests pass) to Open (requests fail fast) once the consecutive-error threshold is exceeded, then to HalfOpen (limited test requests) after the wait time elapses, returning to Closed on success or back to Open on failure.](../../../.gitbook/assets/en-service-mesh-istio-traffic-management-07-circuit-breaker-1.png)

## Connection Pool Settings

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews-circuit-breaker
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
```

## Outlier Detection

Outlier Detection automatically removes unhealthy instances.

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews-outlier
spec:
  host: reviews
  trafficPolicy:
    outlierDetection:
      consecutiveErrors: 5        # 5 consecutive errors
      interval: 30s               # Check every 30 seconds
      baseEjectionTime: 30s       # Remove for 30 seconds
      maxEjectionPercent: 50      # Remove up to 50%
      minHealthPercent: 40        # Maintain at least 40%
```

### Advanced Outlier Detection Settings

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: advanced-outlier
spec:
  host: api-service
  trafficPolicy:
    outlierDetection:
      # Consecutive error based
      consecutiveGatewayErrors: 5    # 5xx errors 5 times
      consecutive5xxErrors: 3        # 500~599 errors 3 times

      # Time intervals
      interval: 10s                  # Check every 10 seconds
      baseEjectionTime: 30s          # First ejection time
      maxEjectionTime: 300s          # Maximum ejection time

      # Rate limits
      maxEjectionPercent: 50         # Remove up to 50%
      minHealthPercent: 30           # Maintain at least 30%

      # Success rate based
      splitExternalLocalOriginErrors: true
```

## Combination with Retry Policy

Use Circuit Breaker together with Retry to increase resilience.

### Basic Combination

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: reviews-retry
spec:
  hosts:
  - reviews
  http:
  - route:
    - destination:
        host: reviews
    retries:
      attempts: 3                    # 3 retries
      perTryTimeout: 2s              # 2 second timeout per attempt
      retryOn: 5xx,reset,connect-failure
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews-circuit-breaker
spec:
  host: reviews
  trafficPolicy:
    connectionPool:
      http:
        http1MaxPendingRequests: 10
        maxRequestsPerConnection: 2
    outlierDetection:
      consecutiveErrors: 5
      interval: 10s
      baseEjectionTime: 30s
```

### Retry Budget Pattern

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: payment-retry-budget
spec:
  hosts:
  - payment-service
  http:
  - route:
    - destination:
        host: payment-service
    retries:
      attempts: 2                    # Minimize retries
      perTryTimeout: 1s              # Fast fail
      retryOn: retriable-4xx,5xx
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: payment-circuit-breaker
spec:
  host: payment-service
  trafficPolicy:
    connectionPool:
      http:
        http1MaxPendingRequests: 5   # Low queue
        maxRequestsPerConnection: 1  # 1 request per connection
    outlierDetection:
      consecutiveErrors: 3           # Fast blocking
      interval: 5s
      baseEjectionTime: 60s          # Long recovery time
```

## Practical Examples

### 1. Circuit Breaker for Services Inside the Mesh

#### Scenario: Database Service Protection

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: database-service-circuit-breaker
  namespace: production
spec:
  host: database-service
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 100          # Maximum 100 connections
      http:
        http1MaxPendingRequests: 50  # 50 pending requests
        http2MaxRequests: 100        # HTTP/2 100 concurrent requests
        maxRequestsPerConnection: 2  # Maximum 2 requests per connection
        idleTimeout: 60s             # Idle connection timeout
    outlierDetection:
      consecutiveErrors: 5
      interval: 30s
      baseEjectionTime: 30s
      maxEjectionPercent: 50
  subsets:
  - name: v1
    labels:
      version: v1
  - name: v2
    labels:
      version: v2
```

**Use Cases**:
- Prevent database connection pool exhaustion
- Block cascading failures from slow queries
- Automatically remove unhealthy instances

### 2. maxConnections: 1 Pattern (Single Connection)

#### Scenario: Legacy System or Resource-Constrained Service

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: legacy-system-protection
spec:
  host: legacy-api-service
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 1            # Limit to 1 connection
      http:
        http1MaxPendingRequests: 1   # 1 pending request
        maxRequestsPerConnection: 1  # 1 request per connection
        h2UpgradePolicy: DO_NOT_UPGRADE  # Prevent HTTP/2 upgrade
    outlierDetection:
      consecutiveErrors: 1           # Block immediately on 1 error
      interval: 10s
      baseEjectionTime: 60s
```

**Use Cases**:
- When legacy systems cannot handle concurrent connections
- When external API rate limits are very strict
- When sequential processing with a single connection is required

### 3. Per-Subset Circuit Breaker

#### Scenario: Different Circuit Breaker Settings per Version

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews-subset-circuit-breaker
spec:
  host: reviews
  trafficPolicy:
    # Default policy (all subsets)
    connectionPool:
      http:
        http1MaxPendingRequests: 50
        maxRequestsPerConnection: 2
    outlierDetection:
      consecutiveErrors: 5
      interval: 30s
      baseEjectionTime: 30s
  subsets:
  - name: v1
    labels:
      version: v1
    # v1 uses default policy

  - name: v2
    labels:
      version: v2
    trafficPolicy:
      # v2 has stricter policy (new version testing)
      connectionPool:
        http:
          http1MaxPendingRequests: 10
          maxRequestsPerConnection: 1
      outlierDetection:
        consecutiveErrors: 3
        interval: 10s
        baseEjectionTime: 60s

  - name: v3-canary
    labels:
      version: v3
    trafficPolicy:
      # v3 Canary is very strict (initial deployment)
      connectionPool:
        http:
          http1MaxPendingRequests: 5
          maxRequestsPerConnection: 1
      outlierDetection:
        consecutiveErrors: 1
        interval: 5s
        baseEjectionTime: 120s
```

### 4. Advanced Connection Pool Pattern

#### Scenario: High-Performance Service

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: high-performance-service
spec:
  host: api-gateway
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 1000         # High concurrent connections
        connectTimeout: 3s
        tcpKeepalive:
          time: 7200s
          interval: 75s
          probes: 9
      http:
        http1MaxPendingRequests: 500
        http2MaxRequests: 1000
        maxRequestsPerConnection: 100  # Connection reuse
        idleTimeout: 300s
        h2UpgradePolicy: UPGRADE       # Use HTTP/2
    outlierDetection:
      consecutiveErrors: 10          # Lenient setting
      interval: 60s
      baseEjectionTime: 30s
      maxEjectionPercent: 20         # Remove up to 20% only
```

### 5. Health Check Based Circuit Breaker

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: health-check-circuit-breaker
spec:
  host: payment-service
  trafficPolicy:
    outlierDetection:
      # HTTP status code based
      consecutiveGatewayErrors: 5    # 502, 503, 504
      consecutive5xxErrors: 3        # 500~599

      # Performance based
      interval: 10s
      baseEjectionTime: 30s
      maxEjectionTime: 300s          # Maximum 5 minutes

      # Dynamic adjustment
      splitExternalLocalOriginErrors: true
      consecutiveLocalOriginFailures: 5
```

## External Service Circuit Breaker

Use with ServiceEntry to protect external services.

### 1. External API Circuit Breaker

```yaml
# ServiceEntry: Register external API
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: external-payment-api
spec:
  hosts:
  - api.payment-provider.com
  ports:
  - number: 443
    name: https
    protocol: HTTPS
  location: MESH_EXTERNAL
  resolution: DNS
---
# DestinationRule: Apply Circuit Breaker
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: external-payment-api-circuit-breaker
spec:
  host: api.payment-provider.com
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 10           # External API is limited
      http:
        http1MaxPendingRequests: 5
        maxRequestsPerConnection: 1  # Minimize connection reuse
    outlierDetection:
      consecutiveErrors: 3           # Fast blocking
      interval: 30s
      baseEjectionTime: 120s         # Long recovery time
      maxEjectionPercent: 100        # Can completely block
    tls:
      mode: SIMPLE                   # TLS connection
```

### 2. External Database Circuit Breaker

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: external-mongodb
spec:
  hosts:
  - mongodb.external-cluster.com
  ports:
  - number: 27017
    name: tcp
    protocol: TCP
  location: MESH_EXTERNAL
  resolution: DNS
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: external-mongodb-circuit-breaker
spec:
  host: mongodb.external-cluster.com
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 50
        connectTimeout: 5s
    outlierDetection:
      consecutiveErrors: 5
      interval: 60s
      baseEjectionTime: 60s
```

### 3. Rate Limited External Service

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: rate-limited-api
spec:
  hosts:
  - api.rate-limited-service.com
  ports:
  - number: 443
    name: https
    protocol: HTTPS
  location: MESH_EXTERNAL
  resolution: DNS
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: rate-limited-api-protection
spec:
  host: api.rate-limited-service.com
  trafficPolicy:
    connectionPool:
      http:
        http1MaxPendingRequests: 1   # Minimize queue
        maxRequestsPerConnection: 1  # Prevent rate limit exceeding
        idleTimeout: 1s              # Fast connection release
    outlierDetection:
      consecutiveErrors: 1           # Block immediately on 429 error
      interval: 60s
      baseEjectionTime: 300s         # Wait 5 minutes (rate limit reset)
---
# VirtualService: Retry settings
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: rate-limited-api-retry
spec:
  hosts:
  - api.rate-limited-service.com
  http:
  - route:
    - destination:
        host: api.rate-limited-service.com
    retries:
      attempts: 0                    # Disable retry (rate limit)
    timeout: 10s
```

## Monitoring and Debugging

### Check Envoy Metrics

```bash
# Check Circuit Breaker status
kubectl exec -it <pod-name> -c istio-proxy -- \
  curl localhost:15000/stats/prometheus | grep circuit_breakers

# Outlier Detection status
kubectl exec -it <pod-name> -c istio-proxy -- \
  curl localhost:15000/stats/prometheus | grep outlier_detection

# Connection Pool status
kubectl exec -it <pod-name> -c istio-proxy -- \
  curl localhost:15000/stats/prometheus | grep upstream_rq
```

### Key Metrics

```yaml
# Prometheus queries
# Circuit Breaker Open count
envoy_cluster_circuit_breakers_default_rq_open

# Pending request count
envoy_cluster_circuit_breakers_default_rq_pending_open

# Outlier Detection Ejection
envoy_cluster_outlier_detection_ejections_active

# Connection pool overflow
envoy_cluster_upstream_rq_pending_overflow

# Retry count
envoy_cluster_upstream_rq_retry
```

### Grafana Dashboard

```yaml
# Circuit Breaker Dashboard
- expr: rate(envoy_cluster_circuit_breakers_default_rq_open[5m])
  legend: "Circuit Breaker Open Rate"

- expr: envoy_cluster_outlier_detection_ejections_active
  legend: "Ejected Instances"

- expr: rate(envoy_cluster_upstream_rq_pending_overflow[5m])
  legend: "Connection Pool Overflow"
```

### istioctl Commands

```bash
# Check Proxy configuration
istioctl proxy-config cluster <pod-name> --fqdn reviews.default.svc.cluster.local

# Check Circuit Breaker settings
istioctl proxy-config cluster <pod-name> -o json | \
  jq '.[] | select(.name=="outbound|9080||reviews.default.svc.cluster.local") | .circuitBreakers'

# Check Outlier Detection settings
istioctl proxy-config cluster <pod-name> -o json | \
  jq '.[] | select(.name=="outbound|9080||reviews.default.svc.cluster.local") | .outlierDetection'
```

## Important Considerations

### Circuit Breaker Does Not Guarantee Data Consistency

**Core Principle**: Circuit Breaker is a tool for **failure isolation**, not for **duplicate request prevention** or **data consistency guarantee**.

#### Circuit Breaker's Role and Limitations

![Grouped list contrasting what a circuit breaker does — isolate failing services, prevent cascading failures, protect system resources, and attempt auto recovery — against what it does not do: prevent duplicate requests, guarantee data consistency, manage transactions, or guarantee idempotency.](../../../.gitbook/assets/en-service-mesh-istio-traffic-management-07-circuit-breaker-2.png)

#### Problem Scenario: Retry + Circuit Breaker

![Sequence diagram showing a client's payment request retried after a timeout, each retry re-inserting the payment into the database, until the third attempt finally returns 200 OK — leaving three duplicate payment inserts even though the circuit breaker's five-consecutive-error threshold was never reached.](../../../.gitbook/assets/en-service-mesh-istio-traffic-management-07-circuit-breaker-3.png)

**Problem**: Before Circuit Breaker activates (after 5 consecutive errors), **3 duplicate payments** have already occurred.

#### Incorrect Usage Example

```yaml
# Dangerous: POST request + Retry + Circuit Breaker
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: payment-dangerous
spec:
  hosts:
  - payment-service
  http:
  - route:
    - destination:
        host: payment-service
    retries:
      attempts: 3  # 3 retries on POST
      perTryTimeout: 2s
      retryOn: 5xx,reset
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: payment-circuit-breaker
spec:
  host: payment-service
  trafficPolicy:
    outlierDetection:
      consecutiveErrors: 5
      interval: 30s
      baseEjectionTime: 30s

# Result:
# - Up to 15 duplicates possible before Circuit Breaker activates (3 retries x 5 errors)
# - Critical operations like payment, inventory deduction get duplicated
# - Data consistency destroyed
```

#### Correct Usage Patterns

**Pattern 1: Circuit Breaker Only (Disable Retry)**

```yaml
# Safe: Read-only + Circuit Breaker
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: product-catalog-safe
spec:
  hosts:
  - product-catalog
  http:
  - match:
    - method:
        regex: "GET|HEAD|OPTIONS"  # Read-only only
    route:
    - destination:
        host: product-catalog
    retries:
      attempts: 3  # GET is safe
      perTryTimeout: 2s
      retryOn: 5xx,reset,connect-failure
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: product-catalog-circuit-breaker
spec:
  host: product-catalog
  trafficPolicy:
    outlierDetection:
      consecutiveErrors: 5
      interval: 30s
      baseEjectionTime: 30s
```

```yaml
# Safe: Disable Retry for POST
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: payment-safe
spec:
  hosts:
  - payment-service
  http:
  - match:
    - method:
        exact: POST
    route:
    - destination:
        host: payment-service
    timeout: 10s
    retries:
      attempts: 0  # Disable Retry for POST
      # Or
      # attempts: 1
      # retryOn: connect-failure,refused-stream  # Network only
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: payment-circuit-breaker
spec:
  host: payment-service
  trafficPolicy:
    outlierDetection:
      consecutiveErrors: 5
      interval: 30s
      baseEjectionTime: 30s
```

**Pattern 2: Application-Level Idempotency + Circuit Breaker**

```python
# Server: Idempotency Key validation
@app.route('/payment', methods=['POST'])
def create_payment():
    idempotency_key = request.headers.get('X-Idempotency-Key')

    if not idempotency_key:
        return jsonify({"error": "Missing Idempotency-Key"}), 400

    # Check if request was already processed
    if redis.exists(f"payment:idempotency:{idempotency_key}"):
        cached_result = redis.get(f"payment:result:{idempotency_key}")
        return jsonify(json.loads(cached_result)), 200

    # Process new payment
    try:
        payment = process_payment(request.json)

        # Cache result (24 hours)
        redis.setex(f"payment:idempotency:{idempotency_key}", 86400, "1")
        redis.setex(f"payment:result:{idempotency_key}", 86400,
                    json.dumps(payment))

        return jsonify(payment), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500
```

```yaml
# Istio: Retry is safe when Idempotency is guaranteed
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: payment-with-idempotency
spec:
  hosts:
  - payment-service
  http:
  - match:
    - headers:
        x-idempotency-key:
          regex: ".+"  # Idempotency Key required
    route:
    - destination:
        host: payment-service
    retries:
      attempts: 3  # Safe with Idempotency
      perTryTimeout: 2s
      retryOn: 5xx,reset
  - route:  # Disable Retry without Idempotency Key
    - destination:
        host: payment-service
    retries:
      attempts: 0
```

#### Safety Strategy by Service Type

| Service Type | Retry | Circuit Breaker | Idempotency Required |
|-------------|-------|----------------|---------------------|
| **Product Catalog** | 3 times | Required | Not required |
| **Shopping Cart** | 3 times | Required | Not required |
| **Order Creation** | 0 times | Required | Required |
| **Payment** | 0 times | Required | Required |
| **Inventory Deduction** | 0 times | Required | Required |
| **Points Accumulation** | 0 times | Required | Required |
| **Notification Sending** | 3 times (idempotent) | Required | Recommended |

#### Connection Pool and Data Consistency

Connection Pool settings also **do not guarantee data consistency**. They only limit the number of concurrent connections.

```yaml
# Misconception: Does maxConnections=1 prevent duplicates?
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: payment-single-connection
spec:
  host: payment-service
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 1  # Does NOT prevent duplicates
      http:
        http1MaxPendingRequests: 1

# maxConnections=1:
# - Only limits concurrent connections
# - Cannot prevent duplicate requests from Retry
# - Retries after network timeout are separate connections
```

#### Practical Checklist

**Pre-deployment verification**:

- [ ] Check Retry settings for POST/PUT/DELETE/PATCH requests
- [ ] Set `attempts: 0` or `retryOn: connect-failure` for non-idempotent requests
- [ ] Review duplicate possibility when combining Circuit Breaker and Retry
- [ ] Implement Idempotency Key for critical operations (payment, inventory)
- [ ] Confirm application-level validation logic exists
- [ ] Perform failure simulation in test environment

**Monitoring**:

```bash
# Check Retry occurrence count
kubectl exec -n <namespace> <pod> -c istio-proxy -- \
  curl -s localhost:15000/stats/prometheus | grep upstream_rq_retry

# Check Circuit Breaker activation
kubectl exec -n <namespace> <pod> -c istio-proxy -- \
  curl -s localhost:15000/stats/prometheus | grep circuit_breakers

# Check logs for suspected duplicate requests
kubectl logs -n <namespace> <pod> | grep -i "duplicate\|idempotency"
```

## Best Practices

### 1. Gradual Configuration

```yaml
# Stage 1: Start with lenient settings
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: service-circuit-breaker-stage1
spec:
  host: my-service
  trafficPolicy:
    connectionPool:
      http:
        http1MaxPendingRequests: 100
        maxRequestsPerConnection: 10
    outlierDetection:
      consecutiveErrors: 10        # Lenient
      interval: 60s
      baseEjectionTime: 30s
```

```yaml
# Stage 2: Adjust after monitoring
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: service-circuit-breaker-stage2
spec:
  host: my-service
  trafficPolicy:
    connectionPool:
      http:
        http1MaxPendingRequests: 50
        maxRequestsPerConnection: 5
    outlierDetection:
      consecutiveErrors: 5         # Moderate
      interval: 30s
      baseEjectionTime: 30s
```

### 2. Service Type-Specific Configuration

```yaml
# Frontend service: Lenient
connectionPool:
  http:
    http1MaxPendingRequests: 100
    maxRequestsPerConnection: 10
outlierDetection:
  consecutiveErrors: 10

# Backend service: Moderate
connectionPool:
  http:
    http1MaxPendingRequests: 50
    maxRequestsPerConnection: 5
outlierDetection:
  consecutiveErrors: 5

# Database/Cache: Strict
connectionPool:
  http:
    http1MaxPendingRequests: 10
    maxRequestsPerConnection: 2
outlierDetection:
  consecutiveErrors: 3

# External API: Very strict
connectionPool:
  http:
    http1MaxPendingRequests: 5
    maxRequestsPerConnection: 1
outlierDetection:
  consecutiveErrors: 1
```

### 3. Alert Configuration

```yaml
# Prometheus Alert Rules
groups:
- name: circuit-breaker
  rules:
  - alert: CircuitBreakerOpen
    expr: envoy_cluster_circuit_breakers_default_rq_open > 0
    for: 1m
    annotations:
      summary: "Circuit breaker is open"

  - alert: HighConnectionPoolOverflow
    expr: rate(envoy_cluster_upstream_rq_pending_overflow[5m]) > 10
    for: 2m
    annotations:
      summary: "Connection pool overflow rate is high"

  - alert: HighOutlierEjectionRate
    expr: rate(envoy_cluster_outlier_detection_ejections_total[5m]) > 5
    for: 3m
    annotations:
      summary: "High outlier ejection rate"
```

### 4. Test Scenarios

```bash
#!/bin/bash
# Circuit Breaker test

# 1. Normal traffic
echo "=== Normal Traffic ==="
for i in {1..10}; do
  curl -s http://service/api | jq .status
  sleep 0.1
done

# 2. Increased load
echo "=== Increased Load ==="
for i in {1..100}; do
  curl -s http://service/api &
done
wait

# 3. Check Circuit Breaker status
echo "=== Circuit Breaker Status ==="
istioctl proxy-config cluster <pod> | grep circuit_breakers

# 4. Wait for recovery
echo "=== Waiting for Recovery ==="
sleep 30

# 5. Verify recovery
echo "=== Recovery Check ==="
curl -s http://service/api | jq .status
```

### 5. Documentation Template

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: my-service-circuit-breaker
  annotations:
    # Configuration purpose
    purpose: "Protect database connection pool"

    # Threshold rationale
    threshold-rationale: |
      - maxConnections: 100 (DB connection pool size)
      - consecutiveErrors: 5 (observed error pattern)
      - baseEjectionTime: 30s (average recovery time)

    # Test results
    test-results: |
      - Load test: 1000 RPS without overflow
      - Failure test: Circuit opens after 5 errors
      - Recovery test: Auto-recovery after 30s

    # Operations guide
    operations: |
      - Monitor: envoy_cluster_circuit_breakers_*
      - Alert: Circuit open > 1min
      - Rollback: kubectl delete dr my-service-circuit-breaker
```

## References

- [Istio Circuit Breaker](https://istio.io/latest/docs/tasks/traffic-management/circuit-breaking/)
- [Envoy Circuit Breaking](https://www.envoyproxy.io/docs/envoy/latest/intro/arch_overview/upstream/circuit_breaking)
- [Envoy Outlier Detection](https://www.envoyproxy.io/docs/envoy/latest/intro/arch_overview/upstream/outlier)
- [Netflix Hystrix](https://github.com/Netflix/Hystrix/wiki/How-it-Works)
