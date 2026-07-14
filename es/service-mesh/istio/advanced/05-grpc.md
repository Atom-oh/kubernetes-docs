# Soporte de gRPC

Istio proporciona enrutamiento y balanceo de carga optimizados para el protocolo gRPC.

## Descripción general

Soporte de gRPC de Istio:
- Balanceo de carga basado en HTTP/2
- Comprobaciones de estado de gRPC
- Plazos y reintentos
- Enrutamiento basado en metadatos

## Configuración básica

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

## Comprobación de estado de gRPC

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

## Configuración de reintentos

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

## Referencias

- [gRPC de Istio](https://istio.io/latest/docs/tasks/traffic-management/request-routing/#route-based-on-user-identity)
- [Balanceo de carga de gRPC](https://grpc.io/blog/grpc-load-balancing/)
