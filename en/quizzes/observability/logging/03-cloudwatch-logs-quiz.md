# CloudWatch Logs Quiz

> **Last Updated**: September 13, 2026

[Guide](../../../observability/logging/03-cloudwatch-logs.md)

---

1. Which is not an EKS control-plane log type?

   - A) api
   - B) audit
   - C) worker
   - D) scheduler

<details>
<summary>Show answer</summary>

**Answer: C**

The five types are api, audit, authenticator, controllerManager and scheduler. Worker/application logs and Auto Mode managed-component delivery are separate paths.

</details>

---

2. How should CloudWatch Logs cost drivers be compared?

   - A) Ingestion is always the largest monthly charge
   - B) Storage is always free
   - C) Every S3 delivery path is free
   - D) Compare actual volume, retention, scans, class, Region and downstream charges

<details>
<summary>Show answer</summary>

**Answer: D**

A price per ingested GB cannot alone be ranked against GB-month storage or repeated scan volume. The guide's $1,575 example is hypothetical arithmetic, not current Seoul pricing or a complete bill.

</details>

---

3. Which Logs Insights QL command extracts fields using a glob or regular expression?

   - A) extract
   - B) parse
   - C) select
   - D) filter

<details>
<summary>Show answer</summary>

**Answer: B**

parse extracts fields; jsonParse can parse a JSON message. The collector envelope places application fields under log_processed. Do not assume arbitrary JSON key order in a glob.

</details>

---

4. Which group is used by the manual application collector in this guide?

   - A) /aws/containerinsights/example-eks/application
   - B) /aws/eks/example-eks/logs
   - C) /var/log/containers/example-eks
   - D) Every cluster uses one immutable universal group name

<details>
<summary>Show answer</summary>

**Answer: A**

The configured application group differs from /aws/eks/example-eks/cluster for control-plane logs. The group is prepared first; the collector does not create it or change retention.

</details>

---

5. Which statement about subscription delivery is correct?

   - A) An S3 bucket ARN is a direct subscription-filter destination
   - B) CloudWatch subscription batches work through Firehose's OpenSearch destination
   - C) A subscription can send to Lambda, Kinesis or Firehose; S3 archiving through Firehose is a separate downstream step
   - D) Subscriptions guarantee exactly-once delivery and backfill all history

<details>
<summary>Show answer</summary>

**Answer: C**

The destination API and input format matter. CloudWatch Logs→Firehose→OpenSearch is specifically unsupported. Subscriptions are asynchronous and at least once; export tasks and vended-log delivery are different APIs.

</details>

---

6. What is the native C Fluent Bit output plugin for CloudWatch Logs?

   - A) cloudwatch
   - B) cloudwatch_logs
   - C) aws_cloudwatch
   - D) cw_logs

<details>
<summary>Show answer</summary>

**Answer: B**

cloudwatch_logs is the native plugin. cloudwatch names the older Go plugin. Credentials, the actual ServiceAccount, output group and IAM policy still need to match.

</details>

---

7. Which QL query counts events per hour and sorts the resulting time buckets?

   - A) stats count(*) group by hour
   - B) stats count(*) as log_count by bin(1h) as bucket | sort bucket asc
   - C) select count(*) from logs group by hour
   - D) stats count(*) by bin(1h) | sort @message

<details>
<summary>Show answer</summary>

**Answer: B**

stats changes the available output fields, so sort its bucket alias. The latency percentile function is pct, not percentile, and case-insensitive regex uses (?i) inside the slashes.

</details>

---

8. Which logging policy is unsafe as a default cost-control approach?

   - A) Review filters against records that must be kept
   - B) Set retention through the log group's single owner
   - C) Keep all DEBUG output indefinitely and indiscriminately drop security-relevant records to compensate
   - D) Measure ingestion and scans before changing the design

<details>
<summary>Show answer</summary>

**Answer: C**

Volume controls must preserve required diagnostics and security records. LOG_LEVEL in a ConfigMap has an effect only if the application consumes it. Retention changes can remove data.

</details>

---

9. What does a metric filter do, and what does a zero default mean?

   - A) It exports every historical record to S3
   - B) It derives metrics from new matching logs; default zero applies when logs arrive but no records match
   - C) It always emits zero even when no logs arrive
   - D) It supports every feature in every log class

<details>
<summary>Show answer</summary>

**Answer: B**

This chapter uses a Standard-class JSON filter on $.log_processed.level. With no incoming logs, data can be missing. The alarm checks an error count in two five-minute periods, not an error rate or proof of service health.

</details>

---

10. Which IAM/ownership arrangement fits the manual logs-only collector?

   - A) Give all Pods an administrator role
   - B) Attach a policy to cloudwatch-agent while deploying an unrelated ServiceAccount
   - C) Use only s3:PutObject
   - D) Precreate the group, authorize logs:CreateLogStream/logs:PutLogEvents on its ARN, and map the actual collector ServiceAccount

<details>
<summary>Show answer</summary>

**Answer: D**

The manual profile uses logging/fluent-bit-cloudwatch and an approved IRSA trust. It does not need PutMetricData or broad logs:* for this path. The full observability chart is a separate profile whose Fluent Bit Pods use cloudwatch-agent.

</details>
