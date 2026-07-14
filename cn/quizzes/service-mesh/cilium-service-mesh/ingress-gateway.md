# Cilium Service Mesh Ingress 与 Gateway 测验

本测验用于测试你对 Cilium Ingress Controller、Gateway API、TLS 终止和 EKS 集成模式的理解。

## 测验题目

### 1. Cilium Ingress Controller 的 loadbalancerMode 选项中的“shared”模式表示什么？

A. 为每个 Ingress 创建单独的负载均衡器
B. 所有 Ingress 共用一个负载均衡器
C. 仅使用 NodePort，不使用负载均衡器
D. 仅处理内部流量

<details>
<summary>显示答案</summary>

**答案：B. 所有 Ingress 共用一个负载均衡器**

**说明：**
loadbalancerMode: shared 设置使所有 Ingress 资源使用同一个共享负载均衡器。这种方式具有成本效益，而 dedicated 模式会为每个 Ingress 创建单独的负载均衡器。

</details>

### 2. Gateway API 的 HTTPRoute 中 parentRefs 字段的作用是什么？

A. 定义父 Pod
B. 指定此路由连接到哪个 Gateway
C. 引用父 namespace
D. 定义要继承的策略

<details>
<summary>显示答案</summary>

**答案：B. 指定此路由连接到哪个 Gateway**

**说明：**
parentRefs 指定 HTTPRoute 连接到哪个 Gateway。通过引用 Gateway 的名称和 namespace，它确定该路由应用于哪个 listener。

</details>

### 3. 哪个 annotation 可在 Cilium Ingress 中启用 TLS passthrough？

A. ingress.cilium.io/tls-mode: passthrough
B. ingress.cilium.io/tls-passthrough: "true"
C. cilium.io/tls: passthrough
D. nginx.ingress.kubernetes.io/ssl-passthrough

<details>
<summary>显示答案</summary>

**答案：B. ingress.cilium.io/tls-passthrough: "true"**

**说明：**
`ingress.cilium.io/tls-passthrough: "true"` annotation 会将 TLS 流量直接转发到后端 Service，而不终止 TLS。当后端需要处理 TLS 时，这非常有用。

</details>

### 4. Gateway API 的 Gateway 资源中使用哪个字段来支持多种协议？

A. protocols
B. listeners
C. endpoints
D. handlers

<details>
<summary>显示答案</summary>

**答案：B. listeners**

**说明：**
可在 Gateway 的 listeners 字段中定义多个 listener，以支持 HTTP、HTTPS、TCP、TLS 等各种协议。每个 listener 都可以单独配置 protocol、port、hostname 等。

</details>

### 5. 在 EKS 上将 NLB 与 Cilium Ingress 一起使用需要哪个 annotation？

A. service.kubernetes.io/load-balancer-type: nlb
B. service.beta.kubernetes.io/aws-load-balancer-type: "nlb"
C. eks.amazonaws.com/load-balancer: nlb
D. aws.load-balancer/type: network

<details>
<summary>显示答案</summary>

**答案：B. service.beta.kubernetes.io/aws-load-balancer-type: "nlb"**

**说明：**
要在 AWS EKS 上使用 Network Load Balancer，请向 Service 添加 `service.beta.kubernetes.io/aws-load-balancer-type: "nlb"` annotation。scheme、target-type 等额外 annotation 可以进一步配置 NLB 行为。

</details>

### 6. Gateway API 的 HTTPRoute 中使用哪种 filter 类型来配置 URL 重写？

A. PathRewrite
B. URLRewrite
C. RequestTransform
D. PathModifier

<details>
<summary>显示答案</summary>

**答案：B. URLRewrite**

**说明：**
在 HTTPRoute 的 filters 部分中，使用 type: URLRewrite 重写请求 URL。path 和 hostname 都可以修改。

</details>

### 7. 要在 Cilium Gateway API 中允许跨 namespace 路由，需要哪个 Gateway 设置？

A. allowedRoutes.namespaces.from: All
B. allowedRoutes.namespaces.from: Selector
C. crossNamespace: true
D. routes.scope: cluster

<details>
<summary>显示答案</summary>

**答案：B. allowedRoutes.namespaces.from: Selector**

**说明：**
在 Gateway 的 listeners 中，将 allowedRoutes.namespaces.from: Selector 设置为 Selector 后，使用 selector 时仅允许来自具有特定标签的 namespace 的路由。'All' 允许所有 namespace，'Same' 仅允许相同的 namespace。

</details>

### 8. 在 CiliumEnvoyConfig 中使用哪种 Envoy 资源类型来配置 Service 健康检查？

A. envoy.config.listener.v3.Listener
B. envoy.config.cluster.v3.Cluster
C. envoy.config.route.v3.Route
D. envoy.config.endpoint.v3.Endpoint

<details>
<summary>显示答案</summary>

**答案：B. envoy.config.cluster.v3.Cluster**

**说明：**
健康检查设置定义在 Cluster 资源的 health_checks 字段中。可以配置 HTTP 健康检查、TCP 健康检查、间隔、阈值等。

</details>

### 9. 在 Gateway API 中从 HTTP 重定向到 HTTPS 时，建议使用哪个 statusCode？

A. 302 (Found)
B. 307 (Temporary Redirect)
C. 301 (Moved Permanently)
D. 303 (See Other)

<details>
<summary>显示答案</summary>

**答案：C. 301 (Moved Permanently)**

**说明：**
对于从 HTTP 到 HTTPS 的永久重定向，建议使用状态码 301。这会告知浏览器和搜索引擎 URL 已永久更改，有利于缓存和 SEO。

</details>

### 10. Cilium 与 AWS Load Balancer Controller 的主要区别是什么？

A. Cilium 仅支持 L4
B. AWS LBC 提供更低延迟
C. Cilium 仅使用 node 资源，无需额外的 LB 成本
D. AWS LBC 完全支持 Gateway API

<details>
<summary>显示答案</summary>

**答案：C. Cilium 仅使用 node 资源，无需额外的 LB 成本**

**说明：**
Cilium Ingress/Gateway 使用 node 的 eBPF 和 Envoy 处理外部流量，因此不会产生单独的 AWS load balancer 成本。相比之下，AWS LBC 会预配 ALB/NLB，从而产生额外成本。

</details>

### 11. Gateway API 中的 TCPRoute 用于什么？

A. HTTP 流量路由
B. 需要 TLS 终止的流量
C. 原始 TCP 流量路由（非 HTTP）
D. 仅用于 UDP 流量

<details>
<summary>显示答案</summary>

**答案：C. 原始 TCP 流量路由（非 HTTP）**

**说明：**
TCPRoute 用于路由非 HTTP 的原始 TCP 流量，例如数据库连接和消息队列。它与 Gateway 的 TCP listener 配合使用，为非 HTTP Service 提供外部访问。

</details>

### 12. 在 Cilium Ingress 中，使用哪种 NLB 设置来保留客户端 IP？

A. X-Forwarded-For header
B. Proxy Protocol
C. Disable Source NAT
D. Direct Server Return

<details>
<summary>显示答案</summary>

**答案：B. Proxy Protocol**

**说明：**
要通过 NLB 保留客户端 IP，必须启用 Proxy Protocol。使用 `service.beta.kubernetes.io/aws-load-balancer-proxy-protocol: "*"` annotation。Envoy 从 Proxy Protocol header 中提取原始客户端 IP。

</details>
