# Custom Scheduler 测验（Part 3）

本测验测试你对在 Kubernetes 中实现和使用 Custom Scheduler 的高级理解。

## 测验问题

### 1. 在 Kubernetes 中同时运行多个 scheduler 时，以下哪一项不是可能出现的问题？

A. 资源竞争
B. 调度决策冲突
C. 网络带宽增加
D. Leader election 冲突

<details>
<summary>显示答案</summary>

**答案：C. 网络带宽增加**

**解释：**
“网络带宽增加”不是在 Kubernetes 中同时运行多个 scheduler 时可能出现的问题。虽然 scheduler 会与 API server 通信，但网络带宽使用量通常很小，并不是一个需要担心的问题。

**同时运行多个 scheduler 时可能出现的实际问题：**

1. **资源竞争**：
   - 当多个 scheduler 尝试将 Pod 调度到同一个 node pool 时，可能发生资源竞争。
   - 由于每个 scheduler 都独立运行，不了解其他 scheduler 的决策，因此存在过度分配 Node 资源的风险。
   - 示例：两个 scheduler 可能同时将 Pod 调度到同一个 Node，导致超过 Node 容量。

2. **调度决策冲突**：
   - 当多个 scheduler 尝试调度同一个 Pod 时，可能发生冲突。
   - 当 Pod 没有显式指定 `schedulerName`，或者多个 scheduler 使用相同名称时，可能会发生这种情况。
   - 示例：当两个 scheduler 尝试将同一个 Pod 绑定到不同 Node 时，会发生竞争条件。

3. **Leader election 冲突**：
   - 如果多个同名 scheduler 实例在启用 leader election 的情况下运行，leader election 机制中可能会发生冲突。
   - 示例：多个同名 scheduler 实例竞争 leadership，可能导致不稳定的 leadership 转换。

**运行多个 scheduler 时的最佳实践：**

1. **明确划分职责**：
   ```yaml
   # Pod for default scheduler
   apiVersion: v1
   kind: Pod
   metadata:
     name: default-pod
   spec:
     # Uses default scheduler when schedulerName is not specified
     containers:
     - name: nginx
       image: nginx

   # Pod for custom scheduler
   apiVersion: v1
   kind: Pod
   metadata:
     name: custom-pod
   spec:
     schedulerName: my-custom-scheduler  # Specify custom scheduler
     containers:
     - name: nginx
       image: nginx
   ```

2. **使用唯一的 scheduler 名称**：
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
         containers:
         - name: scheduler
           image: my-custom-scheduler:v1.0
           args:
           - --scheduler-name=my-custom-scheduler  # Use unique name
           - --leader-elect=true
           - --leader-elect-resource-name=my-custom-scheduler  # Use unique resource name
   ```

3. **使用 Node label 和 taint 分离 node pool**：
   ```yaml
   # Apply node labels and taints
   kubectl label node node1 scheduler=default
   kubectl label node node2 scheduler=custom

   kubectl taint nodes node2 dedicated=custom-scheduler:NoSchedule

   # Custom scheduler configuration
   apiVersion: kubescheduler.config.k8s.io/v1
   kind: KubeSchedulerConfiguration
   profiles:
   - schedulerName: my-custom-scheduler
     plugins:
       filter:
         enabled:
         - name: NodeSelector
     pluginConfig:
     - name: NodeSelector
       args:
         nodeSelector:
           scheduler: custom
   ```

4. **设置 resource quota**：
   ```yaml
   apiVersion: v1
   kind: ResourceQuota
   metadata:
     name: default-scheduler-quota
     namespace: default-workloads
   spec:
     hard:
       pods: "10"
       cpu: "20"
       memory: 40Gi

   ---
   apiVersion: v1
   kind: ResourceQuota
   metadata:
     name: custom-scheduler-quota
     namespace: custom-workloads
   spec:
     hard:
       pods: "10"
       cpu: "20"
       memory: 40Gi
   ```

**监控多个 scheduler：**
```bash
# Check scheduler pods
kubectl get pods -n kube-system -l component=kube-scheduler
kubectl get pods -n kube-system -l component=my-custom-scheduler

# Check scheduler logs
kubectl logs -n kube-system -l component=kube-scheduler
kubectl logs -n kube-system -l component=my-custom-scheduler

# Check scheduling events
kubectl get events | grep -i "Successfully assigned"
```

**其他选项的解释：**
- A. 资源竞争：当多个 scheduler 将 Pod 调度到同一个 node pool 时，可能出现的实际问题。
- B. 调度决策冲突：当多个 scheduler 尝试调度同一个 Pod 时，可能出现的实际问题。
- D. Leader election 冲突：当多个同名 scheduler 实例竞争 leadership 时，可能出现的实际问题。
</details>

### 2. Kubernetes scheduler 中 “Permit” extension point 的作用是什么？

A. 将 Pod 绑定到 Node
B. 允许、拒绝或延迟 Pod 调度
C. 排除 Pod 无法运行的 Node
D. 为 Node 分配分数

<details>
<summary>显示答案</summary>

**答案：B. 允许、拒绝或延迟 Pod 调度**

**解释：**
Kubernetes scheduling framework 中 “Permit” extension point 的作用是允许、拒绝或延迟 Pod 调度。Permit plugin 会在选定 Node 之后、binding phase 之前运行，为 Pod 调度决策提供最终批准或拒绝。

**Permit extension point 的关键功能：**
1. **允许**：允许 Pod 调度进入 binding phase。
2. **拒绝**：拒绝 Pod 调度，以便可以选择另一个 Node。
3. **等待**：临时延迟 Pod 调度，并等待直到满足特定条件。

**Permit plugin interface：**
```go
type PermitPlugin interface {
    Plugin
    // Permit allows, denies, or delays pod scheduling.
    // Return values:
    // - Success: Allows pod scheduling.
    // - Deny: Rejects pod scheduling.
    // - Wait: Delays pod scheduling and waits until timeout or allowed.
    Permit(ctx context.Context, state *CycleState, pod *v1.Pod, nodeName string) (*Status, time.Duration)
}
```

**Permit 结果类型：**
1. **Success**：允许 Pod 调度。
2. **Deny**：拒绝 Pod 调度。
3. **Wait**：延迟 Pod 调度，并等待指定时间。

**默认 Permit plugin：**
Kubernetes 提供以下默认 Permit plugin：

1. **TaintToleration**：检查 Node taint 和 Pod toleration。
2. **PodTopologySpread**：检查 Pod topology spread constraint。

**Custom Permit plugin 示例：**
```go
// CustomPermit implements custom permit logic.
type CustomPermit struct {
    handle framework.Handle
    // Map to track waiting pods
    waitingPods map[string]waitingPod
    // Mutex to synchronize map access
    mu sync.RWMutex
}

// waitingPod stores information about waiting pods.
type waitingPod struct {
    pod      *v1.Pod
    nodeName string
    status   chan bool  // true: allow, false: deny
}

// Name returns the plugin name.
func (pl *CustomPermit) Name() string {
    return "CustomPermit"
}

// Permit allows, denies, or delays pod scheduling.
func (pl *CustomPermit) Permit(ctx context.Context, state *framework.CycleState, pod *v1.Pod, nodeName string) (*framework.Status, time.Duration) {
    // Example: Allow, deny, or delay pod scheduling based on specific conditions
    if shouldWait(pod, nodeName) {
        // Add pod to waiting list
        key := fmt.Sprintf("%s/%s", pod.Namespace, pod.Name)

        pl.mu.Lock()
        if pl.waitingPods == nil {
            pl.waitingPods = make(map[string]waitingPod)
        }
        pl.waitingPods[key] = waitingPod{
            pod:      pod,
            nodeName: nodeName,
            status:   make(chan bool),
        }
        pl.mu.Unlock()

        // Wait for up to 10 minutes
        return framework.NewStatus(framework.Wait, "waiting for condition"), 10 * time.Minute
    }

    if shouldDeny(pod, nodeName) {
        return framework.NewStatus(framework.Unschedulable, "denied by custom permit plugin"), 0
    }

    // Allow pod scheduling
    return nil, 0
}

// Allow waiting pod
func (pl *CustomPermit) Allow(pod *v1.Pod) {
    key := fmt.Sprintf("%s/%s", pod.Namespace, pod.Name)

    pl.mu.RLock()
    waitingPod, ok := pl.waitingPods[key]
    pl.mu.RUnlock()

    if ok {
        // Allow pod
        waitingPod.status <- true

        pl.mu.Lock()
        delete(pl.waitingPods, key)
        pl.mu.Unlock()
    }
}

// Reject waiting pod
func (pl *CustomPermit) Reject(pod *v1.Pod) {
    key := fmt.Sprintf("%s/%s", pod.Namespace, pod.Name)

    pl.mu.RLock()
    waitingPod, ok := pl.waitingPods[key]
    pl.mu.RUnlock()

    if ok {
        // Reject pod
        waitingPod.status <- false

        pl.mu.Lock()
        delete(pl.waitingPods, key)
        pl.mu.Unlock()
    }
}

// Function to check if pod should wait
func shouldWait(pod *v1.Pod, nodeName string) bool {
    // Implement custom logic
    return false
}

// Function to check if pod should be denied
func shouldDeny(pod *v1.Pod, nodeName string) bool {
    // Implement custom logic
    return false
}
```

**在 scheduler configuration 中启用 Permit plugin：**
```yaml
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
profiles:
- schedulerName: custom-scheduler
  plugins:
    permit:
      enabled:
      - name: CustomPermit
      disabled:
      - name: TaintToleration  # Disable default plugin
```

**Permit 使用场景：**
1. **Gang scheduling**：延迟调度一组 Pod，直到所有相关 Pod 都准备好被调度。
2. **Resource reservation**：在 Pod 被调度之前预留外部资源。
3. **Policy validation**：确保 Pod 调度符合组织策略。
4. **Approval workflow**：请求外部批准 Pod 调度。

**Gang scheduling 示例：**
Gang scheduling 是一种确保所有相关 Pod 一起被调度的技术。这对于分布式训练作业等工作负载很有用，因为所有组件都必须同时运行。

```go
// GangPermit implements Gang scheduling.
type GangPermit struct {
    handle framework.Handle
    // Map to track waiting pods by group
    waitingGroups map[string]gangGroup
    mu sync.RWMutex
}

// gangGroup stores Gang information.
type gangGroup struct {
    pods      map[string]*v1.Pod
    nodeName  map[string]string
    minCount  int
    readyPods int
}

// Permit allows, denies, or delays pod scheduling.
func (pl *GangPermit) Permit(ctx context.Context, state *framework.CycleState, pod *v1.Pod, nodeName string) (*framework.Status, time.Duration) {
    // Get Gang ID
    gangID, ok := pod.Labels["gang-id"]
    if !ok {
        // Process as regular pod if no Gang ID
        return nil, 0
    }

    pl.mu.Lock()
    defer pl.mu.Unlock()

    // Create group if not exists
    if _, ok := pl.waitingGroups[gangID]; !ok {
        minCount, _ := strconv.Atoi(pod.Labels["gang-min-count"])
        if minCount <= 0 {
            minCount = 1
        }

        pl.waitingGroups[gangID] = gangGroup{
            pods:      make(map[string]*v1.Pod),
            nodeName:  make(map[string]string),
            minCount:  minCount,
            readyPods: 0,
        }
    }

    // Add pod
    group := pl.waitingGroups[gangID]
    key := fmt.Sprintf("%s/%s", pod.Namespace, pod.Name)
    group.pods[key] = pod
    group.nodeName[key] = nodeName
    group.readyPods++

    // Check if minimum count reached
    if group.readyPods >= group.minCount {
        // Allow all pods
        for _, p := range group.pods {
            pl.handle.PermitPlugin().Allow(p)
        }

        // Delete group
        delete(pl.waitingGroups, gangID)

        return nil, 0
    }

    // Wait until minimum count is reached
    return framework.NewStatus(framework.Wait, "waiting for gang members"), 10 * time.Minute
}
```

**其他选项的问题：**
- A. 将 Pod 绑定到 Node：这是 “Bind” extension point 的作用。
- C. 排除 Pod 无法运行的 Node：这是 “Filter” extension point 的作用。
- D. 为 Node 分配分数：这是 “Score” extension point 的作用。
</details>
### 3. Kubernetes 中 Gang Scheduling 的主要目的是什么？

A. 只将 Pod 放置在特定 Node 上
B. 确保所有相关 Pod 一起被调度
C. 将 Pod 均匀分布到各个 Node 上
D. 基于优先级调度 Pod

<details>
<summary>显示答案</summary>

**答案：B. 确保所有相关 Pod 一起被调度**

**解释：**
Kubernetes 中 Gang Scheduling 的主要目的是确保所有相关 Pod 一起被调度。这对于分布式训练作业和分布式数据处理作业等工作负载很重要，因为所有组件都必须同时运行。

**为什么需要 Gang scheduling：**
1. **All-or-Nothing 要求**：某些工作负载要求所有组件同时运行；如果只有部分组件运行，作业就无法推进。
2. **防止资源浪费**：如果只有部分 Pod 被调度而其他 Pod 仍在等待，已调度 Pod 使用的资源可能会被浪费。
3. **防止 deadlock**：当相互依赖的 Pod 在不同时间被调度时，可能发生 deadlock。

**Gang scheduling 实现方法：**
Kubernetes 本身不原生支持 Gang scheduling，但可以通过以下方式实现：

1. **Custom scheduler**：使用 Permit extension point 实现 Gang scheduling。
2. **外部 controller**：实现一个在 Kubernetes 外部管理 Gang scheduling 的 controller。
3. **开源解决方案**：使用 Volcano 或 Kube-batch 等开源 scheduler。

**Gang scheduling 示例（Volcano）：**
```yaml
# PodGroup definition for Gang scheduling
apiVersion: scheduling.volcano.sh/v1beta1
kind: PodGroup
metadata:
  name: tf-training
  namespace: default
spec:
  minMember: 4  # At least 4 pods must be scheduled together
  minResources:
    cpu: 8
    memory: 16Gi
  queue: default

---
# Pod belonging to Gang
apiVersion: v1
kind: Pod
metadata:
  name: tf-worker-0
  namespace: default
  labels:
    app: tf-training
  annotations:
    scheduling.volcano.sh/pod-group: tf-training  # Reference PodGroup
spec:
  schedulerName: volcano  # Use Volcano scheduler
  containers:
  - name: tensorflow
    image: tensorflow/tensorflow:latest-gpu
    resources:
      requests:
        cpu: 2
        memory: 4Gi
        nvidia.com/gpu: 1
```

**使用 custom Permit plugin 实现 Gang scheduling：**
```go
// GangSchedulingPlugin implements Gang scheduling.
type GangSchedulingPlugin struct {
    handle framework.Handle
    // Pod tracking per Gang
    gangs map[string]*Gang
    mu sync.RWMutex
}

// Gang represents a group of related pods.
type Gang struct {
    MinRequired int
    Scheduled   map[string]string  // pod name -> node name
    Waiting     map[string]*framework.WaitingPod
}

// Name returns the plugin name.
func (pl *GangSchedulingPlugin) Name() string {
    return "GangSchedulingPlugin"
}

// PreFilter initializes Gang information.
func (pl *GangSchedulingPlugin) PreFilter(ctx context.Context, state *framework.CycleState, pod *v1.Pod) *framework.Status {
    gangID, ok := pod.Labels["gang-id"]
    if !ok {
        return nil  // Process as regular pod if no Gang ID
    }

    pl.mu.Lock()
    defer pl.mu.Unlock()

    if _, ok := pl.gangs[gangID]; !ok {
        minRequired, _ := strconv.Atoi(pod.Labels["gang-min-required"])
        if minRequired <= 0 {
            minRequired = 1
        }

        pl.gangs[gangID] = &Gang{
            MinRequired: minRequired,
            Scheduled:   make(map[string]string),
            Waiting:     make(map[string]*framework.WaitingPod),
        }
    }

    return nil
}

// Permit implements Gang scheduling logic.
func (pl *GangSchedulingPlugin) Permit(ctx context.Context, state *framework.CycleState, pod *v1.Pod, nodeName string) (*framework.Status, time.Duration) {
    gangID, ok := pod.Labels["gang-id"]
    if !ok {
        return nil, 0  // Process as regular pod if no Gang ID
    }

    pl.mu.Lock()
    defer pl.mu.Unlock()

    gang, ok := pl.gangs[gangID]
    if !ok {
        return framework.NewStatus(framework.Error, "gang not found"), 0
    }

    podKey := fmt.Sprintf("%s/%s", pod.Namespace, pod.Name)
    gang.Scheduled[podKey] = nodeName

    // Check if enough pods are scheduled
    if len(gang.Scheduled) >= gang.MinRequired {
        // Allow all waiting pods
        for _, waitingPod := range gang.Waiting {
            waitingPod.Allow(pl.Name())
        }
        gang.Waiting = make(map[string]*framework.WaitingPod)
        return nil, 0
    }

    // Wait until enough pods are scheduled
    waitingPod := framework.NewWaitingPod(pod)
    gang.Waiting[podKey] = waitingPod
    return framework.NewStatus(framework.Wait, "waiting for gang members"), 10 * time.Minute
}
```

**Gang scheduling 的优缺点：**
优点：
- 确保所有相关 Pod 一起被调度
- 防止资源浪费
- 防止 deadlock 和 starvation

缺点：
- 实现复杂度增加
- 可能出现调度延迟
- 可能降低 cluster 资源利用率

**需要 Gang scheduling 的工作负载：**
1. **分布式训练作业**：TensorFlow、PyTorch 等分布式训练框架
2. **分布式数据处理**：Spark、Flink 等分布式数据处理框架
3. **MPI 作业**：高性能计算（HPC）工作负载
4. **Service mesh**：多个组件必须协同工作的 Service mesh

**其他选项的问题：**
- A. 只将 Pod 放置在特定 Node 上：这是 node selector 或 node affinity 的作用。
- C. 将 Pod 均匀分布到各个 Node 上：这是 Pod topology spread constraint 的作用。
- D. 基于优先级调度 Pod：这是 Pod priority 和 preemption 的作用。
</details>

### 4. 在 Kubernetes 中实现 Scheduler Extender 时，以下哪一项不是必需的 API endpoint？

A. /filter
B. /prioritize
C. /bind
D. /validate

<details>
<summary>显示答案</summary>

**答案：D. /validate**

**解释：**
在 Kubernetes 中实现 Scheduler Extender 时，“/validate” 不是必需的 API endpoint。Scheduler extender 通常实现 “/filter”、“/prioritize”、“/bind”、“/preempt” 等 endpoint，但 “/validate” 不是 scheduler extender 的标准 API。

**Scheduler Extender API endpoint：**
1. **filter**：接收 Node 列表并返回经过过滤的 Node 列表。
2. **prioritize**：接收 Node 列表并为每个 Node 分配分数。
3. **bind**：将 Pod 绑定到 Node。
4. **preempt**：返回用于 preemption 的 Node 和 Pod。

**Scheduler Extender configuration 示例：**
```yaml
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
profiles:
- schedulerName: default-scheduler
  extenders:
  - urlPrefix: "http://extender-service:8080"
    filterVerb: "filter"
    prioritizeVerb: "prioritize"
    bindVerb: "bind"
    enableHTTPS: false
    nodeCacheCapable: false
    ignorable: true
    managedResources:
    - name: example.com/foo
      ignoredByScheduler: true
```

**Scheduler Extender API request 和 response 格式：**

1. **filter API**：
   - Request：
     ```json
     {
       "pod": <pod>,
       "nodes": <nodes>,
       "nodenames": <node-names>
     }
     ```
   - Response：
     ```json
     {
       "nodes": <filtered-nodes>,
       "nodenames": <filtered-node-names>,
       "failedNodes": <failed-nodes>,
       "error": <error-message>
     }
     ```

2. **prioritize API**：
   - Request：
     ```json
     {
       "pod": <pod>,
       "nodes": <nodes>,
       "nodenames": <node-names>
     }
     ```
   - Response：
     ```json
     {
       "hostPriorities": [
         {
           "host": <node-name>,
           "score": <score>
         },
         ...
       ],
       "error": <error-message>
     }
     ```

3. **bind API**：
   - Request：
     ```json
     {
       "pod": <pod>,
       "node": <node-name>
     }
     ```
   - Response：
     ```json
     {
       "error": <error-message>
     }
     ```

4. **preempt API**：
   - Request：
     ```json
     {
       "pod": <pod>,
       "nodenames": <node-names>,
       "nodes": <nodes>
     }
     ```
   - Response：
     ```json
     {
       "nodenames": <node-names>,
       "nodes": <nodes>,
       "podsToPreempt": {
         <node-name>: [<pod>, ...],
         ...
       },
       "error": <error-message>
     }
     ```

**Scheduler Extender 实现示例（Go）：**
```go
package main

import (
    "encoding/json"
    "log"
    "net/http"

    v1 "k8s.io/api/core/v1"
    extender "k8s.io/kube-scheduler/extender/v1"
)

func main() {
    http.HandleFunc("/filter", filterHandler)
    http.HandleFunc("/prioritize", prioritizeHandler)
    http.HandleFunc("/bind", bindHandler)

    log.Fatal(http.ListenAndServe(":8080", nil))
}

// Filter handler
func filterHandler(w http.ResponseWriter, r *http.Request) {
    var args extender.ExtenderArgs
    var result extender.ExtenderFilterResult

    // Decode request body
    if err := json.NewDecoder(r.Body).Decode(&args); err != nil {
        http.Error(w, err.Error(), http.StatusBadRequest)
        return
    }

    // Implement filtering logic
    filteredNodes := make([]v1.Node, 0, len(args.Nodes.Items))
    failedNodes := make(map[string]string)

    for _, node := range args.Nodes.Items {
        // Custom filtering logic
        if customFilter(&args.Pod, &node) {
            filteredNodes = append(filteredNodes, node)
        } else {
            failedNodes[node.Name] = "Node failed custom filter"
        }
    }

    // Set result
    result.Nodes = &v1.NodeList{Items: filteredNodes}
    result.FailedNodes = failedNodes

    // Send response
    w.Header().Set("Content-Type", "application/json")
    if err := json.NewEncoder(w).Encode(result); err != nil {
        http.Error(w, err.Error(), http.StatusInternalServerError)
        return
    }
}

// Prioritize handler
func prioritizeHandler(w http.ResponseWriter, r *http.Request) {
    var args extender.ExtenderArgs
    var result extender.HostPriorityList

    // Decode request body
    if err := json.NewDecoder(r.Body).Decode(&args); err != nil {
        http.Error(w, err.Error(), http.StatusBadRequest)
        return
    }

    // Implement prioritization logic
    result = make(extender.HostPriorityList, 0, len(args.Nodes.Items))

    for _, node := range args.Nodes.Items {
        // Custom score calculation
        score := customScore(&args.Pod, &node)
        result = append(result, extender.HostPriority{
            Host:  node.Name,
            Score: score,
        })
    }

    // Send response
    w.Header().Set("Content-Type", "application/json")
    if err := json.NewEncoder(w).Encode(result); err != nil {
        http.Error(w, err.Error(), http.StatusInternalServerError)
        return
    }
}

// Bind handler
func bindHandler(w http.ResponseWriter, r *http.Request) {
    var args extender.ExtenderBindingArgs

    // Decode request body
    if err := json.NewDecoder(r.Body).Decode(&args); err != nil {
        http.Error(w, err.Error(), http.StatusBadRequest)
        return
    }

    // Implement binding logic
    err := customBind(&args.Pod, args.Node)

    // Send response
    w.Header().Set("Content-Type", "application/json")
    if err != nil {
        json.NewEncoder(w).Encode(extender.ExtenderBindingResult{
            Error: err.Error(),
        })
    } else {
        json.NewEncoder(w).Encode(extender.ExtenderBindingResult{})
    }
}

// Custom filtering function
func customFilter(pod *v1.Pod, node *v1.Node) bool {
    // Implement custom filtering logic
    return true
}

// Custom score calculation function
func customScore(pod *v1.Pod, node *v1.Node) int64 {
    // Implement custom score calculation logic
    return 100
}

// Custom binding function
func customBind(pod *v1.Pod, nodeName string) error {
    // Implement custom binding logic
    return nil
}
```

**Scheduler Extender 的优缺点：**
优点：
- 可以独立于 scheduler codebase 进行开发
- 可以用多种编程语言实现
- 受 scheduler 升级影响较小

缺点：
- 由于 HTTP 通信开销，性能会下降
- 只能扩展 scheduling cycle 的部分阶段
- scheduler 与 extender 之间可能发生通信失败

**Scheduler Extender vs Scheduling Framework plugin：**
- **Scheduler Extender**：作为外部进程通过 HTTP webhook 运行。
- **Scheduling Framework plugin**：直接集成在 scheduler codebase 中运行。

**其他选项的解释：**
- A. /filter：有效的 scheduler extender API endpoint，用于过滤 Node 列表。
- B. /prioritize：有效的 scheduler extender API endpoint，用于为 Node 分配分数。
- C. /bind：有效的 scheduler extender API endpoint，用于将 Pod 绑定到 Node。
</details>
### 5. Kubernetes scheduler framework 中 “PostFilter” extension point 的作用是什么？

A. 在过滤后为 Node 分配分数
B. 在过滤后将 Pod 绑定到 Node
C. 在过滤失败时执行 preemption 逻辑
D. 在过滤后更新 Pod 状态

<details>
<summary>显示答案</summary>

**答案：C. 在过滤失败时执行 preemption 逻辑**

**解释：**
Kubernetes scheduling framework 中 “PostFilter” extension point 的作用是在过滤失败时执行 preemption 逻辑。当所有 Node 在 filtering phase 中都被排除且 Pod 无法被调度时，PostFilter plugin 会通过 preemption 查找调度该 Pod 的方式。

**PostFilter extension point 的关键功能：**
1. **识别 preemption 候选对象**：识别可以被 preempt 的 Pod 和 Node。
2. **Preemption 模拟**：模拟在 preemption 之后 Pod 是否可以被调度。
3. **Preemption 决策**：确定最佳 preemption 策略。

**PostFilter plugin interface：**
```go
type PostFilterPlugin interface {
    Plugin
    // PostFilter is called when filtering fails.
    // Finds ways to schedule pods through preemption.
    PostFilter(ctx context.Context, state *CycleState, pod *v1.Pod, filteredNodeStatusMap NodeToStatusMap) (*PostFilterResult, *Status)
}

// PostFilterResult represents the result of PostFilter operation.
type PostFilterResult struct {
    // Node where pod will be scheduled after preemption
    NominatedNodeName string
}
```

**默认 PostFilter plugin：**
Kubernetes 提供以下默认 PostFilter plugin：

1. **DefaultPreemption**：实现默认 preemption 逻辑。

**DefaultPreemption plugin 的运行方式：**
1. 识别可以通过 preempt 低优先级 Pod 来腾出空间的 Node。
2. 确定每个 Node 上要 preempt 哪些 Pod。
3. 验证 preemption 后 Pod 是否可以被调度。
4. 选择最佳 preemption 策略。
5. 将选定 Node 设置为 Pod 的 nominatedNodeName。

**Custom PostFilter plugin 示例：**
```go
// CustomPostFilter implements custom preemption logic.
type CustomPostFilter struct {
    handle framework.Handle
}

// Name returns the plugin name.
func (pl *CustomPostFilter) Name() string {
    return "CustomPostFilter"
}

// PostFilter is called when filtering fails.
func (pl *CustomPostFilter) PostFilter(ctx context.Context, state *framework.CycleState, pod *v1.Pod, filteredNodeStatusMap framework.NodeToStatusMap) (*framework.PostFilterResult, *framework.Status) {
    // Identify preemptable nodes
    preemptableNodes := identifyPreemptableNodes(pl.handle, pod, filteredNodeStatusMap)
    if len(preemptableNodes) == 0 {
        return nil, framework.NewStatus(framework.Unschedulable, "no preemptable nodes found")
    }

    // Determine pods to preempt on each node
    nodeToVictims := map[string]*framework.Victims{}
    for _, node := range preemptableNodes {
        victims, err := selectVictimsOnNode(pl.handle, pod, node)
        if err != nil {
            continue
        }
        nodeToVictims[node.Name] = victims
    }

    // Select optimal preemption strategy
    nominatedNode, victims := selectBestNodeForPreemption(nodeToVictims)
    if nominatedNode == "" {
        return nil, framework.NewStatus(framework.Unschedulable, "no node for preemption")
    }

    // Execute preemption
    for _, victim := range victims.Pods {
        if err := pl.handle.ClientSet().CoreV1().Pods(victim.Namespace).Delete(ctx, victim.Name, metav1.DeleteOptions{}); err != nil {
            return nil, framework.NewStatus(framework.Error, err.Error())
        }
    }

    return &framework.PostFilterResult{
        NominatedNodeName: nominatedNode,
    }, nil
}

// Identify preemptable nodes
func identifyPreemptableNodes(handle framework.Handle, pod *v1.Pod, filteredNodeStatusMap framework.NodeToStatusMap) []*v1.Node {
    // Implementation omitted
    return nil
}

// Select pods to preempt on node
func selectVictimsOnNode(handle framework.Handle, pod *v1.Pod, node *v1.Node) (*framework.Victims, error) {
    // Implementation omitted
    return nil, nil
}

// Select optimal preemption strategy
func selectBestNodeForPreemption(nodeToVictims map[string]*framework.Victims) (string, *framework.Victims) {
    // Implementation omitted
    return "", nil
}
```

**在 scheduler configuration 中启用 PostFilter plugin：**
```yaml
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
profiles:
- schedulerName: custom-scheduler
  plugins:
    postFilter:
      enabled:
      - name: CustomPostFilter
      disabled:
      - name: DefaultPreemption  # Disable default plugin
```

**Preemption 相关设置：**
```yaml
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
profiles:
- schedulerName: custom-scheduler
  pluginConfig:
  - name: DefaultPreemption
    args:
      minCandidateNodesPercentage: 10  # Minimum percentage of preemption candidate nodes
      minCandidateNodesAbsolute: 100   # Minimum number of preemption candidate nodes
```

**Preemption 流程：**
1. 当 Pod 在所有 Node 上都未通过 filtering phase 时，会调用 PostFilter phase。
2. PostFilter plugin 识别 preemption candidate Node。
3. 确定每个 Node 上要 preempt 哪些 Pod。
4. 验证 preemption 后 Pod 是否可以被调度。
5. 选择最佳 preemption 策略。
6. 将选定 Node 设置为 Pod 的 nominatedNodeName。
7. 被 preempt 的 Pod 会经历 graceful termination。
8. 当被 preempt 的 Pod 终止后，更高优先级的 Pod 会被调度。

**监控 preemption 相关指标：**
```bash
# Check preemption-related metrics from scheduler metrics
kubectl get --raw /metrics | grep scheduler_preemption
```

**检查 preemption event：**
```bash
# Check preemption events
kubectl get events | grep -i preempt
```

**其他选项的问题：**
- A. 在过滤后为 Node 分配分数：这是 “Score” extension point 的作用。
- B. 在过滤后将 Pod 绑定到 Node：这是 “Bind” extension point 的作用。
- D. 在过滤后更新 Pod 状态：这不是 scheduler framework 中的 extension point。
</details>

### 6. Kubernetes scheduler 中 “NodeResourcesBalancedAllocation” plugin 的主要目的是什么？

A. 给 CPU 和内存使用均衡的 Node 更高分数
B. 给资源使用较低的 Node 更高分数
C. 给资源使用较高的 Node 更高分数
D. 在 Node 上设置 resource limit

<details>
<summary>显示答案</summary>

**答案：A. 给 CPU 和内存使用均衡的 Node 更高分数**

**解释：**
Kubernetes scheduler 中 “NodeResourcesBalancedAllocation” plugin 的主要目的是给 CPU 和内存使用均衡的 Node 更高分数。该 plugin 偏好 CPU 和内存利用率差异较小的 Node，从而提升整个 cluster 中的资源使用均衡性。

**NodeResourcesBalancedAllocation plugin 的运行方式：**
1. 计算每个 Node 的 CPU 利用率和内存利用率。
2. 计算 CPU 利用率与内存利用率之间的差异。
3. 给差异较小的 Node 更高分数。

**分数计算方法：**
```
score = 10 - variance(cpuFraction, memoryFraction) * 10
```
其中：
- cpuFraction =（已请求 CPU + Pod 的 CPU request）/ 可分配 CPU
- memoryFraction =（已请求内存 + Pod 的内存 request）/ 可分配内存
- variance(a, b) = |a - b|

**示例：**
- Node A：CPU 利用率 80%，内存利用率 80% -> 差异：0% -> 分数：10
- Node B：CPU 利用率 90%，内存利用率 50% -> 差异：40% -> 分数：6
- Node C：CPU 利用率 30%，内存利用率 90% -> 差异：60% -> 分数：4

在这种情况下，Node A 获得最高分，最有可能被选中。

**在 scheduler configuration 中启用 NodeResourcesBalancedAllocation plugin：**
```yaml
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
profiles:
- schedulerName: default-scheduler
  plugins:
    score:
      enabled:
      - name: NodeResourcesBalancedAllocation
        weight: 2  # Set weight
```

**Plugin configuration：**
```yaml
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
profiles:
- schedulerName: default-scheduler
  pluginConfig:
  - name: NodeResourcesBalancedAllocation
    args:
      resources:
      - name: cpu
        weight: 1
      - name: memory
        weight: 1
```

**NodeResourcesBalancedAllocation vs 其他 scoring plugin：**
1. **NodeResourcesBalancedAllocation**：偏好 CPU 和内存使用均衡的 Node。
2. **NodeResourcesFit**：相比请求资源，偏好可用资源更多的 Node。
3. **NodeResourcesLeastAllocated**：偏好资源使用较低的 Node。
4. **NodeResourcesMostAllocated**：偏好资源使用较高的 Node。

**使用场景：**
1. **资源均衡**：改善整个 cluster 的 CPU 和内存使用均衡。
2. **防止瓶颈**：防止某一类资源（CPU 或内存）先于另一类资源耗尽。
3. **可扩展性提升**：资源使用均衡的 cluster 可以更高效地扩展。

**Custom balanced allocation plugin 示例：**
```go
// CustomBalancedAllocation implements custom balanced allocation logic.
type CustomBalancedAllocation struct {
    handle framework.Handle
    // Resource weights
    resourceWeights map[v1.ResourceName]int64
}

// Name returns the plugin name.
func (pl *CustomBalancedAllocation) Name() string {
    return "CustomBalancedAllocation"
}

// Score assigns a score to nodes.
func (pl *CustomBalancedAllocation) Score(ctx context.Context, state *framework.CycleState, pod *v1.Pod, nodeName string) (int64, *framework.Status) {
    nodeInfo, err := pl.handle.SnapshotSharedLister().NodeInfos().Get(nodeName)
    if err != nil {
        return 0, framework.NewStatus(framework.Error, fmt.Sprintf("getting node %q from Snapshot: %v", nodeName, err))
    }

    // Node's allocatable resources
    allocatable := nodeInfo.Node().Status.Allocatable

    // Resources already requested on node
    requested := nodeInfo.RequestedResource()

    // Pod's resource request
    podRequest := calculatePodResourceRequest(pod)

    // Calculate resource utilization
    fractions := make(map[v1.ResourceName]float64)
    for resource, weight := range pl.resourceWeights {
        if weight == 0 {
            continue
        }

        allocatableValue := allocatable[resource]
        if allocatableValue.IsZero() {
            continue
        }

        requestedValue := requested.ResourceList[resource]
        podRequestValue := podRequest[resource]

        fraction := float64(requestedValue.Value()+podRequestValue.Value()) / float64(allocatableValue.Value())
        fractions[resource] = fraction
    }

    // Calculate difference between resource utilizations
    var variance float64
    for _, fraction := range fractions {
        for _, otherFraction := range fractions {
            diff := fraction - otherFraction
            if diff > 0 {
                variance += diff
            } else {
                variance -= diff
            }
        }
    }

    // Calculate score
    score := int64(100 - variance*100)
    if score < 0 {
        score = 0
    }

    return score, nil
}

// ScoreExtensions returns interface for score normalization.
func (pl *CustomBalancedAllocation) ScoreExtensions() framework.ScoreExtensions {
    return nil
}

// Calculate pod's resource request
func calculatePodResourceRequest(pod *v1.Pod) v1.ResourceList {
    result := v1.ResourceList{}
    for _, container := range pod.Spec.Containers {
        for resource, value := range container.Resources.Requests {
            if currentValue, ok := result[resource]; ok {
                currentValue.Add(value)
                result[resource] = currentValue
            } else {
                result[resource] = value.DeepCopy()
            }
        }
    }
    return result
}
```

**其他选项的问题：**
- B. 给资源使用较低的 Node 更高分数：这是 “NodeResourcesLeastAllocated” plugin 的作用。
- C. 给资源使用较高的 Node 更高分数：这是 “NodeResourcesMostAllocated” plugin 的作用。
- D. 在 Node 上设置 resource limit：这不是 scheduler plugin 的作用；Node resource limit 是 Node 本身的属性。
</details>
### 7. Kubernetes scheduler 中 “PreBind” extension point 的作用是什么？

A. 将 Pod 绑定到 Node
B. 在 binding 前执行必要操作
C. 在 binding 后执行清理
D. 当 binding 失败时执行恢复操作

<details>
<summary>显示答案</summary>

**答案：B. 在 binding 前执行必要操作**

**解释：**
Kubernetes scheduling framework 中 “PreBind” extension point 的作用是在将 Pod 绑定到 Node 之前执行必要操作。例如，可以执行 volume provisioning、网络设置和 resource reservation 等操作。

**PreBind extension point 的关键功能：**
1. **Volume provisioning**：创建并准备必要的 volume。
2. **网络设置**：配置必要的网络资源。
3. **Resource reservation**：预留必要资源。
4. **预验证**：最终验证 binding 是否可行。

**PreBind plugin interface：**
```go
type PreBindPlugin interface {
    Plugin
    // PreBind is called before binding a pod to a node.
    PreBind(ctx context.Context, state *CycleState, pod *v1.Pod, nodeName string) *Status
}
```

**默认 PreBind plugin：**
Kubernetes 提供以下默认 PreBind plugin：

1. **VolumeBinding**：执行 volume binding 操作。
2. **DefaultPreBind**：执行基本的 pre-binding 操作。

**Custom PreBind plugin 示例：**
```go
// CustomPreBind implements custom pre-binding logic.
type CustomPreBind struct {
    handle framework.Handle
}

// Name returns the plugin name.
func (pl *CustomPreBind) Name() string {
    return "CustomPreBind"
}

// PreBind is called before binding a pod to a node.
func (pl *CustomPreBind) PreBind(ctx context.Context, state *framework.CycleState, pod *v1.Pod, nodeName string) *framework.Status {
    // 1. Volume provisioning
    if err := pl.provisionVolumes(ctx, pod, nodeName); err != nil {
        return framework.NewStatus(framework.Error, err.Error())
    }

    // 2. Network resource setup
    if err := pl.setupNetworking(ctx, pod, nodeName); err != nil {
        return framework.NewStatus(framework.Error, err.Error())
    }

    // 3. Resource reservation
    if err := pl.reserveResources(ctx, pod, nodeName); err != nil {
        return framework.NewStatus(framework.Error, err.Error())
    }

    // 4. Final validation
    if err := pl.validateBinding(ctx, pod, nodeName); err != nil {
        return framework.NewStatus(framework.Error, err.Error())
    }

    return nil
}

// Volume provisioning
func (pl *CustomPreBind) provisionVolumes(ctx context.Context, pod *v1.Pod, nodeName string) error {
    // Identify necessary volumes
    for _, volume := range pod.Spec.Volumes {
        if volume.PersistentVolumeClaim != nil {
            // Check PVC status
            pvc, err := pl.handle.ClientSet().CoreV1().PersistentVolumeClaims(pod.Namespace).Get(ctx, volume.PersistentVolumeClaim.ClaimName, metav1.GetOptions{})
            if err != nil {
                return err
            }

            // If PVC is not bound
            if pvc.Status.Phase != v1.ClaimBound {
                return fmt.Errorf("PVC %s is not bound", pvc.Name)
            }
        }
    }
    return nil
}

// Network resource setup
func (pl *CustomPreBind) setupNetworking(ctx context.Context, pod *v1.Pod, nodeName string) error {
    // Example: Network policy setup
    if err := pl.setupNetworkPolicies(ctx, pod, nodeName); err != nil {
        return err
    }

    // Example: Service endpoint setup
    if err := pl.setupServiceEndpoints(ctx, pod, nodeName); err != nil {
        return err
    }

    return nil
}

// Resource reservation
func (pl *CustomPreBind) reserveResources(ctx context.Context, pod *v1.Pod, nodeName string) error {
    // Example: GPU resource reservation
    if err := pl.reserveGPUs(ctx, pod, nodeName); err != nil {
        return err
    }

    // Example: Special hardware resource reservation
    if err := pl.reserveSpecialHardware(ctx, pod, nodeName); err != nil {
        return err
    }

    return nil
}

// Binding validation
func (pl *CustomPreBind) validateBinding(ctx context.Context, pod *v1.Pod, nodeName string) error {
    // Example: Re-verify node status
    node, err := pl.handle.ClientSet().CoreV1().Nodes().Get(ctx, nodeName, metav1.GetOptions{})
    if err != nil {
        return err
    }

    // Example: Check node resource availability
    if !hasEnoughResources(node, pod) {
        return fmt.Errorf("node %s does not have enough resources", nodeName)
    }

    return nil
}
```

**在 scheduler configuration 中启用 PreBind plugin：**
```yaml
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
profiles:
- schedulerName: custom-scheduler
  plugins:
    preBind:
      enabled:
      - name: CustomPreBind
      disabled:
      - name: VolumeBinding  # Disable default plugin
```

**PreBind 使用场景：**
1. **Volume provisioning**：
   - PersistentVolume 创建和 binding
   - Ephemeral volume 准备
   - Storage class 参数验证

2. **网络设置**：
   - Network policy 应用
   - Service endpoint 设置
   - Load balancer 配置

3. **Resource reservation**：
   - GPU 资源预留
   - FPGA 资源预留
   - 特殊硬件资源预留

4. **安全设置**：
   - Security policy 应用
   - Certificate provisioning
   - Secret mount 准备

**PreBind 失败处理：**
当 PreBind plugin 返回失败时：
1. scheduling cycle 被中止。
2. Pod 返回 scheduling queue。
3. 已预留资源被释放。
4. 记录失败 event。

**监控 PreBind log 和 event：**
```bash
# Check PreBind-related messages in scheduler logs
kubectl logs -n kube-system <scheduler-pod> | grep -i prebind

# Check pod events
kubectl describe pod <pod-name> | grep -i prebind
```

**其他选项的问题：**
- A. 将 Pod 绑定到 Node：这是 “Bind” extension point 的作用。
- C. 在 binding 后执行清理：这是 “PostBind” extension point 的作用。
- D. 当 binding 失败时执行恢复操作：这不是 scheduler framework 中的 extension point。
</details>

### 8. Kubernetes scheduler 中 “NodeResourcesFit” plugin 的主要目的是什么？

A. 监控 Node 资源使用情况
B. 设置 Node resource limit
C. 将 Node 资源容量与 Pod resource request 进行比较
D. 维持 Node 资源使用均衡

<details>
<summary>显示答案</summary>

**答案：C. 将 Node 资源容量与 Pod resource request 进行比较**

**解释：**
Kubernetes scheduler 中 “NodeResourcesFit” plugin 的主要目的是将 Node 资源容量与 Pod resource request 进行比较，以验证 Pod 是否可以在 Node 上运行。该 plugin 会考虑 CPU、内存、ephemeral storage 和 extended resource（如 GPU）等多种资源类型。

**NodeResourcesFit plugin 的关键功能：**
1. **Resource request 验证**：验证 Pod resource request 不会超过 Node 的可分配资源。
2. **Resource limit 验证**：验证 Pod resource limit 不会超过 Node 容量。
3. **Extended resource 验证**：验证 GPU 和 FPGA 等 extended resource request 在 Node 上可用。

**NodeResourcesFit plugin configuration：**
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
        type: LeastAllocated
        resources:
        - name: cpu
          weight: 1
        - name: memory
          weight: 1
```

**Scoring strategy：**
NodeResourcesFit plugin 支持以下 scoring strategy：

1. **LeastAllocated**：给使用资源较少的 Node 更高分数。
   ```
   score = (capacity - requested) / capacity
   ```

2. **MostAllocated**：给使用资源较多的 Node 更高分数。
   ```
   score = requested / capacity
   ```

3. **RequestedToCapacityRatio**：使用自定义函数基于请求资源与容量的比例分配分数。

**Custom NodeResourcesFit plugin 示例：**
```go
// CustomNodeResourcesFit implements custom resource fit logic.
type CustomNodeResourcesFit struct {
    handle framework.Handle
    // Resource weights
    resourceWeights map[v1.ResourceName]int64
}

// Name returns the plugin name.
func (pl *CustomNodeResourcesFit) Name() string {
    return "CustomNodeResourcesFit"
}

// Filter checks node resource fitness.
func (pl *CustomNodeResourcesFit) Filter(ctx context.Context, state *framework.CycleState, pod *v1.Pod, nodeInfo *framework.NodeInfo) *framework.Status {
    // Node's allocatable resources
    allocatable := nodeInfo.Node().Status.Allocatable

    // Resources already requested on node
    requested := nodeInfo.RequestedResource()

    // Pod's resource request
    podRequest := calculatePodResourceRequest(pod)

    // Check each resource type
    for resourceName := range pl.resourceWeights {
        allocatableValue := allocatable[resourceName]
        if allocatableValue.IsZero() {
            return framework.NewStatus(framework.Unschedulable, fmt.Sprintf("node does not have resource %s", resourceName))
        }

        requestedValue := requested.ResourceList[resourceName]
        podRequestValue := podRequest[resourceName]

        if requestedValue.Value()+podRequestValue.Value() > allocatableValue.Value() {
            return framework.NewStatus(framework.Unschedulable, fmt.Sprintf("insufficient %s", resourceName))
        }
    }

    return nil
}

// Score assigns scores to nodes.
func (pl *CustomNodeResourcesFit) Score(ctx context.Context, state *framework.CycleState, pod *v1.Pod, nodeName string) (int64, *framework.Status) {
    nodeInfo, err := pl.handle.SnapshotSharedLister().NodeInfos().Get(nodeName)
    if err != nil {
        return 0, framework.NewStatus(framework.Error, fmt.Sprintf("getting node %q from Snapshot: %v", nodeName, err))
    }

    // Node's allocatable resources
    allocatable := nodeInfo.Node().Status.Allocatable

    // Resources already requested on node
    requested := nodeInfo.RequestedResource()

    // Pod's resource request
    podRequest := calculatePodResourceRequest(pod)

    // Calculate score
    var score int64 = 0
    for resourceName, weight := range pl.resourceWeights {
        allocatableValue := allocatable[resourceName]
        if allocatableValue.IsZero() {
            continue
        }

        requestedValue := requested.ResourceList[resourceName]
        podRequestValue := podRequest[resourceName]

        // Use LeastAllocated strategy
        resourceScore := (float64(allocatableValue.Value()) - float64(requestedValue.Value()+podRequestValue.Value())) / float64(allocatableValue.Value())
        score += int64(resourceScore * float64(weight))
    }

    return score, nil
}

// ScoreExtensions returns interface for score normalization.
func (pl *CustomNodeResourcesFit) ScoreExtensions() framework.ScoreExtensions {
    return pl
}

// NormalizeScore normalizes scores.
func (pl *CustomNodeResourcesFit) NormalizeScore(ctx context.Context, state *framework.CycleState, pod *v1.Pod, scores framework.NodeScoreList) *framework.Status {
    var highest int64 = 0
    for _, nodeScore := range scores {
        if nodeScore.Score > highest {
            highest = nodeScore.Score
        }
    }

    if highest == 0 {
        return nil
    }

    for i := range scores {
        scores[i].Score = scores[i].Score * framework.MaxNodeScore / highest
    }

    return nil
}
```

**Resource request 和 limit 示例：**
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: resource-demo
spec:
  containers:
  - name: nginx
    image: nginx
    resources:
      requests:
        cpu: "500m"
        memory: "256Mi"
      limits:
        cpu: "1"
        memory: "512Mi"
```

**其他选项的问题：**
- A. 监控 Node 资源使用情况：这是 metrics server 或 monitoring system 的作用。
- B. 设置 Node resource limit：这是 Node configuration 或 kubelet 的作用。
- D. 维持 Node 资源使用均衡：这是 “NodeResourcesBalancedAllocation” plugin 的作用。
</details>
### 9. Kubernetes scheduler 中 “InterPodAffinity” plugin 的主要目的是什么？

A. 处理 Pod 与 Node 之间的 affinity rule
B. 处理 Pod 之间的 affinity 和 anti-affinity rule
C. 处理 Pod 与 volume 之间的 affinity rule
D. 处理 Pod 与 Service 之间的 affinity rule

<details>
<summary>显示答案</summary>

**答案：B. 处理 Pod 之间的 affinity 和 anti-affinity rule**

**解释：**
Kubernetes scheduler 中 “InterPodAffinity” plugin 的主要目的是处理 Pod 之间的 affinity 和 anti-affinity rule。该 plugin 控制 Pod 是否与其他 Pod（affinity）放置在同一个 topology domain（Node、zone、region 等）中，或放置在不同 domain（anti-affinity）中。

**InterPodAffinity plugin 的关键功能：**
1. **Pod affinity rule 处理**：确保 Pod 与带有特定 label 的其他 Pod 放置在同一个 topology domain 中。
2. **Pod anti-affinity rule 处理**：确保 Pod 与带有特定 label 的其他 Pod 放置在不同 topology domain 中。
3. **Topology domain 考量**：考虑包括 Node、zone 和 region 在内的多级 topology domain。

**Pod affinity 和 anti-affinity 类型：**
1. **requiredDuringSchedulingIgnoredDuringExecution**：Pod 必须满足才能被调度的规则（硬性要求）。
2. **preferredDuringSchedulingIgnoredDuringExecution**：偏好但非必需的规则（软性要求）。

**Pod affinity 和 anti-affinity 示例：**
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: web-server
  labels:
    app: web
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
    podAntiAffinity:
      preferredDuringSchedulingIgnoredDuringExecution:
      - weight: 100
        podAffinityTerm:
          labelSelector:
            matchExpressions:
            - key: app
              operator: In
              values:
              - web
          topologyKey: kubernetes.io/hostname
  containers:
  - name: nginx
    image: nginx
```

**InterPodAffinity plugin configuration：**
```yaml
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
profiles:
- schedulerName: default-scheduler
  plugins:
    preFilter:
      enabled:
      - name: InterPodAffinity
    filter:
      enabled:
      - name: InterPodAffinity
    score:
      enabled:
      - name: InterPodAffinity
        weight: 2  # Set weight
  pluginConfig:
  - name: InterPodAffinity
    args:
      hardPodAffinityWeight: 1  # Hard pod affinity weight
```

**Custom InterPodAffinity plugin 示例：**
```go
// CustomInterPodAffinity implements custom inter-pod affinity logic.
type CustomInterPodAffinity struct {
    handle framework.Handle
    // Hard pod affinity weight
    hardPodAffinityWeight int64
}

// Name returns the plugin name.
func (pl *CustomInterPodAffinity) Name() string {
    return "CustomInterPodAffinity"
}

// PreFilter initializes inter-pod affinity information.
func (pl *CustomInterPodAffinity) PreFilter(ctx context.Context, state *framework.CycleState, pod *v1.Pod) *framework.Status {
    // Initialize pod affinity information
    if pod.Spec.Affinity == nil || (pod.Spec.Affinity.PodAffinity == nil && pod.Spec.Affinity.PodAntiAffinity == nil) {
        return nil
    }

    // Store pod affinity information
    affinity := pod.Spec.Affinity
    state.Write(framework.StateKey("CustomInterPodAffinity"), affinity)

    return nil
}

// PreFilterExtensions returns interface providing additional features.
func (pl *CustomInterPodAffinity) PreFilterExtensions() framework.PreFilterExtensions {
    return nil
}

// Filter checks inter-pod affinity rules.
func (pl *CustomInterPodAffinity) Filter(ctx context.Context, state *framework.CycleState, pod *v1.Pod, nodeInfo *framework.NodeInfo) *framework.Status {
    // Get pod affinity information
    obj, err := state.Read(framework.StateKey("CustomInterPodAffinity"))
    if err != nil {
        return nil
    }

    affinity, ok := obj.(*v1.Affinity)
    if !ok || affinity == nil {
        return nil
    }

    // Check required pod affinity rules
    if affinity.PodAffinity != nil {
        for _, term := range affinity.PodAffinity.RequiredDuringSchedulingIgnoredDuringExecution {
            if !satisfiesPodAffinityTerm(pod, term, nodeInfo, pl.handle) {
                return framework.NewStatus(framework.Unschedulable, "node does not satisfy pod affinity rules")
            }
        }
    }

    // Check required pod anti-affinity rules
    if affinity.PodAntiAffinity != nil {
        for _, term := range affinity.PodAntiAffinity.RequiredDuringSchedulingIgnoredDuringExecution {
            if satisfiesPodAffinityTerm(pod, term, nodeInfo, pl.handle) {
                return framework.NewStatus(framework.Unschedulable, "node does not satisfy pod anti-affinity rules")
            }
        }
    }

    return nil
}

// Score assigns scores to nodes.
func (pl *CustomInterPodAffinity) Score(ctx context.Context, state *framework.CycleState, pod *v1.Pod, nodeName string) (int64, *framework.Status) {
    // Get pod affinity information
    obj, err := state.Read(framework.StateKey("CustomInterPodAffinity"))
    if err != nil {
        return 0, nil
    }

    affinity, ok := obj.(*v1.Affinity)
    if !ok || affinity == nil {
        return 0, nil
    }

    nodeInfo, err := pl.handle.SnapshotSharedLister().NodeInfos().Get(nodeName)
    if err != nil {
        return 0, framework.NewStatus(framework.Error, fmt.Sprintf("getting node %q from Snapshot: %v", nodeName, err))
    }

    var score int64 = 0

    // Calculate preferred pod affinity score
    if affinity.PodAffinity != nil {
        for _, term := range affinity.PodAffinity.PreferredDuringSchedulingIgnoredDuringExecution {
            if satisfiesPodAffinityTerm(pod, term.PodAffinityTerm, nodeInfo, pl.handle) {
                score += term.Weight
            }
        }
    }

    // Calculate preferred pod anti-affinity score
    if affinity.PodAntiAffinity != nil {
        for _, term := range affinity.PodAntiAffinity.PreferredDuringSchedulingIgnoredDuringExecution {
            if !satisfiesPodAffinityTerm(pod, term.PodAffinityTerm, nodeInfo, pl.handle) {
                score += term.Weight
            }
        }
    }

    return score, nil
}

// ScoreExtensions returns interface for score normalization.
func (pl *CustomInterPodAffinity) ScoreExtensions() framework.ScoreExtensions {
    return pl
}

// NormalizeScore normalizes scores.
func (pl *CustomInterPodAffinity) NormalizeScore(ctx context.Context, state *framework.CycleState, pod *v1.Pod, scores framework.NodeScoreList) *framework.Status {
    var highest int64 = 0
    for _, nodeScore := range scores {
        if nodeScore.Score > highest {
            highest = nodeScore.Score
        }
    }

    if highest == 0 {
        return nil
    }

    for i := range scores {
        scores[i].Score = scores[i].Score * framework.MaxNodeScore / highest
    }

    return nil
}

// Check if pod affinity term is satisfied
func satisfiesPodAffinityTerm(pod *v1.Pod, term v1.PodAffinityTerm, nodeInfo *framework.NodeInfo, handle framework.Handle) bool {
    // Implementation omitted
    return true
}
```

**Pod affinity 和 anti-affinity 使用场景：**
1. **高可用性**：将同一应用的实例分布到不同 Node、zone 或 region
2. **性能优化**：将相互通信的 Pod 放置在同一 Node 上以最大限度降低延迟
3. **资源隔离**：将资源密集型 Pod 分布到不同 Node 上
4. **许可证限制**：将有许可证限制的应用集中在特定 Node 上

**Pod affinity 和 anti-affinity 的性能影响：**
Pod affinity 和 anti-affinity 的计算成本可能很高，因为它们需要考虑所有 Node 和 Pod。在大型 cluster 中，这可能影响调度性能，因此请谨慎使用。

**其他选项的问题：**
- A. 处理 Pod 与 Node 之间的 affinity rule：这是 “NodeAffinity” plugin 的作用。
- C. 处理 Pod 与 volume 之间的 affinity rule：这是 “VolumeBinding” plugin 的作用。
- D. 处理 Pod 与 Service 之间的 affinity rule：这不是 Kubernetes scheduler plugin。
</details>

### 10. Kubernetes scheduler 中 “NodeName” plugin 的主要目的是什么？

A. 验证 Pod 的 spec.nodeName 字段是否与 Node 名称匹配
B. 为 Node 分配名称
C. 为 Pod 分配 Node 名称
D. 验证 Node 名称格式

<details>
<summary>显示答案</summary>

**答案：A. 验证 Pod 的 spec.nodeName 字段是否与 Node 名称匹配**

**解释：**
Kubernetes scheduler 中 “NodeName” plugin 的主要目的是验证 Pod 的 `spec.nodeName` 字段是否与 Node 名称匹配。该 plugin 检查 Pod 是否已被直接分配到特定 Node，并且在 filtering phase 中只允许名称匹配的 Node 通过。

**NodeName plugin 的关键功能：**
1. **Node 名称验证**：如果 Pod 的 `spec.nodeName` 字段已设置，则只选择名称匹配的 Node。
2. **直接调度支持**：允许用户将 Pod 直接分配到特定 Node。
3. **Scheduler bypass**：设置了 `spec.nodeName` 的 Pod 会绕过正常调度逻辑，并被直接分配到指定 Node。

**NodeName plugin 实现：**
```go
// NodeName plugin implementation example
type NodeName struct{}

// Name returns the plugin name.
func (pl *NodeName) Name() string {
    return "NodeName"
}

// Filter verifies that the pod's spec.nodeName field matches the node name.
func (pl *NodeName) Filter(ctx context.Context, state *framework.CycleState, pod *v1.Pod, nodeInfo *framework.NodeInfo) *framework.Status {
    if pod.Spec.NodeName == "" {
        return nil
    }

    if pod.Spec.NodeName != nodeInfo.Node().Name {
        return framework.NewStatus(framework.UnschedulableAndUnresolvable, "node name does not match")
    }

    return nil
}
```

**指定 nodeName 的 Pod 示例：**
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: nginx
spec:
  nodeName: worker-node-1  # Direct assignment to specific node
  containers:
  - name: nginx
    image: nginx
```

**使用 nodeName 时的注意事项：**
1. **Scheduler bypass**：使用 `nodeName` 会绕过 scheduler 的 filtering、scoring 和其他逻辑。
2. **Node 存在性检查**：如果指定的 Node 不存在，Pod 会保持在 `Pending` 状态。
3. **无资源检查**：不会检查 Node 资源可用性，这可能因资源不足导致失败。
4. **忽略约束**：taint、affinity 和其他约束会被忽略。

**nodeName vs nodeSelector vs nodeAffinity：**
1. **nodeName**：直接分配到特定 Node。限制最强，灵活性最低。
2. **nodeSelector**：基于 label 选择 Node。简单但表达能力有限。
3. **nodeAffinity**：支持复杂的 Node 选择规则。最灵活且表达能力最强。

**nodeName 使用场景：**
1. **调试**：在特定 Node 上运行 Pod 以调试问题。
2. **测试**：在特定 Node 上运行测试。
3. **特殊硬件**：将 Pod 分配到具有特定硬件的 Node。
4. **Static Pod**：用于由 kubelet 直接管理的 Static Pod。

**使用 nodeName 时的注意事项：**
1. **无自动恢复**：如果 Node 发生故障，Pod 不会自动移动到其他 Node。
2. **可扩展性有限**：Node 名称是硬编码的，限制了可扩展性。
3. **维护困难**：如果 Node 名称变化，需要更新 Pod 定义。
4. **无负载均衡**：无法利用 scheduler 的负载均衡功能。

**替代方案和建议：**
1. **使用 nodeSelector**：
   ```yaml
   apiVersion: v1
   kind: Pod
   metadata:
     name: nginx
   spec:
     nodeSelector:
       kubernetes.io/hostname: worker-node-1
     containers:
     - name: nginx
       image: nginx
   ```

2. **使用 nodeAffinity**：
   ```yaml
   apiVersion: v1
   kind: Pod
   metadata:
     name: nginx
   spec:
     affinity:
       nodeAffinity:
         requiredDuringSchedulingIgnoredDuringExecution:
           nodeSelectorTerms:
           - matchExpressions:
             - key: kubernetes.io/hostname
               operator: In
               values:
               - worker-node-1
     containers:
     - name: nginx
       image: nginx
   ```

**其他选项的问题：**
- B. 为 Node 分配名称：Node 名称在创建 Node 时分配，并不是 scheduler plugin 的作用。
- C. 为 Pod 分配 Node 名称：这是在 scheduler 的 binding phase 中执行的，而不是由 NodeName plugin 执行。
- D. 验证 Node 名称格式：这是由 API server validation logic 执行的，而不是由 scheduler plugin 执行。
</details>
