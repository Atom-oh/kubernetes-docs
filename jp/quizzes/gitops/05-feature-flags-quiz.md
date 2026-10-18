# Feature Flags と OpenFeature クイズ

1. OpenFeature の Provider モデルの主な利点は何ですか？
   - A) ベンダーロックインにより最適なパフォーマンスが得られる
   - B) ベンダーに依存しない評価 API により、バックエンドを切り替える際のコード変更を抑えられる
   - C) 独自の Feature Flag サーバーを実行する必要がある
   - D) REST API のみをサポートする

<details>
<summary>回答を表示</summary>

**回答: B) ベンダーに依存しない評価 API により、バックエンドを切り替える際のコード変更を抑えられる**

**解説:**
OpenFeature のベンダーに依存しない SDK API を使うと、バックエンドを切り替えるときに評価処理のコードを変更する量を減らせます。ただし、フラグキー、バリアント、対象指定ルール、コンテキストの意味、認証情報、キャッシュ、イベントの動作については、移行とテストが必要です。

</details>

---

2. Kubernetes 上での flagd の Sidecar デプロイモードと Standalone デプロイモードの違いは何ですか？
   - A) Sidecar の方が高性能で、Standalone の方が管理しやすい
   - B) Sidecar はアプリケーションの Pod 内で動作し、Standalone は共有 Service を通じて評価要求を処理する
   - C) Sidecar は TCP のみをサポートし、Standalone は HTTP のみをサポートする
   - D) Sidecar は CRD を使用し、Standalone は ConfigMap のみを使用する

<details>
<summary>回答を表示</summary>

**回答: B) Sidecar はアプリケーションの Pod 内で動作し、Standalone は共有 Service を通じて評価要求を処理する**

**解説:**
RPC は Sidecar にローカル接続することも、Service 経由で共有 Deployment を呼び出すこともできます。実際のレイテンシーとリソース使用量を測定してください。Sidecar/共有型という区分は配置場所を表し、RPC/プロセス内という区分は評価処理をどこで実行するかを表します。プロセス内 Provider はルールを同期し、アプリケーション内で評価できます。

</details>

---

3. Feature Flag の Evaluation Context に含まれる情報の役割は何ですか？
   - A) コンパイル時に Flag を決定するためのビルド情報を渡す
   - B) ユーザー ID、リージョン、環境などのコンテキストを使用してターゲティングルールを評価する
   - C) データベース接続情報を渡す
   - D) Kubernetes ノード情報を渡す

<details>
<summary>回答を表示</summary>

**回答: B) ユーザー ID、リージョン、環境などのコンテキストを使用してターゲティングルールを評価する**

**解説:**
Evaluation Context は、Flag 評価時に動的に渡されるメタデータです。ユーザー ID、リージョン、環境（dev/staging/prod）、ユーザーグループなどの情報が含まれます。ターゲティングルールはこの情報を使い、特定のユーザーやグループに機能を有効化します。権限や利用資格の判定には、サーバー側で検証した属性を使ってください。Feature Flag は認証や認可の代わりにはなりません。

</details>

---

4. Dark Launch パターンにおける Feature Flag の役割は何ですか？
   - A) サービスを完全に隠し、アクセスをブロックする
   - B) 既存の結果を返したまま、副作用のないシャドー実行で新しいロジックをテストする
   - C) サーバーをダークモードに切り替える
   - D) 夜間にのみデプロイを実行する

<details>
<summary>回答を表示</summary>

**回答: B) 既存の結果を返したまま、副作用のないシャドー実行で新しいロジックをテストする**

**解説:**
シャドー検証では既存の結果を返しながら、読み取り専用の計算または隔離した再生処理で新旧の結果を比較します。課金、業務記録の書き込み、通知の二重送信を起こしてはいけません。非同期処理の並行数に上限を設け、バックグラウンド処理には個別のタイムアウトを設定してください。これは新しい結果を選ばれたユーザーに実際に公開する段階的リリースとは異なります。

</details>

---

5. Feature Flag as Code（GitOps）の利点は何ですか？
   - A) Flag は GUI でのみ管理できる
   - B) Git PR を通じて管理される Flag の変更により、レビュー、監査、ロールバックが可能になる
   - C) Flag の評価が高速になる
   - D) サーバーリソースを節約できる

<details>
<summary>回答を表示</summary>

**回答: B) Git PR を通じて管理される Flag の変更により、レビュー、監査、ロールバックが可能になる**

**解説:**
FeatureFlag CR を Git で管理すると、PR レビュー、変更履歴の確認、Git revert による復元ができます。利用側では、ArgoCD/Flux による反映、ソースの同期、SDK 内の状態更新も必要です。Self-healing によって緊急の手動変更が取り消されることもあるため、変更の所有者と反映方法を合わせて管理してください。

</details>

---

6. Feature Flag による技術的負債を防ぐためのベストプラクティスは何ですか？
   - A) すべての Flag を永続的に保持する
   - B) Flag に有効期限を設定し、リリース完了後に Flag のコードをクリーンアップする
   - C) 数を制限せずに自由に Flag を作成する
   - D) Flag 名に日付を含めない

<details>
<summary>回答を表示</summary>

**回答: B) Flag に有効期限を設定し、リリース完了後に Flag のコードをクリーンアップする**

**解説:**
担当者と見直し日を記録し、コードや設定を削除する前に、古いバージョンのアプリケーションやほかの利用者がそのフラグを使っていないか確認してください。有効期限のメタデータを付けても、フラグが自動的に削除されるわけではありません。運用上必要なフラグは削除するのではなく、定期的に見直す場合があります。

</details>

---

7. Kubernetes 上で OpenFeature Operator が提供する中核機能は何ですか？
   - A) flagd Sidecar を Pod に自動注入し、FeatureFlag CRD を管理する
   - B) Kubernetes クラスターのセキュリティを監査する
   - C) コンテナイメージを自動的にビルドする
   - D) HPA を自動的に設定する

<details>
<summary>回答を表示</summary>

**回答: A) flagd Sidecar を Pod に自動注入し、FeatureFlag CRD を管理する**

**解説:**
Operator は `FeatureFlag` と `FeatureFlagSource` などのリソースを管理します。Pod への注入には `openfeature.dev/enabled` と `openfeature.dev/featureflagsource` のアノテーションを使います。ファイルソース用 ConfigMap のボリューム、Kubernetes への直接アクセス、プロキシソースでは、それぞれ同期方法が異なります。アプリケーション側では別途 SDK の組み込みが必要です。

</details>

---

8. Flagger + Feature Flag の組み合わせにおいて、メトリクスベースの自動ロールアウトはどのように機能しますか？
   - A) Feature Flag がトラフィックを直接制御する
   - B) Flagger が Canary トラフィックのシフトを処理し、Feature Flag がアプリケーションレベルでの段階的な機能公開を制御する
   - C) Feature Flag が Flagger を完全に置き換える
   - D) 両方のツールが同一のメトリクスを使用する

<details>
<summary>回答を表示</summary>

**回答: B) Flagger が Canary トラフィックのシフトを処理し、Feature Flag がアプリケーションレベルでの段階的な機能公開を制御する**

**解説:**
Flagger はワークロードのリリースとトラフィックを制御し、Feature Flag はアプリケーションの動作を制御します。両者を組み合わせても、変更が自動的に一つのトランザクションになるわけではありません。フラグ変更とロールバックを連携するには、実際に動作する webhook または Git 自動化に加え、認可と失敗時の処理が必要です。Canary のトラフィック比率とユーザー群に対する公開率は、対象とする母集団が異なります。

</details>
