# 운영 및 관리

> **지원 버전**: EKS 1.29+, EKS Auto Mode GA
> **마지막 업데이트**: 2025년 2월

< [이전: Spot 전략](./04-spot-strategies.md) | [목차](./README.md) | [다음: 비용 관리](./06-cost-management.md) >

---

이 문서에서는 EKS Auto Mode 클러스터의 Day-2 운영, 모니터링, 문제 해결, 그리고 보안 모범 사례를 다룹니다.

## Disruption Budget 설정

안전한 노드 교체를 위한 예산을 설정합니다.

```yaml
# disruption-budget.yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: production-pool
spec:
  template:
    spec:
      requirements:
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["m", "c", "r"]
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["on-demand"]
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 5m
    budgets:
      # 기본: 전체 노드의 10%만 동시 중단
      - nodes: "10%"

      # 업무 시간: 중단 최소화
      - nodes: "1"
        schedule: "0 9-18 * * mon-fri"  # 월-금 9-18시 (KST)
        duration: 9h

      # 주말: 더 적극적인 통합 허용
      - nodes: "30%"
        schedule: "0 0 * * sat-sun"
        duration: 48h

      # 긴급 유지보수 윈도우: 중단 금지
      - nodes: "0"
        schedule: "0 0 1 * *"  # 매월 1일
        duration: 24h
```

## 롤링 교체 전략

```yaml
# rolling-replacement-strategy.yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: rolling-replacement
spec:
  template:
    spec:
      requirements:
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["m"]
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
      # 노드 만료 시간
      expireAfter: 168h  # 7일
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 2m
    budgets:
      # 순차적 교체를 위해 동시 중단 노드 제한
      - nodes: "1"
```

## PodDisruptionBudget과의 연동

```yaml
# pdb-example.yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: web-app-pdb
spec:
  # 최소 가용 Pod 수
  minAvailable: 3
  # 또는 최대 비가용 Pod 수
  # maxUnavailable: 1
  selector:
    matchLabels:
      app: web-app
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
spec:
  replicas: 5
  selector:
    matchLabels:
      app: web-app
  template:
    metadata:
      labels:
        app: web-app
    spec:
      containers:
        - name: web
          image: nginx:latest
          resources:
            requests:
              cpu: 500m
              memory: 256Mi
      # 노드 교체 시 graceful shutdown
      terminationGracePeriodSeconds: 60
```

## Zone 장애 대응

```yaml
# multi-az-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: high-availability-app
spec:
  replicas: 6
  selector:
    matchLabels:
      app: ha-app
  template:
    metadata:
      labels:
        app: ha-app
    spec:
      # 가용 영역 분산
      topologySpreadConstraints:
        - maxSkew: 1
          topologyKey: topology.kubernetes.io/zone
          whenUnsatisfiable: DoNotSchedule
          labelSelector:
            matchLabels:
              app: ha-app
        # 노드 분산
        - maxSkew: 1
          topologyKey: kubernetes.io/hostname
          whenUnsatisfiable: ScheduleAnyway
          labelSelector:
            matchLabels:
              app: ha-app
      containers:
        - name: app
          image: my-app:latest
          resources:
            requests:
              cpu: 500m
              memory: 512Mi
---
# Zone별 최소 노드 보장을 위한 NodePool
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: multi-az-pool
spec:
  template:
    spec:
      requirements:
        - key: topology.kubernetes.io/zone
          operator: In
          values: ["ap-northeast-2a", "ap-northeast-2b", "ap-northeast-2c"]
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["m", "c"]
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
  # Zone당 최소 용량 보장
  limits:
    cpu: 1000
```

## CloudWatch 지표 모니터링

EKS Auto Mode는 다음 지표를 CloudWatch에 자동으로 전송합니다.

```bash
# CloudWatch 메트릭 네임스페이스
# - AWS/EKS
# - Karpenter

# 주요 지표
# - karpenter_nodes_total: 총 노드 수
# - karpenter_pods_pending: Pending Pod 수
# - karpenter_nodeclaims_created: 생성된 NodeClaim 수
# - karpenter_nodeclaims_terminated: 종료된 NodeClaim 수
```

### CloudWatch 대시보드 설정

```json
{
  "widgets": [
    {
      "type": "metric",
      "properties": {
        "title": "Auto Mode 노드 수",
        "metrics": [
          ["Karpenter", "karpenter_nodes_total", "cluster", "my-cluster"]
        ],
        "period": 60
      }
    },
    {
      "type": "metric",
      "properties": {
        "title": "Pending Pods",
        "metrics": [
          ["Karpenter", "karpenter_pods_pending", "cluster", "my-cluster"]
        ],
        "period": 60
      }
    },
    {
      "type": "metric",
      "properties": {
        "title": "노드 프로비저닝 시간",
        "metrics": [
          ["Karpenter", "karpenter_nodeclaims_startup_duration_seconds", "cluster", "my-cluster"]
        ],
        "stat": "p99",
        "period": 300
      }
    }
  ]
}
```

## kubectl 기반 진단

```bash
# NodePool 상태 확인
kubectl get nodepools
kubectl describe nodepool general-purpose

# NodeClaim 상태 확인 (프로비저닝 중인 노드)
kubectl get nodeclaims
kubectl describe nodeclaim <name>

# 노드 상태 및 레이블 확인
kubectl get nodes -o wide -L karpenter.sh/nodepool,karpenter.sh/capacity-type

# Pending Pod 확인
kubectl get pods -A --field-selector=status.phase=Pending

# 이벤트 확인
kubectl get events --sort-by='.lastTimestamp' | grep -E "karpenter|nodepool|nodeclaim"

# 노드 리소스 사용량
kubectl top nodes

# 노드별 Pod 분포
kubectl get pods -A -o wide | awk '{print $8}' | sort | uniq -c | sort -rn
```

## 일반적인 문제와 해결 방법

### 문제 1: Pod가 Pending 상태로 유지됨

```bash
# 원인 분석
kubectl describe pod <pending-pod>

# 일반적인 원인:
# 1. 리소스 요청이 너무 큼
# 2. NodePool 제한 초과
# 3. nodeSelector/affinity 조건 불일치
# 4. taint/toleration 불일치

# 해결: NodePool 제한 확인
kubectl get nodepool -o yaml | grep -A5 limits

# 해결: nodeSelector 조건 확인
kubectl get pod <pending-pod> -o yaml | grep -A10 nodeSelector
```

### 문제 2: 노드 프로비저닝 실패

```bash
# NodeClaim 상태 확인
kubectl describe nodeclaim <name>

# 이벤트에서 오류 메시지 확인
kubectl get events --field-selector reason=FailedProvisioning

# 일반적인 원인:
# 1. 인스턴스 용량 부족
# 2. 서브넷 IP 부족
# 3. IAM 권한 문제
# 4. 보안 그룹 설정 오류

# 해결: 더 다양한 인스턴스 타입 허용
# NodePool의 requirements를 확장
```

### 문제 3: 노드 Consolidation이 작동하지 않음

```bash
# Consolidation 상태 확인
kubectl get nodeclaims -o custom-columns=\
NAME:.metadata.name,\
NODEPOOL:.metadata.labels.karpenter\\.sh/nodepool,\
PHASE:.status.phase,\
AGE:.metadata.creationTimestamp

# PodDisruptionBudget 확인
kubectl get pdb -A

# 해결: PDB 조정 또는 budgets 설정 확인
```

### 문제 4: Spot 인터럽트 후 Pod 재스케줄 지연

```bash
# Spot 인터럽트 이벤트 확인
kubectl get events --sort-by='.lastTimestamp' | grep -i "spot\|interrupt"

# 해결: 빠른 재프로비저닝을 위한 설정
# 1. 다양한 인스턴스 타입 허용
# 2. consolidateAfter 시간 단축
# 3. Spot과 On-Demand 혼합 사용
```

## 보안 모범 사례

```yaml
# security-best-practices.yaml
apiVersion: eks.amazonaws.com/v1
kind: NodeClass
metadata:
  name: secure-nodeclass
spec:
  amiFamily: Bottlerocket  # 보안 강화 OS

  # IMDSv2 필수
  metadataOptions:
    httpEndpoint: enabled
    httpProtocolIPv6: disabled
    httpPutResponseHopLimit: 1  # Pod의 IMDS 접근 차단
    httpTokens: required

  # EBS 암호화
  blockDeviceMappings:
    - deviceName: /dev/xvda
      ebs:
        volumeSize: 100Gi
        volumeType: gp3
        encrypted: true
        kmsKeyId: arn:aws:kms:ap-northeast-2:123456789:key/xxx

  # 프라이빗 서브넷만 사용
  subnetSelectorTerms:
    - tags:
        kubernetes.io/role/internal-elb: "1"

  # 제한적인 보안 그룹
  securityGroupSelectorTerms:
    - tags:
        Type: worker-restricted
---
# Pod 보안 표준 적용
apiVersion: v1
kind: Namespace
metadata:
  name: secure-namespace
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/warn: restricted
```

## Day-2 운영 체크리스트

효과적인 Auto Mode 운영을 위한 일일/주간/월간 체크리스트입니다.

### 일일 체크리스트

| 항목 | 확인 명령어 | 정상 기준 |
|------|------------|----------|
| Pending Pod 확인 | `kubectl get pods -A --field-selector=status.phase=Pending` | 0개 (또는 일시적) |
| NodeClaim 상태 | `kubectl get nodeclaims` | 모두 Ready 상태 |
| 노드 리소스 사용량 | `kubectl top nodes` | CPU/메모리 < 80% |
| 최근 이벤트 확인 | `kubectl get events --sort-by='.lastTimestamp' -A` | 에러 없음 |

### 주간 체크리스트

| 항목 | 설명 |
|------|------|
| 비용 분석 | AWS Cost Explorer에서 EC2 비용 트렌드 확인 |
| Consolidation 효율 | 저사용률 노드 비율 확인 |
| Spot 인터럽트 빈도 | CloudWatch 메트릭에서 Spot 중단 이벤트 검토 |
| 노드 수명 분포 | 오래된 노드 비율 확인 (expireAfter 동작 검증) |

### 월간 체크리스트

| 항목 | 설명 |
|------|------|
| NodePool 설정 검토 | 요구사항 변화에 따른 설정 조정 |
| AMI 업데이트 확인 | 최신 AMI 적용 여부 확인 |
| 보안 패치 상태 | 노드 보안 업데이트 상태 검토 |
| 용량 계획 | limits 설정 적절성 검토 |

## 노드 교체 전략 비교

### Rolling vs Aggressive 교체

| 전략 | 설정 | 사용 시나리오 | 장점 | 단점 |
|------|------|--------------|------|------|
| **Rolling** | `budgets: nodes: "1"` | 프로덕션 환경 | 서비스 영향 최소화 | 교체 시간 김 |
| **Aggressive** | `budgets: nodes: "30%"` | 개발/테스트 환경 | 빠른 교체 | 순간적 용량 감소 |
| **Scheduled** | `schedule: "0 2 * * *"` | 비즈니스 비활성 시간 | 업무 영향 없음 | 유연성 제한 |

### 교체 전략 선택 가이드

```yaml
# 프로덕션 환경: 보수적 롤링 교체
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: production
spec:
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 10m
    budgets:
      - nodes: "1"
      - nodes: "0"
        schedule: "0 9-21 * * mon-fri"  # 업무 시간 중단 금지
        duration: 12h
---
# 개발 환경: 적극적 통합
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: development
spec:
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 1m
    budgets:
      - nodes: "50%"
```

## 가용 영역 장애 대응 패턴

### Multi-AZ Awareness 설정

```yaml
# multi-az-resilient.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: az-resilient-app
spec:
  replicas: 9  # 3 AZ x 3 replicas
  selector:
    matchLabels:
      app: az-resilient
  template:
    metadata:
      labels:
        app: az-resilient
    spec:
      topologySpreadConstraints:
        # AZ 균등 분배 (필수)
        - maxSkew: 1
          topologyKey: topology.kubernetes.io/zone
          whenUnsatisfiable: DoNotSchedule
          labelSelector:
            matchLabels:
              app: az-resilient
      affinity:
        podAntiAffinity:
          # 같은 노드에 배치 금지
          requiredDuringSchedulingIgnoredDuringExecution:
            - labelSelector:
                matchLabels:
                  app: az-resilient
              topologyKey: kubernetes.io/hostname
      containers:
        - name: app
          image: my-app:latest
```

### Capacity Reservation 활용

```yaml
# 특정 AZ에 용량 보장
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: reserved-capacity
spec:
  template:
    spec:
      requirements:
        - key: topology.kubernetes.io/zone
          operator: In
          values: ["ap-northeast-2a"]
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["on-demand"]
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
  limits:
    cpu: 200  # AZ당 최소 보장 용량
```

## 운영 자동화

### 노드 교체 알림 설정

```yaml
# CloudWatch 알람을 통한 노드 교체 알림
# AWS CLI로 생성
# aws cloudwatch put-metric-alarm \
#   --alarm-name "EKS-Auto-Mode-Node-Replacement" \
#   --metric-name karpenter_nodeclaims_terminated \
#   --namespace Karpenter \
#   --statistic Sum \
#   --period 300 \
#   --threshold 5 \
#   --comparison-operator GreaterThanThreshold \
#   --evaluation-periods 1 \
#   --alarm-actions arn:aws:sns:ap-northeast-2:123456789:alerts
```

### PDB 준수 모니터링

```bash
#!/bin/bash
# pdb-compliance-check.sh
# PDB 위반 상태 확인 스크립트

echo "=== PDB Compliance Check ==="
kubectl get pdb -A -o json | jq -r '
  .items[] |
  select(.status.disruptionsAllowed == 0) |
  "\(.metadata.namespace)/\(.metadata.name): No disruptions allowed (current: \(.status.currentHealthy)/\(.status.desiredHealthy))"
'
```

### 용량 모니터링 대시보드

```yaml
# Prometheus 알림 규칙
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: karpenter-alerts
spec:
  groups:
    - name: karpenter
      rules:
        - alert: HighPendingPods
          expr: karpenter_pods_pending > 10
          for: 5m
          labels:
            severity: warning
          annotations:
            summary: "많은 수의 Pending Pod 감지"
            description: "{{ $value }}개의 Pod가 5분 이상 Pending 상태입니다."

        - alert: NodeProvisioningFailed
          expr: increase(karpenter_nodeclaims_terminated{reason="ProvisioningFailed"}[10m]) > 0
          labels:
            severity: critical
          annotations:
            summary: "노드 프로비저닝 실패"
            description: "최근 10분간 노드 프로비저닝 실패가 발생했습니다."
```

## 운영 체크리스트 요약

| 영역 | 체크 항목 |
|------|----------|
| **설정** | NodePool limits 설정 완료 |
| | Disruption Budget 구성 |
| | NodeClass 보안 설정 검토 |
| **모니터링** | CloudWatch 대시보드 생성 |
| | 알람 설정 (Pending Pod, 프로비저닝 실패) |
| | 비용 모니터링 설정 |
| **가용성** | PodDisruptionBudget 설정 |
| | 멀티 AZ 분산 검증 |
| | Spot/On-Demand 혼합 비율 검토 |
| **비용** | Spot 인스턴스 비율 최적화 |
| | Consolidation 정책 검토 |
| | 리소스 요청/제한 적절성 검토 |

---

< [이전: Spot 전략](./04-spot-strategies.md) | [목차](./README.md) | [다음: 비용 관리](./06-cost-management.md) >
