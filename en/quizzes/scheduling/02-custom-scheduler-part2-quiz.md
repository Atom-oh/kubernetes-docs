# Custom Scheduler Quiz (Part 2)

> **Example Baseline**: Kubernetes 1.35.8, Go 1.27.1
> **Last Updated**: September 11, 2026

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
The role of the "Bind" extension point in the Kubernetes scheduling framework is to bind pods to selected nodes to finalize scheduling decisions. The Bind stage commits the assignment during the binding cycle; PostBind follows it, and kubelet may still encounter image, storage or runtime failures.

**Binding Process:**
1. The scheduler selects the optimal node through filtering and scoring.
2. Reserves the pod on the selected node (reserve).
3. In the binding stage, updates the pod's `spec.nodeName` field to the name of the selected node.
4. The updated pod information is stored in the API server.
5. kubelet detects the pod information and runs the pod on that node.

**Binding Request Example:**
Binding happens in the binding cycle after node selection, assumption/reservation, Permit and PreBind. It records an assignment, not successful container startup. Keep the upstream `DefaultBinder`, which also handles the target version's API-cache path and binding errors. This complete helper demonstrates the request identity without sending it:

```go
package bindingexample

import (
	"fmt"

	v1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
)

// This only constructs a request; it neither selects a node nor calls the API.
// Use DefaultBinder within the complete scheduler pipeline for actual binding.
func BindingFor(pod *v1.Pod, nodeName string) (*v1.Binding, error) {
	if pod == nil || pod.Name == "" || pod.Namespace == "" || pod.UID == "" || nodeName == "" {
		return nil, fmt.Errorf("admitted Pod name, namespace, UID and selected node are required")
	}
	return &v1.Binding{
		ObjectMeta: metav1.ObjectMeta{Name: pod.Name, Namespace: pod.Namespace, UID: pod.UID},
		Target:     v1.ObjectReference{Kind: "Node", Name: nodeName},
	}, nil
}
```

The Pod UID protects against confusing a deleted Pod with a new Pod of the same name. A binding request does not itself check resources, affinity or taints; those checks belong earlier in the complete scheduler pipeline.

**Default Binder Configuration:**
The following retains all defaults, including `DefaultBinder`; it does not enable an unregistered custom binder.

```yaml
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
leaderElection:
  leaderElect: true
  resourceLock: leases
  resourceName: custom-scheduler
  resourceNamespace: scheduler-lab
  leaseDuration: 15s
  renewDeadline: 10s
  retryPeriod: 2s
profiles:
- schedulerName: custom-scheduler
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
- D. Set up binding between pods and volumes: PV/PVC binding and CSI provisioning also involve storage controllers and the scheduler’s VolumeBinding plugin, including delayed binding. Pod-to-node Bind is a distinct operation.
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
          - key: topology.kubernetes.io/zone
            operator: In
            values: [us-east-1a, us-east-1b]
      preferredDuringSchedulingIgnoredDuringExecution:
      - weight: 1
        preference:
          matchExpressions:
          - key: another-node-label-key
            operator: Exists
  containers:
  - name: nginx
    image: nginx:1.30.4
```

**Node Affinity Types:**
1. **requiredDuringSchedulingIgnoredDuringExecution**: Rules that must be satisfied for the pod to be scheduled on a node (hard requirement).
2. **preferredDuringSchedulingIgnoredDuringExecution**: Rules that are preferred to be satisfied but are not mandatory (soft requirement).

**Operator Usage Examples:**
1. **In Operator**:
   ```yaml
   - key: topology.kubernetes.io/zone
     operator: In
     values:
     - us-east-1a
     - us-east-1b
   ```
   The node's `topology.kubernetes.io/zone` label value must be `us-east-1a` or `us-east-1b`.

2. **NotIn Operator**:
   ```yaml
   - key: topology.kubernetes.io/zone
     operator: NotIn
     values:
     - us-east-1c
   ```
   The node's `topology.kubernetes.io/zone` label value must not be `us-east-1c`.

3. **Exists Operator**:
   ```yaml
   - key: topology.kubernetes.io/zone
     operator: Exists
   ```
   The `topology.kubernetes.io/zone` label must exist on the node.

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

**Checking Required Node Affinity:**
Keep the default `NodeAffinity` plugin. For a read-only helper, use the versioned component helper rather than a `matchNodeSelectorTerm` stub returning true.

```go
package affinityexample

import (
	"fmt"

	v1 "k8s.io/api/core/v1"
	nodeaffinity "k8s.io/component-helpers/scheduling/corev1/nodeaffinity"
)

// A read-only check of Pod nodeSelector and required node affinity.
// The scheduler's NodeAffinity plugin also handles profile-level addedAffinity.
func MatchesRequired(pod *v1.Pod, node *v1.Node) (bool, error) {
	if pod == nil || node == nil {
		return false, fmt.Errorf("pod and node are required")
	}
	return nodeaffinity.GetRequiredNodeAffinity(pod).Match(node)
}
```

`nodeSelector` and required node affinity must both match. Selector terms are ORed; expressions within one term are ANDed, and an empty term matches no nodes. `NotIn` also matches an absent key; add `Exists` if presence is required. `Gt`/`Lt` require exactly one integer comparison value and an integer node-label value. `IgnoredDuringExecution` means later label changes do not themselves evict a bound Pod. Profile-level `addedAffinity` remains the scheduler plugin's responsibility.

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
Topology spread constrains placement of each incoming Pod across eligible domains. It can improve fault tolerance, but does not rebalance existing Pods or guarantee latency, capacity or availability.

**Main Fields:**
1. **maxSkew**: With `DoNotSchedule`, bounds the incoming Pod's candidate-domain count relative to the eligible global minimum.
2. **topologyKey**: Node label defining a domain.
3. **whenUnsatisfiable**: `DoNotSchedule` is a hard constraint; `ScheduleAnyway` is a scoring preference and does not bypass other hard filters.
4. **labelSelector**: Selects counted Pods in the incoming Pod's namespace. Ensure the incoming Pod matches the intended selector.
5. **minDomains / nodeAffinityPolicy / nodeTaintsPolicy**: Influence eligible-domain counting. They do not create missing nodes or AZ capacity.

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
    image: nginx:1.30.4
```

In the example, both constraints must be satisfied for the candidate placement. For `DoNotSchedule`, calculate:

1. Count matching Pods in every eligible domain, including empty domains.
2. Find the eligible global minimum; it is zero if fewer domains exist than `minDomains`.
3. Include the incoming Pod in its candidate domain if it matches the selector, then compare that candidate count with the minimum.

For counts **2,2,1** and `maxSkew: 1`, another matching Pod can enter the third domain (2−1=1), but not either of the first two (3−1=2). This checks candidate placement, not a promise that every existing domain pair is always balanced.

**Common Topology Keys:**
1. **kubernetes.io/hostname**: Node-level spread
2. **topology.kubernetes.io/zone**: Zone-level spread
3. **topology.kubernetes.io/region**: Region-level spread
4. **node.kubernetes.io/instance-type**: Instance type-level spread

**Use Cases:**
1. **High availability**: Improve failure tolerance by spreading pods across multiple nodes, zones, regions
2. **Resource balance**: Spread workloads evenly across the cluster
3. **Cost optimization**: Spread workloads across specific types of nodes
4. **Topology policy**: Balance fault tolerance against cross-domain traffic and measured latency

**Custom Scheduler Handling:**
Retain `PodTopologySpread` and its PreFilter/Filter/Score stages. Correct handling requires the scheduler snapshot, namespace/selector matching, eligible and empty domains, the incoming Pod, `minDomains`, node affinity/taint policies and requeue events. A loop over Running Pods with omitted skew logic is not an implementation.

This EKS lab uses EC2 nodes in one AWS Region; a `topology.kubernetes.io/region` label does not turn it into a multi-region cluster. Spreading across AZs can increase cross-AZ traffic; it does not inherently minimize network latency.

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
Taints repel Pods; tolerations allow a matching taint to be ignored. A toleration does not force placement on that node or bypass resource/affinity filters.

**Effects:**
1. **NoSchedule**: An untolerated taint blocks new scheduling but does not evict existing Pods.
2. **PreferNoSchedule**: A soft preference; other scores can outweigh it even when capacity exists elsewhere.
3. **NoExecute**: Blocks new scheduling without a matching toleration and triggers eviction handling for existing Pods without one, or after their toleration expires. API deletion does not prove a process on an unreachable node has stopped.

**Taint Application Example:**
```bash
# Apply taint to node
kubectl taint nodes node1 key=value:NoSchedule

# Remove taint from node
kubectl taint nodes node1 key=value:NoSchedule-
```

**Taint and Toleration Example:**
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: pod-with-toleration
spec:
  tolerations:
  - key: key
    operator: Equal
    value: value
    effect: NoSchedule
  containers:
  - name: nginx
    image: nginx:1.30.4
```

**Toleration Fields:**
* `Equal` (the default operator) compares key/value. `Exists` must omit the value.
* A specified effect must match; an empty effect matches all effects for that key. An empty key requires `Exists` and matches all keys, so use it deliberately.
* `tolerationSeconds` applies only to `NoExecute`. Omitting it tolerates that matching taint indefinitely; specifying it bounds the tolerated period.
* This example uses the default `Equal`/`Exists` behavior. Kubernetes1.35's optional comparison-operator feature is alpha and disabled here.

```yaml
tolerations:
- key: "node.kubernetes.io/not-ready"
  operator: "Exists"
  effect: "NoExecute"
  tolerationSeconds: 300
```

**Common Use Cases:**
1. **Dedicated nodes**: Combine taints, controlled tolerations and required affinity; taints alone do not force those workloads onto the dedicated nodes
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

**Checking Hard Taints:**
This complete helper uses the pinned matching semantics, including effect/wildcard handling. It excludes `PreferNoSchedule` from the hard check and includes `NoExecute`. It does not replace the scheduler's other filters or the taint-eviction controller.

```go
package taintexample

import (
    v1 "k8s.io/api/core/v1"
    corehelpers "k8s.io/component-helpers/scheduling/corev1"
    "k8s.io/klog/v2"
)

// Checks hard scheduling taints only; it does not implement eviction timers.
func ToleratesHardTaints(pod *v1.Pod, node *v1.Node) bool {
	if pod == nil || node == nil {
		return false
	}
	_, untolerated := corehelpers.FindMatchingUntoleratedTaint(
		klog.Background(), node.Spec.Taints, pod.Spec.Tolerations,
		func(taint *v1.Taint) bool {
			return taint.Effect == v1.TaintEffectNoSchedule || taint.Effect == v1.TaintEffectNoExecute
		}, false, // Equal/Exists behavior; comparison-operator feature is not enabled here.
	)
	return !untolerated
}
```

**Issues with Other Options:**
- A. Ensure specific pods are scheduled only on specific nodes: This is the role of nodeSelector or nodeAffinity.
- B. Prevent specific pods from being scheduled on specific nodes: This describes only the repelling half of taints/tolerations; podAntiAffinity instead relates placement to other Pods.
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

**Extender Configuration:**
Use the Part2 TLS service and certificate prerequisites with the secondary scheduler. `extenders` is top-level. Keep `ignorable: false` for a required filter; do not combine a failure-tolerant extender with `ignoredByScheduler: true` for resources whose availability must be enforced. The example leaves all GPU accounting to the built-in resource filter.

```yaml
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
leaderElection:
  leaderElect: true
  resourceLock: leases
  resourceName: custom-scheduler
  resourceNamespace: scheduler-lab
  leaseDuration: 15s
  renewDeadline: 10s
  retryPeriod: 2s
profiles:
- schedulerName: custom-scheduler
extenders:
- urlPrefix: https://scheduler-extender.scheduler-lab.svc:8443
  filterVerb: filter
  prioritizeVerb: prioritize
  weight: 1
  enableHTTPS: true
  tlsConfig:
    caFile: /etc/extender-client/ca.crt
    certFile: /etc/extender-client/tls.crt
    keyFile: /etc/extender-client/tls.key
  httpTimeout: 2s
  nodeCacheCapable: false
  ignorable: false
```

**Wire Protocol (Kubernetes 1.35.8):**
The Go types serialize capitalized field names. With `nodeCacheCapable: false`, send `Pod` and full `Nodes`; `NodeNames` is null. With it true, a separately maintained node cache and `NodeNames` contract are required. The following are valid JSON examples, not literal angle-bracket placeholders.

1. **Filter / prioritize request**:

```json
{
  "Pod": {
    "apiVersion": "v1",
    "kind": "Pod",
    "metadata": {
      "name": "gpu-pod",
      "namespace": "default",
      "uid": "00000000-0000-0000-0000-000000000001",
      "annotations": {
        "training.example.com/min-gpu-memory-mib": "16384"
      }
    },
    "spec": {
      "schedulerName": "custom-scheduler",
      "containers": [
        {
          "name": "worker",
          "image": "busybox:1.37.0",
          "resources": {
            "requests": {
              "nvidia.com/gpu": "1"
            },
            "limits": {
              "nvidia.com/gpu": "1"
            }
          }
        }
      ]
    }
  },
  "Nodes": {
    "items": [
      {
        "metadata": {
          "name": "gpu-node",
          "labels": {
            "training.example.com/gpu-memory-mib": "16384"
          }
        },
        "status": {
          "allocatable": {
            "nvidia.com/gpu": "1"
          }
        }
      }
    ]
  },
  "NodeNames": null
}
```

2. **Filter response**: only supplied candidate nodes may be returned. `FailedAndUnresolvableNodes` identifies failures that preemption cannot fix.

```json
{
  "Nodes": {
    "items": [
      {
        "metadata": {
          "name": "gpu-node",
          "labels": {
            "training.example.com/gpu-memory-mib": "16384"
          }
        },
        "status": {
          "allocatable": {
            "nvidia.com/gpu": "1"
          }
        }
      }
    ]
  },
  "NodeNames": null,
  "FailedNodes": {},
  "FailedAndUnresolvableNodes": {},
  "Error": ""
}
```

3. **Prioritize response**: a bare array of `Host`/`Score`, with scores from **0 to 10**. Framework scores use 0–100. A priority error causes this extender's scores to be omitted; mandatory rules therefore belong in Filter.

```json
[
  {
    "Host": "gpu-node",
    "Score": 2
  }
]
```

4. **Optional bind request and response**: the request identifies a Pod by name, namespace and UID plus the chosen node. Part2 does not implement this callback and leaves `bindVerb` unset.

```json
{
  "PodName": "gpu-pod",
  "PodNamespace": "default",
  "PodUID": "00000000-0000-0000-0000-000000000001",
  "Node": "gpu-node"
}
```

```json
{
  "Error": ""
}
```

5. **Optional preemption callback**: `preemptVerb` exchanges the Pod and candidate victims using `ExtenderPreemptionArgs`/`ExtenderPreemptionResult`. It is not a PreFilter or PreScore callback.

**Implementation:**
Use the complete bounded-input handler and TLS command in [Part2](../../scheduling/02-custom-scheduler-part2.md). They reject missing Pods/nodes, malformed memory requirements, oversized input and the wrong cache contract; no unimplemented `customFilter` or `customScore` function is treated as executable code.

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
    image: nginx:1.30.4
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
2. **Locality preference**: Co-location may reduce some network costs; measure contention and latency before relying on it
3. **Resource isolation**: Spread resource-intensive pods across different nodes
4. **License restrictions**: Concentrate applications with license restrictions on specific nodes

**Pod Affinity vs Node Affinity:**
- **Node Affinity**: Defines relationships between pods and nodes.
- **Pod Affinity**: Defines relationships between pods.

**Performance Impact of Pod Affinity and Anti-Affinity:**
Pod affinity and anti-affinity can be computationally expensive as they need to consider all nodes and pods. Especially in large clusters, they can affect scheduling performance, so they should be used carefully.

**Custom Scheduler Handling:**
Keep `InterPodAffinity`, including its preprocessing and scoring. It must account for the incoming Pod's required terms, existing Pods' required anti-affinity, namespace selection, topology labels and self-affinity bootstrap behavior. A stub that always returns true can allow invalid placement or reject every node when inverted for anti-affinity.

`namespaces` and `namespaceSelector` select a union of namespaces; when both are omitted, use the incoming Pod's namespace. `namespaceSelector: {}` selects all namespaces. In the example, the required `app=cache` Pod must already be present in the selected namespace on an eligible node. Preferred anti-affinity does not guarantee separation. `IgnoredDuringExecution` does not continuously relocate Pods as labels or peers change.

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

**Versioned Interface:**
In Kubernetes 1.35.8, QueueSort implements `Less(fwk.QueuedPodInfo, fwk.QueuedPodInfo) bool`; these are interfaces accessed through getters. The default `PrioritySort` compares admitted priority, then queue timestamp.

**Complete Custom Example (`quizplugins/queue.go`):**
This preserves admitted priority before applying lab tie-breakers. Namespace/label preferences can cause unfairness among equal-priority Pods; do not let untrusted labels substitute for an admission-controlled PriorityClass.

```go
package quizplugins

import (
	"context"

	v1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/runtime"
	corehelpers "k8s.io/component-helpers/scheduling/corev1"
	fwk "k8s.io/kube-scheduler/framework"
)

type CustomQueueSort struct{}

var _ fwk.QueueSortPlugin = &CustomQueueSort{}

func (*CustomQueueSort) Name() string { return "CustomQueueSort" }

func (*CustomQueueSort) Less(a, b fwk.QueuedPodInfo) bool {
	pa, pb := a.GetPodInfo().GetPod(), b.GetPodInfo().GetPod()
	ap, bp := corehelpers.PodPriority(pa), corehelpers.PodPriority(pb)
	if ap != bp {
		return ap > bp
	}
	// Lab tie-breakers only; do not override the admitted Pod priority.
	aPreferred := pa.Namespace == "high-priority-namespace"
	bPreferred := pb.Namespace == "high-priority-namespace"
	if aPreferred != bPreferred {
		return aPreferred
	}
	if critical(pa) != critical(pb) {
		return critical(pa)
	}
	return a.GetTimestamp().Before(b.GetTimestamp())
}

func critical(pod *v1.Pod) bool { return pod.Labels["training.example.com/critical"] == "true" }

func NewQueue(_ context.Context, _ runtime.Object, _ fwk.Handle) (fwk.Plugin, error) {
	return &CustomQueueSort{}, nil
}
```

Register it together with the later PoolConstraint example using `cmd/quiz-scheduler/main.go`:

```go
package main

import (
	"os"

	"example.com/custom-scheduler/quizplugins"
	"k8s.io/component-base/cli"
	"k8s.io/kubernetes/cmd/kube-scheduler/app"
)

func main() {
	command := app.NewSchedulerCommand(
		app.WithPlugin("CustomQueueSort", quizplugins.NewQueue),
		app.WithPlugin("PoolConstraint", quizplugins.NewPool),
	)
	os.Exit(cli.Run(command))
}
```

Build with the Part1 module: `CGO_ENABLED=0 go build -buildvcs=false -o custom-scheduler ./cmd/quiz-scheduler`. Enable only the plugins needed in the chosen configuration.

**Enabling QueueSort Plugin in Scheduler Configuration:**
```yaml
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
leaderElection:
  leaderElect: true
  resourceLock: leases
  resourceName: custom-scheduler
  resourceNamespace: scheduler-lab
  leaseDuration: 15s
  renewDeadline: 10s
  retryPeriod: 2s
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
2. **Shared queue**: All profiles in one scheduler process must use the same QueueSort plugin and configuration. Other scheduler processes have separate queues.
3. **Performance importance**: An efficient sorting algorithm is important; complex logic can affect scheduling performance.

**QueueSort Plugin Use Cases:**
1. **Business priority**: Sort pods by business importance
2. **Resource efficiency**: Schedule pods with smaller resource requests first to utilize empty space
3. **Service Level Agreements (SLA)**: Sort pods according to SLA requirements
4. **Batch processing**: Adjust priority between batch jobs and interactive jobs

**Monitoring Scheduling Queue:**
```bash
# Check queue information in scheduler logs
kubectl logs -n scheduler-lab -l app=custom-scheduler --prefix --tail=100

# Check pods pending scheduling
kubectl get pods -A --field-selector=spec.schedulerName=custom-scheduler,spec.nodeName= -o wide
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
The main purpose of Pod Priority Preemption in Kubernetes is to remove lower priority pods so that higher priority pods can be scheduled. When a higher-priority Pod cannot fit, the scheduler may preempt lower-priority Pods if doing so can satisfy the relevant constraints.

**Pod Priority and Preemption Mechanism:**
1. **PriorityClass definition**: A cluster-level resource that defines pod priority.
2. **Assign priority to pod**: Pods reference a PriorityClass through `spec.priorityClassName`.
3. **Scheduling order**: Higher priority pods are processed first in the scheduling queue.
4. **Preemption process**: The scheduler may remove lower-priority Pods when the Pod’s policy allows it and the remaining constraints can be satisfied.

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
    image: nginx:1.30.4
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
4. The scheduler chooses a candidate/victim set using its policy; it does not guarantee global minimum cardinality.
5. Selected pods are gracefully terminated.
6. After victims terminate, scheduling is retried; nomination does not guarantee binding.

**Preemption Considerations:**
1. **Graceful termination period**: Preempted pods have a graceful termination time of `terminationGracePeriodSeconds` (default: 30 seconds).
2. **Pod Disruption Budget (PDB)**: Preemption tries to avoid PDB violations, but PDB compliance is best effort and not guaranteed.
3. **Nomination**: `status.nominatedNodeName` records a possible target. Preemption does not reserve it by adding a node taint.
4. **System Pods**: Critical PriorityClasses have high reserved priorities; this is not immunity from every higher-priority Pod or other eviction mechanism.

**Checking Preemption Events:**
```bash
# Check preemption events
kubectl get events | grep -i preempt
```

**Monitoring Preemption-Related Metrics:**
Read `scheduler_preemption_attempts_total` from the **custom scheduler's** authenticated HTTPS metrics endpoint through your configured monitoring system. `kubectl get --raw /metrics` reads API-server metrics and is not this endpoint.

```bash
kubectl get pods -A -o custom-columns=NAME:.metadata.name,PRIORITY:.spec.priority,NOMINATED:.status.nominatedNodeName
```

**Safe Preemption Handling:**
Keep `DefaultPreemption` in PostFilter. It simulates removal of lower-priority Pods and reruns the relevant constraints; deleting all lower-priority Pods on the first node is unsafe. Selection considers PDB violations and victim priorities and does not promise a globally minimum number of victims.

Preemption cannot repair absent labels, an incompatible volume topology or missing hardware. A Pod may stay Pending after nomination, and another higher-priority Pod can change the outcome. Replacements, termination and API updates are asynchronous. No eviction loop was executed for this audit.

**Pros and Cons of Preemption:**
Pros:
- Can make room for higher-priority workloads when constraints permit
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

**Versioned Interface:**
Kubernetes 1.35.8 uses `PreFilter(ctx, state, pod, nodes) (*fwk.PreFilterResult, *fwk.Status)`, where `state` is `fwk.CycleState` and `nodes` is `[]fwk.NodeInfo`. Optional AddPod/RemovePod extensions receive the Pod being scheduled, the simulated added/removed PodInfo and NodeInfo. They support preemption simulation and may run on cloned state; they are not ordinary informer callbacks.

**Default PreFilter Plugins:**
Kubernetes provides the following default PreFilter plugins:

1. **InterPodAffinity**: Handles inter-pod affinity and anti-affinity requirements.
2. **NodeAffinity**: Handles node affinity requirements.
3. **NodePorts**: Handles host ports requested by pods.
4. **NodeResourcesFit**: Handles node resource requirements.
5. **PodTopologySpread**: Handles pod topology spread constraints.
6. **VolumeBinding**: Handles volume binding requirements.

**Complete PreFilter + Filter Example (`quizplugins/prefilter.go`):**
For an ordinary pool label, required node affinity is simpler. This example demonstrates validated per-cycle state and `Clone()`. It does not depend on other Pods, so no AddPod/RemovePod extensions are needed. A missing PreFilter state is an error, not permission to schedule.

```go
package quizplugins

import (
	"context"
	"strings"

	v1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/runtime"
	validation "k8s.io/apimachinery/pkg/util/validation"
	fwk "k8s.io/kube-scheduler/framework"
)

const poolStateKey fwk.StateKey = "training.example.com/pool-constraint"

type poolState struct{ Pool string }

func (s *poolState) Clone() fwk.StateData { return &poolState{Pool: s.Pool} }

type PoolConstraint struct{}

var _ fwk.PreFilterPlugin = &PoolConstraint{}
var _ fwk.FilterPlugin = &PoolConstraint{}

func (*PoolConstraint) Name() string { return "PoolConstraint" }

func (*PoolConstraint) PreFilter(_ context.Context, state fwk.CycleState, pod *v1.Pod, _ []fwk.NodeInfo) (*fwk.PreFilterResult, *fwk.Status) {
	pool := pod.Annotations["training.example.com/required-pool"]
	if problems := validation.IsValidLabelValue(pool); len(problems) != 0 {
		return nil, fwk.NewStatus(fwk.UnschedulableAndUnresolvable, strings.Join(problems, "; "))
	}
	state.Write(poolStateKey, &poolState{Pool: pool})
	return nil, nil
}

func (*PoolConstraint) PreFilterExtensions() fwk.PreFilterExtensions { return nil }

func (*PoolConstraint) Filter(_ context.Context, state fwk.CycleState, _ *v1.Pod, info fwk.NodeInfo) *fwk.Status {
	data, err := state.Read(poolStateKey)
	if err != nil {
		return fwk.AsStatus(err)
	}
	prepared, ok := data.(*poolState)
	if !ok || info == nil || info.Node() == nil {
		return fwk.NewStatus(fwk.Error, "invalid prepared state or node")
	}
	if prepared.Pool != "" && info.Node().Labels["training.example.com/pool"] != prepared.Pool {
		return fwk.NewStatus(fwk.UnschedulableAndUnresolvable, "required pool label does not match")
	}
	return nil
}

func NewPool(_ context.Context, _ runtime.Object, _ fwk.Handle) (fwk.Plugin, error) {
	return &PoolConstraint{}, nil
}
```

**Enable Both Implemented Stages and Keep Default Resource Checks:**
The registration command in question7 includes this plugin.

```yaml
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
leaderElection:
  leaderElect: true
  resourceLock: leases
  resourceName: custom-scheduler
  resourceNamespace: scheduler-lab
  leaseDuration: 15s
  renewDeadline: 10s
  retryPeriod: 2s
profiles:
- schedulerName: custom-scheduler
  plugins:
    preFilter:
      enabled:
      - name: PoolConstraint
    filter:
      enabled:
      - name: PoolConstraint
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
1. New Pods without a matching toleration are not scheduled on the tainted node.
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
With the default admission behavior, Kubernetes adds these tolerations only when equivalent tolerations were not already explicitly supplied. DaemonSet Pods receive indefinite not-ready/unreachable NoExecute tolerations instead:
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

These defaults tolerate the taint for 300 seconds after taint handling begins; they are not an exact failure-to-replacement timer. Control-plane detection and deletion add delay, and a disconnected process may still run.

**Custom Tolerations:**
Longer tolerations postpone replacement and may extend an outage; choose them from application recovery requirements rather than assuming longer is safer:
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
    image: nginx:1.30.4
```

**Node Controller and Eviction Timing:**
For the pinned upstream 1.35.8 baseline, `--node-monitor-period` defaults to 5s and `--node-monitor-grace-period` to**50s**, not 40s. The old `--pod-eviction-timeout` flag is not the current mechanism for taint-based eviction; matching Pod tolerations and the taint-eviction controller govern it. Detection, taint publication, controller rate limits and deletion can add delay.

Since Kubernetes 1.29, taint-based eviction runs in the separate `taint-eviction-controller`, enabled by default but independently configurable on self-managed control planes. These values are not EKS configuration instructions or a failover-time guarantee. Before force-removing a stateful Pod on an unreachable node, establish that the old writer is stopped/fenced to avoid concurrent writers.

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
package diagnostic

import v1 "k8s.io/api/core/v1"

// This observes a taint; it is not a network probe or proof a process stopped.
func HasUnreachableTaint(node *v1.Node) bool {
    if node == nil {
        return false
    }
    for _, taint := range node.Spec.Taints {
        if taint.Key == "node.kubernetes.io/unreachable" && taint.Effect == v1.TaintEffectNoExecute {
            return true
        }
    }
    return false
}
```

**Issues with Other Options:**
- B. The node is unschedulable but existing pods continue to run: This is the behavior of the `NoSchedule` effect; the `NoExecute` effect also removes existing pods without tolerations.
- C. The node is in maintenance mode and new pods are not scheduled: This is typically the behavior of the `node.kubernetes.io/unschedulable:NoSchedule` taint.
- D. PreferNoSchedule is a soft preference. The usual memory-pressure and disk-pressure taints instead use NoSchedule; neither describes unreachable:NoExecute.
</details>

## References

Use the [Part1 module](../../scheduling/01-custom-scheduler-part1.md) and [Part2 implementation](../../scheduling/02-custom-scheduler-part2.md). Code/configuration checks are local; no cloud deployment or eviction was performed.

* [Framework interfaces at v1.35.8](https://github.com/kubernetes/kubernetes/blob/v1.35.8/staging/src/k8s.io/kube-scheduler/framework/interface.go)
* [Extender wire types](https://github.com/kubernetes/kubernetes/blob/v1.35.8/staging/src/k8s.io/kube-scheduler/extender/v1/types.go)
* [Node and Pod affinity](https://kubernetes.io/docs/concepts/scheduling-eviction/assign-pod-node/)
* [Topology spread](https://kubernetes.io/docs/concepts/scheduling-eviction/topology-spread-constraints/)
* [Taints and tolerations](https://kubernetes.io/docs/concepts/scheduling-eviction/taint-and-toleration/)
* [Priority and preemption](https://kubernetes.io/docs/concepts/scheduling-eviction/pod-priority-preemption/)
* [Node lifecycle defaults](https://github.com/kubernetes/kubernetes/blob/v1.35.8/pkg/controller/nodelifecycle/config/v1alpha1/defaults.go)
