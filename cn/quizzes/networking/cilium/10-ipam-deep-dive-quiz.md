# 第 10 部分：IPAM 深入测验

> **Cilium 1.20.2（稳定版，2026-09-16）· 2026-10-15**。标有 [1.21 预发布版] 的题目基于 v1.21.0-pre.3。

1. **CNI ADD 通过 `POST /ipam` 分配了 Pod IP，但 CNI 插件在创建 endpoint 之前崩溃。若没有任何重启，agent 何时会释放该 IP？**
   - A) 分配时设置的 10 分钟过期计时器到期后
   - B) 只有 agent 重启并恢复 endpoint 时
   - C) REST 连接关闭后立即释放
   - D) 180 秒后，即 `--excess-ip-release-delay` 的默认值

   <details>
   <summary>显示答案</summary>

   **答案：A) 分配时设置的 10 分钟过期计时器到期后**

   **解释：**
   CNI 插件在请求分配时设置了过期标志，因此 agent 会启动 10 分钟计时器（`defaults.IPAMExpiration`）。创建 endpoint 后，计时器会停止；如果始终未创建 endpoint，计时器就会释放该 IP。180 秒是 operator 释放 ENI 多余 IP 的延迟值。

   </details>

2. **使用 Cilium 1.20.2 的 cluster-pool Helm 默认值（`10.0.0.0/8`，IPv4 掩码大小为 24）时，该 CIDR 可以为多少个节点分配 PodCIDR？每个节点块有多少个地址？**
   - A) 16,384 个节点，每个节点 1,024 个地址
   - B) 256 个节点，每个节点 65,536 个地址
   - C) 65,536 个节点，每个节点 256 个地址
   - D) 65,536 个节点；根据掩码定义，每个节点有 254 个可用地址

   <details>
   <summary>显示答案</summary>

   **答案：C) 65,536 个节点，每个节点 256 个地址**

   **解释：**
   每个 pool CIDR 可容纳的节点数为 `2^(nodeMask - poolMask) = 2^(24 - 8) = 65,536`，每个节点块包含 `2^(32 - 24) = 256` 个地址。可用于 Pod 的 IP 数量会更少，因为网络 / 广播地址以及路由器、健康检查和入口地址都要从该块中扣除。

   </details>

3. **在 1.20.2 allocator 中，IPv6 cluster-pool 的 pool 前缀长度与节点掩码之间的差距受什么限制？**
   - A) 差距必须至少为 64 位，让每个节点都获得 /64，与 pool 大小无关
   - B) 差距不得超过 16 位（`clusterSubnetMaxDiff`），因为 allocator 使用未压缩位图
   - C) 没有限制，只要节点掩码不超过 /128，因为位图经过压缩
   - D) 差距必须恰好为 8 位，与 IPv4 默认值相同

   <details>
   <summary>显示答案</summary>

   **答案：B) 差距不得超过 16 位（`clusterSubnetMaxDiff`），因为 allocator 使用未压缩位图**

   **解释：**
   `pkg/ipam/cidrset` 会拒绝比 pool 前缀长 16 位以上的 IPv6 节点掩码（`ErrCIDRSetSubNetTooBig`）。IPv4 只要求节点掩码不超过 32。Helm 默认值 `fd00::/104` 和 `/120` 正好达到 16 位差距上限。

   </details>

4. **在多 pool IPAM 中，Cilium 按什么顺序为新 Pod 选择 pool？**
   - A) 先检查 CiliumPodIPPool selector，然后检查 Pod 注解，再检查 namespace 注解；除非设置了 `require-pool-match`，否则使用 `default` pool
   - B) 始终使用 `default` pool；注解和 selector 只影响 masquerading 与 LB IPAM
   - C) 先检查 namespace 注解，再检查 Pod 注解，然后使用 `default`；CiliumPodIPPool selector 只用于 LB IPAM
   - D) 先检查 Pod 注解（`ipv4-pool` / `ipv6-pool` 优先于 `ip-pool`），再检查 namespace 注解，然后检查 CiliumPodIPPool selector；除非设置了 `require-pool-match`，否则使用 `default`

   <details>
   <summary>显示答案</summary>

   **答案：D) 先检查 Pod 注解（`ipv4-pool` / `ipv6-pool` 优先于 `ip-pool`），再检查 namespace 注解，然后检查 CiliumPodIPPool selector；除非设置了 `require-pool-match`，否则使用 `default`**

   **解释：**
   Pod 注解优先于 namespace 注解，namespace 注解又优先于 `podSelector` / `namespaceSelector` 匹配。若没有匹配项，就使用 `ipam-default-ip-pool` 指定的 pool（默认为 `default`），除非 Pod 或 namespace 设置了 `ipam.cilium.io/require-pool-match: "true"`，这种情况下会阻止分配。pool 只会在 Pod 创建时选择一次。

   </details>

5. **某 Pod 匹配了两个不同 CiliumPodIPPool 的 selector，且地址族相同、没有 pool 注解。会发生什么？**
   - A) 分配失败并产生错误和事件，因为每个地址族必须恰好匹配一个 pool
   - B) 使用名称按字母排序最靠前的 pool，并记录事件
   - C) Pod 从每个匹配的 pool 各获取一个地址，并同时通过两个 pool 路由
   - D) 使用 `default` pool 解决冲突，并忽略 selector

   <details>
   <summary>显示答案</summary>

   **答案：A) 分配失败并产生错误和事件，因为每个地址族必须恰好匹配一个 pool**

   **解释：**
   基于 selector 的选择要求每个地址族恰好匹配一个 pool。匹配多个 pool 会产生错误（`multiple CiliumPodIPPools match pod ...`），并使 Pod 保持在 `ContainerCreating` 状态。可以收紧 selector，或明确为 Pod / namespace 添加注解来解决。

   </details>

6. **关于 Cilium 1.20.2 中的 ENI 前缀委派，哪项说法正确？**
   - A) 适用于任意 EC2 实例类型，并分配 /24 前缀；子网满时回退到 /28
   - B) 适用于任意实例类型，可在同一个节点上自由混用 /32 与 /28 分配，并根据子网状况为每个 Pod 切换
   - C) 要求 `ipam.mode=multi-pool`，并使用一个 CIDR 列出待委派前缀的 `CiliumPodIPPool`
   - D) 仅适用于 Nitro 或裸金属实例，分配 /28 前缀；如果节点已有辅助 /32 IP，就会跳过；子网没有前缀时回退到 /32

   <details>
   <summary>显示答案</summary>

   **答案：D) 仅适用于 Nitro 或裸金属实例，分配 /28 前缀；如果节点已有辅助 /32 IP，就会跳过；子网没有前缀时回退到 /32**

   **解释：**
   operator 会检查 Nitro hypervisor 或裸金属类型；如果节点已有辅助 IP，就会跳过前缀模式（不支持混合模式）。遇到 `InsufficientPrefixesInSubnet` 时，会停止为该节点分配前缀，并改用 `AssignPrivateIpAddresses`。前缀单位为 /28（16 个地址；IPv6 为 /80）。ENI 模式没有 CiliumPodIPPool。

   </details>

7. **在 Cilium 1.20 中，ENI allocator 如何将 EC2 网络接口状态交给 agent？**
   - A) operator 将单个 IP 写入 `spec.ipam.pool`，agent 按照 1.19 的方式在 `status.ipam.used` 中报告用量，并且不写入 ENI 状态
   - B) agent 使用自己的凭证直接调用 EC2 API，而 operator 只负责清理 ENI
   - C) operator 将 ENI 写入 `status.eni.enis`；agent 将其转换为 `spec.ipam.pools.allocated` 中的 /32 和 /28 CIDR（pool 为 `default`），并在 `spec.ipam.pools.requested` 中报告需求
   - D) 每个 ENI 都会成为一个由 operator 创建、通过 `ip-pool` 注解选择的独立 CiliumPodIPPool

   <details>
   <summary>显示答案</summary>

   **答案：C) operator 将 ENI 写入 `status.eni.enis`；agent 将其转换为 `spec.ipam.pools.allocated` 中的 /32 和 /28 CIDR（pool 为 `default`），并在 `spec.ipam.pools.requested` 中报告需求**

   **解释：**
   1.20 将 ENI 接入多 pool allocator：只有 operator 调用 EC2；agent 根据 ENI 清单推导已分配的 CIDR，并回写所需容量。`spec.ipam.pool` / `status.ipam.used` 模型属于 1.19 和 1.18 的 CRD allocator。ENI 模式没有 CiliumPodIPPool，也没有 `ip-pool` 注解。

   </details>

8. **[1.21 预发布版] 目前你直接向 Cilium operator 传入 `--aws-use-primary-address`。升级到 1.21 之前必须做什么？**
   - A) 不需要做任何事；该标志只被弃用，在 1.21 中仍可作为 operator 标志使用
   - B) 移除它，并设置 `eni.nodeSpec.usePrimaryAddress=true`（agent 标志为 `--eni-use-primary-address`）
   - C) 在默认 pool 的 `CiliumPodIPPool` 中通过 `spec.ipv4.pool[]` 设置它
   - D) 将其移到 agent 中，仍使用原名称 `--aws-use-primary-address`

   <details>
   <summary>显示答案</summary>

   **答案：B) 移除它，并设置 `eni.nodeSpec.usePrimaryAddress=true`（agent 标志为 `--eni-use-primary-address`）**

   **解释：**
   1.21 中移除了 operator 标志，以便将每个节点的 `CiliumNode.spec.eni.use-primary-address` 作为唯一事实来源。Helm 用户不受影响，因为 chart 一直只配置 agent 侧的值。这是预发布版本（v1.21.0-pre.3）的变更。

   </details>

9. **[1.21 预发布版] `cilium.io/v2` 的 `CiliumPodIPPool` 中，`spec.ipv4.pool[].reservedRanges` 有什么用途？**
   - A) 从每个节点块排除某些地址，以便 LB IPAM pool 将这些地址作为静态 Service IP 分配
   - B) 无需重建已有节点块，就能修改运行中 pool 的 `maskSize`
   - C) 为每个节点块中的路由器、健康检查和入口 endpoint 保留地址
   - D) 将旧 CIDR 留在 `cidrs` 中，使已有节点块继续工作，同时不再从该 CIDR 划分新块，从而逐步迁移到新 CIDR

   <details>
   <summary>显示答案</summary>

   **答案：D) 将旧 CIDR 留在 `cidrs` 中，使已有节点块继续工作，同时不再从该 CIDR 划分新块，从而逐步迁移到新 CIDR**

   **解释：**
   保留整个旧 CIDR 后，Cilium 会保留现有分配，并只从其他 CIDR 为新的 PodCIDR 分配块。所有节点组迁移完成后，再移除旧 CIDR 和其 `pool` 项。每个 `pool[].cidr` 都必须是 `cidrs` 中的成员；`maskSize` 仍不可变。

   </details>

10. **两个 `CiliumLoadBalancerIPPool` 资源包含重叠的地址块。LB IPAM 会怎么做？**
   - A) 将较晚创建的 pool 标记为 Conflicting（`cilium.io/PoolConflict`），并且不从中分配地址
   - B) 通过 validating webhook 在准入阶段拒绝第二个 pool
   - C) 将它们合并成一个 pool，并从两个地址块的并集中分配
   - D) 根据 Service 数量将重叠范围平均分配给两个 pool

   <details>
   <summary>显示答案</summary>

   **答案：A) 将较晚创建的 pool 标记为 Conflicting（`cilium.io/PoolConflict`），并且不从中分配地址**

   **解释：**
   LB IPAM 不会合并或拒绝重叠的 pool。较晚的 pool 会被标记为 Conflicting，在 `Conflicting` 输出列和 `lbipam_conflicting_pools` 指标中显示（确切的运行时前缀为 `cilium_` 还是 `cilium_operator_` 尚未验证），并且不会从该 pool 分配地址。编辑正在使用的 pool 也可能重新分配现有 Service IP，因此优先考虑添加 pool 或设置 `disabled: true`。

   </details>
