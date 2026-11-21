# EKS 工作负载 IAM 迁移测验

> **最后更新**：2026年11月21日

[阅读工作簿并观看实时演示](../../security/17-eks-workload-identity-migration.md)

### 1. 将应用的 S3 权限附加到节点 IAM 角色上，主要问题是什么？

- A) S3 请求会变慢
- B) 该节点上所有能够访问 IMDS 的 Pod 都会使用相同的权限
- C) 节点将无法再加入集群
- D) S3 存储桶会变成公开状态

<details>
<summary>显示答案</summary>

**答案：B) 该节点上所有能够访问 IMDS 的 Pod 都会使用相同的权限**

**解释**：节点角色通过实例配置文件附加到整个节点。当跳数限制为 2 或更大时，普通 Pod 可以通过 IMDSv2 获取节点角色凭证。CloudTrail 只记录节点实例会话，因此很难区分各个工作负载。

</details>

### 2. 在 AWS SDK 的默认凭证链中，IRSA 和 Pod Identity 提供程序相对于 IMDS 位于什么位置？

- A) IMDS 排在最前面
- B) IRSA（Web 身份）和 Pod Identity（容器提供程序）都排在 IMDS 前面
- C) 顺序是随机的
- D) 只有 Pod Identity 排在 IMDS 前面

<details>
<summary>显示答案</summary>

**答案：B) IRSA（Web 身份）和 Pod Identity（容器提供程序）都排在 IMDS 前面**

**解释**：环境变量、Web 身份令牌和容器凭证提供程序都排在 IMDS 前面。EKS 注入了这些变量的新 Pod 无需更改代码就会使用新角色；没有注入任何变量的 Pod 则会回退到通过 IMDS 获取节点角色。

</details>

### 3. 为什么 STS 可以信任 IRSA 中投射的令牌？

- A) 令牌包含 IAM 访问密钥
- B) 集群发行方已注册为 IAM OIDC 提供程序，且角色信任策略会检查 `aud` 和 `sub`
- C) Pod Identity Agent 会对令牌签名
- D) 节点角色会代表 Pod 调用 STS

<details>
<summary>显示答案</summary>

**答案：B) 集群发行方已注册为 IAM OIDC 提供程序，且角色信任策略会检查 `aud` 和 `sub`**

**解释**：STS 的 `AssumeRoleWithWebIdentity` 会使用通过 OIDC 提供程序注册的发行方密钥验证令牌签名，并检查信任条件：`aud` 为 `sts.amazonaws.com`，`sub` 为 `system:serviceaccount:<namespace>:<serviceaccount>`。

</details>

### 4. 使用 Pod Identity 时，节点角色上必须保留哪项权限？

- A) 应用的 S3 读取权限
- B) `sts:AssumeRoleWithWebIdentity`
- C) 供 Agent 调用 EKS Auth 的 `eks-auth:AssumeRoleForPodIdentity`（属于 `AmazonEKSWorkerNodePolicy`）
- D) 完全不需要任何权限

<details>
<summary>显示答案</summary>

**答案：C) 供 Agent 调用 EKS Auth 的 `eks-auth:AssumeRoleForPodIdentity`（属于 `AmazonEKSWorkerNodePolicy`）**

**解释**：Pod Identity Agent 使用此节点角色权限调用 EKS Auth。应用的业务权限应配置在关联中指定的 Pod Identity 角色上。

</details>

### 5. 在演示的 `diff` 中，IRSA 令牌和 Pod Identity 令牌之间哪个声明不同？

- A) `iss`
- B) `aud`
- C) `exp`
- D) 两者完全相同

<details>
<summary>显示答案</summary>

**答案：B) `aud`**

**解释**：两者都是由同一集群发行方签名的 ServiceAccount 令牌。IRSA 令牌的受众是 `sts.amazonaws.com`；Pod Identity 令牌的受众是 `pods.eks.amazonaws.com`。`sub` 会因 ServiceAccount 不同而异。

</details>

### 6. 哪种方法可以让一个 IAM 角色用于十个新集群，而无需更改信任策略？

- A) IRSA
- B) EKS Pod Identity
- C) 两者都不需要更改
- D) 两者都需要针对每个集群进行修改

<details>
<summary>显示答案</summary>

**答案：B) EKS Pod Identity**

**解释**：Pod Identity 角色只信任 `pods.eks.amazonaws.com`；关联和会话标签用于限定集群范围。IRSA 则需要为每个集群配置一个 OIDC 提供程序和一条信任声明，而默认 2,048 个字符的信任策略通常只能容纳约四个绑定。

</details>

### 7. 在 Fargate 上运行的 Pod 需要工作负载角色。你应该使用哪种方法？

- A) EKS Pod Identity
- B) IRSA
- C) 节点角色
- D) 两种方法都不可用

<details>
<summary>显示答案</summary>

**答案：B) IRSA**

**解释**：EKS Pod Identity 仅支持 EKS 中的 Linux EC2 节点。在 Fargate、Windows EC2 节点、Outposts 和 EKS Anywhere 上使用 IRSA。

</details>

### 8. 你创建了一个关联并立即执行了滚动更新，但新 Pod 仍在使用节点角色。最可能的原因是什么？

- A) 存储桶策略拒绝了请求
- B) 关联尚未应用于 Pod 准入，因此没有注入任何内容
- C) Pod Identity Agent 阻止了 IMDS
- D) 还需要 IRSA 注解

<details>
<summary>显示答案</summary>

**答案：B) 关联尚未应用于 Pod 准入，因此没有注入任何内容**

**解释**：关联最终会保持一致，但可能需要几秒钟。在演示的第一次预演中，创建关联后立即执行滚动更新，没有发生注入；第二次预演中，注入在 5 秒后才出现。滚动更新前，使用 `kubectl create --dry-run=server` 检查 Pod 模板。

</details>

### 9. 你为一个已有 IRSA 注解的 ServiceAccount 添加了 Pod Identity 关联，然后创建了一个新 Pod。新 Pod 会使用哪种凭证？

- A) Pod Identity：Webhook 只注入 Pod Identity 变量
- B) IRSA：Web 身份提供程序在凭证链中优先
- C) 每个请求交替使用两者
- D) 由于冲突，Pod 无法启动

<details>
<summary>显示答案</summary>

**答案：A) Pod Identity：Webhook 只注入 Pod Identity 变量**

**解释**：建立关联后，EKS Webhook 只会向新 Pod 注入 `AWS_CONTAINER_CREDENTIALS_FULL_URI` 和 `AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE`，而不会注入 IRSA 变量，演示集群上的 dry-run 结果证实了这一点。只有在两组变量同时存在时，凭证链顺序（B）才会起作用；在建立关联前创建的 Pod 会继续使用 IRSA，直到重新创建。

</details>

### 10. 移除节点角色的 S3 策略后，旧版 Pod 的读取请求立即被拒绝。你能宣布迁移完成了吗？

- A) 能，一次拒绝就足以定论
- B) 不能，IAM 更改最终才会保持一致，结果可能在几分钟内混杂，因此要继续观察
- C) 能，只要节点重启即可
- D) 不能，必须删除节点角色

<details>
<summary>显示答案</summary>

**答案：B) 不能，IAM 更改最终才会保持一致，结果可能在几分钟内混杂，因此要继续观察**

**解释**：在演示中，旧版 Pod 在 13 秒后被拒绝，但大约 4.5 分钟后又出现了两次允许的读取。应观察数分钟，包括计划任务的运行情况，并保留策略的精确副本以便回滚。

</details>
