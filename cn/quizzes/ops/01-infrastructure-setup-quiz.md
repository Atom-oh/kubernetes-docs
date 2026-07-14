# 基础设施设置测验

> **相关文档**: [基础设施设置](../../ops/01-infrastructure-setup.md)

## 选择题

### 1. Terraform 3-Layer 架构的主要目的是什么？

- A) 减少 Terraform 文件的数量
- B) 按生命周期和爆炸半径分离基础设施
- C) 实现更快的部署时间
- D) 消除对状态管理的需求

<details>
<summary>显示答案</summary>

**答案：B) 按生命周期和爆炸半径分离基础设施**

**解释：**
3-Layer 架构将基础设施分为 Foundation (VPC, IAM)、Platform (EKS cluster) 和 Workload (applications) 层。每一层都有不同的变更频率和爆炸半径，从而使基础设施变更更安全、更易于管理。

</details>

### 2. 在 Terraform S3 backend 配置中，DynamoDB table 的用途是什么？

- A) 存储 Terraform state 文件
- B) 提供 state locking 和一致性
- C) 备份 Terraform 配置
- D) 记录 Terraform 操作日志

<details>
<summary>显示答案</summary>

**答案：B) 提供 state locking 和一致性**

**解释：**
DynamoDB table 支持 state locking，以防止对同一个 state 文件进行并发修改。当多个用户或 CI/CD pipeline 尝试同时修改基础设施时，这可以防止竞争条件。

</details>

### 3. `terraform_remote_state` data source 允许你做什么？

- A) 将 state 文件存储在远程位置
- B) 引用另一个 Terraform state 的输出
- C) 在 backend 之间迁移 state
- D) 自动加密 state 文件

<details>
<summary>显示答案</summary>

**答案：B) 引用另一个 Terraform state 的输出**

**解释：**
`terraform_remote_state` data source 允许一个 Terraform 配置读取另一个 state 文件中的输出值。这支持跨层引用，例如 Platform 层从 Foundation 层读取 VPC ID。

</details>

### 4. 生产环境 EKS cluster 推荐使用哪种 VPC CIDR block 大小？

- A) /24（256 个地址）
- B) /20（4,096 个地址）
- C) /16（65,536 个地址）
- D) /8（1600 万个地址）

<details>
<summary>显示答案</summary>

**答案：C) /16（65,536 个地址）**

**解释：**
/16 CIDR block 提供 65,536 个 IP 地址，推荐用于生产环境 EKS cluster。这可以满足 Pod IP 分配（尤其是使用 VPC CNI 时）、未来增长和多 AZ 部署的需求，而不必担心 IP 耗尽。

</details>

### 5. 与 Managed Node Groups 相比，EKS Auto Mode 的关键特征是什么？

- A) Auto Mode 需要手动预置节点
- B) Auto Mode 自动管理节点生命周期和扩缩容
- C) Auto Mode 只支持 Spot instances
- D) Auto Mode 消除了对 pods 的需求

<details>
<summary>显示答案</summary>

**答案：B) Auto Mode 自动管理节点生命周期和扩缩容**

**解释：**
EKS Auto Mode 会根据 workload 需求自动处理节点预置、扩缩容和生命周期管理。与 Managed Node Groups 不同，operator 不需要配置 Auto Scaling Groups 或手动管理节点更新。

</details>

### 6. Pod Identity 与 IRSA (IAM Roles for Service Accounts) 有何不同？

- A) Pod Identity 不支持 IAM roles
- B) Pod Identity 使用 EKS 管理的凭证，无需设置 OIDC provider
- C) Pod Identity 需要手动轮换 token
- D) Pod Identity 仅适用于 Fargate

<details>
<summary>显示答案</summary>

**答案：B) Pod Identity 使用 EKS 管理的凭证，无需设置 OIDC provider**

**解释：**
Pod Identity 通过消除配置 OIDC provider 的需要，简化了 IAM 集成。AWS 通过 Pod Identity Agent 管理凭证注入，因此与 IRSA 相比更易于设置和维护。

</details>

### 7. 在 3-Layer 架构中，哪一层包含 EKS cluster 资源？

- A) Foundation Layer
- B) Platform Layer
- C) Workload Layer
- D) Network Layer

<details>
<summary>显示答案</summary>

**答案：B) Platform Layer**

**解释：**
Platform Layer 包含 EKS cluster、node groups 和 cluster add-ons。它依赖 Foundation Layer (VPC, subnets)，并为 Workload Layer (applications, services) 提供平台。

</details>

### 8. 存储 Terraform state 的 S3 buckets 应启用什么？

- A) Public access
- B) Versioning and encryption
- C) Static website hosting
- D) 仅 Cross-region replication

<details>
<summary>显示答案</summary>

**答案：B) Versioning and encryption**

**解释：**
Terraform state 文件包含敏感信息，应通过 versioning（用于从损坏或意外变更中恢复）和 encryption（用于保护静态 secret）来保护。应始终阻止 public access。

</details>

### 9. 使用 Terraform workspaces 进行多环境管理时，一个关键限制是什么？

- A) Workspaces 不能使用变量
- B) 所有环境共享相同的 backend 配置
- C) Workspaces 不支持 modules
- D) 只允许两个 workspaces

<details>
<summary>显示答案</summary>

**答案：B) 所有环境共享相同的 backend 配置**

**解释：**
Terraform workspaces 共享相同的 backend 配置和代码，这可能导致在开发环境工作时意外更改生产环境。许多团队更倾向于为每个环境使用单独的目录或代码库，以获得更强的隔离性。

</details>

### 10. 管理 Terraform provider 版本的推荐方法是什么？

- A) 始终使用没有约束的最新版本
- B) 在 required_providers block 中使用精确版本约束
- C) 让 Terraform 自动更新 providers
- D) 避免指定 provider 版本

<details>
<summary>显示答案</summary>

**答案：B) 在 required_providers block 中使用精确版本约束**

**解释：**
在 `required_providers` block 中指定精确或悲观版本约束（例如 `~> 5.0`）可确保部署可复现，并防止 provider 更新带来意外的破坏性变更。这在生产环境中尤其重要。

</details>
