# Gateway API 测验

基于 v1.6 API 基线以及指南中针对具体实现的前置条件。每个代码示例都是一个独立场景。

## 1. 以下哪项不是 Gateway API 的设计目标？

- A. 更明确地划分基础设施、运维人员和应用各自负责的资源
- B. 为多种流量协议定义 API 类型
- C. 使用标准字段，并明确各功能的支持级别
- D. 将所有网络功能合并到一个对象中

<details>
<summary>显示答案</summary>

D. GatewayClass、Gateway 和 Route 资源将职责分开。控制器仍需实现相应的 API 版本、配置档案和功能；RBAC 与准入控制负责执行权限边界。标准字段提升可移植性，但并不意味着可以省去实现特定的扩展。

</details>

## 2. 在按角色分工的模型中，通常由谁管理 GatewayClass？

- A. 每位应用开发人员各自管理
- B. 只有后端 Service 的所有者
- C. 基础设施提供方或平台/网络团队
- D. 未经身份验证的应用客户端

<details>
<summary>显示答案</summary>

C. GatewayClass 用于选择已安装的控制器以及该实现支持的专用参数。平台运维人员管理 Gateway 和路由附加策略；开发人员管理 Route；被引用命名空间的所有者管理该命名空间中的 ReferenceGrant。这些是运维角色的划分，不会自动成为 Kubernetes 权限。

</details>

## 3. TLS 终止与透传有什么区别？

- A. Terminate 会原样传递加密字节
- B. Terminate 在网关处结束下游 TLS；Passthrough 则由后端结束 TLS
- C. 两者都要求使用可互换模式的 HTTPS 监听器
- D. 终止 TLS 一定会使网关到后端的流量变成明文

<details>
<summary>显示答案</summary>

B. HTTPS 终止与 TLS 透传需要不同的监听器配置。终止 TLS 后是否加密网关到后端的连接，是另一个独立决策；可使用受支持的 BackendTLSPolicy 或实现专用配置。

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: quiz-tls
  namespace: gateway-system
spec:
  gatewayClassName: istio
  listeners:
  - name: https
    protocol: HTTPS
    port: 443
    tls:
      mode: Terminate
      certificateRefs:
      - name: tls-cert
  - name: tls-passthrough
    protocol: TLS
    port: 8443
    tls:
      mode: Passthrough
```

被引用的 TLS Secret 以及相应的 Route 和后端都必须存在。不能只把 HTTPS 监听器的 mode 改成 Passthrough 来启用 TLS 透传。

</details>

## 4. HTTPRoute 如何表达按权重拆分后端流量？

- A. 使用 trafficSplit 字段
- B. 在多个 backendRefs 上设置 weight
- C. 使用必需的 canary 注解
- D. 创建其他 API 提供的 TrafficSplit CRD

<details>
<summary>显示答案</summary>

B. 在指南所用的 Gateway/Namespace 配置以及后端 Service 已存在的前提下：

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: quiz-split
  namespace: production
spec:
  parentRefs:
  - name: production-gateway
    namespace: gateway-system
    sectionName: https
  hostnames:
  - api.example.com
  rules:
  - backendRefs:
    - name: app-stable
      port: 80
      weight: 90
    - name: app-canary
      port: 80
      weight: 10
```

weight 表示相对流量分配，无需加总为 100；小样本中的实际比例也不一定精确匹配权重。它控制发往此 Gateway 后端的流量，不会把客户端从旧 Ingress 前端切换到新的 Gateway 前端。

</details>

## 5. 跨命名空间引用后端时，应在哪里创建 ReferenceGrant？

- A. 始终在 Route 所在的命名空间
- B. 在被引用后端所在的命名空间，由其所有者创建
- C. 只能在 kube-system 中
- D. 在客户端工作站上

<details>
<summary>显示答案</summary>

B. 由接收引用的一方授予权限。例如：

```yaml
apiVersion: gateway.networking.k8s.io/v1beta1
kind: ReferenceGrant
metadata:
  name: allow-shared-api
  namespace: backend-services
spec:
  from:
  - group: gateway.networking.k8s.io
    kind: HTTPRoute
    namespace: production
  to:
  - group: ''
    kind: Service
    name: shared-api
---
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: shared-api
  namespace: production
spec:
  parentRefs:
  - name: production-gateway
    namespace: gateway-system
    sectionName: https
  hostnames:
  - api.example.com
  rules:
  - matches:
    - path:
        type: PathPrefix
        value: /shared
    backendRefs:
    - name: shared-api
      namespace: backend-services
      port: 80
```

backend-services 命名空间中必须存在 shared-api Service。`to.name` 将授权范围限制为该 Service。Route 附加到 Gateway 使用的是 parentRefs 和 allowedRoutes，不需要为这种附加关系创建 ReferenceGrant。ReferenceGrant 不负责验证应用用户身份。

</details>

## 6. 哪项资源不属于 Gateway API v1.6 Standard 资源集合？

- A. GatewayClass
- B. GRPCRoute
- C. TCPRoute
- D. Istio VirtualService

<details>
<summary>显示答案</summary>

D. VirtualService 是 Istio API。v1.6 Standard 资源集合包括 HTTPRoute、GRPCRoute、TCPRoute、TLSRoute 和 UDPRoute 等资源。旧版答案中“TCPRoute 属于 Experimental”的说法已不再正确。Channel 与 API 版本是不同概念：ReferenceGrant v1beta1 仍与 v1 一起在 Standard 中提供；Experimental 资源集合中的字段也可能出现在 v1 资源上。

</details>

## 7. 哪种过滤器会改写发往上游的请求，而不向客户端返回重定向？

- A. RequestHeaderModifier
- B. ResponseHeaderModifier
- C. URLRewrite
- D. RequestMirror

<details>
<summary>显示答案</summary>

C. URLRewrite 会更改上游请求的路径或 Host；后端目标仍由 backendRefs 选择。RequestRedirect 则会向客户端返回 3xx 响应。

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: quiz-rewrite
  namespace: production
spec:
  parentRefs:
  - name: production-gateway
    namespace: gateway-system
    sectionName: https
  hostnames:
  - api.example.com
  rules:
  - matches:
    - path:
        type: PathPrefix
        value: /old-api
    filters:
    - type: URLRewrite
      urlRewrite:
        path:
          type: ReplacePrefixMatch
          replacePrefixMatch: /new-api
        hostname: new-api.example.com
    backendRefs:
    - name: new-api-service
      port: 80
```

此处 `/old-api/users` 会变成 `/new-api/users`。ReplaceFullPath 则会替换整个路径。迁移旧版重写规则时，必须区分这两种行为。

</details>

## 8. 哪个组件不会协调 Gateway API 资源？

- A. Istio Gateway 控制器
- B. Cilium Gateway 控制器
- C. kube-proxy
- D. Envoy Gateway

<details>
<summary>显示答案</summary>

C. kube-proxy 负责 Service 转发，也可能参与后端网络路径，但它不会协调 GatewayClass、Gateway 或 Route 资源。仅安装 Gateway API CRD 并不会安装以上任何一个控制器。

</details>

## 9. 旧 Ingress 配置中的 HTTP 路径重写，在 Gateway API 中应使用什么配置？

- A. Gateway 对象名称
- B. HTTPRoute 的 URLRewrite 过滤器
- C. 来自任意命名空间的 ReferenceGrant
- D. 仅使用命名空间标签

<details>
<summary>显示答案</summary>

B. 选择 ReplaceFullPath 还是 ReplacePrefixMatch 前，应先确认旧重写规则的实际语义。指南中的固定 `rewrite-target: /` 会替换完整路径，而不是保留后缀。其他 Ingress 注解可能对应 Gateway 设置或控制器策略 CRD，也可能没有受支持的等效项。HTTP 到 HTTPS 的重定向必须绑定到 HTTP 监听器。

</details>

## 10. 如何限制哪些命名空间中的 Route 可以附加到 Gateway？

- A. `from: All` 将附加范围限制在一个命名空间
- B. `from: Same` 允许同一命名空间中的 Route
- C. `from: Selector` 根据 Namespace 标签选择
- D. B 和 C 都有效，但适用范围不同

<details>
<summary>显示答案</summary>

D. `from` 应选择其中一个值。使用标签选择器的示例：

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: quiz-namespace-selector
  namespace: gateway-system
spec:
  gatewayClassName: istio
  listeners:
  - name: https
    protocol: HTTPS
    port: 443
    tls:
      mode: Terminate
      certificateRefs:
      - name: tls-cert
    allowedRoutes:
      namespaces:
        from: Selector
        selector:
          matchLabels:
            gateway-access: 'true'
```

标签属于 Namespace，而非 Route 或 Pod。应控制哪些主体可以更改 Namespace 标签。allowedRoutes 限制的是 Route 附加范围；它既不会授权跨命名空间访问后端，也不会授权应用请求。

</details>

## 11. GRPCRoute 中哪种匹配条件可以选择某个 Service 的特定 method？

- A. path.service 和 path.method
- B. method.service 和 method.method
- C. grpc.service 和 grpc.method
- D. rpc.service 和 rpc.method

<details>
<summary>显示答案</summary>

B. 对于指南中的 gRPC 监听器：

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: GRPCRoute
metadata:
  name: quiz-grpc
  namespace: production
spec:
  parentRefs:
  - name: multi-protocol-gateway
    namespace: gateway-system
    sectionName: grpc
  hostnames:
  - grpc.example.com
  rules:
  - matches:
    - method:
        service: myapp.UserService
        method: GetUser
    backendRefs:
    - name: user-service
      port: 50051
```

默认采用 Exact 匹配时，method 名称区分大小写。后端必须提供预期的 gRPC 传输协议，并配置适当的 TLS；仅凭端口号无法确认这些条件。只指定 service 的 method 匹配会涵盖该 Service 下的所有 method。

</details>

## 12. 以下哪项对 Gateway API 与 Ingress 的比较不正确？

- A. Gateway API 更明确地分离监听器和 Route 的所有权
- B. Gateway API 为 TCP、UDP 和 gRPC 定义了专用路由类型
- C. Standard 路由字段有实现支持要求
- D. Gateway API 的资源类型比 Ingress 更少

<details>
<summary>显示答案</summary>

D. Gateway API 引入了多种资源类型。Ingress 也有 IngressClass，并且可以使用 RBAC 和准入控制；说它没有任何授权或所有权控制并不准确。Gateway API 更明确地表达了若干职责划分和跨命名空间授权流程。应检查控制器及其版本支持情况，而不要假设每个 API 字段在所有实现中的行为都相同。

</details>

[返回指南](../../networking/04-gateway-api.md)
