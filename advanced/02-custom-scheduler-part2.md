# 커스텀 스케줄러 - 2부

## 스케줄러 확장(Extender) 접근 방식

스케줄러 확장 접근 방식은 기본 스케줄러의 기능을 확장하는 방법입니다. 이 접근 방식에서는 기본 스케줄러가 HTTP 요청을 통해 외부 서비스(스케줄러 확장)를 호출하여 추가 필터링 및 우선순위 기능을 제공합니다.

### 스케줄러 확장 구현

스케줄러 확장은 다음과 같은 HTTP 엔드포인트를 제공해야 합니다:

1. **필터(Filter)**: 포드를 실행할 수 없는 노드를 필터링합니다.
2. **우선순위(Prioritize)**: 노드에 우선순위 점수를 할당합니다.
3. **바인드(Bind)**: 포드를 노드에 바인딩합니다(선택 사항).
4. **사전 필터(Prefilter)**: 필터링 전에 포드를 검사합니다(선택 사항).
5. **사전 점수(Prescore)**: 점수 매기기 전에 포드를 검사합니다(선택 사항).

다음은 Go 언어를 사용한 간단한 스케줄러 확장 예제입니다:

```go
package main

import (
    "encoding/json"
    "log"
    "net/http"

    "github.com/julienschmidt/httprouter"
    extenderv1 "k8s.io/kube-scheduler/extender/v1"
)

func main() {
    router := httprouter.New()
    router.POST("/filter", filterHandler)
    router.POST("/prioritize", prioritizeHandler)

    log.Fatal(http.ListenAndServe(":8888", router))
}

// 필터 핸들러
func filterHandler(w http.ResponseWriter, r *http.Request, _ httprouter.Params) {
    var extenderArgs extenderv1.ExtenderArgs
    var extenderFilterResult extenderv1.ExtenderFilterResult

    if err := json.NewDecoder(r.Body).Decode(&extenderArgs); err != nil {
        http.Error(w, err.Error(), http.StatusBadRequest)
        return
    }

    // 모든 노드를 허용하는 간단한 예제
    extenderFilterResult.Nodes = extenderArgs.Nodes
    extenderFilterResult.FailedNodes = make(map[string]string)

    // 특정 조건에 따라 노드 필터링
    // 예: GPU 요구 사항이 있는 포드에 대해 GPU가 있는 노드만 허용
    if requiresGPU(&extenderArgs.Pod) {
        filteredNodes := &extenderv1.NodeList{
            Items: make([]extenderv1.Node, 0),
        }
        
        for _, node := range extenderArgs.Nodes.Items {
            if hasGPU(&node) {
                filteredNodes.Items = append(filteredNodes.Items, node)
            } else {
                extenderFilterResult.FailedNodes[node.Name] = "Node does not have GPU"
            }
        }
        
        extenderFilterResult.Nodes = filteredNodes
    }

    if err := json.NewEncoder(w).Encode(extenderFilterResult); err != nil {
        http.Error(w, err.Error(), http.StatusInternalServerError)
        return
    }
}

// 우선순위 핸들러
func prioritizeHandler(w http.ResponseWriter, r *http.Request, _ httprouter.Params) {
    var extenderArgs extenderv1.ExtenderArgs
    var hostPriorityList extenderv1.HostPriorityList

    if err := json.NewDecoder(r.Body).Decode(&extenderArgs); err != nil {
        http.Error(w, err.Error(), http.StatusBadRequest)
        return
    }

    // 각 노드에 점수 할당
    hostPriorityList = make(extenderv1.HostPriorityList, len(extenderArgs.Nodes.Items))
    for i, node := range extenderArgs.Nodes.Items {
        // 간단한 예제: 모든 노드에 동일한 점수 할당
        hostPriorityList[i] = extenderv1.HostPriority{
            Host:  node.Name,
            Score: 1,
        }
        
        // 특정 조건에 따라 점수 조정
        // 예: GPU 메모리가 많은 노드에 더 높은 점수 할당
        if requiresGPU(&extenderArgs.Pod) && hasGPU(&node) {
            gpuMemory := getGPUMemory(&node)
            hostPriorityList[i].Score = int64(gpuMemory / 1024) // GB 단위로 변환
        }
    }

    if err := json.NewEncoder(w).Encode(hostPriorityList); err != nil {
        http.Error(w, err.Error(), http.StatusInternalServerError)
        return
    }
}

// GPU 요구 사항 확인 함수
func requiresGPU(pod *extenderv1.Pod) bool {
    // 포드의 리소스 요청에서 GPU 요구 사항 확인
    for _, container := range pod.Spec.Containers {
        if _, ok := container.Resources.Requests["nvidia.com/gpu"]; ok {
            return true
        }
    }
    return false
}

// 노드에 GPU가 있는지 확인하는 함수
func hasGPU(node *extenderv1.Node) bool {
    // 노드의 용량에서 GPU 확인
    if _, ok := node.Status.Capacity["nvidia.com/gpu"]; ok {
        return true
    }
    return false
}

// 노드의 GPU 메모리 확인 함수
func getGPUMemory(node *extenderv1.Node) int {
    // 노드 레이블에서 GPU 메모리 확인
    if memoryStr, ok := node.Labels["gpu.nvidia.com/memory"]; ok {
        var memory int
        fmt.Sscanf(memoryStr, "%d", &memory)
        return memory
    }
    return 0
}
```

### 스케줄러 확장 배포

스케줄러 확장을 컨테이너 이미지로 빌드하고 Kubernetes에 배포합니다:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: scheduler-extender
  namespace: kube-system
spec:
  replicas: 1
  selector:
    matchLabels:
      app: scheduler-extender
  template:
    metadata:
      labels:
        app: scheduler-extender
    spec:
      containers:
      - name: scheduler-extender
        image: your-registry/scheduler-extender:latest
        ports:
        - containerPort: 8888
        resources:
          requests:
            cpu: "100m"
            memory: "100Mi"
          limits:
            cpu: "200m"
            memory: "200Mi"
---
apiVersion: v1
kind: Service
metadata:
  name: scheduler-extender
  namespace: kube-system
spec:
  selector:
    app: scheduler-extender
  ports:
  - port: 8888
    targetPort: 8888
```

### 스케줄러 구성

스케줄러 확장을 사용하려면 기본 스케줄러의 구성을 수정해야 합니다. EKS에서는 다음과 같이 구성할 수 있습니다:

1. 스케줄러 구성 파일 생성:

```yaml
apiVersion: kubescheduler.config.k8s.io/v1beta1
kind: KubeSchedulerConfiguration
clientConnection:
  kubeconfig: /etc/kubernetes/scheduler.conf
extenders:
- urlPrefix: "http://scheduler-extender.kube-system.svc.cluster.local:8888"
  filterVerb: "filter"
  prioritizeVerb: "prioritize"
  weight: 1
  enableHTTPS: false
  nodeCacheCapable: false
```

2. 스케줄러 구성을 ConfigMap으로 생성:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: scheduler-config
  namespace: kube-system
data:
  scheduler-config.yaml: |
    apiVersion: kubescheduler.config.k8s.io/v1beta1
    kind: KubeSchedulerConfiguration
    clientConnection:
      kubeconfig: /etc/kubernetes/scheduler.conf
    extenders:
    - urlPrefix: "http://scheduler-extender.kube-system.svc.cluster.local:8888"
      filterVerb: "filter"
      prioritizeVerb: "prioritize"
      weight: 1
      enableHTTPS: false
      nodeCacheCapable: false
```

3. 커스텀 스케줄러 배포:

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
      - name: kube-scheduler
        image: k8s.gcr.io/kube-scheduler:v1.23.0
        command:
        - kube-scheduler
        - --config=/etc/kubernetes/scheduler-config.yaml
        - --v=3
        volumeMounts:
        - name: scheduler-config
          mountPath: /etc/kubernetes/scheduler-config.yaml
          subPath: scheduler-config.yaml
        - name: kubeconfig
          mountPath: /etc/kubernetes/scheduler.conf
          readOnly: true
      volumes:
      - name: scheduler-config
        configMap:
          name: scheduler-config
      - name: kubeconfig
        hostPath:
          path: /etc/kubernetes/scheduler.conf
          type: File
```

## 스케줄러 프레임워크 플러그인

Kubernetes 1.15부터 도입된 스케줄러 프레임워크는 플러그인 기반 아키텍처를 제공합니다. 이 접근 방식을 사용하면 스케줄링 파이프라인의 다양한 단계에 플러그인을 구현할 수 있습니다.

### 스케줄링 프레임워크 확장 포인트

스케줄링 프레임워크는 다음과 같은 확장 포인트를 제공합니다:

1. **QueueSort**: 스케줄링 큐에서 포드의 순서를 결정합니다.
2. **PreFilter**: 필터링 전에 포드를 검사하고 필터링 데이터를 준비합니다.
3. **Filter**: 포드를 실행할 수 없는 노드를 필터링합니다.
4. **PreScore**: 점수 매기기 전에 포드를 검사하고 점수 매기기 데이터를 준비합니다.
5. **Score**: 노드에 점수를 할당합니다.
6. **NormalizeScore**: 각 점수 플러그인의 점수를 정규화합니다.
7. **Reserve**: 포드를 위한 리소스를 예약합니다.
8. **Permit**: 포드가 스케줄링될 수 있는지 여부를 결정합니다.
9. **PreBind**: 바인딩 전에 필요한 작업을 수행합니다.
10. **Bind**: 포드를 노드에 바인딩합니다.
11. **PostBind**: 바인딩 후에 필요한 작업을 수행합니다.

### 스케줄러 플러그인 구현

다음은 Go 언어를 사용한 간단한 스케줄러 플러그인 예제입니다:

```go
package main

import (
    "context"
    "fmt"

    v1 "k8s.io/api/core/v1"
    "k8s.io/apimachinery/pkg/runtime"
    "k8s.io/kubernetes/pkg/scheduler/framework"
)

// GPUSchedulerPlugin은 GPU 요구 사항에 따라 노드를 필터링하고 점수를 매기는 플러그인입니다.
type GPUSchedulerPlugin struct{}

var _ framework.FilterPlugin = &GPUSchedulerPlugin{}
var _ framework.ScorePlugin = &GPUSchedulerPlugin{}

// Name은 플러그인의 이름을 반환합니다.
func (gsp *GPUSchedulerPlugin) Name() string {
    return "GPUScheduler"
}

// Filter는 포드를 실행할 수 없는 노드를 필터링합니다.
func (gsp *GPUSchedulerPlugin) Filter(ctx context.Context, state *framework.CycleState, pod *v1.Pod, node *framework.NodeInfo) *framework.Status {
    // GPU 요구 사항이 있는 포드에 대해 GPU가 있는 노드만 허용
    if requiresGPU(pod) && !hasGPU(node.Node()) {
        return framework.NewStatus(framework.Unschedulable, "Node does not have GPU")
    }
    return framework.NewStatus(framework.Success, "")
}

// Score는 노드에 점수를 할당합니다.
func (gsp *GPUSchedulerPlugin) Score(ctx context.Context, state *framework.CycleState, pod *v1.Pod, nodeName string) (int64, *framework.Status) {
    nodeInfo, err := state.Read(framework.NodeInfoKey)
    if err != nil {
        return 0, framework.NewStatus(framework.Error, fmt.Sprintf("Error reading node info: %v", err))
    }
    
    node := nodeInfo.(*framework.NodeInfo).Node()
    
    // GPU 요구 사항이 있는 포드에 대해 GPU 메모리에 따라 점수 할당
    if requiresGPU(pod) && hasGPU(node) {
        gpuMemory := getGPUMemory(node)
        return int64(gpuMemory / 1024), framework.NewStatus(framework.Success, "") // GB 단위로 변환
    }
    
    return 0, framework.NewStatus(framework.Success, "")
}

// ScoreExtensions는 점수 플러그인의 확장을 반환합니다.
func (gsp *GPUSchedulerPlugin) ScoreExtensions() framework.ScoreExtensions {
    return gsp
}

// NormalizeScore는 점수를 정규화합니다.
func (gsp *GPUSchedulerPlugin) NormalizeScore(ctx context.Context, state *framework.CycleState, pod *v1.Pod, scores framework.NodeScoreList) *framework.Status {
    // 최대 점수 찾기
    var maxScore int64 = 1
    for _, score := range scores {
        if score.Score > maxScore {
            maxScore = score.Score
        }
    }
    
    // 점수 정규화 (0-100 범위)
    for i := range scores {
        if maxScore > 0 {
            scores[i].Score = scores[i].Score * 100 / maxScore
        } else {
            scores[i].Score = 0
        }
    }
    
    return framework.NewStatus(framework.Success, "")
}

// GPU 요구 사항 확인 함수
func requiresGPU(pod *v1.Pod) bool {
    // 포드의 리소스 요청에서 GPU 요구 사항 확인
    for _, container := range pod.Spec.Containers {
        if _, ok := container.Resources.Requests["nvidia.com/gpu"]; ok {
            return true
        }
    }
    return false
}

// 노드에 GPU가 있는지 확인하는 함수
func hasGPU(node *v1.Node) bool {
    // 노드의 용량에서 GPU 확인
    if _, ok := node.Status.Capacity["nvidia.com/gpu"]; ok {
        return true
    }
    return false
}

// 노드의 GPU 메모리 확인 함수
func getGPUMemory(node *v1.Node) int {
    // 노드 레이블에서 GPU 메모리 확인
    if memoryStr, ok := node.Labels["gpu.nvidia.com/memory"]; ok {
        var memory int
        fmt.Sscanf(memoryStr, "%d", &memory)
        return memory
    }
    return 0
}

// New는 플러그인의 새 인스턴스를 생성합니다.
func New(_ runtime.Object, _ framework.Handle) (framework.Plugin, error) {
    return &GPUSchedulerPlugin{}, nil
}
```

### 스케줄러 플러그인 등록

스케줄러 플러그인을 등록하려면 스케줄러 구성 파일을 수정해야 합니다:

```yaml
apiVersion: kubescheduler.config.k8s.io/v1beta1
kind: KubeSchedulerConfiguration
clientConnection:
  kubeconfig: /etc/kubernetes/scheduler.conf
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
  pluginConfig:
  - name: GPUScheduler
    args: {}
```
