# 可观测性实验第 5 部分：告警与 AIOps 测验

<span id="observability-lab-part-5-alerting-and-aiops-quiz"></span>

> **最后更新**: September 13, 2026

1. 哪个组件负责评估 PrometheusRule 告警？
   - A) Alertmanager
   - B) Prometheus
   - C) SNS
   - D) Lambda DLQ

<details>
<summary>显示答案</summary>

**答案：B) Prometheus**

Prometheus 负责评估；Alertmanager 负责分组、路由和通知。

</details>

---

2. DatapointsToAlarm=2 和 EvaluationPeriods=3 表示什么？
   - A) 必须恰好连续两次超出阈值。
   - B) 三个已评估数据点中必须有两个超出阈值；它们不必连续。
   - C) 每三秒发送两条通知。
   - D) 使用两个 Region。

<details>
<summary>显示答案</summary>

**答案：B) 三个已评估数据点中必须有两个超出阈值；它们不必连续。**

Period 是指标聚合粒度，并不等同于评估频率。

</details>

---

3. 评估旧版 Grafana OnCall OSS 安装步骤时，什么很重要？
   - A) 它具有永久支持。
   - B) 考虑归档以及 Cloud Connection 于 2026-03-24 终止。
   - C) SMS 支持始终永久免费。
   - D) 应用任意 YAML 即可使其正常运行。

<details>
<summary>显示答案</summary>

**答案：B) 考虑归档以及 Cloud Connection 于 2026-03-24 终止。**

验证受支持的事件/通知路径以及组织实际的交付情况。

</details>

---

4. 为什么要将 SNS 输入和输出主题分开？
   - A) 为了更改指标单位。
   - B) 防止报告程序在循环中处理自身的结果。
   - C) 因为 SNS 仅支持一个主题。
   - D) 为了公开发布日志。

<details>
<summary>显示答案</summary>

**答案：B) 防止报告程序在循环中处理自身的结果。**

将订阅和 IAM 发布权限限制在同一边界内。

</details>

---

5. 对于 Alertmanager `{{ . | toJson }}` 输出，解析器必须考虑什么？
   - A) 它始终是纯文本。
   - B) 带有 JSON 标签的小写/camelCase 键与首字母大写的 Go 模板字段访问不同。
   - C) JSON 永远不需要解析。
   - D) 所有 SNS 消息都具有相同的字段。

<details>
<summary>显示答案</summary>

**答案：B) 带有 JSON 标签的小写/camelCase 键与首字母大写的 Go 模板字段访问不同。**

已测试实际的 0.34.0 模板序列化以及有效/无效负载。

</details>

---

6. 应如何报告缺失指标或查询失败？
   - A) 将它们转换为零错误。
   - B) 标记为 missing/no_data/error，而不是虚构测量结果。
   - C) 将查询字符串呈现为测量值。
   - D) 始终报告健康状态。

<details>
<summary>显示答案</summary>

**答案：B) 标记为 missing/no_data/error，而不是虚构测量结果。**

当证据不足时，可以跳过模型调用。

</details>

---

7. 在此示例中，Powertools 幂等性提供什么？
   - A) 端到端的 SNS 恰好一次交付。
   - B) 在 24 小时内禁止对具有相同消息 ID 的重复成功工作。
   - C) 每个新的消息 ID 都是同一操作。
   - D) 以原子方式组合发布和 DB 提交。

<details>
<summary>显示答案</summary>

**答案：B) 在 24 小时内禁止对具有相同消息 ID 的重复成功工作。**

区分发布/提交重复窗口以及 SNS/Lambda 重试层。

</details>

---

8. 如何接受 Converse 诊断响应？
   - A) 任何响应都视为成功。
   - B) 设置 maxTokens，并要求 end_turn 和非空文本。
   - C) max_tokens 停止表示诊断已完成。
   - D) 立即执行模型生成的命令。

<details>
<summary>显示答案</summary>

**答案：B) 设置 maxTokens，并要求 end_turn 和非空文本。**

报告程序创建供人工审查的假设，并且没有修复工具。

</details>

---

9. 如何配置告警以启动 CloudWatch Investigations？
   - A) 调用 list-dashboards。
   - B) 将已准备好的 investigation-group ARN 添加为告警操作。
   - C) 仅调用 put-insight-rule。
   - D) 仅启用 Application Signals 发现。

<details>
<summary>显示答案</summary>

**答案：B) 将已准备好的 investigation-group ARN 添加为告警操作。**

准备组、权限、保留、加密以及实际的告警操作。

</details>

---

10. 调用多个分析模块是否实现了 A2A 协议？
   - A) 两个函数会自动实现 A2A。
   - B) 不会；发现、身份验证以及任务/消息契约需要单独实现。
   - C) SNS 总是意味着 A2A。
   - D) 仅 DynamoDB 就足够了。

<details>
<summary>显示答案</summary>

**答案：B) 不会；发现、身份验证以及任务/消息契约需要单独实现。**

专家拆分是一种设计模式，不同于遵循代理协议。

</details>

---

[返回指南](../../../labs/observability/05-alerting-aiops-lab.md)
