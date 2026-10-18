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

**解释：**
启用后，`general-purpose` 和 `system` 使用第 5 代或更新的按需 C/M/R 实例。general-purpose 使用 amd64；system 支持 amd64 和 arm64，并带有 `CriticalAddonsOnly` 污点。要使用 Spot，请创建自定义池。Auto Mode 的本地 DNS/服务网络功能不是必须调度到 system 池上的普通 Pod。

```yaml
# eksctl configuration fragment
autoModeConfig:
  enabled: true
  nodePools: [general-purpose, system]
```

移除某个内置名称会删除其 NodePool，并排空/终止受管理节点。若同时禁用这两个内置池，还必须提供自定义 NodeClass，不能假定 `default` 仍然存在。

</details>

### 2. 如何为 Auto Mode 节点配置 IMDS？

- A) 在 NodeClass 中设置 `metadataOptions.httpTokens: optional`
- B) AWS 强制使用 IMDSv2 和 hop limit 1；NodeClass 无法覆盖这些设置
- C) 将 hop limit 设为 0 才能使用 IMDSv2
- D) 选择 AL2023 即可禁用 IMDS 身份验证

<details>
<summary>显示答案</summary>

**答案：B) AWS 强制使用 IMDSv2 和 hop limit 1；NodeClass 无法覆盖这些设置**

**解释：**
受管理实例的默认设置要求使用 IMDSv2，并将 hop limit 设为 1；在 Auto Mode 中无法更改。以前的 `metadataOptions` 示例属于另一种 API。hop limit 会限制非 host-network Pod 的访问，但不保证对所有 Pod（包括使用 host network 的工作负载）都实现隔离。应使用工作负载身份并显式配置区域和其他设置，不要依赖节点凭证。参阅[受管理实例限制](https://docs.aws.amazon.com/eks/latest/userguide/automode-learn-instances.html)。

</details>

### 3. 谁为 Auto Mode 节点选择操作系统镜像？

- A) 用户在 amiFamily 中选择 Amazon Linux 2 或 Ubuntu
- B) AWS 选择合适的受管理 Bottlerocket 变体
- C) 用户提供任意 Windows AMI
- D) NodePool weight 选择 AL2023 而不是 Bottlerocket

<details>
<summary>显示答案</summary>

**答案：B) AWS 选择合适的受管理 Bottlerocket 变体**

**解释：**
Auto Mode 使用 AWS 管理的 Bottlerocket 变体。AWS NodeClass 不提供 `amiFamily: AL2023` 或 `amiFamily: Bottlerocket` 选项。请使用文档说明的 NodeClass 设置来配置存储、网络、证书和受支持的内核配置。这些设置不同于任意 AMI 选择或 shell 用户数据。

</details>

### 4. 在 Auto Mode 中，哪个 NodePool 标签用于选择 GPU 制造商？

- A) karpenter.k8s.aws/gpu-vendor
- B) eks.amazonaws.com/instance-gpu-manufacturer
- C) nvidia.com/gpu-family
- D) karpenter.sh/gpu-type

<details>
<summary>显示答案</summary>

**答案：B) eks.amazonaws.com/instance-gpu-manufacturer**

**解释：**
使用 AWS Auto Mode 标签 `eks.amazonaws.com/instance-gpu-manufacturer`。对于 NVIDIA GPU 硬件，requirements 可以包括：

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

选择硬件并不意味着已为容器分配 GPU。Pod 还必须请求相应的扩展资源（例如 `nvidia.com/gpu`），并使用兼容的镜像和运行时。本次审核没有执行 GPU 运算。

</details>

### 5. 使用哪个条件可以选择第 6 代或更新的 EC2 实例？

- A) node.kubernetes.io/instance-generation: "6"
- B) eks.amazonaws.com/instance-generation 配合 Gt 和值 "5"
- C) eks.amazonaws.com/generation: "6"
- D) instance-generation: 6

<details>
<summary>显示答案</summary>

**答案：B) eks.amazonaws.com/instance-generation 配合 Gt 和值 "5"**

**解释：**
`Gt` 是严格的大于数值下限，因此 `Gt ["5"]` 会选择第 6 代及更新的实例。`In ["6"]` 只会选择第 6 代实例，两者并不等价。这两个条件都不表示只选择当前可用的最新一代。

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
- B) 选择经过审核的子网 ID/标签，并检查其路由和 IP 设置
- C) 设置 privateSubnetsOnly: true
- D) 设置 networkType: private

<details>
<summary>显示答案</summary>

**答案：B) 选择经过审核的子网 ID/标签，并检查其路由和 IP 设置**

**解释：**
`subnetSelectorTerms` 可按 ID 或标签选择子网。`kubernetes.io/role/internal-elb` 等标签是一种惯例，并不能证明子网使用私有路由表。不同 term 之间是“或”关系；同一个 term 中的多个标签必须同时匹配。请检查 VPC/AZ 选择、路由和公有 IP 行为。

```yaml
# Selection fragment; a complete NodeClass also needs identity and security groups
subnetSelectorTerms:
  - tags:
      kubernetes.io/role/internal-elb: "1"
      Environment: production
advancedNetworking:
  associatePublicIPAddress: false
```

设置 `associatePublicIPAddress: false` 可以阻止分配公有 IP，但不会创建 NAT 路由或 VPC 端点。请提供完整的 NodeClass 身份和安全组配置，并检查其就绪状态。

</details>
