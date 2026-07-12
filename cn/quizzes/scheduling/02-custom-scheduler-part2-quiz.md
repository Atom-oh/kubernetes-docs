# Custom Scheduler 测验（第 2 部分）

本测验考查你对在 Kubernetes 中实现和使用 Custom Scheduler 的高级理解。

## 测验题

### 1. Kubernetes 调度框架中 “Bind” 扩展点的作用是什么？

A. 将 Pod 绑定到 Node，以最终确定调度决策
B. 在 Pod 和 Node 之间设置网络绑定
C. 在 Pod 和 Service 之间创建绑定
D. 在 Pod 和 volume 之间设置绑定

<details>
<summary>显示答案</summary>

**答案：A. 将 Pod 绑定到 Node，以最终确定调度决策**

**解析：**
Kubernetes 调度框架中 “Bind” 扩展点的作用是将 Pod 绑定到所选 Node，以最终确定调度决策。绑定阶段是调度周期的最后阶段，在此阶段会设置 Pod 的 `spec.nodeName` 字段，使 kubelet 能够运行该 Pod。

**绑定流程：**
1. Scheduler 通过过滤和评分选择最佳 Node。
2. 在所选 Node 上预留 Pod（reserve）。
3. 在绑定阶段，将 Pod 的 `spec.nodeName` 字段更新为所选 Node 的名称。
4. 更新后的 Pod 信息存储在 API server 中。
5. kubelet 检测到 Pod 信息，并在该 Node 上运行 Pod。

**Bind Plugin 实现示例：**
```go
// Bind plugin example
type MyBindPlugin struct {
    handle framework.Handle
}

func (bp *MyBindPlugin) Name() string {
    return "MyBindPlugin"
}

// Bind method implementation
func (bp *MyBindPlugin) Bind(ctx context.Context, state *framework.CycleState, pod *v1.Pod, nodeName string) *framework.Status {
    // Create pod binding object
    binding := &v1.Binding{
        ObjectMeta: metav1.ObjectMeta{
            Name:      pod.Name,
            Namespace: pod.Namespace,
        },
        Target: v1.ObjectReference{
            Kind:       "Node",
            Name:       nodeName,
            APIVersion: "v1",
        },
    }

    // Send binding request to API server
    err := bp.handle.ClientSet().CoreV1().Pods(pod.Namespace).Bind(ctx, binding, metav1.CreateOptions{})
    if err != nil {
        return framework.NewStatus(framework.Error, err.Error())
    }

    return nil
}
```

**在 Scheduler 配置中启用 Bind Plugin：**
```yaml
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
profiles:
- schedulerName: custom-scheduler
  plugins:
    bind:
      enabled:
      - name: MyBindPlugin
      disabled:
      - name: DefaultBinder  # Disable default binder
```

**检查与绑定相关的事件：**
```bash
# Check pod scheduling events
kubectl get events | grep -i "Successfully assigned"
```

**排查绑定失败：**
绑定阶段常见的失败原因：
1. API server 连接问题
2. 权限不足
3. Node 名称错误
4. 竞态条件（另一个 Scheduler 同时尝试绑定同一个 Pod）

**其他选项的问题：**
- B. 在 Pod 和 Node 之间设置网络绑定：网络设置是 CNI plugin 的职责，与 Scheduler 的绑定阶段无关。
- C. 在 Pod 和 Service 之间创建绑定：Service 和 Pod 之间的连接通过 label selector 实现，与 Scheduler 的绑定阶段无关。
- D. 在 Pod 和 volume 之间设置绑定：Volume 绑定由 PersistentVolumeClaim controller 处理，与 Scheduler 的绑定阶段是不同的流程。
</details>

### 2. 以下哪一项不是 Kubernetes 中与 Node Affinity 相关的 operator？

A. In
B. NotIn
C. Exists
D. Contains

<details>
<summary>显示答案</summary>

**答案：D. Contains**

**解析：**
Kubernetes 中与 Node Affinity 无关的 operator 是 `Contains`。Kubernetes 不为 node affinity 提供 `Contains` operator。

**Node Affinity 支持的 Operator：**
1. **In**：Label 值必须匹配指定值之一。
2. **NotIn**：Label 值不得匹配指定值。
3. **Exists**：指定的 label key 必须存在。
4. **DoesNotExist**：指定的 label key 必须不存在。
5. **Gt**：Label 值必须大于指定值（Greater than）。
6. **Lt**：Label 值必须小于指定值（Less than）。

**Node Affinity 示例：**
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
          - key: kubernetes.io/e2e-az-name
            operator: In
            values:
            - e2e-az1
            - e2e-az2
      preferredDuringSchedulingIgnoredDuringExecution:
      - weight: 1
        preference:
          matchExpressions:
          - key: another-node-label-key
            operator: Exists
```

**Node Affinity 类型：**
1. **requiredDuringSchedulingIgnoredDuringExecution**：Pod 要调度到某个 Node 上必须满足的规则（硬性要求）。
2. **preferredDuringSchedulingIgnoredDuringExecution**：希望满足但不是强制的规则（软性要求）。

**Operator 使用示例：**
1. **In Operator**：
   ```yaml
   - key: kubernetes.io/e2e-az-name
     operator: In
     values:
     - e2e-az1
     - e2e-az2
   ```
   Node 的 `kubernetes.io/e2e-az-name` label 值必须是 `e2e-az1` 或 `e2e-az2`。

2. **NotIn Operator**：
   ```yaml
   - key: kubernetes.io/e2e-az-name
     operator: NotIn
     values:
     - e2e-az3
   ```
   Node 的 `kubernetes.io/e2e-az-name` label 值不得是 `e2e-az3`。

3. **Exists Operator**：
   ```yaml
   - key: kubernetes.io/e2e-az-name
     operator: Exists
   ```
   `kubernetes.io/e2e-az-name` label 必须存在于该 Node 上。

4. **DoesNotExist Operator**：
   ```yaml
   - key: emptyLabel
     operator: DoesNotExist
   ```
   `emptyLabel` label 必须不存在于该 Node 上。

5. **Gt/Lt Operator**：
   ```yaml
   - key: node-size
     operator: Gt
     values:
     - "10"
   ```
   Node 的 `node-size` label 值必须大于 10。

**在 Custom Scheduler 中处理 Node Affinity：**
实现 Custom Scheduler 时，应考虑 Pod 的 node affinity 要求。

```go
// Node affinity check example
func checkNodeAffinity(pod *v1.Pod, node *v1.Node) bool {
    affinity := pod.Spec.Affinity
    if affinity == nil || affinity.NodeAffinity == nil {
        return true  // All nodes are suitable if there's no node affinity
    }

    // Check required node affinity
    if required := affinity.NodeAffinity.RequiredDuringSchedulingIgnoredDuringExecution; required != nil {
        for _, term := range required.NodeSelectorTerms {
            if matchNodeSelectorTerm(term, node) {
                return true
            }
        }
        return false  // No NodeSelectorTerm matched
    }

    return true
}

// Check if NodeSelectorTerm matches
func matchNodeSelectorTerm(term v1.NodeSelectorTerm, node *v1.Node) bool {
    // Implementation omitted
    return true
}
```

**其他选项说明：**
- A. In：有效的 node affinity operator。
- B. NotIn：有效的 node affinity operator。
- C. Exists：有效的 node affinity operator。
</details>

### 3. Kubernetes 中 Pod Topology Spread Constraints 的主要目的是什么？

A. 在各种 Node 之间均匀分散 Pod
B. 仅将 Pod 放置在特定 Node 上
C. 仅将 Pod 放置在特定 zone 中
D. 仅将 Pod 放置在具有特定 label 的 Node 上

<details>
<summary>显示答案</summary>

**答案：A. 在各种 Node 之间均匀分散 Pod**

**解析：**
Kubernetes 中 Pod Topology Spread Constraints 的主要目的是在各种 topology domain（Node、zone、region 等）之间均匀分散 Pod。这可以提高应用程序高可用性、优化资源使用并提升容错能力。

**Pod Topology Spread Constraints 的主要组件：**
1. **maxSkew**：指定 topology domain 之间 Pod 数量的最大差异。
2. **topologyKey**：定义用于分散 Pod 的 topology domain 的 Node label key。
3. **whenUnsatisfiable**：指定约束无法满足时的行为。
   - `DoNotSchedule`：如果约束不满足，则不调度 Pod。
   - `ScheduleAnyway`：即使约束不满足，也调度 Pod。
4. **labelSelector**：用于选择在分散计算中要考虑的现有 Pod 的 label selector。

**Pod Topology Spread Constraints 示例：**
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: web-server
  labels:
    app: web
spec:
  topologySpreadConstraints:
  - maxSkew: 1
    topologyKey: kubernetes.io/hostname
    whenUnsatisfiable: DoNotSchedule
    labelSelector:
      matchLabels:
        app: web
  - maxSkew: 2
    topologyKey: topology.kubernetes.io/zone
    whenUnsatisfiable: DoNotSchedule
    labelSelector:
      matchLabels:
        app: web
  containers:
  - name: nginx
    image: nginx
```

在此示例中，定义了两个约束：
1. 每个 Node（`kubernetes.io/hostname`）之间带有 `app=web` label 的 Pod 数量差异最多为 1。
2. 每个 zone（`topology.kubernetes.io/zone`）之间带有 `app=web` label 的 Pod 数量差异最多为 2。

**Topology Spread 计算方法：**
1. 计算每个 topology domain 中匹配 label selector 的 Pod 数量。
2. 计算 Pod 最多的 domain 与 Pod 最少的 domain 之间的差异。
3. 如果该差异大于 `maxSkew`，则违反约束。

**常见 Topology Key：**
1. **kubernetes.io/hostname**：Node 级别分散
2. **topology.kubernetes.io/zone**：Zone 级别分散
3. **topology.kubernetes.io/region**：Region 级别分散
4. **node.kubernetes.io/instance-type**：实例类型级别分散

**使用场景：**
1. **高可用性**：通过将 Pod 分散到多个 Node、zone、region 来提升容错能力
2. **资源均衡**：在集群中均匀分散工作负载
3. **成本优化**：将工作负载分散到特定类型的 Node 上
4. **性能优化**：通过分散来尽量降低网络延迟

**在 Custom Scheduler 中处理 Topology Spread：**
实现 Custom Scheduler 时，应考虑 Pod 的 topology spread constraints。

```go
// Topology spread constraint check example
func checkTopologySpreadConstraints(pod *v1.Pod, node *v1.Node, allPods []*v1.Pod) bool {
    constraints := pod.Spec.TopologySpreadConstraints
    if len(constraints) == 0 {
        return true  // All nodes are suitable if there are no constraints
    }

    for _, constraint := range constraints {
        // Get topology key value
        topologyValue, ok := node.Labels[constraint.TopologyKey]
        if !ok {
            // Skip this constraint if the node doesn't have the topology key
            if constraint.WhenUnsatisfiable == v1.DoNotSchedule {
                return false
            }
            continue
        }

        // Calculate the number of matching pods in the current topology domain
        var matchingPods int
        for _, existingPod := range allPods {
            // Check if the pod matches the label selector and is in the same topology domain
            if podMatchesLabelSelector(existingPod, constraint.LabelSelector) {
                podNode, err := getNodeForPod(existingPod)
                if err != nil {
                    continue
                }
                if podNode.Labels[constraint.TopologyKey] == topologyValue {
                    matchingPods++
                }
            }
        }

        // Calculate pod count in other topology domains and check skew
        // (Implementation omitted)

        // Check maxSkew violation
        if skew > constraint.MaxSkew && constraint.WhenUnsatisfiable == v1.DoNotSchedule {
            return false
        }
    }

    return true
}
```

**其他选项的问题：**
- B. 仅将 Pod 放置在特定 Node 上：这是 nodeSelector 或 nodeAffinity 的作用。
- C. 仅将 Pod 放置在特定 zone 中：这是使用 node affinity 将 Pod 放置在特定 zone 中；topology spread constraints 的主要目的是均匀分布。
- D. 仅将 Pod 放置在具有特定 label 的 Node 上：这是 nodeSelector 或 nodeAffinity 的作用。
</details>
### 4. Kubernetes 中 Taints 和 Tolerations 的主要目的是什么？

A. 确保特定 Pod 只被调度到特定 Node 上
B. 防止特定 Pod 被调度到特定 Node 上
C. 允许 Node 拒绝某些 Pod，并允许 Pod 容忍这一点
D. 限制 Pod 之间的通信

<details>
<summary>显示答案</summary>

**答案：C. 允许 Node 拒绝某些 Pod，并允许 Pod 容忍这一点**

**解析：**
Kubernetes 中 Taints 和 Tolerations 的主要目的是允许 Node 拒绝某些 Pod，并允许 Pod 容忍这一点。Taint 应用于 Node，用于阻止 Pod 被调度；toleration 应用于 Pod，用于允许其调度到带有特定 taint 的 Node 上。

**Taints 和 Tolerations 的工作方式：**
1. **Taints**：应用于 Node，用于限制 Pod 在该 Node 上调度。
2. **Tolerations**：应用于 Pod，用于允许其调度到带有特定 taint 的 Node 上。
3. **Effect**：taint 的 effect 定义了没有 toleration 的 Pod 的行为。

**Taint Effect 类型：**
1. **NoSchedule**：没有 toleration 的 Pod 不会被调度到该 Node 上。
2. **PreferNoSchedule**：没有 toleration 的 Pod 最好不要调度到该 Node 上，但如果集群资源不足，也可能被调度。
3. **NoExecute**：没有 toleration 的 Pod 不会被调度到该 Node 上，并且已经运行的 Pod 会被移除。

**Taint 应用示例：**
```bash
# Apply taint to node
kubectl taint nodes node1 key=value:NoSchedule

# Remove taint from node
kubectl taint nodes node1 key=value:NoSchedule-
```

**Taint 和 Toleration 示例：**
```yaml
# Apply taint to node
apiVersion: v1
kind: Node
metadata:
  name: node1
spec:
  taints:
  - key: "key"
    value: "value"
    effect: "NoSchedule"

# Apply toleration to pod
apiVersion: v1
kind: Pod
metadata:
  name: pod-with-toleration
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

**Toleration Operator：**
1. **Equal**：Key 和 value 必须匹配。
2. **Exists**：只需要 key 匹配（忽略 value）。

**额外的 Toleration 字段：**
- **tolerationSeconds**：指定 Pod 在因 NoExecute effect 被移除之前可以留在 Node 上的时间（秒）。

```yaml
tolerations:
- key: "node.kubernetes.io/not-ready"
  operator: "Exists"
  effect: "NoExecute"
  tolerationSeconds: 300
```

**常见使用场景：**
1. **专用 Node**：仅为特定工作负载预留 Node
2. **特殊硬件**：仅将特定 Pod 调度到具有 GPU 等特殊硬件的 Node 上
3. **Node 维护**：在 Node 维护期间防止新的 Pod 调度
4. **Master Node 保护**：防止普通工作负载调度到 control plane Node 上

**系统 Taints：**
Kubernetes 会自动应用以下系统 taint：
1. **node.kubernetes.io/not-ready**：Node 未就绪
2. **node.kubernetes.io/unreachable**：Node 不可达
3. **node.kubernetes.io/memory-pressure**：Node 存在内存压力
4. **node.kubernetes.io/disk-pressure**：Node 存在磁盘压力
5. **node.kubernetes.io/pid-pressure**：Node 存在 PID 压力
6. **node.kubernetes.io/network-unavailable**：Node 网络不可用
7. **node.kubernetes.io/unschedulable**：Node 被标记为不可调度

**在 Custom Scheduler 中处理 Taints 和 Tolerations：**
实现 Custom Scheduler 时，应考虑 Node taint 和 Pod toleration。

```go
// Taint and toleration check example
func checkTaintsAndTolerations(pod *v1.Pod, node *v1.Node) bool {
    // All pods can be scheduled if the node has no taints
    if len(node.Spec.Taints) == 0 {
        return true
    }

    // Check if the pod has tolerations for each taint
    for _, taint := range node.Spec.Taints {
        if taint.Effect == v1.TaintEffectNoSchedule || taint.Effect == v1.TaintEffectPreferNoSchedule {
            // Check if the pod tolerates this taint
            if !tolerationsTolerateTaint(pod.Spec.Tolerations, &taint) {
                return false
            }
        }
    }

    return true
}

// Check if tolerations tolerate a taint
func tolerationsTolerateTaint(tolerations []v1.Toleration, taint *v1.Taint) bool {
    for _, toleration := range tolerations {
        if toleration.Key == taint.Key {
            if toleration.Operator == v1.TolerationOpExists {
                return true
            } else if toleration.Operator == v1.TolerationOpEqual && toleration.Value == taint.Value {
                return true
            }
        }
    }
    return false
}
```

**其他选项的问题：**
- A. 确保特定 Pod 只被调度到特定 Node 上：这是 nodeSelector 或 nodeAffinity 的作用。
- B. 防止特定 Pod 被调度到特定 Node 上：这是 podAntiAffinity 的作用。
- D. 限制 Pod 之间的通信：这是 NetworkPolicy 的作用。
</details>

### 5. 以下哪一项不是 Kubernetes 中 Scheduler Extender 的主要特征？

A. 通过 HTTP webhook 与 Scheduler 通信
B. 提供过滤和优先级排序能力
C. 直接集成到 Scheduler 代码库中
D. 作为外部进程运行

<details>
<summary>显示答案</summary>

**答案：C. 直接集成到 Scheduler 代码库中**

**解析：**
“直接集成到 Scheduler 代码库中”不是 Kubernetes 中 Scheduler Extender 的主要特征。Scheduler extender 并不直接集成到 Scheduler 代码库中；它们通过 HTTP webhook 通信，并作为外部进程运行。这是它与 scheduling framework plugin 的主要区别。

**Scheduler Extender 的主要特征：**
1. **HTTP webhook**：Scheduler 通过 HTTP request 与 extender 通信。
2. **外部进程**：Extender 作为与 Scheduler 分离的进程运行。
3. **过滤和优先级排序**：Extender 可以提供 Node 过滤和优先级排序能力。
4. **绑定**：Extender 可以选择性地将 Pod 绑定到 Node。

**Scheduler Extender 配置示例：**
```yaml
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
    nodeCacheCapable: false
    ignorable: true
    managedResources:
    - name: example.com/foo
      ignoredByScheduler: true
```

**Scheduler Extender API：**
1. **Filter API**：接收 Node 列表，并返回过滤后的 Node 列表。
   ```
   POST /filter
   ```
   请求体：
   ```json
   {
     "pod": <pod>,
     "nodes": <nodes>,
     "nodenames": <node-names>
   }
   ```
   响应体：
   ```json
   {
     "nodes": <filtered-nodes>,
     "nodenames": <filtered-node-names>,
     "failedNodes": <failed-nodes>,
     "error": <error-message>
   }
   ```

2. **Prioritize API**：接收 Node 列表，并为每个 Node 分配分数。
   ```
   POST /prioritize
   ```
   请求体：
   ```json
   {
     "pod": <pod>,
     "nodes": <nodes>,
     "nodenames": <node-names>
   }
   ```
   响应体：
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

3. **Bind API**：将 Pod 绑定到 Node。
   ```
   POST /bind
   ```
   请求体：
   ```json
   {
     "pod": <pod>,
     "node": <node-name>
   }
   ```
   响应体：
   ```json
   {
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

func main() {
    http.HandleFunc("/filter", filterHandler)
    http.HandleFunc("/prioritize", prioritizeHandler)

    log.Fatal(http.ListenAndServe(":8080", nil))
}
```

**Scheduler Extender 与 Scheduling Framework Plugin 对比：**

| 特性 | Scheduler Extender | Scheduling Framework Plugin |
|---------|-------------------|---------------------------|
| 集成方式 | HTTP webhook | 直接代码库集成 |
| 执行模式 | 外部进程 | Scheduler 内部 |
| 性能 | 由于 HTTP 开销，相对较慢 | 由于直接集成，更快 |
| 开发语言 | 无限制 | Go |
| 部署 | 独立 Service | 随 Scheduler 部署 |
| 维护 | 独立于 Scheduler | 与 Scheduler 版本关联 |

**Scheduler Extender 的优缺点：**
优点：
- 可以独立于 Scheduler 代码库开发
- 可以用多种编程语言实现
- 受 Scheduler 升级影响较小

缺点：
- 由于 HTTP 通信开销导致性能下降
- 只能扩展调度周期的部分阶段
- Scheduler 与 extender 之间存在通信失败的可能性

**其他选项说明：**
- A. 通过 HTTP webhook 与 Scheduler 通信：Scheduler extender 的有效特征。
- B. 提供过滤和优先级排序能力：Scheduler extender 的有效特征。
- D. 作为外部进程运行：Scheduler extender 的有效特征。
</details>
### 6. Kubernetes 中 Pod Affinity 和 Anti-Affinity 的主要目的是什么？

A. 定义 Pod 与 Node 之间的关系
B. 定义 Pod 与 volume 之间的关系
C. 定义 Pod 之间的关系
D. 定义 Pod 与 Service 之间的关系

<details>
<summary>显示答案</summary>

**答案：C. 定义 Pod 之间的关系**

**解析：**
Kubernetes 中 Pod Affinity 和 Anti-Affinity 的主要目的是定义 Pod 之间的关系。这允许控制特定 Pod 是否与其他 Pod 放置在相同的 topology domain（Node、zone、region 等）中（affinity），或不放置在相同 domain 中（anti-affinity）。

**Pod Affinity 和 Anti-Affinity 的主要组件：**
1. **topologyKey**：Node label key，用于指定定义 Pod 之间关系的 topology domain。
2. **labelSelector**：用于选择要建立关系的 Pod 的 label selector。
3. **namespaces**：label selector 适用的 namespace 列表。

**Pod Affinity 类型：**
1. **requiredDuringSchedulingIgnoredDuringExecution**：Pod 要被调度必须满足的规则（硬性要求）。
2. **preferredDuringSchedulingIgnoredDuringExecution**：希望满足但不是强制的规则（软性要求）。

**Pod Affinity 示例：**
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

在此示例中：
1. **Pod Affinity**：web server Pod 必须调度到与带有 `app=cache` label 的 Pod 相同的 Node（`kubernetes.io/hostname`）上。
2. **Pod Anti-Affinity**：web server Pod 最好调度到与其他带有 `app=web` label 的 Pod 不同的 Node 上。

**常见 Topology Key：**
1. **kubernetes.io/hostname**：Node 级别关系
2. **topology.kubernetes.io/zone**：Zone 级别关系
3. **topology.kubernetes.io/region**：Region 级别关系

**使用场景：**
1. **高可用性**：将同一应用程序的实例分散到不同 Node、zone、region 中
2. **性能优化**：将彼此通信的 Pod 放置在同一 Node 上，以尽量降低延迟
3. **资源隔离**：将资源密集型 Pod 分散到不同 Node 上
4. **许可证限制**：将存在许可证限制的应用程序集中到特定 Node 上

**Pod Affinity 与 Node Affinity：**
- **Node Affinity**：定义 Pod 与 Node 之间的关系。
- **Pod Affinity**：定义 Pod 之间的关系。

**Pod Affinity 和 Anti-Affinity 的性能影响：**
Pod affinity 和 anti-affinity 可能计算成本较高，因为它们需要考虑所有 Node 和 Pod。尤其是在大型集群中，它们可能影响调度性能，因此应谨慎使用。

**在 Custom Scheduler 中处理 Pod Affinity：**
实现 Custom Scheduler 时，应考虑 Pod 的 affinity 和 anti-affinity 要求。

```go
// Pod affinity check example
func checkPodAffinity(pod *v1.Pod, node *v1.Node, allPods []*v1.Pod) bool {
    affinity := pod.Spec.Affinity
    if affinity == nil || affinity.PodAffinity == nil {
        return true  // All nodes are suitable if there's no pod affinity
    }

    // Check required pod affinity
    for _, term := range affinity.PodAffinity.RequiredDuringSchedulingIgnoredDuringExecution {
        if !satisfiesPodAffinityTerm(pod, node, term, allPods) {
            return false
        }
    }

    return true
}

// Pod anti-affinity check example
func checkPodAntiAffinity(pod *v1.Pod, node *v1.Node, allPods []*v1.Pod) bool {
    affinity := pod.Spec.Affinity
    if affinity == nil || affinity.PodAntiAffinity == nil {
        return true  // All nodes are suitable if there's no pod anti-affinity
    }

    // Check required pod anti-affinity
    for _, term := range affinity.PodAntiAffinity.RequiredDuringSchedulingIgnoredDuringExecution {
        if satisfiesPodAffinityTerm(pod, node, term, allPods) {
            return false
        }
    }

    return true
}

// Check if pod affinity term is satisfied
func satisfiesPodAffinityTerm(pod *v1.Pod, node *v1.Node, term v1.PodAffinityTerm, allPods []*v1.Pod) bool {
    // Implementation omitted
    return true
}
```

**其他选项的问题：**
- A. 定义 Pod 与 Node 之间的关系：这是 nodeAffinity 的作用。
- B. 定义 Pod 与 volume 之间的关系：这是 volume binding 和 PersistentVolumeClaim 的作用。
- D. 定义 Pod 与 Service 之间的关系：这通过 Service label selector 处理。
</details>

### 7. Kubernetes Scheduler 中 “QueueSort” 扩展点的作用是什么？

A. 为 Node 评分
B. 排除 Pod 无法运行的 Node
C. 对调度队列中的 Pod 进行排序
D. 将 Pod 绑定到 Node

<details>
<summary>显示答案</summary>

**答案：C. 对调度队列中的 Pod 进行排序**

**解析：**
Kubernetes 调度框架中 “QueueSort” 扩展点的作用是对调度队列中的 Pod 进行排序。该扩展点设置决定哪些 Pod 先被调度的优先级。

**Scheduling Queue 与 QueueSort：**
Scheduler 会逐个处理调度队列中的 Pod。QueueSort plugin 决定该队列中 Pod 的顺序。默认情况下，Kubernetes 使用 `PrioritySort` plugin 按 Pod 优先级排序。

**QueueSort Plugin 接口：**
```go
type QueueSortPlugin interface {
    Plugin
    // Less determines which of two pods should be scheduled first.
    // Returns true if pInfo1 should be scheduled before pInfo2.
    Less(*QueuedPodInfo, *QueuedPodInfo) bool
}
```

**默认 QueueSort Plugin - PrioritySort：**
```go
// PrioritySort sorts pods by pod priority.
type PrioritySort struct{}

// Name returns the plugin name.
func (pl *PrioritySort) Name() string {
    return Name
}

// Less determines which of two pods should be scheduled first.
func (pl *PrioritySort) Less(pInfo1, pInfo2 *framework.QueuedPodInfo) bool {
    p1 := getPodPriority(pInfo1.Pod)
    p2 := getPodPriority(pInfo2.Pod)

    // Higher priority pods are scheduled first.
    if p1 != p2 {
        return p1 > p2
    }

    // If priorities are equal, pods with longer wait time are scheduled first.
    return pInfo1.Timestamp.Before(pInfo2.Timestamp)
}
```

**Custom QueueSort Plugin 示例：**
```go
// CustomQueueSort implements custom sorting logic.
type CustomQueueSort struct{}

// Name returns the plugin name.
func (pl *CustomQueueSort) Name() string {
    return "CustomQueueSort"
}

// Less determines which of two pods should be scheduled first.
func (pl *CustomQueueSort) Less(pInfo1, pInfo2 *framework.QueuedPodInfo) bool {
    // Example: Prioritize pods in a specific namespace
    if pInfo1.Pod.Namespace == "high-priority-namespace" && pInfo2.Pod.Namespace != "high-priority-namespace" {
        return true
    }
    if pInfo1.Pod.Namespace != "high-priority-namespace" && pInfo2.Pod.Namespace == "high-priority-namespace" {
        return false
    }

    // Example: Prioritize pods with a specific label
    if hasLabel(pInfo1.Pod, "critical") && !hasLabel(pInfo2.Pod, "critical") {
        return true
    }
    if !hasLabel(pInfo1.Pod, "critical") && hasLabel(pInfo2.Pod, "critical") {
        return false
    }

    // By default, consider priority and wait time
    p1 := getPodPriority(pInfo1.Pod)
    p2 := getPodPriority(pInfo2.Pod)

    if p1 != p2 {
        return p1 > p2
    }

    return pInfo1.Timestamp.Before(pInfo2.Timestamp)
}

// Check if pod has a specific label
func hasLabel(pod *v1.Pod, label string) bool {
    _, exists := pod.Labels[label]
    return exists
}
```

**在 Scheduler 配置中启用 QueueSort Plugin：**
```yaml
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
profiles:
- schedulerName: custom-scheduler
  plugins:
    queueSort:
      enabled:
      - name: CustomQueueSort
      disabled:
      - name: PrioritySort  # Disable default plugin
```

**QueueSort Plugin 的特征：**
1. **单一激活**：一次只能有一个 QueueSort plugin 处于活动状态。
2. **全局影响**：QueueSort plugin 会影响调度队列中的所有 Pod。
3. **性能重要性**：高效的排序算法很重要；复杂逻辑可能影响调度性能。

**QueueSort Plugin 使用场景：**
1. **业务优先级**：按业务重要性对 Pod 排序
2. **资源效率**：优先调度资源请求较小的 Pod，以利用空闲空间
3. **Service Level Agreements (SLA)**：根据 SLA 要求对 Pod 排序
4. **批处理**：调整批处理作业与交互式作业之间的优先级

**监控 Scheduling Queue：**
```bash
# Check queue information in scheduler logs
kubectl logs -n kube-system <scheduler-pod> | grep -i queue

# Check pods pending scheduling
kubectl get pods --all-namespaces -o wide | grep -i pending
```

**其他选项的问题：**
- A. 为 Node 评分：这是 “Score” 扩展点的作用。
- B. 排除 Pod 无法运行的 Node：这是 “Filter” 扩展点的作用。
- D. 将 Pod 绑定到 Node：这是 “Bind” 扩展点的作用。
</details>
### 8. Kubernetes 中 Pod Priority Preemption 的主要目的是什么？

A. 移除较低优先级的 Pod，以便调度较高优先级的 Pod
B. 为较高优先级的 Pod 分配更多资源
C. 让较高优先级的 Pod 运行得更快
D. 仅将较高优先级的 Pod 放置在特定 Node 上

<details>
<summary>显示答案</summary>

**答案：A. 移除较低优先级的 Pod，以便调度较高优先级的 Pod**

**解析：**
Kubernetes 中 Pod Priority Preemption 的主要目的是移除较低优先级的 Pod，以便调度较高优先级的 Pod。当集群资源不足且较高优先级 Pod 无法调度时，Scheduler 会抢占（移除）较低优先级的 Pod 来释放空间。

**Pod Priority 和 Preemption 机制：**
1. **PriorityClass 定义**：定义 Pod 优先级的集群级 resource。
2. **为 Pod 分配优先级**：Pod 通过 `spec.priorityClassName` 引用 PriorityClass。
3. **调度顺序**：较高优先级的 Pod 会在调度队列中先被处理。
4. **Preemption 流程**：当较高优先级的 Pod 无法调度时，Scheduler 会移除较低优先级的 Pod 来释放空间。

**PriorityClass 示例：**
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

**将优先级应用到 Pod：**
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

**Preemption Policy：**
PriorityClass 具有 `preemptionPolicy` 字段，可使用以下值：
1. **PreemptLowerPriority (default)**：可以抢占较低优先级的 Pod。
2. **Never**：不抢占较低优先级的 Pod。

```yaml
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: high-priority-no-preemption
value: 1000000
globalDefault: false
description: "High priority pods that do not preempt other pods"
preemptionPolicy: Never  # Do not preempt
```

**Preemption 流程：**
1. Scheduler 尝试调度较高优先级的 Pod。
2. 如果没有合适的 Node，Scheduler 会识别每个 Node 上的 preemption candidate Pod。
3. Preemption candidate 从较低优先级的 Pod 中选择。
4. Scheduler 会抢占最少数量的 Pod，以释放所需资源。
5. 被选中的 Pod 会被优雅终止。
6. 一旦被抢占的 Pod 终止，较高优先级的 Pod 就会被调度。

**Preemption 注意事项：**
1. **优雅终止期**：被抢占的 Pod 有 `terminationGracePeriodSeconds` 的优雅终止时间（默认：30 秒）。
2. **Pod Disruption Budget (PDB)**：Scheduler 会尽可能避免违反 PDB。
3. **Node taints**：抢占之后，可能会向 Node 添加 taint，以防止新的 Pod 被调度。
4. **System pods**：系统关键 Pod 通常具有非常高的优先级，不会被抢占。

**检查 Preemption 事件：**
```bash
# Check preemption events
kubectl get events | grep -i preempt
```

**监控与 Preemption 相关的指标：**
```bash
# Check preemption-related metrics in scheduler metrics
kubectl get --raw /metrics | grep scheduler_preemption
```

**在 Custom Scheduler 中实现 Preemption：**
实现 Custom Scheduler 时，应考虑 Pod priority 和 preemption 机制。

```go
// Preemption logic example
func preempt(pod *v1.Pod, nodes []*v1.Node) *v1.Node {
    // Check pod priority
    podPriority := getPodPriority(pod)

    // Identify preemptable pods on each node
    for _, node := range nodes {
        // Get pods running on the node
        nodePods := getPodsOnNode(node)

        // Identify preemption candidate pods
        var victims []*v1.Pod
        for _, p := range nodePods {
            // Select only lower priority pods
            if getPodPriority(p) < podPriority {
                victims = append(victims, p)
            }
        }

        // Check if resources are sufficient after preemption
        if hasEnoughResourcesAfterPreemption(node, victims, pod) {
            // Execute preemption
            for _, victim := range victims {
                evictPod(victim)
            }
            return node
        }
    }

    return nil  // No suitable node found
}
```

**Preemption 的优缺点：**
优点：
- 保证重要工作负载的调度
- 高效使用集群资源
- 支持 Service Level Agreement (SLA) 合规性

缺点：
- 被抢占 Pod 会受到中断
- 抢占后重新调度会产生开销
- 抢占决策逻辑复杂

**其他选项的问题：**
- B. 为较高优先级的 Pod 分配更多资源：Pod priority 不会直接影响资源分配。Resource requests 和 limits 在 Pod spec 中单独定义。
- C. 让较高优先级的 Pod 运行得更快：Priority 会影响调度顺序，但不会改变 Pod 本身的执行速度。
- D. 仅将较高优先级的 Pod 放置在特定 Node 上：这是 nodeSelector 或 nodeAffinity 的作用，与 priority 没有直接关系。
</details>

### 9. Kubernetes Scheduler 中 “PreFilter” 扩展点的作用是什么？

A. 在过滤之前对 Pod 和集群状态执行预处理
B. 在过滤之后为 Node 评分
C. 在将 Pod 绑定到 Node 之前执行验证
D. 对调度队列中的 Pod 进行排序

<details>
<summary>显示答案</summary>

**答案：A. 在过滤之前对 Pod 和集群状态执行预处理**

**解析：**
Kubernetes 调度框架中 “PreFilter” 扩展点的作用是在过滤之前对 Pod 和集群状态执行预处理。PreFilter plugin 会准备在过滤阶段使用的数据，并可以预先检查 Pod 是否能够被调度。

**PreFilter 扩展点的主要功能：**
1. **数据准备**：初始化并准备在过滤阶段使用的数据结构。
2. **预检查**：预先检查 Pod 是否可以被调度。
3. **状态存储**：存储在调度周期中使用的状态信息。
4. **优化**：防止不必要的过滤工作以优化性能。

**PreFilter Plugin 接口：**
```go
type PreFilterPlugin interface {
    Plugin
    // PreFilter performs preprocessing on the pod before filtering.
    PreFilter(ctx context.Context, state *CycleState, pod *v1.Pod) *Status
    // PreFilterExtensions returns an interface that provides additional functionality.
    PreFilterExtensions() PreFilterExtensions
}

type PreFilterExtensions interface {
    // AddPod updates state when a pod is added to a node.
    AddPod(ctx context.Context, state *CycleState, podToAdd *v1.Pod, nodeInfo *NodeInfo) *Status
    // RemovePod updates state when a pod is removed from a node.
    RemovePod(ctx context.Context, state *CycleState, podToRemove *v1.Pod, nodeInfo *NodeInfo) *Status
}
```

**默认 PreFilter Plugin：**
Kubernetes 提供以下默认 PreFilter plugin：

1. **InterPodAffinity**：处理 Pod 间 affinity 和 anti-affinity 要求。
2. **NodeAffinity**：处理 node affinity 要求。
3. **NodePorts**：处理 Pod 请求的 host port。
4. **NodeResourcesFit**：处理 Node 资源要求。
5. **PodTopologySpread**：处理 Pod topology spread constraints。
6. **VolumeBinding**：处理 volume binding 要求。

**Custom PreFilter Plugin 示例：**
```go
// CustomPreFilter implements custom pre-filtering logic.
type CustomPreFilter struct {
    handle framework.Handle
}

// Name returns the plugin name.
func (pl *CustomPreFilter) Name() string {
    return "CustomPreFilter"
}

// PreFilter performs preprocessing on the pod before filtering.
func (pl *CustomPreFilter) PreFilter(ctx context.Context, state *framework.CycleState, pod *v1.Pod) *framework.Status {
    // Example: Check if the pod is schedulable according to certain conditions
    if !isPodSchedulable(pod) {
        return framework.NewStatus(framework.Unschedulable, "Pod does not meet custom requirements")
    }

    // Example: Store data to be used in the filtering stage
    data := &customPreFilterState{
        // Initialize required data
    }
    state.Write(stateKey, data)

    return nil
}

// PreFilterExtensions returns an interface that provides additional functionality.
func (pl *CustomPreFilter) PreFilterExtensions() framework.PreFilterExtensions {
    return nil  // Return nil if no extension functionality is needed
}

// State data structure
type customPreFilterState struct {
    // Define required fields
}

// State key
var stateKey = framework.StateKey("CustomPreFilter")

// Function to check if pod is schedulable
func isPodSchedulable(pod *v1.Pod) bool {
    // Implement custom logic
    return true
}
```

**在 Scheduler 配置中启用 PreFilter Plugin：**
```yaml
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
profiles:
- schedulerName: custom-scheduler
  plugins:
    preFilter:
      enabled:
      - name: CustomPreFilter
      disabled:
      - name: NodeResourcesFit  # Disable default plugin
```

**PreFilter 与 Filter 的关系：**
1. **PreFilter**：在开始对所有 Node 进行过滤之前运行一次。
2. **Filter**：针对每个 Node 单独运行。

PreFilter 会准备 Filter 阶段要使用的数据，并预先识别 Pod 无法调度到任何 Node 的情况，以防止不必要的过滤工作。

**PreFilter 使用场景：**
1. **复杂约束处理**：高效处理 Pod 间 affinity、topology spread 等复杂约束
2. **预验证**：预先检查 Pod 是否可以调度，以防止不必要的处理
3. **数据缓存**：预先计算过滤阶段会重复使用的数据，以提升性能
4. **状态共享**：管理多个 plugin 之间共享的状态信息

**其他选项的问题：**
- B. 在过滤之后为 Node 评分：这是 “Score” 扩展点的作用。
- C. 在将 Pod 绑定到 Node 之前执行验证：这是 “PreBind” 扩展点的作用。
- D. 对调度队列中的 Pod 进行排序：这是 “QueueSort” 扩展点的作用。
</details>

### 10. Kubernetes 中 Node taint `node.kubernetes.io/unreachable:NoExecute` 表示什么？

A. Node 不可达，并且没有 toleration 的 Pod 会被移除
B. Node 不可调度，但现有 Pod 继续运行
C. Node 处于维护模式，新 Pod 不会被调度
D. Node 处于资源短缺状态，新 Pod 最好不要被调度

<details>
<summary>显示答案</summary>

**答案：A. Node 不可达，并且没有 toleration 的 Pod 会被移除**

**解析：**
Kubernetes 中 Node taint `node.kubernetes.io/unreachable:NoExecute` 表示该 Node 不可达，并且没有针对该 taint 的 toleration 的 Pod 会从该 Node 上被移除（驱逐）。该 taint 由 node controller 自动添加，当 Node 状态从 `Ready` 变为 `Unknown` 时应用。

**Node Unreachable 状态：**
Node 变为不可达的常见原因：
1. 网络连接问题
2. kubelet 进程崩溃
3. Node 系统故障
4. Node 电源问题

**Taint 组件：**
1. **Key**：`node.kubernetes.io/unreachable`
2. **Value**：通常为空字符串，但也可能有值。
3. **Effect**：`NoExecute` - 没有 toleration 的 Pod 会从 Node 上被移除。

**NoExecute Effect：**
`NoExecute` effect 会导致以下行为：
1. 新 Pod 不会被调度到带有该 taint 的 Node 上。
2. 已经在该 Node 上运行的 Pod 中，没有针对该 taint 的 toleration 的 Pod 会被移除。

**系统 Taints：**
Kubernetes 会根据 Node 状态自动添加以下系统 taint：
1. **node.kubernetes.io/not-ready:NoExecute**：Node 未就绪
2. **node.kubernetes.io/unreachable:NoExecute**：Node 不可达
3. **node.kubernetes.io/memory-pressure:NoSchedule**：Node 存在内存压力
4. **node.kubernetes.io/disk-pressure:NoSchedule**：Node 存在磁盘压力
5. **node.kubernetes.io/pid-pressure:NoSchedule**：Node 存在 PID 压力
6. **node.kubernetes.io/network-unavailable:NoSchedule**：Node 网络不可用
7. **node.kubernetes.io/unschedulable:NoSchedule**：Node 被标记为不可调度

**默认 Tolerations：**
Kubernetes 会自动向所有 Pod 添加以下默认 toleration：
```yaml
tolerations:
- key: node.kubernetes.io/not-ready
  operator: Exists
  effect: NoExecute
  tolerationSeconds: 300
- key: node.kubernetes.io/unreachable
  operator: Exists
  effect: NoExecute
  tolerationSeconds: 300
```

这些默认 toleration 允许 Pod 在 Node 变为未就绪或不可达时，在该 Node 上保留 5 分钟（300 秒），从而避免因临时网络问题导致不必要的 Pod 重新调度。

**自定义 Tolerations：**
对于关键工作负载，可以设置更长的 toleration 时间：
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: critical-pod
spec:
  tolerations:
  - key: node.kubernetes.io/unreachable
    operator: Exists
    effect: NoExecute
    tolerationSeconds: 600  # Tolerate for 10 minutes
  containers:
  - name: nginx
    image: nginx
```

**Node Controller 设置：**
Node controller 通过以下设置控制 Node 状态变更和 taint 应用行为：
1. **--node-monitor-period**：检查 Node 状态的周期（默认：5 秒）
2. **--node-monitor-grace-period**：在将 Node 标记为 `Unknown` 之前等待的时间（默认：40 秒）
3. **--pod-eviction-timeout**：在从 `Unknown` 或 `NotReady` Node 上移除 Pod 之前等待的时间（默认：5 分钟）

**检查 Node 状态和 Taints：**
```bash
# Check node status
kubectl get nodes

# Check node details
kubectl describe node <node-name>

# Check node taints
kubectl get node <node-name> -o jsonpath='{.spec.taints}'
```

**检查 Pod Tolerations：**
```bash
# Check pod tolerations
kubectl get pod <pod-name> -o jsonpath='{.spec.tolerations}'
```

**在 Custom Scheduler 中处理 Taints：**
实现 Custom Scheduler 时，应考虑 Node taint 和 Pod toleration。

```go
// Taint handling example
func checkNodeUnreachableTaint(node *v1.Node) bool {
    for _, taint := range node.Spec.Taints {
        if taint.Key == "node.kubernetes.io/unreachable" && taint.Effect == v1.TaintEffectNoExecute {
            return true  // Node has unreachable taint
        }
    }
    return false
}
```

**其他选项的问题：**
- B. Node 不可调度，但现有 Pod 继续运行：这是 `NoSchedule` effect 的行为；`NoExecute` effect 还会移除没有 toleration 的现有 Pod。
- C. Node 处于维护模式，新 Pod 不会被调度：这通常是 `node.kubernetes.io/unschedulable:NoSchedule` taint 的行为。
- D. Node 处于资源短缺状态，新 Pod 最好不要被调度：这是 `PreferNoSchedule` effect 的行为，资源短缺通常由 `node.kubernetes.io/memory-pressure` 或 `node.kubernetes.io/disk-pressure` taint 表示。
</details>
