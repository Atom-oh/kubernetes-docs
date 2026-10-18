# Linkerd

> **最后更新**：October 16, 2026 · 已使用 edge-26.10.1 检查公开 CLI 示例

上游项目发布 edge 构建；稳定版发行版及其支持生命周期由供应商提供。Linkerd 2.20 是一个功能里程碑，并非下载的 CLI 通用版本号。请选择确切的发行版/版本，并检查其与 Kubernetes 和 Gateway API 的兼容性。此处当前的公开示例为 edge-26.10.1（proxy v2.370.0），于 October 5, 2026 发布。edge-26.9.1 修复了多集群场景下对远程凭证 exec-auth-provider 的接受问题，以及可重试的 destination-IP 冲突处理问题。请参阅[发行说明](https://github.com/linkerd/linkerd2/releases/tag/edge-26.10.1)和[发行版本模型](https://linkerd.io/releases/)。

以下条目保留了历史版本背景。edge-26.8.2 测试的 Kubernetes 最高版本，并不会自动扩展稳定版供应商发行版的支持矩阵。

### 2026 年 8 月更新：edge-26.8.4

edge-26.8.4 于 August 25, 2026 发布，可防止在不透明协议处理期间出现 nil ExternalWorkload，将 policy controller 改为与集群协商 TLSRoute API 版本，并将 Go 升级至 1.26.7。详情请参阅[发行说明](https://github.com/linkerd/linkerd2/releases/tag/edge-26.8.4)。

### 2026 年 8 月更新：edge-26.8.2（支持 Gateway API 1.5.1）

edge-26.8.2 于 August 14, 2026 发布，新增对 Gateway API 1.5.1 的支持（通过 linkerd-kubert 0.27.0），并将测试的 Kubernetes 最高版本提升至 1.36。它还包含稳定性修复：移除 destination controller 中重复的 Job informer，并在 policy controller 的租约监视任务退出时使其退出。详情请参阅[发行说明](https://github.com/linkerd/linkerd2/releases/tag/edge-26.8.2)。

### 2026 年 7 月更新：edge-26.7.1（禁止向未定义的 Service 端口发送请求）

edge-26.7.1 的 GitHub 发行版于 July 21, 2026 发布。其中包含一项会改变行为的修复：即使存在 ServiceProfile，也会拒绝发往 destination Service 未声明端口的请求。升级前请检查实际的 Service 端口声明。此发行版还新增了 Gateway API 安装检查。请参阅[发行说明](https://github.com/linkerd/linkerd2/releases/tag/edge-26.7.1)。

## 概述

Linkerd 是一个 CNCF 毕业项目服务网格，具有 Rust 数据平面代理。CNCF 记录显示，其首次提交发生于 2016 年，并于 2021 年毕业。应根据实际工作负载评估其运维模式、协议支持和资源使用情况，而不要将“简单”或“轻量”视为保证。

### 核心价值主张

| 能力 | 需要验证的内容 |
|---|---|
| 默认工作负载 mTLS | 两端是否都已加入网格，以及流量是否绕过代理；未加入网格的明文流量需要显式授权策略 |
| Rust 代理 | 在预期连接数和流量下的内存/CPU requests、limits 和使用量 |
| HTTP/gRPC 路由 | 支持的 Gateway API 类型、附加方式和协议检测 |
| 运维 | 证书生命周期、高可用性、升级兼容性和扩展所有权 |
| 性能 | 针对工作负载测量延迟/错误/负载；不承诺普遍适用的 10MB 或亚毫秒指标 |

## Linkerd 架构概述

| 组件 | 作用 |
|---|---|
| Destination 和 policy controllers | 发现端点，并向代理分发路由/授权策略 |
| Identity | 验证身份请求，并使用配置的信任凭证签发短期工作负载证书 |
| Proxy Injector | 修改符合条件的新建 Pods，为其添加代理 |
| linkerd-proxy | 拦截已配置的 TCP 流量，对符合条件的网格路径进行身份验证/加密，并提供受支持的 L7 行为 |
| 可选扩展/后端 | Viz 指标/仪表板、多集群集成以及单独配置的跟踪收集/存储 |

此架构并不意味着具有固定的内存占用或延迟开销。请针对选定的工作负载和配置测量这些属性。

## 服务网格比较

| 方面 | Linkerd | Istio | Cilium |
|---|---|---|---|
| 数据平面 | Rust sidecar | Envoy sidecar，或 ztunnel 加 waypoints | 使用 eBPF 网络，并通过 Envoy 提供受支持的 L7 功能 |
| HTTP 路由 | Gateway API routes；仍支持用于较早工作流的 ServiceProfiles | Istio APIs 或受支持的 Gateway API attachment | Gateway API 和 Cilium policy/controller 功能 |
| 安全性 | 符合条件的网格 TCP 对等端之间自动启用 mTLS；其他来源由授权控制 | 自动 mTLS、入站强制执行和授权是彼此独立的控制项 | 必须分别评估对等端身份验证和负载加密 |
| 可观测性 | 代理指标，以及已配置的 Viz/其他后端 | 与模式相关的遥测数据，以及已配置的后端 | Hubble，以及已配置的 L7/指标后端 |
| 多集群 | 镜像/联邦和显式信任/网络设置 | 受支持的特定拓扑网格配置 | ClusterMesh 及其平台/网络要求 |
| 选择 | 测试所需功能和运维事项 | 测试所需功能和运维事项 | 测试所需功能和运维事项 |

SMI TrafficSplit 是一种旧版工作流，并不能完整描述当前 Linkerd 的路由功能。Linkerd 可以通过 Gateway API 根据请求属性路由 HTTP/gRPC。若没有可复现的工作负载和带版本信息的测量数据，固定的内存、p99 和人员配置/复杂度排名就无法比较。

## 何时选择 Linkerd

当 Linkerd 的默认 Kubernetes 集成、工作负载身份以及受支持的 HTTP/gRPC/TCP 行为符合应用需求时，它可以作为候选方案。在真实负载下对资源效率和延迟进行基准测试，并规划 CA 轮换、访问策略和升级。仅有自动传输加密并不能构成完整的零信任或合规计划。

选择网格前，请验证其是否具备所需的路由/过滤/扩展功能。非 HTTP 协议可以通过 TCP 代理；但这并不会让它们获得 HTTP 级路由或指标。服务器优先/空闲连接可能需要配置不透明端口或 appProtocol，而应用发起的 TLS 对 HTTP 检查仍是不透明的。不透明流量仍会经过代理；被跳过的端口则会绕过代理。

可通过[网格扩展](https://linkerd.io/docs/tasks/adding-non-kubernetes-workloads/)集成 VM 和物理机，包括 ExternalWorkload 注册以及外部身份/引导路径。此类集成并非一概不受支持。网络可达性、DNS、代理安装和信任设计会带来普通 Pod 注入之外的额外要求；上游教程中的引导捷径并非生产环境设计。

## 文档结构

| 文档 | 说明 |
|---|---|
| [安装与设置](01-installation.md) | 确切版本/兼容性、CLI/Helm、信任凭证、高可用性和扩展 |
| [架构](02-architecture.md) | 控制器、代理和证书层级 |
| [流量管理](03-traffic-management.md) | Gateway API、旧版 ServiceProfiles、重试/超时和流量拆分 |
| [安全](04-security.md) | mTLS 边界、授权和 CA 轮换 |
| [可观测性](05-observability.md) | 指标、Viz、外部后端和跟踪 |
| [多集群](06-multi-cluster.md) | 镜像/联邦、网络路径、信任和凭证 |
| [最佳实践](07-best-practices.md) | 运维验证、性能和故障排除 |

## 快速入门

### 1. 选择 CLI 和先决条件

请根据所选操作系统/架构和确切版本，遵循[安装指南](01-installation.md)。确认 CLI 输出与预期发行版相符；不要假设未固定版本的安装程序会生成较旧的稳定版。Gateway API CRD 是先决条件，安装的版本包必须与所有使用它的控制器兼容。

```bash
linkerd version --client
kubectl config current-context
kubectl get crd httproutes.gateway.networking.k8s.io   -o 'jsonpath={.metadata.annotations.gateway\.networking\.k8s\.io/bundle-version}'
linkerd check --pre
```

### 2. 渲染、审查并安装

对于使用所选 CLI 和先决条件搭建的新受控实验环境，CLI 可以渲染清单：

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

默认 CLI 设置会生成有效期有限的信任凭证。这并不是现成的共享信任多集群设置。对于可重复的长期安装，请遵循文档中的 Helm/CA 生命周期流程。本次审查检查了离线渲染和 CLI 语法，并未进行实时安装。

### 3. 添加目标应用

对于已存在的目标 namespace 和 Deployment，请将两个 my-app 名称替换为实际目标：

```bash
kubectl annotate namespace my-app linkerd.io/inject=enabled
kubectl -n my-app rollout restart deployment/my-app
kubectl -n my-app rollout status deployment/my-app
linkerd check --proxy -n my-app
```

如遇到现有冲突注解，请先审查，而不是自动覆盖。只有新建的 Pods 会被注入；滚动重启需要做好工作负载就绪状态/容量保障。也可以对已审查的应用清单进行手动注入；不要将每个在线 Deployment 都通过 inject/apply 流程重新处理，作为一刀切的修复办法。

### 4. 按需添加 Viz

```bash
linkerd viz install > linkerd-viz.yaml
# Review the extension's backend, resources and retention.
kubectl apply -f linkerd-viz.yaml
linkerd viz check
linkerd viz dashboard
```

Viz 是可选组件，需要单独管理其生命周期。其默认指标设置并非通用的生产环境数据保留/高可用方案。

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

Tap 可以观察受支持的 HTTP 请求事件；它不能证明每条 TCP 路径、每个数据包或每个加密边界的情况。

## 核心概念

### 数据平面代理

Rust linkerd-proxy 与已加入网格的工作负载并行运行。它处理已配置的 TCP 路径；跳过的端口、未加入网格的端点和平台限制需要分别检查。L7 行为要求 HTTP 可见或可检测。请测量资源使用量和延迟，而不要假定每个 Pod 的占用量恒定。

### 服务发现

Destination 和 policy 组件会监视 Service/端点状态并提供路由信息。ServiceProfiles 和 Gateway API 是不同的配置路径，其优先级和功能支持因版本而异。确保所有目标 Service 端口都已声明；请参阅上文的历史性重大变更说明。

### 自动 mTLS

文档说明的默认工作负载证书有效期为 24 小时，并会自动续期。身份与 Pod 的 ServiceAccount 关联，而不是为每个 Pod 单独创建唯一身份。信任锚和签发者凭证各自具有独立的生命周期；默认 CLI 生成的凭证会在一年后过期，需要提前规划轮换。

加入网格的 TCP 对等端之间使用 mTLS，但与未加入网格的对等端之间的流量以及被跳过端口的流量不在此自动保障范围内。默认入站策略接受未加入网格的明文流量；如果必须拒绝此类流量，请使用授权策略。多集群通信需要共享信任和显式连通性。

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
