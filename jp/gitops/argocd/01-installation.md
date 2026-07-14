# ArgoCD のインストール

> **サポート対象バージョン**: ArgoCD v2.9+
> **最終更新**: February 22, 2026

## 目次
- [前提条件](#前提条件)
- [インストール方法](#インストール方法)
- [CLI のインストール](#cli-のインストール)
- [初期アクセス](#初期アクセス)
- [高可用性のセットアップ](#高可用性のセットアップ)
- [Amazon EKS 上の ArgoCD](#amazon-eks-上の-argocd)
- [宣言的セットアップ](#宣言的セットアップ)
- [ArgoCD のアップグレード](#argocd-のアップグレード)

## 前提条件

ArgoCD をインストールする前に、以下を用意してください。

| 要件 | 最低バージョン | 注記 |
|-------------|-----------------|-------|
| Kubernetes | 1.24+ | ArgoCD のバージョン互換性を確認 |
| kubectl | 1.24+ | クラスターへのアクセスを設定済み |
| Helm | 3.8+ | Helm インストール方法で必要 |
| RAM | 2GB | 非 HA インストール用 |
| RAM | 8GB+ | HA インストール用 |

### 前提条件の確認

```bash
# Check Kubernetes version
kubectl version --short

# Check kubectl context
kubectl config current-context

# Verify cluster access
kubectl auth can-i create namespace --all-namespaces
```

## インストール方法

### 方法 1: プレーンマニフェスト（開始時に推奨）

公式マニフェストを使用する最も簡単なインストール方法です。

```bash
# Create namespace
kubectl create namespace argocd

# Install ArgoCD (non-HA)
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# Or install specific version
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/v2.13.0/manifests/install.yaml
```

高可用性の場合:

```bash
# Install HA manifests
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/ha/install.yaml
```

### 方法 2: Helm Chart（本番環境に推奨）

Helm chart はより多くの設定オプションを提供します。

```bash
# Add Argo Helm repository
helm repo add argo https://argoproj.github.io/argo-helm
helm repo update

# Install with default values
helm install argocd argo/argo-cd \
  --namespace argocd \
  --create-namespace

# Install with custom values
helm install argocd argo/argo-cd \
  --namespace argocd \
  --create-namespace \
  --values values.yaml
```

本番環境用の `values.yaml` の例:

```yaml
global:
  image:
    tag: v2.13.0

controller:
  replicas: 2
  metrics:
    enabled: true
    serviceMonitor:
      enabled: true

server:
  replicas: 2
  autoscaling:
    enabled: true
    minReplicas: 2
    maxReplicas: 5
  ingress:
    enabled: true
    ingressClassName: alb
    annotations:
      alb.ingress.kubernetes.io/scheme: internet-facing
      alb.ingress.kubernetes.io/target-type: ip
      alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:...
    hosts:
      - argocd.example.com
    tls:
      - hosts:
          - argocd.example.com
        secretName: argocd-tls

repoServer:
  replicas: 2
  autoscaling:
    enabled: true
    minReplicas: 2
    maxReplicas: 5

redis-ha:
  enabled: true

configs:
  params:
    server.insecure: true  # When using ALB TLS termination

notifications:
  enabled: true
```

### 方法 3: Kustomize

GitOps で管理する ArgoCD インストールの場合:

```yaml
# kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

namespace: argocd

resources:
  - https://raw.githubusercontent.com/argoproj/argo-cd/v2.13.0/manifests/install.yaml

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
kubectl apply -k .
```

## CLI のインストール

### macOS

```bash
# Using Homebrew
brew install argocd

# Or download binary
curl -sSL -o argocd-darwin-amd64 https://github.com/argoproj/argo-cd/releases/latest/download/argocd-darwin-amd64
sudo install -m 555 argocd-darwin-amd64 /usr/local/bin/argocd
rm argocd-darwin-amd64
```

### Linux

```bash
# Download latest version
curl -sSL -o argocd-linux-amd64 https://github.com/argoproj/argo-cd/releases/latest/download/argocd-linux-amd64

# Install binary
sudo install -m 555 argocd-linux-amd64 /usr/local/bin/argocd
rm argocd-linux-amd64

# Verify installation
argocd version --client
```

### Windows

```powershell
# Using Chocolatey
choco install argocd-cli

# Or download from releases
# https://github.com/argoproj/argo-cd/releases
```

## 初期アクセス

### オプション 1: Port Forwarding（開発環境）

```bash
# Forward API server port
kubectl port-forward svc/argocd-server -n argocd 8080:443

# Access at https://localhost:8080
```

### オプション 2: LoadBalancer Service

```bash
# Patch service type
kubectl patch svc argocd-server -n argocd -p '{"spec": {"type": "LoadBalancer"}}'

# Get external IP/hostname
kubectl get svc argocd-server -n argocd -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'
```

### オプション 3: Ingress（本番環境）

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: argocd-server-ingress
  namespace: argocd
  annotations:
    nginx.ingress.kubernetes.io/ssl-passthrough: "true"
    nginx.ingress.kubernetes.io/backend-protocol: "HTTPS"
spec:
  ingressClassName: nginx
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
  tls:
    - hosts:
        - argocd.example.com
      secretName: argocd-tls
```

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

# Login with password flag (for scripting)
argocd login localhost:8080 --username admin --password <password>
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

```mermaid
flowchart TB
    subgraph LB["Load Balancer"]
        ALB["AWS ALB / NGINX"]
    end

    subgraph API["API Server (2+ replicas)"]
        API1["argocd-server-1"]
        API2["argocd-server-2"]
    end

    subgraph CTRL["Controller (2+ sharded)"]
        CTRL1["controller-1"]
        CTRL2["controller-2"]
    end

    subgraph REPO["Repo Server (2+ replicas)"]
        REPO1["repo-server-1"]
        REPO2["repo-server-2"]
    end

    subgraph REDIS["Redis HA (3 nodes)"]
        R1["redis-1"]
        R2["redis-2"]
        R3["redis-3"]
    end

    ALB --> API1
    ALB --> API2
    API1 --> REDIS
    API2 --> REDIS
    CTRL1 --> REDIS
    CTRL2 --> REDIS
    REPO1 --> REDIS
    REPO2 --> REDIS

    classDef lb fill:#FF9900,stroke:#333,color:white
    classDef api fill:#EB6E85,stroke:#333,color:white
    classDef ctrl fill:#6f42c1,stroke:#333,color:white
    classDef repo fill:#28a745,stroke:#333,color:white
    classDef redis fill:#dc3545,stroke:#333,color:white

    class ALB lb
    class API1,API2 api
    class CTRL1,CTRL2 ctrl
    class REPO1,REPO2 repo
    class R1,R2,R3 redis
```

### Controller のシャーディング

大規模なデプロイメント（100+ applications）では、Controller のシャーディングを有効にします。

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-cmd-params-cm
  namespace: argocd
data:
  # Enable sharding with 2 replicas
  controller.sharding.algorithm: round-robin
  controller.replicas: "2"
```

または Helm 経由で設定します:

```yaml
controller:
  replicas: 2
  env:
    - name: ARGOCD_CONTROLLER_REPLICAS
      value: "2"
```

### Repo Server のスケーリング

```yaml
repoServer:
  replicas: 2
  autoscaling:
    enabled: true
    minReplicas: 2
    maxReplicas: 10
    targetCPUUtilizationPercentage: 80
    targetMemoryUtilizationPercentage: 80
  resources:
    requests:
      cpu: 500m
      memory: 512Mi
    limits:
      cpu: 2000m
      memory: 2Gi
```

### Redis HA の設定

```yaml
# Using Redis HA subchart
redis-ha:
  enabled: true
  exporter:
    enabled: true
  haproxy:
    enabled: true
    replicas: 3
  redis:
    replicas: 3
```

## Amazon EKS 上の ArgoCD

### ALB Ingress の設定

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: argocd-server
  namespace: argocd
  annotations:
    kubernetes.io/ingress.class: alb
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/backend-protocol: HTTPS
    alb.ingress.kubernetes.io/healthcheck-protocol: HTTPS
    alb.ingress.kubernetes.io/healthcheck-path: /healthz
    alb.ingress.kubernetes.io/listen-ports: '[{"HTTPS":443}]'
    alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:us-west-2:123456789012:certificate/xxx
    alb.ingress.kubernetes.io/ssl-policy: ELBSecurityPolicy-TLS-1-2-2017-01
    alb.ingress.kubernetes.io/group.name: argocd
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

TLS termination を使用して ALB を利用する場合は、ArgoCD が insecure mode で動作するように設定します:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-cmd-params-cm
  namespace: argocd
data:
  server.insecure: "true"
```

### IRSA の設定

ArgoCD コンポーネント用の IAM role を作成します:

```bash
# Create IAM policy
cat > argocd-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecr:GetAuthorizationToken",
        "ecr:BatchCheckLayerAvailability",
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue",
        "secretsmanager:DescribeSecret"
      ],
      "Resource": "arn:aws:secretsmanager:*:*:secret:argocd/*"
    }
  ]
}
EOF

aws iam create-policy \
  --policy-name ArgoCD-Policy \
  --policy-document file://argocd-policy.json
```

IRSA を作成します:

```bash
eksctl create iamserviceaccount \
  --cluster=my-cluster \
  --namespace=argocd \
  --name=argocd-repo-server \
  --attach-policy-arn=arn:aws:iam::123456789012:policy/ArgoCD-Policy \
  --override-existing-serviceaccounts \
  --approve
```

または Helm 経由:

```yaml
repoServer:
  serviceAccount:
    create: true
    name: argocd-repo-server
    annotations:
      eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/ArgoCD-RepoServer
```

### クロスアカウントのクラスターアクセス

他の AWS account のクラスターを管理する場合:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: production-cluster
  namespace: argocd
  labels:
    argocd.argoproj.io/secret-type: cluster
type: Opaque
stringData:
  name: production
  server: https://xxx.eks.amazonaws.com
  config: |
    {
      "awsAuthConfig": {
        "clusterName": "production-cluster",
        "roleARN": "arn:aws:iam::999999999999:role/ArgoCD-CrossAccount"
      }
    }
```

## 宣言的セットアップ

### argocd-cm ConfigMap

ArgoCD のコア設定:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-cm
  namespace: argocd
data:
  # ArgoCD URL (required for SSO and notifications)
  url: https://argocd.example.com

  # Enable anonymous access (not recommended for production)
  users.anonymous.enabled: "false"

  # Admin account enabled
  admin.enabled: "true"

  # Exec enabled for debugging
  exec.enabled: "true"

  # Status badge enabled
  statusbadge.enabled: "true"

  # Resource tracking method
  application.resourceTrackingMethod: annotation

  # Repositories (prefer secrets for credentials)
  repositories: |
    - url: https://github.com/myorg/myrepo.git
      name: myrepo
    - url: https://charts.helm.sh/stable
      name: helm-stable
      type: helm

  # Resource exclusions
  resource.exclusions: |
    - apiGroups:
        - cilium.io
      kinds:
        - CiliumIdentity
      clusters:
        - "*"

  # Resource custom health checks
  resource.customizations.health.argoproj.io_Application: |
    hs = {}
    hs.status = "Progressing"
    hs.message = ""
    if obj.status ~= nil then
      if obj.status.health ~= nil then
        hs.status = obj.status.health.status
        if obj.status.health.message ~= nil then
          hs.message = obj.status.health.message
        end
      end
    end
    return hs
```

### リポジトリ認証情報

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: repo-creds-github
  namespace: argocd
  labels:
    argocd.argoproj.io/secret-type: repo-creds
type: Opaque
stringData:
  url: https://github.com/myorg
  password: ghp_xxxxxxxxxxxx
  username: git
```

SSH 認証の場合:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: private-repo-ssh
  namespace: argocd
  labels:
    argocd.argoproj.io/secret-type: repository
type: Opaque
stringData:
  type: git
  url: git@github.com:myorg/private-repo.git
  sshPrivateKey: |
    -----BEGIN OPENSSH PRIVATE KEY-----
    ...
    -----END OPENSSH PRIVATE KEY-----
```

## ArgoCD のアップグレード

### アップグレード前のチェックリスト

1. 破壊的変更について**リリースノートを確認**する
2. **現在のインストールをバックアップ**する:
   ```bash
   kubectl get applications -n argocd -o yaml > applications-backup.yaml
   kubectl get appprojects -n argocd -o yaml > projects-backup.yaml
   kubectl get secrets -n argocd -l argocd.argoproj.io/secret-type -o yaml > secrets-backup.yaml
   ```
3. **クラスターの互換性を確認**する

### マニフェストによるアップグレード

```bash
# Apply new version manifests
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/v2.13.0/manifests/install.yaml

# Wait for rollout
kubectl rollout status deployment argocd-server -n argocd
kubectl rollout status deployment argocd-repo-server -n argocd
kubectl rollout status deployment argocd-application-controller -n argocd
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
  --version 5.55.0
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

**Pod が起動しない場合:**
```bash
# Check pod events
kubectl describe pod -n argocd -l app.kubernetes.io/name=argocd-server

# Check logs
kubectl logs -n argocd -l app.kubernetes.io/name=argocd-server --tail=100
```

**リポジトリ接続に失敗した場合:**
```bash
# Test repository access
argocd repo list
argocd repo get https://github.com/myorg/myrepo.git
```

**証明書の問題:**
```bash
# Check TLS certificates
kubectl get secret -n argocd argocd-secret -o jsonpath='{.data.tls\.crt}' | base64 -d | openssl x509 -text -noout
```

## クイズ

学んだ内容を確認するには、[ArgoCD インストールクイズ](../../quizzes/gitops/argocd/01-installation-quiz.md)に挑戦してください。
