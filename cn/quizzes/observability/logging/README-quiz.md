# 日志概览测验

> **最后更新**: September 13, 2026

1. 关于结构化 JSON 日志，哪项说法正确？

   - A) 它们不需要解析
   - B) 它们始终占用更少字节
   - C) 明确的字段有助于分析，但解码、分帧和字段映射仍然很重要
   - D) 它们会自动脱敏所有敏感数据

<details>
<summary>显示答案</summary>

**答案: C**

使用经过测试的事件 schema，并且通常每行使用一个编码后的事件。JSON 可能比纯文本更大，并且原始副本和解析后的副本都需要数据处理政策。

</details>

2. TRACE 到 FATAL 是否在所有情况下都统一编号为 0 到 5？

   - A) 否；不同 framework 有所不同，OpenTelemetry 使用 1–24 的 severity 范围，而 0 未指定
   - B) 是，在每种语言中都是如此
   - C) 是，仅在 Kubernetes 中如此
   - D) FATAL 始终为 0

<details>
<summary>显示答案</summary>

**答案: A**

应映射 severity 的含义，而不是照搬虚构的数字标度。仅凭日志级别无法决定可恢复性，并且将所有生产日志提高到 WARN 可能会丢失证据。

</details>

3. 常见的默认 Linux 容器日志布局是什么？

   - A) 实际文件位于 /var/log/containers；符号链接位于 /var/log/pods
   - B) 实际文件位于 /var/log/pods；兼容性符号链接位于 /var/log/containers
   - C) 每个 runtime 都仅写入 /var/lib/docker
   - D) kubectl logs 包含无限归档

<details>
<summary>显示答案</summary>

**答案: B**

原始路径颠倒了。podLogsDir/OS/runtime 可能会改变布局。轮转和 --previous 不会创建集中式历史归档。

</details>

4. 公平比较 backend 成本需要什么？

   - A) 只需 S3 的 GB 价格
   - B) 始终选择 Loki 以获得最低账单
   - C) 假设自行管理的查询是免费的
   - D) 在相同 workload 下比较摄取、保留/索引的数据、计算、查询、请求、网络、恢复和运维

<details>
<summary>显示答案</summary>

**答案: D**

旧的 2025 和 100-GB 数字混用了单位，并且缺乏可复现的配置。它们并非经过测量的生产结果；只更新日期无法修复这些问题。

</details>

5. 应如何将 trace context 附加到日志？

   - A) 为每条记录生成无关联的 ID
   - B) 使用实际活动的 context；所示的 trace/span ID 分别有 32/16 个十六进制字符，并且不能全为零
   - C) 要求每条启动记录都包含 trace ID
   - D) 使用 session token 作为 span ID

<details>
<summary>显示答案</summary>

**答案: B**

没有 trace 的事件是有效的。JSON 字段名需要映射到目标模型；仅有 ID 并不能创建分布式 trace 或证明关联性。

</details>

6. 对于示例 pipeline，哪种处理选择更安全？

   - A) 丢弃每一行包含 HealthCheck 的日志
   - B) 信任应用 JSON 作为 tenant 身份
   - C) 将应用字段与可信元数据分开，并验证脱敏/过滤、offset、buffer 和 retry
   - D) 假设缓冲可防止所有丢失和重复

<details>
<summary>显示答案</summary>

**答案: C**

Fluent Bit 示例是一个经典格式的 filter 片段。Keep_Log 会保留另一个副本以供脱敏。失败的健康检查可能是有价值的证据，且交付保证取决于完整路径。

</details>

7. 应如何选择法规要求的保留期限？

   - A) 根据适用的记录类型、司法管辖区、合同、法律保留要求和已批准的政策
   - B) 所有财务日志均保留七年
   - C) 所有医疗保健日志均保留六年
   - D) 使用指定的 backend 即可证明合规

<details>
<summary>显示答案</summary>

**答案: A**

行业标签并不是完整的法律规则。在保留/删除/访问计划中纳入副本、对象版本、备份和导出，并测试恢复。

</details>

8. 关于 sidecar 和 DaemonSet，哪项正确？

   - A) 两者都保证 tenant 隔离
   - B) emptyDir 在 Pod 删除后仍然保留
   - C) DaemonSet 能证明所有节点日志均已交付
   - D) Sidecar 可以帮助仅写入文件的应用；但仍需验证调度、共享存储、生命周期和安全性

<details>
<summary>显示答案</summary>

**答案: D**

emptyDir 会在 Pod 内的 container 重启期间保留，但不会在 Pod 删除后保留。DaemonSet 面向符合条件的节点，并且可能存在 rollout 重叠；多条路由可能会重复记录。

</details>

9. 哪项存储/client 说法正确？

   - A) 在每种 Deployment 中，OpenSearch 都仅将 S3 用于 snapshot
   - B) Deployment/index/query 设计很重要；UltraWarm 使用 S3/cache，且 Promtail 在其声明的 EOL 后需要迁移
   - C) 所有 CloudWatch 日志类别都具有相同功能
   - D) 没有 dataset 的压缩排名是有效的

<details>
<summary>显示答案</summary>

**答案: B**

比较实际的 Deployment 模型和查询需求。Promtail 的 EOL 是 2026-03-02；该通知将 lambda-promtail 视为单独项目。选择 backend 并不保证成本或合规性。

</details>

10. 启用 EKS control-plane audit logging 确立了什么？

   - A) 每个请求和请求正文都会被无损记录
   - B) Worker DaemonSet 会读取受管理的 API-server host
   - C) audit 记录遵循 policy，并通过必须验证的尽力而为 CloudWatch 交付路径传递
   - D) 应用 stdout 收集会自动完整

<details>
<summary>显示答案</summary>

**答案: C**

检查异步更新状态、实际 stream 以及保留/访问。Fargate 使用其受管理的 router；Container Insights performance logs 与应用 stdout/stderr 不同。

</details>

---

[返回指南](../../../observability/logging/README.md)
