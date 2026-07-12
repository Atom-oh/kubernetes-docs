# Custom Scheduler

> **サポート対象バージョン**: Kubernetes 1.31, 1.32, 1.33 **最終更新**: February 19, 2026

Kubernetes scheduler は、Pod（ポッド）をどの Node に配置するかを決定する重要なコンポーネントです。default scheduler はほとんどの場合でうまく機能しますが、特定の要件に合わせて custom scheduler を実装できます。この章では、EKS で custom scheduler を実装する方法を学びます。

## Lab Environment Setup

このドキュメントの例に沿って進めるには、次のツールと環境が必要です。

### Required Tools

* kubectl v1.31 以上
* Go 1.19 以上（custom scheduler 開発用）
* 稼働中の Kubernetes cluster（EKS、minikube、kind など）

### Development Environment Setup

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

## Scheduling Overview

### Kubernetes Scheduling Process

Kubernetes の scheduling process は、次の段階で構成されます。

### Detailed Explanation of Scheduling Stages

1. **Filtering Phase**
   * Pod を実行するのに適した Node を特定する段階です
   * 各 filter plugin が、Node が Pod をホストできるかどうかを判定します
   * いずれかの filter が失敗すると、その Node は候補から除外されます
2. **Scoring Phase**
   * filtering された Node に score を割り当てる段階です
   * 各 scoring plugin が Node に 0〜100 の score を割り当てます
   * weight を適用して最終 score が計算されます
3. **Binding Phase**
   * Pod を最も score の高い Node に割り当てる段階です
   * Pod-Node の binding 情報は Kubernetes API を通じて更新されます

## When Custom Schedulers Are Needed

次のような場合は、custom scheduler を検討してください。

1. **Special Hardware Requirements**: GPU、FPGA、特殊な network device など。
2. **Complex Workload Placement Rules**: 特定の workload を特定の node group に配置する場合。
3. **Cost Optimization**: spot instance と on-demand instance の間で最適に配置する場合。
4. **Locality Requirements**: data locality を考慮した workload 配置。
5. **Multi-Scheduler Scenarios**: 異なる workload type に対して複数の scheduler を使用する場合。

### Real-World Use Cases

| Industry           | Use Case                       | Custom Scheduler Benefits                                 |
| ------------------ | ------------------------------ | --------------------------------------------------------- |
| Finance            | High-frequency trading systems | Network topology-aware placement for latency minimization |
| Healthcare         | Medical image processing       | GPU resource optimization and data locality guarantee     |
| Telecommunications | 5G network functions           | Proximity guarantee to specific network devices           |
| Retail             | Seasonal traffic handling      | Cost-effective spot instance utilization optimization     |
| Media              | Video transcoding              | CPU/GPU node selection based on workload characteristics  |

1. **Filtering**: Pod を実行できる Node を特定します。この段階では、resource requirement、node selector、node affinity、taints and tolerations などを考慮します。
2. **Scoring**: filtering された Node に score を付けます。この段階では、Node の resource usage、inter-pod affinity、node affinity などを考慮します。
3. **Binding**: Pod を最も score の高い Node に割り当てます。

### Limitations of the Default Scheduler

default scheduler には、次のような制限がある場合があります。

1. **Specific Hardware Requirements**: GPU や FPGA のような特殊な hardware には、高度な scheduling logic が必要になる場合があります。
2. **Complex Affinity Rules**: 基本的な affinity rule では表現しにくい複雑な配置制約がある場合があります。
3. **Custom Metrics**: default scheduler が考慮しない custom metrics に基づいて scheduling する必要がある場合があります。
4. **Domain-Specific Knowledge**: 特定の application domain に特化した scheduling logic が必要になる場合があります。

## Custom Scheduler Implementation Methods

custom scheduler を実装する主なアプローチは 3 つあります。

1. **Multiple Scheduler Approach**: default scheduler と並行して custom scheduler を実行します。
2. **Scheduler Extender Approach**: default scheduler を拡張し、追加の filtering function と priority function を提供します。
3. **Scheduler Framework Plugins**: Kubernetes 1.15 で導入された scheduler framework を使用して plugin を開発します。

### Multiple Scheduler Approach

multiple scheduler approach では、custom scheduler が default scheduler と並行して実行されます。Pod を作成するときに、`schedulerName` field で使用する scheduler を指定できます。

#### Custom Scheduler Implementation

Go 言語を使用して custom scheduler を実装できます。以下は簡単な例です。

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

#### Custom Scheduler Deployment

custom scheduler を container image として build し、Kubernetes に deploy します。

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

#### Using the Custom Scheduler

Pod を作成するときに、`schedulerName` field を使用して custom scheduler を指定します。

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

## Custom Scheduler Implementation in EKS

Amazon EKS で custom scheduler を実装する場合は、次の点を考慮してください。

1. **IAM Permissions**: custom scheduler が EKS cluster とやり取りするには、適切な IAM permission が必要です。
2. **Node Group Management**: scheduling logic は、さまざまな node group（managed、self-managed、Fargate）を考慮する必要があります。
3. **Availability Zone Awareness**: availability zone 間の balance を維持するための scheduling logic が必要になる場合があります。
4. **Instance Type Awareness**: さまざまな instance type に対応する scheduling logic が必要になる場合があります。

### EKS Custom Scheduler Architecture

次の図は、EKS cluster で custom scheduler を実装する方法を示しています。

### EKS-Specific Scheduling Considerations

#### 1. Instance Type-Aware Scheduling

EKS cluster では、さまざまな instance type を使用できます。custom scheduler は、workload characteristics に一致する instance type を選択できます。

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

#### 2. Availability Zone Distribution Scheduling

EKS cluster で高可用性を実現するために、複数の availability zone に Pod を分散する scheduling logic を実装できます。

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

#### 3. Spot Instance-Aware Scheduling

cost を最適化するために、scheduling で spot instance と on-demand instance を区別できます。

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

EKS cluster で GPU workload を効率的に schedule する logic を実装できます。

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

## Conclusion

この章では、Kubernetes scheduling process の概要と、multiple scheduler approach を使用して custom scheduler を実装する方法を扱いました。また、EKS cluster で custom scheduler を実装する際の考慮事項についても確認しました。

次の章では、scheduler extender approach と scheduler framework plugin を使用した custom scheduler の実装について学びます。

## Quiz

この章で学んだ内容を確認するために、[トピッククイズ](../quizzes/scheduling/02-custom-scheduler-part1-quiz.md)に挑戦してください。
