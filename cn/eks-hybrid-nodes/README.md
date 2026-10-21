# EKS 混合节点

> **支持的版本**：当前 EKS 支持的版本；示例已针对 EKS 1.36 / nodeadm 1.0.20 进行审核
> **最后更新**：2026年10月12日

Amazon EKS 混合节点可将客户运营的本地或边缘节点连接到由 AWS 管理的 EKS 控制平面。您仍需负责运营主机、操作系统、连接和工作负载。本指南区分受支持的接口与示例配置；它并不能证明某个特定的本地生产部署已通过测试。

EKS 1.37 于2026年10月1日发布。本指南中的示例仍是根据 EKS 1.36 和 nodeadm 1.0.20 审核的。

选择版本前，请查看 [EKS 版本日历](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html)、混合节点文档以及主机/CNI 支持信息。

## 目录

1. [先决条件和系统要求](01-prerequisites.md)
2. [网络配置](02-network-configuration.md)
3. [受限互联网设置（S3 + VPC 端点）](03-airgap-setup.md)
4. [节点引导](04-node-bootstrap.md)
5. [GPU 服务器集成](05-gpu-integration.md)
6. [工作负载放置策略](06-workload-placement.md)
7. [节点生命周期管理](07-node-lifecycle.md)
8. [运维和维护](08-operations.md)
9. [裸机服务器操作系统安装和迁移指南](09-bare-metal-os-setup.md)
10. [混合节点网关](10-hybrid-nodes-gateway.md)
11. [网络隔离安全审查](11-network-separation-security.md)
12. [无需 SNAT 和 PrivateLink 的 Pod 连接](12-connectivity-validation.md)

## 什么是混合节点？

混合节点可以与普通 AWS 计算节点共用一个集群。将云主机注册为**混合**节点则是另一回事：AWS 不支持在 AWS 区域、本地区域、Outposts 或其他云中使用混合节点基础设施，而且使用 EC2 仍会产生混合节点费用。

![EKS 混合节点网络概览图，展示从本地路由器和网关到 AWS 集群 VPC 中控制平面 ENI 的连接。](../.gitbook/assets/en-eks-hybrid-nodes-highlevel-0.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-hybrid-nodes-highlevel-0.html)

下图展示了网络先决条件，包括 VPC、子网、Transit Gateway/Virtual Private Gateway，以及 Remote Node/Pod CIDR 连接。

![混合节点先决条件图，将集群的 RemoteNodeNetwork 和 RemotePodNetwork 设置与 VPC 和本地网络两侧的路由表关联起来。](../.gitbook/assets/en-eks-hybrid-nodes-prereq-0.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-hybrid-nodes-prereq-0.html)

这些图展示的是私有连接和路由，并不表示系统会自动创建每一条本地路由、防火墙规则或 AWS 服务端点。

进行安全团队审查时，请使用[网络隔离审查指南](11-network-separation-security.md)。该指南区分私有集群端点、EKS ENI 和 AWS 服务 PrivateLink 端点，并指出了 DX 上管理连接和数据边界的相关证据。

## 使用场景和数据边界

本地 GPU、大型本地数据集、边缘处理以及现有硬件都可能成为使用混合节点的理由。数据本地化要求仍需要应用程序、存储、出口流量和日志记录方面的控制。Kubernetes API 对象和控制平面元数据由 AWS 管理；仅使用节点选择器并不能确立数据主权或法规合规性。

放置工作负载时，请使用实际的混合计算标签和明确维护的组织标签，而不要假定存在名为 `on-premises` 的 AWS 区域：

```yaml
# Pod spec fragment; set organization labels through the node owner.
nodeSelector:
  eks.amazonaws.com/compute-type: hybrid
  example.com/data-location: on-premises
```

此片段不会创建标签、完整应用程序、安全边界或数据保留策略。请验证映像/运行时兼容性以及实际数据路径。

## 架构和责任归属

| 组件 | 位置 | 责任 |
|-----------|----------|----------------|
| EKS API 服务器、etcd、控制器、调度器 | AWS | AWS 管理的控制平面 |
| nodeadm | 受支持的本地 Linux 主机 | 安装/引导/升级 CLI；不是长期运行的节点代理 |
| kubelet / containerd | 本地 | 节点代理 / CRI 运行时，由主机所有者运营 |
| Cilium 或 Calico | 本地和集群 | 兼容的 CNI 配置；VPC CNI 不管理混合节点 |
| SSM Agent 或 Roles Anywhere 签名辅助程序 | 本地 | 从相应的 AWS 服务获取临时凭证 |
| SSM / IAM Roles Anywhere 服务 | AWS | 凭证服务，不能替代本地离线 CA |
| VPN / Direct Connect 和路由 | 两种环境 | 双向连接；Direct Connect 本身并不意味着加密 |

Bottlerocket 受支持的 VMware 变体使用自己的引导路径，不使用 nodeadm。对于其他受支持的主机，`nodeadm install` 会安装依赖项，`nodeadm init` 会配置/加入节点。基于 SSM 的全新安装/升级要求使用 **nodeadm 1.0.19 或更高版本**，这是由于 SSM 签名密钥发生了变化；经审核的当前版本为 **1.0.20**。

## 规划时需要考虑的限制

- **已连接环境**：必须保持与 AWS 稳定的私有双向连接。混合节点并非为断开连接/间歇性 DDIL 运行而设计。本指南中的“气隙”指限制互联网访问但仍保留所需 AWS 连接，而不是与 AWS 隔离。
- **地址**：使用 IPv4 RFC1918 或 CGNAT 地址范围，远程节点/Pod、VPC 和服务 CIDR 之间不得重叠。每个集群最多支持 **15 个节点 CIDR 和 15 个 Pod CIDR**。
- **身份验证**：使用 `API` 或 `API_AND_CONFIG_MAP`，并准备好混合节点 IAM 角色/访问条目。
- **API 端点**：AWS 建议仅使用公有端点或仅使用私有端点。两者同时启用时，VPC 外的节点会解析到公有端点地址；如果预期路径/访问规则是私有的，这**可能**导致节点无法加入。这并非对 API 的普遍性限制。即使 API 端点是公有的，也不能免除控制平面到节点之间的私有连接要求。
- **区域**：根据当前概览，除 AWS GovCloud（美国）和 AWS 中国区域外均可用。
- **主机支持**：应同时检查操作系统、架构、CNI 和内核。AL2023 适用于本地虚拟化环境，并非通用的裸机推荐方案。
- **费用**：混合节点费用按节点连接期间报告的 vCPU 小时数计算。启用超线程的裸机核心可能会报告两个 vCPU。工作负载空闲不会自动停止节点费用；集群和其他服务费用另计。

## 凭证提供程序

两种提供程序都需要访问 AWS 服务端点才能刷新凭证。本地 CA 无法让 IAM Roles Anywhere 离线签发 AWS 凭证。除非经过审核的原因要求混用，否则建议整个主机群始终使用同一种提供程序。

| 主题 | SSM 混合激活 | IAM Roles Anywhere |
|-------|------------------------|--------------------|
| 引导 | 激活 ID/代码和已准备好的信任 SSM 的角色 | PKI、每节点证书/密钥、信任锚、配置文件和角色 |
| 命名 | SSM 生成的 `mi-...` 名称 | 与证书身份绑定的自定义节点名称 |
| 会话时长 | 固定一小时，由 SSM 刷新 | 默认一小时；支持的请求/配置文件时长为 15 分钟至 12 小时，具体受有效时长和角色最大时长限制 |
| 断连 | 无法刷新；网络恢复后，重试退避可能延迟重新连接 | 无法离线获取新凭证；网络恢复时，凭证进程会按需获取凭证 |
| 规模 / 成本 | 不收取 SSM 节点注册费或每节点管理费；功能使用定价另计 | 请查看 IAM Roles Anywhere 配额和 PKI 运维要求 |
| 典型选择 | 没有现有 PKI；注册更简单 | 已有 PKI，且证书生命周期受管理 |

**价格信息核查日期：2026年9月16日**：SSM 已于2026年6月30日起取消高级实例套餐。有关 Session Manager 和 Run Command 的使用条款，请查阅[当前 SSM 定价](https://aws.amazon.com/systems-manager/pricing/)；[EKS 混合节点 vCPU 费用](https://aws.amazon.com/eks/pricing/)仍单独计算。

Roles Anywhere 配置文件必须接受自定义角色会话名称，且信任策略必须将其绑定到所选证书属性。其有效会话时长**不得超过** IAM 角色的最大时长；CreateSession API 允许两者相等。[先决条件](01-prerequisites.md)详细说明了这些契约和安全准备事项。

## 工作负载示例

1. 使用经过验证的运行时和恢复计划进行本地 GPU 训练或推理。
2. 进行本地数据处理，并单独审核 AWS 元数据/遥测/出口流量路径。
3. 在连接可靠且断连行为经过测试的情况下运行工厂/边缘应用程序。
4. 在大型现有数据集附近进行媒体处理。

## 后续步骤

请从[先决条件和系统要求](01-prerequisites.md)开始，确保您的环境已准备好使用 EKS 混合节点。

## 测验

请尝试以下测验，检验您对 EKS 混合节点的理解：

* [EKS 混合节点先决条件测验](../quizzes/eks-hybrid-nodes/01-prerequisites-quiz.md)
* [EKS 混合节点网络配置测验](../quizzes/eks-hybrid-nodes/02-network-configuration-quiz.md)
* [EKS 混合节点受限互联网设置测验](../quizzes/eks-hybrid-nodes/03-airgap-setup-quiz.md)
* [EKS 混合节点节点引导测验](../quizzes/eks-hybrid-nodes/04-node-bootstrap-quiz.md)
* [EKS 混合节点 GPU 集成测验](../quizzes/eks-hybrid-nodes/05-gpu-integration-quiz.md)
* [EKS 混合节点工作负载放置测验](../quizzes/eks-hybrid-nodes/06-workload-placement-quiz.md)
* [节点生命周期管理测验](../quizzes/eks-hybrid-nodes/07-node-lifecycle-quiz.md)
* [EKS 混合节点运维测验](../quizzes/eks-hybrid-nodes/08-operations-quiz.md)
* [裸机服务器操作系统安装和迁移测验](../quizzes/eks-hybrid-nodes/09-bare-metal-os-setup-quiz.md)
* [EKS 混合节点网关测验](../quizzes/eks-hybrid-nodes/10-hybrid-nodes-gateway-quiz.md)
* [网络隔离安全审查测验](../quizzes/eks-hybrid-nodes/11-network-separation-security-quiz.md)
* [无需 SNAT 和 PrivateLink 的 Pod 连接测验](../quizzes/eks-hybrid-nodes/12-connectivity-validation-quiz.md)

## 相关文档

* [EKS 弹性指南](../eks/10-eks-resiliency.md) - 混合环境中的高可用配置
* [EKS 成本优化](../eks/07-eks-cost-optimization.md) - 成本管理策略
* [EKS 监控和日志记录](../eks/06-eks-monitoring-logging.md) - 集成监控配置

## 官方文档

* [AWS EKS 混合节点官方文档](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-overview.html)
* [EKS Kubernetes 版本日历](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html)
* [nodeadm 用户指南](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-nodeadm.html)
* [Harbor 官方文档](https://goharbor.io/docs/)
* [NVIDIA GPU Operator 文档](https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/overview.html)
* [混合节点网络指南](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-networking.html)
* [混合节点 CNI 配置](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-cni.html)
* [混合节点故障排除](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-troubleshooting.html)

* [混合节点操作系统兼容性](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-os.html)
* [混合节点凭证和 IAM 角色](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-creds.html)
* [网络断连期间的主机凭证](https://docs.aws.amazon.com/eks/latest/best-practices/hybrid-nodes-host-creds.html)
* [IAM Roles Anywhere CreateSession 语义](https://docs.aws.amazon.com/rolesanywhere/latest/userguide/authentication-create-session.html)
* [EKS 定价](https://aws.amazon.com/eks/pricing/)
