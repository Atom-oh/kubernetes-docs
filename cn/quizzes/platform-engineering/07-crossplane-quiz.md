# Crossplane 测验

1. Crossplane Compositions 解决的核心问题是什么？
   - A) 配置 Kubernetes 集群网络
   - B) 将多个基础设施资源捆绑到一个用于自助服务的抽象 API 中
   - C) 自动化容器镜像构建
   - D) 优化 Pod 资源请求

<details>
<summary>显示答案</summary>

**答案：B) 将多个基础设施资源捆绑到一个用于自助服务的抽象 API 中**

**解释：**
Compositions 将多个 Managed Resources（RDS instance、SecurityGroup、SubnetGroup 等）打包到一个 Composite Resource（XR）中。开发者可以通过简单的 Claims 来预置所需的基础设施，而无需了解复杂的基础设施细节。

</details>

---

2. Crossplane Claims (XC) 与 Composite Resources (XR) 之间是什么关系？
   - A) Claims 是集群范围的，XRs 是命名空间范围的
   - B) Claims 是命名空间范围的请求，XRs 是集群范围的实际资源
   - C) Claims 和 XRs 是相同的资源
   - D) XRs 是 Claims 的备份副本

<details>
<summary>显示答案</summary>

**答案：B) Claims 是命名空间范围的请求，XRs 是集群范围的实际资源**

**解释：**
Claims (XC) 是供开发者请求基础设施的命名空间范围接口。创建 Claim 时，会在集群范围创建对应的 Composite Resource (XR)，并且 XR 会根据 Composition 预置实际的 Managed Resources。

</details>

---

3. 使用 Crossplane 管理 AWS 资源时，为什么要使用 IRSA (IAM Roles for Service Accounts)？
   - A) 为了降低 Crossplane 许可证成本
   - B) 为了安全地将 AWS 凭证传递给 Pods，并应用最小权限原则
   - C) 为了提升 Crossplane 性能
   - D) 为了支持多集群

<details>
<summary>显示答案</summary>

**答案：B) 为了安全地将 AWS 凭证传递给 Pods，并应用最小权限原则**

**解释：**
IRSA 通过将 IAM Roles 与 Kubernetes ServiceAccounts 关联，并自动注入临时凭证，消除了直接管理 AWS Access Keys 的需要。这增强了安全性，并允许按 Provider 仅授予所需的最小 IAM 权限。

</details>

---

4. Terraform 和 Crossplane 最大的架构差异是什么？
   - A) Terraform 使用 YAML，Crossplane 使用 HCL
   - B) Terraform 使用命令式执行（apply/destroy），Crossplane 通过 Kubernetes controllers 使用持续调谐
   - C) Terraform 只支持云，Crossplane 只支持本地环境
   - D) Terraform 是免费的，Crossplane 是付费的

<details>
<summary>显示答案</summary>

**答案：B) Terraform 使用命令式执行（apply/destroy），Crossplane 通过 Kubernetes controllers 使用持续调谐**

**解释：**
Terraform 是一种基于工作流的工具，通过 `terraform apply`/`destroy` 命令运行。Crossplane 使用 Kubernetes controller 模式运行，持续比较声明状态与实际状态并调谐差异。这支持自动漂移检测和修正。

</details>

---

5. 在什么场景下会同时使用 ACK 和 Crossplane？
   - A) ACK 和 Crossplane 不兼容，因此只能使用其中一个
   - B) 对简单 AWS 资源使用 ACK，对复杂的多资源抽象使用 Crossplane Compositions
   - C) ACK 用于开发，Crossplane 仅用于生产
   - D) ACK 管理网络，Crossplane 仅管理存储

<details>
<summary>显示答案</summary>

**答案：B) 对简单 AWS 资源使用 ACK，对复杂的多资源抽象使用 Crossplane Compositions**

**解释：**
ACK 适合与 AWS API 进行 1:1 映射的简单资源管理，而 Crossplane 擅长通过 Compositions 将多个资源打包为单个抽象 API。简单的 S3 buckets 可以用 ACK 管理，而 RDS+SecurityGroup+SubnetGroup 这类组合包更适合使用 Crossplane Compositions。

</details>

---

6. 为什么 Crossplane Connection Details 很重要？
   - A) 监控网络连接状态
   - B) 自动生成包含已预置资源访问信息（endpoints、passwords 等）的 Kubernetes Secrets
   - C) 管理 Crossplane Providers 之间的连接
   - D) 配置多集群之间的网络连接

<details>
<summary>显示答案</summary>

**答案：B) 自动生成包含已预置资源访问信息（endpoints、passwords 等）的 Kubernetes Secrets**

**解释：**
Connection Details 会自动将已预置资源的访问信息（database endpoint、port、username、password 等）存储在 Kubernetes Secrets 中。Applications 可以挂载这些 Secrets 来连接到已预置的基础设施。

</details>

---

7. 在 Backstage + Crossplane 集成中，正确的开发者自助服务工作流顺序是什么？
   - A) ArgoCD 部署 → Backstage catalog 注册 → Crossplane Claim 创建
   - B) Backstage Template 生成 Crossplane Claim YAML → Git push → ArgoCD sync → Crossplane 预置
   - C) Crossplane 预置 → Backstage Template 创建 → Git push
   - D) Git push → Backstage catalog 注册 → ArgoCD 部署

<details>
<summary>显示答案</summary>

**答案：B) Backstage Template 生成 Crossplane Claim YAML → Git push → ArgoCD sync → Crossplane 预置**

**解释：**
当开发者在 Backstage Template 中输入参数（DB size、environment 等）时，Template 会生成 Crossplane Claim YAML 并将其推送到 Git repository。ArgoCD 检测到变更并将其同步到集群，在集群中 Crossplane 处理 Claim 并预置实际基础设施。

</details>

---

8. 与 Terraform 相比，Crossplane 的漂移检测为什么更优？
   - A) Terraform 不支持漂移检测
   - B) Crossplane controllers 持续监控实际状态并自动修正，而 Terraform 需要手动 `plan`/`apply`
   - C) Crossplane 预置速度更快
   - D) Crossplane 支持更多云

<details>
<summary>显示答案</summary>

**答案：B) Crossplane controllers 持续监控实际状态并自动修正，而 Terraform 需要手动 `plan`/`apply`**

**解释：**
Crossplane controllers 会定期检查云资源的实际状态，并自动修正与声明状态之间的任何漂移。Terraform 需要手动运行 `terraform plan` 来检测漂移，并运行 `terraform apply` 来修复漂移，因此 Crossplane 的方法更适合 GitOps 工作流。

</details>
