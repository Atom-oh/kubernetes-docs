# IAM 身份验证流程测验

本测验检查你对 Lattice IAM Auth 四阶段流程、SigV4 签名易错点和 403 诊断的理解。

## 单选题

1. 使用 SigV4 对 VPC Lattice 数据平面请求签名时，应使用哪个服务名称？
   - A) `vpc-lattice`
   - B) `vpc-lattice-svcs`
   - C) `lattice`
   - D) `execute-api`

<details>

<summary>显示答案</summary>

**答案：B) `vpc-lattice-svcs`**

**解释：**
`vpc-lattice-svcs` 是数据平面请求的签名服务名称。它很容易与 `vpc-lattice` 混淆，后者是 Lattice 控制平面 API（用于创建服务、listener 等）的服务名称。服务名称是签名密钥派生过程的输入（secret key → date → region → service name → 终止字符串，共四次链式 HMAC-SHA256 运算）；名称错误就会导致签名验证失败。该名称也与服务 DNS 名称一致，格式为 `...vpc-lattice-svcs.<region>.on.aws`。
</details>

2. Lattice IAM Auth 下，403 最常见的原因是什么？
   - A) Lattice service 的身份验证策略中未包含该主体
   - B) 调用方 IAM Role 的基于身份的策略缺少 `vpc-lattice-svcs:Invoke`
   - C) 节点 Security Group 未允许 Lattice 前缀列表
   - D) Target Group 健康检查失败

<details>

<summary>显示答案</summary>

**答案：B) 调用方 IAM Role 的基于身份的策略缺少 `vpc-lattice-svcs:Invoke`**

**解释：**
人们很容易以为“service 的身份验证策略允许这个 Role 就够了”，但调用方 Role 自身也必须具有 Invoke 权限；仅有资源策略仍无法访问。实际错误消息通常以 `because no identity-based policy allows the vpc-lattice-svcs:Invoke action` 结尾，因此遇到 403 时应先查看这部分内容。C 会导致连接失败或超时，而不是 403。
</details>

3. 添加自定义域名后立即出现 403，首先应检查什么？
   - A) Target Group 的协议设置
   - B) `Host` 请求头：SigV4 总会对 Host 签名，签名时使用的 Host 必须与实际请求的 Host 一致
   - C) 是否超过 Lattice 配额
   - D) VPC 的 DNS 解析设置

<details>

<summary>显示答案</summary>

**答案：B) `Host` 请求头：SigV4 总会对 Host 签名，签名时使用的 Host 必须与实际请求的 Host 一致**

**解释：**
SigV4 始终会把 `Host` 请求头纳入签名。关联自定义域名后，客户端会向该域名发送请求并必须使用该值签名；如果签名逻辑仍使用 Lattice 生成的域名，签名就会不匹配。此问题会在关联自定义域名时出现，而不是迁移开始时，因此容易遗漏。引入自定义域名时，应一并确定 SNI 控制、签名所用的 Host 值和证书管理方案。
</details>

4. 如果“只有某台特定节点上的 Pod 会间歇性收到 403”，最可能的原因是什么？
   - A) 该节点上的 Security Group 配置错误
   - B) 该节点的时钟同步问题：`x-amz-date` 会参与签名，而 SigV4 的容差约为 5 分钟
   - C) Gateway API Controller 没有在该节点上运行
   - D) 该节点的 kubelet 版本过旧

<details>

<summary>显示答案</summary>

**答案：B) 该节点的时钟同步问题：`x-amz-date` 会参与签名，而 SigV4 的容差约为 5 分钟**

**解释：**
AWS 一般性的 SigV4 指南指出，大多数请求必须在其时间戳前后五分钟内到达。应检查实际服务错误和 UTC 时钟；不要把这当成单独实测的 Lattice 专属保证。
</details>

5. 从签名到 Lattice 验证之间，还需要检查什么？
   - A) 多个代理会增加延迟
   - B) 改变规范化后的签名字段会导致验证失败；Lattice 要求使用 UNSIGNED-PAYLOAD，因此还需要通过 TLS/应用层控制保护请求体完整性
   - C) 代理无法缓存凭证
   - D) 一个 IAM Role 只能附加到一个代理

<details>

<summary>显示答案</summary>

**答案：B) 改变规范化后的签名字段会导致验证失败；Lattice 要求使用 UNSIGNED-PAYLOAD，因此还需要通过 TLS/应用层控制保护请求体完整性**

**解释：**
签名中的 Host/path/query 值必须与请求一致。由于会进行规范排序，等价的 query 参数顺序不一定构成变化。Lattice 不支持请求载荷签名；必须要求使用 `x-amz-content-sha256: UNSIGNED-PAYLOAD` 请求头。
</details>

6. 为什么集群内部的流量可能不受身份验证策略约束？
   - A) 身份验证策略不支持 IPv6 流量
   - B) 如果客户端直接调用 Kubernetes Service DNS，就会绕过 Lattice，身份验证策略不会被评估
   - C) 身份验证策略只适用于跨账户调用
   - D) Gateway API Controller 尚未协调该策略

<details>

<summary>显示答案</summary>

**答案：B) 如果客户端直接调用 Kubernetes Service DNS，就会绕过 Lattice，身份验证策略不会被评估**

**解释：**
AWS Gateway API Controller 文档对此有明确说明：`IAMAuthPolicy` 只会对经过 Gateway、HTTPRoute 和 GRPCRoute 的流量执行授权。向 `http://svc.ns.svc.cluster.local` 发送请求会绕过 Lattice，因此不会评估任何策略。迁移期间两条路径同时存在，授权策略会在部分路径上生效、在另一些路径上不生效；此时需要 NetworkPolicy 等补偿控制。另一个常见原因是 `authType` 设为 `NONE` 而非 `AWS_IAM`。
</details>

7. 从 AS-IS（App Mesh + SPIRE mTLS）迁移到 TO-BE（Lattice IAM Auth）后，身份验证的“作用范围”和“方向性”如何变化？
   - A) 面向连接的双向认证 → 面向请求的双向认证
   - B) 面向连接的双向相互认证 → 面向请求的单向认证（客户端证明身份）加 TLS 服务器证书
   - C) 面向请求的单向认证 → 面向连接的双向认证
   - D) 作用范围和方向性都不变

<details>

<summary>显示答案</summary>

**答案：B) 面向连接的双向相互认证 → 面向请求的单向认证（客户端证明身份）加 TLS 服务器证书**

**解释：**
mTLS 会在建立连接时使用双方的 SVID 对彼此进行身份验证。Lattice IAM Auth 会对每个请求验证调用方的 SigV4 签名，并可应用 path/method/header 策略条件。SigV4 保护规范化后的签名字段；Lattice 要求使用 `UNSIGNED-PAYLOAD`，且不支持载荷签名。应通过 TLS 保护请求体，并分别评估凭证窃取、请求时效性和重放问题；不要声称请求签名总能阻止连接劫持。在 HTTPS listener 设计中，服务器身份通过 TLS 服务器证书验证，而不是使用对等端的 SPIFFE 身份。
</details>
