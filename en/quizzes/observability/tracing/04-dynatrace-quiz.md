# Dynatrace Quiz

Test your understanding of Dynatrace.

---

1. Which is NOT a characteristic of Dynatrace's core technology, OneAgent?
   - A) Full-stack monitoring with a single agent
   - B) Automatic code instrumentation
   - C) Manual configuration required
   - D) Automatic process discovery

<details>
<summary>Show Answer</summary>

**Answer: C) Manual configuration required**

**Explanation:**
OneAgent's key characteristics are automatic discovery and auto-instrumentation. After installation, it automatically discovers and monitors processes, services, and applications on the host without additional manual configuration. This reflects Dynatrace's "Zero-configuration" philosophy.

</details>

---

2. What is the recommended way to deploy Dynatrace in EKS?
   - A) Deploy directly with kubectl apply
   - B) Use Dynatrace Operator
   - C) Deploy only OneAgent with Helm
   - D) Deploy with Lambda function

<details>
<summary>Show Answer</summary>

**Answer: B) Use Dynatrace Operator**

**Explanation:**
The Dynatrace Operator automatically manages the lifecycle of Dynatrace components (OneAgent, ActiveGate, etc.) in Kubernetes environments. Configure declaratively through the DynaKube CR, providing automatic updates, rolling deployments, and status monitoring.

</details>

---

3. Which is NOT a main feature of the Davis AI engine?
   - A) Automatic baseline learning
   - B) Anomaly detection
   - C) Automatic code fixing
   - D) Root cause analysis

<details>
<summary>Show Answer</summary>

**Answer: C) Automatic code fixing**

**Explanation:**
Davis AI automatically learns baselines, detects anomalies, and analyzes root causes of problems. However, it doesn't automatically fix code. Davis diagnoses problems and suggests resolution directions, but actual code fixes must be performed by developers.

</details>

---

4. What is the difference between Cloud Native Full Stack and Classic Full Stack deployment modes in Dynatrace?
   - A) Cloud Native only supports Windows
   - B) Cloud Native uses code module injection
   - C) Classic cannot be used in cloud environments
   - D) Both modes provide identical functionality

<details>
<summary>Show Answer</summary>

**Answer: B) Cloud Native uses code module injection**

**Explanation:**
Cloud Native Full Stack is a lightweight approach that injects code modules into Pods through CSI Driver. Classic Full Stack deploys the full OneAgent on each node as a DaemonSet. Cloud Native has lower resource usage and allows fine-grained control at the Pod level, but has limitations for host-level monitoring.

</details>

---

5. What functionality does Dynatrace's PurePath technology provide?
   - A) Log compression
   - B) Code-level distributed tracing
   - C) Network packet capture
   - D) Database backup

<details>
<summary>Show Answer</summary>

**Answer: B) Code-level distributed tracing**

**Explanation:**
PurePath is Dynatrace's proprietary distributed tracing technology that traces the complete path of requests through the system down to the code level. It records not just service-to-service calls but also method calls within each service, database queries, and external API calls in detail.

</details>

---

6. What is the correct formula for calculating Dynatrace Host Units?
   - A) vCPU + Memory(GB)
   - B) max(Memory(GB) / 16, vCPU / 1.5)
   - C) vCPU * Memory(GB) / 100
   - D) (vCPU + Memory(GB)) / 2

<details>
<summary>Show Answer</summary>

**Answer: B) max(Memory(GB) / 16, vCPU / 1.5)**

**Explanation:**
Dynatrace Host Units are calculated based on whichever is larger between memory and CPU. 16GB of memory or 1.5 vCPU equals 1 Host Unit. For example, a host with 8 vCPU and 32GB RAM is max(2, 5.33) = 5.33 Host Units.

</details>

---

7. Which is NOT a role of Dynatrace ActiveGate?
   - A) Data routing
   - B) Kubernetes API monitoring
   - C) Long-term data storage
   - D) Network zone separation

<details>
<summary>Show Answer</summary>

**Answer: C) Long-term data storage**

**Explanation:**
ActiveGate handles data routing between OneAgent and Dynatrace SaaS, Kubernetes API monitoring, and proxy roles in air-gapped environments. Long-term data storage is handled by Dynatrace's Grail data lakehouse; ActiveGate doesn't store data, only forwards it.

</details>

---

8. What is the purpose of using namespaceSelector in Dynatrace?
   - A) Create namespaces
   - B) Monitor only specific namespaces
   - C) Block communication between namespaces
   - D) Set resource quotas

<details>
<summary>Show Answer</summary>

**Answer: B) Monitor only specific namespaces**

**Explanation:**
Using namespaceSelector in the DynaKube CR allows you to specify only namespaces with specific labels as monitoring targets. This enables monitoring only production environments or selectively monitoring specific team namespaces to optimize costs.

</details>

---

9. What protocol is used when integrating Dynatrace with OpenTelemetry?
   - A) Only gRPC supported
   - B) Only HTTP supported
   - C) OTLP (gRPC and HTTP)
   - D) Only proprietary protocol supported

<details>
<summary>Show Answer</summary>

**Answer: C) OTLP (gRPC and HTTP)**

**Explanation:**
Dynatrace natively supports OpenTelemetry Protocol (OTLP). Using the otlphttp exporter from the OTEL Collector, you can send traces, metrics, and logs to the Dynatrace API endpoint. Both gRPC and HTTP are supported.

</details>

---

10. What functionality does Dynatrace's Smartscape provide?
    - A) Smart alert filtering
    - B) Real-time topology mapping
    - C) Auto-scaling
    - D) Code review

<details>
<summary>Show Answer</summary>

**Answer: B) Real-time topology mapping**

**Explanation:**
Smartscape is Dynatrace's real-time topology mapping technology. It automatically discovers and visualizes relationships between infrastructure (hosts, containers), processes, services, and applications. This helps understand system dependencies and identify the scope of problem impact.

</details>

---
