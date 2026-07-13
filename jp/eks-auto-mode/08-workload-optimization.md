# ワークロード固有の最適化

> **対応バージョン**: EKS 1.29+, EKS Auto Mode GA
> **最終更新**: February 19, 2026

このガイドでは、web services、batch processing、GPU workloads、AI/ML training など、さまざまなワークロードタイプに合わせて EKS Auto Mode configurations を最適化する方法を説明します。

---

## Web Services（可用性優先）

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
        # General-purpose instances
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["m"]
        - key: karpenter.k8s.aws/instance-size
          operator: In
          values: ["large", "xlarge", "2xlarge"]
        # Use only On-Demand (availability first)
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

### Web Services 最適化サマリー

| 観点 | 推奨事項 | 理由 |
|--------|----------------|-----------|
| Capacity type | On-Demand | 高可用性の要件 |
| Instance family | M-series（general purpose） | CPU/メモリのバランス |
| Anti-affinity | ホスト名ごと | nodes 全体に分散 |
| Health checks | readiness と liveness の両方 | 障害をすばやく検出 |
| PDB | minAvailable: N-1 | 更新中も service を維持 |

---

## Batch Processing（コスト優先、Spot）

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
        # Compute-optimized
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["c"]
        - key: karpenter.k8s.aws/instance-size
          operator: In
          values: ["xlarge", "2xlarge", "4xlarge"]
        # Use only Spot (cost first)
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["spot"]
        # Various instance types for better Spot availability
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

### Batch Processing 最適化サマリー

| 観点 | 推奨事項 | 理由 |
|--------|----------------|-----------|
| Capacity type | Spot のみ | 最大限のコスト削減 |
| Instance family | C-series（compute optimized） | CPU 集約型ワークロード |
| Instance diversity | 複数世代 | Spot の可用性を向上 |
| Restart policy | OnFailure | Spot interrupts に対応 |
| Consolidation | 積極的（30s） | jobs 後のすばやいクリーンアップ |

---

## GPU Workloads（p5、g5）

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
        # GPU instances
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["g", "p"]
        - key: karpenter.k8s.aws/instance-gpu-manufacturer
          operator: In
          values: ["nvidia"]
        # Specific GPU instance types
        - key: node.kubernetes.io/instance-type
          operator: In
          values: ["g5.xlarge", "g5.2xlarge", "g5.4xlarge", "p5.48xlarge"]
        # On-Demand (GPU Spot availability is low)
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
    consolidateAfter: 10m  # GPU takes longer to start
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
        volumeSize: 200Gi  # Large volume for model caching
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

### GPU Instance 選択ガイド

| Instance | GPUs | GPU Memory | Use Case |
|----------|------|------------|----------|
| g5.xlarge | 1x A10G | 24GB | 小規模 inference |
| g5.2xlarge | 1x A10G | 24GB | 中規模 inference |
| g5.4xlarge | 1x A10G | 24GB | 大規模 inference |
| g5.12xlarge | 4x A10G | 96GB | マルチモデル serving |
| p5.48xlarge | 8x H100 | 640GB | 大規模 training |

### GPU 最適化サマリー

| 観点 | 推奨事項 | 理由 |
|--------|----------------|-----------|
| Capacity type | On-Demand | GPU Spot の可用性は限定的 |
| Storage | 200GB+ gp3 | モデル caching、checkpoints |
| Consolidation | 緩やか（10m） | GPU startup は遅い |
| Limits | nvidia.com/gpu limit を設定 | GPU コストの runaway を防止 |

---

## AI/ML Training Workloads

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
        # Large-scale GPU instances
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
  # Enable EFA networking
  blockDeviceMappings:
    - deviceName: /dev/xvda
      ebs:
        volumeSize: 500Gi
        volumeType: gp3
        iops: 16000
        throughput: 1000
    # Additional volume for training data
    - deviceName: /dev/xvdb
      ebs:
        volumeSize: 2000Gi
        volumeType: gp3
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

### ML Training 最適化サマリー

| 観点 | 推奨事項 | 理由 |
|--------|----------------|-----------|
| Instance type | p5.48xlarge、p4d.24xlarge | 最大 GPU capacity |
| Storage | 500GB+ root、2TB+ data | 大規模 datasets、checkpoints |
| IOPS | 16000+ | checkpoint writes を高速化 |
| Networking | EFA-enabled | distributed training |
| Framework | PyTorchJob、TFJob | native distributed support |

---

## ワークロードタイプ早見表

| ワークロード | NodePool Strategy | Instance Types | Capacity | Consolidation |
|----------|-------------------|----------------|----------|---------------|
| Web services | Availability-first | m-series | On-Demand | 中程度（5m） |
| API backend | Mixed | m/c-series | Mixed | 中程度（5m） |
| Batch processing | Cost-first | c-series | Spot only | 積極的（30s） |
| CI/CD | Cost-first | c/m-series | Spot preferred | 積極的（1m） |
| Databases | Stability-first | r-series | On-Demand | 保守的（10m） |
| GPU inference | Availability-first | g5-series | On-Demand | 緩やか（10m） |
| ML training | Performance-first | p5/p4d | On-Demand | 緩やか（15m） |
| Stream processing | Balanced | m/c-series | Mixed | 中程度（5m） |

---

## Pod Resource ガイドライン

### CPU-Bound ワークロード

```yaml
resources:
  requests:
    cpu: 2000m      # Request what you need
    memory: 2Gi
  limits:
    cpu: 4000m      # Allow some burst
    memory: 4Gi
```

### Memory-Bound ワークロード

```yaml
resources:
  requests:
    cpu: 500m
    memory: 8Gi     # Request what you need
  limits:
    cpu: 1000m
    memory: 8Gi     # Limit = request (no overcommit)
```

### GPU Workloads

```yaml
resources:
  requests:
    cpu: 4000m
    memory: 16Gi
  limits:
    nvidia.com/gpu: 1   # GPU limits are always required
    cpu: 8000m
    memory: 32Gi
```

---

< [前へ: Node Lifecycle](./07-node-lifecycle.md) | [目次](./README.md) | [次へ: Migration Guide](./09-migration-guide.md) >
