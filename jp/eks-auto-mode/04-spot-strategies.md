# Spot Instance 活用戦略

> **対応バージョン**: EKS 1.29+, EKS Auto Mode GA
> **最終更新**: February 19, 2026

このガイドでは、混合キャパシティ設定、多様化、Interrupt 処理を含め、EKS Auto Mode で Spot instance を効果的に使用するための戦略を説明します。

---

## Spot と On-Demand の混合戦略

混合戦略は、安定性とコスト効率の両方を実現します。

```yaml
# spot-ondemand-mixed.yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: mixed-capacity
spec:
  template:
    spec:
      requirements:
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["m", "c", "r"]
        - key: karpenter.k8s.aws/instance-generation
          operator: Gt
          values: ["5"]
        # Allow both Spot and On-Demand
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["spot", "on-demand"]
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 1m
---
# Configure Spot preference in Pod
apiVersion: apps/v1
kind: Deployment
metadata:
  name: spot-friendly-app
spec:
  replicas: 10
  selector:
    matchLabels:
      app: spot-friendly
  template:
    metadata:
      labels:
        app: spot-friendly
    spec:
      # Prefer Spot instances
      affinity:
        nodeAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
            - weight: 100
              preference:
                matchExpressions:
                  - key: karpenter.sh/capacity-type
                    operator: In
                    values: ["spot"]
      # For critical workloads, require On-Demand
      # requiredDuringSchedulingIgnoredDuringExecution:
      #   nodeSelectorTerms:
      #     - matchExpressions:
      #         - key: karpenter.sh/capacity-type
      #           operator: In
      #           values: ["on-demand"]
      containers:
        - name: app
          image: my-app:latest
          resources:
            requests:
              cpu: 500m
              memory: 512Mi
```

### キャパシティタイプの選択ガイドライン

| ワークロードタイプ | 推奨キャパシティ | 理由 |
|---------------|---------------------|-----------|
| ステートレス Web サービス | Spot 推奨 | Interrupt に対応可能 |
| バッチ処理 | Spot のみ | コスト削減、リトライ可能 |
| データベース | On-Demand のみ | データ整合性 |
| CI/CD ランナー | Spot 推奨 | コスト削減、リトライ可能 |
| Machine learning inference | 混合 | コストと可用性のバランス |
| Machine learning training | チェックポイント付きの混合 | 長時間実行、チェックポイント可能 |

---

## Spot Instance の多様化

Interrupt リスクを分散するために、多様な Instance type を使用します。

```yaml
# diversified-spot.yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: diversified-spot
spec:
  template:
    spec:
      requirements:
        # Various instance families
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["m", "c", "r", "i", "d"]
        # Various generations
        - key: karpenter.k8s.aws/instance-generation
          operator: In
          values: ["5", "6", "7"]
        # Various sizes
        - key: karpenter.k8s.aws/instance-size
          operator: In
          values: ["large", "xlarge", "2xlarge"]
        # Various architectures
        - key: kubernetes.io/arch
          operator: In
          values: ["amd64", "arm64"]
        # Use only Spot
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["spot"]
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
  # Fast re-provisioning on Spot interrupt
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30s
```

### 多様化のベストプラクティス

| 戦略 | 利点 | 設定 |
|----------|---------|---------------|
| 複数の Instance family | 相関する Interrupt を削減 | `["m", "c", "r", "i", "d"]` |
| 複数の世代 | より大きなキャパシティプールへアクセス | `["5", "6", "7"]` |
| 複数のサイズ | プロビジョニングの柔軟性 | `["large", "xlarge", "2xlarge"]` |
| 複数のアーキテクチャ | キャパシティプールが 2 倍 | `["amd64", "arm64"]` |

---

## Spot Interrupt 処理

### Disruption Budget 設定

```yaml
# spot-disruption-budget.yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: spot-with-disruption-budget
spec:
  template:
    spec:
      requirements:
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["spot"]
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["m", "c", "r"]
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 1m
    # Limit concurrent node disruptions
    budgets:
      - nodes: "10%"    # Only 10% of total nodes simultaneously
      - nodes: "3"      # Or maximum 3 nodes
      # Minimize disruptions during business hours
      - nodes: "0"
        schedule: "0 9-18 * * mon-fri"  # Weekdays 9-18
        duration: 9h
```

### Spot を意識した Pod 設定

```yaml
# Configure Spot interrupt handling in Pod
apiVersion: apps/v1
kind: Deployment
metadata:
  name: spot-aware-app
spec:
  replicas: 5
  selector:
    matchLabels:
      app: spot-aware
  template:
    metadata:
      labels:
        app: spot-aware
    spec:
      # Allow time for graceful shutdown
      terminationGracePeriodSeconds: 120
      containers:
        - name: app
          image: my-app:latest
          lifecycle:
            preStop:
              exec:
                command: ["/bin/sh", "-c", "sleep 90"]
      # Spread across multiple AZs
      topologySpreadConstraints:
        - maxSkew: 1
          topologyKey: topology.kubernetes.io/zone
          whenUnsatisfiable: DoNotSchedule
          labelSelector:
            matchLabels:
              app: spot-aware
```

### Interrupt 処理チェックリスト

| 項目 | 説明 | 実装 |
|------|-------------|----------------|
| Graceful shutdown | SIGTERM を適切に処理 | `terminationGracePeriodSeconds` |
| PreStop hook | 終了を遅延 | `lifecycle.preStop` |
| Multi-AZ spread | AZ 全体の Interrupt に耐える | `topologySpreadConstraints` |
| 複数の Replica | 単一障害点をなくす | `replicas > 1` |
| State externalization | State をローカルに保存しない | 外部データベース/キャッシュを使用 |

---

## コスト削減例

```
+-----------------------------------------------------------------------------+
|                       Spot Instance Cost Savings Examples                    |
+-----------------------------------------------------------------------------+
|                                                                              |
|  Workload Type          On-Demand Cost   Spot Cost      Savings             |
|  ---------------------------------------------------------------------------  |
|  Batch Processing        $1,000/month    $300/month     70%                 |
|  Dev/Test Environment    $2,000/month    $500/month     75%                 |
|  CI/CD Pipeline          $500/month      $150/month     70%                 |
|  Non-critical API Server $3,000/month    $1,200/month   60%                 |
|                                                                              |
|  * Spot instance prices vary based on supply and demand                      |
|                                                                              |
+-----------------------------------------------------------------------------+
```

### Spot 削減額の計算

潜在的な Spot 削減額を見積もるには、次の手順を行います。

1. **Spot 対象ワークロードを特定**: ステートレス、耐障害性、柔軟性
2. **Spot 料金履歴を確認**: AWS Spot Instance Advisor を使用
3. **ベースライン On-Demand コストを計算**: 現在または予測される支出
4. **平均 Spot 割引を適用**: 通常 On-Demand から 60〜90% オフ
5. **Interrupt オーバーヘッドを考慮**: 再プロビジョニングのための追加コンピューティング

### Spot 削減額の式

```
Estimated Monthly Savings =
    (On-Demand Hours * On-Demand Price) -
    (Spot Hours * Spot Price) -
    (Interrupt Overhead * On-Demand Price)

Where:
- Interrupt Overhead = Estimated interrupts * Recovery time * Instance count
```

---

## Spot ベストプラクティスのまとめ

| プラクティス | 説明 |
|----------|-------------|
| Instance type を多様化 | 10 種類以上の Instance type を使用して Interrupt リスクを削減 |
| 複数の AZ を使用 | 可用性のために 3 つ以上の AZ に分散 |
| 適切な Grace period を設定 | Graceful shutdown のために 120 秒以上を許可 |
| Health check を実装 | 異常な Pod を迅速に検出して置き換え |
| Topology spread を使用 | すべての Replica が同じ Spot pool に配置されることを防止 |
| State を外部化 | 重要なデータを Spot node に保存しない |
| Disruption budget を設定 | 同時 Disruption を制限 |
| Spot メトリクスを監視 | Interrupt と削減額を追跡 |

---

< [前へ: Scaling Behavior](./03-scaling-behavior.md) | [目次](./README.md) | [次へ: Operations](./05-operations.md) >
