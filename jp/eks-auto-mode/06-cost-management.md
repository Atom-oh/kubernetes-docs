# コスト管理と最適化

> **対応バージョン**: EKS 1.29+, EKS Auto Mode GA
> **最終更新**: July 11, 2026

このガイドでは、EKS Auto Mode のコスト最適化戦略について説明します。コスト分析、Spot 節約額の測定、リソースの適正化、Savings Plans との統合を含みます。

### 2026 年 7 月更新: GPU 管理料金を最大 60% 削減

2026 年 7 月 1 日より、GPU および高速化インスタンスタイプに対する EKS Auto Mode の管理料金が削減されました。

- **G-series**: 管理料金を 35% 削減
- **P-series and AWS Trainium**: 管理料金を 60% 削減

この削減は、EKS Auto Mode が利用可能なすべての AWS Region のすべての Auto Mode クラスターに自動的に適用されます。対応は不要です。Auto Mode には、高速化ワークロード向けに構築された機能が含まれています。たとえば、ローカル NVMe ストレージを備えた GPU インスタンスでのイメージの並列プルと展開（大きなコンテナイメージやモデルイメージをより速く起動するため）、GPU ハードウェア障害を検出して異常なノードを自動的に置き換える、アクセラレータを認識したノード修復などです。更新後の料金表については、[Amazon EKS pricing](https://aws.amazon.com/eks/pricing/) を参照してください。([発表](https://aws.amazon.com/about-aws/whats-new/2026/07/amazon-eks-auto-mode-gpu-price))

---

## コスト最適化のベストプラクティス

```yaml
# cost-optimization-best-practices.yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: cost-optimized
spec:
  template:
    spec:
      requirements:
        # 1. Allow various instance families
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["m", "c", "r", "i", "d"]

        # 2. Include Graviton (ARM) instances (20% cheaper)
        - key: kubernetes.io/arch
          operator: In
          values: ["amd64", "arm64"]

        # 3. Prioritize Spot instances
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["spot", "on-demand"]

      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default

  # 4. Aggressive Consolidation
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 1m
---
# Pod settings for cost optimization
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cost-efficient-app
spec:
  replicas: 5
  template:
    spec:
      # Prefer Spot
      affinity:
        nodeAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
            - weight: 100
              preference:
                matchExpressions:
                  - key: karpenter.sh/capacity-type
                    operator: In
                    values: ["spot"]

      # Appropriate resource requests (prevent overprovisioning)
      containers:
        - name: app
          resources:
            requests:
              cpu: 250m      # Based on actual usage
              memory: 256Mi
            limits:
              cpu: 500m
              memory: 512Mi
```

---

## コスト分析ダッシュボード

### CloudWatch コストメトリクス

Auto Mode のコストを追跡するために CloudWatch ダッシュボードを設定します。

```json
{
  "widgets": [
    {
      "type": "metric",
      "properties": {
        "title": "Node Hours by Capacity Type",
        "metrics": [
          ["Karpenter", "karpenter_nodes_total", "capacity_type", "spot"],
          ["Karpenter", "karpenter_nodes_total", "capacity_type", "on-demand"]
        ],
        "period": 3600,
        "stat": "Average"
      }
    },
    {
      "type": "metric",
      "properties": {
        "title": "Node Provisioning Rate",
        "metrics": [
          ["Karpenter", "karpenter_nodeclaims_created"],
          ["Karpenter", "karpenter_nodeclaims_terminated"]
        ],
        "period": 3600,
        "stat": "Sum"
      }
    }
  ]
}
```

### Kubecost 統合

詳細なコスト配分には、Kubecost を統合します。

```bash
# Install Kubecost
helm repo add kubecost https://kubecost.github.io/cost-analyzer/
helm install kubecost kubecost/cost-analyzer \
  --namespace kubecost \
  --create-namespace \
  --set kubecostToken="<your-token>"
```

Auto Mode における主要な Kubecost メトリクス:

| メトリクス | 説明 | ユースケース |
|--------|-------------|----------|
| クラスターコスト | 合計コンピュート支出 | 予算追跡 |
| Namespace コスト | Namespace ごとのコスト | チャージバック |
| Pod コスト | ワークロードごとのコスト | 最適化対象 |
| アイドルコスト | 未使用リソース | 適正化の機会 |
| Spot 節約額 | Spot と On-Demand の差分 | Spot 戦略の検証 |

---

## Spot Instance の節約額を測定する

### 実際の Spot 節約額を計算する

```bash
# Get current node distribution
kubectl get nodes -L karpenter.sh/capacity-type -L node.kubernetes.io/instance-type | \
  awk 'NR>1 {print $6, $7}' | sort | uniq -c
```

### Spot 節約額分析スクリプト

```bash
#!/bin/bash
# spot-savings-analysis.sh

# Get Spot and On-Demand node counts
SPOT_NODES=$(kubectl get nodes -l karpenter.sh/capacity-type=spot --no-headers | wc -l)
OD_NODES=$(kubectl get nodes -l karpenter.sh/capacity-type=on-demand --no-headers | wc -l)

echo "Current Node Distribution:"
echo "  Spot nodes: $SPOT_NODES"
echo "  On-Demand nodes: $OD_NODES"
echo "  Spot percentage: $(echo "scale=2; $SPOT_NODES * 100 / ($SPOT_NODES + $OD_NODES)" | bc)%"

# Estimate savings (assuming average 70% Spot discount)
echo ""
echo "Estimated Monthly Savings:"
echo "  If all were On-Demand: \$X,XXX"
echo "  With current Spot mix: \$X,XXX"
echo "  Monthly savings: \$X,XXX (XX%)"
```

### AWS Cost Explorer クエリ

Cost Explorer を使用して Auto Mode のコストを分析します。

1. **タグでフィルター**: `eks:cluster-name` = your-cluster
2. **グループ化**: `Instance Type` または `Purchase Option`
3. **期間**: 過去 30 日間
4. **比較**: Spot と On-Demand の支出

---

## リソース適正化分析

### VPA の推奨事項

適正化の推奨事項を得るために Vertical Pod Autoscaler をインストールします。

```bash
# Install VPA
kubectl apply -f https://github.com/kubernetes/autoscaler/releases/latest/download/vpa-v1-crd-gen.yaml
kubectl apply -f https://github.com/kubernetes/autoscaler/releases/latest/download/vpa-rbac.yaml
kubectl apply -f https://github.com/kubernetes/autoscaler/releases/latest/download/recommender-deployment.yaml
```

推奨モードで VPA を設定します。

```yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: my-app-vpa
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: my-app
  updatePolicy:
    updateMode: "Off"  # Recommendation only
  resourcePolicy:
    containerPolicies:
      - containerName: '*'
        minAllowed:
          cpu: 100m
          memory: 128Mi
        maxAllowed:
          cpu: 4
          memory: 8Gi
```

### 使用パターンの分析

```bash
# Get VPA recommendations
kubectl get vpa my-app-vpa -o jsonpath='{.status.recommendation.containerRecommendations[0]}' | jq

# Compare with current requests
kubectl get deployment my-app -o jsonpath='{.spec.template.spec.containers[0].resources}'
```

### 適正化の判断マトリックス

| 現在値と推奨値の比較 | アクション | 期待される節約 |
|------------------------|--------|------------------|
| Request > 使用量の 2 倍 | Request を削減 | 20-50% |
| Request が 2 倍以内 | 最適 | - |
| Request < 使用量 | Request を増加 | OOM を回避 |
| Limit >> Request | Limit を削減 | より良い bin-packing |

---

## Savings Plans と Reserved Instances の戦略

### Savings Plans と Auto Mode の相互作用

EKS Auto Mode と Savings Plans:

| シナリオ | Savings Plans の適用 | 推奨事項 |
|----------|---------------------|----------------|
| On-Demand ノード | はい | Compute Savings Plans を購入 |
| Spot ノード | いいえ（すでに割引済み） | カバレッジに含めない |
| Graviton インスタンス | はい（別料金） | ARM Savings Plans を検討 |
| 混在ワークロード | 一部 | On-Demand ベースラインを計算 |

### Savings Plans のサイズ設定

```
Recommended Savings Plans Coverage =
    Baseline On-Demand Hours *
    (1 - Expected Spot Percentage) *
    Average Instance Cost

Where:
- Baseline = Minimum sustained usage
- Expected Spot = Target Spot percentage (e.g., 60%)
- Don't over-commit (leave room for Spot)
```

### Savings Plans のベストプラクティス

| プラクティス | 理由 |
|----------|-----------|
| On-Demand ベースラインの 60-70% をカバー | Spot 最適化の余地を残す |
| Compute Savings Plans を使用 | インスタンスタイプ全体での柔軟性 |
| 四半期ごとにレビュー | ワークロードの変化に合わせて調整 |
| GPU インスタンスを除外 | GPU 固有のプランを分離 |

### Reserved Instances と Savings Plans の比較

| 要素 | Reserved Instances | Savings Plans |
|--------|-------------------|---------------|
| 柔軟性 | インスタンス固有 | 任意のインスタンス |
| Auto Mode との適合性 | 低い（インスタンスが変動） | 良い |
| コミットメント | 1 年または 3 年 | 1 年または 3 年 |
| 推奨事項 | 推奨しない | 推奨 |

---

## コスト最適化チェックリスト

### すぐに得られる効果

| アクション | 推定節約額 | 工数 |
|--------|-------------------|--------|
| Spot インスタンスを有効化 | Spot ノードで 60-90% | 低 |
| ARM/Graviton サポートを追加 | ARM インスタンスで 20% | 低 |
| Request を適正化 | 10-30% | 中 |
| 統合を有効化 | 10-20% | 低 |

### 中期的な最適化

| アクション | 推定節約額 | 工数 |
|--------|-------------------|--------|
| VPA を実装 | 15-30% | 中 |
| Savings Plans を購入 | On-Demand で 20-40% | 低 |
| Multi-AZ 最適化 | 5-10% | 中 |
| ワークロードスケジューリング | 10-20% | 高 |

### コスト監視アラート

コスト異常のアラートを設定します。

```yaml
# CloudWatch Alarm for unexpected node growth
AWSTemplateFormatVersion: '2010-09-09'
Resources:
  NodeCountAlarm:
    Type: AWS::CloudWatch::Alarm
    Properties:
      AlarmName: EKS-Auto-Mode-Node-Count-High
      MetricName: karpenter_nodes_total
      Namespace: Karpenter
      Statistic: Average
      Period: 300
      EvaluationPeriods: 3
      Threshold: 100  # Adjust based on expected max
      ComparisonOperator: GreaterThanThreshold
      AlarmActions:
        - !Ref AlertSNSTopic
```

---

## コスト配分

### コスト配分のためのタグ付け戦略

```yaml
# NodeClass with cost allocation tags
apiVersion: eks.amazonaws.com/v1
kind: NodeClass
metadata:
  name: tagged-nodeclass
spec:
  tags:
    Environment: production
    Team: platform
    CostCenter: "12345"
    Application: my-app
    ManagedBy: eks-auto-mode
```

### Namespace レベルのコスト追跡

```yaml
# Namespace with cost labels
apiVersion: v1
kind: Namespace
metadata:
  name: team-a
  labels:
    cost-center: "team-a"
    environment: production
```

---

< [前へ: Operations](./05-operations.md) | [目次](./README.md) | [次へ: Node Lifecycle](./07-node-lifecycle.md) >
