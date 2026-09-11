# Part 2: Implementation

> **Example Baseline**: Kubernetes 1.35.8, Go 1.27.1
> **Last Updated**: September 11, 2026

Use the [Part1 module setup and complete secondary-scheduler RBAC/Deployment](01-custom-scheduler-part1.md). These are two alternative extension methods for that scheduler. The examples were checked locally; no EKS deployment, GPU execution, TLS rollout or production failover was tested. Revalidate other Kubernetes minors rather than assuming Go-interface compatibility.

## Scheduler Extender Approach

The scheduler extender approach is a way to extend the functionality of the default scheduler. In this approach, the default scheduler calls an external service (scheduler extender) via HTTP requests to provide additional filtering and priority functions.

### Scheduler Extender Architecture

An extender runs as a separate service called by the scheduler. On EKS, configure the secondary scheduler from Part1.

### Scheduler Extender Workflow

The scheduler extender workflow is as follows:

![Sequence diagram showing a scheduler observing Pod state through the API, which runs internal filtering and scoring, delegates a filter and a prioritize HTTP call to a scheduler extender, then selects a node, requests binding, and schedules the pod on that node.](../.gitbook/assets/en-scheduling-02-custom-scheduler-part2-0.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-scheduling-02-custom-scheduler-part2-0.html)

### Scheduler Extender Implementation

An extender implements the configured subset of **filter**, **prioritize**, **preempt** and **bind** HTTP callbacks. Filter and priority are the only callbacks in this example. There are no extender `PreFilter` or `PreScore` HTTP hooks; those are in-process framework extension points. Leave `bindVerb` unset to retain the default binder.

Extender priorities are **0–10**, whereas framework scores are **0–100** after normalization. Keep mandatory constraints in Filter: in this pinned scheduler version, a failed prioritization request is logged and its scores are omitted; it is not a reliable enforcement point.

The scheduler watches the API and owns its queue/cache. It applies built-in filters before extender filtering, and combines extender preferences with framework scores. The API server does not push a Pod into a shared queue.

This example adds a **declared per-GPU memory condition** while preserving upstream resource-fit checks. It does not discover GPUs, measure free VRAM or reserve device memory.

The shared policy assumes API-defaulted Pods, an installed device plugin, homogeneous GPUs without MIG/time-slicing, and an administrator-maintained `training.example.com/gpu-memory-mib` node label describing the minimum memory of each eligible GPU. These are **lab-specific keys**, not standard NVIDIA discovery labels. Validate the inventory before labeling; use a device-aware allocation mechanism for heterogeneous/shared GPUs. A node label alone cannot guarantee the characteristics of the device assigned later.

Save the following files in the Part1 module.

**`gpupolicy/policy.go`**

```go
package gpupolicy

import (
	"fmt"
	"strconv"

	v1 "k8s.io/api/core/v1"
	resourcehelper "k8s.io/component-helpers/resource"
)

const (
	MinMemoryAnnotation = "training.example.com/min-gpu-memory-mib"
	NodeMemoryLabel     = "training.example.com/gpu-memory-mib"
	ScoreCeilingMiB     = int64(80 * 1024)
)

// These are lab policy keys, not automatically populated NVIDIA labels.
// NodeMemoryLabel must describe the minimum memory per eligible GPU on a
// homogeneous, non-shared GPU node, not total or currently free VRAM.
type Requirement struct {
	HasGPU       bool
	MinMemoryMiB int64
}

func FromPod(pod *v1.Pod) (Requirement, error) {
	if pod == nil {
		return Requirement{}, fmt.Errorf("missing pod")
	}
	requests := resourcehelper.PodRequests(pod, resourcehelper.PodResourcesOptions{})
	gpu := requests[v1.ResourceName("nvidia.com/gpu")]
	req := Requirement{HasGPU: gpu.Sign() > 0}
	if raw, exists := pod.Annotations[MinMemoryAnnotation]; exists {
		value, err := strconv.ParseInt(raw, 10, 64)
		if err != nil || value <= 0 || value > 1024*1024 {
			return req, fmt.Errorf("minimum GPU memory must be 1..1048576 MiB")
		}
		if !req.HasGPU {
			return req, fmt.Errorf("minimum GPU memory requires a positive GPU request")
		}
		req.MinMemoryMiB = value
	}
	return req, nil
}

func nodeMemory(node *v1.Node) (int64, error) {
	if node == nil {
		return 0, fmt.Errorf("missing node")
	}
	value, err := strconv.ParseInt(node.Labels[NodeMemoryLabel], 10, 64)
	if err != nil || value <= 0 || value > 1024*1024 {
		return 0, fmt.Errorf("missing or invalid administrator GPU-memory label")
	}
	return value, nil
}

// FitsMemory checks only the declared memory label. The default scheduler
// filters must still check free GPU counts, taints, affinity, volumes, etc.
func FitsMemory(req Requirement, node *v1.Node) (bool, string) {
	if req.MinMemoryMiB == 0 {
		return true, ""
	}
	memory, err := nodeMemory(node)
	if err != nil {
		return false, err.Error()
	}
	if memory < req.MinMemoryMiB {
		return false, "GPU memory label is below the required minimum"
	}
	return true, ""
}

// The 80-GiB ceiling is a chosen scoring scale, not a hardware maximum.
func Score100(req Requirement, node *v1.Node) int64 {
	if !req.HasGPU {
		return 0
	}
	memory, err := nodeMemory(node)
	if err != nil {
		return 0
	}
	if memory >= ScoreCeilingMiB {
		return 100
	}
	return memory * 100 / ScoreCeilingMiB
}
```

**`extenderserver/handler.go`**

The handler accepts the `nodeCacheCapable: false` contract, bounds the lab request to 4 MiB/512 nodes, rejects malformed or missing inputs, and returns only a subset of the supplied candidates. These bounds need sizing for a real cluster. Invalid mandatory memory labels exclude a node; preempting Pods cannot repair the label.

```go
package extenderserver

import (
	"encoding/json"
	"errors"
	"io"
	"net/http"

	"example.com/custom-scheduler/gpupolicy"
	v1 "k8s.io/api/core/v1"
	extender "k8s.io/kube-scheduler/extender/v1"
)

const maxBodyBytes = 4 << 20

func NewHandler() http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("POST /filter", filter)
	mux.HandleFunc("POST /prioritize", prioritize)
	return mux
}

func readArgs(w http.ResponseWriter, r *http.Request) (extender.ExtenderArgs, gpupolicy.Requirement, bool) {
	var args extender.ExtenderArgs
	body := http.MaxBytesReader(w, r.Body, maxBodyBytes)
	defer body.Close()
	decoder := json.NewDecoder(body)
	if err := decoder.Decode(&args); err != nil {
		var large *http.MaxBytesError
		status := http.StatusBadRequest
		if errors.As(err, &large) {
			status = http.StatusRequestEntityTooLarge
		}
		http.Error(w, "invalid or oversized extender request", status)
		return args, gpupolicy.Requirement{}, false
	}
	if err := decoder.Decode(new(any)); err != io.EOF {
		http.Error(w, "expected exactly one JSON object", http.StatusBadRequest)
		return args, gpupolicy.Requirement{}, false
	}
	if args.Pod == nil || args.Nodes == nil || args.NodeNames != nil {
		http.Error(w, "Pod and Nodes required; nodeCacheCapable must be false", http.StatusBadRequest)
		return args, gpupolicy.Requirement{}, false
	}
	if len(args.Nodes.Items) > 512 {
		http.Error(w, "lab candidate-node limit exceeded", http.StatusRequestEntityTooLarge)
		return args, gpupolicy.Requirement{}, false
	}
	seen := make(map[string]bool, len(args.Nodes.Items))
	for _, node := range args.Nodes.Items {
		if node.Name == "" || seen[node.Name] {
			http.Error(w, "missing or duplicate node name", http.StatusBadRequest)
			return args, gpupolicy.Requirement{}, false
		}
		seen[node.Name] = true
	}
	req, err := gpupolicy.FromPod(args.Pod)
	if err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return args, req, false
	}
	return args, req, true
}

func writeJSON(w http.ResponseWriter, value any) {
	data, err := json.Marshal(value)
	if err != nil {
		http.Error(w, "response encoding failed", http.StatusInternalServerError)
		return
	}
	w.Header().Set("Content-Type", "application/json")
	_, _ = w.Write(data)
}

func filter(w http.ResponseWriter, r *http.Request) {
	args, req, ok := readArgs(w, r)
	if !ok {
		return
	}
	result := extender.ExtenderFilterResult{
		Nodes:                      &v1.NodeList{Items: []v1.Node{}},
		FailedAndUnresolvableNodes: extender.FailedNodesMap{},
	}
	for _, node := range args.Nodes.Items {
		if fits, reason := gpupolicy.FitsMemory(req, &node); fits {
			result.Nodes.Items = append(result.Nodes.Items, node)
		} else {
			// Preempting other Pods cannot change a hardware inventory label.
			result.FailedAndUnresolvableNodes[node.Name] = reason
		}
	}
	writeJSON(w, result)
}

func prioritize(w http.ResponseWriter, r *http.Request) {
	args, req, ok := readArgs(w, r)
	if !ok {
		return
	}
	result := make(extender.HostPriorityList, 0, len(args.Nodes.Items))
	for _, node := range args.Nodes.Items {
		result = append(result, extender.HostPriority{
			Host: node.Name, Score: gpupolicy.Score100(req, &node) / 10,
		})
	}
	// The wire response is an array, not a hostPriorities wrapper object.
	writeJSON(w, result)
}
```

**`cmd/extender/main.go`**

The server requires a client certificate signed by the configured client CA. Restrict that CA to scheduler clients and rotate the certificates through your normal secret-management process.

```go
package main

import (
	"crypto/tls"
	"crypto/x509"
	"flag"
	"log"
	"net/http"
	"os"
	"time"

	"example.com/custom-scheduler/extenderserver"
)

func main() {
	certFile := flag.String("tls-cert", "/etc/extender-tls/tls.crt", "server certificate")
	keyFile := flag.String("tls-key", "/etc/extender-tls/tls.key", "server private key")
	caFile := flag.String("client-ca", "/etc/extender-tls/client-ca.crt", "trusted scheduler client CA")
	flag.Parse()
	caPEM, err := os.ReadFile(*caFile)
	if err != nil {
		log.Fatal(err)
	}
	roots := x509.NewCertPool()
	if !roots.AppendCertsFromPEM(caPEM) {
		log.Fatal("client CA contains no certificates")
	}
	server := &http.Server{
		Addr:              ":8443",
		Handler:           extenderserver.NewHandler(),
		ReadHeaderTimeout: 2 * time.Second,
		ReadTimeout:       5 * time.Second,
		WriteTimeout:      5 * time.Second,
		IdleTimeout:       30 * time.Second,
		TLSConfig: &tls.Config{
			MinVersion: tls.VersionTLS12,
			ClientAuth: tls.RequireAndVerifyClientCert,
			ClientCAs:  roots,
		},
	}
	log.Fatal(server.ListenAndServeTLS(*certFile, *keyFile))
}
```

### Scheduler Extender Deployment

Build `./cmd/extender` with the same pinned module and Go version as Part1, package the static binary in a non-root image, and replace the registry placeholder below with the resulting image/digest. The Pod reads all scheduling data from each request, so it needs no Kubernetes API token.

Save the following as `Dockerfile.extender`, then build locally. Select an approved registry and replace the deployment image with the published result.

```dockerfile
FROM gcr.io/distroless/static-debian12:nonroot
COPY scheduler-extender /scheduler-extender
ENTRYPOINT ["/scheduler-extender"]
```

```bash
go mod tidy
CGO_ENABLED=0 go build -buildvcs=false -trimpath -o scheduler-extender ./cmd/extender
: "${REGISTRY:?Set the approved registry/repository prefix}"
docker build -f Dockerfile.extender -t "$REGISTRY/scheduler-extender:v1.35.8-1" .
```

Prerequisites in `scheduler-lab`: an `extender-server-tls` Secret with `tls.crt`, `tls.key`, `client-ca.crt`; and an `extender-client-tls` Secret with scheduler client `tls.crt`, `tls.key`, and the server `ca.crt`. The server certificate must cover `scheduler-extender.scheduler-lab.svc`. No certificates or Secrets are created by this document. The NetworkPolicy requires an enforcing CNI. Its TCP readiness probe checks only the listening port, not successful mutual TLS or scheduling behavior.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: scheduler-extender
  namespace: scheduler-lab
spec:
  replicas: 2
  selector:
    matchLabels:
      app: scheduler-extender
  template:
    metadata:
      labels:
        app: scheduler-extender
    spec:
      automountServiceAccountToken: false
      securityContext:
        runAsNonRoot: true
        runAsUser: 65532
        runAsGroup: 65532
        fsGroup: 65532
      nodeSelector:
        kubernetes.io/os: linux
      containers:
      - name: extender
        image: registry.example.com/training/scheduler-extender:v1.35.8-1
        ports:
        - name: https
          containerPort: 8443
        readinessProbe:
          tcpSocket:
            port: https
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop: ["ALL"]
          seccompProfile:
            type: RuntimeDefault
        resources:
          requests:
            cpu: 100m
            memory: 64Mi
          limits:
            memory: 128Mi
        volumeMounts:
        - name: tls
          mountPath: /etc/extender-tls
          readOnly: true
      volumes:
      - name: tls
        secret:
          secretName: extender-server-tls
          defaultMode: 0440
---
apiVersion: v1
kind: Service
metadata:
  name: scheduler-extender
  namespace: scheduler-lab
spec:
  selector:
    app: scheduler-extender
  ports:
  - name: https
    port: 8443
    targetPort: https
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: scheduler-extender
  namespace: scheduler-lab
spec:
  podSelector:
    matchLabels:
      app: scheduler-extender
  policyTypes: [Ingress, Egress]
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: scheduler-lab
      podSelector:
        matchLabels:
          app: custom-scheduler
    ports:
    - protocol: TCP
      port: 8443
  egress: []
```

### Scheduler Configuration

Configure **your secondary scheduler**, including on EKS. EKS does not expose the managed default scheduler's configuration file, and `/etc/kubernetes/scheduler.conf` is not a control-plane credential to mount from an EC2 worker.

1. Save this configuration. It retains the Part1 profile and distinct leader-election Lease, leaves built-in filters enabled, and verifies the extender's server certificate. `ignorable: false` makes filter failures block that scheduling attempt; it does not change the priority-error behavior described above. Do not set `ignoredByScheduler: true` for GPU resources: the extender does not account for available devices.

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

2. Save the corresponding ConfigMap as `extender-scheduler-config.yaml`:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: extender-scheduler-config
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

3. Save this **strategic merge patch**, not a standalone Deployment, as `extender-scheduler-patch.yaml`. It changes the existing Part1 Deployment's config volume and adds client certificates while preserving its ServiceAccount, probes, resources and command.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: custom-scheduler
  namespace: scheduler-lab
spec:
  template:
    spec:
      volumes:
      - name: config
        configMap:
          name: extender-scheduler-config
      - name: extender-client
        secret:
          secretName: extender-client-tls
          defaultMode: 288
      containers:
      - name: custom-scheduler
        volumeMounts:
        - name: extender-client
          mountPath: /etc/extender-client
          readOnly: true
```

Apply these only to the disposable lab after deploying the extender and replacing image placeholders:

```bash
kubectl -n scheduler-lab apply -f extender-scheduler-config.yaml
kubectl -n scheduler-lab patch deployment custom-scheduler --type=strategic --patch-file=extender-scheduler-patch.yaml
kubectl -n scheduler-lab rollout restart deployment/custom-scheduler
kubectl -n scheduler-lab rollout status deployment/custom-scheduler
```

The scheduler reads configuration at startup; a ConfigMap projection alone does not reload it. `subPath` mounts would also prevent normal projected-file updates.

## Scheduler Framework Plugins

The scheduler framework introduced in Kubernetes 1.15 provides a plugin-based architecture. This approach allows you to implement plugins at various stages of the scheduling pipeline.

### Scheduler Framework Architecture

Plugins execute inside the scheduler process at configured extension points; the scheduler remains responsible for its queue, cache and binding workflow.

### Scheduler Framework Plugin Configuration

Each profile enables registered plugins for its scheduler name. All profiles in one process share a scheduling queue and must use the same QueueSort configuration.

### Scheduling Framework Extension Points

The framework includes `PreEnqueue`, `QueueSort`, `PreFilter`, `Filter`, `PostFilter`, `PreScore`, `Score` with optional `NormalizeScore`, `Reserve`/`Unreserve`, `Permit`, `PreBind`, `Bind` and `PostBind`.

Scheduling cycles select nodes serially; binding cycles may overlap. Reserve tracks assumed state and Unreserve unwinds it after failure. PostFilter can attempt preemption when no node fits. PostBind runs after a successful binding and cannot veto it. The pinned Go interfaces may require additional methods at some points; compile against the target version.

### Scheduler Plugin Implementation

Save this as `gpuplugin/plugin.go`. It reuses the policy above and receives `framework.NodeInfo` directly. There is no built-in `NodeInfoKey` to read from CycleState. This plugin handles only the declared memory label; default filters still handle GPU counts, taints, affinity and volumes.

```go
package gpuplugin

import (
	"context"

	"example.com/custom-scheduler/gpupolicy"
	v1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/runtime"
	fwk "k8s.io/kube-scheduler/framework"
)

const Name = "GPUScheduler"

type Plugin struct{}

var _ fwk.FilterPlugin = &Plugin{}
var _ fwk.ScorePlugin = &Plugin{}

func (*Plugin) Name() string { return Name }

func (*Plugin) Filter(_ context.Context, _ fwk.CycleState, pod *v1.Pod, info fwk.NodeInfo) *fwk.Status {
	if info == nil || info.Node() == nil {
		return fwk.NewStatus(fwk.Error, "missing node")
	}
	req, err := gpupolicy.FromPod(pod)
	if err != nil {
		return fwk.NewStatus(fwk.UnschedulableAndUnresolvable, err.Error())
	}
	if ok, reason := gpupolicy.FitsMemory(req, info.Node()); !ok {
		return fwk.NewStatus(fwk.UnschedulableAndUnresolvable, reason)
	}
	return nil
}

func (*Plugin) Score(_ context.Context, _ fwk.CycleState, pod *v1.Pod, info fwk.NodeInfo) (int64, *fwk.Status) {
	if info == nil || info.Node() == nil {
		return 0, fwk.NewStatus(fwk.Error, "missing node")
	}
	req, err := gpupolicy.FromPod(pod)
	if err != nil {
		return 0, fwk.AsStatus(err)
	}
	return gpupolicy.Score100(req, info.Node()), nil
}

func (*Plugin) ScoreExtensions() fwk.ScoreExtensions { return nil }

func New(_ context.Context, _ runtime.Object, _ fwk.Handle) (fwk.Plugin, error) {
	return &Plugin{}, nil
}
```

### Scheduler Plugin Registration

Registering a plugin requires compiling it into the scheduler binary (see the command below). This configuration **enables** the registered plugin; YAML alone does not load Go code. Do not enable it at PreFilter/PreScore when those interfaces are not implemented.

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
      - name: GPUScheduler
    score:
      enabled:
      - name: GPUScheduler
        weight: 10
```

## Scheduler Framework Implementation in EKS

On EKS, run the custom scheduler on EC2 worker nodes with the Part1 ServiceAccount/RBAC and its own profile/Lease. In-cluster API access uses Kubernetes credentials; ECR publishing or optional AWS API calls require separate, appropriate IAM permissions. EKS Fargate scheduling is AWS-managed and GPUs are unavailable there. Use a lab namespace that is not selected by a Fargate profile.

Build the **scheduler binary with the plugin**, not a separate plugin image to inject into the managed control plane. Node labels supplement device-plugin resources; they do not create GPU capacity.

### EKS Scheduler Framework Architecture

The secondary scheduler watches Pod/Node state through the API and executes its registered plugins locally. ECR supplies the image; CloudWatch integration is optional. This example implements `GPUScheduler` only. Spot/AZ plugins in an architectural illustration require separate code and tests before being registered or enabled.

### EKS Scheduler Framework Implementation Steps

1. **Register the custom plugin** (`cmd/gpu-scheduler/main.go`). The upstream command already registers built-in plugins; registering them again causes duplicate-name failures.

```go
package main

import (
	"os"

	"example.com/custom-scheduler/gpuplugin"
	"k8s.io/component-base/cli"
	"k8s.io/kubernetes/cmd/kube-scheduler/app"
)

func main() {
	// Upstream already registers all built-in plugins. Register only our addition.
	command := app.NewSchedulerCommand(app.WithPlugin(gpuplugin.Name, gpuplugin.New))
	os.Exit(cli.Run(command))
}
```

2. **Build the image** after saving the shared policy and plugin and running `go mod tidy`. Match the image architecture to the scheduler's Linux workers. Pin registry base images by digest in a release workflow.

```dockerfile
FROM golang:1.27.1 AS builder
WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 go build -buildvcs=false -trimpath -o /out/gpu-scheduler ./cmd/gpu-scheduler

FROM gcr.io/distroless/static-debian12:nonroot
COPY --from=builder /out/gpu-scheduler /gpu-scheduler
ENTRYPOINT ["/gpu-scheduler"]
```

3. **Publish through your registry workflow**. The following commands require an explicitly selected registry; this audit did not execute them:

```bash
: "${REGISTRY:?Set the approved registry/repository prefix}"
docker build -t "$REGISTRY/gpu-scheduler:v1.35.8-1" .
docker push "$REGISTRY/gpu-scheduler:v1.35.8-1"
```

4. **Save `gpu-scheduler-config.yaml`**. Enable only the interfaces implemented by the plugin and retain upstream defaults:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: gpu-scheduler-config
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
      plugins:
        filter:
          enabled:
          - name: GPUScheduler
        score:
          enabled:
          - name: GPUScheduler
            weight: 10
```

5. **Update the Part1 Deployment** with this strategic merge patch, saved as `gpu-scheduler-patch.yaml`. Replace the image placeholder first. This is an alternative to the extender configuration; do not assume both policies are active merely because both examples exist.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: custom-scheduler
  namespace: scheduler-lab
spec:
  template:
    spec:
      volumes:
      - name: config
        configMap:
          name: gpu-scheduler-config
      containers:
      - name: custom-scheduler
        image: registry.example.com/training/gpu-scheduler:v1.35.8-1
```

```bash
kubectl -n scheduler-lab apply -f gpu-scheduler-config.yaml
kubectl -n scheduler-lab patch deployment custom-scheduler --type=strategic --patch-file=gpu-scheduler-patch.yaml
kubectl -n scheduler-lab rollout restart deployment/custom-scheduler
kubectl -n scheduler-lab rollout status deployment/custom-scheduler
```

6. **Request the scheduler and GPU**. This BusyBox Pod tests only reservation/placement if you run it in a prepared lab; it does not execute CUDA. A real GPU smoke test needs a validated CUDA application image, compatible drivers and an actual device check. Add the appropriate toleration if your GPU nodes are tainted.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: gpu-pod
  annotations:
    training.example.com/min-gpu-memory-mib: "16384"
spec:
  schedulerName: custom-scheduler
  restartPolicy: Never
  containers:
  - name: gpu-reservation-smoke
    image: busybox:1.37.0
    command: ["sh", "-c", "sleep 60"]
    resources:
      requests:
        cpu: 100m
        memory: 64Mi
        nvidia.com/gpu: 1
      limits:
        memory: 128Mi
        nvidia.com/gpu: 1
```

## Conclusion

In this chapter, we covered implementing custom schedulers using the scheduler extender approach and scheduler framework plugins. We also explored how to implement the scheduler framework in EKS clusters.

In the next chapter, we will look at custom scheduler implementation cases in EKS and monitoring methods.

## References and Verification Limits

* [Scheduler configuration and extender fields](https://kubernetes.io/docs/reference/scheduling/config/)
* [Kubernetes 1.35.8 extender wire types](https://github.com/kubernetes/kubernetes/blob/v1.35.8/staging/src/k8s.io/kube-scheduler/extender/v1/types.go)
* [Pinned scheduling framework interfaces](https://github.com/kubernetes/kubernetes/blob/v1.35.8/staging/src/k8s.io/kube-scheduler/framework/interface.go)
* [GPU scheduling](https://kubernetes.io/docs/tasks/manage-gpus/scheduling-gpus/)
* [EKS Fargate scheduling and limitations](https://docs.aws.amazon.com/eks/latest/userguide/fargate.html)

Local code/configuration checks do not verify actual hardware labels, driver compatibility, certificate provisioning, cluster scheduling, capacity or production availability.

## Quiz

To test what you've learned in this chapter, try the [Topic Quiz](../quizzes/scheduling/02-custom-scheduler-part2-quiz.md).
