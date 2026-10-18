# EKS 安全最佳实践测验

> **最后更新**：2026 年 9 月 13 日

通过以下问题测试你对 Amazon EKS 安全最佳实践的理解。

***

## 问题

<span id="_1-what-authentication-method-does-a-pod-use-when-calling-aws-apis-with-irsa-iam-roles-for-service-accounts"></span>

### 1. Pod 如何通过 IRSA 获取临时 AWS 凭证？

* A) IAM 用户访问密钥
* B) EC2 实例配置文件
* C) 基于 OIDC 令牌的 AssumeRoleWithWebIdentity
* D) 存储在 Kubernetes Secret 中的凭证

<details>

<summary>显示答案</summary>

**答案：C) 基于 OIDC 令牌的 AssumeRoleWithWebIdentity**

**说明：** Kubernetes API server 会签发投射的 ServiceAccount JWT。受支持的 SDK 会使用该令牌调用 STS AssumeRoleWithWebIdentity；STS 会检查受信任的签发者/JWKS、audience 和 subject，并返回临时 AWS 凭证。IAM OIDC 提供商对象并不是令牌签发者，JWT 也不能直接替代 AWS API 凭证。

</details>

***

### 2. 与 IRSA 相比，EKS Pod Identity 的主要优势是什么？

* A) 更强的加密
* B) 更快的性能
* C) 无需配置 OIDC 提供商，管理更简单
* D) 支持更多 AWS 服务

<details>

<summary>显示答案</summary>

**答案：C) 无需配置 OIDC 提供商，管理更简单**

**说明：** Pod Identity 无需为每个集群单独配置 IAM OIDC 提供商，而是通过关联关系、受支持的 agent/SDK 和 EKS Auth 工作。角色仍需要信任关系和最小权限。Auto Mode 自带该 agent；其他平台、跨账户角色和链式角色各有特定要求。Pod Identity 不会取代 IRSA，也不会自动增强每个应用的安全性。

</details>

***

<span id="_3-which-is-not-a-requirement-for-using-security-groups-for-pods"></span>

### 3. 对于基于 EC2 的 Security Groups for Pods 路径，以下哪项不是必需的？

* A) 支持 trunking 的 EC2 实例类型
* B) Amazon VPC CNI 插件
* C) Fargate 配置文件
* D) SecurityGroupPolicy 配置

<details>

<summary>显示答案</summary>

**答案：C) Fargate 配置文件**

**说明：** 对于基于 EC2 的路径，请使用支持 trunking 的实例类型、兼容的 Amazon VPC CNI 和 SecurityGroupPolicy。并非所有 Nitro 实例都符合条件。VPC Resource Controller 策略属于集群角色。Fargate 有单独支持的模型；当前 Pod-SG 文档不支持 Windows 和 Auto Mode。ENIConfig 不能替代 SecurityGroupPolicy。

</details>

***

### 4. 将 EKS 集群的 Kubernetes API server 端点设为仅私有，会有什么影响？

* A) 完全无法使用 kubectl
* B) 仅可从 VPC 或已连接的网络访问
* C) 无法从 AWS Console 管理集群
* D) 工作节点无法连接 API server

<details>

<summary>显示答案</summary>

**答案：B) 仅能从 VPC 内部或与之互通的网络访问**

**说明：** 要访问私有 API，网络必须互通，并且 DNS、路由、安全组、IAM 身份验证和 Kubernetes 授权都要正确配置。在移除公共访问前，请先测试运维工具、CI 和故障恢复通道。EKS 管理 API 的 PrivateLink 端点不能替代私有 Kubernetes API 端点。

</details>

***

### 5. AWS GuardDuty EKS Protection 不检测以下哪种威胁类型？

* A) 与恶意 IP 的通信
* B) 加密货币挖矿活动
* C) Pod 资源使用量超出限额
* D) Tor 网络连接

<details>

<summary>显示答案</summary>

**答案：C) Pod 资源使用量超出限额**

**说明：** 应区分 EKS 审计分析、基于 agent 的运行时监控和 GuardDuty 基础数据源。覆盖范围因启用的计划和平台而异；支持 ECS Fargate 不等于支持 EKS Fargate。CPU/内存限额监控属于运维指标工具；检测器没有告警也不能证明没有入侵。

</details>

***

<span id="_6-which-aws-service-does-not-require-vpc-endpoints-in-an-eks-cluster"></span>

### 6. 关于 DNS 和私有 AWS API 访问，哪种说法正确？

* A) EKS 管理端点可替代 Kubernetes API
* B) Pod Identity 始终使用全局 STS 端点
* C) 每个 AWS 区域都支持相同的端点名称
* D) 区分 DNS 解析与 Route 53 管理 API PrivateLink

<details>

<summary>显示答案</summary>

**答案：D) 区分 DNS 解析与 Route 53 管理 API PrivateLink**

**说明：** 常规 DNS 解析使用已配置的解析器和网络路径。Route 53 管理 API 调用则不同；当前 EKS 私有集群文档列出了 Route 53 PrivateLink 服务。EKS Auth、区域 STS、OIDC 发现和 ECR/S3 也各有不同路径，因此请核实实际的服务和区域要求。

</details>

***

### 7. 使用 kube-bench 检查 EKS 集群安全性时采用什么基准？

* A) PCI-DSS
* B) 适用的 CIS Amazon EKS 基准配置文件
* C) NIST Cybersecurity Framework
* D) SOC 2

<details>

<summary>显示答案</summary>

**答案：B) 适用的 CIS Amazon EKS 基准配置文件**

**说明：** 请选择适合该环境的 CIS Amazon EKS 基准版本和 kube-bench 配置文件。kube-bench 0.16.0 包含多个 EKS 配置文件；单个可能变化的上游 Job 不能证明整个集群都已覆盖。仍有需要手动执行或不适用的检查，也存在托管控制平面的限制；测验或工具得分不等同于认证。

</details>

***

### 8. Service Account Token Volume Projection 在 EKS 中提供什么安全收益？

* A) 减小 token 大小
* B) 绑定令牌并可设置有效期
* C) token 加密
* D) 自动备份 token

<details>

<summary>显示答案</summary>

**答案：B) 绑定令牌并可设置有效期**

**说明：** 投射机制支持指定 audience、请求的有效期和对象绑定。请检查令牌的实际过期时间以及接收方的验证逻辑；不要假设每个令牌都会恰好在一小时后过期。被盗的 bearer token 在仍被接受期间可能遭到重放，因此令牌投射不能免除令牌保护要求。仅使用投射机制并不能构成完整的 IRSA 配置。

</details>

***

### 9. Amazon Inspector 在 EKS 环境中扫描什么？

* A) Kubernetes 清单
* B) 容器镜像漏洞
* C) IAM 策略
* D) 网络流量

<details>

<summary>显示答案</summary>

**答案：B) 容器镜像漏洞**

**说明：** ECR 增强扫描会调用 Inspector 检查受支持镜像软件包中的漏洞。有关运行中镜像使用情况的信息不同于运行时行为检测。只有状态为成功、存在完成时间戳且有明确的发现数量映射时，才应根据确切的镜像 digest 执行准入门禁；pending、missing 或 error 结果都不能视为零漏洞。

</details>

***

### 10. 将 EKS 集群控制平面日志发送到 CloudWatch 时，以下哪种日志类型无法启用？

* A) api
* B) audit
* C) controllerManager
* D) kubelet

<details>

<summary>显示答案</summary>

**答案: D) kubelet**

**说明：** EKS 的五种控制平面日志类别是 api、audit、authenticator、controllerManager 和 scheduler。Kubelet 和容器日志需要通过独立的节点/运行时采集路径收集。由集群所有者启用日志导出后，还要检查异步更新结果和日志是否实际到达，并配置保留期与访问权限。

</details>

***

### 11. 为什么应在 EKS 中分离节点 IAM 角色和 Pod IAM 角色（IRSA）？

* A) 节省成本
* B) 遵循最小权限原则
* C) 提升性能
* D) 降低网络延迟

<details>

<summary>显示答案</summary>

**答案：B) 遵循最小权限原则**

**说明：** 工作负载角色可以在节点职责之外单独限制应用权限。节点角色是否会暴露，取决于元数据服务是否可达以及相关权限；并非每个 Pod 都始终可以访问它。仅使用 IRSA 无法阻止对 IMDS 的访问。请检查 IMDSv2、网络控制、hostNetwork/特权工作负载、SDK 凭证优先级以及节点遭入侵时的影响。

</details>

***

<span id="_12-which-component-is-responsible-for-integrating-kubernetes-rbac-with-aws-iam-in-eks"></span>

### 12. 哪种方法可仅向 EKS 开发人员授予所需的命名空间访问权限？

* A) 将每位开发人员都加入 system:masters
* B) 与所有开发人员共享节点角色
* C) 使用 access entry，并配置范围受限的访问策略或组/RBAC 映射
* D) 禁用 API 身份验证

<details>

<summary>显示答案</summary>

**答案：C) 使用 access entry，并配置范围受限的访问策略或组/RBAC 映射**

**说明：** 使用 access entry，并为其配置所需的范围受限 EKS 访问策略或 Kubernetes 组/RBAC 映射。身份验证与授权是两个独立环节。aws-auth ConfigMap 属于旧路径，身份验证模式的迁移则有单向限制。不要为普通开发人员授予 system:masters；EKS 访问策略或 RBAC 中的任一机制都可能单独允许某项操作。

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
