# 路由

Istio 的高级路由功能可根据不同请求属性对流量进行细粒度控制。

## 目录

1. [路由概览](#routing-overview)
2. [匹配条件](#match-conditions)
3. [基于 URI 的路由](#uri-based-routing)
4. [基于 Header 的路由](#header-based-routing)
5. [基于查询参数的路由](#query-parameter-based-routing)
6. [基于 HTTP 方法的路由](#http-method-based-routing)
7. [基于来源的路由](#source-based-routing)
8. [优先级与回退](#priority-and-fallback)
9. [实用示例](#practical-examples)
10. [故障排查](#troubleshooting)

## 路由概览 {#routing-overview}

以下示例分别用于 sidecar 路由。请创建其中命名的 Service 和 subset，并确保每个 host 只应用一个彼此重叠的 VirtualService。如果没有设置 `gateways`，路由将应用于 mesh sidecar；针对外部 host 的入口示例还需要绑定到现有 Gateway，并匹配其 hostname。Header、查询参数和来源工作负载标签只是路由输入，不能证明用户身份。应通过身份验证和 AuthorizationPolicy 强制执行租户/用户权限。

VirtualService 路由规则由**匹配条件**和**路由目标**组成。

![Diagram showing how an incoming request is evaluated against ordered match conditions in an Istio VirtualService and routed to the corresponding destination service, with a default fallback rule applied when no earlier condition matches.](../../../.gitbook/assets/en-service-mesh-istio-traffic-management-02-routing-0.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-traffic-management-02-routing-0.html)

### 基本结构

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: routing-example
spec:
  hosts:
  - myapp.example.com
  http:
  - match:
    - uri:
        prefix: "/api/v1"
    route:
    - destination:
        host: api-v1
  - match:
    - headers:
        user-agent:
          regex: ".*Mobile.*"
    route:
    - destination:
        host: mobile-app
  - route:  # Default route (no match)
    - destination:
        host: web-app
```

## 匹配条件 {#match-conditions}

### 匹配条件类型

| 条件 | 描述 | 匹配类型 |
|-----------|-------------|------------|
| **uri** | 请求路径 | `exact`、`prefix`、`regex` |
| **scheme** | HTTP/HTTPS | `exact`、`prefix`、`regex` |
| **method** | HTTP 方法 | `exact`、`prefix`、`regex` |
| **authority** | Host header | `exact`、`prefix`、`regex` |
| **headers** | HTTP headers | `exact`、`prefix`、`regex` |
| **queryParams** | 查询参数 | `exact`、`prefix`、`regex` |
| **sourceLabels** | 来源工作负载标签 | 标签选择器 |
| **gateways** | Gateway 名称 | 列表 |

### 匹配类型

```yaml
# exact: Exact match
match:
- uri:
    exact: "/login"
```

```yaml
# prefix: Prefix match
match:
- uri:
    prefix: "/api/"
```

```yaml
# regex: Regular expression match
match:
- uri:
    regex: "^/api/v[0-9]+/.*"
```

### 组合多个条件

```yaml
# AND condition: All conditions must match
http:
- match:
  - uri:
      prefix: "/api"
    headers:
      x-api-version:
        exact: "v2"
    queryParams:
      debug:
        exact: "true"
  route:
  - destination:
      host: api-debug
```

```yaml
# OR condition: Use multiple match blocks
http:
- match:
  - uri:
      prefix: "/api/v1"
  - uri:
      prefix: "/api/v2"
  route:
  - destination:
      host: api-service
```

## 基于 URI 的路由 {#uri-based-routing}

### 前缀匹配

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: uri-prefix-routing
spec:
  hosts:
  - myapp.example.com
  http:
  # API traffic
  - match:
    - uri:
        prefix: "/api/"
    route:
    - destination:
        host: api-service
        port:
          number: 8080

  # Admin traffic
  - match:
    - uri:
        prefix: "/admin/"
    route:
    - destination:
        host: admin-service
        port:
          number: 9000

  # Static files
  - match:
    - uri:
        prefix: "/static/"
    route:
    - destination:
        host: static-service
        port:
          number: 8000

  # Default traffic
  - route:
    - destination:
        host: frontend-service
        port:
          number: 3000
```

### 精确匹配

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: uri-exact-routing
spec:
  hosts:
  - myapp.example.com
  http:
  # Login page
  - match:
    - uri:
        exact: "/login"
    route:
    - destination:
        host: auth-service

  # Logout
  - match:
    - uri:
        exact: "/logout"
    route:
    - destination:
        host: auth-service

  # Health check
  - match:
    - uri:
        exact: "/health"
    route:
    - destination:
        host: health-service
```

### 正则表达式匹配

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: uri-regex-routing
spec:
  hosts:
  - myapp.example.com
  http:
  # API version routing: /api/v1/, /api/v2/, etc.
  - match:
    - uri:
        regex: "^/api/v[0-9]+/.*"
    route:
    - destination:
        host: api-service

  # Numeric resource ID: /users/123
  - match:
    - uri:
        regex: "^/users/[0-9]+$"
    route:
    - destination:
        host: user-service

  # File extension: .jpg, .png, .gif
  - match:
    - uri:
        regex: ".*\\.(jpg|png|gif)$"
    route:
    - destination:
        host: image-service
```

## 基于 Header 的路由 {#header-based-routing}

### 基于 User-Agent 的路由

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: header-user-agent-routing
spec:
  hosts:
  - reviews
  http:
  # Tablet devices
  - match:
    - headers:
        user-agent:
          regex: ".*(iPad|Tablet).*"
    route:
    - destination:
        host: reviews
        subset: tablet

  # Mobile devices
  - match:
    - headers:
        user-agent:
          regex: ".*Mobile.*"
    route:
    - destination:
        host: reviews
        subset: mobile

  # Desktop (default)
  - route:
    - destination:
        host: reviews
        subset: desktop
```

### 基于自定义 Header 的路由

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: header-custom-routing
spec:
  hosts:
  - myapp
  http:
  # Developer/Tester routing
  - match:
    - headers:
        x-dev-user:
          exact: "true"
    route:
    - destination:
        host: myapp
        subset: dev

  # Beta testers
  - match:
    - headers:
        x-beta-tester:
          exact: "true"
    route:
    - destination:
        host: myapp
        subset: beta

  # VIP users
  - match:
    - headers:
        x-user-tier:
          exact: "vip"
    route:
    - destination:
        host: myapp
        subset: vip

  # Regular users
  - route:
    - destination:
        host: myapp
        subset: stable
```

### 基于 API 版本的路由

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: header-api-version-routing
spec:
  hosts:
  - api.example.com
  http:
  # API v3
  - match:
    - headers:
        x-api-version:
          exact: "v3"
    route:
    - destination:
        host: api-service
        subset: v3

  # API v2
  - match:
    - headers:
        x-api-version:
          exact: "v2"
    route:
    - destination:
        host: api-service
        subset: v2

  # API v1 (default)
  - route:
    - destination:
        host: api-service
        subset: v1
```

## 基于查询参数的路由 {#query-parameter-based-routing}

### 基本查询参数匹配

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: query-param-routing
spec:
  hosts:
  - search.example.com
  http:
  # Debug mode: ?debug=true
  - match:
    - queryParams:
        debug:
          exact: "true"
    route:
    - destination:
        host: search-service
        subset: debug

  # Premium search: ?premium=1
  - match:
    - queryParams:
        premium:
          exact: "1"
    route:
    - destination:
        host: search-service
        subset: premium

  # A/B testing: ?variant=b
  - match:
    - queryParams:
        variant:
          exact: "b"
    route:
    - destination:
        host: search-service
        subset: variant-b

  # Default search
  - route:
    - destination:
        host: search-service
        subset: standard
```

### 组合多个查询参数

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: query-param-combined-routing
spec:
  hosts:
  - api.example.com
  http:
  # Debug mode + verbose logging
  - match:
    - queryParams:
        debug:
          exact: "true"
        verbose:
          exact: "true"
    route:
    - destination:
        host: api-service
        subset: debug-verbose

  # Debug mode only
  - match:
    - queryParams:
        debug:
          exact: "true"
    route:
    - destination:
        host: api-service
        subset: debug

  # Normal mode
  - route:
    - destination:
        host: api-service
        subset: production
```

## 基于 HTTP 方法的路由 {#http-method-based-routing}

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: method-based-routing
spec:
  hosts:
  - api.example.com
  http:
  # POST requests → Write-only service
  - match:
    - method:
        exact: "POST"
      uri:
        prefix: "/api/"
    route:
    - destination:
        host: api-write-service

  # PUT/PATCH requests → Update service
  - match:
    - method:
        regex: "PUT|PATCH"
      uri:
        prefix: "/api/"
    route:
    - destination:
        host: api-update-service

  # DELETE requests → Delete service
  - match:
    - method:
        exact: "DELETE"
      uri:
        prefix: "/api/"
    route:
    - destination:
        host: api-delete-service

  # GET requests → Read-only service
  - match:
    - method:
        exact: "GET"
      uri:
        prefix: "/api/"
    route:
    - destination:
        host: api-read-service
```

## 基于来源的路由 {#source-based-routing}

`sourceLabels` 和 `sourceNamespace` 用于选择哪些来源 sidecar 接收配置；它们不是入口 Gateway 上经过身份验证的逐请求匹配条件。显式设置顶层 Gateway 列表时，必须包含 `mesh`，这些 selector 才会生效。数据库示例假定 Service 使用 HTTP，不适用于不透明的 SQL 协议。

### 基于 Namespace 的路由

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: source-namespace-routing
  namespace: production
spec:
  hosts:
  - database.production.svc.cluster.local
  http:
  # Requests from production namespace
  - match:
    - sourceNamespace: production
    route:
    - destination:
        host: database
        subset: production

  # Requests from staging namespace
  - match:
    - sourceNamespace: staging
    route:
    - destination:
        host: database
        subset: staging

  # Illustrative HTTP rejection; enforce identity policy at the destination
  - directResponse:
      status: 403
```

### 基于来源工作负载标签的路由

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: source-sa-routing
spec:
  hosts:
  - payment-service
  http:
  # Select configuration for matching source workload labels
  - match:
    - sourceLabels:
        app: frontend
        version: v2
    route:
    - destination:
        host: payment-service
        subset: v2

  # Legacy service
  - match:
    - sourceLabels:
        app: frontend
        version: v1
    route:
    - destination:
        host: payment-service
        subset: v1
```

## 优先级与回退 {#priority-and-fallback}

### 匹配规则优先级

Istio 按**从上到下**的顺序评估 VirtualService 的 HTTP 路由规则。

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: priority-example
spec:
  hosts:
  - myapp.example.com
  http:
  # Priority 1: Most specific condition
  - match:
    - uri:
        exact: "/api/v2/users/admin"
      headers:
        x-admin:
          exact: "true"
    route:
    - destination:
        host: admin-api-v2

  # Priority 2: Medium specificity
  - match:
    - uri:
        prefix: "/api/v2/"
    route:
    - destination:
        host: api-v2

  # Priority 3: Less specific
  - match:
    - uri:
        prefix: "/api/"
    route:
    - destination:
        host: api-v1

  # Priority 4 (last): Default fallback
  - route:
    - destination:
        host: frontend
```

### 回退策略

此处的回退是指最终处理未匹配请求的路由。某条路由匹配后，即使上游请求失败，也不会从头开始检查后续路由。应另行配置重试/异常实例检测，或使用 rollout 控制器处理故障恢复。

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: fallback-strategy
spec:
  hosts:
  - myapp
  http:
  # Requests matching specific conditions
  - match:
    - headers:
        x-canary:
          exact: "true"
    route:
    - destination:
        host: myapp
        subset: canary
    # No fallback on canary failure - return error

  # Default route for requests that did not match the canary condition
  - route:
    - destination:
        host: myapp
        subset: stable
      weight: 100
```

## 实用示例 {#practical-examples}

### 示例 1：多租户路由

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: multi-tenant-routing
spec:
  hosts:
  - api.example.com
  - tenant-b.api.example.com
  http:
  # Tenant A (identified by header)
  - match:
    - headers:
        x-tenant-id:
          exact: "tenant-a"
    route:
    - destination:
        host: api-service
        subset: tenant-a

  # Tenant B (identified by subdomain)
  - match:
    - authority:
        exact: "tenant-b.api.example.com"
    route:
    - destination:
        host: api-service
        subset: tenant-b

  # Tenant C (identified by path)
  - match:
    - uri:
        prefix: "/tenant-c/"
    rewrite:
      uri: "/"
    route:
    - destination:
        host: api-service
        subset: tenant-c
```

### 示例 2：基于功能标志的路由

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: feature-flag-routing
spec:
  hosts:
  - myapp
  http:
  # Users with new feature enabled
  - match:
    - headers:
        x-feature-new-ui:
          exact: "enabled"
    route:
    - destination:
        host: myapp
        subset: new-ui

  # Beta feature testers
  - match:
    - headers:
        x-feature-beta:
          exact: "enabled"
    route:
    - destination:
        host: myapp
        subset: beta

  # Workloads labeled role=employee with the feature header
  - match:
    - headers:
        x-feature-experimental:
          exact: "enabled"
      sourceLabels:
        role: employee
    route:
    - destination:
        host: myapp
        subset: experimental

  # Default (stable version)
  - route:
    - destination:
        host: myapp
        subset: stable
```

### 示例 3：地理位置路由

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: geo-routing
spec:
  hosts:
  - content.example.com
  http:
  # Korean users
  - match:
    - headers:
        x-country-code:
          exact: "KR"
    route:
    - destination:
        host: content-service
        subset: korea

  # Japanese users
  - match:
    - headers:
        x-country-code:
          exact: "JP"
    route:
    - destination:
        host: content-service
        subset: japan

  # US users
  - match:
    - headers:
        x-country-code:
          exact: "US"
    route:
    - destination:
        host: content-service
        subset: us

  # European users
  - match:
    - headers:
        x-country-code:
          regex: "DE|FR|GB|IT|ES"
    route:
    - destination:
        host: content-service
        subset: europe

  # Other regions (global)
  - route:
    - destination:
        host: content-service
        subset: global
```

### 示例 4：API Gateway 模式

对外开放前，请将 `api-gateway` 绑定到实际 Gateway，并对受保护路径配置 [JWT 身份验证和授权](../security/02-authentication.md)。匹配 `Bearer ...` 这段文本并不等于验证了令牌。缺少凭据时，受保护路径不得回退到公共/通用路由。如果地理位置/租户 Header 会影响访问决策，它们必须来自可信且经过身份验证的来源。

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: api-gateway-routing
spec:
  hosts:
  - api.example.com
  gateways:
  - api-gateway
  http:
  # Route protected paths; JWT/authorization must be enforced separately
  - match:
    - uri:
        prefix: "/api/v1/protected/"
    route:
    - destination:
        host: protected-api-service

  # Public APIs
  - match:
    - uri:
        prefix: "/api/v1/public/"
    route:
    - destination:
        host: public-api-service

  # GraphQL endpoint
  - match:
    - uri:
        exact: "/graphql"
      method:
        exact: "POST"
    route:
    - destination:
        host: graphql-service

  # REST API
  - match:
    - uri:
        prefix: "/api/v1/"
    route:
    - destination:
        host: rest-api-service

  # Health check
  - match:
    - uri:
        exact: "/health"
    route:
    - destination:
        host: health-service

  # 404 response for unmatched paths
  - directResponse:
      status: 404
```

## 故障排查 {#troubleshooting}

### 路由不起作用

```bash
# 1. Check VirtualService status
kubectl get virtualservice -A
kubectl describe virtualservice <name> -n <namespace>

# 2. Check routing rules
istioctl proxy-config routes <pod-name> -n <namespace>

# 3. Check routing to specific service
istioctl proxy-config routes <pod-name> -n <namespace> --name <route-name> -o json

# 4. Validate configuration
istioctl analyze -n <namespace>
```

### 调试匹配条件

```bash
# Increase Envoy log level
istioctl proxy-config log <pod-name> -n <namespace> --level debug

# Trace requests
kubectl logs -n <namespace> <pod-name> -c istio-proxy -f

# Debug Pilot
kubectl logs -n istio-system -l app=istiod --tail=100
```

### 常见问题

#### 1. 匹配顺序问题

```yaml
# ❌ Wrong order - default route first ignores other rules
http:
- route:  # All traffic goes here
  - destination:
      host: myapp
- match:  # Never executed
  - uri:
      prefix: "/api"
  route:
  - destination:
      host: api-service
```

```yaml
# ✅ Correct order
http:
- match:  # Specific rules first
  - uri:
      prefix: "/api"
  route:
  - destination:
      host: api-service
- route:  # Default route last
  - destination:
      host: myapp
```

#### 2. 正则表达式匹配范围

RE2 会匹配整个字符串。`/api/v[1-3]` 语法有效，并匹配 `/api/v1`，但不匹配 `/api/v1/users`；`/` 无需转义。若要匹配版本根路径及其后代路径：

```yaml
match:
- uri:
    regex: "^/api/v[1-3](/.*)?$"
```

#### 3. Header 名称

HTTP Header 名称在网络传输时不区分大小写，但 Istio 匹配 map 的键必须使用小写。除非表达式另有说明，Header 值仍区分大小写。

```yaml
match:
- headers:
    x-custom-header:
      exact: "value"
```

## 最佳实践

### 1. 将具体规则放在前面

```yaml
# ✅ Good example
http:
- match:
  - uri:
      exact: "/api/v2/admin"  # Most specific
  route:
  - destination:
      host: admin-v2
- match:
  - uri:
      prefix: "/api/v2/"  # Medium
  route:
  - destination:
      host: api-v2
- match:
  - uri:
      prefix: "/api/"  # General
  route:
  - destination:
      host: api-v1
- route:  # Default
  - destination:
      host: frontend
```

### 2. 尽量少用正则表达式

```yaml
# ❌ Avoid - complex regex degrades performance
match:
- uri:
    regex: "^/(api|admin|public)/v[0-9]+/(users|products|orders)/[a-zA-Z0-9_-]+$"
```

```yaml
# ✅ Recommended - use prefix or exact
match:
- uri:
    prefix: "/api/v1/"
```

### 3. 使用清晰的命名

```yaml
# ✅ Use clear names
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: product-api-routing  # Clear name
  labels:
    app: product-service
    purpose: routing
spec:
  hosts:
  - product-api.example.com
  http:
  - route:
    - destination:
        host: product-api-service
```

### 4. 编写文档

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: myapp-routing
  annotations:
    description: "Routes traffic based on API version and user type"
    owner: "platform-team"
spec:
  hosts:
  - myapp.example.com
  http:
  # Route VIP users to dedicated instance
  - match:
    - headers:
        x-user-tier:
          exact: "vip"
    route:
    - destination:
        host: myapp
        subset: vip
```

### 5. 测试策略

将 GATEWAY_URL 设为已安装入口的地址/端口，并根据当前部署的单个示例调整 Host 和 Header。仅供 mesh 使用的示例必须先绑定到该 Gateway，才能通过这些外部 curl 命令进行测试。排查结束后，请恢复临时设置的 proxy debug 日志级别。

```bash
# Routing rule test script
#!/bin/bash

# API v1 test
curl -H "Host: api.example.com" http://$GATEWAY_URL/api/v1/users

# API v2 test
curl -H "Host: api.example.com" http://$GATEWAY_URL/api/v2/users

# Mobile user test
curl -H "Host: myapp.example.com" -H "User-Agent: Mobile" "http://$GATEWAY_URL/"

# Header-based test
curl -H "Host: myapp.example.com" -H "x-canary: true" "http://$GATEWAY_URL/"
```

## 参考资料

- [Istio 流量管理](https://istio.io/latest/docs/concepts/traffic-management/)
- [VirtualService 参考](https://istio.io/latest/docs/reference/config/networking/virtual-service/)
- [HTTP 路由匹配](https://istio.io/latest/docs/reference/config/networking/virtual-service/#HTTPMatchRequest)
- [流量路由](https://istio.io/latest/docs/tasks/traffic-management/request-routing/)
