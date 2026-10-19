# EKS Auto Mode のコスト管理クイズ

> **関連ドキュメント**: [コスト管理](../../eks-auto-mode/06-cost-management.md)
> **最終更新**: 2026年9月12日

## 選択問題

### 1. 以前示されていた「Graviton で 20% 節約」という数値は、ARM ノードを許可する際にどのように扱うべきですか？

- A) AWS が一律に保証する数値
- B) 請求額全体に適用される割引
- C) 検証されていない例として扱い、互換性のあるワークロードと実際の料金を比較する
- D) すべてのイメージが ARM 上で動くことの証明

<details>
<summary>解答を表示</summary>

**解答: C) 検証されていない例として扱い、互換性のあるワークロードと実際の料金を比較する**

**解説:**
以前の ARM で約 20%、Spot で 70～90% という数値は計画上の例であり、このワークロードで検証された比較結果ではありません。マルチアーキテクチャ対応イメージ、依存関係、有用な処理単位あたりの性能、現在のリージョン別料金、Auto Mode などの料金を確認してください。`amd64` と `arm64` の両方を許可しても、アプリケーションの互換性が検証されるわけではなく、どちらかのアーキテクチャが必ず選択される保証もありません。

</details>

### 2. 動的な NodePool の `limits.cpu: 500` は何を制限しますか？

- A) 各ノードの CPU を 500 コアまでに制限する
- B) そのプールがプロビジョニングする CPU リソースの合計
- C) 各 Pod の CPU を 500m までに制限する
- D) AWS アカウント全体の支出

<details>
<summary>解答を表示</summary>

**解答: B) そのプールがプロビジョニングする CPU リソースの合計**

**解説:**
これはプール単位のリソース上限です。プロビジョニングが急速に行われ、状態の反映に遅延がある場合は、一時的に上限を超えることがあります。`1Ti` は 1 TiB（1024 GiB）を意味し、10 進数の 1 TB ではありません。リソース上限は増加を抑える助けになりますが、インスタンスの料金を算出したり、他のサービスを含めたり、金額ベースの予算を強制したりするものではありません。
```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: compute-optimized
spec:
  template:
    spec:
      requirements:
      - key: eks.amazonaws.com/instance-category
        operator: In
        values:
        - m
        - c
        - r
        - i
        - d
      - key: kubernetes.io/arch
        operator: In
        values:
        - amd64
        - arm64
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - spot
        - on-demand
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
      taints:
      - key: cost-lab
        value: 'true'
        effect: NoSchedule
    metadata:
      labels:
        cost-lab: 'true'
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 1m
    budgets:
    - nodes: 10%
  limits:
    cpu: '500'
    memory: 1Ti
```


</details>

### 3. 再スケジュールの可否とコスト上の制約が許す場合、空のノードと使用率の低いノードの統合を認めるポリシーはどれですか？

- A) `WhenEmpty`
- B) `WhenEmptyOrUnderutilized`
- C) `Always`
- D) `Aggressive`

<details>
<summary>解答を表示</summary>

**解答: B) `WhenEmptyOrUnderutilized`**

**解説:**
このポリシーは、リソースリクエストに基づくスケジューリングの可否とコストを評価します。CPU 使用率が一定値を下回ったノードをすべて削除するものではありません。`consolidateAfter` は処理を開始するまでの待ち時間です。PDB、予算、配置制約によって統合が妨げられることがあります。`WhenEmpty` の対象はより限定的です。どちらのポリシーも、節約を保証したり、他のすべての中断手段を無効にしたりするものではありません。

</details>

### 4. 対象となる EC2 の使用量について、インスタンスファミリーやリージョンが変わる可能性がある場合、請求上の柔軟性を高めるのはどれですか？

- A) Compute Savings Plans
- B) 1 つのファミリーとリージョンに固定される EC2 Instance Savings Plan
- C) サイズを 1 種類に固定する Standard RI のみ
- D) すべての利用コミットメント割引を除外する

<details>
<summary>解答を表示</summary>

**解答: A) Compute Savings Plans**

**解説:**
Compute Savings Plans は、ファミリー、サイズ、リージョン、OS、テナンシーに柔軟性があります。EC2 Instance Savings Plans はファミリーとリージョンにコミットしますが、サイズ、OS、テナンシーには柔軟性があります。広告される最大割引率はそれぞれ最大 66%、72% であり、期待できる実際の割引率ではありません。既存のコミットメントと今後の変更を考慮し、対象となる未カバーの継続的な使用量に対して、1 時間あたり USD のコミット額を合わせてください。以前の「3 か月間の使用量を基準に 70% をカバーする」戦略は、検証されていない計画例です。Spot と別途請求される Auto Mode の料金は EC2 Savings Plans の割引対象ではありません。ARM 専用プランや、GPU を一律に除外する規則もありません。

</details>

### 5. Kubecost で Pod 単位のコスト配分を適切に行うには何が必要ですか？

- A) 設定もデータソースも不要
- B) Pod にコストセンターラベルを付けるだけ
- C) エージェント/クラスター連携を構成し、適切なコストデータを用意する
- D) Kubernetes の配分データがなくても Cost Explorer だけでよい

<details>
<summary>解答を表示</summary>

**解答: C) エージェント/クラスター連携を構成し、適切なコストデータを用意する**

**解説:**
レビュー対象の Kubecost 3.2.4 チャートは、新しいリポジトリの `kubecost/kubecost` です。バージョン 3 の FinOps エージェント/ClickHouse アーキテクチャは、旧 cost-analyzer デプロイメントとは異なります。ライセンス、プライベートアクセス、ストレージ/保持期間、ワークロード IAM、請求データとの照合を構成してください。インストール前にレビュー済みの values をレンダリングします。ラベルを付けるだけでは実際のコストデータは生成されません。
```bash
: "${KUBECOST_VALUES:?Set the reviewed Kubecost 3.2.4 values file}"
test -f "$KUBECOST_VALUES"
helm repo add kubecost https://kubecost.github.io/kubecost/
helm repo update kubecost
helm show chart kubecost/kubecost --version 3.2.4
helm template cost-review kubecost/kubecost --version 3.2.4 \
  --namespace kubecost --values "$KUBECOST_VALUES" \
  > "$WORK_DIR/kubecost-rendered.yaml"
```


</details>

### 6. リソースリクエストを変更する際、どのような根拠を使うべきですか？

- A) 常に requests と limits を同じ値にする
- B) VPA の推奨値と、代表的なワークロード/SLO の根拠
- C) すべての requests を最大化する
- D) requests を削除する

<details>
<summary>解答を表示</summary>

**解答: B) VPA の推奨値と、代表的なワークロード/SLO の根拠**

**解説:**
`Off` モードでは推奨値は適用されません。また、VPA のコンポーネントとメトリクスが正常に動作している必要があります。すべてのコンテナ、推奨値の信頼度と履歴、起動時のピーク、メモリ上限、CPU スロットリングを確認してください。推奨値が性能を保証したり、すべての OOM を防いだり、コスト削減を証明したりすることはありません。数量を比較する際に Kubernetes の単位サフィックスを取り除かないでください。
```yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: cost-app-vpa
  namespace: cost-lab
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: cost-efficient-app
  updatePolicy:
    updateMode: 'Off'
  resourcePolicy:
    containerPolicies:
    - containerName: '*'
      minAllowed:
        cpu: 100m
        memory: 128Mi
      maxAllowed:
        cpu: '4'
        memory: 8Gi
```


</details>

### 7. 中断耐性やアーキテクチャの要件が実際に異なるティアでは、どの設計でその違いを表せますか？

- A) すべてのティアに同一の配置を要求する
- B) ティアに適したプールと、対応するワークロード制約を使う
- C) インスタンスサイズごとにプールを作る
- D) 各 AZ が個別の請求割引対象だと仮定する

<details>
<summary>解答を表示</summary>

**解答: B) ティアに適したプールと、対応するワークロード制約を使う**

**解説:**
プールを分けることで実際の制約を表せますが、細分化しすぎるとアイドルコストが増えることがあります。Spot のみを使うバッチプールには On-Demand へのフォールバックがありません。中断に耐えられ、復旧手段のあるジョブだけに使用してください。プール名を付けるだけではワークロードの振り分けは行われません。ガイドにあるように、selector と toleration を設定します。

| ティア | 以前の戦略 | 元の未検証の節約率 |
|------|----------------|----------------------------|
| フロントエンド | On-Demand + Graviton | 約 20% |
| API | Spot 混在 + Graviton | 約 40% |
| バッチ | Spot + インスタンスの多様化 | 約 70% |
| ML | インスタンスサイズの選定 | 約 30% |

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: batch-tier
spec:
  template:
    spec:
      requirements:
      - key: eks.amazonaws.com/instance-category
        operator: In
        values:
        - m
        - c
        - r
        - i
        - d
      - key: kubernetes.io/arch
        operator: In
        values:
        - amd64
        - arm64
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - spot
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
      taints:
      - key: cost-lab
        value: 'true'
        effect: NoSchedule
    metadata:
      labels:
        cost-lab: 'true'
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 1m
    budgets:
    - nodes: 10%
  limits:
    cpu: '100'
    memory: 400Gi
```


</details>

### 8. AWS のコスト配分にカスタム NodeClass タグを使うには何が必要ですか？

- A) Kubernetes のすべてのラベルが自動的に伝播する
- B) 有効な NodeClass とタグ付け権限、実際のリソースタグ、Billing での有効化
- C) AWS Organization を作成するだけ
- D) タグによる配分はできない

<details>
<summary>解答を表示</summary>

**解答: B) 有効な NodeClass とタグ付け権限、実際のリソースタグ、Billing での有効化**

**解説:**
関連ガイドには、ID とネットワークのセレクターを含む NodeClass 全体の例があります。ノードアクセスエントリとタグ付け権限を確認し、対象のプールからそのクラスを参照して、実際にタグが付いていることを確かめたうえで Billing でタグキーを有効化してください。ユーザー定義のキーが表示されるまで最大 24 時間、さらに有効化まで最大 24 時間かかる場合があります。レポートへの反映には別途遅延があります。AWS が EC2 用に生成するクラスターキーは `aws:eks:cluster-name` です。このタグに Control Plane の料金は含まれません。namespace ラベルだけではタグは伝播せず、AWS の全コストを配分できるわけでもありません。

</details>

## 参考資料

- [EKS の料金](https://aws.amazon.com/eks/pricing/)
- [Savings Plans の種類](https://docs.aws.amazon.com/savingsplans/latest/userguide/plan-types.html)
- [EKS の請求タグ](https://docs.aws.amazon.com/eks/latest/userguide/eks-using-tags.html)
