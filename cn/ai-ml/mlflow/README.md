# EKS 上的 MLflow 深度解析

> **审查基线**：MLflow 3.16.0
> **审查的文档**：2026 年 9 月 12 日

## 概述

MLflow 提供实验跟踪、模型日志记录与注册、版本管理、GenAI 评估和追踪功能。追踪功能于 2.14.0 引入；3.x 扩展了 `LoggedModel`、评估和 UI 集成。3.16.0 版本于 2026-09-04 发布。

你可以通过 SDK 和 SQLite 在本地使用它，也可以运行一个 HTTP tracking service，并使用独立的 SQL 元数据存储和 artifact store。一个逻辑服务不一定对应一个 Pod 或存储系统。本系列涵盖 Tracking、Registry 和 EKS 部署；并不验证每项 MLflow 功能或成功的 GPU 训练。

## 组件图谱

| 概念 | 解决的问题 | 深度解析 |
|---------|--------------------|-----------|
| **Tracking** | 记录并查询实验参数、指标、artifacts、模型和 GenAI traces | [第 1 部分](01-tracking.md) |
| **Model Registry** | 为模型提供独立于任一训练运行的稳定且有版本的身份标识 | [第 2 部分](02-model-registry.md) |
| **EKS Deployment** | 在 EKS 上运行 tracking server、backend store 和 artifact store | [第 3 部分](03-eks-deployment.md) |

![展示三阶段管道的图表：MLflow Tracking（实验、运行、traces）流向 Model Registry（已注册模型、aliases），随后由不在本文档系列范围内的 Serving 阶段进行解析。](../../.gitbook/assets/en-ai-ml-mlflow-readme-0.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-mlflow-readme-0.html)

## 为什么在 EKS 上运行

这种权衡与本文档站点其他数据/ML 部分所述的相同：已经运行 EKS 的团队可以将其相同的 deployment、IAM（IRSA/Pod Identity）和可观测性模式复用于 MLflow 的 tracking server，就像复用于集群中的其他所有内容一样；代价是直接运行 tracking server、其 backend database 和 artifact store，而非使用托管替代方案。

[SageMaker AI 指南](../sagemaker-ai/README.md)描述了一个 Qwen 对比设计。该示例具有独立的历史版本固定，并且由于其 DLC 已停止修补程序支持，目前阻止 GPU 执行。本系列对 MLflow 3.16.0 的本地检查并非对该示例的端到端验证。

Model Registry 注册是一个可选的生命周期步骤。Serving systems 通过单独的配置使用模型 URI 或 aliases；注册或 alias 变更不会自动部署模型。

## 当前涵盖内容

1. [第 1 部分：MLflow Tracking](01-tracking.md) — 实验、运行、autologging、MLflow 3 的 `LoggedModel` 转变以及 GenAI tracing
2. [第 2 部分：MLflow Model Registry](02-model-registry.md) — Registered Models、Model Versions、aliases 和 lineage
3. [第 3 部分：在 EKS 上部署 MLflow](03-eks-deployment.md) — tracking server、PostgreSQL backend store、S3 artifact store 和 IAM 访问

## 主要来源

- [MLflow 3.16.0 发布版本](https://github.com/mlflow/mlflow/releases/tag/v3.16.0)
- [MLflow 2.14.0 中引入的 Tracing](https://github.com/mlflow/mlflow/releases/tag/v2.14.0)
- [Backend store](https://mlflow.org/docs/3.16.0/self-hosting/architecture/backend-store/)
