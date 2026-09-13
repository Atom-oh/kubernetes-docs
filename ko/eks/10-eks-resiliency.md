# EKS 고가용성과 복원력 아키텍처

> **예제 API 기준**: Kubernetes 1.36; 현재 지원 EKS와 호환 controller release 선택
> **마지막 업데이트**: 2026년 9월 12일

Amazon EKS 클러스터의 복원력(Resilience)은 장애 발생 시 서비스 영향을 최소화하고 신속하게 복구하는 능력을 의미합니다. 이 문서에서는 EKS 환경에서 고가용성과 복원력을 구현하기 위한 전략, 아키텍처 패턴 및 모범 사례를 제공합니다.

예시는 설정 패턴이며 검증된 운영 플랫폼이 아닙니다. 소유 test 범위에서 image·health contract·IAM·인프라 참조를 검토한 값으로 바꿉니다. 감사 중 cluster 생성·failover·chaos 실험은 하지 않았습니다. Multi-AZ·복제·control-plane SLA만으로 무손실이나 workload 복구 시간이 보장되지는 않습니다.

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
- 감지·복원을 포함한 허용 복구 시간(RTO) 목표 수립
- 허용 recovery point·데이터 손실 기간(RPO) 정의 및 검증
- 자가 치유(Self-healing) 메커니즘 구현

### 4단계 성숙도 모델

| 단계 | 범위 | 예시 제어 | 기존 복구 시간 예시, 실측 아님 |
| --- | --- | --- | --- |
| 1. 기본 | Pod·workload | Probe·resource·eviction budget·shutdown | 초–분 |
| 2. Multi-AZ | AZ 장애 | Placement·잔여 용량·traffic·data 복구 | 초–분 |
| 3. Cell | 서비스 partition | Routing·제한한 의존성·용량 | 부분 영향의 초–분 |
| 4. Multi-Region | 리전 장애 | 지역별 traffic·data failover·운영 | 설계에 따라 near-zero 목표부터 분·시간 |

이전 양언어판의 시간 범위는 서로 다른 예시였습니다. 이 모델은 설계 선택을 정리하며 높은 단계가 항상 빠르다는 인증·보장이 아닙니다. 사용자 흐름·의존성별 실제 목표를 정하고 측정합니다.

Regional EKS control plane은 3개 AZ에 분산됩니다. 현재 endpoint SLA는 Standard 월 99.95%·5분 측정 간격, Provisioned 월 99.99%·1분 간격입니다. 조건이 있는 service-credit 약정이며 앱 SLO·RTO·RPO 보장이 아닙니다. [AWS EKS SLA](https://aws.amazon.com/eks/sla/)


> 모든 서비스가 Level 4를 필요로 하지는 않습니다. SLA 요구사항, 규정 준수 요건, 예산에 따라 적절한 수준을 선택하세요.

### Level 1: 기본 복원력 (Pod-level)

가장 기본적인 복원력 수준으로, 단일 Pod 장애에 대응합니다.

#### Liveness/Readiness/Startup Probes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
  namespace: resilience-demo
spec:
  replicas: 3
  selector:
    matchLabels:
      app: web-app
  template:
    metadata:
      labels:
        app: web-app
    spec:
      terminationGracePeriodSeconds: 60
      containers:
      - name: app
        image: registry.example.com/team/web-app:replace-with-reviewed-digest
        ports:
        - name: http
          containerPort: 8080
        startupProbe:
          httpGet:
            path: /healthz
            port: http
          failureThreshold: 30
          periodSeconds: 10
        livenessProbe:
          httpGet:
            path: /healthz
            port: http
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /ready
            port: http
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 3
        lifecycle:
          preStop:
            sleep:
              seconds: 5
        resources:
          requests:
            cpu: 250m
            memory: 256Mi
          limits:
            cpu: 500m
            memory: 512Mi
```

#### Resource와 Probe 전제

위 image는 공개 artifact가 아닌 앱 placeholder입니다. 배포 전 검증한 digest·실제 health path로 바꿉니다. startup은 초기 liveness·readiness를 억제하며, 외부 의존성 지연만으로 liveness가 실패하게 만들지 않습니다. resource·probe 값은 예시이며 모든 Job·init container에 같은 probe가 필요한 것은 아닙니다.

#### 기본 PodDisruptionBudget

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: web-app-pdb
  namespace: resilience-demo
spec:
  maxUnavailable: 1
  selector:
    matchLabels:
      app: web-app
```

---

PDB는 지원되는 자발적 eviction을 제한합니다. 3개 Ready·진행 중 차감 없음이면 maxUnavailable=1로 한 번 허용하지만, AZ·hardware 장애, 직접 Pod 삭제, Deployment 자체 rollout·scale-down의 Pod 수를 보장하지 않습니다. minAvailable 2는 고정 3 replica의 대안이며 한 필드만 선택합니다.

퍼센트는 올림합니다. 8×25%=2, 3×25%는 ceil(0.75)=1이며, 3 replica의 minAvailable 75%는 ceil(2.25)=3으로 정상 Pod eviction 여유가 없습니다. 실제 health·진행 중 disruption을 확인합니다.

## Multi-AZ 전략 (Level 2)

Multi-AZ 전략은 가용 영역(AZ) 장애에 대비하여 워크로드를 여러 AZ에 분산 배치합니다.

### Pod Topology Spread Constraints

배치에 영향을 주지만 건강한 용량을 생성하거나 장애 후 기존 Pod를 자동 이동시키지는 않습니다.

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
        minDomains: 2                           # N-1 예시의 eligible-domain 하한; 용량·배치 별도 확인
      containers:
      - name: app
        image: registry.example.com/team/web-app:replace-with-reviewed-digest
```

#### Soft Constraint (선호 분산)

이 기준은 선호도이며 resource·taint·affinity·storage 등 다른 조건을 만족해야 스케줄링됩니다.

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
        image: registry.example.com/team/web-app:replace-with-reviewed-digest
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
        image: registry.example.com/team/web-app:replace-with-reviewed-digest
```

| 파라미터 | 설명 |
|---------|------|
| `maxSkew` | DoNotSchedule에서 후보 domain count와 global minimum의 허용 차이 |
| `topologyKey` | 분산 기준 노드 레이블 (zone, hostname 등) |
| `whenUnsatisfiable` | `DoNotSchedule` (Hard) 또는 `ScheduleAnyway` (Soft) |
| `minDomains` | eligible domain이 더 적으면 global minimum을 0으로 계산 |

eligible zone이 두 개이고 각각 Pod 2개라면 minDomains=3은 global minimum=0으로 maxSkew=1의 replacement를 막을 수 있습니다. minDomains=2는 다른 조건·용량이 충족될 때 배치 계산을 허용합니다. 정확히 2·3개 AZ 점유를 요구하는 값이 아닙니다. 초기 3-AZ 배치와 잔여 AZ headroom을 따로 검증합니다.

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
    - nodes: "20%"                    # 해당 자발적 budget: 올림 후 deleting·NotReady 차감
    - nodes: "0"                      # UTC 00–09 = 한국·일본 09–18; 모든 장애를 막지는 않음
      schedule: "0 0 * * MON-FRI"
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
  weight: 50  # 낮은 provisioning 선호도; Spot 불가 때만이라는 보장은 없음
```

zone requirement는 허용 위치이며 균등 node 생성·장애 headroom 예약이 아닙니다. EKS와 호환되는 Karpenter를 선택합니다. schema 기준은 유지 관리되는 1.14.1이며 과거 1.0+가 모든 현재 cluster에 충분하다는 뜻은 아닙니다. EC2NodeClass·AMI·role·subnet·capacity를 준비해야 합니다.

퍼센트 budget은 ceil(total×percentage)에서 deleting·NotReady를 차감하고 적용 budget 중 가장 엄격한 값을 사용합니다. 모든 interruption·expiration·repair·수동 삭제를 제한하지 않습니다. schedule은 UTC이며 예시는 한국·일본 평일 09–18시 블록입니다. 과거 매시간 9–18 시작·9시간 duration은 중첩되어 의도한 한 업무 시간대가 아니었습니다.

Spot/On-Demand weight 100/50은 provisioning 선호도이지 낮은 weight가 Spot 불가 때만 쓰인다는 보장이 아닙니다. 기존 용량·조건·batching도 영향을 주며 NodePool limit는 pre-scaling이 아닌 상한입니다.

### 같은 Zone Service 선호도

```yaml
apiVersion: v1
kind: Service
metadata:
  name: web-app
  namespace: resilience-demo
spec:
  selector:
    app: web-app
  ports:
  - name: http
    port: 80
    targetPort: http
  trafficDistribution: PreferSameZone
```

PreferSameZone·PreferSameNode는 1.35부터 GA이며 1.36 기준에서 유효합니다. PreferClose는 이전 alias입니다. 엄격한 locality·latency·cost 보장이 아닌 선호이며 실제 proxy·EndpointSlice와 Local traffic policy를 확인합니다. topology-mode=Auto는 다른 hint 할당 방식이고 topology-aware-hints는 legacy 설명입니다.

출처: [PDB](https://kubernetes.io/docs/tasks/run-application/configure-pdb/), [Pod 종료](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/), [topology spread](https://kubernetes.io/docs/concepts/scheduling-eviction/topology-spread-constraints/), [Service traffic distribution](https://kubernetes.io/docs/concepts/services-networking/service/#traffic-distribution), [Karpenter disruption](https://karpenter.sh/docs/concepts/disruption/).

### ARC Zonal Shift

수동 zonal shift와 자동 zonal autoshift는 별도 동작입니다. EKS 연동은 해당 AZ node를 cordon하고 EndpointSlice에서 endpoint를 제외하며 Pod eviction·node termination을 하지는 않습니다. Auto Mode는 해당 AZ 신규 node와 관련 자발적 disruption을 멈추고, managed node group은 AZ rebalancing을 중지하며 신규 node를 건강한 AZ에 배치합니다. 현재 Karpenter 연동에는 문서의 version·설정·IAM 준비가 필요합니다. Load balancer shift는 별도 resource 작업입니다.

먼저 계정·정확한 managed resource·연동 활성화·기존 practice 설정·alarm 동작을 확인합니다. 잔여 AZ의 앱·DNS·data·node 용량을 검증합니다. 모든 service endpoint가 장애 AZ에 있을 때 EKS fail-safe가 있으므로 절대적인 network 차단이 아니며 기존 zonal EBS를 이동시키지 않습니다. 순수 Auto Mode DNS는 node system service이고 혼합·non-Auto node에는 CoreDNS Deployment 용량이 필요합니다.

```bash
set -euo pipefail
: "${AWS_REGION:?Set the resource region}"
: "${ARC_RESOURCE_ARN:?Set the exact owned EKS cluster or eligible load-balancer ARN}"
aws sts get-caller-identity
aws arc-zonal-shift get-managed-resource \
  --region "$AWS_REGION" --resource-identifier "$ARC_RESOURCE_ARN"
```
다음 블록은 하나의 일괄 설치 스크립트가 아닌 별도 운영 단계입니다. Practice 설정은 정기적인 실제 traffic 변경을 시작합니다. 기존 설정이 있으면 재생성 대신 검토합니다. Outcome alarm identifier는 alarmName/region 객체가 아닌 ARN 문자열이며 준비 후 autoshift를 별도 활성화합니다.

```bash
# MUTATION: authorizes recurring weekly traffic-shifting practice runs.
: "${OUTCOME_ALARM_ARN:?Set the reviewed CloudWatch alarm ARN in the resource region}"
aws arc-zonal-shift create-practice-run-configuration \
  --region "$AWS_REGION" --resource-identifier "$ARC_RESOURCE_ARN" \
  --outcome-alarms "alarmIdentifier=$OUTCOME_ALARM_ARN,type=CLOUDWATCH"
```
```bash
# MUTATION: enable automatic shifts only after the readiness review.
aws arc-zonal-shift update-zonal-autoshift-configuration \
  --region "$AWS_REGION" --resource-identifier "$ARC_RESOURCE_ARN" \
  --zonal-autoshift-status ENABLED
```
```bash
# MUTATION: a separate, manually initiated one-hour shift.
set -euo pipefail
: "${AWAY_FROM_AZ:?Set an AZ of this resource}"
SHIFT_ID=$(aws arc-zonal-shift start-zonal-shift \
  --region "$AWS_REGION" --resource-identifier "$ARC_RESOURCE_ARN" \
  --away-from "$AWAY_FROM_AZ" --expires-in 1h \
  --comment "Owned resilience exercise" --query zonalShiftId --output text)
test -n "$SHIFT_ID" && test "$SHIFT_ID" != None
printf '%s\n' "$SHIFT_ID" > owned-zonal-shift-id.txt
```
```bash
# MUTATION: cancel only the recorded manual shift after checking its ownership.
: "${SHIFT_ID:?Use the exact ID recorded for this exercise}"
aws arc-zonal-shift cancel-zonal-shift \
  --region "$AWS_REGION" --zonal-shift-id "$SHIFT_ID"
```
[EKS ARC behavior and prerequisites](https://docs.aws.amazon.com/eks/latest/userguide/zone-shift.html) · [Auto Mode/Karpenter integration](https://aws.amazon.com/blogs/containers/arc-zonal-shift-support-for-eks-auto-mode-and-karpenter/)

### 스토리지 고려사항

WaitForFirstConsumer는 scheduler 배치를 고려할 수 있을 때까지 초기 provisioning·binding을 늦춥니다. **EBS는 계속 AZ에 묶입니다.** AZ 장애 후 다른 AZ의 replacement Pod가 같은 volume을 attach할 수 없습니다. Backup·복제 기반 data 복구·이전과 RPO·RTO를 검증합니다.

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: resilience-ebs
provisioner: ebs.csi.aws.com
volumeBindingMode: WaitForFirstConsumer
parameters:
  type: gp3
  encrypted: 'true'
allowVolumeExpansion: true
reclaimPolicy: Retain
```
위 예제는 표준 EBS CSI driver입니다. Auto Mode는 ebs.csi.eks.amazonaws.com과 별도 node·IAM·migration 전제를 사용합니다. 어느 설계든 encrypted: "true"를 명시하고 생성 EBS·KMS key를 확인합니다. Auto Mode node root/data disk 암호화가 모든 workload PVC의 암호화를 뜻하지 않습니다. 현재 Auto Mode StorageClass parameter 기본값은 false입니다. Retain은 통제된 복구·정리를 위해 released volume을 보존하지만 backup이 아니며 비용이 남을 수 있습니다.

Cross-AZ 공유 filesystem은 기존 **Regional** EFS, 접근 가능한 mount target, TCP 2049 보안 규칙, access-point 권한·CSI IAM 전제가 필요합니다. EFS One Zone은 같은 복원력 설계가 아닙니다. ID는 placeholder이며 여기서 filesystem을 생성하지 않습니다.

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: resilience-efs
provisioner: efs.csi.aws.com
parameters:
  provisioningMode: efs-ap
  fileSystemId: fs-0123456789abcdef0
  directoryPerms: '700'
  basePath: /resilience-demo
reclaimPolicy: Retain
mountOptions:
- tls
```
```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: efs-claim
  namespace: resilience-demo
spec:
  accessModes:
  - ReadWriteMany
  storageClassName: resilience-efs
  resources:
    requests:
      storage: 5Gi
```
PVC의 5Gi 요청은 EFS가 강제하는 저장 quota가 아닙니다. TLS mount 암호화와 filesystem at-rest 암호화는 별도이며 Retain이면 access-point·data 정리 절차도 필요합니다.

[EKS EBS CSI](https://docs.aws.amazon.com/eks/latest/userguide/ebs-csi.html) · [Auto Mode StorageClass parameters](https://docs.aws.amazon.com/eks/latest/userguide/create-storage-class.html) · [EFS CSI](https://github.com/kubernetes-sigs/aws-efs-csi-driver)

### Istio Locality-Aware Routing

이 Istio sidecar-mode 예시는 문서화된 locality override가 없으면 Pod가 실행되는 node에서 locality를 읽습니다. 일반 Pod zone label이 자동으로 locality를 정의하지 않습니다. 실제 proxy endpoint·locality·건강한 잔여 용량을 확인합니다. 문서의 locality failover에는 outlier detection이 필요합니다.

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: web-app-locality
  namespace: resilience-demo
spec:
  host: web-app.resilience-demo.svc.cluster.local
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 100
    loadBalancer:
      simple: ROUND_ROBIN
      localityLbSetting:
        enabled: true
    outlierDetection:
      consecutive5xxErrors: 5
      interval: 10s
      baseEjectionTime: 30s
      maxEjectionPercent: 50
```
**가중 분산 대안 설정**은 loadBalancer의 localityLbSetting을 다음 fragment로 교체합니다. 세 source zone을 모두 포함하며 80/10/10은 설정 weight이지 실측 locality·failover 용량 보장이 아닙니다. 호환되지 않는 failover policy와 distribute를 동시에 조합하지 않습니다.

```yaml
localityLbSetting:
  enabled: true
  distribute:
  - from: ap-northeast-2/ap-northeast-2a/*
    to:
      ap-northeast-2/ap-northeast-2a/*: 80
      ap-northeast-2/ap-northeast-2b/*: 10
      ap-northeast-2/ap-northeast-2c/*: 10
  - from: ap-northeast-2/ap-northeast-2b/*
    to:
      ap-northeast-2/ap-northeast-2a/*: 10
      ap-northeast-2/ap-northeast-2b/*: 80
      ap-northeast-2/ap-northeast-2c/*: 10
  - from: ap-northeast-2/ap-northeast-2c/*
    to:
      ap-northeast-2/ap-northeast-2a/*: 10
      ap-northeast-2/ap-northeast-2b/*: 10
      ap-northeast-2/ap-northeast-2c/*: 80
```
기존 80%+ local traffic, 60–80% 비용 절감, 동일 AZ <1ms 수치는 출처 확인이 안 된 예시로만 보존합니다. Health·connection reuse·endpoint 구성·전송량·가격에 따라 실제 결과가 달라집니다.

[Locality failover](https://istio.io/latest/docs/tasks/traffic-management/locality-load-balancing/failover/) · [Weighted distribution](https://istio.io/latest/docs/tasks/traffic-management/locality-load-balancing/distribute/)

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

Namespace·quota·NetworkPolicy는 논리적 경계이며 독립 장애 영역이 아닙니다. Node·control plane·CNI·DNS·router·data service 공유가 남습니다. Network plugin의 policy enforcement와 모든 적용 policy의 허용 합집합을 확인합니다. 아래 router namespace·workload는 정확한 label로 존재해야 합니다.

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: cell-1
  labels:
    cell: '1'
    customer-range: a-f
```
```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: cell-1-quota
  namespace: cell-1
spec:
  hard:
    requests.cpu: '20'
    requests.memory: 40Gi
    limits.cpu: '40'
    limits.memory: 80Gi
    pods: '100'
    services: '20'
    persistentvolumeclaims: '50'
```
```yaml
apiVersion: v1
kind: LimitRange
metadata:
  name: cell-1-limits
  namespace: cell-1
spec:
  limits:
  - default:
      cpu: 500m
      memory: 512Mi
    defaultRequest:
      cpu: 100m
      memory: 128Mi
    type: Container
```
```yaml
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
  - from:
    - podSelector: {}
  - from:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: cell-router
      podSelector:
        matchLabels:
          app: cell-router
    ports:
    - protocol: TCP
      port: 8080
  egress:
  - to:
    - podSelector: {}
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: kube-system
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - protocol: UDP
      port: 53
    - protocol: TCP
      port: 53
```
DNS는 kube-system의 일치하는 CoreDNS Pod로 TCP·UDP를 허용합니다. Node-local·Auto Mode system DNS는 경로가 달라 mode별 검증이 필요합니다. 임의 외부 traffic은 허용하지 않으므로 필요한 endpoint·egress gateway 규칙을 별도 검토합니다. 0.0.0.0/0에서 10.0.0.0/8만 제외해도 모든 private network·cell이 격리되지는 않습니다.

[NetworkPolicy semantics](https://kubernetes.io/docs/concepts/services-networking/network-policies/)

### Cluster 기반 Cell 구현

별도 cluster는 control-plane·node 경계를 강화하지만 IAM·account quota·region·공유 data·router 의존성은 남을 수 있습니다. Cell별 context·계정·region·용량·배포·data owner inventory를 먼저 정의하고 [cluster 생성 가이드](02-eks-cluster-creation.md)의 검토된 절차를 적용합니다. 여러 운영 cluster를 과거 버전으로 즉시 생성하는 loop는 이 설계의 전제가 아닙니다.

### Shuffle Sharding

Shuffle Sharding은 각 고객을 여러 셀 중 일부에만 할당하여 장애 영향을 제한합니다.

**Shuffle Sharding의 장점 (8개 셀에서 2개 선택):**

- 가능한 조합 수: C(8,2) = 28개
- 독립 균등 할당에서 고정한 단일 셀을 포함하는 assignment의 기대 비율: 25% (2/8), 최대 고객·부하 비율이 아님
- 독립 균등 할당한 두 고객의 완전 동일 조합 확률: 1/28 (약 3.6%)

```
8개 Cell 풀에서 2개 Cell 조합:
- 고객 A -> Cell 1, Cell 5
- 고객 B -> Cell 2, Cell 7
- 고객 C -> Cell 1, Cell 3

Cell 1 장애 시:
- 고객 A -> routing·data·capacity 준비 시 Cell 5 사용 가능
- 고객 B -> 영향 없음
- 고객 C -> routing·data·capacity 준비 시 Cell 3 사용 가능
```

```yaml
# 라우터가 소비하도록 구현해야 하는 예시 data; ConfigMap 자체가 failover를 구현하지 않음
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

사용자 흐름·data consistency 요구별 패턴을 선택합니다. 두 번째 cluster·region만으로 near-zero RTO·RPO가 보장되지는 않습니다. 아래 기존 시간·비용 수치는 검증하지 못한 설계 예시이며 실측·AWS 약정이 아닙니다.

| Pattern | Earlier RTO illustration | Earlier RPO illustration | Earlier cost illustration | Design condition |
| --- | --- | --- | --- | --- |
| Active-Active | ~0 target | ~0 target | 2x+ | Routing, consistency, conflict handling and capacity |
| Active-Passive | Minutes–hours | Minutes | 1.5x | Standby readiness, replication lag and promotion |
| Regional Isolation | Not specified | Not specified | 1x per region | Independent regional service; not automatic regional failover |
| Hub-Spoke | Minutes | Minutes | 1.3x | Hub is a shared dependency unless separately protected |

### Argo CD ApplicationSet

세 대안은 기존 Argo CD·ApplicationSet controller, label을 갖춘 명시적으로 등록된 접근 가능한 cluster, repository credential, repo·destination·resource kind를 제한한 사전 AppProject가 필요합니다. 예제 repo·revision은 소유 값으로 바꿉니다. 생성 Application은 수동 sync이며 자동 sync·prune 전에 대상·manifest를 검토합니다. Generator가 EKS cluster를 생성하지는 않습니다.

#### Cluster generator

```yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: resilience-clusters
  namespace: argocd
spec:
  goTemplate: true
  goTemplateOptions:
  - missingkey=error
  generators:
  - clusters:
      selector:
        matchLabels:
          resilience-example: 'true'
  template:
    metadata:
      name: web-app-{{.nameNormalized}}
    spec:
      project: resilience-reviewed
      source:
        repoURL: https://github.com/example/owned-gitops.git
        targetRevision: REPLACE_WITH_REVIEWED_COMMIT
        path: apps/web-app/overlays/{{.metadata.labels.region}}
      destination:
        server: '{{.server}}'
        namespace: resilience-demo
```
#### Git directories × registered clusters

```yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: resilience-region-directories
  namespace: argocd
spec:
  goTemplate: true
  goTemplateOptions:
  - missingkey=error
  generators:
  - matrix:
      generators:
      - git:
          repoURL: https://github.com/example/owned-gitops.git
          revision: REPLACE_WITH_REVIEWED_COMMIT
          directories:
          - path: regions/*
      - clusters:
          selector:
            matchLabels:
              resilience-example: 'true'
              region: '{{.path.basename}}'
  template:
    metadata:
      name: '{{.nameNormalized}}-{{.path.basename}}'
    spec:
      project: resilience-reviewed
      source:
        repoURL: https://github.com/example/owned-gitops.git
        targetRevision: REPLACE_WITH_REVIEWED_COMMIT
        path: '{{.path.path}}'
      destination:
        server: '{{.server}}'
        namespace: resilience-demo
```
두 번째 matrix child는 directory basename과 등록 cluster label을 일치시키고 실제 server 값을 사용합니다. Region명으로 EKS API URL을 만들 수 없습니다. Label이 없거나 불일치하면 Application이 없을 수 있으므로 schema뿐 아니라 생성 결과를 확인합니다.

#### Cluster × application list

```yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: resilience-cluster-app-matrix
  namespace: argocd
spec:
  goTemplate: true
  goTemplateOptions:
  - missingkey=error
  generators:
  - matrix:
      generators:
      - clusters:
          selector:
            matchLabels:
              resilience-example: 'true'
      - list:
          elements:
          - app: frontend
            port: '80'
          - app: backend
            port: '8080'
          - app: worker
            port: '9090'
  template:
    metadata:
      name: '{{.nameNormalized}}-{{.app}}'
    spec:
      project: resilience-reviewed
      source:
        repoURL: https://github.com/example/owned-gitops.git
        targetRevision: REPLACE_WITH_REVIEWED_COMMIT
        path: apps/{{.app}}
        helm:
          parameters:
          - name: cluster.name
            value: '{{.name}}'
          - name: service.port
            value: '{{.port}}'
      destination:
        server: '{{.server}}'
        namespace: resilience-demo
```
[ApplicationSet matrix parameters](https://argo-cd.readthedocs.io/en/stable/operator-manual/applicationset/Generators-Matrix/)

### Global Accelerator

TLS·health check·리전별 용량을 검증한 기존 ALB/NLB endpoint를 사용합니다. 아래는 실행하지 않은 선택적 provisioning 예시입니다. 반환 ID·소유 자원 정리 계획을 저장하며 중간 실패가 이미 생성한 자원을 삭제하지는 않습니다. Accelerator 비활성화만으로 비용이 없어지지 않습니다.

```bash
# MUTATIONS: creates a disabled, billable accelerator and its configuration.
set -euo pipefail
: "${GA_API_REGION:?Set the documented Global Accelerator API region}"
: "${ACCELERATOR_NAME:?Set a unique owned name}"
: "${REGION_ONE:?Set the first endpoint region}"
: "${REGION_TWO:?Set the second endpoint region}"
: "${REGION_ONE_LB_ARN:?Set the reviewed eligible ALB/NLB ARN}"
: "${REGION_TWO_LB_ARN:?Set the reviewed eligible ALB/NLB ARN}"
test "$REGION_ONE" != "$REGION_TWO"
ACCELERATOR_ARN=$(aws globalaccelerator create-accelerator \
  --region "$GA_API_REGION" --name "$ACCELERATOR_NAME" \
  --ip-address-type IPV4 --no-enabled --query Accelerator.AcceleratorArn --output text)
test -n "$ACCELERATOR_ARN" && test "$ACCELERATOR_ARN" != None
LISTENER_ARN=$(aws globalaccelerator create-listener \
  --region "$GA_API_REGION" --accelerator-arn "$ACCELERATOR_ARN" \
  --protocol TCP --port-ranges FromPort=443,ToPort=443 \
  --query Listener.ListenerArn --output text)
test -n "$LISTENER_ARN" && test "$LISTENER_ARN" != None
aws globalaccelerator create-endpoint-group \
  --region "$GA_API_REGION" --listener-arn "$LISTENER_ARN" \
  --endpoint-group-region "$REGION_ONE" --traffic-dial-percentage 100 \
  --endpoint-configurations "EndpointId=$REGION_ONE_LB_ARN,Weight=100"
aws globalaccelerator create-endpoint-group \
  --region "$GA_API_REGION" --listener-arn "$LISTENER_ARN" \
  --endpoint-group-region "$REGION_TWO" --traffic-dial-percentage 100 \
  --endpoint-configurations "EndpointId=$REGION_TWO_LB_ARN,Weight=100"
```
```bash
# MUTATION: run separately after endpoint health, routing, data and rollback checks.
: "${ACCELERATOR_ARN:?Use the accelerator just reviewed}"
aws globalaccelerator update-accelerator \
  --region "$GA_API_REGION" --accelerator-arn "$ACCELERATOR_ARN" --enabled
```
Traffic dial은 해당 regional endpoint group으로 이미 배정된 traffic 중 신규 connection의 비율입니다. 두 region을 50%로 설정해도 전 세계 50/50 분산이 되지 않으며 예시는 둘 다 100%입니다. Dial 변경이 기존 연결을 강제 이동시키지 않고 failover 규칙은 0 dial을 무시할 수 있습니다. Endpoint weight와도 다릅니다. ALB·NLB endpoint health는 ELB health check를 따르므로 Global Accelerator의 /healthz 값으로 target-group check를 설정할 수 없습니다.

[Traffic dial semantics](https://docs.aws.amazon.com/global-accelerator/latest/dg/about-endpoint-groups-traffic-dial.html) · [Endpoint health](https://repost.aws/knowledge-center/global-accelerator-unhealthy-endpoints) · [Failover rules](https://repost.aws/knowledge-center/global-accelerator-failover-different-region)

### Istio Multi-Primary Federation

Sidecar multi-primary·multiple-network 설계에는 신뢰하는 identity 체계, 고유 cluster·network명, remote Kubernetes API·east-west gateway 접근성, 일치하는 service·namespace와 data 동작이 필요합니다. ServiceEntry만으로 federation이 되지 않습니다. Gateway는 의도한 network만 접근하게 하며 Layer-7 TLS 종료 LB는 AUTO_PASSTHROUGH와 호환되지 않습니다.

다음 IstioOperator는 **istioctl 설치 입력**이며 kubectl apply할 in-cluster operator가 아닙니다. Tokyo 대응 설정과 공식 gateway·discovery 절차 전체를 준비합니다. DNS capture·auto-allocation flag는 이를 대체하지 않습니다.

```yaml
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  values:
    global:
      meshID: resilience-mesh
      multiCluster:
        clusterName: cluster-seoul
      network: network-seoul
```
```bash
# MUTATIONS: source-cluster credentials/RBAC and destination Secret may be created.
set -euo pipefail
umask 077
: "${SEOUL_CONTEXT:?Verify the owned Seoul context}"
: "${TOKYO_CONTEXT:?Verify the owned Tokyo context}"
test "$SEOUL_CONTEXT" != "$TOKYO_CONTEXT"
test ! -e tokyo-remote-secret.yaml && test ! -e seoul-remote-secret.yaml
istioctl create-remote-secret --context "$TOKYO_CONTEXT" --name cluster-tokyo > tokyo-remote-secret.yaml
istioctl create-remote-secret --context "$SEOUL_CONTEXT" --name cluster-seoul > seoul-remote-secret.yaml
# Inspect Secret metadata without printing token data; verify destination contexts first.
kubectl --context "$SEOUL_CONTEXT" -n istio-system apply -f tokyo-remote-secret.yaml
kubectl --context "$TOKYO_CONTEXT" -n istio-system apply -f seoul-remote-secret.yaml
```
Remote-secret 파일은 credential을 포함하므로 비공개로 보관하고 source control에서 제외하며 설치 후 정책에 따라 로컬 사본을 정리합니다. 위 명령은 신뢰·network 설정 이후의 변경 작업이며 read-only 진단이 아닙니다.

명시적 routing subset은 각 cluster의 **Pod template에 직접 설정한 workload-region label**을 사용합니다. Node topology label이 Pod에 자동 복사되지 않습니다. x-region은 routing 입력이지 authorization이 아니며 80/20 weight도 data failover protocol을 구현하지 않습니다.

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: cross-cluster-routing
  namespace: resilience-demo
spec:
  hosts:
  - web-app.resilience-demo.svc.cluster.local
  http:
  - match:
    - headers:
        x-region:
          exact: tokyo
    route:
    - destination:
        host: web-app.resilience-demo.svc.cluster.local
        subset: tokyo
  - route:
    - destination:
        host: web-app.resilience-demo.svc.cluster.local
        subset: seoul
      weight: 80
    - destination:
        host: web-app.resilience-demo.svc.cluster.local
        subset: tokyo
      weight: 20
```
```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: cross-cluster-subsets
  namespace: resilience-demo
spec:
  host: web-app.resilience-demo.svc.cluster.local
  subsets:
  - name: seoul
    labels:
      workload-region: ap-northeast-2
  - name: tokyo
    labels:
      workload-region: ap-northeast-1
```
별도 외부 DNS service는 아래 ServiceEntry로 registry entry를 표현할 수 있습니다. 자체 DNS·TLS·앱 전제를 갖는 외부 service 대안이며 다른 cluster의 Kubernetes service discovery를 구현하지 않습니다.

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: reviewed-remote-service
  namespace: resilience-demo
spec:
  hosts:
  - remote-service.example.com
  location: MESH_EXTERNAL
  ports:
  - number: 443
    name: https
    protocol: TLS
  resolution: DNS
```
[Full Istio multi-primary prerequisites and steps](https://istio.io/latest/docs/setup/install/multicluster/multi-primary_multi-network/)

---

## 애플리케이션 복원력 패턴

### PodDisruptionBudgets

PDB는 지원 eviction 경로를 제한하며 모든 자발적·비자발적 중단이나 controller rollout을 보장하지 않습니다. 다음은 대안 예시이므로 같은 workload에 모두 적용하지 않습니다.

#### minAvailable 방식

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: app-pdb-min
  namespace: resilience-demo
spec:
  minAvailable: 2  # 지원 eviction 뒤 필요한 Ready Pod 수
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
  namespace: resilience-demo
spec:
  maxUnavailable: 1  # 이미 비정상·진행 중인 disruption을 포함한 eviction budget
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
  namespace: resilience-demo
spec:
  minAvailable: "75%"  # 75% 이상 Pod 유지
  selector:
    matchLabels:
      app: my-app
```

```bash
# PDB 목록 및 상태 확인
kubectl --context "$KUBE_CONTEXT" -n resilience-demo get pdb

# 상세 정보 확인
kubectl --context "$KUBE_CONTEXT" -n resilience-demo describe pdb app-pdb-min

# 출력 예시:
# Name:           app-pdb-min
# Min available:  2
# Selector:       app=my-app
# Status:
#     Allowed disruptions:  1
#     Current:              3
#     Desired:              2  # minAvailable=2; illustrative, not observed output
#     Total:                3
```

### Graceful Shutdown

Pod 종료 시 진행 중인 요청을 완료하고 안전하게 종료하는 패턴입니다.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: graceful-app
  namespace: resilience-demo
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
        image: registry.example.com/team/web-app:replace-with-reviewed-digest
        ports:
        - containerPort: 8080
        lifecycle:
          preStop:
            sleep:
              seconds: 5  # 지원 API 기준의 지연이며 전파 보장이 아님
        readinessProbe:
          httpGet:
            path: /ready
            port: 8080
          periodSeconds: 5
```

**Graceful Shutdown 흐름:**

grace period에는 preStop 시간이 포함됩니다. native sleep은 1.34부터 GA이며 5초 대기는 endpoint·LB 전파 보장이 아닙니다. EndpointSlice 종료 갱신과 node shutdown은 병렬이며 endpoint가 ready=false·serving 상태로 남아 있을 수 있습니다.

hook 뒤 runtime이 설정된 stop signal(보통 SIGTERM)을 보내며 image·runtime 설정에 따라 달라질 수 있습니다. 앱은 signal을 처리하고 남은 시간 안에 작업을 마치거나 거부해야 합니다. preStop에서 PID 1을 수동 종료해 엄격한 endpoint 제거 순서를 가정하지 않습니다. 실제 연결·deregistration·data flush를 테스트합니다.

### Circuit Breaker via Istio

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: backend-circuit-breaker
  namespace: resilience-demo
spec:
  host: backend-service.resilience-demo.svc.cluster.local
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 100
        connectTimeout: 3s
      http:
        http1MaxPendingRequests: 100
        http2MaxRequests: 1000
        maxRequestsPerConnection: 10
        maxRetries: 3
    outlierDetection:
      consecutive5xxErrors: 5
      consecutiveGatewayErrors: 5
      interval: 10s
      baseEjectionTime: 30s
      maxEjectionPercent: 50
      minHealthPercent: 30
      splitExternalLocalOriginErrors: true
```
이 제한은 설정한 proxy·destination pool 기준이며 cluster 전체 동시성 상한이 아닙니다. http2MaxRequests는 활성 HTTP 요청을 제한하고 maxRetries는 요청별 횟수가 아닌 **동시에 진행 중인 retry 수**입니다. minHealthPercent는 outlier detection 활성 조건이지 그 비율의 건강한 용량 보장이 아닙니다. Error ejection·연결 제한·retry는 측정 기반 조정이 필요합니다.

### Retry/Timeout

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: backend-retry-timeout
  namespace: resilience-demo
spec:
  hosts:
  - backend-service.resilience-demo.svc.cluster.local
  http:
  - match:
    - method:
        exact: GET
    route:
    - destination:
        host: backend-service.resilience-demo.svc.cluster.local
    timeout: 10s
    retries:
      attempts: 3
      perTryTimeout: 3s
      retryOn: 5xx,reset,connect-failure
      retryRemoteLocalities: true
```
GET 전용 route도 앱이 해당 요청을 안전하게 재시도할 수 있다는 전제입니다. attempts 3은 원 요청 이후 최대 3 retry지만 전체 10초·시도별 3초·backoff·동시성 제한 때문에 모든 시도가 실행되지는 않을 수 있습니다. Retry는 과부하·중복 부작용을 키울 수 있고 write는 명시적 idempotency contract가 필요합니다. retryRemoteLocalities는 대안 허용이지 건강한 원격 용량 보장이 아닙니다. Envoy retriable-4xx는 현재 **409만** 의미하며 408은 포함하지 않습니다. Optimistic-lock 충돌은 같은 요청 반복 대신 state 재조회가 필요할 수 있습니다.

[Istio DestinationRule](https://istio.io/latest/docs/reference/config/networking/destination-rule/) · [Envoy retry conditions](https://www.envoyproxy.io/docs/envoy/latest/configuration/http/http_filters/router_filter)

---

## 카오스 엔지니어링

카오스 엔지니어링은 통제된 fault로 반증 가능한 정상 상태 가설을 검증합니다. 소유한 대표 test 환경에서 시작하고 production은 영향 범위·권한·telemetry·중단 조건·복구를 별도 검토합니다. CR 적용이 fault를 실행할 수 있습니다. 여기서는 설정을 offline 검증했으며 실행·운영 준비 완료를 주장하지 않습니다.

```bash
# Read-only: verify the exact cluster/namespace and opt-in test workload.
: "${KUBE_CONTEXT:?Set the owned test context}"
kubectl --context "$KUBE_CONTEXT" -n resilience-demo get pods \
  -l 'app=web-app,experiment-approved=true' -o wide
kubectl --context "$KUBE_CONTEXT" -n resilience-demo get pdb
```
### AWS Fault Injection Service (FIS)

공식 guide의 IAM experiment role·trust policy, EKS access entry(또는 문서화된 legacy mapping), namespace 내 Kubernetes ServiceAccount·Role·RoleBinding, action별 EC2·network 권한을 준비합니다. 아래 role·alarm ARN은 한 region·account의 placeholder이며 모두 일관되게 교체합니다. Alarm은 실제 존재하고 의미 있는 data를 받아 동작이 검증되어야 합니다. Stop condition은 data restore나 무영향 보장이 아닙니다.

Pod target은 clusterIdentifier·namespace·selector로 식별합니다. **aws:eks:pod의 resourceArns에 cluster ARN을 넣을 수 없습니다.** Action에는 kubernetesServiceAccount가 필요합니다. 직접 Pod 삭제이므로 PDB가 삭제를 막지 않습니다. COUNT(1)은 opt-in 집합에서 하나를 선택하며 AZ 장애를 재현하지 않습니다.

#### One Pod deletion

```json
{
  "description": "Delete one selected test Pod; not an AZ outage",
  "targets": {
    "test-pod": {
      "resourceType": "aws:eks:pod",
      "selectionMode": "COUNT(1)",
      "parameters": {
        "clusterIdentifier": "REPLACE_WITH_OWNED_TEST_CLUSTER",
        "namespace": "resilience-demo",
        "selectorType": "labelSelector",
        "selectorValue": "app=web-app,experiment-approved=true"
      }
    }
  },
  "actions": {
    "delete-one": {
      "actionId": "aws:eks:pod-delete",
      "parameters": {
        "kubernetesServiceAccount": "fis-test",
        "maxErrorsPercent": "0"
      },
      "targets": {
        "Pods": "test-pod"
      }
    }
  },
  "stopConditions": [
    {
      "source": "aws:cloudwatch:alarm",
      "value": "arn:aws:cloudwatch:ap-northeast-2:123456789012:alarm:owned-resilience-stop"
    }
  ],
  "roleArn": "arn:aws:iam::123456789012:role/owned-fis-test"
}
```
#### One Pod network latency

```json
{
  "description": "Add bounded IPv4 latency to one selected test Pod",
  "targets": {
    "test-pod": {
      "resourceType": "aws:eks:pod",
      "selectionMode": "COUNT(1)",
      "parameters": {
        "clusterIdentifier": "REPLACE_WITH_OWNED_TEST_CLUSTER",
        "namespace": "resilience-demo",
        "selectorType": "labelSelector",
        "selectorValue": "app=web-app,experiment-approved=true"
      }
    }
  },
  "actions": {
    "latency": {
      "actionId": "aws:eks:pod-network-latency",
      "parameters": {
        "kubernetesServiceAccount": "fis-test",
        "duration": "PT1M",
        "delayMilliseconds": "200",
        "jitterMilliseconds": "50",
        "sources": "10.20.0.0/24",
        "maxErrorsPercent": "0"
      },
      "targets": {
        "Pods": "test-pod"
      }
    }
  },
  "stopConditions": [
    {
      "source": "aws:cloudwatch:alarm",
      "value": "arn:aws:cloudwatch:ap-northeast-2:123456789012:alarm:owned-resilience-stop"
    }
  ],
  "roleArn": "arn:aws:iam::123456789012:role/owned-fis-test"
}
```
예시 destination CIDR은 검토한 test 의존성으로 바꿉니다. Network action에는 privileged·root fault injection이 필요하며 Fargate·bridge network는 지원하지 않습니다. IPv4 대상이므로 ALL·IPv4 CIDR도 IPv6를 장애 처리하지 않습니다. 현재 readonly-root-filesystem·container 보안 제약을 확인하고 이 예제를 위해 production 보안을 낮추지 않습니다. FIS는 injector Pod를 사용하고 pod-delete 외 action은 ephemeral container를 사용합니다. Process 종료가 Pod spec의 변경 불가능한 ephemeral-container 기록을 지우지는 않습니다.

#### One subnet network disruption

```json
{
  "description": "One owned test subnet network disruption, not a complete AZ outage",
  "targets": {
    "test-subnet": {
      "resourceType": "aws:ec2:subnet",
      "selectionMode": "COUNT(1)",
      "resourceArns": [
        "arn:aws:ec2:ap-northeast-2:123456789012:subnet/subnet-0123456789abcdef0"
      ]
    }
  },
  "actions": {
    "network": {
      "actionId": "aws:network:disrupt-connectivity",
      "parameters": {
        "duration": "PT1M",
        "scope": "all"
      },
      "targets": {
        "Subnets": "test-subnet"
      }
    }
  },
  "stopConditions": [
    {
      "source": "aws:cloudwatch:alarm",
      "value": "arn:aws:cloudwatch:ap-northeast-2:123456789012:alarm:owned-resilience-stop"
    }
  ],
  "roleArn": "arn:aws:iam::123456789012:role/owned-fis-test"
}
```
무관한 workload가 없는 소유 test subnet만 사용합니다. 이 action은 NACL을 복제해 deny 규칙을 적용하고 완료 시 원래 association을 복원합니다. scope=all에서도 subnet 내부 traffic은 남으며 AZ 전체 전원 장애가 아닙니다. 시작 전 NACL quota·IAM·정확한 subnet·관리 및 telemetry 접근성을 검토합니다. Stop·복구는 비동기이므로 최종 experiment 상태와 실제 network·workload 복구를 확인합니다.

```bash
# MUTATION: stop only the recorded experiment ID, not all account experiments.
: "${AWS_REGION:?Set the experiment region}"
: "${EXPERIMENT_ID:?Set the exact running FIS experiment ID}"
aws fis stop-experiment --region "$AWS_REGION" --id "$EXPERIMENT_ID"
```
[FIS EKS Pod prerequisites/RBAC](https://docs.aws.amazon.com/fis/latest/userguide/eks-pod-actions.html) · [Action parameters and subnet behavior](https://docs.aws.amazon.com/fis/latest/userguide/fis-actions-reference.html)

### Litmus Chaos (CNCF Incubating)

검토한 3.31.0 operator CRD는 ChaosEngine·ChaosExperiment·ChaosResult이며 ChaosHub·ChaosSchedule은 정의하지 않습니다. 검토한 release, 각 ChaosExperiment, 제한한 RBAC, 검증한 runner·helper image를 먼저 준비합니다. 현재 catalog fault에는 CI·latest image 기본값이 있으므로 그대로 적용하지 않습니다. Schema 통과는 사용 cluster·runtime 호환성 증명이 아닙니다.

예시는 engineState: stop으로 시작합니다. 정확한 target 준비 후 설치 release의 workflow로 하나씩 검토합니다. Active engine은 duration 동안 반복 삭제할 수 있어 30초가 정확히 한 번 삭제를 뜻하지 않습니다. TARGET_PODS는 현재 name·UID로 Pod를 선택할 때까지 미완성 값으로 두며 공백이나 전체 production selector로 바꾸지 않습니다.

#### Pod deletion

```yaml
apiVersion: litmuschaos.io/v1alpha1
kind: ChaosEngine
metadata:
  name: pod-delete-review
  namespace: resilience-demo
spec:
  engineState: stop
  appinfo:
    appns: resilience-demo
    applabel: app=web-app,experiment-approved=true
    appkind: deployment
  chaosServiceAccount: pod-delete-sa
  experiments:
  - name: pod-delete
    spec:
      components:
        env:
        - name: TOTAL_CHAOS_DURATION
          value: '30'
        - name: CHAOS_INTERVAL
          value: '10'
        - name: FORCE
          value: 'false'
        - name: TARGET_PODS
          value: REPLACE_WITH_ONE_REVIEWED_POD_NAME
        - name: PODS_AFFECTED_PERC
          value: '100'
```
#### Node drain, not instance termination

```yaml
apiVersion: litmuschaos.io/v1alpha1
kind: ChaosEngine
metadata:
  name: node-drain-review
  namespace: resilience-demo
spec:
  engineState: stop
  appinfo:
    appns: resilience-demo
    applabel: app=web-app,experiment-approved=true
    appkind: deployment
  chaosServiceAccount: node-drain-sa
  experiments:
  - name: node-drain
    spec:
      components:
        env:
        - name: TOTAL_CHAOS_DURATION
          value: '60'
        - name: TARGET_NODE
          value: REPLACE_WITH_ONE_OWNED_TEST_NODE
```
Drain은 앱 selector 밖에서도 해당 node의 workload에 영향을 줍니다. 전용 test node·비어 있지 않은 정확한 이름·PDB를 고려한 eviction·복구 및 uncordon 계획이 필요합니다. 소유권 대신 kubernetes.io/os=linux 같은 범용 selector를 쓰지 않습니다. EC2 node termination 실험과 다릅니다.

#### DNS error

```yaml
apiVersion: litmuschaos.io/v1alpha1
kind: ChaosEngine
metadata:
  name: pod-dns-error-review
  namespace: resilience-demo
spec:
  engineState: stop
  appinfo:
    appns: resilience-demo
    applabel: app=web-app,experiment-approved=true
    appkind: deployment
  chaosServiceAccount: pod-dns-error-sa
  experiments:
  - name: pod-dns-error
    spec:
      components:
        env:
        - name: TOTAL_CHAOS_DURATION
          value: '60'
        - name: TARGET_HOSTNAMES
          value: '["backend-service.resilience-demo.svc.cluster.local"]'
        - name: MATCH_SCHEME
          value: exact
        - name: CONTAINER_RUNTIME
          value: containerd
        - name: SOCKET_PATH
          value: /run/containerd/containerd.sock
        - name: PODS_AFFECTED_PERC
          value: '100'
```
TARGET_HOSTNAMES는 JSON array 문자열입니다. Runtime·socket·privilege 전제가 선택한 Linux test node와 일치해야 하며 모든 EKS node 유형에 이식 가능한 예제가 아닙니다. 퍼센트가 무관한 Pod를 선택하지 않도록 workload 범위를 제한합니다. Resource 존재만으로 성공을 판단하지 않고 ChaosResult와 앱 health를 확인합니다.

```bash
kubectl --context "$KUBE_CONTEXT" -n resilience-demo get chaosengine,chaosresult
```
[Litmus operator 3.31.0](https://github.com/litmuschaos/chaos-operator/releases/tag/3.31.0) · [Official fault catalog](https://github.com/litmuschaos/chaos-charts/tree/master/faults/kubernetes) · [CNCF project status](https://www.cncf.io/projects/litmus/)

### Chaos Mesh

예시는 release 2.8.4 CRD shape를 사용합니다. 설치 전에 Helm chart의 runtime·socket·node 선택·daemon privilege·dashboard 접근·cluster 호환성을 검토합니다. Host 권한 fault injection은 명시적으로 허용한 test node 유형에서 수행하며 schema만으로 Auto Mode·Fargate·Hybrid Node 지원을 추정하지 않습니다.

아래 NetworkChaos·IOChaos·TimeChaos는 release의 experiment.chaos-mesh.org/pause annotation으로 중지 상태입니다. Paused manifest 적용도 cluster 변경이며 target·status 검토 후 pause를 별도로 해제합니다. 중단 시 recovery 상태를 기다립니다. Pause가 삭제 data를 복원하지 않으며 one-shot fault는 pause 의미가 다릅니다.

#### Network latency

```yaml
apiVersion: chaos-mesh.org/v1alpha1
kind: NetworkChaos
metadata:
  name: review-network-delay
  namespace: resilience-demo
  annotations:
    experiment.chaos-mesh.org/pause: 'true'
spec:
  action: delay
  mode: fixed
  value: '1'
  selector:
    namespaces:
    - resilience-demo
    labelSelectors:
      app: web-app
      experiment-approved: 'true'
  delay:
    latency: 100ms
    jitter: 50ms
    correlation: '25'
  duration: 1m
```
#### Network partition

```yaml
apiVersion: chaos-mesh.org/v1alpha1
kind: NetworkChaos
metadata:
  name: review-network-partition
  namespace: resilience-demo
  annotations:
    experiment.chaos-mesh.org/pause: 'true'
spec:
  action: partition
  mode: fixed
  value: '1'
  selector:
    namespaces:
    - resilience-demo
    labelSelectors:
      app: web-app
      experiment-approved: 'true'
  direction: both
  target:
    mode: fixed
    value: '1'
    selector:
      namespaces:
      - resilience-demo
      labelSelectors:
        app: backend
        experiment-approved: 'true'
  duration: 1m
```
#### I/O latency

```yaml
apiVersion: chaos-mesh.org/v1alpha1
kind: IOChaos
metadata:
  name: review-io-delay
  namespace: resilience-demo
  annotations:
    experiment.chaos-mesh.org/pause: 'true'
spec:
  action: latency
  mode: fixed
  value: '1'
  selector:
    namespaces:
    - resilience-demo
    labelSelectors:
      app: web-app
      experiment-approved: 'true'
  volumePath: /audit-data
  delay: 100ms
  percent: 50
  duration: 1m
```
/audit-data에는 폐기 가능한 test volume을 mount합니다. 예시는 선택적 path filter를 생략했으므로 활성화 전 대상 file을 확인합니다. percent는 주입 operation 비율이지 용량 상한이 아닙니다. 기존 production PostgreSQL data directory에 연결하지 않습니다. 알려진 baseline으로 복구·data 무결성을 확인합니다.

#### Time offset

```yaml
apiVersion: chaos-mesh.org/v1alpha1
kind: TimeChaos
metadata:
  name: review-time-offset
  namespace: resilience-demo
  annotations:
    experiment.chaos-mesh.org/pause: 'true'
spec:
  mode: fixed
  value: '1'
  selector:
    namespaces:
    - resilience-demo
    labelSelectors:
      app: web-app
      experiment-approved: 'true'
  timeOffset: -2h
  clockIds:
  - CLOCK_REALTIME
  duration: 1m
```
-2h는 선택한 주입 program의 CLOCK_REALTIME 동작 대상이며 node·모든 clock이 두 시간 바뀐다는 뜻이 아닙니다. Token·scheduler·lease 영향을 추정하기 전에 주입 방식과 앱 clock 사용을 확인합니다. Duration은 의도한 fault 기간이지 앱 복구 시간 보장이 아닙니다.

```bash
kubectl --context "$KUBE_CONTEXT" -n resilience-demo \
  get networkchaos,iochaos,timechaos -o yaml
```
[Chaos Mesh 2.8.4 chart](https://github.com/chaos-mesh/chaos-mesh/tree/v2.8.4/helm/chaos-mesh) · [Pause controller](https://github.com/chaos-mesh/chaos-mesh/blob/v2.8.4/controllers/common/desiredphase/controller.go)

### Game Day Framework

주입 전 abort threshold·독립 observer·정확한 recovery owner를 정합니다. 실패·no-data도 포함해 감지와 복원을 분리 기록합니다. 다음 실험 전 현재 실험을 중단하고 duration 경과만으로 성공이라 하지 말고 실제 복구를 검증합니다.

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

- [ ] 장기 실행 앱별 적절한 liveness 동작 검토
- [ ] Service 제공 앱별 실제 readiness contract 검토
- [ ] 시작 시간이 긴 앱에 Startup Probe 설정
- [ ] Resource requests/limits 설정
- [ ] 중요 Deployment에 PDB 설정
- [ ] replicas >= 2 설정

### Level 2: Multi-AZ 체크리스트

- [ ] Topology Spread Constraints 적용
- [ ] eligible domain·maxSkew·minDomains와 AZ 장애 시 배치 검증
- [ ] Karpenter NodePool에 Multi-AZ 설정
- [ ] workload 용량에 맞는 disruption budget·올림·예외 경로 검토
- [ ] StorageClass volumeBindingMode: WaitForFirstConsumer
- [ ] 공유 스토리지에 EFS 사용
- [ ] Istio locality-aware routing 설정
- [ ] ARC 지원·N-1 용량·alarm 확인 후 별도 autoshift 활성화 결정

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

아래는 기존 출처 미확인 비용 예시이며 현재 견적·실측 절감률이 아닙니다. Cross-AZ 요금은 service·경로·방향·region에 따라 달라 $0.01/GB를 모든 EKS traffic의 총 요금으로 쓸 수 없습니다. 현재 service 가격으로 실제 자원·장애 headroom을 계산하며 비용·chaos benchmark를 재실행하지 않았습니다. 이전 EN의 Active-Passive 50–70% 감소 예시도 검증된 절감률이 아닙니다.

| 항목 | 비용 영향 | 절감 전략 |
|------|----------|----------|
| **Multi-Region** | 2x+ 증가 | Active-Passive로 대기 리전 비용 절감 |
| **Spot Instances** | 60-90% 절감 | 상태 없는 워크로드에 Spot 사용 |
| **Locality Routing** | 60-80% 절감 | Cross-AZ 트래픽 최소화 |
| **Cell Architecture** | 10-20% 증가 | 장애 영향 감소로 운영 비용 절감 |
| **Chaos Engineering** | 기존 월 $100–500 예시 | 실제 FIS·자원 사용량으로 계산 |
| **Cross-AZ** | 기존 $0.01/GB 예시 | 경로·방향·service 가격 별도 확인 |

---

## 다음 단계

이 문서에서는 EKS 클러스터의 고가용성과 복원력 아키텍처에 대해 다루었습니다. 복원력 전략을 구현한 후에는 문제 발생 시 효과적인 디버깅이 중요합니다.

### 관련 문서

- **다음 문서**: [EKS 고급 디버깅](./11-eks-advanced-debugging.md) - 복잡한 문제 상황에서의 디버깅 기법
- **퀴즈**: [EKS 복원력 퀴즈](../quizzes/eks/10-eks-resiliency-quiz.md) - 학습 내용 확인

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
