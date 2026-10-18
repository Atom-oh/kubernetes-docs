# 多账户、多集群 EKS 架构测验

> 本测验用于检查你对[多账户、多集群 EKS 架构](../../governance/03-eks-multi-account-multi-cluster.md)的理解。

---

1. 双集群 A/B EKS 的有效验证目标是什么？
   - A) 修复单可用区 EKS 控制平面
   - B) 测试将升级/附加组件/Webhook 故障限制在单个集群内
   - C) 自动覆盖每一种 Region 故障
   - D) 保证降低成本

<details>
<summary>显示答案</summary>

**答案：B) 测试将升级/附加组件/Webhook 故障限制在单个集群内**

**说明：**
集群特定的故障隔离可以成为采用该设计的理由。共享 VPC、DNS、Account 和数据依赖项需要单独分析。

</details>

---

2. 哪项说法正确描述了 ARC 可用区转移的安全行为？
   - A) 发生可用区转移后，任何工作负载的流量都会立即被阻断
   - B) 如果某工作负载的端点只存在于受影响的 AZ，EKS 仍会继续将流量发送到该 AZ
   - C) 每个工作负载都会自动迁移到另一个 AZ
   - D) 这种行为只会出现在 EKS Fargate 上

<details>
<summary>显示答案</summary>

**答案：B) 如果某工作负载的端点只存在于受影响的 AZ，EKS 仍会继续将流量发送到该 AZ**

**说明：**
这是安全行为：只部署在单个 AZ 的工作负载不会受到可用区转移的保护。请测试 N-1 负载和单 AZ 例外；这并不意味着演练时总会停止该工作负载。

</details>

---

3. EC2 link-local 每秒 1,024 个数据包的额度意味着什么？
   - A) 检查合计 DNS/IMDS/NTP 流量和实际 DNS 指标
   - B) 为 DNS 专门预留了无限容量
   - C) 每个 AZ 限制为 100 Gbps
   - D) 证明 CoreDNS 是最常见的故障

<details>
<summary>显示答案</summary>

**答案：A) 检查合计 DNS/IMDS/NTP 流量和实际 DNS 指标**

**说明：**
请检查共享的 link-local 额度和 VPC DNS ENI 限制。应验证 linklocal_allowance_exceeded 和 DNS 延迟，不要仅根据 Pod 密度推断原因。

</details>

---

4. 禁用 ALB 目标组跨区负载均衡时应检查什么？
   - A) 保证节省 ALB 跨区数据传输费用
   - B) 每个 AZ 的容量，并区分空 AZ 返回 503 与不健康目标故障转移
   - C) 自动重启集群
   - D) 所有目标都会变为健康状态

<details>
<summary>显示答案</summary>

**答案：B) 每个 AZ 的容量，并区分空 AZ 返回 503 与不健康目标故障转移**

**说明：**
目标粘性和 Lambda 目标存在限制；空目标与不健康目标并不相同。ALB 跨区产生的区域内数据传输不会另行收费。

</details>
