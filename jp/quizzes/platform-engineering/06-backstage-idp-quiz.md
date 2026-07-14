# Backstage IDP クイズ

1. Backstage Software Catalog に microservice（マイクロサービス）を登録するために使用される Entity Kind はどれですか？
   - A) Service
   - B) Component
   - C) Application
   - D) Workload

<details>
<summary>答えを表示</summary>

**解答: B) Component**

**解説:**
Backstage Software Catalog では、microservices、websites、libraries はすべて `Component` Kind として登録されます。`spec.type` field によって service、website、library などが区別されます。

</details>

---

2. Backstage Software Templates (Golden Paths) の主な目的は何ですか？
   - A) 既存 service のパフォーマンスを監視する
   - B) 新しい services/infrastructure を標準化された方法で自動作成する
   - C) Kubernetes cluster security を監査する
   - D) CI/CD pipelines を監視する

<details>
<summary>答えを表示</summary>

**解答: B) 新しい services/infrastructure を標準化された方法で自動作成する**

**解説:**
Software Templates (Golden Paths) により、developers は Backstage UI でいくつかの parameters を入力するだけで、標準化された project structure（Dockerfile、Helm chart、CI/CD、catalog-info.yaml など）を自動的に scaffold でき、organization の best practices を自然に適用できます。

</details>

---

3. Backstage で Kubernetes Pod status を表示するために catalog-info.yaml で必要な annotation はどれですか？
   - A) kubernetes.io/pod-name
   - B) backstage.io/kubernetes-id
   - C) app.kubernetes.io/managed-by
   - D) backstage.io/k8s-cluster

<details>
<summary>答えを表示</summary>

**解答: B) backstage.io/kubernetes-id**

**解説:**
`backstage.io/kubernetes-id` annotation は、Backstage Kubernetes plugin が catalog entities と Kubernetes resources を対応付けるために使用します。この値は Kubernetes Deployment 上の `backstage.io/kubernetes-id` label と一致している必要があります。

</details>

---

4. EKS production environment における Backstage に最も適した PostgreSQL setup はどれですか？
   - A) Built-in SQLite
   - B) In-cluster PostgreSQL StatefulSet
   - C) Amazon RDS PostgreSQL (external managed)
   - D) DynamoDB

<details>
<summary>答えを表示</summary>

**解答: C) Amazon RDS PostgreSQL (external managed)**

**解説:**
Production environments では、自動 backups、high availability (Multi-AZ)、monitoring のために Amazon RDS のような managed databases を使用するべきです。Helm values で `postgresql.enabled: false` を設定し、Secrets 経由で外部 RDS connection details を提供します。

</details>

---

5. Backstage TechDocs が使用する documentation build tool はどれですか？
   - A) Docusaurus
   - B) GitBook
   - C) MkDocs
   - D) Sphinx

<details>
<summary>答えを表示</summary>

**解答: C) MkDocs**

**解説:**
Backstage TechDocs は MkDocs の上に構築されています。service repo の `docs/` directory と `mkdocs.yml` file から documentation を生成し、S3 のような storage に公開して、catalog から直接アクセスできるようにします。

</details>

---

6. Backstage を段階的に導入する場合、どの feature から始めるべきですか？
   - A) Software Templates
   - B) Software Catalog
   - C) TechDocs
   - D) RBAC Permission Framework

<details>
<summary>答えを表示</summary>

**解答: B) Software Catalog**

**解説:**
Software Catalog は Backstage の基盤であり、他のすべての features はその上に構築されます。まず organization の services、APIs、team information を登録し、その後 Templates と TechDocs を段階的に追加します。

</details>

---

7. Backstage Software Template で GitHub repo creation と ArgoCD Application creation の両方を自動化するにはどうすればよいですか？
   - A) Backstage が Kubernetes API を直接呼び出す
   - B) Template steps が publish:github と argocd:create-resources actions を順番に実行する
   - C) GitHub Webhooks が ArgoCD を自動的に trigger する
   - D) Helm chart にすべての resources を含める

<details>
<summary>答えを表示</summary>

**解答: B) Template steps が publish:github と argocd:create-resources actions を順番に実行する**

**解説:**
Backstage Scaffolder は、Template の `steps` section に定義された actions を順番に実行します。`publish:github` が repo を作成し、その output (remoteUrl) が input として `argocd:create-resources` に渡され、ArgoCD Application を自動作成します。最後に、`catalog:register` がそれを catalog に追加します。

</details>

---

8. Backstage Permission Framework で、teams が自分たちの entities だけを変更できるよう制限するにはどうすればよいですか？
   - A) Kubernetes RBAC ClusterRole
   - B) policy で conditions field を使用して spec.owner と一致させる
   - C) GitHub repository permissions
   - D) Ingress network policies

<details>
<summary>答えを表示</summary>

**解答: B) policy で conditions field を使用して spec.owner と一致させる**

**解説:**
Backstage Permission Framework policy の `conditions` field は、`spec.owner` が team name と等しい entities に一致させることができ、自分たちの entities に対してのみ update permissions を付与します。これにより、team autonomy を維持しながら、他の teams の entities の変更を read-only に制限できます。

</details>
