# 可用区集群运维测验

> **相关文档**: [可用区集群运维](../../ops/15-zonal-operations-guide.md)

## 多项选择题

### 1. Amazon EKS 原生 Kubernetes 版本回滚（于 2026 年 7 月正式发布）的资格窗口期是多长？

- A) 24 小时
- B) 7 天
- C) 30 天
- D) 无限制

<details>
<summary>显示答案</summary>

**答案：B) 7 天**

**说明：**
EKS 原生回滚可在升级后的 7 天内一次回退一个次要版本。在目标版本创建的集群、超过 7 天的集群，或已经再次升级的集群不符合资格。

</details>

### 2. 在可用区原地升级期间，使用什么机制将流量排出某个可用区？

- A) `kubectl drain`
- B) 调整 Target Group 权重
- C) 等待 DNS TTL 到期
- D) 重新创建集群

<details>
<summary>显示答案</summary>

**答案：B) 调整 Target Group 权重**

**说明：**
无需改动集群内部的任何内容，而是调整通过 TargetGroupBinding 绑定的 Target Group 的权重，以减少或停止流向指定可用区的流量。对于 AZ 中断等非计划情况，ARC Zonal Shift 会自动执行这一职责。

</details>

### 3. 要启用 KIP-392（Follower Fetching），Kafka broker 上必须设置什么？

- A) `auto.leader.rebalance.enable=true`
- B) `replica.selector.class=RackAwareReplicaSelector`
- C) `unclean.leader.election.enable=true`
- D) `min.insync.replicas=2`

<details>
<summary>显示答案</summary>

**答案：B) `replica.selector.class=RackAwareReplicaSelector`**

**说明：**
Broker 需要将 `replica.selector.class` 设置为 `RackAwareReplicaSelector`，并分配 `broker.rack`（AZ ID）。在 consumer 端，必须将 `client.rack` 属性设置为 consumer 自己的 AZ ID，以便将拉取请求重定向到同一 rack 的 follower。

</details>

### 4. 对于读取操作占比超过 99% 的工作负载，推荐使用哪种 Valkey GLIDE `ReadFrom` 策略？

- A) `PRIMARY`
- B) `PREFER_REPLICA`
- C) `AZ_AFFINITY_REPLICAS_AND_PRIMARY`
- D) 随机分配

<details>
<summary>显示答案</summary>

**答案：C) `AZ_AFFINITY_REPLICAS_AND_PRIMARY`**

**说明：**
该策略会优先选择同一 AZ 中的 replica，随后回退到同一 AZ 中的 primary，只有在万不得已时才会访问其他 AZ。对于以读取为主的工作负载，这是兼顾成本节约与可用性的推荐平衡方案——HotelTrader 在采用该策略后，将跨 AZ 传输成本降低了 95%。

</details>

### 5. 关于 Amazon Aurora 默认 reader endpoint，以下哪项说法正确？

- A) 它会自动优先选择同一 AZ 中的 replica
- B) 它是没有 AZ 感知能力的轮询 DNS
- C) 它始终路由到 primary
- D) 没有 AWS Advanced JDBC Wrapper 就无法使用它

<details>
<summary>显示答案</summary>

**答案：B) 它是没有 AZ 感知能力的轮询 DNS**

**说明：**
Aurora 的默认 reader endpoint 不具备 AZ 亲和性。你可以通过按 AZ 划分的 custom endpoint 或 AWS Advanced JDBC Wrapper 的 `fastestResponse` 策略来绕过此问题，但真正的 AZ 亲和性本身仍是 `aws-advanced-jdbc-wrapper` 仓库中一项尚未实现的功能请求。

</details>

### 6. 关于 Pod 如何确定自身所在 AZ，以下哪项说法是错误的？

- A) 它可以通过 EC2 IMDS 直接查询
- B) Kyverno mutating policy 可以将 node label 复制到 Pod annotation
- C) Kubernetes Downward API 默认会将 node 的 zone label 注入到 Pod 中
- D) Strimzi 等 operator 可以将 rack-awareness 作为内置功能提供

<details>
<summary>显示答案</summary>

**答案：C) Kubernetes Downward API 默认会将 node 的 zone label 注入到 Pod 中**

**说明：**
Downward API 不会自动将 node 的 `topology.kubernetes.io/zone` label 注入到 Pod 中。因此，需要采用其他方法之一：直接查询 IMDS、基于 Kyverno 的准入时 label 复制，或使用像 Strimzi 一样具备内置支持的 operator。

</details>
