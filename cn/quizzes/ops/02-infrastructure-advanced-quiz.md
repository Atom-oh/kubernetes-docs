# 基础设施高级测验

> **相关文档**: [基础设施高级](../../ops/02-infrastructure-advanced.md)

## 单选题

### 1. 在 blue/green 部署中，NLB weighted target groups 的主要用途是什么？

- A) 通过使用更少的 load balancer 来降低成本
- B) 控制不同 cluster 版本之间的流量分配
- C) 提高 SSL 终止性能
- D) 消除对 health check 的需求

<details>
<summary>显示答案</summary>

**答案：B) 控制不同 cluster 版本之间的流量分配**

**说明：**
NLB weighted target groups 允许在 blue（当前）cluster 和 green（新）cluster 之间逐步切换流量。通过调整权重（例如 90:10、50:50、0:100），运维人员可以执行受控发布，并在检测到问题时快速回滚。

</details>

### 2. 在单可用区 EKS cluster 策略中，为什么可能只将 data nodes 部署到一个 Availability Zone？

- A) 降低跨 AZ 数据传输成本
- B) 简化 DNS 配置
- C) 避免使用多个 subnet
- D) 消除对 persistent volumes 的需求

<details>
<summary>显示答案</summary>

**答案：A) 降低跨 AZ 数据传输成本**

**说明：**
在 AWS 中，跨 AZ 数据传输会产生费用。对于使用本地存储的数据密集型 workload（如数据库），将所有副本保持在单个 AZ 中可以消除这些成本，同时依赖应用层复制来保证持久性。

</details>

### 3. 哪个 Kubernetes 功能可以确保 pods 分布在不同的 zone 或 node 上？

- A) PodAffinity
- B) TopologySpreadConstraints
- C) ResourceQuota
- D) LimitRange

<details>
<summary>显示答案</summary>

**答案：B) TopologySpreadConstraints**

**说明：**
TopologySpreadConstraints 控制 pods 如何分布在 topology domains（zone、node、region）之间。它们确保高可用所需的均匀分布，并且可以使用 `maxSkew`、`topologyKey` 和 `whenUnsatisfiable` 参数进行配置。

</details>

### 4. Route53 weighted routing 与 NLB weighted target groups 有何不同？

- A) Route53 在 DNS 级别工作，NLB 在连接级别工作
- B) Route53 仅支持相等权重
- C) NLB 不支持 health check
- D) Route53 需要 VPC peering

<details>
<summary>显示答案</summary>

**答案：A) Route53 在 DNS 级别工作，NLB 在连接级别工作**

**说明：**
Route53 weighted routing 在 DNS 解析时分配流量，而 NLB weighted target groups 在连接级别分配流量。基于 DNS 的 routing 需要考虑 TTL，而 NLB 提供更即时的流量切换。

</details>

### 5. 在 3-AZ 部署中，TopologySpreadConstraints 推荐的 `maxSkew` 值是多少？

- A) 0
- B) 1
- C) 3
- D) 10

<details>
<summary>显示答案</summary>

**答案：B) 1**

**说明：**
`maxSkew` 为 1 可确保 pods 均匀分布，使 topology domains 之间最多只相差一个 pod。这在节点存在资源限制时，既能提供良好平衡，也仍然允许调度灵活性。

</details>

### 6. 在 blue/green cluster 架构中，哪些内容应在 clusters 之间共享？

- A) Worker nodes
- B) 外部 DNS 和 load balancer
- C) etcd 存储
- D) Kubernetes API server

<details>
<summary>显示答案</summary>

**答案：B) 外部 DNS 和 load balancer**

**说明：**
Blue/green clusters 是独立的 EKS clusters，它们共享 DNS 记录和 load balancer 等外部基础设施。这允许在不更改面向客户端的 endpoint 的情况下，在 clusters 之间切换流量。

</details>

### 7. 在 TopologySpreadConstraints 中设置 `whenUnsatisfiable: DoNotSchedule` 时会发生什么？

- A) Pods 会不受约束地被调度到任意位置
- B) 如果无法满足约束，Pods 会保持 pending 状态
- C) Pods 会被自动删除
- D) 该约束会被忽略

<details>
<summary>显示答案</summary>

**答案：B) 如果无法满足约束，Pods 会保持 pending 状态**

**说明：**
当 spread constraint 会被违反时，`DoNotSchedule` 会阻止 pod 调度。这可确保严格遵守 topology 要求，但如果 cluster topology 不支持该约束，可能会导致 pods 处于 pending 状态。

</details>

### 8. 对于 blue/green clusters 之间的自动故障转移，可以结合 health check 使用哪个 AWS 服务？

- A) AWS Config
- B) Route53 health checks 与 failover routing
- C) AWS Inspector
- D) AWS Trusted Advisor

<details>
<summary>显示答案</summary>

**答案：B) Route53 health checks 与 failover routing**

**说明：**
Route53 health checks 持续监控 endpoint 可用性，并可以使用 failover routing policy 自动将流量切换到健康的 cluster。这可以在无需人工干预的情况下实现自动灾难恢复。

</details>

### 9. 使用 NLB cross-zone load balancing 时，一个关键注意事项是什么？

- A) 它始终免费
- B) 它可能产生额外的数据传输费用
- C) 它需要 VPC peering
- D) 它仅适用于 TCP protocol

<details>
<summary>显示答案</summary>

**答案：B) 它可能产生额外的数据传输费用**

**说明：**
启用 cross-zone load balancing 时，NLB 会将流量均匀分配到所有启用 AZ 中的所有已注册 targets，这可能会产生跨 AZ 数据传输费用。在设计 multi-AZ 部署架构时，需要考虑这项成本。

</details>

### 10. 在 zonal cluster 部署（a-zone blue、c-zone green）中，主要优势是什么？

- A) 降低网络复杂度
- B) 故障隔离和独立升级路径
- C) 更低的计算成本
- D) 自动数据复制

<details>
<summary>显示答案</summary>

**答案：B) 故障隔离和独立升级路径**

**说明：**
Zonal clusters 提供 failure domain 隔离——一个 zone 中的问题不会影响另一个 cluster。这也支持独立的升级测试和渐进式发布，从而降低 Kubernetes 版本升级期间的风险。

</details>
