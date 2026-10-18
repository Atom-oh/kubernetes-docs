# 第 10 部分：IPAM 深入解析

> **审阅基线**：Cilium 1.20.2（稳定版，2026-09-16）；Cilium CLI 0.20.1；Hubble CLI 1.20.2。标注为 **[1.21 预发布版]** 的内容来自 v1.21.0-pre.3，正式发布前可能变更。
> **最后更新**：2026 年 10 月 15 日

[第 4 部分](04-ipam-policy.md)介绍了 IPAM 模式及对应的 Helm 配置片段。本章将深入说明：不同地址由谁负责；从 `cilium-cni ADD` 到 endpoint 运行起来之间会发生什么；安装前如何规划地址池大小；ENI 分配器如何决定调用 EC2；以及 LB IPAM 和 Node IPAM 与 Pod IPAM 有何不同。本章与[覆盖网络和原生路由](09-overlay-native-routing.md)（地址如何路由）以及[BGP、负载均衡、出口流量与边缘](11-bgp-lb-egress-edge.md)（如何通告 LB 地址）互为补充。

## IPAM 是什么，又不是什么

Kubernetes 集群中有四类不同地址，由四种不同的所有者分配。混淆它们是最常见的“IPAM”问题来源。

| 地址 | 所有者 | Cilium 的职责 |
|---|---|---|
| Pod（endpoint）IP | Cilium IPAM（本章的各模式小节） | 分配、跟踪并释放 |
| Service ClusterIP | kube-apiserver（`--service-cluster-ip-range`） | 无；Cilium 只将其配置到数据路径中 |
| LoadBalancer Service IP | LB IPAM（`CiliumLoadBalancerIPPool`）或云控制器 | 仅由 operator 分配；通告是独立功能（BGP Control Plane 或 L2 Announcements） |
| 作为负载均衡器的节点地址 | Node IPAM（`loadBalancerClass: io.cilium/node`） | operator 将节点地址复制到 Service 状态中 |

`CiliumPodIPPool` 不会分配 ClusterIP，`CiliumLoadBalancerIPPool` 也不会分配 Pod IP。`CiliumCIDRGroup`（见下文 CiliumCIDRGroup）不分配任何地址：它只是供策略使用的一组具名 CIDR。

## 概览：CiliumNode 握手

几乎所有模式都由两个组件通过 `CiliumNode` 自定义资源（每个节点一个，名称与节点相同）进行交互：

```
                        +-----------------------------+
                        |        CiliumNode <node>    |
                        |  spec.ipam.podCIDRs         |  cluster-pool
                        |  spec.ipam.pools.requested  |  multi-pool / eni (agent writes)
                        |  spec.ipam.pools.allocated  |  multi-pool / eni (operator writes)
                        |  spec.ipam.pool             |  crd (external allocator writes)
                        |  status.ipam.*              |  used IPs, operator-status.error
                        |  status.eni.enis            |  eni (operator writes)
                        +--------------+--------------+
                 watch/update          |          watch/update
        +------------------------+     |     +--------------------------+
        |  cilium-agent (node)   |<----+---->|  cilium-operator         |
        |  local pod-IP allocator|           |  node CIDRs, EC2/Azure   |
        |  CNI /ipam REST        |           |  API calls, pool alloc   |
        +------------------------+           +--------------------------+
```

agent 从节点当前持有的地址范围中分配单个 Pod IP。operator（或 Kubernetes，或外部系统，取决于模式）决定节点持有哪些地址。在 `cluster-pool`、`multi-pool` 和 `eni` 模式下，agent 会创建自己的 `CiliumNode`（agent 选项 `auto-create-cilium-node-resource`，默认值为 true）。operator 会忽略带有 `ipam.cilium.io/ignore: "true"` 注解的 `CiliumNode`，这是交由其他系统管理的节点所使用的逃生机制。

### 各模式下的 agent 分配器连接方式（1.20.2）

| `ipam.mode` | 节点容量来源 | agent 侧分配器 |
|---|---|---|
| `kubernetes` | `Node.spec.podCIDRs`（或注解） | 在节点 CIDR 上运行的 host-scope 分配器 |
| `cluster-pool`（默认） | operator，通过 `CiliumNode.spec.ipam.podCIDRs` | 在节点 CIDR 上运行的 host-scope 分配器 |
| `multi-pool` | operator，通过 `spec.ipam.pools.allocated` | multi-pool manager |
| `eni` | operator（EC2 API），由 `status.eni.enis` 转换为 `spec.ipam.pools.allocated` | **ENI multi-pool 分配器（1.20 新增）** |
| `crd`、`azure`、`alibabacloud` | `CiliumNode.spec.ipam.pool` | CRD 分配器 |
| `delegated-plugin` | 另一个 CNI IPAM 插件 | 空操作分配器 |

需要注意的 Helm 交互：`eni.enabled=true` 会强制使用 `ipam: eni`，无论 `ipam.mode` 的值为何；若设置了 `ipam.mode=eni` 却未启用 `eni.enabled`，chart 校验会失败。没有 `gke` 这个配置值：自管 GKE 使用 `kubernetes` 模式。

### 节点本地地址

Cilium 会从每个节点的地址范围中为自身保留地址：`cilium_host` 路由器 IP、健康检查 endpoint IP，以及（启用 Ingress 时）Ingress IP。在 `cilium-dbg status --all-addresses` 中，它们分别显示为 `(router)`、`(health)` 和 `(ingress)`。host-scope 分配器还会排除节点 CIDR 的第一个（网络）和最后一个（广播）地址。容量计算（见“容量规划计算”）必须扣除这些地址。

## Pod IP 生命周期

除 `delegated-plugin` 外，各模式下从 kubelet 到运行中 endpoint 的流程如下：

```
kubelet -> CRI -> cilium-cni ADD
                     |
                     | 1. remove stale host-side interface name, if any
                     | 2. POST /ipam   (unix socket to cilium-agent)
                     |       owner = <namespace>/<pod>, expiration = true
                     v
                 cilium-agent: IpamPostIpamHandler
                     | 3. empty pool?  -> pick pool (annotations/selectors, multi-pool)
                     | 4. AllocateNextWithExpiration
                     |       -> response: IPv4/IPv6, pool, cidrs, gateway,
                     |          master-mac, interface-number, skip-masquerade,
                     |          expiration-uuid, host-addressing (router IP)
                     |       -> start 10 minute expiration timer
                     v
                 cilium-cni: create veth (or netkit), set IPs/routes in the pod netns
                     | 5. PUT /endpoint/{id}
                     v
                 cilium-agent: build endpoint, identity, datapath
                     | 6. endpoint creation stops the expiration timer
                     v
                 pod Running

 failure at any point after step 4 -> deferred DELETE /ipam/{ip}?pool=<pool>
 CNI DEL -> endpoint delete -> agent releases the IP (metric ipam_events_total{action="release"})
```

以下关键机制均已在 1.20.2 源码中核实：

- **REST 调用**：agent API（`api/v1/openapi.yaml`）提供 `POST /ipam`、`POST /ipam/{ip}` 和 `DELETE /ipam/{ip}`。CNI 插件调用 `IPAMAllocate("", podName, "", true)`；最后一个参数是过期标记。
- **过期计时器**：设置过期时间分配的 IP 会在 `defaults.IPAMExpiration`（10 分钟）后自动释放，除非 endpoint 创建过程停止了计时器。这样可以避免 CNI 插件在分配地址后、创建 endpoint 前崩溃，导致该地址一直泄漏到 agent 重启。
- **恢复**：agent 重启时会重新认领运行中 endpoint 的 IP（在 `cilium-dbg status --all-addresses` 中显示为 `[restored]`）。选项 `--bypass-ip-availability-upon-restore` 仅用于 ENI/Azure 升级场景。
- **ENI 类模式**（`eni`、`azure`、`alibabacloud`）：响应还会携带 ENI MAC、网关和 CIDR。插件根据 MAC 设置父接口索引（仅 ENI），agent 则在主机上为每个 endpoint 安装路由规则。因此这些模式会强制使用 endpoint 路由。
- **`delegated-plugin`**：CNI 插件本身会针对配置的 IPAM 二进制运行 `DelegateAdd`（例如 AKS 上的 Azure `azure-ipam`），并将 endpoint 标记为 `ExternalIpam`，因此 agent 不会释放该 IP；插件会在 DEL 时调用 `DelegateDel`。在此模式下，Cilium 不会核算 Pod IP。

检查方式：

```bash
# All addresses the agent knows, with owners (ns/pod); multi-pool shows pool/ip
kubectl -n kube-system exec ds/cilium -c cilium-agent -- cilium-dbg status --all-addresses

# Allocation summary line, for example "IPAM: IPv4: N/M allocated from <cidr>"
kubectl -n kube-system exec ds/cilium -c cilium-agent -- cilium-dbg status | grep -i ipam
```

如果 Pod 卡在 `ContainerCreating`，且 CNI 报错 `unable to allocate IP via local cilium agent`，表示第 2–4 步失败；“故障排查”一节会按模式对应到根因。

## 模式目录与决策矩阵

### 功能对比

根据上游 1.20.2 IPAM 概念页面改编。

| 功能 | Kubernetes host scope | 集群范围（默认） | Multi-pool | CRD 支持 | AWS ENI | Azure IPAM | GKE（通过 host scope） |
|---|---|---|---|---|---|---|---|
| 隧道路由 | 是 | 是 | 是 | 否 | 否 | 否 | 否 |
| 直接路由 | 是 | 是 | 是 | 是 | 是 | 是 | 是 |
| CIDR 配置方 | Kubernetes | Cilium | Cilium | 外部系统 | AWS | Azure | GCP |
| 每个集群支持多个 CIDR | 否 | 是 | 是 | 不适用 | 不适用 | 不适用 | 不适用 |
| 每个节点支持多个 CIDR | 否 | 否 | 是 | 不适用 | 不适用 | 不适用 | 不适用 |
| 动态分配 CIDR/IP | 否 | 否 | 是 | 是 | 是 | 是 | 否 |

成熟度：cluster-pool、kubernetes、crd 和 eni 均为稳定版。Multi-pool 在 1.18 中曾带有“Beta”标记，1.19 起该标记移除（本章从 1.19 起将其视为稳定功能；上游没有使用“GA”一词）。ENI IPv6 在 1.20 中为 **beta**。从 cluster-pool 在线迁移到 multi-pool 是 1.20 新增的功能。

### 决策矩阵

这是综合上游文档及各平台约束给出的建议，并非上游提供的表格。

| 环境 | 推荐的 IPAM | 原因与注意事项 |
|---|---|---|
| EKS，希望 Pod IP 可在 VPC 中路由（以安全组为目标、ALB/NLB IP 目标、不做 SNAT） | `eni`，并在 Nitro 上启用前缀委派 | 需要 operator 的 IAM 权限、原生路由，并移除 `aws-node`。除非使用前缀委派，否则 Pod 密度受实例 ENI/IP 限制。IPv6 为 beta。不适用于 Fargate 或 EKS Auto Mode 节点 |
| EKS，VPC IP 紧缺或需要高密度 | 使用 VXLAN（Helm 默认值）的 `cluster-pool`，或 `multi-pool` | Pod 会 SNAT 为节点 IP；EKS 控制平面无法访问 Pod IP，因此 admission webhook 必须使用主机网络，或通过 Service 访问 |
| EKS Hybrid Nodes（本地节点） | 使用 VXLAN 的 `cluster-pool`；地址池列表 = EKS 的“远程 Pod 网络”；掩码按每节点 Pod 数量规划 | AWS 支持的配置仅限 IPv4、VXLAN、cluster-scope IPAM 和 BGP Control Plane。部署后不要更改地址池列表或掩码。`eni` 不能用于本地节点 |
| 本地部署，需求简单 | 使用隧道的 `cluster-pool` | 由 operator 管理，不依赖 kube-controller-manager 分配节点 CIDR |
| 本地部署，需要可路由的 Pod、每个站点或租户使用不同地址范围 | `multi-pool` + BGP `CiliumPodIPPool` 通告，并通过 `CiliumNodeConfig` 设置每站点默认地址池 | 需要 `kubeProxyReplacement=true` 和 `bpf.masquerade=true`；地址池 CIDR 不得重叠 |
| 控制平面已分配节点 CIDR 的集群（使用 `--allocate-node-cidrs` 的 kubeadm、GKE） | `kubernetes` | 静态配置；每节点、每个地址族一个 CIDR |
| 地址由外部系统提供 | `crd` | 仅支持单个 IP，且仅支持直接路由 |
| AKS | Azure CNI Powered by Cilium（`delegated-plugin`），或 BYOCNI 搭配任意 Cilium IPAM | 不要在 AKS 上使用上游 `azure` IPAM |
| 自管 Azure VM | `azure` | 配置资源组和身份相关 flags；在 1.21 预发布版中已重新设计 |

### 在运行中的集群更改模式

上游建议：除非有文档规定的迁移流程，否则不要更改运行中集群的 IPAM 模式；“最安全的方式是新建集群”。唯一有文档说明的在线迁移路径是 **cluster-pool 到 multi-pool**（见迁移小节）。其他所有变更（kubernetes 到 cluster-pool、任意模式迁移到 ENI、overlay 迁移到 ENI）都需要新集群或蓝绿节点组，因为 Pod IP 范围、路由以及（在 EKS 上）webhook 可达性都会改变。上游没有说明可以用 `CiliumNodeConfig` 按节点组混合 IPAM 模式，本章也不建议这样做。

## Kubernetes Host Scope 与 Cluster Scope

### Kubernetes host scope（`ipam.mode=kubernetes`）

启动时，agent 会等待节点为每个启用的地址族提供 PodCIDR。来源可以是 `Node.spec.podCIDRs` / `spec.podCIDR`，或注解 `network.cilium.io/ipv4-pod-cidr`、`network.cilium.io/ipv6-pod-cidr`（以及 `ipv4/6-cilium-host`、`ipv4/6-health-ip` 和 `ipv4/6-Ingress-ip`）。`kube-controller-manager` 必须使用 `--allocate-node-cidrs` 启动（并配置 `--cluster-cidr`、`--node-cidr-mask-size`）。

```yaml
ipam:
  mode: kubernetes
k8s:
  requireIPv4PodCIDR: true     # only effective with ipam.mode=kubernetes
  requireIPv6PodCIDR: false
```

在此模式启用 IPv4 时，agent 会自动启用 `k8s-require-ipv4-pod-cidr`，因此显式设置该项主要起文档说明作用。限制：每个节点、每个地址族只能有一个 CIDR；节点注册后即固定，不能动态扩展。自管 GKE 使用此模式，并将 `ipv4NativeRoutingCIDR` 设为集群 CIDR。

### Cluster scope / cluster-pool（默认）

节点前缀由 operator 分配。每个节点都会获得写入 `CiliumNode.spec.ipam.podCIDRs` 的 CIDR；agent 在启动时会等待所有启用的地址族都填入该字段，然后在该范围上运行相同的 host-scope 分配器。operator 重启后会重新认领既有分配；若有冲突，会报错 `node has CIDRs allocated (...) that conflict with requested CIDRs`。

Helm 配置值（1.20.2 默认值）：

```yaml
ipam:
  mode: cluster-pool
  operator:
    clusterPoolIPv4PodCIDRList: ["10.0.0.0/8"]   # default
    clusterPoolIPv4MaskSize: 24                  # default
    clusterPoolIPv6PodCIDRList: ["fd00::/104"]   # default
    clusterPoolIPv6MaskSize: 120                 # Helm default (operator flag default is 112)
```

渲染后的 ConfigMap 键包括 `cluster-pool-ipv4-cidr`（以空格连接的列表）、`cluster-pool-ipv4-mask-size`、`cluster-pool-ipv6-cidr` 和 `cluster-pool-ipv6-mask-size`。启用 IPv4 却未提供 CIDR 列表时（“cluster-pool-ipv4-cidr must be provided when using ClusterPool”），operator 会拒绝启动；若为未启用的地址族设置了列表，也会拒绝启动。

### 容量规划计算

节点 CIDR 分配器位于 `pkg/ipam/cidrset`。对于前缀长度为 `P` 的每个地址池 CIDR，以及节点掩码 `M`：

```
nodes per pool CIDR      = 2^(M - P)
addresses per node       = 2^(32 - M)          (IPv4)     2^(128 - M) (IPv6)
usable Pod IPs per node  = addresses - 2 (network, broadcast) - up to 3 (router, health, ingress)
```

源码中的限制：对于 IPv6，`M - P` 不能超过 16（`clusterSubnetMaxDiff = 16`，错误为 `ErrCIDRSetSubNetTooBig`），因为分配器使用未压缩的位图；IPv4 只要求 `M <= 32`。上游建议节点掩码最小为 `/30`，推荐 `/29` 或更大。

| 地址池 CIDR | 节点掩码 | 节点数 | 每节点地址数 | 备注 |
|---|---|---|---|---|
| `10.0.0.0/8`（默认） | `/24` | 65,536 | 256 | `2^(24-8)`；可用约 251 个 |
| `10.244.0.0/16` | `/24` | 256 | 256 | 常见的小型集群配置 |
| `10.244.0.0/16` | `/26` | 1,024 | 64 | `2^(26-16)`；可用约 59 个 |
| `10.244.0.0/16` | `/28` | 4,096 | 16 | 实验环境规划；约 11 个可用 |
| `fd00::/104`（默认） | `/120` | 65,536 | 256 | IPv6 默认值，差值恰为 16 |
| `fd00:10:244::/96` | `/112` | 65,536 | 65,536 | 允许的最大差值为 16 |

前四行按上述公式计算；“可用”数量已扣除两个保留地址和三个 Cilium 自用地址，因此只能视为上限。每节点 Pod 密度还取决于 kubelet 的 `maxPods`：掩码应按 `maxPods` 再加上滚动更新所需余量规划（新旧 Pod 会短暂并存）。

修改规则（上游规定；由行为约束，而非校验机制强制执行）：

- 不要编辑或删除 `clusterPoolIPv4PodCIDRList` 中已有的条目。扩容时追加新的 CIDR。
- 运行中的集群不能更改 `clusterPoolIPv4MaskSize`。
- 分配器错误（`allocator full`）会出现在 `CiliumNode.status.ipam.operator-status.error`。

```bash
kubectl get ciliumnodes -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.ipam.podCIDRs}{"\t"}{.status.ipam.operator-status}{"\n"}{end}'
```

地址重叠风险：默认的 `10.0.0.0/8` 与大多数企业和 VPC 网段重叠。若它与节点网络重叠，节点连接就会中断。务必显式设置地址池列表。

**`nativeRoutingCIDRFromClusterPool`**（Helm，默认 false；1.20 新增：在 1.18.14 和 1.19.8 的 `values.yaml` 中不存在，在 1.20.2 和 1.21 中存在）：从地址池推导原生路由 CIDR。仅当使用 cluster-pool 且每个启用的地址族恰好有一个 CIDR 时有效，否则模板渲染会失败。

### 双栈

```yaml
ipam:
  mode: cluster-pool
  operator:
    clusterPoolIPv4PodCIDRList: ["10.244.0.0/16"]
    clusterPoolIPv4MaskSize: 24
    clusterPoolIPv6PodCIDRList: ["fd00:10:244::/96"]
    clusterPoolIPv6MaskSize: 112       # 112 - 96 = 16, the maximum allowed
ipv4: { enabled: true }
ipv6: { enabled: true }
```

设置 `ipv6.enabled` 不会创建 IPv6 Service CIDR，也不会建立底层 IPv6 连通性。各模式的要求如下：host scope 需要提供两个 `podCIDRs` 条目，并启用 `k8s.requireIPv6PodCIDR`；multi-pool 地址池可包含 `ipv4`、`ipv6` 或两者，并提供对应地址族的注解 `ipam.cilium.io/ipv4-pool` 和 `ipam.cilium.io/ipv6-pool`；ENI IPv6 为 beta（见“释放、use-primary-address 与 IPv6”）；LB IPAM 遵循 Service 的 `ipFamilyPolicy`（见下文 LB IPAM）。AWS 支持的 EKS Hybrid Nodes 配置仅支持 IPv4。

## Multi-Pool IPAM

### 概念

Multi-pool 将“整个集群共用一份 CIDR 列表”改为使用多个具名 **pool**，每个 pool 都是一个 `CiliumPodIPPool`。节点可以同时持有多个地址池中的地址块，并由 agent 按需申请。适用于不同租户使用不同地址范围、为部分 Pod 提供可路由地址（按地址池使用 BGP 通告）、按站点划分地址范围，以及需要保留源 IP 的地址池。

### 前提条件与安装

上游教程要求启用 `kubeProxyReplacement=true` 和 `bpf.masquerade=true`。已知限制：基于 iptables 的伪装需要配置 `egressMasqueradeInterfaces`（上游问题 22273），因此受支持的路径是 eBPF masquerade。各地址池的 CIDR 不能互相重叠（IP cache 会将一个前缀映射到一个身份）。

```yaml
ipam:
  mode: multi-pool
  multiPoolPreAllocation: "default=8,mars=4"
  operator:
    autoCreateCiliumPodIPPools:
      default:
        ipv4: { cidrs: ["10.10.0.0/16"], maskSize: 27 }
      mars:
        ipv4: { cidrs: ["10.20.0.0/16"], maskSize: 27 }
kubeProxyReplacement: true
bpf: { masquerade: true }
```

`autoCreateCiliumPodIPPools` 只会创建尚不存在的地址池，不会更新已有地址池。它对应 operator flag `--auto-create-cilium-pod-ip-pools <pool>=ipv4-cidrs:...;ipv4-mask-size:...[;allow-first-ip:...][;allow-last-ip:...]`；该语法无法表示 `podSelector`、`namespaceSelector` 或（1.21 中的）`pool[].reservedRanges`。这些地址池应创建为自定义资源。

### CiliumPodIPPool

```yaml
apiVersion: cilium.io/v2alpha1      # 1.20.x; use cilium.io/v2 from 1.21 [1.21 pre-release]
kind: CiliumPodIPPool
metadata:
  name: mars
spec:
  # allowFirstIP / allowLastIP are fields of spec (not of spec.ipv4); default false,
  # ignored for /31 /32 /127 /128
  ipv4:
    cidrs: ["10.20.0.0/16"]
    maskSize: 27
  podSelector:
    matchLabels:
      io.kubernetes.pod.namespace: tenant-mars   # synthetic label
  namespaceSelector:
    matchLabels:
      tenant: mars
```

此资源的作用范围是整个集群，短名称为 `cpip`。`maskSize`、`allowFirstIP` 和 `allowLastIP` 均不可变（CEL 规则为 `self == oldSelf`）。除非设置 `allowFirstIP` / `allowLastIP`，否则每个*分配给节点的地址块*的首尾地址都会保留。若地址池中没有某个地址族对应的地址块，则该地址族会跳过此地址池。

**API 版本说明**。1.20.2 使用 `cilium.io/v2alpha1`。**[1.21 预发布版]** `cilium.io/v2` 将成为存储版本，`v2alpha1` 将弃用；v2 还会将 `cidrs` 限制为最多 32 项，并新增 `spec.ipv4.pool[]` / `spec.ipv6.pool[]`（见“安全更新地址池”）。升级到 1.21 时，请将清单和工具更新为 v2。

### 地址池选择

在 Pod 创建时只评估一次（更改运行中 Pod 的注解不会生效）。以下优先级来自源码（`pkg/ipam/metadata/manager.go`）和文档：

1. **Pod 注解**：按地址族配置的 `ipam.cilium.io/ipv4-pool` / `ipam.cilium.io/ipv6-pool` 优先于 `ipam.cilium.io/ip-pool`。
2. **Namespace 注解**：在 Pod 所属 namespace 上使用相同的键。
3. **`CiliumPodIPPool` 选择器**：`podSelector` 和 `namespaceSelector`（如果两者都配置，则必须同时匹配）。每个地址族必须恰好匹配一个地址池；否则分配会**失败**，并返回错误和事件。
4. **默认地址池**：`ipam-default-ip-pool`（默认值为 `default`）；但如果 Pod 或 namespace 带有 `ipam.cilium.io/require-pool-match: "true"` 注解，则会阻止分配。

正确的注解键是 `ipam.cilium.io/ip-pool`（`pkg/annotation/k8s.go`）。部分上游教程写成 `ipam.cilium.io/ipam-pool`；该键不起作用。

```bash
kubectl annotate namespace tenant-mars ipam.cilium.io/ip-pool=mars
```

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: pinned
  annotations:
    ipam.cilium.io/ip-pool: mars
spec:
  containers:
  - name: app
    image: registry.k8s.io/pause:3.10
```

### agent 如何申请容量

agent 会将需求写入 `CiliumNode.spec.ipam.pools.requested[] {pool, needed{ipv4-addrs, ipv6-addrs}}`。operator 会按地址池的 `maskSize` 划分节点地址块，直到节点的可用地址数满足 `needed`，然后将其追加到 `spec.ipam.pools.allocated[] {pool, cidrs[], allowFirstIP, allowLastIP}`。若某些地址块完全空闲且超出需求，agent 会将其移除。错误会写入 `status.ipam.operator-status.error`。

文档给出的公式是 `neededIPs = roundUp(inUse + pending + preAlloc, preAlloc)`。源码中的 `neededIPCeil`（`pkg/ipam/multipool_manager.go`）会额外保留一个预分配单位的余量：当 `preAlloc = P` 时，需求为 0 会申请 `P`，需求为 1 到 `P` 会申请 `2P`，需求为 `P+1` 会申请 `3P`。agent flag 是 `--ipam-multi-pool-pre-allocation`（Helm 配置项 `ipam.multiPoolPreAllocation`）；为空时，`default=8`，其他地址池的默认值为 0。该数量针对每个已启用的地址族分别计算。

由于地址块按 `maskSize` 粒度分配，应选择合适的 `maskSize`，使地址块比 `preAlloc` 大数倍（例如 `/27` = 32 个地址，`preAlloc=8`）；否则节点会反复申请和释放大量很小的地址块。

### 每节点默认地址池、伪装与路由

使用 `CiliumNodeConfig` 设置**每节点默认地址池**（`cilium.io/v2`，namespace 为 `kube-system`）。只有 agent Pod 重启后更改才会生效。

```yaml
apiVersion: cilium.io/v2
kind: CiliumNodeConfig
metadata:
  name: ip-pool-dc1
  namespace: kube-system
spec:
  defaults:
    ipam-default-ip-pool: dc1-pool
  nodeSelector:
    matchLabels:
      topology.kubernetes.io/zone: dc1
```

不要将此覆盖项用于 cluster-pool 迁移所用的命名地址池（见“cluster-pool 到 multi-pool 在线迁移”小节）。

**Masquerade**。agent 选项 `--only-masquerade-default-pool`（要求使用 eBPF masquerade），或 `CiliumPodIPPool` 上按地址池设置的注解 `ipam.cilium.io/skip-masquerade="true"`，都可保留非默认地址池 Pod 的源 IP；该设置只影响新建 Pod。agent 选项没有专用的 Helm 配置键；可使用 `extraConfig.only-masquerade-default-pool: "true"`（本次审阅未实际运行这条配置路径）。

**路由**。地址池 CIDR 可以通过 BGP Control Plane 通告（`advertisementType: CiliumPodIPPool`，见[第 11 部分](11-bgp-lb-egress-edge.md)），也可以在共享 L2 网段上通过 `autoDirectNodeRoutes` 访问。

### 安全更新地址池及 `reservedRanges` [1.21 预发布版]

规则：运行中的集群可以新增地址池和额外 CIDR；不得移除节点正在使用的 CIDR，也不得删除正在使用的地址池（operator 会记录 `CIDR from pool still in use by node`）。在 1.20 中替换 CIDR 的流程是：编辑地址池并重启 operator，然后对每个节点组依次 cordon、drain、删除其 `CiliumNode` 对象、重启 agent，再 uncordon；每次只处理一个节点组。

**[1.21 预发布版]** `cilium.io/v2` 新增按 CIDR 配置的 `reservedRanges`，因此可以退役一个 CIDR，而不会遗留失效的地址分配：

```yaml
apiVersion: cilium.io/v2
kind: CiliumPodIPPool
metadata:
  name: default
spec:
  ipv4:
    cidrs: ["10.10.0.0/16", "10.20.0.0/16"]
    maskSize: 24
    pool:
    - cidr: 10.10.0.0/16
      reservedRanges:
      - start: 10.10.0.0
        end: 10.10.255.255
```

`10.10.0.0/16` 中现有的节点地址块会继续工作；新地址块只会从 `10.20.0.0/16` 分配。所有节点组迁移完成后，从 `cidrs` 中移除旧 CIDR 及对应的 `pool` 条目。每个 `pool[].cidr` 都必须是 `cidrs` 中的一个值（由 CEL 校验）。

### cluster-pool 到 multi-pool 在线迁移（1.20+）

该功能在 1.19 及更早版本中不存在。operator 选项：`enable-cluster-pool-to-multi-pool-migration`（默认 false）、`multi-pool-migration-workers`（默认 16）、`ipam-default-ip-pool`。

前提条件：迁移是单向的（不能回滚）；每个现有 Pod 都会进入**默认地址池**；operator 重启前必须创建默认地址池（使用自定义资源或 `autoCreateCiliumPodIPPools`），该地址池必须覆盖所有已分配给节点的 CIDR，并使用相同的掩码大小；不要按节点覆盖默认地址池名称。

```bash
helm upgrade cilium cilium/cilium --version 1.20.2 -n kube-system --reuse-values \
  --set ipam.mode=multi-pool \
  --set ipam.operator.autoCreateCiliumPodIPPools.default.ipv4.cidrs='{10.0.0.0/8}' \
  --set ipam.operator.autoCreateCiliumPodIPPools.default.ipv4.maskSize=24 \
  --set-string extraConfig.enable-cluster-pool-to-multi-pool-migration=true \
  --set operator.rollOutPods=true \
  --set rollOutCiliumPods=false
```

然后等待每个 `CiliumNode` 都在 `spec.ipam.pools.allocated` 下列出已有的 PodCIDR。如果 BGP Control Plane 正在通告 PodCIDR，请在重启 agent **之前**将 `CiliumBGPAdvertisement` 从 `advertisementType: PodCIDR` 改为选择默认地址池的 `CiliumPodIPPool`（预计路由会短暂撤回，因为仍处于 cluster-pool 模式的 agent 会停止通告已迁移的地址分配）；随后一次性或分批重启 agent。滚动期间，混合运行 cluster-pool 和 multi-pool 模式的 agent 可以维持连通性。在所有 agent 都已重启前，不要调度使用非默认地址池的 Pod。

### 限制以及与 BGP 的交互

不同地址池的 CIDR 不能重叠；未设置 `egressMasqueradeInterfaces` 时不支持基于 iptables 的 masquerade；对于不连续的地址池，可考虑使用 `ip-masq-agent`。变更节点正在使用的地址池 CIDR 时，必须采用上述 drain 流程。

## CRD 支持的 IPAM（`ipam.mode=crd`）

agent 会监视名称与节点相同的 `CiliumNode`。`spec.ipam.pool` 是一个 map，形式为 `ip -> {owner, resource}`，包含可用的**单个 IP**（不支持 CIDR）；已使用的 IP 会记录在 `status.ipam.used` 中，每 15 秒最多更新一次状态（Helm 配置项 `ipam.ciliumNodeUpdateRate`）。IPv6 使用 `spec.ipam.ipv6-pool` 和 `status.ipam.ipv6-used`。此模式仅支持直接路由。

启动时，agent 会记录 `Waiting for initial IP to become available in '<node>' custom resource`，且至少需要一个 IP（启用健康检查时至少需要两个）。RBAC 必须允许完整访问 `ciliumnodes` 和 `ciliumnodes/status`。上游的说明文字仍使用 `available` / `inuse`；实际 schema 使用 `pool` / `used`，因此应以已安装的 CRD 为准。

## AWS ENI IPAM

### 架构（1.20.2）

只有 operator 会调用 EC2 API。它将 ENI 清单写入 `CiliumNode.status.eni.enis`。agent 会将清单转换为 `default` 地址池在 `spec.ipam.pools.allocated` 中的 CIDR：辅助 IP 转换为 `/32`，委派前缀转换为 `/28`（IPv4）或 `/80`（IPv6）。agent 在本地分配 Pod IP，并在 `spec.ipam.pools.requested` 中报告需求。1.20 的 ENI 模式没有 `CiliumPodIPPool`，也不使用 `ip-pool` 注解。1.19 和 1.18 中的 ENI 使用 CRD 分配器（`spec.ipam.pool`、`status.ipam.used`）。支持从 1.19 滚动升级到 1.20：operator 根据 `spec.ipam.pools.requested` 是否存在以及 `status.ipam.used` 是否缺失来区分新 agent。

ENI 模式会强制启用原生路由和 endpoint 路由（`eni.enabled=true` 已设置这些选项，因此 values 文件中的 `routingMode: native` 和 `endpointRoutes.enabled` 是重复配置），而且 agent 会拒绝 ENI 与隧道模式组合。从 1.18 起，ENI 模式的 `enableIPv4Masquerade` 默认值为 false。**[1.21 预发布版]** ENI 模式中的 `enableIPv6Masquerade` 默认值也为 false。

### 安装与节点准备

通过将 VPC CNI（`aws-node`）DaemonSet patch 为不可能匹配的 `nodeSelector` 来移除它（上游使用 `io.cilium/aws-node-enabled=true`），并以 `eni.enabled=true` 安装。创建节点组时添加启动污点 `node.cilium.io/agent-not-ready=true:NoExecute`，确保 agent 就绪前工作负载不会调度。关闭 NetworkManager / systemd-networkd 对 `eth0` 以外 `eth*` 接口的管理，否则操作系统可能移除辅助 IP（Amazon Linux 2023 相关）。如果替换 VPC CNI，还要清除 iptables 链 `AWS-SNAT-CHAIN-*` 和 `AWS-CONNMARK-CHAIN-*`。

operator 所需 IAM 权限（均在上游列出；尽量通过资源标签限制范围）：`ec2:DeleteNetworkInterface`、`DescribeInstanceTypes`、`DescribeNetworkInterfaces`、`DescribeSubnets`、`DescribeVpcs`、`DescribeRouteTables`（1.18 起必需）、`DescribeSecurityGroups`、`CreateNetworkInterface`、`AttachNetworkInterface`、`ModifyNetworkInterfaceAttribute`、`AssignPrivateIpAddresses`、`CreateTags`；还包括 `DescribeTags`（默认启用的 ENI 垃圾回收）、`UnassignPrivateIpAddresses`（释放）、`AssignIpv6Addresses`（IPv6）、`DescribeInstances`（使用 `--instance-tags-filter` 时）。**[1.21 预发布版]** 可选权限 `GetSecurityGroupsForVpc`（缺少时会回退并输出一条警告）、`DescribeManagedPrefixLists` / `GetManagedPrefixListEntries`。上游对前缀操作只记录了分配/取消分配私有 IP 的权限；编写最小权限策略前，应根据 AWS 文档确认具体 IAM action。通过 `eni.iamRole`（IRSA）或 `cilium-aws` Secret 提供凭证。

### Helm 配置值

```yaml
eni:
  enabled: true
  iamRole: arn:aws:iam::<account-id>:role/cilium-operator
  awsEnablePrefixDelegation: true
  awsReleaseExcessIPs: true
  eniTags:
    team: platform
  gcInterval: 5m                        # "0s" disables ENI garbage collection
  nodeSpec:                             # per-node settings, since 1.19
    firstInterfaceIndex: 1              # keep eth0 for node traffic
    subnetTags: ["pod-subnet=true"]
    securityGroupTags: ["cilium-pod-sg=true"]
    excludeInterfaceTags: ["no-cilium=true"]
    deleteOnTermination: true
ipam:
  nodeSpec:
    ipamMinAllocate: 16
    ipamPreAllocate: 8
  operator:
    externalAPILimitQPS: 8
    externalAPILimitBurstSize: 40
```

标签列表条目会在 ConfigMap 中渲染为以逗号分隔的 `key=value` 字符串（例如 `eni-subnet-tags`）。有两类筛选器，不能互换：operator 级别的 `eni.subnetIDsFilter`、`eni.subnetTagsFilter` 和 `eni.instanceTagsFilter` 限制 operator 管理哪些实例/子网，并假设部署时每个实例已经有一个位于匹配子网中的 ENI；若只想指定 Cilium **创建**的 ENI，应使用按节点配置的 `eni.nodeSpec` 值（或自定义 CNI 配置中的 `eni` 部分；同一字段存在两处配置时，CNI 配置优先于 Helm）。operator API 限流器的默认值为 4 QPS、burst 20。

值得了解的 operator flags（cmdref `cilium-operator-aws`）：`--aws-enable-prefix-delegation`、`--aws-release-excess-ips`、`--excess-ip-release-delay`（默认 180 秒）、`--eni-gc-interval`（5 分钟）、`--eni-tags`、`--parallel-alloc-workers`（50）、`--limit-ipam-api-qps`、`--limit-ipam-api-burst`、`--aws-max-results-per-call`。

### 分配算法

每节点配置项（位于 `CiliumNode.spec.ipam`）：`min-allocate`、`pre-allocate`（为 0 时按 8 处理）、`max-allocate`、`max-above-watermark`（没有 agent flag 或 Helm 配置键：在 `CiliumNode` 上设置，或放入 CNI 配置的 `ipam` 部分）、`static-ip-tags`。计算公式来自 `operator/pkg/ipam/nodemanager/node.go`：

```
deficit (needed) = max( preAllocate + used - available ,  minAllocate - available )
                   clamped to maxAllocate if set;  floor 0
excess  (only with --aws-release-excess-ips)
                 = max( available - used - preAllocate - maxAboveWatermark , 0 )
                   (while used is small, keep available >= minAllocate + maxAboveWatermark)
per-cycle allocation on the chosen ENI
                 = min( AvailableOnSubnet,
                        min( AvailableOnENI, needed + maxAboveWatermark + surgeAllocate ) )
   where surgeAllocate = pendingPods - needed
```

计算示例：`preAllocate=8`、`minAllocate=16`，节点有 10 个可用地址、已使用 4 个：缺口 = max(8 + 4 - 10, 16 - 10) = 6，因此 operator 至少再分配 6 个。小型实例上的预分配值会自动降低为 `min(8, (adapters - firstIndex) x (ipsPerENI - 1))`。默认 `max-allocate` 等于实例上限：`(adapters - firstInterfaceIndex) x (ipv4PerENI - 1)`；启用前缀委派时再乘以 16。使用 `usePrimaryAddress` 时，每个 ENI 额外贡献一个地址。

调度：每次 `CiliumNode` 更新都会重新评估缺口，并且每分钟完整扫描一次；工作队列按需处理，但每秒最多处理一次，优先处理缺口最大的节点，并且先分配、后释放。

地址来源：operator 会遍历已连接且索引大于等于 `first-interface-index`、有可用容量和子网地址的 ENI；若没有合适的 ENI，就创建一个。候选子网必须位于同一 VPC 和 AZ，并根据 `subnet-ids`（优先级更高）或 `subnet-tags`（所有标签都必须匹配）进一步筛选；最终选择空闲地址最多的子网。两者都未设置时，依次使用节点主 ENI 所在子网、同一路由表中的子网、VPC/AZ 中最大的子网。安全组按以下顺序确定：使用 `spec.eni.security-groups`；否则使用 `security-group-tags`；否则继承 eth0 的安全组。ENI 描述为 `Cilium-CNI (<instance-id>)`，并添加集群标签及 `--eni-tags`。调用的 API 包括 `CreateNetworkInterface`、`AttachNetworkInterface`、`ModifyNetworkInterfaceAttribute`（是否随实例终止删除，默认 true）和 `AssignPrivateIpAddresses`。

### 前缀委派

`eni.awsEnablePrefixDelegation=true`（节点级退出选项：`eni.nodeSpec.disablePrefixDelegation`）会让 operator 分配 `/28` 前缀（16 个地址），而非单个辅助 IP，使每个 ENI 的容量增加 16 倍。源码中列出的限制如下：

- 仅适用于 **Nitro 或裸金属**实例类型。
- 不支持混合模式：如果节点任一 ENI 上已经有辅助 `/32` IP，就不会启用（检查时忽略主 ENI 的 IP）。
- 分配时调用 `AssignENIPrefixes`，数量为 `ceil(needed / 16)`。如果子网返回 `InsufficientPrefixesInSubnet`，operator 会记录不再为该节点分配前缀，并回退到辅助 `/32` IP。
- 子网必须有连续的空闲 `/28` 网段；碎片化的子网可能先耗尽可分配前缀，而非地址总量（这是 AWS 侧行为；见 AWS 前缀委派文档）。

### 释放、use-primary-address 与 IPv6

**释放**（仅 IPv4，要求 `--aws-release-excess-ips=true`）：agent 会从 `spec.ipam.pools.allocated` 中移除完全空闲的 CIDR；operator 等待 `--excess-ip-release-delay`（默认 180 秒），然后调用 `UnassignPrivateIpAddresses`（针对 `/32`）或取消分配前缀（`/28`）。释放操作**不会**分离或删除 ENI；ENI GC 会删除过期 ENI（标签 `io.cilium/cilium-managed=true` 和 `io.cilium/cluster-name=<name>`）。1.19 使用的 `status.ipam.release-ips` 握手机制仅适用于旧版 CRD 分配器 agent。

**`usePrimaryAddress`**：允许将 ENI 主私有 IP 分配给 Pod（每个 ENI +1）。**[1.21 预发布版]** operator flag `--aws-use-primary-address` 已**移除**；应设置 `eni.nodeSpec.usePrimaryAddress=true`（agent flag `--eni-use-primary-address`，存储在 `CiliumNode.spec.eni.use-primary-address` 中）。Helm 用户不受影响，因为 chart 只配置了 agent 侧选项。

**IPv6（1.20 中为 beta；agent 会记录 beta 警告）**：设置 `ipam.mode=eni`、`eni.enabled=true` 和 `ipv6.enabled=true`。每个节点只获得一个委派的 `/80` 前缀，在创建 ENI 时或通过 `AssignIpv6Addresses` 分配，且永不释放；没有水位线；子网必须为双栈。由于每个 ENI 都需要一个主 IPv4 地址，因此不支持纯 IPv6 子网。上游 EKS 需求页面仍称 ENI 仅支持 IPv4；ENI 页面和运行时 beta 警告的信息更新。

### ENI 注意事项

Pod 密度上限为 `(ENIs - firstIndex) x (IPs per ENI - 1)`（启用前缀时乘以 16）。除非按节点组设置 `spec.eni.security-groups`，否则 Pod 会共用节点 ENI 的安全组。Cluster Mesh 使用集群 ID 128–255 且同时使用 ENI 的集群会遇到已知的策略丢弃问题（见[第 13 部分](13-clustermesh-install-upgrade.md)）。1.20 中移除（1.19 仍存在）的字段有 `CiliumNode.spec.eni.min-allocate`、`pre-allocate`、`max-above-watermark` 和 `instance-id`；同名值现在位于 `spec.ipam` 下。基于 VPC CNI 的 chaining 是另一种设计，本章不予讨论。


## Azure、AKS 与 Alibaba Cloud

**AKS**。Azure CNI Powered by Cilium 属于托管模式：使用 `ipam: delegated-plugin`，CNI 配置为 `"ipam": {"type": "azure-ipam"}`，并设置 `local-router-ipv4: 169.254.23.0`。Cilium 不会分配 Pod IP。BYOCNI 集群可以使用任意 Cilium IPAM；Helm 的 `azure.enabled` 与 BYOCNI 不兼容，应使用 `aksbyocni.enabled`。

**自管 Azure（上游 `--ipam=azure`）。operator** flags 包括 `--azure-subscription-id`、`--azure-resource-group`（对于 VMSS，应设置包含该 VMSS 的资源组；设置错误会导致没有地址）、`--azure-user-assigned-identity-id`（这是 client ID，不是资源 ID）和 `--azure-use-primary-address`；认证使用 DefaultAzureCredential 链。每节点配置项为 `azure.nodeSpec.azureInterfaceName`。在 1.20 中，operator 发布包含新 `subnet{id,cidr}` 对象的 `status.azure.interfaces[]`（原先的扁平 `cidr` 和 `addresses[].subnet` 已弃用）。**[1.21 预发布版]** Azure 将迁移到与 ENI 共用的 cloud multi-pool 框架：每个 `succeeded` 地址都会成为默认地址池中的 host prefix，不再释放多余 IP；如果 `--ipv4-native-routing-cidr` 未设置，agent 最多等待 5 分钟以取得有效的 IPv4 子网 CIDR，并将其用作原生路由 CIDR。

**Alibaba Cloud**。使用 `ipam.mode=alibabacloud`、`alibabacloud.enabled` 和按节点设置的 `alibabacloud.nodeSpec.{vSwitches,vSwitchTags,securityGroups,securityGroupTags}`；采用 CRD 分配器。安装指南会替换 Terway/Flannel，并使用 `cilium-alibabacloud` Secret。本章不进一步讨论 Alibaba Cloud；其限制和 IPv6 行为尚未检查。

## Pod IP 以外：LB IPAM、Node IPAM、CiliumCIDRGroup

### LB IPAM 与 `CiliumLoadBalancerIPPool`

LB IPAM 为 `type: LoadBalancer` Service 分配地址。它运行在 operator（`operator/pkg/lbipam`）中，始终编译启用（Helm `enableLBIPAM`，默认 true），并在创建第一个地址池前保持休眠。它**只负责分配**：要让地址可达，还需要 BGP Control Plane（`loadBalancerClass: io.cilium/bgp-control-plane`）或 L2 Announcements（`io.cilium/l2-announcer`），详见[第 11 部分](11-bgp-lb-egress-edge.md)。

> **安全范围**。LB IPAM 地址池必须使用私有地址范围。若没有 BGP 或路由集成，LB IPAM VIP 在 VPC 内无法访问；因此在 EKS 上应使用内部 AWS 负载均衡器。对外的访问路径始终是 CloudFront 到内部 ALB/NLB。LB IPAM 适用于通过 BGP 或 L2 通告连接的本地和混合站点。上游示例会使用类似 `20.0.0.0/8` 的公网地址段；本章使用 RFC 1918 地址段。

```yaml
apiVersion: cilium.io/v2
kind: CiliumLoadBalancerIPPool
metadata:
  name: blue-pool
spec:
  blocks:
  - cidr: 10.0.10.0/24
  - start: 10.0.20.100        # start and stop form ONE block; keep them in one list item
    stop: 10.0.20.200
  serviceSelector:
    matchLabels:
      color: blue
  allowFirstLastIPs: "No"     # default "Yes"; "No" reserves network/broadcast; cidr blocks only
  # disabled: true            # stop new allocations, keep existing ones
```

事实：API 为 `cilium.io/v2`（`v2alpha1` 于 1.19.8 首次标记为弃用），资源作用范围为集群，短名称是 `ippools`、`ippool`、`lbippool`、`lbippools`；打印列包括 Disabled、Conflicting、IPs Available。`serviceSelector` 接受普通标签，以及合成标签 `io.kubernetes.service.namespace` 和 `io.kubernetes.service.name`。地址池重叠时，后创建的池会标为 Conflicting（条件为 `cilium.io/PoolConflict`），且不会分配地址。池条件还包括 `cilium.io/IPsTotal`、`IPsAvailable`、`IPsUsed`。编辑地址池可能导致已有 Service IP 被重新分配（上游问题 40358），因此优先添加新池或设置 `disabled: true`。

Service 处理方式：没有设置 `loadBalancerClass` 的 `LoadBalancer` Service 会由 LB IPAM 处理，除非 Helm 的 `defaultLBServiceIPAM` 设为 `none`（可选值：`lbipam`、`nodeipam`、`none`）；具有未知 class 的 Service 会被忽略。Service 条件 `cilium.io/IPAMRequestSatisfied` 的 reason 为 `satisfied` 或 `no_pool`。默认使用单栈（两种地址族都启用时使用 IPv4）；`PreferDualStack` 会尝试使用两个地址族；若某个地址族未启用，`RequireDualStack` 会保持未满足状态。

请求指定地址：设置注解 `lbipam.cilium.io/ips: "10.0.10.100,10.0.10.101"`（旧字段 `.spec.loadBalancerIP` 已弃用）。地址池的 `serviceSelector` 仍然适用；若池的 `allowFirstLastIPs: "No"`，不得请求其第一个或最后一个地址。

让多个 Service 共用一个 IP：

```yaml
metadata:
  annotations:
    lbipam.cilium.io/sharing-key: "web-vip"
    lbipam.cilium.io/sharing-cross-namespace: "ns1,ns2"   # or "*"
```

在 1.20 中，使用相同共享键的两个 Service 若端口/协议不冲突，就会共用一个 IP；若冲突，则从该共享键的集合中分配不同的 IP。**[1.21 预发布版]兼容性检查更加严格**：Service 必须使用相同的 `externalTrafficPolicy`；若为 `Local`，两者还必须选择相同的 Pod。新注解 `lbipam.cilium.io/sharing-permit-different-pods: "true"` 会关闭该安全检查；与 Cilium BGP 或 L2 通告配合时并不安全（这些机制不了解 L4，因此不同节点可能同时响应同一个 IP）。

指标（文档使用 `cilium_` 前缀；控制器运行于 operator 中，其 registry 可能覆盖 namespace，因此运行时前缀也可能是 `cilium_operator_lbipam_*`。本章未在运行时验证，请检查实际抓取到的名称）：`cilium_lbipam_conflicting_pools`、`cilium_lbipam_ips_available{pool}`、`cilium_lbipam_ips_used{pool}`、`cilium_lbipam_services_matching`、`cilium_lbipam_services_unsatisfied`。

数据路径说明（1.19）：当端口与已配置的 Service 不匹配时，发往 LB IPAM 或 ClusterIP 地址的南北向 TCP/UDP 流量会被丢弃。

### Node IPAM

`nodeIPAM.enabled=true`（默认 false；会设置 `enable-node-ipam`）允许带有 `loadBalancerClass: io.cilium/node`（或使用 `defaultLBServiceIPAM: nodeipam`）的 Service 将节点地址作为负载均衡器入口地址发布。在现有安装中启用后，应重启 operator（`kubectl -n kube-system rollout restart deployment/cilium-operator`）。operator 会将每个所选节点的 ExternalIP（如果存在），否则 InternalIP，填入 `status.loadBalancer.ingress`，并遵循 `ipFamilies`。`externalTrafficPolicy: Cluster` 会使用所有节点；`Local` 只使用承载所选 Pod 的节点（需要 EndpointSlices；不适用于 Cilium Ingress/Gateway 的虚拟 endpoint）。带有标签 `node.kubernetes.io/exclude-from-external-load-balancers` 或污点 `ToBeDeletedByClusterAutoscaler` 的节点会被排除；Service 注解 `io.cilium.nodeipam/match-node-labels` 可按标签筛选节点。

Node IPAM 会将节点地址作为 Service 地址发布。仅在节点 IP 为私有地址的环境中使用；它不是 AWS 上的公网暴露机制。

### CiliumCIDRGroup

`CiliumCIDRGroup` 是一组具名 CIDR（`spec.externalCIDRs`），策略可以通过 `cidrGroupRef` 或 `cidrGroupSelector` 引用，而不必将 CIDR 逐条写入策略。无论列表大小如何，一个组只使用一个安全身份，更适合扩展大型列表；Hubble 还会在流量上标注组名。此资源作用范围为集群，短名称是 `ccg`。使用 `cilium.io/v2`；`v2alpha1` 已弃用（部分上游示例仍使用它）。

```yaml
apiVersion: cilium.io/v2
kind: CiliumCIDRGroup
metadata:
  name: corp-ranges
  labels:
    tier: internal
spec:
  externalCIDRs:
  - 10.30.0.0/16
  - 192.168.100.0/24
---
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: egress-corp
spec:
  endpointSelector:
    matchLabels:
      app: batch
  egress:
  - toCIDRSet:
    - cidrGroupRef: corp-ranges
```

## 运维：检查、指标与升级

```bash
# per-node view of what each node owns
kubectl get ciliumnodes -o custom-columns=NAME:.metadata.name,CIDRS:.spec.ipam.podCIDRs
kubectl get ciliumnode <node> -o yaml        # .spec.ipam, .status.ipam, .status.eni.enis
kubectl get ciliumpodippools                 # multi-pool; short name cpip
kubectl get ippools                          # LB IPAM pools
kubectl -n kube-system logs deploy/cilium-operator | grep -i ipam
```

**Agent 指标：**`cilium_ipam_capacity{family,cidr}`（在 cluster-pool 和 kubernetes 模式下，`cidr` 标签是节点 CIDR；其他模式下为空）、`cilium_ipam_events_total{action,family}`、`cilium_ip_addresses{family}`。

**Operator 指标**（前缀 `cilium_operator_`；通过 `operator.prometheus.enabled` 启用）：`ipam_available_ips{target_node}`、`ipam_used_ips`、`ipam_needed_ips`、`ipam_ip_allocation_ops{subnet_id}`、`ipam_ip_release_ops`、`ipam_interface_creation_ops`、`ipam_interface_candidates`、`ipam_empty_interface_slots`、`ipam_available_ips_per_subnet{subnet_id,availability_zone}`、`ipam_nodes{category=total|in-deficit|at-capacity}`、`ipam_resync_total`、`ipam_allocation_duration_seconds`、`ipam_release_duration_seconds`、`ipam_background_sync_duration_seconds`。上游指标表已过时：它遗漏了 `interface_candidates`、`empty_interface_slots`、`available_ips_per_subnet` 和 `background_sync_duration_seconds`；以上列表依据源码。云 API 调用指标不使用 `ipam_` 前缀：子系统名称对应云厂商，因此 AWS 指标为 `cilium_operator_ec2_api_duration_seconds{operation,response_code}` 和 `cilium_operator_ec2_api_rate_limit_duration_seconds{operation}`（Azure 和 Alibaba Cloud 使用各自的子系统）。1.20 已移除 `ipam_ips` 和 `ipam_available_interfaces`。

建议的告警：`ipam_nodes{category="at-capacity"} > 0`、`ipam_nodes{category="in-deficit"}` 持续上升、每个 AZ 的 `ipam_available_ips_per_subnet` 低于阈值、`ec2_api_rate_limit_duration_seconds` 持续升高，以及 `lbipam_conflicting_pools > 0`。

**升级说明**。支持 ENI 从 1.19 滚动升级到 1.20。**[1.21 预发布版]operator** ClusterRole 新增对 `ciliumpodippools` 的 list/patch 权限（存储版本迁移），并移除 operator flag `--aws-use-primary-address`（见“释放、use-primary-address 与 IPv6”）。若直接传入该 operator flag，而不是通过 Helm 设置，升级前应将其替换为 `eni.nodeSpec.usePrimaryAddress=true`。

## 实验

> 本次审阅没有在真实集群上执行这些实验。实验步骤已依据上游源码和文档核对（见“验证范围限制”）。请用文字描述实际观察到的行为与预期是否相符；格式不必完全一致。

### 实验 1：Cluster-pool 容量规划与耗尽（kind）

前提条件：一个包含两个 worker 的 kind 集群；通过 Helm 使用默认 `cluster-pool` 安装的 Cilium；以及 kubectl 和 Helm。

1. 使用刻意设小的节点掩码安装：

   ```bash
   helm upgrade --install cilium cilium/cilium --version 1.20.2 -n kube-system \
     --set ipam.mode=cluster-pool \
     --set ipam.operator.clusterPoolIPv4PodCIDRList='{10.244.0.0/16}' \
     --set ipam.operator.clusterPoolIPv4MaskSize=28
   ```
2. 查看各节点的地址块：`kubectl get ciliumnodes -o custom-columns=NAME:.metadata.name,CIDRS:.spec.ipam.podCIDRs`。每个节点持有一个 `/28`（16 个地址）。
3. 使用 `nodeSelector` 将 Deployment 固定到一个 worker，并将副本数扩展到 20。
4. 预期结果：最初的 Pod 会运行；当节点的可用地址（16 个地址减去网络、广播以及路由器/健康检查/Ingress 地址）用完后，其余 Pod 会因 CNI 分配错误而停留在 `ContainerCreating`。`cilium-dbg status` 会显示节点地址范围已全部分配。
5. 根据“容量规划计算”中的公式计算预期上限，并与实际 Pod 数量比较。

清理：删除 Deployment。回滚：运行中的集群无法更改掩码，因此应重新安装集群，而不是修改该配置值。

### 实验 2：Multi-pool 选择（kind）

前提条件：kind、Cilium 1.20.2、`ipam.mode=multi-pool`、`kubeProxyReplacement=true`、`bpf.masquerade=true`，以及 multi-pool 安装配置值中的 `default` 和 `mars` 地址池。

1. 创建两个 namespace。为其中一个添加注解：`kubectl annotate namespace ns-a ipam.cilium.io/ip-pool=mars`。
2. 在各 namespace 中运行一个 Pod，并检查 `kubectl get pods -A -o wide`。预期结果：带注解的 namespace 中的 Pod 从 `10.20.0.0/16` 获取地址，另一个 Pod 从 `10.10.0.0/16` 获取地址。
3. 在未注解的 namespace 中运行 Pod，并为 Pod 设置注解 `ipam.cilium.io/ip-pool: mars`。预期结果：Pod 注解优先于 namespace 默认值。
4. 为第三个 namespace 添加注解 `ipam.cilium.io/require-pool-match: "true"`，但不创建匹配的地址池，然后启动 Pod。预期结果：Pod 保持 pending，并出现地址池匹配错误。
5. 检查 `kubectl get ciliumnode <n> -o yaml`，查看 `spec.ipam.pools.requested` 和 `allocated`；`cilium-dbg status --all-addresses` 会显示 `pool/ip` 条目。

清理：删除 namespace；如有需要，也可删除集群。

### 实验 3：从 Cluster-pool 迁移到 Multi-pool（kind）

前提条件：运行 1.20.2、使用 cluster-pool 且已有 Pod 运行的 kind 集群。迁移是单向的，因此请使用可丢弃集群。

1. 记录 `kubectl get ciliumnodes -o yaml | grep -A3 podCIDRs` 的输出。
2. 按“cluster-pool 到 multi-pool 在线迁移”小节执行 Helm upgrade；默认地址池必须覆盖记录的 CIDR，并使用相同掩码。
3. 等待每个节点的 PodCIDR 出现在 `spec.ipam.pools.allocated` 下。
4. 重启 agent（`kubectl -n kube-system rollout restart ds/cilium`）。预期结果：现有 Pod 保留原地址并显示为 restored；滚动期间，跨节点 Pod 仍能互相访问。

不支持回滚。请重新创建集群。

### 实验 4：使用 L2 通告的 LB IPAM（kind，私有地址段）

前提条件：kind 集群，启用 `l2announcements.enabled=true` 和 `kubeProxyReplacement=true`；从 kind Docker 网络中的空闲范围选择地址（使用 RFC 1918 私有地址空间）。

1. 创建 `CiliumLoadBalancerIPPool`，配置较小的 `start`/`stop` 地址块和 `serviceSelector`。
2. 应用 L2 通告策略（见第 11 部分）以及标签匹配的 `LoadBalancer` Service。
3. 预期结果：`kubectl get ippools` 显示可用 IP 数量减少；Service 从地址块中取得 external IP；Service 条件 `cilium.io/IPAMRequestSatisfied` 显示 `satisfied`。
4. 创建另一个地址块重叠的地址池。预期结果：它被标为 Conflicting，且不分配任何地址。
5. 对第一个地址池设置 `disabled: true`，并创建另一个 Service。预期结果：不再从该池分配新地址，但已有 Service 保留原 IP。

清理：删除 Service、地址池和策略。

### 实验 5：使用前缀委派的 EKS ENI 模式（沙盒账户）

前提条件：使用专用私有子网 VPC 的一次性 EKS 集群；节点使用 Nitro 实例类型且无公网 IP；节点安全组仅允许 VPC/集群安全组引用（不得设置 `0.0.0.0/0` 或 `::/0`）；operator IAM 权限按“安装与节点准备”小节配置；并使用目标沙盒账户的 AWS CLI profile。

1. 创建节点组并添加污点 `node.cilium.io/agent-not-ready=true:NoExecute`。禁用 VPC CNI（不要安装托管插件，或将 `aws-node` patch 为不可能匹配的 node selector）。
2. 安装 Cilium，设置 `eni.enabled=true`、`eni.awsEnablePrefixDelegation=true`、`eni.awsReleaseExcessIPs=true` 和 `eni.iamRole`，其余配置值参照“Helm 配置值”小节。
3. 验证清单：`kubectl get ciliumnode <n> -o jsonpath='{.status.eni.enis}'` 应列出带前缀的 ENI；`aws ec2 describe-network-interfaces --filters Name=description,Values='Cilium-CNI*'` 应返回相同 ENI。预期结果：`spec.ipam.pools.allocated` 中包含 `/28` 地址块。
4. 将 Deployment 扩展到超过一个 `/28`（每节点超过 16 个 Pod）。预期结果：operator 会再分配一个前缀；`cilium_operator_ipam_available_ips` 会保持高于 `used + preAllocate`。
5. 缩减副本数，并等待超过 180 秒。预期结果：未使用的前缀会释放，ENI 仍保持连接。

清理：将副本缩至零，卸载 Cilium，删除节点组和任何遗留的 `Cilium-CNI` ENI（启用 ENI GC 后会删除带标签的孤立 ENI）。回滚：在新的节点组上重新启用 VPC CNI 插件；不要在同一组运行中的节点上切换 IPAM。

### 实验 6：Node IPAM（kind）

前提条件：安装了 Cilium 且启用 `nodeIPAM.enabled=true` 的 kind 集群（启用后重启 operator）。

1. 创建带有 `loadBalancerClass: io.cilium/node` 的 `LoadBalancer` Service。
2. 预期结果：`status.loadBalancer.ingress` 列出节点 InternalIP（kind 节点没有 ExternalIP）。
3. 为一个节点添加标签 `node.kubernetes.io/exclude-from-external-load-balancers`。预期结果：该节点地址从列表中移除。

清理：删除 Service 和该标签。

## 版本差异

| 主题 | 1.18 | 1.19 | 1.20 | 1.21 预发布版 |
|---|---|---|---|---|
| Multi-pool 成熟度 | Beta 标记 | 移除标记 | 稳定版 | 稳定版 |
| 地址池选择 | 仅 `ip-pool` 注解 | 新增 `ipv4-pool`/`ipv6-pool` 注解和 `podSelector`/`namespaceSelector`（1.18.14 已有）；`require-pool-match`、`skip-masquerade`、`--only-masquerade-default-pool` 首次出现在 1.19 | 新增 `allowFirstIP`/`allowLastIP` | 同上，另新增 `pool[].reservedRanges` |
| `CiliumPodIPPool` API | v2alpha1 | v2alpha1 | v2alpha1 | v2 存储版本，v2alpha1 弃用，`cidrs` 最多 32 项 |
| cluster-pool 到 multi-pool 迁移 | 不支持 | 不支持 | 新增（`enable-cluster-pool-to-multi-pool-migration`） | 同上 |
| ENI agent 模型 | CRD 分配器 | CRD 分配器 | multi-pool 分配器；IPv6 为 beta（`/80`）；通过 `pools.allocated` 释放 | 与 Azure 共用 cloud multi-pool 框架 |
| 每节点 ENI Helm 配置（`eni.nodeSpec`、`ipam.nodeSpec`） | 仅 CNI conf | 新增 | 同上 | 同上 |
| ENI masquerade 默认值 | `enableIPv4Masquerade` 为 false（新增） | | | `enableIPv6Masquerade` 为 false（新增） |
| ENI IAM | 新增 `DescribeRouteTables` | | | 新增可选 `GetSecurityGroupsForVpc`、`DescribeManagedPrefixLists`、`GetManagedPrefixListEntries` |
| Operator `--aws-use-primary-address` | 存在 | 存在 | 存在 | **移除** |
| `CiliumNode.spec.eni.{min,pre}-allocate`、`max-above-watermark`、`instance-id` | 存在 | 存在 | 移除 | 移除 |
| Operator IPAM 指标 | 已有按节点统计的 `available/used/needed_ips` 和 `interface_candidates` | 同上 | 移除 `ipam_ips`、`ipam_available_interfaces` | |
| Azure IPAM | CRD 分配器 | CRD 分配器 | `status.azure.interfaces[].subnet` | multi-pool 协议；不再释放多余 IP |
| `CiliumLoadBalancerIPPool` API | v2 | v2alpha1 弃用 | v2 | v2 |
| `CiliumCIDRGroup` API | v2alpha1 弃用 | v2 | v2 | v2 |
| LB IPAM 共享 | 共享键 + 跨 namespace | | 端口冲突规则 | 更严格的兼容性检查 + `sharing-permit-different-pods` |

## 故障排查

现象：Pod 停留在 `ContainerCreating`；`kubectl describe pod` 显示 `unable to allocate IP via local cilium agent`。

| 模式 | 可能原因 | 检查方式 | 修复方法 |
|---|---|---|---|
| cluster-pool / kubernetes | 节点地址范围已满（`IPAM: IPv4: N/M allocated`） | `cilium-dbg status`、`--all-addresses` | 降低密度或增加节点；掩码不可变，若需扩大地址范围，应规划新地址池/集群 |
| cluster-pool | 地址池耗尽 | `status.ipam.operator-status.error` = `allocator full` | 向列表追加 CIDR（绝不要编辑现有条目） |
| cluster-pool | agent 始终无法启动 | CiliumNode 缺少 `spec.ipam.podCIDRs` | 检查 operator 日志、CIDR 是否重叠及冲突错误 |
| kubernetes | 没有节点 PodCIDR | `kubectl get node -o jsonpath='{.spec.podCIDRs}'` | 启用 `--allocate-node-cidrs` |
| multi-pool | `needed` 超出地址池可用容量 | `operator-status.error`：`failed to allocate ipv4 address for node ... from pool ...` | 向地址池追加 CIDR，或新建地址池 |
| multi-pool | 地址池不存在或尚未同步 | `kubectl get cpip`；错误 `ErrPoolNotReadyYet`、`ErrManagerPoolsNotSynced` | 在创建 Pod 前创建地址池；检查默认地址池是否存在 |
| multi-pool | 匹配到两个地址池 | 错误 `multiple CiliumPodIPPools match pod` | 收紧选择器 |
| multi-pool | 设置了 `require-pool-match` | 检查 Pod 或 namespace 注解 | 添加匹配的地址池或注解 |
| ENI | 实例的 ENI/IP 数量达到上限 | `ipam_nodes{category="at-capacity"}` | 使用更大规格的实例，或启用前缀委派 |
| ENI | 子网 IP 耗尽 | `ipam_available_ips_per_subnet` | 通过标签/ID 添加子网；若使用前缀委派，检查碎片化（可能回退到 `/32`） |
| ENI | EC2 限流 | `ec2_api_rate_limit_duration_seconds` | 调整 `externalAPILimitQPS` / `externalAPILimitBurstSize` |
| ENI | 缺少 IAM action | operator 日志 | 添加“安装与节点准备”小节列出的 action |
| ENI | 操作系统移除了辅助 IP | NetworkManager / systemd-networkd 日志 | 将 `eth0` 以外的 `eth*` 接口排除在管理范围外 |
| 任意模式 | CNI 崩溃导致 IP 泄漏 | IP 未出现在 endpoint 中，但仍被占用 | 等待 10 分钟的过期时间；或重启 agent 以重新协调 |

对于 LB IPAM：如果 Service 没有 external IP，应检查地址池的 Conflicting 标记、`cilium.io/IPAMRequestSatisfied` 条件、`serviceSelector` 是否匹配，以及是否由某种机制（BGP 或 L2）通告该地址。请记住，IPAM 模式不是开关：模式变更后，运行模式与 Helm 配置值不一致，意味着应暂停并规划迁移，而不是编辑 ConfigMap。

## 验证范围限制与来源

本次审阅未在真实集群上执行这些实验。命令、字段名、默认值、公式和 flags 均已根据引用版本中的 Cilium 源码和文档核对。以下内容未经验证：前缀分配和释放所需的 IAM action 名称（上游只列出私有 IP action）；`only-masquerade-default-pool` 对应的 Helm 配置路径（使用 `extraConfig`）；Alibaba Cloud 限制；以及来自预发布标签 v1.21.0-pre.3 的 1.21 内容。Azure 版本标签、`reservedRanges` 和 cloud multi-pool 框架可能在 GA 前变化。ENI 示例针对私有子网沙盒；本章没有示例会对互联网开放安全组、创建面向互联网的负载均衡器，或给计算资源附加公网 IP。

来源（除非特别注明，均为 v1.20.2）：

- IPAM 概念：https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/concepts/ipam/index.rst
- Cluster scope：https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/concepts/ipam/cluster-pool.rst
- Multi-pool：https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/concepts/ipam/multi-pool.rst
- Cluster-pool 到 multi-pool 迁移：https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/concepts/ipam/cluster-pool-to-multi-pool.rst
- AWS ENI：https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/concepts/ipam/eni.rst
- LB IPAM：https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/lb-ipam.rst
- Node IPAM：https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/node-ipam.rst
- 注解（`ip-pool` 键）：https://github.com/cilium/cilium/blob/v1.20.2/pkg/annotation/k8s.go
- 节点 CIDR 分配器：https://github.com/cilium/cilium/blob/v1.20.2/pkg/ipam/cidrset/cidr_set.go
- Multi-pool manager：https://github.com/cilium/cilium/blob/v1.20.2/pkg/ipam/multipool_manager.go
- ENI 节点管理器公式：https://github.com/cilium/cilium/blob/v1.20.2/operator/pkg/ipam/nodemanager/node.go
- 指标：https://github.com/cilium/cilium/blob/v1.20.2/Documentation/observability/metrics.rst
- [1.21 预发布版] multi-pool 和 `reservedRanges`：https://github.com/cilium/cilium/blob/v1.21.0-pre.3/Documentation/network/concepts/ipam/multi-pool.rst
- [1.21 预发布版] 升级说明：https://github.com/cilium/cilium/blob/v1.21.0-pre.3/Documentation/operations/upgrade-next.inc
- [1.21 预发布版] LB IPAM 共享：https://github.com/cilium/cilium/blob/v1.21.0-pre.3/Documentation/network/lb-ipam.rst
- AWS，EKS Hybrid Nodes CNI：https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-cni.html

## 小测验

通过[第 10 部分小测验](../../quizzes/networking/cilium/10-ipam-deep-dive-quiz.md)检验一下自己。
