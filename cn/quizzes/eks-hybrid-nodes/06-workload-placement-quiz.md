# EKS Hybrid Nodes 工作负载放置测验

> **相关文档**: [Workload Placement](../../eks-hybrid-nodes/06-workload-placement.md)

## 选择题

### 1. 以下哪一项不是在 Kubernetes 中将 Pods 放置到特定 Nodes 上的方法？

A. nodeSelector
B. Node Affinity
C. Taints/Tolerations
D. PodDisruptionBudget

<details>
<summary>显示答案</summary>

**答案：D. PodDisruptionBudget**

**解释：**
PodDisruptionBudget (PDB) 用于确保自愿中断期间的最低可用性，而不是用于 Pod 放置。

**Pod 放置方法：**
- **nodeSelector**: 基于标签的简单 Node 选择
- **Node Affinity**: 基于复杂规则的 Node 选择
- **Taints/Tolerations**: 限制 Nodes 只接受特定 Pods
- **Pod Affinity/Anti-Affinity**: 定义 Pods 之间的放置关系

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

### 2. 在 Hybrid Nodes 上设置 Taint 以便只将 GPU workloads 放置到那里，正确的命令是什么？

A. kubectl label node hybrid-node-1 gpu=true
B. kubectl taint node hybrid-node-1 dedicated=gpu:NoSchedule
C. kubectl annotate node hybrid-node-1 gpu=nvidia
D. kubectl cordon hybrid-node-1

<details>
<summary>显示答案</summary>

**答案：B. kubectl taint node hybrid-node-1 dedicated=gpu:NoSchedule**

**解释：**
Taints 会限制调度，只有能够容忍该 taint 的 Pods 才能被调度。

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

**Taint Effect 类型：**
- **NoSchedule**: 阻止新的 Pod 调度
- **PreferNoSchedule**: 如果可能，避免调度
- **NoExecute**: 同时驱逐现有 Pods

</details>

### 3. 在 cloud bursting 策略中，当本地资源不足时，使用什么方法将 workloads 移动到 cloud nodes？

A. 手动删除并重新创建 Pods
B. 使用 Node Affinity 的 preferredDuringSchedulingIgnoredDuringExecution
C. 将所有 Pods 放置在 cloud 中
D. 删除并重新创建 cluster

<details>
<summary>显示答案</summary>

**答案：B. 使用 Node Affinity 的 preferredDuringSchedulingIgnoredDuringExecution**

**解释：**
Cloud bursting 实现的是优先本地、cloud 回退的策略。

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

**Cloud Bursting 模式：**
```
[On-premises capacity: 8 nodes]    [Cloud capacity: Unlimited]
      | Preferred                       | Fallback
  Pods 1-8 placed -----------------> Pods 9+ overflow
```

</details>

### 4. 使用 TopologySpreadConstraints 在 zones 之间均匀分布 Pods 时，maxSkew 表示什么？

A. 最小 Pod 数量
B. zones 之间 Pod 数量的最大差异
C. Pod 总数
D. 每个 Node 的最大 Pods 数量

<details>
<summary>显示答案</summary>

**答案：B. zones 之间 Pod 数量的最大差异**

**解释：**
`maxSkew` 定义 topology domains（例如 zones）之间 Pod 数量的最大不平衡程度。

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

**maxSkew=1 示例：**
```
Zone A: 2 Pods  |  Zone B: 2 Pods  |  Zone C: 2 Pods  (Balanced)
Zone A: 3 Pods  |  Zone B: 2 Pods  |  Zone C: 2 Pods  (Skew=1, Allowed)
Zone A: 4 Pods  |  Zone B: 2 Pods  |  Zone C: 2 Pods  (Skew=2, Not Allowed)
```

**whenUnsatisfiable 选项：**
- **DoNotSchedule**: 如果违反约束，则拒绝调度
- **ScheduleAnyway**: 即使违反约束也进行调度（尽力而为）

</details>

### 5. 出于 data locality 考虑，如何将 Pods 放置到数据所在的 Nodes 上？

A. 随机调度
B. 使用 Node labels 和 nodeSelector 进行数据邻近放置
C. 始终选择 cloud nodes
D. 按 Pod 名称字母顺序

<details>
<summary>显示答案</summary>

**答案：B. 使用 Node labels 和 nodeSelector 进行数据邻近放置**

**解释：**
对于 data locality，请标记存储数据的 Nodes，并使用这些 labels 放置 Pods。

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

**Data Locality 优势：**
- 最大限度降低网络延迟
- 降低数据传输成本
- 提高处理性能

</details>

### 6. 为什么使用 Pod Anti-Affinity 来防止同一应用的 Pods 被放置在同一个 Node 上？

A. 节省成本
B. 高可用性和故障隔离
C. 提高网络速度
D. 节省存储

<details>
<summary>显示答案</summary>

**答案：B. 高可用性和故障隔离**

**解释：**
Pod Anti-Affinity 会将同一应用的 Pods 分布到不同 Nodes 上，以便即使单个 Node 发生故障，也能保持服务可用性。

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

**结果：**
```
Node 1: ha-webapp-pod-1
Node 2: ha-webapp-pod-2
Node 3: ha-webapp-pod-3
(Only 1 placed per node)
```

如果某个 Node 发生故障，只有 1 个 Pod 受到影响，其余 2 个会继续提供服务。

</details>
