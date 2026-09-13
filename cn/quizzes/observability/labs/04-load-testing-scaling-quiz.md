# 可观测性实验 第 4 部分 测验

> **最后更新**: September 13, 2026

1. k6 的 VU 与 RPS 之间是什么关系？
   - A) 一个 VU 始终等于一个 RPS。
   - B) VU 是并发执行上下文；RPS 还取决于请求数量、延迟和 sleep。
   - C) VU 等于节点数量。
   - D) RPS 与响应时间无关。

<details>
<summary>显示答案</summary>

**答案：B) VU 是并发执行上下文；RPS 还取决于请求数量、延迟和 sleep。**

在不同的工作负载和等待条件下，相同的 VU 数量并不意味着相同的吞吐量。

</details>

---

2. k6 检查（check）失败时应如何让 CI 失败？
   - A) 调用 check 总会以退出码 1 结束。
   - B) 设置 checks/失败率阈值，并检查退出码。
   - C) 生成摘要 JSON 文件即可证明成功。
   - D) 只统计 HTTP 200 响应。

<details>
<summary>显示答案</summary>

**答案：B) 设置 checks/失败率阈值，并检查退出码。**

HTTP 成功与业务成功并不相同；还需断言 JSON、ID 和支付状态。

</details>

---

3. 压测应该读取哪些订单 ID？
   - A) 1 到 1000 之间的随机 ID。
   - B) 由测试实际创建的 ID。
   - C) 客户 ID。
   - D) HTTP 状态码。

<details>
<summary>显示答案</summary>

**答案：B) 由测试实际创建的 ID。**

使用创建响应中返回的 ID，这样随机产生的 404 就不会污染工作负载。

</details>

---

4. 什么应该随 SQS 积压量直接扩缩？
   - A) 始终只扩缩 API 生产者。
   - B) 处理该队列的消费者。
   - C) Alertmanager 副本。
   - D) 队列名称。

<details>
<summary>显示答案</summary>

**答案：B) 处理该队列的消费者。**

KEDA 读取队列属性并通过 HPA 管理扩缩；它本身并不消费消息。

</details>

---

5. KEDA 的 cooldownPeriod 何时生效？
   - A) 每次从 10 个副本变为 9 个副本时。
   - B) 在最后一个活跃触发器之后缩容到零时。
   - C) EC2 启动延迟。
   - D) 日志保留期。

<details>
<summary>显示答案</summary>

**答案：B) 在最后一个活跃触发器之后缩容到零时。**

对于 1..N 个副本范围内的扩缩，请检查 HPA behavior 和稳定窗口（stabilization window）。

</details>

---

6. HPA 的缩容稳定窗口有什么作用？
   - A) 冻结所有节点。
   - B) 采用窗口内最高的副本数推荐值。
   - C) 仅使用瞬时 CPU 值。
   - D) 每隔配置的间隔删除一个 Pod。

<details>
<summary>显示答案</summary>

**答案：B) 采用窗口内最高的副本数推荐值。**

它并不是简单的无条件固定延迟；策略（policy）和推荐值历史同样重要。

</details>

---

7. Karpenter 通常可以解决哪个问题？
   - A) 镜像名称拼写错误。
   - B) 无法调度的 Pod 需要与其 NodePool 兼容的容量。
   - C) 应用程序语法错误。
   - D) 数据库密码错误。

<details>
<summary>显示答案</summary>

**答案：B) 无法调度的 Pod 需要与其 NodePool 兼容的容量。**

增加节点并不能解决镜像拉取问题或应用程序缺陷；请先检查调度失败的原因。

</details>

---

8. kube_deployment_status_replicas 衡量什么？
   - A) 始终是就绪（ready）副本数。
   - B) Deployment 的副本总数，与就绪副本数不同。
   - C) 包含 Rollouts 在内的所有控制器副本数。
   - D) 节点数量。

<details>
<summary>显示答案</summary>

**答案：B) Deployment 的副本总数，与就绪副本数不同。**

就绪副本数请使用 kube_deployment_status_replicas_ready；Rollouts 需要各自的状态源或 exporter。

</details>

---

9. 如何根据 phase 指标统计处于 Running 状态的 Pod 数量？
   - A) 统计所有 Running 时间序列，不过滤取值。
   - B) 直接对 Running phase 的 0/1 gauge 求和。
   - C) 累加 Pod 名称的长度。
   - D) 始终返回三。

<details>
<summary>显示答案</summary>

**答案：B) 直接对 Running phase 的 0/1 gauge 求和。**

Running phase 的时间序列可能存在但取值为零，因此不加过滤的计数会高估数量。对 gauge 求和时，若所有 Pod 都处于 Pending 则返回零，而在缺少遥测数据时结果依然为空。

</details>

---

10. 什么可以作为压测实验成功的证据？
   - A) 从预期文档数值中复制的表格。
   - B) 实测的请求数、错误数、延迟、队列长度、副本数、节点数和退出状态。
   - C) Job 创建成功。
   - D) 仅仅是节点数量减少。

<details>
<summary>显示答案</summary>

**答案：B) 实测的请求数、错误数、延迟、队列长度、副本数、节点数和退出状态。**

不要把未经实测的吞吐量、可用性或成本节省作为结果呈现。

</details>

---

[返回指南](../../../labs/observability/04-load-testing-scaling-lab.md)
