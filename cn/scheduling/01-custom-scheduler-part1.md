# 自定义 Scheduler

> **支持版本**: Kubernetes 1.31, 1.32, 1.33 **最后更新**: February 19, 2026

Kubernetes scheduler 是一个关键组件，用于决定 Pod 应该放置在哪个 node 上。虽然默认 scheduler 在大多数情况下运行良好，但你可以针对特定需求实现自定义 scheduler。在本章中，我们将学习如何在 EKS 中实现自定义 scheduler。

## 实验环境设置

要跟随本文档中的示例进行操作，你需要以下工具和环境：

### 必需工具

* kubectl v1.31 或更高版本
* Go 1.19 或更高版本（用于自定义 scheduler 开发）
* 一个可用的 Kubernetes cluster（EKS、minikube、kind 等）

### 开发环境设置

```bash
# Go development environment setup
mkdir -p $HOME/go/src/custom-scheduler
cd $HOME/go/src/custom-scheduler

# Initialize Go module
go mod init custom-scheduler

# Install required Kubernetes packages
go get k8s.io/kubernetes@v1.26.0
go get k8s.io/client-go@v0.26.0
go get k8s.io/klog/v2
```

## Scheduling 概述

### Kubernetes Scheduling 流程

Kubernetes scheduling 流程包括以下阶段：

### Scheduling 阶段详解

1. **Filtering Phase**
   * 识别适合运行该 Pod 的 node 的阶段
   * 每个 filter plugin 判断某个 node 是否可以承载该 Pod
   * 如果任何 filter 失败，该 node 将从候选列表中排除
2. **Scoring Phase**
   * 为经过 filtering 的 node 分配分数的阶段
   * 每个 scoring plugin 为 node 分配 0-100 之间的分数
   * 通过应用权重计算最终分数
3. **Binding Phase**
   * 将 Pod 分配到得分最高的 node 的阶段
   * 通过 Kubernetes API 更新 Pod-node 绑定信息

## 何时需要自定义 Scheduler

在以下情况下可以考虑使用自定义 scheduler：

1. **特殊硬件需求**：GPU、FPGA、特殊网络设备等。
2. **复杂的 Workload 放置规则**：将特定 workload 放置到特定 node group 上
3. **成本优化**：在 spot 和 on-demand instance 之间进行最优放置
4. **Locality 需求**：考虑数据 locality 的 workload 放置
5. **Multi-Scheduler 场景**：针对不同 workload 类型使用多个 scheduler

### 真实世界用例

| 行业               | 用例                           | 自定义 Scheduler 的优势                                 |
| ------------------ | ------------------------------ | --------------------------------------------------------- |
| 金融               | 高频交易系统                   | 感知网络拓扑的放置，用于最小化延迟                      |
| 医疗健康           | 医学图像处理                   | GPU 资源优化和数据 locality 保证                        |
| 电信               | 5G 网络功能                    | 保证接近特定网络设备                                    |
| 零售               | 季节性流量处理                 | 优化具有成本效益的 spot instance 使用                   |
| 媒体               | 视频转码                       | 根据 workload 特征选择 CPU/GPU node                     |

1. **Filtering**：识别 Pod 可以运行的 node。此阶段会考虑资源需求、node selector、node affinity、taint 和 toleration 等。
2. **Scoring**：为经过 filtering 的 node 打分。此阶段会考虑 node 资源使用情况、inter-pod affinity、node affinity 等。
3. **Binding**：将 Pod 分配到得分最高的 node。

### 默认 Scheduler 的限制

默认 scheduler 可能存在以下限制：

1. **特定硬件需求**：对于 GPU、FPGA 等特殊硬件，可能需要高级 scheduling 逻辑。
2. **复杂的 Affinity 规则**：可能存在难以用基本 affinity 规则表达的复杂放置约束。
3. **自定义 Metrics**：Scheduling 可能需要基于默认 scheduler 不考虑的自定义 metrics。
4. **特定领域知识**：可能需要针对特定应用领域专门设计的 scheduling 逻辑。

## 自定义 Scheduler 实现方法

实现自定义 scheduler 主要有三种方法：

1. **Multiple Scheduler Approach**：在默认 scheduler 旁边运行自定义 scheduler。
2. **Scheduler Extender Approach**：扩展默认 scheduler，以提供额外的 filtering 和 priority function。
3. **Scheduler Framework Plugins**：使用 Kubernetes 1.15 中引入的 scheduler framework 开发 plugin。

### Multiple Scheduler Approach

在 multiple scheduler approach 中，自定义 scheduler 与默认 scheduler 并行运行。创建 Pod 时，你可以使用 `schedulerName` 字段指定要使用的 scheduler。

#### 自定义 Scheduler 实现

你可以使用 Go 语言实现自定义 scheduler。下面是一个简单示例：

```go
package main

import (
    "context"
    "fmt"
    "time"

    v1 "k8s.io/api/core/v1"
    metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
    "k8s.io/client-go/kubernetes"
    "k8s.io/client-go/rest"
)

func main() {
    // Create Kubernetes client
    config, err := rest.InClusterConfig()
    if err != nil {
        panic(err.Error())
    }
    clientset, err := kubernetes.NewForConfig(config)
    if err != nil {
        panic(err.Error())
    }

    // Scheduling loop
    for {
        // Find unscheduled pods
        pods, err := clientset.CoreV1().Pods("").List(context.TODO(), metav1.ListOptions{
            FieldSelector: "spec.schedulerName=custom-scheduler,spec.nodeName=",
        })
        if err != nil {
            fmt.Printf("Error listing pods: %v\n", err)
            time.Sleep(5 * time.Second)
            continue
        }

        // Schedule each pod
        for _, pod := range pods.Items {
            // Select node
            node, err := selectNode(clientset, &pod)
            if err != nil {
                fmt.Printf("Error selecting node for pod %s/%s: %v\n", pod.Namespace, pod.Name, err)
                continue
            }

            // Bind pod to node
            err = bindPod(clientset, &pod, node)
            if err != nil {
                fmt.Printf("Error binding pod %s/%s to node %s: %v\n", pod.Namespace, pod.Name, node, err)
                continue
            }

            fmt.Printf("Successfully scheduled pod %s/%s to node %s\n", pod.Namespace, pod.Name, node)
        }

        time.Sleep(1 * time.Second)
    }
}

// Node selection function
func selectNode(clientset *kubernetes.Clientset, pod *v1.Pod) (string, error) {
    // Get node list
    nodes, err := clientset.CoreV1().Nodes().List(context.TODO(), metav1.ListOptions{})
    if err != nil {
        return "", err
    }

    // Simple example: select the first Ready node
    for _, node := range nodes.Items {
        for _, condition := range node.Status.Conditions {
            if condition.Type == v1.NodeReady && condition.Status == v1.ConditionTrue {
                return node.Name, nil
            }
        }
    }

    return "", fmt.Errorf("no ready nodes available")
}

// Function to bind pod to node
func bindPod(clientset *kubernetes.Clientset, pod *v1.Pod, node string) error {
    binding := &v1.Binding{
        ObjectMeta: metav1.ObjectMeta{
            Name:      pod.Name,
            Namespace: pod.Namespace,
        },
        Target: v1.ObjectReference{
            Kind:       "Node",
            Name:       node,
            APIVersion: "v1",
        },
    }

    return clientset.CoreV1().Pods(pod.Namespace).Bind(context.TODO(), binding, metav1.CreateOptions{})
}
```

#### 自定义 Scheduler 部署

将自定义 scheduler 构建为 container image，并将其部署到 Kubernetes：

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: custom-scheduler
  namespace: kube-system
spec:
  replicas: 1
  selector:
    matchLabels:
      app: custom-scheduler
  template:
    metadata:
      labels:
        app: custom-scheduler
    spec:
      serviceAccountName: custom-scheduler
      containers:
      - name: custom-scheduler
        image: your-registry/custom-scheduler:latest
        resources:
          requests:
            cpu: "100m"
            memory: "100Mi"
          limits:
            cpu: "200m"
            memory: "200Mi"
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: custom-scheduler
  namespace: kube-system
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: custom-scheduler
rules:
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "list", "watch", "update", "patch"]
- apiGroups: [""]
  resources: ["pods/binding"]
  verbs: ["create"]
- apiGroups: [""]
  resources: ["nodes"]
  verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: custom-scheduler
subjects:
- kind: ServiceAccount
  name: custom-scheduler
  namespace: kube-system
roleRef:
  kind: ClusterRole
  name: custom-scheduler
  apiGroup: rbac.authorization.k8s.io
```

#### 使用自定义 Scheduler

创建 Pod 时，使用 `schedulerName` 字段指定自定义 scheduler：

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: nginx
spec:
  schedulerName: custom-scheduler
  containers:
  - name: nginx
    image: nginx:latest
```

## 在 EKS 中实现自定义 Scheduler

在 Amazon EKS 中实现自定义 scheduler 时，请考虑以下事项：

1. **IAM 权限**：自定义 scheduler 需要适当的 IAM 权限，才能与 EKS cluster 交互。
2. **Node Group 管理**：Scheduling 逻辑必须考虑各种 node group（managed、self-managed、Fargate）。
3. **Availability Zone 感知**：可能需要 scheduling 逻辑来维持 availability zone 之间的均衡。
4. **Instance Type 感知**：可能需要针对各种 instance type 的 scheduling 逻辑。

### EKS 自定义 Scheduler 架构

下图展示了如何在 EKS cluster 中实现自定义 scheduler：

### EKS 特定的 Scheduling 注意事项

#### 1. Instance Type 感知的 Scheduling

EKS cluster 中可以使用各种 instance type。自定义 scheduler 可以选择与 workload 特征匹配的 instance type。

```go
// Function to calculate score based on instance type
func scoreNodeByInstanceType(node *v1.Node) int {
    instanceType, exists := node.Labels["node.kubernetes.io/instance-type"]
    if !exists {
        return 0
    }

    // Assign scores to instance types based on workload characteristics
    switch {
    case strings.HasPrefix(instanceType, "c5"):
        return 10  // Compute-optimized instances
    case strings.HasPrefix(instanceType, "m5"):
        return 5   // General-purpose instances
    case strings.HasPrefix(instanceType, "r5"):
        return 3   // Memory-optimized instances
    default:
        return 1
    }
}
```

#### 2. Availability Zone 分布 Scheduling

你可以实现 scheduling 逻辑，在 EKS cluster 中将 Pod 分布到多个 availability zone，以实现高可用性。

```go
// Function to calculate score for availability zone distribution
func scoreNodeByAZ(node *v1.Node, pod *v1.Pod, clientset *kubernetes.Clientset) int {
    // Check node's availability zone
    zone, exists := node.Labels["topology.kubernetes.io/zone"]
    if !exists {
        return 0
    }

    // Query running pods in the current pod's namespace
    pods, err := clientset.CoreV1().Pods(pod.Namespace).List(context.TODO(), metav1.ListOptions{
        FieldSelector: "status.phase=Running",
    })
    if err != nil {
        return 0
    }

    // Calculate the number of pods in each availability zone
    azPodCount := make(map[string]int)
    for _, p := range pods.Items {
        if p.Spec.NodeName == "" {
            continue
        }

        node, err := clientset.CoreV1().Nodes().Get(context.TODO(), p.Spec.NodeName, metav1.GetOptions{})
        if err != nil {
            continue
        }

        if az, exists := node.Labels["topology.kubernetes.io/zone"]; exists {
            azPodCount[az]++
        }
    }

    // Assign higher score to availability zones with fewer pods
    totalAZs := len(azPodCount)
    if totalAZs == 0 {
        return 10
    }

    // Assign higher score if current AZ has fewer pods than average
    totalPods := 0
    for _, count := range azPodCount {
        totalPods += count
    }
    averagePods := float64(totalPods) / float64(totalAZs)

    if float64(azPodCount[zone]) < averagePods {
        return 10
    } else {
        return 5
    }
}
```

#### 3. Spot Instance 感知的 Scheduling

你可以在 scheduling 时区分 spot 和 on-demand instance，以优化成本。

```go
// Spot instance-aware scheduling function
func scoreNodeByLifecycle(node *v1.Node, pod *v1.Pod) int {
    // Check node's lifecycle
    lifecycle, exists := node.Labels["node.kubernetes.io/lifecycle"]
    if !exists {
        return 5  // Middle score if no lifecycle info
    }

    // Check if pod has specific lifecycle requirements
    if pod.Labels["lifecycle-preference"] == "on-demand" {
        // Prefer on-demand instances
        if lifecycle == "on-demand" {
            return 10
        } else {
            return 1
        }
    } else if pod.Labels["lifecycle-preference"] == "spot" {
        // Prefer spot instances
        if lifecycle == "spot" {
            return 10
        } else {
            return 1
        }
    } else {
        // Default: prefer spot instances for cost optimization
        if lifecycle == "spot" {
            return 8
        } else {
            return 5
        }
    }
}
```

#### 4. GPU Workload Scheduling

你可以实现逻辑，在 EKS cluster 中高效地调度 GPU workload。

```go
// GPU workload scheduling function
func scoreNodeByGPU(node *v1.Node, pod *v1.Pod) int {
    // Check pod's GPU request
    gpuRequested := false
    for _, container := range pod.Spec.Containers {
        if _, exists := container.Resources.Requests["nvidia.com/gpu"]; exists {
            gpuRequested = true
            break
        }
    }

    // Check node's GPU availability
    gpuCapacity := 0
    if capacity, exists := node.Status.Capacity["nvidia.com/gpu"]; exists {
        gpuCapacity, _ = capacity.AsInt64()
    }

    // For GPU requests, assign higher score to nodes with GPUs
    if gpuRequested {
        if gpuCapacity > 0 {
            return 10
        } else {
            return 0  // Don't schedule on nodes without GPUs
        }
    } else {
        if gpuCapacity > 0 {
            return 1  // Lower score for non-GPU workloads on GPU nodes
        } else {
            return 5  // Higher score for non-GPU workloads on non-GPU nodes
        }
    }
}
```

## 总结

在本章中，我们概述了 Kubernetes scheduling 流程，并介绍了如何使用 multiple scheduler approach 实现自定义 scheduler。我们还探讨了在 EKS cluster 中实现自定义 scheduler 时的注意事项。

在下一章中，我们将学习如何使用 scheduler extender approach 和 scheduler framework plugins 实现自定义 scheduler。

## 测验

为了测试你在本章中学到的内容，请尝试 [主题测验](../quizzes/scheduling/02-custom-scheduler-part1-quiz.md)。
