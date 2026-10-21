# 无 SNAT 和 PrivateLink 下的 Pod 连通性测验

> **最后更新**：2026 年 10 月 19 日

[学习指南：验证无 SNAT 和 PrivateLink 下的 Pod 连通性](../../eks-hybrid-nodes/12-connectivity-validation.md)

1. AWS 为 EKS Hybrid Nodes 支持哪种 Cilium 网络模式？
   - A) 仅原生路由
   - B) 仅 VXLAN 封装
   - C) VXLAN 和原生路由均支持

<details>
<summary>显示答案</summary>

**答案：B) 仅 VXLAN 封装**

**说明：**
“为混合节点配置 CNI”中的“支持的功能”表将 VXLAN 封装列为网络模式。原生路由不在支持范围内，而且 Hybrid Nodes Gateway 需要 VTEP（VXLAN），因此不能与原生路由一起使用。

</details>

2. 保留 VXLAN，禁用伪装，并通过 Cilium BGP 通告 Pod CIDR。防火墙在哪个网段上仍无法看到 Pod IP？
   - A) 云端 Pod 与本地部署 Pod 之间
   - B) 到 Kubernetes 之外的本地部署服务器的流量
   - C) 混合节点之间

<details>
<summary>显示答案</summary>

**答案：C) 混合节点之间**

**说明：**
混合节点之间的流量通过 VXLAN 封装，外层标头携带节点 IP。关闭伪装后，离开集群的流量会保留 Pod IP。

</details>

3. 切换到原生路由后，云端 Pod 调用本地部署服务器时，该服务器看到的是云端节点 IP。你首先会检查什么？
   - A) VPC CNI 的 `AWS_VPC_K8S_CNI_EXCLUDE_SNAT_CIDRS` 是否包含本地部署节点范围
   - B) Cilium 的 `enableIPv4Masquerade` 值
   - C) TGW 路由表中的默认路由

<details>
<summary>显示答案</summary>

**答案：A) VPC CNI 的 `AWS_VPC_K8S_CNI_EXCLUDE_SNAT_CIDRS` 是否包含本地部署节点范围**

**说明：**
云端 Pod 的 SNAT 由 VPC CNI 而非 Cilium 执行。如果排除列表中只有 Pod 范围（172.17.0.0/16），而没有本地部署节点范围（172.18.0.0/16），发往本地部署服务器的流量就会被转换为节点 IP。

</details>

4. 只有 hostNetwork Pod 无法解析集群 Service 名称；普通混合 Pod 则正常。最可能的原因是什么？
   - A) CoreDNS 未运行在混合节点上
   - B) hostNetwork Pod 使用节点 IP 访问 CoreDNS，而集群 SG 未允许来自节点范围的 53 端口流量
   - C) hostNetwork Pod 无法使用 DNS

<details>
<summary>显示答案</summary>

**答案：B) hostNetwork Pod 使用节点 IP 访问 CoreDNS，而集群 SG 未允许来自节点范围的 53 端口流量**

**说明：**
普通 Pod 使用其 Pod IP（172.17.x）发出流量；hostNetwork Pod 则使用节点 IP（172.18.x）发出流量。在集群 SG 中允许来自 `172.18.0.0/16` 的 UDP 和 TCP 53 端口流量。还必须设置 `dnsPolicy: ClusterFirstWithHostNet`。

</details>

5. 本地部署 Pod 应通过私有路径访问 S3。以下哪项说法正确？
   - A) S3 网关端点也可从本地部署环境访问。
   - B) 需要 S3 接口端点；在没有网关端点的情况下，测试必须将 `DnsOptions` 设为 `AllResolvers`。
   - C) S3 不支持 PrivateLink。

<details>
<summary>显示答案</summary>

**答案：B) 需要 S3 接口端点；在没有网关端点的情况下，测试必须将 `DnsOptions` 设为 `AllResolvers`。**

**说明：**
本地部署环境无法使用网关端点。在测试中，首次创建时未设置 `PrivateDnsOnlyForInboundResolverEndpoint`，因此失败，并提示 VPC 必须具有网关端点。

</details>

6. 端点 SG 仅允许来自 `172.17.0.0/16`（Pod 范围）的 TCP 443 流量。同一混合节点上的普通 Pod 和 hostNetwork Pod 调用 STS 端点时会发生什么？
   - A) 两者都成功。
   - B) 两者都失败。
   - C) 普通 Pod 成功，hostNetwork Pod 超时。

<details>
<summary>显示答案</summary>

**答案：C) 普通 Pod 成功，hostNetwork Pod 超时。**

**说明：**
不进行 SNAT 时，普通 Pod 的源地址是其 Pod IP，而 hostNetwork Pod 的源地址是节点 IP（172.18.x）。因此，AWS 侧的安全组可以根据 Pod 范围区分本地部署 Pod。

</details>

7. 在 Kubernetes 1.36、Cilium 1.18 的混合模式集群测试中，哪项 kube-dns Service 设置可确保链路中断时混合 Pod 继续使用本地部署的 CoreDNS？
   - A) `trafficDistribution: PreferClose`
   - B) `externalTrafficPolicy: Local`
   - C) `sessionAffinity: ClientIP`

<details>
<summary>显示答案</summary>

**答案：A) `trafficDistribution: PreferClose`**

**说明：**
混合节点上的 ClusterIP 负载均衡由 Cilium BPF 执行，而经测试的 Cilium 1.18.13 会忽略 `PreferSameZone`。AWS 文档中的示例也使用 `PreferClose`。该值自 Kubernetes 1.35 起已被弃用为别名，但在此处只有它能正常工作。还需要在节点加入集群时设置区域标签、确保每个区域都有 CoreDNS，并启用 Cilium 的 `loadBalancer.serviceTopology: true`。

</details>
