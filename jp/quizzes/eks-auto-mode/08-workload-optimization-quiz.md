# EKS Auto Mode ワークロード最適化クイズ

> **関連ドキュメント**: [ワークロード最適化](../../eks-auto-mode/08-workload-optimization.md)
> **最終更新日**: 2026年9月12日

## 選択問題

### 1. 可用性が重要なフロントエンドで、妥当な初期構成はどれですか？

- A) 常に Spot のみを適切な選択肢とみなす
- B) On-Demand を使い、アプリケーションの可用性と中断制御を整える
- C) 常に GPU を必須にする
- D) メモリ最適化ノードだけを使う

<details>
<summary>解答を表示</summary>

**解答: B) On-Demand を使い、アプリケーションの可用性と中断制御を整える**

**解説:**
On-Demand は Spot の回収イベントを避けられますが、可用性を保証するものではありません。レプリカ、トポロジー、readiness、PDB、復旧手順をテストする必要があります。以下の代替 disruption budget は、UTC 00:00 から14時間の時間帯を毎日1回開始します（ソウル時間の09:00～23:00）。旧形式の時間単位の `9-23` パターンは使いません。この形式では時間帯が繰り返し延長されていました。有効な budget が複数ある場合は最小値が適用され、あらゆる強制的な中断を制御できるわけではありません。
```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: web-tier
spec:
  template:
    spec:
      requirements:
      - key: eks.amazonaws.com/instance-category
        operator: In
        values:
        - m
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - on-demand
      - key: kubernetes.io/arch
        operator: In
        values:
        - amd64
        - arm64
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
      expireAfter: 168h
      terminationGracePeriod: 24h
      taints:
      - key: workload-lab
        value: web-tier
        effect: NoSchedule
    metadata:
      labels:
        workload-lab: web-tier
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 5m
    budgets:
    - nodes: 10%
    - nodes: '1'
      schedule: 0 0 * * *
      duration: 14h
  limits:
    cpu: '32'
    memory: 128Gi
```


</details>

### 2. 中断への耐性と永続的な復旧手段を実証済みのバッチワークロードに適した NodePool はどれですか？

- A) On-Demand 以外は選べない
- B) 対応するインスタンスタイプを分散させ、空ノードをクリーンアップする Spot
- C) GPU のみ
- D) デフォルトでシステム用プールを使う

<details>
<summary>解答を表示</summary>

**解答: B) 対応するインスタンスタイプを分散させ、空ノードをクリーンアップする Spot**

**解説:**
すべてのバッチジョブが中断に耐えられるわけではありません。Spot のみでは On-Demand にフォールバックできません。コンテナの再起動や `SPOT_AWARE=true` はチェックポイント／再開の仕組みではありません。冪等な出力と永続化された進捗を使ってください。`WhenEmpty` と30秒の待ち時間を設定しても、実行中のジョブが30秒後に終了するわけではありません。関連ガイドの Indexed smoke Job は、範囲を限定した動作確認用であり、本番データ処理用ではありません。
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
        - c
        - m
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - spot
      - key: kubernetes.io/arch
        operator: In
        values:
        - amd64
        - arm64
      - key: eks.amazonaws.com/instance-generation
        operator: Gt
        values:
        - '4'
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
      expireAfter: 168h
      terminationGracePeriod: 24h
      taints:
      - key: workload-lab
        value: batch-tier
        effect: NoSchedule
    metadata:
      labels:
        workload-lab: batch-tier
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30s
    budgets:
    - nodes: 10%
  limits:
    cpu: '16'
    memory: 64Gi
```


</details>

### 3. 推論用プールの `consolidateAfter` を15分にした場合、どのように解釈すべきですか？

- A) GPU の起動期限が保証される
- B) 統合の待ち時間とノードの頻繁な入れ替わりを調整するための例示的な値である
- C) スケジューラーが Pod を配置できるようになるまでの遅延である
- D) ノードの有効期限切れを防ぐ保証である

<details>
<summary>解答を表示</summary>

**解答: B) 統合の待ち時間とノードの頻繁な入れ替わりを調整するための例示的な値である**

**解説:**
この値によって GPU が Ready になるわけでも、ウォーム状態のキャパシティが保証されるわけでもありません。`WhenEmpty` は統合の対象を限定しますが、ドリフト、有効期限切れ、中断は別の事象です。モデルのウォームアップ、必要なキャパシティ、コストを実測値に合わせてください。関連ガイドの推論用テンプレートでは、レビュー済みのイメージ、ランタイム、プローブが用意されるまでレプリカ数をゼロのままにします。4 CPU／16Gi の Pod は、システム予約分を考慮すると g5.xlarge にも収まりません。
```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: gpu-tier
spec:
  template:
    spec:
      requirements:
      - key: eks.amazonaws.com/instance-category
        operator: In
        values:
        - g
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - on-demand
      - key: kubernetes.io/arch
        operator: In
        values:
        - amd64
      - key: node.kubernetes.io/instance-type
        operator: In
        values:
        - g5.2xlarge
        - g5.4xlarge
      - key: eks.amazonaws.com/instance-gpu-manufacturer
        operator: In
        values:
        - nvidia
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: gpu-nodeclass
      expireAfter: 168h
      terminationGracePeriod: 24h
      taints:
      - key: workload-lab
        value: gpu-tier
        effect: NoSchedule
      - key: nvidia.com/gpu
        value: 'true'
        effect: NoSchedule
    metadata:
      labels:
        workload-lab: gpu-tier
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 15m
    budgets:
    - nodes: 10%
  limits:
    cpu: '64'
    memory: 256Gi
    nvidia.com/gpu: '4'
```


</details>

### 4. 中断に耐えられる互換性のあるアプリケーション API バックエンドで、コストと可用性のバランスを取る方法はどれですか？

- A) On-Demand は常に不適切である
- B) Spot のみなら常に可用性が保証される
- C) Spot と On-Demand の混在、およびテスト済みの ARM 対応を検討する
- D) Auto Mode が Fargate ノードをプロビジョニングすると想定する

<details>
<summary>解答を表示</summary>

**解答: C) Spot と On-Demand の混在、およびテスト済みの ARM 対応を検討する**

**解説:**
ここで扱うのはアプリケーションの API バックエンドであり、AWS が管理する Kubernetes API サーバーではありません。混在させる容量に固定比率があるわけでも、即時のフォールバックが保証されるわけでもありません。ARM を使うには、互換性のあるイメージと依存関係を用意し、アプリケーションをテストする必要があります。`weight: 10` はプロビジョニング時の相対的な優先度であり、割合や支出上限ではありません。元の約40%のコスト削減という値は検証されていません。
```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: api-tier
spec:
  template:
    spec:
      requirements:
      - key: eks.amazonaws.com/instance-category
        operator: In
        values:
        - m
        - c
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - on-demand
        - spot
      - key: kubernetes.io/arch
        operator: In
        values:
        - amd64
        - arm64
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
      expireAfter: 168h
      terminationGracePeriod: 24h
      taints:
      - key: workload-lab
        value: api-tier
        effect: NoSchedule
    metadata:
      labels:
        workload-lab: api-tier
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 5m
    budgets:
    - nodes: 10%
  limits:
    cpu: '100'
    memory: 400Gi
  weight: 10
```


</details>

### 5. amd64 と arm64 の両方を許可する前に、何を確認すべきですか？

- A) 確認は不要
- B) digest で固定したイメージのプラットフォーム、ネイティブ依存関係、アプリケーションの動作
- C) Kubernetes のバージョンだけ
- D) リージョンだけ

<details>
<summary>解答を表示</summary>

**解答: B) digest で固定したイメージのプラットフォーム、ネイティブ依存関係、アプリケーションの動作**

**解説:**
以下の index 検査で確認できるのは Linux のプラットフォームエントリーであり、実行時の正しさではありません。無関係な attestation エントリーは除外し、必要なプラットフォームがない場合は失敗します。関連ガイドではローカルの OCI ビルド出力を示しています。指定されていない `myapp:latest` イメージを公開することは、必須のアーキテクチャ検査ではありません。

```bash
: "${IMAGE_REF:?Set a reviewed image reference pinned by digest}"
if ! [[ "$IMAGE_REF" =~ @sha256:[0-9a-f]{64}$ ]]; then
  printf 'Use an immutable sha256 digest reference.\n' >&2
  exit 1
fi
docker buildx imagetools inspect --raw "$IMAGE_REF" > "$WORK_DIR/image-index.json"
jq -e '[.manifests[]?.platform |
         select(.os=="linux" and (.architecture=="amd64" or .architecture=="arm64")) |
         .architecture] | unique | sort == ["amd64","arm64"]' \
  "$WORK_DIR/image-index.json"
```


</details>

### 6. 配置制約を許容しながら、ワークロードを意図したプールへ配置するにはどうしますか？

- A) Pod 名で照合する
- B) 対応する toleration と `nodeSelector` または必須の node affinity を組み合わせる
- C) Namespace による自動照合を使う
- D) AWS タグだけを使う

<details>
<summary>解答を表示</summary>

**解答: B) 対応する toleration と `nodeSelector` または必須の node affinity を組み合わせる**

**解説:**
Toleration は taint の付いたノードへの配置を許可しますが、そのノードへの配置を必須にはしません。selector または必須の affinity によって、配置可能なノードを絞り込みます。以下の断片は Pod テンプレートの `spec` に記述します。関連ガイドには完全な Job も掲載されています。ラベルや taint はテナントを認可する境界ではありません。また、条件に合うキャパシティが不足すれば Pod は Pending のままになることがあります。
```yaml
nodeSelector:
  karpenter.sh/nodepool: batch-tier
tolerations:
- key: workload-lab
  operator: Equal
  value: batch-tier
  effect: NoSchedule
```


</details>

## 参考資料

- [Auto Mode の ML コンピューティング](https://docs.aws.amazon.com/eks/latest/userguide/ml-node-pools.html)
- [Karpenter の disruption](https://karpenter.sh/v1.14/concepts/disruption/)
- [Docker のマルチプラットフォームビルド](https://docs.docker.com/build/building/multi-platform/)
