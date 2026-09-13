# GitOps Automation Quiz

> **Related Document**: [GitOps Automation](../../ops/05-gitops-automation.md)

## Multiple Choice Questions

### 1. What is Atlantis in the context of Terraform automation?

- A) A cloud provider
- B) A pull request automation tool for Terraform
- C) A Terraform module registry
- D) A state file encryption service

<details>
<summary>Show Answer</summary>

**Answer: B) A pull request automation tool for Terraform**

**Explanation:**
Atlantis is a self-hosted application that listens for Terraform pull requests and runs `terraform plan` and `apply` automatically. It provides plan output as PR comments and enforces approval workflows before applying changes.

</details>

### 2. What is a key advantage of HCP Terraform over self-hosted Terraform?

- A) Free unlimited usage
- B) Managed state, runs, and collaboration features
- C) Faster execution speed
- D) Support for more providers

<details>
<summary>Show Answer</summary>

**Answer: B) Managed state, runs, and collaboration features**

**Explanation:**
HCP Terraform provides managed remote state storage, run execution, team collaboration, policy enforcement (Sentinel), and a private module registry. These managed features reduce operational overhead compared to self-hosted setups.

</details>

### 3. How does FluxCD differ from ArgoCD in its architecture?

- A) FluxCD has no UI
- B) Both use reconciliation, with different APIs, controllers and UI choices
- C) FluxCD only supports Helm
- D) FluxCD requires a database

<details>
<summary>Show Answer</summary>

**Answer: B) Both use reconciliation, with different APIs, controllers and UI choices**

**Explanation:**
Flux uses GitRepository, Kustomization and other controller-specific APIs. Argo CD also has multiple components and supports different deployment topologies. Resource use and multi-cluster behavior depend on configuration rather than a universal architectural ranking.

</details>

### 4. What does Flux Image Automation Controller do?

- A) Builds container images
- B) Scans registries and updates git with new image tags
- C) Deploys images to Kubernetes
- D) Manages image pull secrets

<details>
<summary>Show Answer</summary>

**Answer: B) Scans registries and updates git with new image tags**

**Explanation:**
The image-reflector-controller scans registries and evaluates ImagePolicies. The separate image-automation-controller applies those choices to marked files and commits them to Git. This enables fully automated deployments when new images are pushed, maintaining GitOps principles.

</details>

### 5. What is the ordinary Atlantis apply-and-merge sequence?

- A) Merging any PR always applies its Terraform automatically
- B) Review a PR plan, satisfy requirements, explicitly apply the saved plan, then merge
- C) Merge first and ignore the saved plan
- D) A successful plan is itself an apply

<details>
<summary>Show Answer</summary>

**Answer: B) Review a PR plan, satisfy requirements, explicitly apply the saved plan, then merge**

**Explanation:** Atlantis applies from the PR workflow; merge is not an apply trigger by itself. Optional automerge merges after successful applies. Review/re-plan changed commits and do not let a PR override server-enforced requirements.

</details>

### 6. What is a key benefit of AIOps in GitOps workflows?

- A) Eliminating the need for git
- B) Automated anomaly detection and response recommendations
- C) Faster container builds
- D) Reduced storage costs

<details>
<summary>Show Answer</summary>

**Answer: B) Automated anomaly detection and response recommendations**

**Explanation:**
AIOps applies machine learning to detect anomalies in metrics and logs, correlate events, and recommend or automate responses. In GitOps, this can include auto-generating PRs for scaling changes or traffic weight adjustments.

</details>

### 7. How can AIOps automate traffic weight changes in blue/green deployments?

- A) By directly modifying load balancer settings
- B) By detecting anomalies and creating PRs to update weight configurations in git
- C) By restarting failed pods
- D) By changing DNS records

<details>
<summary>Show Answer</summary>

**Answer: B) By detecting anomalies and creating PRs to update weight configurations in git**

**Explanation:**
AIOps can monitor metrics, detect issues in the green deployment (error rates, latency), and automatically create a PR to shift traffic weights back to blue. The proposal still needs data-quality checks, authorized approval and a constrained executor that rechecks current state, capacity and target health. An anomaly or a newly opened PR alone is not permission to shift traffic.

</details>

### 8. What is the purpose of Flux's GitRepository resource?

- A) To create git repositories
- B) To define a git source that Flux monitors for changes
- C) To backup Kubernetes resources to git
- D) To manage git credentials

<details>
<summary>Show Answer</summary>

**Answer: B) To define a git source that Flux monitors for changes**

**Explanation:**
GitRepository is a Flux custom resource that specifies a git repository URL, branch, and polling interval. Flux controllers watch these sources and trigger reconciliation when changes are detected.

</details>

### 9. Which statement about multi-tenancy is accurate?

- A) Argo CD is always more secure because it has AppProjects
- B) A Flux namespace alone completes tenant isolation
- C) Both require deliberate source, identity, RBAC and resource-boundary configuration
- D) Image automation also performs vulnerability scanning

<details>
<summary>Show Answer</summary>

**Answer: C) Both require deliberate source, identity, RBAC and resource-boundary configuration**

**Explanation:** AppProjects and Flux tenant identities constrain different parts of reconciliation. Neither automatically supplies every network, Kubernetes authorization or untrusted-code isolation boundary. Avoid having two controllers own the same resource fields.

</details>

### 10. In HCP Terraform, what is a Sentinel policy?

- A) A backup strategy
- B) A policy-as-code framework for governance and compliance
- C) A state encryption method
- D) A module versioning system

<details>
<summary>Show Answer</summary>

**Answer: B) A policy-as-code framework for governance and compliance**

**Explanation:**
Sentinel is HashiCorp's policy-as-code framework that enforces rules before Terraform applies changes. Policies can check tags, instance types, encryption or other modeled requirements. Their actual effect depends on policy-set scope, enforcement and handling of missing/unknown values; an example does not automatically cover every resource.

</details>
