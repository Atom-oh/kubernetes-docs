# 第 3 部分：高级功能

> **示例基线**：Kubernetes 1.35.8，Go 1.27.2；Python 客户端 API 35.0.0
> **最后更新**：October 16, 2026

以下是使用[第 1 部分的辅助调度器](01-custom-scheduler-part1.md)和[第 2 部分的框架接口](02-custom-scheduler-part2.md)实现的示例模式。它们不是生产部署报告，也不是经过测量的优化结果。本地代码/架构检查并不能证明 GPU 正在执行、应用已就绪、证书已配置或生产环境可用。

## EKS 中的自定义调度器实现案例

本节介绍 EKS 调度策略示例。必须在目标集群上验证实际容量、设备清单、流量模式和故障行为。

### 案例 1：GPU 工作负载优化调度器

在运行 AI/ML 工作负载的 EKS 集群中，高效利用 GPU 资源十分重要。下面是一个用于优化 GPU 工作负载的自定义调度器实现案例。

#### GPU 工作负载优化调度器架构

该设计可以结合放置策略和可选遥测。下面实现的示例使用缓存请求；该图并不能证明存在可用的利用率采集器。

#### GPU 工作负载调度工作流

调度器通过 API 监视 Pod 状态。工作流中展示的基于指标的扩展需要单独验证采集器。

#### 要求

1. 使用经过验证的节点标签和必需节点亲和性，强制执行 GPU 内存/型号要求。
2. 保留 `NodeResourcesFit`，以正确处理 GPU 请求以及已分配/已假定的请求。
3. 使用调度器快照，优先将工作负载集中放置到合适的节点上；此处未实现基于实时利用率的权重，这属于单独的集成。
4. GPU 共享需要适当的设备插件/MIG/时间切片或 DRA 分配策略。节点评分函数不会对设备进行分区，也不会强制限制每个进程的 GPU 内存。


#### 实现方法

本案例采用调度器框架插件方法。

1. **添加标签前验证设备清单。** 下面的 `training.example.com` 键是管理员定义的实验室标签，并非 NVIDIA 发现标签。内存值必须表示同构、非共享 GPU 节点上每个符合条件设备的最小内存。通过 `status.allocatable` 读取 GPU 资源数量；数量标签不代表剩余容量。

```bash
kubectl get nodes -o custom-columns='NAME:.metadata.name,GPUS:.status.allocatable.nvidia\.com/gpu'

# Set only after verifying the actual node and per-device inventory.
: "${NODE_NAME:?Select a verified GPU node}"
: "${GPU_MODEL:?Set the observed model label value}"
: "${GPU_MEMORY_MIB:?Set verified minimum memory per GPU in MiB}"
kubectl label node "$NODE_NAME" \
  "training.example.com/gpu-model=$GPU_MODEL" \
  "training.example.com/gpu-memory-mib=$GPU_MEMORY_MIB" --overwrite
```

2. **添加评分插件，但不要替换默认过滤器。** 将下面的内容保存为 `packing/plugin.go`。它使用可分配 GPU 资源减去现有/已假定请求以及传入请求，而不是使用总设备清单标签或实时利用率。零分不会排除节点。

```go
package packing

import (
	"context"

	v1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/runtime"
	resourcehelper "k8s.io/component-helpers/resource"
	fwk "k8s.io/kube-scheduler/framework"
)

const Name = "GPUPacking"
const gpu v1.ResourceName = "nvidia.com/gpu"

type Plugin struct{}

var _ fwk.ScorePlugin = &Plugin{}

func (*Plugin) Name() string { return Name }

func (*Plugin) Score(_ context.Context, _ fwk.CycleState, pod *v1.Pod, info fwk.NodeInfo) (int64, *fwk.Status) {
	if pod == nil || info == nil || info.Node() == nil {
		return 0, fwk.NewStatus(fwk.Error, "missing node")
	}
	requests := resourcehelper.PodRequests(pod, resourcehelper.PodResourcesOptions{})
	request := requests[gpu]
	needed, exact := request.AsInt64()
	if !exact || needed < 0 {
		return 0, fwk.NewStatus(fwk.Error, "GPU request must be a non-negative integer")
	}
	if needed == 0 {
		return 0, nil
	}
	allocatable := info.GetAllocatable().GetScalarResources()[gpu]
	requested := info.GetRequested().GetScalarResources()[gpu]
	remaining := allocatable - requested - needed
	if remaining < 0 {
		// Score cannot exclude a node. NodeResourcesFit must remain enabled.
		return 0, nil
	}
	if remaining >= 10 {
		return 0, nil
	}
	return 100 - remaining*10, nil
}

func (*Plugin) ScoreExtensions() fwk.ScoreExtensions { return nil }

func New(_ context.Context, _ runtime.Object, _ fwk.Handle) (fwk.Plugin, error) {
	return &Plugin{}, nil
}
```

在 `cmd/gpu-packing-scheduler/main.go` 中注册该插件，然后使用第 1 部分的镜像工作流运行 `CGO_ENABLED=0 go build -buildvcs=false -o custom-scheduler ./cmd/gpu-packing-scheduler`。

```go
package main

import (
	"os"

	"example.com/custom-scheduler/packing"
	"k8s.io/component-base/cli"
	"k8s.io/kubernetes/cmd/kube-scheduler/app"
)

func main() {
	command := app.NewSchedulerCommand(app.WithPlugin(packing.Name, packing.New))
	os.Exit(cli.Run(command))
}
```

原始的 70:30 集中放置/利用率构想可以用示例公式 `(packingScore * 7 + utilizationScore * 3) / 10` 表示，其中 `utilizationScore = (1 - utilization) * 100`。**此公式并未接入该二进制文件**。实际实现需要一致、及时的逐设备快照，0–1 范围内的有限值、有界的采集延迟，以及明确的缺失数据策略。遥测数据缺失不等于利用率为零；利用率也不等于未分配的 GPU 容量。

3. **调度器配置**：

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
      - name: GPUPacking
        weight: 10
```

4. **在 Pod 中声明硬性放置要求。** 请将示例型号/内存替换为经过验证的设备清单值。`Gt: "40959"` 表示整数标签值至少为 40960MiB。下面的 BusyBox 镜像只会在准备好的实验环境中保留 GPU 资源；它不会执行 CUDA，也不会验证 GPU。

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: gpu-reservation-demo
  namespace: scheduler-lab
spec:
  schedulerName: custom-scheduler
  automountServiceAccountToken: false
  restartPolicy: Never
  affinity:
    nodeAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
        nodeSelectorTerms:
        - matchExpressions:
          - key: training.example.com/gpu-model
            operator: In
            values:
            - A100
          - key: training.example.com/gpu-memory-mib
            operator: Gt
            values:
            - '40959'
  containers:
  - name: reservation
    image: busybox:1.38.0
    command:
    - sh
    - -c
    - sleep 60
    resources:
      requests:
        cpu: 100m
        memory: 64Mi
        nvidia.com/gpu: 2
      limits:
        memory: 128Mi
        nvidia.com/gpu: 2
```

### 案例 2：网络局部性优化调度器

在 EKS 集群中，可以实现考虑网络局部性的自定义调度器，以优化网络成本。

#### 网络局部性优化调度器架构

网络局部性设计可以结合拓扑信息和测得的依赖关系信息；这些集成仅作示例说明。

#### 网络局部性优化工作流

在评估可选局部性评分之前，先评估硬性放置约束；实际流量和故障域要求决定了如何权衡。

在创建另一个调度器之前，先使用必需/首选 Pod 亲和性、拓扑分布和存储拓扑。对实际服务依赖关系和符合条件的 AZ 建模；共同放置可以减少部分跨 AZ 流量，但也可能增加故障集中度或资源争用。放置标签和调度评分都不能证明延迟或成本节省。

这些图描述的是可能的集成方式，并非完整的网络策略、服务网格或 CloudWatch 实现。应将指标采集放在逐节点评分调用之外，限制数据陈旧时间和超时时间，并使用实际流量重新评估成本/可用性权衡。本章不包含已部署的网络局部性调度器。

## 使用 Pod 删除成本优化缩容

Pod 删除成本是 ReplicaSet 缩容时的**尽力而为的偏好**，其中也包括由 Deployment 的 ReplicaSet 管理的 Pod。该功能在 1.21 中以 alpha 版形式出现，在 1.22 中成为默认启用的 beta 版；在所引用的文档中仍为 beta 版。它不控制 StatefulSet 序号删除、裸 Pod 删除、驱逐或节点故障。

### Pod 删除成本概念

在每个 Pod 上设置 `controller.kubernetes.io/pod-deletion-cost` 注解。成本只在**同一个 ReplicaSet 内**比较，不会跨 Deployment 或节点进行全局比较。只有在优先级更高的条件允许时，较高成本才会优先保留 Pod。

**关键属性：**

* 缺少注解时默认为 0；有效十进制值范围为有符号 int32，包括负值。启用该功能时，无效值会被拒绝。
* 在固定版本的控制器中，成本排序之前会先考虑分配情况、Pod 阶段和就绪状态；副本放置及其他决胜条件则在其后考虑。
* 不保证删除顺序。模板成本相等时无法区分副本。
* 避免频繁地根据指标更新。优先使用粗粒度的应用状态转换，或在应用控制的缩容操作之前更新一次。


### Pod 删除成本架构

该图仅在分配情况、阶段、就绪状态和其他相关条件相当时展示成本排序；它不代表有保证的删除顺序。

![ReplicaSet 控制器按 Pod 的 pod-deletion-cost 注解排序，并优先删除成本最低的 Pod：先删除 Pod-3（成本 -10），再删除 Pod-4（成本 0），而成本较高的 Pod-1 和 Pod-2 在缩容后保留。](../.gitbook/assets/en-scheduling-03-custom-scheduler-part3-0.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-scheduling-03-custom-scheduler-part3-0.html)

### 使用场景

#### 1. 保护已预热缓存的 Pod

此 Deployment 会将每个 Pod 的初始成本设为 0。这是对**你的应用**的约定：请替换镜像，并在端口 8080 上实现 `/readyz`，使就绪状态能反映实际预热情况。本次审查未构建或运行该应用。不能仅仅因为等待时间结束就设置高成本。

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: deletion-cost-lab
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cache-app
  namespace: deletion-cost-lab
spec:
  replicas: 5
  selector:
    matchLabels:
      app: cache-app
  template:
    metadata:
      labels:
        app: cache-app
      annotations:
        controller.kubernetes.io/pod-deletion-cost: '0'
    spec:
      automountServiceAccountToken: false
      containers:
      - name: app
        image: registry.example.com/training/cache-app:validated
        ports:
        - name: http
          containerPort: 8080
        readinessProbe:
          httpGet:
            path: /readyz
            port: http
          periodSeconds: 5
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            memory: 256Mi
        env:
        - name: POD_NAME
          valueFrom:
            fieldRef:
              fieldPath: metadata.name
        - name: POD_NAMESPACE
          valueFrom:
            fieldRef:
              fieldPath: metadata.namespace
        - name: POD_UID
          valueFrom:
            fieldRef:
              fieldPath: metadata.uid
```

只有在某个特定副本确实完成预热后，经过授权的操作员/控制器才能更新该 Pod 的注解。更新 Deployment 模板会触发一次发布，并创建另一个 ReplicaSet。

```bash
: "${POD_NAME:?Select a verified warm replica of cache-app}"
kubectl -n deletion-cost-lab annotate pod "$POD_NAME" \
  controller.kubernetes.io/pod-deletion-cost=100 --overwrite
```

示例 Deployment 不会挂载 API 令牌。下面的可选动态辅助程序需要单独配置且经过授权的 Kubernetes 客户端。命名空间级 RBAC 中的 `patch pods` 权限不会自动限制为调用该 API 的 Pod；应使用可信控制器，或配置适当受限的身份/准入策略。本示例不会安装此类生产策略。

#### 2. 保护存在活动连接的 Pod

活动连接数可以作为一种保留提示；但仍然需要优雅关闭和排空，因为成本无法阻止删除。此库会串行化更新、使用粗粒度分桶、检查 Pod UID、只修补注解，并跳过未变化的提示。它假定该注解只有一个写入者，且 Pod 模板中已存在 annotations 对象。

传入已配置的 `client-go` 客户端以及已准入 Pod 的名称/命名空间/UID。在 Pod 内集成时，可以通过 Downward API 获取这些标识；但获取标识并不会授予 API 权限。应在受控状态转换时或你负责的缩容操作之前调用 `UpdateDeletionCost(ctx)`，而不是在每次连接事件发生时调用。

```go
package deletioncost

import (
	"context"
	"encoding/json"
	"fmt"
	"strconv"
	"sync"
	"time"

	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/types"
	"k8s.io/client-go/kubernetes"
)

const Annotation = "controller.kubernetes.io/pod-deletion-cost"

type ConnectionTracker struct {
	client                  kubernetes.Interface
	namespace, podName      string
	uid                     types.UID
	connectionsMu, updateMu sync.Mutex
	activeConnections       int64
	lastCost                int32
	lastCostSet             bool
}

func NewConnectionTracker(client kubernetes.Interface, namespace, podName string, uid types.UID) (*ConnectionTracker, error) {
	if client == nil || namespace == "" || podName == "" || uid == "" {
		return nil, fmt.Errorf("client and admitted Pod namespace/name/UID are required")
	}
	return &ConnectionTracker{client: client, namespace: namespace, podName: podName, uid: uid}, nil
}

func (t *ConnectionTracker) OnConnectionOpen() {
	t.connectionsMu.Lock()
	defer t.connectionsMu.Unlock()
	t.activeConnections++
}

func (t *ConnectionTracker) OnConnectionClose() {
	t.connectionsMu.Lock()
	defer t.connectionsMu.Unlock()
	if t.activeConnections > 0 {
		t.activeConnections--
	}
}

// Illustrative coarse policy, not a benchmark or an availability guarantee.
func CostForConnections(count int64) int32 {
	switch {
	case count <= 0:
		return 0
	case count < 10:
		return 100
	case count < 100:
		return 500
	default:
		return 1000
	}
}

// Call at an application-controlled transition or before a controlled scale-down,
// not for every request. Assumes a single owner of this Pod's cost annotation.
func (t *ConnectionTracker) UpdateDeletionCost(parent context.Context) (bool, error) {
	t.updateMu.Lock()
	defer t.updateMu.Unlock()
	if err := parent.Err(); err != nil {
		return false, err
	}
	t.connectionsMu.Lock()
	cost := CostForConnections(t.activeConnections)
	t.connectionsMu.Unlock()
	if t.lastCostSet && t.lastCost == cost {
		return false, nil
	}

	// The Deployment template must already contain an annotations object.
	// JSON Pointer escapes the slash in the annotation key as ~1.
	patch, err := json.Marshal([]map[string]any{
		{"op": "test", "path": "/metadata/uid", "value": string(t.uid)},
		{"op": "add", "path": "/metadata/annotations/controller.kubernetes.io~1pod-deletion-cost", "value": strconv.FormatInt(int64(cost), 10)},
	})
	if err != nil {
		return false, err
	}
	ctx, cancel := context.WithTimeout(parent, 3*time.Second)
	defer cancel()
	_, err = t.client.CoreV1().Pods(t.namespace).Patch(ctx, t.podName, types.JSONPatchType, patch, metav1.PatchOptions{})
	if err != nil {
		return false, err
	}
	t.lastCost, t.lastCostSet = cost, true
	return true, nil
}
```

#### 3. 保护具有数据局部性的 Pod

局部性提示可以优先保留缓存了有用数据的副本。在下面的清单中，每个副本的初始成本均为 50，因此在可信控制器更新各个 Pod 之前，成本不会形成差异。成本不会挂载、保留或恢复数据；存储约束和应用恢复仍需单独处理。

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: data-processor
spec:
  replicas: 5
  selector:
    matchLabels:
      app: data-processor
  template:
    metadata:
      labels:
        app: data-processor
      annotations:
        # Set high cost for pods with high data locality
        controller.kubernetes.io/pod-deletion-cost: "50"
    spec:
      affinity:
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 100
            podAffinityTerm:
              labelSelector:
                matchExpressions:
                - key: app
                  operator: In
                  values:
                  - data-processor
              topologyKey: kubernetes.io/hostname
      containers:
      - name: processor
        image: registry.example.com/training/data-processor:validated
        env:
        - name: POD_NAME
          valueFrom:
            fieldRef:
              fieldPath: metadata.name
        - name: POD_NAMESPACE
          valueFrom:
            fieldRef:
              fieldPath: metadata.namespace
```

#### 4. 优先删除刚启动的 Pod

当其他控制器条件相同时，初始负成本可以优先删除刚启动的副本。请在初次部署**之前**在模板中设置成本，然后在实际就绪/状态转换后更新单个 Pod。固定的 postStart 睡眠时间不能证明缓存已就绪；修改现有 Deployment 模板会触发发布。

```yaml
# Deployment Pod-template fragment, chosen before initial deployment.
spec:
  template:
    metadata:
      annotations:
        controller.kubernetes.io/pod-deletion-cost: "-50"
```

### 与 Horizontal Pod Autoscaler 集成

HPA 会调整期望副本数；Deployment/ReplicaSet 控制器会选择要移除的 Pod。删除成本只是选择 Pod 时的提示，不是 HPA 信号，也不能保证 Pod 得到保护。此 HPA 的目标是上文的 `cache-app` Deployment，并且需要可用的 CPU 资源指标和 CPU 请求。`selectPolicy: Min` 会选择限制更严格的缩容策略。

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: cache-app
  namespace: deletion-cost-lab
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: cache-app
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 50
        periodSeconds: 60
      - type: Pods
        value: 2
        periodSeconds: 60
      selectPolicy: Min
```

### 动态更新 Pod 删除成本模式

此替代策略会将每个 Pod 的最新请求/缓存/延迟输入合并为以 100 为单位的粗粒度提示。权重仅作示例，并非测得的性能结果。这里没有虚假的采集器或后台轮询循环：请提供带有 Pod UID 和时区偏移 `observed_at` 时间戳的真实样本。数据缺失、无效、过期或属于错误的 Pod 时会报错，并保持注解不变。

传入已配置的 Kubernetes Python `ApiClient`；其调用签名已对照 client 35.0.0 检查。该实现明确使用 JSON Patch、UID 检查和有界连接/读取超时。应为该注解选择一个唯一的所有者/策略，不要让两个示例同时作用于同一个 Pod。

```python
from datetime import datetime, timezone
import math
import threading

ANNOTATION_PATH = (
    "/metadata/annotations/controller.kubernetes.io~1pod-deletion-cost"
)


def calculate_cost(metrics, now):
    """Illustrative coarse hint from a real, fresh per-Pod sample."""
    observed = datetime.fromisoformat(metrics["observed_at"].replace("Z", "+00:00"))
    if observed.tzinfo is None or now.tzinfo is None:
        raise ValueError("timestamps must include a timezone")
    age = (now - observed).total_seconds()
    if age < -5 or age > 60:
        raise ValueError("metrics timestamp is in the future or stale")

    active = metrics["active_requests"]
    if isinstance(active, bool) or not isinstance(active, int) or active < 0:
        raise ValueError("active_requests must be a non-negative integer")
    hit_rate = metrics["cache_hit_rate"]
    latency = metrics["avg_response_time_ms"]
    for value in (hit_rate, latency):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError("metrics must be finite numbers")
    if not 0 <= hit_rate <= 1 or latency < 0:
        raise ValueError("invalid hit rate or latency")

    raw_cost = active * 5 + int(hit_rate * 100)
    raw_cost += 50 if latency < 100 else 20 if latency < 500 else 0
    # Coarse buckets reduce annotation churn. Weights are an example policy.
    return min(1000, (raw_cost // 100) * 100)


class DeletionCostManager:
    """Uses a configured Kubernetes Python ApiClient; starts no background loop."""

    def __init__(self, api_client, namespace, pod_name, pod_uid):
        if api_client is None or not all((namespace, pod_name, pod_uid)):
            raise ValueError("API client and admitted Pod namespace/name/UID required")
        self.api_client = api_client
        self.namespace = namespace
        self.pod_name = pod_name
        self.pod_uid = pod_uid
        self._last_cost = None
        self._lock = threading.Lock()

    def update_from_metrics(self, metrics, now=None):
        # A single writer should own this annotation. The Pod template must
        # already create the annotations object with an initial deletion cost.
        if metrics["pod_uid"] != self.pod_uid:
            raise ValueError("metrics belong to a different Pod UID")
        now = now or datetime.now(timezone.utc)
        cost = calculate_cost(metrics, now)
        with self._lock:
            if cost == self._last_cost:
                return False
            patch = [
                {"op": "test", "path": "/metadata/uid", "value": self.pod_uid},
                {"op": "add", "path": ANNOTATION_PATH, "value": str(cost)},
            ]
            # Explicit JSON Patch media type; preserve unrelated Pod fields.
            self.api_client.call_api(
                "/api/v1/namespaces/{namespace}/pods/{name}",
                "PATCH",
                path_params={"namespace": self.namespace, "name": self.pod_name},
                header_params={
                    "Accept": "application/json",
                    "Content-Type": "application/json-patch+json",
                },
                body=patch,
                response_type="V1Pod",
                auth_settings=["BearerToken"],
                _return_http_data_only=True,
                _request_timeout=(3, 5),
            )
            self._last_cost = cost
            return True
```

### 监控与调试

这些命令用于检查注解，并验证缩容请求而不更改副本数。服务器端试运行**不会模拟 ReplicaSet 的受害 Pod 选择过程**。若要进行实际缩容实验，请使用你控制的隔离工作负载，考虑任何可能覆盖副本数的 HPA，并比较缩容前后的 Pod UID/所属 ReplicaSet。仅凭 kubelet 的 `Killing` 事件不能证明删除成本排序生效。

```bash
kubectl -n deletion-cost-lab get pods -l app=cache-app \
  -o custom-columns='NAME:.metadata.name,UID:.metadata.uid,COST:.metadata.annotations.controller\.kubernetes\.io/pod-deletion-cost'

kubectl -n deletion-cost-lab get pods -l app=cache-app -o json | \
  jq -r '.items[] | [.metadata.name, .metadata.uid, (.metadata.annotations["controller.kubernetes.io/pod-deletion-cost"] // "0")] | @tsv'

# Server-side dry run changes no replicas and does not predict victim selection.
kubectl -n deletion-cost-lab scale deployment/cache-app --replicas=3 --dry-run=server
kubectl -n deletion-cost-lab get replicasets,pods -l app=cache-app
```

### Prometheus 指标采集

`kube_pod_annotations` 来自 **kube-state-metrics**，而非应用程序。在现有导出器上启用指定的注解允许列表，并保留其他标志/允许列表键。现有 Prometheus 抓取目标必须处于健康状态；以下内容是参数片段，不是新的 Deployment。

```yaml
# Fragment to merge into the existing kube-state-metrics container arguments.
# Preserve its other arguments and allowlisted keys.
args:
- --metric-annotations-allowlist=pods=[controller.kubernetes.io/pod-deletion-cost]
```

导出的指标是值为 1 的 gauge，且带有 `annotation_controller_kubernetes_io_pod_deletion_cost` **标签**。重新标记注解不会使其成为数值型指标值。缺少时间序列可能意味着未采集；不能假定其成本为 0。

### Grafana 仪表板

这是用于导入的仪表板 JSON 对象，而不是 HTTP API 的 `{"dashboard": ...}` 请求包装对象。请将 `PROMETHEUS_UID` 替换为实际的数据源 UID。面板会按明确的注解标签统计 Pod 数量，包括负值；它们不会将值为 1 的 gauge 绘制为删除成本。解释结果前，请先确认 kube-state-metrics 的允许列表。

```json
{
  "id": null,
  "uid": "pod-deletion-cost-hints",
  "title": "Pod Deletion Cost Hints",
  "schemaVersion": 39,
  "version": 1,
  "refresh": "30s",
  "time": {
    "from": "now-1h",
    "to": "now"
  },
  "panels": [
    {
      "id": 1,
      "title": "Pods by explicit deletion cost",
      "type": "piechart",
      "gridPos": {
        "h": 8,
        "w": 12,
        "x": 0,
        "y": 0
      },
      "datasource": {
        "type": "prometheus",
        "uid": "PROMETHEUS_UID"
      },
      "targets": [
        {
          "refId": "A",
          "expr": "count by (annotation_controller_kubernetes_io_pod_deletion_cost) (kube_pod_annotations{namespace=\"deletion-cost-lab\",annotation_controller_kubernetes_io_pod_deletion_cost=~\"-?[0-9]+\"})",
          "legendFormat": "{{annotation_controller_kubernetes_io_pod_deletion_cost}}",
          "instant": true
        }
      ],
      "fieldConfig": {
        "defaults": {
          "unit": "short"
        },
        "overrides": []
      },
      "options": {}
    },
    {
      "id": 2,
      "title": "Pods with an explicit cost",
      "type": "stat",
      "gridPos": {
        "h": 8,
        "w": 12,
        "x": 12,
        "y": 0
      },
      "datasource": {
        "type": "prometheus",
        "uid": "PROMETHEUS_UID"
      },
      "targets": [
        {
          "refId": "A",
          "expr": "count(kube_pod_annotations{namespace=\"deletion-cost-lab\",annotation_controller_kubernetes_io_pod_deletion_cost!=\"\"})",
          "legendFormat": "",
          "instant": true
        }
      ],
      "fieldConfig": {
        "defaults": {
          "unit": "short"
        },
        "overrides": []
      },
      "options": {}
    }
  ]
}
```

### 最佳实践

1. **使用一致的成本范围**：在团队内部定义并使用一致的成本范围。
   * `-100 to -1`：优先删除（新 Pod、正在预热的 Pod）
   * `0`：默认值（普通 Pod）
   * `1 to 100`：中等重要性（存在活动连接的 Pod）
   * `100 to 1000`：高重要性（缓存已预热的 Pod、连接较多的 Pod）
2. **限制更新频率**：使用粗粒度状态转换，或在受控缩容之前更新；避免针对每个请求/指标样本写入。
3. **设置上限**：为删除成本设置上限，避免过大的值引发问题。
4. **监控**：监控删除成本的分布，以确认其按预期生效。
5. **测试**：在应用到生产环境之前，先在暂存环境中测试缩容行为。
6. **文档**：记录每个成本范围的含义。

### 限制

* **PDB 范围**：普通的 ReplicaSet/Deployment 缩容会直接删除 Pod，不会被 PDB 阻止。PDB 管理通过驱逐 API 发出的请求；这两种机制都不能保证故障期间 Pod 一定存活。
* **版本/功能**：1.21 为 alpha；自 1.22 起为默认启用的 beta 版；所引用的 1.35.8 基线启用了 PodDeletionCost。不要因此部署不受支持的旧次要版本。
* **工作负载/所有权**：该偏好仅在同一个 ReplicaSet 内生效。裸 Pod、StatefulSet 序号选择以及整个工作负载的删除属于不同路径。
* **异步性**：并发更新、就绪状态变化和其他选择条件都可能覆盖预期偏好。新 Pod 需要自己的注解；该提示不是持久的应用状态。


## 自定义调度器监控与调试

实现自定义调度器后，监控和调试非常重要。本节介绍如何监控和调试自定义调度器。

### 监控架构

该架构是监控集成方式的示例选择；下面的具体配置使用调度器自身的 HTTPS 端点和 Prometheus Operator。

### 关键监控指标

应将尝试延迟、尝试结果和队列深度作为不同的信号；其名称和单位已在下文核实。

### 日志

通过检查自定义调度器的日志，可以了解调度决策：

```bash
kubectl logs -n scheduler-lab -l app=custom-scheduler --prefix --tail=100
```

### 检查事件

可以检查与 Pod 调度相关的事件：

```bash
kubectl -n scheduler-lab get events --field-selector involvedObject.name=<pod-name>
```

### 指标采集

下面的示例监控的是**辅助调度器**；它自身会在 10259 端口上提供 HTTPS 指标，因此不需要指标 sidecar。示意图中的 AMP、CloudWatch、日志采集器和告警路由都需要单独配置集成。

前提条件：已有的 Prometheus Operator 堆栈具备发现权限；为 `custom-scheduler.scheduler-lab.svc` 准备服务证书，并将其私钥存储在 `scheduler-lab` 命名空间的 `custom-scheduler-serving-tls` Secret 中。将公有 CA 放入 `monitoring/custom-scheduler-ca`，键名为 `ca.crt`。`monitoring/scheduler-scrape-token` Secret 必须包含 Prometheus ServiceAccount 的有效**短期轮换**令牌；此处未实现令牌的配置和轮换。

仅在准备好该 PKI 后，才将以下内容作为**战略合并补丁**应用到完整的第 1 部分 Deployment。该补丁会保留现有镜像/配置/ServiceAccount 并挂载服务私钥。请使用受控的发布流程；本次审查未执行 TLS 发布。

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: custom-scheduler
  namespace: scheduler-lab
spec:
  template:
    spec:
      containers:
      - name: custom-scheduler
        args:
        - --config=/etc/scheduler/config.yaml
        - --tls-cert-file=/etc/scheduler-serving/tls.crt
        - --tls-private-key-file=/etc/scheduler-serving/tls.key
        volumeMounts:
        - name: serving-tls
          mountPath: /etc/scheduler-serving
          readOnly: true
      volumes:
      - name: serving-tls
        secret:
          secretName: custom-scheduler-serving-tls
          defaultMode: 288
```

Service 会公开命名的 HTTPS 端口。请将示例 `monitoring/prometheus` ServiceAccount 替换为实际的抓取身份。额外的 ClusterRole 只允许对非资源路径 `/metrics` 执行 GET；它不提供发现权限。确保 Prometheus 资源会选择此 ServiceMonitor 的标签/命名空间。

```yaml
apiVersion: v1
kind: Service
metadata:
  name: custom-scheduler
  namespace: scheduler-lab
  labels:
    app: custom-scheduler
spec:
  selector:
    app: custom-scheduler
  ports:
  - name: https
    port: 10259
    targetPort: https
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: custom-scheduler-metrics
rules:
- nonResourceURLs:
  - /metrics
  verbs:
  - get
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: custom-scheduler-metrics
subjects:
- kind: ServiceAccount
  name: prometheus
  namespace: monitoring
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: custom-scheduler-metrics
---
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: custom-scheduler
  namespace: monitoring
  labels:
    app: custom-scheduler
spec:
  namespaceSelector:
    matchNames:
    - scheduler-lab
  selector:
    matchLabels:
      app: custom-scheduler
  endpoints:
  - port: https
    path: /metrics
    scheme: https
    interval: 15s
    tlsConfig:
      serverName: custom-scheduler.scheduler-lab.svc
      ca:
        configMap:
          name: custom-scheduler-ca
          key: ca.crt
    authorization:
      type: Bearer
      credentials:
        name: scheduler-scrape-token
        key: token
```

### 仪表板配置

稳定指标 `scheduler_scheduling_attempt_duration_seconds` 带有 `result` 和 `profile` 标签；其直方图可用于估算尝试延迟。`scheduler_schedule_attempts_total` 是计数器，因此应使用 rate 计算吞吐量。原始 `_count` 不是持续时间。辅助调度器不同于 `kubectl get --raw /metrics`，后者会返回 API 服务器指标。

替换 `PROMETHEUS_UID` 并导入嵌入的 JSON，或者配置 Grafana 仪表板 provider/sidecar 来读取此 ConfigMap。仅创建 ConfigMap 不会加载 Grafana。`grafana_dashboard: "1"` 标签是常见的 provider 约定，必须与你的设置相匹配；实际导入和查询均未执行。

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: custom-scheduler-dashboard
  namespace: monitoring
  labels:
    grafana_dashboard: '1'
data:
  custom-scheduler-dashboard.json: |
    {
      "id": null,
      "uid": "custom-scheduler",
      "title": "Custom Scheduler",
      "schemaVersion": 39,
      "version": 1,
      "refresh": "30s",
      "time": {
        "from": "now-1h",
        "to": "now"
      },
      "panels": [
        {
          "id": 1,
          "title": "Successful scheduling attempt p95",
          "type": "timeseries",
          "gridPos": {
            "h": 8,
            "w": 12,
            "x": 0,
            "y": 0
          },
          "datasource": {
            "type": "prometheus",
            "uid": "PROMETHEUS_UID"
          },
          "targets": [
            {
              "refId": "A",
              "expr": "histogram_quantile(0.95, sum by (le, profile) (rate(scheduler_scheduling_attempt_duration_seconds_bucket{profile=\"custom-scheduler\",result=\"scheduled\"}[5m])))",
              "legendFormat": "{{profile}}",
              "instant": false
            }
          ],
          "fieldConfig": {
            "defaults": {
              "unit": "s"
            },
            "overrides": []
          },
          "options": {}
        },
        {
          "id": 2,
          "title": "Scheduling attempts per second",
          "type": "timeseries",
          "gridPos": {
            "h": 8,
            "w": 12,
            "x": 12,
            "y": 0
          },
          "datasource": {
            "type": "prometheus",
            "uid": "PROMETHEUS_UID"
          },
          "targets": [
            {
              "refId": "A",
              "expr": "sum by (result) (rate(scheduler_schedule_attempts_total{profile=\"custom-scheduler\"}[5m]))",
              "legendFormat": "{{result}}",
              "instant": false
            }
          ],
          "fieldConfig": {
            "defaults": {
              "unit": "ops"
            },
            "overrides": []
          },
          "options": {}
        }
      ]
    }
```

## 结论

自定义调度器是针对特定需求定制 Kubernetes 调度行为的有力方式。在 EKS 中，可以通过多调度器方法、调度器扩展程序方法和调度器框架插件方法等多种方式实现自定义调度器。

自定义调度器可用于多种场景，例如 GPU 工作负载优化和网络局部性优化。实现自定义调度器时，也应配置监控和调试工具。

## 参考资料与验证范围

* [ReplicaSet 删除成本及其限制](https://kubernetes.io/docs/concepts/workloads/controllers/replicaset/#pod-deletion-cost)
* [Pod 中断预算](https://kubernetes.io/docs/concepts/workloads/pods/disruptions/)
* [固定版本的 ReplicaSet 删除路径](https://github.com/kubernetes/kubernetes/blob/v1.35.8/pkg/controller/replicaset/replica_set.go)
* [固定版本的删除顺序](https://github.com/kubernetes/kubernetes/blob/v1.35.8/pkg/controller/controller_utils.go)
* [调度器指标](https://github.com/kubernetes/kubernetes/blob/v1.35.8/pkg/scheduler/metrics/metrics.go)
* [kube-state-metrics Pod 指标](https://github.com/kubernetes/kube-state-metrics/blob/main/docs/metrics/workload/pod-metrics.md)
* [Kubernetes Python 客户端 API](https://github.com/kubernetes-client/python/blob/v35.0.0/kubernetes/client/api_client.py)

本地测试使用合成 Pod、伪造 API 客户端和算术测试数据。它们不代表重新运行基准测试、真实 GPU 利用率、实时 Pod 删除、应用预热、证书/令牌轮换或生产环境可用性。

## 测验

若要检验你对本章内容的掌握情况，请尝试[主题测验](../quizzes/scheduling/02-custom-scheduler-part3-quiz.md)。
