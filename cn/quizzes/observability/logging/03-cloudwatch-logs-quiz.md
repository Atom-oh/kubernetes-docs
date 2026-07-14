# CloudWatch Logs 测验

测试您对 Amazon CloudWatch Logs 的理解。

---

1. 以下哪项不是 EKS control plane logging 支持的日志类型？

   - A) api
   - B) audit
   - C) worker
   - D) scheduler

<details>
<summary>显示答案</summary>

**答案：C) worker**

**说明：**
EKS control plane 支持 5 种日志类型：api、audit、authenticator、controllerManager 和 scheduler。Worker node 日志不属于 control plane 日志，必须通过 Container Insights 或 FluentBit 单独收集。

</details>

---

2. CloudWatch Logs 定价结构中费用最高的项目是什么？

   - A) Storage
   - B) Ingestion
   - C) Query (Logs Insights)
   - D) S3 Export

<details>
<summary>显示答案</summary>

**答案：B) Ingestion**

**说明：**
CloudWatch Logs 的数据摄取费用为 $0.50/GB，远高于存储费用（$0.03/GB/月）或查询费用（每扫描 GB $0.005）。因此，过滤不必要的日志对成本优化非常重要。

</details>

---

3. CloudWatch Logs Insights 中用于提取特定字段的命令是什么？

   - A) extract
   - B) parse
   - C) select
   - D) filter

<details>
<summary>显示答案</summary>

**答案：B) parse**

**说明：**
在 CloudWatch Logs Insights 中，`parse` 命令从日志消息中提取与特定模式匹配的字段。示例：`parse @message '"level":"*"' as level`

</details>

---

4. 通过 Container Insights 收集的日志使用什么 log group 路径格式？

   - A) `/aws/eks/cluster-name/logs`
   - B) `/aws/containerinsights/cluster-name/application`
   - C) `/var/log/containers/cluster-name`
   - D) `/kubernetes/cluster-name/logs`

<details>
<summary>显示答案</summary>

**答案：B) `/aws/containerinsights/cluster-name/application`**

**说明：**
Container Insights 会在 `/aws/containerinsights/{cluster-name}/` 路径下创建 log group，包括 application、host、dataplane 和 performance log group。

</details>

---

5. CloudWatch Logs 中哪项功能可将日志传送到 Lambda functions 以进行实时日志处理？

   - A) Log Stream
   - B) Metric Filter
   - C) Subscription Filter
   - D) Log Insight

<details>
<summary>显示答案</summary>

**答案：C) Subscription Filter**

**说明：**
Subscription Filter 可将 log group 中的日志实时传送到其他服务（Lambda、Kinesis Data Firehose、Kinesis Data Streams）。您可以指定过滤模式，仅传送特定日志。

</details>

---

6. 用于将日志发送到 CloudWatch Logs 的 FluentBit OUTPUT plugin 名称是什么？

   - A) cloudwatch
   - B) cloudwatch_logs
   - C) aws_cloudwatch
   - D) cw_logs

<details>
<summary>显示答案</summary>

**答案：B) cloudwatch_logs**

**说明：**
FluentBit 的 CloudWatch Logs output plugin 名为 `cloudwatch_logs`。它默认包含在 AWS 提供的 `aws-for-fluent-bit` image 中。

</details>

---

7. 按时间段汇总日志数量的正确 CloudWatch Logs Insights query 是什么？

   - A) `stats count(*) group by hour`
   - B) `stats count(*) as log_count by bin(1h)`
   - C) `select count(*) from logs group by hour`
   - D) `aggregate count by time(1h)`

<details>
<summary>显示答案</summary>

**答案：B) `stats count(*) as log_count by bin(1h)`**

**说明：**
在 CloudWatch Logs Insights 中，基于时间的聚合使用 `stats` 命令和 `bin()` function。`bin(1h)` 将数据分组为 1 小时间隔。

</details>

---

8. 以下哪项不是推荐的 CloudWatch Logs 成本优化策略？

   - A) 过滤不必要的日志（healthcheck 等）
   - B) 按环境设置不同的保留期限
   - C) 收集所有 DEBUG level 日志
   - D) 将长期保留的日志归档到 S3

<details>
<summary>显示答案</summary>

**答案：C) 收集所有 DEBUG level 日志**

**说明：**
DEBUG level 日志非常详细，会显著增加日志量。在生产环境中，仅收集 INFO level 及以上的日志有助于成本优化。

</details>

---

9. 在 CloudWatch Logs 中使用 Metric Filters 的主要目的是什么？

   - A) 将日志导出到 S3
   - B) 根据日志模式创建 CloudWatch metrics
   - C) 设置日志保留期限
   - D) 配置日志加密

<details>
<summary>显示答案</summary>

**答案：B) 根据日志模式创建 CloudWatch metrics**

**说明：**
Metric Filters 可检测日志中的特定模式（例如 ERROR），并创建 CloudWatch metrics。您可以基于这些 metrics 设置 CloudWatch Alarms 以接收通知。

</details>

---

10. 在 EKS cluster 上设置 Container Insights 时，IRSA (IAM Roles for Service Accounts) 不需要以下哪项权限？

    - A) logs:CreateLogGroup
    - B) logs:PutLogEvents
    - C) s3:PutObject
    - D) cloudwatch:PutMetricData

<details>
<summary>显示答案</summary>

**答案：C) s3:PutObject**

**说明：**
基本的 Container Insights 设置不需要 S3 权限。只需要 CloudWatch Logs（logs:*）和 CloudWatch Metrics（cloudwatch:PutMetricData）权限。只有在设置单独将日志导出到 S3 时，才需要 S3 权限。

</details>
