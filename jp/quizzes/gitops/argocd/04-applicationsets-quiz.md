# ArgoCD ApplicationSets クイズ

このクイズでは、テンプレート化されたApplication生成のためのArgoCD ApplicationSetsについての理解度を確認します。

1. ApplicationSetの主な目的は何ですか？
   - A) 既存のApplicationsをグループ化する
   - B) テンプレートから複数のApplicationsを自動的に生成する
   - C) applicationのバックアップを作成する
   - D) applicationのシークレットを管理する

<details>
<summary>回答を表示</summary>

**回答: B) テンプレートから複数のApplicationsを自動的に生成する**

**解説:**
ApplicationSetsは、ジェネレーターとテンプレートを使用して複数のArgoCD Applicationsを自動的に作成・管理します。複数のクラスターまたは環境にapplicationsをデプロイする場合に最適です。

</details>

2. ArgoCDに登録されている各クラスター用のApplicationsを作成するには、どのジェネレーターを使用しますか？
   - A) Git generator
   - B) List generator
   - C) Cluster generator
   - D) Matrix generator

<details>
<summary>回答を表示</summary>

**回答: C) Cluster generator**

**解説:**
Cluster generatorは、ArgoCDに登録されている各クラスター用のApplicationsを自動的に生成します。ラベルセレクターを使用して特定のクラスターを対象にできます。

</details>

3. Git directory generatorは何をしますか？
   - A) Gitブランチに基づいてApplicationsを作成する
   - B) 指定されたパス内のディレクトリごとにApplicationsを作成する
   - C) Git認証情報を同期する
   - D) Git webhookを管理する

<details>
<summary>回答を表示</summary>

**回答: B) 指定されたパス内のディレクトリごとにApplicationsを作成する**

**解説:**
Git directory generatorは、Gitリポジトリ内の指定したディレクトリをスキャンし、設定された glob と除外ルールに一致する各ディレクトリに対してApplicationを作成します。これはmonorepo構成で役立ちます。

</details>

4. ApplicationSetで複数のジェネレーターを組み合わせるにはどうしますか？
   - A) Merge generatorを使用する
   - B) Matrix generatorを使用する
   - C) Combine generatorを使用する
   - D) AとBの両方

<details>
<summary>回答を表示</summary>

**回答: D) AとBの両方**

**解説:**
Matrix generatorは、2つの子ジェネレーターからのパラメータの組み合わせ（デカルト積）を作成します。Merge generatorは、複数のジェネレーターからのパラメータを組み合わせ、一致するエントリをマージします。どちらもジェネレーターの組み合わせに使用できます。

</details>

5. ApplicationSetテンプレートの`goTemplate`フィールドの目的は何ですか？
   - A) Goプログラミングを有効にする
   - B) より複雑なテンプレート処理のためにGo template構文を使用する
   - C) Go applicationsをコンパイルする
   - D) デバッグを有効にする

<details>
<summary>回答を表示</summary>

**回答: B) より複雑なテンプレート処理のためにGo template構文を使用する**

**解説:**
`goTemplate: true`を設定するとGo template構文が有効になり、デフォルトの単純な変数置換と比較して、条件分岐、ループ、関数など、より強力なテンプレート機能を利用できます。
各文字列フィールドは個別に評価されます。制御文を複数の YAML フィールドにまたがって記述することはできません。また、ブール値やオブジェクトのフィールドを直接テンプレート化することもできません。

</details>

6. pull requestに基づいてApplicationsを作成するには、どのジェネレーターを使用しますか？
   - A) Git generator
   - B) Pull Request generator
   - C) SCM Provider generator
   - D) Webhook generator

<details>
<summary>回答を表示</summary>

**回答: B) Pull Request generator**

**解説:**
Pull Request generatorは、リポジトリ内のオープンなpull requestごとにApplicationsを作成し、コードレビュー用のプレビュー環境を有効にします。GitHub、GitLab、Bitbucket、Giteaをサポートしています。

</details>

7. ApplicationSetを削除すると、デフォルトではどうなりますか？
   - A) 何も起こらず、生成されたApplicationsは残る
   - B) 生成されたすべてのApplicationsが削除される
   - C) Applicationsが孤立する
   - D) バックアップが作成される

<details>
<summary>回答を表示</summary>

**回答: B) 生成されたすべてのApplicationsが削除される**

**解説:**
デフォルトでは、ApplicationSets の削除ポリシーはカスケード削除です。ApplicationSet を削除すると、生成されたすべての Application も削除されます。`preserveResourcesOnDeletion` が制御するのはデプロイ済みリソースのクリーンアップであり、Application オブジェクトがガベージコレクションされるかどうかではありません。

</details>

8. ApplicationSetが削除されたときに、生成されたApplicationsが削除されないようにするにはどうしますか？
   - A) `kubectl delete applicationset NAME --cascade=orphan` で削除する
   - B) `syncPolicy.preserveResourcesOnDeletion: true` だけを設定する
   - C) 削除ポリシーの annotation を設定する
   - D) ApplicationSet controller のレプリカ数を 0 にする

<details>
<summary>回答を表示</summary>

**回答: A) `kubectl delete applicationset NAME --cascade=orphan` で削除する**

**解説:**
`--cascade=orphan` を指定すると、親の ApplicationSet を削除した後も生成された Application オブジェクトが残ります。`preserveResourcesOnDeletion: true` は、デプロイ済みリソースを削除する finalizer の追加を防ぎますが、Application オブジェクトのガベージコレクションを防ぐものではありません。finalizer が残った orphan Application を後から削除すると、そのリソースが削除される場合があります。

</details>
