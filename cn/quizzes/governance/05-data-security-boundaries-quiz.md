# 数据与安全边界测验

> 本测验用于检查你对[数据与安全边界](../../governance/05-data-security-boundaries.md)的理解。

---

1. 无法共享 Multi-AZ DB 集群快照意味着什么？
   - A) 所有恢复路径都不可行
   - B) 这条 RDS 共享路径不可用；应验证针对具体引擎的恢复替代方案
   - C) 必须使用工作负载自有的数据库
   - D) 所有 AWS Backup 保管库的行为都相同

<details>
<summary>显示答案</summary>

**答案：B) 这条 RDS 共享路径不可用；应验证针对具体引擎的恢复替代方案**

**说明：**
一项 API 限制并不意味着所有逻辑备份或复制替代方案都不可行。选择所有权模式前，请验证支持情况以及 RTO/RPO。

</details>

---

2. 对于需要在事故发生后复制的恢复路径，RTO 应包含什么？
   - A) 仅标签命名
   - B) 复制、还原和应用程序验证所需的时间
   - C) 仅历史保留时间
   - D) 仅 Security Hub 评分

<details>
<summary>显示答案</summary>

**答案：B) 复制、还原和应用程序验证所需的时间**

**说明：**
对于预先创建的副本，复制频率会影响 RPO。应区分无需接收方副本的共享隔离保管库还原路径。

</details>

---

3. 启用跨账户备份后，哪项授权相关说法正确？
   - A) 所有用户都会绕过 IAM 拒绝规则
   - B) 应一并审查 IAM、保管库、KMS、复制目标条件和 RAM 共享设置
   - C) 保管库会变为公开状态
   - D) 组织退出时会删除已复制的备份

<details>
<summary>显示答案</summary>

**答案：B) 应一并审查 IAM、保管库、KMS、复制目标条件和 RAM 共享设置**

**说明：**
启用功能并不会自动授予权限。标准保管库复制与隔离保管库共享是不同的路径；请测试批准的目标以及源不可用的情况。

</details>

---

4. Security Hub CSPM 依赖 Config 意味着什么？
   - A) 所有控制项都可以在没有 Config 的情况下工作
   - B) 大多数 CSPM 控制项需要启用记录；这不是 Identity Center 的服务依赖
   - C) 它会取代 GuardDuty
   - D) 每次 AWS MCP 请求都需要 Config

<details>
<summary>显示答案</summary>

**答案：B) 大多数 CSPM 控制项需要启用记录；这不是 Identity Center 的服务依赖**

**说明：**
应区分由 Control Tower 管理的基线依赖与 Identity Center 服务要求。请检查 Security Hub 的能力范围和 Region 覆盖情况。

</details>
