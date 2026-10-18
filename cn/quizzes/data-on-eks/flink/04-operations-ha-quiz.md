# 运维、高可用性和托管 Flink 测验

检查采集路径、内存/恢复边界和托管服务支持范围。

1. 经审查的 Kubernetes 高可用领导者选举使用哪种资源？

<details>
<summary>显示答案</summary>

**答案**：Fabric8 ConfigMapLock，依赖 Kubernetes 控制平面的可用性。

**解释**：它不会额外添加独立的领导者选举服务器，也不一定使用 Lease 资源。ZooKeeper HA 也是受支持的替代方案。

</details>

2. HA ConfigMap、HA `storageDir` 和检查点目录是否存储相同数据？

<details>
<summary>显示答案</summary>

**答案**：ConfigMap 保存领导者信息/引用，HA `storageDir` 保存 JM 恢复元数据/作业图，检查点目录则保留检查点状态。

**解释**：设置一条 HA 路径，并不能预先准备好所有状态文件或恢复权限。

</details>

3. 仅为 HA 配置的 ConfigMap Role 是否提供了 Flink Native 模式所需的全部权限？

<details>
<summary>显示答案</summary>

**答案**：没有。Native 资源管理还需要 Pod/Service 和其他适当权限。

**解释**：应逐一检查每个调用方的需求，并查看 API 错误、日志和重启记录；失败不一定会被静默处理。

</details>

4. Flink 自动扩缩容控制器和节点自动扩缩容控制器主要分别调整什么？

<details>
<summary>显示答案</summary>

**答案**：分别调整算子并行度和节点容量。

**解释**：压力、配额、状态恢复和 Pod 放置会让两个控制循环相互影响；Flink 并不总是先采取行动。

</details>

5. Karpenter 是否必须为每个 Pending Pod 都创建一个节点？

<details>
<summary>显示答案</summary>

**答案**：不必。应区分无法调度的 Pod 与镜像拉取、PVC、准入或其他问题。

**解释**：约束条件、资源请求、实例供应情况和配额都可能阻止节点预置。

</details>

6. 将节点整合延迟设得长于 Flink 稳定时间，是否能避免中断？

<details>
<summary>显示答案</summary>

**答案**：不能保证。节点故障、Spot 回收和资源漂移可能独立发生。

**解释**：应结合测试节点预置、状态恢复、积压追赶，以及中断/PDB 策略。

</details>

7. 托管 Flink 支持 2.3，是否意味着所有上游功能都可用？

<details>
<summary>显示答案</summary>

**答案**：不是。应核实 Java 17/Python 3.12 组合以及服务专属的排除项。

**解释**：限制项包括 Java 21、ForSt、Native S3、自定义遥测和 Studio。应区分 AWS 基础设施高可用性与应用/状态管理职责。

</details>

8. 应如何将托管 Flink 的 KPU 成本与 EKS Spot 成本进行比较？

<details>
<summary>显示答案</summary>

**答案**：在吞吐量、延迟和恢复目标相同的条件下，比较总成本和运维成本。

**解释**：KPU 方案应计入编排及相关存储/网络成本；Spot 方案应计入中断和恢复成本。

</details>

9. RocksDB 托管内存和网络缓冲区是否共用同一内存池？

<details>
<summary>显示答案</summary>

**答案**：不是。它们属于各自独立的预算区域。

**解释**：在检查过的 4 GiB 配置中，将托管内存比例从 0.4 调到 0.5 后，网络预算没有变化，而任务堆内存减少。预算数值与实测 RSS 不同。

</details>

10. PodMonitor 对象存在，但没有发现任何采集目标时，应检查哪些内容？

<details>
<summary>显示答案</summary>

**答案**：Prometheus 监视器/命名空间选择器、实际 Pod 标签、命名端口、目标命名空间和服务发现权限。

**解释**：此 chart 的 Operator Pod 缺少默认的 instance 标签。Deployment 元数据不会自动成为 Pod 标签。

</details>

11. `block-cache-usage` 是比率吗？Flink Counter 是否总会映射成 Prometheus Counter？

<details>
<summary>显示答案</summary>

**答案**：都不是。缓存使用量以字节计，而经审查的指标导出器会将 Flink Counter 导出为 Gauge。

**解释**：还应结合缓存容量/命中/未命中来解读。Histogram 会映射为 Summary；应检查导出的 TYPE 和标签。

</details>

12. 是否应在由 Operator 管理的 CR 中直接设置 `kubernetes.cluster-id`？

<details>
<summary>显示答案</summary>

**答案**：不应。1.15 验证器禁止这样做；集群标识由 CR 名称/命名空间管理。

**解释**：不要盲目复制底层 CLI 配置。`kubernetes.namespace` 和 `high-availability.cluster-id` 也受到限制。

</details>

13. 两个 JM 副本和一份已完成的检查清单，是否保证恢复立即且不中断？

<details>
<summary>显示答案</summary>

**答案**：不能。应验证选举、节点/AZ 放置、存储、状态恢复、重放时间和实际结果。

**解释**：保留默认值也可能是有效选择。除配置项之外，还应关注实测的 SLO/恢复结果和运维责任归属。

</details>

---

[返回学习资料](../../../data-on-eks/flink/04-operations-ha.md) | [Flink](../../../data-on-eks/flink/README.md)
