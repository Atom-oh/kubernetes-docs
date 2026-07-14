# gRPC 支持

Istio 为 gRPC 协议提供优化的路由和负载均衡。

## 概述

Istio gRPC 支持：
- 基于 HTTP/2 的负载均衡
- gRPC 健康检查
- Deadline 和 Retry
- 基于 Metadata 的路由

## 基本配置

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: grpc-service
spec:
  hosts:
  - grpc-service
  http:
  - match:
    - uri:
        prefix: /mypackage.MyService/
    route:
    - destination:
        host: grpc-service
        subset: v2
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: grpc-service
spec:
  host: grpc-service
  trafficPolicy:
    loadBalancer:
      simple: LEAST_REQUEST  # Suitable for gRPC
    connectionPool:
      http:
        h2UpgradePolicy: UPGRADE
  subsets:
  - name: v2
    labels:
      version: v2
```

## gRPC 健康检查

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: grpc-health-check
spec:
  host: grpc-service
  trafficPolicy:
    outlierDetection:
      consecutiveGatewayErrors: 5
      interval: 30s
      baseEjectionTime: 30s
```

## Retry 配置

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: grpc-retry
spec:
  hosts:
  - grpc-service
  http:
  - route:
    - destination:
        host: grpc-service
    retries:
      attempts: 3
      perTryTimeout: 2s
      retryOn: cancelled,deadline-exceeded,resource-exhausted,unavailable
```

## 参考资料

- [Istio gRPC](https://istio.io/latest/docs/tasks/traffic-management/request-routing/#route-based-on-user-identity)
- [gRPC Load Balancing](https://grpc.io/blog/grpc-load-balancing/)
