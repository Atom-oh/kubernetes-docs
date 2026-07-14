# FinOps コスト可視化プラットフォーム クイズ

1. 3つの FinOps 運用サイクルフェーズの正しい順序はどれですか？
   - A) Optimize → Inform → Operate
   - B) Inform → Optimize → Operate
   - C) Operate → Inform → Optimize
   - D) Inform → Operate → Optimize

<details>
<summary>答えを表示</summary>

**回答: B) Inform → Optimize → Operate**

**解説:**
FinOps サイクルは、Inform（コスト可視性の確立）→ Optimize（コスト削減）→ Operate（ガバナンス）の順に反復します。まず、誰が何にどれだけ支出しているかを理解し、その後に最適化し、最後にポリシーで管理します。

</details>

---

2. AWS CUR (Cost and Usage Report) を Kubecost と統合する主な理由は何ですか？
   - A) Kubecost ライセンスコストを削減するため
   - B) Kubernetes 外の AWS サービスコストを追跡するため
   - C) 実際の AWS 請求データと照合して、Pod レベルのコスト精度を向上させるため
   - D) マルチクラスター フェデレーションを有効にするため

<details>
<summary>答えを表示</summary>

**回答: C) 実際の AWS 請求データと照合して、Pod レベルのコスト精度を向上させるため**

**解説:**
Kubecost は公開定価に基づいてコストを見積もります。CUR 統合により、これらの見積もりを Savings Plans、Reserved Instances、交渉済み料金が反映された実際の請求データと照合でき、コスト精度が大幅に向上します。

</details>

---

3. Kyverno でコストラベルを強制する場合、`validationFailureAction: Enforce` は何を意味しますか？
   - A) ラベルのないワークロードに警告を表示する
   - B) 必須ラベルのないワークロードのデプロイをブロックする
   - C) ラベルを自動的に追加する
   - D) 既存のワークロードのラベルを変更する

<details>
<summary>答えを表示</summary>

**回答: B) 必須ラベルのないワークロードのデプロイをブロックする**

**解説:**
`validationFailureAction: Enforce` は、ポリシーに違反するリソースの作成や変更をブロックします。team、service、cost-center ラベルのない Deployment は拒否されます。まず警告用に `Audit` モードから始め、チームの準備が整ったら `Enforce` に切り替えることを推奨します。

</details>

---

4. VPA を `updateMode: "Off"` に設定する理由は何ですか？
   - A) VPA を完全に無効化するため
   - B) Pod を自動的に再起動せず、推奨値のみを提供するため
   - C) メモリを固定したまま CPU のみを調整するため
   - D) HPA との競合を防ぐため

<details>
<summary>答えを表示</summary>

**回答: B) Pod を自動的に再起動せず、推奨値のみを提供するため**

**解説:**
`updateMode: "Off"` により、VPA はリソース使用量を分析し、変更を適用するために Pod を自動的に再起動することなく推奨値を提供します。これにより、推奨値をレビューし、PR 経由で手動適用する安全なワークフローが可能になります。Goldilocks ダッシュボードもこのモードを活用します。

</details>

---

5. Showback と Chargeback の違いは何ですか？
   - A) Showback はコストを表示し、Chargeback はコストを隠す
   - B) Showback はコスト可視性を提供し、Chargeback は実際に部門やチームに課金する
   - C) Showback はリアルタイムで、Chargeback は月次である
   - D) Showback はクラウド専用で、Chargeback はオンプレミス専用である

<details>
<summary>答えを表示</summary>

**回答: B) Showback はコスト可視性を提供し、Chargeback は実際に部門やチームに課金する**

**解説:**
Showback は、意識を高めるために各チームやサービスがどれだけ支出しているかを示します。一方、Chargeback は実際に部門予算からコストを差し引きます。多くの組織は、Chargeback へ移行する前に、コストを意識する文化を確立するため Showback から始めます。

</details>

---

6. Goldilocks がリソース推奨値を表示するには、namespace にどのラベルが必要ですか？
   - A) goldilocks.fairwinds.com/vpa-enabled=true
   - B) goldilocks.fairwinds.com/enabled=true
   - C) vpa.kubernetes.io/enabled=true
   - D) monitoring.goldilocks.com/watch=true

<details>
<summary>答えを表示</summary>

**回答: B) goldilocks.fairwinds.com/enabled=true**

**解説:**
Goldilocks は、`goldilocks.fairwinds.com/enabled=true` ラベルが付いた namespace 内のすべての Deployment に対して VPA を自動的に作成し、推奨されるリソース値を Web ダッシュボードで可視化します。

</details>

---

7. Kubecost Allocation API で `aggregate=label:team` は何を意味しますか？
   - A) team ラベルを持つ Pod のみをフィルタリングする
   - B) team ラベルの値ごとにコストをグループ化して合計する
   - C) team ごとに個別の API 呼び出しを作成する
   - D) team ラベルを自動的に追加する

<details>
<summary>答えを表示</summary>

**回答: B) team ラベルの値ごとにコストをグループ化して合計する**

**解説:**
`aggregate=label:team` は、すべての Pod コストを `team` ラベルの値（例: team-commerce、team-platform）ごとにグループ化して合計するよう Kubecost に指示します。これにより、team ごとの合計コスト、CPU コスト、メモリコストを単一のクエリで取得できます。

</details>

---

8. コスト異常アラートが発火する前に、30分間継続して高コストであることを要求するのはなぜですか？
   - A) Prometheus のスクレイプ間隔が30分だから
   - B) 一時的なスパイク（デプロイ、オートスケーリング）による誤検知を防ぐため
   - C) Slack API のレート制限を回避するため
   - D) Kubecost データ更新サイクルが30分だから

<details>
<summary>答えを表示</summary>

**回答: B) 一時的なスパイク（デプロイ、オートスケーリング）による誤検知を防ぐため**

**解説:**
Deployment、オートスケーリングイベント、バッチジョブは一時的なコストスパイクを引き起こすことがあります。`for: 30m` 条件により、コストが30分以上高い状態で維持された場合にのみアラートが発火し、通常の運用活動によるノイズを減らします。

</details>
