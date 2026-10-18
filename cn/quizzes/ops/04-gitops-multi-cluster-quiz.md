# GitOps 多集群测验

> **相关文档**：[GitOps 多集群](../../ops/04-gitops-multi-cluster.md)

## 选择题

### 1. 多集群 GitOps 中的 hub-spoke 模型是什么？

- A) 一种网络拓扑模式
- B) 一个中央管理集群管理多个工作负载集群
- C) 一种数据复制策略
- D) 一种负载均衡算法

<details>
<summary>显示答案</summary>

**答案：B) 一个中央管理集群管理多个工作负载集群**

在 hub-spoke 模型中，中央 hub 集群运行 ArgoCD，并将部署管理到多个 spoke 工作负载集群。这种方式集中管理 GitOps 操作，同时让工作负载在各集群中保持隔离。

</details>

### 2. ArgoCD 如何实现高可用性（HA）？

- A) 运行单个副本并自动重启
- B) 结合各组件的副本配置、控制器分片和具备韧性的部署位置
- C) 使用外部数据库复制
- D) 跨多个区域部署

<details>
<summary>显示答案</summary>

**答案：B) 结合各组件的副本配置、控制器分片和具备韧性的部署位置**

Application Controller 会将目标集群分片处理，而不是让其他副本全部待命。ApplicationSet 使用独立的 leader election；Server 是无状态的。Redis HA、组件放置、容量和 PDB 分别应对不同故障模式。单纯增加副本并不能保证高可用。

</details>

### 3. ArgoCD 中的 ApplicationSet 是什么？

- A) 一组手动创建的 Application
- B) 一个根据生成器动态创建 Application 的模板
- C) Application 配置的备份
- D) 一组 Helm chart

<details>
<summary>显示答案</summary>

**答案：B) 一个根据生成器动态创建 Application 的模板**

ApplicationSet 是一个控制器，可根据生成器提供的输入，用单个模板创建并管理多个 ArgoCD Application。这使得多集群和多环境部署可以按需生成。

</details>

### 4. 哪个 ApplicationSet 生成器会根据已注册集群的 Secret 选择集群并创建 Application？

- A) List 生成器
- B) Git 生成器
- C) Cluster 生成器
- D) Matrix 生成器

<details>
<summary>显示答案</summary>

**答案：C) Cluster 生成器**

Cluster 生成器会按配置的 selector 选择已注册集群，并提供这些集群的元数据。默认本地集群可能没有 Secret，因此使用 Secret 标签选择时可能会被排除。新集群只有在注册信息和标签都符合条件时才会被选中。

</details>

### 5. 如何将 IAM Identity Center（SSO）与 ArgoCD 集成？

- A) 直接连接数据库
- B) 通过 Dex 使用 SAML，并将经过验证的断言属性映射到 Argo CD RBAC
- C) 使用 SSH 密钥认证
- D) 管理 API 密钥

<details>
<summary>显示答案</summary>

**答案：B) 通过 Dex 使用 SAML，并将经过验证的断言属性映射到 Argo CD RBAC**

本章采用文档所述的 Identity Center SAML + Dex 路径。SAML URL 不是 OIDC issuer。分配组并不保证断言中会包含 groups 声明；上游指南把组属性映射列为一种变通方式。最小示例明确映射经过验证的 email 身份。

</details>

### 6. External Secrets Operator 在 GitOps 中有什么作用？

- A) 加密 Git 仓库
- B) 将外部提供方（如 AWS Secrets Manager）中的密钥同步到 Kubernetes
- C) 轮换 TLS 证书
- D) 管理访问 Git 所用的 SSH 密钥

<details>
<summary>显示答案</summary>

**答案：B) 将外部提供方（如 AWS Secrets Manager）中的密钥同步到 Kubernetes**

External Secrets Operator 可从 AWS Secrets Manager、HashiCorp Vault 或 Azure Key Vault 等外部密钥管理系统创建 Kubernetes Secret。这样敏感数据可以留在 Git 之外，同时保留 GitOps 工作流。

</details>

### 7. 在 ArgoCD Project 配置中，`sourceRepos` 限制什么？

- A) 部署目标集群
- B) Application 可使用的 Git 仓库
- C) 命名空间选择
- D) 资源配额

<details>
<summary>显示答案</summary>

**答案：B) Application 可使用的 Git 仓库**

ArgoCD Project 中的 `sourceRepos` 字段指定哪些 Git 仓库可以作为该 Project 中 Application 的来源。它限制 Application 的来源选择，但本身不会提供仓库凭据、目标端 RBAC，也不会为不受信任的代码建立沙箱。

</details>

### 8. 在 ApplicationSet 中使用 Matrix 生成器有什么作用？

- A) 执行数学计算
- B) 组合两个子生成器，产生匹配的参数组合
- C) 加密应用清单
- D) 验证 YAML 语法

<details>
<summary>显示答案</summary>

**答案：B) 组合两个子生成器，产生匹配的参数组合**

Matrix 生成器恰好包含两个子生成器。它会组合两者输出的参数，但须满足键兼容性和支持的嵌套限制。例如，可组合 Cluster 与 List 生成器，将多个服务部署到多个集群。

</details>

### 9. 通过 GitOps 管理 NodePool 时，关键注意事项是什么？

- A) NodePool 不能通过 GitOps 管理
- B) 应逐步实施变更，以避免中断正在运行的工作负载
- C) NodePool 必须与 ArgoCD 位于同一命名空间
- D) 只能管理 Spot 实例

<details>
<summary>显示答案</summary>

**答案：B) 应逐步实施变更，以避免中断正在运行的工作负载**

通过 GitOps 修改 NodePool 可能触发节点替换。应审查变更、替换容量、适用的中断预算和删除行为。将基础设施 Application 与手动同步分开，可以减少意外变更；任何同步策略都不能保证节点替换绝无中断。

</details>

### 10. 向 ArgoCD 添加远程集群的推荐方式是什么？

- A) 直接编辑 ArgoCD ConfigMap
- B) 使用 `argocd cluster add`，或创建包含凭据的集群 Secret
- C) 在每个集群上安装 ArgoCD
- D) 使用 kubectl port-forward

<details>
<summary>显示答案</summary>

**答案：B) 使用 `argocd cluster add`，或创建包含凭据的集群 Secret**

可用 `argocd cluster add` CLI 命令添加远程集群，也可以创建包含集群 API server URL 和凭据的 Secret。CLI 会修改目标端 RBAC。声明式 AWS 路径要求事先配置角色信任、EKS Access Entries/RBAC、真实的端点与 CA 数据，以及网络连通性；仅有 Secret 并不能提供这些前置条件。

</details>
