# AWS X-Ray Quiz

> **Last Updated**: September 13, 2026

[AWS X-Ray](../../../observability/tracing/02-xray.md)

---

1. Which behavior is NOT automatically supplied by an X-Ray trace pipeline?
   - A) Service dependency visualization from collected traces
   - B) Distributed request tracing
   - C) Collection of every application's ordinary log files
   - D) Analysis of collected span timings

<details>
<summary>Show Answer</summary>

**Answer: C) Collection of every application's ordinary log files**

**Explanation:**

Tracing does not configure a general application-log collector. CloudWatch Transaction Search can store structured spans in aws/spans, but this is distinct from collecting all ordinary application logs. Metrics/logs need their own configured pipelines and access controls.

</details>

---

2. For the legacy daemon path, which Kubernetes workload can run a daemon on each eligible EC2 worker?
   - A) Deployment
   - B) StatefulSet
   - C) DaemonSet
   - D) Job

<details>
<summary>Show Answer</summary>

**Answer: C) DaemonSet**

**Explanation:**

DaemonSet selects eligible nodes; it is not supported on EKS Fargate. A ClusterIP Service may select a daemon on another node, so DaemonSet placement alone does not guarantee node-local or lossless UDP delivery. X-Ray SDKs/daemon are in maintenance mode; the guide uses a separate OpenTelemetry collector Deployment for new instrumentation.

</details>

---

3. Which is NOT a field of an X-Ray centralized sampling rule?
   - A) FixedRate
   - B) ReservoirSize
   - C) Priority
   - D) RetentionDays

<details>
<summary>Show Answer</summary>

**Answer: D) RetentionDays**

**Explanation:**

FixedRate, ReservoirSize and Priority are sampling fields. RetentionDays is not a sampling-rule parameter. A reservoir is not a guarantee of a minimum number of traces when traffic is absent. Rules require a compatible remote sampler; head sampling cannot select a response error that has not happened yet.

</details>

---

4. Which statement correctly distinguishes X-Ray annotations and metadata?
   - A) Every segment independently receives 100 indexed annotations
   - B) Annotations are indexed for X-Ray filtering; unindexed metadata remains stored and accessible
   - C) Annotations accept only strings
   - D) Metadata is automatically redacted

<details>
<summary>Show Answer</summary>

**Answer: B) Annotations are indexed for X-Ray filtering; unindexed metadata remains stored and accessible**

**Explanation:**

X-Ray indexes up to50annotations per trace. Metadata is not indexed as annotations, but unindexed does not mean secret or inaccessible. Use deliberate bounded fields and remove sensitive payloads, identifiers, tokens and SQL parameters before collection. index_all_attributes=false is not a redaction processor.

</details>

---

5. Which statement about ADOT Collector is false?
   - A) It accepts supported OpenTelemetry protocols
   - B) It can connect supported pipelines to multiple backends
   - C) Declaring an unused CloudWatch Logs exporter automatically converts traces into logs
   - D) Its released component inventory must be checked

<details>
<summary>Show Answer</summary>

**Answer: C) Declaring an unused CloudWatch Logs exporter automatically converts traces into logs**

**Explanation:**

Receivers, processors and exporters must be connected in the appropriate logs/metrics/traces pipeline. ADOT includes AWS integrations such as awsxray, so AWS-specific behavior is not exclusive to the legacy daemon. Do not assume that every upstream Contrib exporter exists in the selected ADOT release.

</details>

---

6. What does the red traffic category represent on the X-Ray/CloudWatch trace map?
   - A) Every slow request
   - B) High traffic volume
   - C) Server faults such as HTTP5xx
   - D) Newly discovered services

<details>
<summary>Show Answer</summary>

**Answer: C) Server faults such as HTTP5xx**

**Explanation:**

Red represents server faults, yellow client errors, purple throttling such as HTTP429, and green successful traffic. These categories are not arbitrary latency thresholds or a claim that every red service has crossed a user-defined high-error-rate alarm.

</details>

---

7. What is required to send OpenTelemetry spans through the guide's X-Ray collection path?
   - A) Every producer must use the legacy X-Ray SDK
   - B) A compatible, authenticated OTLP collector/export pipeline with the correct AWS identity
   - C) Every application must install a CloudWatch Agent
   - D) Every EKS Pod must install a Lambda Layer

<details>
<summary>Show Answer</summary>

**Answer: B) A compatible, authenticated OTLP collector/export pipeline with the correct AWS identity**

**Explanation:**

The guide sends OTLP with mTLS to ADOT, whose awsxray exporter calls the signed classic X-Ray API. X-Ray supports W3C128-bit IDs; a special X-Ray ID generator/propagator is not universally mandatory. The alternative native OTLP HTTPS endpoint requires SigV4 and Transaction Search. Configure propagation for the actual integration.

</details>

---

8. Which X-Ray response-time filter selects values strictly greater than two seconds?
   - A) `responsetime > 2000`
   - B) `responsetime > 2`
   - C) `responsetime >= 2`
   - D) `time > 2s`

<details>
<summary>Show Answer</summary>

**Answer: B) `responsetime > 2`**

**Explanation:**

Response-time values are in seconds. >2 excludes exactly2seconds; >=2 includes it. These are X-Ray filter expressions, not shell commands or Logs Insights QL. duration is also a documented X-Ray keyword and must not be presented as an invented invalid keyword.

</details>

---

9. What does merely opening the CloudWatch trace map NOT establish?
   - A) A view of already collected trace dependencies
   - B) Correlation with configured metrics/alarms
   - C) Automatic instrumentation and successful collection of every application
   - D) Links to appropriately correlated logs

<details>
<summary>Show Answer</summary>

**Answer: C) Automatic instrumentation and successful collection of every application**

**Explanation:**

Instrumentation, collection, identity and correlation must be configured separately. The former ServiceLens and X-Ray map are combined in the CloudWatch trace map. Existing telemetry can be correlated there, but an unmounted ConfigMap or an empty view is not evidence that agents and applications are configured.

</details>

---

10. What is the purpose of X-Ray Groups?
   - A) Replacing IAM authorization
   - B) Grouping matching traces for analysis and associated metrics/alarms
   - C) Assigning AWS billing ownership automatically
   - D) Setting retention through a sampling rule

<details>
<summary>Show Answer</summary>

**Answer: B) Grouping matching traces for analysis and associated metrics/alarms**

**Explanation:**

Groups select traces with filter expressions. Review the resulting metrics and configure CloudWatch alarms separately. Creating a group does not instrument producers, override sampling, define IAM isolation or prove an end-to-end alert has fired.

</details>

---
