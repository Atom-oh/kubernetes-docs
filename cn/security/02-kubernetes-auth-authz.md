# Kubernetes 认证和授权系统

> **支持版本**: Kubernetes 1.31, 1.32, 1.33
> **最后更新**: February 19, 2026

## 概述

Kubernetes 的 Authentication（认证）和 Authorization（授权）系统是 cluster 安全的核心要素。本文档详细介绍 Kubernetes 认证和授权机制，并说明如何在实际环境中配置它们。

## 认证

认证是验证用户或 service 是否确实是其所声称身份的过程。Kubernetes 支持多种认证方法，并且这些方法可以同时启用。

### 认证策略

#### 1. X.509 Certificates

X.509 certificates 是 Kubernetes 中最常见的认证方法。Client certificates 必须由 cluster 的 Certificate Authority (CA) 签名。

**Certificate 生成示例：**

```bash
# Generate private key
openssl genrsa -out john.key 2048

# Generate Certificate Signing Request (CSR)
openssl req -new -key john.key -out john.csr -subj "/CN=john/O=engineering"

# Sign CSR with Kubernetes CA
openssl x509 -req -in john.csr -CA ca.crt -CAkey ca.key -CAcreateserial -out john.crt -days 365
```

**kubeconfig 配置：**

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

Service Account 为在 Pod 内运行的进程提供身份。每个 Namespace 都有一个默认的 Service Account，也可以创建其他 Service Account。

**Service Account 创建：**

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: my-service-account
  namespace: default
```

**将 Service Account 分配给 Pod：**

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

OIDC 支持通过外部身份提供商（例如 Google、Azure AD、Okta）进行认证。

**API Server 配置示例：**

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

Webhook token authentication 通过外部 service 验证 token。

**API Server 配置：**

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

Authentication proxy 位于 API server 前方，用于处理认证。

**API Server 配置：**

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

### 用户和组

在 Kubernetes 中，用户分类如下：

1. **Regular Users**: 在 cluster 外部管理；Kubernetes 不直接管理它们。
2. **Service Accounts**: 由 Kubernetes API 管理的账号。

用户可以属于一个或多个组，组会用于授权策略。

## 授权

授权是验证已认证用户是否有权限执行所请求操作的过程。Kubernetes 支持多种授权模块。

### 授权模式

#### 1. RBAC (Role-Based Access Control)

RBAC 提供基于 Role 的访问控制，目前是 Kubernetes 中使用最广泛的授权机制。

**关键概念：**

1. **Role**: 定义 Namespace 内的权限。
2. **ClusterRole**: 定义 cluster 级别的权限。
3. **RoleBinding**: 将 Role 绑定到用户、组或 Service Account。
4. **ClusterRoleBinding**: 将 ClusterRole 绑定到用户、组或 Service Account。

**Role 示例：**

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

**RoleBinding 示例：**

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

**ClusterRole 示例：**

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

**ClusterRoleBinding 示例：**

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

ABAC 提供基于属性的访问控制。Policy 在 JSON 文件中定义。

**Policy 示例：**

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

Node authorization 在 kubelet 访问 API server 时使用。

#### 4. Webhook Authorization

Webhook authorization 通过外部 service 做出授权决策。

**API Server 配置：**

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

### 授权最佳实践

1. **Principle of Least Privilege**: 仅授予最低必要权限。
2. **Role Separation**: 根据管理员、开发人员和操作人员等角色授予适当权限。
3. **Namespace Separation**: 按团队或项目分隔 Namespace，并授予适当权限。
4. **Service Account Separation**: 为每个应用程序使用单独的 Service Account。
5. **Regular Auditing**: 定期审查和更新授权策略。

## Admission Control

Admission control 在认证和授权之后、处理请求之前执行额外的验证和修改。

### Admission Controller 类型

1. **Mutating Admission Controllers**: 可以修改请求。
2. **Validating Admission Controllers**: 仅验证请求，不进行修改。

### 关键 Admission Controllers

1. **LimitRanger**: 为 Pod 和 container 设置资源限制。
2. **ResourceQuota**: 限制每个 Namespace 的资源使用量。
3. **PodSecurityPolicy**: 限制 Pod 安全上下文。
4. **ServiceAccount**: 自动将 Service Account 分配给 Pod。
5. **DefaultStorageClass**: 设置默认 StorageClass。

### Dynamic Admission Control

Dynamic admission control 通过 webhook 实现：

1. **MutatingAdmissionWebhook**: 可以修改请求。
2. **ValidatingAdmissionWebhook**: 仅验证请求，不进行修改。

**Webhook 配置示例：**

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

## 实践实施示例

### EKS 中的认证和授权配置

#### IAM 和 RBAC 集成

Amazon EKS 将 AWS IAM 与 Kubernetes RBAC 集成，以提供认证和授权。

**aws-auth ConfigMap：**

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

#### OIDC Provider 配置

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

在 multi-tenant 环境中，tenant 之间的隔离很重要。

**Namespace 隔离：**

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

**Resource Quotas：**

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

## 安全最佳实践

1. **Regular Certificate Rotation**: 定期更新 certificates。
2. **Disable Service Account Token Auto-mount**: 在不需要时禁用 Service Account token 自动挂载。
3. **Minimize RBAC Policies**: 仅授予最低必要权限。
4. **Implement Network Policies**: 限制 Pod 之间的通信。
5. **Enable Audit Logging**: 记录并监控所有 API 请求。
6. **Configure Security Contexts**: 为 Pod 和 container 正确配置 security contexts。
7. **Image Scanning**: 定期扫描 container images 以发现漏洞。

## 结论

Kubernetes 的认证和授权系统是 cluster 安全的核心要素。通过选择适当的认证方法、使用 RBAC 实现细粒度访问控制，并通过 admission controllers 应用额外的安全策略，你可以构建安全的 Kubernetes 环境。

Authentication、authorization 和 admission control 相互补充，重要的是将它们结合使用，以实施 Defense in Depth 策略。
