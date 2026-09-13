# Node Lifecycle Management Quiz

> This quiz tests your understanding of the [Node Lifecycle Management](../../eks-hybrid-nodes/07-node-lifecycle.md) document.

---

1. What is the primary purpose of setting `systemReserved` and `kubeReserved` in the NodeConfig kubelet configuration?
   - A) To automatically adjust pod resource requests
   - B) To reserve resources for system processes and Kubernetes components when calculating Node Allocatable
   - C) To increase the total resources available on the node
   - D) To determine pod scheduling priority

<details>
<summary>Show Answer</summary>

**Answer: B) To reserve resources for system processes and Kubernetes components when calculating Node Allocatable**

**Explanation:**
`systemReserved` reserves resources for the OS and system daemons (sshd, udev, etc.), while `kubeReserved` reserves resources for kubelet and containerd. The reservations reduce allocatable capacity. Enforcing host-process cgroup reservations needs additional configuration; these fields alone do not guarantee stability.

</details>

---

2. What is the difference between kubelet's `evictionHard` and `evictionSoft`?
   - A) `evictionHard` is a soft limit and `evictionSoft` is a hard limit
   - B) `evictionHard` has no soft observation grace; `evictionSoft` requires a sustained threshold
   - C) `evictionHard` only evicts pods, while `evictionSoft` shuts down the node
   - D) Both settings behave identically with only different names

<details>
<summary>Show Answer</summary>

**Answer: B) `evictionHard` has no soft observation grace; `evictionSoft` requires a sustained threshold**

**Explanation:**
The kubelet first attempts node-level reclaim and evicts Pods when needed. Hard thresholds have no soft observation period and evict without Pod termination grace. A soft threshold must persist for `evictionSoftGracePeriod`, while `evictionMaxPodGracePeriod` separately caps Pod termination grace. This does not prevent hard eviction or OOM.

</details>

---

3. According to the Kubernetes version skew policy, what is the oldest kubelet version that can run in the historical 1.31 API-server example (ignoring current EKS version availability)?
   - A) 1.27
   - B) 1.28
   - C) 1.29
   - D) 1.30

<details>
<summary>Show Answer</summary>

**Answer: B) 1.28**

**Explanation:**
According to the Kubernetes version skew policy, kubelet may be up to three minor versions older than the API server. With the API server at 1.31, kubelet is compatible with 1.31, 1.30, 1.29, and 1.28. Version 1.27 is n-4 and not supported.

</details>

---

4. What is the core principle of the canary upgrade strategy?
   - A) Upgrade all nodes simultaneously
   - B) Upgrade one node first, validate, then proceed with the rest
   - C) Delete nodes and create new ones
   - D) Perform in-place upgrades with zero downtime

<details>
<summary>Show Answer</summary>

**Answer: B) Upgrade one node first, validate, then proceed with the rest**

**Explanation:**
A canary upgrade upgrades a single "canary" node first and validates the result. If no issues are found, a rolling upgrade proceeds for the remaining nodes, minimizing risk.

</details>

---

5. What label does nodeadm automatically assign when initializing hybrid nodes?
   - A) `node-role.kubernetes.io/hybrid=true`
   - B) `topology.kubernetes.io/zone=on-premises`
   - C) `eks.amazonaws.com/compute-type=hybrid`
   - D) `kubernetes.io/os=hybrid`

<details>
<summary>Show Answer</summary>

**Answer: C) `eks.amazonaws.com/compute-type=hybrid`**

**Explanation:**
nodeadm automatically assigns the `eks.amazonaws.com/compute-type=hybrid` label during hybrid node initialization. This label does not need to be manually added to `--node-labels` and is used for Cilium affinity, workload placement, and more.

</details>

---

6. An SSM activation has expired, but its nodes are already registered. Which action is correct?
   - A) Extend the expiration date of the existing activation
   - B) Keep existing registrations; use a new activation only for required new registrations
   - C) Switch to IAM Roles Anywhere
   - D) Restart kubelet for automatic renewal

<details>
<summary>Show Answer</summary>

**Answer: B) Keep existing registrations; use a new activation only for required new registrations**

**Explanation:**
Activation expiration blocks new registrations. Already registered nodes remain managed until explicitly deregistered. Do not uninstall/re-register healthy nodes solely because the activation expired; agent credentials, role permissions and connectivity are separate concerns.

</details>

---

7. Nodes already match the control-plane minor version. What is the order for moving to the next minor version?
   - A) Upgrade nodes first, then the control plane
   - B) Upgrade the control plane and nodes simultaneously
   - C) Upgrade the control plane (EKS) first, then upgrade nodes
   - D) The order does not matter

<details>
<summary>Show Answer</summary>

**Answer: C) Upgrade the control plane (EKS) first, then upgrade nodes**

**Explanation:**
According to the Kubernetes version skew policy, kubelet cannot be newer than the API server. For this next-minor transition, upgrade the control plane before nodes. Lagging nodes may first be upgraded to the current control-plane version; that catch-up does not violate skew.

</details>

---

8. If `shutdownGracePeriod: 60s` and `shutdownGracePeriodCriticalPods: 20s` are configured, what total shutdown window is allocated to the regular-Pod group?
   - A) 20 seconds
   - B) 40 seconds
   - C) 60 seconds
   - D) 80 seconds

<details>
<summary>Show Answer</summary>

**Answer: B) 40 seconds**

**Explanation:**
`shutdownGracePeriodCriticalPods` is included within `shutdownGracePeriod`. Subtracting the 20 seconds reserved for critical pods from the total 60-second grace period leaves 40 seconds for regular pod termination. The final 20 seconds are budgeted for critical Pods. This describes configured windows, not guaranteed per-Pod grace during forced shutdown; individual terminationGracePeriodSeconds also applies.

</details>
