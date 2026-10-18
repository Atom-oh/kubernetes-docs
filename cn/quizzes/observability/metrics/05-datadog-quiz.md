# Datadog 测验

> **最后更新**: 2026 年 9 月 13 日

1. 使用 Datadog SaaS 后，团队仍需负责什么？

   - A) 安装 Agent 后无需负责任何事
   - B) 仅选择仪表板颜色
   - C) 采集器、身份、埋点、数据处理、监控器和成本
   - D) Datadog 的物理数据库服务器

<details>
<summary>显示答案</summary>

**答案: C**

SaaS 管理后端。APM、性能分析、日志和其他产品具有各自的授权与计费方式；一个 Agent 并不包含所有功能。

</details>

2. 关于凭证/集成，哪项陈述是正确的？

   - A) Agent 的基础数据摄取需要 API 密钥；应用程序密钥和 AWS 账户角色用于其他特定功能
   - B) 每个 Agent 都需要应用程序密钥和具备广泛 AWS 读取权限的角色
   - C) 添加 IRSA 会自动配置 Datadog SaaS AWS 集成
   - D) 猜测出的 ServiceAccount 名称就足够

<details>
<summary>显示答案</summary>

**答案: A**

外部指标提供程序需要额外的 API 权限和密钥配置。SaaS 的 AWS 集成使用获授权的跨账户角色和外部 ID。请确认实际渲染出的 Agent ServiceAccount。

</details>

3. 仅凭 admission.datadoghq.com/enabled=true 能证明 APM SDK 注入吗？

   - A) 是的，会自动包含每种语言/版本
   - B) 否；请配置 SDK 注解或 SSI 目标，然后验证新准入的 Pod 和实际追踪数据
   - C) 是的，即使在 Cluster Agent 命名空间中也是如此
   - D) 是的，只要存在追踪套接字

<details>
<summary>显示答案</summary>

**答案: B**

准入修改/连接设置与库注入是不同的。当前本地注入不包括 kube-system 和 Cluster Agent 命名空间。仍需考虑库、运行时、挂载和安全兼容性。

</details>

4. 应用程序 Pod 应如何访问节点上的 DogStatsD Agent？

   - A) 始终使用应用程序的 localhost
   - B) 在每个 UDP 数据包中放入 API 密钥
   - C) 创建一个无关的 ConfigMap
   - D) 使用配置的可达端点，例如挂载的 Linux UDS 目录

<details>
<summary>显示答案</summary>

**答案: D**

应用程序的 localhost 不是节点 Agent。UDS 路径、权限和 SDK 参数格式必须匹配。数据报不会确认 SaaS 已摄取数据；计数器也不是保证恰好一次的账本。

</details>

5. 哪项指标解读是正确的？

   - A) kubernetes.cpu.usage.total 是百分比
   - B) 所有缺失的旧目录指标都已被移除
   - C) kubernetes.cpu.usage.total 的单位是纳核（nanocores）；Kubelet 重启指标是累积量度值（gauge）
   - D) 对重复的重启样本求和可以算出新增重启次数

<details>
<summary>显示答案</summary>

**答案: C**

system.cpu.idle 的单位是百分比。Kubelet 和 State Core 的有效指标名称和标签不同。示例重启监控器明确评估的是总量；判断近期增量需要进行考虑计数重置的验证。

</details>

6. .as_count() 错误率计算路径得到什么结果？

   - A) 经时间聚合的错误计数与总计数之比
   - B) 各时间分桶中比率的总和
   - C) 全局 p95
   - D) 流量为零时自动 100% 成功

<details>
<summary>显示答案</summary>

**答案: A**

使用求和聚合以及相匹配的分组。该辅助程序会显式输出为零的成功/错误计数。零流量、缺失数据和无错误流量仍是不同状态。

</details>

7. 关于 OpenMetrics/日志配置，哪项陈述是正确的？

   - A) 任何 ConfigMap 都会自动挂载
   - B) 使用匹配的容器注解和当前检查字段；日志 Grok 规则使用 match_rules/support_rules
   - C) chart 根级别的 prometheus.enabled 会配置所有内容
   - D) Grok 的驼峰式键名和下划线分隔的键名是等效的

<details>
<summary>显示答案</summary>

**答案: B**

当前 OpenMetrics 检查使用 openmetrics_endpoint。datadog.confd 提供由 chart 管理的挂载；独立的 ConfigMap 不会自行安装。请求数据模式验证并不等同于实际抓取或 Grok 解析。

</details>

8. 手动关联追踪与日志时，应保留什么？

   - A) 仅保留 dd.trace_id，删除所有其他 MDC 字段
   - B) 对 128 位 ID 进行任意数值类型转换
   - C) 硬编码一个成功的追踪 ID
   - D) 调用方先前的 MDC 上下文、字符串 ID，以及实际的埋点/数据前提条件

<details>
<summary>显示答案</summary>

**答案: D**

即使应用程序代码抛出异常，该辅助程序也会恢复上下文。它是同步的。自动注入/解析、一致的服务标签和可用的追踪数据是独立的要求。

</details>

9. 将 50 个服务按 50 台 APM 主机计价有什么问题？

   - A) APM 始终免费
   - B) 日志数据采集就是全部日志账单
   - C) 服务和可计费主机是不同的计量单位；必须计入产品/合同配额和用量
   - D) 每个集群都只有一台主机

<details>
<summary>显示答案</summary>

**答案: C**

旧估算并非基于实际测量的账单。索引/保留、追踪片段（span）配额、自定义指标和其他产品都会影响成本。nonLocalTraffic 控制的是可达性，而非成本配额。

</details>

10. 关于 Watchdog/SLO/诊断，哪项做法正确？

   - A) 一条 Watchdog 洞察可以证明告警通知已送达
   - B) 匹配 SLO 模型和成功/总量统计策略，测试路由，并在共享前检查本地诊断包
   - C) 本地 flare 诊断包会自动授权上传
   - D) 追踪数据缺失时导出所有 DD_ 环境变量值

<details>
<summary>显示答案</summary>

**答案: B**

Datadog 支持基于指标、监控器和时间切片的 SLO。通知和无数据时的行为需要验证。导出环境变量可能会暴露密钥；--local 会让初次 flare 诊断收集保留在本地。

</details>

---

[返回指南](../../../observability/metrics/05-datadog.md)
