# 第 1 部分：简介

> **已审查的基线版本**：Cilium 1.20.2 / Cilium CLI 0.20.1 / Hubble CLI 1.20.2。**最后更新**：October 15, 2026

## 实验环境设置

使用隔离且已准备好的 Kubernetes 环境。Cilium 1.20 将 Kubernetes **1.33–1.36** 列为已测试版本。节点需要使用内核 **5.10+** 的 AMD64/AArch64 Linux，或使用有文档说明的等效环境，例如 RHEL 8.10 回移的 4.18 内核。kind/minikube VM 或容器使用其节点/VM 内核；仅凭工作站的 OS 名称不能确定兼容性。特定功能的要求仍然适用。

使用与 API server 相差不超过一个次要版本的 kubectl。按[主指南](README.md)所述安装与正确 OS/架构匹配的 Cilium CLI 和 Hubble CLI 资源，并验证校验和。Helm 可用于渲染/审查配置；本次审查使用 Helm 3.21.3。不要反复下载未经校验的 `latest` AMD64 版本，也不要在每个章节中重新安装该版本。

### 使用所选配置文件一次性安装

EKS ENI、VPC CNI 链式配置以及普通 cluster-pool 配置具有不同的前提条件；请参阅[主指南](README.md)。以下实验值是**普通 IPv4 cluster-pool 替代方案**，其中 kube-proxy 和 DNS 已正常运行，并且已准备好一个 CNI 所有者。它们不是 EKS 迁移方案。请验证 Pod CIDR 不与 Service、节点或已连接网络的范围重叠。

保存为 `cilium-lab-values.yaml`：

```yaml
routingMode: tunnel
tunnelProtocol: vxlan
kubeProxyReplacement: false
ipv4:
  enabled: true
ipv6:
  enabled: false
ipam:
  mode: cluster-pool
  operator:
    clusterPoolIPv4PodCIDRList:
    - 10.244.0.0/16
    clusterPoolIPv4MaskSize: 24
hubble:
  enabled: true
  relay:
    enabled: true
  ui:
    enabled: true
  metrics:
    enabled:
    - dns
    - drop
    - tcp
    - flow
    - icmp
    - httpV2
```

```bash
CILIUM_LAB_CONTEXT=replace-with-nonproduction-context
kubectl --context "$CILIUM_LAB_CONTEXT" get nodes -o wide
cilium version --client

# Fresh installation only, after preparing the cluster/CNI ownership and values.
cilium install --context "$CILIUM_LAB_CONTEXT" --version 1.20.2 \
  --values cilium-lab-values.yaml
cilium status --context "$CILIUM_LAB_CONTEXT" --wait
```

如果 Cilium 已安装，请检查其版本/配置并遵循其所有者的升级流程。安装/状态命令以及后续连通性测试并不能证明生产环境兼容性；本次审查未配置任何集群。

## 什么是 Cilium？

Cilium 通过 Linux eBPF 数据平面和 Kubernetes 集成提供网络、安全性和可观测性。它提供端点策略、依赖模式的 IPAM/路由、Service 处理以及 Hubble 流量可见性。Docker libnetwork 集成已在 1.20 中移除；不应将 Kubernetes、Docker 和 Mesos 视为可互换的当前安装目标。

### 核心组件和功能

| 组件 / 功能 | 角色和限定条件 |
| --- | --- |
| Cilium Agent | 每个节点上的端点和数据平面管理；它不负责所有主机/网络功能 |
| Cilium Operator | 集群级别的分配/身份/控制器工作；支持多个副本，并在适用时使用领导者选举。经审查的 chart 默认使用两个副本 |
| eBPF | 内核挂载点上的程序/映射，受验证和功能要求限制；必须测量性能 |
| L3/L4 和 L7 策略 | L7 需要受支持的 Envoy/DNS proxy 路径；面向 Kafka 的 L7 策略已在 1.20 中移除，而 L4 规则仍可管理 Kafka 连接 |
| kube-proxy 替代 | 可选的 Service 处理；DSR、Maglev 和 XDP 各有其自身的配置/拓扑限制 |
| 加密 | `encryption.type` 选择 `ipsec`、`wireguard` 或 beta 版 `ztunnel`；ztunnel 工作负载 mTLS 有其自身的注册、引导、流量和策略前提条件 |
| Hubble | 网络/proxy 流量观测和服务地图，并非自动的端到端应用程序追踪 |
| ClusterMesh / BGP | ClusterMesh 需要身份、信任和网络可达性；BGP 宣告路由，但不会配置集群内部路由 |

组件关系如下：kubelet 通过 **CRI** 请求 Pod sandbox 操作；容器运行时调用已配置的 **CNI plugin**；Cilium 协调端点设置，Agent 配置数据平面。CNI 不是逐数据包转发跳点。Envoy 处理已配置的 L7 proxy 流量，而 Hubble 独立于 Prometheus 指标抓取公开流量事件。

### 安全身份

安全身份是在相关分配范围内为端点的**与安全相关的标签集合**分配的数字标识符。这些标签经过筛选/配置，并且可以包含从 namespace 派生的标签。仅具有相同的 `app` 标签并不能保证跨 namespace 或集群具有相同身份。数字 ID 不是永久且全局有意义的哈希，也不是 Pod IP。其他端点类型也使用身份。

## 容器网络基础

主机网络共享主机网络 namespace。bridge 在主机上连接接口；overlay 在 underlay 之上封装流量。原生路由依赖 underlay 能够到达 Pod 地址。这些概念可以共存，不应与选择 eBPF 还是 Netfilter 实现混淆。

运维问题包括地址容量、路由/MTU、Service 行为、租户策略、可观测性和故障恢复。网络模型本身并不能决定性能或安全性。

## 理解 CNI

CNI 是用于容器网络配置的 CNCF 规范/库/plugin 生态系统。plugin 以 JSON 交换配置/结果，并且可以将地址分配委托给 IPAM plugin。CNI 的设置/移除约定不同于 CRI，后者由 kubelet 用于与容器运行时通信。自 Kubernetes 1.24 起，kubelet 不再负责已移除的 `--network-plugin`/`--cni-bin-dir` 配置标志。

| 项目 | 相关区别 |
| --- | --- |
| Cilium | Linux eBPF 数据平面、多种路由/IPAM 模式、由 proxy 辅助的 L7 策略和 Hubble |
| Calico | Linux Iptables/Nftables/BPF 和受支持的 Windows HNS；OSS WireGuard、分阶段策略和单独配置的 L7 集成 |
| Flannel | VXLAN/host-gw/WireGuard 等连通性后端；可由其可选 chart controller 或其他实现提供策略 |
| AWS VPC CNI | VPC 地址分配/网络；受支持的 EC2 Linux 节点上的原生策略，以及单独的 SG-for-Pods 控制 |
| Weave Net | 原始 `weaveworks/weave` 仓库已归档；应将其视为历史选项，并单独检查任何拟议的维护中发行版 |

请参阅[当前比较](README.md)以了解支持边界。不要将无边界的 Kubernetes 兼容性或“非常高/高/中”等性能排名作为部署证据。Service mesh 是可选集成，而不是普通 Pod 网络的前提条件。

## 实验：范围受限的 L4 策略

使用所选 context 和专用 namespace。此示例定义策略；它**不会**部署应用程序服务器或客户端镜像。请准备由 controller 管理的测试工作负载，并使用已批准的镜像/工具：

- 一个标记为 `app=backend`、监听 TCP 8080 的 backend Pod。
- 一个标记为 `app=frontend` 的 frontend Pod，以及另一个具有不同标签且配备适当测试客户端的客户端。
- 普通的受管理 Pod 接口、默认标签处理、已知的 DNS/Service 配置，以及没有会使预期隔离失效的其他匹配允许策略。

将 namespace 定义保存为 `cilium-intro-namespace.yaml`，应用它，然后准备测试工作负载：

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: cilium-intro-demo
```

```bash
kubectl --context "$CILIUM_LAB_CONTEXT" apply -f cilium-intro-namespace.yaml
```

将以下策略保存为 `cilium-intro-policy.yaml`：

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: allow-frontend-backend
  namespace: cilium-intro-demo
spec:
  endpointSelector:
    matchLabels:
      k8s:app: backend
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:app: frontend
        k8s:io.kubernetes.pod.namespace: cilium-intro-demo
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
```

```bash
kubectl --context "$CILIUM_LAB_CONTEXT" get pods -n cilium-intro-demo --show-labels
kubectl --context "$CILIUM_LAB_CONTEXT" apply -f cilium-intro-policy.yaml
kubectl --context "$CILIUM_LAB_CONTEXT" get cnp -n cilium-intro-demo
```

在满足这些前提条件且没有额外匹配允许策略的情况下，预期的**常规 Pod 到 Pod 入站**结果如下：

| 源 / 目标 | 预期结果 |
| --- | --- |
| 同 namespace frontend → backend TCP 8080 | 允许 |
| 其他客户端标签 → backend TCP 8080 | 拒绝 |
| Frontend → backend 另一端口/协议 | 此策略不允许 |
| 来自另一 namespace 的相同 app 标签 | 此策略不允许 |

在策略实现后验证正向和负向连接。其他允许/拒绝策略、主机流量和探针都可能改变实际结果。此入站规则不会限制 frontend 出站流量，也不提供 HTTP 方法/路径过滤。请检查实际流量和端点状态，而不是假定 API 被接受就等于得到执行。

`cilium connectivity test` 是一个额外的测试运行程序，会创建工作负载和策略。仅在具有所需权限且经过审查的测试环境中运行它；它不是只读的状态命令。对于独立的性能运行程序，请使用 `cilium connectivity perf`；进行基准测试时，请保留实际的版本/拓扑/结果。

## 参考资料和后续步骤

- [Cilium 要求和设置](README.md)
- [CNI 项目](https://github.com/containernetworking/cni)
- [Kubernetes 网络 plugin 和运行时所有权](https://kubernetes.io/docs/concepts/extend-kubernetes/compute-storage-net/network-plugins/)
- [Kubernetes 客户端版本偏差](https://kubernetes.io/releases/version-skew-policy/)
- [Cilium 身份和术语](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/gettingstarted/terminology.rst)
- [原始 Weave 仓库元数据](https://api.github.com/repos/weaveworks/weave)

继续阅读 [eBPF](02-ebpf.md)，或通过[简介测验](../../quizzes/networking/cilium/01-introduction-quiz.md)测试你的理解。