# 第 12 部分：mTLS、透明加密与身份测验

> **审查基线**：Cilium 1.20.2（稳定版，2026-09-16）；Cilium CLI 0.20.1；Hubble CLI 1.20.2。标记为 **[1.21 预发布版]** 的项目来自 v1.21.0-pre.3，正式发布前可能变化。
> **最后更新**：2026 年 10 月 15 日

[返回指南](../../../networking/cilium/12-mtls-encryption-identity.md)

1. Cilium Mutual Authentication（SPIFFE/SPIRE、`authentication.mode: required`）在 1.20 和 1.21 中分别处于什么状态？
   - A) 在 1.20 中移除，在 1.21 中不存在
   - B) 在 1.20 中为 Beta，在 1.21 中稳定
   - C) 在 1.20 中弃用，在 1.21 中移除
   - D) 在 1.21 中弃用，在 1.22 中移除
<details>
<summary>显示答案</summary>

**答案**：C) 在 1.20 中弃用，在 1.21 中移除

1.20 升级说明将其标为弃用（文档页面标题仍为 “Beta”），并指向 ztunnel。1.21 升级说明表示它在弃用后已移除。策略中的 `authentication` 字段为兼容 CRD 而保留，但在 1.21 中不再使用。

</details>

2. 保留身份 `reserved:world` 的数字 ID 是多少？
   - A) 1
   - B) 6
   - C) 8
   - D) 2
<details>
<summary>显示答案</summary>

**答案**：D) 2

1 是 `host`，2 是 `world`，6 是 `remote-node`，8 是 `ingress`。ID 9 和 10 将 world 拆分为 IPv4 与 IPv6 变体。

</details>

3. 工作负载如何加入 Cilium 的 ztunnel mTLS？
   - A) 为每个 Pod 添加注释 `istio.io/dataplane-mode=ambient`
   - B) 为命名空间添加标签 `io.cilium/mtls-enabled=true`
   - C) 在 CiliumNetworkPolicy 中添加 `authentication.mode: required`
   - D) 为每个 Pod 添加标签 `io.cilium/mtls-enabled=true`
<details>
<summary>显示答案</summary>

**答案**：B) 为命名空间添加标签 `io.cilium/mtls-enabled=true`

启用范围仅限命名空间；不支持在 Pod 级别启用。Istio ambient 标签属于 Istio，而 `authentication.mode` 属于已移除的 Mutual Authentication 机制。

</details>

4. ztunnel 代理之间的 HBONE 流量使用哪个 TCP 端口？对于已加入的工作负载，L4 策略唯一能匹配哪个端口？
   - A) 15008
   - B) 4250
   - C) 15006
   - D) 15001
<details>
<summary>显示答案</summary>

**答案**：A) 15008

流量在离开 Pod 之前已加密，因此 L4 策略看不到内部端口；只有 HBONE 端口 15008 可以作为匹配目标。15001 和 15006 分别是 Pod 内的出站重定向端口和明文入站重定向端口；4250 是已移除的 Mutual Authentication 握手端口。

</details>

5. `encryption.ztunnel.ca.type` 的默认值是什么？
   - A) `spire`
   - B) `istiod`
   - C) `internal`
   - D) `cert-manager`
<details>
<summary>显示答案</summary>

**答案**：C) `internal`

`internal` 使用 Cilium 内置 CA。1.20 新增的 `spire` 会使用外部 SPIRE Server，并由 Operator 为已加入的命名空间注册条目。

</details>

6. Cilium WireGuard 隧道端点在每个节点上使用哪个 UDP 端口？
   - A) 51820
   - B) 51871
   - C) 4789
   - D) 8472
<details>
<summary>显示答案</summary>

**答案**：B) 51871

Cilium 使用 51871，而不是 WireGuard 默认的 51820。节点安全组必须引用节点安全组来允许节点间的 UDP 51871 流量，绝不能使用公共 CIDR。4789 和 8472 是 VXLAN 端口。

</details>

7. 哪个透明加密严格模式选项仅适用于 WireGuard？
   - A) `encryption.strictMode.ingress.enabled`
   - B) `encryption.strictMode.egress.allowRemoteNodeIdentities`
   - C) `encryption.strictMode.egress.enabled`
   - D) `encryption.strictMode.egress.cidr`
<details>
<summary>显示答案</summary>

**答案**：A) `encryption.strictMode.ingress.enabled`

入站严格模式会丢弃未经过 WireGuard 隧道进入的集群内部入站流量，因此不支持 IPsec。旧的扁平标志（`encryption.strictMode.enabled` 等）在 1.20 中被移除，改用 `egress.*` 名称。

</details>

8. 在 IPsec 密钥 Secret 中，什么设置会强制使用每隧道派生密钥？
   - A) 设置 `encryption.ipsec.interface`
   - B) 使用密钥 ID 0
   - C) 启用 `encryption.nodeEncryption`
   - D) 在密钥 ID 后加 `+`，例如 `3+ rfc4106(gcm(aes)) ...`
<details>
<summary>显示答案</summary>

**答案**：D) 在密钥 ID 后加 `+`，例如 `3+ rfc4106(gcm(aes)) ...`

全局密钥在 1.16 中已弃用（GHSA-pwqm-x5x6-5586）。`encryption.ipsec.interface` 在 1.20 中移除，密钥 ID 范围为 1 到 15。

</details>

9. 从 kvstore 迁移身份到 CRD 时，Double Write 的顺序是什么？
   - A) `doublewrite-readkvstore`，然后 `doublewrite-readcrd`，最后 `crd`
   - B) `crd`，然后 `doublewrite-readcrd`，最后 `kvstore`
   - C) `kvstore`，然后 `crd`，最后 `doublewrite-readcrd`
   - D) `doublewrite-readcrd`，然后 `doublewrite-readkvstore`，最后 `crd`
<details>
<summary>显示答案</summary>

**答案**：A) `doublewrite-readkvstore`，然后 `doublewrite-readcrd`，最后 `crd`

整个过程中都会同时写入两个存储；读取路径先从 kvstore 切换到 CRD，然后停止使用 kvstore 作为身份分配后端。每个步骤切换前，都要观察 `cilium_operator_doublewrite_*` 指标，直到 `*_only_identities` 值归零。

</details>

10. 在 Cilium 1.20 中，如果应用的 CiliumNetworkPolicy 既没有 `spec` 也没有 `specs`，会发生什么？
    - A) 策略被接受，Agent 会记录警告
    - B) CEL 验证规则会在准入时拒绝策略
    - C) 策略被接受并视为允许所有流量
    - D) 策略被接受，但不会选择任何端点
<details>
<summary>显示答案</summary>

**答案**：B) CEL 验证规则会在准入时拒绝策略

CRD 包含 `has(self.spec) || has(self.specs)`，并显示消息 “spec or specs must be provided”。除非现有空策略被更新，否则不会影响它们。

</details>
