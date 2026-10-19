# 自定义调度器测验（第 2 部分）

> **示例基线**：Kubernetes 1.35.8，Go 1.27.2
> **最后更新**：2026 年 10 月 16 日

本测验用于检验你对在 Kubernetes 中实现和使用自定义调度器的深入理解。

## 测验题目

### 1. Kubernetes 调度框架中“Bind”扩展点的作用是什么？

A. 将 Pod 绑定到节点，以完成调度决策
B. 建立 Pod 与节点之间的网络绑定
C. 建立 Pod 与 Service 之间的绑定
D. 建立 Pod 与卷之间的绑定

<details>
<summary>显示答案</summary>

**答案：A. 将 Pod 绑定到节点，以完成调度决策**

**说明：**
Kubernetes 调度框架中“Bind”扩展点的作用，是将 Pod 绑定到选定节点，以完成调度决策。Bind 阶段会在绑定周期内提交分配结果；随后是 PostBind，而 kubelet 仍可能遇到镜像、存储或运行时故障。

**绑定流程：**
1. 调度器通过过滤和打分选出最合适的节点。
2. 在选定节点上预留 Pod（reserve）。
3. 在绑定阶段，将 Pod 的 `spec.nodeName` 字段更新为选定节点的名称。
4. 更新后的 Pod 信息会存储在 API 服务器中。
5. kubelet 检测到 Pod 信息后，会在该节点上运行 Pod。

**绑定请求示例：**
节点选择、假定/预留、Permit 和 PreBind 之后，绑定会在绑定周期内发生。绑定记录的是分配结果，并不代表容器已成功启动。请保留上游的 `DefaultBinder`，它还会处理目标版本的 API 缓存路径和绑定错误。以下完整辅助函数展示了请求标识信息，但不会发送请求：

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

Pod UID 可防止将已删除的 Pod 与同名的新 Pod 混淆。绑定请求本身不会检查资源、亲和性或污点；这些检查应在完整调度流程的更早阶段完成。

**默认 Binder 配置：**
以下配置保留所有默认值，包括 `DefaultBinder`；它不会启用未注册的自定义 binder。

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

**检查与绑定相关的事件：**
```bash
# Check pod scheduling events
kubectl get events | grep -i "Successfully assigned"
```

**排查绑定失败：**
绑定阶段失败的常见原因：
1. API 服务器连接问题
2. 权限不足
3. 节点名称错误
4. 竞争条件（另一个调度器同时尝试绑定同一个 Pod）

**其他选项的问题：**
- B. 建立 Pod 与节点之间的网络绑定：网络设置是 CNI 插件的职责，与调度器的 bind 阶段无关。
- C. 建立 Pod 与 Service 之间的绑定：Service 与 Pod 之间的关联通过标签选择器建立，与调度器的 bind 阶段无关。
- D. 建立 Pod 与卷之间的绑定：PV/PVC 绑定和 CSI 置备也涉及存储控制器以及调度器的 VolumeBinding 插件，包括延迟绑定。Pod 到节点的 Bind 是一种不同的操作。
</details>

### 2. 以下哪个不是 Kubernetes 中与 Node Affinity 相关的运算符？

A. In
B. NotIn
C. Exists
D. Contains

<details>
<summary>显示答案</summary>

**答案：D. Contains**

**说明：**
Kubernetes 中与 Node Affinity 无关的运算符是 `Contains`。Kubernetes 没有为节点亲和性提供 `Contains` 运算符。

**Node Affinity 支持的运算符：**
1. **In**：标签值必须与指定值之一匹配。
2. **NotIn**：标签值不得与指定值匹配。
3. **Exists**：指定的标签键必须存在。
4. **DoesNotExist**：指定的标签键不得存在。
5. **Gt**：标签值必须大于指定值（Greater than）。
6. **Lt**：标签值必须小于指定值（Less than）。

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
    image: nginx:1.30.6
```

**Node Affinity 类型：**
1. **requiredDuringSchedulingIgnoredDuringExecution**：Pod 要调度到节点上必须满足的规则（硬性要求）。
2. **preferredDuringSchedulingIgnoredDuringExecution**：优先满足但并非强制的规则（软性要求）。

**运算符用法示例：**
1. **In 运算符**：
   ```yaml
   - key: topology.kubernetes.io/zone
     operator: In
     values:
     - us-east-1a
     - us-east-1b
   ```
   节点的 `topology.kubernetes.io/zone` 标签值必须是 `us-east-1a` 或 `us-east-1b`。

2. **NotIn 运算符**：
   ```yaml
   - key: topology.kubernetes.io/zone
     operator: NotIn
     values:
     - us-east-1c
   ```
   节点的 `topology.kubernetes.io/zone` 标签值不得是 `us-east-1c`。

3. **Exists 运算符**：
   ```yaml
   - key: topology.kubernetes.io/zone
     operator: Exists
   ```
   节点上必须存在 `topology.kubernetes.io/zone` 标签。

4. **DoesNotExist 运算符**：
   ```yaml
   - key: emptyLabel
     operator: DoesNotExist
   ```
   节点上不得存在 `emptyLabel` 标签。

5. **Gt/Lt 运算符**：
   ```yaml
   - key: node-size
     operator: Gt
     values:
     - "10"
   ```
   节点的 `node-size` 标签值必须大于 10。

**检查必需的 Node Affinity：**
保留默认的 `NodeAffinity` 插件。对于只读辅助函数，请使用带版本的组件辅助函数，而不要使用始终返回 true 的 `matchNodeSelectorTerm` 存根。

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

`nodeSelector` 和必需的节点亲和性都必须匹配。选择器项之间为 OR 关系；同一项内的表达式之间为 AND 关系；空项不匹配任何节点。`NotIn` 也会匹配缺少该键的情况；如果要求该键必须存在，请添加 `Exists`。`Gt`/`Lt` 要求恰好有一个整数比较值，并且节点标签值也必须是整数。`IgnoredDuringExecution` 表示之后的标签变更本身不会驱逐已绑定的 Pod。Profile 级别的 `addedAffinity` 仍由调度器插件负责处理。

**其他选项说明：**
- A. In：有效的节点亲和性运算符。
- B. NotIn：有效的节点亲和性运算符。
- C. Exists：有效的节点亲和性运算符。
</details>

### 3. Kubernetes 中 Pod 拓扑分布约束的主要目的是什么？

A. 将 Pod 均匀分布到各个节点
B. 仅将 Pod 放置到特定节点上
C. 仅将 Pod 放置到特定可用区中
D. 仅将 Pod 放置到带有特定标签的节点上

<details>
<summary>显示答案</summary>

**答案：A. 将 Pod 均匀分布到各个节点**

**说明：**
拓扑分布约束会限制每个新 Pod 在符合条件的域之间的放置方式。它可以提高容错能力，但不会重新平衡现有 Pod，也不保证延迟、容量或可用性。

**主要字段：**
1. **maxSkew**：对于 `DoNotSchedule`，限制新 Pod 候选域中的 Pod 数量相对于符合条件的全局最小值的差值。
2. **topologyKey**：定义拓扑域的节点标签。
3. **whenUnsatisfiable**：`DoNotSchedule` 是硬性约束；`ScheduleAnyway` 是打分偏好，不会绕过其他硬性过滤条件。
4. **labelSelector**：选择新 Pod 所在命名空间中用于计数的 Pod。请确保新 Pod 与预期的选择器匹配。
5. **minDomains / nodeAffinityPolicy / nodeTaintsPolicy**：影响符合条件的域的计数。它们不会创建缺失的节点或 AZ 容量。

**Pod 拓扑分布约束示例：**
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
    image: nginx:1.30.6
```

在此示例中，候选放置位置必须同时满足两个约束。对于 `DoNotSchedule`，计算步骤如下：

1. 统计每个符合条件的域中的匹配 Pod 数量，包括空域。
2. 找出符合条件的全局最小值；如果域的数量少于 `minDomains`，则该值为零。
3. 如果新 Pod 与选择器匹配，则将其计入候选域的数量，然后将该候选计数与最小值进行比较。

对于计数为 **2,2,1** 且 `maxSkew: 1` 的情况，另一个匹配的 Pod 可以进入第三个域（2−1=1），但不能进入前两个域中的任意一个（3−1=2）。这是对候选放置位置的检查，并不承诺每一对现有域始终保持平衡。

**常见拓扑键：**
1. **kubernetes.io/hostname**：节点级分布
2. **topology.kubernetes.io/zone**：可用区级分布
3. **topology.kubernetes.io/region**：区域级分布
4. **node.kubernetes.io/instance-type**：实例类型级分布

**使用场景：**
1. **高可用性**：通过将 Pod 分布到多个节点、可用区和区域来提高故障容忍能力
2. **资源均衡**：在集群中均匀分布工作负载
3. **成本优化**：将工作负载分布到特定类型的节点
4. **拓扑策略**：在容错能力、跨域流量和实测延迟之间取得平衡

**自定义调度器处理方式：**
保留 `PodTopologySpread` 及其 PreFilter/Filter/Score 阶段。正确处理需要使用调度器快照、命名空间/选择器匹配、符合条件的域和空域、新 Pod、`minDomains`、节点亲和性/污点策略以及重新入队事件。遍历 Running Pod 却省略偏斜计算，并不构成有效实现。

此 EKS 实验环境使用同一个 AWS Region 中的 EC2 节点；`topology.kubernetes.io/region` 标签不会让它变成多区域集群。跨 AZ 分布可能增加跨 AZ 流量；它本身并不会降低网络延迟。

**其他选项的问题：**
- B. 仅将 Pod 放置到特定节点上：这是 nodeSelector 或 nodeAffinity 的职责。
- C. 仅将 Pod 放置到特定可用区中：这是通过节点亲和性将 Pod 放置到特定可用区的做法；拓扑分布约束的主要目的是均匀分布。
- D. 仅将 Pod 放置到带有特定标签的节点上：这是 nodeSelector 或 nodeAffinity 的职责。
</details>

### 4. Kubernetes 中 Taints 和 Tolerations 的主要目的是什么？

A. 确保特定 Pod 只调度到特定节点上
B. 阻止特定 Pod 调度到特定节点上
C. 允许节点拒绝某些 Pod，并允许 Pod 容忍这种拒绝
D. 限制 Pod 之间的通信

<details>
<summary>显示答案</summary>

**答案：C. 允许节点拒绝某些 Pod，并允许 Pod 容忍这种拒绝**

**说明：**
污点会排斥 Pod；容忍度允许 Pod 忽略匹配的污点。容忍度不会强制将 Pod 放置到该节点，也不会绕过资源/亲和性过滤条件。

**效果：**
1. **NoSchedule**：未被容忍的污点会阻止新 Pod 调度，但不会驱逐现有 Pod。
2. **PreferNoSchedule**：这是一种软性偏好；即使其他地方有可用容量，其他分数也可能超过它。
3. **NoExecute**：没有匹配容忍度的 Pod 无法在该节点上新调度；对于现有 Pod，没有匹配容忍度的 Pod 会触发驱逐处理，或者在其容忍度到期后被驱逐。API 删除并不能证明不可达节点上的进程已经停止。

**应用污点示例：**
```bash
# Apply taint to node
kubectl taint nodes node1 key=value:NoSchedule

# Remove taint from node
kubectl taint nodes node1 key=value:NoSchedule-
```

**污点和容忍度示例：**
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
    image: nginx:1.30.6
```

**容忍度字段：**
* `Equal`（默认运算符）用于比较 key/value。使用 `Exists` 时必须省略 value。
* 指定的 effect 必须匹配；空 effect 会匹配该键的所有 effect。空 key 要求使用 `Exists`，并会匹配所有键，因此请谨慎使用。
* `tolerationSeconds` 仅适用于 `NoExecute`。省略该字段表示无限期容忍匹配的污点；指定该字段则会限制容忍时长。
* 此示例使用默认的 `Equal`/`Exists` 行为。Kubernetes 1.35 中可选的比较运算符功能处于 alpha 阶段，在此处未启用。

```yaml
tolerations:
- key: "node.kubernetes.io/not-ready"
  operator: "Exists"
  effect: "NoExecute"
  tolerationSeconds: 300
```

**常见使用场景：**
1. **专用节点**：组合使用污点、受控的容忍度和必需的亲和性；仅使用污点不会强制这些工作负载调度到专用节点上
2. **特殊硬件**：仅将特定 Pod 调度到带有 GPU 等特殊硬件的节点上
3. **节点维护**：在节点维护期间阻止新 Pod 调度
4. **保护主节点**：阻止一般工作负载调度到控制平面节点上

**系统污点：**
Kubernetes 会自动应用以下系统污点：
1. **node.kubernetes.io/not-ready**：节点未就绪
2. **node.kubernetes.io/unreachable**：节点不可达
3. **node.kubernetes.io/memory-pressure**：节点存在内存压力
4. **node.kubernetes.io/disk-pressure**：节点存在磁盘压力
5. **node.kubernetes.io/pid-pressure**：节点存在 PID 压力
6. **node.kubernetes.io/network-unavailable**：节点的网络不可用
7. **node.kubernetes.io/unschedulable**：节点被标记为不可调度

**检查硬性污点：**
此完整辅助函数使用固定版本的匹配语义，包括 effect/通配符处理。它在硬性检查中排除 `PreferNoSchedule`，并包含 `NoExecute`。它不能替代调度器的其他过滤条件或污点驱逐控制器。

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

**其他选项的问题：**
- A. 确保特定 Pod 只调度到特定节点上：这是 nodeSelector 或 nodeAffinity 的职责。
- B. 阻止特定 Pod 调度到特定节点上：这只描述了 taints/tolerations 中排斥的一面；podAntiAffinity 则是根据其他 Pod 来限制放置位置。
- D. 限制 Pod 之间的通信：这是 NetworkPolicy 的职责。
</details>

### 5. 以下哪项不是 Kubernetes 中 Scheduler Extender 的主要特征？

A. 通过 HTTP webhook 与调度器通信
B. 提供过滤和优先级排序能力
C. 直接集成到调度器代码库中
D. 作为外部进程运行

<details>
<summary>显示答案</summary>

**答案：C. 直接集成到调度器代码库中**

**说明：**
“直接集成到调度器代码库中”不是 Kubernetes 中 Scheduler Extender 的主要特征。Scheduler Extender 并不直接集成到调度器代码库中；它们通过 HTTP webhook 通信，并作为外部进程运行。这是它们与调度框架插件的主要区别。

**Scheduler Extender 的主要特征：**
1. **HTTP webhook**：调度器通过 HTTP 请求与 extender 通信。
2. **外部进程**：extender 与调度器作为独立进程运行。
3. **过滤和优先级排序**：extender 可以提供节点过滤和优先级排序能力。
4. **绑定**：extender 可以选择将 Pod 绑定到节点。

**Extender 配置：**
为次级调度器使用 Part2 TLS 服务和证书前置条件。`extenders` 是顶层字段。对于必需的过滤器，请保留 `ignorable: false`；对于必须强制执行可用性的资源，不要将可容忍故障的 extender 与 `ignoredByScheduler: true` 组合使用。此示例将所有 GPU 计数都交给内置资源过滤器处理。

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

**Wire 协议（Kubernetes 1.35.8）：**
Go 类型会将字段名序列化为首字母大写形式。`nodeCacheCapable: false` 时，请发送 `Pod` 和完整的 `Nodes`；`NodeNames` 为 null。若将其设为 true，则需要单独维护节点缓存，并满足 `NodeNames` 约定。以下是有效的 JSON 示例，并非字面上的尖括号占位符。

1. **Filter / prioritize 请求**：

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
          "image": "busybox:1.38.0",
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

2. **Filter 响应**：只能返回提供的候选节点。`FailedAndUnresolvableNodes` 用于标识抢占无法解决的失败。

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

3. **Prioritize 响应**：由 `Host`/`Score` 组成的裸数组，分数范围为 **0 到 10**。Framework 分数使用 0–100。priority 出错时会省略此 extender 的分数；因此，强制规则应放在 Filter 中。

```json
[
  {
    "Host": "gpu-node",
    "Score": 2
  }
]
```

4. **可选的 bind 请求和响应**：请求通过名称、命名空间和 UID 标识 Pod，并指定选定节点。Part2 未实现此回调，因此不设置 `bindVerb`。

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

5. **可选的抢占回调**：`preemptVerb` 使用 `ExtenderPreemptionArgs`/`ExtenderPreemptionResult` 交换 Pod 和候选受害者信息。它不是 PreFilter 或 PreScore 回调。

**实现：**
请使用 [Part2](../../scheduling/02-custom-scheduler-part2.md) 中完整的有界输入处理程序和 TLS 命令。它们会拒绝缺失的 Pod/节点、格式错误的内存要求、超大输入和错误的缓存约定；不会将未实现的 `customFilter` 或 `customScore` 函数当作可执行代码。

**Scheduler Extender 与调度框架插件的对比：**

| 特性 | Scheduler Extender | 调度框架插件 |
|---------|-------------------|---------------------------|
| 集成方式 | HTTP webhook | 直接集成到代码库 |
| 执行模式 | 外部进程 | 在调度器内部 |
| 性能 | 由于 HTTP 开销，相对较慢 | 由于直接集成，速度更快 |
| 开发语言 | 不受限制 | Go |
| 部署 | 独立服务 | 与调度器一同部署 |
| 维护 | 独立于调度器 | 与调度器版本关联 |

**Scheduler Extender 的优缺点：**
优点：
- 可独立于调度器代码库进行开发
- 可使用多种编程语言实现
- 受调度器升级的影响较小

缺点：
- HTTP 通信开销会导致性能下降
- 只能扩展调度周期中的部分阶段
- 调度器与 extender 之间可能发生通信故障

**其他选项说明：**
- A. 通过 HTTP webhook 与调度器通信：Scheduler Extender 的有效特征。
- B. 提供过滤和优先级排序能力：Scheduler Extender 的有效特征。
- D. 作为外部进程运行：Scheduler Extender 的有效特征。
</details>

### 6. Kubernetes 中 Pod Affinity 和 Anti-Affinity 的主要目的是什么？

A. 定义 Pod 与节点之间的关系
B. 定义 Pod 与卷之间的关系
C. 定义 Pod 之间的关系
D. 定义 Pod 与 Service 之间的关系

<details>
<summary>显示答案</summary>

**答案：C. 定义 Pod 之间的关系**

**说明：**
Kubernetes 中 Pod Affinity 和 Anti-Affinity 的主要目的是定义 Pod 之间的关系。这样可以控制特定 Pod 是否与其他 Pod 放置在同一个拓扑域（节点、可用区、区域等）中（亲和性），或避免放置在同一个拓扑域中（反亲和性）。

**Pod Affinity 和 Anti-Affinity 的主要组成部分：**
1. **topologyKey**：指定用于定义 Pod 之间关系的拓扑域的节点标签键。
2. **labelSelector**：用于选择要建立关系的 Pod 的标签选择器。
3. **namespaces**：标签选择器适用的命名空间列表。

**Pod Affinity 类型：**
1. **requiredDuringSchedulingIgnoredDuringExecution**：Pod 要成功调度必须满足的规则（硬性要求）。
2. **preferredDuringSchedulingIgnoredDuringExecution**：优先满足但并非强制的规则（软性要求）。

**Pod Affinity 示例：**
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

在此示例中：
1. **Pod Affinity**：web 服务器 Pod 必须调度到与带有 `app=cache` 标签的 Pod 相同的节点（`kubernetes.io/hostname`）上。
2. **Pod Anti-Affinity**：最好将 web 服务器 Pod 调度到与其他带有 `app=web` 标签的 Pod 不同的节点上。

**常见拓扑键：**
1. **kubernetes.io/hostname**：节点级关系
2. **topology.kubernetes.io/zone**：可用区级关系
3. **topology.kubernetes.io/region**：区域级关系

**使用场景：**
1. **高可用性**：将同一应用的实例分布到不同节点、可用区和区域
2. **位置亲和偏好**：共置可能降低部分网络成本；在依赖此做法之前，应测量资源争用和延迟
3. **资源隔离**：将资源密集型 Pod 分布到不同节点
4. **许可证限制**：将受许可证限制的应用集中到特定节点上

**Pod Affinity 与 Node Affinity 的对比：**
- **Node Affinity**：定义 Pod 与节点之间的关系。
- **Pod Affinity**：定义 Pod 之间的关系。

**Pod Affinity 和 Anti-Affinity 对性能的影响：**
Pod Affinity 和 Anti-Affinity 需要考虑所有节点和 Pod，因此计算开销可能较大。尤其是在大型集群中，它们会影响调度性能，因此应谨慎使用。

**自定义调度器处理方式：**
保留 `InterPodAffinity`，包括其预处理和打分逻辑。它必须考虑新 Pod 的必需条件、现有 Pod 的必需反亲和性、命名空间选择、拓扑标签以及自亲和性引导行为。始终返回 true 的存根可能会允许无效放置；若在反亲和性中对其结果取反，则可能拒绝所有节点。

`namespaces` 和 `namespaceSelector` 选择的命名空间为两者的并集；如果两者都省略，则使用新 Pod 所在的命名空间。`namespaceSelector: {}` 会选择所有命名空间。在此示例中，符合条件的节点上必须已存在所选命名空间中带有 `app=cache` 标签的 Pod。首选反亲和性不保证 Pod 会被分开。随着标签或对等 Pod 发生变化，`IgnoredDuringExecution` 不会持续重新放置 Pod。

**其他选项的问题：**
- A. 定义 Pod 与节点之间的关系：这是 nodeAffinity 的职责。
- B. 定义 Pod 与卷之间的关系：这是卷绑定和 PersistentVolumeClaim 的职责。
- D. 定义 Pod 与 Service 之间的关系：这通过 Service 标签选择器处理。
</details>

### 7. Kubernetes 调度器中“QueueSort”扩展点的作用是什么？

A. 为节点打分
B. 排除 Pod 无法运行的节点
C. 对调度队列中的 Pod 排序
D. 将 Pod 绑定到节点

<details>
<summary>显示答案</summary>

**答案：C. 对调度队列中的 Pod 排序**

**说明：**
Kubernetes 调度框架中“QueueSort”扩展点的作用，是对调度队列中的 Pod 排序。此扩展点设置决定 Pod 调度先后顺序的优先级。

**调度队列和 QueueSort：**
调度器会依次处理调度队列中的 Pod。QueueSort 插件决定这些 Pod 在队列中的顺序。默认情况下，Kubernetes 使用 `PrioritySort` 插件按 Pod 优先级排序。

**带版本的接口：**
在 Kubernetes 1.35.8 中，QueueSort 实现 `Less(fwk.QueuedPodInfo, fwk.QueuedPodInfo) bool`；这些是通过 getter 访问的接口。默认的 `PrioritySort` 先比较已准入的优先级，再比较队列时间戳。

**完整的自定义示例（`quizplugins/queue.go`）：**
此示例在应用实验环境中的平局打破规则之前，先保留已准入的优先级。在优先级相同的 Pod 之间使用命名空间/标签偏好可能造成不公平；不要让不可信标签替代受准入控制的 PriorityClass。

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

使用 `cmd/quiz-scheduler/main.go` 将其与后面的 PoolConstraint 示例一起注册：

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

使用 Part1 模块构建：`CGO_ENABLED=0 go build -buildvcs=false -o custom-scheduler ./cmd/quiz-scheduler`。只启用所选配置所需的插件。

**在调度器配置中启用 QueueSort 插件：**
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

**QueueSort 插件的特征：**
1. **单一激活**：一次只能启用一个 QueueSort 插件。
2. **共享队列**：同一调度器进程中的所有 profile 必须使用相同的 QueueSort 插件和配置。其他调度器进程有各自独立的队列。
3. **性能的重要性**：高效的排序算法很重要；复杂逻辑可能会影响调度性能。

**QueueSort 插件的使用场景：**
1. **业务优先级**：按业务重要性对 Pod 排序
2. **资源效率**：优先调度资源请求较小的 Pod，以利用空闲空间
3. **服务级别协议（SLA）**：根据 SLA 要求对 Pod 排序
4. **批处理**：调整批处理作业和交互式作业之间的优先级

**监控调度队列：**
```bash
# Check queue information in scheduler logs
kubectl logs -n scheduler-lab -l app=custom-scheduler --prefix --tail=100

# Check pods pending scheduling
kubectl get pods -A --field-selector=spec.schedulerName=custom-scheduler,spec.nodeName= -o wide
```

**其他选项的问题：**
- A. 为节点打分：这是“Score”扩展点的职责。
- B. 排除 Pod 无法运行的节点：这是“Filter”扩展点的职责。
- D. 将 Pod 绑定到节点：这是“Bind”扩展点的职责。
</details>

### 8. Kubernetes 中 Pod Priority Preemption 的主要目的是什么？

A. 移除低优先级 Pod，以便高优先级 Pod 能够调度
B. 为高优先级 Pod 分配更多资源
C. 让高优先级 Pod 更快运行
D. 仅将高优先级 Pod 放置到特定节点上

<details>
<summary>显示答案</summary>

**答案：A. 移除低优先级 Pod，以便高优先级 Pod 能够调度**

**说明：**
Kubernetes 中 Pod Priority Preemption 的主要目的是移除低优先级 Pod，以便高优先级 Pod 能够调度。当高优先级 Pod 无法放入节点时，如果移除低优先级 Pod 可以满足相关约束，调度器就可能抢占这些 Pod。

**Pod 优先级和抢占机制：**
1. **PriorityClass 定义**：定义 Pod 优先级的集群级资源。
2. **为 Pod 分配优先级**：Pod 通过 `spec.priorityClassName` 引用 PriorityClass。
3. **调度顺序**：在调度队列中优先处理优先级较高的 Pod。
4. **抢占流程**：如果 Pod 的策略允许，且剩余约束能够满足，调度器可能会移除低优先级 Pod。

**PriorityClass 示例：**
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

**为 Pod 应用优先级：**
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

**抢占策略：**
PriorityClass 有一个 `preemptionPolicy` 字段，可以采用以下值：
1. **PreemptLowerPriority（默认值）**：可以抢占低优先级 Pod。
2. **Never**：不会抢占低优先级 Pod。

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

**抢占流程：**
1. 调度器尝试调度一个高优先级 Pod。
2. 如果没有合适的节点，调度器会识别各节点上的抢占候选 Pod。
3. 从低优先级 Pod 中选出抢占候选对象。
4. 调度器根据其策略选择候选对象/受害者集合；它不保证全局最小基数。
5. 所选 Pod 会被优雅终止。
6. 受害者终止后会重试调度；提名并不保证绑定成功。

**抢占注意事项：**
1. **优雅终止期限**：被抢占的 Pod 有一个由 `terminationGracePeriodSeconds` 指定的优雅终止时间（默认值：30 秒）。
2. **Pod Disruption Budget（PDB）**：抢占会尝试避免违反 PDB，但是否符合 PDB 只是尽力而为，并无保证。
3. **提名**：`status.nominatedNodeName` 记录可能的目标节点。抢占不会通过添加节点污点来预留该节点。
4. **系统 Pod**：关键 PriorityClass 使用较高的保留优先级；这并不意味着它们不会受到任何更高优先级 Pod 或其他驱逐机制的影响。

**检查抢占事件：**
```bash
# Check preemption events
kubectl get events | grep -i preempt
```

**监控与抢占相关的指标：**
通过配置的监控系统，从**自定义调度器**经过身份验证的 HTTPS 指标端点读取 `scheduler_preemption_attempts_total`。`kubectl get --raw /metrics` 读取的是 API 服务器指标，并非此端点。

```bash
kubectl get pods -A -o custom-columns=NAME:.metadata.name,PRIORITY:.spec.priority,NOMINATED:.status.nominatedNodeName
```

**安全处理抢占：**
在 PostFilter 中保留 `DefaultPreemption`。它会模拟移除低优先级 Pod，并重新运行相关约束；在第一个节点上删除所有低优先级 Pod 并不安全。选择过程会考虑 PDB 违规和受害者优先级，并不保证受害者数量在全局范围内最少。

抢占无法修复缺失的标签、不兼容的卷拓扑或缺失的硬件。Pod 在提名后仍可能保持 Pending，另一个更高优先级的 Pod 也可能改变结果。替代 Pod、终止和 API 更新都是异步的。本次审计未运行驱逐循环。

**抢占的优缺点：**
优点：
- 在约束允许时，可以为高优先级工作负载腾出空间
- 高效利用集群资源
- 支持满足服务级别协议（SLA）

缺点：
- 被抢占的 Pod 会受到干扰
- 抢占后重新调度会带来开销
- 抢占决策逻辑复杂

**其他选项的问题：**
- B. 为高优先级 Pod 分配更多资源：Pod 优先级不会直接影响资源分配。资源请求和限制在 Pod 规范中单独定义。
- C. 让高优先级 Pod 更快运行：优先级会影响调度顺序，但不会改变 Pod 本身的执行速度。
- D. 仅将高优先级 Pod 放置到特定节点上：这是 nodeSelector 或 nodeAffinity 的职责，与优先级并无直接关系。
</details>

### 9. Kubernetes 调度器中“PreFilter”扩展点的作用是什么？

A. 在过滤前对 Pod 和集群状态进行预处理
B. 过滤后为节点打分
C. 在将 Pod 绑定到节点之前执行验证
D. 对调度队列中的 Pod 排序

<details>
<summary>显示答案</summary>

**答案：A. 在过滤前对 Pod 和集群状态进行预处理**

**说明：**
Kubernetes 调度框架中“PreFilter”扩展点的作用，是在过滤前对 Pod 和集群状态进行预处理。PreFilter 插件会准备过滤阶段要使用的数据，也可以预先检查 Pod 是否能够调度。

**PreFilter 扩展点的主要功能：**
1. **数据准备**：初始化并准备过滤阶段要使用的数据结构。
2. **预检查**：预先检查 Pod 是否能够调度。
3. **状态存储**：存储调度周期内要使用的状态信息。
4. **优化**：避免不必要的过滤工作，以优化性能。

**带版本的接口：**
Kubernetes 1.35.8 使用 `PreFilter(ctx, state, pod, nodes) (*fwk.PreFilterResult, *fwk.Status)`，其中 `state` 为 `fwk.CycleState`，`nodes` 为 `[]fwk.NodeInfo`。可选的 AddPod/RemovePod 扩展会接收正在调度的 Pod、模拟添加/移除的 PodInfo 和 NodeInfo。它们支持抢占模拟，并可能在克隆后的状态上运行；它们不是常规的 informer 回调。

**默认 PreFilter 插件：**
Kubernetes 提供以下默认 PreFilter 插件：

1. **InterPodAffinity**：处理 Pod 间亲和性和反亲和性要求。
2. **NodeAffinity**：处理节点亲和性要求。
3. **NodePorts**：处理 Pod 请求的主机端口。
4. **NodeResourcesFit**：处理节点资源要求。
5. **PodTopologySpread**：处理 Pod 拓扑分布约束。
6. **VolumeBinding**：处理卷绑定要求。

**完整的 PreFilter + Filter 示例（`quizplugins/prefilter.go`）：**
对于普通的资源池标签，必需节点亲和性更简单。此示例展示经过验证的周期级状态以及 `Clone()`。它不依赖其他 Pod，因此不需要 AddPod/RemovePod 扩展。缺少 PreFilter 状态时应返回错误，而不是允许调度。

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

**启用已实现的两个阶段并保留默认资源检查：**
第 7 题中的注册命令包含此插件。

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

**PreFilter 与 Filter 之间的关系：**
1. **PreFilter**：开始对所有节点进行过滤之前运行一次。
2. **Filter**：针对每个节点分别运行。

PreFilter 会准备 Filter 阶段要使用的数据，并预先识别 Pod 无法在任何节点上调度的情况，以避免不必要的过滤工作。

**PreFilter 的使用场景：**
1. **处理复杂约束**：高效处理 Pod 间亲和性、拓扑分布等复杂约束
2. **预验证**：预先检查 Pod 是否能够调度，避免不必要的处理
3. **数据缓存**：预先计算过滤阶段会重复使用的数据，以提高性能
4. **状态共享**：管理多个插件之间共享的状态信息

**其他选项的问题：**
- B. 过滤后为节点打分：这是“Score”扩展点的职责。
- C. 在将 Pod 绑定到节点之前执行验证：这是“PreBind”扩展点的职责。
- D. 对调度队列中的 Pod 排序：这是“QueueSort”扩展点的职责。
</details>

### 10. Kubernetes 中节点污点 `node.kubernetes.io/unreachable:NoExecute` 表示什么？

A. 节点不可达，且没有容忍度的 Pod 会被移除
B. 节点不可调度，但现有 Pod 会继续运行
C. 节点处于维护模式，不会调度新 Pod
D. 节点资源不足，因此最好不要调度新 Pod

<details>
<summary>显示答案</summary>

**答案：A. 节点不可达，且没有容忍度的 Pod 会被移除**

**说明：**
Kubernetes 中的节点污点 `node.kubernetes.io/unreachable:NoExecute` 表示节点不可达，没有针对该污点配置容忍度的 Pod 会从节点上移除（驱逐）。节点控制器会自动添加此污点，当节点状态从 `Ready` 变为 `Unknown` 时应用该污点。

**节点不可达状态：**
节点变得不可达的常见原因：
1. 网络连接问题
2. kubelet 进程崩溃
3. 节点系统故障
4. 节点电源问题

**污点组成部分：**
1. **Key**：`node.kubernetes.io/unreachable`
2. **Value**：通常为空字符串，但也可能有值。
3. **Effect**：`NoExecute`——没有容忍度的 Pod 会从节点上移除。

**NoExecute 效果：**
`NoExecute` 效果会产生以下行为：
1. 没有匹配容忍度的新 Pod 不会调度到带有该污点的节点上。
2. 对于已在节点上运行的 Pod，没有针对该污点配置容忍度的 Pod 会被移除。

**系统污点：**
Kubernetes 会根据节点状态自动添加以下系统污点：
1. **node.kubernetes.io/not-ready:NoExecute**：节点未就绪
2. **node.kubernetes.io/unreachable:NoExecute**：节点不可达
3. **node.kubernetes.io/memory-pressure:NoSchedule**：节点存在内存压力
4. **node.kubernetes.io/disk-pressure:NoSchedule**：节点存在磁盘压力
5. **node.kubernetes.io/pid-pressure:NoSchedule**：节点存在 PID 压力
6. **node.kubernetes.io/network-unavailable:NoSchedule**：节点的网络不可用
7. **node.kubernetes.io/unschedulable:NoSchedule**：节点被标记为不可调度

**默认容忍度：**
在默认准入行为下，只有在未显式提供等效容忍度时，Kubernetes 才会添加这些容忍度。DaemonSet Pod 则会收到针对 not-ready/unreachable NoExecute 污点的无限期容忍度：
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

这些默认值会在污点处理开始后容忍该污点 300 秒；它们并不精确对应从故障发生到替代 Pod 启动的计时。控制平面检测和删除操作会增加延迟，断开连接的进程也可能仍在运行。

**自定义容忍度：**
较长的容忍时间会推迟替代 Pod 的启动，可能延长故障；应根据应用恢复要求选择容忍时间，而不要假设越长越安全：
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
    image: nginx:1.30.6
```

**节点控制器和驱逐时序：**
对于固定的上游 1.35.8 基线，`--node-monitor-period` 的默认值为 5s，`--node-monitor-grace-period` 的默认值为 **50s**，而不是 40s。旧的 `--pod-eviction-timeout` 标志不是当前基于污点的驱逐机制；匹配的 Pod 容忍度和污点驱逐控制器负责控制该机制。检测、污点发布、控制器限流和删除操作都可能增加延迟。

从 Kubernetes 1.29 开始，基于污点的驱逐由单独的 `taint-eviction-controller` 运行；该控制器默认启用，但在自行管理的控制平面上可以独立配置。这些值不是 EKS 配置说明，也不保证故障转移时间。在不可达节点上强制移除有状态 Pod 之前，应确认旧的写入方已停止/被隔离，以避免多个写入方同时运行。

**检查节点状态和污点：**
```bash
# Check node status
kubectl get nodes

# Check node details
kubectl describe node <node-name>

# Check node taints
kubectl get node <node-name> -o jsonpath='{.spec.taints}'
```

**检查 Pod 容忍度：**
```bash
# Check pod tolerations
kubectl get pod <pod-name> -o jsonpath='{.spec.tolerations}'
```

**在自定义调度器中处理污点：**
实现自定义调度器时，应考虑节点污点和 Pod 容忍度。

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

**其他选项的问题：**
- B. 节点不可调度，但现有 Pod 会继续运行：这是 `NoSchedule` 效果的行为；`NoExecute` 效果还会移除没有容忍度的现有 Pod。
- C. 节点处于维护模式，不会调度新 Pod：这通常是 `node.kubernetes.io/unschedulable:NoSchedule` 污点的行为。
- D. PreferNoSchedule 是一种软性偏好。常见的内存压力和磁盘压力污点使用的是 NoSchedule；二者都不能描述 unreachable:NoExecute。
</details>

## 参考资料

请使用 [Part1 模块](../../scheduling/01-custom-scheduler-part1.md) 和 [Part2 实现](../../scheduling/02-custom-scheduler-part2.md)。代码/配置检查在本地进行；未执行云部署或驱逐操作。

* [v1.35.8 的 Framework 接口](https://github.com/kubernetes/kubernetes/blob/v1.35.8/staging/src/k8s.io/kube-scheduler/framework/interface.go)
* [Extender wire 类型](https://github.com/kubernetes/kubernetes/blob/v1.35.8/staging/src/k8s.io/kube-scheduler/extender/v1/types.go)
* [节点和 Pod 亲和性](https://kubernetes.io/docs/concepts/scheduling-eviction/assign-pod-node/)
* [拓扑分布](https://kubernetes.io/docs/concepts/scheduling-eviction/topology-spread-constraints/)
* [污点和容忍度](https://kubernetes.io/docs/concepts/scheduling-eviction/taint-and-toleration/)
* [优先级和抢占](https://kubernetes.io/docs/concepts/scheduling-eviction/pod-priority-preemption/)
* [节点生命周期默认值](https://github.com/kubernetes/kubernetes/blob/v1.35.8/pkg/controller/nodelifecycle/config/v1alpha1/defaults.go)
