# Custom Scheduler Quiz (Part 1)

This quiz tests your understanding of implementing and using Custom Schedulers in Kubernetes.

## Quiz Questions

### 1. What is the main role of a scheduler in Kubernetes?

A. Pod creation and deletion
B. Assigning pods to appropriate nodes
C. Node resource monitoring
D. Container image download

<details>
<summary>Show Answer</summary>

**Answer: B. Assigning pods to appropriate nodes**

**Explanation:**
The main role of a scheduler in Kubernetes is to assign pods to appropriate nodes. The scheduler watches for newly created pods and finds the best node to run pods that have not yet been assigned to a node.

**Main Functions of the Scheduler:**
1. **Pod-Node Assignment**: Selects the optimal node considering pod requirements and node available resources.
2. **Filtering**: Excludes nodes that cannot run the pod (e.g., insufficient resources, taints, etc.).
3. **Scoring**: Scores suitable nodes to select the optimal node.
4. **Binding**: Binds the pod to the selected node to finalize the scheduling decision.

**Scheduling Process:**
1. **Filtering Stage (Predicates)**: Excludes nodes that cannot run the pod.
   - PodFitsResources: Checks if the node has enough resources to meet the pod's resource requests
   - PodFitsHostPorts: Checks if requested host ports are available
   - PodMatchNodeSelector: Checks if the pod's node selector matches node labels
   - NoVolumeZoneConflict: Checks volume zone constraints
   - CheckNodeMemoryPressure: Checks node memory pressure status
   - CheckNodeDiskPressure: Checks node disk pressure status

2. **Scoring Stage (Priorities)**: Scores suitable nodes.
   - LeastRequestedPriority: Gives higher scores to nodes with fewer requested resources
   - BalancedResourceAllocation: Gives higher scores to nodes with good resource usage balance
   - NodeAffinityPriority: Scores based on node affinity rules
   - TaintTolerationPriority: Scores based on taint toleration
   - InterPodAffinityPriority: Scores based on inter-pod affinity/anti-affinity

3. **Binding**: Binds the pod to the node with the highest score.

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

**Issues with Other Options:**
- A. Pod creation and deletion: This is primarily the role of the controller manager and API server.
- C. Node resource monitoring: This is primarily the role of kubelet and the metrics server.
- D. Container image download: This is the role of kubelet and the container runtime.
</details>

### 2. Which of the following is NOT a method for implementing a Custom Scheduler?

A. Extending the existing kube-scheduler
B. Implementing a completely new scheduler
C. Developing a scheduling framework plugin
D. Modifying kubelet

<details>
<summary>Show Answer</summary>

**Answer: D. Modifying kubelet**

**Explanation:**
Modifying kubelet is not a method for implementing a Custom Scheduler. kubelet is an agent that runs on each node and manages pod execution, but it does not make scheduling decisions. Scheduling is performed by kube-scheduler or custom schedulers.

**Methods for Implementing a Custom Scheduler:**

1. **Extending the existing kube-scheduler**:
   - Use KubeSchedulerConfiguration to customize the default scheduler's behavior.
   - Adjust plugin weights, enable/disable, etc.

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

2. **Implementing a completely new scheduler**:
   - Develop an independent scheduler that communicates with the Kubernetes API.
   - Implement pod watching, node selection, and binding logic directly.

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

3. **Developing a scheduling framework plugin**:
   - Use the Kubernetes scheduling framework to develop plugins for specific scheduling stages.
   - Implement extension points such as filter, score, bind, etc.

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

**Role of kubelet:**
kubelet is an agent that runs on each node and performs the following roles:
- Running and managing containers according to pod specs
- Monitoring and reporting node status
- Performing container health checks
- Managing volume mounts

kubelet executes the decisions made by the scheduler (which pod to run on which node), and does not make scheduling decisions itself.

**Explanation of Other Options:**
- A. Extending the existing kube-scheduler: A valid Custom Scheduler implementation method.
- B. Implementing a completely new scheduler: A valid Custom Scheduler implementation method.
- C. Developing a scheduling framework plugin: A valid Custom Scheduler implementation method.
</details>

### 3. What field is used in a pod to specify a specific scheduler?

A. spec.scheduler
B. spec.schedulerName
C. metadata.scheduler
D. spec.nodeName

<details>
<summary>Show Answer</summary>

**Answer: B. spec.schedulerName**

**Explanation:**
The field used in a pod to specify a specific scheduler is `spec.schedulerName`. When this field is set, the pod is scheduled only by the scheduler with the specified name. The default value is "default-scheduler".

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

This pod is scheduled only by the scheduler named "my-custom-scheduler". If a scheduler with that name does not exist in the cluster, the pod will remain in the `Pending` state.

**Example of Deploying Multiple Schedulers:**
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

**Considerations When Selecting a Scheduler:**
1. **Availability**: If the specified scheduler is not running, the pod will not be scheduled.
2. **Functionality**: Each scheduler can have different scheduling algorithms and policies.
3. **Resource isolation**: Different schedulers can be used to isolate workloads.
4. **Special hardware**: Dedicated schedulers can be used for special hardware like GPUs or FPGAs.

**Checking Scheduler Status:**
```bash
# Check pod status
kubectl get pod custom-scheduled-pod

# Check scheduling events
kubectl describe pod custom-scheduled-pod | grep -A 5 Events

# Check scheduler logs
kubectl logs -n kube-system -l component=my-custom-scheduler
```

**Issues with Other Options:**
- A. spec.scheduler: A field that does not exist in the Kubernetes API.
- C. metadata.scheduler: A field that does not exist in the Kubernetes API.
- D. spec.nodeName: This field is used to bypass the scheduler and directly assign a pod to a specific node. It is not a field for specifying a scheduler.
</details>
### 4. What is the role of the "Filter" extension point in the Kubernetes scheduling framework?

A. Score nodes
B. Bind pods to nodes
C. Exclude nodes where pods cannot run
D. Sort pods in the scheduling queue

<details>
<summary>Show Answer</summary>

**Answer: C. Exclude nodes where pods cannot run**

**Explanation:**
The role of the "Filter" extension point (formerly called "Predicate") in the Kubernetes scheduling framework is to exclude nodes where pods cannot run. Filter plugins check whether each node meets the pod's requirements and exclude nodes that do not meet them from the candidate list.

**Scheduling Framework Extension Points:**
The scheduling framework provides various extension points where plugins can be integrated at different stages of the scheduling cycle:

1. **Queue Sort**: Determines the order of pods in the scheduling queue.
2. **PreFilter**: Performs preprocessing on pod and cluster state before filtering.
3. **Filter**: Excludes nodes where pods cannot run.
4. **PreScore**: Performs calculations needed before scoring.
5. **Score**: Assigns scores to nodes that passed filtering.
6. **NormalizeScore**: Normalizes scores from each scoring plugin.
7. **Reserve**: Reserves pod resources on the selected node.
8. **Permit**: Allows, denies, or delays pod scheduling.
9. **PreBind**: Performs work needed before binding.
10. **Bind**: Binds the pod to the node.
11. **PostBind**: Performs cleanup work after binding.

**Default Filter Plugins:**
Kubernetes provides the following default filter plugins:

1. **NodeResourcesFit**: Checks if the node has enough resources to meet the pod's resource requests.
2. **NodeName**: Checks if the pod's spec.nodeName field matches the node name.
3. **NodeUnschedulable**: Checks if the node is marked as unschedulable.
4. **TaintToleration**: Checks if the pod tolerates the node's taints.
5. **NodeAffinity**: Checks if the pod's node affinity requirements are met.
6. **PodAffinity**: Checks if the pod's pod affinity requirements are met.
7. **VolumeRestrictions**: Checks volume constraints.
8. **EBSLimits**: Checks Amazon EBS volume limits.
9. **NoVolumeZoneConflict**: Checks volume zone constraints.
10. **CheckNodeMemoryPressure**: Checks node memory pressure status.
11. **CheckNodeDiskPressure**: Checks node disk pressure status.

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

**Enabling Filter Plugin in Scheduler Configuration:**
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

**Issues with Other Options:**
- A. Score nodes: This is the role of the "Score" extension point.
- B. Bind pods to nodes: This is the role of the "Bind" extension point.
- D. Sort pods in the scheduling queue: This is the role of the "Queue Sort" extension point.
</details>

### 5. Which of the following is NOT something to consider when implementing a Custom Scheduler?

A. Node resource usage
B. Pod priority and preemption
C. Container image size
D. Node affinity and anti-affinity

<details>
<summary>Show Answer</summary>

**Answer: C. Container image size**

**Explanation:**
Container image size is generally not something to consider when implementing a Custom Scheduler. Image size affects image download and container startup time rather than scheduling decisions, which is the responsibility of kubelet and the container runtime.

**Key Considerations When Implementing a Custom Scheduler:**

1. **Node resource usage**:
   - Resource usage such as CPU, memory, disk, network
   - Optimal placement considering current usage and requests
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
   - Schedule higher priority pods first
   - Preempt lower priority pods when necessary
   - Consider PriorityClass and preemptionPolicy

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
   - Meet pod's nodeSelector, nodeAffinity requirements
   - Apply inter-pod affinity and anti-affinity rules
   - Consider topology spread constraints

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

4. **Other important considerations**:
   - **Taints and tolerations**: Matching node taints and pod tolerations
   - **Topology spread**: Spreading pods across various topology domains
   - **Node status**: Node status (Ready, MemoryPressure, DiskPressure, etc.)
   - **Workload characteristics**: Requirements of various workload types such as batch, service, daemonset
   - **Network topology**: Network latency and bandwidth between nodes
   - **Hardware characteristics**: Special hardware requirements like GPUs, FPGAs

**Considerations related to container image size:**
Container image size generally does not directly affect scheduling decisions for the following reasons:

1. **Image availability**: Whether the image is already cached on the node is handled by kubelet, not the scheduler.
2. **Download time**: Image download occurs after the scheduling decision and is the responsibility of kubelet.
3. **Storage usage**: Image storage is generally not included in the calculation of node allocatable resources.

However, in special cases, a custom scheduler that considers image locality can be implemented. This can help reduce startup time by preferring nodes where the image is already cached.

**Explanation of Other Options:**
- A. Node resource usage: An important factor in scheduling decisions, essential for selecting nodes that can meet the pod's resource requests.
- B. Pod priority and preemption: Important for deciding which pods to schedule first during resource contention and which pods to preempt when necessary.
- D. Node affinity and anti-affinity: Important for handling constraints where pods should be scheduled together with or apart from specific nodes or other pods.
</details>
### 6. What is the role of the "Score" extension point in the Kubernetes scheduling framework?

A. Exclude nodes where pods cannot run
B. Score nodes that passed filtering
C. Bind pods to nodes
D. Sort pods in the scheduling queue

<details>
<summary>Show Answer</summary>

**Answer: B. Score nodes that passed filtering**

**Explanation:**
The role of the "Score" extension point (formerly called "Priority") in the Kubernetes scheduling framework is to assign scores to nodes that passed filtering. Scoring plugins assign scores to each node, and the optimal node is selected based on these scores.

**Scoring Process:**
1. Each scoring plugin calculates a score for each node (typically in the range of 0-100).
2. Each plugin's score is weighted according to the configured weight.
3. The weighted scores from all plugins are summed.
4. The node with the highest total score is selected for pod placement.

**Default Scoring Plugins:**
Kubernetes provides the following default scoring plugins:

1. **NodeResourcesBalancedAllocation**: Gives higher scores to nodes with well-balanced CPU and memory usage.
2. **NodeResourcesFit**: Gives higher scores to nodes with more available resources relative to requested resources.
3. **NodeAffinity**: Scores based on node affinity rules.
4. **InterPodAffinity**: Scores based on inter-pod affinity/anti-affinity rules.
5. **PodTopologySpread**: Gives higher scores to nodes that spread pods evenly across topology domains.
6. **TaintToleration**: Gives higher scores to nodes with fewer taints.
7. **ImageLocality**: Gives higher scores to nodes that already have the required container images.

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

**Enabling Scoring Plugin and Setting Weight in Scheduler Configuration:**
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
Assuming nodes A, B, C passed filtering and there are two scoring plugins:

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

In this case, Node C received the highest score, so the pod is scheduled on Node C.

**Issues with Other Options:**
- A. Exclude nodes where pods cannot run: This is the role of the "Filter" extension point.
- C. Bind pods to nodes: This is the role of the "Bind" extension point.
- D. Sort pods in the scheduling queue: This is the role of the "Queue Sort" extension point.
</details>

### 7. Which of the following is NOT a method for extending the scheduler in Kubernetes?

A. Scheduling framework plugin
B. Scheduler extender
C. Deploying multiple schedulers
D. Modifying the node controller

<details>
<summary>Show Answer</summary>

**Answer: D. Modifying the node controller**

**Explanation:**
Modifying the node controller is not a method for extending the scheduler in Kubernetes. The node controller is a control plane component that monitors and manages node status, and is not directly related to scheduling decisions.

**Methods for Extending the Scheduler in Kubernetes:**

1. **Scheduling framework plugin**:
   - Introduced in Kubernetes 1.15, allows inserting plugins at various stages of the scheduling cycle.
   - Provides extension points such as filter, score, bind, etc.
   - Integrated directly with the scheduler codebase for efficiency.

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
   - Extends scheduler functionality through an external HTTP service.
   - Can extend filtering, prioritization, binding stages.
   - May have performance overhead since it runs separately from the scheduler.

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

3. **Deploying multiple schedulers**:
   - Deploy custom schedulers alongside the default scheduler.
   - Each scheduler operates independently, and pods can specify a particular scheduler via `spec.schedulerName`.
   - Provides complete flexibility but can be complex to implement and maintain.

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

**Role of the Node Controller:**
The node controller is a control plane component that performs the following roles:
- Node registration and status monitoring
- Node status updates (Ready, NotReady, etc.)
- Pod removal based on node status (when a node is NotReady for a long time)
- Node lifecycle management

The node controller is not directly involved in scheduling decisions; it updates node information used by the scheduler. Therefore, modifying the node controller is not a method for extending the scheduler.

**Considerations When Choosing a Scheduler Extension Method:**
1. **Complexity**: Scheduling framework plugins can be complex to implement but are tightly integrated with the scheduler.
2. **Performance**: Scheduler extenders may have HTTP call overhead that can affect performance.
3. **Maintenance**: Multiple schedulers require maintaining separate codebases.
4. **Upgrades**: Compatibility issues may arise during Kubernetes upgrades.
5. **Features**: Each method provides different levels of functionality and flexibility.

**Explanation of Other Options:**
- A. Scheduling framework plugin: A valid scheduler extension method.
- B. Scheduler extender: A valid scheduler extension method.
- C. Deploying multiple schedulers: A valid scheduler extension method.
</details>
### 8. What is the purpose of the `--leader-elect` flag in the Kubernetes scheduler?

A. Grant leadership authority to the scheduler
B. Activate only one instance among multiple scheduler instances
C. Run the scheduler only on the leader node of the cluster
D. Give the scheduler higher priority than other components

<details>
<summary>Show Answer</summary>

**Answer: B. Activate only one instance among multiple scheduler instances**

**Explanation:**
The purpose of the `--leader-elect` flag in the Kubernetes scheduler is to ensure that only one scheduler instance is active and performs work in high availability (HA) configurations. This prevents conflicts and race conditions that could occur if multiple scheduler instances were working simultaneously.

**Leader Election Mechanism:**
1. When multiple scheduler instances are deployed, a leader election algorithm elects only one instance as the leader.
2. Only the instance elected as leader performs actual scheduling work.
3. Other instances remain in standby mode, and a new leader is elected if the current leader fails.
4. This mechanism is implemented using Kubernetes resource locks.

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

**Checking Leader Election Status:**
```bash
# Check leadership resource
kubectl get leases -n kube-system | grep kube-scheduler

# Check leadership details
kubectl describe lease kube-scheduler -n kube-system

# Check leadership related messages in scheduler logs
kubectl logs -n kube-system -l component=kube-scheduler | grep -i leader
```

**Leader Election in Custom Scheduler:**
When implementing a custom scheduler, you can use the same leader election mechanism. This utilizes the leaderelection package from the client-go library.

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

**Cases When Leader Election Should Be Disabled:**
1. **Single instance deployment**: When the scheduler is deployed as only one instance
2. **Using a different leader election mechanism**: When an external orchestration tool manages instance activation
3. **Different scheduler names**: When each scheduler instance uses a different `schedulerName`

In these cases, you can disable leader election by setting `--leader-elect=false`.

**Issues with Other Options:**
- A. Grant leadership authority to the scheduler: This is a vague description that does not explain the specific purpose of leader election.
- C. Run the scheduler only on the leader node of the cluster: There is no concept of "leader node" in Kubernetes; the scheduler runs on control plane nodes.
- D. Give the scheduler higher priority than other components: Leader election is not related to priority; it is for coordination among multiple scheduler instances.
</details>

### 9. What resource is used in Kubernetes to set pod scheduling priority?

A. PodSchedulingPolicy
B. PriorityClass
C. SchedulingPriority
D. PodPriority

<details>
<summary>Show Answer</summary>

**Answer: B. PriorityClass**

**Explanation:**
The resource used in Kubernetes to set pod scheduling priority is `PriorityClass`. PriorityClass defines the relative importance of pods, allowing the scheduler to consider priority when making scheduling and preemption decisions.

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
1. **value**: Priority value; higher values mean higher priority. System pods typically use values of 1000000000 (1 billion) or higher.
2. **globalDefault**: When set to true, this priority class is applied to pods that do not specify a priority class.
3. **description**: Description of the priority class.
4. **preemptionPolicy**: Preemption policy, can be set to `PreemptLowerPriority` (default) or `Never`.

**Applying PriorityClass to a Pod:**
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

**Priority and Preemption Behavior:**
1. **Scheduling priority**: Higher priority pods are processed first in the scheduling queue.
2. **Preemption**: When there is no node to schedule a high priority pod, the scheduler can remove (preempt) lower priority pods to free up space.
3. **Preemption policy**: Pods using a PriorityClass with `preemptionPolicy: Never` do not preempt other pods.

**System PriorityClasses:**
Kubernetes provides the following system PriorityClasses:
- **system-cluster-critical**: For pods critical to cluster operation (value: 2000000000)
- **system-node-critical**: For pods critical to node operation (value: 2000001000)

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

**Monitoring Priority and Preemption Related Metrics:**
```bash
# Check preemption events
kubectl get events | grep -i preempt

# Check pod priorities
kubectl get pods -o custom-columns=NAME:.metadata.name,PRIORITY:.spec.priority
```

**Handling Priority in Custom Scheduler:**
When implementing a custom scheduler, you should consider pod priority when making scheduling decisions.

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

**Issues with Other Options:**
- A. PodSchedulingPolicy: A resource that does not exist in the Kubernetes API.
- C. SchedulingPriority: A resource that does not exist in the Kubernetes API.
- D. PodPriority: This is not a resource type but a field in the pod spec (`spec.priority`). This field is automatically set by the PriorityClass.
</details>

### 10. What is the role of the Kubernetes scheduler's `NodeResourcesFit` plugin?

A. Place pods according to the physical location of nodes
B. Compare node resource capacity with pod resource requests
C. Check compatibility between node operating system and pod
D. Measure node network bandwidth

<details>
<summary>Show Answer</summary>

**Answer: B. Compare node resource capacity with pod resource requests**

**Explanation:**
The role of the Kubernetes scheduler's `NodeResourcesFit` plugin is to compare node resource capacity with pod resource requests to check whether the pod can run on the node. This plugin considers various resource types including CPU, memory, ephemeral storage, and extended resources (GPUs, etc.).

**Main Functions of the NodeResourcesFit Plugin:**
1. **Resource request verification**: Checks if the pod's resource requests do not exceed the node's allocatable resources.
2. **Resource limit verification**: Checks if the pod's resource limits do not exceed the node's capacity.
3. **Extended resource verification**: Checks if extended resource requests like GPUs, FPGAs are available on the node.
4. **Scoring**: Assigns scores to nodes that passed the filtering stage based on resource usage.

**Resource Verification Process:**
1. Sum up resource requests from all containers in the pod.
2. Check the node's allocatable resources.
3. Check if the pod's resource requests do not exceed the node's allocatable resources.
4. If they exceed, the node is filtered out.

**NodeResourcesFit Configuration in Scheduler:**
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
The NodeResourcesFit plugin supports the following scoring strategies:

1. **LeastAllocated**: Gives higher scores to nodes with less used resources. This is useful for spreading resource usage.
   ```
   score = (capacity - requested) / capacity
   ```

2. **MostAllocated**: Gives higher scores to nodes with more used resources. This is useful for concentrating resource usage to minimize the number of nodes.
   ```
   score = requested / capacity
   ```

3. **RequestedToCapacityRatio**: Assigns scores based on the ratio of requested resources to capacity using a custom function.

**Resource Types:**
The NodeResourcesFit plugin considers the following resource types:

1. **CPU**: Measured in cores or millicores.
2. **Memory**: Measured in bytes.
3. **Ephemeral storage**: Node's local ephemeral storage.
4. **Extended resources**: Custom resources like GPUs, FPGAs.

**Checking Node Resources:**
```bash
# Check node's allocatable resources
kubectl describe node <node-name> | grep Allocatable -A 5

# Check node's resource usage
kubectl top node <node-name>
```

**Checking Pod Resource Requests:**
```bash
# Check pod's resource requests
kubectl get pod <pod-name> -o jsonpath='{.spec.containers[*].resources.requests}'
```

**Implementing Resource Fit Check in Custom Scheduler:**
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

**Issues with Other Options:**
- A. Place pods according to the physical location of nodes: This is the role of topology-related plugins (e.g., NodeAffinity, PodTopologySpread).
- C. Check compatibility between node operating system and pod: This is handled through NodeSelector or NodeAffinity, not a separate plugin.
- D. Measure node network bandwidth: The Kubernetes scheduler does not consider network bandwidth by default. Custom metrics and plugins are needed for this.
</details>
