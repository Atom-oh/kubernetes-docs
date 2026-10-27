# Amazon EKS Capabilities：托管式 Argo CD、kro 和 ACK

> **支持的版本**：EKS 1.36–1.37、Argo CD `3.4.6-eks-2` 和 `3.4.7-eks-1`、kro `0.9.4-eks-1`、ACK `46.186.1-eks-1`、AWS CLI 2.38.3
> **最后更新**：2026 年 10 月 23 日

EKS Capabilities 在集群外部以 AWS 运营的控制器形式运行 Argo CD、kro（Kube Resource Orchestrator）和 ACK（AWS Controllers for Kubernetes）。该功能于 2025 年 11 月 30 日正式推出。控制器日志投递（Vended Logs）于 2026 年 6 月推出，Argo CD 的自定义 `argocd-cm` 配置则于 2026 年 8 月推出。

本章中的数据于 2026 年 10 月在 ap-northeast-2 的测试集群上测得。主集群使用私有子网、身份验证模式 `API` 和两个 m7g.large 节点（用于升级和多集群测试的 hub 和 spoke 集群各有一个节点）。我们还在同一集群上安装自管式（OSS）控制器，对相同场景进行了测试。每个场景只运行了 1–5 次，因此请将这些数据视为范围，并在自己的环境中重新核验后再做运维决策。仅根据文档核实、未实际测量的内容会标注为“根据文档”。测量说明和原始结果见 [EKS Capabilities 博客系列](https://blog.atomai.click/eks-capabilities-argocd/)（韩语）。

## 目录

1. [通用模型](#common)
2. [创建和日常运维](#create)
3. [Argo CD Capability](#argocd)
4. [kro Capability](#kro)
5. [ACK Capability](#ack)
6. [同时使用这三者](#together)
7. [集群升级和 Capability 版本](#upgrade)
8. [多集群和蓝绿替换](#multicluster)
9. [与自管式方案的比较及选择时机](#compare)
10. [定价](#pricing)
11. [核验范围和参考资料](#refs)

---

<span id="common"></span>

## 1. 通用模型

| 项目 | 行为 |
|---|---|
| 控制器位置 | AWS 自有基础设施。工作节点上没有 Pod（三者的测量结果均为零） |
| 集群访问 | Capability 角色（受信任主体 `capabilities.eks.amazonaws.com`）通过 EKS access entry 调用 API server。即使 API endpoint 仅提供私有访问也能正常工作 |
| 数量 | 每个集群中每种 Capability 类型一个 |
| 版本 | 由 AWS 选择并推出。创建/更新 API 没有版本参数，因此无法固定或选择版本 |
| 删除 | 仅支持 `--delete-propagation-policy RETAIN`。CRD、CR、已部署资源和 access entry 均会保留 |
| 日志 | 无法通过 `kubectl logs` 获取。日志通过 CloudWatch Vended Logs 投递到 CloudWatch Logs、S3 或 Amazon Data Firehose（参见 [EKS 监控和日志记录](./06-eks-monitoring-logging.md)） |
| 定价 | 按小时收取 Capability 费用，并按托管对象收费（Argo CD 按 Application、kro 按实例、ACK 按资源） |

这三者的共同特点是默认权限范围较窄。仅使用自动创建的 access entry 策略时，Argo CD 无法部署资源，kro 无法启动 RGD 控制器，ACK 也无法在没有服务级 IAM 权限的情况下创建 AWS 资源。相比之下，Argo CD 和 kro 的 OSS Helm Chart 默认会向控制器授予 `apiGroups: ["*"], resources: ["*"], verbs: ["*"]`。

<span id="create"></span>

## 2. 创建和日常运维

### Capability 角色和创建命令

在 Capability 角色中信任 `capabilities.eks.amazonaws.com`，并允许 `sts:AssumeRole` 和 `sts:TagSession`。kro 从不调用 AWS API，因此不需要权限策略。使用 Argo CD 访问公开 Git 仓库时，也无需配置权限策略。

```bash
aws eks create-capability --cluster-name "$CLUSTER_NAME" \
  --capability-name kro --type KRO \
  --role-arn "arn:aws:iam::${ACCOUNT_ID}:role/${CLUSTER_NAME}-kro" \
  --delete-propagation-policy RETAIN

aws eks describe-capability --cluster-name "$CLUSTER_NAME" --capability-name kro \
  --query 'capability.{status:status,version:version}'
```

| Capability | `CREATING` → `ACTIVE` | 删除 | 自动创建的 access entry 策略 | 已安装的 CRD |
|---|---|---|---|---|
| Argo CD | 349 s（在另一个集群上创建带有 `endpointPrefix` 的新 Capability 时为 385 s；使用相同前缀重新创建时为 338 s） | 100.5 s | `AmazonEKSArgoCDClusterPolicy`（集群）、`AmazonEKSArgoCDPolicy`（`argocd` 命名空间） | `applications`、`applicationsets`、`appprojects` |
| kro | 70.1–70.4 s | 46.9 s | `AmazonEKSKROPolicy` | `resourcegraphdefinitions.kro.run`、`graphrevisions.internal.kro.run` |
| ACK | 385.7 s（CRD 已存在时为 77 s） | 67.3 s | `AmazonEKSACKPolicy` | 267 个（66 个服务 API 组，以及 `services.k8s.aws` 中的 `IAMRoleSelector`） |

### 运维说明

- **保持 AWS CLI 为最新版本。** CLI 2.35.11 在 `argoCd` 下只识别 `namespace`、`awsIdc`、`rbacRoleMappings` 和 `networkAccess`（没有 `endpointPrefix`），并且会以 `Unknown parameter in configuration: "ack", must be one of: argoCd` 拒绝 ACK 设置；2.38.3 则能接受两者。在断定某项功能不受支持之前，请先检查 CLI 版本。
- **每次只应用一项 Capability 更改。** 每添加一个日志投递源，Capability 都会进入 `UPDATING` 状态约 6.6–7 秒，期间进行下一项更改会失败，并报错 `ConflictException: ... currently in UPDATING state`。请等待其恢复为 `ACTIVE` 后再进行下一项更改。
- **从一开始就启用日志投递。** 控制器在集群外部运行，因此日志是之后了解其内部行为的唯一途径（CloudTrail 仍会显示 AWS API 调用时间）。日志采用结构化 JSON；Argo CD 会记录每次 reconcile 各阶段的耗时，如 `compare_app_state_ms`、`patch_ms` 等。
- **RETAIN 会保留“除控制器以外的一切”。** 删除 Capability 期间，CR 的更改不会被 reconcile（我们通过更改 kro 实例副本数进行了验证）。安装使用相同 CRD 的 OSS 控制器后，它会处理尚未应用的更改。

<span id="argocd"></span>

## 3. Argo CD Capability

### 注册本地集群并授予部署权限

托管式 Argo CD 不会自动将自己的集群添加为目标集群。请使用 EKS ARN 而不是 API URL 创建集群 Secret。

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: in-cluster
  namespace: argocd
  labels:
    argocd.argoproj.io/secret-type: cluster
stringData:
  name: in-cluster
  server: arn:aws:eks:ap-northeast-2:111122223333:cluster/example-cluster
  project: default
```

仅有自动创建的 access entry 并不足以允许同步，因为 Argo CD 会列出集群中的每种资源类型来构建缓存，而不只是列出它要部署的资源。

| Capability 角色的集群权限 | 结果 |
|---|---|
| 仅有自动创建的 access entry | `ComparisonError: ... podtemplates is forbidden ... at the cluster scope` |
| + `AmazonEKSEditPolicy` | 141 s 后仍然失败；对 `securitygrouppolicies.vpcresources.k8s.aws` 的 list 操作被拒绝 |
| + `AmazonEKSAdminViewPolicy` | 11.6 s 后同步成功且状态为 Healthy |
| 部署 kro/ACK API 的 CR（一个 NginxApp 实例、一个 ACK Queue） | `nginxapps.platform.example.com is forbidden`。在 access entry 中添加 Kubernetes 组并为该 API 组绑定 ClusterRole 后，16 s 内解决 |

AWS 文档建议使用 `AmazonEKSClusterAdminPolicy`（等同于 `system:masters`）开始使用，并介绍了一种生产环境最小权限配置：集群范围的读取权限加上命名空间范围的 `AmazonEKSEditPolicy`。在测试中，集群范围的 Edit 加上 AdminView，并为每个平台 CRD 单独配置 ClusterRole，能够正常工作；这比文档所述的生产环境配置授予了更广泛的权限。若要进一步收窄权限，可以使用托管式 Capability 支持的 `resource.respectRBAC`，将监听范围限制为有权限的资源（未测试）。

### Git 轮询和 webhook

| 方法 | 提交 → 同步完成（运行 3 次） |
|---|---|
| 托管式，默认轮询（根据文档为每 6 分钟） | 341.8 s、619.3 s、697.1 s |
| 托管式，GitHub webhook | 7.0–7.3 s |
| 自管式 3.4.6，默认轮询（120 s + 60 s 抖动） | 115.7–171.4 s |

托管式轮询间隔（`timeout.reconciliation`）不是可配置的键，抖动值也未公开。如果部署延迟不能出现数分钟的波动，实际上就必须使用 webhook。在 Capability 创建的 `argocd-webhook-creds-secret` 中，为 `webhook.github.secret` 设置一个随机字符串，并在 Git 仓库中注册 `<server URL>/api/webhook`，使用相同的密钥。Server URL 是 AWS 托管的公开地址，因此无需另外公开 webhook endpoint。通过 VPC endpoint 限制公网访问很可能也会阻止 GitHub webhook（未测试）。

漂移自愈表现相当：托管式为 2.08–2.32 s，自管式为 1.05–3.06 s。但是，如果同一个应用在没有新提交的情况下反复自愈，就会触发上游退避机制（2 s，每次乘以 3，最多 300 s），恢复时间会延长到接近 5 分钟（测得为 251–254 s）。自管式可通过 `--self-heal-backoff-*` 标志进行调整。托管式仅公开三个 `argocd-cmd-params-cm` 键（`hydrator.enabled`、`application.namespaces`、`applicationsetcontroller.namespaces`），AWS 文档建议向 AWS Support 申请调整自愈时间。遇到紧急情况时，请手动触发同步。

### 设置、健康检查和 CLI

在 Capability 命名空间中创建带有标签 `app.kubernetes.io/part-of: argocd` 的 `argocd-cm` ConfigMap。不受支持的键会被静默忽略。

| 项目 | 结果 |
|---|---|
| `ui.bannercontent` | 显示在 UI 中 |
| kro 实例的 Lua 健康检查 | 已应用；脚本编辑约 12 s 后生效 |
| Lua `string.upper()`、`os.time()` | `attempt to index a non-table object(nil)`，健康状态为 `Unknown`。与上游默认行为相同（`useOpenLibs` 关闭），但托管式无法将其开启 |
| `argocd login --username admin` 或 `--sso` | 两者均失败 |
| UI 中的令牌 + `ARGOCD_SERVER`、`ARGOCD_AUTH_TOKEN`、`ARGOCD_OPTS=--grpc-web` | `app list/get/sync`、`cluster list`、`proj list` 均可用 |
| 睡眠 150 s 的 PreSync hook | 尽管文档规定同步超时为 120 s，仍在 161 s 后显示 `Succeeded`；未知限制适用于哪个阶段 |

Argo CD 3.x 默认不会在 Application 状态中存储资源健康状况，因此通过 `kubectl get application -o json` 获取到空的 `.status.resources[].health` 属于正常现象。请使用 `argocd app get` 或 UI 检查健康状态。

根据文档，Config Management Plugins（CMP）、Notifications 控制器、自定义 SSO、UI 扩展和 `argocd admin` 等均不受支持。如果你使用 Notifications 发送部署通知，或通过 CMP 生成清单，就无法直接迁移到托管式 Capability。

### 登录：仅支持 IAM Identity Center

身份验证仅支持 IAM Identity Center，不提供本地用户。Capability 配置中的 `rbacRoleMappings` 可将 Identity Center 用户（`SSO_USER`）或组（`SSO_GROUP`）映射到 ADMIN、EDITOR 或 VIEWER。Okta 或 Microsoft Entra ID 不会直接连接到 Argo CD；根据文档，应将外部 IdP 设置为 Identity Center 身份源，使用 SAML 登录，并使用 SCIM 同步用户和组。

- 一个 Identity Center 实例只能有一个身份源。如果组织实例已经使用其他 IdP，则若只为 Argo CD 使用另一个 IdP，需要使用账户实例（未测试）。
- 创建后无法更改关联的 Identity Center 实例（根据 EKS 控制台帮助）。映射以用户和组 ID 的形式存储；将身份源切换为 Active Directory 会删除用户和组，因此必须重新配置映射。
- 一个 Capability 最多可映射 1,000 个身份，因此应映射组而非用户。全局角色只有三个，所以精细化的 `argocd-rbac-cm` 策略必须迁移到 AppProject 角色。

<span id="kro"></span>

## 4. kro Capability

AWS 文档称，托管式 kro 使用相同的上游控制器，完全兼容。在测试中，报告的版本 `0.9.4-eks-1` 与最新 OSS 版本一致，同一组 RGD 和 CEL 表达式的行为也完全相同。差异在于权限和运维。有关 kro 概念和示例，请参见 [kro 章节](../platform-engineering/03-kro.md)。

### 默认权限无法让控制器启动

`AmazonEKSKROPolicy` 仅涵盖 `kro.run` 组和 CRD。它既不授予对 RGD Schema 组生成的 API（例如 `platform.example.com`）执行 watch 的权限，也不授予创建子 Deployment 和 Service 的权限。失败表现为缓存同步超时，而不是权限被拒绝。

```text
ControllerReady=False FailedToStart
  ...
  cache sync timeout for platform.example.com/v1alpha1, Resource=nginxapps
```

eksctl 指南建议附加 `AmazonEKSClusterAdminPolicy` 以开始使用。一种最小权限替代方案是在 access entry 中添加 Kubernetes 组，并为每个 RGD 绑定一个 ClusterRole。

```bash
aws eks update-access-entry --cluster-name "$CLUSTER_NAME" \
  --principal-arn "arn:aws:iam::${ACCOUNT_ID}:role/${CLUSTER_NAME}-kro" \
  --kubernetes-groups kro-workloads
```

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: kro-workloads-reviewed-nginxapps
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: kro:controller:reviewed-nginxapps
subjects:
  - kind: Group
    name: kro-workloads
    apiGroup: rbac.authorization.k8s.io
```

在 RGD 创建后授予权限时，228 s 后它才变为 `Active`（推测是控制器重试间隔；日志中未确认）。先应用 ClusterRole 再创建的第二个 RGD 则立即变为 `Active`。请将 RGD 和对应的 ClusterRole 放在同一 Git 路径中，并使用 sync waves 先应用 RBAC（未测试 sync waves）。OSS 的 `rbac.mode: aggregation` 也只会将带标签的 ClusterRole 合并到控制器权限中，因此需要类似的配置（根据 Chart，未测试）。

### 生命周期性能和迁移

| 阶段（每项运行 5 次） | 托管式 | OSS 0.9.4 |
|---|---|---|
| 创建 → `ACTIVE` | 2.49–3.73 s | 2.43–3.44 s |
| Spec 更改 → Deployment 更新 | 0.50–0.52 s（有一次异常值为 51.6 s，原因未知） | 0.49–0.56 s |
| 删除 → Deployment 和 Service 消失 | 1.02–3.02 s | 1.01–4.38 s |

在托管式 → OSS → 托管式之间切换后，两个 RGD 和四个实例均保持完整（先移除一个控制器，再安装另一个控制器）。若要实现零停机迁移，请按照 AWS 的流程迁移 leader-election lease（未测试），但请注意，该流程中的 Chart 路径和值键已过时：当前 Chart 为 `oci://registry.k8s.io/kro/charts/kro`，0.9.4 使用的键为 `config.leaderElectionNamespace`。

### 易错点：kro 会接管同名的现有 CR

如果命名空间中已经存在与子资源同名的 CR，kro 不会拒绝，而是会使用 server-side apply 覆盖它。在测试中，一个现有的 ACK Table CR 被添加了 `kro.run/owned=true`，其 `spec.tableName` 也被更改；ACK 因此创建了一个新表，而原表则无人管理。删除该实例时，被接管的 CR 也会一起删除。OSS 0.9.4 也复现了相同的行为，因此这是上游行为。

- 为子资源名称添加 RGD 专属后缀（`${schema.metadata.name + "-os"}`）。
- 将 kro 管理的命名空间与用户直接创建 CR 的命名空间分开。
- 对保存数据的 ACK 资源设置 `services.k8s.aws/deletion-policy: retain`。这不能阻止重命名后迁移到新资源，因此真正的解决办法是区分名称（未测试 retain 与此场景结合的行为）。
- 在多租户集群中，不要允许实例随意选择 `ingressClassName` 和主机名；应在 RGD 中固定这些值，或根据实例名称生成。

<span id="ack"></span>

## 5. ACK Capability

托管式 ACK 将所有上游已正式推出的服务控制器打包到一个 Capability 中；预览版控制器达到正式发布状态后也会自动添加（根据文档）。有关 ACK 资源模型、接管和保留，请参见 [ACK 章节](../platform-engineering/02-ack.md)。

### 使用 IAMRoleSelector 为各团队配置 IAM

只向 Capability 角色授予代入团队角色的权限，并使用集群范围的 `IAMRoleSelector` 将命名空间映射到角色。每个团队角色都信任 Capability 角色，并允许 `sts:AssumeRole` 和 `sts:TagSession`。

```json
{"Effect": "Allow", "Action": ["sts:AssumeRole", "sts:TagSession"],
 "Resource": ["arn:aws:iam::111122223333:role/ack-team-a",
              "arn:aws:iam::111122223333:role/ack-team-b"]}
```

```yaml
apiVersion: services.k8s.aws/v1alpha1
kind: IAMRoleSelector
metadata:
  name: team-b
spec:
  arn: arn:aws:iam::111122223333:role/ack-team-b
  namespaceSelector:
    names: [team-b]
```

在 team-b 中创建一个 S3 Bucket 时，由于其角色仅允许 SQS 操作，因此创建失败并返回 `AccessDenied`，错误消息还指出了实际使用的角色（`assumed-role/ack-team-b/...`）。CR 条件 `ACK.IAMRoleSelected=True` 也表明匹配到了选择器。调查详情如下：

- S3 Bucket 控制器会先调用 `s3:ListAllMyBuckets`。即使按名称模式缩小了 Bucket 资源的范围，似乎仍需单独授予此权限（资源为 `*`；未测试不授予此权限的情况）。
- 根据文档，没有匹配选择器的命名空间会使用 Capability 角色。如果 Capability 角色没有服务权限，默认结果就是拒绝。
- 若要在 OSS 控制器中实现相同的权限分离，请设置 `featureGates.IAMRoleSelector=true` 和 `enableCARM=false`。使用 Chart 默认的 `enableCARM: true` 时，控制器会陷入崩溃重启循环，并报错 `cannot enable feature gate 'IAMRoleSelector' when flag 'enable-carm' is set to true`。

### 资源创建、标签和漂移

| 资源 | 托管式（运行 3 次） | OSS（运行 2 次） |
|---|---|---|
| SQS Queue | 1.04–1.06 s | 1.10–1.16 s |
| S3 Bucket | 3.10–3.14 s | 3.20–3.32 s |
| DynamoDB Table | 11.28–11.53 s | 10.15–11.54 s |

只有 Capability 首次创建后紧接着进行的第一次创建较慢：Queue 为 7.3 s，Bucket 为 10.9 s，Table 为 16.5 s。

托管式 ACK 会为 AWS 资源添加五个标签：`eks:controller-version`、`eks:kubernetes-namespace`、`eks:kubernetes-resource-name`、`eks:kubernetes-api-group` 和 `eks:eks-capability-arn`。每次 AWS API 调用都会携带会话标签 `eks:eks-capability-arn`、`eks:kubernetes-namespace` 和 `eks:kubernetes-api-group`。OSS 会添加两个标签：`services.k8s.aws/controller-version` 和 `services.k8s.aws/namespace`。从 OSS 迁移时标签前缀会发生变化，因此应同时更新成本分配标签和基于标签的 IAM 条件。

ACK 不会实时监听 AWS 端的更改。通过 CLI 在 ACK 外部更改 SQS `VisibilityTimeout` 后，托管式（运行 2 次）和 OSS（运行 1 次）均未在 25 分钟内定期将其还原。托管式中观察到的两次还原分别发生在 Capability 因日志配置更改而进入 `UPDATING` 状态 86 s 后，以及 Capability 刚重新创建之后（调用时间来自 CloudTrail）。控制器重启似乎是触发原因，但日志中未确认。OSS 默认 resync 间隔为 10 小时（`reconcile.defaultResyncPeriod: 36000`），并且可调整；托管式的间隔未公开且无法更改。如果快速恢复很重要，可通过 SCP 或 IAM 条件阻止越权更改，例如只允许带有匹配 `aws:PrincipalTag/eks:eks-capability-arn` 的调用修改带有 `aws:ResourceTag/eks:eks-capability-arn` 标签的资源（未测试）。

### 托管式的差异和迁移

- 没有 `FieldExport` CRD。若要将状态值导出到 ConfigMap 或 Secret，请使用其他方法，例如让 kro 将状态写入 ConfigMap。
- 使用 CLI 2.38.3 执行 `--configuration '{"ack":{"disabledServices":["sagemaker"]}}'` 后，禁用服务在 12.5 s 内生效，但该服务已安装的 CRD 在 350 s 后仍然存在。请改为在创建时指定未使用的服务（未测试创建时设置）。
- 控制器版本比最新 OSS 版本落后一个版本（s3 为 1.12.2，对比 1.13.1；sqs 为 1.7.1，对比 1.8.2）。
- 接管（`services.k8s.aws/adoption-policy: adopt-or-create`）和 retain 注解在托管式 Capability 上均可正常工作：接管耗时 4.7 s，带有 retain 的 Queue 删除后仍保留在 AWS 中（在托管式上测得）。删除 Capability 后，OSS 控制器按原样接管了剩余的 12 个 CR。

<span id="together"></span>

## 6. 同时使用这三者

一种自然的职责划分是：Argo CD 从 Git 同步清单，kro 将多个资源组合成一个 API，ACK 则创建其中的 AWS 资源。经过测试的 `OrderService` RGD 创建了一个 ACK Queue 和一个 Table，将它们的状态值（Queue URL、Table ARN）复制到 ConfigMap 中，并启动了一个 Deployment。

| 组合 | 结果 | 所需额外配置 |
|---|---|---|
| Argo CD → ACK Queue | Git 中的 Queue CR 在 6.5 s 内同步完成 | 为 Argo CD Capability 角色配置针对 `queues.sqs.services.k8s.aws` 的 RBAC |
| kro → ACK Queue 和 Table + ConfigMap + Deployment | 实例在 13.2–34.3 s 内变为 `ACTIVE`（耗时主要在 DynamoDB Table 创建） | 为 kro Capability 角色配置针对 ACK 资源的 RBAC；在 ACK 端配置 IAMRoleSelector |

ACK CRD 不包含在默认 EKS 访问策略（例如 `AmazonEKSEditPolicy`）中，因此无论由 Argo CD 还是 kro 创建 ACK 资源，相应组件都需要这些 API 组的权限。这两项测量是分开进行的；没有端到端运行完整的三步链路。

<span id="upgrade"></span>

## 7. 集群升级和 Capability 版本

### 原地升级期间的行为

一个具有全部三种 Capability 的集群从 1.36 原地升级到了 1.37。控制平面升级耗时约 7 分钟，三种 Capability 均保持 `ACTIVE`，版本、健康状况和 `modifiedAt` 均未改变。

| 阶段 | Argo CD 自愈 | kro 传播 | ACK Queue 同步 |
|---|---|---|---|
| 升级前（运行 3 次） | 2.1–14.6 s | 1.02–1.04 s | 1.49–3.53 s |
| 升级期间（运行 4 次） | 2.1 s、6.1 s、112.9 s、254.5 s | 1.02–1.07 s | 1.52–1.58 s |
| 升级后（运行 5 次） | 2.3 s，随后为 251–252 s | 1.01–1.15 s | 1.47–1.57 s |

对于 kro 和 ACK，四次“升级期间”的运行中有一次是在升级刚完成后进行的。升级期间的自愈延迟在升级后再次出现，表现完全相同，因此原因是上述自愈退避机制，而非升级。API server 版本在 1.36.4 和 1.37.0 之间交替变化的约 3 分钟内，没有测量 kro 和 ACK。节点组未升级。

原地升级无需执行任何 Capability 专属步骤。自管式控制器需要确认是否支持新的 Kubernetes 版本，并可能需要先升级；托管模型则将兼容性检查交由 AWS 处理。请注意，EKS 升级洞察检查项中没有任何一项涵盖 Capability。

### 无法选择版本

`create-capability` 和 `update-capability` 均没有版本参数，AWS 文档也只提到“自动更新和安全补丁”。在文档中找不到 Capability 版本的更新计划、提前通知、维护时段、逐版本发行说明或回滚路径。2026 年 7 月新增的[集群版本回滚](./08-eks-upgrades.md)只能回滚 Kubernetes 次要版本，回滚文档也未提及 Capability。Capability 没有版本参数，因此不要将其视为回滚 Capability 版本的方法（推断）。在测试中，10 月 21 日创建的 Argo CD Capability 报告版本为 `3.4.6-eks-2`，而一天后在另一个集群创建的实例报告版本为 `3.4.7-eks-1`。控制器版本可能独立于集群升级而变化。

可通过以下方式为有问题的版本做好准备。

| 准备事项 | 方法 | 依据 |
|---|---|---|
| 记录版本变化 | 轮询 `describe-capability` 返回的 `capability.version`，并将其与事故情况关联 | 已测量（已确认该字段） |
| 验证集群 | 先在具有相同 Capability 的集群上运行生产环境 RGD、Application 和 ACK CR。你无法控制推出顺序，因此不能保证生产集群之前会先更新验证集群 | 推断 |
| 在 Git 中固定行为 | 将健康检查（`resource.customizations`）、同步选项和 RBAC 保存在 Git 中，以便重新创建或迁移时还原相同行为 | 已测量（已应用这些设置） |
| AWS Support | 用户端无法回滚，因此应提交支持案例。AWS 文档建议通过 Support 调整自愈时间 | 推断（自愈时间根据文档） |
| 临时回退到自管式方案 | 使用 RETAIN 删除 Capability 会保留 CRD 和资源，同一 CRD 上的 OSS 控制器会接管（已在 kro、ACK 和 Argo CD 上测量）。Argo CD 需要将集群 Secret 的 `server` 从 EKS ARN 改为 API URL（本地使用 `https://kubernetes.default.svc`）；按 ARN 注册的远程或私有 spoke 在 OSS 方案下需要各自配置网络路径和身份验证。要返回托管式方案，必须重新创建 Capability（Argo CD 约需 6 分钟） | 已测量 |
| 按服务回滚 ACK | 仅将受影响的服务添加到 `disabledServices`，然后安装或扩容对应的自管式控制器。OSS 控制器需要单独配置 IAM；使用 IAMRoleSelector 时，还需设置 `featureGates.IAMRoleSelector=true` 和 `enableCARM=false`。尚未测试在 Capability 安装的 CRD 上运行 OSS Chart。已安装的 CRD 会保留（已测量） | 根据文档 |

如果你明确需要固定版本，AWS 文档本身也建议使用自管式方案（“需要特定 Kubernetes 资源 API 版本、自定义控制器构建版本”）。

<span id="multicluster"></span>

## 8. 多集群和蓝绿替换

### Argo CD hub 和私有 spoke

hub 集群上的 Argo CD Capability 注册了同一账户和 VPC 中的一个 spoke 集群。该集群的 API endpoint 仅提供私有访问，且未配置任何网络设置（endpoint、安全组、路由）。另一个 VPC 中的工作站无法访问该 spoke，因此连接似乎使用了 AWS 提供的路径。spoke 需要手动创建一个允许 hub 的 Capability 角色访问的 access entry。

| Spoke access entry 权限 | 结果 |
|---|---|
| `AmazonEKSEditPolicy` + `AmazonEKSAdminViewPolicy` | 连接和身份验证成功，但 `CreateNamespace=true` 失败并报错 `namespaces is forbidden`；五次自动重试（约 303 s）后仍未成功 |
| + `AmazonEKSArgoCDClusterPolicy`，然后手动同步 | 在 11.1 s 内同步成功且状态为 Healthy |

- 集群 Secret 只接受 EKS ARN，因此非 EKS 集群不能作为目标集群（根据文档）。
- Application 费用按每个目标集群中的 Application 数量计算，因此将 Application 放在 hub 或各集群中，成本相同；只有 Argo CD 实例数量增加时，Capability 费用才会上升。不过，hub 的 Capability 角色对所有 spoke 都有写入权限，因此应考虑限制 AppProject 目标或按团队拆分 Capability。
- 根据文档，其他账户中的集群只需要为 hub Capability 角色创建 access entry（未测试）。托管式限制为 100 个远程集群和 3,000 个 Application。

### kro 和 ACK 的部署位置

kro 和 ACK Capability 仅管理其自身所在的集群。要让 hub 上的 Argo CD 将 RGD 实例或 ACK CR 部署到 spoke，spoke 也需要 kro 或 ACK（托管式或 OSS）。

| 部署布局 | 适用情况 | 注意事项 |
|---|---|---|
| 每个集群都运行 kro，并通过 ApplicationSet 推出 RGD | 应用团队在每个集群上使用相同 API | Capability 费用和 RBAC 工作会随集群数量增加；文档不保证各集群上的 kro 版本相同（未测试） |
| 仅在 hub 上运行 kro，由 RGD 为 spoke 创建 ACK 资源和 Argo CD Application | 平台抽象集中定义在一处 | 权限和影响范围集中在 hub；spoke 应用团队无法直接使用 kro API（未测试） |
| 集中式 ACK（hub） | 数据库、IAM、VPC 等平台管理的资源 | hub Capability 角色持有针对所有账户和资源的权限 |
| 分布式 ACK（每个集群） | 与工作负载一起声明 Queue 和 Bucket | IAMRoleSelector 配置会随集群数量增加 |
| 混合式 ACK | 在 hub 上管理管理员范围的资源，在 spoke 上管理工作负载范围的资源 | 需要范围规则，确保同一资源不会在两个位置声明 |

无论采用哪种布局，都要设置范围规则，确保不会有两个集群同时声明相同的 AWS 资源。

### 蓝绿替换

- **Argo CD**：Capability 隶属于其所在集群，因此替换运行 Argo CD 的集群时需要重新创建 Capability。默认地址 `argocd-<ID>-<account ID>.eks-capabilities.<region>.amazonaws.com` 在不同集群间会有所不同，因此 UI 和 webhook URL 也会变化。在创建时设置 `endpointPrefix` 后，删除并使用相同前缀重新创建可保留地址（仅在同一集群上测试）。该地址不包含任何特定于集群的信息，因此迁移到另一个集群后也应该能正常使用。如果前缀在账户和 Region 范围内唯一（未测试），旧集群和新集群就无法同时使用该前缀；替换操作只能先删除再重新创建，期间 UI、webhook 和同步都会中断（测得删除耗时 100 s，重新创建耗时 338 s）。如果无法接受这段暂停，可先使用新前缀启动新的 Capability 并更改 Git webhook URL；启用新 Capability 前，应禁用旧 Capability 的自动同步，或以非级联方式删除其 Application，并预先在目标集群上为新 Capability 角色创建 access entry（未测试）。创建后无法更改前缀。应将 Argo CD 部署在专用 hub 上，而不是经常替换的工作负载集群上。
- **kro**：ClusterRole 和绑定通过 Git 迁移，但向 access entry 添加 Kubernetes 组需要调用 EKS API。请将其纳入创建集群的 IaC（eksctl、Terraform 等）。
- **ACK**：一种可能的顺序是先用 `deletion-policy: retain` 删除旧集群中的 CR，再用 `adoption-policy: adopt-or-create` 在新集群上接管相同资源（每一步均已测量；未测试完整的跨集群流程）。如果 SCP 根据 `eks:eks-capability-arn` 标签阻止更改，新 Capability 的 ARN 会有所不同，接管可能因此被阻止；切换期间应放宽该条件，或改为根据环境或团队标签设置条件。

<span id="compare"></span>

## 9. 与自管式方案的比较及选择时机

| 项目 | 托管式 Capability | 自管式（OSS） |
|---|---|---|
| 安装时间 | Argo CD 349 s、kro 70 s、ACK 386 s | Argo CD 43.4 s、kro 15.6 s、三个 ACK 控制器 46 s |
| 节点资源 | 无 | Argo CD 7 个 Pod（339–624Mi 内存）、kro 1 个 Pod（requests 256m、128Mi）、ACK 3 个 Pod（每个 requests 50m、64Mi） |
| 版本 | 由 AWS 选择，无法固定 | 由你选择（测试时，Argo CD v3.5.5 和 ACK s3 1.13.1 是最新版本） |
| 默认权限 | 范围较窄；需要自行授予部署、子资源和 IAM 权限 | Argo CD 和 kro Chart 默认值为 `*/*/*` |
| 性能 | kro、ACK 和 Argo CD 自愈表现与 OSS 相当；Argo CD 默认轮询较慢 | 基准（Argo CD 3.4.6 和 kro 0.9.4 在相同版本下测量；ACK OSS 使用的版本更新一个版本） |
| SSO | 仅支持 Identity Center，需要配置两个字段 | 可使用 Dex、OIDC 等，并由你自行配置 |
| 远程集群 | 使用 EKS ARN + access entry；私有集群无需网络配置 | 每个集群都需要配置 API URL、身份验证和网络路径 |
| 缺少的功能 | Argo CD Notifications、CMP、`argocd admin`、Lua 标准库；ACK FieldExport | 无 |
| 无法直接调整 | Argo CD 轮询、ACK resync 间隔、控制器标志和资源限制；Argo CD 自愈退避只能通过 AWS Support 调整 | 均可调整 |
| 日志 | Vended Logs | `kubectl logs`，以及你自己的日志收集方案 |

适合使用托管式方案的情况：

- 你正在构建一个要部署到多个 EKS 集群的 hub，尤其是私有集群或其他账户中的集群
- 你的 AWS 登录已经集中在 Identity Center 中，并且不想自行运维 Argo CD SSO
- 你通过 Kubernetes 管理多个 AWS 服务，逐个运行 ACK 控制器是一种负担，并且需要按团队隔离 IAM 权限
- 你希望平台控制器的默认权限范围较窄，并明确配置在 access entry 和 RBAC 中

应继续使用自管式方案的情况：

- 你依赖 Notifications、CMP、FieldExport 或 Lua 标准库
- 部署目标中包含非 EKS 集群
- 只有 Argo CD 必须使用不同于组织 Identity Center 的 IdP，且账户实例不可行
- 你必须自行控制控制器版本、升级时间以及轮询或 resync 间隔

适合评估的一个时机是在集群数量超过一个之前：hub 的位置、Identity Center 实例和 `endpointPrefix` 都是固定的，或在创建后难以更改。另一个时机是自管式 Argo CD 需要进行 HA 重建或重大版本升级时。AWS 迁移流程会将现有控制器缩容到零，迁移 Application 和 Secret，并将 `destination.server` 更改为 ARN；期间同步会停止（未测试）。

<span id="pricing"></span>

## 10. 定价

价格适用于首尔（ap-northeast-2），使用 AWS Pricing API 于 2026 年 10 月 21 日查询，按每月 730 小时计算。

| Capability | Capability 费用 | 每对象费用 | 示例（月费） |
|---|---|---|---|
| Argo CD | 每小时 $0.034799（每月约 $25.4） | 每个 Application 每小时 $0.001726（按目标集群计数） | 9 个应用约 $36.7，100 个应用约 $151 |
| kro | 每小时 $0.006038（每月约 $4.4） | 每个实例每小时 $0.000061 | 100 个实例约 $8.9 |
| ACK | 每小时 $0.006038（每月约 $4.4） | 每项资源每小时 $0.000061 | 200 项资源约 $13.3 |

作为比较，将 m7g.large 的费用（首尔每小时 $0.1003）按默认自管式安装进行分摊后，Argo CD（624Mi 内存）约为 $5.6，kro（CPU request 为 256m）约为 $9.4，三个 ACK 控制器（CPU request 共 150m）约为 $5.5。HA 部署以及更多应用或服务也会增加 OSS 方案的成本。随着应用数量增加，托管式 Argo CD 会变得更贵；对于 kro 和 ACK，两者的成本差异较小，因此主要取决于运维负担和功能缺口。

<span id="refs"></span>

## 11. 核验范围和参考资料

测量在 ap-northeast-2 的一个账户中进行：一个 EKS 1.36.4 集群，以及用于升级和多集群测试的两个集群（hub 从 1.36 升至 1.37，私有 spoke 为 1.37）。场景运行了 1–5 次，最多使用 9 个 Argo CD 应用、6 个 kro 实例和约 20 项 ACK 资源。ACK 仅针对 S3、SQS 和 DynamoDB 进行了测试。以下内容未经测试，依据文档：Okta 或 Entra ID 集成和 Identity Center 账户实例、通过 VPC endpoint 进行私有访问、注册其他账户或 VPC 中的集群、Notifications 和 CMP、跨账户 ACK、托管式和 OSS 同时运行时的零停机迁移，以及完整的跨集群 ACK 先 retain 再 adopt 流程。测量完成后，测试集群和 AWS 资源均已删除。

- [EKS Capabilities](https://docs.aws.amazon.com/eks/latest/userguide/capabilities.html)
- [EKS Capabilities 注意事项](https://docs.aws.amazon.com/eks/latest/userguide/capabilities-considerations.html)
- [Capability Kubernetes 资源](https://docs.aws.amazon.com/eks/latest/userguide/capability-kubernetes-resources.html)
- [Argo CD 注意事项](https://docs.aws.amazon.com/eks/latest/userguide/argocd-considerations.html)
- [比较 EKS Capability for Argo CD 与自管式 Argo CD](https://docs.aws.amazon.com/eks/latest/userguide/argocd-comparison.html)
- [注册目标集群](https://docs.aws.amazon.com/eks/latest/userguide/argocd-register-clusters.html)
- [配置 Argo CD 设置](https://docs.aws.amazon.com/eks/latest/userguide/argocd-configure-settings.html)
- [配置 kro 权限](https://docs.aws.amazon.com/eks/latest/userguide/kro-permissions.html)
- [比较 EKS Capability for kro 与自管式 kro](https://docs.aws.amazon.com/eks/latest/userguide/kro-comparison.html)
- [配置 ACK 权限](https://docs.aws.amazon.com/eks/latest/userguide/ack-permissions.html)
- [比较 EKS Capability for ACK 与自管式 ACK](https://docs.aws.amazon.com/eks/latest/userguide/ack-comparison.html)
- [访问 EKS Capabilities 控制器日志](https://docs.aws.amazon.com/eks/latest/userguide/capabilities-controller-logs.html)
- [将集群回滚到之前的 Kubernetes 版本](https://docs.aws.amazon.com/eks/latest/userguide/rollback-cluster.html)
- [Amazon EKS 定价](https://aws.amazon.com/eks/pricing/)
- 测量博客（韩语）：[托管式 Argo CD](https://blog.atomai.click/eks-capabilities-argocd/)、[托管式 kro](https://blog.atomai.click/eks-capabilities-kro/)、[托管式 ACK](https://blog.atomai.click/eks-capabilities-ack/)
- 测试清单：[Atom-oh/eks-capabilities-demo](https://github.com/Atom-oh/eks-capabilities-demo)

[EKS Capabilities 测验](../quizzes/eks/13-eks-capabilities-quiz.md)
