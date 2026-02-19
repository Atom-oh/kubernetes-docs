# Kubernetes Authentication and Authorization Quiz

> **Related Document**: [Kubernetes Authentication and Authorization System](../../security/02-kubernetes-auth-authz.md)

## Multiple Choice Questions

### 1. In Kubernetes X.509 certificate authentication, from which field is the username extracted?

- A) Subject Alternative Name (SAN)
- B) Common Name (CN)
- C) Organization Unit (OU)
- D) Issuer

<details>
<summary>Show Answer</summary>

**Answer: B) Common Name (CN)**

**Explanation:**
In X.509 certificates, the Common Name (CN) maps to the username, and the Organization (O) maps to groups.

</details>

### 2. What is the main difference between ClusterRole and Role in RBAC?

- A) ClusterRole is read-only, Role is read/write
- B) ClusterRole is cluster-wide scope, Role is namespace scope
- C) ClusterRole is admin-only, Role is for regular users
- D) ClusterRole applies to nodes only, Role applies to pods only

<details>
<summary>Show Answer</summary>

**Answer: B) ClusterRole is cluster-wide scope, Role is namespace scope**

**Explanation:**
Role defines permissions for resources within a specific namespace, while ClusterRole defines permissions for cluster-wide resources or non-namespaced resources.

</details>

### 3. What is the default path where ServiceAccount tokens are automatically mounted in pods?

- A) /var/run/secrets/kubernetes.io/token
- B) /etc/kubernetes/serviceaccount
- C) /var/run/secrets/kubernetes.io/serviceaccount
- D) /opt/kubernetes/secrets

<details>
<summary>Show Answer</summary>

**Answer: C) /var/run/secrets/kubernetes.io/serviceaccount**

**Explanation:**
ServiceAccount tokens are mounted by default at `/var/run/secrets/kubernetes.io/serviceaccount`.

</details>

### 4. What is the execution order of MutatingAdmissionWebhook and ValidatingAdmissionWebhook?

- A) Validating first, then Mutating
- B) Mutating first, then Validating
- C) Executed in parallel simultaneously
- D) Executed randomly without order

<details>
<summary>Show Answer</summary>

**Answer: B) Mutating first, then Validating**

**Explanation:**
Admission controller execution order: 1) MutatingAdmissionWebhook (modifies requests), 2) ValidatingAdmissionWebhook (validates requests).

</details>

### 5. What ConfigMap maps IAM users/roles to Kubernetes RBAC in EKS?

- A) kube-config
- B) aws-auth
- C) eks-iam-mapping
- D) cluster-auth

<details>
<summary>Show Answer</summary>

**Answer: B) aws-auth**

**Explanation:**
In Amazon EKS, the `aws-auth` ConfigMap (in kube-system namespace) maps AWS IAM users and roles to Kubernetes users and groups.

</details>

### 6. Which authentication method is recommended for production Kubernetes clusters?

- A) Static token file
- B) Basic authentication
- C) OIDC (OpenID Connect)
- D) Anonymous authentication

<details>
<summary>Show Answer</summary>

**Answer: C) OIDC (OpenID Connect)**

**Explanation:**
OIDC provides enterprise-grade authentication with features like token expiration, refresh tokens, and integration with identity providers like Okta, Azure AD, and Google.

</details>

### 7. What is the purpose of the `system:masters` group in Kubernetes?

- A) To manage master nodes
- B) To provide cluster-admin privileges
- C) To schedule pods on master nodes
- D) To manage system namespaces

<details>
<summary>Show Answer</summary>

**Answer: B) To provide cluster-admin privileges**

**Explanation:**
The `system:masters` group is bound to the `cluster-admin` ClusterRole, granting full administrative access to the cluster.

</details>

### 8. How do you restrict a ServiceAccount to only read pods in a specific namespace?

- A) ClusterRole + ClusterRoleBinding
- B) Role + ClusterRoleBinding
- C) ClusterRole + RoleBinding
- D) Role + RoleBinding

<details>
<summary>Show Answer</summary>

**Answer: D) Role + RoleBinding**

**Explanation:**
For namespace-scoped permissions, use a Role (defines permissions within a namespace) with a RoleBinding (binds the role to a subject within the same namespace).

</details>

### 9. What is the purpose of the `impersonate` verb in RBAC?

- A) To create fake resources
- B) To allow a user to act as another user or group
- C) To duplicate resources
- D) To mask resource names

<details>
<summary>Show Answer</summary>

**Answer: B) To allow a user to act as another user or group**

**Explanation:**
The `impersonate` verb allows a user to perform actions as if they were another user, group, or ServiceAccount. This is useful for debugging and administrative purposes.

</details>

### 10. Which file contains the ServiceAccount token in a mounted volume?

- A) ca.crt
- B) namespace
- C) token
- D) serviceaccount.json

<details>
<summary>Show Answer</summary>

**Answer: C) token**

**Explanation:**
The ServiceAccount volume mount contains three files: `ca.crt` (CA certificate), `namespace` (current namespace), and `token` (JWT token for authentication).

</details>

## Short Answer Questions

### 1. What is the main difference between user accounts and service accounts in Kubernetes?

<details>
<summary>Show Answer</summary>

**Answer: User accounts are managed externally and not directly managed by Kubernetes, while service accounts are namespace-scoped resources managed through the Kubernetes API.**

</details>

### 2. How do you disable automatic ServiceAccount token mounting?

<details>
<summary>Show Answer</summary>

**Answer: Set `automountServiceAccountToken: false` in either the ServiceAccount or Pod spec.**

</details>

### 3. What is the difference between `rules` and `aggregationRule` in a ClusterRole?

<details>
<summary>Show Answer</summary>

**Answer: `rules` directly defines permissions, while `aggregationRule` automatically combines permissions from other ClusterRoles that match specific labels.**

**Explanation:**
Aggregated ClusterRoles are useful for extending built-in roles without modifying them directly.

</details>

### 4. What is the TokenRequest API and why is it preferred over static tokens?

<details>
<summary>Show Answer</summary>

**Answer: TokenRequest API creates time-limited, audience-bound tokens that are more secure than long-lived static tokens.**

**Explanation:**
Tokens from TokenRequest API expire automatically and are bound to specific audiences, reducing the risk of token theft and misuse.

</details>

### 5. How does Kubernetes determine which authentication method to use when multiple are configured?

<details>
<summary>Show Answer</summary>

**Answer: Kubernetes tries each authentication method in sequence until one succeeds. The first successful authentication is used.**

**Explanation:**
Authentication methods are tried in a chain. If all methods fail, the request is rejected with a 401 Unauthorized error.

</details>

## Hands-on Questions

### 1. Write a Role and RoleBinding that meets the following requirements:

- Namespace: development
- Permissions: Pod read (get, list, watch), ConfigMap full access
- User: developer@example.com

<details>
<summary>Show Answer</summary>

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: development
  name: developer-role
rules:
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "list", "watch"]
- apiGroups: [""]
  resources: ["configmaps"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: developer-binding
  namespace: development
subjects:
- kind: User
  name: developer@example.com
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: developer-role
  apiGroup: rbac.authorization.k8s.io
```

</details>

### 2. Create a ServiceAccount with a custom token expiration time.

<details>
<summary>Show Answer</summary>

```yaml
# ServiceAccount definition
apiVersion: v1
kind: ServiceAccount
metadata:
  name: custom-sa
  namespace: default
---
# Pod using projected token with custom expiration
apiVersion: v1
kind: Pod
metadata:
  name: app-with-custom-token
spec:
  serviceAccountName: custom-sa
  containers:
  - name: app
    image: nginx
    volumeMounts:
    - name: token
      mountPath: /var/run/secrets/tokens
  volumes:
  - name: token
    projected:
      sources:
      - serviceAccountToken:
          path: token
          expirationSeconds: 3600  # 1 hour
          audience: api
```

**Explanation:**
Using projected volumes with `serviceAccountToken`, you can specify custom `expirationSeconds` (minimum 600 seconds) and `audience` for the token.

</details>

### 3. Write a command to check what permissions a specific user has.

<details>
<summary>Show Answer</summary>

```bash
# Check if a user can perform a specific action
kubectl auth can-i create deployments --as=developer@example.com -n development

# List all permissions for a user in a namespace
kubectl auth can-i --list --as=developer@example.com -n development

# Check permissions for a ServiceAccount
kubectl auth can-i --list --as=system:serviceaccount:default:my-sa

# Impersonate a group
kubectl auth can-i create pods --as=developer@example.com --as-group=developers -n development
```

**Explanation:**
The `kubectl auth can-i` command allows checking permissions for the current user or impersonating other users/groups to verify their access levels.

</details>

## Advanced Questions

### 1. Design a security strategy for tenant isolation in a multi-tenant Kubernetes cluster.

<details>
<summary>Show Answer</summary>

**Namespace and RBAC Design:**
- Create separate namespaces per tenant
- Apply Pod Security Standards
- Implement NetworkPolicy for network isolation
- Set ResourceQuota for resource limits

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: tenant-alpha
  labels:
    tenant: alpha
    pod-security.kubernetes.io/enforce: restricted
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: tenant-alpha
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
---
apiVersion: v1
kind: ResourceQuota
metadata:
  name: tenant-quota
  namespace: tenant-alpha
spec:
  hard:
    requests.cpu: "10"
    requests.memory: 20Gi
    limits.cpu: "20"
    limits.memory: 40Gi
    pods: "50"
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: tenant-admin
  namespace: tenant-alpha
rules:
- apiGroups: ["", "apps", "batch"]
  resources: ["*"]
  verbs: ["*"]
- apiGroups: ["networking.k8s.io"]
  resources: ["networkpolicies"]
  verbs: ["get", "list"]  # Read-only for network policies
```

**Additional Security Measures:**
- Use separate ServiceAccounts per application
- Implement audit logging
- Use admission webhooks for policy enforcement
- Consider using Hierarchical Namespaces for sub-tenant management

</details>

### 2. Explain the complete authentication and authorization flow when a kubectl command is executed.

<details>
<summary>Show Answer</summary>

**Complete Flow:**

1. **Client Authentication (kubeconfig)**
   - kubectl reads `~/.kube/config`
   - Extracts credentials (certificate, token, or exec plugin)
   - For EKS: `aws eks get-token` generates temporary token

2. **API Server Authentication**
   - API server receives request with credentials
   - Tries authentication methods in order:
     - X.509 client certificates
     - Bearer tokens (ServiceAccount, OIDC)
     - Authentication proxy
     - Webhook token authentication
   - First successful method determines identity

3. **Authorization**
   - API server checks authorization (typically RBAC)
   - Evaluates all applicable Roles/ClusterRoles
   - Decision: Allow or Deny
   - If multiple authorizers: first non-deny wins

4. **Admission Control**
   - **Mutating Admission**: modifies the request
     - Adds defaults, injects sidecars
   - **Validating Admission**: validates the request
     - Enforces policies, quotas
   - Both can reject the request

5. **Persistence**
   - If all checks pass, resource is stored in etcd
   - Response returned to client

```
kubectl -> kubeconfig -> API Server
                            |
                     Authentication
                            |
                     Authorization (RBAC)
                            |
                   Mutating Admission
                            |
                  Validating Admission
                            |
                         etcd
```

**Key Points:**
- Authentication determines WHO you are
- Authorization determines WHAT you can do
- Admission controls HOW resources are modified/validated

</details>
