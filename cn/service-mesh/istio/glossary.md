# Istio 术语表

> **已审查版本**：Istio 1.31.0
> **最近更新**：September 13, 2026

本术语表按分组参考章节整理 Istio 和服务网格相关的主要术语。

> **参考语言**：下方指向 Architecture 和 DestinationRule 章节的链接使用持续维护的英文指南，供相关译文尚未同步时查阅当前参考内容。

## 目录

- [A-C](#a-c)
- [D-F](#d-f)
- [G-I](#g-i)
- [J-L](#j-l)
- [M-O](#m-o)
- [P-R](#p-r)
- [S-U](#s-u)
- [V-Z](#v-z)

---

## A-C {#a-c}

### AuthorizationPolicy {#authorizationpolicy}

一种 Istio 安全策略，为选定的工作负载或目标资源定义 ALLOW、DENY、CUSTOM 或 AUDIT 行为。身份验证与授权是不同的机制；waypoint 策略使用 targetRefs。

### 控制平面 {#control-plane}

由 istiod 实现的配置、服务发现和身份管理层。应用载荷通过数据平面代理流动，而不是通过 istiod。

### Ambient 模式 {#ambient-mode}

一种无需 Sidecar 代理即可提供服务网格功能的数据平面模式，首次于 Istio 1.18 以 alpha 形式发布，自 Istio 1.24 起正式可用。

**功能**：
- 无需 Sidecar 容器
- 在节点层面使用 ztunnel
- 提高资源效率
- 分离 L4 和 L7 功能

**相关文档**：[Ambient 模式](advanced/01-ambient-mode.md)

---

### 证书颁发机构（CA） {#certificate-authority-ca}

为服务间 mTLS 通信颁发并管理证书的机构。

**在 Istio 中的角色**：
- Istiod 的 Citadel 功能承担 CA 角色
- 根据 SPIFFE ID 颁发证书
- 自动续订证书（默认 TTL：24 小时）

**相关术语**：[Citadel](#citadel)、[SPIFFE](#spiffe-secure-production-identity-framework-for-everyone)、[mTLS](#mtls-mutual-tls)

---

### 熔断器

一种阻断发往故障服务的请求、以防故障传播到整个系统的模式。

**工作原理**：
1. **Closed（关闭）**：正常运行
2. **Open（打开）**：连续故障后阻断请求
3. **Half-Open（半开）**：经过一定时间后允许部分请求

**Istio 实现**：连接池熔断和针对单个端点的异常剔除，不会直接暴露上述三状态的状态机。
```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: glossary-example-1
spec:
  host: reviews
  trafficPolicy:
    outlierDetection:
      consecutive5xxErrors: 5
      interval: 30s
      baseEjectionTime: 30s
```

**相关文档**：[熔断器](traffic-management/07-circuit-breaker.md)

---

### Citadel {#citadel}

在包括 Istio 1.4 在内的早期版本中独立存在的安全组件，现已集成到 Istiod。

**主要功能**：
- 证书颁发机构（CA）管理
- SPIFFE ID 的签发与管理
- X.509 证书生成与续订

**当前状态**：在 Istio 1.5+ 中作为 Istiod 内部功能存在

**相关术语**：[Istiod](#istiod)、[证书颁发机构](#certificate-authority-ca)

---

### CDS（集群发现服务） {#cds-cluster-discovery-service}

xDS API 之一，使 Envoy 能动态接收上游服务（集群）的配置。

**提供的信息**：
- 集群名称和类型
- 负载均衡策略
- 健康检查设置
- 熔断器设置
- TLS 设置

**相关术语**：[xDS](#xds-discovery-service)、[Envoy](#envoy-proxy)

---

## D-F {#d-f}

### 数据平面

服务网格中处理实际流量的层。

**Istio 的数据平面**：
- Envoy sidecar，或 ambient ztunnel 加可选的 L7 waypoint
- 处理已加入网格的流量；仍受排除规则和协议限制约束
- mTLS 加密/解密
- 指标收集

**相关术语**：[控制平面](#control-plane)、[Envoy](#envoy-proxy)

---

### DestinationRule

定义由 VirtualService 路由的流量所用策略的 Istio CRD。

**主要功能**：
- 定义子集（版本、区域等）
- 负载均衡策略
- 连接池设置
- 熔断器设置
- TLS 设置

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews
spec:
  host: reviews
  subsets:
  - name: v1
    labels:
      version: v1
  - name: v2
    labels:
      version: v2
```

**相关文档**：[DestinationRule](traffic-management/03-destination-rule.md)

---

### eBPF（扩展伯克利包过滤器） {#ebpf-extended-berkeley-packet-filter}

一种允许程序在 Linux 内核中安全运行的技术。

Istio 可以与 Cilium 等基于 eBPF 的主 CNI 共存。Istio CNI 是单独的链式插件/节点代理，负责配置重定向；ambient 不要求 eBPF，也不会替代主 CNI。

**优势**：
- 低开销
- 内核级处理
- 动态编程能力

**相关术语**：[Ambient 模式](#ambient-mode)、[iptables](#iptables)

---

### EDS（端点发现服务） {#eds-endpoint-discovery-service}

xDS API 之一，动态提供一个集群中的实际端点（Pod IP）。

**提供的信息**：
- 端点 IP 地址和端口
- 健康状态
- 负载均衡权重
- 位置（Locality）信息

**示例**：
```json
{
  "cluster_name": "outbound|9080||reviews",
  "endpoints": [
    {
      "lb_endpoints": [
        {"endpoint": {"address": {"socket_address": {"address": "10.244.1.5", "port_value": 9080}}}},
        {"endpoint": {"address": {"socket_address": {"address": "10.244.2.8", "port_value": 9080}}}}
      ]
    }
  ]
}
```

**相关术语**：[xDS](#xds-discovery-service)、[CDS](#cds-cluster-discovery-service)

---

### Envoy 代理 {#envoy-proxy}

构成 Istio 数据平面的高性能 L7 代理。

**历史**：
- 2016 年由 Lyft 的 Matt Klein 开发
- 2017 年成为 CNCF 孵化项目
- 2018 年成为 CNCF 毕业项目

**主要特性**：
- 用 C++ 编写的高性能代理
- 通过 xDS API 动态配置
- 支持 HTTP/1.1、HTTP/2 和 gRPC
- 丰富的可观测性

**组件**：
- Listener：侦听端口
- Filter：处理请求/响应
- Router：决定路由
- Cluster：上游服务

**相关文档**：[架构 - Envoy 代理](https://www.atomai.click/kubernetes-docs/en/service-mesh/istio/03-architecture#data-plane-envoy-proxy)

---

## G-I {#g-i}

### Galley

在包括 Istio 1.4 在内的早期版本中独立存在的配置验证组件，现已集成到 Istiod。

**主要功能**：
- 验证 Istio 配置
- 处理 Kubernetes 资源
- 在部署配置前检查错误

**当前状态**：在 Istio 1.5+ 中作为 Istiod 内部功能存在

**相关术语**：[Istiod](#istiod)

---

### Gateway

定义外部流量进入服务网格的入口的 Istio CRD。

**类型**：
1. **Ingress Gateway**：从外部到内部的流量
2. **Egress Gateway**：从内部到外部的流量

```yaml
apiVersion: networking.istio.io/v1
kind: Gateway
metadata:
  name: my-gateway
spec:
  selector:
    istio: ingressgateway
  servers:
  - port:
      number: 80
      name: http
      protocol: HTTP
    hosts:
    - "example.com"
```

**相关文档**：[Gateway 和 VirtualService](traffic-management/01-gateway-virtualservice.md)

---

### gRPC

Google 开发的高性能 RPC（远程过程调用）框架。

**与 Istio 的关系**：
- xDS API 基于 gRPC
- 用于 Istiod 与 Envoy 之间的通信
- 基于 HTTP/2（支持多路复用）

**优势**：
- 双向流式传输
- 低延迟
- 使用 Protocol Buffers

**相关术语**：[xDS](#xds-discovery-service)

---

### 身份 {#identity}

表示服务网格内工作负载的身份。

**Istio 的身份**：
- 使用 SPIFFE ID 格式
- 基于 Kubernetes ServiceAccount
- 由 X.509 证书证明

**示例**：
```
spiffe://cluster.local/ns/default/sa/reviews
```

**相关术语**：[SPIFFE](#spiffe-secure-production-identity-framework-for-everyone)、[mTLS](#mtls-mutual-tls)

---

### iptables {#iptables}

在 Linux 中控制网络流量的防火墙工具。

**在 Istio 中的作用**：
- istio-init 或 Istio CNI 节点代理配置流量重定向
- 将所有 Pod 流量重定向到 Envoy
- 使用 NAT 表（PREROUTING、OUTPUT 链）

**简化规则（仅作说明，不是安装脚本）**：
```bash
# Outbound: All traffic except Envoy -> 15001
iptables -t nat -A OUTPUT -p tcp -m owner ! --uid-owner 1337 -j REDIRECT --to-port 15001

# Inbound: All traffic -> 15006
iptables -t nat -A PREROUTING -p tcp -j REDIRECT --to-port 15006
```

**替代配置方式**：Istio CNI 在节点级执行需要特权的网络配置。

**相关文档**：[架构 - iptables](https://www.atomai.click/kubernetes-docs/en/service-mesh/istio/03-architecture#iptables-and-traffic-interception)

---

### Istiod {#istiod}

Istio 1.5+ 中统一的控制平面组件。

**集成的功能**：
- **Pilot**：服务发现、流量管理
- **Citadel**：证书颁发机构、身份
- **Galley**：配置验证

**运行方式**：
- 单一 Go 二进制文件：`pilot-discovery`
- 所有功能在同一进程中运行
- 默认端口：15012（xDS）、15017（Webhook）

**优势**：
- 降低复杂度
- 简化运维
- 提高资源效率

**相关文档**：[架构 - Istiod](https://www.atomai.click/kubernetes-docs/en/service-mesh/istio/03-architecture#control-plane-istiod)

---

## J-L {#j-l}

### LDS（侦听器发现服务） {#lds-listener-discovery-service}

xDS API 之一，使 Envoy 能动态接收需要侦听的端口和过滤器链。

**提供的信息**：
- 侦听器地址和端口
- 协议（HTTP、TCP）
- 过滤器链配置
- TLS 设置

**Istio 的默认侦听器**：
- `0.0.0.0:15001`：出站 TCP
- `0.0.0.0:15006`：入站 TCP
- `0.0.0.0:15021`：健康检查
- `0.0.0.0:15090`：Prometheus 指标

**相关术语**：[xDS](#xds-discovery-service)、[Envoy](#envoy-proxy)

---

### 位置感知负载均衡 {#locality-aware-load-balancing}

一种考虑位置（区域、可用区）信息的负载均衡方式。

**优先顺序**：
1. 同一可用区内的端点
2. 同一区域内的其他可用区
3. 其他区域

**配置示例**：
```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: glossary-example-2
spec:
  host: reviews
  trafficPolicy:
    loadBalancer:
      localityLbSetting:
        enabled: true
        distribute:
        - from: us-west/zone-1a/*
          to:
            "us-west/zone-1a/*": 80
            "us-west/zone-1b/*": 20
```

**相关文档**：[分区感知路由](resilience/03-zone-aware-routing.md)

---

## M-O {#m-o}

### Mixer

在包括 Istio 1.4 在内的早期版本中存在的策略和遥测组件。

**主要功能**：
- 策略执行（速率限制、访问控制）
- 遥测收集

**移除原因**：
- 性能开销（每个请求都调用 Mixer）
- 架构复杂

**当前状态**：在 1.5 迁移期间弃用；剩余的 Mixer 功能在 1.8 中移除

**相关术语**：[Istiod](#istiod)

---

### mTLS（双向 TLS） {#mtls-mutual-tls}

一种客户端与服务器相互验证身份的双向 TLS 通信方式。

**Istio 的 mTLS**：
- 自动颁发和续订证书
- 基于 SPIFFE ID 的身份验证
- TLS 密码套件通过协商确定，并不固定为 AES-256-GCM

**模式**：
1. **STRICT**：仅允许 mTLS
2. **PERMISSIVE**：允许 mTLS 和明文（用于迁移）
3. **DISABLE**：在 sidecar 模式下禁用 Istio 传输层 mTLS；ambient 不支持此模式

```yaml
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: default
spec:
  mtls:
    mode: STRICT
```

**相关文档**：[mTLS](security/01-mtls.md)

---

### 异常端点检测

自动排除表现异常的端点的功能。

**检测条件**：
- 连续错误次数
- 错误率
- 连接失败/超时；延迟本身不是异常端点剔除阈值

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: glossary-example-3
spec:
  host: reviews
  trafficPolicy:
    outlierDetection:
      consecutive5xxErrors: 5
      interval: 30s
      baseEjectionTime: 30s
      maxEjectionPercent: 50
```

**相关文档**：[异常端点检测](resilience/01-outlier-detection.md)

---

## P-R {#p-r}

### 下游（Downstream） {#downstream}

从 Envoy 的视角看，这是指**发送请求的一方**，即向 Envoy 发起连接的客户端。

**Envoy 的下游**：
- 进入 Envoy 的连接（入站）
- 发送请求的客户端
- 侦听器接收的连接

**流量路径**：
```
Downstream (Client)  ->  Envoy Proxy  ->  Upstream (Backend)
```

**示例场景**：

#### 1. Sidecar 模式 - 出站请求

![在 sidecar 模式下，应用（下游）向同一 Pod 中的 Envoy sidecar 发送请求，Envoy 将请求转发到后端服务（上游）。](../../.gitbook/assets/en-service-mesh-istio-glossary-0.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-glossary-0.html)

**视角**：
- **从 Envoy 看**：应用是下游（发送请求）
- **从 Envoy 看**：后端服务是上游（接收请求）

#### 2. Ingress Gateway - 外部请求

![从 Ingress Gateway 的 Envoy 视角看，外部客户端是下游，其路由目标内部服务是上游。](../../.gitbook/assets/en-service-mesh-istio-glossary-1.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-glossary-1.html)

**与下游相关的 Envoy 配置**：

```yaml
# Listener - Receive Downstream connections
apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata:
  name: downstream-config
  namespace: default
spec:
  workloadSelector:
    labels:
      app: reviews
  configPatches:
  - applyTo: LISTENER
    match:
      context: SIDECAR_INBOUND
    patch:
      operation: MERGE
      value:
        per_connection_buffer_limit_bytes: 32768  # Downstream buffer
```

**下游指标**：
```bash
# Downstream connection count
envoy_listener_downstream_cx_active

# Downstream request count
envoy_http_downstream_rq_total

# Downstream response time
envoy_http_downstream_rq_time
```

**相关术语**：[上游](#upstream)、[Envoy](#envoy-proxy)、[侦听器](#lds-listener-discovery-service)

---

### 上游（Upstream） {#upstream}

从 Envoy 的视角看，这是指**接收请求的一方**，即 Envoy 向其发起连接的后端服务。

**Envoy 的上游**：
- 从 Envoy 发出的连接（出站）
- 处理请求的后端服务
- 由 Cluster 管理的端点

**流量路径**：
```
Downstream (Client)  ->  Envoy Proxy  ->  Upstream (Backend)
```

**上游组件**：

#### 1. Cluster（上游组）

```yaml
# Define Upstream Cluster with DestinationRule
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews
spec:
  host: reviews  # Upstream service
  trafficPolicy:
    loadBalancer:
      simple: ROUND_ROBIN
    connectionPool:
      tcp:
        maxConnections: 100      # Upstream connection limit
      http:
        http1MaxPendingRequests: 50
        http2MaxRequests: 100
    outlierDetection:
      consecutive5xxErrors: 5        # Upstream failure detection
      interval: 30s
```

#### 2. Endpoint（实际的上游实例）

```bash
# Check upstream endpoints
istioctl proxy-config endpoints <pod-name> | grep reviews

# Example output:
# ENDPOINT              STATUS      CLUSTER
# 10.244.1.5:9080       HEALTHY     outbound|9080||reviews.default.svc.cluster.local
# 10.244.2.8:9080       HEALTHY     outbound|9080||reviews.default.svc.cluster.local
# 10.244.3.12:9080      UNHEALTHY   outbound|9080||reviews.default.svc.cluster.local
```

**上游流量策略**：

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: glossary-example-4
spec:
  host: reviews
  trafficPolicy:
    # Upstream load balancing
    loadBalancer:
      consistentHash:
        httpHeaderName: "x-user-id"

    # Upstream connection pool
    connectionPool:
      tcp:
        maxConnections: 100
        connectTimeout: 30s
      http:
        h2UpgradePolicy: UPGRADE

    # Upstream TLS
    tls:
      mode: ISTIO_MUTUAL

    # Upstream Circuit Breaker
    outlierDetection:
      consecutive5xxErrors: 5
      interval: 10s
      baseEjectionTime: 30s
```

**上游与下游比较**：

| 项目 | 下游 | 上游 |
|------|-----------|----------|
| **方向** | 进入 Envoy（入站） | 离开 Envoy（出站） |
| **角色** | 发送请求（客户端） | 接收请求（服务器） |
| **Envoy 配置** | Listener、Filter Chain | Cluster、Endpoint |
| **示例** | 外部用户、其他服务 | 后端 API、数据库 |
| **指标** | `downstream_cx_*`、`downstream_rq_*` | `upstream_cx_*`、`upstream_rq_*` |

**实际示例**：

#### 场景 1：Service A -> Service B 调用

```
+---------------------------------------------------------+
| Service A Pod                                           |
|                                                         |
|  App --> Envoy Sidecar                                 |
|          |                                              |
|          | Downstream: App                              |
|          | Upstream: Service B                          |
+----------|-------------------------------------------------+
           |
           v
+---------------------------------------------------------+
| Service B Pod                                           |
|                                                         |
|          Envoy Sidecar --> App                          |
|          |                                              |
|          | Downstream: Service A Envoy                  |
|          | Upstream: Local App (Service B)              |
+---------------------------------------------------------+
```

**Service A 的 Envoy 视角**：
- 下游：Service A 的应用
- 上游：Service B

**Service B 的 Envoy 视角**：
- 下游：Service A 的 Envoy
- 上游：Service B 的应用（本地）

#### 场景 2：Ingress Gateway

```
External Client (Downstream)
        |
Ingress Gateway (Envoy)
        |
Internal Service (Upstream)
```

**上游指标**：

```bash
# Upstream connection count
envoy_cluster_upstream_cx_active

# Upstream request counter; derive success/error rates from response-class counters
envoy_cluster_upstream_rq_total

# Upstream response time
envoy_cluster_upstream_rq_time

# Upstream health check
envoy_cluster_health_check_success

# Upstream Circuit Breaker
envoy_cluster_circuit_breakers_default_remaining_rq
```

**被动上游健康检测**：主动健康检查统计需要单独配置。

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: glossary-example-5
spec:
  host: reviews
  trafficPolicy:
    outlierDetection:
      # Upstream health detection
      consecutiveGatewayErrors: 5
      consecutive5xxErrors: 5
      interval: 10s
      baseEjectionTime: 30s
      maxEjectionPercent: 50
```

**调试**：

```bash
# 1. Check upstream cluster
istioctl proxy-config clusters <pod-name> --fqdn reviews.default.svc.cluster.local

# 2. Check upstream endpoint status
istioctl proxy-config endpoints <pod-name> --cluster "outbound|9080||reviews.default.svc.cluster.local"

# 3. Check upstream metrics
kubectl exec <pod-name> -c istio-proxy -- \
  curl -s localhost:15000/stats/prometheus | grep upstream

# 4. Check upstream connections
istioctl proxy-config all <pod-name> -o json | \
  jq '.configs[] | select(.["@type"] | contains("ClustersConfigDump"))'
```

**相关术语**：[下游](#downstream)、[Envoy](#envoy-proxy)、[Cluster](#cds-cluster-discovery-service)、[Endpoint](#eds-endpoint-discovery-service)

---

### Pilot

在包括 Istio 1.4 在内的早期版本中独立存在的流量管理组件，现已集成到 Istiod。

**主要功能**：
- 服务发现
- 流量管理（处理 VirtualService、DestinationRule）
- xDS 服务器

**当前状态**：在 Istio 1.5+ 中作为 Istiod 内部功能存在

**相关术语**：[Istiod](#istiod)、[xDS](#xds-discovery-service)

---

### RDS（路由发现服务）

xDS API 之一，动态提供 HTTP 路由规则。

**提供的信息**：
- 路由匹配规则（路径、请求头等）
- 基于权重的路由
- 重定向和重写规则
- 超时和重试设置

**与 VirtualService 的关系**：
- VirtualService -> 由 Istiod 转换 -> RDS 配置

**相关术语**：[xDS](#xds-discovery-service)、[VirtualService](#virtualservice)

---

### 速率限制

限制单位时间内允许的请求数量的功能。

**实现方式**：
1. **本地速率限制**：由 Envoy 在本地处理
2. **全局速率限制**：使用外部速率限制服务

```yaml
apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata:
  name: filter-local-ratelimit
  namespace: default
spec:
  workloadSelector:
    labels:
      app: reviews
  configPatches:
  - applyTo: HTTP_FILTER
    match:
      context: SIDECAR_INBOUND
      listener:
        filterChain:
          filter:
            name: envoy.filters.network.http_connection_manager
            subFilter:
              name: envoy.filters.http.router
    patch:
      operation: INSERT_BEFORE
      value:
        name: envoy.filters.http.local_ratelimit
        typed_config:
          "@type": type.googleapis.com/envoy.extensions.filters.http.local_ratelimit.v3.LocalRateLimit
          stat_prefix: http_local_rate_limiter
          token_bucket:
            max_tokens: 100
            tokens_per_fill: 100
            fill_interval: 1s
          filter_enabled:
            default_value:
              numerator: 100
              denominator: HUNDRED
          filter_enforced:
            default_value:
              numerator: 100
              denominator: HUNDRED
```

**相关文档**：[速率限制](resilience/02-rate-limiting.md)

---

## S-U {#s-u}

### SDS（秘密发现服务）

xDS API 之一，动态提供 TLS 证书和密钥。

**提供的信息**：
- X.509 证书
- 私钥
- CA 根证书

**优势**：
- 不需要文件系统
- 自动续订证书
- 无停机续订

**相关术语**：[xDS](#xds-discovery-service)、[mTLS](#mtls-mutual-tls)

---

### Service Entry {#service-entry}

将服务网格外部的服务注册到网格中的 Istio CRD。

**使用场景**：
- 外部 API 访问控制
- 将 Istio 功能应用到外部服务（重试、超时等）
- 与 Egress Gateway 集成

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: external-api
spec:
  hosts:
  - api.external.com
  ports:
  - number: 443
    name: https
    protocol: HTTPS
  location: MESH_EXTERNAL
  resolution: DNS
```

**相关文档**：[ServiceEntry](traffic-management/12-service-entry.md)

---

### 服务网格

管理微服务之间通信的基础设施层。

**核心功能**：
- 流量管理（路由、负载均衡）
- 安全（mTLS、身份验证/授权）
- 可观测性（指标、日志、追踪）
- 弹性（重试、熔断器）

**主要实现**：
- Istio
- Linkerd
- Consul Connect
- AWS App Mesh（[支持于 September 30, 2026 结束](https://docs.aws.amazon.com/app-mesh/latest/userguide/what-is-app-mesh.html)）

---

### SigV4（AWS 签名版本 4）

用于验证 AWS API 请求身份的签名协议。

**工作原理**：

![时序图展示 Envoy 如何使用 AWS SigV4 凭据透明地为客户端出站请求签名，再将其转发到 AWS 服务并返回响应。](../../.gitbook/assets/en-service-mesh-istio-glossary-2.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-glossary-2.html)

**签名组成**：

1. **Canonical Request**：请求的标准化格式
   - HTTP 方法
   - URI 路径
   - 查询字符串
   - 请求头
   - 载荷哈希

2. **String to Sign**：待签名的字符串
   - 算法：`AWS4-HMAC-SHA256`
   - 时间戳
   - 凭据范围
   - Canonical Request 哈希

3. **Signing Key**：计算签名密钥
   ```
   HMAC(HMAC(HMAC(HMAC("AWS4" + SecretKey, Date), Region), Service), "aws4_request")
   ```

4. **Signature**：最终签名
   ```
   HMAC(SigningKey, StringToSign)
   ```

**与 Istio 集成**：

AWS SDK 和 AWS CLI 使用 IRSA 或 EKS Pod Identity 提供的临时凭据为 HTTPS 请求签名。这使签名与工作负载的 AWS 权限关联。Istio mTLS 身份与 AWS IAM 身份是分离的。

Envoy 的 `aws_request_signing` HTTP 过滤器是一种高级替代方案。它需要包含该扩展的 Envoy 构建、**代理容器**可用的凭据、正确的 AWS 服务/区域，以及仅匹配预期 AWS 目标的过滤器条件。应将其插在 router 之前、任何影响签名的请求头/路径重写之后。应用发起的 HTTPS 对此 HTTP 过滤器是不透明的：Envoy 无法在加密的 TLS 内添加签名。代理签名设计必须向签名代理提供 HTTP，并在上游发起经过验证的 TLS；避免双重 TLS 发起，或将未签名的 HTTP 暴露到预期的本地代理路径之外。

上图描述的是这种显式配置的签名代理路径，而不是 Istio 的默认能力。仅在应用 ServiceAccount 上添加 IRSA 注解，不能证明 gateway 或 sidecar 已具备所需的凭据环境和令牌挂载。

**身份验证不等同于 JWT 验证**：

SigV4 是 HMAC 请求签名，不是 JWT。`https://sts.amazonaws.com/.well-known/jwks` 不是用于验证 AWS API 签名的 JWT 颁发者端点。Istio RequestAuthentication 验证来自真实 OIDC 颁发者的 JWT。CUSTOM AuthorizationPolicy 还需要一个已配置、实现外部授权的 `extensionProviders` 服务；没有该实现，就不能验证 SigV4。访问 AWS API 时，应优先使用经 IAM 身份验证的 AWS 端点或 AWS SDK。

**只读验证示例**（工作负载中已安装 AWS CLI，并使用预期 IAM 角色）：

```bash
aws sts get-caller-identity
aws s3api head-object --bucket my-bucket --key object.txt --region us-west-2
```

**运维注意事项**：

- 只向工作负载授予必需的 AWS 操作和资源权限。避免依赖共享节点实例角色。
- 确认所选凭据提供程序支持临时凭据及刷新。会话时长可配置，并非一律为一小时。
- CloudTrail 管理事件和数据事件的覆盖范围不同；S3 对象访问需要配置相应的数据事件。
- 检查代理配置以确认过滤器放置位置。配置转储不会显示每个实际请求的 Authorization 请求头，通过 HTTPS 执行未签名的 curl 也不是 SigV4 测试。
- 根据实际请求大小测量签名、缓冲及凭据获取开销；不保证固定的毫秒级开销。

**相关术语**：[AuthorizationPolicy](#authorizationpolicy)、[ServiceEntry](#service-entry)、[EnvoyFilter](advanced/03-envoy-filter.md)

**参考资料**：
- [AWS 签名版本 4](https://docs.aws.amazon.com/general/latest/gr/signature-version-4.html)
- [Envoy AWS 请求签名](https://www.envoyproxy.io/docs/envoy/latest/configuration/http/http_filters/aws_request_signing_filter)
- [AWS 集成](04-aws-integration.md)

---

### Sidecar

与应用容器一同部署的辅助容器模式。

**Istio 的 Sidecar**：
- 容器名称：`istio-proxy`
- 镜像：`istio/proxyv2`
- 运行 Envoy 代理
- 通过初始化容器或 Istio CNI 重定向拦截所配置的流量

**注入方式**：
1. **自动**：命名空间标签
2. **手动**：`istioctl kube-inject`

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: example-mesh
  labels:
    istio-injection: enabled  # Automatic injection
```

**相关文档**：[Sidecar 注入](advanced/07-sidecar-injection.md)

---

### Sidecar 资源

限制 Envoy 接收的服务信息的 Istio CRD。

**目的**：
- 降低内存使用量
- 缩短配置推送时间
- 限定配置范围；不是网络安全边界

```yaml
apiVersion: networking.istio.io/v1
kind: Sidecar
metadata:
  name: default
  namespace: default
spec:
  egress:
  - hosts:
    - "./*"  # Same namespace only
    - "istio-system/*"
```

**效果**：
- 减少导入的服务可以降低内存和配置处理开销；应测量实际节省量。

**相关文档**：[架构 - Sidecar 资源](https://www.atomai.click/kubernetes-docs/en/service-mesh/istio/03-architecture#optimization-with-sidecar-resource)

---

### SPIFFE（面向所有人的安全生产身份框架） {#spiffe-secure-production-identity-framework-for-everyone}

用于在云原生环境中证明工作负载身份的标准。

**SPIFFE ID 格式**：
```
spiffe://trust-domain/path
```

**Istio 示例**：
```
spiffe://cluster.local/ns/default/sa/reviews
  |         |           |     |      |    |
  |         |           |     |      |    +- ServiceAccount name
  |         |           |     |      +----- "sa" (ServiceAccount)
  |         |           |     +------------ Namespace name
  |         |           +------------------ "ns" (Namespace)
  |         +------------------------------ Trust Domain
  +---------------------------------------- Protocol
```

**组成**：
- **SPIFFE ID**：工作负载标识符
- **SVID（SPIFFE 可验证身份文档）**：X.509-SVID 或 JWT-SVID；Istio mTLS 使用 X.509-SVID

**相关术语**：[身份](#identity)、[mTLS](#mtls-mutual-tls)

---

### 子集

在 DestinationRule 中定义的服务逻辑分组。

**常见用途**：
- 按版本：`v1`、`v2`、`v3`
- 按部署阶段：`stable`、`canary`、`test`
- 按区域：`us-west`、`us-east`、`eu-central`

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: glossary-example-6
spec:
  host: reviews
  subsets:
  - name: v1
    labels:
      version: v1
  - name: v2
    labels:
      version: v2
```

**相关文档**：[DestinationRule - 子集概念](https://www.atomai.click/kubernetes-docs/en/service-mesh/istio/traffic-management/03-destination-rule#subset-concept)

---

## V-Z {#v-z}

### Waypoint 代理 {#waypoint-proxy}

在 Ambient 模式下提供 L7 功能的可选代理。

**作用**：
- 通过命名空间、Service 或 Pod 标签选择；不会自动按 ServiceAccount 配置
- 基于 Envoy 代理
- 专注于 L7 流量管理功能
- 与 ztunnel 协同工作

**提供的功能**：
- L7 路由（基于路径、请求头）
- 重试和超时
- 熔断器
- 故障注入
- 请求头操作

**部署示例**：
```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: reviews-waypoint
  namespace: default
spec:
  gatewayClassName: istio-waypoint
  listeners:
  - name: mesh
    port: 15008
    protocol: HBONE
```

**特性**：
- ztunnel 仅处理 L4，waypoint 处理 L7
- 仅为需要的服务选择性使用
- 比 Sidecar 更节省资源（共享方式）
- 通过命名空间、Service 或 Pod 标签选择；不会自动按 ServiceAccount 配置

**相关术语**：[Ambient 模式](#ambient-mode)、[ztunnel](#ztunnel-zero-trust-tunnel)

---

创建 waypoint 后，需为目标服务启用它，例如 `kubectl label service reviews istio.io/use-waypoint=reviews-waypoint --overwrite`。仅部署 Gateway 不会使流量通过它。

### VirtualService {#virtualservice}

定义服务网格内流量如何路由的 Istio CRD。

**主要功能**：
- 基于 URI、请求头和查询参数的路由
- 基于权重的流量分配
- 重试和超时设置
- 故障注入

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: reviews
spec:
  hosts:
  - reviews
  http:
  - match:
    - uri:
        prefix: "/v2"
    route:
    - destination:
        host: reviews
        subset: v2
  - route:
    - destination:
        host: reviews
        subset: v1
```

**相关文档**：[Gateway 和 VirtualService](traffic-management/01-gateway-virtualservice.md)

---

### WASM（WebAssembly）

一种为在 Web 浏览器中运行而设计的二进制指令格式。在 Istio 中，用于扩展 Envoy 代理的功能。

**在 Istio 中的用途**：
- 以 Envoy Filter 形式添加自定义逻辑
- 无需重新部署即可动态扩展功能
- 可使用多种语言编写（Rust、C++、Go 等）
- 在沙箱环境中安全运行

**主要使用场景**：
1. **自定义身份验证/授权**：实现复杂业务逻辑
2. **请求/响应转换**：请求头操作、载荷转换
3. **高级路由**：自定义路由逻辑
4. **指标收集**：专用遥测

下面的镜像仓库 URL、摘要、凭据和 pluginConfig 字段是您自行构建插件的占位内容；Istio 不提供这些示例镜像，也不会解释插件特有的选项。file:// 模块必须存在于代理容器内部。

**WASM 插件示例**：
```yaml
apiVersion: extensions.istio.io/v1alpha1
kind: WasmPlugin
metadata:
  name: custom-auth
  namespace: istio-system
spec:
  selector:
    matchLabels:
      istio: ingressgateway
  url: oci://ghcr.io/my-org/custom-auth:v1.0.0
  phase: AUTHN
  pluginConfig:
    api_key_header: "X-API-Key"
    validate_endpoint: "https://auth.example.com/validate"
```

**部署方式**：

#### 1. 通过 OCI 镜像仓库部署（推荐）

```yaml
apiVersion: extensions.istio.io/v1alpha1
kind: WasmPlugin
metadata:
  name: rate-limiter
spec:
  url: oci://ghcr.io/my-org/rate-limit:v1.0.0
  imagePullPolicy: Always
  imagePullSecret: registry-credential
```

#### 2. 通过 HTTP URL 部署

```yaml
apiVersion: extensions.istio.io/v1alpha1
kind: WasmPlugin
metadata:
  name: custom-filter
spec:
  url: https://example.com/filters/custom-filter.wasm
  # Add sha256: with the actual 64-character module digest before deployment
```

#### 3. 本地文件部署

```yaml
apiVersion: extensions.istio.io/v1alpha1
kind: WasmPlugin
metadata:
  name: local-filter
spec:
  url: file:///etc/istio/filters/custom.wasm
```

**WASM 开发示例（Rust）**：

```rust
use proxy_wasm::traits::*;
use proxy_wasm::types::*;

proxy_wasm::main! {{
    proxy_wasm::set_http_context(|_, _| -> Box<dyn HttpContext> {
        Box::new(CustomFilter)
    });
}}

struct CustomFilter;
impl Context for CustomFilter {}

impl HttpContext for CustomFilter {
    fn on_http_request_headers(&mut self, _: usize, _: bool) -> Action {
        // Demonstrate header mutation, not production API-key authentication.
        self.set_http_request_header("x-mesh-demo", Some("wasm"));
        Action::Continue
    }
}
```

**构建和部署前提**：

使用 Rust `cdylib` crate，配置兼容的 `proxy-wasm` 依赖并锁定依赖版本。上面的回调遵循[官方 Rust SDK 示例](https://github.com/proxy-wasm/proxy-wasm-rust-sdk/tree/main/examples/http_headers)。安装 `wasm32-unknown-unknown` 目标，构建模块，并将生成的 `.wasm` 打包到受支持的 OCI Wasm 镜像中，然后再通过 WasmPlugin 引用。没有 Dockerfile 的通用 `docker build` 命令不会完成这项打包。

```bash
rustup target add wasm32-unknown-unknown
cargo build --target wasm32-unknown-unknown --release
```

应针对具体插件测量启动时间、内存和每请求开销。Wasm 在代理进程内的运行时沙箱中执行；它不是独立进程，也不构成无条件的安全/性能保证。

**Ambient 模式支持**：

```yaml
apiVersion: extensions.istio.io/v1alpha1
kind: WasmPlugin
metadata:
  name: waypoint-filter
spec:
  targetRefs:
  - group: gateway.networking.k8s.io
    kind: Gateway
    name: reviews-waypoint
  url: oci://ghcr.io/filters/custom:latest
  phase: AUTHN
```

**调试**：

```bash
# Check WASM plugin status
kubectl get wasmplugin -A

# Check WASM-related logs in Envoy logs
kubectl logs <pod-name> -c istio-proxy | grep wasm

# Check WASM module load
istioctl proxy-config all <pod-name> -o json | jq '.. | objects | select(has("@type")) | select(.["@type"] | test("wasm"; "i"))'
```

**安全注意事项**：
1. **沙箱隔离**：Envoy 内部的运行时沙箱；应审查插件信任和资源使用
2. **资源限制**：可配置 CPU 和内存限制
3. **完整性验证**：SHA256 检查内容；不会验证发布者身份
4. **最小权限**：仅授予必要权限

**优势**：
- 高性能（原生代码级别）
- 安全的沙箱执行
- 无需重新部署即可更新
- 支持多种语言
- 标准 OCI 镜像格式

**限制**：
- 部分系统调用受限
- 文件 I/O 受限
- 网络调用只能通过 Envoy API

**相关术语**：[Envoy](#envoy-proxy)、[Waypoint 代理](#waypoint-proxy)、[Ambient 模式](#ambient-mode)

**参考资料**：
- [Istio WASM 插件](https://istio.io/latest/docs/reference/config/proxy_extensions/wasm-plugin/)
- [Proxy-Wasm SDK](https://github.com/proxy-wasm)
- [WebAssembly 官方网站](https://webassembly.org/)
- [Ambient 模式 - WASM](https://istio.io/latest/docs/ambient/usage/extend-waypoint-wasm/)

---

### xDS（发现服务） {#xds-discovery-service}

用于动态配置 Envoy 代理的一组 API。

**“xDS”的含义**：
- `x`：代表不同类型的变量
- `DS`：发现服务

**xDS API 类型**：

| API | 名称 | 作用 |
|-----|------|------|
| **LDS** | 侦听器发现服务 | 侦听端口和过滤器链 |
| **RDS** | 路由发现服务 | HTTP 路由规则 |
| **CDS** | 集群发现服务 | 上游服务配置 |
| **EDS** | 端点发现服务 | 实际 Pod IP 列表 |
| **SDS** | 秘密发现服务 | TLS 证书和密钥 |

**通信方式**：
- 协议：gRPC
- 端口：15012（Istiod）
- 双向流式传输

**顺序**：
```
Agent bootstraps identity -> Envoy subscribes to ADS resources
Istiod pushes LDS/CDS/EDS/RDS updates; local agent serves SDS certificates
```

**相关文档**：[架构 - xDS API 通信](https://www.atomai.click/kubernetes-docs/en/service-mesh/istio/03-architecture#xds-api-communication)

---

### Zone（可用区）

表示 Kubernetes 可用区。

**标签格式**：
```yaml
topology.kubernetes.io/zone: us-west-1a
```

**在 Istio 中的用途**：
- 位置感知负载均衡
- 分区感知路由
- 同可用区优先路由

**相关术语**：[位置感知负载均衡](#locality-aware-load-balancing)

---

### ztunnel（零信任隧道） {#ztunnel-zero-trust-tunnel}

Ambient 模式的核心组件，是在节点级运行的轻量 L4 代理。

**作用**：
- 以 DaemonSet 形式部署到每个节点
- 处理所有 Pod 的 L4 流量
- 无需 Sidecar 即可提供服务网格功能
- 与 CNI 插件集成

**提供的功能**：
- **mTLS**：自动加密/解密
- **L4 遥测**：指标收集
- **身份**：基于 ServiceAccount 的身份验证
- **L4 负载均衡**：基本负载均衡

**技术特性**：
- 用 Rust 编写（高性能）
- 由 Istio CNI 管理流量重定向
- 不需要初始化容器
- 共享 L4 代理资源；根据测得的节点工作负载进行容量配置

**部署示例**：
```bash
# Use the reviewed istioctl version and the complete ambient installation profile
istioctl install --set profile=ambient
kubectl rollout status daemonset/ztunnel -n istio-system
```

对于现有 sidecar 工作负载，应先移除注入/修订标签并重启 Pod，以移除 sidecar，然后再加入 ambient；新的无 sidecar 工作负载不需要重启。

**启用命名空间**：
```bash
# Enable Ambient Mode
kubectl label namespace default istio-injection- istio.io/rev-
kubectl label namespace default istio.io/dataplane-mode=ambient --overwrite
```

**优势**：
- 潜在的内存节省取决于节点/工作负载和 waypoint 容量
- 不需要重启 Pod
- 对应用透明
- 尽量降低初始延迟

**限制**：
- L7 功能需要 Waypoint 代理
- 需要受支持的 Linux Kubernetes 平台、主 CNI，以及满足 Istio CNI 的前提条件

**相关术语**：[Ambient 模式](#ambient-mode)、[Waypoint 代理](#waypoint-proxy)、[eBPF](#ebpf-extended-berkeley-packet-filter)

---

## 参考资料

### 官方文档
- [Istio 术语表](https://istio.io/latest/docs/reference/glossary/)
- [Envoy 术语](https://www.envoyproxy.io/docs/envoy/latest/intro/arch_overview/intro/terminology)
- [SPIFFE 规范](https://github.com/spiffe/spiffe/tree/main/standards)

### 相关文档
- [Istio 架构](03-architecture.md)
- [流量管理](traffic-management/README.md)
- [安全](security/README.md)
- [可观测性](observability/README.md)

---

**最近更新**：September 11, 2026

- [Destination Rule](https://istio.io/latest/docs/reference/config/networking/destination-rule/)
- [安装 Istio CNI 节点代理](https://istio.io/latest/docs/setup/additional-setup/cni/)
- [Ztunnel 流量重定向](https://istio.io/latest/docs/ambient/architecture/traffic-redirection/)
- [使用 istioctl 安装](https://istio.io/latest/docs/ambient/install/istioctl/)
- [配置 waypoint 代理](https://istio.io/latest/docs/ambient/usage/waypoint/)
- [使用 Envoy 启用速率限制](https://istio.io/latest/docs/tasks/policy-enforcement/rate-limit/)
- [Wasm 插件](https://istio.io/latest/docs/reference/config/proxy_extensions/wasm-plugin/)
- [Proxy-Wasm Rust SDK HTTP 示例](https://raw.githubusercontent.com/proxy-wasm/proxy-wasm-rust-sdk/main/examples/http_headers/src/lib.rs)
- [API 请求的 AWS 签名版本 4 - AWS Identity and Access Management](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_sigv.html)
- [AWS 请求签名](https://www.envoyproxy.io/docs/envoy/latest/configuration/http/http_filters/aws_request_signing_filter)
- [统计信息](https://www.envoyproxy.io/docs/envoy/latest/configuration/upstream/cluster_manager/cluster_stats)
- [Istio 1.8 变更说明](https://istio.io/latest/news/releases/1.8.x/announcing-1.8/change-notes/)
- [什么是 AWS App Mesh？- AWS App Mesh](https://docs.aws.amazon.com/app-mesh/latest/userguide/what-is-app-mesh.html)

- [CloudTrail 数据事件覆盖范围](https://docs.aws.amazon.com/awscloudtrail/latest/userguide/logging-data-events-with-cloudtrail.html)
