# 事件容量规划 Playbook 测验

1. 当在 KEDA ScaledObject 上配置多个触发器（Cron + Prometheus + SQS）时，最终副本数是如何确定的？
   - A) 所有触发器值的平均值
   - B) 最低值（MIN）
   - C) 最高值（MAX）
   - D) 第一个触发器的值

<details>
<summary>显示答案</summary>

**答案：C) 最高值（MAX）**

**说明：**
当配置多个触发器时，KEDA 会在所有触发器中选择最高的期望副本数。这实现了“cron 设置下限，指标决定上限”的模式。例如，如果 cron 请求 100，而 Prometheus 请求 150，则结果为 150。

</details>

---

2. 在 Pause Pod 模式中，当真实工作负载到达时，什么机制会导致 Pause Pods 被驱逐？
   - A) Pods 会因较小的资源请求而被自动替换
   - B) 较低的 PriorityClass 值触发 Preemption
   - C) DaemonSet 会自动重新分配 Pods
   - D) TTL 到期会导致自动删除

<details>
<summary>显示答案</summary>

**答案：B) 较低的 PriorityClass 值触发 Preemption**

**说明：**
Pause Pods 会被分配一个 value: -10 的 PriorityClass。当真实工作负载（默认优先级为 0 或更高）需要调度且容量不足时，Kubernetes Scheduler 会抢占优先级较低的 Pods 以释放空间。这允许真实工作负载立即调度到已预置的 Nodes 上。

</details>

---

3. 为什么 KEDA cron 触发器设置为在闪购开始前 30 分钟触发？
   - A) KEDA 的轮询间隔是 30 分钟
   - B) Cron 触发器不会在精确时间触发
   - C) Node 预置和 Pod 调度需要提前量
   - D) 为了避免 AWS API 限流

<details>
<summary>显示答案</summary>

**答案：C) Node 预置和 Pod 调度需要提前量**

**说明：**
当 KEDA 扩容 Pods 时，Karpenter 需要 60-90 秒来预置新 Nodes，还需要额外时间进行 Pod 调度和容器启动。提前 30 分钟开始扩容可确保所有 Pods 在第一波流量高峰到来前处于 Ready 状态。

</details>

---

4. 为什么 EC2 Capacity Reservation 设置了 `instance_match_criteria = "targeted"`？
   - A) 为了降低成本
   - B) 为了限制只有特定的 Karpenter NodePools 可以使用该预留
   - C) 为了启用与 Spot instances 配合使用
   - D) 为了多 AZ 部署

<details>
<summary>显示答案</summary>

**答案：B) 为了限制只有特定的 Karpenter NodePools 可以使用该预留**

**说明：**
`targeted` 设置可确保只有显式引用该 Capacity Reservation 的实例才能使用它。这可以防止通用工作负载消耗为事件专用 Karpenter NodePool（通过 capacityReservationSelectorTerms 匹配）预留的容量。

</details>

---

5. Karpenter NodePool 上较高的 `weight` 值有什么作用？
   - A) Nodes 会被更快地预置
   - B) 该 NodePool 会优先于其他 NodePools
   - C) 可以预置更多 Nodes
   - D) 会选择成本更低的实例

<details>
<summary>显示答案</summary>

**答案：B) 该 NodePool 会优先于其他 NodePools**

**说明：**
当多个 NodePools 都能满足 Pending Pod 的需求时，Karpenter 会选择 weight 最高的 NodePool。在事件 NodePool 上设置 weight: 100 可确保它先于默认 NodePool（例如 weight: 10）使用，从而应用事件专用配置（实例类型、容量类型等）。

</details>

---

6. 在 HPA scaleDown 行为中，`type: Percent, value: 10, periodSeconds: 120` 表示什么？
   - A) 在 120 秒内缩容到总数的 10%
   - B) 每 120 秒按当前 Pods 数量减少 10%
   - C) 每 10 秒移除 120 个 Pods
   - D) 保持最少 10 个 Pods，然后在 120 秒后全部移除

<details>
<summary>显示答案</summary>

**答案：B) 每 120 秒按当前 Pods 数量减少 10%**

**说明：**
此策略允许每 120 秒（2 分钟）最多减少当前副本数的 10%。对于 200 个 Pods，这意味着每 2 分钟最多移除 20 个 Pods，从而避免突然缩容导致服务不稳定。

</details>

---

7. 为什么容量规划工作表要增加 30% 的安全余量？
   - A) 为了应对 AWS 实例价格波动
   - B) 为了覆盖预测误差、Pod 启动时间和不均匀的负载分布
   - C) 为了考虑 Kubernetes 系统 Pod 的资源使用
   - D) 由于网络带宽限制

<details>
<summary>显示答案</summary>

**答案：B) 为了覆盖预测误差、Pod 启动时间和不均匀的负载分布**

**说明：**
30% 的安全余量可以吸收多种不确定性：(1) 流量预测可能不准确，(2) Pods 不会同时全部就绪，(3) 负载不会在 Pods 之间完美均匀分布，(4) 某些 Nodes/Pods 可能失败。可以根据以往事件的复盘数据调整该余量。

</details>

---

8. 为什么镜像预缓存 DaemonSet 使用 initContainers？
   - A) 为了运行并终止镜像以节省资源
   - B) 为了将镜像下载（pull）到 Node 缓存并退出，只留下缓存
   - C) 为了验证镜像版本
   - D) 为了向 Container Registry 进行身份验证

<details>
<summary>显示答案</summary>

**答案：B) 为了将镜像下载（pull）到 Node 缓存并退出，只留下缓存**

**说明：**
DaemonSet initContainers 会在每个 Node 上运行并拉取容器镜像。它们只执行 `echo cached` 然后退出，但镜像会保留在 Node 的本地缓存中。当实际工作负载 Pods 稍后被调度时，它们会跳过镜像拉取阶段（该阶段可能需要几十秒到数分钟），从而显著缩短 Pod 启动时间。

</details>

---

9. 为什么 D-30 时间线要求以目标 RPM 的 120% 进行负载测试？
   - A) 为了获得 AWS 对高流量的预先批准
   - B) 为了验证超过目标流量时的系统稳定性，并尽早发现瓶颈
   - C) 为了准确计算 KEDA 触发器阈值
   - D) 为了提高成本估算准确性

<details>
<summary>显示答案</summary>

**答案：B) 为了验证超过目标流量时的系统稳定性，并尽早发现瓶颈**

**说明：**
实际活动流量可能超过预测，因此以 120% 进行测试有助于：(1) 确认系统在目标以上流量下的稳定性，(2) 发现 DB 连接、网络带宽、API gateways 等方面的瓶颈，以及 (3) 在真实活动前验证实际扩缩容链路（KEDA → HPA → Karpenter）的行为。

</details>

---

10. 对于活动，哪种情况最有理由使用 On-Demand instances 而不是 Spot？
    - A) 活动持续时间超过 4 小时
    - B) Spot 节省超过 60%
    - C) 不可接受中断的收入关键型服务
    - D) 工作负载已实现重试逻辑

<details>
<summary>显示答案</summary>

**答案：C) 不可接受中断的收入关键型服务**

**说明：**
Spot instances 可能会被 AWS 提前 2 分钟通知后回收。闪购期间的订单处理等收入关键型服务应使用 On-Demand 来保证可用性。电子邮件通知或日志处理等辅助服务如果有重试逻辑，则可以使用 Spot，在保持韧性的同时节省成本。

</details>
