# GitOps 自动化：Atlantis、HCP Terraform、Flux、AIOps

> **审阅基线**：Atlantis 0.47.1 / chart 6.15.0、HCP Terraform Provider 0.80.0、Sentinel 0.41.0、Flux 2.9.5（在发布说明审阅后，于 2026 年 10 月 12 日将 Flux 固定版本更新至补丁版 2.9.6；未重新运行）\
> **最后审阅**：2026 年 9 月 11 日。已使用本地 CLI、chart、schema 和测试替身检查。未执行实际 PR 评论、Terraform apply、HCP 资源创建、集群部署或外部 AI 调用。

< [上一章：多集群](04-gitops-multi-cluster.md) | [目录](README.md) | [下一章：扩缩容](06-scaling-strategies.md) >

将基础设施执行与应用程序协调分离。不要让 Atlantis 和 HCP Terraform 同时针对同一个 state 执行，也不要让 Flux 和 Argo CD 竞争同一 Kubernetes 字段。

| 工具 | 职责 | 独立的前提条件 |
|---|---|---|
| Atlantis | 执行基于 PR 的 Terraform plan/apply | 运行时、凭证、state、锁和命令授权 |
| HCP Terraform | 托管 workspace/run/state 和协作 | VCS 连接、agent、policy 和 workspace 权限 |
| Flux | 根据 source 协调 Kubernetes/Helm state | Controller identity、租户 RBAC 和仓库权限 |
| AIOps 分析 | 汇总观测结果并提出响应建议 | 已验证的数据、批准和受独立约束的执行器 |

## 1. 在 EKS 上运行 Atlantis

Atlantis 从 pull request 执行 Terraform。**plan 可以执行 provider、外部数据源和自定义命令。** 要求 apply 批准并不会使不受信任的 plan 变得安全。本示例适用于受控的私有基础设施仓库和已批准的运维团队，并禁用了 fork PR 和自动 plan。

### 身份与安装前提条件

- 为 namespace/ServiceAccount `atlantis` 配置 EKS Auto Mode Pod Identity association。不要将其与 IRSA annotation 混用。常规节点需要受支持的 agent 和 SDK 设置。
- 将访问范围限定到精确的 state 和 `.tflock` key、所需的 KMS key 及托管资源。区分 state object 的读/写与 lock object 的读/写/删除。宽泛的 `eks:*`、IAM role 创建和 PassRole 不是通用的最小权限策略。
- 将 role assumption 限制为精确的 ARN 和预期 trust。对 Pod Identity 使用受支持的 cluster/namespace/ServiceAccount request-tag condition。
- 保护凭证和 PR 输出中的敏感 plan JSON。Terraform `sensitive=true` 并不能阻止值被存储在 state 中。

运行时需要访问 AWS、Git、provider/module registry 和私有 EKS API。不要依赖未经验证的安装脚本或镜像中缺失的工具。Terraform 1.15.7 必须已存在，或可通过 `defaultTFVersion` 允许的下载路径获得。

### 已版本控制的 Helm values

如果 `auto-gp3` 尚不存在，请准备如下的 Auto Mode StorageClass。其 provisioner 不同于常规 EBS CSI。在不同的集群模式中使用适当的替代方案。

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

使用已批准的 secret-management mechanism，在 namespace `atlantis` 中准备这些 Secret。不要将真实值放入 Git 或 Helm values。

| Secret | 必需的 key |
|---|---|
| `atlantis-vcs` | `github-token`, `webhook-secret` |
| `atlantis-web-auth` | `username`, `password` |

向 GitHub bot/token 授予所需的 repository、PR 和 team-query 权限，并定期轮换它。将 `platform` 替换为实际获得授权的组织 team。使用 Atlantis 的 team allowlist，而不要在 shell hook 中通过用户名子字符串匹配。

```yaml
# fixtures/atlantis-values.yaml
fullnameOverride: atlantis
replicaCount: 1
image:
  repository: ghcr.io/runatlantis/atlantis
  tag: v0.47.1
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
  --version 6.15.0 --namespace atlantis --create-namespace \
  --kube-context "$ATLANTIS_CONTEXT" --values atlantis-values.yaml
```

这些 values 仅创建 ClusterIP。通过已批准的 HTTPS proxy/Ingress 连接 `atlantis.example.com` 和 `/events`，然后配置匹配的 GitHub webhook secret。webhook verification 和 Web UI authentication 是不同的。不要将 event route 扩展为通用 authentication bypass。

Chart 6.15.0 使用 `orgAllowlist`、`volumeClaim`、`environment` map 和 `containerSecurityContext`。可写 PVC 保存 checkout、plan 和 server-lock 数据；不要用只读 ConfigMap 覆盖它。单纯增加 replica 并不能使单个 RWO-PVC/BoltDB 部署变为高可用。管理保留 volume 的 retention、backup、recovery 以及最终 cleanup。

### Server policy 和 repository project

嵌入的 `repoConfig` 由 server 持有。`allowed_overrides: []` 和 `allow_custom_workflows: false` 可防止 PR 更改 approval requirement 或 execution command。单独配置 GitHub branch protection 和 required check。`approved` 并不天然意味着最新 commit 获得了两个不同的、当前有效的批准。

将 apply 本身作为 `mergeable` 的前提条件，可能会造成循环依赖。使 plan/check/review/apply 依赖关系与 repository rule 一致。本示例使用显式的 `atlantis plan -p ...` 命令；审阅并重新 plan 批准后作出的变更。

将此文件放在 repository root。每个 project directory 都使用[第 01 章](01-infrastructure-setup.md)中相应的 root，并拥有各自的 backend/state 以及经过审阅的 `backend.hcl` 和 `terraform.tfvars`。

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

在 plan/review/apply cluster 和 platform 变更前，先审阅并 apply network 变更。`depends_on` 不会传输 remote-state output，也不会自动刷新先前保存的下游 plan。依赖项发生变更时，重新 plan 下游变更。

```text
atlantis plan -p network-prod
atlantis apply -p network-prod
atlantis plan -p cluster-prod
atlantis apply -p cluster-prod
atlantis plan -p platform-prod
atlantis apply -p platform-prod
```

这些是 PR comment command。常规 Atlantis 流程是 **在 PR 中 plan → 满足 approval requirement → apply 该已保存的 plan → merge**。单独 merge 并不会 apply 基础设施。`automerge` 是在 apply 成功后进行 merge 的独立选项。

内置 `plan`/`apply` stage 使用由 Atlantis 管理的 plan file。自定义命令必须遵从 `$PLANFILE`。不要替换为单独的 `-out=tfplan`，也不要在 apply 已保存 plan 时传入新的 `-var-file` 值。plan file 和 JSON 可能包含敏感数据。

### Lock、policy 和故障处理

Atlantis PR/project/workspace lock 与 Terraform backend state lock 不同。当前默认 server database 是 BoltDB；受支持的 Redis configuration 需要单独设计。不要将 DynamoDB 称为默认 Atlantis lock database，也不要虚构 `lock_groups`/`apply_priority` ConfigMap。

`atlantis unlock` 会**移除** lock；它不是查询。首先检查 active run、已保存的 plan 和 state lock。在本示例版本中，`atlantis lock`、`atlantis locks` 和 `unlock --force` 不是通用 PR command。请使用受支持的 UI 或经身份验证的 API 检查 lock。

对 source code 进行 grep 以及对当前 state 中的资源计数，无法验证全部计划内基础设施。应考虑 module、data source、provider 以及 create/update/delete/unknown 值。将失败的 fmt/validate/policy/API operation 转为 warning 或 `|| true` 会移除 gate。

## 2. HCP Terraform

Terraform Cloud 现已更名为 **HCP Terraform**。它是 Atlantis 的替代方案，提供 workspace/run/state/policy 功能。针对 feature、pricing、concurrency、agent 和 Sentinel 检查当前 plan 与 contract。托管 hosting 仍然需要有意识地配置 VCS、权限、network 和 approval。

### Workspace 和动态 AWS 凭证

本示例假定已有 organization/project、VCS OAuth connection，以及具有私有 network 访问权限的 **agent pool**。agent execution 需要合格的 plan 和受支持的 agent version。不要假定公共 remote runner 可以直接访问私有 EKS API。

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

此 root 配置 HCP 资源。将其 backend/state 与基础设施 workspace 分开保护。针对现有 root 使用 HCP 托管 state 前，确定所有权并谨慎迁移其原有 S3 backend。不要从两个执行系统 apply 同一个 state。

AWS 必须已具备 `app.terraform.io` OIDC provider 和范围受限的 plan/apply role。将 trust audience/subject 限制为精确的 organization/project/workspace 以及 `run_phase:plan` 或 `run_phase:apply`。`TFC_AWS_*` variable 是 role identifier，而不是存储的长期 access key。在实际 provider 和 agent version 中验证 dynamic-credential support。

`queue_all_runs=false` 会在初始 workspace 设置期间保留 VCS-triggered run。它并非在首次手动 run 后永久禁用执行的开关。

### Run trigger 和共享 output

成功的上游 apply 会将下游 run 排入队列。**`auto_apply_run_trigger` 独立于普通的 `auto_apply`。** 这里两者都为 false，要求在 apply 前审阅。trigger 既不是所有依赖项均已就绪的证明，也不是 output-transfer mechanism。

本示例不会全局共享 workspace state。如果必须使用 output，请配置已批准的 consumer/permission，并考虑 `tfe_outputs`。能够读取 `terraform_remote_state` 的凭证可以访问完整的敏感 state，而不仅是 data source 显示的 output。根据实际设计连接 output access 与 module input。

### Sentinel policy

这是三个使用 Sentinel 0.41.0 测试的**示例 policy**，而不是 Python program。在它们可以阻止 HCP run 之前，需要 policy set、target workspace 和 enforcement configuration。

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

检查 `tags_all` 会包含 AWS Provider default tag。本示例检查所列 resource type 的 create/update action，并排除 deletion。缺失、空、null 或 unknown 的必需 tag 均无法通过。它并未涵盖所有 AWS resource type。

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

这适用于直接指定 `instance_types` 的 EC2 instance 和 managed node group。仅使用 launch template 的 group、Auto Mode NodePool 和其他 compute service 需要额外 policy。空或 unknown type list 不会被视为已批准的空集合。

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

使用 `tfrun.cost_estimate`，而不是不存在的路径，例如 `tfplan.workspace`。该示例允许提供的不超过 5,000 的月度估算值，并拒绝缺失、负数、NaN 和无限值。它无法保证涵盖不受支持的资源、流量和现有基础设施的完整 AWS 账单上限。

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

将 policy set 附加到预期 workspace，并将 policy administration 与 resource operation 分开。仅命名为 `soft_main` 的 rule 不会将 enforcement 更改为 soft-mandatory。不要将 failed evaluation 或 API error 变为 success。

## 3. Flux

本节使用 [Flux 2.9.6 指南](../gitops/02-fluxcd.md)。Argo CD 和 Flux 都会协调 declarative state。Argo CD 也包含多个 component；Flux 并非在任何情况下都更轻量或更隔离。仅进行 namespace separation 并不能完成 tenant authorization。

Image reflector 和 automation controller 是**可选 component**。bootstrap 会提交到 Git 并安装 controller。运行前验证 CLI checksum、受支持的 Kubernetes version、kubecontext 和 repository access。

```bash
flux check --pre
flux bootstrap github \
  --owner=REPLACE_ORG --repository=fleet-infra --branch=main \
  --path=clusters/production --version=v2.9.6 \
  --components-extra=image-reflector-controller,image-automation-controller
```

安全地提供已授权的 GitHub credential。不要向 organization 示例添加 `--personal`。区分默认 bootstrap 生成的 `flux-system` 文件与自行添加的 infrastructure/apps directory。

### Image automation 和 Git approval

该示例要求已准备 Git write Secret、通过 Pod Identity/IRSA 在 image-reflector-controller 上提供的 ECR read credential，以及部署 app 的 Flux Kustomization/HelmRelease。这些与节点的 image-pull role 分离。不要随意将 `provider: aws` 与不同的 registry-secret authentication path 组合。

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

该 policy 假定**在批准后发布不可变 semver release**。[CI 章节](03-ci-pipelines.md)中的唯一 SHA/build tag 并不匹配它。独立的 promotion process 必须将已批准的 index digest 标记为 release，或者该 policy 必须使用来自一个 CI system 的、经过审阅的单调递增 build scheme。

```yaml
# fixtures/flux-values.yaml
# apps/production/application/values.yaml -- actual Helm values file
# Replace repository and initial digest with the already approved application.
image:
  repository: REPLACE_ACCOUNT.dkr.ecr.ap-northeast-2.amazonaws.com/docs-ci/application # {"$imagepolicy": "flux-system:application:name"}
  tag: "1.0.0" # {"$imagepolicy": "flux-system:application:tag"}
  digest: sha256:REPLACE_APPROVED_DIGEST # {"$imagepolicy": "flux-system:application:digest"}
```

真实的 application chart 必须在构造 container image URI 时使用 `image.repository`、`tag` 和 `digest`。添加 digest value 并不会让现有 chart 使用它。检查 rendered manifest 是否指向已批准的 digest。对齐 Setters path、policy marker 和 GitRepository name。

当前 ImageUpdateAutomation commit template 使用 **`.Changed`**。不要将其替换为已移除的 `.Updated`。automation 推送至专用的 `flux/image-updates` branch；向 main 创建 PR 和进行 approval 需要另一个 workflow。对齐 Git write permission 和 branch protection。tag selection 不能替代 vulnerability/signature verification。

### Source、Helm 和 notification

- 当前示例使用 v1 `GitRepository`、`OCIRepository`、`Bucket` 和 image API。HelmRelease 是 v2；其当前 CRD 同时支持 `test.enable` 和 `test.timeout`。共同验证 chart version/value 与 CRD。
- Kustomization `dependsOn` 等待所引用 Flux object 的 Ready condition。配置 wait/healthChecks 以观测 workload health；它不是全局 cross-cluster barrier。
- 不要让 Terraform Helm Provider 和 Flux 同时拥有同一个 Helm release。迁移 Argo CD installation ownership 需要谨慎的 state/configuration migration。
- 不要将 Terraform state bucket 作为普通 Flux manifest source 公开。使用具有范围受限 prefix access 的独立 manifest-artifact bucket，并避免在 artifact 中包含 `.git` 的 ignore pattern。
- 在 Secret 中存储 notification webhook，并验证实际 receiver type 和 authentication。测试由 severity 和 filter 选择的 event。不要将未安装的 UI 或已弃用的 integration 作为默认 installation 的一部分。

[Flux 指南](../gitops/02-fluxcd.md)包含完整的 source/Kustomization/HelmRelease/notification 示例。

## 4. AIOps：从观测到可审阅的提案

### LLM 辅助的 PR 审阅

通过其受支持的 reviewer/automatic-review setting 配置 GitHub Copilot code review，并具备所需 repository permission 和可用 plan。虚构的 endpoint（如 `api.copilot.example.com`）不是可执行的 API 示例。

自定义 LLM integration 必须实现真实服务当前的 API/model/SDK contract、timeout、HTTP-error handling 和 output validation。diff 和 filename 是不受信任的数据。传递结构化 value，而不是将它们插入 shell、JavaScript 或 JSON string。被审阅内容中的 instruction 不授予执行权限。

披露截断和 API failure。不要向外部 fork PR 提供 secret，也不要仅凭 model response 就进行 approval、merge 或 apply。在使用外部 service 前定义允许的 source-code disclosure 和 cost scope。本次文档审阅期间未调用外部 AI service。

### Metric unit 和数据质量

CPU counter average 不是 CPU utilization。`rate(container_cpu_usage_seconds_total[...])` 产生 CPU core；HPA `averageUtilization` 是 **CPU request** 的百分比。不要将该百分比与 RPS 比较。解析 HPA 的 scaleTargetRef 和实际 Pod ownership，而不是假定 HPA 与 Deployment 共享名称。

RPS 的时间 p95 不同于 request-duration histogram quantile：

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

将 metric name/label 与实际 collection 匹配。缺失 series、零流量、NaN、stale observation 和 collection gap 不是健康状况的证据。结合流量、error、latency 和 capacity。仅平均 CPU 无法确立“最佳 HPA target”；load test、SLO 和 scale-down behavior 都很重要。

### 仅分析的可执行示例

该工具从 stdin 读取已规范化的单 metric JSON series，并且**仅**输出 advisory report。它不会更改 API、HPA、NLB、Git 或 Slack。处于 baseline 内并不能证明 application health。

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

输入包含 `unit`、`periodSeconds` 和 `points`；每个 point 都有 UTC Unix timestamp 和有限的非负 value。至少提供 30 个 baseline point 加上 observation。ratio 的范围为 0–1。collector 必须检查 API error、pagination 和 partial result，并选择一个明确定义的 aggregate series。

observation 被排除在 median/MAD baseline 之外。这些 margin 是**说明性阈值**，而不是训练出的 model 或季节性 forecasting system。该工具对 point 排序，并拒绝 gap、duplicate 和 stale observation。`review_required` 不是执行许可；`actionTaken` 保持为 `none`。

调整 CloudWatch collection 时，使用 metric 的实际 namespace/dimension，并对配对的 `Timestamps`/`Values` 排序。不要假定默认 response order 中 `Values[-1]` 最新。`RequestCount` 和 target-group-specific metric 具有不同的 dimension contract；处理 NextToken、StatusCode 和缺失 point。

### 批准与执行边界

提案应标识 target ARN/namespace、当前 configuration revision、diff、metric evidence/time、expiry、approver 和 rollback condition。执行前，重新检查 authorization、expiry、revision、capacity 和 destination health。string allowlist 或未使用的 guardrail ConfigMap 不是 enforcement mechanism。

approval UI 需要实际的 request-signature verification、approver authorization、persistent state、replay protection 和 timeout handling。发送 Slack button 后等待未变更的 in-memory object status 并不是完整的 approval system。不要声称未实现的 executor 已执行 action。

对 NLB 变更，使用[第 02 章的受约束提案/可选执行流程](02-infrastructure-advanced.md)。不要仅因为未检测到 anomaly 就覆盖每个 listener 或恢复任意的 100/0 split。与普通非零 weight adjustment 不同，NLB weight 为零会在短时间后关闭现有 connection。

对于 progressive delivery，使用[已验证的 Argo Rollouts 指南](../gitops/argocd/05-traffic-management.md)中的 service、routing 和 AnalysisTemplate。对齐 canary-specific metric、argument、namespace、empty/NaN handling 和 failure condition。analysis failure 不会自动 rollback database change，而 pause/abort setting 也不能解决所有 recovery problem。

## 参考资料

- [Atlantis 安全性](https://www.runatlantis.io/docs/security.html)
- [Atlantis 服务端 policy](https://www.runatlantis.io/docs/server-side-repo-config.html)
- [HCP Terraform 动态 AWS 凭证](https://developer.hashicorp.com/terraform/cloud-docs/dynamic-provider-credentials/aws-configuration)
- [HCP Terraform run trigger](https://developer.hashicorp.com/terraform/cloud-docs/workspaces/settings/run-triggers)
- [Sentinel tfrun](https://developer.hashicorp.com/terraform/cloud-docs/policy-enforcement/import-reference/tfrun)
- [Flux ImageUpdateAutomation v1](https://github.com/fluxcd/image-automation-controller/blob/v1.2.5/docs/spec/v1/imageupdateautomations.md)
- [GitHub Copilot code review](https://docs.github.com/en/copilot/how-tos/use-copilot-agents/request-a-code-review/use-code-review)
- [章节测验](../quizzes/ops/05-gitops-automation-quiz.md)

< [上一章：多集群](04-gitops-multi-cluster.md) | [目录](README.md) | [下一章：扩缩容](06-scaling-strategies.md) >
