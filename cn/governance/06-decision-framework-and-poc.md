# 决策框架与 PoC 设计

> **最后更新**：2026 年 10 月 12 日

前文讨论的 Landing Zone、账户 / IAM、EKS、VPC 以及数据 / 安全边界应分别评估；但在实际工作中，都需要通过同一个决策矩阵进行复现和验证。本文介绍如何设计该矩阵，以及如何通过 PoC 对需要真实测量的部分进行验证。

## 1. 容易遗漏的决策因素

无论你多么仔细地设计边界、账户和网络结构，如果不考虑以下因素，就无法判断设计是否正确。

### CUJ 级 RTO / RPO 目标：最大的缺口

如果没有按 CUJ（关键用户旅程）定义 RTO（恢复时间目标）/ RPO（恢复点目标），就无法判断：

- A/B EKS Runtime 故障转移是否足够快（DNS TTL + 边缘传播 + Route 53 传播 + 健康检测延迟的总和）
- 集中式还是工作负载自有的数据归属模型可以真正恢复（快照复制时间是否计入 RTO）
- 2-AZ 和 3-AZ 之间的差异是否重要（N-1 状态下 SLO 是否仍然满足）
- Cell 级隔离带来的额外成本是否合理

**在开展其他工作之前，先定义 CUJ 级 RTO / RPO / 可接受错误率目标表。**

### 事件期间的值班归属

即使已在边界决策中考虑安全、配额、成本、生命周期和故障影响范围，如果没有说明“谁先响应”，当凌晨两点共享集群发生事故，且不清楚问题出在 CNI 还是应用时，就会浪费时间。在决策矩阵中增加“主要响应人”和“升级路径”列，并采用以下规则：**一个边界若有多个主要响应人，就应考虑拆分。**

### 目标 Kubernetes 版本和升级策略

`trafficDistribution` 字段值、Karpenter 的 ARC zonal shift 集成（1.12+）、是否采用 EKS Auto Mode（由谁负责节点生命周期），以及插件兼容性矩阵，都取决于 EKS 版本。如果采用 A/B EKS Runtime 是为了隔离升级风险，就必须明确规定允许的版本偏差、始终先升级一侧的规则，以及是否使用延长支持。

<span id="alb-weighted-target-group-s-fail-open-behavior"></span>

### 区分加权转发与目标组 fail-open

加权转发动作不会因为某个加权目标组为空或不健康，就自动故障转移到另一个目标组。**所选组内部的 fail-open** 是另一项行为：健康目标低于阈值时，负载均衡器节点可能会将请求转发到可访问但不健康的目标。请通过以下属性检查 DNS 和路由故障转移：

- `target_group_health.unhealthy_state_routing.minimum_healthy_targets.count`（或 `.percentage`）
- `target_group_health.dns_failover.minimum_healthy_targets.count`（或 `.percentage`）

统一配置会对这两种动作应用相同的阈值。DNS 故障转移阈值必须不小于路由故障转移阈值；两者都设置时，数量或百分比任一条件都可以触发动作。百分比以已注册目标数量为基准，并不能证明 CUJ 吞吐量或 N-1 SLO 容量。在修改权重前，也应检查实际负载、错误率和延迟。

### 控制未使用的区域

除单区域决策之外，还需处理以下事项：

- **预防**：使用 SCP `aws:RequestedRegion` Deny（为全局服务设置例外列表）
- **检测**：检查允许 / 可用区域中的 CloudTrail、GuardDuty 和 Security Hub CSPM 覆盖情况。禁用某个产品并不意味着所有活动都无法检测。
- **选择加入区域**：可以禁用未使用的选择加入区域；默认启用的区域则不能禁用。禁用区域不会删除已有资源，也不会停止其费用。应结合资源清理、SCP 和检测措施。

### 成本可观测性与何时强制标签

将 Flow Logs、ENI / IP 映射、Kubernetes 工作负载身份和 CUR 计费类别关联起来，验证跨可用区成本的归属。并非每个 ENI 都支持用户标签或创建时的 RequestTag 条件。请根据各服务的具体支持范围应用标签策略、IaC 和受支持的 SCP 条件。

## 2. 设计决策矩阵

这些文档讨论的选项（独立评估边界、混合账户组合、共享 + 专用 EKS、混合信任区 VPC、混合数据、混合密钥归属）都将“**能通过决策矩阵复现**”作为其有效条件。没有决策矩阵，就无法将 PoC 结果转化为标准。

建议决策矩阵包含以下列：

| 列 | 用途 |
|---|---|
| 是否需要 EKS？ | 判断 EKS 边界是否从属于 VPC 边界 |
| 跨账户资源访问 | 根据情况选择目标角色链、资源策略或 IRSA |
| 是否使用不支持共享子网的服务？ | 判断是否要从 Shared VPC 本地化策略中排除 |
| 每个 Permission Set / 账户对的组数 | 检查实际的 100 个限制和增长情况；50 是可选的本地预警值 |
| 主要响应人 / 升级路径 | 有多个主要响应人的边界应考虑拆分 |
| CUJ RTO / RPO | 数据和可用性设计决策的依据 |

## 3. PoC 设计模式

有些项目无法只靠纸面方案最终确定，需要真实测量。以下 PoC 按优先级排列。

### PoC-0：决策矩阵试运行（所有其他 PoC 之前）

- **输入**：10–15 个有代表性的工作负载（包括 CUJ、至少一个 PII 工作负载、至少一个常见领域工作负载、至少两个小型内部工具，以及至少一个外部合作伙伴集成）
- **流程**：由两个人分别独立应用决策矩阵，并比较结果
- **示例成功标准**：分歧低于 20%、例外低于 15%；应将这些阈值视为本地假设并进行调整
- **副产物**：评估结果会估算账户 / VPC / 集群数量，并据此确定其他 PoC 的配额测量目标

### PoC-1：共享集群 + 工作负载账户

| 测量项 | 成功标准 |
|---|---|
| Pod Identity / 资源策略 / IRSA 权限路径 | 验证源 / 目标复用、范围、撤销、KMS 和资源策略；不设固定的两角色公式 |
| ALB Controller 在共享子网中的自动发现 | 检查基于标签的自动发现是否失败 → 若失败，则统一使用显式 annotation |
| Access Entry 增长率 | （每增加一个工作负载的增量）× 目标工作负载数量 < 3,000 |
| 托管节点组数量 | 对照 30 的默认值和已应用配额评估余量；区分放置控制与安全隔离 |
| 集群账户与工作负载账户间的主要响应时间 | 确定“CNI 问题还是应用问题”所需时间 |
| 对参与账户过宽的 SG Allow 规则的检测 / 阻止时间 | 通过 Firewall Manager 审计策略测量从检测到阻止所需时间 |

### PoC-2：A/B EKS Runtime 与 AZ 配置（前置条件：已定义 CUJ 级 RTO / RPO）

| 测量项 | 成功标准 |
|---|---|
| 从[第 3 章](./03-eks-multi-account-multi-cluster.md)列表中注入至少 3 种故障 | 确认每项故障确实只影响一个集群 |
| ARC zonal autoshift 演练 | 确认 A / B 两个集群都能独立应对 N-1 可用区的峰值负载 |
| CoreDNS N-1 吞吐量 / 延迟 | 测量延迟增长率，以及是否达到每个 ENI 每秒 1,024 个数据包的限额 |
| CUJ 服务图的 AZ 覆盖 | 验证仍存活的 AZ 中依赖项是否可达、容量是否充足并具备回退能力 |
| 有状态恢复 | 验证 EBS AZ 限制、替代存储 / 复制方式、恢复时间和数据丢失 |
| A → B 端到端故障转移时间 | 单独测量边缘故障转移和 Route 53 记录变更 |
| 回滚时间 | 与故障转移时间分开测量 |
| 跨 AZ 字节数 | 根据 Flow Logs 比较优化前后的结果 |
| 预置容量倍数 | 将实测值与 2 倍 / 1.5 倍假设进行比较 |

### PoC-3：最小化 Shared VPC / Shared VPC 池

| 测量项 | 成功标准 |
|---|---|
| **TGW / VPC 路由（当前 / 3 年预测）** | 区分 TGW 路由表总数 10,000，与 VPC 非传播路由 500 / 可调整至 1,000；另区分 VGW 的 100 |
| 参与账户增长率 | 对照 100 个上限以及目标团队数量 |
| 每个账户的共享子网数 | 将 AZ × 信任区 × 用途组合与 100 个上限比较 |
| NAU 使用量 | 根据 Pod 密度评估何时需要从 64,000 调整至 256,000 |
| 路由 / DNS 变更请求到所有者完成处理的时间 | 量化瓶颈 |
| Flow Logs 证据完整性 | 验证所有者和参与方日志能否共同还原完整流量路径 |
| 最小化与专用配置下，错误的中心路由变更检测 / 恢复时间 | 测量两种方案（这是实际决策因素） |
| TGW attachment 吞吐量 | 对照每个 AZ 100 Gbps / 7.5M PPS 的余量 |

## 4. 与 AI 驱动运维的关系

该框架不仅适用于账户 / VPC / EKS 等拓扑选择，也可以扩展为应用于每个 ADR（架构决策记录）的运维原则。自动化基础设施变更通常有以下执行路径：

- **仅 IaC**：只通过人工编写、人工审查的 IaC 变更。可复现性最高，但紧急 / 探索性工作较慢。
- **AI 辅助 IaC**：智能体生成 IaC 变更提案，再通过现有的 review → plan → apply 流程执行。能降低编写成本，但可能产生大量生成式 diff，或与实际状态产生偏差。
- **策略 / 意图 + 生成的计划**：智能体读取当前状态并生成执行计划。意图与后端相分离；但意图 schema 或状态对账较弱时，会导致结果不一致。
- **智能体直接通过 MCP / CLI / API 操作**：经批准的智能体直接执行变更并进行验证。速度最快，但可能出现权限范围过广、部分失败和提示注入风险。
- **按风险分层的混合模式**：高风险、持久配置变更使用 IaC；低风险、可逆操作允许智能体有限度地直接执行。这是大多数组织的现实方向。

对于每种执行路径，都应根据风险定义适当控制措施：机器可读的意图、执行前快照、计划、确定性的策略检查、审批、范围受限的临时身份、执行后检查、CloudTrail 日志、实际状态对账以及恢复约定。

> **AWS MCP Server 范围**：截至 2026 年 10 月 12 日检查时，端点表列出 8 个区域（us-east-1、us-west-2、ap-northeast-1、ap-southeast-1 / 2、eu-central-1 和 eu-west-1 / 2），没有首尔（ap-northeast-2）端点。端点所在区域不同于受管理资源所在区域。API 执行使用 IAM 和下游权限，并可通过 CloudTrail 记录进行审查。应根据组织要求评估端点、身份验证、日志和数据路径；仅仅没有首尔端点，并不能证明违反了监管要求。

## 相关文档

- [企业云治理概述](./00-governance-overview.md)
- [Landing Zone、OU 和组织控制](./01-landing-zone-and-ou.md)
- [账户结构与 IAM 边界](./02-account-and-iam.md)
- [多账户、多集群 EKS 架构](./03-eks-multi-account-multi-cluster.md)
- [共享 VPC 与连接](./04-shared-vpc-and-connectivity.md)
- [数据与安全边界](./05-data-security-boundaries.md)

## 参考资料

- [ALB 目标组属性](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/edit-target-group-attributes.html)
- [ALB 目标组健康状态](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/load-balancer-target-groups.html#target-group-health)
- [ALB 规则动作类型（加权）](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/rule-action-types.html)
- [Route 53 加权路由](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/routing-policy-weighted.html)
- [Route 53 故障转移路由](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/routing-policy-failover.html)
- [AWS MCP Server](https://docs.aws.amazon.com/agent-toolkit/latest/userguide/mcp-server.html)
- [AWS MCP Server IAM](https://docs.aws.amazon.com/agent-toolkit/latest/userguide/security_iam_service-with-iam.html)
- [AWS MCP 区域端点](https://docs.aws.amazon.com/general/latest/gr/aws-mcp.html)
- [已禁用区域中的费用](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/checklistforunwantedcharges.html)
