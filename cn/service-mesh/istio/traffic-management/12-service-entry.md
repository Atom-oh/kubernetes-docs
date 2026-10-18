# ServiceEntry

ServiceEntry 会在 Istio 服务网格中注册外部服务，使其能够像内部服务一样进行管理。

## 目录

1. [为什么使用 ServiceEntry？](#why-serviceentry)
2. [ServiceEntry 概述](#serviceentry-overview)
3. [解析模式](#resolution-modes)
4. [位置设置](#location-settings)
5. [实用示例](#practical-examples)
6. [与 Egress Gateway 结合使用](#combining-with-egress-gateway)
7. [安全与 TLS](#security-and-tls)
8. [监控与控制](#monitoring-and-control)
9. [最佳实践](#best-practices)

## 为什么使用 ServiceEntry？ {#why-serviceentry}

### 管理外部服务的必要性

使用 ALLOW_ANY 时，未知的外部目标仍可通过，但可用的策略和遥测信息会减少。ServiceEntry 会注册目标，以便配置兼容的代理策略；它本身不是访问控制规则。

注册后可以针对目标配置相关设置；实际监控、TLS 和流量控制仍取决于协议以及已应用的策略。

### 主要优势

| 功能 | 不使用 ServiceEntry | 使用 ServiceEntry |
|---------|---------------------|-------------------|
| **监控** | 仅有有限的透传遥测 | 遥测取决于协议；HTTP 需要 L7 可见性 |
| **流量控制** | 不可用 | 可配置超时、重试、熔断 |
| **安全** | 应用 TLS 仍可生效 | 需单独配置 TLS/mTLS；不会自动签发外部证书 |
| **出口控制** | 取决于出站/网络策略 | 提供注册表和路由配置；网络强制执行需另行设置 |
| **服务发现** | 手动管理 | 自动 DNS 查找 |

## ServiceEntry 概述 {#serviceentry-overview}

以下示例是彼此独立的 Sidecar 配置方案。ServiceEntry 由 istiod/代理使用，本身不是一个网络跳点。`addresses` 用于归类服务/VIP 流量，`endpoints` 用于标识上游后端。解析模式控制代理如何查找地址，而不控制应用程序的 DNS；使用合成主机名时，应配置 DNS 记录或 DNS 捕获。ServiceEntry 不会将 VM 代理纳入网格，也不会签发其身份凭证。

ServiceEntry 会将外部服务加入 Istio 服务注册表。

![网格中的应用通过 ServiceEntry 注册项发送请求；该注册项应用流量控制、监控和安全配置，然后将请求分发到外部 API 和外部数据库。](../../../.gitbook/assets/en-service-mesh-istio-traffic-management-12-service-entry-1.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-traffic-management-12-service-entry-1.html)

### 基本结构

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: external-api
spec:
  hosts:                  # External service hostname
  - api.example.com
  ports:                  # Port and protocol
  - number: 443
    name: https
    protocol: HTTPS
  location: MESH_EXTERNAL # External/internal location
  resolution: DNS         # Address resolution method
```

## 解析模式 {#resolution-modes}

Istio 1.31 API 定义了五种解析模式。

### 1. DNS 解析

这是最常见的模式，通过 DNS 动态解析 IP 地址。

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: external-api-dns
spec:
  hosts:
  - api.example.com
  ports:
  - number: 443
    name: https
    protocol: HTTPS
  location: MESH_EXTERNAL
  resolution: DNS  # DNS lookup
```

**使用场景**：
- 公共 API（AWS S3、Google Cloud Storage）
- SaaS 服务（Stripe、SendGrid）
- 云托管服务

### 2. STATIC 解析

显式指定固定 IP 地址。

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: external-api-static
spec:
  hosts:
  - legacy-api.company.internal
  addresses:
  - 10.10.10.10
  - 10.10.10.11
  ports:
  - number: 8080
    name: http
    protocol: HTTP
  location: MESH_EXTERNAL
  resolution: STATIC  # Fixed IP
  endpoints:
  - address: 10.10.10.10
  - address: 10.10.10.11
```

**使用场景**：
- 没有 DNS 的旧系统
- 合规要求使用固定 IP
- 内部数据中心服务

### 3. NONE 解析

此模式不执行地址解析，而是按原样使用客户端提供的地址。

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: wildcard-api
spec:
  hosts:
  - "*.api.example.com"  # Wildcard
  ports:
  - number: 443
    name: https
    protocol: HTTPS
  location: MESH_EXTERNAL
  resolution: NONE  # No address resolution
```

**使用场景**：
- 通配符域名
- 客户端负载均衡
- TCP/TLS 代理

### 4. DNS_ROUND_ROBIN 解析

此模式受支持，并未弃用。与 DNS 模式返回完整端点集合不同，它在建立新连接时使用 DNS 返回的第一个地址；DNS 记录变化后，现有连接仍会保留。对于由 DNS 提供前端、且端点频繁变化会不断清空连接池的服务，此模式很有用。

### 5. DYNAMIC_DNS 解析

此模式会在请求到达时，根据 HTTP Host/SNI 解析通配符目标。是否适用取决于 Istio 版本、数据平面和 waypoint 配置；对于无法恢复主机名的透明 TCP 流量，此模式不适用。使用前请核对该模式的具体要求。下方的具体通配符示例使用 Sidecar NONE 模式。

## 位置设置 {#location-settings}

### MESH_EXTERNAL（外部服务）

注册网格之外的服务。

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: external-service
spec:
  hosts:
  - external-api.com
  ports:
  - number: 443
    name: https
    protocol: HTTPS
  location: MESH_EXTERNAL  # External service
  resolution: DNS
```

**特性**：
- 配置适当的 DestinationRule 和服务器信任后，可以使用外部 TLS/mTLS
- 可以经由 Egress Gateway 出站
- 被归类为外部流量

### MESH_INTERNAL（内部服务）

将服务视为网格内部服务（较少使用）。

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: internal-vm-service
spec:
  hosts:
  - vm-service.internal
  ports:
  - number: 8080
    name: http
    protocol: HTTP
  location: MESH_INTERNAL  # Treat as internal service
  resolution: STATIC
  endpoints:
  - address: 10.0.0.5
    labels:
      app: vm-service
```

**使用场景**：
- 将 VM 工作负载纳入网格
- 多集群环境
- 混合云配置

## 实用示例 {#practical-examples}

### 1. 注册外部 REST API

#### 场景：支付网关 API

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: payment-gateway-api
  namespace: production
spec:
  hosts:
  - api.payment-gateway.com
  ports:
  - number: 80
    name: http
    protocol: HTTP
    targetPort: 443
  location: MESH_EXTERNAL
  resolution: DNS
---
# VirtualService: Timeout and Retry settings
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: payment-gateway-routing
  namespace: production
spec:
  hosts:
  - api.payment-gateway.com
  http:
  - match:
    - method:
        regex: "^(GET|HEAD)$"
    route:
    - destination:
        host: api.payment-gateway.com
    timeout: 10s
    retries:
      attempts: 3
      perTryTimeout: 3s
      retryOn: connect-failure,refused-stream
  - route:
    - destination:
        host: api.payment-gateway.com
    timeout: 10s
    retries:
      attempts: 0
---
# DestinationRule: Circuit Breaker
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: payment-gateway-circuit-breaker
  namespace: production
spec:
  host: api.payment-gateway.com
  trafficPolicy:
    connectionPool:
      http:
        http1MaxPendingRequests: 10
        maxRequestsPerConnection: 1
    outlierDetection:
      consecutive5xxErrors: 3
      interval: 30s
      baseEjectionTime: 120s
    tls:
      mode: SIMPLE
      sni: api.payment-gateway.com
      subjectAltNames: [api.payment-gateway.com]
```

在此 TLS 发起方案中，应用向本地 Sidecar 发送 HTTP，代理再向上游发送经过验证的 HTTPS。不要将此方案与应用自行发起的 HTTPS 混用。启用重试前，支付写入操作必须由应用提供幂等性约定。

### 2. 注册外部数据库

#### 场景：AWS RDS MySQL

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: aws-rds-mysql
spec:
  hosts:
  - mydb.abc123.us-west-2.rds.amazonaws.com
  ports:
  - number: 3306
    name: tcp
    protocol: TCP
  location: MESH_EXTERNAL
  resolution: DNS
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: aws-rds-mysql-circuit-breaker
spec:
  host: mydb.abc123.us-west-2.rds.amazonaws.com
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 100
        connectTimeout: 5s
    outlierDetection:
      consecutive5xxErrors: 5
      interval: 60s
      baseEjectionTime: 60s
```

### 3. 注册通配符域名

请在数据库驱动中使用当前 RDS CA bundle 配置 TLS 和证书验证。TCP 注册不会配置数据库身份验证或 SSL 协商。同一端口上存在多个外部数据库时，请使用 DNS 捕获或唯一服务 VIP，避免仅凭端口造成歧义。

#### 场景：访问 AWS S3 存储桶

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: aws-s3-buckets
spec:
  hosts:
  - "*.s3.amazonaws.com"
  - "*.s3.us-west-2.amazonaws.com"
  - "s3.us-west-2.amazonaws.com"
  ports:
  - number: 443
    name: https
    protocol: HTTPS
  location: MESH_EXTERNAL
  resolution: NONE  # Use NONE for wildcards
```

只允许在名称开头使用通配符前缀；应列出实际区域端点后缀，不要在名称中间放置 `*`。这是 Sidecar 示例，未涵盖所有 S3 端点系列，也不会授予 IAM 访问权限。

### 4. 注册具有多个端点的外部服务

#### 场景：多区域 API

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: multi-region-api
spec:
  hosts:
  - api.global-service.com
  ports:
  - number: 80
    name: http
    protocol: HTTP
    targetPort: 443
  location: MESH_EXTERNAL
  resolution: DNS
  endpoints:
  - address: us-west.api.global-service.com
    labels:
      region: us-west
  - address: eu-central.api.global-service.com
    labels:
      region: eu-central
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: multi-region-api
spec:
  host: api.global-service.com
  trafficPolicy:
    tls:
      mode: SIMPLE
      sni: api.global-service.com
      subjectAltNames: [api.global-service.com]
  subsets:
  - name: us-west
    labels:
      region: us-west
  - name: eu-central
    labels:
      region: eu-central
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: multi-region-routing
spec:
  hosts:
  - api.global-service.com
  http:
  - match:
    - headers:
        x-region:
          exact: us-west
    route:
    - destination:
        host: api.global-service.com
        subset: us-west
  - match:
    - headers:
        x-region:
          exact: eu-central
    route:
    - destination:
        host: api.global-service.com
        subset: eu-central
  - route:
    - destination:
        host: api.global-service.com
```

两个区域的端点都必须提供相同的规范 API 主机名和证书。仅更改 HTTP Host 标头不会改变代理选择的 DNS 端点。如示例所示，应用在本地使用 HTTP，TLS 则由代理向上游发起。

### 5. 注册 TCP 服务

#### 场景：外部 Redis 集群

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: external-redis
spec:
  hosts:
  - redis-primary.external-cluster.com
  addresses:
  - 203.0.113.10
  ports:
  - number: 6379
    name: tcp
    protocol: TCP
  location: MESH_EXTERNAL
  resolution: STATIC
  endpoints:
  - address: 203.0.113.10
    labels:
      instance: primary
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: external-redis-lb
spec:
  host: redis-primary.external-cluster.com
  trafficPolicy:
    loadBalancer:
      simple: ROUND_ROBIN
    connectionPool:
      tcp:
        maxConnections: 50
        connectTimeout: 3s
```

此示例只选择可写主节点。只读流量应单独注册副本，或使用能够理解 Redis 的集群客户端；通用轮询无法保留 Redis 主从或分片语义。示例 IP 必须替换为可访问的实际端点。

## 与 Egress Gateway 结合使用 {#combining-with-egress-gateway}

通过 Egress Gateway 集中控制外部流量。

### 基本 Egress Gateway 配置

```yaml
# ServiceEntry: Register external service
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: external-api
spec:
  hosts:
  - api.example.com
  ports:
  - number: 443
    name: https
    protocol: HTTPS
  location: MESH_EXTERNAL
  resolution: DNS
---
# Gateway: Egress Gateway configuration
apiVersion: networking.istio.io/v1
kind: Gateway
metadata:
  name: egress-gateway
  namespace: istio-system
spec:
  selector:
    istio: egressgateway
  servers:
  - port:
      number: 443
      name: tls
      protocol: TLS
    hosts:
    - api.example.com
    tls:
      mode: PASSTHROUGH
---
# VirtualService: Mesh internal -> Egress Gateway
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: direct-api-through-egress
spec:
  hosts:
  - api.example.com
  gateways:
  - mesh
  - istio-system/egress-gateway
  tls:
  - match:
    - gateways:
      - mesh
      port: 443
      sniHosts:
      - api.example.com
    route:
    - destination:
        host: istio-egressgateway.istio-system.svc.cluster.local
        port:
          number: 443
  - match:
    - gateways:
      - istio-system/egress-gateway
      port: 443
      sniHosts:
      - api.example.com
    route:
    - destination:
        host: api.example.com
        port:
          number: 443
```

### TLS 发起（内部 HTTP，外部 HTTPS）

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: external-http-to-https
spec:
  hosts:
  - api.secure-service.com
  ports:
  - number: 80
    name: http
    protocol: HTTP
    targetPort: 443
  - number: 443
    name: https
    protocol: HTTPS
  location: MESH_EXTERNAL
  resolution: DNS
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: originate-tls
spec:
  host: api.secure-service.com
  trafficPolicy:
    portLevelSettings:
    - port:
        number: 80
      tls:
        mode: SIMPLE  # HTTP -> HTTPS conversion
```

## 安全与 TLS {#security-and-tls}

### 与外部服务建立 mTLS

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: mtls-external-service
spec:
  hosts:
  - mtls-api.example.com
  ports:
  - number: 80
    name: http
    protocol: HTTP
    targetPort: 443
  location: MESH_EXTERNAL
  resolution: DNS
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: mtls-external-tls
spec:
  host: mtls-api.example.com
  trafficPolicy:
    tls:
      mode: MUTUAL
      sni: mtls-api.example.com
      subjectAltNames: [mtls-api.example.com]
      clientCertificate: /etc/certs/client-cert.pem
      privateKey: /etc/certs/client-key.pem
      caCertificates: /etc/certs/ca-cert.pem
```

请将这些证书/密钥文件挂载到代理容器，并通过证书管理流程轮换。外部服务器必须信任客户端 CA；ServiceEntry 不会签发这些凭证。这是代理从本地 HTTP 发起的 mTLS，而不是在应用 TLS 之外再套一层 TLS。

### SNI 路由

```yaml
apiVersion: networking.istio.io/v1
kind: Gateway
metadata:
  name: egress-sni-gateway
  namespace: istio-system
spec:
  selector:
    istio: egressgateway
  servers:
  - port:
      number: 443
      name: tls
      protocol: TLS
    hosts:
    - api.example.com
    - api2.example.com
    tls:
      mode: PASSTHROUGH
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: sni-routing
spec:
  hosts:
  - api.example.com
  - api2.example.com
  gateways:
  - mesh
  - istio-system/egress-sni-gateway
  tls:
  - match:
    - gateways:
      - mesh
      port: 443
      sniHosts:
      - api.example.com
    route:
    - destination:
        host: istio-egressgateway.istio-system.svc.cluster.local
        port:
          number: 443
  - match:
    - gateways:
      - istio-system/egress-sni-gateway
      port: 443
      sniHosts:
      - api.example.com
    route:
    - destination:
        host: api.example.com
        port:
          number: 443
  - match:
    - gateways:
      - mesh
      port: 443
      sniHosts:
      - api2.example.com
    route:
    - destination:
        host: istio-egressgateway.istio-system.svc.cluster.local
        port:
          number: 443
  - match:
    - gateways:
      - istio-system/egress-sni-gateway
      port: 443
      sniHosts:
      - api2.example.com
    route:
    - destination:
        host: api2.example.com
        port:
          number: 443
```

按[出口控制](11-egress-control.md)所示安装 Egress Gateway 工作负载和 ClusterIP Service，并为两个外部主机分别注册 ServiceEntry。SNI 路由只配置转发，不会强制所有流量都经过网关；要建立这一边界，请使用网络层强制措施。

## 监控与控制 {#monitoring-and-control}

### 收集指标

```bash
# Check ServiceEntry traffic
kubectl exec -it <pod-name> -c istio-proxy -- \
  curl localhost:15000/stats/prometheus | grep "api.example.com"

# Egress traffic metrics
istio_requests_total{reporter="source",destination_service_name="api.example.com"}
```

### Prometheus 查询

查询前先检查实际指标标签。HTTP 请求数、错误和延迟指标需要 L7 可见性（例如 TLS 发起）；无法解密的 HTTPS/TCP 流量则暴露连接和字节指标。不要假定外部 ServiceEntry 的 namespace 标签为空。

```promql
# External service request count
sum(rate(istio_requests_total{reporter="source",destination_service_name="api.example.com"}[5m]))

# External service error rate
sum(rate(istio_requests_total{reporter="source",destination_service_name="api.example.com",response_code=~"5.."}[5m])) /
sum(rate(istio_requests_total{reporter="source",destination_service_name="api.example.com"}[5m]))

# External service response time
histogram_quantile(0.95,
  sum(rate(istio_request_duration_milliseconds_bucket{reporter="source",destination_service_name="api.example.com"}[5m])) by (le)
)
```

### 检测未注册目标

```yaml
# Registry/configuration control, not a firewall
apiVersion: networking.istio.io/v1
kind: Sidecar
metadata:
  name: default
  namespace: default
spec:
  egress:
  - hosts:
    - "./*"  # Allow only same namespace
    - "istio-system/*"  # Allow istio-system
  outboundTrafficPolicy:
    mode: REGISTRY_ONLY  # Known Kubernetes and ServiceEntry destinations
```

Sidecar 导入范围和 REGISTRY_ONLY 都不是安全边界。必须强制控制出口时，请使用网络策略/防火墙，并在适用时使用 AuthorizationPolicy。

## 最佳实践 {#best-practices}

### 1. 显式注册 ServiceEntry

```yaml
# Good example: Explicit registration
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: payment-api
  namespace: production
  annotations:
    description: "Payment gateway API"
    owner: "payments-team"
    sla: "99.9%"
spec:
  hosts:
  - api.payment.com
  ports:
  - number: 443
    name: https
    protocol: HTTPS
  location: MESH_EXTERNAL
  resolution: DNS
```

### 2. 根据协议调整韧性设置

```yaml
# Always apply Circuit Breaker for external services
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: external-api-protection
spec:
  host: api.example.com
  trafficPolicy:
    connectionPool:
      http:
        http1MaxPendingRequests: 10
        maxRequestsPerConnection: 1
    outlierDetection:
      consecutive5xxErrors: 3
      interval: 30s
      baseEjectionTime: 120s
```

### 3. 设置超时

```yaml
# Set explicit Timeout for external services
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: external-api-timeout
spec:
  hosts:
  - api.example.com
  http:
  - route:
    - destination:
        host: api.example.com
    timeout: 10s  # Explicit Timeout
    retries:
      attempts: 2
      perTryTimeout: 5s
```

### 4. 在生产环境使用 Egress Gateway

```yaml
# Control external traffic through Egress Gateway in production
# - Centralized monitoring
# - Easy IP whitelist management
# - Consistent security policies
```

### 5. 确保命名空间配置可见

```yaml
# Isolate ServiceEntry by namespace
apiVersion: networking.istio.io/v1
kind: Sidecar
metadata:
  name: default
  namespace: team-a
spec:
  egress:
  - hosts:
    - "team-a/*"  # Only own namespace
    - "istio-system/*"
    - "external/*"  # Shared external services
  outboundTrafficPolicy:
    mode: REGISTRY_ONLY
```

### 6. 文档模板

```yaml
# Metadata excerpt; replace illustrative SLA/cost values with the actual service contract
metadata:
  name: external-service
  annotations:
    # Service information
    service-description: "Third-party payment API"
    service-owner: "payments-team@company.com"
    service-documentation: "https://wiki.company.com/payment-api"

    # SLA information
    sla-availability: "99.9%"
    sla-latency-p95: "500ms"
    rate-limit: "1000 req/min"

    # Cost information
    cost-per-request: "$0.01"
    monthly-budget: "$10000"

    # Incident response
    oncall: "payments-oncall"
    escalation: "CTO"
    fallback-strategy: "Use cached data"
```

## 参考资料

- [Istio ServiceEntry](https://istio.io/latest/docs/reference/config/networking/service-entry/)
- [Istio Egress 流量](https://istio.io/latest/docs/tasks/traffic-management/egress/)
- [Istio TLS 发起](https://istio.io/latest/docs/tasks/traffic-management/egress/egress-tls-origination/)
- [Envoy 外部服务](https://www.envoyproxy.io/docs/envoy/latest/intro/arch_overview/upstream/service_discovery)

- [主要参考资料 1](https://istio.io/latest/docs/reference/config/networking/service-entry/)
- [主要参考资料 2](https://istio.io/latest/docs/ops/configuration/traffic-management/dns-proxy/)
- [主要参考资料 3](https://istio.io/latest/docs/reference/config/networking/sidecar/)
- [主要参考资料 4](https://istio.io/latest/docs/reference/config/networking/destination-rule/)
- [主要参考资料 5](https://istio.io/latest/docs/tasks/traffic-management/egress/egress-gateway/)
- [主要参考资料 6](https://istio.io/latest/docs/tasks/traffic-management/egress/egress-tls-origination/)
- [主要参考资料 7](https://docs.aws.amazon.com/AmazonS3/latest/userguide/VirtualHosting.html)
- [主要参考资料 8](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/UsingWithRDS.SSL.html)
