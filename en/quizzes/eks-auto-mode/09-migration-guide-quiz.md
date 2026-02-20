# EKS Auto Mode Migration Guide Quiz

> **Related Document**: [Migration Guide](../../eks-auto-mode/09-migration-guide.md)

## Multiple Choice Questions

### 1. What is the first step when migrating from managed node groups to Auto Mode?

- A) Immediately delete existing node groups
- B) Analyze current state (check node resource usage, workload distribution)
- C) Create Auto Mode NodePool
- D) Drain all Pods

<details>
<summary>Show Answer</summary>

**Answer: B) Analyze current state (check node resource usage, workload distribution)**

**Explanation:**
The first step in migration is to thoroughly analyze your current environment.

**Migration Steps:**
1. **Analyze current state** - Check node groups, resource usage, workload distribution
2. Enable Auto Mode
3. Configure NodePool
4. Migrate workloads
5. Scale down existing node groups
6. Delete existing node groups
7. Validate and optimize

```bash
# Check current node groups
eksctl get nodegroup --cluster my-cluster

# Analyze node resource usage
kubectl top nodes

# Check workload distribution
kubectl get pods -A -o wide | awk '{print $8}' | sort | uniq -c
```

</details>

### 2. How do you allow coexistence of existing node groups and Auto Mode during migration?

- A) Not possible, must be sequential only
- B) Separate workloads using nodeSelector
- C) Requires separate cluster
- D) Requires AWS Support ticket

<details>
<summary>Show Answer</summary>

**Answer: B) Separate workloads using nodeSelector**

**Explanation:**
During the coexistence period, use nodeSelector and affinity to separate workloads.

```yaml
# Workloads pinned to existing node groups
apiVersion: apps/v1
kind: Deployment
metadata:
  name: legacy-critical-app
spec:
  template:
    spec:
      nodeSelector:
        eks.amazonaws.com/nodegroup: old-nodegroup

---
# Workloads that can be migrated to Auto Mode
apiVersion: apps/v1
kind: Deployment
metadata:
  name: migrated-app
spec:
  template:
    spec:
      affinity:
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
              - matchExpressions:
                  - key: karpenter.sh/nodepool
                    operator: Exists
```

</details>

### 3. What is the recommended order for gradual workload migration?

- A) Production -> Staging -> Development
- B) Development -> Staging -> Production (non-critical workloads first)
- C) All workloads simultaneously
- D) Random order

<details>
<summary>Show Answer</summary>

**Answer: B) Development -> Staging -> Production (non-critical workloads first)**

**Explanation:**
Gradual migration minimizes risk.

```yaml
# Step 1: Migrate non-critical workloads
apiVersion: apps/v1
kind: Deployment
metadata:
  name: dev-app
spec:
  template:
    spec:
      affinity:
        nodeAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
            - weight: 100
              preference:
                matchExpressions:
                  - key: node-type
                    operator: In
                    values: ["auto-mode"]
```

**Migration Order:**
1. Development environment workloads
2. Staging workloads
3. Production non-critical workloads
4. Production critical workloads

</details>

### 4. What is the sequence of steps when rollback is needed?

- A) Delete and recreate cluster
- B) Delete NodePool -> Scale up existing node groups -> Migrate workloads
- C) Contact AWS Support
- D) Only disable Auto Mode

<details>
<summary>Show Answer</summary>

**Answer: B) Delete NodePool -> Scale up existing node groups -> Migrate workloads**

**Explanation:**
Rollback proceeds in reverse order.

```bash
#!/bin/bash
# rollback.sh

# 1. Disable Auto Mode NodePool
kubectl delete nodepool migration-pool

# 2. Scale up existing node groups
eksctl scale nodegroup \
    --cluster my-cluster \
    --name old-nodegroup \
    --nodes 10 \
    --nodes-min 3

# 3. Migrate workloads back to existing nodes
kubectl patch deployment migrated-app -p '
{
  "spec": {
    "template": {
      "spec": {
        "nodeSelector": {
          "eks.amazonaws.com/nodegroup": "old-nodegroup"
        },
        "affinity": null
      }
    }
  }
}'

# 4. Drain Auto Mode Pods
for node in $(kubectl get nodes -l karpenter.sh/nodepool=migration-pool -o name); do
    kubectl drain $node --ignore-daemonsets --delete-emptydir-data
done
```

</details>

### 5. What is the recommended method for gradually scaling down existing node groups?

- A) Scale down to 0 immediately
- B) Scale down by 50% incrementally with stabilization check
- C) Scale down by only 1
- D) Drain all nodes simultaneously

<details>
<summary>Show Answer</summary>

**Answer: B) Scale down by 50% incrementally with stabilization check**

**Explanation:**
Gradual scale-down minimizes service impact.

```bash
#!/bin/bash
CLUSTER="my-cluster"
NODEGROUP="old-nodegroup"
CURRENT_SIZE=$(eksctl get nodegroup --cluster $CLUSTER --name $NODEGROUP -o json | jq -r '.[0].DesiredCapacity')

# Scale down by 50%
while [ $CURRENT_SIZE -gt 0 ]; do
    NEW_SIZE=$((CURRENT_SIZE / 2))
    if [ $NEW_SIZE -lt 1 ]; then
        NEW_SIZE=0
    fi

    echo "Scaling from $CURRENT_SIZE to $NEW_SIZE"
    eksctl scale nodegroup --cluster $CLUSTER --name $NODEGROUP \
        --nodes $NEW_SIZE --nodes-min 0

    # Wait for stabilization
    sleep 300

    # Check workload status
    kubectl get pods -A --field-selector=status.phase=Pending

    CURRENT_SIZE=$NEW_SIZE
done
```

</details>

### 6. Which is NOT a key metric to monitor during migration?

- A) Pending Pod count
- B) Node provisioning time
- C) EC2 instance cost
- D) Workload availability

<details>
<summary>Show Answer</summary>

**Answer: C) EC2 instance cost**

**Explanation:**
During migration, service stability is the top priority, so monitor the following metrics.

| Metric | Normal Range | Alarm Condition |
|--------|--------------|-----------------|
| Pending Pod count | 0-5 | > 10 for 5 min |
| Node provisioning time | < 90 sec | > 120 sec |
| Workload availability | > 99.9% | < 99.5% |
| API response time | < 200ms | > 500ms |

Cost is checked during the optimization phase after migration is complete.

```bash
# Real-time monitoring
watch -n 5 'echo "=== Pending Pods ===" && \
kubectl get pods -A --field-selector=status.phase=Pending && \
echo "=== Node Status ===" && kubectl get nodes -o wide'
```

</details>

### 7. What is NOT an item to verify after migration is complete?

- A) Verify all workloads running normally
- B) Verify Pod distribution on Auto Mode nodes
- C) Complete deletion of existing node groups
- D) Verify NodePool status

<details>
<summary>Show Answer</summary>

**Answer: C) Complete deletion of existing node groups**

**Explanation:**
At the verification point, keep existing node groups to preserve rollback options. Deletion proceeds after confirming stability.

**Verification Checklist:**
1. Verify all Pods in Running state
2. Verify workload distribution on Auto Mode nodes
3. NodePool and NodeClaim normal status
4. Application performance testing
5. Normal log and metric collection
6. **Delete existing node groups after confirming stability for a period (1-2 weeks)**

</details>

### 8. What is the precaution when transitioning from a cluster using Karpenter directly to Auto Mode?

- A) Direct transition possible
- B) Possible conflict with existing Karpenter resources, transition after removing Karpenter
- C) Simultaneous operation recommended
- D) Additional cost incurred

<details>
<summary>Show Answer</summary>

**Answer: B) Possible conflict with existing Karpenter resources, transition after removing Karpenter**

**Explanation:**
Auto Mode uses Karpenter internally, so it can conflict with existing self-managed Karpenter.

**Transition Procedure:**
1. Backup existing Karpenter NodePool configuration
2. Temporarily migrate Karpenter-managed workloads to managed node groups
3. Remove self-managed Karpenter
4. Enable Auto Mode
5. Configure Auto Mode NodePool (reference backup)
6. Migrate workloads

```bash
# Verify before removing Karpenter
kubectl get nodepools
kubectl get nodeclaims
kubectl get nodes -l karpenter.sh/nodepool

# Remove Karpenter
helm uninstall karpenter -n karpenter
kubectl delete namespace karpenter
```

</details>
