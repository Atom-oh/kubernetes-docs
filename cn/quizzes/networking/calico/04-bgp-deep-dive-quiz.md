# BGP 深入解析测验

> **相关文档**：[BGP 深入解析](../../../networking/calico/04-bgp-deep-dive.md)
> **最后更新**：February 22, 2026

## 测验

1. BGP 代表什么？
   - A) Basic Gateway Protocol
   - B) Border Gateway Protocol
   - C) Bridge Gateway Protocol
   - D) Bandwidth Gateway Protocol

<details>
<summary>显示答案</summary>

**答案：B) Border Gateway Protocol**

**解释：**
BGP 代表 Border Gateway Protocol。它是为互联网提供支持的路由协议，使自治系统（AS）能够交换路由信息。在 Calico 中，BGP 用于在节点之间分发 Pod 网络路由，也可以将路由分发到外部网络基础设施。

</details>

2. iBGP 和 eBGP 有什么区别？
   - A) iBGP 更快，eBGP 更安全
   - B) iBGP 位于同一 AS 内，eBGP 位于不同 AS 之间
   - C) iBGP 使用 TCP，eBGP 使用 UDP
   - D) iBGP 用于 IPv4，eBGP 用于 IPv6

<details>
<summary>显示答案</summary>

**答案：B) iBGP 位于同一 AS 内，eBGP 位于不同 AS 之间**

**解释：**
iBGP（Internal BGP）指同一自治系统（AS）内路由器之间的 BGP 会话。eBGP（External BGP）指不同自治系统中路由器之间的 BGP 会话。在 Calico 集群中，节点通常在集群内（同一 AS）使用 iBGP，并且可以使用 eBGP 与外部网络基础设施（不同 AS）建立对等连接。

</details>

3. 可用于 Calico 集群的私有 AS 编号范围是什么？
   - A) 1-64511
   - B) 64512-65534
   - C) 65535-65600
   - D) 100000-200000

<details>
<summary>显示答案</summary>

**答案：B) 64512-65534**

**解释：**
私有 AS 编号范围为 64512-65534（适用于 16 位 ASN）和 4200000000-4294967294（适用于 32 位 ASN）。这些范围指定为私有用途，不能在全球范围内路由，与私有 IP 地址范围类似。Calico 集群通常使用 64512-65534 范围内的 AS 编号。

</details>

4. 在全互连 BGP 拓扑中，具有 N 个节点的集群会建立多少个 BGP 会话？
   - A) N 个会话
   - B) N * 2 个会话
   - C) N * (N-1) / 2 个会话
   - D) N^2 个会话

<details>
<summary>显示答案</summary>

**答案：C) N * (N-1) / 2 个会话**

**解释：**
在全互连 BGP 拓扑中，每个节点都会与其他所有节点建立对等连接。会话数量计算为 N * (N-1) / 2，其中 N 是节点数量。例如，一个包含 10 个节点的集群将有 10 * 9 / 2 = 45 个 BGP 会话。因此，较大的集群建议使用 Route Reflector（路由反射器）。

</details>

5. BGP Route Reflector 的主要作用是什么？
   - A) 加密 BGP 流量
   - B) 通过将路由反射给客户端来减少 BGP 会话数量
   - C) 过滤恶意路由
   - D) 将 iBGP 转换为 eBGP

<details>
<summary>显示答案</summary>

**答案：B) 通过将路由反射给客户端来减少 BGP 会话数量**

**解释：**
Route Reflector 通过从客户端接收路由并将其“反射”给其他客户端，减少集群中所需的 BGP 会话数量。与全互连中的 N*(N-1)/2 个会话不同，客户端只需与 Route Reflector 建立对等连接。这对于在大型集群中扩展 BGP 至关重要。

</details>

6. Route Reflector 配置中的 Cluster ID 有什么作用？
   - A) 标识 Kubernetes 集群
   - B) 防止 Route Reflector 之间的路由环路
   - C) 为节点分配 IP 地址
   - D) 加密 BGP 会话

<details>
<summary>显示答案</summary>

**答案：B) 防止 Route Reflector 之间的路由环路**

**解释：**
当部署多个 Route Reflector 时，Cluster ID 用于防止路由环路。当 Route Reflector 收到带有其自身 Cluster ID 的路由时，它会知道该路由已经经过此 RR 集群并将其丢弃。同一集群中的所有 Route Reflector 应共享相同的 Cluster ID。

</details>

7. BGPPeer 资源中的 nodeSelector 字段控制什么？
   - A) 哪些 Pod 可以使用 BGP
   - B) 哪些节点应建立 BGP 对等连接
   - C) 广告哪些路由
   - D) 哪些命名空间可以使用该对等体

<details>
<summary>显示答案</summary>

**答案：B) 哪些节点应建立 BGP 对等连接**

**解释：**
BGPPeer 资源中的 `nodeSelector` 字段指定哪些节点应与定义的对等体建立 BGP 会话。这对于机架感知对等连接非常有用：只有特定机架中的节点应与本地 ToR（Top of Rack）交换机建立对等连接，而不是集群中的所有节点。

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
在 BGPConfiguration 资源中设置 `nodeToNodeMeshEnabled: false` 会禁用所有节点之间自动建立的全互连 BGP 对等连接。当使用 Route Reflector 或外部 BGP 对等连接时应进行此设置，因为在较大的部署中，全互连已无必要且会带来开销。

</details>

9. Calico 可以通过 BGP 广告哪些类型的 Service IP？
   - A) 仅 ClusterIP
   - B) 仅 LoadBalancer IP
   - C) ClusterIP、ExternalIP 和 LoadBalancer IP
   - D) 仅 NodePort Service

<details>
<summary>显示答案</summary>

**答案：C) ClusterIP、ExternalIP 和 LoadBalancer IP**

**解释：**
Calico 可以通过 BGP 广告多种类型的 Service IP：ClusterIP（内部 Service IP）、ExternalIP（分配给 Service 的外部 IP）和 LoadBalancer IP。这分别通过 BGPConfiguration 资源中的 `serviceClusterIPs`、`serviceExternalIPs` 和 `serviceLoadBalancerIPs` 字段进行配置。

</details>

10. BGP community 在 Calico 中有什么用途？
    - A) 创建用于访问控制的用户组
    - B) 使用元数据标记路由，以便制定策略决策
    - C) 加密特定路由
    - D) 压缩路由表

<details>
<summary>显示答案</summary>

**答案：B) 使用元数据标记路由，以便制定策略决策**

**解释：**
BGP community 是附加到路由的标签，路由器可以使用它们来制定策略决策。在 Calico 中，你可以为已广告的前缀配置 community 标签，使下游路由器能够基于这些标签应用特定策略（例如流量工程或过滤）。community 表示为 AS:value 对（例如 64512:100）。

</details>

11. 在 Calico 中可以使用哪种身份验证方法来保护 BGP 会话？
    - A) TLS 证书
    - B) MD5 身份验证
    - C) OAuth token
    - D) Kerberos

<details>
<summary>显示答案</summary>

**答案：B) MD5 身份验证**

**解释：**
Calico 支持使用 MD5 身份验证来保护 BGP 会话。这是一种 TCP MD5 签名选项，用于对对等体之间的 BGP 消息进行身份验证。虽然它不提供加密，但可以防止未经授权的设备与节点建立 BGP 会话。密码在 BGPPeer 资源中配置。

</details>

12. BGP 上下文中的 Graceful Restart 是什么？
    - A) 一种在不丢失配置的情况下重启 BGP 的方法
    - B) 一种在 BGP daemon 重启期间保留转发状态的机制
    - C) 一种逐步添加新 BGP 对等体的方法
    - D) 一种缓慢撤销路由的技术

<details>
<summary>显示答案</summary>

**答案：B) 一种在 BGP daemon 重启期间保留转发状态的机制**

**解释：**
Graceful Restart 是一种 BGP 能力，可让转发平面在 BGP daemon 重启期间继续运行。正在重启的路由器会通知其对等体它正在重启，而对等体会在宽限期内保留来自该路由器的路由。这可以防止在软件更新或短暂故障期间出现流量中断。

</details>

13. 在 BIRD daemon 中，使用什么命令检查 BGP 协议状态？
    - A) bird status
    - B) birdcl show protocols
    - C) bird show peers
    - D) birdctl status bgp

<details>
<summary>显示答案</summary>

**答案：B) birdcl show protocols**

**解释：**
`birdcl show protocols` 命令显示 BIRD daemon 中所有 BGP 协议的状态。这会显示 BGP 会话是否已建立、对等体状态以及路由交换统计信息。其他有用的命令包括用于显示路由表的 `birdcl show route`，以及用于查看详细会话信息的 `birdcl show protocols all <name>`。

</details>

14. 在 Spine-Leaf 数据中心拓扑中，Calico 节点通常应如何建立对等连接？
    - A) 所有节点与所有 Spine 交换机建立对等连接
    - B) 节点与其本地 ToR（Leaf）交换机建立对等连接
    - C) 只有 master 节点与网络基础设施建立对等连接
    - D) 节点直接相互建立对等连接，绕过交换机

<details>
<summary>显示答案</summary>

**答案：B) 节点与其本地 ToR（Leaf）交换机建立对等连接**

**解释：**
在 Spine-Leaf 拓扑中，Calico 节点通常与其本地 Top-of-Rack（ToR/Leaf）交换机建立对等连接。Leaf 交换机随后与 Spine 交换机建立对等连接。这遵循数据中心网络的分层设计，并使用 BGPPeer 资源中的 nodeSelector 确保节点只与其所在机架的 ToR 交换机建立对等连接。

</details>

15. 当 nodeToNodeMeshEnabled 为 true 且你还配置了 Route Reflector 时，会发生什么？
    - A) Route Reflector 优先，mesh 被禁用
    - B) 将同时建立 mesh 和 Route Reflector 会话（非最优）
    - C) 配置错误，Calico 无法启动
    - D) Route Reflector 被忽略

<details>
<summary>显示答案</summary>

**答案：B) 将同时建立 mesh 和 Route Reflector 会话（非最优）**

**解释：**
如果在配置 Route Reflector 时 nodeToNodeMeshEnabled 仍为 true，则会同时建立全互连会话和 Route Reflector 会话。这并非最优且会造成浪费。使用 Route Reflector 时，应设置 `nodeToNodeMeshEnabled: false` 以禁用自动 mesh，并仅依赖 Route Reflector 进行路由分发。

</details>

---

[返回学习材料](../../../networking/calico/04-bgp-deep-dive.md) | [上一测验：网络模式](./03-networking-modes-quiz.md) | [下一测验：网络策略](./05-network-policy-quiz.md)
