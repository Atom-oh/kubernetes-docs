# 관리형 노드 그룹에서 Auto Mode로 마이그레이션

> **지원 버전**: EKS 1.29+, EKS Auto Mode GA
> **마지막 업데이트**: 2025년 2월

< [이전: 워크로드 최적화](./08-workload-optimization.md) | [목차](./README.md) | [다음: 목차](./README.md) >

---

이 문서에서는 기존 관리형 노드 그룹에서 EKS Auto Mode로 안전하게 마이그레이션하는 방법을 설명합니다.

## 마이그레이션 단계

```mermaid
flowchart TD
    A[1. 현재 상태 분석] --> B[2. Auto Mode 활성화]
    B --> C[3. NodePool 구성]
    C --> D[4. 워크로드 마이그레이션]
    D --> E[5. 기존 노드 그룹 축소]
    E --> F[6. 기존 노드 그룹 삭제]
    F --> G[7. 검증 및 최적화]

    style A fill:#e3f2fd
    style B fill:#e8f5e9
    style C fill:#fff3e0
    style D fill:#fce4ec
    style E fill:#f3e5f5
    style F fill:#ffebee
    style G fill:#e0f7fa
```

## 1단계: 현재 상태 분석

```bash
# 현재 노드 그룹 확인
eksctl get nodegroup --cluster my-cluster

# 노드 리소스 사용량 분석
kubectl top nodes

# 워크로드 분포 확인
kubectl get pods -A -o wide | awk '{print $8}' | sort | uniq -c

# 현재 인스턴스 타입별 노드 수
kubectl get nodes -o custom-columns=\
NAME:.metadata.name,\
TYPE:.metadata.labels.node\\.kubernetes\\.io/instance-type,\
ZONE:.metadata.labels.topology\\.kubernetes\\.io/zone
```

## 2단계: Auto Mode 활성화

```bash
# Auto Mode 활성화
aws eks update-cluster-config \
    --name my-cluster \
    --compute-config enabled=true,nodePools=general-purpose,nodePools=system

# 활성화 상태 확인
aws eks describe-cluster --name my-cluster \
    --query 'cluster.computeConfig'
```

## 3단계: 커스텀 NodePool 구성

```yaml
# custom-nodepools.yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: migrated-workloads
spec:
  template:
    metadata:
      labels:
        migration: auto-mode
    spec:
      requirements:
        # 기존 노드 그룹과 유사한 인스턴스 타입
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["m", "c", "r"]
        - key: karpenter.k8s.aws/instance-size
          operator: In
          values: ["large", "xlarge", "2xlarge"]
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["on-demand"]
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
```

## 4단계: 워크로드 마이그레이션

```bash
# 기존 노드에 cordon 적용 (새 Pod 스케줄 방지)
kubectl cordon -l eks.amazonaws.com/nodegroup=old-nodegroup

# 점진적으로 Pod drain
for node in $(kubectl get nodes -l eks.amazonaws.com/nodegroup=old-nodegroup -o name); do
    kubectl drain $node --ignore-daemonsets --delete-emptydir-data
    sleep 60  # 각 노드 사이에 대기 시간
done
```

## 5단계: 기존 노드 그룹 축소

```bash
# 노드 그룹 스케일 다운
eksctl scale nodegroup \
    --cluster my-cluster \
    --name old-nodegroup \
    --nodes 0 \
    --nodes-min 0
```

## 6단계: 기존 노드 그룹 삭제

```bash
# 노드 그룹 삭제
eksctl delete nodegroup \
    --cluster my-cluster \
    --name old-nodegroup

# 삭제 확인
eksctl get nodegroup --cluster my-cluster
```

## 공존 기간 운영 방법

마이그레이션 중 기존 노드 그룹과 Auto Mode가 공존할 수 있습니다.

```yaml
# coexistence-config.yaml
# 기존 노드 그룹 워크로드
apiVersion: apps/v1
kind: Deployment
metadata:
  name: legacy-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: legacy-app
  template:
    metadata:
      labels:
        app: legacy-app
    spec:
      # 기존 노드 그룹에 고정
      nodeSelector:
        eks.amazonaws.com/nodegroup: old-nodegroup
      containers:
        - name: app
          image: legacy-app:latest
---
# Auto Mode 워크로드
apiVersion: apps/v1
kind: Deployment
metadata:
  name: new-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: new-app
  template:
    metadata:
      labels:
        app: new-app
    spec:
      # Auto Mode 노드 선호
      affinity:
        nodeAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
            - weight: 100
              preference:
                matchExpressions:
                  - key: karpenter.sh/nodepool
                    operator: Exists
      containers:
        - name: app
          image: new-app:latest
```

## 주의 사항

| 항목 | 주의 사항 |
|------|----------|
| AMI 호환성 | Auto Mode는 AL2023 또는 Bottlerocket만 지원 |
| 사용자 데이터 | 기존 부트스트랩 스크립트 호환성 확인 필요 |
| IAM 역할 | Auto Mode용 IAM 역할 자동 생성 |
| 보안 그룹 | NodeClass에서 재설정 필요 |
| 태그 | 기존 태그 정책을 NodeClass에 반영 |
| 모니터링 | 새로운 메트릭 수집 설정 필요 |

## 마이그레이션 체크리스트

### 사전 확인

- [ ] EKS 클러스터 버전 1.29 이상 확인
- [ ] 현재 워크로드 인벤토리 작성
- [ ] 리소스 사용량 패턴 분석
- [ ] 기존 nodeSelector/affinity 설정 검토
- [ ] PodDisruptionBudget 설정 확인

### 마이그레이션 중

- [ ] Auto Mode 활성화
- [ ] 기본 NodePool 생성 확인
- [ ] 커스텀 NodePool 구성
- [ ] 테스트 워크로드로 검증
- [ ] 점진적 워크로드 마이그레이션
- [ ] 기존 노드 그룹 축소

### 마이그레이션 후

- [ ] 모든 워크로드 정상 동작 확인
- [ ] 모니터링 대시보드 업데이트
- [ ] 알람 설정 조정
- [ ] 비용 최적화 검토
- [ ] 문서화 업데이트

## 롤백 계획

문제 발생 시 롤백 절차:

```bash
# 1. Auto Mode 노드에서 워크로드 퇴거
kubectl cordon -l karpenter.sh/nodepool

# 2. 기존 노드 그룹 재활성화
eksctl scale nodegroup \
    --cluster my-cluster \
    --name old-nodegroup \
    --nodes 3 \
    --nodes-min 1

# 3. 워크로드를 기존 노드로 복원
kubectl drain -l karpenter.sh/nodepool --ignore-daemonsets

# 4. Auto Mode 비활성화 (필요시)
aws eks update-cluster-config \
    --name my-cluster \
    --compute-config enabled=false
```

---

< [이전: 워크로드 최적화](./08-workload-optimization.md) | [목차](./README.md) | [다음: 목차](./README.md) >
