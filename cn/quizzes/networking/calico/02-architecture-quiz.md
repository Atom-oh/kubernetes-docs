# Calico 架构测验

> **相关文档**：[Calico 架构](../../../networking/calico/02-architecture.md)
> **最后更新**：2026 年 9 月 12 日

## 测验

1. Felix 在 Calico 架构中的主要作用是什么？
   - A) 分发 BGP 路由
   - B) 在每个节点上执行策略并管理网络接口
   - C) 聚合数据存储连接
   - D) 处理配置模板

<details>
<summary>显示答案</summary>

**答案：B) 在每个节点上执行策略并管理网络接口**

**说明**：
Felix 会协调 endpoint 接口设置、适用路由和内核策略。在完整的 Calico Linux 网络中，容器运行时会调用 CNI/IPAM 链来分配地址并创建 Pod veth 接口。Felix 不会直接通过 CNI ADD 调用，也不负责分配 Pod IP。

</details>

2. BIRD 的全称是什么？它在 Calico 中发挥什么作用？
   - A) Basic Internet Routing Daemon，负责 DNS 解析
   - B) BIRD Internet Routing Daemon，负责 BGP 路由
   - C) Binary Internet Relay Daemon，负责数据包转发
   - D) Bridge Internet Routing Device，负责 VXLAN 隧道

<details>
<summary>显示答案</summary>

**答案：B) BIRD Internet Routing Daemon，负责 BGP 路由**

**说明**：
启用相应后端时，BIRD 会管理 BGP 会话和路由交换。它可以充当 route reflector，并通过自身的 kernel 协议与内核同步路由。BGP 可以与封装同时使用；仅启用 BGP 并不保证流量不经封装转发。工作负载数据包不会经过 BIRD 进程。

</details>

3. confd 在 Calico 架构中的用途是什么？
   - A) 管理容器配置
   - B) 动态生成 BIRD 配置文件
   - C) 存储网络策略
   - D) 对流量进行负载均衡

<details>
<summary>显示答案</summary>

**答案：B) 动态生成 BIRD 配置文件**

**说明**：
confd 会监视相关数据存储状态，并根据已安装的 BIRD 模板生成配置。它会检查生成结果，并调用配置的重新加载命令。生成的文件并非持久配置来源；应修改 BGP API 资源，而不是直接编辑生成的 bird.cfg。

</details>

4. 关于部署 Typha，哪种说法正确？
   - A) 无论集群规模如何，都必须部署
   - B) Operator 安装即使在少于 50 个节点时也可能部署 Typha；应依据所安装版本的扩缩容逻辑和实际工作负载需求
   - C) 仅在使用 eBPF 模式时部署
   - D) 仅在多集群部署时部署

<details>
<summary>显示答案</summary>

**答案：B) Operator 安装即使在少于 50 个节点时也可能部署 Typha；应依据所安装版本的扩缩容逻辑和实际工作负载需求**

**说明**：
Typha 可减少向 Felix 扇出数据存储更新时的直接连接。它并非仅在节点数超过 50 时才普遍必需，也不是每种非 Operator 安装都必需。Operator 1.42.6 也会为小型集群扩缩 Typha；它依据计入扩缩容的节点数进行计算，并检查 Linux 节点的放置容量。

</details>

5. Calico 支持哪些数据存储选项？
   - A) MySQL 和 PostgreSQL
   - B) etcd 和 Kubernetes API
   - C) MongoDB 和 Redis
   - D) 仅专用 etcd

<details>
<summary>显示答案</summary>

**答案：B) etcd 和 Kubernetes API**

**说明**：
Calico 支持 Kubernetes API 和直接连接 etcdv3 两种数据存储路径，但各自受功能和安装方式限制。Kubernetes API 路径仍使用 Kubernetes 后端存储，无需单独部署 Calico etcd 集群。直接使用 etcd 则需要自行设计 TLS、凭证、高可用性和备份；节点数量本身并不是切换到 etcd 的理由。

</details>

6. Operator 1.42.6 为标准 Open Source kube-controllers 部署选择哪些 controller？
   - A) 仅 Policy Controller
   - B) node 和 loadbalancer
   - C) 仅 Node 和 Policy Controller
   - D) 仅 WorkloadEndpoint Controller

<details>
<summary>显示答案</summary>

**答案：B) node 和 loadbalancer**

**说明**：
固定版本的 Operator renderer 会为其常规 Open Source 部署启动 node 和 loadbalancer。Policy、namespace、serviceaccount 和 workloadendpoint controller 也存在，适用于相应的数据存储和配置路径，但不一定都会启用。ServiceAccount profile 不会授予 Kubernetes RBAC 权限。

</details>

7. 对于 500 个计入扩缩容的节点，Operator 1.42.6 的扩缩容函数会返回多少个期望 Typha 副本？
   - A) 每 50 个节点 1 个副本
   - B) 4 个副本，计算方式为 floor(500 / 200) + 2
   - C) 固定为 5 个副本
   - D) 每 100 个节点 1 个副本，最少 1 个

<details>
<summary>显示答案</summary>

**答案：B) 4 个副本，计算方式为 floor(500 / 200) + 2**

**说明**：
当计入扩缩容的节点数大于 4 时，此版本使用 max(3, floor(N / 200) + 2) 计算副本数，因此 500 个节点得到 4 个副本。1 或 2 个节点时为 1 个；3 或 4 个节点时为 2 个。1,000 个节点时结果为 7 个。扩缩容计算会排除不可调度节点和 AKS 虚拟节点，并检查可用 Linux 节点；这个结果不代表吞吐量保证。

</details>

8. Calico 的哪个 agent 会协调本地工作负载路由和内核策略状态？
   - A) BIRD
   - B) confd
   - C) Felix
   - D) Typha

<details>
<summary>显示答案</summary>

**答案：C) Felix**

**说明**：
Felix 负责协调本地工作负载路由和策略。这不表示只有 Felix 会操作路由：CNI 会创建初始接口和路由，BIRD 的 kernel 协议也可以安装通过 BGP 学到的路由。confd 生成 BIRD 配置；Typha 则分发缓存的状态。

</details>

9. Typha 使用哪个端口与 Felix 实例通信？
   - A) 443
   - B) 5473
   - C) 8080
   - D) 9090

<details>
<summary>显示答案</summary>

**答案：B) 5473**

**说明**：
TCP 5473 是 Typha 默认的同步监听端口，供 Felix 等客户端连接。该端口与 metrics 和 health 端口分开，也不是代理应用流量的端口。Operator 还会配置 TLS 信任和客户端身份。

</details>

10. 哪个 FelixConfiguration 设置可以启用 eBPF 模式？
    - A) ebpfEnabled: true
    - B) bpfEnabled: true
    - C) dataplaneMode: ebpf
    - D) useEbpf: true

<details>
<summary>显示答案</summary>

**答案：B) bpfEnabled: true**

**说明**：
bpfEnabled 是有效的底层 FelixConfiguration 字段。对于由 Operator 管理的安装，请使用受支持的 Installation linuxDataplane 设置，并协调 kube-proxy 与 API 可达性。只更改一个布尔值并不等于完成经过验证的迁移，也不能保证所有 eBPF 功能都可用。

</details>

11. 大型集群未部署 Typha 时，Felix 实例会怎样？
    - A) Felix 实例无法启动
    - B) 每个 Felix 都直接连接数据存储，可能使 API server 不堪重负
    - C) 网络策略不会执行
    - D) BGP 对等连接会失败

<details>
<summary>显示答案</summary>

**答案：B) 每个 Felix 都直接连接数据存储，可能使 API server 不堪重负**

**说明**：
随着节点数和更新量增加，直接建立 watch 连接会增加数据存储/API 的负载。这是容量问题，并不表示没有 Typha 就一定无法执行策略或运行 BGP。即使部署了 Typha，其他组件仍会访问 Kubernetes API。

</details>

12. Felix 默认使用哪个健康检查端口？
    - A) 8080
    - B) 9091
    - C) 9099
    - D) 10250

<details>
<summary>显示答案</summary>

**答案：C) 9099**

**说明**：
启用 health serving 时，Felix 的默认 health 端口为 9099，默认绑定地址为 localhost。探针和网络设置必须与实际部署一致；在管理员笔记本电脑上请求 localhost 并不能检查节点。常用 metrics 端口为 9091。

</details>

---

[学习材料](../../../networking/calico/02-architecture.md) | [上一份测验](01-introduction-quiz.md) | [下一份测验](03-networking-modes-quiz.md)
