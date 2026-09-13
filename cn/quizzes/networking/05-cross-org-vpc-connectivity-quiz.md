# 跨组织 VPC 连接测验

本测验检验你对在不同 AWS Organizations 之间连接 VPC 的五种选项的理解。

## 多项选择题

1. 与其他 Organization 中的账户共享 Transit Gateway 需要什么？
   - A) 将两个 Organizations 合并为一个
   - B) 使用 `--allow-external-principals` 选项，并由接收方接受邀请
   - C) 在两个 Organizations 的管理账户之间建立 VPN 连接
   - D) 通过 AWS Support 工单进行人工审批

<details>

<summary>显示答案</summary>

**答案：B) 使用 `--allow-external-principals` 选项，并由接收方接受邀请**

**说明：**
通过 AWS RAM 与 Organization 外部的账户共享资源时，资源共享必须启用 `--allow-external-principals`，并且在接收账户运行 `accept-resource-share-invitation` 前，该资源不可见。不同于在同一 Organization 内基于 OU 的自动共享，跨组织共享要求明确指定账户 ID，并进行明确接受。
</details>

2. 当另一个 Organization 中的账户为共享 TGW 创建 VPC attachment 时，会发生什么？
   - A) 它会立即变为可用
   - B) 它会停留在 pendingAcceptance，直到拥有 TGW 的账户接受它
   - C) 请求会被拒绝，且无法创建 attachment
   - D) 它会在 24 小时后自动激活

<details>

<summary>显示答案</summary>

**答案：B) 它会停留在 pendingAcceptance，直到拥有 TGW 的账户接受它**

**说明：**
在禁用自动接受（默认设置）时，外部账户的 attachment 会一直处于 `pendingAcceptance`，直至 TGW 所有者运行 `accept-transit-gateway-vpc-attachment`。这是“TGW 所有者集中控制网络”的模型在 API 层面得到强制执行的地方。接收共享的账户只能创建 attachments，不能修改 route tables。
</details>

3. 根据同一 AZ 内的实时测量，每次 Transit Gateway hop 会增加多少延迟（p50）？
   - A) 约 0.02 ms，几乎为零
   - B) 约 0.4–0.6 ms，不足一毫秒
   - C) 约 3–5 ms
   - D) 10 ms 或更多

<details>

<summary>显示答案</summary>

**答案：B) 约 0.4–0.6 ms，不足一毫秒**

**说明：**
使用 c7g.large、普通 EC2 responder 和持续 TCP_RR（每个路径 1,500 个样本）测得，一个 TGW hop 的开销为 +0.571 ms（TCP_RR）/ +0.410 ms（ICMP）。作为参考，VPC Peering 的开销在测量范围内为零（与同一 VPC 基线相同），而一次 NLB hop（+0.79 ms）的开销实际上高于一次 TGW hop。使用 burstable instances 或多阶段 proxy chains 进行测量，会使这种亚毫秒信号淹没在噪声中，因此测量设计非常重要。
</details>

4. VPC Lattice target instance 的 Security Group 配置中常见的陷阱是什么？
   - A) 必须开放所有 outbound rules
   - B) Lattice data plane 的流量来自链路本地地址（169.254.171.0/24），因此必须允许该 managed prefix list
   - C) 必须使用 NACLs 而非 SGs
   - D) 只需允许端口 443

<details>

<summary>显示答案</summary>

**答案：B) Lattice data plane 的流量来自链路本地地址（169.254.171.0/24），因此必须允许该 managed prefix list**

**说明：**
VPC Lattice 流量（包括 health checks）来自链路本地范围 169.254.171.0/24，而不是 VPC CIDR。如果 target SG 只允许 VPC CIDR，每项 health check 都会报告 UNHEALTHY。解决方法是在 SG 的 inbound rules 中添加 managed prefix list `com.amazonaws.<region>.vpc-lattice`。
</details>

5. 哪些选项可以连接位于两个 Organizations 中且 IP CIDRs 重叠的 VPC？
   - A) VPC Peering 和 TGW Peering
   - B) TGW RAM Sharing
   - C) PrivateLink 和 VPC Lattice
   - D) 没有任何选项可以

<details>

<summary>显示答案</summary>

**答案：C) PrivateLink 和 VPC Lattice**

**说明：**
VPC Peering、TGW RAM sharing 和 TGW Peering 都基于 L3 routing，因此 CIDRs 重叠会将它们排除在外。PrivateLink 通过 consumer VPC 内的 ENI 运行，而 VPC Lattice 使用链路本地地址，因此两者均可在 CIDR 重叠时工作。在 M&A 或 MSP migration 等无法重新规划 IP 的情境中，这两种是唯一的选择。
</details>

6. 关于 TGW Peering 配置中的 routing，哪项陈述是正确的？
   - A) 路由会通过 BGP 自动传播
   - B) 不支持 BGP，因此必须手动将 static routes 添加到两个 TGW route tables
   - C) 只需要修改 VPC route tables
   - D) 完全不需要 routing 配置

<details>

<summary>显示答案</summary>

**答案：B) 不支持 BGP，因此必须手动将 static routes 添加到两个 TGW route tables**

**说明：**
TGW peering attachments 不支持 BGP，因此不会自动传播路由。必须将指向对等方 CIDRs 的 static routes 添加到两个 TGW route tables；在实时测试中，只有配置了 static routes 后流量才会传输。还需注意，在运维上 static TGW routes 的优先级高于 propagated routes，并且 peering attachment ID 在请求方与接受方之间不同。
</details>
