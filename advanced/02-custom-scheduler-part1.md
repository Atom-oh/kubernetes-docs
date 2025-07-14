# 커스텀 스케줄러 - 1부

Kubernetes 스케줄러는 포드를 어떤 노드에 배치할지 결정하는 중요한 구성 요소입니다. 기본 스케줄러는 대부분의 경우 잘 작동하지만, 특정 요구 사항이 있는 경우 커스텀 스케줄러를 구현할 수 있습니다. 이 장에서는 EKS에서 커스텀 스케줄러를 구현하는 방법을 알아보겠습니다.

## 스케줄링 개요

### Kubernetes 스케줄링 프로세스

Kubernetes 스케줄링 프로세스는 다음과 같은 단계로 이루어집니다:

1. **필터링(Filtering)**: 포드를 실행할 수 있는 노드를 식별합니다. 이 단계에서는 리소스 요구 사항, 노드 선택기, 노드 어피니티, 테인트 및 톨러레이션 등을 고려합니다.
2. **점수 매기기(Scoring)**: 필터링된 노드에 점수를 매깁니다. 이 단계에서는 노드의 리소스 사용량, 포드 간 어피니티, 노드 어피니티 등을 고려합니다.
3. **바인딩(Binding)**: 가장 높은 점수를 받은 노드에 포드를 할당합니다.

### 기본 스케줄러의 한계

기본 스케줄러는 다음과 같은 한계가 있을 수 있습니다:

1. **특정 하드웨어 요구 사항**: GPU, FPGA 등 특수 하드웨어에 대한 고급 스케줄링 로직이 필요할 수 있습니다.
2. **복잡한 어피니티 규칙**: 기본 어피니티 규칙으로는 표현하기 어려운 복잡한 배치 제약 조건이 있을 수 있습니다.
3. **사용자 정의 메트릭**: 기본 스케줄러가 고려하지 않는 사용자 정의 메트릭을 기반으로 스케줄링해야 할 수 있습니다.
4. **특정 도메인 지식**: 특정 애플리케이션 도메인에 특화된 스케줄링 로직이 필요할 수 있습니다.

## 커스텀 스케줄러 구현 방법

커스텀 스케줄러를 구현하는 방법은 크게 세 가지가 있습니다:

1. **다중 스케줄러 접근 방식**: 기본 스케줄러와 함께 커스텀 스케줄러를 실행합니다.
2. **스케줄러 확장(Extender) 접근 방식**: 기본 스케줄러를 확장하여 추가 필터링 및 우선순위 기능을 제공합니다.
3. **스케줄러 프레임워크 플러그인**: Kubernetes 1.15부터 도입된 스케줄러 프레임워크를 사용하여 플러그인을 개발합니다.

### 다중 스케줄러 접근 방식

다중 스케줄러 접근 방식에서는 기본 스케줄러와 함께 커스텀 스케줄러를 실행합니다. 포드를 생성할 때 `schedulerName` 필드를 사용하여 어떤 스케줄러를 사용할지 지정할 수 있습니다.

#### 커스텀 스케줄러 구현

Go 언어를 사용하여 커스텀 스케줄러를 구현할 수 있습니다. 다음은 간단한 예제입니다:

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
    // Kubernetes 클라이언트 생성
    config, err := rest.InClusterConfig()
    if err != nil {
        panic(err.Error())
    }
    clientset, err := kubernetes.NewForConfig(config)
    if err != nil {
        panic(err.Error())
    }

    // 스케줄링 루프
    for {
        // 스케줄링되지 않은 포드 찾기
        pods, err := clientset.CoreV1().Pods("").List(context.TODO(), metav1.ListOptions{
            FieldSelector: "spec.schedulerName=custom-scheduler,spec.nodeName=",
        })
        if err != nil {
            fmt.Printf("Error listing pods: %v\n", err)
            time.Sleep(5 * time.Second)
            continue
        }

        // 각 포드에 대해 스케줄링 수행
        for _, pod := range pods.Items {
            // 노드 선택
            node, err := selectNode(clientset, &pod)
            if err != nil {
                fmt.Printf("Error selecting node for pod %s/%s: %v\n", pod.Namespace, pod.Name, err)
                continue
            }

            // 포드를 노드에 바인딩
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

// 노드 선택 함수
func selectNode(clientset *kubernetes.Clientset, pod *v1.Pod) (string, error) {
    // 노드 목록 가져오기
    nodes, err := clientset.CoreV1().Nodes().List(context.TODO(), metav1.ListOptions{})
    if err != nil {
        return "", err
    }

    // 간단한 예제: 첫 번째 Ready 상태의 노드 선택
    for _, node := range nodes.Items {
        for _, condition := range node.Status.Conditions {
            if condition.Type == v1.NodeReady && condition.Status == v1.ConditionTrue {
                return node.Name, nil
            }
        }
    }

    return "", fmt.Errorf("no ready nodes available")
}

// 포드를 노드에 바인딩하는 함수
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

#### 커스텀 스케줄러 배포

커스텀 스케줄러를 컨테이너 이미지로 빌드하고 Kubernetes에 배포합니다:

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

#### 커스텀 스케줄러 사용

포드를 생성할 때 `schedulerName` 필드를 사용하여 커스텀 스케줄러를 지정합니다:

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
