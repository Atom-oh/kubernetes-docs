# Kubernetes 调度、抢占与驱逐

> **支持的版本**：Kubernetes 1.34 - 1.36（Descheduler v0.36 示例）
> **最后更新**：September 17, 2026

在 Kubernetes 中，调度是将 Pod 放置到合适节点的过程。抢占是移除较低优先级 Pod 以便为较高优先级 Pod 腾出空间的过程；驱逐会终止一个 Pod，其工作负载控制器可能会创建由调度器单独放置的替代 Pod。本章将学习 Kubernetes 调度机制、节点选择、抢占、驱逐，以及 Amazon EKS 中的调度优化方法。

## 实验环境设置

要跟随本文档中的示例，你需要以下工具和环境：

### 必需工具
- 与 API server 相差不超过一个次要版本的 kubectl
- 可正常运行的 Kubernetes 集群（EKS、minikube、kind 等）
- 具有多个节点的集群（用于调度测试）

### 调度示例设置

```bash
# Create namespace
kubectl create namespace scheduling-demo

# Add labels to nodes (if you have multiple nodes)
kubectl label nodes <node-name> disktype=ssd
kubectl label nodes <node-name> gpu=true

# Create a pod using node affinity
kubectl -n scheduling-demo apply -f - <<EOF
apiVersion: v1
kind: Pod
metadata:
  name: nginx-ssd
  labels:
    app: nginx
spec:
  affinity:
    nodeAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
        nodeSelectorTerms:
        - matchExpressions:
          - key: disktype
            operator: In
            values:
            - ssd
  containers:
  - name: nginx
    image: nginx
EOF

# Create priority class
kubectl apply -f - <<EOF
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: high-priority
value: 1000000
globalDefault: false
description: "This priority class should be used for critical service pods only."
EOF

# Create Pod Disruption Budget (PDB)
kubectl -n scheduling-demo apply -f - <<EOF
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: nginx-pdb
spec:
  minAvailable: 1
  selector:
    matchLabels:
      app: nginx
EOF
```

## Kubernetes 调度架构

![Kubernetes 调度架构：kube-scheduler 依次让 Pod 经过排队、过滤、评分和绑定，受放置策略约束；基于优先级的抢占和驱逐会反馈到该流水线中。](../.gitbook/assets/en-core-08-scheduling-preemption-eviction-0.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-core-08-scheduling-preemption-eviction-0.html)

## 调度概念对比

| 概念 | 目的 | 使用场景 | Kubernetes 版本 |
|---------|---------|-----------|-------------------|
| **Node Selector** | 将 Pod 放置到具有特定标签的节点上 | 简单节点选择 | 所有版本 |
| **Node Affinity** | 定义复杂的节点选择规则 | 高级节点选择 | 1.6+ |
| **Pod Affinity** | 将 Pod 放置在其他 Pod 附近 | 将相关 Service 共置 | 1.6+ |
| **Pod Anti-Affinity** | 将 Pod 放置在远离其他 Pod 的位置 | 确保高可用性 | 1.6+ |
| **Taints and Tolerations** | 仅允许特定 Pod 使用节点 | 专用节点、节点隔离 | 1.6+ |
| **Topology Spread Constraints** | 将 Pod 分散到拓扑域中 | 跨可用区分布 | 1.16+（在 1.19 中 GA） |
| **Priority and Preemption** | 对重要工作负载确定优先级 | 关键 Service 保障 | 1.8+（在 1.11 中 GA） |
| **Pod Disruption Budget** | 限制同时受干扰的 Pod | 确保高可用性 | 1.4+（在 1.21 中 GA） |

## 基本调度概念

> **关键概念**：Kubernetes 调度器是一个 control plane 组件，负责选择运行 Pod 的最优节点，分为过滤和评分两个阶段运行。

### 调度过程

1. **过滤阶段（Predicates）**
   - 识别可以运行该 Pod 的合适节点集合
   - 考虑资源需求、节点选择器、亲和性规则、污点/容忍等
   - 如果任一条件不满足，则排除该节点

2. **评分阶段（Priorities）**
   - 为通过过滤的节点分配分数
   - 考虑资源利用率、Pod 分布、亲和性偏好等
   - 选择分数最高的节点

3. **绑定阶段**
   - 将 Pod 分配给选定节点
   - 将绑定信息更新到 API server

## 目录
1. [调度概览](#scheduling-overview)
2. [调度器的工作方式](#how-the-scheduler-works)
3. [节点选择](#node-selection)
4. [Pod 亲和性与反亲和性](#pod-affinity-and-anti-affinity)
5. [污点与容忍](#taints-and-tolerations)
6. [节点亲和性](#node-affinity)
7. [Pod 优先级与抢占](#pod-priority-and-preemption)
8. [Pod 驱逐](#pod-eviction)
9. [Pod Disruption Budget (PDB)](#pod-disruption-budget-pdb)
10. [节点压力驱逐](#node-pressure-eviction)
11. [TopologySpreadConstraints](#topologyspreadconstraints)
12. [Pod 删除成本](#pod-deletion-cost)
13. [Descheduler](#descheduler)
14. [Amazon EKS 中的调度优化](#scheduling-optimization-in-amazon-eks)
15. [调度最佳实践](#scheduling-best-practices)
16. [结论](#conclusion)

## 调度概览

Kubernetes 调度器是一个将 Pod 放置到合适节点的 control plane 组件。调度器会考虑多种因素来确定放置 Pod 的最优节点：

1. **资源需求**：Pod 请求的 CPU、内存及其他资源
2. **硬件/软件/策略约束**：节点选择器、节点亲和性、污点等
3. **亲和性/反亲和性规范**：与其他 Pod 的放置关系
4. **数据局部性**：将 Pod 放置在靠近数据的位置
5. **工作负载间干扰**：尽量减少不同工作负载之间的干扰
6. **自定义目标**：感知截止时间或工作负载干扰的调度需要合适的自定义逻辑；默认调度器不会推断应用程序截止时间

### 调度过程

调度过程大致分为两个阶段：

1. **过滤**：识别能够运行该 Pod 的节点集合
   - 检查是否满足资源需求
   - 检查节点选择器、亲和性、污点等约束

2. **评分**：为过滤后的节点评分以选择最优节点
   - 资源利用率平衡
   - Pod 间亲和性/反亲和性
   - 数据局部性
   - 污点/容忍

## 调度器的工作方式

Kubernetes 调度器通过以下过程运行：

![流水线图，展示 Pod 创建事件经过调度队列、kube-scheduler、过滤插件、评分插件、最优节点选择和到 API server 的绑定请求，直至 Pod 落在节点上。](../.gitbook/assets/en-core-08-scheduling-preemption-eviction-1.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-core-08-scheduling-preemption-eviction-1.html)

1. **Pod 队列监视**：调度器监视 API server 中未调度的 Pod。
2. **节点过滤**：识别能够运行该 Pod 的节点集合。
3. **节点评分**：为过滤后的节点评分。
4. **节点选择**：选择分数最高的节点。
5. **绑定**：将 Pod 绑定到选定节点。

### 调度插件

Kubernetes 调度器采用插件架构，旨在支持扩展。各种插件在调度过程的不同阶段运行：

1. **过滤插件**：筛除 Pod 无法运行的节点
   - NodeResourcesFit：检查节点资源容量
   - NodeName：检查 Pod 的 nodeName 字段
   - NodeUnschedulable：检查节点是否可调度
   - TaintToleration：检查污点和容忍

2. **评分插件**：为节点分配分数
   - NodeResourcesBalancedAllocation：考虑资源使用均衡
   - ImageLocality：考虑镜像局部性
   - InterPodAffinity：考虑 Pod 间亲和性
   - NodeAffinity：考虑节点亲和性

### NodeResourcesFit 评分策略：LeastAllocated 与 MostAllocated

`NodeResourcesFit` 既是过滤插件（节点是否拥有足够的可分配 CPU/内存来运行 Pod？），也是评分插件。其评分插件行为由通过 `KubeSchedulerConfiguration` 配置的 `scoringStrategy.type` 控制：

- **`LeastAllocated`**（默认）：节点已分配的资源越少，得分越高。新 Pod 会被引导至最空闲的节点，从而均匀分散负载。
- **`MostAllocated`**：节点已分配的资源越多，得分越高（前提是仍能容纳该 Pod）。新 Pod 会优先打包到最繁忙的节点，使其他节点保持未使用或空闲。
- **`RequestedToCapacityRatio`**：介于两者之间的可配置曲线，适用于 GPU 等扩展资源，即你需要自定义形状而非纯粹的最小化/最大化时。

```yaml
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
profiles:
- schedulerName: most-allocated-scheduler
  pluginConfig:
  - name: NodeResourcesFit
    args:
      scoringStrategy:
        type: MostAllocated
        resources:
        - name: cpu
          weight: 1
        - name: memory
          weight: 1
```

Amazon EKS 的 control plane 由完全托管，因此不能直接编辑默认 kube-scheduler 的 `KubeSchedulerConfiguration`。若要使用 `MostAllocated`，请运行*第二个*调度器（使用此配置运行 `kube-scheduler` 二进制文件的 `Deployment`，通过专用 `ServiceAccount` 绑定到 `system:kube-scheduler`/`system:volume-scheduler`），并使用 `spec.schedulerName` 将特定 Pod 指向它，如下文 [多个调度器](#multiple-schedulers) 所示——这也是[构建自定义调度器](../scheduling/01-custom-scheduler-part1.md)中使用的模式。

**已验证测试——分散与装箱行为。** 为确认实际差异，一个一次性的 3 worker `kind` 集群（`kubectl version` v1.37.0，隔离运行，测试后已拆除——未接触共享基础设施）使用 `nodeName` 固定的填充 Pod 预置了不均衡的基准负载（每个节点 16 CPU 可分配）：`worker`=12 个 Pod（75%）、`worker2`=6 个 Pod（37%）、`worker3`=0 个 Pod（0%）。随后，以相同起始状态对六个相同的 1 CPU Pod 分别调度两次——一次使用默认调度器（`LeastAllocated`），一次使用配置为 `MostAllocated` 的第二个调度器：

| 调度器 / 策略 | 6 个新 Pod 的落点 | 最终 CPU 利用率（worker / worker2 / worker3） |
|---|---|---|
| 默认（`LeastAllocated`） | 6 个全部在 `worker3`（最空闲节点） | 75% / 37% / 37%——三个节点现在均被使用 |
| `MostAllocated` | `worker` 上 3 个、`worker2` 上 3 个（两个最繁忙的节点） | 93% / 56% / 0%——`worker3` 保持完全空闲 |

`LeastAllocated` 提高了 `worker3` 的负载，直至其与 `worker2` 匹配，因此每个节点最终均被部分使用，且没有节点能够安全地缩容。`MostAllocated` 继续将负载集中在已繁忙的节点上，并保持 `worker3` 未被使用——这正是 cluster autoscaler 或 Karpenter 整合过程接下来会终止的节点。

因此，通常建议在与 Karpenter 或 Cluster Autoscaler 一起运行的**批处理/短生命周期 Job 工作负载**中使用 `MostAllocated`：将 Job 装箱到更少的节点上，可最大化完全空闲、符合整合条件的节点数量，直接降低计算成本。对于长期运行且对延迟敏感的 Service，`LeastAllocated` 仍是更好的默认选项，因为分散负载会在每个节点上保留余量，以吸收流量突发或 `kubectl drain`，而不会将压力级联到单个已打包节点上。

请在[调度器评分策略实验](../labs/core/08-scheduling-preemption-eviction-lab.md)中按步骤自行复现这一精确对比。

### 多个调度器

Kubernetes 可以同时运行多个调度器。这使得可以为特定工作负载实现自定义调度逻辑。

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: custom-scheduled-pod
spec:
  schedulerName: my-custom-scheduler
  containers:
  - name: container
    image: nginx
```

在上例中，`schedulerName` 字段指定用于调度该 Pod 的调度器。

## 节点选择

Kubernetes 提供了多种将 Pod 放置到特定节点的机制。

![该图比较了三种节点放置机制：nodeSelector 匹配节点标签、nodeName 固定到特定节点，以及 nodeAffinity 针对候选可用区评估表达式。](../.gitbook/assets/en-core-08-scheduling-preemption-eviction-2.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-core-08-scheduling-preemption-eviction-2.html)

### Node Selector

节点选择器是将 Pod 限制为仅放置到具有特定标签节点上的最简单方式。

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: gpu-pod
spec:
  nodeSelector:
    gpu: "true"
  containers:
  - name: gpu-container
    image: busybox:1.36
    command: ["sh", "-c", "sleep 3600"]
    resources:
      limits:
        nvidia.com/gpu: 1
```

在上例中，Pod 仅放置在具有 `gpu=true` 标签的节点上。

GPU 示例仅测试调度：节点必须确实具有 GPU，以及可通告 `nvidia.com/gpu` 的正常运行的 device plugin。仅有 `gpu=true` 标签不会分配 GPU 资源。

### nodeName

你可以使用 `nodeName` 字段将 Pod 直接放置到特定节点。此方法会绕过调度器，通常不建议使用。

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: specific-node-pod
spec:
  nodeName: worker-node-1
  containers:
  - name: container
    image: nginx
```

在上例中，Pod 被直接放置在名为 `worker-node-1` 的节点上。

## Pod 亲和性与反亲和性

Pod 亲和性和反亲和性提供了根据 Pod 间关系放置 Pod 的方式。

![该图对比了 Pod 亲和性与 Pod 反亲和性：前者将 web Pod 与 cache Pod 共置在同一节点上，后者将两个 web Pod 副本分隔在不同节点上；两者均可配置为硬性或软性要求。](../.gitbook/assets/en-core-08-scheduling-preemption-eviction-3.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-core-08-scheduling-preemption-eviction-3.html)

### Pod 亲和性

Pod 亲和性使 Pod 被放置在与具有特定标签的 Pod 相同的节点或拓扑域中。

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: frontend
spec:
  affinity:
    podAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
      - labelSelector:
          matchExpressions:
          - key: app
            operator: In
            values:
            - cache
        topologyKey: kubernetes.io/hostname
  containers:
  - name: frontend
    image: nginx
```

在上例中，`frontend` Pod 被放置在与具有 `app=cache` 标签的 Pod 相同的主机上。

### Pod 反亲和性

Pod 反亲和性使 Pod 被放置在与具有特定标签的 Pod 不同的节点或拓扑域中。

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: frontend
  labels:
    app: frontend
spec:
  affinity:
    podAntiAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
      - labelSelector:
          matchExpressions:
          - key: app
            operator: In
            values:
            - frontend
        topologyKey: kubernetes.io/hostname
  containers:
  - name: frontend
    image: nginx
```

在上例中，`frontend` Pod 被放置在与其他具有 `app=frontend` 标签的 Pod 不同的主机上。这对于将同一应用程序的实例分布到多个节点以实现高可用性很有用。

### 亲和性类型

Pod 亲和性和反亲和性有两种类型：

1. **requiredDuringSchedulingIgnoredDuringExecution**：必须在调度期间满足的硬性要求
2. **preferredDuringSchedulingIgnoredDuringExecution**：优选但非必需的软性要求

```yaml
# preferredDuringSchedulingIgnoredDuringExecution example
affinity:
  podAffinity:
    preferredDuringSchedulingIgnoredDuringExecution:
    - weight: 100
      podAffinityTerm:
        labelSelector:
          matchExpressions:
          - key: app
            operator: In
            values:
            - cache
        topologyKey: kubernetes.io/hostname
```

在上例中，`weight` 字段表示此偏好的权重。存在多个偏好时，权重越高的偏好越重要。

## 污点与容忍

污点和容忍是允许节点拒绝特定 Pod 的机制。

![该图展示节点污点如何拒绝 Pod，除非其携带匹配的容忍；展示三种污点效果 NoSchedule、PreferNoSchedule 和 NoExecute；并给出一个示例，其中带有 key=gpu:NoSchedule 污点的 GPU 节点拒绝普通 Pod，但接纳具有匹配容忍的 GPU Pod。](../.gitbook/assets/en-core-08-scheduling-preemption-eviction-4.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-core-08-scheduling-preemption-eviction-4.html)

### 污点

污点应用于节点，以限制 Pod 被调度到这些节点。

```bash
# Add taint to node
kubectl taint nodes node1 key=value:NoSchedule
```

污点有三种效果：

1. **NoSchedule**：不具有容忍的 Pod 不会被调度到该节点
2. **PreferNoSchedule**：优先不将不具有容忍的 Pod 调度到该节点
3. **NoExecute**：不具有容忍的 Pod 会从该节点驱逐

### 容忍

容忍应用于 Pod，以允许其被调度到具有污点的节点。

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: nginx
spec:
  tolerations:
  - key: "key"
    operator: "Equal"
    value: "value"
    effect: "NoSchedule"
  containers:
  - name: nginx
    image: nginx
```

在上例中，Pod 可以被调度到具有 `key=value:NoSchedule` 污点的节点上。

### 使用场景

污点和容忍的常见使用场景：

1. **专用节点**：指定节点仅运行特定工作负载
2. **特殊硬件**：管理具有 GPU 等特殊硬件的节点
3. **节点维护**：防止将新的 Pod 调度到正在维护的节点
4. **节点问题**：从有问题的节点驱逐 Pod

### 默认污点

Kubernetes 会对部分节点应用默认污点：

- **node.kubernetes.io/not-ready**：节点未就绪
- **node.kubernetes.io/unreachable**：节点不可达
- **node.kubernetes.io/memory-pressure**：节点存在内存压力
- **node.kubernetes.io/disk-pressure**：节点存在磁盘压力
- **node.kubernetes.io/pid-pressure**：节点存在 PID 压力
- **node.kubernetes.io/network-unavailable**：节点网络不可用
- **node.kubernetes.io/unschedulable**：节点不可调度

## 节点亲和性

节点亲和性提供了将 Pod 放置到特定节点集合的更具表现力的方式。它允许指定比节点选择器更复杂的条件。

### 节点亲和性类型

节点亲和性有两种类型：

1. **requiredDuringSchedulingIgnoredDuringExecution**：必须在调度期间满足的硬性要求
2. **preferredDuringSchedulingIgnoredDuringExecution**：优选但非必需的软性要求

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: with-node-affinity
spec:
  affinity:
    nodeAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
        nodeSelectorTerms:
        - matchExpressions:
          - key: topology.kubernetes.io/zone
            operator: In
            values:
            - us-west-2a
            - us-west-2b
      preferredDuringSchedulingIgnoredDuringExecution:
      - weight: 1
        preference:
          matchExpressions:
          - key: another-node-label-key
            operator: In
            values:
            - another-node-label-value
  containers:
  - name: with-node-affinity
    image: nginx
```

在上例中，Pod 仅放置在 `topology.kubernetes.io/zone` 标签为 `us-west-2a` 或 `us-west-2b` 的节点上。此外，它会优先放置在具有 `another-node-label-key=another-node-label-value` 标签的节点上。

### 操作符

节点亲和性支持多种操作符：

- **In**：标签值匹配指定值之一
- **NotIn**：标签值不匹配指定值
- **Exists**：存在具有指定键的标签
- **DoesNotExist**：不存在具有指定键的标签
- **Gt**：标签值大于指定值
- **Lt**：标签值小于指定值

## Pod 优先级与抢占

Kubernetes 提供 Pod 优先级和抢占功能，以确保重要工作负载能够获得集群资源。

![该图展示 PriorityClass 如何为 Pod 分配优先级，以及资源不足时如何触发对低优先级 Pod 的抢占；同时展示从调度失败到调度高优先级 Pod 的四步抢占流程，以及内置优先级类示例。](../.gitbook/assets/en-core-08-scheduling-preemption-eviction-5.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-core-08-scheduling-preemption-eviction-5.html)

### PriorityClass

PriorityClass 定义 Pod 的相对重要性。优先级值越高，Pod 越重要。

```yaml
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: high-priority
value: 1000000
globalDefault: false
description: "This priority class should be used for critical workloads."
```

在上例中，`value` 字段表示优先级值。值越高，优先级越高。如果将 `globalDefault` 字段设置为 `true`，则此优先级类会应用于未指定优先级类的 Pod。

### 向 Pod 应用 PriorityClass

要向 Pod 应用优先级类，请使用 `priorityClassName` 字段。

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: high-priority-pod
spec:
  priorityClassName: high-priority
  containers:
  - name: container
    image: nginx
```

### 抢占

抢占是移除较低优先级 Pod 以调度较高优先级 Pod 的过程。当调度器无法找到节点来调度较高优先级 Pod 时，它会抢占较低优先级 Pod 以获得资源。

抢占过程：
1. 调度器无法找到用于调度较高优先级 Pod 的节点
2. 调度器选择一个节点，通过抢占移除较低优先级 Pod
3. 通过 API 请求删除选定的较低优先级 Pod；kubelet/runtime 执行终止
4. Pod 优雅终止后，在该节点上调度较高优先级 Pod

### 抢占注意事项

使用抢占时应考虑以下事项：

1. **优雅终止期**：被抢占的 Pod 会在 `terminationGracePeriodSeconds` 指定的时间内经历优雅终止过程
2. **PodDisruptionBudget**：调度器会尝试避免违反它，但在没有合适的受害者可以避免违反时，抢占可能违反 PDB
3. **系统优先级类**：Kubernetes 为系统组件提供优先级类
   - `system-cluster-critical`：对集群运行至关重要的 Pod
   - `system-node-critical`：对节点运行至关重要的 Pod

## Pod 驱逐

Pod 驱逐会终止一个 Pod；其工作负载控制器可能会创建由调度器单独放置的替代 Pod。驱逐可能因多种原因发生。

![该图将 Pod 驱逐分为三类来源——controller manager 从 NotReady 或 Unreachable 节点驱逐 Pod，kubelet 在资源不足或硬件问题时驱逐 Pod 并监控 memory、nodefs、imagefs 和 pid 驱逐信号，以及用户为维护而 drain 节点。](../.gitbook/assets/en-core-08-scheduling-preemption-eviction-6.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-core-08-scheduling-preemption-eviction-6.html)

### 驱逐类型

1. **由 kube-controller-manager 驱逐**：
   - taint-eviction-controller 处理 NoExecute 污点。Pod 通常会获得 300 秒的 not-ready/unreachable 容忍；驱逐遵循其容忍设置
   - 当节点处于 Unreachable 状态时

2. **由 kubelet 驱逐**：
   - 节点资源不足（内存、磁盘等）
   - 硬件故障可能导致节点不可用；它们不是通用 kubelet 压力驱逐信号

3. **由用户驱逐**：
   - 执行 `kubectl drain` 命令
   - 节点维护任务

### kubelet 驱逐信号

kubelet 监控以下驱逐信号：

1. **memory.available**：可用内存
2. **nodefs.available**：节点文件系统中的可用空间
3. **nodefs.inodesFree**：节点文件系统中的可用 inode
4. **imagefs.available**：镜像文件系统中的可用空间
5. **imagefs.inodesFree**：镜像文件系统中的可用 inode
6. **pid.available**：可用进程 ID

可以为每个信号设置软阈值和硬阈值：

- **软阈值**：阈值超出 `grace-period` 后驱逐 Pod
- **硬阈值**：阈值超出时立即驱逐 Pod

```yaml
# kubelet configuration example
evictionHard:
  memory.available: "100Mi"
  nodefs.available: "10%"
  nodefs.inodesFree: "5%"
  imagefs.available: "15%"
  imagefs.inodesFree: "5%"
evictionSoft:
  memory.available: "200Mi"
  nodefs.available: "15%"
evictionSoftGracePeriod:
  memory.available: "1m"
  nodefs.available: "2m"
evictionMaxPodGracePeriod: 30
evictionPressureTransitionPeriod: "30s"
```

### 驱逐优先级

kubelet 根据使用量是否超出请求、Pod 优先级以及相对于请求的使用量对候选 Pod 排序。它不会简单地先驱逐所有 BestEffort Pod，再驱逐所有 Burstable Pod，最后驱逐所有 Guaranteed Pod。磁盘/PID 压力具有不同的资源核算约束；QoS 不是通用的驱逐排序规则。

## Pod Disruption Budget (PDB)

Pod Disruption Budget (PDB) 是在自愿中断期间维持应用程序可用性的一种方式。PDB 限制可同时受干扰的 Pod 数量。

![该图展示 PodDisruptionBudget 的 minAvailable、maxUnavailable 和 selector 设置如何控制节点 drain 等自愿中断，允许或拒绝驱逐；并以一个 Deployment 为例，展示等价的 minAvailable 和 maxUnavailable 设置产生相同效果。](../.gitbook/assets/en-core-08-scheduling-preemption-eviction-7.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-core-08-scheduling-preemption-eviction-7.html)

### PDB 定义

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: frontend-pdb
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: frontend
```

或

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: frontend-pdb
spec:
  maxUnavailable: 1
  selector:
    matchLabels:
      app: frontend
```

在上述示例中：
- `minAvailable`：必须始终保持可用的最小 Pod 数量
- `maxUnavailable`：可同时不可用的最大 Pod 数量
- `selector`：选择 PDB 所适用 Pod 的标签选择器

### PDB 操作

1. 发生节点 drain 等自愿中断时，Kubernetes 检查 PDB
2. 如果满足 PDB 条件，则继续驱逐 Pod
3. 如果不满足 PDB 条件，则拒绝驱逐 Pod

PDB 会控制普通 drain/descheduler 操作等 Eviction API 请求。直接删除 Pod、控制器滚动更新和节点压力驱逐会绕过此控制。仅当工作负载具有三个期望副本时，`minAvailable: 2` 和 `maxUnavailable: 1` 才等价；两者均不会创建替代容量。

### PDB 最佳实践

1. **为所有关键工作负载设置 PDB**：为所有需要高可用性的工作负载设置 PDB
2. **选择合适的值**：选择适合工作负载特征的 `minAvailable` 或 `maxUnavailable` 值
3. **考虑副本数**：`minAvailable` 可以等于副本数以阻止自愿驱逐，但维护可能因此停滞；请配置有意识的中断余量
4. **定期测试**：通过节点 drain 和类似任务测试 PDB 操作

## 节点压力驱逐

节点压力驱逐是因节点资源不足而驱逐 Pod 的机制。

### 节点状态

kubelet 报告以下节点状态：

1. **MemoryPressure**：节点内存不足
2. **DiskPressure**：节点磁盘空间不足
3. **PIDPressure**：节点进程 ID 不足

发生这些状态时，kubelet 会驱逐 Pod 以获得资源。

### 驱逐策略配置

可以在 kubelet 配置中设置驱逐策略：

```yaml
# kubelet configuration example
evictionHard:
  memory.available: "100Mi"
  nodefs.available: "10%"
  nodefs.inodesFree: "5%"
  imagefs.available: "15%"
  imagefs.inodesFree: "5%"
evictionSoft:
  memory.available: "200Mi"
  nodefs.available: "15%"
evictionSoftGracePeriod:
  memory.available: "1m"
  nodefs.available: "2m"
evictionMinimumReclaim:
  memory.available: "50Mi"
  nodefs.available: "5%"
evictionMaxPodGracePeriod: 30
evictionPressureTransitionPeriod: "30s"
```

在上例中：
- `evictionMinimumReclaim`：驱逐后必须回收的最少资源
- `evictionPressureTransitionPeriod`：压力状态转换之间的等待时间

## TopologySpreadConstraints

TopologySpreadConstraints 可细粒度控制 Pod 如何分布在可用区、节点或区域等拓扑域中。相比 Pod 反亲和性，此功能在实现高可用性和高效资源利用方面提供了更大的灵活性。

![该图展示 TopologySpreadConstraints 如何通过 maxSkew、topologyKey、whenUnsatisfiable 和常用的 labelSelector 控制 Pod 在可用区之间的分布；展示 whenUnsatisfiable 的 DoNotSchedule 和 ScheduleAnyway 选项；并给出 EKS 示例，其中 maxSkew=1 的新 Pod 落在拥有最少 Pod 的 ap-northeast-2b 可用区。](../.gitbook/assets/en-core-08-scheduling-preemption-eviction-8.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-core-08-scheduling-preemption-eviction-8.html)

### 关键字段

| 字段 | 描述 | 必需 |
|-------|-------------|----------|
| **maxSkew** | 对于 DoNotSchedule，目标域与全局最小值之间允许的差异；ScheduleAnyway 将 skew 用作偏好 | 是 |
| **topologyKey** | 定义拓扑域的节点标签键 | 是 |
| **whenUnsatisfiable** | 无法满足约束时的操作：`DoNotSchedule` 或 `ScheduleAnyway` | 是 |
| **labelSelector** | 选择要计数的 Pod；通常应指定它和匹配的 Pod 标签 | 否（null 不匹配任何 Pod） |
| **minDomains** | 用于 skew 计算的最小合格域数量（自 v1.30 起稳定） | 否 |
| **matchLabelKeys** | 用于分布计算的匹配 Pod 标签键（1.27+） | 否 |

### whenUnsatisfiable 选项

- **DoNotSchedule**：如果无法满足约束，调度器不会调度该 Pod（硬约束）
- **ScheduleAnyway**：调度器仍会调度该 Pod，并为最小化 skew 的节点赋予更高优先级（软约束）

### EKS 可用区分布示例

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
spec:
  replicas: 6
  selector:
    matchLabels:
      app: web
  template:
    metadata:
      labels:
        app: web
    spec:
      topologySpreadConstraints:
      - maxSkew: 1
        topologyKey: topology.kubernetes.io/zone
        whenUnsatisfiable: DoNotSchedule
        labelSelector:
          matchLabels:
            app: web
      - maxSkew: 1
        topologyKey: kubernetes.io/hostname
        whenUnsatisfiable: ScheduleAnyway
        labelSelector:
          matchLabels:
            app: web
      containers:
      - name: web
        image: nginx:1.30.4
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
```

此配置确保：
1. Pod 在可用区之间均匀分布（硬约束）
2. Pod 优先分布在每个可用区内的不同节点上（软约束）

### minDomains 和 matchLabelKeys

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app-with-min-domains
spec:
  replicas: 4
  selector:
    matchLabels:
      app: distributed-app
  template:
    metadata:
      labels:
        app: distributed-app
        version: v1
    spec:
      topologySpreadConstraints:
      - maxSkew: 1
        topologyKey: topology.kubernetes.io/zone
        whenUnsatisfiable: DoNotSchedule
        labelSelector:
          matchLabels:
            app: distributed-app
        minDomains: 3
        matchLabelKeys:
        - version
      containers:
      - name: app
        image: myapp:v1
```

- **minDomains**：如果合格域少于 3 个，全局最小值将变为零。当 maxSkew 为 1 时，每个合格域中一个匹配的 Pod 仍可被调度；后续 Pod 可能保持 Pending。它不会立即阻止每个 Pod。
- **matchLabelKeys**：自动在选择器中使用 Pod 的 `version` 标签值，从而无需修改选择器即可实现每个修订版本的分布。

### 相比 Pod 反亲和性的优势

| 方面 | TopologySpreadConstraints | Pod 反亲和性 |
|--------|---------------------------|-------------------|
| **灵活性** | 允许受控的 skew（maxSkew > 1） | 二元：相同或不同域 |
| **软约束** | 使用 `ScheduleAnyway` 实现尽力而为 | 使用 `preferredDuringScheduling`，但控制较少 |
| **多层级** | 使用不同 topologyKey 的多个约束 | 需要复杂的嵌套规则 |
| **性能** | 大规模下具有更好的调度器性能 | Pod 较多时可能减慢调度 |
| **使用场景** | 具有容忍度的均匀分布 | 严格分隔 |

## Pod 删除成本

Pod 删除成本是 ReplicaSet 控制器在缩容时使用的尽力而为偏好。HPA 会更改期望副本数；它不会选择单独的受害 Pod。该注解不会保护 Job/StatefulSet、阻止驱逐或保证删除顺序。

### 工作方式

当控制器（如 HPA 或手动缩容）需要减少副本时，它会考虑：
1. 删除成本较低的 Pod 会优先被移除
2. 默认删除成本为 0
3. 有效范围：-2147483648 到 2147483647

### 基本示例

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: worker-pod
  annotations:
    controller.kubernetes.io/pod-deletion-cost: "100"
spec:
  containers:
  - name: worker
    image: worker:latest
```

### HPA 缩容优先级控制

使用删除成本在 HPA 缩容期间保护重要 Pod：

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-service
spec:
  replicas: 5
  selector:
    matchLabels:
      app: web
  template:
    metadata:
      labels:
        app: web
      # Lower cost pods are deleted first during scale-down
      annotations:
        controller.kubernetes.io/pod-deletion-cost: "0"
    spec:
      containers:
      - name: web
        image: nginx:1.30.4
```

### 缓存保护模式

如果缓存将通过基于 CPU 利用率的 HPA 进行扩缩容，请为其设置显式 CPU 请求。以下是调度示例，并非完整的 Redis 生产配置：

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cache-service
spec:
  replicas: 3
  selector:
    matchLabels:
      app: cache
  template:
    metadata:
      labels:
        app: cache
    spec:
      automountServiceAccountToken: false
      containers:
      - name: cache
        image: redis:7
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
```

在测量实际缓存预热程度后，经授权的操作员/控制器可以在缩容前为选定的由 ReplicaSet 管理的 Pod 添加一次注解：

```bash
kubectl -n default annotate pod "$CACHE_POD" \
  controller.kubernetes.io/pod-deletion-cost="1000" --overwrite
```

将 `CACHE_POD` 设置为实际的缓存 Pod。频繁写入注解会产生 API 负载。自定义更新器需要 Redis 和 Kubernetes client 工具，以及范围严格限定的 Pod patch 权限；仅凭经过时间不能证明缓存已预热。本示例未安装任何更新器。

### 实际使用场景

1. **由 ReplicaSet 管理的有状态缓存**：优先保留已预热的副本
2. **leader 选举**：让 leader Pod 运行更久
3. **连接排空**：为长时间运行的连接留出时间
4. **缓存预热**：保留具有热缓存的 Pod
5. **限制**：Job 和 StatefulSet 控制器不使用此偏好

## Descheduler

Descheduler 是一个 Kubernetes 组件，它会从节点驱逐 Pod，使调度器能够将其重新调度到更合适的节点。与仅放置新 Pod 的调度器不同，Descheduler 有助于长期维持最优 Pod 放置。

![该图展示当节点添加、移除或 Pod 变更破坏均匀分布的集群时，Descheduler 如何通过驱逐运行中的 Pod 使调度器重新放置它们来恢复平衡；同时展示六种代表性的 Descheduler 策略，例如 RemoveDuplicates、LowNodeUtilization 和 PodLifeTime。](../.gitbook/assets/en-core-08-scheduling-preemption-eviction-9.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-core-08-scheduling-preemption-eviction-9.html)

### 为什么需要重新调度

1. **集群变更**：添加新节点、节点标签发生变化
2. **Pod 漂移**：初始放置会随时间变得不再最优
3. **亲和性违规**：集群变更后规则被违反
4. **资源不平衡**：一些节点过度利用，另一些节点利用不足
5. **失败的 Pod**：Pod 陷入重启循环

### 关键策略

| 策略 | 描述 | 使用场景 |
|----------|-------------|----------|
| **RemoveDuplicates** | 从同一节点移除重复 Pod | 节点故障后确保 HA |
| **LowNodeUtilization** | 将 Pod 从过度利用的节点移至利用不足的节点 | 平衡集群资源 |
| **RemovePodsHavingTooManyRestarts** | 驱逐重启次数过多的 Pod | 清理有问题的 Pod |
| **PodLifeTime** | 驱逐超过指定年龄的 Pod | 强制重新调度 |
| **RemovePodsViolatingInterPodAntiAffinity** | 驱逐违反反亲和性规则的 Pod | 恢复亲和性合规 |
| **RemovePodsViolatingNodeAffinity** | 驱逐违反节点亲和性的 Pod | 恢复亲和性合规 |
| **RemovePodsViolatingTopologySpreadConstraint** | 驱逐违反分布约束的 Pod | 恢复均匀分布 |

### Helm 安装

Descheduler v0.36.0 是已验证的示例版本，目标为 Kubernetes v1.36 及其测试窗口中的前两个次要版本。将其应用于其他版本前，请检查兼容性矩阵。将经过审查的 Helm 值保存至 `descheduler-values.yaml`，其中包含 `schedule` 和 `deschedulerPolicy.profiles`（下文所示的策略 profiles）；旧的 `strategies.*.enabled` 值不配置此 API。

```bash
helm repo add descheduler https://kubernetes-sigs.github.io/descheduler/
helm upgrade --install descheduler descheduler/descheduler \
  --version 0.36.0 --namespace kube-system \
  --values descheduler-values.yaml
```

### DeschedulerPolicy 配置

```yaml
apiVersion: descheduler/v1alpha2
kind: DeschedulerPolicy
profiles:
- name: default
  pluginConfig:
  - name: DefaultEvictor
    args:
      nodeFit: true
  - name: RemoveDuplicates
    args:
      excludeOwnerKinds: [StatefulSet]
  - name: LowNodeUtilization
    args:
      thresholds:
        cpu: 20
        memory: 20
        pods: 20
      targetThresholds:
        cpu: 50
        memory: 50
        pods: 50
  - name: RemovePodsHavingTooManyRestarts
    args:
      podRestartThreshold: 100
      includingInitContainers: true
  - name: PodLifeTime
    args:
      maxPodLifeTimeSeconds: 86400
      labelSelector:
        matchLabels:
          app.kubernetes.io/lifecycle: ephemeral
  - name: RemovePodsViolatingNodeAffinity
    args:
      nodeAffinityType: [requiredDuringSchedulingIgnoredDuringExecution]
  - name: RemovePodsViolatingTopologySpreadConstraint
    args:
      constraints: [DoNotSchedule]
  plugins:
    balance:
      enabled:
      - RemoveDuplicates
      - LowNodeUtilization
      - RemovePodsViolatingTopologySpreadConstraint
    deschedule:
      enabled:
      - RemovePodsHavingTooManyRestarts
      - PodLifeTime
      - RemovePodsViolatingNodeAffinity
```

### 遵守 PDB

Descheduler 遵守 Pod Disruption Budget (PDB)。如果驱逐一个 Pod 会违反 PDB，Descheduler 将不会驱逐该 Pod：

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: web-pdb
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: web
```

有此 PDB 后，Descheduler 将确保在重新调度操作期间至少有 2 个带有 `app: web` 标签的 Pod 保持可用。

上述策略是 Descheduler 配置文件，而不是供 kubectl apply 使用的 API 对象。它使用 Balance 插件进行组重新分布，并使用 Deschedule 插件进行按 Pod 决策。LowNodeUtilization 通常评估资源请求而非实时 CPU 使用量，且驱逐不保证替代 Pod 会落在其他位置。启用周期性驱逐前，请审查保护措施并在 dry-run 中测试。

### Descheduler CronJob 示例

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: descheduler
  namespace: kube-system
spec:
  schedule: "*/30 * * * *"
  concurrencyPolicy: Forbid
  jobTemplate:
    spec:
      template:
        spec:
          serviceAccountName: descheduler
          containers:
          - name: descheduler
            image: registry.k8s.io/descheduler/descheduler:v0.36.0
            args:
            - --policy-config-file=/policy/policy.yaml
            - --v=3
            volumeMounts:
            - name: policy
              mountPath: /policy
          volumes:
          - name: policy
            configMap:
              name: descheduler-policy
          restartPolicy: OnFailure
```

独立的 CronJob 是 Helm 的替代方案，并非额外的安装。它需要 `descheduler` ServiceAccount/RBAC，以及键为 `policy.yaml` 的 `descheduler-policy` ConfigMap；请使用官方 chart/manifests 来提供这些前提条件。

> **深入了解**：有关自定义调度器的详细信息，请参阅：
> - [自定义调度器第 1 部分：基本概念](../scheduling/01-custom-scheduler-part1.md)
> - [自定义调度器第 2 部分：实现](../scheduling/02-custom-scheduler-part2.md)
> - [自定义调度器第 3 部分：高级功能](../scheduling/03-custom-scheduler-part3.md)

## Amazon EKS 中的调度优化

在 Amazon EKS 中，你可以使用 Kubernetes 调度功能优化工作负载。

![该图展示四个 EKS 调度优化手段——节点组和实例类型选择、可用区分布、Karpenter 自动扩缩容，以及资源请求和限制调优——每种手段均连接到实现它的机制或自动化工具：Cluster Autoscaler、多 AZ 部署、Karpenter NodePool 和 Vertical Pod Autoscaler。](../.gitbook/assets/en-core-08-scheduling-preemption-eviction-11.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-core-08-scheduling-preemption-eviction-11.html)

### 节点组和实例类型

在 EKS 中，可以利用多种节点组和实例类型来为工作负载提供合适的资源：

1. **多种实例类型**：计算优化、内存优化、存储优化等
2. **Spot Instances**：用于成本效益型工作负载的 Spot 实例
3. **GPU Instances**：用于 AI/ML 工作负载的 GPU 实例

你可以使用节点标签和污点将特定工作负载放置到特定节点组：

对于现有集群，请使用经过审查的 eksctl 配置，其中需具有匹配的 Region、受支持的 GPU 实例/AMI，以及所需 IAM 权限：

```yaml
# gpu-nodegroup.yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
- name: gpu-nodes
  instanceType: p3.2xlarge
  desiredCapacity: 1
  privateNetworking: true
  labels:
    workload-type: gpu
  taints:
  - key: gpu
    value: "true"
    effect: NoSchedule
```

```bash
eksctl create nodegroup --config-file=gpu-nodegroup.yaml
```

### 可用区分布

在 EKS 中，你可以使用 Pod 反亲和性和拓扑分布约束将工作负载分布到多个可用区：

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-server
spec:
  replicas: 3
  selector:
    matchLabels:
      app: web
  template:
    metadata:
      labels:
        app: web
    spec:
      topologySpreadConstraints:
      - maxSkew: 1
        topologyKey: topology.kubernetes.io/zone
        whenUnsatisfiable: DoNotSchedule
        labelSelector:
          matchLabels:
            app: web
      containers:
      - name: web
        image: nginx
```

在上例中，`topologySpreadConstraints` 将 Pod 均匀分布到多个可用区。

### 使用 Karpenter 自动扩缩容

在 Amazon EKS 中，你可以使用 Karpenter 自动预置适合工作负载的节点：

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: default
spec:
  template:
    spec:
      requirements:
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["spot", "on-demand"]
        - key: kubernetes.io/arch
          operator: In
          values: ["amd64", "arm64"]
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: default-class
  limits:
    cpu: 1000
    memory: 1000Gi
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30s
---
apiVersion: karpenter.k8s.aws/v1
kind: EC2NodeClass
metadata:
  name: default-class
spec:
  role: KarpenterNodeRole-my-cluster
  amiSelectorTerms:
    - alias: al2023@latest
  subnetSelectorTerms:
    - tags:
        karpenter.sh/discovery: my-cluster
  securityGroupSelectorTerms:
    - tags:
        karpenter.sh/discovery: my-cluster
```

Karpenter 通过根据 Pod 资源需求选择最优实例类型来优化成本。

### 资源请求和限制优化

在 EKS 中优化工作负载的资源请求和限制非常重要：

1. **Vertical Pod Autoscaler (VPA)**：基于实际工作负载资源使用情况优化资源请求
2. **Goldilocks**：可视化 VPA 建议，以支持资源请求优化
3. **Resource Quotas**：限制每个 namespace 的资源使用量

```yaml
# VPA example
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: frontend-vpa
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: frontend
  updatePolicy:
    updateMode: "Recreate"
```

## 调度最佳实践

在 Kubernetes 和 EKS 中优化调度的最佳实践：

1. **设置合适的资源请求和限制**：
   - 根据实际工作负载资源使用情况设置资源请求
   - 为重要工作负载设置合适的资源限制
   - 使用 VPA 自动优化资源请求

2. **工作负载分布**：
   - 使用 Pod 反亲和性将重要工作负载分布到多个节点
   - 使用拓扑分布约束将工作负载分布到多个可用区
   - 使用节点亲和性将特定工作负载放置到特定节点

3. **节点资源优化**：
   - 使用多种实例类型为工作负载提供合适的资源
   - 使用 Spot 实例优化成本
   - 使用 Karpenter 自动预置适合工作负载的节点

4. **PDB 配置**：
   - 为重要工作负载设置 PDB
   - 选择适合工作负载特征的 `minAvailable` 或 `maxUnavailable` 值
   - 定期测试 PDB 操作

5. **优先级和抢占配置**：
   - 为重要工作负载设置高优先级类
   - 为系统组件使用 `system-cluster-critical` 或 `system-node-critical` 优先级类
   - 了解并测试抢占影响

6. **节点污点和容忍**：
   - 为专门工作负载设置专用节点
   - 对维护中的节点应用污点
   - 设置合适的容忍

## 结论

Kubernetes 调度、抢占和驱逐机制在高效管理集群资源并维持工作负载可用性方面发挥重要作用。通过理解和利用这些功能，你可以优化并可靠地运行 Amazon EKS 集群中的工作负载。

调度优化是一个持续过程，应根据工作负载特征和集群状态不断进行调整。使用监控工具跟踪集群资源使用情况，并按需调整调度策略非常重要。

## 测验

要测试你在本章学到的内容，请尝试[调度、抢占与驱逐测验](../quizzes/core/08-scheduling-preemption-eviction-quiz.md)。
