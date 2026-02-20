# Workload-Specific Optimization

> **Supported Versions**: EKS 1.29+, EKS Auto Mode GA
> **Last Updated**: February 2025

This guide covers how to optimize EKS Auto Mode configurations for different workload types including web services, batch processing, GPU workloads, and AI/ML training.

---

## Web Services (Availability First)

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

### Web Services Optimization Summary

| Aspect | Recommendation | Rationale |
|--------|----------------|-----------|
| Capacity type | On-Demand | High availability requirement |
| Instance family | M-series (general purpose) | Balanced CPU/memory |
| Anti-affinity | Per hostname | Spread across nodes |
| Health checks | Both readiness and liveness | Quick failure detection |
| PDB | minAvailable: N-1 | Maintain service during updates |

---

## Batch Processing (Cost First, Spot)

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

### Batch Processing Optimization Summary

| Aspect | Recommendation | Rationale |
|--------|----------------|-----------|
| Capacity type | Spot only | Maximum cost savings |
| Instance family | C-series (compute optimized) | CPU-intensive workloads |
| Instance diversity | Multiple generations | Better Spot availability |
| Restart policy | OnFailure | Handle Spot interrupts |
| Consolidation | Aggressive (30s) | Quick cleanup after jobs |

---

## GPU Workloads (p5, g5)

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

### GPU Instance Selection Guide

| Instance | GPUs | GPU Memory | Use Case |
|----------|------|------------|----------|
| g5.xlarge | 1x A10G | 24GB | Small inference |
| g5.2xlarge | 1x A10G | 24GB | Medium inference |
| g5.4xlarge | 1x A10G | 24GB | Large inference |
| g5.12xlarge | 4x A10G | 96GB | Multi-model serving |
| p5.48xlarge | 8x H100 | 640GB | Large-scale training |

### GPU Optimization Summary

| Aspect | Recommendation | Rationale |
|--------|----------------|-----------|
| Capacity type | On-Demand | GPU Spot availability is limited |
| Storage | 200GB+ gp3 | Model caching, checkpoints |
| Consolidation | Relaxed (10m) | GPU startup is slower |
| Limits | Set nvidia.com/gpu limit | Prevent runaway GPU costs |

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

### ML Training Optimization Summary

| Aspect | Recommendation | Rationale |
|--------|----------------|-----------|
| Instance type | p5.48xlarge, p4d.24xlarge | Maximum GPU capacity |
| Storage | 500GB+ root, 2TB+ data | Large datasets, checkpoints |
| IOPS | 16000+ | Fast checkpoint writes |
| Networking | EFA-enabled | Distributed training |
| Framework | PyTorchJob, TFJob | Native distributed support |

---

## Workload Type Quick Reference

| Workload | NodePool Strategy | Instance Types | Capacity | Consolidation |
|----------|-------------------|----------------|----------|---------------|
| Web services | Availability-first | m-series | On-Demand | Moderate (5m) |
| API backend | Mixed | m/c-series | Mixed | Moderate (5m) |
| Batch processing | Cost-first | c-series | Spot only | Aggressive (30s) |
| CI/CD | Cost-first | c/m-series | Spot preferred | Aggressive (1m) |
| Databases | Stability-first | r-series | On-Demand | Conservative (10m) |
| GPU inference | Availability-first | g5-series | On-Demand | Relaxed (10m) |
| ML training | Performance-first | p5/p4d | On-Demand | Relaxed (15m) |
| Stream processing | Balanced | m/c-series | Mixed | Moderate (5m) |

---

## Pod Resource Guidelines

### CPU-Bound Workloads

```yaml
resources:
  requests:
    cpu: 2000m      # Request what you need
    memory: 2Gi
  limits:
    cpu: 4000m      # Allow some burst
    memory: 4Gi
```

### Memory-Bound Workloads

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

< [Previous: Node Lifecycle](./07-node-lifecycle.md) | [Table of Contents](./README.md) | [Next: Migration Guide](./09-migration-guide.md) >
