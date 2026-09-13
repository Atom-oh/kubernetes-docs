# Istio 比较测验

> **历史报告**：Istio 1.30.2 / EKS 1.36.2；不是当前支持矩阵
> **最后更新**：2026 年 9 月 11 日

本测验检验您对 Sidecar 与 Ambient 模式选择标准的理解，尤其是报告中 EKS 测量的局限。审计未重现这些实验。

## 选择题（1-6）

### 问题 1：Ambient waypoint 503 的证据

仅根据汇总的滚动发布计数，对于报告中 waypoint 503 的原因可得出什么结论？

A. 已证实重复 IP 分配

B. 连接生命周期竞争是一种假设；确定原因需要代理响应标志及端点/连接时间线

C. 已证实所有失败均由 NetworkPolicy 导致

D. 计数证明不支持 STRICT mTLS

<details>
<summary>答案和解释</summary>

**答案：B**

**解释：**

汇总 HTTP 状态计数不能确立根因。Pod 终止、端点传播、应用/代理排空、超时和连接池都可能参与其中。原始 IP 复用/ztunnel 通知解释没有保留的诊断时间线支撑。应调查实际上游主机、响应标志、Pod UID 和连接事件，不要将假设作为已证明机制讲授。

**参考资料：**

- [Sidecar 与 Ambient 模式选择指南](../../../service-mesh/istio/comparison/03-sidecar-vs-ambient.md)
- [Ambient 模式：Waypoint 代理](../../../service-mesh/istio/advanced/01-ambient-mode.md)

</details>

---

### 问题 2：解释报告中的 EKS 结果

未调优样本中，Sidecar 的 60,000 次调用记录 324 个 HTTP 503 和 2 个非 HTTP 错误；Ambient L4 的 60,000 次调用分别为 0 和 195；Ambient L7 的 59,913 次调用分别为 1,528 和 84。哪种解释得到支持？

A. Ambient 总是更稳定

B. L7 样本观察到的 HTTP 503 比例更高，而 L4 虽无 HTTP 503，仍有 195 次非 HTTP 失败

C. 已证实所有错误类别具有相同底层原因

D. Fortio SocketCount 直接测量 waypoint 上游连接池

<details>
<summary>答案和解释</summary>

**答案：B**

**解释：**

实测比例为 Sidecar 0.54%、L7 约 2.55%，这些样本中的比值约 4.72。这不是产品固有倍数。HTTP 503 为零不等于总失败为零。没有错误详情，Fortio 非 HTTP 状态码 -1 不能识别具体重置/EOF/超时原因。SocketCount 关乎客户端套接字；L7 套接字最多（2,486），不是 L4（1,652）。请求 QPS 乘以时长不保证精确完成调用数，且不同滚动发布次数限制因果比较。

**参考资料：**

- [Sidecar 与 Ambient 模式选择指南：零停机滚动发布结果](../../../service-mesh/istio/comparison/03-sidecar-vs-ambient.md)

</details>

---

### 问题 3：NetworkPolicy 和 Ambient

报告中的 VPC CNI 实验已验证策略执行，仅允许 8080 的入站规则阻止了观察到的 HBONE 路径。接下来应检查什么？

A. 移除所有 NetworkPolicy

B. 在适当范围内允许所需 TCP 15008 隧道路径，再验证来源、身份和内部端口策略边界

C. 将 mTLS 改为 PERMISSIVE

D. 重启 CNI 并假定策略正确

<details>
<summary>答案和解释</summary>

**答案：B**

**解释：**

报告流量在允许 TCP 15008 后恢复。这是该测试路径的证据，不证明所有 CNI 或现有策略行为相同。允许外层隧道不是隧道内部流量的完整最小权限策略。验证来源选择器、waypoint 遍历、DNS/控制平面依赖及实际执行。Sidecar 观察到的应用端口结果同样是限定范围观测。

**参考资料：**

- [Sidecar 与 Ambient 模式选择指南：NetworkPolicy](../../../service-mesh/istio/comparison/03-sidecar-vs-ambient.md)

</details>

---

### 问题 4：非幂等 API 和重试

为什么创建订单等非幂等命令路径应默认显式禁用网格重试？

A. 重试总比应用消耗更多 CPU

B. 响应失败或丢失可能使服务器端结果未知，重放可能重复已提交命令

C. 重试与 STRICT mTLS 不兼容

D. Ambient 没有 L7 重试能力

<details>
<summary>答案和解释</summary>

**答案：B**

**解释：**

超时、重置或错误响应不总能证明命令未生效。除非服务器提供合适的持久幂等性/事务语义，否则重放结果不明的写入可能重复工作。此风险不取决于能否证明某个特定 waypoint 竞争。旧 T2 报告的零重复计数不能确立安全性，甚至不能给出可靠频率估计：客户端无界、报告计数与所述时长/速率冲突，观测器错误可能被隐藏。修订后的有界观测器仍不是业务事务台账。应以完整观测测量稳定命令 ID 和响应丢失情况。

**参考资料：**

- [Sidecar 与 Ambient 模式选择指南：以重试缓解问题的风险](../../../service-mesh/istio/comparison/03-sidecar-vs-ambient.md)

</details>

---

### 问题 5：公平比较数据平面行为

要区分原始失败与被重试隐藏的失败，哪个实验是必要起点？

A. 仅比较最终 GET 成功数

B. 保留 Sidecar 重试但禁用 Ambient 重试

C. 两种模式的写入路由都设为 attempts: 0，收集原始 HTTP/非 HTTP 错误、重试计数器、上游交付及最终结果

D. 选择平均 CPU 最低的模式

<details>
<summary>答案和解释</summary>

**答案：C**

**解释：**

Sidecar 和 waypoint Envoy 可执行 L7 重试；ztunnel 不能解释 HTTP 503 或重放 HTTP 请求。以相同方式禁用写入重试，并记录 upstream_rq_retry、实际交付、稳定命令 ID 和客户端记账。同时控制负载、版本、资源和滚动发布暴露，重复实验。这可更公平地区分观测；单次运行仍不能证明产品固有稳定性。

**参考资料：**

- [Sidecar 与 Ambient 模式选择指南：原始失败测量](../../../service-mesh/istio/comparison/03-sidecar-vs-ambient.md)
- [重试和超时](../../../service-mesh/istio/traffic-management/05-retry-timeout.md)

</details>

---

### 问题 6：Cilium 身份验证和加密

对于 Cilium 文档中的带外双向身份验证机制，将 authentication 设为 required 意味着什么？

A. 每个载荷自动使用工作负载 TLS

B. 带外对等身份握手与载荷加密独立；加密必须单独配置和验证

C. 它在实现和成熟度上与 Istio PeerAuthentication STRICT 完全相同

D. 不再需要授权策略

<details>
<summary>答案和解释</summary>

**答案：B**

**解释：**

发布的 Cilium 1.20.1 文档将此机制标为 Beta，介绍了独立于应用数据路径的带外握手。仅身份验证策略不加密应用载荷。单独评估受支持的 WireGuard/IPsec 加密，包括平台和流量覆盖限制。Cilium 1.20.1 还有独立的 ztunnel 加密 beta，要求命名空间纳管，仅支持 TCP，并有策略/平台限制。此带外身份验证策略设置不会激活它。

**参考资料：**

- [Cilium 服务网格安全](../../../service-mesh/cilium-service-mesh/03-security.md)

</details>

---

## 评分

- 统计 6 道题中答对的数量。
- 6/6：您能依据测量证据解释 Sidecar、Ambient 和 Cilium 选择，以及重试风险。
- 4-5/6：复习原始失败测量或身份验证与加密的区别。
- 0-3/6：从头重读 [Sidecar 与 Ambient 模式选择指南](../../../service-mesh/istio/comparison/03-sidecar-vs-ambient.md)。

## 学习资源

- [Sidecar 与 Ambient 模式选择指南](../../../service-mesh/istio/comparison/03-sidecar-vs-ambient.md)
- [Ambient 模式](../../../service-mesh/istio/advanced/01-ambient-mode.md)
- [mTLS](../../../service-mesh/istio/security/01-mtls.md)
- [Cilium 服务网格安全](../../../service-mesh/cilium-service-mesh/03-security.md)

## 官方证据

- [Istio Ambient L7 功能状态](https://github.com/istio/istio.io/blob/release-1.30/content/en/docs/ambient/usage/l7-features/index.md)
- [Cilium 1.20.1 双向身份验证](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/network/servicemesh/mutual-authentication/mutual-authentication.rst)
