# 网络专家学习路径

> **资源核查日期**：2026年9月15日
>
> **环境**：用于主机练习的一次性 Ubuntu Server 24.04 LTS 或 Rocky Linux 9 虚拟机。路由/EVPN 工具和云环境有各自独立的章节前置条件。

这些进阶练习册承接[初学者课程](../beginner/README.md)。将协议原理与代码和数据包联系起来，再依据证据评估路由策略、Linux 性能和云架构。

专家级目标是**明确应当满足的条件、通过观察检验假设，并解释变更的影响及恢复方法**。仅有固定的学习时长或一项认证，并不能保证具备这种能力。

## 入门检查 {#entry-check}

能够解释并复现以下内容后，再进入第 1 章：

- 区分 IP、子网、网关和 DNS 的作用，以及 MAC/ARP 的作用。
- 阅读 `ip route get`、`ss` 和有范围限制的 `tcpdump` 抓包，并指出观察点。
- 验证 SSH 密钥访问和实验防火墙策略，然后恢复之前的状态。
- 区分 HTTP 错误、连接失败和名称解析失败。
- 解释交换机、路由器、防火墙和负载均衡器、VLAN 以及 LAN/WAN 边界的作用。进入第 7 章前，请对照[网络基础知识第 5 部分](../../basics/06-network-fundamentals-part5.md)检查这些内容。
- 将管理路径与实验路径分开，并识别属于自己的文件、虚拟机和容器。

使用[初学者综合项目](../beginner/08-container-cloud-capstone.md)补习欠缺的技能。主机上没有某条命令时，请完成[客户机工具准备](../beginner/README.md#guest-tools)。

## 九本练习册 {#course-map}

每一行都遵循**阅读 → 实验或设计验证 → 证据 → 讲解型测验**。外部课程提供阅读范围；这些练习册则提供评估自己成果的方法。

| 顺序 | 练习册 | 交付成果 |
|---|---|---|
| 1 | [协议与实现项目](01-protocol-projects.md) · [测验](../../quizzes/networking/expert/01-protocol-projects-quiz.md) | 请求路径、探测/响应关联、协议边界和边缘情况 |
| 2 | [路由策略与收敛](02-routing-policy-convergence.md) · [测验](../../quizzes/networking/expert/02-routing-policy-convergence-quiz.md) | 预期的通告/选择、RIB/FIB 与转发证据、故障/恢复时间线 |
| 3 | [数据中心 EVPN/VXLAN](03-datacenter-evpn.md) · [测验](../../quizzes/networking/expert/03-datacenter-evpn-quiz.md) | Underlay/overlay 映射、允许/禁止的 VRF 流量、路由和封装证据 |
| 4 | [Linux 数据包路径与性能](04-linux-performance.md) · [测验](../../quizzes/networking/expert/04-linux-performance-quiz.md) | 按时间关联的队列、计数器和数据包；测量限制与恢复 |
| 5 | [云与 CNI 设计](05-cloud-cni-design.md) · [测验](../../quizzes/networking/expert/05-cloud-cni-design-quiz.md) | 从 DNS 到后端及返回路径的设计和证据 |
| 6 | [自动化与最终评估](06-automation-capstone.md) · [测验](../../quizzes/networking/expert/06-automation-capstone-quiz.md) | 涵盖正常、禁止、失败和恢复状态的证据与变更审查 |
| 7 | [WAN 与混合连接设计](07-wan-hybrid-connectivity.md) · [测验](../../quizzes/networking/expert/07-wan-hybrid-connectivity-quiz.md) | 两个方向的预测路径、故障转移规则、链路故障时的时间与收缩项（带宽、MTU） |
| 8 | [CDN 与边缘交付设计](08-cdn-edge-delivery.md) · [测验](../../quizzes/networking/expert/08-cdn-edge-delivery-quiz.md) | 请求由何处响应（根据响应标头说明），以及只能通过 CloudFront 到达的边缘到源站路径 |
| 9 | [边缘安全：WAF 与 DDoS 防御](09-edge-security-waf-ddos.md) · [测验](../../quizzes/networking/expert/09-edge-security-waf-ddos-quiz.md) | 各攻击层在哪一环被拦截，以及采用计数模式的 WAF 规则计划和回滚触发条件 |

现有参考资料仍然有用：[协议基础](../../basics/06-network-fundamentals-part1.md)、[内核网络](../../kernel/02-network-stack.md)、[Calico BGP](../calico/04-bgp-deep-dive.md)、[Cilium](../cilium/README.md) 和 [VPC CNI](../01-vpc-cni.md)。

## 选择专攻方向 {#tracks}

| 方向 | 优先顺序 | 深入学习 |
|---|---|---|
| 云网络/SRE | 1 → 2 → 4 → 5 → 6 | 深入了解 CNI、DNS、负载均衡器和混合网络边界中的性能与故障 |
| 企业/数据中心 | 1 → 2 → 4 → 3 → 6 | 对照 Cisco 官方范围，检查剩余的 L2/L3、安全、虚拟化和自动化主题 |
| 协议/网络软件 | 1 → 2 → 4 → 6 | 在打好 C/C++ 基础后开展传输层和内核实现项目 |

第 1、2、4 章是共同的前置内容。数据中心方向需增加第 3 章，云方向需增加第 5 章。协议/Linux 方向可以使用第 4 章的主机实验，完成对应的第 6 章评估。完成所选范围内的评估后，再增加另一个专攻方向。除了阅读，也要为环境准备、失败尝试、复现和报告留出时间。

## 实验边界与所有权 {#lab-contract}

不要在一个环境中依次执行所有章节。

| 环境 | 准备工作与边界 | 完成前检查 |
|---|---|---|
| 主机观察 | 初学者课程的一次性虚拟机、已安装的工具、自有流量 | 接口/进程/抓包范围、持续时间、清理自己的文件 |
| 路由/EVPN | 独立的 Linux 实验虚拟机，以及所选 netlab/provider 的安装和镜像要求 | 上游修订版本、工具/镜像版本、自有实验 ID/资源及恢复命令 |
| 云 | 已获批准的现有实验账号/集群，以及只读权限 | 账号、区域、上下文、命名空间、资源所有者、成本/权限/验证范围 |
| 设计/提供的证据 | 明确的假设和输入证据，不一定需要拥有相应设备 | 区分设计审查与实时流量验证，并标记未观察到的项目 |

不要将 netlab/containerlab 设备的地址或名称复制到初学者虚拟机的 NIC 上。有些练习需要商用 NOS 镜像、虚拟化支持或额外的主板：**请先检查各章节和上游前置条件**。全局执行 Docker prune、拆除其他实验环境以及在生产环境注入故障，都不是本课程的默认步骤。

每次实验前都要创建以下记录。记录版本和修订信息意味着记录实际输入；这并不保证任意组合都彼此兼容。

| 记录项 | 示例形式 |
|---|---|
| 实验 ID 和所有者 | 一个便于区分的 ID，以及负责的角色 |
| 环境/权限 | 本地虚拟机、实验容器，或获批准的云只读访问权限 |
| 拓扑 | 节点、接口、地址、VRF、观察路径和管理路径 |
| 工具/输入 | 操作系统、内核、工具和镜像版本；上游提交；输入文件哈希值 |
| 流量范围 | 源、目标、协议、端口和最长持续时间 |
| 基线 | 路由、策略、服务状态和恢复配置 |
| 假设/变更 | 预期结果和唯一要更改的项目 |
| 停止/恢复标准 | 管理连接故障、意外资源、恢复及复查 |

## 选择官方资源 {#resources}

以下为截至2026年9月15日核查的学习方向。请另行确认能否访问学期课程材料、是否能够注册、是否有评分人员，以及培训安排。

| 资源 | 在本课程中的作用 | 使用前须知 |
|---|---|---|
| [Berkeley CS168](https://www.cs168.io/) | 为互联网架构、路由、传输、数据中心和项目提供学习框架 | 选择一个内容完整的公开学期，并分别检查课程说明、代码和评分内容的访问权限 |
| [BGP Labs](https://bgplabs.net/) | 循序渐进地练习 BGP 配置、策略和故障处理 | 检查[安装说明](https://bgplabs.net/install/)、实验修订版本以及 provider/镜像要求 |
| [netlab EVPN](https://netlab.tools/module/evpn/) | 设计 EVPN/VRF/IRB，并验证功能支持情况 | 确认所选设备支持所需功能和数据平面设置 |
| [Bootlin Linux Networking](https://bootlin.com/training/networking/) | 深入学习内核、驱动、用户空间和性能 | 区分公开材料与付费培训；检查 C/kernel 和主板要求 |
| [Cisco Enterprise Infrastructure](https://www.cisco.com/site/us/en/learn/training-certifications/certifications/enterprise/ccie-enterprise-infrastructure/index.html) | 检查企业设计、运维和自动化的覆盖范围 | 选择当前的官方考试大纲；FRR 无法复现所有商用设备或 ASIC 行为 |
| [AWS Advanced Networking](https://docs.aws.amazon.com/aws-certification/latest/advanced-networking-specialty-01/advanced-networking-specialty-01.html) | 为云/混合架构、实施、运维和安全提供范围参考 | 将考试准备与部署分开；明确账号、访问权限、成本和清理条件 |
| [Stanford CS144](https://online.stanford.edu/courses/cs144-introduction-computer-networking) | 可选的协议实现 C/C++ 学习方向 | 确认当前的注册情况、公开作业和代码仓库可用性 |

本仓库不提供私有课程材料或解答。请阅读项目要求，并自行完成实现、测试和设计论证。

## 解读证据 {#evidence-rules}

- **实测**：在所说明的环境、时间窗口和流量中观察到。
- **他人提供**：由他人采集；记录其来源、范围以及与原始资料的关系。
- **示例/合成**：用于说明计算或验证器的输入。不要将其报告为真实流量成功。
- **设计假设**：尚未测试的设计条件。应继续标记为未验证。

缺少观察结果时，应标记为 `unknown`。没有路由输出、没有捕获到数据包，或单独出现 `ping` 超时，都不能证明策略拒绝或端到端根因。BGP 会话已建立，也不能证明前缀符合预期或转发行为正确。

## 最终作品集 {#portfolio}

在自己的环境中串联以下交付成果：

1. 一个请求的正向与返回路径，包括观察点。
2. 正常流量以及**必须禁止的流量**的证据。
3. 一次故障或策略变更的变更前/期间/之后记录。
4. 测量条件、缺失的证据以及被排除的假设。
5. 范围明确的变更，以及恢复后的验证。
6. [最终评估](06-automation-capstone.md)的自动化结果及其人工审查限制。

请将原始证据保存在获准的位置，并在公开笔记中使用一致的别名。不要不加区分地公开原始数据包、日志、账号或拓扑清单。

**下一章：**[第 1 章：协议与实现项目](01-protocol-projects.md)
