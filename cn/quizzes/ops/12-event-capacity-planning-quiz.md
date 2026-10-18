# 活动容量规划测验

> **相关文档**：[活动容量规划](../../ops/12-event-capacity-planning.md)

## 1. 如何使用多个 KEDA 指标来确定目标值？

- A. 将每个值相加
- B. HPA 汇总各指标给出的副本数建议，取最大值，再应用行为设置和最小/最大值
- C. Cron 可保证 Pod 已就绪
- D. 指标始终定义了上限

<details>
<summary>显示答案</summary>

**答案：B**

Cron 提供按计划设置的需求下限；maxReplicaCount 和其他约束会限定范围。还应单独核实实际就绪情况。

</details>

## 2. 为某个有日期的活动使用五字段 Cron 时，哪些事项很重要？

- A. 年份会自动补上
- B. 运行一次后会自动删除
- C. 它可能在下一年再次触发，因此需要检查时区和夏令时
- D. 它始终只使用 UTC

<details>
<summary>显示答案</summary>

**答案：C**

示例会检查每年重复触发的情况和时间边界。活动结束后应删除或更新该活动的配置。

</details>

## 3. 哪项配置描述静态 Karpenter NodePool？

- A. 仅提高 weight 就会创建静态容量
- B. 使用 replicas，不设置 weight，并限制 limits.nodes
- C. 随时移除 replicas 就能切换为动态模式
- D. 每个 NodePool 的预算都会阻止扩缩操作

<details>
<summary>显示答案</summary>

**答案：B**

应区分静态和动态模式。静态扩缩不会受 NodePool disruption budget 限制，但仍须遵守 PDB。

</details>

## 4. 移交后，如果占位 Deployment 的期望副本数仍未改变，可能发生什么？

- A. 它始终不会产生额外费用
- B. 重新创建的占位 Pod 可能导致预置额外节点
- C. Karpenter 会自动将期望副本数设为零
- D. 实际应用总会立即就绪

<details>
<summary>显示答案</summary>

**答案：B**

应同时验证占位资源的保留和过期策略、占位需求是否已移除，以及实际应用是否就绪。

</details>

## 5. 增加 30% 的容量能否保证一个可用区故障后服务继续运行？

- A. 能，任何情况下都可以
- B. 对 On-Demand 实例可以
- C. 不能；需要计算资源放置方式和剩余吞吐量
- D. 只要有 PDB 就可以

<details>
<summary>显示答案</summary>

**答案：C**

在 15/11 个节点的示例中，节点较多的可用区失效后，剩余容量无法满足基线峰值需求。还应通过测量验证输入假设。

</details>

## 6. 定向 Capacity Reservation 表示什么？

- A. 仅限一个 NodePool 使用的安全 ACL
- B. 实例会显式定向到该预留，并且必须满足匹配条件
- C. 它会自动应用于所有现有实例
- D. 一种 On-Demand 折扣产品

<details>
<summary>显示答案</summary>

**答案：B**

应检查 IAM/共享设置、可用区、实例类型、平台、租赁模式和实际使用情况。Capacity Reservation 与 RI 不同。

</details>

## 7. 如果在 D-30 创建即时生效的预留，且只设置了未来的 end_date，会发生什么？

- A. 未使用期间会免费等待活动开始
- B. end_date 会指定未来的开始时间
- C. 已生效但未使用的容量可能产生费用
- D. 已占用的容量始终会被重复收费

<details>
<summary>显示答案</summary>

**答案：C**

成本模型要计入预留的生效时段；也不要对占用预留的实例重复计费。

</details>

## 8. 关于 CloudWatch scaler 的 metricStat 和 minMetricValue，哪项说法正确？

- A. 正确字段是 metricStatType
- B. minMetricValue 始终是激活阈值
- C. metricStat 选择统计量；minMetricValue 是 NoData 回退值，但 ignoreNullValues=false 会覆盖此行为
- D. Sum 适合所有速率型 gauge

<details>
<summary>显示答案</summary>

**答案：C**

应区分增量/计数与速率/累积计数器，并核对周期、采集窗口和发布延迟。

</details>

## 9. 指标有延迟时，应如何处理由 KEDA 管理的工作负载？

- A. 直接缩放 Deployment 总会保留更改
- B. HPA 的名称总是与 Deployment 相同
- C. 在已批准的范围和 GitOps 所有权内，检查 ScaledObject 的下限
- D. 创建没有上限的 NodePool

<details>
<summary>显示答案</summary>

**答案：C**

直接修改 HPA/Deployment 可能会在协调过程中被覆盖。应记录原设置，并在结束时恢复。

</details>

## 10. 关于活动准备和清理，哪项说法正确？

- A. 每个镜像都支持 sh/echo，并会永久保留缓存
- B. 删除 NodePool 三十分钟后总是安全的
- C. 验证应用和缓存限制、基线触发条件，以及节点和预留是否已实际清理
- D. 删除 ScaledObject 总会恢复原副本数

<details>
<summary>显示答案</summary>

**答案：C**

启动行为、垃圾回收、CPU 架构和权限各有不同。清理时必须考虑实际负责资源的控制器以及删除生命周期。

</details>
