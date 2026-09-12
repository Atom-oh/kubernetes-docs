# ArgoCD 멀티클러스터 배포와 IAM Identity Center

> **검토 기준**: Argo CD 3.5.2 / Helm chart 10.8.4, Terraform 1.15.7 / Helm Provider 3.3.0, ESO 2.10.0\
> **마지막 검토**: 2026년 9월 11일. 로컬 스키마·렌더링·테스트 대역을 검증했습니다. 실제 EKS 설치, SSO 로그인과 Secrets Manager 조회는 실행하지 않았습니다.

< [이전: CI 파이프라인](03-ci-pipelines.md) | [목차](README.md) | [다음: GitOps 자동화](05-gitops-automation.md) >

이 장은 관리 EKS(Hub)의 Argo CD가 두 워크로드 EKS(Spoke)를 관리하는 구성을 다룹니다. 앞 장의 CI는 승인한 이미지 digest를 만들고, 검토된 Git 변경이 배포할 digest를 선택합니다. 중앙 관리가 각 클러스터의 인증·인가·네트워크 구성을 대신하지는 않습니다.

## 멀티클러스터 아키텍처

| 위치 | 책임 | 필요한 접근 |
|---|---|---|
| Hub의 Application Controller | 목표 상태 비교·동기화 | 대상 EKS API와 허용된 Kubernetes 리소스 |
| Hub의 Server/ApplicationSet | 사용자 요청·클러스터 관련 작업 | 기능에 필요한 대상 인증과 Hub Secret |
| Repo Server | Git·Helm source 렌더링 | 승인된 저장소와 실제 저장소 자격 증명 |
| Spoke | 애플리케이션·NodePool 실행 | 대상 IAM principal의 EKS Access Entry와 RBAC |
| ESO | 외부 값을 Kubernetes Secret으로 동기화 | 실제 ESO 컨트롤러 역할의 지정된 secret 읽기 |

Blue/Green은 클러스터 식별자입니다. 아래 예제의 워커 NodePool은 서로 다른 AZ로 제한하지만 EKS 제어 영역은 리전 서비스입니다. Hub 장애가 실행 중인 Spoke Pod를 바로 중단시키지는 않아도 배포·동기화를 멈출 수 있습니다. Hub의 광범위한 자격 증명이 탈취되면 여러 Spoke에 영향을 줄 수 있습니다. Git 이력만으로 실제 수동 변경·로그인·데이터 변경까지 모두 감사되지는 않습니다.

### 대상 클러스터의 선행 조건

1. Hub의 Application Controller 및 기능상 필요한 Server/ApplicationSet ServiceAccount에 지원되는 Pod Identity 또는 IRSA 경로를 구성합니다. Repo Server의 Git/ECR 접근과 별개입니다.
2. 관리 역할에는 **정확한 대상 역할 ARN**에 대한 `sts:AssumeRole`을 허용하고, 대상 역할은 해당 관리 역할만 신뢰하게 합니다.
3. 대상 EKS의 인증 모드를 확인하고 대상 역할의 Access Entry를 준비합니다. `demo-app` namespace의 필요한 리소스만 허용하는 access policy/RBAC와, 인프라 관리용 NodePool 권한을 구분합니다. 아래 예제에서 namespace는 미리 만듭니다.
4. Hub에서 대상 private API endpoint로의 DNS·라우팅·보안 그룹 접근을 확인합니다. IAM 권한이 있어도 네트워크가 없으면 연결되지 않습니다.

구체적인 역할·Access Entry 절차는 [Argo CD 설치](../gitops/argocd/01-installation.md)와 [EKS 접근 관리](../eks/02-eks-cluster-creation-part3.md)를 사용합니다. `aws-auth`의 `mapRoles` 전체를 덮어쓰거나 기본적으로 `system:masters`를 부여하지 않습니다.

Argo CD 3.5.2의 `awsAuthConfig.roleARN` 경로는 대상 역할을 AssumeRole하지만 별도의 ExternalId를 설정하는 필드가 없습니다. 대상 trust에 전달되지 않는 `sts:ExternalId` 조건을 넣으면 인증이 실패합니다. 그런 조건이 필요한 환경은 이를 지원하는 별도 인증 경로를 설계해야 합니다.

### 실제 endpoint로 선언적 등록

다음 스크립트를 각 대상에 대해 실행합니다. `CLUSTER_COLOR`와 대상 이름·역할을 바꾸면 서로 다른 Secret을 생성하며, kubeconfig의 기본 context를 변경하지 않습니다. 일반 namespace 접근 범위는 `demo-app`으로 제한하고 NodePool 관리를 위해 cluster resource 조회를 켭니다. 이것이 대상 RBAC 권한을 생성하는 것은 아닙니다.

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

EKS 조회 명령을 실행하는 운영자와 Hub Pod가 사용하는 역할은 별개입니다. Secret의 endpoint·CA를 가짜 EKS 호스트명으로 추측하지 않습니다. 추가 namespace가 필요하면 Secret의 `namespaces`, AppProject와 대상 권한을 함께 수정합니다. 캐시가 불필요한 리소스를 감시하지 않게 하려면 대상 RBAC와 `resource.respectRBAC` 등 Argo CD 캐시 설정도 검토합니다.

`argocd cluster add <kubeconfig-context>`는 다른 등록 방법이며 대상 ServiceAccount/RBAC를 만들 수 있습니다. 단순한 읽기 명령이 아닙니다. CLI 로그인은 대화형 또는 SSO를 사용하고 비밀번호를 명령행 인자로 넘기지 않습니다.

## ArgoCD Terraform 설치

기존 Hub EKS와 설치 권한·AWS CLI가 있는 실행 환경을 전제로 합니다. Helm Provider 3은 `kubernetes = { ... }` 객체를 사용합니다. 단기 EKS 토큰을 Terraform data source/state에 저장하는 대신 exec 인증으로 받습니다. AWS Provider에만 별도 assume_role을 설정했다면 exec의 AWS CLI도 동일한 의도된 자격 증명을 사용하도록 구성해야 합니다.

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

별도 `backend.hcl`에 [01장](01-infrastructure-setup.md)의 계정·환경별 버킷, 고유 state key, `encrypt = true`, `use_lockfile = true`를 지정합니다. `terraform init -backend-config=backend.hcl` 후 plan을 검토합니다. 예전 DynamoDB 잠금 설정이나 다른 root의 state key를 그대로 복사하지 않습니다.

같은 디렉터리에 아래 `argocd-values.yaml`을 저장합니다. [검토된 설치 가이드](../gitops/argocd/01-installation.md)의 HA 시작 구성입니다. Helm이 소유하는 ConfigMap을 별도 Terraform 리소스나 kubectl로 중복 관리하지 않습니다.

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

이 구성은 HTTPS ClusterIP이며 외부 Ingress는 끕니다. 실제 SSO에는 사용자가 접근할 수 있는 HTTPS 도메인과 정확한 라우팅이 필요합니다. [설치 가이드의 ALB 예제](../gitops/argocd/01-installation.md)를 연결할 때 backend HTTPS와 `server.insecure=false`를 맞춥니다. HTTP로 전환한다면 health check와 backend protocol도 함께 맞춰야 합니다. native gRPC와 gRPC-Web 경로도 구분합니다.

Application Controller의 여러 replica는 **클러스터 sharding**이며 모두 standby인 단일 leader 모델이 아닙니다. ApplicationSet은 별도의 leader election을 사용합니다. Server는 stateless이므로 replica가 늘었다는 이유만으로 sticky session이 필수가 되지 않습니다. Dex는 번들 저장소 구성을 고려해 기본 1개로 유지합니다.

Redis는 재구성 가능한 캐시이고 핵심 설정은 Kubernetes 객체에 있습니다. Redis HA는 모든 장애에서 무중단을 보장하지 않습니다. Replica·PDB·노드 분산과 충분한 용량을 함께 설계하며, PDB가 AZ 장애나 강제 종료까지 막는 것은 아닙니다. ServiceMonitor는 Prometheus Operator CRD가 준비된 뒤 켭니다.

## NodePool GitOps 관리

NodePool은 Kubernetes CRD여서 Argo CD로 관리할 수 있지만 Terraform으로 관리할 수 없다는 뜻은 아닙니다. 한 리소스에 하나의 소유 방식을 정합니다. 기존 built-in NodePool이나 Terraform 소유 리소스를 같은 이름으로 무심코 인수하지 않습니다.

다음은 `default` Auto Mode NodeClass가 준비된 예제입니다. 기본 NodeClass의 subnet 선택 범위와 대상 AZ가 맞아야 합니다. 아래 파일 구조를 그대로 준비합니다.

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

`kustomize build nodepools/overlays/blue`와 green을 각각 검토합니다. 표준 instance-type 조건을 사용하므로 self-managed Karpenter의 `karpenter.k8s.aws/*` 키를 Auto Mode에 섞지 않습니다. 스케줄할 Pod에도 필요한 `workload-type`/아키텍처/배치 조건을 맞춰야 합니다.

Auto Mode `NodeClass`에 self-managed `EC2NodeClass`의 `amiSelectorTerms`, `blockDeviceMappings`, `instanceStorePolicy`를 복사하지 않습니다. 커스텀 Auto Mode NodeClass에는 실제 node role·subnet·security group 선택자와 지원되는 `ephemeralStorage` 등을 사용하며, 별도 node role이면 필요한 Auto Mode node access entry도 준비합니다. DB 영속 데이터는 임시 디스크와 별도로 설계합니다. [NodePool/NodeClass 가이드](../eks-auto-mode/02-nodepool-configuration.md)를 참고합니다.

### 프로젝트와 수동 승인

다음 두 AppProject를 Hub에 생성하고 Git URL을 실제 승인된 저장소로 바꿉니다. 대상 이름은 앞의 등록 스크립트와 같습니다. 인프라 프로젝트에는 NodePool만, 애플리케이션 프로젝트에는 필요한 namespaced 종류만 허용합니다. AppProject는 Kubernetes RBAC나 비신뢰 코드의 sandbox를 대신하지 않습니다.

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

Green은 Application 이름·destination·overlay 경로를 함께 바꿉니다. NodePool 예제는 자동 동기화를 켜지 않고 변경을 먼저 검토합니다. Application에는 cascade finalizer를 넣지 않았고 NodePool에 삭제·prune 확인 옵션을 둡니다. `automated.prune=false`만으로 모든 삭제 경로가 막히는 것은 아닙니다.

NodePool 변경은 drift와 노드 교체로 이어질 수 있습니다. Disruption budget은 적용되는 자발적 중단을 제한하며 만료·Spot interruption·강제 삭제에 대한 만능 보호가 아닙니다. Auto Mode 노드 수명 제한, PDB, drain 시간과 대체 용량을 함께 고려합니다.

## ApplicationSet 전략

Generator가 만들어 내는 Application과 실제 배포 경로를 먼저 확인합니다. 예제는 기존 `demo-app` namespace를 사용합니다. Git 저장소의 application 경로에는 유효한 Kustomization과 서로 충돌하지 않는 이름의 리소스가 있어야 합니다.

### Cluster Generator

앞에서 등록한 `gitops-target=true` 클러스터만 선택합니다. 다음 Cluster 예제와 뒤의 Matrix 예제는 **대안**입니다. 같은 frontend 리소스를 두 Application에서 동시에 관리하지 않습니다.

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

`nameNormalized`는 Kubernetes 이름에 적합한 값이고 `name`은 등록된 대상 이름입니다. 하이픈이 있는 label은 Go template의 `index`로 조회합니다. Git file generator에서 읽는 설정에는 `sourcePath` 같은 이름을 사용해 generator의 `.path` 메타데이터와 충돌시키지 않습니다.

### Matrix와 Git Directory Generator

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

이 Matrix에는 **두 개의 자식 generator**가 있습니다. 두 클러스터 × 세 앱이면 조건에 맞는 조합 여섯 개를 생성합니다. 조합 generator를 무제한 깊이로 중첩할 수는 없습니다. `apps/internal` 자체를 제외하며, `apps/internal/*`만 제외해 부모 디렉터리까지 사라진다고 가정하지 않습니다.

Go template은 문자열 필드에 적용됩니다. `prune: '{{.prune}}'`처럼 boolean 필드에 문자열 템플릿을 넣거나 YAML key에 `if`를 쓰지 않습니다. boolean은 명시적으로 두고 조건부 객체가 필요하면 검증한 `templatePatch`를 사용합니다. 경로·project·destination을 외부 입력으로 자유롭게 바꾸는 템플릿은 권한 상승 경로를 만들 수 있습니다.

`preserveResourcesOnDeletion=true`는 생성 Application 삭제 시 리소스 보존을 위한 선택입니다. 기존 finalizer를 자동으로 제거하는 이행 절차가 아니며, Application의 명시적 prune·수동 삭제와도 별개입니다. Git에서 빠진 리소스를 언제 정리할지 운영 절차를 정합니다.

### 순서와 PR 프리뷰

- 한 Application의 sync wave는 해당 sync에서 리소스 적용 순서를 정합니다. ApplicationSet이 생성한 Application들에 wave 번호만 붙여도 클러스터 간 배포가 순차 실행되는 것은 아닙니다.
- 클러스터 간 승인·건강 상태 기반 진행은 별도 promotion workflow 또는 지원되는 ApplicationSet RollingSync를 사용합니다. RollingSync의 feature 설정·health gate·자동 동기화 제약은 [ApplicationSet 가이드](../gitops/argocd/04-applicationsets.md)를 따릅니다.
- PR generator는 PR 코드와 manifest를 실행할 수 있습니다. 보호된 별도 preview 클러스터·제한된 AppProject/RBAC·리소스 할당량과 검증된 이미지 digest를 사용합니다. `preview` label 하나가 신뢰 경계를 만들지 않습니다.
- PR이 닫혀 generator 결과에서 사라지면 Application 삭제 정책이 적용됩니다. `info` 필드는 TTL이 아니며 `CreateNamespace=true`로 생긴 namespace가 항상 함께 삭제되는 것도 아닙니다. finalizer·보존 정책·namespace 정리 주체를 별도로 정합니다.

실행 가능한 PR·templatePatch·RollingSync 예제는 [검토된 ApplicationSet 문서](../gitops/argocd/04-applicationsets.md)에 있습니다.

## IAM Identity Center SSO

이 장은 Argo CD 공식 Identity Center 가이드의 **SAML 2.0 + Dex** 경로를 사용합니다. Identity Center의 OAuth/trusted identity propagation 기능을 임의의 Argo CD OIDC issuer로 바꾸어 쓰지 않습니다. SAML sign-in URL은 OIDC discovery endpoint가 아닙니다.

1. IAM Identity Center **Applications**에서 자체 SAML 2.0 애플리케이션을 만듭니다.
2. 실제 도메인의 ACS URL과 audience를 `https://argocd.example.com/api/dex/callback`에 맞춥니다. 사용자/그룹을 애플리케이션에 할당합니다.
3. 해당 **애플리케이션의** sign-in URL과 서명 인증서를 받습니다. 외부 IdP를 Identity Center에 연결하는 identity-source metadata와 혼동하지 않습니다.
4. `email` 같은 필요한 사용자 속성을 지원되는 매핑으로 전달합니다. 정확한 매핑·subject·값은 실제 assertion으로 확인합니다.
5. 인증서의 BEGIN/END 줄을 포함한 전체 PEM을 base64로 인코딩해 `caData`에 넣습니다. 서명 검증을 끄지 않습니다.

다음 값을 Helm이 관리하는 `argocd-values.yaml`에 병합합니다. raw PEM·가짜 인증서·placeholder URL 상태로 로그인할 수는 없습니다.

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

이 최소 예제는 Identity Center에서 전달되는 **검증된 이메일**을 명시적으로 매핑합니다. 실제 조직이 관리하는 정확한 주소로 바꾸고 계정 변경·퇴사 시 매핑도 관리합니다. 기본 `role:authenticated`에는 권한을 주지 않았습니다. 기본 역할을 `role:readonly`로 주면 모든 로그인 사용자가 그 권한을 받으며 나중의 deny로 제거할 수 없습니다.

**그룹 할당과 groups assertion은 다릅니다.** Argo CD의 Identity Center 가이드도 그룹 attribute 매핑을 AWS 공식 지원 방식이 아닌 workaround로 설명합니다. 그룹이 자동 전달된다고 가정하거나 표시 이름과 Group ID를 혼용하지 않습니다. 그룹 기반 RBAC가 필요하면 지원되는 IdP 경로와 실제 claim을 먼저 검증하고 `groupsAttr`, `scopes`, 정책의 정확한 값을 함께 설정합니다.

Argo CD 로그인에 IAM SAML provider나 `sts:AssumeRoleWithSAML` 역할을 만드는 것은 필요하지 않습니다. 이는 AWS 역할 federation과 다른 흐름입니다. Argo CD RBAC·EKS IAM·Kubernetes RBAC도 자동으로 같은 권한이 되지 않습니다.

SSO 사용자와 최소 한 명의 승인된 관리자 및 복구 경로를 확인한 뒤에만 로컬 admin을 끕니다. Debug 로그나 SAML assertion에는 개인 정보와 인증 자료가 포함될 수 있으므로 공유 로그에 출력하지 않습니다. ACS/audience, 서명 인증서·시간, 사용자 할당, attribute, RBAC를 구분해서 진단합니다.

## 시크릿 관리

각 Spoke에 ESO 2.10.0과 v1 CRD를 설치합니다. [01장](01-infrastructure-setup.md)의 `external-secrets` namespace/ServiceAccount에 대한 Pod Identity association과 지정한 secret ARN의 읽기 권한을 재사용합니다. Hub의 역할만 연결해도 Spoke ESO가 그 권한을 받는 것은 아닙니다.

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

Pod Identity는 **실제로 실행 중인 ESO 컨트롤러**의 기본 AWS credential chain을 사용합니다. 아래 SecretStore에는 `auth.jwt.serviceAccountRef`나 IRSA annotation을 넣지 않습니다. ESO는 다른 namespace의 ServiceAccount를 지정해 그 계정의 Pod Identity를 가장할 수 없습니다.

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

`myapp/production/database`에는 username/password/host/port/dbname 필드가 있어야 하고 ESO IAM policy가 그 정확한 secret ARN을 허용해야 합니다. 고객 관리 KMS 키이면 해당 키의 복호화 권한과 key policy도 필요합니다. 예제는 검색·write 권한을 요구하지 않는 이름 기반 읽기입니다.

DB URL은 비밀번호의 `@`, `:`, `/` 등을 단순 문자열로 이어 붙이지 말고 애플리케이션의 URL builder로 구성합니다. Secret의 환경 변수 값은 이미 실행 중인 Pod에 자동 반영되지 않으므로 reload/restart 전략도 필요합니다.

namespace별 SecretStore라도 동일한 controller 역할이면 IAM 격리까지 자동으로 생기지 않습니다. 별도 controller 역할/범위 또는 검토된 `provider.aws.role` AssumeRole 경로, Store 수정 권한과 admission 정책을 함께 설계합니다. IRSA의 `auth.jwt.serviceAccountRef`는 다른 인증 방식이며 OIDC trust와 해당 SA가 필요합니다.

### 소유권·갱신·로테이션

- Git/Argo CD는 ExternalSecret을, ESO는 생성된 Secret을 소유합니다. 같은 Secret 필드를 Helm/Git/ESO가 동시에 덮어쓰지 않게 합니다. ESO CRD·controller·Store를 ExternalSecret보다 먼저 준비하고 건강 상태를 확인합니다.
- `refreshInterval`은 값을 다시 읽는 주기이며 Secrets Manager의 암호 변경·인증서 발급을 수행하지 않습니다. 회전 Lambda/네트워크/DB 권한·서비스별 회전 기능은 별도 구성입니다.
- `AWSCURRENT`와 `AWSPREVIOUS`는 version stage입니다. `AWSPREVIOUS`가 아직 없으면 이를 필수로 요청한 전체 동기화가 실패할 수 있습니다. 이전 암호가 지금도 유효하거나 DB rollback을 제공한다고 가정하지 않습니다.
- `creationPolicy: Owner`와 `deletionPolicy: Retain`은 서로 다른 수명 주기 조건입니다. 외부 값 삭제 시 retain 설정이 ExternalSecret 자체 삭제에 따른 ownerReference 정리까지 막지는 않습니다.
- `IgnoreExtraneous`는 비교 상태와 관련된 옵션이며 관리 중인 ExternalSecret을 sync/prune 대상에서 자동 제외하는 설정이 아닙니다.
- `PushSecret`은 AWS에 쓰는 기능입니다. 읽기 전용 역할로는 동작하지 않으며 create/update/tag 및 선택 기능의 추가 권한, 충돌·삭제·암호화 정책을 검토해야 합니다. 두 방향 동기화를 무심코 연결하지 않습니다.

## 확인 순서

Hub 설치와 HTTPS 접근 → 대상 역할/Access Entry/RBAC/네트워크 → 클러스터 Secret → AppProject → NodePool 수동 동기화 → ApplicationSet 생성 결과 → SSO의 실제 사용자별 허용/거부 → ESO Ready와 애플리케이션 reload 순서로 확인합니다. Secret 값을 출력하지 않고 상태·조건과 오류만 확인합니다.

## 참고 자료

- [Argo CD Identity Center SAML](https://argo-cd.readthedocs.io/en/stable/operator-manual/user-management/identity-center/)
- [IAM Identity Center 자체 SAML 애플리케이션](https://docs.aws.amazon.com/singlesignon/latest/userguide/customermanagedapps-saml2-setup.html)
- [IAM Identity Center 속성 매핑](https://docs.aws.amazon.com/singlesignon/latest/userguide/mapawsssoattributestoapp.html)
- [ESO 2.10 AWS 인증](https://external-secrets.io/v2.10.0/provider/aws-access/)
- [Helm Provider](https://registry.terraform.io/providers/hashicorp/helm/3.3.0/docs)
- [프로젝트·RBAC](../gitops/argocd/06-projects-rbac.md)
- [이 장의 퀴즈](../quizzes/ops/04-gitops-multi-cluster-quiz.md)

< [이전: CI 파이프라인](03-ci-pipelines.md) | [목차](README.md) | [다음: GitOps 자동화](05-gitops-automation.md) >
