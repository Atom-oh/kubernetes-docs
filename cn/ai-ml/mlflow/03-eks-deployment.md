# 第 3 部分：在 EKS 上部署 MLflow

> **审查基线**：MLflow 3.16.0 · 社区 chart 1.11.7 · 2026-09-12

## 实验环境设置

准备受支持的 EKS Kubernetes 版本、兼容的 kubectl、Helm 3、元数据数据库和制品存储。诸如 `kubectl >=1.34` 的下限并不能证明其与每个 API server 兼容。请根据实际集群检查客户端/服务器版本偏差策略。

本章基于已下载的 chart、原生 Helm 渲染以及 MLflow 3.16.0 server 源代码。**它并不证明 AWS 资源预置、RDS 连接、S3 上传或 EKS 部署成功。**本地 SQLite/API 检查请参阅[第 1 部分](01-tracking.md)，Registry 检查请参阅[第 2 部分](02-model-registry.md)。

## 为什么要在 EKS 上运行 MLflow Tracking Server

您可以复用 Kubernetes 部署、可观测性和 IAM 模式，同时负责 server、数据库、制品、访问控制、备份和升级。SageMaker MLflow Apps 及其他托管 Registry 是替代方案；它们所支持的版本、身份验证、功能和成本不一定相同。

与团队共享并不自动意味着必须预置新的独立 RDS 和 S3 资源。可以进行小型 SQLite/PVC 练习；应根据并发性、持久性和恢复需求选择生产架构。

## 架构

| 层 | 职责和需要检查的状态 |
|---|---|
| HTTP server | SDK API、UI、制品代理；身份验证、授权、host/CORS 策略、worker |
| 元数据数据库 | experiment/run/metric/model/registry 元数据；连接池、迁移、备份 |
| 制品存储 | model/data/plot 文件；bucket/prefix、IAM、加密、保留策略 |
| 身份验证存储 | 用户/权限数据库、session/signing secret、所选身份验证机制的 cache |
| 可选功能状态 | 已启用 job、tracing/evaluation 或 gateway 功能使用的队列、cache 和临时文件 |

PostgreSQL 加 S3 并不会使每项功能都成为无状态。例如，Pod 本地的 basic-auth SQLite 数据库可能使各 replica 拥有不同的用户或权限。请分别检查 OIDC-plugin cache 和 job 存储。

SQLite 是关系型数据库，支持通过串行写入使用多个进程。第二个用户连接时不会立即失败。但是，彼此独立的 Pod 本地 SQLite 文件并非共享数据库；即使是共享文件，也存在 writer、文件系统锁定和恢复方面的限制。应将生产 PostgreSQL 的选择与这些需求关联起来。

![受保护的访问会将请求引向使用元数据/身份验证数据库和 S3 制品的 MLflow server。S3 IAM 权限和 PostgreSQL 登录权限彼此独立；在扩展 replica 前，先将共享状态外部化。](../../.gitbook/assets/en-ai-ml-mlflow-03-eks-deployment-0.png)

[交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-mlflow-03-eks-deployment-0.html)

## 安装方式和版本固定

| 路径 | 已验证内容 |
|---|---|
| 社区 chart | 已下载/渲染 `community-charts/mlflow` 1.11.7；appVersion 3.16.0，默认 image 为 `burakince/mlflow` |
| MLflow repository chart | `v3.16.0/charts` 包含 appVersion 3.15.2 的 chart 0.1.1；source tag、chart 版本和 image 版本不同 |
| 直接使用 manifest | 当基于文件的凭证交付、网络、身份验证或迁移策略需要直接控制时可采用的方式 |

上游 repository 中的源代码并不能证明已发布版本完全相同的 OCI package。审查期间拉取官方 OCI chart 0.1.1 返回 `not found`，因此此处未将其列为已验证的安装命令。

这些命令通过发现、下载和渲染检查 chart 默认值。请使用下方检查项单独准备生产 values。

```bash
helm repo add community-charts https://community-charts.github.io/helm-charts
helm repo update community-charts
helm show chart community-charts/mlflow --version 1.11.7
helm pull community-charts/mlflow --version 1.11.7 --untar --untardir ./vendor
helm show values community-charts/mlflow --version 1.11.7 > values.reference.yaml
helm template mlflow ./vendor/mlflow --namespace mlflow -f values.reference.yaml > rendered.yaml
```

在应用前检查渲染后的 image/digest、ServiceAccount、凭证交付、CLI 参数、probe、Service 和 Ingress。该 chart 默认使用社区 image，而非上游 MLflow image；还应验证其数据库 driver、AWS SDK 和身份验证 plugin。

### 重要的 Chart 1.11.7 默认值

- 默认值包括 `replicaCount: 1`、`auth.enabled: false` 和 `ingress.enabled: false`。
- `backendStore.defaultSqlitePath: ":memory:"` 配置内存中的元数据。**这不同于上游 CLI 新增的 SQLite 文件默认值。**默认 chart 安装并非持久化的生产服务。
- 外部 PostgreSQL 使用 `backendStore.postgres.*`；凭证引用使用 `backendStore.existingDatabaseSecret.*`。
- 请结合 `artifactRoot.proxiedArtifactStorage: true` 检查 `artifactRoot.s3.*`。原生渲染生成了 `--artifacts-destination=s3://...` 和 `--serve-artifacts`。
- basic-auth 数据库设置在 `auth.postgres.*` 下单独配置。更改 tracking 数据库不会自动共享身份验证状态。
- `backendStore.databaseMigration: true` 会添加 Pod init-container 路径。允许多个 replica 并发迁移前，请规划备份、单次协调的迁移阶段和兼容性检查。

仅填入名称而没有实际值和 Secret 并不能完成生产设置。此 chart 中的某些数据库/身份验证引用通过**容器环境变量**交付。SecretKeyRef 可避免在 Git 中存放明文值，但不会消除进程环境暴露。在策略禁止在环境变量中放置 secret 值的场景下，请准备由 Secrets Manager/SSM 或等效存储提供的凭证文件，以及使用这些文件的部署。不要将静态 AWS key 放入 Helm values 或 image 中。

## IAM 和数据库身份验证

将 S3 权限限定到预期的 bucket/prefix。根据实际操作，检查 `GetObject`、`PutObject`、列举、multipart 和 KMS 权限。代理模式使用 server 的 AWS 权限；直接制品模式使用 client 权限。仅更改 server flag 不会重写现有 experiment URI。

EKS Pod Identity 需要 Agent、association 和受支持的 SDK，并面向 Linux EC2 worker。它并非普遍适用于 Fargate 或 Windows Pod。IRSA 仍是其受支持配置中的另一种选择。指定 ServiceAccount 名称或一个 annotation 并不能完成 IAM trust、association 和 SDK 设置。

用于 S3 的 IAM role 不会自动授权 PostgreSQL 登录。请验证数据库网络访问、TLS 验证、用户/凭证，或单独配置的 IAM 数据库身份验证。检查 IMDS 和 SDK 配置，以防止意外回退使用 node-role 凭证。

## Server 访问和健康检查

ClusterIP、私有 ALB 和 TLS 提供网络或传输控制；它们不能取代按用户划分的 MLflow 权限。请使用组织受保护的 ingress 架构，而不是假定可直接公开 ALB。

为实际调用方配置 MLflow 3.16.0 的 `allowed_hosts` 和 CORS origin。在此社区 chart 中，相应的 CLI 参数可通过 `extraArgs.allowedHosts` 和 `extraArgs.corsAllowedOrigins` 设置。host/CORS 限制不能取代登录或授权。basic-auth 在 3.16.0 中已更改为默认拒绝式授权，因此请验证现有 auth plugin 和 endpoint 兼容性。

经验证的 health endpoint 是 **`/health`**，其实现为返回 `"OK", 200`。它检查 HTTP 进程响应性，而非持续的 RDS/S3 连通性或用户授权。此版本将 health endpoint 排除在 host 验证之外。使用 `static-prefix`、ingress rewrite 或 plugin 时，请检查实际 service path。

## 运维说明

在扩展 replica 前，先共享或外部化元数据/身份验证数据库、session secret 以及已启用的队列/cache；测试 failover。然后应用 topology spread、PDB、readiness 和资源限制。仅有两个 Pod 并不能保证高可用性。

一个 API 调用不一定只产生一次 SQL 写入。请结合 batch logging、transaction、trace payload、metric history 和每个 worker 的连接池进行测量。跨 replica/worker 的连接池会累加；单个连接池的配置并不能描述数据库连接总需求。

Aurora Serverless v2 在已配置的容量范围以及连接、I/O 和 transaction 限制内运行。它无法吸收无限突发负载，也不保证成本更低。请根据测得的负载和恢复需求，将其与预置的 RDS/Aurora 进行比较。

同时备份元数据/身份验证数据库和制品，并测试恢复。请根据保留策略审查诸如 `mlflow gc` 的永久删除工具，而不是将其添加为例行清理。model alias 变更和 serving 重新部署也是独立操作。

## 主要来源

- [MLflow 3.16.0 发布版本](https://github.com/mlflow/mlflow/releases/tag/v3.16.0)
- [Tracking server 架构](https://mlflow.org/docs/3.16.0/self-hosting/architecture/tracking-server/)
- [社区 chart](https://github.com/community-charts/helm-charts/tree/main/charts/mlflow)
- [MLflow repository chart](https://github.com/mlflow/mlflow/tree/v3.16.0/charts)
- [Server health 实现](https://github.com/mlflow/mlflow/blob/v3.16.0/mlflow/server/__init__.py)
- [EKS Pod Identity 限制](https://docs.aws.amazon.com/eks/latest/userguide/pod-identities.html)
- [SQLite 使用场景和并发性](https://www.sqlite.org/whentouse.html)
- [Aurora Serverless v2 容量配置](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-serverless-v2.setting-capacity.html)

[主页](README.md) · [测验](../../quizzes/ai-ml/mlflow/03-eks-deployment-quiz.md)
