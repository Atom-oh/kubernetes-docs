# Kubeflow 在 EKS 上的架构与安装测验

本测验检验你对 Kubeflow 组件架构、其 CNCF 毕业状态、Kubeflow Community Distribution 的发布模型、EKS 特定的安装模式，以及 Pipelines 工件存储的 IAM 访问模式的理解。

## 选择题

1. Kubeflow 于 2026 年 8 月 17 日在 CNCF 达成了什么里程碑？
   - A) 被接纳为 CNCF sandbox 项目
   - B) 从 sandbox 状态转为 incubating 状态
   - C) 在通过安全审计并成立指导委员会后毕业——CNCF 最高成熟度层级
   - D) 因不活跃而被 CNCF 归档

<details>
<summary>显示答案</summary>

**答案：C) 在通过安全审计并成立指导委员会后毕业——CNCF 最高成熟度层级**

**解释：**
Kubeflow 于 2023 年以 incubating 项目身份加入 CNCF，并在通过独立的第三方安全审计、为项目治理成立正式指导委员会后，[于 2026 年 8 月 17 日毕业](https://www.cncf.io/announcements/2026/08/17/cncf-announces-kubeflows-graduation-solidifying-the-standard-for-cloud-native-ai-operations/)。毕业是 CNCF 最高的成熟度层级。
</details>

2. Kubeflow Community Distribution 使用什么版本控制方案，并且大约多久发布一次基础版本？
   - A) 语义化版本控制（major.minor.patch），持续发布
   - B) 日历版本控制（YY.MM.patch），每年大约两次
   - C) 单一滚动的“latest”标签，没有离散版本
   - D) LTS 版本控制，每三年一次

<details>
<summary>显示答案</summary>

**答案：B) 日历版本控制（YY.MM.patch），每年大约两次**

**解释：**
Kubeflow Community Distribution 使用 YY.MM.patch 形式的日历版本控制，每年大约发布两个基础版本。撰写本文时，26.03 是最新的基础版本（此后已发布包含较新组件版本的 26.03.1 补丁）。
</details>

3. 在 Kubeflow 架构中，什么是“Kubeflow Profile”？
   - A) 用户个人的 dashboard 主题和布局偏好
   - B) 一个 Kubernetes namespace，加上 RBAC 绑定、资源配额和 Istio AuthorizationPolicy 对象，并由 Profile Controller 协调
   - C) 一个列出 cluster 已安装组件的 YAML 文件
   - D) 仅由托管 Kubeflow 供应商使用的计费结构

<details>
<summary>显示答案</summary>

**答案：B) 一个 Kubernetes namespace，加上 RBAC 绑定、资源配额和 Istio AuthorizationPolicy 对象，并由 Profile Controller 协调**

**解释：**
Kubeflow Profile 是多租户边界：一个 namespace 捆绑了 RBAC 绑定、配额和 Istio 授权策略，全部由 Profile Controller 根据单个 Profile custom resource 进行协调。其他组件（Notebooks、Pipelines、Katib）会在用户的 profile namespace 内创建其资源。
</details>

4. `awslabs/kubeflow-manifests` 使用哪三项 AWS 原生服务来替代 Kubeflow 默认的 Dex、cluster 内 MySQL 和 MinIO？
   - A) IAM、DynamoDB 和 EFS
   - B) Cognito、RDS 和 S3
   - C) Secrets Manager、Aurora Serverless 和 EBS
   - D) SSO、Redshift 和 Glacier

<details>
<summary>显示答案</summary>

**答案：B) Cognito、RDS 和 S3**

**解释：**
`awslabs/kubeflow-manifests` 使用 Amazon Cognito 替代 Dex 进行身份验证，使用 Amazon RDS 替代随附的 cluster 内 MySQL 来存储 Pipelines/Katib 元数据，并使用 Amazon S3 替代 MinIO 来存储 Pipelines 工件。基于 kustomize 的 manifest 部署和基于 Terraform 的部署都记录了这一模式。
</details>

5. 对于专门向 Kubeflow Pipelines Pod 授予 S3 访问权限的 IRSA 支持，特别是针对 KFPv2，其文档记录的历史是什么？
   - A) IRSA 一直完全支持 KFPv2，没有任何注意事项
   - B) 对于任何 Kubeflow Pipelines 版本，IRSA 从未在 EKS 上可用
   - C) IRSA 对 KFPv2 的支持在历史上较为滞后，期间文档记录了基于 IAM user 的变通方法；而 EKS Pod Identity 则是 IAM 到 Pod 绑定更广泛的发展方向
   - D) KFPv2 要求完全禁用 IAM 并使用匿名 S3 访问

<details>
<summary>显示答案</summary>

**答案：C) IRSA 对 KFPv2 的支持在历史上较为滞后，期间文档记录了基于 IAM user 的变通方法；而 EKS Pod Identity 则是 IAM 到 Pod 绑定更广泛的发展方向**

**解释：**
`kubeflow-manifests` 指南在历史上指出，IRSA 支持 KFPv1，但尚未支持 KFPv2，并建议使用具有静态凭证的专用 IAM user 作为临时变通方法。此外，EKS Pod Identity 已日益成为 EKS 上新 IAM 到 Pod 绑定的推荐默认机制——但 KFPv2 特定 Pod Identity 支持的当前状态应根据实时文档进行核实，而不应想当然地假定。
</details>

6. 根据本文讨论的“为何在 EKS 上运行而不是使用托管替代方案”的权衡，哪种条件最能支持在 EKS 上运行 Kubeflow，而不是使用 SageMaker 等完全托管的平台？
   - A) 团队希望永远避免接触 Kubernetes controller 或 CRD
   - B) 团队已经在 EKS 上运行混合工作负载，并希望 ML 共享相同的 node pool、autoscaling 和 observability stack
   - C) 团队没有任何现有的 Kubernetes 运维经验
   - D) 团队无论可移植性如何都希望获得绝对最低的运维开销

<details>
<summary>显示答案</summary>

**答案：B) 团队已经在 EKS 上运行混合工作负载，并希望 ML 共享相同的 node pool、autoscaling 和 observability stack**

**解释：**
当团队已在 EKS 上运行其他工作负载，且能够避免为 ML 维护第二套并行的运维模型时，在 EKS 上使用 Kubeflow 最具合理性——同时还需要可移植性/避免供应商锁定，或对训练/serving 内部机制进行细粒度控制。没有现有 Kubernetes 能力的团队，或者优先考虑最低运维开销的团队，通常更适合使用完全托管的平台。
</details>

## 简答题

7. 请用一句话解释 CNCF 毕业（于 2026 年 8 月 17 日宣布）表明 Kubeflow 的项目成熟度达到什么程度，并说出项目为实现该目标必须满足的一项具体要求。

<details>
<summary>显示答案</summary>

**答案：**
毕业表明 CNCF 项目已经证明具备生产级成熟度、广泛采用和健全治理；为实现毕业，Kubeflow 接受了独立的第三方安全审计，并为项目治理成立了正式指导委员会。完整详情请参阅 [CNCF 公告](https://www.cncf.io/announcements/2026/08/17/cncf-announces-kubeflows-graduation-solidifying-the-standard-for-cloud-native-ai-operations/)。
</details>

8. 在 EKS 上部署 Kubeflow 时，为什么 `awslabs/kubeflow-manifests` 部署模式会分别用 S3 和 Cognito 替代 cluster 内 MinIO 工件存储与随附的 Dex 身份验证？

<details>
<summary>显示答案</summary>

**答案：**
因为 EKS 已为两者提供托管、持久且与 IAM 集成的等效服务——S3 用于对象存储，Cognito 用于身份——而运行随附的 cluster 内替代方案意味着需要运维额外的有状态服务，这些服务重复了 AWS 已提供的功能，却未带来 Kubeflow 从自托管版本中特别需要的任何益处。
</details>

---

[返回学习材料](../../../ai-ml/kubeflow/01-architecture-installation.md) | [下一测验：Pipelines](./02-pipelines-quiz.md)
