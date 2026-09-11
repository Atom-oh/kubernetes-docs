# ArgoCD Best Practices Quiz

This quiz tests your understanding of ArgoCD best practices and operational patterns.

1. Which pattern uses an administrator-owned root repository to declare multiple child Applications?
   - A) Manual configuration through the UI
   - B) App of Apps
   - C) Using kubectl apply directly
   - D) Configuration should never change

<details>
<summary>Show Answer</summary>

**Answer: B) App of Apps**

**Explanation:**
App of Apps uses a root Application to manage child Applications. It is not synonymous with self-managing Argo CD and is not required for every installation. Treat it as an administrative capability, restrict repository writes, and retain an independent bootstrap/recovery path.

</details>

2. What is the recommended repository structure for GitOps?
   - A) Mix application code and manifests in the same repo
   - B) Separate repositories for application code and deployment manifests
   - C) Store everything in a single file
   - D) Use only Helm charts from public repositories

<details>
<summary>Show Answer</summary>

**Answer: B) Separate repositories for application code and deployment manifests**

**Explanation:**
Separating application code from deployment manifests provides clearer audit trails, allows different teams to manage each, and can avoid rebuilding application code for deployment-only changes. CI triggers, path filters, and repository boundaries still need explicit design.

</details>

3. How can you reuse common manifests while expressing environment-specific values?
   - A) Create separate Applications for each environment
   - B) Use Kustomize overlays or Helm values files per environment
   - C) Hardcode values in the manifests
   - D) Use environment variables in pods

<details>
<summary>Show Answer</summary>

**Answer: B) Use Kustomize overlays or Helm values files per environment**

**Explanation:**
Using Kustomize overlays or Helm values files allows you to maintain a common base configuration while customizing specific values (replicas, resources, domains) per environment.

</details>

4. What is the recommended approach for promoting changes across environments?
   - A) Direct commits to production branch
   - B) Pull requests with review from staging to production
   - C) Manual sync in the UI
   - D) Automatic promotion without review

<details>
<summary>Show Answer</summary>

**Answer: B) Pull requests with review from staging to production**

**Explanation:**
Using pull requests for promotion ensures changes are reviewed before reaching production, provides an audit trail, and allows for automated checks (tests, policy validation) before merging.

</details>

5. How should you handle secrets in a GitOps workflow?
   - A) Commit plain text secrets to Git
   - B) Use encrypted secrets (Sealed Secrets, SOPS) or external secret managers
   - C) Manually create secrets in each cluster
   - D) Store secrets in environment variables

<details>
<summary>Show Answer</summary>

**Answer: B) Use encrypted secrets (Sealed Secrets, SOPS) or external secret managers**

**Explanation:**
Secrets should never be stored in plain text in Git. Use encryption tools like Sealed Secrets or SOPS, or external secret managers like HashiCorp Vault with the External Secrets Operator.

</details>
