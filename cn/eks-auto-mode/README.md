# EKS Auto Mode 运维指南

> **支持的版本**：EKS Auto Mode GA；示例基线为 EKS 1.36
> **最后更新**：2026 年 10 月 12 日

Amazon EKS Auto Mode 可自动管理 Kubernetes 节点，包括根据工作负载需求进行预置和优化。本指南介绍 Auto Mode 的概念、配置和运维。AWS 管理 Auto Mode 基础设施；您仍需负责应用可用性、资源请求、安全、监控以及集群/VPC 配置。投入生产前，请先在自己的环境中验证示例。

### 2026 年 10 月更新：EKS 1.37 默认值

EKS 1.37 于 2026 年 10 月 1 日开始提供。在 EKS 1.37 上新建自定义 NodePool 时，如果省略整合策略，其默认值为 `Balanced`；内置的 `general-purpose` 和 `system` 池也使用 `Balanced`，而且无法更改这些内置池的策略。如果希望自定义池采用该行为，请显式设置 `WhenEmptyOrUnderutilized`。本指南中的 NodePool 示例并非都设置了此字段，因此在 EKS 1.37 上创建这些示例时会使用 `Balanced`。详情请参阅 [EKS 标准支持版本说明](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions-standard.html)中的 Kubernetes 1.37 部分。

### 2026 年 7 月更新：支持 EFA 和置放群组

2026 年 7 月 22 日，AWS 宣布 EKS Auto Mode 和开源 Karpenter 节点池现已支持 Elastic Fabric Adapter (EFA) 网络设备配置和 EC2 置放群组。

在支持 EFA 的实例上，可将网络接口配置为仅用于 EFA 的接口或标准 ENI。仅用于 EFA 的接口在提供完整互连带宽的同时，不消耗 VPC IP 地址。节点池配置也可指定 cluster、spread 或 partition 置放策略。这些选项适用于需要高吞吐量或故障隔离的分布式训练和推理工作负载。详情请参阅[公告](https://aws.amazon.com/about-aws/whats-new/2026/07/amazon-eks-efa-placement-groups/)。

### 2026 年 7 月更新：支持 ARC 可用区迁移

自 2026 年 7 月 10 日起，EKS Auto Mode 集群支持 Amazon Application Recovery Controller (ARC) 可用区迁移和自动迁移。在集群上启用 ARC 可用区迁移即可；Auto Mode 不需要额外标志，也不需要您管理 Karpenter 版本。

发生可用区迁移时，Auto Mode 会停止在受影响的可用区中预置容量，并暂停该区节点的整合和漂移等自愿中断。如果健康可用区的节点需要依赖受影响的可用区来安排替换工作负载，Auto Mode 也会阻止这些健康区中的自愿中断。集群注册后，需另行配置 ARC 自动可用区迁移。

可用区迁移不会让可用区本地卷或严格绑定到某个可用区的工作负载变得可迁移。ARC 不收取可用区迁移费用；替换容量和常规基础设施费用仍然适用。详情请参阅[公告](https://aws.amazon.com/about-aws/whats-new/2026/07/eks-auto-mode-arc-zonal-shift)和 [ARC 可用区迁移文档](https://docs.aws.amazon.com/eks/latest/userguide/zone-shift-enable.html)。

## 目录

1. [Auto Mode 入门](./01-getting-started.md) - 创建集群并启用 Auto Mode
2. [NodePool 配置和优化](./02-nodepool-configuration.md) - 默认和自定义 NodePool
3. [了解扩缩容行为](./03-scaling-behavior.md) - 节点预置、整合和漂移检测
4. [Spot 实例使用策略](./04-spot-strategies.md) - 混合容量和中断处理
5. [运维和管理](./05-operations.md) - 中断预算、滚动替换和监控
6. [成本管理和优化](./06-cost-management.md) - 成本分析、Spot 节省和规格调整
7. [节点生命周期管理](./07-node-lifecycle.md) - 到期、AMI 管理和新鲜度策略
8. [针对工作负载的优化](./08-workload-optimization.md) - Web、批处理、GPU 和 AI/ML 工作负载
9. [从托管节点组迁移](./09-migration-guide.md) - 迁移步骤和共存方式

---

## EKS Auto Mode 简介

### 什么是 Auto Mode？

EKS Auto Mode 是由 AWS 管理的全托管节点管理方案，内部基于 Karpenter；AWS 负责运维托管基础设施控制器。用户配置工作负载约束、自定义 NodePool/NodeClass 和中断预算，而不是为 Auto Mode 另行安装 Karpenter 控制器。

```
+-----------------------------------------------------------------------------+
|                           EKS Auto Mode Architecture                         |
+-----------------------------------------------------------------------------+
|                                                                              |
|  +---------------------------------------------------------------------+    |
|  |                    EKS Control Plane (AWS Managed)                   |    |
|  |  +------------+  +------------+  +------------+  +------------+    |    |
|  |  | API Server |  |   etcd     |  | Controller |  |  Karpenter |    |    |
|  |  |            |  |            |  |  Manager   |  | Controller |    |    |
|  |  +------------+  +------------+  +------------+  +------------+    |    |
|  +---------------------------------------------------------------------+    |
|                                    |                                         |
|                                    v                                         |
|  +---------------------------------------------------------------------+    |
|  |                        NodePool Resources                            |    |
|  |  +------------------+  +------------------+  +------------------+  |    |
|  |  |  general-purpose |  |      system      |  |   custom-pool    |  |    |
|  |  | (Default Provided)|  | (Default Provided)|  |  (User Defined)  |  |    |
|  |  +------------------+  +------------------+  +------------------+  |    |
|  +---------------------------------------------------------------------+    |
|                                    |                                         |
|                                    v                                         |
|  +---------------------------------------------------------------------+    |
|  |                     EC2 Instances (Auto Managed)                     |    |
|  |  +--------------+  +--------------+  +--------------+              |    |
|  |  |   m6i.2xl    |  |   c7g.xl     |  |   r6i.4xl    |   ...        |    |
|  |  |  (On-Demand) |  |   (Spot)     |  |  (On-Demand) |              |    |
|  |  +--------------+  +--------------+  +--------------+              |    |
|  +---------------------------------------------------------------------+    |
|                                                                              |
+-----------------------------------------------------------------------------+
```

### 与现有管理方式的比较

| 功能 | 托管节点组 | Fargate | Auto Mode |
|---|---|---|---|
| 节点管理 | AWS 管理节点组；您配置容量和更新 | AWS 管理每个 Pod 所用的基础设施 | AWS 管理已启动的节点和基础设施控制器 |
| 扩缩容 | 安装了 Cluster Autoscaler 时由其管理，否则需显式调整节点组 | 按 Pod 预置 | 基于 Karpenter 为无法调度的 Pod 预置节点 |
| 预置时间 | 取决于容量、引导过程和工作负载 | 取决于容量、镜像和工作负载；并非即时完成 | 取决于容量、引导过程、镜像和约束；没有固定耗时保证 |
| 实例选择 | 配置指定的实例类型 | 托管计算规格 | 在 NodePool 和工作负载约束范围内选择 |
| Spot | 托管节点组支持 | EKS Fargate 不支持 | NodePool 允许时支持 |
| GPU 工作负载 | 在适当节点上支持 | 不支持 | 支持兼容的加速型实例；仍须满足工作负载/运行时要求 |
| DaemonSet | 支持 | 不支持 | 在托管节点限制范围内支持 |
| 成本控制 | 资源请求、实例选择和自动扩缩容策略 | Pod 资源规格和副本数 | 资源请求、允许的容量和整合策略；不保证节省成本 |
| 主机自定义 | AMI/启动模板选项 | 不支持自定义主机 | AWS 管理的 Bottlerocket 变体，以及受支持的 NodeClass 设置 |

### 内部架构和运作原则

基于 Karpenter 的控制器由 AWS 在工作节点之外运维。下图用于说明概念：调度器会识别无法调度的 Pod，随后再将它绑定到节点；API server 负责存储对象。仅凭 Pod 处于 Pending 状态，并不能证明增加节点就能解决问题。

![EKS Auto Mode 节点预置时序图：Pending Pod 触发 Auto Mode 控制器匹配 NodePool 并选择实例类型，随后启动 EC2 实例、注册新节点、调度 Pod，直至 Pod 进入 Running 状态。](../.gitbook/assets/en-eks-auto-mode-readme-0.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-auto-mode-readme-0.html)

### 支持的区域和限制

#### 区域和支持的版本

[EKS 常见问题](https://aws.amazon.com/eks/faqs/)列出了提供 Auto Mode 的 EKS 区域，包括 GovCloud (US)，中国区域除外。实例和功能在各区域的可用性需要另行核实。此前列出的简短区域清单并不完整。

常见问题中原有的 `1.29+` 功能最低版本，并不代表所有这些版本现在都还能新建，也不代表它们都处于标准支持期。2026 年 10 月 12 日，EKS 1.34–1.37 处于标准支持期；本指南示例保留已审阅的 1.36 基线。生命周期日期和延长支持费用请参阅[当前 EKS 版本日历](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html)。

#### 需要核实的限制

| 项目 | 指引 |
|---|---|
| 容量和规模 | 检查已生效的 EKS/EC2 配额、子网 IP 容量和工作负载约束；在自己的环境中验证预期规模 |
| NodePool 限制 | 用户定义的资源限制与 AWS 账户/服务配额不同；验证规模以及替换节点所需的余量 |
| 操作系统 | AWS 选择其管理的 Bottlerocket 变体；AL2023 或任意自定义 AMI 不是 Auto Mode 可选的 AMI |
| Windows | Auto Mode 不提供 Windows 节点；需要时可另用兼容的节点组 |
| DNS 和存储 | Auto Mode 节点提供本地 CoreDNS；混合型集群仍需为其他节点保留 CoreDNS。托管节点磁盘加密不代表所有动态 PVC 都已加密；请显式设置 StorageClass |

使用 [Service Quotas](https://docs.aws.amazon.com/eks/latest/userguide/service-quotas.html) 和 [NodeClass 参考](https://docs.aws.amazon.com/eks/latest/userguide/create-node-class.html)核实相关限制。本次审计未查询实际账户配额或实例容量。

---

## 后续步骤

成功配置 EKS Auto Mode 后，建议继续了解以下主题：

1. **[EKS 成本优化](../eks/07-eks-cost-optimization.md)**：Spot、Savings Plans 和资源优化
2. **[EKS 监控和日志记录](../eks/06-eks-monitoring-logging.md)**：CloudWatch、Prometheus 和 Grafana
3. **[EKS 安全](../eks/05-eks-security.md)**：IAM、网络策略和 Pod 安全
4. **[Karpenter 深入解析](../autoscaling/02-karpenter.md)**：直接安装 Karpenter 和高级功能

## 相关测验

可通过 [EKS Auto Mode 测验](../quizzes/eks-auto-mode/01-getting-started-quiz.md)检验学习成果。

---

## 参考资料

- [AWS EKS Auto Mode 官方文档](https://docs.aws.amazon.com/eks/latest/userguide/automode.html)
- [Karpenter 官方文档](https://karpenter.sh/)
- [EKS 最佳实践指南](https://docs.aws.amazon.com/eks/latest/best-practices/)
- [AWS 成本优化指南](https://aws.amazon.com/pricing/cost-optimization/)
- [增强安全性、网络控制和性能的 EKS Auto Mode 新功能（AWS Containers Blog，2025-10-16）](https://aws.amazon.com/blogs/containers/new-amazon-eks-auto-mode-features-for-enhanced-security-network-control-and-performance/)
- [从自管理 Karpenter 迁移到 EKS Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/auto-migrate-karpenter.html)
- [Auto Mode 架构和责任](https://docs.aws.amazon.com/eks/latest/userguide/automode.html)
- [EKS Fargate 限制](https://docs.aws.amazon.com/eks/latest/userguide/fargate.html)

---

< [返回 EKS 主题](../README.md) | [下一篇：入门](./01-getting-started.md) >
