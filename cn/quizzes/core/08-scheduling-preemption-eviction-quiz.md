# 调度、抢占、驱逐与反调度测验

本测验涵盖 Kubernetes 调度、节点选择、亲和性、污点、优先级、驱逐、中断预算和反调度。

## 选择题

1. 评估候选节点时，过滤、评分和绑定中哪一步最先发生？
   - A) 节点评分
   - B) 节点过滤
   - C) 确定 Pod 优先级
   - D) 绑定

<details>
<summary>显示答案</summary>

**答案：B) 节点过滤**

**解释：**
调度器会过滤不合适的节点，为可行节点评分，选择一个节点，然后绑定 Pod。排队和其他框架扩展点会围绕这些步骤进行。
</details>

2. 节点亲和性和 Pod 亲和性的主要区别是什么？
   - A) 节点亲和性仅支持硬约束；Pod 亲和性仅支持软约束
   - B) 节点亲和性匹配节点标签；Pod 亲和性根据匹配的 Pod 确定放置位置
   - C) 节点亲和性适用于整个集群，而 Pod 亲和性适用于整个命名空间
   - D) 只有 Pod 亲和性会在运行时自动改变放置位置

<details>
<summary>显示答案</summary>

**答案：B) 节点亲和性匹配节点标签；Pod 亲和性根据匹配的 Pod 确定放置位置**

**解释：**
两者都支持必需规则和首选规则。Pod 亲和性使用匹配的 Pod 和拓扑键来表达共置要求。IgnoredDuringExecution 不会在标签更改时自动驱逐 Pod。
</details>

3. 污点和容忍度的作用是什么？
   - A) 保证 Pod 只在某个特定节点上运行
   - B) 让节点排斥 Pod，除非 Pod 具有匹配的容忍度
   - C) 设置 Pod 间亲和性
   - D) 自动优化集群利用率

<details>
<summary>显示答案</summary>

**答案：B) 让节点排斥 Pod，除非 Pod 具有匹配的容忍度**

**解释：**
容忍度允许将带污点的节点纳入考虑范围；它不会吸引 Pod，也不保证 Pod 会被放置在该节点上。对于专用工作负载，应将其与节点亲和性结合使用，并控制谁可以使用该容忍度。
</details>

4. Pod 优先级与抢占有什么关系？
   - A) 调度期间，较高优先级的 Pod 可能抢占较低优先级的 Pod
   - B) 优先级直接设置 CPU/内存分配
   - C) 只有在维护期间才会发生抢占
   - D) 两者无关

<details>
<summary>显示答案</summary>

**答案：A) 调度期间，较高优先级的 Pod 可能抢占较低优先级的 Pod**

**解释：**
如果移除较低优先级的受害 Pod 能让待处理的 Pod 可调度，调度器就可以将其移除。这并不保证容量或放置位置。设置了 preemptionPolicy: Never 的 PriorityClass 不会抢占其他 Pod。
</details>

5. nodeSelector 和节点亲和性有什么区别？
   - A) nodeSelector 是硬约束；节点亲和性同时支持硬约束和软约束
   - B) nodeSelector 只支持一个标签
   - C) 节点亲和性无法匹配标签值
   - D) nodeSelector 只在调度后生效

<details>
<summary>显示答案</summary>

**答案：A) nodeSelector 是硬约束；节点亲和性同时支持硬约束和软约束**

**解释：**
节点亲和性还支持 In、NotIn、Exists、DoesNotExist、Gt 和 Lt。nodeSelector 中的所有条目都必须匹配。必需的节点亲和性必须匹配；首选规则会影响评分。
</details>

6. 哪种情况通常会触发节点压力驱逐？
   - A) 单纯因为某个 Pod 的优先级值较低
   - B) 节点的内存、磁盘空间或其他受监控资源不足
   - C) 单纯因为某个 Pod 已经存在很长时间
   - D) ReplicaSet 的副本过多

<details>
<summary>显示答案</summary>

**答案：B) 节点的内存、磁盘空间或其他受监控资源不足**

**解释：**
Kubelet 会监控压力信号，并可能回收资源和终止 Pod。候选 Pod 的排序会考虑超出请求量的资源使用情况、Pod 优先级和相对使用量，而不是固定的、仅基于 QoS 的顺序。其他驱逐机制包括 drain 和 NoExecute 污点。
</details>

7. DaemonSet Pod 如何放置？
   - A) 在每个符合条件的目标节点上放置一个 Pod
   - B) 只放置在控制平面节点上
   - C) 它们总是绕过 kube-scheduler
   - D) 副本数与符合条件的节点数无关

<details>
<summary>显示答案</summary>

**答案：A) 在每个符合条件的目标节点上放置一个 Pod**

**解释：**
DaemonSet 控制器会创建目标节点为符合条件节点的 Pod；调度器负责绑定它们。选择器、亲和性、容忍度和容量仍然会产生影响。描述当前 DaemonSet 时，不应使用历史上的直接绑定行为。
</details>

8. 未设置 Pod 级资源时，如果每个容器的 CPU 请求和限制相等，且内存请求和限制相等，则适用哪种 QoS 类？
   - A) BestEffort
   - B) Burstable
   - C) Guaranteed
   - D) Critical

<details>
<summary>显示答案</summary>

**答案：C) Guaranteed**

**解释：**
Guaranteed 要求每个容器的 CPU 和内存请求与限制分别相等。BestEffort 表示两者都未设置，其他中间配置属于 Burstable。QoS 不等同于 PriorityClass，也不保证 Pod 在任何故障或压力情况下都能存活。
</details>

9. 什么允许调度器考虑将 Pod 调度到带有 node-role.kubernetes.io/control-plane:NoSchedule 污点的节点上？
   - A) 仅节点亲和性
   - B) 仅 Pod 亲和性
   - C) 匹配的容忍度
   - D) 仅较高的 PriorityClass

<details>
<summary>显示答案</summary>

**答案：C) 匹配的容忍度**

**解释：**
容忍度允许 Pod 容忍该污点，但仍必须满足资源和其他放置约束。仅将控制平面节点用于预期的工作负载。

```yaml
tolerations:
- key: "node-role.kubernetes.io/control-plane"
  operator: "Exists"
  effect: "NoSchedule"
```
</details>

10. PodDisruptionBudget 主要控制什么？
   - A) 容器资源消耗
   - B) 通过 Eviction API 执行的自愿驱逐
   - C) 调度优先级
   - D) 容器重启策略

<details>
<summary>显示答案</summary>

**答案：B) 通过 Eviction API 执行的自愿驱逐**

**解释：**
PDB 会限制允许的 Eviction API 请求，包括常规 drain/descheduler 操作。直接删除 Pod、工作负载控制器滚动更新以及节点压力驱逐都绕过此限制。它不会创建健康副本，也无法防止节点故障。
</details>

## 简答题

1. 描述至少三个调度器 Filter 插件。

<details>
<summary>显示答案</summary>

**答案：**

- **NodeResourcesFit** 会根据节点可分配容量和已有请求检查资源请求。
- **NodeAffinity** 会检查必需的节点选择规则；除非适用相关容忍度，否则 **NodeUnschedulable** 会拒绝已封锁的节点。
- **InterPodAffinity** 会同时检查 Pod 亲和性和反亲和性；**PodTopologySpread** 会检查硬性分布约束。
- **TaintToleration** 会检查污点。**NodePorts** 会检测主机端口冲突。
- **VolumeBinding** 会检查 PVC 绑定/拓扑；**NodeVolumeLimits** 会检查 CSI 附加限制。
- 直接指定 `spec.nodeName` 通常会绕过调度器。不应将 NodeName 描述为优先级最高的过滤器。

像 EBSLimits 这样的旧版按云提供商划分的名称并不是当前 CSI 插件的名称。
</details>

2. 说明节点亲和性与污点/容忍度如何配合用于专用 GPU 节点。

<details>
<summary>显示答案</summary>

**答案：**

节点亲和性会将工作负载限制在目标节点上，而污点会排斥缺少匹配容忍度的 Pod。例如，为实际的 GPU 节点添加标签，要求匹配的 GPU 标签，为这些节点添加污点，并且只在获批的 GPU 工作负载中容忍该污点。

仅有容忍度不能保证 Pod 被放置在 GPU 节点上。还需要像 `nvidia.com/gpu: 1` 这样的 GPU 请求，以及正常工作的设备插件，才能预留 GPU。如果这种隔离属于安全边界，则还需要限制谁可以添加容忍度/标签。
</details>

3. 说明 Pod 优先级和抢占及其限制。

<details>
<summary>显示答案</summary>

**答案：**

创建 PriorityClass，并通过 `spec.priorityClassName` 引用它。调度器队列会使用优先级；如果移除较低优先级的受害 Pod 能让待处理的 Pod 可调度，调度器就可以选择这些受害 Pod。

调度器会通过 API 请求删除受害 Pod；kubelet/runtime 会执行终止操作。受害 Pod 的终止可能会延迟传入 Pod 的启动，而且被提名的节点并非无条件预留。抢占不会移除优先级相同或更高的 Pod，也可能无法解决亲和性或容量约束问题。

PDB 会以尽力而为的方式纳入考虑，不提供保证。用户定义的优先级值不得大于 1,000,000,000；系统类使用保留的更高值。Pod 仅仅运行在 kube-system 中并不会因此获得豁免。请查看事件并测试影响。

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

**节点压力：** Kubelet 会监控内存、文件系统和 PID 可用情况，并可能在终止 Pod 前回收资源。Linux 常见硬阈值默认值包括：memory.available 低于 100Mi、nodefs.available 低于 10%、imagefs.available 低于 15%，以及可用 inode 低于 5%。PID 没有默认的 10% 阈值。Windows 的内存默认值有所不同。

**软阈值与硬阈值：** 必须显式配置软阈值及其宽限期。硬阈值可能会在没有优雅终止期的情况下终止 Pod。软阈值下的终止也受 evictionMaxPodGracePeriod 限制。覆盖默认值时，请保留所有预期阈值。

**Eviction API：** 常规 drain 和兼容的自动化工具会提交 policy/v1 Eviction 请求。PDB 会限制这些请求。直接执行 Pod DELETE 则不同，它会绕过 PDB 检查。

**基于污点的删除：** NoExecute 污点可以删除不容忍这些污点的 Pod。普通 Pod 通常具有 300 秒的 not-ready/unreachable 容忍时间。这与 kubelet 的压力驱逐以及 Eviction API 限制机制相互独立。

驱逐会结束一个 Pod；工作负载控制器可能会使用新的 UID 创建替代 Pod。没有任何机制能安全地将同一个 Pod 移动到另一个节点。可用性需要副本、存储/容量规划以及经过测试的故障处理机制。
</details>

5. 当前 DaemonSet 调度与 Deployment Pod 调度有何不同？

<details>
<summary>显示答案</summary>

**答案：**

DaemonSet 控制器会为每个符合条件的节点创建一个 Pod，并设置目标节点亲和性。调度器负责绑定。Deployment 则通过 ReplicaSet 维护期望的副本数，并根据资源和约束确定放置位置；Pod 数量并非每个节点一个。

DaemonSet 会自动获得若干针对节点状况的容忍度，其中包括对 not-ready/unreachable NoExecute 的无限期容忍度。它们不会绕过所有资源约束，也不会自动在每个带污点的控制平面节点上运行。
</details>

## 实操题

1. 创建一个名为 web-server 的 Pod，使用 nginx:1.30.6，要求放置在 us-east-1a 或 us-east-1b，并优先放置在 m5.large 节点上。

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
    image: nginx:1.30.6
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

必需的节点亲和性会限制符合条件的可用区。首选节点亲和性会为 m5.large 添加评分偏好。标准标签由云/节点集成组件填充；请确认所选集群节点确实具有这些标签。
</details>

2. 为 worker-1 添加 dedicated=database:NoSchedule 污点，并为 postgres-db Pod 添加匹配的容忍度。

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

请先在同一命名空间中创建带有 password 键的 postgres-credentials。此示例演示调度，但没有持久化数据库存储；若要持久使用，请添加 PVC。容忍度允许 Pod 放置在 worker-1 上，但不会强制将其放置在那里。
</details>

3. 创建一个包含三个副本的 web-frontend Deployment，使用 nginx:1.30.6，与 app=cache 的 Pod 共置，同时将自身副本彼此分开。

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
        image: nginx:1.30.6
```

必需的 Pod 亲和性和反亲和性适用于该命名空间。要调度全部三个副本，至少三个符合条件的节点上都必须存在匹配的 cache Pod。否则，副本可能会一直处于 Pending 状态。这些规则不会在标签更改后自动移动现有 Pod。
</details>

4. 创建 value 为 100000 的 high-priority，以及 QoS 为 Guaranteed 的 critical-service Pod：CPU 500m 和内存 512Mi 的请求与限制分别相等。

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
    image: nginx:1.30.6
    resources:
      requests:
        cpu: 500m
        memory: 512Mi
      limits:
        cpu: 500m
        memory: 512Mi
```

优先级会影响排队/抢占；容器的 CPU 和内存请求与限制相等，满足容器级别的 Guaranteed 条件。优先级和 QoS 都无法保证 Pod 免受节点故障或驱逐的影响。
</details>

5. 为 app=web-server 的 Pod 创建 web-pdb，并设置 minAvailable: 2。

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

PDB 会限制常规 Eviction API 请求，使自愿驱逐不会让当前健康状态低于预算。替代方案 maxUnavailable: 1 仅在期望副本数为三个时效果相同。它无法保护直接删除、滚动更新或非自愿故障。
</details>

## 高级主题

1. 为选定 Pod 运行单独调度器的常见方式是什么？
   - A) 每次策略变更都重新构建 kube-scheduler
   - B) 部署一个调度器，并通过 schedulerName 选择它
   - C) 为所有 Pod 添加任意注解
   - D) 在 kubelet 中启用本地调度

<details>
<summary>显示答案</summary>

**答案：B) 部署一个调度器，并通过 schedulerName 选择它**

**解释：**
必须确保实际运行着匹配的调度器，并为其配置合适的 RBAC 和兼容的配置。仅设置 schedulerName 并不会安装调度器。调度器会监视 Pod/节点，并绑定符合条件的待处理 Pod；kubelet 不会选择放置位置。

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

2. 哪个不是 Descheduler 策略？
   - A) LowNodeUtilization
   - B) RemoveDuplicates
   - C) PodLifeTimeExtension
   - D) RemovePodsViolatingInterPodAntiAffinity

<details>
<summary>显示答案</summary>

**答案：C) PodLifeTimeExtension**

**解释：**
PodLifeTime 会驱逐匹配的旧 Pod；它不会延长这些 Pod 的生命周期。其他策略包括 NodeAffinity、拓扑分布和重启次数检查。LowNodeUtilization 通常会比较请求的资源与节点容量。Descheduler 负责驱逐；控制器会创建替代 Pod，而 kube-scheduler 会选择放置位置，但不一定会选择不同的节点。
</details>

3. 哪个不是自动应用的标准节点状况污点？
   - A) node.kubernetes.io/not-ready
   - B) node.kubernetes.io/unreachable
   - C) node.kubernetes.io/disk-pressure
   - D) node.kubernetes.io/high-load

<details>
<summary>显示答案</summary>

**答案：D) node.kubernetes.io/high-load**

**解释：**
当前的标准污点包括 not-ready、unreachable、memory-pressure、disk-pressure、pid-pressure、network-unavailable 和 unschedulable。旧版 out-of-disk 污点不是当前自动应用的污点。压力污点通常使用 NoSchedule；not-ready/unreachable 的 NoExecute 行为与 kubelet 压力驱逐是不同的机制。
</details>

4. 关于拓扑分布约束，哪项说法是错误的？
   - A) 它们可以将 Pod 分布到带标签的可用区、节点或机架
   - B) DoNotSchedule 会根据全局最小值评估偏差
   - C) ScheduleAnyway 使用分布偏好
   - D) 它们会自动迁移现有 Pod

<details>
<summary>显示答案</summary>

**答案：D) 它们会自动迁移现有 Pod**

**解释：**
分布约束会影响传入 Pod 的调度，不会移动正在运行的 Pod。使用 DoNotSchedule 时，maxSkew 会将目标域中的匹配 Pod 数量与全局最小值进行比较；如果符合条件的域少于 minDomains，该最小值就是零。请让传入 Pod 的标签与 labelSelector 匹配，使其计入数量。Descheduler 可能会驱逐符合条件且违反约束的 Pod，但不会保证替代 Pod 被放置在特定位置。

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

5. 关于 QoS 和驱逐，哪项说法是错误的？
   - A) Guaranteed 要求 CPU/内存请求与限制采用适当的相等配置
   - B) Burstable 涵盖介于 Guaranteed 和 BestEffort 之间的配置
   - C) BestEffort 不设置 CPU/内存请求或限制
   - D) 在压力下，Guaranteed Pod 总是最先被驱逐

<details>
<summary>显示答案</summary>

**答案：D) 在压力下，Guaranteed Pod 总是最先被驱逐**

**解释：**
Kubelet 不会将 QoS 作为严格的驱逐顺序。它会根据超出请求量的资源使用情况、优先级以及相对于请求量的使用情况进行排序；磁盘压力采用不同的核算方式。Guaranteed Pod 仍可能被驱逐或在故障中丢失。QoS 根据资源配置推导得出，并非直接设置的 Pod 字段。
</details>

6. 一个批处理作业工作负载与 Karpenter/Cluster Autoscaler 同时运行，并且应尽可能增加可完全空闲以便整合的节点数量。哪种 `NodeResourcesFit` 评分策略最合适，为什么？
   - A) `LeastAllocated`，因为它会让所有节点上的 CPU/内存使用量趋于均衡
   - B) `MostAllocated`，因为它会将新 Pod 集中放到已经最繁忙的节点上，让其他节点空闲
   - C) `RequestedToCapacityRatio`，采用与 `LeastAllocated` 相同的线性曲线
   - D) 两种策略都无关紧要，因为 EKS 允许你直接编辑默认调度器的配置

<details>
<summary>显示答案</summary>

**答案：B) `MostAllocated`，因为它会将新 Pod 集中放到已经最繁忙的节点上，让其他节点空闲**

**解释：**
在有不均衡基线负载（CPU 为 75%/37%/0%）的三节点临时 `kind` 测试中，这一点得到了验证：默认的 `LeastAllocated` 调度器将 6 个新 Pod 都调度到最空闲的节点，使三个节点的负载变为 75%/37%/37%（没有节点可以缩容）。另一个配置了 `scoringStrategy.type: MostAllocated` 的调度器，则将同样的 6 个 Pod 调度到两个最繁忙的节点上（93%/56%/0%），使空闲节点不受影响，因而可以进行整合。Amazon EKS 的控制平面由 AWS 管理，因此要应用 `MostAllocated`，需要运行额外的调度器 `Deployment`，并通过 `schedulerName` 将 Pod 指定给它，而不是直接编辑默认调度器。
</details>

[返回学习材料](../../core/08-scheduling-preemption-eviction.md)
