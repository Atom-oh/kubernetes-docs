# EKS Auto Mode 스케일링 동작 퀴즈

> **관련 문서**: [스케일링 동작](../../eks-auto-mode/03-scaling-behavior.md)

## 객관식 문제

### 1. NodePool의 `consolidationPolicy: WhenEmptyOrUnderutilized`의 동작은 무엇인가요?

- A) 빈 노드만 제거
- B) 빈 노드와 저사용률 노드 모두 통합
- C) 모든 노드를 항상 유지
- D) 특정 시간에만 노드 제거

<details>
<summary>정답 보기</summary>

**정답: B) 빈 노드와 저사용률 노드 모두 통합**

**설명:**
`WhenEmptyOrUnderutilized` 정책은 빈 노드뿐만 아니라 저사용률 노드도 통합하여 비용을 최적화합니다. 이를 통해 여러 개의 저사용률 노드의 워크로드를 더 적은 수의 노드로 통합할 수 있습니다.

```yaml
disruption:
  consolidationPolicy: WhenEmptyOrUnderutilized
  consolidateAfter: 1m  # 조건 충족 후 1분 뒤 통합
```

**비교:**
- `WhenEmpty`: 빈 노드만 제거 (보수적)
- `WhenEmptyOrUnderutilized`: 빈 노드 + 저사용률 노드 통합 (적극적)

</details>

### 2. NodeClaim 상태를 확인하는 kubectl 명령어는 무엇인가요?

- A) `kubectl get nodes --show-claims`
- B) `kubectl get nodeclaims`
- C) `kubectl describe karpenter claims`
- D) `kubectl get ec2-nodes`

<details>
<summary>정답 보기</summary>

**정답: B) `kubectl get nodeclaims`**

**설명:**
NodeClaim은 프로비저닝 중인 노드의 상태를 나타내는 리소스입니다.

```bash
# NodeClaim 목록 확인
kubectl get nodeclaims

# 특정 NodeClaim 상세 정보
kubectl describe nodeclaim <name>

# NodeClaim과 노드 정보 함께 확인
kubectl get nodeclaims -o wide
```

</details>

### 3. Auto Mode에서 Pending Pod가 발생했을 때 노드 프로비저닝이 시작되는 조건은 무엇인가요?

- A) Pod가 5분 이상 Pending 상태일 때
- B) NodePool의 requirements를 충족하는 노드가 없을 때
- C) 클러스터의 전체 노드 수가 임계값 이하일 때
- D) 수동으로 스케일업 명령을 실행할 때

<details>
<summary>정답 보기</summary>

**정답: B) NodePool의 requirements를 충족하는 노드가 없을 때**

**설명:**
Auto Mode는 Pending Pod의 요구사항을 분석하고, 적합한 노드가 없으면 즉시 새 노드를 프로비저닝합니다.

**프로비저닝 흐름:**
1. Pod가 Pending 상태가 됨
2. Karpenter가 Pod의 리소스 요청, nodeSelector, affinity 분석
3. 적합한 NodePool의 requirements 확인
4. 최적의 인스턴스 타입 선택
5. EC2 인스턴스 시작 (40-90초)

</details>

### 4. Consolidation이 발생하지 않는 경우는 무엇인가요?

- A) 노드에 do-not-disrupt 어노테이션이 있을 때
- B) 노드에 DaemonSet Pod만 있을 때
- C) consolidateAfter 시간이 경과하지 않았을 때
- D) 위의 모든 경우

<details>
<summary>정답 보기</summary>

**정답: D) 위의 모든 경우**

**설명:**
Consolidation은 다음 상황에서 발생하지 않습니다:

1. **do-not-disrupt 어노테이션**: 노드나 Pod에 이 어노테이션이 있으면 해당 노드는 통합 대상에서 제외
2. **DaemonSet Pod만 있는 경우**: DaemonSet은 모든 노드에서 실행되므로 빈 노드로 취급
3. **consolidateAfter 미경과**: 조건 충족 후 지정된 시간이 지나야 통합 실행

```yaml
metadata:
  annotations:
    karpenter.sh/do-not-disrupt: "true"
```

</details>

### 5. Drift 감지가 트리거되는 상황은 무엇인가요?

- A) NodeClass 스펙이 변경되었을 때
- B) 새로운 AMI가 사용 가능할 때
- C) 보안 그룹이 변경되었을 때
- D) 위의 모든 경우

<details>
<summary>정답 보기</summary>

**정답: D) 위의 모든 경우**

**설명:**
Drift 감지는 노드의 현재 상태가 원하는 상태와 다를 때 트리거됩니다:

- **NodeClass 변경**: AMI 패밀리, 서브넷, 보안 그룹 등이 변경된 경우
- **새 AMI**: EKS 최적화 AMI가 업데이트된 경우
- **보안 그룹 변경**: 참조하는 보안 그룹이 수정된 경우

Drift가 감지되면 노드가 순차적으로 교체됩니다.

</details>

### 6. 노드 프로비저닝 속도를 최적화하기 위해 권장되는 AMI 패밀리는 무엇인가요?

- A) AL2023
- B) Bottlerocket
- C) Ubuntu
- D) Amazon Linux 2

<details>
<summary>정답 보기</summary>

**정답: B) Bottlerocket**

**설명:**
Bottlerocket은 컨테이너 전용으로 설계된 OS로, AL2023보다 빠른 부팅 시간을 제공합니다.

**부팅 시간 비교:**
- **AL2023**: 20-40초
- **Bottlerocket**: 15-25초

Bottlerocket의 추가 장점:
- 더 작은 공격 표면
- 불변 파일 시스템
- 자동 보안 업데이트

</details>
