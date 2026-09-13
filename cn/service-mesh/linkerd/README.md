# Linkerd

> **最后更新**：2026 年 9 月 11 日 · 公共 CLI 示例使用 edge-26.9.1 检查

上游项目发布 edge 制品；稳定发行版及支持生命周期来自厂商。Linkerd 2.20 是功能里程碑，不是下载 CLI 的通用版本字符串。选择确切发行版/发布并检查 Kubernetes、Gateway API 兼容性。本文当前公共示例为 2026 年 9 月 4 日发布的 edge-26.9.1；它修复多集群接受远程凭证 exec 身份验证提供程序，以及可重试目标 IP 冲突处理。参阅[发布](https://github.com/linkerd/linkerd2/releases/tag/edge-26.9.1)和[发布模型](https://linkerd.io/releases/)。

以下条目保留历史发布背景。edge-26.8.2 已测试 Kubernetes 最高版本不会自动扩展厂商稳定发行版支持矩阵。

### 2026 年 8 月更新：edge-26.8.4

edge-26.8.4 于 2026 年 8 月 25 日发布，防护不透明协议处理中 nil ExternalWorkload，让 policy 控制器与集群协商 TLSRoute API 版本，并将 Go 升至 1.26.7。详情参阅[发布说明](https://github.com/linkerd/linkerd2/releases/tag/edge-26.8.4)。

### 2026 年 8 月更新：edge-26.8.2——支持 Gateway API 1.5.1

edge-26.8.2 于 2026 年 8 月 14 日发布，通过 linkerd-kubert 0.27.0 添加 Gateway API 1.5.1 支持，并将已测试 Kubernetes 最高版本提高到 1.36。还包含稳定性修复：移除 destination 控制器中重复 Job informer，并让 policy 控制器在租约监视任务终止时退出。详情参阅[发布说明](https://github.com/linkerd/linkerd2/releases/tag/edge-26.8.2)。

### 2026 年 7 月更新：edge-26.7.1——禁止访问未定义 Service 端口

edge-26.7.1 GitHub 发布于 2026 年 7 月 21 日。包含改变行为的修复：即使存在 ServiceProfile，也拒绝访问目标 Service 未声明的端口。升级前检查实际 Service 端口声明。发布还添加 Gateway API 安装检查。参阅[发布说明](https://github.com/linkerd/linkerd2/releases/tag/edge-26.7.1)。

## 概述

Linkerd 是 CNCF 毕业服务网格，使用 Rust 数据平面代理。CNCF 记录其首次提交于 2016 年，2021 年毕业。应根据实际工作负载评估运维模型、协议支持和资源用量，不要将“简单”或“轻量”视为保证。

### 核心价值主张

| 能力 | 验证内容 |
|---|---|
| 默认工作负载 mTLS | 两端均纳入网格且流量未绕过代理；非网格明文需要显式授权策略 |
| Rust 代理 | 预期连接和流量下的内存/CPU requests、limits 和用量 |
| HTTP/gRPC 路由 | 受支持 Gateway API 类型、附加和协议检测 |
| 运维 | 证书生命周期、高可用、升级兼容性及扩展所有权 |
| 性能 | 工作负载专属延迟/错误/负载测量；无通用 10MB 或亚毫秒承诺 |

## Linkerd 架构概述

| 组件 | 作用 |
|---|---|
| Destination 和 policy 控制器 | 发现端点并向代理分发路由/授权策略 |
| Identity | 验证身份请求，使用配置信任凭证签发短期工作负载证书 |
| Proxy Injector | 修改合格新建 Pod，添加代理 |
| linkerd-proxy | 拦截配置的 TCP 流量，对合格网格路径认证/加密，并提供受支持 L7 行为 |
| 可选扩展/后端 | Viz 指标/仪表板、多集群集成及独立配置的追踪采集/存储 |

此架构不意味着固定内存占用或延迟开销。应针对所选工作负载和配置测量。

## 服务网格比较

| 方面 | Linkerd | Istio | Cilium |
|---|---|---|---|
| 数据平面 | Rust Sidecar | Envoy Sidecar 或 ztunnel 加 waypoint | eBPF 网络，受支持 L7 功能使用 Envoy |
| HTTP 路由 | Gateway API 路由；ServiceProfile 继续支持早期流程 | Istio API 或受支持 Gateway API 附加 | Gateway API 和 Cilium 策略/控制器功能 |
| 安全 | 合格网格 TCP 对等体间自动 mTLS；授权控制其他来源 | 自动 mTLS、入站强制和授权是独立控制 | 对等身份验证和载荷加密须单独评估 |
| 可观测性 | 代理指标加已配置 Viz/其他后端 | 模式专属遥测加已配置后端 | Hubble 和已配置 L7/指标后端 |
| 多集群 | 镜像/联邦及明确信任/网络设置 | 受支持的拓扑专属网格配置 | ClusterMesh 及其平台/网络要求 |
| 选择 | 测试所需功能和运维 | 测试所需功能和运维 | 测试所需功能和运维 |

SMI TrafficSplit 是旧流程，不是当前 Linkerd 路由的完整描述。Linkerd 可通过 Gateway API 按请求属性路由 HTTP/gRPC。没有可复现工作负载及带版本测量，固定内存、p99、人员/复杂度排名不可比较。

## 何时选择 Linkerd

默认 Kubernetes 集成、工作负载身份和受支持 HTTP/gRPC/TCP 行为符合应用需求时，Linkerd 是候选。真实负载下基准测试资源效率和延迟，并规划 CA 轮换、访问策略和升级。仅自动传输加密不是完整零信任或合规方案。

选择网格前验证确切所需路由/过滤/扩展功能。非 HTTP 协议可作为 TCP 代理；不会因此获得 HTTP 级路由或指标。服务器先发/空闲连接可能需要不透明端口或 appProtocol 配置，应用发起 TLS 对 HTTP 检查仍不透明。不透明流量仍经过代理；skip 端口绕过代理。

通过[网格扩展](https://linkerd.io/docs/tasks/adding-non-kubernetes-workloads/)可集成虚拟机和物理机，包括 ExternalWorkload 注册及外部身份/引导路径。并非一概不支持。网络可达性、DNS、代理安装和信任设计增加普通 Pod 注入之外的要求；上游教程的引导简化不是生产设计。

## 文档结构

| 文档 | 描述 |
|---|---|
| [安装和设置](01-installation.md) | 确切版本/兼容性、CLI/Helm、信任凭证、高可用及扩展 |
| [架构](02-architecture.md) | 控制器、代理和证书层次 |
| [流量管理](03-traffic-management.md) | Gateway API、旧 ServiceProfile、重试/超时和流量拆分 |
| [安全](04-security.md) | mTLS 边界、授权和 CA 轮换 |
| [可观测性](05-observability.md) | 指标、Viz、外部后端和追踪 |
| [多集群](06-multi-cluster.md) | 镜像/联邦、网络路径、信任和凭证 |
| [最佳实践](07-best-practices.md) | 运维验证、性能和故障排除 |

## 快速入门

### 1. 选择 CLI 和前提条件

按[安装指南](01-installation.md)选择操作系统/架构和确切版本。验证 CLI 输出匹配目标发行版；不要假定未固定安装器生成旧稳定版。Gateway API CRD 是前提，已安装资源包必须兼容所有使用控制器。

```bash
linkerd version --client
kubectl config current-context
kubectl get crd httproutes.gateway.networking.k8s.io   -o 'jsonpath={.metadata.annotations.gateway\.networking\.k8s\.io/bundle-version}'
linkerd check --pre
```

### 2. 渲染、审核和安装

全新受控实验满足所选 CLI 和前提后，CLI 渲染清单：

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

默认 CLI 设置生成有限寿命信任凭证。不是现成的共享信任多集群设置。可重复长期安装应遵循文档中的 Helm/CA 生命周期流程。本审查检查离线渲染和 CLI 语法，未执行真实安装。

### 3. 添加目标应用

对于选定的现有命名空间和 Deployment，将两处 my-app 替换为实际目标：

```bash
kubectl annotate namespace my-app linkerd.io/inject=enabled
kubectl -n my-app rollout restart deployment/my-app
kubectl -n my-app rollout status deployment/my-app
linkerd check --proxy -n my-app
```

审核现有冲突注解，不自动覆盖。只有新 Pod 接收注入，滚动重启需要工作负载就绪/容量保护。手动注入可针对已审核应用清单；不要将每个在线 Deployment 导出再经 inject/apply 作为全面修复。

### 4. 按需添加 Viz

```bash
linkerd viz install > linkerd-viz.yaml
# Review the extension's backend, resources and retention.
kubectl apply -f linkerd-viz.yaml
linkerd viz check
linkerd viz dashboard
```

Viz 可选，需要自身生命周期。默认指标设置不是通用生产保留/高可用设计。

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

Tap 观察受支持 HTTP 请求事件；不证明每条 TCP 路径、数据包或加密边界。

## 核心概念

### 数据平面代理

Rust linkerd-proxy 与已纳管工作负载并行运行。处理配置的 TCP 路径；skip 端口、非网格端点和平台限制需单独检查。HTTP 级行为要求可见/已检测 HTTP。测量资源用量和延迟，不假定每 Pod 固定占用。

### 服务发现

Destination 和 policy 组件监视 Service/端点状态并提供路由信息。ServiceProfile 和 Gateway API 是不同配置路径，优先级和功能支持因版本而异。确保每个目标 Service 端口都声明；参阅上方历史破坏性变更说明。

### 自动 mTLS

文档中的默认工作负载证书寿命为 24 小时，自动续订。身份关联 Pod 的 ServiceAccount，不是每 Pod 唯一身份。信任锚和签发者凭证有独立生命周期；CLI 默认生成凭证一年后到期，需要规划轮换。

网格 TCP 对等体使用 mTLS，但与非网格对等体之间的流量和 skip 端口不在自动保证内。默认入站策略接受非网格明文；需要拒绝时使用授权策略。多集群通信需要共享信任和明确连接。

## 后续步骤

1. [安装和设置](01-installation.md)
2. [架构](02-architecture.md)
3. [安装测验](../../quizzes/service-mesh/linkerd/installation.md)、[架构测验](../../quizzes/service-mesh/linkerd/architecture.md)、[流量测验](../../quizzes/service-mesh/linkerd/traffic-management.md)
4. [安全测验](../../quizzes/service-mesh/linkerd/security.md)、[可观测性测验](../../quizzes/service-mesh/linkerd/observability.md)、[多集群测验](../../quizzes/service-mesh/linkerd/multi-cluster.md)

## 参考资料

- [Linkerd 文档](https://linkerd.io/docs/overview/)
- [发布分支](https://linkerd.io/releases/)和[安装](https://linkerd.io/docs/tasks/install/)
- [Gateway API](https://linkerd.io/docs/features/gateway-api/)和[请求路由](https://linkerd.io/docs/features/request-routing/)
- [自动 mTLS 及注意事项](https://linkerd.io/docs/features/automatic-mtls/)和 [TCP/协议处理](https://linkerd.io/docs/features/protocol-detection/)
- [CNCF 项目记录](https://www.cncf.io/projects/linkerd/)
- [Linkerd GitHub](https://github.com/linkerd/linkerd2)、[社区](https://slack.linkerd.io/)、[Buoyant 博客](https://buoyant.io/blog)
