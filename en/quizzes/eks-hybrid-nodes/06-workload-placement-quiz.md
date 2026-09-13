# EKS Hybrid Nodes Workload Placement Quiz

> **Related Document**: [Workload Placement](../../eks-hybrid-nodes/06-workload-placement.md)
> **Last Updated**: September 13, 2026

### 1. Which is not a direct Pod placement/eligibility mechanism?

A. nodeSelector

B. Node affinity

C. Taints and tolerations

D. PodDisruptionBudget

<details>
<summary>Show Answer</summary>

**Answer: D. PodDisruptionBudget**

**Explanation:** A PDB constrains supported voluntary eviction requests; it does not select nodes or guarantee availability across every deletion path. Node selection, affinity and taints have different scheduling roles.

</details>

### 2. What does dedicated=gpu:NoSchedule establish?

A. Only containers requesting a GPU can ever run there

B. New Pods need an applicable toleration; that alone does not prove GPU use or force placement

C. Existing Pods are immediately evicted

D. The node advertises GPU resources automatically

<details>
<summary>Show Answer</summary>

**Answer: B. New Pods need an applicable toleration; that alone does not prove GPU use or force placement**

**Explanation:** A CPU-only Pod can tolerate the taint too. GPU resource requests and admission policy are separate. NoSchedule affects new scheduling; NoExecute has different eviction semantics.

</details>

### 3. What does preferred node affinity provide in a burst-eligible workload?

A. Automatic migration of running cloud Pods back to on premises

B. A fixed on-premises-to-cloud replica ratio

C. A scheduling preference among eligible nodes, subject to other constraints and available capacity

D. Unlimited AWS capacity after the eighth Pod

<details>
<summary>Show Answer</summary>

**Answer: C. A scheduling preference among eligible nodes, subject to other constraints and available capacity**

**Explanation:** Preferred affinity is not a saturation detector, strict ordering or migration controller. Node count is not Pod capacity. Karpenter and the replica autoscaler are separate loops, and quotas, offerings, IPs and workload dependencies can block expansion.

</details>

### 4. With DoNotSchedule, how is topology maxSkew interpreted?

A. As a limit on total cluster Pod count

B. Relative to the global minimum across eligible domains, including minDomains behavior when configured

C. As a guaranteed even distribution under ScheduleAnyway

D. As a count of AWS accounts

<details>
<summary>Show Answer</summary>

**Answer: B. Relative to the global minimum across eligible domains, including minDomains behavior when configured**

**Explanation:** Eligible domains depend on the Pod's constraints and topology policy. ScheduleAnyway uses a soft score and can exceed maxSkew. Missing domains and hard rules can leave Pods Pending.

</details>

### 5. Which approach is appropriate for local persistent data?

A. Use a node label and assume the bytes are present

B. Use managed local PV/PVC topology and binding, and separately plan data access or replication for cloud placement

C. Mount /mnt/data through hostPath and treat it as portable storage

D. Move the Pod to any cloud node without checking the volume

<details>
<summary>Show Answer</summary>

**Answer: B. Use managed local PV/PVC topology and binding, and separately plan data access or replication for cloud placement**

**Explanation:** Labels do not create or replicate data. Local PV node affinity and WaitForFirstConsumer coordinate placement; a bound local volume is not automatically accessible from an EC2 fallback node.

</details>

### 6. What does required hostname anti-affinity help achieve?

A. A complete availability guarantee for the application

B. Separation of matching replicas across eligible Kubernetes Nodes when enough capacity exists

C. Guaranteed separation across independent physical power supplies

D. Automatic replica repair without other controllers

<details>
<summary>Show Answer</summary>

**Answer: B. Separation of matching replicas across eligible Kubernetes Nodes when enough capacity exists**

**Explanation:** It reduces one source of correlated failure. Remaining replicas still need readiness, dependencies and sufficient serving capacity, and separate Kubernetes Nodes can share a physical host or failure domain.

</details>

### 7. Can an on-premises Pod with deletion-cost1000 be deleted before a cloud Pod with cost0?

A. No;1000 makes it eviction-proof

B. No;the cost is the first ReplicaSet comparison

C. Yes;assignment,phase and readiness precede deletion cost in the reviewed controller

D. Only if the cost annotation is absent

<details>
<summary>Show Answer</summary>

**Answer: C. Yes;assignment,phase and readiness precede deletion cost in the reviewed controller**

**Explanation:** Unassigned, Pending/Unknown and NotReady criteria can take precedence. Deletion cost is a best-effort preference among the same ReplicaSet's Pods, not protection from every controller, rollout, eviction or failure.

</details>

### 8. Why is the old CREATE-only location-based mutating webhook incomplete?

A. Pod creation never supports admission webhooks

B. The cloud has no labels

C. A normal CREATE request is usually not yet bound to a node, so eventual node location is unavailable

D. Deletion cost can only be changed before scheduling

<details>
<summary>Show Answer</summary>

**Answer: C. A normal CREATE request is usually not yet bound to a node, so eventual node location is unavailable**

**Explanation:** A post-binding process can inspect spec.nodeName. A production webhook also needs a valid backend, Service,TLS and scoped policy; an incomplete fail-closed webhook can block Pod creation.

</details>

### 9. Does Karpenter1.14.1 read pod-deletion-cost?

A. No;only ReplicaSet can ever read it

B. Yes,as part of a normalized eviction-cost heuristic with other inputs;it is not a disruption prohibition

C. Yes,and1000 guarantees1000times more protection

D. Yes,andit replaces PDBs and all disruption budgets

<details>
<summary>Show Answer</summary>

**Answer: B. Yes,as part of a normalized eviction-cost heuristic with other inputs;it is not a disruption prohibition**

**Explanation:** The tagged Karpenter source includes the annotation in its Pod eviction cost. Candidate evaluation, node state, priority and lifecycle constraints still matter; cost annotations do not guarantee that an empty node will be removed immediately.

</details>

### 10. What makes the single-Pod annotation patch safer than the old cluster-wide CronJob?

A. Suppressing all API errors

B. Inferring cloud placement from missing labels

C. Checking the intended ReplicaSet owner,node classification,Pod UID and resourceVersion,then reviewing a narrow patch

D. Removing concurrent-update tests after the first conflict

<details>
<summary>Show Answer</summary>

**Answer: C. Checking the intended ReplicaSet owner,node classification,Pod UID and resourceVersion,then reviewing a narrow patch**

**Explanation:** The example refuses unknown or unscheduled state and writes a reviewable patch. UID/resourceVersion/node tests reject stale state, and unrelated annotations remain intact. It does not scan or modify every namespace.

</details>

