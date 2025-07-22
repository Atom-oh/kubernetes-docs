# Custom Scheduler 퀴즈 (Part 3)

이 퀴즈는 Kubernetes에서 Custom Scheduler를 구현하고 사용하는 방법에 대한 고급 이해를 테스트합니다.

## 퀴즈 문제

### 1. Kubernetes에서 여러 스케줄러를 동시에 실행할 때 발생할 수 있는 문제가 아닌 것은 무엇인가요?

A. 리소스 경합  
B. 스케줄링 결정 충돌  
C. 네트워크 대역폭 증가  
D. 리더 선출 충돌  

<details>
<summary>정답 및 설명</summary>

**정답: C. 네트워크 대역폭 증가**

**설명:**
Kubernetes에서 여러 스케줄러를 동시에 실행할 때 발생할 수 있는 문제가 아닌 것은 "네트워크 대역폭 증가"입니다. 스케줄러는 API 서버와 통신하지만, 이로 인한 네트워크 대역폭 사용량은 일반적으로 미미하며 문제가 되지 않습니다.

**여러 스케줄러 실행 시 발생할 수 있는 실제 문제:**

1. **리소스 경합**:
   - 여러 스케줄러가 동일한 노드 풀에 파드를 스케줄링하려고 할 때 리소스 경합이 발생할 수 있습니다.
   - 각 스케줄러는 다른 스케줄러의 결정을 인식하지 못하고 독립적으로 작동하므로, 노드 리소스를 과도하게 할당할 위험이 있습니다.
   - 예: 두 스케줄러가 동시에 같은 노드에 파드를 스케줄링하여 노드 용량을 초과할 수 있습니다.

2. **스케줄링 결정 충돌**:
   - 여러 스케줄러가 동일한 파드를 스케줄링하려고 시도하면 충돌이 발생할 수 있습니다.
   - 이는 파드가 `schedulerName`을 명시적으로 지정하지 않거나, 여러 스케줄러가 동일한 이름을 사용할 때 발생할 수 있습니다.
   - 예: 두 스케줄러가 동일한 파드를 서로 다른 노드에 바인딩하려고 시도하면 경쟁 상태가 발생합니다.

3. **리더 선출 충돌**:
   - 동일한 이름의 여러 스케줄러 인스턴스가 실행 중이고 리더 선출이 활성화된 경우, 리더 선출 메커니즘에서 충돌이 발생할 수 있습니다.
   - 예: 동일한 이름의 여러 스케줄러 인스턴스가 리더십을 획득하려고 경쟁하면 불안정한 리더십 전환이 발생할 수 있습니다.

**여러 스케줄러 실행 시 모범 사례:**

1. **명확한 책임 분리**:
   ```yaml
   # 기본 스케줄러용 파드
   apiVersion: v1
   kind: Pod
   metadata:
     name: default-pod
   spec:
     # schedulerName을 지정하지 않으면 기본 스케줄러 사용
     containers:
     - name: nginx
       image: nginx
   
   # 사용자 정의 스케줄러용 파드
   apiVersion: v1
   kind: Pod
   metadata:
     name: custom-pod
   spec:
     schedulerName: my-custom-scheduler  # 사용자 정의 스케줄러 지정
     containers:
     - name: nginx
       image: nginx
   ```

2. **고유한 스케줄러 이름 사용**:
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
         containers:
         - name: scheduler
           image: my-custom-scheduler:v1.0
           args:
           - --scheduler-name=my-custom-scheduler  # 고유한 이름 사용
           - --leader-elect=true
           - --leader-elect-resource-name=my-custom-scheduler  # 고유한 리소스 이름 사용
   ```

3. **노드 레이블 및 테인트를 사용한 노드 풀 분리**:
   ```yaml
   # 노드 레이블 및 테인트 적용
   kubectl label node node1 scheduler=default
   kubectl label node node2 scheduler=custom
   
   kubectl taint nodes node2 dedicated=custom-scheduler:NoSchedule
   
   # 사용자 정의 스케줄러 구성
   apiVersion: kubescheduler.config.k8s.io/v1
   kind: KubeSchedulerConfiguration
   profiles:
   - schedulerName: my-custom-scheduler
     plugins:
       filter:
         enabled:
         - name: NodeSelector
     pluginConfig:
     - name: NodeSelector
       args:
         nodeSelector:
           scheduler: custom
   ```

4. **리소스 할당량 설정**:
   ```yaml
   apiVersion: v1
   kind: ResourceQuota
   metadata:
     name: default-scheduler-quota
     namespace: default-workloads
   spec:
     hard:
       pods: "10"
       cpu: "20"
       memory: 40Gi
   
   ---
   apiVersion: v1
   kind: ResourceQuota
   metadata:
     name: custom-scheduler-quota
     namespace: custom-workloads
   spec:
     hard:
       pods: "10"
       cpu: "20"
       memory: 40Gi
   ```

**여러 스케줄러 모니터링:**
```bash
# 스케줄러 파드 확인
kubectl get pods -n kube-system -l component=kube-scheduler
kubectl get pods -n kube-system -l component=my-custom-scheduler

# 스케줄러 로그 확인
kubectl logs -n kube-system -l component=kube-scheduler
kubectl logs -n kube-system -l component=my-custom-scheduler

# 스케줄링 이벤트 확인
kubectl get events | grep -i "Successfully assigned"
```

**다른 옵션들의 설명:**
- A. 리소스 경합: 여러 스케줄러가 동일한 노드 풀에 파드를 스케줄링할 때 발생할 수 있는 실제 문제입니다.
- B. 스케줄링 결정 충돌: 여러 스케줄러가 동일한 파드를 스케줄링하려고 시도할 때 발생할 수 있는 실제 문제입니다.
- D. 리더 선출 충돌: 동일한 이름의 여러 스케줄러 인스턴스가 리더십을 획득하려고 경쟁할 때 발생할 수 있는 실제 문제입니다.
</details>

### 2. Kubernetes 스케줄러에서 "Permit" 확장 포인트의 역할은 무엇인가요?

A. 파드를 노드에 바인딩  
B. 파드의 스케줄링을 허용, 거부 또는 지연  
C. 파드를 실행할 수 없는 노드 제외  
D. 노드에 점수 부여  

<details>
<summary>정답 및 설명</summary>

**정답: B. 파드의 스케줄링을 허용, 거부 또는 지연**

**설명:**
Kubernetes 스케줄링 프레임워크에서 "Permit" 확장 포인트의 역할은 파드의 스케줄링을 허용, 거부 또는 지연하는 것입니다. Permit 플러그인은 노드가 선택된 후 바인딩 단계 전에 실행되며, 파드의 스케줄링 결정에 대한 최종 승인 또는 거부를 제공합니다.

**Permit 확장 포인트의 주요 기능:**
1. **허용(Allow)**: 파드의 스케줄링을 허용하여 바인딩 단계로 진행합니다.
2. **거부(Deny)**: 파드의 스케줄링을 거부하여 다른 노드를 선택하도록 합니다.
3. **지연(Wait)**: 파드의 스케줄링을 일시적으로 지연시키고, 특정 조건이 충족될 때까지 대기합니다.

**Permit 플러그인 인터페이스:**
```go
type PermitPlugin interface {
    Plugin
    // Permit은 파드의 스케줄링을 허용, 거부 또는 지연합니다.
    // 반환 값:
    // - Success: 파드의 스케줄링을 허용합니다.
    // - Deny: 파드의 스케줄링을 거부합니다.
    // - Wait: 파드의 스케줄링을 지연시키고, 타임아웃 또는 허용될 때까지 대기합니다.
    Permit(ctx context.Context, state *CycleState, pod *v1.Pod, nodeName string) (*Status, time.Duration)
}
```

**Permit 결과 유형:**
1. **Success**: 파드의 스케줄링을 허용합니다.
2. **Deny**: 파드의 스케줄링을 거부합니다.
3. **Wait**: 파드의 스케줄링을 지연시키고, 지정된 시간 동안 대기합니다.

**기본 Permit 플러그인:**
Kubernetes는 다음과 같은 기본 Permit 플러그인을 제공합니다:

1. **TaintToleration**: 노드 테인트와 파드 톨러레이션을 확인합니다.
2. **PodTopologySpread**: 파드 토폴로지 분산 제약 조건을 확인합니다.

**사용자 정의 Permit 플러그인 예시:**
```go
// CustomPermit는 사용자 정의 허가 로직을 구현합니다.
type CustomPermit struct {
    handle framework.Handle
    // 대기 중인 파드를 추적하기 위한 맵
    waitingPods map[string]waitingPod
    // 맵 접근을 동기화하기 위한 뮤텍스
    mu sync.RWMutex
}

// waitingPod는 대기 중인 파드 정보를 저장합니다.
type waitingPod struct {
    pod      *v1.Pod
    nodeName string
    status   chan bool  // true: 허용, false: 거부
}

// Name은 플러그인 이름을 반환합니다.
func (pl *CustomPermit) Name() string {
    return "CustomPermit"
}

// Permit은 파드의 스케줄링을 허용, 거부 또는 지연합니다.
func (pl *CustomPermit) Permit(ctx context.Context, state *framework.CycleState, pod *v1.Pod, nodeName string) (*framework.Status, time.Duration) {
    // 예: 특정 조건에 따라 파드의 스케줄링을 허용, 거부 또는 지연
    if shouldWait(pod, nodeName) {
        // 파드를 대기 목록에 추가
        key := fmt.Sprintf("%s/%s", pod.Namespace, pod.Name)
        
        pl.mu.Lock()
        if pl.waitingPods == nil {
            pl.waitingPods = make(map[string]waitingPod)
        }
        pl.waitingPods[key] = waitingPod{
            pod:      pod,
            nodeName: nodeName,
            status:   make(chan bool),
        }
        pl.mu.Unlock()
        
        // 최대 10분 동안 대기
        return framework.NewStatus(framework.Wait, "waiting for condition"), 10 * time.Minute
    }
    
    if shouldDeny(pod, nodeName) {
        return framework.NewStatus(framework.Unschedulable, "denied by custom permit plugin"), 0
    }
    
    // 파드의 스케줄링을 허용
    return nil, 0
}

// 대기 중인 파드를 허용
func (pl *CustomPermit) Allow(pod *v1.Pod) {
    key := fmt.Sprintf("%s/%s", pod.Namespace, pod.Name)
    
    pl.mu.RLock()
    waitingPod, ok := pl.waitingPods[key]
    pl.mu.RUnlock()
    
    if ok {
        // 파드 허용
        waitingPod.status <- true
        
        pl.mu.Lock()
        delete(pl.waitingPods, key)
        pl.mu.Unlock()
    }
}

// 대기 중인 파드를 거부
func (pl *CustomPermit) Reject(pod *v1.Pod) {
    key := fmt.Sprintf("%s/%s", pod.Namespace, pod.Name)
    
    pl.mu.RLock()
    waitingPod, ok := pl.waitingPods[key]
    pl.mu.RUnlock()
    
    if ok {
        // 파드 거부
        waitingPod.status <- false
        
        pl.mu.Lock()
        delete(pl.waitingPods, key)
        pl.mu.Unlock()
    }
}

// 파드가 대기해야 하는지 확인하는 함수
func shouldWait(pod *v1.Pod, nodeName string) bool {
    // 사용자 정의 로직 구현
    return false
}

// 파드가 거부되어야 하는지 확인하는 함수
func shouldDeny(pod *v1.Pod, nodeName string) bool {
    // 사용자 정의 로직 구현
    return false
}
```

**스케줄러 구성에서 Permit 플러그인 활성화:**
```yaml
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
profiles:
- schedulerName: custom-scheduler
  plugins:
    permit:
      enabled:
      - name: CustomPermit
      disabled:
      - name: TaintToleration  # 기본 플러그인 비활성화
```

**Permit 사용 사례:**
1. **Gang 스케줄링**: 모든 관련 파드가 스케줄링될 준비가 될 때까지 파드 그룹의 스케줄링을 지연합니다.
2. **리소스 예약**: 파드가 스케줄링되기 전에 외부 리소스를 예약합니다.
3. **정책 검증**: 파드 스케줄링이 조직 정책을 준수하는지 확인합니다.
4. **승인 워크플로우**: 파드 스케줄링에 대한 외부 승인을 요청합니다.

**Gang 스케줄링 예시:**
Gang 스케줄링은 모든 관련 파드가 함께 스케줄링되도록 보장하는 기법입니다. 이는 분산 학습 작업과 같이 모든 구성 요소가 동시에 실행되어야 하는 워크로드에 유용합니다.

```go
// GangPermit는 Gang 스케줄링을 구현합니다.
type GangPermit struct {
    handle framework.Handle
    // 그룹별 대기 중인 파드를 추적하기 위한 맵
    waitingGroups map[string]gangGroup
    mu sync.RWMutex
}

// gangGroup은 Gang의 정보를 저장합니다.
type gangGroup struct {
    pods      map[string]*v1.Pod
    nodeName  map[string]string
    minCount  int
    readyPods int
}

// Permit은 파드의 스케줄링을 허용, 거부 또는 지연합니다.
func (pl *GangPermit) Permit(ctx context.Context, state *framework.CycleState, pod *v1.Pod, nodeName string) (*framework.Status, time.Duration) {
    // Gang ID 가져오기
    gangID, ok := pod.Labels["gang-id"]
    if !ok {
        // Gang ID가 없으면 일반 파드로 처리
        return nil, 0
    }
    
    pl.mu.Lock()
    defer pl.mu.Unlock()
    
    // 그룹이 없으면 생성
    if _, ok := pl.waitingGroups[gangID]; !ok {
        minCount, _ := strconv.Atoi(pod.Labels["gang-min-count"])
        if minCount <= 0 {
            minCount = 1
        }
        
        pl.waitingGroups[gangID] = gangGroup{
            pods:      make(map[string]*v1.Pod),
            nodeName:  make(map[string]string),
            minCount:  minCount,
            readyPods: 0,
        }
    }
    
    // 파드 추가
    group := pl.waitingGroups[gangID]
    key := fmt.Sprintf("%s/%s", pod.Namespace, pod.Name)
    group.pods[key] = pod
    group.nodeName[key] = nodeName
    group.readyPods++
    
    // 최소 개수에 도달했는지 확인
    if group.readyPods >= group.minCount {
        // 모든 파드 허용
        for _, p := range group.pods {
            pl.handle.PermitPlugin().Allow(p)
        }
        
        // 그룹 삭제
        delete(pl.waitingGroups, gangID)
        
        return nil, 0
    }
    
    // 최소 개수에 도달할 때까지 대기
    return framework.NewStatus(framework.Wait, "waiting for gang members"), 10 * time.Minute
}
```

**다른 옵션들의 문제점:**
- A. 파드를 노드에 바인딩: 이는 "Bind" 확장 포인트의 역할입니다.
- C. 파드를 실행할 수 없는 노드 제외: 이는 "Filter" 확장 포인트의 역할입니다.
- D. 노드에 점수 부여: 이는 "Score" 확장 포인트의 역할입니다.
</details>
### 3. Kubernetes에서 Gang 스케줄링(Gang Scheduling)의 주요 목적은 무엇인가요?

A. 파드를 특정 노드에만 배치  
B. 모든 관련 파드가 함께 스케줄링되도록 보장  
C. 파드를 다양한 노드에 균등하게 분산  
D. 파드를 우선순위에 따라 스케줄링  

<details>
<summary>정답 및 설명</summary>

**정답: B. 모든 관련 파드가 함께 스케줄링되도록 보장**

**설명:**
Kubernetes에서 Gang 스케줄링(Gang Scheduling)의 주요 목적은 모든 관련 파드가 함께 스케줄링되도록 보장하는 것입니다. 이는 모든 구성 요소가 동시에 실행되어야 하는 분산 학습 작업, 분산 데이터 처리 작업 등의 워크로드에 중요합니다.

**Gang 스케줄링의 필요성:**
1. **All-or-Nothing 요구 사항**: 일부 워크로드는 모든 구성 요소가 동시에 실행되어야 하며, 일부만 실행되면 작업이 진행되지 않습니다.
2. **리소스 낭비 방지**: 일부 파드만 스케줄링되고 나머지는 대기 상태인 경우, 이미 스케줄링된 파드가 사용하는 리소스가 낭비될 수 있습니다.
3. **데드락 방지**: 서로 의존하는 파드가 서로 다른 시점에 스케줄링되면 데드락이 발생할 수 있습니다.

**Gang 스케줄링 구현 방법:**
Kubernetes는 기본적으로 Gang 스케줄링을 지원하지 않지만, 다음과 같은 방법으로 구현할 수 있습니다:

1. **사용자 정의 스케줄러**: Permit 확장 포인트를 사용하여 Gang 스케줄링을 구현합니다.
2. **외부 컨트롤러**: Kubernetes 외부에서 Gang 스케줄링을 관리하는 컨트롤러를 구현합니다.
3. **오픈 소스 솔루션**: Volcano, Kube-batch 등의 오픈 소스 스케줄러를 사용합니다.

**Gang 스케줄링 예시(Volcano):**
```yaml
# Gang 스케줄링을 위한 PodGroup 정의
apiVersion: scheduling.volcano.sh/v1beta1
kind: PodGroup
metadata:
  name: tf-training
  namespace: default
spec:
  minMember: 4  # 최소 4개의 파드가 함께 스케줄링되어야 함
  minResources:
    cpu: 8
    memory: 16Gi
  queue: default

---
# Gang에 속하는 파드
apiVersion: v1
kind: Pod
metadata:
  name: tf-worker-0
  namespace: default
  labels:
    app: tf-training
  annotations:
    scheduling.volcano.sh/pod-group: tf-training  # PodGroup 참조
spec:
  schedulerName: volcano  # Volcano 스케줄러 사용
  containers:
  - name: tensorflow
    image: tensorflow/tensorflow:latest-gpu
    resources:
      requests:
        cpu: 2
        memory: 4Gi
        nvidia.com/gpu: 1
```

**사용자 정의 Permit 플러그인을 사용한 Gang 스케줄링 구현:**
```go
// GangSchedulingPlugin은 Gang 스케줄링을 구현합니다.
type GangSchedulingPlugin struct {
    handle framework.Handle
    // Gang별 파드 추적
    gangs map[string]*Gang
    mu sync.RWMutex
}

// Gang은 관련 파드 그룹을 나타냅니다.
type Gang struct {
    MinRequired int
    Scheduled   map[string]string  // 파드 이름 -> 노드 이름
    Waiting     map[string]*framework.WaitingPod
}

// Name은 플러그인 이름을 반환합니다.
func (pl *GangSchedulingPlugin) Name() string {
    return "GangSchedulingPlugin"
}

// PreFilter는 Gang 정보를 초기화합니다.
func (pl *GangSchedulingPlugin) PreFilter(ctx context.Context, state *framework.CycleState, pod *v1.Pod) *framework.Status {
    gangID, ok := pod.Labels["gang-id"]
    if !ok {
        return nil  // Gang ID가 없으면 일반 파드로 처리
    }
    
    pl.mu.Lock()
    defer pl.mu.Unlock()
    
    if _, ok := pl.gangs[gangID]; !ok {
        minRequired, _ := strconv.Atoi(pod.Labels["gang-min-required"])
        if minRequired <= 0 {
            minRequired = 1
        }
        
        pl.gangs[gangID] = &Gang{
            MinRequired: minRequired,
            Scheduled:   make(map[string]string),
            Waiting:     make(map[string]*framework.WaitingPod),
        }
    }
    
    return nil
}

// Permit은 Gang 스케줄링 로직을 구현합니다.
func (pl *GangSchedulingPlugin) Permit(ctx context.Context, state *framework.CycleState, pod *v1.Pod, nodeName string) (*framework.Status, time.Duration) {
    gangID, ok := pod.Labels["gang-id"]
    if !ok {
        return nil, 0  // Gang ID가 없으면 일반 파드로 처리
    }
    
    pl.mu.Lock()
    defer pl.mu.Unlock()
    
    gang, ok := pl.gangs[gangID]
    if !ok {
        return framework.NewStatus(framework.Error, "gang not found"), 0
    }
    
    podKey := fmt.Sprintf("%s/%s", pod.Namespace, pod.Name)
    gang.Scheduled[podKey] = nodeName
    
    // 충분한 파드가 스케줄링되었는지 확인
    if len(gang.Scheduled) >= gang.MinRequired {
        // 모든 대기 중인 파드 허용
        for _, waitingPod := range gang.Waiting {
            waitingPod.Allow(pl.Name())
        }
        gang.Waiting = make(map[string]*framework.WaitingPod)
        return nil, 0
    }
    
    // 충분한 파드가 스케줄링될 때까지 대기
    waitingPod := framework.NewWaitingPod(pod)
    gang.Waiting[podKey] = waitingPod
    return framework.NewStatus(framework.Wait, "waiting for gang members"), 10 * time.Minute
}
```

**Gang 스케줄링의 장단점:**
장점:
- 모든 관련 파드가 함께 스케줄링되도록 보장
- 리소스 낭비 방지
- 데드락 및 기아 상태 방지

단점:
- 구현 복잡성 증가
- 스케줄링 지연 가능성
- 클러스터 리소스 활용도 감소 가능성

**Gang 스케줄링이 필요한 워크로드:**
1. **분산 학습 작업**: TensorFlow, PyTorch 등의 분산 학습 프레임워크
2. **분산 데이터 처리**: Spark, Flink 등의 분산 데이터 처리 프레임워크
3. **MPI 작업**: 고성능 컴퓨팅(HPC) 워크로드
4. **서비스 메시**: 여러 구성 요소가 함께 작동해야 하는 서비스 메시

**다른 옵션들의 문제점:**
- A. 파드를 특정 노드에만 배치: 이는 노드 셀렉터 또는 노드 어피니티의 역할입니다.
- C. 파드를 다양한 노드에 균등하게 분산: 이는 파드 토폴로지 분산 제약 조건의 역할입니다.
- D. 파드를 우선순위에 따라 스케줄링: 이는 파드 우선순위 및 선점의 역할입니다.
</details>

### 4. Kubernetes에서 스케줄러 익스텐더(Scheduler Extender)를 구현할 때 필요한 API 엔드포인트가 아닌 것은 무엇인가요?

A. /filter  
B. /prioritize  
C. /bind  
D. /validate  

<details>
<summary>정답 및 설명</summary>

**정답: D. /validate**

**설명:**
Kubernetes에서 스케줄러 익스텐더(Scheduler Extender)를 구현할 때 필요한 API 엔드포인트가 아닌 것은 "/validate"입니다. 스케줄러 익스텐더는 일반적으로 "/filter", "/prioritize", "/bind", "/preempt" 등의 엔드포인트를 구현하지만, "/validate" 엔드포인트는 스케줄러 익스텐더의 표준 API가 아닙니다.

**스케줄러 익스텐더 API 엔드포인트:**
1. **filter**: 노드 목록을 받아 필터링된 노드 목록을 반환합니다.
2. **prioritize**: 노드 목록을 받아 각 노드에 점수를 할당합니다.
3. **bind**: 파드를 노드에 바인딩합니다.
4. **preempt**: 선점을 위한 노드와 파드 목록을 반환합니다.

**스케줄러 익스텐더 구성 예시:**
```yaml
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
profiles:
- schedulerName: default-scheduler
  extenders:
  - urlPrefix: "http://extender-service:8080"
    filterVerb: "filter"
    prioritizeVerb: "prioritize"
    bindVerb: "bind"
    enableHTTPS: false
    nodeCacheCapable: false
    ignorable: true
    managedResources:
    - name: example.com/foo
      ignoredByScheduler: true
```

**스케줄러 익스텐더 API 요청 및 응답 형식:**

1. **filter API**:
   - 요청:
     ```json
     {
       "pod": <pod>,
       "nodes": <nodes>,
       "nodenames": <node-names>
     }
     ```
   - 응답:
     ```json
     {
       "nodes": <filtered-nodes>,
       "nodenames": <filtered-node-names>,
       "failedNodes": <failed-nodes>,
       "error": <error-message>
     }
     ```

2. **prioritize API**:
   - 요청:
     ```json
     {
       "pod": <pod>,
       "nodes": <nodes>,
       "nodenames": <node-names>
     }
     ```
   - 응답:
     ```json
     {
       "hostPriorities": [
         {
           "host": <node-name>,
           "score": <score>
         },
         ...
       ],
       "error": <error-message>
     }
     ```

3. **bind API**:
   - 요청:
     ```json
     {
       "pod": <pod>,
       "node": <node-name>
     }
     ```
   - 응답:
     ```json
     {
       "error": <error-message>
     }
     ```

4. **preempt API**:
   - 요청:
     ```json
     {
       "pod": <pod>,
       "nodenames": <node-names>,
       "nodes": <nodes>
     }
     ```
   - 응답:
     ```json
     {
       "nodenames": <node-names>,
       "nodes": <nodes>,
       "podsToPreempt": {
         <node-name>: [<pod>, ...],
         ...
       },
       "error": <error-message>
     }
     ```

**스케줄러 익스텐더 구현 예시(Go):**
```go
package main

import (
    "encoding/json"
    "log"
    "net/http"
    
    v1 "k8s.io/api/core/v1"
    extender "k8s.io/kube-scheduler/extender/v1"
)

func main() {
    http.HandleFunc("/filter", filterHandler)
    http.HandleFunc("/prioritize", prioritizeHandler)
    http.HandleFunc("/bind", bindHandler)
    
    log.Fatal(http.ListenAndServe(":8080", nil))
}

// 필터 핸들러
func filterHandler(w http.ResponseWriter, r *http.Request) {
    var args extender.ExtenderArgs
    var result extender.ExtenderFilterResult
    
    // 요청 본문 디코딩
    if err := json.NewDecoder(r.Body).Decode(&args); err != nil {
        http.Error(w, err.Error(), http.StatusBadRequest)
        return
    }
    
    // 필터링 로직 구현
    filteredNodes := make([]v1.Node, 0, len(args.Nodes.Items))
    failedNodes := make(map[string]string)
    
    for _, node := range args.Nodes.Items {
        // 사용자 정의 필터링 로직
        if customFilter(&args.Pod, &node) {
            filteredNodes = append(filteredNodes, node)
        } else {
            failedNodes[node.Name] = "Node failed custom filter"
        }
    }
    
    // 결과 설정
    result.Nodes = &v1.NodeList{Items: filteredNodes}
    result.FailedNodes = failedNodes
    
    // 응답 전송
    w.Header().Set("Content-Type", "application/json")
    if err := json.NewEncoder(w).Encode(result); err != nil {
        http.Error(w, err.Error(), http.StatusInternalServerError)
        return
    }
}

// 우선순위 지정 핸들러
func prioritizeHandler(w http.ResponseWriter, r *http.Request) {
    var args extender.ExtenderArgs
    var result extender.HostPriorityList
    
    // 요청 본문 디코딩
    if err := json.NewDecoder(r.Body).Decode(&args); err != nil {
        http.Error(w, err.Error(), http.StatusBadRequest)
        return
    }
    
    // 우선순위 지정 로직 구현
    result = make(extender.HostPriorityList, 0, len(args.Nodes.Items))
    
    for _, node := range args.Nodes.Items {
        // 사용자 정의 점수 계산
        score := customScore(&args.Pod, &node)
        result = append(result, extender.HostPriority{
            Host:  node.Name,
            Score: score,
        })
    }
    
    // 응답 전송
    w.Header().Set("Content-Type", "application/json")
    if err := json.NewEncoder(w).Encode(result); err != nil {
        http.Error(w, err.Error(), http.StatusInternalServerError)
        return
    }
}

// 바인드 핸들러
func bindHandler(w http.ResponseWriter, r *http.Request) {
    var args extender.ExtenderBindingArgs
    
    // 요청 본문 디코딩
    if err := json.NewDecoder(r.Body).Decode(&args); err != nil {
        http.Error(w, err.Error(), http.StatusBadRequest)
        return
    }
    
    // 바인딩 로직 구현
    err := customBind(&args.Pod, args.Node)
    
    // 응답 전송
    w.Header().Set("Content-Type", "application/json")
    if err != nil {
        json.NewEncoder(w).Encode(extender.ExtenderBindingResult{
            Error: err.Error(),
        })
    } else {
        json.NewEncoder(w).Encode(extender.ExtenderBindingResult{})
    }
}

// 사용자 정의 필터링 함수
func customFilter(pod *v1.Pod, node *v1.Node) bool {
    // 사용자 정의 필터링 로직 구현
    return true
}

// 사용자 정의 점수 계산 함수
func customScore(pod *v1.Pod, node *v1.Node) int64 {
    // 사용자 정의 점수 계산 로직 구현
    return 100
}

// 사용자 정의 바인딩 함수
func customBind(pod *v1.Pod, nodeName string) error {
    // 사용자 정의 바인딩 로직 구현
    return nil
}
```

**스케줄러 익스텐더의 장단점:**
장점:
- 스케줄러 코드베이스와 독립적으로 개발 가능
- 다양한 프로그래밍 언어로 구현 가능
- 스케줄러 업그레이드에 영향을 덜 받음

단점:
- HTTP 통신 오버헤드로 인한 성능 저하
- 스케줄링 사이클의 일부 단계만 확장 가능
- 스케줄러와 익스텐더 간의 통신 실패 가능성

**스케줄러 익스텐더 vs 스케줄링 프레임워크 플러그인:**
- **스케줄러 익스텐더**: HTTP 웹훅을 통해 외부 프로세스로 실행됩니다.
- **스케줄링 프레임워크 플러그인**: 스케줄러 코드베이스와 직접 통합되어 실행됩니다.

**다른 옵션들의 설명:**
- A. /filter: 스케줄러 익스텐더의 유효한 API 엔드포인트로, 노드 목록을 필터링합니다.
- B. /prioritize: 스케줄러 익스텐더의 유효한 API 엔드포인트로, 노드에 점수를 할당합니다.
- C. /bind: 스케줄러 익스텐더의 유효한 API 엔드포인트로, 파드를 노드에 바인딩합니다.
</details>
### 5. Kubernetes에서 스케줄러 프레임워크의 "PostFilter" 확장 포인트의 역할은 무엇인가요?

A. 필터링 후 노드에 점수 부여  
B. 필터링 후 파드를 노드에 바인딩  
C. 필터링 실패 시 선점 로직 실행  
D. 필터링 후 파드 상태 업데이트  

<details>
<summary>정답 및 설명</summary>

**정답: C. 필터링 실패 시 선점 로직 실행**

**설명:**
Kubernetes 스케줄링 프레임워크에서 "PostFilter" 확장 포인트의 역할은 필터링 실패 시 선점 로직을 실행하는 것입니다. 모든 노드가 필터링 단계에서 제외되어 파드를 스케줄링할 수 없는 경우, PostFilter 플러그인은 선점을 통해 파드를 스케줄링할 수 있는 방법을 찾습니다.

**PostFilter 확장 포인트의 주요 기능:**
1. **선점 후보 식별**: 선점할 수 있는 파드와 노드를 식별합니다.
2. **선점 시뮬레이션**: 선점 후 파드가 스케줄링될 수 있는지 시뮬레이션합니다.
3. **선점 결정**: 최적의 선점 전략을 결정합니다.

**PostFilter 플러그인 인터페이스:**
```go
type PostFilterPlugin interface {
    Plugin
    // PostFilter는 필터링 실패 시 호출됩니다.
    // 선점을 통해 파드를 스케줄링할 수 있는 방법을 찾습니다.
    PostFilter(ctx context.Context, state *CycleState, pod *v1.Pod, filteredNodeStatusMap NodeToStatusMap) (*PostFilterResult, *Status)
}

// PostFilterResult는 PostFilter 작업의 결과를 나타냅니다.
type PostFilterResult struct {
    // 선점 후 파드가 스케줄링될 노드
    NominatedNodeName string
}
```

**기본 PostFilter 플러그인:**
Kubernetes는 다음과 같은 기본 PostFilter 플러그인을 제공합니다:

1. **DefaultPreemption**: 기본 선점 로직을 구현합니다.

**DefaultPreemption 플러그인의 동작:**
1. 우선순위가 낮은 파드를 선점하여 공간을 확보할 수 있는 노드를 식별합니다.
2. 각 노드에서 선점할 파드를 결정합니다.
3. 선점 후 파드가 스케줄링될 수 있는지 확인합니다.
4. 최적의 선점 전략을 선택합니다.
5. 선택된 노드를 파드의 nominatedNodeName으로 설정합니다.

**사용자 정의 PostFilter 플러그인 예시:**
```go
// CustomPostFilter는 사용자 정의 선점 로직을 구현합니다.
type CustomPostFilter struct {
    handle framework.Handle
}

// Name은 플러그인 이름을 반환합니다.
func (pl *CustomPostFilter) Name() string {
    return "CustomPostFilter"
}

// PostFilter는 필터링 실패 시 호출됩니다.
func (pl *CustomPostFilter) PostFilter(ctx context.Context, state *framework.CycleState, pod *v1.Pod, filteredNodeStatusMap framework.NodeToStatusMap) (*framework.PostFilterResult, *framework.Status) {
    // 선점 가능한 노드 식별
    preemptableNodes := identifyPreemptableNodes(pl.handle, pod, filteredNodeStatusMap)
    if len(preemptableNodes) == 0 {
        return nil, framework.NewStatus(framework.Unschedulable, "no preemptable nodes found")
    }
    
    // 각 노드에서 선점할 파드 결정
    nodeToVictims := map[string]*framework.Victims{}
    for _, node := range preemptableNodes {
        victims, err := selectVictimsOnNode(pl.handle, pod, node)
        if err != nil {
            continue
        }
        nodeToVictims[node.Name] = victims
    }
    
    // 최적의 선점 전략 선택
    nominatedNode, victims := selectBestNodeForPreemption(nodeToVictims)
    if nominatedNode == "" {
        return nil, framework.NewStatus(framework.Unschedulable, "no node for preemption")
    }
    
    // 선점 실행
    for _, victim := range victims.Pods {
        if err := pl.handle.ClientSet().CoreV1().Pods(victim.Namespace).Delete(ctx, victim.Name, metav1.DeleteOptions{}); err != nil {
            return nil, framework.NewStatus(framework.Error, err.Error())
        }
    }
    
    return &framework.PostFilterResult{
        NominatedNodeName: nominatedNode,
    }, nil
}

// 선점 가능한 노드 식별
func identifyPreemptableNodes(handle framework.Handle, pod *v1.Pod, filteredNodeStatusMap framework.NodeToStatusMap) []*v1.Node {
    // 구현 생략
    return nil
}

// 노드에서 선점할 파드 선택
func selectVictimsOnNode(handle framework.Handle, pod *v1.Pod, node *v1.Node) (*framework.Victims, error) {
    // 구현 생략
    return nil, nil
}

// 최적의 선점 전략 선택
func selectBestNodeForPreemption(nodeToVictims map[string]*framework.Victims) (string, *framework.Victims) {
    // 구현 생략
    return "", nil
}
```

**스케줄러 구성에서 PostFilter 플러그인 활성화:**
```yaml
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
profiles:
- schedulerName: custom-scheduler
  plugins:
    postFilter:
      enabled:
      - name: CustomPostFilter
      disabled:
      - name: DefaultPreemption  # 기본 플러그인 비활성화
```

**선점 관련 설정:**
```yaml
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
profiles:
- schedulerName: custom-scheduler
  pluginConfig:
  - name: DefaultPreemption
    args:
      minCandidateNodesPercentage: 10  # 선점 후보 노드의 최소 비율
      minCandidateNodesAbsolute: 100   # 선점 후보 노드의 최소 개수
```

**선점 프로세스:**
1. 파드가 모든 노드에서 필터링 단계를 통과하지 못하면 PostFilter 단계가 호출됩니다.
2. PostFilter 플러그인은 선점 후보 노드를 식별합니다.
3. 각 노드에서 선점할 파드를 결정합니다.
4. 선점 후 파드가 스케줄링될 수 있는지 확인합니다.
5. 최적의 선점 전략을 선택합니다.
6. 선택된 노드를 파드의 nominatedNodeName으로 설정합니다.
7. 선점된 파드는 정상적으로 종료(graceful termination)됩니다.
8. 선점된 파드가 종료되면, 우선순위가 높은 파드가 스케줄링됩니다.

**선점 관련 지표 모니터링:**
```bash
# 스케줄러 메트릭에서 선점 관련 지표 확인
kubectl get --raw /metrics | grep scheduler_preemption
```

**선점 이벤트 확인:**
```bash
# 선점 이벤트 확인
kubectl get events | grep -i preempt
```

**다른 옵션들의 문제점:**
- A. 필터링 후 노드에 점수 부여: 이는 "Score" 확장 포인트의 역할입니다.
- B. 필터링 후 파드를 노드에 바인딩: 이는 "Bind" 확장 포인트의 역할입니다.
- D. 필터링 후 파드 상태 업데이트: 이는 스케줄러 프레임워크의 확장 포인트가 아닙니다.
</details>

### 6. Kubernetes에서 스케줄러의 "NodeResourcesBalancedAllocation" 플러그인의 주요 목적은 무엇인가요?

A. 노드의 CPU와 메모리 사용 균형이 좋은 노드에 높은 점수 부여  
B. 노드의 리소스 사용량이 적은 노드에 높은 점수 부여  
C. 노드의 리소스 사용량이 많은 노드에 높은 점수 부여  
D. 노드의 리소스 제한을 설정  

<details>
<summary>정답 및 설명</summary>

**정답: A. 노드의 CPU와 메모리 사용 균형이 좋은 노드에 높은 점수 부여**

**설명:**
Kubernetes 스케줄러의 "NodeResourcesBalancedAllocation" 플러그인의 주요 목적은 노드의 CPU와 메모리 사용 균형이 좋은 노드에 높은 점수를 부여하는 것입니다. 이 플러그인은 노드의 CPU와 메모리 사용률 간의 차이가 적은 노드를 선호하여, 클러스터 전체의 리소스 사용 균형을 개선합니다.

**NodeResourcesBalancedAllocation 플러그인의 동작:**
1. 각 노드의 CPU 사용률과 메모리 사용률을 계산합니다.
2. CPU 사용률과 메모리 사용률 간의 차이를 계산합니다.
3. 차이가 적은 노드에 높은 점수를 부여합니다.

**점수 계산 방식:**
```
score = 10 - variance(cpuFraction, memoryFraction) * 10
```
여기서:
- cpuFraction = (요청된 CPU + 파드의 CPU 요청) / 할당 가능한 CPU
- memoryFraction = (요청된 메모리 + 파드의 메모리 요청) / 할당 가능한 메모리
- variance(a, b) = |a - b|

**예시:**
- 노드 A: CPU 사용률 80%, 메모리 사용률 80% → 차이: 0% → 점수: 10
- 노드 B: CPU 사용률 90%, 메모리 사용률 50% → 차이: 40% → 점수: 6
- 노드 C: CPU 사용률 30%, 메모리 사용률 90% → 차이: 60% → 점수: 4

이 경우, 노드 A가 가장 높은 점수를 받아 선택될 가능성이 높습니다.

**스케줄러 구성에서 NodeResourcesBalancedAllocation 플러그인 활성화:**
```yaml
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
profiles:
- schedulerName: default-scheduler
  plugins:
    score:
      enabled:
      - name: NodeResourcesBalancedAllocation
        weight: 2  # 가중치 설정
```

**플러그인 구성:**
```yaml
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
profiles:
- schedulerName: default-scheduler
  pluginConfig:
  - name: NodeResourcesBalancedAllocation
    args:
      resources:
      - name: cpu
        weight: 1
      - name: memory
        weight: 1
```

**NodeResourcesBalancedAllocation vs 다른 스코어링 플러그인:**
1. **NodeResourcesBalancedAllocation**: CPU와 메모리 사용 균형이 좋은 노드를 선호합니다.
2. **NodeResourcesFit**: 요청된 리소스에 비해 가용 리소스가 많은 노드를 선호합니다.
3. **NodeResourcesLeastAllocated**: 리소스 사용량이 적은 노드를 선호합니다.
4. **NodeResourcesMostAllocated**: 리소스 사용량이 많은 노드를 선호합니다.

**사용 사례:**
1. **리소스 균형**: 클러스터 전체의 CPU와 메모리 사용 균형을 개선합니다.
2. **병목 현상 방지**: 한 리소스 유형(CPU 또는 메모리)이 다른 유형보다 먼저 소진되는 것을 방지합니다.
3. **확장성 개선**: 리소스 사용 균형이 좋은 클러스터는 더 효율적으로 확장될 수 있습니다.

**사용자 정의 균형 할당 플러그인 예시:**
```go
// CustomBalancedAllocation은 사용자 정의 균형 할당 로직을 구현합니다.
type CustomBalancedAllocation struct {
    handle framework.Handle
    // 리소스 가중치
    resourceWeights map[v1.ResourceName]int64
}

// Name은 플러그인 이름을 반환합니다.
func (pl *CustomBalancedAllocation) Name() string {
    return "CustomBalancedAllocation"
}

// Score는 노드에 점수를 할당합니다.
func (pl *CustomBalancedAllocation) Score(ctx context.Context, state *framework.CycleState, pod *v1.Pod, nodeName string) (int64, *framework.Status) {
    nodeInfo, err := pl.handle.SnapshotSharedLister().NodeInfos().Get(nodeName)
    if err != nil {
        return 0, framework.NewStatus(framework.Error, fmt.Sprintf("getting node %q from Snapshot: %v", nodeName, err))
    }
    
    // 노드의 할당 가능한 리소스
    allocatable := nodeInfo.Node().Status.Allocatable
    
    // 노드에서 이미 요청된 리소스
    requested := nodeInfo.RequestedResource()
    
    // 파드의 리소스 요청
    podRequest := calculatePodResourceRequest(pod)
    
    // 리소스 사용률 계산
    fractions := make(map[v1.ResourceName]float64)
    for resource, weight := range pl.resourceWeights {
        if weight == 0 {
            continue
        }
        
        allocatableValue := allocatable[resource]
        if allocatableValue.IsZero() {
            continue
        }
        
        requestedValue := requested.ResourceList[resource]
        podRequestValue := podRequest[resource]
        
        fraction := float64(requestedValue.Value()+podRequestValue.Value()) / float64(allocatableValue.Value())
        fractions[resource] = fraction
    }
    
    // 리소스 사용률 간의 차이 계산
    var variance float64
    for _, fraction := range fractions {
        for _, otherFraction := range fractions {
            diff := fraction - otherFraction
            if diff > 0 {
                variance += diff
            } else {
                variance -= diff
            }
        }
    }
    
    // 점수 계산
    score := int64(100 - variance*100)
    if score < 0 {
        score = 0
    }
    
    return score, nil
}

// ScoreExtensions는 점수 정규화를 위한 인터페이스를 반환합니다.
func (pl *CustomBalancedAllocation) ScoreExtensions() framework.ScoreExtensions {
    return nil
}

// 파드의 리소스 요청 계산
func calculatePodResourceRequest(pod *v1.Pod) v1.ResourceList {
    result := v1.ResourceList{}
    for _, container := range pod.Spec.Containers {
        for resource, value := range container.Resources.Requests {
            if currentValue, ok := result[resource]; ok {
                currentValue.Add(value)
                result[resource] = currentValue
            } else {
                result[resource] = value.DeepCopy()
            }
        }
    }
    return result
}
```

**다른 옵션들의 문제점:**
- B. 노드의 리소스 사용량이 적은 노드에 높은 점수 부여: 이는 "NodeResourcesLeastAllocated" 플러그인의 역할입니다.
- C. 노드의 리소스 사용량이 많은 노드에 높은 점수 부여: 이는 "NodeResourcesMostAllocated" 플러그인의 역할입니다.
- D. 노드의 리소스 제한을 설정: 이는 스케줄러 플러그인의 역할이 아니며, 노드 리소스 제한은 노드 자체의 속성입니다.
</details>
### 7. Kubernetes에서 스케줄러의 "PreBind" 확장 포인트의 역할은 무엇인가요?

A. 파드를 노드에 바인딩  
B. 바인딩 전에 필요한 작업 수행  
C. 바인딩 후 정리 작업 수행  
D. 바인딩 실패 시 복구 작업 수행  

<details>
<summary>정답 및 설명</summary>

**정답: B. 바인딩 전에 필요한 작업 수행**

**설명:**
Kubernetes 스케줄링 프레임워크에서 "PreBind" 확장 포인트의 역할은 파드를 노드에 바인딩하기 전에 필요한 작업을 수행하는 것입니다. 예를 들어, 볼륨 프로비저닝, 네트워크 설정, 리소스 예약 등의 작업을 수행할 수 있습니다.

**PreBind 확장 포인트의 주요 기능:**
1. **볼륨 프로비저닝**: 필요한 볼륨을 생성하고 준비합니다.
2. **네트워크 설정**: 필요한 네트워크 리소스를 설정합니다.
3. **리소스 예약**: 필요한 리소스를 예약합니다.
4. **사전 검증**: 바인딩이 가능한지 최종 확인합니다.

**PreBind 플러그인 인터페이스:**
```go
type PreBindPlugin interface {
    Plugin
    // PreBind는 파드를 노드에 바인딩하기 전에 호출됩니다.
    PreBind(ctx context.Context, state *CycleState, pod *v1.Pod, nodeName string) *Status
}
```

**기본 PreBind 플러그인:**
Kubernetes는 다음과 같은 기본 PreBind 플러그인을 제공합니다:

1. **VolumeBinding**: 볼륨 바인딩 작업을 수행합니다.
2. **DefaultPreBind**: 기본적인 사전 바인딩 작업을 수행합니다.

**사용자 정의 PreBind 플러그인 예시:**
```go
// CustomPreBind는 사용자 정의 사전 바인딩 로직을 구현합니다.
type CustomPreBind struct {
    handle framework.Handle
}

// Name은 플러그인 이름을 반환합니다.
func (pl *CustomPreBind) Name() string {
    return "CustomPreBind"
}

// PreBind는 파드를 노드에 바인딩하기 전에 호출됩니다.
func (pl *CustomPreBind) PreBind(ctx context.Context, state *framework.CycleState, pod *v1.Pod, nodeName string) *framework.Status {
    // 1. 볼륨 프로비저닝
    if err := pl.provisionVolumes(ctx, pod, nodeName); err != nil {
        return framework.NewStatus(framework.Error, err.Error())
    }
    
    // 2. 네트워크 리소스 설정
    if err := pl.setupNetworking(ctx, pod, nodeName); err != nil {
        return framework.NewStatus(framework.Error, err.Error())
    }
    
    // 3. 리소스 예약
    if err := pl.reserveResources(ctx, pod, nodeName); err != nil {
        return framework.NewStatus(framework.Error, err.Error())
    }
    
    // 4. 최종 검증
    if err := pl.validateBinding(ctx, pod, nodeName); err != nil {
        return framework.NewStatus(framework.Error, err.Error())
    }
    
    return nil
}

// 볼륨 프로비저닝
func (pl *CustomPreBind) provisionVolumes(ctx context.Context, pod *v1.Pod, nodeName string) error {
    // 필요한 볼륨 식별
    for _, volume := range pod.Spec.Volumes {
        if volume.PersistentVolumeClaim != nil {
            // PVC 상태 확인
            pvc, err := pl.handle.ClientSet().CoreV1().PersistentVolumeClaims(pod.Namespace).Get(ctx, volume.PersistentVolumeClaim.ClaimName, metav1.GetOptions{})
            if err != nil {
                return err
            }
            
            // PVC가 바인딩되지 않은 경우
            if pvc.Status.Phase != v1.ClaimBound {
                return fmt.Errorf("PVC %s is not bound", pvc.Name)
            }
        }
    }
    return nil
}

// 네트워크 리소스 설정
func (pl *CustomPreBind) setupNetworking(ctx context.Context, pod *v1.Pod, nodeName string) error {
    // 예: 네트워크 정책 설정
    if err := pl.setupNetworkPolicies(ctx, pod, nodeName); err != nil {
        return err
    }
    
    // 예: 서비스 엔드포인트 설정
    if err := pl.setupServiceEndpoints(ctx, pod, nodeName); err != nil {
        return err
    }
    
    return nil
}

// 리소스 예약
func (pl *CustomPreBind) reserveResources(ctx context.Context, pod *v1.Pod, nodeName string) error {
    // 예: GPU 리소스 예약
    if err := pl.reserveGPUs(ctx, pod, nodeName); err != nil {
        return err
    }
    
    // 예: 특수 하드웨어 리소스 예약
    if err := pl.reserveSpecialHardware(ctx, pod, nodeName); err != nil {
        return err
    }
    
    return nil
}

// 바인딩 검증
func (pl *CustomPreBind) validateBinding(ctx context.Context, pod *v1.Pod, nodeName string) error {
    // 예: 노드 상태 재확인
    node, err := pl.handle.ClientSet().CoreV1().Nodes().Get(ctx, nodeName, metav1.GetOptions{})
    if err != nil {
        return err
    }
    
    // 예: 노드 리소스 가용성 확인
    if !hasEnoughResources(node, pod) {
        return fmt.Errorf("node %s does not have enough resources", nodeName)
    }
    
    return nil
}
```

**스케줄러 구성에서 PreBind 플러그인 활성화:**
```yaml
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
profiles:
- schedulerName: custom-scheduler
  plugins:
    preBind:
      enabled:
      - name: CustomPreBind
      disabled:
      - name: VolumeBinding  # 기본 플러그인 비활성화
```

**PreBind 사용 사례:**
1. **볼륨 프로비저닝**:
   - PersistentVolume 생성 및 바인딩
   - 임시 볼륨 준비
   - 스토리지 클래스 파라미터 검증

2. **네트워크 설정**:
   - 네트워크 정책 적용
   - 서비스 엔드포인트 설정
   - 로드 밸런서 구성

3. **리소스 예약**:
   - GPU 리소스 예약
   - FPGA 리소스 예약
   - 특수 하드웨어 리소스 예약

4. **보안 설정**:
   - 보안 정책 적용
   - 인증서 프로비저닝
   - 시크릿 마운트 준비

**PreBind 실패 처리:**
PreBind 플러그인이 실패를 반환하면:
1. 스케줄링 사이클이 중단됩니다.
2. 파드는 다시 스케줄링 큐에 들어갑니다.
3. 예약된 리소스는 해제됩니다.
4. 실패 이벤트가 기록됩니다.

**PreBind 로그 및 이벤트 모니터링:**
```bash
# 스케줄러 로그에서 PreBind 관련 메시지 확인
kubectl logs -n kube-system <scheduler-pod> | grep -i prebind

# 파드 이벤트 확인
kubectl describe pod <pod-name> | grep -i prebind
```

**다른 옵션들의 문제점:**
- A. 파드를 노드에 바인딩: 이는 "Bind" 확장 포인트의 역할입니다.
- C. 바인딩 후 정리 작업 수행: 이는 "PostBind" 확장 포인트의 역할입니다.
- D. 바인딩 실패 시 복구 작업 수행: 이는 스케줄러 프레임워크의 확장 포인트가 아닙니다.
</details>

### 8. Kubernetes에서 스케줄러의 "NodeResourcesFit" 플러그인의 주요 목적은 무엇인가요?

A. 노드의 리소스 사용량 모니터링  
B. 노드의 리소스 제한 설정  
C. 노드의 리소스 용량과 파드의 리소스 요청 비교  
D. 노드의 리소스 사용 균형 유지  

<details>
<summary>정답 및 설명</summary>

**정답: C. 노드의 리소스 용량과 파드의 리소스 요청 비교**

**설명:**
Kubernetes 스케줄러의 "NodeResourcesFit" 플러그인의 주요 목적은 노드의 리소스 용량과 파드의 리소스 요청을 비교하여, 파드가 노드에서 실행될 수 있는지 확인하는 것입니다. 이 플러그인은 CPU, 메모리, 임시 스토리지, 확장 리소스(GPU 등) 등 다양한 리소스 유형을 고려합니다.

**NodeResourcesFit 플러그인의 주요 기능:**
1. **리소스 요청 검증**: 파드의 리소스 요청이 노드의 할당 가능한 리소스를 초과하지 않는지 확인합니다.
2. **리소스 제한 검증**: 파드의 리소스 제한이 노드의 용량을 초과하지 않는지 확인합니다.
3. **확장 리소스 검증**: GPU, FPGA 등의 확장 리소스 요청이 노드에서 사용 가능한지 확인합니다.

**NodeResourcesFit 플러그인 구성:**
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
        type: LeastAllocated
        resources:
        - name: cpu
          weight: 1
        - name: memory
          weight: 1
```

**스코어링 전략:**
NodeResourcesFit 플러그인은 다음과 같은 스코어링 전략을 지원합니다:

1. **LeastAllocated**: 사용 중인 리소스가 적은 노드에 높은 점수를 부여합니다.
   ```
   score = (capacity - requested) / capacity
   ```

2. **MostAllocated**: 사용 중인 리소스가 많은 노드에 높은 점수를 부여합니다.
   ```
   score = requested / capacity
   ```

3. **RequestedToCapacityRatio**: 사용자 정의 함수를 사용하여 요청된 리소스와 용량의 비율에 따라 점수를 부여합니다.

**사용자 정의 NodeResourcesFit 플러그인 예시:**
```go
// CustomNodeResourcesFit는 사용자 정의 리소스 적합성 로직을 구현합니다.
type CustomNodeResourcesFit struct {
    handle framework.Handle
    // 리소스 가중치
    resourceWeights map[v1.ResourceName]int64
}

// Name은 플러그인 이름을 반환합니다.
func (pl *CustomNodeResourcesFit) Name() string {
    return "CustomNodeResourcesFit"
}

// Filter는 노드의 리소스 적합성을 검사합니다.
func (pl *CustomNodeResourcesFit) Filter(ctx context.Context, state *framework.CycleState, pod *v1.Pod, nodeInfo *framework.NodeInfo) *framework.Status {
    // 노드의 할당 가능한 리소스
    allocatable := nodeInfo.Node().Status.Allocatable
    
    // 노드에서 이미 요청된 리소스
    requested := nodeInfo.RequestedResource()
    
    // 파드의 리소스 요청
    podRequest := calculatePodResourceRequest(pod)
    
    // 각 리소스 유형에 대해 검사
    for resourceName := range pl.resourceWeights {
        allocatableValue := allocatable[resourceName]
        if allocatableValue.IsZero() {
            return framework.NewStatus(framework.Unschedulable, fmt.Sprintf("node does not have resource %s", resourceName))
        }
        
        requestedValue := requested.ResourceList[resourceName]
        podRequestValue := podRequest[resourceName]
        
        if requestedValue.Value()+podRequestValue.Value() > allocatableValue.Value() {
            return framework.NewStatus(framework.Unschedulable, fmt.Sprintf("insufficient %s", resourceName))
        }
    }
    
    return nil
}

// Score는 노드에 점수를 할당합니다.
func (pl *CustomNodeResourcesFit) Score(ctx context.Context, state *framework.CycleState, pod *v1.Pod, nodeName string) (int64, *framework.Status) {
    nodeInfo, err := pl.handle.SnapshotSharedLister().NodeInfos().Get(nodeName)
    if err != nil {
        return 0, framework.NewStatus(framework.Error, fmt.Sprintf("getting node %q from Snapshot: %v", nodeName, err))
    }
    
    // 노드의 할당 가능한 리소스
    allocatable := nodeInfo.Node().Status.Allocatable
    
    // 노드에서 이미 요청된 리소스
    requested := nodeInfo.RequestedResource()
    
    // 파드의 리소스 요청
    podRequest := calculatePodResourceRequest(pod)
    
    // 점수 계산
    var score int64 = 0
    for resourceName, weight := range pl.resourceWeights {
        allocatableValue := allocatable[resourceName]
        if allocatableValue.IsZero() {
            continue
        }
        
        requestedValue := requested.ResourceList[resourceName]
        podRequestValue := podRequest[resourceName]
        
        // LeastAllocated 전략 사용
        resourceScore := (float64(allocatableValue.Value()) - float64(requestedValue.Value()+podRequestValue.Value())) / float64(allocatableValue.Value())
        score += int64(resourceScore * float64(weight))
    }
    
    return score, nil
}

// ScoreExtensions는 점수 정규화를 위한 인터페이스를 반환합니다.
func (pl *CustomNodeResourcesFit) ScoreExtensions() framework.ScoreExtensions {
    return pl
}

// NormalizeScore는 점수를 정규화합니다.
func (pl *CustomNodeResourcesFit) NormalizeScore(ctx context.Context, state *framework.CycleState, pod *v1.Pod, scores framework.NodeScoreList) *framework.Status {
    var highest int64 = 0
    for _, nodeScore := range scores {
        if nodeScore.Score > highest {
            highest = nodeScore.Score
        }
    }
    
    if highest == 0 {
        return nil
    }
    
    for i := range scores {
        scores[i].Score = scores[i].Score * framework.MaxNodeScore / highest
    }
    
    return nil
}
```

**리소스 요청 및 제한 예시:**
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: resource-demo
spec:
  containers:
  - name: nginx
    image: nginx
    resources:
      requests:
        cpu: "500m"
        memory: "256Mi"
      limits:
        cpu: "1"
        memory: "512Mi"
```

**다른 옵션들의 문제점:**
- A. 노드의 리소스 사용량 모니터링: 이는 메트릭 서버나 모니터링 시스템의 역할입니다.
- B. 노드의 리소스 제한 설정: 이는 노드 자체의 구성이나 kubelet의 역할입니다.
- D. 노드의 리소스 사용 균형 유지: 이는 "NodeResourcesBalancedAllocation" 플러그인의 역할입니다.
</details>
### 9. Kubernetes에서 스케줄러의 "InterPodAffinity" 플러그인의 주요 목적은 무엇인가요?

A. 파드와 노드 간의 어피니티 규칙 처리  
B. 파드 간의 어피니티 및 안티-어피니티 규칙 처리  
C. 파드와 볼륨 간의 어피니티 규칙 처리  
D. 파드와 서비스 간의 어피니티 규칙 처리  

<details>
<summary>정답 및 설명</summary>

**정답: B. 파드 간의 어피니티 및 안티-어피니티 규칙 처리**

**설명:**
Kubernetes 스케줄러의 "InterPodAffinity" 플러그인의 주요 목적은 파드 간의 어피니티 및 안티-어피니티 규칙을 처리하는 것입니다. 이 플러그인은 파드가 다른 파드와 같은 토폴로지 도메인(노드, 영역, 리전 등)에 배치되거나(어피니티) 또는 배치되지 않도록(안티-어피니티) 제어합니다.

**InterPodAffinity 플러그인의 주요 기능:**
1. **파드 어피니티 규칙 처리**: 파드가 특정 레이블을 가진 다른 파드와 같은 토폴로지 도메인에 배치되도록 합니다.
2. **파드 안티-어피니티 규칙 처리**: 파드가 특정 레이블을 가진 다른 파드와 다른 토폴로지 도메인에 배치되도록 합니다.
3. **토폴로지 도메인 고려**: 노드, 영역, 리전 등 다양한 수준의 토폴로지 도메인을 고려합니다.

**파드 어피니티 및 안티-어피니티 유형:**
1. **requiredDuringSchedulingIgnoredDuringExecution**: 파드가 스케줄링되기 위해 반드시 충족해야 하는 규칙입니다(하드 요구 사항).
2. **preferredDuringSchedulingIgnoredDuringExecution**: 가능하면 충족하는 것이 좋지만, 필수는 아닌 규칙입니다(소프트 요구 사항).

**파드 어피니티 및 안티-어피니티 예시:**
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
    image: nginx
```

**InterPodAffinity 플러그인 구성:**
```yaml
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
profiles:
- schedulerName: default-scheduler
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
        weight: 2  # 가중치 설정
  pluginConfig:
  - name: InterPodAffinity
    args:
      hardPodAffinityWeight: 1  # 하드 파드 어피니티 가중치
```

**사용자 정의 InterPodAffinity 플러그인 예시:**
```go
// CustomInterPodAffinity는 사용자 정의 파드 간 어피니티 로직을 구현합니다.
type CustomInterPodAffinity struct {
    handle framework.Handle
    // 하드 파드 어피니티 가중치
    hardPodAffinityWeight int64
}

// Name은 플러그인 이름을 반환합니다.
func (pl *CustomInterPodAffinity) Name() string {
    return "CustomInterPodAffinity"
}

// PreFilter는 파드 간 어피니티 정보를 초기화합니다.
func (pl *CustomInterPodAffinity) PreFilter(ctx context.Context, state *framework.CycleState, pod *v1.Pod) *framework.Status {
    // 파드 어피니티 정보 초기화
    if pod.Spec.Affinity == nil || (pod.Spec.Affinity.PodAffinity == nil && pod.Spec.Affinity.PodAntiAffinity == nil) {
        return nil
    }
    
    // 파드 어피니티 정보 저장
    affinity := pod.Spec.Affinity
    state.Write(framework.StateKey("CustomInterPodAffinity"), affinity)
    
    return nil
}

// PreFilterExtensions는 추가 기능을 제공하는 인터페이스를 반환합니다.
func (pl *CustomInterPodAffinity) PreFilterExtensions() framework.PreFilterExtensions {
    return nil
}

// Filter는 파드 간 어피니티 규칙을 검사합니다.
func (pl *CustomInterPodAffinity) Filter(ctx context.Context, state *framework.CycleState, pod *v1.Pod, nodeInfo *framework.NodeInfo) *framework.Status {
    // 파드 어피니티 정보 가져오기
    obj, err := state.Read(framework.StateKey("CustomInterPodAffinity"))
    if err != nil {
        return nil
    }
    
    affinity, ok := obj.(*v1.Affinity)
    if !ok || affinity == nil {
        return nil
    }
    
    // 필수 파드 어피니티 규칙 검사
    if affinity.PodAffinity != nil {
        for _, term := range affinity.PodAffinity.RequiredDuringSchedulingIgnoredDuringExecution {
            if !satisfiesPodAffinityTerm(pod, term, nodeInfo, pl.handle) {
                return framework.NewStatus(framework.Unschedulable, "node does not satisfy pod affinity rules")
            }
        }
    }
    
    // 필수 파드 안티-어피니티 규칙 검사
    if affinity.PodAntiAffinity != nil {
        for _, term := range affinity.PodAntiAffinity.RequiredDuringSchedulingIgnoredDuringExecution {
            if satisfiesPodAffinityTerm(pod, term, nodeInfo, pl.handle) {
                return framework.NewStatus(framework.Unschedulable, "node does not satisfy pod anti-affinity rules")
            }
        }
    }
    
    return nil
}

// Score는 노드에 점수를 할당합니다.
func (pl *CustomInterPodAffinity) Score(ctx context.Context, state *framework.CycleState, pod *v1.Pod, nodeName string) (int64, *framework.Status) {
    // 파드 어피니티 정보 가져오기
    obj, err := state.Read(framework.StateKey("CustomInterPodAffinity"))
    if err != nil {
        return 0, nil
    }
    
    affinity, ok := obj.(*v1.Affinity)
    if !ok || affinity == nil {
        return 0, nil
    }
    
    nodeInfo, err := pl.handle.SnapshotSharedLister().NodeInfos().Get(nodeName)
    if err != nil {
        return 0, framework.NewStatus(framework.Error, fmt.Sprintf("getting node %q from Snapshot: %v", nodeName, err))
    }
    
    var score int64 = 0
    
    // 선호 파드 어피니티 점수 계산
    if affinity.PodAffinity != nil {
        for _, term := range affinity.PodAffinity.PreferredDuringSchedulingIgnoredDuringExecution {
            if satisfiesPodAffinityTerm(pod, term.PodAffinityTerm, nodeInfo, pl.handle) {
                score += term.Weight
            }
        }
    }
    
    // 선호 파드 안티-어피니티 점수 계산
    if affinity.PodAntiAffinity != nil {
        for _, term := range affinity.PodAntiAffinity.PreferredDuringSchedulingIgnoredDuringExecution {
            if !satisfiesPodAffinityTerm(pod, term.PodAffinityTerm, nodeInfo, pl.handle) {
                score += term.Weight
            }
        }
    }
    
    return score, nil
}

// ScoreExtensions는 점수 정규화를 위한 인터페이스를 반환합니다.
func (pl *CustomInterPodAffinity) ScoreExtensions() framework.ScoreExtensions {
    return pl
}

// NormalizeScore는 점수를 정규화합니다.
func (pl *CustomInterPodAffinity) NormalizeScore(ctx context.Context, state *framework.CycleState, pod *v1.Pod, scores framework.NodeScoreList) *framework.Status {
    var highest int64 = 0
    for _, nodeScore := range scores {
        if nodeScore.Score > highest {
            highest = nodeScore.Score
        }
    }
    
    if highest == 0 {
        return nil
    }
    
    for i := range scores {
        scores[i].Score = scores[i].Score * framework.MaxNodeScore / highest
    }
    
    return nil
}

// 파드 어피니티 조건 충족 여부 확인
func satisfiesPodAffinityTerm(pod *v1.Pod, term v1.PodAffinityTerm, nodeInfo *framework.NodeInfo, handle framework.Handle) bool {
    // 구현 생략
    return true
}
```

**파드 어피니티 및 안티-어피니티 사용 사례:**
1. **고가용성**: 같은 애플리케이션의 인스턴스를 다른 노드, 영역, 리전에 분산
2. **성능 최적화**: 서로 통신하는 파드를 같은 노드에 배치하여 지연 시간 최소화
3. **리소스 격리**: 리소스를 많이 사용하는 파드를 서로 다른 노드에 분산
4. **라이선스 제한**: 라이선스 제한이 있는 애플리케이션을 특정 노드에 집중

**파드 어피니티 및 안티-어피니티의 성능 영향:**
파드 어피니티 및 안티-어피니티는 모든 노드와 파드를 고려해야 하므로 계산 비용이 높을 수 있습니다. 특히 대규모 클러스터에서는 스케줄링 성능에 영향을 줄 수 있으므로 신중하게 사용해야 합니다.

**다른 옵션들의 문제점:**
- A. 파드와 노드 간의 어피니티 규칙 처리: 이는 "NodeAffinity" 플러그인의 역할입니다.
- C. 파드와 볼륨 간의 어피니티 규칙 처리: 이는 "VolumeBinding" 플러그인의 역할입니다.
- D. 파드와 서비스 간의 어피니티 규칙 처리: 이는 Kubernetes 스케줄러의 플러그인이 아닙니다.
</details>

### 10. Kubernetes에서 스케줄러의 "NodeName" 플러그인의 주요 목적은 무엇인가요?

A. 파드의 spec.nodeName 필드가 노드 이름과 일치하는지 확인  
B. 노드에 이름 할당  
C. 파드에 노드 이름 할당  
D. 노드 이름 형식 검증  

<details>
<summary>정답 및 설명</summary>

**정답: A. 파드의 spec.nodeName 필드가 노드 이름과 일치하는지 확인**

**설명:**
Kubernetes 스케줄러의 "NodeName" 플러그인의 주요 목적은 파드의 `spec.nodeName` 필드가 노드 이름과 일치하는지 확인하는 것입니다. 이 플러그인은 파드가 특정 노드에 직접 할당되었는지 확인하고, 일치하는 경우에만 해당 노드를 필터링 단계에서 통과시킵니다.

**NodeName 플러그인의 주요 기능:**
1. **노드 이름 확인**: 파드의 `spec.nodeName` 필드가 설정된 경우, 해당 이름과 일치하는 노드만 선택합니다.
2. **직접 스케줄링 지원**: 사용자가 파드를 특정 노드에 직접 할당할 수 있도록 합니다.
3. **스케줄러 우회**: `spec.nodeName`이 설정된 파드는 일반적인 스케줄링 로직을 우회하고 지정된 노드에 직접 할당됩니다.

**NodeName 플러그인 구현:**
```go
// NodeName 플러그인 구현 예시
type NodeName struct{}

// Name은 플러그인 이름을 반환합니다.
func (pl *NodeName) Name() string {
    return "NodeName"
}

// Filter는 파드의 spec.nodeName 필드가 노드 이름과 일치하는지 확인합니다.
func (pl *NodeName) Filter(ctx context.Context, state *framework.CycleState, pod *v1.Pod, nodeInfo *framework.NodeInfo) *framework.Status {
    if pod.Spec.NodeName == "" {
        return nil
    }
    
    if pod.Spec.NodeName != nodeInfo.Node().Name {
        return framework.NewStatus(framework.UnschedulableAndUnresolvable, "node name does not match")
    }
    
    return nil
}
```

**파드에 nodeName 지정 예시:**
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: nginx
spec:
  nodeName: worker-node-1  # 특정 노드에 직접 할당
  containers:
  - name: nginx
    image: nginx
```

**nodeName 사용 시 고려 사항:**
1. **스케줄러 우회**: `nodeName`을 사용하면 스케줄러의 필터링, 스코어링 등의 로직을 우회합니다.
2. **노드 존재 확인**: 지정된 노드가 존재하지 않으면 파드는 `Pending` 상태로 남습니다.
3. **리소스 확인 없음**: 노드의 리소스 가용성을 확인하지 않으므로, 리소스 부족으로 인한 실패가 발생할 수 있습니다.
4. **제약 조건 무시**: 테인트, 어피니티 등의 제약 조건을 무시합니다.

**nodeName vs nodeSelector vs nodeAffinity:**
1. **nodeName**: 특정 노드에 직접 할당합니다. 가장 제한적이고 유연성이 낮습니다.
2. **nodeSelector**: 레이블을 기반으로 노드를 선택합니다. 간단하지만 표현력이 제한적입니다.
3. **nodeAffinity**: 복잡한 노드 선택 규칙을 지원합니다. 가장 유연하고 표현력이 높습니다.

**nodeName 사용 사례:**
1. **디버깅**: 특정 노드에서 파드를 실행하여 문제를 디버깅합니다.
2. **테스트**: 특정 노드에서 테스트를 실행합니다.
3. **특수 하드웨어**: 특정 하드웨어가 있는 노드에 파드를 할당합니다.
4. **정적 파드**: kubelet에 의해 직접 관리되는 정적 파드에 사용됩니다.

**nodeName 사용 시 주의 사항:**
1. **자동 복구 없음**: 노드가 실패하면 파드는 자동으로 다른 노드로 이동하지 않습니다.
2. **확장성 제한**: 노드 이름이 하드코딩되므로 확장성이 제한됩니다.
3. **유지 관리 어려움**: 노드 이름이 변경되면 파드 정의를 업데이트해야 합니다.
4. **로드 밸런싱 없음**: 스케줄러의 로드 밸런싱 기능을 활용할 수 없습니다.

**대안 및 권장 사항:**
1. **nodeSelector 사용**:
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
       image: nginx
   ```

2. **nodeAffinity 사용**:
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
       image: nginx
   ```

**다른 옵션들의 문제점:**
- B. 노드에 이름 할당: 노드 이름은 노드 생성 시 할당되며, 스케줄러 플러그인의 역할이 아닙니다.
- C. 파드에 노드 이름 할당: 이는 스케줄러의 바인딩 단계에서 수행되며, NodeName 플러그인의 역할이 아닙니다.
- D. 노드 이름 형식 검증: 이는 API 서버의 검증 로직에 의해 수행되며, 스케줄러 플러그인의 역할이 아닙니다.
</details>
