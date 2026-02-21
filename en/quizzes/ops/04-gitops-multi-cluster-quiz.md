# GitOps Multi-Cluster Quiz

> **Related Document**: [GitOps Multi-Cluster](../../ops/04-gitops-multi-cluster.md)

## Multiple Choice Questions

### 1. What is the hub-spoke model in multi-cluster GitOps?

- A) A network topology pattern
- B) A central management cluster controlling multiple workload clusters
- C) A data replication strategy
- D) A load balancing algorithm

<details>
<summary>Show Answer</summary>

**Answer: B) A central management cluster controlling multiple workload clusters**

**Explanation:**
In the hub-spoke model, a central "hub" cluster runs ArgoCD and manages deployments to multiple "spoke" workload clusters. This centralizes GitOps operations while keeping workloads isolated across clusters.

</details>

### 2. How does ArgoCD achieve High Availability (HA)?

- A) By running a single replica with auto-restart
- B) By running multiple replicas of each component with leader election
- C) By using external database replication
- D) By deploying across multiple regions

<details>
<summary>Show Answer</summary>

**Answer: B) By running multiple replicas of each component with leader election**

**Explanation:**
ArgoCD HA deploys multiple replicas of the application-controller, repo-server, and server components. The application-controller uses leader election to ensure only one instance processes each application while others stand by.

</details>

### 3. What is an ApplicationSet in ArgoCD?

- A) A group of manually created Applications
- B) A template that generates Applications dynamically based on generators
- C) A backup of Application configurations
- D) A collection of Helm charts

<details>
<summary>Show Answer</summary>

**Answer: B) A template that generates Applications dynamically based on generators**

**Explanation:**
ApplicationSet is a controller that uses generators (List, Cluster, Git, Matrix, etc.) to automatically create and manage multiple ArgoCD Applications from a single template. This enables scalable multi-cluster and multi-environment deployments.

</details>

### 4. Which ApplicationSet generator creates Applications based on registered cluster secrets?

- A) List generator
- B) Git generator
- C) Cluster generator
- D) Matrix generator

<details>
<summary>Show Answer</summary>

**Answer: C) Cluster generator**

**Explanation:**
The Cluster generator iterates over all clusters registered in ArgoCD (stored as secrets) and generates an Application for each one. This enables automatic deployment to new clusters without modifying the ApplicationSet.

</details>

### 5. How can IAM Identity Center (SSO) be integrated with ArgoCD?

- A) Direct database connection
- B) SAML or OIDC authentication with group-based RBAC
- C) SSH key authentication
- D) API key management

<details>
<summary>Show Answer</summary>

**Answer: B) SAML or OIDC authentication with group-based RBAC**

**Explanation:**
ArgoCD supports SAML and OIDC for SSO integration. IAM Identity Center groups can be mapped to ArgoCD RBAC roles, enabling centralized access management where permissions are controlled through your identity provider.

</details>

### 6. What is the purpose of External Secrets Operator in GitOps?

- A) To encrypt git repositories
- B) To sync secrets from external providers (AWS Secrets Manager) to Kubernetes
- C) To rotate TLS certificates
- D) To manage SSH keys for git access

<details>
<summary>Show Answer</summary>

**Answer: B) To sync secrets from external providers (AWS Secrets Manager) to Kubernetes**

**Explanation:**
External Secrets Operator automatically creates Kubernetes secrets from external secret management systems like AWS Secrets Manager, HashiCorp Vault, or Azure Key Vault. This keeps sensitive data out of git while maintaining GitOps workflows.

</details>

### 7. In ArgoCD project configuration, what does `sourceRepos` restrict?

- A) Target clusters for deployment
- B) Allowed git repositories for applications
- C) Namespace selection
- D) Resource quotas

<details>
<summary>Show Answer</summary>

**Answer: B) Allowed git repositories for applications**

**Explanation:**
The `sourceRepos` field in ArgoCD Projects specifies which git repositories can be used as sources for Applications in that project. This provides security boundaries by preventing unauthorized repository access.

</details>

### 8. What is the benefit of using Matrix generator in ApplicationSets?

- A) It performs mathematical calculations
- B) It combines multiple generators to create Cartesian product of parameters
- C) It encrypts application manifests
- D) It validates YAML syntax

<details>
<summary>Show Answer</summary>

**Answer: B) It combines multiple generators to create Cartesian product of parameters**

**Explanation:**
The Matrix generator combines two or more generators, creating Applications for every combination of their outputs. For example, combining a Cluster generator with a List generator deploys multiple services to multiple clusters.

</details>

### 9. When managing NodePools through GitOps, what is a key consideration?

- A) NodePools cannot be managed via GitOps
- B) Changes should be gradual to avoid disrupting running workloads
- C) NodePools must be in the same namespace as ArgoCD
- D) Only Spot instances can be managed

<details>
<summary>Show Answer</summary>

**Answer: B) Changes should be gradual to avoid disrupting running workloads**

**Explanation:**
NodePool changes through GitOps should be carefully managed because modifications can trigger node replacements. Using strategies like Progressive Sync or separate Applications for node management helps avoid disruption.

</details>

### 10. What is the recommended way to add a remote cluster to ArgoCD?

- A) Edit the ArgoCD ConfigMap directly
- B) Use `argocd cluster add` or create a cluster Secret with credentials
- C) Install ArgoCD on each cluster
- D) Use kubectl port-forward

<details>
<summary>Show Answer</summary>

**Answer: B) Use `argocd cluster add` or create a cluster Secret with credentials**

**Explanation:**
Remote clusters are added using the `argocd cluster add` CLI command or by creating a Secret with the cluster's API server URL and credentials. ArgoCD uses these credentials to deploy and sync applications to remote clusters.

</details>
