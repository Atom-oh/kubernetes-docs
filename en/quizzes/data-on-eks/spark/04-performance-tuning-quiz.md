# Part 4: Performance and Cost Tuning Quiz

This quiz tests your understanding of node type selection for Spark on EKS, why NVMe instance store beats EBS for shuffle spill, the On-Demand-driver/Spot-executor split, graceful decommissioning during Spot interruptions, and the relationship between Karpenter and Spark's Dynamic Resource Allocation.

## Multiple Choice Questions

1. Which instance family does AWS's best-practices guidance for Spark on EKS recommend for shuffle-heavy jobs?
   - A) T-series burstable instances
   - B) C-series compute-optimized instances
   - C) R-series instances with NVMe instance store (R5d, R5ad, R5dn)
   - D) X-series high-memory instances

<details>
<summary>Show Answer</summary>

**Answer: C) R-series instances with NVMe instance store (R5d, R5ad, R5dn)**

**Explanation:**
Shuffle stages are typically memory- and disk-I/O-bound rather than CPU-bound, so AWS recommends R-series instances (which pair generous memory-per-vCPU with fast local NVMe disk) specifically for shuffle-heavy Spark workloads. T-series and C-series are not sized or equipped for this profile, and X-series is not called out in this guidance.
</details>

2. Why does this document frame Graviton (arm64) instance types as "worth evaluating independently" rather than recommending them outright?
   - A) Graviton instances cannot run containers
   - B) The AWS guidance this section is based on does not cover Graviton specifically for Spark shuffle workloads
   - C) Graviton instances don't support instance store
   - D) Spark cannot run on arm64 architecture at all

<details>
<summary>Show Answer</summary>

**Answer: B) The AWS guidance this section is based on does not cover Graviton specifically for Spark shuffle workloads**

**Explanation:**
The source material recommends R5d/R5ad/R5dn but doesn't address Graviton equivalents like R6gd/R7gd for this specific workload. Rather than asserting parity that isn't documented, the guidance is to benchmark independently — including confirming that native/JNI dependencies have arm64 builds.
</details>

3. Why is the default root EBS volume on an EKS worker node inadequate for `spark.local.dir`?
   - A) EBS volumes cannot be mounted by Spark
   - B) The root volume is typically sized around 20GB, far too small for shuffle-heavy scratch space
   - C) EBS volumes are read-only
   - D) `spark.local.dir` requires a specific EBS volume type

<details>
<summary>Show Answer</summary>

**Answer: B) The root volume is typically sized around 20GB, far too small for shuffle-heavy scratch space**

**Explanation:**
The root EBS volume is sized for the OS and container images, not for the terabytes of shuffle scratch data a heavy job can generate. Under real shuffle pressure, this fills up quickly and jobs fail with "No space left on device."
</details>

4. Why does NVMe instance store outperform EBS for shuffle spill storage?
   - A) It has a larger default size than EBS
   - B) It is directly attached to the physical host, giving higher throughput and IOPS than network-attached EBS
   - C) It automatically replicates data across availability zones
   - D) It is cheaper to provision at large sizes than EBS

<details>
<summary>Show Answer</summary>

**Answer: B) It is directly attached to the physical host, giving higher throughput and IOPS than network-attached EBS**

**Explanation:**
Instance store is ephemeral local disk physically attached to the host, so it delivers much higher throughput/IOPS than EBS, which is network-attached. The tradeoff is that instance store is wiped when the instance stops or terminates, making it suitable only for transient scratch data like shuffle spill.
</details>

5. Why should Spark driver pods run on On-Demand capacity while executor pods run on Spot?
   - A) Drivers require more CPU than Spot instances can provide
   - B) The driver holds job coordination state and losing it fails the whole job, while losing an executor only costs its in-flight tasks
   - C) On-Demand instances are always cheaper than Spot for single-pod workloads
   - D) Spot instances cannot run JVM-based workloads

<details>
<summary>Show Answer</summary>

**Answer: B) The driver holds job coordination state and losing it fails the whole job, while losing an executor only costs its in-flight tasks**

**Explanation:**
The driver is a single point of failure for the entire job (DAG scheduler, task bookkeeping). Executors are replaceable compute — losing one costs at most its in-flight tasks and unmigrated shuffle data, making Spot's interruption risk acceptable for executors but not for the driver.
</details>

6. In the taint/toleration pattern described for enforcing the driver/executor split, what keeps executor pods off the On-Demand NodePool?
   - A) Executors have an explicit anti-affinity rule against On-Demand nodes
   - B) The On-Demand NodePool is tainted, and only driver pods carry the matching toleration
   - C) Executors are physically incapable of running on On-Demand instances
   - D) Karpenter automatically blocks executor pods from On-Demand capacity

<details>
<summary>Show Answer</summary>

**Answer: B) The On-Demand NodePool is tainted, and only driver pods carry the matching toleration**

**Explanation:**
The On-Demand NodePool carries a `NoSchedule` taint (e.g., `spark-role=driver`). Only driver pods are configured with a matching toleration, set via a driver pod template (`spark.kubernetes.driver.podTemplateFile`), so executors — which lack that toleration — can never be scheduled there. Executors are separately steered toward the Spot pool via node selector.
</details>

7. During a Spot Instance interruption, what does graceful decommissioning (`spark.decommission.enabled`, `spark.storage.decommission.enabled`) allow Spark to do?
   - A) Cancel the interruption and keep the instance running
   - B) Migrate shuffle blocks and cached RDD partitions to a healthy peer executor during the interruption notice window
   - C) Automatically restart the entire job from the last checkpoint
   - D) Convert the Spot instance to On-Demand automatically

<details>
<summary>Show Answer</summary>

**Answer: B) Migrate shuffle blocks and cached RDD partitions to a healthy peer executor during the interruption notice window**

**Explanation:**
AWS gives Spot instances roughly a two-minute interruption notice. With decommissioning enabled, Spark uses that window to migrate the doomed executor's shuffle blocks and cached RDD partitions to another healthy executor, rather than losing that data outright. If no peer executor has room, Spark falls back to durable/remote shuffle storage if configured, or lets affected tasks recompute.
</details>

8. Which statement best describes the relationship between Karpenter and Spark's Dynamic Resource Allocation (DRA)?
   - A) They are the same control loop, just running on different components
   - B) DRA reacts to pending tasks and requests/releases executor pods; Karpenter reacts to pending/empty pods and provisions/deprovisions nodes — two independent loops that feed each other
   - C) Karpenter directly controls how many executors Spark requests
   - D) DRA provisions EC2 nodes directly without involving Karpenter

<details>
<summary>Show Answer</summary>

**Answer: B) DRA reacts to pending tasks and requests/releases executor pods; Karpenter reacts to pending/empty pods and provisions/deprovisions nodes — two independent loops that feed each other**

**Explanation:**
DRA has no knowledge of underlying nodes — it only decides how many executor pods to request based on Spark's own task backlog. Karpenter has no knowledge of Spark's task backlog — it only reacts to pods that DRA already created (or nodes that have gone empty). The two loops interact but are tuned independently.
</details>

9. What problem can occur if Karpenter's `consolidateAfter` is set much shorter than DRA's `spark.dynamicAllocation.executorIdleTimeout`?
   - A) Karpenter will never provision new nodes
   - B) Karpenter may try to consolidate a node that still has an executor DRA hasn't released yet, colliding with the decommissioning path
   - C) DRA will stop requesting new executors entirely
   - D) The driver pod will be evicted

<details>
<summary>Show Answer</summary>

**Answer: B) Karpenter may try to consolidate a node that still has an executor DRA hasn't released yet, colliding with the decommissioning path**

**Explanation:**
If Karpenter tries to reclaim a node before DRA has decided to release the idle executor still running there, the two loops collide. Keeping Karpenter's consolidation delay somewhat longer than DRA's executor idle timeout ensures DRA has already vacated a node before Karpenter tries to reclaim it.
</details>

10. Why does this document recommend sizing driver pods larger and steadier, and executor pods smaller and multiplied, rather than giving fixed numeric defaults?
    - A) Kubernetes enforces a fixed ratio between driver and executor resource requests
    - B) The right sizing depends on job-specific factors (state tracked, per-task working set, shuffle buffers) that the source research didn't reduce to universal numbers, so it should be arrived at through load testing
    - C) Spark automatically calculates optimal sizing at runtime
    - D) Driver and executor pods must always request identical resources

<details>
<summary>Show Answer</summary>

**Answer: B) The right sizing depends on job-specific factors (state tracked, per-task working set, shuffle buffers) that the source research didn't reduce to universal numbers, so it should be arrived at through load testing**

**Explanation:**
Driver memory needs depend on how much state it tracks (partition count, broadcast variables, accumulators); executor memory needs depend on per-task working-set size and shuffle settings. Rather than asserting fixed defaults not backed by the source material, the document frames these as values to determine via load testing against the actual job and dataset.
</details>

## Short Answer Questions

11. Name the two Spark configuration properties that together enable graceful executor decommissioning.

<details>
<summary>Show Answer</summary>

**Answer: `spark.decommission.enabled=true` and `spark.storage.decommission.enabled=true`**

**Explanation:**
Both must be set together. `spark.decommission.enabled` turns on the general decommissioning mechanism, and `spark.storage.decommission.enabled` specifically enables migration of storage (shuffle blocks and cached RDD partitions) to peer executors during the termination grace period.
</details>

12. What happens to shuffle data during a Spot interruption if graceful decommissioning is enabled but no peer executor has spare capacity to receive the migrated blocks?

<details>
<summary>Show Answer</summary>

**Answer: Spark falls back to configured durable/remote shuffle storage if available; otherwise, the tasks that depended on that data are recomputed.**

**Explanation:**
Decommissioning's migration path depends on a healthy peer executor having room for the incoming blocks. When that's not available, the fallback is either external shuffle storage (if configured) or recomputation of the affected tasks — a degraded outcome, but not a full job failure.
</details>

## Hands-on Questions

13. Write the driver pod template and `spark-submit` configuration properties that make a driver pod tolerate a `NoSchedule` taint with key `spark-role`, value `driver`, and target nodes labeled `karpenter.sh/capacity-type=on-demand`.

<details>
<summary>Show Answer</summary>

**Answer:**
```yaml
# driver-pod-template.yaml
apiVersion: v1
kind: Pod
spec:
  tolerations:
    - key: spark-role
      operator: Equal
      value: driver
      effect: NoSchedule
```
```properties
spark.kubernetes.driver.podTemplateFile=driver-pod-template.yaml
spark.kubernetes.driver.node.selector.karpenter.sh/capacity-type=on-demand
```

**Explanation:**
Spark has no `spark.kubernetes.*.tolerations.*` configuration property — tolerations are a pod-spec field, not a flat conf key, so they must be set via a pod template (`spark.kubernetes.driver.podTemplateFile`) or, under the Spark Operator, the `SparkApplication` CRD's `spec.driver.tolerations`. `spark.kubernetes.driver.node.selector.<label>` adds a node selector so the driver is actively steered toward On-Demand nodes, not merely permitted to land there.
</details>

14. Write the Spark configuration property that points `spark.local.dir` at a mounted NVMe path and describe, in one sentence, why the executor pod spec needs a `hostPath` volume for this to work.

<details>
<summary>Show Answer</summary>

**Answer:**
```properties
spark.local.dir=/data/spark-local
```

**Explanation:**
Only one property is needed on the Spark side (`spark.local.dir`), but it only works if the executor pod's container actually has that path backed by the host's NVMe disk — which requires a `hostPath` volume (mounted from the node's instance-store mount point, e.g. `/mnt/k8s-disks/nvme1n1`) mapped to `/data/spark-local` in the pod spec. Without that volume mount, `spark.local.dir` would just resolve to ordinary container filesystem space on the root EBS volume.
</details>

---

[Return to Learning Materials](../../../data-on-eks/spark/04-performance-tuning.md)
