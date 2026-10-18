# EKS 上的 Kubeflow 深入解析

> **审查基线**：Kubeflow 社区发行版 26.03.1
> **已检查的最新发行版**：社区发行版 26.03.1；各组件的发行版本单独跟踪
> **最近审查日期**：2026 年 10 月 12 日

## 概述

Kubeflow 提供基于 Kubernetes 的工具，用于 ML 流水线、Notebook、调优、训练和服务部署。社区发行版整合了各组件的修订版本、共享服务和仪表板；各个项目也有自己的发行版本和安装要求。

本系列以该发行版中的 KFP 2.16.1 和 KServe 0.18.0 作为复现基线。

KFP 2.17.2 和 KServe 0.21.0 是较新的独立发行版本。它们未包含在社区发行版 26.03.1 中，本指南也未确定它们彼此兼容。请同时检查发行版锁定的组件清单和当前组件发行版本。

CNCF [于 2026 年 8 月 17 日宣布 Kubeflow 毕业](https://www.cncf.io/announcements/2026/08/17/cncf-announces-kubeflows-graduation-solidifying-the-standard-for-cloud-native-ai-operations/)。这肯定了项目的成熟度和治理情况，包括通过独立安全审计。但这并不代表对特定 EKS 部署的安全性或法规合规性作出认证。

## 组件概览

| 组件 | 用途 | API 或概念 | 指南 |
| --- | --- | --- | --- |
| 仪表板、Profiles、访问管理 | UI 导航、命名空间所有权和成员管理 | 集群范围的 `Profile`；可选配额 | [第 1 部分](01-architecture-installation.md) |
| Pipelines | 编译和执行工作流；跟踪运行和制品 | Pipeline/Run/Experiment API；可选的 Kubernetes Native API 模式会添加 `Pipeline`/`PipelineVersion` CRD | [第 2 部分](02-pipelines.md) |
| Notebooks | 用户 Notebook 工作负载 | `Notebook`；镜像和 PVC 配置 | [第 3 部分](03-notebooks.md) |
| Katib | 超参数搜索和试验 | `Experiment`、`Trial`、`Suggestion` CRD | [第 4 部分](04-katib.md) |
| Trainer | 使用已配置运行时进行分布式训练 | `TrainJob`、`TrainingRuntime`、`ClusterTrainingRuntime` | [第 5 部分](05-training-operator.md) |
| KServe | 模型推理服务 | `InferenceService`；特定模式的依赖项 | [第 6 部分](06-kserve.md) |

本概览涵盖本指南的范围，并非整个发行版。26.03.1 发行版还包括 Hub/模型注册表和 Spark Operator。KFP Experiment 并不是 Katib Experiment CRD。

![Kubeflow 组件图，区分仪表板导航与显式配置的流水线、调优、训练和模型部署集成。](../../.gitbook/assets/en-ai-ml-kubeflow-readme-0.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-kubeflow-readme-0.html)

仪表板提供指向各组件 UI 的链接。只有在其实现明确提交受支持的训练资源时，Pipelines 和 Katib 才会使用 Trainer。将训练后的制品连接到 KServe 需要单独的部署步骤；图表并未表示模型会自动晋级。

## 为什么在 EKS 上运行

现有 EKS 平台可以让 ML 工作负载共享容量管理、存储集成、工作负载身份和监控。兼容性仍取决于 Kubernetes 版本、CPU 架构、镜像、网络、存储驱动程序和身份验证。仅符合 Kubernetes 标准并不足够；发行说明指出 ARM64 镜像覆盖并不完整。

团队仍需负责组件/CRD 升级、租户授权、持久化数据、凭证和恢复。[Amazon SageMaker AI](../sagemaker-ai/README.md) 可减轻部分基础设施管理责任，但数据访问、应用程序正确性、模型质量和成本控制仍需要明确负责人。应根据所需接口、运维能力和工作负载限制进行选择。

## 当前涵盖内容

1. [第 1 部分：EKS 上的架构和安装](01-architecture-installation.md)：当前社区发行版、旧版 AWS 发行版的限制、Profiles、身份和清单渲染。
2. [第 2 部分：Pipelines](02-pipelines.md)：SDK v2、编译、执行和制品存储。
3. [第 3 部分：Notebooks](03-notebooks.md)：工作负载、Profiles、存储和 GPU 放置。
4. [第 4 部分：Katib](04-katib.md)：实验、试验、搜索和提前停止。
5. [第 5 部分：Trainer](05-training-operator.md)：旧版 Training Operator 和 Trainer v2 API。
6. [第 6 部分：KServe](06-kserve.md)：推理资源、部署模式和滚动发布。

请使用各章节对应的组件基线。选择安装方案前，请检查 [26.03.1 发行版](https://github.com/kubeflow/community-distribution/releases/tag/26.03.1)、[锁定的组件清单](https://github.com/kubeflow/community-distribution/blob/26.03.1/README.md)、[KFP 2.17.2](https://github.com/kubeflow/pipelines/releases/tag/2.17.2) 和 [KServe 0.21.0](https://github.com/kserve/kserve/releases/tag/v0.21.0)。
