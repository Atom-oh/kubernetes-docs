# VPC Lattice 深入指南概览

> **范围**：VPC Lattice 服务/资源 API 和 AWS Gateway API Controller；请核实选定的版本和已安装的 CRD。
> **最后更新**：2026 年 10 月 12 日

## 本节涵盖内容

- 从基于 sidecar proxy 的服务网格（App Mesh、Istio）迁移到**托管数据平面**（VPC Lattice）时，实际发生哪些变化
- 文档描述的 Lattice 寻址、SigV4 签名及适用的身份验证策略如何改变请求路径
- 将工作负载身份从 SPIFFE/SPIRE 迁移到 IAM 时遇到的结构性差异，以及这些差异为何会成为评审问题

## 为什么单独设立本节

本节旨在**帮助理解概念**。如何创建 Lattice 资源和安装 AWS Gateway API Controller，已在 [VPC Lattice](../../networking/02-vpc-lattice.md) 中介绍；与 Istio 的逐项功能比较则见 [Istio 与 VPC Lattice](../istio/comparison/02-istio-vs-lattice.md)。前两份文档没有涉及、但本节要回答的是：**“为什么要这样设计”以及“这一设计会带来什么影响”**。

迁移已有紧迫性。**AWS App Mesh 支持已于 2026 年 9 月 30 日结束**，App Mesh 控制台和资源也已无法访问。新客户接入自 2024 年 9 月 24 日起就已停止。对于曾运行 App Mesh 的组织，这次迁移已经不再是可选项；截止日期已经过去。

但 App Mesh 与 Lattice **并不是同一种东西的两种实现**。数据平面位于不同位置（Pod 内部与 AWS 基础设施），身份验证粒度不同（连接与请求），信任根的所有方也不同（客户 CA 与 AWS IAM/STS）。如果迁移时只逐项替换资源名称，功能缺口和安全评审失败可能会在迁移后期才暴露。本节旨在**提前**指出这些问题。

## 读者和前置知识

- AWS 架构师和客户基础设施工程师
- 假定你已了解 EKS 和 Kubernetes
- 假定你尚不了解 VPC Lattice 和服务网格内部机制
- 尽量减少代码和清单示例；本节不是动手实验指南

## 文档结构

| # | 文档 | 回答的问题 |
|---|----------|---------------------|
| 1 | [App Mesh 与 VPC Lattice 架构](./01-appmesh-vs-lattice.md) | 数据平面从 Pod 转移到基础设施后，哪些机制仍然存在，哪些消失了？ |
| 2 | [延迟影响分析](./02-latency.md) | 既有导致性能变差的因素，也有改善因素。哪一方会在我们的环境中占主导？ |
| 3 | [IAM 身份验证流程详解](./03-auth-flow.md) | 从签署请求到授权，四个阶段分别会发生什么？ |
| 4 | [基础知识：链路本地和 SNI](./04-networking-basics.md) | 没有 sidecar 时如何拦截流量？不终止 TLS 会失去什么？ |
| 5 | [工作负载身份迁移：SPIFFE 到 IAM](./05-spiffe-to-iam.md) | IAM 能否实现 SPIRE 原有的功能？哪些内容无法替代？ |
| 6 | [约束和决策要点](./06-constraints.md) | 必须就哪些功能、信任、成本和恢复方案作出决定？ |
| 7 | [内核数据路径](./07-kernel-datapath.md) | Pod 路由、代理规则和连接跟踪如何影响数据路径？ |

建议从文档 1 开始按顺序阅读。文档 4（链路本地、SNI）是理解文档 3 和 6 中约束的前置知识。虽然它排在后面，如果你不熟悉网络基础，请先阅读文档 4。

## 关于准确性的说明

本节的事实依据包括 AWS 官方文档、AWS Gateway API Controller 文档、`aws-samples/migrating-from-aws-app-mesh-to-amazon-vpc-lattice` 参考实现以及 SPIFFE/SPIRE 文档。

未经官方文档确认的内容不会作为事实陈述，而会以 `Needs verification` 提示块标出。Lattice 服务仍在不断增加新功能，尤其是**配额和定价会随区域和时间变化**。最终确定设计前，请直接在 Service Quotas 控制台和 [VPC Lattice 定价页面](https://aws.amazon.com/vpc/lattice/pricing/)核实当前值。

## 相关文档

- [VPC Lattice](../../networking/02-vpc-lattice.md)：Lattice 资源配置和 Gateway API Controller 安装
- [Gateway API](../../networking/04-gateway-api.md)：Kubernetes Gateway API 标准
- [Istio 与 VPC Lattice](../istio/comparison/02-istio-vs-lattice.md)：功能、成本和运维复杂度比较
- [Istio 安全：mTLS](../istio/security/01-mtls.md)：基于 sidecar 的双向身份验证
- [Pod 网络基准测试](../../networking/06-pod-network-benchmark.md)：同 AZ 和跨 AZ 的实测延迟基线
