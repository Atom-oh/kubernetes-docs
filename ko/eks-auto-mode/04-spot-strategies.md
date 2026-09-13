# Spot 인스턴스 활용 전략

> **지원 버전**: EKS Auto Mode GA; 예제 기준 EKS 1.36
> **마지막 업데이트**: 2026년 9월 12일

Spot은 중단·용량 불확실성을 감수하는 대신 EC2 비용을 줄일 수 있는 선택지입니다. 혼합 용량, 다양화와 복제본은 복원력에 도움이 될 수 있지만 각각만으로 가용성이나 절감액을 보장하지는 않습니다. 앞 장에서 확인한 계정·컨텍스트와 NodeClass를 사용하세요.

Manifest는 로컬 스키마로 확인한 실습 예제이며 프로덕션 장애조치 시험 결과가 아닙니다. 관계없는 워크로드의 우발적 배치를 줄이도록 `spot-lab` taint/toleration과 명시적인 풀 선택을 사용합니다. Taint가 테넌트 보안 경계는 아닙니다. 적용 전에 복제본 수와 리소스 제한을 검토하세요. 예제도 과금되는 노드를 생성할 수 있습니다. 이번 감사에서는 Spot 인스턴스 생성이나 고객 청구·EC2 Spot Price History API 조회를 실행하지 않았습니다.

## 혼합 용량과 명시적인 기본 용량

다음 풀은 Spot과 On-Demand를 모두 허용합니다. 적합한 한 풀 안에서는 Auto Mode가 허용된 용량 유형을 우선순위로 선택하며, 둘 다 허용되고 사용 가능하면 On-Demand보다 Spot을 우선합니다. `reserved`도 허용하고 적합한 예약 용량이 있으면 그 우선순위가 더 높습니다. 배열 순서나 NodePool weight가 Spot 비율을 지정하지는 않습니다.

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: spot-lab
---
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: mixed-capacity
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
      - key: eks.amazonaws.com/instance-generation
        operator: Gt
        values:
        - '5'
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
      - key: spot-lab
        value: 'true'
        effect: NoSchedule
    metadata:
      labels:
        capacity-example: spot-lab
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 1m
  limits:
    cpu: '100'
    memory: 400Gi
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: spot-friendly-app
  namespace: spot-lab
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
      containers:
      - name: app
        image: nginx:1.30.4
        resources:
          requests:
            cpu: 100m
            memory: 64Mi
          limits:
            cpu: 500m
            memory: 128Mi
        ports:
        - containerPort: 80
        readinessProbe:
          httpGet:
            path: /
            port: 80
          periodSeconds: 5
      automountServiceAccountToken: false
      nodeSelector:
        karpenter.sh/nodepool: mixed-capacity
      tolerations:
      - key: spot-lab
        operator: Equal
        value: 'true'
        effect: NoSchedule
```

Pod의 preferred affinity는 선호이지 필수 조건이나 용량 예약이 아닙니다. 즉시 On-Demand로 전환되거나 정해진 비율을 유지하거나 중단 시간 안에 대체 용량이 준비됨을 보장하지 않습니다. 기존 용량, 제약, 할당량과 실제 가용성이 중요합니다.

별도의 기본 용량 Deployment가 반드시 On-Demand를 사용해야 한다면 Pod template의 Spot 선호를 아래와 같은 필수 선택으로 바꾸고 실습 toleration을 유지하세요. 적절한 기본 복제본을 계속 실행해야 합니다. 풀에 On-Demand를 허용하는 것만으로 여유 용량이 미리 준비되지는 않습니다.

```yaml
nodeSelector:
  karpenter.sh/nodepool: mixed-capacity
  karpenter.sh/capacity-type: on-demand
tolerations:
- key: spot-lab
  operator: Equal
  value: 'true'
  effect: NoSchedule
```

이 selector는 의도적으로 `on-demand`를 요구하며 `reserved` 용량은 포함하지 않습니다. 나중에 capacity reservation을 사용한다면 label과 예약 구성을 다시 검토하세요. On-Demand 자체도 데이터 내구성이나 용량 가용성 보장은 아닙니다.

## 호환되는 용량 다양화

Spot 용량 풀은 인스턴스 유형과 AZ에 연결됩니다. 호환되는 유형·AZ가 많으면 선택지가 늘어나지만 중단이 서로 독립적이 되거나 아키텍처 두 개만으로 용량이 정확히 두 배가 되지는 않습니다.

예제는 세대 상한을 7로 고정하지 않고 5세대 이상을 허용합니다. 제약을 넓히기 전에 이미지, 바이너리, 스토리지와 성능 호환성을 확인하세요.

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: diversified-spot
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
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30s
  limits:
    cpu: '100'
    memory: 400Gi
```

`consolidationPolicy`와 `consolidateAfter`는 통합 정책이며 EC2 interruption에 반응하는 시간을 정하지 않습니다. 여러 아키텍처에는 호환되는 multi-architecture 이미지와 의존성이 필요합니다. 세대·크기를 늘려도 워크로드에 적합하고 선택한 AZ에서 가용해야 의미가 있습니다.

## 자발적 Budget과 EC2 Interruption 구분

Auto Mode는 Spot interruption을 기본 처리하며 이를 위해 추가 Node Termination Handler나 사용자 관리 SQS queue가 필요하지 않습니다. 이전의 잘못된 NTH DaemonSet을 Auto Mode 노드에 배포하지 마세요. 다른 노드 유형이 공존한다면 대상과 권한을 구분해 그 노드의 interruption 처리를 구성합니다.

NodePool disruption budget은 consolidation·drift 같은 자발적 중단을 제한합니다. EC2의 Spot 회수나 경고 시간을 바꾸거나 대체 용량 준비를 보장하지 않습니다.

적용되는 budget을 함께 평가해 가장 제한적인 허용량을 사용합니다. 아래 `10%`와 `3`은 대안 관계가 아닙니다. 백분율은 올림 계산하며 삭제 중·NotReady 노드도 허용량을 소모합니다. 그 외 모두 정상인 노드가 20개라면 zero-budget 구간 밖에서 두 항목은 새 자발적 중단을 최대 2개 허용합니다.

예제는 **서울(KST) 월–금 09:00–18:00**을 보호하도록 **UTC 00:00**에 9시간 창을 시작합니다. Karpenter budget schedule은 UTC입니다. 이전 `0 9-18 * * mon-fri`는 매시간 9시간 창을 추가해 18시에 끝나는 대신 다음 날까지 중첩됐습니다.

```yaml
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
        values:
        - spot
      - key: eks.amazonaws.com/instance-category
        operator: In
        values:
        - m
        - c
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
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 1m
    budgets:
    - nodes: 10%
    - nodes: '3'
    - nodes: '0'
      schedule: 0 0 * * mon-fri
      duration: 9h
  limits:
    cpu: '100'
    memory: 400Gi
```

운영 달력에 맞게 조정하세요. 다른 시간대와 일광절약시간은 의도적으로 변환해야 합니다. Zero voluntary budget은 필요한 유지보수를 늦출 수 있으며 비자발적 interruption을 막지는 못합니다.

## 실제 남은 시간 안의 Graceful Shutdown

EC2는 일반적으로 stop/terminate interruption 전에 2분 경고를 보내지만 best effort입니다. Hibernation은 즉시 시작하는 다른 동작을 가집니다. 모든 Pod에 2분이 보장된다고 해석하지 마세요. 감지, 축출, 애플리케이션 처리와 라우팅 변경이 시간을 사용하며 장애로 경고를 처리하지 못할 수도 있습니다.

`terminationGracePeriodSeconds`는 Kubernetes 종료 예산이며 EC2 회수 기한을 늘리지 않습니다. `preStop`은 그 예산 안에서 일반 종료 신호보다 먼저 실행됩니다. 무조건 `sleep 90`을 실행하면 120초 예산 대부분을 소비하며 애플리케이션 종료나 체크포인트를 구현하지도 않습니다.

nginx용 다음 예제는 즉시 graceful quit를 시작하고 실제 HTTP readiness probe와 정확한 node name을 사용합니다. 다른 애플리케이션에는 자체 종료 신호 처리, readiness 전환, 진행 중 작업 완료와 durable checkpoint를 구현·검증해야 합니다. 60초는 예시 상한 예산이지 실제로 모두 주어진다는 보장이 아닙니다.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: spot-aware-app
  namespace: spot-lab
spec:
  replicas: 6
  selector:
    matchLabels:
      app: spot-aware
  template:
    metadata:
      labels:
        app: spot-aware
    spec:
      terminationGracePeriodSeconds: 60
      containers:
      - name: app
        image: nginx:1.30.4
        lifecycle:
          preStop:
            exec:
              command:
              - nginx
              - -s
              - quit
        resources:
          requests:
            cpu: 100m
            memory: 64Mi
          limits:
            cpu: 500m
            memory: 128Mi
        ports:
        - containerPort: 80
        readinessProbe:
          httpGet:
            path: /
            port: 80
          periodSeconds: 5
        env:
        - name: NODE_NAME
          valueFrom:
            fieldRef:
              fieldPath: spec.nodeName
      topologySpreadConstraints:
      - maxSkew: 1
        topologyKey: topology.kubernetes.io/zone
        whenUnsatisfiable: DoNotSchedule
        labelSelector:
          matchLabels:
            app: spot-aware
        minDomains: 2
        nodeAffinityPolicy: Honor
        nodeTaintsPolicy: Honor
      automountServiceAccountToken: false
      nodeSelector:
        karpenter.sh/nodepool: spot-with-disruption-budget
      tolerations:
      - key: spot-lab
        operator: Equal
        value: 'true'
        effect: NoSchedule
---
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: spot-aware-budget
  namespace: spot-lab
spec:
  maxUnavailable: 1
  selector:
    matchLabels:
      app: spot-aware
```

`NODE_NAME`은 Downward API로 노드 이름을 받습니다. Spot 여부를 나타내는 boolean이 아니며 Pod용 Downward API가 node label을 자동으로 노출하지도 않습니다. 애플리케이션은 보통 구매 옵션과 관계없이 graceful termination을 처리해야 합니다. 용량 유형이 필요하면 노드 IMDS 자격 증명에 의존하기보다 검토된 방법으로 확인한 metadata를 전달하세요.

예제는 적합한 AZ domain 2개를 요구하고 `maxSkew: 1`로 복제본 6개를 분산합니다. 엄격한 `DoNotSchedule` 제약은 AZ·용량 부족 시 Pod를 Pending에 남길 수 있으며 용량을 만들어내지 않습니다. 세 domain을 요구하기 전에 이 tradeoff를 검토하세요. AZ 분산이 AZ 안의 인스턴스 유형까지 분산한다는 뜻도 아닙니다.

PDB는 자발적인 애플리케이션 축출을 제한할 뿐 EC2가 회수하는 VM을 보존하지 않습니다. 복제본 수를 늘리는 효과도 트래픽 처리, 적합한 용량, topology와 장애 복구를 함께 검증해야 얻을 수 있습니다.

## 워크로드 적합성

| 워크로드 | 시작점과 필수 검증 |
|----------|------------------|
| Stateless 웹·추론 | 중단을 허용하는 Spot 용량과 명시적인 중요 기본 용량, 지연·장애조치 검증 |
| Batch·CI | 재시도 가능하고 idempotent한 작업에 적합할 수 있으나 마감 시간이 엄격하면 다른 용량도 필요 |
| 긴 학습·상태 처리 작업 | 마지막 순간 checkpoint 보장 대신 주기적 durable checkpoint와 resume/replay 검증 |
| 단일 DB·중요 quorum | 명시적인 복구 구조 없이 중단에 노출하지 않음. On-Demand만으로 로컬 데이터를 보호하지는 않음 |
| 개발·테스트 | 비용 제한과 용량 부족 허용. Spot-only 작업이 항상 시작한다고 가정하지 않음 |

중요한 상태의 유일한 복사본을 일회성 노드 로컬 스토리지에 두지 마세요. 구매 옵션과 별도로 durable storage, backup과 restore를 검증합니다.

## 현재 견적이 아닌 과거 비용 예시

이전 가이드에는 리전, 인스턴스 시간 구성, 과금 범위나 재현 가능한 측정 없이 다음 월 비용이 제시됐습니다. **검증되지 않은 교육용 예시**로 보존하며 현재 EKS 버전에서 측정한 절감액이 아닙니다.

| 예시 | 이전 On-Demand 금액 | 이전 Spot 금액 | 산술상 감소율 |
|------|---------------------|----------------|---------------|
| Batch | $1,000/월 | $300/월 | 70% |
| 개발·테스트 | $2,000/월 | $500/월 | 75% |
| CI/CD | $500/월 | $150/월 | 70% |
| 비중요 API | $3,000/월 | $1,200/월 | 60% |

AWS는 EC2 Spot 가격을 최대 90% 할인으로 안내하지만 최소 할인율이나 전체 워크로드 절감 보장은 아닙니다. Spot Instance Advisor는 지난 한 달의 interruption·절감 데이터를 AZ 평균으로 요약하며 지연될 수 있습니다. 계산에는 현재 AZ별 Spot Price History나 실제 청구 데이터를 사용하세요. 과거 interruption 구간은 다음 작업의 예측값이 아닙니다.

같은 유효 작업량, 리전, 기간과 가용성 목표를 비교합니다.

```text
Baseline total =
  sum(baseline On-Demand node-hours[type] * On-Demand rate[type])
  + other baseline costs

Actual total =
  sum(billed Spot node-hours[type, AZ] * time-weighted Spot rate[type, AZ])
  + sum(billed On-Demand fallback node-hours[type] * On-Demand rate[type])
  + other actual costs

Net savings = Baseline total - Actual total
```

시간당 단가에는 시간을 같은 단위로 사용하고 변동 가격은 실제 청구 사용 구간으로 가중하세요. 청구된 Spot·fallback 시간에 실제 지불한 재시도, 용량 중첩과 복구 작업이 포함돼야 합니다. 이미 포함된 작업을 다시 일반적인 “interrupt overhead”로 빼서 이중 계산하지 마세요.

기타 비용에는 관련 Auto Mode 관리 요금, control-plane, EBS, 네트워크/NAT, 전송, 로그와 라이선스를 일관되게 포함합니다. Auto Mode 요금은 EC2 구매 옵션에 추가됩니다. 이전 `중단 횟수 × 복구 시간 × 인스턴스 수` 단축식은 단위와 중단 횟수가 이미 클러스터 전체 기준인지 모호했습니다.

## 운영 검증

Spot에 의존하기 전에 승인된 환경에서 중단·복구를 시험하세요. 경고 누락·지연, 대체 용량 부족, 진행 중 작업, 이미지 다운로드, 스토리지 복구와 엄격한 topology 제약을 포함합니다. 실제 손실 작업량과 청구된 복구 비용을 관찰해야 합니다. 이번 감사는 로컬 스키마·시간 창·구성 검사만 수행했으며 해당 장애 실험을 실행하지 않았습니다.

## 참고 자료

- [Spot interruption notices](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/spot-instance-termination-notices.html)
- [Auto Mode native interruption handling](https://docs.aws.amazon.com/eks/latest/userguide/ml-node-pools.html)
- [Capacity type priority](https://docs.aws.amazon.com/eks/latest/userguide/create-node-pool.html)
- [Karpenter disruption budgets and UTC schedules](https://karpenter.sh/v1.14/concepts/disruption/)
- [Pod termination and preStop](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/)
- [Topology spread](https://kubernetes.io/docs/concepts/scheduling-eviction/topology-spread-constraints/)
- [Downward API fields](https://kubernetes.io/docs/concepts/workloads/pods/downward-api/)
- [nginx graceful shutdown](https://nginx.org/en/docs/control.html)
- [EC2 Spot published discount guidance](https://aws.amazon.com/ec2/spot/)
- [Spot Instance Advisor](https://aws.amazon.com/ec2/spot/instance-advisor/)
- [Spot price history API](https://docs.aws.amazon.com/AWSEC2/latest/APIReference/API_DescribeSpotPriceHistory.html)
- [EKS Auto Mode pricing](https://aws.amazon.com/eks/pricing/)

< [이전: 스케일링 동작](./03-scaling-behavior.md) | [목차](./README.md) | [다음: 운영 및 관리](./05-operations.md) >
