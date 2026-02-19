# NodePool Configuration and Optimization

> **Supported Versions**: EKS 1.29+, EKS Auto Mode GA
> **Last Updated**: February 2025

This guide covers the default NodePools provided by EKS Auto Mode and how to create custom NodePools tailored to your workload requirements.

---

## Understanding Default NodePools

EKS Auto Mode provides two default NodePools:

### general-purpose NodePool

Default NodePool for general-purpose workloads.

```yaml
# general-purpose NodePool (AWS managed, for reference)
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: general-purpose
spec:
  template:
    spec:
      requirements:
        - key: kubernetes.io/arch
          operator: In
          values: ["amd64", "arm64"]
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["on-demand", "spot"]
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["c", "m", "r"]
        - key: karpenter.k8s.aws/instance-generation
          operator: Gt
          values: ["5"]
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 1m
```

### system NodePool

NodePool for system components (CoreDNS, kube-proxy, etc.).

```yaml
# system NodePool (AWS managed, for reference)
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: system
spec:
  template:
    spec:
      requirements:
        - key: kubernetes.io/arch
          operator: In
          values: ["amd64"]
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["on-demand"]
        - key: karpenter.k8s.aws/instance-size
          operator: In
          values: ["medium", "large", "xlarge"]
      taints:
        - key: CriticalAddonsOnly
          value: "true"
          effect: NoSchedule
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30s
```

---

## Creating Custom NodePools

You can create custom NodePools tailored to your workload requirements.

### High-Performance Computing NodePool

```yaml
# compute-optimized-nodepool.yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: compute-optimized
  labels:
    workload-type: compute-intensive
spec:
  template:
    metadata:
      labels:
        workload-type: compute-intensive
    spec:
      requirements:
        # Use only CPU-optimized instances
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["c"]
        # Latest generation instances
        - key: karpenter.k8s.aws/instance-generation
          operator: Gt
          values: ["6"]
        # Limit instance sizes
        - key: karpenter.k8s.aws/instance-size
          operator: In
          values: ["xlarge", "2xlarge", "4xlarge"]
        # Use only x86_64
        - key: kubernetes.io/arch
          operator: In
          values: ["amd64"]
        # Use only On-Demand (stability first)
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["on-demand"]
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
  # Limit maximum nodes
  limits:
    cpu: 1000
    memory: 4000Gi
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 5m
  # Node weight (higher priority)
  weight: 10
```

### Memory-Optimized NodePool

```yaml
# memory-optimized-nodepool.yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: memory-optimized
  labels:
    workload-type: memory-intensive
spec:
  template:
    metadata:
      labels:
        workload-type: memory-intensive
    spec:
      requirements:
        # Memory-optimized instances
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["r"]
        - key: karpenter.k8s.aws/instance-generation
          operator: Gt
          values: ["5"]
        - key: karpenter.k8s.aws/instance-size
          operator: In
          values: ["2xlarge", "4xlarge", "8xlarge", "12xlarge"]
        - key: kubernetes.io/arch
          operator: In
          values: ["amd64", "arm64"]
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["on-demand"]
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
  limits:
    cpu: 500
    memory: 8000Gi
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 10m
  weight: 5
```

---

## NodeClass Configuration

NodeClass defines AWS-specific settings for nodes.

```yaml
# custom-nodeclass.yaml
apiVersion: eks.amazonaws.com/v1
kind: NodeClass
metadata:
  name: custom-nodeclass
spec:
  # Select AMI family
  amiFamily: AL2023

  # Subnet selection
  subnetSelectorTerms:
    - tags:
        kubernetes.io/role/internal-elb: "1"
        Environment: production

  # Security group selection
  securityGroupSelectorTerms:
    - tags:
        kubernetes.io/cluster/my-cluster: owned
        Type: worker-node

  # Instance profile
  instanceProfile: eks-node-instance-profile

  # Block device mappings
  blockDeviceMappings:
    - deviceName: /dev/xvda
      ebs:
        volumeSize: 100Gi
        volumeType: gp3
        iops: 3000
        throughput: 125
        encrypted: true
        deleteOnTermination: true

  # User data (additional bootstrap script)
  userData: |
    #!/bin/bash
    echo "Custom bootstrap script"
    # Kernel parameter tuning
    sysctl -w vm.max_map_count=262144

  # Metadata options
  metadataOptions:
    httpEndpoint: enabled
    httpProtocolIPv6: disabled
    httpPutResponseHopLimit: 2
    httpTokens: required  # IMDSv2 required

  tags:
    Environment: production
    ManagedBy: eks-auto-mode
```

---

## NodePool Separation Strategies

### Separation by Workload

```yaml
# NodePool for frontend workloads
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: frontend
spec:
  template:
    metadata:
      labels:
        workload-tier: frontend
    spec:
      requirements:
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["m", "c"]
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["spot", "on-demand"]
      taints:
        - key: workload-tier
          value: frontend
          effect: NoSchedule
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
  weight: 10
---
# NodePool for backend workloads
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: backend
spec:
  template:
    metadata:
      labels:
        workload-tier: backend
    spec:
      requirements:
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["m", "r"]
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["on-demand"]
      taints:
        - key: workload-tier
          value: backend
          effect: NoSchedule
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
  weight: 10
```

### Separation by Environment (Development/Staging/Production)

```yaml
# Development environment NodePool
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: dev-pool
spec:
  template:
    metadata:
      labels:
        environment: development
    spec:
      requirements:
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["t", "m"]
        - key: karpenter.k8s.aws/instance-size
          operator: In
          values: ["medium", "large"]
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["spot"]  # Cost savings
      taints:
        - key: environment
          value: development
          effect: NoSchedule
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
  limits:
    cpu: 100
  weight: 1
```

---

## NodePool Best Practices

### Resource Limits

Always set appropriate limits to prevent runaway costs:

```yaml
spec:
  limits:
    cpu: 1000        # Maximum 1000 vCPUs
    memory: 4000Gi   # Maximum 4TB memory
```

### Weight Configuration

Use weights to prioritize NodePools when multiple pools match:

```yaml
spec:
  weight: 10  # Higher weight = higher priority
```

### Label and Taint Strategy

Use consistent labeling and tainting for workload isolation:

| Use Case | Label Key | Taint Key | Effect |
|----------|-----------|-----------|--------|
| Workload tier | `workload-tier` | `workload-tier` | NoSchedule |
| Environment | `environment` | `environment` | NoSchedule |
| Team | `team` | `team` | NoSchedule |
| GPU workloads | `accelerator` | `nvidia.com/gpu` | NoSchedule |

---

< [Previous: Getting Started](./01-getting-started.md) | [Table of Contents](./README.md) | [Next: Scaling Behavior](./03-scaling-behavior.md) >
