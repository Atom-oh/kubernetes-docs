# 第 3 部分：在 EKS 上部署 MLflow

> **审查基线**：MLflow 3.16.0 · 社区 chart 1.11.7；已检查最新补丁 3.16.1 · 2026-10-12

## 实验环境设置

准备受支持的 EKS Kubernetes 版本、兼容的 kubectl、Helm 3、元数据数据库和制品存储。诸如 `kubectl >=1.34` 的下限并不能证明其与每个 API server 兼容。请针对实际集群检查客户端/服务器版本偏差策略。

本章基于下载的 chart、原生 Helm 渲染以及 MLflow 3.16.0 server 源代码。**它并不证明 AWS 资源预配、RDS 连接、S3 上传或 EKS 部署成功。**有关本地 SQLite/API 检查，请参见[第 1 部分](01-tracking.md)；有关 Registry 检查，请参见[第 2 部分](02-model-registry.md)。

## 为什么要在 EKS 上运行 MLflow 的 Tracking Server

您可以复用 Kubernetes 的部署、可观测性和 IAM 模式，同时需自行负责 server、数据库、制品、访问控制、备份和升级。SageMaker MLflow Apps 及其他托管 Registry 是替代方案；它们支持的版本、身份验证、功能和成本不一定相同。

与团队共享并不自动意味着必须新建独立的 RDS 和 S3 资源。可以进行小型 SQLite/PVC 练习；应根据并发性、持久性和恢复要求选择生产架构。

## 架构

| 层 | 要检查的职责和状态 |
|---|---|
| HTTP server | SDK API、UI、制品代理；身份验证、授权、host/CORS 策略、worker |
| 元数据数据库 | experiment/run/metric/model/registry 元数据；连接池、迁移、备份 |
| 制品存储 | model/data/plot 文件；bucket/prefix、IAM、加密、保留策略 |
| 身份验证存储 | 用户/权限数据库、session/signing secret、所选身份验证机制的 cache |
| 可选功能状态 | 已启用作业、tracing/evaluation 或 gateway 功能所使用的 queue、cache 和临时文件 |

PostgreSQL 加 S3 并不能让所有功能都无状态。例如，Pod 本地 basic-auth SQLite 数据库可能使各副本拥有不同的用户或权限。请分别检查 OIDC-plugin cache 和作业存储。

SQLite 是关系型数据库，并支持多个进程进行串行写入。第二个用户连接时不会立即失败。但是，独立的 Pod 本地 SQLite 文件不是共享数据库；即使是共享文件，也存在写入器、文件系统锁定和恢复方面的限制。应根据这些要求选择生产 PostgreSQL。

![受保护的访问会进入使用元数据/身份验证数据库和 S3 制品的 MLflow server。S3 IAM 权限和 PostgreSQL 登录权限彼此独立；在扩展副本前，需将共享状态外部化。](../../.gitbook/assets/en-ai-ml-mlflow-03-eks-deployment-0.png)

[交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-mlflow-03-eks-deployment-0.html)

## 安装方式和版本固定

| 路径 | 已验证内容 |
|---|---|
| 社区 chart | 已下载/渲染 `community-charts/mlflow` 1.11.7；appVersion 3.16.0，默认 image 为 `burakince/mlflow` |
| MLflow repository chart | `v3.16.0/charts` 包含 appVersion 3.15.2 的 chart 0.1.1；source tag、chart version 和 image version 不同 |
| 直接 manifests | 当基于文件的凭据交付、网络、身份验证或迁移策略需要直接控制时的一种选择 |

上游 repository 中的源代码并不能证明已发布版本完全相同的 OCI package。审查期间，官方 OCI chart 0.1.1 的 pull 返回 `not found`，因此此处不将其作为已验证的安装命令提供。

这些命令通过发现、下载和渲染来检查 chart 默认值。请使用下方检查项单独准备生产 values。

```bash
helm repo add community-charts https://community-charts.github.io/helm-charts
helm repo update community-charts
helm show chart community-charts/mlflow --version 1.11.7
helm pull community-charts/mlflow --version 1.11.7 --untar --untardir ./vendor
helm show values community-charts/mlflow --version 1.11.7 > values.reference.yaml
helm template mlflow ./vendor/mlflow --namespace mlflow -f values.reference.yaml > rendered.yaml
```

在应用前检查渲染后的 image/digest、ServiceAccount、凭据交付、CLI 参数、probe、Service 和 Ingress。该 chart 默认使用社区 image 而非上游 MLflow image；还应验证其数据库 driver、AWS SDK 和身份验证 plugin。

### 重要的 Chart 1.11.7 默认值

- 默认值包括 `replicaCount: 1`、`auth.enabled: false` 和 `ingress.enabled: false`。
- `backendStore.defaultSqlitePath: ":memory:"` 配置内存中的元数据。**这不同于上游 CLI 的新 SQLite-file 默认值。**默认 chart 安装不是持久的生产服务。
- 外部 PostgreSQL 使用 `backendStore.postgres.*`；凭据引用使用 `backendStore.existingDatabaseSecret.*`。
- 将 `artifactRoot.s3.*` 与 `artifactRoot.proxiedArtifactStorage: true` 一起检查。原生渲染生成了 `--artifacts-destination=s3://...` 和 `--serve-artifacts`。
- Basic-auth 数据库设置位于独立的 `auth.postgres.*` 下。更改 tracking 数据库不会自动共享身份验证状态。
- `backendStore.databaseMigration: true` 会添加一个 Pod init-container 路径。允许多个副本并发迁移前，应规划备份、一次协调的迁移阶段以及兼容性检查。

仅填写名称而不提供实际值和 Secret 并不能完成生产设置。此 chart 中的一些数据库/身份验证引用通过**container environment variables**交付。SecretKeyRef 可避免在 Git 中存储明文值，但不能消除进程环境暴露。当策略禁止在环境中出现 secret 值时，请准备由 Secrets Manager/SSM 或等效存储提供的凭据文件，以及使用这些文件的部署。不要将静态 AWS key 放入 Helm values 或 image 中。

## IAM 和数据库身份验证

将 S3 权限限制在目标 bucket/prefix。根据实际操作，检查 `GetObject`、`PutObject`、listing、multipart 和 KMS 权限。代理模式使用 server AWS 权限；直接制品模式使用 client 权限。仅更改 server flag 不会重写现有 experiment URI。

EKS Pod Identity 需要 Agent、association 和受支持的 SDK，并以 Linux EC2 worker 为目标。它并不普遍适用于 Fargate 或 Windows Pod。在其支持的配置中，IRSA 仍是另一种选择。仅指定 ServiceAccount 名称或一个 annotation 并不能完成 IAM trust、association 和 SDK 设置。

用于 S3 的 IAM role 不会自动授权 PostgreSQL 登录。请验证数据库网络访问、TLS 验证、用户/凭据，或单独配置的 IAM 数据库身份验证。检查 IMDS 和 SDK 配置，以防止意外回退到 node-role 凭据。

## Server 访问和健康检查

ClusterIP、私有 ALB 和 TLS 提供网络或传输控制；它们不能替代按用户配置的 MLflow 权限。应使用组织受保护的 ingress 架构，而非假设直接公开 ALB。

为实际调用方配置 MLflow 3.16.0 `allowed_hosts` 和 CORS origins。在此社区 chart 中，请通过 `extraArgs.allowedHosts` 和 `extraArgs.corsAllowedOrigins` 设置相应的 CLI 参数。Host/CORS 限制不能替代登录或授权。

在 3.16.0 中，basic-auth 默认改为 fail-closed 授权。3.16.1 移除了随附的默认 administrator password，因此不要依赖默认凭据。启动前，显式配置经批准的 administrator password 和 auth 设置。本章的 chart 与 MLflow 3.16.0 组合尚未在 3.16.1 上重新验证。

已验证的 health endpoint 是 **`/health`**，实现为返回 `"OK", 200`。它检查 HTTP 进程响应性，而不是持续的 RDS/S3 连接或用户授权。此版本豁免 health endpoint 的 host 验证。使用 `static-prefix`、ingress 重写或 plugin 时，请检查实际 service path。

## 运维说明

扩展副本前，共享或外部化元数据/身份验证数据库、session secret 和已启用的 queue/cache；测试 failover。然后应用 topology spread、PDB、readiness 和资源限制。仅有两个 Pod 并不能保证高可用性。

一次 API 调用并不总是一次 SQL 写入。应一并测量 batch logging、transaction、trace payload、metric history 和每个 worker 的 connection pool。跨副本/worker 的 pool 会累加；一个 pool 的配置无法描述数据库连接总需求。

Aurora Serverless v2 在已配置的容量范围以及连接、I/O 和 transaction 限制内运行。它不能吸收无限突发流量，也不能保证更低成本。应针对测得的负载和恢复要求，将其与预置 RDS/Aurora 进行比较。

同时备份元数据/身份验证数据库和制品，并测试恢复。应根据保留策略审查诸如 `mlflow gc` 的永久删除工具，而不要将其作为例行清理添加。model alias 变更和 serving 重新部署也是独立操作。

## 主要来源

- [MLflow 3.16.1 补丁发布](https://github.com/mlflow/mlflow/releases/tag/v3.16.1)
- [MLflow 3.16.0 审查基线](https://github.com/mlflow/mlflow/releases/tag/v3.16.0)
- [Tracking server 架构](https://mlflow.org/docs/3.16.0/self-hosting/architecture/tracking-server/)
- [社区 chart](https://github.com/community-charts/helm-charts/tree/main/charts/mlflow)
- [MLflow repository chart](https://github.com/mlflow/mlflow/tree/v3.16.0/charts)
- [Server health 实现](https://github.com/mlflow/mlflow/blob/v3.16.0/mlflow/server/__init__.py)
- [EKS Pod Identity 限制](https://docs.aws.amazon.com/eks/latest/userguide/pod-identities.html)
- [SQLite 使用场景和并发](https://www.sqlite.org/whentouse.html)
- [Aurora Serverless v2 容量配置](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-serverless-v2.setting-capacity.html)

[主页](README.md) · [测验](../../quizzes/ai-ml/mlflow/03-eks-deployment-quiz.md)
