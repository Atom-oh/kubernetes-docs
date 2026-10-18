# Tekton Pipelines：Kubernetes 原生 CI

> **最后更新**：2026 年 10 月 16 日。Pipelines 1.17.0, Triggers 0.37.1, Chains 0.29.0, Dashboard 0.73.0, tkn 0.46.1.
> **验证**：Release CRD schemas、Task 依赖项、本地脚本和模拟程序。未执行实时 EKS 安装、镜像构建/推送、KMS 签名、外部 Webhook 或通知。

< [上一章：FinOps](./13-finops-cost-platform.md) | [目录](./README.md) | [下一章：可用区运维](./15-zonal-operations-guide.md) >

## 概述

Tekton 通过 Kubernetes API 定义 Task、Pipeline 及其执行过程。运维人员仍需管理控制器、工作节点容量、存储、升级和访问权限。其他 CI 系统也可以支持 Kubernetes 执行器、自动扩缩容和证明；请避免声称这些能力只有 Tekton 支持，或声称其运营成本为零。

此示例为**获批仓库的受保护 main 分支**运行 Go 应用 CI：克隆 → 并行执行 vet/test → 发布候选镜像 → 基于摘要扫描。Chains 处理和加密验证完成后，再提交单独审核的 GitOps 变更。外部 fork PR 不得与此 Pipeline 共用 IRSA 角色、PVC 或签名权限。

## 1. 执行模型

| 组件 | 作用 |
| --- | --- |
| Task / Pipeline | 可复用的工作和依赖定义 |
| TaskRun / PipelineRun | 带有参数和状态的执行实例 |
| Step / Sidecar | 顺序执行的工作 / 支持服务，通常位于 TaskRun Pod 内 |
| Workspace / Result | 卷绑定 / 小型输出值；不是独立的 CRD |

Task 定义本身不是 Pod：执行 TaskRun 时才会创建 Pod。Result 支持字符串、数组和对象类型；大型报告应使用制品存储。相同 Pod 中的 Steps 共用网络和卷，因此它们不是相互不可信代码之间可靠的隔离边界。

![定义、执行、Workspace/Result 字段以及单独的 Chains 处理流程](../.gitbook/assets/en-ops-14-tekton-pipelines-0.png)

[查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-ops-14-tekton-pipelines-0.html)

![API server、控制器、Webhook 和使用每次运行专属 Workspace 的 TaskRun Pod](../.gitbook/assets/en-ops-14-tekton-pipelines-1.png)

[查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-ops-14-tekton-pipelines-1.html)

## 2. 安装和执行权限

### 2.1 版本和安装方式

官方安装最低要求为 Kubernetes 1.28，而本章的安全字段和 schema 验证以 Kubernetes 1.36 为目标。上游最低版本并不代表对当前受支持的 EKS 版本的建议。Dashboard 0.73.0 明确支持 Pipelines 1.15 LTS/1.17 和 Triggers 0.37 LTS。

这是一个固定版本的手动安装示例。官方指南也推荐在生产环境中使用 Tekton Operator 管理生命周期。在混用手动 apply 和 Operator 管理的资源之前，先确定由谁负责管理。这些命令会更改真实集群；请先检查资源归属，不要盲目强制解决冲突。

```bash
kubectl version -o yaml
kubectl get storageclass

curl --fail --location \
  https://infra.tekton.dev/tekton-releases/pipeline/previous/v1.17.0/release.yaml \
  -o pipelines-release.yaml
kubectl apply --server-side --field-manager=tekton-install -f pipelines-release.yaml
kubectl wait --for=condition=Established --timeout=120s \
  crd/tasks.tekton.dev crd/taskruns.tekton.dev \
  crd/pipelines.tekton.dev crd/pipelineruns.tekton.dev
kubectl -n tekton-pipelines wait deployment --all \
  --for=condition=Available --timeout=300s

kubectl apply --server-side -f \
  https://infra.tekton.dev/tekton-releases/triggers/previous/v0.37.1/release.yaml
kubectl apply --server-side -f \
  https://infra.tekton.dev/tekton-releases/triggers/previous/v0.37.1/interceptors.yaml
kubectl apply --server-side -f \
  https://infra.tekton.dev/tekton-releases/chains/previous/v0.29.0/release.yaml
kubectl apply --server-side -f \
  https://infra.tekton.dev/tekton-releases/dashboard/previous/v0.73.0/release.yaml
kubectl -n tekton-pipelines port-forward service/tekton-dashboard 9097:9097
```

`release.yaml` 安装的是只读 Dashboard；`release-full.yaml` 包含写入功能。只读模式不会对用户进行身份验证，也不会自动强制执行按命名空间划分的用户权限。对外提供服务前，请验证身份验证代理/OIDC 和访问模型。内部 ALB 不等于身份验证。Cognito 集成需要实际的 HTTPS 监听器、Cognito/OIDC 端点和 Secret。

`https://tekton.dev/helm-charts` 不是此示例可用的官方 chart 仓库。不要安装先前并不存在的 chart 和 values。

### 2.2 当前配置项的含义

| 设置 | 当前含义 |
| --- | --- |
| `feature-flags.coschedule: workspaces` | 让共用 PVC Workspace 的 TaskRun 协同调度；此 RWO 示例应保留此设置 |
| `disable-affinity-assistant` | v0.68 之后已移除的旧版标志 |
| `set-security-context: true` | 1.17 中 Tekton 注入的容器默认启用；用户 Steps 需要各自设置兼容的上下文 |
| `results-from: termination-message` | 默认路径，受 Kubernetes termination-message 大小限制 |
| `max-result-size` | 适用于 `sidecar-logs`；仅更改此项不会扩大默认 termination message |
| 默认 timeout | 由 `config-defaults` 管理；此示例显式设置 PipelineRun timeout |

`running-in-environment-with-injected-sidecars` 不是 Workspace 隔离，`keep-pod-on-cancel` 也不是 PipelineRun 保留 TTL。不要用简短摘录替换完整的 ConfigMap。

### 2.3 分离 ServiceAccount 和 IAM 角色

控制器使用 `tekton-pipelines` / `tekton-chains`；构建使用 `tekton-builds`。简单的 Task/Pipeline 名称引用会在同一命名空间中解析。仅凭名称无法引用共享命名空间中的 Task。

先创建 IAM 角色。每个 IRSA 信任策略都必须限定现有集群 OIDC provider、`aud=sts.amazonaws.com` 和确切的 `sub=system:serviceaccount:tekton-builds:<SA name>`。预先创建 ECR 仓库；构建不需要 `CreateRepository`。尽管名称中含有 readonly，示例中的 `ci-readonly` 并没有 Kubernetes API Role：它是默认的非特权执行账户。

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

将 push policy 附加到 `tekton-candidate-push`，将 read policy 附加到 `tekton-candidate-read`。在所有位置替换账户、区域和仓库。`GetAuthorizationToken` 不支持仓库级资源范围，因此该权限单独列出，并通过请求区域加以限制。

IRSA 对 Pod 内的 AWS SDK/CLI 调用进行身份验证。Kubelet 的 ECR 镜像拉取则通过节点角色、Fargate 执行角色或 imagePullSecrets 等独立路径完成。仅设置 Task 的 IRSA 注解无法解决 ImagePullBackOff。

## 3. 完整的 Task 定义

这六个 Task 构成一个完整一致的示例。源代码仓库必须包含 Go module、测试和 Dockerfile。将 checkout 中固定的 `myorg/myapp` URL 替换为获批仓库，并与 Trigger allowlist 保持一致。不要接受 Webhook 输入提供的任意 Git URL 或 shell 命令。

Tekton 替换是文本替换。应通过环境变量或参数传递 params，而不是将其插入脚本正文。验证 commit 必须是完整的 40 个字符。ECR 身份验证文件使用 Task 本地的 `emptyDir`；不要将它们写入只读 Secret 卷，也不要假设其他 Step 的镜像中存在所需工具。

Rootless BuildKit 需要经过验证的专用构建环境，该环境应支持 user namespace、挂载和适当的 seccomp/AppArmor 配置。`Unconfined` 和 `--oci-worker-no-process-sandbox` 是明确的安全折中，在受限命名空间策略下会被拒绝。它们并非普遍安全的默认设置。外部 PR 应使用单独的环境。

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
    image: golang:1.27.2
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
    image: golang:1.27.2
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
    image: golang:1.27.2
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
    image: aquasec/trivy:0.76.0
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

原始 Google Kaniko 仓库已归档；此新示例使用 BuildKit 0.33.0。Rootless 不保证完全的进程隔离。投入生产前，请验证并固定镜像摘要/平台，并在实际节点上测试可写路径和安全上下文。

发现问题时扫描器返回退出代码 1，其他错误代码也都会导致 Task 失败。缺失的报告不得被当作“零个漏洞”。`/tmp/trivy-report.json` 是临时文件；如果需要长期保留，应在执行清理前将其导出到获批的制品存储。

## 4. Pipeline 和执行

![克隆、并行执行 test/vet、发布/扫描候选镜像，以及尽力执行的最终报告](../.gitbook/assets/en-ops-14-tekton-pipelines-2.png)

[查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-ops-14-tekton-pipelines-2.html)

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

每次执行都会创建一个新的 PVC。ReadWriteOnce 允许多个 Pod 在同一节点上使用，但不是多节点 RWX。emptyDir 不是可供不同 TaskRun Pod 共享的存储。应按信任级别分开缓存，并协调并发写入者。

普通 Tasks 执行后会运行 `finally`，但它并非无条件执行。引用缺失的 Result 可能导致跳过；取消模式、整体 timeout、资源故障和未解析的引用也可能阻止执行。此示例只报告运行名称和 `tasks.status`，避免引用可能尚未生成的镜像 Result。不要假设多个 finally Task 之间存在执行顺序。

## 5. Webhook 和 Triggers

此 Trigger 先验证 GitHub HMAC，再检查**仓库、分支、删除状态和完整 SHA**。Git URL、ECR 路径、Task 名称和 ServiceAccount 均固定在可信定义中。不要将外部 PR 事件连接到此模板。HMAC 用于验证投递来源；它并未授权 PR 代码进行部署。

![验证投递，并检查仓库/分支筛选条件，为获批 commit 创建固定的 PipelineRun](../.gitbook/assets/en-ops-14-tekton-pipelines-3.png)

[查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-ops-14-tekton-pipelines-3.html)

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

`github-webhook` Secret 中的 `token` 必须与 GitHub Webhook secret 一致。应从受保护的存储中提供该值，绝不能提交到 Git。外部 HTTPS 端点和投递重试/去重策略需要单独配置。EventListener 默认带有内部 Service；仅此 YAML 不会创建互联网端点。

为进行 HMAC 验证，应在 TLS 终止和 gateway/Ingress 处理期间保留原始请求正文。对回调配置适当的身份验证、速率限制、可用性和固定路由。安静期并不自动意味着 Webhook 中断：请检查实际投递结果和 EventListener 处理错误。

不要假定 `head_commit` 始终存在，也不要用单次 split 取值来截断 `refs/heads/feature/a`。文件变更筛选必须考虑新增、修改和删除的路径以及 payload 大小限制。此示例不会臆造特定业务的路径筛选条件。

## 6. Chains 和签名验证

### 6.1 CI 成功与签名完成是两个独立步骤

Chains 是单独的控制器，用于处理已完成的 TaskRun/PipelineRun。仅有镜像签名并不能证明完整测试和扫描均已成功。`chains.tekton.dev/signed=true` 既不是部署审批，也不代表已完成加密验证。

Pipeline 级别的 provenance 会在 Pipeline 完成后生成。在该 Pipeline 内等待其自身的证明可能与这一顺序冲突。此示例会在 CI 完成后，通过单独的验证和晋级流程进行处理。

![检查 CI 是否成功、验证 Chains 签名/provenance，并且仅晋级获批的摘要](../.gitbook/assets/en-ops-14-tekton-pipelines-4.png)

[查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-ops-14-tekton-pipelines-4.html)

### 6.2 KMS 配置

使用现有的非对称 `SIGN_VERIFY` KMS key。替换 key ARN 和 `builder.id`。在**Chains 控制器 ServiceAccount `tekton-chains/tekton-chains-controller`** 上配置单独的 IRSA 角色，并为候选仓库提供 ECR 写入权限以及以下 KMS 权限。向构建 Pod 授予 IRSA 角色，并不会使控制器获得这些凭证。

当前 OCI 后端使用 Kubernetes 凭证查找以及默认/ECR 凭证 helper 链。配置控制器的 ambient AWS identity，并验证签名是否实际上传。构建 Task 的 `/auth` emptyDir 不是 Chains 可以读取的共享 Secret。

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

formatter 名称 `slsa/v1` 并不表示 SLSA provenance v1.0。在当前 Chains 中，`slsa/v1` / `in-toto` 对应 v0.2，而 `slsa/v2alpha3` / `slsa/v2alpha4` 对应 v1.0。此示例使用 Pipeline 级别的 `slsa/v2alpha3`，禁用重复的 Task 级 provenance 存储，并单独启用镜像签名。

`storage.oci.encoding-format: dsse` 会保留旧版 `.sig` / `.att` 存储方式。0.29 版的 `sigstore-bundle` 使用 OCI 1.1 referrers；应同时更改存储和验证工具。此处禁用了 Rekor 上传，因此验证会明确遵循内部公钥策略。如有需要，请单独配置透明度，包括审查会暴露哪些构建元数据。

无密钥签名需要由实际 Fulcio 服务信任的 issuer 和有效的 workload token。在 EKS Pod 上设置 GitHub Actions issuer 字符串并不会提供身份验证。仅凭签名和证明也不能确定具体的 SLSA 等级。

### 6.3 独立验证执行和制品

此脚本会检查从**可信 API 读取的** PipelineRun，确认 CI 成功、Chains 处理已完成，并核对获批的仓库、commit 和镜像输出。它不验证签名。随后还必须执行 Cosign 检查和 provenance 策略审查。

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

`--insecure-ignore-tlog` 明确表示不要求存在公开的 Rekor 条目。仍会使用可信 key 验证签名。如果组织策略要求透明度验证，请配置相应的验证链，而不是使用此例外。

对已验证证明中的 subject digest、`runDetails.builder.id`、`buildDefinition.buildType`、准确的源 URI/commit 和获批的 Task/Pipeline 定义应用策略。来自任意生产者的有效签名，或针对其他构建的证明，都不足以满足要求。上述命令不会自动实现这些组织特定的检查。

还需单独配置 admission 验证，确保采用相同的可信 key/identity、摘要和 provenance 条件。不要使用不完整的 `BEGIN PUBLIC KEY ...` 占位符，也不要比较不存在的 predicate 字段。请检查与已安装版本匹配的当前 Kyverno ImageValidatingPolicy 和 registry 身份验证配置，然后测试正确/错误 key、源和未签名镜像等接受与拒绝情形。

## 7. GitOps 交接

使用已验证的 `repository@sha256:...` 更新实际的 Kustomize/Helm 配置。本章不包含会自动推送、创建或合并 PR 的 Task。由负责人或单独获批的晋级流程编辑固定仓库/文件，并在 CI 和审核通过后合并。避免让 Tekton kubectl deployment 和 ArgoCD 同时管理相同的 manifests。

![审核已验证摘要对应的 GitOps 变更；ArgoCD 同步 manifests，kubelet 拉取镜像](../.gitbook/assets/en-ops-14-tekton-pipelines-5.png)

[查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-ops-14-tekton-pipelines-5.html)

```bash
# In a reviewed checkout with the Kustomize CLI installed:
cd overlays/production
kustomize edit set image "myapp=$DOCS_IMAGE_REF"
kustomize build . > /tmp/rendered-myapp.yaml
git diff -- kustomization.yaml
# Run repository checks and submit the focused change for review.
```

使用 `cut -d: -f1/2` 分割镜像引用会破坏包含 registry 端口和摘要的引用。请将完整引用传递给工具。通过可信路径配置 SSH known_hosts；未经验证的 ssh-keyscan 结果不是信任锚。复制到某个 Step 主目录中的凭证不会自动共享给另一个 Step。

ArgoCD 同步 Git manifests；kubelet/container runtime 拉取应用镜像。请分别检查应用健康状态和同步是否完成。回滚不会自动还原数据或 schema 变更。

## 8. 运维和清理

### 8.1 执行记录和 PVC

`keep` 和 `keep-since` 是 tkn 删除命令等工具的选项，并非内置的 PipelineRun TTL 字段。tkn 0.46.1 `pipelinerun delete` 没有 `--dry-run`。删除任何内容之前，请检查日志、扫描报告、签名/provenance 和审计数据的保留情况。不要在没有年龄策略的情况下删除所有成功的 Pod。

此工具只会在单个命名空间中输出**供审核的候选项**：成功运行且完成时间超过七天，以及失败运行且完成时间超过十四天。它依据完成时间，而非创建时间，并要求 Chains 和归档确认。`ci.example.com/archive-complete` 是运维人员管理的注解，记录实际归档成功；它不是 Tekton 自动生成的字段。此脚本不会调用 Kubernetes API，也不会执行删除。

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

PVC 生命周期取决于 `coschedule`。

| 模式 | 完成后 volumeClaimTemplate PVC 的状态 |
| --- | --- |
| `workspaces` | 默认保留；Run 注解 `tekton.dev/auto-cleanup-pvc: "true"` 可启用完成后清理 |
| `pipelineruns`, `isolate-pipelinerun` | 完成后清理 |
| `disabled` | 通过 owner-reference 进行 GC；删除 Run 时应验证删除行为 |

直接绑定到 Workspaces 的现有 PVC 不会因该注解而被删除。仍需归档的数据不要启用自动清理。将 TaskRun 判定为孤儿之前，请检查 ownerReferences。

### 8.2 监控

Pipelines 1.17 通过 OpenTelemetry 导出指标。在 `config-observability` 中设置 `metrics-protocol: prometheus` 后，控制器 Service 的端口名称为 **`http-metrics`**。请同时匹配 ServiceMonitor 选择器和 Prometheus 选择器。

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

此文件采用普通 Prometheus rule 格式；使用 Operator 时，请将其放入 `PrometheusRule.spec`。当前完成次数使用 `pipelinerun_total`；活动运行次数使用 `running_pipelineruns`。计数器状态为 `success`、`failed` 和 `cancelled`，计数器上没有 namespace 标签。此示例比较集群范围内的成功/失败次数，同时排除取消的运行。

请通过**直方图总和之和除以计数之和**来计算平均持续时间。对各序列的平均值再取平均并不能得到总体平均值。带有 `status=running` 的已完成持续时间指标无法提供活动运行已持续的时间。请检查实际的 Run startTime、conditions 和 Pod 状态。

### 8.3 故障排查和日志

```bash
tkn pipelinerun describe "$DOCS_RUN" -n tekton-builds
tkn pipelinerun logs "$DOCS_RUN" -n tekton-builds --log-failed
tkn pipelinerun logs "$DOCS_RUN" -n tekton-builds --task build
kubectl -n tekton-builds get pipelinerun "$DOCS_RUN" -o yaml
kubectl -n tekton-builds describe pod -l "tekton.dev/pipelineRun=$DOCS_RUN"
kubectl -n tekton-pipelines logs deployment/tekton-pipelines-controller --tail=100
kubectl -n tekton-chains logs deployment/tekton-chains-controller --tail=100
```

`--last` 选择最新运行，而不是最近一次失败的运行。请从 JSON 中读取 conditions，不要使用不受支持的 CRD condition 字段选择器。查询 Loki/Alloy 实际收集的 namespace 和 PipelineRun 标签。只收集控制器命名空间中的文件会遗漏在 `tekton-builds` 中运行的构建。

对于 Pending Pod，请检查 quota、节点、PVC 和调度事件。在 YAML 中将 gp3 RWO 改为 RWX 并不会使其表现得像 EFS。延长 timeout 不能解决 Result 过大、权限不足、Task 缺失或工具不存在等问题。

## 9. 复用和运维选项

- **Sidecar**：检查数据库就绪状态和实际连接情况。sleep 不能证明服务已就绪。检查与已安装版本对应的原生 sidecar 功能设置和终止行为。
- **StepAction**：该功能在 1.17 中已稳定，但此版本的 release storage API 仍为 `tekton.dev/v1beta1`。请将实际工具、凭证和结果路径连接到使用它的 Task。
- **Catalog**：Hub 服务弃用与 CLI 内部化是两回事。tkn 0.46 中的 Hub 命令不能保证服务长期可用。请在固定 commit 或经过验证的 OCI bundle digest 上管理获批定义，并限制 resolver 的访问权限。
- **网络**：NetworkPolicy 中 `to: []` 配合 TCP 443 会允许访问所有目的地的该端口；它不是 ECR/GitHub 域名 allowlist。请依据实际的 CNI/proxy/VPC 设计，限制所需的 DNS、STS/ECR/S3、registry 和 API 路径。
- **Spot 和成本**：Karpenter 使用 `karpenter.sh/capacity-type: spot`；EKS Managed Node Groups 使用其实际的 `eks.amazonaws.com/capacityType` 标签。应考虑中断、重试、quota 和存储。没有正在运行的构建 Pod 并不意味着总成本为零。
- **缓存**：测量针对特定工作负载的复用情况。不要承诺普遍能提升 40–60%。不同信任级别之间不得共用可写缓存。

## 10. 参考资料

- [Pipelines 1.17.0](https://github.com/tektoncd/pipeline/releases/tag/v1.17.0)
- [Triggers 0.37.1](https://github.com/tektoncd/triggers/releases/tag/v0.37.1)
- [Chains 0.29.0](https://github.com/tektoncd/chains/releases/tag/v0.29.0)
- [Dashboard 0.73.0](https://github.com/tektoncd/dashboard/releases/tag/v0.73.0)
- [Pipelines 安全模型](https://github.com/tektoncd/pipeline/blob/v1.17.0/docs/security/README.md)
- [Affinity 和 PVC 生命周期](https://github.com/tektoncd/pipeline/blob/v1.17.0/docs/affinityassistants.md)
- [Pipelines 指标](https://github.com/tektoncd/pipeline/blob/v1.17.0/docs/metrics.md)
- [Chains 配置](https://github.com/tektoncd/chains/blob/v0.29.0/docs/config.md)
- [SLSA formatter 和类型提示](https://github.com/tektoncd/chains/blob/v0.29.0/docs/slsa-provenance.md)
- [BuildKit rootless 要求](https://github.com/moby/buildkit/blob/v0.33.0/docs/rootless.md)
- [Cosign 3.1.3](https://github.com/sigstore/cosign/releases/tag/v3.1.3)
- [CI 基础设施](./03-ci-pipelines.md)
- [GitOps 多集群](./04-gitops-multi-cluster.md)
- [可观测性技术栈](./09-observability-stack.md)
