# 对比指南

> **最后审阅日期**：2026 年 9 月 11 日
> **适用读者**：架构师、DevOps 工程师和平台工程师

在选择服务网格之前，应先比较实际所需的流量、身份、平台和运维契约。组织规模、功能星级评分或固定的资源开销百分比都不能证明某个方案适用。版本支持和发布渠道也应单独核实，不能从架构对比中推断。

## 目录

### 1. [服务网格方案对比](01-service-mesh-comparison.md)

详细对比涵盖 Istio、Linkerd、Kong Mesh/Kuma 和 Consul Service Mesh。若要同时评估网络与网格能力，也应考虑持续维护的 [Cilium 服务网格指南](../../cilium-service-mesh/README.md)。

请比较数据面和控制面、支持的流量策略、身份与加密、可观测性、Kubernetes/VM 支持、多集群拓扑、生命周期以及商业发行版条款。在相同策略和流量条件下测量资源用量，不要给产品贴上固有的高、中、低等级。

### 2. [Istio 与 VPC Lattice](02-istio-vs-lattice.md)

Istio 是可部署的服务网格，支持 Kubernetes，也提供有文档说明的 VM 集成。VPC Lattice 是 AWS 托管的应用网络服务，可供服务和资源使用，并支持 EC2、容器和 Lambda 等目标。它并不要求所有应用都采用无服务器架构。

请比较协议和路由行为、每个 TLS 边界上的身份、区域连接、各方责任以及实际计费维度。托管网络并不能免除应用、DNS、IAM、目标健康状况或成本方面的运维工作。

### 3. [Sidecar 与 Ambient](03-sidecar-vs-ambient.md)

本指南包含在 EKS 上进行的实测实验，涉及 mTLS、NetworkPolicy、延迟和发布故障。应在结论中保留每项实验所用的实际版本、工作负载、测量时间窗口和原始 503 结果。重试后的客户端可见结果属于另一项测量；重试可能掩盖故障，也可能重复执行非幂等操作。

可依据这些观测结果为目标工作负载设计测试，但它们不能证明 sidecar 与 waypoint 的可靠性存在普遍排名，也不能证明必须按核心、半核心或边缘层级放置工作负载。

## 选择标准

| 需求 | 可评估的候选能力 | 所需证据 |
|---|---|---|
| 精细的 L7 流量管理和策略 | Istio；以及完成所需工作的具体 Linkerd、Kong、Consul 或 Cilium 功能 | 支持的 API、协议行为、生成的配置和升级测试 |
| 专注于 Kubernetes 的服务网格 | Linkerd，或按需限定范围的 Istio 部署 | 实际运维工作量、身份生命周期、功能覆盖和同等负载下的测量结果 |
| 已有 Cilium 网络 | Cilium 的 eBPF 数据面和基于代理的 L7 功能 | 内核/CNI 兼容性、已启用的 L7 功能，以及单独的身份验证和加密要求 |
| AWS 服务/资源互联 | VPC Lattice | 区域网络/端点路径、目标支持、IAM/TLS 契约以及服务/资源所有者的职责 |
| VM 或混合工作负载 | Istio VM 集成、Linkerd 网格扩展、Kong Universal 模式或 Consul 支持的运行时 | 工作负载身份、DNS、IP/API 可达性和运行时专属限制 |
| 多集群或多云 | 所选网格及任何外部网络所支持的拓扑 | 信任边界、配置分发、数据恢复、延迟和传输成本 |
| 深度可观测性 | 所选网格，以及适当的指标、日志和追踪后端 | 实际遥测标签、应用追踪上下文传播、采样、保留期限和访问控制 |

这些只是候选方案，并非自动适用的产品推荐。追踪后端或仪表板是需要额外配置的依赖项；若没有必要的上下文传播或埋点，任何网格都无法生成完整的应用追踪。

## 架构速览

| 方案 | 数据面 | 平台与运维考量 |
|---|---|---|
| Istio | Envoy sidecar；Ambient 使用每节点的 ztunnel，并可选用 Envoy waypoint | 支持 Kubernetes 和有文档说明的 VM 集成；功能和拓扑支持因模式而异；可自行管理或采用供应商发行版 |
| Linkerd | Rust 编写的 linkerd2-proxy | 支持 Kubernetes，也可通过 ExternalWorkload 和兼容的身份/网络配置扩展至非 Kubernetes 工作负载；不能据此说它“不支持 VM” |
| Kong Mesh | Envoy 数据面代理 | 支持 Kubernetes 和 Universal VM/裸机模式；可自行托管，也可使用托管的全局控制面；具体功能因版本/发行版而异 |
| Consul Service Mesh | 使用 Envoy sidecar，并由 Consul 负责服务发现和控制面 | 文档涵盖 Kubernetes、VM 和其他运行时集成；请核实所选版本/发行版及代理兼容性 |
| Cilium | eBPF 网络数据面，以及用于 L7 的 Envoy 等代理 | 核实已启用的组件和平台支持；其 L7 实现并非完全不使用代理 |

Cilium 1.20.1 将带外相互身份验证标为 **Beta**，并通过带外握手完成身份验证。流量加密仍需单独配置 WireGuard/IPsec；该身份验证功能并不等同于自动为每个应用连接建立 Istio 风格的 TLS 会话。还应考虑其文档列出的 Cluster Mesh 和外部 mTLS 限制。

Cilium 1.20.1 还提供独立的 [ztunnel 透明加密 Beta 功能](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/security/network/encryption-ztunnel.rst)，通过 `encryption.type: ztunnel` 选择。该功能提供 TCP 工作负载 mTLS，并要求按命名空间加入；通信两端都必须加入。它不支持 ClusterMesh 和使用 host network 的 Pod。已发布的指南还指出，在此路径上，普通 L4 策略不起作用，目标端口为 HBONE 15008 时除外。这是一种独立的部署选择，有自己的 CA 和引导配置要求。

Linkerd 项目里程碑版本与实际安装的制品是两种不同选择。官方发布页面列出 Linkerd 2.20 及其对应的 edge 版本；开源项目发布 edge 制品，而稳定版制品由供应商提供。请核实发布指南、Kubernetes 兼容性、更新和支持条款，以及可能的订阅费用。不要根据旧文档链接推断所用的制品或发布渠道。

### Istio 与 VPC Lattice

| 维度 | Istio | VPC Lattice |
|---|---|---|
| 部署 | 自行运维控制面/数据面，或选择供应商发行版 | AWS 运维网络服务；用户配置服务/资源、访问权限和目标 |
| 平台 | Kubernetes 和 VM 集成，但需明确网络和信任前提 | AWS 网络，使用受支持的服务目标/资源配置及文档说明的客户端路径 |
| 流量/安全模型 | 按模式区分的网格路由、工作负载身份和策略 | Listener、规则、目标及服务授权策略契约；资源配置使用不同的控制项 |
| 运维 | 用户仍负责代理/控制面生命周期、容量、证书、策略和遥测 | 用户仍负责 IAM/共享、DNS/端点、目标健康状况、控制器集成、配额和遥测 |
| 成本 | 计算、负载均衡器、传输、存储/遥测及可选支持费用 | 适用的预置/使用量计费维度，以及周边基础设施和运维成本 |
| 混合环境集成 | 明确设计网关、信任和身份 | 明确配置区域端点/网络路径及 TLS/身份验证边界；不会自动构成跨云网格联邦 |

本文不提供功能星级评分，也不列出单一供应商的“企业支持”结论：功能可用性、许可和支持取决于实际发行版与合同，列出某项集成也不能证明配置已获认证。

## 迁移指南

### 从 Linkerd 迁移到 Istio

在转换配置之前，先清点流量 API、重试/超时行为、授权、身份、证书和遥测。Linkerd 除 CRD 外也使用注解，因此迁移并不是机械地把基于注解的配置改写为 Istio CRD。应先选取一组服务或一个命名空间，规划并测试共存路径；避免流量捕获重叠，也不要在同一个 Pod 中注入两个网格 sidecar。

### 从 Kubernetes 迁移到服务网格

从尚未满足的需求出发，例如工作负载身份、策略、弹性或可观测性。服务数量本身不是启用网格的门槛。现有 Service、持续维护的 Ingress/Gateway API 实现、NetworkPolicy 和应用埋点可能已经满足需求。应在范围有限的工作负载上测试注入或 Ambient 加入、启动/排空、策略执行和回滚。

### Istio 与 VPC Lattice

混合架构可在集群内使用 Istio，并通过明确配置的服务路径使用 Lattice。应标明每一个 TLS 终止点和调用方身份。经 IAM 身份验证的 Lattice 请求需要按文档配置签名/授权路径；网格 mTLS 本身不会生成 SigV4 身份，也不会端到端传播 SPIFFE 身份。不要让相互竞争的控制器同时管理同一条路由、目标或 DNS 资源。

## 常见问题

<details>
<summary>服务网格是否总是必需的？</summary>

不一定。先确认网络、身份、策略或可观测性方面有哪些需求尚未满足。小型服务也可能需要严格的身份控制；大型系统也可能已在其他位置实现所需控制。应根据实际运维和资源成本评估收益。

</details>

<details>
<summary>应该选择 Istio 还是 Linkerd？</summary>

比较所需的具体路由、安全和可观测性功能、平台支持及运维流程。Linkerd 并非只能提供“基础”功能，也不局限于 Kubernetes 工作负载；Istio 的 sidecar 和 Ambient 模式在资源用量和功能上也有差异。决策前，应运行相同的代表性工作负载，并核查发布和支持选项。

</details>

<details>
<summary>什么情况下可以考虑 VPC Lattice？</summary>

当它支持的服务/资源模型以及 AWS 网络和身份验证契约符合应用需求时，可以考虑使用。混合使用容器、EC2 和 Lambda 可能适用；仅凭“AWS 中心化”或“优先无服务器”不足以做出判断。请确认区域、客户端路径、目标类型、协议、身份和成本假设。

</details>

<details>
<summary>应该预期多少开销？</summary>

这些产品之间不存在通用的延迟、CPU 百分比或每个 Pod 内存开销数值。应在等效的策略、TLS、流量、并发度、节点/代理/waypoint 数量和故障行为下测量。可复现的基准测试应保留原始版本和数据。托管网络仍会增加处理路径、可观测性工作量和计费使用量，并非对基础设施毫无影响。

</details>

<details>
<summary>可以让多个服务网格共存吗？</summary>

不同集群、不同工作负载组，或明确界定的迁移/混合边界可以共存。同一 Pod 或网络路径上的多个流量拦截器可能发生冲突。应明确流量归属、信任/身份转换、遥测和回滚方案，不要假设仅按命名空间隔离就能保证系统互操作。

</details>

## 相关资源

- [Istio 架构](../03-architecture.md)
- [流量管理](../traffic-management/README.md)
- [安全性](../security/README.md)
- [可观测性](../observability/README.md)
- [VPC Lattice](../../../networking/02-vpc-lattice.md)
- [Linkerd](../../linkerd/README.md)
- [Cilium 服务网格](../../cilium-service-mesh/README.md)

## 官方参考资料

- [Istio 文档](https://istio.io/latest/docs/) 和 [VM 集成](https://istio.io/latest/docs/setup/install/virtual-machine/)
- [Linkerd 概述](https://linkerd.io/docs/overview/)、[网格扩展](https://linkerd.io/docs/tasks/adding-non-kubernetes-workloads/) 和[发布渠道](https://linkerd.io/releases/)
- [Kong Mesh](https://developer.konghq.com/mesh/) 和[架构](https://developer.konghq.com/mesh/architecture/)
- [Consul Service Mesh](https://developer.hashicorp.com/consul/docs/connect)
- [Cilium 1.20.1 网格架构源文件](https://raw.githubusercontent.com/cilium/cilium/v1.20.1/Documentation/network/servicemesh/index.rst) 和[相互身份验证状态](https://raw.githubusercontent.com/cilium/cilium/v1.20.1/Documentation/network/servicemesh/mutual-authentication/mutual-authentication.rst)
- [VPC Lattice 组件和责任](https://docs.aws.amazon.com/vpc-lattice/latest/ug/what-is-vpc-lattice.html)
