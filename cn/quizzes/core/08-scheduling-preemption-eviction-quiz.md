# 调度、抢占和驱逐测验

本测验涵盖 Kubernetes 调度、节点选择、亲和性、污点、优先级、驱逐、中断预算和重新调度。

## 多项选择题

1. 在评估候选节点时，过滤、评分和绑定中哪一项最先发生？
   - A) 节点评分
   - B) 节点过滤
   - C) 确定 Pod 优先级
   - D) 绑定

<details>
<summary>显示答案</summary>

**答案：B) 节点过滤**

**说明：**
调度器会过滤不合适的节点，为可行节点评分，选择一个节点，然后绑定 Pod。队列处理和其他框架扩展点围绕这些步骤运行。
</details>

2. 节点亲和性和 Pod 亲和性的主要区别是什么？
   - A) 节点亲和性仅支持硬约束；Pod 亲和性仅支持软约束
   - B) 节点亲和性匹配节点标签；Pod 亲和性将放置与匹配的 Pod 关联起来
   - C) 节点亲和性是集群范围的，而 Pod 亲和性是命名空间范围的
   - D) 只有 Pod 亲和性会在运行时自动更改放置位置

<details>
<summary>显示答案</summary>

**答案：B) 节点亲和性匹配节点标签；Pod 亲和性将放置与匹配的 Pod 关联起来**

**说明：**
两者都支持必需和首选规则。Pod 亲和性使用匹配的 Pod 和拓扑键来表达共置。标签变更时，IgnoredDuringExecution 不会自动驱逐 Pod。
</details>

3. 污点和容忍的用途是什么？
   - A) 保证一个 Pod 只在某个特定节点上运行
   - B) 使节点排斥 Pod，除非它们具有匹配的容忍
   - C) 设置 Pod 间亲和性
   - D) 自动优化集群利用率

<details>
<summary>显示答案</summary>

**答案：B) 使节点排斥 Pod，除非它们具有匹配的容忍**

**说明：**
容忍允许考虑带有污点的节点；它不会吸引 Pod 或保证放置。对于专用工作负载，应将其与节点亲和性结合使用，并控制谁可以使用该容忍。
</details>

4. Pod 优先级和抢占有何关系？
   - A) 在调度期间，较高优先级的 Pod 可以抢占较低优先级的 Pod
   - B) 优先级直接设置 CPU/内存分配
   - C) 抢占仅在维护期间发生
   - D) 两者无关

<details>
<summary>显示答案</summary>

**答案：A) 在调度期间，较高优先级的 Pod 可以抢占较低优先级的 Pod**

**说明：**
如果移除较低优先级的受害 Pod 能使待处理 Pod 可调度，调度器就可以移除它们。这并不保证容量或放置。具有 preemptionPolicy: Never 的 PriorityClass 不会抢占其他 Pod。
</details>

5. nodeSelector 和节点亲和性有何区别？
   - A) nodeSelector 是硬约束；节点亲和性支持硬约束和软约束
   - B) nodeSelector 仅支持一个标签
   - C) 节点亲和性无法匹配标签值
   - D) nodeSelector 仅在调度后适用

<details>
<summary>显示答案</summary>

**答案：A) nodeSelector 是硬约束；节点亲和性支持硬约束和软约束**

**说明：**
节点亲和性还支持 In、NotIn、Exists、DoesNotExist、Gt 和 Lt。所有 nodeSelector 条目都必须匹配。必需的节点亲和性必须匹配；首选规则会影响评分。
</details>

6. 哪种情况通常会触发节点压力驱逐？
   - A) 一个 Pod 本身具有较低的优先级值
   - B) 节点缺少内存、磁盘空间或其他受监控资源
   - C) 一个 Pod 本身已存在很长时间
   - D) 一个 ReplicaSet 有过多副本

<details>
<summary>显示答案</summary>

**答案：B) 节点缺少内存、磁盘空间或其他受监控资源**

**说明：**
Kubelet 会监控压力信号，并可能回收资源和终止 Pod。候选项排序会考虑超出请求量的使用量、Pod 优先级和相对使用量，而不是固定的仅 QoS 顺序。其他驱逐机制包括 drain 和 NoExecute 污点。
</details>

7. DaemonSet Pod 如何放置？
   - A) 在每个符合条件的目标节点上放置一个 Pod
   - B) 仅在控制平面节点上放置
   - C) 它们始终绕过 kube-scheduler
   - D) 副本数与符合条件节点的数量无关

<details>
<summary>显示答案</summary>

**答案：A) 在每个符合条件的目标节点上放置一个 Pod**

**说明：**
DaemonSet 控制器会创建目标指向符合条件节点的 Pod；调度器负责绑定它们。选择器、亲和性、容忍和容量仍然重要。不应使用历史上的直接绑定行为来描述当前的 DaemonSet。
</details>

8. 没有 Pod 级资源设置时，当每个容器的 CPU 请求/限制相等且内存请求/限制相等，会应用哪个 QoS 类？
   - A) BestEffort
   - B) Burstable
   - C) Guaranteed
   - D) Critical

<details>
<summary>显示答案</summary>

**答案：C) Guaranteed**

**说明：**
Guaranteed 在每个容器上具有相等的 CPU 和内存请求/限制。BestEffort 两者均不设置，而中间配置属于 Burstable。QoS 不是 PriorityClass，也不保证在所有故障或压力情况下都能存活。
</details>

9. 什么允许在带有 node-role.kubernetes.io/control-plane:NoSchedule 污点的节点上进行调度考虑？
   - A) 仅节点亲和性
   - B) 仅 Pod 亲和性
   - C) 匹配的容忍
   - D) 仅较高的 PriorityClass

<details>
<summary>显示答案</summary>

**答案：C) 匹配的容忍**

**说明：**
容忍允许该污点，但仍必须满足资源和其他放置约束。仅将控制平面放置用于预期的工作负载。

```yaml
tolerations:
- key: "node-role.kubernetes.io/control-plane"
  operator: "Exists"
  effect: "NoSchedule"
```
</details>

10. PodDisruptionBudget 主要控制什么？
   - A) 容器资源消耗
   - B) 通过 Eviction API 进行的自愿驱逐
   - C) 调度优先级
   - D) 容器重启策略

<details>
<summary>显示答案</summary>

**答案：B) 通过 Eviction API 进行的自愿驱逐**

**说明：**
PDB 限制允许的 Eviction API 请求，包括常规 drain/descheduler 操作。直接删除 Pod、工作负载控制器滚动发布和节点压力驱逐会绕过此限制。它不会创建健康副本或防止节点故障。
</details>

## 简答题

1. 描述至少三个调度器 Filter 插件。

<details>
<summary>显示答案</summary>

**答案：**

- **NodeResourcesFit** 根据节点可分配容量和现有请求检查所请求的资源。
- **NodeAffinity** 检查必需的节点选择规则；除非适用相关容忍，否则 **NodeUnschedulable** 会拒绝已 cordon 的节点。
- **InterPodAffinity** 同时检查 Pod 亲和性和反亲和性；**PodTopologySpread** 检查硬分布约束。
- **TaintToleration** 检查污点。**NodePorts** 检测主机端口冲突。
- **VolumeBinding** 检查 PVC 绑定/拓扑；**NodeVolumeLimits** 检查 CSI 挂载限制。
- 直接分配的 `spec.nodeName` 通常会绕过调度器。NodeName 不应被描述为最高优先级的过滤器。

诸如 EBSLimits 等旧的每提供商名称不是当前的 CSI 插件名称。
</details>

2. 说明节点亲和性和污点/容忍如何协同用于专用 GPU 节点。

<details>
<summary>显示答案</summary>

**答案：**

节点亲和性将工作负载限制在预期节点上，而污点会排斥缺少匹配容忍的 Pod。例如，为实际 GPU 节点添加标签，要求匹配的 GPU 标签，对它们施加污点，并且只在获批准的 GPU 工作负载中容忍该污点。

单独使用容忍并不能保证放置到 GPU 节点。还需要诸如 `nvidia.com/gpu: 1` 的 GPU 请求和正常工作的设备插件来预留 GPU。当这种隔离是安全边界时，必须限制谁可以添加容忍/标签。
</details>

3. 说明 Pod 优先级和抢占，包括它们的限制。

<details>
<summary>显示答案</summary>

**答案：**

创建一个 PriorityClass，并通过 `spec.priorityClassName` 引用它。调度器队列使用优先级，如果移除较低优先级的受害 Pod 可以使待处理 Pod 可行，抢占可以选择这些受害 Pod。

调度器通过 API 请求删除受害 Pod；kubelet/runtime 执行终止。受害 Pod 的终止可能会延迟传入的 Pod，并且被提名的节点不是无条件的预留。抢占不会移除同等或更高优先级的 Pod，也可能无法解决亲和性或容量约束。

PDB 仅以尽力而为的方式被考虑，并非保证。用户定义的优先级值不得大于 1,000,000,000；系统类具有保留的更高值。仅仅运行在 kube-system 中不会使 Pod 获得豁免。请检查事件并测试影响。

```yaml
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: high-priority
value: 1000000
globalDefault: false
description: "This priority class should be used for critical production workloads."
```

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: critical-pod
spec:
  priorityClassName: high-priority
  containers:
  - name: web-server
    image: nginx
```
</details>

4. 区分节点压力驱逐、Eviction API 请求和基于污点的删除。

<details>
<summary>显示答案</summary>

**答案：**

**节点压力：**Kubelet 观察内存、文件系统和 PID 可用性，并可能在终止 Pod 前回收资源。典型的 Linux 硬默认值包括 memory.available 低于 100Mi、nodefs.available 低于 10%、imagefs.available 低于 15%，以及空闲 inode 低于 5%。PID 没有默认的 10% 阈值。Windows 内存默认值不同。

**软阈值与硬阈值：**必须显式配置软阈值及其宽限期。硬阈值可以在没有优雅终止期的情况下终止 Pod。软终止也受 evictionMaxPodGracePeriod 限制。覆盖默认值时，请保留所有预期阈值。

**Eviction API：**常规 drain 和兼容的自动化会提交 policy/v1 Eviction 请求。PDB 会限制这些请求。直接 Pod DELETE 与此不同，并会绕过 PDB 检查。

**基于污点的删除：**NoExecute 污点可以删除不容忍它们的 Pod。普通 Pod 通常具有 300 秒的 not-ready/unreachable 容忍。这与 Kubelet 压力驱逐以及 Eviction API 限制是不同的机制。

驱逐会结束一个 Pod；工作负载控制器可能会创建一个具有新 UID 的替代 Pod。没有机制能够安全地将同一个 Pod 移动到不同节点。可用性需要副本、存储/容量规划以及经过测试的故障处理。
</details>

5. 当前 DaemonSet 调度与 Deployment Pod 调度有何不同？

<details>
<summary>显示答案</summary>

**答案：**

DaemonSet 控制器会为每个符合条件的节点创建一个 Pod，并设置目标节点亲和性。调度器执行绑定。相比之下，Deployment 通过 ReplicaSet 维持所需副本数，放置基于资源和约束；Pod 数量不是每节点一个。

DaemonSet 会获得针对节点状况的若干自动容忍，包括无限期的 not-ready/unreachable NoExecute 容忍。它们不会绕过所有资源约束，也不会自动在每个带污点的控制平面节点上运行。
</details>

## 实践题

1. 创建一个名为 web-server、使用 nginx:1.30.4 的 Pod，该 Pod 必须位于 us-east-1a 或 us-east-1b，并且首选 m5.large 节点。

<details>
<summary>显示答案</summary>

**答案：**

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: web-server
spec:
  containers:
  - name: nginx
    image: nginx:1.30.4
  affinity:
    nodeAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
        nodeSelectorTerms:
        - matchExpressions:
          - key: topology.kubernetes.io/zone
            operator: In
            values:
            - us-east-1a
            - us-east-1b
      preferredDuringSchedulingIgnoredDuringExecution:
      - weight: 1
        preference:
          matchExpressions:
          - key: node.kubernetes.io/instance-type
            operator: In
            values:
            - m5.large
```

必需节点亲和性限制符合条件的可用区。首选节点亲和性为 m5.large 添加评分偏好。标准标签由云/节点集成填充；请验证所选集群节点实际具有这些标签。
</details>

2. 为 worker-1 添加 dedicated=database:NoSchedule 污点，并为 postgres-db Pod 提供匹配的容忍。

<details>
<summary>显示答案</summary>

**答案：**

```bash
kubectl taint nodes worker-1 dedicated=database:NoSchedule
```

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: postgres-db
spec:
  containers:
  - name: postgres
    image: postgres:17
    env:
    - name: POSTGRES_PASSWORD
      valueFrom:
        secretKeyRef:
          name: postgres-credentials
          key: password
  tolerations:
  - key: "dedicated"
    operator: "Equal"
    value: "database"
    effect: "NoSchedule"
```

请先在同一命名空间中创建具有 password 键的 postgres-credentials。此示例演示调度，且没有持久数据库存储；如需持久使用，请添加 PVC。容忍允许使用 worker-1，但不会强制放置到那里。
</details>

3. 创建一个三副本的 web-frontend Deployment，使用 nginx:1.30.4，与 app=cache Pod 共置，但与自身副本分离。

<details>
<summary>显示答案</summary>

**答案：**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-frontend
spec:
  replicas: 3
  selector:
    matchLabels:
      app: web-frontend
  template:
    metadata:
      labels:
        app: web-frontend
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
            topologyKey: "kubernetes.io/hostname"
        podAntiAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
          - labelSelector:
              matchExpressions:
              - key: app
                operator: In
                values:
                - web-frontend
            topologyKey: "kubernetes.io/hostname"
      containers:
      - name: nginx
        image: nginx:1.30.4
```

必需的 Pod 亲和性和反亲和性在该命名空间中适用。要调度所有三个副本，至少三个符合条件的节点上必须存在匹配的 cache Pod。否则，副本可能保持 Pending。这些规则不会在标签改变后自动移动现有 Pod。
</details>

4. 创建值为 100000 的 high-priority，以及一个具有 Guaranteed QoS 的 critical-service Pod：CPU 500m 和内存 512Mi 的请求和限制均相同。

<details>
<summary>显示答案</summary>

**答案：**

```yaml
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: high-priority
value: 100000
globalDefault: false
description: "This priority class is for critical services that should be scheduled first."
```

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: critical-service
spec:
  priorityClassName: high-priority
  containers:
  - name: nginx
    image: nginx:1.30.4
    resources:
      requests:
        cpu: 500m
        memory: 512Mi
      limits:
        cpu: 500m
        memory: 512Mi
```

优先级影响排队/抢占；容器上相等的 CPU 和内存请求/限制满足容器级 Guaranteed 标准。优先级和 QoS 均不保证免受节点故障或驱逐的影响。
</details>

5. 为具有 app=web-server 的 Pod 创建 minAvailable: 2 的 web-pdb。

<details>
<summary>显示答案</summary>

**答案：**

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: web-pdb
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: web-server
```

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: web-pdb
spec:
  maxUnavailable: 1
  selector:
    matchLabels:
      app: web-server
```

PDB 会限制常规 Eviction API 请求，因此自愿驱逐不会将当前健康状态降低到其预算以下。替代方案 maxUnavailable: 1 仅在所需副本数为三个时具有相同效果。它不防护直接删除、滚动更新或非自愿故障。
</details>

## 高级主题

1. 为选定的 Pod 运行单独调度器的常用方法是什么？
   - A) 为每次策略更改重新构建 kube-scheduler
   - B) 部署一个调度器并使用 schedulerName 选择它
   - C) 为所有 Pod 添加任意注解
   - D) 在 kubelet 中启用本地调度

<details>
<summary>显示答案</summary>

**答案：B) 部署一个调度器并使用 schedulerName 选择它**

**说明：**
匹配的调度器必须实际在运行，并具有合适的 RBAC 和兼容的配置。仅 schedulerName 不会安装它。调度器监视 Pod/节点并绑定符合条件的待处理 Pod；kubelet 不选择放置位置。

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
</details>

2. 哪一项不是 Descheduler 策略？
   - A) LowNodeUtilization
   - B) RemoveDuplicates
   - C) PodLifeTimeExtension
   - D) RemovePodsViolatingInterPodAntiAffinity

<details>
<summary>显示答案</summary>

**答案：C) PodLifeTimeExtension**

**说明：**
PodLifeTime 会驱逐匹配的旧 Pod；它不会延长它们的生命周期。其他策略包括 NodeAffinity、拓扑分布和重启计数检查。LowNodeUtilization 通常将所请求的资源与节点容量进行比较。Descheduler 负责驱逐；控制器创建替代 Pod，kube-scheduler 选择放置位置，该位置不一定是不同的节点。
</details>

3. 哪一项不是标准自动应用的节点状况污点？
   - A) node.kubernetes.io/not-ready
   - B) node.kubernetes.io/unreachable
   - C) node.kubernetes.io/disk-pressure
   - D) node.kubernetes.io/high-load

<details>
<summary>显示答案</summary>

**答案：D) node.kubernetes.io/high-load**

**说明：**
当前标准污点包括 not-ready、unreachable、memory-pressure、disk-pressure、pid-pressure、network-unavailable 和 unschedulable。旧的 out-of-disk 污点不是当前的自动污点。压力污点通常使用 NoSchedule；not-ready/unreachable 的 NoExecute 行为和 kubelet 压力驱逐是不同的机制。
</details>

4. 关于拓扑分布约束的哪项陈述是错误的？
   - A) 它们可以将 Pod 分布到带标签的可用区、节点或机架中
   - B) DoNotSchedule 根据全局最小值评估偏差
   - C) ScheduleAnyway 使用分布偏好
   - D) 它们会自动重新放置现有 Pod

<details>
<summary>显示答案</summary>

**答案：D) 它们会自动重新放置现有 Pod**

**说明：**
分布约束会影响传入 Pod 的调度。它们不会移动正在运行的 Pod。使用 DoNotSchedule 时，maxSkew 会将目标域中匹配 Pod 的数量与全局最小值进行比较；如果符合条件的域少于 minDomains，该最小值为零。请使传入 Pod 标签与 labelSelector 匹配，以便它参与计数。Descheduler 可能会驱逐符合条件且违反约束的 Pod，但不保证特定替代 Pod 的放置位置。

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: example-pod
  labels:
    app: web-server
spec:
  topologySpreadConstraints:
  - maxSkew: 1
    topologyKey: topology.kubernetes.io/zone
    whenUnsatisfiable: DoNotSchedule
    labelSelector:
      matchLabels:
        app: web-server
  containers:
  - name: nginx
    image: nginx
```
</details>

5. 关于 QoS 和驱逐的哪项陈述是错误的？
   - A) Guaranteed 需要适当的相等 CPU/内存请求-限制配置
   - B) Burstable 覆盖 Guaranteed 和 BestEffort 之间的配置
   - C) BestEffort 没有 CPU/内存请求或限制
   - D) Guaranteed Pod 总是在压力下最先被驱逐

<details>
<summary>显示答案</summary>

**答案：D) Guaranteed Pod 总是在压力下最先被驱逐**

**说明：**
Kubelet 不会将 QoS 用作严格的驱逐顺序。它根据超出请求量的使用量、优先级和相对于请求量的使用量进行排序；磁盘压力具有不同的核算方式。Guaranteed Pod 仍可能在故障期间被驱逐或丢失。QoS 源自资源，而不是直接作为 Pod 字段分配。
</details>

6. batch-job 工作负载与 Karpenter/Cluster Autoscaler 一起运行，并且应最大化可完全空闲以进行整合的节点数量。哪种 `NodeResourcesFit` 评分策略最合适，为什么？
   - A) `LeastAllocated`，因为它在每个节点上均衡 CPU/内存使用量
   - B) `MostAllocated`，因为它将新 Pod 打包到已最繁忙的节点上，并使其他节点保持空闲
   - C) 使用与 `LeastAllocated` 相同线性曲线的 `RequestedToCapacityRatio`
   - D) 两种策略都无关紧要，因为 EKS 允许你直接编辑默认调度器的配置

<details>
<summary>显示答案</summary>

**答案：B) `MostAllocated`，因为它将新 Pod 打包到已最繁忙的节点上，并使其他节点保持空闲**

**说明：**
使用负载不均衡的基线（CPU 为 75%/37%/0%）进行的一次性 3-worker `kind` 测试证实了这一点：默认的 `LeastAllocated` 调度器将 6 个新 Pod 路由到最空闲的节点，使三个节点分别达到 75%/37%/37%（没有节点可缩容）。使用 `scoringStrategy.type: MostAllocated` 配置的第二个调度器将相同的 6 个 Pod 路由到两个最繁忙的节点（93%/56%/0%），使空闲节点保持不受影响并符合整合条件。Amazon EKS 的控制平面由托管，因此应用 `MostAllocated` 需要运行额外的调度器 `Deployment`，并使用 `schedulerName` 将 Pod 定向到它，而不是直接编辑默认调度器。
</details>

[返回学习材料](../../core/08-scheduling-preemption-eviction.md)
