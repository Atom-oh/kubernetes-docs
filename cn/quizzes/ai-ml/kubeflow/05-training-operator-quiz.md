# Kubeflow Trainer 和分布式训练测验

本测验检验您对旧版 Training Operator 的框架专用 CRD、向 Kubeflow Trainer v2 统一 `TrainJob`/runtime 模型的转变，以及 Kubernetes 上分布式训练机制的理解。

## 选择题

1. 2021 年整合的原始（v1）Training Operator 采用的基础架构方式是什么？
   - A) 所有框架共用一个 CRD，并在运行时检测框架
   - B) 每个 ML 框架使用一个独立的 CRD（例如 `PyTorchJob`、`TFJob`、`MPIJob`），每个 CRD 都有自己的 controller 来实现该框架的分布式训练语义
   - C) 完全不使用 CRD — 通过 `kubectl run` container 直接提交 job，并将训练参数嵌入 image
   - D) 使用带有 `framework` 字段的单个 `TrainingJob` CRD，但只有一个共享 controller

<details>
<summary>显示答案</summary>

**答案：B) 每个 ML 框架使用一个独立的 CRD（例如 `PyTorchJob`、`TFJob`、`MPIJob`），每个 CRD 都有自己的 controller 来实现该框架的分布式训练语义**

**说明：**
v1 Training Operator 为每个框架提供一个 CRD — `PyTorchJob`、`TFJob`、`MPIJob` 等 — 每个 CRD 都由自己的 controller 支持，该 controller 理解该特定框架的分布式训练约定（例如 PyTorch 的 rank/env-var 模型与 TensorFlow 的 `TF_CONFIG`）。

</details>

2. `PyTorchJob` controller 会注入哪些环境变量，以便 worker 组成 `torch.distributed` process group？
   - A) 仅 `TF_CONFIG`
   - B) `MASTER_ADDR`、`RANK` 和 `WORLD_SIZE`
   - C) `KUBEFLOW_HOST` 和 `KUBEFLOW_PORT`
   - D) `POD_IP` 和 `POD_NAMESPACE`

<details>
<summary>显示答案</summary>

**答案：B) `MASTER_ADDR`、`RANK` 和 `WORLD_SIZE`**

**说明：**
`PyTorchJob` controller 将 `MASTER_ADDR`、`RANK` 和 `WORLD_SIZE` 注入每个 worker Pod，使 PyTorch 的 `torch.distributed` 机制能够组成 process group 并进行协调。

</details>

3. 与 v1 Training Operator 相比，Kubeflow Trainer v2 引入的核心架构变化是什么？
   - A) 在现有的框架专用 CRD 之上添加更多框架专用 CRD
   - B) 使用统一的 `TrainJob` API 以及可复用的 `TrainingRuntime`/`ClusterTrainingRuntime` template 替换按框架划分的 CRD
   - C) 完全不再需要 controller，仅依赖 admission webhook
   - D) 将 `TrainJob` 和 `ClusterTrainingRuntime` 合并回单个按框架划分的 CRD

<details>
<summary>显示答案</summary>

**答案：B) 使用统一的 `TrainJob` API 以及可复用的 `TrainingRuntime`/`ClusterTrainingRuntime` template 替换按框架划分的 CRD**

**说明：**
Trainer v2 不再为每个框架提供一个 CRD 和 controller，而是引入 `TrainJob`（运行什么）和 `TrainingRuntime`/`ClusterTrainingRuntime`（如何运行 — 可复用的、框架专用的执行 template），将 job 提交与分布式启动机制解耦。

</details>

4. 在 `TrainJob` / `ClusterTrainingRuntime` 的划分中，通常由 platform team 拥有并在许多单独训练运行中复用的是哪个对象？
   - A) `TrainJob`
   - B) `ClusterTrainingRuntime`
   - C) 两者始终都会在每次运行时重新创建
   - D) 两者都不是 — 而是创建 `PyTorchJob`

<details>
<summary>显示答案</summary>

**答案：B) `ClusterTrainingRuntime`**

**说明：**
`ClusterTrainingRuntime`（或 namespace-scoped 的 `TrainingRuntime`）是 platform team 一次性定义的可复用 template，其中涵盖 container image 和分布式启动机制。单独的 TrainJob 引用 kind/name，并提供允许的运行专用设置。numNodes 是训练 Pod 数量，不一定是 EC2 instance 数量。

</details>

5. Kubeflow Trainer v2.2 首次为哪两种额外训练 runtime 添加了第一方支持？
   - A) TensorFlow 和 MXNet
   - B) JAX 和 XGBoost
   - C) Scikit-learn 和 ONNX
   - D) Spark MLlib 和 H2O

<details>
<summary>显示答案</summary>

**答案：B) JAX 和 XGBoost**

**说明：**
根据 Kubeflow Trainer 的 [release notes](https://github.com/kubeflow/trainer/releases)，v2.2（于 2026 年 3 月 20 日发布）在现有 PyTorch 支持的基础上，添加了第一方 JAX 和 XGBoost 训练 runtime，并提供 Flux policy/integration。trainerStatus 是一项由 alpha TrainJobStatus-gated 控制的功能，默认禁用，需要显式的 application reporting。

</details>

6. 截至 Kubeflow Community Distribution 26.03.1 release，以下哪项陈述最准确地描述了从 v1 到 Trainer v2 的迁移现状？
   - A) 迁移已完全完成；所有 distribution 都已移除旧版 Training Operator
   - B) 旧版 Training Operator (1.9.2) 仍与 Trainer v2 一起包含在 26.03.1 distribution 中，且旧版 job 和 TrainJob 需要经过单独验证的迁移
   - C) Kubeflow Trainer v2 已被弃用，转而恢复使用 v1 CRD
   - D) `TrainJob` 和 `PyTorchJob` 只是同一个 CRD 的两个名称

<details>
<summary>显示答案</summary>

**答案：B) 旧版 Training Operator (1.9.2) 仍与 Trainer v2 一起包含在 26.03.1 distribution 中，且旧版 job 和 TrainJob 需要经过单独验证的迁移**

**说明：**
Kubeflow Community Distribution 26.03.1 仍会随附旧版 Training Operator 1.9.2 和 Trainer v2，这表明两个 API 都被提供，而非表明任何特定 team 的迁移进度。

</details>

7. 为什么可选的 gang scheduling 有助于同步分布式训练？
   - A) Kubernetes 默认要求 namespace 中的所有 Pod 都采用 gang scheduling
   - B) 当 job 无法获得通信所需的全部 worker 时，它可以减少部分资源分配
   - C) Gang scheduling 仅适用于无状态 Web workload
   - D) 它是 cloud provider 强加的计费要求

<details>
<summary>显示答案</summary>

**答案：B) 当 job 无法获得通信所需的全部 worker 时，它可以减少部分资源分配**

**说明：**
固定大小的同步 job 在 rendezvous 时需要所需的 process。Trainer 不会自动启用 gang scheduling；默认 Torch runtime 没有 podGroupPolicy。需要单独配置 scheduler/CRD/policy。顺序 node provisioning 可以在 timeout 限制内成功。

</details>

## 简答题

8. headless Service 在 Kubernetes 上协调多 worker 分布式训练 job 时发挥什么作用？

<details>
<summary>显示答案</summary>

**答案：** 它为每个 worker Pod 提供稳定、可解析的 DNS 名称，使其他 worker 能够发现它，而不是依赖在重新调度时可能变化的 Pod IP。

**说明：**
分布式训练 worker 需要可靠地相互发现；位于 worker Pod 前方的 headless Service 通过适当的 Pod naming/hostname/subdomain 和 networking 支持基于 DNS 的发现。它不会保留 process state 或 IP。

</details>

9. 在本文档对 Katib 的交叉引用中，`TrainJob` 在 Katib Trial 中扮演什么角色？

<details>
<summary>显示答案</summary>

**答案：** 在具备兼容的 template、runtime、status condition 和 metric collection 的情况下，Katib 可以为每个 Trial 创建一个 TrainJob，将该 Trial 选定的 hyperparameter 值作为 script argument 注入，并读取报告的 metric 以引导搜索。

**说明：**
Katib 本身不需要了解分布式启动机制 — 它会针对 platform team 已定义的 runtime，为每个 Trial 创建一个 `TrainJob`，使 hyperparameter-search logic 与训练执行机制保持解耦。

</details>

10. 对于将现有 v1 CRD manifest（例如 `PyTorchJob`）迁移到 Kubeflow Trainer v2 的逐字段权威参考，您应该去哪里查找，而不是依赖本文档？

<details>
<summary>显示答案</summary>

**答案：** kubeflow.org 上的“迁移到 Kubeflow Trainer v2”指南。

**说明：**
本文档从较高层面介绍概念转变和机制，但特意没有重述每一步迁移操作；[固定版本的官方指南](https://github.com/kubeflow/trainer/blob/v2.3.0/docs/operator-guides/migration.md) 提供了 PyTorchJob 示例，而不是每个框架/字段的详尽映射。请比较实际的 launch role、retry、storage 和 networking。

</details>

---

[返回学习材料](../../../ai-ml/kubeflow/05-training-operator.md)
