# ArgoCD

> **审查基线**：Argo CD 3.5.2、Argo Rollouts 1.10.0；在审查发行说明后，Argo CD manifest 固定版本更新至补丁版本 3.5.4（示例未重新运行）
> **最后更新**：October 12, 2026

## 目录
- [什么是 ArgoCD？](#what-is-argocd)
- [主要优势](#key-benefits)
- [架构概览](#architecture-overview)
- [核心概念](#core-concepts)
- [子指南导航](#sub-guide-navigation)
- [快速开始](#quick-start)
- [版本兼容性](#version-compatibility)

## 什么是 ArgoCD？

ArgoCD 是一款面向 Kubernetes 的声明式 GitOps 持续交付工具。它通过将 Git 仓库中定义的期望状态与集群中的实际状态同步，自动将应用程序部署到 Kubernetes 集群。

Argo CD 是 CNCF 毕业项目 Argo 的一部分。仅凭采用该项目并不能证明其适合某项特定的安全性或可用性要求。

![架构图：展示 ArgoCD 的控制平面通过 Repo Server 从 Git、Helm 和 OCI 源获取 manifest，Application Controller 将其协调并同步到受管 Kubernetes 集群；用户则可通过 Web UI、CLI 或 gRPC API 访问 API Server。](../../.gitbook/assets/en-gitops-argocd-overview-0.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-gitops-argocd-overview-0.html)

## 主要优势

### GitOps 原生

- **Git 作为唯一事实来源**：所有应用程序配置均存储在 Git 中
- **声明式部署**：定义期望状态，其余工作由 ArgoCD 处理
- **审计追踪**：通过 Git commit 获得所有变更的完整历史记录
- **回滚**：重新部署保留的配置修订版本；数据库/外部状态恢复需另行处理

### 多集群管理

- **集中式控制**：通过单个 ArgoCD 实例管理数百个集群
- **ApplicationSet**：基于模板的多集群部署
- **Cluster Generator**：基于标签动态选择目标集群

### 企业就绪

- **RBAC**：细粒度的基于角色的访问控制
- **SSO 集成**：直接使用 OIDC，或通过受支持的 Dex connector 连接其他身份提供商
- **多租户**：基于 Project 的隔离
- **高可用性**：生产就绪的 HA 部署

### 开发者体验

- **Web UI**：可视化应用程序管理和监控
- **CLI**：功能完备的命令行界面
- **通知**：Slack、Teams、电子邮件、webhook 集成
- **运行状况监控**：内置和自定义运行状况检查

## 架构概览

### 核心组件

| 组件 | 描述 | 副本数 (HA) |
|-----------|-------------|---------------|
| **API Server** | 处理所有 API 请求、身份验证和 RBAC | 2+ |
| **Repository Server** | 克隆仓库、生成 manifest、缓存结果 | 2+ |
| **Application Controller** | 监控应用程序并协调状态 | 2+（分片） |
| **Redis** | 用于 repo server 和 controller 的缓存层 | 3 (HA) |
| **Dex** | 可选的身份 broker；捆绑的内存存储无法通过增加副本安全地扩展 | 标准捆绑包中为 1 |
| **Notification Controller** | 在事件发生时发送通知 | 1+ |
| **ApplicationSet Controller** | 管理 ApplicationSet 资源 | 1+ |

### 数据流

![时序图：展示用户通过 API Server 创建 ArgoCD Application，该 Server 经由 Repo Server 渲染 manifest，随后 Application Controller 在协调循环中持续将期望状态与 Kubernetes 中的实际状态进行比较，并在发生漂移时应用变更。](../../.gitbook/assets/en-gitops-argocd-overview-1.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-gitops-argocd-overview-1.html)

## 核心概念

### Application

Application CRD 是 ArgoCD 中的主要资源。它定义：
- **Source**：从何处获取 manifest（Git repo、Helm chart、OCI）
- **Destination**：部署到何处（cluster 和 namespace）
- **Sync Policy**：如何处理同步

### Project

Project 提供逻辑分组和访问控制：
- 限制可使用的仓库
- 限制目标 cluster 和 namespace
- 定义允许/拒绝的资源

### ApplicationSet

ApplicationSet 支持使用 generator 通过单个定义管理多个应用程序：
- **List Generator**：静态值列表
- **Cluster Generator**：定位已注册的 cluster
- **Git Generator**：扫描仓库目录/文件
- **Matrix/Merge**：组合多个 generator

### Sync

同步使 cluster 状态与期望状态保持一致：
- **Manual Sync**：由用户触发
- **Auto Sync**：在 Git 变更时自动执行
- **Self-Heal**：自动纠正漂移
- **Prune**：移除孤立资源

## 子指南导航

| 指南 | 描述 |
|-------|-------------|
| [安装](01-installation.md) | 安装方法、CLI 设置、HA 配置、EKS 集成 |
| [应用程序](02-applications.md) | Application CRD、源类型、运行状况检查、hook、App of Apps |
| [同步策略](03-sync-strategies.md) | 同步策略、wave、window、差异比较、重试配置 |
| [ApplicationSet](04-applicationsets.md) | 所有 generator、模板化、渐进式同步、多集群模式 |
| [流量管理](05-traffic-management.md) | Argo Rollouts、蓝绿、金丝雀、分析、ingress 集成 |
| [Project 与 RBAC](06-projects-rbac.md) | AppProject、RBAC 策略、多租户、JWT token |
| [安全性](07-security.md) | SSO 集成、secret 管理、TLS、审计日志 |
| [通知](08-notifications.md) | 通知服务、trigger、template、subscription |
| [最佳实践](09-best-practices.md) | 仓库模式、性能调优、故障排除、EKS 提示 |
| [Rollouts Experiments 深入解析](10-rollouts-experiment.md) | Experiment CRD、短暂 ReplicaSet 验证、AnalysisRun 判定 |

## 快速开始

### 1. 安装 ArgoCD

这是一个自行管理的非 HA 评估示例。请准备兼容的 cluster、CRD/RBAC 权限和空的专用 namespace；有关生产 HA/身份验证/升级决策，请使用[安装指南](01-installation.md)。

```bash
# Create namespace
kubectl create namespace argocd

# Install ArgoCD
kubectl apply --server-side -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/v3.5.4/manifests/install.yaml

# Wait for pods to be ready
kubectl wait --for=condition=Ready pods --all -n argocd --timeout=300s
```

### 2. 访问 UI

```bash
# Port forward to access locally
kubectl port-forward svc/argocd-server -n argocd 8080:443
```

### 3. 获取初始密码

```bash
# Retrieve the initial admin password
kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath="{.data.password}" | base64 -d && echo
```

### 4. 通过 CLI 登录

如[安装指南](01-installation.md)所示，安装匹配的 OS/架构 CLI，并验证发行版 checksum。请在另一个终端中保持端口转发运行。

```bash
# Install CLI (macOS)
brew install argocd

# Login
argocd login localhost:8080

# Change the bootstrap password
argocd account update-password
kubectl -n argocd delete secret argocd-initial-admin-secret
```

### 5. 部署您的第一个应用程序

```bash
# Create application via CLI
argocd app create guestbook \
  --repo https://github.com/argoproj/argocd-example-apps.git \
  --path guestbook \
  --dest-server https://kubernetes.default.svc \
  --dest-namespace default

# Sync the application
argocd app sync guestbook
```

或者以声明式方式：

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: guestbook
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/argoproj/argocd-example-apps.git
    targetRevision: HEAD
    path: guestbook
  destination:
    server: https://kubernetes.default.svc
    namespace: default
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
```

## 版本兼容性

审查的基线为 **Argo CD 3.5.2 / Helm chart 10.8.4**；在审查发行说明后，manifest 示例已更新至补丁版本 3.5.4（未重新运行）。Chart 10.8.4 仍部署 Argo CD v3.5.2；3.5.4 首次在 chart 10.9.7 中发布。Application 和 installation chart 的版本不同。Argo CD 为最近三个 minor 版本线提供补丁；更早的版本线已 EOL。

### 已测试的 Kubernetes 组合

| Argo CD | Kubernetes |
|---|---|
| 3.5 | 1.36, 1.35, 1.34, 1.33 |
| 3.4 | 1.35, 1.34, 1.33, 1.32 |
| 3.3 | 1.35, 1.34, 1.33, 1.32 |

这是在 3.5.4 仓库中记录的上游测试矩阵。它不同于 chart 的最低 kubeVersion 约束、Kubernetes/EKS 支持窗口和受管 Argo CD 版本策略。EKS minor 版本与 Argo CD minor 版本之间不存在一对一映射。

### 近期发行版本

- 3.5.0：发布于 **2026-08-04**。请查看迁移指南，了解包括 server 的 Helm 4 renderer 在内的变更。
- 3.5.1：发布于 2026-08-12。
- 3.5.2：发布于 2026-08-27。
- 3.5.3：发布于 2026-09-14。错误修复（运行状况检查、同步重试状态、UI）。
- 3.5.4：发布于 2026-10-06。这是一次**安全补丁发行版**：它修复了四个 CRITICAL 问题——通过 Kustomize remote ref 和 Kustomize Helm config home 在 repo-server 中执行命令、通过 Jsonnet import 在 repo-server 中读取文件，以及通过 PreDelete/PostDelete hook 绕过 AppProject 限制（CVE-2026-77459）——相同的修复也已回移至 v3.4.10/v3.3.15。行为变更：Kustomize build 不再遵循 `helmGlobals.configHome`，且会拒绝超过 4 MiB 的 OCI manifest；升级前请查看[发行说明](https://github.com/argoproj/argo-cd/releases/tag/v3.5.4)。
- [3.6.0-rc1](https://github.com/argoproj/argo-cd/releases/tag/v3.6.0-rc1)：3.6 版本线的首个发行候选版，发布于 2026-09-15。并非生产基线。

### 2026 年 10 月更新：Argo CD 4.0 愿景规划启动

根据 [9 月 30 日 CNCF 博文](https://www.cncf.io/blog/2026/09/30/argocon-north-america-2026-what-to-expect-as-the-argo-community-looks-toward-cd-4-0/)，Argo 社区已启动 Argo CD 4.0 的愿景规划流程；ArgoCon North America 2026（与 KubeCon NA 同期举办的全天双轨活动）将以维护者的主题演讲开幕，涵盖近期进展和即将推出的版本。这仍处于早期路线图方向设定阶段；4.0 的功能和时间尚未确定。

### Argo Rollouts

Rollouts 是一个独立的 controller，可在没有 Argo CD 的情况下使用。本次审查使用其 1.10.0 文档。请验证 Rollouts CRD/controller、流量 plugin、Kubernetes 以及 Argo CD 运行状况检查集成，而非映射无关产品的版本号。

### EKS 托管 Argo CD 能力

EKS 的 Argo CD Capability 与自行管理的安装是不同的运行模式。其自定义配置仅适用于**受支持的** argocd-cm key，且必须位于由 Capability 配置的 namespace 中，并带有标签 `app.kubernetes.io/part-of: argocd`。不受支持的 key/flag 会被忽略；请勿假定可使用标准 Lua library 或任意执行 plugin。请参阅[托管配置指南](https://docs.aws.amazon.com/eks/latest/userguide/argocd-configure-settings.html)。

## 后续步骤

1. **[安装指南](01-installation.md)**：为生产环境设置 ArgoCD
2. **[应用程序指南](02-applications.md)**：了解 Application CRD
3. **[ApplicationSet 指南](04-applicationsets.md)**：多集群部署

## 资源

- [ArgoCD 官方文档](https://argo-cd.readthedocs.io/)
- [ArgoCD GitHub 仓库](https://github.com/argoproj/argo-cd)
- [Argo Rollouts 文档](https://argoproj.github.io/argo-rollouts/)
- [CNCF ArgoCD 项目页面](https://www.cncf.io/projects/argo/)

## 测验

为测试您的学习成果，请尝试 [ArgoCD 安装测验](../../quizzes/gitops/argocd/01-installation-quiz.md)。

### 带版本的审查来源

- [Argo CD 3.5.4 已测试的 Kubernetes 版本](https://github.com/argoproj/argo-cd/blob/v3.5.4/docs/operator-manual/tested-kubernetes-versions.md)
- [发行版支持策略](https://github.com/argoproj/argo-cd/blob/v3.5.4/docs/developer-guide/release-process-and-cadence.md)
- [3.5.0 发行版](https://github.com/argoproj/argo-cd/releases/tag/v3.5.0)
- [3.5.2 发行版](https://github.com/argoproj/argo-cd/releases/tag/v3.5.2)
- [3.5.3 发行版](https://github.com/argoproj/argo-cd/releases/tag/v3.5.3)
- [3.5.4 发行版](https://github.com/argoproj/argo-cd/releases/tag/v3.5.4)
- [Chart 10.9.7（包含 Argo CD 3.5.4 的首个 chart）](https://github.com/argoproj/argo-helm/releases/tag/argo-cd-10.9.7)
- [HA 组件行为](https://github.com/argoproj/argo-cd/blob/v3.5.4/docs/operator-manual/high_availability.md)
