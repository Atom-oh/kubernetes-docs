# GitOps Tools Comparison Quiz

This quiz tests your understanding of GitOps tools and how to choose between them.

1. Which GitOps tool provides a built-in Web UI out of the box?
   - A) FluxCD
   - B) ArgoCD
   - C) Both
   - D) Neither

<details>
<summary>Show Answer</summary>

**Answer: B) ArgoCD**

**Explanation:**
ArgoCD includes a built-in, feature-rich Web UI for managing applications. FluxCD is CLI-first and doesn't include a built-in UI, though third-party UIs like Weave GitOps can be added.

</details>

2. Which tool has better native support for OCI artifacts as deployment sources?
   - A) ArgoCD
   - B) FluxCD
   - C) Both have equal support
   - D) Neither supports OCI

<details>
<summary>Show Answer</summary>

**Answer: B) FluxCD**

**Explanation:**
FluxCD has first-class support for OCI artifacts through its OCIRepository source type, allowing you to store and deploy from OCI-compliant registries. ArgoCD's OCI support is limited to Helm charts.

</details>

3. Which tool provides built-in image automation (automatic Git updates for new images)?
   - A) ArgoCD (native)
   - B) FluxCD (native)
   - C) Both have native support
   - D) Neither has native support

<details>
<summary>Show Answer</summary>

**Answer: B) FluxCD (native)**

**Explanation:**
FluxCD has built-in Image Automation through its Image Reflector and Image Automation controllers. ArgoCD requires the separate Argo Image Updater project for similar functionality.

</details>

4. For which use case would ArgoCD be the better choice?
   - A) CLI-driven workflows without UI requirements
   - B) Teams needing visual deployment management and SSO integration
   - C) Minimal resource footprint requirements
   - D) OCI artifact-based deployments

<details>
<summary>Show Answer</summary>

**Answer: B) Teams needing visual deployment management and SSO integration**

**Explanation:**
ArgoCD excels in environments where teams need visual feedback through its Web UI, comprehensive RBAC, and SSO integration with enterprise identity providers.

</details>

5. Can ArgoCD and FluxCD be used together in the same cluster?
   - A) No, they are mutually exclusive
   - B) Yes, they can complement each other
   - C) Only in development environments
   - D) Only with special configuration

<details>
<summary>Show Answer</summary>

**Answer: B) Yes, they can complement each other**

**Explanation:**
ArgoCD and FluxCD can be used together. A common pattern is using FluxCD for infrastructure management and image automation while using ArgoCD for application deployments with its UI.

</details>
