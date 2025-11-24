# gRPC 지원

Istio는 gRPC 프로토콜을 위한 최적화된 라우팅과 로드 밸런싱을 제공합니다.

## 개요

Istio gRPC 지원:
- HTTP/2 기반 로드 밸런싱
- gRPC 헬스 체크
- Deadlines 및 Retries
- 메타데이터 기반 라우팅

## 기본 설정

```yaml
apiVersion: networking.istio.io/v1beta1
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
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: grpc-service
spec:
  host: grpc-service
  trafficPolicy:
    loadBalancer:
      simple: LEAST_REQUEST  # gRPC에 적합
    connectionPool:
      http:
        h2UpgradePolicy: UPGRADE
  subsets:
  - name: v2
    labels:
      version: v2
```

## gRPC 헬스 체크

```yaml
apiVersion: networking.istio.io/v1beta1
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

## Retry 설정

```yaml
apiVersion: networking.istio.io/v1beta1
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

## 참고 자료

- [Istio gRPC](https://istio.io/latest/docs/tasks/traffic-management/request-routing/#route-based-on-user-identity)
- [gRPC Load Balancing](https://grpc.io/blog/grpc-load-balancing/)
