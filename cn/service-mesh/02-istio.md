# Istio

> **最后更新**：2026 年 9 月 11 日 · Istio 1.31 指南

本概述让原章节 URL 继续可用。详细流程和兼容性矩阵由持续维护的 [Istio 文档索引](istio/README.md)及[安装指南](istio/01-installation.md)提供；当前设置请使用这些指南。

## 目录

- [简介](#introduction)
- [主要功能](#key-features)
- [架构概述](#architecture-overview)
- [详细文档](#detailed-documentation)
- [快速入门](#quick-start)
- [学习资源](#learning-resources)

## 简介 {#introduction}

Istio 是面向微服务应用的开源服务网格平台。服务网格是处理服务间通信的基础设施层，允许在基础设施层控制和观察服务通信。应用追踪上下文传播、优雅关闭和业务幂等性仍需要应用参与。

### 什么是服务网格？

服务网格提供以下核心能力：

1. **流量管理**：控制服务间流量
2. **安全**：服务间通信加密和身份验证
3. **可观测性**：了解服务间通信

### Istio 的主要优势

- **平台独立性**：适用于 Kubernetes、虚拟机等多种环境
- **透明集成**：许多网络控制可在不更改应用业务逻辑的情况下添加
- **工作负载 mTLS**：为已纳管网格路径提供托管身份和传输保护；验证执行情况和例外
- **高级流量管理**：路由、负载均衡、故障注入等
- **详细指标**：服务间通信的详细指标
- **策略执行**：访问控制及显式配置的本地/全局限速

## 主要功能 {#key-features}

### 1. 流量管理

Istio 提供强大的流量管理能力：

- **网关**：路由外部流量；区分 Istio Gateway 资源与 Kubernetes Gateway API
- **VirtualService / HTTPRoute**：使用所选数据平面和控制器支持的 API 配置路由
- **DestinationRule**：配置负载均衡和连接池
- **流量拆分**：支持金丝雀部署和 A/B 测试
- **Argo Rollouts 集成**：渐进式交付，分析和失败处理单独配置

### 2. 安全

全面的安全功能：

- **mTLS**：已纳管工作负载传输的身份验证和加密
- **授权策略**：细粒度访问控制
- **请求身份验证**：JWT 验证；必须存在 JWT 时使用 AuthorizationPolicy
- **对等身份验证**：入站工作负载 mTLS 策略

### 3. 可观测性

针对所选模式配置的遥测和后端集成：

- **指标**：Prometheus 集成
- **分布式追踪**：配置的追踪提供程序/后端，如 OpenTelemetry 配合 Jaeger；应用传播上下文
- **日志**：访问日志和结构化日志
- **可视化**：Kiali 仪表板

### 4. 韧性

服务韧性模式：

- **断路器**：连接/请求池限制；不保证防止过载
- **重试**：为可安全重试操作设置明确预算；禁用结果不明的写入重试
- **超时**：请求超时配置
- **异常检测**：排除不健康实例
- **限速**：配置本地令牌桶或全局限速服务

## 架构概述 {#architecture-overview}

Istio 由**控制平面**和**数据平面**组成。下图展示 Sidecar 形式，不是 Ambient 拓扑。

![控制平面的 Istiod 向三个数据平面 Pod 中与应用容器并行运行的 Envoy Sidecar 代理下发配置，这些代理彼此直接建立双向 TLS 连接。](../.gitbook/assets/en-service-mesh-02-istio-0.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-02-istio-0.html)

### 控制平面（istiod）

istiod 是 Istio 的中央控制组件，提供：

- **服务发现**：维护网格服务注册表
- **配置管理**：监视、转换配置并分发代理设置；Kubernetes 持久化 API 资源
- **证书管理**：与配置的 CA 配合管理工作负载证书请求和轮换

### 数据平面：Sidecar 和 Ambient

Sidecar 模式中，Envoy 与每个已纳管应用 Pod 并行运行：

- **流量路由**：控制服务间流量
- **负载均衡**：在服务实例间分配流量
- **安全**：mTLS 加密和身份验证
- **可观测性**：采集指标、日志和追踪

Ambient 使用节点级 ztunnel 提供 L4 传输，并使用可选 Envoy waypoint 提供受支持 L7 功能。它不向每个应用 Pod 注入 Envoy。功能支持、策略附加和资源用量因模式而异；不能从此拓扑得出固定资源节省百分比或普遍性能优势。参阅 [Ambient 模式](istio/advanced/01-ambient-mode.md)。

## 详细文档 {#detailed-documentation}

以下链接是通往持续维护子目录的学习地图。其索引包含额外及新增主题。

### 📚 基础文档

| 文档 | 描述 |
|----------|-------------|
| [安装指南](istio/01-installation.md) | Istio 安装和初始设置 |
| [核心概念](istio/02-basic-concepts.md) | Istio 基本概念和术语 |
| [组件](istio/03-architecture.md) | Istio 架构和组件 |

### 🚦 流量管理

| 文档 | 描述 |
|----------|-------------|
| [Gateway 和 VirtualService](istio/traffic-management/01-gateway-virtualservice.md) | 入口/出口网关配置 |
| [路由](istio/traffic-management/02-routing.md) | VirtualService 路由规则 |
| [DestinationRule](istio/traffic-management/03-destination-rule.md) | 服务流量策略 |
| [流量拆分](istio/traffic-management/04-traffic-splitting.md) | 金丝雀部署和 A/B 测试 |
| [超时和重试](istio/traffic-management/05-retry-timeout.md) | 超时和重试策略 |
| [负载均衡](istio/traffic-management/06-load-balancing.md) | 多种负载均衡策略 |
| [断路器](istio/traffic-management/07-circuit-breaker.md) | 断路器模式实现 |
| [故障注入](istio/traffic-management/08-fault-injection.md) | 混沌工程 |
| [流量镜像](istio/traffic-management/09-traffic-mirror.md) | 流量镜像和影子测试 |
| [会话亲和性](istio/traffic-management/10-session-affinity.md) | 会话亲和性配置 |

### 🔐 安全

| 文档 | 描述 |
|----------|-------------|
| [mTLS](istio/security/01-mtls.md) | 服务间 mTLS 配置 |
| [授权策略](istio/security/03-authorization.md) | 访问控制策略 |
| [请求身份验证](istio/security/02-authentication.md) | 基于 JWT 的身份验证 |
| [对等身份验证](istio/security/01-mtls.md) | 服务间身份验证 |

### 📊 可观测性

| 文档 | 描述 |
|----------|-------------|
| [指标](istio/observability/01-metrics.md) | Prometheus 指标采集 |
| [分布式追踪](istio/observability/02-tracing.md) | Jaeger/Zipkin 集成 |
| [日志](istio/observability/03-logging.md) | 访问日志和结构化日志 |
| [可视化](istio/observability/04-dashboards.md) | Kiali、Grafana 仪表板 |

### 💪 韧性

| 文档 | 描述 |
|----------|-------------|
| [异常检测](istio/resilience/01-outlier-detection.md) | 不健康实例检测 |
| [限速](istio/resilience/02-rate-limiting.md) | 本地和全局限速 |
| [可用区感知路由](istio/resilience/03-zone-aware-routing.md) | 局部性感知路由 |

### 🚀 高级主题

| 文档 | 描述 |
|----------|-------------|
| [Ambient 模式](istio/advanced/01-ambient-mode.md) | 无 Sidecar 服务网格 |
| [多集群](istio/advanced/02-multi-cluster.md) | 多集群网格配置 |
| [EnvoyFilter](istio/advanced/03-envoy-filter.md) | Envoy 自定义 |
| [DNS 捕获和缓存](istio/advanced/04-dns-cache.md) | DNS 捕获、解析和实测缓存行为 |
| [gRPC](istio/advanced/05-grpc.md) | gRPC 协议支持 |
| [WebSocket](istio/advanced/06-websocket.md) | WebSocket 连接支持 |
| [Sidecar 注入](istio/advanced/07-sidecar-injection.md) | Sidecar 注入机制 |
| [Argo Rollouts](istio/advanced/08-argo-rollouts.md) | 渐进式交付集成 |

### ✅ 最佳实践

| 文档 | 描述 |
|----------|-------------|
| [最佳实践](istio/best-practices.md) | 生产检查清单和建议 |

## 快速入门 {#quick-start}

1. 在[安装指南](istio/01-installation.md)检查确切 Istio/Kubernetes/EKS 兼容性交集。通用“Kubernetes 1.28+”前提不足以支持当前 Istio 发布版本。
2. 选择 Sidecar 或 Ambient，并遵循指南中的固定 CLI/chart、隔离命名空间和平台前提条件。不要下载未指定版本的最新 CLI 后，再进入旧版本目录。
3. 使用持续维护指南中匹配版本的 Bookinfo 流程和网关说明。默认配置档不自动提供入口网关 Deployment，仅 Gateway 配置对象也不会创建每种安装所需的全部网关/LoadBalancer。
4. 验证实际网关地址、Service 端口、路由状态和 HTTP 响应。负载均衡器可能发布 IP 或主机名；不要假定仅 AWS 适用的 hostname 字段或某个端口名称。
5. 使用仪表板命令前，安装/配置所选[可观测性后端](istio/observability/README.md)。默认 Istio 配置档不会自动安装 Prometheus、Grafana、Kiali 和追踪存储。

完成该流程后的基本验证：

```bash
istioctl version
istioctl analyze -A
istioctl proxy-status
```

代理状态只是诊断输入之一。Ambient 纳管和 ztunnel 需要自己的检查，分析器结果无问题也不是端到端流量测试。

## 学习资源 {#learning-resources}

### 官方文档

- [Istio 官方文档](https://istio.io/latest/docs/)
- [Istio GitHub 仓库](https://github.com/istio/istio)
- [Envoy 代理文档](https://www.envoyproxy.io/docs/envoy/latest/)

### AWS 和社区

- [Amazon EKS 上的 Istio](https://istio.io/latest/docs/setup/platform-setup/amazon-eks/)
- [持续维护的 AWS 集成指南](istio/04-aws-integration.md)
- [AWS App Mesh 生命周期通知](https://docs.aws.amazon.com/app-mesh/latest/userguide/what-is-app-mesh.html)：AWS 声明支持于 2026 年 9 月 30 日结束。评估迁移要求；这不是全新部署建议。
- [Istio 社区、频道和工作组](https://istio.io/latest/get-involved/)

### 其他资源

- [服务网格模式（O'Reilly）](https://www.oreilly.com/library/view/service-mesh-patterns/9781492086444/)
- [Istio 实战（Manning）](https://www.manning.com/books/istio-in-action)
- [Istio 性能优化指南](https://istio.io/latest/docs/ops/deployment/performance-and-scalability/)

## 测验

要测试对 Istio 的理解，请尝试 [Istio 测验](../quizzes/service-mesh/02-istio-quiz.md)。

测验涵盖以下主题：

- 服务网格基本概念
- Istio 架构
- 流量管理（金丝雀部署）
- 安全（mTLS）
- Gateway 和 Ingress
- 可观测性工具
- Sidecar 和 Ambient 模式
- 限速
- 局部性路由
- Amazon EKS 集成

---

**后续步骤**：参阅[安装指南](istio/01-installation.md)安装 Istio，并在[核心概念](istio/02-basic-concepts.md)学习基础概念。
