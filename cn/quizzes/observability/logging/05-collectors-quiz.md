# 日志采集器对比测验

> **最后更新**: 2026 年 9 月 13 日

1. 应如何比较采集器的资源需求？

   - A) 根据实现语言假设固定的内存用量排名
   - B) 使用相同的记录、处理流程、目标和故障设置进行基准测试
   - C) 将每个 Go 采集器视为完全相同
   - D) 使用某一个已发布的每秒事件数

<details>
<summary>显示答案</summary>

**答案：B) 使用相同的记录、处理流程、目标和故障设置进行基准测试**

缓冲区限制、元数据缓存、批处理、重试和并发都会影响资源使用。仅凭实现语言或压缩格式，无法保证吞吐量。

</details>

---

2. 哪个 Fluent Bit 过滤器会添加 Pod 和命名空间元数据？

   - A) modify
   - B) parser
   - C) kubernetes
   - D) 仅 record_modifier

<details>
<summary>显示答案</summary>

**答案：C) kubernetes**

kubernetes 过滤器需要正确的标签和获授权的元数据访问。启用 Use_Kubelet 时，还需单独检查 kubelet 连通性和权限。

</details>

---

3. 当前针对 Promtail 的正确做法是什么？

   - A) 迁移：它于 2026 年 3 月 2 日结束生命周期（EOL）
   - B) 每个新的 Loki 部署都选择它
   - C) 假设现有安装仍会收到未来更新
   - D) 此退役也会自动包括 lambda-promtail

<details>
<summary>显示答案</summary>

**答案：A) 迁移：它于 2026 年 3 月 2 日结束生命周期（EOL）**

官方生命周期公告指引用户迁移到 Alloy 或其他受支持的客户端，并明确将独立的 lambda-promtail 客户端排除在该公告范围之外。

</details>

---

4. Grafana Alloy 使用什么语法？

   - A) 无需转换的任意 Kubernetes YAML
   - B) Alloy 配置语法，原称 River
   - C) 包含所有 Terraform 提供程序的 Terraform HCL
   - D) 仅 INI

<details>
<summary>显示答案</summary>

**答案：B) Alloy 配置语法，原称 River**

该语法类似 HCL，但 Alloy 组件图不能当作 Terraform 文件互换使用。请使用选定的 Alloy 二进制程序验证配置。

</details>

---

5. Collector 流水线通常按什么顺序处理数据？

   - A) 导出器 → 接收器 → 处理器
   - B) 处理器 → 导出器 → 接收器
   - C) 接收器 → 处理器 → 导出器
   - D) 所有组件按任意顺序运行

<details>
<summary>显示答案</summary>

**答案：C) 接收器 → 处理器 → 导出器**

连接器可以连接多条流水线。当前 Loki 路径使用 OTLP HTTP；已移除的 loki 导出器不存在于 Contrib 0.160.0 中。

</details>

---

6. 示例 Lua 转换能保证什么？

   - A) 从任意文本中移除所有可能的机密信息
   - B) 删除原始节点日志文件
   - C) 恰好一次投递
   - D) 对选定的结构化键进行脱敏，并移除原始重复项

<details>
<summary>显示答案</summary>

**答案：D) 对选定的结构化键进行脱敏，并移除原始重复项**

它不是通用 PII 检测器，也不是在失败时拒绝继续处理的安全边界（fail-closed）。明文和自由文本消息值仍可能包含敏感数据。

</details>

---

7. 哪些名称正确区分了旧版 Promtail 和 Alloy 的丢弃阶段？

   - A) 两者都将 stage.drop 用作 Promtail YAML 键
   - B) Promtail YAML drop；Alloy stage.drop
   - C) Promtail filter.exclude；Alloy ignore
   - D) 两者都不支持丢弃记录

<details>
<summary>显示答案</summary>

**答案：B) Promtail YAML drop；Alloy stage.drop**

解析器、模板、标签和输出阶段同样会受到顺序影响，并影响字段保留。不要将阶段列表视为一条通用处理链。

</details>

---

8. 面向这两个 AWS 目标的原生 Fluent Bit 输出插件名称是什么？

   - A) cloudwatch_logs 和 opensearch
   - B) 仅 cloudwatch 和 elastic
   - C) stage.cloudwatch 和 stage.opensearch
   - D) Loki tenant_id 会创建这两个 AWS 目标

<details>
<summary>显示答案</summary>

**答案：A) cloudwatch_logs 和 opensearch**

插件可用并不意味着已获得 IAM 权限。请匹配实际的 ServiceAccount 身份、区域、端点、TLS 以及预先创建资源的管理归属。

</details>

---

9. memory_limiter 在内存压力下会做什么？

   - A) 保证进程永远不会 OOM
   - B) 创建额外的节点内存
   - C) 可以返回可重试错误来拒绝数据，并请求垃圾回收
   - D) 自动持久化每条源记录

<details>
<summary>显示答案</summary>

**答案：C) 可以返回可重试错误来拒绝数据，并请求垃圾回收**

接收器的重试行为、限制和队列都很重要。filelog 的重试时间窗口有限，窗口到期后可能丢弃失败的批次。

</details>

---

10. 成功将 Promtail 配置转换为 Alloy 配置后，必须做什么？

   - A) 立即宣称投递行为和指标完全相同
   - B) 忽略所有诊断警告
   - C) 无限期地在相同日志上运行两个代理
   - D) 验证解析、状态、管理归属、身份验证、自身指标以及后端实际记录

<details>
<summary>显示答案</summary>

**答案：D) 验证解析、状态、管理归属、身份验证、自身指标以及后端实际记录**

转换器可能将全局速率限制改为每条流水线的限制，且不会验证主机挂载或 Kubernetes 权限。应确定由谁通过文件或 API 采集日志，以免重复采集。

</details>

---

[返回指南](../../../observability/logging/05-collectors.md)
