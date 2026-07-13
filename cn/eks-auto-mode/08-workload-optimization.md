# 工作负载特定优化

> **支持的版本**: EKS 1.29+, EKS Auto Mode GA
> **最后更新**: February 19, 2026

本指南介绍如何针对不同工作负载类型优化 EKS Auto Mode 配置，包括 Web 服务、批处理、GPU 工作负载以及 AI/ML 训练。

---

## Web 服务（可用性优先）

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

### Web 服务优化摘要

| 方面 | 建议 | 理由 |
|--------|----------------|-----------|
| 容量类型 | On-Demand | 高可用性要求 |
| 实例系列 | M-series（通用型） | CPU/内存均衡 |
| 反亲和性 | 按 hostname | 分散到不同节点 |
| 健康检查 | 同时使用 readiness 和 liveness | 快速故障检测 |
| PDB | minAvailable: N-1 | 在更新期间维持服务 |

---

## 批处理（成本优先，Spot）

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

### 批处理优化摘要

| 方面 | 建议 | 理由 |
|--------|----------------|-----------|
| 容量类型 | 仅 Spot | 最大化节省成本 |
| 实例系列 | C-series（计算优化型） | CPU 密集型工作负载 |
| 实例多样性 | 多个世代 | 更好的 Spot 可用性 |
| 重启策略 | OnFailure | 处理 Spot 中断 |
| 整合 | 激进（30s） | Job 完成后快速清理 |

---

## GPU 工作负载（p5, g5）

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

### GPU 实例选择指南

| 实例 | GPU | GPU 内存 | 使用场景 |
|----------|------|------------|----------|
| g5.xlarge | 1x A10G | 24GB | 小型推理 |
| g5.2xlarge | 1x A10G | 24GB | 中型推理 |
| g5.4xlarge | 1x A10G | 24GB | 大型推理 |
| g5.12xlarge | 4x A10G | 96GB | 多模型服务 |
| p5.48xlarge | 8x H100 | 640GB | 大规模训练 |

### GPU 优化摘要

| 方面 | 建议 | 理由 |
|--------|----------------|-----------|
| 容量类型 | On-Demand | GPU Spot 可用性有限 |
| 存储 | 200GB+ gp3 | 模型缓存、检查点 |
| 整合 | 宽松（10m） | GPU 启动较慢 |
| 限制 | 设置 nvidia.com/gpu 限制 | 防止 GPU 成本失控 |

---

## AI/ML 训练工作负载

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

### ML 训练优化摘要

| 方面 | 建议 | 理由 |
|--------|----------------|-----------|
| 实例类型 | p5.48xlarge, p4d.24xlarge | 最大 GPU 容量 |
| 存储 | 500GB+ root, 2TB+ data | 大型数据集、检查点 |
| IOPS | 16000+ | 快速写入检查点 |
| 网络 | 已启用 EFA | 分布式训练 |
| 框架 | PyTorchJob, TFJob | 原生分布式支持 |

---

## 工作负载类型快速参考

| 工作负载 | NodePool 策略 | 实例类型 | 容量 | 整合 |
|----------|-------------------|----------------|----------|---------------|
| Web 服务 | 可用性优先 | m-series | On-Demand | 中等（5m） |
| API 后端 | 混合 | m/c-series | 混合 | 中等（5m） |
| 批处理 | 成本优先 | c-series | 仅 Spot | 激进（30s） |
| CI/CD | 成本优先 | c/m-series | 优先 Spot | 激进（1m） |
| 数据库 | 稳定性优先 | r-series | On-Demand | 保守（10m） |
| GPU 推理 | 可用性优先 | g5-series | On-Demand | 宽松（10m） |
| ML 训练 | 性能优先 | p5/p4d | On-Demand | 宽松（15m） |
| 流处理 | 均衡 | m/c-series | 混合 | 中等（5m） |

---

## Pod 资源指南

### CPU 密集型工作负载

```yaml
resources:
  requests:
    cpu: 2000m      # Request what you need
    memory: 2Gi
  limits:
    cpu: 4000m      # Allow some burst
    memory: 4Gi
```

### 内存密集型工作负载

```yaml
resources:
  requests:
    cpu: 500m
    memory: 8Gi     # Request what you need
  limits:
    cpu: 1000m
    memory: 8Gi     # Limit = request (no overcommit)
```

### GPU 工作负载

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

< [上一页：Node 生命周期](./07-node-lifecycle.md) | [目录](./README.md) | [下一页：迁移指南](./09-migration-guide.md) >
