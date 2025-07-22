# Custom Scheduler 퀴즈 (Part 1)

이 퀴즈는 Kubernetes에서 Custom Scheduler를 구현하고 사용하는 방법에 대한 이해를 테스트합니다.

## 퀴즈 문제

### 1. Kubernetes에서 스케줄러의 주요 역할은 무엇인가요?

A. 파드 생성 및 삭제  
B. 파드를 적절한 노드에 할당  
C. 노드 리소스 모니터링  
D. 컨테이너 이미지 다운로드  

<details>
<summary>정답 및 설명</summary>

**정답: B. 파드를 적절한 노드에 할당**

**설명:**
Kubernetes에서 스케줄러의 주요 역할은 파드를 적절한 노드에 할당하는 것입니다. 스케줄러는 새로 생성된 파드를 감시하고, 아직 노드가 할당되지 않은 파드를 찾아 실행할 최적의 노드를 선택합니다.

**스케줄러의 주요 기능:**
1. **파드-노드 할당**: 파드의 요구 사항과 노드의 가용 리소스를 고려하여 최적의 노드를 선택합니다.
2. **필터링**: 파드를 실행할 수 없는 노드를 제외합니다(예: 리소스 부족, 테인트 등).
3. **스코어링**: 적합한 노드에 점수를 매겨 최적의 노드를 선택합니다.
4. **바인딩**: 선택한 노드에 파드를 바인딩하여 스케줄링 결정을 확정합니다.

**스케줄링 프로세스:**
1. **필터링 단계(Predicates)**: 파드를 실행할 수 없는 노드를 제외합니다.
   - PodFitsResources: 노드에 파드의 리소스 요청을 충족할 수 있는 충분한 리소스가 있는지 확인
   - PodFitsHostPorts: 요청된 호스트 포트가 사용 가능한지 확인
   - PodMatchNodeSelector: 파드의 노드 셀렉터가 노드 레이블과 일치하는지 확인
   - NoVolumeZoneConflict: 볼륨 영역 제약 조건 확인
   - CheckNodeMemoryPressure: 노드의 메모리 압력 상태 확인
   - CheckNodeDiskPressure: 노드의 디스크 압력 상태 확인

2. **스코어링 단계(Priorities)**: 적합한 노드에 점수를 매깁니다.
   - LeastRequestedPriority: 요청된 리소스가 적은 노드에 높은 점수 부여
   - BalancedResourceAllocation: 리소스 사용 균형이 좋은 노드에 높은 점수 부여
   - NodeAffinityPriority: 노드 어피니티 규칙에 따라 점수 부여
   - TaintTolerationPriority: 테인트 톨러레이션에 따라 점수 부여
   - InterPodAffinityPriority: 파드 간 어피니티/안티-어피니티에 따라 점수 부여

3. **바인딩**: 가장 높은 점수를 받은 노드에 파드를 바인딩합니다.

**기본 스케줄러 구성 예시:**
```yaml
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
profiles:
- schedulerName: default-scheduler
  plugins:
    score:
      disabled:
      - name: NodeResourcesLeastAllocated
      enabled:
      - name: NodeResourcesBalancedAllocation
        weight: 1
```

**다른 옵션들의 문제점:**
- A. 파드 생성 및 삭제: 이는 주로 컨트롤러 매니저와 API 서버의 역할입니다.
- C. 노드 리소스 모니터링: 이는 주로 kubelet과 메트릭 서버의 역할입니다.
- D. 컨테이너 이미지 다운로드: 이는 kubelet과 컨테이너 런타임의 역할입니다.
</details>

### 2. 다음 중 Custom Scheduler를 구현하는 방법이 아닌 것은 무엇인가요?

A. 기존 kube-scheduler 확장  
B. 완전히 새로운 스케줄러 구현  
C. 스케줄링 프레임워크 플러그인 개발  
D. kubelet 수정  

<details>
<summary>정답 및 설명</summary>

**정답: D. kubelet 수정**

**설명:**
kubelet 수정은 Custom Scheduler를 구현하는 방법이 아닙니다. kubelet은 각 노드에서 실행되는 에이전트로, 파드의 실행을 관리하지만 스케줄링 결정을 내리지 않습니다. 스케줄링은 kube-scheduler 또는 사용자 정의 스케줄러에 의해 수행됩니다.

**Custom Scheduler 구현 방법:**

1. **기존 kube-scheduler 확장**:
   - KubeSchedulerConfiguration을 사용하여 기본 스케줄러의 동작을 사용자 정의합니다.
   - 플러그인 가중치, 활성화/비활성화 등을 조정합니다.
   
   ```yaml
   apiVersion: kubescheduler.config.k8s.io/v1
   kind: KubeSchedulerConfiguration
   profiles:
   - schedulerName: custom-scheduler
     plugins:
       score:
         disabled:
         - name: NodeResourcesLeastAllocated
         enabled:
         - name: NodeResourcesBalancedAllocation
           weight: 2
   ```

2. **완전히 새로운 스케줄러 구현**:
   - Kubernetes API와 통신하는 독립적인 스케줄러를 개발합니다.
   - 파드 감시, 노드 선택, 바인딩 로직을 직접 구현합니다.
   
   ```go
   // 간단한 Go 스케줄러 예시
   func main() {
       config, err := clientcmd.BuildConfigFromFlags("", os.Getenv("KUBECONFIG"))
       if err != nil {
           log.Fatal(err)
       }
       
       clientset, err := kubernetes.NewForConfig(config)
       if err != nil {
           log.Fatal(err)
       }
       
       // 스케줄링되지 않은 파드 감시
       watchPods(clientset)
   }
   
   func watchPods(clientset *kubernetes.Clientset) {
       watch, err := clientset.CoreV1().Pods("").Watch(context.TODO(), metav1.ListOptions{
           FieldSelector: "spec.schedulerName=custom-scheduler,spec.nodeName=",
       })
       if err != nil {
           log.Fatal(err)
       }
       
       for event := range watch.ResultChan() {
           if event.Type != watch.Added {
               continue
           }
           
           pod := event.Object.(*v1.Pod)
           // 노드 선택 로직 구현
           node := selectNode(clientset, pod)
           if node != "" {
               bindPod(clientset, pod, node)
           }
       }
   }
   ```

3. **스케줄링 프레임워크 플러그인 개발**:
   - Kubernetes 스케줄링 프레임워크를 사용하여 특정 스케줄링 단계에 대한 플러그인을 개발합니다.
   - 필터, 스코어, 바인드 등의 확장 포인트를 구현합니다.
   
   ```go
   // 스코어링 플러그인 예시
   type MyScorePlugin struct{}
   
   func (pl *MyScorePlugin) Name() string {
       return "MyScorePlugin"
   }
   
   func (pl *MyScorePlugin) Score(ctx context.Context, state *framework.CycleState, pod *v1.Pod, nodeName string) (int64, *framework.Status) {
       // 사용자 정의 스코어링 로직 구현
       return score, nil
   }
   
   func (pl *MyScorePlugin) ScoreExtensions() framework.ScoreExtensions {
       return pl
   }
   
   func (pl *MyScorePlugin) NormalizeScore(ctx context.Context, state *framework.CycleState, pod *v1.Pod, scores framework.NodeScoreList) *framework.Status {
       // 점수 정규화 로직 구현
       return nil
   }
   ```

**kubelet의 역할:**
kubelet은 각 노드에서 실행되는 에이전트로, 다음과 같은 역할을 수행합니다:
- 파드 스펙에 따라 컨테이너 실행 및 관리
- 노드 상태 모니터링 및 보고
- 컨테이너 헬스 체크 수행
- 볼륨 마운트 관리

kubelet은 스케줄러가 내린 결정(어떤 파드를 어떤 노드에서 실행할지)을 수행하는 역할을 하며, 스케줄링 결정 자체를 내리지 않습니다.

**다른 옵션들의 설명:**
- A. 기존 kube-scheduler 확장: 유효한 Custom Scheduler 구현 방법입니다.
- B. 완전히 새로운 스케줄러 구현: 유효한 Custom Scheduler 구현 방법입니다.
- C. 스케줄링 프레임워크 플러그인 개발: 유효한 Custom Scheduler 구현 방법입니다.
</details>

### 3. 파드에서 특정 스케줄러를 사용하도록 지정하는 필드는 무엇인가요?

A. spec.scheduler  
B. spec.schedulerName  
C. metadata.scheduler  
D. spec.nodeName  

<details>
<summary>정답 및 설명</summary>

**정답: B. spec.schedulerName**

**설명:**
파드에서 특정 스케줄러를 사용하도록 지정하는 필드는 `spec.schedulerName`입니다. 이 필드를 설정하면 파드는 지정된 이름의 스케줄러에 의해서만 스케줄링됩니다. 기본값은 "default-scheduler"입니다.

**파드 스펙 예시:**
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: custom-scheduled-pod
  labels:
    app: my-app
spec:
  schedulerName: my-custom-scheduler  # 사용자 정의 스케줄러 지정
  containers:
  - name: main-container
    image: nginx:1.19
    resources:
      requests:
        memory: "64Mi"
        cpu: "250m"
      limits:
        memory: "128Mi"
        cpu: "500m"
```

이 파드는 "my-custom-scheduler"라는 이름의 스케줄러에 의해서만 스케줄링됩니다. 해당 이름의 스케줄러가 클러스터에 존재하지 않으면, 파드는 `Pending` 상태로 남게 됩니다.

**여러 스케줄러 배포 예시:**
```yaml
# 사용자 정의 스케줄러 배포
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-custom-scheduler
  namespace: kube-system
spec:
  replicas: 1
  selector:
    matchLabels:
      component: my-custom-scheduler
  template:
    metadata:
      labels:
        component: my-custom-scheduler
    spec:
      serviceAccountName: my-custom-scheduler
      containers:
      - name: scheduler
        image: my-custom-scheduler:v1.0
        args:
        - --scheduler-name=my-custom-scheduler
        - --leader-elect=false
```

**스케줄러 선택 시 고려 사항:**
1. **가용성**: 지정한 스케줄러가 실행 중이 아니면 파드는 스케줄링되지 않습니다.
2. **기능**: 각 스케줄러는 서로 다른 스케줄링 알고리즘과 정책을 가질 수 있습니다.
3. **리소스 분리**: 다른 스케줄러를 사용하여 워크로드를 분리할 수 있습니다.
4. **특수 하드웨어**: GPU나 FPGA와 같은 특수 하드웨어를 위한 전용 스케줄러를 사용할 수 있습니다.

**스케줄러 상태 확인:**
```bash
# 파드 상태 확인
kubectl get pod custom-scheduled-pod

# 스케줄링 이벤트 확인
kubectl describe pod custom-scheduled-pod | grep -A 5 Events

# 스케줄러 로그 확인
kubectl logs -n kube-system -l component=my-custom-scheduler
```

**다른 옵션들의 문제점:**
- A. spec.scheduler: Kubernetes API에 존재하지 않는 필드입니다.
- C. metadata.scheduler: Kubernetes API에 존재하지 않는 필드입니다.
- D. spec.nodeName: 이 필드는 스케줄러를 우회하고 파드를 특정 노드에 직접 할당하는 데 사용됩니다. 스케줄러를 지정하는 필드가 아닙니다.
</details>
### 4. Kubernetes 스케줄링 프레임워크에서 "Filter" 확장 포인트의 역할은 무엇인가요?

A. 노드에 점수 부여  
B. 파드를 노드에 바인딩  
C. 파드를 실행할 수 없는 노드 제외  
D. 스케줄링 큐에서 파드 정렬  

<details>
<summary>정답 및 설명</summary>

**정답: C. 파드를 실행할 수 없는 노드 제외**

**설명:**
Kubernetes 스케줄링 프레임워크에서 "Filter" 확장 포인트(이전에는 "Predicate"라고 불림)의 역할은 파드를 실행할 수 없는 노드를 제외하는 것입니다. 필터 플러그인은 각 노드가 파드의 요구 사항을 충족하는지 확인하고, 충족하지 않는 노드를 후보 목록에서 제외합니다.

**스케줄링 프레임워크 확장 포인트:**
스케줄링 프레임워크는 스케줄링 사이클의 여러 단계에서 플러그인을 통합할 수 있는 다양한 확장 포인트를 제공합니다:

1. **Queue Sort**: 스케줄링 큐에서 파드의 순서를 결정합니다.
2. **PreFilter**: 필터링 전에 파드 및 클러스터 상태에 대한 사전 처리를 수행합니다.
3. **Filter**: 파드를 실행할 수 없는 노드를 제외합니다.
4. **PreScore**: 스코어링 전에 필요한 계산을 수행합니다.
5. **Score**: 필터링을 통과한 노드에 점수를 부여합니다.
6. **NormalizeScore**: 각 스코어링 플러그인의 점수를 정규화합니다.
7. **Reserve**: 선택된 노드에 파드 리소스를 예약합니다.
8. **Permit**: 파드의 스케줄링을 허용, 거부 또는 지연시킵니다.
9. **PreBind**: 바인딩 전에 필요한 작업을 수행합니다.
10. **Bind**: 파드를 노드에 바인딩합니다.
11. **PostBind**: 바인딩 후 정리 작업을 수행합니다.

**기본 필터 플러그인:**
Kubernetes는 다음과 같은 기본 필터 플러그인을 제공합니다:

1. **NodeResourcesFit**: 노드에 파드의 리소스 요청을 충족할 수 있는 충분한 리소스가 있는지 확인합니다.
2. **NodeName**: 파드의 spec.nodeName 필드가 노드 이름과 일치하는지 확인합니다.
3. **NodeUnschedulable**: 노드가 스케줄 불가능으로 표시되었는지 확인합니다.
4. **TaintToleration**: 파드가 노드의 테인트를 허용하는지 확인합니다.
5. **NodeAffinity**: 파드의 노드 어피니티 요구 사항을 충족하는지 확인합니다.
6. **PodAffinity**: 파드의 파드 어피니티 요구 사항을 충족하는지 확인합니다.
7. **VolumeRestrictions**: 볼륨 제약 조건을 확인합니다.
8. **EBSLimits**: Amazon EBS 볼륨 제한을 확인합니다.
9. **NoVolumeZoneConflict**: 볼륨 영역 제약 조건을 확인합니다.
10. **CheckNodeMemoryPressure**: 노드의 메모리 압력 상태를 확인합니다.
11. **CheckNodeDiskPressure**: 노드의 디스크 압력 상태를 확인합니다.

**사용자 정의 필터 플러그인 예시:**
```go
// 사용자 정의 필터 플러그인 예시
type MyFilterPlugin struct{}

func (pl *MyFilterPlugin) Name() string {
    return "MyFilterPlugin"
}

// Filter 메서드 구현
func (pl *MyFilterPlugin) Filter(ctx context.Context, state *framework.CycleState, pod *v1.Pod, nodeInfo *framework.NodeInfo) *framework.Status {
    // 노드가 특정 조건을 충족하는지 확인
    node := nodeInfo.Node()
    if node == nil {
        return framework.NewStatus(framework.Error, "node not found")
    }
    
    // 예: 특정 레이블이 있는 노드만 허용
    if value, exists := node.Labels["custom-label"]; !exists || value != "required-value" {
        return framework.NewStatus(framework.Unschedulable, "node does not have required label")
    }
    
    return nil // nil 반환은 노드가 적합함을 의미
}
```

**스케줄러 구성에서 필터 플러그인 활성화:**
```yaml
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
profiles:
- schedulerName: custom-scheduler
  plugins:
    filter:
      enabled:
      - name: MyFilterPlugin
      disabled:
      - name: NodeResourcesFit  # 기본 플러그인 비활성화
```

**다른 옵션들의 문제점:**
- A. 노드에 점수 부여: 이는 "Score" 확장 포인트의 역할입니다.
- B. 파드를 노드에 바인딩: 이는 "Bind" 확장 포인트의 역할입니다.
- D. 스케줄링 큐에서 파드 정렬: 이는 "Queue Sort" 확장 포인트의 역할입니다.
</details>

### 5. 다음 중 Custom Scheduler 구현 시 고려해야 할 사항이 아닌 것은 무엇인가요?

A. 노드 리소스 사용량  
B. 파드 우선순위 및 선점  
C. 컨테이너 이미지 크기  
D. 노드 어피니티 및 안티-어피니티  

<details>
<summary>정답 및 설명</summary>

**정답: C. 컨테이너 이미지 크기**

**설명:**
컨테이너 이미지 크기는 일반적으로 Custom Scheduler 구현 시 고려하지 않는 요소입니다. 이미지 크기는 스케줄링 결정보다는 이미지 다운로드 및 컨테이너 시작 시간에 영향을 미치며, 이는 kubelet과 컨테이너 런타임의 책임 영역입니다.

**Custom Scheduler 구현 시 주요 고려 사항:**

1. **노드 리소스 사용량**:
   - CPU, 메모리, 디스크, 네트워크 등의 리소스 사용량
   - 현재 사용량과 요청량을 고려한 최적의 배치
   - 리소스 오버커밋 정책

   ```go
   // 리소스 사용량 기반 필터링 예시
   func filterByResourceUsage(pod *v1.Pod, node *v1.Node) bool {
       // 노드의 할당 가능한 리소스 확인
       allocatable := node.Status.Allocatable
       // 노드에서 실행 중인 파드의 리소스 요청 합계 계산
       // 새 파드의 리소스 요청이 가용 리소스를 초과하는지 확인
       return podFitsResources(pod, allocatable, usedResources)
   }
   ```

2. **파드 우선순위 및 선점**:
   - 우선순위가 높은 파드를 먼저 스케줄링
   - 필요한 경우 우선순위가 낮은 파드 선점
   - PriorityClass 및 preemptionPolicy 고려

   ```yaml
   # 우선순위 클래스 예시
   apiVersion: scheduling.k8s.io/v1
   kind: PriorityClass
   metadata:
     name: high-priority
   value: 1000000
   globalDefault: false
   description: "High priority pods"
   ```

3. **노드 어피니티 및 안티-어피니티**:
   - 파드의 nodeSelector, nodeAffinity 요구 사항 충족
   - 파드 간 어피니티 및 안티-어피니티 규칙 적용
   - 토폴로지 분산 제약 조건 고려

   ```yaml
   # 노드 어피니티 예시
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
             - key: kubernetes.io/e2e-az-name
               operator: In
               values:
               - e2e-az1
               - e2e-az2
   ```

4. **기타 중요한 고려 사항**:
   - **테인트 및 톨러레이션**: 노드 테인트와 파드 톨러레이션 매칭
   - **토폴로지 분산**: 파드를 다양한 토폴로지 도메인에 분산
   - **노드 상태**: 노드의 상태(Ready, MemoryPressure, DiskPressure 등)
   - **워크로드 특성**: 배치, 서비스, 데몬셋 등 다양한 워크로드 유형의 요구 사항
   - **네트워크 토폴로지**: 노드 간 네트워크 지연 및 대역폭
   - **하드웨어 특성**: GPU, FPGA 등 특수 하드웨어 요구 사항

**컨테이너 이미지 크기와 관련된 고려 사항:**
컨테이너 이미지 크기는 다음과 같은 이유로 일반적으로 스케줄링 결정에 직접적인 영향을 미치지 않습니다:

1. **이미지 가용성**: 이미지가 노드에 이미 캐시되어 있는지 여부는 스케줄러가 아닌 kubelet이 처리합니다.
2. **다운로드 시간**: 이미지 다운로드는 스케줄링 결정 후에 발생하며, kubelet의 책임입니다.
3. **스토리지 사용량**: 이미지 스토리지는 일반적으로 노드의 할당 가능한 리소스 계산에 포함되지 않습니다.

그러나 특수한 경우에는 이미지 지역성(locality)을 고려하는 사용자 정의 스케줄러를 구현할 수 있습니다. 이는 이미지가 이미 캐시된 노드를 선호하여 시작 시간을 단축하는 데 도움이 될 수 있습니다.

**다른 옵션들의 설명:**
- A. 노드 리소스 사용량: 스케줄링 결정에 중요한 요소로, 파드의 리소스 요청을 충족할 수 있는 노드를 선택하는 데 필수적입니다.
- B. 파드 우선순위 및 선점: 리소스 경합 시 어떤 파드를 먼저 스케줄링할지, 필요한 경우 어떤 파드를 선점할지 결정하는 데 중요합니다.
- D. 노드 어피니티 및 안티-어피니티: 파드가 특정 노드 또는 다른 파드와 함께 또는 떨어져 스케줄링되어야 하는 제약 조건을 처리하는 데 중요합니다.
</details>
### 6. Kubernetes 스케줄링 프레임워크에서 "Score" 확장 포인트의 역할은 무엇인가요?

A. 파드를 실행할 수 없는 노드 제외  
B. 필터링을 통과한 노드에 점수 부여  
C. 파드를 노드에 바인딩  
D. 스케줄링 큐에서 파드 정렬  

<details>
<summary>정답 및 설명</summary>

**정답: B. 필터링을 통과한 노드에 점수 부여**

**설명:**
Kubernetes 스케줄링 프레임워크에서 "Score" 확장 포인트(이전에는 "Priority"라고 불림)의 역할은 필터링을 통과한 노드에 점수를 부여하는 것입니다. 스코어링 플러그인은 각 노드에 점수를 할당하고, 이 점수를 기반으로 최적의 노드가 선택됩니다.

**스코어링 프로세스:**
1. 각 스코어링 플러그인은 노드별로 점수를 계산합니다(일반적으로 0-100 범위).
2. 각 플러그인의 점수는 구성된 가중치에 따라 가중치가 부여됩니다.
3. 모든 플러그인의 가중치가 적용된 점수가 합산됩니다.
4. 가장 높은 총점을 받은 노드가 파드 배치를 위해 선택됩니다.

**기본 스코어링 플러그인:**
Kubernetes는 다음과 같은 기본 스코어링 플러그인을 제공합니다:

1. **NodeResourcesBalancedAllocation**: CPU와 메모리 사용의 균형이 잘 잡힌 노드에 높은 점수를 부여합니다.
2. **NodeResourcesFit**: 요청된 리소스에 비해 가용 리소스가 많은 노드에 높은 점수를 부여합니다.
3. **NodeAffinity**: 노드 어피니티 규칙에 따라 점수를 부여합니다.
4. **InterPodAffinity**: 파드 간 어피니티/안티-어피니티 규칙에 따라 점수를 부여합니다.
5. **PodTopologySpread**: 토폴로지 도메인 전체에 파드를 균등하게 분산시키는 노드에 높은 점수를 부여합니다.
6. **TaintToleration**: 테인트가 적은 노드에 높은 점수를 부여합니다.
7. **ImageLocality**: 필요한 컨테이너 이미지가 이미 있는 노드에 높은 점수를 부여합니다.

**사용자 정의 스코어링 플러그인 예시:**
```go
// 사용자 정의 스코어링 플러그인 예시
type MyScorePlugin struct{}

func (pl *MyScorePlugin) Name() string {
    return "MyScorePlugin"
}

// Score 메서드 구현
func (pl *MyScorePlugin) Score(ctx context.Context, state *framework.CycleState, pod *v1.Pod, nodeName string) (int64, *framework.Status) {
    // 노드 정보 가져오기
    nodeInfo, err := pl.handle.SnapshotSharedLister().NodeInfos().Get(nodeName)
    if err != nil {
        return 0, framework.NewStatus(framework.Error, fmt.Sprintf("getting node %q from Snapshot: %v", nodeName, err))
    }
    
    node := nodeInfo.Node()
    
    // 예: 특정 레이블 값에 따라 점수 부여
    if value, exists := node.Labels["custom-score-label"]; exists {
        score, err := strconv.ParseInt(value, 10, 64)
        if err != nil {
            return 0, framework.NewStatus(framework.Error, fmt.Sprintf("invalid score value: %v", err))
        }
        // 점수 범위는 0-100이어야 함
        if score < 0 {
            score = 0
        } else if score > 100 {
            score = 100
        }
        return score, nil
    }
    
    return 0, nil
}

// ScoreExtensions 인터페이스 구현
func (pl *MyScorePlugin) ScoreExtensions() framework.ScoreExtensions {
    return pl
}

// NormalizeScore 메서드 구현
func (pl *MyScorePlugin) NormalizeScore(ctx context.Context, state *framework.CycleState, pod *v1.Pod, scores framework.NodeScoreList) *framework.Status {
    // 점수 정규화 로직
    var highest int64 = 0
    for _, nodeScore := range scores {
        if nodeScore.Score > highest {
            highest = nodeScore.Score
        }
    }
    
    if highest == 0 {
        return nil
    }
    
    // 모든 점수를 최고 점수에 대한 비율로 조정
    for i := range scores {
        scores[i].Score = scores[i].Score * 100 / highest
    }
    
    return nil
}
```

**스케줄러 구성에서 스코어링 플러그인 활성화 및 가중치 설정:**
```yaml
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
profiles:
- schedulerName: custom-scheduler
  plugins:
    score:
      enabled:
      - name: MyScorePlugin
        weight: 5  # 가중치 설정
      - name: NodeResourcesBalancedAllocation
        weight: 2  # 기본 플러그인 가중치 변경
      disabled:
      - name: NodeResourcesFit  # 기본 플러그인 비활성화
```

**스코어링 결과 예시:**
노드 A, B, C가 필터링을 통과했고, 두 개의 스코어링 플러그인이 있다고 가정합니다:

1. MyScorePlugin (가중치: 5)
   - 노드 A: 80점
   - 노드 B: 60점
   - 노드 C: 90점

2. NodeResourcesBalancedAllocation (가중치: 2)
   - 노드 A: 70점
   - 노드 B: 90점
   - 노드 C: 50점

가중치가 적용된 총점:
- 노드 A: (80 × 5) + (70 × 2) = 400 + 140 = 540점
- 노드 B: (60 × 5) + (90 × 2) = 300 + 180 = 480점
- 노드 C: (90 × 5) + (50 × 2) = 450 + 100 = 550점

이 경우, 노드 C가 가장 높은 점수를 받았으므로 파드는 노드 C에 스케줄링됩니다.

**다른 옵션들의 문제점:**
- A. 파드를 실행할 수 없는 노드 제외: 이는 "Filter" 확장 포인트의 역할입니다.
- C. 파드를 노드에 바인딩: 이는 "Bind" 확장 포인트의 역할입니다.
- D. 스케줄링 큐에서 파드 정렬: 이는 "Queue Sort" 확장 포인트의 역할입니다.
</details>

### 7. 다음 중 Kubernetes에서 스케줄러 확장을 위한 방법이 아닌 것은 무엇인가요?

A. 스케줄링 프레임워크 플러그인  
B. 스케줄러 익스텐더  
C. 다중 스케줄러 배포  
D. 노드 컨트롤러 수정  

<details>
<summary>정답 및 설명</summary>

**정답: D. 노드 컨트롤러 수정**

**설명:**
노드 컨트롤러 수정은 Kubernetes에서 스케줄러 확장을 위한 방법이 아닙니다. 노드 컨트롤러는 노드의 상태를 모니터링하고 관리하는 컨트롤 플레인 구성 요소로, 스케줄링 결정과는 직접적인 관련이 없습니다.

**Kubernetes에서 스케줄러 확장을 위한 방법:**

1. **스케줄링 프레임워크 플러그인**:
   - Kubernetes 1.15부터 도입된 방법으로, 스케줄링 사이클의 다양한 단계에 플러그인을 삽입할 수 있습니다.
   - 필터, 스코어, 바인드 등의 확장 포인트를 제공합니다.
   - 스케줄러 코드베이스와 직접 통합되어 효율적입니다.

   ```go
   // 스케줄링 프레임워크 플러그인 등록 예시
   func NewPlugin(args runtime.Object, handle framework.Handle) (framework.Plugin, error) {
       // 플러그인 구성 파싱
       config, ok := args.(*Config)
       if !ok {
           return nil, fmt.Errorf("want args to be of type Config, got %T", args)
       }
       
       // 플러그인 인스턴스 생성
       return &Plugin{
           handle: handle,
           config: config,
       }, nil
   }
   
   // 플러그인 인터페이스 구현
   type Plugin struct {
       handle framework.Handle
       config *Config
   }
   
   func (pl *Plugin) Name() string { return "MyPlugin" }
   
   // 필요한 확장 포인트 메서드 구현
   func (pl *Plugin) Filter(...) { ... }
   func (pl *Plugin) Score(...) { ... }
   ```

2. **스케줄러 익스텐더**:
   - 외부 HTTP 서비스를 통해 스케줄러의 기능을 확장합니다.
   - 필터링, 우선순위 지정, 바인딩 등의 단계를 확장할 수 있습니다.
   - 스케줄러와 별도로 실행되므로 성능 오버헤드가 있을 수 있습니다.

   ```yaml
   # 스케줄러 익스텐더 구성 예시
   apiVersion: kubescheduler.config.k8s.io/v1
   kind: KubeSchedulerConfiguration
   profiles:
   - schedulerName: default-scheduler
     extenders:
     - urlPrefix: "http://extender-service:8080"
       filterVerb: "filter"
       prioritizeVerb: "prioritize"
       weight: 5
       bindVerb: "bind"
       enableHTTPS: false
   ```

3. **다중 스케줄러 배포**:
   - 기본 스케줄러와 함께 사용자 정의 스케줄러를 배포합니다.
   - 각 스케줄러는 독립적으로 작동하며, 파드는 `spec.schedulerName`을 통해 특정 스케줄러를 지정할 수 있습니다.
   - 완전한 유연성을 제공하지만, 구현 및 유지 관리가 복잡할 수 있습니다.

   ```yaml
   # 사용자 정의 스케줄러 배포 예시
   apiVersion: apps/v1
   kind: Deployment
   metadata:
     name: my-custom-scheduler
     namespace: kube-system
   spec:
     replicas: 1
     selector:
       matchLabels:
         component: my-custom-scheduler
     template:
       metadata:
         labels:
           component: my-custom-scheduler
       spec:
         serviceAccountName: my-custom-scheduler
         containers:
         - name: scheduler
           image: my-custom-scheduler:v1.0
           args:
           - --scheduler-name=my-custom-scheduler
           - --leader-elect=false
   ```

**노드 컨트롤러의 역할:**
노드 컨트롤러는 다음과 같은 역할을 수행하는 컨트롤 플레인 구성 요소입니다:
- 노드 등록 및 상태 모니터링
- 노드 상태 업데이트(Ready, NotReady 등)
- 노드 상태에 따른 파드 제거(노드가 장시간 NotReady 상태인 경우)
- 노드 수명 주기 관리

노드 컨트롤러는 스케줄링 결정에 직접 관여하지 않으며, 스케줄러가 사용하는 노드 정보를 업데이트하는 역할을 합니다. 따라서 노드 컨트롤러를 수정하는 것은 스케줄러 확장 방법이 아닙니다.

**스케줄러 확장 방법 선택 시 고려 사항:**
1. **복잡성**: 스케줄링 프레임워크 플러그인은 구현이 복잡할 수 있지만, 스케줄러와 긴밀하게 통합됩니다.
2. **성능**: 스케줄러 익스텐더는 HTTP 호출 오버헤드가 있어 성능에 영향을 줄 수 있습니다.
3. **유지 관리**: 다중 스케줄러는 별도의 코드베이스를 유지 관리해야 합니다.
4. **업그레이드**: Kubernetes 업그레이드 시 호환성 문제가 발생할 수 있습니다.
5. **기능**: 각 방법은 서로 다른 수준의 기능과 유연성을 제공합니다.

**다른 옵션들의 설명:**
- A. 스케줄링 프레임워크 플러그인: 유효한 스케줄러 확장 방법입니다.
- B. 스케줄러 익스텐더: 유효한 스케줄러 확장 방법입니다.
- C. 다중 스케줄러 배포: 유효한 스케줄러 확장 방법입니다.
</details>
### 8. 다음 중 Kubernetes 스케줄러의 `--leader-elect` 플래그의 목적은 무엇인가요?

A. 스케줄러에 리더십 권한 부여  
B. 여러 스케줄러 인스턴스 중 하나만 활성화  
C. 스케줄러를 클러스터의 리더 노드에서만 실행  
D. 스케줄러에 다른 컴포넌트보다 높은 우선순위 부여  

<details>
<summary>정답 및 설명</summary>

**정답: B. 여러 스케줄러 인스턴스 중 하나만 활성화**

**설명:**
Kubernetes 스케줄러의 `--leader-elect` 플래그는 고가용성(HA) 구성에서 여러 스케줄러 인스턴스 중 하나만 활성화하여 작업을 수행하도록 하는 목적을 가집니다. 이는 여러 스케줄러 인스턴스가 동시에 작동하여 발생할 수 있는 충돌과 경쟁 상태를 방지합니다.

**리더 선출 메커니즘:**
1. 여러 스케줄러 인스턴스가 배포되면, 리더 선출 알고리즘을 통해 하나의 인스턴스만 리더로 선출됩니다.
2. 리더로 선출된 인스턴스만 실제 스케줄링 작업을 수행합니다.
3. 다른 인스턴스는 대기 상태로 유지되며, 현재 리더가 실패하면 새로운 리더가 선출됩니다.
4. 이 메커니즘은 Kubernetes의 리소스 잠금(resource lock)을 사용하여 구현됩니다.

**리더 선출 관련 플래그:**
```
--leader-elect=true                      # 리더 선출 활성화 여부 (기본값: true)
--leader-elect-lease-duration=15s        # 리더십 임대 기간
--leader-elect-renew-deadline=10s        # 리더십 갱신 기한
--leader-elect-retry-period=2s           # 리더십 재시도 주기
--leader-elect-resource-lock=leases      # 리더십 잠금에 사용할 리소스 유형
--leader-elect-resource-name=kube-scheduler  # 리더십 잠금 리소스 이름
--leader-elect-resource-namespace=kube-system  # 리더십 잠금 리소스 네임스페이스
```

**고가용성 스케줄러 배포 예시:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: kube-scheduler
  namespace: kube-system
spec:
  replicas: 3  # 여러 인스턴스 배포
  selector:
    matchLabels:
      component: kube-scheduler
  template:
    metadata:
      labels:
        component: kube-scheduler
    spec:
      containers:
      - name: kube-scheduler
        image: k8s.gcr.io/kube-scheduler:v1.23.0
        command:
        - kube-scheduler
        - --leader-elect=true  # 리더 선출 활성화
        - --leader-elect-lease-duration=15s
        - --leader-elect-renew-deadline=10s
        - --leader-elect-retry-period=2s
```

**리더 선출 상태 확인:**
```bash
# 리더십 리소스 확인
kubectl get leases -n kube-system | grep kube-scheduler

# 리더십 세부 정보 확인
kubectl describe lease kube-scheduler -n kube-system

# 스케줄러 로그에서 리더십 관련 메시지 확인
kubectl logs -n kube-system -l component=kube-scheduler | grep -i leader
```

**사용자 정의 스케줄러에서의 리더 선출:**
사용자 정의 스케줄러를 구현할 때도 동일한 리더 선출 메커니즘을 사용할 수 있습니다. 이를 위해 client-go 라이브러리의 leaderelection 패키지를 활용합니다.

```go
// 사용자 정의 스케줄러에서 리더 선출 구현 예시
import (
    "context"
    "time"
    
    metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
    clientset "k8s.io/client-go/kubernetes"
    "k8s.io/client-go/tools/leaderelection"
    "k8s.io/client-go/tools/leaderelection/resourcelock"
)

func runWithLeaderElection(ctx context.Context, client clientset.Interface, schedulerName string) {
    // 리더 선출 구성
    lock := &resourcelock.LeaseLock{
        LeaseMeta: metav1.ObjectMeta{
            Name:      schedulerName,
            Namespace: "kube-system",
        },
        Client: client.CoordinationV1(),
        LockConfig: resourcelock.ResourceLockConfig{
            Identity: schedulerName + "-" + uuid.New().String(),
        },
    }
    
    // 리더 선출 실행
    leaderelection.RunOrDie(ctx, leaderelection.LeaderElectionConfig{
        Lock:            lock,
        ReleaseOnCancel: true,
        LeaseDuration:   15 * time.Second,
        RenewDeadline:   10 * time.Second,
        RetryPeriod:     2 * time.Second,
        Callbacks: leaderelection.LeaderCallbacks{
            OnStartedLeading: func(ctx context.Context) {
                // 리더가 되었을 때 스케줄러 로직 실행
                runScheduler(ctx)
            },
            OnStoppedLeading: func() {
                // 리더십을 잃었을 때 처리
                log.Printf("Lost leadership, shutting down")
                os.Exit(0)
            },
            OnNewLeader: func(identity string) {
                // 새로운 리더가 선출되었을 때 처리
                log.Printf("New leader elected: %s", identity)
            },
        },
    })
}
```

**리더 선출을 비활성화해야 하는 경우:**
1. **단일 인스턴스 배포**: 스케줄러가 하나의 인스턴스로만 배포되는 경우
2. **다른 리더 선출 메커니즘 사용**: 외부 오케스트레이션 도구가 인스턴스 활성화를 관리하는 경우
3. **서로 다른 스케줄러 이름**: 각 스케줄러 인스턴스가 다른 `schedulerName`을 사용하는 경우

이러한 경우에는 `--leader-elect=false`로 설정하여 리더 선출을 비활성화할 수 있습니다.

**다른 옵션들의 문제점:**
- A. 스케줄러에 리더십 권한 부여: 이는 모호한 설명으로, 리더 선출의 구체적인 목적을 설명하지 않습니다.
- C. 스케줄러를 클러스터의 리더 노드에서만 실행: Kubernetes에는 "리더 노드"라는 개념이 없으며, 스케줄러는 컨트롤 플레인 노드에서 실행됩니다.
- D. 스케줄러에 다른 컴포넌트보다 높은 우선순위 부여: 리더 선출은 우선순위와 관련이 없으며, 여러 스케줄러 인스턴스 간의 조정을 위한 것입니다.
</details>

### 9. 다음 중 Kubernetes에서 파드의 스케줄링 우선순위를 설정하는 데 사용되는 리소스는 무엇인가요?

A. PodSchedulingPolicy  
B. PriorityClass  
C. SchedulingPriority  
D. PodPriority  

<details>
<summary>정답 및 설명</summary>

**정답: B. PriorityClass**

**설명:**
Kubernetes에서 파드의 스케줄링 우선순위를 설정하는 데 사용되는 리소스는 `PriorityClass`입니다. PriorityClass는 파드의 상대적 중요도를 정의하고, 이를 통해 스케줄러가 스케줄링 결정과 선점(preemption) 결정을 내릴 때 우선순위를 고려할 수 있습니다.

**PriorityClass 리소스:**
```yaml
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: high-priority
value: 1000000  # 우선순위 값 (높을수록 우선순위가 높음)
globalDefault: false  # 이 클래스를 기본값으로 사용할지 여부
description: "High priority pods"  # 설명
preemptionPolicy: PreemptLowerPriority  # 선점 정책 (기본값: PreemptLowerPriority)
```

**주요 필드:**
1. **value**: 우선순위 값으로, 높을수록 우선순위가 높습니다. 시스템 파드는 일반적으로 1000000000(10억) 이상의 값을 사용합니다.
2. **globalDefault**: true로 설정하면, 우선순위 클래스를 지정하지 않은 파드에 이 우선순위 클래스가 적용됩니다.
3. **description**: 우선순위 클래스에 대한 설명입니다.
4. **preemptionPolicy**: 선점 정책으로, `PreemptLowerPriority`(기본값) 또는 `Never`로 설정할 수 있습니다.

**파드에 PriorityClass 적용:**
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: high-priority-pod
spec:
  priorityClassName: high-priority  # PriorityClass 이름 참조
  containers:
  - name: nginx
    image: nginx
```

**우선순위 및 선점 동작:**
1. **스케줄링 우선순위**: 우선순위가 높은 파드는 스케줄링 큐에서 우선적으로 처리됩니다.
2. **선점(Preemption)**: 우선순위가 높은 파드가 스케줄링될 노드가 없는 경우, 스케줄러는 우선순위가 낮은 파드를 제거(선점)하여 공간을 확보할 수 있습니다.
3. **선점 정책**: `preemptionPolicy: Never`로 설정된 PriorityClass를 사용하는 파드는 다른 파드를 선점하지 않습니다.

**시스템 PriorityClass:**
Kubernetes는 다음과 같은 시스템 PriorityClass를 제공합니다:
- **system-cluster-critical**: 클러스터 운영에 중요한 파드(value: 2000000000)
- **system-node-critical**: 노드 운영에 중요한 파드(value: 2000001000)

```bash
# 시스템 PriorityClass 확인
kubectl get priorityclasses | grep system
```

**PriorityClass 사용 예시:**
```yaml
# 여러 우선순위 클래스 정의
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
globalDefault: true
description: "Medium priority pods"
---
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: low-priority
value: 10000
globalDefault: false
description: "Low priority pods"
preemptionPolicy: Never  # 선점하지 않음
```

**우선순위 및 선점 관련 지표 모니터링:**
```bash
# 선점 이벤트 확인
kubectl get events | grep -i preempt

# 파드 우선순위 확인
kubectl get pods -o custom-columns=NAME:.metadata.name,PRIORITY:.spec.priority
```

**Custom Scheduler에서 우선순위 처리:**
사용자 정의 스케줄러를 구현할 때는 파드의 우선순위를 고려하여 스케줄링 결정을 내려야 합니다.

```go
// 파드 우선순위 확인 예시
func getPodPriority(pod *v1.Pod) int32 {
    if pod.Spec.Priority != nil {
        return *pod.Spec.Priority
    }
    return 0
}

// 우선순위 기반 파드 정렬 예시
func sortPodsByPriority(pods []*v1.Pod) {
    sort.Slice(pods, func(i, j int) bool {
        return getPodPriority(pods[i]) > getPodPriority(pods[j])
    })
}
```

**다른 옵션들의 문제점:**
- A. PodSchedulingPolicy: Kubernetes API에 존재하지 않는 리소스입니다.
- C. SchedulingPriority: Kubernetes API에 존재하지 않는 리소스입니다.
- D. PodPriority: 이는 리소스 유형이 아니라 파드 스펙의 필드(`spec.priority`)입니다. 이 필드는 PriorityClass에 의해 자동으로 설정됩니다.
</details>

### 10. 다음 중 Kubernetes 스케줄러의 `NodeResourcesFit` 플러그인의 역할은 무엇인가요?

A. 노드의 물리적 위치에 따라 파드 배치  
B. 노드의 리소스 용량과 파드의 리소스 요청 비교  
C. 노드의 운영체제와 파드의 호환성 확인  
D. 노드의 네트워크 대역폭 측정  

<details>
<summary>정답 및 설명</summary>

**정답: B. 노드의 리소스 용량과 파드의 리소스 요청 비교**

**설명:**
Kubernetes 스케줄러의 `NodeResourcesFit` 플러그인은 노드의 리소스 용량과 파드의 리소스 요청을 비교하여, 파드가 노드에서 실행될 수 있는지 확인하는 역할을 합니다. 이 플러그인은 CPU, 메모리, 임시 스토리지, 확장 리소스(GPU 등) 등 다양한 리소스 유형을 고려합니다.

**NodeResourcesFit 플러그인의 주요 기능:**
1. **리소스 요청 검증**: 파드의 리소스 요청이 노드의 할당 가능한 리소스를 초과하지 않는지 확인합니다.
2. **리소스 제한 검증**: 파드의 리소스 제한이 노드의 용량을 초과하지 않는지 확인합니다.
3. **확장 리소스 검증**: GPU, FPGA 등의 확장 리소스 요청이 노드에서 사용 가능한지 확인합니다.
4. **스코어링**: 필터링 단계를 통과한 노드에 대해 리소스 사용량에 따라 점수를 부여합니다.

**리소스 검증 프로세스:**
1. 파드의 모든 컨테이너의 리소스 요청을 합산합니다.
2. 노드의 할당 가능한 리소스를 확인합니다.
3. 파드의 리소스 요청이 노드의 할당 가능한 리소스를 초과하지 않는지 확인합니다.
4. 초과하는 경우, 해당 노드는 필터링됩니다.

**스케줄러 구성에서 NodeResourcesFit 설정:**
```yaml
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
profiles:
- schedulerName: default-scheduler
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
        type: MostAllocated  # 또는 LeastAllocated, RequestedToCapacityRatio
        resources:
        - name: cpu
          weight: 1
        - name: memory
          weight: 1
```

**스코어링 전략:**
NodeResourcesFit 플러그인은 다음과 같은 스코어링 전략을 지원합니다:

1. **LeastAllocated**: 사용 중인 리소스가 적은 노드에 높은 점수를 부여합니다. 이는 리소스 사용을 분산시키는 데 유용합니다.
   ```
   score = (capacity - requested) / capacity
   ```

2. **MostAllocated**: 사용 중인 리소스가 많은 노드에 높은 점수를 부여합니다. 이는 리소스 사용을 집중시켜 노드 수를 최소화하는 데 유용합니다.
   ```
   score = requested / capacity
   ```

3. **RequestedToCapacityRatio**: 사용자 정의 함수를 사용하여 요청된 리소스와 용량의 비율에 따라 점수를 부여합니다.

**리소스 유형:**
NodeResourcesFit 플러그인은 다음과 같은 리소스 유형을 고려합니다:

1. **CPU**: 코어 수 또는 밀리코어 단위로 측정됩니다.
2. **메모리**: 바이트 단위로 측정됩니다.
3. **임시 스토리지**: 노드의 로컬 임시 스토리지입니다.
4. **확장 리소스**: GPU, FPGA 등의 사용자 정의 리소스입니다.

**노드 리소스 확인:**
```bash
# 노드의 할당 가능한 리소스 확인
kubectl describe node <node-name> | grep Allocatable -A 5

# 노드의 리소스 사용량 확인
kubectl top node <node-name>
```

**파드 리소스 요청 확인:**
```bash
# 파드의 리소스 요청 확인
kubectl get pod <pod-name> -o jsonpath='{.spec.containers[*].resources.requests}'
```

**Custom Scheduler에서 리소스 적합성 검사 구현:**
```go
// 노드 리소스 적합성 검사 예시
func checkNodeResourcesFit(pod *v1.Pod, node *v1.Node) bool {
    // 노드의 할당 가능한 리소스 가져오기
    allocatable := node.Status.Allocatable
    
    // 파드의 리소스 요청 계산
    var requestedCPU, requestedMemory resource.Quantity
    for _, container := range pod.Spec.Containers {
        if request, ok := container.Resources.Requests[v1.ResourceCPU]; ok {
            requestedCPU.Add(request)
        }
        if request, ok := container.Resources.Requests[v1.ResourceMemory]; ok {
            requestedMemory.Add(request)
        }
    }
    
    // 노드에서 이미 사용 중인 리소스 계산
    // (실제 구현에서는 노드에서 실행 중인 모든 파드의 리소스 요청을 합산해야 함)
    
    // 리소스 적합성 확인
    if allocatableCPU, ok := allocatable[v1.ResourceCPU]; ok {
        if requestedCPU.Cmp(allocatableCPU) > 0 {
            return false  // CPU 요청이 할당 가능한 양을 초과
        }
    }
    
    if allocatableMemory, ok := allocatable[v1.ResourceMemory]; ok {
        if requestedMemory.Cmp(allocatableMemory) > 0 {
            return false  // 메모리 요청이 할당 가능한 양을 초과
        }
    }
    
    return true  // 모든 리소스 요청이 충족됨
}
```

**다른 옵션들의 문제점:**
- A. 노드의 물리적 위치에 따라 파드 배치: 이는 토폴로지 관련 플러그인(예: NodeAffinity, PodTopologySpread)의 역할입니다.
- C. 노드의 운영체제와 파드의 호환성 확인: 이는 NodeSelector 또는 NodeAffinity를 통해 처리되며, 별도의 플러그인이 아닙니다.
- D. 노드의 네트워크 대역폭 측정: Kubernetes 스케줄러는 기본적으로 네트워크 대역폭을 고려하지 않습니다. 이를 위해서는 사용자 정의 메트릭과 플러그인이 필요합니다.
</details>
