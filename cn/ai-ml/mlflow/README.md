# EKS 上的 MLflow 深入解析

> **审查基线**：MLflow 3.16.0
> **已检查的最新补丁**：MLflow 3.16.1（2026 年 9 月 17 日）
> **文档审查日期**：2026 年 10 月 12 日

## 概述

MLflow 提供实验跟踪、模型记录和注册、版本管理、GenAI 评估及追踪功能。追踪功能于 2.14.0 引入；3.x 扩展了 `LoggedModel`、评估和 UI 集成。版本 3.16.0 于 2026-09-04 发布。

补丁版本 3.16.1 随后于 2026-09-17 发布，并移除了随附的默认 basic-auth 管理员密码。下列示例使用 3.16.0 进行过检查，未在 3.16.1 上重新运行。MLflow 3.17.0（2026-10-07）是后续的次要版本，对于使用 SQL 后端的服务器，需要协调进行 SQL schema 升级；本系列不涵盖该版本。

您可以在本地将其与 SDK 和 SQLite 一起使用，也可以运行 HTTP 跟踪服务，并将 SQL 元数据存储和 artifact 存储分离。逻辑服务不必对应一个 Pod 或一个存储系统。本系列涵盖 Tracking、Registry 和 EKS 部署；但不验证所有 MLflow 功能或成功的 GPU 训练。

## 组件图

| 概念 | 解决的问题 | 深入解析 |
|---------|--------------------|-----------|
| **Tracking** | 记录并查询实验参数、指标、artifact、模型和 GenAI trace | [第 1 部分](01-tracking.md) |
| **Model Registry** | 为模型提供独立于任何单次训练运行的稳定、带版本的身份标识 | [第 2 部分](02-model-registry.md) |
| **EKS Deployment** | 在 EKS 上运行跟踪服务器、后端存储和 artifact 存储 | [第 3 部分](03-eks-deployment.md) |

![一个三阶段流水线图：MLflow Tracking（实验、运行、trace）输入到 Model Registry（已注册模型、别名），随后由处于本系列文档范围之外的 Serving 阶段进行解析。](../../.gitbook/assets/en-ai-ml-mlflow-readme-0.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-mlflow-readme-0.html)

## 为什么要在 EKS 上运行

这种权衡与本文档站点数据/ML 部分其他内容所述的一致：已经运行 EKS 的团队可以为 MLflow 的跟踪服务器复用集群中其他所有工作负载相同的部署、IAM（IRSA/Pod Identity）和可观测性模式，但代价是需要直接运行跟踪服务器、其后端数据库和 artifact 存储，而不是使用托管替代方案。

[SageMaker AI 指南](../sagemaker-ai/README.md)描述了一个 Qwen 对比设计。该示例具有单独的历史版本固定配置，并且由于其 DLC 已到达补丁终止期，目前阻止 GPU 执行。本系列中针对 MLflow 3.16.0 的本地检查并非该示例的端到端验证。

Model Registry 注册是一个可选的生命周期步骤。Serving 系统通过独立配置使用模型 URI 或别名；注册或别名变更不会自动部署模型。

## 当前涵盖内容

1. [第 1 部分：MLflow Tracking](01-tracking.md) — 实验、运行、自动记录、MLflow 3 的 `LoggedModel` 变化以及 GenAI 追踪
2. [第 2 部分：MLflow Model Registry](02-model-registry.md) — Registered Models、Model Versions、别名和血缘
3. [第 3 部分：在 EKS 上部署 MLflow](03-eks-deployment.md) — 跟踪服务器、PostgreSQL 后端存储、S3 artifact 存储和 IAM 访问

## 主要来源

- [MLflow 3.16.1 发布](https://github.com/mlflow/mlflow/releases/tag/v3.16.1)
- [MLflow 3.16.0 审查基线](https://github.com/mlflow/mlflow/releases/tag/v3.16.0)
- [MLflow 2.14.0 中引入追踪功能](https://github.com/mlflow/mlflow/releases/tag/v2.14.0)
- [后端存储](https://mlflow.org/docs/3.16.0/self-hosting/architecture/backend-store/)