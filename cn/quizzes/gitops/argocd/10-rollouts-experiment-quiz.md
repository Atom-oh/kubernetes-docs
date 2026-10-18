# Argo Rollouts Experiment 测验

本测验检查你对 Argo Rollouts Experiment CRD 的理解，包括资源层次结构、流量隔离、分析判定结果和结果传播。

1. Experiment CRD 的核心用途是什么？
   - A) 将所有生产流量切换到新版本
   - B) 使用临时 ReplicaSet 和分析来验证新版本
   - C) 存储 Rollout 的修订历史
   - D) 对集群节点执行负载测试

<details>
<summary>显示答案</summary>

**答案：**B) 使用临时 ReplicaSet 和分析来验证新版本

**说明：**Experiment 会启动临时 ReplicaSet，并在结束时将它们缩容至 0。Service 选择器和路由器必须实现预期的隔离。仅创建独立 ReplicaSet 并不能保证真实用户不会受到影响。

</details>

2. Rollout 的 canary 策略中的 Experiment 步骤结束为 Failed 或 Error 时会发生什么？
   - A) 跳过此步骤，Rollout 继续下一步
   - B) 自动重试失败的 Experiment
   - C) 中止 Rollout，并保持稳定版本不变
   - D) Rollout 等待在暂停状态

<details>
<summary>显示答案</summary>

**答案：**C) 中止 Rollout，并保持稳定版本不变

**说明：**Experiment 步骤会阻塞后续流程。只有 Experiment 以 Successful 阶段结束，Rollout 才会继续；Failed/Error 会中止 Rollout，使其进入 Degraded 状态。Inconclusive 则会设置 InconclusiveExperiment 暂停状态，等待调查和操作员决策。中止不会撤销数据库变更或外部副作用。

</details>

3. `demo-app` Rollout 的 revision 2 更新在第一步（index 0）创建 Experiment 时，如果名称没有冲突，正确的基础名称格式是什么？（新版本 PodTemplateHash 为 `74d8d8b4fb`。）
   - A) `demo-app-experiment-1`
   - B) `demo-app-74d8d8b4fb-2-0`
   - C) `experiment-demo-app-0-2`
   - D) `demo-app-2-0-74d8d8b4fb`

<details>
<summary>显示答案</summary>

**答案：**B) `demo-app-74d8d8b4fb-2-0`

**说明：**Experiment 名称格式为 `<rollout-name>-<new-version PodTemplateHash>-<revision>-<step-index>`。它创建的 ReplicaSet 名称为 `<experiment-name>-<template-name>`（例如 `demo-app-74d8d8b4fb-2-0-baseline`），AnalysisRun 名称为 `<experiment-name>-<analysis-name>`。

</details>

4. 示例 Service 选择 traffic-class=production，而 Experiment Pod 使用 traffic-class=experiment 标签时，为什么这些 Pod 会被该 Service 排除？
   - A) Experiment Pod 创建在单独的命名空间
   - B) NetworkPolicy 阻止了 Experiment Pod
   - C) Service 选择器中的 traffic-class 与 Experiment Pod 标签不同
   - D) Experiment Pod 配置了总是失败的 readinessProbe

<details>
<summary>显示答案</summary>

**答案：**C) Service 选择器中的 traffic-class 与 Experiment Pod 标签不同

**说明：**示例通过标签/选择器明确区分了各自的选择集合。另一个仅选择 app 标签的 Service 仍可能选中 Experiment Pod。若要有意向其发送流量，可在模板上设置 `service` 属性以创建 Experiment 专用 Service，或在配置了 trafficRouting 的 Rollout 上使用 `weight`。

</details>

5. 通过模板的 `weight` 字段将真实流量发送到 Experiment Pod，需要满足什么前提？
   - A) Rollout 必须配置支持加权 Experiment 的 trafficRouting
   - B) 模板的 replicas 必须与稳定版本的 replicas 相等
   - C) AnalysisTemplate 必须使用 web provider
   - D) 必须独立创建 Experiment，不能由 Rollout 创建

<details>
<summary>显示答案</summary>

**答案：**A) Rollout 必须配置支持加权 Experiment 的 trafficRouting

**说明：**weight 属于 Rollout 实验步骤模板。必须使用 ALB/Istio 等受支持的路由器；普通 canary 加权并不意味着支持 Experiment 流量拆分。未配置 trafficRouting 时，可通过 `service` 属性创建 Experiment 专用 Service，并自行配置路由。

</details>

6. AnalysisTemplate 指标设置 `failureLimit: 1` 时，整个 AnalysisRun 何时变为 Failed？
   - A) 一次测量失败后立即
   - B) 两次测量失败后（failed > failureLimit）
   - C) 仅在连续失败一次后
   - D) 只有 count 指定的所有测量都完成后

<details>
<summary>显示答案</summary>

**答案：**B) 两次测量失败后（failed > failureLimit）

**说明：**`failureLimit` 表示允许的失败次数；失败数超过该值时，AnalysisRun 就会被判定为 Failed。1.10.0 的实现会比较 `failed > failureLimit`。同理，超过 `inconclusiveLimit` 会得到 Inconclusive，超过 `consecutiveErrorLimit`（连续采集错误，默认值为 4）会得到 Error。

</details>

7. Experiment 的 `duration` 计时器何时开始？
   - A) 创建 Experiment 资源时立即开始
   - B) 第一次 AnalysisRun 测量成功时
   - C) spec.templates 中所有 ReplicaSet 都变为健康（可用）时
   - D) Rollout 即将进入 Experiment 步骤时

<details>
<summary>显示答案</summary>

**答案：**C) spec.templates 中所有 ReplicaSet 都变为健康（可用）时

**说明：**Experiment 控制器会先为每个模板创建 ReplicaSet，并等待所有 Pod 都可用。随后才启动 duration 计时器并创建 AnalysisRun，因此 Pod 启动缓慢不会占用实验时长。

</details>

8. Experiment 完成后（无论成功还是失败），其中的 ReplicaSet 会怎样？
   - A) 保留供下一次 Experiment 使用
   - B) 缩容至 0，并清理通过 `service` 属性创建的任何 Service
   - C) 提升为稳定 ReplicaSet
   - D) 保留直至手动删除

<details>
<summary>显示答案</summary>

**答案：**B) 缩容至 0，并清理通过 `service` 属性创建的任何 Service

**说明：**Experiment 是临时资源。完成后，默认会先等待 30 秒缩容延迟，再将副本数降为零。生成的 Service 会在可用副本数变为零后删除。根据保留策略，ReplicaSet/AnalysisRun 对象可能仍会保留。成功时 Rollout 会继续；Failed/Error 会中止；Inconclusive 会暂停。

</details>
