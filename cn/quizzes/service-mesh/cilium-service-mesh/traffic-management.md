# Cilium Service Mesh 流量管理测验

本测验用于检验你对 Cilium Service Mesh 中 L7 流量管理、CiliumEnvoyConfig、负载均衡、流量拆分和 Gateway API 集成的理解。

## 测验问题

### 1. 在 CiliumEnvoyConfig 中，哪个 Envoy filter 用于定义 HTTP 路由规则？

A. envoy.filters.network.tcp_proxy
B. envoy.filters.network.http_connection_manager
C. envoy.filters.http.fault
D. envoy.filters.network.redis_proxy

<details>
<summary>显示答案</summary>

**答案：B. envoy.filters.network.http_connection_manager**

**说明：**
HTTP Connection Manager 是处理 HTTP 流量的核心 Envoy filter。在此 filter 中，你可以通过 route_config 定义基于路径、header 和方法的路由规则。

</details>

### 2. 在 CiliumNetworkPolicy 中定义 L7 HTTP 规则时，哪个字段不可用？

A. method
B. path
C. headers
D. body

<details>
<summary>显示答案</summary>

**答案：D. body**

**说明：**
CiliumNetworkPolicy 的 HTTP L7 规则允许基于 method（HTTP 方法）、path（URL 路径）和 headers（HTTP header）进行过滤。L7 规则不支持 body（请求正文）。

</details>

### 3. 在 Cilium 中应用 Kafka L7 policy 时，哪个不是有效的 apiKey？

A. produce
B. fetch
C. delete
D. metadata

<details>
<summary>显示答案</summary>

**答案：C. delete**

**说明：**
Cilium 的 Kafka L7 policy 支持的 apiKey 包括 produce（消息生产）、fetch（消息消费）、metadata（元数据查询）、offsetcommit、offsetfetch、joingroup 等。`delete` 不是受支持的 Kafka API key。

</details>

### 4. Cilium 基于 eBPF 的 L4 负载均衡中，Maglev hash 的优势是什么？

A. 完全随机的分配
B. 即使 backend 发生变化也能保持会话持久性
C. 最低的内存使用量
D. L7 路由支持

<details>
<summary>显示答案</summary>

**答案：B. 即使 backend 发生变化也能保持会话持久性**

**说明：**
Maglev 是一种一致性 hash 算法，即使添加或移除 backend server，它也能让大多数现有连接保持连接到同一 backend。这对于有状态应用程序或需要会话亲和性的场景很有用。

</details>

### 5. 在 Gateway API HTTPRoute 中配置基于权重的流量拆分，正确的方式是什么？

A. 使用 split 字段
B. 在 backendRefs 中指定 weight 字段
C. 使用 trafficPolicy
D. 使用 destinationRule

<details>
<summary>显示答案</summary>

**答案：B. 在 backendRefs 中指定 weight 字段**

**说明：**
在 Gateway API HTTPRoute 中，通过为 backendRefs 数组中的每个 backend 指定 weight 字段来配置流量拆分。例如，使用 `weight: 90` 和 `weight: 10` 会按照 90:10 的比例拆分流量。

</details>

### 6. 在 CiliumEnvoyConfig 中配置 retry policy 时，retry_on 字段的哪个条件无效？

A. 5xx
B. reset
C. timeout
D. connect-failure

<details>
<summary>显示答案</summary>

**答案：C. timeout**

**说明：**
Envoy 的 retry_on 条件包括 5xx（server 错误）、reset（连接重置）、connect-failure（连接失败）、retriable-4xx 等。`timeout` 不是直接的 retry_on 条件；使用 per_try_timeout 设置每次重试尝试的超时时间。

</details>

### 7. 在 Cilium 中使用 DNS L7 policy 的主要好处是什么？

A. 改善 DNS server 性能
B. 仅允许针对特定 domain 的 DNS 查询
C. DNS cache 失效
D. DNS over HTTPS 支持

<details>
<summary>显示答案</summary>

**答案：B. 仅允许针对特定 domain 的 DNS 查询**

**说明：**
DNS L7 policy 可限制 workload 能够查询哪些 domain。通过使用 matchPattern 或 matchName，你可以确保仅查询允许的 domain，从而防止数据泄露或访问恶意 domain。

</details>

### 8. 在 CiliumEnvoyConfig 中配置本地 Rate Limiting 时使用哪个 filter？

A. envoy.filters.http.ratelimit
B. envoy.filters.http.local_ratelimit
C. envoy.filters.http.bandwidth_limit
D. envoy.filters.http.throttle

<details>
<summary>显示答案</summary>

**答案：B. envoy.filters.http.local_ratelimit**

**说明：**
本地 Rate Limiting 使用 envoy.filters.http.local_ratelimit filter。此 filter 通过 token_bucket 配置限制请求速率。envoy.filters.http.ratelimit 用于与外部 Rate Limit service 通信的全局 Rate Limiting。

</details>

### 9. 在 Gateway API 中配置 HTTP -> HTTPS 重定向时使用哪种 filter 类型？

A. URLRewrite
B. RequestMirror
C. RequestRedirect
D. ResponseHeaderModifier

<details>
<summary>显示答案</summary>

**答案：C. RequestRedirect**

**说明：**
在 Gateway API 中，RequestRedirect filter 用于从 HTTP 重定向到 HTTPS。设置 scheme: https 和 statusCode: 301 可配置永久重定向。

</details>

### 10. Cilium Service Mesh 中流量镜像（shadowing）的用途是什么？

A. 流量加密
B. 将生产流量复制到测试环境
C. 负载均衡优化
D. cache 失效

<details>
<summary>显示答案</summary>

**答案：B. 将生产流量复制到测试环境**

**说明：**
流量镜像会将生产流量的副本发送到另一个 service（例如，使用新版本的测试环境）。这可以在不影响用户的情况下，使用真实流量测试新版本。它通过 request_mirror_policies 配置。

</details>

### 11. 在 CiliumEnvoyConfig 中使用 weighted_clusters 进行 canary Deployment 时，total_weight 的作用是什么？

A. 限制请求总数
B. 定义权重总和的参考值
C. 超时设置
D. 连接限制

<details>
<summary>显示答案</summary>

**答案：B. 定义权重总和的参考值**

**说明：**
total_weight 定义各个 cluster 权重之和的参考值。例如，设置 total_weight: 100，并为 cluster A 分配 90、为 cluster B 分配 10，分别会产生 90% 和 10% 的流量。

</details>

### 12. 在 Gateway API HTTPRoute 的 matches 部分中，使用哪个字段配置基于 header 的路由？

A. headerMatchers
B. headers
C. requestHeaders
D. matchHeaders

<details>
<summary>显示答案</summary>

**答案：B. headers**

**说明：**
在 HTTPRoute 的 matches 部分中，使用 headers 字段配置基于 header 的路由。通过为每个 header 指定 name 和 value，你可以将具有特定 header 值的请求路由到不同的 backend。

</details>
