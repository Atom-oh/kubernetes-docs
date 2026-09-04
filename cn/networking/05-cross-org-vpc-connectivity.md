# 跨 Organization VPC 连接

> **最后更新**: September 1, 2026

本文介绍跨越两个不同 AWS Organization **连接 VPC 的五种方式**——例如，当 GPU 工作负载由独立于现有 MSP 付款方的单独付款方（独立 Organization）签约时。本文所有数字均来自在两个真实 Organization 之间进行的实际构建和测量验证（ap-northeast-2，两个账户均固定在 ZoneId `apne2-az1`）。

## 目录

1. [为何需要跨 Organization 连接](#why-cross-org-connectivity)
2. [五种方案对比](#comparing-the-five-options)
3. [现场验证结果](#field-verification-results)
4. [延迟测量（M1–M7）](#latency-measurements-m1m7)
5. [现场运维发现](#operational-findings-from-the-field)
6. [按场景推荐的架构](#recommended-architecture-by-scenario)
7. [结论](#conclusion)

## 为何需要跨 Organization 连接

GPU 实例（P5/P6 等）的成本很高，因此 Organization 越来越多地选择通过**独立付款方（独立 AWS Organization）**而非现有 MSP 付款方来签约。这种做法的常见动机包括：

- **计费分离**：GPU 专属批量折扣 / EDP 优化
- **Service quota 隔离**：独立管理 GPU vCPU 限额和 Capacity Blocks
- **爆炸半径控制**：让 SCP 配置错误和安全事件远离现有生产环境
- **法规合规**：为 AI/ML 工作负载分隔数据边界和审计轨迹

关键挑战是连接现有环境（ORG A）与 GPU 环境（ORG B）。从 EKS 视角来看，这包括训练集群（ORG B）访问现有数据管道（ORG A），或将推理 API 暴露给现有服务。

## 五种方案对比

| 方面 | ① TGW RAM 共享 | ② VPC Peering | ③ PrivateLink | ④ TGW Peering | ⑤ VPC Lattice |
|---|---|---|---|---|---|
| 机制 | 通过 RAM 将 TGW 共享给外部账户 | 1:1 VPC 连接 | 基于 NLB 的终端节点 | 每个 ORG 的 TGW 之间进行 Peering | L7 服务网络 |
| 重叠的 CIDR | ❌ | ❌ | ✅（基于 ENI） | ❌ | ✅（基于 link-local） |
| 方向 | 双向 L3 | 双向 L3 | 单向（Consumer→Provider） | 双向 L3 | 单向（Consumer→Provider） |
| 传递路由 | ✅ 通过 TGW RT | ❌ | ❌ | ✅ | ❌（按服务） |
| 路由控制 | **TGW 所有者账户（ORG A）** | 双方独立 | Provider 控制主体 | **每个 ORG 独立** | 服务网络所有者 |
| 预置时间（实测） | TGW 约 3 分钟 + 接受步骤 | **不到 1 分钟** | Endpoint 约 3 分钟 | **约 7 分钟（最长）** | 约 5 分钟 |

## 现场验证结果

五种方案均已在两个不同 Organization 的账户之间构建，并通过控制平面（连接建立）和数据平面（真实流量）进行测试。**五种方案都可以实现。**没有任何方案被 Organization 边界本身阻止——该边界只体现为显式流程：**指定账户 ID，并由接收方接受**。

![跨 Organization 的五条实测路径拓扑](../../assets/cross-org-5paths-latency.png)

## 延迟测量（M1–M7）

**测量设计**——信号低于 1 毫秒，因此测量误差必须小于信号：

- 使用 **c7g.large** 实例（不使用突发型实例）；响应端为**一个 EC2 实例（nginx 固定 200）**——负载均衡器仅在结构上必需的位置出现（③⑤，以及为隔离 NLB hop 的 M7）
- 响应端有 3 个 ENI（每条路径子网配备独立的返回路由表），因此 **M1–M7 以轮询交错方式运行 ×5 轮**，无需切换路由
- 主要指标：**持久 TCP_RR ping-pong，每条路径 1,500 个样本**（消除进程启动和握手成本）；次要指标：每条路径 ICMP 100 次、HTTP keep-alive 275 次

| ID | 路径 | ICMP p50 | TCP_RR p50 | RR p99 | RR sd | HTTP KA p50 | TTL |
|---|---|---|---|---|---|---|---|
| M1 | 同一 VPC → EC2（基线） | 0.121 | **0.049** | 0.062 | 0.007 | 0.087 | 127 |
| M2 | ② VPC Peering → EC2 | 0.125 | **0.048** | 0.057 | 0.011 | 0.080 | 127 |
| M3 | ① 共享 TGW（RAM）→ EC2 | 0.535 | **0.619** | 0.695 | 0.141 | 0.686 | 126 |
| M4 | ④ TGW Peering（2 hops）→ EC2 | 0.912 | **0.599** | 0.855 | 0.133 | 0.488 | 125 |
| M5 | ③ PrivateLink → NLB → EC2 | not measured | **0.961** | 1.084 | 0.035 | 0.711 | — |
| M6 | ⑤ VPC Lattice → EC2 target | not measured | not measured（仅 L7） | — | — | **1.635** | — |
| M7 | ② Peering → NLB → EC2（NLB hop 隔离） | not measured | **0.841** | 0.909 | 0.119 | 0.883 | — |

**派生指标（p50，毫秒）：**

| 指标 | 定义 | TCP_RR | ICMP |
|---|---|---|---|
| TGW 1-hop 成本 | M3 − M2 | **+0.571** | +0.410 |
| TGW 2-hop 成本 | M4 − M2 | **+0.551** | +0.787 |
| NLB hop 成本 | M7 − M2 | **+0.793** | — |
| 纯 PrivateLink ENI 开销 | M5 − M7 | **+0.120** | — |
| Lattice proxy 成本（HTTP） | M6 − M2 | +1.555 | — |

**结论：**

> **在同一 AZ 内，TGW hop 在 p50 时增加 0.4–0.6 毫秒**——与常见的“每 hop 低于 1 毫秒”观察结果一致。
> **VPC Peering 的延迟成本在测量范围内为零**（M2 0.048 ≈ M1 基线 0.049）。
> **PrivateLink ENI 本身仅增加 +0.12 毫秒**——PrivateLink 总延迟（0.96 毫秒）的主要部分来自结构上必需的 **NLB hop（+0.79 毫秒）**。Lattice 的 L7 proxy 成本为 +1.6 毫秒。

**补充测量——服务前置的公平比较（每条路径均使用 NLB）：**在实际部署中，Peering 和 TGW 路径也会通过 NLB 将服务前置，因此还为每条 L3 路径构建并测量了采用 NLB 前置的配置（每子网 NLB、IP target、相同方法）。

| 配置 | TCP_RR p50 | HTTP KA p50 |
|---|---|---|
| ② Peering → NLB → EC2 | **0.622** | 0.648 |
| ③ PrivateLink → NLB → EC2 | **0.658** | 0.845 |
| ① 共享 TGW → NLB → EC2 | **1.273** | 1.257 |
| ④ TGW Peering → NLB → EC2 | **1.425** | 1.279 |
| ⑤ Lattice（自身充当 LB——无需 NLB） | — | **1.680** |

> **服务暴露框架的结论：**纯 PrivateLink ENI 成本为 +0.036 毫秒（N5−N2）——实际上为零。在响应端前方部署 NLB 作为常见基线的真实服务暴露设置中，**③ PrivateLink 与 Peering+NLB 相当，并且比 TGW 路径 + NLB 快约 2 倍。**“直连 TGW 优于 PrivateLink”仅在没有 LB 的直连框架中成立。Lattice 自身充当负载均衡器，因此不需要单独的 NLB——在相同框架下，它与 TGW+NLB 的差距缩小为 +0.3–0.4 毫秒。

**方法论经验**（为何舍弃并重做了较早的一轮测量）：将突发型实例（t-family）、两阶段 NLB→ALB proxy 链以及每个请求的新连接（curl）组合在一起，会让低于 1 毫秒的信号淹没在噪声中（与路径无关的 p95 约为 7 毫秒）。新 TCP 流在首次经由 TGW/NLB 的 RTT 中确实会产生 +0.6–1.6 毫秒的 flow-setup 成本，因此**应分别评估 keep-alive/长连接工作负载（gRPC、NCCL、DB pools）与一次性连接工作负载的延迟**。

## 现场运维发现

1. **跨 Organization 的 RAM 共享需要明确的邀请接受步骤**——未使用 `--allow-external-principals` 时共享会被拒绝，并且资源在接收方运行 `accept-resource-share-invitation` 前不可见（TGW 和 Lattice 均如此）。自动化流水线需要此接受步骤。
2. **外部 ORG 对共享 TGW 的 attachment 会停留在 `pendingAcceptance`**——TGW 所有者必须接受它。“所有者侧集中控制”在 API 层面得到强制执行。
3. **TGW Peering 在两端显示不同的 attachment ID**——使用请求方 ID 调用接受 API 会返回 `NotFound`。接受方账户必须列出并找到自己的 ID，传播大约需要 2 分钟。
4. **TGW Peering 不支持 BGP**——必须手动向两个 TGW 路由表添加静态路由。
5. **Lattice 数据平面流量来自 link-local（169.254.171.0/24）**——如果 target SG 只允许 VPC CIDR，则所有 health check 都会变为 UNHEALTHY。请将托管前缀列表 `com.amazonaws.<region>.vpc-lattice` 添加至 SG。
6. **静态 TGW 路由优先于传播路由**——两者共存时应留意非预期的路径选择。
7. **账户自动化会干扰资源清理**——GuardDuty Runtime Monitoring 的托管 SG 会阻止 VPC 删除（DependencyViolation），自动附加的 IAM policy 会阻止 role 删除；残留的 Lattice target group 同样会阻止 VPC 删除。

## 按场景推荐的架构

| 场景 | 首选方案 | 理由（实测） |
|---|---|---|
| 完整 GPU ORG 分离、双向批量流量（训练数据） | **④ TGW Peering** | 每个 ORG 独立路由 + 每 hop 0.4–0.6 毫秒的代价可忽略不计 |
| 仅暴露推理 API（单向） | **③ PrivateLink** | 最小化暴露，可接受重叠 CIDR，在服务前置比较中与 Peering+NLB 相当（比 TGW 路径 + NLB 快约 2 倍） |
| 无法避免的 CIDR 重叠（M&A、MSP 迁移） | **③ PrivateLink / ⑤ Lattice** | 基于 ENI / link-local——不依赖 CIDR |
| 仅向现有 TGW 添加一个 GPU 账户 | **① TGW RAM 共享** | 复用现有 hub；外部 ORG 无法更改路由 |
| 小型 PoC（1–2 个 VPC） | **② VPC Peering** | 设置时间不到 1 分钟，延迟成本 ≈ 0，无需额外基础设施 |
| 需要 L7 auth/governance 的服务暴露 | **⑤ VPC Lattice** | 内置 IAM Auth 和服务发现（接受 +1.6 毫秒的 proxy 成本） |

对于大多数 GPU 分离场景，**④ TGW Peering（双向基础设施）+ ③ PrivateLink（推理 API 暴露）**的混合方案最优，测量结果支持这一建议。

## 结论

- 五种方案都可以纯粹通过 API 在不同 Organization 之间配置；Organization 边界仅表现为“指定账户 ID + 由接收方接受”。
- 在同一 AZ 内：TGW 为每 hop 0.4–0.6 毫秒，VPC Peering ≈ 0，NLB hop +0.79 毫秒，PrivateLink ENI +0.12 毫秒，Lattice proxy +1.6 毫秒——延迟成本会随 hop 和 proxy 层数如实增长。
- 对于 EKS：通过 TGW 路由批量训练数据传输（长连接），并通过 PrivateLink 暴露推理 API。

**限制（未测量）：**经由 Network Firewall 检查的路径、Cross-Region、CIDR 重叠环境（仅确认功能可用）以及吞吐量/并发轴。

---

## 参考资料

- [构建可扩展的多 VPC 网络基础设施（AWS 白皮书）](https://docs.aws.amazon.com/whitepapers/latest/building-scalable-secure-multi-vpc-network-infrastructure/welcome.html)
- [通过 RAM 进行 TGW 跨 Organization 共享（AWS Prescriptive Guidance）](https://docs.aws.amazon.com/prescriptive-guidance/latest/integrate-third-party-services/architecture-3-1.html)
- [选择单个还是多个 Organization（AWS Architecture Blog）](https://aws.amazon.com/blogs/architecture/choosing-between-single-or-multiple-organizations-in-aws-organizations/)
- [VPC Lattice（本系列）](02-vpc-lattice.md)
