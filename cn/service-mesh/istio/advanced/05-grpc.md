# gRPC 支持

> **验证基线**：Istio 1.31.0, Kubernetes 1.32–1.37
> **最后审核时间**：2026 年 10 月 16 日

Istio 可以根据 RPC 路径和元数据路由明文 gRPC HTTP/2 请求，并在符合条件的端点之间对新 RPC 进行负载均衡。长时间运行的流会继续连接到选定的后端；扩容副本不会迁移现有流。

## 概述

- 明确将 Service 端口标识为 `grpc` 或 `http2`。除非在配置的边界处终止 TLS，否则 sidecar 无法解析由应用管理的 TLS；网格 mTLS 是独立的传输层。
- 基于元数据的路由会将标头视为输入，而非经过身份验证的身份。
- 健康探测、被动异常主机检测（outlier detection）、客户端截止时间和网格重试是彼此独立的机制，需要分别配置。

## 基本配置

此 sidecar 示例假设现有工作负载带有 `app: grpc-service`，符合条件的 `version: v2` 后端在 9090 端口上监听，并且已实现 `mypackage.MyService`。此示例不会部署服务器。`grpc` 端口声明会建立 HTTP/2；此处不需要统一设置 `h2UpgradePolicy`。请在目标环境中验证生成的端点/路由以及实际 RPC。

```yaml
apiVersion: v1
kind: Service
metadata:
  name: grpc-service
  namespace: default
spec:
  selector:
    app: grpc-service
  ports:
  - name: grpc
    port: 9090
    targetPort: 9090
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: grpc-service
  namespace: default
spec:
  hosts: ["grpc-service"]
  http:
  - match:
    - uri:
        prefix: /mypackage.MyService/
    route:
    - destination:
        host: grpc-service
        subset: v2
        port:
          number: 9090
    retries:
      attempts: 0
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: grpc-service
  namespace: default
spec:
  host: grpc-service
  trafficPolicy:
    loadBalancer:
      simple: LEAST_REQUEST
    outlierDetection:
      consecutiveGatewayErrors: 5
      interval: 30s
      baseEjectionTime: 30s
  subsets:
  - name: v2
    labels:
      version: v2
```

`LEAST_REQUEST` 会在符合条件的主机之间处理新请求的负载均衡。`outlierDetection` 会被动观察真实流量中的故障；它不会发送 `grpc.health.v1.Health` 探测，其计数器遵循 Envoy 配置的错误分类。

## gRPC 健康检查

在应用中实现标准 gRPC 健康检查协议。Kubernetes 支持原生 gRPC 就绪、存活和启动探测；例如，将此就绪探测片段合并到现有应用容器中：

```yaml
# Existing application container fragment, not a complete Pod
name: app
readinessProbe:
  grpc:
    port: 9090
  initialDelaySeconds: 5
  periodSeconds: 10
  timeoutSeconds: 1
  failureThreshold: 3
```

原生探测使用数字端口，不支持自定义身份验证/TLS 参数。请检查应用的健康检查监听器以及 Istio 的探测重写/mTLS 路径。就绪状态会影响端点是否符合条件；存活探测会重启容器，不应将每次下游依赖故障都视为重启理由。

## 重试配置

以下替代方案假设 `GetItem` 是一个**幂等的单次读取 RPC（unary，即单请求/单响应）**。大多数 gRPC 方法使用 HTTP POST，因此仅凭 HTTP 方法无法区分安全读取和写入。请匹配精确的 RPC 路径，并对其他 RPC（包括流和写入操作）禁用网格重试。

```yaml
# Alternative to the VirtualService above; do not create a second competing route.
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: grpc-service
  namespace: default
spec:
  hosts: ["grpc-service"]
  http:
  - name: idempotent-unary-read
    match:
    - uri:
        exact: /mypackage.MyService/GetItem
    route:
    - destination:
        host: grpc-service
        subset: v2
        port:
          number: 9090
    timeout: 3s
    retries:
      attempts: 2
      perTryTimeout: 1s
      retryOn: unavailable
  - name: other-rpcs
    match:
    - uri:
        prefix: /mypackage.MyService/
    route:
    - destination:
        host: grpc-service
        subset: v2
        port:
          number: 9090
    retries:
      attempts: 0
```

`attempts: 2` 表示初始请求后最多可重试两次，且须在 3 秒的网格总超时时间和客户端自身的截止时间内完成。受退避/处理时间影响，不保证能完成三次尝试。不要自动重试取消、截止时间到期或资源耗尽的请求。设置合理的客户端截止时间，并确保服务器工作能够响应取消；网格超时本身并不构成应用级取消约定。

客户端库也可能执行透明重试或配置的重试。请协调各层的重试责任和预算，以避免放大效应。重放写入操作需要应用层提供幂等性/去重保证；而已经开始发送响应的流不能通过此路由示例安全地恢复。

## 参考资料

- [Istio 协议选择](https://istio.io/latest/docs/ops/configuration/traffic-management/protocol-selection/)
- [Istio VirtualService 重试 API](https://istio.io/latest/docs/reference/config/networking/virtual-service/)
- [Istio DestinationRule](https://istio.io/latest/docs/reference/config/networking/destination-rule/)
- [gRPC 截止时间](https://grpc.io/docs/guides/deadlines/)
- [gRPC 重试](https://grpc.io/docs/guides/retry/)
- [gRPC 健康检查](https://grpc.io/docs/guides/health-checking/)
- [Kubernetes 探测](https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/)
- [gRPC 负载均衡背景介绍](https://grpc.io/blog/grpc-load-balancing/)
