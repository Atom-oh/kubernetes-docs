# 深度防御与事件响应测验

> **最后更新**：2026 年 10 月 15 日

[阅读章节和一手资料](../../security/13-defense-in-depth-incident-response.md)

### 1. 除了公共 WAF 覆盖范围外，CVE-2025-1974 还要求检查哪条路径？

- A) Pod 网络可访问的准入 Webhook
- B) 仅 CloudFront 查看者路径
- C) 仅数据库存储加密
- D) 仅 DNS 缓存大小

<details>
<summary>显示答案</summary>

**答案**：A) Pod 网络可访问的准入 Webhook

**说明**：检查 Webhook 的可达性和控制器对 Secret 的权限。历史上修复过的版本并不能改变 ingress-nginx 后续退役这一事实。

</details>

### 2. ingress-nginx 退役对 2026 年的新设计意味着什么？

- A) 历史上的 CVE 修复可以永久满足要求
- B) 规划迁移到仍受维护的实现
- C) WAF 能保证控制器未来持续获得补丁
- D) 禁用所有 Kubernetes Webhook

<details>
<summary>显示答案</summary>

**答案**：B) 规划迁移到仍受维护的实现

**说明**：退役后，ingress-nginx 不会再收到安全版本更新。应检查维护状态并规划迁移，而不能只关注过去应用的补丁。

</details>

### 3. PAN-OS CVE-2026-0322 的受影响范围是什么？

- A) 所有 Palo Alto 产品，无一例外
- B) 仅未通过身份验证的互联网用户
- C) 列出的产品系列中，经过身份验证的管理接口 RCE
- D) WAF 请求正文大小问题

<details>
<summary>显示答案</summary>

**答案**：C) 列出的产品系列中，经过身份验证的管理接口 RCE

**说明**：该公告涉及 PA-Series、VM-Series 和 Panorama；此问题不涉及 Cloud NGFW/Prisma Access。凭证和管理接口可达性都很重要。

</details>

### 4. 应如何体现 Fortinet 1 月 28 日的更正？

- A) 所有 SAML IdP 都受影响
- B) Fortinet 产品均未受影响
- C) 所有 SSO 问题的范围都相同
- D) 第三方 SAML IdP/FortiAuthenticator 不在指定问题的受影响范围内

<details>
<summary>显示答案</summary>

**答案**：D) 第三方 SAML IdP/FortiAuthenticator 不在指定问题的受影响范围内

**说明**：应采用修订后的范围，而不是最初更宽泛的 SAML 说法。仍需检查 FortiCloud SSO 是否受影响。

</details>

### 5. 仅将选定流量经 TGW 集中检查，能自动覆盖哪类流量？

- A) 所有同节点 Pod 流量
- B) 每个 PrivateLink 连接
- C) 所有其他对等互连路由
- D) 仅实际经过该检查路径路由的流量

<details>
<summary>显示答案</summary>

**答案**：D) 仅实际经过该检查路径路由的流量

**说明**：应分别盘点本地、端点、对等互连和 IPv6 路径；仍需使用互补的 CNI、IAM、安全组和应用控制。

</details>

### 6. 补丁安装完成和入侵清除之间有什么区别？

- A) 仅看重启时间戳
- B) 是否有未经授权的账户/设置、持久化访问和泄露的 Secret 等证据
- C) 目标当前健康即可
- D) 版本字符串较新即可

<details>
<summary>显示答案</summary>

**答案**：B) 是否有未经授权的账户/设置、持久化访问和泄露的 Secret 等证据

**说明**：打补丁后仍可能存在持久化访问。应按照供应商指南调查并恢复配置、账户和相关凭证。

</details>

### 7. 单凭 WAF 拦截数为零能证明什么？

- A) 每个请求都安全
- B) 所有路由都已检查
- C) 既不能证明完全安全，也不能证明路径覆盖有效
- D) 管理员凭证没有被盗

<details>
<summary>显示答案</summary>

**答案**：C) 既不能证明完全安全，也不能证明路径覆盖有效

**说明**：应关联检查关联关系、操作、无害的测试请求、源站限制和应用记录。拦截数为零也可能是因为覆盖缺失。

</details>

### 8. 哪种拟议的恢复验收证据最有力？

- A) 仅检查版本
- B) 设备截图
- C) 一次成功登录
- D) 干净的配置/凭证，加上业务、拒绝路径和日志复测

<details>
<summary>显示答案</summary>

**答案**：D) 干净的配置/凭证，加上业务、拒绝路径和日志复测

**说明**：应将清除入侵的证据与合法功能、受限的管理访问、流量检查和已恢复的可观测性结合起来。

</details>
