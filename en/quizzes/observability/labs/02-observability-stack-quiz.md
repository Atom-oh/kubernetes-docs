# Observability Lab Part 2: Observability Stack Quiz

> **Last Updated**: February 2025

Test your understanding of the observability stack concepts covered in the Observability End-to-End Lab Part 2.

---

1. What is the key difference between DaemonSet and Gateway deployment patterns for OpenTelemetry Collector?
   - A) DaemonSet pattern is deprecated and Gateway is the only recommended approach
   - B) DaemonSet runs a collector on each node for local collection while Gateway centralizes collection for cross-node processing
   - C) Gateway pattern cannot handle metrics, only traces
   - D) DaemonSet pattern requires more network bandwidth between clusters

<details>
<summary>Show Answer</summary>

**Answer: B) DaemonSet runs a collector on each node for local collection while Gateway centralizes collection for cross-node processing**

**Explanation:**
The DaemonSet pattern deploys an OTel Collector pod on every node, collecting telemetry locally with low latency and reducing network hops. The Gateway pattern uses a centralized deployment (Deployment or StatefulSet) that receives telemetry from all sources, enabling cross-node processing like tail-based sampling. Often both patterns are combined: DaemonSet collectors gather local data and forward to a Gateway for aggregation and export to backends.

</details>

---

2. How does the OpenTelemetry Collector pipeline architecture organize data flow?
   - A) Exporter → Processor → Receiver
   - B) Receiver → Processor → Exporter
   - C) Processor → Receiver → Exporter
   - D) All components run in parallel without ordering

<details>
<summary>Show Answer</summary>

**Answer: B) Receiver → Processor → Exporter**

**Explanation:**
The OTel Collector pipeline follows a clear data flow: Receivers ingest telemetry data from various sources (OTLP, Prometheus, Jaeger, etc.), Processors transform, filter, or enrich the data (batching, attribute manipulation, sampling), and Exporters send the processed data to backends (Prometheus, Jaeger, cloud services). Multiple pipelines can be defined for different signal types (metrics, traces, logs), and they can share components.

</details>

---

3. How does authentication work when configuring Prometheus remote write to Amazon Managed Prometheus (AMP)?
   - A) Username and password stored in Kubernetes secrets
   - B) IRSA provides IAM credentials, and the SigV4 extension signs requests with AWS Signature Version 4
   - C) API keys generated in the AMP console
   - D) mTLS certificates issued by AWS Certificate Manager

<details>
<summary>Show Answer</summary>

**Answer: B) IRSA provides IAM credentials, and the SigV4 extension signs requests with AWS Signature Version 4**

**Explanation:**
AMP uses AWS IAM for authentication. The remote write component (Prometheus, OTel Collector, or Grafana Agent) uses IRSA to obtain temporary IAM credentials. The SigV4 (AWS Signature Version 4) extension or proxy signs each request with these credentials. This approach leverages AWS's identity infrastructure, eliminating the need to manage long-lived credentials and providing audit trails through CloudTrail.

</details>

---

4. How is VictoriaMetrics compatible with Prometheus?
   - A) It requires data migration tools to import Prometheus data
   - B) It implements the Prometheus remote write/read API and supports PromQL for queries
   - C) It only works as a Prometheus sidecar
   - D) Compatibility requires a paid enterprise license

<details>
<summary>Show Answer</summary>

**Answer: B) It implements the Prometheus remote write/read API and supports PromQL for queries**

**Explanation:**
VictoriaMetrics is designed as a drop-in replacement for Prometheus storage. It implements the Prometheus remote write and remote read APIs, allowing any Prometheus-compatible client to send metrics and any PromQL-compatible tool to query them. It extends PromQL with MetricsQL for additional functions. This compatibility means existing Grafana dashboards, alerting rules, and recording rules work without modification.

</details>

---

5. What characterizes Grafana Mimir's single binary mode?
   - A) It only supports single-tenant deployments
   - B) All Mimir components (ingester, querier, compactor, etc.) run in a single process for simplified deployment
   - C) It cannot scale horizontally
   - D) Single binary mode disables long-term storage

<details>
<summary>Show Answer</summary>

**Answer: B) All Mimir components (ingester, querier, compactor, etc.) run in a single process for simplified deployment**

**Explanation:**
Mimir's single binary mode (monolithic mode) runs all components—distributor, ingester, querier, query-frontend, compactor, store-gateway, and ruler—in a single process. This simplifies deployment and operations for smaller environments. Despite running in one process, it can still scale horizontally by running multiple replicas. For larger deployments, components can be separated into microservices mode for independent scaling.

</details>

---

6. What are the components in Grafana Loki's SimpleScalable deployment mode?
   - A) Only a single read-write pod
   - B) Separate read, write, and backend components that can scale independently
   - C) Ingester and querier only, with external compactor
   - D) Monolithic mode with automatic sharding

<details>
<summary>Show Answer</summary>

**Answer: B) Separate read, write, and backend components that can scale independently**

**Explanation:**
Loki's SimpleScalable mode (also called Simple Scalable Deployment or SSD) divides components into three targets: Write (distributor, ingester), Read (query-frontend, querier), and Backend (compactor, index-gateway, ruler). This allows independent scaling—write path scales with ingestion volume, read path scales with query load. It's a middle ground between monolithic (single binary) and microservices (fully distributed) modes, balancing operational simplicity with scalability.

</details>

---

7. What are the advantages of using ClickHouse as a log store compared to traditional solutions?
   - A) ClickHouse only supports structured JSON logs
   - B) Column-oriented storage, high compression, and fast analytical queries on large log volumes
   - C) It requires less storage but has slower query performance
   - D) ClickHouse is primarily designed for metrics, not logs

<details>
<summary>Show Answer</summary>

**Answer: B) Column-oriented storage, high compression, and fast analytical queries on large log volumes**

**Explanation:**
ClickHouse is a column-oriented OLAP database optimized for analytical queries. For log storage, this means: excellent compression ratios (often 10x better than row-based stores) because similar data in columns compresses well, extremely fast aggregation queries across billions of log entries, and efficient filtering on specific columns without reading entire rows. These characteristics make it cost-effective for high-volume log storage with interactive query performance.

</details>

---

8. What are the key differences between FluentBit and Grafana Alloy for log collection?
   - A) FluentBit is written in Go while Alloy is written in C
   - B) FluentBit is lightweight and focused on log forwarding while Alloy is a unified telemetry collector supporting metrics, logs, traces, and profiles
   - C) Alloy only supports Grafana backends while FluentBit is vendor-agnostic
   - D) FluentBit requires more memory than Alloy for equivalent workloads

<details>
<summary>Show Answer</summary>

**Answer: B) FluentBit is lightweight and focused on log forwarding while Alloy is a unified telemetry collector supporting metrics, logs, traces, and profiles**

**Explanation:**
FluentBit is a lightweight, high-performance log processor and forwarder written in C, designed for resource-constrained environments. Grafana Alloy (evolution of Grafana Agent) is a unified observability collector that handles all telemetry signals—metrics, logs, traces, and profiles. Alloy uses a component-based configuration model and integrates tightly with Grafana's ecosystem. Choose FluentBit for minimal footprint log forwarding; choose Alloy for unified collection across all signal types.

</details>

---

9. How do you configure Tempo-Loki TraceID derived field correlation?
   - A) Correlation is automatic and requires no configuration
   - B) Configure a derived field in Loki data source that extracts TraceID from logs and links to Tempo using the trace ID
   - C) Install a separate correlation service between Tempo and Loki
   - D) TraceID correlation only works with Jaeger, not Tempo

<details>
<summary>Show Answer</summary>

**Answer: B) Configure a derived field in Loki data source that extracts TraceID from logs and links to Tempo using the trace ID**

**Explanation:**
In Grafana's Loki data source settings, you configure derived fields that use regex to extract trace IDs from log lines. The derived field specifies an internal link to the Tempo data source, using the extracted trace ID as a variable. When viewing logs, clickable links appear next to log lines containing trace IDs, enabling direct navigation from a log entry to its corresponding distributed trace in Tempo.

</details>

---

10. How do you configure Alertmanager to send notifications to AWS SNS?
    - A) Alertmanager has native SNS support requiring only the topic ARN
    - B) Configure an SNS receiver with the topic ARN, region, and IAM authentication via IRSA or access keys
    - C) SNS integration requires a webhook proxy service
    - D) Alertmanager cannot send to SNS; use CloudWatch Alarms instead

<details>
<summary>Show Answer</summary>

**Answer: B) Configure an SNS receiver with the topic ARN, region, and IAM authentication via IRSA or access keys**

**Explanation:**
Alertmanager supports SNS as a native receiver type. Configuration requires the SNS topic ARN, AWS region, and authentication credentials. For EKS deployments, use IRSA by configuring the service account with an IAM role that has `sns:Publish` permission. The receiver configuration includes `sigv4` settings for AWS authentication. This enables direct alert delivery to SNS, which can then fan out to email, SMS, Lambda, SQS, or other SNS subscribers.

</details>
