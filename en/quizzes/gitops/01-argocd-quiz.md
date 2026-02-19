# ArgoCD Quiz

This quiz tests your understanding of ArgoCD and GitOps.

## Question 1: GitOps Core Principles

<details>
<summary>What are the 4 core principles of GitOps?</summary>

**Answer:**
1. **Declarative Configuration**: Define the desired state of the system as code
2. **Version Control**: Track all changes in Git
3. **Automated Synchronization**: Automatically reconcile differences between the repository and the running environment
4. **Self-Healing**: Automatically recover the system to the desired state

These principles enable GitOps to operate as a complete operational model beyond just a deployment tool.
</details>

## Question 2: ArgoCD Architecture

<details>
<summary>What are the main components of ArgoCD and their roles?</summary>

**Answer:**
- **API Server**: Provides REST API and web UI, handles authentication and authorization
- **Repository Server**: Connects to Git repositories and generates manifests
- **Application Controller**: Monitors application state and performs synchronization
- **Redis**: Caching and session storage
- **Dex**: OIDC authentication server (optional)

Each component can be scaled independently and supports high availability configurations.
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
- Safer but increases operational overhead
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

## Question 6: Security Best Practices

<details>
<summary>What are the key methods to strengthen ArgoCD security?</summary>

**Answer:**
1. **RBAC Configuration**:
   ```yaml
   policy.default: role:readonly
   policy.csv: |
     p, role:admin, applications, *, */*, allow
     p, role:dev, applications, get, dev/*, allow
     g, dev-team, role:dev
   ```

2. **SSO Integration**:
   - OIDC, SAML, LDAP integration
   - Centralized authentication management

3. **Network Security**:
   - Ingress TLS configuration
   - Network policy enforcement
   - Use private Git repositories

4. **Secret Management**:
   - Use External Secrets Operator
   - Sealed Secrets or Helm Secrets
   - Separate Git repositories for sensitive information

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
   argocd repo get <repo-url>
   ```

2. **Validate Manifests**:
   ```bash
   # Validate manifests locally
   kubectl apply --dry-run=client -f manifests/
   ```

3. **Check Sync Policies**:
   - Auto sync settings
   - Prune and SelfHeal options
   - Sync conditions (Sync Windows)

4. **Analyze Resource Status**:
   ```bash
   # Check application details
   argocd app get <app-name>
   argocd app diff <app-name>
   ```

5. **Check Logs**:
   ```bash
   # ArgoCD controller logs
   kubectl logs -n argocd -l app.kubernetes.io/name=argocd-application-controller
   ```

6. **Try Manual Sync**:
   ```bash
   argocd app sync <app-name> --prune
   ```
</details>

## Question 9: Latest GitOps Trends

<details>
<summary>What are the major trends in the GitOps space in 2023?</summary>

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
   serviceAccount:
     annotations:
       eks.amazonaws.com/role-arn: arn:aws:iam::ACCOUNT:role/argocd-role
   ```

2. **ALB Ingress Configuration**:
   ```yaml
   annotations:
     kubernetes.io/ingress.class: alb
     alb.ingress.kubernetes.io/scheme: internet-facing
     alb.ingress.kubernetes.io/target-type: ip
   ```

3. **EKS Cluster Registration**:
   ```bash
   # Register EKS cluster to ArgoCD
   argocd cluster add arn:aws:eks:region:account:cluster/cluster-name
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
- 8-10 correct: Excellent (ArgoCD expert level)
- 6-7 correct: Good (additional learning recommended)
- 4-5 correct: Average (basic concepts review needed)
- 0-3 correct: Insufficient (full content re-study needed)
