# EKS 上的 Kubeflow 深入解析

> **审核基线**: Kubeflow Community Distribution 26.03.1
> **最后审阅**: September 12, 2026

## 概述

Kubeflow 提供基于 Kubernetes 的工具，用于 ML pipeline、notebook、调优、训练和服务。Community Distribution 汇集了组件修订版本、共享服务和仪表板；各个项目也有各自的发布版本和安装要求。

CNCF [于 2026 年 8 月 17 日宣布 Kubeflow 毕业](https://www.cncf.io/announcements/2026/08/17/cncf-announces-kubeflows-graduation-solidifying-the-standard-for-cloud-native-ai-operations/)。这认可了项目的成熟度和治理情况，包括独立的安全审计。但这并不认证特定 EKS 部署的安全性或法规合规性。

## 组件映射

| 组件 | 用途 | API 或概念 | 指南 |
| --- | --- | --- | --- |
| Dashboard、Profiles、访问管理 | UI 导航、namespace 所有权和成员资格 | 集群范围的 `Profile`；可选配额 | [第 1 部分](01-architecture-installation.md) |
| Pipelines | 编译和执行工作流；跟踪运行和 artifact | Pipeline/Run/Experiment APIs；可选 Kubernetes Native API 模式会添加 `Pipeline`/`PipelineVersion` CRD | [第 2 部分](02-pipelines.md) |
| Notebooks | 用户 notebook 工作负载 | `Notebook`；image 和 PVC 配置 | [第 3 部分](03-notebooks.md) |
| Katib | 超参数搜索和 trial | `Experiment`、`Trial`、`Suggestion` CRD | [第 4 部分](04-katib.md) |
| Trainer | 使用已配置 runtime 的分布式训练 | `TrainJob`、`TrainingRuntime`、`ClusterTrainingRuntime` | [第 5 部分](05-training-operator.md) |
| KServe | 模型推理服务 | `InferenceService`；特定模式的依赖项 | [第 6 部分](06-kserve.md) |

此映射涵盖本指南的范围，而非整个 distribution。26.03.1 版本还包括 Hub/model registry 和 Spark Operator。KFP Experiment 并非 Katib Experiment CRD。

![Kubeflow 组件映射，区分仪表板导航与显式配置的 pipeline、调优、训练和模型部署集成。](../../.gitbook/assets/en-ai-ml-kubeflow-readme-0.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-kubeflow-readme-0.html)

仪表板链接各组件 UI。只有当 Pipelines 和 Katib 的实现明确提交受支持的训练资源时，它们才会使用 Trainer。将训练产物连接到 KServe 需要单独的部署步骤；该图并不表示自动模型晋升。

## 为什么在 EKS 上运行

现有 EKS 平台可与 ML 工作负载共享容量管理、存储集成、工作负载身份和监控。兼容性仍取决于 Kubernetes 版本、CPU 架构、image、网络、存储 driver 和身份验证。仅 Kubernetes 一致性并不足够；发布文档指出 ARM64 image 覆盖范围不完整。

团队仍需负责组件/CRD 升级、租户授权、持久数据、凭证和恢复。[Amazon SageMaker AI](../sagemaker-ai/README.md) 减少了部分基础设施责任，但数据访问、应用程序正确性、模型质量和成本控制仍需要责任人。请根据所需接口、运维能力和工作负载约束进行选择。

## 当前涵盖内容

1. [第 1 部分：EKS 上的架构与安装](01-architecture-installation.md) — 当前社区版本、旧版 AWS distribution 的限制、Profiles、身份和 manifest 渲染。
2. [第 2 部分：Pipelines](02-pipelines.md) — SDK v2、编译、执行和 artifact 存储。
3. [第 3 部分：Notebooks](03-notebooks.md) — 工作负载、Profiles、存储和 GPU 放置。
4. [第 4 部分：Katib](04-katib.md) — experiment、trial、搜索和早停。
5. [第 5 部分：Trainer](05-training-operator.md) — 旧版 Training Operator 和 Trainer v2 APIs。
6. [第 6 部分：KServe](06-kserve.md) — 推理资源、部署模式和 rollout。

请使用每章的组件基线。在选择安装方式之前，请查看 [26.03.1 版本发布](https://github.com/kubeflow/community-distribution/releases/tag/26.03.1) 和 [固定版本清单](https://github.com/kubeflow/community-distribution/blob/26.03.1/README.md)。
