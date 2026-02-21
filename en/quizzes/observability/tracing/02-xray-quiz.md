# AWS X-Ray Quiz

Test your understanding of AWS X-Ray.

---

1. Which is NOT a main feature of AWS X-Ray?
   - A) Service map visualization
   - B) Distributed tracing
   - C) Log aggregation
   - D) Performance analysis

<details>
<summary>Show Answer</summary>

**Answer: C) Log aggregation**

**Explanation:**
AWS X-Ray provides distributed tracing, service map visualization, and performance analysis. Log aggregation is a CloudWatch Logs feature. X-Ray can integrate with CloudWatch Logs to link traces and logs, but it doesn't collect or store logs itself.

</details>

---

2. What is the recommended way to deploy the X-Ray daemon in EKS?
   - A) Deployment
   - B) StatefulSet
   - C) DaemonSet
   - D) Job

<details>
<summary>Show Answer</summary>

**Answer: C) DaemonSet**

**Explanation:**
Deploying the X-Ray Daemon as a DaemonSet is recommended. A DaemonSet runs one Pod on each node, allowing all application Pods on that node to send trace data to the local X-Ray Daemon. This minimizes network latency and ensures reliable data transmission.

</details>

---

3. Which is NOT a parameter used when setting up centralized sampling rules in X-Ray?
   - A) FixedRate
   - B) ReservoirSize
   - C) Priority
   - D) RetentionDays

<details>
<summary>Show Answer</summary>

**Answer: D) RetentionDays**

**Explanation:**
X-Ray sampling rules include FixedRate (fixed sampling ratio), ReservoirSize (minimum samples per second), and Priority (rule priority). RetentionDays is not a sampling rule parameter but is related to X-Ray data retention settings. The default data retention period is 30 days.

</details>

---

4. What is the difference between Annotation and Metadata in X-Ray?
   - A) Annotation maximum is 100, Metadata is unlimited
   - B) Annotation is indexed and filterable, Metadata is not indexed
   - C) Annotation supports only strings, Metadata supports all types
   - D) Annotation is auto-generated, Metadata is manually added

<details>
<summary>Show Answer</summary>

**Answer: B) Annotation is indexed and filterable, Metadata is not indexed**

**Explanation:**
Annotations are indexed and can be searched using filter expressions in the X-Ray console (maximum 50). Metadata is not indexed and cannot be searched but is used to store detailed information. Use Annotations for important identifiers (user_id, order_id, etc.) and Metadata for detailed information like request/response bodies.

</details>

---

5. Which is NOT an advantage of using the ADOT (AWS Distro for OpenTelemetry) Collector?
   - A) Uses vendor-neutral standards
   - B) Multi-backend support
   - C) X-Ray-specific optimization
   - D) OpenTelemetry protocol support

<details>
<summary>Show Answer</summary>

**Answer: C) X-Ray-specific optimization**

**Explanation:**
The ADOT Collector is vendor-neutral based on OpenTelemetry and can send data to various backends (Prometheus, Jaeger, Datadog, etc.) in addition to X-Ray. X-Ray-specific optimization is a characteristic of the X-Ray Daemon. ADOT's advantages are standardized instrumentation and multi-backend support.

</details>

---

6. When does a node appear red in the X-Ray service map?
   - A) When response time is slow
   - B) When traffic is high
   - C) When error rate is high
   - D) When it's a newly added service

<details>
<summary>Show Answer</summary>

**Answer: C) When error rate is high**

**Explanation:**
Node colors in the X-Ray service map indicate service health status. Red indicates services with high error rates, yellow indicates services with warning-level issues, and green indicates normal services. This allows quick identification of problematic services.

</details>

---

7. What configuration is needed to receive OpenTelemetry trace data in X-Ray?
   - A) Install X-Ray SDK
   - B) Configure AWS X-Ray Propagator and ID Generator
   - C) Install CloudWatch Agent
   - D) Add Lambda Layer

<details>
<summary>Show Answer</summary>

**Answer: B) Configure AWS X-Ray Propagator and ID Generator**

**Explanation:**
To send trace data from OpenTelemetry to X-Ray, you need to configure the AWS X-Ray Propagator (context propagation) and AWS X-Ray ID Generator (generates X-Ray format TraceIDs). This allows generating X-Ray compatible trace data while using OpenTelemetry standards.

</details>

---

8. What is the correct X-Ray filter expression query to find requests with response time over 2 seconds?
   - A) `duration > 2`
   - B) `responsetime > 2`
   - C) `latency >= 2000`
   - D) `time > 2s`

<details>
<summary>Show Answer</summary>

**Answer: B) responsetime > 2**

**Explanation:**
In X-Ray filter expressions, the `responsetime` keyword is used for response time, and the unit is seconds. `responsetime > 2` filters requests that took more than 2 seconds. Other useful filters include `fault = true` (server errors), `error = true` (client errors), and `service("name")` (specific service).

</details>

---

9. Which is NOT a feature provided when integrating X-Ray with CloudWatch ServiceLens?
   - A) Integrated view of traces and metrics
   - B) Display CloudWatch alarms on service map
   - C) Automatic code instrumentation
   - D) Link logs and traces

<details>
<summary>Show Answer</summary>

**Answer: C) Automatic code instrumentation**

**Explanation:**
CloudWatch ServiceLens provides an integrated view of X-Ray traces, CloudWatch metrics, and logs. It displays CloudWatch alarms on the service map and provides features to link logs and traces. However, automatic code instrumentation must be done through X-Ray SDK or OpenTelemetry auto-instrumentation.

</details>

---

10. What is the main purpose of X-Ray Groups?
    - A) User permission management
    - B) Filter-based trace grouping and alerting
    - C) Resource cost allocation
    - D) Data retention policy settings

<details>
<summary>Show Answer</summary>

**Answer: B) Filter-based trace grouping and alerting**

**Explanation:**
X-Ray Groups use filter expressions to group traces. For example, you can create groups for production environments, specific services, error requests, etc. For each group, you can set up CloudWatch alarms to receive alerts for specific conditions (such as increased error rates).

</details>

---
