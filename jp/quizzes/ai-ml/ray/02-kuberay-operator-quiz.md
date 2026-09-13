# KubeRay Operator クイズ

## 多肢選択問題

1. KubeRay operator をインストールすると、何が開始されますか？
   - A) すべての Ray workload が自動的に開始される
   - B) reconciler。workload CR は引き続き作成する必要がある
   - C) すべての GPU node
   - D) worker ごとの Deployment

<details>
<summary>回答を表示</summary>

**回答: B**

Operator のインストールは、RayCluster、RayJob、または RayService resource の作成とは別です。
</details>

2. chart 1.7.0 は何をインストールし、RayCronJob のデフォルト状態は何ですか？
   - A) 3 つの CRD のみが存在する
   - B) インストールされた RayCronJob CRD は常に scheduling を有効にする
   - C) 4 つの CRD。RayCronJob feature gate はデフォルトで無効
   - D) v1 API は存在しない

<details>
<summary>回答を表示</summary>

**回答: C**

RayCluster、RayJob、RayService、RayCronJob を区別してください。
</details>

3. RayJob のデフォルトの cleanup 動作は何ですか？
   - A) shutdownAfterJobFinishes を省略すると cleanup が有効になる
   - B) TTL 0 はすべての EC2 instance と PVC を削除する
   - C) shutdownAfterJobFinishes のデフォルトは false。cleanup と保持を設定する
   - D) external cluster は常に削除される

<details>
<summary>回答を表示</summary>

**回答: C**

TTL、deletionStrategy、共有 cluster と作成された cluster の ownership を確認してください。
</details>

4. RayService の incremental upgrade に必要なものは何ですか？
   - A) feature gate のみで downtime がないことが保証される
   - B) strategy、Gateway API/implementation、capacity、readiness、draining
   - C) 既存の 1 つの Pod image の編集のみ
   - D) 必須の RayJob

<details>
<summary>回答を表示</summary>

**回答: B**

cluster 間で traffic を移行します。単なる in-place Pod rolling update ではありません。
</details>

5. 適切な scaling の順序はどれですか？
   - A) Ray autoscaler がすべての EC2 capacity を直接 provision する
   - B) Ray demand → KubeRay Pod reconciliation → Kubernetes placement/capacity provisioning
   - C) Karpenter が Ray actor method を呼び出す
   - D) 両方の controller が同一の resource を所有する

<details>
<summary>回答を表示</summary>

**回答: B**

image、PVC、または authorization に関連する Pending state は、node を追加するだけでは解決しません。
</details>

6. idleTimeoutSeconds 60 はどのように解釈すべきですか？
   - A) すべての worker は ちょうど 60 秒後に消える
   - B) 確認済みの global default。group override、bound、activity、drain condition を考慮する
   - C) RayJob 全体の TTL
   - D) Karpenter の固定 provisioning time

<details>
<summary>回答を表示</summary>

**回答: B**

設定された duration と実際の deletion 完了は異なります。
</details>

7. GPU resource の優先順位に関する正しい説明はどれですか？
   - A) Pod limit のみが使用され、override は無視される
   - B) structured group resource と rayStartParams は limit を override できる
   - C) すべての Pod には常に 1 つの GPU がある
   - D) logical setting により physical GPU が増える

<details>
<summary>回答を表示</summary>

**回答: B**

Ray logical resource を device plugin、driver、visible hardware と整合させてください。
</details>

8. Helm chart の upgrade は、既存の CRD schema を自動的に update しますか？
   - A) 常に upgrade して削除する
   - B) いいえ。保存されている CR の compatibility と別個の CRD update procedure を確認する
   - C) CRD は通常の Pod である
   - D) 最初に CRD を常に削除しても安全である

<details>
<summary>回答を表示</summary>

**回答: B**

Helm crds/ lifecycle の制限と、CRD deletion の影響を理解してください。
</details>

## 短答問題

9. worker replica count と Ray Pod count が常に等しいとは限らないのはなぜですか？

<details>
<summary>回答を表示</summary>

numOfHosts を使用すると、1 つの group replica が複数の host/Pod に対応する場合があります。実際の spec と生成された resource を比較してください。
</details>

10. Ray token authentication を有効にしても、なぜ security configuration は完了しないのですか？

<details>
<summary>回答を表示</summary>

これは TLS とは別であり、すべての application endpoint に対する authentication/authorization の代わりにはなりません。access path、secret delivery、version support、organizational policy を確認してください。
</details>

---

[学習教材に戻る](../../../ai-ml/ray/02-kuberay-operator.md)
