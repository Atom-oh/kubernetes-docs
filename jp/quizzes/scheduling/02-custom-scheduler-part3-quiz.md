# Custom Scheduler クイズ (Part 3)

このクイズでは、Kubernetes における Custom Scheduler の実装と使用に関する高度な理解を確認します。

## クイズ問題

### 1. Kubernetes で複数の scheduler を同時に実行する際に発生しうる問題ではないものは、次のうちどれですか？

A. リソース競合
B. スケジューリング判断の競合
C. ネットワーク帯域幅の増加
D. Leader election の競合

<details>
<summary>答えを表示</summary>

**答え: C. ネットワーク帯域幅の増加**

**解説:**
「ネットワーク帯域幅の増加」は、Kubernetes で複数の scheduler を同時に実行する際に発生しうる問題ではありません。scheduler は API server と通信しますが、ネットワーク帯域幅の使用量は通常ごくわずかであり、懸念事項にはなりません。

**複数の scheduler を実行する際に実際に発生しうる問題:**

1. **リソース競合**:
   - 複数の scheduler が同じ node pool に Pod をスケジュールしようとすると、リソース競合が発生する可能性があります。
   - 各 scheduler は他の scheduler の判断を認識せずに独立して動作するため、node リソースを過剰に割り当てるリスクがあります。
   - 例: 2 つの scheduler が同時に同じ node に Pod をスケジュールし、node の容量を超える可能性があります。

2. **スケジューリング判断の競合**:
   - 複数の scheduler が同じ Pod をスケジュールしようとすると、競合が発生する可能性があります。
   - これは、Pod が `schedulerName` を明示的に指定していない場合や、複数の scheduler が同じ名前を使用している場合に発生することがあります。
   - 例: 2 つの scheduler が同じ Pod を異なる node に bind しようとすると、競合状態が発生します。

3. **Leader election の競合**:
   - 同じ名前の scheduler instance が leader election を有効にして複数実行されている場合、leader election メカニズムで競合が発生する可能性があります。
   - 例: 同じ名前の複数の scheduler instance がリーダーシップを競い合うと、不安定なリーダーシップ遷移が発生する可能性があります。

**複数の scheduler を実行する際のベストプラクティス:**

1. **責任範囲の明確な分離**:
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

2. **一意の scheduler 名を使用する**:
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

3. **node label と taint を使用して node pool を分離する**:
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

4. **resource quota を設定する**:
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

**複数の scheduler の監視:**
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

**他の選択肢の解説:**
- A. リソース競合: 複数の scheduler が同じ node pool に Pod をスケジュールする際に発生しうる実際の問題です。
- B. スケジューリング判断の競合: 複数の scheduler が同じ Pod をスケジュールしようとする際に発生しうる実際の問題です。
- D. Leader election の競合: 同じ名前の複数の scheduler instance がリーダーシップを競い合う際に発生しうる実際の問題です。
</details>

### 2. Kubernetes scheduler における "Permit" extension point の役割は何ですか？

A. Pod を node に bind する
B. Pod のスケジューリングを許可、拒否、または遅延する
C. Pod を実行できない node を除外する
D. node に score を割り当てる

<details>
<summary>答えを表示</summary>

**答え: B. Pod のスケジューリングを許可、拒否、または遅延する**

**解説:**
Kubernetes scheduling framework における "Permit" extension point の役割は、Pod のスケジューリングを許可、拒否、または遅延することです。Permit plugin は node が選択された後、binding phase の前に実行され、Pod のスケジューリング判断に対する最終的な承認または拒否を提供します。

**Permit extension point の主な機能:**
1. **Allow**: Pod のスケジューリングが binding phase に進むことを許可します。
2. **Deny**: Pod のスケジューリングを拒否し、別の node を選択できるようにします。
3. **Wait**: Pod のスケジューリングを一時的に遅延し、特定の条件が満たされるまで待機します。

**Permit plugin interface:**
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

**Permit の結果タイプ:**
1. **Success**: Pod のスケジューリングを許可します。
2. **Deny**: Pod のスケジューリングを拒否します。
3. **Wait**: Pod のスケジューリングを遅延し、指定された時間だけ待機します。

**デフォルトの Permit plugin:**
Kubernetes は次のデフォルト Permit plugin を提供します。

1. **TaintToleration**: node taint と Pod toleration を確認します。
2. **PodTopologySpread**: Pod topology spread constraint を確認します。

**Custom Permit plugin の例:**
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

**scheduler configuration で Permit plugin を有効化する:**
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

**Permit のユースケース:**
1. **Gang scheduling**: 関連するすべての Pod をスケジュールできる準備が整うまで、Pod group のスケジューリングを遅延します。
2. **リソース予約**: Pod がスケジュールされる前に外部リソースを予約します。
3. **ポリシー検証**: Pod のスケジューリングが組織のポリシーに準拠していることを確認します。
4. **承認ワークフロー**: Pod のスケジューリングに対して外部承認を要求します。

**Gang scheduling の例:**
Gang scheduling は、関連するすべての Pod が一緒にスケジュールされることを保証する手法です。これは、すべてのコンポーネントが同時に実行される必要がある分散トレーニングジョブのような workload に役立ちます。

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

**他の選択肢の問題点:**
- A. Pod を node に bind する: これは "Bind" extension point の役割です。
- C. Pod を実行できない node を除外する: これは "Filter" extension point の役割です。
- D. node に score を割り当てる: これは "Score" extension point の役割です。
</details>
### 3. Kubernetes における Gang Scheduling の主な目的は何ですか？

A. Pod を特定の node のみに配置する
B. 関連するすべての Pod が一緒にスケジュールされるようにする
C. Pod をさまざまな node に均等に分散する
D. 優先度に基づいて Pod をスケジュールする

<details>
<summary>答えを表示</summary>

**答え: B. 関連するすべての Pod が一緒にスケジュールされるようにする**

**解説:**
Kubernetes における Gang Scheduling の主な目的は、関連するすべての Pod が一緒にスケジュールされるようにすることです。これは、分散トレーニングジョブや分散データ処理ジョブのように、すべてのコンポーネントが同時に実行される必要がある workload で重要です。

**Gang scheduling が必要な理由:**
1. **All-or-Nothing 要件**: 一部の workload はすべてのコンポーネントが同時に実行される必要があり、一部だけが実行されてもジョブは進行しません。
2. **リソース浪費の防止**: 一部の Pod だけがスケジュールされ、他の Pod が待機している場合、すでにスケジュールされた Pod が使用するリソースが無駄になる可能性があります。
3. **デッドロックの防止**: 相互依存する Pod が異なるタイミングでスケジュールされると、デッドロックが発生する可能性があります。

**Gang scheduling の実装方法:**
Kubernetes は Gang scheduling をネイティブにはサポートしていませんが、次の方法で実装できます。

1. **Custom scheduler**: Permit extension point を使用して Gang scheduling を実装します。
2. **External controller**: Kubernetes の外部で Gang scheduling を管理する controller を実装します。
3. **オープンソースソリューション**: Volcano や Kube-batch のようなオープンソース scheduler を使用します。

**Gang scheduling の例 (Volcano):**
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

**custom Permit plugin を使用した Gang scheduling の実装:**
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

**Gang scheduling の長所と短所:**
長所:
- 関連するすべての Pod が一緒にスケジュールされることを保証します
- リソースの浪費を防ぎます
- デッドロックと starvation を防ぎます

短所:
- 実装の複雑さが増します
- スケジューリング遅延が発生する可能性があります
- cluster リソース使用率が低下する可能性があります

**Gang scheduling を必要とする workload:**
1. **分散トレーニングジョブ**: TensorFlow、PyTorch のような分散トレーニング framework
2. **分散データ処理**: Spark、Flink のような分散データ処理 framework
3. **MPI ジョブ**: High-performance computing (HPC) workload
4. **Service mesh**: 複数のコンポーネントが連携して動作する必要がある Service mesh

**他の選択肢の問題点:**
- A. Pod を特定の node のみに配置する: これは node selector または node affinity の役割です。
- C. Pod をさまざまな node に均等に分散する: これは Pod topology spread constraint の役割です。
- D. 優先度に基づいて Pod をスケジュールする: これは Pod priority と preemption の役割です。
</details>

### 4. Kubernetes で Scheduler Extender を実装する際に必須の API endpoint ではないものは、次のうちどれですか？

A. /filter
B. /prioritize
C. /bind
D. /validate

<details>
<summary>答えを表示</summary>

**答え: D. /validate**

**解説:**
"/validate" は、Kubernetes で Scheduler Extender を実装する際に必須の API endpoint ではありません。Scheduler extender は通常、"/filter"、"/prioritize"、"/bind"、"/preempt" などの endpoint を実装しますが、"/validate" は scheduler extender の標準 API ではありません。

**Scheduler Extender API endpoint:**
1. **filter**: node のリストを受け取り、フィルタリング済みの node リストを返します。
2. **prioritize**: node のリストを受け取り、各 node に score を割り当てます。
3. **bind**: Pod を node に bind します。
4. **preempt**: preemption のための node と Pod を返します。

**Scheduler Extender configuration の例:**
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

**Scheduler Extender API の request と response の形式:**

1. **filter API**:
   - Request:
     ```json
     {
       "pod": <pod>,
       "nodes": <nodes>,
       "nodenames": <node-names>
     }
     ```
   - Response:
     ```json
     {
       "nodes": <filtered-nodes>,
       "nodenames": <filtered-node-names>,
       "failedNodes": <failed-nodes>,
       "error": <error-message>
     }
     ```

2. **prioritize API**:
   - Request:
     ```json
     {
       "pod": <pod>,
       "nodes": <nodes>,
       "nodenames": <node-names>
     }
     ```
   - Response:
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

3. **bind API**:
   - Request:
     ```json
     {
       "pod": <pod>,
       "node": <node-name>
     }
     ```
   - Response:
     ```json
     {
       "error": <error-message>
     }
     ```

4. **preempt API**:
   - Request:
     ```json
     {
       "pod": <pod>,
       "nodenames": <node-names>,
       "nodes": <nodes>
     }
     ```
   - Response:
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

**Scheduler Extender implementation example (Go):**
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

**Scheduler Extender の長所と短所:**
長所:
- scheduler codebase から独立して開発できます
- さまざまなプログラミング言語で実装できます
- scheduler のアップグレードの影響を受けにくいです

短所:
- HTTP 通信オーバーヘッドによる performance 低下
- scheduling cycle の一部の stage しか拡張できません
- scheduler と extender 間の通信障害の可能性

**Scheduler Extender と Scheduling Framework plugin の比較:**
- **Scheduler Extender**: HTTP webhook 経由で外部プロセスとして実行されます。
- **Scheduling Framework plugins**: scheduler codebase に直接統合されて実行されます。

**他の選択肢の解説:**
- A. /filter: node リストをフィルタリングする有効な scheduler extender API endpoint です。
- B. /prioritize: node に score を割り当てる有効な scheduler extender API endpoint です。
- C. /bind: Pod を node に bind する有効な scheduler extender API endpoint です。
</details>
### 5. Kubernetes scheduler framework における "PostFilter" extension point の役割は何ですか？

A. filtering 後に node に score を割り当てる
B. filtering 後に Pod を node に bind する
C. filtering が失敗したときに preemption logic を実行する
D. filtering 後に Pod status を更新する

<details>
<summary>答えを表示</summary>

**答え: C. filtering が失敗したときに preemption logic を実行する**

**解説:**
Kubernetes scheduling framework における "PostFilter" extension point の役割は、filtering が失敗したときに preemption logic を実行することです。filtering phase ですべての node が除外され、Pod をスケジュールできない場合、PostFilter plugin は preemption を通じて Pod をスケジュールする方法を見つけます。

**PostFilter extension point の主な機能:**
1. **preemption 候補の特定**: preempt 可能な Pod と node を特定します。
2. **preemption simulation**: preemption 後に Pod をスケジュールできるかどうかをシミュレートします。
3. **preemption 判断**: 最適な preemption 戦略を決定します。

**PostFilter plugin interface:**
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

**デフォルトの PostFilter plugin:**
Kubernetes は次のデフォルト PostFilter plugin を提供します。

1. **DefaultPreemption**: デフォルトの preemption logic を実装します。

**DefaultPreemption plugin の動作:**
1. 優先度の低い Pod を preempt することで空きを作れる node を特定します。
2. 各 node で preempt する Pod を決定します。
3. preemption 後に Pod をスケジュールできることを検証します。
4. 最適な preemption 戦略を選択します。
5. 選択した node を Pod の nominatedNodeName として設定します。

**Custom PostFilter plugin の例:**
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

**scheduler configuration で PostFilter plugin を有効化する:**
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

**preemption 関連の設定:**
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

**preemption プロセス:**
1. Pod がすべての node で filtering phase に失敗したとき、PostFilter phase が呼び出されます。
2. PostFilter plugin が preemption candidate node を特定します。
3. 各 node でどの Pod を preempt するかを決定します。
4. preemption 後に Pod をスケジュールできることを検証します。
5. 最適な preemption 戦略を選択します。
6. 選択した node を Pod の nominatedNodeName として設定します。
7. preempt された Pod は graceful termination を行います。
8. preempt された Pod が終了すると、より優先度の高い Pod がスケジュールされます。

**preemption 関連 metrics の監視:**
```bash
# Check preemption-related metrics from scheduler metrics
kubectl get --raw /metrics | grep scheduler_preemption
```

**preemption event の確認:**
```bash
# Check preemption events
kubectl get events | grep -i preempt
```

**他の選択肢の問題点:**
- A. filtering 後に node に score を割り当てる: これは "Score" extension point の役割です。
- B. filtering 後に Pod を node に bind する: これは "Bind" extension point の役割です。
- D. filtering 後に Pod status を更新する: これは scheduler framework の extension point ではありません。
</details>

### 6. Kubernetes scheduler における "NodeResourcesBalancedAllocation" plugin の主な目的は何ですか？

A. CPU と memory の使用率がバランスしている node に高い score を付ける
B. リソース使用率が低い node に高い score を付ける
C. リソース使用率が高い node に高い score を付ける
D. node にリソース制限を設定する

<details>
<summary>答えを表示</summary>

**答え: A. CPU と memory の使用率がバランスしている node に高い score を付ける**

**解説:**
Kubernetes scheduler における "NodeResourcesBalancedAllocation" plugin の主な目的は、CPU と memory の使用率がバランスしている node に高い score を付けることです。この plugin は、CPU と memory の利用率の差が小さい node を優先し、cluster 全体のリソース使用バランスを改善します。

**NodeResourcesBalancedAllocation plugin の動作:**
1. 各 node の CPU utilization と memory utilization を計算します。
2. CPU utilization と memory utilization の差を計算します。
3. 差が小さい node に高い score を付けます。

**score 計算方法:**
```
score = 10 - variance(cpuFraction, memoryFraction) * 10
```
Where:
- cpuFraction = (requested CPU + pod's CPU request) / allocatable CPU
- memoryFraction = (requested memory + pod's memory request) / allocatable memory
- variance(a, b) = |a - b|

**例:**
- Node A: CPU utilization 80%、memory utilization 80% -> 差: 0% -> score: 10
- Node B: CPU utilization 90%、memory utilization 50% -> 差: 40% -> score: 6
- Node C: CPU utilization 30%、memory utilization 90% -> 差: 60% -> score: 4

この場合、Node A が最も高い score を受け取り、選択される可能性が最も高くなります。

**scheduler configuration で NodeResourcesBalancedAllocation plugin を有効化する:**
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

**Plugin configuration:**
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

**NodeResourcesBalancedAllocation と他の scoring plugin の比較:**
1. **NodeResourcesBalancedAllocation**: CPU と memory の使用率がバランスしている node を優先します。
2. **NodeResourcesFit**: 要求リソースと比較して、より多くの利用可能リソースを持つ node を優先します。
3. **NodeResourcesLeastAllocated**: リソース使用率が低い node を優先します。
4. **NodeResourcesMostAllocated**: リソース使用率が高い node を優先します。

**ユースケース:**
1. **リソースバランス**: cluster 全体の CPU と memory の使用バランスを改善します。
2. **ボトルネック防止**: あるリソースタイプ（CPU または memory）が他方より先に枯渇することを防ぎます。
3. **スケーラビリティ向上**: リソース使用率がバランスした cluster は、より効率的にスケールできます。

**Custom balanced allocation plugin の例:**
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

**他の選択肢の問題点:**
- B. リソース使用率が低い node に高い score を付ける: これは "NodeResourcesLeastAllocated" plugin の役割です。
- C. リソース使用率が高い node に高い score を付ける: これは "NodeResourcesMostAllocated" plugin の役割です。
- D. node にリソース制限を設定する: これは scheduler plugin の役割ではありません。node リソース制限は node 自体のプロパティです。
</details>
### 7. Kubernetes scheduler における "PreBind" extension point の役割は何ですか？

A. Pod を node に bind する
B. binding 前に必要な操作を実行する
C. binding 後に cleanup を実行する
D. binding が失敗したときに recovery 操作を実行する

<details>
<summary>答えを表示</summary>

**答え: B. binding 前に必要な操作を実行する**

**解説:**
Kubernetes scheduling framework における "PreBind" extension point の役割は、Pod を node に bind する前に必要な操作を実行することです。たとえば、volume provisioning、network setup、resource reservation のような操作を実行できます。

**PreBind extension point の主な機能:**
1. **Volume provisioning**: 必要な volume を作成し、準備します。
2. **Network setup**: 必要な network resource を設定します。
3. **Resource reservation**: 必要なリソースを予約します。
4. **Pre-validation**: binding が可能であることを最終確認します。

**PreBind plugin interface:**
```go
type PreBindPlugin interface {
    Plugin
    // PreBind is called before binding a pod to a node.
    PreBind(ctx context.Context, state *CycleState, pod *v1.Pod, nodeName string) *Status
}
```

**デフォルトの PreBind plugin:**
Kubernetes は次のデフォルト PreBind plugin を提供します。

1. **VolumeBinding**: volume binding 操作を実行します。
2. **DefaultPreBind**: 基本的な pre-binding 操作を実行します。

**Custom PreBind plugin の例:**
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

**scheduler configuration で PreBind plugin を有効化する:**
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

**PreBind のユースケース:**
1. **Volume provisioning**:
   - PersistentVolume の作成と binding
   - Ephemeral volume の準備
   - Storage class parameter の検証

2. **Network setup**:
   - Network policy の適用
   - Service endpoint の設定
   - Load balancer configuration

3. **Resource reservation**:
   - GPU resource reservation
   - FPGA resource reservation
   - Special hardware resource reservation

4. **Security setup**:
   - Security policy の適用
   - Certificate provisioning
   - Secret mount の準備

**PreBind failure handling:**
PreBind plugin が failure を返した場合:
1. scheduling cycle が中止されます。
2. Pod は scheduling queue に戻ります。
3. 予約されたリソースが解放されます。
4. failure event がログに記録されます。

**PreBind log と event の監視:**
```bash
# Check PreBind-related messages in scheduler logs
kubectl logs -n kube-system <scheduler-pod> | grep -i prebind

# Check pod events
kubectl describe pod <pod-name> | grep -i prebind
```

**他の選択肢の問題点:**
- A. Pod を node に bind する: これは "Bind" extension point の役割です。
- C. binding 後に cleanup を実行する: これは "PostBind" extension point の役割です。
- D. binding が失敗したときに recovery 操作を実行する: これは scheduler framework の extension point ではありません。
</details>

### 8. Kubernetes scheduler における "NodeResourcesFit" plugin の主な目的は何ですか？

A. node のリソース使用率を監視する
B. node のリソース制限を設定する
C. node のリソース容量と Pod のリソース要求を比較する
D. node のリソース使用バランスを維持する

<details>
<summary>答えを表示</summary>

**答え: C. node のリソース容量と Pod のリソース要求を比較する**

**解説:**
Kubernetes scheduler における "NodeResourcesFit" plugin の主な目的は、node のリソース容量と Pod のリソース要求を比較し、Pod が node 上で実行できるかどうかを検証することです。この plugin は CPU、memory、ephemeral storage、extended resource（GPU など）を含むさまざまなリソースタイプを考慮します。

**NodeResourcesFit plugin の主な機能:**
1. **Resource request validation**: Pod の resource request が node の allocatable resource を超えていないことを検証します。
2. **Resource limit validation**: Pod の resource limit が node capacity を超えていないことを検証します。
3. **Extended resource validation**: GPU や FPGA のような extended resource request が node 上で利用可能であることを検証します。

**NodeResourcesFit plugin configuration:**
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

**Scoring strategy:**
NodeResourcesFit plugin は次の scoring strategy をサポートします。

1. **LeastAllocated**: 使用中のリソースが少ない node に高い score を付けます。
   ```
   score = (capacity - requested) / capacity
   ```

2. **MostAllocated**: 使用中のリソースが多い node に高い score を付けます。
   ```
   score = requested / capacity
   ```

3. **RequestedToCapacityRatio**: 要求リソースと容量の比率に基づき、custom function を使用して score を割り当てます。

**Custom NodeResourcesFit plugin の例:**
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

**Resource request と limit の例:**
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

**他の選択肢の問題点:**
- A. node のリソース使用率を監視する: これは metrics server または monitoring system の役割です。
- B. node のリソース制限を設定する: これは node configuration または kubelet の役割です。
- D. node のリソース使用バランスを維持する: これは "NodeResourcesBalancedAllocation" plugin の役割です。
</details>
### 9. Kubernetes scheduler における "InterPodAffinity" plugin の主な目的は何ですか？

A. Pod と node 間の affinity rule を処理する
B. Pod 間の affinity rule と anti-affinity rule を処理する
C. Pod と volume 間の affinity rule を処理する
D. Pod と service 間の affinity rule を処理する

<details>
<summary>答えを表示</summary>

**答え: B. Pod 間の affinity rule と anti-affinity rule を処理する**

**解説:**
Kubernetes scheduler における "InterPodAffinity" plugin の主な目的は、Pod 間の affinity rule と anti-affinity rule を処理することです。この plugin は、Pod が他の Pod と同じ topology domain（node、zone、region など）に配置されるか（affinity）、または異なる domain に配置されるか（anti-affinity）を制御します。

**InterPodAffinity plugin の主な機能:**
1. **Pod affinity rule processing**: 特定の label を持つ他の Pod と同じ topology domain に Pod が配置されることを保証します。
2. **Pod anti-affinity rule processing**: 特定の label を持つ他の Pod とは異なる topology domain に Pod が配置されることを保証します。
3. **Topology domain consideration**: node、zone、region を含むさまざまなレベルの topology domain を考慮します。

**Pod affinity と anti-affinity のタイプ:**
1. **requiredDuringSchedulingIgnoredDuringExecution**: Pod をスケジュールするために満たす必要がある rule（hard requirement）。
2. **preferredDuringSchedulingIgnoredDuringExecution**: 必須ではないが優先される rule（soft requirement）。

**Pod affinity と anti-affinity の例:**
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

**InterPodAffinity plugin configuration:**
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

**Custom InterPodAffinity plugin の例:**
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

**Pod affinity と anti-affinity のユースケース:**
1. **High availability**: 同じ application の instance を異なる node、zone、または region に分散します
2. **Performance optimization**: 互いに通信する Pod を同じ node に配置して latency を最小化します
3. **Resource isolation**: resource-intensive な Pod を異なる node に分散します
4. **License restrictions**: license restriction がある application を特定の node に集約します

**Pod affinity と anti-affinity の performance impact:**
Pod affinity と anti-affinity は、すべての node と Pod を考慮する必要があるため、計算コストが高くなる場合があります。大規模 cluster では scheduling performance に影響する可能性があるため、注意して使用してください。

**他の選択肢の問題点:**
- A. Pod と node 間の affinity rule を処理する: これは "NodeAffinity" plugin の役割です。
- C. Pod と volume 間の affinity rule を処理する: これは "VolumeBinding" plugin の役割です。
- D. Pod と service 間の affinity rule を処理する: これは Kubernetes scheduler plugin ではありません。
</details>

### 10. Kubernetes scheduler における "NodeName" plugin の主な目的は何ですか？

A. Pod の spec.nodeName field が node 名と一致することを検証する
B. node に名前を割り当てる
C. Pod に node 名を割り当てる
D. node 名の形式を検証する

<details>
<summary>答えを表示</summary>

**答え: A. Pod の spec.nodeName field が node 名と一致することを検証する**

**解説:**
Kubernetes scheduler における "NodeName" plugin の主な目的は、Pod の `spec.nodeName` field が node 名と一致することを検証することです。この plugin は、Pod が特定の node に直接割り当てられているかどうかを確認し、filtering phase で名前が一致する node のみを通過させます。

**NodeName plugin の主な機能:**
1. **Node name verification**: Pod の `spec.nodeName` field が設定されている場合、一致する名前の node のみが選択されます。
2. **Direct scheduling support**: ユーザーが Pod を特定の node に直接割り当てることを可能にします。
3. **Scheduler bypass**: `spec.nodeName` が設定された Pod は通常の scheduling logic を bypass し、指定された node に直接割り当てられます。

**NodeName plugin implementation:**
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

**nodeName 指定を持つ Pod の例:**
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

**nodeName を使用する際の考慮事項:**
1. **Scheduler bypass**: `nodeName` を使用すると、scheduler の filtering、scoring、およびその他の logic を bypass します。
2. **Node existence check**: 指定された node が存在しない場合、Pod は `Pending` 状態のままになります。
3. **No resource check**: node の resource availability は確認されないため、resource shortage による failure につながる可能性があります。
4. **Ignoring constraints**: taint、affinity、およびその他の constraint は無視されます。

**nodeName と nodeSelector と nodeAffinity の比較:**
1. **nodeName**: 特定の node に直接割り当てます。最も制約が強く、最も柔軟性が低いです。
2. **nodeSelector**: label に基づいて node を選択します。単純ですが表現力は限定的です。
3. **nodeAffinity**: 複雑な node selection rule をサポートします。最も柔軟で表現力があります。

**nodeName のユースケース:**
1. **Debugging**: 問題をデバッグするために特定の node で Pod を実行します。
2. **Testing**: 特定の node でテストを実行します。
3. **Special hardware**: 特定の hardware を持つ node に Pod を割り当てます。
4. **Static pods**: kubelet によって直接管理される static Pod に使用されます。

**nodeName 使用時の注意点:**
1. **No automatic recovery**: node が failure しても、Pod は自動的に他の node に移動しません。
2. **Limited scalability**: node 名が hardcoded されるため、scalability が制限されます。
3. **Maintenance difficulty**: node 名が変更された場合、Pod 定義を更新する必要があります。
4. **No load balancing**: scheduler の load balancing 機能を活用できません。

**代替手段と推奨事項:**
1. **nodeSelector の使用**:
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

2. **nodeAffinity の使用**:
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

**他の選択肢の問題点:**
- B. node に名前を割り当てる: node 名は node 作成時に割り当てられるものであり、scheduler plugin の役割ではありません。
- C. Pod に node 名を割り当てる: これは scheduler の binding phase で実行されるものであり、NodeName plugin によるものではありません。
- D. node 名の形式を検証する: これは API server validation logic によって実行されるものであり、scheduler plugin によるものではありません。
</details>
