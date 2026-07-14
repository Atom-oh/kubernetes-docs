# 基本概念

本文介绍 Istio 的核心概念和架构。理解这些基本概念对于有效使用 Istio 至关重要。

## 目录

1. [背景与历史](02-basic-concepts.md#background-and-history)
2. [为什么选择 Istio？](02-basic-concepts.md#why-istio)
3. [Istio 架构](02-basic-concepts.md#istio-architecture)
4. [部署模式：Sidecar 与 Ambient](02-basic-concepts.md#deployment-modes-sidecar-vs-ambient)
5. [核心资源](02-basic-concepts.md#core-resources)
6. [流量管理概念](02-basic-concepts.md#traffic-management-concepts)
7. [安全概念](02-basic-concepts.md#security-concepts)
8. [可观测性概念](02-basic-concepts.md#observability-concepts)
9. [Namespace 与 Service Mesh](02-basic-concepts.md#namespaces-and-service-mesh)
10. [后续步骤](02-basic-concepts.md#next-steps)

## 背景与历史

### Service Mesh 的诞生

#### Microservices 面临的挑战

2010 年代初期，企业开始将单体应用拆分为 Microservices。

```mermaid
flowchart TB
    subgraph Before[Monolithic Era]
        M[Monolithic<br/>Application]
        M -->|Single process| M
    end

    subgraph After[Microservices Era]
        S1[Service A]
        S2[Service B]
        S3[Service C]
        S4[Service D]
        S5[Service E]

        S1 --> S2
        S1 --> S3
        S2 --> S4
        S3 --> S4
        S4 --> S5
    end

    Before -.->|Transition| After

    %% Style definitions
    classDef monolith fill:#95A5A6,stroke:#333,stroke-width:1px,color:white;
    classDef micro fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;

    %% Apply classes
    class M monolith;
    class S1,S2,S3,S4,S5 micro;
```

**新问题**：

| 问题                            | 说明                                         | 影响                           |
| ------------------------------- | -------------------------------------------- | ------------------------------ |
| **服务间通信**                  | 网络调用增加                                 | 延迟、故障传播                 |
| **可观测性**                    | 需要分布式追踪                               | 调试困难                       |
| **安全性**                      | 服务到服务的认证/加密                        | mTLS 实现复杂度                |
| **流量控制**                    | Canary 部署、A/B 测试                        | 需要修改应用代码               |
| **故障处理**                    | Circuit Breaker、Retry                       | 每个服务都需要单独实现         |

#### 早期解决方案：库

**问题**：

* 每种语言都需要开发库（Java 使用 Hystrix，Go 使用单独的库……）
* 与应用代码紧密耦合
* 更新时需要重新部署所有服务
* 版本管理复杂

```mermaid
flowchart LR
    subgraph App1[Java Service]
        J[Application Code]
        H[Hystrix<br/>Netflix OSS]
    end

    subgraph App2[Go Service]
        G[Application Code]
        L[Go Library]
    end

    subgraph App3[Python Service]
        P[Application Code]
        R[Requests + Retry]
    end

    J --- H
    G --- L
    P --- R

    %% Style definitions
    classDef app fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef lib fill:#FF6B6B,stroke:#333,stroke-width:1px,color:white;

    %% Apply classes
    class J,G,P app;
    class H,L,R lib;
```

**Service Mesh 的理念**：将网络逻辑从应用中移至基础设施层

### Envoy Proxy 的诞生

#### Lyft 面临的问题

**2015 年，Lyft** 面临以下问题：

* 运行 200 多个 Microservices
* 使用多种语言和框架（Python、Go、Java 等）
* 现有代理（HAProxy、NGINX）能力不足
  * 难以动态更改配置
  * 缺少可观测性
  * 高级路由功能有限

#### Matt Klein 与 Envoy

**Matt Klein**（Lyft 工程师）于 2016 年将 Envoy 开源。

**Envoy 解决的问题**：

```mermaid
flowchart TB
    subgraph Problems[Existing Proxy Problems]
        P1[Static configuration<br/>File-based]
        P2[Limited<br/>metrics]
        P3[Complex<br/>restart]
        P4[Simple<br/>routing]
    end

    subgraph Solutions[Envoy's Solutions]
        S1[Dynamic API<br/>xDS Protocol]
        S2[Rich<br/>statistics/tracing]
        S3[Hot Restart<br/>Zero downtime]
        S4[Advanced L7<br/>routing]
    end

    P1 -.->|Solved| S1
    P2 -.->|Solved| S2
    P3 -.->|Solved| S3
    P4 -.->|Solved| S4

    %% Style definitions
    classDef problem fill:#FF6B6B,stroke:#333,stroke-width:1px,color:white;
    classDef solution fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;

    %% Apply classes
    class P1,P2,P3,P4 problem;
    class S1,S2,S3,S4 solution;
```

**Envoy 的主要特性**：

1. **进程外架构**：与应用分离的独立进程
2. **xDS APIs**：动态配置更新
3. **L7 Proxy**：支持 HTTP/2、gRPC、WebSocket
4. **可观测性**：详细的 metrics、tracing、logging
5. **性能**：使用 C++ 编写，性能优异

#### CNCF 接纳

**时间线**：

* **2016 年 9 月**：Envoy 开源
* **2017 年 9 月**：被接纳为 CNCF 项目（Incubating）
* **2018 年 11 月**：晋升为 CNCF Graduated 项目

### Istio 的诞生与历史

#### Google、IBM 和 Lyft 的合作

**2017 年 5 月**，Google、IBM 和 Lyft 合作发布 Istio。

```mermaid
flowchart LR
    subgraph Companies[Participating Companies]
        G[Google<br/>Kubernetes experience]
        I[IBM<br/>Enterprise requirements]
        L[Lyft<br/>Envoy Proxy]
    end

    subgraph Istio[Istio Service Mesh]
        CP[Control Plane<br/>Google led]
        DP[Data Plane<br/>Envoy-based]
    end

    G --> CP
    I --> CP
    L --> DP

    %% Style definitions
    classDef company fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef component fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;

    %% Apply classes
    class G,I,L company;
    class CP,DP component;
```

**各公司贡献**：

| 公司       | 主要贡献               | 原因                           |
| ---------- | ---------------------- | ------------------------------ |
| **Google** | Control Plane 设计     | Borg、Kubernetes 经验          |
| **IBM**    | 企业级功能             | 企业客户需求                   |
| **Lyft**   | Envoy Proxy            | 经生产验证的代理               |

#### Istio 版本历史

**主要里程碑**：

```mermaid
timeline
    title Istio Major Version History
    2017-05 : Istio 0.1 announced
    2018-07 : Istio 1.0 : Production ready
    2019-03 : Istio 1.1 : Performance improvements
    2020-03 : Istio 1.5 : Istiod consolidation
    2021-05 : Istio 1.10 : Discovery Selectors
    2022-02 : Istio 1.13 : Gateway API support
    2023-11 : Istio 1.20 : Ambient Mode
    2024-05 : Istio 1.22 : Stability improvements
    2025-01 : Istio 1.28 : Current version
```

**版本 1.5（2020 年 3 月）——重要转折点**：

此前的架构（Istio 1.4 及更早版本）：

```
Separated into individual components:
- Mixer (policy/telemetry)
- Pilot (traffic management)
- Citadel (certificate management)
- Galley (configuration validation)
```

新架构（Istio 1.5+，当前 1.28）：

```
Istiod (consolidated into single binary)
├── Pilot functionality (Service Discovery, Traffic Management)
├── Citadel functionality (Certificate Authority, Identity)
└── Galley functionality (Configuration Validation)

Mixer completely removed (functionality moved to Envoy)
```

**变更原因**：

* 降低复杂度（4 个组件 → 1 个）
* 提升性能（移除 Mixer 后延迟降低 50%）
* 简化运维（单进程管理）
* 提高资源效率（减少 memory、CPU 使用量）

## 为什么选择 Istio？

Kubernetes 提供容器编排能力，但在管理 Microservices 之间的复杂通信方面存在局限。Istio 是用于解决这些问题的 Service Mesh 方案。

### Microservices 面临的挑战

```mermaid
flowchart TB
    subgraph Problems["Microservices Challenges"]
        P1[Traffic Management<br/>Complex routing]
        P2[Security<br/>Inter-service encryption]
        P3[Observability<br/>Difficult debugging]
        P4[Resilience<br/>Failure handling]
    end

    subgraph Without["Without Istio"]
        W1[Direct implementation<br/>in application code]
        W2[Duplicate code<br/>in each service]
        W3[Inconsistent<br/>implementation]
        W4[Difficult<br/>maintenance]
    end

    subgraph With["Using Istio"]
        I1[Automatic handling<br/>at infrastructure level]
        I2[Central management<br/>with declarative config]
        I3[Consistent<br/>policy application]
        I4[Add features<br/>without code changes]
    end

    P1 & P2 & P3 & P4 -->|Traditional approach| W1
    W1 --> W2 --> W3 --> W4

    P1 & P2 & P3 & P4 -->|Istio| I1
    I1 --> I2 --> I3 --> I4

    %% Style definitions
    classDef problem fill:#FF6B6B,stroke:#333,stroke-width:1px,color:white;
    classDef without fill:#95A5A6,stroke:#333,stroke-width:1px,color:white;
    classDef with fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;

    %% Apply classes
    class P1,P2,P3,P4 problem;
    class W1,W2,W3,W4 without;
    class I1,I2,I3,I4 with;
```

### Istio 提供的核心价值

#### 1. 流量管理

**问题**：部署新版本时，希望安全地切换流量。

**Istio 解决方案**：

```yaml
# Canary deployment without code changes
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: reviews
spec:
  hosts:
  - reviews
  http:
  - route:
    - destination:
        host: reviews
        subset: v1
      weight: 90  # Existing version 90%
    - destination:
        host: reviews
        subset: v2
      weight: 10  # New version 10%
```

**优势**：

* 无需修改应用代码
* 实时调整流量分配
* 支持自动回滚
* 支持 A/B 测试、Blue/Green 部署

#### 2. 安全性

**问题**：希望对服务间通信进行加密和认证。

**Istio 解决方案**：

```yaml
# Automatic mTLS enablement
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: default
  namespace: istio-system
spec:
  mtls:
    mode: STRICT  # Automatic encryption for all inter-service communication
```

**优势**：

* 自动签发和轮换证书
* 自动验证服务身份
* 细粒度权限控制
* 实现 Zero Trust 网络

#### 3. 可观测性

**问题**：难以追踪跨越数十个 Microservices 的请求流。

**Istio 解决方案**：

* 自动生成 metrics（Latency、Traffic、Errors、Saturation）
* Distributed Tracing
* Service 拓扑可视化

**优势**：

* 自动识别瓶颈
* 快速定位错误根因
* 实时监控 Service 状态

#### 4. 弹性

**问题**：一个 Service 的故障会传播到整个系统。

**Istio 解决方案**：

```yaml
# Automatic Circuit Breaker configuration
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews
spec:
  host: reviews
  trafficPolicy:
    outlierDetection:
      consecutiveErrors: 5
      interval: 30s
      baseEjectionTime: 30s
```

**优势**：

* 故障隔离（Circuit Breaker）
* 自动 Retry 和 Timeout
* 自动移除不健康实例
* 流量限制（Rate Limiting）

### 何时使用 Istio

**✅ 适合使用 Istio 的场景：**

1. **Microservices 架构**
   * 10 个或更多 Service
   * Service 之间存在复杂依赖关系
   * 频繁部署
2. **需要高级流量管理**
   * Canary 部署、A/B 测试
   * 细粒度路由控制
   * Traffic Mirroring
3. **严格的安全要求**
   * 必须加密服务间通信
   * 细粒度访问控制
   * 合规性要求
4. **可观测性和调试**
   * 追踪复杂的服务间问题
   * 识别性能瓶颈
   * SLO/SLA 监控

**❌ Istio 可能过于复杂的场景：**

1. **简单应用**
   * Service 数量较少（少于 5 个）
   * 需求简单
   * Kubernetes Ingress 已足够
2. **资源受限**
   * 小型 cluster
   * 无法承受资源开销
   * Sidecar memory 成本负担较重
3. **缺乏运维能力**
   * 学习时间不足
   * 没有专门的平台团队
   * 倾向于更简单的解决方案

### 替代方案对比

#### Kubernetes Ingress 与 Istio

| 特性              | Kubernetes Ingress | Istio                             |
| ----------------- | ------------------ | --------------------------------- |
| **范围**          | 外部 → Cluster     | 外部 + 内部服务间                 |
| **路由**          | 基础（Path、Host） | 高级（Header、Cookie 等）         |
| **mTLS**          | 手动配置           | 自动                              |
| **可观测性**      | 有限               | 丰富                              |
| **复杂度**        | 低                 | 高                                |
| **适用场景**      | 简单应用           | Microservices                     |

#### AWS VPC Lattice 与 Istio

有关详细对比，请参阅 [AWS Integration](04-aws-integration.md#istio-vs-other-solutions-comparison) 文档。

**快速摘要：**

* **VPC Lattice**：AWS 托管、简单、支持跨 VPC/account 通信
* **Istio**：开源、功能强大、仅限 Kubernetes、细粒度控制

#### Linkerd 与 Istio

| 属性               | Istio     | Linkerd            |
| ------------------ | --------- | ------------------ |
| **复杂度**         | 高        | 低                 |
| **功能**           | 非常丰富  | 仅核心功能         |
| **资源**           | 高        | 低                 |
| **学习曲线**       | 陡峭     | 平缓               |
| **社区**           | 大        | 小                 |

**选择指南：**

* 需要高级功能和灵活性 → **Istio**
* 需要简单轻量的 mesh → **Linkerd**

## 部署模式：Sidecar 与 Ambient

Istio 支持两种部署模式：**Sidecar Mode** 和 **Ambient Mode**。

### Sidecar Mode（默认）

将 Envoy Proxy 作为 Sidecar container 注入到每个应用 Pod 中。

```mermaid
flowchart LR
    subgraph Pod["Pod"]
        App[Application<br/>Container]
        Envoy[Envoy Proxy<br/>Sidecar]
    end

    External[External Request] -->|Traffic| Envoy
    Envoy -->|Local| App
    App -->|Outbound call| Envoy
    Envoy -->|Network| Target[Target Service]

    %% Style definitions
    classDef app fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef proxy fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;

    %% Apply classes
    class App app;
    class Envoy proxy;
    class External,Target default;
```

**优势：**

* 成熟稳定
* 支持所有 Istio 功能
* 可按 Pod 进行细粒度控制

**劣势：**

* 资源开销（每个 Pod 一个 Envoy）
* 启动时间增加（Init Container）
* 权限设置复杂（iptables）

### Ambient Mode（新方法）

无需 Sidecar，而是在 node 层处理流量。

```mermaid
flowchart TB
    subgraph Node["Worker Node"]
        subgraph Pod1["Pod 1"]
            App1[Application<br/>No sidecar]
        end

        subgraph Pod2["Pod 2"]
            App2[Application<br/>No sidecar]
        end

        Ztunnel[ztunnel<br/>1 per node<br/>L4 proxy]
        Waypoint[Waypoint Proxy<br/>L7 proxy<br/>Optional]
    end

    App1 <-->|Transparent redirect| Ztunnel
    App2 <-->|Transparent redirect| Ztunnel
    Ztunnel <-->|When L7 needed| Waypoint

    %% Style definitions
    classDef userApp fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef proxy fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;

    %% Apply classes
    class App1,App2 userApp;
    class Ztunnel,Waypoint proxy;
```

**优势：**

* 资源使用量低（每个 node 一个）
* Pod 启动快速
* 运维简单
* 可逐步应用 L7 功能

**劣势：**

* 技术相对较新（成熟度较低）
* 部分高级功能受限
* 难以按 Pod 进行细粒度控制

### 对比表

| 属性                       | Sidecar Mode                | Ambient Mode                   |
| -------------------------- | --------------------------- | ------------------------------ |
| **资源使用量**             | 高（每个 Pod）              | 低（每个 node）                |
| **启动时间**               | 慢（Init Container）        | 快                             |
| **运维复杂度**             | 高                          | 低                             |
| **L4 功能**                | 支持                        | 支持                           |
| **L7 功能**                | 完全支持                    | 可选（Waypoint）               |
| **成熟度**                 | 高                          | 中                             |
| **迁移**                   | -                           | 可从现有 Sidecar 迁移          |
| **推荐用途**               | 需要高级 L7 功能            | 优先考虑资源效率               |

### 选择指南

**选择 Sidecar Mode：**

* 需要使用所有 Istio 功能
* 需要按 Pod 进行细粒度策略控制
* 需要经生产验证的稳定性

**选择 Ambient Mode：**

* 资源效率很重要
* 仅需要简单的 L4 功能
* 计划逐步添加 L7 功能

**有关详情**，请参阅 [Advanced: Ambient Mode](advanced/01-ambient-mode.md) 文档。

## Istio 架构

Istio 由两个主要组件构成：**Control Plane** 和 **Data Plane**。

| 组件                         | 说明                                                                                                         |
| ---------------------------- | ------------------------------------------------------------------------------------------------------------ |
| **Control Plane (istiod)**   | 负责 Service Discovery、配置分发和证书管理的中央控制系统                                                    |
| **Data Plane (Envoy Proxy)** | 以 Sidecar 形式部署在每个 Pod 中，处理实际流量（路由、mTLS、metrics）                                        |

**有关详细的架构结构、内部运行原理和流量拦截机制**，请参阅 [Architecture 文档](03-architecture.md)。

## 核心资源

Istio 使用 Kubernetes Custom Resource Definitions（CRDs）管理配置。

### 1. VirtualService

VirtualService 定义请求如何路由到 Service。

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: reviews-route
spec:
  hosts:
  - reviews  # Target service
  http:
  - match:
    - headers:
        end-user:
          exact: jason
    route:
    - destination:
        host: reviews
        subset: v2  # Route specific user to v2
  - route:
    - destination:
        host: reviews
        subset: v1  # Route to v1 by default
```

**主要特性**：

* 基于路径的路由（Path、Header、Query Parameter）
* 流量拆分（Canary、A/B 测试）
* Retry、Timeout、Fault Injection
* URL Rewrite、Header 操作

### 2. DestinationRule

DestinationRule 定义 Service subset（版本）并应用流量策略。

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews-destination
spec:
  host: reviews
  trafficPolicy:
    loadBalancer:
      simple: LEAST_REQUEST  # Load balancing algorithm
    connectionPool:
      tcp:
        maxConnections: 100
      http:
        http1MaxPendingRequests: 50
        maxRequestsPerConnection: 2
    outlierDetection:
      consecutiveErrors: 5
      interval: 30s
      baseEjectionTime: 30s
  subsets:
  - name: v1
    labels:
      version: v1
  - name: v2
    labels:
      version: v2
  - name: v3
    labels:
      version: v3
```

**主要特性**：

* Service 版本（subset）定义
* Load balancing 算法
* Connection Pool 设置
* Circuit Breaker（Outlier Detection）
* TLS 设置

### 3. Gateway

Gateway 管理进入 mesh 的外部流量。

```yaml
apiVersion: networking.istio.io/v1
kind: Gateway
metadata:
  name: bookinfo-gateway
spec:
  selector:
    istio: ingressgateway  # Select Ingress Gateway pod
  servers:
  - port:
      number: 80
      name: http
      protocol: HTTP
    hosts:
    - "bookinfo.example.com"
  - port:
      number: 443
      name: https
      protocol: HTTPS
    tls:
      mode: SIMPLE
      credentialName: bookinfo-credential  # TLS certificate
    hosts:
    - "bookinfo.example.com"
```

**主要特性**：

* 定义外部流量入口点
* Host、port、protocol 设置
* TLS termination
* SNI 路由

### 4. ServiceEntry

ServiceEntry 使 mesh 外的外部 Service 能够像内部 Service 一样使用。

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

**主要特性**：

* 外部 Service 注册
* 外部 Service 的流量控制
* Egress 流量管理

### 5. PeerAuthentication

PeerAuthentication 定义 Service 之间的认证策略。

```yaml
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: default
  namespace: default
spec:
  mtls:
    mode: STRICT  # STRICT, PERMISSIVE, DISABLE
```

### 6. AuthorizationPolicy

AuthorizationPolicy 定义 Service 访问权限。

```yaml
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: allow-ratings
  namespace: default
spec:
  selector:
    matchLabels:
      app: ratings
  action: ALLOW
  rules:
  - from:
    - source:
        principals: ["cluster.local/ns/default/sa/reviews"]
    to:
    - operation:
        methods: ["GET"]
```

## 流量管理概念

### 流量路由流程

```mermaid
flowchart LR
    Client[Client] -->|1. HTTP Request| Gateway[Gateway<br/>Ingress]
    Gateway -->|2. VirtualService<br/>Apply routing rules| VS[VirtualService]
    VS -->|3. Determine destination| DR[DestinationRule]
    DR -->|4. Select subset<br/>Apply traffic policy| Service[Kubernetes<br/>Service]
    Service -->|5. Endpoint<br/>routing| Pod1[Pod v1]
    Service -->|5. Endpoint<br/>routing| Pod2[Pod v2]

    %% Style definitions
    classDef gateway fill:#FF9900,stroke:#333,stroke-width:1px,color:black;
    classDef istioResource fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef k8sResource fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;

    %% Apply classes
    class Gateway gateway;
    class VS,DR istioResource;
    class Service,Pod1,Pod2 k8sResource;
    class Client default;
```

### 流量拆分（Canary 部署）

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: reviews-canary
spec:
  hosts:
  - reviews
  http:
  - route:
    - destination:
        host: reviews
        subset: v1
      weight: 90  # 90% of traffic
    - destination:
        host: reviews
        subset: v2
      weight: 10  # 10% of traffic (canary)
```

### Circuit Breaker

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews-circuit-breaker
spec:
  host: reviews
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 100
      http:
        http1MaxPendingRequests: 10
        maxRequestsPerConnection: 2
    outlierDetection:
      consecutiveErrors: 5
      interval: 30s
      baseEjectionTime: 30s
      maxEjectionPercent: 50
```

## 安全概念

### mTLS（Mutual TLS）

Istio 会自动加密服务间通信。

```mermaid
flowchart LR
    subgraph Pod1["Pod A"]
        App1[App]
        Envoy1[Envoy]
    end

    subgraph Pod2["Pod B"]
        Envoy2[Envoy]
        App2[App]
    end

    App1 -->|Plaintext| Envoy1
    Envoy1 <-->|mTLS Encrypted| Envoy2
    Envoy2 -->|Plaintext| App2

    Citadel[istiod<br/>Citadel] -.->|Certificate issuance| Envoy1
    Citadel -.->|Certificate issuance| Envoy2

    %% Style definitions
    classDef app fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef proxy fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;
    classDef controlPlane fill:#FF9900,stroke:#333,stroke-width:1px,color:black;

    %% Apply classes
    class App1,App2 app;
    class Envoy1,Envoy2 proxy;
    class Citadel controlPlane;
```

**mTLS 模式**：

* **STRICT**：仅允许 mTLS
* **PERMISSIVE**：同时允许 mTLS 和明文（用于迁移）
* **DISABLE**：禁用 mTLS

### Authentication 与 Authorization

```yaml
# JWT Authentication
apiVersion: security.istio.io/v1
kind: RequestAuthentication
metadata:
  name: jwt-auth
spec:
  jwtRules:
  - issuer: "https://accounts.google.com"
    jwksUri: "https://www.googleapis.com/oauth2/v3/certs"
---
# Authorization Policy
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: require-jwt
spec:
  action: DENY
  rules:
  - from:
    - source:
        notRequestPrincipals: ["*"]
```

## 可观测性概念

Istio 自动生成 metrics、logs 和 traces。

### 自动生成的 Metrics

```mermaid
flowchart TB
    subgraph Pod["Pod"]
        App[Application]
        Envoy[Envoy Proxy]
    end

    App <-->|Traffic| Envoy

    Envoy -->|Metrics| Prometheus[Prometheus<br/>Metric Collection]
    Envoy -->|Traces| Jaeger[Jaeger<br/>Distributed Tracing]
    Envoy -->|Logs| Logging[Logging System]

    Prometheus -->|Visualization| Grafana[Grafana<br/>Dashboard]
    Jaeger -->|Analysis| JaegerUI[Jaeger UI]

    Kiali[Kiali<br/>Service Mesh Dashboard] -->|Query| Prometheus

    %% Style definitions
    classDef app fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef proxy fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;
    classDef monitoring fill:#E6522C,stroke:#333,stroke-width:1px,color:white;
    classDef visualization fill:#F8B52A,stroke:#333,stroke-width:1px,color:black;
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;

    %% Apply classes
    class App app;
    class Envoy proxy;
    class Prometheus,Jaeger,Logging monitoring;
    class Grafana,JaegerUI,Kiali visualization;
```

### 关键 Metrics

| Metric                                | 说明                 |
| ------------------------------------- | -------------------- |
| `istio_requests_total`                | 请求总数             |
| `istio_request_duration_milliseconds` | 请求延迟             |
| `istio_request_bytes`                 | 请求大小             |
| `istio_response_bytes`                | 响应大小             |
| `istio_tcp_connections_opened_total`  | TCP 连接数           |

### Distributed Tracing

```yaml
# Enable tracing in Envoy
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  meshConfig:
    enableTracing: true
    defaultConfig:
      tracing:
        sampling: 100.0  # 100% sampling
        zipkin:
          address: jaeger-collector.istio-system:9411
```

## Namespace 与 Service Mesh

### Namespace 隔离

```yaml
# Per-namespace mTLS policy
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: default
  namespace: production
spec:
  mtls:
    mode: STRICT
---
# Per-namespace authorization policy
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: deny-all
  namespace: production
spec:
  action: DENY
  rules:
  - {}
```

### Service Mesh 范围

```bash
# Include only specific namespaces in the mesh
kubectl label namespace default istio-injection=enabled
kubectl label namespace staging istio-injection=enabled

# Exclude specific namespace
kubectl label namespace kube-system istio-injection=disabled
```

### Multi-tenancy

```yaml
# Restrict mesh scope with Sidecar resource
apiVersion: networking.istio.io/v1
kind: Sidecar
metadata:
  name: default
  namespace: production
spec:
  egress:
  - hosts:
    - "production/*"  # Only production namespace accessible
    - "istio-system/*"
```

## VM Workload 注册

Istio 不仅可以在 Service Mesh 中注册 Kubernetes Pod，还可以注册 **Virtual Machine（VM）Workload**。这使 legacy application 或 cluster 外的 Service 能够使用 Istio 的流量管理、安全和可观测性功能。

### 为什么需要 VM Workload

```mermaid
flowchart TB
    subgraph Legacy[Legacy Environment]
        VM1[VM<br/>Legacy App]
        VM2[VM<br/>Database]
        VM3[VM<br/>External Service]
    end

    subgraph K8S[Kubernetes Cluster]
        subgraph Pod1[Pod]
            App1[New App]
            Envoy1[Envoy]
        end

        subgraph Pod2[Pod]
            App2[Microservice]
            Envoy2[Envoy]
        end
    end

    subgraph Istiod[Control Plane]
        CP[istiod]
    end

    VM1 -->|Before migration<br/>Direct communication| App1
    App1 -.->|After mesh registration<br/>mTLS, policy applied| VM1

    CP -.->|Configuration delivery| Envoy1
    CP -.->|Configuration delivery| Envoy2
    CP -.->|VM can also be registered| VM1

    %% Style definitions
    classDef vm fill:#95A5A6,stroke:#333,stroke-width:1px,color:white;
    classDef k8sApp fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef proxy fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;
    classDef controlPlane fill:#FF9900,stroke:#333,stroke-width:1px,color:black;

    %% Apply classes
    class VM1,VM2,VM3 vm;
    class App1,App2 k8sApp;
    class Envoy1,Envoy2 proxy;
    class CP controlPlane;
```

**使用场景**：

* 逐步迁移 legacy application
* 将 database server 纳入 mesh
* 集成 cluster 外的 Service
* 配置 hybrid cloud 环境

### VM 注册架构

```mermaid
flowchart LR
    subgraph VM[Virtual Machine]
        LegacyApp[Legacy<br/>Application]
        EnvoyVM[Envoy<br/>Sidecar]
    end

    subgraph K8S[Kubernetes Cluster]
        subgraph Pod[Pod]
            App[Application]
            EnvoyPod[Envoy<br/>Sidecar]
        end

        Istiod[istiod<br/>Control Plane]
    end

    LegacyApp <-->|Local communication| EnvoyVM
    App <-->|Local communication| EnvoyPod

    EnvoyVM <-->|mTLS| EnvoyPod

    Istiod -.->|xDS configuration| EnvoyVM
    Istiod -.->|xDS configuration| EnvoyPod
    Istiod -.->|Certificate issuance| EnvoyVM

    %% Style definitions
    classDef vmApp fill:#95A5A6,stroke:#333,stroke-width:1px,color:white;
    classDef k8sApp fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef proxy fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;
    classDef controlPlane fill:#FF9900,stroke:#333,stroke-width:1px,color:black;

    %% Apply classes
    class LegacyApp vmApp;
    class App k8sApp;
    class EnvoyVM,EnvoyPod proxy;
    class Istiod controlPlane;
```

### WorkloadEntry 资源

VM Workload 使用 **WorkloadEntry** 资源进行注册。

```yaml
apiVersion: networking.istio.io/v1
kind: WorkloadEntry
metadata:
  name: legacy-database
  namespace: default
spec:
  address: 192.168.1.100  # VM IP address
  labels:
    app: mysql
    version: v5.7
  serviceAccount: database-sa
  ports:
    mysql: 3306
```

**WorkloadEntry 关键字段**：

* `address`：VM IP 地址
* `labels`：与 Service selector 匹配
* `serviceAccount`：用于 mTLS authentication 的 Service account
* `ports`：暴露的 port 定义

### 与 ServiceEntry 集成

WorkloadEntry 与 ServiceEntry 一起使用，将 VM Service 注册到 mesh 中。

```yaml
# Define service with ServiceEntry
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: legacy-database
spec:
  hosts:
  - database.legacy.com
  ports:
  - number: 3306
    name: mysql
    protocol: TCP
  location: MESH_INTERNAL  # Register as internal mesh service
  resolution: STATIC
  workloadSelector:
    labels:
      app: mysql
---
# Register VM instance with WorkloadEntry
apiVersion: networking.istio.io/v1
kind: WorkloadEntry
metadata:
  name: mysql-vm-1
  namespace: default
spec:
  address: 192.168.1.100
  labels:
    app: mysql
    version: v5.7
  serviceAccount: mysql-sa
```

### VM 注册与 Multi-Cluster 对比

| 特性                       | VM Workload 注册           | Multi-Cluster                  | Kubernetes Pod      |
| -------------------------- | -------------------------- | ------------------------------ | ------------------- |
| **Workload 位置**          | cluster 外的 VM            | 不同的 Kubernetes cluster      | cluster 内          |
| **Envoy 安装**             | 手动安装                   | 自动（Sidecar）                | 自动（Sidecar）     |
| **注册方式**               | WorkloadEntry              | ServiceEntry + EndpointSlice   | Service + Pod       |
| **mTLS**                   | 支持                       | 支持                           | 支持                |
| **Service Discovery**      | 手动（指定 IP）            | 自动                           | 自动                |
| **使用场景**               | Legacy app、DB             | Multi-cloud、disaster recovery | Cloud-native app    |
| **运维复杂度**             | 高                         | 中                             | 低                  |

### VM 注册的优势

#### 1. 逐步迁移

```mermaid
flowchart LR
    subgraph Phase1[Phase 1: Legacy Environment]
        VM1[VM<br/>Monolith App]
    end

    subgraph Phase2[Phase 2: VM Mesh Registration]
        VM2[VM<br/>Monolith App<br/>+ Envoy]
    end

    subgraph Phase3[Phase 3: Hybrid]
        VM3[VM<br/>Legacy Module]
        K8S1[K8s<br/>New Microservices]
        VM3 <-->|mTLS| K8S1
    end

    subgraph Phase4[Phase 4: Complete Migration]
        K8S2[K8s<br/>All Microservices]
    end

    Phase1 -->|VM registration| Phase2
    Phase2 -->|Partial migration| Phase3
    Phase3 -->|Complete| Phase4

    %% Style definitions
    classDef vm fill:#95A5A6,stroke:#333,stroke-width:1px,color:white;
    classDef k8s fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;

    %% Apply classes
    class VM1,VM2,VM3 vm;
    class K8S1,K8S2 k8s;
```

**优势**：

* 无需修改即可将现有 VM application 集成到 mesh
* 分阶段迁移到 Kubernetes
* 在迁移期间保持一致的安全性和可观测性

#### 2. 统一安全策略

```yaml
# mTLS policy applied to both VMs and pods
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: default
  namespace: default
spec:
  mtls:
    mode: STRICT  # Enforce mTLS for both VMs and pods
---
# VM database access control
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: database-access
  namespace: default
spec:
  selector:
    matchLabels:
      app: mysql  # WorkloadEntry label
  action: ALLOW
  rules:
  - from:
    - source:
        principals: ["cluster.local/ns/default/sa/app-sa"]
    to:
    - operation:
        methods: ["*"]
```

#### 3. 一致的可观测性

VM Workload 提供与 Kubernetes Pod 相同的 metrics、logs 和 distributed tracing。

```promql
# Unified metric query for VMs and pods
sum(rate(istio_requests_total{destination_workload="mysql-vm-1"}[5m]))

# Error rate from VM
sum(rate(istio_requests_total{destination_workload="mysql-vm-1",response_code="500"}[5m]))
/
sum(rate(istio_requests_total{destination_workload="mysql-vm-1"}[5m]))
```

### VM 注册的限制

1. **手动安装 Envoy**：必须在 VM 上手动安装和配置 Envoy Proxy
2. **网络连通性**：VM 与 Kubernetes cluster 之间需要网络连接
3. **证书管理**：必须将 Service account certificate 部署到 VM
4. **运维负担**：需要管理和更新 VM Envoy 版本
5. **自动扩缩容限制**：没有 Kubernetes HPA 那样的自动扩缩容能力

### 实际使用示例

#### 场景：Legacy Database 集成

```yaml
# 1. Define database service with ServiceEntry
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: legacy-postgres
  namespace: production
spec:
  hosts:
  - postgres.production.svc.cluster.local
  addresses:
  - 240.240.1.10  # Virtual IP
  ports:
  - number: 5432
    name: postgresql
    protocol: TCP
  location: MESH_INTERNAL
  resolution: STATIC
  workloadSelector:
    labels:
      app: postgres
      tier: database
---
# 2. Register VM instance with WorkloadEntry
apiVersion: networking.istio.io/v1
kind: WorkloadEntry
metadata:
  name: postgres-vm-1
  namespace: production
spec:
  address: 10.0.1.100  # Actual VM IP
  labels:
    app: postgres
    tier: database
    version: v13
  serviceAccount: postgres-sa
  ports:
    postgresql: 5432
---
# 3. Access control policy
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: postgres-access-control
  namespace: production
spec:
  selector:
    matchLabels:
      app: postgres
  action: ALLOW
  rules:
  - from:
    - source:
        namespaces: ["production"]
        principals: ["cluster.local/ns/production/sa/api-service"]
    to:
    - operation:
        ports: ["5432"]
```

**结果**：

* Kubernetes Pod 通过 `postgres.production.svc.cluster.local` 访问 database
* VM 与 Pod 之间自动进行 mTLS 加密
* 应用访问控制策略
* 自动收集 metrics 和 distributed tracing

### Workload 注册对比摘要

```mermaid
flowchart TB
    subgraph Types[Workload Types]
        K8S[Kubernetes Pod<br/>Inside cluster]
        MC[Multi-Cluster<br/>Different cluster]
        VM[Virtual Machine<br/>Outside cluster]
    end

    subgraph Features[Common Features]
        mTLS[mTLS Encryption]
        Traffic[Traffic Management]
        Policy[Security Policy]
        Metrics[Metrics & Tracing]
    end

    K8S & MC & VM --> mTLS
    K8S & MC & VM --> Traffic
    K8S & MC & VM --> Policy
    K8S & MC & VM --> Metrics

    %% Style definitions
    classDef workload fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef feature fill:#326CE5,stroke:#333,stroke-width:1px,color:white;

    %% Apply classes
    class K8S,MC,VM workload;
    class mTLS,Traffic,Policy,Metrics feature;
```

通过 Istio 灵活的 Workload 注册能力：

* **Kubernetes Pod**：Cloud-native application
* **Multi-Cluster**：Multi-cloud、区域分布、disaster recovery
* **Virtual Machine**：Legacy app、database、hybrid 环境

所有 Workload 都能获得一致的安全性、流量管理和可观测性功能。

## 后续步骤

现在你已经了解 Istio 的基本概念。请通过以下文档学习如何在实践中使用它们：

### 核心功能

1. [**Traffic Management**](traffic-management/)
   * Gateway 和 VirtualService 的用法
   * DestinationRule 和 subset 定义
   * ServiceEntry 和 WorkloadEntry（VM 注册）
   * 高级路由模式（Canary、A/B 测试）
   * Traffic Mirroring 和 Shadowing
2. [**Security**](security/)
   * mTLS 配置和 PeerAuthentication
   * Authentication（RequestAuthentication、JWT）
   * Authorization（AuthorizationPolicy）
   * Security policy 管理
   * 外部 Authentication 集成
3. [**Observability**](/broken/pages/HT0uW6gT7EfVN0LF8wU5)
   * Metric 收集（Prometheus）
   * Distributed tracing（Jaeger、Zipkin）
   * Logging 配置
   * Kiali Service Mesh 可视化
   * Grafana dashboards
4. [**Resilience**](resilience/)
   * Circuit Breaker 模式
   * Retry 和 Timeout 设置
   * Rate Limiting
   * Outlier Detection
   * Fault Injection 测试

### 高级主题

5. [**Advanced Topics**](advanced/)
   * Ambient Mode（无 Sidecar 的 mesh）
   * Multi-Cluster 配置
   * EnvoyFilter 自定义
   * DNS Proxy 和 Caching
   * VM Workload 详细配置
   * WASM plugin 开发

## 参考资料

* [Istio Official Documentation - Concepts](https://istio.io/latest/docs/concepts/)
* [Istio Official Documentation - Traffic Management](https://istio.io/latest/docs/concepts/traffic-management/)
* [Istio Official Documentation - Security](https://istio.io/latest/docs/concepts/security/)
* [Istio Official Documentation - Observability](https://istio.io/latest/docs/concepts/observability/)
* [Envoy Proxy Official Documentation](https://www.envoyproxy.io/docs/envoy/latest/)
