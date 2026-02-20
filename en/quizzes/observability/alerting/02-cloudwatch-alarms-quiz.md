# CloudWatch Alarms Quiz

A quiz to test your understanding of CloudWatch Alarms.

---

1. What are the three states of a CloudWatch Alarm?
   - A) Active, Inactive, Pending
   - B) OK, ALARM, INSUFFICIENT_DATA
   - C) Normal, Warning, Critical
   - D) Green, Yellow, Red

<details>
<summary>Show Answer</summary>

**Answer: B) OK, ALARM, INSUFFICIENT_DATA**

**Explanation:**
CloudWatch Alarms have three states:
- **OK**: Metric is within normal range
- **ALARM**: Metric has violated the defined threshold
- **INSUFFICIENT_DATA**: Not enough data to evaluate the alarm

These states automatically transition based on metric values and alarm configuration.

</details>

---

2. What is the difference between `evaluation-periods` and `datapoints-to-alarm` settings in CloudWatch Alarms?
   - A) Both settings perform the same function
   - B) evaluation-periods is the number of evaluation periods, datapoints-to-alarm is the number of datapoints required to trigger ALARM state
   - C) evaluation-periods is in seconds, datapoints-to-alarm is in minutes
   - D) evaluation-periods is the metric collection interval, datapoints-to-alarm is the notification interval

<details>
<summary>Show Answer</summary>

**Answer: B) evaluation-periods is the number of evaluation periods, datapoints-to-alarm is the number of datapoints required to trigger ALARM state**

**Explanation:**
- `evaluation-periods`: Number of periods used to evaluate the alarm (e.g., 3)
- `datapoints-to-alarm`: Number of datapoints that must violate the threshold to transition to ALARM state (e.g., 2)

For example, with evaluation-periods=3 and datapoints-to-alarm=2, it means "ALARM if threshold is violated in 2 or more of the 3 periods". This is called "M of N" alarms.

</details>

---

3. What is the correct expression to calculate ALB error rate in CloudWatch Metric Math?
   - A) `errors + requests`
   - B) `(errors / requests) * 100`
   - C) `errors - requests`
   - D) `RATE(errors)`

<details>
<summary>Show Answer</summary>

**Answer: B) `(errors / requests) * 100`**

**Explanation:**
Error Rate is calculated by dividing the number of errors by the total number of requests and multiplying by 100 to get a percentage. CloudWatch Metric Math allows combining multiple metrics for such calculations, and the result can be used as an alarm condition.

```
errors = HTTPCode_Target_5XX_Count
requests = RequestCount
error_rate = (errors / requests) * 100
```

</details>

---

4. Which statement about Composite Alarms is NOT correct?
   - A) Can combine multiple Metric Alarms to define complex conditions
   - B) Can use AND, OR, NOT logical operators
   - C) Can include other Composite Alarms within a Composite Alarm
   - D) Composite Alarms can define their own metrics

<details>
<summary>Show Answer</summary>

**Answer: D) Composite Alarms can define their own metrics**

**Explanation:**
Composite Alarms do not define their own metrics. Instead, they combine the states of existing Metric Alarms to create complex alarm conditions. Composite Alarm rules are composed of functions like `ALARM(alarm-name)`, `OK(alarm-name)`, and AND, OR, NOT operators. Composite Alarms can also be nested within other Composite Alarms.

</details>

---

5. Which statement correctly describes how CloudWatch Anomaly Detection works?
   - A) Detects anomalies based on fixed thresholds
   - B) Uses machine learning to learn expected metric ranges and alerts when they are exceeded
   - C) Detects anomalies by analyzing correlations with other metrics
   - D) Alerts when patterns don't match user-defined patterns

<details>
<summary>Show Answer</summary>

**Answer: B) Uses machine learning to learn expected metric ranges and alerts when they are exceeded**

**Explanation:**
CloudWatch Anomaly Detection uses machine learning algorithms to analyze historical metric data and learns patterns such as time-of-day and day-of-week variations. Based on this, it generates an expected band, and when actual metric values fall outside this range, they are detected as anomalies. The `ANOMALY_DETECTION_BAND(metric, stddev)` function can be used to adjust the standard deviation multiplier.

</details>

---

6. What does the `notBreaching` option for `treat-missing-data` in CloudWatch Alarms mean?
   - A) Trigger an alarm when data is missing
   - B) Maintain the previous state when data is missing
   - C) Treat missing data as not violating the threshold
   - D) Transition to INSUFFICIENT_DATA state when data is missing

<details>
<summary>Show Answer</summary>

**Answer: C) Treat missing data as not violating the threshold**

**Explanation:**
The meanings of `treat-missing-data` option values:
- `notBreaching`: Treat missing data as not violating the threshold (consider as OK)
- `breaching`: Treat missing data as violating the threshold (consider as ALARM)
- `ignore`: Maintain current state
- `missing`: Transition to INSUFFICIENT_DATA state

Generally, `notBreaching` is recommended to prevent unnecessary alerts due to missing data.

</details>

---

7. Which action CANNOT be directly executed as a CloudWatch Alarm Action?
   - A) EC2 instance stop/start/reboot
   - B) Auto Scaling policy trigger
   - C) Send message to SNS topic
   - D) EKS pod restart

<details>
<summary>Show Answer</summary>

**Answer: D) EKS pod restart**

**Explanation:**
CloudWatch Alarm Actions can directly execute the following AWS native operations:
- EC2 Actions: Stop, start, reboot, recover, terminate
- Auto Scaling Actions: Trigger scale out/in policies
- SNS Actions: Send messages to topics

EKS pod restart is not directly supported and must be implemented indirectly through the SNS -> Lambda -> Kubernetes API chain.

</details>

---

8. What is the metric for monitoring pod restart count in an EKS cluster in Container Insights?
   - A) pod_restart_count
   - B) pod_number_of_container_restarts
   - C) container_restart_total
   - D) kube_pod_container_status_restarts

<details>
<summary>Show Answer</summary>

**Answer: B) pod_number_of_container_restarts**

**Explanation:**
Key EKS metrics in Container Insights:
- `pod_number_of_container_restarts`: Container restart count within a pod
- `pod_cpu_utilization`: Pod CPU utilization
- `pod_memory_utilization`: Pod memory utilization
- `node_cpu_utilization`: Node CPU utilization
- `cluster_node_count`: Cluster node count

These metrics are available in the `ContainerInsights` namespace.

</details>

---

9. Which is NOT a recommended practice for CloudWatch Alarms cost optimization?
   - A) Use Standard Resolution (60 seconds) for non-critical alerts
   - B) Consolidate multiple Metric Alarms into Composite Alarms
   - C) Use High Resolution (10 seconds) for all alerts
   - D) Regularly delete unused alarms

<details>
<summary>Show Answer</summary>

**Answer: C) Use High Resolution (10 seconds) for all alerts**

**Explanation:**
High Resolution alarms cost 3x more than Standard Resolution ($0.30 vs $0.10/alarm/month). For cost optimization:
- Use High Resolution only for Critical alerts
- Use Standard Resolution for Warning/Info alerts
- Consolidate related alarms into Composite Alarms
- Regularly delete unused alarms
- Use Anomaly Detection only when needed (additional cost of $0.30/metric/month)

</details>

---

10. When integrating EventBridge with CloudWatch Alarms for automated response, what is the `detail-type` for detecting alarm state changes?
    - A) "AWS CloudWatch Alarm"
    - B) "CloudWatch Alarm State Change"
    - C) "CloudWatch Metric Alarm"
    - D) "AWS Alarm Notification"

<details>
<summary>Show Answer</summary>

**Answer: B) "CloudWatch Alarm State Change"**

**Explanation:**
Event pattern for detecting CloudWatch Alarm state changes in EventBridge:
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

Using this pattern, you can trigger Lambda functions, Step Functions, SSM Automation, etc. when alarm state changes to ALARM to implement automated response.

</details>

---

## Additional Learning Resources

- [Amazon CloudWatch Alarms Documentation](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/AlarmThatSendsEmail.html)
- [CloudWatch Metrics Math](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/using-metric-math.html)
- [CloudWatch Anomaly Detection](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Anomaly_Detection.html)
- [Container Insights Metrics](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Container-Insights-metrics-EKS.html)
