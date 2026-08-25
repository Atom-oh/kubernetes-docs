# Ray 架构测验

本测验检验你对 Ray 核心原语（task、actor、object store）、Ray 集群架构（head node、worker node），以及 Ray 的高层库如何构建在同一基础之上的理解。

## 单项选择题

1. 从根本上说，Ray 是什么？
   - A) 一个仅为分布式模型训练构建的特定领域框架
   - B) 一个用于扩展 Python 工作负载的开源分布式计算框架，围绕一组少量的通用原语构建
   - C) 一个替代默认 kube-scheduler 的 Kubernetes 原生调度器
   - D) 一个没有编程 API 的托管模型服务产品

<details>

<summary>显示答案</summary>

**答案：B) 一个用于扩展 Python 工作负载的开源分布式计算框架，围绕一组少量的通用原语构建**

**说明：**
Ray 并非为某一种工作负载类型而构建。它提供通用原语——task、actor 和 object store——支持从临时并行 task 到分布式训练、超参数调优和模型服务等各种用例。
</details>

2. 什么是 Ray task？
   - A) 通过将 `@ray.remote` 应用于 class 而创建的有状态、长生命周期远程对象
   - B) 通过将 `@ray.remote` 应用于 function 而创建、由 Ray 远程运行的无状态函数
   - C) 在 head node 上管理集群元数据的进程
   - D) 分布式 object store 的一个分片

<details>

<summary>显示答案</summary>

**答案：B) 通过将 `@ray.remote` 应用于 function 而创建、由 Ray 远程运行的无状态函数**

**说明：**
task 是无状态的远程函数。调用它会立即返回一个 future，而 Ray 会在某个具有可用容量的 worker 上调度实际执行。由于 task 不会在调用之间保留状态，Ray 可以在任何有容量的 worker 上运行任意一次调用。
</details>

3. actor 与 task 的区别是什么？
   - A) actor 是无状态的，而 task 会在调用之间保留状态
   - B) actor 是从 class 创建的长生命周期、有状态远程实例，其状态会在 method 调用之间持续保留
   - C) actor 只能在 head node 上运行
   - D) actor 无法使用 `@ray.remote` decorator 创建

<details>

<summary>显示答案</summary>

**答案：B) actor 是从 class 创建的长生命周期、有状态远程实例，其状态会在 method 调用之间持续保留**

**说明：**
将 `@ray.remote` 应用于 class 会将其转换为 actor。Ray 会将生成的实例作为长生命周期的远程进程保持运行，因此其中存储的状态——例如已加载的模型权重或计数器——会在 method 调用之间持续保留，这与无状态 task 不同。
</details>

4. Ray 的分布式 object store 主要解决什么问题？
   - A) 它取代 Ray 集群中 head node 的需要
   - B) 它允许从共享内存读取大型对象，而不是将其重新序列化到每个需要它的进程中，从而避免不必要的复制
   - C) 它存储集群的 autoscaler 配置
   - D) 它将 task 调度到特定 worker node 上

<details>

<summary>显示答案</summary>

**答案：B) 它允许从共享内存读取大型对象，而不是将其重新序列化到每个需要它的进程中，从而避免不必要的复制**

**说明：**
object store 是用于在 task 和 actor 之间传递对象的分布式共享内存存储。对于 dataset 或模型权重等大型对象，这避免了将对象复制到每个需要它的进程中所产生的序列化和复制成本。
</details>

5. 除了 worker node 上运行的内容外，Ray 集群的 head node 上还运行什么？
   - A) 仅分布式 object store
   - B) Global Control Store (GCS)、driver process（如果在那里运行）和 autoscaler
   - C) 仅用户提交的 task 和 actor
   - D) 独立的 Kubernetes control plane

<details>

<summary>显示答案</summary>

**答案：B) Global Control Store (GCS)、driver process（如果在那里运行）和 autoscaler**

**说明：**
head node 运行 GCS（集群元数据）、driver process（如果顶层脚本或会话在那里运行）和 autoscaler；此外，它还像 worker node 一样，为资源池贡献 CPU/GPU/memory。
</details>

6. Ray 如何在集群中调度 task 和 actor？
   - A) 针对每个 node 的资源单独进行调度，要求用户为每个 task 选择特定 node
   - B) 针对集群合并后的资源池进行调度，因此 task 可以落在任何拥有足够空闲资源的 node 上
   - C) 仅在 head node 上运行，worker node 仅用于存储
   - D) 随机调度，不考虑可用的 CPU、GPU 或 memory

<details>

<summary>显示答案</summary>

**答案：B) 针对集群合并后的资源池进行调度，因此 task 可以落在任何拥有足够空闲资源的 node 上**

**说明：**
Ray 针对整个集群的资源池而不是单个 node 进行工作调度。请求给定 CPU 数量的 task 可以在集群中任何具有该空闲容量的 node 上运行。
</details>

7. 在架构上，Ray Train、Ray Tune 和 Ray Serve 有什么共同点？
   - A) 每个都实现了自己的独立调度和容错系统，不依赖 Ray 核心
   - B) 它们都构建在与 Ray 核心原语相同的底层 task、actor 和 object store 之上
   - C) 它们只能在 Ray 集群外运行
   - D) 它们取代了 head node 的需要

<details>

<summary>显示答案</summary>

**答案：B) 它们都构建在与 Ray 核心原语相同的底层 task、actor 和 object store 之上**

**说明：**
Ray 用于训练、调优和服务的高层库复用相同的原语，而不是为每种工作负载分别重新实现调度和数据移动。这一共享基础是 Ray 与将互不相关的点工具捆绑在一起的模式相比的关键架构区别。
</details>

8. 为什么在 Kubernetes 上运行 Ray 需要 Ray 自身集群概念之外的机制？
   - A) 因为 Ray 无法在 container 内运行
   - B) 因为 Ray 的 head/worker 集群形态与 Kubernetes 自己的调度处于不同层级，所以需要某种机制将该形态转换为 Pods 和 Deployments 等 Kubernetes 对象
   - C) 因为 Kubernetes 不支持 autoscaling
   - D) 因为 Ray task 无法使用 Kubernetes node 上的 CPU 资源

<details>

<summary>显示答案</summary>

**答案：B) 因为 Ray 的 head/worker 集群形态与 Kubernetes 自己的调度处于不同层级，所以需要某种机制将该形态转换为 Pods 和 Deployments 等 Kubernetes 对象**

**说明：**
Ray 自身的集群概念（head node、worker node、autoscaler）不会自动映射到 Kubernetes 的调度模型。必须有某种机制将 Ray 集群的形态转换为 Kubernetes scheduler 能够理解的 Pods 和 Deployments——这项转换正是 KubeRay 提供的功能。
</details>

## 简答题

9. 一位团队成员正在决定将一段逻辑实现为 Ray task 还是 Ray actor。他们需要让一个 machine learning model 在内存中保持加载状态，以处理许多传入请求，而不是每次都重新加载。应该使用哪个原语，为什么？

<details>

<summary>显示答案</summary>

**答案：应使用 actor，因为它是长生命周期、有状态的远程实例——已加载的 model 可以保存在 actor 的状态中，并在多次 method 调用之间复用，而不是像无状态 task 那样需要在每次调用时重新加载。**

**说明：**
task 是无状态的，并在完成一次调用后结束；task 没有可以在调用之间保留已加载 model 的位置。actor 的实例作为远程进程保持运行，因此通过 actor handle 发起调用时，已加载的模型权重等状态会持续保留。
</details>

10. 为什么 Ray 在其核心原语中一次性实现调度、容错和数据移动，而不是在每个高层库（Train、Tune、Serve）中分别实现一次？

<details>

<summary>显示答案</summary>

**答案：因为 Ray Train、Ray Tune 和 Ray Serve 都构建在相同的 task、actor 和 object store 之上，所以每个库都复用这项共享实现，而不是针对自己的工作负载分别重新实现调度和数据移动。**

**说明：**
这一共享基础是 Ray 与由多个独立点工具组成的生态系统相比的关键架构区别；后者的每个工具都有自己的执行模型，只是恰好被捆绑在一起。分布式训练运行和超参数扫描在底层都是以 Ray actor 或 task 形式运行的 worker，通过相同的 object store 交换数据。
</details>

---

[返回学习材料](../../../ai-ml/ray/01-architecture.md) | [下一测验：KubeRay Operator](./02-kuberay-operator-quiz.md)
