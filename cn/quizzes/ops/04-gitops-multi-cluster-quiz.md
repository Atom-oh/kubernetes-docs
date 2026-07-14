# GitOps 多 Cluster 测验

> **相关文档**: [GitOps Multi-Cluster](../../ops/04-gitops-multi-cluster.md)

## 选择题

### 1. 在 multi-cluster GitOps 中，hub-spoke 模型是什么？

- A) 一种网络拓扑模式
- B) 一个中央管理 cluster（集群），控制多个 workload cluster
- C) 一种数据复制策略
- D) 一种负载均衡算法

<details>
<summary>显示答案</summary>

**答案：B) 一个中央管理 cluster，控制多个 workload cluster**

**解释：**
在 hub-spoke 模型中，中央的 “hub” cluster 运行 ArgoCD，并管理到多个 “spoke” workload cluster 的部署。这会集中 GitOps 操作，同时让 workload 在各个 cluster 之间保持隔离。

</details>

### 2. ArgoCD 如何实现高可用性 (HA)？

- A) 运行单个 replica 并自动重启
- B) 为每个 component 运行多个 replica，并使用 leader election
- C) 使用外部数据库复制
- D) 跨多个 region 部署

<details>
<summary>显示答案</summary>

**答案：B) 为每个 component 运行多个 replica，并使用 leader election**

**解释：**
ArgoCD HA 会部署 application-controller、repo-server 和 server component 的多个 replica。application-controller 使用 leader election 来确保每个 application 只有一个 instance 进行处理，而其他 instance 处于待命状态。

</details>

### 3. ArgoCD 中的 ApplicationSet 是什么？

- A) 一组手动创建的 Applications
- B) 一个基于 generator 动态生成 Applications 的 template
- C) Application configuration 的备份
- D) 一组 Helm charts

<details>
<summary>显示答案</summary>

**答案：B) 一个基于 generator 动态生成 Applications 的 template**

**解释：**
ApplicationSet 是一个 controller，使用 generator（List、Cluster、Git、Matrix 等）从单个 template 自动创建并管理多个 ArgoCD Applications。这使可扩展的 multi-cluster 和 multi-environment 部署成为可能。

</details>

### 4. 哪个 ApplicationSet generator 会基于已注册的 cluster secrets 创建 Applications？

- A) List generator
- B) Git generator
- C) Cluster generator
- D) Matrix generator

<details>
<summary>显示答案</summary>

**答案：C) Cluster generator**

**解释：**
Cluster generator 会遍历 ArgoCD 中注册的所有 cluster（以 secrets 形式存储），并为每个 cluster 生成一个 Application。这使得无需修改 ApplicationSet 就能自动部署到新的 cluster。

</details>

### 5. 如何将 IAM Identity Center (SSO) 与 ArgoCD 集成？

- A) 直接数据库连接
- B) 使用 SAML 或 OIDC authentication，并配合基于 group 的 RBAC
- C) SSH key authentication
- D) API key management

<details>
<summary>显示答案</summary>

**答案：B) 使用 SAML 或 OIDC authentication，并配合基于 group 的 RBAC**

**解释：**
ArgoCD 支持 SAML 和 OIDC 进行 SSO 集成。IAM Identity Center groups 可以映射到 ArgoCD RBAC roles，从而实现集中式访问管理，权限由你的 identity provider 控制。

</details>

### 6. External Secrets Operator 在 GitOps 中的用途是什么？

- A) 加密 git repositories
- B) 将 secrets 从 external providers（AWS Secrets Manager）同步到 Kubernetes
- C) 轮换 TLS certificates
- D) 管理用于 git access 的 SSH keys

<details>
<summary>显示答案</summary>

**答案：B) 将 secrets 从 external providers（AWS Secrets Manager）同步到 Kubernetes**

**解释：**
External Secrets Operator 会从 AWS Secrets Manager、HashiCorp Vault 或 Azure Key Vault 等外部 secret management systems 自动创建 Kubernetes secrets。这可以在保持 GitOps workflow 的同时，让 sensitive data 不进入 git。

</details>

### 7. 在 ArgoCD project configuration 中，`sourceRepos` 限制什么？

- A) 部署的 target clusters
- B) applications 允许使用的 git repositories
- C) Namespace selection
- D) Resource quotas

<details>
<summary>显示答案</summary>

**答案：B) applications 允许使用的 git repositories**

**解释：**
ArgoCD Projects 中的 `sourceRepos` 字段指定哪些 git repositories 可以用作该 project 中 Applications 的 source。它通过防止未经授权的 repository access 来提供安全边界。

</details>

### 8. 在 ApplicationSets 中使用 Matrix generator 的好处是什么？

- A) 它执行数学计算
- B) 它组合多个 generator，以创建参数的笛卡尔积
- C) 它加密 application manifests
- D) 它验证 YAML syntax

<details>
<summary>显示答案</summary>

**答案：B) 它组合多个 generator，以创建参数的笛卡尔积**

**解释：**
Matrix generator 会组合两个或更多 generator，为其输出的每一种组合创建 Applications。例如，将 Cluster generator 与 List generator 组合，会把多个 services 部署到多个 cluster。

</details>

### 9. 通过 GitOps 管理 NodePools 时，一个关键注意事项是什么？

- A) NodePools 不能通过 GitOps 管理
- B) 变更应逐步进行，以避免中断正在运行的 workloads
- C) NodePools 必须与 ArgoCD 位于同一个 namespace
- D) 只能管理 Spot instances

<details>
<summary>显示答案</summary>

**答案：B) 变更应逐步进行，以避免中断正在运行的 workloads**

**解释：**
通过 GitOps 进行 NodePool 变更时应谨慎管理，因为修改可能会触发 node replacements。使用 Progressive Sync 或为 node management 使用单独 Applications 等策略，有助于避免中断。

</details>

### 10. 向 ArgoCD 添加 remote cluster 的推荐方式是什么？

- A) 直接编辑 ArgoCD ConfigMap
- B) 使用 `argocd cluster add`，或创建包含 credentials 的 cluster Secret
- C) 在每个 cluster 上安装 ArgoCD
- D) 使用 kubectl port-forward

<details>
<summary>显示答案</summary>

**答案：B) 使用 `argocd cluster add`，或创建包含 credentials 的 cluster Secret**

**解释：**
Remote clusters 可通过 `argocd cluster add` CLI command 添加，或通过创建包含该 cluster 的 API server URL 和 credentials 的 Secret 添加。ArgoCD 使用这些 credentials 将 applications 部署并同步到 remote clusters。

</details>
