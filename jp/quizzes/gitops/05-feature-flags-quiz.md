# Feature Flags と OpenFeature クイズ

1. OpenFeature の Provider モデルの主な利点は何ですか？
   - A) ベンダーロックインにより最適なパフォーマンスが得られる
   - B) ベンダー中立の API により、Feature Flag バックエンドを自由に切り替えられる
   - C) 独自の Feature Flag サーバーを実行する必要がある
   - D) REST API のみをサポートする

<details>
<summary>回答を表示</summary>

**回答: B) ベンダー中立の API により、Feature Flag バックエンドを自由に切り替えられる**

**解説:**
OpenFeature は、ベンダー中立の SDK API を提供する CNCF 標準です。Provider インターフェースを通じて、Provider 設定を変更するだけで、アプリケーションコードを変更せずに、flagd、LaunchDarkly、Flagsmith などのバックエンド間を切り替えられます。

</details>

---

2. Kubernetes 上での flagd の Sidecar デプロイモードと Standalone デプロイモードの違いは何ですか？
   - A) Sidecar の方が高性能で、Standalone の方が管理しやすい
   - B) Sidecar は各 Pod に注入されてレイテンシーを最小化し、Standalone は中央サービスとして実行される
   - C) Sidecar は TCP のみをサポートし、Standalone は HTTP のみをサポートする
   - D) Sidecar は CRD を使用し、Standalone は ConfigMap のみを使用する

<details>
<summary>回答を表示</summary>

**回答: B) Sidecar は各 Pod に注入されてレイテンシーを最小化し、Standalone は中央サービスとして実行される**

**解説:**
Sidecar モードでは、OpenFeature Operator が各 Pod に flagd コンテナを注入し、レイテンシーを最小限に抑えたローカル通信を可能にします。Standalone モードでは、flagd は中央で管理される独立した Deployment として実行されます。リソース効率は高くなりますが、ネットワーク呼び出しが必要です。

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
Evaluation Context は、Flag 評価時に動的に渡されるメタデータです。ユーザー ID、リージョン、環境（dev/staging/prod）、ユーザーグループなどの情報が含まれます。ターゲティングルールはこの情報を使用して、特定のユーザーまたはグループに対して機能を有効にします。

</details>

---

4. Dark Launch パターンにおける Feature Flag の役割は何ですか？
   - A) サービスを完全に隠し、アクセスをブロックする
   - B) 新機能のコードをデプロイするが、ユーザーに表示されないよう Flag で無効化する
   - C) サーバーをダークモードに切り替える
   - D) 夜間にのみデプロイを実行する

<details>
<summary>回答を表示</summary>

**回答: B) 新機能のコードをデプロイするが、ユーザーに表示されないよう Flag で無効化する**

**解説:**
Dark Launch では、新機能のコードを本番環境にデプロイしますが、Feature Flag によってユーザーには表示されない状態に保ちます。その後、テストのために一部のユーザーに対して Flag を段階的に有効化し、問題がなければすべてのユーザーに展開します。これはデプロイとリリースを分離するための重要なパターンです。

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
Feature Flag as Code では、Git リポジトリ内の FeatureFlag CR を管理し、PR ベースのレビューおよび承認プロセスを適用します。変更履歴は監査のために Git に記録され、問題が発生した場合は Git revert により迅速にロールバックできます。ArgoCD または Flux が変更を自動的に同期します。

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
Feature Flag は一時的なリリースツールとして使用されることがよくあります。リリース完了後は、技術的負債の蓄積を防ぐため、Flag と関連する条件付きコードをクリーンアップする必要があります。Flag に有効期限とオーナーをタグ付けし、未使用の Flag を定期的に検出して削除するプロセスを運用します。

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
OpenFeature Operator は、Kubernetes で Feature Flag をネイティブに管理するための Operator です。FeatureFlag CRD を通じて Flag を宣言的に管理し、FeatureFlagSource CRD を通じて Flag のソースを定義し、適切なアノテーションを持つ Pod に flagd Sidecar コンテナを自動注入します。

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
Flagger と Feature Flag は異なるレベルで動作します。Flagger はインフラストラクチャレベルでトラフィックを分割し、メトリクスを分析してデプロイを制御します。Feature Flag はアプリケーションレベルで個々の機能の有効化／無効化を制御します。これらを併用することで、デプロイ（Flagger）とリリース（Feature Flag）を完全に分離できます。

</details>
