# KServe 测验

基线：KServe 0.18.0 / 社区发行版 26.03.1。

## 多项选择题

1. KServe 与 Kubeflow 有何关系？

   - A) 它由 KFServing 演变而来，并且可以连同其依赖项独立运行
   - B) 它是 Katib 的新名称
   - C) 它始终需要完整的 Kubeflow 发行版
   - D) 它取代 Kubernetes

<details>
<summary>显示答案</summary>

**答案：A) 它由 KFServing 演变而来，并且可以连同其依赖项独立运行**

完整的 Kubeflow 和 Models Web Application 并非每个 KServe 安装的先决条件。
</details>

2. 本章审查了哪些版本？

   - A) 仅审查了版本为 0.16.1 的 Web 应用程序
   - B) 社区发行版 26.03.1 中的 KServe 和 Web 应用程序 0.18.0；截至 2026-10-12 检查的最新 KServe 版本为 0.21.0
   - C) 所有组件都必须具有不同版本
   - D) Web 应用程序标签决定所有已安装的 CRD

<details>
<summary>显示答案</summary>

**答案：B) 社区发行版 26.03.1 中的 KServe 和 Web 应用程序 0.18.0；截至 2026-10-12 检查的最新 KServe 版本为 0.21.0**

Controller、CRD 和 Web 应用程序是独立的工件。必须记录它们实际的兼容性和修订版本。
</details>

3. 哪个 InferenceService 组件是必需的？

   - A) Explainer
   - B) Transformer
   - C) Predictor
   - D) 三者皆是

<details>
<summary>显示答案</summary>

**答案：C) Predictor**

Transformer 和 explainer 是可选的；运行时/协议兼容性以及实际的解释路由仍然很重要。
</details>

4. 选择 Knative 是否会自动将每个空闲 predictor 扩缩容至零？

   - A) 是，无需任何配置
   - B) 否；KServe 默认将 minReplicas 设为 1，而扩缩容至零需要受支持的 autoscaler/policy 设置，例如 minReplicas 0
   - C) 是，并且 EC2 计费会立即停止
   - D) 不需要安装 Knative

<details>
<summary>显示答案</summary>

**答案：B) 否；KServe 默认将 minReplicas 设为 1，而扩缩容至零需要受支持的 autoscaler/policy 设置，例如 minReplicas 0**

从零扩容包括容量、镜像和模型加载。Pod 数量为零并不保证节点终止。
</details>

5. 关于 Standard 模式，哪项说法正确？

   - A) 它始终保证有一个预热且健康的副本
   - B) 它使用 Deployment/Service；默认 HPA 至少保留 1 个副本，而已配置的 KEDA 路径可以支持零副本
   - C) 它始终需要 Knative
   - D) 它不支持任何自动扩缩容选项

<details>
<summary>显示答案</summary>

**答案：B) 它使用 Deployment/Service；默认 HPA 至少保留 1 个副本，而已配置的 KEDA 路径可以支持零副本**

KEDA 需要安装、有效的指标/触发器和激活路径。无论哪种模式，重启/滚动更新/横向扩容的启动延迟仍然存在。
</details>

6. 0.18.0 中现代的模式名称是什么？

   - A) Serverless 和 RawDeployment 是唯一有效的名称
   - B) Knative 和 Standard；旧名称是已弃用的别名
   - C) HPA 和 GPU
   - D) Predictor 和 Transformer

<details>
<summary>显示答案</summary>

**答案：B) Knative 和 Standard；旧名称是已弃用的别名**

检查实际的 annotation 和 config。代码回退值为 Standard；所检查的 OCI 资源 chart 默认为 Knative。
</details>

7. 什么实现了已验证的 canaryTrafficPercent 路径？

   - A) KServe controller 自行代理所有请求
   - B) KServe 设置 Knative revision 流量目标；Knative networking 路由请求
   - C) 每个 Standard Deployment 都自动具有相同的 revision 拆分
   - D) Argo Rollouts 是强制要求

<details>
<summary>显示答案</summary>

**答案：B) KServe 设置 Knative revision 流量目标；Knative networking 路由请求**

Standard 滚动更新并不是同一种按 revision 百分比划分的机制。提升/回滚和保留的工件需要单独验证。
</details>

8. 请求 nvidia.com/gpu 是否保证 GPU 推理？

   - A) 是，对每个模型都如此
   - B) 否；驱动程序、镜像/backend 和模型/device 配置也必须匹配
   - C) 它会自动安装所有必需的驱动程序
   - D) 它消除了对节点容量的需求

<details>
<summary>显示答案</summary>

**答案：B) 否；驱动程序、镜像/backend 和模型/device 配置也必须匹配**

资源分配和实际模型执行是不同的。Karpenter 在受策略、配额和可用性约束的前提下提供符合条件的容量。
</details>

## 简答题

9. 为什么始终预热与扩缩容至零并非两种模式之间的绝对区别？

<details>
<summary>显示答案</summary>

Knative 可以通过最小值设置保留预热副本，而 Standard 可以搭配合适的外部信号使用 KEDA。两种模式都不保证可用性或延迟；请测试就绪状态、加载、容量和恢复。
</details>

10. 为什么仅有工件 URI 不足够，以及应如何对待 TorchServe？

<details>
<summary>显示答案</summary>

运行时、模型格式/布局、库版本、凭据、端口和协议必须匹配。TorchServe 表示它不再处于积极维护状态，且没有计划中的安全修复，因此旧的运行时目录条目并不能证明它是一个受维护的默认选项。
</details>

11. Pod 自动扩缩容与 EC2 扩缩容如何交互？

<details>
<summary>显示答案</summary>

Knative/HPA/KEDA 或其他已配置的 scaler 决定所需的 Pod 数量。Kubernetes 调度和 Karpenter 容量策略影响节点预置/回收。在模型 Pod 降至零后，其他工作负载或中断规则仍可能使 EC2 节点继续计费。
</details>

---

[返回学习材料](../../../ai-ml/kubeflow/06-kserve.md)