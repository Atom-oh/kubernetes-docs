# Observability Lab 01 测验

<span id="observability-lab-part-1-infrastructure-setup-quiz"></span>

> **最后更新**: September 13, 2026

1. 应如何使用已评审的 EKS 版本状态？
   - A) 1.31 必然已经不受支持。
   - B) 使用已评审的1.36 标准支持基线，并重新检查当前 Region/支持状态。
   - C) 次要版本会永久受支持。
   - D) kubectl 版本偏差从不重要。

<details>
<summary>显示答案</summary>

**答案：B) 使用已评审的1.36 标准支持基线，并重新检查当前 Region/支持状态。**

区分扩展支持与停止支持，并验证客户端/服务器兼容性。

</details>

---

2. 重用 VPC 时必须检查什么？
   - A) 仅 VPC ID 字符串。
   - B) 子网 AZ、地址容量、路由、DNS/SG 以及不重叠的 Service CIDR。
   - C) 使两个 Service CIDR 相同。
   - D) 永远不需要 NAT/endpoints。

<details>
<summary>显示答案</summary>

**答案：B) 子网 AZ、地址容量、路由、DNS/SG 以及不重叠的 Service CIDR。**

生成器不会创建网络资源，因此实际的连接前提条件仍然存在。

</details>

---

3. 应如何配置公共 API 客户端 CIDR？
   - A) 始终使用0.0.0.0/0。
   - B) 使用与实际源匹配的、经过批准的窄范围。
   - C) 在生产环境中使用任意文档 IP。
   - D) CIDR 本身可替代身份验证。

<details>
<summary>显示答案</summary>

**答案：B) 使用与实际源匹配的、经过批准的窄范围。**

请同时验证私有/公共 endpoints、源地址和身份验证。

</details>

---

4. IRSA 信任约束的关键要素是什么？
   - A) 允许每个 ServiceAccount。
   - B) 正确的 OIDC provider，以及精确的 audience/namespace/ServiceAccount subject。
   - C) 将所有权限授予节点角色。
   - D) 在 Pod 中硬编码 access key。

<details>
<summary>显示答案</summary>

**答案：B) 正确的 OIDC provider，以及精确的 audience/namespace/ServiceAccount subject。**

provider ARN 和 issuer host/path 必须标识同一个 provider。

</details>

---

5. Aurora 的访问边界是什么？
   - A) 向互联网开放的公共 writer。
   - B) 私有子网，以及来自实际服务客户端 SG 的 PostgreSQL5432 访问。
   - C) 相似的 SG 名称就足够了。
   - D) 会自动出现 Multi-AZ writer。

<details>
<summary>显示答案</summary>

**答案：B) 私有子网，以及来自实际服务客户端 SG 的 PostgreSQL5432 访问。**

单个 writer 是实验室选择，而不是 HA 保证。

</details>

---

6. 应用程序应使用哪个 DB 账户？
   - A) 每个 Pod 中都使用 master 账户。
   - B) 使用一个独立的运行时账户，该账户对实验室表具有 DML 访问权限。
   - C) 使用没有密码的公共连接。
   - D) 每次运行时都覆盖现有密码。

<details>
<summary>显示答案</summary>

**答案：B) 使用一个独立的运行时账户，该账户对实验室表具有 DML 访问权限。**

Bootstrap 不会覆盖角色；失败后请验证候选凭证。

</details>

---

7. 应如何提供包含特殊字符的密码？
   - A) 直接拼接到 DSN 中。
   - B) 将原始 JSON 值作为 URL.create 的密码参数传递。
   - C) 重复进行 URL 编码。
   - D) 打印到日志中以便复制。

<details>
<summary>显示答案</summary>

**答案：B) 将原始 JSON 值作为 URL.create 的密码参数传递。**

还请验证 TLS verify-full 和实际的 CA 路径。

</details>

---

8. cluster 创建失败后应执行什么操作？
   - A) 持续创建新名称。
   - B) 检查同一名称下的部分资源、状态和所有权。
   - C) 假设失败后不会产生费用。
   - D) 删除每个 VPC。

<details>
<summary>显示答案</summary>

**答案：B) 检查同一名称下的部分资源、状态和所有权。**

CLI 失败并不能证明未创建任何资源。

</details>

---

9. 检查 gp3 StorageClass 涉及什么？
   - A) 名称匹配就一定能用。
   - B) 检查 EBS CSI、权限、实际的 class 以及 volume 清理。
   - C) 始终覆盖共享 class。
   - D) PVC 和 snapshot 删除是相同的。

<details>
<summary>显示答案</summary>

**答案：B) 检查 EBS CSI、权限、实际的 class 以及 volume 清理。**

区分共享对象更改与资源删除责任。

</details>

---

10. 应如何估算实验室成本？
   - A) 始终为2.5USD每小时。
   - B) 包含实际 Region、使用量、保留期、NAT/LBs/storage/snapshots。
   - C) 将每月 AMG 用户定价视为每小时 workspace 费率。
   - D) NodePool 限制是绝对预算。

<details>
<summary>显示答案</summary>

**答案：B) 包含实际 Region、使用量、保留期、NAT/LBs/storage/snapshots。**

不要声称固定总额或未经测量的节省。

</details>

---

[返回指南](../../../labs/observability/01-infrastructure-setup-lab.md)
