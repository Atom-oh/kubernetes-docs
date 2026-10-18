# CloudWatch Metrics 测验

根据 2026-09-13 版指南进行复核。

1. 使用托管 CloudWatch 后端后，团队可以从哪些责任中卸下工作？

   - A) 所有采集和 IAM 工作
   - B) 仅 AWS 后端运维；collector、身份、保留策略和响应仍需明确负责人
   - C) 所有网络前提条件
   - D) 所有查询和日志费用

<details>
<summary>显示答案</summary>

**答案：B**

传统、增强型和 OTel 采集方式有不同的命名与计费模型。托管存储并不意味着无需运维。

</details>

2. 关于在 EKS 上安装 CloudWatch 组件，哪项说法正确？

   - A) `update-cluster-logging` 会安装 Container Insights
   - B) 所有计算平台都运行同一种主机 DaemonSet
   - C) 选择兼容的 add-on 或由团队负责的 Helm 安装，并验证平台与身份前提条件
   - D) Helm 6.6.0 必然就是 EKS add-on 的版本

<details>
<summary>显示答案</summary>

**答案：C**

控制平面日志是另一项配置。Fargate 不运行此处展示的主机 DaemonSet；Auto Mode 和混合计算需要检查兼容性。Pod Identity/IRSA 仍需实际完成配置。

</details>

3. 如何用 `SEARCH` 生成前十名的仪表板视图？

   - A) `SEARCH` 本身总会将结果限制为十项
   - B) `SLICE(SORT(SEARCH(...), AVG, DESC), 0, 10)`
   - C) `PERCENTILE(SEARCH(...), 10)`
   - D) 对 `SEARCH` 数组直接创建普通告警

<details>
<summary>显示答案</summary>

**答案：B**

`SEARCH` 会返回匹配的时间序列。要排序并截取前十项，必须显式执行排序和切片；排名依据所评估的时间范围。不能直接对 `SEARCH` 结果创建告警。

</details>

4. 关于百分位数和比率，哪项说法正确？

   - A) `PERCENTILE(METRICS(),95)` 会给出全局请求 p95
   - B) 每个零流量时段都代表健康的零错误结果
   - C) `AVG(METRICS()) PERIOD(300)` 是移动平均值
   - D) 使用受支持的 p95 统计值；比率分母应防止零流量，并检查遥测缺失

<details>
<summary>显示答案</summary>

**答案：D**

指南对 ALB 计数使用 Sum，并采用 `IF(m2>0,100*m1/m2)`。CloudWatch 算术会将缺失值视为零，并丢弃除以零的结果；不能通过服务 p95 值重建全局 p95。

</details>

5. ADOT/EMF 指标声明在实际遥测中必须包含什么？

   - A) 维度标签和值，由发现/重标记流程或应用提供
   - B) 只在 exporter 配置中列出维度名称
   - C) 在每个标签中放入 secret access key
   - D) 每个节点运行一个副本来采集所有 Pod

<details>
<summary>显示答案</summary>

**答案：A**

`awsemf` 会发送日志事件，以便从中提取传统指标。示例会创建 ClusterName/Namespace/Service 维度，并使用 gauge。现代的直接 OTLP 路径是另一种选择。

</details>

6. 以下哪项成本操作不安全，或与本指南不兼容？

   - A) 衡量摄取量和查询用量
   - B) 为一个由团队负责的日志组设置经批准的保留策略
   - C) 将 EMF/Container Insights 日志转为 Infrequent Access，并缩短所有未设上限的日志组保留期
   - D) 检查重复采集和不必要的标签

<details>
<summary>显示答案</summary>

**答案：C**

Infrequent Access 不支持 EMF 或 Container Insights 日志摄取。缩短保留期可能导致已有历史数据到期删除。高分辨率会增加请求/告警成本，但不意味着指标存储费用统一按十倍计算。

</details>

7. 关于 PutMetricData 辅助函数，哪项说法正确？

   - A) 它会自动创建 IAM 权限
   - B) 它使用调用方提供的客户端和 UTC 时间戳，并将错误传递给调用方
   - C) 重试可以保证业务计数恰好写入一次
   - D) CloudWatch 会自动创建每一种聚合维度组合

<details>
<summary>显示答案</summary>

**答案：B**

自定义指标由完整维度集合标识。PutMetricData 没有幂等性 token；结果不确定时重试可能造成样本重复。示例上报区间计数，并使用 Sum。

</details>

8. 传统指标的 dimensions 与 OTel labels 有何不同？

   - A) 两者数量都不受限制
   - B) 150 个 label 的上限取代了 PutMetricData 的限制
   - C) 传统指标允许 30 个维度；文档所述 OTel 模型最多支持 150 个 label
   - D) label 不会影响 payload 成本或信息暴露

<details>
<summary>显示答案</summary>

**答案：C**

这是两种不同的摄取模型。额外标签会增加 payload 和元数据暴露；仅查看维度名称无法衡量基数。

</details>

9. 关于指标的解释，哪项说法正确？

   - A) `node_network_total_bytes` 的单位是字节/秒；`namespace_number_of_running_pods` 用于统计 Pod 数量
   - B) `cluster_cpu_utilization` 是标准发布的指标
   - C) 正在运行的容器数始终等于正在运行的 Pod 数
   - D) 所有预留容量指标都只属于增强型功能

<details>
<summary>显示答案</summary>

**答案：A**

请核对实际指标目录及维度集合。Pod CPU/内存利用率可以节点限制为分母。增强型可观测性会增加指标和维度，并采用自己的计费模型。

</details>

10. 配置异常或重启告警时必须检查哪些内容？

   - A) 告警创建成功就证明实时遥测正常
   - B) 重启总量始终代表一个时间窗口内的增量
   - C) 无条件从被观测的异常序列中移除 ReturnData
   - D) 历史记录、精确指标身份、总量或增量的含义、缺失数据以及通知送达情况

<details>
<summary>显示答案</summary>

**答案：D**

`ANOMALY_DETECTION_BAND` 会返回模型学习到的预期范围。指南中的异常检测表达式可以同时返回被观测的序列和范围。带有 PodName/Namespace/ClusterName 维度的重启总量，并不会自动表示每五分钟新增五次重启。

</details>

---

[返回指南](../../../observability/metrics/04-cloudwatch-metrics.md)
