# WebSocket 지원

Istio는 WebSocket 프로토콜을 위한 장시간 연결 지원을 제공합니다.

## 개요

WebSocket 지원 기능:
- 장시간 연결 유지
- Upgrade 헤더 처리
- Idle Timeout 관리

## 기본 설정

```yaml
apiVersion: networking.istio.io/v1beta1
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
apiVersion: networking.istio.io/v1beta1
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
        idleTimeout: 3600s  # 1시간
```

## Gateway 설정

```yaml
apiVersion: networking.istio.io/v1beta1
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

## 모범 사례

1. **Idle Timeout**: 적절한 idle timeout 설정
2. **Connection Pool**: 최대 연결 수 조정
3. **모니터링**: 연결 수 및 상태 확인

## 참고 자료

- [Istio WebSocket](https://istio.io/latest/docs/tasks/traffic-management/tcp-traffic-shifting/)
