# EKS Auto Mode の運用クイズ

> **関連ドキュメント**: [運用](../../eks-auto-mode/05-operations.md)
> **最終更新**: 2026年9月12日

## 選択問題

### 1. ソウルの営業時間中に、該当する任意の NodePool 中断を防ぐスケジュール設定はどれですか？

- A) `nodes: "100%"`
- B) UTC の範囲を正しく指定した `nodes: "0"`
- C) `consolidateAfter: 0s`
- D) `consolidationPolicy: Never`

<details>
<summary>解答を表示</summary>

**解答: B) UTC の範囲を正しく指定した `nodes: "0"`**

**解説:**
予算を 0 にすると、有効な間は Consolidation や Drift など、該当するグレースフルな中断方式がブロックされます。EC2 の中断、期限切れ、修復、あらゆる手動削除まで止めるものではありません。以下の毎日の UTC 00:00 開始、9 時間の期間は、平日のソウル時間 09:00～18:00 に相当します。1 時間ごとの `9-18` スケジュールに 9 時間の期間を組み合わせると、時間帯が重複して繰り返し開始されます。

```yaml
# Fragment of NodePool spec.disruption
budgets:
  - nodes: "10%"
  - nodes: "0"
    schedule: "0 0 * * mon-fri"
    duration: 9h
```

</details>

### 2. スケーラブルなコントローラーの 6 レプリカを選択する PDB で、`minAvailable: "80%"` は何を意味しますか？

- A) 実行可能な Pod は最大 80% である
- B) Eviction の判定では、切り上げて 5 個の正常なレプリカが必要になる
- C) 各 Pod が 80% の確率で保持される
- D) Pod が 80 秒間保護される

<details>
<summary>解答を表示</summary>

**解答: B) Eviction の判定では、切り上げて 5 個の正常なレプリカが必要になる**

**解説:**
コントローラーは 6 の 80% を切り上げ、正常な Ready レプリカが 5 個必要と判断します。これは Eviction API による判定を制約しますが、すべての障害、直接削除、レプリカの作成を制約するわけではありません。`minAvailable` と `maxUnavailable` は意味の異なる代替フィールドであり、両方を設定しないでください。レプリカが 5 個で `minAvailable: 3` の例では、`maxUnavailable: 1` の場合と異なり、最大 2 個まで Eviction が許可されます。

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: web-pdb
  namespace: ops-lab
spec:
  minAvailable: "80%"
  selector:
    matchLabels:
      app: web-app
```

`disruptionsAllowed` が 0 でも、意図した正常なブロックである場合があります。違反と判断する前に、`observedGeneration`、`currentHealthy`、`desiredHealthy` を確認してください。

</details>

### 3. Auto Mode ノードのプロビジョニング過程を診断するのに役立つリソースはどれですか？

- A) アプリケーションログのみ
- B) NodeClaim の conditions と、それに関連する NodePool／NodeClass の情報
- C) EC2 コンソールのみ
- D) CloudWatch ウィジェットのみ

<details>
<summary>解答を表示</summary>

**解答: B) NodeClaim の conditions と、それに関連する NodePool／NodeClass の情報**

**解説:**
まず conditions と理由を読み、証拠に応じてスケジューリング制約、NodeClass の準備状況、IAM、ネットワーク設定を調べてください。NodeClaim に一般的な `.status.phase` フィールドはありません。以下では関連ガイドで設定した `KUBE_CONTEXT` を使い、オブジェクト全体を出力する代わりに診断対象のフィールドを選んでいます。

```bash
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s get nodeclaims -o json |
  jq '[.items[] | {name: .metadata.name, uid: .metadata.uid, node: .status.nodeName,
      pool: .metadata.labels["karpenter.sh/nodepool"], createdAt: .metadata.creationTimestamp,
      expireAfter: .spec.expireAfter, terminationGracePeriod: .spec.terminationGracePeriod,
      imageID: .status.imageID,
      conditions: [.status.conditions[]? | {type,status,reason,lastTransitionTime,observedGeneration}]}]'
```

</details>

### 4. 認識される do-not-disrupt アノテーションはどれですか？

- A) `kubernetes.io/do-not-disrupt: "true"`
- B) `karpenter.sh/do-not-disrupt: "true"`
- C) `eks.amazonaws.com/no-disrupt: "true"`
- D) `node.kubernetes.io/exclude-disruption: "true"`

<details>
<summary>解答を表示</summary>

**解答: B) `karpenter.sh/do-not-disrupt: "true"`**

**解説:**
Pod と Node では適用範囲が異なります。Pod のアノテーションは、その Pod の任意の Eviction と、それを含むノードの Consolidation をブロックします。NodeClaim の終了猶予期間があれば、そのような Pod を含むノードの Drift は許可され、最終的には drain が上限時間内に制御されます。Node のアノテーションは、そのノードを任意の中断の対象から除外します。どちらも、期限切れ、中断、修復、手動削除に対する無期限の保証ではありません。Auto Mode には独自の既定の終了猶予期間があるため、未設定だと想定しないでください。

```yaml
# Metadata fragment for a deliberately selected Pod or Node.
# Review the different Pod/Node semantics before applying.
metadata:
  annotations:
    karpenter.sh/do-not-disrupt: "true"
```

この metadata 断片だけでは、実行可能な Pod にはなりません。実際のワークロードに適用する前に、解除や復旧の計画を決めてください。

</details>

### 5. Auto Mode の運用状況を把握するのに有用な監視方法はどれですか？

- A) `kubectl top` のみを使う
- B) 設定したメトリクス収集・ログ配信と、Kubernetes の状態およびワークロードのシグナルを組み合わせる
- C) EC2 コンソールのみを使う
- D) 収集設定をしなくてもすべてのメトリクスが CloudWatch にあると想定する

<details>
<summary>解答を表示</summary>

**解答: B) 設定したメトリクス収集・ログ配信と、Kubernetes の状態およびワークロードのシグナルを組み合わせる**

**解説:**
Container Insights、EKS コントロールプレーンメトリクス、kube-state-metrics／node-exporter、管理対象の Auto Mode コンポーネントログには、それぞれ異なる前提条件があります。各データ発行元とディメンションを確認してください。`kubectl top` には正常に動作する Metrics API が必要です。エラーが出ても、metrics-server が存在しない証明にはなりません。管理対象コンポーネントのログには、個別の Vended Logs 配信設定が必要です。スケジューリング遅延とアプリケーション可用性には、適切な計装が必要です。Container Insights を有効にしても、提案されているすべてのシグナルが自動的に得られるわけではありません。

</details>

### 6. NodePool のどのフィールドで、経過時間に基づく期限切れの対象を設定しますか？

- A) `autoUpdate: true`
- B) `expireAfter`
- C) `updatePolicy: Rolling`
- D) `refreshInterval: 24h`

<details>
<summary>解答を表示</summary>

**解答: B) `expireAfter`**

**解説:**
この例では NodeClaim が 168 時間後に期限切れの対象となり、終了処理の期間は別の設定で制限されています。7 日間の中断なし稼働、正確な時刻での置き換え、期限までの最新セキュリティパッチ適用を保証するものではありません。それ以前に Drift、Consolidation、中断が起きる可能性があり、テンプレートを変更しても既存の NodeClaim は書き換わりません。Auto Mode の既定値と最大存続期間、およびアプリケーションの復旧要件を確認してください。

```yaml
# Fragment of NodePool spec.template.spec
expireAfter: 168h
terminationGracePeriod: 24h
```

</details>

### 7. 複数の該当する NodePool disruption budget はどのように組み合わされますか？

- A) 最後のスケジュール項目が以前の項目を上書きする
- B) 最も小さい許容値が適用される
- C) パーセンテージが加算される
- D) 置き換えノードの数が保証される

<details>
<summary>解答を表示</summary>

**解答: B) 最も小さい許容値が適用される**

**解説:**
常時有効な 10% の上限を、スケジュールされた 30% の予算で緩和することはできません。関連ガイドでは、30% を基準に、ソウル時間の平日に適用する 10% の上限、営業時間の 1 ノード上限、明示的な UTC の月次停止期間を追加しています。ほかの条件を満たすノードが 20 個なら、それぞれの許容数は 6、2、1、0 です。削除中または NotReady のノードは許容値を減らします。これらの予算は、あらゆる強制的な中断を制約するものではありません。

```yaml
disruption:
  consolidationPolicy: WhenEmptyOrUnderutilized
  consolidateAfter: 5m
  budgets:
  - nodes: 30%
  - nodes: 10%
    schedule: 0 15 * * sun-thu
    duration: 24h
  - nodes: '1'
    schedule: 0 0 * * mon-fri
    duration: 9h
  - nodes: '0'
    schedule: 0 0 1 * *
    duration: 24h
```

</details>

### 8. 発行元が設定されている場合、ノード関連の運用アラートを定義するのに役立つシグナルはどれですか？

- A) EC2 の状態のみ
- B) スケジューリング待ち、測定したプロビジョニング遅延、ワークロードの可用性
- C) コストのみ
- D) ネットワークトラフィックのみ

<details>
<summary>解答を表示</summary>

**解答: B) スケジューリング待ち、測定したプロビジョニング遅延、ワークロードの可用性**

**解説:**
各アラートについて、データ発行元、ディメンション、統計量、時間範囲、アプリケーションの目標を選んでください。Pending は Unschedulable と同じ意味ではありません。次の数値例は検証されていない計画上のしきい値であり、通常範囲の実測値、Auto Mode の既定値、または Container Insights で必ず得られるメトリクスではありません。

| シグナル | 以前の計画例 | 以前のアラート例 |
|--------|----------------|----------------|
| Pending Pod | 0–5 | 5 分間 >10 |
| ノードのプロビジョニング時間 | <90 秒 | >120 秒 |
| ワークロード可用性 | >99.9% | <99.5% |
| API 応答時間 | <200 ms | >500 ms |

メトリクスの欠落や古い収集データを、エラーが 0 件である状態と区別できるようにしてください。関連ガイドでは、メトリクス名を作り上げる代わりに、実際のメトリクスカタログからローカルの CloudWatch ダッシュボード定義を作成します。

</details>

## 参照資料

- [Karpenter の disruption 制御](https://karpenter.sh/v1.14/concepts/disruption/)
- [Kubernetes PDB の仕様](https://kubernetes.io/docs/tasks/run-application/configure-pdb/)
- [Auto Mode NodePool](https://docs.aws.amazon.com/eks/latest/userguide/create-node-pool.html)
