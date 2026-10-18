# 数据与安全边界

> **最后更新**：2026 年 9 月 13 日

## 1. 数据归属方案

| 方案 | 配置 |
|---|---|
| 集中式数据库运维账户 | 平台团队在单个账户中拥有并运维所有数据库 |
| 工作负载自有数据 | 每个工作负载团队拥有并运维自己的数据库 |
| **混合模式** | 按工作负载选择运维数据库；数据湖 / 仓库 / 流处理骨干网等共享资产由独立的数据平台负责 |

对大多数组织来说，混合模式是现实的起点。但与下一节介绍的**跨账户备份 / 恢复技术限制**相比，数据归属的选择没那么关键。

<span id="_2-cross-account-data-recovery-constraints-—-the-conditions-that-actually-change-your-decision"></span>

## 2. 按资源和保管库类型验证跨账户恢复

应同时选择数据归属方式和恢复位置。某个快照 API 的限制，不代表所有恢复路径都无法实现。

<span id="rds-snapshots"></span>

### 共享 RDS 快照

- 对于 RDS DB 实例，先将自动快照复制为手动快照，再进行共享。RDS 共享流程也会讨论 AWS Backup 生成的快照，但并未定义所有 AWS Backup 恢复工作流。
- 接收方在恢复加密的 DB 实例快照之前，必须先复制该快照。使用默认 AWS 托管 KMS 密钥加密的快照不能直接共享；应评估使用经批准的客户托管密钥进行加密复制。
- 一个手动快照最多可以共享给 20 个账户。Oracle / SQL Server 永久 / 持久化选项会增加限制。
- **Multi-AZ DB cluster 快照不能使用此 RDS 快照共享路径**。这并不排除所有逻辑备份或经过验证的复制 / 恢复路径，也不意味着必须让工作负载自有数据库。请检查数据库引擎、快照类型、区域支持情况，以及替代恢复路径的 RTO / RPO。

<span id="aws-backup-cross-account-copy"></span>

### 标准 AWS Backup 保管库：先复制，再恢复

- 源账户和目标账户必须属于同一个 Organization，并且其管理账户已启用跨账户备份。
- 源角色需要 `backup:CopyFromBackupVault` 和 `backup:CopyIntoBackupVault` 权限；目标保管库需要资源策略，允许使用后一个权限。还需相应服务的备份 / 复制权限和 KMS 权限。
- 加密方式取决于资源类型。由 AWS Backup 完全管理的资源支持将目标设为 `aws/backup` 或客户托管密钥；其他资源类型必须使用客户托管密钥。官方复制页面还警告不要使用默认保管库。因此，本指南使用**专用目标保管库，并显式配置密钥 / 策略**；仅凭保管库名称无法确定它是否适合加密 / 复制。
- 标准保管库的跨账户恢复流程是先复制，再在目标账户中恢复。请预先准备资源的服务相关角色、恢复角色、子网和安全组。
- 不支持从冷存储层进行跨账户复制。请检查资源和区域功能矩阵。

### 逻辑隔离保管库：直接从共享账户恢复

可以通过 AWS RAM 将逻辑隔离保管库共享给单个账户，**也包括其他 Organization 中的账户**。接收方可以直接恢复受支持的恢复点，无需先将其复制到接收方的保管库。因此，“AWS Backup 从不支持直接跨账户恢复”这一说法不准确。

请区分标准保管库复制权限和逻辑隔离保管库的 RAM 共享。验证资源 / 区域支持情况、恢复 IAM 权限、加密密钥类型、共享授权，以及源账户不可访问时的恢复方式。不要假设这适用于所有数据库类型。

<span id="summary"></span>

### 限制未经批准的复制和共享

副本离开 Organization 后，目标端可能仍会保留已有副本。应综合评估源端的 `backup:CopyTargets` / `backup:CopyTargetOrgPaths` 条件、目标保管库策略、KMS、RAM 共享权限和退出组织的流程。启用跨账户备份并不会授予所有用户复制权限，也不能绕过 IAM、保管库或 KMS 的拒绝策略。

RTO 应涵盖事件发生后实际执行的复制、恢复和应用验证时间。预先存在的副本则会使复制频率成为 RPO 的考虑因素。请在[决策框架](./06-decision-framework-and-poc.md)中记录每种资源的恢复测试和目标。

## 3. 隔离 PII 数据层

直接放置在 VPC 中的存储（如 RDS）很适合与通用服务层部署在不同的 VPC。这样做是为了分离路由、检查、直接访问和事件遏制的范围。**仅仅拆分 VPC 并不足够**；IAM、安全组、KMS 密钥策略、日志和经批准的访问路径也必须共同发挥作用。

> **共享 VPC 的审计访问**：参与账户无法描述所有者的 NAT Gateway，但所有者提供的路由 / NAT 清单、Config、Flow Logs 和委派只读访问可以提供证据。专用 VPC 可以简化归属管理；共享 VPC 本身并不意味着无法审计。

S3 资源并不直接放置在 VPC 中。应通过存储桶 / 账户归属、VPC 端点及端点策略、存储桶 / 访问点策略、KMS 密钥策略和组织批准的路径来控制访问。

### 阻止 Dev / QA 访问生产环境中的原始 PII 数据

将“阻止直接访问”落实到具体 API 路径后，可以得到如下覆盖矩阵。

| 路径 | 控制机制 |
|---|---|
| AWS Backup 跨账户复制 | 使用 `backup:CopyTargets` / `CopyTargetOrgPaths` SCP 条件、目标保管库访问策略 |
| RDS DB 实例快照共享 | 将 `rds:ModifyDBSnapshotAttribute` 限制为经批准的自动化；使用 `DescribeDBSnapshotAttributes` 审计接收方 |
| Aurora DB cluster 快照共享 | 将 `rds:ModifyDBClusterSnapshotAttribute` 限制为经批准的自动化；使用 `DescribeDBClusterSnapshotAttributes` 审计接收方 |
| RDS / Aurora 公有快照共享 | 验证接收方允许列表和两个共享 API 对 `restore=all` 的拒绝行为；保留 KMS、检测和修复控制措施 |
| 对外共享 EBS 快照 | 限制 / 审计 `ec2:ModifySnapshotAttribute` 和接收方的 createVolumePermission |
| EC2 Allowed AMIs（使用方） | 使用账户 / 区域设置或声明式策略限制对公有 / 共享 AMI 的发现和使用；账户自有 AMI 不受影响 |
| S3 Batch Replication / 跨账户复制 | 存储桶策略、限制复制角色、RCP |
| 使用 DMS / Glue 进行迁移 | 控制对应服务的网络 / IAM 路径 |
| CDC 流（MSK / Kinesis / DMS） | 资源策略 + 限制跨账户使用方 |
| 跨账户 Athena / Redshift 查询、Lake Formation | 审计 Lake Formation 跨账户授权 |

根据所选复制 / 恢复路径和组织要求选择 KMS 密钥类型及恢复权限。AWS 并未普遍要求所有 PII 存储都使用客户托管密钥。请测试目标密钥、预先存在的副本、允许的密钥策略 / 授权，以及源账户不可用时的逻辑隔离保管库共享方式。

## 4. Secrets Manager / KMS 跨账户访问

Secrets Manager 中的 Secret 资源策略和调用方的身份策略都必须配置。跨账户访问 Secrets Manager 时必须使用客户托管 KMS 密钥；该密钥还需要同时配置所有者的密钥策略和调用方的 IAM 策略。也就是说，集中管理密钥 / 密钥材料不能只配置策略和轮换，还需要**由两个账户共同管理权限和恢复责任**。

## 5. AWS 原生安全遥测与现有 CNAPP 的对比

如果组织已经使用 CNAPP（云原生应用保护平台），并准备采用 AWS 原生功能，较稳妥的做法不是“替换现有产品”，而是**按照安全目的，将当前覆盖范围与 AWS 原生能力进行比较，并仅填补已确认的缺口**。安全目的可以分为：

- 组织级预防性控制
- 配置态势
- 数据安全态势
- 工作负载运行时保护
- 威胁检测
- 调查结果工作流
- 工作负载上下文检测

已确认的事实包括：

- 应区分 Security Hub CSPM 标准、控制项和 ASFF 调查结果与 Security Hub 的其他能力。仅凭名称无法确认功能范围或 Config 依赖完全相同。
- 大多数 Security Hub CSPM 控制项都要求 AWS Config 记录配置。应结合 Control Tower 4.0 托管基线的依赖关系进行审查，但不要将其误认为 IAM Identity Center 服务本身的 Config 前置要求。
- **Security Hub CSPM 不会追溯收集启用前生成的调查结果，也只处理已启用该服务的区域中的调查结果**。若要全面覆盖文档所述 CIS AWS Foundations Benchmark 安全检查，必须在每个受支持的区域中启用它。GuardDuty 也需要按区域启用。
- 首尔区域同时支持 GuardDuty 和 Security Hub，但各区域的调查结果类型 / 控制项覆盖范围可能不同；比较时应以首尔区域的实际覆盖情况为准。

## 6. 已确认支持在共享子网中创建资源的服务

下表总结了官方共享 VPC 支持列表。该列表明确允许遗漏服务；对于未列出的服务，请查阅其专属文档，并区分“明确不支持”和“列表中未提及”。

| 支持的服务 | 说明 |
|---|---|
| Amazon RDS、Aurora | 主要目标 |
| ElastiCache（Redis OSS） | |
| Redshift、EMR、Glue | 常见的数据平台目标 |
| OpenSearch Service、MSK | |
| EC2、ECS、EKS、Lambda、EFS | |
| ALB / NLB / GWLB | |
| PrivateLink（接口端点） | |
| VPC Lattice、TGW、VPC Peering、Traffic Mirroring | |
| Route 53（跨账户关联 PHZ） | |
| DMS、Verified Access、SageMaker Unified Studio | |
| **Amazon MQ** | **仅支持 ActiveMQ，不支持 RabbitMQ** |

如果官方列表明确排除了某个引擎（例如 Amazon MQ RabbitMQ），应评估是否单独部署。在将整个 CUJ 排除在 Shared VPC 之外之前，可以考虑只通过其他 VPC 或 API 路径连接这项依赖。

## 后续阅读

若要让跨越边界、账户、IAM、网络和数据的所有决策都可复现，请参阅 → [决策框架与 PoC 设计](./06-decision-framework-and-poc.md)

## 参考资料

- [RDS 快照共享](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_ShareSnapshot.html)
- [RDS 加密快照共享](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/share-encrypted-snapshot.html)
- [AWS Backup 跨账户复制](https://docs.aws.amazon.com/aws-backup/latest/devguide/create-cross-account-backup.html)
- [Secrets Manager 跨账户访问](https://docs.aws.amazon.com/secretsmanager/latest/userguide/auth-and-access_examples_cross.html)
- [KMS 外部账户密钥策略](https://docs.aws.amazon.com/kms/latest/developerguide/key-policy-modifying-external-accounts.html)
- [Security Hub CSPM 简介](https://docs.aws.amazon.com/securityhub/latest/userguide/what-is-securityhub.html)
- [各区域的 Security Hub CSPM 控制项](https://docs.aws.amazon.com/securityhub/latest/userguide/regions-controls.html)
- [GuardDuty 各区域差异](https://docs.aws.amazon.com/guardduty/latest/ug/guardduty_regions.html)
- [AWS SRA 安全工具](https://docs.aws.amazon.com/prescriptive-guidance/latest/security-reference-architecture/security-tooling.html)
- [共享子网支持的服务](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-sharing-service-behavior.html)
- [逻辑隔离保管库的共享与恢复](https://docs.aws.amazon.com/aws-backup/latest/devguide/logicallyairgappedvault.html)

- [Aurora 快照共享 API](https://docs.aws.amazon.com/AmazonRDS/latest/APIReference/API_ModifyDBClusterSnapshotAttribute.html)
- [EC2 Allowed AMIs 的适用范围](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-allowed-amis.html)
