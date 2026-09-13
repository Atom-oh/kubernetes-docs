# Flink Architecture on Kubernetes Quiz

Check execution roles and resource boundaries for Flink 2.2.1 / Operator 1.15.0.

1. Does the JobManager always build the initial graph while the client does no computation?

<details>
<summary>Show Answer</summary>

**Answer:** No. Application main() runs on the JM, while ordinary 2.2 Session CLI submission builds the graph on the client.

**Explanation:** The JM coordinates execution, slots, checkpoints and recovery; TMs execute tasks. User main() can itself consume JM resources.

</details>

2. Do four TaskManager slots imply at most four operator subtasks?

<details>
<summary>Show Answer</summary>

**Answer:** No. Chaining and slot sharing can place several operators in one slot.

**Explanation:** A classic fixed slot is primarily a managed-memory allocation unit, not a CPU core or independent CPU-isolation boundary.

</details>

3. Does Application mode always mean one cluster per job and complete isolation of shared EKS resources?

<details>
<summary>Show Answer</summary>

**Answer:** No. One application/main() can create several jobs, and nodes, network, storage and quotas may be shared.

**Explanation:** Application-level lifecycle/JVM separation helps but is not absolute isolation. Check the 2.2 limits on multi-execute Application HA.

</details>

4. Does submitting to an existing Session cluster always start execution immediately?

<details>
<summary>Show Answer</summary>

**Answer:** No. Cluster startup overhead can be reduced, but slots, CPU, state recovery and shared load can delay execution.

**Explanation:** Session jobs share JM/TM resources; one TM failure can affect several jobs using it.

</details>

5. Should Per-Job be counted as a third current Native Kubernetes mode in this chapter?

<details>
<summary>Show Answer</summary>

**Answer:** No. The covered lifecycle choices are Application and Session; Per-Job is historical.

**Explanation:** Application/Session and the Native/Standalone resource-management choices are separate classifications.

</details>

6. Who manages Native TaskManager pods and the EKS nodes that host them?

<details>
<summary>Show Answer</summary>

**Answer:** Flink's Kubernetes ResourceManager requests TM pods through the API; Karpenter/Cluster Autoscaler separately manages node capacity.

**Explanation:** TM release depends on idle timeouts, resource profiles and demand. Job completion does not immediately remove every pod/node.

</details>

7. Can Standalone-on-Kubernetes TaskManager counts change only through manual YAML edits?

<details>
<summary>Show Answer</summary>

**Answer:** No. An external controller such as the Operator can reconcile Kubernetes resources.

**Explanation:** The Flink runtime does not directly request TM pods through Native resource management. Separately assess API permissions for features such as HA.

</details>

8. What are Operator 1.15.0's two cluster/job CRs, and does it support only Native mode?

<details>
<summary>Show Answer</summary>

**Answer:** FlinkDeployment and FlinkSessionJob; it supports both Native and Standalone.

**Explanation:** Deployment defines Application/Session clusters; SessionJob targets an existing managed Session cluster. Version-enum membership alone does not prove integration compatibility.

</details>

---

[Return to Learning Materials](../../../data-on-eks/flink/01-architecture.md)
