# EKS Hybrid Nodes Gateway 测验

1. EKS Hybrid Nodes Gateway 解决了什么问题？
   - A) 它取代了用于控制平面连接的 VPN/Direct Connect
   - B) 它使用 VXLAN tunnels 自动化 VPC 与 Hybrid Nodes（混合节点）之间的 Pod 级网络，消除手动 Pod 路由
   - C) 它为 Hybrid Nodes 提供托管 NAT gateway
   - D) 它加密云端与本地之间的所有流量

<details>
<summary>显示答案</summary>

**答案：B) 它使用 VXLAN tunnels 自动化 VPC 与 Hybrid Nodes（混合节点）之间的 Pod 级网络，消除手动 Pod 路由**

**解释：**
EKS Hybrid Nodes Gateway 自动化 EKS cluster VPC 与 Hybrid Nodes 上 Kubernetes Pods 之间的网络连接。它在基于 EC2 的 gateway nodes 与由 Cilium 管理的 Hybrid Nodes 之间创建 VXLAN tunnels，并自动维护 VPC route table 条目。这消除了手动配置 BGP、static routes，或让本地 Pod networks 可从 VPC 路由访问的需求。请注意，基础 node 连接仍然需要 VPN/Direct Connect。

</details>

---

2. gateway 如何保持高可用性？
   - A) 通过跨多个 gateways 的 load balancing 实现 active-active
   - B) 两个 gateway Pods 作为一个 Deployment，并使用基于 Kubernetes Lease 的 leader election
   - C) AWS 托管冗余并自动 failover
   - D) 在多个 Availability Zones 上运行，并使用 Route 53 health checks

<details>
<summary>显示答案</summary>

**答案：B) 两个 gateway Pods 作为一个 Deployment，并使用基于 Kubernetes Lease 的 leader election**

**解释：**
gateway 作为 2-Pod Deployment 运行在带有 label 的 EC2 nodes 上。基于 Kubernetes Lease 的 leader election 决定哪个 Pod 处于 active 状态。只有 leader 会执行 leader-specific 操作：管理 VPC route table 条目和 CiliumVTEPConfig CRD。当 leader 失败时，领导权会转移到 standby Pod，然后该 Pod 会更新 VPC routes，使其指向自己的 ENI。

</details>

---

3. CiliumVTEPConfig 在 gateway 架构中的作用是什么？
   - A) 它为 Hybrid Nodes 配置 Cilium network policies
   - B) 它将 gateway IP 注册为 remote VTEP，使 Hybrid Nodes 上的 Cilium agents 通过 gateway 的 VXLAN tunnel 转发发往 VPC 的流量
   - C) 它管理整个 cluster 中的 Cilium 版本升级
   - D) 它为 VXLAN tunnels 提供 encryption keys

<details>
<summary>显示答案</summary>

**答案：B) 它将 gateway IP 注册为 remote VTEP，使 Hybrid Nodes 上的 Cilium agents 通过 gateway 的 VXLAN tunnel 转发发往 VPC 的流量**

**解释：**
gateway leader 创建 CiliumVTEPConfig resource。每个本地 Hybrid Node 的 Cilium agent 都会读取此配置，并将 gateway IP 注册为 remote VTEP (VXLAN Tunnel Endpoint)。这让 Cilium 知道应将发往 VPC 的流量发送到哪里——通过 gateway 的 VXLAN tunnel，而不是尝试直接路由；如果没有可路由的 Pod CIDRs，直接路由会失败。

</details>

---

4. 使用 Hybrid Nodes Gateway 的 CNI 前提条件是什么？
   - A) cloud nodes 和 Hybrid Nodes 上都可以使用任意 CNI
   - B) cloud nodes 上使用 Cilium，Hybrid Nodes 上使用 VPC CNI
   - C) Hybrid Nodes 上使用 Cilium（启用 VTEP），cloud nodes 上使用 VPC CNI
   - D) cloud nodes 和 Hybrid Nodes 上都使用 VPC CNI

<details>
<summary>显示答案</summary>

**答案：C) Hybrid Nodes 上使用 Cilium（启用 VTEP），cloud nodes 上使用 VPC CNI**

**解释：**
gateway 需要：(1) 在 Hybrid Nodes 上使用 EKS 版本的 Cilium 作为 CNI，并启用 VTEP support，以便 Hybrid Nodes 可以参与 VXLAN tunneling。(2) 在 cloud nodes 上使用 AWS VPC CNI，因为 gateway 依赖 VPC-native routing 在 VPC 与 VXLAN tunnel 之间转发流量。两个 CNIs 通过 gateway 协同工作，以实现无缝的 Pod-to-Pod 通信。

</details>

---

5. gateway 使用什么 VXLAN 配置？
   - A) UDP port 4789 上的 VNI 1（标准 VXLAN）
   - B) UDP port 8472 上的 VNI 2（Cilium 默认）
   - C) UDP port 6081 上的 VNI 100（Geneve）
   - D) UDP port 443 上的 VNI 0（HTTPS encapsulation）

<details>
<summary>显示答案</summary>

**答案：B) UDP port 8472 上的 VNI 2（Cilium 默认）**

**解释：**
gateway 创建一个名为 `hybrid_vxlan0` 的 VXLAN interface，其 VNI (VXLAN Network Identifier) 为 2，使用 UDP port 8472，这是 Cilium 默认的 VXLAN port。它通过在 VXLAN interface 上编写 FDB (Forwarding Database) 条目、ARP 条目和 routes，建立到每个 Hybrid Node 的 tunnel。Security groups 和本地 firewalls 必须允许 UDP 8472 双向通信。

</details>

---

6. gateway 如何管理 VPC routing？
   - A) 它使用 BGP 将 Pod routes 通告给 VPC router
   - B) 它自动创建并维护 VPC route table 条目，将 Hybrid Pod CIDRs 指向 active gateway 的 primary ENI
   - C) 它修改 VPC 的 main route table 以添加 NAT rules
   - D) 它配置 Transit Gateway route tables

<details>
<summary>显示答案</summary>

**答案：B) 它自动创建并维护 VPC route table 条目，将 Hybrid Pod CIDRs 指向 active gateway 的 primary ENI**

**解释：**
gateway 的 node controller 监视 CiliumNode objects，并在 Hybrid Nodes 加入或离开时自动添加或删除 VXLAN tunnels。leader Pod 维护 VPC route table 条目，将每个 Hybrid Pod CIDR 路由到 active gateway instance 的 primary ENI。这就是 gateway 的 IAM role 需要 ec2:DescribeRouteTables、ec2:CreateRoute 和 ec2:ReplaceRoute 权限的原因。

</details>

---

7. EKS Hybrid Nodes Gateway 的定价模型是什么？
   - A) 根据处理的数据量按小时收费
   - B) 包含在 EKS Hybrid Nodes 定价中，按每个 Hybrid Node 每小时 $0.10 收费
   - C) gateway 本身不额外收费，但会产生 gateway nodes 的 EC2 instance costs
   - D) 前 3 个月免费，之后按标准 AWS networking charges 收费

<details>
<summary>显示答案</summary>

**答案：C) gateway 本身不额外收费，但会产生 gateway nodes 的 EC2 instance costs**

**解释：**
EKS Hybrid Nodes Gateway 不额外收费，并且是开源的（可在 GitHub 上获取）。不过，由于 gateway 运行在你 VPC 中的 EC2 instances 上，因此你需要为 gateway nodes 支付标准 EC2 instance costs。相比手动管理复杂的 BGP 或 static routing infrastructure，这使其成为一种高性价比的解决方案。

</details>

---

8. 什么时候应该选择 gateway 方案，而不是手动 Pod routing（BGP/static routes）？
   - A) 当你需要 cloud 和本地 Pods 之间尽可能低的延迟时
   - B) 当你希望简化运维并避免让本地 Pod networks 可路由，同时启用 webhook 通信和 AWS service 集成时
   - C) 当你拥有超过 1000 个 Hybrid Nodes 时
   - D) 当 Hybrid Nodes 上使用非 Cilium CNI 时

<details>
<summary>显示答案</summary>

**答案：B) 当你希望简化运维并避免让本地 Pod networks 可路由，同时启用 webhook 通信和 AWS service 集成时**

**解释：**
当你希望避免复杂的 network infrastructure 变更（BGP configuration、static route management）时，gateway 是理想选择。它会自动启用：(1) control plane 到 Hybrid Nodes 上 webhook 的通信，(2) cloud 与本地之间的 Pod-to-Pod 流量，(3) AWS service connectivity（ALB、NLB、Prometheus）到 Hybrid Pods。当你已经拥有 BGP infrastructure，或需要尽量减少通过 gateway 带来的额外 hop 时，手动 BGP 方案可能仍然更适合。

</details>
