# 自定义调度器测验（第 3 部分）

> **示例基线**：Kubernetes 1.35.8、Go 1.27.2；原生 1.37 功能另行说明
> **最后更新**：October 16, 2026

本测验考查你对在 Kubernetes 中实现和使用自定义调度器的深入理解。

## 测验题目

### 1. 关于多个调度器，哪项说法不正确？

A. 额外的调度器会增加 API watch/cache 工作
B. 各自独立假定的放置可能会争抢资源
C. 添加调度器会自动增加节点容量
D. 不相关的调度器组需要使用不同的领导者选举 Lease

<details>
<summary>显示答案</summary>

**答案：C. 添加调度器会自动增加节点容量**

**解释：**
调度器负责分配 Pod；它不会创建节点容量。额外的调度器可能会增加 API/网络负载。每个调度器都会监视已提交的 Pod 状态，但其内存中的假定并不是与其他调度器共享的预留事务。在共享资源池上进行并发调度时，应保留资源过滤器并进行测试。

省略 `schedulerName` 时会选择 `default-scheduler`；这并不意味着所有符合要求的调度器都会来绑定该 Pod。同一调度器的副本会有意共享一个 Lease，以实现高可用。共享该 Lease 的不相关组可能会互相阻塞，而使用相同 profile 但未协调领导者选举的进程则可能发生竞争。

**Pod 路由示例：**

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: default-pod
spec:
  containers:
  - name: nginx
    image: nginx:1.30.6
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
    image: nginx:1.30.6
    resources:
      requests:
        cpu: 100m
        memory: 64Mi
```

**分离调度器身份和节点池策略：**
使用完整的 Part1 Deployment/RBAC。名称和 Lease 身份位于 `KubeSchedulerConfiguration` 中，而不是已过时的 `--scheduler-name` 标志中。内置 `NodeAffinity` 插件支持 profile 级别的 `addedAffinity`；默认情况下没有 `NodeSelector` 插件。

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

上面的自定义 Pod 能容忍示例污点。容忍不会强制放置，而且调度器名称、节点标签和配额都不是安全边界。以下命名空间配额会限制已准入的请求；它们不会预留节点池。请先创建命名空间，并为受这些配额约束的工作负载提供 requests。
**命名空间配额示例：**
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

**对次级调度器进行只读监控：**
使用实际的命名空间/标签。EKS 托管控制平面组件并非此处所示的次级 Deployment。

```bash
kubectl -n scheduler-lab get pods -l app=custom-scheduler
kubectl -n scheduler-lab logs -l app=custom-scheduler --prefix --tail=100
kubectl -n scheduler-lab get lease custom-scheduler
kubectl get pods -A --field-selector=spec.schedulerName=custom-scheduler,spec.nodeName= -o wide
```

**其他选项：**A、B 和 D 描述了实际的工作负载或协调方面的考量。
</details>

### 2. Kubernetes 调度器中“Permit”扩展点的作用是什么？

A. 将 Pod 绑定到节点
B. 允许、拒绝或延迟 Pod 调度
C. 排除 Pod 无法运行的节点
D. 为节点分配评分

<details>
<summary>显示答案</summary>

**答案：B. 允许、拒绝或延迟 Pod 调度**

**解释：**
Kubernetes 调度框架中“Permit”扩展点的作用是允许、拒绝或延迟 Pod 调度。Permit 插件在选定节点之后、绑定阶段之前运行，对 Pod 调度决策进行最终批准或拒绝。

**Permit 扩展点的主要功能：**
1. **允许**：允许 Pod 调度进入绑定阶段。
2. **拒绝**：拒绝 Pod 调度，以便选择其他节点。
3. **等待**：暂时延迟 Pod 调度，并等待满足特定条件。

**版本化的 Permit 契约：**
`Permit(ctx, fwk.CycleState, pod, nodeName)` 会返回状态和等待时长。`Success` 表示继续，`Wait` 要求框架暂缓处理该 Pod，而诸如 `Unschedulable` 之类的失败状态则会拒绝本次尝试。不存在 `framework.Deny` 枚举。拒绝并不会立即绑定到另一个节点；之后会进行重试/退避并清理预留。

`TaintToleration` 和 `PodTopologySpread` 不是默认的 Permit 插件。基线会保留它们实际的 Filter/Score 阶段。

**完整接口示例（`quizplugins/permit.go`）：**
注解值是测试指令，不是可信的授权机制。这里没有提供外部审批服务。除非集成测试驱动程序在框架注册 Pod 后将其释放，否则 `wait` Pod 会超时；未被使用的私有 channel 无法释放框架中的等待者。

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

在 `cmd/quiz-scheduler/main.go` 中注册此示例和后面的 PreBind 示例；构建前保存两个源文件：

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

使用 Part1 模块通过 `CGO_ENABLED=0 go build -buildvcs=false -o custom-scheduler ./cmd/quiz-scheduler` 进行构建。只启用相关扩展点，并保留默认配置：

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

**Permit 的用例：**
1. **Gang 调度**：延迟调度一组 Pod，直到所有相关 Pod 都准备好被调度。
2. **资源预留**：在调度 Pod 前预留外部资源。
3. **策略验证**：确保 Pod 调度符合组织策略。
4. **审批工作流**：请求对 Pod 调度进行外部审批。

**为什么 Permit 屏障并不是完整的 gang 调度器：**
真正的实现必须按命名空间/UID 限定组身份，统计唯一成员，处理重试/删除/超时，在失败时释放预留，并考虑绑定失败。不要自行构造 `WaitingPod`、将同一次重试重复计数，或在 Permit 返回前就认为当前 Pod 已注册。屏障无法保证容器同时启动，也无法确保不会发生饥饿。问题 3 会介绍已维护的实现。

**其他选项的问题：**
- A. 将 Pod 绑定到节点：这是“Bind”扩展点的作用。
- C. 排除 Pod 无法运行的节点：这是“Filter”扩展点的作用。
- D. 为节点分配评分：这是“Score”扩展点的作用。
</details>
### 3. Kubernetes 中 Gang 调度的主要目的是什么？

A. 仅将 Pod 放置到特定节点
B. 协调一组必需 Pod 的放置
C. 将 Pod 均匀分布到不同节点
D. 根据优先级调度 Pod

<details>
<summary>显示答案</summary>

**答案：B. 协调一组必需 Pod 的放置**

**解释：**
Kubernetes 中 Gang 调度的主要目的是协调一组必需 Pod 的放置，然后才允许其继续运行。这对于分布式训练作业和分布式数据处理作业等工作负载非常重要，因为所有组件都必须同时运行。

**Gang 调度的必要性：**
1. **全有或全无的要求**：某些工作负载要求所有组件同时运行；如果只有部分组件运行，作业就无法推进。
2. **避免资源浪费**：如果只有部分 Pod 被调度，而其他 Pod 仍在等待，已调度 Pod 使用的资源可能会被浪费。
3. **避免死锁**：相互依赖的 Pod 在不同时间被调度时可能发生死锁。

**实现选项和版本：**
上游 Kubernetes 1.35 引入了选择启用的 alpha `GenericWorkload`/`GangScheduling`。当前上游 1.37 的 PodGroup 调度功能处于 **beta 阶段且默认禁用**，需要启用 `GenericWorkload` 和 `scheduling.k8s.io/v1beta1` API。这并不能证明 EKS 提供了该功能，也不表示可以更改托管控制平面标志。

Volcano 是一种可安装的替代调度器；Kube-batch 是其历史前身，并非另一种当前推荐方案。使用该方案需要受支持的控制器、其 CRD、已启用的 gang 调度以及 Open 队列。

**Volcano Job 示例（根据 1.15.2 检查 schema）：**
控制器会创建 PodGroup。此处定义了全部四个成员，与只有一个 Pod 的 minMember 为 4 的组不同。这个纯 CPU 的 sleep 工作负载展示的是清单之间的关系，不是分布式训练或基准测试。该示例未实际部署。

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
          image: busybox:1.38.0
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

调度决策会协调满足最小组规模的成员；它不会让进程在同一时刻启动。应用程序屏障、超时策略、公平性和恢复机制仍然必不可少。原生 PodGroup 放置对异构 Pod 和 Pod 间依赖也有已记录的限制；其排序算法并不总能找到可行的放置方案。

**Gang 调度的优缺点：**
优点：
- 协调已配置的最小组规模
- 避免资源浪费
- 可以减少部分分配导致的死锁；公平性和超时仍需考虑

缺点：
- 实现复杂度更高
- 可能增加调度延迟
- 可能降低集群资源利用率

**需要 Gang 调度的工作负载：**
1. **分布式训练作业**：TensorFlow、PyTorch 等分布式训练框架
2. **分布式数据处理**：Spark、Flink 等分布式数据处理框架
3. **MPI 作业**：高性能计算（HPC）工作负载
4. **紧密耦合的并行作业**：要求预先声明最小工作节点集合的工作负载

**其他选项的问题：**
- A. 仅将 Pod 放置到特定节点：这是节点选择器或节点亲和性的作用。
- C. 将 Pod 均匀分布到不同节点：这是 Pod 拓扑分布约束的作用。
- D. 根据优先级调度 Pod：这是 Pod 优先级和抢占的作用。
</details>

### 4. 以下哪项功能不属于 kube-scheduler extender 回调契约？

A. 过滤候选节点
B. 为候选节点排序
C. 可选的 Pod 到节点绑定
D. 通过 ValidatingWebhookConfiguration 进行准入验证

<details>
<summary>显示答案</summary>

**答案：D. 通过 ValidatingWebhookConfiguration 进行准入验证**

Extender 可以实现已配置的 filter、prioritize、preempt 和 bind 回调。没有任何字面 URL 路径是必需的：`filterVerb` 甚至可以将路径命名为 `validate`，但其负载/含义仍然是过滤。准入 Webhook 属于另一种 API 契约。

**配置：**
复用 Part2 中的 TLS 服务/证书先决条件。`extenders` 位于顶层。让必需的过滤采用失败关闭策略，并保留调度器自身的资源核算。

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

**线路契约：**
* Filter/prioritize 使用包含 `Pod` 和完整 `Nodes` 或 `NodeNames` 的 `ExtenderArgs`，具体取决于 `nodeCacheCapable`。
* Filter 返回 `Nodes`/`NodeNames`、失败映射和 `Error`。
* Prioritize 返回一个裸数组，例如 `[{"Host":"node-a","Score":7}]`；分数范围是 0–10，而不是 100。优先级回调出错时会忽略该 extender 的分数，因此不能用分数强制执行必需约束。
* Bind 使用 `PodName`、`PodNamespace`、`PodUID` 和 `Node`。只有真实绑定成功后才返回成功；返回 nil 的 `customBind` 存根并不是绑定实现。
* Preempt 使用带有候选受害者映射的 `ExtenderPreemptionArgs`，并返回 `ExtenderPreemptionResult.NodeNameToMetaVictims`。它不会返回臆造的 `podsToPreempt` 外层结构。

请使用 [Part2](../../scheduling/02-custom-scheduler-part2.md) 中完整且有界的处理程序。该处理程序不设置 `bindVerb`，以保留 `DefaultBinder`。此处未提供额外 HTTP 服务器或伪造成功的 bind 端点。
</details>
### 5. Kubernetes 调度框架中“PostFilter”扩展点的作用是什么？

A. 过滤后为节点分配评分
B. 过滤后将 Pod 绑定到节点
C. 过滤失败时执行抢占逻辑
D. 过滤后更新 Pod 状态

<details>
<summary>显示答案</summary>

**答案：C. 过滤失败时执行抢占逻辑**

**解释：**
当过滤未找到可行节点时，PostFilter 会尝试恢复；默认抢占就是一种实现。当过滤阶段排除所有节点，导致 Pod 无法调度时，PostFilter 插件可以尝试采取操作，使后续尝试能够找到可行方案。

**PostFilter 扩展点的主要功能：**
1. **识别抢占候选项**：识别可以被抢占的 Pod 和节点。
2. **模拟抢占**：模拟抢占 Pod 后是否可以调度。
3. **作出抢占决策**：确定最佳抢占策略。

**版本化接口和安全扩展：**
固定版本的 API 使用 `fwk.CycleState` 和 `fwk.NodeToStatusReader`；`PostFilterResult` 嵌入了 `NominatingInfo`。提名只是可能的下一个目标，并不是已提交的绑定。

除非你已有完整且经过测试的替代方案，否则应保留默认的 `DefaultPreemption` 实现。它会根据剩余约束评估优先级较低的受害者，并尽力考虑 PDB 违规情况。省略受害者选择后直接删除 Pod 的循环是不安全的。恢复插件也可以执行其他合适操作，因此按定义 PostFilter 并不局限于抢占。

以下配置会调整默认实现，但不会将其禁用。候选项限制会限定搜索范围；它们不保证全局最优或最终一定能调度成功。

**与抢占相关的设置：**
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

**抢占过程：**
1. 当 Pod 在所有节点上都未能通过过滤阶段时，会调用 PostFilter 阶段。
2. PostFilter 插件会识别抢占候选节点。
3. 确定每个节点上要抢占哪些 Pod。
4. 验证抢占后是否可以调度 Pod。
5. 选择最佳抢占策略。
6. 将选定节点设置为 Pod 的 nominatedNodeName。
7. 被抢占的 Pod 会进入优雅终止流程。
8. 受害者终止后会重试调度；提名不保证绑定成功。

**监控与抢占相关的指标：**
```bash
# Inspect nominations; scheduler metrics require its authenticated HTTPS endpoint.
kubectl get pods -A -o custom-columns=NAME:.metadata.name,NOMINATED:.status.nominatedNodeName
```

**检查抢占事件：**
```bash
# Check preemption events
kubectl get events | grep -i preempt
```

**其他选项的问题：**
- A. 过滤后为节点分配评分：这是“Score”扩展点的作用。
- B. 过滤后将 Pod 绑定到节点：这是“Bind”扩展点的作用。
- D. 过滤后更新 Pod 状态：这不是调度框架中的扩展点。
</details>

### 6. Kubernetes 调度器中“NodeResourcesBalancedAllocation”插件的主要目的是什么？

A. 为 CPU 和内存请求占比均衡的节点提供更高评分
B. 为资源使用率较低的节点提供更高评分
C. 为资源使用率较高的节点提供更高评分
D. 设置节点资源限制

<details>
<summary>显示答案</summary>

**答案：A. 为 CPU 和内存请求占比均衡的节点提供更高评分**

**解释：**
`NodeResourcesBalancedAllocation` 均衡的是**有效请求量/可分配资源的占比**，而非测得的 CPU/内存利用率。对于固定实现中的两个纳入计算的资源：

```
cpuFraction = min(requestedCPU / allocatableCPU, 1)
memoryFraction = min(requestedMemory / allocatableMemory, 1)
std = abs(cpuFraction - memoryFraction) / 2
score = int((1 - std) * 100)
```

请求总量包括传入的 Pod 和调度器已核算的请求。完整插件还会处理其特定版本的资源选项。对于超过两种纳入计算的资源，插件会使用总体标准差。

以下是说明性计算，并非实际测量值：占比分别为 80%/80% 时得分为 100；90%/50% 时得分为 80；30%/90% 时得分为 70。其他插件及其权重也会影响节点选择。

**在调度器配置中启用 NodeResourcesBalancedAllocation 插件：**
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

**插件配置：**
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

**NodeResourcesBalancedAllocation 与其他评分插件的比较：**
1. **NodeResourcesBalancedAllocation**：倾向于选择请求量/可分配资源占比均衡的节点。
2. **NodeResourcesFit**：使用其配置的 LeastAllocated、MostAllocated 或 RequestedToCapacityRatio 评分策略。
3. **NodeResourcesFit 的 LeastAllocated 策略**：倾向于选择请求占比较低的节点。
4. **NodeResourcesFit 的 MostAllocated 策略**：倾向于选择请求占比较高的节点。

**用例：**
1. **资源均衡**：改善整个集群的 CPU 和内存使用均衡性。
2. **避免瓶颈**：可以减少请求资源的不均衡；但无法避免运行时瓶颈。
3. **提升可扩展性**：资源使用均衡的集群可以更高效地扩展。

**计算辅助程序（`scoring/formulas.go`）：**
它会校验公式以及源章节中描述的可选 70:30 GPU 权重。这不是完整的调度器插件。应保留内置资源核算，包括 CPU 毫核、init/sidecar 容器、开销以及特定功能的处理。

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

**其他选项的问题：**
- B. 为资源使用率较低的节点提供更高评分：这是 NodeResourcesFit 的 LeastAllocated 策略。
- C. 为资源使用率较高的节点提供更高评分：这是 NodeResourcesFit 的 MostAllocated 策略。
- D. 设置节点资源限制：这不是调度器插件的作用；节点资源限制是节点自身的属性。
</details>
### 7. Kubernetes 调度器中“PreBind”扩展点的作用是什么？

A. 将 Pod 绑定到节点
B. 在绑定前执行必要操作
C. 在绑定后执行清理
D. 在绑定失败时执行恢复操作

<details>
<summary>显示答案</summary>

**答案：B. 在绑定前执行必要操作**

**解释：**
PreBind 会在 Pod 绑定提交之前协调前置工作。`VolumeBinding` 会与存储控制器协调调度相关的卷绑定/配置。不存在名为 `DefaultPreBind` 的默认插件。

1.35.8 版本的接口同时包含 `PreBindPreFlight` 和 `PreBind`，二者都使用 `fwk.CycleState`。对于 Pod，Preflight 可以返回 Skip，以避免不必要的工作。

**完整的只读示例（`quizplugins/prebind.go`）：**
此选择启用的身份检查不会配置卷、配置 CNI、创建 Service 端点或分配 GPU。这些操作需要对应的控制器/设备机制。`DefaultBinder` 已经携带 UID，因此这个额外的往返请求仅用于演示接口。

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

问题 2 中的命令会注册它。请保持 `VolumeBinding` 启用：

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

**职责边界：**
存储配置由相关的 provisioner/controller 执行；调度器负责协调放置和绑定。分配后，CNI 网络以及 Secret/卷挂载会通过运行时/kubelet 机制完成。Service/EndpointSlice/负载均衡器控制器会协调各自的资源。如果自定义插件要协调外部预留，就必须实现有界、幂等的操作以及自身的 Unreserve 清理；框架无法自动撤销任意外部副作用。

**PreBind 失败处理：**
当 PreBind 插件返回失败时：
1. 调度周期会中止。
2. Pod 会返回调度队列。
3. Unreserve 钩子会撤销插件拥有的假定；必须实际实现外部清理。
4. 系统会记录失败事件。

**监控 PreBind 日志和事件：**
```bash
# Check PreBind-related messages in scheduler logs
kubectl -n scheduler-lab logs -l app=custom-scheduler --prefix --tail=100

# Check pod events
kubectl describe pod <pod-name>
```

**其他选项的问题：**
- A. 将 Pod 绑定到节点：这是“Bind”扩展点的作用。
- C. 在绑定后执行清理：这是“PostBind”扩展点的作用。
- D. 失败后的恢复包括针对插件自身预留的 Unreserve，以及框架的重试处理。
</details>

### 8. Kubernetes 调度器中“NodeResourcesFit”插件的主要目的是什么？

A. 监控节点资源使用情况
B. 设置节点资源限制
C. 比较剩余可分配资源与有效 Pod 请求
D. 保持节点资源使用均衡

<details>
<summary>显示答案</summary>

**答案：C. 比较剩余可分配资源与有效 Pod 请求**

**解释：**
`NodeResourcesFit` 会将有效 Pod 请求与可分配资源**减去已分配/已假定的请求量**进行比较，同时考虑适用的 Pod 数量和扩展资源约束。它通常不会检查 CPU/内存 limits 的总和是否超过容量。必须核算由准入/默认值生成的请求、init 容器、可重启 sidecar、开销以及已启用的资源功能。

保留默认的 Filter 阶段。此配置会更改评分行为，但不会替换资源适配逻辑。

**NodeResourcesFit 插件配置：**
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

**评分策略：**
NodeResourcesFit 插件支持以下评分策略：

1. **LeastAllocated**：为请求占比较低的节点提供更高评分。
   ```
   score ≈ 100 × (allocatable - requested) / allocatable
   ```

2. **MostAllocated**：为请求占比较高的节点提供更高评分。
   ```
   score ≈ 100 × requested / allocatable
   ```

3. **RequestedToCapacityRatio**：对请求量/可分配资源比率使用配置的分段线性形状。以上公式是针对单一资源的简化示例。

**自定义实现注意事项：**
保留上游 `NodeResourcesFit`。只检查评分权重映射中列出的资源可能会遗漏必需资源，而且 CPU `Quantity.Value()` 会丢失毫核精度。只计算普通容器请求总和会遗漏 init/sidecar/开销行为。一个在缩放前截断占比的手写评分可能只会产生零值。

Part1 中的本地检查会执行实际的固定版本适配函数：在一台 2 核节点上，如果已请求 1500m，再请求 1 核就不适配；而请求 250m 即使 CPU limits 更大也能适配。这是合成的核算测试，不是集群基准测试。

**资源请求和限制示例：**
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: resource-demo
spec:
  containers:
  - name: nginx
    image: nginx:1.30.6
    resources:
      requests:
        cpu: "500m"
        memory: "256Mi"
      limits:
        cpu: "1"
        memory: "512Mi"
```

**其他选项的问题：**
- A. 监控节点资源使用情况：这是 metrics server 或监控系统的作用。
- B. 设置节点资源限制：这是节点配置或 kubelet 的作用。
- D. 保持节点资源使用均衡：这是“NodeResourcesBalancedAllocation”插件的作用。
</details>
### 9. Kubernetes 调度器中“InterPodAffinity”插件的主要目的是什么？

A. 处理 Pod 与节点之间的亲和性规则
B. 处理 Pod 之间的亲和性和反亲和性规则
C. 处理 Pod 与卷之间的亲和性规则
D. 处理 Pod 与 Service 之间的亲和性规则

<details>
<summary>显示答案</summary>

**答案：B. 处理 Pod 之间的亲和性和反亲和性规则**

**解释：**
Kubernetes 调度器中“InterPodAffinity”插件的主要目的是处理 Pod 之间的亲和性和反亲和性规则。此插件会控制 Pod 是否与其他 Pod 放置在相同的拓扑域（节点、区域、地域等）中（亲和性），或放置在不同的拓扑域中（反亲和性）。

**InterPodAffinity 插件的主要功能：**
1. **Pod 亲和性规则处理**：确保 Pod 与具有特定标签的其他 Pod 位于同一拓扑域。
2. **Pod 反亲和性规则处理**：确保 Pod 与具有特定标签的其他 Pod 位于不同拓扑域。
3. **拓扑域考量**：考虑节点、区域和地域等不同级别的拓扑域。

**Pod 亲和性和反亲和性类型：**
1. **requiredDuringSchedulingIgnoredDuringExecution**：Pod 调度必须满足的规则（硬性要求）。
2. **preferredDuringSchedulingIgnoredDuringExecution**：优先满足但非必需的规则（软性要求）。

**Pod 亲和性和反亲和性示例：**
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
    image: nginx:1.30.6
```

**InterPodAffinity 插件配置：**
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

**使用完整的内置实现：**
保留 `InterPodAffinity` 及其预处理逻辑。它会考虑命名空间选择、传入 Pod 的必需条件、已有 Pod 的必需反亲和性、拓扑结构以及自亲和性引导行为。原始的 `*v1.Affinity` 并不是带有 Clone 方法的框架 StateData，且状态缺失时不得静默绕过必需检查。

在此示例中，所选命名空间中必须存在合适的 `app=cache` Pod。首选反亲和性不保证 Pod 一定分开。`hardPodAffinityWeight` 会影响评分，但不会放宽必需约束。请使用实际工作负载测试规模和放置策略之间的权衡；共置并不能证明延迟达到某个下限。

**Pod 亲和性和反亲和性的用例：**
1. **高可用性**：将同一应用的实例分散到不同节点、区域或地域
2. **性能优化**：在测量结果支持其争用/延迟权衡时，将互相通信的 Pod 放在一起
3. **资源隔离**：将资源密集型 Pod 分散到不同节点
4. **许可证限制**：将受许可证限制的应用集中到特定节点

**Pod 亲和性和反亲和性的性能影响：**
Pod 亲和性和反亲和性的计算开销可能很高，因为它们需要考虑所有节点和 Pod。在大型集群中，这可能会影响调度性能，因此应谨慎使用。

**其他选项的问题：**
- A. 处理 Pod 与节点之间的亲和性规则：这是“NodeAffinity”插件的作用。
- C. 处理 Pod 与卷之间的亲和性规则：这是“VolumeBinding”插件的作用。
- D. 处理 Pod 与 Service 之间的亲和性规则：这不是 Kubernetes 调度器插件。
</details>

### 10. Kubernetes 调度器中“NodeName”插件的主要目的是什么？

A. 验证 Pod 的 spec.nodeName 字段是否与节点名称匹配
B. 为节点分配名称
C. 为 Pod 分配节点名称
D. 验证节点名称格式

<details>
<summary>显示答案</summary>

**答案：A. 验证 Pod 的 spec.nodeName 字段是否与节点名称匹配**

**解释：**
Kubernetes 调度器中“NodeName”插件的主要目的是验证 Pod 的 `spec.nodeName` 字段是否与节点名称匹配。如果调用时 nodeName 非空，其谓词只会接受该名称。在正常操作中，预先分配了节点的 Pod 已经会从未调度队列中排除；并不是该插件本身导致了这种绕过行为。

**NodeName 插件的主要功能：**
1. **节点名称验证**：如果设置了 Pod 的 `spec.nodeName` 字段，则只会选择名称匹配的节点。
2. **字段语义**：spec.nodeName 直接指定节点名称；它不是调度器的选择字段。
3. **绕过调度器**：设置了 `spec.nodeName` 的 Pod 会绕过正常调度逻辑，直接分配到指定节点。

**等效的名称检查谓词：**
此辅助程序用于说明内置检查；不要注册一个名为 `NodeName` 的替代插件。

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

**指定 nodeName 的 Pod 示例：**
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: nginx
spec:
  nodeName: worker-node-1  # Direct assignment to specific node
  containers:
  - name: nginx
    image: nginx:1.30.6
```

**使用 nodeName 时的注意事项：**
1. **绕过调度器**：使用 `nodeName` 会绕过调度器的过滤、评分和其他逻辑。
2. **节点是否存在**：节点名称错误/缺失不会触发对备用节点的选择。
3. **准入仍然适用**：虽然会绕过调度器的适配检查，但 kubelet 准入仍可能因资源不足而拒绝 Pod。
4. **其余约束**：会绕过 NoSchedule/亲和性调度检查，但 NoExecute 和节点端准入仍然适用。由于跳过了调度器卷协调，WaitForFirstConsumer PVC 可能会一直处于 Pending 状态。

`kubernetes.io/hostname` 标签不一定与 Node 对象名称相同。使用下面的标签示例前，请检查该标签的实际值。

**nodeName 与 nodeSelector 和 nodeAffinity 的比较：**
1. **nodeName**：直接分配到特定节点。限制最多，灵活性最低。
2. **nodeSelector**：根据标签选择节点。简单但表达能力有限。
3. **nodeAffinity**：支持复杂的节点选择规则。灵活性和表达能力最高。

**nodeName 的用例：**
1. **调试**：在特定节点上运行 Pod，以调试问题。
2. **测试**：在特定节点上运行测试。
3. **特殊硬件**：将 Pod 分配到具有特定硬件的节点。
4. **区分 Static Pod**：由 API 创建且指定了 nodeName 的 Pod 并不是 Static Pod；Static Pod 来源于 kubelet 本地配置。

**使用 nodeName 时的注意事项：**
1. **替换行为**：Pod 不会迁移。控制器可能会创建替代 Pod，但如果模板仍固定到同一个故障节点名称，就仍会限制这些 Pod。
2. **可扩展性有限**：节点名称是硬编码的，会限制可扩展性。
3. **维护困难**：如果节点名称发生变化，就需要更新 Pod 定义。
4. **无法负载均衡**：无法利用调度器的负载均衡功能。

**替代方案和建议：**
1. **使用 nodeSelector**：
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
       image: nginx:1.30.6
   ```

2. **使用 nodeAffinity**：
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
       image: nginx:1.30.6
   ```

**其他选项的问题：**
- B. 为节点分配名称：节点名称在创建节点时分配，不属于调度器插件的职责。
- C. 为 Pod 分配节点名称：这是通过调度器的绑定阶段完成的，不是 NodeName 插件的职责。
- D. 验证节点名称格式：这是由 API server 验证逻辑执行的，不是调度器插件的职责。
</details>

### 11. 哪个控制器会将 Pod Deletion Cost 用作缩容偏好？

A. StatefulSet ordinal 删除
B. ReplicaSet，包括由 Deployment 管理的 ReplicaSet
C. 删除任意独立 Pod
D. 对所有 Deployment 中的 Pod 进行排序的全局调度器

<details>
<summary>显示答案</summary>

**答案：B. ReplicaSet，包括由 Deployment 管理的 ReplicaSet**

该注解会在单个 ReplicaSet 内进行比较，且仅作为尽力而为的偏好。未设置时按 0 处理；有符号的 int32 值（包括负数）均有效。分配情况、阶段和就绪状态可能优先于它，因此高成本但未就绪的 Pod 可能会先于低成本且就绪的 Pod 被删除。此功能在 1.21 中为 alpha，自 1.22 起为 beta 并默认启用。
</details>

### 12. 哪种 deletion-cost 更新模式与源章节相符？

A. 高成本和 PDB 可保证副本在普通缩容时存活
B. 每收到一个请求就替换整个 Pod
C. 只在较粗粒度的状态转换时更新成本，检查 Pod UID 并拒绝过时指标
D. 将不可用指标视为零活动，并立即降低成本

<details>
<summary>显示答案</summary>

**答案：C. 只在较粗粒度的状态转换时更新成本，检查 Pod UID 并拒绝过时指标**

使用单个经过授权的写入者、设置有界请求，并仅对注解进行最小化 patch。UID 检查可以避免误将 patch 应用到同名的新 Pod 上。对缩容执行服务器端 dry run 无法预测具体会删除哪些 Pod。普通的 ReplicaSet 缩容会直接删除 Pod，不会被 PDB 阻止；应用排空/就绪状态和恢复机制仍然很重要。
</details>

## 参考资料

代码使用了 [Part1 模块](../../scheduling/01-custom-scheduler-part1.md)。本地代码/配置测试并不能证明已部署审批系统、gang 工作负载、GPU 执行或生产就绪状态。

* [调度框架](https://kubernetes.io/docs/concepts/scheduling-eviction/scheduling-framework/)
* [固定版本的框架接口](https://github.com/kubernetes/kubernetes/blob/v1.35.8/staging/src/k8s.io/kube-scheduler/framework/interface.go)
* [调度器配置](https://kubernetes.io/docs/reference/scheduling/config/)
* [原生 PodGroup 调度](https://kubernetes.io/docs/concepts/scheduling-eviction/podgroup-scheduling/)
* [PodGroup 策略](https://kubernetes.io/docs/concepts/workloads/workload-api/policies/)
* [Volcano Job](https://volcano.sh/en/docs/vcjob/)
* [Volcano 1.15.2 Job CRD](https://github.com/volcano-sh/volcano/blob/v1.15.2/config/crd/volcano/bases/batch.volcano.sh_jobs.yaml)
* [BalancedAllocation 评分器](https://github.com/kubernetes/kubernetes/blob/v1.35.8/pkg/scheduler/framework/plugins/noderesources/balanced_allocation.go)
* [节点分配](https://kubernetes.io/docs/concepts/scheduling-eviction/assign-pod-node/)
* [ReplicaSet 删除成本](https://kubernetes.io/docs/concepts/workloads/controllers/replicaset/#pod-deletion-cost)

</source_document>
