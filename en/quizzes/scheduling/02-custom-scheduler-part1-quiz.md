# Custom Scheduler Quiz (Part 1)

> **Example Baseline**: Kubernetes 1.35.8, Go 1.27.1
> **Last Updated**: September 11, 2026

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

**Scheduling Process (Kubernetes 1.35.8):**
1. **Filter**: `NodeResourcesFit` checks effective resource requests against remaining allocatable resources; `NodePorts` checks requested host ports; `NodeAffinity` handles node selectors and affinity; `TaintToleration` checks taints. Volume plugins such as `VolumeBinding`, `VolumeZone` and `NodeVolumeLimits` enforce storage constraints. Node pressure is reflected through node conditions/taints; names such as `CheckNodeDiskPressure` are historical predicates, not current configurable plugins.
2. **Score**: `NodeResourcesFit` (default `LeastAllocated`), `NodeResourcesBalancedAllocation`, `NodeAffinity`, `InterPodAffinity`, `PodTopologySpread`, `TaintToleration` and `ImageLocality` contribute preferences. They do not all measure live resource utilization.
3. **Bind**: After the remaining framework phases succeed, the scheduler records the node assignment. Kubelet and the runtime then manage execution. A high score does not guarantee startup, latency or availability.

**Secondary Scheduler Configuration Example:**
This changes a scoring weight and retains the default filters. Configurations in this quiz are files consumed with `--config`, not Kubernetes API resources to apply with `kubectl`.
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
    score:
      enabled:
      - name: NodeResourcesBalancedAllocation
        weight: 2
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

1. **Configure a kube-scheduler-based secondary scheduler**: Preserve the default plugins and adjust only the required behavior. Part1 provides a complete command, RBAC, ConfigMap and Deployment.

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
    score:
      enabled:
      - name: NodeResourcesBalancedAllocation
        weight: 2
```

2. **Implement an independent scheduler**: This requires a correct cache, queue, list/watch recovery, resource accounting, volume coordination, retries, leader election and binding. A watch-only loop misses existing Pods and disconnections; production code should use informers/workqueues and handle tombstones, cancellation and stale objects. Selecting a Ready node does not prove that a Pod fits. The Part1 example therefore delegates these duties to upstream kube-scheduler.

3. **Develop a framework plugin**: Compile a plugin into the scheduler binary and register it with `app.WithPlugin`. Question4 supplies a complete Filter plugin, question6 a Score plugin, and question7 the registration command. Their interfaces are pinned to `k8s.io/kube-scheduler/framework` v0.35.8; signatures differ across Kubernetes minors.

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
  schedulerName: custom-scheduler  # Specify custom scheduler
  containers:
  - name: main-container
    image: nginx:1.30.4
    resources:
      requests:
        memory: "64Mi"
        cpu: "250m"
      limits:
        memory: "128Mi"
        cpu: "500m"
```

This pod is scheduled only by the scheduler named "custom-scheduler". If a scheduler with that name does not exist in the cluster, the pod will remain in the `Pending` state.

**Configuring the Scheduler Name:**
Use the complete Part1 Deployment and mount this configuration as `/etc/scheduler/config.yaml`, with `--config=/etc/scheduler/config.yaml`. `--scheduler-name` is not the current configuration mechanism. The ServiceAccount and Lease permissions are prerequisites.

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

**Considerations When Selecting a Scheduler:**
1. **Availability**: If the specified scheduler is not running, the pod will not be scheduled.
2. **Functionality**: Each scheduler can have different scheduling algorithms and policies.
3. **Policy routing**: `schedulerName` selects a scheduler profile; it provides no security or resource isolation by itself.
4. **Special hardware**: Dedicated schedulers can be used for special hardware like GPUs or FPGAs.

**Checking Scheduler Status:**
```bash
# Check pod status
kubectl get pod custom-scheduled-pod

# Check scheduling events
kubectl describe pod custom-scheduled-pod | grep -A 5 Events

# Check scheduler logs
kubectl logs -n scheduler-lab -l app=custom-scheduler --prefix --tail=100
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
* **PreEnqueue / QueueSort**: Gate queue admission and order queued Pods.
* **PreFilter / Filter**: Prepare shared state and exclude infeasible nodes.
* **PostFilter**: Attempt recovery when no feasible node exists, for example preemption.
* **PreScore / Score / optional NormalizeScore**: Prepare and rank feasible nodes; normalized plugin scores must be in 0–100.
* **Reserve / Unreserve**: Record assumed state and undo it when scheduling fails. This is not physical CPU or device allocation.
* **Permit**: Allow, reject or wait before proceeding.
* **PreBind / Bind / PostBind**: Prepare dependencies, commit binding and run post-binding work. `PostBind` cannot veto an already committed binding. Interfaces can add version-specific methods, so compile against the target release.

**Default Filters:**
`NodeResourcesFit`, `NodeName`, `NodeUnschedulable`, `NodePorts`, `TaintToleration`, `NodeAffinity`, `InterPodAffinity`, `PodTopologySpread`, `VolumeRestrictions`, `NodeVolumeLimits`, `VolumeBinding` and `VolumeZone` cover different constraints. Old predicate names and provider-specific `EBSLimits` are not the current plugin names.

**Custom Filter Example (`plugins/filter.go`):**
This simple label rule would normally be expressed with required node affinity. It demonstrates the framework interface. A missing label is unresolvable by preempting other Pods, but a later node-label change can make the Pod eligible for retry.

```go
package plugins

import (
	"context"

	v1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/runtime"
	fwk "k8s.io/kube-scheduler/framework"
)

type MyFilterPlugin struct{}

var _ fwk.FilterPlugin = &MyFilterPlugin{}

func (*MyFilterPlugin) Name() string { return "MyFilterPlugin" }

func (*MyFilterPlugin) Filter(_ context.Context, _ fwk.CycleState, _ *v1.Pod, info fwk.NodeInfo) *fwk.Status {
	if info == nil || info.Node() == nil {
		return fwk.NewStatus(fwk.Error, "missing node")
	}
	if info.Node().Labels["custom-label"] != "required-value" {
		return fwk.NewStatus(fwk.UnschedulableAndUnresolvable, "node lacks required label")
	}
	return nil
}

func NewFilter(_ context.Context, _ runtime.Object, _ fwk.Handle) (fwk.Plugin, error) {
	return &MyFilterPlugin{}, nil
}
```

**Enable the Custom Filter Alongside the Defaults:**
Question7 registers this plugin. Do not disable `NodeResourcesFit` to add a label check.

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
    filter:
      enabled:
      - name: MyFilterPlugin
```

**Issues with Other Options:**
- A. Score nodes: This is the role of the "Score" extension point.
- B. Bind pods to nodes: This is the role of the "Bind" extension point.
- D. Sort pods in the scheduling queue: This is the role of the "Queue Sort" extension point.
</details>

### 5. Which task is performed by kubelet and the container runtime, rather than by the scheduler?

A. Evaluating node resource requests and allocatable resources
B. Considering Pod priority and preemption
C. Downloading image layers and creating containers
D. Evaluating node affinity and inter-Pod affinity

<details>
<summary>Show Answer</summary>

**Answer: C. Downloading image layers and creating containers**

**Explanation:**
The scheduler chooses a node; kubelet asks the runtime to pull images and create containers. **Image locality can influence scheduling**: the default `ImageLocality` score plugin uses the node's reported cached images and image sizes. Cache reports can be stale and do not guarantee that a pull will be avoided.

**Implementation Considerations:**
1. **Resources**: Keep `NodeResourcesFit`; it uses effective requests and the scheduler's cached assigned/assumed usage. Live CPU/memory metrics are different inputs. CPU/memory limits can be overcommitted and are not the default fit test.
2. **Priority**: Use PriorityClass and preemptionPolicy deliberately. A high-priority Pod may remain Pending if preemption cannot satisfy affinity, volumes or other constraints.
3. **Placement**: Required node affinity restricts eligible nodes; preferred affinity scores them. Replace the example AZs below with zones that actually have eligible capacity. Ordinary GPU and topology requirements often need no custom scheduler.

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
  containers:
  - name: nginx
    image: nginx:1.30.4
    resources:
      requests:
        cpu: 100m
        memory: 64Mi
```

4. **Other constraints**: Preserve taints/tolerations, topology spread, storage topology/attachment limits and hardware resource checks. Model network locality only with reliable topology data; labels do not prove latency.
5. **Image handling**: `ImageLocality` is a preference, not a capacity or startup guarantee. Image garbage collection, registry authentication and pull failures still occur on the node.

**Other Options:**
A, B and D are valid scheduling considerations. The original distinction is between placement and runtime actions, not between scheduling and image information.
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
1. Each scoring plugin computes a score; after optional normalization it must be in the range 0–100.
2. Each plugin's score is weighted according to the configured weight.
3. The weighted scores from all plugins are summed.
4. The node with the highest total score is selected for pod placement.

**Default Scoring Plugins:**
Kubernetes provides the following default scoring plugins:

1. **NodeResourcesBalancedAllocation**: Prefers balanced fractions of requested CPU and memory, not measured utilization.
2. **NodeResourcesFit**: Uses the configured LeastAllocated, MostAllocated or RequestedToCapacityRatio strategy over requests and allocatable resources.
3. **NodeAffinity**: Scores based on node affinity rules.
4. **InterPodAffinity**: Scores based on inter-pod affinity/anti-affinity rules.
5. **PodTopologySpread**: Gives higher scores to nodes that spread pods evenly across topology domains.
6. **TaintToleration**: Penalizes intolerable PreferNoSchedule taints; hard taints are handled during filtering.
7. **ImageLocality**: Gives higher scores to nodes that already have the required container images.

**Custom Scoring Plugin (`plugins/score.go`):**
Node labels in this example are administrator-controlled policy inputs. Invalid values fail the scoring cycle instead of silently inventing a preference. A valid zero score is not a filter.

```go
package plugins

import (
	"context"
	"strconv"

	v1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/runtime"
	fwk "k8s.io/kube-scheduler/framework"
)

type MyScorePlugin struct{}

var _ fwk.ScorePlugin = &MyScorePlugin{}

func (*MyScorePlugin) Name() string { return "MyScorePlugin" }

func (*MyScorePlugin) Score(_ context.Context, _ fwk.CycleState, _ *v1.Pod, info fwk.NodeInfo) (int64, *fwk.Status) {
	if info == nil || info.Node() == nil {
		return 0, fwk.NewStatus(fwk.Error, "missing node")
	}
	value := info.Node().Labels["custom-score-label"]
	if value == "" {
		return 0, nil
	}
	score, err := strconv.ParseInt(value, 10, 64)
	if err != nil || score < fwk.MinNodeScore || score > fwk.MaxNodeScore {
		return 0, fwk.NewStatus(fwk.Error, "custom-score-label must be an integer from 0 to 100")
	}
	return score, nil
}

// Scores are already absolute 0-100 values; no relative rescaling is needed.
func (*MyScorePlugin) ScoreExtensions() fwk.ScoreExtensions { return nil }

func NewScore(_ context.Context, _ runtime.Object, _ fwk.Handle) (fwk.Plugin, error) {
	return &MyScorePlugin{}, nil
}
```

**Weights for the Two-Plugin Arithmetic Example:**
The following deliberately replaces only the **Score** plugin set. Default Filter plugins remain enabled. In a real policy, retain any other scoring preferences you need.

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
    score:
      disabled:
      - name: "*"
      enabled:
      - name: MyScorePlugin
        weight: 5
      - name: NodeResourcesBalancedAllocation
        weight: 2
```

**Scoring Result Example:**
Illustrative arithmetic, not measured results: assume A, B and C passed filtering and the two enabled plugins produce these final 0–100 scores:

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

**Extension Methods:**

1. **Framework plugins** run inside the scheduler. Save the complete Filter/Score examples from questions4/6 under `plugins/` in the Part1 module, and save this command as `cmd/with-plugins/main.go`. Build it with `CGO_ENABLED=0 go build -buildvcs=false -o custom-scheduler ./cmd/with-plugins`. Registration alone does not enable a plugin; the configuration must reference it.

```go
package main

import (
	"os"

	"example.com/custom-scheduler/plugins"
	"k8s.io/component-base/cli"
	"k8s.io/kubernetes/cmd/kube-scheduler/app"
)

func main() {
	command := app.NewSchedulerCommand(
		app.WithPlugin("MyFilterPlugin", plugins.NewFilter),
		app.WithPlugin("MyScorePlugin", plugins.NewScore),
	)
	os.Exit(cli.Run(command))
}
```

Factories receive `(context.Context, runtime.Object, framework.Handle)` in this version. These examples take no custom arguments. If adding configuration, decode and validate the `runtime.Unknown` payload with the versioned framework runtime decoder; do not assert it to an unregistered custom type.

2. **HTTP extenders** add external filtering/prioritization and optionally binding. `extenders` belongs at the **top level**, not under a profile. This illustrative configuration requires an implemented extender service, matching TLS certificates mounted at the shown paths, network reachability and bounded error handling. It is not a standalone working server or an EKS managed-scheduler configuration. Leaving `bindVerb` unset preserves the default binder.

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
- urlPrefix: https://extender.scheduler-lab.svc:8443
  filterVerb: filter
  prioritizeVerb: prioritize
  weight: 5
  enableHTTPS: true
  tlsConfig:
    caFile: /etc/extender-tls/ca.crt
    certFile: /etc/extender-tls/tls.crt
    keyFile: /etc/extender-tls/tls.key
  httpTimeout: 2s
  nodeCacheCapable: false
  ignorable: false
```

With `ignorable: false`, an extender filter failure blocks that scheduling attempt. Setting it true could bypass a required custom constraint. Prioritization errors are handled differently: Kubernetes1.35.8 logs the failure and omits that extender’s scores, so a score must not enforce a mandatory rule. Prefer a framework plugin where possible; test timeout, retry and failure behavior.

3. **Multiple schedulers** use distinct `profiles[].schedulerName` values and separate leader-election groups. Use the complete Part1 Deployment/RBAC rather than launching a second process with the default scheduler's identity or Lease.

**Node Controller Role:**
Kubelet normally registers the node and reports health. Node lifecycle controllers observe heartbeats, update conditions/taints and coordinate reactions to unhealthy nodes. This information affects scheduling, but changing the node controller is not a scheduler extension API.

**Choosing an Approach:**
Assess implementation complexity, per-node HTTP overhead, cache consistency, failure behavior and upgrade compatibility. On EKS, deploy a secondary scheduler; the managed default scheduler's flags and registry are not yours to replace.

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
The purpose of the `--leader-elect` flag in the Kubernetes scheduler is to ensure that only one scheduler instance is active and performs work in high availability (HA) configurations. It coordinates replicas in the same Lease group; it is not fencing for every possible failure or a replacement for concurrency-safe API operations.

**Leader Election Mechanism:**
1. When multiple scheduler instances are deployed, a leader election algorithm elects only one instance as the leader.
2. Only the instance elected as leader performs actual scheduling work.
3. Other instances remain in standby mode, and a new leader is elected if the current leader fails.
4. This mechanism is implemented using Kubernetes resource locks.

**Leader Election Configuration:**
Use the versioned configuration file for the Lease identity and timing:

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

**HA Deployment:**
The complete Part1 Deployment already runs two replicas with the same configuration and ServiceAccount. For an isolated lab, it can be scaled to three. This does not establish production HA: verify separate failure domains, API reachability, bootstrap capacity and failover behavior.

```bash
kubectl -n scheduler-lab scale deployment/custom-scheduler --replicas=3
kubectl -n scheduler-lab get lease custom-scheduler -o yaml
kubectl -n scheduler-lab logs -l app=custom-scheduler --prefix --tail=100
```

**Custom Implementations:**
The kube-scheduler command already integrates client-go leader election. Independent implementations need a unique identity per process, a shared Lease per scheduler group, renewal permissions and cancellation of scheduling work when leadership is lost. The client-go mechanism does not provide fencing against every possible overlapping process; bindings and external side effects still need concurrency-safe design. With `ReleaseOnCancel`, protected work must stop before releasing the Lease.

**When Disabling Election Is Appropriate:**
Only disable it in a deliberately isolated experiment or when another mechanism guarantees a single active process, including rollouts and failures. `replicas: 1` can overlap during a rolling update. Different scheduler names require different election groups; names alone do not make disabling election safe.

**Issues with Other Options:**
- A. Grant leadership authority to the scheduler: This is a vague description that does not explain the specific purpose of leader election.
- C. Run the scheduler only on the leader node of the cluster: Scheduler leadership belongs to a process, not a universal cluster leader node. A secondary scheduler can run as a Pod on worker nodes.
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
1. **value**: Priority value; higher values mean higher priority. User-defined values must be at most 1000000000; the built-in critical classes use the reserved higher range.
2. **globalDefault**: When set to true, this class becomes the cluster-wide default for newly admitted Pods without a class; existing Pods are not retroactively changed. All lab classes below use false.
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
    image: nginx:1.30.4
```

**Priority and Preemption Behavior:**
1. **Scheduling priority**: Higher priority pods are processed first in the scheduling queue.
2. **Preemption**: When there is no node to schedule a high priority pod, the scheduler can remove (preempt) lower priority pods to free up space.
3. **Preemption policy**: Pods using `preemptionPolicy: Never` do not preempt other Pods, but may themselves be preempted. Queue backoff can allow lower-priority Pods to proceed while a higher-priority Pod cannot fit.

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
globalDefault: false
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
package priorityexample

import (
    "sort"
    v1 "k8s.io/api/core/v1"
)

func podPriority(pod *v1.Pod) int32 {
    if pod == nil || pod.Spec.Priority == nil {
        return 0
    }
    return *pod.Spec.Priority
}

// Demonstrates only priority comparison, not queue backoff or requeue handling.
func sortPodsByPriority(pods []*v1.Pod) {
    sort.SliceStable(pods, func(i, j int) bool {
        return podPriority(pods[i]) > podPriority(pods[j])
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
B. Compare remaining allocatable resources with effective Pod requests
C. Check compatibility between node operating system and pod
D. Measure node network bandwidth

<details>
<summary>Show Answer</summary>

**Answer: B. Compare remaining allocatable resources with effective Pod requests**

**Explanation:**
`NodeResourcesFit` compares a Pod's effective requests with a node's **allocatable resources minus already assigned/assumed requests**. It also checks the Pod-count limit and relevant extended resources. It does not simply compare the new Pod with total `Capacity`, and it does not generally reject CPU/memory limits whose sum exceeds capacity.

**Resource Accounting:**
* Account for regular containers, sequential init containers, restartable sidecars, Pod overhead and supported Pod-level resource settings. API defaulting can derive requests from limits.
* Use the scheduler snapshot, including assumed bindings; summing only Running Pods from an API list misses reserved demand.
* Preserve the target version's feature-gate and DRA behavior. CPU/memory arithmetic alone is not a complete resource-fit implementation.

**Configuration:**
`NodeResourcesFit` is enabled by default. This example changes its scoring strategy without removing its Filter stage.

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
  pluginConfig:
  - name: NodeResourcesFit
    args:
      scoringStrategy:
        type: MostAllocated
        resources:
        - name: cpu
          weight: 1
        - name: memory
          weight: 1
```

**Scoring Strategies:**
The NodeResourcesFit plugin supports the following scoring strategies:

1. **LeastAllocated**: Gives higher scores to nodes with lower requested fractions. This is useful for spreading resource usage.
   ```
   score ≈ 100 × (allocatable - requested) / allocatable
   ```

2. **MostAllocated**: Gives higher scores to nodes with higher requested fractions. This is useful for concentrating resource usage to minimize the number of nodes.
   ```
   score ≈ 100 × requested / allocatable
   ```

3. **RequestedToCapacityRatio**: Assigns scores based on the ratio of requested resources to capacity using a configured piecewise-linear shape. The simplified single-resource formulas above omit integer rounding, zero/over-capacity handling and resource weights; they are not live-utilization formulas.

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

**Implementing Fit Safely:**
Keep the upstream plugin in the scheduler framework. A hand-written function that sums the new Pod's CPU/memory, ignores existing demand and then returns true is not a valid replacement. The companion audit checks the pinned upstream fit implementation locally with an existing 1500m request on a 2-core node: another 1-core request is rejected, while a 250m request fits even when CPU limits are larger. This is a local accounting check, not a cluster scheduling benchmark.

`kubectl top` reports current metrics when Metrics Server is available; these are not the requested-resource totals used by default fit/scoring. Inspect full Pod specs, including init containers and overhead, when diagnosing discrepancies.

**Issues with Other Options:**
- A. Place pods according to the physical location of nodes: This is the role of topology-related plugins (e.g., NodeAffinity, PodTopologySpread).
- C. Check compatibility between node operating system and pod: Use OS labels and placement constraints as required; they do not by themselves prove image/runtime compatibility. `NodeResourcesFit` is not that check.
- D. Measure node network bandwidth: The Kubernetes scheduler does not consider network bandwidth by default. Custom metrics and plugins are needed for this.
</details>

## References

The examples use the [Part1 module and deployment](../../scheduling/01-custom-scheduler-part1.md). Local compilation/configuration/accounting checks do not establish production readiness; no cluster or AWS deployment was performed.

* [Scheduler configuration and default plugins](https://kubernetes.io/docs/reference/scheduling/config/)
* [Framework extension points](https://kubernetes.io/docs/concepts/scheduling-eviction/scheduling-framework/)
* [Resource scoring](https://kubernetes.io/docs/concepts/scheduling-eviction/resource-bin-packing/)
* [Priority and preemption](https://kubernetes.io/docs/concepts/scheduling-eviction/pod-priority-preemption/)
* [Pinned Go interfaces](https://github.com/kubernetes/kubernetes/blob/v1.35.8/staging/src/k8s.io/kube-scheduler/framework/interface.go)
