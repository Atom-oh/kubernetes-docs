# 可观测性实验第 5 部分：告警和 AIOps 测验

> **最后更新**: February 22, 2026

测试您对可观测性端到端实验第 5 部分所涵盖的告警和 AIOps 概念的理解。

---

1. Alertmanager PrometheusRule 中的 `for` 字段指定什么？
   - A) 告警评估之间的时间间隔
   - B) 告警触发前条件必须持续为真的时长，使告警从 pending 状态转换为 firing 状态
   - C) 条件解除后告警保持活动状态的时长
   - D) 自动解决前告警的最长生命周期

<details>
<summary>显示答案</summary>

**答案：B) 告警触发前条件必须持续为真的时长，使告警从 pending 状态转换为 firing 状态**

**说明：**
`for` 字段为告警触发设置时长阈值。当告警条件变为真时，告警进入“pending”状态。只有当条件在整个 `for` 时长内持续为真时，告警才会转换为“firing”并触发通知。这可以避免因短暂的瞬态峰值而发出告警。例如，`for: 5m` 表示条件必须连续 5 分钟为真才会告警，从而减少瞬时波动带来的噪声。

</details>

---

2. Alertmanager 的路由树如何确定由哪个 receiver 处理告警？
   - A) 告警会随机分配给各个 receiver
   - B) 路由按从上到下的顺序进行评估；告警根据 labels 匹配，并发送到第一个匹配路由的 receiver；子路由可用于更具体的匹配
   - C) 所有 receiver 会同时收到所有告警
   - D) 路由根据告警严重性评分进行选择

<details>
<summary>显示答案</summary>

**答案：B) 路由按从上到下的顺序进行评估；告警根据 labels 匹配，并发送到第一个匹配路由的 receiver；子路由可用于更具体的匹配**

**说明：**
Alertmanager 的路由树采用分层结构。根路由捕获所有告警，然后子路由在告警 labels 上使用 `match` 或 `match_re` 进行筛选。路由可以具有嵌套的子路由，以实现逐渐更具体的匹配。默认情况下，告警匹配其满足的第一个路由，但 `continue: true` 允许匹配多个路由。这支持复杂的路由：将关键告警发送至 PagerDuty，将警告发送至 Slack，将特定团队的告警发送至不同渠道，所有操作均基于 `severity`、`team` 或 `service` 等 labels。

</details>

---

3. Grafana OnCall Escalation Chain 如何工作？
   - A) 它会随机选择一名团队成员进行通知
   - B) 它定义带有等待时间的一系列通知步骤，通过不同用户或组逐级升级，直到有人确认告警
   - C) 它只发送电子邮件通知
   - D) 升级链仅用于日历管理

<details>
<summary>显示答案</summary>

**答案：B) 它定义带有等待时间的一系列通知步骤，通过不同用户或组逐级升级，直到有人确认告警**

**说明：**
Grafana OnCall Escalation Chains 定义事件响应工作流：第 1 步可能通过 Slack 和电话通知值班工程师，等待 5 分钟；随后第 2 步升级至后备工程师，等待 10 分钟；然后第 3 步呼叫团队负责人。每个步骤可以使用不同的通知渠道（Slack、SMS、电话、电子邮件），并面向不同的用户或值班计划。有人确认后，链会停止，在确保覆盖的同时防止告警疲劳。

</details>

---

4. CloudWatch Alarms 中的评估周期和数据点设置控制什么？
   - A) 它们控制告警名称和描述
   - B) 评估周期设置检查指标的频率；datapoints-to-alarm 指定必须有多少个周期超过阈值才触发告警
   - C) 它们只影响仪表板中的告警可视化
   - D) 这些设置已弃用，改用指标数学

<details>
<summary>显示答案</summary>

**答案：B) 评估周期设置检查指标的频率；datapoints-to-alarm 指定必须有多少个周期超过阈值才触发告警**

**说明：**
CloudWatch Alarms 使用两项关键设置：Period（评估周期）定义指标聚合的时间粒度（例如 1 分钟、5 分钟），“Datapoints to Alarm”指定最近 N 个周期中必须有多少个超过阈值。例如，使用 1 分钟周期时，“5 个中有 3 个”表示如果最近 5 分钟中有 3 分钟超过阈值，则会触发告警。该组合可在响应速度和降噪之间进行调优。

</details>

---

5. CloudWatch Investigations 如何执行基于 AI 的根本原因分析？
   - A) 它只提供静态 runbook
   - B) 它使用 ML 模型分析相关联的指标、日志和追踪，以识别异常并提出具有支持证据的潜在根本原因
   - C) 每个事件都需要手动触发调查
   - D) 它只适用于 EC2 实例

<details>
<summary>显示答案</summary>

**答案：B) 它使用 ML 模型分析相关联的指标、日志和追踪，以识别异常并提出具有支持证据的潜在根本原因**

**说明：**
CloudWatch Investigations（Amazon CloudWatch Application Signals 的一部分）使用机器学习自动调查问题。当由告警或手动操作触发时，它会关联指标、日志和追踪中的遥测信号，以识别与事件同时发生的异常。它会分析相关资源、检测模式，并通过置信度评分和证据链接呈现发现。这通过呈现人工手动调查时可能遗漏的相关数据，加快平均诊断时间。

</details>

---

6. 基于 Lambda 的 AIOps Agent 通常以什么顺序收集用于事件分析的遥测数据？
   - A) 先收集日志，然后依次收集指标和追踪
   - B) 并行收集指标、日志和追踪遥测数据，以最小化总收集时间
   - C) 只收集追踪；忽略指标和日志
   - D) 收集顺序是随机且不可预测的

<details>
<summary>显示答案</summary>

**答案：B) 并行收集指标、日志和追踪遥测数据，以最小化总收集时间**

**说明：**
有效的 AIOps agent 会并行收集遥测数据以最小化延迟。当事件触发 Lambda function 时，它会并发查询：Prometheus/AMP 中的指标（错误率、延迟）、Loki/CloudWatch 中的相关日志（错误消息、堆栈追踪），以及 Tempo/X-Ray 中的分布式追踪（请求流、瓶颈）。并行收集可确保 agent 快速获得全面上下文，从而实现更快的 AI 分析和响应。这使用 async/await 模式或并发 API 调用实现。

</details>

---

7. 将 Bedrock Claude 用作 SRE 专家时，设计 system prompt 的关键原则是什么？
   - A) 使 prompt 尽可能简短
   - B) 清晰定义角色，提供系统架构上下文，指定输出格式，并包含有关常见故障模式的领域特定知识
   - C) system prompt 应仅包含通用指令
   - D) 避免在 prompt 中提及具体技术

<details>
<summary>显示答案</summary>

**答案：B) 清晰定义角色，提供系统架构上下文，指定输出格式，并包含有关常见故障模式的领域特定知识**

**说明：**
有效的 SRE system prompt 包括：清晰的角色定义（“您是一名分析 Kubernetes 事件的 SRE 专家”）、系统上下文（架构、技术栈、典型问题）、结构化输出格式（假设、证据、建议操作、runbook 链接）和领域知识（常见故障模式、升级标准、Service 依赖关系）。加入过往事件和解决方案示例可提高响应质量。prompt 应引导模型提供可执行的具体建议，而非通用建议。

</details>

---

8. Alertmanager webhook 如何连接 API Gateway 和 Lambda 以实现自动化事件响应？
   - A) Lambda 通过 SDK 直接接收 Alertmanager 告警
   - B) Alertmanager 向 API Gateway HTTP endpoint 发送 POST 请求，后者使用告警 payload 触发 Lambda function 进行处理
   - C) API Gateway 轮询 Alertmanager 以获取新告警
   - D) 该连接需要专用 EC2 实例作为代理

<details>
<summary>显示答案</summary>

**答案：B) Alertmanager 向 API Gateway HTTP endpoint 发送 POST 请求，后者使用告警 payload 触发 Lambda function 进行处理**

**说明：**
集成流程如下：将 Alertmanager 的 webhook receiver 配置为使用 API Gateway endpoint URL。告警触发时，Alertmanager 会向此 endpoint POST 包含告警详细信息（labels、annotations、status、timestamps）的 JSON payload。API Gateway 接收请求并触发已集成的 Lambda function，将告警 payload 作为 event 传递。Lambda function 处理告警——通过上下文丰富、运行 AI 分析、触发修复操作，或转发至事件管理系统。

</details>

---

9. 如何使用 Fault Injection 触发 HighLatency 告警，以测试告警管道？
   - A) 在 Alertmanager 中手动编辑告警状态
   - B) 使用 Chaos Mesh、Litmus 或应用程序级故障注入等工具，在服务响应中注入人工延迟，使延迟指标超过告警阈值
   - C) 直接修改 Prometheus 指标值
   - D) 故障注入无法触发 Prometheus 告警

<details>
<summary>显示答案</summary>

**答案：B) 使用 Chaos Mesh、Litmus 或应用程序级故障注入等工具，在服务响应中注入人工延迟，使延迟指标超过告警阈值**

**说明：**
故障注入可端到端验证告警管道。Chaos Mesh 或 Litmus 等工具可以在 Pod 或 Service 层面注入网络延迟。应用程序级注入可在处理程序中添加 sleep 延迟。当注入的延迟导致指标（例如 `histogram_quantile(0.99, http_request_duration_seconds_bucket)`）超过 PrometheusRules 中定义的阈值时，告警会自然地通过管道触发。这可测试指标收集、告警规则、Alertmanager 路由和通知传递是否均正常工作。

</details>

---

10. 在用于 AIOps 的 A2A（Agent-to-Agent）模式中，Collaborator Agent 扮演什么角色？
    - A) 它完全取代人工操作员
    - B) 它充当专业 agent，主 agent 可将子任务委托给它，例如查询特定数据源、执行修复操作或提供领域专业知识
    - C) 它只处理日志记录和监控
    - D) Collaborator agents 是主 agent 的相同副本

<details>
<summary>显示答案</summary>

**答案：B) 它充当专业 agent，主 agent 可将子任务委托给它，例如查询特定数据源、执行修复操作或提供领域专业知识**

**说明：**
在 A2A 模式中，主 agent（orchestrator）与专业的 collaborator agents 协作。对于 AIOps：Metrics Agent 查询 Prometheus/CloudWatch，Logs Agent 搜索和分析日志数据，Traces Agent 调查分布式追踪，Remediation Agent 执行安全恢复操作，Knowledge Agent 检索 runbook 和过去的事件数据。主 agent 将 collaborator 的输出整合为连贯的事件分析。这种划分实现了专业化 prompt、并行执行和关注点分离，从而提升整体系统能力。

</details>
