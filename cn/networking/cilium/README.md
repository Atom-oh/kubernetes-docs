# Cilium 深度解析：云原生网络的未来

## 概览和已审查的基线

本节涵盖 Cilium 网络、策略和可观测性。示例已根据 **Cilium/Helm chart 1.20.2**、Cilium CLI **0.20.1** 和 Hubble CLI **1.20.2** 审查。Cilium 1.20 Kubernetes 兼容性页面将 **1.33–1.36** 列为已测试版本；上游 1.37 版本不会自动扩展该矩阵。支持的主机为搭载内核 **5.10+** 的 AMD64/AArch64 Linux，或文档中对应的发行版内核，例如 RHEL 8.10 回移植的 4.18 内核。各个功能还有额外要求。

> **最后更新**: October 15, 2026

### 历史版本说明

以下日期为 UTC 中的 GitHub 发布时间，描述的是这些版本，而非当前安装固定版本。功能回移植因版本线而异。

| 日期 | 版本 | 已验证的亮点 |
| --- | --- | --- |
| July 14, 2026 | [1.20.0-rc.0](https://github.com/cilium/cilium/releases/tag/v1.20.0-rc.0) | 第一个 1.20 候选版本 |
| July 16, 2026 | [1.19.6](https://github.com/cilium/cilium/releases/tag/v1.19.6), [1.18.12](https://github.com/cilium/cilium/releases/tag/v1.18.12), [1.17.18](https://github.com/cilium/cilium/releases/tag/v1.17.18) | 1.19.6/1.18.12 列出了 Gateway 访问日志配置；此处引用的重启策略和 ClusterMesh 亲和性修复列于 1.19.6，而非全部三个版本 |
| July 21, 2026 | [1.20.0-rc.1](https://github.com/cilium/cilium/releases/tag/v1.20.0-rc.1) | 第二个 1.20 候选版本 |
| July 29, 2026 | [1.20.0](https://github.com/cilium/cilium/releases/tag/v1.20.0) | GA 版本；以下列出部分变更 |
| August 3, 2026 | [1.21.0-pre.0](https://github.com/cilium/cilium/releases/tag/v1.21.0-pre.0) | 下一个周期的预发布版本，不是本指南的部署基线 |
| August 18, 2026 | [1.20.1](https://github.com/cilium/cilium/releases/tag/v1.20.1) | ClusterMesh 文档和错误修复，包括重启/CIDR 策略处理 |
| August 18, 2026 | [1.19.7](https://github.com/cilium/cilium/releases/tag/v1.19.7) | 包含 ENI 接口时序、Service/LB 及其他修复 |
| August 18, 2026 | [1.18.13](https://github.com/cilium/cilium/releases/tag/v1.18.13) | VRRP/IGMP 主机防火墙支持及相关修复 |
| September 9, 2026 | [1.21.0-pre.2](https://github.com/cilium/cilium/releases/tag/v1.21.0-pre.2) | 预发布版本；其变更日志涵盖 pre.0 到 pre.2，因为 **1.21.0-pre.1 从未发布** |
| September 16, 2026 | [1.20.2](https://github.com/cilium/cilium/releases/tag/v1.20.2) | 本指南当前稳定基线；ENI 前缀委派和辅助 VPC CIDR 修复、ClusterMesh 修复，以及升级在 v1.15 或更早版本创建的集群时的修复（`CiliumNodeConfig v2alpha1` CRD 版本） |
| September 16, 2026 | [1.19.8](https://github.com/cilium/cilium/releases/tag/v1.19.8), [1.18.14](https://github.com/cilium/cilium/releases/tag/v1.18.14) | 较旧受支持版本线的补丁版本 |
| October 2, 2026 | [1.21.0-pre.3](https://github.com/cilium/cilium/releases/tag/v1.21.0-pre.3) | 最新 1.21 预发布版本；**1.21 仅为预发布版（尚无 GA）**，本指南中标为 1.21 的项目可能会变动 |

1.20.0 公告报告了 **2,660+ 个新提交**，由 **1,100+ 名贡献者组成的社区** 支持。后者是社区规模，并非此版本作者数量。亮点包括：

- Gateway API **1.6.1**、TCPRoute/UDPRoute、BackendTLSPolicy、ListenerSets、ExternalAuth 和 CORS 支持，具体取决于各功能的配置和 API 成熟度。
- 数据路径插件和可选择启用的 `bpf.datapathMode=auto`；公告中的默认值仍为 veth。双栈集群可以配置 IPv6 egress gateway 地址。
- **Beta** IPv6 ENI IPAM，以及无需重建集群即可从 cluster-pool 迁移至 multi-pool。原地迁移不保证不会中断。
- 流量分发提示、加权 Maglev 后端和稳定的 MCS 集成；Kubernetes ClusterNetworkPolicy 支持以及基于 ztunnel 的工作负载身份 **beta** 功能。
- 据报告，`cilium-cni` 二进制文件从约 **77 MB 缩减到 16 MB**。ADS/Delta xDS 改进见于 1.20 公告；不要将其归因于 1.18.13 补丁说明。这些是上游版本声明，并非在此次审查中重复进行的测量结果。

请查阅 [1.20 升级说明](https://docs.cilium.io/en/v1.20/operations/upgrade/#upgrade-notes)，了解 Mutual Authentication（**在 1.20 中已弃用**，在 1.21 预发布版中移除）、被移除/替换的 Envoy Go 扩展、Kafka 感知策略、旧版 CiliumNodeConfig API、libnetwork 集成和自定义 CNI 配置变更。

### NetworkPolicy 安全公告

[GHSA-fm8w-2m5w-9j7r / CVE-2026-56743](https://github.com/cilium/cilium/security/advisories/GHSA-fm8w-2m5w-9j7r) 的项目公告发布日期为 **July 6, 2026**。项目 API 和 GitHub 全局公告 API 提供不同日期：后者记录为 September 3。请将项目披露日期用于此版本时间线；全局记录日期并非较晚的修复版本。它在公告所述的自定义集群名称条件下影响 **1.19.0–1.19.4**：仅包含 `ipBlock` 的标准 Kubernetes NetworkPolicy 对等规则可能会意外允许来自所选 Pod 命名空间中工作负载的 ingress 流量。**1.19.5** 修复了此问题；部署时请使用适当的当前已修补版本。该公告称 CiliumNetworkPolicy/ClusterwideNetworkPolicy 以及低于 1.19.0 的版本不受此特定错误影响。

## 简介

Cilium 为受支持的 Linux Kubernetes 环境提供网络、安全和可观测性。路由、IPAM、加密和 Service 处理是独立的选择；仅选择 eBPF 并不会建立每项功能或性能保证。旧版 Docker libnetwork 集成已在 1.20 中移除，因此不应在此将 Docker/Mesos 列为可互换的当前安装目标。

### eBPF 和核心能力

内核会在加载 eBPF 程序前对其进行验证，并可在受支持的挂载点将其 JIT 编译后执行。这能在不使用自定义内核模块的情况下实现数据包处理和可观测性；验证器并不证明应用程序或策略正确。实际吞吐量、延迟和内存取决于程序、平台和工作负载。

Cilium 提供 L3/L4 策略、通过 Envoy/DNS 代理集成的 L7 策略、可选 WireGuard/IPsec、Service 负载均衡、Hubble 流可见性、ClusterMesh 和 BGP 通告。XDP 加速是可选功能，取决于设备/配置。L7 功能可能使用每节点 Envoy；通过 ztunnel 提供的工作负载身份具有单独的 beta 配置。仅安装 agent 不会启用所有 mesh、加密或多集群行为。

### 与其他网络项目的比较

| 项目 | 连通性 / IPAM | 策略和相关能力 |
| --- | --- | --- |
| Cilium | 原生或 overlay 路由；包括云 ENI 在内的 IPAM 模式 | eBPF 数据平面、Cilium/Kubernetes 策略、L7 集成、Hubble 和可选加密 |
| Calico | 使用 Calico 或外部 IPAM 的原生/IPIP/VXLAN 配置 | Linux Iptables/Nftables/BPF、受支持的 Windows HNS；OSS WireGuard、分阶段策略和独立 L7 集成 |
| Flannel | 通过 VXLAN/host-gw/WireGuard 等选定后端实现 Pod 连通性 | 路由守护进程不执行 NetworkPolicy；其 chart 可通过 `netpol.enabled` 部署 SIGs network-policy controller，或与其他策略实现配对 |
| AWS VPC CNI | VPC ENI 地址分配/网络 | 受支持 EC2 Linux 节点上的原生网络策略以及独立的 SG-for-Pods 功能；EKS Auto Mode 是不同的托管实现 |

路由模式与数据包处理实现不是同一类别。Calico 不限于 iptables/IPVS，Flannel 可以使用加密后端，AWS 策略也不等同于安全组。Service mesh 是可选层，跨集群 VPC 连通性也不限于 Transit Gateway。请使用经过测量的工作负载和明确的支持矩阵，而非通用性能排名。

## 架构

**Kubernetes API server** 存储 Kubernetes/Cilium 资源。Cilium agent 监视相关状态并编程每个节点的数据平面；Cilium Operator 负责所选 IPAM 以及身份/控制器等集群级职责。在此基本架构中，没有单独的强制性集群范围“Cilium API Server” Deployment。agent 有本地 API，可选的 ClusterMesh API server 则服务于不同用途。

| 组件 | 角色 |
| --- | --- |
| Cilium Agent | 节点本地 endpoint、策略、路由/Service 状态和 eBPF 管理 |
| Cilium Operator | 集群级协调以及依模式而定的分配/控制器工作 |
| Envoy | 为已启用的 L7 策略、ingress/Gateway 及相关功能提供的用户空间代理 |
| Hubble server | 与 agent 集成的节点本地流 API |
| Hubble Relay / UI | 聚合流数据流 / 显示 Service map 和流 |
| Prometheus metrics endpoints | 独立的统计信息收集；Relay/UI 不是 metrics 抓取管道 |
| cilium / cilium-dbg / hubble | 分别为集群管理 CLI / agent 诊断 / 流客户端 |

### 网络和数据包路径

原生路由需要可达的 underlay；隧道使用 VXLAN 或 Geneve。AWS ENI 和 Azure IPAM 是具有自身平台要求的分配/集成选择。Cilium 的 BGP Control Plane 向路由器通告可达性，**不编程数据平面，也不提供集群内部路由**。

不存在通用的 XDP→TC→Pod 序列。Socket 负载均衡可在数据包出现之前起作用，TC/netkit 挂载点取决于数据平面，可选 XDP 加速选定流量，L7 流量可能经过 Envoy。返回流量还取决于 NAT、conntrack 和 DSR 选择。请查看适用于所选配置的网络和 eBPF 章节。

## 与 Amazon EKS 集成

在安装任何组件前选择实际的网络和计算配置。示例 add-on 名称/版本 `cilium` / `v1.17.0-eksbuild.1` 不是经过验证的 AWS 发行版，且此处不是安装命令。若考虑使用打包的供应商 add-on，请检查该 Region 的实际 add-on 目录、发布者、许可证和受支持的计算类型。

| EKS 配置 | 要验证的内容 |
| --- | --- |
| 普通 EC2 节点，Cilium ENI 替换 VPC CNI | 上游/合作伙伴管理的 CNI；AWS 受支持的 EC2 CNI 是 VPC CNI。规划 CNI 所有权、IAM、寻址、路由、引导和节点迁移 |
| 普通 EC2 节点，AWS VPC CNI chaining | VPC CNI 拥有接口/IPAM；Cilium 随后附加其数据平面。现有 Pod 需要重新创建，L7/IPsec 有文档说明的限制 |
| Hybrid Nodes | 遵循 AWS 的专用 CNI 指南和 AWS 维护的 Cilium 构建矩阵；上游 1.20.2 不会自动成为受支持的 AWS 构建 |
| Auto Mode | 不支持替代 CNI/策略插件；使用托管的 NodeClass/网络功能 |
| Fargate | 不支持替代 CNI/DaemonSet 安装 |
| Windows | Cilium agent 要求 Linux；请勿将此方案应用到 Windows worker |

AWS 的通用替代 CNI 页面和专用 Hybrid 指南在 Calico 支持措辞上不同；一个迁移仓库的示例并不能证明支持终止。对于 Hybrid Nodes，请确认确切发行版、功能集和支持负责人。对于 Auto Mode，节点本地 CoreDNS/system 网络也不同于本指南中的普通 EC2 设置；混合的非 Auto 节点仍需要传统 DNS Deployment。

### 使用 Cilium ENI 准备好的 EC2 集群

这些是**已准备 IPv4 EC2 集群的 Cilium Helm values**，而不是完整的集群创建或原地迁移方案。使用前请：

1. 选择受支持的 EKS/Kubernetes 版本和 Linux AMI，并确定一个 CNI 所有者。不要为图省事而从现有工作负载集群删除 `aws-node`。
2. 准备节点 taint/调度，使工作负载等待 Cilium 管理节点。上游 EKS 指南使用 `node.cilium.io/agent-not-ready=true:NoExecute`；请在实际节点生命周期中评估驱逐和引导影响。
3. 准备子网容量、ENI 配额/安全组、节点 metadata 访问权限和 Operator 所需的 EC2 权限。以下 role ARN 是具有正确信任关系的 **cilium-operator ServiceAccount** role 的占位符，不是 values 文件创建的 role。
4. 为此 `kubeProxyReplacement: false` 示例保留可工作的 kube-proxy 和 DNS。对于 replacement 模式，请遵循单独的直接 API/引导 DNS 要求。根据实际实例/IPAM 容量选择 max-Pods，而非通用的 110。

保存为 `cilium-eni-values.yaml`，并将 role/interface 选择替换为已审查的值：

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
helm template cilium cilium/cilium --version 1.20.2 \
  --namespace kube-system -f cilium-eni-values.yaml > cilium-eni-rendered.yaml

# After preparing the cluster and reviewing the rendered configuration:
helm install cilium cilium/cilium --version 1.20.2 \
  --namespace kube-system -f cilium-eni-values.yaml
```

通过安装所有者管理这些设置。仅包含少量键的替换 `cilium-config` 可能移除其他必需设置；旧的 `tunnel=disabled` 值已由 `routingMode: native` 替代。ENI 分配/权限和 SNAT 行为仍需要运行时验证；渲染成功并不证明 EC2 网络可用。

**IPv6 鉴定：**1.20.2 ENI IPAM 参考将 IPv6 描述为 beta，而其 EKS prerequisites 页面仍声明仅支持 IPv4 ENI 集成。本指南保留 IPv4 示例，并记录该文档不一致性，而不是将任一声明视为生产 EKS IPv6 兼容性的证明。在单独设计 IPv6 之前，请审查当前 ENI/双栈子网要求。

### VPC CNI Chaining 替代方案

上游 chaining 指南要求 VPC CNI 1.11.2+，并记录了此配置：

```yaml
cni:
  chainingMode: aws-cni
  exclusive: false
enableIPv4Masquerade: false
routingMode: native
kubeProxyReplacement: false
```

将它作为**不同的配置**使用，而不是叠加在 ENI 替换 values 上。VPC CNI 仍是分配器。通过其所有者升级实际的托管 add-on，而非应用历史上游 DaemonSet。避免在相同 endpoint 上使用相互竞争的策略引擎。当 CNI chain 变更时，现有 Pod 不会追溯性附加到 Cilium；请在计划的 rollout 中重新创建它们并验证 endpoint 管理。Chaining 有已记录的 L7 策略/IPsec 限制，因此不要假定本页后续所有示例均适用于该配置。

### ClusterMesh

ClusterMesh 需要唯一的集群身份、兼容版本、可达且不重叠的 Pod 网络、经过身份验证的 API 连通性和适当的暴露模型。LoadBalancer Service 可以创建云资源，并且需要审慎的网络/安全设计。创建两个公共 endpoint 并不足以安全连接集群。请遵循针对所选拓扑维护的 [ClusterMesh 指南](13-clustermesh-install-upgrade.md) 和高级章节。

## 安装和配置

### 客户端工具

为工作站 OS/架构使用适当的官方 Cilium CLI 0.20.1 和 Hubble CLI 1.20.2 资源，并在解压前验证提供的校验和。Linux ARM64 和 AMD64 不同；macOS 使用相应的 Darwin 资源。CLI 版本独立于 Cilium agent/chart 版本。请参阅[已验证的 CLI 安装指南](../../service-mesh/cilium-service-mesh/README.md)。

```bash
cilium version --client
hubble version
```

### 非云 Cluster-Pool 示例

以下**替代方案**适用于 kube-proxy 和 DNS 已可用的已准备普通 Linux 集群。确保示例 `10.244.0.0/16` Pod 范围与集群兼容，且不与 Service、节点、VPC 或已连接网络范围重叠。不要将此 pool 配置用于 ENI 模式。

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

保存为 `cilium-values.yaml`，渲染固定版本的 chart，然后仅在已准备集群上安装：

```bash
helm template cilium cilium/cilium --version 1.20.2 \
  --namespace kube-system -f cilium-values.yaml > cilium-rendered.yaml
helm install cilium cilium/cilium --version 1.20.2 \
  --namespace kube-system -f cilium-values.yaml
cilium status --wait
```

对于现有 release，请使用其升级/GitOps 流程，保留受其所有的 values，并遵循特定版本的升级过程。重复使用 `cilium install` 示例并不是更改单个设置的通用方法。

| 选择 | 当前配置和前提条件 |
| --- | --- |
| VXLAN/Geneve | `routingMode: tunnel` 加 `tunnelProtocol`；允许所选封装，并为路径设置 MTU |
| 原生路由 | `routingMode: native`；underlay 必须能路由 Pod 地址。`autoDirectNodeRoutes` 需要合适的直接连通性，而非任意多子网路由 |
| kube-proxy replacement | `kubeProxyReplacement: true` 或 `false`，而非旧版 `strict`；replacement 要求可达的 `k8sServiceHost`/`k8sServicePort` 和文档规定的引导方案 |
| WireGuard | 在检查内核/平台和 peer 路径后启用受支持的加密模式；它不会自动加密所有可能的流量路径 |
| IPsec | 要求文档规定的 key Secret、key 分发/轮换和兼容模式；仅 Helm 启用标志并不完整 |
| XDP/DSR/BBR | 独立的设备/内核/拓扑相关选择，而非通用安装预设 |

## 网络策略

Kubernetes `networking.k8s.io/v1` NetworkPolicy 和 Cilium `cilium.io/v2` 策略是不同的 API。多个 allow 策略可组合。这些示例使用**独立的已准备测试命名空间**，以使 L4 allow 不会悄然绕过 L7 限制。在得出结论前，请检查选择实际 endpoint 的所有策略。

### L4 示例

在 `cilium-l4-demo` 中，此策略选择 backend Pod，并允许来自同一命名空间 frontend Pod 的 TCP 8080 ingress：

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

在独立的 `cilium-l7-demo` 中，此策略选择 backend Pod，并将该命名空间 frontend Pod 对 TCP 8080 明文 HTTP 的访问限制为所述 method/path。所选 CNI 模式中必须提供 L7 proxy 支持；若无受支持的终止配置，不会自动检查加密 HTTP。

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

不要为相同 peer/port 添加匹配的无限制 L4 allow：Cilium 文档说明，此类 allow 会移除更严格 L7 限制的效果。L7 deny 可能返回 HTTP 403，而非丢弃数据包。请使用真实 endpoint identity 测试允许的 GET 请求以及被拒绝的 method/path。

### DNS/FQDN 示例

在 `cilium-dns-demo` 中，此策略允许对普通 CoreDNS Pod 的 DNS 查询，以及到为 `api.example.com` 学习到的地址的 TCP 443。该域名仅为示例；请将其替换为已批准的目标。广泛的 `*.amazonaws.com` wildcard 并非账户/资源边界，因此已省略。

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

DNS wildcard 允许向所选 resolver 查询，而非连接到每个返回的地址。它仍可能承载任意 DNS 名称；在需要时限制查询名称，并考虑 DNS 搜索后缀。NodeLocal DNS 或其他 resolver 需要正确的目标选择。FQDN 策略是基于 DNS 派生的 IP 授权，而非 TLS hostname 验证或 HTTP URL 授权；共享 IP 和应用 TLS/身份验证仍然重要。

## 使用 Hubble 进行可观测性

上述 cluster-pool values 启用 Relay/UI 和组件 metrics。对于现有安装，请通过其配置所有者应用预期的 Hubble values；`cilium hubble enable --ui` 是受支持的便捷命令，但 `cilium hubble enable --metrics=...` 不是受支持的 0.20.1 CLI 标志。请改为在 Helm values 中配置 `hubble.metrics.enabled`。不要同时启用旧版 `http` 和 `httpV2` handler。

在一个终端中保持 Relay port-forward 运行：

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

此本地示例假定默认 Relay server 配置；启用 TLS 的 Relay 需要相应的客户端信任/身份验证。HTTP event 要求流量经过已配置的 L7 proxy。`DROPPED` 是数据平面 verdict，而非每个失败的应用请求。使用 `cilium hubble ui` 进行 UI port-forward，并单独配置 Prometheus target discovery 用于 metrics。Hubble 流式传输本身并非分布式应用追踪。

## 测试和运维

连通性/性能命令会创建测试工作负载，且可能变更策略或产生大量流量。请使用已审查的测试命名空间/环境和权限；此次审查未对集群执行它们。

```bash
cilium connectivity test --help
cilium connectivity perf --help
```

性能子命令是 `cilium connectivity perf`；`connectivity test --test=performance` 仅提供测试名称过滤器，并非性能运行器。在比较吞吐量/延迟前，请记录软件版本、拓扑、流量和原始结果。

对于检查，请区分管理 CLI 和 **agent 端的 `cilium-dbg`**：

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

`cilium endpoint list`、`cilium bpf maps list` 和 `cilium metrics list` 在管理 CLI 中并非等效命令。`cilium sysdump` 可以收集诊断材料；请保护生成的基础设施/日志数据。Ready agent 或成功 scrape 不能替代应用和负向策略测试。

### 运维优先事项

- 在启用 map preallocation、XDP、DSR、BBR 或固定设备模式前进行测量。这些会消耗资源或更改数据包路径，且需要特定功能检查。
- 在选定范围内引入 default-deny，同时显式允许 DNS、API、identity 和应用依赖项。除已建立连接外，也应检查新 Pod 和升级过渡。
- 将加密、证书/key 轮换、策略执行和可观测性作为独立验收检查。保留可用的管理/恢复路径。
- 审查当前平台矩阵和受支持的升级路径。历史版本公告并不能证明当前部署兼容性。

## 深度解析目录

**[Cilium 简介和基本概念](01-introduction.md)**
- Cilium 概览和历史
- 容器网络基础
- 理解 CNI（容器网络接口）
- Cilium 的差异化功能

**[eBPF 技术深度解析](02-ebpf.md)**
- eBPF 技术和历史简介
- eBPF 如何在内核中工作
- eBPF 程序类型和 map
- 在 Cilium 中使用 eBPF

**[网络模型和 VXLAN](03-networking.md)**
- 容器网络模型比较
- VXLAN 技术深度解析
- Cilium 的 Overlay 网络
- 性能优化技术
- 路由机制（封装与原生路由）
- 云提供商网络（AWS ENI、Google Cloud）

**[IPAM 和网络策略](04-ipam-policy.md)**
- IP 地址管理（IPAM）策略
- Kubernetes 和 Cilium IPAM 集成
- 网络策略设计和实现
- 多集群场景
- IPAM 模式深度解析（集群范围、Kubernetes 主机范围、Multi-Pool）
- 云提供商 IPAM（Azure IPAM、AWS ENI、GKE）
- 基于 CRD 的 IPAM

**[L2-L7 网络和负载均衡](05-l2-l7-networking.md)**
- 理解 OSI 模型层（L2、L3、L4、L7）
- Cilium 的特定层功能
- Service Mesh 集成
- 负载均衡架构
- Masquerading 配置和实现模式
- IPv4 分片处理

**[安全和可见性](06-security-visibility.md)**
- Cilium 的安全功能
- 网络可见性和监控
- Hubble 架构和用法
- 实时威胁检测

**[高级主题和真实案例](07-advanced-topics.md)**
- 性能调优和故障排除
- 大规模部署策略
- 真实用例研究
- 未来路线图和发展方向

**[eBPF 数据平面内部机制](08-ebpf-datapath-internals.md)**
- 程序集、挂载点和尾调用
- BPF map 目录、大小调整和编译/加载流程
- 策略执行路径和 Hubble event pipeline

**[Overlay 和原生路由](09-overlay-native-routing.md)**
- VXLAN/Geneve、VNI 中的 identity、MTU 和数据包流程
- 原生路由、masquerading、主机路由、DSR 和 netkit
- EKS 决策表：overlay 与 ENI 与 VPC CNI chaining

**[IPAM 深度解析](10-ipam-deep-dive.md)**
- 每种 IPAM 模式、容量计算和决策矩阵
- Multi-pool、`CiliumPodIPPool`、ENI、LB IPAM、Node IPAM
- 耗尽故障排除和 1.21 API 变更

**[BGP、Load Balancer IP 和 Egress](11-bgp-lb-egress-edge.md)**
- BGP Control Plane v2 CRD、通告和检查
- L2 公告、Egress Gateway、Local Redirect Policy
- Gateway API 要求和仅内部 EKS 暴露

**[mTLS、加密和 Identity](12-mtls-encryption-identity.md)**
- Identity 模型、策略语义和审计模式
- Mutual Authentication 时间线、ztunnel 工作负载 mTLS
- WireGuard、IPsec、Hubble 和证书管理

**[版本、安装/升级和 Cluster Mesh](13-clustermesh-install-upgrade.md)**
- 功能矩阵 1.17-1.21、升级和回滚规则
- EKS 安装细节、Cluster Mesh 和 MCS-API

## 附加资源

- [网络概念深度解析](networking-concepts.md)
- [术语表和缩写](glossary.md)

## 参考资料

- [Cilium 1.20 Kubernetes 兼容性](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/kubernetes/compatibility.rst)
- [Cilium 系统要求](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/operations/system_requirements.rst)
- [EKS 前提条件](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/installation/requirements-eks.rst)
- [Cilium ENI IPAM](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/concepts/ipam/eni.rst)
- [AWS 替代 CNI 支持](https://docs.aws.amazon.com/eks/latest/userguide/alternate-cni-plugins.html)
- [AWS Hybrid Nodes CNI](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-cni.html)
- [Cilium L7 策略语义](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/security/policy/layer7.rst)
- [Hubble 项目](https://github.com/cilium/hubble)
- [Flannel 网络和策略集成](https://github.com/flannel-io/flannel)
- [Calico 比较术语](../calico/glossary.md)

## 测验

要测试您在本节所学的内容，请尝试 [Cilium 深度解析测验](../../quizzes/networking/cilium/01-introduction-quiz.md)。
