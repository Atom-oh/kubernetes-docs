# ArgoCD Security Quiz

This quiz tests your understanding of ArgoCD security features and best practices.

1. How does ArgoCD handle secrets in Git repositories by default?
   - A) It encrypts them automatically
   - B) It doesn't handle secrets specially - they're stored as plain text
   - C) It uses Kubernetes Secrets API
   - D) It requires a secrets manager

<details>
<summary>Show Answer</summary>

**Answer: B) It doesn't handle secrets specially - they're stored as plain text**

**Explanation:**
ArgoCD itself doesn't provide secret encryption. Secrets in Git should be encrypted using tools like Sealed Secrets, SOPS, External Secrets Operator, or Vault before committing to Git.

</details>

2. Which tool encrypts Kubernetes Secrets using a cluster-specific key?
   - A) SOPS
   - B) Sealed Secrets
   - C) Vault
   - D) KMS

<details>
<summary>Show Answer</summary>

**Answer: B) Sealed Secrets**

**Explanation:**
Sealed Secrets uses a cluster-specific key pair to encrypt secrets. The encrypted SealedSecret can be safely stored in Git and is decrypted by the Sealed Secrets controller in the cluster.

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
Dex is an identity service that provides OpenID Connect (OIDC) authentication. It enables ArgoCD to integrate with various identity providers (LDAP, SAML, GitHub, etc.) for single sign-on.

</details>

4. How can you restrict which Kubernetes resources an Application can create?
   - A) Using Kubernetes ResourceQuotas
   - B) Using AppProject's namespaceResourceBlacklist or namespaceResourceWhitelist
   - C) Using Pod Security Policies
   - D) It's not possible in ArgoCD

<details>
<summary>Show Answer</summary>

**Answer: B) Using AppProject's namespaceResourceBlacklist or namespaceResourceWhitelist**

**Explanation:**
AppProjects can define `namespaceResourceBlacklist` (deny specific resources) or `namespaceResourceWhitelist` (allow only specific resources) to control what types of Kubernetes resources Applications can manage.

</details>

5. What is the recommended practice for ArgoCD API server exposure?
   - A) Expose it publicly with basic auth
   - B) Keep it internal and use an ingress with TLS and authentication
   - C) Run it without any authentication
   - D) Only access it via port-forwarding

<details>
<summary>Show Answer</summary>

**Answer: B) Keep it internal and use an ingress with TLS and authentication**

**Explanation:**
The ArgoCD API server should be exposed through an ingress with TLS termination and proper authentication (SSO/OIDC). For sensitive environments, additional measures like VPN access or IP whitelisting are recommended.

</details>
