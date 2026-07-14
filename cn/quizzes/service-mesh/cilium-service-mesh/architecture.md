# Cilium Service Mesh 架构测验

本测验用于测试您对 Cilium Service Mesh 架构、eBPF 数据路径、node Envoy proxy 和 CRD 模型的理解。

## 测验题目

### 1. Cilium Service Mesh 与传统基于 sidecar 的 Service Mesh 之间的关键区别是什么？

A. 非 Kubernetes 原生
B. 使用 eBPF 在内核层处理 L3/L4 流量
C. 在 user space 处理所有流量
D. 每个 Pod 使用多个 proxy

<details>
<summary>显示答案</summary>

**答案：B. 使用 eBPF 在内核层处理 L3/L4 流量**

**说明：**
Cilium Service Mesh 使用 eBPF（extended Berkeley Packet Filter）直接在 Linux 内核中处理 L3/L4 流量。这与通过 user-space sidecar proxy 处理所有流量的传统 Service Mesh 有根本区别。仅当需要 L7 处理时，流量才会被转发到每个 node 共享的 Envoy proxy。

</details>

### 2. 以下哪一项不是 Cilium 程序可执行的 eBPF hook point？

A. XDP (eXpress Data Path)
B. TC (Traffic Control)
C. 应用层
D. cgroup

<details>
<summary>显示答案</summary>

**答案：C. 应用层**

**说明：**
eBPF 程序在内核层运行，主要 hook point 包括 XDP（NIC 驱动程序）、TC（网络栈入口）、Socket Operations（socket 层）和 cgroup（进程组）。应用层位于 user space，因此不是 eBPF hook point。

</details>

### 3. Cilium 的每个 node 一个 Envoy proxy 模型有什么优势？

A. 可以实现更复杂的配置
B. 增加每个 Pod 的内存使用量
C. 资源效率和低延迟
D. 无法加密所有流量

<details>
<summary>显示答案</summary>

**答案：C. 资源效率和低延迟**

**说明：**
每个 node 使用一个 Envoy proxy 比为每个 Pod 部署 sidecar 使用的内存显著更少。在一个有 100 个 Pod 的 cluster 中，Istio 使用约 5GB（每个 Pod 50MB），而 Cilium 仅使用约 500MB（每个 node 100MB）。此外，L3/L4 流量直接在 eBPF 中处理，显著降低延迟。

</details>

### 4. CiliumEnvoyConfig CRD 的主要用途是什么？

A. 定义 Kubernetes network policy
B. 为特定 Service 定义 Envoy proxy 配置
C. 定义 Pod 调度规则
D. 定义存储类

<details>
<summary>显示答案</summary>

**答案：B. 为特定 Service 定义 Envoy proxy 配置**

**说明：**
CiliumEnvoyConfig 是一个 namespace-scoped CRD，用于为特定 Service 定义 Envoy proxy 设置（listener、route、cluster 等）。这使得可以配置 HTTP 路由、header 操作和负载均衡等 L7 功能。

</details>

### 5. 当 Cilium 替换 kube-proxy 时，哪种负载均衡算法提供一致性哈希？

A. Random
B. Round Robin
C. Maglev
D. Least Connection

<details>
<summary>显示答案</summary>

**答案：C. Maglev**

**说明：**
Maglev 是由 Google 开发的一致性哈希算法，用于 Cilium 基于 eBPF 的 load balancer。即使 backend 发生变化，该算法也能提供 session affinity，从而维持大多数现有连接。它以 O(1) 查找时间提供高性能。

</details>

### 6. 关于 Cilium Identity，哪项说法正确？

A. 基于 IP 地址识别 workload
B. 通过哈希 Pod label 生成数字 ID
C. 使用 MAC 地址进行识别
D. 必须由用户手动分配

<details>
<summary>显示答案</summary>

**答案：B. 通过哈希 Pod label 生成数字 ID**

**说明：**
Cilium Identity 通过哈希 Pod label（namespace、service account、用户定义的 label 等）生成唯一的数字 ID。基于 ID 的方法的优势在于，当 IP 地址发生变化时，policy 不会受到影响。

</details>

### 7. 在 Cilium 中应用 L7 policy 时，流量会发生什么变化？

A. 所有流量始终通过 Envoy
B. 只有具有 L7 policy 的流量会被重定向到 Envoy
C. 完全绕过 Envoy
D. 流量被丢弃

<details>
<summary>显示答案</summary>

**答案：B. 只有具有 L7 policy 的流量会被重定向到 Envoy**

**说明：**
为了提高效率，Cilium 仅将具有 L7 policy 的流量重定向到 node Envoy proxy。仅具有 L3/L4 policy 或没有 policy 的流量会直接在 eBPF 中处理，并在内核中快速转发。

</details>

### 8. Cilium 的连接跟踪在哪里执行？

A. user space 中的 conntrack daemon
B. eBPF maps
C. Envoy proxy
D. Kubernetes API server

<details>
<summary>显示答案</summary>

**答案：B. eBPF maps**

**说明：**
Cilium 使用 eBPF maps 进行连接跟踪。CT（Connection Tracking）maps 在内核中存储和查找连接状态，从而为现有连接缓存并快速应用 policy 决策。

</details>

### 9. CiliumClusterwideNetworkPolicy 和 CiliumNetworkPolicy 之间有什么区别？

A. 两者具有相同的 scope
B. CiliumClusterwideNetworkPolicy 在整个 cluster 中生效
C. CiliumNetworkPolicy 具有更多功能
D. CiliumClusterwideNetworkPolicy 不支持 L7 policy

<details>
<summary>显示答案</summary>

**答案：B. CiliumClusterwideNetworkPolicy 在整个 cluster 中生效**

**说明：**
CiliumNetworkPolicy 是 namespace-scoped，而 CiliumClusterwideNetworkPolicy 是 cluster-wide scoped。cluster-wide policy 适用于默认拒绝 policy，或必须应用于所有 namespace 的安全规则。两个 CRD 都支持 L7 policy。

</details>

### 10. Cilium Service Mesh 中使用的 SPIFFE ID 的格式是什么？

A. urn:spiffe:cluster/namespace/pod
B. spiffe://cluster.local/ns/\<namespace\>/sa/\<service-account\>
C. https://spiffe.io/id/\<pod-name\>
D. spiffe:\<namespace\>:\<pod-name\>

<details>
<summary>显示答案</summary>

**答案：B. spiffe://cluster.local/ns/\<namespace\>/sa/\<service-account\>**

**说明：**
SPIFFE（Secure Production Identity Framework for Everyone）ID 是 workload 的唯一标识符。在 Cilium Service Mesh 中与 SPIRE 集成时，每个 workload 都会获得格式为 `spiffe://cluster.local/ns/<namespace>/sa/<service-account>` 的 SPIFFE ID。此 ID 用于 mTLS 身份验证。

</details>

### 11. 以下哪一项不是 Cilium Agent 的职责？

A. eBPF program 管理
B. Envoy 配置生成和同步
C. Kubernetes API server 职责
D. Identity 管理

<details>
<summary>显示答案</summary>

**答案：C. Kubernetes API server 职责**

**说明：**
Cilium Agent 在每个 node 上运行，负责 eBPF program 管理、policy 编译、Envoy 配置生成/同步、Identity 管理、endpoint 管理和 flow logging。Kubernetes API server 是 Kubernetes control plane 的一部分，与 Cilium 相互独立。

</details>

### 12. 对于同一 node 上的 Pod-to-Pod 通信，Cilium 提供了什么优化？

A. 始终通过外部网络路由
B. 通过 eBPF 绕过 network stack 的直接内核路径
C. 将所有流量转发到 Envoy
D. 无法通信

<details>
<summary>显示答案</summary>

**答案：B. 通过 eBPF 绕过 network stack 的直接内核路径**

**说明：**
对于同一 node 上的 Pod-to-Pod 通信，Cilium 使用 eBPF 通过直接内核路径转发流量。这会绕过整个 Linux network stack，从而实现极低延迟（~0.1ms）。

</details>
