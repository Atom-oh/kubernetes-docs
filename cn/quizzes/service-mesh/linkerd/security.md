# Linkerd 安全测验

本测验用于测试你对 Linkerd 安全功能的理解。

## 测验问题

### 1. 如何在 Linkerd 中启用 mTLS？

A. 需要为每个 Service 手动配置
B. 自动应用于所有 mesh 流量
C. 需要通过 Kubernetes Secret 配置
D. 必须按 namespace 启用

<details>
<summary>显示答案</summary>

**答案：B. 自动应用于所有 mesh 流量**

**说明：**
Linkerd 的核心价值之一是“默认安全”。mesh 中 Service 之间的所有流量都会自动应用 mTLS，无需任何配置。

</details>

### 2. Server 资源的作用是什么？

A. 定义外部服务器连接
B. 定义入站流量端口和协议
C. 存储服务器证书
D. 配置负载均衡器

<details>
<summary>显示答案</summary>

**答案：B. 定义入站流量端口和协议**

**说明：**
Server 资源为特定 Pod 定义入站流量。它使用 podSelector 指定目标 Pod，使用 port 指定端口，并使用 proxyProtocol 指定协议（HTTP/1、HTTP/2、gRPC、opaque）。

</details>

### 3. ServerAuthorization 中的 meshTLS.serviceAccounts 指定什么？

A. 服务器要使用的 ServiceAccount
B. 允许访问的客户端 ServiceAccount
C. 具有证书签发权限的 ServiceAccount
D. 具有指标收集权限的 ServiceAccount

<details>
<summary>显示答案</summary>

**答案：B. 允许访问的客户端 ServiceAccount**

**说明：**
ServerAuthorization 的 meshTLS.serviceAccounts 指定哪些客户端 ServiceAccount 可以访问 Server。只有使用指定 ServiceAccount 的 workload 才被允许访问。

</details>

### 4. 在 default-deny 策略模式下，如何允许流量？

A. 自动允许所有流量
B. 需要显式定义 ServerAuthorization
C. 通过 namespace label 允许
D. 在 ConfigMap 中配置白名单

<details>
<summary>显示答案</summary>

**答案：B. 需要显式定义 ServerAuthorization**

**说明：**
在 default-deny 模式下，默认拒绝所有流量。要允许流量，必须显式定义 Server 和 ServerAuthorization。这是一种零信任安全模型。

</details>

### 5. Trust Anchor 的建议有效期是多久？

A. 24 小时
B. 1 年
C. 1-10 年
D. 无限制

<details>
<summary>显示答案</summary>

**答案：C. 1-10 年**

**说明：**
Trust Anchor（Root CA）应在较长时间内保持有效。通常建议为 1-10 年。由于替换 Trust Anchor 较为复杂，因此应根据安全要求设置足够长的有效期。

</details>

### 6. 哪项 ServerAuthorization 设置允许未经身份验证的客户端（mesh 外部）？

A. `meshTLS.identities: ["*"]`
B. `unauthenticated: true`
C. `external: allowed`
D. `client: any`

<details>
<summary>显示答案</summary>

**答案：B. `unauthenticated: true`**

**说明：**
设置 `client.unauthenticated: true` 可允许未经过 mTLS 身份验证的客户端（mesh 外部）访问。这用于来自健康检查或 ingress 的流量。

</details>

### 7. 更新 Identity Issuer 证书时需要做什么？

A. 必须重启所有 proxy
B. 必须同时替换 Trust Anchor
C. 更新 Kubernetes Secret 并重启 Identity Controller
D. 需要完全重启 cluster

<details>
<summary>显示答案</summary>

**答案：C. 更新 Kubernetes Secret 并重启 Identity Controller**

**说明：**
更新 Identity Issuer 时：1) 使用新证书更新 Secret，2) 重启 Identity Controller。proxy 会使用新证书自动续期。如果 Trust Anchor 保持不变，则无需替换它。

</details>

### 8. 哪种策略模式仅允许来自 mesh 内部的 mTLS 流量？

A. deny
B. all-unauthenticated
C. all-authenticated
D. cluster-unauthenticated

<details>
<summary>显示答案</summary>

**答案：C. all-authenticated**

**说明：**
`all-authenticated` 模式仅允许来自 mesh 内部且经过 mTLS 身份验证的流量。来自 mesh 外部的未经身份验证的流量将被拒绝。

</details>

### 9. 与 Linkerd 集成时，cert-manager Certificate 资源中需要哪项设置？

A. isCA: false
B. isCA: true
C. usages: [digital signature]
D. algorithm: RSA

<details>
<summary>显示答案</summary>

**答案：B. isCA: true**

**说明：**
Linkerd Identity Issuer 充当中间 CA，因此 cert-manager Certificate 必须具有 `isCA: true`。该证书用于签署 workload 证书。

</details>

### 10. 可以使用 linkerd viz edges 命令验证什么？

A. 网络边缘路由器状态
B. Service 到 Service 的 mTLS 连接状态
C. cluster 边界策略
D. DNS 边缘缓存状态

<details>
<summary>显示答案</summary>

**答案：B. Service 到 Service 的 mTLS 连接状态**

**说明：**
`linkerd viz edges` 显示 Service 之间的连接（边），其中 SECURED 列表示 mTLS 状态。来自 mesh 外部的流量在 SECURED 中显示 X。

</details>

### 11. Linkerd 安全与应用程序安全之间的正确关系是什么？

A. Linkerd 处理所有安全问题，因此无需应用程序安全
B. Linkerd 处理传输层，应用程序处理业务逻辑安全
C. 仅应用程序安全就足够，Linkerd 安全是可选的
D. 两种安全完全独立，没有任何交互

<details>
<summary>显示答案</summary>

**答案：B. Linkerd 处理传输层，应用程序处理业务逻辑安全**

**说明：**
遵循纵深防御原则，Linkerd 处理传输加密（mTLS）和 Service 授权，而应用程序处理用户身份验证（JWT）、RBAC 和输入验证等业务逻辑安全。

</details>

### 12. 以下哪项不是要通过 Prometheus 告警监控的 Linkerd 安全指标？

A. 证书过期时间
B. 非 mTLS 流量比例
C. 应用程序登录失败次数
D. 授权被拒绝的请求数

<details>
<summary>显示答案</summary>

**答案：C. 应用程序登录失败次数**

**说明：**
Linkerd 安全指标包括：证书过期时间、非 mTLS 流量比例、授权被拒绝的请求数。应用程序登录失败属于应用程序级指标，不在 Linkerd 的范围内。

</details>
