# EKS Auto Mode コスト管理クイズ

> **関連ドキュメント**: [コスト管理](../../eks-auto-mode/06-cost-management.md)

## 選択問題

### 1. コスト最適化のために Graviton (ARM) インスタンスを含めることで、約何パーセントのコスト削減を達成できますか？

- A) 5%
- B) 10%
- C) 20%
- D) 50%

<details>
<summary>答えを表示</summary>

**回答: C) 20%**

**解説:**
AWS Graviton プロセッサーベースのインスタンス (arm64) は、優れたパフォーマンスを提供しながら、同等の x86 インスタンスよりも約 20% 安価です。

```yaml
spec:
  template:
    spec:
      requirements:
        # Include Graviton (ARM) instances
        - key: kubernetes.io/arch
          operator: In
          values: ["amd64", "arm64"]
```

**コスト最適化戦略:**
- Graviton (ARM) インスタンスの使用: 約 20% の削減
- Spot インスタンスの使用: 最大 70～90% の削減
- 積極的な Consolidation: 使用率の低いノードを統合
- 適切なリソース requests: 過剰プロビジョニングを防止

</details>

### 2. NodePool の `limits` 設定で CPU limit が 500 に設定されている場合、何を意味しますか？

- A) ノードごとの最大 CPU は 500 コア
- B) NodePool は合計で最大 500 vCPU までプロビジョニングできる
- C) Pod ごとの最大 CPU は 500m
- D) クラスター全体の CPU limit

<details>
<summary>答えを表示</summary>

**回答: B) NodePool は合計で最大 500 vCPU までプロビジョニングできる**

**解説:**
NodePool の `limits` は、NodePool がプロビジョニングできるリソースの合計量を制限します。

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: compute-optimized
spec:
  limits:
    cpu: 500      # Maximum 500 vCPU
    memory: 1Ti   # Maximum 1TB memory
  template:
    spec:
      requirements:
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["c"]
```

これにより、コスト超過を防ぎ、予算を管理しやすくなります。

</details>

### 3. コストを最適化するために、使用率の低いノードを自動的にクリーンアップする Consolidation ポリシーはどれですか？

- A) `consolidationPolicy: WhenEmpty`
- B) `consolidationPolicy: WhenEmptyOrUnderutilized`
- C) `consolidationPolicy: Always`
- D) `consolidationPolicy: Aggressive`

<details>
<summary>答えを表示</summary>

**回答: B) `consolidationPolicy: WhenEmptyOrUnderutilized`**

**解説:**
`WhenEmptyOrUnderutilized` ポリシーは、空のノードと使用率の低いノードの両方を統合対象にします。

```yaml
disruption:
  consolidationPolicy: WhenEmptyOrUnderutilized
  consolidateAfter: 5m
```

**ポリシー比較:**
- `WhenEmpty`: 空のノードのみを削除（保守的、安定性優先）
- `WhenEmptyOrUnderutilized`: 積極的なコスト最適化

コスト削減効果: 使用率の低いノードを統合して、ノード総数とインフラストラクチャコストを削減します

</details>

### 4. Savings Plans を EKS Auto Mode で使用する場合の推奨アプローチは何ですか？

- A) インスタンスファミリーの柔軟性のために Compute Savings Plans を使用する
- B) 特定のインスタンスタイプのために EC2 Instance Savings Plans を使用する
- C) Reserved Instances のみを使用する
- D) Savings Plans を使用しない

<details>
<summary>答えを表示</summary>

**回答: A) インスタンスファミリーの柔軟性のために Compute Savings Plans を使用する**

**解説:**
Auto Mode はワークロードに応じてさまざまなインスタンスタイプを使用するため、Compute Savings Plans が最も適しています。

**Savings Plans 比較:**
| 種類 | 柔軟性 | 割引 |
|------|-------------|----------|
| Compute Savings Plans | インスタンスファミリー、サイズ、リージョン、OS が柔軟 | 最大 66% |
| EC2 Instance Savings Plans | 特定のインスタンスファミリーに固定 | 最大 72% |

```
Recommended Strategy:
1. Analyze baseline workload volume (3-month baseline)
2. Cover 70% of minimum usage with Compute Savings Plans
3. Run remainder flexibly with Spot/On-Demand
```

</details>

### 5. Kubecost を使用したコスト分析で、Pod レベルのコスト配分に必要なものは何ですか？

- A) 設定なしで自動的にサポートされる
- B) Pod に cost-center ラベルを追加する
- C) Kubecost agent とクラスター統合をインストールする
- D) AWS Cost Explorer で十分

<details>
<summary>答えを表示</summary>

**回答: C) Kubecost agent とクラスター統合をインストールする**

**解説:**
Kubecost は、詳細なコスト分析を提供する Kubernetes ネイティブなコスト監視ツールです。

```bash
# Kubecost installation (Helm)
helm repo add kubecost https://kubecost.github.io/cost-analyzer/
helm install kubecost kubecost/cost-analyzer \
    --namespace kubecost \
    --create-namespace
```

Kubecost の機能:
- namespace/workload 別のコスト分析
- リソース効率に関する推奨事項
- 予算アラート設定
- 実際のコスト精度のための AWS 統合

</details>

### 6. リソース requests を設定する際に、過剰プロビジョニングを防ぐためのベストプラクティスは何ですか？

- A) limits と requests を常に同じ値に設定する
- B) 実際の使用状況に基づく VPA の推奨事項を参照する
- C) requests をできるだけ高く設定する
- D) requests 設定を省略する

<details>
<summary>答えを表示</summary>

**回答: B) 実際の使用状況に基づく VPA の推奨事項を参照する**

**解説:**
Vertical Pod Autoscaler (VPA) を使用して実際のリソース使用状況を分析し、適切な request 値を設定します。

```yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: my-app-vpa
spec:
  targetRef:
    apiVersion: "apps/v1"
    kind: Deployment
    name: my-app
  updatePolicy:
    updateMode: "Off"  # Only provide recommendations, no auto-apply
```

推奨事項を確認します:
```bash
kubectl describe vpa my-app-vpa
```

これにより、次が可能になります:
- 過剰プロビジョニングを防止（コスト削減）
- 過少プロビジョニングを防止（パフォーマンス保証）

</details>

### 7. マルチティアワークロードに対するコスト効率のよい NodePool 分離戦略は何ですか？

- A) すべてのワークロードを単一の NodePool に配置する
- B) ティア別（frontend/API/batch/ML）に NodePool を分離する
- C) インスタンスサイズ別に NodePool を分離する
- D) アベイラビリティーゾーン別に NodePool を分離する

<details>
<summary>答えを表示</summary>

**回答: B) ティア別（frontend/API/batch/ML）に NodePool を分離する**

**解説:**
ワークロード特性に応じて NodePool を分離することで、最適なコスト/パフォーマンスバランスを実現できます。

| ティア | 戦略 | 期待される削減 |
|------|----------|-----------------|
| Frontend | On-Demand + Graviton | 約 20% |
| API | Spot 混合 + Graviton | 約 40% |
| Batch | Spot のみ + 分散 | 約 70% |
| ML | 適切なインスタンスサイズの選択 | 約 30% |

```yaml
# Batch tier example - Maximum cost savings
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: batch-tier
spec:
  template:
    spec:
      requirements:
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["spot"]  # Spot only
        - key: kubernetes.io/arch
          operator: In
          values: ["amd64", "arm64"]  # Include Graviton
```

</details>

### 8. AWS Cost Explorer で EKS Auto Mode のコストをタグ別に分類するには何が必要ですか？

- A) すべてのタグが自動的に適用される
- B) NodeClass で tags フィールドを設定する必要がある
- C) AWS Organizations で設定する
- D) タグベースの分類はできない

<details>
<summary>答えを表示</summary>

**回答: B) NodeClass で tags フィールドを設定する必要がある**

**解説:**
NodeClass の tags フィールドを通じて、プロビジョニングされたノードに cost allocation tags を適用します。

```yaml
apiVersion: eks.amazonaws.com/v1
kind: NodeClass
metadata:
  name: production-nodeclass
spec:
  tags:
    Environment: production
    Team: platform
    CostCenter: engineering-001
    Project: kubernetes-platform
```

AWS Cost Explorer のセットアップ:
1. Billing Console で Cost Allocation Tags を有効化する
2. 目的のタグキーを選択する
3. 24 時間後に Cost Explorer で利用可能になる

</details>
