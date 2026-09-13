# Custom Scheduler 퀴즈 (Part 2)

> **예제 기준 버전**: Kubernetes 1.35.8, Go 1.27.1
> **마지막 업데이트**: 2026년 9월 11일

이 퀴즈는 Kubernetes에서 Custom Scheduler를 구현하고 사용하는 방법에 대한 심화 이해를 테스트합니다.

## 퀴즈 문제

### 1. Kubernetes 스케줄링 프레임워크에서 "Bind" 확장 포인트의 역할은 무엇인가요?

A. 파드를 노드에 바인딩하여 스케줄링 결정 확정  
B. 파드와 노드 간의 네트워크 바인딩 설정  
C. 파드와 서비스 간의 바인딩 생성  
D. 파드와 볼륨 간의 바인딩 설정  

<details>
<summary>정답 보기</summary>

**정답: A. 파드를 노드에 바인딩하여 스케줄링 결정 확정**

**설명:**
Kubernetes 스케줄링 프레임워크에서 "Bind" 확장 포인트의 역할은 파드를 선택된 노드에 바인딩하여 스케줄링 결정을 확정하는 것입니다. Bind는 바인딩 사이클에서 할당을 확정하는 단계입니다. 이후 PostBind가 실행되며 kubelet에서는 이미지·스토리지·런타임 오류가 여전히 발생할 수 있습니다.

**바인딩 프로세스:**
1. 스케줄러가 필터링 및 스코어링을 통해 최적의 노드를 선택합니다.
2. 선택된 노드에 파드를 예약(reserve)합니다.
3. 바인딩 단계에서 파드의 `spec.nodeName` 필드를 선택된 노드의 이름으로 업데이트합니다.
4. 업데이트된 파드 정보가 API 서버에 저장됩니다.
5. kubelet이 파드 정보를 감지하고 해당 노드에서 파드를 실행합니다.

**바인딩 요청 예시:**
바인딩은 노드 선택·assume/reserve·Permit·PreBind 이후 바인딩 사이클에서 수행됩니다. 할당 기록이며 컨테이너 시작 성공을 뜻하지 않습니다. 대상 버전의 API 캐시 경로·오류 처리를 지원하는 upstream `DefaultBinder`를 유지하세요. 아래 완전한 함수는 요청의 식별 정보만 구성하며 전송하지 않습니다:

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

Pod UID는 삭제된 Pod와 같은 이름으로 새로 생성된 Pod를 혼동하지 않도록 합니다. 바인딩 요청 자체가 리소스·affinity·taint를 검사하지 않으며 앞선 전체 스케줄러 파이프라인이 이를 담당합니다.

**기본 바인더 설정:**
아래는 `DefaultBinder`를 포함한 기본값을 유지하며 등록되지 않은 커스텀 바인더를 활성화하지 않습니다.

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
- D. 파드와 볼륨 간의 바인딩 설정: PV/PVC 바인딩과 CSI 프로비저닝은 스토리지 컨트롤러 및 delayed binding을 포함한 스케줄러 VolumeBinding 플러그인과 연계됩니다. Pod와 노드의 Bind는 별도 작업입니다.
</details>

### 2. 다음 중 Kubernetes에서 노드 어피니티(Node Affinity)와 관련이 없는 연산자는 무엇인가요?

A. In  
B. NotIn  
C. Exists  
D. Contains  

<details>
<summary>정답 보기</summary>

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
    image: nginx:1.30.4
```

**노드 어피니티 유형:**
1. **requiredDuringSchedulingIgnoredDuringExecution**: 파드가 노드에 스케줄링되기 위해 반드시 충족해야 하는 규칙입니다(하드 요구 사항).
2. **preferredDuringSchedulingIgnoredDuringExecution**: 가능하면 충족하는 것이 좋지만, 필수는 아닌 규칙입니다(소프트 요구 사항).

**연산자 사용 예시:**
1. **In 연산자**:
   ```yaml
   - key: topology.kubernetes.io/zone
     operator: In
     values:
     - us-east-1a
     - us-east-1b
   ```
   노드의 `topology.kubernetes.io/zone` 레이블 값이 `us-east-1a` 또는 `us-east-1b`여야 합니다.

2. **NotIn 연산자**:
   ```yaml
   - key: topology.kubernetes.io/zone
     operator: NotIn
     values:
     - us-east-1c
   ```
   노드의 `topology.kubernetes.io/zone` 레이블 값이 `us-east-1c`가 아니어야 합니다.

3. **Exists 연산자**:
   ```yaml
   - key: topology.kubernetes.io/zone
     operator: Exists
   ```
   노드에 `topology.kubernetes.io/zone` 레이블이 존재해야 합니다.

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

**필수 노드 affinity 확인:**
기본 `NodeAffinity` 플러그인을 유지합니다. 읽기 전용 함수에서는 항상 true를 반환하는 `matchNodeSelectorTerm` 대신 버전에 맞는 도우미를 사용합니다.

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

`nodeSelector`와 required node affinity는 모두 일치해야 합니다. term 사이는 OR, 한 term의 expression 사이는 AND이며 빈 term은 어느 노드에도 일치하지 않습니다. `NotIn`은 키가 없는 노드도 일치하므로 존재가 필수이면 `Exists`도 추가하세요. `Gt`·`Lt`는 비교할 정수 값 하나와 정수 노드 레이블 값을 요구합니다. `IgnoredDuringExecution`은 이후 레이블 변경만으로 배치된 Pod를 축출하지 않는다는 뜻입니다. 프로필의 `addedAffinity`는 스케줄러 플러그인이 계속 처리합니다.

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
<summary>정답 보기</summary>

**정답: A. 파드를 다양한 노드에 균등하게 분산**

**설명:**
topology spread는 들어오는 각 Pod의 적격 도메인별 배치를 제약합니다. 장애 내구성에 도움을 줄 수 있지만 기존 Pod를 재분산하거나 지연 시간·용량·가용성을 보장하지 않습니다.

**주요 필드:**
1. **maxSkew**: `DoNotSchedule`에서는 신규 Pod가 배치될 후보 도메인 개수와 적격 전체 최소값 사이의 차이를 제한합니다.
2. **topologyKey**: 도메인을 정의하는 노드 레이블입니다.
3. **whenUnsatisfiable**: `DoNotSchedule`은 필수 제약, `ScheduleAnyway`는 점수 선호도이며 다른 필수 필터를 우회하지 않습니다.
4. **labelSelector**: 신규 Pod와 같은 네임스페이스에서 집계할 Pod를 선택합니다. 신규 Pod도 의도한 셀렉터와 일치하는지 확인하세요.
5. **minDomains / nodeAffinityPolicy / nodeTaintsPolicy**: 적격 도메인 집계에 영향을 주며 없는 노드·AZ 용량을 생성하지 않습니다.

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
    image: nginx:1.30.4
```

예제에서는 후보 배치가 두 제약을 모두 충족해야 합니다. `DoNotSchedule`은 다음과 같이 계산합니다:

1. 빈 도메인을 포함한 각 적격 도메인의 일치하는 Pod를 셉니다.
2. 적격 전체 최소값을 구합니다. 도메인 수가 `minDomains`보다 작으면 최소값은 0입니다.
3. 신규 Pod가 셀렉터에 일치하면 후보 도메인 개수에 포함하고, 그 후보 개수와 최소값의 차이를 비교합니다.

개수가 **2,2,1**이고 `maxSkew: 1`이면 세 번째 도메인에는 추가 Pod가 들어갈 수 있지만(2−1=1) 첫째·둘째에는 들어갈 수 없습니다(3−1=2). 후보 배치를 검사하는 것이며 모든 기존 도메인 쌍의 균형을 항상 보장하지 않습니다.

**일반적인 토폴로지 키:**
1. **kubernetes.io/hostname**: 노드 수준 분산
2. **topology.kubernetes.io/zone**: 영역 수준 분산
3. **topology.kubernetes.io/region**: 리전 수준 분산
4. **node.kubernetes.io/instance-type**: 인스턴스 유형 수준 분산

**사용 사례:**
1. **고가용성**: 파드를 여러 노드, 영역, 리전에 분산하여 장애 내구성 향상
2. **리소스 균형**: 클러스터 전체에 워크로드를 균등하게 분산
3. **비용 최적화**: 특정 유형의 노드에 워크로드 분산
4. **토폴로지 정책**: 장애 내구성과 도메인 간 트래픽·실측 지연 시간의 균형 고려

**커스텀 스케줄러 처리:**
`PodTopologySpread`의 PreFilter·Filter·Score를 유지합니다. 스케줄러 스냅샷, 네임스페이스·셀렉터, 빈 도메인과 적격 도메인, 신규 Pod, `minDomains`, node affinity·taint 정책, 재시도 이벤트를 올바르게 처리해야 합니다. Running Pod만 순회하고 skew 계산을 생략한 코드는 구현이 아닙니다.

이 EKS 실습은 한 AWS 리전의 EC2 노드를 사용하며 `topology.kubernetes.io/region` 레이블로 멀티 리전 클러스터가 되지 않습니다. AZ 분산은 교차 AZ 트래픽을 늘릴 수 있고 네트워크 지연 시간을 본질적으로 최소화하지 않습니다.

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
<summary>정답 보기</summary>

**정답: C. 노드가 특정 파드를 거부하고, 파드가 이를 허용할 수 있게 함**

**설명:**
taint는 Pod를 거부하고 toleration은 일치하는 taint를 무시할 수 있게 합니다. toleration만으로 해당 노드에 배치를 강제하거나 리소스·affinity 필터를 우회하지 않습니다.

**효과:**
1. **NoSchedule**: 허용되지 않은 taint는 신규 배치를 막지만 기존 Pod를 축출하지 않습니다.
2. **PreferNoSchedule**: 선호 조건이며 다른 점수가 더 크면 다른 곳에 용량이 있어도 해당 노드가 선택될 수 있습니다.
3. **NoExecute**: 일치하는 toleration이 없으면 신규 배치를 막고, 기존 Pod도 toleration이 없거나 기간이 만료되면 축출 대상이 됩니다. API에서 삭제되었다고 도달 불가능한 노드의 프로세스가 중지됐다고 단정할 수 없습니다.

**테인트 적용 예시:**
```bash
# 노드에 테인트 적용
kubectl taint nodes node1 key=value:NoSchedule

# 노드에서 테인트 제거
kubectl taint nodes node1 key=value:NoSchedule-
```

**테인트와 톨러레이션 예시:**
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
    image: nginx:1.30.4
```

**Toleration 필드:**
* 기본 연산자 `Equal`은 키·값을 비교합니다. `Exists`에는 value를 지정하지 않습니다.
* effect를 지정하면 일치해야 하며 비워 두면 해당 키의 모든 effect에 일치합니다. 빈 key는 `Exists`가 필요하고 모든 키에 일치하므로 의도적으로 사용하세요.
* `tolerationSeconds`는 `NoExecute` 전용입니다. 생략하면 일치하는 taint를 무기한 허용하고 지정하면 기간을 제한합니다.
* 이 예제는 기본 `Equal`·`Exists` 동작입니다. Kubernetes1.35의 선택적 비교 연산자 기능은 alpha이며 여기서는 비활성화합니다.

```yaml
tolerations:
- key: "node.kubernetes.io/not-ready"
  operator: "Exists"
  effect: "NoExecute"
  tolerationSeconds: 300
```

**일반적인 사용 사례:**
1. **전용 노드**: taint·통제된 toleration·required affinity를 함께 사용하며 taint만으로 해당 워크로드를 전용 노드에 강제하지 않음
2. **특수 하드웨어**: GPU 노드에서 다른 워크로드를 거부하고 required affinity·리소스 요청으로 GPU 워크로드의 배치도 제한
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

**필수 taint 검사:**
이 함수는 effect·와일드카드를 포함한 고정 버전의 일치 규칙을 사용합니다. 필수 검사에서 `PreferNoSchedule`은 제외하고 `NoExecute`는 포함합니다. 다른 스케줄러 필터나 taint-eviction controller를 대체하지 않습니다.

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

**다른 옵션들의 문제점:**
- A. 특정 파드가 특정 노드에만 스케줄링되도록 보장: 이는 노드 셀렉터(nodeSelector) 또는 노드 어피니티(nodeAffinity)의 역할입니다.
- B. 특정 파드가 특정 노드에 스케줄링되지 않도록 방지: taint/toleration 중 거부 동작만 설명합니다. podAntiAffinity는 다른 Pod와의 관계를 기준으로 배치합니다.
- D. 파드 간 통신을 제한: 이는 네트워크 정책(NetworkPolicy)의 역할입니다.
</details>

### 5. Kubernetes에서 스케줄러 익스텐더(Scheduler Extender)의 주요 특징이 아닌 것은 무엇인가요?

A. HTTP 웹훅을 통해 스케줄러와 통신  
B. 필터링 및 우선순위 지정 기능 제공  
C. 스케줄러 코드베이스와 직접 통합  
D. 외부 프로세스로 실행  

<details>
<summary>정답 보기</summary>

**정답: C. 스케줄러 코드베이스와 직접 통합**

**설명:**
Kubernetes에서 스케줄러 익스텐더(Scheduler Extender)의 주요 특징이 아닌 것은 "스케줄러 코드베이스와 직접 통합"입니다. 스케줄러 익스텐더는 스케줄러 코드베이스와 직접 통합되지 않고, HTTP 웹훅을 통해 외부 프로세스로 실행됩니다. 이는 스케줄링 프레임워크 플러그인과의 주요 차이점입니다.

**스케줄러 익스텐더의 주요 특징:**
1. **HTTP 웹훅**: 스케줄러는 HTTP 요청을 통해 익스텐더와 통신합니다.
2. **외부 프로세스**: 익스텐더는 스케줄러와 별도의 프로세스로 실행됩니다.
3. **필터링 및 우선순위 지정**: 익스텐더는 노드 필터링 및 우선순위 지정 기능을 제공할 수 있습니다.
4. **바인딩**: 익스텐더는 선택적으로 파드를 노드에 바인딩할 수 있습니다.

**extender 설정:**
Part2의 TLS 서비스·인증서 전제를 갖추고 보조 스케줄러에 적용합니다. `extenders`는 최상위 필드입니다. 필수 필터에는 `ignorable: false`를 유지하고, 반드시 가용량을 검사해야 하는 리소스에 실패를 무시하는 extender와 `ignoredByScheduler: true`를 조합하지 마세요. 예제의 GPU 수량 계산은 기본 리소스 필터가 수행합니다.

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

**Wire 프로토콜 (Kubernetes 1.35.8):**
Go 타입은 대문자로 시작하는 필드명을 직렬화합니다. `nodeCacheCapable: false`이면 `Pod`와 전체 `Nodes`를 보내고 `NodeNames`는 null입니다. true이면 별도로 유지하는 노드 캐시와 `NodeNames` 계약이 필요합니다. 아래는 꺾쇠 자리표시자가 아닌 유효한 JSON 예제입니다.

1. **filter / prioritize 요청**:

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
          "image": "busybox:1.37.0",
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

2. **filter 응답**: 받은 후보 노드만 반환할 수 있습니다. `FailedAndUnresolvableNodes`는 선점으로 해결할 수 없는 실패를 나타냅니다.

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

3. **prioritize 응답**: `Host`·`Score`의 배열 자체이며 점수는 **0–10**입니다. 프레임워크 점수는 0–100입니다. priority 오류 시 해당 extender 점수가 제외되므로 필수 규칙은 Filter에 두어야 합니다.

```json
[
  {
    "Host": "gpu-node",
    "Score": 2
  }
]
```

4. **선택적 bind 요청·응답**: Pod 이름·네임스페이스·UID와 선택한 노드를 전달합니다. Part2는 이 callback을 구현하지 않으며 `bindVerb`를 생략합니다.

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

5. **선택적 preemption callback**: `preemptVerb`는 `ExtenderPreemptionArgs`·`ExtenderPreemptionResult`로 Pod와 후보 victim을 교환합니다. PreFilter·PreScore callback이 아닙니다.

**구현:**
[Part2](../../scheduling/02-custom-scheduler-part2.md)의 입력 크기가 제한된 전체 핸들러와 TLS 명령을 사용합니다. 누락된 Pod·노드, 잘못된 메모리 조건, 너무 큰 입력, 다른 캐시 계약을 거부합니다. 구현하지 않은 `customFilter`·`customScore`를 실행 가능한 코드처럼 사용하지 않습니다.

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
<summary>정답 보기</summary>

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
    image: nginx:1.30.4
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
2. **지역성 선호**: 같은 노드 배치로 일부 네트워크 비용을 줄일 수 있으나 경합·지연 시간을 측정해야 함
3. **리소스 격리**: 리소스를 많이 사용하는 파드를 서로 다른 노드에 분산
4. **라이선스 제한**: 라이선스 제한이 있는 애플리케이션을 특정 노드에 집중

**파드 어피니티 vs 노드 어피니티:**
- **노드 어피니티**: 파드와 노드 간의 관계를 정의합니다.
- **파드 어피니티**: 파드 간의 관계를 정의합니다.

**파드 어피니티와 안티-어피니티의 성능 영향:**
파드 어피니티와 안티-어피니티는 모든 노드와 파드를 고려해야 하므로 계산 비용이 높을 수 있습니다. 특히 대규모 클러스터에서는 스케줄링 성능에 영향을 줄 수 있으므로 신중하게 사용해야 합니다.

**커스텀 스케줄러 처리:**
전처리·점수 계산을 포함한 `InterPodAffinity`를 유지합니다. 신규 Pod의 필수 조건, 기존 Pod의 required anti-affinity, 네임스페이스 선택, 토폴로지 레이블, self-affinity의 첫 Pod 처리까지 고려해야 합니다. 항상 true인 stub은 잘못된 배치를 허용하거나 anti-affinity에서 반전될 때 모든 노드를 거부합니다.

`namespaces`와 `namespaceSelector`로 선택한 네임스페이스는 합집합이며 둘 다 생략하면 신규 Pod의 네임스페이스입니다. `namespaceSelector: {}`는 전체 네임스페이스를 선택합니다. 예제의 필수 `app=cache` Pod는 선택한 네임스페이스의 적격 노드에 이미 있어야 합니다. preferred anti-affinity는 분리를 보장하지 않으며 `IgnoredDuringExecution`은 레이블·다른 Pod가 바뀔 때 계속 재배치하지 않는다는 뜻입니다.

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
<summary>정답 보기</summary>

**정답: C. 스케줄링 큐에서 파드 정렬**

**설명:**
Kubernetes 스케줄링 프레임워크에서 "QueueSort" 확장 포인트의 역할은 스케줄링 큐에서 파드를 정렬하는 것입니다. 이 확장 포인트는 어떤 파드가 먼저 스케줄링될지 결정하는 우선순위를 설정합니다.

**스케줄링 큐와 QueueSort:**
스케줄러는 스케줄링 큐에 있는 파드를 하나씩 처리합니다. QueueSort 플러그인은 이 큐에서 파드의 순서를 결정합니다. 기본적으로 Kubernetes는 `PrioritySort` 플러그인을 사용하여 파드의 우선순위(priority)에 따라 정렬합니다.

**버전별 인터페이스:**
Kubernetes 1.35.8의 QueueSort는 `Less(fwk.QueuedPodInfo, fwk.QueuedPodInfo) bool`을 구현합니다. 인자는 getter로 접근하는 인터페이스입니다. 기본 `PrioritySort`는 어드미션된 우선순위 다음 큐 타임스탬프를 비교합니다.

**전체 커스텀 예제 (`quizplugins/queue.go`):**
실습용 동률 처리보다 어드미션된 우선순위를 먼저 유지합니다. 네임스페이스·레이블 선호는 동일 우선순위 Pod 사이의 공정성을 해칠 수 있습니다. 신뢰할 수 없는 레이블을 어드미션으로 통제하는 PriorityClass 대신 사용하지 마세요.

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

뒤의 PoolConstraint 예제와 함께 `cmd/quiz-scheduler/main.go`에서 등록합니다:

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

Part1 모듈에서 `CGO_ENABLED=0 go build -buildvcs=false -o custom-scheduler ./cmd/quiz-scheduler`로 빌드하고 선택한 설정에 필요한 플러그인만 활성화합니다.

**스케줄러 구성에서 QueueSort 플러그인 활성화:**
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
      - name: PrioritySort  # 기본 플러그인 비활성화
```

**QueueSort 플러그인의 특징:**
1. **단일 활성화**: 한 번에 하나의 QueueSort 플러그인만 활성화할 수 있습니다.
2. **공유 큐**: 한 스케줄러 프로세스의 모든 프로필은 같은 QueueSort 플러그인과 설정을 사용해야 합니다. 다른 프로세스는 별도 큐를 가집니다.
3. **성능 중요성**: 효율적인 정렬 알고리즘이 중요하며, 복잡한 로직은 스케줄링 성능에 영향을 줄 수 있습니다.

**QueueSort 플러그인 사용 사례:**
1. **비즈니스 우선순위**: 비즈니스 중요도에 따라 파드 정렬
2. **리소스 효율성**: 리소스 요청이 적은 파드를 먼저 스케줄링하여 빈 공간 활용
3. **서비스 수준 계약(SLA)**: SLA 요구 사항에 따라 파드 정렬
4. **배치 처리**: 배치 작업과 대화형 작업 간의 우선순위 조정

**스케줄링 큐 모니터링:**
```bash
# 스케줄러 로그에서 큐 정보 확인
kubectl logs -n scheduler-lab -l app=custom-scheduler --prefix --tail=100

# 스케줄링 대기 중인 파드 확인
kubectl get pods -A --field-selector=spec.schedulerName=custom-scheduler,spec.nodeName= -o wide
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
<summary>정답 보기</summary>

**정답: A. 우선순위가 높은 파드가 스케줄링될 수 있도록 우선순위가 낮은 파드 제거**

**설명:**
Kubernetes에서 파드 우선순위 선점(Pod Priority Preemption)의 주요 목적은 우선순위가 높은 파드가 스케줄링될 수 있도록 우선순위가 낮은 파드를 제거하는 것입니다. 높은 우선순위 Pod가 적합한 노드를 찾지 못하면, 관련 제약을 만족시킬 수 있는 경우 낮은 우선순위 Pod를 선점할 수 있습니다.

**파드 우선순위 및 선점 메커니즘:**
1. **PriorityClass 정의**: 파드의 우선순위를 정의하는 클러스터 수준 리소스입니다.
2. **파드에 우선순위 할당**: 파드는 `spec.priorityClassName`을 통해 PriorityClass를 참조합니다.
3. **스케줄링 순서**: 우선순위가 높은 파드가 스케줄링 큐에서 우선적으로 처리됩니다.
4. **선점 프로세스**: Pod 정책이 허용하고 나머지 제약을 충족할 수 있으면 낮은 우선순위 Pod를 제거할 수 있습니다.

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
    image: nginx:1.30.4
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
4. 정책에 따라 후보·victim을 선택하며 모든 조합 중 최소 개수를 보장하지 않습니다.
5. 선택된 파드는 정상적으로 종료(graceful termination)됩니다.
6. victim 종료 이후 스케줄링을 재시도합니다. nominate되었다고 바인딩이 보장되지는 않습니다.

**선점 고려 사항:**
1. **그레이스풀 종료 기간**: 선점된 파드는 `terminationGracePeriodSeconds`(기본값: 30초) 동안 정상 종료 시간을 갖습니다.
2. **파드 중단 예산(PDB)**: 선점은 PDB 위반을 피하려 하지만 best effort이며 준수를 보장하지 않습니다.
3. **Nomination**: `status.nominatedNodeName`은 후보 노드를 기록합니다. 선점이 노드 taint를 추가하여 예약하는 것은 아닙니다.
4. **시스템 Pod**: critical PriorityClass는 예약된 높은 우선순위를 사용하지만 더 높은 우선순위 Pod나 다른 축출 방식에 대한 절대 면제는 아닙니다.

**선점 이벤트 확인:**
```bash
# 선점 이벤트 확인
kubectl get events | grep -i preempt
```

**선점 관련 지표 모니터링:**
설정한 모니터링 시스템으로 **커스텀 스케줄러**의 인증된 HTTPS 메트릭 엔드포인트에서 `scheduler_preemption_attempts_total`을 읽습니다. `kubectl get --raw /metrics`는 이 엔드포인트가 아닌 API 서버 메트릭을 읽습니다.

```bash
kubectl get pods -A -o custom-columns=NAME:.metadata.name,PRIORITY:.spec.priority,NOMINATED:.status.nominatedNodeName
```

**안전한 선점 처리:**
PostFilter의 `DefaultPreemption`을 유지합니다. 낮은 우선순위 Pod를 제거한 상태를 모의 계산하고 관련 제약을 다시 검사합니다. 첫 노드의 낮은 우선순위 Pod를 전부 삭제하면 안 됩니다. 선택 과정은 PDB 위반과 victim 우선순위를 고려하며 전체 조합에서 최소 victim 개수를 보장하지 않습니다.

선점으로 없는 레이블, 호환되지 않는 볼륨 토폴로지, 없는 하드웨어를 해결할 수 없습니다. Pod는 nominate된 뒤에도 Pending일 수 있고 더 높은 우선순위 Pod가 결과를 바꿀 수 있습니다. 교체·종료·API 갱신은 비동기이며 이번 감사에서 축출 루프를 실행하지 않았습니다.

**선점의 장단점:**
장점:
- 제약이 허용하는 경우 높은 우선순위 워크로드의 공간 확보
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
<summary>정답 보기</summary>

**정답: A. 필터링 전에 파드 및 클러스터 상태에 대한 사전 처리 수행**

**설명:**
Kubernetes 스케줄링 프레임워크에서 "PreFilter" 확장 포인트의 역할은 필터링 전에 파드 및 클러스터 상태에 대한 사전 처리를 수행하는 것입니다. PreFilter 플러그인은 필터링 단계에서 사용할 데이터를 준비하고, 파드가 스케줄링 가능한지 여부를 미리 확인할 수 있습니다.

**PreFilter 확장 포인트의 주요 기능:**
1. **데이터 준비**: 필터링 단계에서 사용할 데이터 구조를 초기화하고 준비합니다.
2. **사전 검사**: 파드가 스케줄링 가능한지 여부를 미리 확인합니다.
3. **상태 저장**: 스케줄링 사이클 동안 사용할 상태 정보를 저장합니다.
4. **최적화**: 불필요한 필터링 작업을 방지하여 성능을 최적화합니다.

**버전별 인터페이스:**
Kubernetes 1.35.8은 `PreFilter(ctx, state, pod, nodes) (*fwk.PreFilterResult, *fwk.Status)`를 사용하며 state는 `fwk.CycleState`, nodes는 `[]fwk.NodeInfo`입니다. 선택적 AddPod·RemovePod 확장은 스케줄링할 Pod, 모의 추가·제거되는 PodInfo, NodeInfo를 받습니다. 선점 시뮬레이션과 복제된 상태를 위한 것이며 일반 informer callback이 아닙니다.

**기본 PreFilter 플러그인:**
Kubernetes는 다음과 같은 기본 PreFilter 플러그인을 제공합니다:

1. **InterPodAffinity**: 파드 간 어피니티 및 안티-어피니티 요구 사항을 처리합니다.
2. **NodeAffinity**: 노드 어피니티 요구 사항을 처리합니다.
3. **NodePorts**: 파드가 요청한 호스트 포트를 처리합니다.
4. **NodeResourcesFit**: 노드 리소스 요구 사항을 처리합니다.
5. **PodTopologySpread**: 파드 토폴로지 분산 제약 조건을 처리합니다.
6. **VolumeBinding**: 볼륨 바인딩 요구 사항을 처리합니다.

**전체 PreFilter + Filter 예제 (`quizplugins/prefilter.go`):**
일반적인 pool 레이블 조건은 required node affinity가 더 간단합니다. 아래는 검증된 사이클별 상태와 `Clone()` 예제입니다. 다른 Pod에 의존하지 않으므로 AddPod·RemovePod 확장이 필요하지 않습니다. PreFilter 상태가 없으면 배치를 허용하지 않고 오류를 반환합니다.

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

**구현한 두 단계 활성화 및 기본 리소스 검사 유지:**
7번의 등록 명령에 이 플러그인이 포함됩니다.

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
<summary>정답 보기</summary>

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
1. 일치하는 toleration이 없는 새 Pod는 해당 노드에 스케줄링되지 않습니다.
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
기본 어드미션 동작에서는 동등한 toleration이 명시적으로 지정되지 않은 경우에만 아래 기본값을 추가합니다. DaemonSet Pod는 not-ready·unreachable NoExecute에 무기한 toleration을 사용합니다:
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

기본값은 taint 처리 시작 이후 300초 동안 해당 taint를 허용합니다. 장애 발생부터 교체까지의 정확한 시간이 아닙니다. 컨트롤 플레인 감지·삭제에 지연이 더해지며 연결이 끊긴 노드의 프로세스는 계속 실행 중일 수 있습니다.

**사용자 정의 톨러레이션:**
toleration이 길면 교체가 늦어져 장애가 길어질 수도 있습니다. 길수록 안전하다고 가정하지 말고 애플리케이션 복구 요구에 따라 선택하세요:
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
    image: nginx:1.30.4
```

**노드 컨트롤러와 축출 시간:**
고정한 upstream 1.35.8에서 `--node-monitor-period` 기본값은 5초, `--node-monitor-grace-period`는 40초가 아닌 **50초**입니다. 과거 `--pod-eviction-timeout` 플래그가 현재 taint 기반 축출을 제어하지 않습니다. 일치하는 Pod toleration과 taint-eviction controller가 이를 처리하며, 감지·taint 게시·컨트롤러 속도 제한·삭제에 추가 시간이 걸릴 수 있습니다.

Kubernetes 1.29부터 taint 기반 축출은 별도 `taint-eviction-controller`가 담당하며 기본 활성화되지만 자체 관리 컨트롤 플레인에서는 별도로 설정할 수 있습니다. 이 값은 EKS 설정 지침이나 장애 전환 시간 보장이 아닙니다. 도달 불가능한 노드의 stateful Pod를 강제로 제거하기 전에 기존 writer가 중지·fencing됐는지 확인하여 동시 writer를 방지해야 합니다.

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

**다른 옵션들의 문제점:**
- B. 노드가 스케줄링 불가능하지만, 기존 파드는 계속 실행됨: 이는 `NoSchedule` 효과의 동작이며, `NoExecute` 효과는 톨러레이션이 없는 기존 파드도 제거합니다.
- C. 노드가 유지 관리 모드이며, 새 파드는 스케줄링되지 않음: 이는 일반적으로 `node.kubernetes.io/unschedulable:NoSchedule` 테인트의 동작입니다.
- D. PreferNoSchedule은 선호 조건입니다. 일반적인 memory-pressure·disk-pressure taint는 NoSchedule을 사용하며 어느 쪽도 unreachable:NoExecute를 뜻하지 않습니다.
</details>

## 참고 자료

[Part1 모듈](../../scheduling/01-custom-scheduler-part1.md)과 [Part2 구현](../../scheduling/02-custom-scheduler-part2.md)을 사용합니다. 코드·설정 검사는 로컬에서 수행하며 클라우드 배포·축출은 실행하지 않았습니다.

* [v1.35.8 프레임워크 인터페이스](https://github.com/kubernetes/kubernetes/blob/v1.35.8/staging/src/k8s.io/kube-scheduler/framework/interface.go)
* [extender wire 타입](https://github.com/kubernetes/kubernetes/blob/v1.35.8/staging/src/k8s.io/kube-scheduler/extender/v1/types.go)
* [노드·Pod affinity](https://kubernetes.io/docs/concepts/scheduling-eviction/assign-pod-node/)
* [Topology spread](https://kubernetes.io/docs/concepts/scheduling-eviction/topology-spread-constraints/)
* [Taint와 toleration](https://kubernetes.io/docs/concepts/scheduling-eviction/taint-and-toleration/)
* [우선순위와 선점](https://kubernetes.io/docs/concepts/scheduling-eviction/pod-priority-preemption/)
* [노드 수명주기 기본값](https://github.com/kubernetes/kubernetes/blob/v1.35.8/pkg/controller/nodelifecycle/config/v1alpha1/defaults.go)
