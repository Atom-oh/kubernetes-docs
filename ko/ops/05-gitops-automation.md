# GitOps 자동화: Atlantis, HCP Terraform, Flux, AIOps

> **검토 기준**: Atlantis 0.47.1 / chart 6.15.0, HCP Terraform Provider 0.80.0, Sentinel 0.41.0, Flux 2.9.5\
> **마지막 검토**: 2026년 9월 11일. 로컬 CLI·차트·스키마와 테스트 대역으로 확인했습니다. 실제 PR 댓글·Terraform apply·HCP 생성·클러스터 배포·외부 AI 호출은 실행하지 않았습니다.

< [이전: 멀티클러스터](04-gitops-multi-cluster.md) | [목차](README.md) | [다음: 스케일링](06-scaling-strategies.md) >

인프라 변경을 실행하는 도구와 애플리케이션을 동기화하는 도구의 소유권을 분리합니다. 같은 Terraform state를 Atlantis와 HCP Terraform에서 동시에 실행하거나, 같은 Kubernetes 필드를 Flux와 Argo CD가 동시에 관리하지 않습니다.

| 도구 | 역할 | 별도로 준비할 것 |
|---|---|---|
| Atlantis | PR의 Terraform plan/apply 실행 | 실행 환경·자격 증명·state·잠금·실행 권한 |
| HCP Terraform | 관리형 workspace/run/state와 협업 | VCS 연결·agent·정책·워크스페이스별 권한 |
| Flux | source를 읽고 Kubernetes/Helm 상태 동기화 | controller identity·tenant RBAC·저장소 권한 |
| AIOps 분석 | 관측 자료 요약·이상 후보·변경 제안 | 검증된 데이터·승인·제한된 별도 실행기 |

## 1. Atlantis on EKS

Atlantis는 PR의 Terraform 코드를 실행합니다. **plan도 provider, external data source와 custom 명령을 실행할 수 있습니다.** apply 승인만 요구한다고 비신뢰 PR의 plan이 안전해지지는 않습니다. 이 예제는 통제된 private 인프라 저장소와 승인된 운영 팀용이며 fork PR과 자동 plan을 끕니다.

### 역할과 설치 조건

- EKS Auto Mode의 `atlantis` namespace/ServiceAccount에 Pod Identity association을 준비합니다. IRSA annotation을 추가하는 방식과 섞지 않습니다. 일반 노드는 지원되는 agent·SDK 구성이 필요합니다.
- state 버킷의 정확한 key와 `.tflock` key, 필요한 KMS 키와 실제 관리 리소스에만 권한을 부여합니다. S3 state 객체의 읽기·쓰기와 lock 객체의 읽기·쓰기·삭제를 구분합니다. 광범위한 `eks:*`, IAM 역할 생성과 PassRole을 “최소 권한” 예제로 부르지 않습니다.
- 다른 역할로 전환할 때는 정확한 역할 ARN과 제한된 trust를 사용합니다. Pod Identity trust는 해당 클러스터·namespace·ServiceAccount의 지원되는 request-tag 조건으로 제한합니다.
- PR에 credentials·민감한 plan JSON이 노출되지 않게 합니다. `sensitive=true`는 Terraform state에 값을 저장하지 않는다는 뜻이 아닙니다.

실행 환경은 AWS·Git·provider/module registry·private EKS API에 접근할 수 있어야 합니다. 무검증 설치 스크립트나 필요한 도구가 없는 stock 이미지에 의존하지 않습니다. `defaultTFVersion`의 Terraform 1.15.7이 실제 이미지에 있거나 허용된 다운로드 경로를 통해 제공되어야 합니다.

### 안정 차트의 values

기존 `auto-gp3` StorageClass가 없다면 아래처럼 Auto Mode용으로 준비합니다. 일반 EBS CSI의 provisioner와 다릅니다. 다른 클러스터 모드에서는 적절한 StorageClass로 바꿉니다.

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

같은 `atlantis` namespace에 승인된 secret 관리 방식으로 다음 Secret을 먼저 준비합니다. values나 Git에는 실제 값을 넣지 않습니다.

| Secret | 필요한 key |
|---|---|
| `atlantis-vcs` | `github-token`, `webhook-secret` |
| `atlantis-web-auth` | `username`, `password` |

GitHub bot/token에는 필요한 저장소·PR·팀 조회 권한을 주고 회전합니다. `platform`은 실제 조직의 허용 팀 이름으로 바꿉니다. 서버의 팀 allowlist 기능을 사용하며 사용자 이름에 대한 substring grep을 권한 검사로 쓰지 않습니다.

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

이 values는 ClusterIP만 만듭니다. 기존 승인된 HTTPS 프록시/Ingress로 `atlantis.example.com`과 `/events`를 연결한 뒤 GitHub webhook에 동일한 secret을 설정합니다. Webhook 서명 검증과 Web UI 인증은 서로 다른 기능입니다. 이벤트 경로를 임의 인증 우회 경로로 확장하지 않습니다.

차트 6.15.0에서는 `orgAllowlist`, `volumeClaim`, `environment` map, `containerSecurityContext`가 실제 key입니다. PVC에는 checkout·계획·서버 잠금 데이터가 있으므로 ConfigMap을 같은 경로에 read-only로 겹쳐 마운트하지 않습니다. 단일 RWO PVC와 BoltDB 구성에서 replica만 늘려 HA가 된다고 가정하지 않습니다. `Retain` 볼륨의 백업·복구·정리도 따로 관리합니다.

### 서버 정책과 저장소 프로젝트

위 `repoConfig`는 서버가 관리하는 정책입니다. `allowed_overrides: []`, `allow_custom_workflows: false`로 PR에서 승인 조건이나 실행 명령을 바꾸지 못하게 합니다. GitHub branch protection과 required checks도 별도로 설정합니다. `approved`가 자동으로 “최신 commit에 대한 서로 다른 두 명의 유효한 승인”을 뜻하지는 않습니다.

`mergeable` 검사에 apply 자체를 선행 필수 check로 요구하면 순환 대기가 생길 수 있습니다. plan/check/승인/배포의 의존성을 실제 저장소 정책에 맞춥니다. 현재 예제는 명시적인 `atlantis plan -p ...`을 사용하며 승인 후 변경된 commit은 다시 검토·계획합니다.

저장소 root에 다음 파일을 둡니다. 각 디렉터리는 [01장](01-infrastructure-setup.md)의 root 구성을 사용하며 고유한 backend/state와 검토된 `backend.hcl`, `terraform.tfvars`가 있어야 합니다.

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

먼저 network의 plan을 검토하고 apply를 완료한 뒤 cluster, platform을 순서대로 계획·검토·적용합니다. `depends_on`은 remote state 값을 전달하거나 상위 변경 뒤의 기존 하위 plan을 자동으로 새 plan으로 바꾸는 기능이 아닙니다. 의존성이 바뀌면 하위 plan을 다시 만듭니다.

```text
atlantis plan -p network-prod
atlantis apply -p network-prod
atlantis plan -p cluster-prod
atlantis apply -p cluster-prod
atlantis plan -p platform-prod
atlantis apply -p platform-prod
```

이것은 PR 댓글 명령입니다. 일반적인 Atlantis 흐름은 **PR에서 계획 → 승인 조건 확인 → 해당 저장 계획 적용 → merge**입니다. merge 자체가 apply를 대신하지 않습니다. `automerge`는 성공적으로 적용한 뒤 merge하는 별도 선택입니다.

내장 `plan`/`apply` 단계를 쓰면 Atlantis가 관리하는 계획 파일을 사용합니다. custom 명령이면 `$PLANFILE`을 따라야 합니다. `-out=tfplan`으로 별도 파일을 만들거나 저장 계획 apply에 `-var-file`을 다시 넘기지 않습니다. plan 파일과 JSON에는 민감한 값이 있을 수 있습니다.

### 잠금·정책·실패 처리

Atlantis의 PR/project/workspace 잠금과 Terraform backend의 state 잠금은 별개입니다. 현재 기본 서버 DB는 BoltDB이며 지원되는 Redis 구성은 별도 설계입니다. DynamoDB를 Atlantis 기본 잠금 DB라고 설명하거나 존재하지 않는 `lock_groups`, `apply_priority` ConfigMap으로 제어하지 않습니다.

`atlantis unlock`은 잠금을 **해제**하는 변경 작업이며 조회 명령이 아닙니다. 먼저 진행 중인 실행·저장 plan·state 잠금을 확인합니다. `atlantis lock`, `atlantis locks`, `unlock --force`를 이 버전의 일반 PR 명령으로 사용하지 않습니다. 잠금 조회 UI와 인증이 필요한 API는 공식 버전 문서에 맞춥니다.

정책은 Terraform 소스에 대한 단순 grep이나 현재 state 리소스 수만으로 검증하지 않습니다. 모듈·data source·provider·계획의 create/update/delete/unknown 값을 고려해야 합니다. failed fmt/validate/policy/API 요청을 `|| true`나 경고 출력으로 바꾸면 게이트가 사라집니다.

## 2. HCP Terraform

Terraform Cloud의 현재 제품 이름은 **HCP Terraform**입니다. Atlantis의 대안으로 선택할 수 있으며 workspace/run/state/정책을 제공합니다. 기능·요금·동시 실행·agent·Sentinel 사용 조건은 계약과 현재 플랜을 확인합니다. 관리형 서비스도 VCS·권한·네트워크·승인 정책을 자동 완성하지 않습니다.

### Workspace와 동적 AWS 자격 증명

아래 예제는 기존 organization/project, VCS OAuth 연결과 private 네트워크에 접근하는 **agent pool**을 사용합니다. HCP의 agent 실행은 사용 가능한 플랜과 지원 agent 버전을 전제로 합니다. Public remote runner가 private EKS API에 바로 접근할 수 있다고 가정하지 않습니다.

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

이 root는 HCP 리소스 설정용입니다. 실제 인프라 workspace와 분리해서 보호된 backend/state를 구성합니다. HCP run에서 state를 관리할 때는 원래 Terraform root의 S3 backend와의 소유권·state migration을 먼저 결정합니다. 같은 state를 두 곳에서 적용하지 않습니다.

AWS 측에는 `app.terraform.io` OIDC provider와 workspace/run-phase에 맞춘 plan/apply 역할이 미리 있어야 합니다. trust의 audience와 subject를 정확한 organization/project/workspace 및 `run_phase:plan` 또는 `run_phase:apply`로 제한합니다. 예제의 `TFC_AWS_*` 변수는 역할 식별자이며 장기 AWS 액세스 키를 저장하지 않습니다. 실제 provider 버전과 agent가 동적 자격 증명을 지원하는지도 확인합니다.

`queue_all_runs=false`는 새 workspace의 초기 준비가 끝나기 전에 VCS webhook으로 run이 시작되는 것을 막는 설정입니다. 첫 수동 run 이후에도 영구적인 실행 중지 스위치라고 가정하지 않습니다.

### Run Trigger와 출력 공유

상위 workspace의 성공한 apply가 하위 run을 대기열에 넣습니다. **`auto_apply_run_trigger`는 일반 `auto_apply`와 별개**입니다. 위 예제는 둘 다 false로 두어 검토 후 적용합니다. Trigger는 모든 의존성이 준비됐다는 증거나 데이터 전달 수단이 아닙니다.

예제는 workspace 전체의 state 공유를 기본 허용하지 않습니다. 출력 공유가 필요하면 승인된 소비자/권한을 명시하고 `tfe_outputs`를 검토합니다. `terraform_remote_state`를 읽을 수 있는 자격 증명은 출력에 보이지 않는 민감한 전체 state에도 접근할 수 있습니다. 출력 접근 권한과 모듈 입력을 실제 설계에 맞춰 연결합니다.

### Sentinel 정책

다음은 Sentinel 0.41.0으로 테스트한 세 가지 **정책 예제**입니다. Python 코드가 아닙니다. 적용 대상과 enforcement를 policy set에 연결해야 실제 HCP run을 차단합니다.

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

`tags_all`을 검사해 AWS Provider의 default tags도 포함합니다. 예제에 명시한 리소스의 create/update만 검사하며 삭제 작업은 제외합니다. 빈 값·null·알 수 없는 필수 태그는 통과시키지 않습니다. 모든 AWS 리소스 종류를 다 검사하는 정책은 아닙니다.

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

이는 EC2 instance와 직접 `instance_types`를 지정한 managed node group용입니다. launch template만으로 타입을 정한 node group, Auto Mode NodePool, 다른 compute 서비스에는 별도 정책이 필요합니다. 비어 있거나 알 수 없는 타입을 “허용된 타입 없음”으로 통과시키지 않습니다.

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

비용은 `tfrun.cost_estimate`에서 읽습니다. `tfplan.workspace` 같은 존재하지 않는 경로를 쓰지 않습니다. 이 예제는 5,000 이하의 제공된 월 추정치만 허용하며 누락·음수·NaN·무한대를 승인하지 않습니다. HCP 추정치가 지원하지 않는 리소스·데이터 전송·기존 인프라까지 포함한 실제 청구 상한을 보장하지는 않습니다.

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

Policy set을 지정 workspace에 연결하고 권한을 분리합니다. 코드에 별도의 `soft_main` rule을 쓰는 것만으로 enforcement가 soft-mandatory로 바뀌지는 않습니다. 검사 실패와 API 오류를 성공으로 바꾸지 않습니다.

## 3. Flux

이 절은 검토된 [Flux 2.9.5 가이드](../gitops/02-fluxcd.md)의 구성을 사용합니다. Argo CD와 Flux는 모두 선언적인 reconciliation 도구입니다. Argo CD도 여러 컴포넌트로 구성되며, Flux가 모든 환경에서 더 가볍거나 더 강한 격리를 제공한다고 단정하지 않습니다. namespace만 나누면 tenant 권한이 완성되는 것도 아닙니다.

이미지 reflector와 automation controller는 **선택 설치**합니다. Bootstrap은 Git에 commit하고 클러스터에 설치하는 작업입니다. CLI의 checksum·호환 Kubernetes 버전·kubecontext·저장소 권한을 확인한 뒤 수행합니다.

```bash
flux check --pre
flux bootstrap github \
  --owner=REPLACE_ORG --repository=fleet-infra --branch=main \
  --path=clusters/production --version=v2.9.5 \
  --components-extra=image-reflector-controller,image-automation-controller
```

Bootstrap에는 안전하게 제공한 GitHub 자격 증명이 필요합니다. 조직 예제에 `--personal`을 붙이지 않습니다. Bootstrap이 만드는 기본 `flux-system` 파일과 사용자가 추가하는 infrastructure/apps 경로를 구분합니다.

### 이미지 자동화와 Git 승인

아래 예제에는 준비된 Git 쓰기 Secret, image-reflector-controller의 ECR 읽기용 Pod Identity/IRSA, 배포를 담당하는 Flux Kustomization/HelmRelease가 필요합니다. Node의 Pod 이미지 pull 역할과 다른 권한입니다. `provider: aws`와 별도 registry secret을 무심코 섞지 않습니다.

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

이 정책은 **승인 후 게시된 불변 semver 릴리스**를 전제로 합니다. [CI 장](03-ci-pipelines.md)의 고유 SHA/build 태그만으로는 이 semver 정책에 일치하지 않습니다. 별도 promotion 작업에서 승인한 index digest에 릴리스 태그를 부여하거나, 한 CI 시스템의 단조 증가 build 규칙에 맞는 정책으로 변경해야 합니다.

```yaml
# fixtures/flux-values.yaml
# apps/production/application/values.yaml -- actual Helm values file
# Replace repository and initial digest with the already approved application.
image:
  repository: REPLACE_ACCOUNT.dkr.ecr.ap-northeast-2.amazonaws.com/docs-ci/application # {"$imagepolicy": "flux-system:application:name"}
  tag: "1.0.0" # {"$imagepolicy": "flux-system:application:tag"}
  digest: sha256:REPLACE_APPROVED_DIGEST # {"$imagepolicy": "flux-system:application:digest"}
```

실제 앱 차트는 위 `image.repository`, `tag`, `digest`를 컨테이너 image에 사용해야 합니다. values에 digest key만 추가한다고 기존 차트가 이를 자동 사용하지는 않습니다. 생성된 manifest의 image URI가 승인 digest를 가리키는지 확인합니다. Setters의 경로와 policy marker, GitRepository 이름이 서로 맞아야 합니다.

현재 ImageUpdateAutomation의 commit template은 **`.Changed`**를 사용합니다. 제거된 `.Updated`로 바꾸지 않습니다. Automation은 전용 `flux/image-updates` 브랜치에 push하며 main으로의 PR 생성·승인은 별도 절차입니다. Git 쓰기 권한과 branch protection을 함께 구성합니다. 새 태그 선택은 취약점·서명 검증을 대신하지 않습니다.

### Source·Helm·알림의 주의점

- 현재 예제의 `GitRepository`, `OCIRepository`, `Bucket`, 이미지 API는 v1입니다. HelmRelease는 v2이며 이 버전의 CRD는 `test.enable`과 `test.timeout`을 지원합니다. Helm chart 버전·values와 함께 실제 CRD 스키마에 대조합니다.
- Kustomization의 `dependsOn`은 해당 Flux 객체의 Ready 조건을 기다립니다. 실제 건강 검사는 wait/healthChecks를 설정해야 하며 다른 클러스터의 장애까지 막는 전역 barrier가 아닙니다.
- 동일한 Helm release를 Terraform Helm Provider와 Flux가 함께 소유하지 않게 합니다. Argo CD 설치를 Flux로 넘기려면 기존 소유권·설정·state 이행을 먼저 처리합니다.
- Terraform state 버킷을 일반 Flux manifest source로 노출하지 않습니다. 별도의 manifest artifact 버킷과 필요한 prefix 읽기 권한을 사용합니다. `.git`을 artifact에 포함시키는 ignore 예제도 피합니다.
- Notification Provider의 webhook은 Secret으로 관리하고 실제 수신기 종류와 인증을 확인합니다. `eventSeverity: info`와 필터 조합이 어떤 이벤트를 보낼지 테스트합니다. 설치하지 않은 UI나 종료된 연동을 기본 구성이라고 설명하지 않습니다.

완전한 source/Kustomization/HelmRelease/알림 예제는 [Flux 가이드](../gitops/02-fluxcd.md)에 있습니다.

## 4. AIOps: 관측에서 검토 가능한 제안까지

### LLM 기반 PR 리뷰

실제 GitHub Copilot code review 기능은 GitHub의 지원되는 reviewer/자동 리뷰 설정으로 구성합니다. `api.copilot.example.com` 같은 가짜 endpoint를 동작하는 API 예제로 쓰지 않습니다. 사용 가능한 기능·플랜·리포지터리 권한을 확인합니다.

자체 LLM 연동을 만들 때는 실제 서비스의 현재 API·모델·SDK 계약, timeout·HTTP 오류·출력 검증을 구현해야 합니다. Diff와 파일 이름은 비신뢰 데이터입니다. shell/JavaScript/JSON 문자열에 직접 끼워 넣지 말고 구조화된 인자로 전달합니다. 프롬프트에 들어간 명령을 실행 권한으로 취급하지 않습니다.

전체 diff를 보지 못했거나 API가 실패하면 그 한계를 표시합니다. 외부 fork PR에 secret을 전달하지 않고, 리뷰 모델의 응답만으로 승인·merge·apply하지 않습니다. 외부 서비스로 보낼 코드 범위와 비용도 먼저 정합니다. 이 문서 검토에서는 외부 AI 서비스를 호출하지 않았습니다.

### 메트릭 단위와 데이터 품질

CPU 누적 counter의 평균은 CPU 사용률이 아닙니다. CPU 사용량은 `rate(container_cpu_usage_seconds_total[...])`에서 cores로 얻고, HPA의 `averageUtilization`은 CPU **request 대비 비율**입니다. RPS와 이 비율을 같은 숫자로 비교하지 않습니다. HPA 이름을 Deployment 이름으로 추측하지 말고 scaleTargetRef와 실제 Pod 소유 관계를 사용합니다.

RPS의 시간상 p95와 요청 지연 histogram의 p95는 다른 값입니다.

```promql
# RPS의 7일간 p95: counter -> rate -> 시계열 quantile
quantile_over_time(0.95,
  (sum(rate(http_requests_total{namespace="production",service="myapp"}[5m])))[7d:5m]
)

# 요청 지연 p95: classic histogram, 결과 단위 seconds
histogram_quantile(0.95,
  sum by (le) (rate(http_request_duration_seconds_bucket{
    namespace="production",service="myapp"
  }[5m]))
)
```

이 예제의 metric/label은 실제 수집 스키마와 맞아야 합니다. 없는 시계열·0 traffic·NaN·오래된 데이터·수집 공백을 정상으로 간주하지 않습니다. 요청 수, 오류율, latency와 용량을 함께 봅니다. 평균 CPU만으로 “최적 HPA target”을 자동 산출할 수는 없으며 load test와 SLO, scale-down 동작이 필요합니다.

### 실행 가능한 분석 전용 예제

아래 도구는 이미 정규화한 한 metric의 JSON 시계열을 stdin으로 받아 **검토 보고서만** 출력합니다. 실제 API·HPA·NLB·Git·Slack을 변경하지 않습니다. 정상 범위도 애플리케이션이 건강하다는 판정이 아닙니다.

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

입력 형식은 `unit`, `periodSeconds`, `points`이며 각 point는 UTC Unix timestamp와 유한한 비음수 value입니다. 최소 30개 baseline과 최신 관측 1개가 필요합니다. Ratio는 0~1 범위입니다. Collector는 API 오류·페이지 처리·부분 응답을 확인하고 하나의 명확한 집계 시계열만 전달해야 합니다.

이 예제는 최신 관측을 baseline에서 제외하고 median/MAD 기반의 **설명용 임계값**을 사용합니다. 학습된 ML 모델이나 계절성을 처리하는 모델이 아닙니다. 정렬되지 않은 데이터는 정렬하고 누락·중복·stale 데이터를 거부합니다. `review_required`도 실행 허가가 아니며 `actionTaken`은 항상 `none`입니다.

CloudWatch를 연결한다면 metric에 맞는 namespace/dimension을 선택하고 `Timestamps`와 `Values`를 함께 정렬합니다. 기본 반환 순서에서 `Values[-1]`을 최신이라고 가정하지 않습니다. `RequestCount`와 TargetGroup별 metric은 dimension 계약이 다르며 NextToken/StatusCode/누락도 확인해야 합니다.

### 승인과 실행의 경계

변경 제안에는 대상 ARN/namespace, 현재 설정 revision, 제안 diff, 근거 metric·시간, 만료 시각, 승인 주체와 rollback 조건을 담습니다. 실행 직전에 승인·만료·현재 revision·용량·목적지 건강 상태를 다시 확인합니다. 단순한 문자열 allowlist나 존재하기만 하는 guardrail ConfigMap은 실행 통제가 아닙니다.

승인 UI를 만든다면 요청 서명·승인자 권한·영속 상태·재전송 방지·timeout을 실제로 구현해야 합니다. Slack 버튼을 보낸 후 메모리 객체의 status만 기다리는 코드는 완성된 승인 시스템이 아닙니다. 이 장은 구현되지 않은 실행기를 동작한다고 표시하지 않습니다.

NLB 변경은 [02장의 제한된 제안/선택적 실행 흐름](02-infrastructure-advanced.md)을 사용합니다. 모든 listener를 한꺼번에 덮어쓰거나 이상치가 없다는 이유로 임의의 100/0 비율을 복원하지 않습니다. 현재 NLB에서는 weight 0으로 바꿀 때 기존 연결도 잠시 후 닫히므로 일반적인 weight 변경과 구분합니다.

Progressive delivery는 [검증된 Argo Rollouts 예제](../gitops/argocd/05-traffic-management.md)의 서비스·라우팅·AnalysisTemplate을 함께 사용합니다. Canary에 한정한 metric, arguments, namespace, 빈 값/NaN 처리와 실패 조건을 맞춥니다. 분석 실패가 데이터베이스까지 복구한다거나 pause/abort 옵션만으로 모든 rollback이 해결된다고 가정하지 않습니다.

## 참고 자료

- [Atlantis 보안](https://www.runatlantis.io/docs/security.html)
- [Atlantis 서버 측 정책](https://www.runatlantis.io/docs/server-side-repo-config.html)
- [HCP Terraform AWS 동적 자격 증명](https://developer.hashicorp.com/terraform/cloud-docs/dynamic-provider-credentials/aws-configuration)
- [HCP Terraform Run Triggers](https://developer.hashicorp.com/terraform/cloud-docs/workspaces/settings/run-triggers)
- [Sentinel tfrun](https://developer.hashicorp.com/terraform/cloud-docs/policy-enforcement/import-reference/tfrun)
- [Flux ImageUpdateAutomation v1](https://github.com/fluxcd/image-automation-controller/blob/v1.2.5/docs/spec/v1/imageupdateautomations.md)
- [GitHub Copilot code review](https://docs.github.com/en/copilot/how-tos/use-copilot-agents/request-a-code-review/use-code-review)
- [이 장의 퀴즈](../quizzes/ops/05-gitops-automation-quiz.md)

< [이전: 멀티클러스터](04-gitops-multi-cluster.md) | [목차](README.md) | [다음: 스케일링](06-scaling-strategies.md) >
