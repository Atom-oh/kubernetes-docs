# 运维指南

> **最后更新**: February 23, 2026

本节为 EKS Auto Mode 环境提供生产运维指南。内容涵盖使用 Terraform 进行基础设施预置、CI/CD 流水线、基于 GitOps 的部署、扩缩容、可观测性、资源优化和升级。

---

## 目标读者

- **Platform Engineers**：使用 EKS Auto Mode 构建生产环境
- **Infrastructure Engineers**：运维基于 Terraform/Terragrunt 的 IaC
- **DevOps Engineers**：使用 GitLab CI 和 ArgoCD 构建 CI/CD 流水线
- **SREs**：运维 Prometheus、Grafana 和 Loki 可观测性栈

---

## 前置条件

在开始本运维指南之前，请确保熟悉：

- [EKS Auto Mode 入门](../eks-auto-mode/01-getting-started.md)
- Terraform 基础（resources、modules、state management）
- [Kubernetes 核心概念](../core/01-cluster-architecture.md)
- kubectl 和 Helm CLI 使用经验

---

## 目录

| # | 文档 | 关键主题 |
|---|----------|------------|
| 01 | [Terraform 3-Layer 基础设施设置](./01-infrastructure-setup.md) | VPC、EKS Auto Mode、使用 3-Layer Terraform 的 Pod Identity |
| 02 | [NLB 加权路由和 Blue/Green](./02-infrastructure-advanced.md) | 双 cluster 架构、NLB weights、DNS routing |
| 03 | [CI 流水线](./03-ci-pipelines.md) | ECR、GitLab Runner、GitHub ARC、multi-platform builds |
| 04 | [ArgoCD Multi-Cluster](./04-gitops-multi-cluster.md) | Hub-spoke、ApplicationSet、IAM Identity Center SSO |
| 05 | [GitOps 自动化](./05-gitops-automation.md) | Atlantis、FluxCD、Terraform Cloud、AIOps |
| 06 | [扩缩容策略](./06-scaling-strategies.md) | HPA custom metrics、KEDA、VPA、Spot utilization |
| 07 | [运维告警配置](./07-observability-alerts.md) | Network/CPU/Disk/Auto Mode node termination alerts |
| 08 | [可观测性分析](./08-observability-analysis.md) | Logs/Metrics/Traces correlation、PromQL、LogQL、TraceQL |
| 09 | [可观测性栈运维](./09-observability-stack.md) | Loki、Tempo、Prometheus/AMP 安装与运维 |
| 10 | [资源优化](./10-resource-optimization.md) | Requests/Limits、JVM tuning、framework-specific guide |
| 11 | [EKS 升级](./11-upgrade-operations.md) | Auto Mode zero-downtime upgrade、blue/green strategy |

---

## 学习路径

### 推荐顺序

1. **基础设施** (01-02)：使用 Terraform 预置 VPC/EKS
2. **CI/CD** (03-05)：构建流水线和 GitOps 部署
3. **扩缩容** (06)：为 workloads 建立扩缩容策略
4. **可观测性** (07-09)：构建监控、告警和分析系统
5. **优化** (10)：资源效率和成本优化
6. **升级** (11)：建立零停机升级流程

### 按角色

| 角色 | 优先文档 |
|------|-------------------|
| Platform Engineer | 01, 02, 04, 11 |
| DevOps Engineer | 03, 04, 05 |
| SRE | 06, 07, 08, 09, 10 |
| Infrastructure Engineer | 01, 02, 11 |

---

## 与现有文档的关系

本运维指南以实践性、代码为中心的指南补充现有概念文档：

### 概念文档
- [EKS Auto Mode](../eks-auto-mode/README.md) - 架构和概念
- [ArgoCD](../gitops/argocd/README.md) - GitOps 基础
- [KEDA](../autoscaling/01-keda.md) - 事件驱动 autoscaling 概念
- [Karpenter](../autoscaling/02-karpenter.md) - Node provisioning 概念

### 本运维指南
- 用于生产基础设施的 Terraform HCL 代码
- 用于 Kubernetes resources 的 YAML manifests
- 用于可观测性的 PromQL/LogQL queries
- 用于运维自动化的 Bash scripts
- 带验证的分步流程

---

## 快速参考

### 常见操作

| 任务 | 文档 | 章节 |
|------|----------|---------|
| 创建新的 EKS cluster | [01-infrastructure-setup](./01-infrastructure-setup.md) | 3-Layer Terraform |
| 向 ArgoCD 添加新应用 | [04-gitops-multi-cluster](./04-gitops-multi-cluster.md) | ApplicationSet |
| 使用 custom metrics 配置 HPA | [06-scaling-strategies](./06-scaling-strategies.md) | Custom Metrics |
| 为新 service 设置告警 | [07-observability-alerts](./07-observability-alerts.md) | Alert Rules |
| 升级 EKS version | [11-upgrade-operations](./11-upgrade-operations.md) | Auto Mode Upgrade |

### 应急流程

| 场景 | 文档 | 章节 |
|----------|----------|---------|
| 回滚 deployment | [04-gitops-multi-cluster](./04-gitops-multi-cluster.md) | Rollback |
| 回滚 EKS upgrade | [11-upgrade-operations](./11-upgrade-operations.md) | Blue/Green Rollback |
| 为节省成本而缩容 | [06-scaling-strategies](./06-scaling-strategies.md) | Emergency Scale |
| 调试失败的 pods | [08-observability-analysis](./08-observability-analysis.md) | Log Analysis |

---

## 贡献

添加新的运维流程时：

1. 包含实用代码示例（Terraform、YAML、bash）
2. 为每个流程提供验证步骤
3. 在适用时记录回滚流程
4. 添加相关 PromQL/LogQL queries 用于监控
5. 交叉引用相关概念文档
