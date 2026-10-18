# EKS 集成测验

> **相关文档**：[EKS 集成](../../../networking/calico/08-eks-integration.md)
> **最后更新**：2026 年 9 月 12 日

## 测验

1. 本指南中，在普通 Linux EC2 上使用 VPC CNI 与 Calico 时，二者如何分工？
   - A) VPC CNI 执行策略，Calico 分配 VPC IP
   - B) VPC CNI 负责 Pod 网络，Calico 执行网络策略
   - C) 两个 CNI 各自配置所有 Pod 接口
   - D) Calico 取代 AWS 管理的 EKS 控制平面

<details>
<summary>显示答案</summary>

**答案：B) VPC CNI 负责 Pod 网络，Calico 执行网络策略**

VPC CNI 管理 ENI、Pod IP 分配和网络连通性；Calico 配置策略规则。本指南继续使用 Iptables 和 kube-proxy。选择其他数据平面需要单独规划。

</details>

2. 以下哪项准确描述了在 EKS 上安装 Calico？
   - A) 启用 VPC CNI 网络策略就会安装 Calico
   - B) 可通过清单或 Helm chart 安装固定版本的 Tigera Operator
   - C) 每个 EKS 集群都有 AWS 支持的 calico 附加组件
   - D) Helm 回滚总能撤销 Calico CRD 和数据迁移

<details>
<summary>显示答案</summary>

**答案：B) 可通过清单或 Helm chart 安装固定版本的 Tigera Operator**

Helm chart 安装的是 Tigera Operator。AWS VPC CNI 网络策略是另一种实现。对于 Marketplace 或社区产品，应核实实际目录信息及支持责任方，并明确由一种安装方式负责管理。

</details>

3. 以下哪项符合当前 AWS 原生网络策略指南？
   - A) EKS 1.14 引入了所有当前网络策略功能
   - B) VPC CNI 1.21 及更高版本在满足文档规定的平台和内核前提时支持标准策略与 Admin 策略
   - C) 原生策略永久只支持命名空间范围的策略
   - D) 原生策略和 Calico 必须同时对相同端点执行策略

<details>
<summary>显示答案</summary>

**答案：B) VPC CNI 1.21 及更高版本在满足文档规定的平台和内核前提时支持标准策略与 Admin 策略**

标准网络策略支持始于 VPC CNI 1.14，而不是 EKS 1.14。当前 AWS 指南涵盖 VPC CNI 1.21 及更高版本中的 NetworkPolicy 和 AWS ClusterNetworkPolicy；同时还要求兼容的 EKS/平台版本和 Linux 内核 5.10 或更高版本。这些 API 与 Calico 的 API 不同。

</details>

4. EKS Fargate 上的网络策略有哪些限制？
   - A) Fargate 不提供网络功能
   - B) Calico 节点代理策略和 VPC CNI 原生网络策略都不会在 Fargate Pod 内执行
   - C) 只要 kubernetesProvider 是 EKS，所有 Calico 功能都可用
   - D) Fargate 只支持 IPv6

<details>
<summary>显示答案</summary>

**答案：B) Calico 节点代理策略和 VPC CNI 原生网络策略都不会在 Fargate Pod 内执行**

Fargate 不运行这些节点代理。Pod 安全组是另一种控制措施。Calico 仍可限制涉及 Fargate 对等端的连接在 EC2 端点上的流量，但这不等于在 Fargate 内部执行策略。

</details>

5. 在此配置中，应在何处授予 AWS IAM 权限？
   - A) 给每个 calico-node 广泛的 EC2 Describe 和 CloudWatch 权限
   - B) 授予实际调用 AWS API 的组件所需权限；基础 Calico 策略使用 Kubernetes RBAC
   - C) Installation 的 nodeMetadata 字段会创建 IRSA 角色
   - D) 创建 IAM 策略就会自动将其关联到每个 ServiceAccount

<details>
<summary>显示答案</summary>

**答案：B) 授予实际调用 AWS API 的组件所需权限；基础 Calico 策略使用 Kubernetes RBAC**

VPC CNI 需要自己的 AWS 权限。exporter 或云集成也可能需要独立角色。应使用实际负责组件所支持的 IRSA 或 Pod Identity 配置；仅启用策略的基础 Calico 不需要广泛的 AWS 角色。

</details>

6. 将 Pod 安全组与 Calico 策略结合使用时，AWS 有哪些要求？
   - A) 只需设置 POD_SECURITY_GROUP_ENFORCING_MODE=strict
   - B) VPC CNI 1.11 或更高版本、POD_SECURITY_GROUP_ENFORCING_MODE=standard，以及此功能的其他前提条件
   - C) 只需为 EC2 实例添加标签
   - D) EKS Auto Mode 也支持 Pod 安全组

<details>
<summary>显示答案</summary>

**答案：B) VPC CNI 1.11 或更高版本、POD_SECURITY_GROUP_ENFORCING_MODE=standard，以及此功能的其他前提条件**

strict 模式下，这些 Pod 不受 Calico 策略执行。请核实受支持的实例类型和 branch ENI；更改模式后，应替换受影响的 Pod。在 standard 模式且使用常规外部 SNAT 时，离开 VPC 的流量使用节点安全组。

</details>

7. 升级 EKS/Calico 时，正确做法是什么？
   - A) 无论兼容性如何，总是在 EKS 升级后再升级 Calico
   - B) 选择兼容迁移的 Calico 版本，并检查 EKS、节点、附加组件和 CRD 要求
   - C) EKS 会自动升级并回滚所有第三方组件
   - D) 应用较旧的 Operator 就能保证安全降级

<details>
<summary>显示答案</summary>

**答案：B) 选择兼容迁移的 Calico 版本，并检查 EKS、节点、附加组件和 CRD 要求**

请同时检查升级前后两侧的兼容性。当前 EKS 提供有条件的七天回滚窗口，可回到前一个次要版本，但不会自动回滚 Calico 或 EKS 附加组件。恢复仍需验证兼容性和集群就绪状态。

</details>

8. 本指南所审阅的 Installation 使用哪个 provider 值？
   - A) AWS
   - B) EKS
   - C) AmazonEKS
   - D) None

<details>
<summary>显示答案</summary>

**答案：B) EKS**

使用 `spec.kubernetesProvider: EKS`；若通过 Helm values 配置，则使用 `installation.kubernetesProvider: EKS`。该值用于选择 provider 配置，并不能证明每种节点类型、CNI、数据平面或版本都受支持。

</details>

9. 哪种 CNI 类型会将网络功能委托给 Amazon VPC CNI？
   - A) Calico
   - B) AmazonVPC
   - C) AWSCNI
   - D) VPC

<details>
<summary>显示答案</summary>

**答案：B) AmazonVPC**

在 Installation 中设置 `spec.cni.type: AmazonVPC`。仅启用 Calico 策略还需要文档规定的 Pod IP annotation 和 RBAC，并确保只有一个策略引擎；单独设置 `bgp: Disabled` 不足以选择这种 CNI。

</details>

10. 为什么后端 selector 和 TCP 端口必须放在同一个 destination 映射中？
   - A) YAML 要求重复列出每个字段
   - B) 重复的 destination 键可能会丢弃 selector，导致意外端点被允许
   - C) 端口会自动匹配后端 Pod 标签
   - D) Kubernetes 总会因重复键而拒绝配置

<details>
<summary>显示答案</summary>

**答案：B) 重复的 destination 键可能会丢弃 selector，导致意外端点被允许**

有些 YAML 解析器只保留重复键中的最后一个值。应将 selector 和端口放在一起，在验证时拒绝重复键，并测试允许和拒绝的流量。节点处于 Ready 状态并不能证明策略执行正确。

</details>
