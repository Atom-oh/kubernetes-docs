# EKS Spot 生产实验测验

> **相关指南**：[EKS Spot 生产实验与结果评估](../../ops/17-spot-production-experiments.md)

## 1. 在带有 PDB 的 Spot 节点上进行 drain 测试并通过。这能证明什么？

- A) 实际回收 Spot 实例始终能保持相同的可用性
- B) 自愿驱逐路径有效；实际回收需要单独测试
- C) EC2 会等待 PDB 同意后才终止实例
- D) 应用始终有两分钟退出时间

<details>
<summary>显示答案</summary>

**答案：B) 自愿驱逐路径有效；实际回收需要单独测试**

**说明：**PDB 无法阻止 EC2 实例丢失。应通过实际回收测试通知送达、驱逐延迟、强制终止，以及有通知和无通知情况下的服务影响。

</details>

## 2. 一个 Pending Pod 带有仅允许 Spot 的 selector。添加 On-Demand 节点后会发生什么？

- A) 无论 selector 如何，Pod 都会立即迁移
- B) PDB 会将 selector 改为 On-Demand
- C) 该 Pod 仍不符合 On-Demand 节点的调度条件
- D) NodePool 权重会覆盖 selector

<details>
<summary>显示答案</summary>

**答案：C) 该 Pod 仍不符合 On-Demand 节点的调度条件**

**说明：**回退要求既有可用容量，也有兼容的 Pod 约束。仅仅扩大 NodePool 的容量类型，并不会移除 Pod 对 Spot 的限制。

</details>

## 3. 将 NodePool 改为仅使用 On-Demand 后，服务成功启动。这次演练验证了什么？

- A) EC2 返回 Spot 容量不足后会自动回退
- B) 基于配置的转换、调度和 On-Demand 启动
- C) 每个 AZ 都能保证提供 Spot 容量
- D) 所有现有 Spot Pod 都会立即迁移

<details>
<summary>显示答案</summary>

**答案：B) 基于配置的转换、调度和 On-Demand 启动**

**说明：**这次演练没有注入容量错误。应单独验证实际置备路径的错误处理和回退行为；如果无法重现，就将其保留为未验证状态。

</details>

## 4. FIS 报告状态为 `completed`，替代节点也已 Ready。什么可以证明服务级别的测试通过？

- A) 仅凭 FIS 状态
- B) 仅凭节点 Ready
- C) 客户端错误、延迟、吞吐量和正确性都符合标准
- D) 没有负载均衡器 5xx 响应，即使存在客户端超时也不考虑

<details>
<summary>显示答案</summary>

**答案：C) 客户端错误、延迟、吞吐量和正确性都符合标准**

**说明：**FIS 完成状态表示注入已完成。服务恢复还需要 Pod 就绪、负载均衡器目标健康、实际请求成功以及工作结果正确。

</details>

## 5. 哪种比较方式能正确评估 Spot 节省？

- A) 将 Spot 折扣报告为服务成本节省
- B) 在条件等同的情况下，比较通过正确性检查的每个唯一成功操作的有效成本
- C) 排除重试和 On-Demand 替代成本
- D) 将替代实例重叠期同时计入 EC2 账单和额外成本项目

<details>
<summary>显示答案</summary>

**答案：B) 在条件等同的情况下，比较通过正确性检查的每个唯一成功操作的有效成本**

**说明：**应计入开销、承诺折扣、替代实例和重试，但不能重复计算费用。短期运行结果推算出的月度成本应标记为估算值。

</details>

## 6. 没有实验数据时，应如何记录结果？

- A) 将预期恢复时间填为测量值
- B) 记录零错误并标记为通过
- C) 记录为 NOT RUN 和缺少测量数据；暂停扩大生产使用
- D) 将官方文档视为已完成的实验

<details>
<summary>显示答案</summary>

**答案：C) 记录为 NOT RUN 和缺少测量数据；暂停扩大生产使用**

**说明：**文档描述的行为、假设和测量值属于不同类型的证据。缺少运行 ID 和原始结果，无法证明已具备生产就绪条件。

</details>

## 7. E2 混合路径总体错误率为 0.0556%，最差的完整 60 秒窗口错误率为 0.8333%。如果 60 秒窗口标准是 0.1%，会得出什么结论？

- A) 通过，因为总体错误率较低
- B) 忽略故障，因为 p99 较低
- C) 未通过窗口标准；应处理配置问题并重复测试
- D) 任何生产服务都不能使用 Spot

<details>
<summary>显示答案</summary>

**答案：C) 未通过窗口标准；应处理配置问题并重复测试**

**说明：**较长的健康时段可能拉低总体错误率。应使评估窗口符合实际业务 SLO，且不要将一次合成测试的结果推广到所有配置。

</details>

## 8. 某 Pod 从创建时起就是 Guaranteed。其目标普通容器的 CPU request 和 limit 都从 200m 降至 50m。Memory request=limit 仍为 64Mi，所有其他容器也保持 Guaranteed 资源设置。会发生什么？

- A) 降低 CPU 一定会使 Pod 变为 Burstable
- B) Pod 会保留原有的 Guaranteed 类别，缩容后 CPU 和内存的 request 与 limit 仍分别相等
- C) 同样的 resize 也能将创建时为 Burstable 的 Pod 变为 Guaranteed
- D) 即使 memory request 和 limit 不相等，CPU 值相等也能保持 Guaranteed

<details>
<summary>显示答案</summary>

**答案：B) Pod 会保留原有的 Guaranteed 类别，缩容后 CPU 和内存的 request 与 limit 仍分别相等**

**说明：**QoS 类别在创建时确定，不能通过 resize 更改。此容器级设计会保持每个适用容器的 CPU 和内存 request 分别等于相应的正数 limit，并同时降低目标 CPU request 和 limit。保持 Guaranteed 并不能证明缩容后符合应用 SLO，也不能防止 Spot 回收。

</details>

## 9. 在 E10 中，哪些证据能够证明初始化已完成、CPU 缩容已应用，以及缩容后服务质量符合要求？

- A) Pod 处于 Running 状态即可满足全部三项条件
- B) `pods/resize` PATCH 成功即可证明初始化完成、缩容完成并符合 SLO
- C) 验证实际的 startupProbe 和 `started=true`、期望资源与上报资源、各代次及 resize 状态，并检查缩容后的应用 SLO
- D) containerID 未变化且类别为 Guaranteed，因此无需检查请求错误和延迟

<details>
<summary>显示答案</summary>

**答案：C) 验证实际的 startupProbe 和 `started=true`、期望资源与上报资源、各代次及 resize 状态，并检查缩容后的应用 SLO**

**说明：**仅凭 Running 状态或 started 值无法证明初始化已完成；每个目标都需要通过 startupProbe 检查实际初始化情况。PATCH 成功只表示请求已被接受，因此还要检查 kubelet 上报的资源、已观测到的代次、`PodResizePending` 和 `PodResizeInProgress`。缩容实际应用后，应通过就绪状态/负载均衡器状态和应用 SLO 证据另行评估质量，包括错误、p99、吞吐量和 throttling。

</details>

## 10. 2026-09-12 的 Spot 测量结果和已发布的初始模板能证明什么关于分阶段 CPU resize 的结论？

- A) E2 的总体 p99 较低，证明增加启动 CPU 有益
- B) 初始模板和测量结果都缺少分阶段配置和必要证据，因此 E10 仍为 NOT RUN
- C) 仅凭初始模板就能证明准入后的 Pod 资源和 QoS
- D) 路线图中的历史报告和本地原型检查也足以完成 Spot 综合实验

<details>
<summary>显示答案</summary>

**答案：B) 初始模板和测量结果都缺少分阶段配置和必要证据，因此 E10 仍为 NOT RUN**

**说明：**三个初始 Deployment 都请求 50m/64Mi，限制为 500m/256Mi；这些设置本身不符合 Guaranteed 要求。它们缺少分阶段 resize opt-in、`resizePolicy` 和 `startupProbe`，也没有实际资源、QoS 或预热性能对比的前后证据。初始模板不能代表准入后的 Pod 实际观测结果。应将路线图历史报告、本地原型检查和 Spot 测量结果分别记录，并单独运行 E10。

</details>
