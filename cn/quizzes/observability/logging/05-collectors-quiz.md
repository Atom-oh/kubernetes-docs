# Log Collector 对比测验

> **最后更新**: September 13, 2026

1. 应如何比较 Collector 的资源需求？

   - A) 根据实现语言假设固定的内存排名
   - B) 对相同的 records、处理、destinations 和故障设置进行基准测试
   - C) 将每个 Go Collector 视为完全相同
   - D) 使用单一已发布的 events/second 数值

<details>
<summary>显示答案</summary>

**答案：B) 对相同的 records、处理、destinations 和故障设置进行基准测试**

Buffer 限制、metadata caches、batching、retries 和 concurrency 都会影响资源使用。仅凭一种语言或 compression format 无法确立 throughput 保证。

</details>

---

2. 哪个 Fluent Bit filter 会添加 Pod 和 namespace metadata？

   - A) modify
   - B) parser
   - C) kubernetes
   - D) 仅 record_modifier

<details>
<summary>显示答案</summary>

**答案：C) kubernetes**

kubernetes filter 需要正确的 tags 和已获授权的 metadata access。启用 Use_Kubelet 需要其自身的 kubelet connectivity 和 permission checks。

</details>

---

3. 当前针对 Promtail 的正确做法是什么？

   - A) 迁移：它于 2026 年 3 月 2 日达到 EOL
   - B) 为每个新的 Loki deployment 选择它
   - C) 假设现有安装仍会收到未来更新
   - D) 此弃用也会自动包括 lambda-promtail

<details>
<summary>显示答案</summary>

**答案：A) 迁移：它于 2026 年 3 月 2 日达到 EOL**

官方 lifecycle notice 指引迁移到 Alloy 或其他受支持的 client，并明确将独立的 lambda-promtail client 排除在该 notice 之外。

</details>

---

4. Grafana Alloy 使用什么语法？

   - A) 无需转换的任何 Kubernetes YAML
   - B) Alloy configuration syntax，以前称为 River
   - C) 包含所有 Terraform providers 的 Terraform HCL
   - D) 仅 INI

<details>
<summary>显示答案</summary>

**答案：B) Alloy configuration syntax，以前称为 River**

该语法类似 HCL，但 Alloy component graph 不是可互换的 Terraform file。请使用所选的 Alloy binary 对其进行验证。

</details>

---

5. 通常的 Collector pipeline 顺序是什么？

   - A) Exporters → Receivers → Processors
   - B) Processors → Exporters → Receivers
   - C) Receivers → Processors → Exporters
   - D) 所有 components 按任意顺序运行

<details>
<summary>显示答案</summary>

**答案：C) Receivers → Processors → Exporters**

Connectors 可以连接 pipelines。当前 Loki path 使用 OTLP HTTP；已移除的 loki exporter 不存在于 Contrib0.160.0 中。

</details>

---

6. 示例 Lua transform 能保证什么？

   - A) 从任意文本中移除所有可能的 secret
   - B) 删除原始 node log files
   - C) exactly-once delivery
   - D) 对选定的 structured keys 进行脱敏，并移除原始重复项

<details>
<summary>显示答案</summary>

**答案：D) 对选定的 structured keys 进行脱敏，并移除原始重复项**

它不是通用 PII detector 或 fail-closed boundary。plaintext 和 free-text message values 仍可能包含敏感数据。

</details>

---

7. 哪些名称正确区分了旧版 Promtail 和 Alloy drop stages？

   - A) 两者都将 stage.drop 用作 Promtail YAML key
   - B) Promtail YAML drop；Alloy stage.drop
   - C) Promtail filter.exclude；Alloy ignore
   - D) 两者都不支持丢弃 records

<details>
<summary>显示答案</summary>

**答案：B) Promtail YAML drop；Alloy stage.drop**

Parser、template、labels 和 output stages 同样具有顺序和 field-retention 效果。不要将 stage catalogue 视为一条通用 processing chain。

</details>

---

8. 两个 AWS destinations 的原生 Fluent Bit output plugin 名称是什么？

   - A) cloudwatch_logs and opensearch
   - B) cloudwatch and elastic only
   - C) stage.cloudwatch and stage.opensearch
   - D) Loki tenant_id creates both AWS destinations

<details>
<summary>显示答案</summary>

**答案：A) cloudwatch_logs and opensearch**

Plugin availability 不授予 IAM permissions。请匹配实际的 ServiceAccount identity、Region、endpoint、TLS 以及预先创建的 resource ownership。

</details>

---

9. memory_limiter 在 memory pressure 下会做什么？

   - A) 保证 process 永远不会 OOM
   - B) 创建额外的 node memory
   - C) 可以使用可重试错误拒绝 data 并请求 garbage collection
   - D) 自动持久化每条 source record

<details>
<summary>显示答案</summary>

**答案：C) 可以使用可重试错误拒绝 data 并请求 garbage collection**

Receiver retry behavior、limits 和 queues 很重要。有界的 filelog retry window 可能到期并丢弃失败的 batch。

</details>

---

10. 成功完成 Promtail-to-Alloy conversion 后必须做什么？

   - A) 立即声明相同的 delivery 和 metrics
   - B) 忽略所有 diagnostic warnings
   - C) 无限期地在相同 logs 上运行两个 agents
   - D) 验证 parsing、state、ownership、authentication、self-metrics 和真实 backend records

<details>
<summary>显示答案</summary>

**答案：D) 验证 parsing、state、ownership、authentication、self-metrics 和真实 backend records**

converter 可以将全局 rate limit 更改为每个 pipeline 的 limits，并且不会验证 host mounts 或 Kubernetes permissions。选择 file 或 API ownership 以避免重复 collection。

</details>

---

[返回指南](../../../observability/logging/05-collectors.md)
