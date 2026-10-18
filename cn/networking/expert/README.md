# 高级网络学习路径

> **资源检查日期**：2026 年 9 月 15 日
>
> **实验环境**：用于主机实验的一次性 Ubuntu Server 24.04 LTS 或 Rocky Linux 9 虚拟机。路由 / EVPN 工具和云环境有各自独立的章节前置要求。

这些进阶练习册承接[初学者课程](../beginner/README.md)。先将协议原理与代码、数据包联系起来，再根据证据评估路由策略、Linux 性能和云网络设计。

高级学习目标是：**明确预期状态，通过观测验证假设，并说明变更的影响和恢复方法**。固定的学习时长或单独一项认证都不能保证掌握这些能力。

## 入门检查 {#entry-check}

达到以下要求后再进入第 1 章：能够解释并复现以下内容：

- 区分 IP、子网、网关和 DNS 的作用，以及 MAC / ARP 的作用。
- 阅读 `ip route get`、`ss` 和有时长上限的 `tcpdump` 抓包，并指出观测点。
- 验证 SSH 密钥访问和实验防火墙策略，然后恢复原有状态。
- 区分 HTTP 错误、连接失败和名称解析失败。
- 分开管理路径和实验路径，并能识别自己拥有的文件、虚拟机和容器。

使用[初学者综合实践](../beginner/08-container-cloud-capstone.md)复习尚未掌握的内容。如果主机上缺少所需命令，请完成[来宾系统工具准备](../beginner/README.md#guest-tools)。

## 六个练习册 {#course-map}

每章都遵循 **阅读 → 实验或设计验证 → 证据 → 解释型测验**。外部课程提供阅读范围；本练习册提供自我评估的方法。

| 顺序 | 练习册 | 交付成果 |
|---|---|---|
| 1 | [协议与实现项目](01-protocol-projects.md) · [测验](../../quizzes/networking/expert/01-protocol-projects-quiz.md) | 请求路径、探测 / 响应关联、协议边界和边缘情况 |
| 2 | [路由策略与收敛](02-routing-policy-convergence.md) · [测验](../../quizzes/networking/expert/02-routing-policy-convergence-quiz.md) | 预期通告 / 选路、RIB / FIB 和转发证据、故障 / 恢复时间线 |
| 3 | [数据中心 EVPN/VXLAN](03-datacenter-evpn.md) · [测验](../../quizzes/networking/expert/03-datacenter-evpn-quiz.md) | Underlay / overlay 映射、允许 / 禁止的 VRF 流量、路由和封装证据 |
| 4 | [Linux 数据包路径与性能](04-linux-performance.md) · [测验](../../quizzes/networking/expert/04-linux-performance-quiz.md) | 按时间关联的队列、计数器和数据包；测量限制和恢复 |
| 5 | [云与 CNI 设计](05-cloud-cni-design.md) · [测验](../../quizzes/networking/expert/05-cloud-cni-design-quiz.md) | 从 DNS 到后端和返回路径的设计及证据 |
| 6 | [自动化与最终评估](06-automation-capstone.md) · [测验](../../quizzes/networking/expert/06-automation-capstone-quiz.md) | 覆盖正常、禁止、失败和恢复状态的证据及变更审查 |

以下现有参考资料仍然有用：[协议基础](../../basics/06-network-fundamentals-part1.md)、[内核网络](../../kernel/02-network-stack.md)、[Calico BGP](../calico/04-bgp-deep-dive.md)、[Cilium](../cilium/README.md) 和 [VPC CNI](../01-vpc-cni.md)。

## 选择专业方向 {#tracks}

| 方向 | 优先顺序 | 进一步深入 |
|---|---|---|
| 云网络 / SRE | 1 → 2 → 4 → 5 → 6 | 分析 CNI、DNS、负载均衡器和混合网络边界中的性能与故障 |
| 企业 / 数据中心 | 1 → 2 → 4 → 3 → 6 | 对照 Cisco 官方范围检查尚未涵盖的 L2 / L3、安全、虚拟化和自动化主题 |
| 协议 / 网络软件 | 1 → 2 → 4 → 6 | 具备 C / C++ 基础后，开展传输层和内核实现项目 |

第 1、2、4 章是共同前置内容。选择数据中心方向时增加第 3 章，选择云方向时增加第 5 章。协议 / Linux 方向可以使用第 4 章中的主机实验完成相应的第 6 章评估。在选定范围内完成评估后，可以再增加一个专业方向。除了阅读，也要为环境准备、失败尝试、复现和报告留出时间。

## 实验边界与归属 {#lab-contract}

不要在同一个环境中按顺序执行所有章节。

| 环境 | 准备工作与边界 | 完成前检查 |
|---|---|---|
| 主机观测 | 使用初学者课程的一次性虚拟机、已安装工具，以及你自己的流量 | 接口 / 进程 / 抓包范围、时长，以及你创建文件的清理情况 |
| 路由 / EVPN | 使用独立 Linux 实验虚拟机，并按需安装 netlab / provider 和镜像 | 上游版本、工具 / 镜像版本、自己拥有的实验 ID / 资源和恢复命令 |
| 云 | 使用经批准的现有实验账户 / 集群和只读权限 | 账户、区域、上下文、命名空间、资源归属方、成本 / 权限 / 验证范围 |
| 设计 / 提供的证据 | 记录假设和输入证据；不一定要有实际设备 | 区分设计审查与实时流量验证，并标明未观测项目 |

不要把 netlab / containerlab 设备的地址或名称复制到初学者虚拟机的网卡上。有些练习需要商业 NOS 镜像、虚拟化支持或额外硬件：**请先检查各章和上游前置要求**。全局 Docker prune、清理其他实验环境，以及向生产环境注入故障，都不是本课程的默认步骤。

每次实验前都要创建以下记录。记录版本和修订号意味着采集真实输入，并不保证任意组合都相互兼容。

| 记录项 | 示例形式 |
|---|---|
| 实验 ID 和负责人 | 可供识别的 ID，以及负责角色 |
| 环境 / 权限 | 本地虚拟机、实验容器，或经批准的云只读访问 |
| 拓扑 | 节点、接口、地址、VRF、观测路径和管理路径 |
| 工具 / 输入 | 操作系统、内核、工具和镜像版本；上游提交；输入文件哈希 |
| 流量范围 | 源、目标、协议、端口和最长持续时间 |
| 基线 | 路由、策略、服务状态和恢复配置 |
| 假设 / 变更 | 预期结果，以及要更改的单一项目 |
| 停止 / 恢复条件 | 管理连接故障、意外资源、恢复操作和复核步骤 |

## 选择官方资源 {#resources}

以下是截至 2026 年 9 月 15 日确认的学习方向。请分别确认学期课程材料、注册、评分器和培训安排是否可用。

| 资源 | 在本课程中的作用 | 使用前检查 |
|---|---|---|
| [Berkeley CS168](https://www.cs168.io/) | 互联网架构、路由、传输、数据中心和项目的学习框架 | 选择内容完整的公开学期，并分别检查课程介绍、代码和评分材料是否可访问 |
| [BGP Labs](https://bgplabs.net/) | 循序渐进地练习 BGP 配置、策略和故障处理 | 检查[安装说明](https://bgplabs.net/install/)、实验版本和 provider / 镜像要求 |
| [netlab EVPN](https://netlab.tools/module/evpn/) | EVPN / VRF / IRB 设计和功能支持验证 | 确认所选设备支持所需功能和数据平面配置 |
| [Bootlin Linux Networking](https://bootlin.com/training/networking/) | 深入学习内核、驱动、用户空间和性能 | 区分公开资料和付费培训；检查 C / 内核基础和开发板要求 |
| [Cisco Enterprise Infrastructure](https://www.cisco.com/site/us/en/learn/training-certifications/certifications/enterprise/ccie-enterprise-infrastructure/index.html) | 核对企业级设计、运维和自动化范围 | 选择当前官方蓝图；FRR 无法复现所有商业设备或 ASIC 行为 |
| [AWS Advanced Networking](https://docs.aws.amazon.com/aws-certification/latest/advanced-networking-specialty-01/advanced-networking-specialty-01.html) | 云 / 混合网络设计、实施、运维和安全的学习范围 | 将考试准备与实际部署区分开；明确账户、访问、成本和清理条件 |
| [Stanford CS144](https://online.stanford.edu/courses/cs144-introduction-computer-networking) | 可选的 C / C++ 协议实现方向 | 核实当前注册、公开作业和代码仓库是否可用 |

本仓库不提供私有课程材料或解答。请阅读项目要求，自行完成实现、测试和设计论证。

## 解读证据 {#evidence-rules}

- **实测**：在所述环境、时间窗口和流量条件下观测到的结果。
- **他人提供**：由其他人采集；记录来源、范围及其与原始材料的关系。
- **示例 / 合成数据**：用于解释计算方法或验证工具的输入。不要将其报告为真实流量成功通过。
- **设计假设**：尚未测试的设计条件。标记为未验证。

没有观测到的内容应标记为 `unknown`。路由输出为空、没有抓到数据包或单独出现 `ping` 超时，都不足以证明策略拒绝了流量，也不足以定位端到端根因。BGP 会话已建立，也不能证明通告了预期前缀或转发行为正确。

## 最终作品集 {#portfolio}

在你自己的环境中关联以下交付成果：

1. 一个请求的正向和返回路径，包括观测点。
2. 正常流量和**必须禁止的流量**的证据。
3. 一次故障或策略变更的变更前 / 期间 / 变更后记录。
4. 测量条件、缺失证据和被排除的假设。
5. 一项范围明确的变更，以及恢复后的验证。
6. [最终评估](06-automation-capstone.md)自动化结果及其人工审查的局限。

在获准的位置保留原始证据，并在公开笔记中使用一致的别名。不要不加甄别地公开原始数据包、日志、账户或拓扑清单。

**下一步：**[第 1 章：协议与实现项目](01-protocol-projects.md)
