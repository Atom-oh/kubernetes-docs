# 共享 VPC 与连接

> **最后更新**：2026 年 9 月 13 日

## 1. 共享 VPC 所有者与参与者权限：常见误解

采用共享 VPC（通过 AWS RAM 在账户之间共享子网）时，最常见的误解是“共享意味着双方看到的内容完全相同”。实际上，所有者和参与者对不同资源拥有显著不同的权限。

| 资源 | 参与者权限 | 所有者权限 |
|---|---|---|
| 子网 | 仅可查看 | 完全权限 |
| 路由表 | 仅可查看 | 完全权限 |
| NACL | 仅可查看（所有者创建的 NACL） | 完全权限 |
| **NAT 网关** | **甚至无法查看** | 完全权限 |
| Internet 网关 | 仅可查看（仅出站 IGW 甚至无法查看） | 完全权限 |
| TGW 连接 | 无法创建 | 仅所有者可创建 |
| ENI | 对自己的 ENI 有完全权限 | 仅可查看他人的 ENI |
| 安全组 | 对自己的安全组有完全权限，也可使用所有者共享的安全组 | 仅可查看他人的安全组 |
| 流日志 | 仅适用于自己的 ENI | 可涵盖子网和所有 ENI（但参与者创建的流日志，即使所有者也无法查看或删除） |

这张表带来两项实际影响。

**流日志的所有权不对称。** 所有者集中管理的子网/VPC 日志可以与参与者的 ENI 日志并存，并明确各自用途、保留期限和成本归属。AWS 并未要求通过 SCP 禁止参与者创建所有日志。流日志用于观察流量，不会阻止流量。

**VPC/子网标签不会共享给参与者。** 应使用实际的 Load Balancer Controller 版本、模式和 IAM 权限测试资源发现。显式指定子网 ID 是一种可预测的方案；这并不意味着所有发现模式或版本都会失败。

安全组只支持 Allow 规则，多个安全组中的规则会合并；某个安全组里的宽泛 Allow 规则无法被另一个更严格的中央安全组抵消。可调整的默认配额是每个安全组 60 条规则（入站/出站 × IPv4/IPv6，分别计算），每个 ENI 可关联 5 个安全组，并且受 **“规则数 × 每个 ENI 的安全组数 ≤ 1,000”** 这一约束。Firewall Manager 的常见安全组策略也会占用相同的额度。

参与者的 ENI/安全组配额计入该参与者账户。每个可用区默认 5,000 个 ENI、每个区域默认 2,500 个安全组，仍可能成为各账户的瓶颈，并且可以调整。容量评估应与安全组授权分开进行。

<span id="_2-the-real-ceiling-on-shared-vpc-—-it-s-not-the-cidr"></span>

## 2. 按实际适用范围计算共享 VPC 配额

瓶颈出现的先后顺序取决于工作负载。要区分默认配额和已申请配额，并按各自适用范围预测增长。

| 范围 | 默认配额 | 说明 |
|---|---|---|
| 每个 VPC 路由表中的非传播路由 | IPv4/IPv6 各 500 条；可调整至 1,000 条 | 包含指向 TGW 的静态路由 |
| 每个 VPC 路由表中的传播路由 | 100 条；固定 | VGW 传播限制，与 TGW 路由表总量分开计算 |
| 所有 TGW 路由表中的静态与动态路由总数 | 每个 TGW 10,000 条 | 联系 SA/TAM 申请提高配额 |
| 每个 VPC 的参与账户数 | 100 个；可调整 | 共享主体数量 |
| 每个接收账户的共享子网数 | 100 个；可调整 | 可用区/用途组合 |
| 每个 VPC 的 NAU | 64,000；可调整至 256,000 | 包含 Pod IP、ENI 和托管前缀列表条目 |
| 每个 VPC 的子网数和路由表数 | 各 200 个；可调整 | 配置数量 |
| 每个 VPC 的 IPv4 CIDR 数 | 5 个；可调整至 50 个 | 还要评估地址消耗和碎片情况 |

**TGW 路由不会自动传播到 VPC 路由表。** VPC 所有者需要添加指向 TGW 的静态路由；连接传播由 TGW 路由表管理。因此，“TGW 前缀超过 100 个就会让共享 VPC 停止工作”这一说法不正确。默认路由是否保留或绕过检查，取决于实际路由关联和返回路径。

### 最小共享 VPC 池与按工作负载组划分的共享 VPC

比较“用一个最小配置的共享 VPC 汇集所有工作负载”与“每个工作负载组使用多个专用共享 VPC”时，有一个容易忽略的角度。

- **同一个 TGW–VPC 对只允许一个 VPC 连接。** 一个 VPC 最多可连接 5 个 TGW。每个连接默认每个方向最高 100 Gbps、每个可用区 7.5 MPPS；如需额外容量，请咨询 SA/TAM。
- 在最小配置中，所有工作负载的本地网络/外部流量都会汇聚到这一个连接；共享的不只是故障影响范围，还有**带宽和 PPS 上限**。
- 按工作负载组划分的配置让每个 VPC 使用自己的连接，从而分摊吞吐量上限。**能够分摊 TGW 吞吐量上限，是选择“多个专用共享 VPC”的实际主要原因。**

最终，最小配置与按组划分的配置之间，更适合从“**中央网络管道变更风险”与“VPC 级共享故障风险”的权衡**来理解，而非“成本与隔离”的取舍。这两种模式都取决于中央管道的质量，因此真正的决定因素是：在两种方案下，出现错误的中央路由变更后，测量发现和恢复速度。也可以考虑混合方案：通用工作负载采用最小配置；本地网络/外部连接流量大的工作负载采用专用配置；并按信任区拆分。

### Transit Gateway 关键配额

| 配额 | 默认值 | 是否可调整 |
|---|---|---|
| 每个账户的 TGW 数 | 5 | 是 |
| 每个 TGW 的连接数 | 5,000 | 是 |
| **每个 VPC 的 TGW 数** | **5** | **否** |
| 每个 TGW 的路由表数 | 20 | 是 |
| 每个 TGW 的路由总数 | 10,000 | 联系 SA/TAM |
| **同一个 TGW–VPC 对的连接数** | **1** | **否** |

**检查完整路径上的 MTU。** TGW 对 VPC/DX/Connect/对等连接路径支持 8,500 字节；VPN 使用单独的隧道限制。从 VPC 对等连接迁移到 TGW 时，要测试两端的巨型帧设置和 PMTUD。MSS 调整针对 TCP，无法解决 UDP 等所有分组协议的 MTU 问题。

对等连接 NAU 的计算范围是同一区域内一个 VPC 及其直接对等连接的 VPC（默认 128,000，最高 512,000），而不是组织内所有 VPC 或传递连接图中的所有 VPC。

## 3. 可用区 ID 与共享 VPC

可用区名称（例如 `ap-northeast-2a`）在不同账户中可能对应不同的物理可用区。跨账户放置资源时，应使用**可用区 ID（`apne2-az*`）**，而不是可用区名称。

对于 VPC CNI 自定义网络，应使用可用区 ID 将所有者子网映射到参与者节点所在的物理可用区。ENIConfig 名称必须与所选节点注解/标签匹配。使用 `ENI_CONFIG_LABEL_DEF=topology.kubernetes.io/zone` 时，应采用节点的可用区名称，并在 spec 中填写与该 AZ ID 对应的子网 ID。盲目使用 AZ ID 作为 ENIConfig 名称可能导致查找失败。单独使用辅助 CIDR 并不能构成安全边界。

## 4. 区域 NAT 网关

| 项目 | 行为 |
|---|---|
| 扩缩容 | 在同一个 ID 下自动扩缩；不需要公有子网 |
| 私有 NAT | 不支持 |
| 扩缩延迟 | 最长 60 分钟（此期间可能出现跨可用区流量） |
| 从区域型迁移到可用区型 | 连接会重置，IP 可能变化 |
| 受限可用区 | **不支持**（请提前确认） |

区域 NAT 网关比可用区 NAT 网关具有更高的 IP/连接数限制：区域型每个可用区允许 32 个 IP（可用区型为 8 个），每个 IP 针对同一目标（目标 IP + 端口 + 协议）可增加 55,000 个并发连接。对于**少量目标接收大量连接**的模式（例如支付处理商、物流集成），这项能力可以直接避免端口耗尽。

可以选择自动模式（由 AWS 管理 IP/可用区扩缩，推荐）或手动模式（由你直接管理）。**如果需要固定的出站 IP，并且要将它登记到外部合作方的允许列表中，则需要使用手动模式或集成 IPAM 公有 IPv4 分配策略。** 区域 NAT 网关路由表支持将 TGW 作为有效路由，因此可以同时使用中央 TGW 检查和区域 NAT；两者并不互斥。

## 5. TGW 与 Network Firewall（中央检查）

有两种方式可以集中检查东西向流量。

- **通过检查 VPC**：需要 appliance mode 和双向路由。
- **连接到 TGW 的 Network Firewall**：始终启用 appliance mode。

Network Firewall **不支持非对称路由**。如果 TGW 所有者账户和防火墙所有者账户不同，在删除权限和可见性方面会遇到限制。

从 AWS 的角度看，并没有要求必须进行中央检查。在大多数情况下，采用**混合方案**（在信任区内部使用分布式控制，仅在信任区之间或受监管路径上实施中央强制策略）是合理的。

## 6. AWS API 与 VPC 端点

应按服务、区域和功能检查端点及端点策略是否受支持。默认的完全访问端点策略不会授予新的 IAM 权限。将 `describe-vpc-endpoint-services` 清单与服务文档、私有 DNS 检查以及实际的允许/拒绝验证结合使用。

## 7. Route 53 Profiles 与混合 DNS

Route 53 Profile 可以关联 Private Hosted Zone、Resolver 规则（转发/系统）、DNS Firewall 规则组、**接口型 VPC 端点**以及 VPC Resolver 查询日志配置。一个 VPC 只能关联一个 Profile。

**最容易被误解的是优先级规则。** 规则不是“始终由本地 VPC 优先”，而是“**名称越具体，优先级越高**。”

| DNS 查询 | Profile 规则 | VPC 本地规则 | 应用的规则 |
|---|---|---|---|
| `example.com` | `example.com` | `example.com` | 本地 VPC（名称相同，本地规则优先） |
| `test.example.com` | `test.example.com` | `example.com` | **Profile（名称更具体，优先级更高）** |
| `marketing.example.com` | 无 | `marketing.example.com` | 本地 VPC |

如第二行所示，**在中央 Profile 中注册的更具体名称会覆盖工作负载的本地规则。** 如果不了解这一点，工作负载可能会遇到原因不明的名称解析失败。**建议将以下规则正式化：“中央 Profile 拥有的名称不能比委派给工作负载的命名空间更具体。”** 实际上，中央统一管理命名空间，并将其下的子域委派给工作负载团队，是一种有效的组合方式。首尔区域支持 Route 53 Profiles。

## 8. VPC 之间的连接选项

这些选项并非互斥；应根据流量需求，为每条连接选择合适的模式。

| 选项 | 适用场景 | 限制 |
|---|---|---|
| VPC 对等连接 | 少量 VPC 之间的直接双向连接 | 对等 NAU 上限为 128,000（→512,000）；CIDR 不可重叠；不支持传递连接 |
| Transit Gateway | 大量 VPC、本地网络、中央检查 | 分别统计 TGW 路由表总量、VPC 静态路由、每对连接数和吞吐量 |
| PrivateLink | 单向暴露特定服务 | 端点成本，以及服务提供者/使用者的持续运维 |
| **VPC Lattice** | 应用服务/资源连接，包括 CIDR 重叠的场景 | 与 PrivateLink/NAT 等替代方案比较协议、身份验证和成本 |
| 同一 VPC 内的本地路由 | 同一信任区，且资源可以共用一个 VPC | 路由/DNS/IP 故障影响范围相同 |

### VPC Lattice 的限制

对 Lattice 的描述往往过于随意，没有充分强调它的实际限制。

| 项目 | 数值 | 影响 |
|---|---|---|
| 每个 VPC 的服务网络关联数 | **仅 1 个** | 需要连接多个网络时，必须使用服务网络类型的 VPC 端点 |
| **Lattice 服务的最长连接生命周期** | **10 分钟** | 测试重连/重试/幂等性；并区分资源连接 |
| Lattice 服务空闲超时 | 默认 60 秒（60–600 秒） | |
| Lattice 资源空闲超时 | 350 秒；连接生命周期不受限 | TCP 资源受到的限制较少 |
| 每个服务每个可用区的带宽/RPS | 10 Gbps / 10,000 RPS（可提高） | |
| 每个服务的监听器数/每个监听器的规则数 | 2 / 10 | |
| 每个区域的服务网络数 | 50 | |
| MTU | 8,500 字节 | |

应分别评估服务和资源上的长连接流量。服务的 10 分钟连接生命周期不同于资源的 350 秒空闲超时。HTTP/HTTPS 监听器原生不支持 WebSocket；TLS 监听器或 Lattice 资源可提供替代路径。应在验证协议、重连、SNI、授权和负载后再做选择。

## 9. 东西向检查选项

| 选项 | 配置方式 |
|---|---|
| 分布式策略控制 | 安全组/NACL/路由/NetworkPolicy + 流日志 |
| 每 VPC 分布式防火墙 | 每个 VPC 单独部署防火墙 |
| TGW 中央检查 | 在 Transit Gateway 路径上集中检查流量 |
| **混合方案** | 在信任区内分布式检查，在信任区之间/受监管路径上集中检查 |

应记录共享 VPC 日志的所有权、访问权限、保留期限和重复成本。所有者和参与者的日志都可以集中收集；禁止参与者创建日志并非前提。

## 后续

确定 VPC 边界后，下一步是在此基础上划分数据和安全边界 → [数据与安全边界](./05-data-security-boundaries.md)

## 参考资料

- [VPC 配额](https://docs.aws.amazon.com/vpc/latest/userguide/amazon-vpc-limits.html)
- [共享 VPC 所有者/参与者职责](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-share-limitations.html)
- [共享子网支持的服务](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-sharing-service-behavior.html)
- [共享子网的可用区 ID](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-sharing-share-subnet-working-with.html)
- [安全组共享](https://docs.aws.amazon.com/vpc/latest/userguide/security-group-sharing.html)
- [安全组规则](https://docs.aws.amazon.com/vpc/latest/userguide/security-group-rules.html)
- [Firewall Manager 常见安全组策略](https://docs.aws.amazon.com/waf/latest/developerguide/security-group-policies-common.html)
- [Firewall Manager 安全组审计策略](https://docs.aws.amazon.com/waf/latest/developerguide/security-group-policies-audit.html)
- [区域 NAT 网关](https://docs.aws.amazon.com/vpc/latest/userguide/nat-gateways-regional.html)
- [TGW 配额](https://docs.aws.amazon.com/vpc/latest/tgw/transit-gateway-quotas.html)
- [Transit Gateway 概述](https://docs.aws.amazon.com/vpc/latest/tgw/tgw-transit-gateways.html)
- [连接到 TGW 的 Network Firewall](https://docs.aws.amazon.com/network-firewall/latest/developerguide/tgw-firewall.html)
- [Network Firewall 非对称路由](https://docs.aws.amazon.com/network-firewall/latest/developerguide/asymmetric-routing.html)
- [VPC Lattice 配额](https://docs.aws.amazon.com/vpc-lattice/latest/ug/quotas.html)
- [VPC Lattice 概述](https://docs.aws.amazon.com/vpc-lattice/latest/ug/what-is-vpc-lattice.html)
- [PrivateLink 支持的服务](https://docs.aws.amazon.com/vpc/latest/privatelink/aws-services-privatelink-support.html)
- [VPC 对等连接](https://docs.aws.amazon.com/vpc/latest/peering/vpc-peering-basics.html)
- [VPC 连接选项白皮书](https://docs.aws.amazon.com/whitepapers/latest/aws-vpc-connectivity-options/amazon-vpc-to-amazon-vpc-connectivity-options.html)
- [集中式 VPC 检查](https://docs.aws.amazon.com/whitepapers/latest/building-scalable-secure-multi-vpc-network-infrastructure/centralized-network-security-for-vpc-to-vpc-and-on-premises-to-vpc-traffic.html)
- [Route 53 Profiles](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/profiles.html)
- [Route 53 Resolver 混合 DNS](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/resolver.html)
- [TGW 路由传播常见问题](https://aws.amazon.com/transit-gateway/faqs/)
- [ENIConfig 标签映射](https://docs.aws.amazon.com/eks/latest/best-practices/custom-networking.html)
- [Lattice 监听器协议](https://docs.aws.amazon.com/vpc-lattice/latest/ug/listeners.html)
