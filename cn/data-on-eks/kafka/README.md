# EKS 上的 Kafka 深入解析

## 概述

本指南使用 Strimzi Operator 作为 EKS 上的自管 Kafka 方案。Operator 会协调 Pods、存储、监听器、证书和升级；但它不会免除你在数据、可用性和安全策略方面的责任。第 6 部分会比较 Amazon MSK 等托管替代方案。

> **最后更新**：2026 年 10 月 16 日。Strimzi 1.3.0 / Kafka 4.3.1。
> **升级要求**：Strimzi 1.0 及更高版本仅支持 CRD API `v1`。升级 Operator 之前，请按照官方迁移流程转换现有的 `v1beta2` / `v1beta1` / `v1alpha1` 资源并准备 CRD。仅更改版本号并不构成升级计划。

Strimzi 1.3.0 支持 Kafka 4.2.0、4.2.1、4.2.2、4.3.0 和 4.3.1，默认使用 4.3.1。本指南固定使用兼容的组合；安装前也请检查发行版、Kubernetes 版本和升级路径。

## 核心架构概念

Broker 存储主题分区副本。KafkaConsumer 组会分配分区，一个成员可能拥有多个分区。独立的控制器仲裁组负责管理元数据 Raft 日志。

KRaft 于 2.8 版作为早期访问功能推出，并于 3.3 版达到生产就绪状态；Kafka 4.0 移除了 ZooKeeper 模式。控制器和 Broker 可以采用专用角色。移除 ZooKeeper 并不意味着无需再进行控制器、存储或恢复操作。

用户声明 Kafka 和 KafkaNodePool 等自定义资源；Strimzi 会协调 Pods、PVCs、Services 和 Secrets。下图是简化的关系示意图，并非高可用副本数量部署规范。

![Kafka/KafkaNodePool 到 Pod/PVC 的简化协调流程，通过 Strimzi 实现；实际的 Broker 和控制器副本数量需要单独设计](../../.gitbook/assets/en-data-on-eks-kafka-readme-0.png)

[查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-data-on-eks-kafka-readme-0.html)

## 深入解析目录

**[1. Kafka 基础知识](01-kafka-fundamentals.md)**
- Broker 和主题/分区结构
- 复制和持久性保证
- 消费者组和偏移量管理
- KRaft 控制器仲裁架构

**[2. Strimzi Operator](02-strimzi-operator.md)**
- 安装和配置 Strimzi
- 详细介绍 `Kafka` 和 `KafkaNodePool` CRD
- 在 EKS 上部署 Kafka 集群

**[3. Kafka 运维](03-kafka-operations.md)**
- 使用 EBS/gp3 设计存储
- Broker 扩展策略
- 使用 Cruise Control 重新平衡分区
- 通过兼容性和可用性检查执行滚动升级

**[4. Schema Registry](04-schema-registry.md)**
- 设计 Avro/Protobuf Schema
- Karapace 与 Apicurio Registry 的比较
- 兼容性策略：BACKWARD/FORWARD/FULL

**[5. Kafka Connect 和 MirrorMaker](05-kafka-connect-mirrormaker.md)**
- 部署 Kafka Connect 并配置连接器
- 运行源连接器和接收器连接器
- 使用 MirrorMaker2 进行灾难恢复和跨区域复制

**[6. MSK 集成](06-msk-integration.md)**
- Amazon MSK 与自管的 Strimzi
- 使用 MSK Connect
- 与 Kinesis Data Streams 集成并进行比较

**[7. 监控](07-monitoring.md)**
- 使用 Prometheus/Grafana 收集 Broker 指标
- 监控消费者滞后
- 使用 KEDA 对消费者自动扩缩容

**[8. 最佳实践](08-best-practices.md)**
- 分区数量和键设计策略
- 生产者/消费者性能调优
- 使用 mTLS/SASL 保护安全
- 优化存储和实例成本

**[9. Kafka 实测基准测试](09-kafka-benchmark.md)**
- 测量基于 gp3 卷的 3-Broker KRaft 集群在 RF3 与 RF1 下的摄取上限
- 比较 acks=0/1/all 下的吞吐量与 p99 延迟权衡
- 按压缩编解码器和记录大小比较吞吐量与 CPU 成本
- 冷消费者和混合工作负载如何影响生产者吞吐量

## 参考资料

- [Strimzi 1.3.0 发行说明](https://github.com/strimzi/strimzi-kafka-operator/releases/tag/1.3.0)

- [Strimzi 文档](https://strimzi.io/docs/operators/1.3.0/overview.html)
- [Apache Kafka 文档](https://kafka.apache.org/43/design/design/)
- [KRaft 运维指南](https://kafka.apache.org/43/operations/kraft/)
- [AWS Data on EKS 项目](https://awslabs.github.io/data-on-eks/)

## 测验

要测试你对本节内容的掌握程度，请尝试 [Kafka 基础知识测验](../../quizzes/data-on-eks/kafka/01-kafka-fundamentals-quiz.md)。要检查你是否能够将基准测试数据转化为设计决策，也可以尝试 [Kafka 实测基准测试测验](../../quizzes/data-on-eks/kafka/09-kafka-benchmark-quiz.md)。
