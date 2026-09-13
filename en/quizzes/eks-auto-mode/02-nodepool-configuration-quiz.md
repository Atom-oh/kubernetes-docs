# EKS Auto Mode NodePool Configuration Quiz

> **Related Document**: [NodePool Configuration](../../eks-auto-mode/02-nodepool-configuration.md)

## Multiple Choice Questions

### 1. What are the optional built-in NodePools provided by EKS Auto Mode?

- A) default, worker
- B) general-purpose, system
- C) compute, memory
- D) primary, secondary

<details>
<summary>Show Answer</summary>

**Answer: B) general-purpose, system**

**Explanation:**
When enabled, `general-purpose` and `system` use On-Demand C/M/R instances of generation 5 or newer. General-purpose uses amd64; system supports amd64 and arm64 and has a `CriticalAddonsOnly` taint. Use a custom pool for Spot. Auto Mode's local DNS/service-networking functions are not ordinary Pods that must be scheduled on the system pool.

```yaml
# eksctl configuration fragment
autoModeConfig:
  enabled: true
  nodePools: [general-purpose, system]
```

Removing a built-in name deletes its NodePool and drains/terminates managed nodes. Disabling both also means you must provide a custom NodeClass rather than assuming `default` exists.

</details>

### 2. How is IMDS configured for Auto Mode nodes?

- A) Set `metadataOptions.httpTokens: optional` in NodeClass
- B) AWS enforces IMDSv2 and hop limit 1; NodeClass cannot override these settings
- C) Set hop limit 0 to make IMDSv2 work
- D) Select AL2023 to disable IMDS authentication

<details>
<summary>Show Answer</summary>

**Answer: B) AWS enforces IMDSv2 and hop limit 1; NodeClass cannot override these settings**

**Explanation:**
The managed-instance defaults require IMDSv2 and hop limit 1, and cannot be changed in Auto Mode. The former `metadataOptions` example belonged to a different API. The hop limit restricts non-host-network Pods; it does not guarantee isolation for every Pod, including host-network workloads. Use workload identity and explicit region/configuration instead of relying on node credentials. See [managed instance restrictions](https://docs.aws.amazon.com/eks/latest/userguide/automode-learn-instances.html).

</details>

### 3. Who selects the operating-system image for Auto Mode nodes?

- A) The user chooses Amazon Linux 2 or Ubuntu in amiFamily
- B) AWS selects the appropriate managed Bottlerocket variant
- C) The user supplies any Windows AMI
- D) NodePool weight chooses AL2023 instead of Bottlerocket

<details>
<summary>Show Answer</summary>

**Answer: B) AWS selects the appropriate managed Bottlerocket variant**

**Explanation:**
Auto Mode uses AWS-managed Bottlerocket variants. It does not expose an `amiFamily: AL2023` or `amiFamily: Bottlerocket` choice in the AWS NodeClass. Use documented NodeClass settings for storage, networking, certificates and supported kernel configuration. These are different from arbitrary AMI selection or shell user data.

</details>

### 4. Which NodePool label selects GPU manufacturer in Auto Mode?

- A) karpenter.k8s.aws/gpu-vendor
- B) eks.amazonaws.com/instance-gpu-manufacturer
- C) nvidia.com/gpu-family
- D) karpenter.sh/gpu-type

<details>
<summary>Show Answer</summary>

**Answer: B) eks.amazonaws.com/instance-gpu-manufacturer**

**Explanation:**
Use the AWS Auto Mode label `eks.amazonaws.com/instance-gpu-manufacturer`. For NVIDIA GPU hardware, the requirements can include:

```yaml
# Requirements fragment inside a complete NodePool
requirements:
  - key: eks.amazonaws.com/instance-category
    operator: In
    values: ["g", "p"]
  - key: eks.amazonaws.com/instance-gpu-manufacturer
    operator: In
    values: ["nvidia"]
```

Hardware selection does not allocate a GPU to a container. The Pod must request the appropriate extended resource, such as `nvidia.com/gpu`, and use a compatible image/runtime. No GPU execution was performed in this audit.

</details>

### 5. Which condition selects EC2 generation 6 or newer?

- A) node.kubernetes.io/instance-generation: "6"
- B) eks.amazonaws.com/instance-generation with Gt and value "5"
- C) eks.amazonaws.com/generation: "6"
- D) instance-generation: 6

<details>
<summary>Show Answer</summary>

**Answer: B) eks.amazonaws.com/instance-generation with Gt and value "5"**

**Explanation:**
`Gt` is a strict numeric lower bound, so `Gt ["5"]` selects generation 6 and newer. `In ["6"]` selects exactly generation 6; it is not equivalent. Neither condition means only the latest available generation.

```yaml
# Requirements fragment inside a complete NodePool
requirements:
  - key: eks.amazonaws.com/instance-generation
    operator: Gt
    values: ["5"]
```

</details>

### 6. How do you select private subnets for a NodeClass?

- A) Set subnetType: private
- B) Select reviewed subnet IDs/tags and verify their routing and IP settings
- C) Set privateSubnetsOnly: true
- D) Set networkType: private

<details>
<summary>Show Answer</summary>

**Answer: B) Select reviewed subnet IDs/tags and verify their routing and IP settings**

**Explanation:**
`subnetSelectorTerms` selects by IDs or tags. Tags such as `kubernetes.io/role/internal-elb` are a convention, not evidence of a private route table. Terms are alternatives; multiple tags within one term must match together. Review VPC/AZ selection, routes and public-IP behavior.

```yaml
# Selection fragment; a complete NodeClass also needs identity and security groups
subnetSelectorTerms:
  - tags:
      kubernetes.io/role/internal-elb: "1"
      Environment: production
advancedNetworking:
  associatePublicIPAddress: false
```

Setting `associatePublicIPAddress: false` prevents public IP assignment but does not create NAT routes or VPC endpoints. Provide the complete NodeClass identity/security-group configuration and verify readiness.

</details>
