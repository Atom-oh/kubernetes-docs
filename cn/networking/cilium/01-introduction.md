# 第 1 部分：简介

> **已审核基线**：Cilium 1.20.3 / Cilium CLI 0.20.1 / Hubble CLI 1.20.2。**最后更新**：October 16, 2026

## 实验环境设置

请使用隔离且已准备好的 Kubernetes 环境。Cilium 1.20 将 Kubernetes **1.33–1.36** 列为已测试版本。节点需要运行 AMD64/AArch64 Linux，内核版本为 **5.10+**；或者使用文档中列出的等效环境，例如带回移 4.18 内核的 RHEL 8.10。kind/minikube 虚拟机或容器使用其节点/虚拟机的内核；仅凭工作站的操作系统名称无法确定兼容性。具体功能仍需满足各自的要求。

使用与 API server 版本相差不超过一个次要版本的 kubectl。按照[主指南](README.md)中的说明，安装适用于正确操作系统/架构的 Cilium CLI 和 Hubble CLI 资源，并验证校验和。Helm 可用于渲染/审查配置；本次审核使用的是 Helm 3.21.3。不要重复下载未经校验的 `latest` AMD64 版本，也不要在每章中重新安装发行版。

### 使用选定配置文件安装一次

EKS ENI、VPC CNI chaining 和普通 cluster-pool 配置的前置条件各不相同；请参阅[主指南](README.md)。以下实验值是**普通 IPv4 cluster-pool 方案**，假设 kube-proxy 和 DNS 已正常工作，且集群已有一个已准备好的 CNI 所有者。这不是 EKS 迁移方案。请确认 Pod CIDR 不与 Service、节点或互联网络范围重叠。

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
cilium install --context "$CILIUM_LAB_CONTEXT" --version 1.20.3 \
  --values cilium-lab-values.yaml
cilium status --context "$CILIUM_LAB_CONTEXT" --wait
```

如果已安装 Cilium，请检查其版本/配置，并遵循其所有者的升级流程。安装/状态命令以及后续连通性测试，不能证明其适用于生产环境；本次审核未配置任何集群。

## 什么是 Cilium？

Cilium 通过 Linux eBPF 数据平面和 Kubernetes 集成提供网络、安全和可观测性功能。它提供端点策略、依赖模式的 IPAM/路由、Service 处理以及 Hubble 流可见性。Docker libnetwork 集成已在 1.20 中移除；不应将 Kubernetes、Docker 和 Mesos 描述为当前可互换的安装目标。

### 核心组件和功能

| 组件 / 功能 | 作用和说明 |
| --- | --- |
| Cilium Agent | 管理每个节点上的端点和数据平面；它并不负责所有主机/网络功能 |
| Cilium Operator | 负责集群级别的分配/身份/控制器工作；支持多个副本，并在适用时使用领导者选举。经审核的 chart 默认使用两个副本 |
| eBPF | 在内核钩子处运行程序/映射，受验证和功能要求限制；必须进行性能测量 |
| L3/L4 和 L7 策略 | L7 需要受支持的 Envoy/DNS 代理路径；Kafka 感知型 L7 策略已在 1.20 中移除，但 L4 规则仍可管理 Kafka 连接 |
| kube-proxy replacement | 可选的 Service 处理方式；DSR、Maglev 和 XDP 各有自身的配置/拓扑限制 |
| 加密 | `encryption.type` 用于选择 `ipsec`、`wireguard` 或 beta 版 `ztunnel`；ztunnel 工作负载 mTLS 有自身的注册、引导、流量和策略前置条件 |
| Hubble | 用于观察网络/代理流量并显示服务映射，不会自动提供端到端应用跟踪 |
| ClusterMesh / BGP | ClusterMesh 需要身份、信任和网络可达性；BGP 会通告路由，但不会配置集群内部路由 |

组件之间的关系如下：kubelet 通过 **CRI** 请求 Pod sandbox 操作；容器运行时调用已配置的 **CNI 插件**；Cilium 协调端点设置，agent 对数据平面进行编程。CNI 不是逐数据包转发路径中的一跳。Envoy 处理已配置的 L7 代理流量，而 Hubble 单独提供流事件，与 Prometheus 指标抓取相互独立。

### 安全身份

安全身份是为端点的**安全相关标签集**分配的数字标识符，其范围由相关的分配作用域决定。这些标签经过筛选/配置，可包含根据命名空间派生的标签。仅有相同的 `app` 标签，并不能保证不同命名空间或集群中的身份相同。该数字 ID 不是永久且具有全局意义的哈希，也不是 Pod IP。其他类型的端点也会使用身份。

## 容器网络基础知识

主机网络使用主机的网络命名空间。网桥连接同一主机上的接口；覆盖网络则通过底层网络封装流量。原生路由依赖底层网络能够到达 Pod 地址。这些概念可以共存，不应与选择 eBPF 还是 Netfilter 实现混为一谈。

运维问题包括地址容量、路由/MTU、Service 行为、租户策略、可观测性和故障恢复。网络模型本身无法决定性能或安全性。

## 了解 CNI

CNI 是用于容器网络配置的 CNCF 规范/库/插件生态系统。插件通过 JSON 交换配置/结果，也可以委托 IPAM 插件分配地址。CNI 的设置/移除契约不同于 CRI；kubelet 使用 CRI 与容器运行时通信。自 Kubernetes 1.24 起，kubelet 不再管理已移除的 `--network-plugin`/`--cni-bin-dir` 配置标志。

| 项目 | 相关区别 |
| --- | --- |
| Cilium | Linux eBPF 数据平面、多种路由/IPAM 模式、代理辅助的 L7 策略和 Hubble |
| Calico | Linux Iptables/Nftables/BPF 以及受支持的 Windows HNS；OSS WireGuard、分阶段策略和单独配置的 L7 集成 |
| Flannel | VXLAN/host-gw/WireGuard 等连接后端；可通过其可选的 chart 控制器或其他实现提供策略 |
| AWS VPC CNI | VPC 地址分配/网络；在受支持的 EC2 Linux 节点上提供原生策略，并通过单独的 SG-for-Pods 控制 |
| Weave Net | 原始的 `weaveworks/weave` 仓库已归档；请将其视为历史选项，并单独核实任何拟使用的维护中发行版 |

支持范围请参阅[当前对比](README.md)。不要将没有边界的 Kubernetes 兼容性声明或“非常高/高/中”的性能评级作为部署依据。Service mesh 是可选集成，并非普通 Pod 网络的前置条件。

## 实验：范围限定的 L4 策略

使用选定的 context 和专用命名空间。此示例定义策略，但**不会**部署应用服务器或客户端镜像。请准备由控制器管理的测试工作负载，并使用已批准的镜像/工具：

- 一个标记为 `app=backend`、监听 TCP 8080 的后端 Pod。
- 一个标记为 `app=frontend` 的前端 Pod，以及另一个具有不同标签的客户端；两者都应配备合适的测试客户端。
- 使用普通的托管 Pod 接口、默认标签处理方式、已知的 DNS/Service 配置，并且没有其他匹配的允许策略破坏预期的隔离效果。

将命名空间定义保存为 `cilium-intro-namespace.yaml` 并应用，然后准备测试工作负载：

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

满足上述前置条件，且没有其他匹配的允许策略时，预期的**普通 Pod 到 Pod 入站流量**结果如下：

| 源 / 目标 | 预期结果 |
| --- | --- |
| 同一命名空间中的 frontend → backend TCP 8080 | 允许 |
| 其他客户端标签 → backend TCP 8080 | 拒绝 |
| Frontend → backend 的其他端口/协议 | 此策略不允许 |
| 来自其他命名空间的相同 app 标签 | 此策略不允许 |

策略生效后，验证允许和拒绝的连接。其他允许/拒绝策略、主机流量和探测可能改变实际结果。此入站规则不会限制 frontend 的出站流量，也不会提供 HTTP 方法/路径筛选。请检查实际流量和端点状态，不要假设 API 接受策略就等同于策略已生效。

`cilium connectivity test` 是一个额外的测试运行器，会创建工作负载和策略。只有在经过审核且具备所需权限的测试环境中运行；它不是只读状态命令。性能测试请使用独立的性能运行器 `cilium connectivity perf`，并在基准测试中保留实际版本/拓扑/结果。

## 参考资料和后续步骤

- [Cilium 要求和设置](README.md)
- [CNI 项目](https://github.com/containernetworking/cni)
- [Kubernetes 网络插件和运行时职责](https://kubernetes.io/docs/concepts/extend-kubernetes/compute-storage-net/network-plugins/)
- [Kubernetes 客户端版本偏差](https://kubernetes.io/releases/version-skew-policy/)
- [Cilium 身份和术语](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/gettingstarted/terminology.rst)
- [Weave 原始仓库元数据](https://api.github.com/repos/weaveworks/weave)

继续学习 [eBPF](02-ebpf.md)，或通过[简介测验](../../quizzes/networking/cilium/01-introduction-quiz.md)检验你的理解。
