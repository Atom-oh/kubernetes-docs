# Soporte de WebSocket

Istio proporciona soporte para conexiones de larga duración para el protocolo WebSocket.

## Descripción general

Características del soporte de WebSocket:
- Mantenimiento de conexiones de larga duración
- Gestión del encabezado Upgrade
- Gestión de Idle Timeout

## Configuración básica

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

## Configuración de Gateway

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

## Prácticas recomendadas

1. **Idle Timeout**: Establece un tiempo de espera de inactividad adecuado
2. **Connection Pool**: Ajusta el número máximo de conexiones
3. **Monitoring**: Comprueba el número y el estado de las conexiones

## Referencias

- [Istio WebSocket](https://istio.io/latest/docs/tasks/traffic-management/tcp-traffic-shifting/)
