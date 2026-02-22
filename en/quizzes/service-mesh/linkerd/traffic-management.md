# Linkerd Traffic Management Quiz

This quiz tests your understanding of Linkerd traffic management.

## Quiz Questions

### 1. What cannot be configured per-route in a ServiceProfile?

A. Timeout
B. Retryability
C. Load balancer algorithm
D. Path condition

<details>
<summary>Show Answer</summary>

**Answer: C. Load balancer algorithm**

**Explanation:**
ServiceProfile can configure timeout, retryability (isRetryable), and path conditions (method, pathRegex) per route. The load balancer algorithm is a Linkerd global setting, using EWMA.

</details>

### 2. What load balancing algorithm does Linkerd use?

A. Round Robin
B. Least Connections
C. EWMA (Exponentially Weighted Moving Average)
D. Random

<details>
<summary>Show Answer</summary>

**Answer: C. EWMA (Exponentially Weighted Moving Average)**

**Explanation:**
Linkerd uses the EWMA algorithm to prefer endpoints with faster response latency. It adapts to endpoint state in real-time and automatically reduces traffic to slow endpoints.

</details>

### 3. What standard specification does TrafficSplit follow?

A. CNCF
B. SMI (Service Mesh Interface)
C. OpenAPI
D. gRPC

<details>
<summary>Show Answer</summary>

**Answer: B. SMI (Service Mesh Interface)**

**Explanation:**
TrafficSplit is a CRD that follows the SMI (Service Mesh Interface) standard. SMI defines common interfaces for service meshes to provide compatibility between different mesh implementations.

</details>

### 4. What does a retryBudget retryRatio of 0.2 mean?

A. Only 20% of all requests are retried
B. Only 20% of failed requests are retried
C. Up to 20% additional retries allowed relative to original requests
D. Retry budget resets every 20 seconds

<details>
<summary>Show Answer</summary>

**Answer: C. Up to 20% additional retries allowed relative to original requests**

**Explanation:**
A retryRatio of 0.2 allows up to 20% additional retries relative to the original number of requests. Example: Up to 20 additional retries allowed for 100 requests. This prevents overload from retries.

</details>

### 5. Which is NOT a method to auto-generate a ServiceProfile?

A. Generate from OpenAPI/Swagger spec
B. Generate from live traffic tap
C. Generate from Protobuf definition
D. Auto-generate from Kubernetes Service

<details>
<summary>Show Answer</summary>

**Answer: D. Auto-generate from Kubernetes Service**

**Explanation:**
ServiceProfiles can be generated using `linkerd profile --open-api`, `linkerd viz profile --tap`, and `linkerd profile --proto` commands. They are not auto-generated from Kubernetes Services and must be explicitly defined.

</details>

### 6. What should the sum of TrafficSplit backend weights be for canary deployment?

A. Must be exactly 100
B. Must be exactly 1
C. Any value works (calculated as ratio)
D. Must be exactly 1000

<details>
<summary>Show Answer</summary>

**Answer: C. Any value works (calculated as ratio)**

**Explanation:**
TrafficSplit weights are calculated as relative ratios. weight: 90 and weight: 10 is equivalent to weight: 9 and weight: 1. The sum doesn't need to be 100.

</details>

### 7. What routing condition is NOT supported in HTTPRoute (Gateway API)?

A. Header-based routing
B. Path-based routing
C. Cookie-based routing
D. Source IP-based routing

<details>
<summary>Show Answer</summary>

**Answer: D. Source IP-based routing**

**Explanation:**
HTTPRoute supports header, path, method, and cookie (via headers) based routing. Source IP-based routing is outside the scope of L7 routing and is handled by NetworkPolicy or other mechanisms.

</details>

### 8. What metrics server is used when integrating Flagger with Linkerd?

A. Metrics Server
B. Prometheus
C. InfluxDB
D. Datadog

<details>
<summary>Show Answer</summary>

**Answer: B. Prometheus**

**Explanation:**
Flagger retrieves metrics (success rate, latency, etc.) from Linkerd Viz's Prometheus for canary analysis. When installing Flagger, connect with `--set metricsServer=http://prometheus.linkerd-viz:9090`.

</details>

### 9. What happens on a route where ServiceProfile isRetryable is false?

A. All requests fail
B. No retries occur
C. Timeouts are ignored
D. Route is disabled

<details>
<summary>Show Answer</summary>

**Answer: B. No retries occur**

**Explanation:**
isRetryable: false means requests on that route will not be retried even if they fail. This is suitable for non-idempotent operations like POST requests. The request itself is processed normally.

</details>

### 10. How is the Circuit Breaker pattern implemented in Linkerd?

A. Circuit Breaker CRD
B. Failure Accrual
C. Rate Limiter
D. Timeout Policy

<details>
<summary>Show Answer</summary>

**Answer: B. Failure Accrual**

**Explanation:**
Linkerd implements the circuit breaker pattern through failure accrual. On consecutive failures, it temporarily excludes the endpoint, retries with exponential backoff, and returns to normal state on success.

</details>

### 11. How do you send traffic to a mirror service without traffic splitting?

A. Use TrafficMirror CRD
B. Call mirror service DNS directly
C. All traffic is automatically mirrored
D. Linkerd doesn't support traffic mirroring

<details>
<summary>Show Answer</summary>

**Answer: B. Call mirror service DNS directly**

**Explanation:**
Linkerd itself doesn't have traffic mirroring functionality like Istio. Multi-cluster mirror services (e.g., web-west) must be called directly via DNS or configured with TrafficSplit weights.

</details>

### 12. What happens on a route where ServiceProfile timeout is not set?

A. Default 5-second timeout applies
B. No timeout (unlimited)
C. Request fails immediately
D. Global timeout applies

<details>
<summary>Show Answer</summary>

**Answer: B. No timeout (unlimited)**

**Explanation:**
Routes without a timeout specified in ServiceProfile wait indefinitely without timeout. This is suitable for streaming or long-running operations, but explicitly setting timeouts is generally recommended.

</details>
