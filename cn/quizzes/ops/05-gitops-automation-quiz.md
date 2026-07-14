# GitOps 自动化测验

> **相关文档**: [GitOps 自动化](../../ops/05-gitops-automation.md)

## 选择题

### 1. 在 Terraform 自动化的语境中，Atlantis 是什么？

- A) 云提供商
- B) 用于 Terraform 的 pull request 自动化工具
- C) Terraform module registry
- D) 状态文件加密服务

<details>
<summary>显示答案</summary>

**答案：B) 用于 Terraform 的 pull request 自动化工具**

**解释：**
Atlantis 是一个自托管应用程序，会监听 Terraform pull request，并自动运行 `terraform plan` 和 `apply`。它会以 PR 评论的形式提供 plan 输出，并在应用变更前强制执行审批工作流。

</details>

### 2. 与自托管 Terraform 相比，Terraform Cloud 的一个关键优势是什么？

- A) 免费无限使用
- B) 托管状态、运行和协作功能
- C) 更快的执行速度
- D) 支持更多 provider

<details>
<summary>显示答案</summary>

**答案：B) 托管状态、运行和协作功能**

**解释：**
Terraform Cloud 提供托管的远程状态存储、运行执行、团队协作、策略执行（Sentinel）以及私有 module registry。与自托管设置相比，这些托管功能降低了运维开销。

</details>

### 3. FluxCD 在架构上与 ArgoCD 有何不同？

- A) FluxCD 没有 UI
- B) FluxCD 使用基于 pull 的分布式架构，没有中央服务器
- C) FluxCD 只支持 Helm
- D) FluxCD 需要数据库

<details>
<summary>显示答案</summary>

**答案：B) FluxCD 使用基于 pull 的分布式架构，没有中央服务器**

**解释：**
FluxCD 直接在每个 cluster 中运行 controller，从 git 拉取内容，而 ArgoCD 使用集中式服务器模型。FluxCD 的方法更轻量，并且在多 cluster 场景中无需中央 hub 即可自然扩展。

</details>

### 4. Flux Image Automation Controller 的作用是什么？

- A) 构建 container image
- B) 扫描 registry，并用新的 image tag 更新 git
- C) 将 image 部署到 Kubernetes
- D) 管理 image pull secret

<details>
<summary>显示答案</summary>

**答案：B) 扫描 registry，并用新的 image tag 更新 git**

**解释：**
Image Automation Controller 会监视 container registry 中的新 image tag，然后自动将更新提交到 git repository。这样在推送新 image 时即可实现完全自动化部署，同时保持 GitOps 原则。

</details>

### 5. 在 Atlantis workflow 中，当 PR 被批准并合并时会发生什么？

- A) Terraform plan 会自动运行
- B) Atlantis 在合并后的代码上运行 terraform apply
- C) PR 会被关闭且不执行任何操作
- D) 会创建一个新 branch

<details>
<summary>显示答案</summary>

**答案：B) Atlantis 在合并后的代码上运行 terraform apply**

**解释：**
在配置了 auto-apply 或经过明确批准后，Atlantis 会在 PR 合并后运行 `terraform apply`。这确保基础设施变更只有在 code review 和批准后才会应用，从而保持变更控制。

</details>

### 6. AIOps 在 GitOps workflow 中的一个关键好处是什么？

- A) 消除对 git 的需求
- B) 自动化 anomaly detection 和响应建议
- C) 更快的 container build
- D) 降低存储成本

<details>
<summary>显示答案</summary>

**答案：B) 自动化 anomaly detection 和响应建议**

**解释：**
AIOps 应用机器学习来检测 metrics 和 logs 中的异常、关联事件，并推荐或自动执行响应。在 GitOps 中，这可以包括为扩缩容变更或流量权重调整自动生成 PR。

</details>

### 7. AIOps 如何在 blue/green deployments 中自动化流量权重变更？

- A) 通过直接修改 load balancer 设置
- B) 通过检测异常并创建 PR，以更新 git 中的权重配置
- C) 通过重启失败的 pods
- D) 通过更改 DNS 记录

<details>
<summary>显示答案</summary>

**答案：B) 通过检测异常并创建 PR，以更新 git 中的权重配置**

**解释：**
AIOps 可以监控 metrics，检测 green deployment 中的问题（错误率、延迟），并自动创建 PR 将流量权重切回 blue。这样既能启用自动化事件响应，又能保持 GitOps 原则。

</details>

### 8. Flux 的 GitRepository resource 的用途是什么？

- A) 创建 git repository
- B) 定义 Flux 监控其变更的 git source
- C) 将 Kubernetes resource 备份到 git
- D) 管理 git credential

<details>
<summary>显示答案</summary>

**答案：B) 定义 Flux 监控其变更的 git source**

**解释：**
GitRepository 是一个 Flux custom resource，用于指定 git repository URL、branch 和轮询间隔。Flux controller 会监视这些 source，并在检测到变更时触发 reconciliation。

</details>

### 9. 比较 FluxCD 和 ArgoCD 时，哪项陈述是准确的？

- A) ArgoCD 通过其 Project model 提供更好的 multi-tenancy
- B) FluxCD 有更丰富的内置 UI
- C) ArgoCD 使用 GitOps，而 FluxCD 不使用
- D) FluxCD 需要外部数据库

<details>
<summary>显示答案</summary>

**答案：A) ArgoCD 通过其 Project model 提供更好的 multi-tenancy**

**解释：**
ArgoCD 的 Project resource 通过对 repository、cluster 和 namespace 的细粒度访问控制，提供强大的 multi-tenancy。FluxCD 通过 namespace 隔离实现 multi-tenancy，但控制粒度较低。

</details>

### 10. 在 Terraform Cloud 中，Sentinel policy 是什么？

- A) 备份策略
- B) 用于治理和合规的 policy-as-code framework
- C) 状态加密方法
- D) module 版本控制系统

<details>
<summary>显示答案</summary>

**答案：B) 用于治理和合规的 policy-as-code framework**

**解释：**
Sentinel 是 HashiCorp 的 policy-as-code framework，会在 Terraform 应用变更前强制执行规则。策略可以强制要求标签、限制 instance type、要求加密，或执行任何自定义合规要求。

</details>
