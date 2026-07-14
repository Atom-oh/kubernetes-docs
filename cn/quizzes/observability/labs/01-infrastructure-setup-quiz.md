# 可观测性实验第 1 部分：基础设施设置测验

> **最后更新**: February 22, 2026

测试你对可观测性端到端实验第 1 部分中介绍的基础设施设置概念的理解。

---

1. 在多 Cluster EKS 架构中，Managed Cluster 与 Service Cluster 的主要角色差异是什么？
   - A) Managed Cluster 运行应用程序工作负载，而 Service Cluster 仅处理网络
   - B) Managed Cluster 托管可观测性和平台工具，而 Service Cluster 运行应用程序工作负载
   - C) Service Cluster 管理所有 Cluster，而 Managed Cluster 用于测试
   - D) 两者没有功能差异；可以互换使用

<details>
<summary>显示答案</summary>

**答案：B) Managed Cluster 托管可观测性和平台工具，而 Service Cluster 运行应用程序工作负载**

**说明：**
在多 Cluster 架构中，Managed Cluster（通常称为管理或平台 Cluster）托管可观测性栈、GitOps 工具（ArgoCD）和平台组件等共享服务。Service Cluster 运行实际的应用程序工作负载。这种分离可提供更好的资源隔离和安全边界，并允许平台服务与应用程序工作负载独立扩缩容。

</details>

---

2. 对于 EKS 工作负载，为什么 IRSA（IAM Roles for Service Accounts）比使用 IAM instance profiles 更受推荐？
   - A) IRSA 的配置速度比 instance profiles 更快
   - B) IRSA 遵循最小权限原则，提供 Pod 级 IAM 权限
   - C) AWS 已弃用 instance profiles
   - D) IRSA 允许每个 Pod 使用无限数量的 IAM policies

<details>
<summary>显示答案</summary>

**答案：B) IRSA 遵循最小权限原则，提供 Pod 级 IAM 权限**

**说明：**
IRSA（IAM Roles for Service Accounts）通过将 IAM role 与 Kubernetes ServiceAccount 关联，实现细粒度的 Pod 级 IAM 权限。与向 Node 上所有 Pod 授予相同权限的 instance profiles 不同，IRSA 遵循最小权限原则，允许每个工作负载仅拥有其所需的特定权限。这可改善安全态势，并使权限审核和管理更加容易。

</details>

---

3. 在 EKS Cluster 预置方面，选择 Terraform 而非 eksctl 时的一项关键权衡是什么？
   - A) Terraform 完全无法创建 EKS Cluster
   - B) Terraform 提供更好的状态管理和基础设施即代码实践，但学习曲线更陡峭
   - C) eksctl 更适合生产环境
   - D) Terraform 仅适用于 AWS GovCloud Region

<details>
<summary>显示答案</summary>

**答案：B) Terraform 提供更好的状态管理和基础设施即代码实践，但学习曲线更陡峭**

**说明：**
Terraform 提供强大的状态管理、漂移检测、依赖关系图，并使用声明式 HCL 语法跨多个云提供商工作。不过，它要求学习 HCL 并理解 Terraform 概念。eksctl 专为 EKS 构建，提供更简单的 YAML 配置和更快的 Cluster 创建速度，但在复杂基础设施管理方面灵活性较低。对于基础设施即代码实践和状态管理至关重要的生产环境，通常更倾向于使用 Terraform。

</details>

---

4. 在生产可观测性设置中，为什么 Aurora PostgreSQL 使用 writer/reader instance 配置？
   - A) 为了降低许可证成本
   - B) 为了提供高可用性，并将读取密集型可观测性查询与写入操作分离
   - C) Aurora 仅支持这种配置
   - D) 仅为了启用跨 Region 复制

<details>
<summary>显示答案</summary>

**答案：B) 为了提供高可用性，并将读取密集型可观测性查询与写入操作分离**

**说明：**
Aurora PostgreSQL 的 writer/reader 配置可将写入操作（指标采集、日志存储）与读取操作（仪表板查询、告警查询）分离。可观测性工作负载通常是读取密集型的，需要持续刷新仪表板和评估告警。reader instance 可处理这些查询，而不会影响写入性能。此配置还可提供高可用性——如果 writer 发生故障，可自动提升一个 reader，从而最大限度地减少停机时间。

</details>

---

5. 创建 Amazon Managed Service for Prometheus (AMP) workspace 时，必须配置哪些基本组件？
   - A) 只需要 workspace 名称
   - B) workspace、具有 remote write 权限的 IAM role，以及用于安全访问的 VPC endpoint
   - C) 只需要用于存储的 S3 bucket 配置
   - D) workspace 和强制性的 CloudWatch 集成

<details>
<summary>显示答案</summary>

**答案：B) workspace、具有 remote write 权限的 IAM role，以及用于安全访问的 VPC endpoint**

**说明：**
设置 AMP 时，需要创建一个 workspace（Prometheus 数据的逻辑容器），为数据采集配置具有 `aps:RemoteWrite` 权限的 IAM role，并可选择设置 VPC endpoint 以实现私有网络访问。IAM role 与 IRSA 结合使用，以允许采集器进行身份验证并写入指标。VPC endpoint 可确保流量不经过公网，从而提高安全性并降低延迟。

</details>

---

6. 可以使用哪些方法将 Amazon Managed Grafana (AMG) 连接到数据源？
   - A) 只能通过 Grafana UI 手动配置
   - B) AWS 数据源配置、Grafana API 预置，或 Terraform/CloudFormation
   - C) 只能通过 AWS CLI 命令
   - D) 无需配置即可自动发现数据源

<details>
<summary>显示答案</summary>

**答案：B) AWS 数据源配置、Grafana API 预置，或 Terraform/CloudFormation**

**说明：**
AMG 支持多种数据源配置方法：AWS 原生数据源配置（可自动处理 AMP、CloudWatch、X-Ray 等 AWS 服务的身份验证）、基于 Grafana API 的预置以进行编程式设置，以及 Terraform 或 CloudFormation 等基础设施即代码工具。这种灵活性使团队能够选择最适合其工作流程的方法，无论是由 GitOps 驱动的自动化，还是初始设置期间的手动配置。

</details>

---

7. 在多 Cluster 设置中，向 ArgoCD 注册 Service Cluster 时需要哪些设置？
   - A) 只需要 Cluster endpoint URL
   - B) Cluster endpoint、身份验证凭证（ServiceAccount token 或 IAM）以及 Cluster 名称/label
   - C) 只需要 kubeconfig 文件路径
   - D) 两个 Cluster 位于同一 VPC 后，Cluster 注册会自动完成

<details>
<summary>显示答案</summary>

**答案：B) Cluster endpoint、身份验证凭证（ServiceAccount token 或 IAM）以及 Cluster 名称/label**

**说明：**
向 ArgoCD 注册外部 Cluster 需要该 Cluster 的 API server endpoint、身份验证凭证（具有适当 RBAC 权限的 ServiceAccount token，或适用于 EKS 的基于 IAM 的身份验证），以及 Cluster 名称和 labels 等元数据。Cluster 名称和 labels 用于在 ApplicationSets 中定位 Deployments。对于 EKS，建议通过 IRSA 使用基于 IAM 的身份验证，因为这样可避免管理长期有效的 token。

</details>

---

8. 应如何将 Amazon OpenSearch Service domain 与 EKS 集成以存储日志？
   - A) 无法将 OpenSearch 与 EKS 结合使用
   - B) 为日志采集器使用 VPC endpoint、细粒度访问控制和基于 IRSA 的身份验证
   - C) 只能通过使用 IP allowlist 的公共 endpoint
   - D) OpenSearch 集成需要 CloudWatch 作为中介

<details>
<summary>显示答案</summary>

**答案：B) 为日志采集器使用 VPC endpoint、细粒度访问控制和基于 IRSA 的身份验证**

**说明：**
要将 OpenSearch 与 EKS 安全集成，请以 VPC 模式部署 OpenSearch，并使用 VPC endpoint 实现私有访问。启用细粒度访问控制以管理 index 级权限。为日志采集器（如 FluentBit 或 Grafana Alloy）配置 IRSA，以便使用 IAM role 进行身份验证。此设置可确保日志在 VPC 内安全传输、在 index 级别控制访问，并且身份验证遵循 AWS 安全最佳实践。

</details>

---

9. 在 Amazon MWAA (Managed Workflows for Apache Airflow) 环境中，S3 DAG bucket 的作用是什么？
   - A) 它仅存储 Airflow 执行日志
   - B) 它存储 MWAA 加载以定义和执行工作流的 DAG 文件、plugin 和 requirements
   - C) 它作为 MWAA 数据库的备份
   - D) 它为任务输出提供临时存储

<details>
<summary>显示答案</summary>

**答案：B) 它存储 MWAA 加载以定义和执行工作流的 DAG 文件、plugin 和 requirements**

**说明：**
S3 DAG bucket 是 MWAA 工作流定义的事实来源。它存储用于定义工作流的 DAG（Directed Acyclic Graph）Python 文件、用于扩展 Airflow 功能的自定义 plugin，以及用于额外 Python 依赖项的 requirements.txt。MWAA 会持续同步此 bucket，自动检测并加载新增或更新的 DAG。这种基于 S3 的方法支持 GitOps 工作流，其中 DAG 变更通过 CI/CD pipeline 进行部署。

</details>

---

10. 为什么 Argo Rollouts 安装在 Service Cluster 而不是 Managed Cluster 上？
    - A) Argo Rollouts 无法跨 Cluster 通信
    - B) Rollouts controller 需要直接访问其管理的工作负载，以进行 canary/blue-green Deployment
    - C) 在较少的 Cluster 上安装可降低许可证成本
    - D) Managed Cluster 不支持安装 CRD

<details>
<summary>显示答案</summary>

**答案：B) Rollouts controller 需要直接访问其管理的工作负载，以进行 canary/blue-green Deployment**

**说明：**
Argo Rollouts controller 通过 canary、blue-green 或其他 Deployment 策略管理应用程序的渐进式交付。它们需要直接访问运行工作负载的 Cluster 中的 ReplicaSet、Service 和其他资源，以便进行修改。尽管 ArgoCD 可以从中心位置进行部署，但 Rollouts controller 会在 Deployment 期间主动管理流量迁移和 Pod 扩缩容，因此必须与其控制的工作负载一同运行。这就是为什么 Rollouts 安装在每个 Service Cluster 上。

</details>
