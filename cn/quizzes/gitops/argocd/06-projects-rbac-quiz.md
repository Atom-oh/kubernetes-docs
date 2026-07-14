# ArgoCD Projects 和 RBAC 测验

本测验用于测试你对 ArgoCD Projects 和 Role-Based Access Control（基于角色的访问控制）的理解。

1. ArgoCD Project（AppProject）的主要用途是什么？
   - A) 对相关 Git 仓库进行分组
   - B) 对应用程序进行逻辑分组并实施访问限制
   - C) 管理 Kubernetes namespaces
   - D) 配置 CI/CD pipelines

<details>
<summary>显示答案</summary>

**答案：B) 对应用程序进行逻辑分组并实施访问限制**

**说明：**
AppProjects 对 Applications 进行逻辑分组，并限制允许使用的 sources、destinations 和 resources。它们通过限制每个团队能够部署的内容来实现多租户。

</details>

2. AppProject 中的 `sourceRepos` 字段控制什么？
   - A) 可以使用的 Git branches
   - B) Applications 可以从中拉取 manifests 的 Git 仓库
   - C) container image 仓库
   - D) Helm chart 版本

<details>
<summary>显示答案</summary>

**答案：B) Applications 可以从中拉取 manifests 的 Git 仓库**

**说明：**
`sourceRepos` 字段限制此项目中的 Applications 可以用作 source 的 Git 仓库。使用 `*` 允许任何仓库，而指定 URL 则仅限于这些仓库。

</details>

3. 如何限制 AppProject 可以部署到哪些 clusters 和 namespaces？
   - A) 使用 `destinations` 字段
   - B) 使用 `clusters` 字段
   - C) 使用 `namespaces` 字段
   - D) 使用 Kubernetes NetworkPolicies

<details>
<summary>显示答案</summary>

**答案：A) 使用 `destinations` 字段**

**说明：**
`destinations` 字段定义允许的 cluster 和 namespace 组合。每个条目都指定 Applications 可以作为目标的 `server`（cluster URL 或 `*`）和 `namespace`（指定 namespace 或 `*`）。

</details>

4. AppProject 中 `clusterResourceWhitelist` 的用途是什么？
   - A) 允许管理特定的 cluster-scoped resources
   - B) 将 IP addresses 加入白名单
   - C) 允许特定 users
   - D) 启用特定 features

<details>
<summary>显示答案</summary>

**答案：A) 允许管理特定的 cluster-scoped resources**

**说明：**
默认情况下，projects 无法管理 cluster-scoped resources。`clusterResourceWhitelist` 允许项目中的 Applications 管理特定 kinds（例如 Namespaces 或 ClusterRoles）。

</details>

5. 如何在 ArgoCD Project 中定义 role？
   - A) 使用 Kubernetes RBAC
   - B) 使用 AppProject spec 中的 `roles` 字段
   - C) 使用单独的 Role CRD
   - D) 无法在 projects 中定义 roles

<details>
<summary>显示答案</summary>

**答案：B) 使用 AppProject spec 中的 `roles` 字段**

**说明：**
Project roles 在 AppProject 的 `spec.roles` 字段中定义。每个 role 都包含名称、描述、policies（允许执行的 actions），以及可选的 JWT tokens 或 group bindings。

</details>
