# EKS 上的 Ray 深入解析

> **审查基线**：Ray 2.58.0，KubeRay v1.7.1
> **已检查的最新版本**：Ray 2.59.0（2026 年 10 月 2 日），于 2026 年 10 月 16 日检查；示例使用 2.58.0
> **文档审查日期**：2026 年 10 月 16 日

## 概述

Ray 使用 tasks、actors、ObjectRefs 和每个节点的对象存储来分发 Python 工作。Train、Tune 和 Serve 基于这一基础构建，同时增加了训练、搜索和服务策略。单一对象存储路径不会自动处理所有通信或恢复问题。

KubeRay 是用于协调 RayCluster、RayJob 和 RayService 的 Kubernetes operator。它不是为应用选择 ML 库的调度器。Ray 工作调度、Kubernetes Pod 放置和 EC2 节点预置属于不同层级。

## 组件概览

| 概念 | 解决的问题 | 深入解析 |
|---------|--------------------|-----------|
| **架构** | tasks、actors 以及其他所有功能所依赖的对象存储 | [第 1 部分](01-architecture.md) |
| **KubeRay Operator** | 将 Ray 集群作为原生 Kubernetes 资源运行（`RayCluster`/`RayJob`/`RayService`） | [第 2 部分](02-kuberay-operator.md) |
| **Ray Train 和 Tune** | 分布式模型训练和超参数搜索 | [第 3 部分](03-ray-train-tune.md) |
| **Ray Serve** | 模型服务，包括专用的 LLM 服务构建模块 | [第 4 部分](04-ray-serve.md) |

![Train、Tune 和 Serve 等应用库使用 Ray Core tasks 和 actors；KubeRay 则单独管理 Kubernetes 上的 Ray 资源。](../../.gitbook/assets/en-ai-ml-ray-readme-0.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-ray-readme-0.html)

## 为什么在 EKS 上运行

权衡与本文档站点的数据/ML 部分其他内容所述相同：已经运行 EKS 的团队可以将同一套节点池自动扩缩（通过 Karpenter）、IAM 和可观测性模式复用于 Ray 工作负载，就像集群上的其他工作负载一样；代价是直接运维 KubeRay operator 及其 RayCluster/RayJob/RayService 资源，而不是使用托管替代方案。

基础验证是运行一个小型单节点 Ray 实例。它不能作为 GPU 训练、多节点恢复、实际运行的 EKS 部署或自动扩缩的证据。

Ray 2.59.0 默认对本地集群启用令牌身份验证。如果 `~/.ray/auth_token` 不存在，调用 `ray.init()` 且不指定地址时会生成一个令牌；`RAY_AUTH_MODE=disabled` 可将其关闭。发行说明称，计划从 2.61 版开始将此默认设置扩展到远程和多节点集群。本系列示例已在 2.58.0 上检查，未在 2.59.0 上重新运行。

## 当前涵盖内容

1. [第 1 部分：Ray 架构](01-architecture.md)：tasks、actors、对象存储以及 head/worker 集群模型
2. [第 2 部分：KubeRay Operator](02-kuberay-operator.md)：RayCluster、RayJob、RayService，以及与 Karpenter 配合的两级自动扩缩模式
3. [第 3 部分：Ray Train 和 Ray Tune](03-ray-train-tune.md)：分布式训练和超参数调优
4. [第 4 部分：Ray Serve](04-ray-serve.md)：模型服务、Ray Serve LLM，以及基于 RayService 的生产部署

## 主要来源

- [Ray 2.58.0](https://github.com/ray-project/ray/releases/tag/ray-2.58.0)
- [Ray 2.59.0（已检查的最新版本）](https://github.com/ray-project/ray/releases/tag/ray-2.59.0)
- [KubeRay 1.7.1](https://github.com/ray-project/kuberay/releases/tag/v1.7.1)
