# 实验指南

> **最后更新**: February 22, 2026

本节提供用于练习 Kubernetes 及相关技术的动手实验指南。每个实验都包含分步说明和验证方法，帮助你在真实环境中确认理论学习的内容。

## 实验列表

| # | 实验 | 难度 | 前提条件 |
|---|-----|------------|---------------|
| 1 | [Linux 基础实验](basics/01-linux-basics-lab.md) | 初级 | Linux terminal 访问权限 |
| 2 | [Linux 高级技能实验](basics/02-linux-advanced-lab.md) | 初级 | 已完成 Linux 基础 |
| 3 | [Container 技术实验](basics/03-container-technology-lab.md) | 初级 | 已安装 Docker |
| 4 | [Pods and Workloads 实验](core/02-pods-and-workloads-lab.md) | 初级 | kubectl, K8s cluster |
| 5 | [Services and Networking 实验](core/03-services-networking-lab.md) | 中级 | kubectl, K8s cluster |
| 6 | [Storage 实验](core/04-storage-lab.md) | 中级 | kubectl, K8s cluster |
| 7 | [ConfigMap and Secret 实验](core/05-configuration-secrets-lab.md) | 初级 | kubectl, K8s cluster |
| 8 | [EKS Cluster 创建实验](eks/01-eks-cluster-creation-lab.md) | 中级 | AWS CLI, eksctl |
| 9 | [可观测性 E2E：系列介绍](observability/README.md) | 高级 | AWS account, Terraform, Helm |
| 10 | [可观测性 E2E：基础设施设置](observability/01-infrastructure-setup-lab.md) | 中级 | 已完成第 0 部分 |
| 11 | [可观测性 E2E：Observability Stack](observability/02-observability-stack-lab.md) | 高级 | 已完成第 1 部分 |
| 12 | [可观测性 E2E：MSA Deployment 和 Canary](observability/03-msa-deployment-lab.md) | 高级 | 已完成第 2 部分 |
| 13 | [可观测性 E2E：Load Testing 和 Autoscaling](observability/04-load-testing-scaling-lab.md) | 中级 | 已完成第 3 部分 |
| 14 | [可观测性 E2E：Alerting 和 AIOps](observability/05-alerting-aiops-lab.md) | 高级 | 已完成第 4 部分 |
| 15 | [可观测性 E2E：分布式追踪分析](observability/06-distributed-tracing-lab.md) | 高级 | 已完成第 5 部分 |

## 推荐学习路径

1. **基础实验** (1→2→3)：学习 Linux 和 Container 技术
2. **核心实验** (4→7→5→6)：使用 Kubernetes core resources
3. **EKS 实验** (8)：在真实 cloud environment 中操作 cluster
4. **可观测性实验** (9→10→11→12→13→14→15)：构建并运行端到端 observability stack

## 实验环境设置

### 本地环境（用于基础/Container 实验）
- Linux terminal（WSL2, macOS Terminal, or Linux）
- Docker Desktop 或 Docker Engine

### Kubernetes 环境（用于核心实验）
```bash
# Install and start minikube
curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
sudo install minikube-linux-amd64 /usr/local/bin/minikube
minikube start

# Install kubectl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install kubectl /usr/local/bin/kubectl
```

### AWS 环境（用于 EKS 实验）
- 已配置 AWS account 和 AWS CLI
- 已安装 eksctl

## 实验提示

- 首先检查每个实验的 **前提条件**
- 运行命令后，与 **预期输出** 进行比较以验证操作是否正确
- 遇到困难时使用 **提示**
- 完成实验后，务必运行 **清理** 部分中的命令以删除资源
