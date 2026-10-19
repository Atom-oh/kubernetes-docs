# 网络模型与 VXLAN

> **审查基线**：Cilium 1.20.3；已测试的 Kubernetes 版本为 1.33–1.36；Linux 5.10+，或有文档记录的等效回移补丁版本，例如 RHEL 8.10 的 4.18 内核。
> **最后审查**：2026年10月16日

## 实验环境准备

使用[安装指南](README.md)准备一个可随时销毁的集群，以及与系统架构相匹配的 Cilium CLI。kubectl 与 API 服务器的版本差距应在一个次版本以内；“v1.31 或更高”并不是兼容性规则。

以下通用模式示例要求至少有两个可调度的 Linux 节点、没有其他 Pod CNI 与之冲突、kube-proxy 正常工作，并且 Pod CIDR 不与其他地址范围重叠。原生路由示例还要求节点处于同一二层网络。这些示例不适用于 EKS ENI、GKE Dataplane V2、AKS 托管 Cilium，也不是在线迁移 CNI 的操作步骤。

### 网络分析工具

通过分析主机支持的软件源安装 tcpdump/Wireshark。节点抓包必须在相关节点或其网络命名空间中运行；仅在执行 kubectl 的笔记本电脑上操作不够。Agent 的 monitor 工具报告的是发出的 BPF 事件，并非完整的数据包捕获。

```bash
kubectl config current-context
kubectl -n kube-system get pods -l k8s-app=cilium -o wide
export CILIUM_POD=cilium-REPLACE-WITH-AGENT-ON-TARGET-NODE
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- \
  cilium-dbg monitor --type trace -v
```

对于下文给出的 VXLAN 配置，请在相关工作节点上采集有限数量的数据包：

```bash
sudo tcpdump -nn -i any -c 50 'udp port 8472'
```

如果隧道端口有所不同，请使用实际配置的端口。生成跨节点 Pod 流量：同节点流量不一定会经过覆盖网络。抓包为空可能是因为节点、接口、端口或流量路径选错，并不一定代表网络故障。

## 容器网络模型比较

主机命名空间、网桥和节点间传输描述的是网络的不同方面，它们可以同时存在；这些模型并没有通用的性能或安全性排名。

| 模型 | 机制 | 重要权衡 |
|---|---|---|
| Host 网络 | Pod 与节点共享网络命名空间 | 可能发生端口冲突，网络命名空间隔离性较弱；不代表应用性能一定最佳 |
| Bridge 网桥 | 虚拟二层网桥连接各网络接口 | 节点间通信仍需要路由或传输机制；Cilium 并不要求每个端点都使用 Linux 网桥 |
| Overlay 覆盖网络 | 封装后的流量经由 IP 底层网络传输 | 增加报头和处理开销，但底层网络不必为每个 Pod 网段配置路由 |
| Native/underlay 原生/底层路由 | 网络直接路由工作负载地址 | 需要正确配置转发路由、返回路由和地址规划；本身既不会提供也不会移除策略或加密 |

### Cilium 网络模式

Cilium 的 `routingMode` 取值为 `tunnel` 或 `native`。VXLAN/Geneve 是隧道协议选项。云 IPAM 集成是另一个配置维度，通常与原生数据路径配合使用；它不是第三种 `routingMode`。BGP 用于通告路由，并非独立的数据包转发模式。

## 深入了解 VXLAN 技术

VXLAN 会将内层以太网帧放入 UDP 数据报，再通过 IP 网络传输。VTEP 负责封装和解封装流量；24 位 VNI 的理论标识空间为 2^24 个值。这并不表示 Kubernetes 部署实际支持 1,600 万个租户。

标准规定的 VXLAN 目的端口是 UDP 4789。**Cilium 的 VXLAN 默认使用 UDP 8472**，Geneve 默认使用 UDP 6081；两者都可以配置。Cilium 可在封装中携带安全身份元数据，因此不能把通用 VXLAN 网段数量等同于 Cilium 的租户或策略边界。

### VXLAN 数据包结构

```text
Outer Ethernet
  Outer IP (IPv4 or IPv6)
    Outer UDP (Cilium VXLAN default destination 8472; standard 4789)
      VXLAN header (8 bytes, including VNI)
        Inner Ethernet
          Inner IP packet and transport/application payload
```

IP 承载 UDP；外层 IP 报头本身并不是放在外层 UDP 报头之内。VXLAN 分段不提供加密、完整性保护或自动 NetworkPolicy 隔离。应适当限制底层网络路径，并单独配置策略和加密。

### MTU 预算

对于没有其他封装或选项的普通 VXLAN，内层 IP 可用 MTU 的减少量如下：

| 底层 IP 类型 | 外层 IP + UDP + VXLAN + 内层以太网 | 底层 IP MTU 为 1,500 字节时的内层 IP 预算 |
|---|---|---|
| IPv4 | 20 + 8 + 8 + 14 = 50 字节 | 1,450 字节 |
| IPv6 | 40 + 8 + 8 + 14 = 70 字节 | 1,430 字节 |

外层以太网报头不计入底层 IP MTU。加密、Geneve 选项及其他网络路径都可能改变预算。有效路由 MTU 与 Pod veth 设备的 MTU 不一定相同。

在 Cilium 1.20.3 中，Helm 的 **`MTU` 会覆盖底层网络 MTU**；随后由 Cilium 计算路由开销。`MTU: 0` 表示自动检测。如果把 `MTU: 1450` 当作“Pod 最终可用负载 MTU”设置，隧道开销可能会再次扣除。本地接口检测也无法证明整条路径上的最小 MTU。

### VXLAN 与其他封装方式

| 技术 | 承载方式 / 标识符 | 协议或端口 | 边界条件 |
|---|---|---|---|
| VXLAN | UDP 中承载以太网帧；24 位 VNI | 标准端口 UDP 4789；Cilium 默认 8472 | 固定基础报头；不提供加密 |
| Geneve | 带可扩展选项的通用网络虚拟化；24 位 VNI | UDP 6081 | 选项长度会改变开销 |
| GRE | 通用封装；基础 GRE 不含 VXLAN 式 VNI | IP 协议号 47，不是 TCP/UDP 端口 47 | 必须考虑可选扩展；“网络数量无限”不是明确的容量指标 |
| NVGRE | 通过 GRE 承载以太网；GRE key 中含 24 位 VSID | IP 协议号 47 | 标识符和流语义不同；支持情况取决于实现 |

## Cilium 的覆盖网络

在没有平台或配置文件覆盖设置时，Cilium 使用 VXLAN 隧道路由。跨节点传输 Pod 流量需要节点地址可达、隧道 UDP 流量获准通过，并且 MTU 可用。覆盖网络不会解决 Pod 地址段重叠问题，也无法让互不连通的节点变得可达。数据包传输过程、隧道设备、MTU 预算和原生路由变体请参阅[覆盖网络与原生路由](09-overlay-native-routing.md)。

![跨节点覆盖网络流量：端点处理、源 VTEP 封装、底层网络传输、目的端解封装并将数据交付给端点。](../../.gitbook/assets/en-networking-cilium-03-networking-2.png)

[🔍 查看交互式图示](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-cilium-03-networking-2.html)

该图展示的是概念性流程，其中地址并非逐节点 IPAM 分配方案；实际节点 Pod 地址段必须一致规划且互不重叠。策略在已配置的位置生效，源端和目的端的处理钩子也可能不同。

1. Cilium 根据控制平面和数据路径状态识别远端端点或节点。
2. 源端封装相关 Pod 数据包，并使用底层网络中的节点地址发送。
3. 目的端解封装并处理或交付内层数据包。
4. 数据路径事件、路由状态和抓包可帮助定位故障；单独缺少某个事件并不能确定故障原因。

## 路由机制

### 封装

底层网络只需提供节点或隧道路由，无需为每个 Pod 前缀配置路由。代价包括额外报头和处理开销。只有整条路径都支持所选 MTU 时，更大的帧才可能降低相对开销。

### 原生路由

节点和底层网络必须能够路由 Pod 地址，包括返回流量。路由可以来自云网络、路由器、静态配置或其他路由组件。启用原生模式不会自动启动 BGP，也不会自动通告所有 Pod CIDR。

`autoDirectNodeRoutes: true` 会为共享同一二层网络的节点安装 PodCIDR 直连路由。在多个二层网段中，`directRoutingSkipUnreachable` 可以跳过不可达的直连路由，由另一个正常工作的路由路径处理这些流量；它不会回退到覆盖隧道。

**不要同时启用隧道路由和 `autoDirectNodeRoutes: true`：Cilium 1.20.3 会在启动时明确拒绝这种组合。** 旧的“混合模式”步骤无效。原生路由仍可与特定功能的封装共存，例如配置 Geneve 的 DSR 路径；这是另一项服务功能。

Cilium BGP Control Plane 会向对等体通告已配置的 Pod/Service 前缀。它**不会对本地数据路径编程**，也不能被当作自动补齐集群内缺失路由的组件。

## 性能优化技巧

比较模式前，请确保协议、负载大小、并发数、节点位置、策略、加密和代理设置相同。去掉一个封装报头并不保证应用延迟会降低。

- **数据路径**：Socket 负载均衡、受支持的 XDP 加速和 DSR 只适用于特定路径；VXLAN 或原生路由不会自动启用这些功能。
- **连接跟踪**：Cilium BPF 连接跟踪与 Linux netfilter conntrack 是两套不同的状态机制。绕过 netfilter 路径不代表所有已建立连接都不再使用 Cilium 连接状态。
- **Map**：应根据实际容量和内存压力设置 Map 大小。LRU 淘汰适用于缓存，不是所有 Map 的通用优化手段。
- **主机调优**：CPU/NUMA 放置、中断请求（IRQ）的分布或合并，以及队列配置，可能改善或恶化特定工作负载的表现。大页不是通用的 Cilium 加速开关；应先验证实际使用方和环境确有收益。

## 云服务商特定网络

| 环境 | 需要区分的事项 |
|---|---|
| AWS ENI IPAM | Cilium 分配可经 VPC 路由的 ENI 地址，并要求配置 Operator IAM/API、子网和实例容量。ENI 安全组与 Cilium 策略互为补充；这并不自动等同于 AWS VPC CNI 的 Pod 专属分支 ENI 功能 |
| EKS 平台 | 在普通 EC2 节点上使用替代 CNI，需要单独确认支持责任。Fargate 和 EKS Auto Mode 不支持用此通用实验配置替换其 CNI。Hybrid Nodes 有单独的受支持安装路径 |
| Google Cloud | 自行管理的上游 Cilium 可使用 Kubernetes 主机范围 IPAM 和可路由的别名地址范围。托管 GKE Dataplane V2 使用 Google 管理的 Cilium/`anetd`；不要在其上另装上游数据平面，也不要假定其公开功能完全相同 |
| Azure | Azure CNI Powered by Cilium 由 AKS 管理并使用委派式 IPAM。上游 Azure IPAM 面向自行管理的 Azure VM/VMSS 集群；AKS BYOCNI 则是需明确选择的另一种部署模式 |

Cilium 策略不会自动创建所有云防火墙或安全组配置。应先选择对应的平台指南和支持模式。

## 实验：配置 Cilium 网络模式并测试性能

### 在已准备好的全新集群中选择一种模式

保存下面的通用文件。如果 Pod CIDR 与节点、Service、VPC 或互联网络范围重叠，应先替换该值。所选范围必须与集群/kube-proxy 配置及原生模式配置中的 `ipv4NativeRoutingCIDR` 一致；只改其中一个文件是不够的。`kubeProxyReplacement: false` 表示假定 kube-proxy 正常工作。以下是 Helm values，不是可用 kubectl apply 的 ConfigMap。

**`lab-common.yaml`**

```yaml
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
MTU: 0
hubble:
  enabled: true
  relay:
    enabled: true
  ui:
    enabled: true
```

以下模式文件中只能选一个。比较模式时应使用不同的可销毁集群，不要在运行中的集群上反复重装 CNI。

**`mode-vxlan.yaml`**

```yaml
routingMode: tunnel
tunnelProtocol: vxlan
tunnelPort: 8472
autoDirectNodeRoutes: false
```

**`mode-geneve.yaml`**

```yaml
routingMode: tunnel
tunnelProtocol: geneve
tunnelPort: 6081
autoDirectNodeRoutes: false
```

**`mode-native.yaml`**

```yaml
routingMode: native
ipv4NativeRoutingCIDR: 10.244.0.0/16
autoDirectNodeRoutes: true
```

VXLAN 示例：

```bash
kubectl config current-context
cilium install --version 1.20.3 --values lab-common.yaml --values mode-vxlan.yaml
cilium status --wait
```

只有在网络前置条件满足时，才选择 `mode-geneve.yaml` 或 `mode-native.yaml`。不要使用过时的 `tunnel: vxlan`、`ipv4-range` 或 `ipv4-service-range` ConfigMap 示例；应通过受支持的 Helm 字段配置 IPAM。

### 网络性能测试

在已准备好的可销毁集群上，使用 CLI 维护的性能测试工作负载；不要假定无关清单会创建 `netperf-client` 和 `netperf-server`：

```bash
cilium connectivity perf --test-namespace cilium-net-perf \
  --namespace-labels docs-audit-lab=cilium-networking-03 \
  --duration 10s --samples 2 --crr --udp \
  --host-net=false --pod-net=true --same-node=true --other-node=true \
  --report-dir ./cilium-net-perf-results
```

这里的持续时间适用于每种测试情况或样本，并非整个运行过程总共十秒。这会创建测试工作负载并产生网络负载。CLI 0.20.1 会为命名空间追加序号后缀（默认只运行一个测试套件时为 `cilium-net-perf-1`）。请将版本、节点放置和设置与结果一并保存；吞吐量或延迟不作保证。

TCP 请求/响应、连接建立速率和数据流测试回答的是不同问题。如果使用独立准备的 iperf3 环境，UDP 测试仍需要 TCP 控制连接和 UDP 数据路径；只开放 TCP 5201 的 Service 并不够。设定的 UDP 发送速率不等于实测吞吐量。

这些示例已依据当前官方配置值、API schema 和 CLI 源码核对。本次主机重启后的审查没有渲染 Helm 模板、部署集群或运行网络基准测试；依赖测试结果前，请先验证完整的平台和实验环境。

## 参考资料

- [Cilium 1.20.3 路由](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/network/concepts/routing.rst)、[Helm values](https://github.com/cilium/cilium/blob/v1.20.3/install/kubernetes/cilium/values.yaml)、[启动校验](https://github.com/cilium/cilium/blob/v1.20.3/daemon/cmd/daemon_main.go)、[MTU 计算](https://github.com/cilium/cilium/blob/v1.20.3/pkg/mtu/mtu.go)、[MTU 选项](https://github.com/cilium/cilium/blob/v1.20.3/pkg/mtu/cell.go)
- [VXLAN RFC 7348](https://www.rfc-editor.org/rfc/rfc7348.txt)、[Geneve RFC 8926](https://www.rfc-editor.org/rfc/rfc8926.txt)、[GRE RFC 2784](https://www.rfc-editor.org/rfc/rfc2784.txt)、[NVGRE RFC 7637](https://www.rfc-editor.org/rfc/rfc7637.txt)
- [BGP Control Plane](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/network/bgp-control-plane/bgp-control-plane.rst)、[AWS ENI](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/network/concepts/ipam/eni.rst)、[EKS 替代 CNI](https://docs.aws.amazon.com/eks/latest/userguide/alternate-cni-plugins.html)、[GKE Dataplane V2](https://docs.cloud.google.com/kubernetes-engine/docs/concepts/dataplane-v2)、[Azure IPAM](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/network/concepts/ipam/azure.rst)
- [CLI 0.20.1 connectivity/perf 选项](https://github.com/cilium/cilium-cli/blob/v0.20.1/vendor/github.com/cilium/cilium/cilium-cli/cli/connectivity.go)、[iperf3 调用方式](https://software.es.net/iperf/invoking.html)、[kubectl 版本偏差策略](https://kubernetes.io/releases/version-skew-policy/)

[返回主页](README.md)

## 测验

请完成[网络验证练习及预期结果](../../quizzes/networking/cilium/03-networking-quiz.md)。
