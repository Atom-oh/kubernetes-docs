# Amazon EKS 고가용성 및 복원력 퀴즈

이 퀴즈는 Amazon EKS 클러스터의 고가용성(HA), 복원력, Multi-AZ 배포, Cell-Based Architecture, Chaos Engineering, PodDisruptionBudget, Topology Spread Constraints에 대한 이해를 테스트합니다.

## 퀴즈 개요
- Multi-AZ 아키텍처 및 구성
- Cell-Based Architecture 패턴
- Chaos Engineering 원칙 및 도구
- PodDisruptionBudget (PDB) 구성
- Topology Spread Constraints
- 장애 복구 및 재해 복구

## 객관식 문제

### 1. Amazon EKS에서 Multi-AZ 배포의 가장 큰 이점은 무엇인가요?

A. 비용 절감
B. 단일 AZ 장애 시에도 애플리케이션 가용성 유지
C. 네트워크 지연 시간 증가
D. 관리 복잡성 감소

<details>
<summary>정답 보기</summary>

**정답: B. 단일 AZ 장애 시에도 애플리케이션 가용성 유지**

**설명:**
Multi-AZ 배포의 핵심 이점은 단일 가용 영역(AZ)에 장애가 발생하더라도 다른 AZ에서 워크로드가 계속 실행될 수 있어 애플리케이션의 가용성을 유지할 수 있다는 것입니다.

**Multi-AZ 배포의 주요 이점:**
- 단일 AZ 장애 시 자동 페일오버
- 데이터센터 수준의 장애 복원력
- 99.99% 이상의 가용성 달성 가능
- 지역 내 재해 복구 능력 향상

```yaml
# Multi-AZ를 위한 노드 그룹 구성 예시
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: ha-cluster
  region: ap-northeast-2
nodeGroups:
  - name: ng-multi-az
    instanceType: m5.large
    desiredCapacity: 6
    availabilityZones: ["ap-northeast-2a", "ap-northeast-2b", "ap-northeast-2c"]
```

</details>

### 2. PodDisruptionBudget(PDB)의 주요 목적은 무엇인가요?

A. Pod의 CPU 사용량 제한
B. 자발적 중단 시 최소 가용 Pod 수 보장
C. Pod 간 네트워크 트래픽 제어
D. Pod의 메모리 사용량 모니터링

<details>
<summary>정답 보기</summary>

**정답: B. 자발적 중단 시 최소 가용 Pod 수 보장**

**설명:**
PodDisruptionBudget(PDB)은 노드 드레인, 클러스터 업그레이드, 자동 스케일링 등 자발적 중단(Voluntary Disruption) 상황에서 최소한의 Pod가 항상 실행 상태를 유지하도록 보장합니다.

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: web-app-pdb
spec:
  minAvailable: 2  # 또는 maxUnavailable: 1
  selector:
    matchLabels:
      app: web-app
```

**PDB의 핵심 기능:**
- `minAvailable`: 항상 유지해야 할 최소 Pod 수
- `maxUnavailable`: 동시에 중단될 수 있는 최대 Pod 수
- 롤링 업데이트 및 노드 유지보수 시 서비스 연속성 보장

</details>

### 3. Topology Spread Constraints에서 `whenUnsatisfiable: DoNotSchedule`의 의미는 무엇인가요?

A. 제약 조건을 만족하지 못하면 Pod를 아무 노드에나 스케줄링
B. 제약 조건을 만족하지 못하면 Pod 스케줄링을 거부
C. 제약 조건을 무시하고 항상 스케줄링
D. 제약 조건 위반 시 기존 Pod를 삭제

<details>
<summary>정답 보기</summary>

**정답: B. 제약 조건을 만족하지 못하면 Pod 스케줄링을 거부**

**설명:**
`whenUnsatisfiable: DoNotSchedule`은 토폴로지 분산 제약 조건을 만족시킬 수 없는 경우 해당 Pod의 스케줄링을 거부합니다. 이는 엄격한 분산 정책을 적용할 때 사용됩니다.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
spec:
  replicas: 6
  template:
    spec:
      topologySpreadConstraints:
      - maxSkew: 1
        topologyKey: topology.kubernetes.io/zone
        whenUnsatisfiable: DoNotSchedule
        labelSelector:
          matchLabels:
            app: web-app
```

**whenUnsatisfiable 옵션:**
- `DoNotSchedule`: 제약 조건 미충족 시 스케줄링 거부 (Hard 제약)
- `ScheduleAnyway`: 제약 조건을 최대한 만족시키되, 불가능하면 어디든 스케줄링 (Soft 제약)

</details>

### 4. Cell-Based Architecture에서 "Cell"의 주요 특징으로 올바르지 않은 것은?

A. 독립적으로 배포 및 확장 가능
B. 장애가 전체 시스템으로 전파됨
C. 자체 완결적인 기능 단위
D. 다른 Cell과 느슨하게 결합

<details>
<summary>정답 보기</summary>

**정답: B. 장애가 전체 시스템으로 전파됨**

**설명:**
Cell-Based Architecture의 핵심 목적은 장애 격리입니다. 각 Cell은 독립적으로 동작하여 한 Cell의 장애가 다른 Cell로 전파되지 않도록 설계됩니다.

**Cell-Based Architecture의 핵심 원칙:**
1. **장애 격리**: 한 Cell의 장애가 다른 Cell에 영향을 주지 않음
2. **독립적 배포**: 각 Cell을 개별적으로 업데이트 가능
3. **수평적 확장**: Cell 단위로 용량 확장
4. **자체 완결성**: 각 Cell이 필요한 모든 구성 요소 포함

```yaml
# Cell 단위 네임스페이스 구성 예시
apiVersion: v1
kind: Namespace
metadata:
  name: cell-a
  labels:
    cell: a
    region: ap-northeast-2
---
apiVersion: v1
kind: Namespace
metadata:
  name: cell-b
  labels:
    cell: b
    region: ap-northeast-2
```

</details>

### 5. Chaos Engineering에서 "Steady State Hypothesis"의 의미는 무엇인가요?

A. 시스템을 항상 정지 상태로 유지
B. 실험 전후로 시스템이 정상 동작함을 검증하는 기준
C. 카오스 실험을 중단하는 조건
D. 시스템의 최대 부하 상태

<details>
<summary>정답 보기</summary>

**정답: B. 실험 전후로 시스템이 정상 동작함을 검증하는 기준**

**설명:**
Steady State Hypothesis는 시스템의 "정상" 상태를 정의하는 측정 가능한 지표입니다. 카오스 실험 전에 이 가설이 참인지 확인하고, 실험 후에도 시스템이 이 상태로 돌아오는지 검증합니다.

**Steady State 지표 예시:**
- 응답 시간 < 200ms (p99)
- 에러율 < 0.1%
- 처리량 > 1000 req/s
- Pod 가용률 > 99%

```yaml
# Litmus Chaos 실험 정의 예시
apiVersion: litmuschaos.io/v1alpha1
kind: ChaosExperiment
metadata:
  name: pod-delete
spec:
  definition:
    steadyState:
      metrics:
        - name: response_time_p99
          threshold: 200
          comparison: lessThan
        - name: error_rate
          threshold: 0.1
          comparison: lessThan
```

</details>

### 6. EKS에서 Zone-Aware Routing을 구현하기 위한 Service 설정은 무엇인가요?

A. `service.kubernetes.io/topology-aware-hints: auto`
B. `service.kubernetes.io/zone-routing: enabled`
C. `service.kubernetes.io/local-only: true`
D. `service.kubernetes.io/cross-zone: disabled`

<details>
<summary>정답 보기</summary>

**정답: A. `service.kubernetes.io/topology-aware-hints: auto`**

**설명:**
Kubernetes 1.23+에서 도입된 Topology Aware Hints를 사용하면 kube-proxy가 같은 Zone 내의 엔드포인트로 트래픽을 우선 라우팅하여 Cross-AZ 트래픽 비용과 지연 시간을 줄일 수 있습니다.

```yaml
apiVersion: v1
kind: Service
metadata:
  name: web-service
  annotations:
    service.kubernetes.io/topology-aware-hints: auto
spec:
  selector:
    app: web-app
  ports:
  - port: 80
    targetPort: 8080
```

**Zone-Aware Routing의 이점:**
- Cross-AZ 데이터 전송 비용 절감
- 네트워크 지연 시간 감소
- 같은 Zone 내 트래픽 유지로 안정성 향상

</details>

### 7. PDB에서 `maxUnavailable: 25%`를 설정하고 replicas가 8개일 때, 동시에 중단될 수 있는 최대 Pod 수는?

A. 1개
B. 2개
C. 3개
D. 4개

<details>
<summary>정답 보기</summary>

**정답: B. 2개**

**설명:**
`maxUnavailable: 25%`는 전체 replicas의 25%까지 동시에 중단될 수 있음을 의미합니다. 8개의 25%는 2개입니다 (8 × 0.25 = 2).

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: app-pdb
spec:
  maxUnavailable: 25%  # 8개 중 2개까지 중단 가능
  selector:
    matchLabels:
      app: web-app
```

**계산 방식:**
- 백분율은 내림 처리됨
- replicas = 8, maxUnavailable = 25%
- 8 × 0.25 = 2개 (소수점 이하 내림)
- 따라서 최소 6개의 Pod가 항상 실행 상태 유지

</details>

### 8. Litmus Chaos에서 제공하는 실험 유형이 아닌 것은?

A. pod-delete
B. node-drain
C. network-loss
D. cluster-delete

<details>
<summary>정답 보기</summary>

**정답: D. cluster-delete**

**설명:**
Litmus Chaos는 클러스터 전체를 삭제하는 실험은 제공하지 않습니다. Chaos Engineering의 목적은 통제된 환경에서 시스템 복원력을 테스트하는 것이지, 전체 인프라를 파괴하는 것이 아닙니다.

**Litmus Chaos 주요 실험 유형:**
- **Pod 레벨**: pod-delete, pod-cpu-hog, pod-memory-hog, pod-network-loss
- **Node 레벨**: node-drain, node-cpu-hog, node-memory-hog, node-taint
- **Network 레벨**: network-loss, network-latency, network-corruption
- **AWS 특화**: ec2-terminate, ebs-loss, az-chaos

```bash
# Litmus Chaos 설치
kubectl apply -f https://litmuschaos.github.io/litmus/litmus-operator-v2.14.0.yaml
```

</details>

### 9. EKS Control Plane의 고가용성은 어떻게 보장되나요?

A. 사용자가 직접 Multi-AZ 구성 필요
B. AWS가 자동으로 여러 AZ에 걸쳐 관리
C. 단일 AZ에서만 실행됨
D. 수동 페일오버 구성 필요

<details>
<summary>정답 보기</summary>

**정답: B. AWS가 자동으로 여러 AZ에 걸쳐 관리**

**설명:**
Amazon EKS Control Plane은 AWS에 의해 완전 관리되며, 자동으로 여러 가용 영역에 걸쳐 고가용성으로 배포됩니다. etcd 데이터도 여러 AZ에 복제됩니다.

**EKS Control Plane HA 특징:**
- 자동 Multi-AZ 배포 (최소 2개 AZ)
- API 서버 자동 스케일링
- etcd 데이터 자동 복제 및 백업
- 자동 장애 감지 및 복구
- 99.95% SLA 보장

**사용자 책임 영역:**
- 데이터 플레인(노드) Multi-AZ 구성
- 워크로드 Pod 분산 배치
- PDB 및 Topology Spread 설정

</details>

### 10. Topology Spread Constraints에서 `maxSkew`의 의미는 무엇인가요?

A. 최대 Pod 수
B. 토폴로지 도메인 간 Pod 수 차이의 최대 허용치
C. 최소 노드 수
D. 최대 노드당 Pod 수

<details>
<summary>정답 보기</summary>

**정답: B. 토폴로지 도메인 간 Pod 수 차이의 최대 허용치**

**설명:**
`maxSkew`는 서로 다른 토폴로지 도메인(예: AZ, 노드) 간에 허용되는 Pod 수 차이의 최대값입니다. 예를 들어 `maxSkew: 1`이면 어떤 두 도메인 간에도 Pod 수 차이가 1을 초과할 수 없습니다.

```yaml
apiVersion: apps/v1
kind: Deployment
spec:
  template:
    spec:
      topologySpreadConstraints:
      - maxSkew: 1  # 도메인 간 최대 1개 차이
        topologyKey: topology.kubernetes.io/zone
        whenUnsatisfiable: DoNotSchedule
        labelSelector:
          matchLabels:
            app: web-app
```

**maxSkew 예시 (replicas=6, 3개 AZ):**
- maxSkew=1: Zone-A(2), Zone-B(2), Zone-C(2) - 균등 분산
- maxSkew=2: Zone-A(3), Zone-B(2), Zone-C(1) - 허용됨
- maxSkew=1 위반: Zone-A(4), Zone-B(1), Zone-C(1) - 스케줄링 거부

</details>

## 단답형 문제

### 1. EKS에서 Cross-AZ 데이터 전송 비용을 줄이기 위한 Service 어노테이션은 무엇인가요?

<details>
<summary>정답 보기</summary>

**정답:** `service.kubernetes.io/topology-aware-hints: auto`

**설명:**
이 어노테이션을 Service에 추가하면 Kubernetes가 Topology Aware Hints를 활성화하여 같은 AZ 내의 엔드포인트로 트래픽을 우선 라우팅합니다.

```yaml
apiVersion: v1
kind: Service
metadata:
  annotations:
    service.kubernetes.io/topology-aware-hints: auto
```

</details>

### 2. PodDisruptionBudget에서 "자발적 중단(Voluntary Disruption)"의 예시 3가지를 작성하세요.

<details>
<summary>정답 보기</summary>

**정답:**
1. 노드 드레인 (kubectl drain)
2. 클러스터 업그레이드
3. 클러스터 오토스케일러에 의한 노드 축소 (Scale-down)

**추가 예시:**
- Deployment/StatefulSet의 롤링 업데이트
- 수동 Pod 삭제 (kubectl delete pod)
- 노드 유지보수를 위한 cordon/drain

**비자발적 중단(Involuntary Disruption) 예시:**
- 하드웨어 장애
- 커널 패닉
- VM 삭제
- OOM Kill

</details>

### 3. Chaos Engineering의 4가지 핵심 원칙을 나열하세요.

<details>
<summary>정답 보기</summary>

**정답:**
1. **Steady State 가설 수립**: 정상 상태를 정의하는 측정 가능한 지표 설정
2. **실제 이벤트 시뮬레이션**: 실제 발생 가능한 장애 상황 재현
3. **프로덕션 환경에서 실험**: 가능한 실제 환경에서 테스트
4. **폭발 반경 최소화**: 실험의 영향 범위를 제한하고 자동 중단 조건 설정

**추가 원칙:**
- 실험 자동화로 지속적 검증
- 결과 분석 및 시스템 개선

</details>

### 4. EKS 노드 그룹을 Multi-AZ로 구성할 때 최소 권장 AZ 수는 몇 개인가요?

<details>
<summary>정답 보기</summary>

**정답:** 3개

**설명:**
3개 이상의 AZ에 걸쳐 노드를 분산 배치하면:
- 단일 AZ 장애 시에도 2/3 용량 유지
- Quorum 기반 시스템(예: etcd)의 안정성 보장
- 더 균등한 워크로드 분산 가능

```yaml
# eksctl Multi-AZ 노드 그룹 구성
nodeGroups:
  - name: ng-multi-az
    availabilityZones:
      - ap-northeast-2a
      - ap-northeast-2b
      - ap-northeast-2c
    desiredCapacity: 6
```

</details>

### 5. Cell-Based Architecture에서 트래픽을 특정 Cell로 라우팅하는 방법은 무엇인가요?

<details>
<summary>정답 보기</summary>

**정답:** 라우팅 레이어(예: API Gateway, Service Mesh, Load Balancer)에서 사용자/테넌트 ID 기반으로 특정 Cell로 트래픽을 분배합니다.

**구현 방법:**
1. **해시 기반 라우팅**: 사용자 ID를 해시하여 Cell 결정
2. **명시적 매핑**: 사용자-Cell 매핑 테이블 유지
3. **지역 기반**: 지리적 위치에 따른 Cell 할당

```yaml
# Istio VirtualService를 통한 Cell 라우팅 예시
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: cell-router
spec:
  http:
  - match:
    - headers:
        x-cell-id:
          exact: "cell-a"
    route:
    - destination:
        host: app.cell-a.svc.cluster.local
  - match:
    - headers:
        x-cell-id:
          exact: "cell-b"
    route:
    - destination:
        host: app.cell-b.svc.cluster.local
```

</details>

## 실습 문제

### 1. 다음 요구사항을 만족하는 PodDisruptionBudget YAML을 작성하세요.
- 이름: api-server-pdb
- 대상: label이 `app: api-server`인 Pod
- 최소 3개의 Pod가 항상 실행 상태 유지

<details>
<summary>정답 보기</summary>

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: api-server-pdb
spec:
  minAvailable: 3
  selector:
    matchLabels:
      app: api-server
```

**검증 명령어:**
```bash
# PDB 생성
kubectl apply -f api-server-pdb.yaml

# PDB 상태 확인
kubectl get pdb api-server-pdb

# 상세 정보 확인
kubectl describe pdb api-server-pdb
```

**예상 출력:**
```
NAME              MIN AVAILABLE   MAX UNAVAILABLE   ALLOWED DISRUPTIONS   AGE
api-server-pdb    3               N/A               2                     10s
```

</details>

### 2. 3개의 AZ에 균등하게 Pod를 분산시키는 Topology Spread Constraints를 포함한 Deployment를 작성하세요.
- Deployment 이름: web-frontend
- replicas: 6
- maxSkew: 1
- 분산 키: topology.kubernetes.io/zone

<details>
<summary>정답 보기</summary>

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-frontend
spec:
  replicas: 6
  selector:
    matchLabels:
      app: web-frontend
  template:
    metadata:
      labels:
        app: web-frontend
    spec:
      topologySpreadConstraints:
      - maxSkew: 1
        topologyKey: topology.kubernetes.io/zone
        whenUnsatisfiable: DoNotSchedule
        labelSelector:
          matchLabels:
            app: web-frontend
      containers:
      - name: web
        image: nginx:latest
        ports:
        - containerPort: 80
```

**검증 명령어:**
```bash
# Deployment 생성
kubectl apply -f web-frontend.yaml

# Pod 분산 확인
kubectl get pods -l app=web-frontend -o wide

# Zone별 Pod 수 확인
kubectl get pods -l app=web-frontend -o jsonpath='{range .items[*]}{.spec.nodeName}{"\n"}{end}' | \
  xargs -I {} kubectl get node {} -o jsonpath='{.metadata.labels.topology\.kubernetes\.io/zone}{"\n"}' | \
  sort | uniq -c
```

**예상 출력:**
```
2 ap-northeast-2a
2 ap-northeast-2b
2 ap-northeast-2c
```

</details>

### 3. Litmus Chaos를 사용하여 특정 Pod를 삭제하는 Chaos 실험을 정의하세요.
- 대상: namespace가 `production`, label이 `app: payment-service`인 Pod
- 실험 시간: 30초
- 삭제할 Pod 수: 1개

<details>
<summary>정답 보기</summary>

```yaml
apiVersion: litmuschaos.io/v1alpha1
kind: ChaosEngine
metadata:
  name: payment-pod-delete
  namespace: production
spec:
  appinfo:
    appns: production
    applabel: app=payment-service
    appkind: deployment
  engineState: active
  chaosServiceAccount: litmus-admin
  experiments:
  - name: pod-delete
    spec:
      components:
        env:
        - name: TOTAL_CHAOS_DURATION
          value: "30"
        - name: CHAOS_INTERVAL
          value: "10"
        - name: PODS_AFFECTED_PERC
          value: "100"
        - name: TARGET_PODS
          value: ""
        - name: FORCE
          value: "false"
```

**사전 준비:**
```bash
# Litmus Chaos Operator 설치
kubectl apply -f https://litmuschaos.github.io/litmus/litmus-operator-v2.14.0.yaml

# ChaosExperiment CRD 설치
kubectl apply -f https://hub.litmuschaos.io/api/chaos/2.14.0?file=charts/generic/pod-delete/experiment.yaml

# ServiceAccount 생성
kubectl apply -f https://hub.litmuschaos.io/api/chaos/2.14.0?file=charts/generic/pod-delete/rbac.yaml -n production
```

**검증 명령어:**
```bash
# Chaos 실험 실행
kubectl apply -f payment-pod-delete.yaml

# 실험 상태 확인
kubectl get chaosengine payment-pod-delete -n production

# 실험 결과 확인
kubectl get chaosresult payment-pod-delete-pod-delete -n production -o yaml
```

</details>

## 심화 문제

### 1. 금융 서비스 회사에서 EKS 클러스터의 99.99% 가용성을 달성하기 위한 아키텍처를 설계하세요. Multi-AZ, Cell-Based Architecture, PDB, Chaos Engineering을 모두 활용한 종합적인 전략을 제시하세요.

<details>
<summary>정답 보기</summary>

**99.99% 가용성 달성을 위한 종합 아키텍처:**

**1. Multi-Region + Multi-AZ 구성:**
```yaml
# Primary Region (ap-northeast-2)
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: finance-primary
  region: ap-northeast-2
nodeGroups:
  - name: ng-critical
    instanceType: m5.xlarge
    desiredCapacity: 9
    availabilityZones: ["ap-northeast-2a", "ap-northeast-2b", "ap-northeast-2c"]
    labels:
      criticality: high
```

**2. Cell-Based Architecture 적용:**
```yaml
# Cell 단위 격리
apiVersion: v1
kind: Namespace
metadata:
  name: cell-korea-1
  labels:
    cell: korea-1
    region: ap-northeast-2
---
# Cell별 리소스 쿼터
apiVersion: v1
kind: ResourceQuota
metadata:
  name: cell-quota
  namespace: cell-korea-1
spec:
  hard:
    requests.cpu: "100"
    requests.memory: 200Gi
    limits.cpu: "200"
    limits.memory: 400Gi
```

**3. 강력한 PDB 정책:**
```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: critical-service-pdb
spec:
  minAvailable: 80%  # 항상 80% 이상 가용
  selector:
    matchLabels:
      tier: critical
```

**4. Topology Spread + Anti-Affinity:**
```yaml
spec:
  topologySpreadConstraints:
  - maxSkew: 1
    topologyKey: topology.kubernetes.io/zone
    whenUnsatisfiable: DoNotSchedule
  - maxSkew: 1
    topologyKey: kubernetes.io/hostname
    whenUnsatisfiable: ScheduleAnyway
  affinity:
    podAntiAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
      - labelSelector:
          matchLabels:
            app: payment-api
        topologyKey: kubernetes.io/hostname
```

**5. Chaos Engineering 프로그램:**
```yaml
# 주기적 Chaos 실험 (GameDay)
apiVersion: litmuschaos.io/v1alpha1
kind: ChaosSchedule
metadata:
  name: weekly-resilience-test
spec:
  schedule:
    type: repeat
    repeat:
      timeRange:
        startTime: "2024-01-01T02:00:00Z"
        endTime: "2024-12-31T04:00:00Z"
      workDays:
        includedDays: "Sun"
  engineSpec:
    experiments:
    - name: pod-delete
    - name: node-drain
    - name: network-loss
```

**6. 모니터링 및 자동 복구:**
```yaml
# HPA + 자동 복구
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: critical-service-hpa
spec:
  minReplicas: 6
  maxReplicas: 30
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 0
      policies:
      - type: Percent
        value: 100
        periodSeconds: 15
```

**SLA 계산:**
- 99.99% = 연간 약 52분 다운타임
- Multi-AZ: 단일 AZ 장애 대응
- Multi-Region: 리전 장애 대응
- Cell 격리: 영향 범위 제한
- 자동 복구: MTTR 최소화

</details>

### 2. 대규모 이커머스 플랫폼에서 블랙프라이데이 트래픽 급증(10배)에 대비한 EKS 복원력 전략을 수립하세요. Pre-scaling, Chaos Engineering 검증, 장애 시나리오별 대응 방안을 포함하세요.

<details>
<summary>정답 보기</summary>

**블랙프라이데이 트래픽 급증 대비 전략:**

**1. 사전 용량 계획 (Pre-scaling):**
```yaml
# Karpenter Provisioner - 급증 대비 구성
apiVersion: karpenter.sh/v1alpha5
kind: Provisioner
metadata:
  name: blackfriday
spec:
  requirements:
  - key: node.kubernetes.io/instance-type
    operator: In
    values: ["m5.2xlarge", "m5.4xlarge", "c5.2xlarge", "c5.4xlarge"]
  - key: topology.kubernetes.io/zone
    operator: In
    values: ["ap-northeast-2a", "ap-northeast-2b", "ap-northeast-2c"]
  limits:
    resources:
      cpu: 2000
      memory: 4000Gi
  ttlSecondsAfterEmpty: 30
---
# HPA 사전 스케일링
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: product-catalog-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: product-catalog
  minReplicas: 50  # 평소 10 -> 블랙프라이데이 50
  maxReplicas: 500
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 60  # 여유있게 60%
```

**2. 트래픽 급증 전 Chaos Engineering 검증:**
```yaml
# 부하 테스트 + Chaos 조합
apiVersion: litmuschaos.io/v1alpha1
kind: ChaosEngine
metadata:
  name: blackfriday-prep-test
spec:
  experiments:
  # 시나리오 1: 트래픽 10배 + Pod 30% 장애
  - name: pod-delete
    spec:
      components:
        env:
        - name: PODS_AFFECTED_PERC
          value: "30"
        - name: TOTAL_CHAOS_DURATION
          value: "300"
  # 시나리오 2: 트래픽 10배 + AZ 장애
  - name: node-drain
    spec:
      components:
        env:
        - name: TARGET_NODE_LABEL
          value: "topology.kubernetes.io/zone=ap-northeast-2a"
  # 시나리오 3: 트래픽 10배 + DB 지연
  - name: pod-network-latency
    spec:
      components:
        env:
        - name: TARGET_PODS
          value: "app=mysql"
        - name: NETWORK_LATENCY
          value: "500"
```

**3. 장애 시나리오별 대응 방안:**

| 시나리오 | 감지 | 자동 대응 | 수동 대응 |
|---------|------|----------|----------|
| AZ 장애 | CloudWatch Alarm | Topology Spread로 자동 분산 | Route53 Failover |
| DB 지연 | Latency Alert | Circuit Breaker 활성화 | Read Replica 전환 |
| 메모리 부족 | OOM Alert | HPA Scale-out | Node 추가 |
| 트래픽 폭주 | TPS Alert | Rate Limiting | CDN 캐시 확대 |

**4. Circuit Breaker 패턴:**
```yaml
# Istio DestinationRule - Circuit Breaker
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: product-catalog-cb
spec:
  host: product-catalog
  trafficPolicy:
    connectionPool:
      http:
        h2UpgradePolicy: UPGRADE
        http1MaxPendingRequests: 1000
        http2MaxRequests: 2000
    outlierDetection:
      consecutive5xxErrors: 5
      interval: 10s
      baseEjectionTime: 30s
      maxEjectionPercent: 50
```

**5. 실시간 모니터링 대시보드:**
```promql
# Grafana 대시보드 쿼리
# 1. 전체 TPS
sum(rate(http_requests_total[1m]))

# 2. 에러율
sum(rate(http_requests_total{status=~"5.."}[1m])) / sum(rate(http_requests_total[1m])) * 100

# 3. P99 응답시간
histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket[1m])) by (le))

# 4. Pod 가용률
sum(kube_pod_status_ready{condition="true"}) / sum(kube_pod_status_ready) * 100
```

**6. 롤백 계획:**
```bash
#!/bin/bash
# Emergency Rollback Script
NAMESPACE="production"
DEPLOYMENT="product-catalog"

# 1. 이전 버전으로 롤백
kubectl rollout undo deployment/$DEPLOYMENT -n $NAMESPACE

# 2. HPA 일시 중지
kubectl patch hpa $DEPLOYMENT-hpa -n $NAMESPACE -p '{"spec":{"minReplicas":100}}'

# 3. Feature Flag 비활성화
curl -X POST "https://feature-flags.internal/api/v1/flags/blackfriday-features/disable"

# 4. CDN 캐시 연장
aws cloudfront update-distribution --id $CF_DIST_ID --default-cache-behavior "DefaultTTL=86400"
```

**테스트 일정:**
- D-14: 기본 Chaos 테스트
- D-7: 전체 시나리오 GameDay
- D-3: 최종 확인 및 Pre-scaling
- D-Day: 실시간 모니터링 및 대응

</details>
