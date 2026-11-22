# Linkerd

> **最后更新**：2026年11月21日 · 公共 CLI 示例已使用 edge-26.10.1 检查

上游项目发布 edge 构件；稳定版发行版及其支持生命周期由供应商提供。Linkerd 2.20 是一个功能里程碑，并非下载的 CLI 的通用版本号。请选择确切的发行版/版本，并检查其与 Kubernetes 和 Gateway API 的兼容性。此处当前的公共示例为 edge-26.10.1（proxy v2.370.0），于2026年10月5日发布。edge-26.9.1 修复了多集群中对远程凭据 exec-auth-provider 的接受问题，以及可重试的目标 IP 冲突处理问题。请参阅[发行版本](https://github.com/linkerd/linkerd2/releases/tag/edge-26.10.1)和[发行模式](https://linkerd.io/releases/)。

以下条目保留了历史发行版背景。edge-26.8.2 测试过的最高 Kubernetes 版本，不会自动扩展稳定版供应商发行版的支持矩阵。

### 2026年10月更新：edge-26.10.2

edge-26.10.2 于2026年10月29日发布，它提高了策略控制器的 gRPC HTTP/2 连接窗口以避免 GOAWAY，确保连接 tap API 服务器的客户端提供 TLS，随附 proxy v2.372.0，将构建所用的 Go 版本升级到 1.26.9，并将 proxy-init 升级到 v2.4.11、将 CNI 插件升级到 v1.7.1。详情请参阅[发行说明](https://github.com/linkerd/linkerd2/releases/tag/edge-26.10.2)。

### 2026年8月更新：edge-26.8.4

edge-26.8.4 于2026年8月25日发布，它在不透明协议处理过程中防范 nil ExternalWorkload，让策略控制器与集群协商 TLSRoute API 版本，并将 Go 升级到 1.26.7。详情请参阅[发行说明](https://github.com/linkerd/linkerd2/releases/tag/edge-26.8.4)。

### 2026年8月更新：edge-26.8.2（支持 Gateway API 1.5.1）

edge-26.8.2 于2026年8月14日发布，新增对 Gateway API 1.5.1 的支持（通过 linkerd-kubert 0.27.0），并将测试过的最高 Kubernetes 版本提升至 1.36。它还包含稳定性修复：移除 destination 控制器中的重复 Job informer，并确保策略控制器在其租约监视任务退出时退出。详情请参阅[发行说明](https://github.com/linkerd/linkerd2/releases/tag/edge-26.8.2)。

### 2026年7月更新：edge-26.7.1（禁止向未定义的 Service 端口发送请求）

edge-26.7.1 的 GitHub 发行版于2026年7月21日发布。它包含一项会改变行为的修复：即使存在 ServiceProfile，也会拒绝向目标 Service 未声明的端口发送请求。升级前请检查实际的 Service 端口声明。此发行版还新增了 Gateway API 安装检查。请参阅[发行说明](https://github.com/linkerd/linkerd2/releases/tag/edge-26.7.1)。

## 概述

Linkerd 是一个 CNCF 毕业项目服务网格，采用 Rust 数据平面代理。CNCF 记录显示，该项目于2016年首次提交代码，并于2021年毕业。应根据实际工作负载评估其运维模式、协议支持和资源用量，不要将“简单”或“轻量”视为保证。

### 核心价值主张

| 能力 | 需要核实的事项 |
|---|---|
| 默认工作负载 mTLS | 两端都已加入网格，且流量未绕过代理；未加入网格的明文流量需要显式授权策略 |
| Rust 代理 | 在预期连接数和流量下的内存/CPU requests、limits 和用量 |
| HTTP/gRPC 路由 | 支持的 Gateway API 类型、挂载方式和协议检测 |
| 运维 | 证书生命周期、高可用性、升级兼容性和扩展归属 |
| 性能 | 针对具体工作负载测量延迟/错误/负载；不存在普遍适用的 10MB 或亚毫秒承诺 |

## Linkerd 架构概览

| 组件 | 作用 |
|---|---|
| Destination 和策略控制器 | 发现端点，并向代理分发路由/授权策略 |
| Identity | 验证身份请求，并使用已配置的信任凭据颁发短期工作负载证书 |
| Proxy Injector | 修改符合条件的新建 Pod，以添加代理 |
| linkerd-proxy | 拦截已配置的 TCP 流量，对符合条件的网格流量路径进行身份验证/加密，并提供受支持的 L7 行为 |
| 可选扩展/后端 | Viz 指标/仪表板、多集群集成，以及单独配置的跟踪数据收集/存储 |

此架构并不意味着内存占用或延迟开销固定不变。请针对所选工作负载和配置测量这些指标。

## 服务网格比较

| 方面 | Linkerd | Istio | Cilium |
|---|---|---|---|
| 数据平面 | Rust sidecar | Envoy sidecar，或 ztunnel 加 waypoint | 基于 eBPF 的网络，并使用 Envoy 实现受支持的 L7 功能 |
| HTTP 路由 | Gateway API 路由；较早的工作流仍支持 ServiceProfiles | Istio API 或受支持的 Gateway API 挂载方式 | Gateway API 和 Cilium 策略/控制器功能 |
| 安全 | 符合条件且已加入网格的 TCP 对等端之间自动使用 mTLS；其他来源由授权控制 | 自动 mTLS、入站强制执行和授权是不同的控制措施 | 必须分别评估对等身份验证和有效载荷加密 |
| 可观测性 | 代理指标，以及已配置的 Viz/其他后端 | 按模式提供遥测，并使用已配置的后端 | Hubble 以及已配置的 L7/指标后端 |
| 多集群 | 镜像/联邦，以及显式的信任/网络设置 | 受支持的、依拓扑而定的网格配置 | ClusterMesh 及其平台/网络要求 |
| 选择 | 测试所需的功能和运维方式 | 测试所需的功能和运维方式 | 测试所需的功能和运维方式 |

SMI TrafficSplit 是一种旧版工作流，并不能完整描述当前的 Linkerd 路由功能。Linkerd 可以通过 Gateway API 根据请求属性路由 HTTP/gRPC 流量。如果没有可复现的工作负载和带版本信息的测量数据，固定的内存、p99 和人员配置/复杂性排名就无法进行比较。

## 何时选择 Linkerd

如果 Linkerd 的默认 Kubernetes 集成、工作负载身份以及受支持的 HTTP/gRPC/TCP 行为符合应用需求，它就值得考虑。请在真实负载下对资源效率和延迟进行基准测试，并规划 CA 轮换、访问策略和升级。仅有自动传输加密并不构成完整的零信任或合规方案。

选择服务网格前，请验证其是否具备所需的路由/过滤器/可扩展性功能。非 HTTP 协议可以通过 TCP 代理；但这并不会为它们提供 HTTP 级别的路由或指标。服务端先发送数据/空闲连接可能需要配置 opaque-port 或 appProtocol，而应用发起的 TLS 对 HTTP 检查仍不可见。不透明流量仍会经过代理；被跳过的端口则会绕过代理。

可通过[网格扩展](https://linkerd.io/docs/tasks/adding-non-kubernetes-workloads/)集成 VM 和物理机，包括注册 ExternalWorkload 以及外部身份/引导流程。这并非一概不受支持。网络可达性、DNS、代理安装和信任设计会带来普通 Pod 注入之外的额外要求；上游教程中的引导简化做法并非生产环境设计。

## 文档结构

| 文档 | 描述 |
|---|---|
| [安装与设置](01-installation.md) | 确切的发行版/版本及兼容性、CLI/Helm、信任凭据、高可用性和扩展 |
| [架构](02-architecture.md) | 控制器、代理和证书层级 |
| [流量管理](03-traffic-management.md) | Gateway API、旧版 ServiceProfiles、重试/超时和流量拆分 |
| [安全](04-security.md) | mTLS 边界、授权和 CA 轮换 |
| [可观测性](05-observability.md) | 指标、Viz、外部后端和跟踪 |
| [多集群](06-multi-cluster.md) | 镜像/联邦、网络路径、信任和凭据 |
| [最佳实践](07-best-practices.md) | 运维验证、性能和故障排除 |

## 快速入门

### 1. 选择 CLI 和先决条件

按照[安装指南](01-installation.md)，根据所选操作系统/架构和确切发行版进行安装。确认 CLI 输出与预期的发行版一致；不要假定未固定版本的安装程序会安装较早的稳定版。Gateway API CRD 是一项先决条件，已安装的资源包必须与使用它的每个控制器兼容。

```bash
linkerd version --client
kubectl config current-context
kubectl get crd httproutes.gateway.networking.k8s.io   -o 'jsonpath={.metadata.annotations.gateway\.networking\.k8s\.io/bundle-version}'
linkerd check --pre
```

### 2. 渲染、审查并安装

对于使用所选 CLI 和先决条件搭建的全新、受控实验环境，CLI 可以渲染清单：

```bash
set -euo pipefail
linkerd install --crds > linkerd-crds.yaml
# Review CRD ownership/version before applying.
kubectl apply -f linkerd-crds.yaml
linkerd install > linkerd-control-plane.yaml
# Review trust credentials and deployment settings before applying.
kubectl apply -f linkerd-control-plane.yaml
linkerd check
```

默认 CLI 设置会生成有效期有限的信任凭据。这不是现成的共享信任多集群配置。如需可重复部署且长期运行的安装，请遵循文档中的 Helm/CA 生命周期流程。此次审查检查了离线渲染和 CLI 语法，并未进行实时安装。

### 3. 添加目标应用

对于已选定的现有命名空间和 Deployment，请将两个 my-app 名称都替换为实际目标：

```bash
kubectl annotate namespace my-app linkerd.io/inject=enabled
kubectl -n my-app rollout restart deployment/my-app
kubectl -n my-app rollout status deployment/my-app
linkerd check --proxy -n my-app
```

如果已有冲突注解，请先审查，不要自动覆盖。只有新建的 Pod 才会注入代理；滚动重启需要具备适用于该工作负载的就绪性/容量保障。也可以对经过审查的应用清单进行手动注入；不要将每个现有 Deployment 一概通过 inject/apply 流程重新处理来解决问题。

### 4. 按需添加 Viz

```bash
linkerd viz install > linkerd-viz.yaml
# Review the extension's backend, resources and retention.
kubectl apply -f linkerd-viz.yaml
linkerd viz check
linkerd viz dashboard
```

Viz 是可选组件，需要单独管理其生命周期。其默认指标设置并非普遍适用的生产环境数据保留/高可用设计。

## 检查 Linkerd 组件状态

```bash
# Core installation/control-plane checks.
linkerd check
# Data-plane proxy checks in the selected namespace.
linkerd check --proxy -n my-app
# Requires the configured Viz extension.
linkerd viz stat deploy -n my-app
linkerd viz tap deploy/my-app -n my-app
```

Tap 可以观测受支持的 HTTP 请求事件；它并不能证明所有 TCP 路径、数据包或加密边界的情况。

## 核心概念

### 数据平面代理

Rust 编写的 linkerd-proxy 与已加入网格的工作负载并行运行。它会处理已配置的 TCP 路径；跳过的端口、未加入网格的端点和平台限制都必须单独检查。HTTP 级别的行为要求 HTTP 可见或可被检测到。请测量资源用量和延迟，而不要假设每个 Pod 的占用固定不变。

### 服务发现

Destination 和策略组件会监视 Service/端点状态，并提供路由信息。ServiceProfiles 和 Gateway API 是不同的配置路径，其优先级和功能支持因版本而异。确保每个目标 Service 端口都已声明；请参阅上文的历史重大变更说明。

### 自动 mTLS

文档所述的默认工作负载证书有效期为24小时，并会自动续期。身份与 Pod 的 ServiceAccount 关联，并非每个 Pod 都有独立身份。信任锚和颁发者凭据各有不同的生命周期；默认由 CLI 生成的凭据会在一年后过期，因此需要提前规划轮换。

已加入网格的 TCP 对等端之间会使用 mTLS，但与未加入网格的对等端通信，以及通过被跳过端口传输的流量，不在此自动保障范围内。默认入站策略会接受未加入网格的明文流量；如果必须拒绝此类流量，请使用授权策略。多集群通信需要共享信任和显式连通性。

## 后续步骤

1. [安装与设置](01-installation.md)
2. [架构](02-architecture.md)
3. [安装测验](../../quizzes/service-mesh/linkerd/installation.md)、[架构测验](../../quizzes/service-mesh/linkerd/architecture.md)、[流量测验](../../quizzes/service-mesh/linkerd/traffic-management.md)
4. [安全测验](../../quizzes/service-mesh/linkerd/security.md)、[可观测性测验](../../quizzes/service-mesh/linkerd/observability.md)、[多集群测验](../../quizzes/service-mesh/linkerd/multi-cluster.md)

## 参考资料

- [Linkerd 文档](https://linkerd.io/docs/overview/)
- [发行渠道](https://linkerd.io/releases/)和[安装](https://linkerd.io/docs/tasks/install/)
- [Gateway API](https://linkerd.io/docs/features/gateway-api/)和[请求路由](https://linkerd.io/docs/features/request-routing/)
- [自动 mTLS 及注意事项](https://linkerd.io/docs/features/automatic-mtls/)和[TCP/协议处理](https://linkerd.io/docs/features/protocol-detection/)
- [CNCF 项目记录](https://www.cncf.io/projects/linkerd/)
- [Linkerd GitHub](https://github.com/linkerd/linkerd2)、[社区](https://slack.linkerd.io/)、[Buoyant 博客](https://buoyant.io/blog)
