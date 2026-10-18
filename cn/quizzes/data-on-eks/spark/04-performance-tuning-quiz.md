# 第 4 部分：性能与成本调优测验

基线：Spark 4.2.0 / Karpenter 1.14 · 2026 年 9 月。

## 1. R 系列实例和 NVMe 是否总是最适合 Shuffle？

<details>
<summary>显示答案</summary>

不一定。应测量任务/阶段用时、溢写、Shuffle 获取等待时间、数据倾斜以及 CPU/内存/磁盘/网络瓶颈。比较可用容量和每个成功作业的成本；其他实例系列和 EBS 并非天然不适用。

</details>

## 2. 评估 Graviton 时应检查什么？

<details>
<summary>显示答案</summary>

验证 Spark 镜像、JNI、编解码器、BLAS、Python wheel 和插件是否支持 arm64，然后对有代表性的工作负载进行基准测试。使用已有且经过测试的多架构镜像，可以避免自行构建镜像。

</details>

## 3. 对未挂载的 nvme 设备进行格式化是否安全？

<details>
<summary>显示答案</summary>

不安全。在 Nitro 上，EBS 也会显示为 NVMe；未挂载磁盘上可能仍有数据或分区。设备名称和挂载状态都不能证明它是可丢弃的实例存储。

</details>

## 4. instanceStorePolicy: RAID0 在 AL2023 上会配置什么？

<details>
<summary>显示答案</summary>

Karpenter 使用 NodeConfig 为 kubelet/containerd 临时存储配置实例存储 RAID0，并公布可分配容量。RAID0 不是备份；完整的 NodeClass 仍需配置 AMI、IAM、子网等内容。

</details>

## 5. 为什么本实验可以不使用 hostPath 而使用 NVMe 临时存储？

<details>
<summary>显示答案</summary>

预先配置的 NodeClass 将 kubelet 文件系统放在实例存储上，因此基于磁盘的 emptyDir 会使用该存储。其他节点配置或 tmpfs 会改变其后端存储。

</details>

## 6. Spark 识别哪种临时卷名称？

<details>
<summary>显示答案</summary>

例如 spark-local-dir-scratch：名称以 spark-local-dir- 为前缀，并带有后缀。旧名称 spark-local-dir 不匹配，可能会在相同挂载路径上额外创建一个 emptyDir。

</details>

## 7. emptyDir 的 sizeLimit 会预留磁盘空间吗？

<details>
<summary>显示答案</summary>

不会。还要考虑 requests、节点可分配容量、其他 Pod、日志和可写层。节点可能先被写满；基于内存的 tmpfs 会占用内存预算。

</details>

## 8. 按需型 driver/Spot executor 的组合不能保证什么？

<details>
<summary>显示答案</summary>

它无法消除 driver 故障、漂移或到期的风险，也不能保证 executor 丢失不会造成影响。仅限 Spot 的选择器不会回退到按需型实例，供应短缺时 Pod 可能一直处于 Pending 状态。

</details>

## 9. 污点/容忍度与节点选择器有什么区别？

<details>
<summary>显示答案</summary>

容忍度允许工作负载使用带有相应污点的节点；选择器则指定要匹配的节点。其他 Pod 也可能具有相同的容忍度，而 NoSchedule 不会驱逐现有 Pod。

</details>

## 10. Spot 警告和停用标志能保证迁移完成吗？

<details>
<summary>显示答案</summary>

不能。警告是尽力而为的通知；休眠不提供两分钟的窗口。EventBridge/SQS/中断处理、驱逐、钩子/信号、可用时间、对等容量和网络都很重要。Pod 的 120 秒宽限期不会延长云实例的生命周期。

</details>

## 11. 任意远程存储都会自动成为 Shuffle 回退路径吗？

<details>
<summary>显示答案</summary>

不会。需要配置 spark.storage.decommission.fallbackStorage.path，并准备好对应的文件系统和权限。RDD 缓存恢复与 Shuffle 恢复并不相同；重新计算、获取失败和重试上限仍可能导致作业失败。

</details>

## 12. DRA 和 Karpenter 分别根据哪些信号工作？

<details>
<summary>显示答案</summary>

DRA 根据 Spark 任务积压以及空闲/缓存/Shuffle 状态调整 executor 数量。Karpenter 根据 Pod 请求和调度约束来配置节点。不需要 metrics-server；allocation.batch.size 控制 Kubernetes 分配器创建对象的速率。

</details>

## 13. consolidateAfter 大于 executorIdleTimeout 能保证 DRA 先释放资源吗？

<details>
<summary>显示答案</summary>

不能。这些计时器从不同事件开始；Shuffle/缓存也可能让 executor 保持运行。WhenEmpty 可以减少普通工作负载 Pod 的整合，但漂移、到期和 Spot 终止仍是独立因素。

</details>

## 14. 4g JVM heap 和 cores=2 是否就是 Pod 的全部内存和 CPU 限额？

<details>
<summary>显示答案</summary>

不是。本示例还会增加默认的 409MiB 开销，合计内存为 4505MiB。cores 会影响默认 CPU 请求和 Spark 并发度；使用 spark.kubernetes.executor.limit.cores 显式设置 CPU 限额。还应分别检查 PySpark、堆外内存和显式开销。

</details>

[指南](../../../data-on-eks/spark/04-performance-tuning.md)
