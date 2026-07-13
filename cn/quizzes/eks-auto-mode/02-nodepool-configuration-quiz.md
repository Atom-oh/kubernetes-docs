# EKS Auto Mode NodePool 配置测验

> **相关文档**: [NodePool 配置](../../eks-auto-mode/02-nodepool-configuration.md)

## 选择题

### 1. EKS Auto Mode 提供的默认 NodePools 是什么？

- A) default, worker
- B) general-purpose, system
- C) compute, memory
- D) primary, secondary

<details>
<summary>显示答案</summary>

**答案：B) general-purpose, system**

**解释：**
EKS Auto Mode 提供两个默认 NodePools：
- **general-purpose**: 用于通用 workloads 的默认 NodePool，支持多种实例类型（c、m、r）以及 Spot/On-Demand
- **system**: 用于系统组件（CoreDNS、kube-proxy 等）的 NodePool，仅使用 On-Demand，并应用 CriticalAddonsOnly taint

```yaml
# Auto Mode activation example
autoModeConfig:
  enabled: true
  nodePools:
    - general-purpose
    - system
```

</details>

### 2. 如何在 NodeClass 中强制要求使用 IMDSv2？

- A) `httpTokens: optional`
- B) `httpTokens: required`
- C) `httpEndpoint: disabled`
- D) `httpPutResponseHopLimit: 0`

<details>
<summary>显示答案</summary>

**答案：B) `httpTokens: required`**

**解释：**
在 NodeClass 的 `metadataOptions` 中设置 `httpTokens: required` 会强制仅使用 IMDSv2，从而增强安全性。

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

**安全最佳实践：**
- `httpTokens: required`: 强制使用 IMDSv2
- `httpPutResponseHopLimit: 1`: 阻止 Pods 直接访问 IMDS

</details>

### 3. EKS Auto Mode 支持哪些 AMI families？

- A) Amazon Linux 2, Ubuntu
- B) AL2023, Bottlerocket
- C) Windows Server, Amazon Linux 2
- D) Red Hat Enterprise Linux, Ubuntu

<details>
<summary>显示答案</summary>

**答案：B) AL2023, Bottlerocket**

**解释：**
EKS Auto Mode 仅支持 AL2023 (Amazon Linux 2023) 和 Bottlerocket AMI families。不支持 Windows nodes。

**AMI Family 特性：**
- **AL2023**: 通用用途，支持丰富的软件包
- **Bottlerocket**: 针对容器优化的 OS，启动时间更快，安全性更强

```yaml
apiVersion: eks.amazonaws.com/v1
kind: NodeClass
metadata:
  name: custom-nodeclass
spec:
  amiFamily: Bottlerocket  # or AL2023
```

</details>

### 4. 在用于 GPU workloads 的 NodePool 中，指定 GPU 制造商的 label key 是什么？

- A) `karpenter.k8s.aws/gpu-vendor`
- B) `karpenter.k8s.aws/instance-gpu-manufacturer`
- C) `nvidia.com/gpu-family`
- D) `karpenter.sh/gpu-type`

<details>
<summary>显示答案</summary>

**答案：B) `karpenter.k8s.aws/instance-gpu-manufacturer`**

**解释：**
选择 GPU 实例时可以指定制造商。

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

### 5. 在 NodePool 中指定实例 generation 的正确方式是什么？

- A) `node.kubernetes.io/instance-generation: "6"`
- B) `karpenter.k8s.aws/instance-generation`，并使用 `operator: In`
- C) `eks.amazonaws.com/generation: "6"`
- D) `instance-generation: 6`

<details>
<summary>显示答案</summary>

**答案：B) `karpenter.k8s.aws/instance-generation`，并使用 `operator: In`**

**解释：**
使用 Karpenter labels 指定实例 generation。

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

### 6. 将 NodeClass 配置为仅使用私有 subnets 的正确方式是什么？

- A) `subnetType: private`
- B) 带有 internal-elb tag 的 `subnetSelectorTerms`
- C) `privateSubnetsOnly: true`
- D) `networkType: private`

<details>
<summary>显示答案</summary>

**答案：B) 带有 internal-elb tag 的 `subnetSelectorTerms`**

**解释：**
使用 `subnetSelectorTerms` 选择私有 subnets。

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

公有 subnets 使用 `kubernetes.io/role/elb: "1"` tag。

</details>
