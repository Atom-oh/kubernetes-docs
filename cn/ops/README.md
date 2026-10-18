# 运维指南

> **最后更新**：2026 年 9 月 12 日

本节为 EKS Auto Mode 环境提供生产运维指南，涵盖 Terraform 基础设施预置、CI/CD 流水线、基于 GitOps 的部署、扩缩容、可观测性、资源优化和升级。

---

## 目标读者

- **平台工程师**：使用 EKS Auto Mode 构建生产环境
- **基础设施工程师**：运维基于 Terraform/Terragrunt 的 IaC
- **DevOps 工程师**：使用 GitLab CI 和 ArgoCD 构建 CI/CD 流水线
- **SRE**：运维 Prometheus、Grafana 和 Loki 可观测性栈

---

## 前置条件

开始本运维指南前，请确保熟悉以下内容：

- [EKS Auto Mode 入门](../eks-auto-mode/01-getting-started.md)
- Terraform 基础知识（resources、modules、state management）
- [Kubernetes 核心概念](../core/01-cluster-architecture.md)
- kubectl 和 Helm CLI 的使用

---

## 目录

| # | 文档 | 关键主题 |
|---|----------|------------|
| 01 | [Terraform 三层基础设施设置](./01-infrastructure-setup.md) | VPC、EKS Auto Mode、使用三层 Terraform 配置 Pod Identity |
| 02 | [NLB 加权路由和蓝绿部署](./02-infrastructure-advanced.md) | 双集群架构、NLB 权重、DNS 路由 |
| 03 | [CI 流水线](./03-ci-pipelines.md) | ECR、GitLab Runner、GitHub ARC、多平台构建 |
| 04 | [ArgoCD 多集群](./04-gitops-multi-cluster.md) | Hub-spoke、ApplicationSet、IAM Identity Center SSO |
| 05 | [GitOps 自动化](./05-gitops-automation.md) | Atlantis、FluxCD、Terraform Cloud、AIOps |
| 06 | [扩缩容策略](./06-scaling-strategies.md) | HPA 自定义指标、KEDA、VPA、Spot 利用率 |
| 07 | [运维告警配置](./07-observability-alerts.md) | 网络/CPU/磁盘/Auto Mode 节点终止告警 |
| 08 | [可观测性分析](./08-observability-analysis.md) | 日志/指标/追踪关联、PromQL、LogQL、TraceQL |
| 09 | [可观测性栈运维](./09-observability-stack.md) | Loki、Tempo、Prometheus/AMP 的安装与运维 |
| 10 | [资源优化](./10-resource-optimization.md) | Requests/Limits、JVM 调优、针对不同框架的指南 |
| 11 | [EKS 升级](./11-upgrade-operations.md) | 分阶段升级 Auto Mode、蓝绿策略 |
| 12 | [事件容量规划](./12-event-capacity-planning.md) | 流量事件、容量与恢复规划 |
| 13 | [FinOps 成本管理](./13-finops-cost-platform.md) | 成本可见性、分摊与优化 |
| 14 | [Tekton 流水线](./14-tekton-pipelines.md) | Kubernetes 原生 CI 流水线 |
| 15 | [可用区集群运维](./15-zonal-operations-guide.md) | LB 权重切换与 TargetGroupBinding、原生回滚、Kafka/Redis/Aurora 可用区亲和读取 |
| 16 | [故障排除手册](./16-troubleshooting-playbook.md) | 症状 → 诊断 → 原因 → 修复：Pending/ImagePull/CrashLoop/NotReady/PVC、IRSA、VPC CNI、Karpenter、kubectl 速查表 |
| 17 | [EKS Spot 生产实验](./17-spot-production-experiments.md) | 中断、并发回收、回退、结果记录、SLO/成本评估与回滚 |

---

## 学习路径

### 推荐顺序

1. **基础设施**（01–02）：使用 Terraform 预置 VPC/EKS
2. **CI/CD**（03–05）：构建流水线并部署 GitOps
3. **扩缩容**（06）：为工作负载制定扩缩容策略
4. **可观测性**（07–09）：构建监控、告警和分析系统
5. **优化**（10）：提升资源效率并优化成本
6. **升级**（11）：验证可用性和恢复流程
7. **专项运维**（12–16）：容量事件、FinOps、Tekton、可用区运维和故障排除

### 按角色

| 角色 | 优先阅读文档 |
|------|-------------------|
| 平台工程师 | 01、02、04、11 |
| DevOps 工程师 | 03、04、05 |
| SRE | 06、07、08、09、10 |
| 基础设施工程师 | 01、02、11 |

---

## 与现有文档的关系

本运维指南以实践性、代码为中心的内容补充现有概念文档：

### 概念文档
- [EKS Auto Mode](../eks-auto-mode/README.md) - 架构和概念
- [ArgoCD](../gitops/argocd/README.md) - GitOps 基础
- [KEDA](../autoscaling/01-keda.md) - 事件驱动扩缩容概念
- [Karpenter](../autoscaling/02-karpenter.md) - 节点预置概念

### 本运维指南
- 用于生产基础设施的 Terraform HCL 代码
- 用于 Kubernetes 资源的 YAML manifest
- 用于可观测性的 PromQL/LogQL 查询
- 用于运维自动化的 Bash 脚本
- 包含验证步骤的分步流程

---

## 快速参考

### 常见操作

| 任务 | 文档 | 章节 |
|------|----------|---------|
| 创建新的 EKS 集群 | [01-infrastructure-setup](./01-infrastructure-setup.md) | 三层 Terraform |
| 向 ArgoCD 添加新应用 | [04-gitops-multi-cluster](./04-gitops-multi-cluster.md) | ApplicationSet |
| 使用自定义指标配置 HPA | [06-scaling-strategies](./06-scaling-strategies.md) | 自定义指标 |
| 为新服务配置告警 | [07-observability-alerts](./07-observability-alerts.md) | 告警规则 |
| 升级 EKS 版本 | [11-upgrade-operations](./11-upgrade-operations.md) | Auto Mode 升级 |

### 紧急流程

| 场景 | 文档 | 章节 |
|----------|----------|---------|
| 回滚部署 | [04-gitops-multi-cluster](./04-gitops-multi-cluster.md) | 回滚 |
| 回滚 EKS 升级 | [11-upgrade-operations](./11-upgrade-operations.md) | 原生回滚条件或蓝绿切回 |
| 检查需求与可用容量后调整容量 | [06-scaling-strategies](./06-scaling-strategies.md) | 容量与扩缩容策略 |
| 排查故障 Pod | [16-troubleshooting-playbook](./16-troubleshooting-playbook.md) | 按症状诊断 |

---

## 贡献

添加新的运维流程时：

1. 包含实用代码示例（Terraform、YAML、bash）
2. 为每个流程提供验证步骤
3. 在适用时记录回滚流程
4. 添加相关 PromQL/LogQL 监控查询
5. 交叉引用相关概念文档
