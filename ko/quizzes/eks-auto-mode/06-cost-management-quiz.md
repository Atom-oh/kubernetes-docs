# EKS Auto Mode 비용 관리 퀴즈

> **관련 문서**: [비용 관리](../../eks-auto-mode/06-cost-management.md)
> **마지막 업데이트**: 2026년 9월 12일

## 객관식 문제

### 1. ARM 노드를 허용할 때 이전 “Graviton 20% 절감” 수치는 어떻게 사용해야 하나요?

- A) AWS의 보편적 보장
- B) 전체 청구액 할인
- C) 검증되지 않은 예시로 두고 호환 워크로드·실제 요율 비교
- D) 모든 이미지의 ARM 실행 증거

<details>
<summary>정답 보기</summary>

**정답: C) 검증되지 않은 예시로 두고 호환 워크로드·실제 요율 비교**

**설명:**
이전 ARM ~20%, Spot 70–90%는 이 워크로드에서 검증한 비교가 아닌 계획 예시입니다. 다중 아키텍처 이미지·의존성·유효 작업당 성능·현재 리전 요율·Auto Mode/기타 요금을 확인합니다. `amd64`와 `arm64` 허용은 애플리케이션 호환성 검증이나 특정 아키텍처 선택 보장이 아닙니다.

</details>

### 2. 동적 NodePool의 `limits.cpu: 500`은 무엇을 제한하나요?

- A) 각 노드를 500 core로 제한
- B) 해당 pool이 프로비저닝한 CPU 리소스 합계
- C) 각 Pod를 500m로 제한
- D) 계정의 모든 AWS 지출

<details>
<summary>정답 보기</summary>

**정답: B) 해당 pool이 프로비저닝한 CPU 리소스 합계**

**설명:**
Pool 수준 리소스 상한이며 급격한 프로비저닝에서는 eventual consistency로 일시 초과할 수 있습니다. `1Ti`는 1 TiB(1024 GiB)이며 십진수 1 TB가 아닙니다. 리소스 limits는 확장을 제한하지만 인스턴스 가격·다른 서비스 비용을 계산하거나 강제 금액 예산을 적용하지는 않습니다.
```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: compute-optimized
spec:
  template:
    spec:
      requirements:
      - key: eks.amazonaws.com/instance-category
        operator: In
        values:
        - m
        - c
        - r
        - i
        - d
      - key: kubernetes.io/arch
        operator: In
        values:
        - amd64
        - arm64
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - spot
        - on-demand
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
      taints:
      - key: cost-lab
        value: 'true'
        effect: NoSchedule
    metadata:
      labels:
        cost-lab: 'true'
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 1m
    budgets:
    - nodes: 10%
  limits:
    cpu: '500'
    memory: 1Ti
```


</details>

### 3. 재배치·비용 제약이 허용할 때 빈 노드와 저활용 노드의 consolidation을 허용하는 정책은 무엇인가요?

- A) `WhenEmpty`
- B) `WhenEmptyOrUnderutilized`
- C) `Always`
- D) `Aggressive`

<details>
<summary>정답 보기</summary>

**정답: B) `WhenEmptyOrUnderutilized`**

**설명:**
Requests 기반 배치 가능성과 비용을 평가하며 실측 CPU 임계값 아래의 모든 노드를 삭제하지 않습니다. `consolidateAfter`는 debounce이고 PDB·budget·배치 제약이 consolidation을 막을 수 있습니다. `WhenEmpty`는 범위가 더 좁지만 두 정책 모두 절감이나 다른 모든 중단 비활성화를 보장하지는 않습니다.

</details>

### 4. 적격 EC2 사용량의 패밀리·리전이 바뀔 수 있을 때 청구 유연성을 제공하는 옵션은 무엇인가요?

- A) Compute Savings Plans
- B) 한 패밀리·리전에 고정된 EC2 Instance Savings Plan
- C) 정확히 한 크기의 Standard RI만
- D) 모든 약정 할인 제외

<details>
<summary>정답 보기</summary>

**정답: A) Compute Savings Plans**

**설명:**
Compute Savings Plans는 패밀리·크기·리전·OS·tenancy 유연성을 제공합니다. EC2 Instance Savings Plans는 패밀리·리전 약정이며 그 안의 크기·OS·tenancy 유연성이 있습니다. 광고 최대는 각각 66%·72%이며 예상 요율이 아닙니다. USD/hour 약정을 지속되는 적격 미커버 사용량·기존 약정·향후 변경과 맞추세요. 이전 3개월/70% coverage 전략은 검증되지 않은 계획 예시입니다. Spot·별도 Auto Mode 요금은 EC2 Savings Plans 할인을 받지 않으며 별도 ARM plan이나 GPU 전체 제외 규칙도 없습니다.

</details>

### 5. 유용한 Kubecost Pod 수준 비용 할당에 필요한 것은 무엇인가요?

- A) 설정·데이터 소스 불필요
- B) Pod cost-center label만
- C) 구성된 agent/클러스터 연동과 적절한 비용 데이터
- D) Kubernetes 할당 데이터 없이 Cost Explorer만

<details>
<summary>정답 보기</summary>

**정답: C) 구성된 agent/클러스터 연동과 적절한 비용 데이터**

**설명:**
검토한 Kubecost 3.2.4 chart는 새 저장소의 `kubecost/kubecost`입니다. 버전 3의 FinOps agent/ClickHouse 구조는 이전 cost-analyzer 배포와 다릅니다. 라이선스·private 접근·스토리지/보존·워크로드 IAM·청구 대조를 구성하세요. 설치 전에 검토한 values를 렌더링하며 label만으로 실제 비용 데이터가 생성되지는 않습니다.

```bash
: "${KUBECOST_VALUES:?Set the reviewed Kubecost 3.2.4 values file}"
test -f "$KUBECOST_VALUES"
helm repo add kubecost https://kubecost.github.io/kubecost/
helm repo update kubecost
helm show chart kubecost/kubecost --version 3.2.4
helm template cost-review kubecost/kubecost --version 3.2.4 \
  --namespace kubecost --values "$KUBECOST_VALUES" \
  > "$WORK_DIR/kubecost-rendered.yaml"
```


</details>

### 6. Resource request 변경에 어떤 증거를 사용해야 하나요?

- A) 항상 request와 limit을 같게 함
- B) VPA 권장값과 대표 워크로드/SLO 증거
- C) 모든 request 최대화
- D) Requests 제거

<details>
<summary>정답 보기</summary>

**정답: B) VPA 권장값과 대표 워크로드/SLO 증거**

**설명:**
`Off`는 권장값을 적용하지 않으며 정상 VPA 컴포넌트·metrics가 필요합니다. 모든 컨테이너, 신뢰도/이력, 시작 peak, memory limit과 CPU throttling을 확인하세요. 권장값은 성능·모든 OOM 방지·절감의 보장이 아닙니다. Quantity 비교 시 Kubernetes 단위 접미사를 지우지 마세요.
```yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: cost-app-vpa
  namespace: cost-lab
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: cost-efficient-app
  updatePolicy:
    updateMode: 'Off'
  resourcePolicy:
    containerPolicies:
    - containerName: '*'
      minAllowed:
        cpu: 100m
        memory: 128Mi
      maxAllowed:
        cpu: '4'
        memory: 8Gi
```


</details>

### 7. 티어별 interruption·아키텍처 요구가 실제로 다를 때 이를 표현할 수 있는 설계는 무엇인가요?

- A) 모든 티어에 같은 배치 강제
- B) 적절한 티어 pool과 일치하는 워크로드 제약
- C) 모든 인스턴스 크기마다 별도 pool
- D) 각 AZ가 별도 청구 할인이라고 가정

<details>
<summary>정답 보기</summary>

**정답: B) 적절한 티어 pool과 일치하는 워크로드 제약**

**설명:**
별도 pool은 실제 제약을 표현하지만 분할이 idle cost를 늘릴 수도 있습니다. Spot 전용 batch pool에는 On-Demand fallback이 없으므로 호환되는 interruption-tolerant 작업과 복구에 사용하세요. Pool 이름만으로 워크로드가 배치되지는 않으며 본문처럼 selector/toleration이 필요합니다.

| 티어 | 이전 전략 | 원래의 미검증 절감 |
|------|-----------|---------------------|
| 프론트엔드 | On-Demand + Graviton | ~20% |
| API | Spot 혼합 + Graviton | ~40% |
| 배치 | Spot + 다양성 | ~70% |
| ML | 인스턴스 적정화 | ~30% |

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
        - m
        - c
        - r
        - i
        - d
      - key: kubernetes.io/arch
        operator: In
        values:
        - amd64
        - arm64
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - spot
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
      taints:
      - key: cost-lab
        value: 'true'
        effect: NoSchedule
    metadata:
      labels:
        cost-lab: 'true'
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 1m
    budgets:
    - nodes: 10%
  limits:
    cpu: '100'
    memory: 400Gi
```


</details>

### 8. 커스텀 NodeClass 태그를 AWS 비용 할당에 사용하려면 무엇이 필요한가요?

- A) 모든 Kubernetes label 자동 전파
- B) 유효한 NodeClass·태깅 권한·실제 리소스 태그·Billing 활성화
- C) AWS Organization 생성만
- D) 태그 할당 불가능

<details>
<summary>정답 보기</summary>

**정답: B) 유효한 NodeClass·태깅 권한·실제 리소스 태그·Billing 활성화**

**설명:**
본문에는 identity/network selector가 있는 완전한 NodeClass가 있습니다. Node access entry·태그 권한을 검토하고 대상 pool에서 참조한 뒤 실제 태그·Billing key 활성화를 확인하세요. 사용자 정의 key는 표시까지 최대 24시간, 활성화에 추가 최대 24시간이 걸릴 수 있고 보고서 지연은 별도입니다. AWS 생성 EC2 클러스터 key는 `aws:eks:cluster-name`이며 control-plane 비용을 포함하지 않습니다. Namespace label만으로 모든 AWS 비용이 전파·할당되지는 않습니다.

</details>

## 참고 자료

- [EKS pricing](https://aws.amazon.com/eks/pricing/)
- [Savings Plans types](https://docs.aws.amazon.com/savingsplans/latest/userguide/plan-types.html)
- [EKS billing tags](https://docs.aws.amazon.com/eks/latest/userguide/eks-using-tags.html)
