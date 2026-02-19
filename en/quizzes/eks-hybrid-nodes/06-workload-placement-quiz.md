# EKS Hybrid Nodes Workload Placement Quiz

> **Related Document**: [Workload Placement](../../eks-hybrid-nodes/06-workload-placement.md)

## Multiple Choice Questions

### 1. Which is NOT a method used to place Pods on specific nodes in Kubernetes?

A. nodeSelector
B. Node Affinity
C. Taints/Tolerations
D. PodDisruptionBudget

<details>
<summary>Show Answer</summary>

**Answer: D. PodDisruptionBudget**

**Explanation:**
PodDisruptionBudget (PDB) is used to ensure minimum availability during voluntary disruptions, not for Pod placement.

**Pod Placement Methods:**
- **nodeSelector**: Simple label-based node selection
- **Node Affinity**: Complex rule-based node selection
- **Taints/Tolerations**: Restrict nodes to accept only specific Pods
- **Pod Affinity/Anti-Affinity**: Define placement relationships between Pods

```yaml
# nodeSelector example
spec:
  nodeSelector:
    location: onprem

# Node Affinity example
spec:
  affinity:
    nodeAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
        nodeSelectorTerms:
        - matchExpressions:
          - key: gpu
            operator: In
            values: ["nvidia-a100"]
```

</details>

### 2. What is the correct command to set a Taint on Hybrid Nodes so only GPU workloads are placed there?

A. kubectl label node hybrid-node-1 gpu=true
B. kubectl taint node hybrid-node-1 dedicated=gpu:NoSchedule
C. kubectl annotate node hybrid-node-1 gpu=nvidia
D. kubectl cordon hybrid-node-1

<details>
<summary>Show Answer</summary>

**Answer: B. kubectl taint node hybrid-node-1 dedicated=gpu:NoSchedule**

**Explanation:**
Taints restrict scheduling to only Pods that tolerate the taint.

```bash
# Set Taint
kubectl taint node hybrid-node-1 dedicated=gpu:NoSchedule

# Verify Taint
kubectl describe node hybrid-node-1 | grep Taints
```

```yaml
# Toleration that allows the Taint
apiVersion: v1
kind: Pod
metadata:
  name: gpu-workload
spec:
  tolerations:
  - key: "dedicated"
    operator: "Equal"
    value: "gpu"
    effect: "NoSchedule"
  containers:
  - name: cuda-app
    image: nvidia/cuda:12.0-runtime
    resources:
      limits:
        nvidia.com/gpu: 1
```

**Taint Effect Types:**
- **NoSchedule**: Prevent new Pod scheduling
- **PreferNoSchedule**: Avoid scheduling if possible
- **NoExecute**: Also evict existing Pods

</details>

### 3. In a cloud bursting strategy, what method is used to move workloads to cloud nodes when on-premises resources are insufficient?

A. Manually delete and recreate Pods
B. Use Node Affinity's preferredDuringSchedulingIgnoredDuringExecution
C. Place all Pods in cloud
D. Delete and recreate cluster

<details>
<summary>Show Answer</summary>

**Answer: B. Use Node Affinity's preferredDuringSchedulingIgnoredDuringExecution**

**Explanation:**
Cloud bursting implements an on-premises preferred, cloud fallback strategy.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: burst-workload
spec:
  replicas: 10
  template:
    spec:
      affinity:
        nodeAffinity:
          # Prefer on-premises (not required)
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 100
            preference:
              matchExpressions:
              - key: location
                operator: In
                values: ["onprem"]
          - weight: 50
            preference:
              matchExpressions:
              - key: location
                operator: In
                values: ["cloud"]
      containers:
      - name: app
        image: myapp:v1
```

**Cloud Bursting Pattern:**
```
[On-premises capacity: 8 nodes]    [Cloud capacity: Unlimited]
      | Preferred                       | Fallback
  Pods 1-8 placed -----------------> Pods 9+ overflow
```

</details>

### 4. What does maxSkew mean when using TopologySpreadConstraints to evenly distribute Pods across zones?

A. Minimum Pod count
B. Maximum difference in Pod count between zones
C. Total Pod count
D. Maximum Pods per node

<details>
<summary>Show Answer</summary>

**Answer: B. Maximum difference in Pod count between zones**

**Explanation:**
`maxSkew` defines the maximum imbalance in Pod count between topology domains (e.g., zones).

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: distributed-app
spec:
  replicas: 6
  template:
    spec:
      topologySpreadConstraints:
      - maxSkew: 1
        topologyKey: topology.kubernetes.io/zone
        whenUnsatisfiable: DoNotSchedule
        labelSelector:
          matchLabels:
            app: distributed-app
```

**maxSkew=1 Example:**
```
Zone A: 2 Pods  |  Zone B: 2 Pods  |  Zone C: 2 Pods  (Balanced)
Zone A: 3 Pods  |  Zone B: 2 Pods  |  Zone C: 2 Pods  (Skew=1, Allowed)
Zone A: 4 Pods  |  Zone B: 2 Pods  |  Zone C: 2 Pods  (Skew=2, Not Allowed)
```

**whenUnsatisfiable Options:**
- **DoNotSchedule**: Reject scheduling if constraint violated
- **ScheduleAnyway**: Schedule even if constraint violated (best-effort)

</details>

### 5. How do you place Pods on nodes where data resides for data locality considerations?

A. Random scheduling
B. Use node labels and nodeSelector for data-proximity placement
C. Always select cloud nodes
D. Pod name alphabetical order

<details>
<summary>Show Answer</summary>

**Answer: B. Use node labels and nodeSelector for data-proximity placement**

**Explanation:**
For data locality, label nodes where data is stored and place Pods using those labels.

```bash
# Label nodes with data location
kubectl label node storage-node-1 data-location=primary-storage
kubectl label node storage-node-2 data-location=replica-storage
```

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: data-processor
spec:
  template:
    spec:
      nodeSelector:
        data-location: primary-storage
      containers:
      - name: processor
        image: data-processor:v1
        volumeMounts:
        - name: local-data
          mountPath: /data
      volumes:
      - name: local-data
        hostPath:
          path: /mnt/data
```

**Data Locality Benefits:**
- Minimize network latency
- Reduce data transfer costs
- Improve processing performance

</details>

### 6. Why use Pod Anti-Affinity to prevent Pods of the same application from being placed on the same node?

A. Cost savings
B. High availability and fault isolation
C. Network speed improvement
D. Storage savings

<details>
<summary>Show Answer</summary>

**Answer: B. High availability and fault isolation**

**Explanation:**
Pod Anti-Affinity distributes Pods of the same application across different nodes to maintain service availability even during single node failures.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ha-webapp
spec:
  replicas: 3
  template:
    metadata:
      labels:
        app: ha-webapp
    spec:
      affinity:
        podAntiAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
          - labelSelector:
              matchExpressions:
              - key: app
                operator: In
                values: ["ha-webapp"]
            topologyKey: kubernetes.io/hostname
      containers:
      - name: web
        image: nginx:1.25
```

**Result:**
```
Node 1: ha-webapp-pod-1
Node 2: ha-webapp-pod-2
Node 3: ha-webapp-pod-3
(Only 1 placed per node)
```

If a node fails, only 1 Pod is affected, and the remaining 2 continue to provide service.

</details>

