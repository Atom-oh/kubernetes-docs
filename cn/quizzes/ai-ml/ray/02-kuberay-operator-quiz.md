# KubeRay Operator 测验

本测验检验你对 KubeRay 的理解：它是什么、它的三个核心 CRD、它与 Karpenter 共享的双层自动扩缩容模型，以及它如何处理 GPU 调度。

## 选择题

1. KubeRay 是什么？
   - A) 用于运行 Ray 集群的托管 AWS 服务
   - B) 一个 Kubernetes operator，将 Ray 集群作为原生 Kubernetes 自定义资源进行管理，并将 head/worker-node 结构转换为 Pods、Services 和相关对象
   - C) 用于替代 kubectl 的 Ray 专用工具
   - D) 一个用于 Ray 集群的监控仪表板，不具备集群管理能力

<details>

<summary>显示答案</summary>

**答案：B) 一个 Kubernetes operator，将 Ray 集群作为原生 Kubernetes 自定义资源进行管理，并将 head/worker-node 结构转换为 Pods、Services 和相关对象**

**说明：**
KubeRay 使“Ray on Kubernetes”成为声明式配置，而不再需要手动编写 Pod spec：它将声明的 RayCluster/RayJob/RayService spec 协调为 Kubernetes 所需的实际 Pods、Services 和其他对象。
</details>

2. 哪个 CRD 表示由一个 head Pod 和一个或多个 worker group 组成的原始 Ray 集群？
   - A) RayJob
   - B) RayService
   - C) RayCluster
   - D) RayNodePool

<details>

<summary>显示答案</summary>

**答案：C) RayCluster**

**说明：**
RayCluster 是基础 CRD：一个 head Pod 加上一个或多个 worker group，每个 worker group 都是一组同构的 worker Pods（例如，一个 CPU worker group 和一个独立的 GPU worker group），由 operator 协调以匹配所需 spec。
</details>

3. 为什么 RayJob 很适合一次性或计划执行的批处理工作负载？
   - A) 它只能在预先存在且永久运行的 RayCluster 上运行
   - B) 它可以创建 RayCluster、运行所提交的作业，并在作业完成后拆除集群，因此无需让集群在两次运行之间保持空闲
   - C) 它会完全禁用 Ray autoscaler
   - D) 它要求先运行一个独立的 RayService

<details>

<summary>显示答案</summary>

**答案：B) 它可以创建 RayCluster、运行所提交的作业，并在作业完成后拆除集群，因此无需让集群在两次运行之间保持空闲**

**说明：**
RayJob 提交一个批处理作业，并且可以选择管理底层集群的完整生命周期——创建、作业执行和拆除——从而避免在两次运行之间为闲置集群付费。
</details>

4. RayService 与 RayCluster 有何区别？
   - A) RayService 无法运行任何 Ray Serve 应用程序
   - B) RayService 管理一个 RayCluster 及其上层的 Ray Serve 应用程序，并支持零停机滚动升级
   - C) RayService 只能在单个 Pod 上运行，且没有 worker group
   - D) RayService 已弃用，推荐使用 RayCluster

<details>

<summary>显示答案</summary>

**答案：B) RayService 管理一个 RayCluster 及其上层的 Ray Serve 应用程序，并支持零停机滚动升级**

**说明：**
RayService 面向生产环境模型服务：它同时管理 RayCluster 和部署在其上的 Ray Serve 应用程序，并支持旨在实现零停机的滚动升级——在生产环境依赖该升级路径前，请查阅当前 KubeRay release notes 以确认其成熟度。
</details>

5. 在本文档所述的 Ray on EKS 双层自动扩缩容模式中，Ray autoscaler 决定什么，Karpenter 又决定什么？
   - A) Ray autoscaler 决定 EC2 节点类型；Karpenter 决定 Ray task 放置位置
   - B) Ray autoscaler 决定需要多少 Ray worker Pods（通过调整 RayCluster worker group replica count）；Karpenter 决定为由此产生的 pending Pods 配置多少 EC2 节点
   - C) 两个控制循环为实现容错而冗余地决定相同事项
   - D) Karpenter 决定 Pod 数量；Ray autoscaler 决定节点数量

<details>

<summary>显示答案</summary>

**答案：B) Ray autoscaler 决定需要多少 Ray worker Pods（通过调整 RayCluster worker group replica count）；Karpenter 决定为由此产生的 pending Pods 配置多少 EC2 节点**

**说明：**
一个控制循环（通过 KubeRay 协调的 Ray autoscaler）负责 Pod 数量；另一个控制循环（Karpenter 或 Kubernetes Cluster Autoscaler）负责节点数量。它们仅通过普通的 pending-Pod 调度状态间接通信——这与本文档站点为 Flink 和 Katib 描述的双层模式相同。
</details>

6. Ray autoscaler 的 `idleTimeoutSeconds` 设置控制什么？其默认值是多少？
   - A) KubeRay operator 在安装 CRD 前等待的时长；默认 60 秒
   - B) worker Pod 在没有 tasks、actors 或被引用对象的情况下必须保持空闲多久，autoscaler 才会将其缩容；默认 60 秒
   - C) Karpenter 在配置新的 EC2 节点前等待的时长；默认 60 秒
   - D) 已完成 RayJob 的 head Pod 的 TTL；默认 60 秒

<details>

<summary>显示答案</summary>

**答案：B) worker Pod 在没有 tasks、actors 或被引用对象的情况下必须保持空闲多久，autoscaler 才会将其缩容；默认 60 秒**

**说明：**
`idleTimeoutSeconds` 的默认值为 60 秒，是 Ray autoscaler 在缩容空闲 worker Pod 前应用的等待时长。
</details>

7. KubeRay 如何确定一个 worker group 的 Ray processes 可见的 GPU 数量？
   - A) 它读取 RayCluster spec 顶层 metadata 中单独的 `numGPUs` 字段
   - B) 它读取在 worker group 的 Pod spec 中设置的 GPU resource limit（例如 `nvidia.com/gpu`），将其公布给 Ray scheduler 和 autoscaler，并自动将 Ray process 的 `--num-gpus` flag 设置为匹配值
   - C) Pods 启动后，必须使用单独的 `kubectl ray gpu-config` 命令手动设置 GPU 数量
   - D) 无论 Pod spec 如何，KubeRay 始终假定每个 worker Pod 恰好有一个 GPU

<details>

<summary>显示答案</summary>

**答案：B) 它读取在 worker group 的 Pod spec 中设置的 GPU resource limit（例如 `nvidia.com/gpu`），将其公布给 Ray scheduler 和 autoscaler，并自动将 Ray process 的 `--num-gpus` flag 设置为匹配值**

**说明：**
GPU worker group 的 Pod spec 是唯一事实来源：KubeRay 将容器的 GPU resource limits 公布给 Ray scheduler 和 autoscaler，并将 Ray process 的 `--num-gpus` 配置为匹配值，因此无需另行手动维护同步的 GPU 数量。
</details>

8. 根据本文档，安装 KubeRay operator 的标准方法是什么？
   - A) 手动应用从随机 GitHub gist 下载的原始 manifests
   - B) 官方 Helm chart，通过 `helm repo add kuberay https://ray-project.github.io/kuberay-helm/` 添加
   - C) 一行 `kubectl create clusterrole kuberay` 命令
   - D) 没有受支持的安装方法；KubeRay 必须从源代码构建

<details>

<summary>显示答案</summary>

**答案：B) 官方 Helm chart，通过 `helm repo add kuberay https://ray-project.github.io/kuberay-helm/` 添加**

**说明：**
`ray-project/kuberay-helm` repository 托管用于安装 KubeRay operator、其 controller 以及 RayCluster/RayJob/RayService CRD 的官方 Helm chart。
</details>

## 简答题

9. 请列出 KubeRay 提供的三个核心 CRD，并简要说明每个 CRD 的用途。

<details>

<summary>显示答案</summary>

**答案：**
- RayCluster：由一个 head Pod 和一个或多个 worker group 组成的原始 Ray 集群，会被协调以匹配声明的 spec。
- RayJob：向 Ray 集群提交批处理作业，并可选择管理该集群完整的创建、运行和拆除生命周期，适用于一次性或计划执行的工作负载。
- RayService：管理一个 RayCluster 及其上层的 Ray Serve 应用程序，用于生产环境模型服务，并支持零停机滚动升级。

**说明：**
每个 CRD 面向不同的使用模式——原始集群管理、批处理作业执行和生产环境服务——但都构建在相同的底层协调模型之上。
</details>

10. 请说明为什么 Ray-on-EKS 自动扩缩容需要两个独立的控制循环而不是一个，以及每个循环各自负责什么。

<details>

<summary>显示答案</summary>

**答案：**
Ray autoscaler 了解 Ray 层面的状态（pending tasks 和 actors），但不了解 EC2 capacity；Karpenter 了解 Kubernetes 层面的 pending Pods 和 EC2 provisioning，但不了解 Ray tasks 或 actors。Ray autoscaler 决定需要多少 Ray worker Pods，并通过 RayCluster worker group replica count 请求这些 Pods；Karpenter 则独立响应由此产生的 pending Pods，并配置匹配的 EC2 节点来运行它们。

**说明：**
两个循环都不能替代另一个，因为每个循环都基于另一个循环不具备的信息运行。这种双层分工——一个循环负责 Pod 数量，另一个负责节点数量，仅通过普通 Kubernetes 调度状态通信——与本文档站点用于描述 Flink 和 Katib 自动扩缩容的模式相同。
</details>

---

[返回学习资料](../../../ai-ml/ray/02-kuberay-operator.md) | [下一测验：Ray Train and Tune](./03-ray-train-tune-quiz.md)
