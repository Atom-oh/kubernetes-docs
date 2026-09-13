# Datadog 测验

> **最后更新**: September 13, 2026

1. 使用 Datadog SaaS 后，团队仍需负责什么？

   - A) 安装 Agent 后无需负责任何事
   - B) 仅选择仪表板颜色
   - C) 收集器、身份、埋点、数据处理、监控器和成本
   - D) Datadog 的物理数据库服务器

<details>
<summary>显示答案</summary>

**答案: C**

SaaS 管理后端。APM、性能分析、日志和其他产品具有各自的授权与计费方式；一个 Agent 并不包含所有功能。

</details>

2. 关于凭证/集成，哪项陈述是正确的？

   - A) 基础 Agent 数据采集需要 API key；application key 和 AWS account role 用于其他特定功能
   - B) 每个 Agent 都需要 application key 和宽泛的 AWS 读取 role
   - C) 添加 IRSA 会自动配置 Datadog SaaS AWS 集成
   - D) 推测出的 service-account 名称已足够

<details>
<summary>显示答案</summary>

**答案: A**

外部指标提供程序需要额外的 API 权限/key 配置。SaaS AWS 集成使用已授权的跨账户 role/external ID。请解析实际渲染出的 Agent SA。

</details>

3. 仅凭 admission.datadoghq.com/enabled=true 能证明 APM SDK 注入吗？

   - A) 是的，会自动包含每种语言/版本
   - B) 否；请配置 SDK annotations 或 SSI targets，然后验证新准入的 Pods 和实际 trace 数据
   - C) 是的，即使在 Cluster Agent namespace 中也是如此
   - D) 是的，只要存在 trace socket

<details>
<summary>显示答案</summary>

**答案: B**

变更/连接设置与 library 注入是不同的。当前本地注入不包括 kube-system 和 Cluster Agent namespace。仍需考虑 library、runtime、挂载和安全兼容性。

</details>

4. 应用程序 Pod 应如何访问节点上的 DogStatsD Agent？

   - A) 始终使用应用程序的 localhost
   - B) 在每个 UDP packet 中放入 API key
   - C) 创建一个无关的 ConfigMap
   - D) 使用配置的可达端点，例如挂载的 Linux UDS directory

<details>
<summary>显示答案</summary>

**答案: D**

应用程序的 localhost 不是节点 Agent。UDS paths、权限和 SDK 参数格式必须匹配。Datagram 不会确认 SaaS 数据采集；counter 也不是恰好一次的账本。

</details>

5. 哪项指标解读是正确的？

   - A) kubernetes.cpu.usage.total 是百分比
   - B) 所有缺失的旧目录指标都已被移除
   - C) kubernetes.cpu.usage.total 是 nanocores；Kubelet restart metrics 是累积 gauge
   - D) 对重复的 restart samples 求和可以计算新增 restart 次数

<details>
<summary>显示答案</summary>

**答案: C**

system.cpu.idle 是百分比。Kubelet 和 State Core 有不同的有效 metric names 和 tags。示例 restart monitor 会明确评估 total；近期增量需要进行可感知重置的验证。

</details>

6. .as_count() error-ratio 路径计算的是什么？

   - A) 经时间聚合的 error count 与 total count 之比
   - B) 每个 time bucket ratio 的总和
   - C) 全局 p95
   - D) 流量为零时自动 100% 成功

<details>
<summary>显示答案</summary>

**答案: A**

使用 sum aggregation 和匹配的 groups。该 helper 会显式输出零 good/error counts。零流量、缺失数据和无错误流量仍是不同的状态。

</details>

7. 关于 OpenMetrics/log 配置，哪项陈述是正确的？

   - A) 任何 ConfigMap 都会自动挂载
   - B) 使用匹配的 container annotations/current check fields；Logs Grok 规则使用 match_rules/support_rules
   - C) chart root 的 prometheus.enabled 会配置所有内容
   - D) Grok 的 camelCase keys 和 snake_case keys 是等效的

<details>
<summary>显示答案</summary>

**答案: B**

当前 OpenMetrics check 使用 openmetrics_endpoint。datadog.confd 提供 chart 所有的挂载；独立的 ConfigMaps 不会自行安装。请求 schema 验证并不等同于实时 scrape 或 Grok parse。

</details>

8. 手动 trace-log 关联应保留什么？

   - A) 仅保留 dd.trace_id，删除所有其他 MDC fields
   - B) 对 128-bit ID 进行任意 numeric cast
   - C) 硬编码一个成功的 trace ID
   - D) 调用方先前的 MDC context、string IDs，以及实际的 instrumentation/data 前提条件

<details>
<summary>显示答案</summary>

**答案: D**

即使 application code 抛出异常，该 helper 也会恢复 context。它是同步的。自动注入/解析、一致的 service tags 和可用的 traces 是独立的要求。

</details>

9. 将 50 个 services 按 50 个 APM hosts 计价有什么问题？

   - A) APM 始终免费
   - B) 日志数据采集就是全部日志账单
   - C) Services 和可计费 hosts 是不同单位；必须计算产品/合同配额和用量
   - D) 每个 cluster 都有一个 host

<details>
<summary>显示答案</summary>

**答案: C**

旧估算并非经过测量的账单。索引/保留、span 配额、custom metrics 和其他产品都很重要。nonLocalTraffic 是可达性，而非成本配额。

</details>

10. 哪项 Watchdog/SLO/diagnostic 实践是正确的？

   - A) 一条 Watchdog insight 可以证明已送达 page
   - B) 匹配 SLO model 和 good/total policy，测试路由，并在共享前检查本地 diagnostic bundles
   - C) 本地 flare 会自动授权上传
   - D) traces 缺失时导出每个 DD_ environment value

<details>
<summary>显示答案</summary>

**答案: B**

Datadog 支持 metric-、monitor- 和 time-slice SLOs。通知和 no-data 行为需要验证。env dumps 可能暴露 keys；--local 会将初始 flare 收集保留在本地。

</details>

---

[返回指南](../../../observability/metrics/05-datadog.md)
