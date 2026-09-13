# CloudWatch Alarms 测验

关于经典 CloudWatch 指标告警和复合告警的测验，已于 2026-09-13 根据官方文档审阅。

---

1. 经典 CloudWatch 指标告警的三种状态是什么？
   - A) Active、Inactive、Pending
   - B) OK、ALARM、INSUFFICIENT_DATA
   - C) Normal、Warning、Critical
   - D) Green、Yellow、Red

<details>
<summary>显示答案</summary>

**答案：B) OK、ALARM、INSUFFICIENT_DATA**

**说明：**
CloudWatch Alarms 有三种状态：
- **OK**：指标处于正常范围内
- **ALARM**：指标违反了定义的阈值
- **INSUFFICIENT_DATA**：没有足够的数据来评估告警

这些状态会根据指标值和告警配置自动转换。

</details>

---

2. CloudWatch Alarms 中的 `evaluation-periods` 和 `datapoints-to-alarm` 设置有什么区别？
   - A) 两个设置执行相同的功能
   - B) evaluation-periods 是评估周期的数量，datapoints-to-alarm 是触发 ALARM 状态所需的数据点数量
   - C) evaluation-periods 以秒为单位，datapoints-to-alarm 以分钟为单位
   - D) evaluation-periods 是指标采集间隔，datapoints-to-alarm 是通知间隔

<details>
<summary>显示答案</summary>

**答案：B) evaluation-periods 是评估周期的数量，datapoints-to-alarm 是触发 ALARM 状态所需的数据点数量**

**说明：**
- `evaluation-periods`：用于评估告警的周期数量（例如，3）
- `datapoints-to-alarm`：必须违反阈值才能转换为 ALARM 状态的数据点数量（例如，2）

例如，当 evaluation-periods=3 且 datapoints-to-alarm=2 时，表示“在 3 个周期中有 2 个或更多周期违反阈值时进入 ALARM”。这称为“M of N”告警。

</details>

---

3. 在 CloudWatch Metric Math 中，当请求数为正数时，ALB 目标错误率的基本比率是什么？
   - A) `errors + requests`
   - B) `(errors / requests) * 100`
   - C) `errors - requests`
   - D) `RATE(errors)`

<details>
<summary>显示答案</summary>

**答案：B) `(errors / requests) * 100`**

**说明：**
错误率的计算方法是：将错误数量除以请求总数，再乘以 100 得到百分比。分母统计的是转发到目标的请求，而不是每个由 ALB 生成的失败。请分别定义零请求、缺少 5xx 以及缺少采集数据时的处理方式。

```
errors = HTTPCode_Target_5XX_Count
requests = RequestCount
error_rate = (errors / requests) * 100
```

</details>

---

4. 关于 Composite Alarms，以下哪项说法不正确？
   - A) 可以组合多个 Metric Alarms 来定义复杂条件
   - B) 可以使用 AND、OR、NOT 逻辑运算符
   - C) 可以在一个 Composite Alarm 中包含其他 Composite Alarms
   - D) Composite Alarms 可以定义自己的指标

<details>
<summary>显示答案</summary>

**答案：D) Composite Alarms 可以定义自己的指标**

**说明：**
Composite Alarms 不会定义自己的指标。相反，它们组合现有 Metric Alarms 的状态来创建复杂的告警条件。Composite Alarm 规则由 `ALARM(alarm-name)`、`OK(alarm-name)` 等函数以及 AND、OR、NOT 运算符组成。Composite Alarms 也可以嵌套在其他 Composite Alarms 中。

</details>

---

5. 以下哪项说法正确描述了 CloudWatch Anomaly Detection 的工作方式？
   - A) 基于固定阈值检测异常
   - B) 使用机器学习了解预期指标范围，并在超出范围时发出告警
   - C) 通过分析与其他指标的相关性检测异常
   - D) 当模式与用户定义的模式不匹配时发出告警

<details>
<summary>显示答案</summary>

**答案：B) 使用机器学习了解预期指标范围，并在超出范围时发出告警**

**说明：**
CloudWatch Anomaly Detection 使用机器学习算法分析历史指标数据，并学习一天中不同时间和一周中不同日期的变化等模式。基于此，它会生成预期区间；当实际指标值落在该范围之外时，就会被检测为异常。`ANOMALY_DETECTION_BAND(metric, stddev)` 参数控制区间宽度；它并不保证固定的 95% 或 99.7% 置信区间。

</details>

---

6. CloudWatch Alarms 中 `treat-missing-data` 的 `notBreaching` 选项是什么意思？
   - A) 当数据缺失时触发告警
   - B) 当数据缺失时保持先前状态
   - C) 将缺失数据视为未违反阈值
   - D) 当数据缺失时转换为 INSUFFICIENT_DATA 状态

<details>
<summary>显示答案</summary>

**答案：C) 将缺失数据视为未违反阈值**

**说明：**
`treat-missing-data` 选项值的含义：
- `notBreaching`：将缺失数据视为未违反阈值（视为 OK）
- `breaching`：将缺失数据视为违反阈值（视为 ALARM）
- `ignore`：保持当前状态
- `missing`：当所有评估数据都缺失时为 INSUFFICIENT_DATA

应根据指标语义进行选择。`notBreaching` 可能适合稀疏的错误计数，但可能掩盖缺失的心跳信号。对于具有 EC2 变更操作的告警，请使用 `missing`，并且仅在 ALARM 状态触发它们。足够的额外真实数据点优先于缺失数据填充。

</details>

---

7. 以下哪项操作不能作为 CloudWatch Alarm Action 直接执行？
   - A) EC2 实例停止/终止/重启/恢复
   - B) Auto Scaling 策略触发
   - C) 向 SNS 主题发送消息
   - D) EKS Pod 重启

<details>
<summary>显示答案</summary>

**答案：D) EKS Pod 重启**

**说明：**
CloudWatch Alarm Actions 可以直接执行以下 AWS 原生操作：
- EC2 Actions：停止、重启、恢复、终止（启动不是直接操作）
- Auto Scaling Actions：触发扩缩容策略
- SNS Actions：向主题发送消息

不直接支持 EKS Pod 重启；该操作需要单独授权的 Lambda/工作流以及 Kubernetes API 路径。

</details>

---

8. 在 Container Insights 中，用于监控 EKS 集群内 Pod 重启次数的指标是什么？
   - A) pod_restart_count
   - B) pod_number_of_container_restarts
   - C) container_restart_total
   - D) kube_pod_container_status_restarts

<details>
<summary>显示答案</summary>

**答案：B) pod_number_of_container_restarts**

**说明：**
Container Insights 中的关键 EKS 指标：
- `pod_number_of_container_restarts`：Pod 的累计容器重启次数；需要 ClusterName、Namespace 和 PodName
- `pod_cpu_utilization`：Pod CPU 利用率
- `pod_memory_utilization`：Pod 内存利用率
- `node_cpu_utilization`：Node CPU 利用率
- `cluster_node_count`：集群 Node 数量

这些指标可在 `ContainerInsights` 命名空间中获取。

</details>

---

9. 以下哪项不是 CloudWatch Alarms 成本优化的推荐做法？
   - A) 对非关键告警使用 Standard Resolution（60 秒）
   - B) 考虑已评估指标和保留的子告警费用
   - C) 对所有告警使用 High Resolution（10 秒）
   - D) 定期删除未使用的告警

<details>
<summary>显示答案</summary>

**答案：C) 对所有告警使用 High Resolution（10 秒）**

**说明：**
仅当延迟要求和采集分辨率合理时才选择高分辨率。60 秒是标准分辨率。复合告警会保留其子告警并增加费用；减少通知噪声并不会自动降低成本。异常告警包含被评估的指标以及上限/下限区间指标。请查看实际 Region 的当前定价。

</details>

---

10. 在将 EventBridge 与 CloudWatch Alarms 集成以实现自动响应时，用于检测告警状态变化的 `detail-type` 是什么？
    - A) "AWS CloudWatch Alarm"
    - B) "CloudWatch Alarm State Change"
    - C) "CloudWatch Metric Alarm"
    - D) "AWS Alarm Notification"

<details>
<summary>显示答案</summary>

**答案：B) "CloudWatch Alarm State Change"**

**说明：**
用于在 EventBridge 中检测 CloudWatch Alarm 状态变化的事件模式：
```json
{
  "source": ["aws.cloudwatch"],
  "detail-type": ["CloudWatch Alarm State Change"],
  "detail": {
    "state": {
      "value": ["ALARM"]
    }
  }
}
```

使用此模式，当告警状态变为 ALARM 时，可以触发 Lambda 函数、Step Functions、SSM Automation 等来实现自动响应。

</details>

---

## 附加学习资源

- [Amazon CloudWatch Alarms 文档](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/AlarmThatSendsEmail.html)
- [CloudWatch Metrics Math](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/using-metric-math.html)
- [CloudWatch Anomaly Detection](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Anomaly_Detection.html)
- [Container Insights 指标](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Container-Insights-metrics-EKS.html)
