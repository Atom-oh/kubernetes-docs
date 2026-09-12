# Scaling Strategies Quiz

> **Related Document**: [Scaling Strategies](../../ops/06-scaling-strategies.md)

## Multiple Choice Questions

### 1. What is required to use custom metrics with HPA?

- A) Kubernetes 1.30 or higher
- B) Prometheus Adapter or similar custom metrics server
- C) AWS Auto Scaling integration
- D) Manual pod scaling

<details>
<summary>Show Answer</summary>

**Answer: B) Prometheus Adapter or similar custom metrics server**

**Explanation:**
HPA with custom metrics requires a metrics server that implements the custom.metrics.k8s.io API. Prometheus Adapter queries Prometheus and exposes metrics in the format HPA expects, enabling scaling on application-specific metrics like requests per second.

</details>

### 2. What does KEDA add around the native HPA control loop?

- A) CPU utilization
- B) Memory usage
- C) Event-source scalers and activation/scale-to-zero management
- D) Pod restart counts

<details>
<summary>Show Answer</summary>

**Answer: C) Event-source scalers and activation/scale-to-zero management**

**Explanation:**
KEDA (Kubernetes Event-Driven Autoscaling) includes scalers for external systems like AWS SQS, Kafka, RabbitMQ, databases, and more. It supplies external metrics to HPA and manages activation/zero transitions for supported workloads. HPA itself can also consume external metrics through an adapter; KEDA does not make it incapable of reading them.

</details>

### 3. What is the difference between VPA modes: "Recreate" and "Off"?

- A) Recreate enables HPA, Off disables it
- B) Recreate can evict/recreate Pods; Off only provides recommendations
- C) Recreate guarantees no interruption; Off is instant
- D) Recreate uses Spot instances; Off uses On-Demand

<details>
<summary>Show Answer</summary>

**Answer: B) Recreate can evict/recreate Pods; Off only provides recommendations**

**Explanation:**
VPA 1.7.1 deprecates Auto, which currently behaves like Recreate. Recreate can update by eviction/recreation; Off leaves recommendations for review. Explicit InPlaceOrRecreate and feature-gated InPlace are separate modes with different fallback behavior.

</details>

### 4. What is Pod Deletion Cost and how does it affect scaling?

- A) The financial cost of deleting a pod
- B) An annotation that influences which pods are removed first during scale-down
- C) The time required to delete a pod
- D) Storage costs associated with pod termination

<details>
<summary>Show Answer</summary>

**Answer: B) An annotation that influences which pods are removed first during scale-down**

**Explanation:**
The `controller.kubernetes.io/pod-deletion-cost` annotation assigns a cost value to pods. Within a ReplicaSet, lower costs are preferred after earlier assignment, phase and readiness comparisons. This is best-effort, not protection against eviction, Spot reclamation, Job/StatefulSet behavior or scaling across different Deployments.

</details>

### 5. When using HPA with custom metrics, what is the formula for calculating desired replicas?

- A) currentReplicas + 1
- B) desiredReplicas = ceil(currentReplicas * (currentMetricValue / desiredMetricValue))
- C) maxReplicas / 2
- D) currentMetricValue * targetUtilization

<details>
<summary>Show Answer</summary>

**Answer: B) desiredReplicas = ceil(currentReplicas * (currentMetricValue / desiredMetricValue))**

**Explanation:**
HPA calculates desired replicas by comparing current metric values to target values, then scaling proportionally. This simplified formula assumes usable metrics and ready Pods. Tolerance, missing data, min/max and scaling behavior can prevent or limit an actual change; the ceiling does not guarantee an extra Pod.

</details>

### 6. What is the recommended strategy for Spot node interruption handling?

- A) Ignore interruptions
- B) Use Pod Disruption Budgets and graceful termination with interruption handlers
- C) Only run stateless workloads
- D) Disable Spot instances entirely

<details>
<summary>Show Answer</summary>

**Answer: B) Use Pod Disruption Budgets and graceful termination with interruption handlers**

**Explanation:**
Choose the handling appropriate to the node mode: managed Auto Mode, configured self-managed Karpenter, or a complete Node Termination Handler setup where needed. Avoid duplicate drain controllers. PDBs and grace periods do not prevent Spot loss or guarantee a full two-minute application shutdown window.

</details>

### 7. In KEDA, what does `pollingInterval` configure?

- A) How often pods are restarted
- B) How frequently KEDA checks the external metric source
- C) The delay between scale operations
- D) Health check frequency

<details>
<summary>Show Answer</summary>

**Answer: B) How frequently KEDA checks the external metric source**

**Explanation:**
`pollingInterval` defines how often KEDA queries the external scaler (e.g., SQS, Prometheus) for metric values. Lower intervals provide faster reaction times but increase load on the metric source.

</details>

### 8. What Kubernetes feature enables VPA to resize pods without restart (in newer versions)?

- A) Rolling updates
- B) In-place Pod Vertical Scaling
- C) Blue/green deployment
- D) Canary releases

<details>
<summary>Show Answer</summary>

**Answer: B) In-place Pod Vertical Scaling**

**Explanation:**
In-place Pod resize progressed from alpha in 1.27 to beta in 1.33 and stable in 1.35. Supported VPA modes can use it, but resizePolicy can still require a container restart and capacity/QoS constraints can defer or reject an update.

</details>

### 9. What is the benefit of using Prometheus Adapter over metrics-server for HPA?

- A) Lower resource usage
- B) Support for custom and external metrics beyond CPU/memory
- C) Faster metric collection
- D) Built-in alerting

<details>
<summary>Show Answer</summary>

**Answer: B) Support for custom and external metrics beyond CPU/memory**

**Explanation:**
Metrics-server only provides CPU and memory metrics. Prometheus Adapter exposes configured and available series through the custom.metrics.k8s.io API, enabling HPA to scale on application metrics like requests per second, queue depth, or latency.

</details>

### 10. What should you consider when combining HPA and VPA?

- A) They cannot be used together
- B) Configure them on different resource dimensions (HPA on CPU, VPA on memory)
- C) Always disable HPA when VPA is enabled
- D) They automatically coordinate without configuration

<details>
<summary>Show Answer</summary>

**Answer: B) Configure them on different resource dimensions (HPA on CPU, VPA on memory)**

**Explanation:**
HPA and VPA can conflict if both try to manage the same resource dimension. Options include recommendation-only VPA or workload metrics such as RPS/backlog for HPA while VPA handles sizing. Initial still changes new Pods' requests and therefore does not eliminate CPU-utilization denominator interactions. Validate restart and scheduling effects too.

</details>
