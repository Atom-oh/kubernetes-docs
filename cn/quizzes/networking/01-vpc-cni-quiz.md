# Amazon VPC CNI 测验

以下问题用于测试您对 Amazon VPC CNI 的理解。

---

1. IPAMD（L-IPAM Daemon）在 VPC CNI 中的主要作用是什么？
   - A) 管理 Pod DNS 设置
   - B) 预分配和管理 ENI 及 IP 地址
   - C) 应用 Network Policy
   - D) 加密节点间流量

<details>
<summary>显示答案</summary>

**答案：B) 预分配和管理 ENI 及 IP 地址**

**说明：**
IPAMD（L-IPAM Daemon）是在每个节点上运行的守护进程，负责管理 ENI（Elastic Network Interfaces）并预分配 IP 地址，以便在创建 Pod 时能够快速分配 IP。CNI Binary 由 kubelet 调用，从 IPAMD 接收 IP，并设置 Pod 网络命名空间。

</details>

---

2. Secondary IP 模式与 Prefix Delegation 模式的关键区别是什么？
   - A) Secondary IP 仅支持 IPv6，Prefix Delegation 仅支持 IPv4
   - B) Secondary IP 分配单个 IP，Prefix Delegation 分配 /28 前缀（16 个 IP）
   - C) Secondary IP 仅适用于 EKS，Prefix Delegation 仅适用于自管理集群
   - D) Secondary IP 使用覆盖网络，Prefix Delegation 使用直接路由

<details>
<summary>显示答案</summary>

**答案：B) Secondary IP 分配单个 IP，Prefix Delegation 分配 /28 前缀（16 个 IP）**

**说明：**
Secondary IP 模式会逐个向每个 ENI 分配单独的 IP 地址，而 Prefix Delegation 模式会一次分配 /28 IPv4 前缀（16 个 IP）。这使得每个节点可以运行更多 Pod，同时也提高了 IP 分配速度。

</details>

---

3. 为什么使用 VPC CNI 时，m5.large 实例的最大 Pod 数为 29？
   - A) 因为 Kubernetes 的默认限制是 29
   - B) 最多 3 个 ENI × 每个 ENI 10 个 IP = 30，减去用于 Primary IP 的 ENI 数量（3）
   - C) 受 AWS 软限制约束
   - D) 受 VPC 子网大小约束

<details>
<summary>显示答案</summary>

**答案：B) 最多 3 个 ENI × 每个 ENI 10 个 IP = 30，减去用于 Primary IP 的 ENI 数量（3）**

**说明：**
VPC CNI 中的最大 Pod 数计算方式为（ENI 数量 × 每个 ENI 的 IP 数）- ENI 数量。m5.large 最多支持 3 个 ENI，每个 ENI 有 10 个 IPv4 地址。由于每个 ENI 的 Primary IP 被节点使用，因此 (3 × 10) - 3 = 27。实际数量可能因 host networking Pod 和其他因素而略有不同。

</details>

---

4. WARM_IP_TARGET 环境变量的用途是什么？
   - A) 设置可分配给 Pod 的最大 IP 数量
   - B) 设置每个节点上要预分配的备用 IP 数量
   - C) 限制整个集群的 IP 总数
   - D) 设置 IP 地址的 TTL（Time To Live）

<details>
<summary>显示答案</summary>

**答案：B) 设置每个节点上要预分配的备用 IP 数量**

**说明：**
WARM_IP_TARGET 控制 IPAMD 在每个节点上预分配的备用 IP 数量。这确保了创建新 Pod 时可以立即获得 IP。较大的值会加快 Pod 启动速度，但会使用更多 IP；较小的值可提高 IP 使用效率，但可能会减慢 Pod 启动速度。

</details>

---

5. 关于 VPC CNI 原生 Network Policy 支持的哪项说法是正确的？
   - A) 它在内部使用 Calico 来实施 Network Policy
   - B) 从 v1.14 开始，它支持原生的基于 eBPF 的 Network Policy
   - C) EKS 不支持 Network Policy
   - D) 它使用 iptables 来实施 Network Policy

<details>
<summary>显示答案</summary>

**答案：B) 从 v1.14 开始，它支持原生的基于 eBPF 的 Network Policy**

**说明：**
从 VPC CNI v1.14 开始，支持基于 eBPF 的原生 Kubernetes Network Policy。此前需要使用如 Calico 这样的独立 Network Policy 引擎，但现在 VPC CNI 本身可以处理标准 Kubernetes NetworkPolicy 资源。

</details>

---

6. 使用 Custom Networking（ENIConfig）的主要目的是什么？
   - A) 自定义 Pod DNS 服务器设置
   - B) 从与节点不同的子网为 Pod 分配 IP
   - C) 安装自定义 CNI 插件
   - D) 重命名节点的网络接口

<details>
<summary>显示答案</summary>

**答案：B) 从与节点不同的子网为 Pod 分配 IP**

**说明：**
Custom Networking 使用 ENIConfig CRD 从与节点不同的子网为 Pod 分配 IP。当节点子网的 IP 不足、需要对 Pod 应用不同的 Security Group，或需要隔离节点与 Pod 网络时，这会很有用。它通常与 Secondary CIDR 一起使用（例如 100.64.0.0/16）。

</details>

---

7. 在 per-Pod Security Group 功能中，Trunk ENI 和 Branch ENI 的作用是什么？
   - A) Trunk ENI 处理外部流量，Branch ENI 处理内部流量
   - B) Trunk ENI 是承载 Branch ENI 的节点主 ENI，Branch ENI 是分配给每个 Pod 的虚拟 ENI
   - C) Trunk ENI 用于 IPv4，Branch ENI 用于 IPv6
   - D) Trunk ENI 和 Branch ENI 执行相同的作用

<details>
<summary>显示答案</summary>

**答案：B) Trunk ENI 是承载 Branch ENI 的节点主 ENI，Branch ENI 是分配给每个 Pod 的虚拟 ENI**

**说明：**
per-Pod Security Group 使用 Trunk/Branch ENI 架构。Trunk ENI 是附加到节点上的主 ENI，可承载多个 Branch ENI。Branch ENI 是分配给每个 Pod 的虚拟网络接口，从而能够独立实施 AWS Security Group。这可在 Pod 级别实现精细的网络安全控制。

</details>

---

8. 以下哪项不是解决 IP 耗尽问题的有效方案？
   - A) 启用 Prefix Delegation
   - B) 添加 Secondary CIDR
   - C) 将所有 Pod 切换为 host network 模式
   - D) 使用带有专用 Pod 子网的 Custom Networking

<details>
<summary>显示答案</summary>

**答案：C) 将所有 Pod 切换为 host network 模式**

**说明：**
以 host network 模式运行所有 Pod（`hostNetwork: true`）在技术上可以解决 IP 分配问题，但会消除 Pod 之间的网络隔离，并可能导致端口冲突，因此并非实用的解决方案。IP 耗尽的适当解决方案包括启用 Prefix Delegation、添加 Secondary CIDR、使用 Custom Networking 以及调整 WARM_IP_TARGET。

</details>
