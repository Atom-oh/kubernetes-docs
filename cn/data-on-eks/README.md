# EKS 上的数据

> **最后更新**: 2026 年 9 月 12 日

## 概述

本节介绍如何在 Amazon EKS 上运行 Kafka、Spark、Airflow 和 Flink，并将它们与 AWS 托管服务连接起来。Helm chart、Kubernetes Operator 和执行器提供了不同的部署、可观测性、扩缩容和所有权模式。

根据运维能力、所需功能、可用性和总成本，将自行运维与 Amazon MSK、EMR 和 MWAA 等托管选项进行比较。EMR on EKS 管理作业执行，同时将底层 EKS 集群的责任留给你。SageMaker Unified Studio 是一个托管式数据/AI 工作区和治理集成，而不是部署到 EKS 中的软件。

## 数据工作负载类别

区分四种执行工作负载类别，以及连接这些类别的托管治理领域。一个工具可以承担多个角色。

| 类别 | 解决的问题 | 代表性工具 | EKS 上的数据覆盖情况 |
|----------|--------------------|----------------------|------------------------|
| **事件流** | 实时发布/订阅事件，并在系统之间可靠地连接异步通信 | Apache Kafka | 已提供：[EKS 上的 Kafka](kafka/README.md) |
| **批处理与分析** | 对大型数据集进行分布式处理，以用于 ETL、聚合和 ML 管道 | Apache Spark | 已提供：[EKS 上的 Spark](spark/README.md) |
| **编排** | 定义数据作业之间的依赖关系和计划，并管理其执行 | Apache Airflow | 已提供：[EKS 上的 Airflow](airflow/README.md) |
| **流处理** | 对流数据执行实时聚合、转换和有状态计算 | Apache Flink | 已提供：[EKS 上的 Flink](flink/README.md) |
| **受治理的数据和 AI 工作区** | 在托管边界内共享数据资产、项目配置方案、工具和成员资格 | SageMaker Unified Studio | 已提供：[Unified Studio 治理](sagemaker-unified-studio/README.md) |

![Airflow 协调 Spark 作业，而 Spark 和 Flink 读取并处理 Kafka 事件。此图并未表示 Airflow 会调度 Kafka broker 本身。](../.gitbook/assets/en-data-on-eks-readme-0.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-data-on-eks-readme-0.html)

## 为什么要在 EKS 上运行这些工具

考虑直接在 EKS 上运行时，评估以下机会和限制：

- **统一运维和可观测性**：沿用现有的 `kubectl`、GitOps 和 Prometheus/Grafana 实践。数据质量、数据血缘、查询性能和消费者滞后仍需要领域专属的可观测性。
- **自动扩缩容**：[Karpenter](../autoscaling/02-karpenter.md) 调整节点容量；HPA/KEDA 或引擎专属的自动扩缩容控制器调整受支持的工作进程/作业。Kafka broker 变更还需要审查分区重新分配、仲裁、存储和 Operator 支持。
- **成本效率**：在重启、检查点和复制要求允许的情况下使用 Spot 和装箱优化。结合存储、网络和运维成本评估 [EKS 成本优化](../eks/07-eks-cost-optimization.md)；不要对 broker 和有状态作业一概而论。
- **多租户**：Namespaces、ResourceQuotas 和 NetworkPolicies 是隔离组件。验证实际的数据权限、信任级别、身份验证、存储和网络；仅靠命名空间并不能实现完整的租户隔离。

这种方法确实存在权衡：你的团队需要直接承担 Operator 管理、存储设计和升级策略。接下来的深入介绍将针对每种工具详细探讨这种平衡。

## 目前涵盖的内容

- [现代数据管道剖析](01-data-pipeline-anatomy.md)：介绍完整管道的入门指南，分为从数据源到数据使用的五个层次，并展示每个深入介绍涵盖的层次。
- [EKS 上的 Kafka](kafka/README.md)：分为 8 部分，深入介绍如何使用 Strimzi Operator 在 EKS 上部署和运维 Apache Kafka，另有第 9 部分，通过实测基准测试评估 gp3 上由 3 个 broker 组成的 RF3 集群的摄取上限。
- [EKS 上的 Spark](spark/README.md)：分为 5 部分，深入介绍 Spark on Kubernetes 基础知识、Spark Operator 生态、Amazon EMR on EKS 以及性能/成本调优。
- [EKS 上的 Airflow](airflow/README.md)：分为 5 部分，深入介绍 Airflow 3 的架构、基于 Helm 的部署和执行器选择、使用 KubernetesPodOperator 的 DAG 模式，以及 Amazon MWAA 集成。
- [EKS 上的 Flink](flink/README.md)：分为 4 部分，深入介绍 Flink 在 Kubernetes 上的架构、Flink Kubernetes Operator、状态/检查点以及运维/高可用性。
- [SageMaker Unified Studio 治理](sagemaker-unified-studio/README.md)：涵盖域、项目配置方案、项目、目录资产、成员资格和删除生命周期。

## 后续步骤

1. [EKS 上的 Kafka](kafka/README.md)：深入介绍基于 Strimzi 的 Kafka
2. [EKS 上的 Spark](spark/README.md)：深入介绍 Spark Operator 和 EMR on EKS
3. [EKS 上的 Airflow](airflow/README.md)：深入介绍基于 Helm 的 Airflow 部署和 DAG 模式
4. [EKS 上的 Flink](flink/README.md)：深入介绍 Flink Kubernetes Operator 和流处理模式
5. [SageMaker Unified Studio 治理](sagemaker-unified-studio/README.md)：介绍将托管式数据/AI 工作区连接到 EKS 管道的治理指南
