# Kubeflow Trainer 与分布式训练测验

本测验将检验你对旧版 Training Operator 中面向框架的 CRD、向 Kubeflow Trainer v2 统一的 `TrainJob`/runtime 模型转变，以及 Kubernetes 上分布式训练机制的理解。

## 选择题

1. 2021 年整合的原始（v1）Training Operator，其基本架构方法是什么？
   - A) 所有框架共用一个 CRD，并在运行时检测框架
   - B) 每种 ML 框架使用单独的 CRD（例如 `PyTorchJob`、`TFJob`、`MPIJob`），每个 CRD 都有自己的控制器来实现该框架的分布式训练语义
   - C) 完全不使用 CRD；通过 `kubectl run` 直接提交作业，并将训练参数预先打包到镜像中
   - D) 使用一个带有 `framework` 字段的 `TrainingJob` CRD，但由一个共享控制器处理

<details>
<summary>显示答案</summary>

**答案：B) 每种 ML 框架使用单独的 CRD（例如 `PyTorchJob`、`TFJob`、`MPIJob`），每个 CRD 都有自己的控制器来实现该框架的分布式训练语义**

**说明：**
v1 Training Operator 为每种框架提供一个 CRD（`PyTorchJob`、`TFJob`、`MPIJob` 等），每个 CRD 都由自己的控制器支持，该控制器了解特定框架的分布式训练约定（例如，PyTorch 的 rank/环境变量模型与 TensorFlow 的 `TF_CONFIG`）。

</details>

2. `PyTorchJob` 控制器会注入哪些环境变量，以便 worker 组成 `torch.distributed` 进程组？
   - A) 仅 `TF_CONFIG`
   - B) `MASTER_ADDR`、`RANK` 和 `WORLD_SIZE`
   - C) `KUBEFLOW_HOST` 和 `KUBEFLOW_PORT`
   - D) `POD_IP` 和 `POD_NAMESPACE`

<details>
<summary>显示答案</summary>

**答案：B) `MASTER_ADDR`、`RANK` 和 `WORLD_SIZE`**

**说明：**
`PyTorchJob` 控制器会向每个 worker Pod 注入 `MASTER_ADDR`、`RANK` 和 `WORLD_SIZE`，以便 PyTorch 的 `torch.distributed` 机制组成进程组并进行协调。

</details>

3. 与 v1 Training Operator 相比，Kubeflow Trainer v2 引入的核心架构变化是什么？
   - A) 在现有 CRD 的基础上增加更多面向框架的 CRD
   - B) 用统一的 `TrainJob` API，以及可复用的 `TrainingRuntime`/`ClusterTrainingRuntime` 模板取代面向各框架的 CRD
   - C) 完全取消控制器，仅依赖准入 Webhook
   - D) 将 `TrainJob` 和 `ClusterTrainingRuntime` 合并回单个面向框架的 CRD

<details>
<summary>显示答案</summary>

**答案：B) 用统一的 `TrainJob` API，以及可复用的 `TrainingRuntime`/`ClusterTrainingRuntime` 模板取代面向各框架的 CRD**

**说明：**
Trainer v2 不再为每种框架配置一个 CRD 和控制器，而是引入 `TrainJob`（要运行什么）以及 `TrainingRuntime`/`ClusterTrainingRuntime`（如何运行：可复用的、面向特定框架的执行模板），从而将作业提交与分布式启动机制解耦。

</details>

4. 在 `TrainJob` / `ClusterTrainingRuntime` 的拆分中，通常由平台团队管理并在多个独立训练任务之间复用的是哪个对象？
   - A) `TrainJob`
   - B) `ClusterTrainingRuntime`
   - C) 两者每次运行时都会全新创建
   - D) 两者都不是；改为创建 `PyTorchJob`

<details>
<summary>显示答案</summary>

**答案：B) `ClusterTrainingRuntime`**

**说明：**
`ClusterTrainingRuntime`（或限定在命名空间范围内的 `TrainingRuntime`）是平台团队一次性定义的可复用模板，其中涵盖容器镜像和分布式启动机制。单个 TrainJob 通过 kind/name 引用它，并提供允许的、针对本次运行的设置。numNodes 是训练 Pod 的数量，不一定等于 EC2 实例数量。

</details>

5. Kubeflow Trainer v2.2 首先新增了对哪两种训练 runtime 的一等支持？
   - A) TensorFlow 和 MXNet
   - B) JAX 和 XGBoost
   - C) Scikit-learn 和 ONNX
   - D) Spark MLlib 和 H2O

<details>
<summary>显示答案</summary>

**答案：B) JAX 和 XGBoost**

**说明：**
根据 Kubeflow Trainer 的[发行说明](https://github.com/kubeflow/trainer/releases)，v2.2（于 2026 年 3 月 20 日发布）在现有 PyTorch 支持之外，新增了对 JAX 和 XGBoost 训练 runtime 的一等支持，并提供 Flux 策略/集成。trainerStatus 是由 TrainJobStatus 门控的 alpha 功能，默认禁用，需要显式报告应用状态。

</details>

6. 截至 Kubeflow Community Distribution 26.03.1 发布时，关于从 v1 迁移到 Trainer v2 的当前状态，哪项描述最准确？
   - A) 迁移已全部完成；所有发行版都已移除旧版 Training Operator
   - B) 在 26.03.1 发行版中，旧版 Training Operator（1.9.2）仍与 Trainer v2 一同打包；旧版作业迁移到 TrainJob 需要单独验证
   - C) Kubeflow Trainer v2 已弃用，改为恢复使用 v1 CRD
   - D) `TrainJob` 和 `PyTorchJob` 只是同一个 CRD 的两个名称

<details>
<summary>显示答案</summary>

**答案：B) 在 26.03.1 发行版中，旧版 Training Operator（1.9.2）仍与 Trainer v2 一同打包；旧版作业迁移到 TrainJob 需要单独验证**

**说明：**
Kubeflow Community Distribution 26.03.1 仍随 Trainer v2 一同提供旧版 Training Operator 1.9.2，这表明两个 API 都可用，但并不代表任何特定团队的迁移进度。

</details>

7. 为什么可选的 gang 调度有助于同步分布式训练？
   - A) Kubernetes 默认要求命名空间中的所有 Pod 都使用 gang 调度
   - B) 当作业无法获得通信所需的全部 worker 时，它可以减少资源被部分分配的情况
   - C) 只有无状态 Web 工作负载才需要 gang 调度
   - D) 这是云服务提供商规定的计费要求

<details>
<summary>显示答案</summary>

**答案：B) 当作业无法获得通信所需的全部 worker 时，它可以减少资源被部分分配的情况**

**说明：**
固定规模的同步作业需要在 rendezvous 阶段具备所需的进程。Trainer 不会自动启用 gang 调度；默认 Torch runtime 没有 podGroupPolicy。需要单独配置调度器/CRD/策略。在超时时间范围内，节点也可以按顺序完成预配。

</details>

## 简答题

8. 在 Kubernetes 上协调多 worker 分布式训练作业时，无头 Service 起什么作用？

<details>
<summary>显示答案</summary>

**答案：** 它为每个 worker Pod 提供稳定且可解析的 DNS 名称，以便其他 worker 能够发现它，而不必依赖重新调度时可能发生变化的 Pod IP。

**说明：**
分布式训练 worker 需要可靠地相互发现；在 worker Pod 前配置无头 Service，并搭配合适的 Pod 命名、主机名、子域名和网络设置，可支持基于 DNS 的发现。它不会保留进程状态或 IP。

</details>

9. 在本文档对 Katib 的交叉引用中，`TrainJob` 在 Katib Trial 中发挥什么作用？

<details>
<summary>显示答案</summary>

**答案：** 在模板、runtime、状态条件和指标收集都兼容的情况下，Katib 可以为每个 Trial 创建一个 TrainJob，并将该 Trial 选定的超参数值作为脚本参数注入，然后读取报告的指标来引导搜索。

**说明：**
Katib 本身不需要了解分布式启动机制；它会针对平台团队已定义的 runtime，为每个 Trial 创建一个 `TrainJob`，从而使超参数搜索逻辑与训练执行机制相互解耦。

</details>

10. 如果要查阅逐字段的权威参考，了解如何将现有 v1 CRD 清单（例如 `PyTorchJob`）迁移到 Kubeflow Trainer v2，而不是依赖本文档，应该去哪里？

<details>
<summary>显示答案</summary>

**答案：** kubeflow.org 上的《迁移到 Kubeflow Trainer v2》指南。

**说明：**
本文档从较高层面介绍了概念上的转变和相关机制，但有意不重复列出每一步迁移操作；[置顶的官方指南](https://github.com/kubeflow/trainer/blob/v2.3.0/docs/operator-guides/migration.md)提供了一个 PyTorchJob 示例，但并未详尽映射所有框架/字段。请比较实际的启动角色、重试、存储和网络配置。

</details>

---

[返回学习资料](../../../ai-ml/kubeflow/05-training-operator.md)
