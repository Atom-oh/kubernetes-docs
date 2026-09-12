# Operations, HA and Managed Flink Quiz

Check collection paths, memory/recovery boundaries and managed-service support.

1. Which resource does the reviewed Kubernetes HA leader election use?

<details>
<summary>Show Answer</summary>

**Answer:** Fabric8 ConfigMapLock, relying on Kubernetes control-plane availability.

**Explanation:** It does not add a separate leader-election server or invariably use Lease resources. ZooKeeper HA is also a supported alternative.

</details>

2. Do HA ConfigMaps, HA storageDir and checkpoint directories store the same data?

<details>
<summary>Show Answer</summary>

**Answer:** ConfigMaps hold leader information/references, HA storageDir holds JM recovery metadata/job graphs, and checkpoint directories preserve checkpoint state.

**Explanation:** One HA path setting does not prepare every state file or recovery permission.

</details>

3. Does an HA-only ConfigMap Role provide all Native Flink permissions?

<details>
<summary>Show Answer</summary>

**Answer:** No. Native resource management also requires pod/service and other appropriate permissions.

**Explanation:** Check each caller's needs and inspect API errors, logs and restarts; failures are not always silent.

</details>

4. What do the Flink and node autoscalers primarily adjust?

<details>
<summary>Show Answer</summary>

**Answer:** Vertex parallelism and node capacity, respectively.

**Explanation:** Pressure, quotas, state recovery and placement couple the loops; Flink does not universally act first.

</details>

5. Must Karpenter create a node for every Pending pod?

<details>
<summary>Show Answer</summary>

**Answer:** No. Distinguish unschedulable pods from image-pull, PVC, admission and other causes.

**Explanation:** Constraints, resource requests, instance availability and quotas can prevent provisioning.

</details>

6. Does a consolidation delay longer than Flink stabilization prevent interruptions?

<details>
<summary>Show Answer</summary>

**Answer:** No guarantee follows; node failure, Spot reclamation and drift can occur independently.

**Explanation:** Test provisioning, restoration, backlog catch-up and disruption/PDB policies together.

</details>

7. Does managed Flink 2.3 support imply availability of every upstream feature?

<details>
<summary>Show Answer</summary>

**Answer:** No. Check the Java 17/Python 3.12 combination and service-specific exclusions.

**Explanation:** Restrictions include Java 21, ForSt, Native S3, custom telemetry and Studio. Separate AWS infrastructure HA from application/state responsibilities.

</details>

8. How should managed KPU costs be compared with EKS Spot?

<details>
<summary>Show Answer</summary>

**Answer:** Compare total cost and operations at equivalent throughput, latency and recovery objectives.

**Explanation:** Include orchestration and related storage/network costs for KPUs and interruption/recovery costs for Spot.

</details>

9. Do RocksDB managed memory and network buffers share one pool?

<details>
<summary>Show Answer</summary>

**Answer:** They are separate budget regions.

**Explanation:** In the checked 4GiB configuration, changing managed fraction from 0.4 to 0.5 left network unchanged and reduced task heap. Budgets differ from measured RSS.

</details>

10. What should be checked when a PodMonitor exists but has no targets?

<details>
<summary>Show Answer</summary>

**Answer:** Prometheus monitor/namespace selectors, real pod labels, named ports, target namespaces and discovery permissions.

**Explanation:** This chart's Operator pod lacked a default instance label. Deployment metadata is not automatically a pod label.

</details>

11. Is block-cache-usage a ratio, and is a Flink Counter always a Prometheus Counter?

<details>
<summary>Show Answer</summary>

**Answer:** No. Cache usage is bytes, and the reviewed reporter exports Flink Counters as Gauges.

**Explanation:** Interpret cache capacity/hit/miss too. Histograms map to Summaries; inspect exported TYPE and labels.

</details>

12. Should kubernetes.cluster-id be set directly in an Operator-managed CR?

<details>
<summary>Show Answer</summary>

**Answer:** No. The 1.15 validator forbids it; identity is managed from CR name/namespace.

**Explanation:** Do not blindly copy low-level CLI configuration. kubernetes.namespace and high-availability.cluster-id are also restricted.

</details>

13. Do two JM replicas and a completed checklist guarantee instant, uninterrupted recovery?

<details>
<summary>Show Answer</summary>

**Answer:** No. Validate election, node/AZ placement, storage, state restoration, replay time and actual results.

**Explanation:** Keeping defaults can be valid. Measured SLO/recovery outcomes and operating ownership matter beyond settings.

</details>

---

[Return to Learning Materials](../../../data-on-eks/flink/04-operations-ha.md) | [Flink](../../../data-on-eks/flink/README.md)
