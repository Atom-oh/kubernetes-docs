# BGP 深入解析测验

> **相关文档**：[BGP 深入解析](../../../networking/calico/04-bgp-deep-dive.md)
> **最后更新**：2026 年 9 月 12 日

## 测验

1. BGP 代表什么？
   - A) 基本网关协议（Basic Gateway Protocol）
   - B) 边界网关协议（Border Gateway Protocol）
   - C) 桥接网关协议（Bridge Gateway Protocol）
   - D) 带宽网关协议（Bandwidth Gateway Protocol）

<details>
<summary>显示答案</summary>

**答案：B) 边界网关协议（Border Gateway Protocol）**

**解释：**
BGP 是 Border Gateway Protocol（边界网关协议）的缩写，是互联网使用的路由协议，可让自治系统交换路由信息。在 Calico 中，BGP 用于在节点间分发 Pod 网络路由，也可将路由通告到外部网络基础设施。

</details>

2. iBGP 和 eBGP 有什么区别？
   - A) iBGP 更快，eBGP 更安全
   - B) iBGP 在同一 AS 内运行，eBGP 在不同 AS 之间运行
   - C) iBGP 使用 TCP，eBGP 使用 UDP
   - D) iBGP 用于 IPv4，eBGP 用于 IPv6

<details>
<summary>显示答案</summary>

**答案：B) iBGP 在同一 AS 内运行，eBGP 在不同 AS 之间运行**

**解释：**
iBGP（内部 BGP）是同一自治系统（AS）内路由器之间的 BGP 会话；eBGP（外部 BGP）是不同 AS 中路由器之间的会话。在 Calico 集群中，节点通常在集群内使用 iBGP（同一 AS），也可以使用 eBGP 与外部网络基础设施对等（不同 AS）。

</details>

3. 哪个范围预留给 16 位私有 ASN？
   - A) 1-64511
   - B) 64512-65534
   - C) 65535-65600
   - D) 100000-200000

<details>
<summary>显示答案</summary>

**答案：B) 64512-65534**

**解释：**
私有 ASN 范围包括 64512-65534（16 位）和 4200000000-4294967294（32 位）。ASN 用于标识自治系统，不能与不可在全球路由的私有 IP 地址混为一谈。向全球互联网通告路由前，应从 AS 路径中移除私有 ASN。Calico 的默认 ASN 是 64512。

</details>

4. 在全互连 BGP 拓扑中，包含 N 个节点的集群会建立多少个 BGP 会话？
   - A) N 个会话
   - B) N * 2 个会话
   - C) N * (N-1) / 2 个会话
   - D) N^2 个会话

<details>
<summary>显示答案</summary>

**答案：C) N * (N-1) / 2 个会话**

**解释：**
全互连拓扑中，每个节点都与其他节点建立对等连接，会话数为 N * (N-1) / 2，其中 N 是节点数。例如，10 个节点会建立 10 * 9 / 2 = 45 个 BGP 会话。大型集群通常因此建议采用 Route Reflector（路由反射器）。

</details>

5. BGP Route Reflector（路由反射器）的主要作用是什么？
   - A) 加密 BGP 流量
   - B) 将路由反射给客户端，从而减少 BGP 会话数量
   - C) 过滤恶意路由
   - D) 将 iBGP 转换为 eBGP

<details>
<summary>显示答案</summary>

**答案：B) 将路由反射给客户端，从而减少 BGP 会话数量**

**解释：**
Route Reflector 从客户端接收路由，再将路由反射给其他客户端，以减少集群所需的 BGP 会话。全互连需要 N*(N-1)/2 个会话；采用路由反射时，客户端只需与一个或多个 Route Reflector 对等。这是大型集群扩展 BGP 的重要方式。

</details>

6. Route Reflector 配置中的 Cluster ID 有什么作用？
   - A) 标识 Kubernetes 集群
   - B) 防止 Route Reflector 之间形成路由环路
   - C) 为节点分配 IP 地址
   - D) 加密 BGP 会话

<details>
<summary>显示答案</summary>

**答案：B) 防止 Route Reflector 之间形成路由环路**

**解释：**
如果一条被反射的路由的 CLUSTER_LIST 已包含本地 Cluster ID，Route Reflector 就会拒绝该路由。同一组客户端的冗余 Route Reflector 可以共用一个 ID；不同的反射器组或层级则需要有意规划 ID。Cluster ID 不是 Kubernetes 集群标识符。

</details>

7. BGPPeer 资源中的 nodeSelector 字段控制什么？
   - A) 哪些 Pod 可以使用 BGP
   - B) 哪些节点应建立 BGP 对等会话
   - C) 通告哪些路由
   - D) 哪些命名空间可以使用该 peer

<details>
<summary>显示答案</summary>

**答案：B) 哪些节点应建立 BGP 对等会话**

**解释：**
BGPPeer 中的 `nodeSelector` 指定哪些节点应与所定义的 peer 建立 BGP 会话。例如，可以按机架选择节点，让它们只与本机架的 ToR（Top of Rack，机架顶端）交换机对等，而不是让集群中的所有节点都建立该会话。

</details>

8. 哪项 BGPConfiguration 设置会禁用自动节点间 mesh？
   - A) meshEnabled: false
   - B) nodeToNodeMeshEnabled: false
   - C) disableMesh: true
   - D) bgpMesh: disabled

<details>
<summary>显示答案</summary>

**答案：B) nodeToNodeMeshEnabled: false**

**解释：**
该设置会禁用自动 mesh 会话。切换前，应先建立并验证替代 Route Reflector 或网络 fabric 会话、收发路由、下一跳及代表性流量。将节点标记为 Route Reflector 后，该节点会立即退出自动 mesh，因此应先准备好合适的节点。

</details>

9. Calico 可以通过 BGP 通告哪些类型的 Service IP？
   - A) 仅 ClusterIP
   - B) 仅 LoadBalancer IP
   - C) ClusterIP、ExternalIP 和 LoadBalancer IP
   - D) 仅 NodePort Service

<details>
<summary>显示答案</summary>

**答案：C) ClusterIP、ExternalIP 和 LoadBalancer IP**

**解释：**
对应的字段是 `serviceClusterIPs`、`serviceExternalIPs` 和 `serviceLoadBalancerIPs`。这些字段通告的是已存在的地址；地址分配、端点健康状况和返回路由是另外的前提。云负载均衡器的主机名不是 BGP 前缀。Kubernetes `spec.externalIPs` 自 1.36 起已弃用，但尚未移除。

</details>

10. Calico 中 BGP communities 有什么作用？
    - A) 创建用于访问控制的用户组
    - B) 为路由添加元数据标签，以供策略决策使用
    - C) 加密特定路由
    - D) 压缩路由表

<details>
<summary>显示答案</summary>

**答案：B) 为路由添加元数据标签，以供策略决策使用**

**解释：**
Community 用于为路由添加标签，供路由器策略使用。标准 community 由两个 16 位值组成，大型 community 由三个 32 位值组成。诸如 high-priority 或 internal-only 的名称本身不会自动强制执行相应含义。`prefixAdvertisements` 会为匹配的现有路由添加标签，不会起源一个聚合路由。

</details>

11. 在 Calico 中，可以使用哪种身份验证方式保护 BGP 会话？
    - A) TLS 证书
    - B) MD5 身份验证
    - C) OAuth token
    - D) Kerberos

<details>
<summary>显示答案</summary>

**答案：B) MD5 身份验证**

**解释：**
TCP MD5 签名选项通过 BGPPeer 引用的共享密钥对 BGP 流量进行身份验证。它不会加密流量，也不能证明已通过身份验证的对等体通告的路由是合法的。应分别配置匹配的凭据和路由过滤规则。

</details>

12. 在 BGP 中，Graceful Restart（优雅重启）是什么？
    - A) 不丢失配置地重启 BGP 的方法
    - B) BGP 守护进程重启时保留转发状态的机制
    - C) 逐步添加新 BGP 对等体的方法
    - D) 缓慢撤销路由的技术

<details>
<summary>显示答案</summary>

**答案：B) BGP 守护进程重启时保留转发状态的机制**

**解释：**
对等体会协商 Graceful Restart 能力，并可在 BGP 守护进程重启期间，在有时间上限的时段内保留路由。只有转发路径仍可用时这才有帮助；保留已过期的路由也可能导致流量被黑洞。它不能保证更新不中断。

</details>

13. 使用什么命令检查 BIRD 守护进程中的 BGP 协议状态？
    - A) bird status
    - B) birdcl -s /var/run/calico/bird.ctl show protocols
    - C) bird show peers
    - D) birdctl status bgp

<details>
<summary>显示答案</summary>

**答案：B) birdcl -s /var/run/calico/bird.ctl show protocols**

**解释：**
应在目标 calico-node 容器内使用带有显式 IPv4 控制套接字的命令。它会列出包括 BGP、kernel 和 device 协议在内的协议。查看具体协议详情时，可将 `show protocols all` 与实际协议名称一起使用。IPv6 使用 birdcl6 和 /var/run/calico/bird6.ctl。如果安装禁用了 BGP，可能根本没有 BIRD 守护进程。

</details>

14. 在 Spine-Leaf 数据中心拓扑中，Calico 节点通常应如何建立对等连接？
    - A) 每个节点都与所有 Spine 交换机对等
    - B) 节点与本地 ToR（Leaf）交换机对等
    - C) 只有 master 节点与网络基础设施对等
    - D) 节点彼此直接对等并绕过交换机

<details>
<summary>显示答案</summary>

**答案：B) 节点与本地 ToR（Leaf）交换机对等**

**解释：**
在 Spine-Leaf 拓扑中，Calico 节点通常与本机架的 Top-of-Rack（ToR/Leaf）交换机对等；Leaf 交换机再与 Spine 交换机对等。这遵循数据中心网络的分层设计。BGPPeer 资源中的 `nodeSelector` 可确保节点只与所在机架的 ToR 交换机建立对等连接。

</details>

15. 引入显式 Route Reflector 对等会话时，如果 nodeToNodeMeshEnabled 仍为 true，会发生什么？
    - A) Route Reflector 自动优先，mesh 会禁用
    - B) 非 RR 客户端的 mesh 会话可在过渡期间与显式 RR 会话并存
    - C) 配置错误，Calico 无法启动
    - D) Route Reflector 会被忽略

<details>
<summary>显示答案</summary>

**答案：B) 非 RR 客户端的 mesh 会话可在过渡期间与显式 RR 会话并存**

**解释：**
设置 `routeReflectorClusterID` 后，RR 节点会退出自动 mesh。其余非 RR 客户端在准备并测试显式 RR 会话期间仍可保留 mesh。只有在替代会话、路由、下一跳和流量均验证通过后，才应移除该 mesh。

</details>

16. 哪条导入规则只匹配 IPv4 默认路由？
    - A) Accept with In 0.0.0.0/0
    - B) Accept with Equal 0.0.0.0/0
    - C) Reject with NotIn 0.0.0.0/0
    - D) 不配置任何规则的过滤器

<details>
<summary>显示答案</summary>

**答案：B) Accept with Equal 0.0.0.0/0**

**解释：**
Equal 匹配完全相同的 /0 前缀。In /0 会匹配所有 IPv4 路由；NotIn /0 则一个也不匹配。BGPFilter 对未匹配的路由默认采取 Accept，因此白名单还必须包含一条无条件的最终 Reject。

</details>

17. 对 10.244.0.0/16 使用 prefixAdvertisements 会有什么作用？
    - A) 始终起源一条新的 /16 路由
    - B) 将每条 /26 路由都替换成 /16
    - C) 为匹配该范围的现有路由添加 communities
    - D) 分配 Service IP

<details>
<summary>显示答案</summary>

**答案：C) 为匹配该范围的现有路由添加 communities**

**解释：**
当前 Calico 渲染器会为匹配的现有路由（包括 Pod 路由）添加 communities；它不会起源该前缀、分配地址或聚合地址块。如果显式 BGPFilter export Accept 规则先匹配路由，可能会绕过这项内置标记；因此，可能需要对已接受的路由执行补充标记操作。

</details>

---

[返回学习材料](../../../networking/calico/04-bgp-deep-dive.md) | [上一测验：网络模式](./03-networking-modes-quiz.md) | [下一测验：网络策略](./05-network-policy-quiz.md)
