# EKS Hybrid Nodes Gateway 测验

> **最后更新**：2026 年 9 月 13 日

1. EKS Hybrid Nodes Gateway 解决什么问题？
   - A) 取代控制平面连接所需的 VPN/Direct Connect
   - B) 自动管理网关负责的 Pod 路由，并在 VPC 与混合节点之间转发 VXLAN 流量
   - C) 为混合节点提供托管 NAT 网关
   - D) 加密云端与本地之间的所有流量

<details>
<summary>显示答案</summary>

**答案：B) 自动管理网关负责的 Pod 路由，并在 VPC 与混合节点之间转发 VXLAN 流量**

**说明：**
网关会配置聚合的 VPC Pod CIDR 路由和本地 VXLAN 转发状态。底层网络仍须通过获准的私有连接，在网关 IP 与混合节点 IP 之间提供路由。请检查路由表的管理归属、返回路径和安全规则；安装网关不会免除所有手动网络配置，卸载时也不会删除 AWS 路由。

</details>

---

2. 网关如何维持高可用性？
   - A) 多个网关采用主动-主动模式并通过负载均衡分摊流量
   - B) 两个网关 Pod 组成 Deployment，并通过 Kubernetes Lease 选主
   - C) 由 AWS 托管冗余并自动进行故障转移
   - D) 在多个可用区运行，并使用 Route 53 健康检查

<details>
<summary>显示答案</summary>

**答案：B) 两个网关 Pod 组成 Deployment，并通过 Kubernetes Lease 选主**

**说明：**
Chart 默认使用两个副本，要求主机反亲和，并优先分散到不同可用区。两个副本都会维护本地隧道条目；只有 leader 会更新 VPC 路由和 CiliumVTEPConfig。Lease 过期、路由替换、Cilium 收敛和应用恢复都可能造成流量中断。增加 standby 副本不会分摊吞吐量；PDB 也不保证 leader 或 standby 按特定顺序替换。

</details>

---

3. CiliumVTEPConfig 在网关架构中起什么作用？
   - A) 为混合节点配置 Cilium 网络策略
   - B) 将网关 IP 注册为远端 VTEP，使混合节点上的 Cilium agent 通过网关 VXLAN 隧道转发发往 VPC 的流量
   - C) 管理集群中的 Cilium 版本升级
   - D) 为 VXLAN 隧道提供加密密钥

<details>
<summary>显示答案</summary>

**答案：B) 将网关 IP 注册为远端 VTEP，使混合节点上的 Cilium agent 通过网关 VXLAN 隧道转发发往 VPC 的流量**

**说明：**
Gateway 1.0.2 管理名为 `hybrid-gateway` 的 `cilium.io/v2` 对象。其 `spec.endpoints` 条目包含 `name`、`tunnelEndpoint`、`cidr` 和 `mac`。端点使用当前 leader 节点的 IP 和实际 VXLAN 接口 MAC。此资源不是加密密钥配置；VNI 也不是该 CRD 的字段。

</details>

---

4. 使用 Hybrid Nodes Gateway 有哪些 CNI 前提条件？
   - A) 云端和混合节点上可以使用任意 CNI
   - B) 云端节点使用 Cilium，混合节点使用 VPC CNI
   - C) 使用启用了 VTEP、禁用 L7 的 AWS 维护版 Cilium，并正确配置云端节点网络
   - D) 云端和混合节点都使用 VPC CNI

<details>
<summary>显示答案</summary>

**答案：C) 使用启用了 VTEP、禁用 L7 的 AWS 维护版 Cilium，并正确配置云端节点网络**

**说明：**
应使用达到网关 VTEP 最低版本要求的 AWS 维护版 Cilium，并设置 `vtep.enabled=true` 和 `l7Proxy=false`。Cilium Ingress/Gateway API 的 L7 功能不能与此配置共用。使用 `aws-node` 的托管或自管云端节点，必须将混合 Pod CIDR 排除在 SNAT 之外，才能让发往混合端点的 ClusterIP 流量正常工作。Auto Mode 提供内置网络，不要为它安装或配置 `aws-node` DaemonSet。仅测试 Pod IP 不能验证 ClusterIP 行为。

</details>

---

5. 网关使用什么 VXLAN 配置？
   - A) VNI 1、UDP 端口 4789（标准 VXLAN）
   - B) VNI 2、UDP 端口 8472（Cilium 默认值）
   - C) VNI 100、UDP 端口 6081（Geneve）
   - D) VNI 0、UDP 端口 443（HTTPS 封装）

<details>
<summary>显示答案</summary>

**答案：B) VNI 2、UDP 端口 8472（Cilium 默认值）**

**说明：**
默认接口为 `hybrid_vxlan0`，VNI 为 2，UDP 端口为 8472。1.0.2 版本不会为此接口分配 IP。网关会生成确定性 MAC，并根据每个混合节点的内部 IP 和 Pod CIDR 安装 FDB、邻居及 onlink 路由条目。底层网络必须允许 UDP 流量双向通过。VXLAN 封装不会加密流量。

</details>

---

6. 网关如何管理 VPC 路由？
   - A) 使用 BGP 向 VPC 路由器通告 Pod 路由
   - B) 自动创建并维护 VPC 路由表条目，将混合 Pod CIDR 指向活动网关的主 ENI
   - C) 修改 VPC 主路由表以添加 NAT 规则
   - D) 配置 Transit Gateway 路由表

<details>
<summary>显示答案</summary>

**答案：B) 自动创建并维护 VPC 路由表条目，将混合 Pod CIDR 指向活动网关的主 ENI**

**说明：**
leader 的设置流程会为配置的聚合 Pod CIDR 创建或替换路由，然后更新 CiliumVTEPConfig。CiliumNode 事件则会分别更新每个网关副本上的本地节点隧道条目。运行时所需权限为 `DescribeRouteTables`、`DescribeInstances`、`CreateRoute` 和 `ReplaceRoute`。它不会调用 `DeleteRoute`；退役网关后，运维人员必须检查并移除或恢复自己负责的路由。

</details>

---

7. EKS Hybrid Nodes Gateway 的定价模式是什么？
   - A) 按处理的数据量收取小时费用
   - B) 已包含在 EKS Hybrid Nodes 价格中，每个混合节点每小时 0.10 美元
   - C) 网关软件本身不收费；EC2 和其他适用的基础设施及流量费用仍会产生
   - D) 前三个月免费，之后按标准 AWS 网络费用收费

<details>
<summary>显示答案</summary>

**答案：C) 网关软件本身不收费；EC2 和其他适用的基础设施及流量费用仍会产生**

**说明：**
网关软件不额外收费。不过，EC2、适用的 Auto Mode 管理费、存储、跨可用区数据传输、私有连接和可观测性都可能产生费用，集群及 Hybrid Nodes 费用也仍然适用。总费用取决于部署方式和流量情况，不能据此保证所有场景都能节省成本。

</details>

---

8. 在什么情况下，应优先选择网关方案，而不是手动配置 Pod 路由（BGP/静态路由）？
   - A) 需要尽可能降低云端与本地 Pod 之间的延迟时
   - B) AWS Cilium/VTEP 配置和额外网关跳数适合当前设计，并且希望简化 Pod 路由管理时
   - C) 混合节点超过 1000 个时
   - D) 混合节点使用非 Cilium CNI 时

<details>
<summary>显示答案</summary>

**答案：B) AWS Cilium/VTEP 配置和额外网关跳数适合当前设计，并且希望简化 Pod 路由管理时**

**说明：**
如果所需的 AWS Cilium/VTEP 配置符合设计，而且可以接受额外的主动-备用网关跳数，网关有助于简化 Pod 路由管理。Webhook 和 ALB/NLB 目标仍需各自配置路由、返回路径、远端 Pod 网络、健康检查和安全规则；可路由的 Pod 网络也能支持这些路径。已有 BGP/静态路由，或有不同 CNI/L7 需求时，其他设计可能更合适。

</details>
