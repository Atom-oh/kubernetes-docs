# Kubernetes 身份验证和授权系统

> **范围**：Kubernetes stable APIs 和 Amazon EKS 用户访问管理
> **最后更新**：September 13, 2026

## 概述

身份验证用于确定请求身份，授权决定该身份可以执行哪些 API 操作，而准入则对已获授权的变更应用额外策略。以下 manifests 是相互独立的学习示例；请先准备 namespaces、管理员权限、证书和 webhook servers。未测试任何实时 cluster/API 调用或 EKS 访问变更。

`kube-apiserver` flag 示例适用于**自管理 control plane**。对于 EKS，请使用托管访问设置；这些示例并非配置其 API server flags 或获取其 CA private key 的说明。

## 身份验证

身份验证是验证用户或服务是否为其所声称身份的过程。Kubernetes 支持多种身份验证方法，并且可以同时启用这些方法。

使用多个 authenticator 时，将使用第一个成功的结果，但不保证其评估顺序。无效凭证可能导致身份验证失败。对没有凭证的请求如何处理取决于匿名身份验证设置，并且匿名身份仍然需要授权。

### 身份验证策略

#### 1. X.509 证书

使用由 API server 的 `--client-ca-file` 所信任的**客户端 CA**签名的证书。subject CN 提供用户名，O 提供 groups；该证书需要客户端身份验证（`clientAuth`）用途。用于验证 server TLS certificate 的 CA 与用于验证客户端身份的 CA 用途不同。

**本地 private-key 和 CSR 示例：**

```bash
umask 077
auth_lab_dir=$(mktemp -d)
openssl genrsa -out "$auth_lab_dir/john.key" 2048
openssl req -new -key "$auth_lab_dir/john.key" \
  -out "$auth_lab_dir/john.csr" -subj '/CN=john/O=engineering'
openssl req -in "$auth_lab_dir/john.csr" -noout -verify
```

这些命令不会签发证书。仅将 **CSR** 发送给经批准的签发者，签发者必须审查身份、groups、用途和有效期。请勿将 CA private key 复制给用户，也不要在未经审查的情况下批准组织名称。EKS `beta.eks.amazonaws.com/app-serving` signer 用于服务证书，且不支持用户 client-certificate 签名。对于 EKS 用户访问，请使用下面的 IAM/OIDC 路径。

**签发后的 kubeconfig：**

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

请将路径替换为签发的文件，并限制对 private key 和 kubeconfig 的访问。`*-data` fields 中的 Base64 不是加密。使用前请检查不受信任的 kubeconfig 文件：它们可能通过 credential plugins 执行命令。

#### 2. Service Account Tokens

ServiceAccount 是一种有 namespace 范围的 workload identity。每个 namespace 都有一个 `default` account；Pod 的 `serviceAccountName` 指向同一 namespace 中的 account。选择 account 本身并不会授予对应用资源的访问权限。

此示例不会调用 API，并禁用了自动 token 挂载。其示例 image 不提供网络服务。

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

`automountServiceAccountToken` 是顶层 ServiceAccount field 和 Pod `spec` field。Pod 设置优先。它控制默认挂载；不会阻止显式声明的 `serviceAccountToken` projected volume。

对于需要 API 访问的 Pods，kubelet 通过 TokenRequest 获取并轮换默认 projected tokens。默认 token 文件为 `/var/run/secrets/kubernetes.io/serviceaccount/token`。应用程序必须重新加载轮换后的文件。过期时间和 audience 绑定可降低暴露风险，但不会使 bearer token 可安全公开。不要假设创建 account 会自动创建长期 Secret token。[测验中的 projected-volume 示例](../quizzes/security/02-kubernetes-auth-authz-quiz.md)涵盖自定义 audience 和请求的有效期。

#### 3. OpenID Connect (OIDC)

OIDC 让 API server 验证来自外部 identity provider 的 **ID tokens**。配置 issuer、audience、signature/expiry 验证和 identity mapping。API server 不提供交互式登录，也不签发 refresh tokens。客户端应为其 identity provider 使用经过审查的工具或 `exec` credential plugin。

这些是**自管理 API server 的附加 flags**，并非完整启动命令或 kubeconfig。请替换示例 HTTPS issuer 和 client ID。

```text
--oidc-issuer-url=https://idp.example.com
--oidc-client-id=kubernetes
--oidc-username-claim=sub
--oidc-username-prefix=oidc:
--oidc-groups-claim=groups
--oidc-groups-prefix=oidc:
```

为用户名和 groups 添加 prefix，以避免与现有 identities（例如 `system:` groups）冲突。结构化 `AuthenticationConfiguration` 是一种替代方案；不要将 `--authentication-config` 与 `--oidc-*` flags 组合使用。对于 EKS，请通过下文单独的托管流程配置外部 OIDC provider。

#### 4. Webhook Token 身份验证

自管理 API server 会将 `authentication.k8s.io/v1` **TokenReview** 发送到外部服务。以下是**由 API server 用于访问该服务的独立 kubeconfig**。它不是用户 kubeconfig 中的 `authentication.webhook` field。

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

如果安装在 `/etc/kubernetes/authn-webhook.kubeconfig`，请在 API server 上配置 `--authentication-token-webhook-config-file=/etc/kubernetes/authn-webhook.kubeconfig` 和 `--authentication-token-webhook-version=v1`。单独预配所引用的证书和服务。该服务必须验证 token 和预期 audience，并返回 TokenReview response。请设计 mutual TLS、凭证保护、cache TTL 和失败行为。此示例既不提供 webhook implementation，也不提供可用性验证。

#### 5. Authentication Proxy

authentication proxy 验证调用方，并转发得到的用户名和 groups。仅仅指定可信 headers 并不能建立信任。首先使用专用 front-proxy CA 和允许的 client-certificate CN 对 proxy 的 TLS identity 进行身份验证。

**自管理 API server flag 摘录：**

```text
--requestheader-client-ca-file=/etc/kubernetes/front-proxy-ca.crt
--requestheader-allowed-names=front-proxy-client
--requestheader-username-headers=X-Remote-User
--requestheader-group-headers=X-Remote-Group
```

proxy 必须移除调用方提供的 identity headers，并将其替换为已验证的值。不要将普通 user-client CA 复用于 proxy CA，也不要将允许的 CNs 留空而信任每个 client certificate。此摘录并未实现 proxy 本身。

### 用户和 Groups

在 Kubernetes 中，用户分类如下：

1. **普通用户**：在 cluster 外部管理；Kubernetes 不直接管理它们。
2. **Service Accounts**：由 Kubernetes API 管理的 accounts。

用户可以属于一个或多个 groups，groups 用于授权策略。

## 授权

授权是验证已通过身份验证的用户是否有权执行所请求操作的过程。Kubernetes 支持多种授权 modules。

### 授权模式

#### 1. RBAC（Role-Based Access Control）

RBAC 提供基于角色的访问控制，目前是 Kubernetes 中最广泛使用的授权机制。

**关键概念：**

1. **Role**：定义 namespace 内的权限。
2. **ClusterRole**：适用于 cluster resources、non-resource URLs 或 namespaced resources 可重用权限的 cluster-scoped 定义。
3. **RoleBinding**：引用同一 namespace 中的 Role 或一个 ClusterRole，并且**仅在 binding namespace 中**授予权限。ServiceAccount subject 可以显式属于另一个 namespace。
4. **ClusterRoleBinding**：在整个 cluster 中授予 ClusterRole 的权限；不能引用 Role。

没有 binding 的 role definition 不会授予任何权限。RBAC 会添加允许的权限，没有显式 deny rules。Secret 的 `get/list/watch` 允许读取 secret data，因此这些示例改用 Pod 读取权限。

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
  name: pod-reader-reusable
rules:
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "watch", "list"]
```

**ClusterRoleBinding 示例：**

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

该 ClusterRoleBinding 展示了一个明确需要**跨所有 namespaces 的 Pod 信息**的运维 group；它并非默认建议。对于单个 namespace，请改为在该处使用 RoleBinding，并使用 `roleRef.kind: ClusterRole` 和 `roleRef.name: pod-reader-reusable`。

#### 2. ABAC（Attribute-Based Access Control）

ABAC 提供基于属性的访问控制。策略在 JSON files 中定义。

**策略示例：**

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

包含 ABAC 是为了理解现有的自管理 clusters。由 `--authorization-policy-file` 使用的策略是一个**每行一个 JSON object**的文件，而非 Kubernetes API resource。上面的缩进用于说明；在实际文件中，请将每个 policy 序列化为一行。变更需要重启 API server。对于新配置，优先使用 RBAC；此 flag 不是 EKS 配置机制。

#### 3. Node 授权

Node authorization 专用于 kubelets。其 identity 必须属于 `system:nodes`，并使用与实际 node name 匹配的用户名 `system:node:<nodeName>`。这不是 workload access mechanism。在自管理 clusters 上，将其与 NodeRestriction admission 结合使用，以限制 kubelet 对 Node 和 Pod objects 的变更。

#### 4. Webhook 授权

自管理 API server 会将 `authorization.k8s.io/v1` **SubjectAccessReview** 发送到外部服务。请使用与上述 authentication webhook 相同的 connection-file 格式，但使用独立的 authorization endpoint、CA 和 client certificate。配置 `--authorization-webhook-config-file` 和 `--authorization-webhook-version=v1`，或使用结构化 `AuthorizationConfiguration` 配置 chain 和 failure policy。用户 kubeconfig 中不存在 `authorization.webhook` field。

authorizers 按配置顺序运行；第一个 **Allow 或 Deny** 决定结果。`NoOpinion` 会继续到下一个 authorizer；所有 NoOpinion 结果都会拒绝访问。后续 webhook 无法否决 RBAC 已允许的请求。`system:masters` 是一个绕过 RBAC 和 webhook authorization 的特殊 group；不要将其分配给普通 administrators，也不要认为移除 role binding 就会撤销其访问权限。

### 授权最佳实践

1. **最小权限原则**：仅授予最低限度的必要权限。
2. **角色分离**：根据 administrators、developers 和 operators 等角色授予适当权限。
3. **Namespace 分离**：按团队或项目分离 namespaces，并授予适当权限。
4. **Service Account 分离**：为每个应用使用独立的 service accounts。
5. **定期审计**：定期审查和更新授权策略。

## 准入控制

准入控制会在身份验证和授权之后、处理请求之前执行额外的验证和修改。

准入处理创建、变更、删除和某些连接请求；**get/list/watch 读取会绕过准入**。mutation 先于 validation，任一阶段都可以拒绝请求。

### 准入控制器类型

1. **Mutating Admission Controllers**：可以修改请求。
2. **Validating Admission Controllers**：只能验证请求，不能修改。

### 关键准入控制器

1. **LimitRanger**：应用由 LimitRange 定义的默认值和最小/最大约束。
2. **ResourceQuota**：检查为 object counts、resource requests 和类似数量配置的 namespace quotas；它不是对实际 CPU/memory 消耗或支出的上限。
3. **PodSecurity**：根据 namespace labels 应用 Pod Security Standards。旧版 PodSecurityPolicy 已在 Kubernetes 1.25 中移除。
4. **ServiceAccount**：自动为 pods 分配 service accounts。
5. **DefaultStorageClass**：为未指定 class 的 PVC 选择默认 StorageClass；它不会创建 StorageClass。

### Dynamic Admission Control

动态准入控制通过 webhooks 实现：

1. **MutatingAdmissionWebhook**：可以修改请求。
2. **ValidatingAdmissionWebhook**：只能验证请求，不能修改。

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
  namespaceSelector:
    matchLabels:
      training.example.com/pod-policy: "enabled"
  failurePolicy: Fail
  matchPolicy: Equivalent
  admissionReviewVersions: ["v1"]
  sideEffects: None
  timeoutSeconds: 5
```

此 webhook 仅以带有显式 labels 的 namespaces 为目标。没有实际 HTTPS service、CA 和会保留请求 UID 的 AdmissionReview implementation 时，请勿安装它。`failurePolicy: Fail` 会在调用错误/超时时阻止匹配的请求。`Ignore` 会忽略调用失败；它不会将成功返回的拒绝变为允许。请在专用 namespace 中测试可用性和恢复。CEL ValidatingAdmissionPolicy 是另一种验证选项。

## 实际实施示例

### EKS 中的身份验证和授权配置

#### IAM 和 RBAC 集成

对于当前的 EKS IAM 用户访问，请使用 **access entries**。IAM role 提供已通过身份验证的 identity；关联的 EKS access policies 或 Kubernetes RBAC 授予 Kubernetes permissions。来自两个路径的允许权限会累积。EKS access policy 不是 IAM policy。

以下是针对现有 cluster 和 IAM role 的管理员变更示例。请先确认 account、Region、cluster、`API` 或 `API_AND_CONFIG_MAP` mode、现有的 `development` namespace、没有重复的 access entry，以及拥有 `eks:CreateAccessEntry` 和 RBAC 变更权限。这不是 infrastructure creation script 或完整 migration procedure。

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

应用 RBAC objects 后，请使用 role 的实际 credentials 验证访问。此示例不关联 access policy，创建 access entry 也不会创建 RBAC objects。现有 bindings 或 policies 可能使有效权限比这些 Pod 读取权限更广。请考虑 propagation delay。

`aws-auth` ConfigMap 是 legacy mechanism。替换整个 ConfigMap 可能移除 node/Fargate mappings。请规划从 `CONFIG_MAP` 到 `API_AND_CONFIG_MAP` 的迁移，迁移并验证 mappings，然后使用 `API`。一旦启用，不能通过还原 modes 移除 API access；`API` 不能返回 ConfigMap mode。在同时使用两者时，对于同一 IAM principal，access entry 优先。并非所有现有 mappings 都会自动迁移。

`kubectl auth can-i --list` 不会显示来自 EKS access policies 的权限。使用 `--as`/`--as-group` 的 impersonation 会强制进行 Kubernetes RBAC evaluation，因此不会测试 IAM role 的 access-policy permissions。请以真实 role 验证各个操作，包括 namespace 外的预期拒绝和 Secret reads。

#### OIDC Provider 配置

这三条路径的方向和用途不同。

| 路径 | 身份验证目标和配置 |
|---|---|
| External OIDC user → Kubernetes API | 通过 EKS `AssociateIdentityProviderConfig` 关联外部 IdP，然后将其 users/groups 绑定到 RBAC。EKS 必须可通过公共 HTTPS 访问 issuer；不支持 self-signed issuer certificates。这不会禁用 IAM authentication。 |
| Pod → AWS API through IRSA | 在 cluster 的 ServiceAccount OIDC issuer 中建立 IAM trust，将 role trust 限制为预期的 namespace/ServiceAccount，并且仅授予所需 AWS resources。`eksctl utils associate-iam-oidc-provider` 用于此路径，而不是外部用户登录。 |
| Pod → AWS API through EKS Pod Identity | 在支持的 execution environments 中使用 Pod Identity Agent 和 role association。这不同于 IRSA 的 IAM OIDC provider 设置。 |

这两种 workload mechanisms 都不会自行授予 Kubernetes API RBAC。避免默认使用 account-wide S3 read managed policy 示例；应将权限限定到实际 bucket/object ARNs。请遵循 [EKS external OIDC](https://docs.aws.amazon.com/eks/latest/userguide/authenticate-oidc-identity-provider.html) 和 [workload IAM roles](https://docs.aws.amazon.com/eks/latest/userguide/service-accounts.html) 获取配置详情。

### Multi-tenant Cluster 安全性

在 multi-tenant environments 中，tenants 之间的隔离非常重要。

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
  policyTypes: [Ingress]
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          tenant: a
```

此 policy 允许来自每个标有 `tenant: a` 的 namespace 的 ingress。其他 ingress policies 可以添加允许项，且 egress 不受限制。它需要 CNI NetworkPolicy enforcement；只有受信任的 administrators 才应控制 namespace labels 和 policies。namespace 本身并不能保证 hostile tenants 之间的强隔离。测验包含两个方向的 default deny；请审查 DNS 和必要流量的单独允许项。

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

1. **定期证书轮换**：定期续订证书。
2. **禁用 Service Account Token 自动挂载**：不需要时禁用自动 service account token 挂载。
3. **最小化 RBAC 策略**：仅授予最低限度的必要权限。
4. **实施 Network Policies**：限制 pods 之间的通信。
5. **启用 Audit Logging**：验证 audit-policy coverage、敏感数据排除、retention 和 log access。在 EKS 上启用 `audit` control-plane log type 并验证 CloudWatch delivery；不要假设每个 request body 都会被记录。
6. **配置 Security Contexts**：为 pods 和 containers 正确配置 security contexts。
7. **Image Scanning**：定期扫描 container images 中的 vulnerabilities。

## 结论

Kubernetes 的身份验证和授权系统是 cluster security 的核心要素。通过选择适当的身份验证方法、使用 RBAC 实施细粒度访问控制，以及通过 admission controllers 应用额外安全策略，您可以构建一个安全的 Kubernetes environment。

身份验证、授权和准入控制相互补充，必须结合使用它们来实施 Defense in Depth strategy。

## 官方参考资料

- [Kubernetes 身份验证](https://kubernetes.io/docs/reference/access-authn-authz/authentication/)
- [Kubernetes 授权](https://kubernetes.io/docs/reference/access-authn-authz/authorization/)
- [RBAC](https://kubernetes.io/docs/reference/access-authn-authz/rbac/)
- [ServiceAccount 配置](https://kubernetes.io/docs/tasks/configure-pod-container/configure-service-account/)
- [ABAC](https://kubernetes.io/docs/reference/access-authn-authz/abac/)
- [Node 授权](https://kubernetes.io/docs/reference/access-authn-authz/node/)
- [Admission controllers](https://kubernetes.io/docs/reference/access-authn-authz/admission-controllers/)
- [Admission webhooks](https://kubernetes.io/docs/reference/access-authn-authz/extensible-admission-controllers/)
- [NetworkPolicy](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- [EKS certificate signing](https://docs.aws.amazon.com/eks/latest/userguide/cert-signing.html)
- [EKS access entries](https://docs.aws.amazon.com/eks/latest/userguide/creating-access-entries.html)
- [EKS authentication modes](https://docs.aws.amazon.com/eks/latest/userguide/setting-up-access-entries.html)
- [EKS access policy evaluation](https://docs.aws.amazon.com/eks/latest/userguide/access-policies.html)
- [EKS audit logs](https://docs.aws.amazon.com/eks/latest/userguide/control-plane-logs.html)
- [Trusted kubeconfig](https://kubernetes.io/docs/concepts/configuration/organize-cluster-access-kubeconfig/)
