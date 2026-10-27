# ArgoCD

> **审查基线**：Argo CD 3.5.2、Argo Rollouts 1.10.0；审阅发布说明后，将 Argo CD 清单中的版本固定值更新至补丁版本 3.5.5（未重新运行示例）
> **最后更新**：2026年10月26日

## 目录
- [什么是 ArgoCD？](#what-is-argocd)
- [主要优势](#key-benefits)
- [架构概览](#architecture-overview)
- [核心概念](#core-concepts)
- [子指南导航](#sub-guide-navigation)
- [快速入门](#quick-start)
- [版本兼容性](#version-compatibility)

## 什么是 ArgoCD？

ArgoCD 是一款面向 Kubernetes 的声明式 GitOps 持续交付工具。它通过将 Git 仓库中定义的期望状态与集群中的实际状态同步，自动将应用部署到 Kubernetes 集群。

Argo CD 是 CNCF 毕业级 Argo 项目的一部分。仅仅采用该项目，并不能证明它适用于特定的安全性或可用性要求。

![架构图展示了 ArgoCD 控制平面如何通过 Repo Server 从 Git、Helm 和 OCI 来源获取清单，Application Controller 如何协调这些清单并将其同步到受管 Kubernetes 集群，以及用户如何通过 Web UI、CLI 或 gRPC API 访问 API Server。](../../.gitbook/assets/en-gitops-argocd-overview-0.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-gitops-argocd-overview-0.html)

## 主要优势

### 原生支持 GitOps

- **Git 是唯一可信来源**：所有应用配置都存储在 Git 中
- **声明式部署**：定义期望状态，其余工作由 ArgoCD 处理
- **审计记录**：通过 Git 提交完整记录所有变更
- **回滚**：重新部署保留的配置修订版本；数据库/外部状态的恢复需单独处理

### 多集群管理

- **集中控制**：通过单个 ArgoCD 实例管理数百个集群
- **ApplicationSet**：基于模板的多集群部署
- **集群生成器**：根据标签动态选择目标集群

### 满足企业需求

- **RBAC**：精细的基于角色的访问控制
- **SSO 集成**：直接使用 OIDC，或使用受支持的 Dex 连接器对接其他身份提供商
- **多租户**：基于 Project 进行隔离
- **高可用性**：适用于生产环境的 HA 部署

### 开发者体验

- **Web UI**：直观地管理和监控应用
- **CLI**：功能齐全的命令行界面
- **通知**：集成 Slack、Teams、电子邮件和 webhook
- **运行状况监控**：内置和自定义运行状况检查

## 架构概览

### 核心组件

| 组件 | 描述 | 副本数（HA） |
|-----------|-------------|---------------|
| **API Server** | 处理所有 API 请求、身份验证和 RBAC | 2+ |
| **Repository Server** | 克隆仓库、生成清单并缓存结果 | 2+ |
| **Application Controller** | 监控应用并协调状态 | 2+（分片） |
| **Redis** | 为 repo server 和 controller 提供缓存层 | 3（HA） |
| **Dex** | 可选的身份代理；通过增加副本数无法安全扩展捆绑的内存存储 | 标准捆绑包中为 1 个 |
| **Notification Controller** | 针对事件发送通知 | 1+ |
| **ApplicationSet Controller** | 管理 ApplicationSet 资源 | 1+ |

### 数据流

![时序图展示了用户如何通过 API Server 创建 ArgoCD 应用，API Server 如何通过 Repo Server 渲染清单，随后 Application Controller 如何在协调循环中反复比较期望状态与 Kubernetes 中的实际状态，并在发现偏差时应用更改。](../../.gitbook/assets/en-gitops-argocd-overview-1.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-gitops-argocd-overview-1.html)

## 核心概念

### Application

Application CRD 是 ArgoCD 中的主要资源。它定义：
- **Source**：从何处获取清单（Git 仓库、Helm chart、OCI）
- **Destination**：部署到何处（集群和命名空间）
- **Sync Policy**：如何处理同步

### Project

Project 提供逻辑分组和访问控制：
- 限制可使用的仓库
- 限定目标集群和命名空间
- 定义允许/禁止的资源

### ApplicationSet

ApplicationSet 通过生成器，使用单个定义管理多个应用：
- **List Generator**：值的静态列表
- **Cluster Generator**：以已注册的集群为目标
- **Git Generator**：扫描仓库目录/文件
- **Matrix/Merge**：组合多个生成器

### Sync

同步会使集群状态与期望状态一致：
- **手动同步**：由用户触发
- **自动同步**：Git 变更时自动执行
- **自我修复**：自动纠正偏差
- **Prune**：移除孤立资源

## 子指南导航

| 指南 | 描述 |
|-------|-------------|
| [安装](01-installation.md) | 安装方法、CLI 设置、HA 配置、EKS 集成 |
| [应用](02-applications.md) | Application CRD、源类型、运行状况检查、钩子、App of Apps |
| [同步策略](03-sync-strategies.md) | 同步策略、波次、窗口、差异比较、重试配置 |
| [ApplicationSet](04-applicationsets.md) | 所有生成器、模板化、渐进式同步、多集群模式 |
| [流量管理](05-traffic-management.md) | Argo Rollouts、蓝绿部署、金丝雀发布、分析、Ingress 集成 |
| [Projects 与 RBAC](06-projects-rbac.md) | AppProject、RBAC 策略、多租户、JWT 令牌 |
| [安全](07-security.md) | SSO 集成、机密管理、TLS、审计日志记录 |
| [通知](08-notifications.md) | 通知服务、触发器、模板、订阅 |
| [最佳实践](09-best-practices.md) | 仓库模式、性能调优、故障排除、EKS 提示 |
| [Rollouts 实验深入解析](10-rollouts-experiment.md) | Experiment CRD、临时 ReplicaSet 验证、AnalysisRun 判定结果 |

## 快速入门

### 1. 安装 ArgoCD

这是一个用于评估的自主管理、非 HA 示例。请准备兼容的集群、CRD/RBAC 权限和一个专用的空命名空间；有关生产环境的 HA、身份验证和升级决策，请参阅[安装指南](01-installation.md)。

```bash
# Create namespace
kubectl create namespace argocd

# Install ArgoCD
kubectl apply --server-side -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/v3.5.5/manifests/install.yaml

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

请安装与操作系统/架构匹配的 CLI，并按照[安装指南](01-installation.md)中的说明验证发布校验和。在另一终端中保持端口转发运行。

```bash
# Install CLI (macOS)
brew install argocd

# Login
argocd login localhost:8080

# Change the bootstrap password
argocd account update-password
kubectl -n argocd delete secret argocd-initial-admin-secret
```

### 5. 部署第一个应用

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

或者采用声明式方式：

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

审查所依据的基线为 **Argo CD 3.5.2 / Helm chart 10.8.4**；审阅发布说明后，清单示例更新到了补丁版本 3.5.5（未重新运行）。Chart 10.8.4 仍会部署 Argo CD v3.5.2；3.5.5 首次随 chart 10.10.3 发布。应用版本与安装 chart 版本不同。Argo CD 为最近三个次要版本线提供补丁；更旧的版本线已停止支持。

### 已测试的 Kubernetes 版本组合

| Argo CD | Kubernetes |
|---|---|
| 3.5 | 1.36, 1.35, 1.34, 1.33 |
| 3.4 | 1.35, 1.34, 1.33, 1.32 |
| 3.3 | 1.35, 1.34, 1.33, 1.32 |

这是 3.5.5 仓库中记录的上游测试矩阵。它与 chart 的最低 kubeVersion 约束、Kubernetes/EKS 支持窗口以及托管 Argo CD 版本策略不同。EKS 次要版本与 Argo CD 次要版本之间并无一一对应关系。

### 近期发布

- 3.5.0：于 **2026年8月4日**发布。请查看迁移指南，了解包括服务器 Helm 4 渲染器在内的变更。
- 3.5.1：于 2026年8月12日发布。
- 3.5.2：于 2026年8月27日发布。
- 3.5.3：于 2026年9月14日发布。包含错误修复（运行状况检查、同步重试状态、UI）。
- 3.5.4：于 2026年10月6日发布。这是一个**安全补丁版本**：修复了四个 CRITICAL 问题，分别是通过 Kustomize 远程引用和 Kustomize Helm 配置目录在 repo-server 中执行命令、通过 Jsonnet 导入读取 repo-server 文件，以及通过 PreDelete/PostDelete 钩子绕过 AppProject 限制（CVE-2026-77459）。相同修复也回移植到了 v3.4.10/v3.3.15。行为变更：Kustomize 构建不再遵循 `helmGlobals.configHome`，并且超过 4 MiB 的 OCI 清单将被拒绝；升级前请查看[发布说明](https://github.com/argoproj/argo-cd/releases/tag/v3.5.4)。
- 3.5.5：于 2026年10月12日发布。这是一个错误修复补丁版本（修复过时的清单、CMP 失败后 repo-server 中的 goroutine 泄漏、OCI 缓存行为等）；v3.4.11/v3.3.16 也在同一天发布。请参阅[发布说明](https://github.com/argoproj/argo-cd/releases/tag/v3.5.5)。
- 3.5.6：于 2026年10月20日发布。这是一个错误修复补丁版本；v3.4.12（2026年10月21日）和 v3.3.17（2026年10月20日）在同一时间段内发布。请参阅[发布说明](https://github.com/argoproj/argo-cd/releases/tag/v3.5.6)。
- 3.3.18：于 2026年10月22日发布。该版本为 3.3 版本线提供了一项**安全修复**，不再信任已遭入侵的 eMudhra CA 证书（此次中间 CA 遭入侵事件于 2026年10月20日披露，并已在整个生态系统中修复）。请参阅[发布说明](https://github.com/argoproj/argo-cd/releases/tag/v3.3.18)。
- [3.6.0-rc1](https://github.com/argoproj/argo-cd/releases/tag/v3.6.0-rc1)：3.6 版本线的首个候选发布版本，于 2026年9月15日发布。并非生产基线。
- [3.6.0-rc3](https://github.com/argoproj/argo-cd/releases/tag/v3.6.0-rc3)：3.6 版本线的候选发布版本，于 2026年10月15日发布。同样并非生产基线。
- [3.6.0-rc4](https://github.com/argoproj/argo-cd/releases/tag/v3.6.0-rc4)：3.6 版本线的最新候选发布版本，于 2026年10月22日发布。同样并非生产基线。

### 2026年10月更新：Argo CD 4.0 愿景规划启动

根据[9月30日的 CNCF 博文](https://www.cncf.io/blog/2026/09/30/argocon-north-america-2026-what-to-expect-as-the-argo-community-looks-toward-cd-4-0/)，Argo 社区已启动 Argo CD 4.0 的愿景规划流程；与 KubeCon NA 同地举办的 ArgoCon North America 2026（全天、双轨道活动）将以维护者主题演讲开场，介绍近期进展和即将推出的版本。这仍处于路线图方向的早期规划阶段，4.0 的功能和时间安排尚未确定。

### Argo Rollouts

Rollouts 是独立的 controller，也可以在不使用 Argo CD 的情况下使用。本次审查参考了其 1.10.0 文档。请分别验证 Rollouts CRD/controller、流量插件、Kubernetes 以及 Argo CD 运行状况检查集成，而不要将彼此无关的产品版本号对应起来。

### EKS 托管 Argo CD 功能

EKS Capability for Argo CD 与自主管理安装属于不同的运行模式。其自定义配置仅适用于**受支持的** argocd-cm 键，且必须位于该功能配置的命名空间中，并带有标签 `app.kubernetes.io/part-of: argocd`。不支持的键/标志会被忽略；不要假设其中提供了标准 Lua 库或任意执行插件。请参阅[托管配置指南](https://docs.aws.amazon.com/eks/latest/userguide/argocd-configure-settings.html)。

在 2026年10月的测试中，即使是本地集群，也必须使用包含其 EKS ARN 的集群 Secret 进行注册；自动创建的访问条目只有在同时附加 `AmazonEKSEditPolicy` 和 `AmazonEKSAdminViewPolicy` 后才能同步。默认 Git 轮询从提交到状态变为 Synced 需要 342–697 秒；使用 GitHub webhook 后，耗时缩短至约 7 秒。登录仅支持 IAM Identity Center；Notifications、CMP 和 `argocd admin` 不可用，且版本由 AWS 选择。有关权限、多集群布局、版本准备工作以及与自主管理方案的比较，请参阅 [EKS Capabilities](../../eks/13-eks-capabilities.md)。

## 后续步骤

1. **[安装指南](01-installation.md)**：为生产环境设置 ArgoCD
2. **[应用指南](02-applications.md)**：了解 Application CRD
3. **[ApplicationSet 指南](04-applicationsets.md)**：多集群部署

## 资源

- [ArgoCD 官方文档](https://argo-cd.readthedocs.io/)
- [ArgoCD GitHub 仓库](https://github.com/argoproj/argo-cd)
- [Argo Rollouts 文档](https://argoproj.github.io/argo-rollouts/)
- [CNCF ArgoCD 项目页面](https://www.cncf.io/projects/argo/)

## 测验

想检验所学内容，请尝试 [ArgoCD 安装测验](../../quizzes/gitops/argocd/01-installation-quiz.md)。

### 版本化审查资料

- [Argo CD 3.5.5 已测试的 Kubernetes 版本](https://github.com/argoproj/argo-cd/blob/v3.5.5/docs/operator-manual/tested-kubernetes-versions.md)
- [发布支持策略](https://github.com/argoproj/argo-cd/blob/v3.5.5/docs/developer-guide/release-process-and-cadence.md)
- [3.5.0 发布说明](https://github.com/argoproj/argo-cd/releases/tag/v3.5.0)
- [3.5.2 发布说明](https://github.com/argoproj/argo-cd/releases/tag/v3.5.2)
- [3.5.3 发布说明](https://github.com/argoproj/argo-cd/releases/tag/v3.5.3)
- [3.5.4 发布说明](https://github.com/argoproj/argo-cd/releases/tag/v3.5.4)
- [Chart 10.10.3（首个包含 Argo CD 3.5.5 的 chart）](https://github.com/argoproj/argo-helm/releases/tag/argo-cd-10.10.3)
- [HA 组件行为](https://github.com/argoproj/argo-cd/blob/v3.5.5/docs/operator-manual/high_availability.md)
