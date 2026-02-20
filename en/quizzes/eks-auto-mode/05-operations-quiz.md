# EKS Auto Mode Operations Quiz

> **Related Document**: [Operations](../../eks-auto-mode/05-operations.md)

## Multiple Choice Questions

### 1. What is the NodePool Disruption Budget setting to minimize node disruptions during business hours?

- A) `nodes: "100%"`
- B) `nodes: "0"` with schedule
- C) `consolidateAfter: 0s`
- D) `consolidationPolicy: Never`

<details>
<summary>Show Answer</summary>

**Answer: B) `nodes: "0"` with schedule**

**Explanation:**
Setting `nodes: "0"` together with a schedule in Disruption Budget completely prevents node disruptions during specific time windows.

```yaml
disruption:
  consolidationPolicy: WhenEmptyOrUnderutilized
  consolidateAfter: 5m
  budgets:
    # Default: Only 10% of total nodes can be disrupted simultaneously
    - nodes: "10%"

    # Business hours: No disruptions
    - nodes: "0"
      schedule: "0 9-18 * * mon-fri"  # Mon-Fri 9-18
      duration: 9h
```

</details>

### 2. What does `minAvailable: 80%` mean in a PodDisruptionBudget (PDB)?

- A) Maximum 80% of Pods can run
- B) Minimum 80% of Pods must always be running
- C) 80% probability of Pod retention
- D) Protect Pods for 80 seconds

<details>
<summary>Show Answer</summary>

**Answer: B) Minimum 80% of Pods must always be running**

**Explanation:**
PDB's `minAvailable` specifies the minimum number or percentage of Pods that must always be running.

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: web-pdb
spec:
  minAvailable: 80%
  selector:
    matchLabels:
      app: web
```

Alternatively, you can use `maxUnavailable`:
```yaml
spec:
  maxUnavailable: 1  # Only 1 Pod can be disrupted simultaneously
```

</details>

### 3. What is the first resource to check when diagnosing Auto Mode node issues?

- A) Pod logs
- B) NodeClaim status
- C) EC2 console
- D) CloudWatch metrics

<details>
<summary>Show Answer</summary>

**Answer: B) NodeClaim status**

**Explanation:**
NodeClaim is the key resource that tracks the node provisioning process and status.

```bash
# Check NodeClaim status
kubectl get nodeclaims

# Check details and events
kubectl describe nodeclaim <name>

# Check provisioning failure causes
kubectl get nodeclaims -o yaml | grep -A 10 status
```

Typical troubleshooting order:
1. Check NodeClaim status
2. Review NodePool configuration
3. Verify IAM roles/policies
4. Validate subnets/security groups

</details>

### 4. What is the correct usage of do-not-disrupt annotation?

- A) `kubernetes.io/do-not-disrupt: "true"`
- B) `karpenter.sh/do-not-disrupt: "true"`
- C) `eks.amazonaws.com/no-disrupt: "true"`
- D) `node.kubernetes.io/exclude-disruption: "true"`

<details>
<summary>Show Answer</summary>

**Answer: B) `karpenter.sh/do-not-disrupt: "true"`**

**Explanation:**
Adding this annotation to a Pod or Node excludes it from Karpenter's consolidation or drift replacement.

```yaml
# Apply to Pod
apiVersion: v1
kind: Pod
metadata:
  name: critical-pod
  annotations:
    karpenter.sh/do-not-disrupt: "true"
spec:
  containers:
    - name: app
      image: myapp:latest

# Apply to Node
kubectl annotate node <node-name> karpenter.sh/do-not-disrupt=true
```

</details>

### 5. What is the recommended tool for monitoring node status in an Auto Mode cluster?

- A) kubectl top nodes only
- B) Container Insights + kubectl combination
- C) Check directly in EC2 console
- D) AWS CLI only

<details>
<summary>Show Answer</summary>

**Answer: B) Container Insights + kubectl combination**

**Explanation:**
Use a combination of tools for effective monitoring.

```bash
# Real-time monitoring
watch -n 5 'echo "=== Pending Pods ===" && \
kubectl get pods -A --field-selector=status.phase=Pending && \
echo "=== Node Status ===" && kubectl get nodes -o wide'

# Check resource usage
kubectl top nodes
kubectl top pods -A

# Check NodePool status
kubectl get nodepools
kubectl describe nodepool <name>
```

Container Insights metrics:
- Node CPU/memory utilization
- Pod scheduling latency
- Container restart count

</details>

### 6. What NodePool field should be set to automate node updates in Day-2 operations?

- A) `autoUpdate: true`
- B) `expireAfter` setting
- C) `updatePolicy: Rolling`
- D) `refreshInterval: 24h`

<details>
<summary>Show Answer</summary>

**Answer: B) `expireAfter` setting**

**Explanation:**
Setting `expireAfter` ensures nodes are automatically replaced after the specified time, applying latest AMI and security patches.

```yaml
spec:
  template:
    spec:
      expireAfter: 168h  # Auto-replace after 7 days
```

Day-2 operations automation settings:
- `expireAfter`: Regular node replacement
- `consolidationPolicy`: Cost optimization
- Disruption Budget: Minimize service impact

</details>

### 7. What is the recommended Disruption Budget setting for rolling updates in production environments?

- A) `nodes: "100%"` for fast updates
- B) `nodes: "10%"` or absolute value for gradual updates
- C) Disable Disruption Budget
- D) `nodes: "50%"` for medium speed

<details>
<summary>Show Answer</summary>

**Answer: B) `nodes: "10%"` or absolute value for gradual updates**

**Explanation:**
In production environments, update gradually while minimizing service impact.

```yaml
disruption:
  consolidationPolicy: WhenEmptyOrUnderutilized
  consolidateAfter: 5m
  budgets:
    # Default: Gradual replacement at 10%
    - nodes: "10%"

    # Peak hours: More conservative
    - nodes: "1"
      schedule: "0 9-18 * * mon-fri"
      duration: 9h

    # Maintenance window: More aggressive
    - nodes: "30%"
      schedule: "0 2-4 * * sun"
      duration: 2h
```

</details>

### 8. What are the key metrics for Auto Mode node-related CloudWatch alarms?

- A) EC2 instance status only
- B) Pending Pod count, node provisioning time, workload availability
- C) Cost metrics only
- D) Network traffic only

<details>
<summary>Show Answer</summary>

**Answer: B) Pending Pod count, node provisioning time, workload availability**

**Explanation:**
Key metrics to monitor in Auto Mode operations:

| Metric | Normal Range | Alarm Condition |
|--------|--------------|-----------------|
| Pending Pod count | 0-5 | > 10 for 5 min |
| Node provisioning time | < 90 sec | > 120 sec |
| Workload availability | > 99.9% | < 99.5% |
| API response time | < 200ms | > 500ms |

Enable CloudWatch Container Insights to automatically collect these metrics.

</details>
