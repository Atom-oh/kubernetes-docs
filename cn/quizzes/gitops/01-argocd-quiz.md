# ArgoCD 测验

本测验用于检验你对 ArgoCD 和 GitOps 的理解。

## 问题 1：GitOps 核心原则

<details>
<summary>GitOps 的 4 项核心原则是什么？</summary>

**答案：**
1. **声明式配置**：将系统的期望状态定义为代码
2. **版本化且不可变**：保留不可变的期望状态版本和完整历史记录
3. **自动拉取**：由代理自动从来源获取期望状态声明
4. **持续协调**：观察实际状态，并持续尝试使其符合期望状态

这些原则使 GitOps 成为一套完整的运维模型，而不只是部署工具。
</details>

## 问题 2：ArgoCD 架构

<details>
<summary>ArgoCD 的主要组件及其作用是什么？</summary>

**答案：**
- **API Server**：提供 REST API 和 Web UI，并处理身份验证与授权
- **Repository Server**：连接 Git 仓库并生成 manifest
- **Application Controller**：监控应用程序状态并执行同步
- **Redis**：可重建的缓存
- **Dex**：OIDC 身份验证服务器（可选）

各组件的扩展方式不同：Application Controller 使用分片，ApplicationSet 使用领导者选举；内置 Dex 使用内存存储，不能只通过增加副本数来安全地实现高可用。
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
- 仍需设计审查与批准控制，以及相应的运维开销
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
  name: demo-cluster-apps
  namespace: argocd
spec:
  goTemplate: true
  goTemplateOptions: ["missingkey=error"]
  generators:
  - clusters:
      selector:
        matchLabels:
          environment: demo
  template:
    metadata:
      name: '{{.nameNormalized}}-guestbook'
    spec:
      project: default
      source:
        repoURL: https://github.com/argoproj/argocd-example-apps.git
        targetRevision: HEAD
        path: guestbook
      destination:
        server: '{{.server}}'
        namespace: guestbook
      syncPolicy:
        syncOptions: [CreateNamespace=true]
```
</details>

## 问题 6：安全最佳实践

<details>
<summary>增强 ArgoCD 安全性的关键方法有哪些？</summary>

**答案：**
1. **RBAC 配置**：
   ```yaml
   policy.default: role:authenticated
   policy.csv: |
     p, role:dev, applications, get, dev/*, allow
     p, role:dev, projects, get, dev, allow
     g, dev-team, role:dev
   ```

2. **SSO 集成**：
   - 直接使用 OIDC，或通过受支持的 Dex connector 对接其他身份提供商
   - 集中管理身份验证

3. **网络安全**：
   - Ingress TLS 配置
   - 执行网络策略
   - 使用私有 Git 仓库

4. **Secret 管理**：
   - 使用 External Secrets Operator
   - Sealed Secrets 或 Helm Secrets
   - 不要将明文密钥保存在 Git 中；应使用外部密钥存储，或采用适当的加密和密钥管理方式

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
   argocd repo get "$REPO_URL"
   ```

2. **验证 Manifest：**
   ```bash
   # Validate manifests locally
   kubectl --context "$TARGET_CONTEXT" apply --server-side --dry-run=server -f manifests/
   ```

3. **检查同步策略：**
   - 自动同步设置
   - Prune 和 SelfHeal 选项
   - 同步条件（Sync Windows）

4. **分析资源状态：**
   ```bash
   # Check application details
   argocd app get "$APP_NAME"
   argocd app diff "$APP_NAME"
   ```

5. **检查日志：**
   ```bash
   # ArgoCD controller logs
   kubectl logs -n argocd -l app.kubernetes.io/name=argocd-application-controller
   ```

6. **尝试手动同步：**
   ```bash
   argocd app sync "$APP_NAME" --dry-run
   ```
</details>

## 问题 9：GitOps 运维模式

<details>
<summary>本指南涵盖了哪些 GitOps 运维模式？</summary>

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
   controller:
     serviceAccount:
       annotations:
         eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/ArgoCD-Management
   ```

2. **ALB Ingress 配置：**
   ```yaml
   metadata:
     annotations:
       alb.ingress.kubernetes.io/scheme: internal
       alb.ingress.kubernetes.io/target-type: ip
   spec:
     ingressClassName: alb
   ```

3. **EKS 集群注册：**
   ```bash
   # Register EKS cluster to ArgoCD
   argocd cluster add "$TARGET_CONTEXT"
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
- 答对 8–10 题：已掌握本测验的核心概念
- 答对 6–7 题：良好（建议继续学习）
- 答对 4–5 题：一般（需要复习基础知识）
- 答对 0–3 题：请复习基础知识并完成练习

将 `REPO_URL`、`APP_NAME` 和 `TARGET_CONTEXT` 设置为实际值。`TARGET_CONTEXT` 是 kubeconfig context；EKS 的默认 context 本身也可能是 ARN。检查 cluster-add 带来的 RBAC 变更，以及自动同步与手动同步的差异。dry-run 会预览变更；`--prune` 会包含删除操作，需要单独审核。IRSA 注解本身不会配置信任关系或 EKS access entry；ALB 还需要证书、TLS 和网络访问配置。ApplicationSet 示例中的 `demo` 环境要与已注册集群 Secret 的标签相匹配。保留 `role:authenticated` 作为默认角色，不授予全局只读权限，并仅向 `dev-team` 分配其必需的最小权限范围。
