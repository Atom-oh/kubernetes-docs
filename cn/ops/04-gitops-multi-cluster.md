# ArgoCD 多集群部署与 IAM Identity Center

> **审查基线**：Argo CD 3.5.5 / chart 10.10.5，Terraform 1.15.7 / Helm Provider 3.3.0，ESO 2.12.0\
> **最后审核**：2026年10月16日。已检查本地 schema、渲染结果和测试替身。未执行实时 EKS 安装、SSO 登录或 Secrets Manager 读取。

< [上一章：CI 流水线](03-ci-pipelines.md) | [目录](README.md) | [下一章：GitOps 自动化](05-gitops-automation.md) >

本章使用管理 EKS 集群（hub）上的 Argo CD 来管理两个工作负载集群（spoke）。CI 会生成已批准的镜像摘要；经审核的 Git 变更会选择要部署的摘要。集中管理不能取代每个集群自身的身份验证、授权和网络配置。

## 多集群架构

| 位置 | 职责 | 所需访问权限 |
|---|---|---|
| Hub Application Controller | 比较并同步期望状态 | 目标 EKS API 和获准的 Kubernetes 资源 |
| Hub Server/ApplicationSet | 用户请求和集群相关操作 | 这些功能所需的凭据以及 hub Secrets |
| Repo Server | 渲染 Git/Helm 源 | 获准的仓库和可用的仓库凭据 |
| Spoke | 运行应用程序和 NodePools | 目标 IAM 主体的 EKS Access Entry 和 RBAC |
| ESO | 将外部值同步到 Kubernetes Secrets | 实际控制器角色对指定 Secrets 的访问权限 |

蓝色和绿色用于标识集群。示例工作节点 NodePools 被限制在不同的 AZ，而 EKS 控制平面是区域级的。Hub 故障不一定会立即停止现有 spoke Pods，但可能会停止部署/协调。Hub 凭据遭到泄露可能影响多个 spoke。仅凭 Git 历史记录无法审计每一次手动变更、登录或数据库操作。

### 目标集群前提条件

1. 为需要进行目标身份验证的 hub Application Controller 和 Server/ApplicationSet 账户配置受支持的 Pod Identity 或 IRSA。Repo Server 的 Git/ECR 访问权限是独立配置的。
2. 允许管理角色代入**确切的目标角色 ARN**，并将每个目标角色的信任范围限制为预期的管理角色。
3. 检查目标 EKS 身份验证模式并创建该角色的 Access Entry。将 `demo-app` 命名空间所需资源的独立访问策略/RBAC，与集群范围的 NodePool 管理权限区分开来。本示例中请预先创建该命名空间。
4. 验证 hub 到私有目标 API 端点的 DNS、路由和安全组访问。IAM 权限不提供网络连接。

有关角色和访问条目，请使用经审核的 [Argo CD 安装指南](../gitops/argocd/01-installation.md) 和 [EKS 访问管理指南](../eks/02-eks-cluster-creation-part3.md)。不要替换完整的 `aws-auth.mapRoles` 值，也不要默认使用 `system:masters`。

Argo CD 3.5.5 的 `awsAuthConfig.roleARN` 路径会代入角色，但不提供 ExternalId 字段。如果信任条件要求该路径不会发送的 ExternalId，就会阻止身份验证。如果需要此条件，请设计独立且受支持的身份验证路径。

### 使用实际端点进行声明式注册

针对每个目标集群分别运行此脚本。更改 `CLUSTER_COLOR`、集群名称和角色会创建独立的 Secrets，同时不会更改默认 kubeconfig 上下文。命名空间访问权限仅限于 `demo-app`；集群资源访问权限已启用，以便管理 NodePools。此操作不会授予相应的目标 RBAC 权限。

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

执行发现操作的操作者与 hub Pods 使用的角色是不同的身份。不要臆造 EKS 主机名或证书。若要添加命名空间，请同时更新集群 Secret、AppProject 和目标权限。应结合目标 RBAC 检查 `resource.respectRBAC` 等缓存配置，避免监视不必要的资源。

`argocd cluster add <kubeconfig-context>` 是一种替代方式，它可以创建目标 ServiceAccounts/RBAC；但这不是只读命令。请使用交互式或 SSO CLI 登录，而不要将密码作为参数传入。

## ArgoCD Terraform 安装

此根配置假定 hub 已存在，执行环境中已具备安装权限和 AWS CLI。Helm Provider 3 使用 `kubernetes = { ... }` 对象语法。Exec 身份验证会获取短期 EKS 令牌，而不会将 EKS 身份验证数据源令牌存储在 Terraform 状态中。如果只有 AWS Provider 会代入角色，也要配置独立的 AWS CLI exec 进程，使其使用预期凭据。

```hcl
# terraform/main.tf
terraform {
  required_version = ">= 1.10, < 2.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "= 6.69.1"
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
  version          = "10.10.5"
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

配置独立的 `backend.hcl`，使用[第 01 章](01-infrastructure-setup.md)中与账户/环境对应的存储桶、唯一的 state key、`encrypt = true` 和 `use_lockfile = true`。运行 `terraform init -backend-config=backend.hcl` 并审查执行计划。不要复制过时的 DynamoDB 锁配置或其他根配置的 state key。

将此 `argocd-values.yaml` 与 Terraform 文件放在一起。它复用了[经审核的安装指南](../gitops/argocd/01-installation.md)中的 HA 起始配置。不要再创建另一个 Terraform 资源或 kubectl 工作流，与 Helm 争用同一个 ConfigMap。

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

此起始配置通过 HTTPS ClusterIP 暴露服务，并禁用外部 ingress。实际 SSO 需要可访问且路由正确的 HTTPS 域名。添加安装指南中的 ALB 示例时，应使其 HTTPS 后端与 `server.insecure=false` 相匹配。如果改用 HTTP，应同时更改后端和健康检查协议。请区分原生 gRPC 路由与 gRPC-Web 路由。

Application Controller 副本用于实现**集群分片**，而不是一个活动 Leader 加上所有其他待机副本。ApplicationSet 有独立的 Leader 选举。无状态 Server 不会仅仅因为有多个副本就必然需要会话保持。使用捆绑的存储配置时，保持 Dex 默认的单副本设置。

Redis 是可重建的缓存；核心配置存储在 Kubernetes 对象中。Redis HA 并不能保证在所有故障情况下都不中断运行。应一起设计副本、PDB、节点放置和备用容量；PDB 无法防止 AZ 故障或所有强制终止。只有在 Prometheus Operator CRD 已存在后，才启用 ServiceMonitor。

## 使用 GitOps 管理 NodePool

NodePool 是 Kubernetes 自定义资源，可以由 Argo CD 管理。这并不意味着 Terraform 不能管理它们。每个资源应选择一个所有者，并有计划地迁移所有权，避免意外接管同名的内置资源或 Terraform 管理的资源。

下面的示例使用现有的 Auto Mode `default` NodeClass。其子网选择器必须包含所需的 AZ。请创建完整的文件布局：

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

同时审查蓝色 overlay 的 `kustomize build nodepools/overlays/blue` 和绿色 overlay 的构建结果。标准实例类型要求可避免将自管 Karpenter 的 `karpenter.k8s.aws/*` 键混入 Auto Mode。工作负载选择器、架构和放置要求应与这些 NodePool 相匹配。

不要将 `amiSelectorTerms`、`blockDeviceMappings` 或 `instanceStorePolicy` 等自管 `EC2NodeClass` 字段复制到 Auto Mode `NodeClass` 中。自定义 Auto Mode 类使用实际节点角色、子网/安全组选择器以及 `ephemeralStorage` 等受支持字段；如果使用不同的节点角色，还需要相应的 Auto Mode 节点访问条目。持久数据库存储应与临时磁盘分开设计。请参阅 [NodePool/NodeClass 指南](../eks-auto-mode/02-nodepool-configuration.md)。

### 项目与手动审批

在 hub 上创建这些 AppProjects，并将 Git URL 替换为获准的仓库。目标名称与注册脚本中的名称一致。基础设施项目允许使用 NodePools；应用程序项目只允许所需的命名空间范围内的资源类型。AppProjects 不能取代 Kubernetes RBAC，也不能代替对不可信代码进行沙箱隔离。

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

对于 green，应同时更改 Application 名称、目标集群和 overlay 路径。此基础设施示例将自动同步保持为禁用状态，以供审查。它不包含 Application 级联 finalizer，并要求在清理/删除 NodePool 时进行确认。仅设置 `automated.prune=false` 并不能阻止所有删除路径。

NodePool 变更可能触发漂移和节点替换。Disruption budget 会限制适用的自愿中断，但不能限制所有过期、Spot 中断或强制删除。应综合考虑 Auto Mode 节点生命周期限制、PDB、drain 时间和替换容量。

## ApplicationSet 策略

启用协调之前，先检查生成的 Applications 及其实际路径。这些示例使用现有的 `demo-app` 命名空间。每个应用程序目录都需要有效的 Kustomization，且资源名称不能冲突。

### Cluster Generator

仅选择带有 `gitops-target=true` 标签的已注册集群。此示例与后续 Matrix 示例是**互为替代的方案**：不要让它们同时管理相同的前端资源。

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

`nameNormalized` 适用于 Kubernetes 名称；`name` 是已注册的目标名称。对于包含连字符的标签键，请使用 Go template 的 `index`。对于 Git 文件生成器，最好使用 `sourcePath` 之类的配置字段，以避免与生成的 `.path` 元数据冲突。

### Matrix 和 Git 目录生成器

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

此 Matrix 包含**两个子生成器**。两个集群和三个匹配的应用程序会产生六种组合。组合生成器不能无限嵌套。请排除 `apps/internal` 目录本身；仅排除 `apps/internal/*` 未必会移除其父目录。

Go template 适用于字符串字段。不要在 `prune: '{{.prune}}'` 这类布尔字段中放置字符串模板，也不要将 `if` 表达式用作 YAML 键。条件对象应使用明确的布尔值或经过验证的 `templatePatch`。允许外部输入自由选择源路径、项目或目标集群可能造成权限提升路径。

`preserveResourcesOnDeletion=true` 表示在删除生成的 Applications 时选择保留资源。它不会移除现有 finalizer，也不同于显式清理或手动删除资源。应明确由谁清理从 Git 中移除的资源。

### 顺序和 PR 预览

- Sync wave 用于排列单个 Application 同步中的资源。仅在生成的 Applications 上设置 wave 注解，并不能让跨集群的 ApplicationSet 部署按顺序执行。
- 对于跨集群的审批/健康状态推进，请使用独立的晋级工作流或受支持的 ApplicationSet RollingSync。有关功能配置、健康状态门控和自动同步限制，请参阅 [ApplicationSet 指南](../gitops/argocd/04-applicationsets.md)。
- PR generator 可以执行 PR 代码和清单。请使用独立且受保护的预览集群、受限的 AppProject/RBAC、资源配额和经过验证的镜像摘要。`preview` 标签不是信任边界。
- 关闭 PR 后，它会从生成器输出中移除，并触发已配置的删除行为。`info` 不是 TTL；通过 `CreateNamespace=true` 创建的命名空间也不保证会随 Application 一起删除。应明确 finalizer、资源保留和命名空间清理的责任归属。

经过验证的 PR、templatePatch 和 RollingSync 示例见 [ApplicationSet 章节](../gitops/argocd/04-applicationsets.md)。

## IAM Identity Center SSO

本章使用 **SAML 2.0 与 Dex**，这是 Argo CD 文档中针对 IAM Identity Center 的方案。不要将 Identity Center 的 OAuth/可信身份传播功能当作 Argo CD OIDC issuer 的通用方案来臆造。SAML 登录 URL 不是 OIDC 发现端点。

1. 在 IAM Identity Center **Applications** 中创建客户管理的 SAML 2.0 应用程序。
2. 根据实际域名，将其 ACS URL 和受众与 `https://argocd.example.com/api/dex/callback` 匹配。为此应用程序分配获准的用户/组。
3. 获取此**应用程序自身的**登录 URL 和签名证书。不要将这些与用于连接外部 IdP 和 Identity Center 的身份源元数据混淆。
4. 使用受支持的映射配置 `email` 等所需用户属性。通过实际断言验证确切的 subject 和属性。
5. 对完整 PEM（包括 BEGIN/END 行）进行 Base64 编码，以供 `caData` 使用。保持启用签名验证。

将这些设置合并到由 Helm 管理的 `argocd-values.yaml` 中。占位 URL/证书以及未经编码的 PEM `caData` 都无法用于身份验证：

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

这个最小示例明确映射了来自 Identity Center 的**已验证电子邮件声明**。请将示例替换为组织确切控制的身份，并在账户变更或离职时维护映射。默认的 `role:authenticated` 没有任何权限。默认使用 `role:readonly` 会将这些权限授予所有已通过身份验证的用户；后续的 deny 策略无法移除默认角色授予的权限。

**应用程序组分配与 groups 断言并不相同。** Argo CD 的 Identity Center 指南本身将组属性映射描述为一种变通方法，并指出 AWS 文档并未正式支持。不要假定组会自动传播，也不要将显示名称与 Group ID 混为一谈。如果需要基于组的 RBAC，请先验证受支持的 IdP 路径和实际声明，再使 `groupsAttr`、`scopes` 和确切的策略值保持一致。

Argo CD SSO 不需要创建 IAM SAML provider 或 `sts:AssumeRoleWithSAML` 角色；那是另一种 AWS 角色联合流程。Argo CD RBAC、EKS IAM 和 Kubernetes RBAC 也不会自动授予相同访问权限。

只有在确认 SSO 用户、至少一个获准的管理员和恢复路径后，才能禁用本地 admin。调试日志和 SAML 断言可能包含个人/身份验证数据；不要将其打印到共享日志中。应分别诊断 ACS/受众、证书/时间、分配、属性和 RBAC。

## Secret 管理

在每个 spoke 上安装 ESO 2.12.0 及其 v1 CRD。复用[第 01 章](01-infrastructure-setup.md)中为命名空间/ServiceAccount `external-secrets` 配置的 Pod Identity 关联，以及对指定 Secret 的读取权限。只关联到 hub 的角色不会传递给 spoke ESO Pods。

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
  --version 2.12.0 --namespace external-secrets --create-namespace \
  --kube-context "$TARGET_CONTEXT" --values eso-values.yaml
```

Pod Identity 使用**正在运行的 ESO 控制器**的默认 AWS 凭据链。不要为此路径添加 `auth.jwt.serviceAccountRef` 或 IRSA 注解。ESO 无法冒充另一个命名空间的 ServiceAccount 来获取该账户的 Pod Identity 关联。

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

名为 `myapp/production/database` 的 Secret 必须包含 username/password/host/port/dbname 字段，且控制器的 IAM policy 必须允许访问其确切 ARN。客户管理的 KMS key 还需要范围受限的解密权限和兼容的 key policy。这是按名称读取的示例，不包含发现/写入权限。

应使用应用程序的 URL 构建器构造连接 URL，而不是直接拼接包含 `@`、`:` 或 `/` 的密码。Secret 环境变量不会自动刷新现有 Pods 中的值；请为应用程序配置重新加载/重启策略。

使用同一个控制器角色的命名空间级 SecretStore 不会自动提供 IAM 隔离。应设计独立的控制器角色/范围，或在审核 `provider.aws.role` 角色代入配置时，同时考虑 Store 修改权限和准入策略。IRSA `auth.jwt.serviceAccountRef` 是另一种身份验证路径，需要自己的 OIDC 信任和 ServiceAccount。

### 所有权、刷新和轮换

- Git/Argo CD 管理 ExternalSecret；ESO 管理生成的 Secret。避免 Helm/Git/ESO 反复覆盖同一字段。请先安装 CRD/控制器/Store 并确认其就绪。
- `refreshInterval` 会重新读取值；它不会轮换 Secrets Manager 密码或签发证书。轮换函数、网络、数据库权限和服务专用的轮换配置是独立事项。
- `AWSCURRENT` 和 `AWSPREVIOUS` 是版本阶段。在它尚不存在时要求 `AWSPREVIOUS` 可能导致整个同步失败。它不能保证先前的密码仍然有效，也不能提供数据库回滚。
- `creationPolicy: Owner` 和 `deletionPolicy: Retain` 涉及不同的生命周期事件。当外部值消失后保留 Secret，并不会覆盖删除 ExternalSecret 时由 owner-reference 触发的清理。
- `IgnoreExtraneous` 会影响比较状态；它不会自动将受管理的 ExternalSecret 排除在同步或清理之外。
- `PushSecret` 会写入 AWS，不能与只读角色配合使用。请审核 create/update/tag 权限、可选功能权限、所有权冲突、删除和加密设置。不要意外创建双向同步循环。

## 验证顺序

依次验证 hub 安装/HTTPS、目标角色/Access Entries/RBAC/网络、集群 Secrets、AppProjects、经过手动审核的 NodePools、生成的 Applications、实际 SSO 允许/拒绝场景，以及 ESO 就绪状态/应用程序重新加载。检查状态和条件，但不要打印 Secret 值。

## 参考资料

- [Argo CD Identity Center SAML](https://argo-cd.readthedocs.io/en/stable/operator-manual/user-management/identity-center/)
- [IAM Identity Center 客户管理的 SAML 应用程序](https://docs.aws.amazon.com/singlesignon/latest/userguide/customermanagedapps-saml2-setup.html)
- [IAM Identity Center 属性映射](https://docs.aws.amazon.com/singlesignon/latest/userguide/mapawsssoattributestoapp.html)
- [ESO 2.12 AWS 身份验证](https://external-secrets.io/v2.12.0/provider/aws-access/)
- [Helm Provider](https://registry.terraform.io/providers/hashicorp/helm/3.3.0/docs)
- [Projects 和 RBAC](../gitops/argocd/06-projects-rbac.md)
- [本章测验](../quizzes/ops/04-gitops-multi-cluster-quiz.md)

< [上一章：CI 流水线](03-ci-pipelines.md) | [目录](README.md) | [下一章：GitOps 自动化](05-gitops-automation.md) >
