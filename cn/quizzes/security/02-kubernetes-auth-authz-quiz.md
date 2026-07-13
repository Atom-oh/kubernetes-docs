# Kubernetes 身份认证和授权测验

> **相关文档**: [Kubernetes 身份认证和授权系统](../../security/02-kubernetes-auth-authz.md)

## 单项选择题

### 1. 在 Kubernetes X.509 证书身份认证中，用户名是从哪个字段提取的？

- A) 主题备用名称 (SAN)
- B) 通用名称 (CN)
- C) 组织单位 (OU)
- D) 颁发者

<details>
<summary>显示答案</summary>

**答案：B) 通用名称 (CN)**

**解释：**
在 X.509 证书中，通用名称 (CN) 映射到用户名，组织 (O) 映射到组。

</details>

### 2. RBAC 中 ClusterRole 和 Role 的主要区别是什么？

- A) ClusterRole 是只读的，Role 是读/写的
- B) ClusterRole 是集群范围作用域，Role 是 namespace 作用域
- C) ClusterRole 仅限管理员使用，Role 适用于普通用户
- D) ClusterRole 仅适用于 nodes，Role 仅适用于 pods

<details>
<summary>显示答案</summary>

**答案：B) ClusterRole 是集群范围作用域，Role 是 namespace 作用域**

**解释：**
Role 为特定 namespace 内的资源定义权限，而 ClusterRole 为集群范围资源或非 namespace 资源定义权限。

</details>

### 3. ServiceAccount token 在 pods 中自动挂载的默认路径是什么？

- A) /var/run/secrets/kubernetes.io/token
- B) /etc/kubernetes/serviceaccount
- C) /var/run/secrets/kubernetes.io/serviceaccount
- D) /opt/kubernetes/secrets

<details>
<summary>显示答案</summary>

**答案：C) /var/run/secrets/kubernetes.io/serviceaccount**

**解释：**
ServiceAccount token 默认挂载在 `/var/run/secrets/kubernetes.io/serviceaccount`。

</details>

### 4. MutatingAdmissionWebhook 和 ValidatingAdmissionWebhook 的执行顺序是什么？

- A) 先 Validating，然后 Mutating
- B) 先 Mutating，然后 Validating
- C) 同时并行执行
- D) 随机执行，没有顺序

<details>
<summary>显示答案</summary>

**答案：B) 先 Mutating，然后 Validating**

**解释：**
Admission controller 执行顺序：1) MutatingAdmissionWebhook（修改请求），2) ValidatingAdmissionWebhook（验证请求）。

</details>

### 5. 在 EKS 中，哪个 ConfigMap 将 IAM users/roles 映射到 Kubernetes RBAC？

- A) kube-config
- B) aws-auth
- C) eks-iam-mapping
- D) cluster-auth

<details>
<summary>显示答案</summary>

**答案：B) aws-auth**

**解释：**
在 Amazon EKS 中，`aws-auth` ConfigMap（位于 kube-system namespace）将 AWS IAM users 和 roles 映射到 Kubernetes users 和 groups。

</details>

### 6. 生产环境 Kubernetes clusters 推荐使用哪种身份认证方法？

- A) 静态 token 文件
- B) 基本身份认证
- C) OIDC (OpenID Connect)
- D) 匿名身份认证

<details>
<summary>显示答案</summary>

**答案：C) OIDC (OpenID Connect)**

**解释：**
OIDC 提供企业级身份认证，具备 token 过期、refresh tokens，以及与 Okta、Azure AD 和 Google 等身份提供商集成的功能。

</details>

### 7. Kubernetes 中 `system:masters` 组的用途是什么？

- A) 管理 master nodes
- B) 提供 cluster-admin 权限
- C) 在 master nodes 上调度 pods
- D) 管理 system namespaces

<details>
<summary>显示答案</summary>

**答案：B) 提供 cluster-admin 权限**

**解释：**
`system:masters` 组绑定到 `cluster-admin` ClusterRole，从而授予对 cluster 的完全管理访问权限。

</details>

### 8. 如何将一个 ServiceAccount 限制为只能读取特定 namespace 中的 pods？

- A) ClusterRole + ClusterRoleBinding
- B) Role + ClusterRoleBinding
- C) ClusterRole + RoleBinding
- D) Role + RoleBinding

<details>
<summary>显示答案</summary>

**答案：D) Role + RoleBinding**

**解释：**
对于 namespace 作用域的权限，请使用 Role（定义 namespace 内的权限）和 RoleBinding（将该 role 绑定到同一 namespace 内的 subject）。

</details>

### 9. RBAC 中 `impersonate` verb 的用途是什么？

- A) 创建伪造资源
- B) 允许用户以另一个用户或组的身份操作
- C) 复制资源
- D) 掩盖资源名称

<details>
<summary>显示答案</summary>

**答案：B) 允许用户以另一个用户或组的身份操作**

**解释：**
`impersonate` verb 允许用户像另一个 user、group 或 ServiceAccount 一样执行操作。这对于调试和管理很有用。

</details>

### 10. 在已挂载的 volume 中，哪个文件包含 ServiceAccount token？

- A) ca.crt
- B) namespace
- C) token
- D) serviceaccount.json

<details>
<summary>显示答案</summary>

**答案：C) token**

**解释：**
ServiceAccount volume mount 包含三个文件：`ca.crt`（CA 证书）、`namespace`（当前 namespace）和 `token`（用于身份认证的 JWT token）。

</details>

## 简答题

### 1. Kubernetes 中 user accounts 和 service accounts 的主要区别是什么？

<details>
<summary>显示答案</summary>

**答案：User accounts 由外部管理，并不由 Kubernetes 直接管理；而 service accounts 是 namespace 作用域的资源，通过 Kubernetes API 管理。**

</details>

### 2. 如何禁用自动挂载 ServiceAccount token？

<details>
<summary>显示答案</summary>

**答案：在 ServiceAccount 或 Pod spec 中设置 `automountServiceAccountToken: false`。**

</details>

### 3. ClusterRole 中 `rules` 和 `aggregationRule` 的区别是什么？

<details>
<summary>显示答案</summary>

**答案：`rules` 直接定义权限，而 `aggregationRule` 会自动组合来自匹配特定 labels 的其他 ClusterRoles 的权限。**

**解释：**
Aggregated ClusterRoles 适用于在不直接修改内置 roles 的情况下扩展它们。

</details>

### 4. 什么是 TokenRequest API，为什么它比静态 tokens 更受推荐？

<details>
<summary>显示答案</summary>

**答案：TokenRequest API 会创建有时间限制、绑定 audience 的 tokens，比长期有效的静态 tokens 更安全。**

**解释：**
来自 TokenRequest API 的 tokens 会自动过期，并绑定到特定 audiences，从而降低 token 被盗和误用的风险。

</details>

### 5. 当配置了多种身份认证方法时，Kubernetes 如何确定使用哪一种？

<details>
<summary>显示答案</summary>

**答案：Kubernetes 会按顺序尝试每种身份认证方法，直到其中一种成功。将使用第一个成功的身份认证。**

**解释：**
身份认证方法会以链式方式尝试。如果所有方法都失败，请求将被拒绝并返回 401 Unauthorized 错误。

</details>

## 实践题

### 1. 编写一个满足以下要求的 Role 和 RoleBinding：

- Namespace: development
- Permissions: Pod read (get, list, watch), ConfigMap full access
- User: developer@example.com

<details>
<summary>显示答案</summary>

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

### 2. 创建一个具有自定义 token 过期时间的 ServiceAccount。

<details>
<summary>显示答案</summary>

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

**解释：**
使用带有 `serviceAccountToken` 的 projected volumes，可以为 token 指定自定义 `expirationSeconds`（最少 600 秒）和 `audience`。

</details>

### 3. 编写一个命令，用于检查特定用户拥有哪些权限。

<details>
<summary>显示答案</summary>

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

**解释：**
`kubectl auth can-i` 命令可用于检查当前用户的权限，也可模拟其他 users/groups 来验证其访问级别。

</details>

## 进阶题

### 1. 为多租户 Kubernetes cluster 中的 tenant 隔离设计安全策略。

<details>
<summary>显示答案</summary>

**Namespace 和 RBAC 设计：**
- 为每个 tenant 创建单独的 namespaces
- 应用 Pod Security Standards
- 实施 NetworkPolicy 以实现网络隔离
- 设置 ResourceQuota 以限制资源

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

**其他安全措施：**
- 为每个 application 使用单独的 ServiceAccounts
- 实施 audit logging
- 使用 admission webhooks 进行策略执行
- 考虑使用 Hierarchical Namespaces 进行子 tenant 管理

</details>

### 2. 说明执行 kubectl 命令时完整的身份认证和授权流程。

<details>
<summary>显示答案</summary>

**完整流程：**

1. **Client Authentication (kubeconfig)**
   - kubectl 读取 `~/.kube/config`
   - 提取凭证（certificate、token 或 exec plugin）
   - 对于 EKS：`aws eks get-token` 生成临时 token

2. **API Server Authentication**
   - API server 接收带有凭证的请求
   - 按顺序尝试身份认证方法：
     - X.509 client certificates
     - Bearer tokens (ServiceAccount, OIDC)
     - Authentication proxy
     - Webhook token authentication
   - 第一个成功的方法决定身份

3. **Authorization**
   - API server 检查授权（通常是 RBAC）
   - 评估所有适用的 Roles/ClusterRoles
   - 决策：Allow 或 Deny
   - 如果有多个 authorizers：第一个非 deny 的结果获胜

4. **Admission Control**
   - **Mutating Admission**：修改请求
     - 添加 defaults，注入 sidecars
   - **Validating Admission**：验证请求
     - 执行 policies、quotas
   - 两者都可以拒绝请求

5. **Persistence**
   - 如果所有检查都通过，resource 将存储在 etcd 中
   - 将响应返回给 client

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

**要点：**
- Authentication 确定你是谁
- Authorization 确定你能做什么
- Admission controls 决定 resources 如何被修改/验证

</details>
