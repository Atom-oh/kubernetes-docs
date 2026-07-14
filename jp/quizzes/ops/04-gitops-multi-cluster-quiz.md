# GitOps Multi-Cluster クイズ

> **関連ドキュメント**: [GitOps Multi-Cluster](../../ops/04-gitops-multi-cluster.md)

## 選択問題

### 1. multi-cluster GitOps における hub-spoke model (ハブ＆スポークモデル) とは何ですか？

- A) network topology のパターン
- B) central management cluster が複数の workload cluster を制御するモデル
- C) data replication 戦略
- D) load balancing アルゴリズム

<details>
<summary>回答を表示</summary>

**回答: B) central management cluster が複数の workload cluster を制御するモデル**

**解説:**
hub-spoke model では、中央の「hub」cluster が ArgoCD を実行し、複数の「spoke」workload cluster への deployment を管理します。これにより、workload を cluster 間で分離したまま、GitOps operations を一元化できます。

</details>

### 2. ArgoCD はどのように High Availability (HA) を実現しますか？

- A) auto-restart 付きの単一 replica を実行する
- B) leader election を使用して各 component の複数 replica を実行する
- C) 外部 database replication を使用する
- D) 複数 region にまたがって deploy する

<details>
<summary>回答を表示</summary>

**回答: B) leader election を使用して各 component の複数 replica を実行する**

**解説:**
ArgoCD HA は、application-controller、repo-server、server component の複数 replica を deploy します。application-controller は leader election を使用して、各 application を処理する instance が 1 つだけになるようにし、他の instance は待機します。

</details>

### 3. ArgoCD における ApplicationSet とは何ですか？

- A) 手動で作成された Application のグループ
- B) generator に基づいて Application を動的に生成する template
- C) Application configuration の backup
- D) Helm chart の collection

<details>
<summary>回答を表示</summary>

**回答: B) generator に基づいて Application を動的に生成する template**

**解説:**
ApplicationSet は、generator (List、Cluster、Git、Matrix など) を使用して、単一の template から複数の ArgoCD Application を自動的に作成および管理する controller です。これにより、スケーラブルな multi-cluster および multi-environment deployment が可能になります。

</details>

### 4. 登録済み cluster secret に基づいて Application を作成する ApplicationSet generator はどれですか？

- A) List generator
- B) Git generator
- C) Cluster generator
- D) Matrix generator

<details>
<summary>回答を表示</summary>

**回答: C) Cluster generator**

**解説:**
Cluster generator は、ArgoCD に登録されたすべての cluster (secret として保存) を反復処理し、それぞれに対して Application を生成します。これにより、ApplicationSet を変更せずに新しい cluster へ自動 deploy できます。

</details>

### 5. IAM Identity Center (SSO) は ArgoCD とどのように統合できますか？

- A) 直接 database connection
- B) group-based RBAC を使用した SAML または OIDC authentication
- C) SSH key authentication
- D) API key management

<details>
<summary>回答を表示</summary>

**回答: B) group-based RBAC を使用した SAML または OIDC authentication**

**解説:**
ArgoCD は SSO integration のために SAML と OIDC をサポートしています。IAM Identity Center group を ArgoCD RBAC role に map できるため、permission を identity provider 経由で制御する一元的な access management が可能になります。

</details>

### 6. GitOps における External Secrets Operator の目的は何ですか？

- A) git repository を暗号化する
- B) external provider (AWS Secrets Manager) から Kubernetes へ secret を同期する
- C) TLS certificate を rotate する
- D) git access 用の SSH key を管理する

<details>
<summary>回答を表示</summary>

**回答: B) external provider (AWS Secrets Manager) から Kubernetes へ secret を同期する**

**解説:**
External Secrets Operator は、AWS Secrets Manager、HashiCorp Vault、Azure Key Vault などの external secret management system から Kubernetes secret を自動的に作成します。これにより、GitOps workflow を維持しながら、機密 data を git の外に置くことができます。

</details>

### 7. ArgoCD project configuration で `sourceRepos` は何を制限しますか？

- A) deployment の target cluster
- B) application に許可される git repository
- C) Namespace selection
- D) Resource quota

<details>
<summary>回答を表示</summary>

**回答: B) application に許可される git repository**

**解説:**
ArgoCD Project の `sourceRepos` field は、その project 内の Application の source として使用できる git repository を指定します。これにより、未承認の repository access を防止する security boundary が提供されます。

</details>

### 8. ApplicationSet で Matrix generator を使用する利点は何ですか？

- A) 数学的計算を実行する
- B) 複数の generator を組み合わせて parameter の Cartesian product を作成する
- C) application manifest を暗号化する
- D) YAML syntax を検証する

<details>
<summary>回答を表示</summary>

**回答: B) 複数の generator を組み合わせて parameter の Cartesian product を作成する**

**解説:**
Matrix generator は 2 つ以上の generator を組み合わせ、それらの output のすべての組み合わせに対して Application を作成します。たとえば、Cluster generator と List generator を組み合わせると、複数の service を複数の cluster に deploy できます。

</details>

### 9. GitOps を通じて NodePools を管理する場合、重要な考慮事項は何ですか？

- A) NodePools は GitOps 経由では管理できない
- B) 実行中の workload を中断しないよう、変更は段階的に行うべきである
- C) NodePools は ArgoCD と同じ namespace に存在する必要がある
- D) Spot instance のみ管理できる

<details>
<summary>回答を表示</summary>

**回答: B) 実行中の workload を中断しないよう、変更は段階的に行うべきである**

**解説:**
GitOps を通じた NodePool の変更は、node replacement を引き起こす可能性があるため、慎重に管理する必要があります。Progressive Sync や node management 用の個別 Application などの戦略を使用すると、中断を避けるのに役立ちます。

</details>

### 10. remote cluster を ArgoCD に追加する推奨方法は何ですか？

- A) ArgoCD ConfigMap を直接編集する
- B) `argocd cluster add` を使用する、または credential を含む cluster Secret を作成する
- C) 各 cluster に ArgoCD を install する
- D) kubectl port-forward を使用する

<details>
<summary>回答を表示</summary>

**回答: B) `argocd cluster add` を使用する、または credential を含む cluster Secret を作成する**

**解説:**
remote cluster は、`argocd cluster add` CLI command を使用するか、cluster の API server URL と credential を含む Secret を作成することで追加します。ArgoCD はこれらの credential を使用して、application を remote cluster に deploy および同期します。

</details>
