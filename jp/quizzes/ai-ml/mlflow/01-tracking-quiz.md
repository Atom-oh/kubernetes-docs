# MLflow Tracking クイズ

## 選択式問題

1. Experiment と Run はどのように関連していますか？
   - A) Experiment は Run をグループ化し、Run はトレーニングまたは評価を表すことができる
   - B) Experiment は 1 つの GPU である
   - C) Run は常にデプロイ済みモデルである
   - D) 両者は同じエンティティである

<details>
<summary>答えを表示</summary>

**答え: A**

Run には、前処理および比較作業も記録できます。
</details>

2. 新しい MLflow 3.16.0 環境におけるデフォルトのメタデータバックエンドは何ですか？
   - A) S3 バケット
   - B) sqlite:///mlflow.db
   - C) ブラウザの localStorage
   - D) 必須の PostgreSQL

<details>
<summary>答えを表示</summary>

**答え: B**

SQLite がデフォルトです。すでに ./mlruns が存在する場合は、互換性の動作を確認してください。明示的な URI により曖昧さがなくなります。
</details>

3. MLflow 3 の LoggedModel における重要な変更は何ですか？
   - A) 独立した model_id、ステータス、および関係の追跡
   - B) start_run ブロックなしで初めて log_model を呼び出せるようになったこと
   - C) Artifact が不要になったこと
   - D) 登録時に即時 GPU デプロイされること

<details>
<summary>答えを表示</summary>

**答え: A**

2.22.0 の Model.log は、必要な場合にはすでに暗黙的に Run を開始していました。独立したモデル ID は、明示的な Run コンテキストを省略することとは異なります。
</details>

4. autologging について正しい記述はどれですか？
   - A) 任意のコード内にあるすべてをキャプチャする
   - B) 常に PII を削除する
   - C) 各インテグレーションのサポート対象バージョンと収集される入力／出力を確認する
   - D) 自動的にデプロイを完了する

<details>
<summary>答えを表示</summary>

**答え: C**

動作はフレームワークとオプションに依存します。入力例、生データ、モデル Artifact の収集を確認してください。
</details>

5. tracing とコストについて正確な記述はどれですか？
   - A) tracing は 3.x で初めて登場した
   - B) すべてのツール span には LLM コストがある
   - C) トークンから導出されたコストは常に請求額と一致する
   - D) tracing は 2.14.0 で導入され、使用量の収集はインテグレーションに依存する

<details>
<summary>答えを表示</summary>

**答え: D**

後の拡張と最初の導入を区別してください。モデル、使用量、価格情報がなければ、コストを保証することはできません。
</details>

6. リモート Tracking サーバーを使用していても、クライアントが S3 権限を必要とするのはどのような場合ですか？
   - A) 直接 S3 Artifact URI を使用する非プロキシモード
   - B) SQLite パラメータを読み取る場合のみ
   - C) モードにかかわらず権限は不要である
   - D) すべてのエイリアス名の検索で S3 アクセスが必要となる

<details>
<summary>答えを表示</summary>

**答え: A**

メタデータと Artifact のパスは異なります。直接モードでは、クライアントにストレージ権限とネットワークアクセスが必要です。
</details>

7. ステップ 0 と 1 でログに記録された metric はどのように調べますか？
   - A) パラメータが自動的に変更される
   - B) 2 番目の値だけが永続的に保持される
   - C) get_metric_history を使用して両方の観測値を調べる
   - D) 2 つのモデルが自動的に登録される

<details>
<summary>答えを表示</summary>

**答え: C**

現在の要約と、タイムスタンプおよびステップ付きの metric 履歴を区別してください。
</details>

8. 適切な Tracking Web UI のクエリパスはどれですか？
   - A) ブラウザが PostgreSQL に直接接続する
   - B) ブラウザがサーバー HTTP API を呼び出す
   - C) UI は常にトレーニング Pod から直接ファイルを読み取る
   - D) ブラウザにはデータベース管理者のパスワードが必要である

<details>
<summary>答えを表示</summary>

**答え: B**

サーバーがそのバックエンドにアクセスします。Artifact プロキシの設定は別の懸念事項です。
</details>

## 記述式問題

9. PENDING の initialize_logged_model 結果は、直ちに推論を実行できますか？

<details>
<summary>答えを表示</summary>

いいえ。メタデータのみの場合があります。実際の flavor、重み、Artifact のロギング、およびファイナライズが依然として必要です。READY は品質またはデプロイの承認を意味するものではありません。
</details>

10. サーバーの Artifact フラグを変更した後でも、既存の Experiment が S3 に直接アクセスする場合があるのはなぜですか？

<details>
<summary>答えを表示</summary>

記録済みの Experiment/Run Artifact URI は遡及的に書き換えられません。その URI と、実際の権限および転送パスを確認してください。
</details>

---

[学習教材に戻る](../../../ai-ml/mlflow/01-tracking.md)
