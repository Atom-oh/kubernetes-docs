# EKS 上的模型训练测验

关于当前 API、启动器（launcher）与恢复边界的 15 道题。

## 1. 张量并行（tensor parallelism）对什么进行切分？

<details>
<summary>答案与解释</summary>

层内部的张量运算与权重。DP 在副本之间切分数据，PP 切分层的阶段，专家并行切分专家/token 分发；它们的通信方式各不相同。
</details>

## 2. 应如何规划 200B 模型与全局批量（global batch）？

<details>
<summary>答案与解释</summary>

不要仅凭模型规模就强制采用 3D 并行；要考虑训练状态、激活值、通信与设备网格（device mesh）。TP8×PP4×DP2 为 64 个 rank，但微批量 1×梯度累积 32×DP2 得到的全局批量为 64。
</details>

## 3. slurmctld 与 slurmdbd 在状态职责上有何不同？

<details>
<summary>答案与解释</summary>

slurmctld 管理运行中的作业/节点/分区状态、调度以及 StateSaveLocation。slurmdbd 负责记账数据库记录，并不能替代控制器的恢复状态。
</details>

## 4. Slinky 1.2.2 的计算组（compute-group）API 是什么？

<details>
<summary>答案与解释</summary>

slinky.slurm.net/v1beta1 的 NodeSet，使用 Controller 引用/模板。默认为 StatefulSet 风格的扩缩容，也可选 DaemonSet 风格；在 DaemonSet 模式下 replicas 会被忽略。其 kind 不是 SlurmNodeSet。
</details>

## 5. 仅设置 FI_PROVIDER=efa 就能让 NCCL 走 EFA 吗？

<details>
<summary>答案与解释</summary>

不能。还需要 EFA 接口、驱动/libfabric/aws-ofi-nccl、device plugin（设备插件）/Pod 分配、安全组以及同一可用区（AZ）内的放置。请通过日志/集合通信测试验证实际使用的传输方式；400Gbps 并非普遍适用。
</details>

## 6. 使用 BioNeMo 3.0.0 时应检查什么？

<details>
<summary>答案与解释</summary>

在 BioNeMo Recipes 中确认模型/TransformerEngine/训练配方的支持情况。不要在未验证的情况下沿用旧的 1.5 版 MegaMolBART 模块；应验证镜像/数据/模型版本、设备、收敛性以及生物学层面的评估。
</details>

## 7. Optimum Neuron Trainer 能保证训练任意 HF 模型吗？

<details>
<summary>答案与解释</summary>

不能。需要匹配特定版本的训练模型实现、配置、SDK/PyTorch、硬件、数据与 collator。推理支持与训练支持并不相同；仅有一个预训练模型和未定义的数据集并不构成 TP 训练的实现。
</details>

## 8. 应如何验证 FSx 与 S3 的集成？

<details>
<summary>答案与解释</summary>

区分静态挂载与动态制备（dynamic provisioning），并验证 DRA/导入/导出策略、完成状态与权限。EFS PVC 的容量并不是配额，而仅使用本地存储也无法建立 S3 级别的持久性。
</details>

## 9. Volcano 的 minAvailable:4 是否要求四个节点？

<details>
<summary>答案与解释</summary>

不是；它统计的是 Pod/成员数量。三个节点也可能容纳四个 Pod。请检查最小成员数/资源条件以及 gang 插件；它并不保证同时启动或训练成功。
</details>

## 10. BF16 与 FP16 有何不同？

<details>
<summary>答案与解释</summary>

它有 8 位指数位/7 位尾数位。其指数位数与 FP32 相同，但精度和可表示的确切最大有限值并不相同。通常不需要 FP16 那样的损失缩放（loss scaling），但仍需验证硬件/算子/收敛性；autocast 并不会转换所有训练状态。
</details>

## 11. 激活检查点与恢复检查点有何不同？

<details>
<summary>答案与解释</summary>

激活检查点（activation checkpointing）以反向重算换取显存；这与保存到磁盘的模型/优化器/RNG 恢复状态不同。请验证 use_reentrant、RNG/状态与梯度，不要假定固定能节省 3–4 倍。
</details>

## 12. ZeRO Stage 3 会自动卸载（offload）到 CPU 吗？

<details>
<summary>答案与解释</summary>

不会。它切分优化器状态、梯度与参数；卸载需要单独配置。显存的降低取决于 DP 规模、状态、缓冲区与激活值，并非可以无限扩展。
</details>

## 13. MPIJob 的 slotsPerWorker 确定了什么？

<details>
<summary>答案与解释</summary>

worker 的 hostfile slot 数量。实际进程数取决于 mpirun -np/映射方式与启动器设置；每个 GPU 绑定一个 rank 需要显式配置。Operator 0.8.2 使用 v2beta1 API。
</details>

## 14. 应如何验证检查点频率与恢复？

<details>
<summary>答案与解释</summary>

依据保存延迟、故障率、可接受的丢失工作量与保留成本来选择间隔。验证完整的状态/清单/校验和、远端写入完成以及实际能够恢复。本指南会对比连续四次不中断更新与在两次后恢复的 CPU 结果是否一致。
</details>

## 15. 同一可用区内的 EFA 放置与 Karpenter 中断预算（disruption budget）意味着什么？

<details>
<summary>答案与解释</summary>

将 Pod/NodePool 的约束关联起来，使相互通信的 worker 真正位于同一可用区。为获得性能，建议使用放置组（placement group）。预算为 0 只会限制自愿中断，并不能阻止 Spot 回收、故障或强制终止。
</details>

[返回指南](../../ai-ml/05-model-training.md)
