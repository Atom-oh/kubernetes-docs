# GitOps 自動化クイズ

> **関連ドキュメント**: [GitOps 自動化](../../ops/05-gitops-automation.md)

## 選択問題

### 1. Terraform 自動化における Atlantis とは何ですか？

- A) クラウドプロバイダー
- B) Terraform の pull request 自動化ツール
- C) Terraform モジュールレジストリ
- D) state ファイルの暗号化サービス

<details>
<summary>解答を表示</summary>

**解答: B) Terraform の pull request 自動化ツール**

**解説:**
Atlantis は、Terraform の pull request を監視し、`terraform plan` と `apply` を自動実行するセルフホスト型アプリケーションです。plan の結果を PR コメントに表示し、変更の適用前に承認ワークフローを適用します。

</details>

### 2. セルフホスト型 Terraform と比べた HCP Terraform の主な利点は何ですか？

- A) 無料で無制限に使える
- B) state、実行、コラボレーション機能がマネージドで提供される
- C) 実行速度が速い
- D) 対応プロバイダーが多い

<details>
<summary>解答を表示</summary>

**解答: B) state、実行、コラボレーション機能がマネージドで提供される**

**解説:**
HCP Terraform は、リモート state のストレージ、run の実行、チームでのコラボレーション、ポリシー適用（Sentinel）、プライベートモジュールレジストリをマネージド機能として提供します。これにより、セルフホスト構成と比べて運用負荷を軽減できます。

</details>

### 3. アーキテクチャの点で、FluxCD は Argo CD とどう異なりますか？

- A) FluxCD には UI がない
- B) どちらもリコンシリエーションを行うが、API、コントローラー、UI の選択肢が異なる
- C) FluxCD は Helm だけをサポートする
- D) FluxCD にはデータベースが必要である

<details>
<summary>解答を表示</summary>

**解答: B) どちらもリコンシリエーションを行うが、API、コントローラー、UI の選択肢が異なる**

**解説:**
Flux は `GitRepository`、`Kustomization` など、コントローラー固有の API を使います。Argo CD にも複数のコンポーネントがあり、異なるデプロイトポロジーを選べます。リソース使用量やマルチクラスター時の動作は構成によって異なり、どちらかが常に優れているとは言えません。

</details>

### 4. Flux Image Automation Controller は何をしますか？

- A) コンテナイメージをビルドする
- B) レジストリを調べ、新しいイメージタグを Git に反映する
- C) イメージを Kubernetes にデプロイする
- D) イメージ pull 用の Secret を管理する

<details>
<summary>解答を表示</summary>

**解答: B) レジストリを調べ、新しいイメージタグを Git に反映する**

**解説:**
`image-reflector-controller` はレジストリを調べ、`ImagePolicy` を評価します。別の `image-automation-controller` がその選択結果を、指定されたファイルに反映して Git にコミットします。新しいイメージが push されたときにデプロイまで自動化でき、GitOps の原則も維持できます。

</details>

### 5. 通常の Atlantis ワークフローで、apply と merge はどの順序で行いますか？

- A) どの PR も merge すれば必ず Terraform が自動適用される
- B) PR の plan を確認し、必要条件を満たして保存済み plan を明示的に適用してから merge する
- C) 保存済み plan を無視して、先に merge する
- D) plan が成功すれば、それだけで apply も完了している

<details>
<summary>解答を表示</summary>

**解答: B) PR の plan を確認し、必要条件を満たして保存済み plan を明示的に適用してから merge する**

**解説:** Atlantis は PR のワークフローから apply を実行します。merge だけで apply が始まるわけではありません。任意の automerge は、apply 成功後に merge します。コミットが変わった場合は内容を確認して再度 plan を実行し、PR からサーバー側で強制される要件を上書きしないでください。

</details>

### 6. GitOps ワークフローにおける AIOps の主な利点は何ですか？

- A) Git が不要になる
- B) 異常を自動検知し、対応方法を推奨する
- C) コンテナのビルドが速くなる
- D) ストレージコストが下がる

<details>
<summary>解答を表示</summary>

**解答: B) 異常を自動検知し、対応方法を推奨する**

**解説:**
AIOps は機械学習を使って、メトリクスやログから異常を検出し、イベントを関連付け、対応を推奨または自動化します。GitOps では、スケーリング変更やトラフィック比率の調整を提案する PR の自動作成などに利用できます。

</details>

### 7. AIOps は blue/green デプロイのトラフィック比率変更をどのように自動化できますか？

- A) ロードバランサーの設定を直接変更する
- B) 異常を検出し、Git 内の比率設定を更新する PR を作成する
- C) 失敗した Pod を再起動する
- D) DNS レコードを変更する

<details>
<summary>解答を表示</summary>

**解答: B) 異常を検出し、Git 内の比率設定を更新する PR を作成する**

**解説:**
AIOps はメトリクスを監視して、green 側のデプロイにおけるエラー率やレイテンシーの問題を検出し、トラフィック比率を blue に戻す PR を自動作成できます。ただし、提案を実行する前に、データ品質の確認、権限を持つ担当者の承認、現在の状態・キャパシティ・転送先の健全性を再確認する制約付きの実行機構が必要です。異常の検出や PR の作成だけでは、トラフィック変更の実行許可にはなりません。

</details>

### 8. Flux の `GitRepository` リソースは何のために使いますか？

- A) Git リポジトリを作成する
- B) Flux が変更を監視する Git ソースを定義する
- C) Kubernetes リソースを Git にバックアップする
- D) Git 認証情報を管理する

<details>
<summary>解答を表示</summary>

**解答: B) Flux が変更を監視する Git ソースを定義する**

**解説:**
`GitRepository` は Flux のカスタムリソースです。Git リポジトリの URL、ブランチ、ポーリング間隔を指定します。Flux コントローラーはこのソースを監視し、変更を検知するとリコンシリエーションを開始します。

</details>

### 9. マルチテナンシーについて、正しい説明はどれですか？

- A) Argo CD には AppProject があるため、常により安全である
- B) Flux では namespace を分けるだけでテナント分離が完了する
- C) どちらもソース、ID、RBAC、リソース境界を意図的に構成する必要がある
- D) イメージ自動化機能は脆弱性スキャンも行う

<details>
<summary>解答を表示</summary>

**解答: C) どちらもソース、ID、RBAC、リソース境界を意図的に構成する必要がある**

**解説:**
AppProject と Flux のテナント ID は、リコンシリエーションの異なる部分を制約します。どちらも、ネットワーク境界、Kubernetes の認可、信頼できないコードの分離を自動的にすべて提供するわけではありません。同じリソースのフィールドを複数のコントローラーに管理させないようにしてください。

</details>

### 10. HCP Terraform の Sentinel ポリシーとは何ですか？

- A) バックアップ戦略
- B) ガバナンスとコンプライアンスのための Policy as Code フレームワーク
- C) state の暗号化方式
- D) モジュールのバージョン管理方式

<details>
<summary>解答を表示</summary>

**解答: B) ガバナンスとコンプライアンスのための Policy as Code フレームワーク**

**解説:**
Sentinel は HashiCorp の Policy as Code フレームワークで、Terraform が変更を適用する前にルールを強制します。タグ、インスタンスタイプ、暗号化など、モデル化された要件を検査できます。実際の効果は、ポリシーセットの適用範囲や強制レベル、値が欠落または不明な場合の扱いによって異なります。ここでの例だけで、すべてのリソースが検査されるとは限りません。

</details>
