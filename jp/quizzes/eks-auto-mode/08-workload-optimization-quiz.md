# EKS Auto Mode ワークロード最適化クイズ

> **関連ドキュメント**: [ワークロード最適化](../../eks-auto-mode/08-workload-optimization.md)

## 多肢選択問題

### 1. 大規模な e-commerce platform の frontend workloads に推奨される NodePool 設定はどれですか？

- A) Spot のみ、積極的な Consolidation
- B) On-Demand 優先、可用性重視の Disruption Budget
- C) GPU instances、高性能設定
- D) Memory-optimized instances のみ

<details>
<summary>回答を表示</summary>

**回答: B) On-Demand 優先、可用性重視の Disruption Budget**

**解説:**
Frontend workloads はユーザー向けであるため、可用性が最優先です。

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: frontend-tier
spec:
  template:
    metadata:
      labels:
        tier: frontend
    spec:
      requirements:
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["m"]
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["on-demand"]  # Availability first
      taints:
        - key: tier
          value: frontend
          effect: NoSchedule
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 10m
    budgets:
      - nodes: "10%"
      - nodes: "1"
        schedule: "0 9-23 * * *"  # Peak hours
        duration: 14h
```

</details>

### 2. Batch processing workloads に最も適した NodePool 設定はどれですか？

- A) On-Demand のみ、保守的な Consolidation
- B) Spot のみ、多様な instance families、迅速なクリーンアップ
- C) GPU instances のみを使用
- D) system NodePool に配置

<details>
<summary>回答を表示</summary>

**回答: B) Spot のみ、多様な instance families、迅速なクリーンアップ**

**解説:**
Batch jobs は中断に耐性があるため、Spot instances に適しています。

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: batch-tier
spec:
  template:
    metadata:
      labels:
        tier: batch
    spec:
      requirements:
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["c", "m", "r", "i", "d"]  # Diverse families
        - key: karpenter.k8s.aws/instance-generation
          operator: In
          values: ["5", "6", "7"]
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["spot"]  # Spot only
        - key: kubernetes.io/arch
          operator: In
          values: ["amd64", "arm64"]
      taints:
        - key: tier
          value: batch
          effect: NoSchedule
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30s  # Quick cleanup
```

</details>

### 3. GPU ML inference workloads に推奨される Consolidation 設定はどれですか？

- A) `consolidateAfter: 0s`
- B) `consolidateAfter: 15m`（GPU startup time を考慮）
- C) `consolidationPolicy: WhenEmptyOrUnderutilized`
- D) Consolidation を無効化

<details>
<summary>回答を表示</summary>

**回答: B) `consolidateAfter: 15m`（GPU startup time を考慮）**

**解説:**
GPU instances は起動に時間がかかるため、十分な consolidateAfter が必要です。

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: ml-inference
spec:
  template:
    spec:
      requirements:
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["g"]
        - key: node.kubernetes.io/instance-type
          operator: In
          values: ["g5.xlarge", "g5.2xlarge", "g5.4xlarge"]
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["on-demand"]
      taints:
        - key: nvidia.com/gpu
          value: "true"
          effect: NoSchedule
  limits:
    nvidia.com/gpu: 20
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 15m  # Consider GPU startup time
```

</details>

### 4. API server workloads の安定性とコストのバランスを取る戦略はどれですか？

- A) On-Demand のみ
- B) Spot のみ
- C) Spot/On-Demand 混在 + Graviton を含める
- D) Fargate のみ

<details>
<summary>回答を表示</summary>

**回答: C) Spot/On-Demand 混在 + Graviton を含める**

**解説:**
API servers には、コスト最適化を可能にしつつ適切な可用性が必要です。

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: api-tier
spec:
  template:
    metadata:
      labels:
        tier: api
    spec:
      requirements:
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["m", "c"]
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["on-demand", "spot"]  # Mixed
        - key: kubernetes.io/arch
          operator: In
          values: ["amd64", "arm64"]  # Include Graviton
      taints:
        - key: tier
          value: api
          effect: NoSchedule
  weight: 10
```

**想定コスト削減:** 約40%

</details>

### 5. Multi-architecture（amd64/arm64）support のために applications で確認すべきことは何ですか？

- A) 特別な確認は不要
- B) Container images が multi-arch をサポートしていることを確認する
- C) Kubernetes version のみを確認
- D) AWS region のみを確認

<details>
<summary>回答を表示</summary>

**回答: B) Container images が multi-arch をサポートしていることを確認する**

**解説:**
Graviton（arm64）instances を利用するには、container images がその architecture をサポートしている必要があります。

```bash
# Check image supported architectures
docker manifest inspect nginx:latest | grep architecture

# Multi-arch image build example
docker buildx build \
    --platform linux/amd64,linux/arm64 \
    -t myapp:latest \
    --push .
```

**チェックリスト:**
- Base image の multi-arch support を確認
- 両方の architectures 向けに native binaries をビルド
- CI/CD pipeline で multi-arch build を設定

</details>

### 6. Workload ごとに NodePools を分離する場合、Pods が正しい NodePool に schedule されるようにする方法はどれですか？

- A) Pod name による自動マッチング
- B) Taint/Toleration と NodeSelector または Affinity を使用
- C) Namespace による自動分離
- D) AWS tags のみによる分離

<details>
<summary>回答を表示</summary>

**回答: B) Taint/Toleration と NodeSelector または Affinity を使用**

**解説:**
NodePool に taints を設定し、Pods に tolerations と affinity を追加します。

```yaml
# Set taint on NodePool
spec:
  template:
    spec:
      taints:
        - key: tier
          value: batch
          effect: NoSchedule

---
# Set toleration and affinity on Pod
apiVersion: apps/v1
kind: Deployment
metadata:
  name: batch-job
spec:
  template:
    spec:
      tolerations:
        - key: tier
          value: batch
          effect: NoSchedule
      affinity:
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
              - matchExpressions:
                  - key: tier
                    operator: In
                    values: ["batch"]
```

</details>
