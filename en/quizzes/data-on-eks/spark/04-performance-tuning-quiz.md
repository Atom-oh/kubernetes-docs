# Part 4: Performance and Cost Tuning Quiz

Spark 4.2.0 / Karpenter 1.14 기준 · September 2026.

## 1. Are R-series and NVMe always fastest for shuffle?

<details>
<summary>Show answer</summary>

No. Measure task/stage time, spill, shuffle fetch wait, skew, and CPU/memory/disk/network bottlenecks. Compare available capacity and cost per successful job; other families and EBS are not inherently unsuitable.

</details>

## 2. What should be checked when evaluating Graviton?

<details>
<summary>Show answer</summary>

Validate arm64 support in the Spark image, JNI, codecs, BLAS, Python wheels and plugins, then benchmark representative work. An existing tested multi-architecture image can avoid building your own.

</details>

## 3. Is it safe to format an unmounted nvme device?

<details>
<summary>Show answer</summary>

No. EBS also appears as NVMe on Nitro, and an unmounted disk can contain data or partitions. Device names and mount status do not establish that it is disposable instance store.

</details>

## 4. What does instanceStorePolicy: RAID0 configure on AL2023?

<details>
<summary>Show answer</summary>

Karpenter uses NodeConfig to configure instance-store RAID0 for kubelet/containerd ephemeral storage and advertises allocatable capacity. RAID0 is not backup; a complete NodeClass still needs its AMI, IAM, subnet and other settings.

</details>

## 5. Why can this lab use NVMe scratch without hostPath?

<details>
<summary>Show answer</summary>

The prepared NodeClass backs the kubelet filesystem with instance store, so disk-backed emptyDir uses it. Different node configuration or tmpfs changes the backing storage.

</details>

## 6. Which scratch-volume name does Spark recognize?

<details>
<summary>Show answer</summary>

A name such as spark-local-dir-scratch, with the spark-local-dir- prefix and a suffix. The old spark-local-dir does not match and can cause an additional emptyDir at the same mount path.

</details>

## 7. Does emptyDir sizeLimit reserve disk space?

<details>
<summary>Show answer</summary>

No. Consider requests, node allocatable, other pods, logs and writable layers. The node can fill first; memory-backed tmpfs consumes the memory budget.

</details>

## 8. What does the On-Demand-driver/Spot-executor split not guarantee?

<details>
<summary>Show answer</summary>

It does not eliminate driver failure/drift/expiration or make executor loss harmless. A Spot-only selector does not allow On-Demand fallback and may leave pods Pending during shortages.

</details>

## 9. How do taints/tolerations and node selectors differ?

<details>
<summary>Show answer</summary>

A toleration permits a taint; a selector chooses matching nodes. Other pods may have the same toleration, and NoSchedule does not evict existing pods.

</details>

## 10. Do Spot warnings and decommission flags guarantee completed migration?

<details>
<summary>Show answer</summary>

No. Warnings are best-effort and hibernation has no two-minute window. EventBridge/SQS/interruption handling, drain, hooks/signals, time, peer capacity and networking all matter. A 120s pod grace does not extend cloud lifetime.

</details>

## 11. Does any remote storage automatically become shuffle fallback?

<details>
<summary>Show answer</summary>

No. Configure spark.storage.decommission.fallbackStorage.path and working filesystem/permissions. RDD-cache and shuffle recovery differ; recomputation, fetch failures and retry limits can still fail the job.

</details>

## 12. Which signals drive DRA and Karpenter?

<details>
<summary>Show answer</summary>

DRA adjusts executor count from Spark task backlog and idle/cache/shuffle state. Karpenter provisions nodes from pod requests and scheduling constraints. metrics-server is not required; allocation.batch.size controls Kubernetes allocator creation rate.

</details>

## 13. Does consolidateAfter greater than executorIdleTimeout guarantee DRA releases first?

<details>
<summary>Show answer</summary>

No. The timers start from different events, and shuffle/cache can retain executors. WhenEmpty reduces consolidation of ordinary workload pods, but drift, expiration and Spot termination remain separate.

</details>

## 14. Are 4g JVM heap and cores=2 the entire pod memory and CPU limit?

<details>
<summary>Show answer</summary>

No. This example adds 409MiB default overhead for 4505MiB total memory. Cores affect the default CPU request and Spark concurrency; set the CPU limit explicitly with spark.kubernetes.executor.limit.cores. Review PySpark, off-heap and explicit overhead separately.

</details>

[Guide](../../../data-on-eks/spark/04-performance-tuning.md)
