# NodePool の設定と最適化

> **サポート対象バージョン**: EKS 1.29+, EKS Auto Mode GA
> **最終更新**: July 3, 2026

このガイドでは、EKS Auto Mode が提供するデフォルト NodePools と、workload 要件に合わせてカスタム NodePools を作成する方法について説明します。

---

## デフォルト NodePools の理解

EKS Auto Mode は 2 つのデフォルト NodePools を提供します。

### general-purpose NodePool

汎用 workload 向けのデフォルト NodePool です。

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

system components（CoreDNS、kube-proxy など）向けの NodePool です。

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

## カスタム NodePools の作成

workload 要件に合わせてカスタム NodePools を作成できます。

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

## NodeClass の設定

NodeClass は nodes 向けの AWS 固有の設定を定義します。

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

### 拡張 Security と Networking フィールド

NodeClass は、full-disk encryption、custom CA trust chains、Pod traffic isolation のための追加フィールドをサポートします。

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

| Field | Description |
|-------|--------------|
| `kmsKeyID` | Customer-managed KMS key ARN。ephemeral instance storage と root EBS volume を暗号化します |
| `certificateBundles` | custom CA certificate bundles のリスト。enterprise proxy/PKI trust chains に使用されます |
| `podSubnetSelectorTerms` | Pod traffic 用の専用 subnet。secondary ENI によって分離されます |
| `podSecurityGroupSelectorTerms` | Pod traffic 用の専用 security group。secondary ENI によって分離されます |

`podSubnetSelectorTerms`/`podSecurityGroupSelectorTerms` が設定されている場合、node infrastructure traffic（kubelet、control plane communication など）と Pod 由来の application traffic は別々の subnets と security groups を使用します。そのため、traffic type ごとに security group rules と network ACLs を独立して設計できます。

---

## NodePool 分離戦略

### Workload による分離

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

### Environment（Development/Staging/Production）による分離

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

## NodePool のベストプラクティス

### Resource Limits

runaway costs を防ぐため、常に適切な limits を設定してください。

```yaml
spec:
  limits:
    cpu: 1000        # Maximum 1000 vCPUs
    memory: 4000Gi   # Maximum 4TB memory
```

### Weight の設定

複数の pools が一致する場合は、weights を使用して NodePools の優先順位を付けます。

```yaml
spec:
  weight: 10  # Higher weight = higher priority
```

### Label と Taint 戦略

workload isolation のため、一貫した labeling と tainting を使用してください。

| Use Case | Label Key | Taint Key | Effect |
|----------|-----------|-----------|--------|
| Workload tier | `workload-tier` | `workload-tier` | NoSchedule |
| Environment | `environment` | `environment` | NoSchedule |
| Team | `team` | `team` | NoSchedule |
| GPU workloads | `accelerator` | `nvidia.com/gpu` | NoSchedule |

---

< [前へ: Getting Started](./01-getting-started.md) | [目次](./README.md) | [次へ: Scaling Behavior](./03-scaling-behavior.md) >
