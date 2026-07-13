# EKS Hybrid Nodes Workload Placement (ワークロード配置) クイズ

> **関連ドキュメント**: [Workload Placement](../../eks-hybrid-nodes/06-workload-placement.md)

## 多肢選択問題

### 1. Kubernetes で特定の Node に Pod を配置するために使われる方法ではないものはどれですか？

A. nodeSelector
B. Node Affinity
C. Taints/Tolerations
D. PodDisruptionBudget

<details>
<summary>回答を表示</summary>

**回答: D. PodDisruptionBudget**

**解説:**
PodDisruptionBudget (PDB) は、自発的な中断中に最小可用性を確保するために使用されるもので、Pod placement のためではありません。

**Pod Placement の方法:**
- **nodeSelector**: シンプルな label ベースの Node 選択
- **Node Affinity**: 複雑な rule ベースの Node 選択
- **Taints/Tolerations**: 特定の Pod のみを受け入れるよう Node を制限
- **Pod Affinity/Anti-Affinity**: Pod 間の placement 関係を定義

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

### 2. GPU workload のみが配置されるように Hybrid Nodes に Taint を設定する正しい command はどれですか？

A. kubectl label node hybrid-node-1 gpu=true
B. kubectl taint node hybrid-node-1 dedicated=gpu:NoSchedule
C. kubectl annotate node hybrid-node-1 gpu=nvidia
D. kubectl cordon hybrid-node-1

<details>
<summary>回答を表示</summary>

**回答: B. kubectl taint node hybrid-node-1 dedicated=gpu:NoSchedule**

**解説:**
Taint は、その Taint を許容する Toleration を持つ Pod のみに scheduling を制限します。

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

**Taint Effect の種類:**
- **NoSchedule**: 新しい Pod scheduling を防止
- **PreferNoSchedule**: 可能な場合は scheduling を避ける
- **NoExecute**: 既存の Pod も evict する

</details>

### 3. Cloud bursting strategy では、オンプレミスの resource が不足した場合に workload を cloud Node へ移動するために使われる方法はどれですか？

A. Pod を手動で削除して再作成する
B. Node Affinity の preferredDuringSchedulingIgnoredDuringExecution を使用する
C. すべての Pod を cloud に配置する
D. cluster を削除して再作成する

<details>
<summary>回答を表示</summary>

**回答: B. Node Affinity の preferredDuringSchedulingIgnoredDuringExecution を使用する**

**解説:**
Cloud bursting は、オンプレミスを優先し、cloud へ fallback する strategy を実装します。

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

**Cloud Bursting パターン:**
```
[On-premises capacity: 8 nodes]    [Cloud capacity: Unlimited]
      | Preferred                       | Fallback
  Pods 1-8 placed -----------------> Pods 9+ overflow
```

</details>

### 4. TopologySpreadConstraints を使用して Pod を zone 全体に均等に分散する場合、maxSkew は何を意味しますか？

A. 最小 Pod 数
B. zone 間の Pod 数の最大差
C. 合計 Pod 数
D. Node あたりの最大 Pod 数

<details>
<summary>回答を表示</summary>

**回答: B. zone 間の Pod 数の最大差**

**解説:**
`maxSkew` は、topology domain（例: zone）間の Pod 数における最大 imbalance を定義します。

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

**maxSkew=1 の例:**
```
Zone A: 2 Pods  |  Zone B: 2 Pods  |  Zone C: 2 Pods  (Balanced)
Zone A: 3 Pods  |  Zone B: 2 Pods  |  Zone C: 2 Pods  (Skew=1, Allowed)
Zone A: 4 Pods  |  Zone B: 2 Pods  |  Zone C: 2 Pods  (Skew=2, Not Allowed)
```

**whenUnsatisfiable オプション:**
- **DoNotSchedule**: constraint に違反する場合は scheduling を拒否
- **ScheduleAnyway**: constraint に違反していても scheduling する（best-effort）

</details>

### 5. data locality の観点で、data が存在する Node に Pod を配置するにはどうしますか？

A. ランダム scheduling
B. data-proximity placement のために Node label と nodeSelector を使用する
C. 常に cloud Node を選択する
D. Pod 名のアルファベット順

<details>
<summary>回答を表示</summary>

**回答: B. data-proximity placement のために Node label と nodeSelector を使用する**

**解説:**
data locality では、data が保存されている Node に label を付け、それらの label を使って Pod を配置します。

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

**Data Locality の利点:**
- network latency を最小化
- data transfer cost を削減
- processing performance を向上

</details>

### 6. 同じ application の Pod が同じ Node に配置されないように Pod Anti-Affinity を使う理由は何ですか？

A. cost savings
B. 高可用性と障害分離
C. network speed improvement
D. storage savings

<details>
<summary>回答を表示</summary>

**回答: B. 高可用性と障害分離**

**解説:**
Pod Anti-Affinity は、同じ application の Pod を異なる Node に分散し、単一 Node 障害が発生しても service availability を維持します。

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

**結果:**
```
Node 1: ha-webapp-pod-1
Node 2: ha-webapp-pod-2
Node 3: ha-webapp-pod-3
(Only 1 placed per node)
```

Node に障害が発生した場合、影響を受ける Pod は 1 つだけで、残りの 2 つは service の提供を継続します。

</details>
