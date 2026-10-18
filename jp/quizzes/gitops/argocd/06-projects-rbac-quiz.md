# ArgoCD Project と RBAC クイズ

このクイズでは、ArgoCD Project と Role-Based Access Control（RBAC）についての理解度を確認します。

1. ArgoCD Project（AppProject）の主な目的は何ですか？
   - A) 関連する Git repository をグループ化すること
   - B) アクセス制限付きで Application を論理的にグループ化すること
   - C) Kubernetes namespace を管理すること
   - D) CI/CD pipeline を設定すること

<details>
<summary>回答を表示</summary>

**回答: B) アクセス制限付きで Application を論理的にグループ化すること**

**解説:**
AppProject は、許可される source、destination、resource を制限した Application の論理的なグループ化を提供し、Argo CD のデプロイ範囲を制限します。Kubernetes RBAC、Pod Security Admission、ネットワーク分離、クォータは別の制御です。

</details>

2. AppProject の `sourceRepos` field は何を制御しますか？
   - A) 使用できる Git branch
   - B) 許可される source repository（Git/Helm/OCI）
   - C) container image repository
   - D) Helm chart version

<details>
<summary>回答を表示</summary>

**回答: B) 許可される source repository（Git/Helm/OCI）**

**解説:**
`sourceRepos` field は、この Project 内の Application が source として使用できる Git、Helm、OCI repository を制限します。Git branch や container image registry を選択するものではありません。`*` を使用すると任意の repository が許可され、特定の URL を指定すると、その repository のみに制限されます。

</details>

3. AppProject が deploy できる cluster と namespace を制限するにはどうしますか？
   - A) `destinations` field を使用する
   - B) `clusters` field を使用する
   - C) `namespaces` field を使用する
   - D) Kubernetes NetworkPolicy を使用する

<details>
<summary>回答を表示</summary>

**回答: A) `destinations` field を使用する**

**解説:**
`destinations` field は、許可される cluster と namespace の組み合わせを定義します。各 entry では server または登録済み cluster 名と namespace を指定します。これはデプロイ先の範囲であり、Application CR の配置場所を制限する `sourceNamespaces` とは別です。

</details>

4. AppProject における `clusterResourceWhitelist` の目的は何ですか？
   - A) 特定の cluster-scoped resource の管理を許可すること
   - B) IP address を許可リストに登録すること
   - C) 特定の user を許可すること
   - D) 特定の feature を有効にすること

<details>
<summary>回答を表示</summary>

**回答: A) 特定の cluster-scoped resource の管理を許可すること**

**解説:**
許可リストを設定していない新規のカスタム Project は、cluster-scoped resource を管理できません。初期状態で許可範囲の広い default Project は、すべての kind を明示的に許可する例外です。`clusterResourceWhitelist` を設定すると、その Project 内の Application が Namespace や ClusterRole などの特定の kind を管理できます。

</details>

5. ArgoCD Project 内で role を定義するにはどうしますか？
   - A) Kubernetes RBAC を使用する
   - B) AppProject spec の `roles` field を使用する
   - C) 別個の Role CRD を使用する
   - D) Project 内で role は定義できない

<details>
<summary>回答を表示</summary>

**回答: B) AppProject spec の `roles` field を使用する**

**解説:**
Project role は、AppProject の `spec.roles` field で定義されます。各 role には、name、description、許可する action を定める policy、発行 token の metadata または group binding があります。署名付き JWT は CLI/API 経由で発行され、metadata を宣言しただけでは token は発行されません。

</details>
