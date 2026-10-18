# Kubernetes 身份验证和授权系统

> **范围**：Kubernetes 稳定 API 和 Amazon EKS 用户访问管理
> **最后更新**：2026 年 10 月 12 日

## 概述

身份验证用于确定请求身份，授权决定该身份可以执行哪些 API 操作，而准入控制会对已获授权的变更应用额外策略。以下清单是相互独立的学习示例；请先准备命名空间、管理员权限、证书和 webhook 服务器。未测试实际集群/API 调用或 EKS 访问变更。

`kube-apiserver` 标志示例适用于**自管理控制平面**。对于 EKS，请使用托管访问设置；这些示例不是配置其 API server 标志或获取其 CA 私钥的说明。

## 身份验证

身份验证是验证用户或服务是否为其所声称身份的过程。Kubernetes 支持多种身份验证方法，并且可同时启用这些方法。

使用多个身份验证器时，将采用第一个成功的结果，但不保证其评估顺序。无效凭证可能导致身份验证失败。对无凭证请求的处理取决于匿名身份验证设置，并且匿名身份仍然需要授权。

### 身份验证策略

#### 1. X.509 证书

使用由 API server 的 `--client-ca-file` 所信任的**客户端 CA**签名的证书。主体 CN 提供用户名，O 提供组；证书需要客户端身份验证（`clientAuth`）用途。用于验证服务器 TLS 证书的 CA 与对客户端进行身份验证的 CA 用途不同。

**本地私钥和 CSR 示例：**

```bash
umask 077
auth_lab_dir=$(mktemp -d)
openssl genrsa -out "$auth_lab_dir/john.key" 2048
openssl req -new -key "$auth_lab_dir/john.key" \
  -out "$auth_lab_dir/john.csr" -subj '/CN=john/O=engineering'
openssl req -in "$auth_lab_dir/john.csr" -noout -verify
```

这些命令不会签发证书。请将**仅 CSR**发送给获批准的签发方，该签发方必须审查身份、组、用途和有效期。不要将 CA 私钥复制给用户，也不要未经审查就批准组织名称。EKS `beta.eks.amazonaws.com/app-serving` 签发方用于服务证书，且不支持用户客户端证书签名。对于 EKS 用户访问，请使用下方的 IAM/OIDC 路径。

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

请将路径替换为已签发的文件，并限制对私钥和 kubeconfig 的访问。`*-data` 字段中的 Base64 并非加密。使用不受信任的 kubeconfig 文件前请先检查：它们可通过凭证插件执行命令。

#### 2. Service Account Token

ServiceAccount 是带命名空间的工作负载身份。每个命名空间都有一个 `default` 账户；Pod 的 `serviceAccountName` 指向同一命名空间中的账户。选择账户本身不会授予对应用程序资源的访问权限。

此示例不会调用 API，并禁用了自动 Token 挂载。其示例镜像不提供网络服务。

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

`automountServiceAccountToken` 是顶级 ServiceAccount 字段和 Pod `spec` 字段。Pod 设置优先。它控制默认挂载；并不会阻止显式声明的 `serviceAccountToken` 投射卷。

对于需要 API 访问的 Pod，kubelet 通过 TokenRequest 获取并轮换默认投射 Token。默认 Token 文件为 `/var/run/secrets/kubernetes.io/serviceaccount/token`。应用程序必须重新加载轮换后的文件。过期时间和受众绑定会降低暴露风险，但不会使 Bearer Token 可以安全泄露。不要认为创建账户会自动创建长期 Secret Token。[测验的投射卷示例](../quizzes/security/02-kubernetes-auth-authz-quiz.md)涵盖自定义受众和请求的有效期。

#### 3. OpenID Connect (OIDC)

OIDC 允许 API server 验证来自外部身份提供商的 **ID Token**。请配置签发方、受众、签名/过期验证和身份映射。API server 不提供交互式登录或签发刷新 Token。客户端应针对其身份提供商使用经审查的工具或 `exec` 凭证插件。

以下是**自管理 API server 的附加标志**，而非完整启动命令或 kubeconfig。请替换示例 HTTPS 签发方和客户端 ID。

```text
--oidc-issuer-url=https://idp.example.com
--oidc-client-id=kubernetes
--oidc-username-claim=sub
--oidc-username-prefix=oidc:
--oidc-groups-claim=groups
--oidc-groups-prefix=oidc:
```

为用户名和组添加前缀，以避免与 `system:` 组等现有身份冲突。结构化 `AuthenticationConfiguration` 是一种替代方案；不要将 `--authentication-config` 与 `--oidc-*` 标志组合使用。请通过下方单独的托管流程为 EKS 配置外部 OIDC 提供商。

#### 4. Webhook Token 身份验证

自管理 API server 会向外部服务发送 `authentication.k8s.io/v1` **TokenReview**。以下是 API server 用于连接该服务的**独立 kubeconfig**。它不是用户 kubeconfig 中的 `authentication.webhook` 字段。

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

如果安装在 `/etc/kubernetes/authn-webhook.kubeconfig`，请在 API server 上配置 `--authentication-token-webhook-config-file=/etc/kubernetes/authn-webhook.kubeconfig` 和 `--authentication-token-webhook-version=v1`。请分别配置所引用的证书和服务。该服务必须验证 Token 和预期受众，并返回 TokenReview 响应。请设计双向 TLS、凭证保护、缓存 TTL 和故障行为。本示例既未提供 webhook 实现，也未提供可用性验证。

#### 5. 身份验证代理

身份验证代理会验证调用方并转发产生的用户名和组。仅命名受信任的请求头并不能建立信任。首先使用专用前端代理 CA 和允许的客户端证书 CN 来验证代理的 TLS 身份。

**自管理 API server 标志摘录：**

```text
--requestheader-client-ca-file=/etc/kubernetes/front-proxy-ca.crt
--requestheader-allowed-names=front-proxy-client
--requestheader-username-headers=X-Remote-User
--requestheader-group-headers=X-Remote-Group
```

代理必须剥离调用方提供的身份请求头，并用已验证的值替换它们。不要将普通用户客户端 CA 复用于代理 CA，也不要将允许的 CN 留空以信任所有客户端证书。本摘录并未实现代理本身。

### 用户和组

在 Kubernetes 中，用户分类如下：

1. **常规用户**：在集群外部管理；Kubernetes 不直接管理他们。
2. **Service Account**：由 Kubernetes API 管理的账户。

用户可以属于一个或多个组，而组用于授权策略。

## 授权

授权是验证经身份验证的用户是否有权限执行请求操作的过程。Kubernetes 支持多个授权模块。

### 授权模式

#### 1. RBAC（基于角色的访问控制）

RBAC 提供基于角色的访问控制，目前是 Kubernetes 中最广泛使用的授权机制。

**关键概念：**

1. **Role**：定义命名空间内的权限。
2. **ClusterRole**：针对集群资源、非资源 URL 或命名空间资源上可复用权限的集群范围定义。
3. **RoleBinding**：引用同一命名空间中的 Role 或 ClusterRole，并**仅在绑定所在命名空间内**授予权限。ServiceAccount 主体可以显式属于另一个命名空间。
4. **ClusterRoleBinding**：在整个集群范围内授予 ClusterRole 的权限；它不能引用 Role。

没有绑定的角色定义不会授予任何权限。RBAC 会添加允许的权限，且没有显式拒绝规则。Secret `get/list/watch` 允许读取 Secret 数据，因此这些示例改用 Pod 读取。

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

此 ClusterRoleBinding 展示了一个明确需要**跨所有命名空间的 Pod 信息**的运维组；这并非默认建议。对于单个命名空间，请改为使用其中的 RoleBinding，并设置 `roleRef.kind: ClusterRole` 和 `roleRef.name: pod-reader-reusable`。

#### 2. ABAC（基于属性的访问控制）

ABAC 提供基于属性的访问控制。策略在 JSON 文件中定义。

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

包括 ABAC 是为了理解现有自管理集群。由 `--authorization-policy-file` 使用的策略是一个**每行一个 JSON 对象**的文件，而不是 Kubernetes API 资源。上面的缩进用于说明；请在实际文件中将每个策略序列化为一行。变更需要重启 API server。新配置应优先使用 RBAC；此标志不是 EKS 配置机制。

#### 3. Node 授权

Node 授权专用于 kubelet。其身份必须属于 `system:nodes`，并使用与实际 Node 名称匹配的用户名 `system:node:<nodeName>`。这不是工作负载访问机制。在自管理集群上，将其与 NodeRestriction 准入控制结合，以限制 kubelet 对 Node 和 Pod 对象的变更。

#### 4. Webhook 授权

自管理 API server 会向外部服务发送 `authorization.k8s.io/v1` **SubjectAccessReview**。请使用与上方身份验证 webhook 相同的连接文件格式，但使用单独的授权端点、CA 和客户端证书。请配置 `--authorization-webhook-config-file` 和 `--authorization-webhook-version=v1`，或使用结构化 `AuthorizationConfiguration` 来配置链和故障策略。用户 kubeconfig 中不存在 `authorization.webhook` 字段。

授权器按配置顺序运行；第一个**允许或拒绝**决定结果。`NoOpinion` 会继续到下一个授权器；所有 NoOpinion 结果都会拒绝访问。后续 webhook 无法否决 RBAC 已允许的请求。`system:masters` 是一个绕过 RBAC 和 webhook 授权的特殊组；不要将它分配给普通管理员，也不要认为移除角色绑定就能撤销其访问权限。

### 授权最佳实践

1. **最小权限原则**：仅授予最低必要权限。
2. **角色分离**：根据管理员、开发人员和运维人员等角色授予适当权限。
3. **命名空间分离**：按团队或项目划分命名空间，并授予适当权限。
4. **Service Account 分离**：为每个应用程序使用独立的 Service Account。
5. **定期审计**：定期审查和更新授权策略。

## 准入控制

准入控制在身份验证和授权后、处理请求之前执行额外的验证和修改。

准入控制处理创建、变更、删除以及某些连接请求；**get/list/watch 读取会绕过准入控制**。变更在验证之前进行，且任一阶段都可以拒绝请求。

### 准入控制器类型

1. **变更准入控制器**：可以修改请求。
2. **验证准入控制器**：仅验证请求而不进行修改。

### 关键准入控制器

1. **LimitRanger**：应用由 LimitRange 定义的默认值以及最小/最大约束。
2. **ResourceQuota**：检查对象数量、资源请求及类似数量的已配置命名空间配额；它不是对测得的 CPU/内存消耗或支出的上限。
3. **PodSecurity**：根据命名空间标签应用 Pod 安全标准。旧版 PodSecurityPolicy 已在 Kubernetes 1.25 中移除。
4. **ServiceAccount**：自动为 Pod 分配 Service Account。
5. **DefaultStorageClass**：为未指定类的 PVC 选择默认 StorageClass；它不会创建 StorageClass。

### 动态准入控制

动态准入控制通过 webhook 实现：

1. **MutatingAdmissionWebhook**：可以修改请求。
2. **ValidatingAdmissionWebhook**：仅验证请求而不进行修改。

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

此 webhook 仅针对带有显式标签的命名空间。没有实际 HTTPS 服务、CA 和保留请求 UID 的 AdmissionReview 实现时，请不要安装它。`failurePolicy: Fail` 会在调用错误/超时时阻止匹配请求。`Ignore` 会忽略调用失败；它不会将成功返回的拒绝变为允许。请在专用命名空间中测试可用性和恢复。CEL ValidatingAdmissionPolicy 是另一种验证选项。

## 实际实现示例

### EKS 中的身份验证和授权配置

#### IAM 和 RBAC 集成

对于当前的 EKS IAM 用户访问，请使用**访问条目**。IAM 角色提供经身份验证的身份；关联的 EKS 访问策略或 Kubernetes RBAC 授予 Kubernetes 权限。两个路径中的允许权限会累积。EKS 访问策略不是 IAM 策略。

以下是针对现有集群和 IAM 角色的管理员变更示例。首先确认账户、Region、集群、`API` 或 `API_AND_CONFIG_MAP` 模式、现有的 `development` 命名空间、不存在重复的访问条目，以及拥有 `eks:CreateAccessEntry` 和 RBAC 变更的权限。这不是基础设施创建脚本或完整迁移流程。

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

应用 RBAC 对象后，请使用角色的实际凭证验证访问。此示例不关联访问策略，且创建访问条目不会创建 RBAC 对象。现有绑定或策略可能使有效权限比这些 Pod 读取权限更广泛。请考虑传播延迟。

`aws-auth` ConfigMap 是旧版机制。替换整个 ConfigMap 可能移除 Node/Fargate 映射。请规划从 `CONFIG_MAP` 迁移到 `API_AND_CONFIG_MAP`，迁移并验证映射，然后使用 `API`。启用后，无法通过还原模式移除 API 访问；`API` 无法返回 ConfigMap 模式。两者并用时，同一 IAM 主体的访问条目优先。并非所有现有映射都会自动迁移。

`kubectl auth can-i --list` 不显示来自 EKS 访问策略的权限。使用 `--as`/`--as-group` 进行模拟会强制 Kubernetes RBAC 评估，因此不会测试 IAM 角色的访问策略权限。请以实际角色验证各个操作，包括命名空间外的预期拒绝以及 Secret 读取。

#### OIDC 提供商配置

以下三条路径具有不同的方向和用途。

| 路径 | 身份验证目标和配置 |
|---|---|
| 外部 OIDC 用户 → Kubernetes API | 通过 EKS `AssociateIdentityProviderConfig` 关联外部 IdP，然后将其用户/组绑定到 RBAC。EKS 必须能通过公共 HTTPS 访问签发方；使用客户路由的控制平面出口（`controlPlaneEgressMode=CUSTOMER_ROUTED`）时，签发方还必须能通过您在 VPC 中配置的出口路径访问。不支持自签名签发方证书。这不会禁用 IAM 身份验证。 |
| Pod → 通过 IRSA 访问 AWS API | 在集群的 ServiceAccount OIDC 签发方中建立 IAM 信任，将角色信任限制为预期的命名空间/ServiceAccount，并且仅授予所需 AWS 资源。`eksctl utils associate-iam-oidc-provider` 用于此路径，而非外部用户登录。 |
| Pod → 通过 EKS Pod Identity 访问 AWS API | 在支持的执行环境上使用 Pod Identity Agent 和角色关联。这不同于 IRSA 的 IAM OIDC 提供商设置。 |

这两种工作负载机制本身都不会授予 Kubernetes API RBAC。避免将账户范围的 S3 读取托管策略作为默认示例；请将权限范围限定为实际存储桶/对象 ARN。有关配置详情，请参阅 [EKS 外部 OIDC](https://docs.aws.amazon.com/eks/latest/userguide/authenticate-oidc-identity-provider.html) 和 [工作负载 IAM 角色](https://docs.aws.amazon.com/eks/latest/userguide/service-accounts.html)。

### 多租户集群安全

在多租户环境中，租户之间的隔离非常重要。

**命名空间隔离：**

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

此策略允许来自标记为 `tenant: a` 的**每个**命名空间的入站流量。其他入站策略可以增加允许项，且出站不受限制。它需要 CNI NetworkPolicy 强制执行；只有受信任的管理员才应控制命名空间标签和策略。仅凭命名空间无法保证敌对租户之间的强隔离。测验包含双向默认拒绝；请审查 DNS 和必要流量的单独允许项。

**资源配额：**

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

1. **定期轮换证书**：定期更新证书。
2. **禁用 Service Account Token 自动挂载**：在不需要时禁用自动 Service Account Token 挂载。
3. **最小化 RBAC 策略**：仅授予最低必要权限。
4. **实施 NetworkPolicy**：限制 Pod 之间的通信。
5. **启用审计日志**：验证审计策略覆盖范围、敏感数据排除项、保留期和日志访问。在 EKS 上启用 `audit` 控制平面日志类型并验证 CloudWatch 交付；不要假定会记录每个请求正文。
6. **配置安全上下文**：为 Pod 和容器正确配置安全上下文。
7. **镜像扫描**：定期扫描容器镜像中的漏洞。

## 结论

Kubernetes 的身份验证和授权系统是集群安全的核心要素。通过选择适当的身份验证方法、借助 RBAC 实施细粒度访问控制，并使用准入控制器应用额外安全策略，您可以构建安全的 Kubernetes 环境。

身份验证、授权和准入控制彼此互补，重要的是结合使用它们来实施纵深防御策略。

## 官方参考资料

- [Kubernetes 身份验证](https://kubernetes.io/docs/reference/access-authn-authz/authentication/)
- [Kubernetes 授权](https://kubernetes.io/docs/reference/access-authn-authz/authorization/)
- [RBAC](https://kubernetes.io/docs/reference/access-authn-authz/rbac/)
- [ServiceAccount 配置](https://kubernetes.io/docs/tasks/configure-pod-container/configure-service-account/)
- [ABAC](https://kubernetes.io/docs/reference/access-authn-authz/abac/)
- [Node 授权](https://kubernetes.io/docs/reference/access-authn-authz/node/)
- [准入控制器](https://kubernetes.io/docs/reference/access-authn-authz/admission-controllers/)
- [准入 webhook](https://kubernetes.io/docs/reference/access-authn-authz/extensible-admission-controllers/)
- [NetworkPolicy](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- [EKS 证书签名](https://docs.aws.amazon.com/eks/latest/userguide/cert-signing.html)
- [EKS 访问条目](https://docs.aws.amazon.com/eks/latest/userguide/creating-access-entries.html)
- [EKS 身份验证模式](https://docs.aws.amazon.com/eks/latest/userguide/setting-up-access-entries.html)
- [EKS 访问策略评估](https://docs.aws.amazon.com/eks/latest/userguide/access-policies.html)
- [EKS 审计日志](https://docs.aws.amazon.com/eks/latest/userguide/control-plane-logs.html)
- [受信任的 kubeconfig](https://kubernetes.io/docs/concepts/configuration/organize-cluster-access-kubeconfig/)
