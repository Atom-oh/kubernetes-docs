# 第 4 部分：BGP 深入剖析

> **支持版本**：Calico v3.29+ / Kubernetes 1.28+ **最后更新**：February 23, 2026

## 简介

Border Gateway Protocol (BGP) 是为互联网提供路由支持的路由协议，Calico 利用它为 Kubernetes 集群提供高可扩展性、基于标准的网络。与封装流量的 overlay 网络不同，Calico 基于 BGP 的网络支持原生 IP 路由，可提供卓越性能并与现有网络基础设施无缝集成。

本深入剖析涵盖 BGP 基础知识、Calico 的 BGP 架构选项、配置资源，以及适用于企业环境的高级部署模式。

***

## BGP 基础知识

### 什么是 BGP？

BGP (Border Gateway Protocol) 是一种路径向量路由协议，旨在于自治系统之间交换路由信息。在 Calico 中，BGP 会在集群节点间分发 Pod IP 路由，并可选择性地分发至外部网络基础设施。

### BGP 核心概念

| 概念                    | 说明                                                                 |
| ----------------------- | -------------------------------------------------------------------- |
| **Autonomous System (AS)** | 处于单一管理域下的一组 IP 网络                                        |
| **AS Number (ASN)**        | AS 的唯一标识符（16 位：1-65534，32 位：1-4294967294）               |
| **iBGP**                   | 内部 BGP - 同一 AS 中路由器之间的会话                                |
| **eBGP**                   | 外部 BGP - 不同 AS 中路由器之间的会话                                |
| **NLRI**                   | Network Layer Reachability Information - 正在通告的路由              |
| **BGP Speaker**            | 参与 BGP 的路由器或软件                                              |

### 私有 AS Number 范围

对于组织内部使用，IANA 保留了以下私有 ASN 范围：

```
16-bit Private ASN Range: 64512 - 65534
32-bit Private ASN Range: 4200000000 - 4294967294
```

Calico 通常对集群内部 BGP 使用 `64512-65534` 范围内的 ASN。

### BGP 路由选择流程

当 BGP Speaker 收到前往同一目的地的多条路由时，会依据以下条件（按顺序）选择最佳路由：

```mermaid
flowchart TD
    A[Receive Multiple Routes] --> B{Highest Weight?}
    B -->|Tie| C{Highest LOCAL_PREF?}
    C -->|Tie| D{Locally Originated?}
    D -->|Tie| E{Shortest AS_PATH?}
    E -->|Tie| F{Lowest Origin Type?}
    F -->|Tie| G{Lowest MED?}
    G -->|Tie| H{eBGP over iBGP?}
    H -->|Tie| I{Lowest IGP Metric?}
    I -->|Tie| J{Oldest Route?}
    J -->|Tie| K{Lowest Router ID}
    K --> L[Select Best Route]
```

### iBGP 与 eBGP 的行为差异

| 属性                    | iBGP                               | eBGP                                   |
| ----------------------- | ---------------------------------- | -------------------------------------- |
| AS\_PATH 修改          | 不修改                             | 添加本地 AS                            |
| 下一跳                  | 默认不变                           | 更改为对等地址                         |
| 默认 TTL                | 255                                | 1（非相邻节点需要 multihop）           |
| 路由通告                | 仅通告给 eBGP 对等体（split-horizon） | 通告给所有对等体                     |
| 管理距离                | 200                                | 20                                     |

***

## Calico BGP 架构

![Calico BGP Topologies](../../.gitbook/assets/calico_bgp_topology.png)

### BIRD：Calico 的 BGP 实现

Calico 使用 BIRD (BIRD Internet Routing Daemon) 作为其 BGP 实现。BIRD 在每个节点上的 `calico-node` DaemonSet 中运行。

```mermaid
graph TB
    subgraph "Calico Node"
        FV[Felix] --> DT[Dataplane<br/>iptables/eBPF]
        BIRD[BIRD BGP] --> RT[Routing Table]
        CONFD[confd] --> BIRD
        API[Calico API] --> CONFD
    end

    BIRD <--> EXT[External Router]
    BIRD <--> OTHER[Other Calico Nodes]
```

### BGP 拓扑选项

Calico 支持两种主要的 BGP 拓扑：

1. **节点到节点网状拓扑（Full Mesh）** - 默认配置
2. **Route Reflectors** - 推荐用于较大的集群

***

## Full-Mesh 拓扑

### Full-Mesh 的工作方式

在默认的 Full-Mesh 配置中，每个 Calico 节点都会与集群中的其他每个节点建立 BGP 对等会话。

```mermaid
graph TB
    subgraph "Full-Mesh BGP (5 Nodes)"
        N1[Node 1<br/>AS 64512] <--> N2[Node 2<br/>AS 64512]
        N1 <--> N3[Node 3<br/>AS 64512]
        N1 <--> N4[Node 4<br/>AS 64512]
        N1 <--> N5[Node 5<br/>AS 64512]
        N2 <--> N3
        N2 <--> N4
        N2 <--> N5
        N3 <--> N4
        N3 <--> N5
        N4 <--> N5
    end
```

### 会话数量公式

Full-Mesh 拓扑中的 BGP 会话数量呈二次增长：

```
Sessions = N × (N - 1) / 2

Examples:
- 10 nodes:   10 × 9 / 2 = 45 sessions
- 50 nodes:   50 × 49 / 2 = 1,225 sessions
- 100 nodes:  100 × 99 / 2 = 4,950 sessions
- 500 nodes:  500 × 499 / 2 = 124,750 sessions
```

### Full-Mesh 的扩展性限制

| 集群规模        | BGP 会话数    | 每个节点的内存 | CPU 影响 | 建议           |
| --------------- | ------------ | -------------- | -------- | -------------- |
| < 50 个节点     | < 1,225      | \~50 MB        | 极小     | 可使用 Full-mesh |
| 50-100 个节点   | 1,225-4,950  | \~100 MB       | 低       | 考虑使用 RR    |
| 100-200 个节点  | 4,950-19,900 | \~200 MB       | 中等     | 使用 RR        |
| > 200 个节点    | > 19,900     | > 400 MB        | 高       | 必须使用 RR    |

### 启用/禁用节点到节点网状拓扑

检查当前状态：

```bash
calicoctl get bgpconfiguration default -o yaml
```

禁用节点到节点网状拓扑（使用 Route Reflectors 时）：

```yaml
apiVersion: projectcalico.org/v3
kind: BGPConfiguration
metadata:
  name: default
spec:
  nodeToNodeMeshEnabled: false
  asNumber: 64512
```

***

## Route Reflector 拓扑

### Route Reflector 概念

Route Reflectors (RRs) 通过允许一部分节点向其他节点反射路由来解决 iBGP 的扩展性问题。这消除了对 Full Mesh 的需求。

```mermaid
graph TB
    subgraph "Route Reflector Topology"
        subgraph "Route Reflectors"
            RR1[RR Node 1<br/>Cluster ID: 1.0.0.1]
            RR2[RR Node 2<br/>Cluster ID: 1.0.0.1]
        end

        subgraph "Client Nodes"
            C1[Client 1]
            C2[Client 2]
            C3[Client 3]
            C4[Client 4]
            C5[Client 5]
            C6[Client 6]
        end

        RR1 <--> RR2

        C1 --> RR1
        C2 --> RR1
        C3 --> RR1
        C1 --> RR2
        C2 --> RR2
        C3 --> RR2

        C4 --> RR1
        C5 --> RR1
        C6 --> RR1
        C4 --> RR2
        C5 --> RR2
        C6 --> RR2
    end
```

### Route Reflector 的关键属性

| 属性                 | 说明                                                          |
| -------------------- | ------------------------------------------------------------- |
| **Cluster ID**       | 标识为同一批客户端提供服务的一组 RR                           |
| **Originator ID**    | 防止路由环路（设置为发起方的 router ID）                      |
| **Route Reflection** | RR 将从客户端学习到的路由重新通告给其他客户端                 |

### 使用 Route Reflectors 时的会话数量

使用 2 个 Route Reflectors 和 N 个客户端节点：

```
Sessions = 2 × N + 1 (RR-to-RR peering)

Examples:
- 100 nodes: 2 × 100 + 1 = 201 sessions (vs 4,950 in full-mesh)
- 500 nodes: 2 × 500 + 1 = 1,001 sessions (vs 124,750 in full-mesh)
```

### 配置 Route Reflector 节点

**第 1 步：为指定为 Route Reflectors 的节点添加标签**

```bash
kubectl label node rr-node-1 calico-route-reflector=true
kubectl label node rr-node-2 calico-route-reflector=true
```

**第 2 步：配置 Route Reflector Cluster ID**

```yaml
apiVersion: projectcalico.org/v3
kind: Node
metadata:
  name: rr-node-1
  labels:
    calico-route-reflector: "true"
spec:
  bgp:
    ipv4Address: 10.0.1.10/24
    routeReflectorClusterID: 1.0.0.1
---
apiVersion: projectcalico.org/v3
kind: Node
metadata:
  name: rr-node-2
  labels:
    calico-route-reflector: "true"
spec:
  bgp:
    ipv4Address: 10.0.1.11/24
    routeReflectorClusterID: 1.0.0.1
```

**第 3 步：禁用节点到节点网状拓扑**

```yaml
apiVersion: projectcalico.org/v3
kind: BGPConfiguration
metadata:
  name: default
spec:
  nodeToNodeMeshEnabled: false
  asNumber: 64512
```

**第 4 步：配置与 Route Reflectors 的 BGP 对等**

```yaml
# Peering from non-RR nodes to RR nodes
apiVersion: projectcalico.org/v3
kind: BGPPeer
metadata:
  name: peer-to-route-reflectors
spec:
  nodeSelector: "!has(calico-route-reflector)"
  peerSelector: has(calico-route-reflector)
---
# Peering between RR nodes
apiVersion: projectcalico.org/v3
kind: BGPPeer
metadata:
  name: route-reflector-mesh
spec:
  nodeSelector: has(calico-route-reflector)
  peerSelector: has(calico-route-reflector)
```

### Route Reflector 冗余模式

**模式 1：双 Route Reflectors（小型/中型集群）**

```mermaid
graph TB
    subgraph "Availability Zone 1"
        RR1[Route Reflector 1]
        N1[Node 1]
        N2[Node 2]
        N3[Node 3]
    end

    subgraph "Availability Zone 2"
        RR2[Route Reflector 2]
        N4[Node 4]
        N5[Node 5]
        N6[Node 6]
    end

    RR1 <--> RR2
    N1 & N2 & N3 --> RR1
    N1 & N2 & N3 --> RR2
    N4 & N5 & N6 --> RR1
    N4 & N5 & N6 --> RR2
```

**模式 2：分层 Route Reflectors（大型集群）**

```mermaid
graph TB
    subgraph "Tier 1 - Global RRs"
        GRR1[Global RR 1]
        GRR2[Global RR 2]
    end

    subgraph "Tier 2 - Rack RRs"
        RRR1[Rack 1 RR]
        RRR2[Rack 2 RR]
        RRR3[Rack 3 RR]
    end

    subgraph "Rack 1 Nodes"
        R1N1[Node]
        R1N2[Node]
    end

    subgraph "Rack 2 Nodes"
        R2N1[Node]
        R2N2[Node]
    end

    subgraph "Rack 3 Nodes"
        R3N1[Node]
        R3N2[Node]
    end

    GRR1 <--> GRR2
    GRR1 <--> RRR1 & RRR2 & RRR3
    GRR2 <--> RRR1 & RRR2 & RRR3

    R1N1 & R1N2 --> RRR1
    R2N1 & R2N2 --> RRR2
    R3N1 & R3N2 --> RRR3
```

***

## BGPPeer 资源

`BGPPeer` 资源定义 Calico 节点与外部 BGP Speaker 之间的 BGP 对等关系。

### BGPPeer 范围类型

| 类型                  | 说明                 | 使用场景               |
| --------------------- | -------------------- | ---------------------- |
| **全局**              | 应用于所有节点       | 外部路由器对等         |
| **节点特定**          | 使用 nodeSelector    | 机架本地对等           |
| **每节点**            | 指定确切节点         | 特殊配置               |

### 全局 BGPPeer 示例

将所有节点与外部 ToR 交换机建立对等：

```yaml
apiVersion: projectcalico.org/v3
kind: BGPPeer
metadata:
  name: peer-to-tor-switches
spec:
  peerIP: 10.0.0.1
  asNumber: 65001
  # No nodeSelector means all nodes peer with this address
```

### 节点特定 BGPPeer 示例

将特定机架中的节点与其本地 ToR 交换机建立对等：

```yaml
apiVersion: projectcalico.org/v3
kind: BGPPeer
metadata:
  name: rack1-tor-peer
spec:
  nodeSelector: rack == 'rack1'
  peerIP: 10.0.1.1
  asNumber: 65001
---
apiVersion: projectcalico.org/v3
kind: BGPPeer
metadata:
  name: rack2-tor-peer
spec:
  nodeSelector: rack == 'rack2'
  peerIP: 10.0.2.1
  asNumber: 65002
```

### 带有 peerSelector 的 BGPPeer

使用 `peerSelector` 动态选择 Calico 节点作为对等体：

```yaml
apiVersion: projectcalico.org/v3
kind: BGPPeer
metadata:
  name: client-to-rr-peering
spec:
  nodeSelector: "!has(route-reflector)"
  peerSelector: has(route-reflector)
```

### 高级 BGPPeer 配置

```yaml
apiVersion: projectcalico.org/v3
kind: BGPPeer
metadata:
  name: advanced-peer
spec:
  node: specific-node-name
  peerIP: 192.168.1.1
  asNumber: 65100

  # Authentication
  password:
    secretKeyRef:
      name: bgp-secrets
      key: peer-password

  # Timers (seconds)
  keepAliveTime: 30
  holdTime: 90

  # Source address for BGP session
  sourceAddress: 10.0.0.5

  # Maximum number of hops for eBGP multihop
  numAllowedLocalASNumbers: 2

  # TTL security (GTSM)
  ttlSecurity: 1

  # Filters
  filters:
    - action: Accept
      matchOperator: In
      cidr: 10.0.0.0/8
```

***

## BGPConfiguration 资源

`BGPConfiguration` 资源定义集群范围的 BGP 设置。

### 基本 BGPConfiguration

```yaml
apiVersion: projectcalico.org/v3
kind: BGPConfiguration
metadata:
  name: default
spec:
  # Cluster AS number
  asNumber: 64512

  # Node-to-node mesh (disable for Route Reflectors)
  nodeToNodeMeshEnabled: false

  # Log level for BIRD
  logSeverityScreen: Info
```

### Service IP 通告

Calico 可通过 BGP 通告 Kubernetes Service IP，使外部客户端能够直接访问服务。

```yaml
apiVersion: projectcalico.org/v3
kind: BGPConfiguration
metadata:
  name: default
spec:
  asNumber: 64512
  nodeToNodeMeshEnabled: false

  # Advertise Service ClusterIPs
  serviceClusterIPs:
    - cidr: 10.96.0.0/12

  # Advertise Service ExternalIPs
  serviceExternalIPs:
    - cidr: 203.0.113.0/24

  # Advertise Service LoadBalancerIPs
  serviceLoadBalancerIPs:
    - cidr: 198.51.100.0/24
```

### BGP Communities 配置

BGP communities 可让您为外部路由器上的基于策略路由标记路由：

```yaml
apiVersion: projectcalico.org/v3
kind: BGPConfiguration
metadata:
  name: default
spec:
  asNumber: 64512

  # Community tagging for pod networks
  prefixAdvertisements:
    - cidr: 10.244.0.0/16
      communities:
        - "64512:100"  # Standard community
        - "64512:200"
    - cidr: 10.96.0.0/12
      communities:
        - "64512:300"  # Service IPs community

  # Named communities (referenced in other configs)
  communities:
    - name: pod-networks
      value: "64512:100"
    - name: service-networks
      value: "64512:300"
    - name: no-export
      value: "65535:65281"  # Well-known NO_EXPORT
```

### 节点特定 AS Number

对于复杂拓扑，您可为每个节点分配不同的 AS number：

```yaml
apiVersion: projectcalico.org/v3
kind: Node
metadata:
  name: border-node-1
spec:
  bgp:
    ipv4Address: 10.0.1.10/24
    asNumber: 65001  # Override cluster default
```

***

## Service IP 通告

### 通告类型

| 类型                 | 说明                  | 使用场景               |
| -------------------- | --------------------- | ---------------------- |
| **ClusterIP**        | 内部 Service IP       | 内部负载均衡           |
| **ExternalIP**       | 用户分配的外部 IP     | 直接外部访问           |
| **LoadBalancerIP**   | 云提供商分配          | 云集成                 |

### ExternalIP 通告示例

```yaml
# BGPConfiguration for ExternalIP advertisement
apiVersion: projectcalico.org/v3
kind: BGPConfiguration
metadata:
  name: default
spec:
  serviceExternalIPs:
    - cidr: 203.0.113.0/24

---
# Service with ExternalIP
apiVersion: v1
kind: Service
metadata:
  name: my-external-service
spec:
  type: ClusterIP
  externalIPs:
    - 203.0.113.10
  selector:
    app: my-app
  ports:
    - port: 80
      targetPort: 8080
```

### LoadBalancer IP 通告

对于未集成云提供商的 bare-metal 集群：

```yaml
apiVersion: projectcalico.org/v3
kind: BGPConfiguration
metadata:
  name: default
spec:
  serviceLoadBalancerIPs:
    - cidr: 198.51.100.0/24

---
apiVersion: v1
kind: Service
metadata:
  name: my-lb-service
  annotations:
    metallb.universe.tf/loadBalancerIPs: 198.51.100.50
spec:
  type: LoadBalancer
  selector:
    app: my-app
  ports:
    - port: 443
      targetPort: 8443
```

### 选择性 Service 通告

使用 annotations 控制要通告哪些服务：

```yaml
apiVersion: v1
kind: Service
metadata:
  name: internal-only-service
  annotations:
    # Prevent BGP advertisement
    projectcalico.org/bgp-advertise: "false"
spec:
  type: LoadBalancer
  ...
```

***

## 物理网络集成

### ToR 交换机配置示例

**Cisco NX-OS 配置：**

```
! Configure BGP
router bgp 65001
  router-id 10.0.1.1

  ! Peer with Kubernetes nodes in rack
  neighbor 10.0.1.0/24 remote-as 64512

  address-family ipv4 unicast
    ! Accept pod network routes
    network 10.244.0.0/16
    ! Redistribute connected for node networks
    redistribute connected route-map KUBERNETES-NODES

    ! Route map for prefix filtering
    neighbor 10.0.1.0/24 route-map ACCEPT-K8S-ROUTES in
    neighbor 10.0.1.0/24 route-map DENY-ALL out

! Route map definitions
route-map ACCEPT-K8S-ROUTES permit 10
  match ip address prefix-list K8S-POD-NETS

ip prefix-list K8S-POD-NETS seq 10 permit 10.244.0.0/16 le 26
ip prefix-list K8S-POD-NETS seq 20 permit 10.96.0.0/12 le 32
```

**Arista EOS 配置：**

```
! Configure BGP
router bgp 65001
  router-id 10.0.1.1

  ! Peer group for Kubernetes nodes
  neighbor K8S-NODES peer group
  neighbor K8S-NODES remote-as 64512
  neighbor K8S-NODES maximum-routes 10000
  neighbor K8S-NODES password 7 <encrypted>

  ! Dynamic neighbors from subnet
  bgp listen range 10.0.1.0/24 peer-group K8S-NODES

  address-family ipv4
    neighbor K8S-NODES activate
    neighbor K8S-NODES prefix-list K8S-PODS-IN in
    neighbor K8S-NODES prefix-list DENY-ALL out

! Prefix lists
ip prefix-list K8S-PODS-IN seq 10 permit 10.244.0.0/16 le 26
ip prefix-list K8S-PODS-IN seq 20 permit 10.96.0.0/12 le 32
ip prefix-list DENY-ALL seq 10 deny 0.0.0.0/0 le 32
```

**Juniper Junos 配置：**

```
protocols {
    bgp {
        group K8S-NODES {
            type external;
            peer-as 64512;
            local-as 65001;

            multipath multiple-as;

            import K8S-IMPORT;
            export DENY-ALL;

            allow 10.0.1.0/24;

            authentication-key "$9$encrypted";
        }
    }
}

policy-options {
    prefix-list K8S-POD-NETS {
        10.244.0.0/16;
    }
    prefix-list K8S-SVC-NETS {
        10.96.0.0/12;
    }
    policy-statement K8S-IMPORT {
        term accept-pods {
            from {
                prefix-list K8S-POD-NETS;
                prefix-length-range /26-/26;
            }
            then accept;
        }
        term accept-services {
            from {
                prefix-list K8S-SVC-NETS;
            }
            then accept;
        }
        term reject-all {
            then reject;
        }
    }
    policy-statement DENY-ALL {
        then reject;
    }
}
```

### Spine-Leaf 架构集成

```mermaid
graph TB
    subgraph "Spine Layer (AS 65000)"
        S1[Spine 1<br/>10.0.0.1]
        S2[Spine 2<br/>10.0.0.2]
    end

    subgraph "Leaf Layer"
        subgraph "Rack 1 (AS 65001)"
            L1[Leaf 1<br/>10.0.1.1]
            K1[K8s Node 1<br/>AS 64512]
            K2[K8s Node 2<br/>AS 64512]
        end

        subgraph "Rack 2 (AS 65002)"
            L2[Leaf 2<br/>10.0.2.1]
            K3[K8s Node 3<br/>AS 64512]
            K4[K8s Node 4<br/>AS 64512]
        end

        subgraph "Rack 3 (AS 65003)"
            L3[Leaf 3<br/>10.0.3.1]
            K5[K8s Node 5<br/>AS 64512]
            K6[K8s Node 6<br/>AS 64512]
        end
    end

    S1 <--> L1 & L2 & L3
    S2 <--> L1 & L2 & L3

    K1 & K2 --> L1
    K3 & K4 --> L2
    K5 & K6 --> L3
```

适用于 spine-leaf 的 Calico 配置：

```yaml
# Disable node-to-node mesh
apiVersion: projectcalico.org/v3
kind: BGPConfiguration
metadata:
  name: default
spec:
  nodeToNodeMeshEnabled: false
  asNumber: 64512

---
# Peer nodes with their local leaf switch
apiVersion: projectcalico.org/v3
kind: BGPPeer
metadata:
  name: rack1-leaf-peer
spec:
  nodeSelector: topology.kubernetes.io/zone == 'rack1'
  peerIP: 10.0.1.1
  asNumber: 65001

---
apiVersion: projectcalico.org/v3
kind: BGPPeer
metadata:
  name: rack2-leaf-peer
spec:
  nodeSelector: topology.kubernetes.io/zone == 'rack2'
  peerIP: 10.0.2.1
  asNumber: 65002

---
apiVersion: projectcalico.org/v3
kind: BGPPeer
metadata:
  name: rack3-leaf-peer
spec:
  nodeSelector: topology.kubernetes.io/zone == 'rack3'
  peerIP: 10.0.3.1
  asNumber: 65003
```

***

## BGP Community 标记策略

### Community 设计模式

| Community     | 含义           | 操作                             |
| ------------- | -------------- | -------------------------------- |
| `64512:100`   | Pod 网络       | 接受，常规路由                   |
| `64512:200`   | Service IP     | 接受，可能应用特殊策略           |
| `64512:300`   | 基础设施       | 更高优先级路由                   |
| `65535:65281` | NO\_EXPORT     | 不向 AS 外部通告                 |
| `65535:65282` | NO\_ADVERTISE  | 不向任何对等体通告               |

### 基于 Community 的流量工程

```yaml
apiVersion: projectcalico.org/v3
kind: BGPConfiguration
metadata:
  name: default
spec:
  asNumber: 64512

  communities:
    - name: production
      value: "64512:100"
    - name: staging
      value: "64512:200"
    - name: local-only
      value: "65535:65281"  # NO_EXPORT

  prefixAdvertisements:
    # Production pod networks - advertise everywhere
    - cidr: 10.244.0.0/17
      communities:
        - production

    # Staging pod networks - keep local
    - cidr: 10.244.128.0/17
      communities:
        - staging
        - local-only

    # Service IPs
    - cidr: 10.96.0.0/12
      communities:
        - production
```

***

## BGP 安全性

### MD5 身份验证

使用 MD5 身份验证保护 BGP 会话：

```yaml
# Create secret for BGP password
apiVersion: v1
kind: Secret
metadata:
  name: bgp-auth
  namespace: kube-system
type: Opaque
stringData:
  bgp-password: "SuperSecretPassword123!"

---
# Reference in BGPPeer
apiVersion: projectcalico.org/v3
kind: BGPPeer
metadata:
  name: secure-peer
spec:
  peerIP: 10.0.1.1
  asNumber: 65001
  password:
    secretKeyRef:
      name: bgp-auth
      key: bgp-password
```

### 前缀过滤

限制接受/通告哪些前缀：

```yaml
apiVersion: projectcalico.org/v3
kind: BGPFilter
metadata:
  name: allow-pod-nets-only
spec:
  exportV4:
    - action: Accept
      matchOperator: In
      cidr: 10.244.0.0/16
      prefixLength: "24-28"
    - action: Reject
      matchOperator: In
      cidr: 0.0.0.0/0

  importV4:
    - action: Accept
      matchOperator: In
      cidr: 10.0.0.0/8
    - action: Reject
      matchOperator: In
      cidr: 0.0.0.0/0

---
apiVersion: projectcalico.org/v3
kind: BGPPeer
metadata:
  name: filtered-peer
spec:
  peerIP: 10.0.1.1
  asNumber: 65001
  filters:
    - allow-pod-nets-only
```

### GTSM（TTL 安全）

Generalized TTL Security Mechanism 可防止伪造的 BGP 数据包：

```yaml
apiVersion: projectcalico.org/v3
kind: BGPPeer
metadata:
  name: gtsm-enabled-peer
spec:
  peerIP: 10.0.1.1
  asNumber: 65001
  ttlSecurity: 1  # Expect TTL of 254 or higher
```

***

## 性能调优

### BGP 定时器配置

```yaml
apiVersion: projectcalico.org/v3
kind: BGPPeer
metadata:
  name: tuned-peer
spec:
  peerIP: 10.0.1.1
  asNumber: 65001

  # Keepalive interval (default: 60s)
  keepAliveTime: 20

  # Hold time (default: 180s, must be 3x keepalive)
  holdTime: 60
```

### 路由聚合

通过聚合 Pod CIDR 来减少通告的路由数量：

```yaml
apiVersion: projectcalico.org/v3
kind: BGPConfiguration
metadata:
  name: default
spec:
  asNumber: 64512

  # Aggregate individual /26 pod CIDRs into /16
  prefixAdvertisements:
    - cidr: 10.244.0.0/16
      communities:
        - "64512:100"
```

### 优雅重启

启用 BGP 优雅重启，以最大限度地减少 BIRD 重启期间的流量中断：

```yaml
apiVersion: projectcalico.org/v3
kind: BGPConfiguration
metadata:
  name: default
spec:
  asNumber: 64512

  # Enable graceful restart (BIRD default is enabled)
  # Stale route time in seconds
  nodeMeshMaxRestartTime: 120
```

***

## 调试 BGP

### birdcl 命令

从 calico-node Pod 访问 BIRD 命令行界面：

```bash
# Enter calico-node pod
kubectl exec -it -n kube-system calico-node-xxxxx -c calico-node -- /bin/sh

# Show BGP protocol status
birdcl -s /var/run/calico/bird.ctl show protocols all

# Show BGP neighbors
birdcl -s /var/run/calico/bird.ctl show protocols all bgp*

# Show routing table
birdcl -s /var/run/calico/bird.ctl show route

# Show routes to specific prefix
birdcl -s /var/run/calico/bird.ctl show route for 10.244.1.0/24

# Show route export to specific peer
birdcl -s /var/run/calico/bird.ctl show route export Mesh_10_0_1_11

# Show BGP neighbor details
birdcl -s /var/run/calico/bird.ctl show protocols all Mesh_10_0_1_11
```

### 常见 BGP 问题和解决方案

| 问题                     | 症状                          | 解决方案                                  |
| ------------------------ | ----------------------------- | ----------------------------------------- |
| 会话卡在 Active           | 未学习到路由                  | 检查防火墙（TCP 179）、AS number          |
| 路由未传播               | Pod 无法跨机架访问            | 验证节点到节点网状拓扑或 RR 配置          |
| 路由抖动                 | 间歇性连接问题                | 检查 BGP 定时器、网络稳定性               |
| 会话重置                 | 经常从 Established 变为 Active | 检查 MTU、MD5 密码                        |

### 诊断命令

```bash
# Check Calico node status
calicoctl node status

# List all BGP peers
calicoctl get bgppeers -o wide

# Check BGP configuration
calicoctl get bgpconfiguration default -o yaml

# View BIRD logs
kubectl logs -n kube-system calico-node-xxxxx -c calico-node | grep -i bird

# Check IP routes on node
ip route show | grep bird
```

***

## 多机架和多数据中心设计

### 使用 Route Reflectors 的多机架设计

```mermaid
graph TB
    subgraph "Datacenter"
        subgraph "Management Rack"
            RR1[Route Reflector 1<br/>Cluster ID: 1.0.0.1]
            RR2[Route Reflector 2<br/>Cluster ID: 1.0.0.1]
        end

        subgraph "Compute Rack 1"
            N1[Node 1]
            N2[Node 2]
            N3[Node 3]
        end

        subgraph "Compute Rack 2"
            N4[Node 4]
            N5[Node 5]
            N6[Node 6]
        end

        subgraph "Compute Rack 3"
            N7[Node 7]
            N8[Node 8]
            N9[Node 9]
        end
    end

    RR1 <--> RR2

    N1 & N2 & N3 --> RR1
    N1 & N2 & N3 --> RR2
    N4 & N5 & N6 --> RR1
    N4 & N5 & N6 --> RR2
    N7 & N8 & N9 --> RR1
    N7 & N8 & N9 --> RR2
```

### 多数据中心 BGP 设计

```mermaid
graph TB
    subgraph "DC1 (AS 64512)"
        subgraph "DC1 RRs"
            DC1_RR1[DC1 RR1]
            DC1_RR2[DC1 RR2]
        end
        DC1_N1[DC1 Nodes]

        DC1_RR1 <--> DC1_RR2
        DC1_N1 --> DC1_RR1 & DC1_RR2
    end

    subgraph "DC2 (AS 64513)"
        subgraph "DC2 RRs"
            DC2_RR1[DC2 RR1]
            DC2_RR2[DC2 RR2]
        end
        DC2_N1[DC2 Nodes]

        DC2_RR1 <--> DC2_RR2
        DC2_N1 --> DC2_RR1 & DC2_RR2
    end

    subgraph "WAN Edge (AS 65000)"
        WAN1[WAN Router 1]
        WAN2[WAN Router 2]
    end

    DC1_RR1 & DC1_RR2 <--> WAN1 & WAN2
    DC2_RR1 & DC2_RR2 <--> WAN1 & WAN2
```

多数据中心配置：

```yaml
# DC1 Configuration
apiVersion: projectcalico.org/v3
kind: BGPConfiguration
metadata:
  name: default
spec:
  asNumber: 64512
  nodeToNodeMeshEnabled: false

  communities:
    - name: dc1-origin
      value: "64512:1"

---
# Peer DC1 RRs with WAN routers
apiVersion: projectcalico.org/v3
kind: BGPPeer
metadata:
  name: dc1-to-wan
spec:
  nodeSelector: has(route-reflector)
  peerIP: 10.255.0.1  # WAN Router
  asNumber: 65000
```

***

## 最佳实践总结

### 设计建议

1. **集群规模 < 50 个节点**：可接受 Full-mesh
2. **集群规模为 50-200 个节点**：部署 2-3 个 Route Reflectors
3. **集群规模 > 200 个节点**：部署分层 Route Reflectors
4. **多机架**：使用机架感知的 Route Reflector 放置方式
5. **多数据中心**：每个 DC 使用独立 AS，DC 之间使用 eBGP

### 安全建议

1. 始终为外部对等体启用 MD5 身份验证
2. 实施前缀过滤以防止路由注入
3. 在支持的情况下使用 GTSM（TTL 安全）
4. 限制每个对等体接受的最大路由数
5. 监控 BGP 会话是否存在异常

### 运维建议

1. 为 BGP 拓扑一致地标记节点
2. 记录 AS number 分配方案
3. 实施 BGP 监控和告警
4. 定期测试故障转移场景
5. 保持各对等体之间的 BGP 定时器一致

***

## 参考资料

* [Calico BGP Documentation](https://docs.tigera.io/calico/latest/networking/configuring/bgp)
* [BIRD Internet Routing Daemon](https://bird.network.cz/)
* [RFC 4271 - BGP-4](https://tools.ietf.org/html/rfc4271)
* [RFC 4456 - BGP Route Reflection](https://tools.ietf.org/html/rfc4456)
* [RFC 5765 - GTSM for BGP](https://tools.ietf.org/html/rfc5082)
