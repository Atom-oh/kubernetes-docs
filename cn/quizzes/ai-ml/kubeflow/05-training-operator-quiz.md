# Kubeflow Trainer 和分布式训练测验

本测验用于检验你对旧版 Training Operator 的框架专用 CRD、向 Kubeflow Trainer v2 统一 `TrainJob`/runtime 模型的转变，以及 Kubernetes 上分布式训练机制的理解。

## 选择题

1. 2021 年整合的原始（v1）Training Operator 的基本架构方法是什么？
   - A) 所有框架共享一个 CRD，并在运行时检测框架
   - B) 每个 ML 框架各有独立的 CRD（例如 `PyTorchJob`、`TFJob`、`MPIJob`），并由各自的 controller 实现该框架的分布式训练语义
   - C) 完全不使用 CRD — 任务通过 `kubectl run` container 直接提交，训练参数已内置于 image 中
   - D) 使用单个带有 `framework` 字段的 `TrainingJob` CRD，但共享一个 controller

<details>
<summary>显示答案</summary>

**答案：B) 每个 ML 框架各有独立的 CRD（例如 `PyTorchJob`、`TFJob`、`MPIJob`），并由各自的 controller 实现该框架的分布式训练语义**

**说明：**
v1 Training Operator 为每个框架提供一个 CRD — `PyTorchJob`、`TFJob`、`MPIJob` 等 — 每个 CRD 都由其专属 controller 支持，该 controller 理解该特定框架的分布式训练约定（例如 PyTorch 的 rank/env-var 模型与 TensorFlow 的 `TF_CONFIG`）。

</details>

2. `PyTorchJob` controller 会注入哪些环境变量，以便 worker 形成 `torch.distributed` process group？
   - A) 仅 `TF_CONFIG`
   - B) `MASTER_ADDR`、`RANK` 和 `WORLD_SIZE`
   - C) `KUBEFLOW_HOST` 和 `KUBEFLOW_PORT`
   - D) `POD_IP` 和 `POD_NAMESPACE`

<details>
<summary>显示答案</summary>

**答案：B) `MASTER_ADDR`、`RANK` 和 `WORLD_SIZE`**

**说明：**
`PyTorchJob` controller 会将 `MASTER_ADDR`、`RANK` 和 `WORLD_SIZE` 注入每个 worker Pod，使 PyTorch 的 `torch.distributed` 机制能够形成 process group 并进行协调。

</details>

3. 与 v1 Training Operator 相比，Kubeflow Trainer v2 引入的核心架构变更是什么？
   - A) 在现有 CRD 之上新增更多框架专用 CRD
   - B) 使用统一的 `TrainJob` API 以及可复用的 `TrainingRuntime`/`ClusterTrainingRuntime` 模板，取代按框架划分的 CRD
   - C) 完全不再需要 controller，仅依赖 admission webhook
   - D) 将 `TrainJob` 和 `ClusterTrainingRuntime` 合并回单个按框架划分的 CRD

<details>
<summary>显示答案</summary>

**答案：B) 使用统一的 `TrainJob` API 以及可复用的 `TrainingRuntime`/`ClusterTrainingRuntime` 模板，取代按框架划分的 CRD**

**说明：**
Trainer v2 不再为每个框架配备一个 CRD 和 controller，而是引入 `TrainJob`（运行什么）以及 `TrainingRuntime`/`ClusterTrainingRuntime`（如何运行 — 可复用的框架专用执行模板），从而将任务提交与分布式启动机制解耦。

</details>

4. 在 `TrainJob` / `ClusterTrainingRuntime` 的划分中，哪个对象通常由平台团队负责，并跨多个独立训练运行重复使用？
   - A) `TrainJob`
   - B) `ClusterTrainingRuntime`
   - C) 两者始终会为每次运行重新创建
   - D) 两者都不是 — 而是创建 `PyTorchJob`

<details>
<summary>显示答案</summary>

**答案：B) `ClusterTrainingRuntime`**

**说明：**
`ClusterTrainingRuntime`（或 namespace 范围内的 `TrainingRuntime`）是平台团队定义一次即可复用的模板，涵盖 container image 和分布式启动机制。各个 `TrainJob` 通过名称引用它，并且只提供该次运行专用的 script、参数和 worker 数量。

</details>

5. Kubeflow Trainer v2.2 首先为哪两种额外训练 runtime 添加了一等支持？
   - A) TensorFlow 和 MXNet
   - B) JAX 和 XGBoost
   - C) Scikit-learn 和 ONNX
   - D) Spark MLlib 和 H2O

<details>
<summary>显示答案</summary>

**答案：B) JAX 和 XGBoost**

**说明：**
根据 Kubeflow Trainer 的[发行说明](https://github.com/kubeflow/trainer/releases)，v2.2（约于 2026 年 3 月发布）在现有 PyTorch 支持之外，新增了对 JAX 和 XGBoost 训练 runtime 的一等支持，并增强了可观测性以及对用于 HPC 风格工作负载的 Flux Framework 集成。

</details>

6. 截至 Kubeflow Community Distribution 26.03 版本，以下哪项最准确地描述了从 v1 迁移到 Trainer v2 的当前状态？
   - A) 迁移已完全完成；所有发行版均已移除旧版 Training Operator
   - B) 旧版 Training Operator（1.9.2）仍与 Trainer v2 一同包含在 26.03 发行版中；对许多团队而言，将现有任务迁移至 `TrainJob` 仍是正在进行的转变
   - C) Kubeflow Trainer v2 已被弃用，转而恢复使用 v1 CRD
   - D) `TrainJob` 和 `PyTorchJob` 只是同一个 CRD 的两个名称

<details>
<summary>显示答案</summary>

**答案：B) 旧版 Training Operator（1.9.2）仍与 Trainer v2 一同包含在 26.03 发行版中；对许多团队而言，将现有任务迁移至 `TrainJob` 仍是正在进行的转变**

**说明：**
Kubeflow Community Distribution 26.03 仍同时提供旧版 Training Operator 1.9.2 和 Trainer v2，这反映出二者共存，且许多团队仍处于迁移过程中，而非已完全切换至 `TrainJob`。

</details>

7. 为什么分布式训练任务通常需要 gang scheduling？
   - A) Kubernetes 默认要求 namespace 中的所有 Pod 都采用 gang scheduling
   - B) 训练开始前，所有 worker 通常都需要被调度并同时运行；部分调度会浪费 GPU 容量，还可能导致死锁
   - C) Gang scheduling 仅适用于无状态 Web 工作负载
   - D) 这是 cloud provider 施加的计费要求

<details>
<summary>显示答案</summary>

**答案：B) 训练开始前，所有 worker 通常都需要被调度并同时运行；部分调度会浪费 GPU 容量，还可能导致死锁**

**说明：**
若一个分布式训练任务只调度到了部分所需 worker，它可能会无限期等待其余 worker，浪费已占用的 GPU 容量，并可能造成死锁。Gang-scheduling 原语会将任务的 Pod 作为全有或全无的调度单元进行分组，以避免此问题。

</details>

## 简答题

8. headless Service 在协调 Kubernetes 上的多 worker 分布式训练任务中起什么作用？

<details>
<summary>显示答案</summary>

**答案：** 它为每个 worker Pod 提供稳定且可解析的 DNS 名称，使其他 worker 可以发现它，而无需依赖在重新调度时可能变化的 Pod IP。

**说明：**
分布式训练 worker 需要可靠地相互发现；位于 worker Pod 前方的 headless Service 可提供稳定的基于 DNS 的发现机制，即使单个 Pod 被重新调度也能继续工作。

</details>

9. 在本文档对 Katib 的交叉引用中，`TrainJob` 在 Katib Trial 内起什么作用？

<details>
<summary>显示答案</summary>

**答案：** Katib 通常会将 `TrainJob` 模板化为每个 Trial 的底层训练任务，将该 Trial 所选的超参数值作为 script 参数注入，并读取回报的指标以引导搜索。

**说明：**
Katib 本身无需了解分布式启动机制 — 它会针对平台团队已定义的 runtime，为每个 Trial 创建一个 `TrainJob`，从而使超参数搜索逻辑与训练执行机制解耦。

</details>

10. 对于将现有 v1 CRD manifest（例如 `PyTorchJob`）迁移至 Kubeflow Trainer v2 的逐字段权威参考，应前往何处查阅，而不是依赖本文档？

<details>
<summary>显示答案</summary>

**答案：** kubeflow.org 上的“迁移至 Kubeflow Trainer v2”指南。

**说明：**
本文档在较高层次上介绍概念转变和机制，但有意不重复列出每一个迁移步骤；官方 kubeflow.org 迁移指南是具体逐字段映射的权威来源。

</details>

---

[返回学习材料](../../../ai-ml/kubeflow/05-training-operator.md)
