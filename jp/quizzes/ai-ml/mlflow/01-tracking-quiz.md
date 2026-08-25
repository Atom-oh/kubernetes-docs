# MLflow Tracking クイズ

このクイズでは、MLflow Tracking の中核概念、MLflow 3 におけるファーストクラスのログ済みモデルへの移行、autologging、GenAI tracing、そして backend store と artifact store の分離についての理解を確認します。

## 多肢選択問題

1. MLflow Experiment とは何ですか？
   - A) 独自の params と metrics を持つ、training code の単一実行
   - B) 名前付きの Runs コレクション
   - C) MLflow の metadata を保存する database
   - D) シリアライズされた model file

<details>

<summary>回答を表示</summary>

**回答: B) 名前付きの Runs コレクション**

**解説:**
Experiment は Runs を名前でグループ化したもので、通常はプロジェクトごと、または反復処理中の model ごとに 1 つ作成します。Run は、独自の params、metrics、tags、artifacts を持つ training code の単一実行であり、これは別の概念です（選択肢 A）。
</details>

2. MLflow 1.x/2.x の run 中心モデルでは、ログ済み model は通常どのように表現されていましたか？
   - A) どの run にも依存しない `LoggedModel` entity として
   - B) それを生成した Run 配下にネストされた artifact として
   - C) backend store の metrics table 内の row として
   - D) スタンドアロンの experiment として

<details>

<summary>回答を表示</summary>

**回答: B) それを生成した Run 配下にネストされた artifact として**

**解説:**
MLflow 3 より前では、ログ済み model は run の artifact directory 内に保存される単なる artifact でした。model を見つけるには、まずその model を生成した run を見つける必要がありました。MLflow 3 では、`LoggedModel` を独立したファーストクラス entity として導入することでこれが変更されました。
</details>

3. MLflow 3 の `LoggedModel` entity によって可能になった、従来の run 配下にネストされたモデルにはなかった主要な機能は何ですか？
   - A) アクティブな `mlflow.start_run()` context なしで、`mlflow.sklearn.log_model(...)` を直接呼び出すこと
   - B) tracking server なしで metrics をログに記録すること
   - C) Python なしで training code を実行すること
   - D) artifact store なしで artifacts を保存すること

<details>

<summary>回答を表示</summary>

**回答: A) アクティブな `mlflow.start_run()` context なしで、`mlflow.sklearn.log_model(...)` を直接呼び出すこと**

**解説:**
`LoggedModel` は Runs から分離されたファーストクラス entity になったため、追跡対象としてアクティブな run の配下にネストする必要がなくなりました。これにより、model の versioning と比較を単一の training run から切り離せます。
</details>

4. `mlflow.autolog()` は何をしますか？
   - A) 学習済み model を serving endpoint に自動的に deploy する
   - B) 対応する ML library を instrument し、手動の logging call なしで、training 中に params、metrics、artifacts を自動的にログに記録する
   - C) storage を節約するために古い runs を自動的に削除する
   - D) Run を LoggedModel に変換する

<details>

<summary>回答を表示</summary>

**回答: B) 対応する ML library を instrument し、手動の logging call なしで、training 中に params、metrics、artifacts を自動的にログに記録する**

**解説:**
Autologging は、対応する framework の一般的な training data を自動的にキャプチャします。MLflow は、検出されたすべての framework ではなく、1 つの library のみで autologging を有効にするための framework 固有の autolog function（例: scikit-learn または PyTorch 用）も提供します。
</details>

5. MLflow 3 において、"tracing" は主に何に使用されますか？
   - A) 従来の scikit-learn training runs の params と metrics のログ記録
   - B) GenAI observability のために、LLM/agent calls の内部ステップ（spans）、token 使用量、cost をキャプチャすること
   - C) artifact store の disk 使用量の追跡
   - D) Experiments/Runs view を完全に置き換えること

<details>

<summary>回答を表示</summary>

**回答: B) GenAI observability のために、LLM/agent calls の内部ステップ（spans）、token 使用量、cost をキャプチャすること**

**解説:**
Tracing は、LLM または agent call を spans の tree としてキャプチャします。各 span は retrieval call や tool invocation などのステップを表し、token 使用量と cost も含みます。これにより、別個の tool を必要とするのではなく、GenAI/agent observability を中核機能としてカバーするよう MLflow Tracking を拡張します。
</details>

6. LangChain と並んで、MLflow が auto-tracing integration を提供する framework の例は次のうちどれですか？
   - A) Kubernetes
   - B) PostgreSQL
   - C) PydanticAI
   - D) Terraform

<details>

<summary>回答を表示</summary>

**回答: C) PydanticAI**

**解説:**
MLflow は LangChain を含む人気の LLM/agent frameworks 向けの auto-instrumentation を提供しており、PydanticAI や smolagents などの frameworks 向けに新しい auto-tracing integrations も提供しています。
</details>

7. team 規模では、なぜ backend store に通常、実際の relational database（PostgreSQL や MySQL など）が必要ですか？
   - A) database は object storage よりも大きな binary model files を適切に処理できるため
   - B) params、metrics、tags、run/experiment/model records という構造化 metadata を保持しており、迅速な local experimentation を超える用途では database のメリットを得られるため
   - C) MLflow が UI を render するために SQL database を必要とするため
   - D) object storage は metadata をまったく保存できないため

<details>

<summary>回答を表示</summary>

**回答: B) params、metrics、tags、run/experiment/model records という構造化 metadata を保持しており、迅速な local experimentation を超える用途では database のメリットを得られるため**

**解説:**
backend store は、relational database の多数の小規模な構造化 write と query に適した構造化 metadata を保持します。一方、artifact store は大きな binary objects を保持し、通常は S3-compatible bucket などの object storage です。
</details>

8. tracking flow（training script -> Tracking API -> tracking server -> backend store + artifact store）において、Tracking UI は何をしますか？
   - A) training script の local disk に直接書き込む
   - B) backend store と artifact store の両方から読み取り、experiments、runs、logged models、traces を render する
   - C) tracking server をバイパスし、backend store のみを query する
   - D) artifacts のみを表示し、metadata は決して表示しない

<details>

<summary>回答を表示</summary>

**回答: B) backend store と artifact store の両方から読み取り、experiments、runs、logged models、traces を render する**

**解説:**
training script は Tracking API とだけ通信します。tracking server は metadata writes を backend store に、file writes を artifact store にルーティングします。UI は必要なすべてを表示するために、両方の store から読み取ります。
</details>

## 短答問題

9. MLflow 3 が `LoggedModel` と、それに関連する runs、traces、prompts、evaluation metrics の間の lineage を追跡することによる実用的なメリットは何ですか？

<details>

<summary>回答を表示</summary>

**回答: model は、それを学習した単一の run に恒久的に紐付けられなくなります。学習した run、評価した runs、そしてそれを serving することで生成された traces にリンクできます。**

**解説:**
`LoggedModel` は 1 つの run 配下にネストされた file ではなくファーストクラス entity であるため、MLflow 3 は model とそれに関連するすべてのものとの間に、より豊かな関係を表現できます。これは、model が多数の runs にわたって反復処理される場合、または既存の LLM を custom logic でラップするように、従来の training loop の外部で生成される場合に特に重要です。
</details>

10. MLflow が、従来の ML experiment tracking と GenAI/agent observability を 2 つの別個の tools ではなく 1 つの system として位置付けているのはなぜですか？

<details>

<summary>回答を表示</summary>

**回答: MLflow 3 は、両方をカバーするよう同じ Tracking system（および UI）を拡張したためです。GenAI/agent calls の tracing は、従来の training runs の params/metrics/artifacts と同じ tracking server、UI、lineage model を使用します。**

**解説:**
従来の ML training と LLM/agent development の両方を行う team は、GenAI 側だけのために別個の observability tool を立ち上げるのではなく、両方に 1 つの MLflow Tracking deployment を使用できます。
</details>

---

[学習教材に戻る](../../../ai-ml/mlflow/01-tracking.md) | [次のクイズ: Model Registry](./02-model-registry-quiz.md)
