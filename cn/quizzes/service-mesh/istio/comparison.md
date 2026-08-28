# Istio 对比测验

> **支持的版本**: Istio 1.30 / EKS 1.36
> **最后更新**: August 21, 2026

本测验检验你对 sidecar 与 ambient 模式选择标准的理解，尤其是 EKS 1.36 测试结果。

## 选择题（1-6）

### 问题 1：ambient waypoint 503 的根本原因

在 ambient 模式中，发布期间 waypoint 路径上间歇性出现 503 的根本原因是什么？

A. Pod 重启时发生重复 IP 分配
B. waypoint 会复用以目标 IP:Port 为键的连接，而当 Pod 终止时 ztunnel 不会通知 waypoint
C. NetworkPolicy 阻止了 waypoint 流量
D. waypoint 不支持 STRICT mTLS

<details>
<summary>答案与说明</summary>

**答案：B**

**说明：**

waypoint（Envoy）管理并复用一个以目标 IP:Port 为键的连接池。当目标 Pod 终止时，ztunnel 不会显式通知 waypoint。如果已终止 Pod 的 IP 被重新分配给新的 Pod，waypoint 可能会复用一个现已失效的连接并返回 503。这正是该问题背后的机制——**连接生命周期管理**，而非重复 IP 分配——§4 中测得的 503 比率也与此一致。

**参考资料：**
- [Sidecar 与 Ambient 模式选择指南](../../../service-mesh/istio/comparison/03-sidecar-vs-ambient.md)
- [Ambient 模式：Waypoint Proxy](../../../service-mesh/istio/advanced/01-ambient-mode.md)

</details>

---

### 问题 2：解读 EKS 1.36 测试结果

在一个专用单租户 EKS 1.36 集群上，以 100 qps x 600s（60,000 次请求）的负载进行重复发布时，sidecar 的 503 比率为 0.5%，ambient-L4（无 waypoint）没有实际 503（但有 0.3% 的 TCP 错误），而 ambient-L7（有 waypoint）的 503 比率为 2.6%。正确的解读是什么？

A. Ambient 始终比 sidecar 更稳定
B. 通过 waypoint 路由会产生比 sidecar 更高的 503 比率，但仅使用 L4（无 waypoint）则不会产生实际 503
C. ambient-L4 的 TCP 错误（0.3%）与 waypoint 的 503 是同一种现象
D. socket 使用量最低的模式最稳定

<details>
<summary>答案与说明</summary>

**答案：B**

**说明：**

数据表明，“ambient”并非普遍优于或劣于 sidecar——流量是否经过 **waypoint** 才是决定变量。Ambient-L7（有 waypoint）的 503 比率约为 sidecar 的 5 倍（2.6% 对 0.5%），而 ambient-L4（无 waypoint）没有实际 503。不过，这并不意味着 ambient-L4 没有故障——它反而暴露了不同的故障模式：TCP 层连接中断（0.3%），这不同于 waypoint 将请求转发到失效连接并返回 503 的情况（因此 C 不正确）。Socket 使用量并非稳定性指标，只是衡量连接重新建立频率的代理指标（因此 D 不正确）——事实上，ambient-L4 消耗的 socket *最多*，却没有 503。

**参考资料：**
- [Sidecar 与 Ambient 模式选择指南：零停机发布结果](../../../service-mesh/istio/comparison/03-sidecar-vs-ambient.md)

</details>

---

### 问题 3：NetworkPolicy 与 ambient

在使用基于端口的 NetworkPolicy 的集群中，流量无法到达 ambient 模式的 Pod。应用程序监听端口 8080。最可能的原因和修复方法是什么？

A. Ambient 不支持 NetworkPolicy，因此应移除 NetworkPolicy
B. 实际流量通过 HBONE 隧道（TCP 15008）到达，因此 NetworkPolicy 需要为 15008 添加入站允许规则
C. 应将 PeerAuthentication 改为 PERMISSIVE
D. 需要重启 istio-cni DaemonSet

<details>
<summary>答案与说明</summary>

**答案：B**

**说明：**

在 ambient 模式中，ztunnel 将 Pod 流量封装在 HBONE（mTLS）隧道中，并通过端口 15008 传输。仅允许应用程序端口（8080）的 NetworkPolicy 会阻止实际到达的 15008 流量。修复方法是在目标 Pod 上添加针对 TCP 15008 的入站允许规则。Sidecar 不需要此额外规则，因为 sidecar 与应用程序共享相同的 Pod 网络命名空间。

**参考资料：**
- [Sidecar 与 Ambient 模式选择指南：NetworkPolicy](../../../service-mesh/istio/comparison/03-sidecar-vs-ambient.md)

</details>

---

### 问题 4：非幂等 API 与重试策略

为什么建议默认不要在订单创建等非幂等 API 路径上启用网格级重试（例如 waypoint 重试、VirtualService 重试）？

A. 重试会增加过多 CPU 开销
B. 当 waypoint 将请求转发到失效连接并返回 503 时，重试可能会重新执行已在服务器端完成的请求，从而导致重复执行（例如重复下单）
C. 重试与 STRICT mTLS 不兼容
D. Ambient 模式不支持重试

<details>
<summary>答案与说明</summary>

**答案：B**

**说明：**

503 是客户端可见的故障，但该故障类别中隐藏着请求实际上已到达服务器并完成处理的情况——由于连接中断与应用程序完成工作之间的竞争，只有*响应*丢失。在这种情况下，网格重试会通过另一条连接重新发送相同的逻辑请求；如果服务器无法保证幂等性，该请求会被处理两次。对于订单创建等不可逆操作，这种风险尤其严重，因此默认不启用重试并单独验证会更安全。后续测试（T2）在 sidecar 和 ambient-L7 waypoint 重试中都进行了 300s 的持续发布扰动，且该次运行中未发现重复执行——这降低了该竞争条件*常见*的可能性，但并不能证明其*安全*，因为它需要非常狭窄的时间窗口，而更长时间或更高吞吐量的测试仍可能捕获它。

**参考资料：**
- [Sidecar 与 Ambient 模式选择指南：作为缓解措施的重试风险](../../../service-mesh/istio/comparison/03-sidecar-vs-ambient.md)

</details>

---

### 问题 5：公平比较 sidecar 与 ambient 发布

在发布测试中，sidecar 产生的客户端可见 503 少于 ambient。哪种实验最能确定这是否反映了其数据平面本质上更加稳定？

A. 仅发送 GET 请求，并比较最终的 200 计数
B. 保留 sidecar 上的默认重试，但禁用 ambient 上的重试
C. 在两种模式中都将写入路由重试设为 `attempts: 0`，并分别记录原始 HTTP/TCP 故障、重试计数和最终结果
D. 将平均 CPU 使用量较低的模式视为更稳定

<details>
<summary>答案与说明</summary>

**答案：C**

**说明：**

Sidecar Envoy 和 waypoint Envoy 可通过 L7 重试向客户端隐藏原始故障，而 ztunnel 是 L4 proxy，无法解释 HTTP 503 或重放 HTTP 请求。等效地禁用写入重试，并分别记录 HTTP 503、TCP reset/EOF、`upstream_rq_retry`、实际的 upstream 交付以及最终客户端结果。否则，测试无法区分“发生的故障较少”和“重试隐藏了更多故障”。

**参考资料：**
- [Sidecar 与 Ambient 模式选择指南：原始故障测量](../../../service-mesh/istio/comparison/03-sidecar-vs-ambient.md)
- [重试与超时](../../../service-mesh/istio/traffic-management/05-retry-timeout.md)

</details>

---

### 问题 6：Cilium 身份验证与加密

对于已建立且 mutual authentication 设置为 `required` 的 Cilium 数据平面，以下哪项陈述是正确的？

A. 每个应用程序负载都会自动使用 workload TLS 加密
B. Endpoint 身份验证与负载加密是相互独立的；机密性需要 WireGuard/IPsec 或受支持的原生 ztunnel mTLS
C. 它在实现、成熟度和运维语义上与 Istio `PeerAuthentication STRICT` 完全相同
D. 启用 mutual authentication 后便不再需要 CiliumNetworkPolicy

<details>
<summary>答案与说明</summary>

**答案：B**

**说明：**

已建立的 Cilium mutual authentication 通过独立于应用程序数据路径的带外握手验证对等方身份。仅凭身份验证策略不会自动加密负载，因此请单独选择 WireGuard/IPsec，或在受支持的平台上验证原生 ztunnel mTLS 预览版。应分别评估身份授权、对等身份验证和传输中加密，而不是将结果视为与 Istio `STRICT` workload mTLS 相同。

**参考资料：**
- [Cilium Service Mesh 安全性](../../../service-mesh/cilium-service-mesh/03-security.md)

</details>

---

## 评分

- 统计你答对了 6 道题中的几道。
- 6/6：你能够基于实测证据解释 sidecar、ambient 和 Cilium 的选择，以及重试风险。
- 4-5/6：复习原始故障测量或身份验证与加密之间的区别。
- 0-3/6：从头重新阅读[Sidecar 与 Ambient 模式选择指南](../../../service-mesh/istio/comparison/03-sidecar-vs-ambient.md)。

## 学习资源

- [Sidecar 与 Ambient 模式选择指南](../../../service-mesh/istio/comparison/03-sidecar-vs-ambient.md)
- [Ambient 模式](../../../service-mesh/istio/advanced/01-ambient-mode.md)
- [mTLS](../../../service-mesh/istio/security/01-mtls.md)
- [Cilium Service Mesh 安全性](../../../service-mesh/cilium-service-mesh/03-security.md)
