# Amazon EKS Capabilities：托管式 Argo CD、kro 和 ACK

> **支持的版本**：EKS 1.36–1.37、Argo CD `3.4.6-eks-2` 和 `3.4.7-eks-1`、kro `0.9.4-eks-1`、ACK `46.186.1-eks-1`、AWS CLI 2.38.3
> **上次更新**：2026年11月19日

EKS Capabilities 在集群外部的 AWS 运营环境中运行 Argo CD、kro（Kube Resource Orchestrator）和 ACK（AWS Controllers for Kubernetes）控制器。该功能于2025年11月30日正式推出。控制器日志交付（Vended Logs）于2026年6月推出，Argo CD 的自定义 `argocd-cm` 配置则于2026年8月推出。

本章中的数据于2026年10月在 ap-northeast-2 的测试集群上测得。主集群使用私有子网、`API` 身份验证模式和两个 m7g.large 节点（用于升级和多集群测试的 hub 和 spoke 各使用一个节点）。对照场景也在同一集群上安装自托管（OSS）控制器后重复执行。每种场景仅运行了 1–5 次，因此请将这些数据视为范围，并在自己的环境中重新核实后再做运维决策。凡是仅根据文档核实、而非实际测量的内容，均标记为“根据文档”。测量说明和原始结果见 [EKS Capabilities 博客系列](https://blog.atomai.click/eks-capabilities-argocd/)（韩语）。

## 目录

1. [通用模型](#common)
2. [创建与日常运维](#create)
3. [Argo CD Capability](#argocd)
4. [kro Capability](#kro)
5. [ACK Capability](#ack)
6. [三者协同使用](#together)
7. [集群升级与 Capability 版本](#upgrade)
8. [多集群与蓝绿替换](#multicluster)
9. [与自托管方案的比较及选择建议](#compare)
10. [定价](#pricing)
11. [验证范围与参考资料](#refs)

---

<span id="common"></span>

## 1. 通用模型

| 项目 | 行为 |
|---|---|
| 控制器位置 | AWS 所有的基础设施上。工作节点上没有 Pod（三者测得的数量均为零） |
| 集群访问 | Capability 角色（受信任主体 `capabilities.eks.amazonaws.com`）通过 EKS 访问条目调用 API Server。仅启用私有 API 端点时也可使用 |
| 数量 | 每个集群中每种 Capability 类型各一个 |
| 版本 | 由 AWS 选择并滚动更新。创建/更新 API 没有版本参数，因此无法固定或选择版本 |
| 删除 | 仅支持 `--delete-propagation-policy RETAIN`。CRD、CR、已部署资源和访问条目都会保留 |
| 日志 | 无法通过 `kubectl logs` 获取。日志通过 CloudWatch Vended Logs 交付到 CloudWatch Logs、S3 或 Amazon Data Firehose（参见 [EKS 监控与日志记录](./06-eks-monitoring-logging.md)） |
| 定价 | 按小时收取 Capability 费用，另按受管理对象收费（Argo CD 按 Application、kro 按实例、ACK 按资源） |

三者的共同特点是默认权限范围较窄。若只有自动创建的访问条目策略，Argo CD 无法部署，kro 无法启动 RGD 控制器，ACK 也无法在没有相应服务 IAM 权限的情况下创建 AWS 资源。相比之下，Argo CD 和 kro 的 OSS Helm Chart 默认都授予控制器 `apiGroups: ["*"], resources: ["*"], verbs: ["*"]` 权限。

<span id="create"></span>

## 2. 创建与日常运维

### Capability 角色与创建命令

在 Capability 角色中信任 `capabilities.eks.amazonaws.com`，并允许 `sts:AssumeRole` 和 `sts:TagSession`。kro 不会调用 AWS API，因此不需要权限策略。针对公开 Git 仓库的 Argo CD 也无需权限策略即可正常工作。

```bash
aws eks create-capability --cluster-name "$CLUSTER_NAME" \
  --capability-name kro --type KRO \
  --role-arn "arn:aws:iam::${ACCOUNT_ID}:role/${CLUSTER_NAME}-kro" \
  --delete-propagation-policy RETAIN

aws eks describe-capability --cluster-name "$CLUSTER_NAME" --capability-name kro \
  --query 'capability.{status:status,version:version}'
```

| Capability | `CREATING` → `ACTIVE` | 删除 | 自动创建的访问条目策略 | 已安装的 CRD |
|---|---|---|---|---|
| Argo CD | 349 s（另一集群上使用 `endpointPrefix` 创建新 Capability 时为 385 s；使用相同前缀重新创建时为 338 s） | 100.5 s | `AmazonEKSArgoCDClusterPolicy`（集群）、`AmazonEKSArgoCDPolicy`（`argocd` 命名空间） | `applications`、`applicationsets`、`appprojects` |
| kro | 70.1–70.4 s | 46.9 s | `AmazonEKSKROPolicy` | `resourcegraphdefinitions.kro.run`、`graphrevisions.internal.kro.run` |
| ACK | 385.7 s（CRD 已存在时为 77 s） | 67.3 s | `AmazonEKSACKPolicy` | 267 个（66 个服务 API 组，以及 `services.k8s.aws` 中的 `IAMRoleSelector`） |

### 运维说明

- **保持 AWS CLI 为最新版本。** CLI 2.35.11 在 `argoCd` 下只识别 `namespace`、`awsIdc`、`rbacRoleMappings` 和 `networkAccess`（不含 `endpointPrefix`），并会因 ACK 设置报错：`Unknown parameter in configuration: "ack", must be one of: argoCd`；2.38.3 则接受这两项配置。在判断某项功能不受支持之前，请先检查 CLI 版本。
- **一次只修改一个 Capability。** 每次添加日志交付源都会使 Capability 进入 `UPDATING` 状态约 6.6–7 秒，期间进行下一项修改会失败并报错：`ConflictException: ... currently in UPDATING state`。每次修改之间都要等待状态变为 `ACTIVE`。
- **从一开始就启用日志交付。** 控制器在集群外部运行，之后日志将是了解其内部行为的唯一途径（CloudTrail 仍会显示 AWS API 调用时间）。日志采用结构化 JSON 格式；Argo CD 会记录每次 reconcile 各阶段的耗时（`compare_app_state_ms`、`patch_ms` 等）。
- **RETAIN 会保留“控制器以外的一切”。** 删除 Capability 期间，CR 的更改不会被 reconcile（通过更改 kro 实例副本数进行了验证）。安装使用相同 CRD 的 OSS 控制器后，它会处理尚未应用的更改。

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

仅有自动创建的访问条目还不足以进行同步，因为 Argo CD 会列出集群中的所有资源类型来构建缓存，而不只是它要部署的资源。

| Capability 角色的集群权限 | 结果 |
|---|---|
| 仅有自动创建的访问条目 | `ComparisonError: ... podtemplates is forbidden ... at the cluster scope` |
| + `AmazonEKSEditPolicy` | 141 s 后仍然失败；列出 `securitygrouppolicies.vpcresources.k8s.aws` 时被拒绝 |
| + `AmazonEKSAdminViewPolicy` | 在 11.6 s 内同步成功并处于 Healthy 状态 |
| 部署 kro/ACK API 的 CR（一个 NginxApp 实例、一个 ACK Queue） | `nginxapps.platform.example.com is forbidden`。在访问条目中添加 Kubernetes 组并为该 API 组绑定 ClusterRole 后，16 s 内解决 |

AWS 文档建议使用 `AmazonEKSClusterAdminPolicy`（等同于 `system:masters`）开始使用，并介绍了生产环境中的最小权限设置：集群范围的读取权限，加上命名空间范围的 `AmazonEKSEditPolicy`。测试中，集群范围的 Edit 权限加上 AdminView，以及针对每个平台 CRD 的 ClusterRole，能够正常工作；这比文档所述的生产设置权限范围更广。要进一步缩小权限范围，可以使用托管 Capability 支持的 `resource.respectRBAC`，将监视范围限制为获准访问的资源（未测试）。

### Git 轮询与 Webhook

| 方法 | 提交 → 同步完成（3 次运行） |
|---|---|
| 托管式，默认轮询（根据文档为每 6 分钟一次） | 341.8 s、619.3 s、697.1 s |
| 托管式，GitHub webhook | 7.0–7.3 s |
| 自托管 3.4.6，默认轮询（120 s + 60 s 抖动） | 115.7–171.4 s |

托管式轮询间隔（`timeout.reconciliation`）不是可配置的键，抖动值也未公开。如果部署延迟不能出现数分钟的波动，实际上就必须使用 webhook。在 Capability 创建的 `argocd-webhook-creds-secret` 中，为 `webhook.github.secret` 设置一个随机字符串，并在 Git 仓库中将 `<server URL>/api/webhook` 注册为 webhook URL，同时使用相同的密钥。服务器 URL 是 AWS 托管的公共地址，因此无需单独开放 webhook 端点。通过 VPC 端点限制公共访问很可能也会阻断 GitHub webhook（未测试）。

漂移自愈表现相当：托管式为 2.08–2.32 s，自托管为 1.05–3.06 s。不过，同一应用在没有新提交的情况下反复自愈，会触发上游退避机制（从 2 s 开始，每次乘以 3，上限为 300 s），导致恢复时间延长到接近 5 分钟（实测为 251–254 s）。自托管方案可通过 `--self-heal-backoff-*` 标志调整该行为。托管式只开放三个 `argocd-cmd-params-cm` 键（`hydrator.enabled`、`application.namespaces`、`applicationsetcontroller.namespaces`），AWS 文档建议通过 AWS Support 申请调整自愈时序。如情况紧急，请手动触发同步。

### 设置、健康检查与 CLI

在 Capability 命名空间中创建带有标签 `app.kubernetes.io/part-of: argocd` 的 `argocd-cm` ConfigMap。不受支持的键会被静默忽略。

| 项目 | 结果 |
|---|---|
| `ui.bannercontent` | 在 UI 中显示 |
| kro 实例的 Lua 健康检查 | 已应用；脚本编辑内容约 12 s 后生效 |
| Lua `string.upper()`、`os.time()` | `attempt to index a non-table object(nil)`，健康状态为 `Unknown`。与上游默认行为相同（`useOpenLibs` 关闭），但托管式无法启用该选项 |
| `argocd login --username admin` 或 `--sso` | 两者均失败 |
| UI 中获取的令牌 + `ARGOCD_SERVER`、`ARGOCD_AUTH_TOKEN`、`ARGOCD_OPTS=--grpc-web` | `app list/get/sync`、`cluster list`、`proj list` 均可用 |
| PreSync hook 睡眠 150 s | 在 161 s 后变为 `Succeeded`，尽管文档所述同步超时为 120 s；超时限制适用于哪个阶段尚不明确 |

Argo CD 3.x 默认不会在 Application 状态中保存资源健康状态，因此使用 `kubectl get application -o json` 获取到空的 `.status.resources[].health` 属于正常情况。请通过 `argocd app get` 或 UI 检查健康状态。

根据文档，配置管理插件（CMP）、自定义 SSO、UI 扩展和 `argocd admin` 等功能均不受支持。如果你通过 CMP 生成清单，就无法直接迁移到托管 Capability。上文所述的2026年10月测量当时尚不支持 Notifications 控制器，该功能于2026年11月推出（见下文）。

### 2026年11月更新：支持 Argo CD Notifications

根据 [2026年11月3日的公告](https://aws.amazon.com/about-aws/whats-new/2026/11/amazon-eks-argo-cd-notifications/)，EKS Argo CD Capability 现在支持 Argo CD Notifications：你可以在集群中定义触发器和消息模板，并通过注释为各个 Application 订阅通知，方式与上游 Argo CD 相同。支持 16 种通知服务，包括 Slack、PagerDuty、Opsgenie、Amazon SQS 和 Amazon EventBridge。SQS 和 EventBridge 通过 IAM Capability 角色进行身份验证，因此部署事件可以馈送到事件驱动工作流，无需在集群中存储凭证；对于需要第三方凭证的服务（例如 Slack 令牌），可以引用 AWS Secrets Manager ARN 来代替 Secret。所有提供该 Capability 的区域均可免费使用。本文中的测量早于该功能发布，因此没有在此测试通知行为。

### 登录：仅限 IAM Identity Center

身份验证仅支持 IAM Identity Center，不支持本地用户。Capability 配置中的 `rbacRoleMappings` 可将 Identity Center 用户（`SSO_USER`）或组（`SSO_GROUP`）映射到 ADMIN、EDITOR 或 VIEWER。Okta 或 Microsoft Entra ID 不会直接连接到 Argo CD；应根据文档将外部 IdP 设置为 Identity Center 身份源，使用 SAML 登录，并使用 SCIM 同步用户和组。

- 一个 Identity Center 实例只能有一个身份源。如果组织实例已经使用其他 IdP，想让 Argo CD 单独使用不同的 IdP，就需要使用账户实例（未测试）。
- 根据 EKS 控制台帮助信息，创建后无法更改关联的 Identity Center 实例。映射中存储的是用户和组 ID；将身份源切换为 Active Directory 会删除用户和组，因此必须重新配置映射。
- 一个 Capability 最多可映射 1,000 个身份，因此应映射组而不是用户。只有三个全局角色，所以细粒度的 `argocd-rbac-cm` 策略必须迁移到 AppProject 角色。

<span id="kro"></span>

## 4. kro Capability

AWS 文档指出，托管式 kro 使用与上游相同的控制器，完全兼容。测试中，报告的版本 `0.9.4-eks-1` 与最新 OSS 版本一致，相同的 RGD 和 CEL 表达式也表现相同。差异在于权限和运维方式。关于 kro 的概念和示例，请参见 [kro 章节](../platform-engineering/03-kro.md)。

### 默认权限不足以启动控制器

`AmazonEKSKROPolicy` 仅涵盖 `kro.run` 组和 CRD。它既未授予对 RGD Schema 组生成的 API（例如 `platform.example.com`）的 watch 权限，也未授予创建子 Deployment 和 Service 的权限。此类失败会表现为缓存同步超时，而不是 forbidden。

```text
ControllerReady=False FailedToStart
  ...
  cache sync timeout for platform.example.com/v1alpha1, Resource=nginxapps
```

eksctl 指南建议附加 `AmazonEKSClusterAdminPolicy` 以开始使用。一个最小权限替代方案是在访问条目中添加 Kubernetes 组，并为每个 RGD 绑定一个 ClusterRole。

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

在 RGD 创建后才授予权限时，228 s 后 RGD 才变为 `Active`（推测是控制器的重试间隔，日志中未确认）。另一个 RGD 的 ClusterRole 先行应用，因此立即变为 `Active`。请将 RGD 和对应的 ClusterRole 放在同一 Git 路径中，并通过同步波次先应用 RBAC（同步波次未测试）。OSS 的 `rbac.mode: aggregation` 也只会将带标签的 ClusterRole 合并到控制器权限中，因此需要类似的配置（根据 Chart，未测试）。

### 生命周期性能与迁移

| 阶段（每项运行 5 次） | 托管式 | OSS 0.9.4 |
|---|---|---|
| 创建 → `ACTIVE` | 2.49–3.73 s | 2.43–3.44 s |
| Spec 更改 → Deployment 更新 | 0.50–0.52 s（有一次 51.6 s 的异常值，原因不明） | 0.49–0.56 s |
| 删除 → Deployment 和 Service 消失 | 1.02–3.02 s | 1.01–4.38 s |

在托管式 → OSS → 托管式之间切换后，两个 RGD 和四个实例都保持完整（其中一个控制器在另一个控制器安装之前已被移除）。如需实现零停机迁移，请按照 AWS 的流程迁移 leader-election 租约（未测试），但请注意，其 Chart 路径和值键已过时：当前 Chart 为 `oci://registry.k8s.io/kro/charts/kro`，0.9.4 使用的键为 `config.leaderElectionNamespace`。

### 注意事项：kro 会接管同名的现有 CR

如果命名空间中已经存在与子资源同名的 CR，kro 不会拒绝，而是通过 server-side apply 覆盖它。测试中，现有的 ACK Table CR 被添加了 `kro.run/owned=true`，其 `spec.tableName` 也被修改；ACK 随后创建了新表，而原表则不再受管理。删除该实例也会删除被接管的 CR。OSS 0.9.4 也复现了相同的行为，因此这是上游行为。

- 为子资源名称添加针对 RGD 的后缀（`${schema.metadata.name + "-os"}`）。
- 将 kro 管理的命名空间与用户直接创建 CR 的命名空间分开。
- 对包含数据的 ACK 资源设置 `services.k8s.aws/deletion-policy: retain`。该设置无法阻止重命名后迁移到新资源，因此名称隔离才是真正的解决方案（未测试 retain 与此情况同时使用的效果）。
- 在多租户集群中，不要允许实例自由选择 `ingressClassName` 和主机名；应在 RGD 中固定这些值，或根据实例名称生成。

<span id="ack"></span>

## 5. ACK Capability

托管式 ACK 会在一个 Capability 中捆绑所有已在上游正式发布的服务控制器；预览版控制器达到正式发布状态后会自动添加（根据文档）。关于 ACK 资源模型、接管和保留策略，请参见 [ACK 章节](../platform-engineering/02-ack.md)。

### 使用 IAMRoleSelector 按团队配置 IAM

只授予 Capability 角色代入团队角色的权限，并使用集群范围的 `IAMRoleSelector` 将命名空间映射到角色。每个团队角色都信任 Capability 角色，并允许 `sts:AssumeRole` 和 `sts:TagSession`。

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

在 team-b 中创建的 S3 Bucket 使用的角色只有 SQS 权限，因此创建失败并返回 `AccessDenied`；错误消息还指出了实际使用的角色（`assumed-role/ack-team-b/...`）。CR 条件 `ACK.IAMRoleSelected=True` 也表明选择器匹配成功。进一步确认了以下细节：

- S3 Bucket 控制器会先调用 `s3:ListAllMyBuckets`。即使按名称模式缩小了 Bucket 资源的权限范围，该权限（资源为 `*`）似乎仍需单独授予（未测试不授予此权限时的情况）。
- 根据文档，没有匹配选择器的命名空间会使用 Capability 角色。如果 Capability 角色没有服务权限，默认结果就是拒绝。
- 要在 OSS 控制器中实现相同的隔离，请设置 `featureGates.IAMRoleSelector=true` 和 `enableCARM=false`。如果使用 Chart 默认值 `enableCARM: true`，控制器会反复崩溃并重启，报错 `cannot enable feature gate 'IAMRoleSelector' when flag 'enable-carm' is set to true`。

### 资源创建、标签与漂移

| 资源 | 托管式（3 次运行） | OSS（2 次运行） |
|---|---|---|
| SQS Queue | 1.04–1.06 s | 1.10–1.16 s |
| S3 Bucket | 3.10–3.14 s | 3.20–3.32 s |
| DynamoDB Table | 11.28–11.53 s | 10.15–11.54 s |

只有 Capability 首次创建后紧接着进行的首次创建耗时更长：Queue 为 7.3 s，Bucket 为 10.9 s，Table 为 16.5 s。

托管式 ACK 会为 AWS 资源添加五个标签：`eks:controller-version`、`eks:kubernetes-namespace`、`eks:kubernetes-resource-name`、`eks:kubernetes-api-group` 和 `eks:eks-capability-arn`。每次 AWS API 调用都会携带会话标签 `eks:eks-capability-arn`、`eks:kubernetes-namespace` 和 `eks:kubernetes-api-group`。OSS 会添加两个标签：`services.k8s.aws/controller-version` 和 `services.k8s.aws/namespace`。从 OSS 迁移时，标签前缀会改变，因此应同时更新成本分配标签和基于标签的 IAM 条件。

ACK 不会实时监视 AWS 端的更改。通过 CLI 在 ACK 外部更改 SQS `VisibilityTimeout` 后，在 25 分钟内，托管式（2 次运行）和 OSS（1 次运行）都没有定期将其恢复。托管式中观察到的两次恢复，分别发生在 Capability 因日志配置更改进入 `UPDATING` 状态后 86 s，以及 Capability 刚刚重新创建之后（调用时间来自 CloudTrail）。控制器重启似乎是触发因素，但日志中未确认。OSS 的默认重新同步间隔为 10 小时（`reconcile.defaultResyncPeriod: 36000`），且可调整；托管式的间隔未公开，无法更改。如果快速恢复很重要，可以通过 SCP 或 IAM 条件阻止带外更改，例如只允许针对带有 `aws:ResourceTag/eks:eks-capability-arn` 标签的资源进行更改，并且调用必须带有匹配的 `aws:PrincipalTag/eks:eks-capability-arn`（未测试）。

### 托管式方案的差异与迁移

- 没有 `FieldExport` CRD。要将状态值导出到 ConfigMap 或 Secret，请采用其他方案，例如使用 kro 将状态写入 ConfigMap。
- 使用 `--configuration '{"ack":{"disabledServices":["sagemaker"]}}'` 禁用服务后，在 CLI 2.38.3 中 12.5 s 后生效，但 350 s 后该服务已安装的 CRD 仍然存在。应在创建时指定未使用的服务（创建时设置未测试）。
- 控制器版本比最新 OSS 版本落后一个版本（s3 为 1.12.2，而 1.13.1；sqs 为 1.7.1，而 1.8.2）。
- 托管 Capability 支持接管（`services.k8s.aws/adoption-policy: adopt-or-create`）和 retain 注释：接管耗时 4.7 s；使用 retain 删除的 Queue 仍保留在 AWS 中（在托管式上测得）。删除 Capability 后，OSS 控制器按原样接管了剩余的 12 个 CR。

<span id="together"></span>

## 6. 三者协同使用

一种自然的职责划分是：Argo CD 从 Git 同步清单，kro 将多个资源组合成一个 API，ACK 则创建其中的 AWS 资源。经过测试的 `OrderService` RGD 创建了一个 ACK Queue 和一个 Table，将它们的状态值（Queue URL、Table ARN）复制到 ConfigMap，并启动了一个 Deployment。

| 组合 | 结果 | 需要的额外配置 |
|---|---|---|
| Argo CD → ACK Queue | Git 中的 Queue CR 在 6.5 s 内同步成功 | 在 Argo CD Capability 角色上为 `queues.sqs.services.k8s.aws` 配置 RBAC |
| kro → ACK Queue 和 Table + ConfigMap + Deployment | 实例在 13.2–34.3 s 内变为 `ACTIVE`（耗时主要用于创建 DynamoDB Table） | 在 kro Capability 角色上为 ACK 资源配置 RBAC；在 ACK 侧配置 IAMRoleSelector |

默认 EKS 访问策略（例如 `AmazonEKSEditPolicy`）不涵盖 ACK CRD，因此无论由 Argo CD 还是 kro 创建 ACK 资源，相应组件都需要这些 API 组的权限。两项测量分别进行；未端到端运行完整的三步链路。

<span id="upgrade"></span>

## 7. 集群升级与 Capability 版本

### 原地升级期间的行为

将包含全部三个 Capability 的集群从 1.36 原地升级到 1.37。控制平面升级耗时约 7 分钟，三个 Capability 均保持 `ACTIVE`，版本、健康状态和 `modifiedAt` 均未改变。

| 阶段 | Argo CD 自愈 | kro 传播 | ACK Queue 同步 |
|---|---|---|---|
| 升级前（3 次运行） | 2.1–14.6 s | 1.02–1.04 s | 1.49–3.53 s |
| 升级期间（4 次运行） | 2.1 s、6.1 s、112.9 s、254.5 s | 1.02–1.07 s | 1.52–1.58 s |
| 升级后（5 次运行） | 2.3 s，随后为 251–252 s | 1.01–1.15 s | 1.47–1.57 s |

对于 kro 和 ACK，四次“升级期间”运行中有一次是在升级刚完成后测得的。升级期间出现的自愈延迟，在升级后也以相同情况重现，因此它是上文所述自愈退避机制造成的，而非升级所致。在 API Server 版本约 3 分钟交替处于 1.36.4 和 1.37.0 期间，未测量 kro 和 ACK。节点组未升级。

原地升级无需针对 Capability 执行特定步骤。对于自托管控制器，必须检查其是否支持新的 Kubernetes 版本，必要时先升级控制器；托管模式则将此兼容性检查交由 AWS 处理。请注意，EKS 升级洞察中的检查项均未涵盖 Capability。

### 无法选择版本

`create-capability` 和 `update-capability` 都没有版本参数，AWS 文档只提到“自动更新和安全补丁”。在文档中找不到有关 Capability 版本更新计划、提前通知、维护时段、各版本发行说明或回滚路径的信息。2026年7月新增的[集群版本回滚](./08-eks-upgrades.md)可以回滚 Kubernetes 次要版本，但回滚文档未涉及 Capability。由于 Capability 没有版本参数，不要将其视为回滚 Capability 版本的手段（推断）。测试中，10月21日创建的 Argo CD Capability 报告版本为 `3.4.6-eks-2`，而另一个集群在次日创建的 Capability 报告版本为 `3.4.7-eks-1`。控制器版本可能独立于集群升级而变化。

请按以下方式为有问题的版本做好准备。

| 准备事项 | 做法 | 依据 |
|---|---|---|
| 记录版本变化 | 轮询 `describe-capability` 中的 `capability.version`，并与事件关联 | 已测量（已确认字段） |
| 验证集群 | 先在具有相同 Capability 的集群上运行生产 RGD、Application 和 ACK CR。无法控制推出顺序，因此不能保证验证集群一定先于生产环境更新 | 推断 |
| 在 Git 中固定行为 | 将健康检查（`resource.customizations`）、同步选项和 RBAC 保存在 Git 中，以便重建或迁移时能够复现相同行为 | 已测量（设置已应用） |
| AWS Support | 用户无法自行回滚，因此需要提交支持案例。AWS 文档建议通过 Support 调整自愈时序 | 推断（自愈时序根据文档） |
| 临时回退到自托管方案 | 使用 RETAIN 删除 Capability 会保留 CRD 和资源，使用相同 CRD 的 OSS 控制器会接管（已针对 kro、ACK 和 Argo CD 测量）。Argo CD 需要将集群 Secret 的 `server` 从 EKS ARN 改为 API URL（本地使用 `https://kubernetes.default.svc`）；通过 ARN 注册的远程或私有 spoke 则需要在 OSS 方案下自行配置网络路径和身份验证。返回托管式方案需要重新创建 Capability（Argo CD 约 6 分钟） | 已测量 |
| 按服务回滚 ACK | 只将受影响的服务添加到 `disabledServices`，并安装或扩容其自托管控制器。OSS 控制器需要自行配置 IAM；使用 IAMRoleSelector 时，还需设置 `featureGates.IAMRoleSelector=true` 和 `enableCARM=false`。未测试在 Capability 安装的 CRD 上运行 OSS Chart 的情况。已安装的 CRD 会保留（已测量） | 根据文档 |

如果你明确需要固定版本，AWS 文档本身也建议采用自托管方案（“需要特定 Kubernetes 资源 API 版本、自定义控制器构建版本”）。

<span id="multicluster"></span>

## 8. 多集群与蓝绿替换

### Argo CD hub 与私有 spoke

hub 集群上的 Argo CD Capability 注册了同一账户和 VPC 中的 spoke 集群。该 spoke 仅启用私有 API 端点，且未配置网络（端点、安全组、路由）。位于另一个 VPC 的工作站无法访问该 spoke，因此该连接显然使用了 AWS 提供的路径。必须手动为 hub 的 Capability 角色在 spoke 上创建访问条目。

| Spoke 访问条目权限 | 结果 |
|---|---|
| `AmazonEKSEditPolicy` + `AmazonEKSAdminViewPolicy` | 连接和身份验证成功，但 `CreateNamespace=true` 失败，报错 `namespaces is forbidden`；五次自动重试（约 303 s）均已用尽 |
| + `AmazonEKSArgoCDClusterPolicy`，然后手动同步 | 在 11.1 s 内同步成功并处于 Healthy 状态 |

- 集群 Secret 只接受 EKS ARN，因此非 EKS 集群无法作为目标（根据文档）。
- Application 费用按每个目标集群中的 Application 数量计算，因此 hub 部署与每个集群分别部署的费用相同；只有 Argo CD 实例数量增加时，Capability 费用才会增加。不过，hub 的 Capability 角色对每个 spoke 都具有写入权限，因此应考虑限制 AppProject 目标集群，或按团队拆分 Capability。
- 根据文档，其他账户中的集群只需要为 hub Capability 角色创建访问条目（未测试）。托管式限制为 100 个远程集群和 3,000 个 Application。

### kro 和 ACK 的部署位置

kro 和 ACK Capability 只管理各自所在的集群。若 hub 上的 Argo CD 要向 spoke 部署 RGD 实例或 ACK CR，则 spoke 也需要 kro 或 ACK（托管式或 OSS 均可）。

| 布局 | 适用场景 | 注意事项 |
|---|---|---|
| 每个集群都运行 kro，通过 ApplicationSet 推出 RGD | 应用团队在每个集群上使用相同 API | Capability 费用和 RBAC 工作量会随集群数量增加；文档不保证不同集群上的 kro 版本完全相同（未测试） |
| 只在 hub 上运行 kro，由 RGD 为 spoke 创建 ACK 资源和 Argo CD Application | 在一个位置定义平台抽象 | 权限和影响范围集中在 hub；spoke 应用团队无法直接使用 kro API（未测试） |
| 集中式 ACK（hub） | 平台拥有的资源，例如数据库、IAM、VPC | hub Capability 角色拥有对所有账户和资源的权限 |
| 分布式 ACK（每个集群各自运行） | 在工作负载旁声明 Queue 和 Bucket | IAMRoleSelector 配置工作量会随集群数量增加 |
| 混合式 ACK | 在 hub 上管理管理员范围的资源，在 spoke 上管理工作负载范围的资源 | 需要范围规则，以免同一资源在两个位置声明 |

无论采用哪种布局，都应设置范围规则，确保没有两个集群同时声明同一个 AWS 资源。

### 蓝绿替换

- **Argo CD**：Capability 属于所在集群，因此替换承载 Argo CD 的集群时，必须重新创建 Capability。默认地址 `argocd-<ID>-<account ID>.eks-capabilities.<region>.amazonaws.com` 会因集群而异，因此 UI 和 webhook URL 也会改变。在创建时设置 `endpointPrefix` 后，删除并使用相同前缀重新创建可以保留地址（只在同一集群上测试）。该地址不包含集群专属信息，因此迁移到另一个集群后也应该能够使用。如果前缀在账户和区域内必须唯一（未测试），旧集群和新集群就无法同时使用该前缀；替换过程将变成先删除再重新创建，期间 UI、webhook 和同步都会停止（实测删除 100 s，重新创建 338 s）。如果无法接受这样的暂停，应先使用新前缀创建新 Capability 并更改 Git webhook URL；在启用新 Capability 之前，禁用旧 Capability 的自动同步，或以非级联方式删除其 Application，并预先在目标集群中创建新 Capability 角色的访问条目（未测试）。创建后无法更改前缀。请将 Argo CD 部署在专用 hub 上，而不是经常替换的工作负载集群上。
- **kro**：ClusterRole 和绑定可通过 Git 迁移，但向访问条目添加 Kubernetes 组需要调用 EKS API。请将其纳入创建集群的 IaC（eksctl、Terraform 等）。
- **ACK**：一种可行的顺序是使用 `deletion-policy: retain` 删除旧集群中的 CR，然后在新集群上使用 `adoption-policy: adopt-or-create` 接管相同资源（两个步骤分别测量过；未测试完整的跨集群流程）。如果 SCP 根据 `eks:eks-capability-arn` 标签阻止更改，新 Capability 的 ARN 会不同，接管操作可能被阻止；切换期间应放宽条件，或改为根据环境或团队标签设置条件。

<span id="compare"></span>

## 9. 与自托管方案的比较及选择建议

| 项目 | 托管 Capability | 自托管（OSS） |
|---|---|---|
| 安装时间 | Argo CD 349 s，kro 70 s，ACK 386 s | Argo CD 43.4 s，kro 15.6 s，三个 ACK 控制器 46 s |
| 节点资源 | 无 | Argo CD 7 个 Pod（339–624Mi 内存），kro 1 个 Pod（requests 为 256m、128Mi），ACK 3 个 Pod（每个 requests 为 50m、64Mi） |
| 版本 | 由 AWS 选择，无法固定 | 自行选择（测试时最新版本为 Argo CD v3.5.5 和 ACK s3 1.13.1） |
| 默认权限 | 范围较窄；需自行授予部署、子资源和 IAM 权限 | Argo CD 和 kro Chart 的默认权限为 `*/*/*` |
| 性能 | kro、ACK 和 Argo CD 自愈表现与 OSS 相当；Argo CD 默认轮询较慢 | 基准方案（Argo CD 3.4.6 和 kro 0.9.4 在相同版本下测量；ACK OSS 使用了更新一个版本的控制器） |
| SSO | 仅支持 Identity Center，两个配置字段 | Dex、OIDC 等，需自行配置 |
| 远程集群 | EKS ARN + 访问条目；私有集群无需配置网络 | 每个集群都需要配置 API URL、身份验证和网络路径 |
| 缺失功能 | CMP、`argocd admin`、Lua 标准库；ACK FieldExport（Argo CD Notifications 于2026年11月推出） | 无 |
| 无法直接调整 | Argo CD 轮询、ACK 重新同步间隔、控制器标志和资源限制；Argo CD 自愈退避只能通过 AWS Support 调整 | 均可调整 |
| 日志 | Vended Logs | `kubectl logs`，自行收集 |

适合使用托管式方案的情况：

- 你正在构建一个向多个 EKS 集群部署的 hub，尤其是私有集群或其他账户中的集群
- 你的 AWS 登录已经集中在 Identity Center 中，并且不想自行运维 Argo CD SSO
- 你通过 Kubernetes 管理多个 AWS 服务，逐个运行 ACK 控制器负担过重，而且需要按团队进行 IAM 隔离
- 你希望平台控制器默认采用范围较窄的权限，并在访问条目和 RBAC 中明确配置

适合继续使用自托管方案的情况：

- 你依赖 CMP、FieldExport 或 Lua 标准库
- 部署目标中包含非 EKS 集群
- 只有 Argo CD 需要使用不同于组织 Identity Center 的 IdP，而且无法使用账户实例
- 你必须自行控制控制器版本、升级时序以及轮询或重新同步间隔

在集群数量还未超过一个之前进行评估是个好时机：hub 位置、Identity Center 实例和 `endpointPrefix` 都是创建后固定或难以更改的。另一个适合评估的时机是自托管 Argo CD 需要重建 HA 配置或进行重大升级时。AWS 迁移流程会先将现有控制器缩容至零，再迁移 Application 和 Secret，并将 `destination.server` 改为 ARN；期间同步会停止（未测试）。

<span id="pricing"></span>

## 10. 定价

价格适用于首尔（ap-northeast-2），通过 AWS Pricing API 于2026年10月21日查询，按每月 730 小时计算。

| Capability | Capability 费用 | 每对象费用 | 示例（月费用） |
|---|---|---|---|
| Argo CD | $0.034799 每小时（约 $25.4/月） | $0.001726 每 Application 小时（按目标集群计数） | 9 个应用约 $36.7，100 个应用约 $151 |
| kro | $0.006038 每小时（约 $4.4/月） | $0.000061 每实例小时 | 100 个实例约 $8.9 |
| ACK | $0.006038 每小时（约 $4.4/月） | $0.000061 每资源小时 | 200 个资源约 $13.3 |

作为比较，按比例分摊 m7g.large 的费用（首尔为每小时 $0.1003）到默认自托管安装上，Argo CD（624Mi 内存）约为 $5.6，kro（256m CPU request）约为 $9.4，三个 ACK 控制器（150m CPU request）约为 $5.5。HA 配置以及更多应用或服务也会增加 OSS 方案的费用。托管式 Argo CD 的费用会随应用数量增加；kro 和 ACK 的差异较小，因此主要取决于运维负担和功能缺口。

<span id="refs"></span>

## 11. 验证范围与参考资料

测量使用了 ap-northeast-2 中的单一账户：一个 EKS 1.36.4 集群，以及用于升级和多集群测试的另外两个集群（hub 从 1.36 升级到 1.37，私有 spoke 为 1.37）。每种场景运行 1–5 次，最多包含 9 个 Argo CD Application、6 个 kro 实例和约 20 个 ACK 资源。ACK 只针对 S3、SQS 和 DynamoDB 进行了测试。以下内容未测试，依据文档说明：Okta 或 Entra ID 集成以及 Identity Center 账户实例、通过 VPC 端点进行私有访问、注册其他账户或 VPC 中的集群、Notifications 和 CMP、跨账户 ACK、托管式与 OSS 同时运行时的零停机迁移，以及完整的跨集群 ACK retain 后接管流程。测量完成后，测试集群和 AWS 资源均已删除。

- [EKS Capabilities](https://docs.aws.amazon.com/eks/latest/userguide/capabilities.html)
- [EKS Capabilities 注意事项](https://docs.aws.amazon.com/eks/latest/userguide/capabilities-considerations.html)
- [Capability Kubernetes 资源](https://docs.aws.amazon.com/eks/latest/userguide/capability-kubernetes-resources.html)
- [Argo CD 注意事项](https://docs.aws.amazon.com/eks/latest/userguide/argocd-considerations.html)
- [比较 EKS Argo CD Capability 与自托管 Argo CD](https://docs.aws.amazon.com/eks/latest/userguide/argocd-comparison.html)
- [注册目标集群](https://docs.aws.amazon.com/eks/latest/userguide/argocd-register-clusters.html)
- [配置 Argo CD 设置](https://docs.aws.amazon.com/eks/latest/userguide/argocd-configure-settings.html)
- [配置 kro 权限](https://docs.aws.amazon.com/eks/latest/userguide/kro-permissions.html)
- [比较 EKS kro Capability 与自托管 kro](https://docs.aws.amazon.com/eks/latest/userguide/kro-comparison.html)
- [配置 ACK 权限](https://docs.aws.amazon.com/eks/latest/userguide/ack-permissions.html)
- [比较 EKS ACK Capability 与自托管 ACK](https://docs.aws.amazon.com/eks/latest/userguide/ack-comparison.html)
- [访问 EKS Capabilities 控制器日志](https://docs.aws.amazon.com/eks/latest/userguide/capabilities-controller-logs.html)
- [将集群回滚到之前的 Kubernetes 版本](https://docs.aws.amazon.com/eks/latest/userguide/rollback-cluster.html)
- [Amazon EKS 定价](https://aws.amazon.com/eks/pricing/)
- 测量博客（韩语）：[托管式 Argo CD](https://blog.atomai.click/eks-capabilities-argocd/)、[托管式 kro](https://blog.atomai.click/eks-capabilities-kro/)、[托管式 ACK](https://blog.atomai.click/eks-capabilities-ack/)
- 测试清单：[Atom-oh/eks-capabilities-demo](https://github.com/Atom-oh/eks-capabilities-demo)

[EKS Capabilities 测验](../quizzes/eks/13-eks-capabilities-quiz.md)
