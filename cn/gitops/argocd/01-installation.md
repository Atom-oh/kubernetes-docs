# ArgoCD 安装

> **支持的版本**: ArgoCD v2.9+
> **最后更新**: February 22, 2026

## 目录
- [前提条件](#前提条件)
- [安装方法](#安装方法)
- [CLI 安装](#cli-安装)
- [初始访问](#初始访问)
- [高可用性设置](#高可用性设置)
- [Amazon EKS 上的 ArgoCD](#amazon-eks-上的-argocd)
- [声明式设置](#声明式设置)
- [升级 ArgoCD](#升级-argocd)

## 前提条件

安装 ArgoCD 前，请确保具备：

| 要求 | 最低版本 | 说明 |
|-------------|-----------------|-------|
| Kubernetes | 1.24+ | 检查 ArgoCD 版本兼容性 |
| kubectl | 1.24+ | 已配置集群访问权限 |
| Helm | 3.8+ | Helm 安装方法所需 |
| RAM | 2GB | 用于非 HA 安装 |
| RAM | 8GB+ | 用于 HA 安装 |

### 验证前提条件

```bash
# Check Kubernetes version
kubectl version --short

# Check kubectl context
kubectl config current-context

# Verify cluster access
kubectl auth can-i create namespace --all-namespaces
```

## 安装方法

### 方法 1：纯 Manifest（推荐用于入门）

使用官方 Manifest 的最简单安装方法：

```bash
# Create namespace
kubectl create namespace argocd

# Install ArgoCD (non-HA)
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# Or install specific version
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/v2.13.0/manifests/install.yaml
```

如需高可用性：

```bash
# Install HA manifests
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/ha/install.yaml
```

### 方法 2：Helm Chart（推荐用于生产环境）

Helm Chart 提供更多配置选项：

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

用于生产环境的 `values.yaml` 示例：

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

### 方法 3：Kustomize

适用于由 GitOps 管理的 ArgoCD 安装：

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

应用：

```bash
kubectl apply -k .
```

## CLI 安装

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

## 初始访问

### 选项 1：端口转发（开发环境）

```bash
# Forward API server port
kubectl port-forward svc/argocd-server -n argocd 8080:443

# Access at https://localhost:8080
```

### 选项 2：LoadBalancer Service

```bash
# Patch service type
kubectl patch svc argocd-server -n argocd -p '{"spec": {"type": "LoadBalancer"}}'

# Get external IP/hostname
kubectl get svc argocd-server -n argocd -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'
```

### 选项 3：Ingress（生产环境）

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

# Login with password flag (for scripting)
argocd login localhost:8080 --username admin --password <password>
```

### 更改管理员密码

```bash
# Update password interactively
argocd account update-password

# Delete the initial secret after changing password
kubectl -n argocd delete secret argocd-initial-admin-secret
```

## 高可用性设置

### HA 架构

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

### Controller 分片

对于大型部署（100+ 个应用程序），启用 Controller 分片：

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

或者通过 Helm 配置：

```yaml
controller:
  replicas: 2
  env:
    - name: ARGOCD_CONTROLLER_REPLICAS
      value: "2"
```

### Repo Server 扩缩容

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

### Redis HA 配置

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

## Amazon EKS 上的 ArgoCD

### ALB Ingress 配置

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

将 ALB 与 TLS 终止结合使用时，配置 ArgoCD 以不安全模式运行：

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-cmd-params-cm
  namespace: argocd
data:
  server.insecure: "true"
```

### IRSA 配置

为 ArgoCD 组件创建 IAM role：

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

创建 IRSA：

```bash
eksctl create iamserviceaccount \
  --cluster=my-cluster \
  --namespace=argocd \
  --name=argocd-repo-server \
  --attach-policy-arn=arn:aws:iam::123456789012:policy/ArgoCD-Policy \
  --override-existing-serviceaccounts \
  --approve
```

或者通过 Helm：

```yaml
repoServer:
  serviceAccount:
    create: true
    name: argocd-repo-server
    annotations:
      eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/ArgoCD-RepoServer
```

### 跨账户集群访问

用于管理其他 AWS 账户中的集群：

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

## 声明式设置

### argocd-cm ConfigMap

ArgoCD 的核心配置：

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

### Repository 凭证

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

对于 SSH 身份验证：

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

## 升级 ArgoCD

### 升级前检查清单

1. **查看发行说明**，了解破坏性变更
2. **备份当前安装**：
   ```bash
   kubectl get applications -n argocd -o yaml > applications-backup.yaml
   kubectl get appprojects -n argocd -o yaml > projects-backup.yaml
   kubectl get secrets -n argocd -l argocd.argoproj.io/secret-type -o yaml > secrets-backup.yaml
   ```
3. **检查集群兼容性**

### 通过 Manifest 升级

```bash
# Apply new version manifests
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/v2.13.0/manifests/install.yaml

# Wait for rollout
kubectl rollout status deployment argocd-server -n argocd
kubectl rollout status deployment argocd-repo-server -n argocd
kubectl rollout status deployment argocd-application-controller -n argocd
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
  --version 5.55.0
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

## 安装故障排除

### 常见问题

**Pod 无法启动：**
```bash
# Check pod events
kubectl describe pod -n argocd -l app.kubernetes.io/name=argocd-server

# Check logs
kubectl logs -n argocd -l app.kubernetes.io/name=argocd-server --tail=100
```

**Repository 连接失败：**
```bash
# Test repository access
argocd repo list
argocd repo get https://github.com/myorg/myrepo.git
```

**证书问题：**
```bash
# Check TLS certificates
kubectl get secret -n argocd argocd-secret -o jsonpath='{.data.tls\.crt}' | base64 -d | openssl x509 -text -noout
```

## 测验

若要测试所学内容，请尝试 [ArgoCD 安装测验](../../quizzes/gitops/argocd/01-installation-quiz.md)。
