# gRPC Support

Istio provides optimized routing and load balancing for the gRPC protocol.

## Overview

Istio gRPC support:
- HTTP/2 based load balancing
- gRPC health checks
- Deadlines and Retries
- Metadata-based routing

## Basic Configuration

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

## gRPC Health Check

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

## Retry Configuration

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

## References

- [Istio gRPC](https://istio.io/latest/docs/tasks/traffic-management/request-routing/#route-based-on-user-identity)
- [gRPC Load Balancing](https://grpc.io/blog/grpc-load-balancing/)
