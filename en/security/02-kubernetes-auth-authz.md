# Kubernetes Authentication and Authorization System

> **Scope**: Kubernetes stable APIs and Amazon EKS user access management
> **Last Updated**: September 13, 2026

## Overview

Authentication establishes the request identity, authorization decides which API operations that identity may perform, and admission applies additional policy to authorized changes. The manifests below are independent learning examples; prepare the namespaces, administrator permissions, certificates, and webhook servers first. No live cluster/API calls or EKS access changes were tested.

The `kube-apiserver` flag examples apply to a **self-managed control plane**. Use the managed access settings for EKS; these examples are not instructions to configure its API server flags or obtain its CA private key.

## Authentication

Authentication is the process of verifying that a user or service is who they claim to be. Kubernetes supports multiple authentication methods, and these can be enabled simultaneously.

With multiple authenticators, the first successful result is used, but their evaluation order is not guaranteed. Invalid credentials can fail authentication. Handling of requests without credentials depends on anonymous-authentication settings, and an anonymous identity still needs authorization.

### Authentication Strategies

#### 1. X.509 Certificates

Use a certificate signed by a **client CA** trusted through the API server's `--client-ca-file`. The subject CN supplies the username and O supplies groups; the certificate needs the client-authentication (`clientAuth`) usage. The CA used to verify the server's TLS certificate serves a different purpose from the CA that authenticates clients.

**Local private-key and CSR example:**

```bash
umask 077
auth_lab_dir=$(mktemp -d)
openssl genrsa -out "$auth_lab_dir/john.key" 2048
openssl req -new -key "$auth_lab_dir/john.key" \
  -out "$auth_lab_dir/john.csr" -subj '/CN=john/O=engineering'
openssl req -in "$auth_lab_dir/john.csr" -noout -verify
```

These commands do not issue a certificate. Send **only the CSR** to an approved issuer, which must review identity, groups, usage, and lifetime. Do not copy the CA private key to users or approve organization names without review. The EKS `beta.eks.amazonaws.com/app-serving` signer is for serving certificates and does not support user client-certificate signing. Use the IAM/OIDC paths below for EKS user access.

**kubeconfig after issuance:**

```yaml
apiVersion: v1
kind: Config
clusters:
- name: my-cluster
  cluster:
    certificate-authority: /secure/path/server-ca.crt
    server: https://kubernetes.example.com
users:
- name: john
  user:
    client-certificate: /secure/path/john.crt
    client-key: /secure/path/john.key
contexts:
- name: john@my-cluster
  context:
    cluster: my-cluster
    user: john
    namespace: default
current-context: john@my-cluster
```

Replace the paths with the issued files and restrict access to the private key and kubeconfig. Base64 in `*-data` fields is not encryption. Inspect untrusted kubeconfig files before use: they can execute commands through credential plugins.

#### 2. Service Account Tokens

A ServiceAccount is a namespaced workload identity. Every namespace has a `default` account; a Pod's `serviceAccountName` refers to an account in that same namespace. Selecting an account does not by itself grant access to application resources.

This example does not call the API and disables automatic token mounting. Its example image does not provide a network service.

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: my-service-account
  namespace: default
automountServiceAccountToken: false
---
apiVersion: v1
kind: Pod
metadata:
  name: my-pod
  namespace: default
spec:
  serviceAccountName: my-service-account
  automountServiceAccountToken: false
  containers:
  - name: my-container
    image: registry.k8s.io/pause:3.10
```

`automountServiceAccountToken` is a top-level ServiceAccount field and a Pod `spec` field. The Pod setting takes precedence. It controls the default mount; it does not prevent an explicitly declared `serviceAccountToken` projected volume.

For Pods that need API access, kubelet obtains and rotates default projected tokens through TokenRequest. The default token file is `/var/run/secrets/kubernetes.io/serviceaccount/token`. Applications must reload the rotated file. Expiry and audience binding reduce exposure but do not make a bearer token safe to disclose. Do not assume that creating an account automatically creates a long-lived Secret token. The [quiz's projected-volume example](../quizzes/security/02-kubernetes-auth-authz-quiz.md) covers a custom audience and requested lifetime.

#### 3. OpenID Connect (OIDC)

OIDC lets the API server validate **ID tokens** from an external identity provider. Configure issuer, audience, signature/expiry validation, and identity mapping. The API server does not provide an interactive login or issue refresh tokens. Clients use a reviewed tool or `exec` credential plugin for their identity provider.

These are **additional flags for a self-managed API server**, not a complete startup command or a kubeconfig. Replace the example HTTPS issuer and client ID.

```text
--oidc-issuer-url=https://idp.example.com
--oidc-client-id=kubernetes
--oidc-username-claim=sub
--oidc-username-prefix=oidc:
--oidc-groups-claim=groups
--oidc-groups-prefix=oidc:
```

Prefix usernames and groups to avoid collisions with existing identities such as `system:` groups. Structured `AuthenticationConfiguration` is an alternative; do not combine `--authentication-config` with `--oidc-*` flags. Configure an external OIDC provider for EKS through the separate managed procedure below.

#### 4. Webhook Token Authentication

A self-managed API server sends an `authentication.k8s.io/v1` **TokenReview** to an external service. The following is a **separate kubeconfig used by the API server to reach that service**. It is not an `authentication.webhook` field in a user's kubeconfig.

```yaml
apiVersion: v1
kind: Config
clusters:
- name: authentication-service
  cluster:
    server: https://authn.example.com/authenticate
    certificate-authority: /etc/kubernetes/authn-webhook/ca.crt
users:
- name: kube-apiserver-webhook-client
  user:
    client-certificate: /etc/kubernetes/authn-webhook/client.crt
    client-key: /etc/kubernetes/authn-webhook/client.key
contexts:
- name: webhook
  context:
    cluster: authentication-service
    user: kube-apiserver-webhook-client
current-context: webhook
```

If installed at `/etc/kubernetes/authn-webhook.kubeconfig`, configure `--authentication-token-webhook-config-file=/etc/kubernetes/authn-webhook.kubeconfig` and `--authentication-token-webhook-version=v1` on the API server. Provision the referenced certificates and service separately. The service must validate the token and intended audience and return a TokenReview response. Design mutual TLS, credential protection, cache TTL, and failure behavior. This example provides neither a webhook implementation nor availability validation.

#### 5. Authentication Proxy

An authenticating proxy verifies the caller and forwards the resulting username and groups. Merely naming trusted headers does not establish trust. First authenticate the proxy's TLS identity using a dedicated front-proxy CA and an allowed client-certificate CN.

**Self-managed API server flag excerpt:**

```text
--requestheader-client-ca-file=/etc/kubernetes/front-proxy-ca.crt
--requestheader-allowed-names=front-proxy-client
--requestheader-username-headers=X-Remote-User
--requestheader-group-headers=X-Remote-Group
```

The proxy must strip caller-supplied identity headers and replace them with verified values. Do not reuse the ordinary user-client CA as the proxy CA or leave allowed CNs empty to trust every client certificate. This excerpt does not implement the proxy itself.

### Users and Groups

In Kubernetes, users are classified as follows:

1. **Regular Users**: Managed outside the cluster; Kubernetes does not manage them directly.
2. **Service Accounts**: Accounts managed by the Kubernetes API.

Users can belong to one or more groups, and groups are used in authorization policies.

## Authorization

Authorization is the process of verifying whether an authenticated user has permission to perform the requested action. Kubernetes supports multiple authorization modules.

### Authorization Modes

#### 1. RBAC (Role-Based Access Control)

RBAC provides role-based access control and is currently the most widely used authorization mechanism in Kubernetes.

**Key Concepts:**

1. **Role**: Defines permissions within a namespace.
2. **ClusterRole**: A cluster-scoped definition for cluster resources, non-resource URLs, or reusable permissions on namespaced resources.
3. **RoleBinding**: References a Role in the same namespace or a ClusterRole and grants permissions **only in the binding namespace**. A ServiceAccount subject can explicitly belong to another namespace.
4. **ClusterRoleBinding**: Grants a ClusterRole's permissions cluster-wide; it cannot reference a Role.

A role definition grants nothing without a binding. RBAC adds allowed permissions and has no explicit deny rules. Secret `get/list/watch` permits reading secret data, so these examples use Pod reads instead.

**Role Example:**

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: default
  name: pod-reader
rules:
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "watch", "list"]
```

**RoleBinding Example:**

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: read-pods
  namespace: default
subjects:
- kind: User
  name: john
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: pod-reader
  apiGroup: rbac.authorization.k8s.io
```

**ClusterRole Example:**

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: pod-reader-reusable
rules:
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "watch", "list"]
```

**ClusterRoleBinding Example:**

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: read-pods-global
subjects:
- kind: Group
  name: cluster-inventory-readers
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: ClusterRole
  name: pod-reader-reusable
  apiGroup: rbac.authorization.k8s.io
```

The ClusterRoleBinding illustrates an operations group that explicitly needs **Pod information across all namespaces**; it is not a default recommendation. For a single namespace, use a RoleBinding there with `roleRef.kind: ClusterRole` and `roleRef.name: pod-reader-reusable` instead.

#### 2. ABAC (Attribute-Based Access Control)

ABAC provides attribute-based access control. Policies are defined in JSON files.

**Policy Example:**

```json
{
  "apiVersion": "abac.authorization.kubernetes.io/v1beta1",
  "kind": "Policy",
  "spec": {
    "user": "john",
    "namespace": "default",
    "apiGroup": "",
    "resource": "pods",
    "readonly": true
  }
}
```

ABAC is included for understanding existing self-managed clusters. The policy consumed by `--authorization-policy-file` is a file with **one JSON object per line**, not a Kubernetes API resource. The indentation above is for explanation; serialize each policy onto one line in the actual file. Changes require restarting the API server. Prefer RBAC for new configurations; this flag is not an EKS configuration mechanism.

#### 3. Node Authorization

Node authorization is specific to kubelets. Their identity must belong to `system:nodes` and use the username `system:node:<nodeName>` matching the actual node name. This is not a workload access mechanism. On self-managed clusters, combine it with NodeRestriction admission to constrain kubelet changes to Node and Pod objects.

#### 4. Webhook Authorization

A self-managed API server sends an `authorization.k8s.io/v1` **SubjectAccessReview** to an external service. Use the same connection-file format as the authentication webhook above, with a separate authorization endpoint, CA, and client certificate. Configure `--authorization-webhook-config-file` and `--authorization-webhook-version=v1`, or use structured `AuthorizationConfiguration` to configure the chain and failure policy. There is no `authorization.webhook` field in a user kubeconfig.

Authorizers run in configured order; the first **Allow or Deny** decides. `NoOpinion` continues to the next authorizer; all NoOpinion results deny access. A later webhook cannot veto a request RBAC has already allowed. `system:masters` is a special group that bypasses RBAC and webhook authorization; do not assign it to ordinary administrators or assume removing a role binding revokes its access.

### Authorization Best Practices

1. **Principle of Least Privilege**: Grant only the minimum necessary permissions.
2. **Role Separation**: Grant appropriate permissions based on roles such as administrators, developers, and operators.
3. **Namespace Separation**: Separate namespaces by team or project and grant appropriate permissions.
4. **Service Account Separation**: Use separate service accounts for each application.
5. **Regular Auditing**: Regularly review and update authorization policies.

## Admission Control

Admission control performs additional validation and modification before processing requests after authentication and authorization.

Admission handles creation, changes, deletion, and some connection requests; **get/list/watch reads bypass admission**. Mutation precedes validation, and either phase can reject a request.

### Admission Controller Types

1. **Mutating Admission Controllers**: Can modify requests.
2. **Validating Admission Controllers**: Only validate requests without modification.

### Key Admission Controllers

1. **LimitRanger**: Applies defaults and minimum/maximum constraints defined by LimitRange.
2. **ResourceQuota**: Checks configured namespace quotas for object counts, resource requests, and similar quantities; it is not a cap on measured CPU/memory consumption or spending.
3. **PodSecurity**: Applies Pod Security Standards according to namespace labels. The older PodSecurityPolicy was removed in Kubernetes 1.25.
4. **ServiceAccount**: Automatically assigns service accounts to pods.
5. **DefaultStorageClass**: Selects a default StorageClass for a PVC without a specified class; it does not create the StorageClass.

### Dynamic Admission Control

Dynamic admission control is implemented through webhooks:

1. **MutatingAdmissionWebhook**: Can modify requests.
2. **ValidatingAdmissionWebhook**: Only validates requests without modification.

**Webhook Configuration Example:**

```yaml
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingWebhookConfiguration
metadata:
  name: pod-policy-webhook
webhooks:
- name: pod-policy.example.com
  clientConfig:
    url: https://pod-policy.example.com/validate
    caBundle: <BASE64_ENCODED_CA_CERT>
  rules:
  - apiGroups: [""]
    apiVersions: ["v1"]
    resources: ["pods"]
    operations: ["CREATE", "UPDATE"]
    scope: "Namespaced"
  namespaceSelector:
    matchLabels:
      training.example.com/pod-policy: "enabled"
  failurePolicy: Fail
  matchPolicy: Equivalent
  admissionReviewVersions: ["v1"]
  sideEffects: None
  timeoutSeconds: 5
```

This webhook targets only explicitly labeled namespaces. Do not install it without the actual HTTPS service, CA, and an AdmissionReview implementation that preserves the request UID. `failurePolicy: Fail` blocks matching requests on call errors/timeouts. `Ignore` ignores call failures; it does not turn a successfully returned denial into an allow. Test availability and recovery in a dedicated namespace. CEL ValidatingAdmissionPolicy is another option for validation.

## Practical Implementation Examples

### Authentication and Authorization Configuration in EKS

#### IAM and RBAC Integration

Use **access entries** for current EKS IAM user access. An IAM role supplies the authenticated identity; associated EKS access policies or Kubernetes RBAC grant Kubernetes permissions. Allowed permissions from both paths accumulate. An EKS access policy is not an IAM policy.

The following is an administrator's change example for an existing cluster and IAM role. First confirm the account, Region, cluster, `API` or `API_AND_CONFIG_MAP` mode, an existing `development` namespace, absence of a duplicate access entry, and permissions for `eks:CreateAccessEntry` and the RBAC changes. This is not an infrastructure creation script or a complete migration procedure.

```bash
# Example inputs: replace with the approved cluster and existing IAM role.
region=ap-northeast-2
cluster_name=my-cluster
principal_arn=arn:aws:iam::123456789012:role/EKSDeveloperRole
aws eks describe-cluster --region "$region" --name "$cluster_name" \
  --query 'cluster.accessConfig.authenticationMode' --output text

# Mutates access configuration; run only after the prerequisites above.
aws eks create-access-entry --region "$region" --cluster-name "$cluster_name" \
  --principal-arn "$principal_arn" --type STANDARD \
  --kubernetes-groups eks:developers
```

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: developer-pod-reader
  namespace: development
rules:
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: eks-developer-pod-reader
  namespace: development
subjects:
- kind: Group
  name: eks:developers
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: developer-pod-reader
  apiGroup: rbac.authorization.k8s.io
```

After applying the RBAC objects, verify access with the role's actual credentials. This example associates no access policy, and creating an access entry does not create RBAC objects. Existing bindings or policies can make effective permissions broader than these Pod reads. Allow for propagation delay.

The `aws-auth` ConfigMap is the legacy mechanism. Replacing the whole ConfigMap can remove node/Fargate mappings. Plan migration from `CONFIG_MAP` to `API_AND_CONFIG_MAP`, migrate and verify mappings, and then use `API`. Once enabled, API access cannot be removed by reverting modes; `API` cannot return to a ConfigMap mode. While using both, an access entry takes precedence for the same IAM principal. Not all existing mappings migrate automatically.

`kubectl auth can-i --list` does not display permissions from EKS access policies. Impersonation with `--as`/`--as-group` forces Kubernetes RBAC evaluation and therefore does not test the IAM role's access-policy permissions. Verify individual actions as the real role, including expected denials outside the namespace and for Secret reads.

#### OIDC Provider Configuration

These three paths have different directions and purposes.

| Path | Authentication target and configuration |
|---|---|
| External OIDC user → Kubernetes API | Associate the external IdP through EKS `AssociateIdentityProviderConfig`, then bind its users/groups to RBAC. EKS must reach the issuer over public HTTPS; self-signed issuer certificates are unsupported. This does not disable IAM authentication. |
| Pod → AWS API through IRSA | Establish IAM trust in the cluster's ServiceAccount OIDC issuer, restrict role trust to the intended namespace/ServiceAccount, and grant only the required AWS resources. `eksctl utils associate-iam-oidc-provider` serves this path, not external user login. |
| Pod → AWS API through EKS Pod Identity | Use the Pod Identity Agent and a role association on supported execution environments. This differs from IRSA's IAM OIDC provider setup. |

Neither workload mechanism grants Kubernetes API RBAC by itself. Avoid using an account-wide S3 read managed policy as the default example; scope permissions to the actual bucket/object ARNs. Follow [EKS external OIDC](https://docs.aws.amazon.com/eks/latest/userguide/authenticate-oidc-identity-provider.html) and [workload IAM roles](https://docs.aws.amazon.com/eks/latest/userguide/service-accounts.html) for configuration details.

### Multi-tenant Cluster Security

In multi-tenant environments, isolation between tenants is important.

**Namespace Isolation:**

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: tenant-a
  labels:
    tenant: a
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: deny-from-other-namespaces
  namespace: tenant-a
spec:
  podSelector: {}
  policyTypes: [Ingress]
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          tenant: a
```

This policy allows ingress from **every** namespace labeled `tenant: a`. Other ingress policies can add allowances, and egress is unrestricted. It requires CNI NetworkPolicy enforcement; only trusted administrators should control namespace labels and policies. A namespace alone does not guarantee strong isolation between hostile tenants. The quiz includes default deny in both directions; review separate allowances for DNS and necessary traffic.

**Resource Quotas:**

```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: tenant-a-quota
  namespace: tenant-a
spec:
  hard:
    pods: "10"
    requests.cpu: "4"
    requests.memory: 8Gi
    limits.cpu: "8"
    limits.memory: 16Gi
```

## Security Best Practices

1. **Regular Certificate Rotation**: Renew certificates regularly.
2. **Disable Service Account Token Auto-mount**: Disable automatic service account token mounting when not needed.
3. **Minimize RBAC Policies**: Grant only the minimum necessary permissions.
4. **Implement Network Policies**: Restrict communication between pods.
5. **Enable Audit Logging**: Verify audit-policy coverage, sensitive-data exclusions, retention, and log access. On EKS enable the `audit` control-plane log type and verify CloudWatch delivery; do not assume every request body is recorded.
6. **Configure Security Contexts**: Properly configure security contexts for pods and containers.
7. **Image Scanning**: Regularly scan container images for vulnerabilities.

## Conclusion

Kubernetes' authentication and authorization system is a core element of cluster security. By selecting appropriate authentication methods, implementing fine-grained access control through RBAC, and applying additional security policies using admission controllers, you can build a secure Kubernetes environment.

Authentication, authorization, and admission control complement each other, and it is important to use them together to implement a Defense in Depth strategy.

## Official References

- [Kubernetes authentication](https://kubernetes.io/docs/reference/access-authn-authz/authentication/)
- [Kubernetes authorization](https://kubernetes.io/docs/reference/access-authn-authz/authorization/)
- [RBAC](https://kubernetes.io/docs/reference/access-authn-authz/rbac/)
- [ServiceAccount configuration](https://kubernetes.io/docs/tasks/configure-pod-container/configure-service-account/)
- [ABAC](https://kubernetes.io/docs/reference/access-authn-authz/abac/)
- [Node authorization](https://kubernetes.io/docs/reference/access-authn-authz/node/)
- [Admission controllers](https://kubernetes.io/docs/reference/access-authn-authz/admission-controllers/)
- [Admission webhooks](https://kubernetes.io/docs/reference/access-authn-authz/extensible-admission-controllers/)
- [NetworkPolicy](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- [EKS certificate signing](https://docs.aws.amazon.com/eks/latest/userguide/cert-signing.html)
- [EKS access entries](https://docs.aws.amazon.com/eks/latest/userguide/creating-access-entries.html)
- [EKS authentication modes](https://docs.aws.amazon.com/eks/latest/userguide/setting-up-access-entries.html)
- [EKS access policy evaluation](https://docs.aws.amazon.com/eks/latest/userguide/access-policies.html)
- [EKS audit logs](https://docs.aws.amazon.com/eks/latest/userguide/control-plane-logs.html)
- [Trusted kubeconfig](https://kubernetes.io/docs/concepts/configuration/organize-cluster-access-kubeconfig/)
