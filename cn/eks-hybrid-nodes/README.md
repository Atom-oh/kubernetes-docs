# EKS Hybrid Nodes

> **支持的版本**: 当前由 EKS 支持的版本；示例已针对 EKS 1.36 / nodeadm 1.0.20 审核
> **最后更新**: October 12, 2026

Amazon EKS Hybrid Nodes 将客户运营的本地或边缘Node连接到由 AWS 管理的 EKS control plane。您将继续运营主机、操作系统、连接和工作负载。本指南区分受支持的接口与示例配置；它并非特定本地生产部署已经过测试的证据。

EKS 1.37 于 2026 年 10 月 1 日发布。本指南中的示例仍针对 EKS 1.36 和 nodeadm 1.0.20 审核。

在选择版本前，请查看 [EKS version calendar](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html)、Hybrid Nodes 文档以及主机/CNI 支持信息。

## 目录

1. [前提条件和系统要求](01-prerequisites.md)
2. [网络配置](02-network-configuration.md)
3. [受限互联网设置（S3 + VPC Endpoints）](03-airgap-setup.md)
4. [Node引导](04-node-bootstrap.md)
5. [GPU 服务器集成](05-gpu-integration.md)
6. [工作负载放置策略](06-workload-placement.md)
7. [Node生命周期管理](07-node-lifecycle.md)
8. [运维和维护](08-operations.md)
9. [裸金属服务器 OS 安装和迁移指南](09-bare-metal-os-setup.md)
10. [Hybrid Nodes Gateway](10-hybrid-nodes-gateway.md)
11. [网络隔离安全审查](11-network-separation-security.md)

## 什么是 Hybrid Nodes？

Hybrid Nodes 可以与普通 AWS compute Node共享一个集群。将云机器注册为 **hybrid** Node则是另一回事：AWS 不支持在 AWS Regions、Local Zones、Outposts 或其他云中部署 hybrid-node 基础设施，并且使用 EC2 仍会产生 hybrid 费用。

![EKS hybrid Node网络概览图，从本地路由器和网关延伸至 AWS 集群 VPC 中的 control plane ENI。](../.gitbook/assets/en-eks-hybrid-nodes-highlevel-0.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-hybrid-nodes-highlevel-0.html)

下图展示了网络前提条件，包括 VPC、子网、Transit Gateway/Virtual Private Gateway，以及 Remote Node/Pod CIDR 连通性。

![Hybrid Node前提条件图，将集群的 RemoteNodeNetwork 和 RemotePodNetwork 设置关联到 VPC 端和本地端的路由表。](../.gitbook/assets/en-eks-hybrid-nodes-prereq-0.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-hybrid-nodes-prereq-0.html)

这些图表说明了私有连接和路由，而非自动创建每一条本地路由、防火墙规则或 AWS service endpoint。

对于安全团队审查，请使用[网络隔离审查指南](11-network-separation-security.md)。该指南区分私有 cluster endpoint、EKS ENI 和 AWS service PrivateLink endpoint，并识别跨 DX 的管理连接和数据边界的证据。

## 使用场景和数据边界

本地 GPU、大型本地数据集、边缘处理和现有硬件都可能是使用 Hybrid Nodes 的理由。数据本地性要求仍需要应用、存储、出口和日志控制。Kubernetes API 对象和 control-plane 元数据在 AWS 中管理；仅凭 node selector 并不能建立数据主权或合规性。

请使用实际的 hybrid compute label 和显式维护的组织 label 来进行放置，而非假设存在名为 `on-premises` 的 AWS zone：

```yaml
# Pod spec fragment; set organization labels through the node owner.
nodeSelector:
  eks.amazonaws.com/compute-type: hybrid
  example.com/data-location: on-premises
```

此片段不会创建 label、完整应用、安全边界或数据保留策略。请验证 image/runtime 兼容性和实际数据路径。

## 架构和职责归属

| 组件 | 位置 | 职责 |
|-----------|----------|----------------|
| EKS API server、etcd、controllers、scheduler | AWS | 由 AWS 管理的 control plane |
| nodeadm | 受支持的本地 Linux 主机 | 安装/引导/升级 CLI；不是长期运行的Node代理 |
| kubelet / containerd | 本地 | Node代理 / CRI runtime，由主机所有者运营 |
| Cilium 或 Calico | 本地和集群 | 兼容的 CNI 配置；VPC CNI 不管理 hybrid Node |
| SSM Agent 或 Roles Anywhere signing helper | 本地 | 从相应的 AWS service 获取临时凭证 |
| SSM / IAM Roles Anywhere service | AWS | 凭证服务，不是本地离线 CA 的替代品 |
| VPN / Direct Connect 和路由 | 两种环境 | 双向连接；仅有 Direct Connect 并不意味着加密 |

Bottlerocket 支持的 VMware 变体使用其自身的引导路径，并且不使用 nodeadm。对于其他受支持的主机，`nodeadm install` 安装依赖项，而 `nodeadm init` 配置/加入Node。基于 SSM 的新安装/升级要求使用 **nodeadm 1.0.19 或更高版本**，原因是 SSM signing-key 发生变更；经审核的当前版本为 **1.0.20**。

## 需要规划的约束

- **已连接环境：**需要与 AWS 建立可靠的私有双向连接。Hybrid Nodes 并非用于断开连接/间歇性 DDIL 操作。本指南中的“Air-gap”是指具备所需 AWS 连接的受限互联网访问，而非与 AWS 隔离。
- **地址：**IPv4 RFC1918 或 CGNAT 范围，且 remote node/Pod、VPC 和 service CIDR 之间不得重叠。每个集群最多支持 **15 个 node CIDR 和 15 个 Pod CIDR**。
- **身份验证：**使用 `API` 或 `API_AND_CONFIG_MAP`，并准备 Hybrid Nodes IAM role/access entries。
- **API endpoint：**AWS 建议仅使用 public 或仅使用 private。两者均启用时，VPC 外的Node会解析 public endpoint 地址；如果预期路径/访问规则为 private，**可能**会阻止加入。这并不是普遍的 API 禁止。即使是 public API endpoint，也不能免除从 control-plane 到Node的私有连接要求。
- **Regions：**根据当前概览，除 AWS GovCloud (US) 和 AWS China Regions 外均可用。
- **主机支持：**请一并审查 OS、架构、CNI 和 kernel。AL2023 适用于本地虚拟化环境，而非通用的裸金属建议。
- **费用：**Node连接期间，hybrid 费用按报告的 vCPU-hours 计算。启用超线程的裸金属 cores 可能报告为两个 vCPU。空闲工作负载不会自动停止Node费用；集群和其他服务费用另行计算。

## 凭证提供商 {#credential-providers}

两种提供商都需要访问 AWS service endpoints 才能刷新凭证。本地 CA 不能让 IAM Roles Anywhere 离线签发 AWS 凭证。除非已有经过审核的混用理由，否则应在整个Node群中始终使用一种提供商。

| 主题 | SSM hybrid activations | IAM Roles Anywhere |
|-------|------------------------|--------------------|
| 引导 | Activation ID/code 和已准备好信任 SSM 的 role | PKI、每Node certificate/key、trust anchor、profile 和 role |
| 命名 | SSM 生成的 `mi-...` 名称 | 绑定到 certificate identity 的自定义Node名称 |
| Session 持续时间 | 固定一小时，由 SSM 刷新 | 默认一小时；支持请求/profile 持续时间为 15 分钟至 12 小时，但受有效持续时间和 role maximum 限制 |
| 断开连接 | 无法刷新；网络恢复后，retry backoff 可能延迟重新连接 | 无法离线获取新凭证；连接恢复时，credential-process 会按需获取凭证 |
| 规模 / 成本 | 无 SSM Node注册或每Node管理费用；功能使用定价另计 | 审查 IAM Roles Anywhere quotas 和 PKI 运营要求 |
| 典型选择 | 没有现有 PKI；注册更简单 | 具有现有 PKI 和受管理的 certificate 生命周期 |

**定价检查日期为 2026 年 9 月 16 日：**SSM 自 2026 年 6 月 30 日起取消了 Advanced Instances Tier。请查阅 [当前 SSM 定价](https://aws.amazon.com/systems-manager/pricing/)以了解 Session Manager 和 Run Command 的使用条款；[EKS Hybrid Nodes vCPU 费用](https://aws.amazon.com/eks/pricing/)仍另行计算。

Roles Anywhere profile 必须接受自定义 role session name，并且 trust policy 必须将其绑定到所选的 certificate attribute。其有效 session duration 必须**不超过** IAM role maximum；CreateSession API 允许二者相等。[前提条件](01-prerequisites.md)详细说明了这些约定和安全准备。

## 示例工作负载

1. 具有经过验证的 runtime 和恢复计划的本地 GPU 训练或推理。
2. 已单独审查 AWS metadata/telemetry/egress 路径的本地数据处理。
3. 具有可靠连接和经过测试的断开连接行为的工厂/边缘应用程序。
4. 在大型现有数据集附近进行媒体处理。

## 后续步骤

从[前提条件和系统要求](01-prerequisites.md)开始，以确保您的环境已准备好使用 EKS Hybrid Nodes。

## 测验

若要测试您对 EKS Hybrid Nodes 的理解，请尝试以下测验：

* [EKS Hybrid Nodes 前提条件测验](../quizzes/eks-hybrid-nodes/01-prerequisites-quiz.md)
* [EKS Hybrid Nodes 网络配置测验](../quizzes/eks-hybrid-nodes/02-network-configuration-quiz.md)
* [EKS Hybrid Nodes 受限互联网设置测验](../quizzes/eks-hybrid-nodes/03-airgap-setup-quiz.md)
* [EKS Hybrid Nodes Node引导测验](../quizzes/eks-hybrid-nodes/04-node-bootstrap-quiz.md)
* [EKS Hybrid Nodes GPU 集成测验](../quizzes/eks-hybrid-nodes/05-gpu-integration-quiz.md)
* [EKS Hybrid Nodes 工作负载放置测验](../quizzes/eks-hybrid-nodes/06-workload-placement-quiz.md)
* [Node生命周期管理测验](../quizzes/eks-hybrid-nodes/07-node-lifecycle-quiz.md)
* [EKS Hybrid Nodes 运维测验](../quizzes/eks-hybrid-nodes/08-operations-quiz.md)
* [裸金属服务器 OS 安装和迁移测验](../quizzes/eks-hybrid-nodes/09-bare-metal-os-setup-quiz.md)
* [EKS Hybrid Nodes Gateway 测验](../quizzes/eks-hybrid-nodes/10-hybrid-nodes-gateway-quiz.md)
* [网络隔离安全审查测验](../quizzes/eks-hybrid-nodes/11-network-separation-security-quiz.md)

## 相关文档

* [EKS 弹性指南](../eks/10-eks-resiliency.md) - 混合环境中的高可用性配置
* [EKS 成本优化](../eks/07-eks-cost-optimization.md) - 成本管理策略
* [EKS 监控和日志记录](../eks/06-eks-monitoring-logging.md) - 集成监控配置

## 官方文档

* [AWS EKS Hybrid Nodes 官方文档](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-overview.html)
* [EKS Kubernetes 版本日历](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html)
* [nodeadm 用户指南](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-nodeadm.html)
* [Harbor 官方文档](https://goharbor.io/docs/)
* [NVIDIA GPU Operator 文档](https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/overview.html)
* [Hybrid Nodes 网络指南](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-networking.html)
* [Hybrid Nodes CNI 配置](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-cni.html)
* [Hybrid Nodes 故障排除](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-troubleshooting.html)

* [Hybrid 操作系统兼容性](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-os.html)
* [Hybrid 凭证和 IAM role](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-creds.html)
* [网络断开期间的主机凭证](https://docs.aws.amazon.com/eks/latest/best-practices/hybrid-nodes-host-creds.html)
* [IAM Roles Anywhere CreateSession 语义](https://docs.aws.amazon.com/rolesanywhere/latest/userguide/authentication-create-session.html)
* [EKS 定价](https://aws.amazon.com/eks/pricing/)