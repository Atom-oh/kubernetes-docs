# ArgoCD Quiz

This quiz tests your understanding of ArgoCD and GitOps.

## Question 1: GitOps Core Principles

<details>
<summary>What are the 4 core principles of GitOps?</summary>

**Answer:**
1. **Declarative Configuration**: Define the desired state of the system as code
2. **Versioned and Immutable**: Retain immutable desired-state versions and complete history
3. **Pulled Automatically**: Agents automatically retrieve desired-state declarations from the source
4. **Continuously Reconciled**: Observe actual state and continuously attempt to apply desired state

These principles enable GitOps to operate as a complete operational model beyond just a deployment tool.
</details>

## Question 2: ArgoCD Architecture

<details>
<summary>What are the main components of ArgoCD and their roles?</summary>

**Answer:**
- **API Server**: Provides REST API and web UI, handles authentication and authorization
- **Repository Server**: Connects to Git repositories and generates manifests
- **Application Controller**: Monitors application state and performs synchronization
- **Redis**: Rebuildable cache
- **Dex**: OIDC authentication server (optional)

Scaling differs by component: Application Controller uses shards, ApplicationSet uses leader election, and bundled Dex cannot safely gain HA merely by adding replicas to its in-memory storage.
</details>

## Question 3: Application Resource

<details>
<summary>What are the required components of an ArgoCD Application resource?</summary>

**Answer:**
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

**Required elements:**
- `source`: Git repository information
- `destination`: Target cluster and namespace for deployment
- `project`: ArgoCD project (for permission management)
</details>

## Question 4: Sync Policies

<details>
<summary>What are the differences between automated sync and manual sync in ArgoCD?</summary>

**Answer:**
**Automated Sync:**
```yaml
syncPolicy:
  automated:
    prune: true      # Automatically delete unnecessary resources
    selfHeal: true   # Automatically recover from drift
```
- Automatically applies to cluster when Git changes
- Automatically recovers when drift is detected
- Use cautiously in production environments

**Manual Sync:**
- User explicitly triggers synchronization
- Apply after reviewing changes
- Review/approval controls and operational overhead still need design
</details>

## Question 5: ApplicationSet

<details>
<summary>What is the purpose of ArgoCD ApplicationSet and what are the main generator types?</summary>

**Answer:**
**Purpose:**
- Automate multi-cluster deployments
- Template-based Application creation
- Environment-specific configuration management

**Main Generators:**
- **List Generator**: Based on static value lists
- **Cluster Generator**: Based on registered clusters
- **Git Generator**: Based on Git repository structure
- **Matrix Generator**: Combines multiple generators
- **Pull Request Generator**: PR-based temporary environments

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

## Question 6: Security Best Practices

<details>
<summary>What are the key methods to strengthen ArgoCD security?</summary>

**Answer:**
1. **RBAC Configuration**:
   ```yaml
   policy.default: role:authenticated
   policy.csv: |
     p, role:dev, applications, get, dev/*, allow
     p, role:dev, projects, get, dev, allow
     g, dev-team, role:dev
   ```

2. **SSO Integration**:
   - Direct OIDC or supported Dex connectors for other identity providers
   - Centralized authentication management

3. **Network Security**:
   - Ingress TLS configuration
   - Network policy enforcement
   - Use private Git repositories

4. **Secret Management**:
   - Use External Secrets Operator
   - Sealed Secrets or Helm Secrets
   - Keep plaintext secrets out of Git; use an external secret store or appropriate encryption/key management

5. **Audit Logging**:
   - Track all changes
   - Monitor access logs
</details>

## Question 7: Multi-Cluster Management

<details>
<summary>How do you manage multiple clusters in ArgoCD?</summary>

**Answer:**
1. **Cluster Registration**:
   ```bash
   argocd cluster add my-cluster-context
   ```

2. **Per-Cluster Application Deployment**:
   ```yaml
   destination:
     server: https://my-cluster-api-server
     namespace: production
   ```

3. **Automation via ApplicationSet**:
   ```yaml
   generators:
   - clusters:
       selector:
         matchLabels:
           environment: production
   ```

4. **Cluster Permission Management**:
   - Configure service accounts per cluster
   - Apply least privilege principle
   - Namespace-based isolation

5. **Monitoring and Alerts**:
   - Per-cluster status dashboards
   - Sync failure alerts
   - Resource usage monitoring
</details>

## Question 8: Troubleshooting

<details>
<summary>What should you check when an ArgoCD application is in "OutOfSync" state?</summary>

**Answer:**
1. **Check Git Repository Status**:
   ```bash
   # Check repository access permissions
   argocd repo list
   argocd repo get "$REPO_URL"
   ```

2. **Validate Manifests**:
   ```bash
   # Validate manifests locally
   kubectl --context "$TARGET_CONTEXT" apply --server-side --dry-run=server -f manifests/
   ```

3. **Check Sync Policies**:
   - Auto sync settings
   - Prune and SelfHeal options
   - Sync conditions (Sync Windows)

4. **Analyze Resource Status**:
   ```bash
   # Check application details
   argocd app get "$APP_NAME"
   argocd app diff "$APP_NAME"
   ```

5. **Check Logs**:
   ```bash
   # ArgoCD controller logs
   kubectl logs -n argocd -l app.kubernetes.io/name=argocd-application-controller
   ```

6. **Try Manual Sync**:
   ```bash
   argocd app sync "$APP_NAME" --dry-run
   ```
</details>

## Question 9: GitOps Operating Patterns

<details>
<summary>Which GitOps operating patterns does this guide cover?</summary>

**Answer:**
1. **Multi-Cluster GitOps**:
   - Automated multi-cluster deployments via ApplicationSets
   - Cross-cluster configuration sync and policy enforcement

2. **Hybrid and Multi-Cloud GitOps**:
   - Consistent deployment strategies across on-premises and cloud environments
   - Workload portability across various cloud providers

3. **GitOps and Policy Management Integration**:
   - OPA (Open Policy Agent) and Kyverno integration
   - Compliance and governance automation
   - Security policy codification and version control

4. **Progressive Delivery**:
   - Canary and Blue-Green deployment automation
   - Integration with Argo Rollouts
   - Metrics-based automatic rollback
</details>

## Question 10: Amazon EKS Integration

<details>
<summary>What are the considerations when integrating ArgoCD with Amazon EKS?</summary>

**Answer:**
1. **IAM Permission Setup**:
   ```yaml
   # IRSA (IAM Roles for Service Accounts) configuration
   controller:
     serviceAccount:
       annotations:
         eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/ArgoCD-Management
   ```

2. **ALB Ingress Configuration**:
   ```yaml
   metadata:
     annotations:
       alb.ingress.kubernetes.io/scheme: internal
       alb.ingress.kubernetes.io/target-type: ip
   spec:
     ingressClassName: alb
   ```

3. **EKS Cluster Registration**:
   ```bash
   # Register EKS cluster to ArgoCD
   argocd cluster add "$TARGET_CONTEXT"
   ```

4. **ECR Integration**:
   - Automatic ECR image updates
   - Image Updater configuration

5. **AWS Load Balancer Controller**:
   - Service load balancing optimization
   - Target Group Binding utilization

6. **Security Considerations**:
   - Use VPC endpoints
   - Security group configuration
   - Network policy enforcement
</details>

---

**Scoring:**
- 8-10 correct: Core concepts in this quiz understood
- 6-7 correct: Good (additional learning recommended)
- 4-5 correct: Average (basic concepts review needed)
- 0-3 correct: Review fundamentals and practice the labs


Set REPO_URL, APP_NAME and TARGET_CONTEXT to real values. TARGET_CONTEXT is a kubeconfig context; an EKS default context may itself be an ARN. Review cluster-add RBAC changes and sync/prune differences. The dry run previews changes; --prune includes deletion and requires separate review. IRSA annotations do not configure trust/EKS access entries, and ALB needs certificates/TLS/network access. ApplicationSet environment: demo matches registered cluster Secret labels. Keep role:authenticated without global readonly grants and assign dev-team only its required scope.
