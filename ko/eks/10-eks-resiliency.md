# EKS 고가용성과 복원력 아키텍처

> **지원 버전**: EKS 1.28+, Istio 1.20+, Karpenter 0.33+
> **마지막 업데이트**: 2025년 2월

Amazon EKS 클러스터의 복원력(Resilience)은 장애 발생 시 서비스 영향을 최소화하고 신속하게 복구하는 능력을 의미합니다. 이 문서에서는 EKS 환경에서 고가용성과 복원력을 구현하기 위한 전략, 아키텍처 패턴 및 모범 사례를 제공합니다.

## 목차

1. [복원력 개요와 성숙도 모델](#복원력-개요와-성숙도-모델)
2. [Multi-AZ 전략 (Level 2)](#multi-az-전략-level-2)
3. [Cell-Based Architecture (Level 3)](#cell-based-architecture-level-3)
4. [Multi-Cluster/Multi-Region (Level 4)](#multi-clustermulti-region-level-4)
5. [애플리케이션 복원력 패턴](#애플리케이션-복원력-패턴)
6. [카오스 엔지니어링](#카오스-엔지니어링)
7. [구현 체크리스트](#구현-체크리스트)
8. [다음 단계](#다음-단계)

---

## 복원력 개요와 성숙도 모델

### 복원력의 정의

복원력(Resilience)은 두 가지 핵심 요소로 구성됩니다:

**1. 장애 영향 최소화 (Failure Impact Minimization)**
- 장애 발생 시 영향 범위(Blast Radius)를 제한
- 전체 시스템이 아닌 일부 구성 요소만 영향을 받도록 설계
- 격리(Isolation)와 중복성(Redundancy)을 통한 장애 격리

**2. 복구 능력 (Recovery Ability)**
- 장애 감지 후 자동 복구까지의 시간(RTO) 최소화
- 데이터 손실 없는 복구(RPO) 보장
- 자가 치유(Self-healing) 메커니즘 구현

### 4단계 성숙도 모델

| Level | 이름 | 장애 범위 | 복구 시간 | 핵심 기술 |
|-------|------|----------|----------|----------|
| **Level 1** | 기본 (Pod-level) | 단일 Pod | 초 단위 | Probes, Resource Limits, PDB |
| **Level 2** | Multi-AZ | 가용 영역 | 분 단위 | Topology Spread, ARC Zonal Shift |
| **Level 3** | Cell-Based | 셀 단위 | 분 단위 | Shuffle Sharding, Cell Isolation |
| **Level 4** | Multi-Region | 리전 단위 | 분~시간 | Active-Active, Active-Passive |

> 모든 서비스가 Level 4를 필요로 하지는 않습니다. SLA 요구사항, 규정 준수 요건, 예산에 따라 적절한 수준을 선택하세요.

### Level 1: 기본 복원력 (Pod-level)

가장 기본적인 복원력 수준으로, 단일 Pod 장애에 대응합니다.

#### Liveness/Readiness/Startup Probes

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: resilient-app
spec:
  containers:
  - name: app
    image: my-app:1.0
    ports:
    - containerPort: 8080
    # Startup Probe: 시작 시간이 긴 애플리케이션용
    startupProbe:
      httpGet:
        path: /healthz
        port: 8080
      failureThreshold: 30
      periodSeconds: 10
    # Liveness Probe: 컨테이너가 살아있는지 확인
    livenessProbe:
      httpGet:
        path: /healthz
        port: 8080
      initialDelaySeconds: 0
      periodSeconds: 10
      timeoutSeconds: 5
      failureThreshold: 3
    # Readiness Probe: 트래픽을 받을 준비가 되었는지 확인
    readinessProbe:
      httpGet:
        path: /ready
        port: 8080
      initialDelaySeconds: 5
      periodSeconds: 5
      timeoutSeconds: 3
      successThreshold: 1
      failureThreshold: 3
```

#### Resource Limits 설정

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: resource-managed-app
spec:
  containers:
  - name: app
    image: my-app:1.0
    resources:
      requests:
        memory: "256Mi"
        cpu: "250m"
      limits:
        memory: "512Mi"
        cpu: "500m"
```

#### 기본 PodDisruptionBudget

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: app-pdb
spec:
  minAvailable: 2  # 최소 2개 Pod 유지
  selector:
    matchLabels:
      app: my-app
```

---

## Multi-AZ 전략 (Level 2)

Multi-AZ 전략은 가용 영역(AZ) 장애에 대비하여 워크로드를 여러 AZ에 분산 배치합니다.

### Pod Topology Spread Constraints

Pod를 여러 AZ에 균등하게 분산 배치하는 핵심 메커니즘입니다.

#### Hard Constraint (강제 분산)

조건을 만족하지 못하면 Pod가 스케줄링되지 않습니다.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: zone-spread-app
spec:
  replicas: 6
  selector:
    matchLabels:
      app: zone-spread-app
  template:
    metadata:
      labels:
        app: zone-spread-app
    spec:
      topologySpreadConstraints:
      # 가용 영역 간 분산 (Hard)
      - maxSkew: 1                              # 최대 불균형 허용치
        topologyKey: topology.kubernetes.io/zone
        whenUnsatisfiable: DoNotSchedule        # Hard constraint
        labelSelector:
          matchLabels:
            app: zone-spread-app
        minDomains: 3                           # 최소 3개 AZ에 분산
      containers:
      - name: app
        image: my-app:1.0
```

#### Soft Constraint (선호 분산)

조건을 만족하지 못해도 Pod가 스케줄링됩니다.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: soft-spread-app
spec:
  replicas: 4
  selector:
    matchLabels:
      app: soft-spread-app
  template:
    metadata:
      labels:
        app: soft-spread-app
    spec:
      topologySpreadConstraints:
      - maxSkew: 2                              # 더 느슨한 불균형 허용
        topologyKey: topology.kubernetes.io/zone
        whenUnsatisfiable: ScheduleAnyway       # Soft constraint
        labelSelector:
          matchLabels:
            app: soft-spread-app
      containers:
      - name: app
        image: my-app:1.0
```

#### Hard와 Soft 결합

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: hybrid-spread-app
spec:
  replicas: 9
  selector:
    matchLabels:
      app: hybrid-spread-app
  template:
    metadata:
      labels:
        app: hybrid-spread-app
    spec:
      topologySpreadConstraints:
      # AZ 분산: Hard (반드시 여러 AZ에 배치)
      - maxSkew: 1
        topologyKey: topology.kubernetes.io/zone
        whenUnsatisfiable: DoNotSchedule
        labelSelector:
          matchLabels:
            app: hybrid-spread-app
        minDomains: 2
      # 노드 분산: Soft (가능하면 여러 노드에 배치)
      - maxSkew: 2
        topologyKey: kubernetes.io/hostname
        whenUnsatisfiable: ScheduleAnyway
        labelSelector:
          matchLabels:
            app: hybrid-spread-app
      containers:
      - name: app
        image: my-app:1.0
```

| 파라미터 | 설명 |
|---------|------|
| `maxSkew` | 토폴로지 도메인 간 Pod 수 최대 차이 |
| `topologyKey` | 분산 기준 노드 레이블 (zone, hostname 등) |
| `whenUnsatisfiable` | `DoNotSchedule` (Hard) 또는 `ScheduleAnyway` (Soft) |
| `minDomains` | 최소 도메인 수 (3 AZ 사용 시 3 권장) |

### Karpenter Multi-AZ Node Provisioning

Karpenter를 사용하여 여러 AZ에 노드를 자동으로 프로비저닝합니다.

#### NodePool 설정

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: multi-az-nodepool
spec:
  template:
    spec:
      requirements:
        # 인스턴스 타입
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["c", "m", "r"]
        - key: karpenter.k8s.aws/instance-size
          operator: In
          values: ["medium", "large", "xlarge"]
        # 가용 영역 분산
        - key: topology.kubernetes.io/zone
          operator: In
          values: ["ap-northeast-2a", "ap-northeast-2b", "ap-northeast-2c"]
        # 용량 타입
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["spot", "on-demand"]
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: default
  # Disruption 설정: 동시 20% 제한
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 1m
    budgets:
    - nodes: "20%"                    # 동시에 20%까지만 중단 허용
    - nodes: "0"                      # 업무 시간에는 중단 금지
      schedule: "0 9-18 * * MON-FRI"
      duration: 9h
  limits:
    cpu: 1000
    memory: 1000Gi
  weight: 100
```

#### Spot과 On-Demand 혼합 전략

```yaml
# Spot 우선 NodePool
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: spot-preferred
spec:
  template:
    spec:
      requirements:
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["spot"]
        - key: topology.kubernetes.io/zone
          operator: In
          values: ["ap-northeast-2a", "ap-northeast-2b", "ap-northeast-2c"]
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: default
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 30s
    budgets:
    - nodes: "20%"
  weight: 100  # 높은 우선순위
---
# On-Demand 폴백 NodePool
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: on-demand-fallback
spec:
  template:
    spec:
      requirements:
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["on-demand"]
        - key: topology.kubernetes.io/zone
          operator: In
          values: ["ap-northeast-2a", "ap-northeast-2b", "ap-northeast-2c"]
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: default
  weight: 50  # 낮은 우선순위 (Spot 불가 시에만 사용)
```

### ARC Zonal Shift

AWS Application Recovery Controller (ARC)의 Zonal Shift는 특정 AZ 장애 시 트래픽을 자동으로 다른 AZ로 전환합니다.

#### Zonal Autoshift 구성

```bash
# Zonal Autoshift 활성화 (자동 감지 및 전환)
aws arc-zonal-shift update-zonal-autoshift-configuration \
    --zonal-autoshift-status ENABLED

# ALB에 Zonal Autoshift Practice Run 설정
aws arc-zonal-shift create-practice-run-configuration \
    --resource-identifier arn:aws:elasticloadbalancing:ap-northeast-2:123456789012:loadbalancer/app/my-alb/50dc6c495c0c9188 \
    --outcome-alarms '[{
        "alarmIdentifier": "arn:aws:cloudwatch:ap-northeast-2:123456789012:alarm:HighLatencyAlarm",
        "type": "CLOUDWATCH"
    }]' \
    --blocked-windows '[]' \
    --blocked-dates '[]'
```

#### 수동 Zonal Shift 실행

```bash
# 특정 AZ에서 트래픽 제거 (수동)
aws arc-zonal-shift start-zonal-shift \
    --resource-identifier arn:aws:elasticloadbalancing:ap-northeast-2:123456789012:loadbalancer/app/my-alb/50dc6c495c0c9188 \
    --away-from ap-northeast-2a \
    --expires-in 1h \
    --comment "AZ-a experiencing issues"

# Zonal Shift 상태 확인
aws arc-zonal-shift list-zonal-shifts

# Zonal Shift 취소
aws arc-zonal-shift cancel-zonal-shift \
    --zonal-shift-id shift-12345678
```

### 스토리지 고려사항

#### WaitForFirstConsumer StorageClass

EBS 볼륨이 특정 AZ에 고정되는 것을 방지합니다.

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: ebs-sc
provisioner: ebs.csi.aws.com
volumeBindingMode: WaitForFirstConsumer  # Pod가 스케줄된 AZ에서 볼륨 생성
parameters:
  type: gp3
  encrypted: "true"
allowVolumeExpansion: true
reclaimPolicy: Delete
```

#### EFS for Cross-AZ Access

여러 AZ에서 동시 접근이 필요한 경우 EFS를 사용합니다.

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: efs-sc
provisioner: efs.csi.aws.com
parameters:
  provisioningMode: efs-ap
  fileSystemId: fs-0123456789abcdef0
  directoryPerms: "700"
  basePath: "/dynamic_provisioning"
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: efs-claim
spec:
  accessModes:
    - ReadWriteMany  # 여러 Pod에서 동시 읽기/쓰기
  storageClassName: efs-sc
  resources:
    requests:
      storage: 5Gi
```

### Istio Locality-Aware Routing

동일 AZ 내 트래픽을 우선 라우팅하여 Cross-AZ 전송 비용을 절감합니다.

```yaml
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: locality-routing
spec:
  host: my-service.default.svc.cluster.local
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 100
      http:
        h2UpgradePolicy: UPGRADE
    loadBalancer:
      simple: ROUND_ROBIN
      localityLbSetting:
        enabled: true
        # 동일 AZ 우선, 실패 시 다른 AZ로 폴백
        distribute:
        - from: "ap-northeast-2/ap-northeast-2a/*"
          to:
            "ap-northeast-2/ap-northeast-2a/*": 80  # 80% 동일 AZ
            "ap-northeast-2/ap-northeast-2b/*": 10  # 10% 다른 AZ
            "ap-northeast-2/ap-northeast-2c/*": 10  # 10% 다른 AZ
        - from: "ap-northeast-2/ap-northeast-2b/*"
          to:
            "ap-northeast-2/ap-northeast-2b/*": 80
            "ap-northeast-2/ap-northeast-2a/*": 10
            "ap-northeast-2/ap-northeast-2c/*": 10
    outlierDetection:
      consecutive5xxErrors: 5
      interval: 10s
      baseEjectionTime: 30s
      maxEjectionPercent: 50
```

**비용 절감 효과:**
- Locality-aware routing으로 80%+ 트래픽을 동일 AZ 내에서 처리
- Cross-AZ 전송 비용 60-80% 절감 가능
- 네트워크 지연 시간 감소 (동일 AZ 내 <1ms)

---

## Cell-Based Architecture (Level 3)

Cell-Based Architecture는 시스템을 독립적인 셀로 분리하여 장애 영향 범위를 제한합니다.

### Cell의 정의

셀(Cell)은 다음 요소를 포함하는 자체 완결형 서비스 단위입니다:

- **애플리케이션 인스턴스**: 독립적으로 운영되는 서비스 Pod
- **데이터 저장소**: 셀 전용 데이터베이스 또는 파티션
- **캐시**: 셀 전용 Redis/ElastiCache 인스턴스
- **메시지 큐**: 셀 전용 SQS 큐 또는 Kafka 토픽

### Cell 파티셔닝 전략

| 전략 | 설명 | 장점 | 단점 |
|-----|------|------|------|
| **고객 기반** | 고객 ID 범위별 분리 | 데이터 지역성 우수 | 고객 규모 불균형 가능 |
| **지역 기반** | 지리적 위치별 분리 | 규정 준수 용이 | 글로벌 고객 처리 복잡 |
| **용량 기반** | 부하 수준별 분리 | 리소스 효율성 | 동적 재할당 필요 |
| **티어 기반** | 서비스 티어별 분리 | SLA 차별화 용이 | 관리 복잡성 증가 |

### Namespace 기반 Cell 구현

```yaml
# Cell 1 Namespace
apiVersion: v1
kind: Namespace
metadata:
  name: cell-1
  labels:
    cell: "1"
    customer-range: "a-f"
---
# Cell 1 ResourceQuota
apiVersion: v1
kind: ResourceQuota
metadata:
  name: cell-1-quota
  namespace: cell-1
spec:
  hard:
    requests.cpu: "20"
    requests.memory: 40Gi
    limits.cpu: "40"
    limits.memory: 80Gi
    pods: "100"
    services: "20"
    persistentvolumeclaims: "50"
---
# Cell 1 LimitRange
apiVersion: v1
kind: LimitRange
metadata:
  name: cell-1-limits
  namespace: cell-1
spec:
  limits:
  - default:
      cpu: "500m"
      memory: 512Mi
    defaultRequest:
      cpu: "100m"
      memory: 128Mi
    type: Container
---
# Cell 1 NetworkPolicy (셀 간 격리)
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: cell-1-isolation
  namespace: cell-1
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
  ingress:
  # 동일 셀 내 트래픽 허용
  - from:
    - namespaceSelector:
        matchLabels:
          cell: "1"
  # Ingress 컨트롤러에서 오는 트래픽 허용
  - from:
    - namespaceSelector:
        matchLabels:
          name: ingress-nginx
  egress:
  # 동일 셀 내 트래픽 허용
  - to:
    - namespaceSelector:
        matchLabels:
          cell: "1"
  # DNS 허용
  - to:
    - namespaceSelector:
        matchLabels:
          name: kube-system
    ports:
    - protocol: UDP
      port: 53
  # 외부 서비스 허용 (AWS 서비스 등)
  - to:
    - ipBlock:
        cidr: 0.0.0.0/0
        except:
        - 10.0.0.0/8  # 다른 셀의 내부 IP 차단
```

### Cluster 기반 Cell 구현

더 강력한 격리가 필요한 경우 클러스터 단위로 셀을 분리합니다.

```bash
# Cell별 EKS 클러스터 생성
for cell in cell-1 cell-2 cell-3 cell-4; do
  eksctl create cluster \
    --name ${cell}-cluster \
    --region ap-northeast-2 \
    --version 1.29 \
    --with-oidc \
    --managed \
    --node-type m5.xlarge \
    --nodes 3 \
    --nodes-min 2 \
    --nodes-max 10
done
```

### Shuffle Sharding

Shuffle Sharding은 각 고객을 여러 셀 중 일부에만 할당하여 장애 영향을 제한합니다.

**Shuffle Sharding의 장점 (8개 셀에서 2개 선택):**

- 가능한 조합 수: C(8,2) = 28개
- 단일 셀 장애 시 영향: 최대 25% 고객 (2/8)
- 두 개의 다른 고객이 완전히 동일한 셀 조합을 가질 확률: 1/28 (약 3.6%)

```
8개 Cell 풀에서 2개 Cell 조합:
- 고객 A -> Cell 1, Cell 5
- 고객 B -> Cell 2, Cell 7
- 고객 C -> Cell 1, Cell 3

Cell 1 장애 시:
- 고객 A -> Cell 5로 자동 전환
- 고객 B -> 영향 없음
- 고객 C -> Cell 3으로 자동 전환
```

```yaml
# Shuffle Sharding 라우팅 ConfigMap
apiVersion: v1
kind: ConfigMap
metadata:
  name: shuffle-sharding-config
data:
  sharding.yaml: |
    # 8개 셀 풀에서 각 고객에게 2개 셀 할당
    cells:
      - name: cell-1
        weight: 1
      - name: cell-2
        weight: 1
      - name: cell-3
        weight: 1
      - name: cell-4
        weight: 1
      - name: cell-5
        weight: 1
      - name: cell-6
        weight: 1
      - name: cell-7
        weight: 1
      - name: cell-8
        weight: 1

    # 고객별 셀 할당 (해시 기반 자동 할당 또는 명시적 지정)
    customer_assignments:
      customer-001:
        primary: cell-1
        secondary: cell-4
      customer-002:
        primary: cell-2
        secondary: cell-5
      customer-003:
        primary: cell-3
        secondary: cell-6
```

---

## Multi-Cluster/Multi-Region (Level 4)

Multi-Region 아키텍처는 리전 전체 장애에 대비하여 최고 수준의 복원력을 제공합니다.

### 아키텍처 패턴 비교

| 패턴 | RTO | RPO | 비용 | 복잡성 | 사용 사례 |
|-----|-----|-----|-----|-------|----------|
| **Active-Active** | ~0 (Zero) | ~0 (Zero) | 높음 (2x+) | 높음 | 미션 크리티컬 |
| **Active-Passive** | 분 단위 | 분 단위 | 중간 (1.5x) | 중간 | 비즈니스 크리티컬 |
| **Regional Isolation** | 해당 없음 | 해당 없음 | 중간 | 중간 | 데이터 규정 준수 |
| **Hub-Spoke** | 분 단위 | 분 단위 | 낮음 | 낮음 | 중앙 집중 관리 |

### Global Accelerator 구성

```bash
# Global Accelerator 생성
aws globalaccelerator create-accelerator \
    --name my-app-accelerator \
    --ip-address-type IPV4 \
    --enabled

# 리스너 생성
aws globalaccelerator create-listener \
    --accelerator-arn arn:aws:globalaccelerator::123456789012:accelerator/abcd1234 \
    --protocol TCP \
    --port-ranges FromPort=443,ToPort=443

# 엔드포인트 그룹 (서울 리전)
aws globalaccelerator create-endpoint-group \
    --listener-arn arn:aws:globalaccelerator::123456789012:accelerator/abcd1234/listener/efgh5678 \
    --endpoint-group-region ap-northeast-2 \
    --traffic-dial-percentage 50 \
    --health-check-port 443 \
    --health-check-protocol HTTPS \
    --health-check-path /healthz \
    --endpoint-configurations '[{
        "EndpointId": "arn:aws:elasticloadbalancing:ap-northeast-2:123456789012:loadbalancer/app/my-alb-seoul/1234567890123456",
        "Weight": 100
    }]'

# 엔드포인트 그룹 (도쿄 리전)
aws globalaccelerator create-endpoint-group \
    --listener-arn arn:aws:globalaccelerator::123456789012:accelerator/abcd1234/listener/efgh5678 \
    --endpoint-group-region ap-northeast-1 \
    --traffic-dial-percentage 50 \
    --health-check-port 443 \
    --health-check-protocol HTTPS \
    --health-check-path /healthz \
    --endpoint-configurations '[{
        "EndpointId": "arn:aws:elasticloadbalancing:ap-northeast-1:123456789012:loadbalancer/app/my-alb-tokyo/0987654321098765",
        "Weight": 100
    }]'
```

### ArgoCD ApplicationSet for Multi-Cluster Deployment

#### Cluster Generator

```yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: multi-cluster-app
  namespace: argocd
spec:
  generators:
  # 레이블로 클러스터 선택
  - clusters:
      selector:
        matchLabels:
          env: production
          region: asia
  template:
    metadata:
      name: '{{name}}-my-app'
    spec:
      project: default
      source:
        repoURL: https://github.com/my-org/my-app.git
        targetRevision: HEAD
        path: 'k8s/overlays/{{metadata.labels.region}}'
      destination:
        server: '{{server}}'
        namespace: my-app
      syncPolicy:
        automated:
          prune: true
          selfHeal: true
        syncOptions:
        - CreateNamespace=true
```

#### Git Directory Generator

```yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: region-apps
  namespace: argocd
spec:
  generators:
  - git:
      repoURL: https://github.com/my-org/gitops-config.git
      revision: HEAD
      directories:
      - path: 'regions/*'
  template:
    metadata:
      name: '{{path.basename}}-app'
    spec:
      project: default
      source:
        repoURL: https://github.com/my-org/gitops-config.git
        targetRevision: HEAD
        path: '{{path}}'
      destination:
        server: 'https://{{path.basename}}.eks.amazonaws.com'
        namespace: default
```

#### Matrix Generator (클러스터 x 환경)

```yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: matrix-deployment
  namespace: argocd
spec:
  generators:
  - matrix:
      generators:
      # 첫 번째 차원: 클러스터
      - clusters:
          selector:
            matchLabels:
              env: production
      # 두 번째 차원: 애플리케이션 목록
      - list:
          elements:
          - app: frontend
            port: "80"
          - app: backend
            port: "8080"
          - app: worker
            port: "9090"
  template:
    metadata:
      name: '{{name}}-{{app}}'
    spec:
      project: default
      source:
        repoURL: https://github.com/my-org/apps.git
        targetRevision: HEAD
        path: '{{app}}/k8s'
        helm:
          parameters:
          - name: cluster.name
            value: '{{name}}'
          - name: service.port
            value: '{{port}}'
      destination:
        server: '{{server}}'
        namespace: '{{app}}'
```

### Istio Multi-Primary Federation

여러 클러스터 간 서비스 검색과 트래픽 관리를 위한 Istio Multi-Primary 설정입니다.

```yaml
# 클러스터 1 (서울) - IstioOperator
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
metadata:
  name: istio-control-plane
  namespace: istio-system
spec:
  values:
    global:
      meshID: mesh1
      multiCluster:
        clusterName: cluster-seoul
      network: network1
  meshConfig:
    defaultConfig:
      proxyMetadata:
        ISTIO_META_DNS_CAPTURE: "true"
        ISTIO_META_DNS_AUTO_ALLOCATE: "true"
```

```bash
# 클러스터 간 Secret 교환
# cluster-seoul에서 cluster-tokyo의 API 서버에 접근할 수 있도록 설정
istioctl create-remote-secret \
    --context=cluster-tokyo \
    --name=cluster-tokyo | \
    kubectl apply -f - --context=cluster-seoul

# cluster-tokyo에서 cluster-seoul의 API 서버에 접근할 수 있도록 설정
istioctl create-remote-secret \
    --context=cluster-seoul \
    --name=cluster-seoul | \
    kubectl apply -f - --context=cluster-tokyo
```

```yaml
# Cross-cluster 서비스 라우팅
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: cross-cluster-routing
spec:
  hosts:
  - my-service.default.svc.cluster.local
  http:
  - match:
    - headers:
        x-region:
          exact: tokyo
    route:
    - destination:
        host: my-service.default.svc.cluster.local
        subset: tokyo
  - route:
    - destination:
        host: my-service.default.svc.cluster.local
        subset: seoul
      weight: 80
    - destination:
        host: my-service.default.svc.cluster.local
        subset: tokyo
      weight: 20
---
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: cross-cluster-subsets
spec:
  host: my-service.default.svc.cluster.local
  subsets:
  - name: seoul
    labels:
      topology.kubernetes.io/region: ap-northeast-2
  - name: tokyo
    labels:
      topology.kubernetes.io/region: ap-northeast-1
```

---

## 애플리케이션 복원력 패턴

### PodDisruptionBudgets

PDB는 자발적 중단(voluntary disruption) 시 최소 가용 Pod 수를 보장합니다.

#### minAvailable 방식

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: app-pdb-min
spec:
  minAvailable: 2  # 항상 최소 2개 Pod 유지
  selector:
    matchLabels:
      app: my-app
```

#### maxUnavailable 방식

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: app-pdb-max
spec:
  maxUnavailable: 1  # 동시에 1개까지만 중단 허용
  selector:
    matchLabels:
      app: my-app
```

#### 비율 기반 PDB

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: app-pdb-percentage
spec:
  minAvailable: "75%"  # 75% 이상 Pod 유지
  selector:
    matchLabels:
      app: my-app
```

```bash
# PDB 목록 및 상태 확인
kubectl get pdb

# 상세 정보 확인
kubectl describe pdb app-pdb-min

# 출력 예시:
# Name:           app-pdb-min
# Min available:  2
# Selector:       app=my-app
# Status:
#     Allowed disruptions:  1
#     Current:              3
#     Desired:              3
#     Total:                3
```

### Graceful Shutdown

Pod 종료 시 진행 중인 요청을 완료하고 안전하게 종료하는 패턴입니다.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: graceful-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: graceful-app
  template:
    metadata:
      labels:
        app: graceful-app
    spec:
      terminationGracePeriodSeconds: 60  # 최대 60초 대기
      containers:
      - name: app
        image: my-app:1.0
        ports:
        - containerPort: 8080
        lifecycle:
          preStop:
            exec:
              command:
              - /bin/sh
              - -c
              - |
                # 5초 대기: Endpoint 제거가 전파될 시간 확보
                sleep 5
                # 애플리케이션에 종료 시그널 전송 (graceful shutdown 트리거)
                kill -SIGTERM 1
        readinessProbe:
          httpGet:
            path: /ready
            port: 8080
          periodSeconds: 5
```

**Graceful Shutdown 흐름:**

1. `kubectl delete pod` 또는 노드 drain 발생
2. Pod가 `Terminating` 상태로 전환
3. `preStop` 훅 실행 (5초 대기)
4. Service Endpoint에서 Pod 제거 (새 트래픽 차단)
5. SIGTERM 시그널 전송
6. 애플리케이션이 진행 중인 요청 완료
7. `terminationGracePeriodSeconds` 내에 종료되지 않으면 SIGKILL

### Circuit Breaker via Istio

Istio DestinationRule을 사용한 Circuit Breaker 패턴입니다.

```yaml
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: circuit-breaker
spec:
  host: backend-service.default.svc.cluster.local
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 100           # 최대 TCP 연결 수
        connectTimeout: 30s
      http:
        h2UpgradePolicy: UPGRADE
        http1MaxPendingRequests: 100  # 대기 중인 요청 최대 수
        http2MaxRequests: 1000        # 최대 HTTP/2 요청 수
        maxRequestsPerConnection: 10  # 연결당 최대 요청 수
        maxRetries: 3                 # 최대 재시도 횟수
    outlierDetection:
      consecutive5xxErrors: 5         # 연속 5xx 오류 임계값
      consecutiveGatewayErrors: 5     # 연속 게이트웨이 오류 임계값
      interval: 10s                   # 검사 간격
      baseEjectionTime: 30s           # 기본 제외 시간
      maxEjectionPercent: 50          # 최대 제외 비율 (50%)
      minHealthPercent: 30            # 최소 건강 비율 (30% 이하면 제외 중단)
      splitExternalLocalOriginErrors: true
```

### Retry/Timeout 정책

```yaml
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: retry-timeout-policy
spec:
  hosts:
  - backend-service
  http:
  - route:
    - destination:
        host: backend-service
    timeout: 10s                      # 전체 요청 타임아웃 (10초)
    retries:
      attempts: 3                     # 최대 3회 재시도
      perTryTimeout: 3s               # 시도당 타임아웃 (3초)
      retryOn: "5xx,reset,connect-failure,retriable-4xx"
      retryRemoteLocalities: true     # 다른 locality로도 재시도
```

**재시도 조건 설명:**
- `5xx`: 서버 오류 응답
- `reset`: 연결 리셋
- `connect-failure`: 연결 실패
- `retriable-4xx`: 재시도 가능한 4xx 오류 (408, 409 등)

---

## 카오스 엔지니어링

카오스 엔지니어링은 프로덕션 환경에서 장애에 대한 시스템의 복원력을 검증합니다.

### AWS Fault Injection Service (FIS)

#### Pod 삭제 실험

```json
{
  "description": "EKS Pod 삭제 실험",
  "targets": {
    "eks-pods": {
      "resourceType": "aws:eks:pod",
      "resourceArns": [
        "arn:aws:eks:ap-northeast-2:123456789012:cluster/my-cluster"
      ],
      "selectionMode": "COUNT(3)",
      "parameters": {
        "clusterIdentifier": "my-cluster",
        "namespace": "default",
        "selectorType": "labelSelector",
        "selectorValue": "app=my-app"
      }
    }
  },
  "actions": {
    "delete-pods": {
      "actionId": "aws:eks:pod-delete",
      "parameters": {},
      "targets": {
        "Pods": "eks-pods"
      }
    }
  },
  "stopConditions": [
    {
      "source": "aws:cloudwatch:alarm",
      "value": "arn:aws:cloudwatch:ap-northeast-2:123456789012:alarm:HighErrorRate"
    }
  ],
  "roleArn": "arn:aws:iam::123456789012:role/FISRole"
}
```

#### AZ 장애 시뮬레이션

```json
{
  "description": "AZ 장애 시뮬레이션",
  "targets": {
    "az-subnets": {
      "resourceType": "aws:ec2:subnet",
      "resourceArns": [
        "arn:aws:ec2:ap-northeast-2:123456789012:subnet/subnet-abc123"
      ],
      "selectionMode": "ALL"
    }
  },
  "actions": {
    "disrupt-network": {
      "actionId": "aws:network:disrupt-connectivity",
      "parameters": {
        "duration": "PT5M",
        "scope": "all"
      },
      "targets": {
        "Subnets": "az-subnets"
      }
    }
  },
  "stopConditions": [
    {
      "source": "aws:cloudwatch:alarm",
      "value": "arn:aws:cloudwatch:ap-northeast-2:123456789012:alarm:ServiceHealthAlarm"
    }
  ],
  "roleArn": "arn:aws:iam::123456789012:role/FISRole"
}
```

#### 네트워크 지연 실험

```json
{
  "description": "네트워크 지연 주입",
  "targets": {
    "eks-pods": {
      "resourceType": "aws:eks:pod",
      "resourceArns": [
        "arn:aws:eks:ap-northeast-2:123456789012:cluster/my-cluster"
      ],
      "selectionMode": "COUNT(5)",
      "parameters": {
        "clusterIdentifier": "my-cluster",
        "namespace": "default",
        "selectorType": "labelSelector",
        "selectorValue": "app=my-app"
      }
    }
  },
  "actions": {
    "inject-latency": {
      "actionId": "aws:eks:pod-network-latency",
      "parameters": {
        "duration": "PT5M",
        "delayMilliseconds": "200",
        "jitterMilliseconds": "50",
        "sources": "0.0.0.0/0"
      },
      "targets": {
        "Pods": "eks-pods"
      }
    }
  },
  "stopConditions": [
    {
      "source": "aws:cloudwatch:alarm",
      "value": "arn:aws:cloudwatch:ap-northeast-2:123456789012:alarm:HighLatencyAlarm"
    }
  ],
  "roleArn": "arn:aws:iam::123456789012:role/FISRole"
}
```

### Litmus Chaos (CNCF Incubating)

#### Litmus 설치

```bash
# Litmus Operator 설치
kubectl apply -f https://litmuschaos.github.io/litmus/litmus-operator-v3.0.0.yaml

# ChaosHub 연결 (실험 템플릿 저장소)
kubectl apply -f - <<EOF
apiVersion: litmuschaos.io/v1alpha1
kind: ChaosHub
metadata:
  name: litmus-hub
  namespace: litmus
spec:
  repoUrl: https://github.com/litmuschaos/chaos-charts
  branch: master
EOF
```

#### Pod 삭제 ChaosExperiment

```yaml
apiVersion: litmuschaos.io/v1alpha1
kind: ChaosEngine
metadata:
  name: pod-delete-chaos
  namespace: default
spec:
  appinfo:
    appns: default
    applabel: "app=my-app"
    appkind: deployment
  engineState: active
  chaosServiceAccount: litmus-admin
  experiments:
  - name: pod-delete
    spec:
      components:
        env:
        - name: TOTAL_CHAOS_DURATION
          value: "60"
        - name: CHAOS_INTERVAL
          value: "10"
        - name: FORCE
          value: "false"
        - name: PODS_AFFECTED_PERC
          value: "50"
```

#### Node Termination Experiment

```yaml
apiVersion: litmuschaos.io/v1alpha1
kind: ChaosEngine
metadata:
  name: node-drain-chaos
  namespace: default
spec:
  engineState: active
  auxiliaryAppInfo: ""
  chaosServiceAccount: litmus-admin
  experiments:
  - name: node-drain
    spec:
      components:
        env:
        - name: TOTAL_CHAOS_DURATION
          value: "120"
        - name: TARGET_NODE
          value: ""  # 빈 값이면 랜덤 선택
        - name: NODE_LABEL
          value: "kubernetes.io/os=linux"
```

#### DNS Chaos Experiment

```yaml
apiVersion: litmuschaos.io/v1alpha1
kind: ChaosEngine
metadata:
  name: dns-chaos
  namespace: default
spec:
  appinfo:
    appns: default
    applabel: "app=my-app"
    appkind: deployment
  engineState: active
  chaosServiceAccount: litmus-admin
  experiments:
  - name: pod-dns-error
    spec:
      components:
        env:
        - name: TOTAL_CHAOS_DURATION
          value: "60"
        - name: TARGET_HOSTNAMES
          value: "backend-service.default.svc.cluster.local"
        - name: MATCH_SCHEME
          value: "exact"
```

### Chaos Mesh

#### Chaos Mesh 설치

```bash
# Helm으로 설치
helm repo add chaos-mesh https://charts.chaos-mesh.org
helm install chaos-mesh chaos-mesh/chaos-mesh \
    --namespace chaos-mesh \
    --create-namespace \
    --version 2.6.0
```

#### Network Partition

```yaml
apiVersion: chaos-mesh.org/v1alpha1
kind: NetworkChaos
metadata:
  name: network-partition
  namespace: chaos-mesh
spec:
  action: partition
  mode: all
  selector:
    namespaces:
    - default
    labelSelectors:
      app: frontend
  direction: both
  target:
    mode: all
    selector:
      namespaces:
      - default
      labelSelectors:
        app: backend
  duration: "5m"
```

#### I/O Chaos

```yaml
apiVersion: chaos-mesh.org/v1alpha1
kind: IOChaos
metadata:
  name: io-latency
  namespace: chaos-mesh
spec:
  action: latency
  mode: all
  selector:
    namespaces:
    - default
    labelSelectors:
      app: database
  volumePath: /var/lib/postgresql/data
  path: "*"
  delay: "100ms"
  percent: 50
  duration: "5m"
```

#### Time Manipulation

```yaml
apiVersion: chaos-mesh.org/v1alpha1
kind: TimeChaos
metadata:
  name: time-shift
  namespace: chaos-mesh
spec:
  mode: all
  selector:
    namespaces:
    - default
    labelSelectors:
      app: scheduler
  timeOffset: "-2h"  # 2시간 과거로 설정
  duration: "10m"
```

### Game Day Framework

Game Day는 체계적인 카오스 엔지니어링 실습입니다.

**5단계 프레임워크:**

| 단계 | 활동 | 산출물 |
|------|------|--------|
| 1. 정상 상태 기록 | 메트릭 베이스라인 수집 | 대시보드 스냅샷 |
| 2. 장애 주입 | FIS/Litmus/Chaos Mesh 실험 실행 | 실험 로그 |
| 3. 복구 관찰 | 자동 복구 과정 모니터링 | 복구 시간 측정 |
| 4. 영향 분석 | 에러율, 지연시간 변화 분석 | 영향 보고서 |
| 5. 사후 리뷰 | 개선 항목 도출, Action Item | 개선 계획 |

---

## 구현 체크리스트

### Level 1: 기본 복원력 체크리스트

- [ ] 모든 컨테이너에 Liveness Probe 설정
- [ ] 모든 컨테이너에 Readiness Probe 설정
- [ ] 시작 시간이 긴 앱에 Startup Probe 설정
- [ ] Resource requests/limits 설정
- [ ] 중요 Deployment에 PDB 설정
- [ ] replicas >= 2 설정

### Level 2: Multi-AZ 체크리스트

- [ ] Topology Spread Constraints 적용
- [ ] minDomains >= 2 설정
- [ ] Karpenter NodePool에 Multi-AZ 설정
- [ ] Disruption budget 20% 이하로 설정
- [ ] StorageClass volumeBindingMode: WaitForFirstConsumer
- [ ] 공유 스토리지에 EFS 사용
- [ ] Istio locality-aware routing 설정
- [ ] ARC Zonal Autoshift 활성화

### Level 3: Cell-Based 체크리스트

- [ ] Cell 파티셔닝 전략 정의
- [ ] Namespace 또는 Cluster 기반 Cell 구현
- [ ] Cell별 ResourceQuota 설정
- [ ] Cell간 NetworkPolicy 적용
- [ ] Shuffle Sharding 구현 (선택적)
- [ ] Cell별 데이터스토어 분리
- [ ] Cell별 캐시 분리

### Level 4: Multi-Region 체크리스트

- [ ] 아키텍처 패턴 선택 (Active-Active/Passive)
- [ ] Global Accelerator 설정
- [ ] 리전별 EKS 클러스터 생성
- [ ] ArgoCD ApplicationSet 설정
- [ ] 데이터 복제 전략 구현 (Aurora Global DB 등)
- [ ] Istio Multi-Primary 구성 (선택적)
- [ ] Cross-region 장애 조치 테스트
- [ ] 리전별 모니터링 통합

### 비용 고려사항

| 항목 | 비용 영향 | 절감 전략 |
|------|----------|----------|
| **Multi-Region** | 2x+ 증가 | Active-Passive로 대기 리전 비용 절감 |
| **Spot Instances** | 60-90% 절감 | 상태 없는 워크로드에 Spot 사용 |
| **Locality Routing** | 60-80% 절감 | Cross-AZ 트래픽 최소화 |
| **Cell Architecture** | 10-20% 증가 | 장애 영향 감소로 운영 비용 절감 |
| **Chaos Engineering** | 월 $100-500 | FIS 사용량 기반 과금 |

---

## 다음 단계

이 문서에서는 EKS 클러스터의 고가용성과 복원력 아키텍처에 대해 다루었습니다. 복원력 전략을 구현한 후에는 문제 발생 시 효과적인 디버깅이 중요합니다.

### 관련 문서

- **다음 문서**: [EKS 고급 디버깅](./11-eks-advanced-debugging.md) - 복잡한 문제 상황에서의 디버깅 기법
- **퀴즈**: [EKS 복원력 퀴즈](../../quizzes/eks/10-eks-resiliency-quiz.md) - 학습 내용 확인

### 추가 학습 리소스

- [AWS Well-Architected Framework - Reliability Pillar](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/welcome.html)
- [Amazon EKS Best Practices Guide - Reliability](https://aws.github.io/aws-eks-best-practices/reliability/docs/)
- [Kubernetes Documentation - Pod Topology Spread Constraints](https://kubernetes.io/docs/concepts/scheduling-eviction/topology-spread-constraints/)
- [Istio Documentation - Locality Load Balancing](https://istio.io/latest/docs/tasks/traffic-management/locality-load-balancing/)

### 핵심 요약

1. **Level 1 (기본)**: Probes, Resource Limits, PDB로 Pod 수준 복원력 확보
2. **Level 2 (Multi-AZ)**: Topology Spread, ARC Zonal Shift로 AZ 장애 대응
3. **Level 3 (Cell-Based)**: Shuffle Sharding으로 장애 영향 범위 제한
4. **Level 4 (Multi-Region)**: Active-Active/Passive로 리전 장애 대응
5. **카오스 엔지니어링**: FIS, Litmus, Chaos Mesh로 복원력 검증

복원력은 한 번 구현하고 끝나는 것이 아니라, 지속적인 테스트와 개선이 필요한 여정입니다. 정기적인 Game Day를 통해 시스템의 약점을 발견하고 개선해 나가시기 바랍니다.
