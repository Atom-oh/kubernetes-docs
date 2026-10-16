# Cilium Service Mesh Ingress 与 Gateway

> **审查基线**：Cilium 1.20.1；Gateway API 1.6.1；AWS Load Balancer Controller 3.5.0。
> **最后审查**：2026 年 9 月 11 日。请参阅[安装前提条件](./README.md)了解 Kubernetes/EKS 矩阵；仅有较新版本并不能确立兼容性。

## 概述

Cilium 使用 Kubernetes Ingress 和 Gateway API 资源配置其数据平面。eBPF 处理 Service 转发并将 L7 流量重定向到节点本地 Envoy。Envoy 提供 HTTP 路由和 TLS 终止；不透明的 TCP/TLS 路径具有不同的能力。以下示例描述的是替代入口点，而不是完整的应用程序部署。

## 架构

![逻辑配置和流量组件：云负载均衡器访问 Cilium Service 前端；eBPF 将 L7 流量重定向到 Envoy，其配置派生自 Ingress 或 Gateway API 资源。](../../.gitbook/assets/en-service-mesh-cilium-service-mesh-05-ingress-gateway-0.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-cilium-service-mesh-05-ingress-gateway-0.html)

Gateway/Ingress 框表示配置，而非接收数据包的进程。对于 L7 流量，实际路径为负载均衡器 → Service/NodePort 前端 → eBPF/TPROXY → Envoy → 后端。Cilium 在外部 `world` → `ingress` 边界处应用策略，并再次从 `ingress` 到后端应用策略。策略必须允许两个路径。云负载均衡器可用性和目标注册是独立的前提条件。

## Cilium Ingress Controller

### 安装和启用

```yaml
kubeProxyReplacement: true
l7Proxy: true
envoy:
  enabled: true
ingressController:
  enabled: true
  loadbalancerMode: shared
  default: false
  service:
    type: LoadBalancer
```

这些是已规划 Cilium 安装的 Helm **覆盖值**。将它们与安装指南中平台特定的 CNI/IPAM 和可访问 API-server 设置合并。在运行中的集群上更改 kube-proxy 替换是一项迁移工作，而不是常规功能开关。在应用更改前，渲染并审查固定的 1.20.1 chart。

`ingressController.default` 将 `cilium` **IngressClass 标记为默认值**；它不配置回退后端。chart 会创建 class `cilium`；`ingressController.ingressClassName` 不是受支持的值。显式的 `spec.ingressClassName` 可避免依赖集群默认值。

在共享模式中，由 Cilium 管理的 Ingress 资源使用 Helm release namespace（此处为 `kube-system`）中的共享 `cilium-ingress` Service。每个 Ingress 模式注解可以选择专用模式；其他 Controller 和 Gateway API 资源不会自动共享此入口前端。更改模式可能改变地址并中断连接。`LoadBalancer` 需要能够置备/协调它的实现；当 AWS LBC 拥有该 Service 时，请使用下面的 EKS 覆盖层。

### Ingress 资源示例

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: app-ingress
  namespace: default
  annotations:
    ingress.cilium.io/loadbalancer-mode: shared
    ingress.cilium.io/tls-passthrough: 'false'
spec:
  ingressClassName: cilium
  tls:
  - hosts:
    - app.example.com
    secretName: app-tls-secret
  rules:
  - host: app.example.com
    http:
      paths:
      - path: /api
        pathType: Prefix
        backend:
          service:
            name: api-service
            port:
              number: 80
      - path: /
        pathType: Prefix
        backend:
          service:
            name: frontend-service
            port:
              number: 80
```

在 `default` 中创建具名 Service 和就绪 endpoint，每个均公开 Service 端口 80。提供包含 `app.example.com` 的证书的 `app-tls-secret`，并将 DNS 指向该前端。TLS 部分会在 Envoy 终止客户端 TLS；显示的后端端口是明文 HTTP。Cilium 默认的 `enforceHttps: true` 会为已启用 TLS 的主机重定向 HTTP。这并不能建立 workload 到 workload 的 mTLS。

### 基于路径的路由

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: path-routing
  namespace: default
spec:
  ingressClassName: cilium
  rules:
  - host: api.example.com
    http:
      paths:
      - path: /users
        pathType: Prefix
        backend:
          service:
            name: users-service
            port:
              number: 80
      - path: /orders
        pathType: Prefix
        backend:
          service:
            name: orders-service
            port:
              number: 80
      - path: /products
        pathType: Prefix
        backend:
          service:
            name: products-service
            port:
              number: 80
      - path: /health
        pathType: Exact
        backend:
          service:
            name: health-service
            port:
              number: 80
```

`Prefix` 匹配路径元素：`/users` 和 `/users/42` 会匹配，`/users-old` 不会匹配。`Exact` 仅匹配 `/health`。Cilium 的 Ingress 排序为 Exact，然后是 ImplementationSpecific/regex，最后是 Prefix；在这些组内，较长的匹配优先。Gateway API 有自己的优先级规则；YAML 列表顺序并不是通用的路由优先级机制。

### TLS 终止

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: tls-ingress
  namespace: default
spec:
  ingressClassName: cilium
  tls:
  - hosts:
    - secure.example.com
    secretName: app-tls-secret
  rules:
  - host: secure.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: secure-app
            port:
              number: 80
```

从**真实 PEM 文件**生成 Secret，而不要应用占位 Base64。用于两个示例的同一 Secret 必须包含 SAN 覆盖 `app.example.com` 和 `secure.example.com` 的证书；否则请使用单独的 Secret。通过 PKI 置备公开受信任或显式受信任的私有证书，并规划续期。

```bash
openssl x509 -in ./tls.crt -noout -dates -ext subjectAltName
kubectl -n default create secret tls app-tls-secret \
  --cert=./tls.crt --key=./tls.key --dry-run=client -o yaml
```

最后一个命令仅渲染 Secret。通过所选的 Secret 管理工作流审查并应用它；避免将私钥输出写入共享日志。

### TLS 透传

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: tls-passthrough
  namespace: default
  annotations:
    ingress.cilium.io/tls-passthrough: 'true'
spec:
  ingressClassName: cilium
  rules:
  - host: backend.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: tls-backend
            port:
              number: 443
```

后端终止 TLS 并拥有 `backend.example.com` 的证书。Cilium 匹配 TLS SNI；透传 Ingress 需要主机名和路径 `/`。加密流量内部无法使用 HTTP 路径/标头重写。后端看到的是来自 Envoy/节点的新连接，而非原始客户端套接字地址，并且 Envoy 无法向该流插入 HTTP 转发标头。

## Gateway API

### 启用 Gateway API

```yaml
gatewayAPI:
  enabled: true
  gatewayClass:
    create: true
  secretsNamespace:
    create: true
    name: cilium-secrets
    sync: true
```

在启用 Controller 前安装 **Gateway API 1.6.1 Standard CRD**；这是 Cilium 1.20.1 安装参考所使用的版本。审查共享集群的所有 Controller 的 CRD 升级。请勿以此片段替换整个 Cilium values 文件：它补充了上方的 kube-proxy 替换/L7 前提条件。

受支持的键为 `gatewayAPI.gatewayClass.create` 和 `gatewayAPI.secretsNamespace`。先前位置的 `secretNamespace` 和 `gatewayClassName` 会被忽略。默认情况下，证书引用仍在 Gateway 的 namespace 中命名 Secret；Controller 同步的 Secret namespace 不会重定位用户的引用。

### GatewayClass

使用前述 chart 设置时，Cilium 管理 Controller 名称为 `io.cilium/gateway-controller` 的 `cilium` GatewayClass。使用 `kubectl get gatewayclass cilium -o yaml` 检查它；不要为同一对象创建第二个所有者。GatewayClass 选择 Controller 和参数，而不是共享的物理负载均衡器。

### Gateway

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: main-gateway
  namespace: default
spec:
  gatewayClassName: cilium
  listeners:
  - name: http
    protocol: HTTP
    port: 80
    hostname: '*.example.com'
    allowedRoutes:
      namespaces:
        from: Same
  - name: https
    protocol: HTTPS
    port: 443
    hostname: '*.example.com'
    tls:
      mode: Terminate
      certificateRefs:
      - kind: Secret
        name: wildcard-tls
        namespace: default
    allowedRoutes:
      namespaces:
        from: Same
```

在使用 HTTPS 前，在 `default` 中创建含监听器主机名证书的 `wildcard-tls`。`*.example.com` 不覆盖裸 `example.com` 或 `a.b.example.com` 这类更深层名称。这些 listener 终止 HTTP/HTTPS；后续 TCP 和 TLS 透传示例使用单独的 Gateway，以明确其协议和所有权。每个生成的 Gateway Service 都可能需要单独的云负载均衡器。

### HTTPRoute

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: api-routes
  namespace: default
spec:
  parentRefs:
  - name: main-gateway
    namespace: default
    sectionName: https
  hostnames:
  - api.example.com
  rules:
  - matches:
    - path:
        type: PathPrefix
        value: /v1/users
    backendRefs:
    - name: users-v1
      port: 80
  - matches:
    - path:
        type: PathPrefix
        value: /v2/users
    backendRefs:
    - name: users-v2
      port: 80
  - matches:
    - path:
        type: PathPrefix
        value: /api
      headers:
      - name: X-API-Version
        value: '2'
    backendRefs:
    - name: api-v2
      port: 80
  - matches:
    - path:
        type: PathPrefix
        value: /
    backendRefs:
    - name: api-v1
      port: 80
```

每个后端都是 Route namespace 中已有的 Service，带有端口 80 和就绪 endpoint。`sectionName: https` 有意将该 Route 限制为仅用于 HTTPS listener。在正确的 `status.parents` 条目上检查 `Accepted` 和 `ResolvedRefs`，并以当前的 `observedGeneration` 检查 Gateway/listener 的 `Programmed`/`Accepted` 条件。仅被接受的配置并不能证明 DNS、证书信任、目标健康状态或应用程序可达性。

### 基于权重的流量拆分

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: canary-route
  namespace: default
spec:
  parentRefs:
  - name: main-gateway
    sectionName: https
  hostnames:
  - app.example.com
  rules:
  - matches:
    - path:
        type: PathPrefix
        value: /
    backendRefs:
    - name: app-stable
      port: 80
      weight: 90
    - name: app-canary
      port: 80
      weight: 10
```

权重是相对选择概率，并不承诺每十个请求中恰好有九个稳定请求。连接、重试和采样可能改变观察到的计数。此示例仅附加到 HTTPS，并使用不同于 API 示例的主机名。

### 请求/响应转换

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: transform-route
  namespace: default
spec:
  parentRefs:
  - name: main-gateway
    sectionName: https
  rules:
  - matches:
    - path:
        type: PathPrefix
        value: /api
    filters:
    - type: RequestHeaderModifier
      requestHeaderModifier:
        set:
        - name: X-Doc-Route
          value: api-v2
        remove:
        - X-Internal-Header
    - type: URLRewrite
      urlRewrite:
        hostname: internal-api.default.svc
        path:
          type: ReplacePrefixMatch
          replacePrefixMatch: /v2/api
    - type: ResponseHeaderModifier
      responseHeaderModifier:
        set:
        - name: X-Doc-Gateway
          value: cilium
    backendRefs:
    - name: api-service
      port: 80
  hostnames:
  - transform.example.com
```

标头值是**字面字符串**。`X-Doc-Route` 和 `X-Doc-Gateway` 是诊断标记，而不是生成的请求 ID 或测量的响应时间。主机重写使用 `URLRewrite.hostname`；它不会作为 `Host` 标头变更重复设置。这些标头不会对调用方进行身份验证。响应 `Server` 处理也受 Controller 的 Envoy server-header 转换影响；若要改变该行为，请使用经过验证的 `CiliumGatewayClassConfig`。

### 重定向

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: redirect-http
  namespace: default
spec:
  parentRefs:
  - name: main-gateway
    sectionName: http
  hostnames:
  - '*.example.com'
  rules:
  - matches:
    - path:
        type: PathPrefix
        value: /
    filters:
    - type: RequestRedirect
      requestRedirect:
        scheme: https
        port: 443
        statusCode: 308
---
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: redirect-path
  namespace: default
spec:
  parentRefs:
  - name: main-gateway
    sectionName: https
  hostnames:
  - old.example.com
  rules:
  - matches:
    - path:
        type: Exact
        value: /old-path
    filters:
    - type: RequestRedirect
      requestRedirect:
        path:
          type: ReplaceFullPath
          replaceFullPath: /new-path
        statusCode: 308
---
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: redirect-host
  namespace: default
spec:
  parentRefs:
  - name: main-gateway
    sectionName: https
  hostnames:
  - old.example.com
  rules:
  - matches:
    - path:
        type: PathPrefix
        value: /legacy
    filters:
    - type: RequestRedirect
      requestRedirect:
        hostname: legacy.example.com
        statusCode: 307
```

方案重定向**仅附加到 `http`**，因此 HTTPS 请求无法无限重定向回相同 URL。其他两个 Route 仅附加到 `https` 和狭窄的源主机名。308 永久重定向和 307 临时重定向会保留请求方法/正文；301/302 的客户端行为不同，不应将其普遍建议用于写操作。重定向初始 HTTP 请求无法撤回客户端已发送的明文数据。RequestRedirect 和 URLRewrite 是不同的 filter，不能在同一规则中组合。

### TCPRoute

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: tcp-gateway
  namespace: default
spec:
  gatewayClassName: cilium
  listeners:
  - name: tcp
    protocol: TCP
    port: 9000
    allowedRoutes:
      namespaces:
        from: Same
      kinds:
      - kind: TCPRoute
---
apiVersion: gateway.networking.k8s.io/v1
kind: TCPRoute
metadata:
  name: tcp-route
  namespace: default
spec:
  parentRefs:
  - name: tcp-gateway
    sectionName: tcp
  rules:
  - backendRefs:
    - name: tcp-service
      port: 9000
```

Gateway API 1.6.1 以 **v1** 提供 TCPRoute；旧的 `v1alpha2` 版本不再提供。TCPRoute 转发不透明的 TCP 流，且不检查 HTTP 路径。TCP 可以承载 HTTP 或 TLS，但这并不会使该 Route 获得 HTTP 路由或 TLS 终止语义。Cilium 1.20.1 的 L4 Gateway 转换使用后端 EndpointSlice；不要假定 L7 Envoy 前端的 endpoint 实现完全相同。

### TLSRoute

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: tls-gateway
  namespace: default
spec:
  gatewayClassName: cilium
  listeners:
  - name: tls
    protocol: TLS
    port: 443
    hostname: secure.example.com
    tls:
      mode: Passthrough
    allowedRoutes:
      namespaces:
        from: Same
      kinds:
      - kind: TLSRoute
---
apiVersion: gateway.networking.k8s.io/v1
kind: TLSRoute
metadata:
  name: tls-route
  namespace: default
spec:
  parentRefs:
  - name: tls-gateway
    sectionName: tls
  hostnames:
  - secure.example.com
  rules:
  - backendRefs:
    - name: tls-backend
      port: 443
```

在此基线中，TLSRoute 同样以 **v1** 提供。它需要一个兼容的、带有 `mode: Passthrough` 的 `TLS` listener，而不是上述 HTTPS 终止 listener。后端拥有 `secure.example.com` 的证书；SNI 选择后端，而 HTTP 内容保持加密。验证生成的 Service、listener 状态和端到端 TLS 信任。

## EKS 集成模式

### NLB + Cilium Ingress

```yaml
ingressController:
  enabled: true
  loadbalancerMode: shared
  enableProxyProtocol: false
  service:
    type: LoadBalancer
    loadBalancerClass: service.k8s.aws/nlb
    allocateLoadBalancerNodePorts: true
    externalTrafficPolicy: Cluster
    annotations:
      service.beta.kubernetes.io/aws-load-balancer-scheme: internal
      service.beta.kubernetes.io/aws-load-balancer-nlb-target-type: instance
      service.beta.kubernetes.io/aws-load-balancer-attributes: load_balancing.cross_zone.enabled=true
      service.beta.kubernetes.io/aws-load-balancer-healthcheck-protocol: TCP
      service.beta.kubernetes.io/aws-load-balancer-healthcheck-port: traffic-port
```

此 NLB 按设计为**内部**：唯一的公共入口点是 CloudFront，它通过 CloudFront VPC origin 访问该 NLB。其 security group 必须仅允许来自 VPC-origin security group（或 CloudFront 托管前缀列表）的流量，绝不能允许公共 CIDR。

此覆盖层描述的是 **AWS LBC 管理的 NLB → EC2 NodePort → Cilium Ingress Envoy**。它需要 AWS LBC 3.5.0、其 IAM/subnet/security-group 前提条件、符合条件的 EC2 节点、Cilium 支持的 EKS/CNI 配置以及已分配的 NodePort。它不是 EKS Auto Mode 或 Fargate Cilium 安装方案。`service.k8s.aws/nlb` 明确选择 AWS LBC；旧版 `aws-load-balancer-type: nlb` 注解并不表达该所有权。

对此 L7 前端使用 instance target。Cilium 1.20.1 的共享 Ingress Service 有一个合成 EndpointSlice（`192.192.192.192:9999`，没有 Pod target reference）。AWS LBC 的 IP target resolver 要求 Pod target reference，并跳过这些 endpoint。仅将此 Service 切换为 `ip` **不会**发现节点本地 Envoy 进程。这特定于 Cilium L7 前端；普通 workload Service 和当前 L4 Gateway EndpointSlice 则不同。

TCP health check 检查 NodePort 上的传输可达性，而非应用程序 `/healthz`、TLS 有效性或特定主机 HTTP Route。跨可用区均衡使用当前的 load-balancer attributes 注解，且需要成本/流量审查。不要原地更改现有 Service 的 Controller 所有权或 LB 类型，并假定这是一项零停机迁移。

**客户端身份和可选 PROXY protocol：** 无论 external traffic policy 为 `Cluster` 还是 `Local`，Cilium 都会为 HTTP Envoy 处理保留在其前端可见的来源。该来源是否首先为原始客户端取决于上游 NLB 和 target-group attributes。instance TCP target 通常保留客户端 IP；并非普遍需要 PROXY protocol。如果你的拓扑需要它，请与 NLB 设置协调使用此额外覆盖层：

```yaml
ingressController:
  enableProxyProtocol: true
  service:
    annotations:
      service.beta.kubernetes.io/aws-load-balancer-proxy-protocol: '*'
```

这会在 NLB 启用 PPv2，并在 Cilium Ingress 启用其解析器。这是一次协调部署：只启用一侧会中断流量。解析器需要 PROXY header，因此没有它的直接 HTTP/TLS 探测会失败。AWS LBC 警告不要将 PPv2 与 instance target 及 `externalTrafficPolicy: Local` 组合；该示例保持使用 `Cluster`。HTTP/HTTPS health check 也需要兼容的解析器。将直接访问限制于受信任的代理路径：PP metadata 和转发的 HTTP 标头不是经过身份验证的身份。`gatewayAPI.enableProxyProtocol` 是 Gateway API 的单独设置；Ingress flag 不会配置它。

### ALB + Cilium

ALB → Cilium Envoy 可以组合，但必须为实际环境设计并测试以下前提条件。对于上述合成 L7 EndpointSlice，没有通用可行的 `target-type: ip` 快捷方式。

| 边界 | 必需决策 |
|---|---|
| Controller 和 namespace | ALB Ingress 使用 `spec.ingressClassName: alb`。其后端 Service 必须存在于**相同 namespace**中；共享 `cilium-ingress` Service 通常位于 `kube-system`，而非 `default`。 |
| Target | 对于基于节点的路径，使用明确规划的 NodePort Service 和 ALB `target-type: instance`；验证符合条件的节点、NodePort 分配和 security group。不要悄然转换已拥有 NLB 的 Service。 |
| TLS | 决定 ALB 是终止 TLS 并转发 HTTP，还是转发 HTTPS。ACM server-certificate 附加不是客户端 mTLS。如果 ALB 转发 HTTP，除非协调 listener/redirect 行为，否则 Cilium 的 HTTPS 重定向可能导致循环。 |
| 健康 | ALB health check 使用自己的 Host header，而不会自动使用 `app.example.com`；特定主机应用程序 Route 可能返回 404。定义并测试合适的 health route/port。 |
| 客户端归因 | 为实际代理链配置 Cilium 可信 XFF 跳数，清理不可信标头，并防止绕过 ALB 的直接后端访问。 |

之前的示例引用了错误的 namespace 和 IP target，且遗漏了这些决策；现已由这些实施要求替换。本指南尚未部署或对该组合进行负载测试。

### 混合架构

![外部客户端流量在 AWS ALB 和 NLB 之间拆分；ALB 将流量送往 Cilium Gateway，以进行到 Web app 和 API server 的 L7 路由，而 NLB 将流量送往 Cilium LB，以进行到 gRPC Service 的 L4 负载均衡。](../../.gitbook/assets/en-service-mesh-cilium-service-mesh-05-ingress-gateway-1.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-cilium-service-mesh-05-ingress-gateway-1.html)

这是逻辑组合图，而不是已验证的部署 manifest。ALB 路径需要上述 namespace/target/TLS/health/trust 决策。NLB L4 路径可以承载 gRPC 流，而无需理解单个 RPC 方法。将 Cilium 添加到 ALB 后面不会消除 ALB 费用，也不会使 ALB 功能成为原生 Cilium 功能。

## 多租户 Gateway

### 每 Namespace Gateway

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: GatewayClass
metadata:
  name: cilium-shared
spec:
  controllerName: io.cilium/gateway-controller
---
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: team-a-gateway
  namespace: team-a
spec:
  gatewayClassName: cilium-shared
  listeners:
  - name: https
    protocol: HTTPS
    port: 443
    hostname: '*.team-a.example.com'
    tls:
      mode: Terminate
      certificateRefs:
      - kind: Secret
        name: team-a-tls
    allowedRoutes:
      namespaces:
        from: Same
---
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: team-b-gateway
  namespace: team-b
spec:
  gatewayClassName: cilium-shared
  listeners:
  - name: https
    protocol: HTTPS
    port: 443
    hostname: '*.team-b.example.com'
    tls:
      mode: Terminate
      certificateRefs:
      - kind: Secret
        name: team-b-tls
    allowedRoutes:
      namespaces:
        from: Same
```

首先创建每个 namespace 及其自身有效的 TLS Secret。共享 GatewayClass `cilium-shared` **并不意味着**两个 Gateway 共享一个 Service/load balancer。`from: Same` 将 Route 附加限制在各 Gateway namespace 内；RBAC 必须单独控制谁可以更改 Gateway、Secret、Route 和 namespace label。

### 跨 Namespace 路由

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: shared-gateway
  namespace: gateway-system
spec:
  gatewayClassName: cilium
  listeners:
  - name: https
    protocol: HTTPS
    port: 443
    hostname: '*.example.com'
    allowedRoutes:
      namespaces:
        from: Selector
        selector:
          matchLabels:
            gateway-access: 'true'
    tls:
      mode: Terminate
      certificateRefs:
      - kind: Secret
        name: shared-tls
---
apiVersion: v1
kind: Namespace
metadata:
  name: app-team
  labels:
    gateway-access: 'true'
---
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: app-route
  namespace: app-team
spec:
  parentRefs:
  - name: shared-gateway
    namespace: gateway-system
    sectionName: https
  hostnames:
  - app.example.com
  rules:
  - matches:
    - path:
        type: PathPrefix
        value: /
    backendRefs:
    - name: app-service
      port: 80
```

创建 `gateway-system` 及其覆盖允许主机名的 `shared-tls` Secret。namespace selector 授权 Route 附加；它不对用户进行身份验证，也不授权应用程序请求。管理员必须控制 `gateway-access` label。

所示的 `app-service` 后端位于 `app-team` 本地，因此不需要 ReferenceGrant。如果 Route 改为引用 `backend-team/shared-api`，则后端 namespace 必须显式授予该引用：

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: ReferenceGrant
metadata:
  name: allow-app-team
  namespace: backend-team
spec:
  from:
  - group: gateway.networking.k8s.io
    kind: HTTPRoute
    namespace: app-team
  to:
  - group: ''
    kind: Service
    name: shared-api
---
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: shared-api-route
  namespace: app-team
spec:
  parentRefs:
  - name: shared-gateway
    namespace: gateway-system
    sectionName: https
  hostnames:
  - shared-api.example.com
  rules:
  - backendRefs:
    - name: shared-api
      namespace: backend-team
      port: 80
```

在使用此替代方案前，创建带有 Service 端口 80 的 `backend-team/shared-api`。Route → Gateway 跨 namespace 附加使用 `allowedRoutes`；Route → 后端 Service 跨 namespace 引用使用 `ReferenceGrant`。这些是不同的权限检查。ReferenceGrant v1 在 1.6.1 中提供；v1beta1 也仍然提供。

## 高级负载均衡配置

### Service 健康检查

```yaml
apiVersion: cilium.io/v2
kind: CiliumEnvoyConfig
metadata:
  name: health-check-config
  namespace: default
spec:
  services:
  - name: my-service
    namespace: default
    ports:
    - 80
    listener: health-check-config-listener
  resources:
  - '@type': type.googleapis.com/envoy.config.listener.v3.Listener
    name: health-check-config-listener
    filter_chains:
    - filters:
      - name: envoy.filters.network.http_connection_manager
        typed_config:
          '@type': type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
          stat_prefix: health-check-config
          route_config:
            name: health-check-config-routes
            virtual_hosts:
            - name: app
              domains:
              - '*'
              routes:
              - match:
                  prefix: /
                route:
                  cluster: default/my-service
                  retry_policy:
                    num_retries: 0
          http_filters:
          - name: envoy.filters.http.router
            typed_config:
              '@type': type.googleapis.com/envoy.extensions.filters.http.router.v3.Router
  - '@type': type.googleapis.com/envoy.config.cluster.v3.Cluster
    name: default/my-service
    connect_timeout: 5s
    type: EDS
    health_checks:
    - timeout: 5s
      interval: 10s
      unhealthy_threshold: 3
      healthy_threshold: 2
      http_health_check:
        path: /health
        host: health-check.local
        expected_statuses:
        - start: 200
          end: 300
    outlier_detection:
      consecutive_5xx: 5
      interval: 10s
      base_ejection_time: 30s
      max_ejection_percent: 50
      enforcing_consecutive_5xx: 100
```

这是完整的独立 CEC 链：Service 端口 80 → 具名 Listener → HTTP route → EDS Cluster。Cilium 为引用的 Service 提供 xDS endpoint 配置。创建具有就绪后端的 `default/my-service`，且不要同时将其分配给另一个 CEC 或生成的 Ingress/Gateway 配置。CEC 自定义不是针对 Controller 所有资源的补丁机制。

每个后端都必须实际接受 `Host: health-check.local` 和 `/health`。Envoy 状态范围不含上界，因此 `[200, 300)` 覆盖所有 2xx 响应。主动 health check 和被动 outlier detection 是不同机制；驱逐限制和 panic 行为不能保证排除每一个失败 endpoint。请依据你的后端数量和故障模型验证它们。

### 连接池配置

```yaml
apiVersion: cilium.io/v2
kind: CiliumEnvoyConfig
metadata:
  name: connection-pool
  namespace: default
spec:
  services:
  - name: high-traffic-service
    namespace: default
    ports:
    - 80
    listener: connection-pool-listener
  resources:
  - '@type': type.googleapis.com/envoy.config.listener.v3.Listener
    name: connection-pool-listener
    filter_chains:
    - filters:
      - name: envoy.filters.network.http_connection_manager
        typed_config:
          '@type': type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
          stat_prefix: connection-pool
          route_config:
            name: connection-pool-routes
            virtual_hosts:
            - name: app
              domains:
              - '*'
              routes:
              - match:
                  prefix: /
                route:
                  cluster: default/high-traffic-service
                  retry_policy:
                    num_retries: 0
          http_filters:
          - name: envoy.filters.http.router
            typed_config:
              '@type': type.googleapis.com/envoy.extensions.filters.http.router.v3.Router
  - '@type': type.googleapis.com/envoy.config.cluster.v3.Cluster
    name: default/high-traffic-service
    connect_timeout: 5s
    type: EDS
    typed_extension_protocol_options:
      envoy.extensions.upstreams.http.v3.HttpProtocolOptions:
        '@type': type.googleapis.com/envoy.extensions.upstreams.http.v3.HttpProtocolOptions
        explicit_http_config:
          http2_protocol_options:
            max_concurrent_streams: 1000
            initial_stream_window_size: 65536
            initial_connection_window_size: 1048576
    circuit_breakers:
      thresholds:
      - priority: DEFAULT
        max_connections: 10000
        max_pending_requests: 10000
        max_requests: 10000
        max_retries: 5
```

创建端口 80 上的 `default/high-traffic-service`，其后端显式支持明文 HTTP/2 (h2c)。typed protocol option 选择上游 HTTP/2；它不是自动协议协商。`accept_http_10` 只会接受 HTTP/1.0，并非 HTTP/1.1 连接池设置。对于 HTTP/1 后端，请改为选择对应的显式 HTTP/1 配置。

Circuit-breaker 阈值按 Envoy cluster/priority 计算，并非全局 fleet 配额或容量建议。`max_retries` 限制并发重试；它不是每个请求的重试次数。这里的 route 设置了 `num_retries: 0`。提高连接/流限制需要资源和后端测试；数值仅用于说明。

## 与 AWS Load Balancer Controller 的比较

| 能力 | Cilium Ingress/Gateway | AWS Load Balancer Controller 3.5 |
|---|---|---|
| 数据平面 | eBPF Service/L4 转发；Envoy 用于 HTTP/TLS 功能 | AWS ALB 或 NLB |
| Gateway API | 查看固定的 Cilium 功能/一致性表 | HTTPRoute/GRPCRoute 映射到 ALB；TCPRoute/UDPRoute/TLSRoute 映射到 NLB；不支持在一个 Gateway 上混合 L4/L7 |
| TLS 和身份 | Ingress TLS 终止/透传；workload 加密/身份验证是独立的[安全配置](./03-security.md) | ACM server certificate；ALB 客户端 mTLS 需要其 mutual-authentication mode/trust store |
| 成本 | 节点/代理资源**加上任何已置备的云 LB 和网络费用** | 已置备的 ALB/NLB、容量/使用量和网络费用 |
| 自定义 | 受支持的 Gateway API 功能和单独管理的 CEC；生成对象仍由 Controller 所有 | 通过 LBC API/annotation 公开的 AWS listener/rule/target-group 功能 |
| 性能 | 测量实际拓扑、加密和 workload | 测量相同 workload 和 Service 限制；不存在通用延迟排名 |

LBC 3.5 将 Gateway API **1.6.0** 记录为其经过测试的基线；Cilium 的安装参考使用 **1.6.1**。共享这些 CRD 的集群需要兼容性测试，而非假定最新目录条目受每个 Controller 支持。

针对所需 AWS L7 集成选择 ALB，针对所需传输/target 行为选择 NLB，并根据集群内路由/策略要求选择 Cilium 功能。NLB 目前支持具有 **0–999** 权重的新流量加权 target group；Controller 支持情况以及特定 Route 的语义是不同的问题。普通权重更改会保留现有连接，但根据 AWS 文档，将 target group 的权重设为 **0** 会在短时间后关闭其现有连接。不要将该操作描述为保留连接的排空。

旧的决策图重复了不受支持的成本、延迟、mTLS 和 Gateway API 声明。该表替换了这些断言；它并未移除任一集成选项。

## 监控

### Gateway 指标

```bash
kubectl get gatewayclass cilium -o yaml
kubectl get gateway,httproute,tcproute,tlsroute -A
kubectl -n default describe gateway main-gateway
kubectl -n default get httproute api-routes -o yaml
kubectl -n kube-system exec ds/cilium -- cilium-dbg status --verbose
kubectl -n kube-system exec ds/cilium -- cilium-dbg envoy admin metrics -f downstream_rq
```

### Prometheus 指标

首先使用[可观测性指南](./04-observability.md)启用并抓取 Cilium Envoy Prometheus endpoint。当多个集群向同一个 Prometheus 提供数据时，请配置稳定的 `cluster` target label。原生 Cilium Envoy image 公开 `envoy_http_conn_manager_prefix`，其生成值包括 `listener-insecure`、`listener-secure` 和特定端口变体——而不是固定的 `cilium-gateway` 值。前缀可能在同一 Envoy 上的 Gateway 间复用；这些示例描述的是**已抓取的 proxy/HCM**，而不是保证的按 Gateway 计费。构建 dashboard 前检查实际 label。

以下三个查询显示已开始请求速率、被归类为 5xx 的已完成响应计数器百分比，以及以**秒**为单位的 p99 时长。缺失的 5xx 分子仅从匹配的已观察分母填充；缺失的流量/遥测并不表示健康的零值。正分母 filter 会省略空闲 series。Envoy 的 `downstream_rq_time` histogram 以**毫秒**为单位，因此除以 `/ 1000`。计算 quantile 前，在保留 `le` 的同时聚合 histogram bucket。低样本数、抓取间隙和缺失 histogram 仍需要单独监控。

```promql
sum by (cluster, instance, envoy_http_conn_manager_prefix) (
  rate(envoy_http_downstream_rq_total[5m])
)
```

```promql
100 *
(
  sum by (cluster, instance, envoy_http_conn_manager_prefix) (
    rate(envoy_http_downstream_rq_xx{envoy_response_code_class="5"}[5m])
  )
  or
  0 * sum by (cluster, instance, envoy_http_conn_manager_prefix) (
    rate(envoy_http_downstream_rq_xx[5m])
  )
)
/
(
  sum by (cluster, instance, envoy_http_conn_manager_prefix) (
    rate(envoy_http_downstream_rq_xx[5m])
  ) > 0
)
```

```promql
histogram_quantile(
  0.99,
  sum by (cluster, instance, envoy_http_conn_manager_prefix, le) (
    rate(envoy_http_downstream_rq_time_bucket[5m])
  )
) / 1000
```

## 后续步骤

- [最佳实践](./06-best-practices.md)：操作前提条件和限制

## 参考资料

- [Cilium 1.20.1 Ingress](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/network/servicemesh/ingress.rst)
- [Cilium 流量、源 IP 和策略](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/network/servicemesh/ingress-reference.rst)
- [Cilium Gateway API 安装](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/network/servicemesh/gateway-api/gateway-api.rst)
- [Cilium 1.20.1 Helm values](https://github.com/cilium/cilium/blob/v1.20.1/install/kubernetes/cilium/values.yaml)
- [Gateway API 1.6.1 CRD](https://github.com/kubernetes-sigs/gateway-api/tree/v1.6.1/config/crd/standard)
- [AWS LBC 3.5 NLB 配置](https://github.com/kubernetes-sigs/aws-load-balancer-controller/blob/v3.5.0/docs/guide/service/nlb.md)
- [AWS LBC 3.5 annotation](https://github.com/kubernetes-sigs/aws-load-balancer-controller/blob/v3.5.0/docs/guide/service/annotations.md)
- [AWS LBC 3.5 Gateway API](https://github.com/kubernetes-sigs/aws-load-balancer-controller/blob/v3.5.0/docs/guide/gateway/gateway.md)
- [NLB target group attribute](https://docs.aws.amazon.com/elasticloadbalancing/latest/network/edit-target-group-attributes.html)
- [NLB listener 权重](https://docs.aws.amazon.com/elasticloadbalancing/latest/network/load-balancer-listeners.html)
- [Envoy 1.37 请求统计](https://www.envoyproxy.io/docs/envoy/v1.37.5/configuration/http/http_conn_man/stats)
