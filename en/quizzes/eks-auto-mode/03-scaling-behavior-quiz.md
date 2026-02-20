# EKS Auto Mode Scaling Behavior Quiz

> **Related Document**: [Scaling Behavior](../../eks-auto-mode/03-scaling-behavior.md)

## Multiple Choice Questions

### 1. What is the behavior of NodePool's `consolidationPolicy: WhenEmptyOrUnderutilized`?

- A) Only removes empty nodes
- B) Consolidates both empty and underutilized nodes
- C) Always keeps all nodes
- D) Only removes nodes at specific times

<details>
<summary>Show Answer</summary>

**Answer: B) Consolidates both empty and underutilized nodes**

**Explanation:**
The `WhenEmptyOrUnderutilized` policy consolidates not only empty nodes but also underutilized nodes to optimize costs. This allows consolidating workloads from multiple underutilized nodes onto fewer nodes.

```yaml
disruption:
  consolidationPolicy: WhenEmptyOrUnderutilized
  consolidateAfter: 1m  # Consolidate 1 minute after condition is met
```

**Comparison:**
- `WhenEmpty`: Only removes empty nodes (conservative)
- `WhenEmptyOrUnderutilized`: Consolidates empty + underutilized nodes (aggressive)

</details>

### 2. What is the kubectl command to check NodeClaim status?

- A) `kubectl get nodes --show-claims`
- B) `kubectl get nodeclaims`
- C) `kubectl describe karpenter claims`
- D) `kubectl get ec2-nodes`

<details>
<summary>Show Answer</summary>

**Answer: B) `kubectl get nodeclaims`**

**Explanation:**
NodeClaim is a resource that represents the state of a node being provisioned.

```bash
# List NodeClaims
kubectl get nodeclaims

# Detailed information for specific NodeClaim
kubectl describe nodeclaim <name>

# View NodeClaims with node information
kubectl get nodeclaims -o wide
```

</details>

### 3. Under what condition does node provisioning start when a Pending Pod occurs in Auto Mode?

- A) When Pod has been Pending for more than 5 minutes
- B) When no node satisfies the NodePool's requirements
- C) When total node count falls below threshold
- D) When manual scale-up command is executed

<details>
<summary>Show Answer</summary>

**Answer: B) When no node satisfies the NodePool's requirements**

**Explanation:**
Auto Mode analyzes the requirements of Pending Pods and immediately provisions a new node if no suitable node exists.

**Provisioning Flow:**
1. Pod enters Pending state
2. Karpenter analyzes Pod's resource requests, nodeSelector, affinity
3. Checks requirements of suitable NodePools
4. Selects optimal instance type
5. Launches EC2 instance (40-90 seconds)

</details>

### 4. In which cases does Consolidation NOT occur?

- A) When node has do-not-disrupt annotation
- B) When node only has DaemonSet Pods
- C) When consolidateAfter time has not elapsed
- D) All of the above

<details>
<summary>Show Answer</summary>

**Answer: D) All of the above**

**Explanation:**
Consolidation does not occur in the following situations:

1. **do-not-disrupt annotation**: Nodes or Pods with this annotation are excluded from consolidation
2. **Only DaemonSet Pods**: DaemonSets run on all nodes, so treated as empty node
3. **consolidateAfter not elapsed**: Must wait specified time after condition is met

```yaml
metadata:
  annotations:
    karpenter.sh/do-not-disrupt: "true"
```

</details>

### 5. What situations trigger Drift detection?

- A) When NodeClass spec changes
- B) When new AMI becomes available
- C) When security groups change
- D) All of the above

<details>
<summary>Show Answer</summary>

**Answer: D) All of the above**

**Explanation:**
Drift detection is triggered when the current state of a node differs from the desired state:

- **NodeClass changes**: AMI family, subnets, security groups, etc. changed
- **New AMI**: EKS optimized AMI updated
- **Security group changes**: Referenced security groups modified

When Drift is detected, nodes are replaced sequentially.

</details>

### 6. Which AMI family is recommended for optimizing node provisioning speed?

- A) AL2023
- B) Bottlerocket
- C) Ubuntu
- D) Amazon Linux 2

<details>
<summary>Show Answer</summary>

**Answer: B) Bottlerocket**

**Explanation:**
Bottlerocket is an OS designed specifically for containers, providing faster boot times than AL2023.

**Boot Time Comparison:**
- **AL2023**: 20-40 seconds
- **Bottlerocket**: 15-25 seconds

Additional Bottlerocket benefits:
- Smaller attack surface
- Immutable file system
- Automatic security updates

</details>
