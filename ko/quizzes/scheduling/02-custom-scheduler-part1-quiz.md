# Custom Scheduler 퀴즈 (Part 1)

> **예제 기준 버전**: Kubernetes 1.35.8, Go 1.27.1
> **마지막 업데이트**: 2026년 9월 11일

이 퀴즈는 Kubernetes에서 Custom Scheduler를 구현하고 사용하는 방법에 대한 이해를 테스트합니다.

## 퀴즈 문제

### 1. Kubernetes에서 스케줄러의 주요 역할은 무엇인가요?

A. 파드 생성 및 삭제  
B. 파드를 적절한 노드에 할당  
C. 노드 리소스 모니터링  
D. 컨테이너 이미지 다운로드  

<details>
<summary>정답 보기</summary>

**정답: B. 파드를 적절한 노드에 할당**

**설명:**
Kubernetes에서 스케줄러의 주요 역할은 파드를 적절한 노드에 할당하는 것입니다. 스케줄러는 새로 생성된 파드를 감시하고, 아직 노드가 할당되지 않은 파드를 찾아 실행할 최적의 노드를 선택합니다.

**스케줄러의 주요 기능:**
1. **파드-노드 할당**: 파드의 요구 사항과 노드의 가용 리소스를 고려하여 최적의 노드를 선택합니다.
2. **필터링**: 파드를 실행할 수 없는 노드를 제외합니다(예: 리소스 부족, 테인트 등).
3. **스코어링**: 적합한 노드에 점수를 매겨 최적의 노드를 선택합니다.
4. **바인딩**: 선택한 노드에 파드를 바인딩하여 스케줄링 결정을 확정합니다.

**스케줄링 프로세스 (Kubernetes 1.35.8):**
1. **Filter**: `NodeResourcesFit`은 유효 리소스 요청과 남은 allocatable을 비교하고, `NodePorts`는 host port 요청, `NodeAffinity`는 nodeSelector와 affinity, `TaintToleration`은 taint를 검사합니다. `VolumeBinding`, `VolumeZone`, `NodeVolumeLimits` 등은 스토리지 제약을 처리합니다. 노드 pressure는 조건·taint에 반영됩니다. `CheckNodeDiskPressure` 같은 이름은 과거 predicate이며 현재 설정할 플러그인 이름이 아닙니다.
2. **Score**: `NodeResourcesFit`(기본 `LeastAllocated`), `NodeResourcesBalancedAllocation`, `NodeAffinity`, `InterPodAffinity`, `PodTopologySpread`, `TaintToleration`, `ImageLocality`가 선호도에 기여합니다. 모두 실시간 사용률을 측정하는 것은 아닙니다.
3. **Bind**: 나머지 프레임워크 단계도 성공하면 노드 할당을 기록하고 kubelet·런타임이 실행을 관리합니다. 높은 점수가 시작 성공·지연 시간·가용성을 보장하지는 않습니다.

**보조 스케줄러 설정 예시:**
점수 가중치만 변경하고 기본 필터를 유지합니다. 이 퀴즈의 스케줄러 설정은 `--config`로 읽는 파일이며 `kubectl apply`할 Kubernetes API 리소스가 아닙니다.
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
    score:
      enabled:
      - name: NodeResourcesBalancedAllocation
        weight: 2
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
<summary>정답 보기</summary>

**정답: D. kubelet 수정**

**설명:**
kubelet 수정은 Custom Scheduler를 구현하는 방법이 아닙니다. kubelet은 각 노드에서 실행되는 에이전트로, 파드의 실행을 관리하지만 스케줄링 결정을 내리지 않습니다. 스케줄링은 kube-scheduler 또는 사용자 정의 스케줄러에 의해 수행됩니다.

**Custom Scheduler 구현 방법:**

1. **kube-scheduler 기반 보조 스케줄러 설정**: 기본 플러그인을 유지하고 필요한 동작만 조정합니다. Part1 본문에 전체 명령·RBAC·ConfigMap·Deployment가 있습니다.

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
    score:
      enabled:
      - name: NodeResourcesBalancedAllocation
        weight: 2
```

2. **독립 스케줄러 구현**: 올바른 캐시·큐·list/watch 복구·리소스 계산·볼륨 조정·재시도·리더 선출·바인딩이 필요합니다. watch만 시작하면 기존 Pod나 연결 끊김을 놓칩니다. 실제 구현은 informer/workqueue를 사용하고 tombstone·취소·오래된 객체를 처리해야 합니다. Ready 노드를 선택하는 것만으로 Pod 적합성을 확인할 수 없으므로 본문의 예제는 upstream kube-scheduler에 이 동작을 맡깁니다.

3. **프레임워크 플러그인 개발**: 플러그인을 스케줄러 바이너리에 컴파일하고 `app.WithPlugin`으로 등록합니다. 4번은 전체 Filter 플러그인, 6번은 Score 플러그인, 7번은 등록 명령을 제공합니다. 인터페이스는 `k8s.io/kube-scheduler/framework` v0.35.8 기준이며 Kubernetes 마이너 버전에 따라 시그니처가 달라집니다.

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
<summary>정답 보기</summary>

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
  schedulerName: custom-scheduler  # 사용자 정의 스케줄러 지정
  containers:
  - name: main-container
    image: nginx:1.30.4
    resources:
      requests:
        memory: "64Mi"
        cpu: "250m"
      limits:
        memory: "128Mi"
        cpu: "500m"
```

이 파드는 "custom-scheduler"라는 이름의 스케줄러에 의해서만 스케줄링됩니다. 해당 이름의 스케줄러가 클러스터에 존재하지 않으면, 파드는 `Pending` 상태로 남게 됩니다.

**스케줄러 이름 설정:**
Part1의 전체 Deployment에서 아래 설정을 `/etc/scheduler/config.yaml`로 마운트하고 `--config=/etc/scheduler/config.yaml`로 읽습니다. `--scheduler-name`은 현재 설정 방식이 아닙니다. ServiceAccount와 Lease 권한이 먼저 필요합니다.

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
kubectl logs -n scheduler-lab -l app=custom-scheduler --prefix --tail=100
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
<summary>정답 보기</summary>

**정답: C. 파드를 실행할 수 없는 노드 제외**

**설명:**
Kubernetes 스케줄링 프레임워크에서 "Filter" 확장 포인트(이전에는 "Predicate"라고 불림)의 역할은 파드를 실행할 수 없는 노드를 제외하는 것입니다. 필터 플러그인은 각 노드가 파드의 요구 사항을 충족하는지 확인하고, 충족하지 않는 노드를 후보 목록에서 제외합니다.

**스케줄링 프레임워크 확장 포인트:**
* **PreEnqueue / QueueSort**: 큐 진입을 제어하고 대기 Pod의 순서를 정합니다.
* **PreFilter / Filter**: 공통 상태를 준비하고 부적합 노드를 제외합니다.
* **PostFilter**: 적격 노드가 없을 때 선점 등의 복구를 시도합니다.
* **PreScore / Score / 선택적 NormalizeScore**: 적격 노드를 준비·평가하며 정규화된 플러그인 점수는 0–100이어야 합니다.
* **Reserve / Unreserve**: assume 상태를 기록하고 이후 실패 시 되돌립니다. 물리적 CPU·장치 할당을 뜻하지 않습니다.
* **Permit**: 허용·거부·대기 여부를 결정합니다.
* **PreBind / Bind / PostBind**: 의존성을 준비하고 바인딩을 확정한 뒤 후속 작업을 합니다. `PostBind`로 이미 확정된 바인딩을 거부할 수 없습니다. 버전별 추가 메서드가 있으므로 대상 릴리스로 컴파일해야 합니다.

**기본 필터:**
`NodeResourcesFit`, `NodeName`, `NodeUnschedulable`, `NodePorts`, `TaintToleration`, `NodeAffinity`, `InterPodAffinity`, `PodTopologySpread`, `VolumeRestrictions`, `NodeVolumeLimits`, `VolumeBinding`, `VolumeZone`이 각 제약을 담당합니다. 과거 predicate 이름과 공급자별 `EBSLimits`는 현재 플러그인 이름이 아닙니다.

**커스텀 필터 예시 (`plugins/filter.go`):**
이처럼 단순한 레이블 조건은 보통 required node affinity로 표현합니다. 아래는 프레임워크 인터페이스 예제입니다. 레이블이 없으면 다른 Pod를 선점해도 해결되지 않지만, 이후 노드 레이블이 바뀌면 재시도할 수 있습니다.

```go
package plugins

import (
	"context"

	v1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/runtime"
	fwk "k8s.io/kube-scheduler/framework"
)

type MyFilterPlugin struct{}

var _ fwk.FilterPlugin = &MyFilterPlugin{}

func (*MyFilterPlugin) Name() string { return "MyFilterPlugin" }

func (*MyFilterPlugin) Filter(_ context.Context, _ fwk.CycleState, _ *v1.Pod, info fwk.NodeInfo) *fwk.Status {
	if info == nil || info.Node() == nil {
		return fwk.NewStatus(fwk.Error, "missing node")
	}
	if info.Node().Labels["custom-label"] != "required-value" {
		return fwk.NewStatus(fwk.UnschedulableAndUnresolvable, "node lacks required label")
	}
	return nil
}

func NewFilter(_ context.Context, _ runtime.Object, _ fwk.Handle) (fwk.Plugin, error) {
	return &MyFilterPlugin{}, nil
}
```

**기본 필터와 함께 활성화:**
7번에서 플러그인을 등록합니다. 레이블 검사를 추가하려고 `NodeResourcesFit`을 비활성화하지 마세요.

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
    filter:
      enabled:
      - name: MyFilterPlugin
```

**다른 옵션들의 문제점:**
- A. 노드에 점수 부여: 이는 "Score" 확장 포인트의 역할입니다.
- B. 파드를 노드에 바인딩: 이는 "Bind" 확장 포인트의 역할입니다.
- D. 스케줄링 큐에서 파드 정렬: 이는 "Queue Sort" 확장 포인트의 역할입니다.
</details>

### 5. 다음 중 스케줄러 대신 kubelet과 컨테이너 런타임이 수행하는 작업은 무엇인가요?

A. 노드의 리소스 요청량과 allocatable 평가
B. Pod 우선순위와 선점 고려
C. 이미지 레이어 다운로드와 컨테이너 생성
D. 노드 affinity와 Pod 간 affinity 평가

<details>
<summary>정답 보기</summary>

**정답: C. 이미지 레이어 다운로드와 컨테이너 생성**

**설명:**
스케줄러는 노드를 선택하고 kubelet은 런타임에 이미지 pull과 컨테이너 생성을 요청합니다. **이미지 지역성은 스케줄링에 영향을 줄 수 있습니다.** 기본 `ImageLocality` 점수 플러그인은 노드가 보고한 이미지 캐시와 크기를 활용합니다. 캐시 보고가 오래될 수 있으므로 pull 생략을 보장하지 않습니다.

**구현 시 고려 사항:**
1. **리소스**: `NodeResourcesFit`을 유지합니다. 유효 요청과 캐시의 할당·assume된 요청을 사용하며 실시간 CPU·메모리 사용률과는 다릅니다. CPU·메모리 limit은 초과 약정될 수 있고 기본 적합성 검사 기준이 아닙니다.
2. **우선순위**: PriorityClass와 preemptionPolicy를 의도적으로 사용합니다. 선점해도 affinity·볼륨 등 조건을 충족하지 못하면 고우선순위 Pod도 Pending으로 남습니다.
3. **배치**: required node affinity는 후보를 제한하고 preferred affinity는 점수를 줍니다. 아래 AZ는 실제 적격 용량이 있는 영역으로 바꾸세요. 일반적인 GPU·토폴로지 요구에는 커스텀 스케줄러가 필요하지 않을 수 있습니다.

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
  containers:
  - name: nginx
    image: nginx:1.30.4
    resources:
      requests:
        cpu: 100m
        memory: 64Mi
```

4. **기타 제약**: taint/toleration, topology spread, 스토리지 토폴로지·연결 제한, 하드웨어 리소스 검사를 유지합니다. 네트워크 지역성은 신뢰할 수 있는 토폴로지 데이터로 모델링하며 레이블만으로 지연 시간을 입증할 수 없습니다.
5. **이미지 처리**: `ImageLocality`는 선호도이며 용량·시작 시간 보장이 아닙니다. 이미지 가비지 컬렉션, 레지스트리 인증, pull 실패는 여전히 노드에서 발생합니다.

**다른 선택지:**
A·B·D는 스케줄링 고려 사항입니다. 구분해야 할 것은 배치 결정과 런타임 작업이며, 이미지 정보 자체를 스케줄링에서 제외하는 것이 아닙니다.
</details>
### 6. Kubernetes 스케줄링 프레임워크에서 "Score" 확장 포인트의 역할은 무엇인가요?

A. 파드를 실행할 수 없는 노드 제외  
B. 필터링을 통과한 노드에 점수 부여  
C. 파드를 노드에 바인딩  
D. 스케줄링 큐에서 파드 정렬  

<details>
<summary>정답 보기</summary>

**정답: B. 필터링을 통과한 노드에 점수 부여**

**설명:**
Kubernetes 스케줄링 프레임워크에서 "Score" 확장 포인트(이전에는 "Priority"라고 불림)의 역할은 필터링을 통과한 노드에 점수를 부여하는 것입니다. 스코어링 플러그인은 각 노드에 점수를 할당하고, 이 점수를 기반으로 최적의 노드가 선택됩니다.

**스코어링 프로세스:**
1. 각 플러그인은 점수를 계산하고 선택적 정규화 이후 반드시 0–100 범위를 반환합니다.
2. 각 플러그인의 점수는 구성된 가중치에 따라 가중치가 부여됩니다.
3. 모든 플러그인의 가중치가 적용된 점수가 합산됩니다.
4. 가장 높은 총점을 받은 노드가 파드 배치를 위해 선택됩니다.

**기본 스코어링 플러그인:**
Kubernetes는 다음과 같은 기본 스코어링 플러그인을 제공합니다:

1. **NodeResourcesBalancedAllocation**: CPU와 메모리 사용의 균형이 잘 잡힌 노드에 높은 점수를 부여합니다.
2. **NodeResourcesFit**: 요청량과 allocatable을 기준으로 설정된 LeastAllocated·MostAllocated·RequestedToCapacityRatio 전략을 사용합니다.
3. **NodeAffinity**: 노드 어피니티 규칙에 따라 점수를 부여합니다.
4. **InterPodAffinity**: 파드 간 어피니티/안티-어피니티 규칙에 따라 점수를 부여합니다.
5. **PodTopologySpread**: 토폴로지 도메인 전체에 파드를 균등하게 분산시키는 노드에 높은 점수를 부여합니다.
6. **TaintToleration**: 허용되지 않은 PreferNoSchedule taint를 감점하며 hard taint는 필터에서 처리합니다.
7. **ImageLocality**: 필요한 컨테이너 이미지가 이미 있는 노드에 높은 점수를 부여합니다.

**커스텀 점수 플러그인 (`plugins/score.go`):**
이 예제의 노드 레이블은 관리자가 제어하는 정책 입력입니다. 잘못된 값은 임의의 선호도로 바꾸지 않고 점수 계산 사이클을 실패시킵니다. 유효한 0점은 필터가 아닙니다.

```go
package plugins

import (
	"context"
	"strconv"

	v1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/runtime"
	fwk "k8s.io/kube-scheduler/framework"
)

type MyScorePlugin struct{}

var _ fwk.ScorePlugin = &MyScorePlugin{}

func (*MyScorePlugin) Name() string { return "MyScorePlugin" }

func (*MyScorePlugin) Score(_ context.Context, _ fwk.CycleState, _ *v1.Pod, info fwk.NodeInfo) (int64, *fwk.Status) {
	if info == nil || info.Node() == nil {
		return 0, fwk.NewStatus(fwk.Error, "missing node")
	}
	value := info.Node().Labels["custom-score-label"]
	if value == "" {
		return 0, nil
	}
	score, err := strconv.ParseInt(value, 10, 64)
	if err != nil || score < fwk.MinNodeScore || score > fwk.MaxNodeScore {
		return 0, fwk.NewStatus(fwk.Error, "custom-score-label must be an integer from 0 to 100")
	}
	return score, nil
}

// Scores are already absolute 0-100 values; no relative rescaling is needed.
func (*MyScorePlugin) ScoreExtensions() fwk.ScoreExtensions { return nil }

func NewScore(_ context.Context, _ runtime.Object, _ fwk.Handle) (fwk.Plugin, error) {
	return &MyScorePlugin{}, nil
}
```

**두 플러그인 산술 예제의 가중치:**
아래는 의도적으로 **Score** 플러그인 집합만 교체합니다. 기본 Filter는 유지됩니다. 실제 정책에는 필요한 다른 점수 선호도도 유지하세요.

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
    score:
      disabled:
      - name: "*"
      enabled:
      - name: MyScorePlugin
        weight: 5
      - name: NodeResourcesBalancedAllocation
        weight: 2
```

**스코어링 결과 예시:**
실측 결과가 아닌 산술 예제입니다. A·B·C가 필터를 통과하고 두 플러그인이 아래 최종 0–100 점수를 반환한다고 가정합니다:

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
<summary>정답 보기</summary>

**정답: D. 노드 컨트롤러 수정**

**설명:**
노드 컨트롤러 수정은 Kubernetes에서 스케줄러 확장을 위한 방법이 아닙니다. 노드 컨트롤러는 노드의 상태를 모니터링하고 관리하는 컨트롤 플레인 구성 요소로, 스케줄링 결정과는 직접적인 관련이 없습니다.

**확장 방법:**

1. **프레임워크 플러그인**은 스케줄러 내부에서 실행됩니다. 4·6번의 전체 Filter/Score 파일을 Part1 모듈의 `plugins/`에 저장하고 아래를 `cmd/with-plugins/main.go`로 저장합니다. `CGO_ENABLED=0 go build -buildvcs=false -o custom-scheduler ./cmd/with-plugins`로 빌드합니다. 등록만으로 활성화되지는 않으며 설정에서도 참조해야 합니다.

```go
package main

import (
	"os"

	"example.com/custom-scheduler/plugins"
	"k8s.io/component-base/cli"
	"k8s.io/kubernetes/cmd/kube-scheduler/app"
)

func main() {
	command := app.NewSchedulerCommand(
		app.WithPlugin("MyFilterPlugin", plugins.NewFilter),
		app.WithPlugin("MyScorePlugin", plugins.NewScore),
	)
	os.Exit(cli.Run(command))
}
```

이 버전의 factory는 `(context.Context, runtime.Object, framework.Handle)`을 받습니다. 예제는 사용자 인수를 받지 않습니다. 설정을 추가한다면 버전에 맞는 framework runtime decoder로 `runtime.Unknown` payload를 디코딩·검증하세요. 등록되지 않은 사용자 정의 타입으로 바로 단언하면 안 됩니다.

2. **HTTP extender**는 외부 필터·우선순위 계산과 선택적인 바인딩을 제공합니다. `extenders`는 profile 내부가 아닌 **최상위 필드**입니다. 아래 구성에는 실제 extender 서비스, 표시한 경로에 마운트된 일치하는 TLS 인증서, 네트워크 연결, 제한된 오류 처리가 필요합니다. 독립 실행 가능한 서버나 EKS 관리형 스케줄러 설정이 아닙니다. `bindVerb`를 생략하여 기본 바인더를 유지합니다.

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
- urlPrefix: https://extender.scheduler-lab.svc:8443
  filterVerb: filter
  prioritizeVerb: prioritize
  weight: 5
  enableHTTPS: true
  tlsConfig:
    caFile: /etc/extender-tls/ca.crt
    certFile: /etc/extender-tls/tls.crt
    keyFile: /etc/extender-tls/tls.key
  httpTimeout: 2s
  nodeCacheCapable: false
  ignorable: false
```

`ignorable: false`에서는 extender filter 실패 시 해당 스케줄링 시도가 차단됩니다. true로 바꾸면 필수 사용자 제약을 우회할 수 있습니다. prioritize 오류는 다르게 처리됩니다. Kubernetes1.35.8은 실패를 기록하고 해당 extender 점수를 제외하므로 점수로 필수 규칙을 강제해서는 안 됩니다. 가능하면 프레임워크 플러그인을 사용하고 타임아웃·재시도·실패 동작을 검증하세요.

3. **다중 스케줄러**는 구별되는 `profiles[].schedulerName`과 별도의 리더 선출 그룹을 사용합니다. 기본 스케줄러의 이름·Lease를 공유하는 프로세스를 추가하지 말고 Part1의 전체 Deployment/RBAC를 사용합니다.

**노드 컨트롤러 역할:**
보통 kubelet이 노드를 등록하고 상태를 보고합니다. 노드 수명주기 컨트롤러는 heartbeat를 관찰하고 조건·taint를 갱신하며 비정상 노드 대응을 조정합니다. 이 정보는 스케줄링에 영향을 주지만 노드 컨트롤러 수정은 스케줄러 확장 API가 아닙니다.

**방법 선택:**
구현 복잡도, 노드별 HTTP 비용, 캐시 일관성, 실패 동작, 업그레이드 호환성을 평가합니다. EKS에서는 별도 스케줄러를 배포하며 관리형 기본 스케줄러의 플래그·레지스트리를 교체하지 않습니다.

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
<summary>정답 보기</summary>

**정답: B. 여러 스케줄러 인스턴스 중 하나만 활성화**

**설명:**
Kubernetes 스케줄러의 `--leader-elect` 플래그는 고가용성(HA) 구성에서 여러 스케줄러 인스턴스 중 하나만 활성화하여 작업을 수행하도록 하는 목적을 가집니다. 같은 Lease 그룹의 복제본을 조정하며, 모든 장애에 대한 fencing이나 동시성 안전 API 작업을 대체하지는 않습니다.

**리더 선출 메커니즘:**
1. 여러 스케줄러 인스턴스가 배포되면, 리더 선출 알고리즘을 통해 하나의 인스턴스만 리더로 선출됩니다.
2. 리더로 선출된 인스턴스만 실제 스케줄링 작업을 수행합니다.
3. 다른 인스턴스는 대기 상태로 유지되며, 현재 리더가 실패하면 새로운 리더가 선출됩니다.
4. 이 메커니즘은 Kubernetes의 리소스 잠금(resource lock)을 사용하여 구현됩니다.

**리더 선출 설정:**
버전이 지정된 설정 파일로 Lease 이름·네임스페이스·시간을 구성합니다:

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

**HA 배포:**
Part1의 전체 Deployment는 이미 같은 설정·ServiceAccount를 사용하는 두 복제본을 실행합니다. 격리된 실습에서는 세 개로 늘릴 수 있습니다. 이것만으로 운영 HA가 검증되지는 않습니다. 장애 영역 분리, API 연결, 부트스트랩 용량, 장애 전환을 확인하세요.

```bash
kubectl -n scheduler-lab scale deployment/custom-scheduler --replicas=3
kubectl -n scheduler-lab get lease custom-scheduler -o yaml
kubectl -n scheduler-lab logs -l app=custom-scheduler --prefix --tail=100
```

**독립 구현:**
kube-scheduler 명령에는 client-go 리더 선출이 통합되어 있습니다. 독립 구현은 프로세스별 고유 ID, 스케줄러 그룹별 공용 Lease, 갱신 권한, 리더십 상실 시 스케줄링 작업 취소가 필요합니다. client-go는 가능한 모든 프로세스 중첩에 대한 fencing을 제공하지 않습니다. 바인딩·외부 부작용에도 동시성 안전 설계가 필요합니다. `ReleaseOnCancel`을 사용하면 Lease를 반납하기 전에 보호 대상 작업이 중지되어야 합니다.

**리더 선출을 끌 수 있는 경우:**
의도적으로 격리한 실험이거나 롤아웃·장애 상황에도 단일 활성 프로세스를 보장하는 다른 장치가 있을 때만 끕니다. `replicas: 1`도 rolling update 중에는 중첩될 수 있습니다. 스케줄러 이름이 다르면 별도 선출 그룹이 필요하며, 이름만 다르다고 리더 선출을 꺼도 안전하지는 않습니다.

**다른 옵션들의 문제점:**
- A. 스케줄러에 리더십 권한 부여: 이는 모호한 설명으로, 리더 선출의 구체적인 목적을 설명하지 않습니다.
- C. 스케줄러를 클러스터의 리더 노드에서만 실행: 스케줄러 리더십은 프로세스에 속하며 클러스터 전체의 단일 리더 노드를 뜻하지 않습니다. 보조 스케줄러는 워커 노드의 Pod에서도 실행할 수 있습니다.
- D. 스케줄러에 다른 컴포넌트보다 높은 우선순위 부여: 리더 선출은 우선순위와 관련이 없으며, 여러 스케줄러 인스턴스 간의 조정을 위한 것입니다.
</details>

### 9. 다음 중 Kubernetes에서 파드의 스케줄링 우선순위를 설정하는 데 사용되는 리소스는 무엇인가요?

A. PodSchedulingPolicy  
B. PriorityClass  
C. SchedulingPriority  
D. PodPriority  

<details>
<summary>정답 보기</summary>

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
1. **value**: 우선순위 값으로, 높을수록 우선순위가 높습니다. 사용자 정의 값은 최대 1000000000이며 기본 critical 클래스는 예약된 상위 범위를 사용합니다.
2. **globalDefault**: true이면 클래스가 없는 신규 Pod의 클러스터 전체 기본값이 됩니다. 기존 Pod를 소급 변경하지 않으며 아래 실습 클래스는 모두 false를 사용합니다.
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
    image: nginx:1.30.4
```

**우선순위 및 선점 동작:**
1. **스케줄링 우선순위**: 우선순위가 높은 파드는 스케줄링 큐에서 우선적으로 처리됩니다.
2. **선점(Preemption)**: 우선순위가 높은 파드가 스케줄링될 노드가 없는 경우, 스케줄러는 우선순위가 낮은 파드를 제거(선점)하여 공간을 확보할 수 있습니다.
3. **선점 정책**: `preemptionPolicy: Never`인 Pod는 다른 Pod를 선점하지 않지만 자신은 선점될 수 있습니다. 높은 우선순위 Pod가 적합한 노드를 찾지 못해 backoff 중이면 더 낮은 우선순위 Pod가 진행할 수 있습니다.

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
globalDefault: false
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
package priorityexample

import (
    "sort"
    v1 "k8s.io/api/core/v1"
)

func podPriority(pod *v1.Pod) int32 {
    if pod == nil || pod.Spec.Priority == nil {
        return 0
    }
    return *pod.Spec.Priority
}

// Demonstrates only priority comparison, not queue backoff or requeue handling.
func sortPodsByPriority(pods []*v1.Pod) {
    sort.SliceStable(pods, func(i, j int) bool {
        return podPriority(pods[i]) > podPriority(pods[j])
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
B. 남은 allocatable과 Pod의 유효 요청 비교\
C. 노드의 운영체제와 파드의 호환성 확인  
D. 노드의 네트워크 대역폭 측정  

<details>
<summary>정답 보기</summary>

**정답: B. 남은 allocatable과 Pod의 유효 요청 비교**

**설명:**
`NodeResourcesFit`은 Pod의 유효 요청을 **노드 allocatable에서 이미 할당·assume된 요청을 뺀 값**과 비교합니다. Pod 개수 제한과 관련 확장 리소스도 검사합니다. 신규 Pod와 전체 `Capacity`만 비교하는 것이 아니며 CPU·메모리 limit 합이 용량을 넘는다고 일반적으로 거부하지도 않습니다.

**리소스 계산:**
* 일반 컨테이너, 순차 init 컨테이너, 재시작 가능한 sidecar, Pod overhead, 지원되는 Pod 수준 리소스 설정을 고려합니다. API 기본값 처리로 limit에서 request가 유도될 수 있습니다.
* assume된 바인딩을 포함한 스케줄러 스냅샷을 사용합니다. API로 Running Pod만 합산하면 예약된 수요를 놓칩니다.
* 대상 버전의 기능 게이트와 DRA 동작을 유지합니다. CPU·메모리 산술만으로 전체 리소스 적합성 검사를 구현할 수 없습니다.

**설정:**
`NodeResourcesFit`은 기본 활성화되어 있습니다. 아래는 Filter 단계를 제거하지 않고 점수 전략만 변경합니다.

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
  pluginConfig:
  - name: NodeResourcesFit
    args:
      scoringStrategy:
        type: MostAllocated
        resources:
        - name: cpu
          weight: 1
        - name: memory
          weight: 1
```

**스코어링 전략:**
NodeResourcesFit 플러그인은 다음과 같은 스코어링 전략을 지원합니다:

1. **LeastAllocated**: 리소스 요청 비율이 낮은 노드에 높은 점수를 부여하여 요청량을 분산합니다.
   ```
   score ≈ 100 × (allocatable - requested) / allocatable
   ```

2. **MostAllocated**: 리소스 요청 비율이 높은 노드에 높은 점수를 부여하여 요청량을 집중합니다. 이 전략 자체가 노드를 축소하지는 않습니다.
   ```
   score ≈ 100 × requested / allocatable
   ```

3. **RequestedToCapacityRatio**: 설정한 구간별 선형 shape를 사용하여 요청량과 allocatable의 비율에 점수를 매깁니다. 위 단일 리소스 식은 정수 반올림, 0·용량 초과 처리와 리소스 가중치를 생략한 설명용 식이며 실시간 사용률 식이 아닙니다.

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

**안전한 적합성 검사:**
스케줄러 프레임워크의 upstream 플러그인을 유지합니다. 신규 Pod의 CPU·메모리만 합산하고 기존 수요를 무시한 채 true를 반환하는 함수는 대체 구현이 아닙니다. 이번 감사에서는 고정한 upstream 구현을 로컬에서 검사합니다. 2코어 노드에 이미 1500m 요청이 있을 때 추가 1코어 요청은 거부되고 250m 요청은 CPU limit이 더 커도 적합합니다. 이는 로컬 리소스 계산 검사이며 클러스터 스케줄링 벤치마크가 아닙니다.

`kubectl top`은 Metrics Server가 있을 때 현재 메트릭을 보여주며 기본 fit/score가 사용하는 요청량 합계가 아닙니다. 차이를 진단할 때 init 컨테이너와 overhead를 포함한 전체 Pod 스펙을 확인하세요.

**다른 옵션들의 문제점:**
- A. 노드의 물리적 위치에 따라 파드 배치: 이는 토폴로지 관련 플러그인(예: NodeAffinity, PodTopologySpread)의 역할입니다.
- C. 노드의 운영체제와 파드의 호환성 확인: OS 레이블과 배치 제약을 적절히 사용하되 이미지·런타임 호환성 자체를 보장하지는 않습니다. `NodeResourcesFit`은 해당 검사가 아닙니다.
- D. 노드의 네트워크 대역폭 측정: Kubernetes 스케줄러는 기본적으로 네트워크 대역폭을 고려하지 않습니다. 이를 위해서는 사용자 정의 메트릭과 플러그인이 필요합니다.
</details>

## 참고 자료

[Part1 모듈과 배포 구성](../../scheduling/01-custom-scheduler-part1.md)을 사용합니다. 로컬 컴파일·설정·리소스 계산 검사는 운영 적합성 검증이 아니며 클러스터·AWS 배포는 실행하지 않았습니다.

* [스케줄러 설정과 기본 플러그인](https://kubernetes.io/docs/reference/scheduling/config/)
* [프레임워크 확장 포인트](https://kubernetes.io/docs/concepts/scheduling-eviction/scheduling-framework/)
* [리소스 점수 전략](https://kubernetes.io/docs/concepts/scheduling-eviction/resource-bin-packing/)
* [우선순위와 선점](https://kubernetes.io/docs/concepts/scheduling-eviction/pod-priority-preemption/)
* [고정 버전 Go 인터페이스](https://github.com/kubernetes/kubernetes/blob/v1.35.8/staging/src/k8s.io/kube-scheduler/framework/interface.go)
