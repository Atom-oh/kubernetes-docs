# EKS Auto Mode のスケーリング動作クイズ

> **関連ドキュメント**: [スケーリング動作](../../eks-auto-mode/03-scaling-behavior.md)

## 選択問題

### 1. `consolidationPolicy: WhenEmptyOrUnderutilized` で許可されるのはどれですか？

- A) 空のノードだけを削除する
- B) 対象となる空または空でないノードを、コスト削減のために統合する
- C) すべてのノードを無期限に維持する
- D) 固定時刻に限って削除する

<details>
<summary>解答を表示</summary>

**解答: B) 対象となる空または空でないノードを、コスト削減のために統合する**

**解説:**
関連する制約の下でワークロードをスケジュール可能な状態に保てる場合に、ノードの削除や、より低コストな構成への置き換えが許可されます。リソース要求、PDB、予算、アノテーションが影響します。実測 CPU 使用率だけで決まるわけではありません。

```yaml
# Fragment inside a NodePool; eligibility delay, not a deletion deadline
disruption:
  consolidationPolicy: WhenEmptyOrUnderutilized
  consolidateAfter: 1m
```

Pod が追加または削除されるとタイマーはリセットされます。1 分は処理対象になり得るまでの安定待ち時間であり、削除や置き換えが 1 分以内に完了する保証ではありません。現在の AWS API は `Balanced` もサポートしており、コスト削減とあわせて中断のコストを考慮します。

</details>

### 2. NodeClaim を一覧表示するコマンドはどれですか？

- A) kubectl get nodes --show-claims
- B) kubectl get nodeclaims
- C) kubectl describe karpenter claims
- D) kubectl get ec2-nodes

<details>
<summary>解答を表示</summary>

**解答: B) kubectl get nodeclaims**

**解説:**
NodeClaim には、希望するノード構成とプロバイダーのライフサイクルやステータスが記録されます。プロビジョニングの瞬間だけを表すものではありません。condition と関連付けられたノード名を確認してください。`Drifted` は condition であり、かつて存在すると誤って説明された `karpenter.sh/drift-hash` ノードアノテーションではありません。

```bash
kubectl --context "$CLUSTER_NAME" --request-timeout=15s get nodeclaims -o wide
: "${NODECLAIM_NAME:?Select a NodeClaim from the list}"
kubectl --context "$CLUSTER_NAME" --request-timeout=15s describe nodeclaim "$NODECLAIM_NAME"
```

</details>

### 3. スケジュール不能な Pod によって、Auto Mode がキャパシティをプロビジョニングするのはどのような場合ですか？

- A) すべての Pod が 5 分間 Pending になった場合
- B) 既存のキャパシティに Pod を配置できず、適合する利用可能なプールやキャパシティが Pod の制約を満たせる場合
- C) ノード数が固定のグローバルなしきい値を下回った場合
- D) オペレーターが手動のスケールコマンドを実行した後に限る

<details>
<summary>解答を表示</summary>

**解答: B) 既存のキャパシティに Pod を配置できず、適合する利用可能なプールやキャパシティが Pod の制約を満たせる場合**

**解説:**
スケジューラーが Pod を配置できるか、NodePool と NodeClass の制約に適合するか、クォータと実際のキャパシティがあるか、すべてが関係します。スケジュール自体は済んでいても、イメージの取得や init container の完了を待つ Pod は Pending になることがあり、その場合は新しいノードが必要とは限りません。Auto Mode は即時の割り当てを保証しません。また、以前の未検証の「40～90 秒」という見積もりも保証値ではありません。

</details>

### 4. 統合候補ノードの統合を妨げる可能性があるものはどれですか？

- A) 対象ノードまたは Pod に適用される do-not-disrupt アノテーション
- B) PDB によって必要なワークロードの退避が阻止されること
- C) `consolidateAfter` で指定された安定待ち時間が経過していないこと
- D) 上記すべて

<details>
<summary>解答を表示</summary>

**解答: D) 上記すべて**

**解説:**
いずれも統合作業を妨げたり遅らせたりする可能性があります。以前の選択肢には「DaemonSet だけが実行されているノード」も妨げになるとありましたが、そうしたノードも空とみなされ、統合対象になり得ます。

```yaml
# Metadata fragment on the intended Node or Pod, not NodePool metadata
metadata:
  annotations:
    karpenter.sh/do-not-disrupt: "true"
```

このアノテーションがあらゆる理由による中断を防ぐわけではありません。有効期限、割り込み、終了猶予時間の上限は別途考慮が必要です。一時的な保護は、保守上必要な期間が終わったら解除してください。

</details>

### 5. Drift や置き換えの要因になり得るものはどれですか？

- A) 希望する NodeClass の関連設定が、ノードの状態と一致しなくなること
- B) AWS が Auto Mode 管理の新しい AMI を選択すること
- C) 解決されるサブネットまたはセキュリティグループの選択が変わること
- D) 上記のすべてが要因になり得る

<details>
<summary>解答を表示</summary>

**解答: D) 上記のすべてが要因になり得る**

**解説:**
実際の NodeClaim condition とプロバイダーの判断を確認してください。設定を変更すれば必ず Drift が発生するわけではありません。要件を広げても既存インスタンスが引き続き適合する場合があり、weight、limits、disruption の設定は動作に影響する項目です。同じセキュリティグループ内のルールを編集することと、解決されるセキュリティグループ自体が変わることも異なります。スケジューリングと予算の条件を満たせば、正常な置き換えは複数ノードで並行して進む場合があり、常に一度に 1 ノードずつ順番に行われるわけではありません。

</details>

### 6. Auto Mode の起動レイテンシーを改善するには、どうすればよいですか？

- A) `amiFamily` を AL2023 に切り替える
- B) ワークロードの処理経路を計測し、サポートされるキャパシティ、イメージ、ストレージの変更を検証する
- C) 可能な限り小さいボリュームが常に最速だと仮定する
- D) 40～90 秒をエンドツーエンドの SLO として保証値のように扱う

<details>
<summary>解答を表示</summary>

**解答: B) ワークロードの処理経路を計測し、サポートされるキャパシティ、イメージ、ストレージの変更を検証する**

**解説:**
AWS は Auto Mode が管理する Bottlerocket イメージを選択します。Auto Mode には、以前の `amiFamily` 比較用設定はありません。ノード登録、イメージ取得と初期化、アプリケーションの準備完了を分けて計測し、失敗やタイムアウトも測定に含めてください。

以前のクイズに記載されていた **AL2023 の 20～40 秒** と **Bottlerocket の 15～25 秒** は、未検証の過去の教材上の推定値としてここに残しています。実測された Auto Mode の結果ではなく、現在の起動時間の優位性やサポート対象の AMI 選択を示すものではありません。

</details>
