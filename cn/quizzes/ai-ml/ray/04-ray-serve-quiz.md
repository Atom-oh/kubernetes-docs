# Ray Serve 测验

本测验用于测试你对 Ray Serve 的 Deployment 模型、Ray Serve LLM、Serve 级自动扩缩容、GPU 推理，以及 RayService 如何在 EKS 上管理生产环境 Serve 应用程序的理解。

## 选择题

1. 在 Ray Serve 的路由层之下，Ray Serve Deployment 是如何实现的？
   - A) 一个与 Ray 核心原语无关的独立容器
   - B) 一个 Ray actor，或一组 actor 副本，Ray Serve 将 HTTP/gRPC 请求路由到它们
   - C) 一个按固定计划运行的 Kubernetes CronJob
   - D) 一个针对每个传入请求重新执行的单个 Ray task

<details>

<summary>显示答案</summary>

**答案：B) 一个 Ray actor，或一组 actor 副本，Ray Serve 将 HTTP/gRPC 请求路由到它们**

**说明：**
Ray Serve 直接构建在 Ray 的 actor 原语之上。一个 Deployment 是一个 actor 或一组 actor 副本，Ray Serve 将传入的 HTTP/gRPC 请求路由到这些副本——因此，模型一旦加载到副本内存中，就可以在无需重新加载的情况下响应许多请求。
</details>

2. 按照 Ray Serve 的术语，“application” 是什么？
   - A) 一个无法扩缩容的单个 Deployment
   - B) 一个或多个组合的 Deployment——例如，预处理 Deployment 向模型推理 Deployment 提供输入——共同组成一个服务流水线
   - C) 一个运行一次后自行销毁的 RayJob
   - D) RayCluster 所在的 Kubernetes namespace

<details>

<summary>显示答案</summary>

**答案：B) 一个或多个组合的 Deployment——例如，预处理 Deployment 向模型推理 Deployment 提供输入——共同组成一个服务流水线**

**说明：**
Ray Serve 允许多个 Deployment 组合成一个名为 application 的服务流水线，例如，预处理步骤将其输出传递给模型推理步骤。该流水线中的每个 Deployment 仍可独立扩缩容、版本化和分配资源。
</details>

3. 什么是 `ray.serve.llm`，它将哪种推理引擎记录为其支持的引擎？
   - A) 一个与 LLM 无关的通用批处理模块；它支持任何引擎
   - B) 一组专用于 LLM 服务的构建块，构建于 Ray Serve 的通用 Deployment 模型之上，并将 vLLM 记录为其支持的推理引擎
   - C) 一个不使用 actor 的 Ray Serve 替代方案
   - D) 一个专用于训练 LLM 而非提供服务的模块

<details>

<summary>显示答案</summary>

**答案：B) 一组专用于 LLM 服务的构建块，构建于 Ray Serve 的通用 Deployment 模型之上，并将 vLLM 记录为其支持的推理引擎**

**说明：**
`ray.serve.llm` 提供了专为 LLM 服务模式定制的高级构造，并分层构建于 Ray Serve 的通用 Deployment 模型之上。它将 vLLM 记录为其支持的推理引擎，并提供与 OpenAI 兼容的 API，该 API 旨在与 vLLM 自身的 OpenAI 兼容服务器紧密对应。
</details>

4. Ray Serve 自己的 autoscaler 会决定什么，又会通过比较什么来做出该决定？
   - A) Karpenter 应预置多少个 EC2 节点，依据是账单数据
   - B) 特定 Deployment 需要多少个 actor 副本，方法是将每个副本的进行中请求数（排队中加执行中）与目标值进行比较
   - C) RayCluster 需要多少个 worker Pod，依据是待处理 task 的放置情况
   - D) 应将 RayCluster 部署到哪个 AWS 区域

<details>

<summary>显示答案</summary>

**答案：B) 特定 Deployment 需要多少个 actor 副本，方法是将每个副本的进行中请求数（排队中加执行中）与目标值进行比较**

**说明：**
Ray Serve 的 autoscaler 是独立于集群级自动扩缩容的一层。它将每个副本的进行中请求数与目标值进行比较，并在配置的最小值和最大值范围内上调或下调该 Deployment 的副本数量。
</details>

5. 在 EKS 上 Ray Serve application 的三层自动扩缩容模型中，哪一层直接位于 Karpenter 之上？
   - A) AWS Load Balancer Controller
   - B) Ray/KubeRay autoscaler，它根据待处理 actor 的放置情况决定 worker Pod 数量
   - C) 一个监控 CPU 使用率的独立 Kubernetes Horizontal Pod Autoscaler
   - D) 发出请求的客户端 application

<details>

<summary>显示答案</summary>

**答案：B) Ray/KubeRay autoscaler，它根据待处理 actor 的放置情况决定 worker Pod 数量**

**说明：**
这三层分别是：Ray Serve 的 autoscaler 决定副本数量；Ray/KubeRay autoscaler 根据待处理 actor 的放置情况（包括 Serve 的 autoscaler 请求的副本）决定 worker Pod 数量；Karpenter 决定运行这些 Pod 所需的节点数量。
</details>

6. 由 GPU 支持的 Ray Serve Deployment 如何请求 GPU？
   - A) 通过 Ray Serve 特有的独立 GPU 预留 API
   - B) 通过 Ray 的常规按 actor 资源请求机制，即 Ray Train 和 Ray Tune worker 使用的同一机制
   - C) 通过手动 SSH 登录 worker 节点并设置环境变量
   - D) Ray Serve Deployment 根本无法请求 GPU

<details>

<summary>显示答案</summary>

**答案：B) 通过 Ray 的常规按 actor 资源请求机制，即 Ray Train 和 Ray Tune worker 使用的同一机制**

**说明：**
需要 GPU 的模型推理 Deployment 通过 Ray Train 和 Ray Tune 所使用的同一 actor 级资源请求机制来请求 GPU，而 worker group 的 Pod spec 会向 Ray scheduler 公布 GPU 容量。
</details>

7. 当 Ray Serve 的 autoscaler 请求一个新的 GPU 副本，但现有的 GPU worker Pod 都没有空间容纳它时，会发生什么？
   - A) 请求会被静默丢弃，且永远不会创建新副本
   - B) 副本请求会变为待处理 Pod，Karpenter 必须先预置一个由 GPU 支持的新的 EC2 节点，该副本才能开始为流量提供服务
   - C) Ray Serve 会自动回退为在 CPU 上运行模型
   - D) Ray autoscaler 完全绕过 Karpenter，自行创建 EC2 实例

<details>

<summary>显示答案</summary>

**答案：B) 副本请求会变为待处理 Pod，Karpenter 必须先预置一个由 GPU 支持的新的 EC2 节点，该副本才能开始为流量提供服务**

**说明：**
Ray Serve 的自动扩缩容与 Karpenter 的节点预置所需时间的交互方式，与其他 GPU 工作负载相同：待处理 Pod 会触发 Karpenter 预置匹配的节点；激进扩缩 GPU 副本的服务 application 应将该准备时间考虑在内。
</details>

8. RayService CRD 在生产环境中管理什么，以及它具体支持哪项能力？
   - A) 仅管理 Serve application，与底层 RayCluster 无关
   - B) 同时管理底层 RayCluster 及部署在其上的 Serve application，并支持零停机滚动升级
   - C) 仅管理运行一次后销毁的批处理作业，不具备服务能力
   - D) 一个无法升级的静态且不可更改的 Ray cluster 快照

<details>

<summary>显示答案</summary>

**答案：B) 同时管理底层 RayCluster 及部署在其上的 Serve application，并支持零停机滚动升级**

**说明：**
RayService 将 RayCluster 及其 Serve application 作为一个整体进行管理，并且该资源支持零停机滚动升级，从而可在不丢弃执行中请求的情况下推出新 application 版本或 RayCluster spec——在生产环境依赖此升级路径之前，请查看当前 KubeRay 发布说明以了解其成熟度。
</details>

## 简答题

9. 解释为什么 Ray Serve 的 autoscaler 和 Ray/KubeRay autoscaler 被描述为独立层，并且它们“只能看到紧邻的下一层”。

<details>

<summary>显示答案</summary>

**答案：**
Ray Serve 的 autoscaler 仅根据请求负载决定特定 Deployment 需要多少个 actor 副本；它无法得知新副本是部署在现有 worker Pod 上，还是需要新的 worker Pod。下一层的 Ray/KubeRay autoscaler 只会响应待处理 actor 的放置情况（包括 Serve 的 autoscaler 所请求的副本）来决定 worker Pod 数量，而不了解任何请求级指标。再下一层的 Karpenter 只会响应待处理 Pod 来决定节点数量。

**说明：**
每个控制循环回答的问题都比其上一层更狭窄，各层仅通过每层产生的常规状态间接通信——副本请求变为待处理 Pod，待处理 Pod 变为待处理节点——而非通过直接协调。
</details>

10. 一个团队正在将一个两步 Ray Serve application（预处理，然后是由 GPU 支持的模型推理）部署到 EKS 的生产环境。请描述本文档中所述的 Deployment 拓扑、自动扩缩容和生命周期管理如何共同适用于该 application。

<details>

<summary>显示答案</summary>

**答案：**
该 application 由两个 Deployment 组成——一个预处理 Deployment 和一个模型推理 Deployment——每个 Deployment 都实现为 actor 副本，预处理 Deployment 的输出会传递给推理 Deployment。每个 Deployment 都基于自身的请求负载，通过 Ray Serve 的 autoscaler 独立自动扩缩自身的副本数量。推理 Deployment 的 actor 副本通过 Ray 的常规按 actor 资源机制请求 GPU；如果 Ray Serve 的 autoscaler 所需的 GPU 副本数量超过现有 worker Pod 可容纳的数量，Ray/KubeRay autoscaler 就会请求更多 worker Pod，Karpenter 则预置匹配的由 GPU 支持的 EC2 节点。在生产环境中，`RayService` 对象会共同管理整个 application 的 RayCluster 和 Serve 发布流程，包括 application 或集群 spec 变更时的零停机升级。

**说明：**
这将文档中的所有概念关联起来：基于 actor 的 Deployment/application 模型、Serve 自身的自动扩缩容层、与 Ray/KubeRay 和 Karpenter 构成的三层自动扩缩容划分、GPU 资源请求，以及作为整个生产生命周期管理器的 RayService。
</details>

---

[返回学习材料](../../../ai-ml/ray/04-ray-serve.md)
