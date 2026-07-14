# 对比测验

> **支持的版本**: Istio 1.30 / EKS 1.36 **最后更新**: July 7, 2026

本测验测试您对 sidecar 与 ambient mode 选择标准的理解，尤其是 EKS 1.36 测试结果。

## 多项选择题（1-4）

### 问题 1：ambient waypoint 503 的根本原因

ambient mode 在滚动发布期间，waypoint 路径上间歇性出现 503 的根本原因是什么？

A. Pod 重启时分配了重复的 IP B. waypoint 会复用以目标 IP:Port 为键的连接，而 ztunnel 不会在 Pod 终止时通知 waypoint C. NetworkPolicy 阻止了 waypoint 流量 D. waypoint 不支持 STRICT mTLS

<details>

<summary>答案 &#x26; 说明</summary>

**答案: B**

**说明:**

waypoint（Envoy）管理并复用以目标 IP:Port 为键的连接池。目标 Pod 终止时，ztunnel 不会显式通知 waypoint。如果终止的 Pod IP 被重新分配给新的 Pod，waypoint 可能复用一个已失效的连接并返回 503。这正是该问题背后的机制——**连接生命周期管理**，而不是重复 IP 分配——§4 中测得的 503 比率也与此一致。

**参考资料:**

* [Sidecar vs Ambient Mode Selection Guide](../../../service-mesh/istio/comparison/03-sidecar-vs-ambient.md)
* [Ambient Mode: Waypoint Proxy](../../../service-mesh/istio/advanced/01-ambient-mode.md)

</details>

***

### 问题 2：解读 EKS 1.36 测试结果

在专用单租户 EKS 1.36 集群上，执行具有重复滚动发布的 100 qps x 600s（60,000 个请求）负载时，sidecar 的 503 比率为 0.5%，ambient-L4（无 waypoint）实际 503 为零（但出现 0.3% TCP 错误），ambient-L7（有 waypoint）为 2.6%。正确的解读是什么？

A. Ambient 始终比 sidecar 更稳定 B. 经由 waypoint 路由的 503 比率高于 sidecar，但仅使用 L4（无 waypoint）不会产生实际 503 C. Ambient-L4 的 TCP 错误（0.3%）与 waypoint 的 503 是同一现象 D. socket 使用量最低的 mode 最稳定

<details>

<summary>答案 &#x26; 说明</summary>

**答案: B**

**说明:**

数据表明，“ambient”并非总是优于或劣于 sidecar——流量是否经过 **waypoint** 才是决定因素。Ambient-L7（有 waypoint）的 503 比率约为 sidecar 的 5 倍（2.6% 对 0.5%），而 ambient-L4（无 waypoint）实际 503 为零。不过，这并不表示 ambient-L4 没有故障——它表现出另一种故障模式：TCP 层连接中断（0.3%），这不同于 waypoint 将请求转发到失效连接并返回 503 的情况（因此 C 不正确）。Socket 使用量并非稳定性指标，只是连接重新建立频率的代理指标（因此 D 不正确）——实际上，ambient-L4 消耗了 _最多_ 的 socket，却没有出现 503。

**参考资料:**

* [Sidecar vs Ambient Mode Selection Guide: Zero-Downtime Rollout Results](../../../service-mesh/istio/comparison/03-sidecar-vs-ambient.md)

</details>

***

### 问题 3：NetworkPolicy 和 ambient

在使用基于端口的 NetworkPolicy 的集群中，流量无法到达 ambient-mode Pod。应用程序监听端口 8080。最可能的原因和修复方法是什么？

A. Ambient 不支持 NetworkPolicy，因此应删除 NetworkPolicy B. 实际流量通过 HBONE 隧道（TCP 15008）到达，因此 NetworkPolicy 需要为 15008 添加入站允许规则 C. 应将 PeerAuthentication 更改为 PERMISSIVE D. 需要重启 istio-cni DaemonSet

<details>

<summary>答案 &#x26; 说明</summary>

**答案: B**

**说明:**

在 ambient mode 中，ztunnel 会将 Pod 流量封装在 HBONE（mTLS）隧道中，并通过端口 15008 传输。仅允许应用程序端口（8080）的 NetworkPolicy 会阻止实际到达的 15008 流量。修复方法是在目标 Pod 上为 TCP 15008 添加入站允许规则。Sidecar 不需要此额外规则，因为 sidecar 与应用程序共享相同的 Pod 网络命名空间。

**参考资料:**

* [Sidecar vs Ambient Mode Selection Guide: NetworkPolicy](../../../service-mesh/istio/comparison/03-sidecar-vs-ambient.md)

</details>

***

### 问题 4：非幂等 API 和重试策略

为什么建议默认不要在订单创建等非幂等 API 路径上启用 mesh 级别的重试（例如 waypoint 重试、VirtualService 重试）？

A. 重试会增加过多 CPU 开销 B. 当 waypoint 将请求转发到失效连接并返回 503 时，重试可能重新执行已在服务器端完成的请求，从而导致重复执行（例如重复订单） C. 重试与 STRICT mTLS 不兼容 D. ambient mode 不支持重试

<details>

<summary>答案 &#x26; 说明</summary>

**答案: B**

**说明:**

503 是客户端可见的故障，但该故障类别中隐藏着请求实际上已到达服务器并完成处理的情况——由于连接中断与应用程序完成工作之间发生竞争，只有 _响应_ 丢失了。在这种情况下，mesh 重试会通过另一条连接重新发送相同的逻辑请求；如果服务器不保证幂等性，该请求就会被处理两次。对于订单创建等不可逆操作，这种风险尤其严重，因此默认不启用重试并单独验证会更安全。后续测试（T2）针对 sidecar 和 ambient-L7 waypoint 重试进行了 300s 的持续滚动发布变动，结果在该次运行中发现零次重复执行——这降低了该竞争条件 _常见_ 的可能性，但并不能证明它是 _安全_ 的，因为它需要极窄的时间窗口，更长时间或更高吞吐量的测试仍可能捕获到它。

**参考资料:**

* [Sidecar vs Ambient Mode Selection Guide: The Risk of Retry as a Mitigation](../../../service-mesh/istio/comparison/03-sidecar-vs-ambient.md)

</details>

***

## 评分

* 统计 4 道题中答对的题数。
* 4/4：您可以根据测试结果中的证据说明 sidecar 与 ambient 的决策。
* 2-3/4：您理解核心概念，但应再次复习 NetworkPolicy 和重试风险部分。
* 0-1/4：从头重新阅读 [Sidecar vs Ambient Mode Selection Guide](../../../service-mesh/istio/comparison/03-sidecar-vs-ambient.md)。

## 学习资源

* [Sidecar vs Ambient Mode Selection Guide](../../../service-mesh/istio/comparison/03-sidecar-vs-ambient.md)
* [Ambient Mode](../../../service-mesh/istio/advanced/01-ambient-mode.md)
* [mTLS](../../../service-mesh/istio/security/01-mtls.md)
