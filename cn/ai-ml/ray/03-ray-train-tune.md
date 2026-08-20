# 第 3 部分：Ray Train 和 Ray Tune

> **支持的版本**：Ray 2.57.0
> **最后更新**：August 20, 2026

## 实验环境设置

要跟随本文档中的示例操作，您需要以下工具和环境：

### 必需工具

* Python 3.10 或更高版本
* `pip install "ray[train,tune]"`
* 访问 Ray 集群（请参阅[第 2 部分：KubeRay Operator](02-kuberay-operator.md)，了解如何在 EKS 上部署集群；或者，为本文档中的示例在本地运行 `ray.init()`）

## Ray Train：基于 Ray 原语的分布式训练

[第 1 部分](01-architecture.md)介绍了 Ray 的核心原语：任务、Actor 和对象存储。直接针对这些原语编写分布式训练作业是可行的，但这意味着需要手动编写大量样板代码：为每个 GPU 启动一个 worker 进程，设置这些 worker 用于同步梯度的通信组，以及在所有 worker 之间一致地协调 checkpoint。

**Ray Train** 是一个构建在 Ray 任务和 Actor 原语之上的库，可处理这些样板工作。它接收一个根据熟悉的框架 API 编写的训练函数——最常见的情形是 PyTorch，不过 Ray Train 也支持其他框架——并按照您的要求在任意数量的分布式 worker 上运行该函数，而训练函数的作者无需直接管理 worker 启动、worker 间通信或 checkpoint 协调。

### Ray Train V2

Ray Train 的公共 API 在项目历史中不断演进。面向用户的导入路径对于 PyTorch 训练仍然是 `ray.train.torch.TorchTrainer`，但该路径背后的实现已经被重写——这次重写（“Train V2”）整合并简化了早期一代 Trainer 类的内部工作方式，现在也是通过该导入获得的默认实现。如果您遇到一个固定在此次重写推出之前的 Ray 版本上的旧代码库，应将其视为运行在早期实现上，而不要假定它已损坏；具体细节请查阅 docs.ray.io 上的 Ray 文档，因为默认实现切换的确切版本会因 Ray 版本而变化。

## Ray Train 核心概念

### Trainer

**Trainer**（例如 `TorchTrainer`）封装用户提供的训练函数。训练函数包含所选框架的常规模型训练逻辑：构建模型、迭代 batch、计算 loss，以及执行 optimizer step。Trainer 负责在底层框架的数据并行训练所期望的分布式进程组中为每个 worker 启动一次该函数（例如 PyTorch DDP 进程组），因此训练函数本身无需手动进行设置。

### ScalingConfig

**ScalingConfig** 告诉 Trainer 要启动多少个 worker，以及每个 worker 需要哪些资源——例如，要运行多少个 worker，以及每个 worker 是否需要 GPU。Trainer 使用此配置从底层 Ray 集群请求相应资源，方式与任何其他 Ray 任务或 Actor 相同。

### Checkpoint

Ray Train worker 可以在训练期间报告 checkpoint。checkpoint 捕获足够的状态——通常是模型权重和 optimizer 状态——以便从该点恢复训练，而不是从头开始。这有两个目的：它使长时间运行的分布式训练作业能够在 worker 发生故障后恢复，而不会丢失此前的所有进度；并且它将已训练的模型交给工作流中的后续步骤，无论是后续的超参数调优决策（如下文所述），还是将结果注册为模型版本（概念上类似于本文档站点的 MLflow Model Registry 材料所涵盖的内容，尽管该材料并非 Ray 专用）。

## Ray Tune：跨集群的超参数搜索

**Ray Tune** 是一个同样构建在 Ray 之上的超参数调优库，它可在集群中并行运行许多训练 trial，并使用可插拔的搜索算法来决定接下来尝试哪些超参数组合。每个 trial 使用一组特定的超参数训练模型，并报告结果，供 Tune 的搜索算法决定下一步尝试什么。

这在概念上与本文档站点的 Kubeflow 子树针对 Katib 所描述的内容相对应，但 Tune 是 Ray 生态系统原生的库，而不是基于独立 Kubernetes CRD 的系统。

## 结合使用 Ray Train 和 Ray Tune

Ray Tune 运行的 trial 不必是单进程函数。常见模式是向 Tune 提供一个 Ray Train `Trainer` 作为其搜索的 trainable：随后每个超参数 trial 都会成为各自的分布式 Ray Train 运行，可能跨越多个 GPU 或多个节点。

当模型的训练成本很高，以致单个 trial 本身就需要分布式训练才能在合理时间内完成时，这种组合就很重要。如果没有它，团队将面临一个棘手的选择：针对分布式训练作业串行调优超参数，或者在搜索阶段放弃分布式训练。由于两个库共享相同的底层 Ray 原语，Tune 可以驱动多个并发的 Ray Train 运行，每个运行都有各自的一组分布式 worker，而任一库都无需为另一方提供特殊集成代码。

```mermaid
flowchart TB
    Driver["Ray Tune Driver<br/>(search algorithm)"]

    subgraph Trial1["Trial 1: Ray Train run"]
        T1W1["Worker Actor 1"]
        T1W2["Worker Actor 2"]
        T1OS[(("Object Store"))]
        T1W1 <--> T1OS
        T1W2 <--> T1OS
    end

    subgraph Trial2["Trial 2: Ray Train run"]
        T2W1["Worker Actor 1"]
        T2W2["Worker Actor 2"]
        T2OS[(("Object Store"))]
        T2W1 <--> T2OS
        T2W2 <--> T2OS
    end

    Driver -->|launches with hyperparameter set A| Trial1
    Driver -->|launches with hyperparameter set B| Trial2
    Trial1 -->|reports results/checkpoints| Driver
    Trial2 -->|reports results/checkpoints| Driver
    Driver -->|decides next round of trials| Driver

    style Driver fill:#4fc3f7
    style Trial1 fill:#81c784
    style Trial2 fill:#ffb74d
```

## 资源分配和集群自动扩缩器

Ray Train 和 Ray Tune 都通过 [第 1 部分](01-architecture.md)所述的 Ray 常规任务和 Actor 资源请求机制请求其 worker 所需的 CPU 和 GPU——不存在专门用于训练或调优的独立资源请求路径。这一点在 EKS 上很重要，因为这正是让第 2 部分所介绍的 KubeRay 管理的 autoscaler 能够响应训练或调优作业实际资源需求的机制。集群无需预先按其将要运行的最大作业进行扩容；当 Ray Tune sweep 启动更多并发 trial 时，autoscaler 可以请求更多 worker 节点，并在 trial 完成后缩减规模。

## 实用说明：EKS 上的协同调度和 GPU 节点准备时间

构成单个 Ray Train 运行的分布式 worker 进程通常需要协同调度——它们都需要同时启动并占有所分配的 GPU，才能建立其组成的通信组，这类似于本文档站点其他分布式训练系统中讨论的 gang scheduling 需求。如果集群的 autoscaler 无法在合理时间窗口内配置所有请求的 GPU worker，训练运行可能会停滞，等待最后几个 worker 启动。

这直接关系到 GPU 节点池配置的准备时间：从节点池获取新的 GPU 容量需要时间，并且该时间通常比通用 CPU 节点更长、更难预测。本文档站点的 [Karpenter 指南](../../autoscaling/02-karpenter.md)深入介绍了节点配置机制；在规划 Ray Train/Tune 时需要理解的是，EKS 上训练作业的实际启动时间取决于集群能够多快地协同调度它请求的每一个 worker，而不只是取决于作业何时提交。

## 后续步骤

第 3 部分介绍了 Ray Train 的 Trainer、ScalingConfig 和 checkpoint、Ray Tune 基于 trial 的超参数搜索，以及当调优 trial 本身需要分布式训练时二者如何结合。[第 4 部分：Ray Serve](04-ray-serve.md)从训练转向服务：将经过训练（以及可能经过调优）的模型置于可扩展的推理端点之后。

[返回主页](./README.md)

## 测验

通过 [Ray Train 和 Ray Tune 测验](../../quizzes/ai-ml/ray/03-ray-train-tune-quiz.md)测试您的理解。
