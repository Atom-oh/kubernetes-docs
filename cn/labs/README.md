# 实验指南


> **最后更新**：2026年11月21日

本节提供实践实验指南，帮助你练习 Kubernetes 及相关技术。每个实验都包含分步说明和验证方法，让你能够在真实环境中确认自己对理论知识的掌握情况。

## 实验列表

| # | 实验 | 难度 | 前置条件 |
|---|-----|------------|---------------|
| 1 | [Linux 基础实验](basics/01-linux-basics-lab.md) | 初级 | 可访问 Linux 终端 |
| 2 | [Linux 进阶技能实验](basics/02-linux-advanced-lab.md) | 初级 | 已完成 Linux 基础学习 |
| 3 | [容器技术实验](basics/03-container-technology-lab.md) | 初级 | 已安装 Docker |
| 4 | [Pod 和工作负载实验](core/02-pods-and-workloads-lab.md) | 初级 | kubectl、K8s 集群 |
| 5 | [Service 和网络实验](core/03-services-networking-lab.md) | 中级 | kubectl、K8s 集群 |
| 6 | [存储实验](core/04-storage-lab.md) | 中级 | kubectl、K8s 集群 |
| 7 | [ConfigMap 和 Secret 实验](core/05-configuration-secrets-lab.md) | 初级 | kubectl、K8s 集群 |
| 8 | [EKS 集群创建实验](eks/01-eks-cluster-creation-lab.md) | 中级 | AWS CLI、eksctl |
| 9 | [可观测性端到端：系列介绍](observability/README.md) | 高级 | 已批准的 AWS 环境、Helm、Python |
| 10 | [可观测性端到端：基础设施设置](observability/01-infrastructure-setup-lab.md) | 中级 | 已阅读系列介绍并准备好网络 |
| 11 | [可观测性端到端：可观测性技术栈](observability/02-observability-stack-lab.md) | 高级 | 已完成第 1 部分 |
| 12 | [可观测性端到端：MSA 部署与金丝雀发布](observability/03-msa-deployment-lab.md) | 高级 | 已完成第 2 部分 |
| 13 | [可观测性端到端：负载测试与自动扩缩容](observability/04-load-testing-scaling-lab.md) | 中级 | 已完成第 3 部分 |
| 14 | [可观测性端到端：告警与 AIOps](observability/05-alerting-aiops-lab.md) | 高级 | 已完成第 4 部分 |
| 15 | [可观测性端到端：分布式追踪分析](observability/06-distributed-tracing-lab.md) | 高级 | 已完成第 5 部分 |
| 16 | [EKS 工作负载 IAM 迁移实验](security/17-eks-workload-identity-migration-lab.md) | 高级 | 现有 EKS 集群、AWS CLI、kubectl、jq |

## 推荐学习路径

1. **基础实验**（1→2→3）：学习 Linux 和容器技术
2. **核心实验**（4→7→5→6）：使用 Kubernetes 核心资源
3. **EKS 实验**（8）：在真实云环境中操作集群
4. **可观测性实验**（9→10→11→12→13→14→15）：构建和运维端到端的可观测性技术栈
5. **安全实验**（16）：将 EKS 工作负载的 IAM 从节点角色迁移到 IRSA 和 Pod Identity

## 实验环境设置

### 本地环境（适用于基础/容器实验）
- Linux 终端（WSL2、macOS 终端或 Linux）
- Docker Desktop 或 Docker Engine

### Kubernetes 环境（适用于核心实验）
请为你的操作系统和 CPU 架构安装相应工具，并遵循各实验对集群和版本的要求。请勿在 macOS 或 ARM 上原样安装 Linux AMD64 二进制文件。

```bash
kubectl version --client
kubectl config current-context
```

### AWS 环境（适用于 EKS 实验）
- 已配置 AWS 账户和 AWS CLI
- 已安装 eksctl

## 实验提示

- 先检查每个实验的**前置条件**
- 运行命令后，将结果与**预期输出**进行比较，以验证操作是否正确
- 遇到困难时使用**提示**
- 完成实验后，务必运行**清理**部分中的命令来删除资源
