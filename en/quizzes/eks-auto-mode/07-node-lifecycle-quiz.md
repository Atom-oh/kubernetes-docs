# EKS Auto Mode Node Lifecycle Quiz

> **Related Document**: [Node Lifecycle](../../eks-auto-mode/07-node-lifecycle.md)

## Multiple Choice Questions

### 1. What is the configuration field name for periodically replacing nodes in NodePool?

- A) `nodeLifetime`
- B) `maxAge`
- C) `expireAfter`
- D) `rotationPeriod`

<details>
<summary>Show Answer</summary>

**Answer: C) `expireAfter`**

**Explanation:**
The `expireAfter` field allows you to set the maximum node lifetime for periodic node replacement to apply security patches or AMI updates.

```yaml
spec:
  template:
    spec:
      # Set maximum node lifetime
      expireAfter: 168h  # Auto-replace after 7 days
```

**Common settings:**
- Development environment: 336h (14 days)
- Staging: 168h (7 days)
- Production: 72h ~ 168h (3-7 days)
- Security-critical environment: 24h ~ 48h (1-2 days)

</details>

### 2. What happens when a node with expireAfter set expires?

- A) Node is immediately deleted
- B) Node is cordoned, drained, then deleted
- C) Only notification sent to administrator
- D) Node automatically reboots

<details>
<summary>Show Answer</summary>

**Answer: B) Node is cordoned, drained, then deleted**

**Explanation:**
When a node expires, Karpenter executes a graceful process:

1. **Cordon**: Block new Pod scheduling
2. **Drain**: Move existing Pods to other nodes
3. **Delete**: Terminate EC2 instance

PodDisruptionBudgets and Disruption Budgets are respected during this process.

```yaml
disruption:
  budgets:
    # Expiration-based replacement also follows this budget
    - nodes: "10%"
```

</details>

### 3. Which AMI provides faster boot time between AL2023 and Bottlerocket?

- A) AL2023
- B) Bottlerocket
- C) They are the same
- D) Depends on instance type

<details>
<summary>Show Answer</summary>

**Answer: B) Bottlerocket**

**Explanation:**
Bottlerocket is an OS optimized for container workloads, providing faster boot times than AL2023.

**Boot Time Comparison:**
| AMI | Boot Time | Characteristics |
|-----|-----------|-----------------|
| AL2023 | 20-40 sec | General packages, flexibility |
| Bottlerocket | 15-25 sec | Container-only, minimal OS |

```yaml
apiVersion: eks.amazonaws.com/v1
kind: NodeClass
metadata:
  name: fast-boot
spec:
  amiFamily: Bottlerocket  # Fast boot
```

Additional Bottlerocket benefits:
- Immutable root file system
- Automatic security updates
- Smaller attack surface

</details>

### 4. What happens when Drift is detected on existing nodes due to AMI updates?

- A) Node is automatically updated in-place
- B) Nodes are sequentially replaced with new AMI
- C) Replacement after administrator approval
- D) Nothing happens

<details>
<summary>Show Answer</summary>

**Answer: B) Nodes are sequentially replaced with new AMI**

**Explanation:**
When a new AMI becomes available, EKS Auto Mode detects Drift and sequentially replaces nodes.

**Drift Detection Conditions:**
- New EKS optimized AMI release
- amiFamily change in NodeClass
- Security group changes
- Subnet setting changes

```yaml
# Drift-based replacement also follows Disruption Budget
disruption:
  budgets:
    - nodes: "10%"  # Only 10% replaced at a time
```

</details>

### 5. What is a potential trade-off when setting expireAfter short for node freshness?

- A) Cost reduction
- B) Potential temporary performance degradation due to increased node replacement frequency
- C) Increased security vulnerabilities
- D) Improved cluster stability

<details>
<summary>Show Answer</summary>

**Answer: B) Potential temporary performance degradation due to increased node replacement frequency**

**Explanation:**
Short expireAfter enhances security but has the following trade-offs:

**Advantages:**
- Latest security patches applied
- Quick AMI update application
- Prevent node drift

**Disadvantages:**
- Temporary capacity reduction during node replacement
- More Pod rescheduling
- Additional interrupt possibility for Spot instances

**Recommendations:**
```yaml
# Balanced setting
spec:
  template:
    spec:
      expireAfter: 168h  # 7 days
  disruption:
    budgets:
      - nodes: "10%"  # Limit concurrent replacement
```

</details>

### 6. What takes precedence when both Consolidation and Expiration are triggered simultaneously?

- A) Consolidation always takes precedence
- B) Expiration always takes precedence
- C) Whichever reaches node replacement condition first executes
- D) Administrator must choose

<details>
<summary>Show Answer</summary>

**Answer: C) Whichever reaches node replacement condition first executes**

**Explanation:**
Karpenter evaluates multiple disruption reasons independently and executes when conditions are met.

**Disruption Priority (typical evaluation order):**
1. **Drift**: Configuration change or AMI update detected
2. **Expiration**: expireAfter time exceeded
3. **Consolidation**: Underutilized or empty node

```yaml
# Example: 5-day-old underutilized node
# - expireAfter: 7 days -> Not expired yet
# - Consolidation condition met -> Replaced by Consolidation

# Example: 8-day-old normal utilization node
# - expireAfter: 7 days -> Expired
# - Replaced by Expiration
```

</details>

### 7. What method is used when nodes need to be replaced immediately for security patch application?

- A) Set expireAfter to 0
- B) Add Drift annotation to node
- C) Update NodeClass to trigger Drift or drain node
- D) Restart cluster

<details>
<summary>Show Answer</summary>

**Answer: C) Update NodeClass to trigger Drift or drain node**

**Explanation:**
Emergency security patch application methods:

**Method 1: NodeClass Update (Recommended)**
```yaml
# Trigger drift by changing tags or settings
apiVersion: eks.amazonaws.com/v1
kind: NodeClass
metadata:
  name: default
spec:
  tags:
    SecurityPatch: "2025-02-19"  # Drift triggered by tag change
```

**Method 2: Manual drain**
```bash
# Drain specific node
kubectl drain <node-name> --ignore-daemonsets --delete-emptydir-data

# Delete node (Auto Mode provisions new node)
kubectl delete node <node-name>
```

**Method 3: Rolling replacement**
```bash
# Sequentially replace all nodes
kubectl delete nodes -l karpenter.sh/nodepool=general-purpose
```

</details>

### 8. What behavior results from setting expireAfter to Never?

- A) Node expires immediately
- B) Time-based automatic replacement is disabled
- C) Setting is invalidated and default applied
- D) Error occurs

<details>
<summary>Show Answer</summary>

**Answer: B) Time-based automatic replacement is disabled**

**Explanation:**
Setting `expireAfter: Never` disables time-based node expiration.

```yaml
spec:
  template:
    spec:
      expireAfter: Never  # Disable time-based expiration
```

**Cautions:**
- Drift and Consolidation still work
- Security patch application may be delayed
- Recommended only for long-running workloads

**Recommended Use Cases:**
- Stateful workloads (databases)
- Very long-running jobs
- Environments with manual maintenance schedules

</details>
