# ArgoCD Best Practices Quiz

This quiz tests your understanding of ArgoCD best practices and operational patterns.

1. What is the recommended approach for managing ArgoCD's own configuration?
   - A) Manual configuration through the UI
   - B) Managing ArgoCD with ArgoCD (app-of-apps pattern)
   - C) Using kubectl apply directly
   - D) Configuration should never change

<details>
<summary>Show Answer</summary>

**Answer: B) Managing ArgoCD with ArgoCD (app-of-apps pattern)**

**Explanation:**
The "app-of-apps" pattern involves having ArgoCD manage its own configuration and other ArgoCD Applications. This ensures ArgoCD's configuration is version-controlled and follows GitOps principles.

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
Separating application code from deployment manifests provides clearer audit trails, allows different teams to manage each, and prevents CI triggers from deployment changes.

</details>

3. How should you handle environment-specific configurations?
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
