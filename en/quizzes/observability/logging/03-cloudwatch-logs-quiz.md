# CloudWatch Logs Quiz

Test your understanding of Amazon CloudWatch Logs.

---

1. Which is NOT a supported log type in EKS control plane logging?

   - A) api
   - B) audit
   - C) worker
   - D) scheduler

<details>
<summary>Show Answer</summary>

**Answer: C) worker**

**Explanation:**
The EKS control plane supports 5 log types: api, audit, authenticator, controllerManager, and scheduler. Worker node logs are not control plane logs and must be collected separately through Container Insights or FluentBit.

</details>

---

2. Which is the most expensive item in CloudWatch Logs pricing structure?

   - A) Storage
   - B) Ingestion
   - C) Query (Logs Insights)
   - D) S3 Export

<details>
<summary>Show Answer</summary>

**Answer: B) Ingestion**

**Explanation:**
CloudWatch Logs ingestion costs $0.50/GB, which is much higher than storage ($0.03/GB/month) or queries ($0.005/GB scanned). Therefore, filtering unnecessary logs is important for cost optimization.

</details>

---

3. What command in CloudWatch Logs Insights extracts specific fields?

   - A) extract
   - B) parse
   - C) select
   - D) filter

<details>
<summary>Show Answer</summary>

**Answer: B) parse**

**Explanation:**
In CloudWatch Logs Insights, the `parse` command extracts fields matching specific patterns from log messages. Example: `parse @message '"level":"*"' as level`

</details>

---

4. What is the log group path format for logs collected through Container Insights?

   - A) `/aws/eks/cluster-name/logs`
   - B) `/aws/containerinsights/cluster-name/application`
   - C) `/var/log/containers/cluster-name`
   - D) `/kubernetes/cluster-name/logs`

<details>
<summary>Show Answer</summary>

**Answer: B) `/aws/containerinsights/cluster-name/application`**

**Explanation:**
Container Insights creates log groups under the `/aws/containerinsights/{cluster-name}/` path, including application, host, dataplane, and performance log groups.

</details>

---

5. What CloudWatch Logs feature delivers logs to Lambda functions for real-time log processing?

   - A) Log Stream
   - B) Metric Filter
   - C) Subscription Filter
   - D) Log Insight

<details>
<summary>Show Answer</summary>

**Answer: C) Subscription Filter**

**Explanation:**
Subscription Filters deliver logs from log groups in real-time to other services (Lambda, Kinesis Data Firehose, Kinesis Data Streams). You can specify filter patterns to deliver only specific logs.

</details>

---

6. What is the name of the FluentBit OUTPUT plugin for sending logs to CloudWatch Logs?

   - A) cloudwatch
   - B) cloudwatch_logs
   - C) aws_cloudwatch
   - D) cw_logs

<details>
<summary>Show Answer</summary>

**Answer: B) cloudwatch_logs**

**Explanation:**
FluentBit's CloudWatch Logs output plugin is named `cloudwatch_logs`. It is included by default in the `aws-for-fluent-bit` image provided by AWS.

</details>

---

7. What is the correct CloudWatch Logs Insights query to aggregate log counts by time period?

   - A) `stats count(*) group by hour`
   - B) `stats count(*) as log_count by bin(1h)`
   - C) `select count(*) from logs group by hour`
   - D) `aggregate count by time(1h)`

<details>
<summary>Show Answer</summary>

**Answer: B) `stats count(*) as log_count by bin(1h)`**

**Explanation:**
In CloudWatch Logs Insights, time-based aggregation uses the `stats` command and `bin()` function. `bin(1h)` groups data into 1-hour intervals.

</details>

---

8. Which is NOT a recommended strategy for CloudWatch Logs cost optimization?

   - A) Filtering unnecessary logs (healthcheck, etc.)
   - B) Setting different retention periods by environment
   - C) Collecting all logs at DEBUG level
   - D) Archiving long-retention logs to S3

<details>
<summary>Show Answer</summary>

**Answer: C) Collecting all logs at DEBUG level**

**Explanation:**
DEBUG level logs are very detailed and significantly increase log volume. In production environments, collecting only INFO level and above helps with cost optimization.

</details>

---

9. What is the primary purpose of using Metric Filters in CloudWatch Logs?

   - A) Exporting logs to S3
   - B) Creating CloudWatch metrics from log patterns
   - C) Setting log retention periods
   - D) Configuring log encryption

<details>
<summary>Show Answer</summary>

**Answer: B) Creating CloudWatch metrics from log patterns**

**Explanation:**
Metric Filters detect specific patterns (e.g., ERROR) in logs and create CloudWatch metrics. Based on these metrics, you can set up CloudWatch Alarms to receive notifications.

</details>

---

10. Which permission is NOT required for IRSA (IAM Roles for Service Accounts) when setting up Container Insights on an EKS cluster?

    - A) logs:CreateLogGroup
    - B) logs:PutLogEvents
    - C) s3:PutObject
    - D) cloudwatch:PutMetricData

<details>
<summary>Show Answer</summary>

**Answer: C) s3:PutObject**

**Explanation:**
The basic Container Insights setup does not require S3 permissions. Only CloudWatch Logs (logs:*) and CloudWatch Metrics (cloudwatch:PutMetricData) permissions are needed. S3 permissions are only required when setting up separate log exports to S3.

</details>
