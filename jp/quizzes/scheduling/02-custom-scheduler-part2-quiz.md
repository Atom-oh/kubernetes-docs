# Custom Scheduler クイズ (Part 2)

このクイズでは、Kubernetes で Custom Scheduler を実装し使用するための高度な理解を確認します。

## クイズ問題

### 1. Kubernetes scheduling framework における "Bind" extension point の役割は何ですか？

A. scheduling decision を確定するために Pod を Node に bind する
B. Pod と Node の間の network binding を設定する
C. Pod と Service の間の binding を作成する
D. Pod と volume の間の binding を設定する

<details>
<summary>回答を表示</summary>

**回答: A. scheduling decision を確定するために Pod を Node に bind する**

**解説:**
Kubernetes scheduling framework における "Bind" extension point の役割は、選択された Node に Pod を bind し、scheduling decision を確定することです。binding stage は scheduling cycle の最終 stage であり、kubelet が Pod を実行できるように Pod の `spec.nodeName` field が設定されます。

**Binding Process:**
1. scheduler は filtering と scoring を通じて最適な Node を選択します。
2. 選択された Node に Pod を予約します (reserve)。
3. binding stage で、Pod の `spec.nodeName` field を選択された Node の名前に更新します。
4. 更新された Pod 情報が API server に保存されます。
5. kubelet が Pod 情報を検出し、その Node 上で Pod を実行します。

**Bind Plugin Implementation Example:**
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

**Enabling Bind Plugin in Scheduler Configuration:**
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

**Checking Binding-Related Events:**
```bash
# Check pod scheduling events
kubectl get events | grep -i "Successfully assigned"
```

**Troubleshooting Binding Failures:**
binding stage で失敗する一般的な原因:
1. API server 接続の問題
2. 権限不足
3. Node 名の誤り
4. Race condition（別の scheduler が同じ Pod を同時に bind しようとしている）

**Issues with Other Options:**
- B. Pod と Node の間の network binding を設定する: Network setup は CNI plugin の役割であり、scheduler の bind stage とは関係ありません。
- C. Pod と Service の間の binding を作成する: Service と Pod の接続は label selector を通じて行われ、scheduler の bind stage とは関係ありません。
- D. Pod と volume の間の binding を設定する: Volume binding は PersistentVolumeClaim controller によって処理され、scheduler の bind stage とは別の process です。
</details>

### 2. 次のうち、Kubernetes の Node Affinity に関連する operator ではないものはどれですか？

A. In
B. NotIn
C. Exists
D. Contains

<details>
<summary>回答を表示</summary>

**回答: D. Contains**

**解説:**
Kubernetes の Node Affinity に関連しない operator は `Contains` です。Kubernetes は node affinity に対して `Contains` operator を提供していません。

**Operators Supported in Node Affinity:**
1. **In**: Label value は指定された値のいずれかに一致する必要があります。
2. **NotIn**: Label value は指定された値に一致してはいけません。
3. **Exists**: 指定された label key が存在する必要があります。
4. **DoesNotExist**: 指定された label key が存在してはいけません。
5. **Gt**: Label value は指定された値より大きい必要があります (Greater than)。
6. **Lt**: Label value は指定された値より小さい必要があります (Less than)。

**Node Affinity Example:**
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

**Node Affinity Types:**
1. **requiredDuringSchedulingIgnoredDuringExecution**: Pod を Node に schedule するために満たす必要がある rule（hard requirement）。
2. **preferredDuringSchedulingIgnoredDuringExecution**: 満たされることが望ましいが必須ではない rule（soft requirement）。

**Operator Usage Examples:**
1. **In Operator**:
   ```yaml
   - key: kubernetes.io/e2e-az-name
     operator: In
     values:
     - e2e-az1
     - e2e-az2
   ```
   Node の `kubernetes.io/e2e-az-name` label value は `e2e-az1` または `e2e-az2` である必要があります。

2. **NotIn Operator**:
   ```yaml
   - key: kubernetes.io/e2e-az-name
     operator: NotIn
     values:
     - e2e-az3
   ```
   Node の `kubernetes.io/e2e-az-name` label value は `e2e-az3` であってはいけません。

3. **Exists Operator**:
   ```yaml
   - key: kubernetes.io/e2e-az-name
     operator: Exists
   ```
   `kubernetes.io/e2e-az-name` label は Node 上に存在する必要があります。

4. **DoesNotExist Operator**:
   ```yaml
   - key: emptyLabel
     operator: DoesNotExist
   ```
   `emptyLabel` label は Node 上に存在してはいけません。

5. **Gt/Lt Operators**:
   ```yaml
   - key: node-size
     operator: Gt
     values:
     - "10"
   ```
   Node の `node-size` label value は 10 より大きい必要があります。

**Handling Node Affinity in Custom Scheduler:**
Custom Scheduler を実装する際は、Pod の node affinity 要件を考慮する必要があります。

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

**Explanation of Other Options:**
- A. In: 有効な node affinity operator です。
- B. NotIn: 有効な node affinity operator です。
- C. Exists: 有効な node affinity operator です。
</details>

### 3. Kubernetes における Pod Topology Spread Constraints の主な目的は何ですか？

A. さまざまな Node に Pod を均等に分散する
B. Pod を特定の Node にのみ配置する
C. Pod を特定の zone にのみ配置する
D. Pod を特定の label を持つ Node にのみ配置する

<details>
<summary>回答を表示</summary>

**回答: A. さまざまな Node に Pod を均等に分散する**

**解説:**
Kubernetes における Pod Topology Spread Constraints の主な目的は、さまざまな topology domain（Node、zone、region など）に Pod を均等に分散することです。これにより、application の高可用性が向上し、resource usage が最適化され、failure tolerance が向上します。

**Main Components of Pod Topology Spread Constraints:**
1. **maxSkew**: topology domain 間の Pod 数の最大差を指定します。
2. **topologyKey**: Pod を分散する topology domain を定義する Node label key です。
3. **whenUnsatisfiable**: constraint を満たせない場合の動作を指定します。
   - `DoNotSchedule`: constraint が満たされない場合、Pod を schedule しません。
   - `ScheduleAnyway`: constraint が満たされなくても Pod を schedule します。
4. **labelSelector**: spread calculation で考慮する既存の Pod を選択する label selector です。

**Pod Topology Spread Constraints Example:**
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

この例では、2 つの constraint が定義されています:
1. 各 Node（`kubernetes.io/hostname`）間で、`app=web` label を持つ Pod 数の差は最大 1 である必要があります。
2. 各 zone（`topology.kubernetes.io/zone`）間で、`app=web` label を持つ Pod 数の差は最大 2 である必要があります。

**Topology Spread Calculation Method:**
1. 各 topology domain で label selector に一致する Pod 数を計算します。
2. 最も多くの Pod を持つ domain と最も少ない Pod を持つ domain の差を計算します。
3. この差が `maxSkew` より大きい場合、constraint に違反しています。

**Common Topology Keys:**
1. **kubernetes.io/hostname**: Node-level spread
2. **topology.kubernetes.io/zone**: Zone-level spread
3. **topology.kubernetes.io/region**: Region-level spread
4. **node.kubernetes.io/instance-type**: Instance type-level spread

**Use Cases:**
1. **High availability**: 複数の Node、zone、region に Pod を分散して failure tolerance を向上させる
2. **Resource balance**: workload を cluster 全体に均等に分散する
3. **Cost optimization**: workload を特定 type の Node に分散する
4. **Performance optimization**: network latency を最小化するように分散する

**Handling Topology Spread in Custom Scheduler:**
Custom Scheduler を実装する際は、Pod の topology spread constraints を考慮する必要があります。

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

**Issues with Other Options:**
- B. Pod を特定の Node にのみ配置する: これは nodeSelector または nodeAffinity の役割です。
- C. Pod を特定の zone にのみ配置する: これは node affinity を使って Pod を特定の zone に配置することです。topology spread constraints の主な目的は均等な分散です。
- D. Pod を特定の label を持つ Node にのみ配置する: これは nodeSelector または nodeAffinity の役割です。
</details>
### 4. Kubernetes における Taints and Tolerations の主な目的は何ですか？

A. 特定の Pod が特定の Node にのみ schedule されることを保証する
B. 特定の Pod が特定の Node に schedule されるのを防ぐ
C. Node が特定の Pod を拒否し、Pod がそれを許容できるようにする
D. Pod 間の通信を制限する

<details>
<summary>回答を表示</summary>

**回答: C. Node が特定の Pod を拒否し、Pod がそれを許容できるようにする**

**解説:**
Kubernetes における Taints and Tolerations の主な目的は、Node が特定の Pod を拒否し、Pod がそれを許容できるようにすることです。Taint は Pod が schedule されるのを防ぐために Node に適用され、toleration は特定の taint を持つ Node への scheduling を許可するために Pod に適用されます。

**How Taints and Tolerations Work:**
1. **Taints**: その Node への Pod scheduling を制限するために Node に適用されます。
2. **Tolerations**: 特定の taint を持つ Node への scheduling を許可するために Pod に適用されます。
3. **Effect**: taint の effect は、toleration を持たない Pod に対する動作を定義します。

**Taint Effect Types:**
1. **NoSchedule**: toleration を持たない Pod はその Node に schedule されません。
2. **PreferNoSchedule**: toleration を持たない Pod はできればその Node に schedule されませんが、cluster resource が不足している場合は schedule される可能性があります。
3. **NoExecute**: toleration を持たない Pod はその Node に schedule されず、すでに実行中の Pod は削除されます。

**Taint Application Example:**
```bash
# Apply taint to node
kubectl taint nodes node1 key=value:NoSchedule

# Remove taint from node
kubectl taint nodes node1 key=value:NoSchedule-
```

**Taint and Toleration Example:**
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

**Toleration Operators:**
1. **Equal**: Key と value が一致する必要があります。
2. **Exists**: Key のみ一致すればよいです（value は無視されます）。

**Additional Toleration Field:**
- **tolerationSeconds**: NoExecute effect で削除されるまで、Pod が Node 上に残ることができる時間（秒）を指定します。

```yaml
tolerations:
- key: "node.kubernetes.io/not-ready"
  operator: "Exists"
  effect: "NoExecute"
  tolerationSeconds: 300
```

**Common Use Cases:**
1. **Dedicated nodes**: 特定の workload 専用に Node を予約する
2. **Special hardware**: GPU などの special hardware を持つ Node にのみ特定の Pod を schedule する
3. **Node maintenance**: Node maintenance 中に新しい Pod scheduling を防ぐ
4. **Master node protection**: control plane node に一般的な workload が schedule されるのを防ぐ

**System Taints:**
Kubernetes は次の system taints を自動的に適用します:
1. **node.kubernetes.io/not-ready**: Node is not ready
2. **node.kubernetes.io/unreachable**: Node is unreachable
3. **node.kubernetes.io/memory-pressure**: Node has memory pressure
4. **node.kubernetes.io/disk-pressure**: Node has disk pressure
5. **node.kubernetes.io/pid-pressure**: Node has PID pressure
6. **node.kubernetes.io/network-unavailable**: Node's network is unavailable
7. **node.kubernetes.io/unschedulable**: Node is marked as unschedulable

**Handling Taints and Tolerations in Custom Scheduler:**
Custom Scheduler を実装する際は、Node taints と Pod tolerations を考慮する必要があります。

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

**Issues with Other Options:**
- A. 特定の Pod が特定の Node にのみ schedule されることを保証する: これは nodeSelector または nodeAffinity の役割です。
- B. 特定の Pod が特定の Node に schedule されるのを防ぐ: これは podAntiAffinity の役割です。
- D. Pod 間の通信を制限する: これは NetworkPolicy の役割です。
</details>

### 5. 次のうち、Kubernetes における Scheduler Extender の主な特性ではないものはどれですか？

A. HTTP webhook を通じて scheduler と通信する
B. filtering と prioritization の機能を提供する
C. scheduler codebase に直接統合されている
D. 外部 process として実行される

<details>
<summary>回答を表示</summary>

**回答: C. scheduler codebase に直接統合されている**

**解説:**
「scheduler codebase に直接統合されている」は、Kubernetes における Scheduler Extender の主な特性ではありません。Scheduler extender は scheduler codebase に直接統合されておらず、HTTP webhook を通じて通信し、外部 process として実行されます。これは scheduling framework plugin との主な違いです。

**Main Characteristics of Scheduler Extender:**
1. **HTTP webhooks**: scheduler は HTTP request を通じて extender と通信します。
2. **External process**: extender は scheduler とは別の process として実行されます。
3. **Filtering and prioritization**: extender は Node filtering と prioritization の機能を提供できます。
4. **Binding**: extender は任意で Pod を Node に bind できます。

**Scheduler Extender Configuration Example:**
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

**Scheduler Extender API:**
1. **Filter API**: Node list を受け取り、filtered node list を返します。
   ```
   POST /filter
   ```
   Request body:
   ```json
   {
     "pod": <pod>,
     "nodes": <nodes>,
     "nodenames": <node-names>
   }
   ```
   Response body:
   ```json
   {
     "nodes": <filtered-nodes>,
     "nodenames": <filtered-node-names>,
     "failedNodes": <failed-nodes>,
     "error": <error-message>
   }
   ```

2. **Prioritize API**: Node list を受け取り、各 Node に score を割り当てます。
   ```
   POST /prioritize
   ```
   Request body:
   ```json
   {
     "pod": <pod>,
     "nodes": <nodes>,
     "nodenames": <node-names>
   }
   ```
   Response body:
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

3. **Bind API**: Pod を Node に bind します。
   ```
   POST /bind
   ```
   Request body:
   ```json
   {
     "pod": <pod>,
     "node": <node-name>
   }
   ```
   Response body:
   ```json
   {
     "error": <error-message>
   }
   ```

**Scheduler Extender Implementation Example (Go):**
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

**Scheduler Extender vs Scheduling Framework Plugin:**

| Feature | Scheduler Extender | Scheduling Framework Plugin |
|---------|-------------------|---------------------------|
| Integration Method | HTTP webhook | Direct codebase integration |
| Execution Mode | External process | Inside scheduler |
| Performance | Relatively slower due to HTTP overhead | Faster due to direct integration |
| Development Language | No restriction | Go |
| Deployment | Separate service | Deployed with scheduler |
| Maintenance | Independent from scheduler | Linked to scheduler version |

**Pros and Cons of Scheduler Extender:**
Pros:
- scheduler codebase から独立して開発できます
- さまざまな programming language で実装できます
- scheduler upgrade の影響を受けにくいです

Cons:
- HTTP communication overhead による performance degradation
- scheduling cycle の一部の stage しか拡張できません
- scheduler と extender 間で communication failure が発生する可能性があります

**Explanation of Other Options:**
- A. HTTP webhook を通じて scheduler と通信する: scheduler extender の有効な特性です。
- B. filtering と prioritization の機能を提供する: scheduler extender の有効な特性です。
- D. 外部 process として実行される: scheduler extender の有効な特性です。
</details>
### 6. Kubernetes における Pod Affinity and Anti-Affinity の主な目的は何ですか？

A. Pod と Node の関係を定義する
B. Pod と volume の関係を定義する
C. Pod 間の関係を定義する
D. Pod と Service の関係を定義する

<details>
<summary>回答を表示</summary>

**回答: C. Pod 間の関係を定義する**

**解説:**
Kubernetes における Pod Affinity and Anti-Affinity の主な目的は、Pod 間の関係を定義することです。これにより、特定の Pod を他の Pod と同じ topology domain（Node、zone、region など）に配置するか（affinity）、配置しないか（anti-affinity）を制御できます。

**Main Components of Pod Affinity and Anti-Affinity:**
1. **topologyKey**: Pod 間の関係を定義する topology domain を指定する Node label key です。
2. **labelSelector**: 関係を確立する対象の Pod を選択する label selector です。
3. **namespaces**: label selector が適用される namespace の list です。

**Pod Affinity Types:**
1. **requiredDuringSchedulingIgnoredDuringExecution**: Pod を schedule するために満たす必要がある rule（hard requirement）。
2. **preferredDuringSchedulingIgnoredDuringExecution**: 満たされることが望ましいが必須ではない rule（soft requirement）。

**Pod Affinity Example:**
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

この例では:
1. **Pod Affinity**: web server Pod は、`app=cache` label を持つ Pod と同じ Node（`kubernetes.io/hostname`）に schedule される必要があります。
2. **Pod Anti-Affinity**: web server Pod は、できれば `app=web` label を持つ他の Pod とは異なる Node に schedule されるべきです。

**Common Topology Keys:**
1. **kubernetes.io/hostname**: Node-level relationship
2. **topology.kubernetes.io/zone**: Zone-level relationship
3. **topology.kubernetes.io/region**: Region-level relationship

**Use Cases:**
1. **High availability**: 同じ application の instance を異なる Node、zone、region に分散する
2. **Performance optimization**: 相互に通信する Pod を同じ Node に配置して latency を最小化する
3. **Resource isolation**: resource-intensive な Pod を異なる Node に分散する
4. **License restrictions**: license restriction がある application を特定の Node に集中させる

**Pod Affinity vs Node Affinity:**
- **Node Affinity**: Pod と Node の関係を定義します。
- **Pod Affinity**: Pod 間の関係を定義します。

**Performance Impact of Pod Affinity and Anti-Affinity:**
Pod affinity と anti-affinity は、すべての Node と Pod を考慮する必要があるため、計算コストが高くなる可能性があります。特に大規模 cluster では scheduling performance に影響する可能性があるため、慎重に使用する必要があります。

**Handling Pod Affinity in Custom Scheduler:**
Custom Scheduler を実装する際は、Pod の affinity と anti-affinity 要件を考慮する必要があります。

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

**Issues with Other Options:**
- A. Pod と Node の関係を定義する: これは nodeAffinity の役割です。
- B. Pod と volume の関係を定義する: これは volume binding と PersistentVolumeClaim の役割です。
- D. Pod と Service の関係を定義する: これは service label selector を通じて処理されます。
</details>

### 7. Kubernetes scheduler における "QueueSort" extension point の役割は何ですか？

A. Node を score する
B. Pod が実行できない Node を除外する
C. scheduling queue 内の Pod を sort する
D. Pod を Node に bind する

<details>
<summary>回答を表示</summary>

**回答: C. scheduling queue 内の Pod を sort する**

**解説:**
Kubernetes scheduling framework における "QueueSort" extension point の役割は、scheduling queue 内の Pod を sort することです。この extension point は、どの Pod を先に schedule するかを決定する priority を設定します。

**Scheduling Queue and QueueSort:**
scheduler は scheduling queue 内の Pod を 1 つずつ処理します。QueueSort plugin は、この queue 内の Pod の順序を決定します。デフォルトでは、Kubernetes は `PrioritySort` plugin を使用して Pod priority で sort します。

**QueueSort Plugin Interface:**
```go
type QueueSortPlugin interface {
    Plugin
    // Less determines which of two pods should be scheduled first.
    // Returns true if pInfo1 should be scheduled before pInfo2.
    Less(*QueuedPodInfo, *QueuedPodInfo) bool
}
```

**Default QueueSort Plugin - PrioritySort:**
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

**Custom QueueSort Plugin Example:**
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

**Enabling QueueSort Plugin in Scheduler Configuration:**
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

**Characteristics of QueueSort Plugin:**
1. **Single activation**: 同時に有効にできる QueueSort plugin は 1 つだけです。
2. **Global impact**: QueueSort plugin は scheduling queue 内のすべての Pod に影響します。
3. **Performance importance**: 効率的な sorting algorithm が重要です。複雑な logic は scheduling performance に影響する可能性があります。

**QueueSort Plugin Use Cases:**
1. **Business priority**: business importance に基づいて Pod を sort する
2. **Resource efficiency**: empty space を活用するために resource request が小さい Pod を先に schedule する
3. **Service Level Agreements (SLA)**: SLA 要件に従って Pod を sort する
4. **Batch processing**: batch job と interactive job の間の priority を調整する

**Monitoring Scheduling Queue:**
```bash
# Check queue information in scheduler logs
kubectl logs -n kube-system <scheduler-pod> | grep -i queue

# Check pods pending scheduling
kubectl get pods --all-namespaces -o wide | grep -i pending
```

**Issues with Other Options:**
- A. Node を score する: これは "Score" extension point の役割です。
- B. Pod が実行できない Node を除外する: これは "Filter" extension point の役割です。
- D. Pod を Node に bind する: これは "Bind" extension point の役割です。
</details>
### 8. Kubernetes における Pod Priority Preemption の主な目的は何ですか？

A. より高い priority の Pod を schedule できるように、より低い priority の Pod を削除する
B. より高い priority の Pod により多くの resource を割り当てる
C. より高い priority の Pod をより速く実行する
D. より高い priority の Pod を特定の Node にのみ配置する

<details>
<summary>回答を表示</summary>

**回答: A. より高い priority の Pod を schedule できるように、より低い priority の Pod を削除する**

**解説:**
Kubernetes における Pod Priority Preemption の主な目的は、より高い priority の Pod を schedule できるように、より低い priority の Pod を削除することです。cluster resource が不足し、より高い priority の Pod を schedule できない場合、scheduler はより低い priority の Pod を preempt（削除）して空き容量を確保します。

**Pod Priority and Preemption Mechanism:**
1. **PriorityClass definition**: Pod priority を定義する cluster-level resource です。
2. **Assign priority to pod**: Pod は `spec.priorityClassName` を通じて PriorityClass を参照します。
3. **Scheduling order**: より高い priority の Pod が scheduling queue で先に処理されます。
4. **Preemption process**: より高い priority の Pod を schedule できない場合、scheduler はより低い priority の Pod を削除して空き容量を確保します。

**PriorityClass Example:**
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

**Applying Priority to a Pod:**
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

**Preemption Policies:**
PriorityClass には、次の値を取ることができる `preemptionPolicy` field があります:
1. **PreemptLowerPriority (default)**: より低い priority の Pod を preempt できます。
2. **Never**: より低い priority の Pod を preempt しません。

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

**Preemption Process:**
1. scheduler がより高い priority の Pod を schedule しようとします。
2. 適切な Node がない場合、scheduler は各 Node 上の preemption candidate Pod を特定します。
3. preemption candidate は、より低い priority の Pod から選択されます。
4. scheduler は必要な resource を解放するために最小数の Pod を preempt します。
5. 選択された Pod は graceful に終了されます。
6. preempt された Pod が終了すると、より高い priority の Pod が schedule されます。

**Preemption Considerations:**
1. **Graceful termination period**: preempt された Pod には `terminationGracePeriodSeconds`（default: 30 seconds）の graceful termination time があります。
2. **Pod Disruption Budget (PDB)**: scheduler は可能な場合、PDB に違反しないようにします。
3. **Node taints**: preemption 後、新しい Pod が schedule されるのを防ぐために Node に taint が追加される場合があります。
4. **System pods**: system critical Pod は通常、非常に高い priority を持ち、preempt されません。

**Checking Preemption Events:**
```bash
# Check preemption events
kubectl get events | grep -i preempt
```

**Monitoring Preemption-Related Metrics:**
```bash
# Check preemption-related metrics in scheduler metrics
kubectl get --raw /metrics | grep scheduler_preemption
```

**Implementing Preemption in Custom Scheduler:**
Custom Scheduler を実装する際は、Pod priority と preemption mechanism を考慮する必要があります。

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

**Pros and Cons of Preemption:**
Pros:
- 重要な workload の scheduling を保証します
- cluster resource を効率的に使用します
- Service Level Agreement (SLA) compliance をサポートします

Cons:
- preempt された Pod の disruption
- preemption 後の rescheduling による overhead
- 複雑な preemption decision logic

**Issues with Other Options:**
- B. より高い priority の Pod により多くの resource を割り当てる: Pod priority は resource allocation に直接影響しません。Resource request と limit は Pod spec で別途定義されます。
- C. より高い priority の Pod をより速く実行する: Priority は scheduling order に影響しますが、Pod の execution speed 自体は変わりません。
- D. より高い priority の Pod を特定の Node にのみ配置する: これは nodeSelector または nodeAffinity の役割であり、priority とは直接関係ありません。
</details>

### 9. Kubernetes scheduler における "PreFilter" extension point の役割は何ですか？

A. filtering の前に Pod と cluster state に対して preprocessing を実行する
B. filtering 後に Node を score する
C. Pod を Node に bind する前に verification を実行する
D. scheduling queue 内の Pod を sort する

<details>
<summary>回答を表示</summary>

**回答: A. filtering の前に Pod と cluster state に対して preprocessing を実行する**

**解説:**
Kubernetes scheduling framework における "PreFilter" extension point の役割は、filtering の前に Pod と cluster state に対して preprocessing を実行することです。PreFilter plugin は filtering stage で使用する data を準備し、Pod を schedule できるかを事前に check できます。

**Main Functions of the PreFilter Extension Point:**
1. **Data preparation**: filtering stage で使用する data structure を初期化し準備します。
2. **Pre-checks**: Pod を schedule できるかを事前に check します。
3. **State storage**: scheduling cycle 中に使用する state information を保存します。
4. **Optimization**: 不要な filtering work を防ぎ、performance を最適化します。

**PreFilter Plugin Interface:**
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

**Default PreFilter Plugins:**
Kubernetes は次の default PreFilter plugin を提供しています:

1. **InterPodAffinity**: inter-pod affinity と anti-affinity 要件を処理します。
2. **NodeAffinity**: node affinity 要件を処理します。
3. **NodePorts**: Pod が要求する host port を処理します。
4. **NodeResourcesFit**: Node resource 要件を処理します。
5. **PodTopologySpread**: Pod topology spread constraints を処理します。
6. **VolumeBinding**: volume binding 要件を処理します。

**Custom PreFilter Plugin Example:**
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

**Enabling PreFilter Plugin in Scheduler Configuration:**
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

**Relationship Between PreFilter and Filter:**
1. **PreFilter**: すべての Node に対する filtering を開始する前に 1 回実行されます。
2. **Filter**: 各 Node に対して個別に実行されます。

PreFilter は Filter stage で使用する data を準備し、どの Node にも schedule できない Pod を事前に特定して、不要な filtering work を防ぎます。

**PreFilter Use Cases:**
1. **Complex constraint handling**: inter-pod affinity、topology spread などの複雑な constraint を効率的に処理する
2. **Pre-validation**: Pod を schedule できるかを事前に check し、不要な processing を防ぐ
3. **Data caching**: filtering stage で繰り返し使用される data を事前に計算し、performance を向上させる
4. **State sharing**: 複数の plugin 間で共有される state information を管理する

**Issues with Other Options:**
- B. filtering 後に Node を score する: これは "Score" extension point の役割です。
- C. Pod を Node に bind する前に verification を実行する: これは "PreBind" extension point の役割です。
- D. scheduling queue 内の Pod を sort する: これは "QueueSort" extension point の役割です。
</details>

### 10. Kubernetes における Node taint `node.kubernetes.io/unreachable:NoExecute` は何を意味しますか？

A. Node が unreachable であり、toleration を持たない Pod は削除される
B. Node は unschedulable だが、既存の Pod は実行を続ける
C. Node は maintenance mode であり、新しい Pod は schedule されない
D. Node は resource shortage state であり、新しい Pod はできれば schedule されない

<details>
<summary>回答を表示</summary>

**回答: A. Node が unreachable であり、toleration を持たない Pod は削除される**

**解説:**
Kubernetes における Node taint `node.kubernetes.io/unreachable:NoExecute` は、その Node が unreachable であり、この taint に対する toleration を持たない Pod が Node から削除（evict）されることを意味します。この taint は node controller によって自動的に追加され、Node の status が `Ready` から `Unknown` に変わったときに適用されます。

**Node Unreachable State:**
Node が unreachable になる一般的な原因:
1. Network connectivity の問題
2. kubelet process の crash
3. Node system failure
4. Node power issues

**Taint Components:**
1. **Key**: `node.kubernetes.io/unreachable`
2. **Value**: 通常は空文字列ですが、値を持つ場合があります。
3. **Effect**: `NoExecute` - toleration を持たない Pod は Node から削除されます。

**NoExecute Effect:**
`NoExecute` effect は次の動作を引き起こします:
1. taint を持つ Node には新しい Pod は schedule されません。
2. すでにその Node 上で実行中の Pod のうち、その taint に対する toleration を持たないものは削除されます。

**System Taints:**
Kubernetes は Node status に基づいて次の system taints を自動的に追加します:
1. **node.kubernetes.io/not-ready:NoExecute**: Node is not ready
2. **node.kubernetes.io/unreachable:NoExecute**: Node is unreachable
3. **node.kubernetes.io/memory-pressure:NoSchedule**: Node has memory pressure
4. **node.kubernetes.io/disk-pressure:NoSchedule**: Node has disk pressure
5. **node.kubernetes.io/pid-pressure:NoSchedule**: Node has PID pressure
6. **node.kubernetes.io/network-unavailable:NoSchedule**: Node's network is unavailable
7. **node.kubernetes.io/unschedulable:NoSchedule**: Node is marked as unschedulable

**Default Tolerations:**
Kubernetes はすべての Pod に次の default toleration を自動的に追加します:
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

これらの default toleration により、Node が not ready または unreachable になった場合でも、Pod は 5 分間（300 秒）その Node 上に残ることができ、一時的な network issue による不要な Pod rescheduling を防ぎます。

**Custom Tolerations:**
critical workload では、より長い toleration time を設定できます:
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

**Node Controller Settings:**
node controller は、次の settings を通じて Node status change と taint application behavior を制御します:
1. **--node-monitor-period**: Node status を check する period（default: 5 seconds）
2. **--node-monitor-grace-period**: Node を `Unknown` として mark する前の wait time（default: 40 seconds）
3. **--pod-eviction-timeout**: `Unknown` または `NotReady` Node から Pod を削除する前の wait time（default: 5 minutes）

**Checking Node Status and Taints:**
```bash
# Check node status
kubectl get nodes

# Check node details
kubectl describe node <node-name>

# Check node taints
kubectl get node <node-name> -o jsonpath='{.spec.taints}'
```

**Checking Pod Tolerations:**
```bash
# Check pod tolerations
kubectl get pod <pod-name> -o jsonpath='{.spec.tolerations}'
```

**Handling Taints in Custom Scheduler:**
Custom Scheduler を実装する際は、Node taints と Pod tolerations を考慮する必要があります。

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

**Issues with Other Options:**
- B. Node は unschedulable だが、既存の Pod は実行を続ける: これは `NoSchedule` effect の動作です。`NoExecute` effect は toleration を持たない既存の Pod も削除します。
- C. Node は maintenance mode であり、新しい Pod は schedule されない: これは通常、`node.kubernetes.io/unschedulable:NoSchedule` taint の動作です。
- D. Node は resource shortage state であり、新しい Pod はできれば schedule されない: これは `PreferNoSchedule` effect の動作であり、resource shortage は通常 `node.kubernetes.io/memory-pressure` または `node.kubernetes.io/disk-pressure` taint によって示されます。
</details>
