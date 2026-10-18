# Amazon ECRクイズ
> **最終更新日**: 2026年9月11日

1. Amazon ECR PrivateとAmazon ECR Publicの主な違いは何ですか？
   - A) ECR Privateは無料でECR Publicは有料
   - B) ECR Privateではすべての操作で認証が必要だが、ECR Publicでは匿名でpullできる
   - C) ECR PrivateはDockerイメージだけをサポートし、ECR Publicはすべての形式をサポートする
   - D) ECR Privateはリージョン別で、ECR Publicはus-east-1でしか利用できない

<details>
<summary>回答を表示</summary>

**回答: B) ECR Privateではすべての操作で認証が必要だが、ECR Publicでは匿名でpullできる**

**解説:**
Privateのpush/pull操作には認証が必要です。Publicのイメージは匿名でpullできますが、公開や管理には認証が必要です。Public APIエンドポイントはus-east-1とus-west-2にあり、イメージはグローバルURLを通じて配布されます。

</details>

2. `docker login --password-stdin`で使うECRパスワードを直接出力するCLIコマンドはどれですか？
   - A) `aws ecr get-authorization-token`
   - B) `aws ecr get-login-password`
   - C) `aws ecr login`
   - D) `aws ecr authenticate`

<details>
<summary>回答を表示</summary>

**回答: B) `aws ecr get-login-password`**

**解説:**
`get-login-password`は、標準入力へ渡せるパスワードを出力します。`get-authorization-token`も有効なAPI/CLI操作ですが、デコードが必要なエンコード済みの認証トークンを返します。

</details>

3. ECRライフサイクルポリシーでは、複数のルールが同じイメージに一致する場合、どのルールを適用するかは何で決まりますか？
   - A) `rulePriority`の数値が最も小さいルールが優先される
   - B) `rulePriority`の数値が最も大きいルールが優先される
   - C) ルールがアルファベット順に適用される
   - D) 一致するすべてのルールが同時に適用される

<details>
<summary>回答を表示</summary>

**回答: A) `rulePriority`の数値が最も小さいルールが優先される**

**解説:**
まずすべてのルールが評価され、その後に優先度に従って結果が適用されます。数値が小さいほど優先度が高くなります。優先度の高いルールのタグ要件に一致するイメージは、優先度の低いルールでは期限切れにできません。ルールそのものを順番に評価して短絡する方式ではありません。

</details>

4. ECRライフサイクルポリシーの`tagPatternList`では、どのパターン構文を使いますか？
   - A) 正規表現（regex）
   - B) ドキュメントに記載された`*`ワイルドカードパターン
   - C) SQL LIKEパターン
   - D) 完全一致する文字列のみ

<details>
<summary>回答を表示</summary>

**回答: B) ドキュメントに記載された`*`ワイルドカードパターン**

**解説:**
ドキュメントに記載された`*`ワイルドカードを使います。1つの文字列につき星印は最大4つです。正規表現、文字クラス、Unix globの完全な動作を想定してはいけません。`v*`は接頭辞を選択します。CI側でリリースのバージョン形式を検証してください。

</details>

5. ECRライフサイクルポリシーのルールロジックに関する主な制限は何ですか？
   - A) ルールを5個以上作れない
   - B) 1つのルール内でタグパターンを対象とするOR/和集合の条件を表せない
   - C) タグなしイメージを削除できない
   - D) `imageCountMoreThan`でcountTypeを使えない

<details>
<summary>回答を表示</summary>

**回答: B) 1つのルール内でタグパターンを対象とするOR/和集合の条件を表せない**

**解説:**
`tagPatternList`に複数のパターンを指定した1つのECRライフサイクルルールはAND条件です（イメージがすべてのパターンに一致する必要があります）。OR条件（いずれかのパターンに一致）にするには、パターンごとに別のルールを作成します。異なるタグパターンのイメージに同じ保持ポリシーを適用する場合は、この制限を踏まえてルールを設計してください。

</details>

6. ECRで環境ごとに別リポジトリを作る方法（Strategy A）の主な利点は何ですか？
   - A) 各リポジトリで保持要件が揃うため、ライフサイクルポリシーがシンプルになる
   - B) ストレージコストが下がる
   - C) イメージのpullが速くなる
   - D) クロスリージョンレプリケーションが自動的に行われる

<details>
<summary>回答を表示</summary>

**回答: A) 各リポジトリで保持要件が揃うため、ライフサイクルポリシーがシンプルになる**

**解説:**
Strategy Aでは、環境ごとに別リポジトリを使います（例: `myapp-dev`、`myapp-prod`）。各リポジトリ内のイメージで保持要件が揃うため、ライフサイクルポリシーがシンプルになります。代わりに、複数リポジトリの管理が必要になり、リポジトリ間でイメージが重複する場合があります。

</details>

7. ECRライフサイクルポリシーを定義するTerraformリソースはどれですか？
   - A) `aws_ecr_repository`
   - B) `aws_ecr_lifecycle_policy`
   - C) `aws_ecr_repository_policy`
   - D) `aws_ecr_retention_policy`

<details>
<summary>回答を表示</summary>

**回答: B) `aws_ecr_lifecycle_policy`**

**解説:**
Terraformの`aws_ecr_lifecycle_policy`リソースを使って、ECRリポジトリにライフサイクルポリシーを適用します。リポジトリ名の`repository`と、ライフサイクルルールを定義する`policy` JSONドキュメントが必要です。`aws_ecr_repository_policy`は別のリソースで、リポジトリへのアクセスを制御するIAMリソースベースポリシーに使います。

</details>

8. EC2ベースのEKSノードでECRイメージをpullする場合、通常、最初の権限を提供するIDは何ですか？
   - A) Secretに保存した静的アクセスキー
   - B) kubeletがノードのIAMロールを直接使う
   - C) PodがOIDCフェデレーション経由でIAMロールを引き受け、一時的な認証情報を使う
   - D) ECRトークンをConfigMapに事前設定する

<details>
<summary>回答を表示</summary>

**回答: B) kubeletがノードのIAMロールを直接使う**

**解説:**
kubeletはアプリケーションが起動する前に、ノードのイメージpull用認証情報を使ってイメージを取得します。FargateではPod execution roleを使います。IRSA/Pod IdentityはPod起動後のワークロードSDK用の認証情報を提供するものであり、初期のイメージpullに使うIDの代わりにはなりません。

</details>

9. ECRリポジトリでimmutable tagを有効にすると、何を防止できますか？
   - A) リポジトリ内のすべてのイメージの削除
   - B) 既存イメージと同じタグを使った新しいイメージのpush
   - C) 認証なしでのイメージpull
   - D) ライフサイクルポリシーの作成

<details>
<summary>回答を表示</summary>

**回答: B) 既存イメージと同じタグを使った新しいイメージのpush**

**解説:**
immutable tagでは、既存イメージのタグを上書きできません。特定のタグでイメージをpushすると、そのタグを別のイメージダイジェストに再利用できなくなります。これによってデプロイ時のタグの安定性が高まり、意図しない、または悪意のあるイメージ置き換えを防ぎます。イメージの削除や、新しい一意なタグを使ったpushは引き続き可能です。

</details>

10. ECRのクロスリージョンレプリケーションに関する正しい説明はどれですか？
    - A) イメージマニフェストだけが複製される
    - B) 対象となるイメージとタグが非同期で複製される。宛先の設定は別に管理する
    - C) ライフサイクルポリシーとアクセス許可を含むすべてが複製される
    - D) 既存のイメージはすべて自動的にバックフィルされる

<details>
<summary>回答を表示</summary>

**回答: B) 対象となるイメージとタグが非同期で複製される。宛先の設定は別に管理する**

**解説:**
レプリケーションの設定後にpushまたは復元されたイメージが対象になります。既存のコンテンツは自動的にバックフィルされません。宛先リポジトリの設定、権限、ライフサイクルポリシーは、たとえばcreation templateを使って個別に設定します。復旧にレプリケーションを使う場合は、必要な宛先ダイジェストを確認してください。

</details>
