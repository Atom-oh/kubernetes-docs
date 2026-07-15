# Flink Kubernetes Operator Quiz

This quiz tests your understanding of the Flink Kubernetes Operator's core CRDs, upgrade modes, and built-in autoscaler.

## Multiple Choice Questions

1. What is the main difference between a `FlinkDeployment` and a `FlinkSessionJob`?
   - A) `FlinkDeployment` is only for batch jobs, `FlinkSessionJob` is only for streaming jobs
   - B) `FlinkDeployment` defines an Application-mode cluster or a job-less Session-mode cluster; `FlinkSessionJob` submits a job onto an already-running Session-mode cluster
   - C) They are interchangeable names for the same resource
   - D) `FlinkSessionJob` can only run once and cannot be deleted independently

<details>

<summary>Show Answer</summary>

**Answer: B) `FlinkDeployment` defines an Application-mode cluster or a job-less Session-mode cluster; `FlinkSessionJob` submits a job onto an already-running Session-mode cluster**

**Explanation:**
`FlinkDeployment` either bundles a job directly into an Application-mode cluster, or defines a Session-mode cluster with no job attached. `FlinkSessionJob` submits a job onto an existing Session-mode `FlinkDeployment`, and a single session cluster can host many independently managed `FlinkSessionJob` resources.
</details>

2. Which Kubernetes version is required by the Flink Kubernetes Operator 1.15+, and why?
   - A) Kubernetes 1.16+, for CRD v1 support
   - B) Kubernetes 1.21+, for the automatic namespace-labeling support the admission webhook relies on
   - C) Kubernetes 1.25+, because PodSecurityPolicy was removed
   - D) There is no minimum version requirement

<details>

<summary>Show Answer</summary>

**Answer: B) Kubernetes 1.21+, for the automatic namespace-labeling support the admission webhook relies on**

**Explanation:**
The operator's admission webhook depends on automatic namespace labeling, which requires Kubernetes 1.21 or later.
</details>

3. What capability did operator release 1.14.0 add natively?
   - A) Savepoint-based upgrades
   - B) Blue/Green deployments
   - C) The built-in autoscaler
   - D) Session-mode clusters

<details>

<summary>Show Answer</summary>

**Answer: B) Blue/Green deployments**

**Explanation:**
Operator 1.14.0 (February 2026) added native Blue/Green deployment support, letting two versions of a job run side by side under Operator control instead of requiring external scripting.
</details>

4. Which `upgradeMode` is the safest but slowest, since it requires a clean stop-the-world savepoint before proceeding?
   - A) `stateless`
   - B) `last-state`
   - C) `savepoint`
   - D) `blue-green`

<details>

<summary>Show Answer</summary>

**Answer: C) `savepoint`**

**Explanation:**
`savepoint` mode takes an explicit savepoint, tears the cluster down cleanly, and restores from that savepoint — the most durable and verifiable option, but the slowest because it requires a clean savepoint before the old cluster can be torn down.
</details>

5. Why is `last-state` upgrade mode able to work even on an unhealthy or actively failing job, unlike `savepoint` mode?
   - A) It skips checkpointing entirely
   - B) It uses the latest checkpoint's metadata instead of requiring a fresh, cleanly-taken savepoint
   - C) It restarts the job with no state at all
   - D) It requires manual intervention from an operator (human)

<details>

<summary>Show Answer</summary>

**Answer: B) It uses the latest checkpoint's metadata instead of requiring a fresh, cleanly-taken savepoint**

**Explanation:**
`last-state` restores from the most recent checkpoint's metadata rather than taking a new savepoint, so it doesn't depend on the job being healthy enough to cleanly quiesce for a savepoint — making it usable even when a job is already failing.
</details>

6. Since which operator version has `last-state` upgrade mode been usable with `FlinkSessionJob` (not just `FlinkDeployment`)?
   - A) 1.0.0
   - B) 1.10.0
   - C) 1.14.0
   - D) 1.15.0

<details>

<summary>Show Answer</summary>

**Answer: B) 1.10.0**

**Explanation:**
`last-state` became usable with `FlinkSessionJob` starting with operator 1.10.0; before that release it was only available for `FlinkDeployment`.
</details>

7. What does the Flink autoscaler adjust to respond to load, in contrast to a typical Kubernetes HPA?
   - A) The number of Pod replicas, exactly like HPA
   - B) The CPU and memory requests/limits on TaskManager Pods
   - C) The parallelism of each individual vertex in the job graph
   - D) The number of Kafka partitions on the source topic

<details>

<summary>Show Answer</summary>

**Answer: C) The parallelism of each individual vertex in the job graph**

**Explanation:**
Unlike HPA, which scales pod replica counts, the Flink autoscaler scales the parallelism of each vertex (source, map, join, sink, etc.) independently, based on that vertex's own processing needs.
</details>

8. For a downstream (non-source) vertex, how does the autoscaler compute its target processing rate?
   - A) A fixed value set by the user
   - B) The sum of the output rates of all upstream vertices feeding into it
   - C) The average CPU utilization of the TaskManager Pods
   - D) The Kafka consumer lag of the entire job

<details>

<summary>Show Answer</summary>

**Answer: B) The sum of the output rates of all upstream vertices feeding into it**

**Explanation:**
For source vertices the target rate is the incoming data rate; for downstream vertices, the target rate is the sum of the output rates of all upstream vertices feeding into them. The autoscaler then solves for the parallelism that lets the vertex sustain that rate at the configured utilization target.
</details>

9. Why does the autoscaler deliberately avoid using CPU/memory metrics to detect load?
   - A) CPU and memory metrics aren't available in Kubernetes
   - B) A vertex can be CPU-idle while still bottlenecked (e.g., waiting on slow I/O), so busy-time and processing-rate metrics reflect real throughput pressure more directly
   - C) CPU/memory metrics require a separate Prometheus installation
   - D) Flink vertices don't consume any CPU or memory

<details>

<summary>Show Answer</summary>

**Answer: B) A vertex can be CPU-idle while still bottlenecked (e.g., waiting on slow I/O), so busy-time and processing-rate metrics reflect real throughput pressure more directly**

**Explanation:**
In a dataflow engine, a vertex can be a bottleneck while CPU-idle (blocked on I/O) or CPU-busy without being under real load pressure. Busy time, backlog, and processing-rate metrics reflect actual throughput pressure directly, which is what determines whether Flink can keep up with input — CPU/memory is a poor proxy for that.
</details>

10. Why is it recommended to set `pipeline.max-parallelism` to a highly composite number (e.g., 360)?
    - A) It reduces JVM heap usage
    - B) Flink's key-group model divides max-parallelism evenly among the chosen parallelism, so a highly composite ceiling gives the autoscaler far more valid divisor values to choose from
    - C) It is required by the Kubernetes scheduler
    - D) It disables checkpointing overhead

<details>

<summary>Show Answer</summary>

**Answer: B) Flink's key-group model divides max-parallelism evenly among the chosen parallelism, so a highly composite ceiling gives the autoscaler far more valid divisor values to choose from**

**Explanation:**
Because max-parallelism must divide evenly by the actual parallelism under Flink's key-group model, a highly composite number like 120, 180, 240, 360, or 720 has many more divisors than a prime number, giving the autoscaler many more valid parallelism values to select between.
</details>

## Short Answer Questions

11. What upgrade mechanism does the autoscaler use under the hood when it decides to rescale a vertex?

<details>

<summary>Show Answer</summary>

**Answer: A `last-state` upgrade**

**Explanation:**
When the autoscaler crosses a scaling threshold, it triggers a rescale through the same mechanism as a manual `last-state` upgrade — fast, and resilient even if the job isn't perfectly healthy.
</details>

12. What Flink runtime versions does operator 1.15.0 support as job runtimes?

<details>

<summary>Show Answer</summary>

**Answer: Flink 2.2.x, 2.1.x, 2.0.x, 1.20.x, and 1.19.x**

**Explanation:**
Operator 1.15.0 (May 2026) supports these five Flink minor version lines as job runtimes.
</details>

13. What two new logging/metrics-related capabilities does operator 1.15.0 add?

<details>

<summary>Show Answer</summary>

**Answer: An optional Logback logging configuration (alongside the default Log4j2), and the `flink-metrics-dropwizard` reporter bundled into the Helm chart by default**

**Explanation:**
1.15.0 adds a Logback option alongside Log4j2 and bundles the Dropwizard metrics reporter in its Helm chart, in addition to adding Kubernetes-native `Conditions` on `FlinkDeployment.status`.
</details>

14. Which Helm chart value scopes the operator to watch only specific namespaces instead of the whole cluster?

<details>

<summary>Show Answer</summary>

**Answer: `watchNamespaces`**

**Explanation:**
By default the operator watches every namespace. Setting `watchNamespaces` (e.g., `--set watchNamespaces="{flink,flink-staging}"`) restricts it to the listed namespaces.
</details>

15. What configuration key controls the rolling window used to smooth metrics before the autoscaler makes a scaling decision, and what range is recommended?

<details>

<summary>Show Answer</summary>

**Answer: `job.autoscaler.metrics.window`, recommended range 3–60 minutes**

**Explanation:**
Too short a window reacts to noise; too long a window reacts too slowly to genuine load changes. 3–60 minutes is the recommended range.
</details>

## Hands-on Questions

16. Write the full command sequence to install the Flink Kubernetes Operator via Helm into the `flink` namespace.

<details>

<summary>Show Answer</summary>

**Answer:**
```bash
# Add the Flink Kubernetes Operator Helm repository
helm repo add flink-operator-repo https://downloads.apache.org/flink/flink-kubernetes-operator-1.15.0/
helm repo update

# Install the operator into the flink namespace
helm install flink-kubernetes-operator flink-operator-repo/flink-kubernetes-operator \
  --namespace flink \
  --create-namespace

# Verify the installation
kubectl get pods -n flink
kubectl get crd | grep flink
```

**Explanation:**
`helm repo add` registers the operator's Helm repository, and `--create-namespace` on `helm install` creates the `flink` namespace automatically if it doesn't exist. `kubectl get crd | grep flink` confirms `FlinkDeployment` and `FlinkSessionJob` CRDs were registered.
</details>

17. Write a minimal `FlinkDeployment` running an Application-mode job with `upgradeMode: last-state` and a parallelism of 4.

<details>

<summary>Show Answer</summary>

**Answer:**
```yaml
apiVersion: flink.apache.org/v1beta1
kind: FlinkDeployment
metadata:
  name: order-events-processor
  namespace: flink
spec:
  image: apache/flink:2.1.0
  flinkVersion: v2_1
  serviceAccount: flink
  jobManager:
    resource:
      memory: "2048m"
      cpu: 1
  taskManager:
    resource:
      memory: "4096m"
      cpu: 2
  job:
    jarURI: local:///opt/flink/usrlib/order-events-processor.jar
    entryClass: com.example.flink.OrderEventsJob
    parallelism: 4
    upgradeMode: last-state
```

**Explanation:**
`spec.job` with a `jarURI` and `entryClass` makes this an Application-mode `FlinkDeployment` — the job is baked directly into the cluster definition rather than submitted separately as a `FlinkSessionJob`. `upgradeMode: last-state` means future spec changes (and autoscaler rescales) will restore from the latest checkpoint rather than requiring a fresh savepoint.
</details>

18. Write the `flinkConfiguration` block that enables the autoscaler with a target utilization of 0.6, a 10-minute metrics window, and `pipeline.max-parallelism` set to a highly composite number.

<details>

<summary>Show Answer</summary>

**Answer:**
```yaml
flinkConfiguration:
  job.autoscaler.enabled: "true"
  job.autoscaler.target.utilization: "0.6"
  job.autoscaler.metrics.window: "10m"
  pipeline.max-parallelism: "360"
```

**Explanation:**
`job.autoscaler.target.utilization: "0.6"` is the busy-time ratio the autoscaler tries to maintain per vertex. `job.autoscaler.metrics.window: "10m"` is within the recommended 3–60 minute range for smoothing metrics. `pipeline.max-parallelism: "360"` is highly composite (divisible by 1, 2, 3, 4, 5, 6, 8, 9, 10, 12, ...), giving the autoscaler many valid parallelism values to choose from.
</details>

19. Write the `kubectl` commands to apply a `FlinkDeployment` and then wait for it to become available.

<details>

<summary>Show Answer</summary>

**Answer:**
```bash
kubectl apply -f order-events-processor.yaml -n flink
kubectl get flinkdeployment -n flink
kubectl wait --for=condition=Available flinkdeployment/order-events-processor -n flink --timeout=180s
```

**Explanation:**
`kubectl wait --for=condition=Available` relies on the Kubernetes-native `Conditions` that operator 1.15.0 added to `FlinkDeployment.status`, letting you block on a specific condition instead of polling `.status.jobStatus.state` manually.
</details>

20. Explain in your own words why setting `job.autoscaler.catch-up.duration` prevents the autoscaler from over-scaling a vertex that is working through a backlog.

<details>

<summary>Show Answer</summary>

**Answer:**
A vertex working through backlog will temporarily show a higher processing rate and busy time than its steady-state load, because it's catching up on old data as well as new. Without `job.autoscaler.catch-up.duration`, the autoscaler could mistake this temporary catch-up spike for a permanent increase in load and scale the vertex up unnecessarily. The catch-up duration gives the vertex a time budget to work through backlog before the autoscaler reacts to it as sustained load.

**Explanation:**
This setting distinguishes a transient backlog-clearing spike from a genuine, sustained increase in incoming data rate, avoiding unnecessary rescales (and the `last-state` upgrades they trigger) in response to temporary conditions.
</details>

---

[Return to Learning Materials](../../../data-on-eks/flink/02-flink-kubernetes-operator.md)
