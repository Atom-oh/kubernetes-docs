# 第 2 部分：实施

> **示例基线**：Kubernetes 1.35.8，Go 1.27.2
> **最后更新**：2026 年 10 月 16 日

使用 [Part1 模块设置和完整的 secondary-scheduler RBAC/Deployment](01-custom-scheduler-part1.md)。以下是为该调度器扩展功能的两种替代方法。示例已在本地检查；未测试 EKS 部署、GPU 执行、TLS 推出或生产故障转移。请重新验证其他 Kubernetes 次版本，不要假定 Go 接口兼容。

## 调度器扩展器方案

调度器扩展器方案是扩展默认调度器功能的一种方式。在此方案中，默认调度器通过 HTTP 请求调用外部服务（调度器扩展器），以提供额外的过滤和优先级功能。

### 调度器扩展器架构

扩展器作为由调度器调用的独立服务运行。在 EKS 上，请配置 Part1 中的 secondary scheduler。

### 调度器扩展器工作流

调度器扩展器的工作流如下：

![时序图显示调度器通过 API 观察 Pod 状态，执行内部过滤和评分，将 filter 和 prioritize HTTP 调用委派给调度器扩展器，然后选择节点、请求绑定，并在该节点上调度 Pod。](../.gitbook/assets/en-scheduling-02-custom-scheduler-part2-0.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-scheduling-02-custom-scheduler-part2-0.html)

### 调度器扩展器实施

扩展器实现已配置的 **filter**、**prioritize**、**preempt** 和 **bind** HTTP 回调中的一部分。本示例只使用 filter 和 priority 回调。扩展器没有 `PreFilter` 或 `PreScore` HTTP 钩子；这些是进程内的框架扩展点。将 `bindVerb` 留空以保留默认绑定器。

扩展器优先级范围为 **0–10**，而框架评分归一化后范围为 **0–100**。请将强制约束放在 Filter 中：在此固定版本的调度器中，优先级请求失败时只会记录日志并忽略其评分；它不是可靠的强制执行点。

调度器监视 API，并拥有自己的队列/缓存。它会在扩展器过滤之前应用内置过滤器，并将扩展器偏好与框架评分相结合。API server 不会将 Pod 推送到共享队列中。

本示例在保留上游资源适配检查的同时，添加了**声明式的每 GPU 内存条件**。它不会发现 GPU、测量可用 VRAM，也不会预留设备内存。

共享策略假设 Pod 已由 API 设置默认值、已安装设备插件、GPU 同质且未使用 MIG/时间切片，并由管理员维护 `training.example.com/gpu-memory-mib` 节点标签，以描述每个符合条件的 GPU 的最小内存。这些是**特定于实验环境的键**，不是标准 NVIDIA 发现标签。请先验证设备清单，再设置标签；对于异构/共享 GPU，请使用感知设备的分配机制。单靠节点标签无法保证之后分配的设备具备相应特性。

将以下文件保存在 Part1 模块中。

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

处理程序接受 `nodeCacheCapable: false` 契约，将实验请求限制为 4 MiB/512 个节点，拒绝格式错误或缺失的输入，并且只返回所提供候选项的一个子集。这些限制需要根据实际集群调整。无效的强制内存标签会使节点被排除；抢占其他 Pod 无法修复该标签。

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

服务器要求客户端证书由配置的客户端 CA 签发。请将该 CA 的信任范围限制为调度器客户端，并通过常规密钥管理流程轮换证书。

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

### 调度器扩展器部署

使用与 Part1 相同的固定模块和 Go 版本构建 `./cmd/extender`，将静态二进制打包到非 root 镜像中，并将下方的镜像占位符替换为构建得到的镜像/摘要。Pod 会从每个请求中读取全部调度数据，因此不需要 Kubernetes API token。

将以下内容保存为 `Dockerfile.extender`，然后在本地构建。选择一个获准使用的 registry，并将 Deployment 镜像替换为已发布的镜像。

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

`scheduler-lab` 中的先决条件：一个包含 `tls.crt`、`tls.key`、`client-ca.crt` 的 `extender-server-tls` Secret；以及一个包含调度器客户端 `tls.crt`、`tls.key` 和服务器 `ca.crt` 的 `extender-client-tls` Secret。服务器证书必须涵盖 `scheduler-extender.scheduler-lab.svc`。本文档不会创建任何证书或 Secret。NetworkPolicy 要求 CNI 强制执行策略。其 TCP 就绪探针只检查端口是否在监听，不检查双向 TLS 或调度行为是否成功。

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

### 调度器配置

请配置**你的 secondary scheduler**，包括在 EKS 上。EKS 不会公开受管默认调度器的配置文件，而且 `/etc/kubernetes/scheduler.conf` 也不是可以从 EC2 worker 挂载的控制平面凭证。

1. 保存此配置。它保留 Part1 的 profile 和独立的 leader-election Lease，保留内置过滤器，并验证扩展器的服务器证书。`ignorable: false` 会使过滤失败阻止此次调度尝试；它不会改变上文所述的 priority 错误处理行为。GPU 资源不要设置 `ignoredByScheduler: true`：扩展器不会核算可用设备。

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

2. 将对应的 ConfigMap 保存为 `extender-scheduler-config.yaml`：

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

3. 将此**战略合并补丁**（而非独立的 Deployment）保存为 `extender-scheduler-patch.yaml`。它会更改现有 Part1 Deployment 的 config 卷并添加客户端证书，同时保留其 ServiceAccount、探针、资源和命令。

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

部署扩展器并替换镜像占位符后，仅在可随时销毁的实验环境中应用以下内容：

```bash
kubectl -n scheduler-lab apply -f extender-scheduler-config.yaml
kubectl -n scheduler-lab patch deployment custom-scheduler --type=strategic --patch-file=extender-scheduler-patch.yaml
kubectl -n scheduler-lab rollout restart deployment/custom-scheduler
kubectl -n scheduler-lab rollout status deployment/custom-scheduler
```

调度器会在启动时读取配置；仅投射 ConfigMap 不会使其重新加载。使用 `subPath` 挂载也会阻止投射文件正常更新。

## 调度器框架插件

Kubernetes 1.15 引入的调度器框架提供了基于插件的架构。此方案允许你在调度流水线的各个阶段实现插件。

### 调度器框架架构

插件会在配置的扩展点内、调度器进程中执行；调度器仍负责其队列、缓存和绑定工作流。

### 调度器框架插件配置

每个 profile 都会为其调度器名称启用已注册的插件。同一进程中的所有 profile 共享一个调度队列，因此必须使用相同的 QueueSort 配置。

### 调度框架扩展点

框架包含 `PreEnqueue`、`QueueSort`、`PreFilter`、`Filter`、`PostFilter`、`PreScore`、带可选 `NormalizeScore` 的 `Score`、`Reserve`/`Unreserve`、`Permit`、`PreBind`、`Bind` 和 `PostBind`。

调度周期会串行选择节点；绑定周期可以重叠执行。Reserve 会跟踪假定状态，失败后由 Unreserve 撤销。没有节点符合条件时，PostFilter 可以尝试抢占。成功绑定后会运行 PostBind，且不能否决绑定。固定版本的 Go 接口可能要求在某些扩展点实现额外方法；请针对目标版本进行编译。

### 调度器插件实施

将以下内容保存为 `gpuplugin/plugin.go`。它会复用上文的策略，并直接接收 `framework.NodeInfo`。没有可从 CycleState 读取的内置 `NodeInfoKey`。该插件只处理声明的内存标签；默认过滤器仍会处理 GPU 数量、污点、亲和性和卷。

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

### 调度器插件注册

注册插件需要将其编译到调度器二进制文件中（请参见下方命令）。此配置会**启用**已注册的插件；仅有 YAML 不会加载 Go 代码。如果未实现相应接口，请勿在 PreFilter/PreScore 阶段启用插件。

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

## 在 EKS 中实施调度器框架

在 EKS 上，请使用 Part1 的 ServiceAccount/RBAC 及其独立的 profile/Lease，在 EC2 worker 节点上运行自定义调度器。集群内 API 访问使用 Kubernetes 凭证；发布到 ECR 或调用可选 AWS API 需要单独配置适当的 IAM 权限。EKS Fargate 调度由 AWS 管理，且不提供 GPU。请使用未被 Fargate profile 选中的实验 namespace。

请构建**包含该插件的调度器二进制文件**，而不是构建一个单独的插件镜像并注入受管控制平面。节点标签只是设备插件资源的补充；它们不会创建 GPU 容量。

### EKS 调度器框架架构

secondary scheduler 通过 API 监视 Pod/Node 状态，并在本地执行已注册的插件。ECR 提供镜像；CloudWatch 集成是可选的。本示例只实现 `GPUScheduler`。架构图示中的 Spot/AZ 插件需要单独编写代码并完成测试，之后才能注册或启用。

### EKS 调度器框架实施步骤

1. **注册自定义插件**（`cmd/gpu-scheduler/main.go`）。上游命令已经注册了内置插件；再次注册会导致名称重复错误。

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

2. 保存共享策略和插件并运行 `go mod tidy` 后，**构建镜像**。镜像架构应与调度器所运行的 Linux worker 架构一致。在发布工作流中按摘要固定 registry 基础镜像。

```dockerfile
FROM golang:1.27.2 AS builder
WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 go build -buildvcs=false -trimpath -o /out/gpu-scheduler ./cmd/gpu-scheduler

FROM gcr.io/distroless/static-debian12:nonroot
COPY --from=builder /out/gpu-scheduler /gpu-scheduler
ENTRYPOINT ["/gpu-scheduler"]
```

3. **通过你的 registry 工作流发布**。以下命令需要显式选择 registry；本次审核未执行这些命令：

```bash
: "${REGISTRY:?Set the approved registry/repository prefix}"
docker build -t "$REGISTRY/gpu-scheduler:v1.35.8-1" .
docker push "$REGISTRY/gpu-scheduler:v1.35.8-1"
```

4. **保存 `gpu-scheduler-config.yaml`**。仅启用插件已实现的接口，并保留上游默认设置：

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

5. 使用此战略合并补丁**更新 Part1 Deployment**，并将其保存为 `gpu-scheduler-patch.yaml`。先替换镜像占位符。这是扩展器配置的替代方案；不要仅仅因为两个示例都存在，就假设两种策略会同时生效。

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

6. **请求调度器和 GPU**。如果在准备好的实验环境中运行，此 BusyBox Pod 只会测试预留/放置；它不会执行 CUDA。真正的 GPU 冒烟测试需要经过验证的 CUDA 应用镜像、兼容的驱动程序以及实际设备检查。如果 GPU 节点带有污点，请添加相应的容忍度。

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
    image: busybox:1.38.0
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

## 结论

本章介绍了如何使用调度器扩展器方案和调度器框架插件实现自定义调度器。我们还探讨了如何在 EKS 集群中实施调度器框架。

下一章将介绍 EKS 中的自定义调度器实施案例和监控方法。

## 参考资料和验证限制

* [调度器配置和扩展器字段](https://kubernetes.io/docs/reference/scheduling/config/)
* [Kubernetes 1.35.8 扩展器线缆类型](https://github.com/kubernetes/kubernetes/blob/v1.35.8/staging/src/k8s.io/kube-scheduler/extender/v1/types.go)
* [固定版本的调度框架接口](https://github.com/kubernetes/kubernetes/blob/v1.35.8/staging/src/k8s.io/kube-scheduler/framework/interface.go)
* [GPU 调度](https://kubernetes.io/docs/tasks/manage-gpus/scheduling-gpus/)
* [EKS Fargate 调度和限制](https://docs.aws.amazon.com/eks/latest/userguide/fargate.html)

本地代码/配置检查无法验证实际硬件标签、驱动兼容性、证书配置、集群调度、容量或生产可用性。

## 测验

要测试你对本章内容的掌握情况，请尝试[主题测验](../quizzes/scheduling/02-custom-scheduler-part2-quiz.md)。
