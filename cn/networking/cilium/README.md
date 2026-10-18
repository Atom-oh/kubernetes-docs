# Cilium 深入解析：云原生网络的未来

## 概述与审查基线

本节介绍 Cilium 网络、策略和可观测性。示例已根据 **Cilium/Helm chart 1.20.3**、Cilium CLI **0.20.1** 和 Hubble CLI **1.20.2** 进行审查。Cilium 1.20 Kubernetes 兼容性页面列出的测试版本为 **1.33–1.36**；上游发布 1.37 并不会自动扩展该兼容性矩阵。支持的主机为 AMD64/AArch64 Linux，内核版本需为 **5.10+**；或者使用文档中列出的发行版等效版本，例如 RHEL 8.10 回移植的 4.18 内核。各项功能还有额外要求。

> **最后更新**：October 16, 2026

### 历史版本发布说明

以下日期为 GitHub 上的 UTC 发布日期，描述的是对应版本，而非当前安装锁定版本。不同发布线的功能回移情况有所不同。

| 日期 | 版本 | 已核实的要点 |
| --- | --- | --- |
| July 14, 2026 | [1.20.0-rc.0](https://github.com/cilium/cilium/releases/tag/v1.20.0-rc.0) | 首个 1.20 候选版本 |
| July 16, 2026 | [1.19.6](https://github.com/cilium/cilium/releases/tag/v1.19.6), [1.18.12](https://github.com/cilium/cilium/releases/tag/v1.18.12), [1.17.18](https://github.com/cilium/cilium/releases/tag/v1.17.18) | Gateway 访问日志配置列于 1.19.6/1.18.12；此处提到的重启策略和 ClusterMesh 亲和性修复列于 1.19.6，并非全部三个版本 |
| July 21, 2026 | [1.20.0-rc.1](https://github.com/cilium/cilium/releases/tag/v1.20.0-rc.1) | 第二个 1.20 候选版本 |
| July 29, 2026 | [1.20.0](https://github.com/cilium/cilium/releases/tag/v1.20.0) | GA 版本；下文列出部分变更 |
| August 3, 2026 | [1.21.0-pre.0](https://github.com/cilium/cilium/releases/tag/v1.21.0-pre.0) | 下一周期的预发布版本，不是本指南的部署基线 |
| August 18, 2026 | [1.20.1](https://github.com/cilium/cilium/releases/tag/v1.20.1) | ClusterMesh 文档和错误修复，包括重启/CIDR 策略处理 |
| August 18, 2026 | [1.19.7](https://github.com/cilium/cilium/releases/tag/v1.19.7) | 包含 ENI 接口时序、Service/LB 及其他修复 |
| August 18, 2026 | [1.18.13](https://github.com/cilium/cilium/releases/tag/v1.18.13) | VRRP/IGMP 主机防火墙支持及相关修复 |
| September 9, 2026 | [1.21.0-pre.2](https://github.com/cilium/cilium/releases/tag/v1.21.0-pre.2) | 预发布版本；其变更日志涵盖 pre.0 到 pre.2，因为 **1.21.0-pre.1 从未发布** |
| September 16, 2026 | [1.20.2](https://github.com/cilium/cilium/releases/tag/v1.20.2) | 错误修复包括 ENI IPAM 前缀委派的分配/释放和辅助 VPC CIDR 处理、ClusterMesh 修复、策略变更后立即创建的 Pod 的策略修订、LocalRedirectPolicy 回归，以及升级在 v1.15 或更早版本中创建的集群（`CiliumNodeConfig v2alpha1` CRD 版本） |
| September 16, 2026 | [1.19.8](https://github.com/cilium/cilium/releases/tag/v1.19.8), [1.18.14](https://github.com/cilium/cilium/releases/tag/v1.18.14) | 较旧受支持版本线的补丁版本 |
| October 2, 2026 | [1.21.0-pre.3](https://github.com/cilium/cilium/releases/tag/v1.21.0-pre.3) | 最新的 1.21 预发布版本；**1.21 目前仅有预发布版本（尚无 GA 版本）**，本指南中标记为 1.21 的内容可能会变更 |
| October 15, 2026 | [1.20.3](https://github.com/cilium/cilium/releases/tag/v1.20.3) | Gateway API 依赖项 v1.6.3、conntrack GC 和对带有 `nodeSelector` 的 CNP 的处理等修复；也是本指南当前审查的基线 |

2026 年 9 月 14 日，CNCF 博客发布了 [Cilium 1.20 功能回顾](https://www.cncf.io/blog/2026/09/14/cilium-1-20-gateway-api-externalauth-tcproute-udproute-eni-ipam-for-ipv6-and-more/)（Gateway API ExternalAuth、TCPRoute/UDPRoute、IPv6 ENI IPAM 等），覆盖了与下文 1.20.0 公告摘要相同的范围。

1.20.0 公告报告称新增了 **2,660+ 个提交**，由一个 **1,100+ 名贡献者的社区**提供支持。后者指社区规模，并非此版本作者人数。主要内容包括：

- Gateway API **1.6.1**、TCPRoute/UDPRoute、BackendTLSPolicy、ListenerSets、ExternalAuth 和 CORS 支持，具体取决于各功能的配置和 API 成熟度。
- Datapath 插件和可选启用的 `bpf.datapathMode=auto`；公告所述的默认模式仍为 veth。双栈集群可以配置 IPv6 Egress Gateway 地址。
- **Beta** IPv6 ENI IPAM，以及无需重建集群即可从 cluster-pool 迁移到 multi-pool。原地迁移并不保证不中断。
- 流量分布提示、加权 Maglev 后端和稳定的 MCS 集成；支持 Kubernetes ClusterNetworkPolicy 和基于 ztunnel 的工作负载身份（**Beta**）。
- 据报告，`cilium-cni` 二进制文件大小从约 **77 MB 减少到 16 MB**。ADS/Delta xDS 改进已列于 1.20 公告；不要将其归入 1.18.13 补丁说明。这些是上游版本发布声明，并非本次审查重新测量的结果。

请查看 [1.20 升级说明](https://docs.cilium.io/en/v1.20/operations/upgrade/#upgrade-notes)，了解 Mutual Authentication（**在 1.20 中已弃用**，并在 1.21 预发布版本中移除）、已移除/替换的 Envoy Go 扩展、Kafka 感知策略、旧版 CiliumNodeConfig API、libnetwork 集成以及自定义 CNI 配置变更。

### NetworkPolicy 安全公告

[GHSA-fm8w-2m5w-9j7r / CVE-2026-56743](https://github.com/cilium/cilium/security/advisories/GHSA-fm8w-2m5w-9j7r) 的项目公告发布日期为 **July 6, 2026**。项目 API 与 GitHub 全局公告 API 暴露的日期不同：后者记录的日期为 September 3。此版本时间线采用项目披露日期；全局记录日期并不代表有更晚的修复版本。根据公告中的自定义集群名称条件，此问题影响 **1.19.0–1.19.4**：仅包含 `ipBlock` 的标准 Kubernetes NetworkPolicy 对等端可能会无意中允许来自所选 Pod 所在命名空间中工作负载的入口流量。**1.19.5** 修复了此问题；部署时请使用适当的当前已打补丁版本。公告称，CiliumNetworkPolicy/ClusterwideNetworkPolicy 以及低于 1.19.0 的版本不受此特定错误影响。

## 简介

Cilium 为受支持的 Linux Kubernetes 环境提供网络、安全和可观测性。路由、IPAM、加密和 Service 处理是彼此独立的选项；仅选择 eBPF 并不能启用所有功能，也不代表性能有保证。旧版 Docker libnetwork 集成已在 1.20 中移除，因此不应再将 Docker/Mesos 列为可互换的当前安装目标。

### eBPF 与关键能力

内核会在加载 eBPF 程序前验证程序，并可在受支持的挂载点将其 JIT 编译后执行。这使得无需自定义内核模块即可进行数据包处理和可观测性；但验证器并不能证明应用或策略正确。实际吞吐量、延迟和内存占用取决于程序、平台和工作负载。

Cilium 提供 L3/L4 策略、通过 Envoy/DNS 代理集成实现的 L7 策略、可选的 WireGuard/IPsec、Service 负载均衡、Hubble 流可见性、ClusterMesh 和 BGP 通告。XDP 加速为可选功能，具体取决于设备和配置。L7 功能可能会使用每个节点上的 Envoy；通过 ztunnel 实现工作负载身份需要单独的 Beta 配置。仅安装 agent 并不会启用所有网格、加密或多集群行为。

### 与其他网络项目的比较

| 项目 | 连接性 / IPAM | 策略及相关能力 |
| --- | --- | --- |
| Cilium | 原生或覆盖网络路由；包括云 ENI 在内的 IPAM 模式 | eBPF 数据平面、Cilium/Kubernetes 策略、L7 集成、Hubble 和可选加密 |
| Calico | 使用 Calico 或外部 IPAM 的原生/IPIP/VXLAN 配置 | Linux Iptables/Nftables/BPF、受支持的 Windows HNS；OSS WireGuard、分阶段策略和独立的 L7 集成 |
| Flannel | 通过所选后端（如 VXLAN/host-gw/WireGuard）提供 Pod 连接 | 路由守护进程本身不执行 NetworkPolicy；其 chart 可通过 `netpol.enabled` 部署 SIGs network-policy 控制器，也可以与其他策略实现搭配使用 |
| AWS VPC CNI | VPC ENI 地址分配/网络 | 在受支持的 EC2 Linux 节点上提供原生网络策略，以及独立的 SG-for-Pods 功能；EKS Auto Mode 是另一种托管实现 |

路由模式与数据包处理实现并非同一类别。Calico 并不局限于 iptables/IPVS，Flannel 可以使用加密后端，AWS 策略也不等同于安全组。Service mesh 是可选层，跨集群 VPC 连接也不局限于 Transit Gateway。应使用经过测量的工作负载和明确的支持矩阵，而不是采用普遍适用的性能排名。

## 架构

**Kubernetes API server** 存储 Kubernetes/Cilium 资源。Cilium agent 监视相关状态并配置每个节点的数据平面；Cilium Operator 负责集群级任务，例如所选 IPAM 模式以及身份/控制器工作。在这一基本架构中，并不存在一个必需的、独立的全局 “Cilium API Server” 部署。Agent 具有本地 API，而可选的 ClusterMesh API server 用途不同。

| 组件 | 作用 |
| --- | --- |
| Cilium Agent | 管理节点本地端点、策略、路由/Service 状态和 eBPF |
| Cilium Operator | 负责集群级协调，以及依模式而定的分配/控制器工作 |
| Envoy | 为已启用的 L7 策略、入口/Gateway 及相关功能提供用户空间代理 |
| Hubble server | 与 agent 集成的节点本地流 API |
| Hubble Relay / UI | 聚合流数据 / 显示 Service 映射和流量 |
| Prometheus metrics endpoints | 单独收集统计信息；Relay/UI 并不是指标抓取管线 |
| cilium / cilium-dbg / hubble | 分别用于集群管理 CLI / agent 诊断 / 流量客户端 |

### 网络与数据包路径

原生路由需要可达的底层网络；隧道模式使用 VXLAN 或 Geneve。AWS ENI 和 Azure IPAM 是各自具有平台要求的分配/集成选项。Cilium 的 BGP Control Plane 会向路由器通告可达性，**不会配置数据平面，也不提供内部集群路由**。

不存在通用的 XDP→TC→Pod 顺序。Socket 负载均衡可以在数据包尚未生成时生效；TC/netkit 挂载点取决于数据平面；可选的 XDP 会加速特定流量；L7 流量可能经过 Envoy。返回流量还取决于 NAT、conntrack 和 DSR 选项。请参阅网络和 eBPF 章节，了解所选配置。

## 与 Amazon EKS 集成

在安装任何组件之前，先选择实际的网络和计算配置。示例插件名称/版本 `cilium` / `v1.17.0-eksbuild.1` 并非经过核实的 AWS 发行版本，此处也不是安装命令。如果考虑使用打包的供应商插件，请检查所在 Region 的实际插件目录、发布者、许可证和支持的计算类型。

| EKS 配置 | 需要核实的内容 |
| --- | --- |
| 普通 EC2 节点，由 Cilium ENI 替代 VPC CNI | 上游/合作伙伴管理的 CNI；AWS 支持的 EC2 CNI 是 VPC CNI。规划 CNI 所有权、IAM、地址、路由、引导配置和节点迁移 |
| 普通 EC2 节点，采用 AWS VPC CNI chaining | VPC CNI 管理接口/IPAM；Cilium 随后附加其数据平面。现有 Pod 需要重新创建，且 L7/IPsec 有文档说明的限制 |
| Hybrid Nodes | 遵循 AWS 专用 CNI 指南和 AWS 维护的 Cilium 构建矩阵；上游 1.20.3 并不会自动成为受支持的 AWS 构建版本 |
| Auto Mode | 不支持替代 CNI/策略插件；请使用托管的 NodeClass/网络功能 |
| Fargate | 不支持替代 CNI/DaemonSet 安装 |
| Windows | Cilium agent 的要求是 Linux；不要将此方案用于 Windows 工作节点 |

AWS 的通用替代 CNI 页面与专用 Hybrid 指南对 Calico 支持的表述有所不同；示例中的仓库迁移并不能证明支持已终止。对于 Hybrid Nodes，请确认确切的发行版本、功能集和支持责任方。对于 Auto Mode，节点本地 CoreDNS/系统网络设置也不同于本指南中的普通 EC2 配置；混合部署中的非 Auto 节点仍需要传统的 DNS Deployment。

### 已准备好的采用 Cilium ENI 的 EC2 集群

以下是**已准备好的 IPv4 EC2 集群的 Cilium Helm values**，并非完整的集群创建或原地迁移方案。使用前请先：

1. 选择受支持的 EKS/Kubernetes 版本和 Linux AMI，并确定唯一的 CNI 所有者。不要为了图方便而从现有工作负载集群中删除 `aws-node`。
2. 准备好节点污点/调度配置，以便在 Cilium 管理节点之前让工作负载等待。上游 EKS 指南使用 `node.cilium.io/agent-not-ready=true:NoExecute`；请评估其对实际节点生命周期中驱逐和引导过程的影响。
3. 准备好子网容量、ENI 配额/安全组、节点元数据访问权限以及 Operator 所需的 EC2 权限。下方的角色 ARN 是一个占位值，用于正确建立信任关系的 **cilium-operator ServiceAccount** 角色；values 文件不会创建该角色。
4. 在此 `kubeProxyReplacement: false` 示例中，保留可正常工作的 kube-proxy 和 DNS。若要使用替换模式，请遵循单独的直接 API/引导 DNS 要求。请根据实际实例/IPAM 容量选择 max-Pods，不要一概使用 110。

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

请通过安装配置的所有者管理这些设置。仅包含少数几个键的替代 `cilium-config` 可能会移除其他必需设置；旧的 `tunnel=disabled` 值已由 `routingMode: native` 取代。ENI 分配/权限和 SNAT 行为仍需在运行时验证；成功渲染并不能证明 EC2 网络可用。

**IPv6 说明**：1.20.3 的 ENI IPAM 参考文档将 IPv6 标为 Beta，而其 EKS 先决条件页面仍声明 ENI 集成仅支持 IPv4。本指南保留 IPv4 示例，并记录这一文档矛盾，而不将任一说法视为 EKS 生产环境 IPv6 兼容性的证明。在单独设计 IPv6 方案之前，请查阅当前的 ENI/双栈子网要求。

### VPC CNI Chaining 替代方案

上游 chaining 指南要求 VPC CNI 1.11.2+，并记录了以下配置：

```yaml
cni:
  chainingMode: aws-cni
  exclusive: false
enableIPv4Masquerade: false
routingMode: native
kubeProxyReplacement: false
```

请将其作为**另一种配置**使用，不要将其叠加到替代 ENI 的配置上。VPC CNI 仍负责地址分配。请通过实际所有者升级托管插件，而不要应用历史版本的上游 DaemonSet。避免在相同端点上运行相互竞争的策略引擎。更改 CNI 链后，现有 Pod 不会自动附加到 Cilium；应在计划好的滚动部署中重新创建这些 Pod，并确认端点由 Cilium 管理。Chaining 存在文档说明的 L7 策略/IPsec 限制，因此不要假定本页后面的所有示例在此配置中都可用。

### ClusterMesh

ClusterMesh 需要唯一的集群标识、兼容的版本、可达且不重叠的 Pod 网络、经过身份验证的 API 连接，以及适当的暴露方式。LoadBalancer Service 可能会创建云资源，因此需要审慎设计网络/安全配置。创建两个公共端点并不足以安全地连接集群。请遵循维护中的 [ClusterMesh 指南](13-clustermesh-install-upgrade.md)，以及适用于所选拓扑的高级章节。

## 安装与配置

### 客户端工具

请为工作站的操作系统/架构使用相应的官方 Cilium CLI 0.20.1 和 Hubble CLI 1.20.2 资源，并在解压前验证随附的校验和。Linux ARM64 和 AMD64 资源不同；macOS 使用对应的 Darwin 资源。CLI 版本与 Cilium agent/chart 版本相互独立。请参阅[经过核实的 CLI 安装指南](../../service-mesh/cilium-service-mesh/README.md)。

```bash
cilium version --client
hubble version
```

### 非云集群 Cluster-Pool 示例

以下**替代方案**适用于已准备好的普通 Linux 集群，且 kube-proxy 和 DNS 已经正常工作。请确保示例 Pod 网段 `10.244.0.0/16` 与集群兼容，且不与 Service、节点、VPC 或互联网络网段重叠。ENI 模式不要使用此池配置。

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

保存为 `cilium-values.yaml`，渲染锁定版本的 chart，然后仅在已准备好的集群上安装：

```bash
helm template cilium cilium/cilium --version 1.20.3 \
  --namespace kube-system -f cilium-values.yaml > cilium-rendered.yaml
helm install cilium cilium/cilium --version 1.20.3 \
  --namespace kube-system -f cilium-values.yaml
cilium status --wait
```

对于现有版本，请使用其升级/GitOps 流程，保留由该流程管理的 values，并遵循特定版本的升级步骤。重复运行 `cilium install` 的示例并非通用的单项设置变更方法。

| 选项 | 当前配置与先决条件 |
| --- | --- |
| VXLAN/Geneve | `routingMode: tunnel` 加上 `tunnelProtocol`；允许所选封装流量，并为路径设置 MTU |
| 原生路由 | `routingMode: native`；底层网络必须能够路由 Pod 地址。`autoDirectNodeRoutes` 需要合适的直接连接，并不适用于任意多子网路由 |
| kube-proxy 替换 | `kubeProxyReplacement: true` 或 `false`，而非旧版 `strict`；替换模式需要可达的 `k8sServiceHost`/`k8sServicePort` 以及文档说明的引导方案 |
| WireGuard | 检查内核/平台和对等端路径后，启用受支持的加密模式；它不会自动加密所有可能的流量路径 |
| IPsec | 需要文档说明的密钥 Secret、密钥分发/轮换和兼容模式；仅启用 Helm 标志并不完整 |
| XDP/DSR/BBR | 取决于设备/内核/拓扑的独立选项，并非通用安装预设 |

## 网络策略

Kubernetes `networking.k8s.io/v1` NetworkPolicy 和 Cilium `cilium.io/v2` 策略是不同的 API。多个允许策略可以组合生效。这些示例使用**分别准备的测试命名空间**，以避免 L4 允许规则悄然绕过 L7 限制。在得出结论之前，请检查选择实际端点的所有策略。

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

在独立的 `cilium-l7-demo` 中，此策略选择后端 Pod，并将前端 Pod（位于该命名空间）的明文 HTTP TCP 8080 流量限制为指定的方法/路径。所选 CNI 模式必须支持 L7 代理；如果没有受支持的终止配置，则不会自动检查加密的 HTTP 流量。

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

不要为相同的对等端/端口添加匹配的、不受限制的 L4 允许规则：Cilium 文档指出，此类允许规则会消除较严格 L7 限制的效果。L7 拒绝可能返回 HTTP 403，而不是丢弃数据包。请使用真实端点身份测试允许的 GET 请求以及被拒绝的方法/路径。

### DNS/FQDN 示例

在 `cilium-dns-demo` 中，此策略允许向普通 CoreDNS Pod 发送 DNS 查询，并允许连接到为 `api.example.com` 学习到的地址的 TCP 443 流量。该域名只是示例；请替换为已批准的目标。此处省略范围过宽的 `*.amazonaws.com` 通配符，因为它不能用作账户/资源边界。

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

DNS 通配符允许向所选解析器发送查询，而不是连接到所有返回的地址。它仍可能承载任意 DNS 名称；如有需要，请考虑 DNS 搜索后缀并限制查询名称。使用 NodeLocal DNS 或其他解析器时，需要正确选择目标。FQDN 策略是基于 DNS 解析结果的 IP 授权，并不是 TLS 主机名验证或 HTTP URL 授权；共享 IP 以及应用 TLS/身份验证仍然重要。

## 使用 Hubble 进行可观测性

上面的 cluster-pool values 启用了 Relay/UI 和组件指标。对于现有安装，请通过其配置所有者应用预期的 Hubble values；`cilium hubble enable --ui` 是受支持的便捷命令，但 `cilium hubble enable --metrics=...` 不是受支持的 0.20.1 CLI 标志。请改为在 Helm values 中配置 `hubble.metrics.enabled`。不要同时启用旧版 `http` 和 `httpV2` 处理程序。

在一个终端中保持 Relay 端口转发运行：

```bash
cilium hubble port-forward --port-forward 4245
```

在另一个已安装 Hubble CLI 的终端中：

```bash
hubble observe --server 127.0.0.1:4245 --namespace cilium-l7-demo
hubble observe --server 127.0.0.1:4245 --protocol http
hubble observe --server 127.0.0.1:4245 --from-label k8s:app=frontend --to-label k8s:app=backend
hubble observe --server 127.0.0.1:4245 --verdict DROPPED
hubble observe --server 127.0.0.1:4245 --http-status 403
```

此本地示例假定 Relay server 使用默认配置；启用了 TLS 的 Relay 需要相应的客户端信任/身份验证配置。只有流量经过已配置的 L7 代理时才会产生 HTTP 事件。`DROPPED` 是数据平面判定结果，并不代表所有应用请求失败。请使用 `cilium hubble ui` 进行 UI 端口转发，并单独配置 Prometheus 目标发现以收集指标。Hubble 流数据本身并不等同于分布式应用追踪。

## 测试与运维

连通性/性能命令会创建测试工作负载，且可能更改策略或产生大量流量。请在经过审查的测试命名空间/环境和权限下使用；本次审查并未在集群上执行这些命令。

```bash
cilium connectivity test --help
cilium connectivity perf --help
```

性能子命令是 `cilium connectivity perf`；`connectivity test --test=performance` 只是提供测试名称筛选条件，并非性能测试运行器。比较吞吐量/延迟之前，请记录软件版本、拓扑、流量和原始结果。

检查时，请区分管理 CLI 与 **agent 端的 `cilium-dbg`**：

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

`cilium endpoint list`、`cilium bpf maps list` 和 `cilium metrics list` 并不是管理 CLI 中的等效命令。`cilium sysdump` 可以收集诊断材料；请保护好由此生成的基础设施/日志数据。Agent Ready 或抓取成功都不能替代应用测试和负向策略测试。

### 运维优先事项

- 在启用 map 预分配、XDP、DSR、BBR 或固定设备模式之前进行测量。这些设置会消耗资源或改变数据包路径，需要针对特定功能进行检查。
- 在选定范围内引入默认拒绝策略，并明确允许 DNS、API、身份和应用依赖项。除了已建立的连接，还应检查新建 Pod 和升级期间的行为。
- 将加密、证书/密钥轮换、策略执行和可观测性作为彼此独立的验收检查。保留可用的管理/恢复路径。
- 审查当前平台矩阵和受支持的升级路径。历史版本公告不能证明当前部署兼容性。

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
- 深入解析 IPAM 模式（Cluster Scope、Kubernetes Host Scope、Multi-Pool）
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
- 未来路线图与发展方向

**[eBPF 数据平面内部机制](08-ebpf-datapath-internals.md)**
- 程序集合、挂载点和尾调用
- BPF 映射目录、容量规划和编译/加载流程
- 策略执行路径与 Hubble 事件管线

**[覆盖网络与原生路由](09-overlay-native-routing.md)**
- VXLAN/Geneve、VNI 中的身份、MTU 和数据包路径
- 原生路由、伪装、主机路由、DSR 和 netkit
- EKS 决策表：覆盖网络与 ENI 与 VPC CNI chaining

**[深入解析 IPAM](10-ipam-deep-dive.md)**
- 各种 IPAM 模式、容量计算和决策矩阵
- Multi-pool、`CiliumPodIPPool`、ENI、LB IPAM、Node IPAM
- 资源耗尽故障排查与 1.21 API 变更

**[BGP、负载均衡器 IP 和出口流量](11-bgp-lb-egress-edge.md)**
- BGP Control Plane v2 CRD、通告与检查
- L2 通告、Egress Gateway、Local Redirect Policy
- Gateway API 要求与仅限内部访问的 EKS 暴露方式

**[mTLS、加密与身份](12-mtls-encryption-identity.md)**
- 身份模型、策略语义和审计模式
- Mutual Authentication 时间线、ztunnel 工作负载 mTLS
- WireGuard、IPsec、Hubble 和证书管理

**[版本、安装/升级与 Cluster Mesh](13-clustermesh-install-upgrade.md)**
- 1.17-1.21 功能矩阵、升级与回滚规则
- EKS 安装细节、Cluster Mesh 和 MCS-API

## 其他资源

- [深入了解网络概念](networking-concepts.md)
- [术语表与缩略语](glossary.md)

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
- [Calico 对比术语](../calico/glossary.md)

## 测验

要检验你对本节内容的掌握情况，请尝试 [Cilium 深入解析测验](../../quizzes/networking/cilium/01-introduction-quiz.md)。
