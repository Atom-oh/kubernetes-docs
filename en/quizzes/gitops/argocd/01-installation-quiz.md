# ArgoCD Installation Quiz

This quiz tests your understanding of ArgoCD installation and configuration.

1. What is the recommended method for installing ArgoCD in a production environment?
   - A) kubectl apply from the raw GitHub URL
   - B) Helm chart with custom values
   - C) Docker Compose
   - D) Manual binary installation

<details>
<summary>Show Answer</summary>

**Answer: B) Helm chart with custom values**

**Explanation:**
While ArgoCD can be installed using kubectl apply from the official manifests, using a Helm chart is recommended for production environments because it allows for easier customization, upgrades, and management of configuration values.

</details>

2. Which namespace is ArgoCD typically installed into by default?
   - A) default
   - B) kube-system
   - C) argocd
   - D) gitops

<details>
<summary>Show Answer</summary>

**Answer: C) argocd**

**Explanation:**
By convention, ArgoCD is installed into the `argocd` namespace. This keeps ArgoCD components isolated and makes it easier to manage RBAC and resource quotas.

</details>

3. What is the purpose of the ArgoCD Repo Server component?
   - A) To store application state
   - B) To clone Git repositories and generate Kubernetes manifests
   - C) To serve the web UI
   - D) To manage user authentication

<details>
<summary>Show Answer</summary>

**Answer: B) To clone Git repositories and generate Kubernetes manifests**

**Explanation:**
The Repo Server is responsible for cloning Git repositories and generating Kubernetes manifests from various sources (Helm, Kustomize, plain YAML). It caches repository data for performance.

</details>

4. How do you retrieve the initial admin password after installing ArgoCD?
   - A) It's printed during installation
   - B) From a Secret named argocd-initial-admin-secret
   - C) From the ArgoCD ConfigMap
   - D) It's always "admin"

<details>
<summary>Show Answer</summary>

**Answer: B) From a Secret named argocd-initial-admin-secret**

**Explanation:**
The initial admin password is auto-generated and stored in a Kubernetes Secret named `argocd-initial-admin-secret`. You can retrieve it using: `kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d`

</details>

5. Which ArgoCD installation mode uses fewer resources but has limited functionality?
   - A) HA mode
   - B) Core mode
   - C) Lite mode
   - D) Minimal mode

<details>
<summary>Show Answer</summary>

**Answer: B) Core mode**

**Explanation:**
ArgoCD Core mode installs only the essential components (Application Controller and Repo Server) without the API Server, UI, or Dex. This mode is suitable for environments where ArgoCD is managed entirely through Git and the CLI.

</details>
