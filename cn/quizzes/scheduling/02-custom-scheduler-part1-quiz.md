# 自定义调度器测验（第 1 部分）

> **示例基准**：Kubernetes 1.35.8，Go 1.27.2
> **最后更新**：October 16, 2026

本测验考查你对 Kubernetes 中自定义调度器的实现和使用的理解。

## 测验问题

### 1. 调度器在 Kubernetes 中的主要作用是什么？

A. 创建和删除 Pod
B. 将 Pod 分配到合适的节点
C. 监控节点资源
D. 下载容器镜像

<details>
<summary>显示答案</summary>

**答案：B. 将 Pod 分配到合适的节点**

**说明：**
调度器在 Kubernetes 中的主要作用是将 Pod 分配到合适的节点。调度器会监视新创建的 Pod，并为尚未分配到节点的 Pod 找到最合适的运行节点。

**调度器的主要功能：**
1. **Pod-节点分配**：结合 Pod 的要求和节点的可用资源，选择最合适的节点。
2. **过滤**：排除无法运行该 Pod 的节点（例如资源不足、存在污点等）。
3. **评分**：为合适的节点评分，以选出最合适的节点。
4. **绑定**：将 Pod 绑定到选定的节点，完成调度决策。

**调度流程（Kubernetes 1.35.8）：**
1. **过滤**：`NodeResourcesFit` 将有效资源请求与剩余可分配资源进行比较；`NodePorts` 检查请求的主机端口；`NodeAffinity` 处理节点选择器和亲和性；`TaintToleration` 检查污点。`VolumeBinding`、`VolumeZone` 和 `NodeVolumeLimits` 等卷插件会强制执行存储约束。节点压力通过节点状况/污点体现；`CheckNodeDiskPressure` 之类的名称是历史谓词，并非当前可配置的插件。
2. **评分**：`NodeResourcesFit`（默认使用 `LeastAllocated`）、`NodeResourcesBalancedAllocation`、`NodeAffinity`、`InterPodAffinity`、`PodTopologySpread`、`TaintToleration` 和 `ImageLocality` 会影响调度偏好。它们并非都用于衡量实时资源利用率。
3. **绑定**：其余框架阶段成功后，调度器会记录节点分配结果。随后由 Kubelet 和运行时管理执行过程。高分并不保证 Pod 能启动、延迟表现良好或服务可用。

**次级调度器配置示例：**
此配置会更改一个评分权重，并保留默认过滤器。本测验中的配置均为通过 `--config` 使用的文件，而不是可用 `kubectl` 应用的 Kubernetes API 资源。
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

**其他选项的问题：**
- A. 创建和删除 Pod：这主要是控制器管理器和 API 服务器的职责。
- C. 监控节点资源：这主要是 kubelet 和 metrics server 的职责。
- D. 下载容器镜像：这是 kubelet 和容器运行时的职责。
</details>

### 2. 以下哪项不是实现自定义调度器的方法？

A. 扩展现有的 kube-scheduler
B. 实现一个全新的调度器
C. 开发调度框架插件
D. 修改 kubelet

<details>
<summary>显示答案</summary>

**答案：D. 修改 kubelet**

**说明：**
修改 kubelet 不是实现自定义调度器的方法。kubelet 是运行在每个节点上的代理，负责管理 Pod 的执行，但它不会做出调度决策。调度由 kube-scheduler 或自定义调度器执行。

**实现自定义调度器的方法：**

1. **配置基于 kube-scheduler 的次级调度器**：保留默认插件，仅调整所需行为。Part1 提供完整的命令、RBAC、ConfigMap 和 Deployment。

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

2. **实现独立调度器**：这要求正确实现缓存、队列、list/watch 恢复、资源记账、卷协调、重试、领导者选举和绑定逻辑。仅使用 watch 的循环会遗漏现有 Pod 和连接断开情况；生产代码应使用 informer/workqueue，并处理 tombstone、取消操作和过期对象。选择一个 Ready 节点并不能证明 Pod 能适配该节点。因此，Part1 示例将这些工作委托给上游 kube-scheduler。

3. **开发框架插件**：将插件编译进调度器二进制文件，并通过 `app.WithPlugin` 注册。问题 4 提供完整的 Filter 插件，问题 6 提供 Score 插件，问题 7 提供注册命令。这些插件接口固定对应 `k8s.io/kube-scheduler/framework` v0.35.8；不同 Kubernetes 次版本的签名可能不同。

**kubelet 的职责：**
kubelet 是运行在每个节点上的代理，负责以下工作：
- 根据 Pod 规格运行和管理容器
- 监控并报告节点状态
- 执行容器健康检查
- 管理卷挂载

kubelet 执行调度器做出的决策（在哪个节点上运行哪个 Pod），但它本身不做调度决策。

**其他选项的说明：**
- A. 扩展现有的 kube-scheduler：这是实现自定义调度器的有效方法。
- B. 实现一个全新的调度器：这是实现自定义调度器的有效方法。
- C. 开发调度框架插件：这是实现自定义调度器的有效方法。
</details>

### 3. Pod 中使用哪个字段来指定特定调度器？

A. spec.scheduler
B. spec.schedulerName
C. metadata.scheduler
D. spec.nodeName

<details>
<summary>显示答案</summary>

**答案：B. spec.schedulerName**

**说明：**
Pod 中用于指定特定调度器的字段是 `spec.schedulerName`。设置此字段后，只有名称与指定值匹配的调度器才会调度该 Pod。默认值为 "default-scheduler"。

**Pod 规格示例：**
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
    image: nginx:1.30.6
    resources:
      requests:
        memory: "64Mi"
        cpu: "250m"
      limits:
        memory: "128Mi"
        cpu: "500m"
```

此 Pod 只会由名为 "custom-scheduler" 的调度器进行调度。如果集群中不存在该名称的调度器，Pod 将一直处于 `Pending` 状态。

**配置调度器名称：**
使用完整的 Part1 Deployment，并将此配置挂载为 `/etc/scheduler/config.yaml`，同时设置 `--config=/etc/scheduler/config.yaml`。`--scheduler-name` 不是当前使用的配置方式。ServiceAccount 和 Lease 权限是前置条件。

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

**选择调度器时的注意事项：**
1. **可用性**：如果指定的调度器没有运行，Pod 将无法调度。
2. **功能**：不同调度器可以使用不同的调度算法和策略。
3. **策略路由**：`schedulerName` 用于选择调度器配置文件；它本身不提供安全性或资源隔离。
4. **专用硬件**：可使用专用调度器来处理 GPU 或 FPGA 等特殊硬件。

**检查调度器状态：**
```bash
# Check pod status
kubectl get pod custom-scheduled-pod

# Check scheduling events
kubectl describe pod custom-scheduled-pod | grep -A 5 Events

# Check scheduler logs
kubectl logs -n scheduler-lab -l app=custom-scheduler --prefix --tail=100
```

**其他选项的问题：**
- A. spec.scheduler：Kubernetes API 中不存在此字段。
- C. metadata.scheduler：Kubernetes API 中不存在此字段。
- D. spec.nodeName：此字段用于绕过调度器，将 Pod 直接分配给特定节点。它不是用于指定调度器的字段。
</details>
### 4. Kubernetes 调度框架中“Filter”扩展点的作用是什么？

A. 为节点评分
B. 将 Pod 绑定到节点
C. 排除无法运行 Pod 的节点
D. 对调度队列中的 Pod 排序

<details>
<summary>显示答案</summary>

**答案：C. 排除无法运行 Pod 的节点**

**说明：**
Kubernetes 调度框架中“Filter”扩展点（以前称为“Predicate”）的作用是排除无法运行 Pod 的节点。Filter 插件会检查每个节点是否满足 Pod 的要求，并将不满足要求的节点从候选列表中排除。

**调度框架扩展点：**
* **PreEnqueue / QueueSort**：控制队列准入，并对排队中的 Pod 排序。
* **PreFilter / Filter**：准备共享状态，并排除不符合条件的节点。
* **PostFilter**：在没有可行节点时尝试恢复，例如执行抢占。
* **PreScore / Score / 可选的 NormalizeScore**：准备可行节点并进行排序；插件归一化后的分数必须在 0–100 之间。
* **Reserve / Unreserve**：记录假定状态，并在调度失败时撤销。这不是实际的 CPU 或设备分配。
* **Permit**：允许、拒绝或等待后续操作。
* **PreBind / Bind / PostBind**：准备依赖项、提交绑定并执行绑定后的工作。`PostBind` 无法否决已提交的绑定。接口可能会因版本而添加方法，因此应针对目标版本进行编译。

**默认过滤器：**
`NodeResourcesFit`、`NodeName`、`NodeUnschedulable`、`NodePorts`、`TaintToleration`、`NodeAffinity`、`InterPodAffinity`、`PodTopologySpread`、`VolumeRestrictions`、`NodeVolumeLimits`、`VolumeBinding` 和 `VolumeZone` 分别处理不同的约束。旧的谓词名称和特定云提供商的 `EBSLimits` 并非当前的插件名称。

**自定义 Filter 示例（`plugins/filter.go`）：**
此简单的标签规则通常可以通过 required node affinity 实现。这里用它来演示框架接口。通过抢占其他 Pod 无法解决缺少标签的问题，但之后节点标签发生更改时，Pod 可能会重新获得调度资格。

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

**在保留默认插件的同时启用自定义 Filter：**
问题 7 会注册此插件。添加标签检查时，不要禁用 `NodeResourcesFit`。

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

**其他选项的问题：**
- A. 为节点评分：这是“Score”扩展点的职责。
- B. 将 Pod 绑定到节点：这是“Bind”扩展点的职责。
- D. 对调度队列中的 Pod 排序：这是“Queue Sort”扩展点的职责。
</details>

### 5. 以下哪项任务由 kubelet 和容器运行时执行，而不是由调度器执行？

A. 评估节点资源请求和可分配资源
B. 考虑 Pod 优先级和抢占
C. 下载镜像层并创建容器
D. 评估节点亲和性和 Pod 间亲和性

<details>
<summary>显示答案</summary>

**答案：C. 下载镜像层并创建容器**

**说明：**
调度器选择节点；kubelet 则请求运行时拉取镜像并创建容器。**镜像本地性可以影响调度**：默认的 `ImageLocality` 评分插件会使用节点报告的缓存镜像及其大小。缓存报告可能已过时，也不能保证无需拉取镜像。

**实现注意事项：**
1. **资源**：保留 `NodeResourcesFit`；它会使用有效请求和调度器缓存中已分配/假定的资源用量。实时 CPU/内存指标属于不同的输入。CPU/内存限制可以超额分配，且不是默认的适配测试。
2. **优先级**：谨慎使用 PriorityClass 和 preemptionPolicy。如果抢占无法满足亲和性、卷或其他约束，高优先级 Pod 仍可能处于 Pending 状态。
3. **放置**：required node affinity 会限制符合条件的节点；preferred affinity 会影响节点评分。请将下面示例中的 AZ 替换为确实具有可用容量的可用区。通常，GPU 和拓扑需求无需自定义调度器。

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
    image: nginx:1.30.6
    resources:
      requests:
        cpu: 100m
        memory: 64Mi
```

4. **其他约束**：保留污点/容忍度、拓扑分布、存储拓扑/挂载限制和硬件资源检查。只有在存在可靠拓扑数据时，才应对网络本地性建模；标签本身不能证明延迟情况。
5. **镜像处理**：`ImageLocality` 只是偏好，不代表容量或启动保证。节点上仍可能发生镜像垃圾回收、注册表身份验证和拉取失败。

**其他选项：**
A、B 和 D 都是合理的调度考量。这里的区别在于放置和运行时操作，而不是调度与镜像信息之间的区别。
</details>
### 6. Kubernetes 调度框架中“Score”扩展点的作用是什么？

A. 排除无法运行 Pod 的节点
B. 为通过过滤的节点评分
C. 将 Pod 绑定到节点
D. 对调度队列中的 Pod 排序

<details>
<summary>显示答案</summary>

**答案：B. 为通过过滤的节点评分**

**说明：**
Kubernetes 调度框架中“Score”扩展点（以前称为“Priority”）的作用是为通过过滤的节点评分。评分插件会为每个节点赋分，并根据分数选择最合适的节点。

**评分流程：**
1. 每个评分插件都会计算分数；经过可选的归一化后，分数必须处于 0–100 范围内。
2. 每个插件的分数都会根据配置的权重加权。
3. 所有插件的加权分数会相加。
4. 总分最高的节点会被选中来放置 Pod。

**默认评分插件：**
Kubernetes 提供以下默认评分插件：

1. **NodeResourcesBalancedAllocation**：倾向于让 CPU 和内存请求占比保持平衡，而不是依据测得的利用率。
2. **NodeResourcesFit**：根据请求量和可分配资源，使用所配置的 LeastAllocated、MostAllocated 或 RequestedToCapacityRatio 策略。
3. **NodeAffinity**：根据节点亲和性规则评分。
4. **InterPodAffinity**：根据 Pod 间亲和性/反亲和性规则评分。
5. **PodTopologySpread**：优先选择有助于在各拓扑域间均匀分布 Pod 的节点。
6. **TaintToleration**：对 Pod 无法容忍的 PreferNoSchedule 污点进行惩罚；硬性污点由过滤阶段处理。
7. **ImageLocality**：优先选择已具有所需容器镜像的节点。

**自定义评分插件（`plugins/score.go`）：**
此示例中的节点标签由管理员控制，是策略输入。无效值会导致评分周期失败，而不会悄悄生成一个偏好。有效的零分并不等同于过滤。

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

**双插件算术示例的权重：**
以下配置会刻意只替换 **Score** 插件集。默认 Filter 插件仍会启用。实际策略中，应保留所需的其他评分偏好。

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

**评分结果示例：**
以下仅为演示性计算，并非实测结果：假设 A、B 和 C 均通过过滤，且两个启用的插件产生了以下最终 0–100 分数：

1. MyScorePlugin（权重：5）
   - 节点 A：80 分
   - 节点 B：60 分
   - 节点 C：90 分

2. NodeResourcesBalancedAllocation（权重：2）
   - 节点 A：70 分
   - 节点 B：90 分
   - 节点 C：50 分

加权总分：
- 节点 A：(80 x 5) + (70 x 2) = 400 + 140 = 540 分
- 节点 B：(60 x 5) + (90 x 2) = 300 + 180 = 480 分
- 节点 C：(90 x 5) + (50 x 2) = 450 + 100 = 550 分

在此情况下，节点 C 得分最高，因此 Pod 会被调度到节点 C。

**其他选项的问题：**
- A. 排除无法运行 Pod 的节点：这是“Filter”扩展点的职责。
- C. 将 Pod 绑定到节点：这是“Bind”扩展点的职责。
- D. 对调度队列中的 Pod 排序：这是“Queue Sort”扩展点的职责。
</details>

### 7. 以下哪项不是在 Kubernetes 中扩展调度器的方法？

A. 调度框架插件
B. 调度器扩展器
C. 部署多个调度器
D. 修改节点控制器

<details>
<summary>显示答案</summary>

**答案：D. 修改节点控制器**

**说明：**
修改节点控制器不是在 Kubernetes 中扩展调度器的方法。节点控制器是控制平面组件，负责监视和管理节点状态，与调度决策没有直接关系。

**扩展方法：**

1. **框架插件**在调度器内部运行。将问题 4/6 中完整的 Filter/Score 示例保存到 Part1 模块的 `plugins/` 下，并将此命令保存为 `cmd/with-plugins/main.go`。使用 `CGO_ENABLED=0 go build -buildvcs=false -o custom-scheduler ./cmd/with-plugins` 构建。仅进行注册并不会启用插件；必须在配置中引用该插件。

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

在此版本中，工厂函数接收 `(context.Context, runtime.Object, framework.Handle)`。这些示例不需要自定义参数。如果要添加配置，请使用带版本信息的框架运行时解码器解码并验证 `runtime.Unknown` 负载；不要将其断言为尚未注册的自定义类型。

2. **HTTP 扩展器**用于添加外部过滤/优先级处理，并可选择执行绑定。`extenders` 应位于**顶层**，而不是放在配置文件下。此示例配置要求实现扩展器服务、在所示路径挂载匹配的 TLS 证书、确保网络可达，并对错误进行有界处理。它不是可独立运行的服务器，也不是 EKS 托管调度器配置。将 `bindVerb` 留空会保留默认绑定器。

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

当 `ignorable: false` 时，扩展器过滤失败会阻止本次调度尝试。将其设为 true 可能绕过必须满足的自定义约束。优先级处理错误的方式有所不同：Kubernetes 1.35.8 会记录失败并忽略该扩展器的分数，因此不能用分数来强制实施必需规则。尽可能优先使用框架插件；并测试超时、重试和故障行为。

3. **多个调度器**使用不同的 `profiles[].schedulerName` 值和单独的领导者选举组。请使用完整的 Part1 Deployment/RBAC，而不要以默认调度器的身份或 Lease 启动第二个进程。

**节点控制器的职责：**
kubelet 通常负责注册节点并报告健康状态。节点生命周期控制器会监视心跳、更新状况/污点，并协调对不健康节点的响应。这些信息会影响调度，但修改节点控制器并不是调度器扩展 API。

**选择方案：**
评估实现复杂度、每个节点的 HTTP 开销、缓存一致性、故障行为和升级兼容性。在 EKS 上部署次级调度器；托管的默认调度器的标志和注册机制不由你替换。

**其他选项的说明：**
- A. 调度框架插件：这是有效的调度器扩展方法。
- B. 调度器扩展器：这是有效的调度器扩展方法。
- C. 部署多个调度器：这是有效的调度器扩展方法。
</details>
### 8. Kubernetes 调度器中 `--leader-elect` 标志的用途是什么？

A. 授予调度器领导权限
B. 在多个调度器实例中只激活一个实例
C. 仅在集群的领导节点上运行调度器
D. 让调度器拥有高于其他组件的优先级

<details>
<summary>显示答案</summary>

**答案：B. 在多个调度器实例中只激活一个实例**

**说明：**
Kubernetes 调度器中 `--leader-elect` 标志的用途是在高可用（HA）配置中确保只有一个调度器实例处于活动状态并执行工作。它用于协调同一 Lease 组中的副本；它并非适用于所有可能故障情况的隔离机制，也不能替代具备并发安全性的 API 操作。

**领导者选举机制：**
1. 部署多个调度器实例时，领导者选举算法会选出唯一一个领导者实例。
2. 只有当选的实例会执行实际调度工作。
3. 其他实例保持待机状态；当前领导者发生故障时，会选出新的领导者。
4. 此机制通过 Kubernetes 资源锁实现。

**领导者选举配置：**
使用带版本信息的配置文件来设置 Lease 标识和时序：

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

**HA Deployment：**
完整的 Part1 Deployment 已经使用相同的配置和 ServiceAccount 运行两个副本。在隔离的实验环境中，可以将副本扩展到三个。但这并不能建立生产级 HA：应验证故障域是否分离、API 是否可达、引导容量是否充足，以及故障转移行为是否正常。

```bash
kubectl -n scheduler-lab scale deployment/custom-scheduler --replicas=3
kubectl -n scheduler-lab get lease custom-scheduler -o yaml
kubectl -n scheduler-lab logs -l app=custom-scheduler --prefix --tail=100
```

**自定义实现：**
kube-scheduler 命令已集成 client-go 领导者选举。独立实现需要为每个进程分配唯一标识，为每个调度器组共享一个 Lease，授予续租权限，并在失去领导权时取消调度工作。client-go 机制无法防止所有可能的进程重叠情况；绑定和外部副作用仍需采用并发安全设计。使用 `ReleaseOnCancel` 时，必须先停止受保护的工作，再释放 Lease。

**何时适合禁用选举：**
仅在刻意隔离的实验中，或者有其他机制保证只有一个活动进程（包括滚动更新和故障期间）时，才禁用选举。滚动更新期间，`replicas: 1` 仍可能出现进程重叠。不同的调度器名称需要使用不同的选举组；仅有不同名称并不能确保禁用选举是安全的。

**其他选项的问题：**
- A. 授予调度器领导权限：这是含糊的描述，并未说明领导者选举的具体用途。
- C. 仅在集群的领导节点上运行调度器：调度器领导权属于进程，而不是某个通用的集群领导节点。次级调度器可以作为 Pod 运行在工作节点上。
- D. 让调度器拥有高于其他组件的优先级：领导者选举与优先级无关；它用于协调多个调度器实例。
</details>

### 9. Kubernetes 中使用哪种资源设置 Pod 调度优先级？

A. PodSchedulingPolicy
B. PriorityClass
C. SchedulingPriority
D. PodPriority

<details>
<summary>显示答案</summary>

**答案：B. PriorityClass**

**说明：**
Kubernetes 中用于设置 Pod 调度优先级的资源是 `PriorityClass`。PriorityClass 用于定义 Pod 的相对重要性，让调度器在进行调度和抢占决策时考虑优先级。

**PriorityClass 资源：**
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

**关键字段：**
1. **value**：优先级值；值越高，优先级越高。用户定义的值不得超过 1000000000；内置的关键类使用保留的更高取值范围。
2. **globalDefault**：设为 true 后，对于新准入且未指定类的 Pod，此类将成为集群范围的默认类；现有 Pod 不会被追溯性地更改。下面的所有实验类都使用 false。
3. **description**：优先级类的说明。
4. **preemptionPolicy**：抢占策略，可以设为 `PreemptLowerPriority`（默认值）或 `Never`。

**将 PriorityClass 应用于 Pod：**
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: high-priority-pod
spec:
  priorityClassName: high-priority  # Reference PriorityClass name
  containers:
  - name: nginx
    image: nginx:1.30.6
```

**优先级与抢占行为：**
1. **调度优先级**：高优先级 Pod 会优先在调度队列中处理。
2. **抢占**：如果没有节点可以调度高优先级 Pod，调度器可以移除（抢占）低优先级 Pod 以释放空间。
3. **抢占策略**：使用 `preemptionPolicy: Never` 的 Pod 不会抢占其他 Pod，但自身仍可能被抢占。队列退避可以让低优先级 Pod 继续调度，即使高优先级 Pod 无法适配。

**系统 PriorityClass：**
Kubernetes 提供以下系统 PriorityClass：
- **system-cluster-critical**：用于对集群运行至关重要的 Pod（值：2000000000）
- **system-node-critical**：用于对节点运行至关重要的 Pod（值：2000001000）

```bash
# Check system PriorityClasses
kubectl get priorityclasses | grep system
```

**PriorityClass 使用示例：**
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

**监控优先级和抢占相关指标：**
```bash
# Check preemption events
kubectl get events | grep -i preempt

# Check pod priorities
kubectl get pods -o custom-columns=NAME:.metadata.name,PRIORITY:.spec.priority
```

**在自定义调度器中处理优先级：**
实现自定义调度器时，应在调度决策中考虑 Pod 优先级。

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

**其他选项的问题：**
- A. PodSchedulingPolicy：Kubernetes API 中不存在此资源。
- C. SchedulingPriority：Kubernetes API 中不存在此资源。
- D. PodPriority：这不是资源类型，而是 Pod 规格中的一个字段（`spec.priority`）。PriorityClass 会自动设置此字段。
</details>

### 10. Kubernetes 调度器的 `NodeResourcesFit` 插件有什么作用？

A. 根据节点的物理位置放置 Pod
B. 将剩余可分配资源与 Pod 有效请求进行比较
C. 检查节点操作系统与 Pod 是否兼容
D. 测量节点网络带宽

<details>
<summary>显示答案</summary>

**答案：B. 将剩余可分配资源与 Pod 有效请求进行比较**

**说明：**
`NodeResourcesFit` 会将 Pod 的有效请求与节点的**可分配资源减去已分配/假定的请求**进行比较。它还会检查 Pod 数量上限和相关的扩展资源。它并非简单地将新 Pod 与总 `Capacity` 比较，也通常不会因为 CPU/内存限制总和超过容量而拒绝 Pod。

**资源记账：**
* 需要计入常规容器、顺序执行的 init 容器、可重启 sidecar、Pod 开销以及受支持的 Pod 级资源设置。API 默认值设置可能会根据限制值推导请求值。
* 使用调度器快照，包括假定的绑定；仅从 API 列表中汇总 Running Pod 会遗漏已预留的需求。
* 保留目标版本的功能门控和 DRA 行为。仅计算 CPU/内存并不足以完整实现资源适配检查。

**配置：**
`NodeResourcesFit` 默认启用。此示例更改其评分策略，但不会移除其 Filter 阶段。

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

**评分策略：**
NodeResourcesFit 插件支持以下评分策略：

1. **LeastAllocated**：节点请求占比越低，得分越高。适合分散资源用量。
   ```
   score ≈ 100 × (allocatable - requested) / allocatable
   ```

2. **MostAllocated**：节点请求占比越高，得分越高。适合集中资源用量，以尽量减少节点数量。
   ```
   score ≈ 100 × requested / allocatable
   ```

3. **RequestedToCapacityRatio**：根据请求资源与容量之比评分，使用配置的分段线性形状。上面的简化单资源公式未考虑整数舍入、零容量/超容量处理和资源权重；它们不是实时利用率公式。

**资源类型：**
NodeResourcesFit 插件会考虑以下资源类型：

1. **CPU**：以核或毫核为单位。
2. **内存**：以字节为单位。
3. **临时存储**：节点的本地临时存储。
4. **扩展资源**：GPU、FPGA 等自定义资源。

**检查节点资源：**
```bash
# Check node's allocatable resources
kubectl describe node <node-name> | grep Allocatable -A 5

# Check node's resource usage
kubectl top node <node-name>
```

**检查 Pod 资源请求：**
```bash
# Check pod's resource requests
kubectl get pod <pod-name> -o jsonpath='{.spec.containers[*].resources.requests}'
```

**安全地实现资源适配检查：**
在调度框架中保留上游插件。手写一个只汇总新 Pod 的 CPU/内存、忽略现有需求并返回 true 的函数，并不能有效替代该插件。配套审计会在本地检查固定版本的上游适配实现：对于 2 核节点上现有的 1500m 请求，另一个 1 核请求会被拒绝，而 250m 请求可以适配，即使 CPU 限制值更大。这是本地记账检查，并非集群调度基准测试。

如果 Metrics Server 可用，`kubectl top` 会报告当前指标；这些指标不是默认适配/评分所使用的资源请求总量。排查差异时，应检查完整的 Pod 规格，包括 init 容器和开销。

**其他选项的问题：**
- A. 根据节点的物理位置放置 Pod：这是拓扑相关插件（例如 NodeAffinity、PodTopologySpread）的职责。
- C. 检查节点操作系统与 Pod 是否兼容：根据需要使用 OS 标签和放置约束；但这些本身不能证明镜像/运行时兼容性。`NodeResourcesFit` 不负责此类检查。
- D. 测量节点网络带宽：Kubernetes 调度器默认不会考虑网络带宽。为此需要自定义指标和插件。
</details>

## 参考资料

示例使用 [Part1 模块和部署](../../scheduling/01-custom-scheduler-part1.md)。本地编译/配置/记账检查并不能证明已达到生产就绪状态；本示例未执行集群或 AWS 部署。

* [调度器配置和默认插件](https://kubernetes.io/docs/reference/scheduling/config/)
* [框架扩展点](https://kubernetes.io/docs/concepts/scheduling-eviction/scheduling-framework/)
* [资源评分](https://kubernetes.io/docs/concepts/scheduling-eviction/resource-bin-packing/)
* [优先级和抢占](https://kubernetes.io/docs/concepts/scheduling-eviction/pod-priority-preemption/)
* [固定版本的 Go 接口](https://github.com/kubernetes/kubernetes/blob/v1.35.8/staging/src/k8s.io/kube-scheduler/framework/interface.go)
