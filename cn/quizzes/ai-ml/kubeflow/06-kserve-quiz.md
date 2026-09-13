# KServe 测验

基线：KServe 0.18.0 / Community Distribution 26.03.1。

## 单项选择题

1. KServe 与 Kubeflow 有何关系？

   - A) 它从 KFServing 演变而来，并且可连同其依赖项独立运行
   - B) 它是 Katib 的新名称
   - C) 它始终需要完整的 Kubeflow 发行版
   - D) 它取代 Kubernetes

<details>
<summary>显示答案</summary>

**答案：A) 它从 KFServing 演变而来，并且可连同其依赖项独立运行**

完整的 Kubeflow 和 Models Web Application 并非每次安装 KServe 的前提条件。
</details>

2. 本章审查了哪些版本？

   - A) 仅审查 0.16.1 的 web app
   - B) Community 26.03.1 中的 KServe 和 web app 0.18.0；审查的最新 KServe 为 0.20.0
   - C) 所有组件都必须使用不同的版本
   - D) web-app 标签决定所有已安装的 CRD

<details>
<summary>显示答案</summary>

**答案：B) Community 26.03.1 中的 KServe 和 web app 0.18.0；审查的最新 KServe 为 0.20.0**

Controller、CRD 和 web app 是独立的构件。必须记录它们实际的兼容性和修订版本。
</details>

3. 哪个 InferenceService 组件是必需的？

   - A) Explainer
   - B) Transformer
   - C) Predictor
   - D) 三者全部

<details>
<summary>显示答案</summary>

**答案：C) Predictor**

Transformer 和 Explainer 是可选的；runtime/protocol 兼容性以及实际的 explanation route 仍然很重要。
</details>

4. 选择 Knative 是否会自动将每个空闲的 predictor 缩容至零？

   - A) 是，无需任何配置
   - B) 否；KServe 默认将 minReplicas 设为 1，缩容至零需要受支持的 autoscaler/policy 设置，例如 minReplicas 0
   - C) 是，并且 EC2 计费会立即停止
   - D) 不需要安装 Knative

<details>
<summary>显示答案</summary>

**答案：B) 否；KServe 默认将 minReplicas 设为 1，缩容至零需要受支持的 autoscaler/policy 设置，例如 minReplicas 0**

从零扩容包括容量、镜像和模型加载。Pod 数量为零并不保证节点终止。
</details>

5. 关于 Standard 模式，哪项说法正确？

   - A) 它始终保证存在一个预热且健康的 replica
   - B) 它使用 Deployment/Service；默认 HPA 至少保留 1 个，而经过配置的 KEDA 路径可以支持零个
   - C) 它始终需要 Knative
   - D) 它不支持任何 autoscaling 选项

<details>
<summary>显示答案</summary>

**答案：B) 它使用 Deployment/Service；默认 HPA 至少保留 1 个，而经过配置的 KEDA 路径可以支持零个**

KEDA 需要安装、有效的 metrics/triggers 以及 activation path。在任一模式中，重启/rollout/scale-out 的启动延迟仍然存在。
</details>

6. 0.18.0 中的现代模式名称是什么？

   - A) Serverless 和 RawDeployment 是仅有的有效名称
   - B) Knative 和 Standard；旧名称是已弃用的别名
   - C) HPA 和 GPU
   - D) Predictor 和 Transformer

<details>
<summary>显示答案</summary>

**答案：B) Knative 和 Standard；旧名称是已弃用的别名**

检查实际的 annotation 和 config。代码回退值为 Standard；审查的 OCI resource chart 默认使用 Knative。
</details>

7. 什么实现了经过验证的 canaryTrafficPercent 路径？

   - A) KServe Controller 自行代理所有请求
   - B) KServe 设置 Knative revision traffic targets；Knative networking 路由请求
   - C) 每个 Standard Deployment 都自动具有相同的 revision splitting
   - D) Argo Rollouts 是必需的

<details>
<summary>显示答案</summary>

**答案：B) KServe 设置 Knative revision traffic targets；Knative networking 路由请求**

Standard rolling update 并非相同的 revision-percentage 机制。Promotion/rollback 和保留的构件需要单独验证。
</details>

8. 请求 nvidia.com/gpu 是否能保证 GPU inference？

   - A) 是，适用于每个模型
   - B) 否；drivers、image/backend 以及 model/device 配置也必须匹配
   - C) 它会自动安装所有必需的 drivers
   - D) 它消除了对节点容量的需求

<details>
<summary>显示答案</summary>

**答案：B) 否；drivers、image/backend 以及 model/device 配置也必须匹配**

资源分配与实际模型执行是不同的。Karpenter 根据 policies、quotas 和可用性提供符合条件的容量。
</details>

## 简答题

9. 为什么始终预热与缩容至零并不是两种模式之间的绝对区别？

<details>
<summary>显示答案</summary>

Knative 可以通过 minimum settings 保留预热的 replica，而 Standard 可以结合合适的 external signal 使用 KEDA。两种模式均不保证可用性或延迟；应测试 readiness、加载、容量和恢复。
</details>

10. 为什么仅有 artifact URI 还不够，以及应如何看待 TorchServe？

<details>
<summary>显示答案</summary>

runtime、模型格式/layout、library version、credentials、ports 和 protocol 必须匹配。TorchServe 表示它不再处于积极维护状态，并且没有计划提供 security fixes，因此旧的 runtime catalog 条目不能证明其是受到维护的默认选项。
</details>

11. Pod autoscaling 和 EC2 scaling 如何相互作用？

<details>
<summary>显示答案</summary>

Knative/HPA/KEDA 或其他配置的 scaler 决定期望的 Pod 数量。Kubernetes scheduling 和 Karpenter capacity policies 会影响节点的供应/回收。在模型 Pod 数量归零后，其他 workloads 或 disruption rules 仍可能使 EC2 节点继续产生费用。
</details>

---

[返回学习材料](../../../ai-ml/kubeflow/06-kserve.md)
