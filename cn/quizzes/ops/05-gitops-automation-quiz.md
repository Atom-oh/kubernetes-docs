# GitOps 自动化测验

> **相关文档**：[GitOps 自动化](../../ops/05-gitops-automation.md)

## 选择题

### 1. 在 Terraform 自动化中，Atlantis 是什么？

- A) 云服务提供商
- B) 用于 Terraform 的拉取请求自动化工具
- C) Terraform 模块注册表
- D) State 文件加密服务

<details>
<summary>显示答案</summary>

**答案：B) 用于 Terraform 的拉取请求自动化工具**

**说明：**
Atlantis 是一个自托管应用，会监听 Terraform 拉取请求并自动运行 `terraform plan` 和 `apply`。它会将 plan 输出作为 PR 评论提供，并在应用变更前强制执行审批工作流。

</details>

### 2. 相比自托管 Terraform，HCP Terraform 的一项主要优势是什么？

- A) 免费且不限制使用量
- B) 提供托管式 State、运行执行和协作功能
- C) 执行速度更快
- D) 支持更多 Provider

<details>
<summary>显示答案</summary>

**答案：B) 提供托管式 State、运行执行和协作功能**

**说明：**
HCP Terraform 提供托管式远程 State 存储、运行执行、团队协作、策略执行（Sentinel）和私有模块注册表。与自托管方案相比，这些托管功能可以减少运维负担。

</details>

### 3. FluxCD 与 ArgoCD 的架构有何不同？

- A) FluxCD 没有 UI
- B) 两者都使用协调机制，但 API、控制器和 UI 选择不同
- C) FluxCD 只支持 Helm
- D) FluxCD 必须使用数据库

<details>
<summary>显示答案</summary>

**答案：B) 两者都使用协调机制，但 API、控制器和 UI 选择不同**

**说明：**
Flux 使用 GitRepository、Kustomization 等由各控制器定义的 API。Argo CD 也包含多个组件，并支持不同的部署拓扑。资源用量和多集群行为取决于具体配置，不能对两者的架构作普遍排名。

</details>

### 4. Flux Image Automation Controller 会做什么？

- A) 构建容器镜像
- B) 扫描镜像注册表，并将新的镜像标签更新到 Git
- C) 将镜像部署到 Kubernetes
- D) 管理镜像拉取 Secret

<details>
<summary>显示答案</summary>

**答案：B) 扫描镜像注册表，并将新的镜像标签更新到 Git**

**说明：**
image-reflector-controller 会扫描镜像注册表并评估 ImagePolicy。另一个独立的 image-automation-controller 会将这些选择写入带标记的文件并提交到 Git。新镜像推送后，这些能力可以支持全自动部署，同时遵循 GitOps 原则。

</details>

### 5. Atlantis 的常规 apply 和 merge 顺序是什么？

- A) 合并任何 PR 都会自动应用其中的 Terraform 变更
- B) 审查 PR plan、满足要求、明确应用已保存的 plan，然后再合并
- C) 先合并，再忽略已保存的 plan
- D) plan 成功就等同于已经 apply

<details>
<summary>显示答案</summary>

**答案：B) 审查 PR plan、满足要求、明确应用已保存的 plan，然后再合并**

**说明**：Atlantis 通过 PR 工作流执行 apply；单独合并 PR 并不会触发 apply。可选的自动合并功能会在 apply 成功后合并 PR。对于发生变更的提交，应重新审查或生成 plan；不要允许 PR 覆盖服务器强制执行的要求。

</details>

### 6. AIOps 在 GitOps 工作流中的一项主要优势是什么？

- A) 不再需要 Git
- B) 自动检测异常并提出响应建议
- C) 更快地构建容器
- D) 降低存储成本

<details>
<summary>显示答案</summary>

**答案：B) 自动检测异常并提出响应建议**

**说明：**
AIOps 使用机器学习检测指标和日志中的异常、关联事件，并建议或自动执行响应。在 GitOps 中，这可能包括自动创建 PR 来调整扩缩容配置或流量权重。

</details>

### 7. AIOps 如何自动调整蓝绿部署中的流量权重？

- A) 直接修改负载均衡器设置
- B) 检测异常并创建 PR，在 Git 中更新权重配置
- C) 重启故障 Pod
- D) 更改 DNS 记录

<details>
<summary>显示答案</summary>

**答案：B) 检测异常并创建 PR，在 Git 中更新权重配置**

**说明：**
AIOps 可以监控指标、检测绿色部署中的问题（例如错误率或延迟），并自动创建 PR，将流量权重切回蓝色部署。该提案仍需经过数据质量检查和授权审批，并由受约束的执行器重新检查当前状态、容量和目标健康状况。发现异常或新建 PR 本身都不构成调整流量的授权。

</details>

### 8. Flux 的 GitRepository 资源有什么用途？

- A) 创建 Git 仓库
- B) 定义 Flux 监视变更的 Git 源
- C) 将 Kubernetes 资源备份到 Git
- D) 管理 Git 凭证

<details>
<summary>显示答案</summary>

**答案：B) 定义 Flux 监视变更的 Git 源**

**说明：**
GitRepository 是 Flux 自定义资源，用于指定 Git 仓库 URL、分支和轮询间隔。Flux 控制器会监视这些源，并在检测到变更时触发协调。

</details>

### 9. 关于多租户，哪项说法准确？

- A) Argo CD 总是更安全，因为它有 AppProjects
- B) 仅使用 Flux Namespace 就能完成租户隔离
- C) 两者都需要有意配置源、身份、RBAC 和资源边界
- D) Image Automation 也会扫描漏洞

<details>
<summary>显示答案</summary>

**答案：C) 两者都需要有意配置源、身份、RBAC 和资源边界**

**说明**：AppProjects 和 Flux 的租户身份会约束协调过程的不同部分。两者都不会自动提供所有网络隔离、Kubernetes 授权或不可信代码隔离边界。应避免让两个控制器同时管理同一资源字段。

</details>

### 10. 在 HCP Terraform 中，Sentinel 策略是什么？

- A) 备份策略
- B) 用于治理和合规的 Policy as Code 框架
- C) State 加密方法
- D) 模块版本管理系统

<details>
<summary>显示答案</summary>

**答案：B) 用于治理和合规的 Policy as Code 框架**

**说明：**
Sentinel 是 HashiCorp 的 Policy as Code 框架，可在 Terraform apply 前强制执行规则。策略可以检查标签、实例类型、加密设置或其他可建模的要求。策略的实际效果取决于策略集的适用范围、强制级别，以及如何处理缺失值或未知值；一个示例并不会自动覆盖所有资源。

</details>
