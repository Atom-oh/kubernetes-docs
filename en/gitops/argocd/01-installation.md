# ArgoCD Installation

> **Supported Versions**: ArgoCD v2.9+
> **Last Updated**: February 21, 2025

## Table of Contents
- [Prerequisites](#prerequisites)
- [Installation Methods](#installation-methods)
- [CLI Installation](#cli-installation)
- [Initial Access](#initial-access)
- [High Availability Setup](#high-availability-setup)
- [ArgoCD on Amazon EKS](#argocd-on-amazon-eks)
- [Declarative Setup](#declarative-setup)
- [Upgrading ArgoCD](#upgrading-argocd)

## Prerequisites

Before installing ArgoCD, ensure you have:

| Requirement | Minimum Version | Notes |
|-------------|-----------------|-------|
| Kubernetes | 1.24+ | Check ArgoCD version compatibility |
| kubectl | 1.24+ | Configured with cluster access |
| Helm | 3.8+ | Required for Helm installation method |
| RAM | 2GB | For non-HA installation |
| RAM | 8GB+ | For HA installation |

### Verify Prerequisites

```bash
# Check Kubernetes version
kubectl version --short

# Check kubectl context
kubectl config current-context

# Verify cluster access
kubectl auth can-i create namespace --all-namespaces
```

## Installation Methods

### Method 1: Plain Manifests (Recommended for Getting Started)

The simplest installation method using official manifests:

```bash
# Create namespace
kubectl create namespace argocd

# Install ArgoCD (non-HA)
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# Or install specific version
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/v2.13.0/manifests/install.yaml
```

For high availability:

```bash
# Install HA manifests
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/ha/install.yaml
```

### Method 2: Helm Chart (Recommended for Production)

The Helm chart provides more configuration options:

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

Example `values.yaml` for production:

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

### Method 3: Kustomize

For GitOps-managed ArgoCD installations:

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

Apply with:

```bash
kubectl apply -k .
```

## CLI Installation

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

## Initial Access

### Option 1: Port Forwarding (Development)

```bash
# Forward API server port
kubectl port-forward svc/argocd-server -n argocd 8080:443

# Access at https://localhost:8080
```

### Option 2: LoadBalancer Service

```bash
# Patch service type
kubectl patch svc argocd-server -n argocd -p '{"spec": {"type": "LoadBalancer"}}'

# Get external IP/hostname
kubectl get svc argocd-server -n argocd -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'
```

### Option 3: Ingress (Production)

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

### Retrieve Initial Password

```bash
# Get the auto-generated admin password
kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath="{.data.password}" | base64 -d && echo
```

### Login

```bash
# CLI login
argocd login argocd.example.com

# Or with port-forwarding
argocd login localhost:8080

# Login with password flag (for scripting)
argocd login localhost:8080 --username admin --password <password>
```

### Change Admin Password

```bash
# Update password interactively
argocd account update-password

# Delete the initial secret after changing password
kubectl -n argocd delete secret argocd-initial-admin-secret
```

## High Availability Setup

### HA Architecture

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

### Controller Sharding

For large deployments (100+ applications), enable controller sharding:

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

Or configure via Helm:

```yaml
controller:
  replicas: 2
  env:
    - name: ARGOCD_CONTROLLER_REPLICAS
      value: "2"
```

### Repo Server Scaling

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

### Redis HA Configuration

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

## ArgoCD on Amazon EKS

### ALB Ingress Configuration

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

When using ALB with TLS termination, configure ArgoCD to run in insecure mode:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-cmd-params-cm
  namespace: argocd
data:
  server.insecure: "true"
```

### IRSA Configuration

Create IAM role for ArgoCD components:

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

Create IRSA:

```bash
eksctl create iamserviceaccount \
  --cluster=my-cluster \
  --namespace=argocd \
  --name=argocd-repo-server \
  --attach-policy-arn=arn:aws:iam::123456789012:policy/ArgoCD-Policy \
  --override-existing-serviceaccounts \
  --approve
```

Or via Helm:

```yaml
repoServer:
  serviceAccount:
    create: true
    name: argocd-repo-server
    annotations:
      eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/ArgoCD-RepoServer
```

### Cross-Account Cluster Access

For managing clusters in other AWS accounts:

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

## Declarative Setup

### argocd-cm ConfigMap

Core configuration for ArgoCD:

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

### Repository Credentials

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

For SSH authentication:

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

## Upgrading ArgoCD

### Pre-Upgrade Checklist

1. **Review release notes** for breaking changes
2. **Backup current installation**:
   ```bash
   kubectl get applications -n argocd -o yaml > applications-backup.yaml
   kubectl get appprojects -n argocd -o yaml > projects-backup.yaml
   kubectl get secrets -n argocd -l argocd.argoproj.io/secret-type -o yaml > secrets-backup.yaml
   ```
3. **Check cluster compatibility**

### Upgrade via Manifests

```bash
# Apply new version manifests
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/v2.13.0/manifests/install.yaml

# Wait for rollout
kubectl rollout status deployment argocd-server -n argocd
kubectl rollout status deployment argocd-repo-server -n argocd
kubectl rollout status deployment argocd-application-controller -n argocd
```

### Upgrade via Helm

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

### Post-Upgrade Verification

```bash
# Verify versions
argocd version

# Check all applications sync status
argocd app list

# Verify component health
kubectl get pods -n argocd
```

## Troubleshooting Installation

### Common Issues

**Pods not starting:**
```bash
# Check pod events
kubectl describe pod -n argocd -l app.kubernetes.io/name=argocd-server

# Check logs
kubectl logs -n argocd -l app.kubernetes.io/name=argocd-server --tail=100
```

**Repository connection failed:**
```bash
# Test repository access
argocd repo list
argocd repo get https://github.com/myorg/myrepo.git
```

**Certificate issues:**
```bash
# Check TLS certificates
kubectl get secret -n argocd argocd-secret -o jsonpath='{.data.tls\.crt}' | base64 -d | openssl x509 -text -noout
```

## Quiz

To test what you've learned, try the [ArgoCD installation quiz](../../quizzes/gitops/argocd/01-installation-quiz.md).
