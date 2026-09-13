# 可观测性实验 03 测验

<span id="observability-lab-part-3-msa-deployment-and-canary-quiz"></span>

> **最后更新**: September 13, 2026

1. 订单/outbox 的事务边界是什么？
   - A) 提交订单，然后忽略失败的消息传递。
   - B) 在一个 DB transaction（数据库事务）中同时提交或回滚。
   - C) SNS 和 DB 会自动保持原子性。
   - D) 为每个请求初始化 DB。

<details>
<summary>显示答案</summary>

**答案：B) 在一个 DB transaction（数据库事务）中同时提交或回滚。**

验证 DB 回滚以及未发布 outbox 记录的保留。

</details>

---

2. 谁拥有 payment workload？
   - A) Deployment 和 Rollout 同时拥有。
   - B) 单个 Rollout。
   - C) KEDA 和 Rollout 争夺 replicas。
   - D) Grafana。

<details>
<summary>显示答案</summary>

**答案：B) 单个 Rollout。**

明确 controller 所有权和 Git 期望状态。

</details>

---

3. 为什么要分离 notification 和 analytics queues？
   - A) 在一个 queue 上竞争就是 fanout。
   - B) 这样每个 consumer 都能独立接收相同的 event。
   - C) SQS 仅支持一个 queue。
   - D) 这可以消除所有重复。

<details>
<summary>显示答案</summary>

**答案：B) 这样每个 consumer 都能独立接收相同的 event。**

SNS fanout 和每个 consumer 的 event-ID 去重是不同的职责。

</details>

---

4. 对完全相同的重复 synthetic payment 会发生什么？
   - A) 始终创建新的 payment。
   - B) 复用已存储的结果；冲突的值返回409。
   - C) 对真实卡收费。
   - D) 即使没有订单也始终成功。

<details>
<summary>显示答案</summary>

**答案：B) 复用已存储的结果；冲突的值返回409。**

该实验未实现真实的 payment gateway。

</details>

---

5. 如果在 SNS 发布之后、DB 标记之前发生崩溃，会怎样？
   - A) 自动实现 exactly once。
   - B) 可能会重新投递，因此 consumer 需要去重。
   - C) 删除所有 outbox 行。
   - D) 始终确认消息。

<details>
<summary>显示答案</summary>

**答案：B) 可能会重新投递，因此 consumer 需要去重。**

外部副作用需要额外的幂等性约定。

</details>

---

6. 哪个 workload 会随 SQS backlog 扩缩容？
   - A) 始终只有 API producer。
   - B) 该 queue 的 consumer。
   - C) 数据库管理员。
   - D) NLB。

<details>
<summary>显示答案</summary>

**答案：B) 该 queue 的 consumer。**

KEDA 读取 queue attributes；它不消费消息。

</details>

---

7. canary 成功查询应选择什么？
   - A) 所有 stable 和 canary 流量。
   - B) 仅新的 pod-template revision。
   - C) 每个 namespace。
   - D) 仅部署前的平均值。

<details>
<summary>显示答案</summary>

**答案：B) 仅新的 pod-template revision。**

不要让大量 stable 流量掩盖失败的 canary。

</details>

---

8. 应如何处理空/NaN/Inf 结果？
   - A) 始终为100%成功。
   - B) 不通过成功条件。
   - C) 将所有结果转换为零并通过。
   - D) metrics 并非必需。

<details>
<summary>显示答案</summary>

**答案：B) 不通过成功条件。**

同时检查最低请求数量和可观测性。

</details>

---

9. 哪些 labels 应包含在 metrics 中？
   - A) 每个 order ID。
   - B) Service、受限 route、status 和 revision。
   - C) Customer/card 数据。
   - D) 完整的 request body。

<details>
<summary>显示答案</summary>

**答案：B) Service、受限 route、status 和 revision。**

唯一 ID 会带来基数/隐私问题；请适当使用 trace/log 关联。

</details>

---

10. Rollout abort 是什么意思？
   - A) Git 会自动还原。
   - B) 它与 Git revert 或期望 image 恢复相互独立；请明确恢复 source of truth。
   - C) 所有 DB 写入都会回滚。
   - D) 新 image 会被永久删除。

<details>
<summary>显示答案</summary>

**答案：B) 它与 Git revert 或期望 image 恢复相互独立；请明确恢复 source of truth。**

不要将直接 Helm 和 ArgoCD 用作同时拥有资源的所有者。

</details>

---

[返回指南](../../../labs/observability/03-msa-deployment-lab.md)
