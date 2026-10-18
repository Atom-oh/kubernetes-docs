# Kubernetes 上的 Spark 基础测验

复习部署模式、职责边界、资源、动态分配和终止条件。

## 1. Spark 4.2 支持哪些 Kubernetes 部署模式？有哪些前置条件？

<details>
<summary>显示答案</summary>

支持 cluster 和 client 两种模式；Spark 4.2 文档要求 Kubernetes 1.34 或更高版本。Client 模式从 Spark 2.4 起受支持，并非只用于 notebook。kubectl 必须与实际使用的 API server 版本兼容。

</details>

## 2. 谁负责请求 executor Pod、选择节点并启动 Pod，以及分配 Spark 任务？

<details>
<summary>显示答案</summary>

Driver 通过 API 请求 executor Pod。Kubernetes scheduler 选择节点，kubelet 启动容器。Driver 中的 Spark scheduler 将任务分配给已注册的 executor。API server 和 driver 都不会取代 Kubernetes 的调度器。

</details>

## 3. 移除 YARN 层是否意味着无需运维基础设施或配置 driver 权限？

<details>
<summary>显示答案</summary>

不是。节点、Kubernetes、镜像、网络、存储和可观测性仍需管理。提交者需要 API 身份验证，而 driver 需要命名空间级 RBAC。示例使用单独的 executor service account；AWS 数据权限与 Kubernetes RBAC 是两种不同权限。

</details>

## 4. 是否必须始终显式设置动态分配和 shuffle tracking 的两个标志？

<details>
<summary>显示答案</summary>

不是。应启用动态分配，但 Spark 4.2 中 shuffle tracking 默认已启用，该功能自 3.0 起提供。标准 Kubernetes ESS 不受支持；在符合相应条件时，可以使用基于 decommission 的保留机制或合适且可靠的 ShuffleDataIO。重叠使用多种机制可能延迟 executor 移除。

</details>

## 5. 启用 decommission 后，会增加哪种终止流程？

<details>
<summary>显示答案</summary>

Spark 4.2 会注入一个运行 `/opt/decom.sh` 的 preStop hook。官方镜像包含此脚本；它会向 executor JVM 发送 SIGPWR 信号并等待。迁移 block 还需要配置存储 decommission 设置，并确保有实际的目标位置、时间和容量。

</details>

## 6. 将 `terminationGracePeriodSeconds` 增加到 60，是否能保证迁移每个 block？

<details>
<summary>显示答案</summary>

不能。Spark 4.2 会覆盖模板中的值，因此还要设置 `spark.kubernetes.executor.terminationGracePeriodSeconds=60s`。默认的 30 秒和配置的 60 秒都包含 preStop 阶段，只是可用时间预算；强制终止、Spot 实例期限或目标容量不足都可能导致迁移无法完成。

</details>

## 7. `allocation.batch.size` 与 executor 的初始/最小数量有什么区别？

<details>
<summary>显示答案</summary>

`batch.size` 控制分批请求 Pod 的数量。最小值/初始值/最大值定义 executor 的数量范围和启动数量，同时还会考虑已有的 `executor.instances`。示例中的 min=2、initial=3、instances=3 表示启动 3 个；节点预置是另一回事。

</details>

## 8. 应如何理解 Spark core、CPU 限制、内存和 Pod 模板？

<details>
<summary>显示答案</summary>

Cores 与默认 CPU request 和 executor 任务处理能力有关；要设置 CPU limit，需使用 `limit.cores`。JVM 示例中的 1 GiB heap 加上至少 384 MiB overhead，会产生 1408 MiB 的 request/limit。Pod 模板由提交者读取并由 Spark 组合处理；它不是可直接用 `kubectl apply` 应用的完整 Pod。

</details>

## 9. 使用 shuffle tracking 和 decommission 时，仍需核实哪些事项？

<details>
<summary>显示答案</summary>

应检查 tracking/空闲超时、强制终止、节点容量和重新计算情况。Client 模式还需要可访问的 driver 端点，并在适用时配置实际管理 driver Pod 的控制器。保留中间数据块不能替代检查点、driver 恢复或端到端 exactly-once 保证。

</details>

---

[返回学习资料](../../../data-on-eks/spark/01-spark-fundamentals.md)
