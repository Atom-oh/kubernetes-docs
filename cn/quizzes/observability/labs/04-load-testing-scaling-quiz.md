# 可观测性实验第 4 部分：负载测试与自动扩缩容测验

> **最后更新**: February 22, 2026

检验你对可观测性端到端实验第 4 部分中涵盖的负载测试和自动扩缩容概念的理解。

---

1. k6 中的 Virtual User (VU) 是什么，以及如何配置分阶段负载模式？
   - A) VU 是一个网络连接；阶段在 JSON 文件中配置
   - B) VU 表示并发执行测试脚本的模拟用户；阶段通过包含目标 VU 和持续时间的 stages 进行配置
   - C) VU 是一个 CPU 线程；阶段只能通过命令行标志设置
   - D) VU 是一个请求队列；阶段需要单独的测试脚本

<details>
<summary>显示答案</summary>

**答案：B) VU 表示并发执行测试脚本的模拟用户；阶段通过包含目标 VU 和持续时间的 stages 进行配置**

**解释：**
在 k6 中，Virtual User (VU) 是运行测试脚本的独立执行上下文——每个 VU 都会模拟发出请求的真实用户。分阶段负载模式使用 `options` 块中的 `stages` 选项：每个阶段定义一个 `target`（VU 数量）和 `duration`（达到该目标所需的时间）。例如，在 2 分钟内逐步增加到 100 个 VU，保持 5 分钟，然后逐步减少。这支持渐进式增载、稳态和峰值测试等真实的负载配置文件。

</details>

---

2. k6 和 Locust 在负载测试方面的主要区别是什么？
   - A) k6 使用 Python 编写，而 Locust 使用 Go 编写
   - B) k6 使用 JavaScript 编写测试脚本，并使用 Go runtime 提供性能；Locust 使用 Python 和分布式架构
   - C) Locust 仅支持 HTTP/1.1，而 k6 支持所有协议
   - D) k6 需要 GUI，而 Locust 仅提供 CLI

<details>
<summary>显示答案</summary>

**答案：B) k6 使用 JavaScript 编写测试脚本，并使用 Go runtime 提供性能；Locust 使用 Python 和分布式架构**

**解释：**
k6 凭借基于 Go 的 runtime 提供高性能，同时为测试脚本使用熟悉的 JavaScript/ES6，并提供内置指标和出色的 CI/CD 集成。Locust 使用 Python 编写测试脚本，使 Python 开发者更易上手，并可为复杂测试逻辑提供高度灵活性；它还提供用于实时监控的 Web UI 和便捷的分布式测试。k6 通常可以在每个实例上处理更高负载；Locust 则在测试逻辑方面提供更大的灵活性和更直观的体验。

</details>

---

3. KEDA 的 SQS scaler 如何确定何时扩缩容 Pods？
   - A) 它根据现有 Pods 的 CPU 利用率进行扩缩容
   - B) 它查询 SQS 队列指标，并根据队列消息与每个 Pod 的配置目标值之间的比率扩缩容 Pods
   - C) 它根据队列中消息的存留时间进行扩缩容
   - D) 它仅在计划的时间窗口内进行扩缩容

<details>
<summary>显示答案</summary>

**答案：B) 它查询 SQS 队列指标，并根据队列消息与每个 Pod 的配置目标值之间的比率扩缩容 Pods**

**解释：**
KEDA 的 SQS scaler 会定期查询 SQS 以获取队列深度指标。它按以下方式计算所需副本数：`queue_length / queueLength_target`。例如，有 100 条消息且 `queueLength: 10` 时，KEDA 的目标是 10 个 Pods。它还会遵守 `minReplicaCount` 和 `maxReplicaCount` 的边界。当队列为空时，它可以缩容至零（如果已配置），并在消息到达时扩容。scaler 使用 IAM 凭证（通过 IRSA）访问 SQS 指标。

</details>

---

4. KEDA 的 Prometheus scaler 如何查询指标以做出扩缩容决策？
   - A) 它仅支持 Prometheus 的内置指标
   - B) 它针对 Prometheus server 执行配置的 PromQL 查询，并根据返回值与阈值的比较进行扩缩容
   - C) 它要求 Prometheus 中使用专用的 KEDA metrics exporter
   - D) 它只能查询 counter 指标，不能查询 gauge 指标

<details>
<summary>显示答案</summary>

**答案：B) 它针对 Prometheus server 执行配置的 PromQL 查询，并根据返回值与阈值的比较进行扩缩容**

**解释：**
KEDA Prometheus scaler 会针对配置的 Prometheus endpoint 执行任何有效的 PromQL 查询。你需要指定 `serverAddress`、`query` (PromQL) 和 `threshold`。KEDA 会扩缩容 Pods，使 `query_result / threshold = replica_count`。这支持根据业务指标（请求/秒、队列深度）、自定义应用程序指标或任何可查询的数据进行扩缩容。对于受保护的 Prometheus 实例，身份验证支持 bearer tokens 或 TLS。

</details>

---

5. Karpenter 如何检测 Pending Pods 并预置合适的节点？
   - A) 它轮询 Kubernetes API 以查找 PodScheduled=False 的 Pods，并将其要求与 NodePool 模板进行匹配
   - B) 它要求 Pods 通过 annotations 显式请求 Karpenter 预置
   - C) 它监控集群 CPU 使用率并预置节点
   - D) 它在预置前等待 Horizontal Pod Autoscaler 信号

<details>
<summary>显示答案</summary>

**答案：A) 它轮询 Kubernetes API 以查找 PodScheduled=False 的 Pods，并将其要求与 NodePool 模板进行匹配**

**解释：**
Karpenter 会监视不可调度的 Pods（即因没有任何现有节点能满足其要求而处于 Pending 状态的 Pods）。检测到后，它会分析 Pod 要求（资源请求、node selectors、tolerations、topology constraints），并从已配置的 NodePools 预置最优的 EC2 实例。Karpenter 的 bin-packing 算法可高效地对 Pending Pods 分组，并选择在满足要求的同时将成本降至最低的实例类型。这种“just-in-time”预置方式比 Cluster Autoscaler 基于 node group 的方法更快。

</details>

---

6. Karpenter 的 Consolidation 策略如何实现成本优化？
   - A) 它仅在现有节点内整合 Pods
   - B) 它识别利用率不足或为空的节点，并迁移工作负载以减少节点总数，终止不必要的节点
   - C) 它整合来自多个节点的日志
   - D) 它仅在计划的维护窗口内工作

<details>
<summary>显示答案</summary>

**答案：B) 它识别利用率不足或为空的节点，并迁移工作负载以减少节点总数，终止不必要的节点**

**解释：**
Karpenter 的 consolidation 会持续评估集群效率。它通过以下方式识别降低成本的机会：立即终止空节点、以仍满足要求的更低成本替代方案替换节点，以及将多个利用率不足节点上的工作负载整合到更少的节点上。consolidation 会遵守 pod disruption budgets 并使用优雅终止。这种自动化的 right-sizing 确保你只为所需容量付费，并以智能缩容补充扩容。

</details>

---

7. 在 Grafana dashboards 中进行负载测试时，应观察哪些关键 RED 指标？
   - A) RAM、Ethernet、Disk
   - B) Rate（请求/秒）、Errors（错误率/计数）、Duration（延迟分布）
   - C) Replicas、Events、Deployments
   - D) Reads、Executions、Deletions

<details>
<summary>显示答案</summary>

**答案：B) Rate（请求/秒）、Errors（错误率/计数）、Duration（延迟分布）**

**解释：**
RED 指标是服务监控的标准方法论：Rate 衡量吞吐量（每秒请求数），Errors 跟踪失败率或数量（4xx、5xx 响应），Duration 捕获延迟分布（p50、p95、p99 响应时间）。在负载测试期间，这些指标会揭示系统在压力下的表现：吞吐量是否趋于平稳？错误是否激增？延迟是否恶化？RED dashboards 可立即呈现服务运行状况，并有助于识别临界点。

</details>

---

8. 如何使用 Prometheus 指标跟踪扩缩容事件期间 Pod 数量的变化？
   - A) 仅使用 `kube_pod_created` 时间戳
   - B) 使用 `kube_deployment_status_replicas` 跟踪当前副本数，并将其与 `kube_deployment_spec_replicas` 进行比较以获取所需副本数
   - C) Prometheus 中没有 Pod 数量指标
   - D) 使用按 Pod 聚合的 `container_cpu_usage`

<details>
<summary>显示答案</summary>

**答案：B) 使用 `kube_deployment_status_replicas` 跟踪当前副本数，并将其与 `kube_deployment_spec_replicas` 进行比较以获取所需副本数**

**解释：**
kube-state-metrics 会公开 Deployment 副本信息：`kube_deployment_spec_replicas` 显示所需副本数（HPA/KEDA 的目标），`kube_deployment_status_replicas` 显示当前就绪副本数，`kube_deployment_status_replicas_available` 显示可用副本数。对这些指标绘制时间序列图可揭示扩缩容行为——实际副本与所需副本匹配的速度、是否存在振荡，以及扩容/缩容的时间。对于 HPA 特定指标，`kube_horizontalpodautoscaler_*` 指标会提供更多细节。

</details>

---

9. `stabilizationWindowSeconds` 设置在 KEDA 扩缩容行为中起什么作用？
   - A) 它设置 Pod 在终止前必须运行的最短时间
   - B) 它定义缩容期间的回溯窗口，通过考虑该时间段内的最高建议值来防止快速振荡
   - C) 它配置指标查询之间的间隔
   - D) 它设置 Pod 启动的最长时间

<details>
<summary>显示答案</summary>

**答案：B) 它定义缩容期间的回溯窗口，通过考虑该时间段内的最高建议值来防止快速振荡**

**解释：**
`stabilizationWindowSeconds` 可防止缩容期间发生抖动。缩容时，KEDA 会查看过去 N 秒内（即稳定窗口）的所有扩缩容建议，并使用最高值。这可防止短暂的指标下降触发缩容、而负载恢复后立即又扩容的情况。例如，300 秒窗口意味着只有当指标持续低位 5 分钟时才会缩容。扩容通常不会稳定化，以确保对负载增加快速响应。

</details>

---

10. 在基于队列的工作负载架构中，SQS 队列深度如何与 Pod 扩缩容相关联？
    - A) 队列深度和 Pod 数量始终成反比
    - B) 随着队列深度增加，KEDA 会扩容 Pods 以更快处理消息，从而降低队列深度；随着队列排空，Pods 会缩容
    - C) 队列深度仅影响内存分配，不影响 Pod 数量
    - D) Pod 扩缩容独立于队列深度发生

<details>
<summary>显示答案</summary>

**答案：B) 随着队列深度增加，KEDA 会扩容 Pods 以更快处理消息，从而降低队列深度；随着队列排空，Pods 会缩容**

**解释：**
在基于队列的架构中，存在一个反馈循环：传入消息会增加队列深度，KEDA 检测到这一点并扩容 consumer Pods，更多 Pods 会更快地处理消息（提高吞吐量），队列深度随之下降，最终当队列可控时 KEDA 会缩容 Pods。`queueLength` 阈值决定每个 Pod 的目标消息数。将队列深度与 Pod 数量一同观察可以揭示处理能力——如果即使 Pods 已达到最大数量，队列深度仍在增长，那么你就发现了一个需要优化或提高限制的瓶颈。

</details>
