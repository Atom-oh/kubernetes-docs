# 跨组织 VPC 连接测验

请区分报告中的测量结果与 AWS 平台要求。

## 1. 与资源所有者不属于同一 Organization 的账户共享 TGW，需要满足什么条件？

- A. 合并两个 Organization
- B. 共享资源允许外部主体，并由接收账户接受 RAM 邀请
- C. 通过 VPN 连接两个管理账户
- D. 取得 Support 工单审批

<details>
<summary>显示答案</summary>

B. 共享设置必须允许外部账户，接收方必须先接受邀请，才能使用共享资源。`CreateResourceShare` 默认将 `allowExternalPrincipals` 设为 true，因此并非始终都需要显式指定 `--allow-external-principals`。请检查实际生效的配置以及 IAM/共享限制。

</details>

## 2. 禁用 AutoAcceptSharedAttachments 后，要使跨账户 VPC attachment 连接到共享 TGW，还需要什么？

- A. 不需要接受
- B. TGW 所有者必须接受待处理的共享 attachment
- C. 这类 attachment 不能跨 Organization 建立
- D. 它总会在 24 小时后激活

<details>
<summary>显示答案</summary>

B. 默认禁用共享 attachment 的自动接受。接受 RAM 共享和接受 VPC attachment 是两个独立步骤。如果启用了自动接受，第二个流程会有所不同。TGW 所有者控制 TGW 路由表；接收账户仍负责自己的 VPC 路由和安全设置。

</details>

## 3. 报告中的 TCP_RR 对比 M3−M2 能证明什么？

- A. 每个 TGW 跳点总会增加相同的单向延迟
- B. 报告的路径中位数相差 0.619−0.048 = 0.571 ms
- C. AWS 提供有保证的延迟 SLA
- D. GPU 训练的吞吐量

<details>
<summary>显示答案</summary>

B. 这是报告中的往返时延中位数之差，并非对单个组件的纯测量，也不是每跳固定值。在该次测试中，两台 TGW 的路径的 TCP_RR 中位数低于单台 TGW 的路径。要得出更广泛的结论，还需要原始样本、不确定性和工作负载测量；本次复核没有重新运行基准测试。

</details>

## 4. 对已测试的 Lattice HTTP service/VPC association 路径，应检查目标 SG 中的什么设置？

- A. 开放所有入站和出站端口
- B. 在实际目标端口和运行状况检查端口上，允许正确区域和 IP 地址族对应的托管前缀列表
- C. 用 NACL 替代安全组
- D. 无论后端如何都只允许 TCP 443

<details>
<summary>显示答案</summary>

B. Lattice 流量可能来自其托管前缀列表中的地址，因此仅允许客户端 VPC CIDR 并不足够。历史示例中的 169.254.171.0/24 并非完整且通用的地址定义。应使用文档列出的前缀列表和已配置端口；endpoint/resource gateway 路径有各自的控制措施。

</details>

## 5. 哪些对比方案可以在 VPC CIDR 重叠、且不在这些重叠网段之间直接路由的情况下提供服务访问？

- A. 直接 VPC peering
- B. 未修改的直接 TGW 路由
- C. PrivateLink 服务访问或 VPC Lattice 服务访问
- D. 没有任何架构能够处理网段重叠

<details>
<summary>显示答案</summary>

C. 这些方案提供的是服务访问，而不是不受限制的双向 VPC 路由。直接 VPC peering 无法连接 CIDR 重叠的 VPC，路由方案则需要明确且无歧义的地址规划。NAT 和重新规划地址也是其他选择，所以 PrivateLink/Lattice 并非唯一可行架构。

</details>

## 6. 关于直接 TGW-to-TGW peering，哪项路由说明正确？

- A. peering 会通过 BGP 自动传播所有路由
- B. 明确配置静态对等路由以及所需的 VPC 路由
- C. 只需配置 VPC 路由表
- D. 接受 peering 后会自动创建所有必需路由

<details>
<summary>显示答案</summary>

B. peering attachment 使用静态路由；也可以通过自动化管理这些路由。TGW 路由先选择最长匹配前缀；当静态路由与传播路由的前缀相同时，静态路由优先。应在接收方区域使用其 attachment ID 接受待处理的 peering 请求；仅凭 NotFound 不能证明请求方和接收方的 ID 必须不同。

</details>

[返回指南](../../networking/05-cross-org-vpc-connectivity.md)
