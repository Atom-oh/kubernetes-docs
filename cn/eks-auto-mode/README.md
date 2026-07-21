# EKS Auto Mode 操作指南

> **支持的版本**: EKS 1.29+, EKS Auto Mode GA
> **最后更新**: July 21, 2026

Amazon EKS Auto Mode 是一项可完全自动化 Kubernetes Node 管理的功能，可根据 workload 要求自动预置和优化 Node。本指南介绍 EKS Auto Mode 的概念、配置方法以及生产环境最佳实践。

### 2026 年 7 月更新：ARC Zonal Shift 支持

自 2026 年 7 月 10 日起，EKS Auto Mode Cluster 支持 Amazon Application Recovery Controller (ARC) zonal shift 和 autoshift。由于 Auto Mode 代表您管理计算资源，无需设置标志或管理 Karpenter 版本即可获得 zonal shift 支持——只需在 Cluster 上启用 ARC zonal shift。激活 zonal shift 后，Auto Mode 会停止在受影响的 AZ 中预置新的容量，并停止该区域内 Node 的 consolidation 和 drift 等自愿中断。此功能不额外收费；详情请参阅[公告](https://aws.amazon.com/about-aws/whats-new/2026/07/eks-auto-mode-arc-zonal-shift)和 [ARC zonal shift 文档](https://docs.aws.amazon.com/eks/latest/userguide/zone-shift.html)。

## 目录

1. [Auto Mode 入门](./01-getting-started.md) - 创建 Cluster 并启用 Auto Mode
2. [NodePool 配置和优化](./02-nodepool-configuration.md) - 默认和自定义 NodePools
3. [了解扩缩容行为](./03-scaling-behavior.md) - 预置、consolidation、drift 检测
4. [Spot Instance 利用策略](./04-spot-strategies.md) - 混合容量和中断处理
5. [运维和管理](./05-operations.md) - 中断预算、滚动替换、监控
6. [成本管理和优化](./06-cost-management.md) - 成本分析、Spot 节省、资源规格优化
7. [Node 生命周期管理](./07-node-lifecycle.md) - 到期、AMI 管理、新鲜度策略
8. [特定 workload 优化](./08-workload-optimization.md) - Web、batch、GPU、AI/ML workload
9. [从 Managed Node Groups 迁移](./09-migration-guide.md) - 迁移步骤和共存

---

## EKS Auto Mode 简介

### 什么是 Auto Mode？

EKS Auto Mode 是由 AWS 管理的全自动 Node 管理解决方案。它在内部基于 Karpenter，AWS 管理所有内容，用户无需安装或配置单独的 Node 管理组件。

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
|  |  | (Default Provided)|  | (Default Provided)|  |  (User Defined)  |    |
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

### 与现有管理方法的对比

| 功能 | Managed Node Groups | Fargate | Auto Mode |
|---------|---------------------|---------|-----------|
| Node 管理 | 用户（基于 ASG） | 完全由 AWS 管理 | 完全由 AWS 管理 |
| 扩缩容方式 | Cluster Autoscaler | 按 Pod | 基于 Karpenter |
| 扩缩容速度 | 分钟 | 即时（Pod 调度） | 数十秒 |
| Instance 类型选择 | 预定义 | 自动 | 自动优化 |
| Spot 支持 | 手动配置 | 不支持 | 自动管理 |
| GPU workload | 支持 | 有限支持 | 完全支持 |
| DaemonSet 支持 | 支持 | 不支持 | 支持 |
| 成本优化 | 手动 | 中等 | 自动 |
| 复杂性 | 高 | 低 | 低 |
| 自定义程度 | 高 | 低 | 中等 |

### 内部架构和运行原理

EKS Auto Mode 基于 Karpenter 运行，但在 AWS 管理的 control plane 内执行。

```mermaid
sequenceDiagram
    participant User as User
    participant API as EKS API Server
    participant Karpenter as Auto Mode Controller
    participant EC2 as EC2 Fleet
    participant Node as New Node

    User->>API: Pod creation request
    API->>API: Pod Pending state
    Karpenter->>API: Detect Pending Pod
    Karpenter->>Karpenter: NodePool matching
    Karpenter->>Karpenter: Determine optimal instance type
    Karpenter->>EC2: Instance launch request
    EC2->>Node: Instance provisioning
    Node->>API: Node registration (kubelet)
    API->>Node: Pod scheduling
    Node->>API: Pod Running
```

### 支持的 Region 和限制

#### 支持的 Region（截至 2025 年 2 月）

EKS Auto Mode 在以下 Region 可用：

- **美洲**: us-east-1, us-east-2, us-west-1, us-west-2
- **欧洲**: eu-west-1, eu-west-2, eu-central-1, eu-north-1
- **亚太地区**: ap-northeast-1, ap-northeast-2, ap-southeast-1, ap-southeast-2, ap-south-1

#### 限制

| 项目 | 限制 |
|------|-------|
| 每个 Cluster 的最大 NodePools 数量 | 100 |
| 每个 NodePool 的最大 Node 数量 | 1000 |
| 每个 Cluster 的最大 Node 数量 | 5000 |
| 最低 EKS 版本 | 1.29 |
| 支持的 AMI family | AL2023, Bottlerocket |
| Windows Node | 不支持 |

---

## 后续步骤

成功配置 EKS Auto Mode 后，我们建议学习以下主题：

1. **[EKS 成本优化](../eks/07-eks-cost-optimization.md)**: Spot、Savings Plans、资源优化
2. **[EKS 监控和日志](../eks/06-eks-monitoring-logging.md)**: CloudWatch、Prometheus、Grafana
3. **[EKS 安全](../eks/05-eks-security.md)**: IAM、网络策略、Pod 安全
4. **[Karpenter 深入解析](../autoscaling/02-karpenter.md)**: 直接安装 Karpenter 和高级功能

## 相关测验

为检验您的学习成果，请尝试 [EKS Auto Mode 测验](../quizzes/eks-auto-mode/01-getting-started-quiz.md)。

---

## 参考资料

- [AWS EKS Auto Mode 官方文档](https://docs.aws.amazon.com/eks/latest/userguide/automode.html)
- [Karpenter 官方文档](https://karpenter.sh/)
- [EKS 最佳实践指南](https://aws.github.io/aws-eks-best-practices/)
- [AWS 成本优化指南](https://aws.amazon.com/pricing/cost-optimization/)
- [用于增强安全性、网络控制和性能的新 EKS Auto Mode 功能（AWS Containers Blog，2025-10-16）](https://aws.amazon.com/blogs/containers/new-amazon-eks-auto-mode-features-for-enhanced-security-network-control-and-performance/)
- [从自管理 Karpenter 迁移到 EKS Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/auto-migrate-karpenter.html)

---

< [返回 EKS 主题](../README.md) | [下一步：入门](./01-getting-started.md) >
