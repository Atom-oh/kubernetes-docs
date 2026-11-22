# IRSA 和 OIDC 提供商测验

> **最后更新**：2026年11月21日

本测验用于检查你对 [IRSA 和 OIDC 提供商](../../eks/05-eks-security-irsa-oidc.md)的理解。

## 测验概览
- 集群 OIDC 颁发者和 IAM OIDC 提供商
- IRSA 令牌交换
- 角色信任条件
- 发现文档/JWKS 和密钥轮换

## 选择题

### 1. EKS 集群会发布 OIDC 颁发者和公钥签名密钥。在工作负载能够代入角色之前，IRSA 还需要什么？

- A) 无需其他条件；仅凭颁发者端点即可授权代入角色
- B) 一个关联的外部 OIDC 身份提供商，用于 Kubernetes 用户登录
- C) 一个 IAM OIDC 提供商、一个具有匹配信任关系的角色，以及兼容的 SDK
- D) 将工作负载所需的 S3 权限添加到节点 IAM 角色

<details>
<summary>显示答案</summary>

**答案：C) 一个 IAM OIDC 提供商、一个具有匹配信任关系的角色，以及兼容的 SDK**

**解释：**

EKS 发布的集群 OIDC 颁发者端点本身不会创建 IAM OIDC 提供商，也不会授权代入角色。IRSA 需要在角色所属账户中配置预期的 IAM OIDC 提供商、一个信任该提供商且具有正确颁发者/主体/受众条件的角色，以及兼容的 SDK。用于 Kubernetes 用户登录的外部 OIDC 提供商与 IRSA 是两回事。

</details>

### 2. 使用 IRSA 时，SDK 会调用哪个 API，将投射的 Web 身份令牌交换为临时 AWS 凭证？

- A) EKS Auth AssumeRoleForPodIdentity
- B) STS AssumeRoleWithWebIdentity
- C) IMDSv2 实例配置文件凭证
- D) STS GetSessionToken

<details>
<summary>显示答案</summary>

**答案：B) STS AssumeRoleWithWebIdentity**

**解释：**

IRSA webhook 会向符合条件的 Pod 添加投射令牌和角色配置，SDK 随后使用 AssumeRoleWithWebIdentity 将令牌交给 STS 进行交换。STS 会验证颁发者、签名、令牌和角色信任关系，然后返回临时凭证。AssumeRoleForPodIdentity 是 Pod Identity 代理调用的 EKS Auth API。Kubernetes 会轮换投射令牌，而 SDK 会按照不同的生命周期刷新 AWS 凭证。

</details>

### 3. 在范围受限的 IRSA 信任示例中，哪些条件会将角色限制为 `security-demo/irsa-reader` ServiceAccount？

- A) `aws:RequestTag/kubernetes-service-account` 会话标签条件
- B) 将 `Principal.Service` 设置为 `pods.eks.amazonaws.com`
- C) 将 IAM 角色准确命名为与 ServiceAccount 相同的名称
- D) 对 `<issuer>:sub` 和 `<issuer>:aud` 使用 StringEquals 条件

<details>
<summary>显示答案</summary>

**答案：D) 对 `<issuer>:sub` 和 `<issuer>:aud` 使用 StringEquals 条件**

**解释：**

IRSA 角色使用 IAM OIDC 提供商作为其 `Federated` 主体，并允许 `sts:AssumeRoleWithWebIdentity`。以完整颁发者主机名/路径为前缀的 StringEquals 条件会绑定 ServiceAccount 和受众：`:sub` 为 `system:serviceaccount:security-demo:irsa-reader`，而 `:aud` 为 `sts.amazonaws.com`。`aws:RequestTag/...` 条件和 `pods.eks.amazonaws.com` 属于 Pod Identity 信任关系。一个角色可以信任多个明确允许的 ServiceAccount 或颁发者；IRSA 不强制要求每个 ServiceAccount 对应一个角色。

</details>

### 4. 如果你要构建一个验证器，通过获取集群 OIDC 发现文档和 JWKS 来验证令牌，以下哪项说法正确？

- A) 根据 Cache-Control 缓存密钥，并处理密钥轮换和未知的 kid 值
- B) 仅获取一次 JWKS，将其硬编码在验证器中并永久重复使用
- C) 将成功获取 JWKS 视为令牌签名已验证的证明
- D) 跳过将发现文档中的颁发者与集群颁发者进行比较

<details>
<summary>显示答案</summary>

**答案：A) 根据 Cache-Control 缓存密钥，并处理密钥轮换和未知的 kid 值**

**解释：**

页面中的诊断脚本会获取公开的发现文档/JWKS，并检查发现文档中的颁发者和 HTTPS 方案；它既不会验证工作负载令牌签名，也不会验证 IAM 权限。自动化验证器必须根据 Cache-Control 缓存密钥，并使用经过审核的 JWT 库处理签名密钥轮换和未知的 kid 值。EKS 每七天轮换一次 OIDC 签名密钥。

</details>

### 5. 没有互联网出站访问的验证器如何访问集群 OIDC 发现文档和 JWKS？

- A) 创建 EKS 管理 API 接口端点，该端点也会提供 OIDC 服务
- B) 需要时，临时在安全组中开放到 0.0.0.0/0 的出站访问
- C) 使用 `oidc-eks` PrivateLink 接口端点访问发现文档和 JWKS
- D) 不准备任何网络路径，因为 IRSA 从不需要 JWKS

<details>
<summary>显示答案</summary>

**答案：C) 使用 `oidc-eks` PrivateLink 接口端点访问发现文档和 JWKS**

**解释：**

目前，EKS 支持用于集群 OIDC 发现文档/JWKS 的 PrivateLink 接口端点 `com.amazonaws.region-code.oidc-eks`，供没有互联网出站访问的验证器使用。请确认该端点的区域/DNS 要求；EKS 管理 API 端点是另一项服务。

</details>
