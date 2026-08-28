# 第 6 部分：KServe — Kubernetes 上的模型服务测验

本测验旨在检验你对 KServe 与 Kubeflow 的关系、`InferenceService` 组件、Serverless 与 Raw Deployment 的权衡、自动扩缩容机制、金丝雀发布以及 EKS 上 GPU 推理的理解。

## 选择题

1. KServe 与 Kubeflow 的历史关系是什么？
   - A) KServe 一直是一个完全独立的项目，与 Kubeflow 没有任何关联
   - B) KServe 最初以 KFServing 的形式诞生于 Kubeflow 中，之后独立成为自己的顶级项目
   - C) Kubeflow 是 KServe 的子组件
   - D) KServe 是 Katib 的重新品牌化名称

<details>
<summary>显示答案</summary>

**答案：B) KServe 最初以 KFServing 的形式诞生于 Kubeflow 中，之后独立成为自己的顶级项目**

**说明：**
KServe 最初名为 KFServing，是 Kubeflow 中负责将训练好的模型转变为推理端点的组件。后来它成为一个独立的项目，可以在不安装 Kubeflow 的情况下安装到任何 Kubernetes 集群上；Kubeflow 则继续将它作为默认的模型服务层进行捆绑。
</details>

2. 为什么不能假定 KServe controller/CRD 的版本与 Kubeflow dashboard 中显示的 KServe web app 版本一致？
   - A) Kubeflow dashboard 从不显示任何 KServe 版本信息
   - B) KServe 有独立于 Kubeflow Community Distribution 按日历版本发布节奏的发布周期，因此平台团队可以独立于 web app 升级 controller
   - C) KServe 已被弃用，不再接收版本更新
   - D) Kubeflow web app 与 KServe controller 始终是完全相同的二进制文件

<details>
<summary>显示答案</summary>

**答案：B) KServe 有独立于 Kubeflow Community Distribution 按日历版本发布节奏的发布周期，因此平台团队可以独立于 web app 升级 controller**

**说明：**
Kubeflow Community Distribution 26.03 捆绑的 KServe web app 版本为 v0.16.1，但该版本号描述的是 dashboard 集成，而不一定是集群中运行的底层 KServe controller/CRD 版本，因为 controller 可以按自己的计划进行升级。
</details>

3. 哪个 `InferenceService` 组件是必需的，其他组件则是可选的？
   - A) Explainer
   - B) Transformer
   - C) Predictor
   - D) 三者都是必需的

<details>
<summary>显示答案</summary>

**答案：C) Predictor**

**说明：**
predictor 是模型服务器本身，也是 `InferenceService` 唯一必需的组件。transformer（预处理/后处理）和 explainer（模型解释）均为可选附加组件，仅在用例需要时使用。
</details>

4. KServe 的 Serverless 部署模式的定义性能力是什么，其代价又是什么？
   - A) 它使用普通的 Deployment 和 HPA，且完全没有任何权衡
   - B) 它在空闲时通过 Knative 将 pod 扩缩容至零，代价是在扩容时产生冷启动延迟
   - C) 它完全不需要 Kubernetes 集群
   - D) 它消除了对 predictor 的需求

<details>
<summary>显示答案</summary>

**答案：B) 它在空闲时通过 Knative 将 pod 扩缩容至零，代价是在扩容时产生冷启动延迟**

**说明：**
Serverless 模式将 pod 生命周期委托给 Knative Serving。当没有流量时，它可以将 predictor（以及 transformer/explainer）pod 一直缩容至零，从而节省空闲 GPU 成本。其权衡是冷启动延迟：调度新 pod、启动容器和加载模型工件都需要时间，因此从零扩容后的第一个请求需要等待才能得到响应。
</details>

5. Raw Deployment 模式与 Serverless 模式的关键差异是什么？
   - A) Raw Deployment 模式管理普通的 Deployment/Service（以及可选的 HPA），不依赖 Knative，也不支持扩缩容至零
   - B) Raw Deployment 模式需要 Knative Serving，但会自动添加 transformer
   - C) Raw Deployment 模式仅适用于 SKLearn 模型
   - D) Raw Deployment 模式运行的副本数始终多于 Serverless 模式

<details>
<summary>显示答案</summary>

**答案：A) Raw Deployment 模式管理普通的 Deployment/Service（以及可选的 HPA），不依赖 Knative，也不支持扩缩容至零**

**说明：**
Raw Deployment 模式在运维上更简单（无需安装或升级 Knative），并且完全避免冷启动；但它永远不会缩容到低于 Deployment 配置的最小副本数。因此，无论是否有流量，至少都会运行相应数量的 predictor pod（以及其中的 GPU，如有）。
</details>

6. 两种部署模式的自动扩缩容有何不同？
   - A) 两种模式都使用完全相同的基于 HPA 的 CPU 扩缩容
   - B) Serverless 模式根据 Knative 基于并发数/RPS 的信号扩缩容；Raw Deployment 模式使用基于 CPU/内存或自定义指标的标准 HPA 进行扩缩容
   - C) Serverless 模式完全不会扩缩容
   - D) Raw Deployment 模式基于 Knative 并发数扩缩容，而 Serverless 模式使用 HPA

<details>
<summary>显示答案</summary>

**答案：B) Serverless 模式根据 Knative 基于并发数/RPS 的信号扩缩容；Raw Deployment 模式使用基于 CPU/内存或自定义指标的标准 HPA 进行扩缩容**

**说明：**
Serverless 模式中的 Knative autoscaler 会对并发数或每秒请求数等请求级信号作出响应，相较于资源利用率信号，它通常能更快地响应突发性推理流量。Raw Deployment 模式则依赖标准 Kubernetes HorizontalPodAutoscaler，这与集群中其他 Deployment 使用的自动扩缩容模型相同。
</details>

7. KServe 内置的金丝雀发布机制与本文档其他部分介绍的 Istio/Argo Rollouts 流量拆分模式有什么关系？
   - A) 它们是完全相同的机制，只是名称不同
   - B) KServe 的金丝雀发布是内置于 KServe control plane 的、专用于模型服务的独立机制，与 service mesh 或渐进式交付 controller 的流量拆分不同
   - C) KServe 没有金丝雀发布能力，必须改用 Argo Rollouts
   - D) Istio 流量拆分取代了对 InferenceService 的全部需求

<details>
<summary>显示答案</summary>

**答案：B) KServe 的金丝雀发布是内置于 KServe control plane 的、专用于模型服务的独立机制，与 service mesh 或渐进式交付 controller 的流量拆分不同**

**说明：**
KServe 可以在稳定版和金丝雀版 `InferenceService` 修订版本之间自行拆分流量，并随着信心提高逐步迁移流量。这项机制专门在 `InferenceService` 修订版本层级上运行，与平台中用于其他工作负载的基于 Istio 或 Argo Rollouts 的流量拆分模式是不同的工具——不是替代要求，而是一条独立的、专用于模型服务的路径。
</details>

8. 当某个 `InferenceService` predictor 在 EKS 上请求 GPU 时，Karpenter 扮演什么角色？
   - A) Karpenter 配置 KServe predictor 的推理协议
   - B) 当 pod 的 GPU 请求无法由现有 node 满足时，Karpenter 预置匹配的 GPU 支持 EC2 instance，并可在不再需要这些容量时进行整合/回收
   - C) Karpenter 取代了对 GPU device plugin 的需求
   - D) Karpenter 仅适用于 Raw Deployment 模式，绝不适用于 Serverless 模式

<details>
<summary>显示答案</summary>

**答案：B) 当 pod 的 GPU 请求无法由现有 node 满足时，Karpenter 预置匹配的 GPU 支持 EC2 instance，并可在不再需要这些容量时进行整合/回收**

**说明：**
EKS 上的 GPU 推理遵循针对 GPU device plugin 所公布资源的标准 Kubernetes 资源请求模型；Karpenter 的 GPU node pool 会响应无法调度的 GPU 请求，预置匹配的容量；当 predictor（尤其是在 Serverless 模式中缩容至零的 predictor）不再需要该容量时，其整合行为可以回收这些容量——这也是 EKS 上其他场景所使用的双层自动扩缩容模式。
</details>

## 简答题

9. 请用一到两句话说明：为什么选择 Serverless 模式适合推理流量呈突发、间歇性特征的模型，却不适合要求每个请求都保持稳定低延迟的模型。

<details>
<summary>显示答案</summary>

**答案：Serverless 模式的扩缩容至零可以在空闲期间节省 GPU 成本，适用于模型大部分时间处于空闲状态的突发/间歇性流量。但从零重新扩容会产生冷启动延迟（pod 调度、容器启动、模型加载），对于要求每一个请求都保持稳定低延迟的工作负载而言，这是不可接受的。**

**说明：**
这项权衡的本质是成本（节省空闲 GPU）与延迟可预测性（没有冷启动）之间的取舍。Raw Deployment 模式通过始终保持最小副本数处于就绪状态，反转了这一权衡，但即使在空闲时也需要为该容量付费。
</details>

10. 在 KServe 中，predictor 的内置框架支持与自定义容器 predictor 有什么区别？

<details>
<summary>显示答案</summary>

**答案：内置 predictor server（例如用于 SKLearn、XGBoost、通过 TorchServe 使用 PyTorch，或 NVIDIA Triton）允许 predictor spec 只需指向模型工件位置，即可获得可工作的服务器，而无需编写服务代码。自定义容器 predictor 用于这些内置框架以外的任何情况，并且其自身必须实现 KServe 的推理协议。**

**说明：**
这种区别决定了所需的服务端实现工作量：内置 server 开箱即用地支持常见框架，其他任何情况都需要手写一个能够使用 KServe 协议通信的容器。
</details>

11. 说明 KServe 自身的扩缩容决策与 Karpenter 对这些决策的响应之间的双层自动扩缩容关系。

<details>
<summary>显示答案</summary>

**答案：KServe（在 Serverless 模式中通过 Knative，或在 Raw Deployment 模式中通过 HPA）根据请求级或资源利用率信号决定需要多少 predictor pod——这是不了解 node 的 pod 级决策。Karpenter 则对由此产生的 pod 调度状态（无法调度的 GPU 请求或空的 GPU node）作出独立响应，以决定要预置或回收多少 EC2 GPU 容量——这是不了解这些 pod 存在原因的 node 级决策。**

**说明：**
这是两个独立的控制循环，仅通过 pod 数量/调度状态相互关联——与本文档其他部分中 EKS 上其他自动扩缩容工作负载使用的一般双层自动扩缩容模式相同（先作出 job/pod 级决策，再由 node 级决策对其作出响应）。
</details>

---

[返回学习材料](../../../ai-ml/kubeflow/06-kserve.md)
