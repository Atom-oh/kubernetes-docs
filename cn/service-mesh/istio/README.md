# Istio

> **最后更新**：2026年11月16日

在 Amazon EKS 上使用 Istio Service Mesh 的实用指南。

### 2026年11月更新：Istio 1.32.0 已发布

**Istio 1.32.0** 于2026年11月9日正式发布（[发行说明](https://istio.io/latest/news/releases/1.32.x/announcing-1.32/)，[GitHub 发行版](https://github.com/istio/istio/releases/tag/1.32.0)）；此前，1.32.0-beta.0 于10月22日发布，rc.0 至 rc.2 则在10月28日至11月6日期间发布。同一周（11月6日），受支持分支也发布了补丁版本 [1.31.4](https://istio.io/news/releases/1.31.x/announcing-1.31.4/) 和 1.30.8。新的次要版本正式发布后，Istio 的支持策略会使旧分支更接近生命周期结束，因此在安装或升级前，请查看[支持矩阵](https://istio.io/latest/docs/releases/supported-releases/)，确认 1.32 支持的 Kubernetes 版本范围以及各分支的状态。本指南中的新安装命令和示例仍以 1.31 为目标版本。

### 2026年10月安全更新：1.31.3、1.30.7 和 1.29.10

2026年10月22日，针对 [ISTIO-SECURITY-2026-008](https://istio.io/latest/news/security/istio-security-2026-008/)（CVE-2026-111943）的安全补丁版本发布：**1.31.3**、**1.30.7** 和 **1.29.10**。其中最后一个版本属于特殊发布，因为 1.29 已于2026年10月15日结束生命周期。2026年10月20日，有消息披露八个 eMudhra 中间 CA 证书的私钥已泄露并遭到窃取；Envoy、Go 和 ztunnel 不会强制执行证书透明度，因此持有这些私钥的人可能为 Istio 镜像所附带的公共 CA bundle 信任的任何域名签发证书。这些补丁会从镜像 CA bundle 中移除遭泄露的中间证书，在 1.30/1.31 上使用 Go 1.26.10 构建 istiod、`istioctl` 和 `pilot-agent`（该版本会拒绝包含遭泄露密钥的证书链），并更新 ztunnel 的 `rustls-webpki`。信任系统 CA bundle 的配置可能受到影响，例如使用 `tls.mode: SIMPLE` 且未设置 `caCertificates` 的 `DestinationRule`，或通过 `jwksUri` 获取密钥集的 `RequestAuthentication`；Istio 自身的网格 mTLS 证书不受影响。Istio 1.32.0-beta.0 也于同一天发布。

### 2026年10月回顾：受支持的版本

Istio 1.31.0 已正式发布；其[发行公告](https://istio.io/latest/news/releases/1.31.x/announcing-1.31/)于2026年8月31日发布。目前的补丁版本是 **1.31.3**，于10月22日发布（参见上文的2026年10月安全更新）。1.31.2 补丁于10月15日发布，包含 [ISTIO-SECURITY-2026-007](https://istio.io/latest/news/security/istio-security-2026-007/) 安全修复（[发行公告](https://istio.io/latest/news/releases/1.31.x/announcing-1.31.2/)）。更早的补丁 1.31.1 于9月21日发布；其[发行公告](https://istio.io/latest/news/releases/1.31.x/announcing-1.31.1/)记录了一项修复，该修复可防止未解析的 `BackendTLSPolicy` CA 引用回退到明文后端连接。

本指南中的新安装命令使用 1.31.2。Istio 1.31 公布的 Kubernetes 支持范围为 1.32–1.37；EKS 当前的标准支持范围为 1.34–1.37。两者的标准支持交集为 1.34–1.37；在 EKS 扩展支持的版本（1.31–1.33）中，1.32 和 1.33 也处于 Istio 1.31 的支持范围内。安装前请再次查看 [Istio 支持矩阵](https://istio.io/latest/docs/releases/supported-releases/)和 [EKS 版本生命周期](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html)。

在本次回顾时，支持矩阵仍将 Istio 1.30 和 1.29 列为受支持版本；矩阵列出的 1.29 生命周期结束日期为2026年10月12日（预计）。安装或升级前请核实其状态。运行这些分支的现有安装至少需要 1.30.4 或 1.29.7，才能获得 [ISTIO-SECURITY-2026-006](https://istio.io/latest/news/security/istio-security-2026-006/) 修复；该公告涉及 Envoy 漏洞、BackendTLSPolicy 故障时默认放行，以及 EnvoyFilter 控制平面拒绝服务问题。10月15日发布的 [ISTIO-SECURITY-2026-007](https://istio.io/latest/news/security/istio-security-2026-007/) 影响 1.31.0–1.31.1、1.30.0–1.30.5 和 1.29.0–1.29.8；矩阵列出的首个无已知 CVE 的版本分别为 1.31.2、1.30.6 和 1.29.9。Istio 1.28 已停止支持。Istio 1.31 的 Chart 使用 `https://blob.istio.io/istio-release/charts`；之前由 Google 托管的仓库不再接收新版本。

### 2026年9月更新：1.31.1、1.30.5 和 1.29.8 补丁版本

2026年9月21日，所有三个受支持分支均发布了补丁版本：[1.31.1](https://istio.io/latest/news/releases/1.31.x/announcing-1.31.1/)、1.30.5 和 1.29.8。1.31.1 包含安全修复 [GHSA-qm8v-g4f9-qhjx](https://github.com/istio/istio/security/advisories/GHSA-qm8v-g4f9-qhjx)（CVSS 6.8，中危）：当 CA 引用未解析时，`BackendTLSPolicy` 会在 sidecar 代理上故障时默认回退到明文。其他修复包括：ambient 模式 CNI 节点代理自动检测到的 iptables 后端（legacy 与 nft）在代理重启之间发生切换；istiod CPU 使用量随 `AuthorizationPolicies` 数量增长；以及 ambient 多集群模式在轮换远程集群凭据时发生内存泄漏。新安装和现有的 1.31 安装都应升级到 1.31.1。

## 目录

1. [你真的需要 Service Mesh 吗？](#do-you-really-need-a-service-mesh)
2. [安装与初始设置](01-installation.md)
3. [基本概念](02-basic-concepts.md)
4. [架构](03-architecture.md)
5. [AWS 集成](04-aws-integration.md)
6. [术语表](glossary.md)
7. [流量管理](traffic-management/README.md)
8. [安全](security/README.md)
9. [可观测性](observability/README.md)
10. [弹性](resilience/README.md)
11. [高级主题](advanced/README.md)
12. [故障排查](troubleshooting/common-errors.md)
13. [最佳实践](best-practices.md)
14. [替代方案对比](comparison/README.md)

## 什么是 Istio？

Istio 是一个开源 Service Mesh 平台，用于连接、保护、控制和观测微服务。它管理复杂微服务架构中服务之间的通信，并提供流量控制、安全和可观测性能力。

### Service Mesh 概念

<div align="center"><img src="https://istio.io/latest/img/service-mesh.svg" alt="Istio Service Mesh" width="800"></div>

Service Mesh 是管理微服务之间通信的基础设施层。Istio 支持 Envoy sidecar 和 ambient 模式（节点级 ztunnel 加上可选的 L7 waypoint）。代理负责处理已加入网格的流量；被排除的流量和不受支持的协议不在覆盖范围内。它无需修改应用程序代码即可提供以下能力：

* **流量路由**：智能路由、负载均衡、金丝雀部署
* **安全**：自动 mTLS、身份验证、授权
* **可观测性**：指标、日志、分布式追踪
* **弹性**：断路、重试、超时

### 实际使用示例

<p align="center"><img src="https://istio.io/latest/docs/examples/bookinfo/noistio.svg" alt="Application without Istio"><br><em>不使用 Istio 的应用程序</em></p>

<p align="center"><img src="https://istio.io/latest/docs/examples/bookinfo/withistio.svg" alt="Application with Istio"><br><em>使用 Istio 的应用程序 - Envoy Proxy 作为 Sidecar 部署到每个服务</em></p>

这些 Bookinfo 图示展示了 sidecar 模式。对于选择加入的命名空间或工作负载，自动注入只会向新创建的 Pod 添加 Envoy；ambient 模式不会注入 sidecar。

## 你真的需要 Service Mesh 吗？ {#do-you-really-need-a-service-mesh}

下方的服务数量阈值和检查清单评分仅供讨论参考，并非 Istio 的要求。即使是小型网格，也可能因安全需求而具有合理性。决策图使用相同的示意性阈值。

Service Mesh 是一种强大的工具，但并非适用于所有情况。采用之前需要仔细考虑。

### 决策流程

![采用 Service Mesh 的决策流程：依次检查微服务架构、是否有 10 个以上服务、是否存在复杂的流量/安全/可观测性需求，以及是否具备运维资源，最终得出建议采用网格、无需采用、考虑替代方案或谨慎评估的结论。](../../.gitbook/assets/en-service-mesh-istio-overview-0.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-overview-0.html)

### 何时需要 Service Mesh ✅

#### 1. 复杂的微服务环境

![对比四个服务在没有网格时手动配置 mTLS、重试和日志，与使用 Service Mesh 自动处理并控制这四个相同服务之间通信的情形。](../../.gitbook/assets/en-service-mesh-istio-overview-1.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-overview-1.html)

**建议条件**：

* ✅ 10 个或更多微服务
* ✅ 服务间通信频繁（东西向流量）
* ✅ 使用多种编程语言（多语言环境）
* ✅ 多个团队独立开发服务

#### 2. 零信任安全要求

**Service Mesh 提供的能力**：

* 服务间自动进行 mTLS 加密
* 基于 SPIFFE 的身份管理
* 精细化的身份验证/授权策略
* 强制执行 mTLS 时对网格流量进行加密；仅启用自动 mTLS 并不会拒绝明文客户端

**没有替代方案时难以实现的事项**：

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
* 基于 Header/路径的路由
* 流量镜像（影子测试）
* 故障注入（混沌工程）
* 断路、重试、超时

#### 4. 统一的可观测性

**Service Mesh 的优势**：

* 无需修改应用程序代码即可自动收集指标
* 由代理生成追踪 Span；应用程序必须传播追踪 Header，才能关联请求
* 统一的日志格式
* 服务拓扑可视化（Kiali）

### 何时不需要 Service Mesh ❌

#### 1. 架构简单

![用户请求经由负载均衡器（Ingress Controller）到达单体应用和数据库，架构足够简单，无需 Service Mesh，仅使用 Ingress Controller 即可满足需求。](../../.gitbook/assets/en-service-mesh-istio-overview-2.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-overview-2.html)

**可改用以下方案**：

* 受维护的 Kubernetes Gateway API 或 Ingress Controller
* 简单的负载均衡器
* 在应用程序层实现

#### 2. 微服务较少（<10）

**额外开销大于收益**：

* Service Mesh 的运维复杂性 > 所获收益
* 5–10 个服务可以手动管理
* 如果 CNI 强制执行 NetworkPolicy，则可提供 L3/L4 隔离；但它不提供 mTLS 或 HTTP 授权

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

**Service Mesh 的运维要求**：

* 具备 Istio/Envoy 专业知识
* 监控和管理控制平面
* 升级与补丁管理
* 故障排查能力（调试复杂度增加）

**团队需要做好以下准备**：

* 至少有 1–2 名 Service Mesh 专家
* 持续学习并跟踪更新
* 具备充足的测试环境

#### 4. 性能要求极为关键

**Service Mesh 的开销**：

使用有代表性的流量、代理配置和遥测设置测量延迟、CPU 和内存。[官方性能页面](https://istio.io/latest/docs/ops/deployment/performance-and-scalability/)记录了 Istio 1.24 的基准测试；这些历史结果不保证适用于其他版本或工作负载。

**可考虑的替代方案**：

* Ambient 模式（共享 L4 代理；节省效果取决于流量和 waypoint 的部署情况）
* 基于 CNI 的方案（Cilium）
* 在应用程序层进行优化

### 替代方案对比

| 特性                       | Service Mesh                                 | CNI (Cilium)    | Ingress Controller | 应用层                   |
| -------------------------- | -------------------------------------------- | --------------- | ------------------ | ------------------------ |
| **L7 流量管理**            | ✅ 完全支持                                   | ⚠️ 有限支持      | ⚠️ 仅支持 Ingress   | ✅ 可以实现               |
| **mTLS 自动化**            | ✅ 完全支持                                   | ⚠️ 相互身份验证与加密彼此独立      | ❌ 不支持            | ❌ 手动实现               |
| **分布式追踪**             | ⚠️ 需要传播追踪上下文                                  | ❌ 不支持        | ❌ 不支持            | ⚠️ 手动实现               |
| **L3/L4 策略**             | ✅ 支持                                       | ✅ 完全支持      | ❌ 不支持            | ❌ 不支持                 |
| **运维复杂度**             | 🔴 高                                         | 🟡 中            | 🟢 低               | 🟡 中                     |
| **资源开销**               | <p>🔴 高 (Sidecar)<br>🟢 低 (Ambient)</p> | 🟢 低            | 🟢 低               | 🟢 无                     |
| **适用规模**               | 取决于需求                                   | 所有规模        | 小规模              | 小规模                   |

### 基于 CNI 的方案（Cilium）

Cilium 基于 eBPF 在**网络层**提供许多功能：

![对比 Istio 基于 L7 代理的 Service Mesh 与 Cilium 基于 eBPF 内核层的 CNI，并展示相应使用场景：复杂 L7 逻辑适合 Service Mesh，策略和性能需求适合 Cilium，大型企业则同时使用两者。](../../.gitbook/assets/en-service-mesh-istio-overview-3.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-overview-3.html)

**Cilium 更适合以下情况**：

* 主要需求是 L3/L4 网络策略
* 在所需策略/加密设置下测得的性能符合工作负载需求
* 复用现有的 Cilium 部署，且其支持的功能满足需求
* 主要需求是网络策略和可观测性；Cilium 的带外相互身份验证需要另外使用 WireGuard/IPsec 加密，才能确保有效载荷的机密性

Cilium 1.20.1 还提供独立的 [ztunnel 透明加密 Beta 版](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/security/network/encryption-ztunnel.rst)，通过 `encryption.type: ztunnel` 选择。它支持基于 TCP 的工作负载 mTLS，并要求工作负载加入命名空间；两个端点都必须加入。它不支持 ClusterMesh 和使用主机网络的 Pod；已发布的指南还提醒，除非目标是 HBONE 端口 15008，否则常规 L4 策略在此路径上不起作用。这是一个独立的部署选择，有其自身的 CA/引导要求。

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
* [ ] 是否必须对服务间通信进行 mTLS 加密？
* [ ] 是否需要精细化访问控制？

**流量管理**：

* [ ] 是否需要金丝雀部署和 A/B 测试？
* [ ] 是否需要高级路由规则？
* [ ] 是否有许多服务需要断路和重试？

**可观测性**：

* [ ] 分布式追踪是否为强制要求？
* [ ] 是否需要统一收集指标？
* [ ] 是否需要服务拓扑可视化？

**运维**：

* [ ] 是否有 Service Mesh 专家？
* [ ] 能否应对运维复杂性？
* [ ] 能否接受资源开销？

**结果**：

* ✅ 勾选 10 项或更多：强烈建议采用 Service Mesh
* 🟡 勾选 5–9 项：需要谨慎评估，从小规模开始（建议使用 Ambient 模式）
* ❌ 勾选 4 项或更少：考虑替代方案（CNI、Ingress、应用层）

### 渐进式采用策略

如果确定需要 Service Mesh，请逐步采用：

![四阶段部署流程：从仅用于可观测性的指标收集开始，然后是 mTLS 安全，再到金丝雀流量管理，最后启用完整的高级功能集，每个阶段都必须通过验证才能继续。](../../.gitbook/assets/en-service-mesh-istio-overview-4.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-overview-4.html)

**建议顺序**：

1. **试点项目**（1–2 个命名空间）
2. **先实现可观测性**（指标、日志、追踪）
3. **应用安全措施**（mTLS PERMISSIVE → STRICT）
4. **流量管理**（VirtualService、DestinationRule）
5. **扩展到整个公司**

### 主要功能

1.  **流量管理**

    VirtualService 用于选择路由；DestinationRule 用于定义子集和目标流量策略。

    * 智能路由和负载均衡
    * A/B 测试、金丝雀部署、蓝绿部署
    * 断路、重试、超时控制
    * 流量镜像和故障注入
2.  **安全**

    <div align="center"><img src="https://istio.io/latest/docs/concepts/security/arch-sec.svg" alt="Security Architecture" width="600"></div>

    * 服务间自动进行 mTLS 加密
    * 强身份验证和授权
    * 精细化访问控制策略
    * 网络隔离和安全策略
3.  **可观测性**

    <div align="center"><img src="https://istio.io/latest/docs/tasks/observability/kiali/kiali-graph.png" alt="Kiali Service Graph" width="700"></div>

    * 代理指标，以及可配置的访问日志和追踪
    * 与 Prometheus、Grafana、Jaeger、Kiali 集成
    * 服务拓扑可视化
    * 实时流量监控
4. **弹性**
   * 断路器模式
   * 速率限制
   * 异常点检测
   * 区域感知路由

### Istio 架构

<div align="center"><img src="https://istio.io/latest/docs/ops/deployment/architecture/arch.svg" alt="Istio Architecture" width="700"></div>

Istio 由控制平面和数据平面组成：

![Istio 的控制平面和数据平面：istiod 的 Pilot 向每个 Pod 中的 Envoy sidecar 推送路由配置，Citadel 颁发证书；Envoy 拦截应用请求并交换经 mTLS 加密的流量。](../../.gitbook/assets/en-service-mesh-istio-overview-5.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-overview-5.html)

**控制平面（istiod）**：

* 服务发现和代理配置（历史上由 Pilot 负责）
* 证书颁发机构和身份管理（历史上由 Citadel 负责）
* 配置验证；Galley 是已退役的独立组件，并非当前单独运行的服务

**数据平面**：

* **Sidecar 模式**：每个已加入网格的 Pod 部署一个 Envoy
* **Ambient 模式**：每个节点部署一个 ztunnel 以提供 L4 安全，并可选择部署 waypoint 代理进行 L7 处理

### 在 Amazon EKS 上使用 Istio 的优势

1. **轻松管理微服务**
   * 无需修改应用程序代码即可进行流量管理
   * 通过声明式配置一致地应用策略
   * 使用 Kubernetes 原生 API
2. **增强安全性**
   * 服务间自动加密
   * 通过 EKS Pod Identity 或 IRSA 访问 AWS API；Istio 工作负载身份仍基于服务账号
   * 精细化权限控制
3. **提升可观测性**
   * 与 Amazon CloudWatch 集成
   * 通过 AWS X-Ray 进行分布式追踪
   * 详细的指标和日志
4. **与 AWS 服务集成**
   * 集成 Application Load Balancer（ALB）
   * 集成 AWS Certificate Manager（ACM）
   * 兼容 Amazon EBS CSI Driver

### 开始使用

[Gateway API 指南](https://istio.io/latest/docs/tasks/traffic-management/ingress/gateway-api/)

如果你刚开始接触 Istio，请按以下顺序阅读文档：

1. [**安装与初始设置**](01-installation.md)：在 EKS 集群上安装 Istio
2. [**基本概念**](02-basic-concepts.md)：了解 Istio 的核心概念
3. [**流量管理**](traffic-management/README.md)：了解 Gateway、VirtualService、DestinationRule
4. [**安全**](security/README.md)：配置 mTLS、身份验证和授权
5. [**可观测性**](observability/README.md)：收集指标、日志和追踪数据
6. [**最佳实践**](best-practices.md)：生产环境建议

### 动手示例

以下路由片段要求存在匹配的 Service 和 DestinationRule 子集（`v1`/`v2`）；请参阅流量管理章节。

每个部分都包含可运行的 YAML 示例。所有示例都支持点击复制：

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


* [追踪与应用 Header 传播](https://istio.io/latest/docs/tasks/observability/distributed-tracing/overview/)
* [Kubernetes NetworkPolicy 功能](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
* [Cilium 相互身份验证](https://docs.cilium.io/en/stable/network/servicemesh/mutual-authentication/mutual-authentication/)

### 测验

要检验你对本章内容的掌握情况，请尝试以下测验：

* [流量管理测验](../../quizzes/service-mesh/istio/traffic-management.md)
* [安全测验](../../quizzes/service-mesh/istio/security.md)
* [可观测性测验](../../quizzes/service-mesh/istio/observability.md)
* [弹性测验](../../quizzes/service-mesh/istio/resilience.md)
* [高级主题测验](../../quizzes/service-mesh/istio/advanced.md)
