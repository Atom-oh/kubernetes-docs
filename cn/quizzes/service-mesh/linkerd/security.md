# Linkerd 安全测验

基于[安全指南](../../../service-mesh/linkerd/04-security.md)，于 2026 年 9 月 11 日审阅。

### 1. Linkerd 如何为网格启用 mTLS？

- A. 每个服务都必须自行实现 Linkerd TLS
- B. 在参与网格的 Pod 之间，自动保护符合条件的 TCP 流量
- C. 任意 Kubernetes Secret 都能加密所有网络路径
- D. 所有 UDP 流量都会自动受到保护

<details>
<summary>显示答案</summary>

**答案：B**

**说明：** 两端的代理都必须参与通信，并且信任相应的证书链。未加入网格的端点和被跳过的端口不会自动获得 Linkerd mTLS 保护。默认配置仍可能接受入站明文流量；应使用适当的策略要求客户端通过身份验证。

</details>

### 2. Server 资源会选择什么？

- A. 外部 DNS 记录
- B. 其命名空间内匹配 Pod 上的入站端口和协议
- C. 证书 Secret
- D. 出站负载均衡算法

<details>
<summary>显示答案</summary>

**答案：B**

**说明：** Server 会选择目标 Pod 和端口。应声明应用程序使用的端口，并避免多个 Server 的选择范围重叠。未匹配的流量默认会被拒绝，除非 `accessPolicy` 改变这一行为。在代理管理端口 4191 上创建 Server，也不会取消该管理端口绕过流量拦截的行为。

</details>

### 3. ServerAuthorization 中的 meshTLS.serviceAccounts 表示什么？

- A. 服务器自身的 serviceAccountName
- B. 获准访问的、经过身份验证的客户端 ServiceAccount
- C. 用来签发所有证书的账户
- D. 仅用于收集指标的账户

<details>
<summary>显示答案</summary>

**答案：B**

**说明：** 此授权规则允许匹配的网格客户端身份访问。其他授权规则也可能扩大访问范围。当前发布版本使用 ServerAuthorization/v1beta1；AuthorizationPolicy 也可以直接引用 ServiceAccount，无须依赖这种旧式授权规则。

</details>

### 4. 在 default-deny 模式下，如何放行业务流量？

- A. 所有请求仍会自动获准
- B. 定义目标，并配置匹配的授权规则
- C. 设置通用命名空间标签，就能允许任何调用方访问
- D. 任意 ConfigMap 白名单都足够

<details>
<summary>显示答案</summary>

**答案：B**

**说明：** Server 配合 AuthorizationPolicy 是当前可用的一种模式；ServerAuthorization 是较旧的替代方案。它们不是必须依次经过的处理流水线。在同一个 AuthorizationPolicy 中，多个必需的 `requiredAuthenticationRefs` 必须全部匹配；还要为探针访问配置适当的处理方式。

</details>

### 5. 应如何确定信任锚的有效期？

- A. 一律设为 24 小时
- B. 一律设为无限期
- C. 根据 CA 策略、计划轮换和恢复要求确定；CLI 的默认值为一年
- D. 每个集群都必须遵循统一的 1 至 10 年建议

<details>
<summary>显示答案</summary>

**答案：C**

**说明：** 可以手动配置有效期为十年的根证书，但这并不代表十年就是自动适用的最佳实践。应跟踪证书链中每张证书的到期时间，并确保签发者的续期安排和有效期符合其 CA 的要求。轮换根证书时，需要安排重叠期，并将新信任锚分发给所有使用方，包括关联集群。

</details>

### 6. ServerAuthorization 中的 client.unauthenticated:true 允许什么？

- A. 只允许通配符匹配到的已验证身份
- B. 无须网格身份验证的客户端
- C. 只允许携带特殊外部标头的调用方
- D. 无论目标是什么，都只允许指定的就绪检查 URL

<details>
<summary>显示答案</summary>

**答案：B**

**说明：** 此设置允许其目标范围内的客户端在不经过网格身份验证的情况下访问，并不会自动将访问范围限制在健康检查路径。`meshTLS.identities:["*"]` 含义不同：它会广泛允许网格身份，但仍要求客户端通过网格身份验证。

</details>

### 7. 在相同信任根下续期有效的签发者证书时，通常会发生什么？

- A. 每个代理都必须立即重启
- B. 信任根也必须始终更换
- C. 负责人更新签发者 Secret；Identity 会验证并重新加载文件，代理则按正常流程续期叶证书
- D. 整个集群都会重启

<details>
<summary>显示答案</summary>

**答案：C**

**说明：** 应检查 `IssuerUpdated` 状态，并调查被跳过或无效的更新。如果证书链仍然有效，现有叶证书可以继续使用旧签发者，直到正常续期时再更换。每次更新签发者都无须一律重启 Identity；信任锚轮换是另一项需要分阶段执行的流程。

</details>

### 8. 哪种默认策略要求经过身份验证的网格客户端（包括受信任且配置适当的多集群客户端）？

- A. deny
- B. all-unauthenticated
- C. all-authenticated
- D. cluster-unauthenticated

<details>
<summary>显示答案</summary>

**答案：C**

**说明：** `all-authenticated` 要求客户端通过网格身份验证，但它并不是只允许特定调用方的白名单。仍需考虑明确配置的 Server 策略和授权规则；命名空间默认注解会在代理初始化时应用。

</details>

### 9. 使用 cert-manager 签发 Linkerd 的签名者证书时，需要满足什么条件？

- A. `isCA:false`
- B. `isCA:true`，并使用合适的 ECDSA P-256 凭证和有效证书链
- C. 任意叶证书只要具有数字签名用途即可
- D. 必须始终使用 RSA 私钥

<details>
<summary>显示答案</summary>

**答案：B**

**说明：** Identity 需要能够为工作负载证书签名的中间 CA。此外，应明确设置 `rotationPolicy`，验证 Secret 的格式和所有权，并检查 CA 的有效期。应确认 Identity 已加载签发结果。即使请求中写了 `isCA:true`，也不能据此断定通用 Vault 叶证书签名流程会提供 CA 证书。

</details>

### 10. linkerd viz edges 能显示什么？

- A. 每台边缘路由器的硬件状态
- B. 已观测到的资源连接及其 mTLS/安全状态
- C. 所有可能路径或空闲路径都已加密的证明
- D. 完整的终端用户身份验证审计记录

<details>
<summary>显示答案</summary>

**答案：B**

**说明：** SECURED 视图反映的是已观测到的连接，而不是完整的网络清单。可使用 `linkerd identity` 查看公开证书，并使用策略诊断和指标检查访问决策。不要将 CLI 中的显示结果等同于 Prometheus 中字面意义上的 TLS 标签值。

</details>

### 11. Linkerd 安全与应用程序安全如何配合？

- A. 网格 mTLS 消除了应用程序安全的必要性
- B. 网格工作负载和传输控制补充用户、租户及业务授权
- C. ServiceAccount 获准访问就能证明每个调用方都是管理员
- D. 网格会自动执行输入验证

<details>
<summary>显示答案</summary>

**答案：B**

**说明：** Linkerd 提供工作负载身份验证、符合条件的传输加密和入站授权。应用程序仍需验证用户凭证、权限和输入。网络及准入控制还应覆盖代理被绕过或工作负载未加入网格的情况。

</details>

### 12. 哪种指标需要应用程序级埋点或其他能够识别应用程序行为的数据源？

- A. 代理工作负载证书的到期时间
- B. 已观测到的缺少网格客户端身份的 HTTP 响应
- C. 应用程序登录失败次数
- D. 代理入站授权拒绝计数器

<details>
<summary>显示答案</summary>

**答案：C**

**说明：** Linkerd 无法自动获知应用程序的登录结果。为 Linkerd 本身设置告警时，应区分叶证书到期时间戳与签发者 TTL 时长，使用按范围计算的流量比例速率，保留身份标签，并将缺失数据与空闲时没有流量的情况分开处理。

</details>
