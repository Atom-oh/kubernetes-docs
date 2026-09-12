# Linkerd Traffic Management Quiz

Based on the [maintained traffic guide](../../../service-mesh/linkerd/03-traffic-management.md), reviewed September 11, 2026.

### 1. What cannot be configured per route in a ServiceProfile?

- A. Timeout
- B. Retryability
- C. Load balancer algorithm
- D. Path condition

<details>
<summary>Show Answer</summary>

**Answer: C**

**Explanation:** ServiceProfile routes can specify timeout, isRetryable and method/path conditions. They do not select a load-balancing algorithm. This does not imply a universal global algorithm switch exists.

</details>

### 2. What describes Linkerd HTTP load balancing?

- A. Strict round robin
- B. Always select the fewest connections
- C. Latency-aware EWMA behavior
- D. Always select a random endpoint without latency information

<details>
<summary>Show Answer</summary>

**Answer: C**

**Explanation:** EWMA favors suitable low-latency candidates, but it does not guarantee that every request selects the globally lowest displayed score. HTTP is balanced at request granularity; TCP is balanced at connection granularity.

</details>

### 3. Which specification defines the legacy TrafficSplit resource?

- A. CNCF
- B. SMI (Service Mesh Interface)
- C. OpenAPI
- D. gRPC

<details>
<summary>Show Answer</summary>

**Answer: B**

**Explanation:** TrafficSplit is an SMI resource. Linkerd TrafficSplit/linkerd-smi is deprecated and requires its extension/CRDs. The maintained guide uses supported Gateway API HTTPRoutes for new configurations; applying a legacy resource alone does not install that extension.

</details>

### 4. What does ServiceProfile retryRatio:0.2 contribute to the retry budget?

- A. Exactly 20% of every request stream must be retried
- B. Only 20% of failed requests may be retried
- C. A proportional allowance relative to original requests, in addition to minRetriesPerSecond
- D. A budget reset every 20 seconds

<details>
<summary>Show Answer</summary>

**Answer: C**

**Explanation:** The proportional contribution is not a strict 20% total cap when minRetriesPerSecond also adds allowance. ttl is the lookback/retention window, not a periodic reset. Eligibility, buffering and deadlines still constrain actual retries.

</details>

### 5. Which input alone cannot infer the application operations needed for a ServiceProfile?

- A. An OpenAPI specification
- B. Observed live traffic via tap
- C. A protobuf service definition
- D. A Kubernetes Service selector and port list

<details>
<summary>Show Answer</summary>

**Answer: D**

**Explanation:** The CLI supports OpenAPI/protobuf generation and Viz supports tap-based generation. Use a short Service name with -n; the tap command also needs its positional Service argument. Review generated matches and retry safety because sampled traffic is not a complete API inventory.

</details>

### 6. Which statement about backend weights is correct?

- A. They must total exactly 100
- B. They must total exactly 1
- C. Valid nonnegative relative weights need a usable positive total; 90/10 and 9/1 express the same ratio
- D. Negative weights and a zero total always work

<details>
<summary>Show Answer</summary>

**Answer: C**

**Explanation:** Weights are relative, subject to the selected resource schema and backend validity. The sum need not be 100, and the configured proportion does not guarantee exact short-window request counts. New examples use HTTPRoute; TrafficSplit is the legacy SMI path.

</details>

### 7. Which is not an HTTPRoute request-match field?

- A. HTTP header
- B. HTTP path
- C. HTTP method
- D. Source IP

<details>
<summary>Show Answer</summary>

**Answer: D**

**Explanation:** HTTPRoute supports header/path/method matching. An exact Cookie header match compares the whole header value, not individual cookie pairs. A caller-controlled cohort/debug header is not authorization. Use suitable network/security policy for source-address restrictions.

</details>

### 8. Which provider do the guide’s custom Linkerd Flagger MetricTemplates use?

- A. Kubernetes Metrics Server
- B. Prometheus
- C. An undeclared InfluxDB Service
- D. A mandatory Datadog backend

<details>
<summary>Show Answer</summary>

**Answer: B**

**Explanation:** These templates query Linkerd Viz Prometheus with explicit namespace/deployment/direction scope. Flagger supports other providers too. The example uses gatewayapi:v1 routing and custom metric names; meshProvider:linkerd still selects the legacy SMI router in Flagger1.45.0.

</details>

### 9. What does isRetryable:false mean for a matched ServiceProfile route?

- A. All matching requests fail
- B. The ServiceProfile mechanism does not retry that route
- C. All timeout policies are ignored
- D. The route is disabled

<details>
<summary>Show Answer</summary>

**Answer: B**

**Explanation:** The request can still be forwarded normally. This setting does not stop client/SDK/other-proxy retries. In the current annotation path, limit:0 is not a reliable disable switch in edge-26.9.1; keep Service defaults free of retries and opt in only the intended read routes.

</details>

### 10. How is Linkerd HTTP circuit breaking configured?

- A. An automatically installed CircuitBreaker CRD
- B. Opt-in Service failure-accrual annotations
- C. An unconditional default five-connection-failure rule
- D. A periodic synthetic readiness-probe loop

<details>
<summary>Show Answer</summary>

**Answer: B**

**Explanation:** Failure accrual is disabled by default and is incompatible with a ServiceProfile for the Service. The consecutive policy defaults to seven supported response failures. Recovery probation uses a real application request after backoff, not a periodic synthetic probe.

</details>

### 11. How can a client explicitly call an exported service represented by a multicluster mirror Service?

- A. Apply a fictional TrafficMirror CRD
- B. Call the mirror Service DNS name, with the required connectivity and policy
- C. Every local request is automatically duplicated
- D. A mirror Service can never be called

<details>
<summary>Show Answer</summary>

**Answer: B**

**Explanation:** Multicluster service mirroring provides discovery/routing to a remote service. Calling its DNS name sends the request there; it does not inherently duplicate the request for shadow testing. Request mirroring is a separate feature whose support must be checked for the chosen implementation/version.

</details>

### 12. What does omitting timeout on a ServiceProfile route mean?

- A. An automatic five-second profile timeout
- B. No timeout from that ServiceProfile field
- C. Immediate failure
- D. All other layer timeouts are removed

<details>
<summary>Show Answer</summary>

**Answer: B**

**Explanation:** The field adds no route timeout, but application, client, transport, proxy and load-balancer limits may still apply. It is not an unlimited end-to-end guarantee. Streaming deadlines and cancellation need explicit application-aware design.

</details>
