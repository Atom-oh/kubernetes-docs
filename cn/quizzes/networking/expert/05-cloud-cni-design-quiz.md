# 云网络与 CNI 设计测验

[练习手册](../../../networking/expert/05-cloud-cni-design.md)

1. DNS 可以解析，但 TCP 连接失败。接下来应采取什么措施？

   - A) 仅凭 DNS 就宣布后端健康
   - B) 检查实际目标、端口、路由、控制策略和监听器
   - C) 放开所有安全组
   - D) 断定资源不存在

<details>
<summary>显示答案</summary>

**答案：B**

**解释：**DNS 只能提供名称解析证据。TCP 和 HTTP 需要分别检查路径、策略和应用层证据。

</details>

2. 什么是 AWS Load Balancer Controller？

   - A) 每个 HTTP 请求都会经过的数据平面
   - B) 每个 Pod 的默认网关
   - C) 使用 AWS API 管理负载均衡器资源的控制平面协调器
   - D) DNS 缓存本身

<details>
<summary>显示答案</summary>

**答案：C**

**解释：**请求会经过负载均衡器及其实际目标。应将控制器状态与数据平面通信分开调查。

</details>

3. EndpointSlice 显示就绪，但负载均衡器目标不健康。应如何理解？

   - A) 对照注册信息、端口、健康检查条件和网络路径，因为这些状态可能不同
   - B) 这不可能，因为二者含义相同
   - C) 修改 DNS TTL 总能解决问题
   - D) 删除 EndpointSlice

<details>
<summary>显示答案</summary>

**答案：A**

**解释：**就绪状态和负载均衡器健康检查由不同的观察方依据不同条件判定。应将每个端点地址与其条件及实际目标对应起来核查。

</details>

4. NetworkPolicy 对象存在时，还需要检查什么？

   - A) 无需检查；对象存在就能证明策略已执行
   - B) 将每个 Pod 都迁移到 hostNetwork
   - C) 获得每个 AWS 账户的管理员权限
   - D) 选中的 Pod、流量方向、API 支持、引擎启用状态和实际流量证据

<details>
<summary>显示答案</summary>

**答案：D**

**解释：**对象列表不能保证 Pod 被选中或策略得到执行。其他托管策略或 CRD 也可能同时生效。

</details>

5. 关于 TGW，哪种说法正确？

   - A) 两者都是同一条防火墙规则
   - B) Association 用于选择 attachment 查询路由的表；Propagation 用于指定哪些表会学习路由
   - C) Propagation 总会使 attachment 使用该路由表
   - D) 一个 attachment 会与所有路由表关联

<details>
<summary>显示答案</summary>

**答案：B**

**解释：**一个 attachment 会与一张表关联，也可以向多张表传播路由。应分别检查路由查询方向和返回路径。

</details>

6. 查询返回 AccessDenied，且无法获取端点信息。应如何记录结果？

   - A) 流量拒绝已成功验证
   - B) 自动附加管理员策略
   - C) 证据不可用；应申请获批的最小权限或获取已提供的证据
   - D) 后端不存在

<details>
<summary>显示答案</summary>

**答案：C**

**解释：**权限错误不代表资源或网络状态。不要把未知状态改写成允许、拒绝或不存在。

</details>

7. 在数据包路径中，应如何表示 Service ClusterIP？

   - A) 区分逻辑目标选择与实际代理及目标端转发
   - B) 始终将它视为节点后的另一个物理跃点
   - C) 每个以 IP 为目标的请求都必须经过它
   - D) 省略返回路径

<details>
<summary>显示答案</summary>

**答案：A**

**解释：**转发取决于目标类型、代理实现和策略。把对象关系当成必经的数据包路径会扭曲问题诊断。

</details>

8. 如果只审查了混合网络路由设计，没有访问账户，适用哪种完成状态？

   - A) 已验证实时故障转移
   - B) 性能有保证
   - C) 所有策略均已执行
   - D) 设计审查已完成；实时观测尚未验证

<details>
<summary>显示答案</summary>

**答案：D**

**解释：**设计审查、已提供证据的分析和实际实验属于不同的证据等级。结论范围应与实际执行的工作一致。

</details>
