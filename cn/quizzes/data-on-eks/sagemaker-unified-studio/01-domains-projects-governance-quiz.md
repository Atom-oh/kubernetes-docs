# Unified Studio 域与项目治理测验

## 选择题

1. 哪项说法正确描述了项目配置文件？

   - A) 它只选择 GPU 驱动程序
   - B) 它组合蓝图，并配置创建时或按需使用的工具
   - C) 所有功能都能保证每个工具立即就绪
   - D) 它取代所有 IAM 权限

<details>
<summary>显示答案</summary>

**答案：B**

请验证预期的配置文件 ID、域类型以及所需的蓝图/账户/区域。

</details>

2. IAM DeleteProject 权限和普通贡献者成员资格是否能保证项目可删除？

   - A) 总是可以
   - B) 不可以；请验证删除路径所需的所有者/管理员权限以及其他 IAM/服务策略
   - C) 可以，只要 EKS 命名空间匹配
   - D) 可以，只要项目名称唯一

<details>
<summary>显示答案</summary>

**答案：B**

项目所有权、API 授权以及实际数据/资源权限是彼此独立的边界。

</details>

3. 应如何理解 projectStatus=ACTIVE？

   - A) 每个环境和 GPU 工具都已就绪
   - B) 这表示项目状态；还应单独检查所需的 environmentDeploymentDetails 和工具访问权限
   - C) 所有按需功能都已经配置好
   - D) 训练已成功

<details>
<summary>显示答案</summary>

**答案：B**

应区分有意尚未配置的按需工具与实际故障。

</details>

4. CreateProject 的 membershipAssignments 成员中应包含什么？

   - A) 始终同时包含 userIdentifier 和 groupIdentifier
   - B) 根据预期的配置文件，恰好包含一个 userIdentifier 或 groupIdentifier
   - C) IAM 密钥
   - D) 用任意 IAM 角色 ARN 代替组配置文件 ID

<details>
<summary>显示答案</summary>

**答案：B**

这是一个带标签的联合类型。在同一请求中分配成员并不保证所有环境配置失败都会原子回滚；请验证执行结果。

</details>

5. 如何验证剩余项目是否已删除？

   - A) 将 AccessDenied 视为资源不存在
   - B) 检查授权的 get/list 范围、域、筛选条件/分页以及自有资源清单
   - C) 9 月初的记录可以证明当前状态
   - D) 标签处理失败后，删除所有名称前缀相同的共享存储桶/角色

<details>
<summary>显示答案</summary>

**答案：B**

历史记录不能代替当前验证。清理必须遵循本次运行的资源所有权和保留策略。

</details>

---

[返回学习材料](../../../data-on-eks/sagemaker-unified-studio/01-domains-projects-governance.md)
