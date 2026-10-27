# EKS Auto Mode NodePool 配置测验

> **相关文档**：[NodePool 配置](../../eks-auto-mode/02-nodepool-configuration.md)

## 选择题

### 1. EKS Auto Mode 提供哪些可选的内置 NodePool？

- A) default、worker
- B) general-purpose、system
- C) compute、memory
- D) primary、secondary

<details>
<summary>显示答案</summary>

**答案：B) general-purpose、system**

**说明：**
启用后，`general-purpose` 和 `system` 使用第 5 代或更新一代的按需 C/M/R 实例。General-purpose 使用 amd64；system 支持 amd64 和 arm64，并带有 `CriticalAddonsOnly` 污点。Spot 实例请使用自定义池。Auto Mode 的本地 DNS/服务网络功能并非必须调度到 system 池上的普通 Pod。

```yaml
# eksctl configuration fragment
autoModeConfig:
  enabled: true
  nodePools: [general-purpose, system]
```

移除内置名称会删除相应的 NodePool，并排空/终止受其管理的节点。如果同时禁用这两个内置池，也就意味着你必须提供自定义 NodeClass，不能假定 `default` 一定存在。

</details>

### 2. 如何为 Auto Mode 节点配置 IMDS？

- A) 在 NodeClass 中设置 `metadataOptions.httpTokens: optional`
- B) AWS 强制使用 IMDSv2 和跳数限制 1；NodeClass 无法覆盖这些设置
- C) 将跳数限制设为 0，以启用 IMDSv2
- D) 选择 AL2023，以禁用 IMDS 身份验证

<details>
<summary>显示答案</summary>

**答案：B) AWS 强制使用 IMDSv2 和跳数限制 1；NodeClass 无法覆盖这些设置**

**说明：**
受管实例的默认设置要求使用 IMDSv2，并将跳数限制设为 1；在 Auto Mode 中无法更改这些设置。之前的 `metadataOptions` 示例属于另一种 API。跳数限制会限制非 host-network Pod，但不能保证隔离所有 Pod，包括使用 hostNetwork 的工作负载。请使用工作负载身份和显式配置区域/配置，而不要依赖节点凭证。请参阅[受管实例限制](https://docs.aws.amazon.com/eks/latest/userguide/automode-learn-instances.html)。

</details>

### 3. 谁为 Auto Mode 节点选择操作系统映像？

- A) 用户在 amiFamily 中选择 Amazon Linux 2 或 Ubuntu
- B) AWS 选择适用的受管 Bottlerocket 变体
- C) 用户提供任意 Windows AMI
- D) NodePool 权重选择 AL2023 而非 Bottlerocket

<details>
<summary>显示答案</summary>

**答案：B) AWS 选择适用的受管 Bottlerocket 变体**

**说明：**
Auto Mode 使用 AWS 管理的 Bottlerocket 变体。在 AWS NodeClass 中，不能选择 `amiFamily: AL2023` 或 `amiFamily: Bottlerocket`。请使用文档中列出的 NodeClass 设置来配置存储、网络、证书和受支持的内核配置。这些设置不同于任意选择 AMI 或使用 shell 用户数据。

</details>

### 4. Auto Mode 中，哪个 NodePool 标签用于选择 GPU 制造商？

- A) karpenter.k8s.aws/gpu-vendor
- B) eks.amazonaws.com/instance-gpu-manufacturer
- C) nvidia.com/gpu-family
- D) karpenter.sh/gpu-type

<details>
<summary>显示答案</summary>

**答案：B) eks.amazonaws.com/instance-gpu-manufacturer**

**说明：**
请使用 AWS Auto Mode 标签 `eks.amazonaws.com/instance-gpu-manufacturer`。对于 NVIDIA GPU 硬件，要求可以包括：

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

选择硬件并不会为容器分配 GPU。Pod 必须请求适当的扩展资源，例如 `nvidia.com/gpu`，并使用兼容的映像/运行时。本次审查未执行 GPU 运算。

</details>

### 5. 哪个条件用于选择第 6 代或更新一代的 EC2 实例？

- A) node.kubernetes.io/instance-generation: "6"
- B) eks.amazonaws.com/instance-generation，运算符为 Gt，值为 "5"
- C) eks.amazonaws.com/generation: "6"
- D) instance-generation: 6

<details>
<summary>显示答案</summary>

**答案：B) eks.amazonaws.com/instance-generation，运算符为 Gt，值为 "5"**

**说明：**
`Gt` 表示严格的数值下限，因此 `Gt ["5"]` 会选择第 6 代及更新一代的实例。`In ["6"]` 只选择第 6 代，并不等同于前者。这两个条件都不表示只选择当前可用的最新一代。

```yaml
# Requirements fragment inside a complete NodePool
requirements:
  - key: eks.amazonaws.com/instance-generation
    operator: Gt
    values: ["5"]
```

</details>

### 6. 如何为 NodeClass 选择私有子网？

- A) 设置 subnetType: private
- B) 选择经过审核的子网 ID/标签，并验证其路由和 IP 设置
- C) 设置 privateSubnetsOnly: true
- D) 设置 networkType: private

<details>
<summary>显示答案</summary>

**答案：B) 选择经过审核的子网 ID/标签，并验证其路由和 IP 设置**

**说明：**
`subnetSelectorTerms` 可以按 ID 或标签进行选择。诸如 `kubernetes.io/role/internal-elb` 的标签是一种约定，并不能证明子网使用私有路由表。多个标签位于同一个 term 时，必须全部匹配；不同 term 之间则是备选关系。请检查 VPC/AZ 选择、路由和公有 IP 行为。

```yaml
# Selection fragment; a complete NodeClass also needs identity and security groups
subnetSelectorTerms:
  - tags:
      kubernetes.io/role/internal-elb: "1"
      Environment: production
advancedNetworking:
  associatePublicIPAddress: false
```

设置 `associatePublicIPAddress: false` 可以阻止分配公有 IP，但不会创建 NAT 路由或 VPC 端点。请提供包含身份/安全组配置的完整 NodeClass，并验证其就绪状态。

</details>

### 7. 在现有 Auto Mode NodeClass 上更改 `maxPods` 等 kubelet 设置后会发生什么？

- A) EKS 会在不中断服务的情况下就地修补运行中节点的 kubelet
- B) 现有节点保留旧设置，只有新节点使用更改后的设置
- C) 使用该 NodeClass 的节点会被标记为发生偏移，EKS 会用采用新设置的节点替换它们
- D) 你必须通过 SSH 在每个节点上重启 kubelet

<details>
<summary>显示答案</summary>

**答案：C) 使用该 NodeClass 的节点会被标记为发生偏移，EKS 会用采用新设置的节点替换它们**

**说明：**
`spec.advancedCompute.kubelet` 下的 kubelet 设置会在创建节点时应用。编辑这些设置会导致现有节点发生偏移，因此 EKS 会替换这些节点，而不是修改运行中的节点；请先检查 PDB 和中断预算。`maxPods` 只是上限：实际生效值取你设置的值、实例类型提供的 IP 地址数，以及 Auto Mode 每个节点最多 110 个 Pod 的限制三者中的最低值。

```yaml
# NodeClass fragment
advancedCompute:
  kubelet:
    maxPods: 60
    podPidsLimit: 4096
```

</details>
