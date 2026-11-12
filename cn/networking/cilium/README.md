# Cilium 深入解析：云原生网络的未来

## 概述与审查基线

本节介绍 Cilium 网络、策略和可观测性。示例已根据 **Cilium/Helm chart 1.20.3**、Cilium CLI **0.20.1** 和 Hubble CLI **1.20.2** 进行审查。Cilium 1.20 Kubernetes 兼容性页面列出的测试版本为 **1.33–1.36**；上游发布 1.37 并不会自动扩展该兼容矩阵。支持的主机系统为 AMD64/AArch64 Linux，内核版本 **5.10+**；也支持文档中注明的发行版等效版本，例如 RHEL 8.10 回移植的 4.18 内核。各项功能还有额外要求。

> **最后更新**：2026年10月26日

### 历史版本发布说明

下方日期为 GitHub 上的 UTC 发布时间，描述的是相应版本，而不是当前安装版本固定项。不同版本线的功能回移情况各不相同。

| 日期 | 版本 | 已核实的要点 |
| --- | --- | --- |
| 2026年7月14日 | [1.20.0-rc.0](https://github.com/cilium/cilium/releases/tag/v1.20.0-rc.0) | 1.20 的首个候选发布版本 |
| 2026年7月16日 | [1.19.6](https://github.com/cilium/cilium/releases/tag/v1.19.6), [1.18.12](https://github.com/cilium/cilium/releases/tag/v1.18.12), [1.17.18](https://github.com/cilium/cilium/releases/tag/v1.17.18) | 1.19.6/1.18.12 列出了 Gateway 访问日志配置；此处提到的重启策略和 ClusterMesh 亲和性修复列于 1.19.6，并非全部三个版本 |
| 2026年7月21日 | [1.20.0-rc.1](https://github.com/cilium/cilium/releases/tag/v1.20.0-rc.1) | 1.20 的第二个候选发布版本 |
| 2026年7月29日 | [1.20.0](https://github.com/cilium/cilium/releases/tag/v1.20.0) | GA 正式发布；下方列出部分变更 |
| 2026年8月3日 | [1.21.0-pre.0](https://github.com/cilium/cilium/releases/tag/v1.21.0-pre.0) | 下一周期的预发布版本，不是本指南的部署基线 |
| 2026年8月18日 | [1.20.1](https://github.com/cilium/cilium/releases/tag/v1.20.1) | ClusterMesh 文档和错误修复，包括重启/CIDR 策略处理 |
| 2026年8月18日 | [1.19.7](https://github.com/cilium/cilium/releases/tag/v1.19.7) | 包含 ENI 接口时序、Service/LB 及其他修复 |
| 2026年8月18日 | [1.18.13](https://github.com/cilium/cilium/releases/tag/v1.18.13) | VRRP/IGMP 主机防火墙支持及相关修复 |
| 2026年9月9日 | [1.21.0-pre.2](https://github.com/cilium/cilium/releases/tag/v1.21.0-pre.2) | 预发布版本；其变更日志涵盖 pre.0 到 pre.2，因为 **1.21.0-pre.1 从未发布** |
| 2026年9月16日 | [1.20.2](https://github.com/cilium/cilium/releases/tag/v1.20.2) | 错误修复包括 ENI IPAM 前缀委派的分配/释放和辅助 VPC CIDR 处理、ClusterMesh 修复、策略变更后立即创建的 Pod 的策略修订、LocalRedirectPolicy 回归问题，以及升级在 v1.15 或更早版本中创建的集群（`CiliumNodeConfig v2alpha1` CRD 版本） |
| 2026年9月16日 | [1.19.8](https://github.com/cilium/cilium/releases/tag/v1.19.8), [1.18.14](https://github.com/cilium/cilium/releases/tag/v1.18.14) | 较旧受支持版本线的补丁版本 |
| 2026年10月2日 | [1.21.0-pre.3](https://github.com/cilium/cilium/releases/tag/v1.21.0-pre.3) | 最新的 1.21 预发布版本；**1.21 目前仅有预发布版本（尚无 GA 正式版）**，本指南中标记为 1.21 的内容可能会变化 |
| 2026年10月15日 | [1.20.3](https://github.com/cilium/cilium/releases/tag/v1.20.3) | Gateway API 依赖项 v1.6.3、conntrack GC 和带有 `nodeSelector` 的 CNP 处理等修复；这是本指南当前审查所依据的基线 |
| 2026年10月15日 | [1.19.9](https://github.com/cilium/cilium/releases/tag/v1.19.9), [1.18.15](https://github.com/cilium/cilium/releases/tag/v1.18.15) | 较旧受支持版本线的补丁版本 |
| 2026年10月23日 | [1.20.4](https://github.com/cilium/cilium/releases/tag/v1.20.4), [1.19.10](https://github.com/cilium/cilium/releases/tag/v1.19.10), [1.18.16](https://github.com/cilium/cilium/releases/tag/v1.18.16) | 带外安全补丁版本，用于修复 CVE-2026-111943：将 Go 升级到 1.26.10，使被攻陷的 eMudhra 中间 CA 证书不再受信任；此外还包括依赖项补丁更新和回移植的修复 |

2026年9月14日，CNCF 博客发布了 [Cilium 1.20 功能回顾](https://www.cncf.io/blog/2026/09/14/cilium-1-20-gateway-api-externalauth-tcproute-udproute-eni-ipam-for-ipv6-and-more/)（Gateway API ExternalAuth、TCPRoute/UDPRoute、IPv6 ENI IPAM 等），内容范围与下方 1.20.0 公告摘要相同。

1.20.0 公告称该版本包含 **2,660+ 次新提交**，由 **1,100+ 名贡献者组成的社区**支持。后者指社区规模，并非该版本的作者人数。主要亮点包括：

- Gateway API **1.6.1**、TCPRoute/UDPRoute、BackendTLSPolicy、ListenerSets、ExternalAuth 和 CORS 支持，具体取决于各功能的配置和 API 成熟度。
- 数据路径插件和可选启用的 `bpf.datapathMode=auto`；公告中仍将 veth 列为默认值。双栈集群可以配置 IPv6 出口网关地址。
- **Beta** 版 IPv6 ENI IPAM，以及无需重建集群即可从 cluster-pool 迁移到 multi-pool。就地迁移并不保证不会中断。
- 流量分发提示、加权 Maglev 后端和稳定的 MCS 集成；支持 Kubernetes ClusterNetworkPolicy，以及基于 ztunnel 的 **Beta** 工作负载身份。
- 据报告，`cilium-cni` 二进制文件大小从约 **77 MB 缩减到 16 MB**。ADS/Delta xDS 改进见于 1.20 公告；不要将这些改进归入 1.18.13 补丁说明。这些是上游版本发布声明，并非本次审查中重新测量的结果。

请查阅 [1.20 升级说明](https://docs.cilium.io/en/v1.20/operations/upgrade/#upgrade-notes)，了解相互身份验证（**在 1.20 中已弃用**，在 1.21 预发布版本中移除）、已移除/替换的 Envoy Go 扩展、Kafka 感知策略、旧版 CiliumNodeConfig API、libnetwork 集成以及自定义 CNI 配置变更。

### NetworkPolicy 安全公告

[GHSA-fm8w-2m5w-9j7r / CVE-2026-56743](https://github.com/cilium/cilium/security/advisories/GHSA-fm8w-2m5w-9j7r) 的项目公告发布日期为 **2026年7月6日**。项目 API 和 GitHub 全局公告 API 提供的日期不同：后者记录为 9 月 3 日。本版本时间线使用项目披露日期；全局记录日期并不代表之后才发布了修复版本。根据公告中的自定义集群名称条件，该问题影响 **1.19.0–1.19.4**：仅包含 `ipBlock` 的标准 Kubernetes NetworkPolicy 对等端可能会意外允许来自所选 Pod 所在命名空间内工作负载的入站流量。**1.19.5** 修复了此问题；部署时请使用适当的当前补丁版本。公告指出，CiliumNetworkPolicy/ClusterwideNetworkPolicy 以及低于 1.19.0 的版本不受此特定错误影响。

## 简介

Cilium 为受支持的 Linux Kubernetes 环境提供网络、安全和可观测性功能。路由、IPAM、加密和 Service 处理是不同的选择；仅选择 eBPF 并不能启用所有功能，也不构成性能保证。旧版 Docker libnetwork 集成已在 1.20 中移除，因此不应再将 Docker/Mesos 列为可互换的当前安装目标。

### eBPF 与关键功能

内核会在加载 eBPF 程序前对其进行验证，并可在受支持的挂载点将其 JIT 编译后执行。这样可以在无需自定义内核模块的情况下处理数据包并实现可观测性；但验证器无法证明应用程序或策略正确。实际吞吐量、延迟和内存用量取决于程序、平台和工作负载。

Cilium 提供 L3/L4 策略、通过 Envoy/DNS 代理集成实现的 L7 策略、可选 WireGuard/IPsec、Service 负载均衡、Hubble 流量可视化、ClusterMesh 和 BGP 通告。XDP 加速是可选功能，并取决于设备和配置。L7 功能可能会使用每节点 Envoy；通过 ztunnel 实现的工作负载身份需要单独配置 Beta 功能。仅安装 Agent 并不会启用所有网格、加密或多集群行为。

### 与其他网络项目的比较

| 项目 | 连通性 / IPAM | 策略及相关功能 |
| --- | --- | --- |
| Cilium | 原生或覆盖网络路由；包括云 ENI 在内的多种 IPAM 模式 | eBPF 数据平面、Cilium/Kubernetes 策略、L7 集成、Hubble 和可选加密 |
| Calico | 原生/IPIP/VXLAN 配置，可使用 Calico 或外部 IPAM | Linux Iptables/Nftables/BPF、受支持的 Windows HNS；开源版 WireGuard、分阶段策略和单独的 L7 集成 |
| Flannel | 通过所选后端（如 VXLAN/host-gw/WireGuard）提供 Pod 连通性 | 路由守护进程本身不执行 NetworkPolicy；其 Helm Chart 可通过 `netpol.enabled` 部署 SIGs network-policy 控制器，也可与其他策略实现搭配使用 |
| AWS VPC CNI | VPC ENI 地址分配/网络连接 | 在受支持的 EC2 Linux 节点上提供原生网络策略，以及单独的 Pod 安全组功能；EKS Auto Mode 是另一种托管实现 |

路由模式与数据包处理实现不属于同一类别。Calico 并不局限于 iptables/IPVS，Flannel 可以使用加密后端，而 AWS 策略也不等同于安全组。Service mesh 是可选层，跨集群 VPC 连通性也不局限于 Transit Gateway。应使用经过测量的工作负载和明确的支持矩阵，而不是笼统地对性能进行排名。

## 架构

**Kubernetes API server** 存储 Kubernetes/Cilium 资源。Cilium Agent 会监视相关状态，并对每个节点的数据平面进行编程；Cilium Operator 负责集群级任务，例如所选 IPAM 模式以及身份/控制器相关工作。这个基础架构中没有必须单独部署的集群级“Cilium API Server”。Agent 提供本地 API，而可选的 ClusterMesh API server 用途不同。

| 组件 | 作用 |
| --- | --- |
| Cilium Agent | 节点本地端点、策略、路由/Service 状态和 eBPF 管理 |
| Cilium Operator | 集群级协调，以及依赖运行模式的分配/控制器工作 |
| Envoy | 为已启用的 L7 策略、入口/Gateway 及相关功能提供用户空间代理 |
| Hubble server | 与 Agent 集成的节点本地流量 API |
| Hubble Relay / UI | 汇总流量流 / 显示 Service 映射和流量 |
| Prometheus 指标端点 | 单独收集统计信息；Relay/UI 并非指标抓取管道 |
| cilium / cilium-dbg / hubble | 分别用于集群管理、Agent 诊断和流量客户端的 CLI |

### 网络与数据包路径

原生路由需要可达的底层网络；隧道模式使用 VXLAN 或 Geneve。AWS ENI 和 Azure IPAM 是地址分配/集成方式，各自有平台要求。Cilium 的 BGP Control Plane 会向路由器通告可达性，**不会对数据路径进行编程，也不提供集群内部路由**。

不存在通用的 XDP→TC→Pod 顺序。Socket 负载均衡可以在数据包产生之前发挥作用，TC/netkit 挂载点取决于数据路径，可选 XDP 用于加速特定流量，而 L7 流量可能会经过 Envoy。返回流量同样取决于 NAT、conntrack 和 DSR 选项。请参阅网络和 eBPF 章节，了解所选配置。

## 与 Amazon EKS 集成

安装任何组件之前，先选择实际的网络和计算配置。示例中的附加组件名称/版本 `cilium` / `v1.17.0-eksbuild.1` 并非经过验证的 AWS 发行版本，因此此处不会将其作为安装命令。如果考虑使用打包的供应商附加组件，请检查所在 Region 的实际附加组件目录、发布方、许可证和受支持的计算类型。

| EKS 配置 | 需要核实的内容 |
| --- | --- |
| 普通 EC2 节点，由 Cilium ENI 替代 VPC CNI | 上游/合作伙伴管理的 CNI；AWS 支持的 EC2 CNI 是 VPC CNI。规划 CNI 所有权、IAM、地址分配、路由、引导过程和节点迁移 |
| 普通 EC2 节点，采用 AWS VPC CNI 链式模式 | VPC CNI 负责接口/IPAM；Cilium 随后挂接其数据平面。现有 Pod 需要重新创建，且 L7/IPsec 有文档注明的限制 |
| Hybrid Nodes | 遵循 AWS 专用 CNI 指南和 AWS 维护的 Cilium 构建矩阵；上游 1.20.3 不会自动成为 AWS 支持的构建版本 |
| Auto Mode | 不支持替代 CNI/策略插件；请使用托管的 NodeClass/网络功能 |
| Fargate | 不支持替代 CNI/DaemonSet 安装 |
| Windows | Cilium Agent 的要求是 Linux；不要将此方案用于 Windows 工作节点 |

AWS 的通用替代 CNI 页面与 Hybrid 专用指南对 Calico 支持的表述有所不同；示例中的仓库迁移并不能证明支持已终止。对于 Hybrid Nodes，请确认确切的发行版本、功能集和支持责任方。对于 Auto Mode，本指南中的节点本地 CoreDNS/系统网络也不同于普通 EC2 设置；混合使用的非 Auto 节点仍需要传统 DNS Deployment。

### 已准备好的、采用 Cilium ENI 的 EC2 集群

以下是为已准备好的 IPv4 EC2 集群提供的 **Cilium Helm values**，不是完整的集群创建或就地迁移方案。使用前：

1. 选择受支持的 EKS/Kubernetes 版本和 Linux AMI，并确定唯一的 CNI 所有者。不要为了走捷径而从现有工作负载集群中删除 `aws-node`。
2. 准备节点污点/调度配置，使工作负载等待 Cilium 管理节点。上游 EKS 指南使用 `node.cilium.io/agent-not-ready=true:NoExecute`；请评估其对实际节点生命周期中驱逐和引导的影响。
3. 准备子网容量、ENI 配额/安全组、节点元数据访问权限，以及 Operator 所需的 EC2 权限。下方的角色 ARN 是一个正确配置了信任关系的 **cilium-operator ServiceAccount** 角色占位符，并非由 values 文件创建的角色。
4. 对于这个 `kubeProxyReplacement: false` 示例，保留可正常工作的 kube-proxy 和 DNS。若使用替代模式，请遵循单独的直接 API/引导 DNS 要求。max-Pods 应根据实际实例/IPAM 容量选择，不要一概设为 110。

保存为 `cilium-eni-values.yaml`，并将角色/接口选项替换为经过审查的值：

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

通过安装责任方管理这些设置。若用只包含少数几个键的 `cilium-config` 替换现有配置，可能会删除其他必需设置；旧的 `tunnel=disabled` 值已由 `routingMode: native` 取代。ENI 分配/权限和 SNAT 行为仍需在运行时验证；成功渲染并不能证明 EC2 网络可用。

**IPv6 说明**：1.20.3 ENI IPAM 参考文档将 IPv6 描述为 Beta，而其 EKS 前提条件页面仍指出 ENI 集成仅支持 IPv4。本指南保留 IPv4 示例，并记录这处文档不一致，而不将任一表述视为 EKS 生产环境 IPv6 兼容性的证明。开展单独的 IPv6 设计前，请核查当前 ENI/双栈子网要求。

### VPC CNI 链式模式替代方案

上游链式模式指南要求 VPC CNI 1.11.2+，并记录了以下配置：

```yaml
cni:
  chainingMode: aws-cni
  exclusive: false
enableIPv4Masquerade: false
routingMode: native
kubeProxyReplacement: false
```

请将其用作**另一种独立配置**，而不是叠加到 ENI 替代模式的 values 上。VPC CNI 仍负责地址分配。应由其所有者升级实际的托管附加组件，而不是应用历史版本的上游 DaemonSet。避免在相同端点上运行相互竞争的策略引擎。更改 CNI 链并不会将 Cilium 追溯性地挂接到现有 Pod；应在规划好的滚动过程中重新创建这些 Pod，并验证端点管理情况。链式模式有文档注明的 L7 策略/IPsec 限制，因此不要假定本页后续的每个示例都适用于该配置。

### ClusterMesh

ClusterMesh 需要唯一的集群标识、兼容的版本、可达且不重叠的 Pod 网络、经过身份验证的 API 连通性，以及适当的暴露方式。LoadBalancer Service 可能会创建云资源，因此需要经过审慎设计的网络/安全方案。创建两个公共端点并不足以安全地连接集群。请遵循维护中的 [ClusterMesh 指南](13-clustermesh-install-upgrade.md)以及适用于所选拓扑的高级章节。

## 安装与配置

### 客户端工具

请为工作站操作系统/架构选用官方 Cilium CLI 0.20.1 和 Hubble CLI 1.20.2 对应的资源，并在解压前验证随附的校验和。Linux ARM64 与 AMD64 的资源不同；macOS 使用对应的 Darwin 资源。CLI 版本与 Cilium Agent/Helm Chart 版本相互独立。请参阅[已核实的 CLI 安装指南](../../service-mesh/cilium-service-mesh/README.md)。

```bash
cilium version --client
hubble version
```

### 非云集群的 cluster-pool 示例

以下**替代方案**适用于已准备好的普通 Linux 集群，其中 kube-proxy 和 DNS 已正常工作。确保示例中的 `10.244.0.0/16` Pod 地址段与集群兼容，并且不与 Service、节点、VPC 或互联网络地址段重叠。ENI 模式不要使用此地址池配置。

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

保存为 `cilium-values.yaml`，渲染固定版本的 Helm Chart，然后仅在已准备好的集群上安装：

```bash
helm template cilium cilium/cilium --version 1.20.3 \
  --namespace kube-system -f cilium-values.yaml > cilium-rendered.yaml
helm install cilium cilium/cilium --version 1.20.3 \
  --namespace kube-system -f cilium-values.yaml
cilium status --wait
```

对于现有版本，请使用其升级/GitOps 流程，保留由其管理的 values，并遵循对应版本的升级流程。重复使用 `cilium install` 示例并不是更改单个设置的通用方法。

| 选项 | 当前配置和前提条件 |
| --- | --- |
| VXLAN/Geneve | 使用 `routingMode: tunnel` 和 `tunnelProtocol`；允许所选封装协议，并根据路径设置 MTU |
| 原生路由 | 使用 `routingMode: native`；底层网络必须能够路由 Pod 地址。`autoDirectNodeRoutes` 需要适当的直接连通性，而非任意多子网路由 |
| kube-proxy 替代模式 | 使用 `kubeProxyReplacement: true` 或 `false`，而非旧版 `strict`；替代模式要求 `k8sServiceHost`/`k8sServicePort` 可达，并且需要采用文档说明的引导方案 |
| WireGuard | 检查内核/平台和对等端路径后，启用受支持的加密模式；它不会自动加密所有可能的流量路径 |
| IPsec | 需要文档说明的密钥 Secret、密钥分发/轮换和兼容模式；仅设置 Helm 启用标志并不完整 |
| XDP/DSR/BBR | 需要根据设备/内核/拓扑单独选择，不是通用安装预设 |

## 网络策略

Kubernetes `networking.k8s.io/v1` NetworkPolicy 和 Cilium `cilium.io/v2` 策略是不同的 API。多个允许策略可以组合生效。以下示例使用**分别准备的测试命名空间**，避免 L4 允许规则悄然绕过 L7 限制。在得出结论前，请检查所有选中实际端点的策略。

### L4 示例

在 `cilium-l4-demo` 中，此策略选中后端 Pod，并允许来自同一命名空间前端 Pod、发往 TCP 8080 的入站流量：

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

在另一个独立的 `cilium-l7-demo` 命名空间中，此策略选中后端 Pod，并将来自该命名空间前端 Pod、发往 TCP 8080 的明文 HTTP 流量限制为指定方法/路径。所选 CNI 模式必须支持 L7 代理；如果没有受支持的终止配置，则不会自动检查加密的 HTTP 流量。

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

不要为相同的对等端/端口添加匹配的、不受限制的 L4 允许规则：Cilium 文档指出，此类允许规则会使更严格的 L7 限制失效。L7 拒绝可能返回 HTTP 403，而不是丢弃数据包。请使用真实端点身份测试允许的 GET 请求以及被拒绝的方法/路径。

### DNS/FQDN 示例

在 `cilium-dns-demo` 中，此策略允许向普通 CoreDNS Pod 发起 DNS 查询，并允许连接到为 `api.example.com` 学习到的地址的 TCP 443 流量。该域名仅为示例；请将其替换为经过批准的目标。此处省略了宽泛的 `*.amazonaws.com` 通配符，因为它并不能界定账户/资源范围。

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

DNS 通配符允许向所选解析器发起查询，而不是连接到所有返回的地址。它仍可能承载任意 DNS 名称；如有需要，请考虑 DNS 搜索后缀并限制查询名称。NodeLocal DNS 或其他解析器需要正确选择目标。FQDN 策略是基于 DNS 的 IP 授权，并非 TLS 主机名验证或 HTTP URL 授权；共享 IP 以及应用的 TLS/身份验证仍然重要。

## 使用 Hubble 实现可观测性

上方的 cluster-pool values 启用了 Relay/UI 和组件指标。对于现有安装，请通过其配置责任方应用预期的 Hubble values；`cilium hubble enable --ui` 是受支持的便捷命令，但 `cilium hubble enable --metrics=...` 并非受支持的 0.20.1 CLI 标志。请改用 Helm values 配置 `hubble.metrics.enabled`。不要同时启用旧版 `http` 和 `httpV2` 处理程序。

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

此本地示例假定使用默认 Relay server 配置；启用 TLS 的 Relay 需要相应的客户端信任/身份验证配置。只有流量经过配置好的 L7 代理时，才会产生 HTTP 事件。`DROPPED` 表示数据路径判定，并不涵盖所有应用请求失败。请使用 `cilium hubble ui` 转发 UI 端口，并单独配置 Prometheus 目标发现以收集指标。Hubble 流量流本身并不等同于分布式应用跟踪。

## 测试与运维

连通性/性能命令会创建测试工作负载，还可能更改策略或产生大量流量。请在经过审查的测试命名空间/环境中运行，并确保拥有相应权限；本次审查没有在集群上执行这些命令。

```bash
cilium connectivity test --help
cilium connectivity perf --help
```

性能子命令是 `cilium connectivity perf`；`connectivity test --test=performance` 只是提供测试名称筛选条件，并非性能测试运行器。比较吞吐量/延迟之前，请记录软件版本、拓扑、流量和原始结果。

检查时，应区分管理 CLI 与**Agent 侧的 `cilium-dbg`**：

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

`cilium endpoint list`、`cilium bpf maps list` 和 `cilium metrics list` 并不是管理 CLI 中功能等效的命令。`cilium sysdump` 可以收集诊断材料；请妥善保护由此产生的基础设施/日志数据。Agent 处于 Ready 状态或抓取指标成功，不能替代应用测试和负向策略测试。

### 运维优先事项

- 启用映射表预分配、XDP、DSR、BBR 或固定设备模式之前，先进行测量。这些功能会消耗资源或改变数据包路径，需要针对具体功能进行检查。
- 在选定范围内引入默认拒绝策略，并明确允许 DNS、API、身份和应用依赖项。除了已建立的连接，也要检查新 Pod 和升级期间的状态转换。
- 将加密、证书/密钥轮换、策略强制执行和可观测性分别纳入验收检查。保留可用的管理/恢复路径。
- 审查当前平台矩阵和受支持的升级路径。历史版本公告不能证明当前部署兼容性。

## 深入解析目录

**[Cilium 简介与基本概念](01-introduction.md)**
- Cilium 概述与历史
- 容器网络基础
- 了解 CNI（容器网络接口）
- Cilium 的差异化功能

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
- 了解 OSI 模型各层（L2、L3、L4、L7）
- Cilium 的分层功能
- Service mesh 集成
- 负载均衡架构
- 伪装配置与实现模式
- IPv4 分片处理

**[安全与可视性](06-security-visibility.md)**
- Cilium 的安全功能
- 网络可视性与监控
- Hubble 架构与使用
- 实时威胁检测

**[高级主题与真实案例](07-advanced-topics.md)**
- 性能调优与故障排除
- 大规模部署策略
- 真实用例研究
- 未来路线图与开发方向

**[深入解析 eBPF 数据路径内部机制](08-ebpf-datapath-internals.md)**
- 程序集、挂载点和尾调用
- BPF 映射目录、大小设定和编译/加载流程
- 策略强制执行路径与 Hubble 事件管道

**[覆盖路由与原生路由](09-overlay-native-routing.md)**
- VXLAN/Geneve、VNI 中的身份、MTU 和数据包路径分析
- 原生路由、伪装、主机路由、DSR 和 netkit
- EKS 决策表：覆盖网络、ENI 与 VPC CNI 链式模式

**[深入解析 IPAM](10-ipam-deep-dive.md)**
- 每种 IPAM 模式、容量计算和决策矩阵
- Multi-pool、`CiliumPodIPPool`、ENI、LB IPAM、Node IPAM
- 耗尽问题排查与 1.21 API 变更

**[BGP、负载均衡器 IP 和出口流量](11-bgp-lb-egress-edge.md)**
- BGP Control Plane v2 CRD、通告和检查
- L2 通告、Egress Gateway、Local Redirect Policy
- Gateway API 要求及 EKS 仅限内部的暴露方式

**[mTLS、加密与身份](12-mtls-encryption-identity.md)**
- 身份模型、策略语义和审计模式
- 相互身份验证时间线、ztunnel 工作负载 mTLS
- WireGuard、IPsec、Hubble 和证书管理

**[版本、安装/升级与 Cluster Mesh](13-clustermesh-install-upgrade.md)**
- 1.17–1.21 功能矩阵、升级和回滚规则
- EKS 安装细节、Cluster Mesh 和 MCS-API

## 其他资源

- [深入了解网络概念](networking-concepts.md)
- [术语表与缩写](glossary.md)

## 参考资料

- [Cilium 1.20 Kubernetes 兼容性](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/network/kubernetes/compatibility.rst)
- [Cilium 系统要求](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/operations/system_requirements.rst)
- [EKS 前提条件](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/installation/requirements-eks.rst)
- [Cilium ENI IPAM](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/network/concepts/ipam/eni.rst)
- [AWS 替代 CNI 支持](https://docs.aws.amazon.com/eks/latest/userguide/alternate-cni-plugins.html)
- [AWS Hybrid Nodes CNI](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-cni.html)
- [Cilium L7 策略语义](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/security/policy/layer7.rst)
- [Hubble 项目](https://github.com/cilium/hubble)
- [Flannel 网络与策略集成](https://github.com/flannel-io/flannel)
- [Calico 对比术语](../calico/glossary.md)

## 测验

检验你在本节中的学习成果，请尝试 [Cilium 深入解析测验](../../quizzes/networking/cilium/01-introduction-quiz.md)。
