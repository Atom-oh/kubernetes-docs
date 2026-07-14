# Tekton Pipelines クイズ

1. Kubernetes 環境において、Tekton は Jenkins や GitHub Actions と比べてどのような利点がありますか？
   - A) Tekton はより多くの plugins を提供する
   - B) CRD ベースの pipelines は Kubernetes resources として管理され、GitOps、RBAC、namespace isolation を可能にする
   - C) Tekton はより高速な実行速度を提供する
   - D) Tekton は無料だが、他のツールは有料である

<details>
<summary>答えを表示</summary>

**回答: B) CRD ベースの pipelines は Kubernetes resources として管理され、GitOps、RBAC、namespace isolation を可能にする**

**解説:**
Tekton は Tasks、Pipelines、PipelineRuns を Kubernetes CRDs として定義します。これにより、Git での宣言的な pipeline 管理（GitOps）、Kubernetes RBAC によるアクセス制御、namespace レベルの isolation、kubectl による管理が可能になります。各 Step は個別の container で実行され、強力な isolation を実現します。

</details>

---

2. Tekton Pipeline で Tasks 間でデータを共有するにはどうしますか？
   - A) environment variables 経由で渡す
   - B) Workspaces（PVC）を通じて file systems を共有し、小さなデータは Results 経由で渡す
   - C) ConfigMaps に保存する
   - D) Tasks 間で直接 network communication を行う

<details>
<summary>答えを表示</summary>

**回答: B) Workspaces（PVC）を通じて file systems を共有し、小さなデータは Results 経由で渡す**

**解説:**
Workspaces は Tasks 間で PVC ベースの file system 共有を提供し、source code を clone してから build するような patterns に適しています。Results は小さな string データ（image tags、commit SHAs など）を Tasks 間で渡し、`$(tasks.task-name.results.result-name)` として参照されます。

</details>

---

3. Tekton Triggers の EventListener は何をしますか？
   - A) events を生成して外部 systems に送信する
   - B) webhook requests を受信し、TriggerBinding/TriggerTemplate 経由で PipelineRuns を自動的に作成する
   - C) pipeline execution results を監視する
   - D) 定期的に Git repositories を poll する

<details>
<summary>答えを表示</summary>

**回答: B) webhook requests を受信し、TriggerBinding/TriggerTemplate 経由で PipelineRuns を自動的に作成する**

**解説:**
EventListener は webhook requests（GitHub Push、PR events など）を受信する HTTP endpoint です。Interceptors が request を検証/フィルタリングし、TriggerBinding が payload から parameters を抽出し、TriggerTemplate がそれらの parameters を使って PipelineRun を作成します。

</details>

---

4. Tekton Chains はどの Supply Chain Security 機能を提供しますか？
   - A) container images の vulnerabilities を scan する
   - B) TaskRun/PipelineRun artifacts（images）に自動的に署名し、SLSA Provenance を生成する
   - C) network traffic を暗号化する
   - D) RBAC policies を自動生成する

<details>
<summary>答えを表示</summary>

**回答: B) TaskRun/PipelineRun artifacts（images）に自動的に署名し、SLSA Provenance を生成する**

**解説:**
Tekton Chains は TaskRun 完了後に Cosign/Sigstore を使って OCI images に自動的に署名し、SLSA Provenance（build metadata、source information、build steps など）を生成します。これにより software supply chain security が強化され、image の出所と integrity の検証が可能になります。

</details>

---

5. Tekton Pipeline における `finally` Tasks の目的は何ですか？
   - A) pipeline の最初の Task として実行する
   - B) pipeline の成功/失敗に関係なく常に最後に実行される cleanup tasks
   - C) 条件付きで実行される Tasks
   - D) parallel に実行される Tasks

<details>
<summary>答えを表示</summary>

**回答: B) pipeline の成功/失敗に関係なく常に最後に実行される cleanup tasks**

**解説:**
`finally` Tasks は、pipeline 内の他のすべての Tasks が完了した後、成功または失敗に関係なく実行されます。build 失敗時にも実行されるため、一時 resources の cleanup、notifications の送信、test results の reporting に適しています。try-catch-finally pattern に似ています。

</details>

---

6. ArgoCD + Tekton の integration architecture で CI/CD を分離する理由は何ですか？
   - A) Tekton は CD を support していないため
   - B) CI（build/test）と CD（deploy）の関心事を分離すると、security、auditing、rollback が向上する
   - C) ArgoCD は CI を support していないため
   - D) ツールの licenses が異なるため

<details>
<summary>答えを表示</summary>

**回答: B) CI（build/test）と CD（deploy）の関心事を分離すると、security、auditing、rollback が向上する**

**解説:**
Tekton は CI（source clone、test、build、image push）を処理し、ArgoCD は CD（Git ベースの宣言的 deployment）を処理します。CI は image tag を Git に commit し、ArgoCD がこの変更を検出して deploy します。これにより deployment 権限の分離、Git ベースの audit trails、宣言的 rollback が可能になります。

</details>

---

7. Tekton における CEL Interceptor のユースケースは何ですか？
   - A) GitHub signatures を検証する
   - B) CEL expressions（特定の branches、file paths など）を使用して webhook payloads をフィルタリングおよび変換する
   - C) GitLab tokens を検証する
   - D) Bitbucket events を処理する

<details>
<summary>答えを表示</summary>

**回答: B) CEL expressions（特定の branches、file paths など）を使用して webhook payloads をフィルタリングおよび変換する**

**解説:**
CEL（Common Expression Language）Interceptor は、CEL expressions を使用して webhook payloads に対するフィルタリングと変換を行います。たとえば、`body.ref == 'refs/heads/main'` は main branch の pushes のみをフィルタリングし、`body.commits.exists(c, c.modified.exists(f, f.startsWith('src/')))` は特定の path 変更時のみ trigger します。

</details>

---

8. Tekton PipelineRuns に適した cleanup strategy は何ですか？
   - A) すべての PipelineRuns を永続的に保持する
   - B) resources を管理するため、成功/失敗ごとに異なる retention periods を設定した TTL ベースの自動削除を行う
   - C) 手動でのみ削除する
   - D) PipelineRuns は自動的に削除される

<details>
<summary>答えを表示</summary>

**回答: B) resources を管理するため、成功/失敗ごとに異なる retention periods を設定した TTL ベースの自動削除を行う**

**解説:**
PipelineRuns と TaskRuns は実行後も etcd に残り、storage を消費します。Tekton の cleanup settings（`keep`、`keep-since`）または CronJob ベースの cleanup scripts を使用して、古い execution records を自動的に削除します。Failed runs は通常、debugging のためにより長く保持されます。

</details>
