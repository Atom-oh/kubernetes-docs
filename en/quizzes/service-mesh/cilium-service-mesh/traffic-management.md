# Cilium Service Mesh Traffic Management Quiz

Reviewed against Cilium 1.20.1/Gateway API 1.6.1. See the [traffic guide](../../../service-mesh/cilium-service-mesh/02-traffic-management.md) for complete examples and primary references.

### 1. Which Envoy filter is used to define HTTP routing rules in CiliumEnvoyConfig?

- **A.** envoy.filters.network.tcp_proxy
- **B.** envoy.filters.network.http_connection_manager
- **C.** envoy.filters.http.fault
- **D.** envoy.filters.network.redis_proxy

<details>
<summary>Show Answer</summary>

**Answer: B. envoy.filters.network.http_connection_manager**

The HTTP Connection Manager handles HTTP traffic and obtains routes through inline route_config or RDS. The router HTTP filter and referenced Cluster resources are also needed; listing backend Services alone is insufficient.

</details>

### 2. Which field is NOT available when defining L7 HTTP rules in CiliumNetworkPolicy?

- **A.** method
- **B.** path
- **C.** headers
- **D.** body

<details>
<summary>Show Answer</summary>

**Answer: D. body**

HTTP policy can match method, path and headers, including structured headerMatches. It does not authorize arbitrary request-body fields. Authentication and application-level authorization remain separate.

</details>

### 3. How should Kafka topic-level access be controlled with Cilium 1.20.1?

- **A.** Use Cilium rules.kafka unchanged
- **B.** Use an HTTP body rule to inspect Kafka messages
- **C.** Use Kafka broker ACLs, with L4 policy separately controlling reachability
- **D.** Delete all rules and assume topic permissions remain

<details>
<summary>Show Answer</summary>

**Answer: C. Use Kafka broker ACLs, with L4 policy separately controlling reachability**

Cilium 1.20.1's L7 rules schema supports HTTP and DNS, and rejects the old rules.kafka object. Use L4 network policy for broker reachability and Kafka TLS/SASL plus broker ACLs for topics, groups and operations. Removing obsolete Kafka rules does not preserve topic-level authorization.

</details>

### 4. What does Maglev provide for applicable Cilium eBPF load balancing?

- **A.** Completely random distribution
- **B.** Consistent backend selection with reduced reassignment when membership changes
- **C.** Guaranteed survival of connections to removed backends
- **D.** The lowest possible memory use

<details>
<summary>Show Answer</summary>

**Answer: B. Consistent backend selection with reduced reassignment when membership changes**

Maglev minimizes flow reassignment when the backend set changes for applicable external load balancing. It is separate from ClientIP session affinity and cannot preserve connections to an unavailable backend. Cilium's socket-level east–west path is not subject to this Maglev selection.

</details>

### 5. What is the correct way to configure weight-based traffic splitting in Gateway API HTTPRoute?

- **A.** Use the split field
- **B.** Specify weight field in backendRefs
- **C.** Use trafficPolicy
- **D.** Use destinationRule

<details>
<summary>Show Answer</summary>

**Answer: B. Specify weight field in backendRefs**

backendRefs weights define relative selection probabilities. 90 and 10 express a 90:10 ratio, not an exact count in every ten requests or a per-user session guarantee. The Services, ports and parent listener must resolve and accept the route.

</details>

### 6. Which is NOT a valid condition for the retry_on field when configuring retry policies in CiliumEnvoyConfig?

- **A.** 5xx
- **B.** reset
- **C.** timeout
- **D.** connect-failure

<details>
<summary>Show Answer</summary>

**Answer: C. timeout**

timeout is not a retry_on token. per_try_timeout limits each upstream attempt, including the first; it is not a backoff interval. The guide enables retries only for safe GET operations, explicitly disables non-GET retries and removes caller-supplied Envoy retry/timeout overrides before routing.

</details>

### 7. What is the main benefit of using DNS L7 policies in Cilium?

- **A.** Improved DNS server performance
- **B.** Allow only DNS queries for specific domains
- **C.** DNS cache invalidation
- **D.** DNS over HTTPS support

<details>
<summary>Show Answer</summary>

**Answer: B. Allow only DNS queries for specific domains**

DNS rules constrain query names sent to the selected trusted resolver. They do not by themselves allow connections to the returned addresses or guarantee prevention of exfiltration/DoH. Add separate destination/port policies; include UDP/TCP and actual resolver/search-list behavior.

</details>

### 8. Which filter is used to configure local Rate Limiting in CiliumEnvoyConfig?

- **A.** envoy.filters.http.ratelimit
- **B.** envoy.filters.http.local_ratelimit
- **C.** envoy.filters.http.bandwidth_limit
- **D.** envoy.filters.http.throttle

<details>
<summary>Show Answer</summary>

**Answer: B. envoy.filters.http.local_ratelimit**

envoy.filters.http.local_ratelimit uses a token bucket with explicit enabled/enforced fractions. Those fractions default to 0%, including route-level overrides. The examples use one bucket per Envoy process, shared by its worker threads, rather than a cluster-wide or per-user quota.

</details>

### 9. Which filter type is used to configure HTTP -> HTTPS redirect in Gateway API?

- **A.** URLRewrite
- **B.** RequestMirror
- **C.** RequestRedirect
- **D.** ResponseHeaderModifier

<details>
<summary>Show Answer</summary>

**Answer: C. RequestRedirect**

RequestRedirect can return a redirect with scheme:https. A 301 is permanent but may change the request method in clients. Configure the HTTP listener route separately, prepare a working HTTPS listener/certificate, and avoid silently redirecting writes with method-changing semantics.

</details>

### 10. What is the purpose of traffic mirroring (shadowing) in Cilium Service Mesh?

- **A.** Traffic encryption
- **B.** Replicate production traffic to test environment
- **C.** Load balancing optimization
- **D.** Cache invalidation

<details>
<summary>Show Answer</summary>

**Answer: B. Replicate production traffic to test environment**

request_mirror_policies sends a copy to a shadow backend while ignoring its response for the caller's result. It still copies data, consumes resources and can cause side effects. The guide mirrors approved GET/HEAD traffic to an isolated backend and leaves other methods unmirrored; zero user impact is not guaranteed.

</details>

### 11. How does current Envoy determine the weight total for weighted_clusters?

- **A.** It limits the total number of requests
- **B.** It uses the sum of Cluster weights; total_weight is deprecated
- **C.** It treats weights as timeouts
- **D.** It requires every request to use the lowest-weight Cluster

<details>
<summary>Show Answer</summary>

**Answer: B. It uses the sum of Cluster weights; total_weight is deprecated**

Current Envoy uses the sum of individual Cluster weights. total_weight is deprecated and is omitted from the updated example. For weights 90 and 10 the relative selection ratio is 90:10; this does not implement automatic promotion, rollback or a strict per-window request quota.

</details>

### 12. Which field is used in the matches section to configure header-based routing in Gateway API HTTPRoute?

- **A.** headerMatchers
- **B.** headers
- **C.** requestHeaders
- **D.** matchHeaders

<details>
<summary>Show Answer</summary>

**Answer: B. headers**

HTTPRoute.matches.headers expresses header match conditions. Multiple headers in one match are ANDed; the Gateway API's path/header precedence rules determine selection. A client-supplied version/canary header is not authentication.

</details>
