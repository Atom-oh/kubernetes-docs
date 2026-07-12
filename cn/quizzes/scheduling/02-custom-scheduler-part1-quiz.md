# Custom Scheduler 测验（第 1 部分）

本测验用于测试你对在 Kubernetes 中实现和使用 Custom Scheduler 的理解。

## 测验问题

### 1. 在 Kubernetes 中，scheduler 的主要作用是什么？

A. Pod 的创建和删除
B. 将 Pod 分配给合适的 Node
C. Node 资源监控
D. Container image 下载

<details>
<summary>显示答案</summary>

**答案: B. 将 Pod 分配给合适的 Node**

**解析:**
在 Kubernetes 中，scheduler 的主要作用是将 Pod 分配给合适的 Node。scheduler 会监听新创建的 Pod，并为尚未分配到 Node 的 Pod 找到最适合运行它们的 Node。

**Scheduler 的主要功能:**
1. **Pod-Node 分配**: 根据 Pod 需求和 Node 可用资源选择最优 Node。
2. **Filtering**: 排除无法运行该 Pod 的 Node（例如资源不足、taints 等）。
3. **Scoring**: 对合适的 Node 进行评分，以选择最优 Node。
4. **Binding**: 将 Pod 绑定到所选 Node，以最终确定调度决策。

**调度流程:**
1. **Filtering Stage (Predicates)**: 排除无法运行该 Pod 的 Node。
   - PodFitsResources: 检查 Node 是否有足够资源满足 Pod 的 resource requests
   - PodFitsHostPorts: 检查请求的 host ports 是否可用
   - PodMatchNodeSelector: 检查 Pod 的 node selector 是否匹配 Node labels
   - NoVolumeZoneConflict: 检查 volume zone 约束
   - CheckNodeMemoryPressure: 检查 Node memory pressure 状态
   - CheckNodeDiskPressure: 检查 Node disk pressure 状态

2. **Scoring Stage (Priorities)**: 对合适的 Node 进行评分。
   - LeastRequestedPriority: 给已请求资源较少的 Node 更高分数
   - BalancedResourceAllocation: 给资源使用更均衡的 Node 更高分数
   - NodeAffinityPriority: 基于 node affinity 规则评分
   - TaintTolerationPriority: 基于 taint toleration 评分
   - InterPodAffinityPriority: 基于 inter-pod affinity/anti-affinity 评分

3. **Binding**: 将 Pod 绑定到得分最高的 Node。

**默认 Scheduler 配置示例:**
```yaml
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
profiles:
- schedulerName: default-scheduler
  plugins:
    score:
      disabled:
      - name: NodeResourcesLeastAllocated
      enabled:
      - name: NodeResourcesBalancedAllocation
        weight: 1
```

**其他选项的问题:**
- A. Pod 的创建和删除: 这主要是 controller manager 和 API server 的职责。
- C. Node 资源监控: 这主要是 kubelet 和 metrics server 的职责。
- D. Container image 下载: 这是 kubelet 和 container runtime 的职责。
</details>

### 2. 以下哪一项不是实现 Custom Scheduler 的方法？

A. 扩展现有的 kube-scheduler
B. 实现一个全新的 scheduler
C. 开发 scheduling framework plugin
D. 修改 kubelet

<details>
<summary>显示答案</summary>

**答案: D. 修改 kubelet**

**解析:**
修改 kubelet 不是实现 Custom Scheduler 的方法。kubelet 是运行在每个 Node 上并管理 Pod 执行的代理，但它不做调度决策。调度由 kube-scheduler 或 custom schedulers 执行。

**实现 Custom Scheduler 的方法:**

1. **扩展现有的 kube-scheduler**:
   - 使用 KubeSchedulerConfiguration 自定义默认 scheduler 的行为。
   - 调整 plugin 权重、启用/禁用等。

   ```yaml
   apiVersion: kubescheduler.config.k8s.io/v1
   kind: KubeSchedulerConfiguration
   profiles:
   - schedulerName: custom-scheduler
     plugins:
       score:
         disabled:
         - name: NodeResourcesLeastAllocated
         enabled:
         - name: NodeResourcesBalancedAllocation
           weight: 2
   ```

2. **实现一个全新的 scheduler**:
   - 开发一个与 Kubernetes API 通信的独立 scheduler。
   - 直接实现 Pod 监听、Node 选择和绑定逻辑。

   ```go
   // Simple Go scheduler example
   func main() {
       config, err := clientcmd.BuildConfigFromFlags("", os.Getenv("KUBECONFIG"))
       if err != nil {
           log.Fatal(err)
       }

       clientset, err := kubernetes.NewForConfig(config)
       if err != nil {
           log.Fatal(err)
       }

       // Watch unscheduled pods
       watchPods(clientset)
   }

   func watchPods(clientset *kubernetes.Clientset) {
       watch, err := clientset.CoreV1().Pods("").Watch(context.TODO(), metav1.ListOptions{
           FieldSelector: "spec.schedulerName=custom-scheduler,spec.nodeName=",
       })
       if err != nil {
           log.Fatal(err)
       }

       for event := range watch.ResultChan() {
           if event.Type != watch.Added {
               continue
           }

           pod := event.Object.(*v1.Pod)
           // Implement node selection logic
           node := selectNode(clientset, pod)
           if node != "" {
               bindPod(clientset, pod, node)
           }
       }
   }
   ```

3. **开发 scheduling framework plugin**:
   - 使用 Kubernetes scheduling framework 为特定调度阶段开发 plugins。
   - 实现 filter、score、bind 等 extension points。

   ```go
   // Scoring plugin example
   type MyScorePlugin struct{}

   func (pl *MyScorePlugin) Name() string {
       return "MyScorePlugin"
   }

   func (pl *MyScorePlugin) Score(ctx context.Context, state *framework.CycleState, pod *v1.Pod, nodeName string) (int64, *framework.Status) {
       // Implement custom scoring logic
       return score, nil
   }

   func (pl *MyScorePlugin) ScoreExtensions() framework.ScoreExtensions {
       return pl
   }

   func (pl *MyScorePlugin) NormalizeScore(ctx context.Context, state *framework.CycleState, pod *v1.Pod, scores framework.NodeScoreList) *framework.Status {
       // Implement score normalization logic
       return nil
   }
   ```

**kubelet 的作用:**
kubelet 是运行在每个 Node 上的代理，执行以下职责:
- 根据 Pod specs 运行和管理 containers
- 监控并报告 Node 状态
- 执行 container health checks
- 管理 volume mounts

kubelet 执行 scheduler 做出的决策（在哪个 Node 上运行哪个 Pod），它本身不做调度决策。

**其他选项说明:**
- A. 扩展现有的 kube-scheduler: 有效的 Custom Scheduler 实现方法。
- B. 实现一个全新的 scheduler: 有效的 Custom Scheduler 实现方法。
- C. 开发 scheduling framework plugin: 有效的 Custom Scheduler 实现方法。
</details>

### 3. 在 Pod 中，用于指定特定 scheduler 的字段是什么？

A. spec.scheduler
B. spec.schedulerName
C. metadata.scheduler
D. spec.nodeName

<details>
<summary>显示答案</summary>

**答案: B. spec.schedulerName**

**解析:**
在 Pod 中用于指定特定 scheduler 的字段是 `spec.schedulerName`。设置此字段后，Pod 只会由具有指定名称的 scheduler 进行调度。默认值是 "default-scheduler"。

**Pod Spec 示例:**
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: custom-scheduled-pod
  labels:
    app: my-app
spec:
  schedulerName: my-custom-scheduler  # Specify custom scheduler
  containers:
  - name: main-container
    image: nginx:1.19
    resources:
      requests:
        memory: "64Mi"
        cpu: "250m"
      limits:
        memory: "128Mi"
        cpu: "500m"
```

此 Pod 只会由名为 "my-custom-scheduler" 的 scheduler 调度。如果集群中不存在该名称的 scheduler，Pod 将保持在 `Pending` 状态。

**部署多个 Scheduler 的示例:**
```yaml
# Custom scheduler deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-custom-scheduler
  namespace: kube-system
spec:
  replicas: 1
  selector:
    matchLabels:
      component: my-custom-scheduler
  template:
    metadata:
      labels:
        component: my-custom-scheduler
    spec:
      serviceAccountName: my-custom-scheduler
      containers:
      - name: scheduler
        image: my-custom-scheduler:v1.0
        args:
        - --scheduler-name=my-custom-scheduler
        - --leader-elect=false
```

**选择 Scheduler 时的注意事项:**
1. **Availability**: 如果指定的 scheduler 未运行，Pod 将不会被调度。
2. **Functionality**: 每个 scheduler 可以有不同的调度算法和策略。
3. **Resource isolation**: 可以使用不同的 scheduler 来隔离 workloads。
4. **Special hardware**: 可以为 GPU 或 FPGA 等特殊硬件使用专用 scheduler。

**检查 Scheduler 状态:**
```bash
# Check pod status
kubectl get pod custom-scheduled-pod

# Check scheduling events
kubectl describe pod custom-scheduled-pod | grep -A 5 Events

# Check scheduler logs
kubectl logs -n kube-system -l component=my-custom-scheduler
```

**其他选项的问题:**
- A. spec.scheduler: Kubernetes API 中不存在的字段。
- C. metadata.scheduler: Kubernetes API 中不存在的字段。
- D. spec.nodeName: 此字段用于绕过 scheduler 并将 Pod 直接分配给特定 Node。它不是用于指定 scheduler 的字段。
</details>
### 4. Kubernetes scheduling framework 中 "Filter" extension point 的作用是什么？

A. 对 Node 进行评分
B. 将 Pod 绑定到 Node
C. 排除 Pod 无法运行的 Node
D. 对 scheduling queue 中的 Pod 进行排序

<details>
<summary>显示答案</summary>

**答案: C. 排除 Pod 无法运行的 Node**

**解析:**
在 Kubernetes scheduling framework 中，"Filter" extension point（以前称为 "Predicate"）的作用是排除 Pod 无法运行的 Node。Filter plugins 会检查每个 Node 是否满足 Pod 的需求，并将不满足需求的 Node 从候选列表中排除。

**Scheduling Framework Extension Points:**
Scheduling framework 提供了多种 extension points，可以在调度周期的不同阶段集成 plugins:

1. **Queue Sort**: 决定 Pod 在 scheduling queue 中的顺序。
2. **PreFilter**: 在 filtering 之前对 Pod 和集群状态执行预处理。
3. **Filter**: 排除 Pod 无法运行的 Node。
4. **PreScore**: 执行 scoring 前所需的计算。
5. **Score**: 为通过 filtering 的 Node 分配分数。
6. **NormalizeScore**: 规范化每个 scoring plugin 的分数。
7. **Reserve**: 在所选 Node 上为 Pod 预留资源。
8. **Permit**: 允许、拒绝或延迟 Pod 调度。
9. **PreBind**: 执行 binding 前所需的工作。
10. **Bind**: 将 Pod 绑定到 Node。
11. **PostBind**: 在 binding 后执行清理工作。

**默认 Filter Plugins:**
Kubernetes 提供以下默认 filter plugins:

1. **NodeResourcesFit**: 检查 Node 是否有足够资源满足 Pod 的 resource requests。
2. **NodeName**: 检查 Pod 的 spec.nodeName 字段是否匹配 Node 名称。
3. **NodeUnschedulable**: 检查 Node 是否被标记为不可调度。
4. **TaintToleration**: 检查 Pod 是否 tolerates Node 的 taints。
5. **NodeAffinity**: 检查是否满足 Pod 的 node affinity 要求。
6. **PodAffinity**: 检查是否满足 Pod 的 pod affinity 要求。
7. **VolumeRestrictions**: 检查 volume 约束。
8. **EBSLimits**: 检查 Amazon EBS volume 限制。
9. **NoVolumeZoneConflict**: 检查 volume zone 约束。
10. **CheckNodeMemoryPressure**: 检查 Node memory pressure 状态。
11. **CheckNodeDiskPressure**: 检查 Node disk pressure 状态。

**Custom Filter Plugin 示例:**
```go
// Custom filter plugin example
type MyFilterPlugin struct{}

func (pl *MyFilterPlugin) Name() string {
    return "MyFilterPlugin"
}

// Filter method implementation
func (pl *MyFilterPlugin) Filter(ctx context.Context, state *framework.CycleState, pod *v1.Pod, nodeInfo *framework.NodeInfo) *framework.Status {
    // Check if the node meets certain conditions
    node := nodeInfo.Node()
    if node == nil {
        return framework.NewStatus(framework.Error, "node not found")
    }

    // Example: Only allow nodes with a specific label
    if value, exists := node.Labels["custom-label"]; !exists || value != "required-value" {
        return framework.NewStatus(framework.Unschedulable, "node does not have required label")
    }

    return nil // Returning nil means the node is suitable
}
```

**在 Scheduler 配置中启用 Filter Plugin:**
```yaml
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
profiles:
- schedulerName: custom-scheduler
  plugins:
    filter:
      enabled:
      - name: MyFilterPlugin
      disabled:
      - name: NodeResourcesFit  # Disable default plugin
```

**其他选项的问题:**
- A. 对 Node 进行评分: 这是 "Score" extension point 的作用。
- B. 将 Pod 绑定到 Node: 这是 "Bind" extension point 的作用。
- D. 对 scheduling queue 中的 Pod 进行排序: 这是 "Queue Sort" extension point 的作用。
</details>

### 5. 以下哪一项不是实现 Custom Scheduler 时需要考虑的内容？

A. Node 资源使用情况
B. Pod 优先级和抢占
C. Container image 大小
D. Node affinity 和 anti-affinity

<details>
<summary>显示答案</summary>

**答案: C. Container image 大小**

**解析:**
Container image 大小通常不是实现 Custom Scheduler 时需要考虑的内容。Image 大小影响的是 image 下载和 container 启动时间，而不是调度决策；这些由 kubelet 和 container runtime 负责。

**实现 Custom Scheduler 时的关键考虑事项:**

1. **Node 资源使用情况**:
   - CPU、memory、disk、network 等资源使用情况
   - 根据当前使用情况和 requests 进行最优放置
   - Resource overcommit policy

   ```go
   // Resource usage based filtering example
   func filterByResourceUsage(pod *v1.Pod, node *v1.Node) bool {
       // Check node's allocatable resources
       allocatable := node.Status.Allocatable
       // Calculate sum of resource requests for pods running on the node
       // Check if new pod's resource requests exceed available resources
       return podFitsResources(pod, allocatable, usedResources)
   }
   ```

2. **Pod 优先级和抢占**:
   - 优先调度更高优先级的 Pod
   - 必要时抢占较低优先级的 Pod
   - 考虑 PriorityClass 和 preemptionPolicy

   ```yaml
   # Priority class example
   apiVersion: scheduling.k8s.io/v1
   kind: PriorityClass
   metadata:
     name: high-priority
   value: 1000000
   globalDefault: false
   description: "High priority pods"
   ```

3. **Node affinity 和 anti-affinity**:
   - 满足 Pod 的 nodeSelector、nodeAffinity 要求
   - 应用 inter-pod affinity 和 anti-affinity 规则
   - 考虑 topology spread constraints

   ```yaml
   # Node affinity example
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
             - key: kubernetes.io/e2e-az-name
               operator: In
               values:
               - e2e-az1
               - e2e-az2
   ```

4. **其他重要考虑事项**:
   - **Taints and tolerations**: 匹配 Node taints 和 Pod tolerations
   - **Topology spread**: 将 Pod 分散到不同 topology domains
   - **Node status**: Node 状态（Ready、MemoryPressure、DiskPressure 等）
   - **Workload characteristics**: batch、service、daemonset 等各种 workload 类型的需求
   - **Network topology**: Node 之间的 network latency 和 bandwidth
   - **Hardware characteristics**: GPU、FPGA 等特殊硬件需求

**与 container image 大小相关的考虑:**
通常，container image 大小不会出于以下原因直接影响调度决策:

1. **Image availability**: image 是否已缓存在 Node 上由 kubelet 处理，而不是 scheduler。
2. **Download time**: Image 下载发生在调度决策之后，并由 kubelet 负责。
3. **Storage usage**: Image 存储通常不包含在 Node allocatable resources 的计算中。

不过，在特殊情况下，可以实现一个考虑 image locality 的 custom scheduler。这可以通过优先选择已缓存该 image 的 Node 来帮助缩短启动时间。

**其他选项说明:**
- A. Node 资源使用情况: 调度决策中的重要因素，对选择能够满足 Pod resource requests 的 Node 至关重要。
- B. Pod 优先级和抢占: 在资源竞争期间决定哪些 Pod 先调度，以及必要时抢占哪些 Pod 很重要。
- D. Node affinity 和 anti-affinity: 对于处理 Pod 应该与特定 Node 或其他 Pod 一起调度或分开调度的约束很重要。
</details>
### 6. Kubernetes scheduling framework 中 "Score" extension point 的作用是什么？

A. 排除 Pod 无法运行的 Node
B. 对通过 filtering 的 Node 进行评分
C. 将 Pod 绑定到 Node
D. 对 scheduling queue 中的 Pod 进行排序

<details>
<summary>显示答案</summary>

**答案: B. 对通过 filtering 的 Node 进行评分**

**解析:**
在 Kubernetes scheduling framework 中，"Score" extension point（以前称为 "Priority"）的作用是为通过 filtering 的 Node 分配分数。Scoring plugins 会为每个 Node 分配分数，并根据这些分数选择最优 Node。

**Scoring 流程:**
1. 每个 scoring plugin 为每个 Node 计算一个分数（通常范围为 0-100）。
2. 每个 plugin 的分数根据配置的 weight 进行加权。
3. 汇总所有 plugins 的加权分数。
4. 选择总分最高的 Node 用于 Pod 放置。

**默认 Scoring Plugins:**
Kubernetes 提供以下默认 scoring plugins:

1. **NodeResourcesBalancedAllocation**: 给 CPU 和 memory 使用均衡的 Node 更高分数。
2. **NodeResourcesFit**: 根据相对于 requested resources 的可用资源多少，给 Node 更高分数。
3. **NodeAffinity**: 基于 node affinity 规则评分。
4. **InterPodAffinity**: 基于 inter-pod affinity/anti-affinity 规则评分。
5. **PodTopologySpread**: 给能让 Pod 在 topology domains 间均匀分布的 Node 更高分数。
6. **TaintToleration**: 给 taints 更少的 Node 更高分数。
7. **ImageLocality**: 给已经有所需 container images 的 Node 更高分数。

**Custom Scoring Plugin 示例:**
```go
// Custom scoring plugin example
type MyScorePlugin struct{}

func (pl *MyScorePlugin) Name() string {
    return "MyScorePlugin"
}

// Score method implementation
func (pl *MyScorePlugin) Score(ctx context.Context, state *framework.CycleState, pod *v1.Pod, nodeName string) (int64, *framework.Status) {
    // Get node info
    nodeInfo, err := pl.handle.SnapshotSharedLister().NodeInfos().Get(nodeName)
    if err != nil {
        return 0, framework.NewStatus(framework.Error, fmt.Sprintf("getting node %q from Snapshot: %v", nodeName, err))
    }

    node := nodeInfo.Node()

    // Example: Score based on specific label value
    if value, exists := node.Labels["custom-score-label"]; exists {
        score, err := strconv.ParseInt(value, 10, 64)
        if err != nil {
            return 0, framework.NewStatus(framework.Error, fmt.Sprintf("invalid score value: %v", err))
        }
        // Score range should be 0-100
        if score < 0 {
            score = 0
        } else if score > 100 {
            score = 100
        }
        return score, nil
    }

    return 0, nil
}

// ScoreExtensions interface implementation
func (pl *MyScorePlugin) ScoreExtensions() framework.ScoreExtensions {
    return pl
}

// NormalizeScore method implementation
func (pl *MyScorePlugin) NormalizeScore(ctx context.Context, state *framework.CycleState, pod *v1.Pod, scores framework.NodeScoreList) *framework.Status {
    // Score normalization logic
    var highest int64 = 0
    for _, nodeScore := range scores {
        if nodeScore.Score > highest {
            highest = nodeScore.Score
        }
    }

    if highest == 0 {
        return nil
    }

    // Adjust all scores relative to the highest score
    for i := range scores {
        scores[i].Score = scores[i].Score * 100 / highest
    }

    return nil
}
```

**在 Scheduler 配置中启用 Scoring Plugin 并设置 Weight:**
```yaml
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
profiles:
- schedulerName: custom-scheduler
  plugins:
    score:
      enabled:
      - name: MyScorePlugin
        weight: 5  # Set weight
      - name: NodeResourcesBalancedAllocation
        weight: 2  # Change default plugin weight
      disabled:
      - name: NodeResourcesFit  # Disable default plugin
```

**Scoring 结果示例:**
假设 Node A、B、C 通过了 filtering，并且有两个 scoring plugins:

1. MyScorePlugin (weight: 5)
   - Node A: 80 分
   - Node B: 60 分
   - Node C: 90 分

2. NodeResourcesBalancedAllocation (weight: 2)
   - Node A: 70 分
   - Node B: 90 分
   - Node C: 50 分

加权总分:
- Node A: (80 x 5) + (70 x 2) = 400 + 140 = 540 分
- Node B: (60 x 5) + (90 x 2) = 300 + 180 = 480 分
- Node C: (90 x 5) + (50 x 2) = 450 + 100 = 550 分

在这种情况下，Node C 得分最高，因此 Pod 被调度到 Node C。

**其他选项的问题:**
- A. 排除 Pod 无法运行的 Node: 这是 "Filter" extension point 的作用。
- C. 将 Pod 绑定到 Node: 这是 "Bind" extension point 的作用。
- D. 对 scheduling queue 中的 Pod 进行排序: 这是 "Queue Sort" extension point 的作用。
</details>

### 7. 以下哪一项不是在 Kubernetes 中扩展 scheduler 的方法？

A. Scheduling framework plugin
B. Scheduler extender
C. 部署多个 scheduler
D. 修改 node controller

<details>
<summary>显示答案</summary>

**答案: D. 修改 node controller**

**解析:**
修改 node controller 不是在 Kubernetes 中扩展 scheduler 的方法。node controller 是一个 control plane 组件，用于监控和管理 Node 状态，与调度决策没有直接关系。

**在 Kubernetes 中扩展 Scheduler 的方法:**

1. **Scheduling framework plugin**:
   - 在 Kubernetes 1.15 中引入，允许在调度周期的各个阶段插入 plugins。
   - 提供 filter、score、bind 等 extension points。
   - 为提高效率，直接与 scheduler codebase 集成。

   ```go
   // Scheduling framework plugin registration example
   func NewPlugin(args runtime.Object, handle framework.Handle) (framework.Plugin, error) {
       // Parse plugin configuration
       config, ok := args.(*Config)
       if !ok {
           return nil, fmt.Errorf("want args to be of type Config, got %T", args)
       }

       // Create plugin instance
       return &Plugin{
           handle: handle,
           config: config,
       }, nil
   }

   // Plugin interface implementation
   type Plugin struct {
       handle framework.Handle
       config *Config
   }

   func (pl *Plugin) Name() string { return "MyPlugin" }

   // Implement required extension point methods
   func (pl *Plugin) Filter(...) { ... }
   func (pl *Plugin) Score(...) { ... }
   ```

2. **Scheduler extender**:
   - 通过外部 HTTP service 扩展 scheduler 功能。
   - 可以扩展 filtering、prioritization、binding 阶段。
   - 因为它与 scheduler 分开运行，可能产生性能开销。

   ```yaml
   # Scheduler extender configuration example
   apiVersion: kubescheduler.config.k8s.io/v1
   kind: KubeSchedulerConfiguration
   profiles:
   - schedulerName: default-scheduler
     extenders:
     - urlPrefix: "http://extender-service:8080"
       filterVerb: "filter"
       prioritizeVerb: "prioritize"
       weight: 5
       bindVerb: "bind"
       enableHTTPS: false
   ```

3. **部署多个 scheduler**:
   - 将 custom schedulers 与默认 scheduler 一起部署。
   - 每个 scheduler 独立运行，Pod 可以通过 `spec.schedulerName` 指定特定 scheduler。
   - 提供完全灵活性，但实现和维护可能较复杂。

   ```yaml
   # Custom scheduler deployment example
   apiVersion: apps/v1
   kind: Deployment
   metadata:
     name: my-custom-scheduler
     namespace: kube-system
   spec:
     replicas: 1
     selector:
       matchLabels:
         component: my-custom-scheduler
     template:
       metadata:
         labels:
           component: my-custom-scheduler
       spec:
         serviceAccountName: my-custom-scheduler
         containers:
         - name: scheduler
           image: my-custom-scheduler:v1.0
           args:
           - --scheduler-name=my-custom-scheduler
           - --leader-elect=false
   ```

**Node Controller 的作用:**
node controller 是一个 control plane 组件，执行以下职责:
- Node 注册和状态监控
- Node 状态更新（Ready、NotReady 等）
- 根据 Node 状态移除 Pod（当 Node 长时间处于 NotReady 时）
- Node lifecycle management

node controller 不直接参与调度决策；它会更新 scheduler 使用的 Node 信息。因此，修改 node controller 不是扩展 scheduler 的方法。

**选择 Scheduler 扩展方法时的注意事项:**
1. **Complexity**: Scheduling framework plugins 实现起来可能复杂，但与 scheduler 紧密集成。
2. **Performance**: Scheduler extenders 可能有 HTTP 调用开销，会影响性能。
3. **Maintenance**: 多个 schedulers 需要维护独立的 codebases。
4. **Upgrades**: Kubernetes 升级时可能出现兼容性问题。
5. **Features**: 每种方法提供不同级别的功能和灵活性。

**其他选项说明:**
- A. Scheduling framework plugin: 有效的 scheduler 扩展方法。
- B. Scheduler extender: 有效的 scheduler 扩展方法。
- C. 部署多个 scheduler: 有效的 scheduler 扩展方法。
</details>
### 8. Kubernetes scheduler 中 `--leader-elect` flag 的用途是什么？

A. 授予 scheduler 领导权限
B. 在多个 scheduler instances 中只激活一个 instance
C. 仅在集群的 leader Node 上运行 scheduler
D. 赋予 scheduler 比其他组件更高的优先级

<details>
<summary>显示答案</summary>

**答案: B. 在多个 scheduler instances 中只激活一个 instance**

**解析:**
Kubernetes scheduler 中 `--leader-elect` flag 的用途是，在 high availability (HA) 配置中确保只有一个 scheduler instance 处于活跃状态并执行工作。这可以防止多个 scheduler instances 同时工作时可能发生的冲突和 race conditions。

**Leader Election 机制:**
1. 部署多个 scheduler instances 时，leader election 算法只选举一个 instance 作为 leader。
2. 只有被选为 leader 的 instance 执行实际调度工作。
3. 其他 instances 保持 standby mode，如果当前 leader 失败，会选举新的 leader。
4. 该机制使用 Kubernetes resource locks 实现。

**Leader Election 相关 Flags:**
```
--leader-elect=true                      # Whether to enable leader election (default: true)
--leader-elect-lease-duration=15s        # Leadership lease duration
--leader-elect-renew-deadline=10s        # Leadership renewal deadline
--leader-elect-retry-period=2s           # Leadership retry period
--leader-elect-resource-lock=leases      # Resource type to use for leadership lock
--leader-elect-resource-name=kube-scheduler  # Leadership lock resource name
--leader-elect-resource-namespace=kube-system  # Leadership lock resource namespace
```

**High Availability Scheduler 部署示例:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: kube-scheduler
  namespace: kube-system
spec:
  replicas: 3  # Deploy multiple instances
  selector:
    matchLabels:
      component: kube-scheduler
  template:
    metadata:
      labels:
        component: kube-scheduler
    spec:
      containers:
      - name: kube-scheduler
        image: k8s.gcr.io/kube-scheduler:v1.23.0
        command:
        - kube-scheduler
        - --leader-elect=true  # Enable leader election
        - --leader-elect-lease-duration=15s
        - --leader-elect-renew-deadline=10s
        - --leader-elect-retry-period=2s
```

**检查 Leader Election 状态:**
```bash
# Check leadership resource
kubectl get leases -n kube-system | grep kube-scheduler

# Check leadership details
kubectl describe lease kube-scheduler -n kube-system

# Check leadership related messages in scheduler logs
kubectl logs -n kube-system -l component=kube-scheduler | grep -i leader
```

**Custom Scheduler 中的 Leader Election:**
实现 custom scheduler 时，可以使用相同的 leader election 机制。这会使用 client-go library 中的 leaderelection package。

```go
// Leader election implementation example in custom scheduler
import (
    "context"
    "time"

    metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
    clientset "k8s.io/client-go/kubernetes"
    "k8s.io/client-go/tools/leaderelection"
    "k8s.io/client-go/tools/leaderelection/resourcelock"
)

func runWithLeaderElection(ctx context.Context, client clientset.Interface, schedulerName string) {
    // Leader election configuration
    lock := &resourcelock.LeaseLock{
        LeaseMeta: metav1.ObjectMeta{
            Name:      schedulerName,
            Namespace: "kube-system",
        },
        Client: client.CoordinationV1(),
        LockConfig: resourcelock.ResourceLockConfig{
            Identity: schedulerName + "-" + uuid.New().String(),
        },
    }

    // Execute leader election
    leaderelection.RunOrDie(ctx, leaderelection.LeaderElectionConfig{
        Lock:            lock,
        ReleaseOnCancel: true,
        LeaseDuration:   15 * time.Second,
        RenewDeadline:   10 * time.Second,
        RetryPeriod:     2 * time.Second,
        Callbacks: leaderelection.LeaderCallbacks{
            OnStartedLeading: func(ctx context.Context) {
                // Execute scheduler logic when becoming leader
                runScheduler(ctx)
            },
            OnStoppedLeading: func() {
                // Handle when leadership is lost
                log.Printf("Lost leadership, shutting down")
                os.Exit(0)
            },
            OnNewLeader: func(identity string) {
                // Handle when a new leader is elected
                log.Printf("New leader elected: %s", identity)
            },
        },
    })
}
```

**应禁用 Leader Election 的情况:**
1. **Single instance deployment**: 当 scheduler 只部署为一个 instance 时
2. **Using a different leader election mechanism**: 当外部 orchestration tool 管理 instance 激活时
3. **Different scheduler names**: 当每个 scheduler instance 使用不同的 `schedulerName` 时

在这些情况下，可以通过设置 `--leader-elect=false` 来禁用 leader election。

**其他选项的问题:**
- A. 授予 scheduler 领导权限: 这是模糊描述，没有解释 leader election 的具体用途。
- C. 仅在集群的 leader Node 上运行 scheduler: Kubernetes 中没有 "leader node" 的概念；scheduler 运行在 control plane nodes 上。
- D. 赋予 scheduler 比其他组件更高的优先级: Leader election 与优先级无关；它用于多个 scheduler instances 之间的协调。
</details>

### 9. Kubernetes 中用于设置 Pod 调度优先级的资源是什么？

A. PodSchedulingPolicy
B. PriorityClass
C. SchedulingPriority
D. PodPriority

<details>
<summary>显示答案</summary>

**答案: B. PriorityClass**

**解析:**
Kubernetes 中用于设置 Pod 调度优先级的资源是 `PriorityClass`。PriorityClass 定义 Pod 的相对重要性，使 scheduler 在做出调度和抢占决策时可以考虑优先级。

**PriorityClass 资源:**
```yaml
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: high-priority
value: 1000000  # Priority value (higher value means higher priority)
globalDefault: false  # Whether to use this class as the default
description: "High priority pods"  # Description
preemptionPolicy: PreemptLowerPriority  # Preemption policy (default: PreemptLowerPriority)
```

**关键字段:**
1. **value**: 优先级值；值越大表示优先级越高。System Pods 通常使用 1000000000（10 亿）或更高的值。
2. **globalDefault**: 设置为 true 时，此 priority class 会应用到未指定 priority class 的 Pod。
3. **description**: priority class 的描述。
4. **preemptionPolicy**: 抢占策略，可设置为 `PreemptLowerPriority`（默认）或 `Never`。

**将 PriorityClass 应用于 Pod:**
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: high-priority-pod
spec:
  priorityClassName: high-priority  # Reference PriorityClass name
  containers:
  - name: nginx
    image: nginx
```

**Priority 和 Preemption 行为:**
1. **Scheduling priority**: 更高优先级的 Pod 会在 scheduling queue 中先处理。
2. **Preemption**: 当没有 Node 可以调度高优先级 Pod 时，scheduler 可以移除（抢占）较低优先级的 Pod 以释放空间。
3. **Preemption policy**: 使用带有 `preemptionPolicy: Never` 的 PriorityClass 的 Pod 不会抢占其他 Pod。

**System PriorityClasses:**
Kubernetes 提供以下 system PriorityClasses:
- **system-cluster-critical**: 用于对集群运行至关重要的 Pod（value: 2000000000）
- **system-node-critical**: 用于对 Node 运行至关重要的 Pod（value: 2000001000）

```bash
# Check system PriorityClasses
kubectl get priorityclasses | grep system
```

**PriorityClass 使用示例:**
```yaml
# Define multiple priority classes
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: high-priority
value: 1000000
globalDefault: false
description: "High priority pods"
---
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: medium-priority
value: 100000
globalDefault: true
description: "Medium priority pods"
---
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: low-priority
value: 10000
globalDefault: false
description: "Low priority pods"
preemptionPolicy: Never  # Do not preempt
```

**监控 Priority 和 Preemption 相关指标:**
```bash
# Check preemption events
kubectl get events | grep -i preempt

# Check pod priorities
kubectl get pods -o custom-columns=NAME:.metadata.name,PRIORITY:.spec.priority
```

**在 Custom Scheduler 中处理 Priority:**
实现 custom scheduler 时，在做出调度决策时应考虑 Pod 优先级。

```go
// Pod priority check example
func getPodPriority(pod *v1.Pod) int32 {
    if pod.Spec.Priority != nil {
        return *pod.Spec.Priority
    }
    return 0
}

// Priority-based pod sorting example
func sortPodsByPriority(pods []*v1.Pod) {
    sort.Slice(pods, func(i, j int) bool {
        return getPodPriority(pods[i]) > getPodPriority(pods[j])
    })
}
```

**其他选项的问题:**
- A. PodSchedulingPolicy: Kubernetes API 中不存在的资源。
- C. SchedulingPriority: Kubernetes API 中不存在的资源。
- D. PodPriority: 这不是资源类型，而是 Pod spec 中的字段（`spec.priority`）。此字段会由 PriorityClass 自动设置。
</details>

### 10. Kubernetes scheduler 的 `NodeResourcesFit` plugin 的作用是什么？

A. 根据 Node 的物理位置放置 Pod
B. 比较 Node resource capacity 和 Pod resource requests
C. 检查 Node operating system 与 Pod 的兼容性
D. 测量 Node network bandwidth

<details>
<summary>显示答案</summary>

**答案: B. 比较 Node resource capacity 和 Pod resource requests**

**解析:**
Kubernetes scheduler 的 `NodeResourcesFit` plugin 的作用是比较 Node resource capacity 和 Pod resource requests，以检查 Pod 是否可以在该 Node 上运行。此 plugin 会考虑 CPU、memory、ephemeral storage 和 extended resources（GPU 等）在内的各种 resource types。

**NodeResourcesFit Plugin 的主要功能:**
1. **Resource request verification**: 检查 Pod 的 resource requests 是否不超过 Node 的 allocatable resources。
2. **Resource limit verification**: 检查 Pod 的 resource limits 是否不超过 Node 的 capacity。
3. **Extended resource verification**: 检查 GPU、FPGA 等 extended resource requests 在 Node 上是否可用。
4. **Scoring**: 基于资源使用情况，为通过 filtering 阶段的 Node 分配分数。

**资源验证流程:**
1. 汇总 Pod 中所有 containers 的 resource requests。
2. 检查 Node 的 allocatable resources。
3. 检查 Pod 的 resource requests 是否不超过 Node 的 allocatable resources。
4. 如果超过，该 Node 会被过滤掉。

**Scheduler 中的 NodeResourcesFit 配置:**
```yaml
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
profiles:
- schedulerName: default-scheduler
  plugins:
    filter:
      enabled:
      - name: NodeResourcesFit
    score:
      enabled:
      - name: NodeResourcesFit
        weight: 1
  pluginConfig:
  - name: NodeResourcesFit
    args:
      scoringStrategy:
        type: MostAllocated  # or LeastAllocated, RequestedToCapacityRatio
        resources:
        - name: cpu
          weight: 1
        - name: memory
          weight: 1
```

**Scoring Strategies:**
NodeResourcesFit plugin 支持以下 scoring strategies:

1. **LeastAllocated**: 给已使用资源较少的 Node 更高分数。这适用于分散资源使用。
   ```
   score = (capacity - requested) / capacity
   ```

2. **MostAllocated**: 给已使用资源较多的 Node 更高分数。这适用于集中资源使用，以最小化 Node 数量。
   ```
   score = requested / capacity
   ```

3. **RequestedToCapacityRatio**: 使用自定义函数根据 requested resources 与 capacity 的比率分配分数。

**Resource Types:**
NodeResourcesFit plugin 会考虑以下 resource types:

1. **CPU**: 以 cores 或 millicores 度量。
2. **Memory**: 以 bytes 度量。
3. **Ephemeral storage**: Node 的本地 ephemeral storage。
4. **Extended resources**: GPU、FPGA 等 custom resources。

**检查 Node Resources:**
```bash
# Check node's allocatable resources
kubectl describe node <node-name> | grep Allocatable -A 5

# Check node's resource usage
kubectl top node <node-name>
```

**检查 Pod Resource Requests:**
```bash
# Check pod's resource requests
kubectl get pod <pod-name> -o jsonpath='{.spec.containers[*].resources.requests}'
```

**在 Custom Scheduler 中实现 Resource Fit Check:**
```go
// Node resource fit check example
func checkNodeResourcesFit(pod *v1.Pod, node *v1.Node) bool {
    // Get node's allocatable resources
    allocatable := node.Status.Allocatable

    // Calculate pod's resource requests
    var requestedCPU, requestedMemory resource.Quantity
    for _, container := range pod.Spec.Containers {
        if request, ok := container.Resources.Requests[v1.ResourceCPU]; ok {
            requestedCPU.Add(request)
        }
        if request, ok := container.Resources.Requests[v1.ResourceMemory]; ok {
            requestedMemory.Add(request)
        }
    }

    // Calculate resources already in use on the node
    // (In actual implementation, sum resource requests of all pods running on the node)

    // Check resource fit
    if allocatableCPU, ok := allocatable[v1.ResourceCPU]; ok {
        if requestedCPU.Cmp(allocatableCPU) > 0 {
            return false  // CPU request exceeds allocatable amount
        }
    }

    if allocatableMemory, ok := allocatable[v1.ResourceMemory]; ok {
        if requestedMemory.Cmp(allocatableMemory) > 0 {
            return false  // Memory request exceeds allocatable amount
        }
    }

    return true  // All resource requests are satisfied
}
```

**其他选项的问题:**
- A. 根据 Node 的物理位置放置 Pod: 这是 topology 相关 plugins（例如 NodeAffinity、PodTopologySpread）的作用。
- C. 检查 Node operating system 与 Pod 的兼容性: 这是通过 NodeSelector 或 NodeAffinity 处理的，而不是单独的 plugin。
- D. 测量 Node network bandwidth: Kubernetes scheduler 默认不考虑 network bandwidth。需要 custom metrics 和 plugins 来实现这一点。
</details>
