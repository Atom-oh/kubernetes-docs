# ArgoCD 最佳实践

> **支持的版本**: ArgoCD v2.9+
> **最后更新**: February 22, 2026

## 目录
- [仓库结构](#repository-structure)
- [环境提升](#environment-promotion)
- [资源管理](#resource-management)
- [性能调优](#performance-tuning)
- [灾难恢复](#disaster-recovery)
- [升级策略](#upgrade-strategies)
- [故障排除](#troubleshooting)
- [EKS 最佳实践](#eks-best-practices)
- [生产环境检查清单](#production-checklist)

## 仓库结构

### Monorepo 模式

用于所有应用程序和环境的单一仓库：

```
gitops-repo/
├── apps/
│   ├── app-a/
│   │   ├── base/
│   │   │   ├── deployment.yaml
│   │   │   ├── service.yaml
│   │   │   └── kustomization.yaml
│   │   └── overlays/
│   │       ├── dev/
│   │       │   ├── kustomization.yaml
│   │       │   └── patch.yaml
│   │       ├── staging/
│   │       │   ├── kustomization.yaml
│   │       │   └── patch.yaml
│   │       └── production/
│   │           ├── kustomization.yaml
│   │           └── patch.yaml
│   └── app-b/
│       └── ...
├── platform/
│   ├── argocd/
│   ├── monitoring/
│   └── ingress/
└── clusters/
    ├── dev/
    ├── staging/
    └── production/
```

**优点：**
- 单一事实来源
- 便于跨应用程序变更
- 简化 CI/CD
- 原子化多应用程序更新

**缺点：**
- 可能变得庞大
- 访问控制复杂
- 单点故障

### Polyrepo 模式

按应用程序或团队划分的独立仓库：

```
Organization:
├── gitops-platform/          # Platform team
│   ├── argocd/
│   ├── monitoring/
│   └── ingress/
├── gitops-team-a/            # Team A applications
│   ├── app-a/
│   └── app-b/
├── gitops-team-b/            # Team B applications
│   ├── app-c/
│   └── app-d/
└── gitops-infra/             # Infrastructure
    ├── terraform/
    └── clusters/
```

**优点：**
- 归属明确
- 独立部署
- 细粒度访问控制
- 仓库规模更小

**缺点：**
- 变更协调更困难
- 需要管理更多仓库
- 可能发生漂移

### App of Apps 仓库结构

```
gitops-root/
├── argocd-apps/
│   ├── Chart.yaml
│   ├── values.yaml
│   ├── values-dev.yaml
│   ├── values-staging.yaml
│   ├── values-production.yaml
│   └── templates/
│       ├── _helpers.tpl
│       ├── namespace.yaml
│       ├── project.yaml
│       ├── app-a.yaml
│       ├── app-b.yaml
│       └── platform-apps.yaml
└── bootstrap/
    └── root-app.yaml
```

### 推荐命名约定

| 类型 | 模式 | 示例 |
|------|---------|---------|
| Application | `{app}-{env}` | `frontend-production` |
| Project | `{team}` or `{env}` | `platform`, `production` |
| Namespace | `{app}` or `{app}-{env}` | `frontend`, `frontend-prod` |
| 仓库 | `gitops-{scope}` | `gitops-platform` |

## 环境提升

### Git 分支策略

```mermaid
flowchart LR
    subgraph BRANCHES["Git Branches"]
        DEV["develop"]
        STG["staging"]
        MAIN["main"]
    end

    subgraph ENVS["Environments"]
        E_DEV["Dev Cluster"]
        E_STG["Staging Cluster"]
        E_PROD["Production Cluster"]
    end

    DEV -->|"merge"| STG
    STG -->|"merge"| MAIN

    DEV -->|"deploy"| E_DEV
    STG -->|"deploy"| E_STG
    MAIN -->|"deploy"| E_PROD

    classDef branch fill:#f9f9f9,stroke:#333,color:black
    classDef env fill:#326CE5,stroke:#333,color:white

    class DEV,STG,MAIN branch
    class E_DEV,E_STG,E_PROD env
```

### 基于目录的提升

```yaml
# overlays/dev/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - ../../base
images:
  - name: myapp
    newTag: dev-abc1234

# overlays/staging/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - ../../base
images:
  - name: myapp
    newTag: v1.2.3-rc1

# overlays/production/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - ../../base
images:
  - name: myapp
    newTag: v1.2.3
```

### 自动化提升流水线

```yaml
# .github/workflows/promote.yaml
name: Promote to Production
on:
  workflow_dispatch:
    inputs:
      version:
        description: 'Version to promote'
        required: true

jobs:
  promote:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Update production overlay
        run: |
          cd overlays/production
          kustomize edit set image myapp=myregistry/myapp:${{ github.event.inputs.version }}

      - name: Create Pull Request
        uses: peter-evans/create-pull-request@v5
        with:
          title: "Promote ${{ github.event.inputs.version }} to production"
          branch: promote/${{ github.event.inputs.version }}
          commit-message: "chore: promote ${{ github.event.inputs.version }} to production"
```

## 资源管理

### ArgoCD 组件资源

```yaml
# Helm values for production
controller:
  resources:
    requests:
      cpu: 500m
      memory: 512Mi
    limits:
      cpu: 2000m
      memory: 2Gi

server:
  resources:
    requests:
      cpu: 250m
      memory: 256Mi
    limits:
      cpu: 1000m
      memory: 1Gi

repoServer:
  resources:
    requests:
      cpu: 500m
      memory: 512Mi
    limits:
      cpu: 2000m
      memory: 2Gi

redis:
  resources:
    requests:
      cpu: 100m
      memory: 128Mi
    limits:
      cpu: 500m
      memory: 512Mi
```

### 按规模划分的资源限制

| 规模 | Applications | Controller CPU | Controller 内存 | Repo Server CPU | Repo Server 内存 |
|-------|--------------|----------------|-------------------|-----------------|-------------------|
| 小型 | < 50 | 500m | 512Mi | 500m | 512Mi |
| 中型 | 50-200 | 1000m | 1Gi | 1000m | 1Gi |
| 大型 | 200-500 | 2000m | 2Gi | 2000m | 2Gi |
| 超大型 | > 500 | 4000m | 4Gi | 4000m | 4Gi |

### Horizontal Pod Autoscaler

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: argocd-repo-server
  namespace: argocd
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: argocd-repo-server
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80
```

## 性能调优

### Controller 优化

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-cmd-params-cm
  namespace: argocd
data:
  # Reduce reconciliation frequency
  controller.status.processors: "50"
  controller.operation.processors: "25"
  controller.self.heal.timeout.seconds: "5"

  # Increase cache TTL
  controller.repo.server.timeout.seconds: "180"

  # Sharding for large deployments
  controller.sharding.algorithm: round-robin
```

### Repo Server 优化

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-cmd-params-cm
  namespace: argocd
data:
  # Increase parallelism
  reposerver.parallelism.limit: "10"

  # Cache settings
  reposerver.repo.cache.expiration: "24h"

  # Git optimization
  reposerver.git.request.timeout: "60s"
  reposerver.git.lsremote.parallelism: "5"
```

### Redis 优化

```yaml
# For high-traffic deployments, use Redis HA
redis-ha:
  enabled: true
  redis:
    config:
      maxmemory: "512mb"
      maxmemory-policy: "allkeys-lru"
  haproxy:
    enabled: true
    replicas: 3
```

### Application 级优化

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: large-app
  namespace: argocd
spec:
  # Reduce sync frequency for stable apps
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - ApplyOutOfSyncOnly=true  # Only apply changed resources

  # Ignore frequently changing fields
  ignoreDifferences:
    - group: apps
      kind: Deployment
      jsonPointers:
        - /spec/replicas
    - group: "*"
      kind: "*"
      managedFieldsManagers:
        - kube-controller-manager
```

## 灾难恢复

### 备份策略

```bash
#!/bin/bash
# backup-argocd.sh

BACKUP_DIR="/backups/argocd/$(date +%Y%m%d)"
mkdir -p $BACKUP_DIR

# Backup Applications
kubectl get applications -n argocd -o yaml > $BACKUP_DIR/applications.yaml

# Backup AppProjects
kubectl get appprojects -n argocd -o yaml > $BACKUP_DIR/appprojects.yaml

# Backup Repositories
kubectl get secrets -n argocd -l argocd.argoproj.io/secret-type=repository -o yaml > $BACKUP_DIR/repositories.yaml

# Backup Repo Credentials
kubectl get secrets -n argocd -l argocd.argoproj.io/secret-type=repo-creds -o yaml > $BACKUP_DIR/repo-creds.yaml

# Backup Clusters
kubectl get secrets -n argocd -l argocd.argoproj.io/secret-type=cluster -o yaml > $BACKUP_DIR/clusters.yaml

# Backup ConfigMaps
kubectl get configmaps -n argocd -o yaml > $BACKUP_DIR/configmaps.yaml

# Backup RBAC
kubectl get configmap argocd-rbac-cm -n argocd -o yaml > $BACKUP_DIR/rbac.yaml

echo "Backup completed: $BACKUP_DIR"
```

### 恢复过程

```bash
#!/bin/bash
# restore-argocd.sh

BACKUP_DIR=$1

if [ -z "$BACKUP_DIR" ]; then
  echo "Usage: restore-argocd.sh <backup-dir>"
  exit 1
fi

# Ensure ArgoCD is installed
kubectl get namespace argocd || kubectl create namespace argocd

# Restore in order
kubectl apply -f $BACKUP_DIR/configmaps.yaml
kubectl apply -f $BACKUP_DIR/rbac.yaml
kubectl apply -f $BACKUP_DIR/repo-creds.yaml
kubectl apply -f $BACKUP_DIR/repositories.yaml
kubectl apply -f $BACKUP_DIR/clusters.yaml
kubectl apply -f $BACKUP_DIR/appprojects.yaml
kubectl apply -f $BACKUP_DIR/applications.yaml

# Restart ArgoCD components
kubectl rollout restart deployment -n argocd

echo "Restore completed"
```

### 多区域 DR

```yaml
# Primary region ArgoCD manages secondary
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: argocd-dr
  namespace: argocd
spec:
  project: platform
  source:
    repoURL: https://github.com/myorg/gitops-platform.git
    targetRevision: HEAD
    path: argocd
  destination:
    server: https://dr-region.k8s.local  # DR cluster
    namespace: argocd
  syncPolicy:
    automated:
      prune: false  # Don't auto-prune in DR
      selfHeal: true
```

## 升级策略

### 升级前检查清单

1. **查看发布说明**，了解破坏性变更
2. **备份当前状态**（applications、projects、secrets）
3. 首先在**非生产环境**中测试
4. 如有需要，**安排维护窗口**
5. **通知利益相关者**

### 滚动升级

```bash
# 1. Update ArgoCD manifests
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/v2.13.0/manifests/install.yaml

# 2. Wait for rollout
kubectl rollout status deployment argocd-server -n argocd
kubectl rollout status deployment argocd-repo-server -n argocd
kubectl rollout status deployment argocd-application-controller -n argocd

# 3. Verify
argocd version
argocd app list
```

### 蓝绿升级

```bash
# 1. Install new version in separate namespace
kubectl create namespace argocd-new
kubectl apply -n argocd-new -f https://raw.githubusercontent.com/argoproj/argo-cd/v2.13.0/manifests/install.yaml

# 2. Migrate configuration
kubectl get configmap argocd-cm -n argocd -o yaml | sed 's/namespace: argocd/namespace: argocd-new/' | kubectl apply -f -
kubectl get configmap argocd-rbac-cm -n argocd -o yaml | sed 's/namespace: argocd/namespace: argocd-new/' | kubectl apply -f -

# 3. Test new installation
kubectl port-forward svc/argocd-server -n argocd-new 8081:443

# 4. Switch traffic (update ingress/load balancer)
# 5. Decommission old installation
kubectl delete namespace argocd
kubectl rename namespace argocd-new argocd
```

## 故障排除

### 常见问题及解决方案

#### Sync 失败

```bash
# Check application events
kubectl describe application my-app -n argocd

# Check application controller logs
kubectl logs -n argocd -l app.kubernetes.io/name=argocd-application-controller --tail=100

# Force refresh
argocd app get my-app --refresh

# Hard refresh (clear cache)
argocd app get my-app --hard-refresh
```

#### 仓库连接问题

```bash
# Test repository connectivity
argocd repo list
argocd repo get https://github.com/myorg/myrepo.git

# Check repo server logs
kubectl logs -n argocd -l app.kubernetes.io/name=argocd-repo-server --tail=100

# Verify credentials
kubectl get secret -n argocd -l argocd.argoproj.io/secret-type=repository
```

#### 内存不足（OOM）

```bash
# Check current memory usage
kubectl top pods -n argocd

# Increase limits
kubectl patch deployment argocd-repo-server -n argocd -p '
{
  "spec": {
    "template": {
      "spec": {
        "containers": [{
          "name": "argocd-repo-server",
          "resources": {
            "limits": {"memory": "4Gi"},
            "requests": {"memory": "2Gi"}
          }
        }]
      }
    }
  }
}'
```

#### Sync 缓慢

```bash
# Check sync duration
argocd app get my-app -o json | jq '.status.operationState.finishedAt, .status.operationState.startedAt'

# Enable debug logging
kubectl patch configmap argocd-cmd-params-cm -n argocd -p '{"data":{"controller.log.level":"debug"}}'

# Check for large manifests
argocd app manifests my-app | wc -l
```

### 调试命令速查表

```bash
# Application status
argocd app get <app-name>
argocd app get <app-name> -o json | jq '.status'

# Diff between desired and live
argocd app diff <app-name>

# View manifests
argocd app manifests <app-name>

# Sync with debug
argocd app sync <app-name> --debug

# View all applications
argocd app list -o wide

# Check cluster connectivity
argocd cluster list
argocd cluster get <cluster-url>

# View logs
kubectl logs -n argocd deployment/argocd-server --tail=100
kubectl logs -n argocd deployment/argocd-repo-server --tail=100
kubectl logs -n argocd deployment/argocd-application-controller --tail=100

# Clear application cache
argocd app get <app-name> --hard-refresh

# Force reconciliation
kubectl patch application <app-name> -n argocd -p '{"metadata":{"annotations":{"argocd.argoproj.io/refresh":"hard"}}}' --type merge
```

## EKS 最佳实践

### IRSA 配置

```yaml
# Service account with IRSA
apiVersion: v1
kind: ServiceAccount
metadata:
  name: argocd-application-controller
  namespace: argocd
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/ArgoCD-Controller
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: argocd-repo-server
  namespace: argocd
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/ArgoCD-RepoServer
```

### 使用 WAF 的 ALB Ingress

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
    alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:us-west-2:123456789012:certificate/xxx
    alb.ingress.kubernetes.io/wafv2-acl-arn: arn:aws:wafv2:us-west-2:123456789012:regional/webacl/argocd/xxx
    alb.ingress.kubernetes.io/shield-advanced-protection: "true"
    alb.ingress.kubernetes.io/ssl-policy: ELBSecurityPolicy-TLS-1-2-2017-01
spec:
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

### EKS 集群升级

升级由 ArgoCD 管理的 EKS 集群时：

1. 如果发生变更，使用新的 API endpoint 更新 **ArgoCD cluster secret**
2. 升级后测试连接性
3. 重新 Sync applications 以验证兼容性
4. 如果 Application manifests 中硬编码了 Kubernetes version，请进行更新

## 生产环境检查清单

### 安全性

- [ ] 已配置并测试 SSO
- [ ] 已实施 RBAC 策略
- [ ] 已为所有 endpoints 启用 TLS
- [ ] Secrets 存储在外部（不在 Git 中）
- [ ] 已应用网络策略
- [ ] 已启用审计日志记录
- [ ] 已保护仓库凭证
- [ ] 已将管理员密码从默认值更改

### 高可用性

- [ ] 所有组件均有多个副本
- [ ] 已启用 Redis HA
- [ ] 已配置 Controller 分片（如果应用程序数量 > 100）
- [ ] 已适当设置资源限制
- [ ] 已为 repo-server 配置 HPA
- [ ] 已配置 PodDisruptionBudgets

### 监控

- [ ] 已启用 Prometheus metrics
- [ ] 已配置 ServiceMonitor
- [ ] 已创建仪表板（Grafana）
- [ ] 已为以下情况配置告警：
  - [ ] Sync 失败
  - [ ] 健康状态恶化
  - [ ] 内存使用量高
  - [ ] API server 错误

### 备份与 DR

- [ ] 已配置备份脚本
- [ ] 已设置备份计划（至少每日一次）
- [ ] 已记录并测试恢复过程
- [ ] 已配置 DR 站点（如需要）

### 运维

- [ ] 已配置通知服务
- [ ] 已为生产环境定义 Sync 窗口
- [ ] 已按团队/环境配置 Projects
- [ ] 已记录仓库结构
- [ ] 已记录升级过程
- [ ] 已为常见问题创建运行手册

## 测验

要测试所学内容，请尝试 [ArgoCD 最佳实践测验](../../quizzes/gitops/argocd/09-best-practices-quiz.md)。
