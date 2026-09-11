# ArgoCD Projects and RBAC Quiz

This quiz tests your understanding of ArgoCD Projects and Role-Based Access Control.

1. What is the primary purpose of an ArgoCD Project (AppProject)?
   - A) To group related Git repositories
   - B) To provide logical grouping of applications with access restrictions
   - C) To manage Kubernetes namespaces
   - D) To configure CI/CD pipelines

<details>
<summary>Show Answer</summary>

**Answer: B) To provide logical grouping of applications with access restrictions**

**Explanation:**
AppProjects provide a logical grouping of Applications with restrictions on what sources, destinations, and resources are allowed. They limit Argo CD deployment scope; Kubernetes RBAC, Pod Security Admission, network isolation and quotas remain separate controls.

</details>

2. What does the `sourceRepos` field in an AppProject control?
   - A) The Git branches that can be used
   - B) Allowed source repositories (Git/Helm/OCI)
   - C) The container image repositories
   - D) The Helm chart versions

<details>
<summary>Show Answer</summary>

**Answer: B) Allowed source repositories (Git/Helm/OCI)**

**Explanation:**
The `sourceRepos` field restricts which Git, Helm and OCI repositories Applications can use as sources, rather than selecting Git branches or container-image registries. Using `*` allows any repository, while specific URLs limit to those repositories only.

</details>

3. How do you restrict which clusters and namespaces an AppProject can deploy to?
   - A) Using the `destinations` field
   - B) Using the `clusters` field
   - C) Using the `namespaces` field
   - D) Using Kubernetes NetworkPolicies

<details>
<summary>Show Answer</summary>

**Answer: A) Using the `destinations` field**

**Explanation:**
The `destinations` field defines allowed cluster and namespace combinations. Each entry matches a server or registered cluster name with a namespace. This is deployment-target scope, distinct from sourceNamespaces for Application CR locations.

</details>

4. What is the purpose of `clusterResourceWhitelist` in an AppProject?
   - A) To allow specific cluster-scoped resources to be managed
   - B) To whitelist IP addresses
   - C) To allow specific users
   - D) To enable specific features

<details>
<summary>Show Answer</summary>

**Answer: A) To allow specific cluster-scoped resources to be managed**

**Explanation:**
A new custom project without an allowlist cannot manage cluster-scoped resources. The initially permissive default project is an exception because it explicitly allows every kind. The `clusterResourceWhitelist` allows specific kinds (like Namespaces or ClusterRoles) to be managed by Applications in the project.

</details>

5. How do you define a role within an ArgoCD Project?
   - A) Using Kubernetes RBAC
   - B) Using the `roles` field in the AppProject spec
   - C) Using a separate Role CRD
   - D) Roles cannot be defined in projects

<details>
<summary>Show Answer</summary>

**Answer: B) Using the `roles` field in the AppProject spec**

**Explanation:**
Project roles are defined in the `spec.roles` field of an AppProject. Each role has a name, description, policies (what actions are allowed), and issued-token metadata or group bindings. Signed JWTs are issued through the CLI/API; declaring metadata alone does not issue a token.

</details>
