# 容器镜像仓库

> **最后更新**：2026 年 9 月 11 日

## 简介

容器镜像仓库是 Kubernetes 生态系统中的基础设施组件，用于集中存储、管理和分发容器镜像。它连接 CI/CD 流水线与 Kubernetes 集群，帮助工作负载可靠、安全地获取镜像。

容器镜像仓库提供：

- **镜像存储**：持久化存储容器镜像，并通过标签进行版本管理
- **访问控制**：通过身份验证和授权机制控制谁可以推送或拉取镜像
- **安全扫描**：在部署前检测容器镜像中的漏洞
- **分发**：高效缓存和分发镜像层到容器运行时
- **生命周期管理**：通过自动清理和保留策略优化存储

![流程图：容器镜像从 CI/CD 流水线（构建、测试、推送）进入容器镜像仓库（存储、版本管理、扫描），再进入 Kubernetes 集群（拉取、运行、扩缩容）。](../.gitbook/assets/en-container-registry-readme-0.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-container-registry-readme-0.html)

## 镜像仓库对比

| 特性 | Docker Hub | Amazon ECR | Harbor |
|---------|------------|------------|--------|
| **类型** | SaaS（公有云） | AWS 托管服务 | 自托管（CNCF） |
| **定价模式** | 个人版和付费订阅 | 按使用量计费 | 基础设施、运维和备份费用 |
| **私有仓库** | 个人版：1 个；付费方案按方案提供额度 | 适用服务配额 | 由运营方配置配额 |
| **公有仓库** | 遵循方案政策提供 | ECR Public 提供免费额度并收取使用费用 | 支持 |
| **存储定价** | 取决于方案 | 取决于区域和存储类别 | 自行管理 |
| **数据传输** | 遵循使用量和合理使用政策 | 费用取决于目的地和区域 | 自行管理 |
| **漏洞扫描** | Docker Scout 方案额度 | Basic / Enhanced（Inspector） | 集成 Trivy |
| **镜像签名** | DCT 或单独的 OCI 签名工具 | AWS Signer 托管签名或手动签名 | Cosign / Notation |
| **复制** | 不提供 | 跨区域复制 | 拉取 / 推送复制 |
| **RBAC** | 组织级别 | IAM 策略 | 项目级别角色 |
| **完全断网运行** | 需要能访问 Hub | 需要 AWS 连接；VPC 端点提供私有访问 | 导入镜像、扫描器数据库和安装依赖 |
| **速率限制** | 按账户设置拉取限制和合理使用政策 | 每个 API 的服务配额 | 运营方限制和基础设施容量 |
| **集成** | 通用 | AWS 原生（EKS、IAM） | Kubernetes 原生 |
| **合规** | 检查服务当前的合规证明及其适用范围 | 检查 AWS 服务 / 区域资格和你的控制措施 | 由运营方负责控制措施和证据 |

ECR 有[服务配额](https://docs.aws.amazon.com/AmazonECR/latest/userguide/service-quotas.html)，包括请求速率和仓库数量限制。ECR 支持 [AWS Signer 集成](https://docs.aws.amazon.com/AmazonECR/latest/userguide/image-signing.html)；存储签名和在部署期间强制验证属于两项独立配置。请查看 Docker Hub 的[当前使用政策](https://docs.docker.com/docker-hub/usage/)和响应标头，不要将历史拉取限制当作普遍适用的当前规则。

## 详细对比

### Docker Hub

**适用场景**：开源项目、开发环境，以及需要快速上手的团队

**优点**：

- 公有镜像库规模最大（Official Images、Verified Publishers）
- 无需管理基础设施
- Docker CLI 集成简单
- 可通过 GitHub Actions / GitLab CI 等外部 CI 自动构建并推送；Hub 原生 Automated Builds 已弃用

**缺点**：

- 按账户设置拉取限制，并有合理使用 / 滥用控制
- 免费方案的私有仓库存储有限
- 没有原生 AWS / Kubernetes 集成
- 使用公有镜像可能带来供应链安全风险

**定价**：请通过[当前定价页面](https://www.docker.com/pricing/)比较用户数量、按月或按年计费方式，以及包含的 Scout / 构建用量。历史上的 Pro 每月 5 美元、Team 每月 9 美元价格和每日拉取额度不能作为当前定价基准。

### Amazon ECR

**适用场景**：AWS 原生工作负载、EKS 集群，以及需要满足合规要求的企业

**优点**：

- 与 EKS 节点和 Fargate 执行角色集成；工作负载的 IRSA / Pod Identity 权限与镜像拉取凭证相互独立
- 基于 IAM 的访问控制，并可调整 API 服务配额
- 跨区域复制
- 使用 Amazon Inspector 进行增强扫描
- 通过 VPC 端点私有连接 AWS；但这并不构成完全断网的隔离环境
- 按使用量付费（无需预先承诺）

**缺点**：

- 可能造成 AWS 厂商锁定
- 镜像库较大时成本可能不断累积
- 生命周期策略语法较复杂
- 跨账户访问需要仔细配置 IAM

**定价**：根据适用的区域 / 存储类别费率计算已存储数据的费用，再计入传输、Inspector、AWS Signer 和 VPC 端点费用。按照官方示例中的每 GB 月 0.10 美元费率，100 GB 每月需 10 美元，**这仅是存储费用**。传输到同一区域内受支持的 AWS 计算服务，与互联网或跨区域流量的费用不同；请依据实际路径查阅 [ECR 定价](https://aws.amazon.com/ecr/pricing/)。

### Harbor

**适用场景**：本地部署、隔离网络环境、多云和合规要求严格的行业

**优点**：

- 完全控制数据和基础设施
- 不受厂商锁定
- 功能丰富（复制、扫描、签名、RBAC）
- CNCF 毕业项目，拥有成熟且活跃的社区
- 适合受监管行业（金融、医疗保健、政府）

**缺点**：

- 运维开销较大（部署、升级、备份）
- 需要投入基础设施
- 管理学习曲线较陡
- 实现高可用较复杂

**定价**：无许可证费用。基础设施费用取决于部署方式，包括：

- Kubernetes 集群资源（CPU、内存、存储）
- 持久化存储（数据库、镜像仓库存储）
- 网络 / 负载均衡器费用

## 选择标准

请根据以下因素选择容器镜像仓库：

### 1. 基础设施环境

| 环境 | 推荐的镜像仓库 |
|-------------|---------------------|
| AWS 原生（EKS） | Amazon ECR |
| 多云 / 混合云 | Harbor |
| 开发 / 开源 | Docker Hub |
| 隔离 / 断网环境 | Harbor |
| 边缘计算 / IoT | Harbor（配合复制） |

### 2. 安全与合规要求

比较访问控制、凭证有效期、漏洞扫描、按摘要固定版本、签名验证、网络边界和恢复流程。产品不会仅仅因为自托管或订阅等级较高就自动变得更安全。服务符合某项合规资格，也不意味着工作负载在缺少必要控制措施时就自动合规。

- **AWS 要求**：检查 ECR 是否适用于指定区域和合规范围。
- **数据主权或断网运行**：Harbor 可提供部署控制权，但补丁、备份和证据收集由运营方负责。
- **托管协作**：将 Docker Hub 实际方案功能与团队所需的控制措施进行比较。

### 3. 团队规模与预算

- **小型团队、预算有限**：Docker Hub Free / Pro
- **使用 AWS 的成长型团队**：Amazon ECR（按使用量付费）
- **拥有专职平台团队的企业**：Harbor

### 4. 运维偏好

- **完全托管、无需运维**：Docker Hub 或 Amazon ECR
- **全面控制、自定义**：Harbor

## 章节内容

本章节将深入介绍容器镜像仓库概念和实现方式：

1. [Docker Hub](01-docker-hub.md) - 公有仓库的使用、速率限制和 Kubernetes 集成
2. [Amazon ECR](02-amazon-ecr.md) - 支持生命周期策略和 EKS 集成的 AWS 原生镜像仓库
3. [Harbor](03-harbor.md) - 通过 CNCF 毕业认证的自托管企业级镜像仓库
4. [最佳实践](04-best-practices.md) - 跨镜像仓库的安全、成本和运维策略

## 快速选择决策树

![容器镜像仓库选择决策树：隔离环境选择自托管 Harbor；已连接的 AWS / EKS 工作负载选择 Amazon ECR；其他有合规要求的生产工作负载选择 Harbor 或 Docker Hub Business；其余场景使用 Docker Hub Free / Pro。](../.gitbook/assets/en-container-registry-readme-1.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-container-registry-readme-1.html)

## 总结

容器镜像仓库是关键基础设施，会直接影响部署可靠性、安全态势和运维成本。Docker Hub 最容易上手，Amazon ECR 与 AWS 集成最紧密，而 Harbor 能为复杂的企业需求提供最高程度的控制和灵活性。

本章节后续文档将针对每种镜像仓库方案提供详细的实施指南，帮助你充分利用所选方案。
