# ArgoCD 测验

本测验用于测试你对 ArgoCD 和 GitOps 的理解。

## 问题 1：GitOps 核心原则

<details>
<summary>GitOps 的 4 项核心原则是什么？</summary>

**答案：**
1. **声明式配置**：将系统的期望状态定义为代码
2. **版本控制**：在 Git 中跟踪所有变更
3. **自动同步**：自动协调仓库与运行环境之间的差异
4. **自愈**：自动将系统恢复到期望状态

这些原则使 GitOps 能够作为一套完整的运维模型运行，而不仅仅是一个部署工具。
</details>

## 问题 2：ArgoCD 架构

<details>
<summary>ArgoCD 的主要组件及其作用是什么？</summary>

**答案：**
- **API Server**：提供 REST API 和 Web UI，并处理身份验证与授权
- **Repository Server**：连接 Git 仓库并生成 manifest
- **Application Controller**：监控应用程序状态并执行同步
- **Redis**：缓存和会话存储
- **Dex**：OIDC 身份验证服务器（可选）

每个组件都可以独立扩展，并支持高可用配置。
</details>

## 问题 3：Application 资源

<details>
<summary>ArgoCD Application 资源的必需组件是什么？</summary>

**答案：**
```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: my-app
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/example/app-config
    targetRevision: HEAD
    path: k8s
  destination:
    server: https://kubernetes.default.svc
    namespace: default
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
```

**必需元素：**
- `source`：Git 仓库信息
- `destination`：用于部署的目标集群和 namespace
- `project`：ArgoCD project（用于权限管理）
</details>

## 问题 4：同步策略

<details>
<summary>ArgoCD 中的自动同步和手动同步有什么区别？</summary>

**答案：**
**自动同步：**
```yaml
syncPolicy:
  automated:
    prune: true      # Automatically delete unnecessary resources
    selfHeal: true   # Automatically recover from drift
```
- Git 发生变更时自动应用到集群
- 检测到漂移时自动恢复
- 在生产环境中应谨慎使用

**手动同步：**
- 用户显式触发同步
- 审核变更后再应用
- 更安全，但会增加运维开销
</details>

## 问题 5：ApplicationSet

<details>
<summary>ArgoCD ApplicationSet 的用途是什么？主要的 generator 类型有哪些？</summary>

**答案：**
**用途：**
- 自动化多集群部署
- 基于模板创建 Application
- 针对特定环境的配置管理

**主要 Generators：**
- **List Generator**：基于静态值列表
- **Cluster Generator**：基于已注册的集群
- **Git Generator**：基于 Git 仓库结构
- **Matrix Generator**：组合多个 generator
- **Pull Request Generator**：基于 PR 的临时环境

```yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: cluster-apps
spec:
  generators:
  - clusters: {}
  template:
    metadata:
      name: '{{name}}-app'
    spec:
      source:
        repoURL: https://github.com/example/apps
        path: '{{name}}'
      destination:
        server: '{{server}}'
```
</details>

## 问题 6：安全最佳实践

<details>
<summary>增强 ArgoCD 安全性的关键方法有哪些？</summary>

**答案：**
1. **RBAC 配置**：
   ```yaml
   policy.default: role:readonly
   policy.csv: |
     p, role:admin, applications, *, */*, allow
     p, role:dev, applications, get, dev/*, allow
     g, dev-team, role:dev
   ```

2. **SSO 集成**：
   - OIDC、SAML、LDAP 集成
   - 集中式身份验证管理

3. **网络安全**：
   - Ingress TLS 配置
   - 执行网络策略
   - 使用私有 Git 仓库

4. **Secret 管理**：
   - 使用 External Secrets Operator
   - Sealed Secrets 或 Helm Secrets
   - 为敏感信息使用独立的 Git 仓库

5. **审计日志**：
   - 跟踪所有变更
   - 监控访问日志
</details>

## 问题 7：多集群管理

<details>
<summary>如何在 ArgoCD 中管理多个集群？</summary>

**答案：**
1. **集群注册：**
   ```bash
   argocd cluster add my-cluster-context
   ```

2. **按集群部署 Application：**
   ```yaml
   destination:
     server: https://my-cluster-api-server
     namespace: production
   ```

3. **通过 ApplicationSet 实现自动化：**
   ```yaml
   generators:
   - clusters:
       selector:
         matchLabels:
           environment: production
   ```

4. **集群权限管理：**
   - 为每个集群配置 service account
   - 应用最小权限原则
   - 基于 namespace 的隔离

5. **监控和告警：**
   - 按集群划分的状态仪表板
   - 同步失败告警
   - 资源使用情况监控
</details>

## 问题 8：故障排查

<details>
<summary>当 ArgoCD Application 处于“OutOfSync”状态时，应检查哪些内容？</summary>

**答案：**
1. **检查 Git 仓库状态：**
   ```bash
   # Check repository access permissions
   argocd repo list
   argocd repo get <repo-url>
   ```

2. **验证 Manifest：**
   ```bash
   # Validate manifests locally
   kubectl apply --dry-run=client -f manifests/
   ```

3. **检查同步策略：**
   - 自动同步设置
   - Prune 和 SelfHeal 选项
   - 同步条件（Sync Windows）

4. **分析资源状态：**
   ```bash
   # Check application details
   argocd app get <app-name>
   argocd app diff <app-name>
   ```

5. **检查日志：**
   ```bash
   # ArgoCD controller logs
   kubectl logs -n argocd -l app.kubernetes.io/name=argocd-application-controller
   ```

6. **尝试手动同步：**
   ```bash
   argocd app sync <app-name> --prune
   ```
</details>

## 问题 9：最新 GitOps 趋势

<details>
<summary>2023 年 GitOps 领域的主要趋势是什么？</summary>

**答案：**
1. **多集群 GitOps：**
   - 通过 ApplicationSet 自动化多集群部署
   - 跨集群配置同步和策略执行

2. **混合云和多云 GitOps：**
   - 跨本地环境和云环境的一致部署策略
   - 跨不同云提供商的 workload 可移植性

3. **GitOps 与策略管理集成：**
   - OPA（Open Policy Agent）和 Kyverno 集成
   - 合规性和治理自动化
   - 安全策略的代码化和版本控制

4. **渐进式交付：**
   - Canary 和 Blue-Green 部署自动化
   - 与 Argo Rollouts 集成
   - 基于指标的自动回滚
</details>

## 问题 10：Amazon EKS 集成

<details>
<summary>将 ArgoCD 与 Amazon EKS 集成时需要考虑哪些事项？</summary>

**答案：**
1. **IAM 权限设置：**
   ```yaml
   # IRSA (IAM Roles for Service Accounts) configuration
   serviceAccount:
     annotations:
       eks.amazonaws.com/role-arn: arn:aws:iam::ACCOUNT:role/argocd-role
   ```

2. **ALB Ingress 配置：**
   ```yaml
   annotations:
     kubernetes.io/ingress.class: alb
     alb.ingress.kubernetes.io/scheme: internet-facing
     alb.ingress.kubernetes.io/target-type: ip
   ```

3. **EKS 集群注册：**
   ```bash
   # Register EKS cluster to ArgoCD
   argocd cluster add arn:aws:eks:region:account:cluster/cluster-name
   ```

4. **ECR 集成：**
   - 自动更新 ECR 镜像
   - Image Updater 配置

5. **AWS Load Balancer Controller：**
   - Service 负载均衡优化
   - 使用 Target Group Binding

6. **安全注意事项：**
   - 使用 VPC endpoint
   - Security group 配置
   - 执行网络策略
</details>

---

**评分：**
- 8-10 题正确：优秀（ArgoCD 专家级）
- 6-7 题正确：良好（建议进一步学习）
- 4-5 题正确：一般（需要复习基本概念）
- 0-3 题正确：不足（需要重新学习全部内容）
