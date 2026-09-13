# EKS Hybrid Nodes

> **支持的版本**: EKS 1.31+, nodeadm 0.1+ **最后更新**: February 23, 2026

Amazon EKS Hybrid Nodes 是一项功能，可让您通过 AWS EKS 控制平面管理本地服务器。本指南介绍 EKS Hybrid Nodes 在生产环境中的概念、配置方法和实际使用方式。

## 目录

1. [前提条件和系统要求](01-prerequisites.md)
2. [网络配置](02-network-configuration.md)
3. [隔离网络环境设置（S3 + VPC Endpoints）](03-airgap-setup.md)
4. [节点引导](04-node-bootstrap.md)
5. [GPU 服务器集成](05-gpu-integration.md)
6. [工作负载放置策略](06-workload-placement.md)
7. [节点生命周期管理](07-node-lifecycle.md)
8. [运维](08-operations.md)
9. [裸金属服务器 OS 安装和迁移指南](09-bare-metal-os-setup.md)
10. [Hybrid Nodes Gateway](10-hybrid-nodes-gateway.md)

## 什么是 Hybrid Nodes？

EKS Hybrid Nodes 是一项功能，可让您将本地数据中心或边缘环境中的服务器注册为由 AWS EKS 控制平面管理的 Kubernetes 节点。这样，您便可将云端和本地基础设施作为单个 Kubernetes 集群进行管理。

![EKS hybrid nodes 网络概览图，展示从本地路由器和网关到 AWS 集群 VPC 中控制平面 ENI 的连接。](../.gitbook/assets/en-eks-hybrid-nodes-highlevel-0.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-hybrid-nodes-highlevel-0.html)

下图展示了网络前提条件，包括 VPC、子网、Transit Gateway/Virtual Private Gateway 以及 Remote Node/Pod CIDR 连接。

![Hybrid nodes 前提条件图，将集群的 RemoteNodeNetwork 和 RemotePodNetwork 设置与 VPC 端和本地端的路由表关联起来。](../.gitbook/assets/en-eks-hybrid-nodes-prereq-0.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-hybrid-nodes-prereq-0.html)

## 为什么使用 Hybrid Nodes？

### 1. 法规合规性和数据主权

某些行业（金融、医疗保健、政府）受法规要求，数据必须保留在特定区域或设施内。借助 Hybrid Nodes，您可以将敏感数据保留在本地，同时利用 EKS 管理功能。

```yaml
# Example of regulatory compliance workload placement
apiVersion: v1
kind: Pod
metadata:
  name: financial-data-processor
spec:
  nodeSelector:
    topology.kubernetes.io/zone: "on-premises"
    compliance.company.io/data-sovereignty: "required"
  containers:
  - name: processor
    image: harbor.internal.company.io/finance/data-processor:v1.2.0
```

### 2. 数据引力

当大型数据集位于本地时，将计算资源靠近数据比将数据迁移到云端更高效。

### 3. 利用现有硬件

您可以继续使用已投资的高性能服务器（尤其是 GPU 服务器），同时采用基于 Kubernetes 的现代工作负载管理方式。

### 4. 统一管理

从单一控制平面管理云端和本地环境中的 Kubernetes 工作负载，可降低运维复杂性。

## 架构组件

EKS Hybrid Nodes 架构由以下组件构成：

| 组件                       | 位置       | 角色                                            |
| ------------------------------- | ----------- | ----------------------------------------------- |
| EKS Control Plane               | AWS         | API server、etcd、controller manager、scheduler |
| nodeadm                         | 本地        | 节点引导和管理代理                              |
| kubelet                         | 本地        | Pod 执行和节点状态报告                          |
| containerd                      | 本地        | 容器运行时                                      |
| VPN/Direct Connect              | 网络        | AWS 与本地之间的安全连接                        |
| SSM Agent or IAM Roles Anywhere | 本地        | 凭证管理                                        |

### 关键约束和限制

* **网络连接**：需要通过 VPN 或 Direct Connect 建立可靠的本地到 AWS 连接（不适用于断开、间歇、受限或被拒绝的环境）
* **CIDR 限制**：每个集群的 Remote Node Networks 和 Remote Pod Networks 最多可使用 15 个 CIDR
* **仅支持 IPv4**：必须使用 IPv4 地址族（混合节点不支持 IPv6）
* **身份验证模式**：集群必须使用 `API` 或 `API_AND_CONFIG_MAP` 身份验证模式
* **端点访问**：必须仅使用 Public 或 Private（**不支持**“Public and Private”——会导致混合节点加入失败）
* **按 vCPU 计费**：混合节点按 vCPU 按小时计费（无最低承诺）
* **云基础设施**：不支持在云基础设施上运行（在 EC2 上运行会产生混合节点费用）
* **VPC CNI**：Amazon VPC CNI 与混合节点不兼容；请使用 Cilium 或 Calico

### 凭证提供程序选项

EKS Hybrid Nodes 支持两种凭证提供程序，用于向 AWS 验证本地节点的身份：

| 功能                  | SSM Hybrid Activations                                                           | IAM Roles Anywhere                                     |
| ------------------------ | -------------------------------------------------------------------------------- | ------------------------------------------------------ |
| **设置复杂度**     | 简单 — 激活代码/ID 对                                                 | 中等 — 需要 PKI 基础设施                 |
| **需要证书** | 否                                                                               | 是（每个节点一个 X.509 证书）                       |
| **兼容隔离网络**   | 否（需要访问 SSM 端点）                                                | 是（可与本地 CA 配合使用）                              |
| **凭证轮换**  | 自动（由 AWS 管理，1 小时 TTL 固定）                                        | 自动（基于证书，可配置为 1-12 小时） |
| **节点命名**          | 自动生成（`mi-xxxx`，不可自定义）                                     | 自定义（必须与证书 CN 匹配）                     |
| **扩展限制**       | 每个账户每个区域免费 1,000 个；更多需要 advanced-instances 层级（额外费用） | 无限制                                              |
| **AWS 依赖项**       | SSM 服务                                                                      | IAM Roles Anywhere 服务                             |
| **最适用场景**             | 具有互联网/VPN 的标准环境                                          | 隔离网络、严格合规性、现有 PKI               |

> **建议**：在大多数环境中，为了简便起见，请使用 SSM Hybrid Activations。当您需要隔离网络支持或已有 PKI 基础设施时，请选择 IAM Roles Anywhere。

## 主要使用场景

1. **AI/ML 工作负载**：在本地 GPU 服务器上训练模型，在云端提供推理服务
2. **金融服务**：在本地处理交易数据，在云端进行分析
3. **制造业**：将工厂中的边缘计算与中央云端集成
4. **媒体处理**：处理数据所在地的大型媒体文件

## 后续步骤

请从 [前提条件和系统要求](01-prerequisites.md) 开始，确保您的环境已准备好使用 EKS Hybrid Nodes。

## 测验

要测试您对 EKS Hybrid Nodes 的理解，请尝试以下测验：

* [EKS Hybrid Nodes 测验](https://github.com/Atom-oh/kubernetes-docs/blob/main/en/quizzes/eks-hybrid-nodes/README.md)

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
