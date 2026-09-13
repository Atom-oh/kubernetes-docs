# Kubernetes 认证与授权测验

> **相关文档**: [Kubernetes 认证与授权系统](../../security/02-kubernetes-auth-authz.md)

> **最后更新**: September 13, 2026

## 单选题

### 1. 在 Kubernetes X.509 证书认证中，用户名是从哪个字段中提取的？

- A) Subject Alternative Name (SAN)
- B) Common Name (CN)
- C) Organization Unit (OU)
- D) Issuer

<details>
<summary>显示答案</summary>

**答案：B) Common Name (CN)**

**解释：**
在 X.509 证书中，Common Name (CN) 映射为用户名，而 Organization (O) 映射为用户组。

</details>

### 2. 在 RBAC 中，ClusterRole 与 Role 的主要区别是什么？

- A) ClusterRole 是只读的，Role 是可读写的
- B) ClusterRole 是集群范围（cluster-scoped）的定义；Role 是命名空间范围（namespaced）的定义
- C) ClusterRole 仅限管理员使用，Role 供普通用户使用
- D) ClusterRole 仅适用于 node，Role 仅适用于 pod

<details>
<summary>显示答案</summary>

**答案：B) ClusterRole 是集群范围（cluster-scoped）的定义；Role 是命名空间范围（namespaced）的定义**

**解释：**
ClusterRole 也可以为命名空间级资源定义可复用的权限。引用它的 RoleBinding 会把授权限制在该绑定所在的 namespace（命名空间）内；而 ClusterRoleBinding 则在整个集群范围内授予其权限。仅有定义本身不会授予任何权限。

</details>

### 3. ServiceAccount token 在 pod 中被自动挂载的默认路径是什么？

- A) /var/run/secrets/kubernetes.io/token
- B) /etc/kubernetes/serviceaccount
- C) /var/run/secrets/kubernetes.io/serviceaccount
- D) /opt/kubernetes/secrets

<details>
<summary>显示答案</summary>

**答案：C) /var/run/secrets/kubernetes.io/serviceaccount**

**解释：**
这是在启用了自动挂载的 Linux Pod 中的默认目录。token 就是该目录下的 `token` 文件。设置了 `automountServiceAccountToken: false` 的 Pod 或使用自定义 projected volume 的 Pod，其路径可能不同，或者根本没有 token。

</details>

### 4. MutatingAdmissionWebhook 和 ValidatingAdmissionWebhook 的执行顺序是什么？

- A) 先 Validating，然后 Mutating
- B) 先 Mutating，然后 Validating
- C) 同时并行执行
- D) 无序随机执行

<details>
<summary>显示答案</summary>

**答案：B) 先 Mutating，然后 Validating**

**解释：**
Admission controller（准入控制器）的执行顺序：1) MutatingAdmissionWebhook（修改请求），2) ValidatingAdmissionWebhook（校验请求）。

</details>

<span id="_5-what-configmap-maps-iam-users-roles-to-kubernetes-rbac-in-eks"></span>

### 5. 在旧版 EKS CONFIG_MAP 认证模式中，哪个 ConfigMap 存储 IAM 映射？

- A) kube-config
- B) aws-auth
- C) eks-iam-mapping
- D) cluster-auth

<details>
<summary>显示答案</summary>

**答案：B) aws-auth**

**解释：**
`kube-system/aws-auth` 是旧版的 IAM 映射方式。当前的访问管理应使用 EKS access entry 配合适当的 RBAC，或使用 EKS access policy。在双模式迁移期间，对于同一个 principal，access entry 优先生效。替换整个 ConfigMap 可能会移除 node 的映射。

</details>

<span id="_6-which-authentication-method-is-recommended-for-production-kubernetes-clusters"></span>

### 6. 哪种方式通过外部身份提供商（identity provider）颁发的 ID token 来集成用户登录？

- A) 静态 token 文件
- B) Basic 认证
- C) OIDC (OpenID Connect)
- D) 匿名认证

<details>
<summary>显示答案</summary>

**答案：C) OIDC (OpenID Connect)**

**解释：**
OIDC 会校验外部颁发的 ID token 的 issuer、audience、签名和有效期。登录与刷新由 IdP/客户端处理；API server 不会颁发 refresh token。EKS IAM 认证是另一条用户访问路径，而 IRSA/Pod Identity 的用途不同：它们用于 Pod 访问 AWS API。

</details>

### 7. Kubernetes 中 `system:masters` 组的作用是什么？

- A) 管理 master 节点
- B) 提供绕过 RBAC/webhook 授权的无限制 API 访问权限
- C) 在 master 节点上调度 pod
- D) 管理系统 namespace

<details>
<summary>显示答案</summary>

**答案：B) 提供绕过 RBAC/webhook 授权的无限制 API 访问权限**

**解释：**
`system:masters` 是一个特殊的绕过授权的组。它并不等同于普通的管理员角色绑定，删除 ClusterRoleBinding 也无法收回这种绕过能力。请避免把该组分配给普通管理员。

</details>

### 8. 如何限制一个 ServiceAccount 只能读取特定 namespace 中的 pod？

- A) ClusterRole + ClusterRoleBinding
- B) Role + ClusterRoleBinding
- C) 仅使用 Role
- D) Role + RoleBinding

<details>
<summary>显示答案</summary>

**答案：D) Role + RoleBinding**

**解释：**
在假定不存在其他授权的前提下，使用一个仅允许对 Pod 执行 get/list/watch 的 Role，并在该 namespace 中创建 RoleBinding。**ClusterRole + RoleBinding 同样有效**，因此它不能作为错误选项。作为 subject 的 ServiceAccount 可以显式属于另一个 namespace；权限范围仍然是绑定所在的 namespace。

</details>

### 9. RBAC 中 `impersonate` 动词（verb）的作用是什么？

- A) 创建伪造的资源
- B) 允许一个用户以另一个用户或组的身份执行操作
- C) 复制资源
- D) 屏蔽资源名称

<details>
<summary>显示答案</summary>

**答案：B) 允许一个用户以另一个用户或组的身份执行操作**

**解释：**
`impersonate` 动词允许用户像另一个用户、组或 ServiceAccount 那样执行操作。这在调试和管理场景中非常有用。

</details>

### 10. 在挂载的卷中，哪个文件包含 ServiceAccount token？

- A) ca.crt
- B) namespace
- C) token
- D) serviceaccount.json

<details>
<summary>显示答案</summary>

**答案：C) token**

**解释：**
默认自动挂载的 ServiceAccount 卷提供以下文件（自定义 projection 可能有所不同）：`ca.crt`（CA 证书）、`namespace`（当前 namespace）以及 `token`（用于认证的 JWT token）。

</details>

## 简答题

### 1. Kubernetes 中用户账户（user account）与服务账户（service account）的主要区别是什么？

<details>
<summary>显示答案</summary>

**答案：用户账户由外部系统管理，不由 Kubernetes 直接管理；而服务账户是通过 Kubernetes API 管理的命名空间级资源。**

</details>

### 2. 如何禁用 ServiceAccount token 的自动挂载？

<details>
<summary>显示答案</summary>

**答案：在 ServiceAccount 顶层或 Pod spec 中设置 `automountServiceAccountToken: false`。Pod 上的设置优先生效；显式声明的 projected token 卷仍然有效。**

</details>

### 3. ClusterRole 中的 `rules` 与 `aggregationRule` 有什么区别？

<details>
<summary>显示答案</summary>

**答案：`rules` 直接定义权限，而 `aggregationRule` 会自动合并匹配特定 label 的其他 ClusterRole 的权限。**

**解释：**
聚合控制器（aggregation controller）管理目标 ClusterRole 的 rules，可能会覆盖手动修改的规则。添加或编辑被 label 选中的角色的权限，同样会影响最终生效的访问权限。

</details>

### 4. 什么是 TokenRequest API，为什么它比静态 token 更受推荐？

<details>
<summary>显示答案</summary>

**答案：TokenRequest API 创建有时间限制、绑定 audience 的 token，比长期有效的静态 token 更安全。**

**解释：**
请查看服务器返回的实际有效期，服务器可能会调整所请求的生命周期。kubelet 会轮换 Pod 中 projected 的 token，但应用程序必须重新加载该文件。单独调用 TokenRequest 本身并不提供文件的自动轮换。这些 token 仍然属于需要保密的 bearer 凭证。

</details>

### 5. 当配置了多种认证方式时，Kubernetes 如何决定使用哪一种？

<details>
<summary>显示答案</summary>

**答案：使用第一个认证成功的结果，但 authenticator（认证器）的评估顺序并不保证。**

**解释：**
不要假定存在固定的 X.509 → OIDC → proxy 顺序。无效凭证可能导致 401。对于不带凭证的请求，是否按匿名处理取决于服务器设置；匿名身份仍可能在授权阶段被拒绝。

</details>

## 实操题

### 1. 编写满足以下要求的 Role 和 RoleBinding：

- Namespace: development
- 权限：Pod 读取（get、list、watch），ConfigMap 读取以及针对单个对象的 create/update/patch/delete（不包含 deletecollection）
- 用户：developer@example.com

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

<span id="_2-create-a-serviceaccount-with-a-custom-token-expiration-time"></span>

### 2. 创建一个 ServiceAccount 以及一个使用 projected token 并请求自定义生命周期的 Pod。

<details>
<summary>显示答案</summary>

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

**解释：**
所请求的 `expirationSeconds` 最小值为 600；实际有效期由服务器决定。示例中的 audience 必须由接收方服务配置并校验；Kubernetes API 不会自动接受它。对于调用 Kubernetes API 的场景，请使用 API server 能够接受的 audience。示例中禁用了自动挂载，只以只读方式挂载了显式声明的 token。这个 pause Pod 只是用来演示该卷；它既不使用该 token，也不提供 HTTP 服务。实际应用必须在 kubelet 轮换该文件后重新加载它。

</details>

### 3. 编写命令以检查某个特定用户拥有哪些权限。

<details>
<summary>显示答案</summary>

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

**解释：**
调用方需要对目标用户/ServiceAccount 以及所使用的每个组拥有 `impersonate` 权限。不要假定组成员关系会被自动重建。`--list` 并不总是完整的有效权限清单，且不包含 EKS access policy 授予的权限。EKS impersonation 会强制走 RBAC 评估；请另外单独测试实际的 IAM role。`can-i` 返回肯定结果并不保证能够通过 admission、具备网络访问能力或被 quota 接受。

</details>

## 进阶题

### 1. 为多租户 Kubernetes 集群中的租户隔离设计一套安全策略。

<details>
<summary>显示答案</summary>

**Namespace 与 RBAC 设计：**

- 为每个租户创建独立的 namespace
- 应用 Pod Security Standards
- 通过 NetworkPolicy 实现网络隔离
- 通过 ResourceQuota 设置资源限制

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

这里固定的 PSS 版本 `v1.35` 只是学习用的基线；请选择并验证目标集群支持的策略版本。默认拒绝同时也会阻断 DNS 和外部依赖，因此需要审视显式放行的规则。策略必须由 CNI 来实施。租户不得修改 namespace label、NetworkPolicy、ResourceQuota 或 RBAC，同时还需要审查其他已有的绑定。

**创建/编辑 Deployment 可能使 Pod 得以使用该 namespace 中的其他 ServiceAccount 或 Secret。** 仅移除 Secret 的 get 权限并不能封堵这条路径。请把信任级别不同的身份/机密分离到不同的 namespace，必要时通过 admission 约束允许使用的身份，或者使用独立的集群。本示例并不足以证明实现了强租户隔离。

**额外的安全措施：**

- 为每个应用使用独立的 ServiceAccount
- 实施审计日志（audit logging）
- 使用 admission webhook 强制执行策略
- 明确定义子租户的归属与策略传播方式；普通的 Kubernetes namespace 是扁平结构

</details>

### 2. 解释执行一条 kubectl 命令时完整的认证与授权流程。

<details>
<summary>显示答案</summary>

1. **客户端**：kubectl 读取所选的 kubeconfig/context，并校验服务器的 TLS 证书。默认文件是 `~/.kube/config`，但 `--kubeconfig` 和 `KUBECONFIG` 可以改变它。它从证书、token 或 exec 插件获取凭证；EKS IAM 访问通常使用 `aws eks get-token`。
2. **认证（Authentication）**：API server 校验凭证以确定用户/组身份。它采用第一个认证成功的 authenticator 结果，且不保证固定的评估顺序。OIDC、proxy 和 webhook 各有不同的校验与信任要求。
3. **授权（Authorization）**：已配置的 authorizer（授权器）按顺序执行，直到出现第一个 Allow 或 Deny。NoOpinion 会继续往下评估；如果全部返回 NoOpinion，则以 403 拒绝。RBAC 会累加所有适用绑定授予的权限，且没有显式拒绝规则。`system:masters` 的绕过机制是一个单独的风险点。
4. **请求处理**：普通资源的 CREATE/UPDATE 请求会先经过 mutation（修改）准入，再经过 validation（校验）准入；两者都可能拒绝请求。变更在通过对象校验、冲突检查以及其他相关检查后才会被存储。`get/list/watch` 会跳过 admission。dry-run、DELETE、CONNECT 以及聚合 API 并不都能用同一套 etcd 写入流程来描述。
5. **响应**：API server 返回结果或错误。API 调用成功并不意味着某个控制器已完成处理，或应用已就绪。

| 示例请求 | 认证/授权之后的差异 |
|---|---|
| `kubectl get pods` | 返回读取结果；不执行 admission，也不存储新的 Pod |
| Pod CREATE | 在存储前需通过 mutation/validation 准入及对象检查；随后进行调度 |
| 服务端 dry-run CREATE | 执行包含 admission 的服务端校验，但不做持久化存储 |

认证确定身份，授权允许 API 操作，而 admission 对变更施加额外的策略。

</details>

## 官方参考资料

- [Authentication](https://kubernetes.io/docs/reference/access-authn-authz/authentication/)
- [Authorization](https://kubernetes.io/docs/reference/access-authn-authz/authorization/)
- [RBAC](https://kubernetes.io/docs/reference/access-authn-authz/rbac/)
- [ServiceAccount](https://kubernetes.io/docs/tasks/configure-pod-container/configure-service-account/)
- [Admission](https://kubernetes.io/docs/reference/access-authn-authz/admission-controllers/)
- [EKS access policies](https://docs.aws.amazon.com/eks/latest/userguide/access-policies.html)
