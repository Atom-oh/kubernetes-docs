# CloudWatch Alarms 测验

用于测试你对 CloudWatch Alarms 理解程度的测验。

---

1. CloudWatch Alarm 有哪三种状态？
   - A) Active, Inactive, Pending
   - B) OK, ALARM, INSUFFICIENT_DATA
   - C) Normal, Warning, Critical
   - D) Green, Yellow, Red

<details>
<summary>显示答案</summary>

**答案：B) OK, ALARM, INSUFFICIENT_DATA**

**说明：**
CloudWatch Alarms 有三种状态：
- **OK**：指标处于正常范围内
- **ALARM**：指标违反了已定义的阈值
- **INSUFFICIENT_DATA**：没有足够的数据来评估 Alarm

这些状态会根据指标值和 Alarm 配置自动转换。

</details>

---

2. CloudWatch Alarms 中的 `evaluation-periods` 与 `datapoints-to-alarm` 设置有什么区别？
   - A) 两项设置执行相同的功能
   - B) evaluation-periods 是评估周期数，datapoints-to-alarm 是触发 ALARM 状态所需的数据点数量
   - C) evaluation-periods 以秒为单位，datapoints-to-alarm 以分钟为单位
   - D) evaluation-periods 是指标收集间隔，datapoints-to-alarm 是通知间隔

<details>
<summary>显示答案</summary>

**答案：B) evaluation-periods 是评估周期数，datapoints-to-alarm 是触发 ALARM 状态所需的数据点数量**

**说明：**
- `evaluation-periods`：用于评估 Alarm 的周期数（例如，3）
- `datapoints-to-alarm`：必须违反阈值才能转换为 ALARM 状态的数据点数量（例如，2）

例如，当 evaluation-periods=3 且 datapoints-to-alarm=2 时，表示“3 个周期中有 2 个或更多周期违反阈值即触发 ALARM”。这称为“M of N” Alarms。

</details>

---

3. 在 CloudWatch Metric Math 中计算 ALB 错误率的正确表达式是什么？
   - A) `errors + requests`
   - B) `(errors / requests) * 100`
   - C) `errors - requests`
   - D) `RATE(errors)`

<details>
<summary>显示答案</summary>

**答案：B) `(errors / requests) * 100`**

**说明：**
错误率的计算方法是将错误数量除以请求总数，再乘以 100 得到百分比。CloudWatch Metric Math 支持组合多个指标来进行此类计算，结果可用作 Alarm 条件。

```
errors = HTTPCode_Target_5XX_Count
requests = RequestCount
error_rate = (errors / requests) * 100
```

</details>

---

4. 关于 Composite Alarms，哪项说法不正确？
   - A) 可以组合多个 Metric Alarms 来定义复杂条件
   - B) 可以使用 AND、OR、NOT 逻辑运算符
   - C) 可以在一个 Composite Alarm 中包含其他 Composite Alarms
   - D) Composite Alarms 可以定义自己的指标

<details>
<summary>显示答案</summary>

**答案：D) Composite Alarms 可以定义自己的指标**

**说明：**
Composite Alarms 不会定义自己的指标。相反，它们组合现有 Metric Alarms 的状态来创建复杂的 Alarm 条件。Composite Alarm 规则由 `ALARM(alarm-name)`、`OK(alarm-name)` 等函数以及 AND、OR、NOT 运算符组成。Composite Alarms 也可以嵌套在其他 Composite Alarms 中。

</details>

---

5. 以下哪项正确描述了 CloudWatch Anomaly Detection 的工作原理？
   - A) 基于固定阈值检测异常
   - B) 使用机器学习来了解预期指标范围，并在超出范围时发出警报
   - C) 通过分析与其他指标的相关性来检测异常
   - D) 当模式与用户定义的模式不匹配时发出警报

<details>
<summary>显示答案</summary>

**答案：B) 使用机器学习来了解预期指标范围，并在超出范围时发出警报**

**说明：**
CloudWatch Anomaly Detection 使用机器学习算法分析历史指标数据，并学习一天中的时间和一周中的日期等变化模式。基于此，它会生成预期范围；当实际指标值超出该范围时，就会被检测为异常。可以使用 `ANOMALY_DETECTION_BAND(metric, stddev)` 函数调整标准差乘数。

</details>

---

6. CloudWatch Alarms 中 `treat-missing-data` 的 `notBreaching` 选项表示什么？
   - A) 数据缺失时触发 Alarm
   - B) 数据缺失时保持先前状态
   - C) 将缺失数据视为未违反阈值
   - D) 数据缺失时转换为 INSUFFICIENT_DATA 状态

<details>
<summary>显示答案</summary>

**答案：C) 将缺失数据视为未违反阈值**

**说明：**
`treat-missing-data` 选项值的含义：
- `notBreaching`：将缺失数据视为未违反阈值（视为 OK）
- `breaching`：将缺失数据视为违反阈值（视为 ALARM）
- `ignore`：保持当前状态
- `missing`：转换为 INSUFFICIENT_DATA 状态

通常建议使用 `notBreaching`，以防止因数据缺失导致不必要的警报。

</details>

---

7. 以下哪项操作不能作为 CloudWatch Alarm Action 直接执行？
   - A) EC2 instance stop/start/reboot
   - B) Auto Scaling policy trigger
   - C) 向 SNS topic 发送消息
   - D) EKS pod restart

<details>
<summary>显示答案</summary>

**答案：D) EKS pod restart**

**说明：**
CloudWatch Alarm Actions 可以直接执行以下 AWS 原生操作：
- EC2 Actions：停止、启动、重启、恢复、终止
- Auto Scaling Actions：触发扩缩容策略
- SNS Actions：向 topics 发送消息

不直接支持 EKS pod restart，必须通过 SNS -> Lambda -> Kubernetes API 链间接实现。

</details>

---

8. 在 Container Insights 中，用于监控 EKS cluster 内 pod restart count 的指标是什么？
   - A) pod_restart_count
   - B) pod_number_of_container_restarts
   - C) container_restart_total
   - D) kube_pod_container_status_restarts

<details>
<summary>显示答案</summary>

**答案：B) pod_number_of_container_restarts**

**说明：**
Container Insights 中的关键 EKS 指标：
- `pod_number_of_container_restarts`：pod 内的 Container restart count
- `pod_cpu_utilization`：Pod CPU utilization
- `pod_memory_utilization`：Pod memory utilization
- `node_cpu_utilization`：Node CPU utilization
- `cluster_node_count`：Cluster node count

这些指标可在 `ContainerInsights` namespace 中使用。

</details>

---

9. 以下哪项不是 CloudWatch Alarms cost optimization 的推荐做法？
   - A) 对非关键警报使用 Standard Resolution（60 秒）
   - B) 将多个 Metric Alarms 整合为 Composite Alarms
   - C) 对所有警报使用 High Resolution（10 秒）
   - D) 定期删除未使用的 Alarms

<details>
<summary>显示答案</summary>

**答案：C) 对所有警报使用 High Resolution（10 秒）**

**说明：**
High Resolution Alarms 的成本是 Standard Resolution 的 3 倍（$0.30 对 $0.10/alarm/month）。为优化成本：
- 仅对 Critical 警报使用 High Resolution
- 对 Warning/Info 警报使用 Standard Resolution
- 将相关 Alarms 整合为 Composite Alarms
- 定期删除未使用的 Alarms
- 仅在需要时使用 Anomaly Detection（额外成本为 $0.30/metric/month）

</details>

---

10. 将 EventBridge 与 CloudWatch Alarms 集成以实现自动化响应时，用于检测 Alarm 状态变化的 `detail-type` 是什么？
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

使用此模式，当 Alarm 状态变为 ALARM 时，可以触发 Lambda functions、Step Functions、SSM Automation 等来实现自动化响应。

</details>

---

## 其他学习资源

- [Amazon CloudWatch Alarms 文档](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/AlarmThatSendsEmail.html)
- [CloudWatch Metrics Math](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/using-metric-math.html)
- [CloudWatch Anomaly Detection](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Anomaly_Detection.html)
- [Container Insights Metrics](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Container-Insights-metrics-EKS.html)
