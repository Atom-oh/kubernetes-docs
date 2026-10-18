# Landing Zone、OU 和组织级管控

> **最后更新**：2026 年 9 月 13 日

## 1. Control Tower Landing Zone 4.0 的基线依赖链

标准化多账户环境时，AWS Control Tower 通常是首先会采用的工具。Control Tower 提供受管账户创建功能，以及组织级基线 / 控制；但 **Landing Zone 4.0 中的多个基线存在必须遵循的启用顺序**。如果没有了解这一依赖链就定稿 OU 和 IAM 设计，之后可能需要返工。

### 启用依赖链

```
CentralConfigBaseline
  └─▶ CentralSecurityRolesBaseline
        ├─▶ IdentityCenterBaseline
        ├─▶ BackupAdminBaseline
        └─▶ BackupCentralVaultBaseline
```

要使用 `IdentityCenterBaseline`（Identity Center 集成），必须先启用 `CentralSecurityRolesBaseline`，而后者又要求先启用 `CentralConfigBaseline`（AWS Config）。**停用时必须按相反顺序进行**：先关闭右侧的全部三个基线（IdentityCenter / BackupAdmin / BackupCentralVault），再关闭 SecurityRoles，最后才能关闭 Config。

> **范围**：此依赖链适用于 Control Tower 4.0 管理的 IdentityCenterBaseline。IAM Identity Center 本身并不要求 AWS Config。请区分独立管理的 Identity Center 与其 Control Tower 集成。

Landing Zone 的 Config 集成会将 Config 资源部署到服务集成账户。成员账户需要应用 OU 级别的 AWSControlTowerBaseline 或 ConfigBaseline；一个 OU 不能同时使用这两种基线。此受管路径要求启用 Landing Zone Config 集成。若独立部署 Config，则还需单独设计资源所有权、冲突处理和侦测型控制覆盖范围。

<span id="the-security-ou-is-no-longer-freely-designable"></span>

### Security OU 的放置和基线范围

较早的 Landing Zone 版本会创建由 Control Tower 管理的 Security OU。**4.0 版本不再管理该 OU 的创建；包含服务集成账户的共同父级 OU 会被指定为 Security OU**。请检查以下基线范围限制。

1. `AWSControlTowerBaseline` 和 Config Baseline 不能应用到此 OU（显示为 `Not Applicable` 是正常现象）。可以应用 `BackupBaseline`。
2. 如果将非服务集成账户放入此 OU，它们不会获得基线资源。
3. Control Tower 只会自动为 Logging 账户和 SecurityRoles 账户创建 Identity Center 权限集。**Config 账户和 Backup 账户的权限集必须由你自行创建。**

将普通账户移入与服务集成账户相同的 OU，可能导致已启用的控制发生漂移；此问题独立于自动注册。上述限制针对该 OU。可考虑为普通安全工具和等待迁移的账户单独设置受管 OU。

> **设计提议**：将服务集成账户与一般安全运维账户分开，以明确基线范围。AWS 不要求使用特定 OU 名称。

### CentralizedLogging 停用行为已变更

在 Control Tower 3.3 及更早版本中，停用 CentralizedLogging 集成只会关闭 Organization CloudTrail，并保留已经部署的资源。**在 4.0 中，停用该集成会实际删除日志账户中的 Config Recorder、Delivery Channel 和与 CloudTrail 相关的 stack instance**。此后，Control Tower 将不再管理该账户。

停用之前，应分别清点受影响的 stack、记录缺口和保留的 S3 日志。可通过重新启用集成或将账户移至受管 OU 来恢复管理，但必须验证采集缺口是否已恢复。此行为并不能证明所有历史日志都已被删除。

### 在 Control Tower 与内部流水线之间划分职责

根据启用哪些服务集成和 OU 基线，需要先在以下两个方向中作出选择。

| 方向 | 配置 | 权衡 |
|---|---|---|
| A. 由 Control Tower 管理 | 按依赖顺序启用所需集成；为各 OU 选择基线 | 集中运维，同时管理记录范围和成本 |
| B. 明确划分所有权 | 定义独立管理的 Identity Center / Config 和 Control Tower 范围 | 由内部负责生命周期、冲突和覆盖范围验证 |

## 2. 自动注册

从 Landing Zone 3.1+ 开始，在将账户移入已注册 OU 之前，通过 Landing Zone 设置 / API 启用自动注册，便可自动应用该 OU 的基线和控制。但仍有一些事情不会自动为你处理。

- **它不会自动解决已有配置冲突或处理故障恢复**。必须单独进行预检查，例如 Config、CloudTrail、SCP 和 IAM 冲突检查。
- 取消注册可能会移除受管基线资源。还需单独确认现有日志和证据是否保留。对于正在退役的账户，在限制变更的同时保留治理是一种运维选择；AWS 并未要求每个 OU 都必须保持注册状态。
- 注册遵循最终一致性模型；根据移动账户的数量，可能需要几分钟到几小时。
- **自动注册不会创建、修改或终止 Service Catalog provisioned product**。如果取消注册通过 Account Factory 创建的账户，其 provisioned product 会成为管理账户中的孤立资源。

如果内部流水线自动执行“移动账户 → 自动注册 → 工作负载引导”，触发条件应为“**已确认基线应用完成**”，而不是账户移动事件本身。

## 3. 各组织策略类型的配额

Organizations 支持的策略类型用途不同，默认配额也各不相同。

| 策略类型 | 每个实体最多可附加数量 | 文档最大大小 | 全组织最大数量 |
|---|---|---|---|
| SCP | 10 | 10,240 个字符 | 10,000 |
| RCP | 5（包括 `RCPFullAWSAccess`；可用 4 个） | 5,120 个字符 | 2,000 |
| Declarative policy | 10 | 10,000 个字符 | 1,000 |
| Tag policy | 10 | 10,000 个字符 | 1,000 |
| Backup policy | 10 | 10,000 个字符 | 1,000 |
| Security Hub policy | 10 | 10,000 个字符 | 1,000 |

关键在于，**继承的策略不会占用实体级别的附加数量限制**。这会极大影响 SCP 的放置策略。

### SCP 附加位置策略

| 策略 | 配置 | 从配额角度评估 |
|---|---|---|
| 根级集中 | 在 Root 附加组织范围通用 SCP，OU 继承 | 新账户会立即继承控制，但很难为各 OU 单独设置例外 |
| 每个 OU 直接附加完整策略 | 直接附加每个 OU 所需的所有 SCP，尽量减少对父 OU 的依赖 | 不使用继承，因此单个 OU 可能耗尽全部 10 个附加名额；达到上限后必须合并策略 |
| **分层策略包** | Root 只承载最少且无例外的 SCP；其余通过版本化的 OU 级策略包和有期限的例外管理 | 主动利用继承来节省每个 OU 的直接附加名额，**从配额角度看最易扩展** |

通过 Git 修订版本、部署清单和 CloudTrail 变更记录，管理策略文档及附加清单的版本。Sid 中的版本标记是可选的。继承的 SCP / RCP、资源策略和权限边界具有不同的评估范围；一次模拟不能证明最终有效授权完整无误。

还有几项已确认的限制：

- **如果实体启用了任何 SCP，就不能移除最后剩余的 SCP。**“例外 OU 完全没有控制”的设计无法成立；即使例外 OU 也需要最低限度的基线 SCP。
- OU 在 Root 之下最多可嵌套 **5 层**，整个组织最多可有 **2,000 个 OU**。扁平结构或浅层功能混合结构不受此上限影响。
- 每个实体的五个 RCP 附加名额中，`RCPFullAWSAccess` 占用一个。直接附加名额只剩四个并不妨碍继承。应在 Root、OU 和账户层分布控制，同时检查受支持的服务、服务主体例外和显式 Deny。RCP 可以保护敏感数据路径，但不能取代 IAM、KMS 或资源策略。
- Organizations 还支持 **Security Hub policy 类型**，可通过组织策略集中部署 Security Hub 配置；值得将其与 SCP / RCP / declarative policy / Tag Policy 一并审查。

### 各策略类型的职责（已确认事实）

| 策略类型 | 职责 |
|---|---|
| SCP | 限定主体的最大权限（不会授予权限） |
| RCP | 限定成员账户中受支持资源可用的最大权限（不会授予权限） |
| Declarative policy | 为受支持服务维护全组织通用基线设置 |
| Tag Policy | 检查并强制执行标签标准合规性 |
| Control Tower control | 在 OU 层实施预防型 / 主动型 / 侦测型控制 |

请牢记 SCP 求值的一项原则：采用允许列表时，从 Root 到目标账户的**每一层**都必须有明确的 Allow；而任何一层中的显式 Deny 都不能被下层的 Allow 覆盖。

## 4. 允许列表与拒绝列表

| 方法 | 适用场景 | 运维开销 |
|---|---|---|
| 以允许列表为主 | 沙箱、可预先限制可用服务集合的受监管区域 | 每个新服务 / API 在使用前都必须显式允许 |
| **以拒绝列表为主** | 一般 Workload OU（默认） | 需要持续侦测新服务 / API 风险并维护 Deny 目录 |

将各区域的 describe-vpc-endpoint-services 结果与服务文档进行比较。仅凭 API 清单无法证明 endpoint policy、功能或私有 DNS 支持情况完整。

## 5. OU 设计选项

| 选项 | 配置 | 优点 | 缺点 |
|---|---|---|---|
| 深层级结构 | Root 下多个嵌套层级，父级控制由子级继承 | 易于通过层次结构表达分类和共享控制 | 高层级 Deny 的影响范围大；实际层级上限为 5 层 |
| Root 下扁平结构 | 大多数 OU 直接位于 Root 下，控制直接附加 | 易于判断每个 OU 的影响范围 | 可能重复或遗漏共享策略；不使用继承时会消耗 10 个附加名额 |
| **浅层功能混合结构** | 将较少变动的功能型 OU（`Security`、`Infrastructure`）与生命周期 / 流程型 OU（`Workloads/Production`、`Workloads/Non-production`、`Sandbox`、`PolicyStaging`、`Transitional`、`Suspended`）浅层组合 | 降低组织结构图变更的影响范围，同时表达运维状态 | 功能分类、生命周期、继承和策略包必须一起验证。由于上文所述的 4.0 Security OU 限制，应考虑将服务集成账户和一般运维账户分开部署 |

`Transitional` 可暂存待迁移账户，以执行迁移检查；`Suspended` 可在退役前限制变更。应按生命周期决定注册状态、证据保留和恢复访问。若事件调查流程不同，应单独设置 `Quarantine`。

应区分长期存在的 `Production-Exception` OU 与有时限的例外策略。如果某个 API 或策略只需在有限时间内获准，应在标准 Production OU 中通过需审批且会过期的例外处理；只有当账户需要与标准基线在技术上不兼容、且长期不同的控制集时，才单独创建 OU。

## 下一步

确定 Landing Zone 和 OU 结构后，下一项决策是如何划分账户，以及应向人员和工作负载开放哪些 IAM 路径 → [账户结构和 IAM 边界](./02-account-and-iam.md)

## 参考资料

- [Organizations 配额](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_reference_limits.html)
- [Control Tower Landing Zone 4.0 的重要变更](https://docs.aws.amazon.com/controltower/latest/userguide/key-changes-lz-v4.html)
- [Control Tower AWS Config 更新（4.0）](https://docs.aws.amazon.com/controltower/latest/userguide/config-updates-v4.html)
- [Control Tower 账户自动注册](https://docs.aws.amazon.com/controltower/latest/userguide/account-auto-enrollment.html)
- [基线类型](https://docs.aws.amazon.com/controltower/latest/userguide/types-of-baselines.html)
- [注册现有账户](https://docs.aws.amazon.com/controltower/latest/userguide/enroll-account.html)
- [SCP 求值](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_scps_evaluation.html)
- [RCP](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_rcps.html)
- [Declarative policy](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_declarative_policies.html)
- [Tag Policy](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_tag-policies.html)
- [Control Tower 控制参考](https://docs.aws.amazon.com/controltower/latest/controlreference/controls.html)
- [AWS 多账户设计原则](https://docs.aws.amazon.com/whitepapers/latest/organizing-your-aws-environment/design-principles-for-your-multi-account-strategy.html)
- [AWS 推荐的 OU 和账户](https://docs.aws.amazon.com/whitepapers/latest/organizing-your-aws-environment/recommended-ous-and-accounts.html)
