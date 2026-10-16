# ArgoCD のインストール

> **レビュー基準**: Argo CD 3.5.2 / Helm Chart 10.8.4。リリースノートのレビュー後、manifest と CLI のピンをパッチ 3.5.4 に更新しました（例は再実行していません）
> **最終更新**: October 12, 2026

## 目次
- [前提条件](#prerequisites)
- [インストール方法](#installation-methods)
- [CLI のインストール](#cli-installation)
- [初期アクセス](#initial-access)
- [高可用性のセットアップ](#high-availability-setup)
- [Amazon EKS 上の ArgoCD](#argocd-on-amazon-eks)
- [宣言的セットアップ](#declarative-setup)
- [ArgoCD のアップグレード](#upgrading-argocd)

## 前提条件

これはセルフマネージド型のインストールガイドです。EKS managed Argo CD では機能作成、認可、設定が分離されているため、そこにセルフマネージド型のインストールを重ねないでください。[概要の互換性表](README.md)および EKS のサポート期間を確認してください。Chart の最小 kubeVersion は、テスト済みまたはサポート対象である保証ではありません。

namespace を作成する権限があっても、CRD、ClusterRole、binding の権限があるとは限りません。実際の context と認可を確認してください。HA バンドルでは anti-affinity のために少なくとも 3 ノードが必要です。アプリケーション、cluster、repository の規模に応じて CPU と memory を測定してください。固定の 10/50GB Redis PVC が常に必要とは限りません。

```bash
kubectl version --client
kubectl config current-context
kubectl cluster-info
kubectl auth can-i create customresourcedefinitions.apiextensions.k8s.io
kubectl auth can-i create clusterrolebindings.rbac.authorization.k8s.io
```

## インストール方法

インストールの管理者として manifests、Helm、Kustomize のいずれか 1 つを選択してください。以下の非 HA/HA コマンドは順番に実行する手順ではなく、代替手段です。カスタム namespace では、ClusterRoleBindings の ServiceAccount subject も更新する必要があります。

### 方法 1: プレーンな Manifest（開始時に推奨）

公式 manifest を使用する最も簡単なインストール方法です。

```bash
# Create namespace
kubectl create namespace argocd

# Install ArgoCD (non-HA)
kubectl apply --server-side -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/v3.5.4/manifests/install.yaml

```

高可用性の場合:

```bash
# Install HA manifests
kubectl apply --server-side -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/v3.5.4/manifests/ha/install.yaml
```

### 方法 2: Helm Chart（本番環境に推奨）

Helm Chart はより多くの設定オプションを提供します。

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

Chart 10.8.4 は、manifest の例でピン留めした 3.5.4 パッチではなく Argo CD v3.5.2（その `appVersion`）を deploy するため、3.5.4 のセキュリティ修正を含みません。Argo CD 3.5.4 が最初に提供されるのは chart 10.9.7 ですが、これはこのガイドでレビューしていない chart のマイナーアップデートです。ピンを変更する前に chart の changelog を読んでください。

本番環境用の `values.yaml` の例:

これらは実際の負荷に合わせて調整する HA の開始値です。Chart は controller の shard 数と ApplicationSet の leader election を設定します。Dex は 1 replica のままです。デフォルトまたはカスタムのインストールのいずれかを選択してください。まず `helm template` の出力をレビューし、Operator CRD がインストールされている場合にのみ ServiceMonitor を有効にしてください。

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

### 方法 3: Kustomize

GitOps 管理の ArgoCD インストールの場合:

```yaml
# kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

namespace: argocd

resources:
  - https://raw.githubusercontent.com/argoproj/argo-cd/v3.5.4/manifests/install.yaml

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

次のコマンドで適用します:

```bash
kubectl apply --server-side -k .
```

## CLI のインストール

### Linux / macOS

以下をスクリプトとして保存して実行してください。CPU architecture と server version を一致させ、公式リリースの checksum を検証してください。macOS では Homebrew も代替手段ですが、インストールされる version を確認してください。

```bash
#!/usr/bin/env bash
set -euo pipefail
ARGOCD_VERSION=v3.5.4
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

v3.5.4 リリースから `argocd-windows-amd64.exe` と `cli_checksums.txt` をダウンロードしてください。`Get-FileHash -Algorithm SHA256` を対応する checksum エントリと比較してください。System32 をデフォルトとして使用せず、ユーザーが所有する directory にインストールしてユーザー PATH に追加してください。

### 補完

```bash
# Bash session
source <(argocd completion bash)
# Zsh alternative:
# source <(argocd completion zsh)
```

## 初期アクセス

### オプション 1: Port Forwarding（開発環境）

```bash
# Forward API server port
kubectl port-forward svc/argocd-server -n argocd 8080:443

# Access at https://localhost:8080
```

### Ingress アクセス

メンテナンスされている controller、有効な certificate、意図的に設定したアクセス境界を使用してください。Community ingress-nginx は 2026 年 3 月に廃止され、ここでは新たなデフォルトではありません。以下の EKS セクションでは一貫した internal ALB/HTTPS-backend の例を示します。passthrough/gRPC については別の controller のドキュメントに従ってください。

### 初期パスワードの取得

```bash
# Get the auto-generated admin password
kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath="{.data.password}" | base64 -d && echo
```

### ログイン

```bash
# CLI login
argocd login argocd.example.com

# Or with port-forwarding
argocd login localhost:8080

# Use the interactive password prompt
argocd login localhost:8080 --username admin
```

### Admin パスワードの変更

```bash
# Update password interactively
argocd account update-password

# Delete the initial secret after changing password
kubectl -n argocd delete secret argocd-initial-admin-secret
```

## 高可用性のセットアップ

### HA アーキテクチャ

![API/Repo replica と Application Controller shard は Redis HA cache を使用し、Sentinel が Redis failover をサポートします。](../../.gitbook/assets/en-gitops-argocd-01-installation-0.png)

[🔍 インタラクティブな図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-gitops-argocd-01-installation-0.html)

レンダリングされた Helm の例では、次の項目を確認してください。

- Application Controller は、1 つのグローバル leader と standby を使用するのではなく、cluster を shard 間に分散します。Chart は replica 数を `ARGOCD_CONTROLLER_REPLICAS` に合わせます。algorithm、再分散、復旧を検証してください。動的分散は別の機能です。
- ApplicationSet の leader election は Application Controller の sharding とは異なります。この chart では複数の ApplicationSet replica に対して leader election を有効にします。
- バンドルされた Dex は in-memory storage を使用します。replica を追加するとデータに不整合が生じる可能性があります。デフォルトの single replica を維持し、追加の HA 要件にはサポートされる設計を検証してください。
- Redis は破棄可能な cache であり、Kubernetes object は Argo 設定を永続化します。Redis HA の replica 数は `redis-ha.redis.replicas` ではなく `redis-ha.replicas` です。このバンドルは 3 つの Redis/Sentinel instance を使用します。
- PDB は任意の eviction を制限しますが、node 障害やすべての rollout を対象とするものではありません。分散、readiness、dependency、reconciliation の復旧をテストしてください。
- 実際の manifest-generation/memory 負荷に基づいて Repo Server の concurrency、HPA、CPU limit を調整してください。「100 apps は 2 shard」という普遍的な閾値はありません。

## Amazon EKS 上の ArgoCD

### ALB と TLS

この例では internal ALB を使用します。AWS Load Balancer Controller、subnet/tag/security group、DNS、および有効な同一 region の ACM certificate を準備してください。certificate の placeholder/hostname を置き換え、管理 client に ALB へのネットワークアクセスを提供してください。

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

backend が HTTPS を使用するため、`server.insecure=false` を維持してください。この単一の HTTP target group を通る CLI traffic には `--grpc-web` を使用してください。native gRPC には、upstream のドキュメントにあるとおり、別の gRPC target group と routing condition が必要です。

```bash
argocd login argocd.example.com --grpc-web
```

### IRSA と機能別の権限

IAM annotation だけでは AWS integration や token renewal を設定できません。機能ごとに実際の identity を区別してください。

| 機能 | Identity |
|---|---|
| 別の EKS API への deploy | Controller および必要な ApplicationSet/Server management role → target AssumeRole → EKS Access Entry/RBAC |
| OCI/Helm source の読み取り | 実際の Repo Server の registry authentication、credential provider、token renewal |
| image の検出/Git の更新 | 個別の Image Updater |
| Secrets Manager の読み取り | External Secrets など、実際の AWS caller の role |
| Pod image の pull | Node role または Fargate execution role |

IRSA には OIDC provider と aud/sub で制約した trust が必要です。Pod Identity には agent、association、対応 SDK が必要です。target trust と management-role の AssumeRole 権限を意図した ARN に制限してください。target EKS access entry、namespace authorization、API connectivity も個別に設定してください。必要に応じて workload identity を変更した後、影響を受ける Pod を再作成してください。

### 宣言的な EKS Cluster 登録

role と権限を確立した後、実際の endpoint と CA を使用して登録します。management-cluster の kubeconfig context を明示的に選択してください。

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

命令的な `argocd cluster add` は kubeconfig context 名を受け取ります。EKS のデフォルト context は ARN の場合がありますが、これは任意の ARN を受け付ける AWS API ではありません。target ServiceAccount/RBAC object を作成する場合があるため、必要な namespace と権限に scope を限定してください。

## 宣言的セットアップ

Helm では values 内の `configs.cm`/`configs.params` を管理してください。manifest では、以下の必須 key を既存の設定に merge してください。Helm と別の kubectl 管理者が同じ field を競合して管理しないようにしてください。

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

SSO authorization と recovery access をテストした後にのみ admin.enabled=false を設定してください。/argocd subpath は ingress route および server.rootpath/basehref とともに設計してください。これはデフォルト要件ではありません。command-line/environment 設定では component rollout が必要になる場合があります。

Rollouts などのサポート対象 resource には、組み込みの health check を優先してください。カスタム Lua は status がない場合でも有効な state を返す必要があります。unknown を Healthy と同一視しないでください。カスタム Kustomize version には `kustomize.path.<version>` と実際の executable が必要です。legacy の repositories/repository.credentials ConfigMap field ではなく、以下の repository Secret を使用してください。

### Repository Credential

これらの例では、保護された file から Secret を bootstrap します。実際の user/repository/App ID と、必要な read 権限のみを指定してください。token、private key、base64 の Secret を Git に commit しないでください。継続的な rotation には External Secrets などの単一の管理者を使用してください。

#### HTTPS credential template

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

repo-creds は URL-prefix の credential template であり、repository は 1 つの repository を登録します。repository にすでに明示的な credential がある場合は、precedence を確認してください。

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

SSH server host key を known hosts に追加する前に、信頼できる channel を通じて検証してください。未検証の key scan を信頼しないでください。

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

## ArgoCD のアップグレード

### アップグレード前のチェックリスト

インストール済み version から target までの関連するすべての breaking-change ガイドをレビューし、staging でテストしてください。2.x から 3.5 への直接的な version 置換で十分だと想定しないでください。同じインストール管理者を維持してください。Secret backup を暗号化してアクセスを制限してください。Git に commit しても安全ではありません。

1. **リリースノートをレビュー**して breaking change を確認する
2. **現在のインストールを backup**する:
   ```bash
   umask 077
   kubectl get applications,applicationsets -n argocd -o yaml > applications-backup.yaml
   kubectl get appprojects -n argocd -o yaml > projects-backup.yaml
   kubectl get secrets -n argocd -l argocd.argoproj.io/secret-type -o yaml > secrets-backup.yaml
   ```
3. **cluster の互換性**、chart value、target-cluster 権限、rollback/restore 手順を確認する。設定の backup では application database は backup されません。

### Manifest によるアップグレード

```bash
# Apply new version manifests
kubectl apply --server-side -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/v3.5.4/manifests/install.yaml

# Wait for rollout
kubectl rollout status deployment argocd-server -n argocd
kubectl rollout status deployment argocd-repo-server -n argocd
kubectl rollout status statefulset/argocd-application-controller -n argocd
```

### Helm によるアップグレード

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

### アップグレード後の検証

```bash
# Verify versions
argocd version

# Check all applications sync status
argocd app list

# Verify component health
kubectl get pods -n argocd
```

## インストールのトラブルシューティング

### よくある問題

**Pod が起動しない:**
```bash
# Check pod events
kubectl describe pod -n argocd -l app.kubernetes.io/name=argocd-server

# Check logs
kubectl logs -n argocd -l app.kubernetes.io/name=argocd-server --tail=100
```

**Repository 接続の失敗:**
```bash
# Test repository access
argocd repo list
argocd repo get https://github.com/myorg/myrepo.git
```

**Certificate の問題:**
```bash
# Check TLS certificates
# Select the Secret actually used by the server (argocd-server-tls or its configured fallback).
: "${ARGOCD_TLS_SECRET:?Set the actual TLS Secret name}"
kubectl get secret -n argocd "$ARGOCD_TLS_SECRET" -o jsonpath='{.data.tls\.crt}' \
  | base64 -d | openssl x509 -noout -dates -subject -issuer
# An ALB frontend ACM certificate is a separate TLS layer.
```

## クイズ

学んだ内容をテストするには、[ArgoCD インストールクイズ](../../quizzes/gitops/argocd/01-installation-quiz.md)に挑戦してください。

### 参照ソース

- [Argo CD 3.5.4 のインストール](https://github.com/argoproj/argo-cd/blob/v3.5.4/docs/operator-manual/installation.md)
- [Argo CD HA](https://github.com/argoproj/argo-cd/blob/v3.5.4/docs/operator-manual/high_availability.md)
- [EKS と repository のセットアップ](https://github.com/argoproj/argo-cd/blob/v3.5.4/docs/operator-manual/declarative-setup.md)
- [Ingress と gRPC](https://github.com/argoproj/argo-cd/blob/v3.5.4/docs/operator-manual/ingress.md)
- [Chart 10.8.4](https://github.com/argoproj/argo-helm/releases/tag/argo-cd-10.8.4)
- [Ingress NGINX の廃止](https://kubernetes.io/blog/2025/11/11/ingress-nginx-retirement/)
