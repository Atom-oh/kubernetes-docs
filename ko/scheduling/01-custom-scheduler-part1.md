# Part 1: 커스텀 스케줄러 기초

> **지원 버전**: Kubernetes 1.31, 1.32, 1.33  
> **마지막 업데이트**: 2025년 11월 24일

Kubernetes 스케줄러는 포드를 어떤 노드에 배치할지 결정하는 중요한 구성 요소입니다. 기본 스케줄러는 대부분의 경우 잘 작동하지만, 특정 요구 사항이 있는 경우 커스텀 스케줄러를 구현할 수 있습니다. 이 장에서는 EKS에서 커스텀 스케줄러를 구현하는 방법을 알아보겠습니다.

## 실습 환경 설정

이 문서의 예제를 따라하기 위해서는 다음과 같은 도구와 환경이 필요합니다:

### 필수 도구
- kubectl v1.31 이상
- Go 1.19 이상 (커스텀 스케줄러 개발용)
- 작동하는 Kubernetes 클러스터 (EKS, minikube, kind 등)

### 개발 환경 설정

```bash
# Go 개발 환경 설정
mkdir -p $HOME/go/src/custom-scheduler
cd $HOME/go/src/custom-scheduler

# Go 모듈 초기화
go mod init custom-scheduler

# 필요한 Kubernetes 패키지 설치
go get k8s.io/kubernetes@v1.26.0
go get k8s.io/client-go@v0.26.0
go get k8s.io/klog/v2
```

## 스케줄링 개요

### Kubernetes 스케줄링 프로세스

Kubernetes 스케줄링 프로세스는 다음과 같은 단계로 이루어집니다:

![kubernetes_scheduling_process](../assets/kubernetes_scheduling_process.svg)

### 스케줄링 단계 상세 설명

1. **필터링 단계 (Filtering Phase)**
   - 포드가 실행될 수 있는 적합한 노드를 찾는 단계
   - 각 필터 플러그인은 노드가 포드를 호스팅할 수 있는지 여부를 결정
   - 하나의 필터라도 실패하면 해당 노드는 후보에서 제외됨

2. **점수 매기기 단계 (Scoring Phase)**
   - 필터링을 통과한 노드에 점수를 매기는 단계
   - 각 점수 플러그인은 노드에 0-100 사이의 점수를 부여
   - 가중치를 적용하여 최종 점수 계산

3. **바인딩 단계 (Binding Phase)**
   - 최고 점수를 받은 노드에 포드를 할당하는 단계
   - Kubernetes API를 통해 포드-노드 바인딩 정보 업데이트

## 커스텀 스케줄러가 필요한 경우

다음과 같은 경우에 커스텀 스케줄러를 고려할 수 있습니다:

1. **특수한 하드웨어 요구 사항**: GPU, FPGA, 특수 네트워크 장치 등
2. **복잡한 워크로드 배치 규칙**: 특정 노드 그룹에 특정 워크로드 배치
3. **비용 최적화**: 스팟 인스턴스와 온디맨드 인스턴스 간의 최적 배치
4. **지역성 요구 사항**: 데이터 지역성을 고려한 워크로드 배치
5. **다중 스케줄러 시나리오**: 다양한 워크로드 유형에 대해 여러 스케줄러 사용

### 실제 사용 사례

| 산업 | 사용 사례 | 커스텀 스케줄러 이점 |
|------|----------|-------------------|
| 금융 | 고주파 거래 시스템 | 지연 시간 최소화를 위한 네트워크 토폴로지 인식 배치 |
| 의료 | 의료 영상 처리 | GPU 리소스 최적화 및 데이터 지역성 보장 |
| 통신 | 5G 네트워크 기능 | 특정 네트워크 장치에 대한 근접성 보장 |
| 소매 | 계절적 트래픽 처리 | 비용 효율적인 스팟 인스턴스 활용 최적화 |
| 미디어 | 비디오 트랜스코딩 | 워크로드 특성에 따른 CPU/GPU 노드 선택 |

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

![multi_scheduler_approach](../assets/multi_scheduler_approach.svg)

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

## EKS에서의 커스텀 스케줄러 구현

Amazon EKS에서 커스텀 스케줄러를 구현할 때는 다음과 같은 사항을 고려해야 합니다:

1. **IAM 권한**: 커스텀 스케줄러가 EKS 클러스터와 상호 작용하기 위한 적절한 IAM 권한이 필요합니다.
2. **노드 그룹 관리**: 다양한 노드 그룹(관리형, 자체 관리형, Fargate)에 대한 스케줄링 로직을 고려해야 합니다.
3. **가용 영역 인식**: 가용 영역 간의 균형을 유지하기 위한 스케줄링 로직이 필요할 수 있습니다.
4. **인스턴스 유형 인식**: 다양한 인스턴스 유형에 대한 스케줄링 로직이 필요할 수 있습니다.

### EKS 커스텀 스케줄러 아키텍처

다음 다이어그램은 EKS 클러스터에서 커스텀 스케줄러를 구현하는 방법을 보여줍니다:

![EKS 커스텀 스케줄러 아키텍처](../assets/eks_custom_scheduler_architecture.svg)

### EKS 특화 스케줄링 고려 사항

#### 1. 인스턴스 유형 인식 스케줄링

EKS 클러스터에서는 다양한 인스턴스 유형을 사용할 수 있습니다. 커스텀 스케줄러는 워크로드 특성에 맞는 인스턴스 유형을 선택할 수 있습니다.

```go
// 인스턴스 유형에 따른 점수 계산 함수
func scoreNodeByInstanceType(node *v1.Node) int {
    instanceType, exists := node.Labels["node.kubernetes.io/instance-type"]
    if !exists {
        return 0
    }
    
    // 워크로드 특성에 따라 인스턴스 유형에 점수 할당
    switch {
    case strings.HasPrefix(instanceType, "c5"):
        return 10  // 컴퓨팅 최적화 인스턴스
    case strings.HasPrefix(instanceType, "m5"):
        return 5   // 범용 인스턴스
    case strings.HasPrefix(instanceType, "r5"):
        return 3   // 메모리 최적화 인스턴스
    default:
        return 1
    }
}
```

#### 2. 가용 영역 분산 스케줄링

EKS 클러스터의 고가용성을 위해 포드를 여러 가용 영역에 분산하는 스케줄링 로직을 구현할 수 있습니다.

```go
// 가용 영역 분산을 위한 점수 계산 함수
func scoreNodeByAZ(node *v1.Node, pod *v1.Pod, clientset *kubernetes.Clientset) int {
    // 노드의 가용 영역 확인
    zone, exists := node.Labels["topology.kubernetes.io/zone"]
    if !exists {
        return 0
    }
    
    // 현재 포드의 네임스페이스에서 실행 중인 포드 조회
    pods, err := clientset.CoreV1().Pods(pod.Namespace).List(context.TODO(), metav1.ListOptions{
        FieldSelector: "status.phase=Running",
    })
    if err != nil {
        return 0
    }
    
    // 각 가용 영역에 있는 포드 수 계산
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
    
    // 포드 수가 적은 가용 영역에 높은 점수 할당
    totalAZs := len(azPodCount)
    if totalAZs == 0 {
        return 10
    }
    
    // 현재 가용 영역의 포드 수가 평균보다 적으면 높은 점수 할당
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

#### 3. 스팟 인스턴스 인식 스케줄링

비용 최적화를 위해 스팟 인스턴스와 온디맨드 인스턴스를 구분하여 스케줄링할 수 있습니다.

```go
// 스팟 인스턴스 인식 스케줄링 함수
func scoreNodeByLifecycle(node *v1.Node, pod *v1.Pod) int {
    // 노드의 라이프사이클 확인
    lifecycle, exists := node.Labels["node.kubernetes.io/lifecycle"]
    if !exists {
        return 5  // 라이프사이클 정보가 없으면 중간 점수
    }
    
    // 포드에 특정 라이프사이클 요구 사항이 있는지 확인
    if pod.Labels["lifecycle-preference"] == "on-demand" {
        // 온디맨드 인스턴스 선호
        if lifecycle == "on-demand" {
            return 10
        } else {
            return 1
        }
    } else if pod.Labels["lifecycle-preference"] == "spot" {
        // 스팟 인스턴스 선호
        if lifecycle == "spot" {
            return 10
        } else {
            return 1
        }
    } else {
        // 기본적으로 비용 최적화를 위해 스팟 인스턴스 선호
        if lifecycle == "spot" {
            return 8
        } else {
            return 5
        }
    }
}
```

#### 4. GPU 워크로드 스케줄링

EKS 클러스터에서 GPU 워크로드를 효율적으로 스케줄링하기 위한 로직을 구현할 수 있습니다.

```go
// GPU 워크로드 스케줄링 함수
func scoreNodeByGPU(node *v1.Node, pod *v1.Pod) int {
    // 포드의 GPU 요청 확인
    gpuRequested := false
    for _, container := range pod.Spec.Containers {
        if _, exists := container.Resources.Requests["nvidia.com/gpu"]; exists {
            gpuRequested = true
            break
        }
    }
    
    // 노드의 GPU 가용성 확인
    gpuCapacity := 0
    if capacity, exists := node.Status.Capacity["nvidia.com/gpu"]; exists {
        gpuCapacity, _ = capacity.AsInt64()
    }
    
    // GPU 요청이 있는 경우 GPU가 있는 노드에 높은 점수 할당
    if gpuRequested {
        if gpuCapacity > 0 {
            return 10
        } else {
            return 0  // GPU가 없는 노드에는 스케줄링하지 않음
        }
    } else {
        if gpuCapacity > 0 {
            return 1  // GPU가 필요하지 않은 워크로드는 GPU 노드에 낮은 점수 할당
        } else {
            return 5  // GPU가 필요하지 않은 워크로드는 비 GPU 노드에 높은 점수 할당
        }
    }
}
```

## 결론

이 장에서는 Kubernetes 스케줄링 프로세스의 개요와 다중 스케줄러 접근 방식을 사용하여 커스텀 스케줄러를 구현하는 방법을 알아보았습니다. 또한 EKS 클러스터에서 커스텀 스케줄러를 구현할 때 고려해야 할 사항들을 살펴보았습니다.

다음 장에서는 스케줄러 확장(Extender) 접근 방식과 스케줄러 프레임워크 플러그인을 사용하여 커스텀 스케줄러를 구현하는 방법을 알아보겠습니다.

## 퀴즈

이 장에서 배운 내용을 테스트하려면 [주제 퀴즈](../quizzes/scheduling/02-custom-scheduler-part1-quiz.md)를 풀어보세요.
