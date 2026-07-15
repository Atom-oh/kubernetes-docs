# Spark on Kubernetes Fundamentals Quiz

This quiz tests your understanding of cluster-mode submission, the driver's role as its own scheduler, Dynamic Resource Allocation on Kubernetes, and graceful executor decommissioning.

## Multiple Choice Questions

1. Which Spark deploy mode does Kubernetes support for `spark-submit`?
   - A) Client mode only
   - B) Cluster mode only
   - C) Both client and cluster mode, chosen automatically by Kubernetes
   - D) Neither — Kubernetes requires a separate submission tool

<details>

<summary>Show Answer</summary>

**Answer: B) Cluster mode only**

**Explanation:**
On Kubernetes, `spark-submit` with `--deploy-mode cluster` creates the driver as a pod running inside the cluster itself, rather than running the driver on the machine that issued the submit command. Client mode exists on Kubernetes too, but it is mainly used for interactive tools like spark-shell and notebooks where the driver needs to run outside the cluster.
</details>

2. After `spark-submit` creates the driver pod, who creates the executor pods?
   - A) A separate Spark cluster-manager daemon similar to YARN's ResourceManager
   - B) The Kubernetes scheduler automatically, without any Spark-side request
   - C) The driver pod itself, by calling the Kubernetes API
   - D) The `spark-submit` client process, before it exits

<details>

<summary>Show Answer</summary>

**Answer: C) The driver pod itself, by calling the Kubernetes API**

**Explanation:**
Once the driver pod is running, it acts as its own scheduler: it calls back into the Kubernetes API server to create the executor pods it needs, based on `spark.executor.instances` or Dynamic Resource Allocation. This is a key architectural difference from YARN, where a persistent ResourceManager and per-node NodeManagers negotiate and hand out containers.
</details>

3. What operational simplification does running Spark on Kubernetes provide compared to YARN?
   - A) It eliminates the need for a driver process entirely
   - B) There is no separate, persistent Spark cluster-manager daemon (like a ResourceManager/NodeManager) to install and maintain
   - C) It removes the need for executors to report status back to the driver
   - D) It guarantees lower memory usage per task

<details>

<summary>Show Answer</summary>

**Answer: B) There is no separate, persistent Spark cluster-manager daemon (like a ResourceManager/NodeManager) to install and maintain**

**Explanation:**
On YARN, submitting a job requires a persistent ResourceManager negotiating containers from per-node NodeManager daemons. On Kubernetes, the same Kubernetes control plane already used for every other workload schedules Spark's driver and executor pods directly — there's no separate Spark-specific cluster-manager process to run. The trade-off is that scheduling/allocation responsibility shifts onto the driver pod itself.
</details>

4. Why does Kubernetes need `spark.dynamicAllocation.shuffleTracking.enabled=true` in addition to `spark.dynamicAllocation.enabled=true` for Dynamic Resource Allocation to work safely?
   - A) Kubernetes has no External Shuffle Service (ESS) daemon, so shuffle tracking is what prevents scale-down from removing executors that still hold needed shuffle blocks
   - B) It is required to enable executor autoscaling at all; without it, `spark.dynamicAllocation.enabled` has no effect
   - C) It reduces the memory footprint of each executor
   - D) It is only needed when running Spark in client mode

<details>

<summary>Show Answer</summary>

**Answer: A) Kubernetes has no External Shuffle Service (ESS) daemon, so shuffle tracking is what prevents scale-down from removing executors that still hold needed shuffle blocks**

**Explanation:**
On YARN, the NodeManager hosts an External Shuffle Service that can keep serving shuffle blocks even after the executor that produced them is removed. Kubernetes has no equivalent built-in daemon. Shuffle tracking (stable since Spark 3.3.0) lets Spark's scale-down logic know which executors still hold shuffle blocks that other tasks depend on, so it won't kill them until those blocks are no longer needed or the job completes.
</details>

5. What does Spark's graceful decommissioning feature (`spark.decommission.enabled` + `spark.storage.decommission.enabled`) protect against?
   - A) It prevents the Kubernetes API server from becoming a bottleneck during executor creation
   - B) It migrates cached RDD and shuffle blocks to peer executors before a pod terminates, instead of losing that data outright
   - C) It automatically restarts the driver pod if it crashes
   - D) It increases the `terminationGracePeriodSeconds` value cluster-wide

<details>

<summary>Show Answer</summary>

**Answer: B) It migrates cached RDD and shuffle blocks to peer executors before a pod terminates, instead of losing that data outright**

**Explanation:**
When a pod is signaled for termination — due to a node scale-down, Spot Instance interruption, or rolling upgrade — Kubernetes gives it a grace period (`terminationGracePeriodSeconds`, 30 seconds by default) before force-killing it. With graceful decommissioning enabled, Spark uses that window to migrate cached RDD blocks and shuffle blocks to other healthy executors rather than simply losing them, turning what would otherwise be a job-wide failure into a more limited, recoverable event.
</details>

6. What is the default value of a pod's `terminationGracePeriodSeconds`, which bounds how long graceful decommissioning has to migrate blocks before a pod is forcibly killed?
   - A) 10 seconds
   - B) 30 seconds
   - C) 60 seconds
   - D) 5 minutes

<details>

<summary>Show Answer</summary>

**Answer: B) 30 seconds**

**Explanation:**
Kubernetes' default `terminationGracePeriodSeconds` is 30 seconds. This is the window Spark's graceful decommissioning has to migrate cached RDD and shuffle blocks to other executors before the pod is forcibly terminated. Jobs that need more migration time can increase this value on the executor pod template, giving decommissioning more time to work.
</details>

7. Which setting controls how many executor pod creation requests the driver sends to the Kubernetes API per batch when Dynamic Resource Allocation scales up?
   - A) `spark.dynamicAllocation.maxExecutors`
   - B) `spark.executor.instances`
   - C) `spark.kubernetes.allocation.batch.size`
   - D) `spark.dynamicAllocation.shuffleTracking.enabled`

<details>

<summary>Show Answer</summary>

**Answer: C) `spark.kubernetes.allocation.batch.size`**

**Explanation:**
`spark.kubernetes.allocation.batch.size` controls how aggressively the driver ramps up executor pod creation requests against the Kubernetes API. Setting it too high can cause a burst of pod creation requests to hit the API and the underlying node group's autoscaling all at once; `minExecutors`/`maxExecutors` set the overall floor and ceiling but don't control request batching.
</details>

## Short Answer Questions

8. In cluster mode on Kubernetes, what role does the driver pod play that a persistent ResourceManager plays on YARN?

<details>

<summary>Show Answer</summary>

**Answer: The driver pod acts as its own scheduler.**

**Explanation:**
Rather than a separate, persistent cluster-manager process negotiating and handing out containers (as YARN's ResourceManager does), the Spark driver pod itself issues requests directly to the Kubernetes API to create the executor pods it needs, tracks which executors are alive, and requests replacements when executors fail. This removes a layer of infrastructure to operate, but makes the driver pod's API access and permissions critical to the entire job running.
</details>

9. Why can't Dynamic Resource Allocation safely remove an idle-looking executor on Kubernetes without shuffle tracking enabled?

<details>

<summary>Show Answer</summary>

**Answer: Because that executor might still be holding shuffle blocks that other, not-yet-finished tasks need to read, and Kubernetes has no External Shuffle Service to keep serving those blocks after the executor is gone.**

**Explanation:**
On YARN, the NodeManager-hosted External Shuffle Service can keep serving shuffle blocks independent of any executor's lifetime, so removing an idle executor is safe. On Kubernetes, no such daemon exists, so if DRA removes an executor that's still serving shuffle blocks other tasks depend on, those blocks are lost and dependent tasks fail, forcing a recompute. `spark.dynamicAllocation.shuffleTracking.enabled=true` closes this gap by making Spark track which executors still hold needed shuffle data before allowing them to be reclaimed.
</details>

---

[Return to Learning Materials](../../../data-on-eks/spark/01-spark-fundamentals.md)
