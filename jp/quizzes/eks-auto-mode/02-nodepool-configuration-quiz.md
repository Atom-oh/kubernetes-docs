# EKS Auto Mode NodePool 設定クイズ

> **関連ドキュメント**: [NodePool 設定](../../eks-auto-mode/02-nodepool-configuration.md)

## 選択式問題

### 1. EKS Auto Mode が提供するデフォルトの NodePools はどれですか？

- A) default, worker
- B) general-purpose, system
- C) compute, memory
- D) primary, secondary

<details>
<summary>答えを表示</summary>

**答え: B) general-purpose, system**

**解説:**
EKS Auto Mode は 2 つのデフォルト NodePools を提供します。
- **general-purpose**: general workloads 向けのデフォルト NodePool で、さまざまな instance types (c, m, r) と Spot/On-Demand の両方をサポートします
- **system**: system components (CoreDNS, kube-proxy など) 向けの NodePool で、CriticalAddonsOnly taint が適用され、On-Demand のみを使用します

```yaml
# Auto Mode activation example
autoModeConfig:
  enabled: true
  nodePools:
    - general-purpose
    - system
```

</details>

### 2. NodeClass で IMDSv2 を必須として適用するにはどうしますか？

- A) `httpTokens: optional`
- B) `httpTokens: required`
- C) `httpEndpoint: disabled`
- D) `httpPutResponseHopLimit: 0`

<details>
<summary>答えを表示</summary>

**答え: B) `httpTokens: required`**

**解説:**
NodeClass の `metadataOptions` で `httpTokens: required` を設定すると、IMDSv2 のみが強制され、security が向上します。

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
- `httpTokens: required`: IMDSv2 の使用を強制します
- `httpPutResponseHopLimit: 1`: Pods からの直接 IMDS access をブロックします

</details>

### 3. EKS Auto Mode がサポートする AMI families はどれですか？

- A) Amazon Linux 2, Ubuntu
- B) AL2023, Bottlerocket
- C) Windows Server, Amazon Linux 2
- D) Red Hat Enterprise Linux, Ubuntu

<details>
<summary>答えを表示</summary>

**答え: B) AL2023, Bottlerocket**

**解説:**
EKS Auto Mode は AL2023 (Amazon Linux 2023) と Bottlerocket の AMI families のみをサポートします。Windows nodes はサポートされていません。

**AMI Family Characteristics:**
- **AL2023**: general-purpose use、豊富な package support
- **Bottlerocket**: Container-optimized OS、より速い boot time、強化された security

```yaml
apiVersion: eks.amazonaws.com/v1
kind: NodeClass
metadata:
  name: custom-nodeclass
spec:
  amiFamily: Bottlerocket  # or AL2023
```

</details>

### 4. GPU workloads 用の NodePool で GPU manufacturer を指定する label key はどれですか？

- A) `karpenter.k8s.aws/gpu-vendor`
- B) `karpenter.k8s.aws/instance-gpu-manufacturer`
- C) `nvidia.com/gpu-family`
- D) `karpenter.sh/gpu-type`

<details>
<summary>答えを表示</summary>

**答え: B) `karpenter.k8s.aws/instance-gpu-manufacturer`**

**解説:**
GPU instances を選択するときに manufacturer を指定できます。

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

### 5. NodePool で instance generation を指定する正しい方法はどれですか？

- A) `node.kubernetes.io/instance-generation: "6"`
- B) `karpenter.k8s.aws/instance-generation` with `operator: In`
- C) `eks.amazonaws.com/generation: "6"`
- D) `instance-generation: 6`

<details>
<summary>答えを表示</summary>

**答え: B) `karpenter.k8s.aws/instance-generation` with `operator: In`**

**解説:**
instance generation を指定するには Karpenter labels を使用します。

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

### 6. private subnets のみを使用するように NodeClass を設定する正しい方法はどれですか？

- A) `subnetType: private`
- B) `subnetSelectorTerms` with internal-elb tag
- C) `privateSubnetsOnly: true`
- D) `networkType: private`

<details>
<summary>答えを表示</summary>

**答え: B) `subnetSelectorTerms` with internal-elb tag**

**解説:**
private subnets を選択するには `subnetSelectorTerms` を使用します。

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

Public subnets は `kubernetes.io/role/elb: "1"` tag を使用します。

</details>
