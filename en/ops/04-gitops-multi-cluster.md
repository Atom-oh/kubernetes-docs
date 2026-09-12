# ArgoCD Multi-Cluster Deployment and IAM Identity Center

> **Review baseline**: Argo CD 3.5.2 / chart 10.8.4, Terraform 1.15.7 / Helm Provider 3.3.0, ESO 2.10.0\
> **Last reviewed**: September 11, 2026. Local schemas, rendering and test doubles were checked. No live EKS installation, SSO login or Secrets Manager read was performed.

< [Previous: CI Pipelines](03-ci-pipelines.md) | [Contents](README.md) | [Next: GitOps Automation](05-gitops-automation.md) >

This chapter uses Argo CD on a management EKS cluster (hub) to manage two workload clusters (spokes). CI produces approved image digests; reviewed Git changes select the digest to deploy. Central management does not replace each cluster's authentication, authorization and network configuration.

## Multi-Cluster Architecture

| Location | Responsibility | Required access |
|---|---|---|
| Hub Application Controller | Compare and synchronize desired state | Target EKS API and allowed Kubernetes resources |
| Hub Server/ApplicationSet | User requests and cluster-related operations | Credentials required by those features and hub Secrets |
| Repo Server | Render Git/Helm sources | Approved repositories and working repository credentials |
| Spoke | Run applications and NodePools | Target IAM principal's EKS Access Entry and RBAC |
| ESO | Synchronize external values into Kubernetes Secrets | Actual controller role's access to named secrets |

Blue and green identify clusters. The example worker NodePools are constrained to different AZs, while EKS control planes are regional. A hub failure need not immediately stop existing spoke Pods, but can stop deployment/reconciliation. Compromised hub credentials can affect multiple spokes. Git history alone does not audit every manual change, login or database operation.

### Target prerequisites

1. Configure supported Pod Identity or IRSA for the hub Application Controller and Server/ApplicationSet accounts that need target authentication. Repo Server Git/ECR access is separate.
2. Allow the management role to assume **exact target role ARNs**, and restrict each target role's trust to the intended management role.
3. Check the target EKS authentication mode and create the role's Access Entry. Separate access policies/RBAC for required `demo-app` namespace resources from cluster-scoped NodePool administration. Pre-create the namespace in this example.
4. Verify DNS, routing and security-group access from the hub to private target API endpoints. IAM permissions do not supply network connectivity.

Use the reviewed [Argo CD installation](../gitops/argocd/01-installation.md) and [EKS access management](../eks/02-eks-cluster-creation-part3.md) guides for roles and access entries. Do not replace the complete `aws-auth.mapRoles` value or default to `system:masters`.

The Argo CD 3.5.2 `awsAuthConfig.roleARN` path assumes a role but does not expose an ExternalId field. A trust condition requiring an ExternalId that this path does not send prevents authentication. Design a separate supported authentication path if that condition is required.

### Declarative registration using real endpoints

Run this script separately for each target. Changing `CLUSTER_COLOR`, cluster name and role creates separate Secrets without changing the default kubeconfig context. Namespace access is restricted to `demo-app`; cluster-resource access is enabled for NodePools. This does not grant the corresponding target RBAC permissions.

```bash
# fixtures/register-cluster.sh
#!/usr/bin/env bash
set -euo pipefail
: "${ARGOCD_CONTEXT:?Set the hub kubeconfig context}"
: "${TARGET_EKS_NAME:?Set the actual target EKS cluster name}"
: "${TARGET_AWS_REGION:?Set the target AWS region}"
: "${TARGET_ROLE_ARN:?Set the pre-authorized target role ARN}"
: "${CLUSTER_COLOR:?Set blue or green}"
case "$CLUSTER_COLOR" in blue|green) ;; *) exit 2 ;; esac
[[ "$TARGET_ROLE_ARN" =~ ^arn:aws:iam::[0-9]{12}:role/.+ ]] || exit 2
umask 077
REVIEW_TMP="$(mktemp -d)"
trap 'rm -rf -- "$REVIEW_TMP"' EXIT
aws eks describe-cluster --name "$TARGET_EKS_NAME" --region "$TARGET_AWS_REGION" \
  --query 'cluster.{name:name,server:endpoint,ca:certificateAuthority.data}' \
  --output json > "$REVIEW_TMP/cluster.json"
jq -e '(.name | type == "string" and length > 0)
  and (.server | type == "string" and startswith("https://"))
  and (.ca | type == "string" and length > 0)' "$REVIEW_TMP/cluster.json" >/dev/null
jq --arg role "$TARGET_ROLE_ARN" --arg color "$CLUSTER_COLOR" '{
  apiVersion:"v1",kind:"Secret",
  metadata:{name:("workload-"+$color),namespace:"argocd",labels:{
    "argocd.argoproj.io/secret-type":"cluster",
    "environment":"production","cluster-color":$color,"gitops-target":"true"
  }},
  type:"Opaque",
  stringData:{
    name:("workload-"+$color),server:.server,namespaces:"demo-app",
    clusterResources:"true",
    config:({
      awsAuthConfig:{clusterName:.name,roleARN:$role},
      tlsClientConfig:{insecure:false,caData:.ca}
    }|tojson)
  }
}' "$REVIEW_TMP/cluster.json" > "$REVIEW_TMP/secret.json"
kubectl --context "$ARGOCD_CONTEXT" apply -f "$REVIEW_TMP/secret.json"
```

The operator performing discovery and the role used by hub Pods are different identities. Do not invent an EKS hostname or certificate. To add namespaces, update the cluster Secret, AppProject and target permissions together. Review cache configuration such as `resource.respectRBAC` alongside target RBAC to avoid unnecessarily watching resources.

`argocd cluster add <kubeconfig-context>` is an alternative that can create target ServiceAccounts/RBAC; it is not a read-only command. Use interactive or SSO CLI login rather than a password argument.

## ArgoCD Terraform Installation

This root assumes an existing hub, installation permissions and AWS CLI in the execution environment. Helm Provider 3 uses the `kubernetes = { ... }` object syntax. Exec authentication obtains a short-lived EKS token without storing an EKS authentication data-source token in Terraform state. If only the AWS Provider assumes a role, configure its separate AWS CLI exec process to use the intended credentials too.

```hcl
# terraform/main.tf
terraform {
  required_version = ">= 1.10, < 2.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "= 6.64.0"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "= 3.3.0"
    }
  }
  backend "s3" {}
}

provider "aws" {
  region = var.aws_region
}

data "aws_eks_cluster" "hub" {
  name = var.management_cluster_name
}

provider "helm" {
  kubernetes = {
    host                   = data.aws_eks_cluster.hub.endpoint
    cluster_ca_certificate = base64decode(data.aws_eks_cluster.hub.certificate_authority[0].data)
    exec = {
      api_version = "client.authentication.k8s.io/v1beta1"
      command     = "aws"
      args        = ["eks", "get-token", "--cluster-name", var.management_cluster_name, "--region", var.aws_region]
    }
  }
}

resource "helm_release" "argocd" {
  name             = "argocd"
  namespace        = "argocd"
  create_namespace = true
  repository       = "https://argoproj.github.io/argo-helm"
  chart            = "argo-cd"
  version          = "10.8.4"
  timeout          = 900
  wait             = true
  values           = [file("${path.module}/argocd-values.yaml")]
}
```

```hcl
# terraform/variables.tf
variable "aws_region" {
  type    = string
  default = "ap-northeast-2"
}

variable "management_cluster_name" {
  type = string
  validation {
    condition     = can(regex("^[A-Za-z0-9][A-Za-z0-9_-]{0,99}$", var.management_cluster_name))
    error_message = "Use the actual EKS management cluster name."
  }
}
```

Configure a separate `backend.hcl` using the account/environment-specific bucket from [chapter 01](01-infrastructure-setup.md), a unique state key, `encrypt = true` and `use_lockfile = true`. Run `terraform init -backend-config=backend.hcl` and review the plan. Do not copy an obsolete DynamoDB-lock configuration or another root's state key.

Save this `argocd-values.yaml` beside the Terraform files. It reuses the [reviewed installation guide](../gitops/argocd/01-installation.md)'s HA starting point. Do not make another Terraform resource or kubectl workflow compete with Helm for the same ConfigMap.

```yaml
# fixtures/argocd-values.yaml
fullnameOverride: argocd
global:
  domain: argocd.example.com
configs:
  params:
    server.insecure: false
  cm:
    url: https://argocd.example.com
    users.anonymous.enabled: 'false'
    exec.enabled: 'false'
controller:
  replicas: 2
  resources:
    requests:
      cpu: 250m
      memory: 512Mi
    limits:
      cpu: '1'
      memory: 2Gi
  pdb:
    enabled: true
    minAvailable: 1
server:
  replicas: 2
  service:
    type: ClusterIP
  ingress:
    enabled: false
  resources:
    requests:
      cpu: 100m
      memory: 128Mi
    limits:
      cpu: 500m
      memory: 512Mi
  pdb:
    enabled: true
    minAvailable: 1
repoServer:
  replicas: 2
  resources:
    requests:
      cpu: 100m
      memory: 256Mi
    limits:
      cpu: '1'
      memory: 1Gi
  pdb:
    enabled: true
    minAvailable: 1
applicationSet:
  replicas: 2
  pdb:
    enabled: true
    minAvailable: 1
notifications:
  enabled: true
redis:
  enabled: false
redis-ha:
  enabled: true
  replicas: 3
  persistentVolume:
    enabled: false
  haproxy:
    enabled: true
    replicas: 3
```

The starting point exposes an HTTPS ClusterIP and disables external ingress. Real SSO requires a reachable HTTPS domain with correct routing. When adding the installation guide's ALB example, match its HTTPS backend to `server.insecure=false`. If changing to HTTP, change backend and health-check protocols together. Distinguish native gRPC from gRPC-Web routing.

Application Controller replicas implement **cluster sharding**, not a single active leader with all other replicas on standby. ApplicationSet has separate leader election. The stateless Server does not inherently require sticky sessions just because there are multiple replicas. Keep Dex at its default single replica with the bundled storage configuration.

Redis is a reconstructible cache; core configuration lives in Kubernetes objects. Redis HA does not guarantee uninterrupted operation under every failure. Design replicas, PDBs, node placement and spare capacity together; PDBs do not prevent AZ failures or all forced termination. Enable ServiceMonitor only after its Prometheus Operator CRD exists.

## NodePool GitOps Management

NodePools are Kubernetes custom resources and can be managed by Argo CD. This does not mean Terraform cannot manage them. Choose one owner per resource, and deliberately migrate ownership rather than accidentally adopting built-in or Terraform-managed resources with the same name.

The following uses an existing Auto Mode `default` NodeClass. Its subnet selectors must include the desired AZ. Create the complete file layout:

```text
nodepools/
  base/kustomization.yaml
  base/nodepool.yaml
  overlays/blue/kustomization.yaml
  overlays/green/kustomization.yaml
```

```yaml
# nodepools/base/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - nodepool.yaml
```

```yaml
# nodepools/base/nodepool.yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: workloads
  annotations:
    argocd.argoproj.io/sync-options: Prune=confirm,Delete=confirm
spec:
  template:
    metadata:
      labels:
        workload-type: applications
    spec:
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
      requirements:
        - key: kubernetes.io/arch
          operator: In
          values: [amd64, arm64]
        - key: karpenter.sh/capacity-type
          operator: In
          values: [on-demand]
        - key: node.kubernetes.io/instance-type
          operator: In
          values: [m7i.large, m7i.xlarge, m7g.large, m7g.xlarge]
  limits:
    cpu: "100"
    memory: 200Gi
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 10m
    budgets:
      - nodes: "10%"
```

```yaml
# nodepools/overlays/blue/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - ../../base
patches:
  - target:
      group: karpenter.sh
      version: v1
      kind: NodePool
      name: workloads
    patch: |
      - op: add
        path: /spec/template/metadata/labels/cluster-color
        value: blue
      - op: add
        path: /spec/template/spec/requirements/-
        value:
          key: topology.kubernetes.io/zone
          operator: In
          values: [ap-northeast-2a]
```

```yaml
# nodepools/overlays/green/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - ../../base
patches:
  - target:
      group: karpenter.sh
      version: v1
      kind: NodePool
      name: workloads
    patch: |
      - op: add
        path: /spec/template/metadata/labels/cluster-color
        value: green
      - op: add
        path: /spec/template/spec/requirements/-
        value:
          key: topology.kubernetes.io/zone
          operator: In
          values: [ap-northeast-2c]
```

Review both `kustomize build nodepools/overlays/blue` and green. Standard instance-type requirements avoid mixing self-managed Karpenter's `karpenter.k8s.aws/*` keys into Auto Mode. Match workload selectors, architecture and placement requirements to the pools.

Do not copy self-managed `EC2NodeClass` fields such as `amiSelectorTerms`, `blockDeviceMappings` or `instanceStorePolicy` into an Auto Mode `NodeClass`. Custom Auto Mode classes use actual node roles, subnet/security-group selectors and supported fields such as `ephemeralStorage`; a different node role also needs its Auto Mode node access entry. Design persistent database storage separately from ephemeral disks. See the [NodePool/NodeClass guide](../eks-auto-mode/02-nodepool-configuration.md).

### Projects and manual approval

Create these AppProjects on the hub and replace Git URLs with approved repositories. Destination names match the registration script. The infrastructure project permits NodePools; the application project allows only the required namespaced kinds. AppProjects do not replace Kubernetes RBAC or sandbox untrusted code.

```yaml
# fixtures/projects.yaml
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: infrastructure
  namespace: argocd
spec:
  sourceRepos: [https://github.com/REPLACE_ORG/infra-manifests.git]
  destinations:
    - name: workload-blue
      namespace: demo-app
    - name: workload-green
      namespace: demo-app
  clusterResourceWhitelist:
    - group: karpenter.sh
      kind: NodePool
  namespaceResourceWhitelist: []
---
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: applications
  namespace: argocd
spec:
  sourceRepos: [https://github.com/REPLACE_ORG/app-manifests.git]
  destinations:
    - name: workload-blue
      namespace: demo-app
    - name: workload-green
      namespace: demo-app
  clusterResourceWhitelist: []
  namespaceResourceWhitelist:
    - group: apps
      kind: Deployment
    - group: ""
      kind: Service
    - group: ""
      kind: ConfigMap
    - group: autoscaling
      kind: HorizontalPodAutoscaler
    - group: policy
      kind: PodDisruptionBudget
```

```yaml
# fixtures/nodepool-application.yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: nodepools-blue
  namespace: argocd
spec:
  project: infrastructure
  source:
    repoURL: https://github.com/REPLACE_ORG/infra-manifests.git
    targetRevision: main
    path: nodepools/overlays/blue
  destination:
    name: workload-blue
    namespace: demo-app
  syncPolicy:
    syncOptions:
      - ServerSideApply=true
    retry:
      limit: 3
      backoff:
        duration: 5s
        factor: 2
        maxDuration: 1m
```

For green, change the Application name, destination and overlay path together. This infrastructure example leaves automatic synchronization disabled for review. It omits an Application cascade finalizer and requires confirmation for NodePool pruning/deletion. `automated.prune=false` alone does not block every deletion path.

NodePool changes can trigger drift and node replacement. Disruption budgets constrain applicable voluntary disruption, not all expiration, Spot interruption or forced deletion. Consider Auto Mode node-lifetime limits, PDBs, drain time and replacement capacity together.

## ApplicationSet Strategies

Inspect generated Applications and their actual paths before enabling reconciliation. These examples use the existing `demo-app` namespace. Each application directory needs a valid Kustomization and resource names that do not collide.

### Cluster Generator

Select only registered clusters labeled `gitops-target=true`. This example and the following Matrix example are **alternatives**: do not let both manage the same frontend resources.

```yaml
# fixtures/cluster-appset.yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: frontend-clusters
  namespace: argocd
spec:
  goTemplate: true
  goTemplateOptions: [missingkey=error]
  syncPolicy:
    preserveResourcesOnDeletion: true
  generators:
    - clusters:
        selector:
          matchLabels:
            gitops-target: "true"
            environment: production
  template:
    metadata:
      name: '{{.nameNormalized}}-frontend'
    spec:
      project: applications
      source:
        repoURL: https://github.com/REPLACE_ORG/app-manifests.git
        targetRevision: main
        path: 'apps/frontend/overlays/{{index .metadata.labels "cluster-color"}}'
      destination:
        name: '{{.name}}'
        namespace: demo-app
      syncPolicy:
        automated:
          prune: false
          selfHeal: true
```

`nameNormalized` is suitable for Kubernetes names; `name` is the registered destination name. Use Go template `index` for label keys containing hyphens. For Git file generators, prefer a configuration field such as `sourcePath` rather than colliding with generated `.path` metadata.

### Matrix and Git Directory Generators

```yaml
# fixtures/matrix-appset.yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: application-matrix
  namespace: argocd
spec:
  goTemplate: true
  goTemplateOptions: [missingkey=error]
  syncPolicy:
    preserveResourcesOnDeletion: true
  generators:
    - matrix:
        generators:
          - clusters:
              selector:
                matchLabels:
                  gitops-target: "true"
                  environment: production
          - git:
              repoURL: https://github.com/REPLACE_ORG/app-manifests.git
              revision: main
              directories:
                - path: apps/*
                - path: apps/internal
                  exclude: true
  template:
    metadata:
      name: '{{.nameNormalized}}-{{.path.basenameNormalized}}'
    spec:
      project: applications
      source:
        repoURL: https://github.com/REPLACE_ORG/app-manifests.git
        targetRevision: main
        path: '{{.path.path}}/overlays/{{index .metadata.labels "cluster-color"}}'
      destination:
        name: '{{.name}}'
        namespace: demo-app
      syncPolicy:
        automated:
          prune: false
          selfHeal: true
```

This Matrix has **two child generators**. Two clusters and three matching apps produce six combinations. Combination generators cannot be nested to arbitrary depth. Exclude `apps/internal` itself; excluding only `apps/internal/*` does not necessarily remove its parent.

Go templates apply to string fields. Do not put a string template in a boolean field such as `prune: '{{.prune}}'`, or use an `if` expression as a YAML key. Use explicit booleans or a validated `templatePatch` for conditional objects. Letting external input freely select source paths, projects or destinations can create privilege-escalation paths.

`preserveResourcesOnDeletion=true` is a choice to preserve resources when generated Applications are deleted. It is not a migration that removes existing finalizers, and is distinct from explicit pruning or manual resource deletion. Define who cleans up resources removed from Git.

### Ordering and PR previews

- A sync wave orders resources within an Application's sync. Wave annotations on generated Applications alone do not serialize ApplicationSet deployments across clusters.
- Use a separate promotion workflow or supported ApplicationSet RollingSync for cross-cluster approval/health progression. Follow the [ApplicationSet guide](../gitops/argocd/04-applicationsets.md) for feature configuration, health gates and automatic-sync restrictions.
- PR generators can execute PR code and manifests. Use a separate protected preview cluster, constrained AppProject/RBAC, resource quotas and verified image digests. A `preview` label is not a trust boundary.
- Closing a PR removes it from generator output and invokes the configured deletion behavior. `info` is not a TTL, and a namespace created through `CreateNamespace=true` is not guaranteed to be deleted with the Application. Define finalizer, preservation and namespace-cleanup ownership.

Validated PR, templatePatch and RollingSync examples are in the [ApplicationSet chapter](../gitops/argocd/04-applicationsets.md).

## IAM Identity Center SSO

This chapter uses **SAML 2.0 with Dex**, the path documented by Argo CD for IAM Identity Center. Do not turn Identity Center's OAuth/trusted-identity-propagation functionality into an invented general-purpose Argo CD OIDC issuer. A SAML sign-in URL is not an OIDC discovery endpoint.

1. Create a customer-managed SAML 2.0 application in IAM Identity Center **Applications**.
2. Match its ACS URL and audience to `https://argocd.example.com/api/dex/callback` using the actual domain. Assign the permitted users/groups to this application.
3. Obtain this **application's** sign-in URL and signing certificate. Do not confuse these with identity-source metadata used to connect an external IdP to Identity Center.
4. Map required user attributes such as `email` using supported mappings. Verify the exact subject and attributes in an actual assertion.
5. Base64-encode the complete PEM, including BEGIN/END lines, for `caData`. Keep signature verification enabled.

Merge these settings into the Helm-owned `argocd-values.yaml`. Placeholder URLs/certificates and raw PEM in `caData` are not working authentication:

```yaml
# fixtures/sso-values.yaml
# Merge into the Helm-owned argocd-values.yaml after configuring the SAML app.
dex:
  enabled: true
configs:
  cm:
    url: https://argocd.example.com
    dex.config: |
      connectors:
        - type: saml
          id: identity-center
          name: AWS IAM Identity Center
          config:
            ssoURL: https://REPLACE_WITH_APPLICATION_SIGN_IN_URL
            caData: BASE64_OF_COMPLETE_APPLICATION_SIGNING_CERTIFICATE_PEM
            entityIssuer: https://argocd.example.com/api/dex/callback
            redirectURI: https://argocd.example.com/api/dex/callback
            usernameAttr: email
            emailAttr: email
  rbac:
    policy.default: role:authenticated
    scopes: '[email]'
    policy.csv: |
      p, role:application-viewer, applications, get, applications/*, allow
      p, role:application-operator, applications, get, applications/*, allow
      p, role:application-operator, applications, sync, applications/*, allow
      g, viewer@example.com, role:application-viewer
      g, operator@example.com, role:application-operator
```

The minimal example explicitly maps **verified email claims** from Identity Center. Replace examples with exact organization-controlled identities, and maintain mappings when accounts change or leave. The default `role:authenticated` has no permissions. A default `role:readonly` would grant those rights to every authenticated user; later deny policies cannot remove that default-role grant.

**Application group assignment is different from a groups assertion.** Argo CD's Identity Center guide itself describes group attribute mapping as a workaround not officially supported by AWS documentation. Do not assume automatic group propagation or interchange display names and Group IDs. If group RBAC is required, first verify the supported IdP path and real claims, then align `groupsAttr`, `scopes` and exact policy values.

Argo CD SSO does not require creating an IAM SAML provider or `sts:AssumeRoleWithSAML` role; that is a different AWS role-federation flow. Argo CD RBAC, EKS IAM and Kubernetes RBAC also do not automatically confer identical access.

Disable local admin only after verifying SSO users, at least one approved administrator and the recovery path. Debug logs and SAML assertions can contain personal/authentication data; do not print them into shared logs. Diagnose ACS/audience, certificate/time, assignment, attributes and RBAC separately.

## Secret Management

Install ESO 2.10.0 and its v1 CRDs on each spoke. Reuse [chapter 01](01-infrastructure-setup.md)'s Pod Identity association for namespace/ServiceAccount `external-secrets` and named-secret read permissions. A role associated only with the hub is not inherited by spoke ESO Pods.

```yaml
# fixtures/eso-values.yaml
# Reuse the existing external-secrets ServiceAccount Pod Identity association.
installCRDs: true
replicaCount: 2
leaderElect: true
serviceAccount:
  create: true
  name: external-secrets
  annotations: {}
serviceMonitor:
  enabled: false
```

```bash
helm repo add external-secrets https://charts.external-secrets.io
helm repo update
helm upgrade --install external-secrets external-secrets/external-secrets \
  --version 2.10.0 --namespace external-secrets --create-namespace \
  --kube-context "$TARGET_CONTEXT" --values eso-values.yaml
```

Pod Identity uses the default AWS credential chain of the **running ESO controller**. Do not add `auth.jwt.serviceAccountRef` or an IRSA annotation to this path. ESO cannot impersonate another namespace's ServiceAccount to acquire that account's Pod Identity association.

```yaml
# fixtures/external-secrets.yaml
apiVersion: external-secrets.io/v1
kind: SecretStore
metadata:
  name: application-config
  namespace: demo-app
spec:
  provider:
    aws:
      service: SecretsManager
      region: ap-northeast-2
---
apiVersion: external-secrets.io/v1
kind: ExternalSecret
metadata:
  name: database-credentials
  namespace: demo-app
spec:
  refreshPolicy: Periodic
  refreshInterval: 1h
  secretStoreRef:
    name: application-config
    kind: SecretStore
  target:
    name: database-credentials
    creationPolicy: Owner
    deletionPolicy: Retain
  data:
    - secretKey: username
      remoteRef:
        key: myapp/production/database
        property: username
    - secretKey: password
      remoteRef:
        key: myapp/production/database
        property: password
        version: AWSCURRENT
    - secretKey: host
      remoteRef:
        key: myapp/production/database
        property: host
    - secretKey: port
      remoteRef:
        key: myapp/production/database
        property: port
    - secretKey: database
      remoteRef:
        key: myapp/production/database
        property: dbname
```

The named `myapp/production/database` secret must contain username/password/host/port/dbname fields, and the controller's IAM policy must allow its exact ARN. A customer-managed KMS key also needs scoped decrypt permission and a compatible key policy. This is a name-based read example without discovery/write permissions.

Construct connection URLs with the application's URL builder rather than concatenating passwords containing `@`, `:` or `/`. Secret environment variables do not automatically refresh inside existing Pods; provide the application's reload/restart strategy.

Namespaced SecretStores using one controller role do not automatically provide IAM isolation. Design separate controller roles/scopes or reviewed `provider.aws.role` assumptions alongside Store modification permissions and admission policy. IRSA `auth.jwt.serviceAccountRef` is a different authentication path requiring its own OIDC trust and ServiceAccount.

### Ownership, refresh and rotation

- Git/Argo CD owns the ExternalSecret; ESO owns the generated Secret. Avoid Helm/Git/ESO repeatedly overwriting the same fields. Install the CRD/controller/Store first and verify readiness.
- `refreshInterval` reads values again; it does not rotate Secrets Manager passwords or issue certificates. Rotation functions, networking, database permissions and service-specific rotation are separate configuration.
- `AWSCURRENT` and `AWSPREVIOUS` are version stages. Requiring `AWSPREVIOUS` before it exists can fail the entire synchronization. It does not guarantee the previous password is still valid or provide a database rollback.
- `creationPolicy: Owner` and `deletionPolicy: Retain` concern different lifecycle events. Retention after an external value disappears does not override owner-reference cleanup when the ExternalSecret itself is deleted.
- `IgnoreExtraneous` affects comparison status; it does not automatically exclude a managed ExternalSecret from synchronization or pruning.
- `PushSecret` writes to AWS and does not work with a read-only role. Review create/update/tag permissions, optional-feature permissions, ownership conflicts, deletion and encryption. Do not accidentally create a two-way synchronization loop.

## Verification Order

Verify hub installation/HTTPS, target roles/Access Entries/RBAC/network, cluster Secrets, AppProjects, manually reviewed NodePools, generated Applications, real SSO allow/deny cases, and ESO readiness/application reload. Inspect status and conditions without printing Secret values.

## References

- [Argo CD Identity Center SAML](https://argo-cd.readthedocs.io/en/stable/operator-manual/user-management/identity-center/)
- [IAM Identity Center customer-managed SAML applications](https://docs.aws.amazon.com/singlesignon/latest/userguide/customermanagedapps-saml2-setup.html)
- [IAM Identity Center attribute mappings](https://docs.aws.amazon.com/singlesignon/latest/userguide/mapawsssoattributestoapp.html)
- [ESO 2.10 AWS authentication](https://external-secrets.io/v2.10.0/provider/aws-access/)
- [Helm Provider](https://registry.terraform.io/providers/hashicorp/helm/3.3.0/docs)
- [Projects and RBAC](../gitops/argocd/06-projects-rbac.md)
- [Chapter quiz](../quizzes/ops/04-gitops-multi-cluster-quiz.md)

< [Previous: CI Pipelines](03-ci-pipelines.md) | [Contents](README.md) | [Next: GitOps Automation](05-gitops-automation.md) >
