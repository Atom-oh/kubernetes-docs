# Part 4: Performance and Cost Tuning

> **Last Updated**: July 15, 2026

Part 1 covered how `spark-submit` schedules driver and executor pods directly against the Kubernetes API, and introduced Dynamic Resource Allocation (DRA) and graceful decommissioning as the two mechanisms that make Spark on Kubernetes resilient to pods disappearing mid-job. This document builds on both: it looks at what node types and local storage actually hold up under shuffle-heavy Spark workloads, how to combine Spot Instances with decommissioning without losing job progress, and how Karpenter's node-level autoscaling and Spark's pod-level DRA have to be tuned as two separate but interacting control loops rather than one.

## Lab Environment Setup

To follow along with the examples in this document, you will need:

### Required Tools

* kubectl v1.30 or later
* An EKS cluster with [Karpenter](../../autoscaling/02-karpenter.md) installed and at least one `EC2NodeClass`/`NodePool` pair configured
* Apache Spark 4.2 distributed locally (for `spark-submit` against the cluster)
* metrics-server or the Kubernetes Metrics API enabled, so pending-pod-driven scaling behaves as described

## 1. Node Type Selection for Shuffle-Heavy Jobs

AWS's own best-practices guidance for running Spark on EKS recommends **R-series instances with local NVMe instance store** — specifically R5d, R5ad, and R5dn — for shuffle-heavy workloads. The reasoning is straightforward: shuffle stages are usually memory- and disk-I/O-bound rather than CPU-bound, so an instance family that pairs generous memory-per-vCPU with fast local disk fits the workload better than a general-purpose or compute-optimized family.

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: spark-shuffle-heavy
spec:
  template:
    spec:
      requirements:
        - key: node.kubernetes.io/instance-type
          operator: In
          values: ["r5d.2xlarge", "r5d.4xlarge", "r5ad.2xlarge", "r5dn.2xlarge"]
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["spot", "on-demand"]
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: spark-nvme
```

**A note on Graviton:** the source AWS guidance this section is based on does not call out Graviton (arm64) instance types — such as R6gd or R7gd, which also pair R-series memory ratios with NVMe instance store — specifically for Spark shuffle workloads. Rather than assert Graviton parity that hasn't been documented for this workload, treat it as worth evaluating independently: build a Spark container image for arm64, benchmark a representative shuffle-heavy job against equivalent x86 NVMe instances, and confirm any native/JNI dependencies in your job (compression codecs, native BLAS libraries, etc.) actually have arm64 builds before committing to it.

## 2. Shuffle Spill Storage: NVMe Instance Store Over EBS

Spark writes shuffle blocks and RDD spill data to the directories listed in `spark.local.dir`. By default, on a freshly provisioned EKS worker node, that resolves to space on the **root EBS volume** — typically provisioned around 20GB, which is sized for the OS and container images, not for terabytes of shuffle scratch space. Under real shuffle pressure this fills up fast and jobs fail with `No space left on device` long before they fail for any Spark-level reason.

The fix is to mount the NVMe instance store disks that come attached to R5d/R5ad/R5dn instances (and Nitro instances generally) and point `spark.local.dir` at them instead. Because instance store is ephemeral local disk directly attached to the physical host, it delivers far higher throughput and IOPS than network-attached EBS, with none of the per-GB or per-IOPS cost.

```bash
# EC2NodeClass userData (excerpt): format and mount NVMe instance store at bootstrap
#!/bin/bash
for disk in $(lsblk -d -o NAME,TYPE | awk '$2=="disk" && $1 ~ /^nvme/ {print $1}'); do
  # Skip the root/EBS-backed device; only touch actual instance-store NVMe disks
  if ! mount | grep -q "/dev/$disk"; then
    mkfs.xfs "/dev/$disk"
    mkdir -p "/mnt/k8s-disks/$disk"
    mount "/dev/$disk" "/mnt/k8s-disks/$disk"
    chmod 777 "/mnt/k8s-disks/$disk"
  fi
done
```

```yaml
# Executor pod template: mount the host's NVMe path as spark.local.dir
apiVersion: v1
kind: Pod
spec:
  containers:
    - name: spark-kubernetes-executor
      volumeMounts:
        - name: spark-local-dir
          mountPath: /data/spark-local
  volumes:
    - name: spark-local-dir
      hostPath:
        path: /mnt/k8s-disks/nvme1n1
        type: Directory
```

```properties
# spark-submit conf
spark.local.dir=/data/spark-local
```

Since instance store is wiped whenever the underlying instance stops or terminates, this pattern is only appropriate for transient shuffle/spill scratch data — never for anything Spark needs to survive a pod restart.

## 3. Spot Instance Strategy: On-Demand Drivers, Spot Executors

The driver holds the job's coordination state — the DAG scheduler, task bookkeeping, and (in client-adjacent setups) the SparkContext itself. Losing it mid-job means losing the whole job, not just a few tasks. Executors, by contrast, are replaceable compute: losing one costs at most the tasks it was running and whatever shuffle data it hadn't yet migrated. This asymmetry is why the recommended split is:

* **Driver pods → On-Demand** capacity, which AWS will not reclaim on short notice
* **Executor pods → Spot** capacity, accepting that individual executors may be interrupted

### Enforcing the Split

Node-group-level taints plus pod-level tolerations and node selectors keep driver pods off Spot nodes and executor pods off (or, less strictly, merely preferring) On-Demand nodes:

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: spark-driver-on-demand
spec:
  template:
    spec:
      requirements:
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["on-demand"]
      taints:
        - key: spark-role
          value: driver
          effect: NoSchedule
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: spark-nvme
---
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: spark-executor-spot
spec:
  template:
    spec:
      requirements:
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["spot"]
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: spark-nvme
```

Spark has no `spark.kubernetes.*.tolerations.*` configuration property — tolerations aren't exposed as flat `spark-submit` conf keys, only as pod template fields (or, if you're on the Spark Operator from Part 2, as the `SparkApplication` CRD's `spec.driver.tolerations`). For a plain `spark-submit`, add the toleration via a driver pod template:

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
# spark-submit conf: driver uses the template above and targets the On-Demand pool
spark.kubernetes.driver.podTemplateFile=driver-pod-template.yaml
spark.kubernetes.driver.node.selector.karpenter.sh/capacity-type=on-demand

# Executors get no toleration for the driver taint, so they can never land there,
# and are explicitly steered toward the Spot pool
spark.kubernetes.executor.node.selector.karpenter.sh/capacity-type=spot
```

Because only driver pods carry the `spark-role=driver` toleration, the `NoSchedule` taint on the On-Demand `NodePool` keeps every other pod — including executors — off it. Executors are separately pointed at the Spot `NodePool` via node selector.

### Making Interruptions Survivable

Taints and tolerations only control *placement* — they don't make a Spot interruption harmless on their own. That's what Part 1's graceful decommissioning settings are for:

```properties
spark.decommission.enabled=true
spark.storage.decommission.enabled=true
```

AWS gives Spot instances roughly a **two-minute interruption notice** before reclaiming the capacity. With decommissioning enabled, Spark uses that window to migrate the shuffle blocks and cached RDD partitions the doomed executor is holding to a healthy peer executor, rather than losing them outright. If no peer executor has spare capacity to receive that data, Spark falls back to whatever durable/remote shuffle storage is configured (or, absent one, simply lets the affected tasks recompute) — degraded, but not a job failure. The result is that a Spot interruption becomes "a handful of tasks re-run on another executor" instead of "the job restarts from scratch."

## 4. Two Independent Scaling Loops: Karpenter and Dynamic Resource Allocation

Once DRA and Karpenter are both in play, it helps to be explicit that they are **two separate control loops**, each reacting to a different signal, that happen to feed each other:

* **Spark's DRA** watches its own backlog of pending *tasks* and decides how many executor *pods* to request or release — a Spark-internal decision that has no direct knowledge of the underlying nodes.
* **Karpenter** watches for pending *pods* that can't be scheduled (or nodes that have gone empty) and decides whether to provision or deprovision EC2 capacity — a node-level decision that has no knowledge of Spark's task backlog, only of the pods DRA already created.

```mermaid
flowchart LR
    A[Pending Spark tasks] -->|DRA sees backlog| B[Spark requests<br/>more executor pods]
    B --> C[New executor pods<br/>Pending scheduling]
    C -->|unschedulable| D[Karpenter provisions<br/>new EC2 node]
    D --> E[Executor pods<br/>Scheduled & Running]
    E -->|tasks drain, executors idle| F[DRA releases<br/>idle executor pods]
    F --> G[Node becomes empty]
    G -->|consolidateAfter elapses| H[Karpenter deprovisions<br/>the node]
    H -.-> A
```

The practical consequence is that tuning one loop without the other produces mismatched behavior. If DRA's `spark.kubernetes.allocation.batch.size` requests executors faster than Karpenter's `NodePool` can provision matching nodes, new executor pods sit `Pending` for longer than expected. If Karpenter's `consolidateAfter` (see the [NodePool configuration](../../autoscaling/02-karpenter.md#nodepool) reference) is set very aggressively while DRA's `spark.dynamicAllocation.executorIdleTimeout` is comparatively long, Karpenter may try to consolidate a node that still has an executor DRA hasn't decided to release yet, colliding with the PodDisruptionBudget/decommissioning path from section 3. As a starting point, keep Karpenter's consolidation delay somewhat longer than DRA's executor idle timeout, so DRA has already vacated a node before Karpenter tries to reclaim it.

## 5. Sizing Driver and Executor Resource Requests/Limits

The driver and executor pods have different jobs, and that should show up in how they're sized, at least conceptually:

* **Driver**: sized larger and steadier relative to its actual workload, because it's a single point of failure for the job — it shouldn't be running so close to its memory limit that a transient spike triggers an OOM-kill, and (per section 3) it shouldn't be casually evicted the way a replaceable executor can be.
* **Executors**: sized smaller and multiplied — many executors each handling a slice of the data is the whole point of horizontal parallelism, and DRA (section 4) depends on executors being cheap enough, individually, to add and remove freely.

Spark's own resource settings map directly onto Kubernetes pod resource fields:

| Spark Setting | Kubernetes Effect |
| --- | --- |
| `spark.driver.memory`, `spark.driver.cores` | Driver container's `resources.requests`/`.limits` (with memory overhead added) |
| `spark.executor.memory`, `spark.executor.cores` | Each executor container's `resources.requests`/`.limits` |
| `spark.driver.memoryOverheadFactor` | Extra headroom added on top of `spark.driver.memory` for off-heap/JVM overhead |

There isn't a numeric default that fits every job here — how much memory a driver needs depends on how much state it tracks (partition count, broadcast variable size, accumulators), and how much an executor needs depends on per-task working-set size and shuffle buffer settings. Treat these as values to arrive at through load testing against your actual job and dataset size, not as constants to copy from another pipeline.

## 6. Cost Optimization: Building on General EKS Practices

Most EKS-wide cost techniques — Spot Instance usage, bin-packing via Karpenter consolidation, right-sizing instance types — apply to Spark exactly as they apply to any other workload on the cluster. [Amazon EKS Cost Optimization](../../eks/07-eks-cost-optimization.md) covers those techniques in general; this section is specifically about applying them to **Spark's driver/executor pod model**:

* The [Spot Instance section](../../eks/07-eks-cost-optimization.md#spot-instance-utilization) of that guide applies to executors, not drivers — section 3 above is the Spark-specific reason why the split matters.
* [Karpenter's consolidation behavior](../../autoscaling/02-karpenter.md#nodepool) reclaims nodes left empty when DRA scales executors down, which is exactly the second half of the feedback loop in section 4 — consolidation only pays off if DRA is actually releasing idle executors promptly.
* Instance-type selection (section 1) and NVMe-backed local storage (section 2) are Spark-specific refinements on top of the general "pick the right instance family" guidance in the cost-optimization document.

## Next Steps

This document covered node type selection for shuffle-heavy jobs, why NVMe instance store beats EBS for shuffle spill, the On-Demand-driver/Spot-executor split and how graceful decommissioning makes Spot interruptions survivable, the two independent Karpenter/DRA scaling loops and how to keep them from working against each other, and how to think about driver/executor resource sizing. Together with the general EKS cost techniques it builds on, this rounds out the performance and cost half of running Spark on EKS. Operational concerns — monitoring, security, and day-2 best practices for Spark on EKS — are covered next in [Part 5: Best Practices and Security](./05-best-practices.md).

[Return to Main Page](./README.md)

## Quiz

To test what you've learned in this chapter, try the [Topic Quiz](../../quizzes/data-on-eks/spark/04-performance-tuning-quiz.md).
