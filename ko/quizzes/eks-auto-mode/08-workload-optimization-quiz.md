# EKS Auto Mode 워크로드 최적화 퀴즈

> **관련 문서**: [워크로드 최적화](../../eks-auto-mode/08-workload-optimization.md)
> **마지막 업데이트**: 2026년 9월 12일

## 객관식 문제

### 1. 가용성이 중요한 프론트엔드의 합리적인 시작 구성은 무엇인가요?

- A) Spot-only가 항상 적합하다고 가정
- B) On-Demand와 애플리케이션 가용성·disruption 제어
- C) 항상 GPU 요구
- D) Memory-optimized 노드만

<details>
<summary>정답 보기</summary>

**정답: B) On-Demand와 애플리케이션 가용성·disruption 제어**

**설명:**
On-Demand는 Spot 회수 이벤트를 피하지만 가용성 보장은 아닙니다. Replica·topology·readiness·PDB·복구를 검증해야 합니다. 아래 대안 budget은 UTC 00:00에 매일 14시간, 즉 서울 09:00–23:00 창을 시작합니다. 이전 매시간 `9-23` 패턴처럼 창을 반복 연장하지 않습니다. 활성 budget은 최솟값으로 결합하며 모든 forceful 중단을 제어하지는 않습니다.
```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: web-tier
spec:
  template:
    spec:
      requirements:
      - key: eks.amazonaws.com/instance-category
        operator: In
        values:
        - m
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - on-demand
      - key: kubernetes.io/arch
        operator: In
        values:
        - amd64
        - arm64
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
      expireAfter: 168h
      terminationGracePeriod: 24h
      taints:
      - key: workload-lab
        value: web-tier
        effect: NoSchedule
    metadata:
      labels:
        workload-lab: web-tier
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 5m
    budgets:
    - nodes: 10%
    - nodes: '1'
      schedule: 0 0 * * *
      duration: 14h
  limits:
    cpu: '32'
    memory: 128Gi
```


</details>

### 2. Interruption 내성과 영구 복구를 입증한 batch 워크로드에 적합할 수 있는 pool은 무엇인가요?

- A) On-Demand만 가능
- B) 호환 인스턴스 다양성·빈 노드 정리를 적용한 Spot
- C) GPU만
- D) 기본적으로 system pool

<details>
<summary>정답 보기</summary>

**정답: B) 호환 인스턴스 다양성·빈 노드 정리를 적용한 Spot**

**설명:**
모든 batch 작업이 interruption을 감당하지는 않습니다. Spot-only에는 On-Demand fallback이 없습니다. 컨테이너 재시작이나 `SPOT_AWARE=true`는 checkpoint/resume 로직이 아니므로 멱등 output·영구 진행 상태를 사용합니다. `WhenEmpty`의 30초 debounce는 30초 후 실행 중 Job을 죽이지 않습니다. 본문은 제한된 Indexed smoke Job이며 프로덕션 데이터 처리 구현은 아닙니다.
```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: batch-tier
spec:
  template:
    spec:
      requirements:
      - key: eks.amazonaws.com/instance-category
        operator: In
        values:
        - c
        - m
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - spot
      - key: kubernetes.io/arch
        operator: In
        values:
        - amd64
        - arm64
      - key: eks.amazonaws.com/instance-generation
        operator: Gt
        values:
        - '4'
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
      expireAfter: 168h
      terminationGracePeriod: 24h
      taints:
      - key: workload-lab
        value: batch-tier
        effect: NoSchedule
    metadata:
      labels:
        workload-lab: batch-tier
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30s
    budgets:
    - nodes: 10%
  limits:
    cpu: '16'
    memory: 64Gi
```


</details>

### 3. 추론 pool의 15분 `consolidateAfter`를 어떻게 해석해야 하나요?

- A) GPU 시작 마감 보장
- B) Consolidation debounce/churn 절충의 예시
- C) Scheduler의 모든 Pod 배치를 막는 지연
- D) 노드가 만료되지 않는다는 보장

<details>
<summary>정답 보기</summary>

**정답: B) Consolidation debounce/churn 절충의 예시**

**설명:**
GPU Ready나 warm capacity를 보장하지 않습니다. `WhenEmpty`는 consolidation을 좁히며 drift·expiration·interruption은 별도입니다. Model warm-up·desired capacity·비용을 실측에 맞추세요. 본문 추론 template은 검토된 image/runtime/probe 전까지 replicas 0을 유지합니다. 또한 4 CPU/16Gi Pod는 system 예약을 제외하면 g5.xlarge에 들어가지 않습니다.
```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: gpu-tier
spec:
  template:
    spec:
      requirements:
      - key: eks.amazonaws.com/instance-category
        operator: In
        values:
        - g
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - on-demand
      - key: kubernetes.io/arch
        operator: In
        values:
        - amd64
      - key: node.kubernetes.io/instance-type
        operator: In
        values:
        - g5.2xlarge
        - g5.4xlarge
      - key: eks.amazonaws.com/instance-gpu-manufacturer
        operator: In
        values:
        - nvidia
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: gpu-nodeclass
      expireAfter: 168h
      terminationGracePeriod: 24h
      taints:
      - key: workload-lab
        value: gpu-tier
        effect: NoSchedule
      - key: nvidia.com/gpu
        value: 'true'
        effect: NoSchedule
    metadata:
      labels:
        workload-lab: gpu-tier
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 15m
    budgets:
    - nodes: 10%
  limits:
    cpu: '64'
    memory: 256Gi
    nvidia.com/gpu: '4'
```


</details>

### 4. 호환성이 있고 interruption을 감당하는 애플리케이션 API backend의 비용·가용성 균형에 가능한 접근은 무엇인가요?

- A) On-Demand는 항상 잘못됨
- B) Spot-only가 항상 가용성 보장
- C) Spot/On-Demand 혼합과 검증한 ARM 지원 평가
- D) Auto Mode가 Fargate 노드를 만든다고 가정

<details>
<summary>정답 보기</summary>

**정답: C) Spot/On-Demand 혼합과 검증한 ARM 지원 평가**

**설명:**
애플리케이션 API backend에 대한 설명이며 AWS 관리형 Kubernetes API server가 아닙니다. 혼합 용량은 고정 비율·즉각적인 fallback이 아니고 ARM에는 호환 image/dependency·애플리케이션 테스트가 필요합니다. `weight: 10`은 상대 프로비저닝 선호이지 백분율·지출 상한이 아닙니다. 이전 ~40% 절감은 미검증 추정입니다.
```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: api-tier
spec:
  template:
    spec:
      requirements:
      - key: eks.amazonaws.com/instance-category
        operator: In
        values:
        - m
        - c
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - on-demand
        - spot
      - key: kubernetes.io/arch
        operator: In
        values:
        - amd64
        - arm64
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
      expireAfter: 168h
      terminationGracePeriod: 24h
      taints:
      - key: workload-lab
        value: api-tier
        effect: NoSchedule
    metadata:
      labels:
        workload-lab: api-tier
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 5m
    budgets:
    - nodes: 10%
  limits:
    cpu: '100'
    memory: 400Gi
  weight: 10
```


</details>

### 5. amd64와 arm64를 모두 허용하기 전에 무엇을 검증해야 하나요?

- A) 없음
- B) 고정된 image platform·native 의존성·애플리케이션 동작
- C) Kubernetes 버전만
- D) 리전만

<details>
<summary>정답 보기</summary>

**정답: B) 고정된 image platform·native 의존성·애플리케이션 동작**

**설명:**
아래 index 검사는 Linux platform 항목 확인이며 runtime 정확성 검증이 아닙니다. 관련 없는 attestation 항목을 제외하고 필요한 platform이 없으면 거부합니다. 본문은 로컬 OCI build output을 사용하며, 불명확한 `myapp:latest` 게시가 아키텍처 검사의 필수 단계는 아닙니다.

```bash
: "${IMAGE_REF:?Set a reviewed image reference pinned by digest}"
if ! [[ "$IMAGE_REF" =~ @sha256:[0-9a-f]{64}$ ]]; then
  printf 'Use an immutable sha256 digest reference.\n' >&2
  exit 1
fi
docker buildx imagetools inspect --raw "$IMAGE_REF" > "$WORK_DIR/image-index.json"
jq -e '[.manifests[]?.platform |
         select(.os=="linux" and (.architecture=="amd64" or .architecture=="arm64")) |
         .architecture] | unique | sort == ["amd64","arm64"]' \
  "$WORK_DIR/image-index.json"
```


</details>

### 6. 배치 제한을 tolerate하면서 대상 pool을 선택하는 방법은 무엇인가요?

- A) Pod 이름 매칭
- B) 일치하는 toleration과 nodeSelector 또는 required node affinity
- C) Namespace 자동 매칭
- D) AWS tag만

<details>
<summary>정답 보기</summary>

**정답: B) 일치하는 toleration과 nodeSelector 또는 required node affinity**

**설명:**
Toleration은 taint 노드 배치를 허용하지만 그 노드를 강제하지는 않습니다. Selector/required affinity가 적격 노드를 좁힙니다. 다음은 Pod template의 `spec` 조각이며 본문에 완전한 Job이 있습니다. Label/taint는 테넌트 권한 경계가 아니고 일치 용량이 부족하면 Pod는 Pending일 수 있습니다.
```yaml
nodeSelector:
  karpenter.sh/nodepool: batch-tier
tolerations:
- key: workload-lab
  operator: Equal
  value: batch-tier
  effect: NoSchedule
```


</details>

## 참고 자료

- [Auto Mode ML compute](https://docs.aws.amazon.com/eks/latest/userguide/ml-node-pools.html)
- [Karpenter disruption](https://karpenter.sh/v1.14/concepts/disruption/)
- [Docker multi-platform builds](https://docs.docker.com/build/building/multi-platform/)
