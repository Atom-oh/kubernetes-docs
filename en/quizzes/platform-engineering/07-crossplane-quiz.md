# Crossplane Quiz

1. What is the core problem that Crossplane Compositions solve?
   - A) Configuring Kubernetes cluster networking
   - B) Bundling multiple infrastructure resources into a single abstracted API for self-service
   - C) Automating container image builds
   - D) Optimizing Pod resource requests

<details>
<summary>Show Answer</summary>

**Answer: B) Bundling multiple infrastructure resources into a single abstracted API for self-service**

**Explanation:**
Compositions package multiple Managed Resources (RDS instance, SecurityGroup, SubnetGroup, etc.) into a single Composite Resource (XR). Developers can provision required infrastructure through simple Claims without needing to understand complex infrastructure details.

</details>

---

2. What is the relationship between Crossplane Claims (XC) and Composite Resources (XR)?
   - A) Claims are cluster-scoped and XRs are namespace-scoped
   - B) Claims are namespace-scoped requests and XRs are cluster-scoped actual resources
   - C) Claims and XRs are identical resources
   - D) XRs are backup copies of Claims

<details>
<summary>Show Answer</summary>

**Answer: B) Claims are namespace-scoped requests and XRs are cluster-scoped actual resources**

**Explanation:**
Claims (XC) are namespace-scoped interfaces for developers to request infrastructure. When a Claim is created, a corresponding Composite Resource (XR) is created at the cluster scope, and the XR provisions actual Managed Resources according to the Composition.

</details>

---

3. Why use IRSA (IAM Roles for Service Accounts) when managing AWS resources with Crossplane?
   - A) To reduce Crossplane license costs
   - B) To securely pass AWS credentials to Pods and apply the principle of least privilege
   - C) To improve Crossplane performance
   - D) For multi-cluster support

<details>
<summary>Show Answer</summary>

**Answer: B) To securely pass AWS credentials to Pods and apply the principle of least privilege**

**Explanation:**
IRSA eliminates the need to directly manage AWS Access Keys by associating IAM Roles with Kubernetes ServiceAccounts, automatically injecting temporary credentials. This enhances security and allows granting only the minimum IAM permissions needed per Provider.

</details>

---

4. What is the biggest architectural difference between Terraform and Crossplane?
   - A) Terraform uses YAML, Crossplane uses HCL
   - B) Terraform uses imperative execution (apply/destroy), Crossplane uses continuous reconciliation via Kubernetes controllers
   - C) Terraform only supports cloud, Crossplane only supports on-premises
   - D) Terraform is free, Crossplane is paid

<details>
<summary>Show Answer</summary>

**Answer: B) Terraform uses imperative execution (apply/destroy), Crossplane uses continuous reconciliation via Kubernetes controllers**

**Explanation:**
Terraform is a workflow-based tool that runs via `terraform apply`/`destroy` commands. Crossplane operates using the Kubernetes controller pattern, continuously comparing declared state with actual state and reconciling differences. This enables automatic drift detection and correction.

</details>

---

5. In what scenario would you use both ACK and Crossplane together?
   - A) ACK and Crossplane are incompatible, so only use one
   - B) Use ACK for simple AWS resources and Crossplane Compositions for complex multi-resource abstractions
   - C) ACK is for development, Crossplane for production only
   - D) ACK manages networking, Crossplane manages storage only

<details>
<summary>Show Answer</summary>

**Answer: B) Use ACK for simple AWS resources and Crossplane Compositions for complex multi-resource abstractions**

**Explanation:**
ACK is suited for simple resource management that maps 1:1 to the AWS API, while Crossplane excels at packaging multiple resources into a single abstracted API through Compositions. Simple S3 buckets can be managed with ACK, while RDS+SecurityGroup+SubnetGroup packages are better suited for Crossplane Compositions.

</details>

---

6. Why are Crossplane Connection Details important?
   - A) Monitor network connection status
   - B) Automatically generate Kubernetes Secrets with provisioned resource access info (endpoints, passwords, etc.)
   - C) Manage connections between Crossplane Providers
   - D) Configure network connections between multi-cluster

<details>
<summary>Show Answer</summary>

**Answer: B) Automatically generate Kubernetes Secrets with provisioned resource access info (endpoints, passwords, etc.)**

**Explanation:**
Connection Details automatically store provisioned resource access information (database endpoint, port, username, password, etc.) in Kubernetes Secrets. Applications can mount these Secrets to connect to the provisioned infrastructure.

</details>

---

7. What is the correct developer self-service workflow order in a Backstage + Crossplane integration?
   - A) ArgoCD deployment → Backstage catalog registration → Crossplane Claim creation
   - B) Backstage Template generates Crossplane Claim YAML → Git push → ArgoCD sync → Crossplane provisioning
   - C) Crossplane provisioning → Backstage Template creation → Git push
   - D) Git push → Backstage catalog registration → ArgoCD deployment

<details>
<summary>Show Answer</summary>

**Answer: B) Backstage Template generates Crossplane Claim YAML → Git push → ArgoCD sync → Crossplane provisioning**

**Explanation:**
When a developer enters parameters (DB size, environment, etc.) in a Backstage Template, the Template generates Crossplane Claim YAML and pushes it to the Git repository. ArgoCD detects the change and syncs it to the cluster, where Crossplane processes the Claim and provisions the actual infrastructure.

</details>

---

8. How is Crossplane's drift detection superior compared to Terraform?
   - A) Terraform doesn't support drift detection
   - B) Crossplane controllers continuously monitor actual state and auto-correct, while Terraform requires manual `plan`/`apply`
   - C) Crossplane provisions faster
   - D) Crossplane supports more clouds

<details>
<summary>Show Answer</summary>

**Answer: B) Crossplane controllers continuously monitor actual state and auto-correct, while Terraform requires manual `plan`/`apply`**

**Explanation:**
Crossplane controllers periodically check the actual state of cloud resources and automatically correct any drift from the declared state. Terraform requires manually running `terraform plan` to detect drift and `terraform apply` to fix it, making Crossplane's approach more suitable for GitOps workflows.

</details>
