# Cilium Service Mesh Traffic Management Quiz

This quiz tests your understanding of L7 traffic management, CiliumEnvoyConfig, load balancing, traffic splitting, and Gateway API integration in Cilium Service Mesh.

## Quiz Questions

### 1. Which Envoy filter is used to define HTTP routing rules in CiliumEnvoyConfig?

A. envoy.filters.network.tcp_proxy
B. envoy.filters.network.http_connection_manager
C. envoy.filters.http.fault
D. envoy.filters.network.redis_proxy

<details>
<summary>Show Answer</summary>

**Answer: B. envoy.filters.network.http_connection_manager**

**Explanation:**
The HTTP Connection Manager is the core Envoy filter for processing HTTP traffic. Within this filter, you can define path-based, header-based, and method-based routing rules through route_config.

</details>

### 2. Which field is NOT available when defining L7 HTTP rules in CiliumNetworkPolicy?

A. method
B. path
C. headers
D. body

<details>
<summary>Show Answer</summary>

**Answer: D. body**

**Explanation:**
CiliumNetworkPolicy's HTTP L7 rules allow filtering based on method (HTTP method), path (URL path), and headers (HTTP headers). body (request body) is not supported in L7 rules.

</details>

### 3. Which is NOT a valid apiKey when applying Kafka L7 policies in Cilium?

A. produce
B. fetch
C. delete
D. metadata

<details>
<summary>Show Answer</summary>

**Answer: C. delete**

**Explanation:**
Cilium's Kafka L7 policies support apiKeys including produce (message production), fetch (message consumption), metadata (metadata queries), offsetcommit, offsetfetch, joingroup, etc. 'delete' is not a supported Kafka API key.

</details>

### 4. What is the advantage of Maglev hashing in Cilium's eBPF-based L4 load balancing?

A. Completely random distribution
B. Session persistence even when backends change
C. Lowest memory usage
D. L7 routing support

<details>
<summary>Show Answer</summary>

**Answer: B. Session persistence even when backends change**

**Explanation:**
Maglev is a consistent hashing algorithm that maintains most existing connections to the same backend even when backend servers are added or removed. This is useful for stateful applications or when session affinity is required.

</details>

### 5. What is the correct way to configure weight-based traffic splitting in Gateway API HTTPRoute?

A. Use the split field
B. Specify weight field in backendRefs
C. Use trafficPolicy
D. Use destinationRule

<details>
<summary>Show Answer</summary>

**Answer: B. Specify weight field in backendRefs**

**Explanation:**
In Gateway API HTTPRoute, traffic splitting is configured by specifying the weight field for each backend in the backendRefs array. For example, using `weight: 90` and `weight: 10` splits traffic in a 90:10 ratio.

</details>

### 6. Which is NOT a valid condition for the retry_on field when configuring retry policies in CiliumEnvoyConfig?

A. 5xx
B. reset
C. timeout
D. connect-failure

<details>
<summary>Show Answer</summary>

**Answer: C. timeout**

**Explanation:**
Envoy's retry_on conditions include 5xx (server errors), reset (connection reset), connect-failure (connection failure), retriable-4xx, etc. 'timeout' is not a direct retry_on condition; per_try_timeout is used to set the timeout for each retry attempt.

</details>

### 7. What is the main benefit of using DNS L7 policies in Cilium?

A. Improved DNS server performance
B. Allow only DNS queries for specific domains
C. DNS cache invalidation
D. DNS over HTTPS support

<details>
<summary>Show Answer</summary>

**Answer: B. Allow only DNS queries for specific domains**

**Explanation:**
DNS L7 policies allow restricting which domains workloads can query. Using matchPattern or matchName, you can ensure only allowed domains are queried, preventing data exfiltration or access to malicious domains.

</details>

### 8. Which filter is used to configure local Rate Limiting in CiliumEnvoyConfig?

A. envoy.filters.http.ratelimit
B. envoy.filters.http.local_ratelimit
C. envoy.filters.http.bandwidth_limit
D. envoy.filters.http.throttle

<details>
<summary>Show Answer</summary>

**Answer: B. envoy.filters.http.local_ratelimit**

**Explanation:**
Local Rate Limiting uses the envoy.filters.http.local_ratelimit filter. This filter limits request rates through token_bucket configuration. envoy.filters.http.ratelimit is used for global Rate Limiting that communicates with external Rate Limit services.

</details>

### 9. Which filter type is used to configure HTTP -> HTTPS redirect in Gateway API?

A. URLRewrite
B. RequestMirror
C. RequestRedirect
D. ResponseHeaderModifier

<details>
<summary>Show Answer</summary>

**Answer: C. RequestRedirect**

**Explanation:**
In Gateway API, the RequestRedirect filter is used to redirect from HTTP to HTTPS. Setting scheme: https and statusCode: 301 configures a permanent redirect.

</details>

### 10. What is the purpose of traffic mirroring (shadowing) in Cilium Service Mesh?

A. Traffic encryption
B. Replicate production traffic to test environment
C. Load balancing optimization
D. Cache invalidation

<details>
<summary>Show Answer</summary>

**Answer: B. Replicate production traffic to test environment**

**Explanation:**
Traffic mirroring sends a copy of production traffic to another service (e.g., a test environment with a new version). This allows testing new versions with real traffic without affecting users. It's configured through request_mirror_policies.

</details>

### 11. What is the role of total_weight in canary deployment using weighted_clusters in CiliumEnvoyConfig?

A. Limit total request count
B. Define the reference value for weight sum
C. Timeout setting
D. Connection limit

<details>
<summary>Show Answer</summary>

**Answer: B. Define the reference value for weight sum**

**Explanation:**
total_weight defines the reference value for the sum of individual cluster weights. For example, setting total_weight: 100 and assigning 90 to cluster A and 10 to cluster B results in 90% and 10% traffic respectively.

</details>

### 12. Which field is used in the matches section to configure header-based routing in Gateway API HTTPRoute?

A. headerMatchers
B. headers
C. requestHeaders
D. matchHeaders

<details>
<summary>Show Answer</summary>

**Answer: B. headers**

**Explanation:**
In HTTPRoute's matches section, the headers field is used to configure header-based routing. By specifying name and value for each header, you can route requests with specific header values to different backends.

</details>
