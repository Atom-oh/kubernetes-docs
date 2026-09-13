# FluxCD

> **지원 버전**: Flux 2.9.5
> **마지막 업데이트**: 2026년 9월 11일

FluxCD는 Kubernetes를 위한 개방적이고 확장 가능한 지속적 배포 및 점진적 배포 솔루션 세트입니다. FluxCD는 2022년 11월에 CNCF를 졸업하여 클라우드 네이티브 생태계에서 가장 성숙한 GitOps 도구 중 하나가 되었습니다.

이 장은 **자체 관리 Flux 2.9.5** 기준입니다. CLI 사전 검사의 최소 Kubernetes 버전은 1.33이며 실제 운영에서는 배포판의 지원 기간도 확인합니다. 2.6 이하에서 올릴 때는 2.7+ API migration 절차를 먼저 확인합니다. 아래 `OCIRepository`/`Bucket`/image API는 v1이고 Notification Provider/Alert는 v1beta3입니다.

예제는 신뢰하는 플랫폼 팀이 관리하는 `flux-system` 객체입니다. 같은 이름의 Kustomization 예제는 대안/병합 조각이며 순서대로 교체 적용하는 절차가 아닙니다. 저장소 URL·경로·namespace·Secret은 실제 환경에 맞춰 준비합니다. 테넌트에게 적용하려면 별도 namespace, `spec.serviceAccountName`에 대한 RBAC/impersonation, cross-namespace 참조 제한을 설계해야 합니다.

## 소개

FluxCD는 Git 리포지토리를 Kubernetes 클러스터의 원하는 상태를 정의하는 신뢰할 수 있는 소스로 사용하여 GitOps 원칙을 구현합니다. 소스 변경과 드리프트를 주기적으로 재조정합니다. 권한·가용성·헬스 체크 실패가 있으면 수렴이 지연되거나 실패할 수 있습니다.

### 주요 기능

- **GitOps 네이티브**: GitOps 워크플로우를 위해 처음부터 구축됨
- **멀티 테넌시**: 격리된 구성으로 여러 팀 지원
- **멀티 클러스터**: 단일 Git 리포지토리에서 여러 클러스터 관리
- **확장성**: 전문화된 컨트롤러를 갖춘 모듈식 아키텍처
- **Kubernetes 네이티브**: 구성에 Custom Resource Definitions (CRDs) 사용

## 아키텍처 개요

FluxCD는 GitOps 워크플로우를 구현하기 위해 함께 작동하는 전문화된 컨트롤러 세트로 구성됩니다:

![Flux의 외부 Git·Helm·OCI·Bucket 소스, apply/release controller, 이벤트를 받는 Notification controller와 선택 설치하는 이미지 Reflector/Automation의 역할을 구분한 아키텍처.](../.gitbook/assets/ko-gitops-02-fluxcd-0.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-gitops-02-fluxcd-0.html)

## 핵심 컴포넌트

기본 설치는 source/kustomize/helm/notification controller 네 개입니다. 이미지 자동화에는 **image-reflector-controller + image-automation-controller**를 추가해야 합니다. 선택적인 source-watcher는 ArtifactGenerator 등 소스 조합 기능에 사용합니다.

| Secret | 필요한 내용 |
|---|---|
| git-credentials | HTTPS Git의 username/password 등 인증 정보; 이미지 업데이트 시 해당 저장소 쓰기 권한도 필요 |
| registry-credentials | private ImageRepository의 kubernetes.io/dockerconfigjson Secret |
| slack-bot-token | Slack Bot OAuth token을 `token` 키에 저장 |
| github-webhook-token | GitHub webhook과 공유할 `token` |

참조한 ConfigMap/Secret은 해당 Flux 리소스와 같은 namespace에 준비합니다. 실제 값은 보호된 Secret 관리 경로로 주입하고 Git에 평문으로 넣지 않습니다.

### Source Controller

Source Controller는 외부 소스에서 아티팩트를 가져오는 역할을 합니다. 여러 소스 유형을 지원합니다:

#### GitRepository

Git 리포지토리를 추적하고 다른 컨트롤러에서 사용할 수 있도록 합니다:

```yaml
apiVersion: source.toolkit.fluxcd.io/v1
kind: GitRepository
metadata:
  name: my-app
  namespace: flux-system
spec:
  interval: 1m
  url: https://github.com/my-org/my-app
  ref:
    branch: main
  secretRef:
    name: git-credentials
```

#### HelmRepository

Helm 차트 리포지토리를 추적합니다:

```yaml
apiVersion: source.toolkit.fluxcd.io/v1
kind: HelmRepository
metadata:
  name: podinfo
  namespace: flux-system
spec:
  interval: 1h
  url: https://stefanprodan.github.io/podinfo
```

#### OCIRepository

이는 Kubernetes manifest/Helm 등 **Flux가 읽을 OCI 아티팩트** 예제입니다. 일반 컨테이너 이미지를 가져와 실행하는 설정이 아닙니다. 올바른 artifact를 미리 게시하고 tag/digest를 고정합니다.

OCI 호환 레지스트리(컨테이너 레지스트리 포함)에 저장된 아티팩트를 추적합니다:

```yaml
apiVersion: source.toolkit.fluxcd.io/v1
kind: OCIRepository
metadata:
  name: my-artifacts
  namespace: flux-system
spec:
  interval: 5m
  url: oci://ghcr.io/my-org/my-artifacts
  ref:
    tag: v1.0.0
```

#### Bucket

AWS 예제는 source-controller에 구성된 IRSA/Pod Identity 등 기본 자격 증명 체인을 전제로 합니다. 뒤의 EKS 인증 절차와 버킷 권한을 함께 준비합니다.

S3 호환 스토리지에 저장된 아티팩트를 추적합니다:

```yaml
apiVersion: source.toolkit.fluxcd.io/v1
kind: Bucket
metadata:
  name: my-bucket
  namespace: flux-system
spec:
  interval: 5m
  provider: aws
  bucketName: my-flux-bucket
  endpoint: s3.us-east-1.amazonaws.com
  region: us-east-1
```

### Kustomize Controller

Kustomize Controller는 소스에서 Kustomize 오버레이와 일반 Kubernetes 매니페스트를 적용합니다.

#### Kustomization CRD

`targetNamespace`는 namespace를 자동 생성하지 않습니다. 미리 만들거나 해당 Kustomization의 리소스에 Namespace manifest를 포함합니다. `prune: true`는 이전에 관리하던 리소스가 소스에서 사라지면 삭제할 수 있으므로 소스 경계·삭제 정책을 검토합니다.

```yaml
apiVersion: kustomize.toolkit.fluxcd.io/v1
kind: Kustomization
metadata:
  name: my-app
  namespace: flux-system
spec:
  interval: 10m
  targetNamespace: production
  sourceRef:
    kind: GitRepository
    name: my-app
  path: ./deploy/production
  prune: true
  healthChecks:
  - apiVersion: apps/v1
    kind: Deployment
    name: my-app
    namespace: production
  timeout: 2m
```

#### 변수 치환

`substituteFrom`은 뒤의 항목이 앞의 값을 덮어쓰고 inline `substitute`가 우선합니다. Secret 치환값은 렌더링된 manifest에 들어가므로 출력/권한을 관리합니다. 이 버전에 포함된 kustomize-controller 1.9.5는 `StrictPostBuildSubstitutions`가 기본 true여서 기본값 없는 누락 변수에 실패합니다. 기존 배포에서 이 gate를 false로 지정했는지도 확인합니다. 숫자 필드는 치환 후에도 Kubernetes가 기대하는 숫자 타입이어야 합니다.

FluxCD는 `postBuild`를 사용한 변수 치환을 지원합니다:

```yaml
apiVersion: kustomize.toolkit.fluxcd.io/v1
kind: Kustomization
metadata:
  name: my-app
  namespace: flux-system
spec:
  interval: 10m
  sourceRef:
    kind: GitRepository
    name: my-app
  path: ./deploy
  postBuild:
    substitute:
      ENVIRONMENT: production
      REPLICAS: '3'
    substituteFrom:
    - kind: ConfigMap
      name: cluster-config
    - kind: Secret
      name: cluster-secrets
  prune: true
  targetNamespace: production
```

#### 헬스 체크

배포된 리소스에 대한 커스텀 헬스 체크를 정의합니다:

```yaml
spec:
  healthChecks:
  - apiVersion: apps/v1
    kind: Deployment
    name: frontend
    namespace: production
  - apiVersion: apps/v1
    kind: StatefulSet
    name: database
    namespace: production
  timeout: 5m
```

### Helm Controller

Helm Controller는 Helm 차트 릴리스를 선언적으로 관리합니다.

#### HelmRelease CRD

```yaml
apiVersion: helm.toolkit.fluxcd.io/v2
kind: HelmRelease
metadata:
  name: podinfo
  namespace: flux-system
spec:
  interval: 5m
  chart:
    spec:
      chart: podinfo
      version: 6.15.0
      sourceRef:
        kind: HelmRepository
        name: podinfo
        namespace: flux-system
  targetNamespace: web
  install:
    createNamespace: true
    remediation:
      retries: 3
  upgrade:
    remediation:
      retries: 3
  values:
    replicaCount: 2
    service:
      type: ClusterIP
  releaseName: podinfo
```

#### Values 오버라이드

valuesFrom은 뒤의 참조가 앞의 값을 덮어쓰고 inline values가 우선합니다. 단, targetPath 참조는 inline 값까지 덮어쓸 수 있으므로 별도로 확인합니다.

여러 소스에서 Helm values를 오버라이드합니다:

```yaml
spec:
  valuesFrom:
  - kind: ConfigMap
    name: podinfo-values
    valuesKey: values.yaml
  - kind: Secret
    name: podinfo-secrets
    valuesKey: credentials.yaml
  values:
    replicaCount: 3
```

#### 드리프트 감지

replicas 무시는 해당 Deployment를 HPA 등 별도 controller가 관리할 때만 선택합니다. 필요 없는 ignore 규칙을 추가하면 수동 변경을 탐지하지 못할 수 있습니다.

배포된 리소스가 원하는 상태와 일치하는지 확인하기 위해 드리프트 감지를 활성화합니다:

```yaml
spec:
  driftDetection:
    mode: enabled
    ignore:
    - paths:
      - /spec/replicas
      target:
        kind: Deployment
```

### Notification Controller

Notification Controller는 인바운드 및 아웃바운드 이벤트를 처리합니다.

#### Providers

예제는 Slack Bot API 방식입니다. Bot에 chat:write 권한과 대상 채널 참여를 설정하고 channel을 실제 채널 ID로 바꿉니다. Incoming Webhook 주소를 Bot token 대신 넣지 않습니다.

알림을 위한 프로바이더를 구성합니다:

```yaml
apiVersion: notification.toolkit.fluxcd.io/v1beta3
kind: Provider
metadata:
  name: slack
  namespace: flux-system
spec:
  type: slack
  channel: C0123456789
  secretRef:
    name: slack-bot-token
  address: https://slack.com/api/chat.postMessage
```

지원되는 프로바이더:
- Slack
- Microsoft Teams Workflows (`msteams`)
- Discord
- PagerDuty
- Opsgenie (기존 고객; 2027-04-05 종료 예정)
- GitHub
- GitLab
- Grafana
- 일반 웹훅

#### Alerts

FluxCD 이벤트에 대한 알림을 정의합니다:

```yaml
apiVersion: notification.toolkit.fluxcd.io/v1beta3
kind: Alert
metadata:
  name: on-call
  namespace: flux-system
spec:
  providerRef:
    name: slack
  eventSeverity: error
  eventSources:
  - kind: GitRepository
    name: '*'
  - kind: Kustomization
    name: '*'
  - kind: HelmRelease
    name: '*'
  eventMetadata:
    summary: 클러스터 알림
```

#### Receivers (웹훅)

Receiver 생성만으로 인터넷 endpoint가 생기지는 않습니다. webhook-receiver Service에 대한 검토된 TLS ingress와 Receiver의 status.webhookPath를 조합하고 GitHub에도 동일 token을 설정합니다. type: github의 서명 검증을 유지합니다.

외부 이벤트를 위한 웹훅을 구성합니다:

```yaml
apiVersion: notification.toolkit.fluxcd.io/v1
kind: Receiver
metadata:
  name: github-receiver
  namespace: flux-system
spec:
  type: github
  events:
  - ping
  - push
  secretRef:
    name: github-webhook-token
  resources:
  - kind: GitRepository
    name: my-app
```

### Image Automation

FluxCD는 Git 리포지토리의 컨테이너 이미지 태그를 자동으로 업데이트할 수 있습니다.

#### ImageRepository

태그 스캔과 ImagePolicy 선택은 image-reflector-controller가 담당합니다. 이미지 빌드/취약점 스캔이나 워크로드의 이미지 pull을 대신하지 않습니다.

컨테이너 레지스트리에서 새 태그를 스캔합니다:

```yaml
apiVersion: image.toolkit.fluxcd.io/v1
kind: ImageRepository
metadata:
  name: my-app
  namespace: flux-system
spec:
  image: ghcr.io/my-org/my-app
  interval: 1m
  secretRef:
    name: registry-credentials
```

#### ImagePolicy

이미지 태그 선택을 위한 정책을 정의합니다:

```yaml
apiVersion: image.toolkit.fluxcd.io/v1
kind: ImagePolicy
metadata:
  name: my-app
  namespace: flux-system
  labels:
    app: my-app
spec:
  imageRepositoryRef:
    name: my-app
  policy:
    semver:
      range: '>=1.0.0 <2.0.0'
  digestReflectionPolicy: IfNotPresent
```

#### ImageUpdateAutomation

업데이트할 YAML 필드에는 policy marker가 필요합니다. `IfNotPresent`는 선택된 태그의 digest를 반영하며 서명/취약점 정책 검증을 대신하지 않습니다. 아래 automation은 전용 `flux/image-updates` 브랜치에 push합니다. main으로의 PR/승인은 별도 CI/운영 절차이며 Flux가 자동 생성하지 않습니다. 브랜치는 automation 전용으로 두고 실제 Git 인증에 쓰기 권한을 부여합니다.

```yaml
# Deployment Pod-template fragment; the policy marker is required.
spec:
  template:
    spec:
      containers:
        - name: app
          image: ghcr.io/my-org/my-app:1.0.0 # {"$imagepolicy": "flux-system:my-app"}
```

새 이미지가 감지되면 Git 커밋을 자동화합니다:

```yaml
apiVersion: image.toolkit.fluxcd.io/v1
kind: ImageUpdateAutomation
metadata:
  name: my-app
  namespace: flux-system
spec:
  interval: 30m
  sourceRef:
    kind: GitRepository
    name: my-app
  git:
    checkout:
      ref:
        branch: main
    commit:
      author:
        email: flux@my-org.com
        name: Flux
      messageTemplate: |
        자동 이미지 업데이트

        Automation: {{ .AutomationObject }}

        파일:
        {{ range $filename, $_ := .Changed.FileChanges -}}
        - {{ $filename }}
        {{ end -}}

        오브젝트:
        {{ range $resource, $changes := .Changed.Objects -}}
        - {{ $resource.Kind }} {{ $resource.Name }}
          {{- range $_, $change := $changes }}
          {{ $change.OldValue }} -> {{ $change.NewValue }}
          {{- end }}
        {{ end -}}
    push:
      branch: flux/image-updates
  update:
    path: ./deploy
    strategy: Setters
  policySelector:
    matchLabels:
      app: my-app
```

## 설치

### Flux CLI 사용

검증된 Linux amd64/arm64 릴리스 설치 예제입니다. 다른 OS는 [공식 CLI 설치 안내](https://fluxcd.io/flux/installation/#install-the-flux-cli)를 따르고 설치된 버전을 확인합니다.

```bash
set -euo pipefail
FLUX_VERSION=2.9.5
case "$(uname -m)" in
  x86_64)
    flux_arch=amd64
    flux_sha=b853df82adfd7736f580692f9f734473d571606307139f8fd20c2a80dd1ff473 ;;
  aarch64|arm64)
    flux_arch=arm64
    flux_sha=f3e159af616ec0b9bd0a405c2185cf09d06b74652c1de3c7f377e8166826651a ;;
  *) echo "Use the official installer for this architecture" >&2; exit 1 ;;
esac
flux_tmp="$(mktemp -d)"
trap 'rm -rf "$flux_tmp"' EXIT
curl -fsSL -o "$flux_tmp/flux.tar.gz" \
  "https://github.com/fluxcd/flux2/releases/download/v${FLUX_VERSION}/flux_${FLUX_VERSION}_linux_${flux_arch}.tar.gz"
printf '%s  %s\n' "$flux_sha" "$flux_tmp/flux.tar.gz" | sha256sum -c -
tar -xzf "$flux_tmp/flux.tar.gz" -C "$flux_tmp" flux
mkdir -p "$HOME/.local/bin"
install -m 0755 "$flux_tmp/flux" "$HOME/.local/bin/flux"
export PATH="$HOME/.local/bin:$PATH"
flux --version
```

### 부트스트랩

bootstrap은 Git 저장소에 구성을 기록하고 클러스터에 controller를 설치합니다. kubecontext와 저장소 권한을 먼저 확인하고 GitHub/GitLab 중 한 절차만 선택합니다. my-org는 조직/그룹이며 개인 계정일 때만 --personal을 사용합니다. 토큰은 안전하게 환경 변수로 주입합니다. 아래는 이미지 자동화 controller도 설치합니다. 같은 bootstrap 저장소를 이미지 자동화로 수정한다면 deploy key 쓰기 권한도 별도로 준비해야 합니다.

```bash
kubectl config current-context
flux check --pre

# Alternative A: GitHub organization; provide authorized GITHUB_TOKEN securely.
flux bootstrap github \
  --owner=my-org \
  --repository=fleet-infra \
  --branch=main \
  --path=clusters/production \
  --version=v2.9.5 \
  --components-extra=image-reflector-controller,image-automation-controller

# Alternative B: GitLab group; provide authorized GITLAB_TOKEN securely.
flux bootstrap gitlab \
  --owner=my-org \
  --repository=fleet-infra \
  --branch=main \
  --path=clusters/production \
  --version=v2.9.5 \
  --components-extra=image-reflector-controller,image-automation-controller
```

### 설치 확인

```bash
# Flux 컴포넌트 확인
flux check --components-extra=image-reflector-controller,image-automation-controller

# 모든 Flux 리소스 가져오기
flux get all

# 변경 사항 감시
flux get kustomizations --watch
```

## Flux로 멀티 클러스터 관리

FluxCD는 단일 리포지토리에서 여러 클러스터를 관리하는 것을 지원합니다.

### Fleet 리포지토리 구조

```
fleet-infra/
├── clusters/
│   ├── production/
│   │   ├── flux-system/
│   │   │   ├── gotk-components.yaml
│   │   │   ├── gotk-sync.yaml
│   │   │   └── kustomization.yaml
│   │   └── apps.yaml
│   ├── staging/
│   │   ├── flux-system/
│   │   │   ├── gotk-components.yaml
│   │   │   ├── gotk-sync.yaml
│   │   │   └── kustomization.yaml
│   │   └── apps.yaml
│   └── development/
│       ├── flux-system/
│       │   └── gotk-sync.yaml
│       └── apps.yaml
├── infrastructure/
│   ├── base/
│   │   ├── cert-manager/
│   │   ├── envoy-gateway/
│   │   └── monitoring/
│   └── overlays/
│       ├── production/
│       └── staging/
└── apps/
    ├── base/
    │   ├── frontend/
    │   └── backend/
    └── overlays/
        ├── production/
        └── staging/
```

### 같은 control plane의 Kustomization 의존성

dependsOn은 Flux가 관찰하는 Kustomization 객체의 Ready 상태를 기다립니다. 아래는 같은 클러스터의 두 객체이며 cross-cluster barrier가 아닙니다. infrastructure의 wait: true가 워크로드 헬스까지 기다리게 합니다. bootstrap이 만든 기본 GitRepository 이름은 flux-system이므로 이를 sourceRef로 사용합니다. 독립 클러스터마다 해당 kubecontext/경로로 bootstrap하거나, 명시적인 remote kubeConfig/권한을 구성해야 합니다. 2.9.5의 Secret kubeconfig는 certificate-authority/tokenFile/client-certificate/client-key의 로컬 파일 참조를 거부합니다. 필요한 인증서·키·토큰은 보호된 kubeconfig 안에 inline data로 제공하거나 지원되는 workload identity 구성을 사용합니다.

```yaml
apiVersion: kustomize.toolkit.fluxcd.io/v1
kind: Kustomization
metadata:
  name: infrastructure
  namespace: flux-system
spec:
  interval: 1h
  sourceRef:
    kind: GitRepository
    name: flux-system
  path: ./infrastructure/overlays/production
  prune: true
  wait: true
  timeout: 5m
---
apiVersion: kustomize.toolkit.fluxcd.io/v1
kind: Kustomization
metadata:
  name: apps
  namespace: flux-system
spec:
  dependsOn:
  - name: infrastructure
  interval: 10m
  sourceRef:
    kind: GitRepository
    name: flux-system
  path: ./apps/overlays/production
  prune: true
```

## Amazon EKS에서 FluxCD

### Controller별 AWS 인증

아래는 **controller-level IRSA** 예제입니다. EKS OIDC provider, 정확한 ServiceAccount subject와 sts.amazonaws.com audience에 대한 역할 trust, 대상 리소스 권한을 먼저 구성합니다. role ARN annotation만으로 trust/권한이 만들어지지는 않습니다. EKS Pod Identity를 선택한다면 별도의 Pod Identity association/agent 절차를 따르며 IRSA annotation과 혼동하지 않습니다.

| Controller | AWS 접근 목적 |
|---|---|
| source-controller | OCI/Helm artifact, S3 Bucket, CodeCommit Git 소스 읽기 |
| image-reflector-controller | ECR의 workload 이미지 태그/digest 스캔 |
| image-automation-controller | CodeCommit 등을 직접 clone/push하는 경우 Git 권한 |
| kustomize-controller | SOPS KMS 복호화 또는 원격 EKS 적용 |
| helm-controller | 원격 EKS에 Helm release 적용 |

서로 다른 controller의 역할을 source-controller 하나에 부여했다고 모두 공유하지는 않습니다. 멀티 테넌시는 지원되는 object-level workload identity와 해당 feature gate/ServiceAccount/RBAC 설정까지 별도로 검토합니다.

bootstrap 경로의 `flux-system/kustomization.yaml`에 다음 patch를 병합해 Git에서 관리합니다. 기존 patch/리소스 목록을 유지합니다. 이미 실행 중인 Pod는 ServiceAccount 변경만으로 IRSA 환경이 다시 주입되지 않으므로 변경 반영 후 해당 controller를 rollout합니다.

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
- gotk-components.yaml
- gotk-sync.yaml
patches:
- target:
    kind: ServiceAccount
    name: source-controller
  patch: |
    apiVersion: v1
    kind: ServiceAccount
    metadata:
      name: source-controller
      annotations:
        eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/flux-source-controller
```

```bash
kubectl rollout restart deployment/source-controller -n flux-system
kubectl rollout status deployment/source-controller -n flux-system --timeout=180s
```

### ECR의 GitOps artifact

아래 IAM 정책은 전용 gitops-artifacts repository를 읽는 source-controller용 예제입니다. GetAuthorizationToken은 repository ARN으로 제한할 수 없어 Resource는 *이고 요청 region을 제한했습니다. 콘텐츠 읽기 권한은 repository ARN으로 제한합니다. 계정/region/repository를 실제 값으로 바꿉니다.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "ecr:GetAuthorizationToken",
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "aws:RequestedRegion": "us-east-1"
        }
      }
    },
    {
      "Effect": "Allow",
      "Action": [
        "ecr:BatchCheckLayerAvailability",
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage"
      ],
      "Resource": "arn:aws:ecr:us-east-1:123456789012:repository/gitops-artifacts"
    }
  ]
}
```

```yaml
apiVersion: source.toolkit.fluxcd.io/v1
kind: OCIRepository
metadata:
  name: gitops-artifacts
  namespace: flux-system
spec:
  interval: 5m
  url: oci://123456789012.dkr.ecr.us-east-1.amazonaws.com/gitops-artifacts
  ref:
    tag: v1.0.0
  provider: aws
```

OCIRepository는 Flux가 처리할 manifest/Helm artifact를 읽습니다. 애플리케이션 이미지를 배포하는 API가 아니며, EKS node/Fargate의 실제 image pull 권한과 별개입니다. ECR ImageRepository 스캔에는 image-reflector-controller의 별도 인증과 필요한 registry 읽기 권한을 준비합니다.

### S3 Bucket 소스

전용 artifact bucket을 읽는 예제이며 controller 역할에 아래 권한을 추가합니다. 고객 관리 KMS 암호화를 쓰면 해당 키 정책과 kms:Decrypt도 검토합니다. 다른 계정의 bucket이면 bucket policy도 필요합니다.

```yaml
apiVersion: source.toolkit.fluxcd.io/v1
kind: Bucket
metadata:
  name: artifacts
  namespace: flux-system
spec:
  interval: 5m
  provider: aws
  bucketName: my-flux-artifacts
  endpoint: s3.us-east-1.amazonaws.com
  region: us-east-1
```

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "s3:ListBucket",
      "Resource": "arn:aws:s3:::my-flux-artifacts"
    },
    {
      "Effect": "Allow",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::my-flux-artifacts/*"
    }
  ]
}
```

### CodeCommit HTTPS 소스

이는 **이미 설치된 Flux의 Source 연동**입니다. bootstrap이나 IAM 자격 증명 생성을 대신하지 않습니다. source-controller 1.9.5는 provider: aws와 CodeCommit HTTPS endpoint로 IRSA/Pod Identity 인증을 사용할 수 있습니다. 아래 읽기 권한을 controller 역할에 추가하고 Kustomization의 sourceRef가 이 GitRepository 이름을 참조하도록 연결합니다.

```yaml
apiVersion: source.toolkit.fluxcd.io/v1
kind: GitRepository
metadata:
  name: codecommit-manifests
  namespace: flux-system
spec:
  interval: 1m
  provider: aws
  url: https://git-codecommit.us-east-1.amazonaws.com/v1/repos/fleet-infra
  ref:
    branch: main
```

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "codecommit:GitPull",
      "Resource": "arn:aws:codecommit:us-east-1:123456789012:fleet-infra"
    }
  ]
}
```

ImageUpdateAutomation이 CodeCommit에 push한다면 그 controller/객체 identity에도 GitPull/GitPush 권한과 전용 브랜치·PR 정책이 필요합니다. SSH 방식은 IAM에 등록한 SSH key ID 사용자명과 해당 개인키가 별도로 필요하므로, 사용자명 없이 ssh:// URL만 넣거나 CLI의 키 생성 옵션으로 IAM 등록이 된다고 가정하지 않습니다.

## 모범 사례

### 리포지토리 구조

- 소규모 팀에는 모노레포 사용
- 대규모 조직에서는 인프라와 애플리케이션을 위한 별도 리포지토리 사용
- Kustomize로 환경별 오버레이 구현

### 보안

- SOPS/Sealed Secrets 또는 External Secrets Operator로 Secret과 키 수명주기 관리
- 테넌트 namespace와 spec.serviceAccountName 기반 RBAC/impersonation 및 cross-namespace 참조 제한 구성
- receivers에 대한 웹훅 검증 활성화

### 모니터링

- 재조정 실패에 대한 알림 구성
- Prometheus로 메트릭 내보내기
- Flux 컴포넌트를 위한 대시보드 설정

### 성능

- 변경 빈도에 따라 재조정 간격 조정
- Helm 리포지토리에 캐싱 사용
- 적절한 타임아웃으로 헬스 체크 구현

## 참고 자료

- [Flux 2.9.5 release and migration notice](https://github.com/fluxcd/flux2/releases/tag/v2.9.5)
- [Flux installation](https://fluxcd.io/flux/installation/)
- [AWS integration](https://fluxcd.io/flux/integrations/aws/)
- [GitRepository v1](https://github.com/fluxcd/source-controller/blob/v1.9.5/docs/spec/v1/gitrepositories.md)
- [ImageUpdateAutomation v1](https://github.com/fluxcd/image-automation-controller/blob/v1.2.5/docs/spec/v1/imageupdateautomations.md)
- [Kustomization v1](https://github.com/fluxcd/kustomize-controller/blob/v1.9.5/docs/spec/v1/kustomizations.md)
- [Notification providers](https://github.com/fluxcd/notification-controller/blob/v1.9.4/docs/spec/v1beta3/providers.md)
- [Opsgenie lifecycle](https://www.atlassian.com/software/opsgenie)

## 퀴즈

이 장에서 배운 내용을 테스트하려면 [FluxCD 퀴즈](../quizzes/gitops/02-fluxcd-quiz.md)를 풀어보세요.
