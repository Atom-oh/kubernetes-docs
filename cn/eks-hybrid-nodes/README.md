# EKS Hybrid Nodes

> **支持的版本**：当前 EKS 支持的版本；示例已针对 EKS 1.36 / nodeadm 1.0.20 审核
> **最后更新**：September 16, 2026

Amazon EKS Hybrid Nodes 将客户运营的本地或边缘节点连接到 AWS 托管的 EKS 控制平面。您仍然负责运营主机、操作系统、连接和工作负载。本指南区分受支持的接口与示例配置；它并不证明某个特定的本地生产部署已经过测试。

## 目录

1. [前提条件和系统要求](01-prerequisites.md)
2. [网络配置](02-network-configuration.md)
3. [受限互联网设置（S3 + VPC 终端节点）](03-airgap-setup.md)
4. [节点引导](04-node-bootstrap.md)
5. [GPU 服务器集成](05-gpu-integration.md)
6. [工作负载放置策略](06-workload-placement.md)
7. [节点生命周期管理](07-node-lifecycle.md)
8. [运维和维护](08-operations.md)
9. [裸金属服务器操作系统安装和迁移指南](09-bare-metal-os-setup.md)
10. [Hybrid Nodes 网关](10-hybrid-nodes-gateway.md)
11. [网络隔离安全审查](11-network-separation-security.md)

## 什么是 Hybrid Nodes？

Hybrid Nodes 可以与普通 AWS 计算节点共享一个集群。将云计算机注册为 **hybrid** 节点则是另一回事：AWS 不支持在 AWS Regions、Local Zones、Outposts 或其他云中运行 hybrid-node 基础设施，而且 EC2 的使用仍会产生 hybrid 费用。

![从本地路由器和网关到 AWS 集群 VPC 中控制平面 ENI 的 EKS hybrid nodes 网络概览图。](../.gitbook/assets/en-eks-hybrid-nodes-highlevel-0.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-hybrid-nodes-highlevel-0.html)

下图展示了网络前提条件，包括 VPC、子网、Transit Gateway/Virtual Private Gateway，以及 Remote Node/Pod CIDR 连接。

![Hybrid nodes 前提条件图，将集群的 RemoteNodeNetwork 和 RemotePodNetwork 设置关联至 VPC 侧和本地侧的路由表。](../.gitbook/assets/en-eks-hybrid-nodes-prereq-0.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-hybrid-nodes-prereq-0.html)

这些图表说明了私有连接和路由，而不是自动创建所有本地路由、防火墙规则或 AWS 服务终端节点。

对于安全团队审查，请使用[网络隔离审查指南](11-network-separation-security.md)。该指南区分私有集群终端节点、EKS ENI 和 AWS 服务 PrivateLink 终端节点，并识别跨 DX 的管理连接和数据边界的证据。

## 使用场景和数据边界

本地 GPU、大型本地数据集、边缘处理和既有硬件都可能是使用 Hybrid Nodes 的理由。数据本地化要求仍需要应用程序、存储、出口和日志控制。Kubernetes API 对象和控制平面元数据由 AWS 管理；仅凭节点选择器并不能建立数据主权或法规合规性。

请使用实际的 hybrid 计算标签和显式维护的组织标签进行放置，不要假定存在名为 `on-premises` 的 AWS 可用区：

```yaml
# Pod spec fragment; set organization labels through the node owner.
nodeSelector:
  eks.amazonaws.com/compute-type: hybrid
  example.com/data-location: on-premises
```

此片段不会创建标签、完整的应用程序、安全边界或数据保留策略。请验证镜像/运行时兼容性和实际数据路径。

## 架构和责任归属

| 组件 | 位置 | 职责 |
|-----------|----------|----------------|
| EKS API server、etcd、controllers、scheduler | AWS | AWS 托管的控制平面 |
| nodeadm | 受支持的本地 Linux 主机 | 安装/引导/升级 CLI；不是长期运行的节点代理 |
| kubelet / containerd | 本地 | 节点代理 / CRI 运行时，由主机所有者运营 |
| Cilium 或 Calico | 本地和集群 | 兼容的 CNI 配置；VPC CNI 不管理 hybrid 节点 |
| SSM Agent 或 Roles Anywhere 签名帮助程序 | 本地 | 从相应的 AWS 服务获取临时凭证 |
| SSM / IAM Roles Anywhere 服务 | AWS | 凭证服务，不是本地离线 CA 的替代品 |
| VPN / Direct Connect 和路由 | 两种环境 | 双向连接；仅有 Direct Connect 并不意味着已加密 |

Bottlerocket 受支持的 VMware 变体使用自己的引导路径，不使用 nodeadm。对于其他受支持的主机，`nodeadm install` 安装依赖项，`nodeadm init` 配置/加入节点。由于 SSM 签名密钥变更，基于 SSM 的新安装/升级需要 **nodeadm 1.0.19 或更高版本**；经审核的当前版本为 **1.0.20**。

## 需要规划的约束

- **已连接环境：**需要到 AWS 的可靠私有双向连接。Hybrid Nodes 不适用于断开连接/间歇性 DDIL 运行。本指南中的“Air-gap”是指在保持所需 AWS 连接的情况下限制互联网访问，而不是与 AWS 隔离。
- **地址：**IPv4 RFC1918 或 CGNAT 范围，且远程节点/Pod、VPC 和服务 CIDR 之间不得重叠。每个集群最多支持 **15 个节点 CIDR 和 15 个 Pod CIDR**。
- **身份验证：**使用 `API` 或 `API_AND_CONFIG_MAP`，并准备 Hybrid Nodes IAM 角色/访问条目。
- **API 终端节点：**AWS 建议仅使用公有或仅使用私有。两者都启用时，VPC 外的节点会解析公有终端节点地址；如果预期路径/访问规则是私有的，这**可能**会阻止加入。这并非通用的 API 禁止规则。即使使用公有 API 终端节点，也不会消除控制平面到节点的私有连接要求。
- **区域：**根据当前概览，除 AWS GovCloud (US) 和 AWS China Regions 外均可用。
- **主机支持：**请一并审核操作系统、架构、CNI 和内核。AL2023 适用于本地虚拟化环境，并非通用的裸金属建议。
- **费用：**节点连接期间，hybrid 费用按报告的 vCPU 小时计算。启用超线程的裸金属核心可能报告为两个 vCPU。空闲工作负载不会自动停止节点费用；集群费用和其他服务费用另计。

## 凭证提供程序

两种提供程序都需要访问 AWS 服务终端节点以刷新凭证。本地 CA 不能让 IAM Roles Anywhere 离线签发 AWS 凭证。除非有经过审核的混用理由，否则应在整个节点群中一致地使用一种提供程序。

| 主题 | SSM hybrid activations | IAM Roles Anywhere |
|-------|------------------------|--------------------|
| 引导 | Activation ID/code 和已准备的信任 SSM 的角色 | PKI、每节点证书/密钥、信任锚点、profile 和角色 |
| 命名 | SSM 生成的 `mi-...` 名称 | 绑定到证书身份的自定义节点名称 |
| 会话时长 | 固定为一小时，由 SSM 刷新 | 默认一小时；支持的请求/profile 时长为 15 分钟–12 小时，受有效时长和角色最大值约束 |
| 断开连接 | 无法刷新；网络恢复后，重试退避可能延迟重新连接 | 无法离线获取新凭证；连接恢复后，credential-process 会按需获取凭证 |
| 规模/成本 | 不收取 SSM 节点注册或每节点管理费用；功能使用定价另计 | 请审核 IAM Roles Anywhere 配额和 PKI 运维要求 |
| 典型选择 | 没有现有 PKI；注册更简单 | 具有现有 PKI 和受管理的证书生命周期 |

**已于 September 16, 2026 核查定价：**SSM 已于 June 30, 2026 取消 Advanced Instances Tier。请查阅[当前 SSM 定价](https://aws.amazon.com/systems-manager/pricing/)以了解 Session Manager 和 Run Command 的使用条款；[EKS Hybrid Nodes vCPU 费用](https://aws.amazon.com/eks/pricing/)另行计算。

Roles Anywhere profile 必须接受自定义角色会话名称，并且信任策略必须将其绑定到所选证书属性。其有效会话时长必须**不超过** IAM 角色最大值；CreateSession API 允许两者相等。[前提条件](01-prerequisites.md)详细说明了这些契约和安全准备。

## 示例工作负载

1. 具有经过验证的运行时和恢复计划的本地 GPU 训练或推理。
2. 对 AWS 元数据/遥测/出口路径进行单独审核的本地数据处理。
3. 具有可靠连接和经过测试的断开连接行为的工厂/边缘应用程序。
4. 靠近现有大型数据集的媒体处理。

## 后续步骤

首先阅读[前提条件和系统要求](01-prerequisites.md)，以确保您的环境已准备好使用 EKS Hybrid Nodes。

## 测验

要测试您对 EKS Hybrid Nodes 的理解，请尝试以下测验：

* [EKS Hybrid Nodes 前提条件测验](../quizzes/eks-hybrid-nodes/01-prerequisites-quiz.md)
* [EKS Hybrid Nodes 网络配置测验](../quizzes/eks-hybrid-nodes/02-network-configuration-quiz.md)
* [EKS Hybrid Nodes 受限互联网设置测验](../quizzes/eks-hybrid-nodes/03-airgap-setup-quiz.md)
* [EKS Hybrid Nodes 节点引导测验](../quizzes/eks-hybrid-nodes/04-node-bootstrap-quiz.md)
* [EKS Hybrid Nodes GPU 集成测验](../quizzes/eks-hybrid-nodes/05-gpu-integration-quiz.md)
* [EKS Hybrid Nodes 工作负载放置测验](../quizzes/eks-hybrid-nodes/06-workload-placement-quiz.md)
* [节点生命周期管理测验](../quizzes/eks-hybrid-nodes/07-node-lifecycle-quiz.md)
* [EKS Hybrid Nodes 运维测验](../quizzes/eks-hybrid-nodes/08-operations-quiz.md)
* [裸金属服务器操作系统安装和迁移测验](../quizzes/eks-hybrid-nodes/09-bare-metal-os-setup-quiz.md)
* [EKS Hybrid Nodes 网关测验](../quizzes/eks-hybrid-nodes/10-hybrid-nodes-gateway-quiz.md)
* [网络隔离安全审查测验](../quizzes/eks-hybrid-nodes/11-network-separation-security-quiz.md)

## 相关文档

* [EKS 弹性指南](../eks/10-eks-resiliency.md) - 混合环境中的高可用性配置
* [EKS 成本优化](../eks/07-eks-cost-optimization.md) - 成本管理策略
* [EKS 监控和日志记录](../eks/06-eks-monitoring-logging.md) - 集成监控配置

## 官方文档

* [AWS EKS Hybrid Nodes 官方文档](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-overview.html)
* [nodeadm 用户指南](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-nodeadm.html)
* [Harbor 官方文档](https://goharbor.io/docs/)
* [NVIDIA GPU Operator 文档](https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/overview.html)
* [Hybrid Nodes 网络指南](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-networking.html)
* [Hybrid Nodes CNI 配置](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-cni.html)
* [Hybrid Nodes 故障排除](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-troubleshooting.html)

* [Hybrid 操作系统兼容性](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-os.html)
* [Hybrid 凭证和 IAM 角色](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-creds.html)
* [网络断开期间的主机凭证](https://docs.aws.amazon.com/eks/latest/best-practices/hybrid-nodes-host-creds.html)
* [IAM Roles Anywhere CreateSession 语义](https://docs.aws.amazon.com/rolesanywhere/latest/userguide/authentication-create-session.html)
* [EKS 定价](https://aws.amazon.com/eks/pricing/)
