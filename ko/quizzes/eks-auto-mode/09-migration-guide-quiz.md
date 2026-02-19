# EKS Auto Mode 마이그레이션 가이드 퀴즈

> **관련 문서**: [마이그레이션 가이드](../../eks-auto-mode/09-migration-guide.md)

## 객관식 문제

### 1. 관리형 노드 그룹에서 Auto Mode로 마이그레이션 시 첫 번째 단계는 무엇인가요?

- A) 기존 노드 그룹 즉시 삭제
- B) 현재 상태 분석 (노드 리소스 사용량, 워크로드 분포 확인)
- C) Auto Mode NodePool 생성
- D) 모든 Pod drain

<details>
<summary>정답 보기</summary>

**정답: B) 현재 상태 분석 (노드 리소스 사용량, 워크로드 분포 확인)**

**설명:**
마이그레이션의 첫 단계는 현재 환경을 철저히 분석하는 것입니다.

**마이그레이션 단계:**
1. **현재 상태 분석** - 노드 그룹, 리소스 사용량, 워크로드 분포 확인
2. Auto Mode 활성화
3. NodePool 구성
4. 워크로드 마이그레이션
5. 기존 노드 그룹 축소
6. 기존 노드 그룹 삭제
7. 검증 및 최적화

```bash
# 현재 노드 그룹 확인
eksctl get nodegroup --cluster my-cluster

# 노드 리소스 사용량 분석
kubectl top nodes

# 워크로드 분포 확인
kubectl get pods -A -o wide | awk '{print $8}' | sort | uniq -c
```

</details>

### 2. 마이그레이션 중 기존 노드 그룹과 Auto Mode를 공존시키는 방법은?

- A) 불가능하므로 순차적으로만 가능
- B) nodeSelector로 워크로드 분리
- C) 별도 클러스터 필요
- D) AWS Support 티켓 필요

<details>
<summary>정답 보기</summary>

**정답: B) nodeSelector로 워크로드 분리**

**설명:**
공존 기간 동안 nodeSelector와 affinity를 사용하여 워크로드를 분리합니다.

```yaml
# 기존 노드 그룹에 고정된 워크로드
apiVersion: apps/v1
kind: Deployment
metadata:
  name: legacy-critical-app
spec:
  template:
    spec:
      nodeSelector:
        eks.amazonaws.com/nodegroup: old-nodegroup

---
# Auto Mode로 이전 가능한 워크로드
apiVersion: apps/v1
kind: Deployment
metadata:
  name: migrated-app
spec:
  template:
    spec:
      affinity:
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
              - matchExpressions:
                  - key: karpenter.sh/nodepool
                    operator: Exists
```

</details>

### 3. 점진적 워크로드 이전 순서로 권장되는 것은?

- A) 프로덕션 -> 스테이징 -> 개발
- B) 개발 -> 스테이징 -> 프로덕션 (비중요 워크로드부터)
- C) 모든 워크로드 동시 이전
- D) 랜덤 순서

<details>
<summary>정답 보기</summary>

**정답: B) 개발 -> 스테이징 -> 프로덕션 (비중요 워크로드부터)**

**설명:**
점진적 마이그레이션으로 위험을 최소화합니다.

```yaml
# 1단계: 비중요 워크로드 이전
apiVersion: apps/v1
kind: Deployment
metadata:
  name: dev-app
spec:
  template:
    spec:
      affinity:
        nodeAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
            - weight: 100
              preference:
                matchExpressions:
                  - key: node-type
                    operator: In
                    values: ["auto-mode"]
```

**이전 순서:**
1. 개발 환경 워크로드
2. 스테이징 워크로드
3. 프로덕션 비중요 워크로드
4. 프로덕션 중요 워크로드

</details>

### 4. 롤백이 필요할 때 수행해야 하는 단계 순서는?

- A) 클러스터 삭제 후 재생성
- B) NodePool 삭제 -> 기존 노드 그룹 스케일업 -> 워크로드 이전
- C) AWS Support 문의
- D) Auto Mode만 비활성화

<details>
<summary>정답 보기</summary>

**정답: B) NodePool 삭제 -> 기존 노드 그룹 스케일업 -> 워크로드 이전**

**설명:**
롤백은 역순으로 진행합니다.

```bash
#!/bin/bash
# rollback.sh

# 1. Auto Mode NodePool 비활성화
kubectl delete nodepool migration-pool

# 2. 기존 노드 그룹 스케일 업
eksctl scale nodegroup \
    --cluster my-cluster \
    --name old-nodegroup \
    --nodes 10 \
    --nodes-min 3

# 3. 워크로드를 기존 노드로 이전
kubectl patch deployment migrated-app -p '
{
  "spec": {
    "template": {
      "spec": {
        "nodeSelector": {
          "eks.amazonaws.com/nodegroup": "old-nodegroup"
        },
        "affinity": null
      }
    }
  }
}'

# 4. Auto Mode Pod drain
for node in $(kubectl get nodes -l karpenter.sh/nodepool=migration-pool -o name); do
    kubectl drain $node --ignore-daemonsets --delete-emptydir-data
done
```

</details>

### 5. 기존 노드 그룹을 단계적으로 축소할 때 권장되는 방법은?

- A) 즉시 0으로 축소
- B) 50%씩 단계적 축소 후 안정화 확인
- C) 1개씩만 축소
- D) 모든 노드 동시에 drain

<details>
<summary>정답 보기</summary>

**정답: B) 50%씩 단계적 축소 후 안정화 확인**

**설명:**
점진적 축소로 서비스 영향을 최소화합니다.

```bash
#!/bin/bash
CLUSTER="my-cluster"
NODEGROUP="old-nodegroup"
CURRENT_SIZE=$(eksctl get nodegroup --cluster $CLUSTER --name $NODEGROUP -o json | jq -r '.[0].DesiredCapacity')

# 50%씩 축소
while [ $CURRENT_SIZE -gt 0 ]; do
    NEW_SIZE=$((CURRENT_SIZE / 2))
    if [ $NEW_SIZE -lt 1 ]; then
        NEW_SIZE=0
    fi

    echo "Scaling from $CURRENT_SIZE to $NEW_SIZE"
    eksctl scale nodegroup --cluster $CLUSTER --name $NODEGROUP \
        --nodes $NEW_SIZE --nodes-min 0

    # 안정화 대기
    sleep 300

    # 워크로드 상태 확인
    kubectl get pods -A --field-selector=status.phase=Pending

    CURRENT_SIZE=$NEW_SIZE
done
```

</details>

### 6. 마이그레이션 중 모니터링해야 할 핵심 지표가 아닌 것은?

- A) Pending Pod 수
- B) 노드 프로비저닝 시간
- C) EC2 인스턴스 비용
- D) 워크로드 가용성

<details>
<summary>정답 보기</summary>

**정답: C) EC2 인스턴스 비용**

**설명:**
마이그레이션 중에는 서비스 안정성이 최우선이므로 다음 지표를 모니터링합니다.

| 지표 | 정상 범위 | 알람 조건 |
|------|----------|----------|
| Pending Pod 수 | 0-5 | > 10 for 5분 |
| 노드 프로비저닝 시간 | < 90초 | > 120초 |
| 워크로드 가용성 | > 99.9% | < 99.5% |
| API 응답 시간 | < 200ms | > 500ms |

비용은 마이그레이션 완료 후 최적화 단계에서 확인합니다.

```bash
# 실시간 모니터링
watch -n 5 'echo "=== Pending Pods ===" && \
kubectl get pods -A --field-selector=status.phase=Pending && \
echo "=== Node Status ===" && kubectl get nodes -o wide'
```

</details>

### 7. 마이그레이션 완료 후 검증해야 할 항목이 아닌 것은?

- A) 모든 워크로드 정상 실행 확인
- B) Auto Mode 노드에서 Pod 분포 확인
- C) 기존 노드 그룹 완전 삭제
- D) NodePool 상태 확인

<details>
<summary>정답 보기</summary>

**정답: C) 기존 노드 그룹 완전 삭제**

**설명:**
마이그레이션 검증 시점에서는 기존 노드 그룹을 유지하여 롤백 옵션을 보존합니다. 삭제는 안정성 확인 후 진행합니다.

**검증 체크리스트:**
1. 모든 Pod Running 상태 확인
2. Auto Mode 노드에 워크로드 분포 확인
3. NodePool 및 NodeClaim 정상 상태
4. 애플리케이션 성능 테스트
5. 로그 및 메트릭 정상 수집
6. **일정 기간(1-2주) 안정성 확인 후 기존 노드 그룹 삭제**

</details>

### 8. Karpenter를 직접 사용하던 클러스터에서 Auto Mode로 전환 시 주의사항은?

- A) 직접 전환 가능
- B) 기존 Karpenter 리소스와 충돌 가능, Karpenter 제거 후 전환
- C) 동시 운영 권장
- D) 추가 비용 발생

<details>
<summary>정답 보기</summary>

**정답: B) 기존 Karpenter 리소스와 충돌 가능, Karpenter 제거 후 전환**

**설명:**
Auto Mode는 내부적으로 Karpenter를 사용하므로, 기존 self-managed Karpenter와 충돌할 수 있습니다.

**전환 절차:**
1. 기존 Karpenter NodePool 구성 백업
2. Karpenter가 관리하는 워크로드를 관리형 노드 그룹으로 임시 이전
3. self-managed Karpenter 제거
4. Auto Mode 활성화
5. Auto Mode NodePool 구성 (백업 참고)
6. 워크로드 이전

```bash
# Karpenter 제거 전 확인
kubectl get nodepools
kubectl get nodeclaims
kubectl get nodes -l karpenter.sh/nodepool

# Karpenter 제거
helm uninstall karpenter -n karpenter
kubectl delete namespace karpenter
```

</details>
