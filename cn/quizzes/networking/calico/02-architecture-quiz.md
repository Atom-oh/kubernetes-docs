# Calico 架构测验

> **相关文档**: [Calico 架构](../../../networking/calico/02-architecture.md)
> **最后更新**: February 22, 2026

## 测验

1. Felix 在 Calico 架构中的主要职责是什么？
   - A) BGP 路由分发
   - B) 在每个节点上执行策略强制实施和接口管理
   - C) 聚合数据存储连接
   - D) 处理配置模板

<details>
<summary>显示答案</summary>

**答案：B) 在每个节点上执行策略强制实施和接口管理**

**说明：**
Felix 是在 Calico 集群中每个节点上运行的核心代理。其主要职责包括接口管理（创建 Pod veth 对）、路由表编程、iptables/eBPF 规则管理以及网络策略强制实施。Felix 确保数据平面得到正确配置，以实施所需的网络策略。

</details>

2. BIRD 的全称是什么，它在 Calico 中的作用是什么？
   - A) Basic Internet Routing Daemon - 处理 DNS 解析
   - B) BIRD Internet Routing Daemon - 处理 BGP 路由
   - C) Binary Internet Relay Daemon - 处理数据包转发
   - D) Bridge Internet Routing Device - 处理 VXLAN 隧道

<details>
<summary>显示答案</summary>

**答案：B) BIRD Internet Routing Daemon - 处理 BGP 路由**

**说明：**
BIRD（BIRD Internet Routing Daemon）是 Calico 中的 BGP 代理，负责管理 BGP 对等连接、在节点之间交换和传播路由，并可选择作为 Route Reflector 运行。BIRD 使 Calico 能够使用原生 BGP 功能进行无需封装的直接路由。

</details>

3. confd 在 Calico 架构中的用途是什么？
   - A) 管理容器配置
   - B) 动态生成 BIRD 配置文件
   - C) 存储网络策略
   - D) 对流量进行负载均衡

<details>
<summary>显示答案</summary>

**答案：B) 动态生成 BIRD 配置文件**

**说明：**
confd 负责根据模板动态生成 BIRD 配置文件。它会监控 Calico 数据存储中 BGP 配置、节点信息和对等设置的变更，然后自动更新 BIRD 的配置以反映这些变更，无需手动干预。

</details>

4. 何时应在 Calico 集群中部署 Typha？
   - A) 无论集群规模如何，始终部署
   - B) 仅适用于超过 50 个节点的集群
   - C) 仅在使用 eBPF 模式时
   - D) 仅适用于多集群部署

<details>
<summary>显示答案</summary>

**答案：B) 仅适用于超过 50 个节点的集群**

**说明：**
建议在具有 50 个或更多节点的集群中使用 Typha。如果没有 Typha，每个 Felix 实例都会直接连接到数据存储，这可能会使大型集群中的 API server 不堪重负。Typha 会聚合数据存储连接，并向 Felix 实例提供缓存数据，从而显著降低 API server 的负载。

</details>

5. Calico 支持哪些数据存储选项？
   - A) MySQL 和 PostgreSQL
   - B) etcd 和 Kubernetes API
   - C) MongoDB 和 Redis
   - D) 仅专用 etcd

<details>
<summary>显示答案</summary>

**答案：B) etcd 和 Kubernetes API**

**说明：**
Calico 支持两种数据存储选项：专用 etcd 集群或 Kubernetes API（使用 CRDs）。对于大多数部署，建议使用 Kubernetes API 数据存储，因为它通过利用现有 Kubernetes 基础设施简化了运维。etcd 数据存储用于非 Kubernetes 部署，或在需要特定 etcd 功能时使用。

</details>

6. kube-controllers 包含哪些控制器？
   - A) 仅 Policy Controller
   - B) Policy、Namespace、ServiceAccount、WorkloadEndpoint 和 Node Controllers
   - C) 仅 Node 和 Policy Controllers
   - D) 仅 WorkloadEndpoint Controller

<details>
<summary>显示答案</summary>

**答案：B) Policy、Namespace、ServiceAccount、WorkloadEndpoint 和 Node Controllers**

**说明：**
kube-controllers 包含多个在 Kubernetes 和 Calico 数据存储之间进行同步的控制器：Policy Controller（NetworkPolicy 同步）、Namespace Controller（命名空间配置文件管理）、ServiceAccount Controller（服务账户同步）、WorkloadEndpoint Controller（端点清理）和 Node Controller（节点信息同步）。

</details>

7. 在大型集群中计算 Typha 副本数的推荐公式是什么？
   - A) 每 50 个节点 1 个副本
   - B) 节点数量除以 200，最少 3 个
   - C) 固定为 5 个副本
   - D) 每 100 个节点 1 个副本，最少 1 个

<details>
<summary>显示答案</summary>

**答案：B) 节点数量除以 200，最少 3 个**

**说明：**
Typha 副本数的推荐公式为：节点数量 / 200，且为实现高可用性至少需要 3 个副本。例如，一个包含 500 个节点的集群至少需要 3 个副本（500/200 = 2.5，向上取整后最少为 3 个），而一个包含 1000 个节点的集群则需要 5 个副本。

</details>

8. 在 Calico 的数据包流中，哪个组件负责在节点上编写路由表？
   - A) BIRD
   - B) confd
   - C) Felix
   - D) Typha

<details>
<summary>显示答案</summary>

**答案：C) Felix**

**说明：**
Felix 负责在每个节点上编写路由表。尽管 BIRD 负责节点之间的 BGP 路由交换，Felix 会获取路由信息并将其编写到 Linux 内核的路由表中。Felix 还管理用于策略强制实施的 iptables/eBPF 规则。

</details>

9. Typha 使用哪个端口与 Felix 实例通信？
   - A) 443
   - B) 5473
   - C) 8080
   - D) 9090

<details>
<summary>显示答案</summary>

**答案：B) 5473**

**说明：**
Typha 在端口 5473（calico-typha）上监听来自 Felix 实例的连接。这是在 Typha 部署中配置的默认端口，用于接收集群中每个节点上运行的 calico-node Pod 的连接。

</details>

10. 哪项 FelixConfiguration 设置可启用 eBPF 模式？
    - A) ebpfEnabled: true
    - B) bpfEnabled: true
    - C) dataplaneMode: ebpf
    - D) useEbpf: true

<details>
<summary>显示答案</summary>

**答案：B) bpfEnabled: true**

**说明：**
要在 Calico 中启用 eBPF 模式，需要在 FelixConfiguration 资源中设置 `bpfEnabled: true`。这会将数据平面从 iptables 切换到 eBPF，提升性能，并启用 Direct Server Return (DSR) 和 kube-proxy 替代等功能。

</details>

11. 当大型集群中未部署 Typha 时，Felix 实例会发生什么？
    - A) Felix 实例无法启动
    - B) 每个 Felix 都会直接连接到数据存储，可能使 API server 不堪重负
    - C) 不会强制实施网络策略
    - D) BGP 对等连接失败

<details>
<summary>显示答案</summary>

**答案：B) 每个 Felix 都会直接连接到数据存储，可能使 API server 不堪重负**

**说明：**
如果没有 Typha，每个节点上的每个 Felix 实例都会与数据存储（Kubernetes API server）保持自己的连接。在拥有数百个节点的大型集群中，这可能会因 watch 连接和数据传输而使 API server 不堪重负。Typha 通过聚合连接和缓存数据来解决此问题。

</details>

12. Felix 默认使用的健康检查端口是什么？
    - A) 8080
    - B) 9091
    - C) 9099
    - D) 10250

<details>
<summary>显示答案</summary>

**答案：C) 9099**

**说明：**
默认情况下，当在 FelixConfiguration 中设置 `healthEnabled: true` 时，Felix 的健康检查端点会监听端口 9099。Kubernetes 存活探针和就绪探针使用此端口来验证 Felix 是否在每个节点上正确运行。

</details>

---

[返回学习材料](../../../networking/calico/02-architecture.md) | [上一份测验：简介](./01-introduction-quiz.md) | [下一份测验：网络模式](./03-networking-modes-quiz.md)
