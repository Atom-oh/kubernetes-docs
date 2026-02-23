# Observability Lab Part 4: Load Testing and Autoscaling Quiz

> **Last Updated**: February 22, 2026

Test your understanding of load testing and autoscaling concepts covered in the Observability End-to-End Lab Part 4.

---

1. What is a Virtual User (VU) in k6, and how do you configure phased load patterns?
   - A) VU is a network connection; phases are configured in JSON files
   - B) VU represents a simulated user executing the test script concurrently; phases are configured using stages with target VUs and duration
   - C) VU is a CPU thread; phases are set via command-line flags only
   - D) VU is a request queue; phases require separate test scripts

<details>
<summary>Show Answer</summary>

**Answer: B) VU represents a simulated user executing the test script concurrently; phases are configured using stages with target VUs and duration**

**Explanation:**
In k6, a Virtual User (VU) is an independent execution context running your test script—each VU simulates a real user making requests. Phased load patterns use the `stages` option in the `options` block: each stage defines a `target` (number of VUs) and `duration` (time to reach that target). For example, ramp up to 100 VUs over 2 minutes, sustain for 5 minutes, then ramp down. This enables realistic load profiles like gradual ramp-up, steady state, and spike testing.

</details>

---

2. What are the key differences between k6 and Locust for load testing?
   - A) k6 is written in Python while Locust is written in Go
   - B) k6 uses JavaScript for test scripts with a Go runtime for performance while Locust uses Python with a distributed architecture
   - C) Locust only supports HTTP/1.1 while k6 supports all protocols
   - D) k6 requires a GUI while Locust is CLI-only

<details>
<summary>Show Answer</summary>

**Answer: B) k6 uses JavaScript for test scripts with a Go runtime for performance while Locust uses Python with a distributed architecture**

**Explanation:**
k6 offers high performance from its Go-based runtime while using familiar JavaScript/ES6 for test scripts, built-in metrics, and excellent CI/CD integration. Locust uses Python for test scripts, making it accessible to Python developers and highly flexible for complex test logic, with a web UI for real-time monitoring and easy distributed testing. k6 generally handles higher load per instance; Locust offers more flexibility in test logic and a more visual experience.

</details>

---

3. How does KEDA's SQS scaler determine when to scale pods?
   - A) It scales based on CPU utilization of existing pods
   - B) It queries SQS queue metrics and scales pods based on the ratio of queue messages to a configured target value per pod
   - C) It scales based on the age of messages in the queue
   - D) It only scales during scheduled time windows

<details>
<summary>Show Answer</summary>

**Answer: B) It queries SQS queue metrics and scales pods based on the ratio of queue messages to a configured target value per pod**

**Explanation:**
KEDA's SQS scaler periodically queries SQS for queue depth metrics. It calculates desired replicas as: `queue_length / queueLength_target`. For example, with 100 messages and `queueLength: 10`, KEDA targets 10 pods. It also respects `minReplicaCount` and `maxReplicaCount` bounds. When the queue is empty, it can scale to zero (if configured), and scales up as messages arrive. The scaler uses IAM credentials (via IRSA) to access SQS metrics.

</details>

---

4. How does KEDA's Prometheus scaler query metrics for scaling decisions?
   - A) It only supports Prometheus's built-in metrics
   - B) It executes a configured PromQL query against a Prometheus server and scales based on the returned value compared to a threshold
   - C) It requires a special KEDA metrics exporter in Prometheus
   - D) It can only query counter metrics, not gauges

<details>
<summary>Show Answer</summary>

**Answer: B) It executes a configured PromQL query against a Prometheus server and scales based on the returned value compared to a threshold**

**Explanation:**
The KEDA Prometheus scaler executes any valid PromQL query against a configured Prometheus endpoint. You specify the `serverAddress`, `query` (PromQL), and `threshold`. KEDA scales pods to make `query_result / threshold = replica_count`. This enables scaling based on business metrics (requests/second, queue depth), custom application metrics, or any queryable data. Authentication supports bearer tokens or TLS for secured Prometheus instances.

</details>

---

5. How does Karpenter detect pending pods and provision appropriate nodes?
   - A) It polls the Kubernetes API for pods with PodScheduled=False and matches their requirements against NodePool templates
   - B) It requires pods to explicitly request Karpenter provisioning via annotations
   - C) It monitors cluster CPU usage and pre-provisions nodes
   - D) It waits for Horizontal Pod Autoscaler signals before provisioning

<details>
<summary>Show Answer</summary>

**Answer: A) It polls the Kubernetes API for pods with PodScheduled=False and matches their requirements against NodePool templates**

**Explanation:**
Karpenter watches for unschedulable pods (those pending because no existing node can satisfy their requirements). When detected, it analyzes pod requirements (resource requests, node selectors, tolerations, topology constraints) and provisions optimal EC2 instances from configured NodePools. Karpenter's bin-packing algorithm efficiently groups pending pods and selects instance types that minimize cost while meeting requirements. This "just-in-time" provisioning is faster than Cluster Autoscaler's node-group-based approach.

</details>

---

6. What does Karpenter's Consolidation policy do for cost optimization?
   - A) It only consolidates pods within existing nodes
   - B) It identifies underutilized or empty nodes and migrates workloads to reduce the total node count, terminating unnecessary nodes
   - C) It consolidates logs from multiple nodes
   - D) It only works during scheduled maintenance windows

<details>
<summary>Show Answer</summary>

**Answer: B) It identifies underutilized or empty nodes and migrates workloads to reduce the total node count, terminating unnecessary nodes**

**Explanation:**
Karpenter's consolidation continuously evaluates cluster efficiency. It identifies opportunities to reduce costs by: terminating empty nodes immediately, replacing nodes with cheaper alternatives that still meet requirements, and consolidating workloads from multiple underutilized nodes onto fewer nodes. Consolidation respects pod disruption budgets and uses graceful termination. This automated right-sizing ensures you only pay for needed capacity, complementing scale-up with intelligent scale-down.

</details>

---

7. What are the key RED metrics to observe during load testing in Grafana dashboards?
   - A) RAM, Ethernet, Disk
   - B) Rate (requests/second), Errors (error rate/count), Duration (latency distribution)
   - C) Replicas, Events, Deployments
   - D) Reads, Executions, Deletions

<details>
<summary>Show Answer</summary>

**Answer: B) Rate (requests/second), Errors (error rate/count), Duration (latency distribution)**

**Explanation:**
RED metrics are a standard methodology for service monitoring: Rate measures throughput (requests per second), Errors tracks failure rate or count (4xx, 5xx responses), and Duration captures latency distribution (p50, p95, p99 response times). During load testing, these metrics reveal how the system behaves under stress: does throughput plateau? Do errors spike? Does latency degrade? RED dashboards provide immediate visibility into service health and help identify breaking points.

</details>

---

8. How can you track pod count changes during scaling events using Prometheus metrics?
   - A) Using `kube_pod_created` timestamp only
   - B) Using `kube_deployment_status_replicas` to track current replica count and comparing against `kube_deployment_spec_replicas` for desired count
   - C) Pod count metrics are not available in Prometheus
   - D) Using `container_cpu_usage` aggregated by pod

<details>
<summary>Show Answer</summary>

**Answer: B) Using `kube_deployment_status_replicas` to track current replica count and comparing against `kube_deployment_spec_replicas` for desired count**

**Explanation:**
kube-state-metrics exposes deployment replica information: `kube_deployment_spec_replicas` shows desired replicas (what HPA/KEDA targets), `kube_deployment_status_replicas` shows current ready replicas, and `kube_deployment_status_replicas_available` shows available replicas. Graphing these over time reveals scaling behavior—how quickly actual replicas match desired, any oscillation, and scale-up/down timing. For HPA-specific metrics, `kube_horizontalpodautoscaler_*` metrics provide additional detail.

</details>

---

9. What role does the `stabilizationWindowSeconds` setting play in KEDA scaling behavior?
   - A) It sets the minimum time a pod must run before termination
   - B) It defines a lookback window during scale-down to prevent rapid oscillation by considering the highest recommendation over that period
   - C) It configures the interval between metric queries
   - D) It sets the maximum time for pod startup

<details>
<summary>Show Answer</summary>

**Answer: B) It defines a lookback window during scale-down to prevent rapid oscillation by considering the highest recommendation over that period**

**Explanation:**
`stabilizationWindowSeconds` prevents thrashing during scale-down. When scaling down, KEDA looks at all scale recommendations from the past N seconds (the stabilization window) and uses the highest value. This prevents scenarios where brief metric dips trigger scale-down, immediately followed by scale-up when load returns. For example, a 300-second window means scale-down only occurs if metrics have been consistently low for 5 minutes. Scale-up is typically not stabilized to ensure quick response to load increases.

</details>

---

10. How does SQS Queue Depth correlate with pod scaling in a queue-based workload architecture?
    - A) Queue depth and pod count are inversely proportional always
    - B) As queue depth increases, KEDA scales up pods to process messages faster, reducing queue depth; as the queue drains, pods scale down
    - C) Queue depth only affects memory allocation, not pod count
    - D) Pod scaling happens independently of queue depth

<details>
<summary>Show Answer</summary>

**Answer: B) As queue depth increases, KEDA scales up pods to process messages faster, reducing queue depth; as the queue drains, pods scale down**

**Explanation:**
In queue-based architectures, there's a feedback loop: incoming messages increase queue depth, KEDA detects this and scales up consumer pods, more pods process messages faster (increasing throughput), queue depth decreases, and eventually KEDA scales down pods when the queue is manageable. The `queueLength` threshold determines the messages-per-pod target. Observing queue depth alongside pod count reveals processing capacity—if queue depth grows despite maximum pods, you've found a bottleneck requiring optimization or higher limits.

</details>
