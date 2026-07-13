# Kubernetes Authentication and Authorization System

> **Supported Versions**: Kubernetes 1.31, 1.32, 1.33
> **最終更新**: February 19, 2026

## Overview

Kubernetes の Authentication（認証）と Authorization（認可）system は、cluster security の中核要素です。このドキュメントでは、Kubernetes の authentication と authorization の仕組みを詳しく取り上げ、実環境でそれらを設定する方法を説明します。

## Authentication

Authentication は、user または service が主張どおりの本人であることを検証する process です。Kubernetes は複数の authentication methods をサポートしており、これらは同時に有効化できます。

### Authentication Strategies

#### 1. X.509 Certificates

X.509 certificates は Kubernetes で最も一般的な authentication method です。Client certificates は、cluster の Certificate Authority (CA) によって署名されている必要があります。

**証明書生成例:**

```bash
# Generate private key
openssl genrsa -out john.key 2048

# Generate Certificate Signing Request (CSR)
openssl req -new -key john.key -out john.csr -subj "/CN=john/O=engineering"

# Sign CSR with Kubernetes CA
openssl x509 -req -in john.csr -CA ca.crt -CAkey ca.key -CAcreateserial -out john.crt -days 365
```

**kubeconfig 設定:**

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

Service accounts は、pods 内で実行される processes に identity を提供します。各 namespace には default service account があり、追加の service accounts を作成できます。

**Service Account 作成:**

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: my-service-account
  namespace: default
```

**Service Account の Pod への割り当て:**

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

OIDC は、external identity providers（例: Google、Azure AD、Okta）を通じた authentication をサポートします。

**API Server 設定例:**

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

Webhook token authentication は、external service を通じて tokens を検証します。

**API Server 設定:**

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

Authentication proxy は API server の前段に配置され、authentication を処理します。

**API Server 設定:**

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

Kubernetes では、users は次のように分類されます。

1. **Regular Users**: cluster の外部で管理されます。Kubernetes はこれらを直接管理しません。
2. **Service Accounts**: Kubernetes API によって管理される accounts です。

Users は 1 つ以上の groups に所属でき、groups は authorization policies で使用されます。

## Authorization

Authorization は、authenticated user が要求された action を実行する permission を持っているかどうかを検証する process です。Kubernetes は複数の authorization modules をサポートしています。

### Authorization Modes

#### 1. RBAC (Role-Based Access Control)

RBAC は role-based access control を提供し、現在 Kubernetes で最も広く使われている authorization mechanism です。

**主要な概念:**

1. **Role**: namespace 内の permissions を定義します。
2. **ClusterRole**: cluster-wide な permissions を定義します。
3. **RoleBinding**: Role を users、groups、または service accounts に bind します。
4. **ClusterRoleBinding**: ClusterRole を users、groups、または service accounts に bind します。

**Role 例:**

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

**RoleBinding 例:**

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

**ClusterRole 例:**

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

**ClusterRoleBinding 例:**

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

ABAC は attribute-based access control を提供します。Policies は JSON files で定義されます。

**Policy 例:**

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

Node authorization は、kubelets が API server にアクセスするときに使用されます。

#### 4. Webhook Authorization

Webhook authorization は、external service を通じて authorization decisions を行います。

**API Server 設定:**

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

1. **Principle of Least Privilege**: 必要最小限の permissions のみを付与します。
2. **Role Separation**: administrators、developers、operators などの roles に基づいて適切な permissions を付与します。
3. **Namespace Separation**: team または project ごとに namespaces を分離し、適切な permissions を付与します。
4. **Service Account Separation**: 各 application に個別の service account を使用します。
5. **Regular Auditing**: authorization policies を定期的に review し、update します。

## Admission Control

Admission control は、authentication と authorization の後、requests を処理する前に追加の validation と modification を実行します。

### Admission Controller Types

1. **Mutating Admission Controllers**: requests を変更できます。
2. **Validating Admission Controllers**: modification なしで requests の validation のみを行います。

### Key Admission Controllers

1. **LimitRanger**: pods と containers の resource limits を設定します。
2. **ResourceQuota**: namespace ごとの resource usage を制限します。
3. **PodSecurityPolicy**: pod security contexts を制限します。
4. **ServiceAccount**: service accounts を pods に自動的に割り当てます。
5. **DefaultStorageClass**: default storage class を設定します。

### Dynamic Admission Control

Dynamic admission control は webhooks を通じて実装されます。

1. **MutatingAdmissionWebhook**: requests を変更できます。
2. **ValidatingAdmissionWebhook**: modification なしで requests の validation のみを行います。

**Webhook 設定例:**

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

Amazon EKS は AWS IAM と Kubernetes RBAC を統合し、authentication と authorization を提供します。

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

Multi-tenant environments では、tenants 間の isolation が重要です。

**Namespace 分離:**

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

1. **Regular Certificate Rotation**: certificates を定期的に更新します。
2. **Disable Service Account Token Auto-mount**: 不要な場合は automatic service account token mounting を無効化します。
3. **Minimize RBAC Policies**: 必要最小限の permissions のみを付与します。
4. **Implement Network Policies**: pods 間の communication を制限します。
5. **Enable Audit Logging**: すべての API requests を log に記録し、monitoring します。
6. **Configure Security Contexts**: pods と containers の security contexts を適切に設定します。
7. **Image Scanning**: container images の vulnerabilities を定期的に scan します。

## Conclusion

Kubernetes の authentication と authorization system は、cluster security の中核要素です。適切な authentication methods を選択し、RBAC による fine-grained access control を実装し、admission controllers を使用して追加の security policies を適用することで、安全な Kubernetes environment を構築できます。

Authentication、authorization、admission control は相互に補完し合うものであり、Defense in Depth strategy を実装するために併用することが重要です。
