# CloudWatch Metrics Quiz

A quiz to test your understanding of CloudWatch Metrics.

---

1. What is the primary function of Amazon CloudWatch Container Insights?
   - A) Container image building
   - B) Container/pod-level monitoring for EKS clusters
   - C) Container orchestration
   - D) CI/CD pipeline management

<details>
<summary>Show Answer</summary>

**Answer: B) Container/pod-level monitoring for EKS clusters**

**Explanation:**
Container Insights is a CloudWatch feature for monitoring containerized workloads in EKS, ECS, and Kubernetes environments. It automatically collects and visualizes cluster, node, pod, and container-level CPU, memory, network, and filesystem metrics.

</details>

---

2. What is the recommended method for deploying CloudWatch Agent to EKS?
   - A) Deploy as a single Pod
   - B) Deploy to all nodes as a DaemonSet
   - C) Deploy as 3 replicas with Deployment
   - D) Deploy as a StatefulSet

<details>
<summary>Show Answer</summary>

**Answer: B) Deploy to all nodes as a DaemonSet**

**Explanation:**
CloudWatch Agent is deployed as a DaemonSet to collect metrics and logs from each node. This ensures consistent collection of system metrics, container metrics, and logs from all nodes.

</details>

---

3. What is the purpose of the `SEARCH()` function in CloudWatch Metric Math?
   - A) Log search
   - B) Dynamically search for metrics matching a pattern
   - C) Alert search
   - D) Dashboard search

<details>
<summary>Show Answer</summary>

**Answer: B) Dynamically search for metrics matching a pattern**

**Explanation:**
The `SEARCH()` function dynamically searches for metrics using namespace, dimension, and metric name patterns. For example, `SEARCH('{AWS/EC2,InstanceId} MetricName="CPUUtilization"', 'Average')` searches for CPU utilization of all EC2 instances.

</details>

---

4. How does CloudWatch Anomaly Detection work?
   - A) Detection based on manually set thresholds
   - B) ML-based automatic anomaly pattern detection
   - C) Log pattern analysis
   - D) Network traffic analysis

<details>
<summary>Show Answer</summary>

**Answer: B) ML-based automatic anomaly pattern detection**

**Explanation:**
CloudWatch Anomaly Detection uses machine learning to learn normal patterns of metrics and automatically detect abnormal values. It generates dynamic expected ranges (bands) considering seasonality, trends, and day-of-week patterns, and identifies anomalies when values fall outside these ranges.

</details>

---

5. When using AWS Distro for OpenTelemetry (ADOT) to send Prometheus metrics to CloudWatch, which exporter is used?
   - A) prometheus-exporter
   - B) awsemf (AWS EMF Exporter)
   - C) cloudwatch-exporter
   - D) metric-exporter

<details>
<summary>Show Answer</summary>

**Answer: B) awsemf (AWS EMF Exporter)**

**Explanation:**
To send Prometheus metrics to CloudWatch in ADOT, use the AWS EMF (Embedded Metric Format) Exporter. This exporter converts metrics to EMF format in CloudWatch Logs and sends them, which CloudWatch then extracts as metrics.

</details>

---

6. Which is NOT a valid method for CloudWatch cost optimization?
   - A) Set log retention periods
   - B) Remove unnecessary high-resolution metrics
   - C) Collect all metrics at 1-second intervals
   - D) Use Infrequent Access log class

<details>
<summary>Show Answer</summary>

**Answer: C) Collect all metrics at 1-second intervals**

**Explanation:**
High-resolution metrics (1-second intervals) are expensive. For cost optimization, collect only necessary metrics at high resolution and most metrics at 60-second intervals (default). Setting log retention periods, filtering unnecessary metrics, and using Infrequent Access log class also help reduce costs.

</details>

---

7. Which API is used to create custom metrics in CloudWatch?
   - A) CreateMetric
   - B) PutMetricData
   - C) PublishMetric
   - D) SendMetric

<details>
<summary>Show Answer</summary>

**Answer: B) PutMetricData**

**Explanation:**
The `PutMetricData` API is used to send custom metrics to CloudWatch. You can specify namespace, metric name, dimensions, value, unit, timestamp, etc. It can be called through AWS SDK or CLI.

</details>

---

8. What is the role of Dimensions in CloudWatch?
   - A) Specify metric units
   - B) Key-value pairs that segment metrics
   - C) Specify alert severity
   - D) Specify log groups

<details>
<summary>Show Answer</summary>

**Answer: B) Key-value pairs that segment metrics**

**Explanation:**
Dimensions are key-value pairs that segment and identify metrics. For example, in EC2 instance metrics, the `InstanceId` dimension identifies specific instances. Up to 30 dimensions can be specified for a single metric.

</details>

---

9. How does Enhanced Container Insights differ from basic Container Insights?
   - A) Provided for free
   - B) Provides additional metrics and more detailed monitoring
   - C) Removes log collection functionality
   - D) Provides only alerting functionality

<details>
<summary>Show Answer</summary>

**Answer: B) Provides additional metrics and more detailed monitoring**

**Explanation:**
Enhanced Container Insights collects more metrics than basic Container Insights. It provides additional information such as reserved CPU/memory capacity, GPU metrics (when applicable), and Kubernetes control plane metrics. It costs more but enables more detailed monitoring.

</details>

---

10. What is the role of the `ANOMALY_DETECTION_BAND()` function in CloudWatch alerts?
    - A) Set fixed thresholds
    - B) Return expected range from anomaly detection model
    - C) Log filtering
    - D) Dashboard creation

<details>
<summary>Show Answer</summary>

**Answer: B) Return expected range from anomaly detection model**

**Explanation:**
The `ANOMALY_DETECTION_BAND()` function returns the expected value range (upper/lower bounds) learned by the anomaly detection model. This range can be used in alerts to trigger notifications when metrics fall outside the expected range. The second argument specifies the standard deviation multiplier to adjust the band width.

</details>
