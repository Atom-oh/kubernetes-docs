# EKS Hybrid Nodes 워크로드 배치 퀴즈

> **관련 문서**: [워크로드 배치](../../eks-hybrid-nodes/06-workload-placement.md)

## 객관식 문제

### 1. Kubernetes에서 특정 노드에 Pod를 배치하기 위해 사용하는 방법이 아닌 것은?

A. nodeSelector
B. Node Affinity
C. Taints/Tolerations
D. PodDisruptionBudget

<details>
<summary>정답 보기</summary>

**정답: D. PodDisruptionBudget**

**설명:**
PodDisruptionBudget(PDB)는 Pod 배치가 아닌, 자발적 중단(voluntary disruption) 시 최소 가용성을 보장하는 데 사용됩니다.

**Pod 배치 방법:**
- **nodeSelector**: 간단한 레이블 기반 노드 선택
- **Node Affinity**: 복잡한 규칙 기반 노드 선택
- **Taints/Tolerations**: 노드가 특정 Pod만 수용하도록 제한
- **Pod Affinity/Anti-Affinity**: Pod 간 배치 관계 정의

```yaml
# nodeSelector 예시
spec:
  nodeSelector:
    location: onprem

# Node Affinity 예시
spec:
  affinity:
    nodeAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
        nodeSelectorTerms:
        - matchExpressions:
          - key: gpu
            operator: In
            values: ["nvidia-a100"]
```

</details>

### 2. Hybrid Nodes에 GPU 워크로드만 배치하도록 Taint를 설정할 때 올바른 명령은?

A. kubectl label node hybrid-node-1 gpu=true
B. kubectl taint node hybrid-node-1 dedicated=gpu:NoSchedule
C. kubectl annotate node hybrid-node-1 gpu=nvidia
D. kubectl cordon hybrid-node-1

<details>
<summary>정답 보기</summary>

**정답: B. kubectl taint node hybrid-node-1 dedicated=gpu:NoSchedule**

**설명:**
Taint는 특정 Pod만 해당 노드에 스케줄링되도록 제한합니다.

```bash
# Taint 설정
kubectl taint node hybrid-node-1 dedicated=gpu:NoSchedule

# Taint 확인
kubectl describe node hybrid-node-1 | grep Taints
```

```yaml
# 해당 Taint를 허용하는 Toleration
apiVersion: v1
kind: Pod
metadata:
  name: gpu-workload
spec:
  tolerations:
  - key: "dedicated"
    operator: "Equal"
    value: "gpu"
    effect: "NoSchedule"
  containers:
  - name: cuda-app
    image: nvidia/cuda:12.0-runtime
    resources:
      limits:
        nvidia.com/gpu: 1
```

**Taint Effect 유형:**
- **NoSchedule**: 새 Pod 스케줄링 방지
- **PreferNoSchedule**: 가능하면 스케줄링 회피
- **NoExecute**: 기존 Pod도 퇴거

</details>

### 3. 클라우드 버스팅(Cloud Bursting) 전략에서 온프레미스 리소스가 부족할 때 클라우드 노드로 워크로드를 이동시키는 방법은?

A. 수동으로 Pod 삭제 후 재생성
B. Node Affinity의 preferredDuringSchedulingIgnoredDuringExecution 사용
C. 모든 Pod를 클라우드에 배치
D. 클러스터 삭제 후 재생성

<details>
<summary>정답 보기</summary>

**정답: B. Node Affinity의 preferredDuringSchedulingIgnoredDuringExecution 사용**

**설명:**
클라우드 버스팅은 온프레미스 우선, 클라우드 대체 전략을 구현합니다.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: burst-workload
spec:
  replicas: 10
  template:
    spec:
      affinity:
        nodeAffinity:
          # 온프레미스 선호 (필수 아님)
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 100
            preference:
              matchExpressions:
              - key: location
                operator: In
                values: ["onprem"]
          - weight: 50
            preference:
              matchExpressions:
              - key: location
                operator: In
                values: ["cloud"]
      containers:
      - name: app
        image: myapp:v1
```

**클라우드 버스팅 패턴:**
```
[온프레미스 용량: 8 노드]    [클라우드 용량: 무제한]
      ↓ 선호                    ↓ 대체
  Pod 1-8 배치 ──────────> Pod 9+ 오버플로우
```

</details>

### 4. TopologySpreadConstraints를 사용하여 Pod를 여러 영역에 균등하게 분산시킬 때 maxSkew의 의미는?

A. 최소 Pod 수
B. 영역 간 Pod 수의 최대 차이
C. 총 Pod 수
D. 노드당 최대 Pod 수

<details>
<summary>정답 보기</summary>

**정답: B. 영역 간 Pod 수의 최대 차이**

**설명:**
`maxSkew`는 토폴로지 도메인(예: 영역) 간 Pod 수의 최대 불균형을 정의합니다.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: distributed-app
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
            app: distributed-app
```

**maxSkew=1 예시:**
```
Zone A: 2 Pods  |  Zone B: 2 Pods  |  Zone C: 2 Pods  (균형)
Zone A: 3 Pods  |  Zone B: 2 Pods  |  Zone C: 2 Pods  (Skew=1, 허용)
Zone A: 4 Pods  |  Zone B: 2 Pods  |  Zone C: 2 Pods  (Skew=2, 불허)
```

**whenUnsatisfiable 옵션:**
- **DoNotSchedule**: 제약 위반 시 스케줄링 거부
- **ScheduleAnyway**: 제약 위반해도 스케줄링 (best-effort)

</details>

### 5. 데이터 로컬리티를 고려한 워크로드 배치에서 데이터가 있는 노드에 Pod를 배치하는 방법은?

A. Random 스케줄링
B. 노드 레이블과 nodeSelector를 사용한 데이터 근접 배치
C. 항상 클라우드 노드 선택
D. Pod 이름 알파벳 순서

<details>
<summary>정답 보기</summary>

**정답: B. 노드 레이블과 nodeSelector를 사용한 데이터 근접 배치**

**설명:**
데이터 로컬리티를 위해 데이터가 저장된 노드에 레이블을 지정하고, 해당 레이블로 Pod를 배치합니다.

```bash
# 데이터 위치 노드 레이블링
kubectl label node storage-node-1 data-location=primary-storage
kubectl label node storage-node-2 data-location=replica-storage
```

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: data-processor
spec:
  template:
    spec:
      nodeSelector:
        data-location: primary-storage
      containers:
      - name: processor
        image: data-processor:v1
        volumeMounts:
        - name: local-data
          mountPath: /data
      volumes:
      - name: local-data
        hostPath:
          path: /mnt/data
```

**데이터 로컬리티 이점:**
- 네트워크 지연 최소화
- 데이터 전송 비용 절감
- 처리 성능 향상

</details>

### 6. Pod Anti-Affinity를 사용하여 같은 애플리케이션의 Pod가 동일 노드에 배치되지 않도록 하는 이유는?

A. 비용 절감
B. 고가용성 및 장애 격리
C. 네트워크 속도 향상
D. 스토리지 절약

<details>
<summary>정답 보기</summary>

**정답: B. 고가용성 및 장애 격리**

**설명:**
Pod Anti-Affinity는 동일 애플리케이션의 Pod를 서로 다른 노드에 분산시켜 단일 노드 장애 시에도 서비스 가용성을 유지합니다.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ha-webapp
spec:
  replicas: 3
  template:
    metadata:
      labels:
        app: ha-webapp
    spec:
      affinity:
        podAntiAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
          - labelSelector:
              matchExpressions:
              - key: app
                operator: In
                values: ["ha-webapp"]
            topologyKey: kubernetes.io/hostname
      containers:
      - name: web
        image: nginx:1.25
```

**결과:**
```
Node 1: ha-webapp-pod-1
Node 2: ha-webapp-pod-2
Node 3: ha-webapp-pod-3
(각 노드에 1개씩만 배치)
```

노드 장애 시 영향 받는 Pod는 1개뿐이며, 나머지 2개가 서비스를 계속 제공합니다.

</details>

