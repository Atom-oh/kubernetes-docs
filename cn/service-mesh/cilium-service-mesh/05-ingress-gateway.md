# Cilium Service Mesh Ingress 与 Gateway

> **支持版本**: Cilium 1.16+, Kubernetes 1.28+
> **最后更新**: February 22, 2026

## 概述

Cilium Service Mesh 原生支持 Kubernetes Ingress Controller 和 Gateway API。它使用基于 eBPF 的高性能数据路径高效处理外部流量，提供 L7 路由、TLS 终止和负载均衡等功能。

## 架构

```mermaid
graph TB
    subgraph "External"
        Client[External Client]
        LB[Cloud Load Balancer<br/>NLB/ALB]
    end

    subgraph "Kubernetes Cluster"
        subgraph "Cilium Ingress/Gateway"
            GW[Gateway<br/>or Ingress]
            Envoy[Cilium Envoy<br/>L7 Proxy]
        end

        subgraph "Backend Services"
            SvcA[Service A]
            SvcB[Service B]
            SvcC[Service C]
        end
    end

    Client --> LB
    LB --> GW
    GW --> Envoy
    Envoy --> SvcA
    Envoy --> SvcB
    Envoy --> SvcC
```

## Cilium Ingress Controller

### 安装与启用

```yaml
# values.yaml
ingressController:
  enabled: true

  # Load balancer mode
  loadbalancerMode: shared  # shared or dedicated

  # Default backend service
  default: true

  # Ingress Class name
  ingressClassName: cilium

  # Service configuration
  service:
    type: LoadBalancer
    annotations:
      # Use EKS NLB
      service.beta.kubernetes.io/aws-load-balancer-type: "nlb"
      service.beta.kubernetes.io/aws-load-balancer-scheme: "internet-facing"
```

### Ingress 资源示例

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: app-ingress
  namespace: default
  annotations:
    # Cilium-specific annotations
    ingress.cilium.io/loadbalancer-mode: shared
    ingress.cilium.io/tls-passthrough: "false"
spec:
  ingressClassName: cilium
  tls:
  - hosts:
    - app.example.com
    secretName: app-tls-secret
  rules:
  - host: app.example.com
    http:
      paths:
      - path: /api
        pathType: Prefix
        backend:
          service:
            name: api-service
            port:
              number: 80
      - path: /
        pathType: Prefix
        backend:
          service:
            name: frontend-service
            port:
              number: 80
```

### 基于路径的路由

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: path-routing
  namespace: default
spec:
  ingressClassName: cilium
  rules:
  - host: api.example.com
    http:
      paths:
      # /users/* -> users-service
      - path: /users
        pathType: Prefix
        backend:
          service:
            name: users-service
            port:
              number: 80

      # /orders/* -> orders-service
      - path: /orders
        pathType: Prefix
        backend:
          service:
            name: orders-service
            port:
              number: 80

      # /products/* -> products-service
      - path: /products
        pathType: Prefix
        backend:
          service:
            name: products-service
            port:
              number: 80

      # Exact path matching
      - path: /health
        pathType: Exact
        backend:
          service:
            name: health-service
            port:
              number: 80
```

### TLS 终止

```yaml
# Create TLS Secret
apiVersion: v1
kind: Secret
metadata:
  name: app-tls-secret
  namespace: default
type: kubernetes.io/tls
data:
  tls.crt: <base64-encoded-cert>
  tls.key: <base64-encoded-key>
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: tls-ingress
  namespace: default
spec:
  ingressClassName: cilium
  tls:
  - hosts:
    - secure.example.com
    secretName: app-tls-secret
  rules:
  - host: secure.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: secure-app
            port:
              number: 80
```

### TLS 透传

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: tls-passthrough
  namespace: default
  annotations:
    ingress.cilium.io/tls-passthrough: "true"
spec:
  ingressClassName: cilium
  rules:
  - host: backend.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: tls-backend
            port:
              number: 443
```

## Gateway API

### 启用 Gateway API

```yaml
# values.yaml
gatewayAPI:
  enabled: true

  # Gateway Controller settings
  secretNamespace: kube-system

  # Gateway Class name
  gatewayClassName: cilium
```

### GatewayClass

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: GatewayClass
metadata:
  name: cilium
spec:
  controllerName: io.cilium/gateway-controller
  description: "Cilium Gateway Controller"
```

### Gateway

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: main-gateway
  namespace: default
spec:
  gatewayClassName: cilium

  listeners:
  # HTTP listener
  - name: http
    protocol: HTTP
    port: 80
    hostname: "*.example.com"
    allowedRoutes:
      namespaces:
        from: Same

  # HTTPS listener
  - name: https
    protocol: HTTPS
    port: 443
    hostname: "*.example.com"
    tls:
      mode: Terminate
      certificateRefs:
      - kind: Secret
        name: wildcard-tls
        namespace: default
    allowedRoutes:
      namespaces:
        from: Same

  # TCP listener
  - name: tcp
    protocol: TCP
    port: 9000
    allowedRoutes:
      namespaces:
        from: Same
      kinds:
      - kind: TCPRoute
```

### HTTPRoute

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: api-routes
  namespace: default
spec:
  parentRefs:
  - name: main-gateway
    namespace: default
    sectionName: https

  hostnames:
  - "api.example.com"

  rules:
  # Path-based routing
  - matches:
    - path:
        type: PathPrefix
        value: /v1/users
    backendRefs:
    - name: users-v1
      port: 80

  - matches:
    - path:
        type: PathPrefix
        value: /v2/users
    backendRefs:
    - name: users-v2
      port: 80

  # Header-based routing
  - matches:
    - path:
        type: PathPrefix
        value: /api
      headers:
      - name: X-API-Version
        value: "2"
    backendRefs:
    - name: api-v2
      port: 80

  # Default route
  - matches:
    - path:
        type: PathPrefix
        value: /
    backendRefs:
    - name: api-v1
      port: 80
```

### 基于权重的流量拆分

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: canary-route
  namespace: default
spec:
  parentRefs:
  - name: main-gateway

  hostnames:
  - "app.example.com"

  rules:
  - matches:
    - path:
        type: PathPrefix
        value: /
    backendRefs:
    # 90% -> stable
    - name: app-stable
      port: 80
      weight: 90
    # 10% -> canary
    - name: app-canary
      port: 80
      weight: 10
```

### 请求/响应转换

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: transform-route
  namespace: default
spec:
  parentRefs:
  - name: main-gateway

  rules:
  - matches:
    - path:
        type: PathPrefix
        value: /api

    filters:
    # Request header modification
    - type: RequestHeaderModifier
      requestHeaderModifier:
        add:
        - name: X-Request-ID
          value: "generated-id"
        - name: X-Forwarded-By
          value: "cilium-gateway"
        set:
        - name: Host
          value: "internal-api.default.svc"
        remove:
        - X-Internal-Header

    # URL rewrite
    - type: URLRewrite
      urlRewrite:
        hostname: internal-api.default.svc
        path:
          type: ReplacePrefixMatch
          replacePrefixMatch: /v2/api

    # Response header modification
    - type: ResponseHeaderModifier
      responseHeaderModifier:
        add:
        - name: X-Response-Time
          value: "computed"
        remove:
        - Server

    backendRefs:
    - name: api-service
      port: 80
```

### 重定向

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: redirect-route
  namespace: default
spec:
  parentRefs:
  - name: main-gateway

  rules:
  # HTTP -> HTTPS redirect
  - matches:
    - path:
        type: PathPrefix
        value: /
    filters:
    - type: RequestRedirect
      requestRedirect:
        scheme: https
        statusCode: 301

  # Path redirect
  - matches:
    - path:
        type: Exact
        value: /old-path
    filters:
    - type: RequestRedirect
      requestRedirect:
        path:
          type: ReplaceFullPath
          replaceFullPath: /new-path
        statusCode: 301

  # Host redirect
  - matches:
    - path:
        type: PathPrefix
        value: /legacy
    filters:
    - type: RequestRedirect
      requestRedirect:
        hostname: legacy.example.com
        statusCode: 302
```

### TCPRoute

```yaml
apiVersion: gateway.networking.k8s.io/v1alpha2
kind: TCPRoute
metadata:
  name: tcp-route
  namespace: default
spec:
  parentRefs:
  - name: main-gateway
    sectionName: tcp

  rules:
  - backendRefs:
    - name: tcp-service
      port: 9000
```

### TLSRoute

```yaml
apiVersion: gateway.networking.k8s.io/v1alpha2
kind: TLSRoute
metadata:
  name: tls-route
  namespace: default
spec:
  parentRefs:
  - name: main-gateway

  hostnames:
  - "secure.example.com"

  rules:
  - backendRefs:
    - name: tls-backend
      port: 443
```

## EKS 集成模式

### NLB + Cilium Ingress

```yaml
# values.yaml
ingressController:
  enabled: true
  loadbalancerMode: shared
  service:
    type: LoadBalancer
    annotations:
      # Use NLB
      service.beta.kubernetes.io/aws-load-balancer-type: "nlb"
      service.beta.kubernetes.io/aws-load-balancer-scheme: "internet-facing"

      # NLB target type
      service.beta.kubernetes.io/aws-load-balancer-nlb-target-type: "ip"

      # Cross-zone load balancing
      service.beta.kubernetes.io/aws-load-balancer-cross-zone-load-balancing-enabled: "true"

      # Health check
      service.beta.kubernetes.io/aws-load-balancer-healthcheck-protocol: "HTTP"
      service.beta.kubernetes.io/aws-load-balancer-healthcheck-path: "/healthz"
      service.beta.kubernetes.io/aws-load-balancer-healthcheck-interval: "10"

      # Proxy protocol (preserve client IP)
      service.beta.kubernetes.io/aws-load-balancer-proxy-protocol: "*"
```

### ALB + Cilium

```yaml
# Use with ALB Ingress Controller
# ALB -> NodePort -> Cilium -> Pods

apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: alb-to-cilium
  namespace: default
  annotations:
    kubernetes.io/ingress.class: alb
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/backend-protocol: HTTP
spec:
  rules:
  - host: app.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: cilium-ingress  # Cilium Ingress Service
            port:
              number: 80
```

### 混合架构

```mermaid
graph TB
    subgraph "Internet"
        Client[External Client]
    end

    subgraph "AWS"
        ALB[Application<br/>Load Balancer]
        NLB[Network<br/>Load Balancer]
    end

    subgraph "EKS Cluster"
        subgraph "Cilium Layer"
            CiliumGW[Cilium Gateway<br/>L7 Routing]
            CiliumLB[Cilium LB<br/>L4 Load Balancing]
        end

        subgraph "Applications"
            WebApp[Web App]
            API[API Server]
            gRPC[gRPC Service]
        end
    end

    Client --> ALB
    Client --> NLB

    ALB --> CiliumGW
    NLB --> CiliumLB

    CiliumGW --> WebApp
    CiliumGW --> API
    CiliumLB --> gRPC
```

## 多租户 Gateway

### 每个 Namespace 的 Gateway

```yaml
# Shared GatewayClass
apiVersion: gateway.networking.k8s.io/v1
kind: GatewayClass
metadata:
  name: cilium-shared
spec:
  controllerName: io.cilium/gateway-controller
---
# Team A Gateway
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: team-a-gateway
  namespace: team-a
spec:
  gatewayClassName: cilium-shared
  listeners:
  - name: https
    protocol: HTTPS
    port: 443
    hostname: "*.team-a.example.com"
    tls:
      mode: Terminate
      certificateRefs:
      - kind: Secret
        name: team-a-tls
    allowedRoutes:
      namespaces:
        from: Same
---
# Team B Gateway
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: team-b-gateway
  namespace: team-b
spec:
  gatewayClassName: cilium-shared
  listeners:
  - name: https
    protocol: HTTPS
    port: 443
    hostname: "*.team-b.example.com"
    tls:
      mode: Terminate
      certificateRefs:
      - kind: Secret
        name: team-b-tls
    allowedRoutes:
      namespaces:
        from: Same
```

### 跨 Namespace 路由

```yaml
# Shared Gateway
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: shared-gateway
  namespace: gateway-system
spec:
  gatewayClassName: cilium
  listeners:
  - name: https
    protocol: HTTPS
    port: 443
    hostname: "*.example.com"
    allowedRoutes:
      namespaces:
        from: Selector
        selector:
          matchLabels:
            gateway-access: "true"
---
# Namespace labels
apiVersion: v1
kind: Namespace
metadata:
  name: app-team
  labels:
    gateway-access: "true"
---
# HTTPRoute from different namespace
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: app-route
  namespace: app-team
spec:
  parentRefs:
  - name: shared-gateway
    namespace: gateway-system
  hostnames:
  - "app.example.com"
  rules:
  - matches:
    - path:
        type: PathPrefix
        value: /
    backendRefs:
    - name: app-service
      port: 80
```

## 高级负载均衡配置

### Service 健康检查

```yaml
apiVersion: cilium.io/v2
kind: CiliumEnvoyConfig
metadata:
  name: health-check-config
  namespace: default
spec:
  services:
  - name: my-service
    namespace: default

  resources:
  - "@type": type.googleapis.com/envoy.config.cluster.v3.Cluster
    name: default/my-service
    connect_timeout: 5s
    type: EDS

    # Health check configuration
    health_checks:
    - timeout: 5s
      interval: 10s
      unhealthy_threshold: 3
      healthy_threshold: 2
      http_health_check:
        path: "/health"
        host: "health-check.local"
        expected_statuses:
        - start: 200
          end: 299

    # Outlier detection
    outlier_detection:
      consecutive_5xx: 5
      interval: 10s
      base_ejection_time: 30s
      max_ejection_percent: 50
      enforcing_consecutive_5xx: 100
```

### 连接池配置

```yaml
apiVersion: cilium.io/v2
kind: CiliumEnvoyConfig
metadata:
  name: connection-pool
  namespace: default
spec:
  services:
  - name: high-traffic-service
    namespace: default

  resources:
  - "@type": type.googleapis.com/envoy.config.cluster.v3.Cluster
    name: default/high-traffic-service
    connect_timeout: 5s

    # HTTP/1.1 connection pool
    http_protocol_options:
      accept_http_10: true

    # HTTP/2 connection pool
    http2_protocol_options:
      max_concurrent_streams: 1000
      initial_stream_window_size: 65536
      initial_connection_window_size: 1048576

    # Circuit Breaker
    circuit_breakers:
      thresholds:
      - priority: DEFAULT
        max_connections: 10000
        max_pending_requests: 10000
        max_requests: 10000
        max_retries: 5
      - priority: HIGH
        max_connections: 20000
        max_pending_requests: 20000
        max_requests: 20000
        max_retries: 10
```

## 与 AWS Load Balancer Controller 的对比

| 功能 | Cilium Ingress/Gateway | AWS LB Controller |
|---------|------------------------|-------------------|
| L7 路由 | 基于 Envoy | 基于 ALB |
| L4 负载均衡 | 基于 eBPF | 基于 NLB |
| mTLS | 原生支持 | ACM 集成 |
| Gateway API | 完整支持 | 有限 |
| 成本 | 仅 Node 资源 | 额外的 LB 成本 |
| 延迟 | 极低 | 中等 |
| 自定义 | Envoy 配置 | 有限 |

### 选型指南

```mermaid
graph TB
    Start[Start] --> Q1{Need AWS native<br/>integration?}
    Q1 -->|Yes| Q2{Need WAF/Shield?}
    Q1 -->|No| Cilium[Cilium Gateway]

    Q2 -->|Yes| ALB[AWS ALB]
    Q2 -->|No| Q3{Need high-perf<br/>L4?}

    Q3 -->|Yes| NLBCilium[NLB + Cilium]
    Q3 -->|No| Cilium

    ALB --> Done[Done]
    NLBCilium --> Done
    Cilium --> Done
```

## 监控

### Gateway 指标

```bash
# Check Cilium Gateway status
kubectl get gateway -A

# Gateway details
kubectl describe gateway main-gateway

# HTTPRoute status
kubectl get httproute -A

# Check Envoy status
kubectl exec -n kube-system ds/cilium -- cilium status | grep -i envoy
```

### Prometheus 指标

```promql
# Gateway request count
rate(envoy_http_downstream_rq_total{envoy_http_conn_manager_prefix="cilium-gateway"}[5m])

# Gateway error rate
sum(rate(envoy_http_downstream_rq_xx{envoy_http_conn_manager_prefix="cilium-gateway",envoy_response_code_class="5"}[5m])) /
sum(rate(envoy_http_downstream_rq_total{envoy_http_conn_manager_prefix="cilium-gateway"}[5m])) * 100

# Gateway latency
histogram_quantile(0.99, rate(envoy_http_downstream_rq_time_bucket{envoy_http_conn_manager_prefix="cilium-gateway"}[5m]))
```

## 后续步骤

- [最佳实践](./06-best-practices.md): 生产环境部署指南

## 参考资料

- [Cilium Ingress Controller](https://docs.cilium.io/en/stable/network/servicemesh/ingress/)
- [Cilium Gateway API](https://docs.cilium.io/en/stable/network/servicemesh/gateway-api/gateway-api/)
- [Gateway API 规范](https://gateway-api.sigs.k8s.io/)
- [AWS Load Balancer Controller](https://kubernetes-sigs.github.io/aws-load-balancer-controller/)
