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

### 2. What type of events can KEDA scale on that HPA cannot?

- A) CPU utilization
- B) Memory usage
- C) External events like SQS queue depth or Kafka lag
- D) Pod restart counts

<details>
<summary>Show Answer</summary>

**Answer: C) External events like SQS queue depth or Kafka lag**

**Explanation:**
KEDA (Kubernetes Event-Driven Autoscaling) includes scalers for external systems like AWS SQS, Kafka, RabbitMQ, databases, and more. It can scale to zero and react to events outside the Kubernetes metrics system.

</details>

### 3. What is the difference between VPA modes: "Auto" and "Off"?

- A) Auto enables HPA, Off disables it
- B) Auto updates pods in-place, Off only provides recommendations
- C) Auto requires restart, Off is instant
- D) Auto uses Spot instances, Off uses On-Demand

<details>
<summary>Show Answer</summary>

**Answer: B) Auto updates pods in-place, Off only provides recommendations**

**Explanation:**
VPA "Auto" mode automatically evicts and recreates pods with updated resource requests. "Off" mode only generates recommendations without making changes, useful for reviewing suggestions before manual implementation.

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
The `controller.kubernetes.io/pod-deletion-cost` annotation assigns a cost value to pods. During scale-down, pods with lower deletion cost are terminated first. This helps preserve pods running important workloads or those with cached data.

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
HPA calculates desired replicas by comparing current metric values to target values, then scaling proportionally. The ceiling function ensures at least one additional replica is added when scaling up.

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
Spot interruption handling combines AWS Node Termination Handler (or Karpenter's native handling), Pod Disruption Budgets to ensure availability, adequate termination grace periods, and workload design that handles preemption gracefully.

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
Kubernetes 1.27+ supports in-place vertical scaling through the `resizePolicy` field, allowing CPU and memory changes without pod restart. VPA can leverage this for less disruptive resource adjustments.

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
Metrics-server only provides CPU and memory metrics. Prometheus Adapter exposes any Prometheus metric through the custom.metrics.k8s.io API, enabling HPA to scale on application metrics like requests per second, queue depth, or latency.

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
HPA and VPA can conflict if both try to manage the same resource dimension. A common pattern is using HPA for horizontal scaling based on CPU and VPA in recommendation mode for memory, or using the VPA "Initial" mode which only sets resources at pod creation.

</details>
