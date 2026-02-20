# 워크로드별 최적화

> **지원 버전**: EKS 1.29+, EKS Auto Mode GA
> **마지막 업데이트**: 2025년 2월

< [이전: 노드 생명주기](./07-node-lifecycle.md) | [목차](./README.md) | [다음: 마이그레이션 가이드](./09-migration-guide.md) >

---

이 문서에서는 다양한 워크로드 유형에 맞게 EKS Auto Mode를 최적화하는 방법을 설명합니다.

## 웹 서비스 (가용성 우선)

```yaml
# web-service-optimized.yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: web-tier
spec:
  template:
    metadata:
      labels:
        tier: web
    spec:
      requirements:
        # 범용 인스턴스
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["m"]
        - key: karpenter.k8s.aws/instance-size
          operator: In
          values: ["large", "xlarge", "2xlarge"]
        # On-Demand만 사용 (가용성 우선)
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["on-demand"]
      taints:
        - key: tier
          value: web
          effect: NoSchedule
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 5m
    budgets:
      - nodes: "10%"
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-frontend
spec:
  replicas: 10
  selector:
    matchLabels:
      app: web-frontend
  template:
    metadata:
      labels:
        app: web-frontend
    spec:
      tolerations:
        - key: tier
          value: web
          effect: NoSchedule
      nodeSelector:
        tier: web
      affinity:
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
            - weight: 100
              podAffinityTerm:
                labelSelector:
                  matchLabels:
                    app: web-frontend
                topologyKey: kubernetes.io/hostname
      containers:
        - name: web
          image: my-web-app:latest
          resources:
            requests:
              cpu: 500m
              memory: 512Mi
            limits:
              cpu: 1000m
              memory: 1Gi
          readinessProbe:
            httpGet:
              path: /health
              port: 8080
            initialDelaySeconds: 5
            periodSeconds: 10
          livenessProbe:
            httpGet:
              path: /health
              port: 8080
            initialDelaySeconds: 15
            periodSeconds: 20
```

## 배치 처리 (비용 우선, Spot)

```yaml
# batch-processing-optimized.yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: batch-tier
spec:
  template:
    metadata:
      labels:
        tier: batch
    spec:
      requirements:
        # 컴퓨팅 최적화
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["c"]
        - key: karpenter.k8s.aws/instance-size
          operator: In
          values: ["xlarge", "2xlarge", "4xlarge"]
        # Spot만 사용 (비용 우선)
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["spot"]
        # 다양한 인스턴스 타입으로 Spot 가용성 향상
        - key: karpenter.k8s.aws/instance-generation
          operator: In
          values: ["5", "6", "7"]
      taints:
        - key: tier
          value: batch
          effect: NoSchedule
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30s
---
apiVersion: batch/v1
kind: Job
metadata:
  name: data-processing
spec:
  parallelism: 20
  completions: 100
  backoffLimit: 10
  template:
    spec:
      tolerations:
        - key: tier
          value: batch
          effect: NoSchedule
      nodeSelector:
        tier: batch
      restartPolicy: OnFailure
      terminationGracePeriodSeconds: 30
      containers:
        - name: processor
          image: my-batch-processor:latest
          resources:
            requests:
              cpu: 2000m
              memory: 4Gi
            limits:
              cpu: 4000m
              memory: 8Gi
          env:
            - name: SPOT_AWARE
              value: "true"
```

## GPU 워크로드 (p5, g5)

```yaml
# gpu-workload-optimized.yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: gpu-tier
spec:
  template:
    metadata:
      labels:
        tier: gpu
        accelerator: nvidia
    spec:
      requirements:
        # GPU 인스턴스
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["g", "p"]
        - key: karpenter.k8s.aws/instance-gpu-manufacturer
          operator: In
          values: ["nvidia"]
        # 특정 GPU 인스턴스 타입
        - key: node.kubernetes.io/instance-type
          operator: In
          values: ["g5.xlarge", "g5.2xlarge", "g5.4xlarge", "p5.48xlarge"]
        # On-Demand (GPU는 Spot 가용성이 낮음)
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["on-demand"]
      taints:
        - key: nvidia.com/gpu
          value: "true"
          effect: NoSchedule
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: gpu-nodeclass
  limits:
    nvidia.com/gpu: 16
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 10m  # GPU는 시작 시간이 오래 걸림
---
apiVersion: eks.amazonaws.com/v1
kind: NodeClass
metadata:
  name: gpu-nodeclass
spec:
  amiFamily: AL2023
  blockDeviceMappings:
    - deviceName: /dev/xvda
      ebs:
        volumeSize: 200Gi  # 모델 캐싱을 위한 큰 볼륨
        volumeType: gp3
        iops: 6000
        throughput: 250
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ml-inference
spec:
  replicas: 2
  selector:
    matchLabels:
      app: ml-inference
  template:
    metadata:
      labels:
        app: ml-inference
    spec:
      tolerations:
        - key: nvidia.com/gpu
          value: "true"
          effect: NoSchedule
      nodeSelector:
        tier: gpu
      containers:
        - name: inference
          image: my-ml-model:latest
          resources:
            limits:
              nvidia.com/gpu: 1
            requests:
              cpu: 4000m
              memory: 16Gi
```

## AI/ML 학습 워크로드

```yaml
# ml-training-optimized.yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: ml-training
spec:
  template:
    metadata:
      labels:
        tier: ml-training
    spec:
      requirements:
        # 대규모 GPU 인스턴스
        - key: node.kubernetes.io/instance-type
          operator: In
          values: ["p5.48xlarge", "p4d.24xlarge"]
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["on-demand"]
      taints:
        - key: ml-training
          value: "true"
          effect: NoSchedule
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: ml-training-nodeclass
  limits:
    nvidia.com/gpu: 64
---
apiVersion: eks.amazonaws.com/v1
kind: NodeClass
metadata:
  name: ml-training-nodeclass
spec:
  amiFamily: AL2023
  # EFA 네트워킹 활성화
  blockDeviceMappings:
    - deviceName: /dev/xvda
      ebs:
        volumeSize: 500Gi
        volumeType: gp3
        iops: 16000
        throughput: 1000
---
apiVersion: kubeflow.org/v1
kind: PyTorchJob
metadata:
  name: distributed-training
spec:
  pytorchReplicaSpecs:
    Master:
      replicas: 1
      template:
        spec:
          tolerations:
            - key: ml-training
              value: "true"
              effect: NoSchedule
          nodeSelector:
            tier: ml-training
          containers:
            - name: pytorch
              image: my-training-image:latest
              resources:
                limits:
                  nvidia.com/gpu: 8
    Worker:
      replicas: 3
      template:
        spec:
          tolerations:
            - key: ml-training
              value: "true"
              effect: NoSchedule
          nodeSelector:
            tier: ml-training
          containers:
            - name: pytorch
              image: my-training-image:latest
              resources:
                limits:
                  nvidia.com/gpu: 8
```

## 워크로드 유형별 요약

| 워크로드 | 인스턴스 카테고리 | Capacity Type | Consolidation | expireAfter |
|----------|------------------|---------------|---------------|-------------|
| 웹 서비스 | m (범용) | On-Demand | WhenEmptyOrUnderutilized, 5m | 168h |
| 배치 처리 | c (컴퓨팅) | Spot | WhenEmpty, 30s | 72h |
| GPU 추론 | g, p | On-Demand | WhenEmpty, 10m | 336h |
| ML 학습 | p5, p4d | On-Demand | WhenEmpty, 30m | 336h |
| 개발/테스트 | t, m | Spot | WhenEmptyOrUnderutilized, 1m | 24h |

## 추가 최적화 팁

### 리소스 요청 최적화

```yaml
# 워크로드별 적절한 리소스 설정
containers:
  - name: app
    resources:
      requests:
        # 실제 사용량의 1.2-1.5배
        cpu: 250m
        memory: 256Mi
      limits:
        # requests의 2배 이내
        cpu: 500m
        memory: 512Mi
```

### 토폴로지 분산

```yaml
# 고가용성을 위한 분산 설정
topologySpreadConstraints:
  - maxSkew: 1
    topologyKey: topology.kubernetes.io/zone
    whenUnsatisfiable: DoNotSchedule
    labelSelector:
      matchLabels:
        app: my-app
```

---

< [이전: 노드 생명주기](./07-node-lifecycle.md) | [목차](./README.md) | [다음: 마이그레이션 가이드](./09-migration-guide.md) >
