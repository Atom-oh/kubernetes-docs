# gRPC Support

> **Verification baseline**: Istio 1.31.0, Kubernetes 1.32–1.36
> **Last reviewed**: September 11, 2026

Istio can route plaintext gRPC HTTP/2 requests by RPC path and metadata, and load-balance new RPCs across eligible endpoints. A long-lived stream stays with its selected backend; scaling replicas does not migrate an existing stream.

## Overview

- Explicitly identify the Service port as `grpc` or `http2`. Application-managed TLS is opaque to a sidecar unless terminated at a configured boundary; mesh mTLS is a separate transport layer.
- Metadata-based routing treats headers as input, not authenticated identity.
- Health probes, passive outlier detection, client deadlines and mesh retries are separate mechanisms that require configuration.

## Basic Configuration

This sidecar example assumes existing workloads with `app: grpc-service`, an eligible `version: v2` backend listening on 9090 and an implementation of `mypackage.MyService`. It does not deploy the server. The `grpc` port declaration establishes HTTP/2; a blanket `h2UpgradePolicy` is unnecessary here. Verify generated endpoints/routes and an actual RPC in the target environment.

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

`LEAST_REQUEST` operates across eligible hosts for new requests. `outlierDetection` passively observes failures of real traffic; it does not send `grpc.health.v1.Health` probes, and its counters follow Envoy's configured error classification.

## gRPC Health Check

Implement the standard gRPC Health Checking Protocol in the application. Kubernetes supports native gRPC readiness/liveness/startup probes; for example, merge this readiness fragment into the existing application container:

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

The native probe uses a numeric port and does not support custom authentication/TLS parameters. Review the application's health listener and Istio probe rewriting/mTLS path. Readiness affects endpoint eligibility; liveness restarts containers and should not treat every downstream dependency failure as a reason to restart.

## Retry Configuration

The following alternative assumes `GetItem` is an **idempotent unary read**. Most gRPC methods use HTTP POST, so HTTP method alone cannot separate safe reads from writes. Match the exact RPC path, and leave mesh retries disabled for other RPCs, including streams and writes.

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

`attempts: 2` allows up to two retries after the initial request, within the total 3-second mesh timeout and the client's own deadline. Backoff/processing means three completed attempts are not guaranteed. Do not automatically retry cancellation, deadline expiry or resource exhaustion. Set realistic client deadlines and ensure server work responds to cancellation; mesh timeout alone is not an application cancellation contract.

Client libraries can also perform transparent/configured retries. Coordinate retry ownership and budgets across layers to avoid amplification. Replaying writes requires application idempotency/deduplication guarantees, and a stream already delivering responses is not safely resumed by this route example.

## References

- [Istio protocol selection](https://istio.io/latest/docs/ops/configuration/traffic-management/protocol-selection/)
- [Istio VirtualService retry API](https://istio.io/latest/docs/reference/config/networking/virtual-service/)
- [Istio DestinationRule](https://istio.io/latest/docs/reference/config/networking/destination-rule/)
- [gRPC deadlines](https://grpc.io/docs/guides/deadlines/)
- [gRPC retries](https://grpc.io/docs/guides/retry/)
- [gRPC health checking](https://grpc.io/docs/guides/health-checking/)
- [Kubernetes probes](https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/)
- [gRPC load balancing background](https://grpc.io/blog/grpc-load-balancing/)
