# Custom Scheduler 퀴즈 (Part 3)

> **예제 기준 버전**: Kubernetes 1.35.8, Go 1.27.1; native 1.37 기능은 별도 설명
> **마지막 업데이트**: 2026년 9월 11일

이 퀴즈는 Kubernetes에서 Custom Scheduler를 구현하고 사용하는 방법에 대한 고급 이해를 테스트합니다.

## 퀴즈 문제

### 1. 여러 스케줄러에 관한 설명 중 틀린 것은 무엇인가요?

A. 스케줄러 추가로 API watch와 캐시 작업이 늘어난다
B. 독립적으로 assume한 배치가 리소스를 경합할 수 있다
C. 스케줄러를 추가하면 노드 용량이 자동으로 늘어난다
D. 서로 다른 스케줄러 그룹은 별도 리더 선출 Lease가 필요하다

<details>
<summary>정답 보기</summary>

**정답: C. 스케줄러를 추가하면 노드 용량이 자동으로 늘어난다**

**설명:**
스케줄러는 Pod를 할당하며 노드 용량을 만들지 않습니다. 추가 스케줄러는 API·네트워크 부하를 늘릴 수 있습니다. 각각 확정된 Pod 상태를 감시하지만 메모리의 assume 상태는 다른 스케줄러와 공유하는 예약 트랜잭션이 아닙니다. 리소스 필터를 유지하고 공유 노드 풀의 동시 배치를 검증해야 합니다.

`schedulerName`을 생략하면 `default-scheduler`가 선택되며 모든 정상 스케줄러가 경쟁하는 것은 아닙니다. 같은 스케줄러의 HA 복제본은 의도적으로 Lease를 공유합니다. 서로 다른 그룹이 같은 Lease를 사용하면 상대를 막을 수 있고 같은 프로필의 프로세스가 리더십을 조정하지 않으면 경합할 수 있습니다.

**Pod 라우팅 예제:**

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: default-pod
spec:
  containers:
  - name: nginx
    image: nginx:1.30.4
    resources:
      requests:
        cpu: 100m
        memory: 64Mi
---
apiVersion: v1
kind: Pod
metadata:
  name: custom-pod
spec:
  schedulerName: custom-scheduler
  tolerations:
  - key: dedicated
    operator: Equal
    value: custom-scheduler
    effect: NoSchedule
  containers:
  - name: nginx
    image: nginx:1.30.4
    resources:
      requests:
        cpu: 100m
        memory: 64Mi
```

**스케줄러 식별자와 노드 풀 정책 분리:**
Part1의 전체 Deployment/RBAC를 사용합니다. 이름과 Lease는 과거 `--scheduler-name` 플래그가 아닌 `KubeSchedulerConfiguration`에 둡니다. 기본 `NodeAffinity` 플러그인은 프로필의 `addedAffinity`를 지원하며 기본 `NodeSelector` 플러그인은 없습니다.

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
  - name: NodeAffinity
    args:
      addedAffinity:
        requiredDuringSchedulingIgnoredDuringExecution:
          nodeSelectorTerms:
          - matchExpressions:
            - key: training.example.com/scheduler-pool
              operator: In
              values:
              - custom
```

```bash
# Only label/taint a node selected for this isolated lab.
: "${CUSTOM_NODE:?Select the lab node}"
kubectl label node "$CUSTOM_NODE" training.example.com/scheduler-pool=custom --overwrite
kubectl taint node "$CUSTOM_NODE" dedicated=custom-scheduler:NoSchedule --overwrite
```

위 커스텀 Pod는 예제 taint를 허용합니다. toleration은 배치를 강제하지 않고 스케줄러 이름·노드 레이블·quota는 보안 경계가 아닙니다. 아래 namespace quota는 어드미션되는 요청량을 제한하며 노드 풀을 예약하지 않습니다. 네임스페이스를 먼저 만들고 quota 대상 워크로드에 requests를 지정하세요.
**네임스페이스 quota 예제:**
   ```yaml
   apiVersion: v1
   kind: ResourceQuota
   metadata:
     name: default-scheduler-quota
     namespace: default-workloads
   spec:
     hard:
       pods: "10"
       requests.cpu: "20"
       requests.memory: 40Gi
   
   ---
   apiVersion: v1
   kind: ResourceQuota
   metadata:
     name: custom-scheduler-quota
     namespace: custom-workloads
   spec:
     hard:
       pods: "10"
       requests.cpu: "20"
       requests.memory: 40Gi
   ```

**보조 스케줄러 읽기 전용 확인:**
실제 네임스페이스·레이블을 사용합니다. EKS 관리형 컨트롤 플레인 구성 요소는 여기의 보조 Deployment와 다릅니다.

```bash
kubectl -n scheduler-lab get pods -l app=custom-scheduler
kubectl -n scheduler-lab logs -l app=custom-scheduler --prefix --tail=100
kubectl -n scheduler-lab get lease custom-scheduler
kubectl get pods -A --field-selector=spec.schedulerName=custom-scheduler,spec.nodeName= -o wide
```

**다른 선택지:** A·B·D는 실제 부하·조정 시 고려할 사항입니다.
</details>

### 2. Kubernetes 스케줄러에서 "Permit" 확장 포인트의 역할은 무엇인가요?

A. 파드를 노드에 바인딩  
B. 파드의 스케줄링을 허용, 거부 또는 지연  
C. 파드를 실행할 수 없는 노드 제외  
D. 노드에 점수 부여  

<details>
<summary>정답 보기</summary>

**정답: B. 파드의 스케줄링을 허용, 거부 또는 지연**

**설명:**
Kubernetes 스케줄링 프레임워크에서 "Permit" 확장 포인트의 역할은 파드의 스케줄링을 허용, 거부 또는 지연하는 것입니다. Permit 플러그인은 노드가 선택된 후 바인딩 단계 전에 실행되며, 파드의 스케줄링 결정에 대한 최종 승인 또는 거부를 제공합니다.

**Permit 확장 포인트의 주요 기능:**
1. **허용(Allow)**: 파드의 스케줄링을 허용하여 바인딩 단계로 진행합니다.
2. **거부(Deny)**: 파드의 스케줄링을 거부하여 다른 노드를 선택하도록 합니다.
3. **지연(Wait)**: 파드의 스케줄링을 일시적으로 지연시키고, 특정 조건이 충족될 때까지 대기합니다.

**버전별 Permit 계약:**
`Permit(ctx, fwk.CycleState, pod, nodeName)`은 상태와 대기 시간을 반환합니다. `Success`는 진행, `Wait`는 프레임워크 대기, `Unschedulable` 같은 실패 상태는 해당 시도 거부입니다. `framework.Deny` enum은 없습니다. 거부 즉시 다른 노드에 바인딩하지 않으며 재시도·backoff·예약 정리가 뒤따릅니다.

`TaintToleration`·`PodTopologySpread`는 기본 Permit 플러그인이 아닙니다. 예제는 이들의 실제 Filter·Score 단계를 유지합니다.

**전체 인터페이스 예제 (`quizplugins/permit.go`):**
어노테이션 값은 테스트 지시이며 신뢰할 수 있는 인가가 아닙니다. 외부 승인 서비스는 제공하지 않습니다. `wait` Pod는 프레임워크 등록 이후 통합된 테스트 드라이버가 해제하지 않으면 시간 초과됩니다. 읽는 쪽이 없는 자체 채널로 프레임워크 대기를 해제할 수 없습니다.

```go
package quizplugins

import (
	"context"
	"time"

	v1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/apimachinery/pkg/types"
	fwk "k8s.io/kube-scheduler/framework"
)

type CustomPermit struct{ handle fwk.Handle }

var _ fwk.PermitPlugin = &CustomPermit{}

func (*CustomPermit) Name() string { return "CustomPermit" }

func (*CustomPermit) Permit(_ context.Context, _ fwk.CycleState, pod *v1.Pod, _ string) (*fwk.Status, time.Duration) {
	// These are test directives, not an authorization or approval mechanism.
	switch pod.Annotations["training.example.com/permit"] {
	case "", "allow":
		return nil, 0
	case "wait":
		return fwk.NewStatus(fwk.Wait, "waiting for the test driver"), 30 * time.Second
	case "deny":
		return fwk.NewStatus(fwk.UnschedulableAndUnresolvable, "test driver denied"), 0
	default:
		return fwk.NewStatus(fwk.Error, "unknown test permit directive"), 0
	}
}

// Call only after the framework has registered the waiting Pod. The caller
// must handle false (not registered yet, already released, deleted or timed out).
func (p *CustomPermit) Allow(uid types.UID) bool {
	waiting := p.handle.GetWaitingPod(uid)
	if waiting == nil {
		return false
	}
	waiting.Allow(p.Name())
	return true
}

func (p *CustomPermit) Reject(uid types.UID, reason string) bool {
	waiting := p.handle.GetWaitingPod(uid)
	if waiting == nil {
		return false
	}
	waiting.Reject(p.Name(), reason)
	return true
}

func NewPermit(_ context.Context, _ runtime.Object, handle fwk.Handle) (fwk.Plugin, error) {
	return &CustomPermit{handle: handle}, nil
}
```

뒤의 PreBind 예제와 함께 `cmd/quiz-scheduler/main.go`에 등록합니다. 두 소스 파일을 모두 저장한 뒤 빌드하세요:

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
		app.WithPlugin("CustomPermit", quizplugins.NewPermit),
		app.WithPlugin("IdentityPreBind", quizplugins.NewPreBind),
	)
	os.Exit(cli.Run(command))
}
```

Part1 모듈에서 `CGO_ENABLED=0 go build -buildvcs=false -o custom-scheduler ./cmd/quiz-scheduler`로 빌드합니다. 필요한 확장 지점만 활성화하고 기본값을 유지합니다:

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
    permit:
      enabled:
      - name: CustomPermit
```

**Permit 사용 사례:**
1. **Gang 스케줄링**: 모든 관련 파드가 스케줄링될 준비가 될 때까지 파드 그룹의 스케줄링을 지연합니다.
2. **리소스 예약**: 파드가 스케줄링되기 전에 외부 리소스를 예약합니다.
3. **정책 검증**: 파드 스케줄링이 조직 정책을 준수하는지 확인합니다.
4. **승인 워크플로우**: 파드 스케줄링에 대한 외부 승인을 요청합니다.

**Permit 대기만으로 gang 스케줄러가 완성되지 않는 이유:**
실제 구현은 namespace·UID로 그룹을 구분하고 고유 멤버를 세며 재시도·삭제·타임아웃·실패 시 예약 해제·바인딩 실패를 처리해야 합니다. 자체 `WaitingPod`를 만들거나 재시도를 중복 계산하거나 Permit이 반환되기 전에 현재 Pod가 등록되었다고 가정하면 안 됩니다. 대기 장치만으로 동시 컨테이너 시작이나 기아 방지를 보장하지 않습니다. 3번은 유지되는 구현을 설명합니다.

**다른 옵션들의 문제점:**
- A. 파드를 노드에 바인딩: 이는 "Bind" 확장 포인트의 역할입니다.
- C. 파드를 실행할 수 없는 노드 제외: 이는 "Filter" 확장 포인트의 역할입니다.
- D. 노드에 점수 부여: 이는 "Score" 확장 포인트의 역할입니다.
</details>
### 3. Kubernetes에서 Gang 스케줄링(Gang Scheduling)의 주요 목적은 무엇인가요?

A. 파드를 특정 노드에만 배치  
B. 필요한 Pod 그룹의 배치를 조정\
C. 파드를 다양한 노드에 균등하게 분산  
D. 파드를 우선순위에 따라 스케줄링  

<details>
<summary>정답 보기</summary>

**정답: B. 필요한 Pod 그룹의 배치를 조정**

**설명:**
Kubernetes에서 Gang 스케줄링(Gang Scheduling)의 주요 목적은 필요한 Pod 그룹의 배치를 조정하는 것입니다. 이는 모든 구성 요소가 동시에 실행되어야 하는 분산 학습 작업, 분산 데이터 처리 작업 등의 워크로드에 중요합니다.

**Gang 스케줄링의 필요성:**
1. **All-or-Nothing 요구 사항**: 일부 워크로드는 모든 구성 요소가 동시에 실행되어야 하며, 일부만 실행되면 작업이 진행되지 않습니다.
2. **리소스 낭비 방지**: 일부 파드만 스케줄링되고 나머지는 대기 상태인 경우, 이미 스케줄링된 파드가 사용하는 리소스가 낭비될 수 있습니다.
3. **데드락 방지**: 서로 의존하는 파드가 서로 다른 시점에 스케줄링되면 데드락이 발생할 수 있습니다.

**구현 선택과 버전:**
upstream Kubernetes 1.35에는 opt-in alpha `GenericWorkload`·`GangScheduling`이 도입됐습니다. 현재 upstream 1.37의 PodGroup scheduling은 **beta이며 기본 비활성화**이고 `GenericWorkload`와 `scheduling.k8s.io/v1beta1` API가 필요합니다. 이것이 EKS에서의 기능 제공이나 관리형 컨트롤 플레인 플래그 변경 가능성을 입증하지는 않습니다.

Volcano는 별도로 설치하는 스케줄러입니다. Kube-batch는 역사적인 전신이며 별도 최신 권고 대상이 아닙니다. 지원되는 컨트롤러·CRD·활성화된 gang 스케줄링·Open queue가 전제입니다.

**Volcano Job 예제 (1.15.2 스키마 검증):**
컨트롤러가 PodGroup을 생성합니다. minMember4에 Pod 하나만 선언하는 대신 네 멤버를 모두 정의합니다. CPU만 요청하는 sleep 워크로드는 매니페스트 관계를 설명하며 분산 학습·벤치마크가 아닙니다. 배포하지 않았습니다.

```yaml
apiVersion: batch.volcano.sh/v1alpha1
kind: Job
metadata:
  name: gang-demo
  namespace: default
spec:
  minAvailable: 4
  schedulerName: volcano
  queue: default
  maxRetry: 1
  tasks:
  - name: workers
    replicas: 4
    template:
      spec:
        restartPolicy: Never
        containers:
        - name: worker
          image: busybox:1.37.0
          command:
          - sh
          - -c
          - sleep 60
          resources:
            requests:
              cpu: 250m
              memory: 128Mi
            limits:
              memory: 256Mi
```

스케줄링 결정은 최소 그룹을 조정하지만 프로세스를 같은 순간에 시작하지는 않습니다. 애플리케이션 barrier·타임아웃·공정성·복구가 여전히 필요합니다. native PodGroup 배치에도 이기종 Pod·Pod 간 의존성에 관한 제한이 있으며, 순서 알고리즘이 가능한 모든 배치를 찾아내지는 않습니다.

**Gang 스케줄링의 장단점:**
장점:
- 필요한 Pod 그룹의 배치를 조정
- 리소스 낭비 방지
- 부분 할당 데드락을 줄일 수 있으나 공정성·타임아웃은 여전히 필요

단점:
- 구현 복잡성 증가
- 스케줄링 지연 가능성
- 클러스터 리소스 활용도 감소 가능성

**Gang 스케줄링이 필요한 워크로드:**
1. **분산 학습 작업**: TensorFlow, PyTorch 등의 분산 학습 프레임워크
2. **분산 데이터 처리**: Spark, Flink 등의 분산 데이터 처리 프레임워크
3. **MPI 작업**: 고성능 컴퓨팅(HPC) 워크로드
4. **밀접한 병렬 작업**: 선언한 최소 worker 집합이 필요한 워크로드

**다른 옵션들의 문제점:**
- A. 파드를 특정 노드에만 배치: 이는 노드 셀렉터 또는 노드 어피니티의 역할입니다.
- C. 파드를 다양한 노드에 균등하게 분산: 이는 파드 토폴로지 분산 제약 조건의 역할입니다.
- D. 파드를 우선순위에 따라 스케줄링: 이는 파드 우선순위 및 선점의 역할입니다.
</details>

### 4. kube-scheduler extender callback 계약에 해당하지 않는 기능은 무엇인가요?

A. 후보 노드 필터링
B. 후보 노드 우선순위 평가
C. 선택적인 Pod와 노드 바인딩
D. ValidatingWebhookConfiguration을 통한 어드미션 검증

<details>
<summary>정답 보기</summary>

**정답: D. ValidatingWebhookConfiguration을 통한 어드미션 검증**

extender는 설정한 filter·prioritize·preempt·bind callback을 구현할 수 있습니다. 특정 URL 경로가 필수인 것은 아닙니다. `filterVerb`에 `validate` 경로를 지정해도 payload와 의미는 여전히 필터링입니다. 어드미션 webhook은 다른 API 계약입니다.

**설정:**
Part2의 TLS 서비스·인증서 전제를 재사용합니다. `extenders`는 최상위 필드입니다. 필수 filter는 실패 시 차단하고 기본 리소스 계산을 유지합니다.

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

**Wire 계약:**
* Filter·prioritize는 `ExtenderArgs`의 `Pod`와, `nodeCacheCapable`에 따라 전체 `Nodes` 또는 `NodeNames`를 사용합니다.
* Filter는 `Nodes`·`NodeNames`, 실패 map, `Error`를 반환합니다.
* Prioritize는 `[{"Host":"node-a","Score":7}]` 같은 배열 자체를 반환하며 점수는100이 아닌0–10입니다. 오류 시 해당 extender 점수가 제외되므로 필수 제약을 점수로 강제할 수 없습니다.
* Bind는 `PodName`·`PodNamespace`·`PodUID`·`Node`를 받습니다. 실제 바인딩 성공 후에만 성공을 반환하세요. nil만 반환하는 `customBind`는 바인딩 구현이 아닙니다.
* Preempt는 후보 victim map을 담은 `ExtenderPreemptionArgs`를 받고 `ExtenderPreemptionResult.NodeNameToMetaVictims`를 반환합니다. 임의의 `podsToPreempt` envelope가 아닙니다.

[Part2](../../scheduling/02-custom-scheduler-part2.md)의 입력이 제한된 전체 핸들러를 사용합니다. 그 예제는 `bindVerb`를 생략해 `DefaultBinder`를 유지합니다. 여기서는 추가 HTTP 서버나 가짜 성공을 반환하는 바인딩 엔드포인트를 제공하지 않습니다.
</details>
### 5. Kubernetes에서 스케줄러 프레임워크의 "PostFilter" 확장 포인트의 역할은 무엇인가요?

A. 필터링 후 노드에 점수 부여  
B. 필터링 후 파드를 노드에 바인딩  
C. 필터링 실패 시 선점 로직 실행  
D. 필터링 후 파드 상태 업데이트  

<details>
<summary>정답 보기</summary>

**정답: C. 필터링 실패 시 선점 로직 실행**

**설명:**
PostFilter는 필터링으로 적격 노드를 찾지 못할 때 복구를 시도하며 기본 선점은 한 구현입니다. 모든 노드가 필터링 단계에서 제외되어 파드를 스케줄링할 수 없는 경우, PostFilter 플러그인은 이후 시도가 가능하도록 조치를 취할 수 있습니다.

**PostFilter 확장 포인트의 주요 기능:**
1. **선점 후보 식별**: 선점할 수 있는 파드와 노드를 식별합니다.
2. **선점 시뮬레이션**: 선점 후 파드가 스케줄링될 수 있는지 시뮬레이션합니다.
3. **선점 결정**: 최적의 선점 전략을 결정합니다.

**버전별 인터페이스와 안전한 확장:**
고정 버전 API는 `fwk.CycleState`·`fwk.NodeToStatusReader`를 사용하며 `PostFilterResult`에는 `NominatingInfo`가 포함됩니다. nomination은 가능한 다음 후보이지 확정된 바인딩이 아닙니다.

완전하게 검증한 대안이 없다면 기본 `DefaultPreemption`을 유지합니다. 낮은 우선순위 victim 제거 후 남는 제약을 평가하며 PDB 위반을 best effort로 고려합니다. victim 선택을 생략한 루프에서 Pod를 직접 삭제하면 안 됩니다. 복구 플러그인은 다른 적합한 작업도 할 수 있으므로 PostFilter의 정의가 선점으로만 제한되지는 않습니다.

아래 설정은 기본 구현을 끄지 않고 조정합니다. 후보 수 제한은 탐색을 제한하며 전역 최적성·최종 스케줄링을 보장하지 않습니다.

**선점 관련 설정:**
```yaml
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
profiles:
- schedulerName: custom-scheduler
  pluginConfig:
  - name: DefaultPreemption
    args:
      minCandidateNodesPercentage: 10
      minCandidateNodesAbsolute: 100
leaderElection:
  leaderElect: true
  resourceLock: leases
  resourceName: custom-scheduler
  resourceNamespace: scheduler-lab
  leaseDuration: 15s
  renewDeadline: 10s
  retryPeriod: 2s
```

**선점 프로세스:**
1. 파드가 모든 노드에서 필터링 단계를 통과하지 못하면 PostFilter 단계가 호출됩니다.
2. PostFilter 플러그인은 선점 후보 노드를 식별합니다.
3. 각 노드에서 선점할 파드를 결정합니다.
4. 선점 후 파드가 스케줄링될 수 있는지 확인합니다.
5. 최적의 선점 전략을 선택합니다.
6. 선택된 노드를 파드의 nominatedNodeName으로 설정합니다.
7. 선점된 파드는 정상적으로 종료(graceful termination)됩니다.
8. victim 종료 후 스케줄링을 재시도하며 nomination이 바인딩을 보장하지 않습니다.

**선점 관련 지표 모니터링:**
```bash
# nomination을 확인합니다. 스케줄러 메트릭은 별도 인증 HTTPS 엔드포인트에서 수집합니다.
kubectl get pods -A -o custom-columns=NAME:.metadata.name,NOMINATED:.status.nominatedNodeName
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

A. 요청된 CPU·메모리 비율이 균형 잡힌 노드에 높은 점수 부여\
B. 노드의 리소스 사용량이 적은 노드에 높은 점수 부여  
C. 노드의 리소스 사용량이 많은 노드에 높은 점수 부여  
D. 노드의 리소스 제한을 설정  

<details>
<summary>정답 보기</summary>

**정답: A. 요청된 CPU·메모리 비율이 균형 잡힌 노드에 높은 점수 부여**

**설명:**
`NodeResourcesBalancedAllocation`은 실측 CPU·메모리 사용률이 아닌 **유효 요청량/allocatable 비율**을 균형 있게 평가합니다. 고정 구현에서 포함된 리소스가 두 개이면:

```
cpuFraction = min(requestedCPU / allocatableCPU, 1)
memoryFraction = min(requestedMemory / allocatableMemory, 1)
std = abs(cpuFraction - memoryFraction) / 2
score = int((1 - std) * 100)
```

요청량 합계에는 신규 Pod와 스케줄러가 계산한 기존 요청이 포함됩니다. 전체 플러그인은 버전별 리소스 옵션도 처리합니다. 리소스가 두 개보다 많으면 모집단 표준편차를 사용합니다.

실측이 아닌 산술 예제로 비율80%/80%는100,90%/50%는80,30%/90%는70점입니다. 다른 플러그인과 가중치도 최종 노드 선택에 영향을 줍니다.

**스케줄러 구성에서 NodeResourcesBalancedAllocation 플러그인 활성화:**
```yaml
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
profiles:
- schedulerName: custom-scheduler
  plugins:
    score:
      enabled:
      - name: NodeResourcesBalancedAllocation
        weight: 2
leaderElection:
  leaderElect: true
  resourceLock: leases
  resourceName: custom-scheduler
  resourceNamespace: scheduler-lab
  leaseDuration: 15s
  renewDeadline: 10s
  retryPeriod: 2s
```

**플러그인 구성:**
```yaml
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
profiles:
- schedulerName: custom-scheduler
  pluginConfig:
  - name: NodeResourcesBalancedAllocation
    args:
      resources:
      - name: cpu
        weight: 1
      - name: memory
        weight: 1
leaderElection:
  leaderElect: true
  resourceLock: leases
  resourceName: custom-scheduler
  resourceNamespace: scheduler-lab
  leaseDuration: 15s
  renewDeadline: 10s
  retryPeriod: 2s
```

**NodeResourcesBalancedAllocation vs 다른 스코어링 플러그인:**
1. **NodeResourcesBalancedAllocation**: 요청량/allocatable 비율이 균형 잡힌 노드를 선호합니다.
2. **NodeResourcesFit**: 설정된 LeastAllocated·MostAllocated·RequestedToCapacityRatio 점수 전략을 사용합니다.
3. **NodeResourcesFit의 LeastAllocated 전략**: 요청 비율이 낮은 노드를 선호합니다.
4. **NodeResourcesFit의 MostAllocated 전략**: 요청 비율이 높은 노드를 선호합니다.

**사용 사례:**
1. **리소스 균형**: 클러스터 전체의 CPU와 메모리 사용 균형을 개선합니다.
2. **병목 현상 방지**: 요청량 불균형을 줄일 수 있지만 런타임 병목을 방지하지는 않습니다.
3. **확장성 개선**: 리소스 사용 균형이 좋은 클러스터는 더 효율적으로 확장될 수 있습니다.

**산술 도우미 (`scoring/formulas.go`):**
점수 식과 본문에서 다룬 선택적인70:30 GPU 가중치를 확인합니다. 전체 스케줄러 플러그인은 아닙니다. CPU millicore, init·sidecar, overhead, 기능별 처리를 포함한 기본 리소스 계산을 유지하세요.

```go
package scoring

import (
	"fmt"
	"math"
)

// Two-resource form of the pinned BalancedAllocation formula.
// Inputs are effective requested/allocatable fractions, not live utilization.
func BalancedScore(cpuFraction, memoryFraction float64) (int64, error) {
	for _, value := range []float64{cpuFraction, memoryFraction} {
		if math.IsNaN(value) || math.IsInf(value, 0) || value < 0 {
			return 0, fmt.Errorf("fractions must be finite and non-negative")
		}
	}
	cpuFraction = math.Min(cpuFraction, 1)
	memoryFraction = math.Min(memoryFraction, 1)
	std := math.Abs(cpuFraction-memoryFraction) / 2
	return int64((1 - std) * 100), nil
}

// Optional policy arithmetic only; no GPU telemetry collector is implemented here.
// The caller must establish freshness and workload/device relevance first.
func WeightedGPUScore(packing int64, utilization float64) (int64, error) {
	if packing < 0 || packing > 100 || math.IsNaN(utilization) || math.IsInf(utilization, 0) || utilization < 0 || utilization > 1 {
		return 0, fmt.Errorf("packing must be 0..100 and utilization finite in 0..1")
	}
	utilizationScore := int64((1 - utilization) * 100)
	return (packing*7 + utilizationScore*3) / 10, nil
}
```

**다른 옵션들의 문제점:**
- B. 노드의 리소스 사용량이 적은 노드에 높은 점수 부여: 이는 NodeResourcesFit의 LeastAllocated 전략입니다.
- C. 노드의 리소스 사용량이 많은 노드에 높은 점수 부여: 이는 NodeResourcesFit의 MostAllocated 전략입니다.
- D. 노드의 리소스 제한을 설정: 이는 스케줄러 플러그인의 역할이 아니며, 노드 리소스 제한은 노드 자체의 속성입니다.
</details>
### 7. Kubernetes에서 스케줄러의 "PreBind" 확장 포인트의 역할은 무엇인가요?

A. 파드를 노드에 바인딩  
B. 바인딩 전에 필요한 작업 수행  
C. 바인딩 후 정리 작업 수행  
D. 바인딩 실패 시 복구 작업 수행  

<details>
<summary>정답 보기</summary>

**정답: B. 바인딩 전에 필요한 작업 수행**

**설명:**
PreBind는 Pod 바인딩 확정 전에 전제 조건을 조정합니다. `VolumeBinding`은 스토리지 컨트롤러와 스케줄링 관련 볼륨 바인딩·프로비저닝을 조정합니다. `DefaultPreBind`라는 기본 플러그인은 없습니다.

1.35.8 인터페이스는 `fwk.CycleState`를 사용하는 **PreBindPreFlight와 PreBind 모두**를 포함합니다. Preflight는 불필요한 작업을 피하도록 Pod에 Skip을 반환할 수 있습니다.

**전체 읽기 전용 예제 (`quizplugins/prebind.go`):**
이 opt-in 식별자 검사는 볼륨을 프로비저닝하거나 CNI·서비스 엔드포인트·GPU를 구성하지 않습니다. 해당 작업에는 실제 컨트롤러·장치 기제가 필요합니다. `DefaultBinder`도 이미 UID를 전달하므로 추가 API 요청은 인터페이스 설명용입니다.

```go
package quizplugins

import (
	"context"
	"fmt"
	"time"

	v1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
	fwk "k8s.io/kube-scheduler/framework"
)

type IdentityPreBind struct{ handle fwk.Handle }

var _ fwk.PreBindPlugin = &IdentityPreBind{}

func (*IdentityPreBind) Name() string { return "IdentityPreBind" }

func (*IdentityPreBind) PreBindPreFlight(_ context.Context, _ fwk.CycleState, pod *v1.Pod, _ string) *fwk.Status {
	if pod.Annotations["training.example.com/check-identity"] != "true" {
		return fwk.NewStatus(fwk.Skip)
	}
	return nil
}

// Read-only interface demonstration. DefaultBinder already carries the Pod UID;
// this extra API round trip is not required for ordinary scheduling.
func (p *IdentityPreBind) PreBind(parent context.Context, _ fwk.CycleState, pod *v1.Pod, _ string) *fwk.Status {
	ctx, cancel := context.WithTimeout(parent, 3*time.Second)
	defer cancel()
	current, err := p.handle.ClientSet().CoreV1().Pods(pod.Namespace).Get(ctx, pod.Name, metav1.GetOptions{})
	if err != nil {
		return fwk.AsStatus(err)
	}
	if current.UID != pod.UID || current.DeletionTimestamp != nil || current.Spec.NodeName != "" {
		return fwk.AsStatus(fmt.Errorf("Pod identity/state changed before binding"))
	}
	return nil
}

func NewPreBind(_ context.Context, _ runtime.Object, handle fwk.Handle) (fwk.Plugin, error) {
	return &IdentityPreBind{handle: handle}, nil
}
```

2번 명령에서 등록합니다. `VolumeBinding`을 유지하세요:

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
    preBind:
      enabled:
      - name: IdentityPreBind
```

**책임 구분:**
스토리지 프로비저닝은 해당 provisioner·controller가 수행하고 스케줄러는 배치·바인딩을 조정합니다. CNI 네트워크와 Secret·볼륨 마운트는 할당 이후 런타임·kubelet 경로에서 처리합니다. Service·EndpointSlice·로드 밸런서 컨트롤러는 자체 리소스를 조정합니다. 커스텀 플러그인이 외부 예약을 조정하면 제한된 시간·멱등성·자체 Unreserve 정리를 구현해야 하며 프레임워크가 임의의 외부 부작용을 자동으로 되돌리지는 않습니다.

**PreBind 실패 처리:**
PreBind 플러그인이 실패를 반환하면:
1. 스케줄링 사이클이 중단됩니다.
2. 파드는 다시 스케줄링 큐에 들어갑니다.
3. Unreserve가 플러그인 소유의 assume 상태를 해제합니다. 외부 자원 정리는 실제로 구현해야 합니다.
4. 실패 이벤트가 기록됩니다.

**PreBind 로그 및 이벤트 모니터링:**
```bash
# 스케줄러 로그에서 PreBind 관련 메시지 확인
kubectl -n scheduler-lab logs -l app=custom-scheduler --prefix --tail=100

# 파드 이벤트 확인
kubectl describe pod <pod-name>
```

**다른 옵션들의 문제점:**
- A. 파드를 노드에 바인딩: 이는 "Bind" 확장 포인트의 역할입니다.
- C. 바인딩 후 정리 작업 수행: 이는 "PostBind" 확장 포인트의 역할입니다.
- D. 실패 복구에는 플러그인 예약의 Unreserve와 프레임워크 재시도 처리가 포함됩니다.
</details>

### 8. Kubernetes에서 스케줄러의 "NodeResourcesFit" 플러그인의 주요 목적은 무엇인가요?

A. 노드의 리소스 사용량 모니터링  
B. 노드의 리소스 제한 설정  
C. 남은 allocatable과 Pod의 유효 요청 비교\
D. 노드의 리소스 사용 균형 유지  

<details>
<summary>정답 보기</summary>

**정답: C. 남은 allocatable과 Pod의 유효 요청 비교**

**설명:**
`NodeResourcesFit`은 유효 Pod 요청을 **할당·assume된 요청을 제외한 allocatable**과 비교하며 적용되는 Pod 개수·확장 리소스 제약도 검사합니다. CPU·메모리 limit 합을 용량과 비교하는 일반 검사가 아닙니다. 어드미션·기본값에서 유도된 요청, init·재시작 가능한 sidecar·overhead·활성화된 리소스 기능을 고려해야 합니다.

기본 Filter를 유지합니다. 아래 설정은 적합성 로직을 교체하지 않고 점수 동작을 조정합니다.

**NodeResourcesFit 플러그인 구성:**
```yaml
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
profiles:
- schedulerName: custom-scheduler
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
leaderElection:
  leaderElect: true
  resourceLock: leases
  resourceName: custom-scheduler
  resourceNamespace: scheduler-lab
  leaseDuration: 15s
  renewDeadline: 10s
  retryPeriod: 2s
```

**스코어링 전략:**
NodeResourcesFit 플러그인은 다음과 같은 스코어링 전략을 지원합니다:

1. **LeastAllocated**: 요청 비율이 낮은 노드에 높은 점수를 부여합니다.
   ```
   score ≈ 100 × (allocatable - requested) / allocatable
   ```

2. **MostAllocated**: 요청 비율이 높은 노드에 높은 점수를 부여합니다.
   ```
   score ≈ 100 × requested / allocatable
   ```

3. **RequestedToCapacityRatio**: 설정한 구간별 선형 shape로 요청량/allocatable 비율을 평가합니다. 위 식은 단일 리소스 설명용입니다.

**커스텀 구현 주의점:**
upstream `NodeResourcesFit`을 유지하세요. 점수 가중치 map에 나열된 리소스만 검사하면 필수 리소스를 빠뜨릴 수 있고 CPU `Quantity.Value()`는 millicore 정밀도를 잃습니다. 일반 컨테이너만 합산하면 init·sidecar·overhead를 놓치며 비율을 스케일링 전에 정수로 바꾸면 점수가 모두0이 될 수 있습니다.

Part1의 로컬 검사는 실제 고정 버전 fit 함수를 사용합니다. 2코어 노드에1500m 요청이 있으면 추가1코어는 맞지 않지만250m는 CPU limit이 더 커도 적합합니다. 합성 리소스 계산 테스트이며 클러스터 벤치마크가 아닙니다.

**리소스 요청 및 제한 예시:**
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: resource-demo
spec:
  containers:
  - name: nginx
    image: nginx:1.30.4
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
<summary>정답 보기</summary>

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
    image: nginx:1.30.4
```

**InterPodAffinity 플러그인 구성:**
```yaml
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
profiles:
- schedulerName: custom-scheduler
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
        weight: 2
  pluginConfig:
  - name: InterPodAffinity
    args:
      hardPodAffinityWeight: 1
leaderElection:
  leaderElect: true
  resourceLock: leases
  resourceName: custom-scheduler
  resourceNamespace: scheduler-lab
  leaseDuration: 15s
  renewDeadline: 10s
  retryPeriod: 2s
```

**완전한 기본 구현 사용:**
전처리를 포함한 `InterPodAffinity`를 유지합니다. namespace 선택, 신규 required 조건, 기존 Pod의 required anti-affinity, 토폴로지, self-affinity의 첫 Pod 처리를 고려합니다. `*v1.Affinity` 자체는 Clone이 있는 framework StateData가 아니며 상태가 없다고 필수 검사를 조용히 건너뛰면 안 됩니다.

예제에서는 선택한 네임스페이스에 적합한 `app=cache` Pod가 있어야 합니다. preferred anti-affinity는 분리를 보장하지 않습니다. `hardPodAffinityWeight`는 점수에 영향을 주며 required 조건을 완화하지 않습니다. 실제 워크로드로 규모·배치의 균형을 검증하세요. 같은 위치에 둔다고 최소 지연 시간을 입증하지는 않습니다.

**파드 어피니티 및 안티-어피니티 사용 사례:**
1. **고가용성**: 같은 애플리케이션의 인스턴스를 다른 노드, 영역, 리전에 분산
2. **성능 최적화**: 실측 경합·지연 시간의 균형을 고려하여 통신하는 Pod의 같은 위치 배치
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
<summary>정답 보기</summary>

**정답: A. 파드의 spec.nodeName 필드가 노드 이름과 일치하는지 확인**

**설명:**
Kubernetes 스케줄러의 "NodeName" 플러그인의 주요 목적은 파드의 `spec.nodeName` 필드가 노드 이름과 일치하는지 확인하는 것입니다. nodeName이 있는 Pod로 호출하면 그 이름만 허용합니다. 일반 동작에서는 미리 할당된 Pod가 unscheduled 큐에서 이미 제외되므로 플러그인 자체가 우회의 원인은 아닙니다.

**NodeName 플러그인의 주요 기능:**
1. **노드 이름 확인**: 파드의 `spec.nodeName` 필드가 설정된 경우, 해당 이름과 일치하는 노드만 선택합니다.
2. **필드 의미**: spec.nodeName은 노드를 직접 지정하며 스케줄러 선택 필드가 아닙니다.
3. **스케줄러 우회**: `spec.nodeName`이 설정된 파드는 일반적인 스케줄링 로직을 우회하고 지정된 노드에 직접 할당됩니다.

**이름 검사와 동등한 predicate:**
기본 검사를 설명하는 함수입니다. `NodeName`이라는 대체 플러그인으로 등록하지 마세요.

```go
package quizplugins

import v1 "k8s.io/api/core/v1"

// Equivalent name predicate for explanation; not a replacement scheduler.
func NodeNameMatches(pod *v1.Pod, node *v1.Node) bool {
	if pod == nil || node == nil {
		return false
	}
	return pod.Spec.NodeName == "" || pod.Spec.NodeName == node.Name
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
    image: nginx:1.30.4
```

**nodeName 사용 시 고려 사항:**
1. **스케줄러 우회**: `nodeName`을 사용하면 스케줄러의 필터링, 스코어링 등의 로직을 우회합니다.
2. **노드 존재**: 이름이 잘못되거나 노드가 없어도 다른 노드를 자동 선택하지 않습니다.
3. **어드미션 유지**: 스케줄러 fit 검사는 우회하지만 kubelet 어드미션은 리소스 부족으로 Pod를 거부할 수 있습니다.
4. **남는 제약**: NoSchedule·affinity 스케줄링 검사는 우회하지만 NoExecute·노드 어드미션은 적용됩니다. WaitForFirstConsumer PVC는 스케줄러 볼륨 조정이 생략되어 Pending일 수 있습니다.

`kubernetes.io/hostname` 레이블은 Node 객체 이름과 같다고 보장되지 않습니다. 아래 레이블 예제에는 실제 값을 확인해 사용하세요.

**nodeName vs nodeSelector vs nodeAffinity:**
1. **nodeName**: 특정 노드에 직접 할당합니다. 가장 제한적이고 유연성이 낮습니다.
2. **nodeSelector**: 레이블을 기반으로 노드를 선택합니다. 간단하지만 표현력이 제한적입니다.
3. **nodeAffinity**: 복잡한 노드 선택 규칙을 지원합니다. 가장 유연하고 표현력이 높습니다.

**nodeName 사용 사례:**
1. **디버깅**: 특정 노드에서 파드를 실행하여 문제를 디버깅합니다.
2. **테스트**: 특정 노드에서 테스트를 실행합니다.
3. **특수 하드웨어**: 특정 하드웨어가 있는 노드에 파드를 할당합니다.
4. **정적 Pod 구분**: nodeName을 가진 API 생성 Pod가 정적 Pod가 되는 것은 아닙니다. 정적 Pod는 kubelet 로컬 설정에서 생성됩니다.

**nodeName 사용 시 주의 사항:**
1. **교체 동작**: Pod는 이동하지 않습니다. 컨트롤러가 교체 Pod를 만들어도 템플릿이 실패한 같은 이름에 고정되어 있으면 계속 제약됩니다.
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
       image: nginx:1.30.4
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
       image: nginx:1.30.4
   ```

**다른 옵션들의 문제점:**
- B. 노드에 이름 할당: 노드 이름은 노드 생성 시 할당되며, 스케줄러 플러그인의 역할이 아닙니다.
- C. 파드에 노드 이름 할당: 이는 스케줄러의 바인딩 단계에서 수행되며, NodeName 플러그인의 역할이 아닙니다.
- D. 노드 이름 형식 검증: 이는 API 서버의 검증 로직에 의해 수행되며, 스케줄러 플러그인의 역할이 아닙니다.
</details>

### 11. 어떤 컨트롤러가 축소 시 Pod Deletion Cost를 선호도로 사용하나요?

A. StatefulSet ordinal 삭제
B. Deployment가 소유한 것을 포함한 ReplicaSet
C. 모든 독립 Pod의 삭제
D. Deployment 전체의 Pod를 정렬하는 전역 스케줄러

<details>
<summary>정답 보기</summary>

**정답: B. Deployment가 소유한 것을 포함한 ReplicaSet**

같은 ReplicaSet 내부에서 best effort로 비교합니다. 없으면0이며 음수를 포함한 signed int32 값이 유효합니다. 할당·phase·준비 상태가 우선할 수 있으므로 높은 비용의 unready Pod가 낮은 비용의 ready Pod보다 먼저 삭제될 수 있습니다. 1.21 alpha,1.22부터 beta·기본 활성화입니다.
</details>

### 12. 본문의 삭제 비용 갱신 방식과 일치하는 것은 무엇인가요?

A. 높은 비용과 PDB가 일반 축소에서 복제본 생존을 보장한다
B. 요청마다 전체 Pod를 교체한다
C. 큰 상태 전환에 비용만 패치하고 UID를 검사하며 오래된 메트릭은 거부한다
D. 메트릭이 없으면 활동0으로 보고 즉시 비용을 낮춘다

<details>
<summary>정답 보기</summary>

**정답: C. 큰 상태 전환에 비용만 패치하고 UID를 검사하며 오래된 메트릭은 거부한다**

권한이 있는 단일 작성자·제한된 요청 시간·최소 어노테이션 패치를 사용합니다. UID 검사는 같은 이름의 새 Pod를 잘못 갱신하지 않게 합니다. scale의 서버 dry run은 삭제될 Pod를 예측하지 않습니다. 일반 ReplicaSet 축소는 Pod를 직접 삭제하고 PDB가 차단하지 않으므로 앱 드레이닝·준비 상태·복구가 여전히 필요합니다.
</details>

## 참고 자료

[Part1 모듈](../../scheduling/01-custom-scheduler-part1.md)을 사용합니다. 로컬 코드·설정 테스트는 배포된 승인 시스템·gang 워크로드·GPU 실행·운영 적합성을 검증하지 않습니다.

* [Scheduling framework](https://kubernetes.io/docs/concepts/scheduling-eviction/scheduling-framework/)
* [Pinned framework interfaces](https://github.com/kubernetes/kubernetes/blob/v1.35.8/staging/src/k8s.io/kube-scheduler/framework/interface.go)
* [Scheduler configuration](https://kubernetes.io/docs/reference/scheduling/config/)
* [Native PodGroup scheduling](https://kubernetes.io/docs/concepts/scheduling-eviction/podgroup-scheduling/)
* [PodGroup policies](https://kubernetes.io/docs/concepts/workloads/workload-api/policies/)
* [Volcano Job](https://volcano.sh/en/docs/vcjob/)
* [Volcano 1.15.2 Job CRD](https://github.com/volcano-sh/volcano/blob/v1.15.2/config/crd/volcano/bases/batch.volcano.sh_jobs.yaml)
* [BalancedAllocation scorer](https://github.com/kubernetes/kubernetes/blob/v1.35.8/pkg/scheduler/framework/plugins/noderesources/balanced_allocation.go)
* [Node assignment](https://kubernetes.io/docs/concepts/scheduling-eviction/assign-pod-node/)
* [ReplicaSet deletion cost](https://kubernetes.io/docs/concepts/workloads/controllers/replicaset/#pod-deletion-cost)
