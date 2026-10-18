# Account 结构与 IAM 边界测验

> 本测验用于检查你对 [Account 结构与 IAM 边界](../../governance/02-account-and-iam.md)的理解。

---

1. Identity Center 的 100 个组限制适用于什么范围？
   - A) Organization 中的所有组
   - B) Account 中的所有组
   - C) 分配给某个 Account 中一个权限集的组，或分配给某个应用程序的组
   - D) 同时登录的用户数

<details>
<summary>显示答案</summary>

**答案：C) 分配给某个 Account 中一个权限集的组，或分配给某个应用程序的组**

**说明：**
此限制按权限集/Account 组合计算，而不是跨权限集对整个 Account 求和。它也不会普遍强制要求使用 ABAC。

</details>

---

2. 规划从使用 Shared VPC 的 Account 中拆分出来时，哪些事项很重要？
   - A) 所有资源都会立即删除
   - B) 规划迁移，以满足必须位于同一 Organization 的要求，并考虑取消共享后的创建/替换限制
   - C) RAM 子网会继续与外部 Organization 共享
   - D) EKS 会自动迁移 VPC

<details>
<summary>显示答案</summary>

**答案：B) 规划迁移，以满足必须位于同一 Organization 的要求，并考虑取消共享后的创建/替换限制**

**说明：**
取消共享后，现有资源可能仍会继续运行，但新建资源以及托管服务的扩缩容/替换可能受影响。离开前应准备一条可独立运行的路径。

</details>

---

3. 共享集群如何访问另一个 Account 的 AWS 资源？
   - A) 始终签发 IAM 用户密钥
   - B) 根据情况选择目标角色链、受支持的资源策略或 IRSA
   - C) 为每个工作负载精确创建两个角色
   - D) 编辑 aws-auth 即可授予 AWS 权限

<details>
<summary>显示答案</summary>

**答案：B) 根据情况选择目标角色链、受支持的资源策略或 IRSA**

**说明：**
Pod Identity 主角色必须位于同一 Account，并不意味着每个请求都必须使用目标角色。应区分集群所属的 Account 与仅拥有数据库的 Account。

</details>

---

4. Access Policies 与 Kubernetes RBAC 组合使用时会怎样？
   - A) 仅最新添加的策略生效
   - B) Allow 权限会合并，两者不会互相限制
   - C) 两者不能组合
   - D) RBAC 总是覆盖 Access Policies

<details>
<summary>显示答案</summary>

**答案：B) Allow 权限会合并，两者不会互相限制**

**说明：**
请检查有意授予的权限及其重叠部分。自动化会有所帮助，但它不是 API 的前提条件。

</details>
