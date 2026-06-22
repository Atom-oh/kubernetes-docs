# Backstage IDP Quiz

1. Which Entity Kind is used to register a microservice in the Backstage Software Catalog?
   - A) Service
   - B) Component
   - C) Application
   - D) Workload

<details>
<summary>Show Answer</summary>

**Answer: B) Component**

**Explanation:**
In the Backstage Software Catalog, microservices, websites, and libraries are all registered as `Component` Kind. The `spec.type` field distinguishes between service, website, library, etc.

</details>

---

2. What is the primary purpose of Backstage Software Templates (Golden Paths)?
   - A) Monitor existing service performance
   - B) Automatically create new services/infrastructure in a standardized way
   - C) Audit Kubernetes cluster security
   - D) Monitor CI/CD pipelines

<details>
<summary>Show Answer</summary>

**Answer: B) Automatically create new services/infrastructure in a standardized way**

**Explanation:**
Software Templates (Golden Paths) allow developers to enter a few parameters in the Backstage UI and automatically scaffold a standardized project structure (Dockerfile, Helm chart, CI/CD, catalog-info.yaml, etc.), naturally applying organizational best practices.

</details>

---

3. Which annotation is required in catalog-info.yaml to display Kubernetes Pod status in Backstage?
   - A) kubernetes.io/pod-name
   - B) backstage.io/kubernetes-id
   - C) app.kubernetes.io/managed-by
   - D) backstage.io/k8s-cluster

<details>
<summary>Show Answer</summary>

**Answer: B) backstage.io/kubernetes-id**

**Explanation:**
The `backstage.io/kubernetes-id` annotation is used by the Backstage Kubernetes plugin to match catalog entities with Kubernetes resources. This value must match the `backstage.io/kubernetes-id` label on the Kubernetes Deployment.

</details>

---

4. What is the most appropriate PostgreSQL setup for Backstage in an EKS production environment?
   - A) Built-in SQLite
   - B) In-cluster PostgreSQL StatefulSet
   - C) Amazon RDS PostgreSQL (external managed)
   - D) DynamoDB

<details>
<summary>Show Answer</summary>

**Answer: C) Amazon RDS PostgreSQL (external managed)**

**Explanation:**
Production environments should use managed databases like Amazon RDS for automatic backups, high availability (Multi-AZ), and monitoring. Set `postgresql.enabled: false` in Helm values and provide external RDS connection details via Secrets.

</details>

---

5. Which documentation build tool does Backstage TechDocs use?
   - A) Docusaurus
   - B) GitBook
   - C) MkDocs
   - D) Sphinx

<details>
<summary>Show Answer</summary>

**Answer: C) MkDocs**

**Explanation:**
Backstage TechDocs is built on MkDocs. It generates documentation from a service repo's `docs/` directory and `mkdocs.yml` file, publishes to storage like S3, and makes it accessible directly from the catalog.

</details>

---

6. When adopting Backstage incrementally, which feature should you start with?
   - A) Software Templates
   - B) Software Catalog
   - C) TechDocs
   - D) RBAC Permission Framework

<details>
<summary>Show Answer</summary>

**Answer: B) Software Catalog**

**Explanation:**
The Software Catalog is the foundation of Backstage and all other features build upon it. Start by registering your organization's services, APIs, and team information, then incrementally add Templates and TechDocs.

</details>

---

7. How can a Backstage Software Template automate both GitHub repo creation and ArgoCD Application creation?
   - A) Backstage calls the Kubernetes API directly
   - B) Template steps sequentially execute publish:github and argocd:create-resources actions
   - C) GitHub Webhooks automatically trigger ArgoCD
   - D) The Helm chart includes all resources

<details>
<summary>Show Answer</summary>

**Answer: B) Template steps sequentially execute publish:github and argocd:create-resources actions**

**Explanation:**
The Backstage Scaffolder executes actions defined in the Template's `steps` section sequentially. `publish:github` creates the repo, and its output (remoteUrl) is passed as input to `argocd:create-resources` to automatically create the ArgoCD Application. Finally, `catalog:register` adds it to the catalog.

</details>

---

8. How do you restrict teams to only modify their own entities in the Backstage Permission Framework?
   - A) Kubernetes RBAC ClusterRole
   - B) Use conditions field in policy to match spec.owner
   - C) GitHub repository permissions
   - D) Ingress network policies

<details>
<summary>Show Answer</summary>

**Answer: B) Use conditions field in policy to match spec.owner**

**Explanation:**
The Backstage Permission Framework policy's `conditions` field can match entities where `spec.owner` equals the team name, granting update permissions only for their own entities. This maintains team autonomy while restricting modification of other teams' entities to read-only.

</details>
