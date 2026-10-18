# Linkerd 可观测性测验

本测验基于[可观测性指南](../../../service-mesh/linkerd/05-observability.md)，审阅日期：2026 年 9 月 11 日。

### 1. 以下哪项不是 Linkerd 的三项核心 HTTP 服务指标之一？

- A. 成功率
- B. 请求率
- C. 延迟
- D. CPU 利用率

<details>
<summary>显示答案</summary>

**答案：D**

**说明：**
三项指标分别是由代理分类的成功率、请求率和延迟。CPU 或容量属于额外的运维信息；这并不表示代理或其他采集器不能提供进程或资源指标。对于不透明的 TCP 流量，系统也不会自动提供 HTTP 服务指标。

</details>

### 2. 以下哪项不是此版本 linkerd viz stat 表中的标准列？

- A. SUCCESS
- B. RPS
- C. LATENCY_P99
- D. ERROR_TYPE

<details>
<summary>显示答案</summary>

**答案：D**

**说明：**
所选版本包含 MESHED、SUCCESS、RPS、各百分位延迟以及 TCP_CONN。宽格式输出还会包含传输字节速率，而不是代理版本清单。排查错误时，应结合适用的策略、Tap、日志和指标。

</details>

### 3. linkerd viz tap 提供什么？

- A. 完整的网络数据包捕获
- B. 对受支持请求的实时观测流
- C. 自动修改代理策略
- D. 证书续期

<details>
<summary>显示答案</summary>

**答案：B**

**说明：**
Tap 只能观测受支持的流量，并且会进行采样；它不是完整审计记录。max-rps 限制被 Tap 观测的速率，不会限制所有应用流量。当前版本的 Tap 没有 --from 或 --show-headers 标志；应使用受支持的 selector，并保护请求元数据的访问权限。

</details>

### 4. 旧版 ServiceProfile 中的路由命名有什么作用？

- A. 统计磁盘 I/O
- B. 提供逐路由指标
- C. 自动生成完整的分布式追踪
- D. 对每种方法强制启用重试

<details>
<summary>显示答案</summary>

**答案：B**

**说明：**
ServiceProfile 支持路由指标以及 viz routes 视图。它仍是兼容性接口，可能优先于当前出站 HTTPRoute 的可靠性设置。为获得可观测性而添加 profile 时，不应悄然启用不安全的重试或覆盖现有策略。

</details>

### 5. 指南如何在本机访问现有的默认 Viz Prometheus？

- A. 暴露未经身份验证的 NodePort
- B. 创建公共 LoadBalancer
- C. 使用绑定到 loopback 地址的 kubectl port-forward
- D. 假定存在公共 URL

<details>
<summary>显示答案</summary>

**答案：C**

**说明：**
示例会将现有 Prometheus Service 转发到 127.0.0.1。它既不会安装 Prometheus，也不会配置公共身份验证。其他工作负载若要访问，还需配置适用的网络规则和 Linkerd 授权设置。

</details>

### 6. 应用示例所用的 W3C trace context 包含哪一对字段？

- A. x-request-id 和 Authorization
- B. x-b3-traceid 和 x-b3-spanid
- C. traceparent 和 tracestate
- D. x-linkerd-proxy 和 Cookie

<details>
<summary>显示答案</summary>

**答案：C**

**说明：**
Linkerd 支持 W3C 和 B3；两者同时存在时优先使用 W3C。x-request-id 是关联请求的 ID，并不是必需的追踪格式。仅传播这些 header 不会创建应用 span，也不会配置采样或导出；这些工作需要合适的追踪库。

</details>

### 7. linkerd viz top 汇总什么？

- A. 按 CPU 使用量排序的 Pod
- B. Tap 捕获的实时请求路径或路由
- C. 所有历史错误消息
- D. 最新的容器日志

<details>
<summary>显示答案</summary>

**答案：B**

**说明：**
top 汇总实时流量，并受采样、速率限制和受支持过滤条件的约束。hide-sources 控制是否显示来源列，不控制 header。此视图不能替代保留在 Prometheus 中的指标或完整请求审计记录。

</details>

### 8. 哪个 annotation 会更改代理诊断日志级别？

- A. config.linkerd.io/log-level
- B. config.linkerd.io/proxy-log-level
- C. linkerd.io/proxy-log
- D. proxy.linkerd.io/log-level

<details>
<summary>显示答案</summary>

**答案：B**

**说明：**
proxy-log-level 控制诊断日志过滤器，proxy-log-format 控制诊断日志格式。HTTP 访问日志通过 config.linkerd.io/access-log:json 或 apache 单独启用。局部 Pod 模板只是补丁或片段，并不是完整的 Deployment。

</details>

### 9. 如何计算一个时间窗口内的成功率？

- A. 不使用 rate，直接将生命周期累计成功数除以总数
- B. 使用并不存在的 success_total 计数器
- C. 在范围一致、正确处理缺失成功序列且总响应速率为正的前提下，用成功响应速率除以总响应速率
- D. 对并不存在的 success_rate 指标求平均值

<details>
<summary>显示答案</summary>

**答案：C**

**说明：**
应选定一种观测方向，以及明确的工作负载和集群范围。若窗口内全部请求失败而没有成功序列，结果仍应为 0；缺失或空闲数据不能被误算为 100% 成功。代理的 HTTP 分类可能将 400 计为成功，因此应根据业务 SLI 有意选择分类方式。

</details>

### 10. 在当前追踪配置中，Jaeger 可以承担什么角色？

- A. 替代 Kubernetes 指标发现
- B. 只聚合应用访问日志
- C. 作为单独管理的后端收集、存储和查询分布式追踪
- D. 自动拆分流量

<details>
<summary>显示答案</summary>

**答案：C**

**说明：**
Linkerd-Jaeger 扩展已在 2.19 中移除。当前 Linkerd 配置兼容 OpenTelemetry 的采集器；在示例所示的 chart 配置路径中，还会配置其 mesh identity。只有后端 UI 并不能证明应用或代理 span 已送达，也不能证明追踪完整。

</details>

### 11. 哪类信息应通过 kubectl logs 或日志系统获取，而不能假设 Viz 是容器日志查看器？

- A. 工作负载拓扑
- B. Deployment 指标
- C. Pod 容器日志
- D. ServiceProfile 路由指标

<details>
<summary>显示答案</summary>

**答案：C**

**说明：**
Viz 提供工作负载和流量视图、拓扑以及 Tap。诊断日志和访问日志属于不同的数据。查看这些视图的流程仍须确定原因、实施修复并验证结果；它不会自动解决事件。

</details>

### 12. 哪项设置可将 Viz 链接到现有且浏览器可访问的外部 Grafana？

- A. grafana.external:true
- B. grafana.externalUrl:https://grafana.example.com/
- C. grafana.enabled:false
- D. monitoring:external

<details>
<summary>显示答案</summary>

**答案：B**

**说明：**
当前 Viz 不会安装 Grafana。externalUrl 提供外部链接；grafana.url 是集群内反向代理选项，还需要配置根路径或子路径。这两项设置都不会创建 Grafana、配置其数据源或授予它访问 Prometheus 的权限。

</details>
