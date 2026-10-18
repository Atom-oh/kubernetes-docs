# Linkerd 流量管理测验

基于[维护中的流量指南](../../../service-mesh/linkerd/03-traffic-management.md)，审阅日期：2026 年 10 月 16 日。

### 1. ServiceProfile 中哪些内容不能按路由配置？

- A. 超时
- B. 可重试性
- C. 负载均衡算法
- D. 路径条件

<details>
<summary>显示答案</summary>

**答案：C**

**解释**：ServiceProfile 路由可以指定超时、isRetryable 以及方法/路径条件，但不能选择负载均衡算法。这并不意味着存在通用的全局算法开关。

</details>

### 2. 哪项描述了 Linkerd HTTP 负载均衡？

- A. 严格轮询
- B. 始终选择连接数最少的端点
- C. 基于延迟感知 EWMA 的行为
- D. 始终在没有延迟信息的情况下随机选择一个端点

<details>
<summary>显示答案</summary>

**答案：C**

**解释**：EWMA 会优先选择合适的低延迟候选端点，但不保证每个请求都会选择全局显示评分最低的端点。HTTP 按请求粒度进行负载均衡；TCP 按连接粒度进行负载均衡。

</details>

### 3. 哪个规范定义了旧版 TrafficSplit 资源？

- A. CNCF
- B. SMI（Service Mesh Interface）
- C. OpenAPI
- D. gRPC

<details>
<summary>显示答案</summary>

**答案：B**

**解释**：TrafficSplit 是一种 SMI 资源。Linkerd TrafficSplit/linkerd-smi 已弃用，且需要安装其扩展/CRD。维护中的指南使用受支持的 Gateway API HTTPRoutes 来创建新配置；仅应用旧版资源并不会安装该扩展。

</details>

### 4. ServiceProfile 中的 retryRatio:0.2 对重试预算有什么作用？

- A. 每个请求流中恰好有 20% 的请求必须重试
- B. 失败的请求中最多只能重试 20%
- C. 按原始请求数比例提供额度，此外 minRetriesPerSecond 也会提供额度
- D. 每 20 秒重置一次预算

<details>
<summary>显示答案</summary>

**答案：C**

**解释**：当 minRetriesPerSecond 也会增加额度时，按比例提供的额度并不构成严格的 20% 总上限。ttl 是回溯/保留时间窗口，而不是定期重置。是否符合重试条件、缓冲和截止时间仍会限制实际重试次数。

</details>

### 5. 仅凭以下哪项输入无法推断 ServiceProfile 所需的应用操作？

- A. OpenAPI 规范
- B. 通过 tap 观察到的实时流量
- C. protobuf 服务定义
- D. Kubernetes Service 选择器和端口列表

<details>
<summary>显示答案</summary>

**答案：D**

**解释**：CLI 支持根据 OpenAPI/protobuf 生成配置，Viz 支持基于 tap 生成配置。使用 -n 时应提供简短的 Service 名称；tap 命令还需要其位置参数 Service。请检查生成的匹配规则和重试安全性，因为采样到的流量并不包含完整的 API 清单。

</details>

### 6. 关于后端权重，哪项说法正确？

- A. 总和必须恰好为 100
- B. 总和必须恰好为 1
- C. 有效的非负相对权重必须有可用的正总和；90/10 和 9/1 表示相同的比例
- D. 负权重和零总和始终有效

<details>
<summary>显示答案</summary>

**答案：C**

**解释**：权重是相对值，同时受所选资源模式和后端有效性的约束。总和不必为 100，而且配置的比例并不能保证较短时间窗口内的请求数完全精确。新示例使用 HTTPRoute；TrafficSplit 是旧版 SMI 方案。

</details>

### 7. 哪项不是 HTTPRoute 的请求匹配字段？

- A. HTTP 标头
- B. HTTP 路径
- C. HTTP 方法
- D. 源 IP

<details>
<summary>显示答案</summary>

**答案：D**

**解释**：HTTPRoute 支持按标头/路径/方法匹配。精确匹配 Cookie 标头时，会比较整个标头值，而不是单个 Cookie 键值对。由调用方控制的 cohort/debug 标头不能用于授权。应使用适当的网络/安全策略限制源地址。

</details>

### 8. 指南中的自定义 Linkerd Flagger MetricTemplates 使用哪个指标提供程序？

- A. Kubernetes Metrics Server
- B. Prometheus
- C. 未声明的 InfluxDB Service
- D. 必需的 Datadog 后端

<details>
<summary>显示答案</summary>

**答案：B**

**解释**：这些模板会查询 Linkerd Viz Prometheus，并明确指定命名空间/Deployment/方向范围。Flagger 也支持其他提供程序。示例使用 gatewayapi:v1 路由和自定义指标名称；在 Flagger1.45.0 中，meshProvider:linkerd 仍会选择旧版 SMI 路由器。

</details>

### 9. 对匹配的 ServiceProfile 路由而言，isRetryable:false 表示什么？

- A. 所有匹配的请求都会失败
- B. ServiceProfile 机制不会重试该路由
- C. 所有超时策略都会被忽略
- D. 该路由已禁用

<details>
<summary>显示答案</summary>

**答案：B**

**解释**：请求仍可正常转发。此设置不会阻止客户端/SDK/其他代理进行重试。在当前的注解路径中，limit:0 在 edge-26.10.1 中并非可靠的禁用开关；请确保 Service 默认配置不启用重试，仅对预期的只读路由选择性启用重试。

</details>

### 10. 如何配置 Linkerd HTTP 熔断？

- A. 自动安装的 CircuitBreaker CRD
- B. 选择启用的 Service 故障累积注解
- C. 无条件默认采用连续五次连接失败规则
- D. 定期运行合成就绪探测循环

<details>
<summary>显示答案</summary>

**答案：B**

**解释**：故障累积默认处于禁用状态，且不能与该 Service 的 ServiceProfile 同时使用。连续失败策略默认值为七次受支持的响应失败。恢复试运行会在退避后发送真实的应用请求，而不是定期运行合成探测。

</details>

### 11. 客户端如何显式调用由多集群镜像 Service 表示的已导出 Service？

- A. 应用虚构的 TrafficMirror CRD
- B. 调用镜像 Service 的 DNS 名称，并确保满足所需的连通性和策略
- C. 所有本地请求都会自动复制
- D. 镜像 Service 永远无法被调用

<details>
<summary>显示答案</summary>

**答案：B**

**解释**：多集群 Service 镜像功能可发现并路由到远程 Service。调用其 DNS 名称会将请求发送到该 Service；这本身并不会为了影子测试而复制请求。请求镜像是另一项独立功能，必须确认所选实现/版本是否支持。

</details>

### 12. ServiceProfile 路由中省略 timeout 表示什么？

- A. 自动设置五秒的 profile 超时
- B. 该 ServiceProfile 字段不设置超时
- C. 立即失败
- D. 移除其他层级的所有超时

<details>
<summary>显示答案</summary>

**答案：B**

**解释**：该字段不会为路由添加超时，但应用、客户端、传输、代理和负载均衡器的限制仍可能生效。这并不意味着端到端请求没有时限。流式传输的截止时间和取消需要根据应用情况进行明确设计。

</details>
