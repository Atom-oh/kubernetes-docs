# Istio

> **最后更新**: October 12, 2026

在 Amazon EKS 上使用 Istio Service Mesh 的实用指南。

### 2026 年 10 月审查：受支持的版本

Istio 1.31.0 已正式发布（GA）；其[发布公告](https://istio.io/latest/news/releases/1.31.x/announcing-1.31/)于 2026 年 8 月 31 日发布。当前补丁版本是 **1.31.1**，于 9 月 21 日发布。其[发布公告](https://istio.io/latest/news/releases/1.31.x/announcing-1.31.1/)说明了一项修复：该修复可防止无法解析的 `BackendTLSPolicy` CA 引用回退到明文后端连接。

本指南中的新安装命令使用 1.31.1。Istio 1.31 公布的 Kubernetes 支持范围为 1.32–1.37；EKS 标准支持目前涵盖 1.34–1.37。两者的标准支持重叠范围为 1.34–1.37；在 EKS 延长支持版本（1.31–1.33）中，1.32 和 1.33 也属于 Istio 1.31 的支持范围。安装前请重新核对 [Istio 支持矩阵](https://istio.io/latest/docs/releases/supported-releases/)和 [EKS 版本生命周期](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html)。

在本次审查时，矩阵中仍将 Istio 1.30 和 1.29 列为受支持版本；1.29 的预计生命周期结束日期是今天，即 2026 年 10 月 12 日。安装或升级前请确认其状态。位于这些分支的现有安装至少需要 1.30.4 或 1.29.7，以应对 [ISTIO-SECURITY-2026-006](https://istio.io/latest/news/security/istio-security-2026-006/)，该公告涵盖 Envoy 漏洞、BackendTLSPolicy 的失效开放（fail-open）以及 EnvoyFilter Control Plane 拒绝服务问题。Istio 1.28 已停止支持。Istio 1.31 charts 使用 `https://blob.istio.io/istio-release/charts`；此前由 Google 托管的仓库不再接收新版本。

## 目录

1. [你真的需要 Service Mesh 吗？](#do-you-really-need-a-service-mesh)
2. [安装和初始设置](01-installation.md)
3. [基本概念](02-basic-concepts.md)
4. [架构](03-architecture.md)
5. [AWS 集成](04-aws-integration.md)
6. [术语表](glossary.md)
7. [流量管理](traffic-management/README.md)
8. [安全性](security/README.md)
9. [可观测性](observability/README.md)
10. [弹性](resilience/README.md)
11. [高级主题](advanced/README.md)
12. [故障排除](troubleshooting/common-errors.md)
13. [最佳实践](best-practices.md)
14. [替代方案比较](comparison/README.md)

## 什么是 Istio？

Istio 是一个开源 Service Mesh 平台，用于连接、保护、控制和观测微服务。它管理复杂微服务架构中服务之间的通信，并提供流量控制、安全性和可观测性。

### Service Mesh 概念

<div align="center"><img src="https://istio.io/latest/img/service-mesh.svg" alt="Istio Service Mesh" width="800"></div>

Service Mesh 是管理微服务之间通信的基础设施层。Istio 支持 Envoy Sidecar 和 ambient 模式（节点级 ztunnel 加上可选的 L7 waypoint）。代理处理已加入 mesh 的流量；被排除的流量和不受支持的协议不在此覆盖范围内。无需修改应用程序代码即可提供以下能力：

* **流量路由**：智能路由、负载均衡、Canary 部署
* **安全性**：自动 mTLS、身份验证、授权
* **可观测性**：指标、日志、分布式追踪
* **弹性**：Circuit Breaking、Retry、Timeout

### 实际使用示例

<p align="center"><img src="https://istio.io/latest/docs/examples/bookinfo/noistio.svg" alt="没有 Istio 的应用程序"><br><em>没有 Istio 的应用程序</em></p>

<p align="center"><img src="https://istio.io/latest/docs/examples/bookinfo/withistio.svg" alt="使用 Istio 的应用程序"><br><em>使用 Istio 的应用程序 - Envoy Proxy 作为 Sidecar 部署到每个服务</em></p>

这些 Bookinfo 图示展示了 Sidecar 模式。自动注入仅会向选择加入的命名空间或工作负载中新创建的 Pod 添加 Envoy；ambient 模式不会注入 Sidecar。

## 你真的需要 Service Mesh 吗？

下方的服务数量阈值和检查清单分数仅用于引导讨论，并非 Istio 的要求。出于安全需求，小型 mesh 也可能有合理性。决策图使用相同的示例阈值。

Service Mesh 是强大的工具，但并不适用于所有情况。采用前需要谨慎考虑。

### 决策流程

![采用 Service Mesh 的决策流程：依次检查微服务架构、10 个以上服务、复杂的流量/安全性/可观测性需求以及运维资源，最终得出建议使用 mesh、无需使用、采用替代方案或谨慎审查的结论。](../../.gitbook/assets/en-service-mesh-istio-overview-0.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-overview-0.html)

### 需要 Service Mesh 的情况 ✅

#### 1. 复杂的微服务环境

![并列比较：四个服务在没有 mesh 时手动配置 mTLS、重试和日志，与 Service Mesh 自动处理并控制相同四个服务之间通信的情形。](../../.gitbook/assets/en-service-mesh-istio-overview-1.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-overview-1.html)

**建议标准**：

* ✅ 10 个或更多微服务
* ✅ 频繁的服务间通信（东西向流量）
* ✅ 使用多种编程语言（多语言）
* ✅ 多个团队独立开发服务

#### 2. Zero Trust 安全要求

**Service Mesh 提供**：

* 服务之间自动进行 mTLS 加密
* 基于 SPIFFE 的身份管理
* 细粒度的身份验证/授权策略
* 强制执行 mTLS 时 mesh 流量会被加密；仅自动 mTLS 不会拒绝明文客户端

**不使用替代方案难以实现**：

* 在每个服务中重复实现安全逻辑
* 手动管理证书的复杂性
* 不一致的安全策略

#### 3. 高级流量管理

```yaml
# Canary Deployment (Traffic Distribution)
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
      weight: 90
    - destination:
        host: reviews
        subset: v2
      weight: 10  # Only 10% to new version
```

**需要以下场景时**：

* Canary 部署、A/B 测试
* 基于 Header/路径的路由
* Traffic Mirroring（Shadow Testing）
* Fault Injection（Chaos Engineering）
* Circuit Breaking、Retry、Timeout

#### 4. 统一的可观测性

**Service Mesh 的优势**：

* 无需修改应用程序代码即可自动收集指标
* 代理生成 trace span；应用程序必须传播 trace header，才能关联请求
* 统一的日志格式
* 服务拓扑可视化（Kiali）

### 不需要 Service Mesh 的情况 ❌

#### 1. 简单架构

![用户请求通过负载均衡器（Ingress Controller）到达单体应用程序及其数据库——架构足够简单，无需 Service Mesh，Ingress Controller 即可满足需求。](../../.gitbook/assets/en-service-mesh-istio-overview-2.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-overview-2.html)

**改用以下方案**：

* 受维护的 Kubernetes Gateway API 或 Ingress Controller
* 简单的负载均衡器
* 在应用程序层实现

#### 2. 微服务数量较少（<10）

**开销大于收益**：

* Service Mesh 的运维复杂性 > 获得的收益
* 5-10 个服务可以手动管理
* 当 CNI 强制执行时，NetworkPolicy 可以提供 L3/L4 隔离；它不提供 mTLS 或 HTTP 授权

**替代方案**：

```yaml
# L3/L4 ingress isolation; requires a NetworkPolicy-capable CNI
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-frontend-to-backend
spec:
  podSelector:
    matchLabels:
      app: backend
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: frontend
```

#### 3. 运维资源不足

**Service Mesh 运维要求**：

* Istio/Envoy 专业知识
* Control Plane 监控和管理
* 升级和补丁管理
* 故障排除能力（调试复杂度增加）

**所需团队准备**：

* 至少 1-2 名 Service Mesh 专家
* 持续学习和跟踪更新
* 足够的测试环境

#### 4. 性能极其关键时

**Service Mesh 开销**：

使用具有代表性的流量、代理配置和遥测设置测量延迟、CPU 和内存。[官方性能页面](https://istio.io/latest/docs/ops/deployment/performance-and-scalability/)记录了 Istio 1.24 基准测试；这些历史结果不能保证适用于其他版本或工作负载。

**考虑替代方案**：

* Ambient 模式（共享 L4 代理；节省程度取决于流量和 waypoint 部署）
* 基于 CNI 的解决方案（Cilium）
* 应用程序层优化

### 替代解决方案比较

| 功能                    | Service Mesh                                 | CNI (Cilium)    | Ingress Controller | 应用程序层                |
| -------------------------- | -------------------------------------------- | --------------- | ------------------ | ------------------------ |
| **L7 流量管理**  | ✅ 完全支持                               | ⚠️ 有限      | ⚠️ 仅 Ingress    | ✅ 可实现               |
| **mTLS 自动化**        | ✅ 完全支持                               | ⚠️ 双向身份验证和加密相互独立      | ❌ 不支持    | ❌ 手动实现  |
| **分布式追踪**    | ⚠️ 需要传播 trace context                                  | ❌ 不支持 | ❌ 不支持    | ⚠️ 手动实现 |
| **L3/L4 策略**         | ✅ 支持                                  | ✅ 完全支持  | ❌ 不支持    | ❌ 不支持          |
| **运维复杂性** | 🔴 高                                      | 🟡 中       | 🟢 低             | 🟡 中                |
| **资源开销**      | <p>🔴 高（Sidecar）<br>🟢 低（Ambient）</p> | 🟢 低          | 🟢 低             | 🟢 无                  |
| **适用规模**         | 取决于需求                                 | 所有规模      | 小规模        | 小规模              |

### 基于 CNI 的解决方案（Cilium）

Cilium 基于 eBPF 在**网络层**提供许多功能：

![Istio 基于 L7 代理的 Service Mesh 与 Cilium 基于 eBPF 内核级 CNI 的比较，并关联到相应使用场景：复杂 L7 逻辑适合 Service Mesh，策略与性能适合 Cilium，大型企业则同时使用两者。](../../.gitbook/assets/en-service-mesh-istio-overview-3.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-overview-3.html)

**Cilium 更适合的情况**：

* L3/L4 网络策略是主要目的
* 在所需策略/加密设置下测得的性能满足工作负载需求
* 复用现有 Cilium 部署，且其受支持功能符合要求
* 网络策略和可观测性是主要需求；Cilium 的带外双向身份验证需要单独使用 WireGuard/IPsec 加密，以保障负载数据机密性

Cilium 1.20.1 还提供独立的 [ztunnel 透明加密 beta](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/security/network/encryption-ztunnel.rst)，通过 `encryption.type: ztunnel` 选择。它通过命名空间注册提供 TCP 工作负载 mTLS；两个端点都必须注册。它不包括 ClusterMesh 和使用 host network 的 Pod，并且已发布指南警告，除非目标是 HBONE 端口 15008，否则常规 L4 策略在此路径上不生效。这是一个独立的部署选择，具有自身的 CA/bootstrap 要求。

该图强调 CNI 的作用；Cilium 也有 L7 Envoy 功能。组件数量和运维成本取决于所选模式。

**参考**：[Cilium 文档](../../networking/cilium/README.md)

### 决策检查清单

采用前请回答以下问题：

**架构**：

* [ ] 是否有 10 个或更多微服务？
* [ ] 服务间通信是否复杂？
* [ ] 是否使用多种编程语言？

**安全性**：

* [ ] 是否需要 Zero Trust 安全模型？
* [ ] 服务之间是否必须使用 mTLS 加密？
* [ ] 是否需要细粒度访问控制？

**流量管理**：

* [ ] 是否需要 Canary 部署、A/B 测试？
* [ ] 是否需要高级路由规则？
* [ ] 是否有许多服务需要 Circuit Breaking、Retry？

**可观测性**：

* [ ] 是否必须使用分布式追踪？
* [ ] 是否需要统一指标收集？
* [ ] 是否需要服务拓扑可视化？

**运维**：

* [ ] 是否拥有 Service Mesh 专家？
* [ ] 能否应对运维复杂性？
* [ ] 能否接受资源开销？

**结果**：

* ✅ 勾选 10 项或更多：强烈建议使用 Service Mesh
* 🟡 勾选 5-9 项：需要仔细评估，从小规模开始（建议使用 Ambient Mode）
* ❌ 勾选 4 项或更少：考虑替代方案（CNI、Ingress、应用程序层）

### 渐进式采用策略

如果确定需要 Service Mesh，请逐步采用：

![分四个阶段进行推广：从仅收集指标的可观测性，到 mTLS 安全性，再到 Canary 流量管理，最后达到完整的高级功能集——每个阶段都由验证把关。](../../.gitbook/assets/en-service-mesh-istio-overview-4.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-overview-4.html)

**建议顺序**：

1. **试点项目**（1-2 个命名空间）
2. **可观测性优先**（指标、日志、trace）
3. **应用安全性**（mTLS PERMISSIVE → STRICT）
4. **流量管理**（VirtualService、DestinationRule）
5. **全公司范围扩展**

### 主要功能

1.  **流量管理**

    VirtualService 选择路由；DestinationRule 定义 subsets 和目标流量策略。

    * 智能路由和负载均衡
    * A/B 测试、Canary 部署、Blue/Green 部署
    * Circuit Breaking、Retry、Timeout 控制
    * Traffic Mirroring 和 Fault Injection
2.  **安全性**

    <div align="center"><img src="https://istio.io/latest/docs/concepts/security/arch-sec.svg" alt="安全架构" width="600"></div>

    * 服务之间自动进行 mTLS 加密
    * 强身份验证和授权
    * 细粒度访问控制策略
    * 网络隔离和安全策略
3.  **可观测性**

    <div align="center"><img src="https://istio.io/latest/docs/tasks/observability/kiali/kiali-graph.png" alt="Kiali 服务图" width="700"></div>

    * 代理指标以及可配置的访问日志和追踪
    * Prometheus、Grafana、Jaeger、Kiali 集成
    * 服务拓扑可视化
    * 实时流量监控
4. **弹性**
   * Circuit Breaker 模式
   * Rate Limiting
   * Outlier Detection
   * Zone Aware Routing

### Istio 架构

<div align="center"><img src="https://istio.io/latest/docs/ops/deployment/architecture/arch.svg" alt="Istio 架构" width="700"></div>

Istio 由 Control Plane 和 Data Plane 组成：

![Istio 的 Control Plane 和 Data Plane：istiod 的 Pilot 将路由配置推送至每个 Pod 中的 Envoy Sidecar，Citadel 颁发证书；Envoy 拦截应用程序请求并交换经 mTLS 加密的流量。](../../.gitbook/assets/en-service-mesh-istio-overview-5.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-overview-5.html)

**Control Plane（istiod）**：

* 服务发现和代理配置（历史上称为 Pilot）
* 证书颁发机构和身份管理（历史上称为 Citadel）
* 配置验证；Galley 是已退役的独立组件，而非当前的独立服务

**Data Plane**：

* **Sidecar 模式**：每个已注册 Pod 一个 Envoy
* **Ambient 模式**：每个节点一个 ztunnel，用于 L4 安全性；可选 waypoint 代理用于 L7 处理

### 在 Amazon EKS 上使用 Istio 的优势

1. **轻松管理微服务**
   * 无需修改应用程序代码即可进行流量管理
   * 使用声明式配置一致地应用策略
   * 使用 Kubernetes Native API
2. **增强的安全性**
   * 服务之间自动加密
   * 通过 EKS Pod Identity 或 IRSA 访问 AWS API；Istio 工作负载身份仍基于 ServiceAccount
   * 细粒度权限控制
3. **改进的可观测性**
   * 与 Amazon CloudWatch 集成
   * 通过 AWS X-Ray 进行分布式追踪
   * 详细指标和日志
4. **与 AWS 服务集成**
   * Application Load Balancer（ALB）集成
   * AWS Certificate Manager（ACM）集成
   * 与 Amazon EBS CSI Driver 兼容

### 开始使用

[Gateway API 指南](https://istio.io/latest/docs/tasks/traffic-management/ingress/gateway-api/)

如果你刚开始使用 Istio，请按以下顺序阅读文档：

1. [**安装和初始设置**](01-installation.md)：在 EKS cluster 上安装 Istio
2. [**基本概念**](02-basic-concepts.md)：了解 Istio 核心概念
3. [**流量管理**](traffic-management/README.md)：学习 Gateway、VirtualService、DestinationRule
4. [**安全性**](security/README.md)：配置 mTLS、身份验证、授权
5. [**可观测性**](observability/README.md)：收集指标、日志、trace
6. [**最佳实践**](best-practices.md)：生产环境建议

### 动手示例

这些路由摘录需要匹配的 Service 和 DestinationRule subsets（`v1`/`v2`）；请参阅流量管理章节。

每个部分均包含可运行的 YAML 示例。所有示例均设计为可点击复制：

```yaml
# Example VirtualService
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
```

### 参考资料

* [Istio 官方文档](https://istio.io/latest/docs/)
* [Istio GitHub](https://github.com/istio/istio)
* [Istio EKS 平台指南](https://istio.io/latest/docs/setup/platform-setup/amazon-eks/)
* [Istio 社区](https://istio.io/latest/get-involved/)


* [追踪与应用程序 Header 传播](https://istio.io/latest/docs/tasks/observability/distributed-tracing/overview/)
* [Kubernetes NetworkPolicy 功能](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
* [Cilium 双向身份验证](https://docs.cilium.io/en/stable/network/servicemesh/mutual-authentication/mutual-authentication/)

### 测验

要测试你在本章中所学的内容，请尝试以下测验：

* [流量管理测验](../../quizzes/service-mesh/istio/traffic-management.md)
* [安全性测验](../../quizzes/service-mesh/istio/security.md)
* [可观测性测验](../../quizzes/service-mesh/istio/observability.md)
* [弹性测验](../../quizzes/service-mesh/istio/resilience.md)
* [高级主题测验](../../quizzes/service-mesh/istio/advanced.md)
