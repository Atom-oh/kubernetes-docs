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

### 2. What is a key advantage of Terraform Cloud over self-hosted Terraform?

- A) Free unlimited usage
- B) Managed state, runs, and collaboration features
- C) Faster execution speed
- D) Support for more providers

<details>
<summary>Show Answer</summary>

**Answer: B) Managed state, runs, and collaboration features**

**Explanation:**
Terraform Cloud provides managed remote state storage, run execution, team collaboration, policy enforcement (Sentinel), and a private module registry. These managed features reduce operational overhead compared to self-hosted setups.

</details>

### 3. How does FluxCD differ from ArgoCD in its architecture?

- A) FluxCD has no UI
- B) FluxCD uses a pull-based, distributed architecture without central server
- C) FluxCD only supports Helm
- D) FluxCD requires a database

<details>
<summary>Show Answer</summary>

**Answer: B) FluxCD uses a pull-based, distributed architecture without central server**

**Explanation:**
FluxCD runs controllers directly in each cluster that pull from git, while ArgoCD uses a centralized server model. FluxCD's approach is more lightweight and scales naturally in multi-cluster scenarios without a central hub.

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
The Image Automation Controller watches container registries for new image tags, then automatically commits updates to git repositories. This enables fully automated deployments when new images are pushed, maintaining GitOps principles.

</details>

### 5. In Atlantis workflow, what happens when a PR is approved and merged?

- A) Terraform plan runs automatically
- B) Atlantis runs terraform apply on the merged code
- C) The PR is closed without action
- D) A new branch is created

<details>
<summary>Show Answer</summary>

**Answer: B) Atlantis runs terraform apply on the merged code**

**Explanation:**
When configured with auto-apply or after explicit approval, Atlantis runs `terraform apply` after PR merge. This ensures infrastructure changes are applied only after code review and approval, maintaining change control.

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
AIOps can monitor metrics, detect issues in the green deployment (error rates, latency), and automatically create a PR to shift traffic weights back to blue. This maintains GitOps principles while enabling automated incident response.

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

### 9. When comparing FluxCD and ArgoCD, which statement is accurate?

- A) ArgoCD has better multi-tenancy through its Project model
- B) FluxCD has a richer built-in UI
- C) ArgoCD uses GitOps while FluxCD doesn't
- D) FluxCD requires external databases

<details>
<summary>Show Answer</summary>

**Answer: A) ArgoCD has better multi-tenancy through its Project model**

**Explanation:**
ArgoCD's Project resource provides robust multi-tenancy with fine-grained access control over repositories, clusters, and namespaces. FluxCD achieves multi-tenancy through namespace isolation but with less granular control.

</details>

### 10. In Terraform Cloud, what is a Sentinel policy?

- A) A backup strategy
- B) A policy-as-code framework for governance and compliance
- C) A state encryption method
- D) A module versioning system

<details>
<summary>Show Answer</summary>

**Answer: B) A policy-as-code framework for governance and compliance**

**Explanation:**
Sentinel is HashiCorp's policy-as-code framework that enforces rules before Terraform applies changes. Policies can mandate tagging, restrict instance types, require encryption, or enforce any custom compliance requirements.

</details>
