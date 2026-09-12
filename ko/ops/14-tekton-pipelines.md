# Tekton Pipelines: Kubernetes 네이티브 CI

> **검토일**: 2026-09-12. Pipelines 1.16.0, Triggers 0.37.0, Chains 0.29.0, Dashboard 0.72.0, tkn 0.46.0.
> **검증 범위**: 릴리스 CRD 스키마·Task 의존 관계·로컬 스크립트와 모의 도구 실행. 실제 EKS 설치, 이미지 빌드·게시, KMS 서명, 외부 Webhook/알림은 실행하지 않았습니다.

< [이전: FinOps](./13-finops-cost-platform.md) | [목차](./README.md) | [다음: 가용 영역 운영](./15-zonal-operations-guide.md) >

## 개요

Tekton은 Kubernetes API에 Task·Pipeline과 실행 인스턴스를 정의하는 CI/CD 프레임워크입니다. 컨트롤러, 실행 노드, 스토리지, 업그레이드와 접근 제어를 직접 운영합니다. 다른 CI 도구도 Kubernetes executor, 자동 확장, 공급망 증명을 지원할 수 있으므로 “Tekton만 지원한다”거나 운영 비용이 없다고 비교하지 않습니다.

이 장의 예제는 **승인된 저장소의 보호된 main 브랜치**에서 실행하는 Go 애플리케이션 CI입니다. clone → 병렬 vet/test → 후보 이미지 게시 → digest 스캔으로 끝납니다. Chains 처리와 암호학적 검증 후, 별도 담당자가 GitOps 변경을 검토합니다. 외부 fork PR에는 이 Pipeline·IRSA 역할·PVC·서명 권한을 공유하지 않습니다.

## 1. 실행 모델

| 구성 | 역할 |
| --- | --- |
| Task / Pipeline | 재사용하는 작업과 의존 관계의 정의 |
| TaskRun / PipelineRun | 파라미터와 실행 상태를 가진 인스턴스 |
| Step / Sidecar | 보통 TaskRun Pod 안에서 실행되는 순차 작업 / 보조 서비스 |
| Workspace / Result | volume 바인딩 / 작은 출력 값. 별도 CRD가 아님 |

Task 정의 자체가 Pod는 아닙니다. TaskRun이 실행되면서 Pod가 생성됩니다. Results에는 지원되는 string·array·object 타입이 있으며, 큰 보고서는 결과 필드 대신 아티팩트 저장소로 보냅니다. 같은 Pod의 Step은 네트워크와 볼륨을 공유하므로 서로 신뢰하지 않는 코드의 강한 보안 경계가 아닙니다.

![Task·Pipeline 정의와 실행 인스턴스, Workspace·Result, 별도 Chains 처리의 관계](../.gitbook/assets/ko-ops-14-tekton-pipelines-0.png)

[인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-ops-14-tekton-pipelines-0.html)

![API 서버·컨트롤러·Webhook과 실행별 Workspace를 사용하는 TaskRun Pod](../.gitbook/assets/ko-ops-14-tekton-pipelines-1.png)

[인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-ops-14-tekton-pipelines-1.html)

## 2. 설치와 실행 권한

### 2.1 버전과 설치 경로

공식 설치 문서의 최소 Kubernetes 버전은 1.28이지만, 이 장의 보안 필드와 검증 기준은 Kubernetes 1.36입니다. 최소 버전 표기는 EKS의 현재 지원 버전 추천이 아닙니다. Dashboard 0.72.0 릴리스는 Pipelines 1.15 LTS/1.16, Triggers 0.37 LTS 조합을 명시합니다.

다음은 버전이 고정된 수동 설치 예제입니다. 공식 가이드는 운영 수명 주기 관리에 Tekton Operator도 안내합니다. 기존 Operator·배포 도구가 관리하는 객체에 수동 apply를 섞지 말고 관리 주체를 먼저 결정하십시오. 아래 명령은 실제 클러스터를 변경하며, 충돌이 나면 소유권을 검토합니다.

```bash
kubectl version -o yaml
kubectl get storageclass

curl --fail --location \
  https://infra.tekton.dev/tekton-releases/pipeline/previous/v1.16.0/release.yaml \
  -o pipelines-release.yaml
kubectl apply --server-side --field-manager=tekton-install -f pipelines-release.yaml
kubectl wait --for=condition=Established --timeout=120s \
  crd/tasks.tekton.dev crd/taskruns.tekton.dev \
  crd/pipelines.tekton.dev crd/pipelineruns.tekton.dev
kubectl -n tekton-pipelines wait deployment --all \
  --for=condition=Available --timeout=300s

kubectl apply --server-side -f \
  https://infra.tekton.dev/tekton-releases/triggers/previous/v0.37.0/release.yaml
kubectl apply --server-side -f \
  https://infra.tekton.dev/tekton-releases/triggers/previous/v0.37.0/interceptors.yaml
kubectl apply --server-side -f \
  https://infra.tekton.dev/tekton-releases/chains/previous/v0.29.0/release.yaml
kubectl apply --server-side -f \
  https://infra.tekton.dev/tekton-releases/dashboard/previous/v0.72.0/release.yaml
kubectl -n tekton-pipelines port-forward service/tekton-dashboard 9097:9097
```

`release.yaml`은 Dashboard 읽기 전용 배포이고 `release-full.yaml`은 쓰기 기능을 포함합니다. 읽기 전용도 사용자를 인증하거나 namespace별 권한을 자동 적용하지는 않습니다. 운영 공개 전에 인증 proxy/OIDC와 사용자별 접근 모델을 검증합니다. 내부 ALB라는 사실만으로 인증되지는 않으며 Cognito를 연결한다면 실제 HTTPS listener·Cognito/OIDC endpoint·Secret을 맞춰야 합니다.

`https://tekton.dev/helm-charts`는 이 장에서 사용할 공식 Helm 저장소가 아닙니다. 이전 예제처럼 존재하지 않는 chart/values를 설치하지 않습니다.

### 2.2 현재 설정의 의미

| 설정 | 현재 의미 |
| --- | --- |
| `feature-flags.coschedule: workspaces` | 같은 PVC Workspace를 쓰는 TaskRun의 배치. RWO 예제에서 유지 |
| `disable-affinity-assistant` | v0.68 이후 제거된 예전 플래그 |
| `set-security-context: true` | 1.16 기본값. Tekton 주입 컨테이너에 적용하며 사용자 Step의 정책 적합성은 별도 |
| `results-from: termination-message` | 기본 경로. Kubernetes 종료 메시지 크기의 제한을 받음 |
| `max-result-size` | `sidecar-logs` 결과 경로에 관한 설정. 기본 종료 메시지 한도를 이 값만으로 늘리지 않음 |
| 기본 timeout | `config-defaults`에서 관리. 이 예제는 PipelineRun에 명시 |

`running-in-environment-with-injected-sidecars`는 Workspace 격리 설정이 아니고 `keep-pod-on-cancel`은 오래된 PipelineRun을 정리하는 TTL도 아닙니다. 전체 ConfigMap을 작은 발췌로 덮어쓰지 않습니다.

### 2.3 ServiceAccount와 IAM 분리

컨트롤러는 `tekton-pipelines`/`tekton-chains`, 빌드는 `tekton-builds`에 둡니다. Task/ Pipeline의 단순 이름 참조는 같은 namespace에서 찾습니다. 공통 namespace의 Task를 이름만으로 참조할 수 있다고 가정하지 않습니다.

아래 IAM 역할은 먼저 생성해야 합니다. 각 IRSA 신뢰 정책에서 기존 클러스터 OIDC provider, `aud=sts.amazonaws.com`, 정확한 `sub=system:serviceaccount:tekton-builds:<SA 이름>`을 제한합니다. ECR 리포지터리는 플랫폼에서 미리 생성하고 빌드에 `CreateRepository`를 주지 않습니다. `ci-readonly`는 이름과 달리 Kubernetes 읽기 Role을 부여한 계정이 아니라, 이 예제에서 API 권한을 부여하지 않는 기본 실행 계정입니다.

**`service-accounts.yaml`**

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: tekton-builds
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: ci-readonly
  namespace: tekton-builds
automountServiceAccountToken: false
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: ci-image-push
  namespace: tekton-builds
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/tekton-candidate-push
automountServiceAccountToken: false
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: ci-image-read
  namespace: tekton-builds
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/tekton-candidate-read
automountServiceAccountToken: false
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: ci-triggers
  namespace: tekton-builds
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: ci-triggers
  namespace: tekton-builds
rules:
  - apiGroups: [triggers.tekton.dev]
    resources: [eventlisteners, triggers, triggerbindings, triggertemplates, interceptors]
    verbs: [get, list, watch]
  - apiGroups: [tekton.dev]
    resources: [pipelineruns]
    verbs: [create]
  - apiGroups: [""]
    resources: [configmaps]
    verbs: [get, list, watch]
  - apiGroups: [""]
    resources: [secrets]
    resourceNames: [github-webhook]
    verbs: [get]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: ci-triggers
  namespace: tekton-builds
subjects:
  - kind: ServiceAccount
    name: ci-triggers
    namespace: tekton-builds
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: ci-triggers
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: ci-triggers-interceptors
rules:
  - apiGroups: [triggers.tekton.dev]
    resources: [clusterinterceptors, clustertriggerbindings]
    verbs: [get, list, watch]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: ci-triggers-interceptors
subjects:
  - kind: ServiceAccount
    name: ci-triggers
    namespace: tekton-builds
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: ci-triggers-interceptors
```

**`ecr-push-policy.json`**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "ecr:GetAuthorizationToken",
      "Resource": "*",
      "Condition": {
        "StringEquals": {"aws:RequestedRegion": "ap-northeast-2"}
      }
    },
    {
      "Effect": "Allow",
      "Action": [
        "ecr:BatchCheckLayerAvailability",
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage",
        "ecr:InitiateLayerUpload",
        "ecr:UploadLayerPart",
        "ecr:CompleteLayerUpload",
        "ecr:PutImage"
      ],
      "Resource": "arn:aws:ecr:ap-northeast-2:123456789012:repository/myapp-candidates"
    }
  ]
}
```

**`ecr-read-policy.json`**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "ecr:GetAuthorizationToken",
      "Resource": "*",
      "Condition": {
        "StringEquals": {"aws:RequestedRegion": "ap-northeast-2"}
      }
    },
    {
      "Effect": "Allow",
      "Action": [
        "ecr:BatchCheckLayerAvailability",
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage"
      ],
      "Resource": "arn:aws:ecr:ap-northeast-2:123456789012:repository/myapp-candidates"
    }
  ]
}
```

Push 정책은 `tekton-candidate-push`, Read 정책은 `tekton-candidate-read`에 연결합니다. 계정·리전·리포지터리를 모두 바꿉니다. `GetAuthorizationToken`은 repository별 Resource 제한을 지원하지 않으므로 별도 statement에서 요청 리전을 제한합니다.

IRSA는 Pod 안의 AWS SDK/CLI 인증입니다. kubelet의 ECR 이미지 pull 권한은 노드 역할·Fargate 실행 역할·imagePullSecrets 등 별도의 경로입니다. `ImagePullBackOff`를 Task IRSA annotation만으로 해결하려 하지 않습니다.

## 3. 실행 가능한 Task 정의

다음 여섯 Task는 서로 참조가 맞는 하나의 예제입니다. 소스 저장소에는 Go module·테스트·Dockerfile이 있어야 합니다. `checkout`의 고정 URL `myorg/myapp`을 승인된 실제 저장소로 바꾸고 Trigger의 allowlist도 같은 값으로 맞춥니다. 임의 Git URL·셸 명령을 Webhook 입력으로 받지 않습니다.

Tekton 치환은 문자열 대체입니다. params를 script 본문에 직접 삽입하지 않고 환경 변수나 인수로 전달합니다. 커밋은 40자리 SHA로 검사하고, ECR 인증은 Task의 `emptyDir`에 저장합니다. 읽기 전용 Secret volume에 로그인 파일을 쓰거나 다른 Step의 이미지에 도구가 있을 것이라고 가정하지 않습니다.

BuildKit rootless 예제는 전용 빌드 환경의 user namespace·mount·seccomp/AppArmor 설정 검증이 필요합니다. `Unconfined`와 `--oci-worker-no-process-sandbox`는 명시적인 보안 절충이며 제한된 namespace 정책에서는 거부됩니다. 이를 모든 클러스터에 적용 가능한 안전한 기본값으로 취급하지 않습니다. 외부 PR에는 별도 실행 환경을 사용합니다.

**`tasks.yaml`**

```yaml
apiVersion: tekton.dev/v1
kind: Task
metadata:
  name: checkout
  namespace: tekton-builds
spec:
  params:
  - name: revision
    type: string
  workspaces:
  - name: source
  results:
  - name: CHAINS-GIT_URL
    type: string
  - name: CHAINS-GIT_COMMIT
    type: string
  steps:
  - name: checkout
    image: golang:1.27.1
    script: |
      #!/usr/bin/env bash
      set -euo pipefail
      if [[ ! "$REVISION" =~ ^[0-9a-f]{40}$ ]]; then
        echo "Expected a full commit SHA" >&2
        exit 1
      fi
      cd "$SOURCE"
      git init .
      git config credential.helper ''
      git remote add origin "$REPOSITORY"
      git -c protocol.file.allow=never fetch --depth=1 origin "$REVISION"
      git -c advice.detachedHead=false checkout --detach FETCH_HEAD
      test "$(git rev-parse HEAD)" = "$REVISION"
      printf '%s' "$REPOSITORY" > "$GIT_URL_RESULT"
      printf '%s' "$REVISION" > "$GIT_COMMIT_RESULT"
    env:
    - name: REVISION
      value: $(params.revision)
    - name: REPOSITORY
      value: https://github.com/myorg/myapp.git
    - name: SOURCE
      value: $(workspaces.source.path)
    - name: GIT_URL_RESULT
      value: $(results.CHAINS-GIT_URL.path)
    - name: GIT_COMMIT_RESULT
      value: $(results.CHAINS-GIT_COMMIT.path)
    computeResources:
      requests:
        cpu: 100m
        memory: 128Mi
      limits:
        memory: 1Gi
  stepTemplate:
    securityContext:
      runAsUser: 1000
      runAsGroup: 1000
---
apiVersion: tekton.dev/v1
kind: Task
metadata:
  name: go-vet
  namespace: tekton-builds
spec:
  params: []
  workspaces:
  - name: source
  results: []
  steps:
  - name: vet
    image: golang:1.27.1
    script: |
      #!/usr/bin/env bash
      set -euo pipefail
      cd "$SOURCE"
      go vet ./...
    env:
    - name: SOURCE
      value: $(workspaces.source.path)
    - name: GOCACHE
      value: /tmp/go-build
    - name: GOMODCACHE
      value: /tmp/go-mod
    computeResources:
      requests:
        cpu: 100m
        memory: 128Mi
      limits:
        memory: 1Gi
  stepTemplate:
    securityContext:
      runAsUser: 1000
      runAsGroup: 1000
---
apiVersion: tekton.dev/v1
kind: Task
metadata:
  name: go-test
  namespace: tekton-builds
spec:
  params: []
  workspaces:
  - name: source
  results: []
  steps:
  - name: test
    image: golang:1.27.1
    script: |
      #!/usr/bin/env bash
      set -euo pipefail
      cd "$SOURCE"
      go test -count=1 -race -coverprofile=/tmp/coverage.out ./...
      go tool cover -func=/tmp/coverage.out
    env:
    - name: SOURCE
      value: $(workspaces.source.path)
    - name: GOCACHE
      value: /tmp/go-build
    - name: GOMODCACHE
      value: /tmp/go-mod
    computeResources:
      requests:
        cpu: 100m
        memory: 128Mi
      limits:
        memory: 1Gi
  stepTemplate:
    securityContext:
      runAsUser: 1000
      runAsGroup: 1000
---
apiVersion: tekton.dev/v1
kind: Task
metadata:
  name: build-image
  namespace: tekton-builds
spec:
  params:
  - name: image
    type: string
  - name: revision
    type: string
  - name: region
    type: string
  workspaces:
  - name: source
  results:
  - name: IMAGE_URL
    type: string
  - name: IMAGE_DIGEST
    type: string
  steps:
  - name: ecr-token
    image: public.ecr.aws/aws-cli/aws-cli:2.36.44
    script: |
      #!/bin/bash
      set -euo pipefail
      umask 077
      aws ecr get-authorization-token --region "$AWS_REGION" \
        --query 'authorizationData[0].authorizationToken' --output text > /auth/token
    env:
    - name: AWS_REGION
      value: $(params.region)
    - name: AWS_DEFAULT_REGION
      value: $(params.region)
    computeResources:
      requests:
        cpu: 100m
        memory: 128Mi
      limits:
        memory: 1Gi
    volumeMounts:
    - name: auth
      mountPath: /auth
  - name: docker-config
    image: python:3.12.13-slim
    script: |
      #!/usr/bin/env python3
      import base64, json, os, re
      from pathlib import Path
      image, region = os.environ["IMAGE"], os.environ["REGION"]
      match = re.fullmatch(r"([0-9]{12})\.dkr\.ecr\.([a-z0-9-]+)\.amazonaws\.com/([a-z0-9][a-z0-9._/-]*)", image)
      if not match or match.group(2) != region or ".." in match.group(3):
          raise SystemExit("Use a private ECR repository in the configured region")
      token = Path("/auth/token").read_text().strip()
      decoded = base64.b64decode(token, validate=True)
      if not decoded.startswith(b"AWS:") or len(decoded) <= 4:
          raise SystemExit("Invalid ECR authorization token")
      Path("/auth/config.json").write_text(json.dumps({"auths": {image.split("/")[0]: {"auth": token}}}))
      Path("/auth/config.json").chmod(0o600)
      Path("/auth/token").unlink()
    env:
    - name: IMAGE
      value: $(params.image)
    - name: REGION
      value: $(params.region)
    computeResources:
      requests:
        cpu: 100m
        memory: 128Mi
      limits:
        memory: 1Gi
    volumeMounts:
    - name: auth
      mountPath: /auth
  - name: build-and-push
    image: moby/buildkit:v0.33.0-rootless
    script: |
      #!/bin/sh
      set -eu
      case "$REVISION" in *[!0-9a-f]*|"") echo "Invalid commit tag" >&2; exit 1;; esac
      test "${#REVISION}" -eq 40
      buildctl-daemonless.sh build \
        --frontend dockerfile.v0 \
        --local "context=$SOURCE" --local "dockerfile=$SOURCE" \
        --output "type=image,name=$IMAGE:$REVISION,push=true" \
        --metadata-file /build-result/metadata.json
    env:
    - name: SOURCE
      value: $(workspaces.source.path)
    - name: IMAGE
      value: $(params.image)
    - name: REVISION
      value: $(params.revision)
    - name: DOCKER_CONFIG
      value: /auth
    - name: BUILDKITD_FLAGS
      value: --oci-worker-no-process-sandbox
    computeResources:
      requests:
        cpu: '1'
        memory: 1Gi
      limits:
        memory: 4Gi
    securityContext:
      runAsUser: 1000
      runAsGroup: 1000
      seccompProfile:
        type: Unconfined
      appArmorProfile:
        type: Unconfined
    volumeMounts:
    - name: auth
      mountPath: /auth
      readOnly: true
    - name: buildkit-state
      mountPath: /home/user/.local/share/buildkit
    - name: build-result
      mountPath: /build-result
  - name: record-digest
    image: python:3.12.13-slim
    script: |
      #!/usr/bin/env python3
      import json, os, re
      from pathlib import Path
      data = json.loads(Path("/build-result/metadata.json").read_text())
      digest = data.get("containerimage.digest", "")
      if not re.fullmatch(r"sha256:[0-9a-f]{64}", digest):
          raise SystemExit("BuildKit did not return an image digest")
      Path(os.environ["URL_RESULT"]).write_text(os.environ["IMAGE"])
      Path(os.environ["DIGEST_RESULT"]).write_text(digest)
    env:
    - name: IMAGE
      value: $(params.image)
    - name: URL_RESULT
      value: $(results.IMAGE_URL.path)
    - name: DIGEST_RESULT
      value: $(results.IMAGE_DIGEST.path)
    computeResources:
      requests:
        cpu: 100m
        memory: 128Mi
      limits:
        memory: 1Gi
    volumeMounts:
    - name: build-result
      mountPath: /build-result
      readOnly: true
  volumes:
  - name: auth
    emptyDir: {}
  - name: buildkit-state
    emptyDir: {}
  - name: build-result
    emptyDir: {}
  stepTemplate:
    securityContext:
      runAsUser: 1000
      runAsGroup: 1000
---
apiVersion: tekton.dev/v1
kind: Task
metadata:
  name: scan-image
  namespace: tekton-builds
spec:
  params:
  - name: image
    type: string
  - name: digest
    type: string
  - name: region
    type: string
  workspaces: []
  results: []
  steps:
  - name: ecr-token
    image: public.ecr.aws/aws-cli/aws-cli:2.36.44
    script: |
      #!/bin/bash
      set -euo pipefail
      umask 077
      aws ecr get-authorization-token --region "$AWS_REGION" \
        --query 'authorizationData[0].authorizationToken' --output text > /auth/token
    env:
    - name: AWS_REGION
      value: $(params.region)
    - name: AWS_DEFAULT_REGION
      value: $(params.region)
    computeResources:
      requests:
        cpu: 100m
        memory: 128Mi
      limits:
        memory: 1Gi
    volumeMounts:
    - name: auth
      mountPath: /auth
  - name: docker-config
    image: python:3.12.13-slim
    script: |
      #!/usr/bin/env python3
      import base64, json, os, re
      from pathlib import Path
      image, region = os.environ["IMAGE"], os.environ["REGION"]
      match = re.fullmatch(r"([0-9]{12})\.dkr\.ecr\.([a-z0-9-]+)\.amazonaws\.com/([a-z0-9][a-z0-9._/-]*)", image)
      if not match or match.group(2) != region or ".." in match.group(3):
          raise SystemExit("Use a private ECR repository in the configured region")
      token = Path("/auth/token").read_text().strip()
      decoded = base64.b64decode(token, validate=True)
      if not decoded.startswith(b"AWS:") or len(decoded) <= 4:
          raise SystemExit("Invalid ECR authorization token")
      Path("/auth/config.json").write_text(json.dumps({"auths": {image.split("/")[0]: {"auth": token}}}))
      Path("/auth/config.json").chmod(0o600)
      Path("/auth/token").unlink()
    env:
    - name: IMAGE
      value: $(params.image)
    - name: REGION
      value: $(params.region)
    computeResources:
      requests:
        cpu: 100m
        memory: 128Mi
      limits:
        memory: 1Gi
    volumeMounts:
    - name: auth
      mountPath: /auth
  - name: scan
    image: aquasec/trivy:0.74.0
    script: |
      #!/bin/sh
      set -eu
      trivy image --scanners vuln --severity HIGH,CRITICAL \
        --exit-code 1 --format json --output /tmp/trivy-report.json "$IMAGE@$DIGEST"
    env:
    - name: IMAGE
      value: $(params.image)
    - name: DIGEST
      value: $(params.digest)
    - name: DOCKER_CONFIG
      value: /auth
    - name: TRIVY_CACHE_DIR
      value: /tmp/trivy-cache
    computeResources:
      requests:
        cpu: 100m
        memory: 128Mi
      limits:
        memory: 1Gi
    volumeMounts:
    - name: auth
      mountPath: /auth
      readOnly: true
  volumes:
  - name: auth
    emptyDir: {}
  stepTemplate:
    securityContext:
      runAsUser: 1000
      runAsGroup: 1000
---
apiVersion: tekton.dev/v1
kind: Task
metadata:
  name: report-status
  namespace: tekton-builds
spec:
  params:
  - name: run
    type: string
  - name: status
    type: string
  workspaces: []
  results: []
  steps:
  - name: report
    image: python:3.12.13-slim
    script: |
      #!/usr/bin/env python3
      import json, os
      print(json.dumps({"pipelineRun": os.environ["RUN"], "status": os.environ["STATUS"]}))
    env:
    - name: RUN
      value: $(params.run)
    - name: STATUS
      value: $(params.status)
    computeResources:
      requests:
        cpu: 100m
        memory: 128Mi
      limits:
        memory: 1Gi
  stepTemplate:
    securityContext:
      runAsUser: 1000
      runAsGroup: 1000
```

Google Kaniko 원본 저장소는 보관 상태이므로 새 예제는 BuildKit 0.33.0을 사용합니다. rootless도 완전한 프로세스 격리를 보장하지 않습니다. 프로덕션에서는 Step image의 digest·아키텍처를 확인해 고정하고, 도구별 writable path와 securityContext를 실제 노드에서 검증합니다.

스캐너 exit code 1은 취약점 발견, 다른 오류도 실패로 처리합니다. 실패한 스캔의 보고서가 없다는 이유로 “취약점 0”으로 바꾸지 않습니다. `/tmp/trivy-report.json`은 임시 파일이므로 장기 보관이 필요하면 실행 종료 전에 승인된 아티팩트 저장소로 내보내야 합니다.

## 4. Pipeline과 실행

![clone 후 병렬 테스트·정적 검사, 후보 이미지 게시·스캔과 조건부 종료 리포트](../.gitbook/assets/ko-ops-14-tekton-pipelines-2.png)

[인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-ops-14-tekton-pipelines-2.html)

**`pipeline.yaml`**

```yaml
apiVersion: tekton.dev/v1
kind: Pipeline
metadata:
  name: trusted-image-ci
  namespace: tekton-builds
spec:
  params:
    - name: revision
      type: string
    - name: image
      type: string
    - name: region
      type: string
      default: ap-northeast-2
  workspaces:
    - name: source
  results:
    - name: CHAINS-GIT_URL
      value: $(tasks.clone.results.CHAINS-GIT_URL)
    - name: CHAINS-GIT_COMMIT
      value: $(tasks.clone.results.CHAINS-GIT_COMMIT)
    - name: IMAGE_URL
      value: $(tasks.build.results.IMAGE_URL)
    - name: IMAGE_DIGEST
      value: $(tasks.build.results.IMAGE_DIGEST)
  tasks:
    - name: clone
      taskRef:
        name: checkout
      params:
        - name: revision
          value: $(params.revision)
      workspaces:
        - name: source
          workspace: source
    - name: lint
      runAfter: [clone]
      taskRef:
        name: go-vet
      workspaces:
        - name: source
          workspace: source
    - name: test
      runAfter: [clone]
      taskRef:
        name: go-test
      workspaces:
        - name: source
          workspace: source
    - name: build
      runAfter: [lint, test]
      taskRef:
        name: build-image
      params:
        - name: image
          value: $(params.image)
        - name: revision
          value: $(tasks.clone.results.CHAINS-GIT_COMMIT)
        - name: region
          value: $(params.region)
      workspaces:
        - name: source
          workspace: source
    - name: scan
      runAfter: [build]
      taskRef:
        name: scan-image
      params:
        - name: image
          value: $(tasks.build.results.IMAGE_URL)
        - name: digest
          value: $(tasks.build.results.IMAGE_DIGEST)
        - name: region
          value: $(params.region)
  finally:
    - name: report
      taskRef:
        name: report-status
      params:
        - name: run
          value: $(context.pipelineRun.name)
        - name: status
          value: $(tasks.status)
```

**`pipelinerun.yaml`**

```yaml
apiVersion: tekton.dev/v1
kind: PipelineRun
metadata:
  generateName: trusted-image-ci-
  namespace: tekton-builds
spec:
  pipelineRef:
    name: trusted-image-ci
  params:
    - name: revision
      value: REPLACE_WITH_FULL_40_CHARACTER_COMMIT_SHA
    - name: image
      value: 123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/myapp-candidates
  workspaces:
    - name: source
      volumeClaimTemplate:
        spec:
          accessModes: [ReadWriteOnce]
          storageClassName: gp3
          resources:
            requests:
              storage: 10Gi
  taskRunTemplate:
    serviceAccountName: ci-readonly
    podTemplate:
      automountServiceAccountToken: false
      securityContext:
        fsGroup: 1000
  taskRunSpecs:
    - pipelineTaskName: build
      serviceAccountName: ci-image-push
    - pipelineTaskName: scan
      serviceAccountName: ci-image-read
  timeouts:
    pipeline: 1h
    tasks: 50m
    finally: 5m
```

```bash
kubectl apply -f service-accounts.yaml
kubectl apply -f tasks.yaml -f pipeline.yaml
# Replace the commit placeholder and provision the referenced IAM roles first.
kubectl create -f pipelinerun.yaml
tkn pipelinerun logs --last -n tekton-builds --follow --exit-with-pipelinerun-error
```

생성되는 PVC는 실행마다 새로 만들어집니다. `ReadWriteOnce`는 같은 노드의 여러 Pod가 접근할 수 있지만 다중 노드 RWX가 아닙니다. `emptyDir`를 서로 다른 TaskRun Pod의 공유 저장소로 가정하지 않습니다. 캐시는 신뢰 수준과 실행별 쓰기 충돌을 고려해 분리합니다.

`finally`는 일반 Task 종료 후 실행되지만 무조건 실행 보장은 아닙니다. 누락된 Task Result를 참조하면 skip될 수 있고, 취소 방식·전체 timeout·자원/참조 오류로도 실행되지 못할 수 있습니다. 이 예제의 최종 리포트는 생성되지 않았을 수 있는 이미지 Result 대신 run 이름과 `tasks.status`만 사용합니다. 여러 finally Task 사이의 실행 순서도 가정하지 않습니다.

## 5. Webhook과 Triggers

아래 Trigger는 GitHub HMAC 검증을 먼저 거친 뒤 **저장소·브랜치·삭제 여부·전체 SHA**를 확인합니다. Git URL, ECR 경로, Task 이름과 서비스 계정은 신뢰된 정의에 고정합니다. 외부 PR 이벤트를 같은 template에 연결하지 않습니다. HMAC은 요청의 출처를 검증하지만 PR 코드에 배포 권한을 부여할 근거는 아닙니다.

![GitHub 서명과 저장소·브랜치 필터를 통과한 승인 커밋만 고정된 PipelineRun을 생성](../.gitbook/assets/ko-ops-14-tekton-pipelines-3.png)

[인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-ops-14-tekton-pipelines-3.html)

**`triggers.yaml`**

```yaml
apiVersion: triggers.tekton.dev/v1beta1
kind: EventListener
metadata:
  name: trusted-github
  namespace: tekton-builds
spec:
  serviceAccountName: ci-triggers
  triggers:
    - name: protected-main-push
      interceptors:
        - ref:
            name: github
          params:
            - name: secretRef
              value:
                secretName: github-webhook
                secretKey: token
            - name: eventTypes
              value: [push]
        - ref:
            name: cel
          params:
            - name: filter
              value: >-
                body.repository.full_name == 'myorg/myapp' &&
                body.ref == 'refs/heads/main' &&
                body.deleted == false &&
                body.after.matches('^[0-9a-f]{40}$')
      bindings:
        - ref: trusted-commit
      template:
        ref: trusted-image-ci
---
apiVersion: triggers.tekton.dev/v1beta1
kind: TriggerBinding
metadata:
  name: trusted-commit
  namespace: tekton-builds
spec:
  params:
    - name: revision
      value: $(body.after)
---
apiVersion: triggers.tekton.dev/v1beta1
kind: TriggerTemplate
metadata:
  name: trusted-image-ci
  namespace: tekton-builds
spec:
  params:
    - name: revision
  resourcetemplates:
    - apiVersion: tekton.dev/v1
      kind: PipelineRun
      metadata:
        generateName: trusted-image-ci-
        namespace: tekton-builds
      spec:
        pipelineRef:
          name: trusted-image-ci
        params:
          - name: revision
            value: $(tt.params.revision)
          - name: image
            value: 123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/myapp-candidates
        workspaces:
          - name: source
            volumeClaimTemplate:
              spec:
                accessModes: [ReadWriteOnce]
                storageClassName: gp3
                resources:
                  requests:
                    storage: 10Gi
        taskRunTemplate:
          serviceAccountName: ci-readonly
          podTemplate:
            automountServiceAccountToken: false
            securityContext:
              fsGroup: 1000
        taskRunSpecs:
          - pipelineTaskName: build
            serviceAccountName: ci-image-push
          - pipelineTaskName: scan
            serviceAccountName: ci-image-read
        timeouts:
          pipeline: 1h
          tasks: 50m
          finally: 5m
```

`github-webhook` Secret의 `token`과 GitHub Webhook 설정의 Secret은 같은 값이어야 합니다. Secret은 암호 관리자나 보호된 파일에서 제공하고 Git에 넣지 않습니다. 외부 HTTPS endpoint와 GitHub delivery 재시도·중복 처리를 별도로 구성합니다. EventListener 자체는 기본 내부 Service이며, 이 YAML만으로 인터넷 endpoint가 생기지 않습니다.

TLS termination을 포함한 gateway/Ingress 경로에서 HMAC 검증에 필요한 원본 본문을 바꾸지 않습니다. 스스로 호스팅하는 callback에는 인증·속도 제한·가용성·고정된 경로를 적용합니다. 일일 또는 일회성 이벤트가 없는 시간을 장애로 단정하지 않습니다. 실제 delivery 결과와 EventListener 처리 오류를 확인합니다.

CEL 필터에서 `head_commit`이 항상 존재한다고 가정하거나 `refs/heads/feature/a`를 단순 split의 세 번째 요소로 자르지 않습니다. 파일 변경 필터는 added/modified/removed 및 payload 크기 제한을 고려해야 합니다. 여기서는 업무 경로 필터를 임의로 추가하지 않습니다.

## 6. Chains와 서명 검증

### 6.1 CI 성공과 서명 완료는 별도 상태

Chains는 별도 컨트롤러이며 완료된 TaskRun/PipelineRun을 처리합니다. 이미지 서명만으로 전체 테스트·스캔 성공이 입증되지는 않습니다. `chains.tekton.dev/signed=true`도 배포 승인이나 암호학적 검증을 대신하지 않습니다.

Pipeline-level provenance는 Pipeline 종료 후 생성됩니다. 같은 Pipeline 안에서 자신의 Pipeline attestation을 기다리면 완료 순서가 충돌할 수 있습니다. 이 예제는 CI 종료 후 별도의 검증·승격 절차를 사용합니다.

![CI 성공 확인 후 Chains 서명·provenance를 검증하고 승인된 digest만 승격](../.gitbook/assets/ko-ops-14-tekton-pipelines-4.png)

[인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-ops-14-tekton-pipelines-4.html)

### 6.2 KMS 기반 구성

기존 비대칭 `SIGN_VERIFY` KMS 키를 사용합니다. 키 ARN과 `builder.id`를 실제 값으로 바꿉니다. **Chains 컨트롤러의 ServiceAccount `tekton-chains/tekton-chains-controller`**에는 별도의 IRSA 역할을 설정하고 후보 리포지터리 ECR 쓰기 권한과 다음 KMS 권한을 줍니다. 빌드 Pod의 IRSA 역할을 설정했다고 컨트롤러까지 같은 자격 증명을 받지는 않습니다.

현재 OCI 저장 구현은 Kubernetes credential 조회와 기본/ECR credential helper 체인을 사용합니다. 컨트롤러의 ambient AWS 자격 증명을 구성하고 실제 서명 업로드를 확인해야 합니다. 빌드 Task의 `/auth` emptyDir는 Chains에서 읽을 수 있는 공용 Secret이 아닙니다.

**`chains-kms-policy.json`**

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": ["kms:Sign", "kms:GetPublicKey", "kms:DescribeKey"],
    "Resource": "arn:aws:kms:ap-northeast-2:123456789012:key/REPLACE_KEY_ID"
  }]
}
```

**`chains-config.yaml`**

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: chains-config
  namespace: tekton-chains
data:
  artifacts.taskrun.storage: ""
  artifacts.pipelinerun.format: slsa/v2alpha3
  artifacts.pipelinerun.storage: oci
  artifacts.pipelinerun.signer: kms
  artifacts.oci.format: simplesigning
  artifacts.oci.storage: oci
  artifacts.oci.signer: kms
  signers.kms.kmsref: awskms:///arn:aws:kms:ap-northeast-2:123456789012:key/REPLACE_KEY_ID
  signers.x509.fulcio.enabled: "false"
  transparency.enabled: "false"
  storage.oci.encoding-format: dsse
  builder.id: https://ci.example.com/tekton/trusted-image-ci
  builddefinition.buildtype: https://tekton.dev/chains/v2/slsa
```

`slsa/v1`이라는 formatter 이름은 SLSA provenance v1.0을 의미하지 않습니다. 현재 Chains에서 `slsa/v1`/`in-toto`는 v0.2, `slsa/v2alpha3`/`slsa/v2alpha4`는 v1.0에 대응합니다. 이 예제는 Pipeline-level `slsa/v2alpha3`를 사용하고 중복 Task-level provenance 저장을 끕니다. 이미지 서명은 별도로 켭니다.

`storage.oci.encoding-format: dsse`는 기존 `.sig`/`.att` 저장 방식입니다. 0.29의 `sigstore-bundle`은 OCI 1.1 referrer 방식이며 저장 위치·검증 도구와 함께 변경해야 합니다. Rekor 업로드는 여기서 꺼 두었으므로 아래 검증도 내부 공개 키 정책을 명시합니다. 공개 transparency log가 필요한 운영 정책이면 별도로 설정하고 민감한 빌드 메타데이터의 공개 범위도 검토합니다.

Keyless를 선택한다면 실제 Fulcio가 신뢰하는 issuer와 워크로드 토큰을 구성해야 합니다. EKS Pod에 GitHub Actions issuer 문자열만 넣는 방식으로 인증이 생기지는 않습니다. 서명/증명이 존재한다는 이유만으로 SLSA 특정 레벨 충족을 선언하지 않습니다.

### 6.3 실행 상태와 아티팩트의 독립 검증

다음 스크립트는 **신뢰된 API에서 읽은 PipelineRun**의 성공 상태, Chains 처리 완료, 승인한 저장소·커밋·이미지 출력만 확인합니다. 서명을 검증하지 않습니다. 뒤의 Cosign 검증과 provenance 정책 검토가 모두 필요합니다.

**`check_run.py`**

```python
"""Check trusted API output before separate cryptographic artifact verification."""
import argparse
import json
import re
from pathlib import Path


def check(run, repository, revision, image):
    if run.get("kind") != "PipelineRun" or run.get("apiVersion") != "tekton.dev/v1":
        raise ValueError("Expected a tekton.dev/v1 PipelineRun")
    metadata = run.get("metadata", {})
    if metadata.get("namespace") != "tekton-builds" or not metadata.get("uid"):
        raise ValueError("Unexpected namespace or missing run UID")
    if run.get("spec", {}).get("pipelineRef", {}).get("name") != "trusted-image-ci":
        raise ValueError("Unexpected pipeline")
    succeeded = [c for c in run.get("status", {}).get("conditions", []) if c.get("type") == "Succeeded"]
    if len(succeeded) != 1 or succeeded[0].get("status") != "True":
        raise ValueError("CI has not succeeded")
    if not run.get("status", {}).get("completionTime"):
        raise ValueError("CI completion time is missing")
    if metadata.get("annotations", {}).get("chains.tekton.dev/signed") != "true":
        raise ValueError("Chains has not completed; retry later with a fresh API read")
    results = {}
    for result in run.get("status", {}).get("results", []):
        if result["name"] in results:
            raise ValueError("Duplicate result")
        results[result["name"]] = result["value"]
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("Expected full source revision")
    expected = {"CHAINS-GIT_URL": repository, "CHAINS-GIT_COMMIT": revision, "IMAGE_URL": image}
    if any(results.get(k) != v for k, v in expected.items()):
        raise ValueError("Run outputs do not match the approved source and repository")
    digest = results.get("IMAGE_DIGEST", "")
    if not isinstance(digest, str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", digest):
        raise ValueError("Missing or invalid image digest")
    return image + "@" + digest


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--image", required=True)
    args = parser.parse_args()
    try:
        print(check(json.loads(args.run.read_text()), args.repository, args.revision, args.image))
    except (ValueError, KeyError, TypeError) as error:
        parser.exit(1, f"Run gate failed: {error}\n")
```

```bash
set -euo pipefail
DOCS_RUN="REPLACE_PIPELINERUN_NAME"
DOCS_REVISION="REPLACE_WITH_FULL_40_CHARACTER_COMMIT_SHA"
DOCS_IMAGE="123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/myapp-candidates"
kubectl -n tekton-builds get pipelinerun "$DOCS_RUN" -o json > run.json
DOCS_IMAGE_REF="$(python3 check_run.py --run run.json \
  --repository https://github.com/myorg/myapp.git \
  --revision "$DOCS_REVISION" --image "$DOCS_IMAGE")"

# chains.pub must be the independently trusted public key for the configured KMS key.
# Registry read authentication must already be configured.
# Explicit private-key policy: verify signatures, without requiring a Rekor entry.
cosign verify --key chains.pub --insecure-ignore-tlog=true "$DOCS_IMAGE_REF" \
  > verified-signature.json
cosign verify-attestation --key chains.pub --insecure-ignore-tlog=true \
  --type https://slsa.dev/provenance/v1 "$DOCS_IMAGE_REF" \
  > verified-attestations.json
```

이 예제의 `--insecure-ignore-tlog`는 공개 Rekor entry를 요구하지 않는다는 명시적인 선택입니다. 신뢰된 키로 서명 자체를 검사하는 단계는 유지합니다. 조직 정책이 transparency 검증을 요구한다면 이 예외를 사용하지 말고 업로드·검증 체인을 먼저 구성합니다.

검증된 attestation의 subject digest, `runDetails.builder.id`, `buildDefinition.buildType`, 소스의 URI와 정확한 commit, 사용한 Task/Pipeline 정의가 승인한 값과 일치하는지 정책으로 확인합니다. 임의 공급자의 올바른 서명이나 다른 빌드의 attestation을 허용하면 안 됩니다. 위 명령만으로 이 조직별 정책이 자동 구현되는 것은 아닙니다.

Kyverno admission에서도 같은 공개 키/identity·digest·provenance 조건을 검사하도록 별도 정책을 구성합니다. 불완전한 `BEGIN PUBLIC KEY ...` 문자열을 적용하거나 존재하지 않는 predicate 필드를 비교하지 않습니다. 최신 Kyverno의 ImageValidatingPolicy와 해당 버전의 registry 인증을 확인하고, 정상·다른 키·다른 소스·미서명 이미지의 허용/거부 사례를 테스트합니다.

## 7. GitOps로 전달

검증된 `repository@sha256:...`를 GitOps 저장소의 실제 Kustomize/Helm 설정에 반영합니다. 이 장은 Git push/PR 생성·merge를 자동으로 실행하는 Task를 포함하지 않습니다. 담당자나 별도 승인된 promotion workflow가 고정된 저장소와 파일을 수정하고 CI·리뷰 후 병합합니다. 같은 manifest를 Tekton의 kubectl deploy와 ArgoCD가 동시에 관리하지 않습니다.

![검증된 digest의 GitOps 변경을 리뷰하고 ArgoCD가 manifest를 동기화하며 kubelet이 이미지를 가져오는 흐름](../.gitbook/assets/ko-ops-14-tekton-pipelines-5.png)

[인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-ops-14-tekton-pipelines-5.html)

```bash
# In a reviewed checkout with the Kustomize CLI installed:
cd overlays/production
kustomize edit set image "myapp=$DOCS_IMAGE_REF"
kustomize build . > /tmp/rendered-myapp.yaml
git diff -- kustomization.yaml
# Run repository checks and submit the focused change for review.
```

image 참조를 `cut -d: -f1/2`로 분해하면 registry port와 digest를 잘못 처리할 수 있습니다. 도구에 전체 참조를 전달합니다. SSH known_hosts는 신뢰된 배포 경로에서 제공하고 검증 없는 `ssh-keyscan` 결과를 신뢰 근거로 삼지 않습니다. 다른 Step의 홈 디렉터리에 복사한 인증 파일이 자동 공유된다고 가정하지 않습니다.

ArgoCD는 Git의 manifest를 동기화하고, 실제 애플리케이션 이미지는 노드 kubelet/container runtime이 가져옵니다. Sync 완료와 애플리케이션의 정상 동작은 별도로 확인합니다. 롤백도 데이터·스키마 변경을 자동 복원하지 않습니다.

## 8. 운영과 정리

### 8.1 실행 기록과 PVC

`keep`, `keep-since`는 tkn 삭제 명령 등의 옵션이며 PipelineRun에 기본 TTL을 부여하는 필드가 아닙니다. tkn 0.46.0의 `pipelinerun delete`에는 `--dry-run`이 없습니다. 삭제 전에 로그·스캔 보고서·서명/provenance 보관과 감사 기간을 확인합니다. 성공 Pod 전체를 나이 조건 없이 삭제하지 않습니다.

다음 도구는 선택한 namespace에서 성공 7일·실패 14일이 지난 **검토 후보만** 출력합니다. 생성 시각 대신 완료 시각을 사용하며, Chains와 외부 아카이브의 완료 표시를 요구합니다. `ci.example.com/archive-complete`는 자동 제공되는 Tekton 필드가 아니라 실제 아카이브 성공 후 운영 절차가 기록할 annotation입니다. 스크립트는 Kubernetes API를 호출하거나 삭제하지 않습니다.

**`cleanup_candidates.py`**

```python
"""Print names for review; this script never deletes Kubernetes objects."""
import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path


def timestamp(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Timezone required")
    return parsed.astimezone(timezone.utc)


def candidates(document, now, namespace):
    if now.tzinfo is None:
        raise ValueError("Timezone required")
    result, skipped = [], []
    for obj in document.get("items", []):
        meta, status = obj.get("metadata", {}), obj.get("status", {})
        name = meta.get("name", "<unnamed>")
        conditions = [c for c in status.get("conditions", []) if c.get("type") == "Succeeded"]
        annotations = meta.get("annotations", {})
        if (obj.get("kind") != "PipelineRun" or meta.get("namespace") != namespace
                or not meta.get("uid") or len(conditions) != 1
                or conditions[0].get("status") not in ("True", "False")):
            skipped.append({"name": name, "reason": "not a terminal run in the selected namespace"})
            continue
        if annotations.get("ci.example.com/retain") == "true":
            skipped.append({"name": name, "reason": "retention hold"})
            continue
        if (annotations.get("chains.tekton.dev/signed") != "true"
                or annotations.get("ci.example.com/archive-complete") != "true"):
            skipped.append({"name": name, "reason": "Chains processing or archive acknowledgement incomplete"})
            continue
        try:
            completed = timestamp(status["completionTime"])
        except (ValueError, KeyError, TypeError, AttributeError):
            skipped.append({"name": name, "reason": "invalid completion time"})
            continue
        retention_days = 7 if conditions[0]["status"] == "True" else 14
        if completed < now - timedelta(days=retention_days):
            result.append({"namespace": namespace, "name": name, "uid": meta["uid"],
                           "completed": completed.isoformat(), "retentionDays": retention_days})
    return {"mode": "review-only", "candidates": result, "skipped": skipped}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--namespace", default="tekton-builds")
    parser.add_argument("--now", default=datetime.now(timezone.utc).isoformat())
    args = parser.parse_args()
    print(json.dumps(candidates(json.loads(args.input.read_text()), timestamp(args.now), args.namespace), indent=2))
```

```bash
kubectl -n tekton-builds get pipelineruns -o json > runs.json
python3 cleanup_candidates.py --input runs.json --namespace tekton-builds
```

PVC 생명 주기는 `coschedule` 모드별로 다릅니다.

| 모드 | volumeClaimTemplate PVC의 완료 후 동작 |
| --- | --- |
| `workspaces` | 기본 유지. `tekton.dev/auto-cleanup-pvc: "true"`를 Run에 설정하면 완료 시 정리 |
| `pipelineruns`, `isolate-pipelinerun` | 완료 시 정리 |
| `disabled` | ownerReference에 따른 GC. Run 삭제 시 함께 삭제되는지 확인 |

이미 존재하는 PVC를 직접 바인딩한 Workspace는 위 annotation으로 삭제되지 않습니다. 백업·보관이 필요한 Workspace에 자동 정리를 켜지 않습니다. TaskRun의 ownerReference를 보지 않고 모두 “고아”로 간주하지 않습니다.

### 8.2 모니터링

Pipelines 1.16의 메트릭은 OpenTelemetry로 내보냅니다. `config-observability`의 `metrics-protocol: prometheus`에서 controller Service의 포트 이름은 **`http-metrics`**입니다. 실제 ServiceMonitor selector와 Prometheus selector를 모두 맞춥니다.

**`servicemonitor.yaml`**

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: tekton-pipelines
  namespace: observability
  labels:
    release: prometheus
spec:
  namespaceSelector:
    matchNames: [tekton-pipelines]
  selector:
    matchLabels:
      app.kubernetes.io/component: controller
      app.kubernetes.io/part-of: tekton-pipelines
  endpoints:
    - port: http-metrics
      path: /metrics
      interval: 30s
      honorLabels: true
```

**`monitoring-rules.yaml`**

```yaml
groups:
  - name: tekton-ci
    rules:
      - record: tekton:completed_duration_seconds:mean1h
        expr: |
          sum(rate(tekton_pipelines_controller_pipelinerun_duration_seconds_sum[1h]))
          /
          sum(rate(tekton_pipelines_controller_pipelinerun_duration_seconds_count[1h]))
      - alert: TektonCompletedRunFailureRatio
        expr: |
          (
            sum(increase(tekton_pipelines_controller_pipelinerun_total{status="failed"}[1h]))
            /
            sum(increase(tekton_pipelines_controller_pipelinerun_total{status=~"success|failed"}[1h]))
            > 0.30
          )
          and
          (
            sum(increase(tekton_pipelines_controller_pipelinerun_total{status=~"success|failed"}[1h])) >= 10
          )
        for: 15m
        labels:
          severity: warning
        annotations:
          summary: "More than 30% failed among at least 10 completed non-cancelled CI runs"
      - alert: TektonControllerMetricsUnavailable
        expr: |
          absent(up{namespace="tekton-pipelines",service="tekton-pipelines-controller",endpoint="http-metrics"} == 1)
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "No healthy scrape target for the Tekton controller"
```

위 파일은 일반 Prometheus rule 형식입니다. Operator를 사용하면 `PrometheusRule.spec`에 넣습니다. 현재 완료 횟수는 `pipelinerun_total`, 실행 중 수는 `running_pipelineruns`입니다. 완료 counter의 status는 `success`·`failed`·`cancelled`이며 counter에는 namespace label이 없습니다. 이 실패율은 클러스터 단위로 취소를 제외한 성공/실패만 비교하는 예시입니다.

평균 시간은 histogram sum/count의 **합을 나눈 값**을 사용합니다. 각 시계열 평균의 단순 평균을 전체 평균이라고 표시하지 않습니다. 완료 duration metric에 `status=running`을 붙여 실행 중 경과 시간을 얻을 수는 없습니다. 장시간 실행은 실제 Run의 startTime·condition과 Pod 상태를 조회합니다.

### 8.3 문제 해결과 로그

```bash
tkn pipelinerun describe "$DOCS_RUN" -n tekton-builds
tkn pipelinerun logs "$DOCS_RUN" -n tekton-builds --log-failed
tkn pipelinerun logs "$DOCS_RUN" -n tekton-builds --task build
kubectl -n tekton-builds get pipelinerun "$DOCS_RUN" -o yaml
kubectl -n tekton-builds describe pod -l "tekton.dev/pipelineRun=$DOCS_RUN"
kubectl -n tekton-pipelines logs deployment/tekton-pipelines-controller --tail=100
kubectl -n tekton-chains logs deployment/tekton-chains-controller --tail=100
```

`--last`는 마지막 실행이며 “마지막 실패 실행”이 아닙니다. CRD에 지원되지 않는 condition field-selector를 사용하지 말고 JSON을 읽어 condition type/value를 확인합니다. Loki/Alloy를 쓰면 실제로 수집한 namespace·PipelineRun label을 조회합니다. 빌드 namespace가 `tekton-builds`인데 컨트롤러 namespace 파일만 수집하는 경로는 빌드 로그를 놓칩니다.

`Pending`은 quota·노드·PVC·스케줄링 이벤트를 확인합니다. `gp3` RWO를 YAML에서 RWX로 바꾸는 것만으로 EFS처럼 동작하지 않습니다. 결과 과다·권한 오류·누락 Task·없는 CLI는 timeout 연장으로 해결되지 않습니다.

## 9. 재사용과 운영 선택

- **Sidecar**: DB readiness probe와 실제 연결 확인을 사용합니다. 단순 sleep은 준비 완료의 증거가 아닙니다. native sidecar 지원 설정과 종료 동작을 설치 버전에 맞춰 확인합니다.
- **StepAction**: 1.16에서 기능은 안정화되어 있지만 릴리스의 저장 API는 `tekton.dev/v1beta1`입니다. 재사용 Step의 실행 도구·credentials·결과 경로를 실제 Task와 연결합니다.
- **Task 카탈로그**: Hub 서비스 폐기와 CLI 내부화는 별개입니다. tkn 0.46의 Hub 명령 존재를 서비스의 장기 가용성으로 해석하지 않습니다. 승인한 정의를 고정 commit 또는 검증된 OCI bundle digest로 관리하고 resolver 접근 범위를 제한합니다.
- **네트워크**: NetworkPolicy의 `to: []`와 TCP 443 허용은 모든 대상의 해당 포트를 허용합니다. ECR/GitHub 도메인 allowlist가 아닙니다. 필요한 DNS·STS/ECR/S3·레지스트리·API 경로를 CNI/프록시/VPC 설계에 맞춰 제한합니다.
- **Spot과 비용**: Karpenter는 `karpenter.sh/capacity-type: spot`, EKS Managed Node Group은 실제 `eks.amazonaws.com/capacityType` label을 확인합니다. 중단·재시도·quota·스토리지 비용을 고려합니다. 실행 Pod가 없다고 모든 비용이 0이 되지는 않습니다.
- **캐시**: 재사용 비율은 workload별로 측정합니다. 보편적인 40–60% 절감률을 보장하지 않습니다. 신뢰 수준이 다른 실행은 writable 캐시를 공유하지 않습니다.

## 10. 참고 자료

- [Pipelines 1.16.0](https://github.com/tektoncd/pipeline/releases/tag/v1.16.0)
- [Triggers 0.37.0](https://github.com/tektoncd/triggers/releases/tag/v0.37.0)
- [Chains 0.29.0](https://github.com/tektoncd/chains/releases/tag/v0.29.0)
- [Dashboard 0.72.0](https://github.com/tektoncd/dashboard/releases/tag/v0.72.0)
- [Pipelines security model](https://github.com/tektoncd/pipeline/blob/v1.16.0/docs/security/README.md)
- [Affinity and PVC lifecycle](https://github.com/tektoncd/pipeline/blob/v1.16.0/docs/affinityassistants.md)
- [Pipelines metrics](https://github.com/tektoncd/pipeline/blob/v1.16.0/docs/metrics.md)
- [Chains configuration](https://github.com/tektoncd/chains/blob/v0.29.0/docs/config.md)
- [SLSA formatter and type hints](https://github.com/tektoncd/chains/blob/v0.29.0/docs/slsa-provenance.md)
- [BuildKit rootless requirements](https://github.com/moby/buildkit/blob/v0.33.0/docs/rootless.md)
- [Cosign 3.1.3](https://github.com/sigstore/cosign/releases/tag/v3.1.3)
- [CI infrastructure](./03-ci-pipelines.md)
- [GitOps multi-cluster](./04-gitops-multi-cluster.md)
- [Observability stack](./09-observability-stack.md)
