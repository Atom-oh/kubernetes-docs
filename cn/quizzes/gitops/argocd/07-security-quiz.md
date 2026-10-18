# ArgoCD 安全测验

本测验用于测试您对 ArgoCD 安全功能和最佳实践的理解。

1. 默认情况下，ArgoCD 如何处理 Git 存储库中的 Secret？
   - A) 它会自动加密它们
   - B) 它不会自动加密 Git 中的 Secret
   - C) 它使用 Kubernetes Secrets API
   - D) 它需要一个 secrets manager

<details>
<summary>显示答案</summary>

**答案：B) 它不会自动加密 Git 中的 Secret**

**说明：**
ArgoCD 本身不提供 Secret 加密。Sealed Secrets/SOPS 在 Git 中存储密文。ESO/Vault 集成则可以存储外部引用并获取 Secret 值；它们不会自动加密 Git 文件。Base64 不是加密。

</details>

2. 哪种工具使用控制器公钥加密 Kubernetes Secrets？
   - A) SOPS
   - B) Sealed Secrets
   - C) Vault
   - D) KMS

<details>
<summary>显示答案</summary>

**答案：B) Sealed Secrets**

**说明：**
Sealed Secrets 使用控制器密钥对。默认的严格作用域还会绑定名称和 namespace，而解密的信任边界取决于密钥的持有者。加密后的 SealedSecret 可以安全地存储在 Git 中，并由集群中的 Sealed Secrets controller 解密。

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
Dex 是一个提供 OpenID Connect (OIDC) 身份验证的身份服务。它通过 OIDC 对接 LDAP、SAML、GitHub 等身份来源。Argo CD 直接使用 OIDC 时并不总是需要 Dex。

</details>

4. 如何限制 Application 管理的命名空间级资源类型？
   - A) 使用 Kubernetes ResourceQuotas
   - B) 使用 AppProject 的 namespaceResourceBlacklist 或 namespaceResourceWhitelist
   - C) 仅更改 Pod 的 requests/limits
   - D) 在 ArgoCD 中无法实现

<details>
<summary>显示答案</summary>

**答案：B) 使用 AppProject 的 namespaceResourceBlacklist 或 namespaceResourceWhitelist**

**说明：**
AppProject 可以定义 `namespaceResourceBlacklist`（拒绝特定资源）或 `namespaceResourceWhitelist`（仅允许特定资源），以控制命名空间级资源类型。集群级资源使用单独的列表，而且这不会像准入策略一样检查 Pod 的特权设置。

</details>

5. 暴露 ArgoCD API server 的推荐做法是什么？
   - A) 使用基本身份验证将其公开暴露
   - B) 使用带 TLS 和身份验证的受保护访问路径
   - C) 在没有任何身份验证的情况下运行它
   - D) 只能通过 port-forwarding 访问它

<details>
<summary>显示答案</summary>

**答案：B) 使用带 TLS 和身份验证的受保护访问路径**

**说明：**
通过 Ingress/Gateway 或受保护的内部路径提供经过身份验证的 TLS 访问。仅在前端终止 TLS，并不能验证后端 TLS。对于敏感环境，建议采取 VPN 访问或 IP 白名单等额外措施。

</details>
