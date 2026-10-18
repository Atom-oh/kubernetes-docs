# GitOps 自动化：Atlantis、HCP Terraform、Flux、AIOps

> **审查基准**：Atlantis 0.48.1 / chart 6.16.1、HCP Terraform Provider 0.80.0、Sentinel 0.41.0、Flux 2.9.6（在 2.9.5 上验证；仅更新补丁版本锁定，未重新运行）\
> **最后审查时间**：October 16, 2026。已使用本地 CLI、charts、schemas 和测试替身进行检查。未实际执行 PR 评论、Terraform apply、HCP 资源创建、集群部署或外部 AI 调用。

< [上一章：多集群](04-gitops-multi-cluster.md) | [目录](README.md) | [下一章：扩展策略](06-scaling-strategies.md) >

将基础设施执行与应用协调分开。不要让 Atlantis 和 HCP Terraform 同时针对同一状态执行，也不要让 Flux 和 Argo CD 争相管理同一批 Kubernetes 字段。

| 工具 | 职责 | 独立的前置条件 |
|---|---|---|
| Atlantis | 执行基于 PR 的 Terraform plan/apply | 运行环境、凭证、状态、锁和命令授权 |
| HCP Terraform | 托管 workspace/run/state 和协作 | VCS 连接、agents、策略和 workspace 权限 |
| Flux | 根据源协调 Kubernetes/Helm 状态 | Controller 身份、租户 RBAC 和仓库权限 |
| AIOps 分析 | 汇总观察结果并提出响应建议 | 经过验证的数据、审批和单独受限的执行器 |

## 1. 在 EKS 上运行 Atlantis

Atlantis 从 pull request 执行 Terraform。**Plan 可能会执行 provider、外部数据源和自定义命令**。要求审批 apply 并不能让不可信的 plan 变得安全。本示例适用于受控的私有基础设施仓库和获准的运维团队，并禁用 fork PR 和自动 plan。

### 身份和安装前置条件

- 为命名空间/ServiceAccount `atlantis` 配置 EKS Auto Mode Pod Identity 关联。不要与 IRSA 注解混用。传统节点需要配置受支持的 agent 和 SDK。
- 将访问范围限定为确切的状态和 `.tflock` 对象键、所需的 KMS key 以及托管资源。区分状态对象的读/写权限与锁对象的读/写/删权限。宽泛的 `eks:*`、IAM role 创建权限和 PassRole 并非通用的最小权限策略。
- 将角色代入限制为确切的 ARN 和预期信任关系。对 Pod Identity 使用受支持的集群/命名空间/ServiceAccount 请求标签条件。
- 保护凭证和敏感的 plan JSON，避免其出现在 PR 输出中。Terraform 的 `sensitive=true` 不会阻止值存储在 state 中。

运行环境需要访问 AWS、Git、provider/module registry 和私有 EKS API。不要依赖未经验证的安装脚本或镜像中不存在的工具。`defaultTFVersion` 必须使用 Terraform 1.15.7，或能够通过获准的下载路径获取该版本。

### 版本化 Helm values

如果 `auto-gp3` 尚不存在，请准备如下 Auto Mode StorageClass。它使用的 provisioner 与传统 EBS CSI 不同。在其他集群模式下，请使用合适的替代方案。

```yaml
# fixtures/atlantis-storage.yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: auto-gp3
provisioner: ebs.csi.eks.amazonaws.com
volumeBindingMode: WaitForFirstConsumer
reclaimPolicy: Retain
allowVolumeExpansion: true
parameters:
  type: gp3
  encrypted: "true"
allowedTopologies:
  - matchLabelExpressions:
      - key: eks.amazonaws.com/compute-type
        values: [auto]
```

使用获准的密钥管理机制，在命名空间 `atlantis` 中准备以下 Secret。不要将真实值放入 Git 或 Helm values。

| Secret | 必需的键 |
|---|---|
| `atlantis-vcs` | `github-token`、`webhook-secret` |
| `atlantis-web-auth` | `username`、`password` |

为 GitHub bot/token 配置所需的仓库、PR 和团队查询权限，并定期轮换。将 `platform` 替换为实际获准的组织团队。使用 Atlantis 的团队允许列表，不要在 shell hook 中对用户名做子字符串匹配。

```yaml
# fixtures/atlantis-values.yaml
fullnameOverride: atlantis
replicaCount: 1
image:
  repository: ghcr.io/runatlantis/atlantis
  tag: v0.48.1
orgAllowlist: github.com/REPLACE_ORG/eks-infra
atlantisUrl: https://atlantis.example.com
defaultTFVersion: 1.15.7
allowForkPRs: false
disableApplyAll: true
basicAuthSecretName: atlantis-web-auth
service:
  type: ClusterIP
ingress:
  enabled: false
volumeClaim:
  enabled: true
  dataStorage: 10Gi
  storageClassName: auto-gp3
  accessModes:
  - ReadWriteOnce
serviceAccount:
  create: true
  name: atlantis
  mount: false
  annotations: {}
resources:
  requests:
    cpu: 500m
    memory: 1Gi
  limits:
    cpu: '2'
    memory: 4Gi
containerSecurityContext:
  allowPrivilegeEscalation: false
  capabilities:
    drop:
    - ALL
environment:
  ATLANTIS_GH_USER: REPLACE_BOT_USER
  ATLANTIS_GH_TEAM_ALLOWLIST: platform:plan,platform:apply
  ATLANTIS_DISABLE_AUTOPLAN: 'true'
  ATLANTIS_FAIL_ON_PRE_WORKFLOW_HOOK_ERROR: 'true'
  ATLANTIS_BLOCKED_EXTRA_ARGS: -chdir,--chdir,-plugin-dir,--plugin-dir,-target,--target,-replace,--replace,-out,--out,-var-file,--var-file,-var,--var
environmentSecrets:
- name: ATLANTIS_GH_TOKEN
  secretKeyRef:
    name: atlantis-vcs
    key: github-token
- name: ATLANTIS_GH_WEBHOOK_SECRET
  secretKeyRef:
    name: atlantis-vcs
    key: webhook-secret
repoConfig: |
  repos:
    - id: github.com/REPLACE_ORG/eks-infra
      plan_requirements: [approved]
      apply_requirements: [approved, mergeable, undiverged]
      import_requirements: [approved, mergeable, undiverged]
      workflow: reviewed
      allowed_overrides: []
      allow_custom_workflows: false
      repo_locks:
        mode: on_plan
  workflows:
    reviewed:
      plan:
        steps:
          - init:
              extra_args: [-backend-config=backend.hcl]
          - run: terraform fmt -check -diff
          - run: terraform validate
          - plan:
              extra_args: [-var-file=terraform.tfvars, -lock-timeout=300s]
      apply:
        steps:
          - apply
```

```bash
helm repo add runatlantis https://runatlantis.github.io/helm-charts
helm repo update
helm upgrade --install atlantis runatlantis/atlantis \
  --version 6.16.1 --namespace atlantis --create-namespace \
  --kube-context "$ATLANTIS_CONTEXT" --values atlantis-values.yaml
```

这些 values 只会创建 ClusterIP。通过获准的 HTTPS 代理/Ingress 接入 `atlantis.example.com` 和 `/events`，然后配置匹配的 GitHub webhook secret。Webhook 验证与 Web UI 身份验证是两回事。不要将事件路由扩展为通用的身份验证绕过通道。

Chart 6.16.1 使用 `orgAllowlist`、`volumeClaim`、`environment` 映射和 `containerSecurityContext`。可写 PVC 存放 checkout、plan 和服务器锁数据；不要用只读 ConfigMap 覆盖它。仅增加副本数无法让使用单个 RWO PVC/BoltDB 的部署实现高可用。应管理保留策略、备份、恢复以及保留卷的最终清理。

### 服务器策略和仓库项目

内嵌的 `repoConfig` 由服务器管理。`allowed_overrides: []` 和 `allow_custom_workflows: false` 可防止 PR 更改审批要求或执行命令。请单独配置 GitHub 分支保护和必需检查。`approved` 本身并不意味着最新提交获得了两个不同人员的有效审批。

将 apply 本身设为 `mergeable` 的前置条件可能造成循环依赖。应使 plan/check/review/apply 依赖关系与仓库规则保持一致。本示例使用明确的 `atlantis plan -p ...` 命令；审批后发生变更时，应重新审查并重新 plan。

将此文件放在仓库根目录。每个项目目录使用[第 01 章](01-infrastructure-setup.md)中的对应根目录，并拥有自己的 backend/state，以及经过审查的 `backend.hcl` 和 `terraform.tfvars`。

```yaml
# fixtures/atlantis.yaml
version: 3
automerge: false
parallel_plan: false
parallel_apply: false
projects:
  - name: network-prod
    dir: 01-network
    workspace: default
    terraform_version: v1.15.7
    autoplan:
      enabled: false
      when_modified: ["*.tf", "*.tfvars", "backend.hcl", ".terraform.lock.hcl", "../modules/**/*.tf"]
  - name: cluster-prod
    dir: 02-cluster
    workspace: default
    terraform_version: v1.15.7
    depends_on: [network-prod]
    autoplan:
      enabled: false
      when_modified: ["*.tf", "*.tfvars", "backend.hcl", ".terraform.lock.hcl", "../modules/**/*.tf"]
  - name: platform-prod
    dir: 03-platform
    workspace: default
    terraform_version: v1.15.7
    depends_on: [cluster-prod]
    autoplan:
      enabled: false
      when_modified: ["*.tf", "*.tfvars", "backend.hcl", ".terraform.lock.hcl", "../modules/**/*.tf"]
```

先审查并 apply 网络变更，再 plan/审查/apply集群和平台变更。`depends_on` 不会传递 remote-state 输出，也不会自动刷新之前保存的下游 plan。依赖发生变化时，应重新 plan 下游变更。

```text
atlantis plan -p network-prod
atlantis apply -p network-prod
atlantis plan -p cluster-prod
atlantis apply -p cluster-prod
atlantis plan -p platform-prod
atlantis apply -p platform-prod
```

这些是 PR 评论命令。常规 Atlantis 流程是 **在 PR 中 plan → 满足审批要求 → apply 已保存的 plan → merge**。仅 merge 不会 apply 基础设施。`automerge` 是一个独立选项，可在 apply 成功后 merge。

内置的 `plan`/`apply` 阶段使用 Atlantis 管理的 plan 文件。自定义命令必须遵循 `$PLANFILE`。不要用单独的 `-out=tfplan` 替换它，也不要在 apply 已保存的 plan 时传入新的 `-var-file` 值。Plan 文件和 JSON 可能包含敏感数据。

### 锁、策略和故障处理

Atlantis PR/project/workspace 锁不同于 Terraform backend state 锁。当前默认服务器数据库是 BoltDB；受支持的 Redis 配置需要单独设计。不要将 DynamoDB 称为 Atlantis 的默认锁数据库，也不要虚构 `lock_groups`/`apply_priority` ConfigMaps。

`atlantis unlock` **会移除**锁，并非查询命令。先检查正在运行的任务、已保存的 plan 和 state 锁。在本示例使用的版本中，`atlantis lock`、`atlantis locks` 和 `unlock --force` 不是通用 PR 命令。请使用受支持的 UI 或经过身份验证的 API 检查锁。

在源代码中搜索并统计当前 state 中的资源，并不能验证所有计划中的基础设施。还要考虑 modules、data sources、providers，以及 create/update/delete/unknown 值。将失败的 fmt/validate/policy/API 操作转为警告或使用 `|| true`，会移除这道门禁。

## 2. HCP Terraform

Terraform Cloud 现在名为 **HCP Terraform**。它是 Atlantis 的替代方案，具备 workspace/run/state/policy 功能。请查看当前套餐和合同，了解功能、定价、并发、agents 和 Sentinel。托管服务仍需谨慎配置 VCS、权限、网络和审批。

### Workspace 和动态 AWS 凭证

本示例假设已存在组织/项目、VCS OAuth 连接，以及可访问私有网络的 **agent pool**。Agent 执行需要符合条件的套餐和受支持的 agent 版本。不要假设公共远程 runner 能直接访问私有 EKS API。

```hcl
# tfe/main.tf
terraform {
  required_version = ">= 1.10, < 2.0"
  required_providers {
    tfe = {
      source  = "hashicorp/tfe"
      version = "= 0.80.0"
    }
  }
}

# Supply a scoped TFE_TOKEN through the approved secret mechanism, not in Git.
provider "tfe" {
  hostname = "app.terraform.io"
}

locals {
  layers = {
    network  = "01-network"
    cluster  = "02-cluster"
    platform = "03-platform"
  }
  environment_variables = merge([
    for layer, directory in local.layers : {
      for key, value in {
        TFC_AWS_PROVIDER_AUTH  = "true"
        TFC_AWS_PLAN_ROLE_ARN  = var.workspace_roles[layer].plan
        TFC_AWS_APPLY_ROLE_ARN = var.workspace_roles[layer].apply
        AWS_REGION             = var.aws_region
      } : "${layer}:${key}" => { layer = layer, key = key, value = value }
    }
  ]...)
}

resource "tfe_workspace" "layer" {
  for_each               = local.layers
  name                   = "${each.key}-prod"
  organization           = var.organization
  project_id             = var.project_id
  terraform_version      = "1.15.7"
  working_directory      = each.value
  auto_apply             = false
  auto_apply_run_trigger = false
  queue_all_runs         = false
  tag_names              = ["production", each.key]
  vcs_repo {
    identifier     = var.repository
    branch         = "main"
    oauth_token_id = var.vcs_connection_id
  }
}

resource "tfe_workspace_settings" "layer" {
  for_each                  = local.layers
  workspace_id              = tfe_workspace.layer[each.key].id
  execution_mode            = "agent"
  agent_pool_id             = var.agent_pool_id
  global_remote_state       = false
  project_remote_state      = false
  remote_state_consumer_ids = []
}

resource "tfe_variable" "aws" {
  for_each     = local.environment_variables
  workspace_id = tfe_workspace.layer[each.value.layer].id
  category     = "env"
  key          = each.value.key
  value        = each.value.value
}

resource "tfe_run_trigger" "cluster_after_network" {
  workspace_id  = tfe_workspace.layer["cluster"].id
  sourceable_id = tfe_workspace.layer["network"].id
}

resource "tfe_run_trigger" "platform_after_cluster" {
  workspace_id  = tfe_workspace.layer["platform"].id
  sourceable_id = tfe_workspace.layer["cluster"].id
}
```

```hcl
# tfe/variables.tf
variable "organization" {
  type = string
}
variable "project_id" {
  type = string
}
variable "agent_pool_id" {
  type = string
}
variable "repository" {
  type = string
}
variable "vcs_connection_id" {
  type = string
}
variable "aws_region" {
  type    = string
  default = "ap-northeast-2"
}
variable "workspace_roles" {
  type = map(object({
    plan  = string
    apply = string
  }))
  validation {
    condition = alltrue([
      for layer in ["network", "cluster", "platform"] :
      can(regex("^arn:aws:iam::[0-9]{12}:role/.+$", var.workspace_roles[layer].plan)) &&
      can(regex("^arn:aws:iam::[0-9]{12}:role/.+$", var.workspace_roles[layer].apply))
    ])
    error_message = "Supply existing scoped plan/apply role ARNs for every layer."
  }
}
```

此根配置用于管理 HCP 资源。应单独保护其 backend/state。在将 HCP 托管 state 用于现有根目录之前，应明确所有权，并谨慎迁移原有的 S3 backend。不要让两个执行系统操作同一份 state。

AWS 必须已配置 `app.terraform.io` OIDC provider 和范围受限的 plan/apply 角色。将信任关系的 audience/subject 限定为确切的组织/项目/workspace 以及 `run_phase:plan` 或 `run_phase:apply`。`TFC_AWS_*` 变量是角色标识符，不是存储的长期访问密钥。请在实际使用的 provider 和 agent 版本中验证动态凭证支持情况。

`queue_all_runs=false` 会在 workspace 初始设置期间暂存 VCS 触发的 run。第一次手动运行后，它不是永久禁用执行的开关。

### Run trigger 和输出共享

上游 apply 成功后会将下游 run 加入队列。**`auto_apply_run_trigger` 与普通的 `auto_apply` 相互独立。此处两者都设为** false，因此 apply 前需要审查。Trigger 既不能证明所有依赖均已就绪，也不是输出传递机制。

本示例不会全局共享 workspace state。如果必须使用输出，请配置获准的消费者/权限，并考虑使用 `tfe_outputs`。能够读取 `terraform_remote_state` 的凭证可以访问完整的敏感 state，而不只是数据源显示的输出。应根据实际设计配置输出访问和 module 输入。

### Sentinel 策略

以下是使用 Sentinel 0.41.0 测试过的三个**策略示例**，不是 Python 程序。必须先配置策略集、目标 workspace 和强制执行设置，策略才能阻止 HCP run。

```text
# policies/required-tags.sentinel
import "tfplan/v2" as tfplan

required_tags = ["Environment", "Team", "CostCenter"]
taggable_types = ["aws_instance", "aws_vpc", "aws_subnet",
                 "aws_security_group", "aws_eks_cluster", "aws_eks_node_group"]

changes = filter tfplan.resource_changes as _, rc {
  rc.mode is "managed" and rc.type in taggable_types and
  (rc.change.actions contains "create" or rc.change.actions contains "update")
}

valid_tag = func(tags, key) {
  value = tags[key] else null
  return value is not null and value is not ""
}

has_required_tags = func(rc) {
  tags = rc.change.after.tags_all else {}
  unknown = rc.change.after_unknown.tags_all else false
  if tags is null or unknown is true {
    return false
  }
  if unknown is false or unknown is null {
    unknown = {}
  }
  return all required_tags as tag {
    not (unknown[tag] else false) and valid_tag(tags, tag)
  }
}

main = rule {
  all changes as _, rc { has_required_tags(rc) }
}
```

检查 `tags_all` 会包含 AWS Provider 的默认标签。此示例针对列出的资源类型检查 create/update 操作，不包括删除操作。缺失、空、null 或未知的必需标签都不能通过检查。它并未覆盖所有 AWS 资源类型。

```text
# policies/instance-types.sentinel
import "tfplan/v2" as tfplan

# Organization policy example; use a reviewed allowlist for the actual region.
allowed = ["m7i.large", "m7i.xlarge", "m7g.large", "m7g.xlarge"]
changes = filter tfplan.resource_changes as _, rc {
  rc.mode is "managed" and
  rc.type in ["aws_instance", "aws_eks_node_group"] and
  (rc.change.actions contains "create" or rc.change.actions contains "update")
}

approved_types = func(rc) {
  if rc.type is "aws_instance" {
    return (rc.change.after.instance_type else "") in allowed and
           not (rc.change.after_unknown.instance_type else false)
  }
  types = rc.change.after.instance_types else []
  return length(types) > 0 and
         not (rc.change.after_unknown.instance_types else false) and
         all types as instance_type { instance_type in allowed }
}

main = rule {
  all changes as _, rc { approved_types(rc) }
}
```

此策略适用于 EC2 实例以及直接指定 `instance_types` 的托管节点组。仅使用 launch template 的节点组、Auto Mode NodePools 和其他计算服务需要额外策略。空或未知的类型列表不会被视为已批准的空集合。

```text
# policies/cost-limit.sentinel
import "tfrun"
import "decimal"

# This checks HCP's available estimate, not the complete future AWS bill.
param monthly_limit default "5000"
estimate = tfrun.cost_estimate.proposed_monthly_cost else null

main = rule {
  estimate is not null and
  decimal.new(estimate).greater_than_or_equals(0) and
  decimal.new(estimate).less_than_or_equals(monthly_limit)
}
```

请使用 `tfrun.cost_estimate`，而不是 `tfplan.workspace` 这类不存在的路径。此示例允许提供的月度估算不超过 5,000，并拒绝缺失、负数、NaN 和无限值。它无法保证 AWS 总账单被完整限制，因为某些资源、流量和现有基础设施可能未被计入。

```hcl
# policies/sentinel.hcl
policy "required-tags" {
  source            = "./required-tags.sentinel"
  enforcement_level = "hard-mandatory"
}
policy "instance-types" {
  source            = "./instance-types.sentinel"
  enforcement_level = "hard-mandatory"
}
policy "cost-limit" {
  source            = "./cost-limit.sentinel"
  enforcement_level = "hard-mandatory"
}
```

将策略集关联到预期的 workspace，并将策略管理与资源操作分开。仅将规则命名为 `soft_main` 不会将强制级别改为 soft-mandatory。不要把评估失败或 API 错误转为成功。

## 3. Flux

本节使用 [Flux 2.9.6 指南](../gitops/02-fluxcd.md)。Argo CD 和 Flux 都会协调声明式状态。Argo CD 也有多个组件；Flux 并非在所有情况下都更轻量或隔离性更强。仅分离命名空间并不能完成租户授权。

Image reflector 和 automation controller 是**可选组件**。Bootstrap 会向 Git 提交内容并安装 controller。运行前请验证 CLI checksum、受支持的 Kubernetes 版本、kubecontext 和仓库访问权限。

```bash
flux check --pre
flux bootstrap github \
  --owner=REPLACE_ORG --repository=fleet-infra --branch=main \
  --path=clusters/production --version=v2.9.6 \
  --components-extra=image-reflector-controller,image-automation-controller
```

请安全地提供获准的 GitHub 凭证。组织示例中不要添加 `--personal`。请区分 bootstrap 默认生成的 `flux-system` 文件与你自行添加的基础设施/应用目录。

### Image 自动化和 Git 审批

此示例需要预先准备 Git 写入 Secret、通过 Pod Identity/IRSA 为 image-reflector-controller 配置 ECR 读取凭证，以及用于部署应用的 Flux Kustomization/HelmRelease。这些配置与节点的 image-pull 角色彼此独立。不要随意将 `provider: aws` 与另一种 registry-secret 身份验证路径组合使用。

```yaml
# fixtures/flux-images.yaml
apiVersion: source.toolkit.fluxcd.io/v1
kind: GitRepository
metadata:
  name: applications
  namespace: flux-system
spec:
  interval: 1m
  url: https://github.com/REPLACE_ORG/app-manifests.git
  ref:
    branch: main
  secretRef:
    name: applications-git-auth
---
apiVersion: image.toolkit.fluxcd.io/v1
kind: ImageRepository
metadata:
  name: application
  namespace: flux-system
spec:
  image: REPLACE_ACCOUNT.dkr.ecr.ap-northeast-2.amazonaws.com/docs-ci/application
  interval: 5m
  provider: aws
---
apiVersion: image.toolkit.fluxcd.io/v1
kind: ImagePolicy
metadata:
  name: application
  namespace: flux-system
  labels:
    app: application
spec:
  imageRepositoryRef:
    name: application
  policy:
    semver:
      range: ">=1.0.0 <2.0.0"
  digestReflectionPolicy: IfNotPresent
---
apiVersion: image.toolkit.fluxcd.io/v1
kind: ImageUpdateAutomation
metadata:
  name: application
  namespace: flux-system
spec:
  interval: 30m
  sourceRef:
    kind: GitRepository
    name: applications
  git:
    checkout:
      ref:
        branch: main
    commit:
      author:
        name: Flux automation
        email: flux@example.com
      messageTemplate: |
        Update approved application image
        {{ range .Changed.Changes -}}
        {{ .OldValue }} -> {{ .NewValue }}
        {{ end -}}
    push:
      branch: flux/image-updates
  update:
    path: ./apps/production
    strategy: Setters
  policySelector:
    matchLabels:
      app: application
```

此策略假设使用的是**审批通过后发布的不可变 semver 版本**。[CI 章节](03-ci-pipelines.md)中的唯一 SHA/build 标签与之不匹配。必须由单独的晋级流程将获批的 index digest 标记为 release，或者让策略采用经过审查的、由单一 CI 系统生成的单调递增 build 方案。

```yaml
# fixtures/flux-values.yaml
# apps/production/application/values.yaml -- actual Helm values file
# Replace repository and initial digest with the already approved application.
image:
  repository: REPLACE_ACCOUNT.dkr.ecr.ap-northeast-2.amazonaws.com/docs-ci/application # {"$imagepolicy": "flux-system:application:name"}
  tag: "1.0.0" # {"$imagepolicy": "flux-system:application:tag"}
  digest: sha256:REPLACE_APPROVED_DIGEST # {"$imagepolicy": "flux-system:application:digest"}
```

实际应用 chart 必须在构造容器镜像 URI 时使用 `image.repository`、`tag` 和 `digest`。仅添加 digest 值并不会让现有 chart 自动使用它。请检查渲染后的 manifest 是否指向获批的 digest。确保 Setters 路径、策略标记和 GitRepository 名称彼此一致。

当前 ImageUpdateAutomation 提交模板使用 **`.Changed`**。不要将它替换成已移除的 `.Updated`。自动化会推送到专用的 `flux/image-updates` 分支；创建 PR 并将更改审批后合入 main 需要另一个工作流。请确保 Git 写入权限和分支保护设置一致。标签选择不能替代漏洞/签名验证。

### Source、Helm 和通知

- 当前示例使用 v1 `GitRepository`、`OCIRepository`、`Bucket` 和 image API。HelmRelease 为 v2；其当前 CRD 同时支持 `test.enable` 和 `test.timeout`。请一并验证 chart 版本/values 和 CRD。
- Kustomization `dependsOn` 会等待所引用 Flux 对象的 Ready 状态。配置 wait/healthChecks 以观察工作负载健康状况；它不是全局的跨集群屏障。
- 不要让 Terraform Helm Provider 和 Flux 同时管理同一个 Helm release。迁移 Argo CD 安装的所有权需要谨慎迁移 state/configuration。
- 不要将 Terraform state bucket 暴露为普通 Flux manifest source。应使用独立的 manifest-artifact bucket，并限制其前缀访问；避免在 artifact 中包含 `.git` 的 ignore pattern。
- 将通知 webhook 存储在 Secret 中，并验证实际接收器类型和身份验证方式。测试按严重性和过滤器选定的事件。不要将未安装的 UI 或已停用的集成描述为默认安装的一部分。

[Flux 指南](../gitops/02-fluxcd.md)包含完整的 source/Kustomization/HelmRelease/notification 示例。

## 4. AIOps：从观察到可审查的提案

### 使用 LLM 辅助 PR 审查

通过 GitHub Copilot 支持的 reviewer/automatic-review 设置配置代码审查，并确保具备所需的仓库权限和可用套餐。虚构的 `api.copilot.example.com` 不是可执行的 API 示例。

自定义 LLM 集成必须遵循实际服务当前的 API/model/SDK 合约，并实现超时处理、HTTP 错误处理和输出验证。Diff 和文件名都是不可信数据。应传递结构化值，而不是将其插入 shell、JavaScript 或 JSON 字符串中。被审查内容中的指令不会赋予执行权限。

明确说明内容截断和 API 故障。不要向外部 fork PR 暴露密钥，也不要仅凭模型响应就批准、合并或 apply。使用外部服务前，应明确允许披露的源代码范围和成本范围。审查本文档期间未调用任何外部 AI 服务。

### 指标单位和数据质量

CPU counter 的平均值不是 CPU 利用率。`rate(container_cpu_usage_seconds_total[...])` 得到的是 CPU 核数；HPA 的 `averageUtilization` 是相对于 **CPU requests** 的百分比。不要将该百分比与 RPS 比较。应解析 HPA 的 scaleTargetRef 和实际 Pod 所属关系，而不是假设 HPA 和 Deployment 名称相同。

RPS 的时间序列 p95 与请求时长直方图分位数不同：

```promql
# Seven-day p95 of RPS: counter -> rate -> temporal quantile
quantile_over_time(0.95,
  (sum(rate(http_requests_total{namespace="production",service="myapp"}[5m])))[7d:5m]
)

# Request-duration p95 from a classic histogram, in seconds
histogram_quantile(0.95,
  sum by (le) (rate(http_request_duration_seconds_bucket{
    namespace="production",service="myapp"
  }[5m]))
)
```

请将指标名称/标签与实际采集的数据对应起来。指标序列缺失、流量为零、NaN、过期观察值和采集间断都不能证明系统健康。应综合考虑流量、错误、延迟和容量。仅凭 CPU 平均值无法确定“最优 HPA 目标”；负载测试、SLO 和缩容行为也很重要。

### 可执行的纯分析示例

此工具从标准输入读取已规范化的单指标 JSON 序列，并仅输出**供参考的报告**。它不会更改 API、HPA、NLB、Git 或 Slack。数值在基线范围内并不能证明应用健康。

```python
# fixtures/anomaly-report.py
#!/usr/bin/env python3
"""Read an already normalized metric series; emit an advisory report only."""
import argparse
import json
import math
import statistics
import sys
import time


def number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def assess(data, now):
    if not number(now):
        return {"status": "invalid_data", "reason": "Invalid observation clock"}
    if not isinstance(data, dict):
        return {"status": "invalid_data", "reason": "Expected an object"}
    if data.get("unit") not in {"requests_per_second", "seconds", "ratio"}:
        return {"status": "invalid_data", "reason": "Declare one supported normalized unit"}
    period = data.get("periodSeconds")
    points = data.get("points")
    if not number(period) or period <= 0 or not isinstance(points, list):
        return {"status": "invalid_data", "reason": "Invalid period or series"}
    if len(points) < 31:
        return {"status": "insufficient_data", "reason": "Need 30 baseline points and one observation"}
    if any(
        not isinstance(p, dict)
        or not number(p.get("timestamp"))
        or not number(p.get("value"))
        or p["value"] < 0
        or (data["unit"] == "ratio" and p["value"] > 1)
        for p in points
    ):
        return {"status": "invalid_data", "reason": "Non-finite, negative or incorrectly normalized point"}
    ordered = sorted(points, key=lambda p: p["timestamp"])
    gaps = [b["timestamp"] - a["timestamp"] for a, b in zip(ordered, ordered[1:])]
    if any(abs(gap - period) > period * 0.1 for gap in gaps):
        return {"status": "insufficient_data", "reason": "Duplicate or missing collection intervals"}
    age = now - ordered[-1]["timestamp"]
    if age < 0 or age > period * 2:
        return {"status": "insufficient_data", "reason": "Observation is future-dated or stale"}

    # The observation is excluded from the baseline. Use an explicit per-unit
    # absolute margin; this is a demonstration heuristic, not an SLO or ML model.
    baseline = [p["value"] for p in ordered[:-1]]
    center = statistics.median(baseline)
    mad = statistics.median(abs(value - center) for value in baseline)
    absolute_margin = {"requests_per_second": 1.0, "seconds": 0.01, "ratio": 0.001}[data["unit"]]
    margin = max(6 * 1.4826 * mad, abs(center) * 0.2, absolute_margin)
    latest = ordered[-1]["value"]
    return {
        "status": "review_required" if abs(latest - center) > margin else "within_baseline",
        "unit": data["unit"],
        "observedAt": ordered[-1]["timestamp"],
        "observedValue": latest,
        "baselineMedian": center,
        "illustrativeMargin": margin,
        "baselinePoints": len(baseline),
        "actionTaken": "none",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--now", type=float, help="Unix timestamp; omit to use the current clock")
    args = parser.parse_args()
    now = args.now if args.now is not None else time.time()
    try:
        data = json.load(sys.stdin)
        result = assess(data, now)
    except (ValueError, TypeError):
        result = {"status": "invalid_data", "reason": "Invalid JSON"}
    print(json.dumps(result, allow_nan=False))
    return 2 if result["status"] in {"invalid_data", "insufficient_data"} else 0


if __name__ == "__main__":
    raise SystemExit(main())
```

输入包含 `unit`、`periodSeconds` 和 `points`；每个 point 都包含 UTC Unix 时间戳和有限的非负值。至少提供 30 个基线点和一个观察值。ratio 的范围为 0–1。采集器必须检查 API 错误、分页和部分结果，并选择一个定义明确的聚合序列。

观察值不会纳入中位数/MAD 基线。边界是**用于说明的阈值**，并非训练好的模型或季节性预测系统。工具会对点排序，并拒绝存在间隔、重复或过期观察值的数据。`review_required` 不代表获准执行；`actionTaken` 始终为 `none`。

调整 CloudWatch 数据采集时，请使用指标的实际命名空间/维度，并对成对的 `Timestamps`/`Values` 排序。不要假设在默认响应顺序下 `Values[-1]` 是最新值。`RequestCount` 和特定目标组的指标具有不同的维度约定；还要处理 NextToken、StatusCode 和缺失的数据点。

### 审批和执行边界

提案应标明目标 ARN/namespace、当前配置版本、diff、指标证据/时间、失效时间、审批人和回滚条件。执行前，应重新检查授权、失效时间、版本、容量和目标端健康状况。字符串允许列表或未实际使用的 guardrail ConfigMap 都不是执行机制。

审批 UI 需要真正的请求签名验证、审批人授权、持久化状态、防重放保护和超时处理。发送 Slack 按钮，然后等待一个状态未改变的内存对象，并不构成完整的审批系统。不要声称未实现的执行器已执行操作。

NLB 变更请使用[第 02 章中受限的提案/可选执行流程](02-infrastructure-advanced.md)。不要仅因为未检测到异常，就覆盖每个 listener 或恢复任意 100/0 权重分配。NLB 权重设为零会在短时间后关闭现有连接，这与普通的非零权重调整不同。

对于渐进式交付，请使用[经过验证的 Argo Rollouts 指南](../gitops/argocd/05-traffic-management.md)中的 services、路由和 AnalysisTemplates。应使指标、参数、命名空间、空值/NaN 处理和失败条件符合金丝雀发布场景。分析失败不会自动回滚数据库变更，暂停/中止设置也无法解决所有恢复问题。

## 参考资料

- [Atlantis 安全性](https://www.runatlantis.io/docs/security.html)
- [Atlantis 服务器端策略](https://www.runatlantis.io/docs/server-side-repo-config.html)
- [HCP Terraform 动态 AWS 凭证](https://developer.hashicorp.com/terraform/cloud-docs/dynamic-provider-credentials/aws-configuration)
- [HCP Terraform run trigger](https://developer.hashicorp.com/terraform/cloud-docs/workspaces/settings/run-triggers)
- [Sentinel tfrun](https://developer.hashicorp.com/terraform/cloud-docs/policy-enforcement/import-reference/tfrun)
- [Flux ImageUpdateAutomation v1](https://github.com/fluxcd/image-automation-controller/blob/v1.2.5/docs/spec/v1/imageupdateautomations.md)
- [GitHub Copilot 代码审查](https://docs.github.com/en/copilot/how-tos/use-copilot-agents/request-a-code-review/use-code-review)
- [本章测验](../quizzes/ops/05-gitops-automation-quiz.md)

< [上一章：多集群](04-gitops-multi-cluster.md) | [目录](README.md) | [下一章：扩展策略](06-scaling-strategies.md) >
