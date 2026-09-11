# Scheduling, Preemption, and Eviction Quiz

This quiz covers Kubernetes scheduling, node selection, affinity, taints, priority, eviction, disruption budgets, and descheduling.

## Multiple Choice Questions

1. Which of filtering, scoring, and binding occurs first when evaluating candidate nodes?
   - A) Node scoring
   - B) Node filtering
   - C) Determining Pod priority
   - D) Binding

<details>
<summary>Show Answer</summary>

**Answer: B) Node filtering**

**Explanation:**
The scheduler filters unsuitable nodes, scores feasible nodes, selects a node, and binds the Pod. Queueing and other framework extension points surround these steps.
</details>

2. What is the main difference between node affinity and Pod affinity?
   - A) Node affinity supports only hard constraints; Pod affinity supports only soft constraints
   - B) Node affinity matches node labels; Pod affinity relates placement to matching Pods
   - C) Node affinity is cluster-wide while Pod affinity is namespace-wide
   - D) Only Pod affinity automatically changes placement at runtime

<details>
<summary>Show Answer</summary>

**Answer: B) Node affinity matches node labels; Pod affinity relates placement to matching Pods**

**Explanation:**
Both support required and preferred rules. Pod affinity uses matching Pods and a topology key to express co-location. IgnoredDuringExecution does not automatically evict Pods when labels change.
</details>

3. What is the purpose of taints and tolerations?
   - A) Guarantee that a Pod runs only on one specific node
   - B) Let nodes repel Pods unless they have a matching toleration
   - C) Set inter-Pod affinity
   - D) Automatically optimize cluster utilization

<details>
<summary>Show Answer</summary>

**Answer: B) Let nodes repel Pods unless they have a matching toleration**

**Explanation:**
A toleration permits consideration of a tainted node; it does not attract the Pod or guarantee placement. Combine it with node affinity for dedicated workloads, and control who may use the toleration.
</details>

4. How do Pod priority and preemption relate?
   - A) A higher-priority Pod may preempt lower-priority Pods during scheduling
   - B) Priority directly sets CPU/memory allocations
   - C) Preemption occurs only during maintenance
   - D) They are unrelated

<details>
<summary>Show Answer</summary>

**Answer: A) A higher-priority Pod may preempt lower-priority Pods during scheduling**

**Explanation:**
The scheduler can remove lower-priority victims if doing so makes a pending Pod schedulable. This is not a capacity or placement guarantee. A PriorityClass with preemptionPolicy: Never does not preempt other Pods.
</details>

5. How do nodeSelector and node affinity differ?
   - A) nodeSelector is a hard constraint; node affinity supports hard and soft constraints
   - B) nodeSelector supports only one label
   - C) Node affinity cannot match label values
   - D) nodeSelector applies only after scheduling

<details>
<summary>Show Answer</summary>

**Answer: A) nodeSelector is a hard constraint; node affinity supports hard and soft constraints**

**Explanation:**
Node affinity additionally supports In, NotIn, Exists, DoesNotExist, Gt, and Lt. All nodeSelector entries must match. Required node affinity must match; preferred rules affect scores.
</details>

6. Which condition commonly triggers node-pressure eviction?
   - A) A Pod has a low priority value by itself
   - B) The node is short of memory, disk space, or other monitored resources
   - C) A Pod has existed for a long time by itself
   - D) A ReplicaSet has too many replicas

<details>
<summary>Show Answer</summary>

**Answer: B) The node is short of memory, disk space, or other monitored resources**

**Explanation:**
Kubelet monitors pressure signals and may reclaim resources and terminate Pods. Candidate ordering considers usage above requests, Pod priority, and relative usage, not a fixed QoS-only order. Other eviction mechanisms include drain and NoExecute taints.
</details>

7. How are DaemonSet Pods placed?
   - A) One Pod on each eligible target node
   - B) Only on control-plane nodes
   - C) They always bypass kube-scheduler
   - D) The replica count is independent of the number of eligible nodes

<details>
<summary>Show Answer</summary>

**Answer: A) One Pod on each eligible target node**

**Explanation:**
The DaemonSet controller creates Pods targeted to eligible nodes; the scheduler binds them. Selectors, affinity, tolerations, and capacity still matter. The historical direct-binding behavior should not be used to describe current DaemonSets.
</details>

8. Without Pod-level resource settings, which QoS class applies when every container has equal CPU requests/limits and equal memory requests/limits?
   - A) BestEffort
   - B) Burstable
   - C) Guaranteed
   - D) Critical

<details>
<summary>Show Answer</summary>

**Answer: C) Guaranteed**

**Explanation:**
Guaranteed has equal CPU and memory requests/limits on every container. BestEffort has neither, while intermediate configurations are Burstable. QoS is not PriorityClass and does not guarantee survival under every failure or pressure condition.
</details>

9. What permits scheduling consideration on a node tainted node-role.kubernetes.io/control-plane:NoSchedule?
   - A) Node affinity alone
   - B) Pod affinity alone
   - C) A matching toleration
   - D) A higher PriorityClass alone

<details>
<summary>Show Answer</summary>

**Answer: C) A matching toleration**

**Explanation:**
The toleration permits the taint, but resource and other placement constraints must still be satisfied. Use control-plane placement only for intended workloads.

```yaml
tolerations:
- key: "node-role.kubernetes.io/control-plane"
  operator: "Exists"
  effect: "NoSchedule"
```
</details>

10. What does a PodDisruptionBudget primarily control?
   - A) Container resource consumption
   - B) Voluntary eviction through the Eviction API
   - C) Scheduling priority
   - D) Container restart policy

<details>
<summary>Show Answer</summary>

**Answer: B) Voluntary eviction through the Eviction API**

**Explanation:**
A PDB limits allowed Eviction API requests, including normal drain/descheduler operations. Direct Pod deletion, workload-controller rollouts, and node-pressure eviction bypass this gate. It does not create healthy replicas or prevent node failures.
</details>

## Short Answer Questions

1. Describe at least three scheduler Filter plugins.

<details>
<summary>Show Answer</summary>

**Answer:**

- **NodeResourcesFit** checks requested resources against node allocatable capacity and existing requests.
- **NodeAffinity** checks required node selection rules; **NodeUnschedulable** rejects cordoned nodes unless the relevant toleration applies.
- **InterPodAffinity** checks both Pod affinity and anti-affinity; **PodTopologySpread** checks hard spread constraints.
- **TaintToleration** checks taints. **NodePorts** detects host-port conflicts.
- **VolumeBinding** checks PVC binding/topology; **NodeVolumeLimits** checks CSI attachment limits.
- A directly assigned `spec.nodeName` normally bypasses the scheduler. NodeName should not be described as a highest-priority filter.

Old per-provider names such as EBSLimits are not the current CSI plugin names.
</details>

2. Explain how node affinity and taints/tolerations work together for dedicated GPU nodes.

<details>
<summary>Show Answer</summary>

**Answer:**

Node affinity restricts a workload to the intended nodes, while a taint repels Pods that lack a matching toleration. For example, label actual GPU nodes, require the matching GPU label, taint them, and tolerate that taint only in approved GPU workloads.

A toleration alone does not guarantee GPU-node placement. A GPU request such as `nvidia.com/gpu: 1` and a working device plugin are also required to reserve a GPU. Restricting who can add tolerations/labels is needed when this separation is a security boundary.
</details>

3. Explain Pod priority and preemption, including their limits.

<details>
<summary>Show Answer</summary>

**Answer:**

Create a PriorityClass and reference it with `spec.priorityClassName`. The scheduler queue uses priority, and preemption can select lower-priority victims if removing them makes a pending Pod feasible.

The scheduler requests victim deletion through the API; kubelet/runtime carry out termination. Victim termination can delay the incoming Pod, and a nominated node is not an unconditional reservation. Preemption does not remove equal/higher-priority Pods and may not solve affinity or capacity constraints.

PDBs are considered on a best-effort basis, not guaranteed. User-defined priority values must be no greater than 1,000,000,000; system classes have reserved higher values. Merely running in kube-system does not make a Pod exempt. Review events and test the impact.

```yaml
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: high-priority
value: 1000000
globalDefault: false
description: "This priority class should be used for critical production workloads."
```

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: critical-pod
spec:
  priorityClassName: high-priority
  containers:
  - name: web-server
    image: nginx
```
</details>

4. Distinguish node-pressure eviction, Eviction API requests, and taint-based deletion.

<details>
<summary>Show Answer</summary>

**Answer:**

**Node pressure:** Kubelet observes memory, filesystem, and PID availability and may reclaim resources before terminating Pods. Typical Linux hard defaults include memory.available below 100Mi, nodefs.available below 10%, imagefs.available below 15%, and free inodes below 5%. PID does not have a default 10% threshold. Windows memory defaults differ.

**Soft versus hard:** Soft thresholds and their grace periods must be explicitly configured. Hard thresholds can terminate Pods without a graceful period. Soft termination is also bounded by evictionMaxPodGracePeriod. Preserve all intended thresholds when overriding defaults.

**Eviction API:** Normal drain and compatible automation submit policy/v1 Eviction requests. PDBs gate these requests. A direct Pod DELETE is different and bypasses PDB checks.

**Taint-based deletion:** NoExecute taints can delete Pods that do not tolerate them. Ordinary Pods usually have 300-second not-ready/unreachable tolerations. This is separate from kubelet pressure eviction and from the Eviction API gate.

Eviction ends a Pod; a workload controller may create a replacement with a new UID. No mechanism safely moves the same Pod to a different node. Availability requires replicas, storage/capacity planning, and tested failure handling.
</details>

5. How does current DaemonSet scheduling differ from Deployment Pod scheduling?

<details>
<summary>Show Answer</summary>

**Answer:**

A DaemonSet controller creates one Pod for each eligible node and sets target-node affinity. The scheduler performs binding. A Deployment instead maintains a desired replica count through ReplicaSets, with placement based on resources and constraints; Pod count is not one-per-node.

DaemonSets get several automatic tolerations for node conditions, including indefinite not-ready/unreachable NoExecute tolerations. They do not bypass all resource constraints or automatically run on every tainted control-plane node.
</details>

## Hands-on Questions

1. Create a Pod named web-server using nginx:1.30.4 that requires us-east-1a or us-east-1b and prefers m5.large nodes.

<details>
<summary>Show Answer</summary>

**Answer:**

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: web-server
spec:
  containers:
  - name: nginx
    image: nginx:1.30.4
  affinity:
    nodeAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
        nodeSelectorTerms:
        - matchExpressions:
          - key: topology.kubernetes.io/zone
            operator: In
            values:
            - us-east-1a
            - us-east-1b
      preferredDuringSchedulingIgnoredDuringExecution:
      - weight: 1
        preference:
          matchExpressions:
          - key: node.kubernetes.io/instance-type
            operator: In
            values:
            - m5.large
```

Required node affinity limits eligible zones. Preferred node affinity adds a scoring preference for m5.large. The standard labels are populated by cloud/node integration; verify that the chosen cluster nodes actually have them.
</details>

2. Taint worker-1 with dedicated=database:NoSchedule and give a postgres-db Pod a matching toleration.

<details>
<summary>Show Answer</summary>

**Answer:**

```bash
kubectl taint nodes worker-1 dedicated=database:NoSchedule
```

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: postgres-db
spec:
  containers:
  - name: postgres
    image: postgres:17
    env:
    - name: POSTGRES_PASSWORD
      valueFrom:
        secretKeyRef:
          name: postgres-credentials
          key: password
  tolerations:
  - key: "dedicated"
    operator: "Equal"
    value: "database"
    effect: "NoSchedule"
```

Create postgres-credentials with a password key in the same namespace first. The example demonstrates scheduling and has no persistent database storage; add a PVC for durable use. A toleration permits worker-1 but does not force placement there.
</details>

3. Create a three-replica web-frontend Deployment using nginx:1.30.4, co-located with app=cache Pods but separated from its own replicas.

<details>
<summary>Show Answer</summary>

**Answer:**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-frontend
spec:
  replicas: 3
  selector:
    matchLabels:
      app: web-frontend
  template:
    metadata:
      labels:
        app: web-frontend
    spec:
      affinity:
        podAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
          - labelSelector:
              matchExpressions:
              - key: app
                operator: In
                values:
                - cache
            topologyKey: "kubernetes.io/hostname"
        podAntiAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
          - labelSelector:
              matchExpressions:
              - key: app
                operator: In
                values:
                - web-frontend
            topologyKey: "kubernetes.io/hostname"
      containers:
      - name: nginx
        image: nginx:1.30.4
```

Required Pod affinity and anti-affinity apply in the namespace. To schedule all three replicas, matching cache Pods must be present on at least three eligible nodes. Otherwise replicas can remain Pending. These rules do not automatically move existing Pods after labels change.
</details>

4. Create high-priority with value 100000 and a critical-service Pod with Guaranteed QoS: CPU 500m and memory 512Mi for both requests and limits.

<details>
<summary>Show Answer</summary>

**Answer:**

```yaml
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: high-priority
value: 100000
globalDefault: false
description: "This priority class is for critical services that should be scheduled first."
```

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: critical-service
spec:
  priorityClassName: high-priority
  containers:
  - name: nginx
    image: nginx:1.30.4
    resources:
      requests:
        cpu: 500m
        memory: 512Mi
      limits:
        cpu: 500m
        memory: 512Mi
```

Priority affects queueing/preemption; equal CPU and memory requests/limits on the container meet the container-level Guaranteed criteria. Neither priority nor QoS guarantees immunity from node failure or eviction.
</details>

5. Create web-pdb for app=web-server Pods with minAvailable: 2.

<details>
<summary>Show Answer</summary>

**Answer:**

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: web-pdb
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: web-server
```

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: web-pdb
spec:
  maxUnavailable: 1
  selector:
    matchLabels:
      app: web-server
```

The PDB gates normal Eviction API requests so voluntary eviction does not reduce current health below its budget. The alternative maxUnavailable: 1 has the same effect only for three desired replicas. It does not protect direct deletion, rolling updates, or involuntary failures.
</details>

## Advanced Topics

1. Which is the usual way to run a separate scheduler for selected Pods?
   - A) Rebuild kube-scheduler for every policy change
   - B) Deploy a scheduler and select it with schedulerName
   - C) Add any annotation to all Pods
   - D) Enable local scheduling in kubelet

<details>
<summary>Show Answer</summary>

**Answer: B) Deploy a scheduler and select it with schedulerName**

**Explanation:**
A matching scheduler must actually be running with suitable RBAC and a compatible configuration. schedulerName alone does not install it. The scheduler watches Pods/nodes and binds eligible pending Pods; kubelet does not choose placement.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: custom-scheduled-pod
spec:
  schedulerName: my-custom-scheduler
  containers:
  - name: container
    image: nginx
```
</details>

2. Which is not a Descheduler strategy?
   - A) LowNodeUtilization
   - B) RemoveDuplicates
   - C) PodLifeTimeExtension
   - D) RemovePodsViolatingInterPodAntiAffinity

<details>
<summary>Show Answer</summary>

**Answer: C) PodLifeTimeExtension**

**Explanation:**
PodLifeTime evicts matching old Pods; it does not extend their lifetime. Other strategies include NodeAffinity, topology-spread, and restart-count checks. LowNodeUtilization normally compares requested resources with node capacity. Descheduler evicts; controllers create replacements and kube-scheduler chooses placement, which may not be a different node.
</details>

3. Which is not a standard automatically applied node-condition taint?
   - A) node.kubernetes.io/not-ready
   - B) node.kubernetes.io/unreachable
   - C) node.kubernetes.io/disk-pressure
   - D) node.kubernetes.io/high-load

<details>
<summary>Show Answer</summary>

**Answer: D) node.kubernetes.io/high-load**

**Explanation:**
Current standard taints include not-ready, unreachable, memory-pressure, disk-pressure, pid-pressure, network-unavailable, and unschedulable. The old out-of-disk taint is not a current automatic taint. Pressure taints generally use NoSchedule; not-ready/unreachable NoExecute behavior and kubelet pressure eviction are separate mechanisms.
</details>

4. Which statement about topology spread constraints is false?
   - A) They can spread Pods across labeled zones, nodes, or racks
   - B) DoNotSchedule evaluates skew against the global minimum
   - C) ScheduleAnyway uses a spread preference
   - D) They automatically relocate existing Pods

<details>
<summary>Show Answer</summary>

**Answer: D) They automatically relocate existing Pods**

**Explanation:**
Spread constraints affect scheduling of incoming Pods. They do not move running Pods. With DoNotSchedule, maxSkew compares matching Pod count in the target domain to the global minimum; if eligible domains are fewer than minDomains, that minimum is zero. Match the incoming Pod labels to labelSelector so it participates in the count. A descheduler may evict eligible violating Pods, but does not guarantee a particular replacement placement.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: example-pod
  labels:
    app: web-server
spec:
  topologySpreadConstraints:
  - maxSkew: 1
    topologyKey: topology.kubernetes.io/zone
    whenUnsatisfiable: DoNotSchedule
    labelSelector:
      matchLabels:
        app: web-server
  containers:
  - name: nginx
    image: nginx
```
</details>

5. Which statement about QoS and eviction is false?
   - A) Guaranteed requires the appropriate equal CPU/memory request-limit configuration
   - B) Burstable covers configurations between Guaranteed and BestEffort
   - C) BestEffort has no CPU/memory requests or limits
   - D) Guaranteed Pods are always evicted first under pressure

<details>
<summary>Show Answer</summary>

**Answer: D) Guaranteed Pods are always evicted first under pressure**

**Explanation:**
Kubelet does not use QoS as a strict eviction sequence. It ranks usage above requests, priority, and usage relative to requests; disk pressure has different accounting. Guaranteed Pods can still be evicted or lost during failures. QoS is derived from resources, not directly assigned as a Pod field.
</details>

[Return to Learning Materials](../../core/08-scheduling-preemption-eviction.md)
