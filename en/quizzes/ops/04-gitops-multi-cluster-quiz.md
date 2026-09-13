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
- B) By combining component-specific replication, controller sharding, and resilient placement
- C) By using external database replication
- D) By deploying across multiple regions

<details>
<summary>Show Answer</summary>

**Answer: B) By combining component-specific replication, controller sharding, and resilient placement**

**Explanation:**
The Application Controller shards target clusters rather than keeping every other replica on standby. ApplicationSet uses separate leader election, and the Server is stateless. Redis HA, placement, capacity and PDBs address different failure modes; adding replicas alone is not an availability guarantee.

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
The Cluster generator selects registered clusters using the configured selector and supplies their metadata. A default local cluster may lack a Secret, so Secret-label selection can exclude it. New clusters are selected only if their registration and labels match.

</details>

### 5. How can IAM Identity Center (SSO) be integrated with ArgoCD?

- A) Direct database connection
- B) SAML through Dex, with verified assertion attributes mapped to Argo CD RBAC
- C) SSH key authentication
- D) API key management

<details>
<summary>Show Answer</summary>

**Answer: B) SAML through Dex, with verified assertion attributes mapped to Argo CD RBAC**

**Explanation:**
This chapter follows the documented Identity Center SAML + Dex path. A SAML URL is not an OIDC issuer. Group assignment does not guarantee a groups claim; the upstream guide identifies group attribute mapping as a workaround. The minimal example explicitly maps verified email identities.

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
The `sourceRepos` field in ArgoCD Projects specifies which git repositories can be used as sources for Applications in that project. It constrains Application source selection, but does not itself supply repository credentials, target RBAC, or a sandbox for untrusted code.

</details>

### 8. What is the benefit of using Matrix generator in ApplicationSets?

- A) It performs mathematical calculations
- B) It combines two child generators to produce matching parameter combinations
- C) It encrypts application manifests
- D) It validates YAML syntax

<details>
<summary>Show Answer</summary>

**Answer: B) It combines two child generators to produce matching parameter combinations**

**Explanation:**
A Matrix generator has exactly two child generators. It combines their output parameters, subject to compatible keys and supported nesting restrictions. For example, combining a Cluster generator with a List generator deploys multiple services to multiple clusters.

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
NodePool changes through GitOps should be carefully managed because modifications can trigger node replacements. Review changes, replacement capacity, applicable disruption budgets and deletion behavior. Separate manually synchronized infrastructure Applications can limit accidental changes; no synchronization strategy guarantees that node replacement will be disruption-free.

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
Remote clusters are added using the `argocd cluster add` CLI command or by creating a Secret with the cluster's API server URL and credentials. The CLI can mutate target RBAC. The declarative AWS path requires existing role trust, EKS Access Entries/RBAC, real endpoint/CA data and network connectivity; a Secret alone grants none of those prerequisites.

</details>
