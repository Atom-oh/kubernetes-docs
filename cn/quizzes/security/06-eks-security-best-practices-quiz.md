# EKS 安全最佳实践测验

> **最后更新**: September 13, 2026

通过以下问题测试你对 Amazon EKS 安全最佳实践的理解。

***

## 问题

<span id="_1-what-authentication-method-does-a-pod-use-when-calling-aws-apis-with-irsa-iam-roles-for-service-accounts"></span>

### 1. Pod 如何通过 IRSA 获取临时 AWS 凭证？

* A) IAM User Access Key
* B) EC2 Instance Profile
* C) 基于 OIDC token 的 AssumeRoleWithWebIdentity
* D) 存储在 Kubernetes Secret 中的凭证

<details>

<summary>显示答案</summary>

**答案: C) 基于 OIDC token 的 AssumeRoleWithWebIdentity**

**说明：** Kubernetes API server 签发投射的 ServiceAccount JWT。受支持的 SDK 使用它调用 STS AssumeRoleWithWebIdentity；STS 检查受信任的 issuer/JWKS、audience 和 subject，并返回临时 AWS 凭证。IAM OIDC provider object 并非 token issuer，且 JWT 不会被直接替换为 AWS API 凭证。

</details>

***

### 2. 与 IRSA 相比，EKS Pod Identity 的主要优势是什么？

* A) 更强的加密
* B) 更快的性能
* C) 无需设置 OIDC Provider，管理更简单
* D) 支持更多 AWS 服务

<details>

<summary>显示答案</summary>

**答案: C) 无需设置 OIDC Provider，管理更简单**

**说明：** Pod Identity 无需为每个 cluster 设置 IAM OIDC provider，而是使用 association、受支持的 agent/SDK 和 EKS Auth。Role 仍需要信任关系和最小权限。Auto Mode 包含该 agent；其他平台以及 cross-account/chained role 有特定要求。它不会取代 IRSA，也不会自动增强每个应用程序的安全性。

</details>

***

<span id="_3-which-is-not-a-requirement-for-using-security-groups-for-pods"></span>

### 3. 对于基于 EC2 的 Security Groups for Pods 路径，以下哪项不是必需的？

* A) 支持 trunking 的兼容 EC2 instance type
* B) Amazon VPC CNI plugin
* C) Fargate profile
* D) SecurityGroupPolicy 配置

<details>

<summary>显示答案</summary>

**答案: C) Fargate profile**

**说明：** 对于基于 EC2 的路径，请使用支持 trunking 的兼容 instance type、兼容的 Amazon VPC CNI 以及 SecurityGroupPolicy。并非每个 Nitro instance 都符合条件。VPC Resource Controller policy 属于 cluster role。Fargate 有单独支持的模型；当前 Pod-SG 文档不支持 Windows 和 Auto Mode。ENIConfig 不能替代 SecurityGroupPolicy。

</details>

***

### 4. 将 EKS cluster 的 Kubernetes API server endpoint 设置为仅私有的影响是什么？

* A) 完全无法使用 kubectl
* B) 仅可从 VPC 或已连接网络内访问
* C) 无法从 AWS Console 管理 cluster
* D) worker node 无法连接到 API server

<details>

<summary>显示答案</summary>

**答案: B) 仅可从 VPC 或已连接网络内访问**

**说明：** 私有 API 可达性需要已连接的网络、DNS、路由和 security group，以及 IAM authentication/Kubernetes authorization。在移除公共访问前，测试 operator、CI 和恢复访问。EKS management PrivateLink endpoint 不能替代私有 Kubernetes API endpoint。

</details>

***

### 5. AWS GuardDuty EKS Protection 不检测以下哪种威胁类型？

* A) 与恶意 IP 的通信
* B) 加密货币挖矿活动
* C) Pod resource usage 超出限制
* D) Tor network 连接

<details>

<summary>显示答案</summary>

**答案: C) Pod resource usage 超出限制**

**说明：** 应区分 EKS audit 分析、基于 agent 的 Runtime Monitoring 和基础 GuardDuty 来源。覆盖范围因已启用的 plan 和平台而异；ECS Fargate 支持不等同于 EKS Fargate 支持。CPU/memory limit 监控属于运营指标工具，且检测器没有告警并不能证明不存在入侵。

</details>

***

<span id="_6-which-aws-service-does-not-require-vpc-endpoints-in-an-eks-cluster"></span>

### 6. 关于 DNS 和私有 AWS API 访问，正确的理解方式是什么？

* A) EKS management endpoint 可替代 Kubernetes API
* B) Pod Identity 始终使用全局 STS endpoint
* C) 每个 AWS Region 都支持相同的 endpoint 名称
* D) 区分 DNS resolution 与 Route 53 management API PrivateLink

<details>

<summary>显示答案</summary>

**答案: D) 区分 DNS resolution 与 Route 53 management API PrivateLink**

**说明：** 常规 DNS resolution 使用已配置的 resolver/network path。Route 53 management API 调用则不同；当前 EKS private-cluster 文档列出了 Route 53 PrivateLink service。EKS Auth、regional STS、OIDC discovery 和 ECR/S3 也各有不同路径，因此请核实实际的 service/Region 要求。

</details>

***

### 7. 使用 kube-bench 检查 EKS cluster 安全性时采用什么 benchmark？

* A) PCI-DSS
* B) 适用的 CIS Amazon EKS benchmark profile
* C) NIST Cybersecurity Framework
* D) SOC 2

<details>

<summary>显示答案</summary>

**答案: B) 适用的 CIS Amazon EKS benchmark profile**

**说明：** 请选择适用于环境的 CIS Amazon EKS benchmark edition 和 kube-bench profile。kube-bench0.16.0 包含多个 EKS profile；单个可变的上游 Job 不能证明已覆盖整个 fleet。仍存在手动/不适用检查和 managed control plane 限制，且测验/tool 分数并不等同于认证。

</details>

***

### 8. Service Account Token Volume Projection 在 EKS 中提供什么安全收益？

* A) 减小 token 大小
* B) 绑定的 token 和过期时间设置
* C) token 加密
* D) 自动备份 token

<details>

<summary>显示答案</summary>

**答案: B) 绑定的 token 和过期时间设置**

**说明：** Projection 支持 audience、请求的生命周期以及 object binding。请检查 token 的实际过期时间和接收方验证；不要假设每个 token 都会恰好在一小时后过期。被盗的 bearer token 在仍被接受期间可能遭到重放，因此 Projection 不会消除 token-protection 要求。仅使用 Projection 并不是完整的 IRSA 配置。

</details>

***

### 9. Amazon Inspector 在 EKS 环境中扫描什么？

* A) Kubernetes manifest
* B) container image 漏洞
* C) IAM policy
* D) network traffic

<details>

<summary>显示答案</summary>

**答案: B) container image 漏洞**

**说明：** ECR enhanced scanning 使用 Inspector 扫描受支持 image package 的漏洞。运行中 image 的使用信息不同于 runtime behavior 检测。只有在成功状态、完成 timestamp 和明确的 findings-count map 均存在后，才对确切 digest 进行 gate；pending/missing/error 结果不得被视为零漏洞。

</details>

***

### 10. 将 EKS cluster Control Plane log 发送到 CloudWatch 时，以下哪种 log type 无法启用？

* A) api
* B) audit
* C) controllerManager
* D) kubelet

<details>

<summary>显示答案</summary>

**答案: D) kubelet**

**说明：** 五个 EKS control-plane 类别为 api、audit、authenticator、controllerManager 和 scheduler。Kubelet/container log 需要单独的 node/runtime collection path。通过 cluster owner 启用导出，检查异步更新和实际到达情况，并配置 retention 和访问权限。

</details>

***

### 11. 为什么应在 EKS 中分离 Node IAM Role 和 Pod IAM Role (IRSA)？

* A) 节省成本
* B) 应用最小权限原则
* C) 提升性能
* D) 降低网络延迟

<details>

<summary>显示答案</summary>

**答案: B) 应用最小权限原则**

**说明：** Workload role 可独立于 node 职责限制应用程序权限。Node-role 暴露取决于 metadata 可达性和权限；并非每个 Pod 始终都能访问。仅使用 IRSA 无法阻止 IMDS。请审查 IMDSv2、network control、hostNetwork/privileged workload、SDK credential precedence 以及 node compromise。

</details>

***

<span id="_12-which-component-is-responsible-for-integrating-kubernetes-rbac-with-aws-iam-in-eks"></span>

### 12. 哪种方法可仅授予 EKS developer 所需的 namespace 访问权限？

* A) 将每位 developer 添加到 system:masters
* B) 与所有 developer 共享 node role
* C) 使用带有 scoped access policy 或 group/RBAC mapping 的 access entry
* D) 禁用 API authentication

<details>

<summary>显示答案</summary>

**答案: C) 使用带有 scoped access policy 或 group/RBAC mapping 的 access entry**

**说明：** 使用带有所需 scoped EKS access policy 或 Kubernetes group/RBAC mapping 的 access entry。Authentication 和 authorization 是分离的。aws-auth ConfigMap 是 legacy 路径，而 authentication-mode 迁移存在单向限制。避免为普通 developer 使用 system:masters；EKS access policy 或 RBAC 均可独立允许某项操作。

</details>

***

## 分数计算

每题计 1 分。

| 分数 | 评级                                                     |
| ----- | ---------------------------------------------------------- |
| 11-12 | 复习完成；接下来验证运营场景                      |
| 8-10  | 良好 - 已理解基本概念，复习高级功能 |
| 5-7   | 一般 - 建议进一步学习                     |
| 0-4   | 需要基础学习                                      |

***

## 相关文档

* [EKS 安全最佳实践](../../security/06-eks-security-best-practices.md)
* [Pod 安全标准](../../security/03-pod-security-standards.md)
* [Secrets 管理](../../security/05-secrets-management.md)
