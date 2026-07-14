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
AppProject は、許可される source、destination、resource を制限した Application の論理的なグループ化を提供します。各チームが deploy できる内容を制限することで、マルチテナンシーを実現します。

</details>

2. AppProject の `sourceRepos` field は何を制御しますか？
   - A) 使用できる Git branch
   - B) Application が manifest を取得できる Git repository
   - C) container image repository
   - D) Helm chart version

<details>
<summary>回答を表示</summary>

**回答: B) Application が manifest を取得できる Git repository**

**解説:**
`sourceRepos` field は、この Project 内の Application が source として使用できる Git repository を制限します。`*` を使用すると任意の repository が許可されますが、特定の URL を指定すると、それらの repository のみに制限されます。

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
`destinations` field は、許可される cluster と namespace の組み合わせを定義します。各 entry では、Application が target にできる `server`（cluster URL または `*`）と `namespace`（特定の namespace または `*`）を指定します。

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
デフォルトでは、Project は cluster-scoped resource を管理できません。`clusterResourceWhitelist` により、Project 内の Application が特定の kind（Namespace や ClusterRole など）を管理できるようになります。

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
Project role は、AppProject の `spec.roles` field で定義されます。各 role には、name、description、policy（許可される action）、および任意の JWT token または group binding があります。

</details>
