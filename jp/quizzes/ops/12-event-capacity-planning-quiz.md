# イベントのキャパシティ計画クイズ

> **関連ドキュメント**: [イベントのキャパシティ計画](../../ops/12-event-capacity-planning.md)

## 1. 複数の KEDA metric を使う場合、目標値はどのように決まりますか？

- A) すべての値を合計する
- B) HPA が metric ごとの推奨値の最大値を使い、behavior と最小値・最大値を適用する
- C) Cron が Pod の Ready 状態を保証する
- D) metric が常に上限を決める

<details>
<summary>回答を表示</summary>

**回答: B**

Cron はスケジュールに基づく需要の下限を示し、`maxReplicaCount` などの制約が上限を定めます。実際に Pod が Ready になったかは別途確認してください。

</details>

## 2. 日付が決まっているイベントで、5 フィールド形式の Cron を使う場合に重要な点は何ですか？

- A) 年は暗黙に指定される
- B) 1 回実行すると自動的に削除される
- C) 翌年も繰り返される可能性があるため、timezone と DST を確認する
- D) 常に UTC だけを使う

<details>
<summary>回答を表示</summary>

**回答: C**

この例では、年次の繰り返しと期間の境界を確認します。イベント後は構成を削除するか更新してください。

</details>

## 3. 静的な Karpenter NodePool を構成する方法はどれですか？

- A) `weight` だけを大きくして容量を静的にする
- B) `weight` を使わずに `replicas` を指定し、`limits.nodes` で制限する
- C) いつでも `replicas` を削除すれば動的モードに切り替わる
- D) すべての NodePool budget が常にスケーリング操作をブロックする

<details>
<summary>回答を表示</summary>

**回答: B**

静的モードと動的モードを区別してください。静的スケーリングは NodePool の disruption budget を迂回しますが、PDB には従います。

</details>

## 4. 引き継ぎ後も placeholder Deployment の desired 数が変わらないと、何が起こる可能性がありますか？

- A) 追加費用が発生することはない
- B) placeholder が再作成され、node が追加で provision されることがある
- C) Karpenter が desired 数を自動的に 0 にする
- D) 実アプリケーションが常にすぐ Ready になる

<details>
<summary>回答を表示</summary>

**回答: B**

placeholder の保持期間と期限切れ、placeholder 需要の削除、実アプリケーションの readiness を合わせて確認してください。

</details>

## 5. 容量を 30% 増やせば、1 つの AZ を失っても必ずサービスを維持できますか？

- A) 常に維持できる
- B) On-Demand なら維持できる
- C) いいえ。配置と残存スループットを計算する必要がある
- D) PDB があれば維持できる

<details>
<summary>回答を表示</summary>

**回答: C**

15 node と 11 node の例では、より多くの node がある AZ を失うと、残りの容量がベースラインのピーク需要を満たしません。入力した前提も実測で検証してください。

</details>

## 6. 特定の Capacity Reservation は何を意味しますか？

- A) 1 つの NodePool だけに制限されたセキュリティ ACL
- B) instance が明示的に対象として指定し、一致条件を満たす必要がある予約
- C) 既存のすべての instance に自動適用される予約
- D) On-Demand の割引商品

<details>
<summary>回答を表示</summary>

**回答: B**

IAM と共有設定、AZ、instance type、platform、tenancy、実際の消費状況を確認してください。Capacity Reservation は RI とは別のものです。

</details>

## 7. D-30 に即時予約を作成し、将来の `end_date` だけを指定すると何が起こりますか？

- A) イベントまで無料で待機する
- B) `end_date` が将来の開始時刻を指定する
- C) 使用されていない稼働中の容量にも料金が発生することがある
- D) 予約済み容量を使う instance に必ず二重課金される

<details>
<summary>回答を表示</summary>

**回答: C**

コストモデルには予約が有効な期間を含め、予約を消費している instance を二重計上しないようにしてください。

</details>

## 8. CloudWatch scaler の `metricStat` と `minMetricValue` について、正しい説明はどれですか？

- A) 正しい field は `metricStatType` である
- B) `minMetricValue` は常に activation threshold である
- C) `metricStat` は statistic を選び、`minMetricValue` は NoData 時の代替値を指定する。ただし `ignoreNullValues=false` の場合は上書きされる
- D) `Sum` はあらゆる rate gauge に適している

<details>
<summary>回答を表示</summary>

**回答: C**

差分や count と、rate や累積 counter を区別し、period、収集期間、metric の発行遅延を確認してください。

</details>

## 9. metric の反映が遅れている場合、KEDA 管理下の workload をどう扱うべきですか？

- A) Deployment を直接スケーリングすれば常に設定が維持される
- B) HPA 名は常に Deployment 名と同じである
- C) 承認済みの範囲内で ScaledObject の下限を確認し、GitOps の所有関係を守る
- D) 上限のない NodePool を作成する

<details>
<summary>回答を表示</summary>

**回答: C**

直接加えた HPA や Deployment の変更は、reconciliation によって上書きされることがあります。元の設定を記録し、復元してください。

</details>

## 10. 準備と後片付けについて、正しい説明はどれですか？

- A) すべての image が `sh` と `echo` を備え、cache を無期限に保持する
- B) 30 分後に NodePool を削除すれば常に安全である
- C) アプリケーションと cache の制約、ベースラインの発動条件、実際の node と予約の後片付けを検証する
- D) ScaledObject を削除すれば元の replica 数が常に復元される

<details>
<summary>回答を表示</summary>

**回答: C**

起動処理、GC、architecture、権限は環境によって異なります。後片付けでは、各リソースを所有する controller と削除時のライフサイクルを考慮してください。

</details>
