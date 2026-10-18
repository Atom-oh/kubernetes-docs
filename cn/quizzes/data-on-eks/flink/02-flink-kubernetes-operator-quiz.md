# Flink Kubernetes Operator 测验

检查 Operator 1.15.0 / Flink 2.2.1 的安装、状态恢复和自动扩缩容。

1. Deployment 和 SessionJob 有什么区别？

<details>
<summary>显示答案</summary>

**答案**：Deployment 定义 Application/Session 集群；SessionJob 则定义在现有受管 Session 集群上运行的作业。

**说明**：分别管理 SessionJob 并不能隔离共享集群资源或故障。

</details>

2. 历史上的 Kubernetes 1.21+ 最低版本要求足以验证当前 EKS 部署吗？

<details>
<summary>显示答案</summary>

**答案**：不够。应检查当前 EKS 支持情况、客户端版本偏差，以及 Operator/Webhook/CRD 兼容性。

**说明**：命名空间标签功能的引入日期并不是完整的支持或功能验证矩阵。

</details>

3. 蓝绿 CR 会自动切换 Kafka/S3 写入并避免重复吗？

<details>
<summary>显示答案</summary>

**答案**：不会。Consumer group、事务 ID、Sink 输出和状态兼容性都要单独设计。

**说明**：管理子 Deployment 之间的切换，不等于提供端到端数据保证；切换还需要额外的过渡容量。

</details>

4. 保存点升级是否总是最安全、最慢且需要全停机的选择？

<details>
<summary>显示答案</summary>

**答案**：不存在普遍适用的排名；耗时、可恢复性和回退能力取决于作业及状态变更。

**说明**：创建快照并不能证明序列化器、UID 或连接器兼容。

</details>

5. 不健康作业的 last-state 恢复需要什么条件？

<details>
<summary>显示答案</summary>

**答案**：可访问的 HA 元数据/检查点、兼容的状态、凭证和存储。

**说明**：它可以避免创建新的保存点，但不能自动解决元数据丢失或检查点陈旧的问题。

</details>

6. 在 SessionJob YAML 中设置 last-state，就完成了有状态升级的准备吗？

<details>
<summary>显示答案</summary>

**答案**：没有。有效的 Session/作业配置还需要满足检查点、存储和恢复前提条件。

**说明**：应检查验证器和恢复路径，而不能只看模式字符串。

</details>

7. Flink 自动扩缩容器主要调整什么？

<details>
<summary>显示答案</summary>

**答案**：单个作业图顶点的并行度。

**说明**：这与 HPA 的副本扩缩容不同；实际 Pod/节点数量取决于 slot 分配和资源管理层。

</details>

8. 下游目标速率是否只是当前上游输出速率的总和？

<details>
<summary>显示答案</summary>

**答案**：它会综合各上游目标速率与相应边输出比率的乘积，并传播积压处理目标。

**说明**：输出选择性和未来所需容量都很重要。

</details>

9. 自动扩缩容器是否会忽略所有 CPU/内存信号？

<details>
<summary>显示答案</summary>

**答案**：其主要并行度模型使用速率/忙碌时间，但也会考虑内存/GC 压力、配额和可选的内存调优。

**说明**：内存调优默认关闭；不过，这仍与基于 CPU 的 HPA 不同。

</details>

10. Flink 并行度是否必须始终是最大并行度的因数？

<details>
<summary>显示答案</summary>

**答案**：不必。为了平衡键组/分区，自动扩缩容器采用的对齐偏好与 Flink 允许的取值范围不同。

**说明**：应检查对齐模式、按键输入和源分区。更改现有状态的最大并行度时，需要审查兼容性。

</details>

11. 自动扩缩容器每次调整规模时，是否都会执行完整的 last-state 升级？

<details>
<summary>显示答案</summary>

**答案**：不会。在适用时，它会使用原位资源需求 API；某些条件下则需要重新部署。

**说明**：原位扩缩并不保证不会重启任务或产生状态恢复成本。

</details>

12. 为什么这些示例使用 Flink 2.2.1，而不是最新的 2.3.0？

<details>
<summary>显示答案</summary>

**答案**：为了固定一个参照已发布的 Operator/连接器兼容性表核对过的集成基线。

**说明**：CRD 枚举接受较新的取值，并不能证明运行时兼容。

</details>

13. Chart 中配置日志，就能证明 Reporter JAR 和采集服务器已安装吗？

<details>
<summary>显示答案</summary>

**答案**：不能。应区分 Chart 文件、运行时镜像中的 JAR、Reporter 激活状态和指标采集后端。

**说明**：1.15 Chart 包含 Log4j/Logback 配置，但仅有 YAML 并不会自动构成完整的指标流水线。

</details>

14. 设置 watchNamespaces 时还需要检查什么？

<details>
<summary>显示答案</summary>

**答案**：目标命名空间是否存在、生成的作业服务账户/Role/RoleBinding，以及其他授权。

**说明**：空列表会监视所有命名空间。仅设置监视范围并不能完全隔离租户。

</details>

15. 十分钟的指标窗口是否适合所有工作负载？

<details>
<summary>显示答案</summary>

**答案**：不适合。应结合实际 SLO，一起调整窗口、稳定性设置和缩容间隔。

**说明**：窗口太短可能放大噪声；太长则可能延误响应。应通过观察和负载测试来确定。

</details>

16. 默认的 Webhook 安装是否需要 cert-manager？

<details>
<summary>显示答案</summary>

**答案**：需要。经审查的 Chart 会创建 Certificate 和 Issuer 资源，并且没有内部证书生成 Job。

**说明**：应检查控制器/Webhook/cainjector 和 Certificate 是否就绪，而不能只检查 CRD 是否存在。

</details>

17. 默认 Flink 镜像能否运行虚构的 order-events JAR？

<details>
<summary>显示答案</summary>

**答案**：如果没有将该 JAR 打包进镜像，就不能。本章使用随附的 StateMachineExample 验证执行路径。

**说明**：无状态演示与验证持久检查点/HA 恢复是两项不同工作。

</details>

18. 哪些设置可以收集建议但不实际执行扩缩容？

<details>
<summary>显示答案</summary>

**答案**：job.autoscaler.enabled=true 和 job.autoscaler.scaling.enabled=false。

**说明**：应使用当前的 utilization.target/min/max 键，并在启用实际操作前验证建议、状态恢复和配额。

</details>

19. 等待 FlinkDeployment 初始就绪时，应使用哪个条件？

<details>
<summary>显示答案</summary>

**答案**：Running，而不是 Available。

**说明**：它反映已观察到的作业/JM 状态。更新后，要区分过时的条件与针对新 spec 的实际协调情况。

</details>

20. 对 6,000 条积压记录，将 catch-up.duration 从 600 秒缩短到 60 秒，会如何改变额外目标速率？

<details>
<summary>显示答案</summary>

**答案**：会从每秒 10 条增加到每秒 100 条。

**说明**：目标恢复时间越短，所需容量越大。这不是忽略积压的宽限期；设为零会禁用基于积压的扩缩容。

</details>

---

[返回学习资料](../../../data-on-eks/flink/02-flink-kubernetes-operator.md)
