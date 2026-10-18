# 自定义调度器

> **示例基线**：Kubernetes 1.35.8，Go 1.27.2
> **最后更新**：October 16, 2026

Kubernetes 调度器是一个关键组件，它负责决定将 Pod 放置在哪个节点上。虽然默认调度器在大多数情况下都能很好地工作，但你也可以针对特定需求实现自定义调度器。在本章中，我们将学习如何在 EKS 中实现自定义调度器。

## 实验环境设置

若要跟着本文档中的示例操作，你需要准备以下工具和环境：

### 必需工具

* 与集群 API 服务器版本相差不超过一个次要版本的 kubectl
* 用于下方可复现示例的 Go 1.27.2 和 Python 3
* 一个可随时销毁的 Kubernetes 1.35 集群，且包含 Linux 工作节点；对于 EKS，请先查看 [AWS 版本日历](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html)

此处的框架接口和配置已针对 Kubernetes **1.35.8** 进行核对。这是一个示例基线，并不表示它是最新的 Kubernetes 或 EKS 版本。请使调度器与集群次要版本匹配，并在升级时重新验证插件、功能门控和 RBAC。Kubernetes 模块使用 staging 依赖；单独执行 `go get k8s.io/kubernetes` 无法解析其 `v0.0.0` staging 依赖。

### 开发环境设置

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
text = f"module example.com/custom-scheduler\n\ngo 1.27.2\n\nrequire k8s.io/kubernetes {version}\n\nreplace (\n"
text += "".join(f"\t{m} => {m} {staging_version}\n" for m in modules)
Path("go.mod").write_text(text + ")\n")
PY
```

## 调度概述

### Kubernetes 调度流程

Kubernetes 调度流程包含以下阶段：

### 调度阶段详解

1. **过滤阶段**
   * 识别适合运行 Pod 的节点
   * 每个过滤插件都会判断某个节点是否可以承载该 Pod
   * 如果任何过滤插件未通过，该节点就会从候选节点中排除
2. **评分阶段**
   * 为过滤后的节点分配分数
   * 每个评分插件都会返回 0–100 分，之后可进行归一化
   * 最终分数通过应用权重计算得出
3. **绑定阶段**
   * 将 Pod 分配给得分最高的节点
   * 通过 Kubernetes API 更新 Pod 与节点的绑定信息

## 何时需要自定义调度器

以下情况可以考虑使用自定义调度器：

1. **特殊硬件需求**：GPU、FPGA、特殊网络设备等。
2. **复杂的工作负载放置规则**：将特定工作负载放置到特定节点组上
3. **成本优化**：在 Spot 实例和按需实例之间进行优化放置
4. **局部性需求**：根据数据局部性放置工作负载
5. **多调度器场景**：针对不同类型的工作负载使用多个调度器

### 实际应用场景

| 行业           | 使用场景                       | 自定义调度器的优势                                 |
| ------------------ | ------------------------------ | --------------------------------------------------------- |
| 金融             | 高频交易系统 | 根据网络拓扑进行放置，以尽量降低延迟 |
| 医疗保健         | 医学图像处理       | 支持 GPU 感知的放置，并优先考虑数据局部性     |
| 电信 | 5G 网络功能           | 针对带标签的网络设备设置放置约束           |
| 零售             | 季节性流量处理      | 优化 Spot 实例的经济高效使用     |
| 媒体              | 视频转码              | 根据工作负载特征选择 CPU/GPU 节点  |

1. **过滤**：识别可运行 Pod 的节点。此阶段会考虑资源需求、节点选择器、节点亲和性、污点和容忍度等。
2. **评分**：为过滤后的节点评分。此阶段会考虑节点资源使用情况、Pod 间亲和性、节点亲和性等。
3. **绑定**：将 Pod 分配给得分最高的节点。

编写代码之前，先检查设备插件、必需/首选亲和性、污点/容忍度和拓扑分布是否已经能够表达你的需求。普通的 GPU 资源请求不需要自定义调度器。

### 默认调度器的局限性

默认调度器可能存在以下局限性：

1. **特定硬件需求**：对于 GPU、FPGA 等特殊硬件，可能需要高级调度逻辑。
2. **复杂的亲和性规则**：可能存在难以通过基本亲和性规则表达的复杂放置约束。
3. **自定义指标**：调度可能需要依据默认调度器不会考虑的自定义指标。
4. **领域专用知识**：可能需要针对特定应用领域定制调度逻辑。

## 自定义调度器的实现方法

实现自定义调度器主要有三种方法：

1. **多调度器方法**：在默认调度器旁运行自定义调度器。
2. **调度器扩展器方法**：扩展默认调度器，提供额外的过滤和优先级功能。
3. **调度框架插件**：使用 Kubernetes 1.15 中引入的调度框架开发插件。

### 多调度器方法

在多调度器方法中，自定义调度器与默认调度器并行运行。创建 Pod 时，可以通过 `schedulerName` 字段指定要使用的调度器。

#### 自定义调度器实现

以上游调度器命令为基础创建一个次级调度器。这样可以保留 `NodeResourcesFit`、`TaintToleration`、`NodeAffinity`、`VolumeBinding` 和其他默认插件。如果只是选择第一个 Ready 节点并调用绑定 API，就会绕过这些检查。

将以下内容保存为 `main.go`。它目前尚未添加自定义放置策略；后续的评分辅助函数和测验会展示扩展点。

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

#### 自定义调度器 Deployment

将以下内容保存为 `Dockerfile`，运行本地构建命令，并通过经批准的镜像仓库工作流发布镜像。将清单中的 `registry.example.com/...` 替换为该镜像，最好使用摘要固定版本。二进制文件和镜像必须与工作节点的架构匹配。

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

这是实验环境中的部署示例，不是经过生产环境测试的高可用方案。调度器 Pod 本身使用 `default-scheduler`，以便在 `custom-scheduler` 尚不可用时也能启动。两个副本共用 `scheduler-lab` 中的**同一个** Lease；其他调度器组需要使用不同的 Lease。首选反亲和性有助于分散放置，但不能保证分布在不同主机或可用区。

管理员必须确认引用的引导 RBAC 角色确实存在。`system:kube-scheduler` 和 `system:volume-scheduler` 授予强大的集群范围调度权限，包括绑定和抢占；`schedulerName` 不是安全边界。单独的 Role 用于授予对我们 Lease 的访问权限，不会修改 Kubernetes 的引导角色。请确保 HTTPS 端点仅在私有网络中可访问。需要在目标集群上测试资源配置和故障行为。

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

#### 使用自定义调度器

创建 Pod 时，使用 `schedulerName` 字段指定自定义调度器：

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: nginx
spec:
  schedulerName: custom-scheduler
  containers:
  - name: nginx
    image: nginx:1.30.6
    resources:
      requests:
        cpu: 100m
        memory: 64Mi
      limits:
        memory: 128Mi
```

## 在 EKS 中实现自定义调度器

在 Amazon EKS 中实现自定义调度器时，请考虑以下事项：

1. **Kubernetes 身份验证和授权**：集群内的调度器使用其 ServiceAccount 令牌和 Kubernetes RBAC。只有在调用 EC2 或 CloudWatch 等 AWS API 时才需要额外使用 IAM；请仅向该工作负载身份授予所需的 AWS 权限。
2. **托管控制平面**：在工作节点上运行自己的次级调度器。不要假定你可以访问托管默认调度器的进程、标志或插件注册表。
3. **计算边界**：此示例面向 EC2 工作节点。[EKS Fargate 使用 AWS 托管的调度和准入控制器](https://docs.aws.amazon.com/eks/latest/userguide/fargate.html)；选择 Fargate 节点或设置 `custom-scheduler` 并不会预置 Fargate 容量。
4. **拓扑和实例标签**：优先使用现有节点标签、资源请求、亲和性和拓扑分布。自定义调度器不会创建容量，也不保证延迟。

### EKS 自定义调度器架构

每个调度器都会监视 Kubernetes API，并为匹配的 Pod 维护**自己的缓存和队列**。API 服务器存储并公开 Pod 状态；它不拥有共享的调度队列。与 EC2/CloudWatch 的集成是可选的；对于缓慢或失败的指标查询，需要设置有界超时和明确的回退策略。

### EKS 特定调度注意事项

以下函数是**用于说明的软评分辅助函数**，作为单独的文件保存在 `preferences` 包中。它们不会自动注册到上面的二进制文件中。只有在默认过滤器通过后，才应从经过测试的框架 `Score` 插件中调用这些函数。分数为 **0 仍表示节点符合条件**；强制规则应放在过滤器或必需亲和性中。分数应保持在 0–100 之间。

#### 1. 根据实例类型进行调度

以下 c5/m5/r5 权重用于演示基于标签的偏好。它们既不是经过测量的性能排名，也不是购买这些代际实例的建议。对于实际工作负载，请对合适的实例类型进行基准测试，并明确配置偏好。

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

#### 2. 按可用区分布进行调度

优先使用内置的 `PodTopologySpread` 插件和 `topologySpreadConstraints`。如果确实需要自定义评分，请根据调度器缓存构建一致的周期快照，范围限定为目标工作负载和所有符合条件的可用区，包括其中没有 Pod 的可用区。应根据需要纳入已分配/已假定的 Pod；只统计 Running Pod 会遗漏预留资源。不要针对每个候选节点各执行一次 API list/get，也不要将 API 错误转换成虚构计数。

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

#### 3. 根据 Spot 实例进行调度

[EKS 托管节点组](https://docs.aws.amazon.com/eks/latest/userguide/managed-node-groups.html) 使用 `eks.amazonaws.com/capacityType` 标签，其取值为 `SPOT` / `ON_DEMAND`；[Karpenter](https://karpenter.sh/docs/concepts/nodepools/) 使用 `karpenter.sh/capacity-type` 标签，其取值为 `spot` / `on-demand` / `reserved`。`node.kubernetes.io/lifecycle` 并不是标准的等效标签。此辅助函数会应用明确的 Pod 偏好；未知标签保持中性。如果容量类型是强制要求，请使用必需亲和性。无法根据分数推断 Spot 定价或中断容忍度。

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

#### 4. GPU 工作负载调度

设备插件必须公布 GPU 资源，准入后的 Pod 也必须请求该资源。对于扩展资源，如果指定了 limit 而未指定 request，request 会默认设置为相同值；值为零的 request 不代表 GPU 需求。`NodeResourcesFit` 会根据可分配资源扣除现有/已假定的请求，再检查有效请求是否符合要求。仅查看 `Capacity` 无法得知 GPU 是否空闲。

此辅助函数只会阻止非 GPU 工作负载占用具备 GPU 能力的节点。它使用版本化资源辅助函数，包括 init/sidecar/开销核算，并假定 Pod 已由 API 设置默认值。它**不能**确定 GPU 资格、处理所有 DRA 资源模型，也不能替代默认资源过滤器。

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

## 结论

本章概述了 Kubernetes 调度流程，并介绍了如何使用多调度器方法实现自定义调度器。我们还探讨了在 EKS 集群中实现自定义调度器时需要考虑的事项。

下一章中，我们将学习如何使用调度器扩展器方法和调度框架插件实现自定义调度器。

## 验证与参考资料

已在本地根据固定的依赖版本核对 Go 命令、插件和配置。本次审计未执行集群部署、镜像推送、AWS 调用、放置基准测试或 HA 故障转移测试。

* [配置多个调度器](https://kubernetes.io/docs/tasks/extend-kubernetes/configure-multiple-schedulers/)：架构/RBAC 模式；其中的旧镜像和构建示例不适用于版本指导
* [调度器配置](https://kubernetes.io/docs/reference/scheduling/config/)
* [调度框架](https://kubernetes.io/docs/concepts/scheduling-eviction/scheduling-framework/)
* [Kubernetes 1.35.8 框架接口](https://github.com/kubernetes/kubernetes/blob/v1.35.8/staging/src/k8s.io/kube-scheduler/framework/interface.go)
* [Kubernetes 1.35.8 默认插件](https://github.com/kubernetes/kubernetes/blob/v1.35.8/pkg/scheduler/apis/config/v1/default_plugins.go)

## 测验

若要检验你在本章中的学习成果，请尝试[主题测验](../quizzes/scheduling/02-custom-scheduler-part1-quiz.md)。
