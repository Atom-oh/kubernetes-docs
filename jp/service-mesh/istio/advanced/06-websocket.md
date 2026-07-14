# WebSocket サポート

Istio は WebSocket プロトコル向けに長時間接続サポートを提供します。

## 概要

WebSocket サポートの機能:
- 長時間接続の維持
- Upgrade ヘッダーの処理
- Idle Timeout の管理

## 基本設定

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

## Gateway 設定

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

## ベストプラクティス

1. **Idle Timeout**: 適切な idle timeout を設定する
2. **Connection Pool**: 最大接続数を調整する
3. **Monitoring**: 接続数とステータスを確認する

## 参照

- [Istio WebSocket](https://istio.io/latest/docs/tasks/traffic-management/tcp-traffic-shifting/)
