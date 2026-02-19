# EKS Auto Mode NodePool Configuration Quiz

> **Related Document**: [NodePool Configuration](../../eks-auto-mode/02-nodepool-configuration.md)

## Multiple Choice Questions

### 1. What are the default NodePools provided by EKS Auto Mode?

- A) default, worker
- B) general-purpose, system
- C) compute, memory
- D) primary, secondary

<details>
<summary>Show Answer</summary>

**Answer: B) general-purpose, system**

**Explanation:**
EKS Auto Mode provides two default NodePools:
- **general-purpose**: Default NodePool for general workloads, supporting various instance types (c, m, r) and both Spot/On-Demand
- **system**: NodePool for system components (CoreDNS, kube-proxy, etc.), using On-Demand only with CriticalAddonsOnly taint applied

```yaml
# Auto Mode activation example
autoModeConfig:
  enabled: true
  nodePools:
    - general-purpose
    - system
```

</details>

### 2. How do you enforce IMDSv2 as required in NodeClass?

- A) `httpTokens: optional`
- B) `httpTokens: required`
- C) `httpEndpoint: disabled`
- D) `httpPutResponseHopLimit: 0`

<details>
<summary>Show Answer</summary>

**Answer: B) `httpTokens: required`**

**Explanation:**
Setting `httpTokens: required` in NodeClass's `metadataOptions` enforces IMDSv2 only, enhancing security.

```yaml
apiVersion: eks.amazonaws.com/v1
kind: NodeClass
metadata:
  name: secure-nodeclass
spec:
  metadataOptions:
    httpEndpoint: enabled
    httpProtocolIPv6: disabled
    httpPutResponseHopLimit: 2
    httpTokens: required  # IMDSv2 required
```

**Security Best Practices:**
- `httpTokens: required`: Enforce IMDSv2 usage
- `httpPutResponseHopLimit: 1`: Block direct IMDS access from Pods

</details>

### 3. What AMI families does EKS Auto Mode support?

- A) Amazon Linux 2, Ubuntu
- B) AL2023, Bottlerocket
- C) Windows Server, Amazon Linux 2
- D) Red Hat Enterprise Linux, Ubuntu

<details>
<summary>Show Answer</summary>

**Answer: B) AL2023, Bottlerocket**

**Explanation:**
EKS Auto Mode only supports AL2023 (Amazon Linux 2023) and Bottlerocket AMI families. Windows nodes are not supported.

**AMI Family Characteristics:**
- **AL2023**: General-purpose use, rich package support
- **Bottlerocket**: Container-optimized OS, faster boot time, enhanced security

```yaml
apiVersion: eks.amazonaws.com/v1
kind: NodeClass
metadata:
  name: custom-nodeclass
spec:
  amiFamily: Bottlerocket  # or AL2023
```

</details>

### 4. What is the label key to specify GPU manufacturer in a NodePool for GPU workloads?

- A) `karpenter.k8s.aws/gpu-vendor`
- B) `karpenter.k8s.aws/instance-gpu-manufacturer`
- C) `nvidia.com/gpu-family`
- D) `karpenter.sh/gpu-type`

<details>
<summary>Show Answer</summary>

**Answer: B) `karpenter.k8s.aws/instance-gpu-manufacturer`**

**Explanation:**
You can specify the manufacturer when selecting GPU instances.

```yaml
spec:
  template:
    spec:
      requirements:
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["g", "p"]
        - key: karpenter.k8s.aws/instance-gpu-manufacturer
          operator: In
          values: ["nvidia"]
```

</details>

### 5. What is the correct way to specify instance generation in a NodePool?

- A) `node.kubernetes.io/instance-generation: "6"`
- B) `karpenter.k8s.aws/instance-generation` with `operator: In`
- C) `eks.amazonaws.com/generation: "6"`
- D) `instance-generation: 6`

<details>
<summary>Show Answer</summary>

**Answer: B) `karpenter.k8s.aws/instance-generation` with `operator: In`**

**Explanation:**
Use Karpenter labels to specify instance generation.

```yaml
spec:
  template:
    spec:
      requirements:
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["c"]
        - key: karpenter.k8s.aws/instance-generation
          operator: Gt
          values: ["5"]  # Generation 6 or higher
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["on-demand"]
```

</details>

### 6. What is the correct way to configure NodeClass to use only private subnets?

- A) `subnetType: private`
- B) `subnetSelectorTerms` with internal-elb tag
- C) `privateSubnetsOnly: true`
- D) `networkType: private`

<details>
<summary>Show Answer</summary>

**Answer: B) `subnetSelectorTerms` with internal-elb tag**

**Explanation:**
Use `subnetSelectorTerms` to select private subnets.

```yaml
apiVersion: eks.amazonaws.com/v1
kind: NodeClass
metadata:
  name: secure-nodeclass
spec:
  # Use private subnets only
  subnetSelectorTerms:
    - tags:
        kubernetes.io/role/internal-elb: "1"
```

Public subnets use the `kubernetes.io/role/elb: "1"` tag.

</details>
