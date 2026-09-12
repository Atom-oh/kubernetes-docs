# GitOps Automation: Atlantis, HCP Terraform, Flux, AIOps

> **Review baseline**: Atlantis 0.47.1 / chart 6.15.0, HCP Terraform Provider 0.80.0, Sentinel 0.41.0, Flux 2.9.5\
> **Last reviewed**: September 11, 2026. Checked with local CLIs, charts, schemas and test doubles. No actual PR comments, Terraform apply, HCP resource creation, cluster deployment or external AI calls were performed.

< [Previous: Multi-Cluster](04-gitops-multi-cluster.md) | [Contents](README.md) | [Next: Scaling](06-scaling-strategies.md) >

Separate infrastructure execution from application reconciliation. Do not let Atlantis and HCP Terraform execute against the same state concurrently, or let Flux and Argo CD compete for the same Kubernetes fields.

| Tool | Responsibility | Separate prerequisites |
|---|---|---|
| Atlantis | Execute PR-based Terraform plans/applies | Runtime, credentials, state, locks and command authorization |
| HCP Terraform | Managed workspaces/runs/state and collaboration | VCS connection, agents, policies and workspace permissions |
| Flux | Reconcile Kubernetes/Helm state from sources | Controller identities, tenant RBAC and repository permissions |
| AIOps analysis | Summarize observations and propose responses | Validated data, approval and a separately constrained executor |

## 1. Atlantis on EKS

Atlantis executes Terraform from pull requests. **Planning can execute providers, external data sources and custom commands.** Requiring apply approval does not make an untrusted plan safe. This example is for a controlled private infrastructure repository and an approved operations team, with fork PRs and automatic planning disabled.

### Identity and installation prerequisites

- Configure the EKS Auto Mode Pod Identity association for namespace/ServiceAccount `atlantis`. Do not mix it with an IRSA annotation. Conventional nodes need the supported agent and SDK setup.
- Scope access to the exact state and `.tflock` keys, required KMS keys and managed resources. Distinguish state-object read/write from lock-object read/write/delete. Broad `eks:*`, IAM role creation and PassRole are not a universal least-privilege policy.
- Restrict role assumptions to exact ARNs and intended trust. Use supported cluster/namespace/ServiceAccount request-tag conditions for Pod Identity.
- Protect credentials and sensitive plan JSON from PR output. Terraform `sensitive=true` does not prevent values from being stored in state.

The runtime needs access to AWS, Git, provider/module registries and private EKS APIs. Do not depend on unverified installation scripts or tools absent from the image. Terraform 1.15.7 must be present or obtainable through the permitted download path for `defaultTFVersion`.

### Versioned Helm values

If `auto-gp3` does not already exist, prepare an Auto Mode StorageClass such as this. Its provisioner differs from conventional EBS CSI. Use an appropriate alternative on a different cluster mode.

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

Prepare these Secrets in namespace `atlantis` using the approved secret-management mechanism. Do not put real values in Git or Helm values.

| Secret | Required keys |
|---|---|
| `atlantis-vcs` | `github-token`, `webhook-secret` |
| `atlantis-web-auth` | `username`, `password` |

Give the GitHub bot/token the required repository, PR and team-query permissions and rotate it. Replace `platform` with the actual authorized organization team. Use Atlantis's team allowlist rather than substring matching usernames in a shell hook.

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

These values create a ClusterIP only. Connect `atlantis.example.com` and `/events` through an approved HTTPS proxy/Ingress, then configure the matching GitHub webhook secret. Webhook verification and Web UI authentication are distinct. Do not expand the event route into a general authentication bypass.

Chart 6.15.0 uses `orgAllowlist`, `volumeClaim`, an `environment` map and `containerSecurityContext`. The writable PVC holds checkout, plan and server-lock data; do not overlay it with a read-only ConfigMap. Increasing replicas alone does not make a single-RWO-PVC/BoltDB deployment highly available. Manage retention, backup, recovery and eventual cleanup of retained volumes.

### Server policy and repository projects

The embedded `repoConfig` is server-owned. `allowed_overrides: []` and `allow_custom_workflows: false` prevent a PR from changing approval requirements or execution commands. Configure GitHub branch protection and required checks separately. `approved` does not inherently mean two distinct, current approvals of the latest commit.

Requiring apply itself as a prerequisite for `mergeable` can create a circular dependency. Align plan/check/review/apply dependencies with repository rules. This example uses explicit `atlantis plan -p ...` commands; review and re-plan changes made after approval.

Place this file at the repository root. Each project directory uses the corresponding root from [chapter 01](01-infrastructure-setup.md), with its own backend/state and reviewed `backend.hcl` and `terraform.tfvars`.

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

Review and apply network changes before planning/reviewing/applying cluster and platform changes. `depends_on` does not transmit remote-state outputs or automatically refresh a previously saved downstream plan. Re-plan downstream changes when dependencies change.

```text
atlantis plan -p network-prod
atlantis apply -p network-prod
atlantis plan -p cluster-prod
atlantis apply -p cluster-prod
atlantis plan -p platform-prod
atlantis apply -p platform-prod
```

These are PR comment commands. The ordinary Atlantis flow is **plan in the PR → satisfy approval requirements → apply that saved plan → merge**. Merging alone does not apply infrastructure. `automerge` is a separate option to merge after successful applies.

Built-in `plan`/`apply` stages use the plan file managed by Atlantis. Custom commands must respect `$PLANFILE`. Do not replace it with a separate `-out=tfplan` or pass new `-var-file` values while applying a saved plan. Plan files and JSON can contain sensitive data.

### Locks, policies and failure handling

Atlantis PR/project/workspace locks differ from Terraform backend state locks. The current default server database is BoltDB; supported Redis configurations require separate design. Do not call DynamoDB the default Atlantis lock database or invent `lock_groups`/`apply_priority` ConfigMaps.

`atlantis unlock` **removes** a lock; it is not a query. Check active runs, saved plans and state locks first. `atlantis lock`, `atlantis locks` and `unlock --force` are not general PR commands in this example's version. Use the supported UI or authenticated API for lock inspection.

Source-code grep and counting resources in the current state do not validate all planned infrastructure. Consider modules, data sources, providers and create/update/delete/unknown values. Converting failed fmt/validate/policy/API operations to warnings or `|| true` removes the gate.

## 2. HCP Terraform

Terraform Cloud is now named **HCP Terraform**. It is an alternative to Atlantis with workspace/run/state/policy capabilities. Check the current plan and contract for features, pricing, concurrency, agents and Sentinel. Managed hosting still requires deliberate VCS, permissions, network and approval configuration.

### Workspaces and dynamic AWS credentials

This example assumes an existing organization/project, VCS OAuth connection and **agent pool** with private-network access. Agent execution requires an eligible plan and supported agent version. Do not assume a public remote runner can directly reach a private EKS API.

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

This root configures HCP resources. Protect its backend/state separately from infrastructure workspaces. Before using HCP-managed state for an existing root, decide ownership and migrate its original S3 backend deliberately. Do not apply the same state from two execution systems.

AWS must already have the `app.terraform.io` OIDC provider and scoped plan/apply roles. Restrict trust audience/subject to the exact organization/project/workspace and `run_phase:plan` or `run_phase:apply`. The `TFC_AWS_*` variables are role identifiers, not stored long-lived access keys. Verify dynamic-credential support in the actual provider and agent versions.

`queue_all_runs=false` holds VCS-triggered runs during initial workspace setup. It is not a permanent execution-disable switch after the first manual run.

### Run triggers and sharing outputs

A successful upstream apply queues a downstream run. **`auto_apply_run_trigger` is independent of ordinary `auto_apply`.** Both are false here, requiring review before apply. A trigger is neither proof that all dependencies are ready nor an output-transfer mechanism.

The example does not globally share workspace state. If outputs must be consumed, configure approved consumers/permissions and consider `tfe_outputs`. Credentials capable of reading `terraform_remote_state` can access the complete sensitive state, not just the outputs shown by the data source. Connect output access and module inputs according to the actual design.

### Sentinel policies

These are three **example policies** tested with Sentinel 0.41.0, not Python programs. A policy set, target workspaces and enforcement configuration are required before they can block HCP runs.

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

Checking `tags_all` includes AWS Provider default tags. This example checks create/update actions for the listed resource types and excludes deletion. Missing, empty, null or unknown required tags do not pass. It does not cover every AWS resource type.

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

This applies to EC2 instances and managed node groups with directly specified `instance_types`. Launch-template-only groups, Auto Mode NodePools and other compute services require additional policies. An empty or unknown type list is not treated as an approved empty set.

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

Use `tfrun.cost_estimate`, not a nonexistent path such as `tfplan.workspace`. The example allows a supplied monthly estimate up to 5,000, rejecting missing, negative, NaN and infinite values. It cannot guarantee a complete AWS bill cap covering unsupported resources, traffic and existing infrastructure.

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

Attach the policy set to the intended workspaces and separate policy administration from resource operations. A rule merely named `soft_main` does not change enforcement to soft-mandatory. Do not turn failed evaluation or API errors into success.

## 3. Flux

This section uses the reviewed [Flux 2.9.5 guide](../gitops/02-fluxcd.md). Argo CD and Flux both reconcile declarative state. Argo CD also has multiple components; Flux is not universally lighter or more isolated. Namespace separation alone does not complete tenant authorization.

Image reflector and automation controllers are **optional components**. Bootstrap commits to Git and installs controllers. Verify the CLI checksum, supported Kubernetes version, kubecontext and repository access before running it.

```bash
flux check --pre
flux bootstrap github \
  --owner=REPLACE_ORG --repository=fleet-infra --branch=main \
  --path=clusters/production --version=v2.9.5 \
  --components-extra=image-reflector-controller,image-automation-controller
```

Supply authorized GitHub credentials securely. Do not add `--personal` to an organization example. Distinguish the default bootstrap-generated `flux-system` files from infrastructure/apps directories you add yourself.

### Image automation and Git approval

The example requires a prepared Git write Secret, ECR read credentials on image-reflector-controller through Pod Identity/IRSA, and the Flux Kustomization/HelmRelease that deploys the app. Those are separate from the node's image-pull role. Do not casually combine `provider: aws` with a different registry-secret authentication path.

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

The policy assumes **immutable semver releases published after approval**. The unique SHA/build tags from [the CI chapter](03-ci-pipelines.md) do not match it. A separate promotion process must tag the approved index digest as a release, or the policy must use a reviewed monotonically increasing build scheme from one CI system.

```yaml
# fixtures/flux-values.yaml
# apps/production/application/values.yaml -- actual Helm values file
# Replace repository and initial digest with the already approved application.
image:
  repository: REPLACE_ACCOUNT.dkr.ecr.ap-northeast-2.amazonaws.com/docs-ci/application # {"$imagepolicy": "flux-system:application:name"}
  tag: "1.0.0" # {"$imagepolicy": "flux-system:application:tag"}
  digest: sha256:REPLACE_APPROVED_DIGEST # {"$imagepolicy": "flux-system:application:digest"}
```

The real application chart must use `image.repository`, `tag` and `digest` when constructing the container image URI. Adding a digest value does not make an existing chart consume it. Check that the rendered manifest points to the approved digest. Align Setters paths, policy markers and the GitRepository name.

The current ImageUpdateAutomation commit template uses **`.Changed`**. Do not replace it with the removed `.Updated`. Automation pushes to its dedicated `flux/image-updates` branch; PR creation and approval into main require another workflow. Align Git write permissions and branch protection. Tag selection does not replace vulnerability/signature verification.

### Sources, Helm and notifications

- The current examples use v1 `GitRepository`, `OCIRepository`, `Bucket` and image APIs. HelmRelease is v2; its current CRD supports both `test.enable` and `test.timeout`. Validate chart versions/values and CRDs together.
- Kustomization `dependsOn` waits for the referenced Flux object's Ready condition. Configure wait/healthChecks to observe workload health; it is not a global cross-cluster barrier.
- Do not let Terraform Helm Provider and Flux own the same Helm release simultaneously. Migrating Argo CD installation ownership requires deliberate state/configuration migration.
- Do not expose Terraform state buckets as ordinary Flux manifest sources. Use a separate manifest-artifact bucket with scoped prefix access, and avoid ignore patterns that include `.git` in artifacts.
- Store notification webhooks in Secrets and verify the actual receiver type and authentication. Test the events selected by severity and filters. Do not present an uninstalled UI or retired integration as part of the default installation.

The [Flux guide](../gitops/02-fluxcd.md) contains complete source/Kustomization/HelmRelease/notification examples.

## 4. AIOps: From Observation to Reviewable Proposals

### LLM-assisted PR review

Configure GitHub Copilot code review through its supported reviewer/automatic-review settings, with the required repository permissions and available plan. A fictional endpoint such as `api.copilot.example.com` is not an executable API example.

A custom LLM integration must implement the real service's current API/model/SDK contract, timeout, HTTP-error handling and output validation. Diffs and filenames are untrusted data. Pass structured values instead of interpolating them into shell, JavaScript or JSON strings. Instructions inside reviewed content do not grant execution authority.

Disclose truncation and API failure. Do not give secrets to external fork PRs or turn a model response alone into approval, merge or apply. Define the permitted source-code disclosure and cost scope before using an external service. No external AI service was called during this document review.

### Metric units and data quality

A CPU counter average is not CPU utilization. `rate(container_cpu_usage_seconds_total[...])` yields CPU cores; HPA `averageUtilization` is a percentage of **CPU requests**. Do not compare that percentage with RPS. Resolve the HPA's scaleTargetRef and actual Pod ownership rather than assuming the HPA and Deployment share a name.

The temporal p95 of RPS differs from a request-duration histogram quantile:

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

Match metric names/labels to actual collection. Missing series, zero traffic, NaN, stale observations and collection gaps are not evidence of health. Combine traffic, errors, latency and capacity. Mean CPU alone cannot establish an “optimal HPA target”; load tests, SLOs and scale-down behavior matter.

### Executable analysis-only example

This tool reads an already normalized single-metric JSON series from stdin and emits an **advisory report only**. It does not change APIs, HPAs, NLBs, Git or Slack. Being within the baseline does not establish application health.

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

Input contains `unit`, `periodSeconds` and `points`; each point has a UTC Unix timestamp and finite nonnegative value. Supply at least 30 baseline points plus the observation. Ratios are in 0–1. The collector must check API errors, pagination and partial results and select one clearly defined aggregate series.

The observation is excluded from the median/MAD baseline. The margins are **illustrative thresholds**, not a trained model or a seasonal forecasting system. The tool sorts points and rejects gaps, duplicates and stale observations. `review_required` is not permission to execute; `actionTaken` remains `none`.

When adapting CloudWatch collection, use the metric's actual namespace/dimensions and sort paired `Timestamps`/`Values`. Do not assume `Values[-1]` is newest with the default response order. `RequestCount` and target-group-specific metrics have different dimension contracts; handle NextToken, StatusCode and missing points.

### Approval and execution boundaries

A proposal should identify the target ARN/namespace, current configuration revision, diff, metric evidence/time, expiry, approver and rollback conditions. Before execution, re-check authorization, expiry, revision, capacity and destination health. A string allowlist or an otherwise unused guardrail ConfigMap is not an enforcement mechanism.

An approval UI needs actual request-signature verification, approver authorization, persistent state, replay protection and timeout handling. Sending Slack buttons and then waiting on an unchanged in-memory object's status is not a complete approval system. Do not claim an unimplemented executor performed an action.

Use [chapter 02's constrained proposal/optional execution flow](02-infrastructure-advanced.md) for NLB changes. Do not overwrite every listener or restore an arbitrary 100/0 split merely because no anomaly was detected. NLB weight zero closes existing connections after a short period, unlike ordinary nonzero weight adjustments.

For progressive delivery, use the services, routing and AnalysisTemplates from the [validated Argo Rollouts guide](../gitops/argocd/05-traffic-management.md). Align canary-specific metrics, arguments, namespaces, empty/NaN handling and failure conditions. Analysis failure does not automatically roll back database changes, and pause/abort settings do not solve every recovery problem.

## References

- [Atlantis security](https://www.runatlantis.io/docs/security.html)
- [Atlantis server-side policy](https://www.runatlantis.io/docs/server-side-repo-config.html)
- [HCP Terraform dynamic AWS credentials](https://developer.hashicorp.com/terraform/cloud-docs/dynamic-provider-credentials/aws-configuration)
- [HCP Terraform run triggers](https://developer.hashicorp.com/terraform/cloud-docs/workspaces/settings/run-triggers)
- [Sentinel tfrun](https://developer.hashicorp.com/terraform/cloud-docs/policy-enforcement/import-reference/tfrun)
- [Flux ImageUpdateAutomation v1](https://github.com/fluxcd/image-automation-controller/blob/v1.2.5/docs/spec/v1/imageupdateautomations.md)
- [GitHub Copilot code review](https://docs.github.com/en/copilot/how-tos/use-copilot-agents/request-a-code-review/use-code-review)
- [Chapter quiz](../quizzes/ops/05-gitops-automation-quiz.md)

< [Previous: Multi-Cluster](04-gitops-multi-cluster.md) | [Contents](README.md) | [Next: Scaling](06-scaling-strategies.md) >
