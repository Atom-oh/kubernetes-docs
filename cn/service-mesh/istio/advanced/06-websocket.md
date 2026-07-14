# WebSocket 支持

Istio 为 WebSocket 协议提供长连接支持。

## 概述

WebSocket 支持的特性：
- 长连接维护
- Upgrade header 处理
- Idle Timeout 管理

## 基本配置

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: websocket-service
spec:
  hosts:
  - ws.example.com
  http:
  - match:
    - headers:
        upgrade:
          exact: websocket
    route:
    - destination:
        host: websocket-service
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: websocket-service
spec:
  host: websocket-service
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 1000
      http:
        http1MaxPendingRequests: 1000
        idleTimeout: 3600s  # 1 hour
```

## Gateway 配置

```yaml
apiVersion: networking.istio.io/v1
kind: Gateway
metadata:
  name: websocket-gateway
spec:
  selector:
    istio: ingressgateway
  servers:
  - port:
      number: 80
      name: http
      protocol: HTTP
    hosts:
    - ws.example.com
```

## 最佳实践

1. **Idle Timeout**：设置合适的空闲超时时间
2. **Connection Pool**：调整最大连接数
3. **Monitoring**：检查连接数和状态

## 参考资料

- [Istio WebSocket](https://istio.io/latest/docs/tasks/traffic-management/tcp-traffic-shifting/)
