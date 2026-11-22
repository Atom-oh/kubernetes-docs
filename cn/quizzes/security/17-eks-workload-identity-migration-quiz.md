# EKS 工作负载 IAM 迁移测验

> **最后更新**：2026年11月21日

[阅读工作簿并观看现场演示](../../security/17-eks-workload-identity-migration.md)

### 1. 将应用的 S3 权限附加到节点 IAM 角色上，主要问题是什么？

- A) S3 请求会变慢
- B) 该节点上所有能够访问 IMDS 的 Pod 都会使用相同的权限
- C) 节点将无法再加入集群
- D) S3 存储桶会变成公开状态

<details>
<summary>显示答案</summary>

**答案：B) 该节点上所有能够访问 IMDS 的 Pod 都会使用相同的权限**

**说明：** 节点角色通过实例配置文件附加到整个节点上。跳数限制为 2 或更高时，普通 Pod 可以通过 IMDSv2 获取节点角色凭证。CloudTrail 只记录节点实例会话，因此很难区分各个工作负载。

</details>

### 2. 在 AWS SDK 默认凭证链中，IRSA 和 Pod Identity 提供程序相对于 IMDS 位于什么位置？

- A) IMDS 位于最前面
- B) IRSA（Web 身份）和 Pod Identity（容器提供程序）都位于 IMDS 之前
- C) 顺序是随机的
- D) 只有 Pod Identity 位于 IMDS 之前

<details>
<summary>显示答案</summary>

**答案：B) IRSA（Web 身份）和 Pod Identity（容器提供程序）都位于 IMDS 之前**

**说明：** 环境变量密钥、Web 身份令牌和容器凭证提供程序都先于 IMDS。EKS 注入了变量的新 Pod 无需更改代码即可使用新角色；没有注入任何内容的 Pod 则会回退到通过 IMDS 获取的节点角色。

</details>

### 3. 为什么 STS 能信任 IRSA 中投射的令牌？

- A) 令牌包含 IAM 访问密钥
- B) 集群颁发者已注册为 IAM OIDC 提供程序，并且角色信任策略会检查 `aud` 和 `sub`
- C) Pod Identity Agent 对令牌进行了签名
- D) 节点角色代表 Pod 调用 STS

<details>
<summary>显示答案</summary>

**答案：B) 集群颁发者已注册为 IAM OIDC 提供程序，并且角色信任策略会检查 `aud` 和 `sub`**

**说明：** STS `AssumeRoleWithWebIdentity` 会使用通过 OIDC 提供程序注册的颁发者密钥验证令牌签名，并检查信任条件：`aud` 为 `sts.amazonaws.com`，`sub` 为 `system:serviceaccount:<namespace>:<serviceaccount>`。

</details>

### 4. 使用 Pod Identity 时，节点角色上必须保留哪项权限？

- A) 应用的 S3 读取权限
- B) `sts:AssumeRoleWithWebIdentity`
- C) 供 Agent 调用 EKS Auth 的 `eks-auth:AssumeRoleForPodIdentity`（属于 `AmazonEKSWorkerNodePolicy`）
- D) 完全不需要任何权限

<details>
<summary>显示答案</summary>

**答案：C) 供 Agent 调用 EKS Auth 的 `eks-auth:AssumeRoleForPodIdentity`（属于 `AmazonEKSWorkerNodePolicy`）**

**说明：** Pod Identity Agent 使用此节点角色权限调用 EKS Auth。应用的业务权限应授予关联中指定的 Pod Identity 角色。

</details>

### 5. 在演示的 `diff` 中，哪个声明区分了 IRSA 令牌和 Pod Identity 令牌？

- A) `iss`
- B) `aud`
- C) `exp`
- D) 两者完全相同

<details>
<summary>显示答案</summary>

**答案：B) `aud`**

**说明：** 两者都是由同一集群颁发者签名的 ServiceAccount 令牌。IRSA 令牌的受众是 `sts.amazonaws.com`；Pod Identity 令牌的受众是 `pods.eks.amazonaws.com`。`sub` 会因 ServiceAccount 不同而异。

</details>

### 6. 哪种方法可以让一个 IAM 角色为十个新集群提供服务，而无需更改信任策略？

- A) IRSA
- B) EKS Pod Identity
- C) 两者都不需要更改
- D) 两者都需要逐个集群修改

<details>
<summary>显示答案</summary>

**答案：B) EKS Pod Identity**

**说明：** Pod Identity 角色只信任 `pods.eks.amazonaws.com`；关联和会话标签用于设置集群范围。IRSA 则需要为每个集群配置 OIDC 提供程序和信任声明，而默认 2,048 个字符的信任策略通常只能容纳约四个绑定。

</details>

### 7. 在 Fargate 上运行的 Pod 需要工作负载角色。你会使用哪种方法？

- A) EKS Pod Identity
- B) IRSA
- C) 节点角色
- D) 两者都不适用

<details>
<summary>显示答案</summary>

**答案：B) IRSA**

**说明：** EKS Pod Identity 支持 EKS 中的 Linux EC2 节点和 EKS Hybrid Nodes（需要配置 Agent 的混合节点 DaemonSet 和节点凭证文件）。Fargate、Windows EC2 节点、Outposts 和 EKS Anywhere 应使用 IRSA。

</details>

### 8. 你创建了关联并立即推出新版本，但新 Pod 仍在使用节点角色。最可能的原因是什么？

- A) 存储桶策略拒绝了请求
- B) 关联尚未在 Pod 准入时生效，因此没有注入任何内容
- C) Pod Identity Agent 阻止了 IMDS
- D) 还需要 IRSA 注释

<details>
<summary>显示答案</summary>

**答案：B) 关联尚未在 Pod 准入时生效，因此没有注入任何内容**

**说明：** 关联最终会保持一致，可能需要几秒钟。在演示的第一次预演中，创建关联后立即推出新版本，没有注入任何内容；第二次预演中，注入在 5 秒后才出现。推出前，使用 `kubectl create --dry-run=server` 检查 Pod 模板。

</details>

### 9. 你为已经带有 IRSA 注释的 ServiceAccount 添加了 Pod Identity 关联，然后创建一个新 Pod。新 Pod 会使用哪种凭证？

- A) Pod Identity：Webhook 只注入 Pod Identity 变量
- B) IRSA：Web 身份提供程序在凭证链中优先
- C) 每个请求轮流使用两者
- D) 由于冲突，Pod 无法启动

<details>
<summary>显示答案</summary>

**答案：A) Pod Identity：Webhook 只注入 Pod Identity 变量**

**说明：** 添加关联后，EKS Webhook 只会向新 Pod 注入 `AWS_CONTAINER_CREDENTIALS_FULL_URI` 和 `AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE`，而不会注入 IRSA 变量；演示集群上的 dry-run 结果也证实了这一点。只有两组变量都存在时，凭证链顺序（B）才会起作用；在关联创建前已创建的 Pod 会继续使用 IRSA，直到重新创建。

</details>

### 10. 移除节点角色的 S3 策略后，旧版 Pod 立即遭到读取拒绝。你能宣布迁移完成了吗？

- A) 能，单次拒绝就足以确认
- B) 不能，IAM 更改最终才会保持一致，几分钟内结果可能混杂，因此要继续观察
- C) 能，节点重启后就可以
- D) 不能，必须删除节点角色

<details>
<summary>显示答案</summary>

**答案：B) 不能，IAM 更改最终才会保持一致，几分钟内结果可能混杂，因此要继续观察**

**说明：** 在演示中，旧版 Pod 在 13 秒后遭到拒绝，但约 4.5 分钟后又出现了两次获准的读取。应观察数分钟并涵盖计划任务，同时保留策略的精确副本以便回滚。

</details>
