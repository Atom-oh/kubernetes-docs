# GitOps 自動化: Atlantis、HCP Terraform、Flux、AIOps

> **レビュー基準**: Atlantis 0.48.1 / chart 6.16.1、HCP Terraform Provider 0.80.0、Sentinel 0.41.0、Flux 2.9.6（2.9.5 で検証。パッチ版への pin 更新のみで再実行なし）\
> **最終レビュー**: 2026年10月16日。ローカル CLI、chart、schema、テストダブルで確認しました。実際の PR コメント、Terraform apply、HCP リソース作成、クラスターへのデプロイ、外部 AI 呼び出しは実行していません。

< [前へ: マルチクラスター](04-gitops-multi-cluster.md) | [目次](README.md) | [次へ: スケーリング](06-scaling-strategies.md) >

インフラストラクチャの実行とアプリケーションの reconciliation を分離してください。Atlantis と HCP Terraform が同じ state に対して同時に実行したり、Flux と Argo CD が同じ Kubernetes フィールドを競合して管理したりしないようにします。

| ツール | 責務 | 分離すべき前提条件 |
|---|---|---|
| Atlantis | PR ベースの Terraform plan/apply の実行 | Runtime、認証情報、state、lock、コマンド認可 |
| HCP Terraform | 管理された workspace/run/state とコラボレーション | VCS 接続、agent、policy、workspace 権限 |
| Flux | source から Kubernetes/Helm state を reconciliation | Controller identity、テナント RBAC、repository 権限 |
| AIOps 分析 | 観測結果の要約と対応の提案 | 検証済みデータ、承認、別途制約された executor |

## 1. EKS 上の Atlantis

Atlantis は pull request から Terraform を実行します。**plan は provider、external data source、custom command を実行する場合があります。** apply の承認を要求しても、信頼できない plan が安全になるわけではありません。この例は、fork PR と自動 plan を無効化した、管理対象のプライベートなインフラストラクチャ repository と承認済みの運用チーム向けです。

### Identity とインストールの前提条件

- namespace/ServiceAccount `atlantis` 用に EKS Auto Mode Pod Identity association を設定してください。IRSA annotation と混在させないでください。従来型 node には対応する agent と SDK のセットアップが必要です。
- 正確な state および `.tflock` key、必要な KMS key、管理対象リソースにアクセス範囲を限定してください。state object の read/write と lock object の read/write/delete を区別します。広範な `eks:*`、IAM role 作成、PassRole は汎用的な最小権限 policy ではありません。
- role assumption を正確な ARN と意図した trust に限定してください。Pod Identity には対応する cluster/namespace/ServiceAccount の request-tag 条件を使用します。
- PR 出力から認証情報と機密の plan JSON を保護してください。Terraform の `sensitive=true` は値が state に保存されることを防ぎません。

Runtime には AWS、Git、provider/module registry、プライベート EKS API へのアクセスが必要です。検証されていないインストール script や image に存在しない tool に依存しないでください。Terraform 1.15.7 は、`defaultTFVersion` 用に存在しているか、許可されたダウンロードパスから取得可能でなければなりません。

### バージョン固定 Helm values

`auto-gp3` がまだ存在しない場合は、以下のような Auto Mode StorageClass を準備してください。その provisioner は従来の EBS CSI とは異なります。異なる cluster mode では適切な代替を使用します。

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

承認済みの secret-management mechanism を使って、namespace `atlantis` にこれらの Secret を準備してください。実際の値を Git や Helm values に入れないでください。

| Secret | 必須 key |
|---|---|
| `atlantis-vcs` | `github-token`, `webhook-secret` |
| `atlantis-web-auth` | `username`, `password` |

GitHub bot/token に必要な repository、PR、team-query 権限を与え、ローテーションしてください。`platform` を実際に認可された organization team に置き換えます。shell hook で username を部分文字列一致させるのではなく、Atlantis の team allowlist を使用してください。

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

これらの values は ClusterIP のみを作成します。承認済みの HTTPS proxy/Ingress を介して `atlantis.example.com` と `/events` を接続し、対応する GitHub webhook secret を設定してください。Webhook の検証と Web UI の認証は別物です。event route を一般的な認証バイパスに拡張しないでください。

Chart 6.16.1 は `orgAllowlist`、`volumeClaim`、`environment` map、`containerSecurityContext` を使用します。書き込み可能な PVC には checkout、plan、server-lock のデータが保持されます。read-only ConfigMap で overlay しないでください。replica を増やすだけでは、単一 RWO PVC/BoltDB のデプロイメントは高可用になりません。retained volume の保持、backup、recovery、最終的な cleanup を管理してください。

### Server policy と repository project

埋め込みの `repoConfig` は server が所有します。`allowed_overrides: []` と `allow_custom_workflows: false` により、PR が承認要件や実行コマンドを変更することを防ぎます。GitHub の branch protection と required check は別途設定してください。`approved` は、最新 commit に対する別個で現在有効な 2 件の承認を本質的に意味するものではありません。

`mergeable` の前提条件として apply 自体を要求すると循環依存が生じることがあります。plan/check/review/apply の依存関係を repository rule と整合させます。この例では明示的な `atlantis plan -p ...` command を使用します。承認後に変更された内容は review し、再度 plan してください。

このファイルを repository root に配置してください。各 project directory は、[chapter 01](01-infrastructure-setup.md) の対応する root を使用し、それぞれ固有の backend/state と、review 済みの `backend.hcl` および `terraform.tfvars` を持ちます。

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

cluster と platform の変更を plan/review/apply する前に network の変更を review、apply してください。`depends_on` は remote-state output を伝達せず、以前保存した downstream plan を自動で更新もしません。依存関係が変わったら downstream の変更を再度 plan してください。

```text
atlantis plan -p network-prod
atlantis apply -p network-prod
atlantis plan -p cluster-prod
atlantis apply -p cluster-prod
atlantis plan -p platform-prod
atlantis apply -p platform-prod
```

これらは PR comment command です。通常の Atlantis flow は **PR 内で plan → 承認要件を満たす → 保存された plan を apply → merge** です。merge だけではインフラストラクチャは apply されません。`automerge` は apply が成功した後に merge する別の option です。

組み込みの `plan`/`apply` stage は Atlantis が管理する plan file を使用します。custom command は `$PLANFILE` を遵守しなければなりません。別の `-out=tfplan` に置き換えたり、保存済み plan を apply するときに新しい `-var-file` 値を渡したりしないでください。plan file と JSON には機密データが含まれる可能性があります。

### Lock、policy、障害処理

Atlantis の PR/project/workspace lock は Terraform backend state lock とは異なります。現在のデフォルト server database は BoltDB です。対応する Redis 構成には別途設計が必要です。DynamoDB をデフォルト Atlantis lock database と呼んだり、存在しない `lock_groups`/`apply_priority` ConfigMap を作ったりしないでください。

`atlantis unlock` は lock を**削除**します。query ではありません。まず active run、saved plan、state lock を確認してください。この例の version では、`atlantis lock`、`atlantis locks`、`unlock --force` は汎用的な PR command ではありません。lock の確認には対応する UI または認証済み API を使用してください。

source code の grep や現在の state に含まれる resource の数は、すべての計画済みインフラストラクチャを検証しません。module、data source、provider、create/update/delete/unknown 値を考慮してください。失敗した fmt/validate/policy/API 操作を warning や `|| true` に変換すると gate がなくなります。

## 2. HCP Terraform

Terraform Cloud は現在 **HCP Terraform** という名称です。workspace/run/state/policy 機能を備えた Atlantis の代替です。機能、価格、concurrency、agent、Sentinel について、現在の plan と契約を確認してください。管理ホスティングでも、VCS、権限、network、承認の慎重な構成が必要です。

### Workspace と動的 AWS 認証情報

この例は、既存の organization/project、VCS OAuth connection、プライベート network にアクセスできる **agent pool** を前提とします。agent 実行には対象となる plan と対応した agent version が必要です。public remote runner がプライベート EKS API に直接到達できると想定しないでください。

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

この root は HCP resource を構成します。その backend/state をインフラストラクチャ workspace とは別に保護してください。既存 root に HCP 管理 state を使用する前に、所有権を決定し、元の S3 backend を慎重に移行してください。2 つの実行 system から同じ state を apply しないでください。

AWS にはすでに `app.terraform.io` OIDC provider と、範囲を限定した plan/apply role が必要です。trust の audience/subject を正確な organization/project/workspace と `run_phase:plan` または `run_phase:apply` に制限してください。`TFC_AWS_*` variable は role identifier であり、保存された長期 access key ではありません。実際の provider と agent version で dynamic credential のサポートを検証してください。

`queue_all_runs=false` は最初の workspace setup 時に VCS-triggered run を保留します。最初の manual run 後に永続的に実行を無効化する switch ではありません。

### Run trigger と output の共有

upstream apply が成功すると downstream run が queue されます。**`auto_apply_run_trigger` は通常の `auto_apply` から独立しています。** ここでは両方とも false であり、apply 前に review が必要です。trigger はすべての依存関係の準備ができた証明でも、output 転送 mechanism でもありません。

この例では workspace state をグローバルに共有しません。output を利用する必要がある場合は、承認済みの consumer/permission を構成し、`tfe_outputs` を検討してください。`terraform_remote_state` を読み取れる認証情報は、data source が表示する output だけでなく完全な機密 state にアクセスできます。実際の設計に従って output access と module input を接続してください。

### Sentinel policy

これらは Sentinel 0.41.0 でテストした 3 つの**例示 policy**であり、Python program ではありません。HCP run を block するには、policy set、対象 workspace、enforcement 構成が必要です。

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

`tags_all` を確認すると AWS Provider の default tag が含まれます。この例は、一覧の resource type に対する create/update action を確認し、deletion を除外します。必須 tag が欠落、空、null、unknown の場合は通過しません。すべての AWS resource type を対象にするものではありません。

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

これは直接指定された `instance_types` を持つ EC2 instance と managed node group に適用されます。launch-template 専用 group、Auto Mode NodePool、その他の compute service には追加 policy が必要です。空または unknown の type list は、承認済みの空集合として扱われません。

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

存在しない `tfplan.workspace` のような path ではなく、`tfrun.cost_estimate` を使用してください。この例は、提供された月額見積もりが 5,000 以下であることを許可し、欠落、負、NaN、無限の値を拒否します。未対応 resource、traffic、既存インフラストラクチャを含む完全な AWS 請求上限を保証することはできません。

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

policy set を意図した workspace に attach し、policy administration を resource operation から分離してください。単に `soft_main` と名付けた rule では enforcement は soft-mandatory に変わりません。失敗した evaluation や API error を success に変換しないでください。

## 3. Flux

この section では [Flux 2.9.6 guide](../gitops/02-fluxcd.md) を使用します。Argo CD と Flux はどちらも宣言的 state を reconciliation します。Argo CD にも複数 component があります。Flux が常に軽量またはより分離されているわけではありません。namespace の分離だけでは tenant authorization は完了しません。

image reflector と automation controller は**任意 component**です。bootstrap は Git に commit し、controller をインストールします。実行前に CLI checksum、対応 Kubernetes version、kubecontext、repository access を検証してください。

```bash
flux check --pre
flux bootstrap github \
  --owner=REPLACE_ORG --repository=fleet-infra --branch=main \
  --path=clusters/production --version=v2.9.6 \
  --components-extra=image-reflector-controller,image-automation-controller
```

認可された GitHub 認証情報を安全に提供してください。organization の例に `--personal` を追加しないでください。デフォルトで bootstrap が生成する `flux-system` file と、自分で追加する infrastructure/apps directory を区別してください。

### Image automation と Git 承認

この例には、準備済みの Git write Secret、Pod Identity/IRSA を通じて image-reflector-controller が使用する ECR read credential、アプリをデプロイする Flux Kustomization/HelmRelease が必要です。これらは node の image-pull role とは別です。`provider: aws` を別の registry-secret authentication path と安易に組み合わせないでください。

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

policy は**承認後に公開された immutable な semver release**を前提とします。[CI chapter](03-ci-pipelines.md) の一意な SHA/build tag はこれに一致しません。別の promotion process が承認済み index digest を release として tag 付けするか、policy が 1 つの CI system からの review 済みで単調増加する build scheme を使用する必要があります。

```yaml
# fixtures/flux-values.yaml
# apps/production/application/values.yaml -- actual Helm values file
# Replace repository and initial digest with the already approved application.
image:
  repository: REPLACE_ACCOUNT.dkr.ecr.ap-northeast-2.amazonaws.com/docs-ci/application # {"$imagepolicy": "flux-system:application:name"}
  tag: "1.0.0" # {"$imagepolicy": "flux-system:application:tag"}
  digest: sha256:REPLACE_APPROVED_DIGEST # {"$imagepolicy": "flux-system:application:digest"}
```

実際の application chart は、container image URI を構築するときに `image.repository`、`tag`、`digest` を使用しなければなりません。digest 値を追加しても、既存 chart がそれを利用するわけではありません。render された manifest が承認済み digest を指すことを確認してください。Setters path、policy marker、GitRepository 名を整合させます。

現在の ImageUpdateAutomation commit template は **`.Changed`** を使用します。削除された `.Updated` に置き換えないでください。automation は専用の `flux/image-updates` branch に push します。main への PR 作成と承認には別の workflow が必要です。Git write permission と branch protection を整合させてください。tag の選択は vulnerability/signature verification の代替ではありません。

### Source、Helm、notification

- 現在の例では v1 の `GitRepository`、`OCIRepository`、`Bucket`、image API を使用します。HelmRelease は v2 です。その現在の CRD は `test.enable` と `test.timeout` の両方をサポートします。chart version/value と CRD を合わせて検証してください。
- Kustomization の `dependsOn` は、参照する Flux object の Ready condition を待ちます。workload health を観測するために wait/healthChecks を構成してください。これはグローバルな cross-cluster barrier ではありません。
- Terraform Helm Provider と Flux が同じ Helm release を同時に所有しないようにしてください。Argo CD installation の所有権を移行するには、慎重な state/configuration migration が必要です。
- Terraform state bucket を通常の Flux manifest source として公開しないでください。prefix access を限定した別の manifest-artifact bucket を使用し、artifact 内の `.git` を含む ignore pattern を避けます。
- notification webhook は Secret に格納し、実際の receiver type と authentication を検証してください。severity と filter で選択した event をテストします。未インストールの UI や廃止された integration をデフォルト installation の一部として示さないでください。

[Flux guide](../gitops/02-fluxcd.md) には完全な source/Kustomization/HelmRelease/notification の例があります。

## 4. AIOps: 観測からレビュー可能な提案へ

### LLM 支援 PR review

必要な repository permission と利用可能な plan を使用して、対応する reviewer/automatic-review setting を通じて GitHub Copilot code review を構成してください。`api.copilot.example.com` のような架空の endpoint は実行可能な API 例ではありません。

custom LLM integration は、実際の service の現在の API/model/SDK contract、timeout、HTTP-error handling、output validation を実装しなければなりません。diff と filename は信頼できない data です。shell、JavaScript、JSON string に埋め込むのではなく、structured value を渡してください。レビュー対象 content 内の instruction に実行権限はありません。

truncation と API failure を開示してください。外部 fork PR に secret を渡したり、model response だけを approval、merge、apply にしたりしないでください。外部 service を使用する前に、許可する source-code disclosure と cost scope を定義してください。この document のレビュー中に外部 AI service は呼び出されませんでした。

### Metric unit と data quality

CPU counter average は CPU utilization ではありません。`rate(container_cpu_usage_seconds_total[...])` は CPU core を返します。HPA の `averageUtilization` は**CPU request**の percentage です。その percentage を RPS と比較しないでください。HPA と Deployment が同じ name を共有すると仮定するのではなく、HPA の scaleTargetRef と実際の Pod ownership を解決してください。

RPS の時間的 p95 は request-duration histogram quantile とは異なります:

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

metric name/label を実際の collection に合わせてください。missing series、zero traffic、NaN、stale observation、collection gap は正常性の証拠ではありません。traffic、error、latency、capacity を組み合わせます。平均 CPU だけでは「最適な HPA target」を確立できません。load test、SLO、scale-down behavior が重要です。

### 実行可能な分析専用の例

この tool は stdin からすでに正規化された単一 metric の JSON series を読み取り、**助言レポートのみ**を出力します。API、HPA、NLB、Git、Slack を変更しません。baseline 内であっても、アプリケーションの正常性が確立されるわけではありません。

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

入力には `unit`、`periodSeconds`、`points` が含まれます。各 point は UTC Unix timestamp と有限の非負値を持ちます。少なくとも 30 個の baseline point と observation を指定してください。ratio は 0–1 です。collector は API error、pagination、partial result を確認し、明確に定義された 1 つの aggregate series を選択しなければなりません。

observation は median/MAD baseline から除外されます。margin は**例示的な threshold**であり、学習済み model や季節予測 system ではありません。tool は point を sort し、gap、duplicate、stale observation を拒否します。`review_required` は実行の許可ではありません。`actionTaken` は `none` のままです。

CloudWatch collection を適用するときは、metric の実際の namespace/dimension を使用し、対応する `Timestamps`/`Values` を sort してください。デフォルトの response order で `Values[-1]` が最新であると仮定しないでください。`RequestCount` と target-group 固有の metric には異なる dimension contract があります。NextToken、StatusCode、missing point を処理してください。

### 承認と実行の境界

proposal には、target ARN/namespace、現在の configuration revision、diff、metric evidence/time、expiry、approver、rollback condition を示す必要があります。実行前に authorization、expiry、revision、capacity、destination health を再確認してください。string allowlist や未使用の guardrail ConfigMap は enforcement mechanism ではありません。

approval UI には、実際の request-signature verification、approver authorization、永続 state、replay protection、timeout handling が必要です。Slack button を送信してから変更されない in-memory object の status を待つだけでは、完全な approval system ではありません。未実装の executor が action を実行したと主張しないでください。

NLB の変更には、[chapter 02 の制約付き proposal/任意の実行 flow](02-infrastructure-advanced.md) を使用してください。anomaly が検出されなかったというだけで、すべての listener を上書きしたり任意の 100/0 split を復元したりしないでください。NLB weight がゼロの場合、通常の非ゼロ weight 調整とは異なり、短時間後に既存 connection が閉じられます。

progressive delivery には、[検証済み Argo Rollouts guide](../gitops/argocd/05-traffic-management.md) の service、routing、AnalysisTemplates を使用してください。canary 固有の metric、argument、namespace、empty/NaN handling、failure condition を整合させます。analysis failure は database change を自動的に rollback しません。また、pause/abort setting はすべての recovery problem を解決しません。

## 参考資料

- [Atlantis security](https://www.runatlantis.io/docs/security.html)
- [Atlantis server-side policy](https://www.runatlantis.io/docs/server-side-repo-config.html)
- [HCP Terraform dynamic AWS credentials](https://developer.hashicorp.com/terraform/cloud-docs/dynamic-provider-credentials/aws-configuration)
- [HCP Terraform run triggers](https://developer.hashicorp.com/terraform/cloud-docs/workspaces/settings/run-triggers)
- [Sentinel tfrun](https://developer.hashicorp.com/terraform/cloud-docs/policy-enforcement/import-reference/tfrun)
- [Flux ImageUpdateAutomation v1](https://github.com/fluxcd/image-automation-controller/blob/v1.2.5/docs/spec/v1/imageupdateautomations.md)
- [GitHub Copilot code review](https://docs.github.com/en/copilot/how-tos/use-copilot-agents/request-a-code-review/use-code-review)
- [章のクイズ](../quizzes/ops/05-gitops-automation-quiz.md)

< [前へ: マルチクラスター](04-gitops-multi-cluster.md) | [目次](README.md) | [次へ: スケーリング](06-scaling-strategies.md) >
