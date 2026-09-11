# Custom Scheduler

> **Example Baseline**: Kubernetes 1.35.8, Go 1.27.1
> **Last Updated**: September 11, 2026

The Kubernetes scheduler is a critical component that decides which node a pod should be placed on. While the default scheduler works well in most cases, you can implement a custom scheduler for specific requirements. In this chapter, we will learn how to implement a custom scheduler in EKS.

## Lab Environment Setup

To follow along with the examples in this document, you will need the following tools and environment:

### Required Tools

* kubectl within one minor version of the cluster's API server
* Go 1.27.1 and Python 3 for the reproducible example below
* A disposable Kubernetes 1.35 cluster with Linux worker nodes; for EKS, first check the [AWS version calendar](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html)

The framework interfaces and configuration here were checked against Kubernetes **1.35.8**. This is an example baseline, not a claim that it is the latest Kubernetes or EKS release. Match the scheduler to the cluster minor and revalidate plugins, feature gates and RBAC when upgrading. The Kubernetes module uses staging dependencies; a lone `go get k8s.io/kubernetes` does not resolve its `v0.0.0` staging requirements.

### Development Environment Setup

```bash
mkdir -p custom-scheduler
cd custom-scheduler

# Generate a standalone module from the pinned upstream staging-module list.
python3 - <<'PY'
from pathlib import Path
import re
from urllib.request import urlopen

version = "v1.35.8"
staging_version = "v0.35.8"
url = f"https://raw.githubusercontent.com/kubernetes/kubernetes/{version}/go.mod"
with urlopen(url, timeout=30) as response:
    upstream = response.read().decode()
modules = re.findall(r"^\s*(k8s\.io/[\w-]+) => \./staging/src/\1\s*$", upstream, re.M)
if not modules:
    raise RuntimeError("No staging modules found; review upstream go.mod")
text = f"module example.com/custom-scheduler\n\ngo 1.27.1\n\nrequire k8s.io/kubernetes {version}\n\nreplace (\n"
text += "".join(f"\t{m} => {m} {staging_version}\n" for m in modules)
Path("go.mod").write_text(text + ")\n")
PY
```

## Scheduling Overview

### Kubernetes Scheduling Process

The Kubernetes scheduling process consists of the following stages:

### Detailed Explanation of Scheduling Stages

1. **Filtering Phase**
   * The stage where suitable nodes for running the pod are identified
   * Each filter plugin determines whether a node can host the pod
   * If any filter fails, that node is excluded from candidates
2. **Scoring Phase**
   * The stage where filtered nodes are assigned scores
   * Each scoring plugin returns a 0–100 score after optional normalization
   * Final scores are calculated by applying weights
3. **Binding Phase**
   * The stage where the pod is assigned to the highest-scoring node
   * Pod-node binding information is updated through the Kubernetes API

## When Custom Schedulers Are Needed

Consider a custom scheduler in the following cases:

1. **Special Hardware Requirements**: GPUs, FPGAs, special network devices, etc.
2. **Complex Workload Placement Rules**: Placing specific workloads on specific node groups
3. **Cost Optimization**: Optimal placement between spot and on-demand instances
4. **Locality Requirements**: Workload placement considering data locality
5. **Multi-Scheduler Scenarios**: Using multiple schedulers for different workload types

### Real-World Use Cases

| Industry           | Use Case                       | Custom Scheduler Benefits                                 |
| ------------------ | ------------------------------ | --------------------------------------------------------- |
| Finance            | High-frequency trading systems | Network topology-aware placement for latency minimization |
| Healthcare         | Medical image processing       | GPU-aware placement and data-locality preferences     |
| Telecommunications | 5G network functions           | Placement constraints for labeled network devices           |
| Retail             | Seasonal traffic handling      | Cost-effective spot instance utilization optimization     |
| Media              | Video transcoding              | CPU/GPU node selection based on workload characteristics  |

1. **Filtering**: Identifies nodes where the pod can run. This stage considers resource requirements, node selectors, node affinity, taints and tolerations, etc.
2. **Scoring**: Scores the filtered nodes. This stage considers node resource usage, inter-pod affinity, node affinity, etc.
3. **Binding**: Assigns the pod to the highest-scoring node.

Before writing code, check whether device plugins, required/preferred affinity, taints/tolerations and topology spread already express the requirement. Ordinary GPU requests do not require a custom scheduler.

### Limitations of the Default Scheduler

The default scheduler may have the following limitations:

1. **Specific Hardware Requirements**: Advanced scheduling logic may be needed for special hardware like GPUs, FPGAs.
2. **Complex Affinity Rules**: There may be complex placement constraints that are difficult to express with basic affinity rules.
3. **Custom Metrics**: Scheduling may need to be based on custom metrics that the default scheduler doesn't consider.
4. **Domain-Specific Knowledge**: Scheduling logic specialized for specific application domains may be required.

## Custom Scheduler Implementation Methods

There are three main approaches to implementing a custom scheduler:

1. **Multiple Scheduler Approach**: Run a custom scheduler alongside the default scheduler.
2. **Scheduler Extender Approach**: Extend the default scheduler to provide additional filtering and priority functions.
3. **Scheduler Framework Plugins**: Develop plugins using the scheduler framework introduced in Kubernetes 1.15.

### Multiple Scheduler Approach

In the multiple scheduler approach, a custom scheduler runs alongside the default scheduler. When creating a pod, you can specify which scheduler to use with the `schedulerName` field.

#### Custom Scheduler Implementation

Use the upstream scheduler command as the base of a secondary scheduler. This retains `NodeResourcesFit`, `TaintToleration`, `NodeAffinity`, `VolumeBinding` and the other default plugins. Selecting the first Ready node and calling the binding API would bypass those checks.

Save this as `main.go`. It adds no custom placement policy yet; the later scoring helpers and quiz show extension points.

```go
package main

import (
    "os"

    "k8s.io/component-base/cli"
    "k8s.io/kubernetes/cmd/kube-scheduler/app"
)

func main() {
    os.Exit(cli.Run(app.NewSchedulerCommand()))
}
```

#### Custom Scheduler Deployment

Save the following `Dockerfile`, run the local build commands, and publish the image through your approved registry workflow. Replace `registry.example.com/...` in the manifest with that image, preferably pinned by digest. The binary and image must match the worker architecture.

```dockerfile
FROM gcr.io/distroless/static-debian12:nonroot
COPY custom-scheduler /custom-scheduler
ENTRYPOINT ["/custom-scheduler"]
```

```bash
go mod tidy
CGO_ENABLED=0 go build -buildvcs=false -trimpath -o custom-scheduler .
# Build for the same architecture as the scheduler's worker nodes.
docker build -t custom-scheduler:v1.35.8-1 .
```

This is a lab deployment, not a production-tested HA recipe. The scheduler Pods themselves use `default-scheduler` so they can start before `custom-scheduler` is available. Both replicas share **one** Lease in `scheduler-lab`; another scheduler group needs a different Lease. Preferred anti-affinity improves placement but does not guarantee host or AZ separation.

The administrator must verify the referenced bootstrap RBAC roles exist. `system:kube-scheduler` and `system:volume-scheduler` grant powerful cluster-wide scheduling permissions, including binding and preemption; `schedulerName` is not a security boundary. The separate Role adds access to our Lease without changing Kubernetes' bootstrap roles. Keep the HTTPS endpoint private. Resource sizing and failure behavior need testing on the target cluster.

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: scheduler-lab
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: custom-scheduler
  namespace: scheduler-lab
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: scheduler-lab-scheduling
subjects:
- kind: ServiceAccount
  name: custom-scheduler
  namespace: scheduler-lab
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: system:kube-scheduler
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: scheduler-lab-volumes
subjects:
- kind: ServiceAccount
  name: custom-scheduler
  namespace: scheduler-lab
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: system:volume-scheduler
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: scheduler-lab-authentication
  namespace: kube-system
subjects:
- kind: ServiceAccount
  name: custom-scheduler
  namespace: scheduler-lab
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: extension-apiserver-authentication-reader
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: custom-scheduler-leader-election
  namespace: scheduler-lab
rules:
- apiGroups: ["coordination.k8s.io"]
  resources: ["leases"]
  verbs: ["create"]
- apiGroups: ["coordination.k8s.io"]
  resources: ["leases"]
  resourceNames: ["custom-scheduler"]
  verbs: ["get", "update", "patch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: custom-scheduler-leader-election
  namespace: scheduler-lab
subjects:
- kind: ServiceAccount
  name: custom-scheduler
  namespace: scheduler-lab
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: custom-scheduler-leader-election
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: custom-scheduler-config
  namespace: scheduler-lab
data:
  config.yaml: |
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
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: custom-scheduler
  namespace: scheduler-lab
spec:
  replicas: 2
  selector:
    matchLabels:
      app: custom-scheduler
  template:
    metadata:
      labels:
        app: custom-scheduler
    spec:
      serviceAccountName: custom-scheduler
      securityContext:
        runAsUser: 65532
        runAsGroup: 65532
        fsGroup: 65532
      nodeSelector:
        kubernetes.io/os: linux
      affinity:
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 100
            podAffinityTerm:
              topologyKey: kubernetes.io/hostname
              labelSelector:
                matchLabels:
                  app: custom-scheduler
      containers:
      - name: custom-scheduler
        image: registry.example.com/training/custom-scheduler:v1.35.8-1
        args:
        - --config=/etc/scheduler/config.yaml
        - --cert-dir=/tmp
        ports:
        - name: https
          containerPort: 10259
        livenessProbe:
          httpGet:
            path: /healthz
            port: https
            scheme: HTTPS
          initialDelaySeconds: 15
        securityContext:
          runAsNonRoot: true
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop: ["ALL"]
          seccompProfile:
            type: RuntimeDefault
        resources:
          requests:
            cpu: 100m
            memory: 256Mi
          limits:
            memory: 512Mi
        volumeMounts:
        - name: config
          mountPath: /etc/scheduler
          readOnly: true
        - name: tmp
          mountPath: /tmp
      volumes:
      - name: config
        configMap:
          name: custom-scheduler-config
      - name: tmp
        emptyDir: {}
```

#### Using the Custom Scheduler

When creating a pod, use the `schedulerName` field to specify the custom scheduler:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: nginx
spec:
  schedulerName: custom-scheduler
  containers:
  - name: nginx
    image: nginx:1.30.4
    resources:
      requests:
        cpu: 100m
        memory: 64Mi
      limits:
        memory: 128Mi
```

## Custom Scheduler Implementation in EKS

When implementing a custom scheduler in Amazon EKS, consider the following:

1. **Kubernetes authentication and authorization**: An in-cluster scheduler uses its ServiceAccount token and Kubernetes RBAC. IAM is additionally needed only if it calls AWS APIs, such as EC2 or CloudWatch; grant that workload identity only the required AWS permissions.
2. **Managed control plane**: Run your own secondary scheduler on worker nodes. Do not assume access to the managed default scheduler's process, flags or plugin registry.
3. **Compute boundaries**: This example targets EC2 worker nodes. [EKS Fargate uses AWS-managed scheduling and admission controllers](https://docs.aws.amazon.com/eks/latest/userguide/fargate.html); selecting a Fargate node or setting `custom-scheduler` does not provision Fargate capacity.
4. **Topology and instance labels**: Use existing node labels, resource requests, affinity and topology spread first. A custom scheduler does not create capacity or guarantee latency.

### EKS Custom Scheduler Architecture

Each scheduler watches the Kubernetes API and maintains its **own cache and queue** for matching Pods. The API server stores and exposes Pod state; it does not own a shared scheduling queue. EC2/CloudWatch integration is optional, and slow or failed metric queries require bounded timeouts and an explicit fallback policy.

### EKS-Specific Scheduling Considerations

The following functions are **illustrative soft scoring helpers**, saved as separate files in a `preferences` package. They are not automatically registered in the binary above. Call them from a tested framework `Score` plugin only after the default filters pass. A score of **0 still leaves a node eligible**; mandatory rules belong in filters or required affinity. Keep scores in 0–100.

#### 1. Instance Type-Aware Scheduling

The c5/m5/r5 weights below demonstrate label-based preferences. They are neither measured performance rankings nor recommendations to buy those generations. For an actual workload, benchmark suitable instance types and configure the preference explicitly.

```go
package preferences

import (
	"strings"

	v1 "k8s.io/api/core/v1"
)

// Illustrative weights, not measured performance or current purchase advice.
func ScoreInstanceType(node *v1.Node) int64 {
	switch {
	case strings.HasPrefix(node.Labels["node.kubernetes.io/instance-type"], "c5."):
		return 100
	case strings.HasPrefix(node.Labels["node.kubernetes.io/instance-type"], "m5."):
		return 50
	case strings.HasPrefix(node.Labels["node.kubernetes.io/instance-type"], "r5."):
		return 30
	default:
		return 10
	}
}
```

#### 2. Availability Zone Distribution Scheduling

Prefer the built-in `PodTopologySpread` plugin and `topologySpreadConstraints`. If custom scoring is necessary, build a consistent cycle snapshot from the scheduler cache, restricted to the intended workload and all eligible zones, including zones with zero Pods. Include assigned/assumed Pods as appropriate; counting only Running Pods misses reservations. Do not make one API list/get sequence per candidate node or turn API errors into invented counts.

```go
package preferences

import (
	"fmt"

	v1 "k8s.io/api/core/v1"
)

// counts is a consistent snapshot for one workload, including empty eligible zones.
// Build it once per scheduling cycle, not by making API calls for every node.
func ScoreAZ(node *v1.Node, counts map[string]int) (int64, error) {
	zone := node.Labels["topology.kubernetes.io/zone"]
	count, ok := counts[zone]
	if zone == "" || !ok {
		return 0, fmt.Errorf("missing eligible-zone snapshot for node %q", node.Name)
	}
	maxCount := 0
	for _, n := range counts {
		if n < 0 {
			return 0, fmt.Errorf("negative pod count")
		}
		if n > maxCount {
			maxCount = n
		}
	}
	if maxCount == 0 {
		return 100, nil
	}
	return int64(100 * (maxCount - count) / maxCount), nil
}
```

#### 3. Spot Instance-Aware Scheduling

[EKS managed node groups](https://docs.aws.amazon.com/eks/latest/userguide/managed-node-groups.html) use `eks.amazonaws.com/capacityType` values `SPOT` / `ON_DEMAND`; [Karpenter](https://karpenter.sh/docs/concepts/nodepools/) uses `karpenter.sh/capacity-type` values `spot` / `on-demand` / `reserved`. `node.kubernetes.io/lifecycle` is not a standard equivalent. This helper applies an explicit Pod preference; unknown labels remain neutral. Use required affinity when a capacity type is mandatory. Spot pricing or interruption tolerance cannot be inferred from a score.

```go
package preferences

import v1 "k8s.io/api/core/v1"

func ScoreCapacityType(node *v1.Node, pod *v1.Pod) int64 {
	preferred := pod.Labels["lifecycle-preference"]
	if preferred != "spot" && preferred != "on-demand" {
		return 50
	}
	actual := node.Labels["karpenter.sh/capacity-type"]
	if actual == "" {
		switch node.Labels["eks.amazonaws.com/capacityType"] {
		case "SPOT":
			actual = "spot"
		case "ON_DEMAND":
			actual = "on-demand"
		}
	}
	if actual != "spot" && actual != "on-demand" && actual != "reserved" {
		return 50
	}
	if actual == preferred {
		return 100
	}
	return 0
}
```

#### 4. GPU Workload Scheduling

A device plugin must advertise the GPU resource and the admitted Pod must request it. For extended resources, a limit without a request is defaulted to the same request; a request of zero is not GPU demand. `NodeResourcesFit` checks effective requests against allocatable resources minus existing/assumed requests. `Capacity` alone does not show free GPUs.

This helper only discourages non-GPU workloads from occupying GPU-capable nodes. It uses the versioned resource helper, including init/sidecar/overhead accounting, and assumes an API-defaulted Pod. It does **not** establish GPU eligibility, handle every DRA resource model, or replace the default resource filter.

```go
package preferences

import (
	v1 "k8s.io/api/core/v1"
	resourcehelper "k8s.io/component-helpers/resource"
)

// pod must be API-defaulted; limits-only extended resources acquire requests.
// NodeResourcesFit still decides whether the effective request fits.
func ScoreGPU(node *v1.Node, pod *v1.Pod) int64 {
	requests := resourcehelper.PodRequests(pod, resourcehelper.PodResourcesOptions{})
	gpuRequest := requests[v1.ResourceName("nvidia.com/gpu")]
	if gpuRequest.Sign() > 0 {
		return 50
	}
	gpuAllocatable := node.Status.Allocatable[v1.ResourceName("nvidia.com/gpu")]
	if gpuAllocatable.Sign() > 0 {
		return 0
	}
	return 100
}
```

## Conclusion

In this chapter, we covered an overview of the Kubernetes scheduling process and how to implement a custom scheduler using the multiple scheduler approach. We also explored considerations for implementing custom schedulers in EKS clusters.

In the next chapter, we will learn about implementing custom schedulers using the scheduler extender approach and scheduler framework plugins.

## Verification and References

The Go command, plugins and configuration are checked locally against the pinned dependency versions. No cluster deployment, image push, AWS call, placement benchmark or HA failover test was performed for this audit.

* [Configure multiple schedulers](https://kubernetes.io/docs/tasks/extend-kubernetes/configure-multiple-schedulers/) — architecture/RBAC pattern; its old image/build examples are not version guidance
* [Scheduler configuration](https://kubernetes.io/docs/reference/scheduling/config/)
* [Scheduling framework](https://kubernetes.io/docs/concepts/scheduling-eviction/scheduling-framework/)
* [Kubernetes 1.35.8 framework interfaces](https://github.com/kubernetes/kubernetes/blob/v1.35.8/staging/src/k8s.io/kube-scheduler/framework/interface.go)
* [Kubernetes 1.35.8 default plugins](https://github.com/kubernetes/kubernetes/blob/v1.35.8/pkg/scheduler/apis/config/v1/default_plugins.go)

## Quiz

To test what you've learned in this chapter, try the [Topic Quiz](../quizzes/scheduling/02-custom-scheduler-part1-quiz.md).
