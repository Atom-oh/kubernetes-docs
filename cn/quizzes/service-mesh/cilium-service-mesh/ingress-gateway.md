# Cilium Service Mesh Ingress 与 Gateway 测验

基线版本：Cilium 1.20.3、Gateway API 1.6.3 和 AWS LBC 3.6.0。阅读[指南](../../../service-mesh/cilium-service-mesh/05-ingress-gateway.md)及其主要来源。

## 测验题目

### 1. Cilium Ingress `loadbalancerMode: shared` 共享的是什么？

- A. 集群中所有控制器共用的一个前端
- B. 使用此模式的资源共用的 Cilium Ingress Service
- C. 仅限内部 NodePort
- D. 所有 Gateway API Gateway 自动共用

<details>
<summary>显示答案</summary>

**答案：B. 使用此模式的资源共用的 Cilium Ingress Service**

此设置适用于使用 shared 模式、由 Cilium 管理的 Ingress 资源。Dedicated 模式的覆盖设置和其他控制器彼此独立。共享的 GatewayClass 也不意味着共用一个云负载均衡器。

</details>

### 2. 如何将 HTTPRoute 显式关联到 Gateway 的 HTTPS listener？

- A. 指定一个父 Pod
- B. 使用 `parentRefs` 指定 Gateway 名称和 `sectionName: https`
- C. 仅设置 Route 的命名空间
- D. 使用任意 listener 注解

<details>
<summary>显示答案</summary>

**答案：B. 使用 `parentRefs` 指定 Gateway 名称和 `sectionName: https`**

section 名称必须与 listener 匹配，其 `allowedRoutes` 必须允许关联，并且主机名/协议必须兼容。请检查正确的 parent status 条目中的 Accepted/ResolvedRefs 状态；仅有 parent reference 并不能证明可达。

</details>

### 3. 哪个 Cilium Ingress 注解可启用 TLS passthrough？

- A. `ingress.cilium.io/tls-mode: passthrough`
- B. `ingress.cilium.io/tls-passthrough: "true"`
- C. `cilium.io/tls: passthrough`
- D. nginx 专用注解

<details>
<summary>显示答案</summary>

**答案：B. `ingress.cilium.io/tls-passthrough: "true"`**

TLS 由后端终止。Ingress 需要设置主机名和路径 `/`；Cilium 使用 SNI，而不是检查 HTTP 路径。后端看到的是 Envoy/节点连接，而不是原始客户端的套接字地址。

</details>

### 4. 在哪里配置 Gateway 的协议和端口？

- A. `protocols`
- B. `listeners`
- C. `endpoints`
- D. `handlers`

<details>
<summary>显示答案</summary>

**答案：B. `listeners`**

每个 listener 定义其协议/端口以及适用的主机名/TLS/关联设置。实际支持的协议组合取决于控制器。例如，LBC 3.6 不支持在同一个 Gateway 中混用其 L4/NLB 和 L7/ALB listener。

</details>

### 5. 要为指南中的 Cilium shared Ingress NLB 前端选择 AWS LBC，应使用哪项配置？

- A. 仅使用旧版 `aws-load-balancer-type: nlb` 注解
- B. Service `spec.loadBalancerClass: service.k8s.aws/nlb`、instance target 和已分配的 NodePort
- C. 使用 IP target，但不检查 EndpointSlices
- D. 任意 EKS 命名空间标签

<details>
<summary>显示答案</summary>

**答案：B. Service `spec.loadBalancerClass: service.k8s.aws/nlb`、instance target 和已分配的 NodePort**

对应的 Helm 设置是 `ingressController.service.loadBalancerClass`。Cilium 的 L7 shared Ingress EndpointSlice 是合成的，并且没有 Pod target 引用；LBC 的 IP 解析器会跳过它。仍需验证 EC2 instance/NodePort 前提条件。

</details>

### 6. 哪个 HTTPRoute filter 会改写上游主机名/路径，而不重定向客户端？

- A. `PathRewrite`
- B. `URLRewrite`
- C. `RequestTransform`
- D. `RequestRedirect`

<details>
<summary>显示答案</summary>

**答案：B. `URLRewrite`**

URLRewrite 会更改转发给后端的请求。RequestRedirect 会向客户端返回重定向。指南中的 header 值是字面字符串，不会自动生成 UUID 或延迟值。

</details>

### 7. 哪项 listener 设置可将跨命名空间的 Route 关联限制为带有获准标签的命名空间？

- A. `allowedRoutes.namespaces.from: All`
- B. `allowedRoutes.namespaces.from: Selector` 并配置匹配的 selector
- C. `crossNamespace: true`
- D. `routes.scope: cluster`

<details>
<summary>显示答案</summary>

**答案：B. `allowedRoutes.namespaces.from: Selector` 并配置匹配的 selector**

All 也允许跨命名空间关联，但不会按标签进行限制。Same 会将关联范围限制在 Gateway 所在的命名空间。跨命名空间引用后端 Service 还需要在后端命名空间中配置 ReferenceGrant；这是另一项独立检查。

</details>

### 8. 在哪里配置 Envoy 主动健康检查？

- A. Listener 的名称
- B. Cluster 的 `health_checks`
- C. Route 的名称
- D. Endpoint 的命名空间

<details>
<summary>显示答案</summary>

**答案：B. Cluster 的 `health_checks`**

可用的 CEC 仍需具备 Service→Listener→route→Cluster 链路。HTTP 健康检查的主机名/路径必须能在实际后端上正常工作。预期状态码区间不包含上界，因此起始值为 200、结束值为 300 时会覆盖所有 2xx 状态码。

</details>

### 9. 哪种永久重定向会保留请求方法/正文？HTTP→HTTPS Route 应如何关联？

- A. HTTP 和 HTTPS 上都使用 302
- B. HTTP 和 HTTPS 上都使用 307
- C. 仅在 HTTP listener 上使用 308
- D. 仅在 HTTPS listener 上使用 303

<details>
<summary>显示答案</summary>

**答案：C. 仅在 HTTP listener 上使用 308**

308 是永久重定向，并会保留方法/正文；307 是对应的临时重定向。仅将 scheme 重定向绑定到 HTTP，可避免 HTTPS 自我重定向循环。重定向无法保护已在初始明文请求中发送的数据。

</details>

### 10. 哪项成本和能力比较是准确的？

- A. Cilium 从不需要云负载均衡器
- B. AWS LBC 总是更快
- C. Cilium 节点/代理成本可能与云 LB 费用同时产生；应比较特定版本支持的功能
- D. 每个控制器都支持所有 Gateway API 功能

<details>
<summary>显示答案</summary>

**答案：C. Cilium 节点/代理成本可能与云 LB 费用同时产生；应比较特定版本支持的功能**

Cilium 可以运行在 ALB/NLB 后方，而 ALB/NLB 仍会产生费用。LBC 3.6 会将 HTTP/GRPC Route 映射到 ALB，并将 TCP/UDP/TLS Route 映射到 NLB。工作负载 mTLS 和 ACM 服务器证书是不同的机制；性能比较需要采用可比的测量方式。

</details>

### 11. 在指南所用的 Gateway API 1.6.3 基线中，TCPRoute 有什么作用？

- A. 检查 HTTP 路径
- B. 默认终止 TLS
- C. 使用已提供的 v1 API 转发不透明的 TCP 流
- D. 仅处理 UDP

<details>
<summary>显示答案</summary>

**答案：C. 使用已提供的 v1 API 转发不透明的 TCP 流**

TCP 可以承载 HTTP 或 TLS，但 TCPRoute 不具备它们的 L7 语义。此基线不提供旧版 TCPRoute v1alpha2 API。TLSRoute v1 则需要兼容的 TLS passthrough listener 才能进行 SNI 路由。

</details>

### 12. 如果在此 Cilium Ingress 拓扑中启用 NLB PPv2，需要协调哪些事项？

- A. 仅需客户端 X-Forwarded-For header
- B. 同时配置 NLB 发送端和 Cilium `enableProxyProtocol` 接收端、健康检查及可信访问路径
- C. 无需更改接收端
- D. 每个 NLB 都必须启用 PPv2

<details>
<summary>显示答案</summary>

**答案：B. 同时配置 NLB 发送端和 Cilium `enableProxyProtocol` 接收端、健康检查及可信访问路径**

解析器要求存在 PROXY header，因此只启用一端会导致流量中断。PPv2 是可选项；客户端 IP 是否保留也取决于 target 类型/属性。AWS LBC 警告不要在使用 instance target 和 externalTrafficPolicy Local 时启用 PPv2。PROXY 元数据不是经过身份验证的身份信息。

</details>
