# Cilium Service Mesh 流量管理测验

根据 Cilium 1.20.3/Gateway API 1.6.3 进行审核。完整示例和主要参考资料请参阅[流量指南](../../../service-mesh/cilium-service-mesh/02-traffic-management.md)。

### 1. 在 CiliumEnvoyConfig 中用于定义 HTTP 路由规则的 Envoy 过滤器是什么？

- **A.** envoy.filters.network.tcp_proxy
- **B.** envoy.filters.network.http_connection_manager
- **C.** envoy.filters.http.fault
- **D.** envoy.filters.network.redis_proxy

<details>
<summary>显示答案</summary>

**答案：B. envoy.filters.network.http_connection_manager**

HTTP Connection Manager 处理 HTTP 流量，并通过内联 route_config 或 RDS 获取路由。还需要 router HTTP 过滤器和被引用的 Cluster 资源；仅列出后端 Service 并不足够。

</details>

### 2. 在 CiliumNetworkPolicy 中定义 L7 HTTP 规则时，以下哪个字段不可用？

- **A.** method
- **B.** path
- **C.** headers
- **D.** body

<details>
<summary>显示答案</summary>

**答案：D. body**

HTTP 策略可以匹配 method、path 和 headers，包括结构化的 headerMatches。它不会授权任意请求正文中的字段。身份验证和应用层授权仍需单独处理。

</details>

### 3. 使用 Cilium 1.20.3 时，应如何控制 Kafka 主题级别的访问？

- **A.** 原样使用 Cilium rules.kafka
- **B.** 使用 HTTP 正文规则检查 Kafka 消息
- **C.** 使用 Kafka 消息代理的 ACL，并通过 L4 策略单独控制可达性
- **D.** 删除所有规则并假设主题权限仍然有效

<details>
<summary>显示答案</summary>

**答案：C. 使用 Kafka 消息代理的 ACL，并通过 L4 策略单独控制可达性**

Cilium 1.20.3 的 L7 规则字段模式（schema）支持 HTTP 和 DNS，并会拒绝旧的 rules.kafka 对象。使用 L4 网络策略控制消息代理的可达性，并使用 Kafka TLS/SASL 和消息代理 ACL 控制主题、组和操作。删除过时的 Kafka 规则并不会保留主题级授权。

</details>

### 4. Maglev 为适用的 Cilium eBPF 负载均衡提供什么？

- **A.** 完全随机的分配
- **B.** 一致的后端选择，并在成员发生变化时减少重新分配
- **C.** 保证与已移除后端的连接能够继续存活
- **D.** 尽可能低的内存使用量

<details>
<summary>显示答案</summary>

**答案：B. 一致的后端选择，并在成员发生变化时减少重新分配**

对于适用的外部负载均衡，当后端集合发生变化时，Maglev 会尽量减少流的重新分配。它与 ClientIP 会话亲和性相互独立，也无法保留与不可用后端的连接。Cilium 的套接字级东西向路径不使用此 Maglev 选择机制。

</details>

### 5. 在 Gateway API HTTPRoute 中配置基于权重的流量拆分，正确的方法是什么？

- **A.** 使用 split 字段
- **B.** 在 backendRefs 中指定 weight 字段
- **C.** 使用 trafficPolicy
- **D.** 使用 destinationRule

<details>
<summary>显示答案</summary>

**答案：B. 在 backendRefs 中指定 weight 字段**

backendRefs 的权重用于定义相对选择概率。90 和 10 表示 90:10 的比例，并不保证每十个请求都严格按九个和一个分配到对应后端，也不保证按用户维持会话。Service、端口和父级侦听器必须能正确解析，且路由必须被接受。

</details>

### 6. 在 CiliumEnvoyConfig 中配置重试策略时，以下哪项不是 retry_on 字段的有效条件？

- **A.** 5xx
- **B.** reset
- **C.** timeout
- **D.** connect-failure

<details>
<summary>显示答案</summary>

**答案：C. timeout**

timeout 不是 retry_on 标记。per_try_timeout 限制每次上游尝试的时间，包括第一次尝试；它不是退避间隔。指南仅对安全的 GET 操作启用重试，明确禁用非 GET 请求的重试，并在路由前移除调用方提供的 Envoy 重试/超时覆盖设置。

</details>

### 7. 在 Cilium 中使用 DNS L7 策略的主要好处是什么？

- **A.** 提高 DNS 服务器性能
- **B.** 仅允许查询特定域名的 DNS 请求
- **C.** DNS 缓存失效
- **D.** 支持 DNS over HTTPS

<details>
<summary>显示答案</summary>

**答案：B. 仅允许查询特定域名的 DNS 请求**

DNS 规则会限制发送到所选可信解析器的查询名称。仅靠这些规则，既不能允许连接到返回的地址，也不能保证防止数据外泄或 DoH。请另外添加目标地址/端口策略；并纳入 UDP/TCP 以及实际的解析器/搜索列表行为。

</details>

### 8. 在 CiliumEnvoyConfig 中用于配置本地速率限制的过滤器是什么？

- **A.** envoy.filters.http.ratelimit
- **B.** envoy.filters.http.local_ratelimit
- **C.** envoy.filters.http.bandwidth_limit
- **D.** envoy.filters.http.throttle

<details>
<summary>显示答案</summary>

**答案：B. envoy.filters.http.local_ratelimit**

envoy.filters.http.local_ratelimit 使用令牌桶，并明确配置启用/执行比例（enabled/enforced）。这些比例默认均为 0%，包括路由级覆盖设置。示例使用每个 Envoy 进程一个令牌桶，由该进程的工作线程共享，而不是使用集群范围或按用户划分的配额。

</details>

### 9. 在 Gateway API 中，使用哪种过滤器类型配置 HTTP -> HTTPS 重定向？

- **A.** URLRewrite
- **B.** RequestMirror
- **C.** RequestRedirect
- **D.** ResponseHeaderModifier

<details>
<summary>显示答案</summary>

**答案：C. RequestRedirect**

RequestRedirect 可以使用 scheme:https 返回重定向。301 是永久重定向，但某些客户端可能会因此更改请求方法。请单独配置 HTTP 侦听器路由，确保 HTTPS 侦听器/证书可正常工作，并避免在不提示的情况下以可能改变请求方法的方式重定向写入请求。

</details>

### 10. 在 Cilium Service Mesh 中，流量镜像（影子流量）的用途是什么？

- **A.** 流量加密
- **B.** 将生产流量复制到测试环境
- **C.** 优化负载均衡
- **D.** 缓存失效

<details>
<summary>显示答案</summary>

**答案：B. 将生产流量复制到测试环境**

request_mirror_policies 会将流量副本发送到影子后端，但忽略其响应，不将其用于决定调用方收到的结果。它仍会复制数据、消耗资源，也可能造成副作用。指南会将获准的 GET/HEAD 流量镜像到隔离的后端，而其他方法不进行镜像；这并不能保证对用户零影响。

</details>

### 11. 当前 Envoy 如何确定 weighted_clusters 的权重总和？

- **A.** 限制请求总数
- **B.** 使用各 Cluster 权重之和；total_weight 已弃用
- **C.** 将权重视为超时时间
- **D.** 要求每个请求都使用权重最低的 Cluster

<details>
<summary>显示答案</summary>

**答案：B. 使用各 Cluster 权重之和；total_weight 已弃用**

当前 Envoy 使用各个 Cluster 权重之和。total_weight 已弃用，因此更新后的示例中不再包含此字段。权重 90 和 10 表示 90:10 的相对选择比例；这并不能实现自动推进发布、回滚或严格的时间窗口内请求配额。

</details>

### 12. 在 Gateway API HTTPRoute 的 matches 部分中，哪个字段用于配置基于标头的路由？

- **A.** headerMatchers
- **B.** headers
- **C.** requestHeaders
- **D.** matchHeaders

<details>
<summary>显示答案</summary>

**答案：B. headers**

HTTPRoute.matches.headers 用于表达标头匹配条件。同一匹配项中的多个标头采用 AND 逻辑；具体选择由 Gateway API 的路径/标头优先级规则决定。由客户端提供的版本/金丝雀发布标头不能作为身份验证。

</details>
