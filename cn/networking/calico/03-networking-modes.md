# 第 3 部分：网络模式

> **支持的版本**：Calico v3.29+ / Kubernetes 1.28+ **最后更新**：February 23, 2026

## 概述

Calico 支持多种网络模式，以适应不同的基础设施要求、性能需求和运维限制。本节将深入介绍每种网络模式，帮助你为环境选择并配置最佳模式。

## 网络模式概览

![Calico 的 IPIP、VXLAN 和 Direct/BGP 模式并排展示：来自 Node 1 上 Pod A 的数据包通过 tunl0 IPIP 隧道（+20 字节）、vxlan.calico VXLAN 隧道（+50 字节），或无封装的 BGP 对等 L3 路由器，到达 Node 2 上的 Pod B。](../../.gitbook/assets/en-networking-calico-03-networking-modes-7.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-calico-03-networking-modes-7.html)

## IPIP 模式

IP-in-IP (IPIP) 是 Calico 的默认封装模式。它将原始 IP 数据包封装在另一个 IP 数据包中，以进行跨子网通信。

### IPIP 数据包结构

```
Standard IP Packet (1500 bytes MTU):
┌──────────────────────────────────────────────────────────────────┐
│ Ethernet │    IP Header (20B)    │  TCP/UDP  │     Payload      │
│   (14B)  │ Src: 192.168.1.10     │   (20B)   │   (up to 1460B)  │
│          │ Dst: 192.168.2.10     │           │                   │
└──────────────────────────────────────────────────────────────────┘

IPIP Encapsulated Packet (1500 bytes outer MTU):
┌───────────────────────────────────────────────────────────────────────────────┐
│ Ethernet │  Outer IP (20B)   │  Inner IP (20B)   │ TCP/UDP │    Payload     │
│   (14B)  │ Src: 10.0.1.10    │ Src: 192.168.1.10 │  (20B)  │ (up to 1440B)  │
│          │ Dst: 10.0.1.11    │ Dst: 192.168.2.10 │         │                │
│          │ Proto: 4 (IPIP)   │                   │         │                │
└───────────────────────────────────────────────────────────────────────────────┘
                                ▲
                                │
                         20 bytes overhead
                         Effective MTU: 1480
```

### IPIP 模式选项

| 模式            | 描述                               | 使用场景                                   |
| --------------- | ----------------------------------------- | ------------------------------------------ |
| **Always**      | 所有 Pod 到 Pod 的流量都会被封装    | 云环境，设置简单           |
| **CrossSubnet** | 仅跨子网流量会被封装 | 混合环境，性能优化 |
| **Never**       | 禁用 IPIP（与 Direct 路由配合使用）   | 使用 BGP 的本地部署环境                       |

### IPIP CrossSubnet 模式

CrossSubnet 是一种优化方式，仅对跨越 L3 边界的流量进行封装：

![同一子网中的两个 Node 直接相互路由，无需封装；而进入另一个子网的流量仅在该跨子网跳转时使用 IPIP 封装。](../../../assets/diagrams/rendered/en-networking-calico-03-networking-modes-1.svg)

### IPIP IPPool 配置

```yaml
apiVersion: projectcalico.org/v3
kind: IPPool
metadata:
  name: default-ipv4-ippool
spec:
  cidr: 192.168.0.0/16
  blockSize: 26                    # /26 = 64 IPs per block
  ipipMode: Always                 # Options: Always, CrossSubnet, Never
  vxlanMode: Never
  natOutgoing: true
  nodeSelector: all()
---
# CrossSubnet mode for optimized performance
apiVersion: projectcalico.org/v3
kind: IPPool
metadata:
  name: crosssubnet-ippool
spec:
  cidr: 10.244.0.0/16
  blockSize: 26
  ipipMode: CrossSubnet
  vxlanMode: Never
  natOutgoing: true
  nodeSelector: all()
```

### IPIP 隧道接口

```bash
# View IPIP tunnel interface on a node
ip link show tunl0

# Expected output:
# tunl0@NONE: <NOARP,UP,LOWER_UP> mtu 1480 qdisc noqueue state UNKNOWN mode DEFAULT group default qlen 1000
#     link/ipip 0.0.0.0 brd 0.0.0.0

# View IPIP routes
ip route | grep tunl0

# Expected output:
# 192.168.2.0/26 via 10.0.1.11 dev tunl0 proto bird onlink
# 192.168.3.0/26 via 10.0.1.12 dev tunl0 proto bird onlink
```

### IPIP 数据包流图

![来自 Pod A 的数据包在 Node 1 上被路由至 tunl0 接口，经过 IPIP 封装后穿越物理网络到达 Node 2，解封装后交付给 Pod B。](../../../assets/diagrams/rendered/en-networking-calico-03-networking-modes-2.svg)

## VXLAN 模式

VXLAN（Virtual Extensible LAN）是一种行业标准的覆盖网络协议，可将 Layer 2 帧封装在 UDP 数据包中。

### VXLAN 数据包结构

```
VXLAN Encapsulated Packet:
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│ Outer    │ Outer IP (20B)   │  UDP (8B)  │ VXLAN  │ Inner    │ Inner IP │ TCP/ │ Pay- │
│ Ethernet │ Src: 10.0.1.10   │ Src: rand  │ Header │ Ethernet │  (20B)   │ UDP  │ load │
│  (14B)   │ Dst: 10.0.1.11   │ Dst: 4789  │  (8B)  │  (14B)   │          │(20B) │      │
└─────────────────────────────────────────────────────────────────────────────────────────┘
                                                      ▲
                                                      │
                                               50 bytes overhead
                                               Effective MTU: 1450
```

### VXLAN 组件

| 组件             | 描述                                      |
| --------------------- | ------------------------------------------------ |
| **VTEP**              | VXLAN Tunnel Endpoint - 封装/解封装点        |
| **VNI**               | VXLAN Network Identifier（Calico 使用固定 VNI） |
| **UDP Port**          | 4789（由 IANA 分配）                             |
| **Multicast/Unicast** | Calico 使用具有已知对等 VTEP 的单播        |

### VXLAN IPPool 配置

```yaml
apiVersion: projectcalico.org/v3
kind: IPPool
metadata:
  name: vxlan-ippool
spec:
  cidr: 10.244.0.0/16
  blockSize: 26
  ipipMode: Never
  vxlanMode: Always                # Options: Always, CrossSubnet, Never
  natOutgoing: true
  nodeSelector: all()
---
# VXLAN CrossSubnet mode
apiVersion: projectcalico.org/v3
kind: IPPool
metadata:
  name: vxlan-crosssubnet-ippool
spec:
  cidr: 10.245.0.0/16
  blockSize: 26
  ipipMode: Never
  vxlanMode: CrossSubnet
  natOutgoing: true
  nodeSelector: all()
```

### VXLAN 接口配置

```bash
# View VXLAN interface
ip link show vxlan.calico

# Expected output:
# vxlan.calico: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1450 qdisc noqueue state UNKNOWN mode DEFAULT group default
#     link/ether 66:5b:5c:5d:5e:5f brd ff:ff:ff:ff:ff:ff

# View VXLAN FDB (Forwarding Database)
bridge fdb show dev vxlan.calico

# Expected output:
# 66:a1:a2:a3:a4:a5 dst 10.0.1.11 self permanent
# 66:b1:b2:b3:b4:b5 dst 10.0.1.12 self permanent

# View VXLAN routes
ip route | grep vxlan

# Expected output:
# 10.244.1.0/26 via 10.244.1.0 dev vxlan.calico onlink
# 10.244.2.0/26 via 10.244.2.0 dev vxlan.calico onlink
```

### VXLAN 数据包流

![Pod A 的数据包由其所在 Node 的 VTEP 封装为 UDP/VXLAN 帧，穿越物理网络后由目标 VTEP 解封装，再到达 Pod B。](../../../assets/diagrams/rendered/en-networking-calico-03-networking-modes-3.svg)

## Direct/无封装模式

Direct 路由模式使用原生 IP 路由，无需任何封装，可提供尽可能高的性能。

### Direct 模式的要求

| 要求           | 描述                                    |
| --------------------- | ---------------------------------------------- |
| **L2 邻接**      | Node 必须位于同一 L2 网络中，或者       |
| **BGP 路由**       | 外部路由器必须通过 BGP 学习 Pod 路由 |
| **路由传播** | 物理网络必须能够路由 Pod CIDR          |

### Direct 模式拓扑

![每个机架中的 Node 通过 BGP 与其机架的 ToR 交换机对等，两个 ToR 交换机则与共享的 Spine 交换机对等，因此 Pod 路由无需任何覆盖网络即可原生传播。](../../../assets/diagrams/rendered/en-networking-calico-03-networking-modes-4.svg)

### Direct 模式 IPPool 配置

```yaml
apiVersion: projectcalico.org/v3
kind: IPPool
metadata:
  name: direct-routing-pool
spec:
  cidr: 192.168.0.0/16
  blockSize: 26
  ipipMode: Never                  # Disable IPIP
  vxlanMode: Never                 # Disable VXLAN
  natOutgoing: true
  nodeSelector: all()
```

### Direct 模式的 BGP 配置

```yaml
# Global BGP configuration
apiVersion: projectcalico.org/v3
kind: BGPConfiguration
metadata:
  name: default
spec:
  logSeverityScreen: Info
  nodeToNodeMeshEnabled: true      # Full mesh for small clusters
  asNumber: 64512
---
# Peer with ToR switches
apiVersion: projectcalico.org/v3
kind: BGPPeer
metadata:
  name: rack1-tor
spec:
  peerIP: 10.0.1.1
  asNumber: 65001
  nodeSelector: rack == 'rack1'
---
apiVersion: projectcalico.org/v3
kind: BGPPeer
metadata:
  name: rack2-tor
spec:
  peerIP: 10.0.2.1
  asNumber: 65001
  nodeSelector: rack == 'rack2'
```

### Direct 模式路由

```bash
# View routes on a node in direct mode
ip route

# Expected output (no tunnel interfaces):
# default via 10.0.1.1 dev eth0
# 10.0.1.0/24 dev eth0 proto kernel scope link src 10.0.1.10
# 192.168.1.0/26 dev cali123456 scope link           # Local pods
# 192.168.1.64/26 via 10.0.1.11 dev eth0 proto bird  # Node 2 pods
# 192.168.2.0/26 via 10.0.1.1 dev eth0 proto bird    # Rack 2 via ToR
# 192.168.2.64/26 via 10.0.1.1 dev eth0 proto bird   # Rack 2 via ToR
```

## 模式比较

### IPIP 对比 VXLAN 对比 Direct

| 特性               | IPIP                | VXLAN                | Direct       |
| --------------------- | ------------------- | -------------------- | ------------ |
| **协议**          | IP 协议 4       | UDP 端口 4789        | 原生 IP    |
| **开销**          | 20 字节            | 50 字节             | 0 字节      |
| **MTU**               | 1480                | 1450                 | 1500         |
| **防火墙兼容性** | 可能需要 IP 协议 4 | UDP 可直通     | 原生       |
| **硬件卸载**  | 有限             | 支持更好       | 完整支持 |
| **L2 要求**    | 否                  | 否                   | 是（或 BGP） |
| **组播**         | 不需要          | 不需要（单播） | 不需要   |
| **性能**       | 良好                | 良好                 | 最佳         |
| **复杂度**        | 低                 | 低                  | 中等       |

### 性能基准测试比较

```
Test Environment:
- Nodes: 3x c5.xlarge (AWS)
- Network: 10 Gbps
- Tool: iperf3 TCP, 60 second test

Results (TCP throughput, single stream):

┌─────────────────────────────────────────────────────────────┐
│                    Throughput (Gbps)                        │
├─────────────────────────────────────────────────────────────┤
│ Direct Mode      ████████████████████████████████  9.41     │
│ IPIP Mode        ███████████████████████████████   9.12     │
│ VXLAN Mode       ██████████████████████████████    8.89     │
└─────────────────────────────────────────────────────────────┘

Latency (microseconds, p99):

┌─────────────────────────────────────────────────────────────┐
│                    Latency (μs)                             │
├─────────────────────────────────────────────────────────────┤
│ Direct Mode      ████                              45       │
│ IPIP Mode        █████                             52       │
│ VXLAN Mode       ██████                            61       │
└─────────────────────────────────────────────────────────────┘

CPU Usage (% per Gbps):

┌─────────────────────────────────────────────────────────────┐
│                    CPU (% per Gbps)                         │
├─────────────────────────────────────────────────────────────┤
│ Direct Mode      ███                               2.1      │
│ IPIP Mode        ████                              2.8      │
│ VXLAN Mode       █████                             3.4      │
└─────────────────────────────────────────────────────────────┘
```

### 数据包流比较

![三条通道分别追踪 Direct、IPIP 和 VXLAN 模式下相同的 Pod A 到 Pod B 跳转，显示它们之间仅在物理网络边界的封装步骤不同。](../../../assets/diagrams/rendered/en-networking-calico-03-networking-modes-5.svg)

## 云服务提供商兼容性

| 提供商        | IPIP | VXLAN | Direct           | 推荐方案               |
| --------------- | ---- | ----- | ---------------- | ------------------------- |
| **AWS EC2**     | 是  | 是   | 使用 VPC 路由 | VXLAN 或 IPIP CrossSubnet |
| **AWS EKS**     | 是  | 是   | 有限          | VXLAN（默认）           |
| **Azure**       | 是  | 是   | 使用 UDR         | VXLAN                     |
| **GCP**         | 是  | 是   | 使用 VPC 路由  | IPIP CrossSubnet          |
| **本地部署** | 是  | 是   | 是（BGP）        | Direct（使用 BGP）         |
| **裸金属**  | 是  | 是   | 是              | Direct（使用 BGP）         |
| **OpenStack**   | 是  | 是   | 是              | 取决于 neutron 配置 |

### AWS 专用配置

```yaml
# For AWS EC2/EKS with VXLAN
apiVersion: operator.tigera.io/v1
kind: Installation
metadata:
  name: default
spec:
  kubernetesProvider: EKS
  cni:
    type: Calico
  calicoNetwork:
    bgp: Disabled                  # AWS VPC doesn't support BGP
    ipPools:
    - cidr: 10.244.0.0/16
      encapsulation: VXLAN
      natOutgoing: Enabled
      nodeSelector: all()
```

### 使用 BGP 的本地部署环境

```yaml
# For on-premises with BGP peering
apiVersion: operator.tigera.io/v1
kind: Installation
metadata:
  name: default
spec:
  kubernetesProvider: ""
  cni:
    type: Calico
  calicoNetwork:
    bgp: Enabled
    ipPools:
    - cidr: 192.168.0.0/16
      encapsulation: None          # Direct routing
      natOutgoing: Enabled
      nodeSelector: all()
```

## 模式迁移指南

### 从 IPIP 迁移到 VXLAN

```bash
# Step 1: Create new VXLAN IPPool
cat <<EOF | kubectl apply -f -
apiVersion: projectcalico.org/v3
kind: IPPool
metadata:
  name: vxlan-pool
spec:
  cidr: 10.245.0.0/16
  blockSize: 26
  ipipMode: Never
  vxlanMode: Always
  natOutgoing: true
  nodeSelector: all()
EOF

# Step 2: Disable old IPIP pool (prevents new allocations)
calicoctl patch ippool default-ipv4-ippool -p '{"spec": {"disabled": true}}'

# Step 3: Rolling restart workloads to get new IPs
kubectl rollout restart deployment -n <namespace>

# Step 4: After all pods migrated, delete old pool
calicoctl delete ippool default-ipv4-ippool
```

### 从 Overlay 迁移到 Direct

```yaml
# Step 1: Ensure BGP is configured
apiVersion: projectcalico.org/v3
kind: BGPConfiguration
metadata:
  name: default
spec:
  nodeToNodeMeshEnabled: true
  asNumber: 64512
---
# Step 2: Configure BGP peers (for external routing)
apiVersion: projectcalico.org/v3
kind: BGPPeer
metadata:
  name: tor-peer
spec:
  peerIP: 10.0.0.1
  asNumber: 65001
---
# Step 3: Create direct mode IPPool
apiVersion: projectcalico.org/v3
kind: IPPool
metadata:
  name: direct-pool
spec:
  cidr: 192.168.0.0/16
  ipipMode: Never
  vxlanMode: Never
  natOutgoing: true
```

## MTU 优化指南

### 按模式计算 MTU

| 模式             | 基础 MTU | 开销 | 有效 MTU | 配置        |
| ---------------- | -------- | -------- | ------------- | -------------------- |
| Direct           | 1500     | 0        | 1500          | 无需更改     |
| IPIP             | 1500     | 20       | 1480          | `ipipMTU: 1480`      |
| VXLAN            | 1500     | 50       | 1450          | `vxlanMTU: 1450`     |
| WireGuard        | 1500     | 60       | 1440          | `wireguardMTU: 1440` |
| IPIP + WireGuard | 1500     | 80       | 1420          | 合并开销    |

### MTU 配置

```yaml
apiVersion: projectcalico.org/v3
kind: FelixConfiguration
metadata:
  name: default
spec:
  # Auto-detect MTU (recommended)
  mtuIfacePattern: ^((en|wl|eth).*|bond[0-9]+)$

  # Or set explicit values
  ipipMTU: 1480
  vxlanMTU: 1450
  wireguardMTU: 1440
```

### Jumbo Frames 配置

```yaml
# For networks supporting jumbo frames (MTU 9000)
apiVersion: projectcalico.org/v3
kind: FelixConfiguration
metadata:
  name: default
spec:
  ipipMTU: 8980              # 9000 - 20 (IPIP overhead)
  vxlanMTU: 8950             # 9000 - 50 (VXLAN overhead)
```

### 验证 MTU

```bash
# Check interface MTU
ip link show | grep mtu

# Test path MTU
ping -M do -s 1472 <destination-pod-ip>   # For 1500 MTU
ping -M do -s 1452 <destination-pod-ip>   # For IPIP (1480 MTU)
ping -M do -s 1422 <destination-pod-ip>   # For VXLAN (1450 MTU)

# Check for MTU issues in tcpdump
tcpdump -i eth0 'icmp[icmptype] == 3 and icmp[icmpcode] == 4'
```

## 决策流程图

![一棵决策树从云环境与本地部署环境的分支开始，经过服务提供商、VPC 路由以及 BGP/L2 邻接性问题，最终确定 VXLAN、IPIP CrossSubnet 或 Direct 模式；其中本地部署环境的 BGP 路径被突出显示为性能最高的路线。](../../../assets/diagrams/rendered/en-networking-calico-03-networking-modes-6.svg)

## 总结

选择正确的网络模式对于实现最佳 Calico 性能至关重要：

1. **IPIP 模式**：云环境的默认选择，配置简单
2. **VXLAN 模式**：防火墙兼容性更好，是标准覆盖网络协议
3. **Direct 模式**：使用 BGP 基础设施的本地部署环境可获得最高性能

关键考虑因素：

* **云部署**：使用 VXLAN 或 IPIP CrossSubnet
* **使用 BGP 的本地部署环境**：使用 Direct 模式以获得最佳性能
* **混合环境**：IPIP 或 VXLAN CrossSubnet 可提供良好平衡
* **性能关键型场景**：使用正确 BGP 配置的 Direct 模式

[上一节：第 2 部分 - Calico 架构深入解析](02-architecture.md)

[返回 Calico 概览](./README.md)

## 测验

要检验你在本章中学到的内容，请尝试 [网络模式测验](../../quizzes/networking/calico/03-networking-modes-quiz.md)。
