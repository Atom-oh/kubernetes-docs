# EKS 集成测验

> **相关文档**: [EKS 集成](../../../networking/calico/08-eks-integration.md)
> **最后更新**: February 22, 2026

## 测验

1. 在 EKS 上将 VPC CNI 与 Calico 配合使用时，典型的职责划分是什么？
   - A) VPC CNI 处理策略，Calico 处理网络
   - B) VPC CNI 处理网络（IP 分配），Calico 处理网络策略
   - C) VPC CNI 和 Calico 都重复处理网络
   - D) Calico 完全取代 VPC CNI

<details>
<summary>显示答案</summary>

**答案：B) VPC CNI 处理网络（IP 分配），Calico 处理网络策略**

**说明：**
在最常见的 EKS 配置中，AWS VPC CNI 通过从 VPC 分配 IP 来处理 Pod 网络，而 Calico 则以“仅策略”模式安装，以提供网络策略强制执行。这将原生 VPC 集成与 Calico 强大的策略功能相结合。

</details>

2. 在 EKS 上安装 Calico 的三种主要方法是什么？
   - A) kubectl apply、Docker、AWS CLI
   - B) EKS Add-on、Tigera Operator、Helm chart
   - C) CloudFormation、Terraform、Pulumi
   - D) eksctl、AWS Console、SDK

<details>
<summary>显示答案</summary>

**答案：B) EKS Add-on、Tigera Operator、Helm chart**

**说明：**
可使用以下方式在 EKS 上安装 Calico：1) EKS 托管附加组件（对于仅策略模式最简单），2) Tigera Operator（推荐用于完整的 Calico 功能），或 3) Helm chart（配置灵活）。每种方法在简易性与可定制性方面各有不同的权衡。

</details>

3. 从哪个 EKS 版本开始可以使用原生 Network Policy Controller？
   - A) EKS 1.12
   - B) EKS 1.14
   - C) EKS 1.18
   - D) EKS 1.24

<details>
<summary>显示答案</summary>

**答案：B) EKS 1.14**

**说明：**
EKS 从 1.14 版本开始引入原生 Network Policy Controller。该控制器提供基本的 Kubernetes NetworkPolicy 支持。不过，Calico 还提供 GlobalNetworkPolicy 和策略层级等额外策略功能，超出了原生控制器的能力范围。

</details>

4. 在 EKS Fargate 上运行 Calico 的一个关键限制是什么？
   - A) Fargate 不支持任何网络功能
   - B) Calico 无法在 Fargate Pod 上强制执行网络策略
   - C) Fargate 仅支持 IPv6
   - D) Calico 需要 root 访问权限，而 Fargate 提供该权限

<details>
<summary>显示答案</summary>

**答案：B) Calico 无法在 Fargate Pod 上强制执行网络策略**

**说明：**
Fargate Pod 在由 AWS 管理的隔离 microVM 中运行，用户无法安装 DaemonSet 或修改底层主机。由于 Calico 的 Felix agent 以 DaemonSet 形式运行，因此无法将其部署到 Fargate 节点，这意味着 Fargate Pod 无法使用网络策略强制执行功能。

</details>

5. 在 EKS 上使用 Calico 的场景中，IRSA 是什么？
   - A) Internal Route Service Allocation
   - B) IAM Roles for Service Accounts - 允许 Pod 承担 AWS IAM role
   - C) Ingress Resource Security Association
   - D) IP Range Subnet Assignment

<details>
<summary>显示答案</summary>

**答案：B) IAM Roles for Service Accounts - 允许 Pod 承担 AWS IAM role**

**说明：**
IRSA（IAM Roles for Service Accounts）允许 Kubernetes Service Account 承担 AWS IAM role。当 Calico 组件需要访问 AWS API（例如，用于 cloud provider 集成）时，IRSA 可提供安全、细粒度的访问权限，而无需在 Pod 中嵌入凭证。

</details>

6. Security Group 和 Calico 网络策略在作用范围上有何不同？
   - A) 它们在功能上完全相同
   - B) Security Group 在 VPC/ENI 层级运行，Calico 策略在 Pod/container 层级运行
   - C) Security Group 仅用于 ingress，Calico 仅用于 egress
   - D) Security Group 已被弃用，转而使用 Calico

<details>
<summary>显示答案</summary>

**答案：B) Security Group 在 VPC/ENI 层级运行，Calico 策略在 Pod/container 层级运行**

**说明：**
AWS Security Group 在 VPC 网络层运行，控制往返 ENI（Elastic Network Interface）的流量。Calico 网络策略在 Kubernetes Pod 层级运行，并使用基于 label 的 selector。两者可以结合使用以实现纵深防御：SG 提供 VPC 层级的控制，Calico 提供应用层级的策略。

</details>

7. 升级运行 Calico 的 EKS cluster 时，应考虑什么？
   - A) 升级前必须卸载 Calico
   - B) 验证 Calico 版本与目标 EKS 版本的兼容性
   - C) EKS 升级会自动升级 Calico
   - D) Calico 仅支持版本号以偶数结尾的特定 EKS 版本

<details>
<summary>显示答案</summary>

**答案：B) 验证 Calico 版本与目标 EKS 版本的兼容性**

**说明：**
升级 EKS 时，应验证当前 Calico 版本与目标 Kubernetes/EKS 版本兼容。请查阅 Calico 的兼容性矩阵，并在 EKS 升级前或升级后根据需要升级 Calico，同时遵循文档化的升级流程。

</details>

8. 对于 EKS 安装，kubernetesProvider 设置应配置为什么？
   - A) kubernetesProvider: AWS
   - B) kubernetesProvider: EKS
   - C) kubernetesProvider: Amazon
   - D) kubernetesProvider: None (auto-detected)

<details>
<summary>显示答案</summary>

**答案：B) kubernetesProvider: EKS**

**说明：**
在 EKS 上安装 Calico 时，应在 Installation resource 中将 `kubernetesProvider` 设为 `EKS`。这会告知 Calico 使用 EKS 专用配置和优化，确保与托管 Kubernetes service 正确集成。

</details>

9. 对于 EKS，Calico 的 Installation resource 中 cni.type 设置控制什么？
   - A) 要使用的 CNI 规范版本
   - B) Calico 是管理 CNI，还是交由另一个 CNI plugin 管理
   - C) 网络加密的类型
   - D) Container runtime 集成模式

<details>
<summary>显示答案</summary>

**答案：B) Calico 是管理 CNI，还是交由另一个 CNI plugin 管理**

**说明：**
`cni.type` 设置决定 Calico 的 CNI 行为。设置 `cni.type: AmazonVPC` 会告知 Calico 将网络功能交由 VPC CNI 处理，而 Calico 仅处理策略。设置 `cni.type: Calico` 则使 Calico 同时处理网络和策略。

</details>

10. EKS 上 Calico 的“仅策略模式”是什么？
    - A) 仅强制执行 GlobalNetworkPolicy 的模式
    - B) Calico 处理网络策略但不处理 Pod 网络的模式
    - C) 禁用所有 egress 策略的模式
    - D) 仅用于策略评估审计的模式

<details>
<summary>显示答案</summary>

**答案：B) Calico 处理网络策略但不处理 Pod 网络的模式**

**说明：**
仅策略模式是一种 Calico 部署配置：VPC CNI 继续处理 Pod IP 分配和路由，而 Calico 仅负责网络策略强制执行。这是 EKS 上最常见的 Calico 部署模式，因为它保留了原生 VPC 网络的优势。

</details>
