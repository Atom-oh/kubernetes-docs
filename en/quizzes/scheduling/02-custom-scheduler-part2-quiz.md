# Custom Scheduler Quiz (Part 2)

This quiz tests your advanced understanding of implementing and using Custom Schedulers in Kubernetes.

## Quiz Questions

### 1. What is the role of the "Bind" extension point in the Kubernetes scheduling framework?

A. Bind pods to nodes to finalize scheduling decisions
B. Set up network binding between pods and nodes
C. Create binding between pods and services
D. Set up binding between pods and volumes

<details>
<summary>Show Answer</summary>

**Answer: A. Bind pods to nodes to finalize scheduling decisions**

**Explanation:**
The role of the "Bind" extension point in the Kubernetes scheduling framework is to bind pods to selected nodes to finalize scheduling decisions. The binding stage is the final stage of the scheduling cycle, where the pod's `spec.nodeName` field is set so that kubelet can run the pod.

**Binding Process:**
1. The scheduler selects the optimal node through filtering and scoring.
2. Reserves the pod on the selected node (reserve).
3. In the binding stage, updates the pod's `spec.nodeName` field to the name of the selected node.
4. The updated pod information is stored in the API server.
5. kubelet detects the pod information and runs the pod on that node.

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
Common causes of failure at the binding stage:
1. API server connection issues
2. Insufficient permissions
3. Node name errors
4. Race conditions (another scheduler trying to bind the same pod simultaneously)

**Issues with Other Options:**
- B. Set up network binding between pods and nodes: Network setup is the role of CNI plugins and is not related to the scheduler's bind stage.
- C. Create binding between pods and services: The connection between services and pods is made through label selectors and is not related to the scheduler's bind stage.
- D. Set up binding between pods and volumes: Volume binding is handled by the PersistentVolumeClaim controller and is a separate process from the scheduler's bind stage.
</details>

### 2. Which of the following is NOT an operator related to Node Affinity in Kubernetes?

A. In
B. NotIn
C. Exists
D. Contains

<details>
<summary>Show Answer</summary>

**Answer: D. Contains**

**Explanation:**
The operator not related to Node Affinity in Kubernetes is `Contains`. Kubernetes does not provide a `Contains` operator for node affinity.

**Operators Supported in Node Affinity:**
1. **In**: Label value must match one of the specified values.
2. **NotIn**: Label value must not match the specified values.
3. **Exists**: The specified label key must exist.
4. **DoesNotExist**: The specified label key must not exist.
5. **Gt**: Label value must be greater than the specified value (Greater than).
6. **Lt**: Label value must be less than the specified value (Less than).

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
1. **requiredDuringSchedulingIgnoredDuringExecution**: Rules that must be satisfied for the pod to be scheduled on a node (hard requirement).
2. **preferredDuringSchedulingIgnoredDuringExecution**: Rules that are preferred to be satisfied but are not mandatory (soft requirement).

**Operator Usage Examples:**
1. **In Operator**:
   ```yaml
   - key: kubernetes.io/e2e-az-name
     operator: In
     values:
     - e2e-az1
     - e2e-az2
   ```
   The node's `kubernetes.io/e2e-az-name` label value must be `e2e-az1` or `e2e-az2`.

2. **NotIn Operator**:
   ```yaml
   - key: kubernetes.io/e2e-az-name
     operator: NotIn
     values:
     - e2e-az3
   ```
   The node's `kubernetes.io/e2e-az-name` label value must not be `e2e-az3`.

3. **Exists Operator**:
   ```yaml
   - key: kubernetes.io/e2e-az-name
     operator: Exists
   ```
   The `kubernetes.io/e2e-az-name` label must exist on the node.

4. **DoesNotExist Operator**:
   ```yaml
   - key: emptyLabel
     operator: DoesNotExist
   ```
   The `emptyLabel` label must not exist on the node.

5. **Gt/Lt Operators**:
   ```yaml
   - key: node-size
     operator: Gt
     values:
     - "10"
   ```
   The node's `node-size` label value must be greater than 10.

**Handling Node Affinity in Custom Scheduler:**
When implementing a custom scheduler, you should consider the pod's node affinity requirements.

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
- A. In: A valid node affinity operator.
- B. NotIn: A valid node affinity operator.
- C. Exists: A valid node affinity operator.
</details>

### 3. What is the main purpose of Pod Topology Spread Constraints in Kubernetes?

A. Spread pods evenly across various nodes
B. Place pods only on specific nodes
C. Place pods only in specific zones
D. Place pods only on nodes with specific labels

<details>
<summary>Show Answer</summary>

**Answer: A. Spread pods evenly across various nodes**

**Explanation:**
The main purpose of Pod Topology Spread Constraints in Kubernetes is to spread pods evenly across various topology domains (nodes, zones, regions, etc.). This improves application high availability, optimizes resource usage, and improves failure tolerance.

**Main Components of Pod Topology Spread Constraints:**
1. **maxSkew**: Specifies the maximum difference in pod count between topology domains.
2. **topologyKey**: Node label key that defines the topology domain to spread pods across.
3. **whenUnsatisfiable**: Specifies behavior when the constraint cannot be satisfied.
   - `DoNotSchedule`: Do not schedule the pod if the constraint is not met.
   - `ScheduleAnyway`: Schedule the pod even if the constraint is not met.
4. **labelSelector**: Label selector to select existing pods to consider in spread calculation.

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

In this example, two constraints are defined:
1. The difference in pod count with `app=web` label across each node (`kubernetes.io/hostname`) must be at most 1.
2. The difference in pod count with `app=web` label across each zone (`topology.kubernetes.io/zone`) must be at most 2.

**Topology Spread Calculation Method:**
1. Calculate the number of pods matching the label selector in each topology domain.
2. Calculate the difference between the domain with the most pods and the domain with the fewest pods.
3. If this difference is greater than `maxSkew`, the constraint is violated.

**Common Topology Keys:**
1. **kubernetes.io/hostname**: Node-level spread
2. **topology.kubernetes.io/zone**: Zone-level spread
3. **topology.kubernetes.io/region**: Region-level spread
4. **node.kubernetes.io/instance-type**: Instance type-level spread

**Use Cases:**
1. **High availability**: Improve failure tolerance by spreading pods across multiple nodes, zones, regions
2. **Resource balance**: Spread workloads evenly across the cluster
3. **Cost optimization**: Spread workloads across specific types of nodes
4. **Performance optimization**: Spread to minimize network latency

**Handling Topology Spread in Custom Scheduler:**
When implementing a custom scheduler, you should consider the pod's topology spread constraints.

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
- B. Place pods only on specific nodes: This is the role of nodeSelector or nodeAffinity.
- C. Place pods only in specific zones: This is placing pods in specific zones using node affinity; the main purpose of topology spread constraints is even distribution.
- D. Place pods only on nodes with specific labels: This is the role of nodeSelector or nodeAffinity.
</details>
### 4. What is the main purpose of Taints and Tolerations in Kubernetes?

A. Ensure specific pods are scheduled only on specific nodes
B. Prevent specific pods from being scheduled on specific nodes
C. Allow nodes to reject certain pods, and pods to tolerate this
D. Restrict communication between pods

<details>
<summary>Show Answer</summary>

**Answer: C. Allow nodes to reject certain pods, and pods to tolerate this**

**Explanation:**
The main purpose of Taints and Tolerations in Kubernetes is to allow nodes to reject certain pods, and pods to tolerate this. Taints are applied to nodes to prevent pods from being scheduled, and tolerations are applied to pods to allow scheduling on nodes with certain taints.

**How Taints and Tolerations Work:**
1. **Taints**: Applied to nodes to restrict pod scheduling on that node.
2. **Tolerations**: Applied to pods to allow scheduling on nodes with certain taints.
3. **Effect**: The effect of a taint defines the behavior for pods without tolerations.

**Taint Effect Types:**
1. **NoSchedule**: Pods without tolerations are not scheduled on the node.
2. **PreferNoSchedule**: Pods without tolerations are preferably not scheduled on the node, but may be scheduled if cluster resources are insufficient.
3. **NoExecute**: Pods without tolerations are not scheduled on the node, and already running pods are removed.

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
1. **Equal**: Key and value must match.
2. **Exists**: Only the key needs to match (value is ignored).

**Additional Toleration Field:**
- **tolerationSeconds**: Specifies the time (in seconds) that a pod can remain on a node before being removed with NoExecute effect.

```yaml
tolerations:
- key: "node.kubernetes.io/not-ready"
  operator: "Exists"
  effect: "NoExecute"
  tolerationSeconds: 300
```

**Common Use Cases:**
1. **Dedicated nodes**: Reserve nodes for specific workloads only
2. **Special hardware**: Schedule specific pods only on nodes with special hardware like GPUs
3. **Node maintenance**: Prevent new pod scheduling during node maintenance
4. **Master node protection**: Prevent general workloads from scheduling on control plane nodes

**System Taints:**
Kubernetes automatically applies the following system taints:
1. **node.kubernetes.io/not-ready**: Node is not ready
2. **node.kubernetes.io/unreachable**: Node is unreachable
3. **node.kubernetes.io/memory-pressure**: Node has memory pressure
4. **node.kubernetes.io/disk-pressure**: Node has disk pressure
5. **node.kubernetes.io/pid-pressure**: Node has PID pressure
6. **node.kubernetes.io/network-unavailable**: Node's network is unavailable
7. **node.kubernetes.io/unschedulable**: Node is marked as unschedulable

**Handling Taints and Tolerations in Custom Scheduler:**
When implementing a custom scheduler, you should consider node taints and pod tolerations.

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
- A. Ensure specific pods are scheduled only on specific nodes: This is the role of nodeSelector or nodeAffinity.
- B. Prevent specific pods from being scheduled on specific nodes: This is the role of podAntiAffinity.
- D. Restrict communication between pods: This is the role of NetworkPolicy.
</details>

### 5. Which of the following is NOT a main characteristic of Scheduler Extender in Kubernetes?

A. Communicates with the scheduler through HTTP webhooks
B. Provides filtering and prioritization capabilities
C. Directly integrated with the scheduler codebase
D. Runs as an external process

<details>
<summary>Show Answer</summary>

**Answer: C. Directly integrated with the scheduler codebase**

**Explanation:**
"Directly integrated with the scheduler codebase" is NOT a main characteristic of Scheduler Extender in Kubernetes. Scheduler extenders are not directly integrated with the scheduler codebase; they communicate through HTTP webhooks and run as external processes. This is the main difference from scheduling framework plugins.

**Main Characteristics of Scheduler Extender:**
1. **HTTP webhooks**: The scheduler communicates with extenders through HTTP requests.
2. **External process**: Extenders run as separate processes from the scheduler.
3. **Filtering and prioritization**: Extenders can provide node filtering and prioritization capabilities.
4. **Binding**: Extenders can optionally bind pods to nodes.

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
1. **Filter API**: Receives a node list and returns a filtered node list.
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

2. **Prioritize API**: Receives a node list and assigns a score to each node.
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

3. **Bind API**: Binds the pod to the node.
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
- Can be developed independently of the scheduler codebase
- Can be implemented in various programming languages
- Less affected by scheduler upgrades

Cons:
- Performance degradation due to HTTP communication overhead
- Can only extend some stages of the scheduling cycle
- Possibility of communication failure between scheduler and extender

**Explanation of Other Options:**
- A. Communicates with the scheduler through HTTP webhooks: A valid characteristic of scheduler extender.
- B. Provides filtering and prioritization capabilities: A valid characteristic of scheduler extender.
- D. Runs as an external process: A valid characteristic of scheduler extender.
</details>
### 6. What is the main purpose of Pod Affinity and Anti-Affinity in Kubernetes?

A. Define relationships between pods and nodes
B. Define relationships between pods and volumes
C. Define relationships between pods
D. Define relationships between pods and services

<details>
<summary>Show Answer</summary>

**Answer: C. Define relationships between pods**

**Explanation:**
The main purpose of Pod Affinity and Anti-Affinity in Kubernetes is to define relationships between pods. This allows controlling whether specific pods are placed in the same topology domain (node, zone, region, etc.) as other pods (affinity) or not (anti-affinity).

**Main Components of Pod Affinity and Anti-Affinity:**
1. **topologyKey**: Node label key that specifies the topology domain defining relationships between pods.
2. **labelSelector**: Label selector to select pods to establish relationships with.
3. **namespaces**: List of namespaces where the label selector applies.

**Pod Affinity Types:**
1. **requiredDuringSchedulingIgnoredDuringExecution**: Rules that must be satisfied for the pod to be scheduled (hard requirement).
2. **preferredDuringSchedulingIgnoredDuringExecution**: Rules that are preferred to be satisfied but not mandatory (soft requirement).

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

In this example:
1. **Pod Affinity**: The web server pod must be scheduled on the same node (`kubernetes.io/hostname`) as pods with the `app=cache` label.
2. **Pod Anti-Affinity**: The web server pod preferably should be scheduled on a different node from other pods with the `app=web` label.

**Common Topology Keys:**
1. **kubernetes.io/hostname**: Node-level relationship
2. **topology.kubernetes.io/zone**: Zone-level relationship
3. **topology.kubernetes.io/region**: Region-level relationship

**Use Cases:**
1. **High availability**: Spread instances of the same application across different nodes, zones, regions
2. **Performance optimization**: Place pods that communicate with each other on the same node to minimize latency
3. **Resource isolation**: Spread resource-intensive pods across different nodes
4. **License restrictions**: Concentrate applications with license restrictions on specific nodes

**Pod Affinity vs Node Affinity:**
- **Node Affinity**: Defines relationships between pods and nodes.
- **Pod Affinity**: Defines relationships between pods.

**Performance Impact of Pod Affinity and Anti-Affinity:**
Pod affinity and anti-affinity can be computationally expensive as they need to consider all nodes and pods. Especially in large clusters, they can affect scheduling performance, so they should be used carefully.

**Handling Pod Affinity in Custom Scheduler:**
When implementing a custom scheduler, you should consider the pod's affinity and anti-affinity requirements.

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
- A. Define relationships between pods and nodes: This is the role of nodeAffinity.
- B. Define relationships between pods and volumes: This is the role of volume binding and PersistentVolumeClaim.
- D. Define relationships between pods and services: This is handled through service label selectors.
</details>

### 7. What is the role of the "QueueSort" extension point in the Kubernetes scheduler?

A. Score nodes
B. Exclude nodes where pods cannot run
C. Sort pods in the scheduling queue
D. Bind pods to nodes

<details>
<summary>Show Answer</summary>

**Answer: C. Sort pods in the scheduling queue**

**Explanation:**
The role of the "QueueSort" extension point in the Kubernetes scheduling framework is to sort pods in the scheduling queue. This extension point sets the priority that determines which pods are scheduled first.

**Scheduling Queue and QueueSort:**
The scheduler processes pods in the scheduling queue one by one. The QueueSort plugin determines the order of pods in this queue. By default, Kubernetes uses the `PrioritySort` plugin to sort by pod priority.

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
1. **Single activation**: Only one QueueSort plugin can be active at a time.
2. **Global impact**: The QueueSort plugin affects all pods in the scheduling queue.
3. **Performance importance**: An efficient sorting algorithm is important; complex logic can affect scheduling performance.

**QueueSort Plugin Use Cases:**
1. **Business priority**: Sort pods by business importance
2. **Resource efficiency**: Schedule pods with smaller resource requests first to utilize empty space
3. **Service Level Agreements (SLA)**: Sort pods according to SLA requirements
4. **Batch processing**: Adjust priority between batch jobs and interactive jobs

**Monitoring Scheduling Queue:**
```bash
# Check queue information in scheduler logs
kubectl logs -n kube-system <scheduler-pod> | grep -i queue

# Check pods pending scheduling
kubectl get pods --all-namespaces -o wide | grep -i pending
```

**Issues with Other Options:**
- A. Score nodes: This is the role of the "Score" extension point.
- B. Exclude nodes where pods cannot run: This is the role of the "Filter" extension point.
- D. Bind pods to nodes: This is the role of the "Bind" extension point.
</details>
### 8. What is the main purpose of Pod Priority Preemption in Kubernetes?

A. Remove lower priority pods so that higher priority pods can be scheduled
B. Allocate more resources to higher priority pods
C. Run higher priority pods faster
D. Place higher priority pods only on specific nodes

<details>
<summary>Show Answer</summary>

**Answer: A. Remove lower priority pods so that higher priority pods can be scheduled**

**Explanation:**
The main purpose of Pod Priority Preemption in Kubernetes is to remove lower priority pods so that higher priority pods can be scheduled. When cluster resources are insufficient and higher priority pods cannot be scheduled, the scheduler preempts (removes) lower priority pods to free up space.

**Pod Priority and Preemption Mechanism:**
1. **PriorityClass definition**: A cluster-level resource that defines pod priority.
2. **Assign priority to pod**: Pods reference a PriorityClass through `spec.priorityClassName`.
3. **Scheduling order**: Higher priority pods are processed first in the scheduling queue.
4. **Preemption process**: When higher priority pods cannot be scheduled, the scheduler removes lower priority pods to free up space.

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
PriorityClass has a `preemptionPolicy` field that can have the following values:
1. **PreemptLowerPriority (default)**: Can preempt lower priority pods.
2. **Never**: Does not preempt lower priority pods.

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
1. The scheduler attempts to schedule a higher priority pod.
2. If there is no suitable node, the scheduler identifies preemption candidate pods on each node.
3. Preemption candidates are selected from lower priority pods.
4. The scheduler preempts the minimum number of pods to free up required resources.
5. Selected pods are gracefully terminated.
6. Once preempted pods are terminated, the higher priority pod is scheduled.

**Preemption Considerations:**
1. **Graceful termination period**: Preempted pods have a graceful termination time of `terminationGracePeriodSeconds` (default: 30 seconds).
2. **Pod Disruption Budget (PDB)**: The scheduler tries not to violate PDBs when possible.
3. **Node taints**: After preemption, taints may be added to the node to prevent new pods from being scheduled.
4. **System pods**: System critical pods typically have very high priority and are not preempted.

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
When implementing a custom scheduler, you should consider pod priority and preemption mechanisms.

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
- Guarantees scheduling of important workloads
- Efficient use of cluster resources
- Supports Service Level Agreement (SLA) compliance

Cons:
- Disruption of preempted pods
- Overhead from rescheduling after preemption
- Complex preemption decision logic

**Issues with Other Options:**
- B. Allocate more resources to higher priority pods: Pod priority does not directly affect resource allocation. Resource requests and limits are defined separately in the pod spec.
- C. Run higher priority pods faster: Priority affects scheduling order, but does not change pod execution speed itself.
- D. Place higher priority pods only on specific nodes: This is the role of nodeSelector or nodeAffinity and is not directly related to priority.
</details>

### 9. What is the role of the "PreFilter" extension point in the Kubernetes scheduler?

A. Perform preprocessing on pod and cluster state before filtering
B. Score nodes after filtering
C. Perform verification before binding pods to nodes
D. Sort pods in the scheduling queue

<details>
<summary>Show Answer</summary>

**Answer: A. Perform preprocessing on pod and cluster state before filtering**

**Explanation:**
The role of the "PreFilter" extension point in the Kubernetes scheduling framework is to perform preprocessing on pod and cluster state before filtering. PreFilter plugins prepare data to be used in the filtering stage and can pre-check whether pods can be scheduled.

**Main Functions of the PreFilter Extension Point:**
1. **Data preparation**: Initialize and prepare data structures to be used in the filtering stage.
2. **Pre-checks**: Pre-check whether pods can be scheduled.
3. **State storage**: Store state information to be used during the scheduling cycle.
4. **Optimization**: Prevent unnecessary filtering work to optimize performance.

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
Kubernetes provides the following default PreFilter plugins:

1. **InterPodAffinity**: Handles inter-pod affinity and anti-affinity requirements.
2. **NodeAffinity**: Handles node affinity requirements.
3. **NodePorts**: Handles host ports requested by pods.
4. **NodeResourcesFit**: Handles node resource requirements.
5. **PodTopologySpread**: Handles pod topology spread constraints.
6. **VolumeBinding**: Handles volume binding requirements.

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
1. **PreFilter**: Runs once before starting filtering for all nodes.
2. **Filter**: Runs individually for each node.

PreFilter prepares data to be used in the Filter stage and pre-identifies cases where pods cannot be scheduled on any node to prevent unnecessary filtering work.

**PreFilter Use Cases:**
1. **Complex constraint handling**: Efficiently handle complex constraints like inter-pod affinity, topology spread
2. **Pre-validation**: Pre-check whether pods can be scheduled to prevent unnecessary processing
3. **Data caching**: Pre-calculate data that is repeatedly used in the filtering stage to improve performance
4. **State sharing**: Manage state information shared between multiple plugins

**Issues with Other Options:**
- B. Score nodes after filtering: This is the role of the "Score" extension point.
- C. Perform verification before binding pods to nodes: This is the role of the "PreBind" extension point.
- D. Sort pods in the scheduling queue: This is the role of the "QueueSort" extension point.
</details>

### 10. What does the node taint `node.kubernetes.io/unreachable:NoExecute` mean in Kubernetes?

A. The node is unreachable and pods without tolerations are removed
B. The node is unschedulable but existing pods continue to run
C. The node is in maintenance mode and new pods are not scheduled
D. The node is in resource shortage state and new pods are preferably not scheduled

<details>
<summary>Show Answer</summary>

**Answer: A. The node is unreachable and pods without tolerations are removed**

**Explanation:**
The node taint `node.kubernetes.io/unreachable:NoExecute` in Kubernetes means that the node is unreachable and pods without tolerations for this taint are removed (evicted) from the node. This taint is automatically added by the node controller and is applied when the node's status changes from `Ready` to `Unknown`.

**Node Unreachable State:**
Common causes for a node becoming unreachable:
1. Network connectivity issues
2. kubelet process crash
3. Node system failure
4. Node power issues

**Taint Components:**
1. **Key**: `node.kubernetes.io/unreachable`
2. **Value**: Usually an empty string, but may have a value.
3. **Effect**: `NoExecute` - Pods without tolerations are removed from the node.

**NoExecute Effect:**
The `NoExecute` effect causes the following behavior:
1. New pods are not scheduled on nodes with the taint.
2. Among pods already running on the node, those without tolerations for the taint are removed.

**System Taints:**
Kubernetes automatically adds the following system taints based on node status:
1. **node.kubernetes.io/not-ready:NoExecute**: Node is not ready
2. **node.kubernetes.io/unreachable:NoExecute**: Node is unreachable
3. **node.kubernetes.io/memory-pressure:NoSchedule**: Node has memory pressure
4. **node.kubernetes.io/disk-pressure:NoSchedule**: Node has disk pressure
5. **node.kubernetes.io/pid-pressure:NoSchedule**: Node has PID pressure
6. **node.kubernetes.io/network-unavailable:NoSchedule**: Node's network is unavailable
7. **node.kubernetes.io/unschedulable:NoSchedule**: Node is marked as unschedulable

**Default Tolerations:**
Kubernetes automatically adds the following default tolerations to all pods:
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

These default tolerations allow pods to remain on the node for 5 minutes (300 seconds) when the node becomes not ready or unreachable, preventing unnecessary pod rescheduling due to temporary network issues.

**Custom Tolerations:**
For critical workloads, you can set longer toleration times:
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
The node controller controls node status changes and taint application behavior through the following settings:
1. **--node-monitor-period**: Period to check node status (default: 5 seconds)
2. **--node-monitor-grace-period**: Wait time before marking a node as `Unknown` (default: 40 seconds)
3. **--pod-eviction-timeout**: Wait time before removing pods from `Unknown` or `NotReady` nodes (default: 5 minutes)

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
When implementing a custom scheduler, you should consider node taints and pod tolerations.

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
- B. The node is unschedulable but existing pods continue to run: This is the behavior of the `NoSchedule` effect; the `NoExecute` effect also removes existing pods without tolerations.
- C. The node is in maintenance mode and new pods are not scheduled: This is typically the behavior of the `node.kubernetes.io/unschedulable:NoSchedule` taint.
- D. The node is in resource shortage state and new pods are preferably not scheduled: This is the behavior of the `PreferNoSchedule` effect, and resource shortage is typically indicated by `node.kubernetes.io/memory-pressure` or `node.kubernetes.io/disk-pressure` taints.
</details>
