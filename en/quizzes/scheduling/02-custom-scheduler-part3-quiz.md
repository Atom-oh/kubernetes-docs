# Custom Scheduler Quiz (Part 3)

This quiz tests your advanced understanding of implementing and using Custom Schedulers in Kubernetes.

## Quiz Questions

### 1. Which of the following is NOT a problem that can occur when running multiple schedulers simultaneously in Kubernetes?

A. Resource contention
B. Scheduling decision conflicts
C. Increased network bandwidth
D. Leader election conflicts

<details>
<summary>Show Answer</summary>

**Answer: C. Increased network bandwidth**

**Explanation:**
"Increased network bandwidth" is NOT a problem that can occur when running multiple schedulers simultaneously in Kubernetes. While schedulers communicate with the API server, the network bandwidth usage is typically minimal and not a concern.

**Actual problems that can occur when running multiple schedulers:**

1. **Resource contention**:
   - Resource contention can occur when multiple schedulers try to schedule pods to the same node pool.
   - Since each scheduler operates independently without awareness of other schedulers' decisions, there's a risk of over-allocating node resources.
   - Example: Two schedulers may simultaneously schedule pods to the same node, exceeding node capacity.

2. **Scheduling decision conflicts**:
   - Conflicts can occur when multiple schedulers try to schedule the same pod.
   - This can happen when pods don't explicitly specify a `schedulerName`, or when multiple schedulers use the same name.
   - Example: Race conditions occur when two schedulers try to bind the same pod to different nodes.

3. **Leader election conflicts**:
   - If multiple scheduler instances with the same name are running with leader election enabled, conflicts can occur in the leader election mechanism.
   - Example: Multiple scheduler instances with the same name competing for leadership can cause unstable leadership transitions.

**Best practices when running multiple schedulers:**

1. **Clear separation of responsibilities**:
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

2. **Use unique scheduler names**:
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

3. **Separate node pools using node labels and taints**:
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

4. **Set resource quotas**:
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

**Monitoring multiple schedulers:**
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

**Explanation of other options:**
- A. Resource contention: An actual problem that can occur when multiple schedulers schedule pods to the same node pool.
- B. Scheduling decision conflicts: An actual problem that can occur when multiple schedulers try to schedule the same pod.
- D. Leader election conflicts: An actual problem that can occur when multiple scheduler instances with the same name compete for leadership.
</details>

### 2. What is the role of the "Permit" extension point in the Kubernetes scheduler?

A. Bind pods to nodes
B. Allow, deny, or delay pod scheduling
C. Exclude nodes where pods cannot run
D. Assign scores to nodes

<details>
<summary>Show Answer</summary>

**Answer: B. Allow, deny, or delay pod scheduling**

**Explanation:**
The role of the "Permit" extension point in the Kubernetes scheduling framework is to allow, deny, or delay pod scheduling. Permit plugins run after a node is selected but before the binding phase, providing final approval or rejection for pod scheduling decisions.

**Key functions of the Permit extension point:**
1. **Allow**: Permits pod scheduling to proceed to the binding phase.
2. **Deny**: Rejects pod scheduling so another node can be selected.
3. **Wait**: Temporarily delays pod scheduling and waits until specific conditions are met.

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

**Permit result types:**
1. **Success**: Allows pod scheduling.
2. **Deny**: Rejects pod scheduling.
3. **Wait**: Delays pod scheduling and waits for the specified time.

**Default Permit plugins:**
Kubernetes provides the following default Permit plugins:

1. **TaintToleration**: Checks node taints and pod tolerations.
2. **PodTopologySpread**: Checks pod topology spread constraints.

**Custom Permit plugin example:**
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

**Enabling Permit plugin in scheduler configuration:**
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

**Permit use cases:**
1. **Gang scheduling**: Delay scheduling of a pod group until all related pods are ready to be scheduled.
2. **Resource reservation**: Reserve external resources before pods are scheduled.
3. **Policy validation**: Ensure pod scheduling complies with organizational policies.
4. **Approval workflows**: Request external approval for pod scheduling.

**Gang scheduling example:**
Gang scheduling is a technique that ensures all related pods are scheduled together. This is useful for workloads like distributed training jobs where all components must run simultaneously.

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

**Issues with other options:**
- A. Bind pods to nodes: This is the role of the "Bind" extension point.
- C. Exclude nodes where pods cannot run: This is the role of the "Filter" extension point.
- D. Assign scores to nodes: This is the role of the "Score" extension point.
</details>
### 3. What is the main purpose of Gang Scheduling in Kubernetes?

A. Place pods only on specific nodes
B. Ensure all related pods are scheduled together
C. Distribute pods evenly across various nodes
D. Schedule pods based on priority

<details>
<summary>Show Answer</summary>

**Answer: B. Ensure all related pods are scheduled together**

**Explanation:**
The main purpose of Gang Scheduling in Kubernetes is to ensure that all related pods are scheduled together. This is important for workloads like distributed training jobs and distributed data processing jobs where all components must run simultaneously.

**Why Gang scheduling is needed:**
1. **All-or-Nothing requirement**: Some workloads require all components to run simultaneously; if only some run, the job doesn't progress.
2. **Preventing resource waste**: If only some pods are scheduled while others wait, resources used by already-scheduled pods may be wasted.
3. **Preventing deadlock**: Deadlock can occur when interdependent pods are scheduled at different times.

**Gang scheduling implementation methods:**
Kubernetes doesn't natively support Gang scheduling, but it can be implemented through:

1. **Custom scheduler**: Implement Gang scheduling using the Permit extension point.
2. **External controller**: Implement a controller that manages Gang scheduling outside Kubernetes.
3. **Open source solutions**: Use open source schedulers like Volcano or Kube-batch.

**Gang scheduling example (Volcano):**
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

**Gang scheduling implementation using custom Permit plugin:**
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

**Pros and cons of Gang scheduling:**
Pros:
- Ensures all related pods are scheduled together
- Prevents resource waste
- Prevents deadlock and starvation

Cons:
- Increased implementation complexity
- Potential scheduling delays
- Potential decrease in cluster resource utilization

**Workloads that need Gang scheduling:**
1. **Distributed training jobs**: Distributed training frameworks like TensorFlow, PyTorch
2. **Distributed data processing**: Distributed data processing frameworks like Spark, Flink
3. **MPI jobs**: High-performance computing (HPC) workloads
4. **Service mesh**: Service meshes where multiple components must work together

**Issues with other options:**
- A. Place pods only on specific nodes: This is the role of node selectors or node affinity.
- C. Distribute pods evenly across various nodes: This is the role of pod topology spread constraints.
- D. Schedule pods based on priority: This is the role of pod priority and preemption.
</details>

### 4. Which of the following is NOT a required API endpoint when implementing a Scheduler Extender in Kubernetes?

A. /filter
B. /prioritize
C. /bind
D. /validate

<details>
<summary>Show Answer</summary>

**Answer: D. /validate**

**Explanation:**
"/validate" is NOT a required API endpoint when implementing a Scheduler Extender in Kubernetes. Scheduler extenders typically implement endpoints like "/filter", "/prioritize", "/bind", "/preempt", but "/validate" is not a standard API for scheduler extenders.

**Scheduler Extender API endpoints:**
1. **filter**: Receives a list of nodes and returns a filtered list of nodes.
2. **prioritize**: Receives a list of nodes and assigns scores to each node.
3. **bind**: Binds a pod to a node.
4. **preempt**: Returns nodes and pods for preemption.

**Scheduler Extender configuration example:**
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

**Scheduler Extender API request and response formats:**

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

**Pros and cons of Scheduler Extenders:**
Pros:
- Can be developed independently from the scheduler codebase
- Can be implemented in various programming languages
- Less affected by scheduler upgrades

Cons:
- Performance degradation due to HTTP communication overhead
- Can only extend some stages of the scheduling cycle
- Possibility of communication failure between scheduler and extender

**Scheduler Extender vs Scheduling Framework plugins:**
- **Scheduler Extender**: Runs as an external process via HTTP webhooks.
- **Scheduling Framework plugins**: Runs directly integrated with the scheduler codebase.

**Explanation of other options:**
- A. /filter: A valid scheduler extender API endpoint that filters the node list.
- B. /prioritize: A valid scheduler extender API endpoint that assigns scores to nodes.
- C. /bind: A valid scheduler extender API endpoint that binds pods to nodes.
</details>
### 5. What is the role of the "PostFilter" extension point in the Kubernetes scheduler framework?

A. Assign scores to nodes after filtering
B. Bind pods to nodes after filtering
C. Execute preemption logic when filtering fails
D. Update pod status after filtering

<details>
<summary>Show Answer</summary>

**Answer: C. Execute preemption logic when filtering fails**

**Explanation:**
The role of the "PostFilter" extension point in the Kubernetes scheduling framework is to execute preemption logic when filtering fails. When all nodes are excluded during the filtering phase and a pod cannot be scheduled, PostFilter plugins find ways to schedule the pod through preemption.

**Key functions of the PostFilter extension point:**
1. **Identify preemption candidates**: Identifies pods and nodes that can be preempted.
2. **Preemption simulation**: Simulates whether pods can be scheduled after preemption.
3. **Preemption decision**: Determines the optimal preemption strategy.

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

**Default PostFilter plugin:**
Kubernetes provides the following default PostFilter plugin:

1. **DefaultPreemption**: Implements default preemption logic.

**DefaultPreemption plugin operation:**
1. Identifies nodes where space can be made by preempting lower-priority pods.
2. Determines which pods to preempt on each node.
3. Verifies that pods can be scheduled after preemption.
4. Selects the optimal preemption strategy.
5. Sets the selected node as the pod's nominatedNodeName.

**Custom PostFilter plugin example:**
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

**Enabling PostFilter plugin in scheduler configuration:**
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

**Preemption-related settings:**
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

**Preemption process:**
1. PostFilter phase is called when a pod fails the filtering phase on all nodes.
2. PostFilter plugin identifies preemption candidate nodes.
3. Determines which pods to preempt on each node.
4. Verifies that pods can be scheduled after preemption.
5. Selects the optimal preemption strategy.
6. Sets the selected node as the pod's nominatedNodeName.
7. Preempted pods undergo graceful termination.
8. When preempted pods terminate, higher-priority pods are scheduled.

**Monitoring preemption-related metrics:**
```bash
# Check preemption-related metrics from scheduler metrics
kubectl get --raw /metrics | grep scheduler_preemption
```

**Check preemption events:**
```bash
# Check preemption events
kubectl get events | grep -i preempt
```

**Issues with other options:**
- A. Assign scores to nodes after filtering: This is the role of the "Score" extension point.
- B. Bind pods to nodes after filtering: This is the role of the "Bind" extension point.
- D. Update pod status after filtering: This is not an extension point in the scheduler framework.
</details>

### 6. What is the main purpose of the "NodeResourcesBalancedAllocation" plugin in the Kubernetes scheduler?

A. Give higher scores to nodes with balanced CPU and memory usage
B. Give higher scores to nodes with lower resource usage
C. Give higher scores to nodes with higher resource usage
D. Set resource limits on nodes

<details>
<summary>Show Answer</summary>

**Answer: A. Give higher scores to nodes with balanced CPU and memory usage**

**Explanation:**
The main purpose of the "NodeResourcesBalancedAllocation" plugin in the Kubernetes scheduler is to give higher scores to nodes with balanced CPU and memory usage. This plugin prefers nodes where the difference between CPU and memory utilization is small, improving overall resource usage balance across the cluster.

**NodeResourcesBalancedAllocation plugin operation:**
1. Calculates CPU utilization and memory utilization for each node.
2. Calculates the difference between CPU utilization and memory utilization.
3. Gives higher scores to nodes with smaller differences.

**Score calculation method:**
```
score = 10 - variance(cpuFraction, memoryFraction) * 10
```
Where:
- cpuFraction = (requested CPU + pod's CPU request) / allocatable CPU
- memoryFraction = (requested memory + pod's memory request) / allocatable memory
- variance(a, b) = |a - b|

**Example:**
- Node A: CPU utilization 80%, memory utilization 80% -> difference: 0% -> score: 10
- Node B: CPU utilization 90%, memory utilization 50% -> difference: 40% -> score: 6
- Node C: CPU utilization 30%, memory utilization 90% -> difference: 60% -> score: 4

In this case, Node A receives the highest score and is most likely to be selected.

**Enabling NodeResourcesBalancedAllocation plugin in scheduler configuration:**
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

**NodeResourcesBalancedAllocation vs other scoring plugins:**
1. **NodeResourcesBalancedAllocation**: Prefers nodes with balanced CPU and memory usage.
2. **NodeResourcesFit**: Prefers nodes with more available resources compared to requested resources.
3. **NodeResourcesLeastAllocated**: Prefers nodes with lower resource usage.
4. **NodeResourcesMostAllocated**: Prefers nodes with higher resource usage.

**Use cases:**
1. **Resource balance**: Improves CPU and memory usage balance across the entire cluster.
2. **Bottleneck prevention**: Prevents one resource type (CPU or memory) from being exhausted before the other.
3. **Scalability improvement**: Clusters with balanced resource usage can scale more efficiently.

**Custom balanced allocation plugin example:**
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

**Issues with other options:**
- B. Give higher scores to nodes with lower resource usage: This is the role of the "NodeResourcesLeastAllocated" plugin.
- C. Give higher scores to nodes with higher resource usage: This is the role of the "NodeResourcesMostAllocated" plugin.
- D. Set resource limits on nodes: This is not the role of scheduler plugins; node resource limits are properties of the nodes themselves.
</details>
### 7. What is the role of the "PreBind" extension point in the Kubernetes scheduler?

A. Bind pods to nodes
B. Perform necessary operations before binding
C. Perform cleanup after binding
D. Perform recovery operations when binding fails

<details>
<summary>Show Answer</summary>

**Answer: B. Perform necessary operations before binding**

**Explanation:**
The role of the "PreBind" extension point in the Kubernetes scheduling framework is to perform necessary operations before binding a pod to a node. For example, operations like volume provisioning, network setup, and resource reservation can be performed.

**Key functions of the PreBind extension point:**
1. **Volume provisioning**: Creates and prepares necessary volumes.
2. **Network setup**: Configures necessary network resources.
3. **Resource reservation**: Reserves necessary resources.
4. **Pre-validation**: Final verification that binding is possible.

**PreBind plugin interface:**
```go
type PreBindPlugin interface {
    Plugin
    // PreBind is called before binding a pod to a node.
    PreBind(ctx context.Context, state *CycleState, pod *v1.Pod, nodeName string) *Status
}
```

**Default PreBind plugins:**
Kubernetes provides the following default PreBind plugins:

1. **VolumeBinding**: Performs volume binding operations.
2. **DefaultPreBind**: Performs basic pre-binding operations.

**Custom PreBind plugin example:**
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

**Enabling PreBind plugin in scheduler configuration:**
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

**PreBind use cases:**
1. **Volume provisioning**:
   - PersistentVolume creation and binding
   - Ephemeral volume preparation
   - Storage class parameter validation

2. **Network setup**:
   - Network policy application
   - Service endpoint setup
   - Load balancer configuration

3. **Resource reservation**:
   - GPU resource reservation
   - FPGA resource reservation
   - Special hardware resource reservation

4. **Security setup**:
   - Security policy application
   - Certificate provisioning
   - Secret mount preparation

**PreBind failure handling:**
When a PreBind plugin returns failure:
1. The scheduling cycle is aborted.
2. The pod goes back to the scheduling queue.
3. Reserved resources are released.
4. Failure events are logged.

**Monitoring PreBind logs and events:**
```bash
# Check PreBind-related messages in scheduler logs
kubectl logs -n kube-system <scheduler-pod> | grep -i prebind

# Check pod events
kubectl describe pod <pod-name> | grep -i prebind
```

**Issues with other options:**
- A. Bind pods to nodes: This is the role of the "Bind" extension point.
- C. Perform cleanup after binding: This is the role of the "PostBind" extension point.
- D. Perform recovery operations when binding fails: This is not an extension point in the scheduler framework.
</details>

### 8. What is the main purpose of the "NodeResourcesFit" plugin in the Kubernetes scheduler?

A. Monitor node resource usage
B. Set node resource limits
C. Compare node resource capacity with pod resource requests
D. Maintain node resource usage balance

<details>
<summary>Show Answer</summary>

**Answer: C. Compare node resource capacity with pod resource requests**

**Explanation:**
The main purpose of the "NodeResourcesFit" plugin in the Kubernetes scheduler is to compare node resource capacity with pod resource requests to verify whether pods can run on nodes. This plugin considers various resource types including CPU, memory, ephemeral storage, and extended resources (like GPUs).

**Key functions of the NodeResourcesFit plugin:**
1. **Resource request validation**: Verifies that pod resource requests don't exceed node's allocatable resources.
2. **Resource limit validation**: Verifies that pod resource limits don't exceed node capacity.
3. **Extended resource validation**: Verifies that extended resource requests like GPUs and FPGAs are available on nodes.

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

**Scoring strategies:**
The NodeResourcesFit plugin supports the following scoring strategies:

1. **LeastAllocated**: Gives higher scores to nodes with fewer resources in use.
   ```
   score = (capacity - requested) / capacity
   ```

2. **MostAllocated**: Gives higher scores to nodes with more resources in use.
   ```
   score = requested / capacity
   ```

3. **RequestedToCapacityRatio**: Uses custom functions to assign scores based on the ratio of requested resources to capacity.

**Custom NodeResourcesFit plugin example:**
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

**Resource request and limit example:**
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

**Issues with other options:**
- A. Monitor node resource usage: This is the role of metrics servers or monitoring systems.
- B. Set node resource limits: This is the role of node configuration or kubelet.
- D. Maintain node resource usage balance: This is the role of the "NodeResourcesBalancedAllocation" plugin.
</details>
### 9. What is the main purpose of the "InterPodAffinity" plugin in the Kubernetes scheduler?

A. Process affinity rules between pods and nodes
B. Process affinity and anti-affinity rules between pods
C. Process affinity rules between pods and volumes
D. Process affinity rules between pods and services

<details>
<summary>Show Answer</summary>

**Answer: B. Process affinity and anti-affinity rules between pods**

**Explanation:**
The main purpose of the "InterPodAffinity" plugin in the Kubernetes scheduler is to process affinity and anti-affinity rules between pods. This plugin controls whether pods are placed in the same topology domain (node, zone, region, etc.) as other pods (affinity) or in different domains (anti-affinity).

**Key functions of the InterPodAffinity plugin:**
1. **Pod affinity rule processing**: Ensures pods are placed in the same topology domain as other pods with specific labels.
2. **Pod anti-affinity rule processing**: Ensures pods are placed in different topology domains from other pods with specific labels.
3. **Topology domain consideration**: Considers various levels of topology domains including nodes, zones, and regions.

**Pod affinity and anti-affinity types:**
1. **requiredDuringSchedulingIgnoredDuringExecution**: Rules that must be met for pods to be scheduled (hard requirement).
2. **preferredDuringSchedulingIgnoredDuringExecution**: Rules that are preferred but not required (soft requirement).

**Pod affinity and anti-affinity example:**
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

**Custom InterPodAffinity plugin example:**
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

**Pod affinity and anti-affinity use cases:**
1. **High availability**: Distribute instances of the same application across different nodes, zones, or regions
2. **Performance optimization**: Place pods that communicate with each other on the same node to minimize latency
3. **Resource isolation**: Distribute resource-intensive pods across different nodes
4. **License restrictions**: Concentrate applications with license restrictions on specific nodes

**Performance impact of pod affinity and anti-affinity:**
Pod affinity and anti-affinity can be computationally expensive as they need to consider all nodes and pods. In large clusters, this can impact scheduling performance, so use with caution.

**Issues with other options:**
- A. Process affinity rules between pods and nodes: This is the role of the "NodeAffinity" plugin.
- C. Process affinity rules between pods and volumes: This is the role of the "VolumeBinding" plugin.
- D. Process affinity rules between pods and services: This is not a Kubernetes scheduler plugin.
</details>

### 10. What is the main purpose of the "NodeName" plugin in the Kubernetes scheduler?

A. Verify that the pod's spec.nodeName field matches the node name
B. Assign names to nodes
C. Assign node names to pods
D. Validate node name format

<details>
<summary>Show Answer</summary>

**Answer: A. Verify that the pod's spec.nodeName field matches the node name**

**Explanation:**
The main purpose of the "NodeName" plugin in the Kubernetes scheduler is to verify that the pod's `spec.nodeName` field matches the node name. This plugin checks if a pod has been directly assigned to a specific node, and only passes nodes with matching names through the filtering phase.

**Key functions of the NodeName plugin:**
1. **Node name verification**: If the pod's `spec.nodeName` field is set, only nodes with matching names are selected.
2. **Direct scheduling support**: Allows users to directly assign pods to specific nodes.
3. **Scheduler bypass**: Pods with `spec.nodeName` set bypass normal scheduling logic and are directly assigned to the specified node.

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

**Pod with nodeName specification example:**
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

**Considerations when using nodeName:**
1. **Scheduler bypass**: Using `nodeName` bypasses the scheduler's filtering, scoring, and other logic.
2. **Node existence check**: If the specified node doesn't exist, the pod remains in `Pending` state.
3. **No resource check**: Node resource availability isn't checked, which can lead to failures due to resource shortages.
4. **Ignoring constraints**: Taints, affinity, and other constraints are ignored.

**nodeName vs nodeSelector vs nodeAffinity:**
1. **nodeName**: Directly assigns to a specific node. Most restrictive and least flexible.
2. **nodeSelector**: Selects nodes based on labels. Simple but limited expressiveness.
3. **nodeAffinity**: Supports complex node selection rules. Most flexible and expressive.

**nodeName use cases:**
1. **Debugging**: Run pods on specific nodes for debugging issues.
2. **Testing**: Run tests on specific nodes.
3. **Special hardware**: Assign pods to nodes with specific hardware.
4. **Static pods**: Used for static pods managed directly by kubelet.

**Cautions when using nodeName:**
1. **No automatic recovery**: If a node fails, pods don't automatically move to other nodes.
2. **Limited scalability**: Node names are hardcoded, limiting scalability.
3. **Maintenance difficulty**: Pod definitions need updates if node names change.
4. **No load balancing**: Can't leverage the scheduler's load balancing features.

**Alternatives and recommendations:**
1. **Using nodeSelector**:
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

2. **Using nodeAffinity**:
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

**Issues with other options:**
- B. Assign names to nodes: Node names are assigned at node creation and are not the role of scheduler plugins.
- C. Assign node names to pods: This is performed in the scheduler's binding phase, not by the NodeName plugin.
- D. Validate node name format: This is performed by API server validation logic, not by scheduler plugins.
</details>
