# EKS Auto Mode Spot 전략 퀴즈

> **관련 문서**: [Spot 인스턴스 전략](../../eks-auto-mode/04-spot-strategies.md)

## 객관식 문제

### 1. 호환되는 Spot 용량 선택지를 넓히는 방법은 무엇인가요?

- A) 한 AZ의 단일 인스턴스 유형만 사용
- B) 호환되는 유형·크기·아키텍처·AZ를 다양하게 허용
- C) 호환되지 않는 이미지를 추가 아키텍처에서 강제로 실행
- D) 항상 가장 저렴한 유형만 선택

<details>
<summary>정답 보기</summary>

**정답: B) 호환되는 유형·크기·아키텍처·AZ를 다양하게 허용**

**설명:**
Spot pool은 인스턴스 유형/AZ 조합에 연결됩니다. 다양화는 선택지를 늘리지만 중단을 독립적으로 만들거나 아키텍처 두 개만으로 실제 용량을 두 배로 만들지 않습니다. 이미지, 의존성과 성능 특성을 먼저 검증하세요.

```yaml
requirements:
- key: eks.amazonaws.com/instance-category
  operator: In
  values:
  - m
  - c
  - r
  - i
  - d
- key: eks.amazonaws.com/instance-generation
  operator: Gt
  values:
  - '4'
- key: eks.amazonaws.com/instance-size
  operator: In
  values:
  - large
  - xlarge
  - 2xlarge
- key: kubernetes.io/arch
  operator: In
  values:
  - amd64
  - arm64
- key: karpenter.sh/capacity-type
  operator: In
  values:
  - spot
```

위 내용은 requirements 조각이며 완전한 NodePool이 아닙니다.

</details>

### 2. 예제에서 Spot과 On-Demand 용량을 구분하는 label은 무엇인가요?

- A) node.kubernetes.io/capacity-type
- B) karpenter.sh/capacity-type
- C) eks.amazonaws.com/instance-type
- D) karpenter.k8s.aws/spot-or-ondemand

<details>
<summary>정답 보기</summary>

**정답: B) karpenter.sh/capacity-type**

**설명:**
NodePool requirements나 Pod 선택에 `karpenter.sh/capacity-type`을 사용합니다. Preferred affinity는 Spot 사용을 강제하거나 여유 노드를 예약하거나 고정 구매 비율을 만들지 않습니다.

```yaml
affinity:
  nodeAffinity:
    preferredDuringSchedulingIgnoredDuringExecution:
    - weight: 100
      preference:
        matchExpressions:
        - key: karpenter.sh/capacity-type
          operator: In
          values:
          - spot
```

필수 기본 용량은 별도 워크로드에 호환되는 hard selector/required affinity로 지정하세요. Downward API의 `spec.nodeName`은 노드 이름이며 Spot 여부 boolean이 아닙니다.

</details>

### 3. EC2 Spot stop/terminate 경고를 어떻게 해석해야 하나요?

- A) 모든 Pod에 30초가 보장된다
- B) 일반적으로 2분이며 best effort로 전달된다
- C) 모든 Pod에 5분이 보장된다
- D) preStop으로 10분 연장을 요청할 수 있다

<details>
<summary>정답 보기</summary>

**정답: B) 일반적으로 2분이며 best effort로 전달된다**

**설명:**
EC2는 일반적으로 stop/terminate 전에 2분 경고를 제공하지만 best effort이며 hibernation은 즉시 시작하는 다른 동작입니다. Kubernetes 감지·축출과 애플리케이션 처리가 시간을 소모합니다. Pod grace period와 preStop이 EC2 기한을 늘리지 않으며 90초 sleep은 checkpoint나 graceful shutdown 구현이 아닙니다. 주기적 durable checkpoint, idempotent 복구와 검증된 신호 처리를 사용하세요.

</details>

### 4. 중단 가능한 용량에 의존하기 전에 가장 재설계가 필요한 패턴은 무엇인가요?

- A) 재시도를 검증한 idempotent batch 작업
- B) 복제본과 장애조치를 검증한 stateless 서비스
- C) 복구 경로가 없고 유일한 상태를 로컬에 둔 중요 단일 DB
- D) 지연과 재시도를 허용하는 개발 작업

<details>
<summary>정답 보기</summary>

**정답: C) 복구 경로가 없고 유일한 상태를 로컬에 둔 중요 단일 DB**

**설명:**
단일 인스턴스 패턴은 가용성과 유일한 상태를 잃을 수 있습니다. On-Demand도 노드 로컬 스토리지를 durable하게 만들거나 유지보수·장애 위험을 없애지 않습니다. DB, queue와 장기 작업은 이름만으로 일괄 분류하지 말고 아키텍처별로 평가해야 합니다.

</details>

### 5. 한 혼합 용량 NodePool에서 Spot 우선 선택을 어떻게 허용하나요?

- A) spotPriority: high 설정
- B) spot과 on-demand를 허용하면 Auto Mode가 적합한 용량 우선순위를 적용
- C) capacityPriority: spot 설정
- D) weight로 정확히 80%의 Spot 노드를 예약

<details>
<summary>정답 보기</summary>

**정답: B) spot과 on-demand를 허용하면 Auto Mode가 적합한 용량 우선순위를 적용**

**설명:**
두 용량 유형을 허용합니다. 배열 순서와 weight가 풀 안의 비율을 정하지는 않습니다. 적합한 reserved 용량도 허용하면 Spot보다 우선하며, Spot은 On-Demand보다 우선합니다. 가용성과 제약은 여전히 적용됩니다.

별도의 두 풀 전략에서는 weight로 프로비저닝 선호도를 지정할 수 있습니다.

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: spot-first
spec:
  weight: 100
  template:
    spec:
      requirements:
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - spot
      - key: eks.amazonaws.com/instance-category
        operator: In
        values:
        - c
        - m
        - r
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
      taints:
      - key: spot-lab
        value: 'true'
        effect: NoSchedule
    metadata:
      labels:
        capacity-example: spot-lab
        capacity-strategy: spot-preferred
  limits:
    cpu: '100'
    memory: 400Gi
---
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: ondemand-fallback
spec:
  weight: 10
  template:
    spec:
      requirements:
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - on-demand
      - key: eks.amazonaws.com/instance-category
        operator: In
        values:
        - c
        - m
        - r
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
      taints:
      - key: spot-lab
        value: 'true'
        effect: NoSchedule
    metadata:
      labels:
        capacity-example: spot-lab
        capacity-strategy: spot-preferred
  limits:
    cpu: '100'
    memory: 400Gi
```

두 풀은 공통 label과 실습 taint를 사용합니다. Fallback이 필요한 워크로드는 해당 taint를 허용하고 두 풀에 모두 맞아야 합니다. Spot-only 풀 이름으로 Pod를 고정하면 fallback할 수 없습니다. Weight가 이미 배치된 Pod를 옮기거나 즉시 대체 용량을 보장하지는 않습니다.

</details>

### 6. AWS가 안내하는 잠재적 EC2 Spot 할인은 무엇인가요?

- A) 30–40% 절감을 보장
- B) 50–60% 절감을 보장
- C) On-Demand 대비 최대 90%이며 전체 워크로드 절감 보장은 아님
- D) 95% 이상 절감을 보장

<details>
<summary>정답 보기</summary>

**정답: C) On-Demand 대비 최대 90%이며 전체 워크로드 절감 보장은 아님**

**설명:**
실제 단가와 유효 작업 비용은 유형, AZ, 기간, 복구와 다른 요금에 따라 달라집니다. Auto Mode 관리 요금도 EC2 가격에 추가됩니다. 이전 교육용 표는 검증된 결과로 주장하지 않고 아래에 보존합니다.

| 이전 예시 | 검증되지 않은 수치 |
|---|---|
| Spot | 70–90% |
| Graviton/ARM | 약 20% |
| Spot + Graviton | 최대 90% |

비교 기준과 측정 근거가 확인되지 않았습니다. 비율을 더하거나 보장된 절감액으로 취급하지 마세요. Advisor는 지연될 수 있는 지난달 요약이므로 AZ별 가격 이력·실제 청구서를 사용하고 복구 시간을 이중 계산하지 않아야 합니다.

</details>
