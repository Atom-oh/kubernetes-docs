# Landing Zone、OU 与组织控制测验

> 本测验用于检查你对 [Landing Zone、OU 与组织控制](../../governance/01-landing-zone-and-ou.md)的理解。

---

1. 在 Control Tower 4.0 中，激活 IdentityCenterBaseline 之前需要完成什么？
   - A) 不需要任何基线
   - B) CentralSecurityRolesBaseline 及其前置依赖 CentralConfigBaseline
   - C) BackupCentralVaultBaseline
   - D) Identity Center 本身要求每个环境都启用 Config

<details>
<summary>显示答案</summary>

**答案：B) CentralSecurityRolesBaseline 及其前置依赖 CentralConfigBaseline**

**说明：**
这是 Control Tower 管理基线的依赖，并非 Identity Center 服务对 Config 的通用前置要求。

</details>

---

2. 哪项说法描述了 Control Tower 4.0 的 Security OU？
   - A) 每个 OU 都是 Security OU
   - B) 包含服务集成 Account 的 OU 被指定为 Security OU
   - C) Security OU 已被移除
   - D) 其中的每个通用 Account 都会应用所有基线

<details>
<summary>显示答案</summary>

**答案：B) 包含服务集成 Account 的 OU 被指定为 Security OU**

**说明：**
集成 Account 共用一个父 OU，并通过 landing zone 进行管理。AWSControlTowerBaseline/ConfigBaseline 不适用于该 Security OU。将通用运维 Account 放在其他位置属于设计选择。

</details>

---

3. 分层 SCP 组合为什么能节省直接附加配额？
   - A) 文档大小限制会消失
   - B) 继承的策略不会占用子级的直接附加名额
   - C) 子级的允许规则会覆盖父级的拒绝规则
   - D) 根级没有配额限制

<details>
<summary>显示答案</summary>

**答案：B) 继承的策略不会占用子级的直接附加名额**

**说明：**
每个实体的直接附加上限为 10 个 SCP。继承不会占用这些名额，但父级策略仍会施加有效限制。

</details>

---

4. 哪项说法正确描述了 RCP 附加与继承？
   - A) 它们会直接授予权限
   - B) 它们不能继承
   - C) RCPFullAWSAccess 会占用五个名额之一；应同时规划剩余直接名额和继承关系
   - D) 它们的大小限制与 SCP 相同

<details>
<summary>显示答案</summary>

**答案：C) RCPFullAWSAccess 会占用五个名额之一；应同时规划剩余直接名额和继承关系**

**说明：**
还剩四个直接附加名额，文档上限为 5,120 个字符。此预算并不禁止分层继承。请检查受支持的资源和主体例外。

</details>
