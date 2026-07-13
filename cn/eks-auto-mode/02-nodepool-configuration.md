# NodePool 配置与优化

> **支持的版本**: EKS 1.29+, EKS Auto Mode GA
> **最后更新**: July 3, 2026

本指南介绍 EKS Auto Mode 提供的默认 NodePool，以及如何创建符合你的 workload 要求的自定义 NodePool。

---

## 了解默认 NodePool

EKS Auto Mode 提供两个默认 NodePool：

### general-purpose NodePool

用于通用 workload 的默认 NodePool。

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

用于系统组件（CoreDNS、kube-proxy 等）的 NodePool。

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

## 创建自定义 NodePool

你可以创建符合 workload 要求的自定义 NodePool。

### 高性能计算 NodePool

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

### 内存优化 NodePool

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

## NodeClass 配置

NodeClass 定义节点的 AWS 特定设置。

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

### 扩展的安全和网络字段

NodeClass 支持用于全磁盘加密、自定义 CA 信任链和 Pod 流量隔离的附加字段。

```yaml
# secure-network-nodeclass.yaml
apiVersion: eks.amazonaws.com/v1
kind: NodeClass
metadata:
  name: secure-network-nodeclass
spec:
  amiFamily: AL2023

  # Encrypt ephemeral instance storage + root EBS volume with a customer-managed KMS key
  # (no custom AMI required)
  kmsKeyID: arn:aws:kms:us-west-2:111122223333:key/1234abcd-12ab-34cd-56ef-1234567890ab

  # Custom CA certificate bundle for enterprise PKI/proxy trust chains
  certificateBundles:
    - name: corporate-ca
      content: |
        -----BEGIN CERTIFICATE-----
        MIIDXTCCAkWgAwIBAgIJAK...
        -----END CERTIFICATE-----

  # Separate infrastructure traffic from application Pod traffic using
  # dedicated subnets/security groups (secondary ENI)
  subnetSelectorTerms:
    - tags:
        kubernetes.io/role/internal-elb: "1"
  securityGroupSelectorTerms:
    - tags:
        kubernetes.io/cluster/my-cluster: owned
  podSubnetSelectorTerms:
    - tags:
        Purpose: pod-network
  podSecurityGroupSelectorTerms:
    - tags:
        Purpose: pod-network
```

| 字段 | 描述 |
|-------|--------------|
| `kmsKeyID` | 客户管理的 KMS key ARN。加密临时实例存储和根 EBS 卷 |
| `certificateBundles` | 自定义 CA certificate bundle 列表。用于企业 proxy/PKI 信任链 |
| `podSubnetSelectorTerms` | Pod 流量的专用 subnet，通过 secondary ENI 隔离 |
| `podSecurityGroupSelectorTerms` | Pod 流量的专用 security group，通过 secondary ENI 隔离 |

配置 `podSubnetSelectorTerms`/`podSecurityGroupSelectorTerms` 后，节点基础设施流量（kubelet、control plane 通信等）和源自 Pod 的应用流量会使用独立的 subnet 和 security group，因此你可以按流量类型独立设计 security group 规则和网络 ACL。

---

## NodePool 分离策略

### 按 Workload 分离

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

### 按环境分离（Development/Staging/Production）

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

## NodePool 最佳实践

### 资源限制

始终设置适当的限制，以防止成本失控：

```yaml
spec:
  limits:
    cpu: 1000        # Maximum 1000 vCPUs
    memory: 4000Gi   # Maximum 4TB memory
```

### 权重配置

当多个 pool 匹配时，使用权重确定 NodePool 的优先级：

```yaml
spec:
  weight: 10  # Higher weight = higher priority
```

### Label 和 Taint 策略

使用一致的 label 和 taint 实现 workload 隔离：

| 使用场景 | Label Key | Taint Key | Effect |
|----------|-----------|-----------|--------|
| Workload tier | `workload-tier` | `workload-tier` | NoSchedule |
| Environment | `environment` | `environment` | NoSchedule |
| Team | `team` | `team` | NoSchedule |
| GPU workload | `accelerator` | `nvidia.com/gpu` | NoSchedule |

---

< [上一页：入门](./01-getting-started.md) | [目录](./README.md) | [下一页：扩缩容行为](./03-scaling-behavior.md) >
