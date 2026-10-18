# 第 3 部分：在 EKS 上部署 MLflow

> **审查基线**：MLflow 3.16.0 · community chart 1.11.7；已检查最新版本 3.17.1 · 2026-10-16

## 实验环境设置

准备受支持的 EKS Kubernetes 版本、兼容的 kubectl、Helm 3、元数据数据库和制品存储。`kubectl >=1.34` 这样的最低版本要求并不能证明它与每个 API 服务器都兼容。请根据实际集群检查客户端/服务器版本偏差策略。

本章基于下载的 chart、原生 Helm 渲染以及 MLflow 3.16.0 服务器源代码。**本章并未证明 AWS 资源配置、RDS 连接、S3 上传或 EKS 部署成功**。本地 SQLite/API 检查请参阅[第 1 部分](01-tracking.md)，Registry 检查请参阅[第 2 部分](02-model-registry.md)。

## 为什么要在 EKS 上运行 MLflow 的 Tracking Server

你可以复用 Kubernetes 部署、可观测性和 IAM 模式，同时承担管理服务器、数据库、制品、访问控制、备份和升级的责任。SageMaker MLflow Apps 和其他托管 Registry 也是替代方案；它们支持的版本、身份验证、功能和成本未必相同。

与团队共享并不意味着必须新建并单独配置 RDS 和 S3 资源。可以进行小规模的 SQLite/PVC 练习；生产架构应根据并发、持久性和恢复要求来选择。

## 架构

| 层 | 需要检查的职责和状态 |
|---|---|
| HTTP 服务器 | SDK API、UI、制品代理；身份验证、授权、主机/CORS 策略、worker |
| 元数据库 | experiment/run/metric/model/registry 元数据；连接池、迁移、备份 |
| 制品存储 | 模型/数据/绘图文件；存储桶/前缀、IAM、加密、保留策略 |
| 身份验证存储 | 用户/权限数据库、会话/签名密钥、所选身份验证机制的缓存 |
| 可选功能状态 | 启用的作业、追踪/评估或网关功能所使用的队列、缓存和临时文件 |

PostgreSQL 加 S3 并不会让所有功能都变成无状态。例如，Pod 本地的 basic-auth SQLite 数据库可能导致各个副本中的用户或权限不一致。请单独检查 OIDC 插件缓存和作业存储。

SQLite 是一种关系型数据库，支持多个进程，并通过串行化写入来处理并发。第二个用户连接时，它不会立即失败。不过，各 Pod 上彼此独立的 SQLite 文件并不是共享数据库；即使共享文件，也存在写入、文件系统锁定和恢复方面的限制。请根据这些要求来决定生产环境是否选择 PostgreSQL。

![受保护的访问入口连接到使用元数据/身份验证数据库和 S3 制品存储的 MLflow 服务器。S3 IAM 权限与 PostgreSQL 登录权限彼此独立；在扩展副本前，先将共享状态外置。](../../.gitbook/assets/en-ai-ml-mlflow-03-eks-deployment-0.png)

[交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-mlflow-03-eks-deployment-0.html)

## 安装方式和版本固定

| 方式 | 已验证内容 |
|---|---|
| Community chart | 已下载/渲染 `community-charts/mlflow` 1.11.7；appVersion 3.16.0，默认镜像为 `burakince/mlflow` |
| MLflow 仓库 chart | `v3.16.0/charts` 包含 chart 0.1.1，appVersion 为 3.15.2；源代码标签、chart 版本和镜像版本各不相同 |
| 直接使用清单 | 当需要直接控制基于文件的凭证交付、网络、身份验证或迁移策略时，可选择此方式 |

上游仓库中的源代码并不能证明发布了版本号完全相同的 OCI 包。审查期间，官方 OCI chart 0.1.1 的拉取返回了 `not found`，因此这里不将其列为已验证的安装命令。

以下命令通过查询、下载和渲染来检查 chart 默认值。请根据下面的检查项单独准备生产环境 values。

```bash
helm repo add community-charts https://community-charts.github.io/helm-charts
helm repo update community-charts
helm show chart community-charts/mlflow --version 1.11.7
helm pull community-charts/mlflow --version 1.11.7 --untar --untardir ./vendor
helm show values community-charts/mlflow --version 1.11.7 > values.reference.yaml
helm template mlflow ./vendor/mlflow --namespace mlflow -f values.reference.yaml > rendered.yaml
```

应用前，请检查渲染后的镜像/摘要、ServiceAccount、凭证交付方式、CLI 参数、探针、Service 和 Ingress。该 chart 默认使用社区镜像，而不是上游 MLflow 镜像；还要验证其数据库驱动程序、AWS SDK 和身份验证插件。

### Chart 1.11.7 的重要默认值

- 默认值包括 `replicaCount: 1`、`auth.enabled: false` 和 `ingress.enabled: false`。
- `backendStore.defaultSqlitePath: ":memory:"` 配置的是内存中的元数据。**这与上游 CLI 新的 SQLite 文件默认值不同**。默认安装的 chart 并不是持久化的生产服务。
- 外部 PostgreSQL 使用 `backendStore.postgres.*`；凭证引用使用 `backendStore.existingDatabaseSecret.*`。
- 将 `artifactRoot.s3.*` 与 `artifactRoot.proxiedArtifactStorage: true` 一并检查。原生渲染生成了 `--artifacts-destination=s3://...` 和 `--serve-artifacts`。
- Basic-auth 数据库设置位于单独的 `auth.postgres.*` 下。更改 Tracking 数据库不会自动共享身份验证状态。
- `backendStore.databaseMigration: true` 会添加 Pod init-container 流程。在允许多个副本同时迁移之前，请规划备份、一次协调完成的迁移阶段以及兼容性检查。

仅填写名称而不提供真实值和 Secrets，并不能完成生产环境配置。此 chart 中的一些数据库/身份验证引用通过**容器环境变量**传递。使用 SecretKeyRef 可以避免将明文值存入 Git，但不能消除进程环境中的暴露。如果策略禁止在环境变量中存放 Secret 值，请准备由 Secrets Manager/SSM 或同等存储提供的凭证文件，以及能够使用这些文件的部署方式。不要将静态 AWS 密钥放入 Helm values 或镜像中。

## IAM 和数据库身份验证

将 S3 权限限制在目标存储桶/前缀范围内。根据实际操作检查 `GetObject`、`PutObject`、列举、多部分上传和 KMS 权限。代理模式使用服务器的 AWS 权限；直接制品模式使用客户端权限。仅更改服务器标志不会重写现有 experiment URI。

EKS Pod Identity 需要 Agent、association 和受支持的 SDK，并适用于 Linux EC2 worker。它并非普遍适用于 Fargate 或 Windows Pod。IRSA 也是受支持配置中的一种选择。指定 ServiceAccount 名称或单个 annotation，并不能完成 IAM 信任、association 和 SDK 配置。

用于 S3 的 IAM role 不会自动授权 PostgreSQL 登录。请验证数据库网络访问、TLS 验证、用户/凭证，或单独配置的 IAM 数据库身份验证。检查 IMDS 和 SDK 配置，防止意外回退到节点 role 凭证。

## 服务器访问和健康检查

ClusterIP、私有 ALB 和 TLS 提供网络或传输层控制；它们不能取代 MLflow 的逐用户权限。请使用组织的受保护入口架构，不要想当然地直接公开 ALB。

为实际调用方配置 MLflow 3.16.0 的 `allowed_hosts` 和 CORS 来源。在此 community chart 中，通过 `extraArgs.allowedHosts` 和 `extraArgs.corsAllowedOrigins` 设置相应的 CLI 参数。主机/CORS 限制不能取代登录或授权。

在 3.16.0 中，basic-auth 的授权默认改为故障时拒绝。3.16.1 移除了随附的默认管理员密码，因此不要依赖默认凭证。启动前请明确配置获准使用的管理员密码和身份验证设置。本章中的 chart 与 MLflow 3.16.0 组合尚未在 3.16.1 或 3.17.x 上重新验证；升级到 3.17.0 或更高版本需要升级 SQL 后端架构。

已验证的健康端点是 **`/health`**，其实现返回 `"OK", 200`。它检查 HTTP 进程是否响应，不会持续检查 RDS/S3 连接或用户授权。此版本的健康端点不进行主机验证。使用 `static-prefix`、Ingress 重写或插件时，请检查实际服务路径。

## 运维说明

扩展副本前，请共享或外置元数据/身份验证数据库、会话密钥以及已启用的队列/缓存，并测试故障转移。之后再配置拓扑分布、PDB、就绪状态和资源限制。仅有两个 Pod 并不能保证高可用性。

一次 API 调用并不总是对应一次 SQL 写入。请综合测量批量日志记录、事务、追踪负载、指标历史记录以及每个 worker 的连接池。多个副本/worker 的连接池会累加；单个连接池的配置不能代表数据库的总连接需求。

Aurora Serverless v2 在配置的容量范围以及连接、I/O 和事务限制内运行。它无法吸收无限突发流量，也不保证成本更低。请根据实测负载和恢复要求，将其与预置的 RDS/Aurora 进行比较。

同时备份元数据/身份验证数据库和制品，并测试恢复。请依据保留策略审查 `mlflow gc` 等永久删除工具，而不要将它们作为例行清理手段。模型别名变更和服务重新部署也是彼此独立的操作。

## 主要来源

- [MLflow 3.16.1 补丁版本](https://github.com/mlflow/mlflow/releases/tag/v3.16.1)
- [MLflow 3.16.0 审查基线](https://github.com/mlflow/mlflow/releases/tag/v3.16.0)
- [Tracking Server 架构](https://mlflow.org/docs/3.16.0/self-hosting/architecture/tracking-server/)
- [Community chart](https://github.com/community-charts/helm-charts/tree/main/charts/mlflow)
- [MLflow 仓库 chart](https://github.com/mlflow/mlflow/tree/v3.16.0/charts)
- [服务器健康检查实现](https://github.com/mlflow/mlflow/blob/v3.16.0/mlflow/server/__init__.py)
- [EKS Pod Identity 限制](https://docs.aws.amazon.com/eks/latest/userguide/pod-identities.html)
- [SQLite 用例和并发](https://www.sqlite.org/whentouse.html)
- [Aurora Serverless v2 容量配置](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-serverless-v2.setting-capacity.html)

[主页](README.md) · [测验](../../quizzes/ai-ml/mlflow/03-eks-deployment-quiz.md)
