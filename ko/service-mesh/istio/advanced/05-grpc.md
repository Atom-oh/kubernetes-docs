# gRPC 지원

> **검증 기준**: Istio 1.31.0, Kubernetes 1.32–1.36
> **마지막 검토**: 2026년 9월 11일

Istio는 평문 gRPC HTTP/2 요청을 RPC 경로·metadata로 라우팅하고 새 RPC를 적격 endpoint로 분산할 수 있습니다. 장시간 stream은 선택한 backend에 유지되며 복제본 확장만으로 기존 stream이 이동하지 않습니다.

## 개요

- Service port를 `grpc` 또는 `http2`로 명시합니다. 애플리케이션 자체 TLS는 설정한 경계에서 종료하지 않는 한 sidecar에서 불투명하며, mesh mTLS는 별도 전송 계층입니다.
- Metadata 헤더를 라우팅 입력으로 사용할 수 있지만 인증된 신원으로 간주하지 않습니다.
- Health probe, 수동적 outlier detection, client deadline, mesh retry는 각각 설정해야 하는 별도 기능입니다.

## 기본 설정

이 sidecar 예제는 `app: grpc-service` workload와9090번 포트를 수신하는 `version: v2` backend, `mypackage.MyService` 구현이 이미 있다고 가정합니다. 서버 배포를 포함하지 않습니다. `grpc` port 선언으로 HTTP/2를 명시하므로 모든 연결에 `h2UpgradePolicy`를 추가할 필요가 없습니다. 대상 환경에서 생성된 endpoint/route와 실제 RPC를 검증하세요.

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

`LEAST_REQUEST`는 새 요청을 적격 host 사이에 분산합니다. `outlierDetection`은 실제 트래픽의 실패를 수동적으로 관찰하며 `grpc.health.v1.Health` probe를 보내지 않습니다. 오류 카운터는 Envoy의 설정된 오류 분류를 따릅니다.

## gRPC 헬스 체크

애플리케이션에 표준 gRPC Health Checking Protocol을 구현합니다. Kubernetes의 native gRPC readiness/liveness/startup probe를 사용할 수 있으며, 다음 readiness 조각을 기존 애플리케이션 container에 병합할 수 있습니다.

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

Native probe는 숫자 포트를 사용하고 별도 인증/TLS parameter를 지원하지 않습니다. 앱의 health listener와 Istio probe rewrite/mTLS 경로를 검토하세요. Readiness는 endpoint 포함 여부에 영향을 주며, liveness는 container를 재시작하므로 모든 downstream 의존성 장애를 재시작 사유로 취급하지 않아야 합니다.

## Retry 설정

다음 대안은 `GetItem`이 **멱등적인 unary 읽기**라고 가정합니다. 대부분의 gRPC method는 HTTP POST를 사용하므로 HTTP method만으로 읽기와 쓰기를 구분할 수 없습니다. 정확한 RPC 경로를 매칭하고 다른 RPC·stream·쓰기는 mesh 재시도를 끕니다.

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

`attempts: 2`는 최초 요청 이후 최대 두 번의 재시도를 허용하며 전체3초 mesh timeout과 client deadline의 제한을 받습니다. Backoff·처리 시간 때문에 세 번의 완료를 보장하지 않습니다. 취소·deadline 만료·resource exhaustion을 무조건 재시도하지 마세요. Client deadline을 적절히 설정하고 서버 작업이 취소에 반응하도록 구현해야 하며 mesh timeout만으로 이를 보장할 수 없습니다.

Client library도 transparent/configured retry를 수행할 수 있으므로 계층별 retry 담당과 예산을 조율하여 호출 증폭을 막습니다. 쓰기 재생에는 애플리케이션의 멱등성·중복 제거 보장이 필요하며, 이미 응답을 전달한 stream을 이 route로 안전하게 재개할 수는 없습니다.

## 참고 자료

- [Istio protocol selection](https://istio.io/latest/docs/ops/configuration/traffic-management/protocol-selection/)
- [Istio VirtualService retry API](https://istio.io/latest/docs/reference/config/networking/virtual-service/)
- [Istio DestinationRule](https://istio.io/latest/docs/reference/config/networking/destination-rule/)
- [gRPC deadlines](https://grpc.io/docs/guides/deadlines/)
- [gRPC retries](https://grpc.io/docs/guides/retry/)
- [gRPC health checking](https://grpc.io/docs/guides/health-checking/)
- [Kubernetes probes](https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/)
- [gRPC load balancing background](https://grpc.io/blog/grpc-load-balancing/)
