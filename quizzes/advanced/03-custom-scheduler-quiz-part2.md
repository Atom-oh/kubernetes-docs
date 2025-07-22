# Custom Scheduler 퀴즈 (Part 2)

이 퀴즈는 Kubernetes에서 Custom Scheduler를 구현하고 사용하는 방법에 대한 심화 이해를 테스트합니다.

## 퀴즈 문제

### 1. Kubernetes 스케줄링 프레임워크에서 "Bind" 확장 포인트의 역할은 무엇인가요?

A. 파드를 노드에 바인딩하여 스케줄링 결정 확정  
B. 파드와 노드 간의 네트워크 바인딩 설정  
C. 파드와 서비스 간의 바인딩 생성  
D. 파드와 볼륨 간의 바인딩 설정  

<details>
<summary>정답 및 설명</summary>

**정답: A. 파드를 노드에 바인딩하여 스케줄링 결정 확정**

**설명:**
Kubernetes 스케줄링 프레임워크에서 "Bind" 확장 포인트의 역할은 파드를 선택된 노드에 바인딩하여 스케줄링 결정을 확정하는 것입니다. 바인딩 단계는 스케줄링 사이클의 마지막 단계로, 이 단계에서 파드의 `spec.nodeName` 필드가 설정되어 kubelet이 파드를 실행할 수 있게 됩니다.

**바인딩 프로세스:**
1. 스케줄러가 필터링 및 스코어링을 통해 최적의 노드를 선택합니다.
2. 선택된 노드에 파드를 예약(reserve)합니다.
3. 바인딩 단계에서 파드의 `spec.nodeName` 필드를 선택된 노드의 이름으로 업데이트합니다.
4. 업데이트된 파드 정보가 API 서버에 저장됩니다.
5. kubelet이 파드 정보를 감지하고 해당 노드에서 파드를 실행합니다.

**바인드 플러그인 구현 예시:**
```go
// 바인드 플러그인 예시
type MyBindPlugin struct {
    handle framework.Handle
}

func (bp *MyBindPlugin) Name() string {
    return "MyBindPlugin"
}

// Bind 메서드 구현
func (bp *MyBindPlugin) Bind(ctx context.Context, state *framework.CycleState, pod *v1.Pod, nodeName string) *framework.Status {
    // 파드 바인딩 객체 생성
    binding := &v1.Binding{
        ObjectMeta: metav1.ObjectMeta{
            Name:      pod.Name,
            Namespace: pod.Namespace,
        },
        Target: v1.ObjectReference{
            Kind:       "Node",
            Name:       nodeName,
            APIVersion: "v1",
        },
    }
    
    // API 서버에 바인딩 요청 전송
    err := bp.handle.ClientSet().CoreV1().Pods(pod.Namespace).Bind(ctx, binding, metav1.CreateOptions{})
    if err != nil {
        return framework.NewStatus(framework.Error, err.Error())
    }
    
    return nil
}
```

**스케줄러 구성에서 바인드 플러그인 활성화:**
```yaml
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
profiles:
- schedulerName: custom-scheduler
  plugins:
    bind:
      enabled:
      - name: MyBindPlugin
      disabled:
      - name: DefaultBinder  # 기본 바인더 비활성화
```

**바인딩 관련 이벤트 확인:**
```bash
# 파드 스케줄링 이벤트 확인
kubectl get events | grep -i "Successfully assigned"
```

**바인딩 실패 시 문제 해결:**
바인딩 단계에서 실패가 발생할 수 있는 일반적인 원인:
1. API 서버 연결 문제
2. 권한 부족
3. 노드 이름 오류
4. 경쟁 상태(다른 스케줄러가 동시에 같은 파드를 바인딩하려고 시도)

**다른 옵션들의 문제점:**
- B. 파드와 노드 간의 네트워크 바인딩 설정: 네트워크 설정은 CNI 플러그인의 역할이며, 스케줄러의 바인드 단계와는 관련이 없습니다.
- C. 파드와 서비스 간의 바인딩 생성: 서비스와 파드의 연결은 레이블 셀렉터를 통해 이루어지며, 스케줄러의 바인드 단계와는 관련이 없습니다.
- D. 파드와 볼륨 간의 바인딩 설정: 볼륨 바인딩은 PersistentVolumeClaim 컨트롤러에 의해 처리되며, 스케줄러의 바인드 단계와는 별개의 프로세스입니다.
</details>

### 2. 다음 중 Kubernetes에서 노드 어피니티(Node Affinity)와 관련이 없는 연산자는 무엇인가요?

A. In  
B. NotIn  
C. Exists  
D. Contains  

<details>
<summary>정답 및 설명</summary>

**정답: D. Contains**

**설명:**
Kubernetes에서 노드 어피니티(Node Affinity)와 관련이 없는 연산자는 `Contains`입니다. Kubernetes는 노드 어피니티에 `Contains` 연산자를 제공하지 않습니다.

**노드 어피니티에서 지원하는 연산자:**
1. **In**: 레이블 값이 지정된 값 중 하나와 일치해야 합니다.
2. **NotIn**: 레이블 값이 지정된 값과 일치하지 않아야 합니다.
3. **Exists**: 지정된 레이블 키가 존재해야 합니다.
4. **DoesNotExist**: 지정된 레이블 키가 존재하지 않아야 합니다.
5. **Gt**: 레이블 값이 지정된 값보다 커야 합니다(Greater than).
6. **Lt**: 레이블 값이 지정된 값보다 작아야 합니다(Less than).

**노드 어피니티 예시:**
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
          - key: kubernetes.io/e2e-az-name
            operator: In
            values:
            - e2e-az1
            - e2e-az2
      preferredDuringSchedulingIgnoredDuringExecution:
      - weight: 1
        preference:
          matchExpressions:
          - key: another-node-label-key
            operator: Exists
```

**노드 어피니티 유형:**
1. **requiredDuringSchedulingIgnoredDuringExecution**: 파드가 노드에 스케줄링되기 위해 반드시 충족해야 하는 규칙입니다(하드 요구 사항).
2. **preferredDuringSchedulingIgnoredDuringExecution**: 가능하면 충족하는 것이 좋지만, 필수는 아닌 규칙입니다(소프트 요구 사항).

**연산자 사용 예시:**
1. **In 연산자**:
   ```yaml
   - key: kubernetes.io/e2e-az-name
     operator: In
     values:
     - e2e-az1
     - e2e-az2
   ```
   노드의 `kubernetes.io/e2e-az-name` 레이블 값이 `e2e-az1` 또는 `e2e-az2`여야 합니다.

2. **NotIn 연산자**:
   ```yaml
   - key: kubernetes.io/e2e-az-name
     operator: NotIn
     values:
     - e2e-az3
   ```
   노드의 `kubernetes.io/e2e-az-name` 레이블 값이 `e2e-az3`가 아니어야 합니다.

3. **Exists 연산자**:
   ```yaml
   - key: kubernetes.io/e2e-az-name
     operator: Exists
   ```
   노드에 `kubernetes.io/e2e-az-name` 레이블이 존재해야 합니다.

4. **DoesNotExist 연산자**:
   ```yaml
   - key: emptyLabel
     operator: DoesNotExist
   ```
   노드에 `emptyLabel` 레이블이 존재하지 않아야 합니다.

5. **Gt/Lt 연산자**:
   ```yaml
   - key: node-size
     operator: Gt
     values:
     - "10"
   ```
   노드의 `node-size` 레이블 값이 10보다 커야 합니다.

**Custom Scheduler에서 노드 어피니티 처리:**
사용자 정의 스케줄러를 구현할 때는 파드의 노드 어피니티 요구 사항을 고려해야 합니다.

```go
// 노드 어피니티 검사 예시
func checkNodeAffinity(pod *v1.Pod, node *v1.Node) bool {
    affinity := pod.Spec.Affinity
    if affinity == nil || affinity.NodeAffinity == nil {
        return true  // 노드 어피니티가 없으면 모든 노드가 적합
    }
    
    // 필수 노드 어피니티 검사
    if required := affinity.NodeAffinity.RequiredDuringSchedulingIgnoredDuringExecution; required != nil {
        for _, term := range required.NodeSelectorTerms {
            if matchNodeSelectorTerm(term, node) {
                return true
            }
        }
        return false  // 어떤 NodeSelectorTerm도 일치하지 않음
    }
    
    return true
}

// NodeSelectorTerm 일치 여부 확인
func matchNodeSelectorTerm(term v1.NodeSelectorTerm, node *v1.Node) bool {
    // 구현 생략
    return true
}
```

**다른 옵션들의 설명:**
- A. In: 유효한 노드 어피니티 연산자입니다.
- B. NotIn: 유효한 노드 어피니티 연산자입니다.
- C. Exists: 유효한 노드 어피니티 연산자입니다.
</details>

### 3. Kubernetes에서 파드 토폴로지 분산 제약 조건(Pod Topology Spread Constraints)의 주요 목적은 무엇인가요?

A. 파드를 다양한 노드에 균등하게 분산  
B. 파드를 특정 노드에만 배치  
C. 파드를 특정 영역(zone)에만 배치  
D. 파드를 특정 레이블이 있는 노드에만 배치  

<details>
<summary>정답 및 설명</summary>

**정답: A. 파드를 다양한 노드에 균등하게 분산**

**설명:**
Kubernetes에서 파드 토폴로지 분산 제약 조건(Pod Topology Spread Constraints)의 주요 목적은 파드를 다양한 토폴로지 도메인(노드, 영역, 리전 등)에 균등하게 분산하는 것입니다. 이를 통해 애플리케이션의 고가용성을 향상시키고, 리소스 사용을 최적화하며, 장애 내구성을 개선할 수 있습니다.

**파드 토폴로지 분산 제약 조건의 주요 구성 요소:**
1. **maxSkew**: 토폴로지 도메인 간 파드 수의 최대 차이를 지정합니다.
2. **topologyKey**: 파드를 분산시킬 토폴로지 도메인을 정의하는 노드 레이블 키입니다.
3. **whenUnsatisfiable**: 제약 조건을 충족할 수 없을 때의 동작을 지정합니다.
   - `DoNotSchedule`: 제약 조건을 충족하지 않으면 파드를 스케줄링하지 않습니다.
   - `ScheduleAnyway`: 제약 조건을 충족하지 않아도 파드를 스케줄링합니다.
4. **labelSelector**: 분산 계산 시 고려할 기존 파드를 선택하는 레이블 셀렉터입니다.

**파드 토폴로지 분산 제약 조건 예시:**
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
    image: nginx
```

이 예시에서는 두 가지 제약 조건을 정의합니다:
1. 각 노드(`kubernetes.io/hostname`)에 있는 `app=web` 레이블이 있는 파드 수의 차이가 최대 1이어야 합니다.
2. 각 영역(`topology.kubernetes.io/zone`)에 있는 `app=web` 레이블이 있는 파드 수의 차이가 최대 2여야 합니다.

**토폴로지 분산 계산 방법:**
1. 각 토폴로지 도메인에서 레이블 셀렉터와 일치하는 파드 수를 계산합니다.
2. 가장 많은 파드가 있는 도메인과 가장 적은 파드가 있는 도메인 간의 차이를 계산합니다.
3. 이 차이가 `maxSkew`보다 크면 제약 조건을 위반한 것입니다.

**일반적인 토폴로지 키:**
1. **kubernetes.io/hostname**: 노드 수준 분산
2. **topology.kubernetes.io/zone**: 영역 수준 분산
3. **topology.kubernetes.io/region**: 리전 수준 분산
4. **node.kubernetes.io/instance-type**: 인스턴스 유형 수준 분산

**사용 사례:**
1. **고가용성**: 파드를 여러 노드, 영역, 리전에 분산하여 장애 내구성 향상
2. **리소스 균형**: 클러스터 전체에 워크로드를 균등하게 분산
3. **비용 최적화**: 특정 유형의 노드에 워크로드 분산
4. **성능 최적화**: 네트워크 지연 시간을 최소화하기 위한 분산

**Custom Scheduler에서 토폴로지 분산 처리:**
사용자 정의 스케줄러를 구현할 때는 파드의 토폴로지 분산 제약 조건을 고려해야 합니다.

```go
// 토폴로지 분산 제약 조건 검사 예시
func checkTopologySpreadConstraints(pod *v1.Pod, node *v1.Node, allPods []*v1.Pod) bool {
    constraints := pod.Spec.TopologySpreadConstraints
    if len(constraints) == 0 {
        return true  // 제약 조건이 없으면 모든 노드가 적합
    }
    
    for _, constraint := range constraints {
        // 토폴로지 키 값 가져오기
        topologyValue, ok := node.Labels[constraint.TopologyKey]
        if !ok {
            // 노드에 토폴로지 키가 없으면 이 제약 조건을 건너뜀
            if constraint.WhenUnsatisfiable == v1.DoNotSchedule {
                return false
            }
            continue
        }
        
        // 현재 토폴로지 도메인의 매칭되는 파드 수 계산
        var matchingPods int
        for _, existingPod := range allPods {
            // 파드가 레이블 셀렉터와 일치하고 같은 토폴로지 도메인에 있는지 확인
            if podMatchesLabelSelector(existingPod, constraint.LabelSelector) {
                podNode, err := getNodeForPod(existingPod)
                if err != nil {
                    continue
                }
                if podNode.Labels[constraint.TopologyKey] == topologyValue {
                    matchingPods++
                }
            }
        }
        
        // 다른 토폴로지 도메인의 파드 수 계산 및 skew 확인
        // (구현 생략)
        
        // maxSkew 위반 여부 확인
        if skew > constraint.MaxSkew && constraint.WhenUnsatisfiable == v1.DoNotSchedule {
            return false
        }
    }
    
    return true
}
```

**다른 옵션들의 문제점:**
- B. 파드를 특정 노드에만 배치: 이는 노드 셀렉터(nodeSelector) 또는 노드 어피니티(nodeAffinity)의 역할입니다.
- C. 파드를 특정 영역(zone)에만 배치: 이는 노드 어피니티를 사용하여 특정 영역에 배치하는 것이며, 토폴로지 분산 제약 조건의 주요 목적은 균등한 분산입니다.
- D. 파드를 특정 레이블이 있는 노드에만 배치: 이는 노드 셀렉터 또는 노드 어피니티의 역할입니다.
</details>
### 4. Kubernetes에서 테인트(Taint)와 톨러레이션(Toleration)의 주요 목적은 무엇인가요?

A. 특정 파드가 특정 노드에만 스케줄링되도록 보장  
B. 특정 파드가 특정 노드에 스케줄링되지 않도록 방지  
C. 노드가 특정 파드를 거부하고, 파드가 이를 허용할 수 있게 함  
D. 파드 간 통신을 제한  

<details>
<summary>정답 및 설명</summary>

**정답: C. 노드가 특정 파드를 거부하고, 파드가 이를 허용할 수 있게 함**

**설명:**
Kubernetes에서 테인트(Taint)와 톨러레이션(Toleration)의 주요 목적은 노드가 특정 파드를 거부하고, 파드가 이를 허용할 수 있게 하는 것입니다. 테인트는 노드에 적용되어 파드가 스케줄링되는 것을 방지하고, 톨러레이션은 파드에 적용되어 특정 테인트가 있는 노드에 스케줄링될 수 있게 합니다.

**테인트와 톨러레이션의 작동 방식:**
1. **테인트**: 노드에 적용되어 파드가 해당 노드에 스케줄링되는 것을 제한합니다.
2. **톨러레이션**: 파드에 적용되어 특정 테인트가 있는 노드에 스케줄링될 수 있게 합니다.
3. **효과(Effect)**: 테인트의 효과는 톨러레이션이 없는 파드에 대한 동작을 정의합니다.

**테인트 효과(Effect) 유형:**
1. **NoSchedule**: 톨러레이션이 없는 파드는 노드에 스케줄링되지 않습니다.
2. **PreferNoSchedule**: 톨러레이션이 없는 파드는 가능하면 노드에 스케줄링되지 않지만, 클러스터 리소스가 부족하면 스케줄링될 수 있습니다.
3. **NoExecute**: 톨러레이션이 없는 파드는 노드에 스케줄링되지 않으며, 이미 실행 중인 파드는 제거됩니다.

**테인트 적용 예시:**
```bash
# 노드에 테인트 적용
kubectl taint nodes node1 key=value:NoSchedule

# 노드에서 테인트 제거
kubectl taint nodes node1 key=value:NoSchedule-
```

**테인트와 톨러레이션 예시:**
```yaml
# 노드에 테인트 적용
apiVersion: v1
kind: Node
metadata:
  name: node1
spec:
  taints:
  - key: "key"
    value: "value"
    effect: "NoSchedule"

# 파드에 톨러레이션 적용
apiVersion: v1
kind: Pod
metadata:
  name: pod-with-toleration
spec:
  tolerations:
  - key: "key"
    operator: "Equal"
    value: "value"
    effect: "NoSchedule"
  containers:
  - name: nginx
    image: nginx
```

**톨러레이션 연산자(Operator):**
1. **Equal**: 키와 값이 일치해야 합니다.
2. **Exists**: 키만 일치하면 됩니다(값은 무시).

**톨러레이션 추가 필드:**
- **tolerationSeconds**: NoExecute 효과에서 파드가 제거되기 전에 노드에 남아 있을 수 있는 시간(초)을 지정합니다.

```yaml
tolerations:
- key: "node.kubernetes.io/not-ready"
  operator: "Exists"
  effect: "NoExecute"
  tolerationSeconds: 300
```

**일반적인 사용 사례:**
1. **전용 노드**: 특정 워크로드만 실행하도록 노드 예약
2. **특수 하드웨어**: GPU와 같은 특수 하드웨어가 있는 노드에 특정 파드만 스케줄링
3. **노드 유지 관리**: 노드 유지 관리 중 새 파드 스케줄링 방지
4. **마스터 노드 보호**: 컨트롤 플레인 노드에 일반 워크로드 스케줄링 방지

**시스템 테인트:**
Kubernetes는 다음과 같은 시스템 테인트를 자동으로 적용합니다:
1. **node.kubernetes.io/not-ready**: 노드가 준비되지 않은 상태
2. **node.kubernetes.io/unreachable**: 노드에 도달할 수 없음
3. **node.kubernetes.io/memory-pressure**: 노드에 메모리 압력 있음
4. **node.kubernetes.io/disk-pressure**: 노드에 디스크 압력 있음
5. **node.kubernetes.io/pid-pressure**: 노드에 PID 압력 있음
6. **node.kubernetes.io/network-unavailable**: 노드의 네트워크가 사용 불가능
7. **node.kubernetes.io/unschedulable**: 노드가 스케줄 불가능으로 표시됨

**Custom Scheduler에서 테인트와 톨러레이션 처리:**
사용자 정의 스케줄러를 구현할 때는 노드의 테인트와 파드의 톨러레이션을 고려해야 합니다.

```go
// 테인트와 톨러레이션 검사 예시
func checkTaintsAndTolerations(pod *v1.Pod, node *v1.Node) bool {
    // 노드에 테인트가 없으면 모든 파드가 스케줄링 가능
    if len(node.Spec.Taints) == 0 {
        return true
    }
    
    // 각 테인트에 대해 파드가 톨러레이션을 가지고 있는지 확인
    for _, taint := range node.Spec.Taints {
        if taint.Effect == v1.TaintEffectNoSchedule || taint.Effect == v1.TaintEffectPreferNoSchedule {
            // 파드가 이 테인트를 허용하는지 확인
            if !tolerationsTolerateTaint(pod.Spec.Tolerations, &taint) {
                return false
            }
        }
    }
    
    return true
}

// 톨러레이션이 테인트를 허용하는지 확인
func tolerationsTolerateTaint(tolerations []v1.Toleration, taint *v1.Taint) bool {
    for _, toleration := range tolerations {
        if toleration.Key == taint.Key {
            if toleration.Operator == v1.TolerationOpExists {
                return true
            } else if toleration.Operator == v1.TolerationOpEqual && toleration.Value == taint.Value {
                return true
            }
        }
    }
    return false
}
```

**다른 옵션들의 문제점:**
- A. 특정 파드가 특정 노드에만 스케줄링되도록 보장: 이는 노드 셀렉터(nodeSelector) 또는 노드 어피니티(nodeAffinity)의 역할입니다.
- B. 특정 파드가 특정 노드에 스케줄링되지 않도록 방지: 이는 파드 안티-어피니티(podAntiAffinity)의 역할입니다.
- D. 파드 간 통신을 제한: 이는 네트워크 정책(NetworkPolicy)의 역할입니다.
</details>

### 5. Kubernetes에서 스케줄러 익스텐더(Scheduler Extender)의 주요 특징이 아닌 것은 무엇인가요?

A. HTTP 웹훅을 통해 스케줄러와 통신  
B. 필터링 및 우선순위 지정 기능 제공  
C. 스케줄러 코드베이스와 직접 통합  
D. 외부 프로세스로 실행  

<details>
<summary>정답 및 설명</summary>

**정답: C. 스케줄러 코드베이스와 직접 통합**

**설명:**
Kubernetes에서 스케줄러 익스텐더(Scheduler Extender)의 주요 특징이 아닌 것은 "스케줄러 코드베이스와 직접 통합"입니다. 스케줄러 익스텐더는 스케줄러 코드베이스와 직접 통합되지 않고, HTTP 웹훅을 통해 외부 프로세스로 실행됩니다. 이는 스케줄링 프레임워크 플러그인과의 주요 차이점입니다.

**스케줄러 익스텐더의 주요 특징:**
1. **HTTP 웹훅**: 스케줄러는 HTTP 요청을 통해 익스텐더와 통신합니다.
2. **외부 프로세스**: 익스텐더는 스케줄러와 별도의 프로세스로 실행됩니다.
3. **필터링 및 우선순위 지정**: 익스텐더는 노드 필터링 및 우선순위 지정 기능을 제공할 수 있습니다.
4. **바인딩**: 익스텐더는 선택적으로 파드를 노드에 바인딩할 수 있습니다.

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
    weight: 5
    bindVerb: "bind"
    enableHTTPS: false
    nodeCacheCapable: false
    ignorable: true
    managedResources:
    - name: example.com/foo
      ignoredByScheduler: true
```

**스케줄러 익스텐더 API:**
1. **필터(Filter) API**: 노드 목록을 받아 필터링된 노드 목록을 반환합니다.
   ```
   POST /filter
   ```
   요청 본문:
   ```json
   {
     "pod": <pod>,
     "nodes": <nodes>,
     "nodenames": <node-names>
   }
   ```
   응답 본문:
   ```json
   {
     "nodes": <filtered-nodes>,
     "nodenames": <filtered-node-names>,
     "failedNodes": <failed-nodes>,
     "error": <error-message>
   }
   ```

2. **우선순위 지정(Prioritize) API**: 노드 목록을 받아 각 노드에 점수를 할당합니다.
   ```
   POST /prioritize
   ```
   요청 본문:
   ```json
   {
     "pod": <pod>,
     "nodes": <nodes>,
     "nodenames": <node-names>
   }
   ```
   응답 본문:
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

3. **바인드(Bind) API**: 파드를 노드에 바인딩합니다.
   ```
   POST /bind
   ```
   요청 본문:
   ```json
   {
     "pod": <pod>,
     "node": <node-name>
   }
   ```
   응답 본문:
   ```json
   {
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

func main() {
    http.HandleFunc("/filter", filterHandler)
    http.HandleFunc("/prioritize", prioritizeHandler)
    
    log.Fatal(http.ListenAndServe(":8080", nil))
}
```

**스케줄러 익스텐더 vs 스케줄링 프레임워크 플러그인:**

| 특징 | 스케줄러 익스텐더 | 스케줄링 프레임워크 플러그인 |
|------|-------------------|---------------------------|
| 통합 방식 | HTTP 웹훅 | 코드베이스 직접 통합 |
| 실행 모드 | 외부 프로세스 | 스케줄러 내부 |
| 성능 | HTTP 오버헤드로 인해 상대적으로 느림 | 직접 통합으로 더 빠름 |
| 개발 언어 | 제한 없음 | Go |
| 배포 | 별도 서비스 | 스케줄러와 함께 배포 |
| 유지 관리 | 스케줄러와 독립적 | 스케줄러 버전과 연결됨 |

**스케줄러 익스텐더의 장단점:**
장점:
- 스케줄러 코드베이스와 독립적으로 개발 가능
- 다양한 프로그래밍 언어로 구현 가능
- 스케줄러 업그레이드에 영향을 덜 받음

단점:
- HTTP 통신 오버헤드로 인한 성능 저하
- 스케줄링 사이클의 일부 단계만 확장 가능
- 스케줄러와 익스텐더 간의 통신 실패 가능성

**다른 옵션들의 설명:**
- A. HTTP 웹훅을 통해 스케줄러와 통신: 스케줄러 익스텐더의 유효한 특징입니다.
- B. 필터링 및 우선순위 지정 기능 제공: 스케줄러 익스텐더의 유효한 특징입니다.
- D. 외부 프로세스로 실행: 스케줄러 익스텐더의 유효한 특징입니다.
</details>
### 6. Kubernetes에서 파드 어피니티(Pod Affinity)와 안티-어피니티(Anti-Affinity)의 주요 목적은 무엇인가요?

A. 파드와 노드 간의 관계 정의  
B. 파드와 볼륨 간의 관계 정의  
C. 파드 간의 관계 정의  
D. 파드와 서비스 간의 관계 정의  

<details>
<summary>정답 및 설명</summary>

**정답: C. 파드 간의 관계 정의**

**설명:**
Kubernetes에서 파드 어피니티(Pod Affinity)와 안티-어피니티(Anti-Affinity)의 주요 목적은 파드 간의 관계를 정의하는 것입니다. 이를 통해 특정 파드가 다른 파드와 같은 토폴로지 도메인(노드, 영역, 리전 등)에 배치되거나(어피니티) 또는 배치되지 않도록(안티-어피니티) 제어할 수 있습니다.

**파드 어피니티와 안티-어피니티의 주요 구성 요소:**
1. **topologyKey**: 파드 간의 관계를 정의하는 토폴로지 도메인을 지정하는 노드 레이블 키입니다.
2. **labelSelector**: 관계를 맺을 파드를 선택하는 레이블 셀렉터입니다.
3. **namespaces**: 레이블 셀렉터가 적용될 네임스페이스 목록입니다.

**파드 어피니티 유형:**
1. **requiredDuringSchedulingIgnoredDuringExecution**: 파드가 스케줄링되기 위해 반드시 충족해야 하는 규칙입니다(하드 요구 사항).
2. **preferredDuringSchedulingIgnoredDuringExecution**: 가능하면 충족하는 것이 좋지만, 필수는 아닌 규칙입니다(소프트 요구 사항).

**파드 어피니티 예시:**
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

이 예시에서:
1. **파드 어피니티**: 웹 서버 파드는 `app=cache` 레이블이 있는 파드와 같은 노드(`kubernetes.io/hostname`)에 스케줄링되어야 합니다.
2. **파드 안티-어피니티**: 웹 서버 파드는 가능하면 다른 `app=web` 레이블이 있는 파드와 다른 노드에 스케줄링되는 것이 좋습니다.

**일반적인 토폴로지 키:**
1. **kubernetes.io/hostname**: 노드 수준 관계
2. **topology.kubernetes.io/zone**: 영역 수준 관계
3. **topology.kubernetes.io/region**: 리전 수준 관계

**사용 사례:**
1. **고가용성**: 같은 애플리케이션의 인스턴스를 다른 노드, 영역, 리전에 분산
2. **성능 최적화**: 서로 통신하는 파드를 같은 노드에 배치하여 지연 시간 최소화
3. **리소스 격리**: 리소스를 많이 사용하는 파드를 서로 다른 노드에 분산
4. **라이선스 제한**: 라이선스 제한이 있는 애플리케이션을 특정 노드에 집중

**파드 어피니티 vs 노드 어피니티:**
- **노드 어피니티**: 파드와 노드 간의 관계를 정의합니다.
- **파드 어피니티**: 파드 간의 관계를 정의합니다.

**파드 어피니티와 안티-어피니티의 성능 영향:**
파드 어피니티와 안티-어피니티는 모든 노드와 파드를 고려해야 하므로 계산 비용이 높을 수 있습니다. 특히 대규모 클러스터에서는 스케줄링 성능에 영향을 줄 수 있으므로 신중하게 사용해야 합니다.

**Custom Scheduler에서 파드 어피니티 처리:**
사용자 정의 스케줄러를 구현할 때는 파드의 어피니티와 안티-어피니티 요구 사항을 고려해야 합니다.

```go
// 파드 어피니티 검사 예시
func checkPodAffinity(pod *v1.Pod, node *v1.Node, allPods []*v1.Pod) bool {
    affinity := pod.Spec.Affinity
    if affinity == nil || affinity.PodAffinity == nil {
        return true  // 파드 어피니티가 없으면 모든 노드가 적합
    }
    
    // 필수 파드 어피니티 검사
    for _, term := range affinity.PodAffinity.RequiredDuringSchedulingIgnoredDuringExecution {
        if !satisfiesPodAffinityTerm(pod, node, term, allPods) {
            return false
        }
    }
    
    return true
}

// 파드 안티-어피니티 검사 예시
func checkPodAntiAffinity(pod *v1.Pod, node *v1.Node, allPods []*v1.Pod) bool {
    affinity := pod.Spec.Affinity
    if affinity == nil || affinity.PodAntiAffinity == nil {
        return true  // 파드 안티-어피니티가 없으면 모든 노드가 적합
    }
    
    // 필수 파드 안티-어피니티 검사
    for _, term := range affinity.PodAntiAffinity.RequiredDuringSchedulingIgnoredDuringExecution {
        if satisfiesPodAffinityTerm(pod, node, term, allPods) {
            return false
        }
    }
    
    return true
}

// 파드 어피니티 조건 충족 여부 확인
func satisfiesPodAffinityTerm(pod *v1.Pod, node *v1.Node, term v1.PodAffinityTerm, allPods []*v1.Pod) bool {
    // 구현 생략
    return true
}
```

**다른 옵션들의 문제점:**
- A. 파드와 노드 간의 관계 정의: 이는 노드 어피니티(nodeAffinity)의 역할입니다.
- B. 파드와 볼륨 간의 관계 정의: 이는 볼륨 바인딩 및 PersistentVolumeClaim의 역할입니다.
- D. 파드와 서비스 간의 관계 정의: 이는 서비스의 레이블 셀렉터를 통해 처리됩니다.
</details>

### 7. Kubernetes 스케줄러에서 "QueueSort" 확장 포인트의 역할은 무엇인가요?

A. 노드에 점수 부여  
B. 파드를 실행할 수 없는 노드 제외  
C. 스케줄링 큐에서 파드 정렬  
D. 파드를 노드에 바인딩  

<details>
<summary>정답 및 설명</summary>

**정답: C. 스케줄링 큐에서 파드 정렬**

**설명:**
Kubernetes 스케줄링 프레임워크에서 "QueueSort" 확장 포인트의 역할은 스케줄링 큐에서 파드를 정렬하는 것입니다. 이 확장 포인트는 어떤 파드가 먼저 스케줄링될지 결정하는 우선순위를 설정합니다.

**스케줄링 큐와 QueueSort:**
스케줄러는 스케줄링 큐에 있는 파드를 하나씩 처리합니다. QueueSort 플러그인은 이 큐에서 파드의 순서를 결정합니다. 기본적으로 Kubernetes는 `PrioritySort` 플러그인을 사용하여 파드의 우선순위(priority)에 따라 정렬합니다.

**QueueSort 플러그인 인터페이스:**
```go
type QueueSortPlugin interface {
    Plugin
    // Less는 두 파드 중 어느 것이 먼저 스케줄링되어야 하는지 결정합니다.
    // pInfo1이 pInfo2보다 먼저 스케줄링되어야 하면 true를 반환합니다.
    Less(*QueuedPodInfo, *QueuedPodInfo) bool
}
```

**기본 QueueSort 플러그인 - PrioritySort:**
```go
// PrioritySort는 파드 우선순위에 따라 파드를 정렬합니다.
type PrioritySort struct{}

// Name은 플러그인 이름을 반환합니다.
func (pl *PrioritySort) Name() string {
    return Name
}

// Less는 두 파드 중 어느 것이 먼저 스케줄링되어야 하는지 결정합니다.
func (pl *PrioritySort) Less(pInfo1, pInfo2 *framework.QueuedPodInfo) bool {
    p1 := getPodPriority(pInfo1.Pod)
    p2 := getPodPriority(pInfo2.Pod)
    
    // 우선순위가 높은 파드가 먼저 스케줄링됩니다.
    if p1 != p2 {
        return p1 > p2
    }
    
    // 우선순위가 같으면 대기 시간이 긴 파드가 먼저 스케줄링됩니다.
    return pInfo1.Timestamp.Before(pInfo2.Timestamp)
}
```

**사용자 정의 QueueSort 플러그인 예시:**
```go
// CustomQueueSort는 사용자 정의 정렬 로직을 구현합니다.
type CustomQueueSort struct{}

// Name은 플러그인 이름을 반환합니다.
func (pl *CustomQueueSort) Name() string {
    return "CustomQueueSort"
}

// Less는 두 파드 중 어느 것이 먼저 스케줄링되어야 하는지 결정합니다.
func (pl *CustomQueueSort) Less(pInfo1, pInfo2 *framework.QueuedPodInfo) bool {
    // 예: 특정 네임스페이스의 파드를 우선시
    if pInfo1.Pod.Namespace == "high-priority-namespace" && pInfo2.Pod.Namespace != "high-priority-namespace" {
        return true
    }
    if pInfo1.Pod.Namespace != "high-priority-namespace" && pInfo2.Pod.Namespace == "high-priority-namespace" {
        return false
    }
    
    // 예: 특정 레이블이 있는 파드를 우선시
    if hasLabel(pInfo1.Pod, "critical") && !hasLabel(pInfo2.Pod, "critical") {
        return true
    }
    if !hasLabel(pInfo1.Pod, "critical") && hasLabel(pInfo2.Pod, "critical") {
        return false
    }
    
    // 기본적으로 우선순위와 대기 시간을 고려
    p1 := getPodPriority(pInfo1.Pod)
    p2 := getPodPriority(pInfo2.Pod)
    
    if p1 != p2 {
        return p1 > p2
    }
    
    return pInfo1.Timestamp.Before(pInfo2.Timestamp)
}

// 파드에 특정 레이블이 있는지 확인
func hasLabel(pod *v1.Pod, label string) bool {
    _, exists := pod.Labels[label]
    return exists
}
```

**스케줄러 구성에서 QueueSort 플러그인 활성화:**
```yaml
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
profiles:
- schedulerName: custom-scheduler
  plugins:
    queueSort:
      enabled:
      - name: CustomQueueSort
      disabled:
      - name: PrioritySort  # 기본 플러그인 비활성화
```

**QueueSort 플러그인의 특징:**
1. **단일 활성화**: 한 번에 하나의 QueueSort 플러그인만 활성화할 수 있습니다.
2. **전역 영향**: QueueSort 플러그인은 스케줄링 큐의 모든 파드에 영향을 미칩니다.
3. **성능 중요성**: 효율적인 정렬 알고리즘이 중요하며, 복잡한 로직은 스케줄링 성능에 영향을 줄 수 있습니다.

**QueueSort 플러그인 사용 사례:**
1. **비즈니스 우선순위**: 비즈니스 중요도에 따라 파드 정렬
2. **리소스 효율성**: 리소스 요청이 적은 파드를 먼저 스케줄링하여 빈 공간 활용
3. **서비스 수준 계약(SLA)**: SLA 요구 사항에 따라 파드 정렬
4. **배치 처리**: 배치 작업과 대화형 작업 간의 우선순위 조정

**스케줄링 큐 모니터링:**
```bash
# 스케줄러 로그에서 큐 정보 확인
kubectl logs -n kube-system <scheduler-pod> | grep -i queue

# 스케줄링 대기 중인 파드 확인
kubectl get pods --all-namespaces -o wide | grep -i pending
```

**다른 옵션들의 문제점:**
- A. 노드에 점수 부여: 이는 "Score" 확장 포인트의 역할입니다.
- B. 파드를 실행할 수 없는 노드 제외: 이는 "Filter" 확장 포인트의 역할입니다.
- D. 파드를 노드에 바인딩: 이는 "Bind" 확장 포인트의 역할입니다.
</details>
### 8. Kubernetes에서 파드 우선순위 선점(Pod Priority Preemption)의 주요 목적은 무엇인가요?

A. 우선순위가 높은 파드가 스케줄링될 수 있도록 우선순위가 낮은 파드 제거  
B. 우선순위가 높은 파드에 더 많은 리소스 할당  
C. 우선순위가 높은 파드를 더 빠르게 실행  
D. 우선순위가 높은 파드를 특정 노드에만 배치  

<details>
<summary>정답 및 설명</summary>

**정답: A. 우선순위가 높은 파드가 스케줄링될 수 있도록 우선순위가 낮은 파드 제거**

**설명:**
Kubernetes에서 파드 우선순위 선점(Pod Priority Preemption)의 주요 목적은 우선순위가 높은 파드가 스케줄링될 수 있도록 우선순위가 낮은 파드를 제거하는 것입니다. 클러스터 리소스가 부족하여 우선순위가 높은 파드를 스케줄링할 수 없는 경우, 스케줄러는 우선순위가 낮은 파드를 선점(제거)하여 공간을 확보합니다.

**파드 우선순위 및 선점 메커니즘:**
1. **PriorityClass 정의**: 파드의 우선순위를 정의하는 클러스터 수준 리소스입니다.
2. **파드에 우선순위 할당**: 파드는 `spec.priorityClassName`을 통해 PriorityClass를 참조합니다.
3. **스케줄링 순서**: 우선순위가 높은 파드가 스케줄링 큐에서 우선적으로 처리됩니다.
4. **선점 프로세스**: 우선순위가 높은 파드를 스케줄링할 수 없는 경우, 스케줄러는 우선순위가 낮은 파드를 제거하여 공간을 확보합니다.

**PriorityClass 예시:**
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

**파드에 우선순위 적용:**
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

**선점 정책:**
PriorityClass에는 `preemptionPolicy` 필드가 있으며, 다음 값을 가질 수 있습니다:
1. **PreemptLowerPriority(기본값)**: 우선순위가 낮은 파드를 선점할 수 있습니다.
2. **Never**: 우선순위가 낮은 파드를 선점하지 않습니다.

```yaml
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: high-priority-no-preemption
value: 1000000
globalDefault: false
description: "High priority pods that do not preempt other pods"
preemptionPolicy: Never  # 선점하지 않음
```

**선점 프로세스:**
1. 스케줄러는 우선순위가 높은 파드를 스케줄링하려고 시도합니다.
2. 적합한 노드가 없으면, 스케줄러는 각 노드에서 선점 후보 파드를 식별합니다.
3. 선점 후보는 우선순위가 낮은 파드 중에서 선택됩니다.
4. 스케줄러는 최소한의 파드를 선점하여 필요한 리소스를 확보합니다.
5. 선택된 파드는 정상적으로 종료(graceful termination)됩니다.
6. 선점된 파드가 종료되면, 우선순위가 높은 파드가 스케줄링됩니다.

**선점 고려 사항:**
1. **그레이스풀 종료 기간**: 선점된 파드는 `terminationGracePeriodSeconds`(기본값: 30초) 동안 정상 종료 시간을 갖습니다.
2. **파드 중단 예산(PDB)**: 스케줄러는 가능한 한 PDB를 위반하지 않으려고 합니다.
3. **노드 테인트**: 선점 후 노드에 테인트가 추가되어 새 파드가 스케줄링되는 것을 방지할 수 있습니다.
4. **시스템 파드**: 시스템 중요 파드는 일반적으로 매우 높은 우선순위를 가지며 선점되지 않습니다.

**선점 이벤트 확인:**
```bash
# 선점 이벤트 확인
kubectl get events | grep -i preempt
```

**선점 관련 지표 모니터링:**
```bash
# 스케줄러 메트릭에서 선점 관련 지표 확인
kubectl get --raw /metrics | grep scheduler_preemption
```

**Custom Scheduler에서 선점 구현:**
사용자 정의 스케줄러를 구현할 때는 파드 우선순위와 선점 메커니즘을 고려해야 합니다.

```go
// 선점 로직 예시
func preempt(pod *v1.Pod, nodes []*v1.Node) *v1.Node {
    // 파드 우선순위 확인
    podPriority := getPodPriority(pod)
    
    // 각 노드에서 선점 가능한 파드 식별
    for _, node := range nodes {
        // 노드에서 실행 중인 파드 가져오기
        nodePods := getPodsOnNode(node)
        
        // 선점 후보 파드 식별
        var victims []*v1.Pod
        for _, p := range nodePods {
            // 우선순위가 낮은 파드만 선택
            if getPodPriority(p) < podPriority {
                victims = append(victims, p)
            }
        }
        
        // 선점 후 리소스가 충분한지 확인
        if hasEnoughResourcesAfterPreemption(node, victims, pod) {
            // 선점 실행
            for _, victim := range victims {
                evictPod(victim)
            }
            return node
        }
    }
    
    return nil  // 적합한 노드를 찾지 못함
}
```

**선점의 장단점:**
장점:
- 중요한 워크로드의 스케줄링 보장
- 클러스터 리소스의 효율적인 활용
- 서비스 수준 계약(SLA) 준수 지원

단점:
- 선점된 파드의 중단
- 선점 후 재스케줄링으로 인한 오버헤드
- 복잡한 선점 결정 로직

**다른 옵션들의 문제점:**
- B. 우선순위가 높은 파드에 더 많은 리소스 할당: 파드 우선순위는 리소스 할당량에 직접적인 영향을 주지 않습니다. 리소스 요청과 제한은 파드 스펙에서 별도로 정의됩니다.
- C. 우선순위가 높은 파드를 더 빠르게 실행: 우선순위는 스케줄링 순서에 영향을 주지만, 파드 실행 속도 자체를 변경하지는 않습니다.
- D. 우선순위가 높은 파드를 특정 노드에만 배치: 이는 노드 셀렉터 또는 노드 어피니티의 역할이며, 우선순위와는 직접적인 관련이 없습니다.
</details>

### 9. Kubernetes 스케줄러에서 "PreFilter" 확장 포인트의 역할은 무엇인가요?

A. 필터링 전에 파드 및 클러스터 상태에 대한 사전 처리 수행  
B. 필터링 후에 노드에 점수 부여  
C. 파드를 노드에 바인딩하기 전에 검증 수행  
D. 스케줄링 큐에서 파드 정렬  

<details>
<summary>정답 및 설명</summary>

**정답: A. 필터링 전에 파드 및 클러스터 상태에 대한 사전 처리 수행**

**설명:**
Kubernetes 스케줄링 프레임워크에서 "PreFilter" 확장 포인트의 역할은 필터링 전에 파드 및 클러스터 상태에 대한 사전 처리를 수행하는 것입니다. PreFilter 플러그인은 필터링 단계에서 사용할 데이터를 준비하고, 파드가 스케줄링 가능한지 여부를 미리 확인할 수 있습니다.

**PreFilter 확장 포인트의 주요 기능:**
1. **데이터 준비**: 필터링 단계에서 사용할 데이터 구조를 초기화하고 준비합니다.
2. **사전 검사**: 파드가 스케줄링 가능한지 여부를 미리 확인합니다.
3. **상태 저장**: 스케줄링 사이클 동안 사용할 상태 정보를 저장합니다.
4. **최적화**: 불필요한 필터링 작업을 방지하여 성능을 최적화합니다.

**PreFilter 플러그인 인터페이스:**
```go
type PreFilterPlugin interface {
    Plugin
    // PreFilter는 필터링 전에 파드에 대한 사전 처리를 수행합니다.
    PreFilter(ctx context.Context, state *CycleState, pod *v1.Pod) *Status
    // PreFilterExtensions는 추가 기능을 제공하는 인터페이스를 반환합니다.
    PreFilterExtensions() PreFilterExtensions
}

type PreFilterExtensions interface {
    // AddPod는 노드에 파드가 추가될 때 상태를 업데이트합니다.
    AddPod(ctx context.Context, state *CycleState, podToAdd *v1.Pod, nodeInfo *NodeInfo) *Status
    // RemovePod는 노드에서 파드가 제거될 때 상태를 업데이트합니다.
    RemovePod(ctx context.Context, state *CycleState, podToRemove *v1.Pod, nodeInfo *NodeInfo) *Status
}
```

**기본 PreFilter 플러그인:**
Kubernetes는 다음과 같은 기본 PreFilter 플러그인을 제공합니다:

1. **InterPodAffinity**: 파드 간 어피니티 및 안티-어피니티 요구 사항을 처리합니다.
2. **NodeAffinity**: 노드 어피니티 요구 사항을 처리합니다.
3. **NodePorts**: 파드가 요청한 호스트 포트를 처리합니다.
4. **NodeResourcesFit**: 노드 리소스 요구 사항을 처리합니다.
5. **PodTopologySpread**: 파드 토폴로지 분산 제약 조건을 처리합니다.
6. **VolumeBinding**: 볼륨 바인딩 요구 사항을 처리합니다.

**사용자 정의 PreFilter 플러그인 예시:**
```go
// CustomPreFilter는 사용자 정의 사전 필터링 로직을 구현합니다.
type CustomPreFilter struct {
    handle framework.Handle
}

// Name은 플러그인 이름을 반환합니다.
func (pl *CustomPreFilter) Name() string {
    return "CustomPreFilter"
}

// PreFilter는 필터링 전에 파드에 대한 사전 처리를 수행합니다.
func (pl *CustomPreFilter) PreFilter(ctx context.Context, state *framework.CycleState, pod *v1.Pod) *framework.Status {
    // 예: 특정 조건에 따라 파드가 스케줄링 가능한지 확인
    if !isPodSchedulable(pod) {
        return framework.NewStatus(framework.Unschedulable, "Pod does not meet custom requirements")
    }
    
    // 예: 필터링 단계에서 사용할 데이터 저장
    data := &customPreFilterState{
        // 필요한 데이터 초기화
    }
    state.Write(stateKey, data)
    
    return nil
}

// PreFilterExtensions는 추가 기능을 제공하는 인터페이스를 반환합니다.
func (pl *CustomPreFilter) PreFilterExtensions() framework.PreFilterExtensions {
    return nil  // 확장 기능이 필요 없으면 nil 반환
}

// 상태 데이터 구조
type customPreFilterState struct {
    // 필요한 필드 정의
}

// 상태 키
var stateKey = framework.StateKey("CustomPreFilter")

// 파드가 스케줄링 가능한지 확인하는 함수
func isPodSchedulable(pod *v1.Pod) bool {
    // 사용자 정의 로직 구현
    return true
}
```

**스케줄러 구성에서 PreFilter 플러그인 활성화:**
```yaml
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
profiles:
- schedulerName: custom-scheduler
  plugins:
    preFilter:
      enabled:
      - name: CustomPreFilter
      disabled:
      - name: NodeResourcesFit  # 기본 플러그인 비활성화
```

**PreFilter와 Filter의 관계:**
1. **PreFilter**: 모든 노드에 대한 필터링을 시작하기 전에 한 번 실행됩니다.
2. **Filter**: 각 노드에 대해 개별적으로 실행됩니다.

PreFilter는 Filter 단계에서 사용할 데이터를 준비하고, 파드가 어떤 노드에도 스케줄링될 수 없는 경우를 미리 식별하여 불필요한 필터링 작업을 방지합니다.

**PreFilter 사용 사례:**
1. **복잡한 제약 조건 처리**: 파드 간 어피니티, 토폴로지 분산 등의 복잡한 제약 조건을 효율적으로 처리
2. **사전 검증**: 파드가 스케줄링 가능한지 여부를 미리 확인하여 불필요한 처리 방지
3. **데이터 캐싱**: 필터링 단계에서 반복적으로 사용되는 데이터를 미리 계산하여 성능 향상
4. **상태 공유**: 여러 플러그인 간에 공유되는 상태 정보 관리

**다른 옵션들의 문제점:**
- B. 필터링 후에 노드에 점수 부여: 이는 "Score" 확장 포인트의 역할입니다.
- C. 파드를 노드에 바인딩하기 전에 검증 수행: 이는 "PreBind" 확장 포인트의 역할입니다.
- D. 스케줄링 큐에서 파드 정렬: 이는 "QueueSort" 확장 포인트의 역할입니다.
</details>

### 10. Kubernetes에서 노드 테인트(Node Taint) `node.kubernetes.io/unreachable:NoExecute`의 의미는 무엇인가요?

A. 노드에 도달할 수 없으며, 톨러레이션이 없는 파드는 제거됨  
B. 노드가 스케줄링 불가능하지만, 기존 파드는 계속 실행됨  
C. 노드가 유지 관리 모드이며, 새 파드는 스케줄링되지 않음  
D. 노드가 리소스 부족 상태이며, 새 파드는 가능하면 스케줄링되지 않음  

<details>
<summary>정답 및 설명</summary>

**정답: A. 노드에 도달할 수 없으며, 톨러레이션이 없는 파드는 제거됨**

**설명:**
Kubernetes에서 노드 테인트(Node Taint) `node.kubernetes.io/unreachable:NoExecute`의 의미는 노드에 도달할 수 없으며, 이 테인트에 대한 톨러레이션이 없는 파드는 노드에서 제거(축출)된다는 것입니다. 이 테인트는 노드 컨트롤러에 의해 자동으로 추가되며, 노드의 상태가 `Ready` 상태에서 `Unknown` 상태로 변경될 때 적용됩니다.

**노드 도달 불가능 상태:**
노드가 도달 불가능한 상태가 되는 일반적인 원인:
1. 네트워크 연결 문제
2. kubelet 프로세스 중단
3. 노드 시스템 장애
4. 노드 전원 문제

**테인트 구성 요소:**
1. **키(Key)**: `node.kubernetes.io/unreachable`
2. **값(Value)**: 일반적으로 빈 문자열이지만, 값이 있을 수도 있습니다.
3. **효과(Effect)**: `NoExecute` - 톨러레이션이 없는 파드는 노드에서 제거됩니다.

**NoExecute 효과:**
`NoExecute` 효과는 다음과 같은 동작을 유발합니다:
1. 테인트가 있는 노드에 새 파드가 스케줄링되지 않습니다.
2. 이미 노드에서 실행 중인 파드 중 해당 테인트에 대한 톨러레이션이 없는 파드는 제거됩니다.

**시스템 테인트:**
Kubernetes는 노드 상태에 따라 다음과 같은 시스템 테인트를 자동으로 추가합니다:
1. **node.kubernetes.io/not-ready:NoExecute**: 노드가 준비되지 않은 상태
2. **node.kubernetes.io/unreachable:NoExecute**: 노드에 도달할 수 없음
3. **node.kubernetes.io/memory-pressure:NoSchedule**: 노드에 메모리 압력 있음
4. **node.kubernetes.io/disk-pressure:NoSchedule**: 노드에 디스크 압력 있음
5. **node.kubernetes.io/pid-pressure:NoSchedule**: 노드에 PID 압력 있음
6. **node.kubernetes.io/network-unavailable:NoSchedule**: 노드의 네트워크가 사용 불가능
7. **node.kubernetes.io/unschedulable:NoSchedule**: 노드가 스케줄 불가능으로 표시됨

**기본 톨러레이션:**
Kubernetes는 모든 파드에 다음과 같은 기본 톨러레이션을 자동으로 추가합니다:
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

이러한 기본 톨러레이션은 파드가 노드가 준비되지 않거나 도달할 수 없는 상태가 되었을 때 즉시 제거되지 않고, 5분(300초) 동안 노드에 남아 있을 수 있게 합니다. 이는 일시적인 네트워크 문제로 인한 불필요한 파드 재스케줄링을 방지합니다.

**사용자 정의 톨러레이션:**
중요한 워크로드의 경우, 더 긴 톨러레이션 시간을 설정할 수 있습니다:
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
    tolerationSeconds: 600  # 10분 동안 톨러레이션
  containers:
  - name: nginx
    image: nginx
```

**노드 컨트롤러 설정:**
노드 컨트롤러는 다음과 같은 설정을 통해 노드 상태 변경 및 테인트 적용 동작을 제어합니다:
1. **--node-monitor-period**: 노드 상태를 확인하는 주기(기본값: 5초)
2. **--node-monitor-grace-period**: 노드를 `Unknown` 상태로 표시하기 전의 대기 시간(기본값: 40초)
3. **--pod-eviction-timeout**: `Unknown` 또는 `NotReady` 상태의 노드에서 파드를 제거하기 전의 대기 시간(기본값: 5분)

**노드 상태 및 테인트 확인:**
```bash
# 노드 상태 확인
kubectl get nodes

# 노드 세부 정보 확인
kubectl describe node <node-name>

# 노드 테인트 확인
kubectl get node <node-name> -o jsonpath='{.spec.taints}'
```

**파드 톨러레이션 확인:**
```bash
# 파드 톨러레이션 확인
kubectl get pod <pod-name> -o jsonpath='{.spec.tolerations}'
```

**Custom Scheduler에서 테인트 처리:**
사용자 정의 스케줄러를 구현할 때는 노드의 테인트와 파드의 톨러레이션을 고려해야 합니다.

```go
// 테인트 처리 예시
func checkNodeUnreachableTaint(node *v1.Node) bool {
    for _, taint := range node.Spec.Taints {
        if taint.Key == "node.kubernetes.io/unreachable" && taint.Effect == v1.TaintEffectNoExecute {
            return true  // 노드에 unreachable 테인트가 있음
        }
    }
    return false
}
```

**다른 옵션들의 문제점:**
- B. 노드가 스케줄링 불가능하지만, 기존 파드는 계속 실행됨: 이는 `NoSchedule` 효과의 동작이며, `NoExecute` 효과는 톨러레이션이 없는 기존 파드도 제거합니다.
- C. 노드가 유지 관리 모드이며, 새 파드는 스케줄링되지 않음: 이는 일반적으로 `node.kubernetes.io/unschedulable:NoSchedule` 테인트의 동작입니다.
- D. 노드가 리소스 부족 상태이며, 새 파드는 가능하면 스케줄링되지 않음: 이는 `PreferNoSchedule` 효과의 동작이며, 리소스 부족은 일반적으로 `node.kubernetes.io/memory-pressure` 또는 `node.kubernetes.io/disk-pressure` 테인트로 표시됩니다.
</details>
