# Gateway 和 VirtualService

Gateway 和 VirtualService 是 Istio 中用于管理流量的核心资源。

## 目录

1. [Gateway 概述](#gateway-overview)
2. [VirtualService 概述](#virtualservice-overview)
3. [基本配置](#basic-configuration)
4. [实践示例](#practical-examples)
5. [高级模式](#advanced-patterns)
6. [故障排除](#troubleshooting)

## Gateway 概述

Gateway 定义了外部流量进入网格的入口点。

```yaml
apiVersion: networking.istio.io/v1
kind: Gateway
metadata:
  name: my-gateway
  namespace: istio-system
spec:
  selector:
    istio: ingressgateway  # Select Ingress Gateway pods
  servers:
  - port:
      number: 80
      name: http
      protocol: HTTP
    hosts:
    - "myapp.example.com"
  - port:
      number: 443
      name: https
      protocol: HTTPS
    tls:
      mode: SIMPLE
      credentialName: myapp-tls-secret
    hosts:
    - "myapp.example.com"
```

## VirtualService 概述

VirtualService 定义如何路由通过 Gateway 进入的流量。

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: myapp
  namespace: default
spec:
  hosts:
  - "myapp.example.com"
  gateways:
  - istio-system/my-gateway
  http:
  - match:
    - uri:
        prefix: "/api"
    route:
    - destination:
        host: api-service
        port:
          number: 8080
  - route:
    - destination:
        host: frontend-service
        port:
          number: 3000
```

## 基本配置

### HTTP 流量

```yaml
apiVersion: networking.istio.io/v1
kind: Gateway
metadata:
  name: http-gateway
spec:
  selector:
    istio: ingressgateway
  servers:
  - port:
      number: 80
      name: http
      protocol: HTTP
    hosts:
    - "*"  # Allow all hosts
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: app-routes
spec:
  hosts:
  - "*"
  gateways:
  - http-gateway
  http:
  - route:
    - destination:
        host: myapp
        port:
          number: 8080
```

### HTTPS 流量

```yaml
# Create TLS certificate Secret
kubectl create secret tls myapp-tls \
  --cert=myapp.crt \
  --key=myapp.key \
  -n istio-system
```

```yaml
apiVersion: networking.istio.io/v1
kind: Gateway
metadata:
  name: https-gateway
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
      credentialName: myapp-tls
    hosts:
    - "myapp.example.com"
```

## 实践示例

### 基于路径的路由

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: path-routing
spec:
  hosts:
  - "myapp.example.com"
  gateways:
  - my-gateway
  http:
  # API traffic
  - match:
    - uri:
        prefix: "/api/v1"
    route:
    - destination:
        host: api-v1
        port:
          number: 8080
  # Admin traffic
  - match:
    - uri:
        prefix: "/admin"
    route:
    - destination:
        host: admin-service
        port:
          number: 9000
  # Default traffic
  - route:
    - destination:
        host: frontend
        port:
          number: 3000
```

### 基于请求头的路由

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: header-routing
spec:
  hosts:
  - reviews
  http:
  # Mobile traffic
  - match:
    - headers:
        user-agent:
          regex: ".*Mobile.*"
    route:
    - destination:
        host: reviews
        subset: mobile-v2
  # Developer traffic
  - match:
    - headers:
        x-dev-user:
          exact: "true"
    route:
    - destination:
        host: reviews
        subset: v3
  # Default traffic
  - route:
    - destination:
        host: reviews
        subset: v1
```

### 多域名配置

```yaml
apiVersion: networking.istio.io/v1
kind: Gateway
metadata:
  name: multi-domain-gateway
spec:
  selector:
    istio: ingressgateway
  servers:
  - port:
      number: 443
      name: https-api
      protocol: HTTPS
    tls:
      mode: SIMPLE
      credentialName: api-tls
    hosts:
    - "api.example.com"
  - port:
      number: 443
      name: https-admin
      protocol: HTTPS
    tls:
      mode: SIMPLE
      credentialName: admin-tls
    hosts:
    - "admin.example.com"
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: api-routes
spec:
  hosts:
  - "api.example.com"
  gateways:
  - multi-domain-gateway
  http:
  - route:
    - destination:
        host: api-service
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: admin-routes
spec:
  hosts:
  - "admin.example.com"
  gateways:
  - multi-domain-gateway
  http:
  - route:
    - destination:
        host: admin-service
```

## 高级模式

### HTTP 重定向到 HTTPS

```yaml
apiVersion: networking.istio.io/v1
kind: Gateway
metadata:
  name: secure-gateway
spec:
  selector:
    istio: ingressgateway
  servers:
  # HTTP (for redirect)
  - port:
      number: 80
      name: http
      protocol: HTTP
    hosts:
    - "myapp.example.com"
    tls:
      httpsRedirect: true  # Redirect to HTTPS
  # HTTPS
  - port:
      number: 443
      name: https
      protocol: HTTPS
    tls:
      mode: SIMPLE
      credentialName: myapp-tls
    hosts:
    - "myapp.example.com"
```

### URL 重写

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: url-rewrite
spec:
  hosts:
  - "myapp.example.com"
  gateways:
  - my-gateway
  http:
  - match:
    - uri:
        prefix: "/old-api"
    rewrite:
      uri: "/api/v2"  # URL rewrite
    route:
    - destination:
        host: api-service
```

### 请求头添加/修改

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: header-manipulation
spec:
  hosts:
  - reviews
  http:
  - route:
    - destination:
        host: reviews
    headers:
      request:
        add:
          x-custom-header: "custom-value"
          x-forwarded-proto: "https"
        set:
          x-api-version: "v2"
        remove:
          - x-internal-header
      response:
        add:
          x-response-time: "100ms"
```

### 重定向

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: redirect-example
spec:
  hosts:
  - "myapp.example.com"
  gateways:
  - my-gateway
  http:
  - match:
    - uri:
        prefix: "/old-page"
    redirect:
      uri: "/new-page"
      authority: "newapp.example.com"
```

## 故障排除

### Gateway 未正常工作

```bash
# 1. Check Gateway status
kubectl get gateway -n istio-system

# 2. Check Ingress Gateway pods
kubectl get pods -n istio-system -l istio=ingressgateway

# 3. Check Gateway configuration
kubectl describe gateway my-gateway -n istio-system

# 4. Check Envoy configuration
istioctl proxy-config listeners -n istio-system istio-ingressgateway-xxx
```

### VirtualService 路由失败

```bash
# 1. Check VirtualService
kubectl get virtualservice

# 2. Analyze configuration
istioctl analyze

# 3. Check routing rules
istioctl proxy-config routes -n istio-system istio-ingressgateway-xxx

# 4. Check logs
kubectl logs -n istio-system -l istio=ingressgateway --tail=100
```

### TLS 证书问题

```bash
# Check Secret
kubectl get secret -n istio-system myapp-tls

# Check Secret contents
kubectl describe secret -n istio-system myapp-tls

# Check Gateway TLS configuration
istioctl proxy-config secret -n istio-system istio-ingressgateway-xxx
```

## 最佳实践

1. **Namespace 隔离**：Gateway 位于 `istio-system`，VirtualService 位于应用程序 Namespace
2. **必须使用 TLS**：在生产环境中始终使用 HTTPS
3. **明确指定 Host**：使用明确的域名，而非通配符（`*`）
4. **匹配条件顺序**：特定条件在前，通用条件在后
5. **资源命名**：使用一致的命名约定

## 参考资料

- [Istio Gateway](https://istio.io/latest/docs/reference/config/networking/gateway/)
- [Istio VirtualService](https://istio.io/latest/docs/reference/config/networking/virtual-service/)
- [入口流量](https://istio.io/latest/docs/tasks/traffic-management/ingress/)
