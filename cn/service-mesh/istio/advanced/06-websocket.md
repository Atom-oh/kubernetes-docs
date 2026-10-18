# WebSocket 支持

> **验证基线**：Istio 1.31.0，Kubernetes 1.32–1.37
> **上次审阅**：2026年10月16日

Istio 会在其生成的 HTTP connection manager 中启用 WebSocket 升级。本示例介绍在 ingress gateway 处终止 TLS 的 HTTP/1.1 Upgrade。HTTP/2 Extended CONNECT 和 HTTP/3 需要在整个链路中单独提供支持/配置。

## 基本配置

前提条件：现有的 ingress gateway Deployment/Service，暴露端口 443 并带有下方所示标签；`ws.example.com` 的 DNS 可正常工作；gateway 工作负载命名空间中有 `ws-tls` 证书/密钥 Secret；以及现有的 `app: websocket-service` Pods，在 8080 端口上提供 `/ws` 服务。请将示例域名替换为证书所涵盖的真实域名。以下资源不会部署应用，也不会配置负载均衡器/证书。

```yaml
apiVersion: v1
kind: Service
metadata:
  name: websocket-service
  namespace: default
spec:
  selector:
    app: websocket-service
  ports:
  - name: http
    port: 8080
    targetPort: 8080
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: websocket-service
  namespace: default
spec:
  hosts: ["ws.example.com"]
  gateways: ["istio-system/websocket-gateway"]
  http:
  - match:
    - uri:
        exact: /ws
    - uri:
        prefix: /ws/
    route:
    - destination:
        host: websocket-service.default.svc.cluster.local
        port:
          number: 8080
    retries:
      attempts: 0
```

下方的 Gateway 会显式绑定此路由。匹配路径可以避免不必要地匹配区分大小写的 `Upgrade` header；应用仍会验证 WebSocket 握手。Mesh 重试已禁用。VirtualService 未设置请求超时，因此使用 Istio 默认禁用的路由超时；这不会禁用链路中所有连接/流的超时。

## Gateway 配置

```yaml
apiVersion: networking.istio.io/v1
kind: Gateway
metadata:
  name: websocket-gateway
  namespace: istio-system
spec:
  selector:
    istio: ingressgateway
  servers:
  - port:
      number: 443
      name: https
      protocol: HTTPS
    tls:
      mode: SIMPLE
      credentialName: ws-tls
    hosts: ["ws.example.com"]
```

客户端使用 `wss://ws.example.com/ws`。gateway 终止客户端 TLS，然后使用已配置的 mesh/后端传输方式。应用身份验证、Origin 检查和授权仍然必不可少。如果代理/负载均衡器更早终止 TLS，请分别检查该拓扑中的协议、证书和 header 信任设置。

## 连接与超时管理

以下可选的 DestinationRule 保留了原示例中的限制值，作为**负载测试的示例输入**：

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: websocket-service
  namespace: default
spec:
  host: websocket-service.default.svc.cluster.local
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 1000
      http:
        http1MaxPendingRequests: 1000
        idleTimeout: 3600s
```

`maxConnections` 和待处理请求数是针对每个代理的目标池控制项，并不保证整个集群的 WebSocket 容量。`connectionPool.http.idleTimeout` 表示 HTTP 连接上没有活动请求/流；它不是活动 WebSocket 的一小时生命周期限制，也不是空闲消息限制。

检查生成的 HCM/路由流空闲设置、最大流/连接持续时间、应用心跳/关闭策略，以及每个中间代理的空闲超时。Istio 的 HCM 生成逻辑和已安装的 ConnectionSettings 可以覆盖 Envoy 默认值。缓冲/请求体处理过滤器可能与升级不兼容。副本扩容时，现有 WebSocket 不会迁移；请规划连接排空和应用感知的重新连接，避免盲目重放写入操作。

## 验证

```bash
# Inspect the selected gateway and backend configuration.
istioctl proxy-config routes <gateway-pod> -n istio-system
istioctl proxy-config clusters <gateway-pod> -n istio-system --fqdn websocket-service.default.svc.cluster.local

# Bounded HTTP/1.1 handshake check; certificate validation remains enabled.
curl --http1.1 --include --max-time 5 https://ws.example.com/ws -H 'Connection: Upgrade' -H 'Upgrade: websocket' -H 'Sec-WebSocket-Version: 13' -H 'Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ=='
```

对于此 HTTP/1.1 检查，正常情况下，有效的服务器会返回 101，并提供匹配的 `Sec-WebSocket-Accept`。curl 命令只检查握手；其 5 秒截止时间可能会结束原本仍保持打开的连接，并返回退出码 28。请使用真实的 WebSocket 客户端测试帧、ping/pong、应用身份验证、持续空闲时段、关闭代码以及发布/重新连接行为。本文档审查未测试任何部署或实时会话。

## 参考资料

- [Envoy HTTP 升级](https://www.envoyproxy.io/docs/envoy/latest/intro/arch_overview/http/upgrades)
- [Envoy 超时类型](https://www.envoyproxy.io/docs/envoy/latest/faq/configuration/timeouts)
- [Istio 安全 ingress](https://istio.io/latest/docs/tasks/traffic-management/ingress/secure-ingress/)
- [Istio VirtualService](https://istio.io/latest/docs/reference/config/networking/virtual-service/)
- [Istio DestinationRule](https://istio.io/latest/docs/reference/config/networking/destination-rule/)
- [Istio 1.31 HCM 生成逻辑](https://raw.githubusercontent.com/istio/istio/1.31.0/pilot/pkg/networking/core/listener_builder.go)
