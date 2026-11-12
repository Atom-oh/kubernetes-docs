# Istio

> **最后更新**：2026年10月26日

Amazon EKS 上使用 Istio 服务网格的实用指南。

### 2026年10月安全更新：1.31.3、1.30.7 和 1.29.10

2026年10月22日，针对 [ISTIO-SECURITY-2026-008](https://istio.io/latest/news/security/istio-security-2026-008/)（CVE-2026-111943）的安全补丁版本发布：**1.31.3**、**1.30.7** 和 **1.29.10**——最后一个版本属于例外发布，因为 1.29 已于2026年10月15日停止维护。2026年10月20日，八个 eMudhra 中间 CA 证书的私钥被披露为已泄露；Envoy、Go 和 ztunnel 都不会强制执行证书透明度，因此持有这些密钥的人可以为 Istio 镜像所附带的公共 CA 证书包信任的任意域名签发证书。补丁从镜像 CA 证书包中移除了这些已泄露的中间证书，并在 1.30/1.31 上使用 Go 1.26.10 构建 istiod、`istioctl` 和 `pilot-agent`（该版本会拒绝包含这些已泄露密钥的证书链），同时更新 ztunnel 的 `rustls-webpki`。信任系统 CA 证书包的配置可能受到影响——例如，`tls.mode: SIMPLE` 且未设置 `caCertificates` 的 `DestinationRule`，或 `RequestAuthentication` 的 `jwksUri` 获取；Istio 自身网格的 mTLS 证书不受影响。Istio 1.32.0-beta.0 也于同日发布。

### 2026年10月审查：受支持的版本

Istio 1.31.0 已正式发布；其[发布公告](https://istio.io/latest/news/releases/1.31.x/announcing-1.31/)于2026年8月31日发布。目前的补丁版本为 **1.31.3**，于10月22日发布（见上文的2026年10月安全更新）。1.31.2 补丁于10月15日发布，包含 [ISTIO-SECURITY-2026-007](https://istio.io/latest/news/security/istio-security-2026-007/) 安全修复（[发布公告](https://istio.io/latest/news/releases/1.31.x/announcing-1.31.2/)）。更早的补丁 1.31.1 于9月21日发布；其[发布公告](https://istio.io/latest/news/releases/1.31.x/announcing-1.31.1/)介绍了一项修复，可防止未解析的 `BackendTLSPolicy` CA 引用回退到明文后端连接。

本指南中的全新安装命令使用 1.31.2。Istio 1.31 公布的 Kubernetes 支持范围为 1.32–1.37；EKS 标准支持目前覆盖 1.34–1.37。两者标准支持范围的交集为 1.34–1.37；在 EKS 延长支持版本（1.31–1.33）中，1.32 和 1.33 也在 Istio 1.31 的支持范围内。安装前请重新查阅 [Istio 支持矩阵](https://istio.io/latest/docs/releases/supported-releases/)和 [EKS 版本生命周期](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html)。

截至本次审查时，支持矩阵仍将 Istio 1.30 和 1.29 列为受支持版本；矩阵列出的 1.29 停止维护日期为2026年10月12日（预计）。安装或升级前请确认其状态。这些分支上的现有安装至少需要升级到 1.30.4 或 1.29.7，才能获得 [ISTIO-SECURITY-2026-006](https://istio.io/latest/news/security/istio-security-2026-006/) 修复；该公告涵盖 Envoy 漏洞、BackendTLSPolicy 故障时默认放行，以及 EnvoyFilter 导致的控制平面拒绝服务问题。于10月15日发布的 [ISTIO-SECURITY-2026-007](https://istio.io/latest/news/security/istio-security-2026-007/) 影响 1.31.0–1.31.1、1.30.0–1.30.5 和 1.29.0–1.29.8；矩阵列出的首批已知无 CVE 版本分别是 1.31.2、1.30.6 和 1.29.9。Istio 1.28 已停止支持。Istio 1.31 的 Chart 使用 `https://blob.istio.io/istio-release/charts`；此前由 Google 托管的仓库不再接收新版本。

### 2026年9月更新：1.31.1、1.30.5 和 1.29.8 补丁版本

2026年9月21日，三个受支持分支均发布了补丁版本：[1.31.1](https://istio.io/latest/news/releases/1.31.x/announcing-1.31.1/)、1.30.5 和 1.29.8。1.31.1 包含安全修复 [GHSA-qm8v-g4f9-qhjx](https://github.com/istio/istio/security/advisories/GHSA-qm8v-g4f9-qhjx)（CVSS 6.8，中危）：当 CA 引用无法解析时，`BackendTLSPolicy` 会在 sidecar 代理上故障并以明文方式放行。其他修复包括：ambient 模式 CNI 节点代理自动检测到的 iptables 后端（legacy 与 nft）在代理重启间发生切换；istiod 的 CPU 使用量随 `AuthorizationPolicies` 数量增加而增长；以及 ambient 多集群模式在轮换远程集群凭证时发生内存泄漏。全新安装和现有的 1.31 安装都应更新到 1.31.1。

## 目录

1. [你真的需要服务网格吗？](#do-you-really-need-a-service-mesh)
2. [安装和初始设置](01-installation.md)
3. [基本概念](02-basic-concepts.md)
4. [架构](03-architecture.md)
5. [AWS 集成](04-aws-integration.md)
6. [术语表](glossary.md)
7. [流量管理](traffic-management/README.md)
8. [安全](security/README.md)
9. [可观测性](observability/README.md)
10. [弹性](resilience/README.md)
11. [高级主题](advanced/README.md)
12. [故障排除](troubleshooting/common-errors.md)
13. [最佳实践](best-practices.md)
14. [替代方案对比](comparison/README.md)

## 什么是 Istio？

Istio 是一个开源服务网格平台，用于连接、保护、控制和观测微服务。它管理复杂微服务架构中的服务间通信，并提供流量控制、安全和可观测性功能。

### 服务网格概念

<div align="center"><img src="https://istio.io/latest/img/service-mesh.svg" alt="Istio Service Mesh" width="800"></div>

服务网格是用于管理微服务间通信的基础设施层。Istio 支持 Envoy sidecar 和 ambient 模式（节点级 ztunnel 加可选的 L7 waypoint）。代理负责处理已加入网格的流量；未纳入网格的流量和不受支持的协议不在其覆盖范围内。无需修改应用代码，即可获得以下能力：

* **流量路由**：智能路由、负载均衡、金丝雀部署
* **安全**：自动 mTLS、身份验证、授权
* **可观测性**：指标、日志、分布式追踪
* **弹性**：断路器、重试、超时

### 实用示例

<p align="center"><img src="https://istio.io/latest/docs/examples/bookinfo/noistio.svg" alt="Application without Istio"><br><em>Application without Istio</em></p>

<p align="center"><img src="https://istio.io/latest/docs/examples/bookinfo/withistio.svg" alt="Application with Istio"><br><em>Application with Istio - Envoy Proxy deployed as Sidecar to each service</em></p>

这些 Bookinfo 示意图展示的是 sidecar 模式。自动注入只会为选择启用注入的命名空间或工作负载中新建的 Pod 添加 Envoy；ambient 模式不会注入 sidecar。

## 你真的需要服务网格吗？

以下服务数量阈值和检查清单评分只是讨论参考，并非 Istio 的要求。即使是小型网格，也可能因安全需求而有其必要性。决策图使用相同的示例性阈值。

服务网格是一种强大的工具，但并非适用于所有场景。采用之前需要审慎考虑。

### 决策流程

![Decision flow for adopting a service mesh: checking microservices architecture, 10+ services, complex traffic/security/observability needs, and ops resources in turn leads to mesh recommended, not needed, alternatives, or careful review.](../../.gitbook/assets/en-service-mesh-istio-overview-0.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-overview-0.html)

### 需要服务网格的情况 ✅

#### 1. 复杂的微服务环境

![Side-by-side comparison of four services hand-wiring mTLS, retries, and logging without a mesh versus a Service Mesh automatically handling and controlling communication between the same four services.](../../.gitbook/assets/en-service-mesh-istio-overview-1.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-overview-1.html)

**建议条件**：

* ✅ 10 个或更多微服务
* ✅ 服务间通信频繁（东西向流量）
* ✅ 使用多种编程语言（多语言）
* ✅ 多个团队独立开发服务

#### 2. 零信任安全要求

**服务网格提供**：

* 服务间自动 mTLS 加密
* 基于 SPIFFE 的身份管理
* 精细化的身份验证/授权策略
* 强制执行 mTLS 时对网格流量进行加密；仅启用自动 mTLS 并不会拒绝明文客户端

**缺少替代方案时难以实现**：

* 在每个服务中重复实现安全逻辑
* 手动管理证书的复杂性
* 安全策略不一致

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

**适用场景**：

* 金丝雀部署、A/B 测试
* 基于标头/路径的路由
* 流量镜像（影子测试）
* 故障注入（混沌工程）
* 断路器、重试、超时

#### 4. 统一的可观测性

**服务网格的优势**：

* 无需修改应用代码即可自动收集指标
* 代理生成追踪跨度；应用必须传播追踪标头，才能关联请求
* 统一的日志格式
* 服务拓扑可视化（Kiali）

### 不需要服务网格的情况 ❌

#### 1. 简单的架构

![A user request passing through a load balancer (Ingress Controller) to a single monolithic application and its database, simple enough that an ingress controller suffices without a service mesh.](../../.gitbook/assets/en-service-mesh-istio-overview-2.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-overview-2.html)

**可改用**：

* 维护中的 Kubernetes Gateway API 或 Ingress Controller
* 简单的负载均衡器
* 在应用层实现

#### 2. 微服务较少（<10）

**额外负担更大**：

* 服务网格的运维复杂性 > 所获得的收益
* 5–10 个服务可以手动管理
* 如果 CNI 强制执行 NetworkPolicy，它可以提供 L3/L4 隔离；但不提供 mTLS 或 HTTP 授权

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

**服务网格的运维要求**：

* Istio/Envoy 专业知识
* 控制平面监控和管理
* 升级和补丁管理
* 故障排除能力（调试复杂度增加）

**团队需要做好以下准备**：

* 至少 1–2 名服务网格专家
* 持续学习并跟踪更新
* 充足的测试环境

#### 4. 性能要求极为严格

**服务网格的额外开销**：

使用有代表性的流量、代理配置和遥测设置，测量延迟、CPU 和内存。[官方性能页面](https://istio.io/latest/docs/ops/deployment/performance-and-scalability/)记录了 Istio 1.24 的基准测试；这些历史结果并不保证适用于其他版本或工作负载。

**可考虑的替代方案**：

* Ambient 模式（共享 L4 代理；节省效果取决于流量和 waypoint 部署方式）
* 基于 CNI 的方案（Cilium）
* 应用层优化

### 替代方案对比

| 特性                       | 服务网格                                      | CNI（Cilium）   | Ingress Controller | 应用层                   |
| -------------------------- | -------------------------------------------- | --------------- | ------------------ | ------------------------ |
| **L7 流量管理**            | ✅ 完全支持                                    | ⚠️ 有限支持      | ⚠️ 仅支持 Ingress   | ✅ 可以实现               |
| **mTLS 自动化**            | ✅ 完全支持                                    | ⚠️ 双向身份验证与加密相互独立      | ❌ 不支持            | ❌ 手动实现               |
| **分布式追踪**             | ⚠️ 需要传播追踪上下文                                  | ❌ 不支持         | ❌ 不支持            | ⚠️ 手动实现              |
| **L3/L4 策略**             | ✅ 支持                                        | ✅ 完全支持       | ❌ 不支持            | ❌ 不支持                 |
| **运维复杂性**             | 🔴 高                                         | 🟡 中            | 🟢 低               | 🟡 中                    |
| **资源开销**               | <p>🔴 高（Sidecar）<br>🟢 低（Ambient）</p> | 🟢 低            | 🟢 低               | 🟢 无                    |
| **适用规模**               | 取决于需求                                     | 所有规模          | 小规模              | 小规模                   |

### 基于 CNI 的方案（Cilium）

Cilium 基于 eBPF 在**网络层**提供许多功能：

![Comparison of Istio's L7 proxy-based service mesh and Cilium's eBPF kernel-level CNI, linked to the usage scenarios where complex L7 logic calls for a service mesh, policy and performance call for Cilium, and large enterprises use both.](../../.gitbook/assets/en-service-mesh-istio-overview-3.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-overview-3.html)

**更适合使用 Cilium 的情况**：

* 主要需求是 L3/L4 网络策略
* 在所需的策略/加密设置下测得的性能能够满足工作负载需求
* 复用现有 Cilium 部署，且其支持的功能能够满足要求
* 主要需求是网络策略和可观测性；Cilium 的带外双向身份验证需要另行配置 WireGuard/IPsec 加密，才能保护有效载荷的机密性

Cilium 1.20.1 还提供独立的 [ztunnel 透明加密 beta 版](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/security/network/encryption-ztunnel.rst)，通过 `encryption.type: ztunnel` 选择启用。它支持 TCP 工作负载 mTLS，并通过命名空间加入网格；通信的两个端点都必须加入。它不支持 ClusterMesh 和使用主机网络的 Pod；已发布指南还警告，普通 L4 策略在此路径上不起作用，除非策略以 HBONE 端口 15008 为目标。这是一种独立的部署选择，有其自身的 CA/引导要求。

该图强调了 CNI 的作用；Cilium 也具备 L7 Envoy 功能。组件数量和运维成本取决于所选模式。

**参考**：[Cilium 文档](../../networking/cilium/README.md)

### 决策检查清单

采用之前，请回答以下问题：

**架构**：

* [ ] 你有 10 个或更多微服务吗？
* [ ] 服务间通信是否复杂？
* [ ] 是否使用多种编程语言？

**安全**：

* [ ] 是否需要零信任安全模型？
* [ ] 服务间是否必须使用 mTLS 加密？
* [ ] 是否需要精细化访问控制？

**流量管理**：

* [ ] 是否需要金丝雀部署和 A/B 测试？
* [ ] 是否需要高级路由规则？
* [ ] 是否有许多服务需要断路器和重试？

**可观测性**：

* [ ] 是否必须使用分布式追踪？
* [ ] 是否需要统一收集指标？
* [ ] 是否需要服务拓扑可视化？

**运维**：

* [ ] 你有服务网格专家吗？
* [ ] 你能应对运维复杂性吗？
* [ ] 你能接受资源开销吗？

**结果**：

* ✅ 勾选 10 项或更多：强烈建议使用服务网格
* 🟡 勾选 5–9 项：需要谨慎评估，从小规模开始（建议使用 Ambient 模式）
* ❌ 勾选 4 项或更少：考虑替代方案（CNI、Ingress、应用层）

### 渐进式采用策略

如果确定需要服务网格，请逐步采用：

![Four-phase rollout moving from observability-only metric collection, to mTLS security, to canary traffic management, and finally to the full advanced feature set, with each phase gated by validation.](../../.gitbook/assets/en-service-mesh-istio-overview-4.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-overview-4.html)

**建议顺序**：

1. **试点项目**（1–2 个命名空间）
2. **优先实现可观测性**（指标、日志、追踪）
3. **应用安全措施**（mTLS PERMISSIVE → STRICT）
4. **流量管理**（VirtualService、DestinationRule）
5. **全公司推广**

### 主要功能

1.  **流量管理**

    VirtualService 选择路由；DestinationRule 定义子集和目标流量策略。

    * 智能路由和负载均衡
    * A/B 测试、金丝雀部署、蓝绿部署
    * 断路器、重试、超时控制
    * 流量镜像和故障注入
2.  **安全**

    <div align="center"><img src="https://istio.io/latest/docs/concepts/security/arch-sec.svg" alt="Security Architecture" width="600"></div>

    * 服务间自动 mTLS 加密
    * 强身份验证和授权
    * 精细化访问控制策略
    * 网络隔离和安全策略
3.  **可观测性**

    <div align="center"><img src="https://istio.io/latest/docs/tasks/observability/kiali/kiali-graph.png" alt="Kiali Service Graph" width="700"></div>

    * 代理指标，以及可配置的访问日志和追踪
    * 集成 Prometheus、Grafana、Jaeger、Kiali
    * 服务拓扑可视化
    * 实时流量监控
4. **弹性**
   * 断路器模式
   * 速率限制
   * 异常检测
   * 区域感知路由

### Istio 架构

<div align="center"><img src="https://istio.io/latest/docs/ops/deployment/architecture/arch.svg" alt="Istio Architecture" width="700"></div>

Istio 由控制平面和数据平面组成：

![Istio's Control Plane and Data Plane: istiod's Pilot pushes routing configuration and Citadel issues certificates to the Envoy sidecar in each pod, and the Envoys intercept application requests and exchange mTLS-encrypted traffic.](../../.gitbook/assets/en-service-mesh-istio-overview-5.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-overview-5.html)

**控制平面（istiod）**：

* 服务发现和代理配置（历史上由 Pilot 负责）
* 证书颁发机构和身份管理（历史上由 Citadel 负责）
* 配置验证；Galley 是已退役的独立组件，并非当前单独运行的服务

**数据平面**：

* **Sidecar 模式**：每个加入网格的 Pod 配置一个 Envoy
* **Ambient 模式**：每个节点配置一个 ztunnel，负责 L4 安全；可选配置 waypoint 代理进行 L7 处理

### 在 Amazon EKS 上使用 Istio 的优势

1. **简化微服务管理**
   * 无需修改应用代码即可进行流量管理
   * 通过声明式配置一致地应用策略
   * 使用 Kubernetes 原生 API
2. **增强安全性**
   * 自动加密服务间通信
   * 通过 EKS Pod Identity 或 IRSA 访问 AWS API；Istio 工作负载身份仍基于服务账户
   * 精细化权限控制
3. **改善可观测性**
   * 与 Amazon CloudWatch 集成
   * 通过 AWS X-Ray 实现分布式追踪
   * 详细的指标和日志
4. **与 AWS 服务集成**
   * 集成 Application Load Balancer（ALB）
   * 集成 AWS Certificate Manager（ACM）
   * 兼容 Amazon EBS CSI Driver

### 开始使用

[Gateway API 指南](https://istio.io/latest/docs/tasks/traffic-management/ingress/gateway-api/)

如果你刚开始使用 Istio，请按以下顺序阅读文档：

1. [**安装和初始设置**](01-installation.md)：在 EKS 集群上安装 Istio
2. [**基本概念**](02-basic-concepts.md)：了解 Istio 的核心概念
3. [**流量管理**](traffic-management/README.md)：了解 Gateway、VirtualService、DestinationRule
4. [**安全**](security/README.md)：配置 mTLS、身份验证和授权
5. [**可观测性**](observability/README.md)：收集指标、日志和追踪数据
6. [**最佳实践**](best-practices.md)：了解生产环境建议

### 实践示例

这些路由配置片段需要匹配的 Service 和 DestinationRule 子集（`v1`/`v2`）；请参阅流量管理章节。

每个部分都包含可运行的 YAML 示例。所有示例均可点击复制：

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


* [追踪和应用标头传播](https://istio.io/latest/docs/tasks/observability/distributed-tracing/overview/)
* [Kubernetes NetworkPolicy 功能](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
* [Cilium 双向身份验证](https://docs.cilium.io/en/stable/network/servicemesh/mutual-authentication/mutual-authentication/)

### 测验

要检验你对本章内容的掌握程度，请尝试以下测验：

* [流量管理测验](../../quizzes/service-mesh/istio/traffic-management.md)
* [安全测验](../../quizzes/service-mesh/istio/security.md)
* [可观测性测验](../../quizzes/service-mesh/istio/observability.md)
* [弹性测验](../../quizzes/service-mesh/istio/resilience.md)
* [高级主题测验](../../quizzes/service-mesh/istio/advanced.md)
