# GitOps

> **最后更新**：October 12, 2026

## 目录
- [什么是 GitOps？](#what-is-gitops)
- [核心原则](#core-principles)
- [推送与拉取模型](#push-vs-pull-model)
- [GitOps 工具概览](#gitops-tools-overview)
- [工具选择指南](#tool-selection-guide)
- [Amazon EKS 上的 GitOps](#gitops-on-amazon-eks)
- [入门](#getting-started)

## 什么是 GitOps？

GitOps 是一种运维框架，它将 DevOps 的基础设施自动化最佳实践（例如版本控制、协作、合规性和 CI/CD）应用于基础设施管理。Weaveworks 于 2017 年创造了这个术语，此后它成为 CNCF 认可的云原生应用部署方法。

GitOps 的核心是将 Git 仓库用作声明式基础设施和应用配置的唯一事实来源。通过 Git 提交来更改期望状态，并由自动化流程确保系统的实际状态与声明状态一致。

![架构图展示开发者将更改推送到 Git，GitOps agent 监视这些更改并将其协调到 Kubernetes 集群中，同时集群将状态报告回 agent。](../.gitbook/assets/en-gitops-readme-10.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-gitops-readme-10.html)

### 历史与演进

| 里程碑 | 已核实的项目历史 |
|---|---|
| Flux | 2019 年 7 月进入 CNCF Sandbox；2021 年 3 月进入 Incubating；2022 年 11 月 30 日毕业 |
| Argo 项目 | 2020 年 3 月进入 CNCF Incubating；2022 年 12 月 6 日毕业 |
| OpenGitOps | 发布带版本号的原则；应区分已发布文档和正在维护的 main 分支 |

### CNCF OpenGitOps 定义

OpenGitOps 项目通过四项原则定义 GitOps：

1. **声明式**：由 GitOps 管理的系统必须以声明式方式表达其期望状态
2. **有版本且不可变**：期望状态以能够确保不可变性和版本控制的方式存储，并保留完整的版本历史
3. **自动拉取**：软件 agent 自动从源拉取期望状态声明
4. **持续协调**：软件 agent 持续观察系统实际状态，并尝试应用期望状态

## 核心原则

Git 历史记录期望配置。Git revert 不会还原数据库迁移、已删除的数据或外部状态。Argo CD 的 automated sync、prune 和 selfHeal 是相互独立的设置；GitOps 描述的是一个尝试进行协调的控制循环。

### 声明式配置

所有内容都以代码定义：基础设施、应用、策略和配置。这使得以下事项成为可能：

- **可重现性**：有版本控制的配置，加上可用的制品、密钥和数据，可用于重建
- **可审计性**：保留配置历史；仍需收集运行时/API 审计日志
- **一致性**：使用共享基础配置，并明确列出经过审查的环境差异

```yaml
# Example: Declarative application state
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
  labels:
    app: web-app
    version: v1.2.3
spec:
  replicas: 3
  selector:
    matchLabels:
      app: web-app
  template:
    metadata:
      labels:
        app: web-app
    spec:
      containers:
      - name: web-app
        image: myregistry/web-app:v1.2.3
        ports:
        - containerPort: 8080
```

### Git 作为唯一事实来源

Git 仓库存储整个系统的期望状态：

- **应用配置**
- **基础设施定义**
- **安全策略**
- **特定环境的设置**

### 自动协调

GitOps agent 会持续执行以下操作：

1. 监视 Git 仓库中的更改
2. 比较期望状态与实际状态
3. 应用更改，使系统符合期望状态
4. 报告状态和偏差

### 自愈系统

协调尝试取决于 sync/self-heal 策略、权限和运行状况。例如，Argo CD automated sync 和 selfHeal 需要配置；仅安装 Argo CD 并不会回退每一项手动更改或恢复丢失的数据。

## 推送与拉取模型

对比传统的推送式部署与基于拉取的 GitOps。仅使用 `kubectl apply` 的 CI 流水线本身并不符合 OpenGitOps 的自动拉取和持续协调原则：

![流程图对比传统的推送式 CI/CD（流水线直接将更改应用到集群）与 GitOps 拉取模型（agent 监视 Git 并自行应用更改）。](../.gitbook/assets/en-gitops-readme-11.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-gitops-readme-11.html)

### 推送模型

在传统的推送模型中：
- CI/CD 流水线可以直接访问集群
- 凭证存储在 CI 系统中
- 从集群外部推送更改

**缺点：**
- 需要在 CI 系统中存储集群凭证
- 更难审计是谁进行了更改
- 没有自动偏差检测

### 拉取模型（推荐）

在 GitOps 拉取模型中：
- agent 在目标集群或独立的管理集群中运行
- agent 从 Git 拉取更改
- 管理集群中的 agent 仍需要经过授权的网络/API 访问权限，才能访问远程目标

**优点：**
- 可减少 CI 中的目标集群凭证；agent 仍持有源和 API 访问权限
- Git 中有完整的审计轨迹
- 自动检测并纠正偏差
- 可在防火墙后运行

## GitOps 工具概览

### ArgoCD

[ArgoCD](argocd/README.md) 是面向 Kubernetes 的声明式 GitOps 持续交付工具。

**主要功能：**
- 用于可视化的 Web UI
- 多集群支持
- SSO 集成
- 回滚功能
- 运行状况监控
- 用于集群群组管理的 ApplicationSet

**适用场景：**需要可视化管理、多集群部署和企业级功能的团队

### FluxCD

FluxCD 是一套开放且可扩展的 Kubernetes 持续交付解决方案。

**主要功能：**
- 轻量且模块化
- 原生支持 Helm 和 Kustomize
- 镜像自动化
- 多租户
- 通知控制器

**适用场景：**倾向于 CLI 优先、轻量级解决方案和镜像自动化工作流的团队

### Jenkins X / JayeX

Jenkins X / JayeX 为 Kubernetes 上的云原生应用提供 CI/CD。

**主要功能：**
- 自动化 CI/CD 流水线
- 预览环境
- GitOps 推广
- 基于 Tekton 的流水线

**评估适用场景：**集成式 CI/CD 和预览环境工作流；JayeX/Jenkins X / JayeX 并非只是启用了 GitOps 的 Jenkins

### 对比矩阵

| 需求 | Argo CD | Flux |
|---|---|---|
| 默认 UI | 内置 Web UI 和 CLI | 核心控制器/CLI；可选生态系统 UI |
| Helm 行为 | 使用 helm template；Argo CD 管理资源生命周期 | Helm Controller 管理 Helm release 生命周期 |
| 镜像更新 | 独立的 Argo CD Image Updater | 可选的 Image Reflector/Automation 控制器 |
| 多租户 | AppProjects、RBAC、目标/源限制 | Kubernetes RBAC、ServiceAccount 模拟、跨命名空间限制 |
| OCI 源 | 通用 OCI/Helm 源；需验证层和媒体类型 | OCIRepository/Helm 源；需验证验证和层设置 |
| 容量 | 测量应用/集群数量和协调负载 | 测量已安装的控制器、源和协调负载 |

## 工具选择指南

### 适合选择 ArgoCD 的情况：

- 需要用于运维的可视化仪表板
- 需要多集群管理
- 企业 SSO/RBAC 很重要
- 团队偏好基于 UI 的工作流
- 需要使用 ApplicationSet 管理集群群组

### 适合选择 FluxCD 的情况：

- 偏好轻量、模块化的架构
- 镜像自动化是首要需求
- 偏好 CLI 优先的工作流
- 需要考虑资源限制
- 需要与 Helm controller 紧密集成

### 决策框架

该图展示的是选择时要考虑的问题，并不表示这些功能互不兼容。请结合表格和有代表性的试用，对比当前功能、授权边界和运维成本。

![决策树根据是否需要 Web UI、多集群范围、RBAC 需求、镜像自动化优先级以及轻量化优先级，引导用户选择 ArgoCD、FluxCD 或两者皆可。](../.gitbook/assets/en-gitops-readme-12.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-gitops-readme-12.html)

## Amazon EKS 上的 GitOps

### EKS 特定注意事项

在 Amazon EKS 上实施 GitOps 时：

#### IAM 集成

仅添加 ServiceAccount 注解并不能建立 IAM 访问权限。请配置 IRSA OIDC provider/trust policy/SDK 支持，或配置 EKS Pod Identity association。AWS API 权限与目标 Kubernetes API 身份验证/RBAC 是相互独立的。

使用 IAM Roles for Service Accounts (IRSA) 安全访问 AWS API：

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: gitops-controller
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/GitOpsRole
```

#### 多账户架构

![架构图展示管理账户中的 ArgoCD 从 Git 读取内容，并通过跨账户连接协调开发、预发布和生产账户中的 EKS 集群。](../.gitbook/assets/en-gitops-readme-13.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-gitops-readme-13.html)

#### AWS 服务集成

GitOps 可通过以下方式管理 AWS 资源：

- **AWS Controllers for Kubernetes (ACK)**：用于 AWS 服务的原生 K8s CRD
- **Crossplane**：多云资源配置
- **Terraform Controller**：通过 GitOps 管理 Terraform 状态

### 推荐架构

```
├── infrastructure/
│   ├── base/                    # Shared infrastructure
│   │   ├── vpc/
│   │   ├── eks/
│   │   └── iam/
│   └── environments/
│       ├── dev/
│       ├── staging/
│       └── production/
├── applications/
│   ├── base/                    # Application base configs
│   └── overlays/
│       ├── dev/
│       ├── staging/
│       └── production/
└── platform/
    ├── argocd/                  # GitOps tooling
    ├── monitoring/              # Observability stack
    └── security/                # Security policies
```

## 入门

### ArgoCD 快速入门

请使用兼容的 Kubernetes 版本、专用的空命名空间，以及用于 CRD/RBAC 的集群权限。此非 HA 安装示例固定使用 Argo CD 3.5.4；在生产环境中使用之前，请先查阅完整的[安装指南](argocd/01-installation.md)。必须更改初始管理员凭证，并在使用后删除引导 Secret。

1. **安装 ArgoCD：**
   ```bash
   kubectl create namespace argocd
   kubectl apply --server-side -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/v3.5.4/manifests/install.yaml
   ```

2. **访问 UI：**
   ```bash
   kubectl port-forward svc/argocd-server -n argocd 8080:443
   ```

3. **获取初始密码：**
   ```bash
   kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d
   ```

有关 ArgoCD 的详细设置说明，请参阅 [ArgoCD 文档](argocd/README.md)。

### FluxCD 快速入门

请准备好 `GITHUB_ORG`/`GITOPS_REPOSITORY`、文档所述的 GitHub 身份验证方式以及 Kubernetes 权限。Bootstrap 会写入 Git 并安装集群控制器。只有在使用个人账户作为所有者时才添加 `--personal`；如有需要，请明确选择可选的镜像自动化控制器。

1. **安装 Flux CLI：**
   ```bash
   curl --fail --location https://fluxcd.io/install.sh -o install-flux.sh
   # Review the script and select a supported version before running it.
   sudo bash install-flux.sh
   ```

2. **Bootstrap Flux：**
   ```bash
   flux bootstrap github \
     --owner="$GITHUB_ORG" \
     --repository="$GITOPS_REPOSITORY" \
     --path=clusters/my-cluster
   ```

有关 FluxCD 的详细设置说明，请参阅 FluxCD 文档。

## 章节导航

| 主题 | 描述 |
|-------|-------------|
| [ArgoCD](argocd/README.md) | 完整的 ArgoCD 指南，涵盖安装、应用、同步策略等内容 |
| [FluxCD](02-fluxcd.md) | FluxCD 设置、源控制器和镜像自动化 |

## 延伸阅读

- [CNCF GitOps 工作组](https://github.com/cncf/tag-app-delivery/tree/main/gitops-wg)
- [OpenGitOps 项目](https://opengitops.dev/)
- [GitOps 原则](https://www.gitops.tech/)

## 测验

请尝试以下测验，检验你所学的内容：
- [ArgoCD 测验](../quizzes/gitops/01-argocd-quiz.md)
- [FluxCD 测验](../quizzes/gitops/02-fluxcd-quiz.md)
- [GitOps 对比测验](../quizzes/gitops/03-gitops-comparison-quiz.md)

### 审阅资料

- [OpenGitOps 原则](https://github.com/open-gitops/documents/blob/v1.0.0/PRINCIPLES.md)
- [Argo 项目成熟度](https://www.cncf.io/projects/argo/)
- [Flux 项目成熟度](https://www.cncf.io/projects/flux/)
- [Argo CD OCI 源](https://argo-cd.readthedocs.io/en/stable/user-guide/oci/)
- [Argo CD automated sync](https://argo-cd.readthedocs.io/en/stable/user-guide/auto_sync/)
- [Flux 多租户](https://fluxcd.io/flux/installation/configuration/multitenancy/)
- [Flux 生态系统](https://fluxcd.io/ecosystem/)
- [JayeX 项目](https://jayex.io/v3/about/)
