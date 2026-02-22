# ArgoCD Applications Quiz

This quiz tests your understanding of ArgoCD Applications and their configuration.

1. What is the primary purpose of an ArgoCD Application resource?
   - A) To define user access controls
   - B) To specify the desired state of an application and its sync settings
   - C) To configure notifications
   - D) To manage secrets

<details>
<summary>Show Answer</summary>

**Answer: B) To specify the desired state of an application and its sync settings**

**Explanation:**
An ArgoCD Application is a Kubernetes custom resource that defines the source (Git repo, path, revision) and destination (cluster, namespace) of an application, along with sync policies and health checks.

</details>

2. Which field in an Application spec defines where the manifests should be deployed?
   - A) source
   - B) target
   - C) destination
   - D) cluster

<details>
<summary>Show Answer</summary>

**Answer: C) destination**

**Explanation:**
The `destination` field specifies the target cluster (by server URL or name) and namespace where the application's resources should be deployed.

</details>

3. What does the `spec.source.path` field specify in an Application?
   - A) The path to the ArgoCD installation
   - B) The directory within the Git repository containing the manifests
   - C) The local file system path
   - D) The API server path

<details>
<summary>Show Answer</summary>

**Answer: B) The directory within the Git repository containing the manifests**

**Explanation:**
The `path` field under `source` specifies the directory within the Git repository that contains the Kubernetes manifests, Helm chart, or Kustomize configuration.

</details>

4. How can you deploy an application to a specific namespace that doesn't exist yet?
   - A) Manually create the namespace first
   - B) Use syncPolicy.syncOptions with CreateNamespace=true
   - C) It's not possible
   - D) Use a pre-sync hook

<details>
<summary>Show Answer</summary>

**Answer: B) Use syncPolicy.syncOptions with CreateNamespace=true**

**Explanation:**
Setting `CreateNamespace=true` in `syncPolicy.syncOptions` tells ArgoCD to automatically create the target namespace if it doesn't exist before syncing the application resources.

</details>

5. What is the difference between `targetRevision: HEAD` and `targetRevision: main`?
   - A) No difference
   - B) HEAD always points to the default branch, main is explicit
   - C) HEAD is faster
   - D) main supports webhooks, HEAD doesn't

<details>
<summary>Show Answer</summary>

**Answer: B) HEAD always points to the default branch, main is explicit**

**Explanation:**
`HEAD` is a symbolic reference that points to whatever the repository's default branch is, while `main` explicitly specifies the main branch. Using `HEAD` is more flexible if the default branch changes.

</details>

6. Which source type would you use to deploy a Helm chart from a Helm repository (not Git)?
   - A) git
   - B) helm
   - C) directory
   - D) kustomize

<details>
<summary>Show Answer</summary>

**Answer: B) helm**

**Explanation:**
When deploying from a Helm repository, you set `source.chart` and `source.repoURL` to point to the Helm repository, and ArgoCD will treat it as a Helm source rather than a Git source.

</details>

7. What happens when you set `spec.source.helm.releaseName`?
   - A) It creates a new Helm repository
   - B) It overrides the default release name (which is the Application name)
   - C) It enables Helm hooks
   - D) It sets the chart version

<details>
<summary>Show Answer</summary>

**Answer: B) It overrides the default release name (which is the Application name)**

**Explanation:**
By default, ArgoCD uses the Application name as the Helm release name. Setting `releaseName` explicitly allows you to use a different name for the Helm release.

</details>

8. How do you specify Helm values in an ArgoCD Application?
   - A) Only through values files in the repository
   - B) Only inline in the Application spec
   - C) Both through values files and inline values
   - D) Values must be stored in a ConfigMap

<details>
<summary>Show Answer</summary>

**Answer: C) Both through values files and inline values**

**Explanation:**
ArgoCD supports specifying Helm values through `spec.source.helm.valueFiles` (referencing files in the repo) and/or `spec.source.helm.values` (inline YAML). Both can be used together, with inline values taking precedence.

</details>
