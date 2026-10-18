# EKS 上的模型训练测验

关于当前 API、启动器和恢复边界的 15 个问题。

## 1. 张量并行会对什么进行分区？

<details>
<summary>答案与说明</summary>

对层内的张量运算和权重进行分区。DP 会在副本之间对数据进行分区，PP 会对层阶段进行分区，专家并行会对专家/Token 分发进行分区；它们的通信方式各不相同。
</details>

## 2. 应如何规划 200B 模型和全局批次？

<details>
<summary>答案与说明</summary>

不要仅凭模型大小就强制采用 3D 并行；还要考虑训练状态、激活值、通信和设备网格。TP8×PP4×DP2 是 64 个 rank，但 microbatch1×accumulation32×DP2 得到的全局批次为 64。
</details>

## 3. slurmctld 和 slurmdbd 的状态管理职责有何不同？

<details>
<summary>答案与说明</summary>

slurmctld 管理运行中的作业/节点/分区状态、调度和 StateSaveLocation。slurmdbd 处理记账数据库记录，不能替代控制器的恢复状态。
</details>

## 4. Slinky1.2.3 的计算组 API 是什么？

<details>
<summary>答案与说明</summary>

使用 slinky.slurm.net/v1beta1 NodeSet，并引用 Controller/template。默认采用 StatefulSet 风格扩缩容，也可选择 DaemonSet 风格；在 DaemonSet 模式下会忽略 replicas。其 kind 不是 SlurmNodeSet。
</details>

## 5. 仅设置 FI_PROVIDER=efa 就能启用通过 EFA 运行的 NCCL 吗？

<details>
<summary>答案与说明</summary>

不能。需要 EFA 接口、driver/libfabric/aws-ofi-nccl、device plugin/Pod 分配、安全组和同一 AZ 部署。通过日志/collective 测试验证实际传输方式；400Gbps 并非普遍适用。
</details>

## 6. 对 BioNeMo3.0.0 应检查什么？

<details>
<summary>答案与说明</summary>

检查 BioNeMo Recipes 中的模型/TransformerEngine/训练配方支持。不要未经验证就沿用旧版1.5 MegaMolBART 模块；应验证镜像/数据/模型版本、设备、收敛情况和生物学评估。
</details>

## 7. Optimum Neuron Trainer 能保证训练所有 HF 模型吗？

<details>
<summary>答案与说明</summary>

不能。需匹配特定版本的训练模型实现、配置、SDK/PyTorch、硬件、数据和 collator。推理支持与训练支持不同；预训练模型和未定义的数据集并不能实现 TP 训练。
</details>

## 8. 应如何验证 FSx 和 S3 集成？

<details>
<summary>答案与说明</summary>

区分静态挂载和动态置备，并验证 DRA/导入/导出策略、完成情况和权限。EFS PVC 容量并非配额，仅使用本地存储也不能确保 S3 持久性。
</details>

## 9. Volcano 的 minAvailable:4 要求四个节点吗？

<details>
<summary>答案与说明</summary>

不要求；它统计的是 Pod/成员数量。四个 Pod 可能分布在三个节点上。检查最小成员数/资源条件和 gang 插件；它不能保证同时启动或训练成功。
</details>

## 10. BF16 与 FP16 有何不同？

<details>
<summary>答案与说明</summary>

它有 8 位指数/7 位尾数。其指数位数与 FP32 相同，但精度和最大有限值并不相同。通常不需要 FP16 风格的 loss scaling，但仍需验证硬件/运算/收敛情况；autocast 不会转换所有训练状态。
</details>

## 11. 激活检查点与恢复检查点有何不同？

<details>
<summary>答案与说明</summary>

激活检查点通过反向传播时重新计算来换取内存空间；它不同于用于恢复的磁盘模型/优化器/RNG 状态。验证 use_reentrant、RNG/状态和梯度，不要假定能固定节省 3–4 倍内存。
</details>

## 12. ZeRO Stage3 会自动将数据卸载到 CPU 吗？

<details>
<summary>答案与说明</summary>

不会。它会对优化器状态、梯度和参数进行分区；卸载需单独配置。内存减少量取决于 DP 大小、状态、缓冲区和激活值，并非可以无限扩展。
</details>

## 13. MPIJob 的 slotsPerWorker 表示什么？

<details>
<summary>答案与说明</summary>

它表示 worker hostfile 中的 slots 数量。实际进程数取决于 mpirun -np/mapping 和启动器设置；每个 GPU 绑定一个 rank 需要显式配置。Operator0.8.2 使用 v2beta1 API。
</details>

## 14. 应如何验证检查点频率和恢复能力？

<details>
<summary>答案与说明</summary>

根据保存延迟、故障率、可接受的工作损失和保留成本选择间隔。验证完整状态/清单/校验和、远程保存完成情况以及实际恢复能力。本指南会检查以下两种情况的 CPU 结果是否相同：不中断地更新四次，以及更新两次后恢复并继续运行。
</details>

## 15. 同一 AZ 中的 EFA 部署和 Karpenter 中断预算意味着什么？

<details>
<summary>答案与说明</summary>

配置 Pod/NodePool 约束，确保通信中的 worker 实际位于同一 AZ。建议使用置放群组以提升性能。预算 0 会限制自愿中断，但无法阻止 Spot 回收、故障或强制终止。
</details>

[返回指南](../../ai-ml/05-model-training.md)
