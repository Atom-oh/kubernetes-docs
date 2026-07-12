# Custom Scheduler Quiz (Part 1)

このクイズでは、Kubernetes における Custom Scheduler の実装と使用に関する理解を確認します。

## Quiz Questions

### 1. What is the main role of a scheduler in Kubernetes?

A. Pod の作成と削除
B. Pod を適切な node に割り当てる
C. Node リソースの監視
D. Container image のダウンロード

<details>
<summary>答えを表示</summary>

**回答: B. Pod を適切な node に割り当てる**

**解説:**
Kubernetes における scheduler の主な役割は、Pod を適切な node に割り当てることです。scheduler は新しく作成された Pod を監視し、まだ node に割り当てられていない Pod を実行するための最適な node を見つけます。

**Scheduler の主な機能:**
1. **Pod-Node 割り当て**: Pod の要件と node の利用可能なリソースを考慮して、最適な node を選択します。
2. **Filtering**: Pod を実行できない node（例: リソース不足、taints など）を除外します。
3. **Scoring**: 適切な node にスコアを付け、最適な node を選択します。
4. **Binding**: Pod を選択された node にバインドし、スケジューリングの決定を確定します。

**Scheduling プロセス:**
1. **Filtering Stage (Predicates)**: Pod を実行できない node を除外します。
   - PodFitsResources: node が Pod のリソース要求を満たす十分なリソースを持っているか確認します
   - PodFitsHostPorts: 要求された host port が利用可能か確認します
   - PodMatchNodeSelector: Pod の node selector が node labels と一致するか確認します
   - NoVolumeZoneConflict: volume zone の制約を確認します
   - CheckNodeMemoryPressure: node の memory pressure 状態を確認します
   - CheckNodeDiskPressure: node の disk pressure 状態を確認します

2. **Scoring Stage (Priorities)**: 適切な node にスコアを付けます。
   - LeastRequestedPriority: 要求済みリソースが少ない node に高いスコアを与えます
   - BalancedResourceAllocation: リソース使用のバランスがよい node に高いスコアを与えます
   - NodeAffinityPriority: node affinity ルールに基づいてスコアを付けます
   - TaintTolerationPriority: taint toleration に基づいてスコアを付けます
   - InterPodAffinityPriority: inter-pod affinity/anti-affinity に基づいてスコアを付けます

3. **Binding**: 最も高いスコアを持つ node に Pod をバインドします。

**Default Scheduler Configuration Example:**
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

**他の選択肢の問題点:**
- A. Pod の作成と削除: これは主に controller manager と API server の役割です。
- C. Node リソースの監視: これは主に kubelet と metrics server の役割です。
- D. Container image のダウンロード: これは kubelet と container runtime の役割です。
</details>

### 2. Which of the following is NOT a method for implementing a Custom Scheduler?

A. 既存の kube-scheduler を拡張する
B. 完全に新しい scheduler を実装する
C. scheduling framework plugin を開発する
D. kubelet を変更する

<details>
<summary>答えを表示</summary>

**回答: D. kubelet を変更する**

**解説:**
kubelet を変更することは、Custom Scheduler を実装する方法ではありません。kubelet は各 node で実行され、Pod の実行を管理する agent ですが、スケジューリングの決定は行いません。スケジューリングは kube-scheduler または custom scheduler によって実行されます。

**Custom Scheduler を実装する方法:**

1. **既存の kube-scheduler を拡張する**:
   - KubeSchedulerConfiguration を使用して default scheduler の動作をカスタマイズします。
   - plugin の weight、enable/disable などを調整します。

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

2. **完全に新しい scheduler を実装する**:
   - Kubernetes API と通信する独立した scheduler を開発します。
   - Pod の監視、node 選択、binding ロジックを直接実装します。

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

3. **scheduling framework plugin を開発する**:
   - Kubernetes scheduling framework を使用して、特定の scheduling stage 用の plugin を開発します。
   - filter、score、bind などの extension point を実装します。

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

**kubelet の役割:**
kubelet は各 node で実行され、次の役割を担う agent です。
- Pod spec に従って container を実行および管理する
- Node の状態を監視し報告する
- Container の health check を実行する
- volume mount を管理する

kubelet は scheduler が行った決定（どの Pod をどの node で実行するか）を実行するものであり、自身でスケジューリングの決定は行いません。

**他の選択肢の解説:**
- A. 既存の kube-scheduler を拡張する: 有効な Custom Scheduler 実装方法です。
- B. 完全に新しい scheduler を実装する: 有効な Custom Scheduler 実装方法です。
- C. scheduling framework plugin を開発する: 有効な Custom Scheduler 実装方法です。
</details>

### 3. What field is used in a pod to specify a specific scheduler?

A. spec.scheduler
B. spec.schedulerName
C. metadata.scheduler
D. spec.nodeName

<details>
<summary>答えを表示</summary>

**回答: B. spec.schedulerName**

**解説:**
Pod で特定の scheduler を指定するために使用される field は `spec.schedulerName` です。この field が設定されると、Pod は指定された名前の scheduler によってのみスケジューリングされます。default value は "default-scheduler" です。

**Pod Spec Example:**
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

この Pod は "my-custom-scheduler" という名前の scheduler によってのみスケジューリングされます。その名前の scheduler が cluster 内に存在しない場合、Pod は `Pending` 状態のままになります。

**複数の Scheduler をデプロイする例:**
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

**Scheduler を選択する際の考慮事項:**
1. **Availability**: 指定した scheduler が実行されていない場合、Pod はスケジューリングされません。
2. **Functionality**: 各 scheduler は異なる scheduling algorithm や policy を持つことができます。
3. **Resource isolation**: 異なる scheduler を使用して workload を分離できます。
4. **Special hardware**: GPU や FPGA などの特殊 hardware 用に専用 scheduler を使用できます。

**Scheduler Status の確認:**
```bash
# Check pod status
kubectl get pod custom-scheduled-pod

# Check scheduling events
kubectl describe pod custom-scheduled-pod | grep -A 5 Events

# Check scheduler logs
kubectl logs -n kube-system -l component=my-custom-scheduler
```

**他の選択肢の問題点:**
- A. spec.scheduler: Kubernetes API に存在しない field です。
- C. metadata.scheduler: Kubernetes API に存在しない field です。
- D. spec.nodeName: この field は scheduler をバイパスし、Pod を特定の node に直接割り当てるために使用されます。scheduler を指定するための field ではありません。
</details>
### 4. What is the role of the "Filter" extension point in the Kubernetes scheduling framework?

A. node にスコアを付ける
B. Pod を node にバインドする
C. Pod を実行できない node を除外する
D. scheduling queue 内の Pod を並べ替える

<details>
<summary>答えを表示</summary>

**回答: C. Pod を実行できない node を除外する**

**解説:**
Kubernetes scheduling framework における "Filter" extension point（以前は "Predicate" と呼ばれていました）の役割は、Pod を実行できない node を除外することです。Filter plugin は各 node が Pod の要件を満たすかどうかを確認し、要件を満たさない node を候補リストから除外します。

**Scheduling Framework Extension Points:**
Scheduling framework は、scheduling cycle のさまざまな stage で plugin を統合できる各種 extension point を提供します。

1. **Queue Sort**: scheduling queue 内の Pod の順序を決定します。
2. **PreFilter**: filtering の前に Pod と cluster state の前処理を実行します。
3. **Filter**: Pod を実行できない node を除外します。
4. **PreScore**: scoring の前に必要な計算を実行します。
5. **Score**: filtering を通過した node にスコアを割り当てます。
6. **NormalizeScore**: 各 scoring plugin のスコアを正規化します。
7. **Reserve**: 選択された node 上に Pod のリソースを予約します。
8. **Permit**: Pod のスケジューリングを許可、拒否、または遅延します。
9. **PreBind**: binding の前に必要な処理を実行します。
10. **Bind**: Pod を node にバインドします。
11. **PostBind**: binding 後の cleanup 処理を実行します。

**Default Filter Plugins:**
Kubernetes は次の default filter plugin を提供しています。

1. **NodeResourcesFit**: node が Pod のリソース要求を満たす十分なリソースを持っているか確認します。
2. **NodeName**: Pod の spec.nodeName field が node name と一致するか確認します。
3. **NodeUnschedulable**: node が unschedulable としてマークされているか確認します。
4. **TaintToleration**: Pod が node の taints を tolerates しているか確認します。
5. **NodeAffinity**: Pod の node affinity 要件が満たされているか確認します。
6. **PodAffinity**: Pod の pod affinity 要件が満たされているか確認します。
7. **VolumeRestrictions**: volume constraints を確認します。
8. **EBSLimits**: Amazon EBS volume limits を確認します。
9. **NoVolumeZoneConflict**: volume zone constraints を確認します。
10. **CheckNodeMemoryPressure**: node の memory pressure 状態を確認します。
11. **CheckNodeDiskPressure**: node の disk pressure 状態を確認します。

**Custom Filter Plugin Example:**
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

**Scheduler Configuration で Filter Plugin を有効化する:**
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

**他の選択肢の問題点:**
- A. node にスコアを付ける: これは "Score" extension point の役割です。
- B. Pod を node にバインドする: これは "Bind" extension point の役割です。
- D. scheduling queue 内の Pod を並べ替える: これは "Queue Sort" extension point の役割です。
</details>

### 5. Which of the following is NOT something to consider when implementing a Custom Scheduler?

A. Node リソース使用量
B. Pod priority と preemption
C. Container image size
D. Node affinity と anti-affinity

<details>
<summary>答えを表示</summary>

**回答: C. Container image size**

**解説:**
Container image size は、Custom Scheduler を実装する際に一般的には考慮すべきものではありません。Image size は scheduling decision ではなく、image download と container startup time に影響し、それらは kubelet と container runtime の責任です。

**Custom Scheduler 実装時の主な考慮事項:**

1. **Node resource usage**:
   - CPU、memory、disk、network などのリソース使用量
   - 現在の使用量と requests を考慮した最適な配置
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

2. **Pod priority and preemption**:
   - 優先度の高い Pod を先にスケジューリングする
   - 必要に応じて優先度の低い Pod を preempt する
   - PriorityClass と preemptionPolicy を考慮する

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

3. **Node affinity and anti-affinity**:
   - Pod の nodeSelector、nodeAffinity 要件を満たす
   - inter-pod affinity と anti-affinity ルールを適用する
   - topology spread constraints を考慮する

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

4. **その他の重要な考慮事項**:
   - **Taints and tolerations**: node taints と Pod tolerations の一致
   - **Topology spread**: Pod をさまざまな topology domain に分散すること
   - **Node status**: Node status（Ready、MemoryPressure、DiskPressure など）
   - **Workload characteristics**: batch、service、daemonset など、さまざまな workload type の要件
   - **Network topology**: node 間の network latency と bandwidth
   - **Hardware characteristics**: GPU、FPGA などの特殊 hardware 要件

**container image size に関連する考慮事項:**
Container image size は、一般的に次の理由から scheduling decision に直接影響しません。

1. **Image availability**: image が node にすでにキャッシュされているかどうかは、scheduler ではなく kubelet が扱います。
2. **Download time**: Image download は scheduling decision の後に発生し、kubelet の責任です。
3. **Storage usage**: Image storage は一般的に node の allocatable resources の計算に含まれません。

ただし、特殊なケースでは、image locality を考慮する custom scheduler を実装できます。これにより、image がすでにキャッシュされている node を優先して startup time を短縮できます。

**他の選択肢の解説:**
- A. Node リソース使用量: scheduling decision における重要な要素であり、Pod のリソース要求を満たせる node を選択するために不可欠です。
- B. Pod priority と preemption: resource contention 時にどの Pod を先にスケジューリングするか、必要な場合にどの Pod を preempt するかを決定する上で重要です。
- D. Node affinity と anti-affinity: Pod を特定の node または他の Pod と一緒に、あるいは離してスケジューリングすべき制約を扱う上で重要です。
</details>
### 6. What is the role of the "Score" extension point in the Kubernetes scheduling framework?

A. Pod を実行できない node を除外する
B. filtering を通過した node にスコアを付ける
C. Pod を node にバインドする
D. scheduling queue 内の Pod を並べ替える

<details>
<summary>答えを表示</summary>

**回答: B. filtering を通過した node にスコアを付ける**

**解説:**
Kubernetes scheduling framework における "Score" extension point（以前は "Priority" と呼ばれていました）の役割は、filtering を通過した node にスコアを割り当てることです。Scoring plugin は各 node にスコアを割り当て、これらのスコアに基づいて最適な node が選択されます。

**Scoring Process:**
1. 各 scoring plugin は各 node に対してスコアを計算します（通常は 0〜100 の範囲）。
2. 各 plugin のスコアは、設定された weight に従って重み付けされます。
3. すべての plugin からの weighted score が合計されます。
4. 合計スコアが最も高い node が Pod の配置先として選択されます。

**Default Scoring Plugins:**
Kubernetes は次の default scoring plugin を提供しています。

1. **NodeResourcesBalancedAllocation**: CPU と memory の使用量がよくバランスした node に高いスコアを与えます。
2. **NodeResourcesFit**: requested resources に対して利用可能なリソースが多い node に高いスコアを与えます。
3. **NodeAffinity**: node affinity ルールに基づいてスコアを付けます。
4. **InterPodAffinity**: inter-pod affinity/anti-affinity ルールに基づいてスコアを付けます。
5. **PodTopologySpread**: Pod を topology domain 全体に均等に分散する node に高いスコアを与えます。
6. **TaintToleration**: taints が少ない node に高いスコアを与えます。
7. **ImageLocality**: 必要な container image をすでに持っている node に高いスコアを与えます。

**Custom Scoring Plugin Example:**
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

**Scheduler Configuration で Scoring Plugin を有効化し Weight を設定する:**
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

**Scoring Result Example:**
node A、B、C が filtering を通過し、2 つの scoring plugin があると仮定します。

1. MyScorePlugin (weight: 5)
   - Node A: 80 points
   - Node B: 60 points
   - Node C: 90 points

2. NodeResourcesBalancedAllocation (weight: 2)
   - Node A: 70 points
   - Node B: 90 points
   - Node C: 50 points

Weighted total scores:
- Node A: (80 x 5) + (70 x 2) = 400 + 140 = 540 points
- Node B: (60 x 5) + (90 x 2) = 300 + 180 = 480 points
- Node C: (90 x 5) + (50 x 2) = 450 + 100 = 550 points

この場合、Node C が最も高いスコアを受け取ったため、Pod は Node C にスケジューリングされます。

**他の選択肢の問題点:**
- A. Pod を実行できない node を除外する: これは "Filter" extension point の役割です。
- C. Pod を node にバインドする: これは "Bind" extension point の役割です。
- D. scheduling queue 内の Pod を並べ替える: これは "Queue Sort" extension point の役割です。
</details>

### 7. Which of the following is NOT a method for extending the scheduler in Kubernetes?

A. Scheduling framework plugin
B. Scheduler extender
C. 複数の scheduler をデプロイする
D. node controller を変更する

<details>
<summary>答えを表示</summary>

**回答: D. node controller を変更する**

**解説:**
node controller を変更することは、Kubernetes における scheduler の拡張方法ではありません。node controller は node status を監視および管理する control plane component であり、scheduling decision には直接関係しません。

**Kubernetes で scheduler を拡張する方法:**

1. **Scheduling framework plugin**:
   - Kubernetes 1.15 で導入され、scheduling cycle のさまざまな stage に plugin を挿入できます。
   - filter、score、bind などの extension point を提供します。
   - 効率のため scheduler codebase と直接統合されます。

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
   - 外部 HTTP service を通じて scheduler の機能を拡張します。
   - filtering、prioritization、binding stage を拡張できます。
   - scheduler とは別に実行されるため、performance overhead が発生する場合があります。

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

3. **複数の scheduler をデプロイする**:
   - default scheduler と並行して custom scheduler をデプロイします。
   - 各 scheduler は独立して動作し、Pod は `spec.schedulerName` を介して特定の scheduler を指定できます。
   - 完全な柔軟性を提供しますが、実装と保守が複雑になる場合があります。

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

**Node Controller の役割:**
node controller は次の役割を実行する control plane component です。
- Node registration と status monitoring
- Node status updates（Ready、NotReady など）
- Node status に基づく Pod removal（node が長時間 NotReady の場合）
- Node lifecycle management

node controller は scheduling decision には直接関与せず、scheduler が使用する node 情報を更新します。したがって、node controller を変更することは scheduler を拡張する方法ではありません。

**Scheduler Extension Method を選択する際の考慮事項:**
1. **Complexity**: Scheduling framework plugin は実装が複雑になる場合がありますが、scheduler と密接に統合されています。
2. **Performance**: Scheduler extender では HTTP call overhead が performance に影響する場合があります。
3. **Maintenance**: 複数の scheduler では、別々の codebase を保守する必要があります。
4. **Upgrades**: Kubernetes upgrade 時に compatibility issue が発生する場合があります。
5. **Features**: 各方法は異なるレベルの functionality と flexibility を提供します。

**他の選択肢の解説:**
- A. Scheduling framework plugin: 有効な scheduler 拡張方法です。
- B. Scheduler extender: 有効な scheduler 拡張方法です。
- C. 複数の scheduler をデプロイする: 有効な scheduler 拡張方法です。
</details>
### 8. What is the purpose of the `--leader-elect` flag in the Kubernetes scheduler?

A. scheduler に leadership authority を付与する
B. 複数の scheduler instance のうち 1 つだけを active にする
C. cluster の leader node 上でのみ scheduler を実行する
D. scheduler に他の component より高い priority を与える

<details>
<summary>答えを表示</summary>

**回答: B. 複数の scheduler instance のうち 1 つだけを active にする**

**解説:**
Kubernetes scheduler における `--leader-elect` flag の目的は、高可用性（HA）構成で 1 つの scheduler instance だけが active になり作業を実行するようにすることです。これにより、複数の scheduler instance が同時に動作した場合に発生し得る conflict や race condition を防ぎます。

**Leader Election Mechanism:**
1. 複数の scheduler instance がデプロイされると、leader election algorithm が 1 つの instance だけを leader として選出します。
2. leader として選出された instance だけが実際の scheduling work を実行します。
3. 他の instance は standby mode のままで、現在の leader が失敗した場合には新しい leader が選出されます。
4. この mechanism は Kubernetes resource locks を使用して実装されます。

**Leader Election Related Flags:**
```
--leader-elect=true                      # Whether to enable leader election (default: true)
--leader-elect-lease-duration=15s        # Leadership lease duration
--leader-elect-renew-deadline=10s        # Leadership renewal deadline
--leader-elect-retry-period=2s           # Leadership retry period
--leader-elect-resource-lock=leases      # Resource type to use for leadership lock
--leader-elect-resource-name=kube-scheduler  # Leadership lock resource name
--leader-elect-resource-namespace=kube-system  # Leadership lock resource namespace
```

**High Availability Scheduler Deployment Example:**
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

**Leader Election Status の確認:**
```bash
# Check leadership resource
kubectl get leases -n kube-system | grep kube-scheduler

# Check leadership details
kubectl describe lease kube-scheduler -n kube-system

# Check leadership related messages in scheduler logs
kubectl logs -n kube-system -l component=kube-scheduler | grep -i leader
```

**Custom Scheduler における Leader Election:**
custom scheduler を実装する場合、同じ leader election mechanism を使用できます。これは client-go library の leaderelection package を利用します。

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

**Leader Election を無効にすべきケース:**
1. **Single instance deployment**: scheduler が 1 つの instance としてのみデプロイされる場合
2. **異なる leader election mechanism の使用**: 外部 orchestration tool が instance activation を管理する場合
3. **異なる scheduler names**: 各 scheduler instance が異なる `schedulerName` を使用する場合

これらの場合、`--leader-elect=false` を設定して leader election を無効化できます。

**他の選択肢の問題点:**
- A. scheduler に leadership authority を付与する: これは leader election の具体的な目的を説明していない曖昧な説明です。
- C. cluster の leader node 上でのみ scheduler を実行する: Kubernetes には "leader node" という概念はありません。scheduler は control plane node 上で実行されます。
- D. scheduler に他の component より高い priority を与える: leader election は priority とは関係なく、複数の scheduler instance 間の coordination のためのものです。
</details>

### 9. What resource is used in Kubernetes to set pod scheduling priority?

A. PodSchedulingPolicy
B. PriorityClass
C. SchedulingPriority
D. PodPriority

<details>
<summary>答えを表示</summary>

**回答: B. PriorityClass**

**解説:**
Kubernetes で Pod の scheduling priority を設定するために使用される resource は `PriorityClass` です。PriorityClass は Pod の相対的な重要度を定義し、scheduler が scheduling と preemption の決定を行う際に priority を考慮できるようにします。

**PriorityClass Resource:**
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

**Key Fields:**
1. **value**: Priority value。値が大きいほど priority が高くなります。System Pod は通常 1000000000（10 億）以上の値を使用します。
2. **globalDefault**: true に設定すると、この priority class は priority class を指定しない Pod に適用されます。
3. **description**: priority class の説明です。
4. **preemptionPolicy**: Preemption policy。`PreemptLowerPriority`（default）または `Never` に設定できます。

**PriorityClass を Pod に適用する:**
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

**Priority と Preemption の動作:**
1. **Scheduling priority**: より高い priority の Pod は scheduling queue で先に処理されます。
2. **Preemption**: 高 priority Pod をスケジューリングする node がない場合、scheduler は低 priority Pod を削除（preempt）して空き容量を確保できます。
3. **Preemption policy**: `preemptionPolicy: Never` を持つ PriorityClass を使用する Pod は、他の Pod を preempt しません。

**System PriorityClasses:**
Kubernetes は次の system PriorityClasses を提供しています。
- **system-cluster-critical**: cluster operation に重要な Pod 用（value: 2000000000）
- **system-node-critical**: node operation に重要な Pod 用（value: 2000001000）

```bash
# Check system PriorityClasses
kubectl get priorityclasses | grep system
```

**PriorityClass Usage Example:**
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

**Priority と Preemption 関連 Metrics の監視:**
```bash
# Check preemption events
kubectl get events | grep -i preempt

# Check pod priorities
kubectl get pods -o custom-columns=NAME:.metadata.name,PRIORITY:.spec.priority
```

**Custom Scheduler で Priority を扱う:**
custom scheduler を実装する場合、scheduling decision を行う際に Pod priority を考慮する必要があります。

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

**他の選択肢の問題点:**
- A. PodSchedulingPolicy: Kubernetes API に存在しない resource です。
- C. SchedulingPriority: Kubernetes API に存在しない resource です。
- D. PodPriority: これは resource type ではなく、Pod spec の field（`spec.priority`）です。この field は PriorityClass によって自動的に設定されます。
</details>

### 10. What is the role of the Kubernetes scheduler's `NodeResourcesFit` plugin?

A. node の物理的な場所に従って Pod を配置する
B. node の resource capacity と Pod の resource requests を比較する
C. node operating system と Pod の互換性を確認する
D. node network bandwidth を測定する

<details>
<summary>答えを表示</summary>

**回答: B. node の resource capacity と Pod の resource requests を比較する**

**解説:**
Kubernetes scheduler の `NodeResourcesFit` plugin の役割は、node の resource capacity と Pod の resource requests を比較し、Pod がその node で実行できるかどうかを確認することです。この plugin は CPU、memory、ephemeral storage、extended resources（GPU など）を含むさまざまな resource type を考慮します。

**NodeResourcesFit Plugin の主な機能:**
1. **Resource request verification**: Pod の resource requests が node の allocatable resources を超えないか確認します。
2. **Resource limit verification**: Pod の resource limits が node の capacity を超えないか確認します。
3. **Extended resource verification**: GPU、FPGA などの extended resource requests が node で利用可能か確認します。
4. **Scoring**: filtering stage を通過した node に、resource usage に基づいてスコアを割り当てます。

**Resource Verification Process:**
1. Pod 内のすべての container の resource requests を合計します。
2. node の allocatable resources を確認します。
3. Pod の resource requests が node の allocatable resources を超えないか確認します。
4. 超えている場合、その node は filtered out されます。

**Scheduler における NodeResourcesFit Configuration:**
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
NodeResourcesFit plugin は次の scoring strategies をサポートします。

1. **LeastAllocated**: 使用済みリソースが少ない node に高いスコアを与えます。これは resource usage を分散するのに役立ちます。
   ```
   score = (capacity - requested) / capacity
   ```

2. **MostAllocated**: 使用済みリソースが多い node に高いスコアを与えます。これは node の数を最小化するために resource usage を集約するのに役立ちます。
   ```
   score = requested / capacity
   ```

3. **RequestedToCapacityRatio**: custom function を使用して requested resources と capacity の比率に基づいてスコアを割り当てます。

**Resource Types:**
NodeResourcesFit plugin は次の resource types を考慮します。

1. **CPU**: core または millicore で測定されます。
2. **Memory**: byte で測定されます。
3. **Ephemeral storage**: node の local ephemeral storage です。
4. **Extended resources**: GPU、FPGA などの custom resources です。

**Node Resources の確認:**
```bash
# Check node's allocatable resources
kubectl describe node <node-name> | grep Allocatable -A 5

# Check node's resource usage
kubectl top node <node-name>
```

**Pod Resource Requests の確認:**
```bash
# Check pod's resource requests
kubectl get pod <pod-name> -o jsonpath='{.spec.containers[*].resources.requests}'
```

**Custom Scheduler で Resource Fit Check を実装する:**
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

**他の選択肢の問題点:**
- A. node の物理的な場所に従って Pod を配置する: これは topology 関連 plugin（例: NodeAffinity、PodTopologySpread）の役割です。
- C. node operating system と Pod の互換性を確認する: これは NodeSelector または NodeAffinity を通じて処理され、個別の plugin ではありません。
- D. node network bandwidth を測定する: Kubernetes scheduler は default では network bandwidth を考慮しません。これには custom metrics と plugin が必要です。
</details>
