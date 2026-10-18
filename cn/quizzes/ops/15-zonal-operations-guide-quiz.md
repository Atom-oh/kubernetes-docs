# 可用区集群运维测验

> **相关文档**：[可用区集群运维](../../ops/15-zonal-operations-guide.md)

## 选择题

### 1. EKS 原生回滚的七天窗口意味着什么？

- A) 回滚必须耗费的时间
- B) 升级完成后允许发起回滚的资格窗口
- C) 节点的最长生命周期
- D) 自动恢复附加组件的期限

<details>
<summary>显示答案</summary>

**答案：B) 升级完成后允许发起回滚的资格窗口**

这是允许发起回滚到紧邻前一个次要版本的窗口。集群创建时的版本、支持状态、后续升级和兼容性仍会影响资格。Auto Mode 会先回滚节点；附加组件、应用和数据变更不会自动恢复。

</details>

### 2. 将 NLB 目标组权重设为零后，必须检查什么？

- A) 所有现有连接都会立即终止
- B) TargetGroupBinding 会迁移到另一个集群
- C) 分别检查新流量减少和现有流量排空
- D) ARC 会自动重写其他每个集群的权重

<details>
<summary>显示答案</summary>

**答案：C) 分别检查新流量减少和现有流量排空**

通常，权重变更影响新流；但当前 NLB 指南说明，权重为零也会在短时间后关闭现有连接。不要只假定连接会自然排空，应测试重新连接和重试行为。变更节点前，应检查 NewFlowCount、ActiveFlowCount 和错误。TGB 没有权重字段，EKS 可用区转移也不会自动更改跨集群的权重。

</details>

### 3. 哪种组合能正确配置 Kafka KIP-392？

- A) 只设置 broker.rack 就会自动配置所有消费者
- B) RackAwareReplicaSelector、broker.rack，以及与之匹配的消费者 client.rack
- C) 只设置 unclean.leader.election.enable=true
- D) 不同的 AZ 名称和 AZ ID 字符串可以互换

<details>
<summary>显示答案</summary>

**答案：B) RackAwareReplicaSelector、broker.rack，以及与之匹配的消费者 client.rack**

replica.selector.class 的完整值是 org.apache.kafka.common.replica.RackAwareReplicaSelector。Strimzi Kafka CR 配置的是 broker；普通应用消费者需要单独配置。如果没有合适的本地副本，选择器会回退到 leader。

</details>

### 4. GLIDE AZ_AFFINITY_REPLICAS_AND_PRIMARY 的优先顺序是什么？

- A) 仅选择 primary
- B) 本地 replica → 本地 primary → 其他 AZ 中的 replica 或 primary
- C) 仅选择远程 replica
- D) 没有本地节点时始终报错

<details>
<summary>显示答案</summary>

**答案：B) 本地 replica → 本地 primary → 其他 AZ 中的 replica 或 primary**

服务器的 AZ 元数据必须与 client_az 匹配。应评估对副本读取陈旧数据的容忍度；只看读取占比并不足够。HotelTrader 报告的改进既包含 AZ 感知路由，也包含请求批处理。

</details>

### 5. 关于 Aurora 默认的 reader endpoint，哪项说法正确？

- A) 它会将每条 SQL 查询分配到不同的副本
- B) 它保证选择同一 AZ 中的 reader
- C) 它在连接层面进行负载均衡；如果没有副本，也可能使用 writer
- D) 必须使用 JDBC Wrapper 才能连接

<details>
<summary>显示答案</summary>

**答案：C) 它在连接层面进行负载均衡；如果没有副本，也可能使用 writer**

它不保证 AZ 优先选择。按 AZ 划分的 READER 自定义端点需要管理成员和回退机制。JDBC fastestResponse 依据响应时间选择，而不是严格的 AZ 约束。功能请求 #1139 已于 2025 年关闭。

</details>

### 6. 关于确定 Pod 所在的 AZ，哪项说法不正确？

- A) 普通 Pod 创建准入过程始终知道调度器选中的节点
- B) AWS MSK 的 Kyverno 示例处理 Pod/binding 请求
- C) 可以通过 Downward API 将 spec.nodeName 传给初始化组件
- D) IMDS 的访问取决于环境和安全配置

<details>
<summary>显示答案</summary>

**答案：A) 普通 Pod 创建准入过程始终知道调度器选中的节点**

创建 Pod 时通常还未选定节点。应在绑定时注入信息，或在调度后查询。Downward API 不会直接查询节点标签，Strimzi 也不会自动配置与其无关的应用消费者。

</details>
