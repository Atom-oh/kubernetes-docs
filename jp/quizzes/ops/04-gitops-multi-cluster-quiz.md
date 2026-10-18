# GitOps マルチクラスタークイズ

> **関連ドキュメント**: [GitOps マルチクラスター](../../ops/04-gitops-multi-cluster.md)

## 選択問題

### 1. マルチクラスター GitOps におけるハブ・スポークモデルとは何ですか？

- A) ネットワークトポロジーのパターン
- B) 中央の管理クラスターが複数のワークロードクラスターを管理するモデル
- C) データレプリケーション方式
- D) ロードバランシングアルゴリズム

<details>
<summary>解答を表示</summary>

**解答: B) 中央の管理クラスターが複数のワークロードクラスターを管理するモデル**

ハブ・スポークモデルでは、中央の「ハブ」クラスターで Argo CD を動かし、複数の「スポーク」ワークロードクラスターへのデプロイを管理します。GitOps 運用を一元化しながら、各クラスターのワークロードは分離できます。

</details>

### 2. Argo CD はどのように高可用性（HA）を実現しますか？

- A) 自動再起動を設定してレプリカを 1 つだけ動かす
- B) コンポーネントごとのレプリカ構成、コントローラーのシャーディング、障害に強い配置を組み合わせる
- C) 外部データベースのレプリケーションを使う
- D) 複数リージョンにデプロイする

<details>
<summary>解答を表示</summary>

**解答: B) コンポーネントごとのレプリカ構成、コントローラーのシャーディング、障害に強い配置を組み合わせる**

Application Controller は対象クラスターをシャーディングし、他のレプリカをすべて待機状態にするわけではありません。ApplicationSet は別のリーダー選出を使い、Server はステートレスです。Redis HA、配置、キャパシティ、PDB はそれぞれ異なる障害に対処します。レプリカを増やすだけで可用性が保証されるわけではありません。

</details>

### 3. Argo CD の ApplicationSet とは何ですか？

- A) 手動で作成した Application のグループ
- B) generator に基づいて Application を動的に生成するテンプレート
- C) Application 設定のバックアップ
- D) Helm chart のコレクション

<details>
<summary>解答を表示</summary>

**解答: B) generator に基づいて Application を動的に生成するテンプレート**

ApplicationSet は List、Cluster、Git、Matrix などの generator を使い、1 つのテンプレートから複数の Argo CD Application を自動作成・管理するコントローラーです。マルチクラスターや複数環境へのデプロイを拡張しやすくします。

</details>

### 4. 登録済みクラスターの Secret に基づいて Application を作成する ApplicationSet generator はどれですか？

- A) List generator
- B) Git generator
- C) Cluster generator
- D) Matrix generator

<details>
<summary>解答を表示</summary>

**解答: C) Cluster generator**

Cluster generator は、構成した selector で登録済みクラスターを選び、そのメタデータを渡します。既定のローカルクラスターには Secret がない場合があるため、Secret のラベルによる選択では除外されることがあります。新しいクラスターも、登録内容とラベルが selector に一致した場合にだけ選ばれます。

</details>

### 5. IAM Identity Center（SSO）を Argo CD と統合するにはどうしますか？

- A) データベースに直接接続する
- B) Dex 経由の SAML を使い、検証済み assertion 属性を Argo CD RBAC に割り当てる
- C) SSH 鍵で認証する
- D) API キーを管理する

<details>
<summary>解答を表示</summary>

**解答: B) Dex 経由の SAML を使い、検証済み assertion 属性を Argo CD RBAC に割り当てる**

この章では、文書化された Identity Center SAML と Dex の連携方法を使います。SAML の URL は OIDC issuer ではありません。グループを割り当てただけで groups claim が届くとは限らず、上流ガイドではグループ属性マッピングを回避策として説明しています。最小構成の例では、検証済みのメール ID を明示的にマッピングします。

</details>

### 6. GitOps における External Secrets Operator の目的は何ですか？

- A) Git リポジトリを暗号化する
- B) AWS Secrets Manager などの外部プロバイダーから Kubernetes に Secret を同期する
- C) TLS 証明書をローテーションする
- D) Git アクセス用の SSH 鍵を管理する

<details>
<summary>解答を表示</summary>

**解答: B) AWS Secrets Manager などの外部プロバイダーから Kubernetes に Secret を同期する**

External Secrets Operator は、AWS Secrets Manager、HashiCorp Vault、Azure Key Vault などの外部シークレット管理システムから Kubernetes Secret を自動作成します。機密データを Git の外に置いたまま、GitOps のワークフローを維持できます。

</details>

### 7. Argo CD の Project 設定にある `sourceRepos` は何を制限しますか？

- A) デプロイ先のクラスター
- B) Application のソースとして許可する Git リポジトリ
- C) namespace の選択
- D) リソースクォータ

<details>
<summary>解答を表示</summary>

**解答: B) Application のソースとして許可する Git リポジトリ**

Argo CD Project の `sourceRepos` フィールドは、その Project 内の Application がソースとして使える Git リポジトリを制限します。ただし、リポジトリの認証情報、デプロイ先の RBAC、信頼できないコードのサンドボックスを提供するものではありません。

</details>

### 8. ApplicationSet で Matrix generator を使う利点は何ですか？

- A) 数学的な計算を行う
- B) 2 つの子 generator を組み合わせ、一致するパラメーターの組を生成する
- C) Application manifest を暗号化する
- D) YAML 構文を検証する

<details>
<summary>解答を表示</summary>

**解答: B) 2 つの子 generator を組み合わせ、一致するパラメーターの組を生成する**

Matrix generator の子 generator はちょうど 2 つです。対応するキーと、サポートされるネストの制限に従って、両方の出力パラメーターを組み合わせます。たとえば Cluster generator と List generator を組み合わせると、複数のサービスを複数のクラスターにデプロイできます。

</details>

### 9. GitOps で NodePool を管理するとき、重要な考慮事項は何ですか？

- A) NodePool は GitOps で管理できない
- B) 実行中のワークロードへの影響を避けるため、変更を慎重に進める
- C) NodePool は Argo CD と同じ namespace に置かなければならない
- D) Spot インスタンスだけを管理できる

<details>
<summary>解答を表示</summary>

**解答: B) 実行中のワークロードへの影響を避けるため、変更を慎重に進める**

GitOps 経由の NodePool 変更は、ノード置き換えを引き起こすことがあるため、慎重に管理してください。変更内容、置き換え後のキャパシティ、適用される disruption budget、削除時の動作を確認します。インフラ用 Application を分け、手動で同期する方法は意図しない変更を抑えるのに役立ちますが、どの同期方式でもノード置き換えによる中断がなくなる保証はありません。

</details>

### 10. リモートクラスターを Argo CD に追加する推奨方法は何ですか？

- A) Argo CD ConfigMap を直接編集する
- B) `argocd cluster add` を使うか、認証情報を含むクラスター Secret を作成する
- C) 各クラスターに Argo CD をインストールする
- D) `kubectl port-forward` を使う

<details>
<summary>解答を表示</summary>

**解答: B) `argocd cluster add` を使うか、認証情報を含むクラスター Secret を作成する**

`argocd cluster add` CLI コマンドを使うか、クラスターの API server URL と認証情報を含む Secret を作成して、リモートクラスターを登録します。CLI は接続先の RBAC を変更する場合があります。宣言的な AWS 構成では、ロールの信頼関係、EKS Access Entry／RBAC、実際のエンドポイントと CA 情報、ネットワーク接続が事前に必要です。Secret を作成しただけでは、これらの前提条件は満たされません。

</details>
