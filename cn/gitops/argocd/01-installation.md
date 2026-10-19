# ArgoCD 安装

> **审查基线**：Argo CD 3.5.2 / Helm Chart 10.8.4；在审查发行说明后，清单和 CLI 固定版本更新为补丁版本 3.5.5（示例未重新运行）
> **最后更新**：2026 年 10 月 16 日

## 目录
- [先决条件](#prerequisites)
- [安装方式](#installation-methods)
- [CLI 安装](#cli-installation)
- [初始访问](#initial-access)
- [高可用设置](#high-availability-setup)
- [Amazon EKS 上的 ArgoCD](#argocd-on-amazon-eks)
- [声明式设置](#declarative-setup)
- [升级 ArgoCD](#upgrading-argocd)

## 先决条件 {#prerequisites}

这是自我管理安装指南。EKS 托管 Argo CD 使用单独的功能创建、授权和配置流程；不要在其中叠加自我管理安装。请查看[概览兼容性表](README.md)和 EKS 支持窗口。Chart 声明的最低 kubeVersion 并不代表经过测试或受支持。

拥有创建命名空间的权限，并不能证明拥有创建 CRD、ClusterRole 和绑定的权限。请检查实际上下文和授权情况。HA 资源包需要至少三个节点以实现反亲和性。请根据应用、集群和仓库规模评估 CPU/内存；并非所有场景都普遍需要固定为 10/50GB 的 Redis PVC。

```bash
kubectl version --client
kubectl config current-context
kubectl cluster-info
kubectl auth can-i create customresourcedefinitions.apiextensions.k8s.io
kubectl auth can-i create clusterrolebindings.rbac.authorization.k8s.io
```

## 安装方式 {#installation-methods}

请选择一种安装管理方式：manifests、Helm 或 Kustomize。以下非 HA/HA 命令是可选方案，并非需要按顺序执行的步骤。使用自定义命名空间时，还必须更新 ClusterRoleBindings 中的 ServiceAccount subjects。

### 方式 1：纯 Manifests（推荐入门使用）

使用官方 manifests 的最简单安装方式：

```bash
# Create namespace
kubectl create namespace argocd

# Install ArgoCD (non-HA)
kubectl apply --server-side -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/v3.5.5/manifests/install.yaml

```

要实现高可用：

```bash
# Install HA manifests
kubectl apply --server-side -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/v3.5.5/manifests/ha/install.yaml
```

### 方式 2：Helm Chart（推荐用于生产环境）

Helm chart 提供更多配置选项：

```bash
# Add Argo Helm repository
helm repo add argo https://argoproj.github.io/argo-helm
helm repo update

# Install with default values
helm install argocd argo/argo-cd --version 10.8.4 \
  --namespace argocd \
  --create-namespace

# Install with custom values
helm install argocd argo/argo-cd --version 10.8.4 \
  --namespace argocd \
  --create-namespace \
  --values values.yaml
```

Chart 10.8.4 部署的是 Argo CD v3.5.2（其 `appVersion`），而不是 manifests 示例固定使用的 3.5.5 补丁版本，因此缺少 3.5.4 的安全修复。Argo CD 3.5.5 首次随 chart 10.10.3 发布，这是本指南尚未审查的 chart 次版本更新；更改固定版本前请先阅读 chart 更新日志。

生产环境的 `values.yaml` 示例：

以下是需要在真实负载下调整的 HA 起始值。该 chart 会配置控制器分片数和 ApplicationSet leader election；Dex 仍保持一个副本。请选择默认安装或自定义安装中的一种。请先检查 `helm template` 的输出；仅当已安装 Operator CRD 时才启用 ServiceMonitor。

```yaml
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

### 方式 3：Kustomize

适用于由 GitOps 管理的 ArgoCD 安装：

```yaml
# kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

namespace: argocd

resources:
  - https://raw.githubusercontent.com/argoproj/argo-cd/v3.5.5/manifests/install.yaml

patches:
  - patch: |-
      - op: replace
        path: /spec/template/spec/containers/0/resources
        value:
          requests:
            cpu: 500m
            memory: 512Mi
          limits:
            cpu: 2000m
            memory: 2Gi
    target:
      kind: Deployment
      name: argocd-server

configMapGenerator:
  - name: argocd-cm
    behavior: merge
    literals:
      - url=https://argocd.example.com
```

使用以下命令应用：

```bash
kubectl apply --server-side -k .
```

## CLI 安装 {#cli-installation}

### Linux / macOS

将以下内容保存为脚本并运行。请确保 CPU 架构与服务器版本相匹配，并验证官方发行版校验和。在 macOS 上也可使用 Homebrew；请检查其安装的版本。

```bash
#!/usr/bin/env bash
set -euo pipefail
ARGOCD_VERSION=v3.5.5
case "$(uname -s)" in
  Linux) ARGOCD_OS=linux ;;
  Darwin) ARGOCD_OS=darwin ;;
  *) echo 'Select the release package for your OS' >&2; exit 1 ;;
esac
case "$(uname -m)" in
  x86_64) ARGOCD_ARCH=amd64 ;;
  arm64|aarch64) ARGOCD_ARCH=arm64 ;;
  *) echo 'Select a supported release architecture' >&2; exit 1 ;;
esac
ARGOCD_BINARY="argocd-${ARGOCD_OS}-${ARGOCD_ARCH}"
ARGOCD_INSTALL_TMP=$(mktemp -d)
trap 'rm -rf -- "$ARGOCD_INSTALL_TMP"' EXIT
cd "$ARGOCD_INSTALL_TMP"
curl --fail --location --remote-name \
  "https://github.com/argoproj/argo-cd/releases/download/${ARGOCD_VERSION}/${ARGOCD_BINARY}"
curl --fail --location --remote-name \
  "https://github.com/argoproj/argo-cd/releases/download/${ARGOCD_VERSION}/cli_checksums.txt"
EXPECTED=$(awk -v name="$ARGOCD_BINARY" '$2 == name || $2 == "*" name {print $1}' cli_checksums.txt)
[[ "$EXPECTED" =~ ^[a-f0-9]{64}$ ]]
if command -v sha256sum >/dev/null; then
  ACTUAL=$(sha256sum "$ARGOCD_BINARY" | awk '{print $1}')
else
  ACTUAL=$(shasum -a 256 "$ARGOCD_BINARY" | awk '{print $1}')
fi
[[ "$ACTUAL" == "$EXPECTED" ]]
sudo install -m 0755 "$ARGOCD_BINARY" /usr/local/bin/argocd
argocd version --client
```

### Windows

从 v3.5.5 发行版下载 `argocd-windows-amd64.exe` 和 `cli_checksums.txt`。将 `Get-FileHash -Algorithm SHA256` 的结果与对应的校验和条目进行比较。请将其安装到用户拥有的目录，并将该目录添加到用户 PATH；不要默认使用 System32。

### 自动补全

```bash
# Bash session
source <(argocd completion bash)
# Zsh alternative:
# source <(argocd completion zsh)
```

## 初始访问 {#initial-access}

### 选项 1：端口转发（开发环境）

```bash
# Forward API server port
kubectl port-forward svc/argocd-server -n argocd 8080:443

# Access at https://localhost:8080
```

### Ingress 访问

请使用仍在维护的控制器、有效证书和明确设置的访问边界。社区版 ingress-nginx 已于 2026 年 3 月退役，因此这里不将其作为新的默认选项。以下 EKS 部分提供了配置一致的内部 ALB/HTTPS 后端示例；如需使用其他控制器进行透传/gRPC，请遵循该控制器的文档。

### 获取初始密码

```bash
# Get the auto-generated admin password
kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath="{.data.password}" | base64 -d && echo
```

### 登录

```bash
# CLI login
argocd login argocd.example.com

# Or with port-forwarding
argocd login localhost:8080

# Use the interactive password prompt
argocd login localhost:8080 --username admin
```

### 更改管理员密码

```bash
# Update password interactively
argocd account update-password

# Delete the initial secret after changing password
kubectl -n argocd delete secret argocd-initial-admin-secret
```

## 高可用设置 {#high-availability-setup}

### HA 架构

![API/Repo 副本和 Application Controller 分片使用 Redis HA 缓存，并由 Sentinel 支持 Redis 故障转移。](../../.gitbook/assets/en-gitops-argocd-01-installation-0.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-gitops-argocd-01-installation-0.html)

请检查渲染后的 Helm 示例中以下内容。

- Application Controller 会将集群分配到多个分片，而不是使用一个全局 leader 和备用实例。该 chart 会使副本数与 `ARGOCD_CONTROLLER_REPLICAS` 保持一致。请验证算法、重新分配和恢复行为；动态分配是单独的功能。
- ApplicationSet leader election 与 Application Controller 分片不同。此 chart 会为多个 ApplicationSet 副本启用 leader election。
- 捆绑的 Dex 使用内存存储；增加副本可能会导致数据不一致。请保持默认的单副本设置，并针对额外的 HA 需求验证受支持的设计。
- Redis 是可丢弃的缓存；Kubernetes 对象会持久保存 Argo 配置。Redis HA 副本数由 `redis-ha.replicas` 设置，而不是 `redis-ha.redis.replicas`。该捆绑配置使用三个 Redis/Sentinel 实例。
- PDB 会限制自愿驱逐，但无法防止节点故障，也不能覆盖每一种滚动更新。请测试实例分布、就绪状态、依赖项和协调恢复。
- 请根据实际的 manifest 生成和内存负载调整 Repo Server 并发数、HPA 和 CPU 限制。不存在通用的“100 个应用就需要两个分片”阈值。

## Amazon EKS 上的 ArgoCD {#argocd-on-amazon-eks}

### ALB 和 TLS

此示例使用内部 ALB。请准备好 AWS Load Balancer Controller、子网/标签/安全组、DNS 和有效的同区域 ACM 证书。替换证书占位符/主机名，并确保管理客户端能够通过网络访问 ALB。

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: argocd-server
  namespace: argocd
  annotations:
    alb.ingress.kubernetes.io/scheme: internal
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/backend-protocol: HTTPS
    alb.ingress.kubernetes.io/healthcheck-protocol: HTTPS
    alb.ingress.kubernetes.io/healthcheck-path: /healthz
    alb.ingress.kubernetes.io/listen-ports: '[{"HTTPS":443}]'
    alb.ingress.kubernetes.io/certificate-arn: REPLACE_WITH_ACM_CERTIFICATE_ARN
    alb.ingress.kubernetes.io/ssl-policy: ELBSecurityPolicy-TLS13-1-2-2021-06
spec:
  ingressClassName: alb
  rules:
  - host: argocd.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: argocd-server
            port:
              number: 443
```

由于后端使用 HTTPS，请保持 `server.insecure=false`。通过此单一 HTTP target group 传输 CLI 流量时，请使用 `--grpc-web`。原生 gRPC 需要单独的 gRPC target group 和路由条件，详情请参阅上游文档。

```bash
argocd login argocd.example.com --grpc-web
```

### IRSA 和特定功能权限

仅添加 IAM 注解并不能配置 AWS 集成或令牌续期。请区分各项功能实际使用的身份。

| 功能 | 身份 |
|---|---|
| 部署到另一个 EKS API | Controller 以及所需的 ApplicationSet/Server 管理角色 → 目标 AssumeRole → EKS Access Entry/RBAC |
| 读取 OCI/Helm 源 | 实际的 Repo Server registry 身份验证、凭据提供程序和令牌续期 |
| 发现镜像/更新 Git | 单独的 Image Updater |
| 读取 Secrets Manager | 实际 AWS 调用方的角色，例如 External Secrets |
| 拉取 Pod 镜像 | 节点角色或 Fargate 执行角色 |

IRSA 需要 OIDC provider 和受 aud/sub 限制的信任关系；Pod Identity 需要 agent、关联配置和受支持的 SDK。请将目标信任关系和管理角色的 AssumeRole 权限限制为预期的 ARN。还需单独配置目标 EKS 访问条目、命名空间授权和 API 连通性。在需要的情况下，更改工作负载身份后请重新创建受影响的 Pod。

### 声明式 EKS 集群注册

建立角色和权限后，使用真实的 endpoint 和 CA 进行注册。请明确选择管理集群的 kubeconfig context。

```bash
# IAM roles, trust relationships and target EKS access/RBAC must already exist.
set -euo pipefail
: "${ARGOCD_CONTEXT:?Set the management cluster kubeconfig context}"
: "${TARGET_EKS_NAME:?Set the target EKS cluster name}"
: "${TARGET_AWS_REGION:?Set the target region}"
: "${TARGET_ROLE_ARN:?Set the authorized target-cluster IAM role}"
umask 077
aws eks describe-cluster --name "$TARGET_EKS_NAME" --region "$TARGET_AWS_REGION" \
  --query 'cluster.{name:name,server:endpoint,ca:certificateAuthority.data}' \
  --output json > target-eks.json
jq --arg role "$TARGET_ROLE_ARN" '{
  apiVersion:"v1", kind:"Secret",
  metadata:{name:"target-eks",namespace:"argocd",
    labels:{"argocd.argoproj.io/secret-type":"cluster"}},
  type:"Opaque",
  data:{name:(.name|@base64),server:(.server|@base64),config:({
    awsAuthConfig:{clusterName:.name,roleARN:$role},
    tlsClientConfig:{insecure:false,caData:.ca}
  }|tojson|@base64)}
}' target-eks.json > target-cluster-secret.json
kubectl --context "$ARGOCD_CONTEXT" apply -f target-cluster-secret.json
argocd cluster list
```

命令式命令 `argocd cluster add` 接受 kubeconfig context 名称。EKS 默认 context 可能是 ARN，但这并不意味着这是一个接受任意 ARN 的 AWS API。该命令可能会创建目标 ServiceAccount/RBAC 对象；请将其权限范围限制为所需的命名空间和权限。

## 声明式设置 {#declarative-setup}

对于 Helm，请在 values 中管理 `configs.cm`/`configs.params`。对于 manifests，请将以下必需键与现有设置合并。避免 Helm 和单独的 kubectl 管理方同时更改相同字段。

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-cm
  namespace: argocd
  labels:
    app.kubernetes.io/part-of: argocd
data:
  url: https://argocd.example.com
  users.anonymous.enabled: "false"
  exec.enabled: "false"
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-cmd-params-cm
  namespace: argocd
  labels:
    app.kubernetes.io/part-of: argocd
data:
  server.insecure: "false"
```

只有在测试 SSO 授权和恢复访问后，才设置 admin.enabled=false。请结合 ingress 路由和 server.rootpath/basehref 一起设计任何 /argocd 子路径；这并非默认要求。命令行/环境设置可能需要滚动重启相应组件。

对于受支持的资源（例如 Rollouts），优先使用内置健康检查。自定义 Lua 必须在 status 缺失时仍返回有效状态；不要将未知状态等同于 Healthy。自定义 Kustomize 版本需要配置 `kustomize.path.<version>` 并提供实际的可执行文件。请使用下方的 repository Secrets，而不要使用旧版 repositories/repository.credentials ConfigMap 字段。

### 仓库凭据

以下示例从受保护的文件创建初始 Secrets。请提供实际的用户/仓库/App ID，并仅授予所需的读取权限。不要将令牌、私钥或 base64 编码的 Secrets 提交到 Git。对于持续轮换，请使用 External Secrets 等单一管理方。

#### HTTPS 凭据模板

```bash
set -euo pipefail
# Bootstrap one credential method; use an external secret manager for rotation.
# Credential files must contain only their value, without an accidental trailing newline.
kubectl -n argocd create secret generic github-repo-creds \
  --from-literal=url=https://github.com/myorg/ \
  --from-file=username=/secure/path/github-user \
  --from-file=password=/secure/path/github-token
kubectl -n argocd label secret github-repo-creds \
  argocd.argoproj.io/secret-type=repo-creds
```

repo-creds 是 URL 前缀凭据模板；repository 则注册单个仓库。如果仓库已有显式凭据，请检查凭据优先级。

#### SSH

```bash
set -euo pipefail
kubectl -n argocd create secret generic private-repo-ssh \
  --from-literal=type=git \
  --from-literal=url=git@github.com:myorg/private-repo.git \
  --from-file=sshPrivateKey=/secure/path/id_ed25519
kubectl -n argocd label secret private-repo-ssh \
  argocd.argoproj.io/secret-type=repository
```

将 SSH 服务器主机密钥添加到 known hosts 之前，请通过可信渠道验证；不要信任未经验证的密钥扫描结果。

#### GitHub App

```bash
set -euo pipefail
kubectl -n argocd create secret generic github-app-creds \
  --from-literal=url=https://github.com/myorg/ \
  --from-literal=githubAppID=123456 \
  --from-literal=githubAppInstallationID=12345678 \
  --from-file=githubAppPrivateKey=/secure/path/github-app.pem
kubectl -n argocd label secret github-app-creds \
  argocd.argoproj.io/secret-type=repo-creds
```

## 升级 ArgoCD {#upgrading-argocd}

### 升级前检查清单

请审查从当前安装版本到目标版本之间所有相关的破坏性变更指南，并在 staging 环境中测试。不要假定将 2.x 直接替换为 3.5 版本就足够了。请保持相同的安装管理方式。对 Secret 备份进行加密并限制访问；不要将其提交到 Git。

1. **查看发行说明**，了解破坏性变更
2. **备份当前安装**：
   ```bash
   umask 077
   kubectl get applications,applicationsets -n argocd -o yaml > applications-backup.yaml
   kubectl get appprojects -n argocd -o yaml > projects-backup.yaml
   kubectl get secrets -n argocd -l argocd.argoproj.io/secret-type -o yaml > secrets-backup.yaml
   ```
3. **检查集群兼容性**、chart values、目标集群权限以及回滚/恢复流程。配置备份不包含应用数据库备份。

### 通过 Manifests 升级

```bash
# Apply new version manifests
kubectl apply --server-side -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/v3.5.5/manifests/install.yaml

# Wait for rollout
kubectl rollout status deployment argocd-server -n argocd
kubectl rollout status deployment argocd-repo-server -n argocd
kubectl rollout status statefulset/argocd-application-controller -n argocd
```

### 通过 Helm 升级

```bash
# Update repo
helm repo update

# Check available versions
helm search repo argo/argo-cd --versions

# Upgrade
helm upgrade argocd argo/argo-cd \
  --namespace argocd \
  --values values.yaml \
  --version 10.8.4
```

### 升级后验证

```bash
# Verify versions
argocd version

# Check all applications sync status
argocd app list

# Verify component health
kubectl get pods -n argocd
```

## 安装故障排查

### 常见问题

**Pod 无法启动：**
```bash
# Check pod events
kubectl describe pod -n argocd -l app.kubernetes.io/name=argocd-server

# Check logs
kubectl logs -n argocd -l app.kubernetes.io/name=argocd-server --tail=100
```

**仓库连接失败：**
```bash
# Test repository access
argocd repo list
argocd repo get https://github.com/myorg/myrepo.git
```

**证书问题：**
```bash
# Check TLS certificates
# Select the Secret actually used by the server (argocd-server-tls or its configured fallback).
: "${ARGOCD_TLS_SECRET:?Set the actual TLS Secret name}"
kubectl get secret -n argocd "$ARGOCD_TLS_SECRET" -o jsonpath='{.data.tls\.crt}' \
  | base64 -d | openssl x509 -noout -dates -subject -issuer
# An ALB frontend ACM certificate is a separate TLS layer.
```

## 测验

测试一下你学到的内容，试试 [ArgoCD 安装测验](../../quizzes/gitops/argocd/01-installation-quiz.md)。

### 参考资料

- [Argo CD 3.5.5 安装](https://github.com/argoproj/argo-cd/blob/v3.5.5/docs/operator-manual/installation.md)
- [Argo CD HA](https://github.com/argoproj/argo-cd/blob/v3.5.5/docs/operator-manual/high_availability.md)
- [EKS 和仓库设置](https://github.com/argoproj/argo-cd/blob/v3.5.5/docs/operator-manual/declarative-setup.md)
- [Ingress 和 gRPC](https://github.com/argoproj/argo-cd/blob/v3.5.5/docs/operator-manual/ingress.md)
- [Chart 10.8.4](https://github.com/argoproj/argo-helm/releases/tag/argo-cd-10.8.4)
- [Ingress NGINX 退役](https://kubernetes.io/blog/2025/11/11/ingress-nginx-retirement/)
