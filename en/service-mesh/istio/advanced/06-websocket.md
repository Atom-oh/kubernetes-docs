# WebSocket Support

> **Verification baseline**: Istio 1.31.0, Kubernetes 1.32–1.36
> **Last reviewed**: September 11, 2026

Istio enables WebSocket upgrades in its generated HTTP connection manager. This example covers HTTP/1.1 Upgrade with TLS terminated at the ingress gateway. HTTP/2 Extended CONNECT and HTTP/3 need separate support/configuration across the entire path.

## Basic Configuration

Prerequisites: an existing ingress gateway Deployment/Service exposing 443 with the shown label, working DNS for `ws.example.com`, a `ws-tls` certificate/key Secret in the gateway workload namespace, and existing `app: websocket-service` Pods serving `/ws` on 8080. Replace the example domain with the real name covered by the certificate. The following resources do not deploy the application or provision the load balancer/certificate.

```yaml
apiVersion: v1
kind: Service
metadata:
  name: websocket-service
  namespace: default
spec:
  selector:
    app: websocket-service
  ports:
  - name: http
    port: 8080
    targetPort: 8080
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: websocket-service
  namespace: default
spec:
  hosts: ["ws.example.com"]
  gateways: ["istio-system/websocket-gateway"]
  http:
  - match:
    - uri:
        exact: /ws
    - uri:
        prefix: /ws/
    route:
    - destination:
        host: websocket-service.default.svc.cluster.local
        port:
          number: 8080
    retries:
      attempts: 0
```

The route is explicitly bound to the Gateway below. Matching the path avoids an unnecessary case-sensitive `Upgrade` header match; the application still validates the WebSocket handshake. Mesh retries are disabled. The VirtualService request timeout is omitted, using Istio's default-disabled route timeout; this does not disable every connection/stream timeout along the path.

## Gateway Configuration

```yaml
apiVersion: networking.istio.io/v1
kind: Gateway
metadata:
  name: websocket-gateway
  namespace: istio-system
spec:
  selector:
    istio: ingressgateway
  servers:
  - port:
      number: 443
      name: https
      protocol: HTTPS
    tls:
      mode: SIMPLE
      credentialName: ws-tls
    hosts: ["ws.example.com"]
```

Clients use `wss://ws.example.com/ws`. The gateway terminates viewer TLS, then uses the configured mesh/backend transport. Application authentication, Origin checks and authorization remain necessary. If a proxy/load balancer terminates TLS earlier, review that topology's protocol, certificate and header trust separately.

## Connection and Timeout Management

This optional DestinationRule preserves the original example limits as **illustrative inputs to load testing**:

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: websocket-service
  namespace: default
spec:
  host: websocket-service.default.svc.cluster.local
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 1000
      http:
        http1MaxPendingRequests: 1000
        idleTimeout: 3600s
```

`maxConnections` and pending requests are per-proxy destination-pool controls, not a cluster-wide WebSocket capacity guarantee. `connectionPool.http.idleTimeout` means an HTTP connection has no active requests/streams; it is not a one-hour lifetime or idle-message limit for an active WebSocket.

Inspect the generated HCM/route stream idle settings, maximum stream/connection duration, application heartbeat/close policy and every intermediary's idle timeout. Istio's HCM generation and installed ConnectionSettings can override Envoy defaults. Buffering/body-processing filters can be incompatible with upgrades. Existing WebSockets do not migrate when replicas scale; plan draining and application-aware reconnection without replaying writes blindly.

## Verification

```bash
# Inspect the selected gateway and backend configuration.
istioctl proxy-config routes <gateway-pod> -n istio-system
istioctl proxy-config clusters <gateway-pod> -n istio-system --fqdn websocket-service.default.svc.cluster.local

# Bounded HTTP/1.1 handshake check; certificate validation remains enabled.
curl --http1.1 --include --max-time 5 https://ws.example.com/ws -H 'Connection: Upgrade' -H 'Upgrade: websocket' -H 'Sec-WebSocket-Version: 13' -H 'Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ=='
```

For this HTTP/1.1 check, a valid server normally responds with 101 and a matching `Sec-WebSocket-Accept`. The curl command checks the handshake only; its 5-second deadline may end an otherwise-open connection with exit 28. Use a real WebSocket client to test frames, ping/pong, application authentication, sustained idle periods, close codes and rollout/reconnect behavior. No deployment or live session was tested by this documentation audit.

## References

- [Envoy HTTP upgrades](https://www.envoyproxy.io/docs/envoy/latest/intro/arch_overview/http/upgrades)
- [Envoy timeout types](https://www.envoyproxy.io/docs/envoy/latest/faq/configuration/timeouts)
- [Istio secure ingress](https://istio.io/latest/docs/tasks/traffic-management/ingress/secure-ingress/)
- [Istio VirtualService](https://istio.io/latest/docs/reference/config/networking/virtual-service/)
- [Istio DestinationRule](https://istio.io/latest/docs/reference/config/networking/destination-rule/)
- [Istio 1.31 HCM generation](https://raw.githubusercontent.com/istio/istio/1.31.0/pilot/pkg/networking/core/listener_builder.go)
