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

ArgoCD 是适用于 Kubernetes 的声明式 GitOps 持续交付工具。它通过将 Git 仓库中定义的期望状态与集群中的实际状态同步，自动将应用程序部署到 Kubernetes 集群。

Argo CD 是 CNCF Graduated Argo 项目的一部分。仅凭其被采用，并不能证明它适合特定的安全性或可用性要求。

![架构图展示了 ArgoCD 的控制平面如何通过其 Repo Server 从 Git、Helm 和 OCI 源获取 manifest，Application Controller 则将它们协调并同步到受管理的 Kubernetes 集群；用户可通过 Web UI、CLI 或 gRPC API 访问 API Server。](../../.gitbook/assets/en-gitops-argocd-overview-0.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-gitops-argocd-overview-0.html)

## 主要优势

### GitOps 原生

- **Git 作为唯一事实来源**：所有应用程序配置均存储在 Git 中
- **声明式部署**：定义期望状态，其余工作由 ArgoCD 处理
- **审计跟踪**：通过 Git commit 保留所有变更的完整历史记录
- **回滚**：重新部署保留的配置修订版本；数据库/外部状态恢复需另行处理

### 多集群管理

- **集中式控制**：通过单个 ArgoCD 实例管理数百个集群
- **ApplicationSet**：基于模板的多集群部署
- **Cluster Generator**：基于标签动态定位集群

### 企业就绪

- **RBAC**：细粒度的基于角色的访问控制
- **SSO 集成**：直接 OIDC，或使用支持的 Dex connector 连接其他身份提供商
- **多租户**：基于项目的隔离
- **高可用性**：生产就绪的 HA 部署

### 开发者体验

- **Web UI**：可视化的应用程序管理与监控
- **CLI**：功能完备的命令行界面
- **通知**：Slack、Teams、电子邮件、webhook 集成
- **运行状况监控**：内置和自定义运行状况检查

## 架构概览

### 核心组件

| 组件 | 描述 | 副本数（HA） |
|-----------|-------------|---------------|
| **API Server** | 处理所有 API 请求、身份验证和 RBAC | 2+ |
| **Repository Server** | 克隆仓库、生成 manifest、缓存结果 | 2+ |
| **Application Controller** | 监控应用程序、协调状态 | 2+（分片） |
| **Redis** | Repo Server 和 controller 的缓存层 | 3（HA） |
| **Dex** | 可选的身份 broker；捆绑的内存存储无法通过增加副本安全地扩展 | 标准捆绑包中为 1 |
| **Notification Controller** | 在事件发生时发送通知 | 1+ |
| **ApplicationSet Controller** | 管理 ApplicationSet 资源 | 1+ |

### 数据流

![时序图展示了用户通过 API Server 创建 ArgoCD 应用程序，该服务器通过 Repo Server 渲染 manifest；随后 Application Controller 在协调循环中反复针对 Kubernetes 比较期望状态和实际状态，并在发生漂移时应用变更。](../../.gitbook/assets/en-gitops-argocd-overview-1.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-gitops-argocd-overview-1.html)

## 核心概念

### Application

Application CRD 是 ArgoCD 中的主要资源。它定义：
- **源**：从何处获取 manifest（Git 仓库、Helm chart、OCI）
- **目标**：部署到何处（集群和 namespace）
- **Sync 策略**：如何处理同步

### Project

Project 提供逻辑分组和访问控制：
- 限制可使用的仓库
- 限制目标集群和 namespace
- 定义允许/拒绝的资源

### ApplicationSet

ApplicationSet 使用 generator，使得可通过单个定义管理多个应用程序：
- **List Generator**：静态值列表
- **Cluster Generator**：定位已注册的集群
- **Git Generator**：扫描仓库目录/文件
- **Matrix/Merge**：组合多个 generator

### Sync

同步使集群状态与期望状态一致：
- **手动 Sync**：由用户触发
- **自动 Sync**：Git 变更时自动执行
- **Self-Heal**：自动纠正漂移
- **Prune**：移除孤立资源

## 子指南导航

| 指南 | 描述 |
|-------|-------------|
| [安装](01-installation.md) | 安装方法、CLI 设置、HA 配置、EKS 集成 |
| [应用程序](02-applications.md) | Application CRD、源类型、运行状况检查、hook、App of Apps |
| [Sync 策略](03-sync-strategies.md) | Sync 策略、wave、窗口、差异比较、重试配置 |
| [ApplicationSet](04-applicationsets.md) | 所有 generator、模板、渐进式 Sync、多集群模式 |
| [流量管理](05-traffic-management.md) | Argo Rollouts、蓝绿、金丝雀、分析、ingress 集成 |
| [Project 和 RBAC](06-projects-rbac.md) | AppProject、RBAC 策略、多租户、JWT token |
| [安全性](07-security.md) | SSO 集成、secret 管理、TLS、审计日志记录 |
| [通知](08-notifications.md) | 通知服务、触发器、模板、订阅 |
| [最佳实践](09-best-practices.md) | 仓库模式、性能调优、故障排除、EKS 提示 |
| [Rollouts Experiments 深入解析](10-rollouts-experiment.md) | Experiment CRD、临时 ReplicaSet 验证、AnalysisRun 判定 |

## 快速开始

### 1. 安装 ArgoCD

这是一个自行管理的非 HA 评估示例。请准备兼容的集群、CRD/RBAC 权限以及一个空的专用 namespace；有关生产 HA/身份验证/升级决策，请使用[安装指南](01-installation.md)。

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

请安装与操作系统/架构相匹配的 CLI，并按照[安装指南](01-installation.md)所示验证发行版 checksum。请在另一个终端中保持端口转发运行。

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

或者使用声明式方式：

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

审查的基线为 **Argo CD 3.5.2 / Helm chart 10.8.4**；在审查发行说明后，manifest 示例已更新至补丁版本 3.5.4（未重新运行）。Chart 10.8.4 仍部署 Argo CD v3.5.2；3.5.4 首次随 chart 10.9.7 发布。Application 与安装 chart 的版本不同。Argo CD 为最近三个 minor 版本线提供补丁；较旧的版本线已 EOL。

### 已测试的 Kubernetes 组合

| Argo CD | Kubernetes |
|---|---|
| 3.5 | 1.36, 1.35, 1.34, 1.33 |
| 3.4 | 1.35, 1.34, 1.33, 1.32 |
| 3.3 | 1.35, 1.34, 1.33, 1.32 |

这是 3.5.4 仓库中记录的上游测试矩阵。它与 chart 的最低 kubeVersion 约束、Kubernetes/EKS 支持窗口以及托管 Argo CD 版本策略不同。不存在 EKS minor 版本与 Argo CD minor 版本的一一对应关系。

### 最近发布版本

- 3.5.0：发布于 **2026-08-04**。请查看迁移指南，了解包括服务器 Helm 4 renderer 在内的变更。
- 3.5.1：发布于 2026-08-12。
- 3.5.2：发布于 2026-08-27。
- 3.5.3：发布于 2026-09-14。错误修复（运行状况检查、Sync 重试状态、UI）。
- 3.5.4：发布于 2026-10-06。安全修复，包括 repo-server 和 AppProject hook 处理中四个评级为 CRITICAL 的问题。发行说明列出了两项可能造成破坏性影响的变更：渲染 Helm chart 的 Kustomize build 不再遵循 `helmGlobals.configHome`，且大于 4 MiB 的 OCI manifest 会被拒绝。请查看官方发行版以了解当前受支持的版本线。

### Argo Rollouts

Rollouts 是单独的 controller，也可在不使用 Argo CD 的情况下使用。本审查使用其 1.10.0 文档。请验证 Rollouts CRD/controller、流量 plugin、Kubernetes 以及 Argo CD 运行状况检查集成，而非映射无关的产品版本号。

### EKS 托管 Argo CD 功能

EKS 的 Argo CD Capability 是一种不同于自行管理安装的运行模式。其自定义配置仅适用于 **受支持的** argocd-cm key、capability 配置的 namespace，以及带有标签 `app.kubernetes.io/part-of: argocd` 的资源。不支持的 key/flag 会被忽略；不要假定标准 Lua library 或任意执行 plugin 可用。请参阅[托管配置指南](https://docs.aws.amazon.com/eks/latest/userguide/argocd-configure-settings.html)。

## 后续步骤

1. **[安装指南](01-installation.md)**：为生产环境设置 ArgoCD
2. **[应用程序指南](02-applications.md)**：了解 Application CRD
3. **[ApplicationSets 指南](04-applicationsets.md)**：多集群部署

## 资源

- [ArgoCD 官方文档](https://argo-cd.readthedocs.io/)
- [ArgoCD GitHub 仓库](https://github.com/argoproj/argo-cd)
- [Argo Rollouts 文档](https://argoproj.github.io/argo-rollouts/)
- [CNCF ArgoCD 项目页面](https://www.cncf.io/projects/argo/)

## 测验

要测试您所学的内容，请尝试 [ArgoCD 安装测验](../../quizzes/gitops/argocd/01-installation-quiz.md)。

### 版本化审查来源

- [Argo CD 3.5.4 已测试的 Kubernetes 版本](https://github.com/argoproj/argo-cd/blob/v3.5.4/docs/operator-manual/tested-kubernetes-versions.md)
- [发行版支持策略](https://github.com/argoproj/argo-cd/blob/v3.5.4/docs/developer-guide/release-process-and-cadence.md)
- [3.5.0 发布版](https://github.com/argoproj/argo-cd/releases/tag/v3.5.0)
- [3.5.2 发布版](https://github.com/argoproj/argo-cd/releases/tag/v3.5.2)
- [3.5.3 发布版](https://github.com/argoproj/argo-cd/releases/tag/v3.5.3)
- [3.5.4 发布版](https://github.com/argoproj/argo-cd/releases/tag/v3.5.4)
- [Chart 10.9.7（首个包含 Argo CD 3.5.4 的 chart）](https://github.com/argoproj/argo-helm/releases/tag/argo-cd-10.9.7)
- [HA 组件行为](https://github.com/argoproj/argo-cd/blob/v3.5.4/docs/operator-manual/high_availability.md)