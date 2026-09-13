# 第 2 部分：架构

> **支持的版本**：Calico v3.29+ / Kubernetes 1.28+ **最后更新**：February 23, 2026

## 概览

本节深入介绍 Calico 的架构。了解每个组件的工作方式及其交互对于在生产环境中有效部署、排障和优化 Calico 至关重要。

## 完整架构图

![展示 Kubernetes 控制平面、Calico 控制平面（API server、kube-controllers、Typha）以及一个 worker node；其中 Felix 编程本地数据平面，confd/BIRD 通过节点 BGP 网格分发路由。](../../.gitbook/assets/en-networking-calico-02-architecture-0.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-calico-02-architecture-0.html)

## Felix：Calico Agent

Felix 是运行在集群中每个节点上的主要 Calico Agent。它负责在主机上配置路由和 ACL（Access Control Lists，访问控制列表），以提供所需的连通性和网络策略执行。

### Felix 职责

![展示 Felix 的 Datastore Watcher 向其路由、ACL、接口和 IPAM 管理器分发信息，这些管理器进而配置节点的路由表、iptables 规则、IP 集合和网络接口。](../../../assets/diagrams/rendered/en-networking-calico-02-architecture-1.svg)

### 核心功能

1. **路由配置**：管理 Pod CIDR 块的路由
2. **ACL 执行**：为网络策略配置 iptables/nftables/eBPF 规则
3. **接口管理**：配置 workload endpoint 接口
4. **健康状态报告**：向 datastore 报告节点和 endpoint 的健康状态
5. **IPAM 协调**：管理本地 workload 的 IP 地址分配

### Felix 数据平面选项

Felix 支持多个数据平面后端：

| 数据平面     | 描述                 | 最适用场景                              |
| ------------ | -------------------- | --------------------------------------- |
| **iptables** | 传统 Linux 防火墙    | 兼容性、成熟部署                        |
| **nftables** | 现代 Linux 防火墙    | 较新的内核、更好的性能                  |
| **eBPF**     | 内核内可编程         | 极致性能、替代 kube-proxy               |

### FelixConfiguration Resource

```yaml
apiVersion: projectcalico.org/v3
kind: FelixConfiguration
metadata:
  name: default
spec:
  # Logging configuration
  logSeverityScreen: Info
  logSeverityFile: Warning
  logFilePath: /var/log/calico/felix.log

  # Data plane selection
  bpfEnabled: false                    # Set true for eBPF data plane
  bpfDataIfacePattern: ^((en|wl|eth).*|bond[0-9]+)$
  bpfConnectTimeLoadBalancingEnabled: true
  bpfExternalServiceMode: Tunnel

  # iptables configuration
  iptablesBackend: Auto               # Auto, Legacy, NFT
  iptablesRefreshInterval: 90s
  iptablesPostWriteCheckIntervalSecs: 1
  iptablesLockFilePath: /run/xtables.lock
  iptablesLockTimeoutSecs: 0
  iptablesLockProbeIntervalMillis: 50

  # Performance tuning
  ipipMTU: 1440
  vxlanMTU: 1410
  wireguardMTU: 1420

  # Health and metrics
  healthEnabled: true
  healthPort: 9099
  prometheusMetricsEnabled: true
  prometheusMetricsPort: 9091
  prometheusGoMetricsEnabled: true
  prometheusProcessMetricsEnabled: true

  # Policy configuration
  defaultEndpointToHostAction: Drop
  failsafeInboundHostPorts:
    - protocol: TCP
      port: 22
    - protocol: UDP
      port: 68
  failsafeOutboundHostPorts:
    - protocol: UDP
      port: 53
    - protocol: UDP
      port: 67

  # Interface configuration
  interfacePrefix: cali
  chainInsertMode: Insert

  # Reporting
  reportingIntervalSecs: 30
  reportingTTLSecs: 90
```

### Felix iptables 规则结构

Felix 将 iptables 规则组织为链，以实现高效处理：

```
                         ┌─────────────────────────────────────────┐
                         │              FORWARD Chain              │
                         └─────────────────┬───────────────────────┘
                                           │
                         ┌─────────────────▼───────────────────────┐
                         │          cali-FORWARD (Calico)          │
                         └─────────────────┬───────────────────────┘
                                           │
              ┌────────────────────────────┼────────────────────────────┐
              │                            │                            │
┌─────────────▼─────────────┐ ┌────────────▼────────────┐ ┌─────────────▼─────────────┐
│   cali-from-wl-dispatch   │ │   cali-to-wl-dispatch   │ │    cali-from-host-ep     │
│  (from workload traffic)  │ │  (to workload traffic)  │ │   (from host endpoints)   │
└─────────────┬─────────────┘ └────────────┬────────────┘ └─────────────┬─────────────┘
              │                            │                            │
┌─────────────▼─────────────┐ ┌────────────▼────────────┐ ┌─────────────▼─────────────┐
│    cali-fw-caliXXXXXX     │ │    cali-tw-caliXXXXXX   │ │    Per-endpoint policy    │
│    (per-endpoint rules)   │ │   (per-endpoint rules)  │ │          chains           │
└───────────────────────────┘ └─────────────────────────┘ └───────────────────────────┘
```

### Felix 数据流

![时序图展示 Felix 从 datastore 接收策略、endpoint 和 IP pool 更新，并将每项更新转换为 iptables 规则、路由表条目或网络接口配置。](../../../assets/diagrams/rendered/en-networking-calico-02-architecture-2.svg)

## BIRD：BGP 路由守护进程

BIRD（BIRD Internet Routing Daemon）是 Calico 用于在节点之间分发路由的 BGP 守护进程。

### Calico 架构中的 BIRD

![展示每个节点上的 BIRD 实例构成完整 iBGP 网格来交换 Pod 路由，然后通过 eBGP 与 top-of-rack switch 和 core router 建立对等连接，以向外部通告这些路由。](../../../assets/diagrams/rendered/en-networking-calico-02-architecture-3.svg)

### BGP 会话类型

| 会话类型              | 使用场景                    | 配置                   |
| --------------------- | --------------------------- | ---------------------- |
| **Node-to-Node Mesh** | 小型集群的默认选项          | 自动配置，全网状        |
| **Route Reflector**   | 大型集群（100+ 节点）       | 专用 RR 节点           |
| **External Peering**  | 本地部署集成                | 手动 BGP peer 配置     |

### BGP 配置示例

#### Node-to-Node Mesh（默认）

```yaml
apiVersion: projectcalico.org/v3
kind: BGPConfiguration
metadata:
  name: default
spec:
  logSeverityScreen: Info
  nodeToNodeMeshEnabled: true
  asNumber: 64512
```

#### Route Reflector 配置

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
# Configure route reflector nodes
apiVersion: projectcalico.org/v3
kind: Node
metadata:
  name: node-rr-1
  labels:
    route-reflector: "true"
spec:
  bgp:
    routeReflectorClusterID: 224.0.0.1
---
# Configure BGP peer to route reflector
apiVersion: projectcalico.org/v3
kind: BGPPeer
metadata:
  name: peer-to-rr
spec:
  nodeSelector: "!has(route-reflector)"
  peerSelector: route-reflector == "true"
```

#### 外部 BGP Peering

```yaml
apiVersion: projectcalico.org/v3
kind: BGPPeer
metadata:
  name: tor-switch-peer
spec:
  peerIP: 10.0.0.1
  asNumber: 65001
  nodeSelector: rack == 'rack-1'
  password:
    secretKeyRef:
      name: bgp-passwords
      key: tor-password
  sourceAddress: UseNodeIP
  keepOriginalNextHop: false
```

### 路由传播过程

![时序图展示新 Pod 的路由由 Felix 分配、添加到 BIRD 的本地路由表，并通过 BGP UPDATE 传播到 peer 节点，使其安装该路由并相应地路由 Felix。](../../../assets/diagrams/rendered/en-networking-calico-02-architecture-4.svg)

### BIRD 状态命令

```bash
# Access BIRD CLI on a Calico node
kubectl exec -n calico-system calico-node-xxxxx -c calico-node -- birdcl

# Show BGP protocol status
birdcl> show protocols
name     proto    table    state  since       info
kernel1  Kernel   master   up     2024-01-01
device1  Device   master   up     2024-01-01
direct1  Direct   master   up     2024-01-01
Mesh_10_0_1_10  BGP  master  up   2024-01-01  Established
Mesh_10_0_1_11  BGP  master  up   2024-01-01  Established

# Show BGP routes
birdcl> show route protocol Mesh_10_0_1_10
192.168.1.0/26     via 10.0.1.10 on eth0 [Mesh_10_0_1_10 2024-01-01] * (100/0) [i]
192.168.1.64/26    via 10.0.1.10 on eth0 [Mesh_10_0_1_10 2024-01-01] * (100/0) [i]

# Show route details
birdcl> show route 192.168.1.0/26 all
```

## confd：配置管理

confd 是一款轻量级配置管理工具，它监视 Calico datastore 并生成 BIRD 配置文件。

### confd 工作流

![展示 confd 的 watcher 对 Calico datastore 中的 BGP 配置、peer 和节点 Resource 作出响应，从模板渲染 bird.cfg 文件，并将其交给运行中的 BIRD 进程。](../../../assets/diagrams/rendered/en-networking-calico-02-architecture-5.svg)

### confd 模板处理

confd 使用 Go 模板生成 BIRD 配置：

```
# Template: /etc/calico/confd/templates/bird.cfg.template
# Output: /etc/calico/confd/config/bird.cfg

router id {{.NodeIP}};

protocol kernel {
    learn;
    persist;
    scan time 2;
    import all;
    export {{if .ExportKernel}}all{{else}}none{{end}};
}

protocol device {
    scan time 2;
}

{{range .BGPPeers}}
protocol bgp {{.Name}} {
    local as {{$.LocalAS}};
    neighbor {{.PeerIP}} as {{.PeerAS}};
    import all;
    export {{if .ExportFilter}}filter {{.ExportFilter}}{{else}}all{{end}};
    {{if .Password}}password "{{.Password}}";{{end}}
    graceful restart;
}
{{end}}
```

## Typha：扩缩容组件

Typha 是位于 Kubernetes API server 与 Felix Agent 之间的扇出代理。它通过缓存和分发 datastore 更新来降低 API server 的负载。

### 为什么使用 Typha？

![对比图展示在小型集群中，每个 Felix 直接监视 Kubernetes API；而在大型集群中，Typha Pod 将缓存的更新扇出分发给数百个 Felix Agent。](../../../assets/diagrams/rendered/en-networking-calico-02-architecture-6.svg)

### Typha 扩缩容计算

建议的 Typha 副本数量取决于集群规模：

```
Typha Replicas = max(3, ceil(Nodes / 200))

Examples:
- 50 nodes:   3 Typha replicas (minimum)
- 200 nodes:  3 Typha replicas
- 500 nodes:  3 Typha replicas
- 1000 nodes: 5 Typha replicas
- 2000 nodes: 10 Typha replicas
```

### Typha Deployment 配置

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: calico-typha
  namespace: calico-system
spec:
  replicas: 3
  revisionHistoryLimit: 2
  selector:
    matchLabels:
      k8s-app: calico-typha
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 1
  template:
    metadata:
      labels:
        k8s-app: calico-typha
    spec:
      nodeSelector:
        kubernetes.io/os: linux
      tolerations:
      - key: CriticalAddonsOnly
        operator: Exists
      priorityClassName: system-cluster-critical
      serviceAccountName: calico-typha
      containers:
      - name: calico-typha
        image: calico/typha:v3.29.0
        ports:
        - containerPort: 5473
          name: calico-typha
          protocol: TCP
        env:
        - name: TYPHA_LOGSEVERITYSCREEN
          value: "info"
        - name: TYPHA_LOGFILEPATH
          value: "none"
        - name: TYPHA_LOGSEVERITYSYS
          value: "none"
        - name: TYPHA_CONNECTIONREBALANCINGMODE
          value: "kubernetes"
        - name: TYPHA_DATASTORETYPE
          value: "kubernetes"
        - name: TYPHA_HEALTHENABLED
          value: "true"
        - name: TYPHA_PROMETHEUSMETRICSENABLED
          value: "true"
        - name: TYPHA_PROMETHEUSMETRICSPORT
          value: "9093"
        livenessProbe:
          httpGet:
            path: /liveness
            port: 9098
          periodSeconds: 30
          initialDelaySeconds: 30
        readinessProbe:
          httpGet:
            path: /readiness
            port: 9098
          periodSeconds: 10
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 1000m
            memory: 512Mi
---
apiVersion: v1
kind: Service
metadata:
  name: calico-typha
  namespace: calico-system
spec:
  ports:
  - port: 5473
    protocol: TCP
    targetPort: calico-typha
    name: calico-typha
  selector:
    k8s-app: calico-typha
```

### Typha 扇出架构

![架构图展示两个 API server watch 流输入两个 Typha Pod，每个 Pod 在本地缓存更新，并将其扇出分发给其节点组中约一百个 Felix Agent。](../../../assets/diagrams/rendered/en-networking-calico-02-architecture-7.svg)

## kube-controllers：Kubernetes 集成

calico-kube-controllers Pod 运行一组 Controller，用于将 Kubernetes Resource 与 Calico datastore 同步。

### Controller 概览

| Controller                      | 用途                                              |
| ------------------------------- | ------------------------------------------------- |
| **Node Controller**             | 将 Kubernetes 节点与 Calico 节点 Resource 同步    |
| **Policy Controller**           | 将 Kubernetes NetworkPolicy 与 Calico 策略同步    |
| **Namespace Controller**        | 同步 namespace 标签以进行 profile 管理           |
| **ServiceAccount Controller**   | 同步 service account 标签以支持 RBAC              |
| **WorkloadEndpoint Controller** | 清理过期的 workload endpoint                     |

### Controller 协调循环

![时序图展示 kube-controllers 反复列出 Kubernetes 和 Calico Resource、比较它们的差异，并在两者已同步时将变更写入 Calico datastore 或不执行任何操作。](../../../assets/diagrams/rendered/en-networking-calico-02-architecture-8.svg)

### kube-controllers 配置

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: calico-kube-controllers-config
  namespace: calico-system
data:
  config: |
    {
      "logSeverityScreen": "info",
      "healthEnabled": true,
      "prometheusPort": 9094,
      "controllers": {
        "node": {
          "hostEndpoint": {
            "autoCreate": "Disabled"
          },
          "syncLabels": "Enabled",
          "leakGracePeriod": "15m"
        },
        "policy": {
          "reconcilerPeriod": "5m"
        },
        "workloadEndpoint": {
          "reconcilerPeriod": "5m"
        },
        "namespace": {
          "reconcilerPeriod": "5m"
        },
        "serviceAccount": {
          "reconcilerPeriod": "5m"
        }
      }
    }
```

## Datastore 选项

Calico 支持两种用于存储其配置和状态的 datastore 后端。

### Kubernetes API Datastore（推荐）

![展示 Felix、Typha 和 kube-controllers 都通过 Kubernetes API server 读取和写入 Calico 状态，API server 本身持久化到 etcd，无需单独的 Calico etcd 集群。](../../../assets/diagrams/rendered/en-networking-calico-02-architecture-9.svg)

**优点：**

* 无需管理单独的 etcd 集群
* 使用 Kubernetes RBAC 进行访问控制
* 运维模型更简单
* 适用于任何 Kubernetes 发行版

### etcd Datastore（旧版）

![展示 Felix 和 Typha 直接从专用 Calico etcd 集群读取和写入，而 kube-controllers 将该集群与 Kubernetes API server 连接起来——这是旧版的解耦 datastore 选项。](../../../assets/diagrams/rendered/en-networking-calico-02-architecture-10.svg)

**优点：**

* 与 Kubernetes API server 解耦
* 可用于非 Kubernetes workload（VM、裸金属）
* 面向超大型集群的历史选项

### Datastore 对比

| 特性                       | Kubernetes API    | etcd               |
| -------------------------- | ----------------- | ------------------ |
| **运维复杂度**             | 较低              | 较高               |
| **可扩展性**               | 良好（配合 Typha）| 卓越               |
| **非 K8s Workload**        | 有限              | 完整支持           |
| **备份/恢复**              | 通过 K8s          | 单独的工具         |
| **访问控制**               | K8s RBAC          | etcd 认证          |
| **建议**                   | 默认选择          | 仅适用于特殊场景   |

## 组件交互时序

![时序图跟踪 NetworkPolicy 和 Pod 创建过程：从 Kubernetes API 经由 kube-controllers 和 Typha 到 Felix，后者配置本地数据平面并更新 BGP 路由。](../../../assets/diagrams/rendered/en-networking-calico-02-architecture-11.svg)

## 数据包流分析

### 入站数据包流（Pod 到 Pod，同一节点）

![展示数据包通过其 veth 接口和主机的 iptables/eBPF 策略检查，从一个 Pod 到达同一节点上的另一个 Pod。](../../../assets/diagrams/rendered/en-networking-calico-02-architecture-12.svg)

### 出站数据包流（Pod 到 Pod，使用 IPIP 的不同节点）

![展示数据包从一个节点的 Pod 经由其 veth 和 iptables 检查离开，通过物理网络交换机以 IPIP 封装传输，在第二个节点解封装后送达一个 Pod。](../../../assets/diagrams/rendered/en-networking-calico-02-architecture-13.svg)

### 数据包结构对比

```
Original Pod-to-Pod Packet:
┌─────────────────────────────────────────────────────────────┐
│ Ethernet │   IP Header    │   TCP/UDP   │     Payload      │
│  Header  │ Src: 192.168.1.10 │   Header    │                  │
│          │ Dst: 192.168.2.10 │             │                  │
└─────────────────────────────────────────────────────────────┘

IPIP Encapsulated Packet:
┌───────────────────────────────────────────────────────────────────────────────┐
│ Ethernet │   Outer IP     │   Inner IP     │   TCP/UDP   │     Payload      │
│  Header  │ Src: 10.0.1.10 │ Src: 192.168.1.10 │   Header    │                  │
│          │ Dst: 10.0.1.11 │ Dst: 192.168.2.10 │             │                  │
│          │ Proto: 4 (IPIP)│                │             │                  │
└───────────────────────────────────────────────────────────────────────────────┘
```

## 总结

Calico 的架构专为可扩展性、性能和运维简洁性而设计：

1. **Felix**：每个节点上的核心 Agent，配置路由和 ACL
2. **BIRD**：通过 BGP 分发路由，实现原生路由集成
3. **confd**：将 datastore 桥接到 BIRD 配置
4. **Typha**：通过降低 API server 负载来扩展系统
5. **kube-controllers**：保持 Kubernetes 与 Calico 同步
6. **Datastore**：使用 Kubernetes API（推荐）或 etcd 存储配置

了解这些组件及其交互对于以下事项至关重要：

* 排查连通性问题
* 大规模优化性能
* 规划容量和架构
* 与现有网络基础设施集成

[上一节：第 1 部分 - Calico 简介](01-introduction.md)

[下一节：第 3 部分 - 网络模式](03-networking-modes.md)

[返回 Calico 概览](./README.md)

## 测验

要检验您在本章所学的内容，请尝试[架构测验](../../quizzes/networking/calico/02-architecture-quiz.md)。
