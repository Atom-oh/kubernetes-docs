# Cilium 服务网格架构测验

基于 Cilium 1.20.3 审核。有关配置、资格要求和主要参考资料，请阅读[架构指南](../../../service-mesh/cilium-service-mesh/01-architecture.md)。

### 1. Cilium 架构的一个特点是什么？

- **A.** 它取代 Kubernetes API server
- **B.** 它将 eBPF L3/L4 处理与用于适用 L7 流量的 Envoy 相结合
- **C.** 它通过每个 Pod 的 Envoy 发送所有数据包
- **D.** 它无法使用 Kubernetes 资源

<details>
<summary>显示答案</summary>

**答案：B. 它将 eBPF L3/L4 处理与用于适用 L7 流量的 Envoy 相结合**

Cilium 使用 eBPF 实现网络功能和 L3/L4 策略。适用的 L7 功能使用 Envoy，可由 Agent 管理，也可运行在独立的 DaemonSet 中。这描述的是组件部署位置，并不代表普遍适用的性能结果。

</details>

### 2. 以下哪项不是用于描述 Cilium 数据路径的内核挂载机制？

- **A.** TC/TCX
- **B.** cgroup socket hooks
- **C.** 应用程序的 HTTP handler
- **D.** XDP

<details>
<summary>显示答案</summary>

**答案：C. 应用程序的 HTTP handler**

HTTP handler 是应用程序代码，不是内核钩子。Cilium 可以使用 TC/TCX 和 cgroup hooks；XDP 加速需要适当的配置/设备。存在 eBPF 并不意味着这些钩子会在每个数据包上运行。

</details>

### 3. 在节点范围内共享 Envoy 进程意味着什么？

- **A.** 每个节点恰好占用 100 MB 内存
- **B.** 请求延迟保证为 0.1 ms
- **C.** 共享代理生命周期/资源/故障边界，需要根据工作负载进行容量规划
- **D.** 无需配置加密

<details>
<summary>显示答案</summary>

**答案：C. 共享代理生命周期/资源/故障边界，需要根据工作负载进行容量规划**

与每个 Pod 都运行 sidecar 相比，共享方式可以减少代理实例数量，但总资源使用量还包括 Agent、映射、控制平面和可选组件。实际开销取决于节点数量、流量、策略和功能；过去关于固定 5 GB 与 500 MB 的对比并非测量结果。

</details>

### 4. CiliumEnvoyConfig 定义什么？

- **A.** 仅 Pod 调度
- **B.** 命名空间范围的低级 Envoy 资源，以及关联的 Service 流量重定向/后端同步
- **C.** 所有 CiliumEndpoint 的替代品
- **D.** 只要 kubectl apply 成功，就一定会被接受的通用配置

<details>
<summary>显示答案</summary>

**答案：B. 命名空间范围的低级 Envoy 资源，以及关联的 Service 流量重定向/后端同步**

CEC 将 Kubernetes Service 与 Envoy Listener、Route 和 Cluster 关联起来。Cilium 可以分配未指定的 listener 地址，并填充 xDS 源。Kubernetes 不会验证所有内嵌的 Envoy 字段，因此仍需检查配置是否被接受以及运行时行为。CCEC 的作用范围是集群级别，但它不会将“*”变成 Service 通配符。

</details>

### 5. 关于 Maglev，哪项说法正确？

- **A.** 它是 HTTP cookie 解析器
- **B.** 它取代 Kubernetes ClientIP 会话亲和性
- **C.** 它为适用的外部流量提供一致的后端选择，与会话亲和性相互独立
- **D.** 它保证已移除的后端继续处理旧连接

<details>
<summary>显示答案</summary>

**答案：C. 它为适用的外部流量提供一致的后端选择，与会话亲和性相互独立**

对于适用的南北向负载均衡，Maglev 会将流一致地映射到后端。文档所述的 socket 级东西向路径不使用 Maglev。ClientIP 亲和性和连接跟踪是不同的机制；Maglev 无法使不可用的后端继续运行。

</details>

### 6. Cilium 如何分配工作负载安全身份？

- **A.** 它始终与 Pod IP 相同
- **B.** Cilium 会为一组与身份相关的标签分配一个数字 ID；多个 Pod 可以共用该 ID
- **C.** 用户计算标签哈希并创建一个猜测出来的 CiliumIdentity
- **D.** 每个 Pod 都有一个永久不变的全局数字身份

<details>
<summary>显示答案</summary>

**答案：B. Cilium 会为一组与身份相关的标签分配一个数字 ID；多个 Pod 可以共用该 ID**

与身份相关的标签可以包括命名空间、service account 和选定的工作负载标签。分配器会将标签集解析为一个 ID；它既不是用户计算出来的哈希值，也不一定是每个 Pod 唯一的。请检查 CiliumEndpoint/CiliumIdentity 和 Agent 的 cilium-dbg identity list。

</details>

### 7. 哪些流量可能使用 Envoy？

- **A.** 在任何配置下的每个数据包
- **B.** HTTP L7 策略流量，以及由受支持的 Service/Ingress/Gateway 配置重定向的流量
- **C.** 仅包含 CiliumNetworkPolicy HTTP 规则的流，Gateway 流量绝不会使用
- **D.** 除非每个 Pod 都有 Envoy sidecar，否则没有任何流量会使用

<details>
<summary>显示答案</summary>

**答案：B. HTTP L7 策略流量，以及由受支持的 Service/Ingress/Gateway 配置重定向的流量**

HTTP 策略会将相应的入站或出站流量重定向到 Envoy。CEC Service 负载均衡以及 Gateway/Ingress 也可能需要 Envoy。经代理的请求，其响应会使用已建立的代理连接；这并不是针对每个响应单独进行的可选重定向。

</details>

### 8. Cilium 的 BPF 连接跟踪有什么用途？

- **A.** 取代 Kubernetes API
- **B.** 维护流状态并识别返回流量，同时执行策略检查
- **C.** 永久缓存首次允许决定，并将其应用于之后的所有数据包
- **D.** 存储 HTTP 应用程序凭据

<details>
<summary>显示答案</summary>

**答案：B. 维护流状态并识别返回流量，同时执行策略检查**

CT maps 会跟踪流状态、生命周期以及转换/代理元数据。已发布的 endpoint 数据路径会针对新建流量和已建立连接的发起方向流量检查策略，但有明确列出的例外情况，并会以有状态方式处理已识别的回复流量。CT 缓存并不意味着策略执行可以一概豁免。

</details>

### 9. CiliumClusterwideNetworkPolicy 与 CiliumNetworkPolicy 有什么区别？

- **A.** 它们的 Kubernetes 资源作用范围相同
- **B.** CCNP 的作用范围是集群级别，而 CNP 的作用范围是命名空间级别；受影响的 endpoint 仍由选择器决定
- **C.** 只有 CNP 能表达任何 L7 规则
- **D.** 每个 CCNP 都必然拒绝所有命名空间中的流量

<details>
<summary>显示答案</summary>

**答案：B. CCNP 的作用范围是集群级别，而 CNP 的作用范围是命名空间级别；受影响的 endpoint 仍由选择器决定**

两者都支持适用的 L7 策略规则。资源作用范围与 endpoint 选择是不同的概念：集群级别的资源不会自动选择或拒绝所有工作负载。其他适用策略的允许规则也同样重要。

</details>

### 10. Cilium beta 版带外双向身份验证的默认 SPIFFE ID 格式是什么？

- **A.** urn:spiffe:cluster/namespace/pod
- **B.** `spiffe://spiffe.cilium/identity/<numeric-security-identity>`
- **C.** `spiffe://cluster.local/ns/<namespace>/sa/<service-account>`，适用于每个 Cilium 安装
- **D.** `https://spiffe.io/id/<pod-name>`

<details>
<summary>显示答案</summary>

**答案：B. `spiffe://spiffe.cilium/identity/<numeric-security-identity>`**

Cilium 已发布的 SPIRE provider 会在其配置的 trust domain 下构造 `/identity/<numeric-id>` 路径，默认值为 spiffe.cilium。Agent 代表 Cilium 安全身份运行。身份验证交换在带外进行；应用程序加密需要单独配置 WireGuard/IPsec。带外功能仍处于 beta 阶段/尚未完善。独立的 ztunnel 加密 beta 使用不同的工作负载身份模型；此答案并不描述其证书路径。

</details>

### 11. 以下哪项不是 Cilium Agent 的职责？

- **A.** 管理本地 eBPF 程序和映射
- **B.** 管理本地策略和 Envoy 配置
- **C.** 充当 Kubernetes API server
- **D.** 管理本地 endpoint 和身份相关内容

<details>
<summary>显示答案</summary>

**答案：C. 充当 Kubernetes API server**

Agent 在节点上运行；Kubernetes API server 仍是独立的控制平面组件。Cilium Operator 是独立的 Deployment，负责身份垃圾回收和相关 IPAM 操作等集群级任务。

</details>

### 12. 关于同节点 Pod 流量，哪项说法准确？

- **A.** 它必须始终离开节点
- **B.** 满足条件时，合适的 BPF 主机路由路径可以绕过主机网络栈的上层；但实际路径取决于配置
- **C.** 始终会绕过所有 Linux 和 Pod 网络栈
- **D.** 其延迟保证为 0.1 ms

<details>
<summary>显示答案</summary>

**答案：B. 满足条件时，合适的 BPF 主机路由路径可以绕过主机网络栈的上层；但实际路径取决于配置**

满足要求时，BPF 主机路由可以绕过主机网络栈的上层/netfilter。Pod 协议栈仍然存在。传统路由、endpoint 设备模式、L7 策略和集成组件都会改变路径；延迟需要通过测量确定。

</details>
