# ArgoCD 安全测验

本测验用于测试您对 ArgoCD 安全功能和最佳实践的理解。

1. 默认情况下，ArgoCD 如何处理 Git 存储库中的 Secret？
   - A) 它会自动加密它们
   - B) 它不会对 Secret 进行特殊处理——它们以纯文本形式存储
   - C) 它使用 Kubernetes Secrets API
   - D) 它需要一个 secrets manager

<details>
<summary>显示答案</summary>

**答案：B) 它不会对 Secret 进行特殊处理——它们以纯文本形式存储**

**说明：**
ArgoCD 本身不提供 Secret 加密。Git 中的 Secret 应在提交到 Git 前使用 Sealed Secrets、SOPS、External Secrets Operator 或 Vault 等工具加密。

</details>

2. 哪种工具使用集群特定的密钥加密 Kubernetes Secrets？
   - A) SOPS
   - B) Sealed Secrets
   - C) Vault
   - D) KMS

<details>
<summary>显示答案</summary>

**答案：B) Sealed Secrets**

**说明：**
Sealed Secrets 使用集群特定的密钥对来加密 Secret。加密后的 SealedSecret 可以安全地存储在 Git 中，并由集群中的 Sealed Secrets controller 解密。

</details>

3. ArgoCD 的 Dex 组件的用途是什么？
   - A) Container image 扫描
   - B) OpenID Connect 身份验证和 SSO
   - C) Network policy 强制执行
   - D) Secret 轮换

<details>
<summary>显示答案</summary>

**答案：B) OpenID Connect 身份验证和 SSO**

**说明：**
Dex 是一个提供 OpenID Connect (OIDC) 身份验证的身份服务。它使 ArgoCD 能够与各种身份提供商（LDAP、SAML、GitHub 等）集成，以实现单点登录。

</details>

4. 如何限制 Application 可以创建的 Kubernetes 资源？
   - A) 使用 Kubernetes ResourceQuotas
   - B) 使用 AppProject 的 namespaceResourceBlacklist 或 namespaceResourceWhitelist
   - C) 使用 Pod Security Policies
   - D) 在 ArgoCD 中无法实现

<details>
<summary>显示答案</summary>

**答案：B) 使用 AppProject 的 namespaceResourceBlacklist 或 namespaceResourceWhitelist**

**说明：**
AppProject 可以定义 `namespaceResourceBlacklist`（拒绝特定资源）或 `namespaceResourceWhitelist`（仅允许特定资源），以控制 Application 可以管理的 Kubernetes 资源类型。

</details>

5. 公开 ArgoCD API server 的推荐做法是什么？
   - A) 使用基本身份验证将其公开暴露
   - B) 将其保留为内部访问，并使用带 TLS 和身份验证的 ingress
   - C) 在没有任何身份验证的情况下运行它
   - D) 只能通过 port-forwarding 访问它

<details>
<summary>显示答案</summary>

**答案：B) 将其保留为内部访问，并使用带 TLS 和身份验证的 ingress**

**说明：**
ArgoCD API server 应通过配置 TLS termination 和适当身份验证（SSO/OIDC）的 ingress 公开。对于敏感环境，建议采取 VPN 访问或 IP 白名单等额外措施。

</details>
