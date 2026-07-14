# Backstage IDP 测验

1. 在 Backstage Software Catalog 中，用于注册微服务的 Entity Kind 是哪个？
   - A) Service
   - B) Component
   - C) Application
   - D) Workload

<details>
<summary>显示答案</summary>

**答案：B) Component**

**解释：**
在 Backstage Software Catalog 中，微服务、网站和库都会注册为 `Component` Kind。`spec.type` 字段用于区分 service、website、library 等。

</details>

---

2. Backstage Software Templates (Golden Paths) 的主要用途是什么？
   - A) 监控现有服务性能
   - B) 以标准化方式自动创建新服务/基础设施
   - C) 审计 Kubernetes 集群安全性
   - D) 监控 CI/CD pipelines

<details>
<summary>显示答案</summary>

**答案：B) 以标准化方式自动创建新服务/基础设施**

**解释：**
Software Templates (Golden Paths) 允许开发者在 Backstage UI 中输入少量参数，并自动生成标准化的项目结构（Dockerfile、Helm chart、CI/CD、catalog-info.yaml 等），从而自然地应用组织最佳实践。

</details>

---

3. 要在 Backstage 中显示 Kubernetes Pod 状态，catalog-info.yaml 中需要哪个 annotation？
   - A) kubernetes.io/pod-name
   - B) backstage.io/kubernetes-id
   - C) app.kubernetes.io/managed-by
   - D) backstage.io/k8s-cluster

<details>
<summary>显示答案</summary>

**答案：B) backstage.io/kubernetes-id**

**解释：**
`backstage.io/kubernetes-id` annotation 由 Backstage Kubernetes plugin 用于将 catalog entities 与 Kubernetes resources 进行匹配。该值必须与 Kubernetes Deployment 上的 `backstage.io/kubernetes-id` label 匹配。

</details>

---

4. 在 EKS 生产环境中，最适合 Backstage 的 PostgreSQL 设置是什么？
   - A) 内置 SQLite
   - B) 集群内 PostgreSQL StatefulSet
   - C) Amazon RDS PostgreSQL（外部托管）
   - D) DynamoDB

<details>
<summary>显示答案</summary>

**答案：C) Amazon RDS PostgreSQL（外部托管）**

**解释：**
生产环境应使用 Amazon RDS 这样的托管数据库，以获得自动备份、高可用性（Multi-AZ）和监控能力。在 Helm values 中设置 `postgresql.enabled: false`，并通过 Secrets 提供外部 RDS 连接详细信息。

</details>

---

5. Backstage TechDocs 使用哪个文档构建工具？
   - A) Docusaurus
   - B) GitBook
   - C) MkDocs
   - D) Sphinx

<details>
<summary>显示答案</summary>

**答案：C) MkDocs**

**解释：**
Backstage TechDocs 基于 MkDocs 构建。它从服务 repo 的 `docs/` 目录和 `mkdocs.yml` 文件生成文档，发布到 S3 等存储，并使其可直接从 catalog 访问。

</details>

---

6. 在逐步采用 Backstage 时，应该从哪个功能开始？
   - A) Software Templates
   - B) Software Catalog
   - C) TechDocs
   - D) RBAC Permission Framework

<details>
<summary>显示答案</summary>

**答案：B) Software Catalog**

**解释：**
Software Catalog 是 Backstage 的基础，所有其他功能都建立在其之上。先注册组织的服务、APIs 和团队信息，然后再逐步添加 Templates 和 TechDocs。

</details>

---

7. Backstage Software Template 如何同时自动完成 GitHub repo 创建和 ArgoCD Application 创建？
   - A) Backstage 直接调用 Kubernetes API
   - B) Template steps 按顺序执行 publish:github 和 argocd:create-resources actions
   - C) GitHub Webhooks 自动触发 ArgoCD
   - D) Helm chart 包含所有 resources

<details>
<summary>显示答案</summary>

**答案：B) Template steps 按顺序执行 publish:github 和 argocd:create-resources actions**

**解释：**
Backstage Scaffolder 会按顺序执行 Template 的 `steps` section 中定义的 actions。`publish:github` 创建 repo，并将其输出（remoteUrl）作为输入传递给 `argocd:create-resources`，以自动创建 ArgoCD Application。最后，`catalog:register` 会将其添加到 catalog。

</details>

---

8. 在 Backstage Permission Framework 中，如何限制团队只能修改自己的 entities？
   - A) Kubernetes RBAC ClusterRole
   - B) 在 policy 中使用 conditions field 匹配 spec.owner
   - C) GitHub repository permissions
   - D) Ingress network policies

<details>
<summary>显示答案</summary>

**答案：B) 在 policy 中使用 conditions field 匹配 spec.owner**

**解释：**
Backstage Permission Framework policy 的 `conditions` field 可以匹配 `spec.owner` 等于团队名称的 entities，从而仅授予团队更新其自有 entities 的权限。这样既保持团队自主性，又将其他团队 entities 的修改权限限制为只读。

</details>
