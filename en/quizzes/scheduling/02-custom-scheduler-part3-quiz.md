# Custom Scheduler Quiz (Part 3)

> **Example Baseline**: Kubernetes 1.35.8, Go 1.27.1; native 1.37 features noted separately
> **Last Updated**: September 11, 2026

This quiz tests your advanced understanding of implementing and using Custom Schedulers in Kubernetes.

## Quiz Questions

### 1. Which claim about multiple schedulers is incorrect?

A. Additional schedulers add API watch/cache work
B. Independently assumed placements can contend for resources
C. Adding a scheduler automatically increases node capacity
D. Unrelated scheduler groups need distinct leader-election Leases

<details>
<summary>Show Answer</summary>

**Answer: C. Adding a scheduler automatically increases node capacity**

**Explanation:**
A scheduler assigns Pods; it does not create node capacity. Additional schedulers can increase API/network load. Each watches committed Pod state, but its in-memory assumptions are not a shared reservation transaction with other schedulers. Keep resource filters, and test concurrent scheduling on shared pools.

Omitting `schedulerName` selects `default-scheduler`; it does not invite every compliant scheduler to bind the Pod. Replicas of one scheduler intentionally share a Lease for HA. Unrelated groups sharing that Lease can block each other, while processes using the same profile without coordinated leadership can race.

**Pod routing examples:**

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: default-pod
spec:
  containers:
  - name: nginx
    image: nginx:1.30.4
    resources:
      requests:
        cpu: 100m
        memory: 64Mi
---
apiVersion: v1
kind: Pod
metadata:
  name: custom-pod
spec:
  schedulerName: custom-scheduler
  tolerations:
  - key: dedicated
    operator: Equal
    value: custom-scheduler
    effect: NoSchedule
  containers:
  - name: nginx
    image: nginx:1.30.4
    resources:
      requests:
        cpu: 100m
        memory: 64Mi
```

**Separate scheduler identity and node-pool policy:**
Use the complete Part1 Deployment/RBAC. Names and Lease identity are in `KubeSchedulerConfiguration`, not an obsolete `--scheduler-name` flag. The built-in `NodeAffinity` plugin supports profile-level `addedAffinity`; there is no default `NodeSelector` plugin.

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
  - name: NodeAffinity
    args:
      addedAffinity:
        requiredDuringSchedulingIgnoredDuringExecution:
          nodeSelectorTerms:
          - matchExpressions:
            - key: training.example.com/scheduler-pool
              operator: In
              values:
              - custom
```

```bash
# Only label/taint a node selected for this isolated lab.
: "${CUSTOM_NODE:?Select the lab node}"
kubectl label node "$CUSTOM_NODE" training.example.com/scheduler-pool=custom --overwrite
kubectl taint node "$CUSTOM_NODE" dedicated=custom-scheduler:NoSchedule --overwrite
```

The custom Pod above tolerates the example taint. Tolerations do not force placement, and scheduler names, node labels and quotas are not security boundaries. The following namespace quotas limit admitted requests; they do not reserve a node pool. Create the namespaces first and supply requests on workloads subject to these quotas.
**Namespace quota examples:**
   ```yaml
   apiVersion: v1
   kind: ResourceQuota
   metadata:
     name: default-scheduler-quota
     namespace: default-workloads
   spec:
     hard:
       pods: "10"
       requests.cpu: "20"
       requests.memory: 40Gi

   ---
   apiVersion: v1
   kind: ResourceQuota
   metadata:
     name: custom-scheduler-quota
     namespace: custom-workloads
   spec:
     hard:
       pods: "10"
       requests.cpu: "20"
       requests.memory: 40Gi
   ```

**Read-only monitoring of the secondary scheduler:**
Use its actual namespace/labels. EKS managed control-plane components are not the secondary Deployment shown here.

```bash
kubectl -n scheduler-lab get pods -l app=custom-scheduler
kubectl -n scheduler-lab logs -l app=custom-scheduler --prefix --tail=100
kubectl -n scheduler-lab get lease custom-scheduler
kubectl get pods -A --field-selector=spec.schedulerName=custom-scheduler,spec.nodeName= -o wide
```

**Other options:** A, B and D describe real workload or coordination considerations.
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

**Versioned Permit contract:**
`Permit(ctx, fwk.CycleState, pod, nodeName)` returns a status and wait duration. `Success` continues, `Wait` asks the framework to hold the Pod, and a failure status such as `Unschedulable` rejects the attempt. There is no `framework.Deny` enum. Rejection does not immediately bind another node; retry/backoff and reservation cleanup follow.

`TaintToleration` and `PodTopologySpread` are not default Permit plugins. The baseline retains their actual Filter/Score stages.

**Complete interface demonstration (`quizplugins/permit.go`):**
The annotation values are test directives, not trusted authorization. No external approval service is supplied. A `wait` Pod times out unless an integrated test driver releases it after the framework registers it; private unconsumed channels cannot release framework waiters.

```go
package quizplugins

import (
	"context"
	"time"

	v1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/apimachinery/pkg/types"
	fwk "k8s.io/kube-scheduler/framework"
)

type CustomPermit struct{ handle fwk.Handle }

var _ fwk.PermitPlugin = &CustomPermit{}

func (*CustomPermit) Name() string { return "CustomPermit" }

func (*CustomPermit) Permit(_ context.Context, _ fwk.CycleState, pod *v1.Pod, _ string) (*fwk.Status, time.Duration) {
	// These are test directives, not an authorization or approval mechanism.
	switch pod.Annotations["training.example.com/permit"] {
	case "", "allow":
		return nil, 0
	case "wait":
		return fwk.NewStatus(fwk.Wait, "waiting for the test driver"), 30 * time.Second
	case "deny":
		return fwk.NewStatus(fwk.UnschedulableAndUnresolvable, "test driver denied"), 0
	default:
		return fwk.NewStatus(fwk.Error, "unknown test permit directive"), 0
	}
}

// Call only after the framework has registered the waiting Pod. The caller
// must handle false (not registered yet, already released, deleted or timed out).
func (p *CustomPermit) Allow(uid types.UID) bool {
	waiting := p.handle.GetWaitingPod(uid)
	if waiting == nil {
		return false
	}
	waiting.Allow(p.Name())
	return true
}

func (p *CustomPermit) Reject(uid types.UID, reason string) bool {
	waiting := p.handle.GetWaitingPod(uid)
	if waiting == nil {
		return false
	}
	waiting.Reject(p.Name(), reason)
	return true
}

func NewPermit(_ context.Context, _ runtime.Object, handle fwk.Handle) (fwk.Plugin, error) {
	return &CustomPermit{handle: handle}, nil
}
```

Register this and the later PreBind example in `cmd/quiz-scheduler/main.go`; save both source files before building:

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
		app.WithPlugin("CustomPermit", quizplugins.NewPermit),
		app.WithPlugin("IdentityPreBind", quizplugins.NewPreBind),
	)
	os.Exit(cli.Run(command))
}
```

Build with the Part1 module using `CGO_ENABLED=0 go build -buildvcs=false -o custom-scheduler ./cmd/quiz-scheduler`. Enable only the relevant extension point and retain defaults:

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
    permit:
      enabled:
      - name: CustomPermit
```

**Permit use cases:**
1. **Gang scheduling**: Delay scheduling of a pod group until all related pods are ready to be scheduled.
2. **Resource reservation**: Reserve external resources before pods are scheduled.
3. **Policy validation**: Ensure pod scheduling complies with organizational policies.
4. **Approval workflows**: Request external approval for pod scheduling.

**Why a Permit barrier is not a complete gang scheduler:**
A real implementation must scope group identity by namespace/UID, count unique members, handle retries/deletion/timeouts, release reservations on failure and account for binding failures. Do not construct a private `WaitingPod`, count the same retry twice or treat the current Pod as registered before Permit returns. A barrier does not guarantee simultaneous container startup or freedom from starvation. Question3 describes maintained implementations.

**Issues with other options:**
- A. Bind pods to nodes: This is the role of the "Bind" extension point.
- C. Exclude nodes where pods cannot run: This is the role of the "Filter" extension point.
- D. Assign scores to nodes: This is the role of the "Score" extension point.
</details>
### 3. What is the main purpose of Gang Scheduling in Kubernetes?

A. Place pods only on specific nodes
B. Coordinate placement of a required group of Pods
C. Distribute pods evenly across various nodes
D. Schedule pods based on priority

<details>
<summary>Show Answer</summary>

**Answer: B. Coordinate placement of a required group of Pods**

**Explanation:**
The main purpose of Gang Scheduling in Kubernetes is to coordinate placement of the required group before allowing it to proceed. This is important for workloads like distributed training jobs and distributed data processing jobs where all components must run simultaneously.

**Why Gang scheduling is needed:**
1. **All-or-Nothing requirement**: Some workloads require all components to run simultaneously; if only some run, the job doesn't progress.
2. **Preventing resource waste**: If only some pods are scheduled while others wait, resources used by already-scheduled pods may be wasted.
3. **Preventing deadlock**: Deadlock can occur when interdependent pods are scheduled at different times.

**Implementation choices and versions:**
Upstream Kubernetes 1.35 introduced opt-in alpha `GenericWorkload`/`GangScheduling`. The current upstream 1.37 PodGroup scheduling feature is **beta and disabled by default**, requiring `GenericWorkload` and the `scheduling.k8s.io/v1beta1` API. This is not proof of EKS feature availability or permission to change managed control-plane flags.

Volcano is an alternative installed scheduler; Kube-batch is its historical predecessor, not a separate current recommendation. A supported controller, its CRDs, enabled gang scheduling and an Open queue are prerequisites.

**Volcano Job example (schema checked against1.15.2):**
The controller creates the PodGroup. All four members are defined, unlike a minMember4 group with only one Pod. This CPU-only sleep workload demonstrates the manifest relationship, not distributed training or a benchmark. It was not deployed.

```yaml
apiVersion: batch.volcano.sh/v1alpha1
kind: Job
metadata:
  name: gang-demo
  namespace: default
spec:
  minAvailable: 4
  schedulerName: volcano
  queue: default
  maxRetry: 1
  tasks:
  - name: workers
    replicas: 4
    template:
      spec:
        restartPolicy: Never
        containers:
        - name: worker
          image: busybox:1.37.0
          command:
          - sh
          - -c
          - sleep 60
          resources:
            requests:
              cpu: 250m
              memory: 128Mi
            limits:
              memory: 256Mi
```

The scheduling decision coordinates the minimum group; it does not make processes start at the same instant. Application barriers, timeout policy, fairness and recovery remain necessary. Native PodGroup placement also has documented limitations for heterogeneous Pods and inter-Pod dependencies; a feasible placement is not always found by its ordering algorithm.

**Pros and cons of Gang scheduling:**
Pros:
- Coordinates the configured minimum group
- Prevents resource waste
- Can reduce partial-allocation deadlocks; fairness and timeouts still matter

Cons:
- Increased implementation complexity
- Potential scheduling delays
- Potential decrease in cluster resource utilization

**Workloads that need Gang scheduling:**
1. **Distributed training jobs**: Distributed training frameworks like TensorFlow, PyTorch
2. **Distributed data processing**: Distributed data processing frameworks like Spark, Flink
3. **MPI jobs**: High-performance computing (HPC) workloads
4. **Tightly coupled parallel jobs**: Workloads that require a declared minimum set of workers

**Issues with other options:**
- A. Place pods only on specific nodes: This is the role of node selectors or node affinity.
- C. Distribute pods evenly across various nodes: This is the role of pod topology spread constraints.
- D. Schedule pods based on priority: This is the role of pod priority and preemption.
</details>

### 4. Which function is not part of the kube-scheduler extender callback contract?

A. Filtering candidate nodes
B. Prioritizing candidate nodes
C. Optional Pod-to-node binding
D. Admission validation through ValidatingWebhookConfiguration

<details>
<summary>Show Answer</summary>

**Answer: D. Admission validation through ValidatingWebhookConfiguration**

An extender can implement configured filter, prioritize, preempt and bind callbacks. None of the literal URL paths is mandatory: `filterVerb` could even name a path `validate`, but its payload/meaning would still be filtering. Admission webhooks are a different API contract.

**Configuration:**
Reuse the Part2 TLS service/certificate prerequisites. `extenders` is top-level. Keep required filtering fail-closed and keep the scheduler's own resource accounting.

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

**Wire contract:**
* Filter/prioritize use `ExtenderArgs` with `Pod` and either full `Nodes` or `NodeNames`, according to `nodeCacheCapable`.
* Filter returns `Nodes`/`NodeNames`, failure maps and `Error`.
* Prioritize returns a bare array such as `[{"Host":"node-a","Score":7}]`; scores are0–10, not100. Priority errors omit that extender's scores, so scores cannot enforce required constraints.
* Bind uses `PodName`, `PodNamespace`, `PodUID` and `Node`. Only return success after the real binding succeeds; a `customBind` stub returning nil is not a binding implementation.
* Preempt uses `ExtenderPreemptionArgs` with candidate victim maps and returns `ExtenderPreemptionResult.NodeNameToMetaVictims`. It does not return an invented `podsToPreempt` envelope.

Use the complete bounded handler in [Part2](../../scheduling/02-custom-scheduler-part2.md). It leaves `bindVerb` unset to retain `DefaultBinder`. No additional HTTP server or fake-success bind endpoint is provided here.
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
PostFilter attempts recovery when filtering finds no feasible node; default preemption is one implementation. When all nodes are excluded during the filtering phase and a pod cannot be scheduled, PostFilter plugins may try actions that make a later attempt feasible.

**Key functions of the PostFilter extension point:**
1. **Identify preemption candidates**: Identifies pods and nodes that can be preempted.
2. **Preemption simulation**: Simulates whether pods can be scheduled after preemption.
3. **Preemption decision**: Determines the optimal preemption strategy.

**Versioned interface and safe extension:**
The pinned API uses `fwk.CycleState` and `fwk.NodeToStatusReader`; `PostFilterResult` embeds `NominatingInfo`. A nomination is a possible next target, not a committed binding.

Keep the default `DefaultPreemption` implementation unless you have a complete, tested alternative. It evaluates lower-priority victims against the remaining constraints and considers PDB violations on a best-effort basis. A loop with omitted victim selection followed by direct Pod deletion is unsafe. Recovery plugins can perform other suitable actions, so PostFilter is not limited by definition to preemption.

The configuration below tunes the default implementation without disabling it. The candidate limits bound its search; they are not a guarantee of global optimality or eventual scheduling.

**Preemption-related settings:**
```yaml
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
profiles:
- schedulerName: custom-scheduler
  pluginConfig:
  - name: DefaultPreemption
    args:
      minCandidateNodesPercentage: 10
      minCandidateNodesAbsolute: 100
leaderElection:
  leaderElect: true
  resourceLock: leases
  resourceName: custom-scheduler
  resourceNamespace: scheduler-lab
  leaseDuration: 15s
  renewDeadline: 10s
  retryPeriod: 2s
```

**Preemption process:**
1. PostFilter phase is called when a pod fails the filtering phase on all nodes.
2. PostFilter plugin identifies preemption candidate nodes.
3. Determines which pods to preempt on each node.
4. Verifies that pods can be scheduled after preemption.
5. Selects the optimal preemption strategy.
6. Sets the selected node as the pod's nominatedNodeName.
7. Preempted pods undergo graceful termination.
8. After victims terminate, scheduling is retried; nomination does not guarantee binding.

**Monitoring preemption-related metrics:**
```bash
# Inspect nominations; scheduler metrics require its authenticated HTTPS endpoint.
kubectl get pods -A -o custom-columns=NAME:.metadata.name,NOMINATED:.status.nominatedNodeName
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

A. Give higher scores to nodes with balanced requested CPU and memory fractions
B. Give higher scores to nodes with lower resource usage
C. Give higher scores to nodes with higher resource usage
D. Set resource limits on nodes

<details>
<summary>Show Answer</summary>

**Answer: A. Give higher scores to nodes with balanced requested CPU and memory fractions**

**Explanation:**
`NodeResourcesBalancedAllocation` balances **effective requested/allocatable fractions**, not measured CPU/memory utilization. For two included resources in the pinned implementation:

```
cpuFraction = min(requestedCPU / allocatableCPU, 1)
memoryFraction = min(requestedMemory / allocatableMemory, 1)
std = abs(cpuFraction - memoryFraction) / 2
score = int((1 - std) * 100)
```

The requested totals include the incoming Pod and the scheduler's accounted requests. The full plugin also handles its version-specific resource options. For more than two included resources, it uses population standard deviation.

Illustrative arithmetic, not measurements: fractions80%/80% give100;90%/50% give80;30%/90% give70. Other plugins and weights also affect node selection.

**Enabling NodeResourcesBalancedAllocation plugin in scheduler configuration:**
```yaml
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
profiles:
- schedulerName: custom-scheduler
  plugins:
    score:
      enabled:
      - name: NodeResourcesBalancedAllocation
        weight: 2
leaderElection:
  leaderElect: true
  resourceLock: leases
  resourceName: custom-scheduler
  resourceNamespace: scheduler-lab
  leaseDuration: 15s
  renewDeadline: 10s
  retryPeriod: 2s
```

**Plugin configuration:**
```yaml
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
profiles:
- schedulerName: custom-scheduler
  pluginConfig:
  - name: NodeResourcesBalancedAllocation
    args:
      resources:
      - name: cpu
        weight: 1
      - name: memory
        weight: 1
leaderElection:
  leaderElect: true
  resourceLock: leases
  resourceName: custom-scheduler
  resourceNamespace: scheduler-lab
  leaseDuration: 15s
  renewDeadline: 10s
  retryPeriod: 2s
```

**NodeResourcesBalancedAllocation vs other scoring plugins:**
1. **NodeResourcesBalancedAllocation**: Prefers balanced requested/allocatable fractions.
2. **NodeResourcesFit**: Uses its configured LeastAllocated, MostAllocated or RequestedToCapacityRatio scoring strategy.
3. **LeastAllocated strategy of NodeResourcesFit**: Prefers lower requested fractions.
4. **MostAllocated strategy of NodeResourcesFit**: Prefers higher requested fractions.

**Use cases:**
1. **Resource balance**: Improves CPU and memory usage balance across the entire cluster.
2. **Bottleneck prevention**: Can reduce imbalance in requested resources; it does not prevent runtime bottlenecks.
3. **Scalability improvement**: Clusters with balanced resource usage can scale more efficiently.

**Arithmetic helper (`scoring/formulas.go`):**
This checks the formula and the optional70:30 GPU weighting described in the source chapter. It is not a complete scheduler plugin. Keep the built-in resource accounting, including CPU millicores, init/sidecar containers, overhead and feature-specific handling.

```go
package scoring

import (
	"fmt"
	"math"
)

// Two-resource form of the pinned BalancedAllocation formula.
// Inputs are effective requested/allocatable fractions, not live utilization.
func BalancedScore(cpuFraction, memoryFraction float64) (int64, error) {
	for _, value := range []float64{cpuFraction, memoryFraction} {
		if math.IsNaN(value) || math.IsInf(value, 0) || value < 0 {
			return 0, fmt.Errorf("fractions must be finite and non-negative")
		}
	}
	cpuFraction = math.Min(cpuFraction, 1)
	memoryFraction = math.Min(memoryFraction, 1)
	std := math.Abs(cpuFraction-memoryFraction) / 2
	return int64((1 - std) * 100), nil
}

// Optional policy arithmetic only; no GPU telemetry collector is implemented here.
// The caller must establish freshness and workload/device relevance first.
func WeightedGPUScore(packing int64, utilization float64) (int64, error) {
	if packing < 0 || packing > 100 || math.IsNaN(utilization) || math.IsInf(utilization, 0) || utilization < 0 || utilization > 1 {
		return 0, fmt.Errorf("packing must be 0..100 and utilization finite in 0..1")
	}
	utilizationScore := int64((1 - utilization) * 100)
	return (packing*7 + utilizationScore*3) / 10, nil
}
```

**Issues with other options:**
- B. Give higher scores to nodes with lower resource usage: This is the LeastAllocated strategy of NodeResourcesFit.
- C. Give higher scores to nodes with higher resource usage: This is the MostAllocated strategy of NodeResourcesFit.
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
PreBind coordinates prerequisites before the Pod binding commits. `VolumeBinding` handles scheduling-related volume binding/provisioning coordination with storage controllers. There is no default plugin named `DefaultPreBind`.

The1.35.8 interface includes **both** `PreBindPreFlight` and `PreBind`, using `fwk.CycleState`. Preflight can return Skip for a Pod to avoid unnecessary work.

**Complete read-only demonstration (`quizplugins/prebind.go`):**
This opt-in identity check does not provision volumes, configure CNI, create service endpoints or allocate GPUs. Those require their actual controllers/device mechanisms. `DefaultBinder` already carries the UID, so this extra round trip is only an interface example.

```go
package quizplugins

import (
	"context"
	"fmt"
	"time"

	v1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
	fwk "k8s.io/kube-scheduler/framework"
)

type IdentityPreBind struct{ handle fwk.Handle }

var _ fwk.PreBindPlugin = &IdentityPreBind{}

func (*IdentityPreBind) Name() string { return "IdentityPreBind" }

func (*IdentityPreBind) PreBindPreFlight(_ context.Context, _ fwk.CycleState, pod *v1.Pod, _ string) *fwk.Status {
	if pod.Annotations["training.example.com/check-identity"] != "true" {
		return fwk.NewStatus(fwk.Skip)
	}
	return nil
}

// Read-only interface demonstration. DefaultBinder already carries the Pod UID;
// this extra API round trip is not required for ordinary scheduling.
func (p *IdentityPreBind) PreBind(parent context.Context, _ fwk.CycleState, pod *v1.Pod, _ string) *fwk.Status {
	ctx, cancel := context.WithTimeout(parent, 3*time.Second)
	defer cancel()
	current, err := p.handle.ClientSet().CoreV1().Pods(pod.Namespace).Get(ctx, pod.Name, metav1.GetOptions{})
	if err != nil {
		return fwk.AsStatus(err)
	}
	if current.UID != pod.UID || current.DeletionTimestamp != nil || current.Spec.NodeName != "" {
		return fwk.AsStatus(fmt.Errorf("Pod identity/state changed before binding"))
	}
	return nil
}

func NewPreBind(_ context.Context, _ runtime.Object, handle fwk.Handle) (fwk.Plugin, error) {
	return &IdentityPreBind{handle: handle}, nil
}
```

The question2 command registers it. Keep `VolumeBinding` enabled:

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
    preBind:
      enabled:
      - name: IdentityPreBind
```

**Responsibility boundaries:**
Storage provisioning is performed by the relevant provisioner/controller; the scheduler coordinates placement and binding. CNI networking and Secret/volume mounts occur through runtime/kubelet mechanisms after assignment. Service/EndpointSlice/load-balancer controllers reconcile their own resources. If a custom plugin coordinates an external reservation, it must implement bounded, idempotent operations and its own Unreserve cleanup; the framework cannot undo arbitrary external side effects automatically.

**PreBind failure handling:**
When a PreBind plugin returns failure:
1. The scheduling cycle is aborted.
2. The pod goes back to the scheduling queue.
3. Unreserve hooks undo plugin-owned assumptions; external cleanup must actually be implemented.
4. Failure events are logged.

**Monitoring PreBind logs and events:**
```bash
# Check PreBind-related messages in scheduler logs
kubectl -n scheduler-lab logs -l app=custom-scheduler --prefix --tail=100

# Check pod events
kubectl describe pod <pod-name>
```

**Issues with other options:**
- A. Bind pods to nodes: This is the role of the "Bind" extension point.
- C. Perform cleanup after binding: This is the role of the "PostBind" extension point.
- D. Recovery after failure includes Unreserve for plugin-owned reservations and framework retry handling.
</details>

### 8. What is the main purpose of the "NodeResourcesFit" plugin in the Kubernetes scheduler?

A. Monitor node resource usage
B. Set node resource limits
C. Compare remaining allocatable resources with effective Pod requests
D. Maintain node resource usage balance

<details>
<summary>Show Answer</summary>

**Answer: C. Compare remaining allocatable resources with effective Pod requests**

**Explanation:**
`NodeResourcesFit` compares effective Pod requests with allocatable resources **minus assigned/assumed requests**, including applicable Pod-count and extended-resource constraints. It does not generally check the sum of CPU/memory limits against capacity. Requests derived by admission/defaulting, init containers, restartable sidecars, overhead and enabled resource features must be accounted for.

Keep the default Filter stage. The configuration changes scoring behavior without replacing resource-fit logic.

**NodeResourcesFit plugin configuration:**
```yaml
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
profiles:
- schedulerName: custom-scheduler
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
leaderElection:
  leaderElect: true
  resourceLock: leases
  resourceName: custom-scheduler
  resourceNamespace: scheduler-lab
  leaseDuration: 15s
  renewDeadline: 10s
  retryPeriod: 2s
```

**Scoring strategies:**
The NodeResourcesFit plugin supports the following scoring strategies:

1. **LeastAllocated**: Gives higher scores to nodes with lower requested fractions.
   ```
   score ≈ 100 × (allocatable - requested) / allocatable
   ```

2. **MostAllocated**: Gives higher scores to nodes with higher requested fractions.
   ```
   score ≈ 100 × requested / allocatable
   ```

3. **RequestedToCapacityRatio**: Uses a configured piecewise-linear shape over requested/allocatable ratios. The formulas above are simplified single-resource examples.

**Custom implementation caution:**
Keep upstream `NodeResourcesFit`. Checking only resources listed in a scoring-weight map can omit a required resource, and CPU `Quantity.Value()` loses millicore precision. A sum of ordinary container requests misses init/sidecar/overhead behavior. A hand-written score that truncates fractions before scaling may produce only zeros.

Part1's local check exercises the actual pinned fit function: with1500m already requested on a2-core node, another1-core request does not fit, while250m fits even with larger CPU limits. That is a synthetic accounting test, not a cluster benchmark.

**Resource request and limit example:**
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: resource-demo
spec:
  containers:
  - name: nginx
    image: nginx:1.30.4
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
    image: nginx:1.30.4
```

**InterPodAffinity plugin configuration:**
```yaml
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
profiles:
- schedulerName: custom-scheduler
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
        weight: 2
  pluginConfig:
  - name: InterPodAffinity
    args:
      hardPodAffinityWeight: 1
leaderElection:
  leaderElect: true
  resourceLock: leases
  resourceName: custom-scheduler
  resourceNamespace: scheduler-lab
  leaseDuration: 15s
  renewDeadline: 10s
  retryPeriod: 2s
```

**Use the complete built-in implementation:**
Retain `InterPodAffinity` and its preprocessing. It accounts for namespace selection, incoming required terms, existing Pods' required anti-affinity, topology and self-affinity bootstrap behavior. A raw `*v1.Affinity` is not framework StateData with Clone, and missing state must not silently bypass required checks.

In this example, a suitable `app=cache` Pod must exist in the selected namespace. Preferred anti-affinity does not guarantee separation. `hardPodAffinityWeight` affects scoring and does not relax required constraints. Test scale and placement tradeoffs with actual workloads; co-location does not prove a latency minimum.

**Pod affinity and anti-affinity use cases:**
1. **High availability**: Distribute instances of the same application across different nodes, zones, or regions
2. **Performance optimization**: Co-locate communicating Pods where measurements support the contention/latency tradeoff
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
The main purpose of the "NodeName" plugin in the Kubernetes scheduler is to verify that the pod's `spec.nodeName` field matches the node name. If invoked with a nonempty nodeName, its predicate only accepts that name. In normal operation, preassigned Pods are already excluded from the unscheduled queue; the plugin itself does not cause the bypass.

**Key functions of the NodeName plugin:**
1. **Node name verification**: If the pod's `spec.nodeName` field is set, only nodes with matching names are selected.
2. **Field semantics**: spec.nodeName directly names the node; it is not a scheduler selection field.
3. **Scheduler bypass**: Pods with `spec.nodeName` set bypass normal scheduling logic and are directly assigned to the specified node.

**Predicate equivalent to the name check:**
This helper illustrates the built-in check; do not register a replacement named `NodeName`.

```go
package quizplugins

import v1 "k8s.io/api/core/v1"

// Equivalent name predicate for explanation; not a replacement scheduler.
func NodeNameMatches(pod *v1.Pod, node *v1.Node) bool {
	if pod == nil || node == nil {
		return false
	}
	return pod.Spec.NodeName == "" || pod.Spec.NodeName == node.Name
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
    image: nginx:1.30.4
```

**Considerations when using nodeName:**
1. **Scheduler bypass**: Using `nodeName` bypasses the scheduler's filtering, scoring, and other logic.
2. **Node existence**: A wrong/missing node name does not trigger selection of an alternative node.
3. **Admission remains**: Scheduler fit checks are bypassed, but kubelet admission can still reject the Pod for insufficient resources.
4. **Remaining constraints**: NoSchedule/affinity scheduling checks are bypassed, but NoExecute and node-side admission still apply. WaitForFirstConsumer PVCs can remain Pending because scheduler volume coordination was skipped.

The `kubernetes.io/hostname` label is not required to equal the Node object name. Inspect its actual value before using the label examples below.

**nodeName vs nodeSelector vs nodeAffinity:**
1. **nodeName**: Directly assigns to a specific node. Most restrictive and least flexible.
2. **nodeSelector**: Selects nodes based on labels. Simple but limited expressiveness.
3. **nodeAffinity**: Supports complex node selection rules. Most flexible and expressive.

**nodeName use cases:**
1. **Debugging**: Run pods on specific nodes for debugging issues.
2. **Testing**: Run tests on specific nodes.
3. **Special hardware**: Assign pods to nodes with specific hardware.
4. **Static Pod distinction**: An API-created Pod with nodeName is not a static Pod; static Pods come from kubelet-local configuration.

**Cautions when using nodeName:**
1. **Replacement behavior**: Pods do not move. A controller may create replacements, but a template pinned to the same failed name still constrains them.
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
       image: nginx:1.30.4
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
       image: nginx:1.30.4
   ```

**Issues with other options:**
- B. Assign names to nodes: Node names are assigned at node creation and are not the role of scheduler plugins.
- C. Assign node names to pods: This is performed in the scheduler's binding phase, not by the NodeName plugin.
- D. Validate node name format: This is performed by API server validation logic, not by scheduler plugins.
</details>

### 11. Which controller uses Pod Deletion Cost as a scale-down preference?

A. StatefulSet ordinal deletion
B. ReplicaSet, including those owned by Deployments
C. Deletion of any standalone Pod
D. A global scheduler that ranks all Pods across Deployments

<details>
<summary>Show Answer</summary>

**Answer: B. ReplicaSet, including those owned by Deployments**

The annotation is compared within one ReplicaSet and is best effort. Missing means0 and signed int32 values, including negatives, are valid. Assignment, phase and readiness can take precedence, so a high-cost unready Pod can be removed before a lower-cost ready Pod. The feature was alpha in1.21 and beta/default-on since1.22.
</details>

### 12. Which deletion-cost update pattern matches the source chapter?

A. A high cost and PDB guarantee a replica survives ordinary scale-down
B. Replace the whole Pod on every incoming request
C. Patch only the cost at coarse transitions, check the Pod UID and reject stale metrics
D. Treat unavailable metrics as zero activity and immediately lower the cost

<details>
<summary>Show Answer</summary>

**Answer: C. Patch only the cost at coarse transitions, check the Pod UID and reject stale metrics**

Use a single authorized writer, bounded requests and a minimal annotation patch. A UID test prevents accidentally patching a new Pod with the same name. A server dry run of scale does not predict which Pods will be deleted. Ordinary ReplicaSet scale-down directly deletes Pods and is not blocked by a PDB; application draining/readiness and recovery still matter.
</details>

## References

The code uses the [Part1 module](../../scheduling/01-custom-scheduler-part1.md). Local code/configuration tests do not establish a deployed approval system, gang workload, GPU execution or production readiness.

* [Scheduling framework](https://kubernetes.io/docs/concepts/scheduling-eviction/scheduling-framework/)
* [Pinned framework interfaces](https://github.com/kubernetes/kubernetes/blob/v1.35.8/staging/src/k8s.io/kube-scheduler/framework/interface.go)
* [Scheduler configuration](https://kubernetes.io/docs/reference/scheduling/config/)
* [Native PodGroup scheduling](https://kubernetes.io/docs/concepts/scheduling-eviction/podgroup-scheduling/)
* [PodGroup policies](https://kubernetes.io/docs/concepts/workloads/workload-api/policies/)
* [Volcano Job](https://volcano.sh/en/docs/vcjob/)
* [Volcano 1.15.2 Job CRD](https://github.com/volcano-sh/volcano/blob/v1.15.2/config/crd/volcano/bases/batch.volcano.sh_jobs.yaml)
* [BalancedAllocation scorer](https://github.com/kubernetes/kubernetes/blob/v1.35.8/pkg/scheduler/framework/plugins/noderesources/balanced_allocation.go)
* [Node assignment](https://kubernetes.io/docs/concepts/scheduling-eviction/assign-pod-node/)
* [ReplicaSet deletion cost](https://kubernetes.io/docs/concepts/workloads/controllers/replicaset/#pod-deletion-cost)
