# Ray on EKS 深入解析

> **审阅基线**: Ray 2.58.0, KubeRay v1.7.0
> **最后更新**: September 12, 2026

## 概述

Ray 使用 tasks、actors、ObjectRefs 以及各节点上的 object store 来分布式执行 Python 工作负载。Train、Tune 和 Serve 在此基础之上构建，并各自补充了训练、搜索和服务方面的策略。单一的 object store 路径并不会自动解决所有通信或恢复方面的问题。

KubeRay 是负责协调（reconcile）RayCluster、RayJob 和 RayService 的 Kubernetes operator。它并不会以调度器的身份为应用选择 ML 库。Ray 的工作调度、Kubernetes 的 Pod 放置以及 EC2 节点的置备是相互独立的层次。

## 组件地图

| 概念 | 解决的问题 | 深入解析 |
|---------|--------------------|-----------|
| **Architecture** | tasks、actors 以及作为其他一切基础的 object store | [第 1 部分](01-architecture.md) |
| **KubeRay Operator** | 以原生 Kubernetes 资源（`RayCluster`/`RayJob`/`RayService`）的形式运行 Ray 集群 | [第 2 部分](02-kuberay-operator.md) |
| **Ray Train & Tune** | 分布式模型训练与超参数搜索 | [第 3 部分](03-ray-train-tune.md) |
| **Ray Serve** | 模型服务，包括专用的 LLM 服务构建模块 | [第 4 部分](04-ray-serve.md) |

![Application libraries such as Train, Tune, and Serve use Ray Core tasks and actors; KubeRay separately manages Ray resources on Kubernetes.](../../.gitbook/assets/en-ai-ml-ray-readme-0.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-ray-readme-0.html)

## 为什么要在 EKS 上运行

这里的取舍与本文档站点数据/ML 章节其他部分讨论的相同：已经在运行 EKS 的团队可以为 Ray workloads 复用与集群上其他一切相同的节点池自动扩缩（通过 Karpenter）、IAM 和可观测性模式，代价是需要直接运维 KubeRay operator 及其 RayCluster/RayJob/RayService 资源，而不是使用托管的替代方案。

基础验证是一次小规模的单节点 Ray 运行。它并不能证明 GPU 训练、多节点恢复、真实的 EKS 安装或自动扩缩能力。

## 当前涵盖内容

1. [第 1 部分：Ray 架构](01-architecture.md) — tasks、actors、object store 以及 head/worker 集群模型
2. [第 2 部分：KubeRay Operator](02-kuberay-operator.md) — RayCluster、RayJob、RayService 以及与 Karpenter 配合的两层自动扩缩模式
3. [第 3 部分：Ray Train 与 Ray Tune](03-ray-train-tune.md) — 分布式训练与超参数调优
4. [第 4 部分：Ray Serve](04-ray-serve.md) — 模型服务、Ray Serve LLM 以及基于 RayService 的生产部署

## 主要来源

- [Ray 2.58.0](https://github.com/ray-project/ray/releases/tag/ray-2.58.0)
- [KubeRay 1.7.0](https://github.com/ray-project/kuberay/releases/tag/v1.7.0)
