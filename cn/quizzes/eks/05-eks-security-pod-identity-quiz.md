# EKS Pod Identity 测验

> **最后更新**：2026年11月21日

本测验用于检查你对 [EKS Pod Identity](../../eks/05-eks-security-pod-identity.md) 的理解。

## 测验概览
- 关联的作用
- 代理和凭证流程
- 角色信任和会话标签
- 跨账户访问和缓存
- 与 IRSA 共存及从 IRSA 迁移

## 选择题

### 1. 关于 EKS Pod Identity 关联，哪项说法正确？

- A) 创建关联时，会自动在命名空间中创建 ServiceAccount
- B) 除 IAM 角色外，它还会授予 Kubernetes RBAC 权限
- C) 它以 ServiceAccount 对象本身上的注释形式存储在 Kubernetes 中
- D) 它会在 EKS API 中将集群、命名空间和 ServiceAccount 映射到 IAM 角色

<details>
<summary>显示答案</summary>

**答案：D) 它会在 EKS API 中将集群、命名空间和 ServiceAccount 映射到 IAM 角色**

**说明：**

关联是在 EKS API 中存储的集群/命名空间/ServiceAccount 到 IAM 角色的映射。它不会创建 ServiceAccount、授予 Kubernetes RBAC 权限，也不会创建 IAM 角色或代理。页面中的示例会先使用 `list-pod-identity-associations` 检查现有的关联，然后再创建关联，以免覆盖其他所有者的配置。

</details>

### 2. 新建且已关联的 Pod 中的 AWS SDK 如何获取 Pod Identity 凭证？

- A) SDK 调用节点代理，代理从 EKS Auth 获取凭证
- B) 代理会透明地拦截并签署 Pod 发出的每个 AWS 请求
- C) SDK 使用 Web 身份令牌调用 STS AssumeRoleWithWebIdentity
- D) SDK 使用通过 IMDSv2 从节点 IAM 角色获取的凭证

<details>
<summary>显示答案</summary>

**答案：A) SDK 调用节点代理，代理从 EKS Auth 获取凭证**

**说明：**

对于已关联的新 Pod，EKS 会注入一个受众为 `pods.eks.amazonaws.com` 的令牌、一个令牌文件环境变量，以及一个容器凭证 URI。SDK 会调用代理端点（通常为 `169.254.170.23/v1/credentials`），代理则会调用 EKS Auth 上的 AssumeRoleForPodIdentity，并将凭证返回给 SDK。这不是请求拦截器；应用仍会使用自己的凭证直接调用 AWS 服务。

</details>

### 3. 关于 Pod Identity 角色信任示例，哪项说法正确？

- A) 它会在信任策略中将集群的 IAM OIDC 提供商指定为 `Federated` 主体
- B) 只允许 `sts:AssumeRoleWithWebIdentity` 就足以支持 Pod Identity
- C) 它信任 `pods.eks.amazonaws.com` 执行 AssumeRole/TagSession，并通过标签限定范围
- D) 不附加任何条件地信任 `pods.eks.amazonaws.com` 符合最小权限原则

<details>
<summary>显示答案</summary>

**答案：C) 它信任 `pods.eks.amazonaws.com` 执行 AssumeRole/TagSession，并通过标签限定范围**

**说明：**

示例信任策略允许服务主体 `pods.eks.amazonaws.com` 执行 `sts:AssumeRole` 和 `sts:TagSession`，并通过 `aws:RequestTag/eks-cluster-arn`、`kubernetes-namespace` 和 `kubernetes-service-account` 条件限定范围。这些条件依赖默认会话标签，因此禁用标签时需要重新审查这些条件。创建关联的调用方还需要对目标角色拥有 `iam:PassRole` 权限。

</details>

### 4. 关于使用 Pod Identity 访问其他账户中的资源，哪项说法正确？

- A) 直接将其他账户中的任意角色设为关联角色
- B) 将关联角色保留在集群账户中，再链式切换到目标角色
- C) Pod Identity 不支持跨账户访问，因此始终应将这些工作负载切换到 IRSA
- D) 使用目标角色时，更改关联会立即重置凭证缓存

<details>
<summary>显示答案</summary>

**答案：B) 将关联角色保留在集群账户中，再链式切换到目标角色**

**说明：**

关联角色必须位于 EKS 集群所在的账户中。可选的目标 IAM 角色可以位于其他账户；配置好信任和 AssumeRole 权限后，Pod Identity 会从同一账户中的角色链式切换到该目标角色。当前指南说明，没有目标角色时缓存的凭证有效期为 6 小时，有目标角色时为 59 分钟；更改关联不会重置该缓存。重新创建 Pod 可以更快地获取新配置。

</details>

### 5. 如果一个 ServiceAccount 同时具有 IRSA 注释和 Pod Identity 关联，EKS 会如何注入凭证？

- A) 新 Pod 只会获得 Pod Identity 环境变量；运行中的 Pod 会保留其 IRSA 环境变量
- B) 新 Pod 会同时获得两组环境变量，SDK 会随机选择其中一组
- C) 创建关联会立即重写运行中 Pod 的环境变量
- D) IRSA 注释始终优先，因此新 Pod 会忽略该关联

<details>
<summary>显示答案</summary>

**答案：A) 新 Pod 只会获得 Pod Identity 环境变量；运行中的 Pod 会保留其 IRSA 环境变量**

**说明：**

如 [将 EKS 节点 IAM 权限迁移到 IRSA 和 Pod Identity](../../security/17-eks-workload-identity-migration.md#irsa-and-pod-identity-compared) 中所验证的，当两种设置同时存在时，EKS webhook 只会向新 Pod 注入 `AWS_CONTAINER_CREDENTIALS_FULL_URI` 和 `AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE`。运行中的 Pod 会保留其 IRSA 环境变量，直到 Pod 被重新创建，因此应通过受控滚动更新进行切换，并移除不再使用的注释。`get-caller-identity` 的结果即使显示相同的角色，也无法区分这两种机制，因此应检查注入的环境变量名称。

</details>
