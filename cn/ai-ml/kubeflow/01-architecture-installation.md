# 第 1 部分：Kubeflow 架构与在 EKS 上安装

> **审查基线**：Community Distribution 26.03.1；Dashboard 2.0.0；KFP 2.16.1
> **最后更新**：September 12, 2026
> **验证**：使用 kubectl 1.36.2 / Kustomize 5.8.1 在本地渲染了 Profile overlay。未执行 EKS 安装或 AWS 身份流程。

## 准备环境

在选择命令之前先选择发行版版本。记录 EKS/Kubernetes 版本、节点架构、CNI、存储类、身份提供商和所需组件。`Kubernetes 1.34+` 并非无条件的支持保证。

26.03.1 版本报告 Kubernetes 1.36 CI 覆盖以及使用 Kind 0.32+。这并不认证每一种 EKS add-on 组合。其 README 警告，某些镜像可能不支持 ARM64。渲染需要带有 Kustomize 的 kubectl，或该发行版指定的独立 Kustomize；应用资源还需要目标集群、权限和就绪的依赖项。

## 什么是 Kubeflow？

Kubeflow 由独立发布的 ML 组件组成。Community Distribution 将其版本和共享服务组装在一起。一些工作负载使用 CRD；其他操作使用应用程序 API、数据库和对象存储。Dashboard 是 UI 入口点，而非调度器或通用分发器。

### CNCF 毕业 — August 17, 2026

[CNCF 公告](https://www.cncf.io/announcements/2026/08/17/cncf-announces-kubeflows-graduation-solidifying-the-standard-for-cloud-native-ai-operations/)记录了毕业、独立安全审计和正式治理。这支持对项目成熟度的评估，但不能替代威胁建模、租户隔离测试或特定部署的合规性评估。

## 发布模型和当前基线

该发行版使用 `YY.MM.patch`，计划每年大约两个基础版本，并将社区支持描述为约六个月内尽力而为。这不是供应商支持 SLA。

[26.03.1 版本](https://github.com/kubeflow/community-distribution/releases/tag/26.03.1)于 June 15, 2026 发布，其[带标签的清单](https://github.com/kubeflow/community-distribution/blob/26.03.1/README.md)提供以下基线：

| 组件 | 捆绑版本 |
| --- | --- |
| Dashboard / Profile Controller / 访问管理 | 2.0.0 |
| Pipelines | 2.16.1 |
| Notebooks v1 | 1.11.0 |
| Trainer v2 / 旧版 Training Operator | 2.2.0 / 1.9.2 |
| Katib | 0.19.0 |
| KServe / Models Web Application | 0.18.0 / 0.18.0 |
| Hub / Spark Operator | 0.3.9 / 2.5.0 |
| Istio / Knative | 1.30.1 / 1.22.0 |
| cert-manager / Dex / oauth2-proxy | 1.20.2 / 2.45.1 / 7.15.2 |

该版本将 Workspaces（Notebooks v2）描述为 beta；这并不取代稳定的 Notebooks v1 行。旧版 Training Operator 和 Trainer v2 使用不同的 API 并存。在编写训练作业之前，请检查已安装的 CRD 和运行时定义。

## 组件架构

![Kubeflow 架构：将已认证的 UI 访问、应用程序 API 与存储，以及由 Profile 和工作负载控制器执行的 Kubernetes 协调分开。](../../.gitbook/assets/en-ai-ml-kubeflow-01-architecture-installation-0.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-kubeflow-01-architecture-installation-0.html)

| 边界 | 提供 | 仍需配置 |
| --- | --- | --- |
| 身份提供商、oauth2-proxy、gateway | 浏览器认证和受信任的身份转发 | OIDC 客户端、TLS、受信任的请求头、机器到机器认证 |
| Dashboard 和组件 Web 应用 | 导航和应用程序界面 | 每个 API 的授权和 Service 身份 |
| Profile Controller 和访问管理（KFAM） | Namespace 所有权、所有者/贡献者访问、生成的 RBAC 和 Istio 策略 | 配额、网络隔离、工作负载权限、存储和 AWS 权限 |
| 组件控制器 | 对受支持 Kubernetes 资源的协调 | 准入、调度、依赖项和状态 |
| KFP API 和持久化 | Pipeline/运行/实验操作、元数据和工件 | 数据库/对象存储可用性、授权和备份 |

集群范围的 `Profile` 具有一个所有者并管理一个 Namespace；贡献者通过访问管理进行处理。Dashboard 2.0.0 仅在 `spec.resourceQuotaSpec.hard` 非空时创建其 `ResourceQuota`。省略配额不会产生默认资源上限；清空该字段会移除此控制器管理的配额。

由 Profile 生成的 RBAC 和 Istio `AuthorizationPolicy` 不提供完整的租户隔离。NetworkPolicy 执行、Pod 权限、存储访问、AWS IAM 和应用程序授权仍各自独立。随 Profile overlay 捆绑的 NetworkPolicy 保护的是该控制器/访问管理 Service，而不是每个用户 Namespace。

KFP 的 Pipeline、Run 和 Experiment 概念并不普遍是 CRD。可选的 Kubernetes Native API 模式会添加 `Pipeline` 和 `PipelineVersion` CRD。KFP Experiment 和 Katib Experiment 是不同的资源。

### Profile 示例

这会声明一个所有者和一个显式配额。它不是安装命令，也不是完整的隔离策略。

```yaml
apiVersion: kubeflow.org/v1
kind: Profile
metadata:
  name: team-a
spec:
  owner:
    kind: User
    name: owner@example.com
  resourceQuotaSpec:
    hard:
      requests.cpu: "8"
      requests.memory: 32Gi
      requests.nvidia.com/gpu: "2"
      persistentvolumeclaims: "10"
```

控制器拒绝接管所有权不匹配的现有 Namespace。其 Namespace owner reference 也使删除具有重要影响：删除 Profile 可能会删除所属的 Namespace 及其资源。在迁移至 Dashboard v2 期间，请遵循特定版本对旧控制器资源的移除步骤；保留 Profile CRD、Profile 对象和用户 Namespace。

## 在 EKS 上的安装路径

| 路径 | 证据和限制 |
| --- | --- |
| Community Distribution 26.03.1 | 已审查的社区 bundle；为此版本配置 EKS 网络、存储、ingress 和身份 |
| `awslabs/kubeflow-manifests` | 已检查的最新已发布版本：`v1.7.0-aws-b1.0.3`（September 1, 2023）。其发布页面称新安装会失败，因为旧 OIDC 镜像已被移除 |
| 供应商支持的发行版 | 评估其自身的版本矩阵、支持、集成和迁移路径 |

[AWS 发布警告](https://github.com/awslabs/kubeflow-manifests/releases/tag/v1.7.0-aws-b1.0.3)意味着旧 manifest/Terraform 演练并不是经过验证的 26.03.1 安装方案。仅凭仓库活跃度并不能改变该版本的兼容性。

历史 AWS overlay 描述了 Cognito、RDS 和 S3 集成。它们可以减少对自托管身份、数据库和对象存储服务的运维，但不是可互换的默认值：issuer/claim 映射、数据库兼容性、网络、IAM、成本和迁移仍然重要。在将旧 overlay 与新版本结合使用之前，请先验证它们。

### 应用前渲染

以下命令获取已审查的版本，并且仅渲染其 Profile controller overlay。它们会创建本地文件，但不会连接到 Kubernetes：

```bash
git clone --depth 1 --branch 26.03.1 \
  https://github.com/kubeflow/community-distribution.git kubeflow-26.03.1
cd kubeflow-26.03.1
kubectl kustomize \
  applications/dashboard/upstream/profile-controller/overlays/kubeflow \
  > profile-controller.rendered.yaml
```

已审查的 overlay 生成了 14 个资源，包括 Profile CRD、RBAC、Service，以及位于 `kubeflow` 中的 `profiles-deployment`。其容器使用 Dashboard 2.0.0 Profile Controller 和访问管理镜像。此 overlay 不会创建 `kubeflow` Namespace，并且需要其 Istio/NetworkPolicy 依赖项。

安装时，请遵循固定版本的逐组件顺序。检查已渲染的资源，建立所需的 CRD，等待控制器/webhook，然后应用自定义资源。应诊断准入或字段所有权错误，而不是反复强制解决冲突。渲染成功既不能证明 API 准入，也不能证明 EKS 部署可用。

## IAM 访问模式：IRSA、KFPv2 和 Pod Identity

[当前 KFP 对象存储指南](https://www.kubeflow.org/docs/components/pipelines/operator-guides/configure-object-store/)记录了 S3 与 IRSA 以及 launcher `credentials.fromEnv: true` 的用法。旧 AWS 发行版中“仅 KFPv1”IRSA 的说明，并非当前 KFPv2 的普遍限制。

在 KFP 2.16.1 中，`fromEnv` 委托给 Go Cloud 的 bucket opener。除非指定 SDK override，否则其固定的 `gocloud.dev` 0.40.0 默认使用 AWS SDK v2 凭证链。这比读取静态 access-key 环境变量的范围更广。

配置 Pipeline 执行 ServiceAccount，以及每个访问工件的组件；当其对象存储配置要求时，也包括 API server。检查实际容器 SDK/provider 支持、bucket 前缀和 KMS 权限。IRSA 需要匹配的 role trust 和投影凭证，而不仅是 annotation。Pod Identity 还需要受支持的 EKS 环境、agent、association 和 SDK 支持；本次审查未运行该集成。

Dashboard 的 `AwsIamForServiceAccount` Profile plugin 并非 Pod Identity 开关：它会为 `default-editor` 添加 annotation，并且可以更新 IAM role 的 trust policy。需考虑控制器权限和 trust 变更。上面的示例并未启用该 plugin。请使用具有范围限制访问权限的工作负载身份，而不要将历史 IAM-user/static-key 变通方案复制到新部署中。

## 为什么要在 EKS 而不是托管替代方案上运行？

EKS 适合具备 Kubernetes 运维能力、需要共享工具、自定义训练运行时或特定调度和服务行为的团队。团队拥有控制器、CRD、租户边界、恢复、容量和升级的责任。

SageMaker AI 可以减少基础设施运维，但不会消除应用程序、数据、IAM 或模型质量责任。比较实际所需的服务和部署模式。

## 来源和验证

本次审查检查了带标签的发行版 manifest、Dashboard 2.0.0 Profile 代码以及 KFP 2.16.1 对象存储代码。Profile overlay 已在本地渲染，示例已根据其 CRD schema 进行检查。这并不能证明端到端认证、隔离或工件访问。

- [Dashboard Profile controller](https://github.com/kubeflow/dashboard/blob/v2.0.0/components/profile-controller/controllers/profile_controller.go)
- [Dashboard AWS Profile plugin](https://github.com/kubeflow/dashboard/blob/v2.0.0/components/profile-controller/controllers/plugin_iam.go)
- [KFP 对象存储实现](https://github.com/kubeflow/pipelines/blob/2.16.1/backend/src/v2/objectstore/object_store.go)

## 后续步骤

继续阅读[第 2 部分：Pipelines](02-pipelines.md)。

[返回主页](README.md)

## 测验

尝试[主题测验](../../quizzes/ai-ml/kubeflow/01-architecture-installation-quiz.md)。
