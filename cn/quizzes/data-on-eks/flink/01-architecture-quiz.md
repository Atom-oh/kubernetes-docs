# Kubernetes 上的 Flink 架构测验

检查你对 Flink 2.2.1 / Operator 1.15.0 执行角色和资源边界的理解。

1. JobManager 是否总是构建初始执行图，而客户端不承担任何计算？

<details>
<summary>显示答案</summary>

**答案**：不是。应用的 main() 在 JM 上运行，而普通的 2.2 Session CLI 提交会在客户端构建执行图。

**解释**：JM 负责协调执行、slot、检查点和恢复；TM 执行任务。用户 main() 本身也可能消耗 JM 资源。

</details>

2. 四个 TaskManager slot 是否意味着最多只能有四个算子子任务？

<details>
<summary>显示答案</summary>

**答案**：不是。算子链和 slot 共享可以让多个算子位于同一个 slot 中。

**解释**：经典固定 slot 主要是托管内存分配单元，并不代表一个 CPU 核，也不是独立的 CPU 隔离边界。

</details>

3. Application 模式是否总意味着每个作业对应一个集群，并且共享的 EKS 资源完全隔离？

<details>
<summary>显示答案</summary>

**答案**：不是。一个应用/main() 可以创建多个作业，而且节点、网络、存储和配额可能由多个工作负载共享。

**解释**：应用级生命周期/JVM 隔离有所帮助，但并非绝对隔离。请检查 2.2 对多个 execute 的 Application HA 支持限制。

</details>

4. 向现有 Session 集群提交作业是否总能立即开始执行？

<details>
<summary>显示答案</summary>

**答案**：不是。集群启动开销可能减少，但 slot、CPU、状态恢复和共享负载仍可能延迟执行。

**解释**：Session 作业会共享 JM/TM 资源；一个 TM 故障可能影响使用该 TM 的多个作业。

</details>

5. 本章是否应将 Per-Job 视为当前第三种 Native Kubernetes 模式？

<details>
<summary>显示答案</summary>

**答案**：不应。本章介绍的生命周期选项是 Application 和 Session；Per-Job 已属于历史模式。

**解释**：Application/Session 与 Native/Standalone 资源管理选项是不同的分类维度。

</details>

6. 谁负责管理 Native TaskManager Pod 以及承载这些 Pod 的 EKS 节点？

<details>
<summary>显示答案</summary>

**答案**：Flink 的 Kubernetes ResourceManager 通过 API 请求 TM Pod；Karpenter/Cluster Autoscaler 则单独管理节点容量。

**解释**：TM 何时释放取决于空闲超时、资源配置文件和需求。作业完成后，并非所有 Pod/节点都会立即移除。

</details>

7. Kubernetes 上的 Standalone 模式中，TaskManager 数量是否只能通过手动修改 YAML 来调整？

<details>
<summary>显示答案</summary>

**答案**：不是。Operator 等外部控制器可以协调 Kubernetes 资源。

**解释**：在 Native 资源管理模式下，Flink 运行时不会直接请求 TM Pod。对于 HA 等功能，还应单独评估 API 权限。

</details>

8. Operator 1.15.0 的两个集群/作业自定义资源（CR）是什么？它是否只支持 Native 模式？

<details>
<summary>显示答案</summary>

**答案**：FlinkDeployment 和 FlinkSessionJob；两种模式 Native 和 Standalone 都受支持。

**解释**：Deployment 定义 Application/Session 集群；SessionJob 则针对一个现有且由 Operator 管理的 Session 集群。仅凭某个枚举值存在，并不能证明集成兼容性。

</details>

---

[返回学习资料](../../../data-on-eks/flink/01-architecture.md)
