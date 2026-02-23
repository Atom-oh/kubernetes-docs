# Kubernetes Authentication and Authorization System

> **Supported Versions**: Kubernetes 1.31, 1.32, 1.33
> **Last Updated**: February 19, 2026

## Overview

Kubernetes' Authentication and Authorization system is a core element of cluster security. This document provides a detailed look at Kubernetes authentication and authorization mechanisms and explains how to configure them in real-world environments.

## Authentication

Authentication is the process of verifying that a user or service is who they claim to be. Kubernetes supports multiple authentication methods, and these can be enabled simultaneously.

### Authentication Strategies

#### 1. X.509 Certificates

X.509 certificates are the most common authentication method in Kubernetes. Client certificates must be signed by the cluster's Certificate Authority (CA).

**Certificate Generation Example:**

```bash
# Generate private key
openssl genrsa -out john.key 2048

# Generate Certificate Signing Request (CSR)
openssl req -new -key john.key -out john.csr -subj "/CN=john/O=engineering"

# Sign CSR with Kubernetes CA
openssl x509 -req -in john.csr -CA ca.crt -CAkey ca.key -CAcreateserial -out john.crt -days 365
```

**kubeconfig Configuration:**

```yaml
apiVersion: v1
kind: Config
clusters:
- name: my-cluster
  cluster:
    certificate-authority-data: <BASE64_ENCODED_CA_CERT>
    server: https://kubernetes.example.com
users:
- name: john
  user:
    client-certificate-data: <BASE64_ENCODED_CLIENT_CERT>
    client-key-data: <BASE64_ENCODED_CLIENT_KEY>
contexts:
- name: john@my-cluster
  context:
    cluster: my-cluster
    user: john
current-context: john@my-cluster
```

#### 2. Service Account Tokens

Service accounts provide identity for processes running inside pods. Each namespace has a default service account, and additional service accounts can be created.

**Service Account Creation:**

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: my-service-account
  namespace: default
```

**Assigning Service Account to Pod:**

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: my-pod
spec:
  serviceAccountName: my-service-account
  containers:
  - name: my-container
    image: nginx
```

#### 3. OpenID Connect (OIDC)

OIDC supports authentication through external identity providers (e.g., Google, Azure AD, Okta).

**API Server Configuration Example:**

```yaml
apiVersion: v1
kind: Config
clusters:
- name: my-cluster
  cluster:
    server: https://kubernetes.example.com
    certificate-authority-data: <BASE64_ENCODED_CA_CERT>
users:
- name: oidc-user
  user:
    auth-provider:
      name: oidc
      config:
        client-id: <CLIENT_ID>
        client-secret: <CLIENT_SECRET>
        id-token: <ID_TOKEN>
        refresh-token: <REFRESH_TOKEN>
        idp-issuer-url: https://accounts.google.com
contexts:
- name: oidc-context
  context:
    cluster: my-cluster
    user: oidc-user
current-context: oidc-context
```

#### 4. Webhook Token Authentication

Webhook token authentication validates tokens through an external service.

**API Server Configuration:**

```yaml
apiVersion: v1
kind: Config
# ...
authentication:
  webhook:
    config:
      url: https://authn.example.com/authenticate
      caCert: <BASE64_ENCODED_CA_CERT>
```

#### 5. Authentication Proxy

An authentication proxy sits in front of the API server to handle authentication.

**API Server Configuration:**

```yaml
apiVersion: v1
kind: Config
# ...
authentication:
  proxy:
    headerName: X-Remote-User
    usernameHeaders: ["X-Remote-User"]
    groupHeaders: ["X-Remote-Group"]
```

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
2. **ClusterRole**: Defines cluster-wide permissions.
3. **RoleBinding**: Binds a Role to users, groups, or service accounts.
4. **ClusterRoleBinding**: Binds a ClusterRole to users, groups, or service accounts.

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
  name: secret-reader
rules:
- apiGroups: [""]
  resources: ["secrets"]
  verbs: ["get", "watch", "list"]
```

**ClusterRoleBinding Example:**

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: read-secrets-global
subjects:
- kind: Group
  name: security-team
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: ClusterRole
  name: secret-reader
  apiGroup: rbac.authorization.k8s.io
```

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
    "resource": "pods",
    "readonly": true
  }
}
```

#### 3. Node Authorization

Node authorization is used when kubelets access the API server.

#### 4. Webhook Authorization

Webhook authorization makes authorization decisions through an external service.

**API Server Configuration:**

```yaml
apiVersion: v1
kind: Config
# ...
authorization:
  webhook:
    config:
      url: https://authz.example.com/authorize
      caCert: <BASE64_ENCODED_CA_CERT>
```

### Authorization Best Practices

1. **Principle of Least Privilege**: Grant only the minimum necessary permissions.
2. **Role Separation**: Grant appropriate permissions based on roles such as administrators, developers, and operators.
3. **Namespace Separation**: Separate namespaces by team or project and grant appropriate permissions.
4. **Service Account Separation**: Use separate service accounts for each application.
5. **Regular Auditing**: Regularly review and update authorization policies.

## Admission Control

Admission control performs additional validation and modification before processing requests after authentication and authorization.

### Admission Controller Types

1. **Mutating Admission Controllers**: Can modify requests.
2. **Validating Admission Controllers**: Only validate requests without modification.

### Key Admission Controllers

1. **LimitRanger**: Sets resource limits for pods and containers.
2. **ResourceQuota**: Limits resource usage per namespace.
3. **PodSecurityPolicy**: Restricts pod security contexts.
4. **ServiceAccount**: Automatically assigns service accounts to pods.
5. **DefaultStorageClass**: Sets the default storage class.

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
  admissionReviewVersions: ["v1"]
  sideEffects: None
  timeoutSeconds: 5
```

## Practical Implementation Examples

### Authentication and Authorization Configuration in EKS

#### IAM and RBAC Integration

Amazon EKS integrates AWS IAM with Kubernetes RBAC to provide authentication and authorization.

**aws-auth ConfigMap:**

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: aws-auth
  namespace: kube-system
data:
  mapRoles: |
    - rolearn: arn:aws:iam::123456789012:role/EKSAdminRole
      username: admin
      groups:
        - system:masters
    - rolearn: arn:aws:iam::123456789012:role/EKSDeveloperRole
      username: developer
      groups:
        - developers
  mapUsers: |
    - userarn: arn:aws:iam::123456789012:user/john
      username: john
      groups:
        - developers
```

#### OIDC Provider Configuration

```bash
# Create OIDC provider
eksctl utils associate-iam-oidc-provider \
    --cluster my-cluster \
    --approve

# Create IAM role and associate with service account
eksctl create iamserviceaccount \
    --name my-service-account \
    --namespace default \
    --cluster my-cluster \
    --attach-policy-arn arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess \
    --approve
```

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
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          tenant: a
```

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
5. **Enable Audit Logging**: Log and monitor all API requests.
6. **Configure Security Contexts**: Properly configure security contexts for pods and containers.
7. **Image Scanning**: Regularly scan container images for vulnerabilities.

## Conclusion

Kubernetes' authentication and authorization system is a core element of cluster security. By selecting appropriate authentication methods, implementing fine-grained access control through RBAC, and applying additional security policies using admission controllers, you can build a secure Kubernetes environment.

Authentication, authorization, and admission control complement each other, and it is important to use them together to implement a Defense in Depth strategy.
