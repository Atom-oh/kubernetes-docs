# 第 11 部分：BGP 控制平面、负载均衡器 IP 和出站流量测验

> **Cilium 1.20.2 · 2026-10-15**

1. **使用 ENI IPAM 的 EKS 集群中，`CiliumBGPAdvertisement` 的 `PodCIDR` 类型会起什么作用？**
   - A) 将每个 ENI 辅助 IP 都作为 `/32` 路由通告给对等节点
   - B) 将路由写入 VPC 路由表
   - C) 从每个节点通告 VPC CIDR
   - D) 没有实际作用：ENI IPAM 不会为节点分配 Cilium 管理的 PodCIDR，因此没有可通告的节点级前缀

   <details>
   <summary>显示答案</summary>

   **答案**：D) 没有实际作用：ENI IPAM 不会为节点分配 Cilium 管理的 PodCIDR，因此没有可通告的节点级前缀

   `PodCIDR` 通告仅适用于会为每个节点分配 PodCIDR 的 IPAM 模式（cluster-pool、Kubernetes host scope）。使用 ENI 时，Pod IP 已经是由 VPC 路由的 VPC 地址；BGP Control Plane 不会配置云端路由表。

   </details>

2. **`CiliumBGPPeerConfig` 如何选择要向对等节点发送哪些通告？**
   - A) 通过 `families[].advertisements`，使用标签选择器匹配 `CiliumBGPAdvertisement` 对象的 `metadata.labels`
   - B) 通过 peer 的 `families` 条目匹配 `advertisementType`
   - C) 在 `peerConfigRef` 中列出通告名称
   - D) 使用节点上的注释

   <details>
   <summary>显示答案</summary>

   **答案**：A) 通过 `families[].advertisements`，使用标签选择器匹配 `CiliumBGPAdvertisement` 对象的 `metadata.labels`

   ClusterConfig 通过名称关联 PeerConfig；PeerConfig 则通过通告对象上的标签来关联通告。如果没有匹配的通告，会话仍会建立，但不会通告任何路由。

   </details>

3. **一个 `LoadBalancer` Service 使用 BGP 通告，且 `externalTrafficPolicy: Local`。该 Service 的 VIP 会从哪些节点通告？**
   - A) 仅从持有该 Service 租约的节点通告
   - B) 从集群配置选中的所有节点通告
   - C) 仅从至少有一个本地就绪后端的节点通告；路由随 Pod 所在位置变化
   - D) 仅从控制平面节点通告

   <details>
   <summary>显示答案</summary>

   **答案**：C) 仅从至少有一个本地就绪后端的节点通告；路由随 Pod 所在位置变化

   使用 `Cluster` 时，VIP 会从所有选定节点通告。使用 `Local` 时，没有本地就绪端点的节点会撤回路由。租约属于 L2 announcement，不属于 BGP。

   </details>

4. **从 Cilium 1.19 升级到 1.20 后，Grafana 中 BGP 会话面板为空。可能是什么变更导致？**
   - A) BGP 指标迁移到了 Operator
   - B) 每实例标签从 `vrouter` 改为 `instance_name`，而 1.20 升级说明没有提及此事
   - C) 除非设置 `bgpControlPlane.metrics.enabled`，否则 BGP 指标会被禁用
   - D) 指标前缀从 `cilium_` 改为 `bgp_`

   <details>
   <summary>显示答案</summary>

   **答案**：B) 每实例标签从 `vrouter` 改为 `instance_name`，而 1.20 升级说明没有提及此事

   1.19.8 指标文档使用 `vrouter`；1.20.2 使用 `instance_name`。筛选旧标签的查询和告警会静默地停止匹配。

   </details>

5. **两个 `CiliumBGPAdvertisement` 对象同时匹配同一个 Service，但设置了不同的 communities 和 `localPreference` 值（Cilium 1.18 及之后版本）。会通告什么？**
   - A) 合并 communities，并采用最大的 `localPreference`
   - B) 应用最后一个通告对象的属性
   - C) 仅应用按字母顺序最先的通告对象
   - D) 因冲突而撤回路由

   <details>
   <summary>显示答案</summary>

   **答案**：A) 合并 communities，并采用最大的 `localPreference`

   1.18 之前的行为是“最后匹配优先”。还要记住，`localPreference` 只会发送给 iBGP 对等节点。

   </details>

6. **v1 `CiliumBGPPeeringPolicy` 及其控制平面在哪个版本中移除？**
   - A) 1.18
   - B) 1.20
   - C) 1.21
   - D) 1.19

   <details>
   <summary>显示答案</summary>

   **答案**：D) 1.19

   它在 1.18 中弃用，并于 1.19 与 `pkg/bgpv1` 一同移除，因此集群必须在升级到 1.19 前迁移到 `cilium.io/v2` CRD。v2alpha1 版 v2 CRD 在 1.20 和 1.21-pre 中仍提供服务，但已弃用。

   </details>

7. **在 Cilium 1.20 的多跳 BGP 会话中，如何实现快速故障检测？**
   - A) 在 `CiliumBGPPeerConfig.spec.bfd` 中启用 BFD
   - B) 不支持 BFD；降低 hold 和 keepalive 计时器（CRD 最低值分别为 3 和 1），并为 Agent 重启使用 Graceful Restart
   - C) 将 `ebgpMultihop` 设为 255，以启用快速故障切换
   - D) 设置 `connectRetryTimeSeconds: 1`

   <details>
   <summary>显示答案</summary>

   **答案**：B) 不支持 BFD；降低 hold 和 keepalive 计时器（CRD 最低值分别为 3 和 1），并为 Agent 重启使用 Graceful Restart

   从 1.18 到 1.21-pre 的 CRD 中都没有 BFD 字段。常见的 9/3 计时器是建议使用的激进设置，不是 CRD 最低值。`ebgpMultihop` 只设置 TTL；connect-retry 影响重新连接，而非故障检测。

   </details>

8. **现有 `TLSRoute` 对象使用 `v1alpha2`，你计划升级到 Cilium 1.20（Gateway API v1.6.1）。需要做什么？**
   - A) 无需操作；standard channel CRD 会自动转换对象
   - B) 删除 TLSRoute，并在升级后重新创建
   - C) 备份 TLSRoute，并在升级 Cilium 前安装仍包含 `v1alpha2` 的 experimental channel v1.6.1 TLSRoute CRD
   - D) 仅安装 standard channel v1.6 TLSRoute CRD，它会保留所有版本

   <details>
   <summary>显示答案</summary>

   **答案**：C) 备份 TLSRoute，并在升级 Cilium 前安装仍包含 `v1alpha2` 的 experimental channel v1.6.1 TLSRoute CRD

   安装 standard channel v1.6 TLSRoute CRD 后，已存储的 `v1alpha2` 对象将无法读取，因此看起来会消失。

   </details>

9. **使用默认的 L2 announcement 租约设置（持续 15 秒、续期截止时间 5 秒、重试 2 秒）时，故障切换窗口约为多长？**
   - A) 2 到 4 秒
   - B) 正好 15 秒
   - C) 30 到 60 秒
   - D) 10 到 20 秒

   <details>
   <summary>显示答案</summary>

   **答案**：D) 10 到 20 秒

   故障切换时间介于 `leaseDuration - leaseRenewDeadline` 和 `leaseDuration + leaseRenewDeadline` 之间。调成 3s/1s/200ms 可缩短到 2 到 4 秒，但会增加 API QPS，因此应提高客户端速率限制。

   </details>

10. **`CiliumEgressGatewayPolicy` 的 `egressGateway.nodeSelector` 未匹配任何节点时，被选中的 Pod 发往目标 CIDR 的流量会怎样？**
    - A) 被丢弃
    - B) 经由随机节点发送
    - C) 回退为普通节点 masquerade
    - D) 排队等待网关出现

    <details>
    <summary>显示答案</summary>

    **答案**：A) 被丢弃

    在 1.20.2 和 1.21.0-pre.3 中，Egress Gateway 都没有基于健康状况的故障切换或回退机制。如果没有匹配的网关，发往目标 CIDR 的流量会被丢弃。

    </details>
