# Spot 인스턴스 활용 전략

> **지원 버전**: EKS 1.29+, EKS Auto Mode GA
> **마지막 업데이트**: 2026년 2월 19일

< [이전: 스케일링 동작](./03-scaling-behavior.md) | [목차](./README.md) | [다음: 운영 및 관리](./05-operations.md) >

---

이 문서에서는 EKS Auto Mode에서 Spot 인스턴스를 효과적으로 활용하여 비용을 최적화하는 전략을 설명합니다.

## Spot vs On-Demand 혼합 전략

안정성과 비용 효율성을 모두 달성하기 위한 혼합 전략입니다.

```yaml
# spot-ondemand-mixed.yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: mixed-capacity
spec:
  template:
    spec:
      requirements:
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["m", "c", "r"]
        - key: karpenter.k8s.aws/instance-generation
          operator: Gt
          values: ["5"]
        # Spot과 On-Demand 모두 허용
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["spot", "on-demand"]
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 1m
---
# Pod에서 Spot 선호 설정
apiVersion: apps/v1
kind: Deployment
metadata:
  name: spot-friendly-app
spec:
  replicas: 10
  selector:
    matchLabels:
      app: spot-friendly
  template:
    metadata:
      labels:
        app: spot-friendly
    spec:
      # Spot 인스턴스 선호
      affinity:
        nodeAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
            - weight: 100
              preference:
                matchExpressions:
                  - key: karpenter.sh/capacity-type
                    operator: In
                    values: ["spot"]
      # 중요 워크로드는 On-Demand 필수
      # requiredDuringSchedulingIgnoredDuringExecution:
      #   nodeSelectorTerms:
      #     - matchExpressions:
      #         - key: karpenter.sh/capacity-type
      #           operator: In
      #           values: ["on-demand"]
      containers:
        - name: app
          image: my-app:latest
          resources:
            requests:
              cpu: 500m
              memory: 512Mi
```

## Spot 인스턴스 다양화

인터럽트 위험을 분산하기 위해 다양한 인스턴스 타입을 사용합니다.

```yaml
# diversified-spot.yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: diversified-spot
spec:
  template:
    spec:
      requirements:
        # 다양한 인스턴스 패밀리
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["m", "c", "r", "i", "d"]
        # 다양한 세대
        - key: karpenter.k8s.aws/instance-generation
          operator: In
          values: ["5", "6", "7"]
        # 다양한 크기
        - key: karpenter.k8s.aws/instance-size
          operator: In
          values: ["large", "xlarge", "2xlarge"]
        # 다양한 아키텍처
        - key: kubernetes.io/arch
          operator: In
          values: ["amd64", "arm64"]
        # Spot만 사용
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["spot"]
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
  # Spot 인터럽트 시 빠른 재프로비저닝
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30s
```

## Spot 인터럽트 대응

```yaml
# spot-disruption-budget.yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: spot-with-disruption-budget
spec:
  template:
    spec:
      requirements:
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["spot"]
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["m", "c", "r"]
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 1m
    # 동시 중단 노드 수 제한
    budgets:
      - nodes: "10%"    # 전체 노드의 10%만 동시 중단
      - nodes: "3"      # 또는 최대 3개 노드
      # 비즈니스 시간에는 중단 최소화
      - nodes: "0"
        schedule: "0 9-18 * * mon-fri"  # 평일 9-18시
        duration: 9h
---
# Pod에 Spot 인터럽트 대응 설정
apiVersion: apps/v1
kind: Deployment
metadata:
  name: spot-aware-app
spec:
  replicas: 5
  selector:
    matchLabels:
      app: spot-aware
  template:
    metadata:
      labels:
        app: spot-aware
    spec:
      # Graceful shutdown 시간 확보
      terminationGracePeriodSeconds: 120
      containers:
        - name: app
          image: my-app:latest
          lifecycle:
            preStop:
              exec:
                command: ["/bin/sh", "-c", "sleep 90"]
      # 여러 AZ에 분산
      topologySpreadConstraints:
        - maxSkew: 1
          topologyKey: topology.kubernetes.io/zone
          whenUnsatisfiable: DoNotSchedule
          labelSelector:
            matchLabels:
              app: spot-aware
```

## 워크로드별 Spot 적합성

| 워크로드 유형 | Spot 적합성 | 권장 설정 |
|--------------|------------|----------|
| 상태 없는 웹 서비스 | 높음 | Spot 우선, On-Demand 폴백 |
| 배치 처리 | 매우 높음 | Spot 전용 |
| CI/CD 파이프라인 | 높음 | Spot 전용 |
| 개발/테스트 환경 | 매우 높음 | Spot 전용 |
| 데이터베이스 | 낮음 | On-Demand 필수 |
| 실시간 스트리밍 | 낮음 | On-Demand 필수 |
| GPU/ML 추론 | 중간 | 혼합 (중요도에 따라) |

## 비용 절감 사례

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       Spot 인스턴스 비용 절감 사례                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  워크로드 유형          On-Demand 비용    Spot 비용      절감률              │
│  ─────────────────────────────────────────────────────────────────────────  │
│  배치 처리               $1,000/월        $300/월        70%                │
│  개발/테스트 환경        $2,000/월        $500/월        75%                │
│  CI/CD 파이프라인        $500/월          $150/월        70%                │
│  비중요 API 서버         $3,000/월        $1,200/월      60%                │
│                                                                              │
│  ※ Spot 인스턴스 가격은 수요/공급에 따라 변동됩니다                           │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Spot 인터럽트 핸들링 모범 사례

### 1. 애플리케이션 레벨 대응

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: spot-resilient-app
spec:
  replicas: 6
  selector:
    matchLabels:
      app: spot-resilient
  template:
    metadata:
      labels:
        app: spot-resilient
    spec:
      terminationGracePeriodSeconds: 120
      containers:
        - name: app
          image: my-app:latest
          env:
            # Spot 인터럽트 감지를 위한 환경 변수
            - name: SPOT_INSTANCE
              valueFrom:
                fieldRef:
                  fieldPath: spec.nodeName
          lifecycle:
            preStop:
              exec:
                command:
                  - /bin/sh
                  - -c
                  - |
                    # 진행 중인 작업 완료
                    /app/graceful-shutdown.sh
                    # 헬스체크 실패 유도
                    rm /tmp/healthy
                    sleep 90
          readinessProbe:
            exec:
              command: ["test", "-f", "/tmp/healthy"]
            initialDelaySeconds: 5
            periodSeconds: 5
```

### 2. 클러스터 레벨 대응

```yaml
# Node Termination Handler DaemonSet (AWS 제공)
# Auto Mode에서는 기본 제공되지만, 추가 설정 가능
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: aws-node-termination-handler
  namespace: kube-system
spec:
  selector:
    matchLabels:
      app: aws-node-termination-handler
  template:
    spec:
      nodeSelector:
        karpenter.sh/capacity-type: spot
      containers:
        - name: handler
          image: public.ecr.aws/aws-ec2/aws-node-termination-handler:v1.19.0
          env:
            - name: ENABLE_SPOT_INTERRUPTION_DRAINING
              value: "true"
            - name: ENABLE_REBALANCE_DRAINING
              value: "true"
```

---

< [이전: 스케일링 동작](./03-scaling-behavior.md) | [목차](./README.md) | [다음: 운영 및 관리](./05-operations.md) >
