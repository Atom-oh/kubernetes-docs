# 第 4 部分：Katib（超参数调优和 AutoML）测验

本测验考查你对 Katib 的 Experiment/Trial/Suggestion 架构、支持的搜索算法、提前停止、指标收集，以及在 EKS 上运行 Katib 时资源压力相关注意事项的理解。

## 选择题

1. 在 Katib 架构中，Experiment、Trial 和 Suggestion 之间是什么关系？
   - A) 它们是同一个 CRD 的三个可互换名称
   - B) 一个 Suggestion 拥有多个 Experiment，每个 Experiment 拥有一个 Trial
   - C) 一个 Experiment 拥有多个 Trial，每个 Trial 运行一种特定的超参数组合，而 Suggestion 服务负责提出这些组合
   - D) 一个 Trial 拥有多个 Experiment，并由一个全局 Suggestion 协调

<details>
<summary>显示答案</summary>

**答案：C) 一个 Experiment 拥有多个 Trial，每个 Trial 运行一种特定的超参数组合，而 Suggestion 服务负责提出这些组合**

**解释：**
Experiment 对象用于描述调优过程；maxTrialCount 是完成数量的判定标准，不是成功训练的数量，也不是不可更改的支出上限。每个 Trial 都是一次使用特定超参数组合的训练运行。Suggestion 服务实现某种算法；它如何使用先前的观察结果取决于该算法。
</details>

2. 哪种搜索算法会构建一个概率模型，用于描述超参数与目标指标之间的关系，并利用该模型选择接下来最有希望尝试的点？
   - A) 网格搜索
   - B) 随机搜索
   - C) 贝叶斯优化
   - D) Hyperband

<details>
<summary>显示答案</summary>

**答案：C) 贝叶斯优化**

**解释：**
贝叶斯优化会构建一个描述超参数与目标之间关系的概率模型，并利用该模型选择最有可能优于当前最佳结果的下一个候选项。随机搜索会独立采样，不记忆过去的 Trial；网格搜索会穷举离散组合；Hyperband 则会先向大量配置分配少量预算，再将预算重新分配给较早胜出的配置。
</details>

3. 与为每个配置提供完整且相同的训练预算相比，Hyperband 做出了什么权衡？
   - A) 先将每个配置都训练至完全结束，再进行比较
   - B) 为许多配置分配少量预算，提前淘汰表现最差者，并将释放出的预算重新分配给剩余配置
   - C) 始终一次只尝试一个配置
   - D) 完全忽略中间表现，并随机选择配置

<details>
<summary>显示答案</summary>

**答案：B) 为许多配置分配少量预算，提前淘汰表现最差者，并将释放出的预算重新分配给剩余配置**

**解释：**
Hyperband 以牺牲每个配置的穷尽性信息为代价，进行提前剪枝：首先以较低成本运行许多配置，积极淘汰看起来表现最差的配置，并将释放出的资源预算分配给仍有希望的配置。
</details>

4. 在 Experiment 的 spec 中，`objective` 字段定义了什么？
   - A) 用于运行每个 Trial 的容器镜像
   - B) 要优化的指标，以及是要最大化还是最小化该指标
   - C) 可并行运行的 Trial 数量
   - D) 搜索算法的内部超参数

<details>
<summary>显示答案</summary>

**答案：B) 要优化的指标，以及是要最大化还是最小化该指标**

**解释：**
`objective` 指定指标（例如准确率或损失）和优化目标（最大化或最小化），还可以选择性地包含一个目标值；达到该值后，Experiment 可以提前停止。搜索空间在 `parameters` 下单独定义，每个 Trial 的作业运行方式则在 `trialTemplate` 下定义。
</details>

5. 本次审查验证了关于 Katib 0.19.0 medianstop 阈值计算的哪项内容？
   - A) 中位数 Trial 完成后，整个 Experiment 就会停止
   - B) 它会存储前 start_step 次观察中成功 Trial 的平均值，然后计算这些平均值的算术平均数
   - C) 它只允许所有已提出的 Trial 中恰好一半运行
   - D) 它会选择中位数超参数值作为最终答案

<details>
<summary>显示答案</summary>

**答案：B) 它会存储前 start_step 次观察中成功 Trial 的平均值，然后计算这些平均值的算术平均数**

**解释：**
官方指南描述的是中位数规则，但 0.19.0 实际计算的是算术平均数。成功 Trial 的平均值 [1, 2, 100] 在未修改的函数中会得出约 34.333，而不是统计学上的中位数 2。默认值为 min_trials_required=3 和 start_step=4；此外还需满足 collector 和时间戳要求。
</details>

6. Katib 通常如何从正在运行的 Trial 训练容器中获取目标指标值？
   - A) 训练容器必须在其代码中直接调用 Katib API
   - B) 已配置的 pull collector 会收集指标，或由 Push 模式下的 report_metrics() 将指标发送到 DB manager
   - C) Katib 会暂停容器并直接检查其内存
   - D) Kubernetes 调度程序会自动从资源使用情况中提取指标

<details>
<summary>显示答案</summary>

**答案：B) 已配置的 pull collector 会收集指标，或由 Push 模式下的 report_metrics() 将指标发送到 DB manager**

**解释：**
StdOut/File/TensorFlowEvent 和 Custom collector 可与 Push 模式并存。任意 HTTP 抓取并非内置默认功能。注入 pull collector 需要为命名空间添加标签，并配置 webhook 和目标 Pod/容器。作业成功并不能证明指标已被收集。
</details>

7. 为什么在 EKS 集群上，与以低并发运行相同 `maxTrialCount` 的情况相比，较高的 `parallelTrialCount` 会造成更显著的资源压力？
   - A) `parallelTrialCount` 不会影响创建的 Pod 数量
   - B) 高并行度意味着许多 Trial（及其资源请求，例如 GPU）会同时而不是分批到达集群，从而造成短时的需求激增
   - C) EKS 默认将 `parallelTrialCount` 限制为 1
   - D) 并行 Trial 总是在同一节点上运行，因此不会增加额外需求

<details>
<summary>显示答案</summary>

**答案：B) 高并行度意味着许多 Trial（及其资源请求，例如 GPU）会同时而不是分批到达集群，从而造成短时的需求激增**

**解释：**
每个并发 Trial 都是一个完整的训练作业。需求量取决于并发数 × 每个 Trial 的 Pod 数量 × 每个 Pod 的资源量，再加上 collector 和服务的开销。因此，即便某个 Experiment 的总 `maxTrialCount` 看起来不高，也可能造成需求急剧上升。
</details>

8. 在高 `parallelTrialCount` 的 Experiment 启动后，如果新创建的 Trial Pod 一段时间内一直处于 pending 状态，在 EKS 上可能是什么原因？
   - A) Suggestion 服务已崩溃
   - B) 它可能正在等待可用容量；请通过 Pod 事件、NodePool 状态、配额、EC2 容量和引导状态进行确认
   - C) Katib 总会暂停新 Trial，等待一段固定的预热时间
   - D) metrics-collector sidecar 阻止了 Pod 启动

<details>
<summary>显示答案</summary>

**答案：B) 它可能正在等待可用容量；请通过 Pod 事件、NodePool 状态、配额、EC2 容量和引导状态进行确认**

**解释：**
仅凭 pending 状态不能证明 Karpenter 正在成功配置资源。亲和性、污点、卷、配额、容量限制和引导失败也可能是原因。请依据实际观察到的事件和控制器状态进行排查。
</details>

## 简答题

9. 列出 Katib 支持的两种搜索算法，并各用一句话描述每种算法最适合解决的问题。

<details>
<summary>显示答案</summary>

**答案：** 以下任意两种：随机搜索（适用于大型或尚未充分了解的搜索空间的低成本基准方法）、网格搜索（适用于小型且维度较低的离散搜索空间的穷举覆盖）、贝叶斯优化（通过对目标建立概率模型，在每个 Trial 成本较高时减少所需的 Trial 总数）、Hyperband（利用低成本且信息丰富的早期信号，提前剪枝表现不佳的配置）、CMA-ES（协方差矩阵自适应进化策略），或 PBT（需要共享检查点的独立群体式训练策略）。

**解释：**
每种算法在探索成本与搜索效率之间的权衡各不相同；正确选择取决于单个 Trial 的成本，以及搜索空间具有多少结构。
</details>

10. Hyperband 和提前停止（例如 median-stopping 规则）都旨在避免浪费计算资源，它们的做法有何不同？

<details>
<summary>显示答案</summary>

**答案：** Hyperband 是一种搜索策略，会预先决定为每个配置分配多少资源预算；提前停止则是在 Trial 已经运行期间，根据它在训练该阶段相对于同伴的表现进行运行时检查。

**解释：**
二者作用于不同层面：Hyperband 的剪枝属于搜索算法整体预算分配策略的一部分，而提前停止是在 Trial 运行期间针对单个 Trial 做出的决策；这需要兼容的 collector/日志配置，并不意味着所有组合都自动受支持。
</details>

## 实操 / 应用题

11. 你正在配置一个 Experiment，其中每个 Trial 需要一个 GPU；集群有一个用于 GPU 实例的 Karpenter NodePool，通常需要几分钟才能配置出新的容量。你设置了 `maxTrialCount: 60`，现在需要决定 `parallelTrialCount`。请用几句话说明，在此环境中将其设得较高（例如 20）与设得较低（例如 4）之间的权衡。

<details>
<summary>显示答案</summary>

**答案：** 较高的 `parallelTrialCount`（例如 20）在有可用容量时可以用更少轮次处理完 Trial，但会产生 20 个同时到来的 GPU 请求，可能超过 Karpenter 配置 GPU 节点的速度，导致早期 Trial 处于 pending 状态而无法开始训练；如果其他工作负载也在争用同一个 GPU NodePool，还可能使共享集群容量骤增。较低的 `parallelTrialCount`（例如 4）会将相同的 60 个 Trial 分散到更多轮次中，为 Karpenter 逐步配置资源留出时间，从而降低容量激增的风险，但可能延长总耗时。实际耗时和成本取决于容量、运行时长、故障、停止情况和节点回收情况。

**解释：**
设置 `parallelTrialCount` 和 `maxTrialCount` 时，需要同时考虑集群自动扩缩容的行为，而不能将二者视为互不相关的设置；当 Trial 请求 GPU 等稀缺或配置速度较慢的资源时尤其如此。
</details>

---

[返回学习材料](../../../ai-ml/kubeflow/04-katib.md)
