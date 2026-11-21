# Cilium 深入解析：云原生网络的未来

## 概述与审查基线

本节介绍 Cilium 网络、策略和可观测性。示例已针对 **Cilium/Helm chart 1.20.3**、Cilium CLI **0.20.1** 和 Hubble CLI **1.20.2** 进行审查。Cilium 1.20 Kubernetes 兼容性页面列出的测试版本为 **1.33–1.36**；上游发布 1.37 并不会自动扩展此兼容矩阵。支持的主机为 AMD64/AArch64 Linux，内核版本 **5.10+**；或者使用文档中列出的发行版等效版本，例如 RHEL 8.10 向后移植的 4.18 内核。各项功能另有额外要求。

> **最后更新**：2026 年 11 月 19 日

### 历史发行说明

以下日期为 GitHub 上的 UTC 发布日期，描述的是相应发行版本，而非当前安装版本。不同发行分支的功能回移情况有所不同。

| 日期 | 发行版本 | 已核实的要点 |
| --- | --- | --- |
| 2026 年 7 月 14 日 | [1.20.0-rc.0](https://github.com/cilium/cilium/releases/tag/v1.20.0-rc.0) | 首个 1.20 候选发行版 |
| 2026 年 7 月 16 日 | [1.19.6](https://github.com/cilium/cilium/releases/tag/v1.19.6), [1.18.12](https://github.com/cilium/cilium/releases/tag/v1.18.12), [1.17.18](https://github.com/cilium/cilium/releases/tag/v1.17.18) | 1.19.6/1.18.12 列出了 Gateway 访问日志配置；此处提到的重启策略和 ClusterMesh 亲和性修复列于 1.19.6，并非全部三个发行版本 |
| 2026 年 7 月 21 日 | [1.20.0-rc.1](https://github.com/cilium/cilium/releases/tag/v1.20.0-rc.1) | 第二个 1.20 候选发行版 |
| 2026 年 7 月 29 日 | [1.20.0](https://github.com/cilium/cilium/releases/tag/v1.20.0) | GA 发行版；以下为部分变更 |
| 2026 年 8 月 3 日 | [1.21.0-pre.0](https://github.com/cilium/cilium/releases/tag/v1.21.0-pre.0) | 下一周期的预发行版，不是本指南的部署基线 |
| 2026 年 8 月 18 日 | [1.20.1](https://github.com/cilium/cilium/releases/tag/v1.20.1) | ClusterMesh 文档及错误修复，包括重启/CIDR 策略处理 |
| 2026 年 8 月 18 日 | [1.19.7](https://github.com/cilium/cilium/releases/tag/v1.19.7) | 包括 ENI 接口时序、Service/LB 及其他修复 |
| 2026 年 8 月 18 日 | [1.18.13](https://github.com/cilium/cilium/releases/tag/v1.18.13) | VRRP/IGMP 主机防火墙支持及相关修复 |
| 2026 年 9 月 9 日 | [1.21.0-pre.2](https://github.com/cilium/cilium/releases/tag/v1.21.0-pre.2) | 预发行版；其变更日志涵盖从 pre.0 到 pre.2 的变更，因为 **1.21.0-pre.1 从未发布** |
| 2026 年 9 月 16 日 | [1.20.2](https://github.com/cilium/cilium/releases/tag/v1.20.2) | 错误修复，包括 ENI IPAM 前缀委派的分配/释放和辅助 VPC CIDR 处理、ClusterMesh 修复、策略变更后立即创建的 Pod 的策略修订、LocalRedirectPolicy 回归问题，以及升级在 v1.15 或更早版本创建的集群（`CiliumNodeConfig v2alpha1` CRD 版本） |
| 2026 年 9 月 16 日 | [1.19.8](https://github.com/cilium/cilium/releases/tag/v1.19.8), [1.18.14](https://github.com/cilium/cilium/releases/tag/v1.18.14) | 仍受支持的旧分支补丁版本 |
| 2026 年 10 月 2 日 | [1.21.0-pre.3](https://github.com/cilium/cilium/releases/tag/v1.21.0-pre.3) | 1.21 预发行版 |
| 2026 年 10 月 15 日 | [1.20.3](https://github.com/cilium/cilium/releases/tag/v1.20.3) | Gateway API 依赖项 v1.6.3、conntrack GC 和带有 `nodeSelector` 的 CNP 处理等修复；这是本指南当前审查的基线 |
| 2026 年 10 月 15 日 | [1.19.9](https://github.com/cilium/cilium/releases/tag/v1.19.9), [1.18.15](https://github.com/cilium/cilium/releases/tag/v1.18.15) | 仍受支持的旧分支补丁版本 |
| 2026 年 10 月 23 日 | [1.20.4](https://github.com/cilium/cilium/releases/tag/v1.20.4), [1.19.10](https://github.com/cilium/cilium/releases/tag/v1.19.10), [1.18.16](https://github.com/cilium/cilium/releases/tag/v1.18.16) | 针对 CVE-2026-111943 的带外安全补丁版本：将 Go 升级到 1.26.10，使遭到入侵的 eMudhra 中间 CA 证书不再受信任，并包含依赖项补丁更新和回移修复 |
| 2026 年 11 月 2 日 | [1.21.0-pre.4](https://github.com/cilium/cilium/releases/tag/v1.21.0-pre.4) | 最新的 1.21 预发行版：基于接口的 BGP 无编号对等、默认启用 BPF 伪装、Gateway API 前端客户端证书验证（mTLS）和监听器 TLS 版本选项、agent/operator 中的多池 Resource IPAM，以及 Gateway API Inference Extension 支持。**1.21 目前仅为预发行版（目标是在 2027 年初发布 GA）**，本指南中标记为 1.21 的项目可能会变更 |

2026 年 9 月 14 日，CNCF 博客发布了 [Cilium 1.20 功能回顾](https://www.cncf.io/blog/2026/09/14/cilium-1-20-gateway-api-externalauth-tcproute-udproute-eni-ipam-for-ipv6-and-more/)（Gateway API ExternalAuth、TCPRoute/UDPRoute、IPv6 ENI IPAM 等），所涵盖的范围与下方 1.20.0 公告摘要相同。

1.20.0 公告报告称有 **2,660 多个新提交**，由一个 **拥有 1,100 多名贡献者的社区** 支持。后者指社区规模，而不是本次发行版的作者人数。主要内容包括：

- Gateway API **1.6.1**、TCPRoute/UDPRoute、BackendTLSPolicy、ListenerSets、ExternalAuth 和 CORS 支持，具体取决于各项功能的配置和 API 成熟度。
- Datapath 插件和选择启用的 `bpf.datapathMode=auto`；公告所述的默认值仍为 veth。双栈集群可以配置 IPv6 出口网关地址。
- **Beta** 版 IPv6 ENI IPAM，以及从 cluster-pool 迁移到 multi-pool 而无需重建集群。原地迁移并不保证不会中断。
- 流量分布提示、加权 Maglev 后端和稳定的 MCS 集成；Kubernetes ClusterNetworkPolicy 支持，以及基于 ztunnel 的工作负载身份（**Beta**）。
- 据报告，`cilium-cni` 二进制文件从约 **77 MB 缩减到 16 MB**。ADS/Delta xDS 改进见于 1.20 公告；不要将其归因于 1.18.13 补丁说明。这些是上游发行说明中的声明，并非本次审查重复测得的结果。

请查看 [1.20 升级说明](https://docs.cilium.io/en/v1.20/operations/upgrade/#upgrade-notes)，了解 Mutual Authentication（**在 1.20 中弃用**，在 1.21 预发行版中移除）、已移除/替换的 Envoy Go 扩展、Kafka 感知策略、旧版 CiliumNodeConfig API、libnetwork 集成和自定义 CNI 配置变更。

### NetworkPolicy 安全公告

[GHSA-fm8w-2m5w-9j7r / CVE-2026-56743](https://github.com/cilium/cilium/security/advisories/GHSA-fm8w-2m5w-9j7r) 的项目安全公告发布日期为 **2026 年 7 月 6 日**。项目 API 与 GitHub 全局安全公告 API 显示的日期不同：后者记录为 9 月 3 日。本发行时间线采用项目披露日期；全局记录日期并不代表之后发布了修复版本。该问题在安全公告所述的自定义集群名称条件下影响 **1.19.0–1.19.4**：仅包含 `ipBlock` 的标准 Kubernetes NetworkPolicy 对等方，可能会意外允许来自所选 Pod 所在命名空间内工作负载的入站流量。**1.19.5** 修复了此问题；部署时请使用合适的当前修补版本。公告称 CiliumNetworkPolicy/ClusterwideNetworkPolicy 和低于 1.19.0 的发行版本不受这一特定错误影响。

## 简介

Cilium 为受支持的 Linux Kubernetes 环境提供网络、安全和可观测性功能。路由、IPAM、加密和 Service 处理是彼此独立的选择；仅选择 eBPF 并不能启用所有功能，也不能保证性能。旧版 Docker libnetwork 集成已在 1.20 中移除，因此不应再将 Docker/Mesos 列为可互换的当前安装目标。

### eBPF 与关键功能

内核会在加载 eBPF 程序前验证程序，并可在受支持的挂载点将其 JIT 编译后执行。这使得无需自定义内核模块即可进行数据包处理和可观测性；但验证器并不能证明应用程序或策略正确。实际吞吐量、延迟和内存占用取决于程序、平台和工作负载。

Cilium 提供 L3/L4 策略、通过 Envoy/DNS 代理集成实现的 L7 策略、可选 WireGuard/IPsec、Service 负载均衡、Hubble 流可见性、ClusterMesh 和 BGP 通告。XDP 加速为可选功能，并取决于设备和配置。L7 功能可能会使用每节点 Envoy；通过 ztunnel 实现的工作负载身份需要单独的 Beta 配置。仅安装 agent 并不会启用所有网格、加密或多集群行为。

### 与其他网络项目的比较

| 项目 | 连通性 / IPAM | 策略及相关功能 |
| --- | --- | --- |
| Cilium | 原生路由或覆盖网络；包括云 ENI 在内的多种 IPAM 模式 | eBPF 数据平面、Cilium/Kubernetes 策略、L7 集成、Hubble 和可选加密 |
| Calico | 使用 Calico 或外部 IPAM 的原生/IPIP/VXLAN 配置 | Linux Iptables/Nftables/BPF，支持 Windows HNS；开源版 WireGuard、分阶段策略和独立的 L7 集成 |
| Flannel | 通过选定的后端（例如 VXLAN/host-gw/WireGuard）提供 Pod 连通性 | 路由守护进程本身不执行 NetworkPolicy；其 Helm Chart 可以通过 `netpol.enabled` 部署 SIGs 网络策略控制器，也可以与其他策略实现配合使用 |
| AWS VPC CNI | VPC ENI 地址分配/网络 | 在受支持的 EC2 Linux 节点上提供原生网络策略，并提供独立的 SG-for-Pods 功能；EKS Auto Mode 是另一种托管实现 |

路由模式与数据包处理实现并不属于同一类别。Calico 并非仅限于 iptables/IPVS，Flannel 可以使用加密后端，而 AWS 策略也不等同于安全组。Service mesh 是可选层；跨集群 VPC 连通性也不限于 Transit Gateway。应使用经过测量的工作负载和明确的支持矩阵，而不是采用适用于所有场景的性能排名。

## 架构

**Kubernetes API server** 存储 Kubernetes/Cilium 资源。Cilium agents 监听相关状态并配置每个节点的数据平面；Cilium Operator 负责集群级任务，例如所选 IPAM 模式相关工作，以及身份/控制器工作。在此基本架构中，不存在必须单独部署的集群级“Cilium API Server”。agents 有本地 API，而可选的 ClusterMesh API server 用途不同。

| 组件 | 作用 |
| --- | --- |
| Cilium Agent | 节点本地的 endpoint、策略、路由/Service 状态和 eBPF 管理 |
| Cilium Operator | 集群级协调，以及依赖模式的分配/控制器工作 |
| Envoy | 为启用的 L7 策略、Ingress/Gateway 和相关功能提供用户空间代理 |
| Hubble server | 与 agent 集成的节点本地流 API |
| Hubble Relay / UI | 汇总流数据 / 显示 Service 映射和流 |
| Prometheus 指标端点 | 单独收集统计数据；Relay/UI 不是指标抓取管道 |
| cilium / cilium-dbg / hubble | 分别用于集群管理 CLI / agent 诊断 / 流客户端 |

### 网络与数据包路径

原生路由需要可达的底层网络；隧道模式使用 VXLAN 或 Geneve。AWS ENI 和 Azure IPAM 是地址分配/集成选项，各自有平台要求。Cilium 的 BGP Control Plane 会向路由器通告可达性，**不会配置数据路径，也不提供内部集群路由**。

不存在通用的 XDP→TC→Pod 顺序。Socket 负载均衡可以在数据包产生之前生效；TC/netkit 挂载点取决于数据平面；可选 XDP 可加速选定的流量；L7 流量可能会经过 Envoy。返回流量也取决于 NAT、conntrack 和 DSR 选择。所选配置的详情请参阅网络和 eBPF 章节。

## 与 Amazon EKS 集成

在安装任何组件之前，先选择实际的网络和计算配置。示例插件名称/版本 `cilium` / `v1.17.0-eksbuild.1` 并非经过核实的 AWS 发行版，因此此处不将其作为安装命令。若考虑使用打包的供应商插件，请检查所在 Region 的实际插件目录、发布方、许可证和支持的计算类型。

| EKS 配置 | 需要核实的内容 |
| --- | --- |
| 普通 EC2 节点，使用 Cilium ENI 替代 VPC CNI | 上游/合作伙伴管理的 CNI；AWS 支持的 EC2 CNI 是 VPC CNI。规划 CNI 归属、IAM、地址分配、路由、引导过程和节点迁移 |
| 普通 EC2 节点，AWS VPC CNI 链接模式 | VPC CNI 管理接口/IPAM；随后由 Cilium 挂载其数据平面。现有 Pod 需要重新创建，且 L7/IPsec 有文档说明的限制 |
| Hybrid Nodes | 遵循 AWS 专用 CNI 指南和 AWS 维护的 Cilium 构建矩阵；上游 1.20.3 不会自动成为受支持的 AWS 构建版本 |
| Auto Mode | 不支持替代 CNI/策略插件；请使用托管的 NodeClass/网络功能 |
| Fargate | 不支持替代 CNI/DaemonSet 安装 |
| Windows | Cilium agent 的要求是 Linux；不要将此配置用于 Windows 工作节点 |

AWS 的通用替代 CNI 页面与专用 Hybrid 指南在对 Calico 支持的措辞上有所不同；仓库迁移示例并不能证明支持已终止。对于 Hybrid Nodes，请确认具体发行版、功能集和支持责任方。对于 Auto Mode，其节点本地 CoreDNS/系统网络也不同于本指南中的普通 EC2 配置；混合使用的非 Auto 节点仍需要传统的 DNS Deployment。

### 配置了 Cilium ENI 的 EC2 集群

以下是用于已准备好的 IPv4 EC2 集群的 **Cilium Helm 值**，不是完整的集群创建或原地迁移方案。使用前请完成以下事项：

1. 选择受支持的 EKS/Kubernetes 版本和 Linux AMI，并确定唯一的 CNI 管理方。不要为了省事而从现有工作负载集群中删除 `aws-node`。
2. 准备节点污点/调度配置，确保在 Cilium 管理节点之前，工作负载不会运行。上游 EKS 指南使用 `node.cilium.io/agent-not-ready=true:NoExecute`；请根据实际节点生命周期评估驱逐和引导过程的影响。
3. 准备子网容量、ENI 配额/安全组、节点元数据访问权限，以及 Operator 所需的 EC2 权限。以下角色 ARN 是正确受信任的 **cilium-operator ServiceAccount** 角色的占位符，并非由值文件创建的角色。
4. 对于此 `kubeProxyReplacement: false` 示例，请保留正常工作的 kube-proxy 和 DNS。如要使用替换模式，请遵循单独的直接 API/引导 DNS 要求。max-Pods 应根据实际实例/IPAM 容量选择，不要一概使用 110。

保存为 `cilium-eni-values.yaml`，并将角色/接口选项替换为经过审核的值：

```yaml
eni:
  enabled: true
ipam:
  mode: eni
routingMode: native
kubeProxyReplacement: false
ipv4:
  enabled: true
ipv6:
  enabled: false
# egressMasqueradeInterfaces is intentionally omitted: it only affects iptables masquerade,
# and ENI mode leaves IPv4 masquerade off by default since 1.18.
serviceAccounts:
  operator:
    annotations:
      eks.amazonaws.com/role-arn: arn:aws:iam::111122223333:role/CiliumOperatorENI
```

```bash
helm repo add cilium https://helm.cilium.io/
helm repo update cilium
helm template cilium cilium/cilium --version 1.20.3 \
  --namespace kube-system -f cilium-eni-values.yaml > cilium-eni-rendered.yaml

# After preparing the cluster and reviewing the rendered configuration:
helm install cilium cilium/cilium --version 1.20.3 \
  --namespace kube-system -f cilium-eni-values.yaml
```

请通过安装管理方管理这些设置。仅包含少数几个键的替代 `cilium-config` 可能会移除其他必需设置；旧的 `tunnel=disabled` 值已由 `routingMode: native` 取代。ENI 分配/权限和 SNAT 行为仍需运行时验证；成功渲染并不能证明 EC2 网络可用。

**IPv6 说明**：1.20.3 ENI IPAM 参考文档将 IPv6 描述为 Beta，而其 EKS 先决条件页面仍声明 ENI 集成仅支持 IPv4。本指南保留 IPv4 示例，并记录这一文档不一致之处，不将任一说法视为 EKS 生产环境 IPv6 兼容性的证明。单独设计 IPv6 方案之前，请查看当前 ENI/双栈子网要求。

### VPC CNI 链接模式备选方案

上游链接模式指南要求 VPC CNI 1.11.2+，并说明以下配置：

```yaml
cni:
  chainingMode: aws-cni
  exclusive: false
enableIPv4Masquerade: false
routingMode: native
kubeProxyReplacement: false
```

应将其作为**另一种配置**使用，而不是叠加到 ENI 替代配置上。VPC CNI 仍负责地址分配。应通过实际管理方升级托管插件，而不是应用历史上游 DaemonSet。避免在相同 endpoint 上运行相互竞争的策略引擎。CNI 链发生变化时，现有 Pod 不会自动追溯接入 Cilium；请在规划好的滚动更新期间重新创建 Pod，并验证 endpoint 管理情况。链接模式存在文档说明的 L7 策略/IPsec 限制，因此不要假设本页后续的所有示例都适用于该配置。

### ClusterMesh

ClusterMesh 需要唯一的集群标识、兼容的版本、可达且不重叠的 Pod 网络、经过身份验证的 API 连接，以及适当的暴露模式。LoadBalancer Service 可能会创建云资源，因此需要经过审慎设计的网络/安全方案。创建两个公共端点并不足以安全地连接集群。请遵循维护中的 [ClusterMesh 指南](13-clustermesh-install-upgrade.md) 和高级章节中针对所选拓扑的说明。

## 安装与配置

### 客户端工具

根据工作站的操作系统/架构，使用对应的官方 Cilium CLI 0.20.1 和 Hubble CLI 1.20.2 资源，并在解压前核对提供的校验和。Linux ARM64 和 AMD64 的资源不同；macOS 使用相应的 Darwin 资源。CLI 版本与 Cilium agent/Helm chart 版本彼此独立。请参阅[已核实的 CLI 安装指南](../../service-mesh/cilium-service-mesh/README.md)。

```bash
cilium version --client
hubble version
```

### 非云环境 Cluster-Pool 示例

以下**备选方案**适用于已准备好的普通 Linux 集群，且其中 kube-proxy 和 DNS 已正常工作。确保示例 `10.244.0.0/16` Pod 地址范围与集群兼容，且不会与 Service、节点、VPC 或互联网络的地址范围重叠。不要在 ENI 模式下使用此地址池配置。

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

保存为 `cilium-values.yaml`，渲染固定版本的 chart，然后仅在已准备好的集群上安装：

```bash
helm template cilium cilium/cilium --version 1.20.3 \
  --namespace kube-system -f cilium-values.yaml > cilium-rendered.yaml
helm install cilium cilium/cilium --version 1.20.3 \
  --namespace kube-system -f cilium-values.yaml
cilium status --wait
```

对于现有发行版本，请使用其升级/GitOps 流程，保留由其管理的值，并遵循特定版本的升级步骤。反复执行 `cilium install` 示例并不是更改单项设置的通用方法。

| 选项 | 当前配置和先决条件 |
| --- | --- |
| VXLAN/Geneve | `routingMode: tunnel` 加上 `tunnelProtocol`；允许选定的封装流量，并根据路径设置 MTU |
| 原生路由 | `routingMode: native`；底层网络必须能够路由 Pod 地址。`autoDirectNodeRoutes` 需要合适的直接连通性，不能用于任意多子网路由 |
| kube-proxy 替换 | 使用 `kubeProxyReplacement: true` 或 `false`，而不是旧版 `strict`；替换模式要求可达的 `k8sServiceHost`/`k8sServicePort` 和文档所述的引导方案 |
| WireGuard | 检查内核/平台和对等路径后，启用受支持的加密模式；它不会自动加密所有可能的流量路径 |
| IPsec | 需要文档所述的密钥 Secret、密钥分发/轮换和兼容模式；仅设置 Helm 启用标志并不完整 |
| XDP/DSR/BBR | 这些选项分别取决于设备/内核/拓扑，不是通用的安装预设 |

## Network Policies

Kubernetes `networking.k8s.io/v1` NetworkPolicy 与 Cilium `cilium.io/v2` 策略是不同的 API。多个允许策略可以组合生效。以下示例使用**分别准备的测试命名空间**，以避免 L4 允许规则悄然绕过 L7 限制。在得出结论前，请检查所有选择实际 endpoint 的策略。

### L4 示例

在 `cilium-l4-demo` 中，此策略选择后端 Pod，并允许来自同一命名空间前端 Pod 的 TCP 8080 入站流量：

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-frontend-to-backend
  namespace: cilium-l4-demo
spec:
  podSelector:
    matchLabels:
      app: backend
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: frontend
    ports:
    - port: 8080
      protocol: TCP
```

### HTTP 示例

在单独的 `cilium-l7-demo` 命名空间中，此策略选择后端 Pod，并将来自该命名空间前端 Pod 的 TCP 8080 明文 HTTP 流量限制为指定的方法/路径。所选 CNI 模式必须支持 L7 代理；如果没有受支持的终止配置，则不会自动检查加密 HTTP 流量。

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: allow-product-read
  namespace: cilium-l7-demo
spec:
  endpointSelector:
    matchLabels:
      k8s:app: backend
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:app: frontend
        k8s:io.kubernetes.pod.namespace: cilium-l7-demo
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
      rules:
        http:
        - method: GET
          path: ^/api/v1/products$
```

不要为相同的对等方/端口添加匹配的、无限制的 L4 允许规则：Cilium 文档指出，此类允许规则会使更严格的 L7 限制失效。L7 拒绝可能会返回 HTTP 403，而不是丢弃数据包。请使用真实的 endpoint 身份测试允许的 GET 请求以及被拒绝的方法/路径。

### DNS/FQDN 示例

在 `cilium-dns-demo` 中，此策略允许向普通 CoreDNS Pod 发送 DNS 查询，并允许访问为 `api.example.com` 学习到的地址的 TCP 443 流量。该域名仅为示例；请将其替换为获准的目标。此处省略了宽泛的 `*.amazonaws.com` 通配符，因为它并不能限定账户/资源边界。

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: allow-api-domain
  namespace: cilium-dns-demo
spec:
  endpointSelector:
    matchLabels:
      k8s:app: web
  egress:
  - toEndpoints:
    - matchLabels:
        k8s:k8s-app: kube-dns
        k8s:io.kubernetes.pod.namespace: kube-system
    toPorts:
    - ports:
      - port: '53'
        protocol: ANY
      rules:
        dns:
        - matchPattern: '*'
  - toFQDNs:
    - matchName: api.example.com
    toPorts:
    - ports:
      - port: '443'
        protocol: TCP
```

DNS 通配符允许向选定的解析器发送查询，并不允许连接到所有返回的地址。它仍然可以承载任意 DNS 名称；如有需要，请考虑 DNS 搜索后缀并限制查询名称。NodeLocal DNS 或其他解析器需要正确选择目标。FQDN 策略是基于 DNS 派生 IP 的授权，不是 TLS 主机名验证或 HTTP URL 授权；共享 IP 以及应用层 TLS/身份验证仍然重要。

## 使用 Hubble 进行可观测性

上方的 cluster-pool 值会启用 Relay/UI 和组件指标。对于现有安装，请通过其配置管理方应用预期的 Hubble 值；`cilium hubble enable --ui` 是受支持的便捷命令，但 `cilium hubble enable --metrics=...` 并不是受支持的 0.20.1 CLI 标志。请改为在 Helm 值中配置 `hubble.metrics.enabled`。不要同时启用旧版 `http` 和 `httpV2` 处理器。

在一个终端中保持 Relay 端口转发运行：

```bash
cilium hubble port-forward --port-forward 4245
```

在另一个安装了 Hubble CLI 的终端中运行：

```bash
hubble observe --server 127.0.0.1:4245 --namespace cilium-l7-demo
hubble observe --server 127.0.0.1:4245 --protocol http
hubble observe --server 127.0.0.1:4245 --from-label k8s:app=frontend --to-label k8s:app=backend
hubble observe --server 127.0.0.1:4245 --verdict DROPPED
hubble observe --server 127.0.0.1:4245 --http-status 403
```

此本地示例假设使用默认 Relay server 配置；启用了 TLS 的 Relay 需要相应的客户端信任/身份验证配置。HTTP 事件要求流量经过已配置的 L7 代理。`DROPPED` 是数据平面的判定结果，并不代表所有应用请求失败。使用 `cilium hubble ui` 进行 UI 端口转发，并单独配置 Prometheus 目标发现以抓取指标。Hubble 流式传输本身并不是分布式应用跟踪。

## 测试与运维

连通性/性能命令会创建测试工作负载，且可能更改策略或产生大量流量。请使用经过审查的测试命名空间/环境和相应权限；本次审查并未在集群上执行这些命令。

```bash
cilium connectivity test --help
cilium connectivity perf --help
```

性能子命令是 `cilium connectivity perf`；`connectivity test --test=performance` 只是提供测试名称筛选条件，并不是性能测试运行器。比较吞吐量/延迟前，请记录软件版本、拓扑、流量和原始结果。

检查时，请区分管理 CLI 与**agent 端的 `cilium-dbg`**：

```bash
cilium status --verbose
kubectl get cnp,ccnp -A
kubectl get pods -n kube-system -l k8s-app=cilium -o wide

# Choose the agent Pod on the affected node.
CILIUM_POD=replace-with-actual-cilium-pod
kubectl exec -n kube-system "$CILIUM_POD" -c cilium-agent -- cilium-dbg endpoint list
kubectl exec -n kube-system "$CILIUM_POD" -c cilium-agent -- cilium-dbg map list
kubectl exec -n kube-system "$CILIUM_POD" -c cilium-agent -- cilium-dbg metrics list
kubectl logs -n kube-system "$CILIUM_POD" -c cilium-agent --since=15m --tail=200 --timestamps
```

管理 CLI 中的 `cilium endpoint list`、`cilium bpf maps list` 和 `cilium metrics list` 并非等效命令。`cilium sysdump` 可以收集诊断材料；请保护收集到的基础设施/日志数据。agent 处于 Ready 状态或抓取成功，都不能替代应用测试和负向策略测试。

### 运维优先事项

- 在启用映射预分配、XDP、DSR、BBR 或固定设备模式之前先进行测量。这些功能会消耗资源或改变数据包路径，需要针对具体功能进行检查。
- 在选定范围内引入默认拒绝策略，并明确允许 DNS、API、身份和应用依赖项。除已有连接外，还要检查新建 Pod 和升级过程中的变化。
- 将加密、证书/密钥轮换、策略实施和可观测性作为独立的验收检查。保留可用的管理/恢复路径。
- 审查当前平台矩阵和受支持的升级路径。历史发行公告并不能证明当前部署兼容性。

## 深入解析目录

**[Cilium 简介与基本概念](01-introduction.md)**
- Cilium 概述与历史
- 容器网络基础
- 了解 CNI（容器网络接口）
- Cilium 的差异化特性

**[深入解析 eBPF 技术](02-ebpf.md)**
- eBPF 技术简介与历史
- eBPF 在内核中的工作方式
- eBPF 程序类型与映射
- 在 Cilium 中使用 eBPF

**[网络模型与 VXLAN](03-networking.md)**
- 容器网络模型比较
- 深入解析 VXLAN 技术
- Cilium 的覆盖网络
- 性能优化技术
- 路由机制（封装与原生路由）
- 云服务商网络（AWS ENI、Google Cloud）

**[IPAM 与网络策略](04-ipam-policy.md)**
- IP 地址管理（IPAM）策略
- Kubernetes 与 Cilium IPAM 集成
- 网络策略设计与实施
- 多集群场景
- 深入解析 IPAM 模式（集群范围、Kubernetes 主机范围、多池）
- 云服务商 IPAM（Azure IPAM、AWS ENI、GKE）
- 基于 CRD 的 IPAM

**[L2-L7 网络与负载均衡](05-l2-l7-networking.md)**
- 了解 OSI 模型层（L2、L3、L4、L7）
- Cilium 的分层功能
- Service Mesh 集成
- 负载均衡架构
- 伪装配置与实现模式
- IPv4 分片处理

**[安全与可见性](06-security-visibility.md)**
- Cilium 的安全功能
- 网络可见性与监控
- Hubble 架构与用法
- 实时威胁检测

**[高级主题与真实案例](07-advanced-topics.md)**
- 性能调优与故障排查
- 大规模部署策略
- 真实用例研究
- 未来路线图与开发方向

**[eBPF 数据路径内部机制](08-ebpf-datapath-internals.md)**
- 程序集、挂载点和尾调用
- BPF 映射目录、容量规划和编译/加载流程
- 策略实施路径与 Hubble 事件管道

**[覆盖网络与原生路由](09-overlay-native-routing.md)**
- VXLAN/Geneve、VNI 中的身份、MTU 和数据包路径
- 原生路由、伪装、主机路由、DSR 和 netkit
- EKS 决策表：覆盖网络与 ENI 与 VPC CNI 链接模式

**[深入解析 IPAM](10-ipam-deep-dive.md)**
- 所有 IPAM 模式、容量规划计算和决策矩阵
- 多池、`CiliumPodIPPool`、ENI、LB IPAM、Node IPAM
- 耗尽问题排查和 1.21 API 变更

**[BGP、负载均衡器 IP 和出口流量](11-bgp-lb-egress-edge.md)**
- BGP Control Plane v2 CRD、通告与检查
- L2 通告、Egress Gateway、Local Redirect Policy
- Gateway API 要求和仅供内部使用的 EKS 暴露方式

**[mTLS、加密与身份](12-mtls-encryption-identity.md)**
- 身份模型、策略语义和审计模式
- Mutual Authentication 时间线、ztunnel 工作负载 mTLS
- WireGuard、IPsec、Hubble 和证书管理

**[版本、安装/升级与 Cluster Mesh](13-clustermesh-install-upgrade.md)**
- 1.17-1.21 功能矩阵、升级和回滚规则
- EKS 安装细节、Cluster Mesh 和 MCS-API

## 其他资源

- [深入了解网络概念](networking-concepts.md)
- [术语表与缩写](glossary.md)

## 参考资料

- [Cilium 1.20 Kubernetes 兼容性](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/network/kubernetes/compatibility.rst)
- [Cilium 系统要求](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/operations/system_requirements.rst)
- [EKS 先决条件](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/installation/requirements-eks.rst)
- [Cilium ENI IPAM](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/network/concepts/ipam/eni.rst)
- [AWS 替代 CNI 支持](https://docs.aws.amazon.com/eks/latest/userguide/alternate-cni-plugins.html)
- [AWS Hybrid Nodes CNI](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-cni.html)
- [Cilium L7 策略语义](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/security/policy/layer7.rst)
- [Hubble 项目](https://github.com/cilium/hubble)
- [Flannel 网络与策略集成](https://github.com/flannel-io/flannel)
- [Calico 比较术语](../calico/glossary.md)

## 测验

要检验你在本节中学到的内容，请尝试 [Cilium 深入解析测验](../../quizzes/networking/cilium/01-introduction-quiz.md)。
