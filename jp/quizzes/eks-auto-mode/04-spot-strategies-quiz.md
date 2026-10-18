# EKS Auto Mode Spot 戦略クイズ

> **関連ドキュメント**: [Spot インスタンスの戦略](../../eks-auto-mode/04-spot-strategies.md)

## 選択式問題

### 1. 利用可能な Spot 容量の選択肢を広げる方法はどれですか?

- A) 1 つの AZ で単一のインスタンスタイプを使う
- B) 互換性のある複数のタイプ、サイズ、アーキテクチャ、AZ を許可する
- C) 追加アーキテクチャで互換性のないイメージを必須にする
- D) 常に最も安価なタイプだけを選ぶ

<details>
<summary>答えを表示</summary>

**答え: B) 互換性のある複数のタイプ、サイズ、アーキテクチャ、AZ を許可する**

**解説:**
Spot プールはインスタンスタイプと AZ の組み合わせごとに存在します。選択肢を多様化すると利用可能なプールが増えますが、中断が互いに独立するわけではなく、2 つのアーキテクチャを列挙しただけで実際の容量が倍になるわけでもありません。まず、イメージ、依存関係、性能特性との互換性を確認してください。

```yaml
requirements:
- key: eks.amazonaws.com/instance-category
  operator: In
  values:
  - m
  - c
  - r
  - i
  - d
- key: eks.amazonaws.com/instance-generation
  operator: Gt
  values:
  - '4'
- key: eks.amazonaws.com/instance-size
  operator: In
  values:
  - large
  - xlarge
  - 2xlarge
- key: kubernetes.io/arch
  operator: In
  values:
  - amd64
  - arm64
- key: karpenter.sh/capacity-type
  operator: In
  values:
  - spot
```

これは requirements の断片であり、完全な NodePool 定義ではありません。

</details>

### 2. この例で Spot 容量と On-Demand 容量を区別するラベルはどれですか?

- A) node.kubernetes.io/capacity-type
- B) karpenter.sh/capacity-type
- C) eks.amazonaws.com/instance-type
- D) karpenter.k8s.aws/spot-or-ondemand

<details>
<summary>答えを表示</summary>

**答え: B) karpenter.sh/capacity-type**

**解説:**
NodePool の requirements または Pod の選択条件で `karpenter.sh/capacity-type` を使います。preferred affinity は Spot を必須にせず、予備ノードを確保せず、購入オプションの固定比率も設定しません。

```yaml
affinity:
  nodeAffinity:
    preferredDuringSchedulingIgnoredDuringExecution:
    - weight: 100
      preference:
        matchExpressions:
        - key: karpenter.sh/capacity-type
          operator: In
          values:
          - spot
```

必須のベースラインを確保する場合は、互換性のある hard selector または required affinity を別のワークロードで使います。Downward API の `spec.nodeName` が示すのはノード名であり、Spot かどうかを示す値ではありません。

</details>

### 3. EC2 Spot の停止・終了に関する警告をどう解釈すべきですか?

- A) すべての Pod に 30 秒が保証される
- B) 通常は 2 分前に通知されるが、通知はベストエフォートである
- C) すべての Pod に 5 分が保証される
- D) preStop によって 10 分の延長を要求できる

<details>
<summary>答えを表示</summary>

**答え: B) 通常は 2 分前に通知されるが、通知はベストエフォートである**

**解説:**
EC2 は通常、停止または終了の中断通知を 2 分前に提供しますが、通知はベストエフォートであり、休止状態への移行では直ちに開始する別の動作になります。Kubernetes による検知、退避、アプリケーション処理にも時間がかかります。Pod の猶予期間や preStop hook で EC2 の期限を延長することはできません。また、90 秒の sleep はチェックポイント保存や正常終了の実装にはなりません。定期的に永続ストレージへチェックポイントを保存し、冪等な復旧処理を用意して、アプリケーションのシグナル処理をテストしてください。

</details>

### 4. 中断可能な容量に依存する前に、最も再設計が必要なパターンはどれですか?

- A) 検証済みの再試行処理を備えた冪等なバッチ処理
- B) フェイルオーバーをテスト済みの、レプリケーションされたステートレスサービス
- C) 復旧手段がなく、唯一の状態をローカルストレージに置く重要な単一インスタンスデータベース
- D) 遅延や再試行を許容できる開発用ジョブ

<details>
<summary>答えを表示</summary>

**答え: C) 復旧手段がなく、唯一の状態をローカルストレージに置く重要な単一インスタンスデータベース**

**解説:**
この単一インスタンス構成では、可用性が失われ、唯一の状態も失われるおそれがあります。On-Demand を使っても、ノードローカルストレージが永続化されるわけではなく、メンテナンスや障害のリスクがなくなるわけでもありません。データベース、キュー、長時間実行されるジョブは、ワークロード名だけを基準に一律に判断せず、それぞれのアーキテクチャに応じて評価してください。

</details>

### 5. Spot と On-Demand が混在する 1 つの NodePool で、Spot を優先させるにはどうしますか?

- A) `spotPriority: high` を設定する
- B) Spot と On-Demand の両方を許可し、Auto Mode の対象容量に対する優先順位を適用させる
- C) `capacityPriority: spot` を設定する
- D) weight を使って Spot ノードを正確に 80% 確保する

<details>
<summary>答えを表示</summary>

**答え: B) Spot と On-Demand の両方を許可し、Auto Mode の対象容量に対する優先順位を適用させる**

**解説:**
両方の容量タイプを許可します。配列の順序や weight では、この NodePool 内の比率は選べません。予約済み容量も許可され、かつ条件に合う場合は Spot より優先され、Spot は On-Demand より優先されます。ただし、実際に利用できる容量や制約条件にも左右されます。

2 つの NodePool を使う方法では、weight によってプロビジョニングの優先度を調整できます。

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: spot-first
spec:
  weight: 100
  template:
    spec:
      requirements:
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - spot
      - key: eks.amazonaws.com/instance-category
        operator: In
        values:
        - c
        - m
        - r
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
      taints:
      - key: spot-lab
        value: 'true'
        effect: NoSchedule
    metadata:
      labels:
        capacity-example: spot-lab
        capacity-strategy: spot-preferred
  limits:
    cpu: '100'
    memory: 400Gi
---
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: ondemand-fallback
spec:
  weight: 10
  template:
    spec:
      requirements:
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - on-demand
      - key: eks.amazonaws.com/instance-category
        operator: In
        values:
        - c
        - m
        - r
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
      taints:
      - key: spot-lab
        value: 'true'
        effect: NoSchedule
    metadata:
      labels:
        capacity-example: spot-lab
        capacity-strategy: spot-preferred
  limits:
    cpu: '100'
    memory: 400Gi
```

両方の NodePool には共通のラベルと実習用 taint があります。フォールバック先を必要とするワークロードは、その taint を許容し、両方の NodePool に一致する必要があります。Pod を Spot 専用の NodePool 名に固定すると、フォールバックできません。weight は、すでにスケジュールされた Pod を移動させず、フォールバック先の容量がすぐに確保されることも保証しません。

</details>

### 6. AWS が公表している EC2 Spot の割引率はどの程度ですか?

- A) 30～40% の削減が保証される
- B) 50～60% の削減が保証される
- C) On-Demand と比べて最大 90% だが、ワークロード全体の削減額は保証されない
- D) 95% 以上の削減が保証される

<details>
<summary>答えを表示</summary>

**答え: C) On-Demand と比べて最大 90% だが、ワークロード全体の削減額は保証されない**

**解説:**
実際の料金や有効な処理あたりのコストは、インスタンスタイプ、AZ、期間、復旧処理、その他の料金によって異なります。Auto Mode の管理料金は EC2 の料金に追加されます。以前の教材にあった次の表は、実測値が検証されていないものとして残しています。

| 以前の例示 | 未検証の数値 |
|---|---|
| Spot | 70～90% |
| Graviton/ARM | 約 20% |
| Spot + Graviton | 最大 90% |

比較の基準と測定方法は確認されていません。これらの割合を加算したり、保証された削減額として扱ったりしないでください。Advisor のデータは過去 1 か月分の集計であり、反映が遅れる場合があります。AZ ごとの価格履歴または実際の請求額を確認し、復旧にかかった時間を二重計上しないでください。

</details>
