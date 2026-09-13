# 워크로드별 최적화

> **지원 버전**: EKS Auto Mode GA; 예제 검토 기준 EKS 1.36
> **마지막 업데이트**: 2026년 9월 12일

워크로드에 배치·복구 정책을 맞춘 뒤 실제 용량·성능·비용을 검증합니다. Web/batch 예제는 제한된 실습 구성입니다. GPU 예제는 **비활성 구성 template**이며 검증된 학습/추론 애플리케이션이 아닙니다. 추론은 replicas 0, legacy training job은 suspend 상태입니다. GPU/model 실행·실제 클러스터 배포·benchmark는 수행하지 않았습니다.

[운영 및 관리](./05-operations.md)의 계정/context 검사를 사용하세요. 모든 pool은 동적이며 물리 용량을 예약하지 않습니다. 필요한 예제만 선택하고 `default`/커스텀 NodeClass identity·subnet 접근과 지속되는 노드/스토리지 비용을 검토합니다. Taint/selector는 배치 제어이지 테넌트 보안 경계가 아닙니다.

## 웹 서비스: 가용성과 복구

On-Demand는 Spot 회수 이벤트를 피하지만 용량·가용성을 보장하지는 않습니다. Replica, topology, readiness, disruption policy, 영구 상태와 장애 복구 검증이 필요합니다.

다음은 복제본 3개와 모두 정상일 때 자발적 축출 1개를 허용하는 PDB입니다. `N-1`을 PDB의 실제 값으로 가정하지 않습니다. 이전 복제본 10개는 크기 예시이지 보편적 요구가 아닙니다. Nginx 이미지/digest·non-root 구성은 운영 장에서 확인한 것을 사용하며 8080의 `/`를 probe합니다. 임의 애플리케이션 이미지에 `/health`가 있다고 가정할 수는 없습니다.

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: workload-lab
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: v1.36
    pod-security.kubernetes.io/warn: restricted
    pod-security.kubernetes.io/warn-version: v1.36
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/audit-version: v1.36
---
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: web-tier
spec:
  template:
    spec:
      requirements:
      - key: eks.amazonaws.com/instance-category
        operator: In
        values:
        - m
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - on-demand
      - key: kubernetes.io/arch
        operator: In
        values:
        - amd64
        - arm64
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
      expireAfter: 168h
      terminationGracePeriod: 24h
      taints:
      - key: workload-lab
        value: web-tier
        effect: NoSchedule
    metadata:
      labels:
        workload-lab: web-tier
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 5m
    budgets:
    - nodes: 10%
  limits:
    cpu: '32'
    memory: 128Gi
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-frontend
  namespace: workload-lab
spec:
  replicas: 3
  selector:
    matchLabels:
      app: web-frontend
  template:
    metadata:
      labels:
        app: web-frontend
    spec:
      containers:
      - name: web
        image: nginxinc/nginx-unprivileged:1.30.4@sha256:cb92301e719d6639028de775fe8b28e15f58343aca5e5372001311958aafb300
        resources:
          requests:
            cpu: 500m
            memory: 512Mi
          limits:
            cpu: 1000m
            memory: 1Gi
        ports:
        - containerPort: 8080
        securityContext:
          allowPrivilegeEscalation: false
          capabilities:
            drop:
            - ALL
          readOnlyRootFilesystem: true
        volumeMounts:
        - name: tmp
          mountPath: /tmp
        readinessProbe:
          httpGet:
            path: /
            port: 8080
          periodSeconds: 5
        startupProbe:
          httpGet:
            path: /
            port: 8080
          periodSeconds: 2
          failureThreshold: 30
        livenessProbe:
          httpGet:
            path: /
            port: 8080
          periodSeconds: 20
          failureThreshold: 3
      terminationGracePeriodSeconds: 60
      automountServiceAccountToken: false
      nodeSelector:
        karpenter.sh/nodepool: web-tier
      tolerations:
      - key: workload-lab
        operator: Equal
        value: web-tier
        effect: NoSchedule
      securityContext:
        runAsNonRoot: true
        runAsUser: 101
        runAsGroup: 101
        fsGroup: 101
        seccompProfile:
          type: RuntimeDefault
      volumes:
      - name: tmp
        emptyDir:
          sizeLimit: 128Mi
      topologySpreadConstraints:
      - maxSkew: 1
        minDomains: 2
        topologyKey: topology.kubernetes.io/zone
        whenUnsatisfiable: DoNotSchedule
        nodeAffinityPolicy: Honor
        nodeTaintsPolicy: Honor
        labelSelector:
          matchLabels:
            app: web-frontend
      - maxSkew: 1
        topologyKey: kubernetes.io/hostname
        whenUnsatisfiable: ScheduleAnyway
        labelSelector:
          matchLabels:
            app: web-frontend
---
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: web-frontend
  namespace: workload-lab
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: web-frontend
```

Hard zone spread는 적합한 domain을 최소 2개 요구하므로 용량이 없으면 Pod가 Pending일 수 있습니다. Soft hostname spread는 선호이며 노드당 복제본 1개나 3-AZ 보장이 아닙니다. Label 일치·subnet 범위·장애 정책을 확인하세요.

Startup probe는 느린 초기화 중 조기 liveness 검사를 막습니다. Readiness는 endpoint 적격성, liveness는 컨테이너 재시작을 제어합니다. 애플리케이션에 맞게 임계값을 정하고 공통 의존 서비스 장애 때문에 모든 replica를 재시작하는 liveness 검사는 피하세요. 예시 probe 간격은 실측 startup SLA가 아닙니다.

## 배치: 재시도와 Checkpoint 복구는 다름

Interruption, deadline 미준수와 Spot 용량 부재를 감당하는 작업에만 Spot을 사용합니다. 이 pool에는 On-Demand fallback이 없습니다. `restartPolicy: OnFailure`는 살아 있는 Pod에서 실패한 컨테이너를 재시작할 수 있지만 종료된 노드의 process memory를 복구하지 못합니다. `SPOT_AWARE=true`도 애플리케이션 구현이 없으면 단순 환경 변수입니다.

다음 Indexed Job은 논리 shard 번호만 출력하는 **smoke 예제**입니다. 이전 parallelism 20/completions 100 대신 병렬 2개·완료 5개·deadline·제한된 재시도를 사용하며 데이터 처리 구현은 아닙니다. 확인한 BusyBox 이미지 index는 Linux amd64/arm64를 포함하지만 이번 감사에서 이미지를 실행하지 않았습니다.

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: batch-tier
spec:
  template:
    spec:
      requirements:
      - key: eks.amazonaws.com/instance-category
        operator: In
        values:
        - c
        - m
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - spot
      - key: kubernetes.io/arch
        operator: In
        values:
        - amd64
        - arm64
      - key: eks.amazonaws.com/instance-generation
        operator: Gt
        values:
        - '4'
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
      expireAfter: 168h
      terminationGracePeriod: 24h
      taints:
      - key: workload-lab
        value: batch-tier
        effect: NoSchedule
    metadata:
      labels:
        workload-lab: batch-tier
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30s
    budgets:
    - nodes: 10%
  limits:
    cpu: '16'
    memory: 64Gi
---
apiVersion: batch/v1
kind: Job
metadata:
  name: indexed-smoke
  namespace: workload-lab
spec:
  completionMode: Indexed
  parallelism: 2
  completions: 5
  backoffLimit: 2
  activeDeadlineSeconds: 300
  ttlSecondsAfterFinished: 3600
  template:
    metadata:
      labels:
        app: indexed-smoke
    spec:
      restartPolicy: Never
      automountServiceAccountToken: false
      terminationGracePeriodSeconds: 30
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        runAsGroup: 1000
        seccompProfile:
          type: RuntimeDefault
      containers:
      - name: processor
        image: busybox:1.37.0@sha256:9db7b59979c38555a39def84a31fb98b5296952f9e3afd4f6f11f05b07adfab0
        command:
        - /bin/sh
        - -ec
        args:
        - printf 'logical shard=%s; smoke only\n' "$JOB_COMPLETION_INDEX"
        env:
        - name: JOB_COMPLETION_INDEX
          valueFrom:
            fieldRef:
              fieldPath: metadata.annotations['batch.kubernetes.io/job-completion-index']
        resources:
          requests:
            cpu: 100m
            memory: 32Mi
          limits:
            cpu: 500m
            memory: 64Mi
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop:
            - ALL
      nodeSelector:
        karpenter.sh/nodepool: batch-tier
      tolerations:
      - key: workload-lab
        operator: Equal
        value: batch-tier
        effect: NoSchedule
```

실제 작업에는 멱등 output commit, 영구 checkpoint와 resume 로직이 필요합니다. Indexed Job도 장애 상황에서 같은 index를 여러 번 실행할 수 있으므로 exactly-once 부수 효과를 가정하지 마세요. TTL 정리 전에 필요한 로그·artifact를 export합니다. Node-local cache·emptyDir는 영구 checkpoint가 아닙니다.

`WhenEmpty`는 해당 애플리케이션 작업이 사라진 뒤 노드를 정리할 수 있습니다. 30초 `consolidateAfter`는 debounce이며 실행 중 작업 완료나 30초 후 노드 삭제 보장이 아닙니다. Drift·expiration·interruption은 별도 수명 주기 경로로 남습니다.

## GPU 추론: 노드 전체 사양 확인

Auto Mode는 NVIDIA driver/device 지원과 Bottlerocket 이미지를 관리합니다. 이전 NodeClass의 `amiFamily: AL2023`·`blockDeviceMappings`는 지원하지 않습니다.

| 인스턴스 | GPU | GPU 메모리 | Host vCPU/RAM |
|----------|-----|------------|---------------|
| g5.xlarge | A10G 1개 | 24 GB | 4 / 16 GiB |
| g5.2xlarge | A10G 1개 | 24 GB | 8 / 32 GiB |
| g5.4xlarge | A10G 1개 | 24 GB | 16 / 64 GiB |
| g5.12xlarge | A10G 4개 | 합계 96 GB, 각각 24 GB | 48 / 192 GiB |
| p5.48xlarge | H100 8개 | 합계 640 GB, 각각 80 GB | 192 / 2 TiB |

최신·모든 지역에서 사용 가능한 GPU 목록이 아닌 예시입니다. GPU 메모리 합계는 단일 장치의 연속 메모리가 아닙니다. 특히 이전 Pod의 4 CPU/16Gi request는 노드/system 예약·DaemonSet overhead를 제외하면 g5.xlarge에 들어가지 않습니다. 추론 pool은 더 큰 G5를 허용하며 검토되지 않은 1-GPU 서비스 때문에 8-GPU 학습 노드를 선택하지 않도록 구성합니다.

```yaml
apiVersion: eks.amazonaws.com/v1
kind: NodeClass
metadata:
  name: gpu-nodeclass
spec:
  instanceProfile: eks-node-instance-profile
  subnetSelectorTerms:
  - tags:
      Name: private-subnet
  securityGroupSelectorTerms:
  - tags:
      Name: worker-restricted
  advancedNetworking:
    associatePublicIPAddress: false
  ephemeralStorage:
    size: 200Gi
    iops: 6000
    throughput: 250
---
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: gpu-tier
spec:
  template:
    spec:
      requirements:
      - key: eks.amazonaws.com/instance-category
        operator: In
        values:
        - g
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - on-demand
      - key: kubernetes.io/arch
        operator: In
        values:
        - amd64
      - key: node.kubernetes.io/instance-type
        operator: In
        values:
        - g5.2xlarge
        - g5.4xlarge
      - key: eks.amazonaws.com/instance-gpu-manufacturer
        operator: In
        values:
        - nvidia
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: gpu-nodeclass
      expireAfter: 168h
      terminationGracePeriod: 24h
      taints:
      - key: workload-lab
        value: gpu-tier
        effect: NoSchedule
      - key: nvidia.com/gpu
        value: 'true'
        effect: NoSchedule
    metadata:
      labels:
        workload-lab: gpu-tier
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 10m
    budgets:
    - nodes: 10%
  limits:
    cpu: '64'
    memory: 256Gi
    nvidia.com/gpu: '4'
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ml-inference
  namespace: workload-lab
spec:
  replicas: 0
  selector:
    matchLabels:
      app: ml-inference
  template:
    metadata:
      labels:
        app: ml-inference
    spec:
      automountServiceAccountToken: false
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        runAsGroup: 1000
        seccompProfile:
          type: RuntimeDefault
      containers:
      - name: inference
        image: registry.example.invalid/reviewed-inference:replace-me
        resources:
          requests:
            cpu: '4'
            memory: 16Gi
            nvidia.com/gpu: 1
          limits:
            cpu: '4'
            memory: 16Gi
            nvidia.com/gpu: 1
        securityContext:
          allowPrivilegeEscalation: false
          capabilities:
            drop:
            - ALL
      nodeSelector:
        karpenter.sh/nodepool: gpu-tier
      tolerations:
      - key: workload-lab
        operator: Equal
        value: gpu-tier
        effect: NoSchedule
      - key: nvidia.com/gpu
        operator: Equal
        value: 'true'
        effect: NoSchedule
```

의도적으로 무효인 예시 registry/image를 검토된 immutable image로 바꾸고 실제 entrypoint·model/input 경로·probe·스토리지·제한된 워크로드 identity를 제공하기 전까지 `replicas: 0`을 유지합니다. Driver/CUDA/library와 non-root UID 1000/security policy 호환성을 그 이미지로 검증하세요. 추론 runtime 실행 검증은 하지 않았습니다.

`ephemeralStorage`는 노드 스토리지 설정이며 영구 model/checkpoint 저장소나 throughput 보장이 아닙니다. 실제 allocatable storage와 backing device를 확인하세요. Node root/data EBS 암호화가 임의 PVC 암호화를 입증하지 않습니다. GPU 개수 limit은 pool 리소스 제어이며 전체 달러 상한이 아니고 급격한 프로비저닝에서 일시 초과할 수도 있습니다. 이전 16/20-GPU는 크기 예시이며 실습은 더 작은 4-GPU 상한을 사용합니다.

`WhenEmpty`·10분 debounce는 작업 종료 후 churn을 줄일 수 있지만 GPU 초기화까지 배치를 지연하거나 warm node를 보장하지는 않습니다. 미리 확보한 desired 용량이 필요하면 별도 limits/consolidation 의미와 지속 비용을 가진 static NodePool도 검토할 수 있습니다.

## 분산 학습과 EFA

Auto Mode의 EFA는 현재 지원 기능입니다. **디스크 설정 옆 주석만으로 활성화되지 않습니다.** 지원 NodeClass 필드는 `advancedNetworking.networkInterfaces`이며 device-plugin 경로는 `vpc.amazonaws.com/efa`를 발행합니다.

학습 활성화 전에 다음을 검토하세요.

- Auto Mode는 현재 EFA **DRA 경로를 지원하지 않습니다**. 다른 compute mode의 DRANET ResourceClaim 예제를 복사하지 말고 EFA device plugin을 사용합니다.
- Auto Mode가 NVIDIA/Neuron host driver를 관리하지만 EFA host 의존성이 있다고 별도 EFA device plugin의 설치·Ready가 입증되지는 않습니다.
- EFA-only interface는 RDMA용이며 Pod IP를 운반하지 않습니다. Primary interface는 card 0/device 0/type `interface`입니다. 예제는 `efa-only` 장치 4개와 Pod IP용 `/28` prefix 1개를 추가합니다.
- Static interface 구성은 IPv4만 지원하며 시작 후 IP/prefix/ENI를 추가하지 않습니다. Multi-interface와 `associatePublicIPAddress`를 조합하지 마세요. 워크로드·system Pod IP 수를 계획합니다.
- 호환되는 기존 placement group, 같은 private AZ/subnet과 필요한 self-reference 통신을 허용한 검토된 EFA security group을 사용합니다. 예시 AZ/group 이름은 placeholder이며 그 위치의 P5 용량 증거가 아닙니다.
- EFA/libfabric/NCCL, process launch/rendezvous, GPU/EFA locality와 필요한 hugepage/memory-lock 설정을 확인합니다. 장치 4개 예제는 P5 최대 네트워크 대역폭이나 Auto Mode Bottlerocket의 자동 GPU/EFA 정렬 보장이 아닙니다.

다음은 P4d/P5 worker를 서로 바꿔 쓸 수 있다고 가정하지 않는 동일 P5 pool입니다. P4d는 별도 호환 pool/runtime 검증이 필요한 대안으로 남습니다. 이전 500Gi/16,000 IOPS/1,000 throughput과 추가 2,000Gi data disk는 예시이며, 지원 NodeClass가 임의 추가 block device를 만드는 것은 아닙니다.

```yaml
apiVersion: eks.amazonaws.com/v1
kind: NodeClass
metadata:
  name: ml-training-nodeclass
spec:
  instanceProfile: eks-node-instance-profile
  subnetSelectorTerms:
  - tags:
      Name: private-subnet
  securityGroupSelectorTerms:
  - tags:
      Name: reviewed-efa-security-group
  advancedNetworking:
    networkInterfaces:
    - networkCardIndex: 0
      deviceIndex: 0
      interfaceType: interface
      secondaryIPv4PrefixCount: 1
    - networkCardIndex: 0
      deviceIndex: 1
      interfaceType: efa-only
    - networkCardIndex: 1
      deviceIndex: 0
      interfaceType: efa-only
    - networkCardIndex: 2
      deviceIndex: 0
      interfaceType: efa-only
    - networkCardIndex: 3
      deviceIndex: 0
      interfaceType: efa-only
  ephemeralStorage:
    size: 500Gi
    iops: 16000
    throughput: 1000
  placementGroupSelector:
    name: reviewed-ml-training-pg
---
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: ml-training
spec:
  template:
    spec:
      requirements:
      - key: eks.amazonaws.com/instance-category
        operator: In
        values:
        - p
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - on-demand
      - key: kubernetes.io/arch
        operator: In
        values:
        - amd64
      - key: node.kubernetes.io/instance-type
        operator: In
        values:
        - p5.48xlarge
      - key: topology.kubernetes.io/zone
        operator: In
        values:
        - ap-northeast-2a
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: ml-training-nodeclass
      expireAfter: 168h
      terminationGracePeriod: 24h
      taints:
      - key: workload-lab
        value: ml-training
        effect: NoSchedule
      - key: nvidia.com/gpu
        value: 'true'
        effect: NoSchedule
    metadata:
      labels:
        workload-lab: ml-training
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30m
    budgets:
    - nodes: 10%
  limits:
    cpu: '960'
    memory: 10Ti
    nvidia.com/gpu: '40'
```

### 유지한 Legacy PyTorchJob 구조

`kubeflow.org/v1 PyTorchJob`에는 **Kubeflow Training Operator V1**이 필요하며 구조 검증에는 릴리스된 v1.9.3 CRD를 사용했습니다. 현재 Kubeflow Trainer의 TrainJob/Runtime API는 다릅니다. Auto Mode에서 NodePool을 만든다고 어느 operator도 자동 설치되지 않습니다.

Template은 suspend 상태이며 의도적으로 무효인 placeholder 이미지를 사용합니다. Master 1개·worker 3개, 노드별 GPU process 8개·Pod별 EFA 장치 4개로 활성화 시 **GPU 32개/8-GPU 노드 4대**를 표현합니다. Pool의 40-GPU 상한은 교체 여유를 포함한 해당 사양 노드 최대 5대의 계획 제한이며 예약이나 강제 청구 상한은 아닙니다.

```yaml
apiVersion: kubeflow.org/v1
kind: PyTorchJob
metadata:
  name: distributed-training
  namespace: workload-lab
spec:
  nprocPerNode: '8'
  runPolicy:
    suspend: true
    activeDeadlineSeconds: 3600
    backoffLimit: 1
    cleanPodPolicy: None
  pytorchReplicaSpecs:
    Master:
      replicas: 1
      restartPolicy: Never
      template:
        metadata:
          labels:
            app: distributed-training
        spec:
          automountServiceAccountToken: false
          securityContext:
            runAsNonRoot: true
            runAsUser: 1000
            runAsGroup: 1000
            seccompProfile:
              type: RuntimeDefault
          containers:
          - name: pytorch
            image: registry.example.invalid/reviewed-training:replace-me
            resources:
              requests:
                cpu: '32'
                memory: 128Gi
                nvidia.com/gpu: 8
                vpc.amazonaws.com/efa: 4
              limits:
                cpu: '32'
                memory: 128Gi
                nvidia.com/gpu: 8
                vpc.amazonaws.com/efa: 4
            securityContext:
              allowPrivilegeEscalation: false
              capabilities:
                drop:
                - ALL
          nodeSelector:
            karpenter.sh/nodepool: ml-training
          tolerations:
          - key: workload-lab
            operator: Equal
            value: ml-training
            effect: NoSchedule
          - key: nvidia.com/gpu
            operator: Equal
            value: 'true'
            effect: NoSchedule
    Worker:
      replicas: 3
      restartPolicy: Never
      template:
        metadata:
          labels:
            app: distributed-training
        spec:
          automountServiceAccountToken: false
          securityContext:
            runAsNonRoot: true
            runAsUser: 1000
            runAsGroup: 1000
            seccompProfile:
              type: RuntimeDefault
          containers:
          - name: pytorch
            image: registry.example.invalid/reviewed-training:replace-me
            resources:
              requests:
                cpu: '32'
                memory: 128Gi
                nvidia.com/gpu: 8
                vpc.amazonaws.com/efa: 4
              limits:
                cpu: '32'
                memory: 128Gi
                nvidia.com/gpu: 8
                vpc.amazonaws.com/efa: 4
            securityContext:
              allowPrivilegeEscalation: false
              capabilities:
                drop:
                - ALL
          nodeSelector:
            karpenter.sh/nodepool: ml-training
          tolerations:
          - key: workload-lab
            operator: Equal
            value: ml-training
            effect: NoSchedule
          - key: nvidia.com/gpu
            operator: Equal
            value: 'true'
            effect: NoSchedule
```

Unsuspend 전에 operator의 분산 launch 계약을 구현한 검토된 image/entrypoint, 실제 dataset 경로와 영구 checkpoint/artifact export를 준비하세요. Operator, queue/gang scheduling, 4-node 용량, DNS/rendezvous, network rule, runtime 권한과 deadline을 검증합니다. 완전한 프로덕션 학습 절차가 아닙니다. 가속기 runtime이 충족할 수 없는 권한을 요구하면 Restricted namespace template과 별도로 검토된 workload policy가 필요할 수 있으며, 단순히 클러스터 전체 admission 보안을 끄면 안 됩니다.

이미 실행 중인 legacy PyTorchJob을 suspend하면 active Pod/PodGroup이 삭제됩니다. Checkpoint 작업이 아닙니다. `cleanPodPolicy: None`은 완료 Pod를 검사용으로 남기지만 artifact를 export하지 않습니다. 영구 export 후 PVC·노드·별도 소유 reservation까지 정리를 검토하세요.

### 실제 장치 용량 관측

다음 읽기 전용 snapshot은 실제 allocatable과 Ready condition을 보여줍니다. GPU/EFA 값 부재나 API 오류를 장치 설정 성공으로 해석하지 마세요.

```bash
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s get nodes \
  -l eks.amazonaws.com/compute-type=auto -o json |
jq '[.items[]|{name:.metadata.name,
  instanceType:.metadata.labels["node.kubernetes.io/instance-type"],
  pool:.metadata.labels["karpenter.sh/nodepool"],
  allocatable:{cpu:.status.allocatable.cpu,memory:.status.allocatable.memory,
    gpu:.status.allocatable["nvidia.com/gpu"],efa:.status.allocatable["vpc.amazonaws.com/efa"]},
  conditions:[.status.conditions[]?|select(.type=="Ready")|{type,status,reason}]}]'
```

## 리소스와 아키텍처 결정

| 워크로드 | 정책 후보 | 여전히 필요한 검증 |
|----------|-----------|--------------------|
| Web/API | On-Demand 또는 검토한 혼합 용량·적당한 consolidation | 가용성 예산·replica·runtime 아키텍처·실측 latency |
| Batch/CI | 재시작·deadline을 허용할 때 Spot | 멱등성·영구 진행 상태·재시도·용량 부재 |
| Database/streaming | 상태를 고려한 배치·disruption | Quorum·volume topology·복구·partition 동작 |
| GPU 추론 | Model에 맞는 GPU/CPU/RAM, 필요하면 warm capacity | Image/driver·probe·cold start·비용 |
| 분산 학습 | 동일 가속기 pool과 검증한 network/runtime | Gang capacity·checkpoint/export·EFA 장치·placement |

이전 expiry 24h/72h/168h/336h, consolidation 30s/1m/5m/10m/15m/30m은 정책 예시이며 워크로드 유형별 기본값이 아닙니다. Auto Mode 최대 수명과 별도 termination grace도 적용됩니다.

CPU 중심 워크로드의 이전 2 CPU/2Gi request·4 CPU/4Gi limit은 가능한 burst 정책 예시이지 보편적 크기가 아닙니다. Memory 중심 워크로드도 8Gi request/limit만 같고 CPU가 다르면 Guaranteed QoS가 되지 않습니다. Guaranteed QoS는 모든 해당 컨테이너·리소스 조건도 충족해야 하며 memory limit에서도 OOM은 가능합니다. 이전 사용량 1.2–1.5배·request 2배 공식에는 확인된 일반 성능 근거가 없습니다.

Device-plugin API의 GPU는 정수 extended resource입니다. Limit을 지정하고 request도 지정한다면 일치시킵니다. Request만 쓰는 방식은 GPU 패턴이 아닙니다. CPU/memory request 외에 필수 system 작업의 node allocatable 여유도 필요합니다. Limit만 줄여도 일반적인 request 기반 bin-packing이 개선되는 것은 아닙니다.

### 다중 아키텍처 검증

`nginx:latest` grep 대신 고정된 image index를 확인합니다. 두 platform이 있는 index는 필요한 packaging 확인이지만 native 의존성·애플리케이션 동작까지 입증하지는 않습니다.

```bash
: "${IMAGE_REF:?Set a reviewed image reference pinned by digest}"
if ! [[ "$IMAGE_REF" =~ @sha256:[0-9a-f]{64}$ ]]; then
  printf 'Use an immutable sha256 digest reference.\n' >&2
  exit 1
fi
docker buildx imagetools inspect --raw "$IMAGE_REF" > "$WORK_DIR/image-index.json"
jq -e '[.manifests[]?.platform |
         select(.os=="linux" and (.architecture=="amd64" or .architecture=="arm64")) |
         .architecture] | unique | sort == ["amd64","arm64"]' \
  "$WORK_DIR/image-index.json"
```

검토한 자체 Dockerfile에 대해 다음은 불명확한 image를 게시하지 않고 로컬 OCI archive를 생성합니다.

```bash
: "${BUILD_CONTEXT:?Set the reviewed Dockerfile directory}"
test -f "$BUILD_CONTEXT/Dockerfile"
docker buildx build --platform linux/amd64,linux/arm64 \
  --output "type=oci,dest=$WORK_DIR/app-multiarch.tar" "$BUILD_CONTEXT"
```

적합한 Buildx builder, native worker 또는 올바른 emulation/cross-compilation이 필요합니다. 정상 registry 절차로 게시하기 전에 아키텍처별 애플리케이션 테스트를 실행하세요. 이전 Spot/Graviton 혼합 ~40%는 미검증 추정이며 [비용 관리](./06-cost-management.md)처럼 실제 유효 작업 비용을 비교합니다.

## 참고 자료

- [Auto Mode AI/ML compute](https://docs.aws.amazon.com/eks/latest/userguide/ml-node-pools.html)
- [NodeClass storage and static network interfaces](https://docs.aws.amazon.com/eks/latest/userguide/create-node-class.html)
- [EFA device management, including Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/device-management-efa.html)
- [G5 instance specifications](https://aws.amazon.com/ec2/instance-types/g5/)
- [P5 instance specifications](https://aws.amazon.com/ec2/instance-types/p5/)
- [Kubernetes Jobs and Indexed Jobs](https://kubernetes.io/docs/concepts/workloads/controllers/job/)
- [Kubernetes GPU scheduling](https://kubernetes.io/docs/tasks/manage-gpus/scheduling-gpus/)
- [Resource requests, limits and quantities](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/)
- [Topology spread constraints](https://kubernetes.io/docs/concepts/scheduling-eviction/topology-spread-constraints/)
- [Startup, readiness and liveness probes](https://kubernetes.io/docs/concepts/configuration/liveness-readiness-startup-probes/)
- [Training Operator v1.9.3 PyTorchJob CRD](https://github.com/kubeflow/training-operator/blob/v1.9.3/manifests/base/crds/kubeflow.org_pytorchjobs.yaml)
- [Kubeflow Trainer and legacy-v1 migration](https://github.com/kubeflow/trainer)
- [Docker multi-platform builds](https://docs.docker.com/build/building/multi-platform/)

< [이전: 노드 생명주기](./07-node-lifecycle.md) | [목차](./README.md) | [다음: 마이그레이션 가이드](./09-migration-guide.md) >
