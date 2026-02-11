# WebSocket Support

Istio provides long-lived connection support for the WebSocket protocol.

## Overview

WebSocket support features:
- Long-lived connection maintenance
- Upgrade header handling
- Idle Timeout management

## Basic Configuration

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

## Gateway Configuration

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

## Best Practices

1. **Idle Timeout**: Set appropriate idle timeout
2. **Connection Pool**: Adjust maximum connection count
3. **Monitoring**: Check connection count and status

## References

- [Istio WebSocket](https://istio.io/latest/docs/tasks/traffic-management/tcp-traffic-shifting/)
