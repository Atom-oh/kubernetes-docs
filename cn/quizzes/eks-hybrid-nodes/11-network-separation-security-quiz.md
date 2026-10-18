# 混合节点网络隔离安全审查测验

> **最后更新**：2026 年 9 月 16 日

[学习指南：与安全团队审查混合节点网络隔离](../../eks-hybrid-nodes/11-network-separation-security.md)

1. 应如何修正“DX 和私有端点使此方案符合网络隔离要求”这句话？
   - A) 只要附加 DX 连接 ID 就足够。
   - B) 明确适用的策略、允许的连接、权限和数据、实施证据以及审批条件。
   - C) 没有互联网访问，就不存在来自外部的管理连接。

<details>
<summary>显示答案</summary>

**答案：**B

私有路由可以减少暴露，但无法判断客户策略是否允许该管理连接。

</details>

2. `com.amazonaws.<region>.eks` 接口端点提供什么？
   - A) 为所有从控制平面到 kubelet 的 TCP 10250 连接提供中继。
   - B) 提供替代 Kubernetes API RBAC 的端点策略。
   - C) 通过私有连接访问 AWS EKS 管理 API，例如 `DescribeCluster`。

<details>
<summary>显示答案</summary>

**答案：**C

Kubernetes API 私有端点与 AWS EKS 管理 API 的 PrivateLink 端点是不同的端点。

</details>

3. 防火墙只允许混合节点主动发起 TCP 443 会话的响应流量。传统路由部署中，这是否也允许 `kubectl logs` 使用的 kubelet 连接？
   - A) 不允许。应单独检查从 API Server 发起、发往节点 TCP 10250 的会话。
   - B) 允许。同一集群中的所有数据包都是现有会话的响应。
   - C) 允许。DX 会自动绕过防火墙规则。

<details>
<summary>显示答案</summary>

**答案：**A

允许有状态会话的返回流量，并不等于允许一个面向不同 TCP 会话的新入站连接。

</details>

4. 哪些检查可以证实本文假设只使用私有端点？
   - A) 只检查 `endpointPrivateAccess=true`。
   - B) 确认已启用私有访问并禁用公共访问，然后验证 DNS、路由和实际流量。
   - C) 缩小 `publicAccessCidrs` 范围；它会以同样方式限制私有端点。

<details>
<summary>显示答案</summary>

**答案：**B

如果同时启用公共和私有访问，混合节点可能会使用公共地址。公共访问 CIDR 不会控制私有端点的访问。

</details>

5. 关于 DX 部署中的加密，哪种说法正确？
   - A) DX 默认会加密每条 Pod 流量。
   - B) 使用私有 IP 后可以跳过 TLS 证书验证。
   - C) 保留 TLS；若还需要单独的链路加密，应检查 IPsec/MACsec 是否受支持以及覆盖范围。

<details>
<summary>显示答案</summary>

**答案：**C

DX 默认不会加密传输中的数据。MACsec 链路保护的覆盖范围也不同于应用层端到端 TLS。

</details>

6. 业务应用的 Pod 在本地运行。以下哪项正确描述了数据边界？
   - A) 所有业务数据都会自动复制到 AWS。
   - B) 所有数据必然保留在本地。
   - C) 除业务数据存储外，还应分别检查 API 对象、Secret、`logs`、管理流和应用程序出站流量。

<details>
<summary>显示答案</summary>

**答案：**C

节点运行位置并不能决定每种数据的存储与传输位置。Kubernetes 管理操作也可能处理敏感数据。

</details>

7. 在防火墙允许列表中使用 EKS ENI 地址时，需要什么流程？
   - A) 永久保留最初观察到的 `/32` 地址。
   - B) 验证集群所有权和地址范围；ENI 变更后刷新并重新测试，同时记录共享子网的风险。
   - C) 允许所有 AWS 地址范围。

<details>
<summary>显示答案</summary>

**答案：**B

ENI IP 可能变化。若允许整个共享子网，该范围内的其他资源也可能被纳入允许的源地址。

</details>

8. “我们移除了 `exec`，因此管理员介入的数据访问都已阻断”这句话遗漏了什么？
   - A) 还应审查工作负载的创建/修改、特权/hostPath 访问、其他子资源以及主机管理权限。
   - B) 集群管理员不能跨越命名空间边界。
   - C) NetworkPolicy 会使所有管理员权限失效。

<details>
<summary>显示答案</summary>

**答案：**A

限制一条命令并不会移除其他访问路径。应结合准入和主机控制，审查该主体的完整权限。

</details>

9. 关于安全审查证据，哪种说法正确？
   - A) VPC Flow Logs 可以重建所有 TLS 载荷以及 `exec` 的输入/输出。
   - B) 有了 CloudTrail 就不需要 Kubernetes 审计日志。
   - C) 区分网络记录、Kubernetes 审计和 CloudTrail，并用合成数据测试允许与拒绝的行为。

<details>
<summary>显示答案</summary>

**答案：**C

这些记录的覆盖范围各不相同。Kubernetes 审计不会记录所有流式载荷，也不能替代拒绝行为测试或数据分类。

</details>

10. 如果策略禁止所有新建的云端发起连接，将 Webhook 移到云节点或使用 Hybrid Nodes Gateway 就能自动满足要求吗？
    - A) 任一种变更都足够。
    - B) 不够。应重新评估设计，包括独立的 kubelet 连接和网关实际的双向流量路径。
    - C) 将架构描述为 PrivateLink 就足够。

<details>
<summary>显示答案</summary>

**答案：**B

移动 Webhook 并不会消除 kubelet 的连接要求。Hybrid Nodes Gateway 也不是单向安全网关。如果策略与受支持的连接要求冲突，应重新考虑设计或正式审批条件。

</details>
