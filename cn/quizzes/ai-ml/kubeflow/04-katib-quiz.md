# 第 4 部分：Katib — 超参数调优与 AutoML 测验

本测验用于检验你对 Katib 的 Experiment/Trial/Suggestion 架构、其支持的搜索算法、提前停止、指标收集，以及在 EKS 上运行 Katib 时资源压力考量的理解。

## 选择题

1. 在 Katib 架构中，Experiment、Trial 和 Suggestion 之间是什么关系？
   - A) 它们是同一个 CRD 的三个可互换名称
   - B) 一个 Suggestion 拥有多个 Experiment，而每个 Experiment 拥有一个 Trial
   - C) 一个 Experiment 拥有多个 Trial，每个 Trial 运行一个特定的超参数组合，而 Suggestion Service 提出这些组合
   - D) 一个 Trial 拥有多个 Experiment，并由单个全局 Suggestion 协调

<details>
<summary>显示答案</summary>

**答案：C) 一个 Experiment 拥有多个 Trial，每个 Trial 运行一个特定的超参数组合，而 Suggestion Service 提出这些组合**

**说明：**
一个 Experiment 对象描述调优；maxTrialCount 是完成次数标准，而不是成功训练次数或不可变的支出上限。每个 Trial 是一次使用特定超参数组合的单独训练运行。Suggestion Service 实现一种算法；它如何使用先前的观测结果取决于该算法。
</details>

2. 哪种搜索算法会构建超参数如何映射到目标指标的概率模型，并使用该模型选择下一个最有希望尝试的点？
   - A) 网格搜索
   - B) 随机搜索
   - C) 贝叶斯优化
   - D) Hyperband

<details>
<summary>显示答案</summary>

**答案：C) 贝叶斯优化**

**说明：**
贝叶斯优化会构建一个将超参数与目标关联起来的概率模型，并使用它选择最有可能改进目前最佳结果的下一个候选点。随机搜索独立采样，不会记忆过去的 Trial；网格搜索会穷举离散组合；Hyperband 会广泛分配少量预算，并将其重新分配给早期存留下来的候选项。
</details>

3. 与向每个配置提供完整且相等的训练预算相比，Hyperband 做出了什么权衡？
   - A) 它会在比较前将每个配置都训练至完全完成
   - B) 它为许多配置提供少量预算，提前丢弃表现最差的配置，并将释放的预算重新分配给存留下来的配置
   - C) 它一次只会尝试一个配置
   - D) 它完全忽略中间表现，并随机选择配置

<details>
<summary>显示答案</summary>

**答案：B) 它为许多配置提供少量预算，提前丢弃表现最差的配置，并将释放的预算重新分配给存留下来的配置**

**说明：**
Hyperband 用每个配置的详尽信息换取提前剪枝：它起初以较低成本运行许多配置，积极丢弃看起来最弱的配置，并将释放的资源预算提供给仍有希望的配置。
</details>

4. 在 Experiment 的 spec 中，`objective` 字段定义什么？
   - A) 用于运行每个 Trial 的容器镜像
   - B) 要优化的指标，以及是最大化还是最小化该指标
   - C) 可并行运行的 Trial 数量
   - D) 搜索算法的内部超参数

<details>
<summary>显示答案</summary>

**答案：B) 要优化的指标，以及是最大化还是最小化该指标**

**说明：**
`objective` 为指标命名（例如 accuracy 或 loss）并指定目标（最大化或最小化），还可以选择性地包含一个目标值，使 Experiment 在达到该值后提前停止。搜索空间在 `parameters` 下单独定义，而每个 Trial 的 Job 如何运行则在 `trialTemplate` 下定义。
</details>

5. 本次审查验证了 Katib 0.19.0 的 medianstop 阈值计算的什么行为？
   - A) 一旦中位数 Trial 完成，它会完全停止 Experiment
   - B) 它存储成功 Trial 在前 start_step 个观测值上的平均值，然后计算这些平均值的算术平均数
   - C) 它只允许所有提议 Trial 中恰好一半运行
   - D) 它选择中位数超参数值作为最终答案

<details>
<summary>显示答案</summary>

**答案：B) 它存储成功 Trial 在前 start_step 个观测值上的平均值，然后计算这些平均值的算术平均数**

**说明：**
官方指南描述的是中位数规则，但 0.19.0 计算的是算术平均数。成功 Trial 的平均值 [1, 2, 100] 在未修改的函数中会得到约 34.333，而不是统计中位数 2。默认值为 min_trials_required=3 和 start_step=4；还适用 collector/timestamp 要求。
</details>

6. Katib 通常如何从正在运行的 Trial 训练容器中获取目标指标值？
   - A) 训练容器必须从其代码内部直接调用 Katib API
   - B) 已配置的拉取 collector 收集指标，或 Push 模式的 report_metrics() 将指标发送到 DB manager
   - C) Katib 暂停容器并直接检查其内存
   - D) Kubernetes scheduler 自动从资源使用情况中提取指标

<details>
<summary>显示答案</summary>

**答案：B) 已配置的拉取 collector 收集指标，或 Push 模式的 report_metrics() 将指标发送到 DB manager**

**说明：**
StdOut/File/TensorFlowEvent 和 Custom collector 与 Push 模式并存。任意 HTTP 抓取不是内置默认行为。拉取注入需要 namespace 标签、webhook 以及目标 Pod/container 配置。仅 Job 成功并不能证明指标已被收集。
</details>

7. 为什么高 `parallelTrialCount` 比以低并发运行相同的 `maxTrialCount` 会在 EKS 集群上造成更尖锐的资源压力？
   - A) `parallelTrialCount` 不影响创建的 Pod 数量
   - B) 高并行度意味着许多 Trial（及其资源请求，例如 GPU）会同时冲击集群，而不是分散进行，从而产生短暂而剧烈的需求峰值
   - C) EKS 默认将 `parallelTrialCount` 限制为 1
   - D) 并行 Trial 总在同一 Node 上运行，因此不会产生额外需求

<details>
<summary>显示答案</summary>

**答案：B) 高并行度意味着许多 Trial（及其资源请求，例如 GPU）会同时冲击集群，而不是分散进行，从而产生短暂而剧烈的需求峰值**

**说明：**
每个并发 Trial 都是一个完整的训练 Job。需求量为并发数 × 每个 Trial 的 Pod 数 × 每个 Pod 的资源，加上 collector 和 Service 开销——即使 Experiment 的总 `maxTrialCount` 看起来不大，也可能使需求急剧飙升。
</details>

8. 在 EKS 上，如果高 `parallelTrialCount` Experiment 启动后，新创建的 Trial Pod 随即处于 Pending 状态一段时间，可能的解释是什么？
   - A) Suggestion Service 已崩溃
   - B) 它可能在等待容量；请通过 Pod event、NodePool condition、quota、EC2 容量和 bootstrap 状态进行确认
   - C) Katib 总会将新的 Trial 暂停一个固定的预热期
   - D) metrics-collector sidecar 正在阻止 Pod 启动

<details>
<summary>显示答案</summary>

**答案：B) 它可能在等待容量；请通过 Pod event、NodePool condition、quota、EC2 容量和 bootstrap 状态进行确认**

**说明：**
仅凭 Pending 并不能证明 Karpenter 正在成功预置资源。亲和性、污点、卷、quota、容量限制和 bootstrap 失败也可能是原因。请使用观察到的 event 和 controller 状态。
</details>

## 简答题

9. 请列出 Katib 支持的两种搜索算法，并分别用一句话说明每种算法最适合解决什么问题。

<details>
<summary>显示答案</summary>

**答案：** 以下任意两种：随机搜索（适用于大型或理解不足的搜索空间的低成本基线）、网格搜索（对小型、低维离散空间进行穷举覆盖）、贝叶斯优化（通过目标的概率模型减少所需 Trial 总数，适用于每个 Trial 成本高的情形）、Hyperband（利用低成本但信息丰富的早期信号提前剪除表现不佳的配置），或 CMA-ES（协方差自适应进化），或 PBT（需要共享 checkpoint 的独立的基于种群训练策略）。

**说明：**
每种算法对探索成本和搜索效率的权衡不同，正确选择取决于单个 Trial 的成本以及搜索空间具有多少结构。
</details>

10. Hyperband 的作用与提前停止（例如中位数停止规则）有什么区别，鉴于二者都旨在避免浪费计算资源？

<details>
<summary>显示答案</summary>

**答案：** Hyperband 是一种搜索策略，会预先决定为每个配置提供多少资源预算；提前停止是应用于已在进行中的 Trial 的运行时检查，取决于它在训练该时刻相对于同类 Trial 的表现。

**说明：**
二者在不同层级上运作：Hyperband 的剪枝是搜索算法整体预算分配策略的一部分，而提前停止是在 Trial 运行期间做出的逐 Trial 决策，受兼容的 collector/log 配置约束，并非每种组合都自动支持。
</details>

## 动手 / 应用题

11. 你正在配置一个 Experiment，其中每个 Trial 请求一个 GPU，而集群有一个用于 GPU instance 的 Karpenter NodePool，预置新容量通常需要数分钟。你设置了 `maxTrialCount: 60`，并正在决定 `parallelTrialCount`。请用几句话说明在此环境中将其设为较高值（例如 20）与较低值（例如 4）之间的权衡。

<details>
<summary>显示答案</summary>

**答案：** 较高的 `parallelTrialCount`（例如 20）可在容量可用时以更少的轮次处理 Trial，但会产生 20 个同时发生的 GPU 请求的尖锐峰值，这可能超过 Karpenter 预置 GPU Node 的速度——导致早期 Trial 处于 Pending 而非训练状态；如果其他工作负载正在竞争同一 GPU NodePool，还可能使共享集群容量急剧攀升。较低的 `parallelTrialCount`（例如 4）会将相同的 60 个 Trial 分散到更多轮次，使 Karpenter 有时间逐步预置资源，并降低容量峰值的风险，但可能增加经过时间。实际时间和成本取决于容量、持续时间、失败、停止和 Node 回收。

**说明：**
需要同时结合集群自动扩缩容行为调优 `parallelTrialCount` 和 `maxTrialCount`，而不能将它们视为独立设置——尤其是在 Trial 请求 GPU 等稀缺或预置缓慢的资源时。
</details>

---

[返回学习资料](../../../ai-ml/kubeflow/04-katib.md)
