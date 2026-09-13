# CloudWatch Logs 测验

> **最后更新**: September 13, 2026

[指南](../../../observability/logging/03-cloudwatch-logs.md)

---

1. 以下哪项不是 EKS control-plane 日志类型？

   - A) api
   - B) audit
   - C) worker
   - D) scheduler

<details>
<summary>显示答案</summary>

**答案：C**

这五种类型是 api、audit、authenticator、controllerManager 和 scheduler。Worker/application 日志以及 Auto Mode managed-component 交付属于独立路径。

</details>

---

2. 应如何比较 CloudWatch Logs 成本驱动因素？

   - A) Ingestion 始终是每月最大的费用
   - B) Storage 始终免费
   - C) 每条 S3 交付路径都免费
   - D) 比较实际容量、retention、scans、class、Region 和下游费用

<details>
<summary>显示答案</summary>

**答案：D**

仅凭每 GB ingested 的价格，无法与 GB-month storage 或重复 scan 容量进行排序比较。指南中的 $1,575 示例是假设性的算术计算，并非当前 Seoul 定价或完整账单。

</details>

---

3. 哪个 Logs Insights QL 命令使用 glob 或正则表达式提取字段？

   - A) extract
   - B) parse
   - C) select
   - D) filter

<details>
<summary>显示答案</summary>

**答案：B**

parse 提取字段；jsonParse 可以解析 JSON message。collector envelope 将 application 字段置于 log_processed 下。不要假定 glob 中任意 JSON key 的顺序。

</details>

---

4. 本指南中的手动 application collector 使用哪个 group？

   - A) /aws/containerinsights/example-eks/application
   - B) /aws/eks/example-eks/logs
   - C) /var/log/containers/example-eks
   - D) 每个 cluster 都使用一个不可变的通用 group 名称

<details>
<summary>显示答案</summary>

**答案：A**

配置的 application group 与 control-plane 日志使用的 /aws/eks/example-eks/cluster 不同。该 group 会预先准备；collector 不会创建它或更改 retention。

</details>

---

5. 关于 subscription delivery，哪项说法正确？

   - A) S3 bucket ARN 是直接的 subscription-filter destination
   - B) CloudWatch subscription batches 可通过 Firehose 的 OpenSearch destination 工作
   - C) subscription 可以发送到 Lambda、Kinesis 或 Firehose；通过 Firehose 归档到 S3 是单独的下游步骤
   - D) Subscriptions 保证 exactly-once delivery，并回填全部历史记录

<details>
<summary>显示答案</summary>

**答案：C**

destination API 和 input format 很重要。CloudWatch Logs→Firehose→OpenSearch 明确不受支持。Subscriptions 是异步且 at least once；export tasks 和 vended-log delivery 是不同的 API。

</details>

---

6. CloudWatch Logs 的原生 C Fluent Bit output plugin 是什么？

   - A) cloudwatch
   - B) cloudwatch_logs
   - C) aws_cloudwatch
   - D) cw_logs

<details>
<summary>显示答案</summary>

**答案：B**

cloudwatch_logs 是原生 plugin。cloudwatch 是较旧的 Go plugin。Credentials、实际的 ServiceAccount、output group 和 IAM policy 仍需要相匹配。

</details>

---

7. 哪个 QL query 按小时统计 events，并对生成的 time buckets 排序？

   - A) stats count(*) group by hour
   - B) stats count(*) as log_count by bin(1h) as bucket | sort bucket asc
   - C) select count(*) from logs group by hour
   - D) stats count(*) by bin(1h) | sort @message

<details>
<summary>显示答案</summary>

**答案：B**

stats 会更改可用的 output fields，因此应对其 bucket alias 排序。latency percentile function 是 pct，而不是 percentile；不区分大小写的 regex 在斜杠内使用 (?i)。

</details>

---

8. 哪种 logging policy 作为默认的 cost-control 方法是不安全的？

   - A) 针对必须保留的 records 审查 filters
   - B) 通过 log group 的单一 owner 设置 retention
   - C) 无限期保留所有 DEBUG output，并不加区分地丢弃 security-relevant records 作为补偿
   - D) 在更改设计前测量 ingestion 和 scans

<details>
<summary>显示答案</summary>

**答案：C**

容量控制必须保留所需的 diagnostics 和 security records。ConfigMap 中的 LOG_LEVEL 仅在 application 使用它时才会生效。Retention 更改可能会删除数据。

</details>

---

9. metric filter 的作用是什么，zero default 又意味着什么？

   - A) 它将每条 historical record 导出到 S3
   - B) 它从新的匹配 logs 派生 metrics；当 logs 到达但没有 records 匹配时，默认值为 zero
   - C) 即使没有 logs 到达，它也始终输出 zero
   - D) 它支持每种 log class 中的所有功能

<details>
<summary>显示答案</summary>

**答案：B**

本章在 $.log_processed.level 上使用 Standard-class JSON filter。没有传入 logs 时，数据可能缺失。该 alarm 检查两个 five-minute periods 中的 error count，而不是 error rate 或 Service health 的证明。

</details>

---

10. 哪种 IAM/ownership 安排适用于手动 logs-only collector？

   - A) 为所有 Pods 授予 administrator role
   - B) 将 policy 附加到 cloudwatch-agent，同时部署无关的 ServiceAccount
   - C) 仅使用 s3:PutObject
   - D) 预先创建 group，在其 ARN 上授权 logs:CreateLogStream/logs:PutLogEvents，并映射实际的 collector ServiceAccount

<details>
<summary>显示答案</summary>

**答案：D**

手动 profile 使用 logging/fluent-bit-cloudwatch 和已批准的 IRSA trust。此路径不需要 PutMetricData 或宽泛的 logs:*。完整 observability chart 属于独立 profile，其 Fluent Bit Pods 使用 cloudwatch-agent。

</details>
