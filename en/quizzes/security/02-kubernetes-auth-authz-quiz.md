# Kubernetes Authentication and Authorization Quiz

> **Related Document**: [Kubernetes Authentication and Authorization System](../../security/02-kubernetes-auth-authz.md)

> **Last Updated**: September 13, 2026

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
- B) ClusterRole is a cluster-scoped definition; Role is a namespaced definition
- C) ClusterRole is admin-only, Role is for regular users
- D) ClusterRole applies to nodes only, Role applies to pods only

<details>
<summary>Show Answer</summary>

**Answer: B) ClusterRole is a cluster-scoped definition; Role is a namespaced definition**

**Explanation:**
A ClusterRole can also define reusable permissions on namespaced resources. A RoleBinding referencing it limits the grant to the binding namespace; a ClusterRoleBinding grants its permissions cluster-wide. A definition alone grants nothing.

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
This is the default directory in a Linux Pod with automatic mounting enabled. The token is the `token` file inside it. Pods with `automountServiceAccountToken: false` or custom projected volumes can have different paths or no token.

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

<span id="_5-what-configmap-maps-iam-users-roles-to-kubernetes-rbac-in-eks"></span>

### 5. Which ConfigMap stores IAM mappings in the legacy EKS CONFIG_MAP authentication mode?

- A) kube-config
- B) aws-auth
- C) eks-iam-mapping
- D) cluster-auth

<details>
<summary>Show Answer</summary>

**Answer: B) aws-auth**

**Explanation:**
`kube-system/aws-auth` is the legacy IAM mapping. Use EKS access entries with appropriate RBAC or EKS access policies for current access management. During dual-mode migration, an access entry takes precedence for the same principal. Replacing the whole ConfigMap can remove node mappings.

</details>

<span id="_6-which-authentication-method-is-recommended-for-production-kubernetes-clusters"></span>

### 6. Which method integrates user login through ID tokens issued by an external identity provider?

- A) Static token file
- B) Basic authentication
- C) OIDC (OpenID Connect)
- D) Anonymous authentication

<details>
<summary>Show Answer</summary>

**Answer: C) OIDC (OpenID Connect)**

**Explanation:**
OIDC validates the issuer, audience, signature, and expiry of externally issued ID tokens. The IdP/client handles login and refresh; the API server does not issue refresh tokens. EKS IAM authentication is another user-access path, while IRSA/Pod Identity serve a different purpose: Pod access to AWS APIs.

</details>

### 7. What is the purpose of the `system:masters` group in Kubernetes?

- A) To manage master nodes
- B) To provide unrestricted API access that bypasses RBAC/webhook authorization
- C) To schedule pods on master nodes
- D) To manage system namespaces

<details>
<summary>Show Answer</summary>

**Answer: B) To provide unrestricted API access that bypasses RBAC/webhook authorization**

**Explanation:**
`system:masters` is a special authorization-bypass group. It is not equivalent to an ordinary administrator role binding, and deleting a ClusterRoleBinding does not revoke that bypass. Avoid assigning this group to ordinary administrators.

</details>

### 8. How do you restrict a ServiceAccount to only read pods in a specific namespace?

- A) ClusterRole + ClusterRoleBinding
- B) Role + ClusterRoleBinding
- C) Role only
- D) Role + RoleBinding

<details>
<summary>Show Answer</summary>

**Answer: D) Role + RoleBinding**

**Explanation:**
Use a Role allowing only Pod get/list/watch and a RoleBinding in that namespace, assuming no other grants. **ClusterRole + RoleBinding is also valid** and therefore is not a wrong-answer option. A ServiceAccount subject can explicitly belong to another namespace; the permission scope remains the binding namespace.

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
The default automatically mounted ServiceAccount volume provides these files (custom projections can differ): `ca.crt` (CA certificate), `namespace` (current namespace), and `token` (JWT token for authentication).

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

**Answer: Set `automountServiceAccountToken: false` at the ServiceAccount top level or in the Pod spec. The Pod setting takes precedence; explicitly declared projected token volumes still work.**

</details>

### 3. What is the difference between `rules` and `aggregationRule` in a ClusterRole?

<details>
<summary>Show Answer</summary>

**Answer: `rules` directly defines permissions, while `aggregationRule` automatically combines permissions from other ClusterRoles that match specific labels.**

**Explanation:**
The aggregation controller manages the target ClusterRole rules and can overwrite manual rule changes. Permission to add or edit label-selected roles also affects the resulting access.

</details>

### 4. What is the TokenRequest API and why is it preferred over static tokens?

<details>
<summary>Show Answer</summary>

**Answer: TokenRequest API creates time-limited, audience-bound tokens that are more secure than long-lived static tokens.**

**Explanation:**
Check the actual expiry returned by the server, which can adjust the requested lifetime. Kubelet rotates Pod-projected tokens, but the application must reload the file. A standalone TokenRequest does not itself provide automatic file rotation. These tokens remain secret bearer credentials.

</details>

### 5. How does Kubernetes determine which authentication method to use when multiple are configured?

<details>
<summary>Show Answer</summary>

**Answer: The first successful authentication result is used, but authenticator evaluation order is not guaranteed.**

**Explanation:**
Do not assume a fixed X.509 → OIDC → proxy order. Invalid credentials can result in 401. Anonymous handling of requests without credentials depends on server settings; an anonymous identity can still be denied by authorization.

</details>

## Hands-on Questions

### 1. Write a Role and RoleBinding that meets the following requirements:

- Namespace: development
- Permissions: Pod read (get, list, watch), ConfigMap reads and individual-object create/update/patch/delete (no deletecollection)
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

<span id="_2-create-a-serviceaccount-with-a-custom-token-expiration-time"></span>

### 2. Create a ServiceAccount and a Pod with a projected token requesting a custom lifetime.

<details>
<summary>Show Answer</summary>

```yaml
# ServiceAccount definition
apiVersion: v1
kind: ServiceAccount
metadata:
  name: custom-sa
  namespace: default
automountServiceAccountToken: false
---
# Pod using projected token with custom expiration
apiVersion: v1
kind: Pod
metadata:
  name: app-with-custom-token
  namespace: default
spec:
  serviceAccountName: custom-sa
  automountServiceAccountToken: false
  containers:
  - name: app
    image: registry.k8s.io/pause:3.10
    volumeMounts:
    - name: token
      mountPath: /var/run/secrets/tokens
      readOnly: true
  volumes:
  - name: token
    projected:
      sources:
      - serviceAccountToken:
          path: token
          expirationSeconds: 3600  # requested, not guaranteed
          audience: https://service.example.com
```

**Explanation:**
The minimum requested `expirationSeconds` is 600; the server determines actual expiry. The example audience must be configured and validated by the receiving service; it is not automatically accepted by the Kubernetes API. For Kubernetes API calls, use an audience that API server accepts. Automatic mounting is disabled, and only the explicit token is mounted read-only. This pause Pod illustrates the volume; it neither uses the token nor serves HTTP. A real application must reload the file after kubelet rotates it.

</details>

### 3. Write a command to check what permissions a specific user has.

<details>
<summary>Show Answer</summary>

```bash
# Check if a user can perform a specific action
kubectl auth can-i create deployments --as=developer@example.com -n development

# Request the namespace rule list (see authorizer limitations below)
kubectl auth can-i --list --as=developer@example.com -n development

# Check permissions for a ServiceAccount
kubectl auth can-i get pods -n development \
  --as=system:serviceaccount:default:my-sa \
  --as-group=system:serviceaccounts \
  --as-group=system:serviceaccounts:default \
  --as-group=system:authenticated

# Impersonate a group
kubectl auth can-i create pods --as=developer@example.com --as-group=developers -n development
```

**Explanation:**
The caller needs `impersonate` permission for the user/ServiceAccount and each group used. Do not assume group membership is reconstructed automatically. `--list` is not always a complete effective-permission inventory and omits EKS access-policy permissions. EKS impersonation forces RBAC evaluation; separately test the actual IAM role. A positive `can-i` result does not guarantee admission, network access, or quota acceptance.

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
    pod-security.kubernetes.io/enforce-version: v1.35
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
  name: tenant-workload-editor
  namespace: tenant-alpha
rules:
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "list", "watch"]
- apiGroups: ["apps"]
  resources: ["deployments"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
- apiGroups: ["networking.k8s.io"]
  resources: ["networkpolicies"]
  verbs: ["get", "list"]  # Read-only for network policies
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: tenant-workload-editors
  namespace: tenant-alpha
subjects:
- kind: Group
  name: tenant-alpha:developers
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: tenant-workload-editor
  apiGroup: rbac.authorization.k8s.io
```

The pinned PSS version `v1.35` is a learning baseline; select and validate a policy version supported by the target cluster. Default deny also blocks DNS and external dependencies, so review explicit allowances. The CNI must enforce the policies. Tenants must not change namespace labels, NetworkPolicy, ResourceQuota, or RBAC, and other existing bindings need review.

**Deployment creation/editing can permit Pods to use other ServiceAccounts or Secrets in the namespace.** Removing Secret get permission alone does not close this path. Separate identities/secrets with different trust levels into different namespaces, constrain allowed identities through admission where needed, or use separate clusters. This example is not evidence of strong tenant isolation.

**Additional Security Measures:**

- Use separate ServiceAccounts per application
- Implement audit logging
- Use admission webhooks for policy enforcement
- Define sub-tenant ownership and policy propagation explicitly; ordinary Kubernetes namespaces are flat

</details>

### 2. Explain the complete authentication and authorization flow when a kubectl command is executed.

<details>
<summary>Show Answer</summary>

1. **Client**: kubectl reads the selected kubeconfig/context and validates the server's TLS certificate. The default file is `~/.kube/config`, but `--kubeconfig` and `KUBECONFIG` can change that. It obtains credentials from certificates, tokens, or an exec plugin; EKS IAM access commonly uses `aws eks get-token`.
2. **Authentication**: The API server verifies credentials to establish user/group identity. It uses the first successful authenticator result without guaranteeing a fixed evaluation order. OIDC, proxies, and webhooks have different verification and trust requirements.
3. **Authorization**: Configured authorizers run in order until the first Allow or Deny. NoOpinion continues; all NoOpinion results cause a 403 denial. RBAC adds permissions from applicable bindings and has no explicit deny rule. The `system:masters` bypass is a separate risk.
4. **Request handling**: Ordinary resource CREATE/UPDATE requests pass mutation and then validation admission; both can reject. Successful changes are stored after object validation, conflict checks, and other relevant checks. `get/list/watch` bypass admission. Dry-run, DELETE, CONNECT, and aggregated APIs cannot all be represented by the same etcd-write sequence.
5. **Response**: The API server returns a result or error. API success does not mean a controller has finished processing or an application is ready.

| Example request | Difference after authentication/authorization |
|---|---|
| `kubectl get pods` | Returns read results; does not run admission or store a new Pod |
| Pod CREATE | Passes mutation/validation admission and object checks before storage; scheduling follows |
| Server dry-run CREATE | Performs server validation including admission without persistent storage |

Authentication establishes identity, authorization permits API operations, and admission applies additional policy to changes.

</details>

## Official References

- [Authentication](https://kubernetes.io/docs/reference/access-authn-authz/authentication/)
- [Authorization](https://kubernetes.io/docs/reference/access-authn-authz/authorization/)
- [RBAC](https://kubernetes.io/docs/reference/access-authn-authz/rbac/)
- [ServiceAccount](https://kubernetes.io/docs/tasks/configure-pod-container/configure-service-account/)
- [Admission](https://kubernetes.io/docs/reference/access-authn-authz/admission-controllers/)
- [EKS access policies](https://docs.aws.amazon.com/eks/latest/userguide/access-policies.html)
