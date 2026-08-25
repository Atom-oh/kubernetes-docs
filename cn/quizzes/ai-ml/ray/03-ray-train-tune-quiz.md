# Ray Train 和 Ray Tune 测验

本测验用于检验你对 Ray Train（Trainer、ScalingConfig、checkpointing）、Ray Tune 以及二者如何结合进行分布式超参数调优的理解。

## 多项选择题

1. Ray Train 主要为分布式训练脚本解决什么问题？
   - A) 它使用新的训练 API 替换 PyTorch 和其他训练框架
   - B) 它处理启动 worker 进程、设置其通信组以及协调 checkpoint 的样板代码
   - C) 它会在运行开始前自动为训练数据添加标签
   - D) 它通过完全在 CPU 上运行训练来免除对 GPU 的需求

<details>

<summary>显示答案</summary>

**答案：B) 它处理启动 worker 进程、设置其通信组以及协调 checkpoint 的样板代码**

**说明：**
Ray Train 构建在 Ray 的 task 和 actor 原语之上，并接管分布式训练的样板代码——为每个已分配资源启动一个 worker、设置 worker 间通信组（例如 PyTorch DDP 进程组），以及协调 checkpoint——因此，基于熟悉框架 API 编写的训练脚本无需由作者手动实现这些协调工作即可扩展。
</details>

2. 以下哪项最准确地描述了 Ray Train V2？
   - A) 与早期 Ray Train 版本无关的完全独立产品
   - B) 现有 `ray.train.torch.TorchTrainer` 导入路径背后的重写实现，它整合并简化了早期一代 Trainer 类在内部的工作方式
   - C) 仅支持基于 CPU 训练的 Ray Train 版本
   - D) Ray 不再记录文档的已弃用 API

<details>

<summary>显示答案</summary>

**答案：B) 现有 `ray.train.torch.TorchTrainer` 导入路径背后的重写实现，它整合并简化了早期一代 Trainer 类在内部的工作方式**

**说明：**
Ray Train 的 API 表面随时间演进，但面向用户的导入路径（PyTorch 使用 `ray.train.torch.TorchTrainer`）并未改变——改变的是其背后的实现。关于此次重写何时成为默认实现的确切版本历史，最好查阅当前 Ray 文档，而非想当然地假设。
</details>

3. `ScalingConfig` 在 Ray Train 中的作用是什么？
   - A) 指定要启动多少个 worker，以及每个 worker 需要哪些资源（例如 GPU）
   - B) 定义训练期间使用的神经网络架构
   - C) 设置 optimizer 的学习率调度
   - D) 配置 Ray cluster 运行所在的云区域

<details>

<summary>显示答案</summary>

**答案：A) 指定要启动多少个 worker，以及每个 worker 需要哪些资源（例如 GPU）**

**说明：**
`ScalingConfig` 告诉 Trainer 要启动多少个 worker，以及每个 worker 是否需要 GPU。Trainer 使用它从底层 Ray cluster 请求相应资源，方式与任何其他 Ray task 或 actor 相同。
</details>

4. 除了支持在 worker 失败后恢复，Ray Train checkpointing 还有什么其他用途？
   - A) 压缩训练数据集以节省存储空间
   - B) 将已训练的模型移交给工作流中的后续步骤，例如超参数调优决策或模型注册
   - C) 自动将模型部署到生产 serving endpoint
   - D) 替代对 ScalingConfig 的需求

<details>

<summary>显示答案</summary>

**答案：B) 将已训练的模型移交给工作流中的后续步骤，例如超参数调优决策或模型注册**

**说明：**
已报告的 checkpoint 会捕获足以恢复训练的状态（通常是模型权重和 optimizer 状态），但它也是移交给后续步骤的节点——例如调优决策，或将结果注册为模型版本；从概念上说，这类似于本文档站点其他地方介绍的模型注册表模式。
</details>

5. Ray Tune 的作用是什么？
   - A) 它在 cluster 中并行运行许多训练 trial，并使用可插拔搜索算法决定下一步尝试哪些超参数组合
   - B) 它每次只按顺序调优一个超参数
   - C) 它完全替代所有分布式训练工作负载中的 Ray Train
   - D) 它是一个基于 Kubernetes CRD、与 Ray 核心原语无关的 controller

<details>

<summary>显示答案</summary>

**答案：A) 它在 cluster 中并行运行许多训练 trial，并使用可插拔搜索算法决定下一步尝试哪些超参数组合**

**说明：**
Ray Tune 是构建在 Ray 之上的超参数调优库。每个 trial 使用一种超参数组合进行训练并报告结果，Tune 的搜索算法利用该结果决定下一步尝试什么。这在概念上与 Kubeflow 生态系统中 Katib 所提供的功能并行，但它原生属于 Ray，而非一个独立的基于 Kubernetes CRD 的系统。
</details>

6. 对于本身需要分布式训练的模型，Ray Tune 通常如何与 Ray Train 结合？
   - A) Tune 和 Train 无法一起使用；团队必须二选一
   - B) Tune 将 Ray Train `Trainer` 包装为其搜索的 trainable，因此每个 trial 都成为各自的分布式 Ray Train 运行
   - C) Ray Train 先运行至完成，之后 Ray Tune 才在另一个 cluster 上开始运行
   - D) Tune 使用自己的资源模型替换 Trainer 的 ScalingConfig

<details>

<summary>显示答案</summary>

**答案：B) Tune 将 Ray Train `Trainer` 包装为其搜索的 trainable，因此每个 trial 都成为各自的分布式 Ray Train 运行**

**说明：**
一种常见模式是将 Ray Train `Trainer` 作为 trainable 提供给 Tune。随后，每个超参数 trial 本身就是一次分布式 Ray Train 运行，可能跨越多个 GPU 或节点——当单个 trial 需要分布式训练才能在合理时间内完成时，这种方式很有用。
</details>

7. 为什么 EKS 上由 KubeRay 管理的 autoscaler 会响应 Ray Train 或 Ray Tune job 的实际资源需求？
   - A) 因为 Ray Train 和 Ray Tune 通过 Ray 常规的 task/actor 资源请求机制请求 CPU 和 GPU，与其他任何 Ray 工作负载相同
   - B) 因为 Ray Train 和 Ray Tune 直接与 Kubernetes API server 通信，绕过 Ray scheduler
   - C) 因为在任何 job 运行之前，cluster 必须始终预置为固定规模
   - D) 因为 Karpenter 会在训练进程内部监控 GPU 利用率

<details>

<summary>显示答案</summary>

**答案：A) 因为 Ray Train 和 Ray Tune 通过 Ray 常规的 task/actor 资源请求机制请求 CPU 和 GPU，与其他任何 Ray 工作负载相同**

**说明：**
这两个库都通过 Ray 常规的 task/actor 资源请求机制请求资源，没有专用于训练或调优的单独路径。这使得第 2 部分所介绍的 autoscaler 能够响应实际需求——当 Tune sweep 启动更多并发 trial 时请求更多 worker 节点，并在 trial 完成后缩容——而不是预先要求固定规模的 cluster。
</details>

8. 在 EKS 上，Ray Train 运行的分布式 worker 的共同调度需求可能导致什么实际问题？
   - A) 没有问题——Ray Train worker 从不需要同时启动
   - B) 如果 autoscaler 无法在合理时间窗口内预置所有请求的 worker，训练运行可能会在等待最后几个 GPU worker 启动时停滞
   - C) 共同调度只与 Ray Tune 有关，与 Ray Train 无关
   - D) Checkpointing 会自动解决任何共同调度延迟

<details>

<summary>显示答案</summary>

**答案：B) 如果 autoscaler 无法在合理时间窗口内预置所有请求的 worker，训练运行可能会在等待最后几个 GPU worker 启动时停滞**

**说明：**
一次 Ray Train 运行中的 worker 通常需要被共同调度——在能够建立其通信组之前，所有 worker 都必须启动并持有已分配的 GPU，这类似于本文档站点其他地方讨论的 gang scheduling 需求。GPU node pool 的预置准备时间通常比 CPU 节点更长且更难预测，因此训练 job 的实际启动时间取决于每个请求的 worker 能多快被共同调度。
</details>

## 简答题

9. 说明 Ray Train `Trainer` 和 `ScalingConfig` 分别做什么，以及它们如何协同运行分布式训练 job。

<details>

<summary>显示答案</summary>

**答案：**
Trainer（例如 `TorchTrainer`）包装用户提供的训练函数，该函数包含常规的模型训练逻辑——构建模型、遍历 batch、计算 loss 以及执行 optimizer step。Trainer 负责在底层框架的数据并行训练所需的分布式进程组中，为每个 worker 启动一次该函数（例如 PyTorch DDP 进程组），因此训练函数自身无需手动设置这些协调工作。

`ScalingConfig` 告诉 Trainer 要启动多少个 worker，以及每个 worker 需要哪些资源，例如是否需要 GPU。Trainer 通过 Ray 常规的 task/actor 资源请求机制，使用 `ScalingConfig` 从底层 Ray cluster 请求相应资源。二者结合后，Trainer 提供训练逻辑和协调能力，`ScalingConfig` 提供 Trainer 用于扩展该逻辑的资源形态。
</details>

10. 描述将 Ray Tune 与 Ray Train 结合为何有用，以及该组合的资源请求如何与 EKS 上的 cluster autoscaling 交互。

<details>

<summary>显示答案</summary>

**答案：**
某些模型的训练成本很高，以至于单个超参数 trial 本身也需要分布式（多 GPU 或多节点）训练，才能在合理时间内完成。如果不结合这两个库，团队要么必须针对一个分布式训练 job 串行调优超参数，要么在搜索阶段放弃分布式训练。由于 Ray Tune 可以将 Ray Train `Trainer` 包装为其 trainable，每个 trial 都会成为各自的分布式 Ray Train 运行，而 Tune 可以同时运行多个此类运行，并决定下一步尝试哪些超参数组合。

由于每个 trial 中的每个 worker 仍然通过 Ray 常规的 task/actor 资源请求机制请求 CPU 和 GPU，EKS 上由 KubeRay 管理的 autoscaler 看到的是所有活跃 trial 的组合实时资源需求，而不是单一的预先声明的形态。随着 Tune sweep 启动更多并发 trial，它可以预置更多 worker 节点；随着 trial 完成，它可以缩容，而不必预先按可能的最大 sweep 规模配置 cluster。
</details>

---

[返回学习材料](../../../ai-ml/ray/03-ray-train-tune.md) | [下一测验：Ray Serve](./04-ray-serve-quiz.md)
