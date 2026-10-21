# 在没有 SNAT 的情况下验证 Pod 连通性，以及 PrivateLink

> **支持的版本**：EKS 1.36、Cilium 1.18.13（AWS 构建版）、CoreDNS add-on v1.14.7-eksbuild.10、默认 VPC CNI 配置
> **最后更新**：2026 年 10 月 19 日

有些防火墙必须根据 **Pod IP** 而非节点 IP 来识别本地部署的 Pod。本页记录了对此要求的一次测试：将 Cilium 切换为原生路由并禁用伪装，然后在集群内外运行了 38 项连通性检查。本文还介绍了让本地部署的 Pod 在不经过互联网的情况下调用 AWS API（STS、S3）的 PrivateLink 路径，以及链路中断时 DNS 的行为。

测试环境**模拟本地部署环境**。通过 Transit Gateway (TGW) 连接了第二个 VPC，并将其中的 EC2 实例注册为混合节点。不支持在 EC2 上运行混合节点，且会按混合节点费率计费。这些数据来自 2026 年 10 月 19 日的一次测试。在真实的本地网络上通过 Direct Connect 或 VPN 重新验证这些数据。

## 首先了解支持范围

在[配置混合节点的 CNI](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-cni.html)的“支持的功能”表中，AWS 唯一支持的 Cilium **网络模式是“VXLAN 封装”**。同一页面还说明，可以禁用伪装，但这样一来，Pod CIDR 必须能在本地网络上路由；页面建议使用 Cilium BGP Control Plane 使其可路由。

| 配置 | Pod IP 可见的位置 | AWS 支持 | Hybrid Nodes Gateway |
|---|---|---|---|
| VXLAN + 伪装（默认） | 集群外的任何位置都不可见：显示节点 IP | 支持 | 可用 |
| VXLAN + 关闭伪装 + BGP | 云到本地部署、本地部署服务器 | 支持 | 可用 |
| **原生路由 + 关闭伪装**（本页） | 上述位置，**以及混合节点到混合节点的网段** | **超出支持范围** | 不可用（需要 VTEP，即 VXLAN） |

使用 VXLAN 时，混合节点之间的流量会在外层报头中携带节点 IP，因此该网段上的防火墙无法看到 Pod IP。如何选择取决于你是否也需要在该网段上看到 Pod IP。仍处于支持范围内的第二行已足以满足大多数情况。只有在你有商业版 Cilium 支持或内部专业知识、而非依赖 AWS 支持时，才考虑第三行。

## 配置

### 地址范围

| 范围 | 值 | 备注 |
|---|---|---|
| 云 VPC | `10.0.0.0/16` | 云节点和 Pod（VPC CNI） |
| 远程节点网络 | `172.18.0.0/16` | 模拟的本地部署 VPC（混合节点主机） |
| 远程 Pod 网络 | `172.17.0.0/16` | Cilium 集群池，每个节点 `/25` |
| Service | `172.16.0.0/16` | |

### Cilium 值（叠加在基础值之上）

```yaml
routingMode: native
ipv4NativeRoutingCIDR: "172.17.0.0/16"   # remote pod network
autoDirectNodeRoutes: false              # hosts are in different subnets; the on-prem router forwards
enableIPv4Masquerade: false              # no SNAT
vtep:
  enabled: false                         # no gateway
```

Cilium Chart 在 ConfigMap 变更时不会重启代理（`rollOutCiliumPods` 默认为 `false`），因此更改值后运行 `kubectl -n kube-system rollout restart ds/cilium`。之后检查 `cilium-dbg status` 是否显示 `Routing: Network: Native`。ConfigMap 中仍然包含 `tunnel-protocol: vxlan`，但它没有产生任何影响：在主机 NIC 上抓包显示 VXLAN 数据包（UDP 8472 和 4789）数量为零。

### 路由和 SNAT 例外

| 位置 | 设置 | 原因 |
|---|---|---|
| 本地部署路由器 | 将每个节点的 Pod 网段（`/25`）路由到该节点 | 在生产环境中，使用 Cilium BGP Control Plane 发布路由。测试使用了本地部署 VPC 路由表中的静态路由；节点重新加入并获得不同的 Pod 网段后，这些路由会过时。 |
| 云路由表、TGW | 将 `172.17.0.0/16` 指向本地部署环境 | 返回流量可直接到达 Pod IP |
| VPC CNI | `AWS_VPC_K8S_CNI_EXCLUDE_SNAT_CIDRS=172.17.0.0/16,172.18.0.0/16` | 云 Pod 发往本地部署环境时也保留其 IP。**如果未包含节点范围（172.18），本地部署服务器看到的将是云节点 IP。** |
| 集群安全组 | 允许来自 `172.17.0.0/16` 的所有流量，以及来自 `172.18.0.0/16` 的 UDP/TCP 53 | Pod 流量，以及来自 hostNetwork Pod 的 DNS 流量（这些 Pod 使用节点 IP 调用 CoreDNS） |

## 连通性矩阵结果

每项检查验证的不仅是 HTTP 响应，还包括**服务器记录的源地址**：nginx 访问日志中的 (`$remote_addr`)，或者对于 Kubernetes 外部的服务器，验证回显对端地址的 `socat` 监听器。结果：38 项通过，0 项失败。

| 网段 | 检查项 | 检查内容 | 结果 |
|---|---|---|---|
| Pod 到 Pod，直连 | 7 | 同一混合节点上、混合节点之间、混合节点与云节点双向通信、云节点之间 | 服务器看到的源地址 = 客户端 Pod IP |
| ClusterIP Service | 3 | 混合节点到混合节点后端、混合节点到云后端、云节点到混合节点后端 | kube-proxy 只改写目标地址；保留源 Pod IP |
| DNS | 4 | 从两个混合 Pod 和一个 hostNetwork Pod 查询 Service 名称，以及查询一个公共名称 | 通过 CoreDNS（云节点）和 VPC 解析器解析 |
| Kubernetes API | 2 | `kubernetes.default.svc/livez`、ServiceAccount token | 返回 200 和 403（已通过身份验证，但没有 RBAC 授权） |
| 控制平面到混合节点 | 3 | API server 代理（webhook 路径）、`exec` 和 `logs`、metrics-server | 代理请求来自云 VPC 中由 EKS 管理的 ENI |
| Kubernetes 外部的本地部署服务器 | 2 | 混合 Pod 和云 Pod 访问混合主机上的 `socat` | 服务器收到 172.17.x 和 10.0.x 的 Pod IP |
| 互联网 | 3 | 两个混合 Pod、一个云 Pod | 所有流量都经由唯一的云 NAT 网关离开；这是路径上唯一的地址转换 |
| Cilium 策略 | 3 | 在混合 Pod 上设置 `fromCIDR: 10.0.0.0/16` | 混合 Pod 被阻止，云 Pod 被允许；删除策略后恢复 |
| MTU、大批量传输 | 2 | 双向传输 32 MiB，并比较 sha256 | 匹配。Pod MTU 为 9001，使用 8500 字节数据包的 DF ping 成功 |
| ALB IP 目标 | 1 | 两个混合 Pod | 健康 |
| PrivateLink | 8 | 见下文 | 全部通过 |

可用的 `fromCIDR` 策略也证明了没有 SNAT。云 Pod 使用 VPC CNI，没有 Cilium 身份，因此策略只能通过 IP 范围匹配它们；这只有在 Pod IP 原样到达时才有效。

Pod MTU 为 9001，TGW 限制为 8500。TCP 没有问题，因为 TGW 会限制 MSS。对于没有 MSS 限制的协议（如 UDP），以及 DX 或 VPN 路径，应单独检查路径 MTU。

### 首次运行时的三项失败

| 症状 | 原因 | 修复方法 |
|---|---|---|
| hostNetwork Pod 无法解析 Service 名称 | hostNetwork Pod 使用节点 IP (172.18.x) 调用 CoreDNS，而集群安全组未为该范围配置端口 53 规则 | 在集群安全组中允许来自 `172.18.0.0/16` 的 UDP 和 TCP 53 |
| 本地部署服务器看到的是云 Pod 的节点 IP | VPC CNI 的 SNAT 排除列表包含 Pod 范围，但不包含本地部署节点范围 | 将 `172.18.0.0/16` 添加到 `AWS_VPC_K8S_CNI_EXCLUDE_SNAT_CIDRS` |
| 匿名 `GET /version` 返回 401 | EKS 1.36 只允许匿名请求访问运行状况端点 | 使用 `/livez` 或 `/readyz` 检查连通性 |

## 本地部署 Pod 通过 PrivateLink 调用 AWS API

要让本地部署的 Pod 在调用 AWS API 时不访问互联网，请在云 VPC 中放置接口端点，并通过 DX 或 VPN 访问这些端点。

```
hybrid Pod (172.17.x)
  -> CoreDNS -> VPC resolver: sts.<region>.amazonaws.com and s3.<region>.amazonaws.com resolve to endpoint ENIs (10.0.x)
  -> TGW (DX/VPN in production), source Pod IP preserved
  -> STS and S3 interface endpoints (2 AZs, private DNS)
```

混合 Pod 通过集群 DNS（CoreDNS）和 VPC 解析器解析名称，因此端点的私有 DNS 会直接生效。Kubernetes 外部的本地部署服务器需要配置 [Route 53 Resolver 入站端点](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/resolver-forwarding-inbound-queries.html)，才能获得相同的解析结果。

### 组件

| 组件 | 设置 |
|---|---|
| STS 接口端点 | 启用私有 DNS |
| S3 接口端点 | 启用私有 DNS。**对于没有 S3 网关端点的 VPC，设置 `DnsOptions.PrivateDnsOnlyForInboundResolverEndpoint: AllResolvers`。第一次尝试时未设置该项**，因而失败并提示："To set PrivateDnsOnlyForInboundResolverEndpoint to true, the VPC must have a Gateway endpoint". |
| 端点安全组 | 仅允许来自 `10.0.0.0/16`（VPC）和 `172.17.0.0/16`（混合 Pod）的 TCP 443。特意不包括节点范围 `172.18.0.0/16` |
| IAM | 集群 OIDC 提供商，以及绑定到 ServiceAccount 的角色 (IRSA) |
| 存储桶策略 | 只有当 `aws:SourceVpce` 为 S3 端点时，测试角色才被允许访问 |

S3 网关端点[无法从本地部署环境使用](https://docs.aws.amazon.com/AmazonS3/latest/userguide/privatelink-interface-endpoints.html)；本地部署 Pod 需要使用接口端点。

下面的存储桶策略只会阻止测试角色在端点之外访问。其他主体（例如运维人员）不受影响。

```json
{
  "Sid": "TestRoleOnlyThroughEndpoint",
  "Effect": "Deny",
  "Principal": "*",
  "Action": "s3:*",
  "Resource": ["arn:aws:s3:::<bucket>", "arn:aws:s3:::<bucket>/*"],
  "Condition": {
    "StringNotEquals": {"aws:SourceVpce": "<s3-endpoint-id>"},
    "ArnEquals": {"aws:PrincipalArn": "<test-role-arn>"}
  }
}
```

### IRSA 和 Pod Identity

使用 IRSA 时，Pod 会使用其投射的令牌自行调用 STS `AssumeRoleWithWebIdentity`，因此令牌交换本身已经通过 STS 端点。如果集群 OIDC 提供商尚不存在，请先创建它。在 Pod `env` 中设置 `AWS_STS_REGIONAL_ENDPOINTS=regional`，可让 SDK 使用区域 STS 名称，该名称由私有 DNS 解析。

在混合节点上使用 EKS Pod Identity 需要[额外设置](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-add-ons.html)：在 nodeadm 配置中设置 `enableCredentialsFile`，并将 Pod Identity Agent add-on 配置为 `{"daemonsets":{"hybrid":{"create":true}}}`。测试集群中的默认 Agent DaemonSet 排除了混合节点，因此本次测试使用了 IRSA。

### 结果（8 项全部通过）

| 检查项 | 结果 |
|---|---|
| 从混合 Pod 解析 `sts`、`s3` 和存储桶主机名 | 均返回端点 ENI 地址 (10.0.x) |
| 混合 Pod：`sts get-caller-identity`（IRSA） | 返回 AssumeRole ARN；令牌交换使用了 STS 端点 |
| 混合 Pod：`PutObject` | 成功。存储桶策略会阻止该角色在端点之外访问，因此请求经过了该端点 |
| 云 Pod：对同一对象执行 `GetObject` | 内容相同 |
| 从同一节点上的 Pod 和 hostNetwork Pod 访问 STS ENI:443 | Pod (172.17.x) 获得 HTTP 302，hostNetwork (172.18.x) 超时 |
| 在端点之外（工作站）使用同一角色 | 被 `aws:SourceVpce` 条件拒绝 |

Pod 的请求成功，而 hostNetwork Pod 被阻止，尽管二者都从同一节点发出。**AWS 侧的安全组也能通过 Pod 范围区分本地部署 Pod**，这是没有 SNAT 的最直接证据。

## 链路中断时 DNS 会发生什么

通过在 TGW 路由表中添加黑洞路由（针对本地部署节点和 Pod 范围的 `/17`），模拟了约 95 秒的 DX 或 VPN 中断。路由变更约 17 秒后生效。在每个混合节点上，一个探测 Pod 每秒解析一次本地部署 Service 名称和云 Service 名称，然后分别通过名称和 ClusterIP 调用本地部署 Service。中断期间，混合节点变为 `NotReady`，但其 Pod 仍在运行（探测日志没有间断）；在首次运行中，链路恢复后约 23 秒节点重新变为 `Ready`。

| 配置 | 中断期间混合 Pod 的名称解析 | 对本地部署 Service 的调用 | 备注 |
|---|---|---|---|
| 默认配置：两个 CoreDNS 副本都在云节点上 | **每次查询都失败**（43 至 44 个样本中有 26 个失败） | ClusterIP 返回 200，按名称调用失败 | 本地部署内部的流量仍然正常，但名称解析失败 |
| 区域标签 + 3 个副本 + `PreferSameZone`（与文档示例不同） | 约一半失败（76 至 80 个样本中有 38 至 44 个失败） | 按名称调用间歇性失败 | Cilium 忽略提示，仍将流量负载均衡到无法访问的云 CoreDNS |
| 区域标签 + 4 个副本 + **`PreferClose`** + 强制区域分布 + 重启 Cilium | **0 次失败**（全部 96 至 97 个样本） | 按名称和 ClusterIP 调用均返回 200 | 云 Pod 的解析正常；只有它们对本地部署服务的调用失败，符合预期 |

各步骤中发现的原因：

1. **使用 AWS 文档中的值 `PreferClose`。Cilium 不会根据 `PreferSameZone` 执行操作。AWS** 示例使用 `trafficDistribution: PreferClose`。由于 Kubernetes 1.35 中 `PreferClose` 已成为弃用别名，测试改用了较新的名称 `PreferSameZone`，结果导致约一半请求失败。在混合节点上，即使设置了 `kubeProxyReplacement: false`，ClusterIP 负载均衡也由 Cilium BPF 而非 kube-proxy 执行。EndpointSlice 中虽然有区域提示，但 `cilium-dbg bpf lb list` 仍保留了全部三个 CoreDNS 后端。设置 `trafficDistribution: PreferClose` 后，只剩两个本地部署后端。两个值对应的 EndpointSlice 提示看起来相同，因此请在混合节点上检查 Cilium 中的后端列表。
2. **在加入节点时设置区域标签**。测试中先添加标签，之后再使用 `kubectl -n kube-system rollout restart ds/cilium` 重启 Cilium；未检查不重启是否也会生效。在 nodeadm 配置中使用 kubelet `--node-labels=topology.kubernetes.io/zone=<name>`，在节点加入时设置标签，可以避免这个问题。
3. **没有 CoreDNS 的云 AZ 也会造成问题**。如果云 Pod 所在的区域没有 CoreDNS，它会被分配到所有后端，而在中断期间，落到本地部署 CoreDNS 的查询会失败。每个云 AZ 至少运行一个副本，并至少在一个本地部署区域运行一个副本。
4. **首选反亲和性无法保证调度位置**。CoreDNS 重启后，本地部署副本曾有一次减少到一个。使用 `topologySpreadConstraints` 并设置 `whenUnsatisfiable: DoNotSchedule`，可确保每个区域至少有一个副本。
5. **混合节点上的 CoreDNS 会绕过 PrivateLink**。它会将请求转发到节点的解析器（本地部署 DNS），因此 `sts` 和 `s3` 会解析为公共地址。请求仍能通过 NAT 成功执行，看起来也正常，但 S3 请求被 `aws:SourceVpce` 存储桶策略拒绝，矩阵中的四项检查因此失败。修复方法是在云 VPC 中创建 Route 53 Resolver 入站端点，并在 CoreDNS 中添加 `amazonaws.com` 区块。在真实网络中，在本地部署 DNS 服务器上配置条件转发器也能达到相同效果。

最终的 CoreDNS add-on 配置值（`aws eks update-addon --configuration-values`）：

```json
{
  "replicaCount": 4,
  "trafficDistribution": "PreferClose",
  "topologySpreadConstraints": [{
    "maxSkew": 1, "topologyKey": "topology.kubernetes.io/zone", "whenUnsatisfiable": "DoNotSchedule",
    "labelSelector": {"matchLabels": {"k8s-app": "kube-dns"}}
  }],
  "corefile": "...default .:53 block...\namazonaws.com:53 {\n    errors\n    cache 30\n    forward . <inbound endpoint IP 1> <inbound endpoint IP 2>\n}"
}
```

`corefile` 值会替换整个 Corefile，因此必须包含默认的 `.:53` 区块。更改 Corefile 后，一个位于混合节点上的 CoreDNS 副本延迟加载了 ConfigMap，并在一段时间内使用旧配置响应请求；运行 `rollout restart deploy/coredns` 后问题解决。入站端点安全组只允许 VPC 范围和混合 Pod 范围访问端口 53。中断期间，入站端点也无法访问，因此 AWS API 名称无法解析；不过此时端点本身也无法访问。

## 运维中需要关注的事项

- **CoreDNS 的调度位置**：AWS 建议在混合模式集群中，至少在混合节点和云节点上各运行一个 CoreDNS 副本（[配置 CoreDNS 副本](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-webhooks.html)）。如上所测，只有区域标签、区域分布、`trafficDistribution` 和 Cilium `loadBalancer.serviceTopology: true` 都正确配置，中断期间才能发挥作用。更改后应实际切断链路进行验证。
- **Webhook 和控制平面路径**：API server 代理请求来自云 VPC 中由 EKS 管理的 ENI。要在混合节点上运行 webhook，Pod CIDR 必须可路由，并且本地部署防火墙必须允许这些 ENI 所在的 VPC 范围。
- **静态路由变更**：重新加入的节点可能获得不同的 Pod 网段。若不使用 BGP，就需要在每次节点加入后执行步骤来协调路由。
- **互联网出站流量**：此设置将本地部署环境的默认路由指向云端，因此所有流量都通过一个 NAT 网关离开。如果本地部署环境使用自己的互联网路径，该路径上的 NAT 和防火墙策略必须识别 Pod 范围。
- **成本**：接口端点按 AZ、按小时计费，并按处理的 GB 数计费。

## 测验

* [无 SNAT 的 Pod 连通性与 PrivateLink 测验](../quizzes/eks-hybrid-nodes/12-connectivity-validation-quiz.md)

## 参考资料

* [配置混合节点的 CNI](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-cni.html)：支持的网络模式、伪装、BGP 建议
* [为混合节点准备网络](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-networking.html)
* [为混合节点配置 webhook](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-webhooks.html)：CoreDNS 副本调度位置
* [为混合节点配置 add-on](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-add-ons.html)：Pod Identity Agent
* [通过网络断连保持稳定性的最佳实践](https://docs.aws.amazon.com/eks/latest/best-practices/hybrid-nodes-network-disconnection-best-practices.html)
* [Amazon S3 的 AWS PrivateLink](https://docs.aws.amazon.com/AmazonS3/latest/userguide/privatelink-interface-endpoints.html)
* [通过 AWS PrivateLink 访问 AWS 服务](https://docs.aws.amazon.com/vpc/latest/privatelink/privatelink-access-aws-services.html)
* [Hybrid Nodes Gateway](10-hybrid-nodes-gateway.md)、[网络配置](02-network-configuration.md)、[网络隔离安全审查](11-network-separation-security.md)
