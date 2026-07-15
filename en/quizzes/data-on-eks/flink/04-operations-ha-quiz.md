# Part 4: Operations, High Availability, and Managed Flink Quiz

This quiz tests your understanding of how Kubernetes-native HA works without Zookeeper, what ConfigMaps store for HA, the two-tier relationship between the Flink autoscaler and Karpenter, and when to choose Amazon Managed Service for Apache Flink over self-managed Flink on EKS.

## Multiple Choice Questions

1. What replaces Zookeeper in Flink's Kubernetes-native High Availability (FLIP-144)?
   - A) An etcd cluster deployed alongside Flink
   - B) The Kubernetes leader-election API plus ConfigMaps
   - C) A dedicated Raft consensus sidecar
   - D) AWS Systems Manager Parameter Store

<details>
<summary>Show Answer</summary>

**Answer: B) The Kubernetes leader-election API plus ConfigMaps**

**Explanation:**
Kubernetes-native HA, available since Flink 1.12, uses the same leader-election primitive other Kubernetes controllers rely on to decide which JobManager replica is active, and stores the leader's address and HA metadata in ConfigMaps. No external Zookeeper ensemble needs to be deployed, upgraded, or backed up.
</details>

2. What does the ConfigMap used by Flink's Kubernetes-native HA actually store?
   - A) The full checkpoint data for the job
   - B) The active leader's address and HA metadata (JobGraph store, checkpoint pointers)
   - C) A copy of the TaskManager's RocksDB state
   - D) The Flink Kubernetes Operator's Helm values

<details>
<summary>Show Answer</summary>

**Answer: B) The active leader's address and HA metadata (JobGraph store, checkpoint pointers)**

**Explanation:**
The ConfigMap stores the currently active JobManager's address so other components can find it, plus HA metadata — pointers to the JobGraph store and checkpoints — needed to recover the job on a new leader after failover. The actual JobGraph and checkpoint data live in the durable storage referenced by `high-availability.storageDir` (e.g., S3), not in the ConfigMap itself.
</details>

3. What RBAC permissions does the JobManager's `ServiceAccount` need for Kubernetes-native HA to work?
   - A) Cluster-wide admin access
   - B) Read-only access to `Pod` objects
   - C) `get`/`list`/`watch`/`create`/`update`/`patch`/`delete` on `ConfigMap` objects in its namespace
   - D) Write access to `PersistentVolumeClaim` objects

<details>
<summary>Show Answer</summary>

**Answer: C) `get`/`list`/`watch`/`create`/`update`/`patch`/`delete` on `ConfigMap` objects in its namespace**

**Explanation:**
Because the JobManager talks to the Kubernetes API directly to run leader election and read/write HA metadata, its `ServiceAccount` needs a namespaced `Role` granting exactly these verbs on `configmaps` — nothing broader like cluster-wide admin access. Without this Role bound via a `RoleBinding`, HA configuration fails silently: the pod comes up, but leader election and failover never actually function.
</details>

4. In the two-tier autoscaling relationship between the Flink autoscaler and Karpenter, what does the Flink autoscaler control?
   - A) EC2 instance types and node provisioning directly
   - B) Per-vertex parallelism, based on job-internal metrics like backpressure and busy time
   - C) Karpenter's `NodePool` consolidation settings
   - D) The Kubernetes scheduler's bin-packing algorithm

<details>
<summary>Show Answer</summary>

**Answer: B) Per-vertex parallelism, based on job-internal metrics like backpressure and busy time**

**Explanation:**
The Flink Kubernetes Operator's built-in autoscaler watches per-vertex metrics (backpressure, busy time, lag) and adjusts how much parallelism each operator needs — a job-internal decision with no knowledge of the underlying nodes. Karpenter is the separate, node-level loop that reacts to the resulting TaskManager pod count.
</details>

5. Why does Karpenter provision new EC2 nodes in this two-tier stack?
   - A) It independently monitors Flink's checkpoint metrics
   - B) It reacts to TaskManager pods that become unschedulable after the autoscaler increases parallelism
   - C) It directly queries the Flink REST API for parallelism settings
   - D) It provisions nodes on a fixed schedule regardless of pod state

<details>
<summary>Show Answer</summary>

**Answer: B) It reacts to TaskManager pods that become unschedulable after the autoscaler increases parallelism**

**Explanation:**
Karpenter has no knowledge of *why* TaskManager pods exist — only that pending, unschedulable pods need capacity. When the Flink autoscaler raises parallelism and more TaskManager pods are requested, some may be unschedulable on existing nodes; Karpenter reacts to that signal by provisioning new EC2 capacity. The job-level decision always happens first, and the node-level decision only reacts to its consequences.
</details>

6. What can go wrong if the Flink autoscaler scales parallelism up faster than Karpenter's `NodePool` can provision matching nodes?
   - A) The job crashes with an out-of-memory error
   - B) New TaskManager pods sit `Pending` longer than expected, stalling the scale-up
   - C) Flink automatically falls back to the heap state backend
   - D) The Kubernetes API server rejects further pod creation requests

<details>
<summary>Show Answer</summary>

**Answer: B) New TaskManager pods sit `Pending` longer than expected, stalling the scale-up**

**Explanation:**
If the autoscaler's parallelism increases faster than Karpenter can provision matching EC2 capacity, new TaskManager pods remain `Pending` for longer than expected, which stalls the very scale-up the autoscaler triggered. This is the same kind of mismatch the Spark performance-tuning document describes for Karpenter and Dynamic Resource Allocation.
</details>

7. Who manages JobManager High Availability in Amazon Managed Service for Apache Flink?
   - A) The customer, via a self-configured RBAC Role
   - B) AWS, automatically across multiple Availability Zones
   - C) A Zookeeper ensemble provisioned by the customer
   - D) The Flink Kubernetes Operator running inside the managed service

<details>
<summary>Show Answer</summary>

**Answer: B) AWS, automatically across multiple Availability Zones**

**Explanation:**
Amazon Managed Service for Apache Flink is fully managed and serverless — there are no clusters, hosts, or Kubernetes objects to provision, and JobManager HA (the concern that requires a manually configured RBAC Role and `flinkConfiguration` on self-managed EKS) is handled by AWS automatically across multiple AZs.
</details>

8. Which of the following is a concrete reason to run Flink yourself on EKS rather than use Amazon Managed Service for Apache Flink?
   - A) You want to avoid ever configuring an RBAC Role
   - B) Cost control via EC2 Spot Instances matters at your scale, and AWS has published guidance on optimizing Flink-on-EKS costs with Spot
   - C) Amazon Managed Service for Apache Flink cannot run any version of Flink 2.x
   - D) Self-managed Flink requires no monitoring setup at all

<details>
<summary>Show Answer</summary>

**Answer: B) Cost control via EC2 Spot Instances matters at your scale, and AWS has published guidance on optimizing Flink-on-EKS costs with Spot**

**Explanation:**
Amazon Managed Service for Apache Flink bills on a usage-based (KPU) model that doesn't expose a Spot-like cost lever. Teams that need fine-grained autoscaler tuning, want to control costs via Spot Instances, or already run other workloads (like Kafka-on-EKS via Strimzi) through the same GitOps/observability pipeline benefit from self-managing Flink on EKS instead. As of March 2026, the managed service does support Flink 2.2, so option C is incorrect.
</details>

## Short Answer Questions

9. In one sentence, explain why Flink's Kubernetes-native HA doesn't need a separate quorum ensemble the way Zookeeper-based HA did.

<details>
<summary>Show Answer</summary>

**Answer: Kubernetes' own leader-election API already provides the leader-election primitive, so Flink doesn't need to run and size a separate Zookeeper quorum for that purpose.**

**Explanation:**
What you still control under Kubernetes-native HA is how many JobManager replicas the `FlinkDeployment` runs — more than one gives a warm standby ready to take over on failover — but there's no separate consensus ensemble to size and operate, unlike the Zookeeper-based approach it replaces.
</details>

10. What must `high-availability.storageDir` point to, and why?

<details>
<summary>Show Answer</summary>

**Answer: Durable, shared storage (such as S3) reachable by any pod that could become the new leader, because it's where the actual JobGraph and checkpoint pointers are stored — the ConfigMap only holds a pointer to that location plus the leader's address.**

**Explanation:**
If `storageDir` isn't durable and shared, a new leader elected after a failover wouldn't be able to reach the JobGraph and checkpoint data needed to recover the job, defeating the purpose of HA.
</details>

11. Describe the two separate signals that the Flink autoscaler and Karpenter each react to in the two-tier autoscaling stack.

<details>
<summary>Show Answer</summary>

**Answer: The Flink autoscaler reacts to per-vertex job metrics (backpressure, busy time, lag) to decide operator parallelism. Karpenter reacts to the resulting TaskManager pod scheduling state (pending/unschedulable pods, or empty nodes) to decide EC2 capacity.**

**Explanation:**
These are two independent control loops with no direct knowledge of each other — the Flink autoscaler doesn't know about nodes, and Karpenter doesn't know about job-internal metrics — but they're coupled because the autoscaler's parallelism decision changes the pod count Karpenter then reacts to.
</details>

## Hands-on Questions

12. Write the `flinkConfiguration` snippet that enables Kubernetes-native HA on a `FlinkDeployment`, with the HA metadata stored at `s3://my-flink-bucket/ha/` and cluster ID `my-flink-cluster`.

<details>
<summary>Show Answer</summary>

**Answer:**
```yaml
high-availability.type: kubernetes
high-availability.storageDir: s3://my-flink-bucket/ha/
kubernetes.cluster-id: my-flink-cluster
```

**Explanation:**
`high-availability.type: kubernetes` selects Kubernetes-native HA (as opposed to the legacy Zookeeper-based option). `high-availability.storageDir` points to the durable, shared location for JobGraph and checkpoint data. `kubernetes.cluster-id` scopes the HA ConfigMaps to this specific cluster so multiple Flink clusters in the same namespace don't collide.
</details>

13. Write the RBAC `Role` (rules only) that grants a Flink `ServiceAccount` in namespace `flink` the permissions it needs on `ConfigMap` objects for Kubernetes-native HA.

<details>
<summary>Show Answer</summary>

**Answer:**
```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: flink-ha-role
  namespace: flink
rules:
  - apiGroups: [""]
    resources: ["configmaps"]
    verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
```

**Explanation:**
The JobManager needs to create, read, update, and delete ConfigMaps in its own namespace to run leader election and manage HA metadata. This `Role` must be bound to the JobManager's `ServiceAccount` via a `RoleBinding` for HA to actually function — without it, HA configuration fails silently.
</details>

---

[Return to Learning Materials](../../../data-on-eks/flink/04-operations-ha.md) | [Previous Quiz: State Backends and Checkpointing](./03-state-checkpointing-streaming-quiz.md)
