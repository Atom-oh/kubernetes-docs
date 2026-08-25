# 第 4 部分：Katib — 超参数调优和 AutoML 测验

本测验检验你对 Katib 的 Experiment/Trial/Suggestion 架构、其支持的搜索算法、早停、指标收集，以及在 EKS 上运行 Katib 时资源压力考量的理解。

## 选择题

1. 在 Katib 的架构中，Experiment、Trial 和 Suggestion 之间是什么关系？
   - A) 它们是同一个 CRD 的三个可互换名称
   - B) 一个 Suggestion 拥有多个 Experiment，每个 Experiment 拥有一个 Trial
   - C) 一个 Experiment 拥有多个 Trial，每个 Trial 运行特定的超参数组合，而 Suggestion Service 提出这些组合
   - D) 一个 Trial 拥有多个 Experiment，由单个全局 Suggestion 协调

<details>
<summary>显示答案</summary>

**答案：C) 一个 Experiment 拥有多个 Trial，每个 Trial 运行特定的超参数组合，而 Suggestion Service 提出这些组合**

**说明：**
一个 Experiment CRD 描述一次调优运行，并在其生命周期内拥有最多 `maxTrialCount` 个 Trial。每个 Trial 都是一次使用特定超参数组合的独立训练运行。Suggestion Service 实现搜索算法，并基于先前结果提出每个 Trial 应尝试的组合。
</details>

2. 哪种搜索算法构建超参数如何映射到 objective metric 的概率模型，并使用该模型选择下一个最有希望尝试的点？
   - A) 网格搜索
   - B) 随机搜索
   - C) 贝叶斯优化
   - D) Hyperband

<details>
<summary>显示答案</summary>

**答案：C) 贝叶斯优化**

**说明：**
贝叶斯优化构建关联超参数与 objective 的概率模型，并使用该模型选择最有可能改善当前最佳结果的下一个候选项。随机搜索进行相互独立的采样，不会记忆过去的 Trial；网格搜索会穷举离散组合；Hyperband 会广泛分配少量预算，并将其重新分配给早期存活的候选项。
</details>

3. 与为每个配置提供完整且相同的训练预算相比，Hyperband 做出了什么权衡？
   - A) 它会在比较前将每个配置都训练至完全完成
   - B) 它为许多配置提供少量预算，尽早丢弃表现最差的配置，并将释放的预算重新分配给存活的配置
   - C) 它一次只会尝试一个配置
   - D) 它完全忽略中间性能并随机选择配置

<details>
<summary>显示答案</summary>

**答案：B) 它为许多配置提供少量预算，尽早丢弃表现最差的配置，并将释放的预算重新分配给存活的配置**

**说明：**
Hyperband 以早期剪枝换取每个配置的详尽信息：它首先以较低成本运行许多配置，积极丢弃看起来最弱的配置，并将释放的资源预算提供给仍有希望的配置。
</details>

4. 在一个 Experiment 的 spec 中，`objective` 字段定义什么？
   - A) 用于运行每个 Trial 的容器镜像
   - B) 要优化的 metric，以及是最大化还是最小化它
   - C) 可以并行运行的 Trial 数量
   - D) 搜索算法的内部超参数

<details>
<summary>显示答案</summary>

**答案：B) 要优化的 metric，以及是最大化还是最小化它**

**说明：**
`objective` 指定 metric（例如 accuracy 或 loss）和目标（最大化或最小化），还可以选择包含一个目标值，使 Experiment 在达到该值后提前停止。搜索空间在 `parameters` 下单独定义，而每个 Trial 的 job 如何运行则在 `trialTemplate` 下定义。
</details>

5. 从概念上讲，中位数停止规则的作用是什么？
   - A) 一旦中位数 Trial 完成，它就停止整个 Experiment
   - B) 它将 Trial 的中间 objective 值与其同伴在训练相同阶段的中位数进行比较，如果明显落后则提前停止该 Trial
   - C) 它只允许恰好一半的所有提议 Trial 运行
   - D) 它选择中位数超参数值作为最终答案

<details>
<summary>显示答案</summary>

**答案：B) 它将 Trial 的中间 objective 值与其同伴在训练相同阶段的中位数进行比较，如果明显落后则提前停止该 Trial**

**说明：**
中位数停止是一种早停形式：它不会让明显表现不佳的 Trial 运行至完成，而是将其间隔值与其他 Trial 在训练相同阶段的中位数进行比较；如果它明显落后，就会提前终止，从而节省原本会消耗在不太可能具备竞争力的结果上的计算资源。
</details>

6. Katib 通常如何从正在运行的 Trial 的训练容器中获取 objective metric 值？
   - A) 训练容器必须从其代码内部直接调用 Katib API
   - B) metrics-collector sidecar 跟踪日志/stdout 或抓取 metrics endpoint，并将解析后的值报告给 Katib
   - C) Katib 暂停容器并直接检查其内存
   - D) Kubernetes scheduler 会自动从资源使用情况中提取 metric

<details>
<summary>显示答案</summary>

**答案：B) metrics-collector sidecar 跟踪日志/stdout 或抓取 metrics endpoint，并将解析后的值报告给 Katib**

**说明：**
metrics-collector sidecar 会与训练容器一同注入 Trial pod。它观察训练容器的输出——通常会解析 stdout/日志文件或抓取暴露的 metrics endpoint——并将 objective metric 报告给 Katib，使训练代码本身基本无需感知 Katib。
</details>

7. 为什么较高的 `parallelTrialCount` 会比以低并发运行相同 `maxTrialCount` 时在 EKS 集群上产生更严重的资源压力？
   - A) `parallelTrialCount` 不会影响创建多少 pod
   - B) 高并行度意味着许多 Trial（及其资源请求，例如 GPU）会同时到达集群，而不是分散到不同时间，从而产生短暂而急剧的需求峰值
   - C) EKS 默认将 `parallelTrialCount` 限制为 1
   - D) 并行 Trial 总是在同一个节点上运行，因此没有额外需求

<details>
<summary>显示答案</summary>

**答案：B) 高并行度意味着许多 Trial（及其资源请求，例如 GPU）会同时到达集群，而不是分散到不同时间，从而产生短暂而急剧的需求峰值**

**说明：**
每个并发 Trial 都是一个完整的训练 job。`parallelTrialCount` 为 8 表示同时发出 8 个并发资源请求（例如 GPU 请求），而不是将其分散到一段时间内——即使一个 Experiment 的总 `maxTrialCount` 看似不高，也可能使需求急剧上升。
</details>

8. 在 EKS 上，如果高 `parallelTrialCount` 的 Experiment 启动后，新创建的 Trial pod 在一段时间内处于 pending 状态，可能的解释是什么？
   - A) Suggestion Service 已崩溃
   - B) Karpenter 正在响应 pending pod 的突发请求而预置新的 GPU 支持节点，而 GPU instance type 通常需要更长的预置时间
   - C) Katib 总是在固定的预热期内暂停新的 Trial
   - D) metrics-collector sidecar 正在阻止 pod 启动

<details>
<summary>显示答案</summary>

**答案：B) Karpenter 正在响应 pending pod 的突发请求而预置新的 GPU 支持节点，而 GPU instance type 通常需要更长的预置时间**

**说明：**
高 `parallelTrialCount` 产生的 pending Trial pod 突发请求通常会触发 Karpenter 预置新节点。GPU instance type 的预置时间可能比通用型实例更长，因此 Trial 可能会等待节点容量——在假设搜索算法本身很慢之前，值得先通过 Trial pod event 进行检查。
</details>

## 简答题

9. 请列出 Katib 支持的两种搜索算法，并各用一句话说明它们最适合解决什么问题。

<details>
<summary>显示答案</summary>

**答案：** 以下任意两种：随机搜索（适用于大型或了解不充分的搜索空间的低成本基线）、网格搜索（小型、低维离散空间的穷尽覆盖）、贝叶斯优化（通过 objective 的概率模型，在每个 Trial 成本较高时减少所需 Trial 总数）、Hyperband（利用低成本但信息丰富的早期信号，尽早剪枝表现不佳的配置），或 CMA-ES/基于种群的方法（适用于通过演化候选种群进行探索的连续或高维空间）。

**说明：**
每种算法对探索成本和搜索效率的权衡方式都不同，正确选择取决于单个 Trial 的成本以及搜索空间具有多少结构。
</details>

10. 鉴于 Hyperband 和早停（例如中位数停止规则）都旨在避免浪费计算资源，两者之间有什么区别？

<details>
<summary>显示答案</summary>

**答案：** Hyperband 是一种搜索策略，它预先决定为每个配置提供多少资源预算；早停则是在 Trial 已经运行期间，根据其相对于同伴在该训练阶段的表现所进行的运行时检查。

**说明：**
两者在不同层级上运作：Hyperband 的剪枝是搜索算法整体预算分配策略的一部分，而早停是在某个 Trial 运行期间作出的逐 Trial 决策，独立于提出该 Trial 的搜索算法。
</details>

## 实操 / 应用题

11. 你正在配置一个 Experiment，其中每个 Trial 请求一个 GPU，并且集群具有一个用于 GPU instance 的 Karpenter NodePool，预置新容量通常需要数分钟。你设置 `maxTrialCount: 60`，并正在决定 `parallelTrialCount`。请用几句话说明，在此环境中将其设置为较高值（例如 20）与较低值（例如 4）之间的权衡。

<details>
<summary>显示答案</summary>

**答案：** 较高的 `parallelTrialCount`（例如 20）可在更少的顺序轮次中完成全部 60 个 Trial，但会产生 20 个同时发生的 GPU 请求的急剧突发，这可能超过 Karpenter 预置 GPU 节点的速度——导致早期 Trial 处于 pending 状态而非训练状态；如果其他 workload 正在争用相同的 GPU NodePool，也可能使共享集群容量急剧上升。较低的 `parallelTrialCount`（例如 4）会将同样的 60 个 Trial 分散到更多轮次中，让 Karpenter 有时间逐步预置，并降低容量峰值的风险，但代价是 Experiment 达到 `maxTrialCount` 所需的总体时间更长。

**说明：**
在调优 `parallelTrialCount` 和 `maxTrialCount` 时，需要结合集群 autoscaling 行为一起考虑，不能将二者视为独立设置——尤其是在 Trial 请求 GPU 等稀缺或预置较慢的资源时。
</details>

---

[返回学习资料](../../../ai-ml/kubeflow/04-katib.md)
