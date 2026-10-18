# AWS X-Ray 测验

> **最后更新**：2026 年 9 月 13 日

[AWS X-Ray](../../../observability/tracing/02-xray.md)

---

1. 以下哪项行为不是 X-Ray 追踪管道自动提供的？
   - A) 基于收集到的追踪数据生成服务依赖关系可视化
   - B) 分布式请求追踪
   - C) 收集每个应用程序的普通日志文件
   - D) 分析收集到的跨度（span）耗时

<details>
<summary>显示答案</summary>

**答案：C) 收集每个应用程序的普通日志文件**

**说明：**

追踪不会配置通用的应用程序日志收集器。CloudWatch Transaction Search 可以将结构化跨度（span）存储在 aws/spans 中，但这不同于收集所有普通应用程序日志。指标和日志需要分别配置管道和访问控制。

</details>

---

2. 对于旧版守护进程路径，哪种 Kubernetes 工作负载可以在每个符合条件的 EC2 工作节点上运行一个守护进程？
   - A) Deployment
   - B) StatefulSet
   - C) DaemonSet
   - D) Job

<details>
<summary>显示答案</summary>

**答案：C) DaemonSet**

**说明：**

DaemonSet 会选择符合条件的节点；EKS Fargate 不支持它。ClusterIP Service 可能会选择另一个节点上的守护进程，因此仅靠 DaemonSet 的部署位置，不能保证 UDP 数据在节点本地传递或不会丢失。X-Ray SDK/守护进程处于维护模式；本指南为新的埋点使用单独的 OpenTelemetry 收集器 Deployment。

</details>

---

3. 以下哪项不是 X-Ray 集中式采样规则的字段？
   - A) FixedRate
   - B) ReservoirSize
   - C) Priority
   - D) RetentionDays

<details>
<summary>显示答案</summary>

**答案：D) RetentionDays**

**说明：**

FixedRate、ReservoirSize 和 Priority 是采样字段。RetentionDays 不是采样规则参数。没有流量时，采样储备量（reservoir）并不能保证最低追踪数量。规则需要兼容的远程采样器；头部采样无法选择尚未发生的响应错误。

</details>

---

4. 以下哪种说法正确区分了 X-Ray 注解（annotations）和元数据（metadata）？
   - A) 每个片段（segment）都会独立接收 100 个已建立索引的注解
   - B) 注解会建立索引以供 X-Ray 筛选；未建立索引的元数据仍会存储且可访问
   - C) 注解仅接受字符串
   - D) 元数据会自动脱敏

<details>
<summary>显示答案</summary>

**答案：B) 注解会建立索引以供 X-Ray 筛选；未建立索引的元数据仍会存储且可访问**

**说明：**

X-Ray 每条追踪最多为 50 个注解建立索引。元数据不会像注解一样建立索引，但未建立索引并不意味着它是机密的或不可访问的。请使用经过审慎限定的字段，并在收集前移除敏感载荷、标识符、令牌和 SQL 参数。index_all_attributes=false 不是脱敏处理器。

</details>

---

5. 关于 ADOT Collector，哪种说法是错误的？
   - A) 它接受受支持的 OpenTelemetry 协议
   - B) 它可以将受支持的管道连接到多个后端
   - C) 声明一个未使用的 CloudWatch Logs 导出器会自动将追踪转换为日志
   - D) 必须检查其发布版本的组件清单

<details>
<summary>显示答案</summary>

**答案：C) 声明一个未使用的 CloudWatch Logs 导出器会自动将追踪转换为日志**

**说明：**

接收器、处理器和导出器必须连接到相应的日志/指标/追踪管道。ADOT 包含 awsxray 等 AWS 集成组件，因此 AWS 特定行为并非旧版守护进程独有。不要假设每个上游 Contrib 导出器都存在于所选的 ADOT 发布版本中。

</details>

---

6. X-Ray/CloudWatch 追踪地图中的红色流量类别代表什么？
   - A) 每个缓慢请求
   - B) 高流量
   - C) HTTP 5xx 等服务器故障
   - D) 新发现的服务

<details>
<summary>显示答案</summary>

**答案：C) HTTP 5xx 等服务器故障**

**说明：**

红色代表服务器故障，黄色代表客户端错误，紫色代表 HTTP 429 等限流，绿色代表成功流量。这些类别不是任意的延迟阈值，也不意味着每个红色服务都已触发用户定义的高错误率告警条件。

</details>

---

7. 通过本指南的 X-Ray 收集路径发送 OpenTelemetry 跨度（span）需要什么？
   - A) 每个数据生成方都必须使用旧版 X-Ray SDK
   - B) 使用正确 AWS 身份、兼容且经过身份验证的 OTLP 收集/导出管道
   - C) 每个应用程序都必须安装 CloudWatch Agent
   - D) 每个 EKS Pod 都必须安装 Lambda Layer

<details>
<summary>显示答案</summary>

**答案：B) 使用正确 AWS 身份、兼容且经过身份验证的 OTLP 收集/导出管道**

**说明：**

本指南通过 mTLS 向 ADOT 发送 OTLP，其 awsxray 导出器调用经过签名的经典 X-Ray API。X-Ray 支持 W3C 128 位 ID；专用的 X-Ray ID 生成器/传播器并非普遍强制要求。作为替代方案的原生 OTLP HTTPS 端点需要 SigV4 和 Transaction Search。请根据实际集成配置追踪上下文传播。

</details>

---

8. 以下哪个 X-Ray 响应时间筛选条件会选择严格大于两秒的值？
   - A) `responsetime > 2000`
   - B) `responsetime > 2`
   - C) `responsetime >= 2`
   - D) `time > 2s`

<details>
<summary>显示答案</summary>

**答案：B) `responsetime > 2`**

**说明：**

响应时间以秒为单位。>2 不包括恰好为 2 秒的值；>=2 包括它。这些是 X-Ray 筛选表达式，不是 shell 命令或 Logs Insights QL。duration 也是文档中说明的 X-Ray 关键字，不能将其描述为虚构的无效关键字。

</details>

---

9. 仅仅打开 CloudWatch 追踪地图无法证明什么？
   - A) 显示已收集追踪的依赖关系
   - B) 与已配置指标/告警的关联
   - C) 每个应用程序都已自动埋点并成功收集数据
   - D) 指向适当关联日志的链接

<details>
<summary>显示答案</summary>

**答案：C) 每个应用程序都已自动埋点并成功收集数据**

**说明：**

埋点、收集、身份和关联必须分别配置。原来的 ServiceLens 和 X-Ray 地图已合并到 CloudWatch 追踪地图中。现有遥测数据可以在那里关联，但未挂载的 ConfigMap 或空视图不能证明代理和应用程序已完成配置。

</details>

---

10. X-Ray Groups 的用途是什么？
   - A) 替代 IAM 授权
   - B) 对匹配的追踪分组，用于分析及相关指标/告警
   - C) 自动分配 AWS 账单归属
   - D) 通过采样规则设置保留期限

<details>
<summary>显示答案</summary>

**答案：B) 对匹配的追踪分组，用于分析及相关指标/告警**

**说明：**

Groups 使用筛选表达式选择追踪。请审查生成的指标，并分别配置 CloudWatch 告警。创建分组不会为数据生成方添加埋点、覆盖采样、定义 IAM 隔离，或证明端到端告警已触发。

</details>

---
