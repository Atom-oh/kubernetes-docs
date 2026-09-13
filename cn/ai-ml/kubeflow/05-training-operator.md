# 第 5 部分：Kubeflow Trainer 与分布式训练

> **审查基准**：Trainer 2.2.0 / 社区发行版 26.03.1；另行比较 2.3.0 升级
> **最后更新**：September 12, 2026

## 实验环境设置

使用兼容的 Kubernetes、Trainer controller/CRD、runtime 及其依赖项（如 JobSet）。GPU 取决于工作负载；可以进行 CPU 训练。GPU 工作负载还需要 driver、device plugin、node capacity 和网络。此处验证的是 Helm 渲染和 schema 检查，而不是训练执行。

## 从框架专用 Operator 到统一 API

Kubernetes 上的分布式训练在 Kubeflow 项目中经历了真正的架构转变，在接触任何 YAML 之前，这是最重要的理解要点。

### 原始 Training Operator (v1)

Kubeflow 在 2021 年整合的 Training Operator 采用了**框架专用 CRD**方法。每个受支持的 ML framework 都有自己的 Custom Resource Definition，每个都有自己的 controller，用于实现该 framework 特有的分布式训练语义：

* **`PyTorchJob`** — controller 理解 PyTorch 的分布式启动约定，将 `MASTER_ADDR`、`RANK` 和 `WORLD_SIZE` 等环境变量注入每个 worker Pod，使 `torch.distributed` 能够形成 process group。
* **`TFJob`** — controller 则构建 `TF_CONFIG` 环境变量（描述 cluster task role 的 JSON blob — chief、worker、parameter server），这是 TensorFlow 的 distribution strategy 所期望的配置。
* **`MPIJob`** — controller 负责跨 Pod 启动 MPI job，协调一个 `mpirun` 风格的 launcher 来对接一组 worker Pod。

除了这三种之外，v1 Training Operator 还为少数其他 framework 提供了 CRD。每个 CRD 都将不同 framework 对“worker 如何相互发现并就其 role 达成一致”的理念直接编码到独立 controller 中，因此添加 framework 需要集成，而共享的 Job-controller 基础设施仍可复用。

### 转向 Kubeflow Trainer v2

Kubeflow Trainer v2 使用围绕两个概念构建的单一统一 API 取代了每个 framework 一个 CRD 的模式：

* **`TrainJob`** — 描述*运行什么*：训练 script/entrypoint、arguments、resource count（例如 worker 数量），以及对执行该任务的 runtime 的引用。这是 ML practitioner 为单次训练运行创建的对象。
* **`TrainingRuntime` / `ClusterTrainingRuntime`** — 描述*如何运行*：可复用、特定 framework 的执行 template，涵盖 container image、分布式启动机制（worker 如何相互发现、使用哪些 env var 或 launcher process）以及默认 resource shape。platform team 一次性定义少量此类配置 — 例如 PyTorch DDP runtime、MPI runtime — 许多不同的 `TrainJob` 会在多次训练运行中引用相同 runtime。

这映射了 Kubernetes 其他地方可见的模式：将可复用的“template” resource 与使用它的“instance”分离，其精神类似于 `StorageClass` 是许多 `PersistentVolumeClaim` 引用的可复用 template。实际优势是 platform team 可以在一个位置（runtime）拥有并版本化棘手的分布式启动机制，而提交 job 的 ML practitioner 只需提供自己的 script 并按名称请求 runtime — runtime 可减少重复设置，而训练代码仍必须处理兼容的分布式初始化、数据分片、checkpointing 和恢复。

### 2.2.0 与 2.3.0 之间的差异

[Trainer 2.2.0](https://github.com/kubeflow/trainer/releases/tag/v2.2.0) 于 2026 年 3 月 20 日发布，并包含在 26.03.1 中。它新增 JAX/XGBoost runtime 以及 Flux policy/integration；包含某项功能并不能证明其与每种 image、网络或 accelerator 配置兼容。

2.2.0 还将 `PodTemplateOverrides` 替换为 `RuntimePatches`，并从 Torch policy 中移除 `numProcPerNode`，同时移除 `ElasticPolicy`。不要将 runtime Torch policy 与每次运行的 `trainer.numProcPerNode` 混淆。较早的 2.x manifest 也可能需要迁移。

`status.trainerStatus` 中的 runtime 进度/metrics 需要 **alpha TrainJobStatus feature gate，默认禁用**。训练代码必须通过可正常工作的 TLS/projected ServiceAccount-token access 向 status server 报告。注入的 token/CA 环境值是文件路径，而非 secret 内容。仅打印日志不会自动填充 status metrics。

[2.3.0](https://github.com/kubeflow/trainer/releases/tag/v2.3.0) 于 2026 年 8 月 7 日发布，更改了 runtime finalizer/snapshot 和 Helm CRD placement。其 release note 要求 2.0/2.1/2.2 安装必须先经过 2.3，才能升级到后续版本。升级前请审查 CRD Helm ownership 和特定 release 的迁移；删除现有 CRD 并非例行升级修复方法。

已发布的 OCI chart 也有所不同：2.2 直接渲染八个默认 runtime，而 2.3 则将它们打包在一个 runtimes.yaml ConfigMap 中，并通过 post-install/post-upgrade installer Job 应用。2.3 hook 在运行时安装 kubectl，使用 server-side 方式 force-apply resource，并按其 management label 进行 prune；还存在一个 pre-delete hook。请审查 GitOps hook 处理、网络访问和 runtime ownership。本审查渲染了这些 hook，但未执行它们。

### 迁移 Legacy API

26.03.1 包含 Trainer 2.2.0 和 legacy Training Operator 1.9.2。它们的共存并不能显示任何 team 的迁移进度。PyTorchJob/TFJob/MPIJob 和 TrainJob 是不同的 API，且不会自动转换。

固定版本的[官方迁移文档](https://github.com/kubeflow/trainer/blob/v2.3.0/docs/operator-guides/migration.md)提供了一个 PyTorchJob 到默认 Torch runtime 的示例以及 SDK 方向，而不是每个 framework/field 的详尽映射。请针对每个工作负载比较 replica role、启动 command、environment、retry、storage、scheduling/networking 和 checkpoint recovery。

## TrainJob 和 Runtime 的职责

`TrainingRuntime` 是 namespaced；`ClusterTrainingRuntime` 是 cluster-scoped。两者都包含执行 template 和 ML policy。`TrainJob.runtimeRef` 选择 kind/name，而 trainer field 可以配置 command/arguments、训练 Pod 数量和每个 Pod 的 resource。权限和允许的 override 需要单独管理。

默认 `torch-distributed` runtime 具有 `mlPolicy.numNodes: 1`、`torch: {}` 和一个 JobSet template。在 2.2.0 中，它引用 `pytorch/pytorch:2.10.0-cuda12.8-cudnn9-runtime`。请记录 image/runtime revision，并验证 architecture、driver 和 communication library；本审查未执行该 image 或训练 model。

这里的 numNodes 表示训练 Pod 数量，而不是与 EC2 instance 数量一一对应。请分别计算 process、每个 Pod 的 GPU 数量和多个 Pod 的 placement。

## Kubernetes 上的分布式训练机制

JobSet 和 runtime 组合 Job/Pod，并通过 Service/DNS 以及 rank/rendezvous 配置进行 process discovery。仅有 headless Service 无法保留 process state 或 IP；稳定的 Pod naming、hostname/subdomain 和网络条件仍然很重要。

**安装 Trainer 不会自动启用 gang scheduling。**2.2.0 默认 Torch runtime 没有 podGroupPolicy。Coscheduling/Volcano policy、CRD 和 scheduler integration 必须安装/配置，才能使用这些 PodGroup path。Kueue admission 也不同于实际的 Pod scheduling。

固定大小的同步训练需要所有必需 process 都准备好进行通信，但 node 不必在同一时刻创建。顺序 provisioning 可以在 rendezvous timeout 内成功；受支持的 elastic 工作负载适用不同规则。Gang admission 可减少部分 allocation，但无法解决每种 EC2 shortage 或 application deadlock。请将 [Karpenter](../../autoscaling/02-karpenter.md) capacity 与 JobSet、scheduler 以及 framework timeout/retry 协调起来。

![Trainer 将 TrainJob 和 runtime 组合为 JobSet，并单独展示可选的 PodGroup scheduling 和选择启用的 runtime-status reporting。](../../.gitbook/assets/en-ai-ml-kubeflow-05-training-operator-0.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-kubeflow-05-training-operator-0.html)

## 交叉参考：Katib 和 TrainJob

Katib 0.19.0 可以在已配置的 Trial template 中使用 TrainJob。请匹配 trialResources registration、runtime、success/failure condition、primary Pod/container 和 metric collection。Katib metrics reporting 与 Trainer 的选择启用 status server 是分开的。成功的 TrainJob 不会自动将 model 部署到 KServe。

## 验证和来源

已拉取并在启用默认 runtime 的情况下渲染官方 OCI Trainer Helm chart 2.2.0 和 2.3.0；并检查了 CRD/runtime schema。未执行 API admission/CEL、实际升级、JobSet 创建、分布式/GPU 训练和 status-server reporting。

- [2.2.0 TrainJob API](https://github.com/kubeflow/trainer/blob/v2.2.0/pkg/apis/trainer/v1alpha1/trainjob_types.go)
- [TrainJobStatus 默认 feature gate](https://github.com/kubeflow/trainer/blob/v2.2.0/pkg/features/features.go)
- [条件式 Coscheduling PodGroup 创建](https://github.com/kubeflow/trainer/blob/v2.2.0/pkg/runtime/framework/plugins/coscheduling/coscheduling.go)
- [默认 Torch runtime](https://github.com/kubeflow/trainer/blob/v2.2.0/manifests/base/runtimes/torch_distributed.yaml)

## 后续步骤

在完成从 framework 专用 CRD 向统一 `TrainJob`/runtime 模型的转变后，[第 6 部分：KServe — Kubernetes 上的模型服务](./06-kserve.md)将介绍针对 `TrainJob` 完成训练后，model 会发生什么：为 inference 提供服务。

[返回主页](./README.md)

## 测验

为测试你在本章中学到的内容，请尝试[主题测验](../../quizzes/ai-ml/kubeflow/05-training-operator-quiz.md)。
