# 스케줄링, 선점 및 축출 퀴즈

이 퀴즈는 Kubernetes의 스케줄링, 선점 및 축출 관련 개념에 대한 이해도를 테스트합니다. 포드 스케줄링 알고리즘, 노드 선택, 어피니티, 테인트, 톨러레이션, 선점, 축출 등의 주제를 다룹니다.

## 객관식 문제

1. Kubernetes 스케줄러가 포드를 노드에 할당하는 과정에서 첫 번째 단계는 무엇인가요?
   - A) 노드에 점수 매기기
   - B) 노드 필터링
   - C) 포드 우선순위 결정
   - D) 바인딩 작업 수행
   
<details>
<summary>정답 보기</summary>

**정답: B) 노드 필터링**

**설명:**
Kubernetes 스케줄러는 포드를 노드에 할당할 때 다음과 같은 단계를 거칩니다:
1. 노드 필터링: 포드를 실행할 수 있는 노드를 식별합니다. 이 단계에서는 리소스 요구 사항, 노드 선택기, 어피니티, 테인트 및 톨러레이션 등을 고려합니다.
2. 노드 점수 매기기: 필터링된 노드에 점수를 할당합니다.
3. 최적의 노드 선택: 가장 높은 점수를 받은 노드를 선택합니다.
4. 바인딩: 선택된 노드에 포드를 할당합니다.

따라서 첫 번째 단계는 노드 필터링입니다.
</details>

2. 노드 어피니티(Node Affinity)와 포드 어피니티(Pod Affinity)의 주요 차이점은 무엇인가요?
   - A) 노드 어피니티는 하드 제약 조건만 지원하고, 포드 어피니티는 소프트 제약 조건만 지원한다
   - B) 노드 어피니티는 노드 레이블을 기반으로 하고, 포드 어피니티는 포드 레이블을 기반으로 한다
   - C) 노드 어피니티는 클러스터 수준에서 적용되고, 포드 어피니티는 네임스페이스 수준에서 적용된다
   - D) 노드 어피니티는 스케줄링 시에만 적용되고, 포드 어피니티는 런타임에도 적용된다
   
<details>
<summary>정답 보기</summary>

**정답: B) 노드 어피니티는 노드 레이블을 기반으로 하고, 포드 어피니티는 포드 레이블을 기반으로 한다**

**설명:**
노드 어피니티(Node Affinity)는 노드의 레이블을 기반으로 포드가 특정 노드에 스케줄링되도록 제약 조건을 설정합니다. 예를 들어, GPU가 있는 노드나 특정 가용 영역의 노드에 포드를 배치할 수 있습니다.

포드 어피니티(Pod Affinity)는 이미 실행 중인 다른 포드의 레이블을 기반으로 포드가 스케줄링되도록 제약 조건을 설정합니다. 예를 들어, 프론트엔드 포드를 백엔드 포드와 같은 노드나 같은 가용 영역에 배치할 수 있습니다.

두 가지 모두 requiredDuringSchedulingIgnoredDuringExecution(하드 제약 조건)과 preferredDuringSchedulingIgnoredDuringExecution(소프트 제약 조건)을 지원합니다.
</details>

3. 테인트(Taint)와 톨러레이션(Toleration)의 주요 목적은 무엇인가요?
   - A) 특정 포드가 특정 노드에만 스케줄링되도록 보장
   - B) 노드가 특정 포드를 거부하도록 하고, 포드가 이를 허용할 수 있게 함
   - C) 포드 간의 어피니티 규칙 설정
   - D) 클러스터의 리소스 사용량 최적화
   
<details>
<summary>정답 보기</summary>

**정답: B) 노드가 특정 포드를 거부하도록 하고, 포드가 이를 허용할 수 있게 함**

**설명:**
테인트(Taint)는 노드에 적용되어 특정 포드가 해당 노드에 스케줄링되지 않도록 합니다. 톨러레이션(Toleration)은 포드에 적용되어 특정 테인트가 있는 노드에도 스케줄링될 수 있도록 합니다.

이 메커니즘은 특정 노드를 특정 워크로드 전용으로 예약하거나, 특정 하드웨어를 필요로 하는 워크로드를 적절한 노드에 배치하는 데 유용합니다. 예를 들어, GPU 노드에 테인트를 적용하고 GPU를 필요로 하는 포드에만 해당 톨러레이션을 부여할 수 있습니다.

테인트와 톨러레이션은 노드 어피니티와 반대 방향으로 작동합니다. 노드 어피니티는 포드가 특정 노드에 끌리도록 하는 반면, 테인트와 톨러레이션은 포드가 특정 노드를 피하도록 합니다(톨러레이션이 없는 경우).
</details>

4. 포드 우선순위(Pod Priority)와 선점(Preemption)의 관계는 무엇인가요?
   - A) 우선순위가 높은 포드는 스케줄링 시 우선순위가 낮은 포드를 선점할 수 있다
   - B) 우선순위는 포드의 CPU 및 메모리 할당량을 결정한다
   - C) 선점은 노드 유지 보수 중에만 발생한다
   - D) 우선순위와 선점은 서로 관련이 없다
   
<details>
<summary>정답 보기</summary>

**정답: A) 우선순위가 높은 포드는 스케줄링 시 우선순위가 낮은 포드를 선점할 수 있다**

**설명:**
포드 우선순위(Pod Priority)는 포드의 중요도를 나타내는 값입니다. PriorityClass 리소스를 통해 정의되며, 포드 스펙에서 참조됩니다.

선점(Preemption)은 우선순위가 높은 포드가 스케줄링될 때 리소스가 부족한 경우, 스케줄러가 우선순위가 낮은 포드를 종료하여 리소스를 확보하는 프로세스입니다.

이 메커니즘을 통해 중요한 워크로드가 클러스터 리소스 부족 상황에서도 스케줄링될 수 있도록 보장할 수 있습니다. 예를 들어, 프로덕션 워크로드에 높은 우선순위를 부여하고 개발/테스트 워크로드에 낮은 우선순위를 부여하면, 리소스 경합 시 프로덕션 워크로드가 우선적으로 실행됩니다.
</details>

5. 노드 셀렉터(Node Selector)와 노드 어피니티(Node Affinity)의 주요 차이점은 무엇인가요?
   - A) 노드 셀렉터는 하드 제약 조건만 지원하고, 노드 어피니티는 하드 및 소프트 제약 조건을 모두 지원한다
   - B) 노드 셀렉터는 여러 레이블을 지원하지 않지만, 노드 어피니티는 지원한다
   - C) 노드 셀렉터는 클러스터 수준에서 적용되고, 노드 어피니티는 네임스페이스 수준에서 적용된다
   - D) 노드 셀렉터는 레이블 키만 지정할 수 있고, 노드 어피니티는 키와 값을 모두 지정할 수 있다
   
<details>
<summary>정답 보기</summary>

**정답: A) 노드 셀렉터는 하드 제약 조건만 지원하고, 노드 어피니티는 하드 및 소프트 제약 조건을 모두 지원한다**

**설명:**
노드 셀렉터(Node Selector)는 포드 스펙에서 `nodeSelector` 필드를 사용하여 특정 레이블이 있는 노드에만 포드를 스케줄링하는 간단한 방법입니다. 이는 항상 하드 제약 조건으로 작동합니다. 즉, 조건을 만족하는 노드가 없으면 포드는 스케줄링되지 않습니다.

노드 어피니티(Node Affinity)는 더 표현력이 풍부한 언어를 제공하며, 두 가지 유형의 제약 조건을 지원합니다:
- `requiredDuringSchedulingIgnoredDuringExecution`: 하드 제약 조건으로, 조건을 만족하는 노드가 없으면 포드는 스케줄링되지 않습니다.
- `preferredDuringSchedulingIgnoredDuringExecution`: 소프트 제약 조건으로, 조건을 만족하는 노드가 선호되지만, 없는 경우에도 다른 노드에 스케줄링될 수 있습니다.

또한 노드 어피니티는 `In`, `NotIn`, `Exists`, `DoesNotExist`, `Gt`, `Lt` 등의 연산자를 사용하여 더 복잡한 조건을 표현할 수 있습니다.
</details>

6. Kubernetes에서 포드 축출(Pod Eviction)이 발생하는 주요 원인은 무엇인가요?
   - A) 포드의 우선순위가 낮을 때
   - B) 노드의 리소스(메모리, 디스크 등)가 부족할 때
   - C) 포드가 너무 오래 실행되었을 때
   - D) 포드의 레플리카 수가 너무 많을 때
   
<details>
<summary>정답 보기</summary>

**정답: B) 노드의 리소스(메모리, 디스크 등)가 부족할 때**

**설명:**
Kubernetes에서 포드 축출(Pod Eviction)은 주로 노드의 리소스가 부족할 때 발생합니다. kubelet은 노드의 메모리, 디스크 공간, PID 등의 리소스 사용량을 모니터링하고, 특정 임계값을 초과하면 포드 축출을 시작합니다.

축출 프로세스는 다음과 같은 순서로 진행됩니다:
1. BestEffort QoS 클래스의 포드(리소스 요청 및 제한이 없는 포드)
2. Burstable QoS 클래스의 포드(리소스 요청은 있지만 제한이 없거나 요청보다 높은 포드)
3. Guaranteed QoS 클래스의 포드(리소스 요청과 제한이 동일한 포드)

또한 각 QoS 클래스 내에서는 포드의 우선순위와 리소스 사용량을 고려하여 축출할 포드를 선택합니다.

노드 유지 보수, 노드 풀 크기 조정, 노드 장애 등의 이유로도 포드 축출이 발생할 수 있습니다.
</details>

7. Kubernetes에서 DaemonSet 포드의 스케줄링 특성은 무엇인가요?
   - A) 모든 노드에 하나씩 스케줄링된다
   - B) 특정 레이블이 있는 노드에만 스케줄링된다
   - C) 기본 스케줄러를 사용하지 않고 직접 노드에 배치된다
   - D) 항상 마스터 노드에 스케줄링된다
   
<details>
<summary>정답 보기</summary>

**정답: A) 모든 노드에 하나씩 스케줄링된다**

**설명:**
DaemonSet은 클러스터의 모든 노드(또는 노드 셀렉터를 사용하는 경우 선택된 노드)에 포드의 복사본을 하나씩 실행하도록 설계된 워크로드 리소스입니다. 새 노드가 클러스터에 추가되면 DaemonSet 컨트롤러는 자동으로 해당 노드에 포드를 배치합니다.

DaemonSet은 일반적으로 로깅 에이전트, 모니터링 에이전트, 네트워크 플러그인 등 모든 노드에서 실행해야 하는 백그라운드 서비스에 사용됩니다.

Kubernetes 1.12 이전에는 DaemonSet 컨트롤러가 기본 스케줄러를 우회하고 직접 노드에 포드를 배치했습니다(옵션 C). 그러나 1.12 이후에는 기본 스케줄러를 사용하여 DaemonSet 포드를 스케줄링합니다.
</details>

8. Kubernetes에서 QoS(Quality of Service) 클래스 중 가장 높은 우선순위를 가지는 것은 무엇인가요?
   - A) BestEffort
   - B) Burstable
   - C) Guaranteed
   - D) Critical
   
<details>
<summary>정답 보기</summary>

**정답: C) Guaranteed**

**설명:**
Kubernetes에서는 포드의 리소스 요청(requests)과 제한(limits) 설정에 따라 세 가지 QoS(Quality of Service) 클래스를 정의합니다:

1. **Guaranteed**: 모든 컨테이너가 CPU와 메모리에 대한 요청과 제한을 명시적으로 설정하고, 요청과 제한이 동일한 경우입니다. 이 클래스는 가장 높은 우선순위를 가지며, 리소스 부족 시 마지막으로 축출됩니다.

2. **Burstable**: 적어도 하나의 컨테이너가 CPU나 메모리에 대한 요청을 설정했지만, 모든 컨테이너의 요청과 제한이 동일하지 않은 경우입니다. 이 클래스는 중간 우선순위를 가집니다.

3. **BestEffort**: 어떤 컨테이너도 CPU나 메모리에 대한 요청이나 제한을 설정하지 않은 경우입니다. 이 클래스는 가장 낮은 우선순위를 가지며, 리소스 부족 시 가장 먼저 축출됩니다.

리소스 부족 상황에서 kubelet은 BestEffort 포드를 먼저 축출하고, 그 다음으로 Burstable 포드를, 마지막으로 Guaranteed 포드를 축출합니다.
</details>

9. 노드에 `node-role.kubernetes.io/master:NoSchedule` 테인트가 적용되어 있을 때, 이 노드에 포드를 스케줄링하기 위해 필요한 것은 무엇인가요?
   - A) 노드 어피니티 규칙
   - B) 포드 어피니티 규칙
   - C) 해당 테인트에 대한 톨러레이션
   - D) 높은 우선순위 클래스
   
<details>
<summary>정답 보기</summary>

**정답: C) 해당 테인트에 대한 톨러레이션**

**설명:**
노드에 `node-role.kubernetes.io/master:NoSchedule` 테인트가 적용되어 있으면, 기본적으로 포드는 해당 노드에 스케줄링되지 않습니다. 이 노드에 포드를 스케줄링하려면, 포드에 해당 테인트에 대한 톨러레이션을 추가해야 합니다.

예를 들어, 다음과 같은 톨러레이션을 포드 스펙에 추가할 수 있습니다:

```yaml
tolerations:
- key: "node-role.kubernetes.io/master"
  operator: "Exists"
  effect: "NoSchedule"
```

이 톨러레이션은 포드가 마스터 노드의 테인트를 허용하도록 하여, 마스터 노드에도 스케줄링될 수 있게 합니다. 이는 클러스터 관리 도구나 모니터링 도구와 같이 마스터 노드에서 실행해야 하는 특정 워크로드에 유용합니다.
</details>

10. Kubernetes에서 포드 중단 예산(PodDisruptionBudget)의 주요 목적은 무엇인가요?
    - A) 포드의 리소스 사용량 제한
    - B) 자발적 중단 중에도 애플리케이션 가용성 보장
    - C) 포드 스케줄링 우선순위 설정
    - D) 포드 재시작 정책 정의
    
<details>
<summary>정답 보기</summary>

## 주관식 문제

1. Kubernetes 스케줄러의 필터링 단계에서 사용되는 주요 필터(predicates)를 세 가지 이상 설명하세요.

<details>
<summary>정답 보기</summary>

**정답:**
Kubernetes 스케줄러의 필터링 단계에서 사용되는 주요 필터(predicates)는 다음과 같습니다:

1. **NodeResourcesFit**: 포드의 리소스 요청(CPU, 메모리 등)을 충족할 수 있는 노드를 필터링합니다. 노드의 할당 가능한 리소스가 포드의 요청보다 적으면 해당 노드는 필터링됩니다.

2. **NodeName**: 포드 스펙에 `nodeName` 필드가 지정된 경우, 해당 이름의 노드만 선택합니다. 이는 가장 높은 우선순위를 가진 필터입니다.

3. **NodeUnschedulable**: `Unschedulable` 플래그가 설정된 노드(예: 유지 보수 모드의 노드)를 필터링합니다.

4. **NodeAffinity**: 포드의 노드 어피니티 규칙을 충족하는 노드만 선택합니다.

5. **PodAffinity**: 포드의 포드 어피니티 규칙을 충족하는 노드만 선택합니다.

6. **PodAntiAffinity**: 포드의 포드 안티-어피니티 규칙을 충족하는 노드만 선택합니다.

7. **TaintToleration**: 포드가 톨러레이션하지 않는 테인트가 있는 노드를 필터링합니다.

8. **NodePorts**: 포드가 요청하는 포트가 이미 노드에서 사용 중인 경우 해당 노드를 필터링합니다.

9. **VolumeRestrictions**: 포드가 요청하는 볼륨 유형을 노드가 지원하는지 확인합니다.

10. **EBSLimits**, **GCEPDLimits**, **AzureDiskLimits**: 클라우드 제공자별 볼륨 제한을 확인합니다.

(위 중 세 가지 이상만 설명하면 됩니다)
</details>

2. Kubernetes에서 노드 어피니티(Node Affinity)와 테인트/톨러레이션(Taints/Tolerations)을 함께 사용하는 방법과 그 이점을 설명하세요.

<details>
<summary>정답 보기</summary>

**정답:**
노드 어피니티와 테인트/톨러레이션은 서로 보완적인 기능으로, 함께 사용하면 포드 배치에 대한 더 세밀한 제어가 가능합니다.

**함께 사용하는 방법:**

1. **노드 어피니티로 후보 노드 선택**:
   노드 어피니티를 사용하여 포드가 스케줄링될 수 있는 노드 집합을 정의합니다.
   ```yaml
   affinity:
     nodeAffinity:
       requiredDuringSchedulingIgnoredDuringExecution:
         nodeSelectorTerms:
         - matchExpressions:
           - key: gpu-type
             operator: In
             values: ["nvidia-tesla-v100"]
   ```

2. **테인트로 다른 포드 제외**:
   특수 하드웨어가 있는 노드에 테인트를 적용하여 일반 포드가 해당 노드에 스케줄링되지 않도록 합니다.
   ```bash
   kubectl taint nodes node1 gpu=true:NoSchedule
   ```

3. **톨러레이션으로 선택된 포드만 허용**:
   특정 워크로드에만 톨러레이션을 추가하여 테인트가 있는 노드에 스케줄링될 수 있도록 합니다.
   ```yaml
   tolerations:
   - key: "gpu"
     operator: "Equal"
     value: "true"
     effect: "NoSchedule"
   ```

**이점:**

1. **양방향 제어**: 
   - 노드 어피니티는 "포드가 특정 노드에 끌리도록" 하는 반면(포드 → 노드)
   - 테인트/톨러레이션은 "노드가 특정 포드를 거부하도록" 합니다(노드 → 포드)
   - 이 두 가지를 함께 사용하면 양방향에서 포드 배치를 제어할 수 있습니다.

2. **리소스 격리 강화**:
   - 특수 하드웨어(GPU, FPGA 등)가 있는 노드를 해당 하드웨어를 필요로 하는 워크로드 전용으로 예약할 수 있습니다.
   - 테인트로 일반 워크로드를 제외하고, 노드 어피니티로 특정 워크로드를 해당 노드로 유도합니다.

3. **복잡한 배치 시나리오 지원**:
   - 예: "고성능 GPU가 있는 노드 중에서도 특정 가용 영역에 있는 노드에만 배치"와 같은 복잡한 요구 사항을 구현할 수 있습니다.

4. **리소스 낭비 방지**:
   - 비싼 리소스(예: GPU)가 있는 노드에 일반 워크로드가 스케줄링되는 것을 방지하여 리소스 낭비를 줄일 수 있습니다.

5. **보안 및 격리**:
   - 특정 보안 요구 사항이 있는 워크로드를 격리된 노드에 배치할 수 있습니다.

**예시 시나리오:**
GPU 워크로드를 위한 전용 노드 풀을 구성하는 경우:
1. GPU 노드에 `dedicated=gpu:NoSchedule` 테인트 적용
2. GPU 워크로드에 해당 테인트에 대한 톨러레이션 추가
3. GPU 워크로드에 `gpu-type=nvidia` 노드 어피니티 추가

이렇게 하면 GPU 워크로드는 GPU가 있는 노드에만 스케줄링되고, 다른 워크로드는 GPU 노드에 스케줄링되지 않습니다.
</details>

3. Kubernetes에서 포드 우선순위(Pod Priority)와 선점(Preemption) 메커니즘이 작동하는 방식을 설명하세요.

<details>
<summary>정답 보기</summary>

**정답:**
Kubernetes에서 포드 우선순위와 선점 메커니즘은 다음과 같이 작동합니다:

**1. 우선순위 클래스 정의:**
먼저 PriorityClass 리소스를 생성하여 다양한 우선순위 레벨을 정의합니다.
```yaml
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: high-priority
value: 1000000
globalDefault: false
description: "This priority class should be used for critical production workloads."
```

**2. 포드에 우선순위 할당:**
포드 스펙에서 priorityClassName 필드를 사용하여 우선순위 클래스를 참조합니다.
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: critical-pod
spec:
  priorityClassName: high-priority
  containers:
  - name: web-server
    image: nginx
```

**3. 스케줄링 큐 정렬:**
포드가 생성되면 스케줄러의 큐에 추가되며, 큐는 우선순위에 따라 정렬됩니다. 우선순위가 높은 포드가 먼저 스케줄링됩니다.

**4. 선점 프로세스:**
우선순위가 높은 포드가 스케줄링될 때 적합한 노드가 없으면 선점 프로세스가 시작됩니다:

   a. 스케줄러는 각 노드를 평가하여 우선순위가 낮은 포드를 선점(제거)했을 때 새 포드를 스케줄링할 수 있는지 확인합니다.
   
   b. 가장 적합한 노드를 선택합니다(선점으로 인한 영향이 최소화되는 노드).
   
   c. 선택된 노드에서 우선순위가 낮은 포드에 종료 신호를 보냅니다. 이때 여러 포드를 선점해야 할 수도 있습니다.
   
   d. 선점된 포드가 정상적으로 종료되고 리소스가 확보되면, 우선순위가 높은 포드가 해당 노드에 스케줄링됩니다.

**5. 종료 유예 기간:**
선점된 포드는 즉시 강제 종료되지 않고, 포드의 terminationGracePeriodSeconds 설정(기본값: 30초)에 따라 정상적으로 종료됩니다. 이 기간 동안 포드는 정리 작업을 수행할 수 있습니다.

**6. 선점 제한 사항:**
- 우선순위가 같거나 높은 포드는 선점되지 않습니다.
- 시스템 크리티컬 포드(예: kube-system 네임스페이스의 핵심 구성 요소)는 특별히 보호됩니다.
- PodDisruptionBudget은 선점 중에도 고려됩니다.

**7. 이벤트 기록:**
선점이 발생하면 이벤트가 기록되어 어떤 포드가 왜 선점되었는지 추적할 수 있습니다.

**주요 사용 사례:**
- 중요한 프로덕션 워크로드에 높은 우선순위 부여
- 클러스터 자동 확장 전에 덜 중요한 워크로드 선점
- 리소스 경합 시 중요한 서비스의 가용성 보장
- 배치 작업과 서비스 워크로드 간의 리소스 균형 조정

**모범 사례:**
- 우선순위 클래스를 너무 많이 만들지 않기
- 시스템 우선순위 클래스(system-cluster-critical, system-node-critical)보다 낮은 값 사용
- 우선순위와 QoS 클래스를 함께 고려하여 리소스 관리 전략 수립
</details>

4. Kubernetes에서 포드 축출(Pod Eviction)의 종류와 각각의 발생 조건을 설명하세요.

<details>
<summary>정답 보기</summary>

**정답:**
Kubernetes에서 포드 축출(Pod Eviction)은 크게 두 가지 유형으로 나눌 수 있습니다: 노드 수준 축출과 API 서버 수준 축출입니다.

**1. 노드 수준 축출 (Node-level Eviction)**

kubelet에 의해 관리되며, 노드의 리소스 부족 상황에 대응하기 위해 발생합니다.

**발생 조건:**
- **메모리 부족**: 노드의 사용 가능한 메모리가 임계값 아래로 떨어질 때
  - `memory.available < 100Mi` (기본값)
- **디스크 공간 부족**: 노드의 디스크 공간이 임계값 아래로 떨어질 때
  - `nodefs.available < 10%` (기본값)
  - `nodefs.inodesFree < 5%` (기본값)
  - `imagefs.available < 15%` (기본값)
- **PID 부족**: 사용 가능한 프로세스 ID가 임계값 아래로 떨어질 때
  - `pid.available < 10%` (기본값)

**심각도 수준:**
- **소프트 축출(Soft Eviction)**: 유예 기간이 있으며, 임계값을 초과한 후 일정 시간(기본값: 5분) 동안 지속되면 축출이 시작됩니다.
  - 예: `eviction-soft-grace-period.memory.available=1m30s`
- **하드 축출(Hard Eviction)**: 즉시 축출이 시작됩니다.
  - 예: `eviction-hard=memory.available<100Mi`

**축출 순서:**
1. BestEffort QoS 클래스의 포드(리소스 요청 및 제한이 없는 포드)
2. Burstable QoS 클래스의 포드(리소스 요청은 있지만 제한이 없거나 요청보다 높은 포드)
3. Guaranteed QoS 클래스의 포드(리소스 요청과 제한이 동일한 포드)

각 QoS 클래스 내에서는 포드의 우선순위와 리소스 사용량을 고려하여 축출할 포드를 선택합니다.

**2. API 서버 수준 축출 (API Server-level Eviction)**

클러스터 관리자나 자동화 도구에 의해 의도적으로 발생하는 축출입니다.

**발생 조건:**
- **노드 드레이닝(Node Draining)**: 노드 유지 보수, 업그레이드, 삭제 등을 위해 노드의 모든 포드를 축출
  - `kubectl drain <node-name>`
- **테인트 기반 축출**: 노드에 `NoExecute` 효과가 있는 테인트를 추가하고, 해당 테인트를 톨러레이션하지 않는 포드 축출
- **API 직접 호출**: 포드 삭제 API를 직접 호출하여 포드 축출

**제약 조건:**
- **PodDisruptionBudget(PDB)**: 자발적 중단 중에도 애플리케이션의 가용성을 보장하기 위한 제약 조건
  - `minAvailable`: 중단 중에도 항상 사용 가능해야 하는 최소 포드 수 또는 비율
  - `maxUnavailable`: 중단 중에 사용할 수 없게 될 수 있는 최대 포드 수 또는 비율
- PDB는 API 서버 수준 축출에만 적용되며, 노드 수준 축출에는 적용되지 않습니다.

**3. 기타 축출 시나리오**

- **노드 자동 확장 축소**: 클러스터 자동 확장기가 노드를 제거할 때 포드 축출
- **선점(Preemption)**: 우선순위가 높은 포드를 위해 우선순위가 낮은 포드 축출
- **노드 장애**: 노드가 실패하면 컨트롤 플레인이 해당 노드의 포드를 축출로 표시

**축출 영향 최소화 전략:**
- 적절한 QoS 클래스 설정(중요한 워크로드에 Guaranteed QoS 사용)
- PodDisruptionBudget 구성
- 적절한 리소스 요청 및 제한 설정
- 다중 가용 영역에 워크로드 분산
- 노드 리소스 모니터링 및 경고 설정
</details>

5. Kubernetes에서 DaemonSet의 스케줄링 동작과 일반 포드의 스케줄링 동작의 차이점을 설명하세요.

<details>
<summary>정답 보기</summary>

**정답:**
## 실습 문제

1. 다음 요구 사항에 맞는 노드 어피니티(Node Affinity) 설정을 포함한 포드 매니페스트를 작성하세요:
   - 포드 이름: web-server
   - 이미지: nginx:latest
   - 가용 영역(zone)이 "us-east-1a" 또는 "us-east-1b"인 노드에만 스케줄링
   - 인스턴스 타입(instance-type)이 "m5.large"인 노드 선호

<details>
<summary>정답 보기</summary>

**정답:**

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: web-server
spec:
  containers:
  - name: nginx
    image: nginx:latest
  affinity:
    nodeAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
        nodeSelectorTerms:
        - matchExpressions:
          - key: topology.kubernetes.io/zone
            operator: In
            values:
            - us-east-1a
            - us-east-1b
      preferredDuringSchedulingIgnoredDuringExecution:
      - weight: 1
        preference:
          matchExpressions:
          - key: node.kubernetes.io/instance-type
            operator: In
            values:
            - m5.large
```

이 포드 매니페스트는 다음과 같은 노드 어피니티 규칙을 설정합니다:
- `requiredDuringSchedulingIgnoredDuringExecution`: 포드는 반드시 "us-east-1a" 또는 "us-east-1b" 가용 영역에 있는 노드에만 스케줄링됩니다. 이 조건을 만족하는 노드가 없으면 포드는 스케줄링되지 않습니다.
- `preferredDuringSchedulingIgnoredDuringExecution`: 가능하다면 "m5.large" 인스턴스 타입의 노드에 스케줄링됩니다. 이러한 노드가 없어도 포드는 다른 적합한 노드에 스케줄링될 수 있습니다.

`topology.kubernetes.io/zone`과 `node.kubernetes.io/instance-type`은 Kubernetes에서 자동으로 설정되는 표준 노드 레이블입니다.
</details>

2. 다음 요구 사항에 맞는 테인트(Taint)와 톨러레이션(Toleration) 설정을 작성하세요:
   - 노드 이름: worker-1
   - 테인트: dedicated=database:NoSchedule
   - 데이터베이스 포드(이름: postgres-db, 이미지: postgres:13)에 적절한 톨러레이션 추가

<details>
<summary>정답 보기</summary>

**정답:**

노드에 테인트 적용:
```bash
kubectl taint nodes worker-1 dedicated=database:NoSchedule
```

데이터베이스 포드 매니페스트:
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: postgres-db
spec:
  containers:
  - name: postgres
    image: postgres:13
    env:
    - name: POSTGRES_PASSWORD
      value: "password"  # 실제 환경에서는 Secret을 사용해야 합니다
  tolerations:
  - key: "dedicated"
    operator: "Equal"
    value: "database"
    effect: "NoSchedule"
```

이 설정은 다음과 같이 작동합니다:
- `worker-1` 노드에 `dedicated=database:NoSchedule` 테인트를 적용하여, 이 테인트를 톨러레이션하지 않는 포드는 이 노드에 스케줄링되지 않습니다.
- `postgres-db` 포드에는 이 테인트에 대한 톨러레이션을 추가하여, 이 노드에 스케줄링될 수 있도록 합니다.

톨러레이션의 각 필드 의미:
- `key`: 테인트의 키와 일치해야 합니다 ("dedicated").
- `operator`: "Equal"은 값이 정확히 일치해야 함을 의미합니다. "Exists"를 사용하면 값을 지정하지 않아도 됩니다.
- `value`: 테인트의 값과 일치해야 합니다 ("database").
- `effect`: 테인트의 효과와 일치해야 합니다 ("NoSchedule").
</details>

3. 다음 요구 사항에 맞는 포드 어피니티(Pod Affinity) 및 안티-어피니티(Anti-Affinity) 설정을 포함한 디플로이먼트 매니페스트를 작성하세요:
   - 디플로이먼트 이름: web-frontend
   - 이미지: nginx:latest
   - 레플리카: 3
   - app=cache 레이블이 있는 포드와 같은 노드에 배치(어피니티)
   - 같은 디플로이먼트의 다른 포드와는 다른 노드에 배치(안티-어피니티)

<details>
<summary>정답 보기</summary>

**정답:**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-frontend
spec:
  replicas: 3
  selector:
    matchLabels:
      app: web-frontend
  template:
    metadata:
      labels:
        app: web-frontend
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
            topologyKey: "kubernetes.io/hostname"
        podAntiAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
          - labelSelector:
              matchExpressions:
              - key: app
                operator: In
                values:
                - web-frontend
            topologyKey: "kubernetes.io/hostname"
      containers:
      - name: nginx
        image: nginx:latest
```

이 디플로이먼트 매니페스트는 다음과 같은 어피니티 규칙을 설정합니다:

1. **포드 어피니티(Pod Affinity)**:
   - `app=cache` 레이블이 있는 포드와 같은 노드에 배치됩니다.
   - `topologyKey: "kubernetes.io/hostname"`은 같은 호스트(노드)에 배치되어야 함을 의미합니다.
   - `requiredDuringSchedulingIgnoredDuringExecution`은 이 조건이 반드시 충족되어야 함을 의미합니다.

2. **포드 안티-어피니티(Pod Anti-Affinity)**:
   - `app=web-frontend` 레이블이 있는 다른 포드와는 다른 노드에 배치됩니다.
   - `topologyKey: "kubernetes.io/hostname"`은 다른 호스트(노드)에 배치되어야 함을 의미합니다.
   - `requiredDuringSchedulingIgnoredDuringExecution`은 이 조건이 반드시 충족되어야 함을 의미합니다.

이 설정을 통해 각 `web-frontend` 포드는 `cache` 포드가 있는 노드에 배치되지만, 다른 `web-frontend` 포드와는 다른 노드에 배치됩니다. 이는 캐시 접근 지연 시간을 최소화하면서도 고가용성을 보장하는 데 유용합니다.
</details>

4. 다음 요구 사항에 맞는 PriorityClass와 이를 사용하는 포드 매니페스트를 작성하세요:
   - PriorityClass 이름: high-priority
   - 우선순위 값: 100000
   - 포드 이름: critical-service
   - 이미지: nginx:latest
   - QoS 클래스: Guaranteed (CPU 요청 및 제한: 500m, 메모리 요청 및 제한: 512Mi)

<details>
<summary>정답 보기</summary>

**정답:**

PriorityClass 매니페스트:
```yaml
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: high-priority
value: 100000
globalDefault: false
description: "This priority class is for critical services that should be scheduled first."
```

포드 매니페스트:
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: critical-service
spec:
  priorityClassName: high-priority
  containers:
  - name: nginx
    image: nginx:latest
    resources:
      requests:
        cpu: 500m
        memory: 512Mi
      limits:
        cpu: 500m
        memory: 512Mi
```

이 설정은 다음과 같이 작동합니다:
- `high-priority` PriorityClass는 100000의 우선순위 값을 가집니다. 이 값이 클수록 우선순위가 높습니다.
- `critical-service` 포드는 이 PriorityClass를 참조하여 높은 우선순위를 가집니다.
- 리소스 요청과 제한이 동일하게 설정되어 있어 Guaranteed QoS 클래스에 속합니다.

Guaranteed QoS 클래스는 다음 조건을 만족해야 합니다:
1. 모든 컨테이너가 CPU와 메모리에 대한 요청과 제한을 모두 지정해야 합니다.
2. 각 컨테이너의 CPU 요청과 CPU 제한이 동일해야 합니다.
3. 각 컨테이너의 메모리 요청과 메모리 제한이 동일해야 합니다.

이 포드는 리소스 부족 상황에서 가장 마지막에 축출되며, 스케줄링 시 다른 낮은 우선순위 포드보다 먼저 고려됩니다.
</details>

5. 다음 요구 사항에 맞는 PodDisruptionBudget 매니페스트를 작성하세요:
   - 이름: web-pdb
   - 대상 포드 셀렉터: app=web-server
   - 항상 최소 2개의 포드가 사용 가능하도록 설정

<details>
<summary>정답 보기</summary>

**정답:**

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: web-pdb
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: web-server
```

이 PodDisruptionBudget(PDB)은 다음과 같이 작동합니다:
- `app=web-server` 레이블이 있는 포드에 적용됩니다.
- `minAvailable: 2`는 자발적 중단(예: 노드 드레이닝, 클러스터 업그레이드) 중에도 항상 최소 2개의 포드가 사용 가능해야 함을 의미합니다.

대안으로, `maxUnavailable`을 사용할 수도 있습니다:
```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: web-pdb
spec:
  maxUnavailable: 1  # 최대 1개의 포드만 사용 불가능할 수 있음
  selector:
    matchLabels:
      app: web-server
```

PDB는 다음과 같은 상황에서 유용합니다:
- 클러스터 업그레이드 중 서비스 가용성 보장
- 노드 드레이닝 중 애플리케이션 중단 최소화
- 자동 확장 축소 중 서비스 연속성 유지

PDB는 비자발적 중단(예: 노드 장애, 하드웨어 장애)에는 영향을 미치지 않습니다.
</details>

## 고급 주제

1. **커스텀 스케줄러 구현**: Kubernetes에서는 기본 스케줄러 외에도 커스텀 스케줄러를 구현하여 특정 워크로드에 대한 스케줄링 요구 사항을 충족시킬 수 있습니다. 다음 중 커스텀 스케줄러를 구현하는 방법으로 올바른 것은 무엇인가요?

   - A) 기존 kube-scheduler를 수정하여 새로운 스케줄링 알고리즘 추가
   - B) 별도의 스케줄러 포드를 배포하고 `schedulerName` 필드를 사용하여 포드 연결
   - C) 모든 포드에 특정 어노테이션을 추가하여 스케줄링 동작 변경
   - D) kubelet 설정을 수정하여 로컬 스케줄링 활성화

<details>
<summary>정답 보기</summary>

**정답: B) 별도의 스케줄러 포드를 배포하고 `schedulerName` 필드를 사용하여 포드 연결**

**설명:**
Kubernetes에서 커스텀 스케줄러를 구현하는 가장 일반적인 방법은 별도의 스케줄러 포드를 배포하고, 포드 스펙의 `schedulerName` 필드를 사용하여 해당 스케줄러가 특정 포드를 스케줄링하도록 지정하는 것입니다.

예를 들어:
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: custom-scheduled-pod
spec:
  schedulerName: my-custom-scheduler  # 커스텀 스케줄러 이름
  containers:
  - name: container
    image: nginx
```

커스텀 스케줄러는 Kubernetes API 서버와 통신하여 포드 및 노드 정보를 가져오고, 자체 알고리즘을 사용하여 포드를 노드에 할당합니다. 이를 통해 특정 워크로드에 대한 특별한 스케줄링 요구 사항(예: GPU 워크로드 최적화, 데이터 지역성 고려, 특수 하드웨어 활용 등)을 충족시킬 수 있습니다.

기존 kube-scheduler를 수정하는 것은 가능하지만 유지 관리가 어렵고, 어노테이션만으로는 완전한 스케줄링 동작을 변경할 수 없으며, kubelet은 스케줄링 결정을 담당하지 않습니다.
</details>

2. **Descheduler**: Kubernetes Descheduler는 이미 실행 중인 포드를 재스케줄링하여 클러스터 리소스 사용을 최적화하는 도구입니다. 다음 중 Descheduler의 주요 정책이 아닌 것은 무엇인가요?

   - A) LowNodeUtilization - 노드 간 리소스 사용률 불균형 해소
   - B) RemoveDuplicates - 동일한 노드에 있는 동일한 ReplicaSet의 포드 제거
   - C) PodLifeTimeExtension - 오래 실행된 포드의 수명 연장
   - D) RemovePodsViolatingInterPodAntiAffinity - 포드 안티-어피니티 규칙을 위반하는 포드 제거

<details>
<summary>정답 보기</summary>

**정답: C) PodLifeTimeExtension - 오래 실행된 포드의 수명 연장**

**설명:**
Kubernetes Descheduler는 클러스터의 포드 배치를 최적화하기 위해 다양한 정책을 제공합니다. 그러나 "PodLifeTimeExtension"은 실제 Descheduler 정책이 아닙니다. 오히려 Descheduler에는 "PodLifeTime"이라는 정책이 있는데, 이는 오래 실행된 포드를 제거하여 새로운 노드에 재스케줄링하도록 합니다.

Descheduler의 실제 주요 정책은 다음과 같습니다:

1. **LowNodeUtilization**: 노드 간 리소스 사용률 불균형을 해소합니다. 일부 노드가 과소 활용되고 다른 노드가 과다 활용되는 경우, 과다 활용된 노드에서 포드를 제거하여 과소 활용된 노드로 재스케줄링합니다.

2. **RemoveDuplicates**: 동일한 노드에 있는 동일한 ReplicaSet, StatefulSet 또는 Job의 복제본 포드를 제거합니다. 이는 고가용성을 향상시키기 위해 복제본을 다른 노드로 분산시키는 데 도움이 됩니다.

3. **RemovePodsViolatingInterPodAntiAffinity**: 포드 안티-어피니티 규칙을 위반하는 포드를 제거합니다. 이는 노드 추가 후 안티-어피니티 규칙이 위반될 수 있는 경우에 유용합니다.

4. **RemovePodsViolatingNodeAffinity**: 노드 어피니티 규칙을 위반하는 포드를 제거합니다. 노드 레이블이 변경되어 기존 포드가 노드 어피니티 규칙을 더 이상 만족하지 않는 경우에 유용합니다.

5. **PodLifeTime**: 지정된 기간보다 오래 실행된 포드를 제거합니다.

6. **RemovePodsHavingTooManyRestarts**: 너무 많은 재시작을 한 포드를 제거합니다.

7. **RemovePodsViolatingTopologySpreadConstraint**: 토폴로지 분산 제약 조건을 위반하는 포드를 제거합니다.

Descheduler는 클러스터 관리자가 설정한 정책에 따라 주기적으로 실행되며, 제거된 포드는 해당 컨트롤러(예: Deployment 컨트롤러)에 의해 다시 생성되어 더 나은 배치를 얻을 수 있습니다.
</details>

3. **노드 테인트 기반 축출(Taint-Based Evictions)**: Kubernetes는 노드 상태에 따라 자동으로 테인트를 적용하여 포드를 축출할 수 있습니다. 다음 중 노드 상태에 따른 테인트가 아닌 것은 무엇인가요?

   - A) `node.kubernetes.io/not-ready` - 노드가 준비되지 않은 상태
   - B) `node.kubernetes.io/unreachable` - 노드가 도달할 수 없는 상태
   - C) `node.kubernetes.io/out-of-disk` - 노드의 디스크 공간 부족
   - D) `node.kubernetes.io/high-load` - 노드의 부하가 높은 상태

<details>
<summary>정답 보기</summary>

**정답: D) `node.kubernetes.io/high-load` - 노드의 부하가 높은 상태**

**설명:**
Kubernetes는 노드의 상태에 따라 자동으로 테인트를 적용하여 새로운 포드가 스케줄링되는 것을 방지하고, 경우에 따라 기존 포드를 축출할 수 있습니다. 그러나 `node.kubernetes.io/high-load`는 Kubernetes에서 자동으로 적용하는 테인트가 아닙니다.

Kubernetes에서 자동으로 적용하는 노드 상태 테인트는 다음과 같습니다:

1. **`node.kubernetes.io/not-ready`**: 노드가 준비되지 않은 상태일 때 적용됩니다. 노드가 상태 점검에 실패하거나 kubelet이 API 서버에 보고하지 않는 경우 발생합니다.

2. **`node.kubernetes.io/unreachable`**: 노드 컨트롤러가 노드에 연결할 수 없을 때 적용됩니다. 네트워크 문제나 노드 장애로 인해 발생할 수 있습니다.

3. **`node.kubernetes.io/out-of-disk`**: 노드의 디스크 공간이 부족할 때 적용됩니다.

4. **`node.kubernetes.io/memory-pressure`**: 노드의 메모리 압박이 있을 때 적용됩니다.

5. **`node.kubernetes.io/disk-pressure`**: 노드의 디스크 압박이 있을 때 적용됩니다.

6. **`node.kubernetes.io/pid-pressure`**: 노드의 PID 압박이 있을 때 적용됩니다(너무 많은 프로세스가 실행 중).

7. **`node.kubernetes.io/network-unavailable`**: 노드의 네트워크가 올바르게 구성되지 않았을 때 적용됩니다.

이러한 테인트는 기본적으로 `NoExecute` 효과를 가질 수 있으며, 이 경우 해당 테인트를 톨러레이션하지 않는 포드는 노드에서 축출됩니다. 포드는 `tolerationSeconds` 필드를 사용하여 이러한 상태가 일시적인 경우 일정 시간 동안 노드에 남아있을 수 있습니다.

중요한 시스템 포드는 이러한 테인트에 대한 톨러레이션을 기본적으로 가지고 있어 노드 문제 시에도 계속 실행될 수 있습니다.
</details>

4. **토폴로지 분산 제약 조건(Topology Spread Constraints)**: Kubernetes 1.19부터 토폴로지 분산 제약 조건을 사용하여 포드를 다양한 토폴로지 도메인에 분산시킬 수 있습니다. 다음 중 토폴로지 분산 제약 조건에 대한 설명으로 올바르지 않은 것은 무엇인가요?

   - A) 가용 영역, 노드, 랙 등 다양한 토폴로지 도메인에 포드를 분산시킬 수 있다
   - B) `maxSkew` 필드는 토폴로지 도메인 간 포드 수의 최대 차이를 지정한다
   - C) `whenUnsatisfiable: DoNotSchedule`은 제약 조건을 만족할 수 없을 때 포드를 스케줄링하지 않는다
   - D) 토폴로지 분산 제약 조건은 기존 포드에 자동으로 적용되어 재배치한다

<details>
<summary>정답 보기</summary>

**정답: D) 토폴로지 분산 제약 조건은 기존 포드에 자동으로 적용되어 재배치한다**

**설명:**
토폴로지 분산 제약 조건(Topology Spread Constraints)은 포드를 다양한 토폴로지 도메인(예: 가용 영역, 노드, 랙 등)에 균등하게 분산시키는 기능을 제공합니다. 그러나 이 기능은 새로 생성되는 포드에만 적용되며, 기존 포드를 자동으로 재배치하지 않습니다.

토폴로지 분산 제약 조건의 주요 특징은 다음과 같습니다:

1. **토폴로지 도메인**: `topologyKey` 필드를 사용하여 포드를 분산시킬 토폴로지 도메인을 지정합니다. 예를 들어, `topology.kubernetes.io/zone`은 가용 영역 간에 포드를 분산시킵니다.

2. **최대 편차(maxSkew)**: 토폴로지 도메인 간 포드 수의 최대 허용 차이를 지정합니다. 예를 들어, `maxSkew: 1`은 어떤 두 도메인 간의 포드 수 차이가 최대 1이어야 함을 의미합니다.

3. **불만족 시 동작(whenUnsatisfiable)**: 제약 조건을 만족할 수 없을 때의 동작을 지정합니다:
   - `DoNotSchedule`: 제약 조건을 만족할 수 없으면 포드를 스케줄링하지 않습니다.
   - `ScheduleAnyway`: 제약 조건을 만족할 수 없어도 최대한 균등하게 분산시키려고 시도합니다.

4. **레이블 셀렉터(labelSelector)**: 어떤 포드를 계산에 포함할지 지정합니다.

예시:
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: example-pod
spec:
  topologySpreadConstraints:
  - maxSkew: 1
    topologyKey: topology.kubernetes.io/zone
    whenUnsatisfiable: DoNotSchedule
    labelSelector:
      matchLabels:
        app: web-server
  containers:
  - name: nginx
    image: nginx
```

이 예시에서는 `app=web-server` 레이블이 있는 포드가 가용 영역 간에 최대 1의 차이로 분산되도록 합니다.

기존 포드의 재배치가 필요한 경우, Descheduler의 `RemovePodsViolatingTopologySpreadConstraint` 정책을 사용하여 제약 조건을 위반하는 포드를 제거하고 재스케줄링할 수 있습니다.
</details>

5. **리소스 할당 및 QoS**: Kubernetes에서 포드의 QoS(Quality of Service) 클래스는 리소스 부족 시 축출 우선순위에 영향을 미칩니다. 다음 중 QoS 클래스에 대한 설명으로 올바르지 않은 것은 무엇인가요?

   - A) Guaranteed QoS 클래스는 모든 컨테이너의 리소스 요청과 제한이 동일할 때 할당된다
   - B) Burstable QoS 클래스는 적어도 하나의 컨테이너가 리소스 요청을 지정했지만 Guaranteed 조건을 만족하지 않을 때 할당된다
   - C) BestEffort QoS 클래스는 모든 컨테이너가 리소스 요청과 제한을 지정하지 않았을 때 할당된다
   - D) 리소스 부족 시 Guaranteed QoS 클래스의 포드가 가장 먼저 축출된다

<details>
<summary>정답 보기</summary>

**정답: D) 리소스 부족 시 Guaranteed QoS 클래스의 포드가 가장 먼저 축출된다**

**설명:**
Kubernetes에서 QoS(Quality of Service) 클래스는 리소스 부족 상황에서 포드의 축출 우선순위를 결정하는 중요한 요소입니다. 그러나 리소스 부족 시 Guaranteed QoS 클래스의 포드가 가장 먼저 축출된다는 설명은 잘못되었습니다. 실제로는 정반대입니다.

QoS 클래스와 축출 우선순위의 올바른 관계는 다음과 같습니다:

1. **BestEffort** (가장 낮은 우선순위):
   - 모든 컨테이너가 CPU와 메모리에 대한 요청과 제한을 지정하지 않은 경우
   - 리소스 부족 시 가장 먼저 축출됩니다.

2. **Burstable** (중간 우선순위):
   - 적어도 하나의 컨테이너가 CPU나 메모리에 대한 요청을 지정했지만, 모든 컨테이너가 Guaranteed 조건을 만족하지 않는 경우
   - BestEffort 포드가 모두 축출된 후에 축출 대상이 됩니다.
   - 같은 Burstable 클래스 내에서는 실제 메모리 사용량 대비 요청의 비율이 높은 포드가 먼저 축출됩니다.

3. **Guaranteed** (가장 높은 우선순위):
   - 모든 컨테이너가 CPU와 메모리에 대한 요청과 제한을 명시적으로 설정하고, 각 컨테이너의 요청과 제한이 동일한 경우
   - 리소스 부족 시 마지막으로 축출됩니다.
   - 시스템이 극도로 압박받는 상황에서만 축출 대상이 됩니다.

이러한 축출 우선순위는 노드의 리소스(특히 메모리)가 부족할 때 kubelet의 축출 관리자에 의해 적용됩니다. 이는 중요한 워크로드에 Guaranteed QoS 클래스를 할당하여 리소스 부족 상황에서도 계속 실행되도록 보장하는 데 유용합니다.

QoS 클래스는 포드의 리소스 요청과 제한 설정에 따라 자동으로 할당되며, 포드 스펙에서 직접 지정할 수 없습니다.
</details>
