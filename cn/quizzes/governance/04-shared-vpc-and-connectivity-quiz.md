# 共享 VPC 与连接测验

> 本测验用于检查你对[共享 VPC 与连接](../../governance/04-shared-vpc-and-connectivity.md)的理解。

---

1. TGW 路由传播与 VPC 路由表是什么关系？
   - A) 100 个 TGW 前缀是共享 VPC 的固定上限
   - B) TGW 路由不会自动传播；所有者会添加指向 TGW 的 VPC 静态路由
   - C) 所有路由表共用一个配额
   - D) 永远不会先达到 CIDR 配额

<details>
<summary>显示答案</summary>

**答案：B) TGW 路由不会自动传播；所有者会添加指向 TGW 的 VPC 静态路由**

**说明：**
TGW 路由表的合计默认上限为 10,000 条路由；VPC 非传播路由的默认上限为 500 条。不要将 VGW 传播路由的 100 条限制与 TGW 总量混淆。

</details>

---

2. 共享 VPC 参与者无法描述所有者的哪种资源？
   - A) 子网
   - B) 自己的安全组
   - C) NAT Gateway
   - D) 路由表

<details>
<summary>显示答案</summary>

**答案：C) NAT Gateway**

**说明：**
参与者无法描述所有者的 NAT Gateway。集中式清单、日志和委派的只读访问路径仍可提供审计证据。

</details>

---

3. 应如何为共享 VPC 设计 LBC 子网发现？
   - A) 假设每个版本都能成功
   - B) 验证控制器模式、权限和标签可见性；考虑显式指定子网 ID
   - C) 始终由所有者创建 Ingress
   - D) 仅通过 NAT Gateway 发现子网

<details>
<summary>显示答案</summary>

**答案：B) 验证控制器模式、权限和标签可见性；考虑显式指定子网 ID**

**说明：**
所有者的标签不会自动共享。显式指定子网具有可预测性，但这并不能证明每种发现模式都会失败。

</details>

---

4. 哪项说法正确描述了长期运行的 VPC Lattice 连接？
   - A) 服务和资源的生命周期都为 10 分钟
   - B) 区分服务的 10 分钟生命周期与资源 350 秒的空闲超时；测试协议/重新连接行为
   - C) HTTP 侦听器原生支持所有 WebSocket
   - D) 没有任何路径支持长期流量

<details>
<summary>显示答案</summary>

**答案：B) 区分服务的 10 分钟生命周期与资源 350 秒的空闲超时；测试协议/重新连接行为**

**说明：**
资源没有相同的生命周期限制。TLS 侦听器或资源路径可以承载 WebSocket，但仍需满足协议和授权要求。

</details>

---

5. 哪项说法正确描述了 Route 53 Profiles 的 DNS 优先级规则？
   - A) 本地 VPC 规则总是优先于 Profile
   - B) Profile 规则总是优先于本地 VPC
   - C) 名称相同时本地 VPC 优先；如果 Profile 注册了更具体的名称，则 Profile 优先
   - D) 优先级随机决定

<details>
<summary>显示答案</summary>

**答案：C) 名称相同时本地 VPC 优先；如果 Profile 注册了更具体的名称，则 Profile 优先**

**说明：**
例如，如果本地 VPC 有一条 `example.com` 规则，而 Profile 有一条更具体的 `test.example.com` 规则，则使用 Profile 规则。因此建议正式规定：“中央 Profile 不会拥有比委派给工作负载的命名空间更具体的名称。”

</details>
