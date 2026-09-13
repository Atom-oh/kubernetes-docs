# EKS Auto Mode 스케일링 동작 퀴즈

> **관련 문서**: [스케일링 동작](../../eks-auto-mode/03-scaling-behavior.md)

## 객관식 문제

### 1. `consolidationPolicy: WhenEmptyOrUnderutilized`는 어떤 동작을 허용하나요?

- A) 빈 노드만 제거
- B) 조건을 충족한 빈 노드 또는 비어 있지 않은 노드의 비용 절감 통합
- C) 모든 노드를 무기한 유지
- D) 정해진 시각에만 제거

<details>
<summary>정답 보기</summary>

**정답: B) 조건을 충족한 빈 노드 또는 비어 있지 않은 노드의 비용 절감 통합**

**설명:**
관련 제약을 만족하며 워크로드를 배치할 수 있으면 제거하거나 더 저렴한 노드로 교체할 수 있습니다. Resource requests, PDB, budget과 annotation이 중요하며 단순한 실측 CPU 임계값이 아닙니다.

```yaml
# Fragment inside a NodePool; eligibility delay, not a deletion deadline
disruption:
  consolidationPolicy: WhenEmptyOrUnderutilized
  consolidateAfter: 1m
```

Pod 추가·제거 시 타이머가 재설정됩니다. 1분은 후보 검토를 위한 안정화 지연이지 삭제·교체가 1분 안에 끝난다는 보장이 아닙니다. 현재 AWS API는 절감 효과와 중단 비용을 함께 고려하는 `Balanced`도 지원합니다.

</details>

### 2. NodeClaim 목록을 조회하는 명령은 무엇인가요?

- A) kubectl get nodes --show-claims
- B) kubectl get nodeclaims
- C) kubectl describe karpenter claims
- D) kubectl get ec2-nodes

<details>
<summary>정답 보기</summary>

**정답: B) kubectl get nodeclaims**

**설명:**
NodeClaim은 프로비저닝 순간만이 아니라 원하는 노드 구성과 provider 수명 주기·상태를 나타냅니다. Condition과 연결된 node name을 확인하세요. `Drifted`는 condition이며 이전의 잘못된 `karpenter.sh/drift-hash` node annotation이 아닙니다.

```bash
kubectl --context "$CLUSTER_NAME" --request-timeout=15s get nodeclaims -o wide
: "${NODECLAIM_NAME:?Select a NodeClaim from the list}"
kubectl --context "$CLUSTER_NAME" --request-timeout=15s describe nodeclaim "$NODECLAIM_NAME"
```

</details>

### 3. 스케줄 불가능한 Pod가 Auto Mode 용량 프로비저닝으로 이어질 수 있는 조건은 무엇인가요?

- A) 모든 Pod가 5분 동안 Pending이 된 경우
- B) 기존 용량에 배치할 수 없고 적합한 풀·용량으로 Pod 제약을 만족할 수 있는 경우
- C) 노드 수가 고정된 전역 임계값보다 작은 경우
- D) 운영자가 수동 scale 명령을 실행한 경우에만 가능

<details>
<summary>정답 보기</summary>

**정답: B) 기존 용량에 배치할 수 없고 적합한 풀·용량으로 Pod 제약을 만족할 수 있는 경우**

**설명:**
스케줄러가 Pod를 배치하지 못하는 이유, NodePool/NodeClass 제약, 할당량과 실제 가용 용량이 모두 중요합니다. 이미 배치된 Pod가 이미지나 init container를 기다리는 Pending 상태라면 새 노드가 필요하지 않을 수 있습니다. 즉시 할당이나 이전의 검증되지 않은 40–90초 추정값이 보장되지는 않습니다.

</details>

### 4. 어떤 조건이 후보 노드의 consolidation을 막을 수 있나요?

- A) 적용되는 do-not-disrupt annotation
- B) 필요한 워크로드 축출을 막는 PDB
- C) consolidateAfter 안정화 구간이 아직 지나지 않음
- D) 위의 모든 경우

<details>
<summary>정답 보기</summary>

**정답: D) 위의 모든 경우**

**설명:**
각 조건은 consolidation 작업을 막거나 늦출 수 있습니다. 이전 정답은 DaemonSet만 있는 노드까지 중단 조건으로 잘못 포함했습니다. 그런 노드는 빈 노드로 취급될 수 있습니다.

```yaml
# Metadata fragment on the intended Node or Pod, not NodePool metadata
metadata:
  annotations:
    karpenter.sh/do-not-disrupt: "true"
```

모든 중단 원인을 막는 보장은 아닙니다. Expiration, interruption과 종료 유예 한도를 별도로 고려하고, 임시 보호는 의도한 유지보수 필요가 끝나면 제거하세요.

</details>

### 5. 어떤 상황이 drift나 교체의 원인이 될 수 있나요?

- A) 관련된 원하는 NodeClass 구성과 현재 노드가 더 이상 일치하지 않음
- B) AWS가 새로운 관리형 Auto Mode AMI를 선택
- C) 해석된 서브넷·보안 그룹 선택이 변경됨
- D) 위의 모든 경우가 원인이 될 수 있음

<details>
<summary>정답 보기</summary>

**정답: D) 위의 모든 경우가 원인이 될 수 있음**

**설명:**
실제 NodeClaim condition과 provider 판단을 확인하세요. 모든 편집이 drift를 만들지는 않습니다. Requirements를 넓혀도 기존 인스턴스가 계속 호환될 수 있고 weight·limits·disruption 설정은 동작 정책입니다. 같은 보안 그룹의 규칙을 편집하는 것과 다른 그룹을 선택하는 것은 다릅니다. Graceful 교체는 배치 가능성과 budget을 따르며 병렬로 진행될 수 있습니다. 반드시 한 노드씩 순차적으로 교체하지는 않습니다.

</details>

### 6. Auto Mode 시작 지연을 어떻게 개선해야 하나요?

- A) amiFamily를 AL2023으로 변경
- B) 워크로드 경로를 측정하고 지원되는 용량·이미지·스토리지 변경을 실험
- C) 가장 작은 볼륨이 항상 가장 빠르다고 가정
- D) 40–90초를 보장된 종단 간 SLO로 사용

<details>
<summary>정답 보기</summary>

**정답: B) 워크로드 경로를 측정하고 지원되는 용량·이미지·스토리지 변경을 실험**

**설명:**
AWS가 관리형 Bottlerocket 이미지를 선택하며 Auto Mode에 이전의 `amiFamily` 비교 선택지는 없습니다. 노드 등록, 이미지·초기화와 애플리케이션 readiness를 구분하고 실패·timeout을 측정에 포함하세요.

이전 퀴즈의 **AL2023 20–40초**, **Bottlerocket 15–25초**는 검증되지 않은 과거 교육용 추정값으로 보존합니다. 실측 Auto Mode 결과가 아니며 현재 부팅 시간 우위나 지원되는 AMI 선택지를 입증하지 않습니다.

</details>
