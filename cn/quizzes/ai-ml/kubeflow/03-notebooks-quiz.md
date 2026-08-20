# Kubeflow Notebooks 测验

本测验检验你对 Kubeflow Notebooks 架构、其基于 Profile 的多租户模型、存储与空闲清理行为、EKS 上的 GPU 调度以及自定义 notebook 镜像的理解。

## 多项选择题

1. Kubeflow Notebooks 使用哪种 Kubernetes 原生机制，将用户在 spawner 中的选择（镜像、CPU/内存/GPU、存储）转换为运行中的 notebook server？
   - A) 由 dashboard 直接针对 `kubectl` 执行的 shell script
   - B) 由 controller 协调为 StatefulSet/pod 的 `Notebook` custom resource
   - C) 每分钟轮询 dashboard 数据库的 cron job
   - D) 用户手动安装的 Helm chart

<details>

<summary>显示答案</summary>

**答案：B) 由 controller 协调为 StatefulSet/pod 的 `Notebook` custom resource**

**说明：**
Central Dashboard 的 spawner 会创建一个描述所需环境的 `Notebook` custom resource。controller 会监视该 resource，并将其协调为常规 Kubernetes 对象（包含所请求镜像、资源和 PVC 的 StatefulSet/pod），而不是由 dashboard 直接创建 pods。
</details>

2. 截至 Kubeflow Community Distribution 26.03，Kubeflow Notebooks v2 的准确状态是什么？
   - A) 它已经 GA，并且已完全取代 v1
   - B) 它尚不存在，即使是 alpha 版本也没有
   - C) 它正接近发布，围绕新的 `Workspace`/`WorkspaceKind` CRDs 的 alpha manifests 已可用于测试，但尚未 GA
   - D) 它已被取消，转而无限期保留 v1

<details>

<summary>显示答案</summary>

**答案：C) 它正接近发布，围绕新的 `Workspace`/`WorkspaceKind` CRDs 的 alpha manifests 已可用于测试，但尚未 GA**

**说明：**
在 26.03 distribution 发布时，Notebooks v2（围绕新的 `Workspace` 和 `WorkspaceKind` custom resources 构建）已有可供测试的 alpha manifests，但尚未达到 general availability。v1 的 `Notebook` CRD 仍是生产环境中使用的架构，预计将在 v2 准备好 GA 后转为仅维护状态。
</details>

3. 在 Kubeflow Notebooks 的多租户模型中，Profile 是什么？
   - A) 用户保存的 notebook UI 主题和键盘快捷键
   - B) 为每位用户提供 namespace 的构造，它会配置 RBAC bindings 和限定该用户访问范围的 Istio authorization policies
   - C) 记录用户此前启动过哪些镜像的记录
   - D) 与用户 AWS IAM identity 关联的 billing account

<details>

<summary>显示答案</summary>

**答案：B) 为每位用户提供 namespace 的构造，它会配置 RBAC bindings 和限定该用户访问范围的 Istio authorization policies**

**说明：**
Profile 会为用户（或团队）配置专用 namespace、将其权限限定在该 namespace 内的 RBAC bindings，以及限制哪些 identities 能访问其中 services 的 Istio `AuthorizationPolicy`。Notebooks 始终在 Profile namespace 内创建，默认情况下正是它将一个用户的 notebook 与其他用户的 notebook 隔离开来。
</details>

4. notebook 的 PersistentVolumeClaim 对其抵御 pod 重启的能力为何重要？
   - A) 每次 pod 重启时，PVC 都会被自动删除并重新创建
   - B) claim 而非 pod 才是持久对象——从中挂载的文件和已安装 packages 可在 pod 重启、node 替换或停止/启动周期后保留
   - C) PVC 仅对 RStudio 镜像有意义，对 JupyterLab 没有意义
   - D) PVC 仅用于存储 logs，而不用于存储用户文件

<details>

<summary>显示答案</summary>

**答案：B) claim 而非 pod 才是持久对象——从中挂载的文件和已安装 packages 可在 pod 重启、node 替换或停止/启动周期后保留**

**说明：**
spawner 允许用户附加一个 PVC，通常将其挂载到 notebook 的 home directory。由于 PVC 独立于 pod 的生命周期而持续存在，用户的工作可在 pod 重启、node 替换或有意的停止/启动周期后得以保留——而空闲清理会停止但不删除 notebook，因此不会影响 PVC。
</details>

5. 为什么空闲清理对于 GPU-backed notebooks 尤其重要？
   - A) notebook pods 根本无法请求 GPUs，因此清理与它们无关
   - B) 无论是否活跃使用，运行中的 notebook pod 在其存在期间都会一直持有 GPU allocation，因此空闲的 GPU notebook 可能会长时间占用昂贵的 capacity
   - C) 清理会删除 notebook 的 PVC 以释放 GPU memory
   - D) GPU nodes 需要完整的 cluster 重启才能回收 capacity，而清理会触发该重启

<details>

<summary>显示答案</summary>

**答案：B) 无论是否活跃使用，运行中的 notebook pod 在其存在期间都会一直持有 GPU allocation，因此空闲的 GPU notebook 可能会长时间占用昂贵的 capacity**

**说明：**
notebook pod 在运行期间会持续持有其所请求的 CPU、memory 和 GPU allocation，无论是否有人正在积极使用它。空闲清理会在配置的时间段后停止（而不删除）空闲 notebooks；这对 GPU notebooks 尤其有价值，因为空闲的 GPU-backed server 否则可能无限期占用昂贵的 accelerator capacity。
</details>

6. EKS 上的 notebook pod 如何请求 GPU access，这与 cluster autoscaling 如何交互？
   - A) 它使用专用于 Notebooks 的 GPU scheduler，与 cluster 的其余部分相互独立
   - B) 与其他 pod 一样，它设置 `resources.limits."nvidia.com/gpu"`，并与 training jobs 和 inference workloads 竞争相同的 GPU-capable node pools（例如由 Karpenter 管理的 NodePools）
   - C) notebooks 的 GPU access 必须由 administrator 通过 SSH 到 node 手动分配
   - D) Notebook pods 无法请求 GPUs；只有 KServe endpoints 可以

<details>

<summary>显示答案</summary>

**答案：B) 与其他 pod 一样，它设置 `resources.limits."nvidia.com/gpu"`，并与 training jobs 和 inference workloads 竞争相同的 GPU-capable node pools（例如由 Karpenter 管理的 NodePools）**

**说明：**
spawner 中的 GPU 选择会转换为 pod spec 上的标准 `nvidia.com/gpu` resource request，并由 NVIDIA device plugin 作为可分配资源公布。这不是一个独立的 GPU subsystem——notebook pod 会与任何其他 GPU workload 竞争相同的 GPU node pools；在 EKS 上，该 capacity 通常通过 Karpenter 动态配置。
</details>

7. 团队构建自定义 notebook 镜像，而不是直接使用 stock spawner 镜像的典型原因是什么？
   - A) Kubeflow 要求使用自定义镜像，根本不能使用 stock 镜像
   - B) 为每位 data scientist 提供具有预安装团队特定 dependencies 的一致、可复现环境，而不是在运行中的 container 内手动安装 packages
   - C) stock 镜像不支持 PVC mounts
   - D) 自定义镜像可以免除 Profile namespace 的需要

<details>

<summary>显示答案</summary>

**答案：B) 为每位 data scientist 提供具有预安装团队特定 dependencies 的一致、可复现环境，而不是在运行中的 container 内手动安装 packages**

**说明：**
大多数生产团队都会基于上游 Kubeflow/Jupyter base image 构建自定义镜像，在其中分层添加固定版本的 Python/R packages、内部 libraries 以及相匹配的 GPU-framework versions，然后将镜像推送到 registry（例如 EKS 上的 Amazon ECR），并直接从 spawner 引用它。这可确保使用相同镜像 tag 的两位用户获得相同的 package sets，而不是因手动安装而逐渐产生差异。
</details>

## 简答题

8. 请用一两句话说明 notebook pod 的 GPU request 如何在 EKS 上与 Karpenter 交互，以及这为何对 cost 很重要。

<details>

<summary>显示答案</summary>

**答案：**
当 notebook Pod 的 spec 请求 `nvidia.com/gpu` resources，且没有现有 node 具有 capacity 时，Karpenter 会配置一个新的 GPU-backed EC2 instance 来满足 pending Pod；由于 GPU instances 很昂贵，对 notebook GPU requests 进行空闲清理和适当调整大小，会直接决定团队在活跃 sessions 之间为多少未使用的 GPU capacity 付费。
</details>

9. 每 namespace 的 Istio isolation 能为 Kubeflow Profile 提供哪些仅靠普通 Kubernetes namespace RBAC 无法提供的能力？

<details>

<summary>显示答案</summary>

**答案：**
RBAC 控制谁可以在 namespace 中创建/读取/修改 Kubernetes API objects，但并不涉及 network traffic；Istio 每 namespace 的 `AuthorizationPolicy` 还会在 network layer 限制哪些 services 实际可以向用户的 notebook Pod 发送 requests，即使仅靠 RBAC 本来会允许某些 cross-namespace object access，也能在用户的 notebook servers 之间实现隔离。
</details>

---

[返回学习资料](../../../ai-ml/kubeflow/03-notebooks.md)
