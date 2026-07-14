# ArgoCD Applications クイズ

このクイズでは、ArgoCD Applications とその設定についての理解度を確認します。

1. ArgoCD Application リソースの主な目的は何ですか？
   - A) ユーザーのアクセス制御を定義する
   - B) アプリケーションの望ましい状態と同期設定を指定する
   - C) 通知を設定する
   - D) シークレットを管理する

<details>
<summary>回答を表示</summary>

**回答: B) アプリケーションの望ましい状態と同期設定を指定する**

**解説:**
ArgoCD Application は、アプリケーションのソース（Git リポジトリ、パス、リビジョン）とデプロイ先（クラスター、namespace）を、同期ポリシーおよびヘルスチェックとともに定義する Kubernetes カスタムリソースです。

</details>

2. Application spec で、マニフェストのデプロイ先を定義するフィールドはどれですか？
   - A) source
   - B) target
   - C) destination
   - D) cluster

<details>
<summary>回答を表示</summary>

**回答: C) destination**

**解説:**
`destination` フィールドは、アプリケーションのリソースをデプロイするターゲットクラスター（server URL または名前で指定）と namespace を指定します。

</details>

3. Application の `spec.source.path` フィールドは何を指定しますか？
   - A) ArgoCD インストールへのパス
   - B) マニフェストを含む Git リポジトリ内のディレクトリ
   - C) ローカルファイルシステムのパス
   - D) API server のパス

<details>
<summary>回答を表示</summary>

**回答: B) マニフェストを含む Git リポジトリ内のディレクトリ**

**解説:**
`source` 配下の `path` フィールドは、Kubernetes マニフェスト、Helm chart、または Kustomize 設定を含む Git リポジトリ内のディレクトリを指定します。

</details>

4. まだ存在しない特定の namespace にアプリケーションをデプロイするには、どうすればよいですか？
   - A) まず namespace を手動で作成する
   - B) CreateNamespace=true を指定して syncPolicy.syncOptions を使用する
   - C) 不可能である
   - D) pre-sync hook を使用する

<details>
<summary>回答を表示</summary>

**回答: B) CreateNamespace=true を指定して syncPolicy.syncOptions を使用する**

**解説:**
`syncPolicy.syncOptions` で `CreateNamespace=true` を設定すると、アプリケーションリソースを同期する前に、ターゲット namespace が存在しない場合は ArgoCD が自動的に作成します。

</details>

5. `targetRevision: HEAD` と `targetRevision: main` の違いは何ですか？
   - A) 違いはない
   - B) HEAD は常にデフォルトブランチを指し、main は明示的に指定する
   - C) HEAD の方が高速である
   - D) main は webhook をサポートするが、HEAD はサポートしない

<details>
<summary>回答を表示</summary>

**回答: B) HEAD は常にデフォルトブランチを指し、main は明示的に指定する**

**解説:**
`HEAD` はリポジトリのデフォルトブランチを指すシンボリック参照である一方、`main` は main ブランチを明示的に指定します。デフォルトブランチが変更される場合、`HEAD` を使用する方が柔軟です。

</details>

6. Helm リポジトリ（Git ではない）から Helm chart をデプロイするには、どのソースタイプを使用しますか？
   - A) git
   - B) helm
   - C) directory
   - D) kustomize

<details>
<summary>回答を表示</summary>

**回答: B) helm**

**解説:**
Helm リポジトリからデプロイする場合は、Helm リポジトリを指すように `source.chart` と `source.repoURL` を設定します。すると ArgoCD は Git ソースではなく Helm ソースとして扱います。

</details>

7. `spec.source.helm.releaseName` を設定するとどうなりますか？
   - A) 新しい Helm リポジトリを作成する
   - B) デフォルトのリリース名（Application 名）を上書きする
   - C) Helm hook を有効にする
   - D) chart バージョンを設定する

<details>
<summary>回答を表示</summary>

**回答: B) デフォルトのリリース名（Application 名）を上書きする**

**解説:**
デフォルトでは、ArgoCD は Application 名を Helm リリース名として使用します。`releaseName` を明示的に設定すると、Helm リリースに別の名前を使用できます。

</details>

8. ArgoCD Application で Helm values を指定するにはどうしますか？
   - A) リポジトリ内の values ファイルのみを使用する
   - B) Application spec 内でのみインライン指定する
   - C) values ファイルとインライン values の両方を使用する
   - D) values は ConfigMap に保存する必要がある

<details>
<summary>回答を表示</summary>

**回答: C) values ファイルとインライン values の両方を使用する**

**解説:**
ArgoCD では、`spec.source.helm.valueFiles`（リポジトリ内のファイルを参照）および／または `spec.source.helm.values`（インライン YAML）を通じて Helm values を指定できます。両方を併用でき、インライン values が優先されます。

</details>
