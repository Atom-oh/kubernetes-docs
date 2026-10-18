# CloudWatch Logs 测验

> **最后更新**: 2026 年 9 月 13 日

[指南](../../../observability/logging/03-cloudwatch-logs.md)

---

1. 以下哪项不是 EKS 控制平面日志类型？

   - A) api
   - B) audit
   - C) worker
   - D) scheduler

<details>
<summary>显示答案</summary>

**答案：C**

这五种类型是 api、audit、authenticator、controllerManager 和 scheduler。工作节点/应用程序日志以及 Auto Mode 托管组件日志的投递属于独立路径。

</details>

---

2. 应如何比较 CloudWatch Logs 的成本因素？

   - A) 摄取费用始终是每月最大的费用
   - B) 存储始终免费
   - C) 每条 S3 投递路径都免费
   - D) 比较实际数据量、保留期、扫描量、日志类别、区域和下游费用

<details>
<summary>显示答案</summary>

**答案：D**

仅凭每 GB 摄取数据的价格，无法与按 GB·月计费的存储或重复扫描的数据量比较成本高低。指南中的 $1,575 示例是假设性的算术计算，并非当前首尔区域定价或完整账单。

</details>

---

3. 哪个 Logs Insights QL 命令使用 glob 匹配模式或正则表达式提取字段？

   - A) extract
   - B) parse
   - C) select
   - D) filter

<details>
<summary>显示答案</summary>

**答案：B**

parse 提取字段；jsonParse 可以解析 JSON 消息。采集器的封装结构将应用程序字段放在 log_processed 下。使用 glob 时，不要假定 JSON 键可以按任意顺序排列。

</details>

---

4. 本指南中手动配置的应用程序日志采集器使用哪个日志组？

   - A) /aws/containerinsights/example-eks/application
   - B) /aws/eks/example-eks/logs
   - C) /var/log/containers/example-eks
   - D) 每个集群都使用同一个不可变的通用日志组名称

<details>
<summary>显示答案</summary>

**答案：A**

配置的应用程序日志组与控制平面日志使用的 /aws/eks/example-eks/cluster 不同。该日志组会预先准备；采集器不会创建它或更改保留期。

</details>

---

5. 关于订阅投递，哪项说法正确？

   - A) S3 存储桶 ARN 是订阅筛选器的直接目标
   - B) CloudWatch 订阅批次可通过 Firehose 的 OpenSearch 目标进行投递
   - C) 订阅可以发送到 Lambda、Kinesis 或 Firehose；通过 Firehose 归档到 S3 是单独的下游步骤
   - D) 订阅保证恰好一次投递，并回填全部历史记录

<details>
<summary>显示答案</summary>

**答案：C**

目标 API 和输入格式很重要。CloudWatch Logs→Firehose→OpenSearch 明确不受支持。订阅采用异步、至少一次投递；导出任务和服务提供的日志投递（vended-log delivery）使用的是不同 API。

</details>

---

6. CloudWatch Logs 的原生 C Fluent Bit 输出插件是什么？

   - A) cloudwatch
   - B) cloudwatch_logs
   - C) aws_cloudwatch
   - D) cw_logs

<details>
<summary>显示答案</summary>

**答案：B**

cloudwatch_logs 是原生插件。cloudwatch 是较旧的 Go 插件。凭证、实际的 ServiceAccount、输出日志组和 IAM 策略仍需相互匹配。

</details>

---

7. 哪个 QL 查询按小时统计事件，并对生成的时间桶排序？

   - A) stats count(*) group by hour
   - B) stats count(*) as log_count by bin(1h) as bucket | sort bucket asc
   - C) select count(*) from logs group by hour
   - D) stats count(*) by bin(1h) | sort @message

<details>
<summary>显示答案</summary>

**答案：B**

stats 会更改可用的输出字段，因此应按时间桶的别名 bucket 排序。延迟百分位数函数是 pct，而不是 percentile；不区分大小写的正则表达式在斜杠内使用 (?i)。

</details>

---

8. 哪种日志策略不适合作为默认的成本控制方法？

   - A) 根据必须保留的记录审查筛选器
   - B) 由日志组的唯一管理方设置保留期
   - C) 无限期保留所有 DEBUG 输出，并不加区分地丢弃安全相关记录来抵消成本
   - D) 在更改设计前测量摄取量和扫描量

<details>
<summary>显示答案</summary>

**答案：C**

控制数据量时，必须保留所需的诊断和安全记录。ConfigMap 中的 LOG_LEVEL 仅在应用程序使用它时才会生效。更改保留期可能会删除数据。

</details>

---

9. 指标筛选器有什么作用，默认值为零意味着什么？

   - A) 它将每条历史记录导出到 S3
   - B) 它从新到达的匹配日志派生指标；有日志到达但没有记录匹配时，默认值为零
   - C) 即使没有日志到达，它也始终输出零
   - D) 它支持每种日志类别中的所有功能

<details>
<summary>显示答案</summary>

**答案：B**

本章使用 Standard 类别的 JSON 筛选器，匹配 $.log_processed.level。没有传入日志时，数据可能缺失。该告警检查两个五分钟周期中的错误计数，而不是错误率，也不能证明服务健康。

</details>

---

10. 哪种 IAM 和管理归属安排适用于手动配置的纯日志采集器？

   - A) 为所有 Pod 授予管理员角色
   - B) 将策略附加到 cloudwatch-agent，同时部署无关的 ServiceAccount
   - C) 仅使用 s3:PutObject
   - D) 预先创建日志组，在其 ARN 上授权 logs:CreateLogStream/logs:PutLogEvents，并映射实际的采集器 ServiceAccount

<details>
<summary>显示答案</summary>

**答案：D**

手动配置方案使用 logging/fluent-bit-cloudwatch 和已批准的 IRSA 信任关系。此路径不需要 PutMetricData 或宽泛的 logs:* 权限。完整可观测性 chart 属于独立配置方案，其 Fluent Bit Pod 使用 cloudwatch-agent。

</details>
