# ArgoCD Security Quiz

This quiz tests your understanding of ArgoCD security features and best practices.

1. How does ArgoCD handle secrets in Git repositories by default?
   - A) It encrypts them automatically
   - B) It does not automatically encrypt Git secrets
   - C) It uses Kubernetes Secrets API
   - D) It requires a secrets manager

<details>
<summary>Show Answer</summary>

**Answer: B) It does not automatically encrypt Git secrets**

**Explanation:**
ArgoCD itself doesn't provide secret encryption. Sealed Secrets/SOPS store ciphertext in Git. ESO/Vault integrations can instead store external references and retrieve values; they do not automatically encrypt Git files. Base64 is not encryption.

</details>

2. Which tool seals Kubernetes Secrets using a controller public key?
   - A) SOPS
   - B) Sealed Secrets
   - C) Vault
   - D) KMS

<details>
<summary>Show Answer</summary>

**Answer: B) Sealed Secrets**

**Explanation:**
Sealed Secrets uses controller key pairs. Default strict scope also binds the name/namespace, while the decryption trust boundary depends on possession of the keys. The encrypted SealedSecret can be safely stored in Git and is decrypted by the Sealed Secrets controller in the cluster.

</details>

3. What is the purpose of ArgoCD's Dex component?
   - A) Container image scanning
   - B) OpenID Connect authentication and SSO
   - C) Network policy enforcement
   - D) Secret rotation

<details>
<summary>Show Answer</summary>

**Answer: B) OpenID Connect authentication and SSO**

**Explanation:**
Dex is an identity service that provides OpenID Connect (OIDC) authentication. It brokers LDAP, SAML, GitHub and other identities through OIDC. Direct OIDC in Argo CD does not always require Dex.

</details>

4. How can you restrict which namespaced resource kinds an Application manages?
   - A) Using Kubernetes ResourceQuotas
   - B) Using AppProject's namespaceResourceBlacklist or namespaceResourceWhitelist
   - C) Only changing Pod requests/limits
   - D) It's not possible in ArgoCD

<details>
<summary>Show Answer</summary>

**Answer: B) Using AppProject's namespaceResourceBlacklist or namespaceResourceWhitelist**

**Explanation:**
AppProjects can define `namespaceResourceBlacklist` (deny specific resources) or `namespaceResourceWhitelist` (allow only specific resources) to control namespaced kinds. Cluster-scoped resources use separate lists, and this does not inspect privileged Pod settings like an admission policy.

</details>

5. What is the recommended practice for ArgoCD API server exposure?
   - A) Expose it publicly with basic auth
   - B) Use protected access paths with TLS and authentication
   - C) Run it without any authentication
   - D) Only access it via port-forwarding

<details>
<summary>Show Answer</summary>

**Answer: B) Use protected access paths with TLS and authentication**

**Explanation:**
Use authenticated TLS through an Ingress/Gateway or protected internal path. Frontend TLS termination does not itself validate backend TLS. For sensitive environments, additional measures like VPN access or IP whitelisting are recommended.

</details>
