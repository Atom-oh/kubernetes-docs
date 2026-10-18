# 第 13 部分：版本、安装/升级与 Cluster Mesh

> **审阅基线**：Cilium 1.20.2（稳定版，2026-09-16）；Cilium CLI 0.20.1；Hubble CLI 1.20.2。标注为 **[1.21 预发布版]** 的内容来自 v1.21.0-pre.3，正式发布前可能变更。
> **最后更新**：2026 年 10 月 15 日

本章回答前文仅简要提到的三个运维问题：不同 Cilium 版本各自支持哪些功能及其成熟度；如何安全地安装和升级（包括 EKS 专项说明）；以及从控制平面开始，Cluster Mesh 如何工作。仓库之前只在[IPAM 与网络策略](04-ipam-policy.md)中用一个短小章节介绍 Cluster Mesh；本章提供深入指南。

相关部分：[简介](01-introduction.md)、[网络](03-networking.md)、[IPAM](10-ipam-deep-dive.md)、[BGP、LB 与出口流量](11-bgp-lb-egress-edge.md)、[mTLS、加密与身份](12-mtls-encryption-identity.md)。

## 目录

1. 发布节奏与工具版本
2. 按版本划分的功能矩阵（1.17 至 1.21 预发布版）
3. 1.20.1 到 1.20.2 的变更
4. 兼容性与要求
5. 使用 Helm 安装（OCI chart、验证）
6. EKS 安装专项说明
7. 升级与回滚流程
8. 日常运维配置：漂移检测、CiliumNodeConfig、身份迁移
9. Cluster Mesh 架构
10. Cluster Mesh 配置
11. 全局 Service、亲和性与 EndpointSlice 同步
12. MCS-API（多集群 Service）
13. 跨集群策略
14. 在 EKS 上运行 Cluster Mesh
15. 实验
16. 版本差异、故障排查、验证范围限制与来源

---

## 1. 发布节奏与工具版本

Cilium 发布三种各自独立版本控制、容易混淆的制品。

| 制品 | 本次审阅时的版本 | 说明 |
|---|---|---|
| Cilium（agent、operator、Helm chart） | 1.20.2（2026-09-16） | 在 v1.20.2 源码树（`install/kubernetes/cilium/Chart.yaml`）中，chart 的 `version` 和 `appVersion` 均为 1.20.2 |
| Cilium CLI（`cilium`） | 0.20.1（2026-09-24） | 0.20.1 只改动依赖/CI，并将 Cilium 依赖升级到 v1.20.2 |
| Hubble CLI（`hubble`） | 1.20.2（2026-10-07） | 前一个标签为 1.19.4；不存在 1.20.0/1.20.1 的 Hubble CLI 标签。1.20.2 修复了默认字段掩码下 policy-verdict 事件的 `compact` 输出 |
| 回移分支 | 1.19.8 和 1.18.14（均于 2026-09-16 发布） | 与 1.20.2 同日发布 |
| 预发布版 | 1.21.0-pre.3（2026-10-02） | `v1.21.0-pre.1` 从未发布；pre.2 变更日志涵盖 pre.0 到 pre.2 |

Cilium CLI 的发布节奏独立于 agent；若要指定 agent 版本，请显式传入 `--version`。

本次审阅前后的发布历史：

| 发布版本 | 日期 | 备注 |
|---|---|---|
| v1.20.0 | 2026-07-29 | 2660 次提交（发布说明中的统计） |
| v1.20.1 | 2026-08-18 | Cluster Mesh 文档大幅改版；修复 agent 重启后 CIDR 策略处理的 endpoint 问题 |
| v1.20.2 | 2026-09-16 | 最新稳定版；参见第 3 节 |
| v1.21.0-pre.0 | 2026-08-03 | |
| v1.21.0-pre.2 | 2026-09-09 | |
| v1.21.0-pre.3 | 2026-10-02 | 最新预发布版 |

将 1.21.0-pre.x 视为预览版本：选项名称、默认值和升级说明仍可能变更。

## 2. 按版本划分的功能矩阵（1.17 至 1.21 预发布版）

成熟度描述引用自相应版本的发布说明或源码树文档（`.. include:: /beta.rst` 标记）。短横线表示该功能尚不存在。

### 2.1 主要功能

| 功能 | 1.17 | 1.18 | 1.19 | 1.20 | 1.21 pre.3 |
|---|---|---|---|---|---|
| 最低内核版本 | 5.4 | 5.10（RHEL 8.10 为 4.18） | 5.10 | 5.10 | 5.10（原生构建要求 LLVM >= 21.1） |
| 已测试的 Kubernetes | 见 1.17 文档 | 最高 1.33（Go 库 1.33） | 库版本 1.35 | 1.33 至 1.36 | 1.34 至 1.37 |
| Gateway API CRD | v1.2.1 | v1.3.0 | v1.4 | v1.6.1 | v1.6.1 |
| Helm OCI chart `quay.io/cilium/charts/cilium` | 否 | 否 | 是 | 是（推荐） | 是 |
| MCS-API | beta（新增） | beta，镜像 EndpointSlice | beta，CRD 为 `v1alpha1`，自动安装 CRD | 稳定版，`v1beta1`（仍支持 `v1alpha1`） | `v1beta1`；修复镜像 EndpointSlice 名称 |
| Cluster Mesh 策略默认范围 | 所有集群 | 所有集群；新增 `policy-default-local-cluster` flag（默认 false） | 仅本地集群（默认 true） | 仅本地集群；新增 `cluster-mesh` entity | 仅本地集群 |
| `clustermesh.apiserver.tls.authMode` | `legacy`（默认） | `legacy`（默认） | `migration`（默认） | `migration`（默认） | `cluster`（新增 `cluster-strict`） |
| KVStoreMesh | 从 1.16 起默认启用 | `kvstoremesh.enabled` 已弃用 | 默认启用 | 默认启用，该配置值已弃用 | 始终启用，移除此配置值 |
| Double Write 身份分配 | 新增（beta） | beta | beta | beta | beta；弃用 `cilium-dbg preflight migrate-identity` |
| Multi-pool IPAM | beta | beta（+KVStore、IPsec、隧道） | 稳定版 | 稳定版；支持 cluster-pool 原地迁移到 multi-pool | Azure IPAM 迁移到 multi-pool；`CiliumPodIPPool` API 为 `cilium.io/v2`，并新增 `reservedRanges` |
| ENI IPv6 IPAM | - | - | - | beta | ENI 模式下默认关闭 IPv6 masquerade |
| 双向身份验证（SPIFFE/SPIRE） | 存在 | 存在 | 默认关闭 | 已弃用 | 已移除（防火墙表不再列出端口 4250） |
| ztunnel | - | - | beta | beta（内部 CA 或 SPIRE） | beta（1.21 源码树中的 `encryption-ztunnel.rst` 仍带有 `beta.rst` 标记） |
| 感知 Kafka 的 L7 策略 | 支持 | 已弃用 | 已弃用 | 已移除 | 已移除 |
| Envoy Go 扩展（proxylib） | 支持 | 已弃用 | 已弃用 | 已移除 | 已移除 |
| BGPv1 `CiliumBGPPeeringPolicy` | 支持 | 已弃用 | 已移除 | - | - |
| ConfigMap 漂移检测（`configDriftDetection`） | - | 回移到 1.18.x 补丁版 | 回移到 1.19.x 补丁版 | 1.20.0 原生支持 | 同上 |
| 数据路径模式 | `veth`（默认）、`netkit`（beta）、`netkit-l2`、`lb-only` | veth、netkit | 隧道中的 BIG TCP、PLPMTUD | `bpf.datapathMode=auto`（支持时用 netkit，否则用 veth；默认仍是 veth） | 未变 |

### 2.2 各版本主要变化

**1.17**（2025-02，2761 次提交）：QoS Pod 注解（Guaranteed/Burstable/BestEffort 出站优先级）；新增 MCS-API；按协议（TCP/UDP）进行 Service 负载均衡；按 Service 选择 LB 算法（maglev/random）；`loadBalancerSourceRanges` 拒绝列表模式；通过标签配置 AWS 静态 IP，以及单 IP 的 multi-pool 地址池；动态 MTU；`CiliumCIDRGroup` 标签选择；支持端口范围的 HTTP 策略；Gateway API 1.2.1 和静态 Gateway 地址；可动态配置 Hubble metrics ConfigMap；新增 Double Write 身份分配模式（在 KVStore 与 CRD 之间迁移）。

**1.18**（3298 次提交）：LB 控制平面重新设计；IPsec VXLAN-in-IPsec；支持多个 egress gateway（包括 IPv6 地址范围）；带宽入站限速；隧道底层 IPv6；Hubble 策略名称和 `policy log` 字段；`cluster` entity 可限制为本地集群；通过 `k8s.apiServerURLs` 实现 apiserver 故障转移；BGP CRD、`CiliumCIDRGroup` 和 `CiliumLoadBalancerIPPool` 升级为稳定的 `cilium.io/v2`；ENI 模式支持 AWS 前缀委派；Gateway API 1.3.0 和 `CiliumGatewayClassConfig`；最低内核版本提高到 5.10。行为变化：在 ENI 模式下，`enableIPv4Masquerade` 默认值从 true 改为 false（可以将 `upgradeCompatibility` 设为低于 1.18 的版本，或显式设置该项）；ENI 模式下 operator 需要 `ec2:DescribeRouteTables`；`io.cilium.k8s.policy.serviceaccount` 加入默认身份标签，升级时会导致身份短暂变化。

**1.19**（2934 次提交）：默认启用本地集群策略范围；默认关闭双向身份验证；multi-pool IPAM 升为稳定版；支持 OCI Helm chart；ztunnel 进入 beta；IPsec 和 WireGuard 增加严格加密模式；Kafka 策略字段弃用并移除 `FromRequires/ToRequires`；移除 BGPv1；自动安装 MCS-API CRD（`clustermesh.mcsapi.installCRDs`）；重新设计证书生成，不再将 CronJob 用作 Helm hook（兼容 Argo CD 和 `--wait`）；Gateway API 1.4；GAMMA GRPCRoute。

**1.20**（2026-07-29）：Gateway API 1.6.1（ListenerSet、BackendTLSPolicy、TCPRoute/UDPRoute、ExternalAuth、CORS）；数据路径插件；`bpf.datapathMode=auto`；egress gateway 支持 IPv6 出口 IP；通过 `cilium-dbg shell -- bgp/*` 管理 BGP，GoBGP 4.6.1；ENI IPv6（beta）；支持 cluster-pool 原地迁移到 multi-pool；流量分布 `PreferSameZone`/`PreferSameNode`；通过 `service.cilium.io/weight` 设置 Maglev 权重（0 表示排空）；MCS-API 升为稳定版；新增 `cluster-mesh` 策略 entity；Kubernetes ClusterNetworkPolicy admin/baseline 层级；ConfigMap 漂移检测；`cilium-cni` 二进制文件从 77 MB 缩减到 16 MB；Kubernetes 1.36、Envoy 1.37.x。**1.20 移除的功能**：Envoy Go 扩展（proxylib）、感知 Kafka 的 L7 策略、`CiliumNodeConfig` `v2alpha1`、`clustermesh.enableMCSAPISupport`（改用 `clustermesh.mcsapi.enabled`）、Cluster Mesh 的 values 证书、`cilium-docker-plugin`、旧版 `encryption.strictMode.*` flags（现为 `encryption.strictMode.egress.*`）、`--node-port-algorithm`/`--node-port-mode`、`--ces-slice-mode`、`encryption.ipsec.interface`。**行为变化：**`bpf.tproxy=true` 与 netkit 不兼容；启用 NodePort 但未使用 SocketLB 的 Pod（或设置 `socketLB.hostNamespaceOnly=true` 的 Pod）访问集群内部 NodePort 时，现在由客户端 Pod 执行负载均衡，因此客户端出站和后端入站策略都必须允许该流量；空的 `CiliumNetworkPolicy`/`CiliumClusterwideNetworkPolicy`（没有 `spec`/`specs`）会在准入时被拒绝；Cluster Mesh 自动生成证书默认有效期为一年，并由 CronJob 每四个月重新生成；certgen 会要求 CA 有效期不短于叶证书有效期（设置 `certgen.enforceCAValidityThroughoutLeavesDuration=false` 可关闭此检查）。

**1.21 预发布版**（v1.21.0-pre.3）：delta xDS（`envoy.xdsMode=delta-split`）；Cilium Network Driver（DRA、SR-IOV）；Gateway API 会话持久性；策略中支持 AWS managed prefix list；KVStoreMesh 无条件启用；Cluster Mesh `authMode` 默认值改为 `cluster`；移除双向身份验证；弃用 `encryption.nodeEncryption`（WireGuard），计划在 1.22 移除；移除 operator flag `--aws-use-primary-address`（改用 `eni.nodeSpec.usePrimaryAddress`）；不再将 Gateway/GAMMA 基础设施元数据中的 `cec.cilium.io/*` 注解传递给生成的 `CiliumEnvoyConfig`；operator 会自动迁移已弃用对象的存储版本；Kubernetes 库升级到 1.37。pre.2 发布说明中的“默认启用 BPF masquerading”没有反映在 pre.3 源码树中（见“验证范围限制”）。

## 3. 1.20.1 到 1.20.2 的变更

`gh api repos/cilium/cilium/compare/v1.20.1...v1.20.2` 显示 204 次提交（API 返回的文件列表在 300 项处截断，因此变更文件数不可靠）。没有逐项审计提交列表中的功能类改动，所以不要假设升级风险低，应先阅读发布说明；其中若干修复只对特定配置有影响。

| 范围 | 修复内容 |
|---|---|
| AWS ENI IPAM | operator 会将仍在使用的委派前缀错误地当作单个 IP 释放；子网前缀耗尽时分配失败；ENI 模式下 `ipv4NativeRoutingCIDR` 为 VPC 辅助 CIDR 时 agent 启动崩溃；修复 IPv6 ENI 路由（健康检查 endpoint、Ingress、IPsec）；masquerade 配置变更后恢复 ENI endpoint 路由规则；减少 EC2 IMDS 负载 |
| Cluster Mesh | 修复罕见竞态，避免已移除的远端集群仍保持连接；加强对 Cluster Mesh 接收的 Service 后端校验；配置变更时 clustermesh-apiserver etcd 用户管理未撤销过期角色（Helm chart 用户不受影响） |
| 升级 | 使用 Cilium 1.15 或更早版本创建的集群会因移除 `CiliumNodeConfig` `v2alpha1` CRD 版本而升级失败。将这类集群升级到 1.20 时，请使用 1.20.2 或更高版本 |
| 被忽略的选项 | 五个以前会被接受但静默忽略的选项现在生效：`vtep-sync-interval`、`enable-xt-socket-fallback`、自定义 CNI 配置中的 `eni-delete-on-termination`、非 chaining 模式下 Helm 的 `enableIdentityMark`、`lb-retry-backoff-max`；另修复了四个从未传递到 sink 的 Hubble 配置项 |
| 数据路径 | 修复被误判为 WireGuard 的分片 UDP、SNAT LB 流量的 ICMP 错误校验和、DSR 恢复和 PMTU ICMP 来源、`externalTrafficPolicy: Local` 下的 L2 通告、LocalRedirectPolicy 回归问题，以及 `policy-deny-response: icmp` 的出站拒绝指标 |
| 策略 | NetworkPolicy 变更后立即创建的 Pod，其 revision 可能过时达两分钟；修复命名端口下并发策略映射崩溃；修复身份保留时间达到预期两倍的问题 |
| Gateway API | `HTTPRoute` ExternalAuth 遇到无效 `backendRef` 时现在会 fail-closed；文档说明 `bpf.tproxy` 为 false（默认值）时，Gateway API 需要 iptables 和 netfilter TPROXY 模块 |
| BGP | `defaultGateway` peer 自动发现选错路由表 |

1.20.2 中的镜像和 chart 升级：certgen 从 v0.4.9 升至 v0.4.11；Envoy 从 v1.37.5 升至 v1.37.6；hubble-ui 从 v0.13.5 升至 v0.13.6；SPIRE 从 1.15.2 升至 1.15.3。`values.yaml` 的差异只有镜像标签和一个 schema 注解；现在仅当设置 `enableIdentityMark` 时才会渲染 `enable-identity-mark` ConfigMap 键。

1.20.2 的文档变更：从 `system_requirements.rst` 的必需内核配置列表中移除了 `CONFIG_CRYPTO_USER_API_HASH` 和 `CONFIG_INET_XFRM_MODE_TUNNEL` 两项；Cluster Mesh 简介新增“安全”一节，说明 mesh 中的所有集群属于同一个信任域，因此只应连接彼此信任且安全状态相当的集群。

建议：ENI 用户、Cluster Mesh 部署以及任何使用 Cilium 1.15 或更早版本创建的集群均使用 `--version 1.20.2`。

## 4. 兼容性与要求

### 4.1 版本兼容性

| 项目 | 1.20.2 | 1.21.0-pre.3 |
|---|---|---|
| Kubernetes（已测试） | 1.33、1.34、1.35、1.36 | 1.34、1.35、1.36、1.37 |
| Linux 内核 | >= 5.10（RHEL 8.10：4.18） | >= 5.10 |
| clang/LLVM（仅原生构建 agent） | >= 18.1 | >= 21.1 |
| Gateway API CRD | 必需 v1.6.1 | v1.6.1 |
| Helm chart `kubeVersion` | `>= 1.21.0-0`（chart 约束，并非已测试范围） | 相同 |
| Cilium CLI | 0.20.1 | 不适用 |
| Hubble CLI | 1.20.2 | 不适用 |

1.20.2 系统要求中的特定功能最低内核版本：AMD64 多播 >= 5.10，AArch64 多播 >= 6.0；IPv6 BIG TCP >= 5.19；IPv4 BIG TCP >= 6.3；netkit >= 6.8 且需启用 `CONFIG_NETKIT=y`。1.19 的说明指出：IPsec、kube-proxy 替换和 BPF masquerade 同时启用时，会自动启用 BPF host routing，而该功能要求内核包含 CVE-2025-37959 的修复。

Cluster Mesh 还有一项约束：所有互联集群的 Cilium 版本最多只能相差一个次版本（例如，1.19.x 可以加入 1.18.x 和 1.20.x，但不能加入 1.17.x）。

### 4.2 端口

节点之间仅通过安全组引用或私有 CIDR 开放下列端口（绝不能使用 `0.0.0.0/0`）：

| 端口 | 用途 |
|---|---|
| UDP 8472 | VXLAN 隧道 |
| UDP 6081 | Geneve 隧道 |
| TCP 4240 加 ICMP 类型 8/0 | 健康检查 |
| TCP 4244 | Hubble server |
| TCP 4245 | Hubble Relay |
| UDP 51871 | WireGuard |
| ESP（IP 协议 50） | IPsec（除非添加允许规则，否则 AWS 安全组会阻止 ESP） |
| TCP 4250 | 双向身份验证（出现在 1.20 文档中；已从 1.21 文档移除） |
| TCP 2379 | 集群之间的 clustermesh-apiserver 通信 |

### 4.3 Gateway API CRD

Cilium 1.20 要求 Gateway API CRD 为 v1.6.1（`Documentation/conf.py` 中的 `gateway_api_version = 'v1.6.1'`，以及 `go.mod` 中的 `sigs.k8s.io/gateway-api v1.6.1`）。Helm chart 不会安装这些 CRD。必需 CRD：GatewayClass、Gateway、HTTPRoute、GRPCRoute、ReferenceGrant、BackendTLSPolicy、TLSRoute。可选 CRD（缺失时相应功能保持禁用）：TCPRoute、UDPRoute、ListenerSet。前置条件：`kubeProxyReplacement=true`、`l7Proxy=true`，并安装 iptables 和 TPROXY 模块；若使用 beta 版 `bpf.tproxy=true`，则不需要后两者。使用 `kubectl apply --server-side` 应用 CRD。

TLSRoute 陷阱：如果已经在使用 TLSRoute，请安装 experimental channel 中的 TLSRoute v1.6.1，它仍包含 `v1alpha2`。安装 standard channel 的 v1.6 TLSRoute 会使现有 TLSRoute 对象无法读取（它们实际上会消失）。请先备份这些对象（`kubectl get tlsroutes -A -o yaml`）。

## 5. 使用 Helm 安装

Helm chart 有两个来源：

| 来源 | 状态 |
|---|---|
| `oci://quay.io/cilium/charts/cilium` | 自 1.19 起文档推荐；chart 由 cosign 签名，并可按摘要固定版本 |
| `https://helm.cilium.io/`（`helm repo add cilium`） | 传统仓库，仍受完整支持 |

Chart 版本号不带 `v` 前缀（`--version 1.20.2`），镜像标签则带字母 v。OCI registry 不支持 `helm search`；使用 `crane ls quay.io/cilium/charts/cilium` 列出版本。验证 chart 签名：

```bash
cosign verify \
  --certificate-identity-regexp='https://github.com/cilium/cilium/.*' \
  --certificate-oidc-issuer=https://token.actions.githubusercontent.com \
  quay.io/cilium/charts/cilium:1.20.2
```

将 values 保存在版本控制下的文件中，并使用 `-f values.yaml` 安装；不要依赖一长串 `--set` 参数，因为第 7 节要求每次次版本升级时都重新提供这些 values。

## 6. EKS 安装细节

### 6.1 选择模式

| 模式 | Helm | 数据路径 / IPAM | 说明 |
|---|---|---|---|
| ENI（EKS 上游默认模式） | `eni.enabled=true` | 原生路由（启用 `eni.enabled` 时 chart 默认将 `routingMode` 设为 native）、AWS ENI IPAM、Kubernetes CRD 数据存储 | Pod 获得可由 VPC 路由的 IP；operator 需要 EC2 API 权限；Cilium 节点上不能运行 `aws-node` |
| Overlay | 不设置 `eni.enabled`（chart 默认使用隧道/VXLAN） | VXLAN、cluster-pool IPAM | 每个节点可运行的 Pod 数量可超过 ENI 限制；Pod 到 VPC 的流量会 SNAT 为节点 IP；EKS API server 无法路由到 overlay Pod IP，因此 webhook 必须使用 host network，或通过 Service/Ingress 访问；清理 VPC CNI 留下的 `AWS-SNAT-CHAIN-0/1` 和 `AWS-CONNMARK-CHAIN-0/1` iptables 链 |
| 在 VPC CNI 上进行 chaining | `cni.chainingMode=aws-cni`、`cni.exclusive=false`、`enableIPv4Masquerade=false`、`routingMode=native` | VPC CNI 负责网络，Cilium 添加策略和可见性 | 要求 VPC CNI >= 1.11.2；启用后需重启现有 Pod。上游 `cni-chaining-limitations.rst` 列出了 chaining 的限制；选择此模式前请阅读 |
| EKS Hybrid Nodes | AWS 构建的 chart `oci://public.ecr.aws/eks/cilium/cilium` | VXLAN overlay、cluster-pool | 参见 6.4 |
| EKS Auto Mode | 不支持 | 不适用 | 参见 6.5 |

### 6.2 ENI 模式安装

Cilium 会管理 ENI，因此不要让 VPC CNI 在由 Cilium 管理的节点上运行。通过添加一个没有任何节点匹配的 node selector 来修补 `aws-node` DaemonSet（上游命令，原样使用）：

```bash
kubectl -n kube-system patch daemonset aws-node --type='strategic' \
  -p='{"spec":{"template":{"spec":{"nodeSelector":{"io.cilium/aws-node-enabled":"true"}}}}}'
```

为托管节点组添加 taint，使应用 Pod 等待 Cilium 就绪（上游建议）：

```yaml
# eksctl ClusterConfig fragment
managedNodeGroups:
- name: ng-1
  taints:
  - key: "node.cilium.io/agent-not-ready"
    value: "true"
    effect: "NoExecute"
```

Values 文件（下列键均存在于 1.20.2 chart 中；`eni.enabled=true` 会设置 operator 镜像、endpoint 路由、CiliumNode 管理和 IPv4 masquerade 默认值；如果设置了 `ipam.mode=eni` 却未设置 `eni.enabled=true`，chart 校验会失败）：

```yaml
# values-eks-eni.yaml  (Cilium 1.20.2)
eni:
  enabled: true
kubeProxyReplacement: true
k8sServiceHost: <EKS-API-ENDPOINT-FQDN-without-scheme>
k8sServicePort: 443
cluster:
  name: eks-a
  id: 1   # keep below 128 in ENI mode (see the cluster.id note in the Helm reference)
```

```bash
helm install cilium oci://quay.io/cilium/charts/cilium --version 1.20.2 \
  -n kube-system -f values-eks-eni.yaml
```

注意：

- 使用 kube-proxy 替换时，必须在移除 kube-proxy 前设置 `k8sServiceHost` 和 `k8sServicePort`，否则 agent 无法连接 API server。
- Operator 需要 EC2 权限（参见上游 `ec2privileges` 一节）；从 1.18 起还需要 `ec2:DescribeRouteTables`。
- 1.18 将 ENI 模式下 `enableIPv4Masquerade` 的默认值改为 false。如果升级 1.18 之前的 ENI 集群且依赖 masquerade，请显式设置该值，或使用 `upgradeCompatibility`。
- 1.20 中 ENI IPv6 为 beta（参见 `eni.rst`）。一个上游页面（`requirements-eks.rst`）仍声称 ENI 仅支持 IPv4；请以发行说明和 `eni.rst` 为准。
- ENI 模式建议使用 1.20.2：该版本修复了前缀委派释放、子网前缀耗尽时的分配，以及辅助 VPC CIDR 下原生路由崩溃问题。
- Pod IP 来自 `default` pool；ENI 模式下不使用 `CiliumPodIPPool` 和 `ipam.cilium.io/ip-pool` 注解（参见 `eni.rst`）。另见 [IPAM](10-ipam-deep-dive.md)。

### 6.3 AMI

1.20.2 系统要求列出的支持平台包括 Amazon Linux 2 和 Bottlerocket（“所有”版本）、Ubuntu >= 20.04、RHEL >= 8.6、Talos >= 1.5.0，以及 Flatcar（ENI 有 DHCP 注意事项）。文档没有明确列出 Amazon Linux 2023；其内核版本高于 5.10 最低要求，但这是推断，并非上游声明。AWS 的 Hybrid Nodes 文档指出，Ubuntu 20.04 和 RHEL 8 不满足 Cilium 1.18.3 的内核要求。

### 6.4 EKS Hybrid Nodes

AWS 仅通过其维护的公共 ECR 构建版本支持在 hybrid node 上使用 Cilium：`oci://public.ecr.aws/eks/cilium/cilium`（AWS 文档中出现了 `1.17.9-0` 和 `1.18.3-0` 等版本；本次审查未核实更新的 AWS 构建版本列表）。VPC CNI 与 hybrid node 不兼容。AWS 默认配置使用 VXLAN overlay 和 cluster-pool IPAM；pool CIDR 必须与 EKS 远程 Pod 网络相同，不得与节点、VPC 或 Service CIDR 重叠，且部署后不得更改。使用 `eks.amazonaws.com/compute-type In hybrid` affinity 将 agent 和 operator 固定到 hybrid node，并使用 BGP Control Plane 使 Pod CIDR 可路由。AWS 支持列表将 Cilium Ingress 和 Cilium Gateway 列为 hybrid node 支持功能（默认配置；参见 AWS 的 [CNI](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-cni.html) 和 [Ingress](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-ingress.html) 页面）。`envoy.enabled: false` 只出现在 AWS 基线示例 values 中；由于 Cilium Ingress/Gateway 和 L7 网络策略需要 Envoy，若使用这些功能，请按照 AWS ingress 页面启用 Envoy。在该设置中，AWS 云节点不受 Cilium 支持。

### 6.5 EKS Auto Mode

EKS Auto Mode 无法与 Cilium 配合使用。AWS 文档指出 Auto Mode 不支持替代 CNI 插件或网络策略插件（EKS 用户指南中的“alternate CNI plugins”和“auto networking”页面），而上游 Cilium 文档也没有 Auto Mode 页面。若要使用 Cilium，请选择标准托管节点组或自管理节点。

### 6.6 本仓库的对外暴露规则

本章不需要任何公共监听器。如果 VPC 外部的客户端需要访问应用，请使用 CloudFront 和 VPC origin，连接到内部 ALB/NLB。clustermesh-apiserver Service 也必须是内部 Service（第 14 节）。

## 7. 升级与回滚流程

### 7.1 规则

1. 仅测试过相邻次版本间的升级和回滚（1.19 到 1.20，再回退）。不要跳过次版本。
2. 首先升级到当前次版本的最新补丁版本，以确保存在包含所有修复的回滚目标版本。
3. 所有组件（agent、operator、Hubble Relay、clustermesh-apiserver）都必须升级到相同版本；不要只升级 agent。
4. L3/L4 流量受到的影响很小或没有影响；经用户态代理（L7 策略、Ingress、Gateway API、Envoy）的连接会中断，客户端必须重新连接。节点上的 agent 恢复运行前，新策略规则会延迟生效。
5. 跨次版本升级时绝不要使用 `helm upgrade --reuse-values`：它会忽略 chart 的新默认值，并可能生成无效清单。仅当 chart 版本不变时才可以使用 `--reuse-values`（例如本章稍后的 Cluster Mesh 配置升级）。
6. 将 `upgradeCompatibility` 设置为最初安装的次版本（而不是当前待升级版本）。它会在渲染后的 ConfigMap 中固定旧默认值；例如，它会恢复 1.18 之前的 ENI masquerade 默认值。
7. 对于使用 1.15 或更早版本创建的集群，请升级到 1.20.2 或更高版本，不要使用 1.20.0/1.20.1。

### 7.2 流程

```bash
# 0. Save and review current values for renamed/removed keys
helm get values cilium -n kube-system -o yaml > old-values.yaml

# 1. Pre-flight: pre-pulls the new image on every node and validates existing CNPs
helm install cilium-preflight oci://quay.io/cilium/charts/cilium --version 1.20.2 \
  -n kube-system \
  --set preflight.enabled=true --set agent=false --set operator.enabled=false
#   (add k8sServiceHost/k8sServicePort when kube-proxy replacement is on)
kubectl -n kube-system get ds cilium-pre-flight-check   # READY must equal the node count
kubectl -n kube-system get deploy cilium-pre-flight-check   # must be 1/1
kubectl -n kube-system logs deployment/cilium-pre-flight-check -c cnp-validator --previous
helm delete cilium-preflight -n kube-system

# 2. Upgrade (NO --reuse-values); 1.19 is the minor you installed originally in this example
helm upgrade cilium oci://quay.io/cilium/charts/cilium --version 1.20.2 \
  -n kube-system -f old-values.yaml --set upgradeCompatibility=1.19

# 3. Watch
kubectl -n kube-system rollout status ds/cilium
kubectl -n kube-system rollout status deploy/cilium-operator
cilium status --wait
```

如果预检 Deployment 一直显示 `READY 0/1`，表示至少有一个现有 CiliumNetworkPolicy 无法通过新版本校验；升级前先修复该策略。

### 7.3 回滚

```bash
helm history cilium -n kube-system
helm rollback cilium <REVISION> -n kube-system
# or, for the DaemonSet only:
kubectl -n kube-system rollout undo daemonset/cilium
```

如果已经使用了新次版本的功能（新 CR、ConfigMap opt-in 项），回滚前请阅读该版本的升级说明；回滚会恢复旧清单，但不会删除新版本创建的对象。

### 7.4 CRD 处理

| CRD 类型 | 安装/更新方 | 操作 |
|---|---|---|
| Cilium CRD（`cilium.io`） | operator/agent 启动时注册并更新 | 无需操作，但升级后请使用 `kubectl get crd \| grep cilium.io` 检查。1.20 移除了 `CiliumNodeConfig` `v2alpha1`；请使用 `cilium.io/v2` |
| Gateway API | 由你手动执行（`kubectl apply --server-side`） | 与第 4.3 节的版本一致；先备份 TLSRoute |
| MCS-API（`multicluster.x-k8s.io`） | 当 `clustermesh.mcsapi.enabled=true` 时由 chart 安装，除非设置 `clustermesh.mcsapi.installCRDs=false`（自 1.19 起） | 如果由其他 controller 管理这些 CRD，请设置 `installCRDs=false` |
| 过时的存储版本 | **[1.21 预发布版]** operator 会自动迁移存储版本 | `CiliumPodIPPool` `v2` 将成为存储版本 |

### 7.5 逐个次版本检查升级操作

务必阅读目标次版本的“Upgrade Notes”。上文提到的常见注意项包括：ENI masquerade 默认值和 `ec2:DescribeRouteTables`（1.18）；新增 service-account 标签导致的身份标签变化（1.18）；`policy-default-local-cluster` 改为 true（1.19，参见第 13 节）；默认禁用双向身份验证（1.19）；移除选项以及移除 Kafka/proxylib（1.20）；`bpf.tproxy` 与 netkit 的兼容性，以及 NodePort 客户端侧负载均衡（1.20）；`authMode=cluster` 默认值，以及移除 `kvstoremesh.enabled` value（1.21 预发布版）。

## 8. 日常配置

### 8.1 ConfigMap 漂移检测

许多选项只有在 agent 重启后才会生效。编辑 `cilium-config` ConfigMap（通过 `helm upgrade` 或 `cilium config set`）后，运行中的 agent 配置可能会与 ConfigMap 不一致。漂移检测可以让这种差异可见。1.20.0 原生支持此功能，且该功能已回移到 1.18.x 和 1.19.x 的补丁版本（v1.18.14 和 v1.19.8 chart 中包含此功能，但 v1.18.0 和 v1.19.0 中没有）。

```yaml
configDriftDetection:
  enabled: true        # enable-dynamic-config: watch the ConfigMap
  driftChecker: true   # enable-drift-checker: compare desired vs active
  ignoredKeys: []      # for example ["devices"] for keys that are intentionally different
```

对于每个不匹配的键，agent 都会记录一条警告，并公开 gauge 指标 `cilium_drift_checker_config_delta`。值为 `0` 表示配置一致；大于 0 表示 agent 尚未应用当前 ConfigMap，需要重启。若 `cilium_drift_checker_config_delta > 0` 的状态持续时间超过你的发布窗口，请触发告警。

默认情况下，`cilium config set <key> <value>` 会修改 ConfigMap 并重启 agent；传入 `--restart=false` 可以延迟重启，并通过漂移 gauge 显示尚未应用的变更。

### 8.2 CiliumNodeConfig（逐节点覆盖项）

`CiliumNodeConfig`（`apiVersion: cilium.io/v2`，namespace 为 `kube-system`）会覆盖由 `spec.nodeSelector` 匹配的节点上的 ConfigMap/agent 键值（空 selector `{}` 匹配所有节点）。只有重新创建 agent Pod 或重启节点后，更改才会生效。`v2alpha1` 已在 1.20 移除。

```yaml
apiVersion: cilium.io/v2
kind: CiliumNodeConfig
metadata:
  namespace: kube-system
  name: enable-xdp
spec:
  nodeSelector:
    matchLabels:
      io.cilium.xdp-offload: "true"
  defaults:
    bpf-lb-acceleration: native
```

常见用途：仅在硬件适用的节点上启用 XDP 或 IPv6 BIG TCP，以及逐步推出 kube-proxy 替换（为已迁移节点添加标签 `io.cilium.migration/kube-proxy-replacement=true`，为 kube-proxy DaemonSet 设置针对该标签的 `NotIn` affinity，在 CiliumNodeConfig 中设置 `kube-proxy-replacement: "true"`，然后逐节点删除 agent Pod）。在移除 kube-proxy 前，必须先设置 `k8sServiceHost` 和 `k8sServicePort`。

### 8.3 从 KVStore 迁移到 CRD 身份存储（“Double Write”，beta）

此功能在 1.17 引入，在 1.20.2 和 1.21 pre.3 中仍标记为 beta。分配模式由 agent 选项 `--identity-allocation-mode` 控制，并通过 Helm value `identityAllocationMode` 设置（chart 会将其渲染为 ConfigMap 键 `identity-allocation-mode`）。

| 步骤 | 模式 | 发布顺序 | 数据源 |
|---|---|---|---|
| 0 | `kvstore` | | KVStore |
| 1 | `doublewrite-readkvstore` | 先 operator，再 agents | KVStore（身份也会写入 CRD，但不会读取） |
| 2 | `doublewrite-readcrd` | 先 operator，再 agents | CRD（仍会写入 KVStore，以便快速回滚） |
| 3 | `crd` | 先 agents，再 operator | 仅 CRD；可以停用 KVStore |

每个步骤之间都要等待状态收敛。Operator 会在 `cilium_operator` 命名空间公开 gauge 指标。上游升级页面仍列出旧名称 `cilium_operator_identity_*_count`，但 v1.20.2 的 `operator/doublewrite/metrics.go` 代码注册了 `doublewrite_crd_identities`、`doublewrite_kvstore_identities`、`doublewrite_crd_only_identities` 和 `doublewrite_kvstore_only_identities`，它们显示为 `cilium_operator_doublewrite_*`。请在 operator metrics 端口上使用 `curl`，确认你所用版本的确切名称。KVStore 和 CRD 的垃圾回收运行时间不同（`--identity-gc-interval`、`--identity-heartbeat-timeout`），因此短暂出现差异属于正常情况。反向迁移（从 CRD 迁回 KVStore）可按相反顺序重复这些步骤。全新恢复：确保没有 agent 以 `crd` 模式运行，然后执行 `kubectl delete ciliumid --all`。

一次性工具 `cilium-dbg preflight migrate-identity` 在 1.20.2 文档中有说明，但存在限制（不允许身份变化，且不容易回滚）；它已在 1.21 预发布版中弃用，请改用 Double Write。

## 9. Cluster Mesh 架构

Cluster Mesh 会连接多个 Kubernetes 集群的控制平面，以共享身份、endpoint、节点和 Service；Pod 流量则直接在节点之间传输，不经过网关或代理。

```
 Cluster 1                                         Cluster 2
 ┌──────────────────────────────┐                  ┌──────────────────────────────┐
 │ clustermesh-apiserver (Deploy)│                 │ clustermesh-apiserver (Deploy)│
 │  ┌────────┐ ┌──────────────┐ │  mTLS etcd 2379  │  ┌────────┐ ┌──────────────┐ │
 │  │ etcd   │◄┤ apiserver    │ │◄────────────────►│  │ etcd   │◄┤ apiserver    │ │
 │  │(local  │ │ (sync local  │ │  (via internal LB│  │        │ │              │ │
 │  │ state) │ │  state -> etcd)│ │   / NodePort)   │  │        │ │              │ │
 │  └───▲────┘ └──────────────┘ │                  │  └───▲────┘ └──────────────┘ │
 │      │      ┌──────────────┐ │                  │      │      ┌──────────────┐ │
 │      └──────┤ kvstoremesh  │─┼─ pulls remote ──►│      └──────┤ kvstoremesh  │ │
 │             └──────▲───────┘ │   cluster state  │             └──────▲───────┘ │
 │   agents read ONLY │ local   │                  │   agents read ONLY │ local   │
 │   ┌────────────────┴─┐       │                  │   ┌────────────────┴─┐       │
 │   │ cilium-agent (DS)│       │                  │   │ cilium-agent (DS)│       │
 │   └─────────┬────────┘       │                  │   └─────────┬────────┘       │
 └─────────────┼────────────────┘                  └─────────────┼────────────────┘
               └──────── Pod -> Pod, node to node (VXLAN/Geneve or native) ───────┘
```

组件（v1.20.2 `intro.rst`、`values.yaml`）：

- **clustermesh-apiserver** 是一个包含三个容器的 Deployment。`etcd` 是单实例嵌入式 etcd，不使用持久化存储；启动时会从 Kubernetes API server 重建状态，并通过 mTLS 对外提供服务。`apiserver` 将本地 Cilium 和 Kubernetes 状态（节点、endpoint、身份、Service）同步到该 etcd（`etcdQPS: 50`）。`kvstoremesh` 将各远程集群的状态拉取到本地 etcd 缓存（`etcdQPS: 100`）。
- **KVStoreMesh**：agent 仅从本地缓存读取远程状态，因此每个 agent 不必分别连接所有远程 etcd。自 1.16 起它就是默认组件；`clustermesh.apiserver.kvstoremesh.enabled` value 在 1.18 弃用，**并在[1.21 预发布版]中变为无条件启用**，该 value 也会被移除。
- **副本**：`clustermesh.apiserver.replicas` 默认值为 1。每个副本运行自己的 etcd 集群；远程客户端通过 Service 选择其中一个。`service.enableSessionAffinity`（默认 `HAOnly`，还可设为 `Always`、`Never`）可减少重新连接后的完整状态同步。默认禁用 `podDisruptionBudget`。
- **KVStore 模式**：如果 Cilium 已将外部 etcd 用作身份/状态存储，Cluster Mesh 可以复用它（`clustermesh.apiserver.kvstoremesh.kvstoreMode: external`）；`external` 不能与 `crd` 身份分配模式同时使用。
- **单一信任域**（v1.20.2 `intro.rst`）：一旦某个集群遭到入侵，就可能污染其他集群，因此只能连接相互信任且安全态势相当的集群。

### 9.1 数据路径

远程 Pod 会以远程节点为隧道端点出现在本地 ipcache 中（overlay 模式），或通过 underlay 路由（原生路由模式）。由于身份中包含 cluster ID，因此集群 1 对来自集群 2 的 Pod 流量进行策略判定时，会使用远程 Pod 的数字身份，无需经过任何网关即可生效。这就是 Pod CIDR 不得重叠且节点 IP 必须互通的原因。

## 10. Cluster Mesh 配置

### 10.1 前置条件

| 要求 | 详情 |
|---|---|
| 数据路径模式相同 | 所有集群都使用 overlay，或全部使用原生路由 |
| Cilium 次版本差异 | 最多相差一个次版本 |
| Pod CIDR 唯一且不重叠 | 必须覆盖所有集群的所有节点 |
| 节点间可达 | 通过每个节点的 InternalIP（peering、TGW 或 VPN） |
| 防火墙 | TCP 2379（clustermesh-apiserver）、TCP 4240 和 ICMP（健康检查）、UDP 8472/6081（隧道）、UDP 51871（WireGuard） |
| 仅原生路由模式 | `ipv4NativeRoutingCIDR` 必须覆盖每个集群的 Pod CIDR（例如 `10.0.0.0/8`），并且 Pod 流量必须能够在集群间通过所有端口路由 |

### 10.2 集群名称和 ID

| 设置 | 规则 |
|---|---|
| `cluster.name` | 最多 32 个字符，正则表达式 `^([a-z0-9][-a-z0-9]*)?[a-z0-9]$`（`pkg/clustermesh/types/types.go`）；每个集群必须唯一。ID 非零时不能使用 `default` |
| `cluster.id` | 默认范围为 1 至 255；0 表示未设置且为保留值。设置 `maxConnectedClusters: 511` 后范围扩展到 511。**ENI 模式和 aws-cni chaining**：除非设置 `extraConfig.allow-unsafe-policy-skb-usage=true`，否则 chart 会拒绝 128-255 的 ID（以及 `maxConnectedClusters: 511` 时的 384-511）（`templates/validate.yaml:160-168`、cilium/cilium#21330）；EKS ENI 模式请使用小于 128 的 ID |
| `clustermesh.maxConnectedClusters` | `255`（默认值）或 `511`；所有集群必须一致，且只能在安装时设置 |

权衡：cluster ID 会占用数字身份中的若干位。最多连接 255 个集群时，每个集群可使用的集群本地身份上限为 65535；连接 511 个集群时，上限降为 32767。在运行中的集群上更改 `maxConnectedClusters` 可能中断连接并导致策略执行错误。`values.yaml` 中 `cluster.id` 的注释仍称范围为 1 至 255；对 511 的情况来说，这个说明已过时。在运行中的集群上更改 cluster name 或 ID，需要重启所有工作负载，因为身份中包含 cluster ID。

### 10.3 TLS 和 authMode

| 值 | 含义 |
|---|---|
| `clustermesh.apiserver.tls.auto.method` | `helm`（仅在 `helm upgrade` 时续签证书，因此至少每年升级一次）、`cronJob`（默认计划为 `0 0 1 */4 *`，每四个月运行一次）、`certmanager` |
| `tls.auto.certValidityDuration` | `365` 天 |
| 共享 CA | 所有集群必须使用同一个 CA：启用前将 `cilium-ca` Secret 复制到其他集群，或设置 `tls.caBundle` |
| 用户提供的证书 | Secrets：`clustermesh-apiserver-{server,admin,remote,local}-cert`；CN：server 为 `clustermesh-apiserver.<ns>.svc`（SAN 包括 `*.mesh.cilium.io`、`127.0.0.1`、`::1` 和额外 DNS 名称），admin 为 `admin-<cluster>`，local 为 `local-<cluster>`，remote 在 1.20 中为 `remote`，在 `cluster` 模式中为 `remote-<cluster-name>` |

`authMode` 决定每个集群连接远程 clustermesh-apiserver 时使用哪个 etcd 用户：

| authMode | 行为 | 默认版本 |
|---|---|---|
| `legacy` | 所有集群都使用用户 `remote` | 1.17、1.18（`values.yaml`：v1.17.18 第 3416 行，v1.18.14 第 3634 行） |
| `migration` | 为每个集群创建独立用户，但身份验证仍使用 `remote`；从 legacy 切换到 cluster 或反向切换且不中断服务时必须使用 | 1.19、1.20 |
| `cluster` | 每个集群使用 `remote-<cluster-name>` 进行身份验证；只有共享同一个 CA 时才有意义 | **[1.21 预发布版]** |
| `cluster-strict` | **[1.21 预发布版]** 类似 `cluster`，但不使用共享的 `remote` 用户；仅当所有集群都已使用 `cluster` 后启用 | - |

1.21 的操作说明：如果设置了 `clustermesh.useAPIServer=true` 和 `tls.auto.enabled=false`，请重新签发 remote 证书，将 CN 设为 `remote-<cluster-name>`，或者将 `authMode` 改回 `migration` 或 `legacy`。使用自动证书时，预计切换过程不会产生可见影响。设置 `clustermesh.config.enabled=false` 时，必须自行创建 `clustermesh-remote-users` ConfigMap（1.19 说明）。证书有效期也有变化：1.19 重新设计了证书生成流程（CronJob 不再用作 Helm hook）；1.20 默认有效期为一年、每四个月重新生成，并要求 CA 有效期 >= 叶证书有效期；1.20 中的键 `clustermesh.apiserver.tls.server.{extraDnsNames,extraIpAddresses}` 已移至 `clustermesh.apiserver.tls.auto.server.*`。

### 10.4 Helm 配置

每个集群各自使用的 values（结构参考上游配置指南；内部 LB 注解采用 AWS Load Balancer Controller 的标准 scheme 注解；本次未核实 chart 注释中是否也提供此说明）：

```yaml
# cluster1.yaml
cluster:
  name: cluster1
  id: 1
clustermesh:
  useAPIServer: true
  config:
    enabled: true
  apiserver:
    service:
      type: LoadBalancer
      annotations:
        service.beta.kubernetes.io/aws-load-balancer-scheme: internal
    tls:
      auto:
        enabled: true
        method: cronJob
        server:
          extraDnsNames:
            - cluster1.example.com
```

```yaml
# clusters.yaml  (shared; the local cluster entry is ignored by each cluster)
clustermesh:
  config:
    clusters:
      cluster1:
        address: cluster1.example.com
        port: 2379
      cluster2:
        address: cluster2.example.com
        port: 2379
```

复制 CA 后，使用已安装的相同 chart 版本应用配置（这是允许使用 `--reuse-values` 的唯一情况，上游指南也采用此方式）：

```bash
helm upgrade cilium oci://quay.io/cilium/charts/cilium --version 1.20.2 -n kube-system \
  --kube-context $CLUSTER1 --reuse-values -f clusters.yaml -f cluster1.yaml

kubectl --context $CLUSTER1 get secret -n kube-system cilium-ca -o yaml | \
  kubectl --context $CLUSTER2 create -f -

helm upgrade cilium oci://quay.io/cilium/charts/cilium --version 1.20.2 -n kube-system \
  --kube-context $CLUSTER2 --reuse-values -f clusters.yaml -f cluster2.yaml
```

Service 暴露方式：`clustermesh.apiserver.service.type` 默认为 `NodePort`（`nodePort: 32379`）。上游建议使用 `LoadBalancer` 获得稳定地址；`NodePort` 需要稳定的节点 IP；使用 `ClusterIP` 时，集群间必须能路由 ClusterIP。在 AWS 上，应始终设置 `service.beta.kubernetes.io/aws-load-balancer-scheme: internal`（并将 `loadBalancerSourceRanges` 限制为对等 VPC CIDR），或通过 peering/TGW 使用 NodePort/ClusterIP；面向互联网的 LB 违反本仓库政策，并会暴露 mesh 信任域。还应配置安全组，仅允许来自对等集群节点安全组或私有 CIDR 的 TCP 2379。

部分 mesh：为每个集群配置 `clusters` map，其中只包含它需要连接的集群。也支持为每个集群设置静态 `ips`；**[1.21 预发布版]** 更改静态 IP 时不再重启 Pod，且 `clustermesh.apiserver.service.port` 可配置。

CLI 替代方式（对 Helm 的封装，适合实验环境）：

```bash
cilium install --set cluster.name=$CLUSTER1 --set cluster.id=1 --context $CLUSTER1
cilium install --set cluster.name=$CLUSTER2 --set cluster.id=2 --context $CLUSTER2
cilium clustermesh enable --context $CLUSTER1
cilium clustermesh enable --context $CLUSTER2
cilium clustermesh connect --context $CLUSTER1 --destination-context $CLUSTER2   # one direction is enough
cilium clustermesh status --context $CLUSTER1 --wait
cilium connectivity test --context $CLUSTER1 --multi-cluster $CLUSTER2
```

### 10.5 Namespace：`defaultGlobalNamespace`

`clustermesh.defaultGlobalNamespace`（默认值 `true`；存在于 1.20.2 chart 中，不在 1.19.8 chart 中）用于控制是否导出 namespace 的 CiliumEndpoints、CiliumIdentities 和 Service。为 namespace 添加注解 `clustermesh.cilium.io/global: "true"` 或 `"false"` 可以覆盖默认值。跨集群连通性和策略要求源、目标 namespace 都是 global；Global Service 也必须位于 global namespace 中，并带有对应的 Service 注解。将默认值设为 `false` 可减少集群间同步的状态量，有助于扩展。

### 10.6 数据过期：`cacheTTL`

`clustermesh.cacheTTL` 默认值为 `"0s"`：断开连接的远程集群缓存数据永远不会被撤销。可设置一个时长（例如 `"15m"`），在该时长内连接仍未恢复时清除过期远程数据。

## 11. 全局 Service、Affinity 和 EndpointSlice 同步

Global Service 在每个集群中使用相同的 Service 名称和 namespace，并带有注解 `service.cilium.io/global: "true"`。来自所有集群的后端会合并到一起。

| 注解 | 效果 |
|---|---|
| `service.cilium.io/global: "true"` | 将 Service 设为全局。如果任一集群未设置此项或设为 false，则该集群中的 Service 仍为本地 Service |
| `service.cilium.io/shared: "false"` | 不导出此集群的后端，但仍消费远程后端。如果双方都设为 global 且两边都启用 shared，则每个集群都会看到本地和远程后端；设置 `shared: "false"` 的集群不导出任何后端 |
| `service.cilium.io/affinity: none\|local\|remote` | `local`：优先使用健康的本地后端，仅当所有本地后端都不可用时才回退到远程后端；`remote` 的行为相反；`none`（默认值）表示不偏好任何一方 |
| `service.cilium.io/global-sync-endpoint-slices: "true"` | **Beta。** 同时为远程后端创建 EndpointSlice，使第三方 controller 能看到它们；需要启用 Helm 配置 `clustermesh.enableEndpointSliceSynchronization=true` 并重启 operator。Headless Global Service 默认启用此项 |

```yaml
apiVersion: v1
kind: Service
metadata:
  name: rebel-base
  annotations:
    service.cilium.io/global: "true"
    service.cilium.io/affinity: "local"
spec:
  type: ClusterIP
  ports:
  - port: 80
  selector:
    name: rebel-base
```

使用 `cilium-dbg service list --clustermesh-affinity` 检查 affinity（首选后端会显示 `(preferred)`）。限制：Global NodePort 和 host-network 客户端只有在使用 kube-proxy 替换时（或设置 `socketLB.enabled=true` 和 `socketLB.hostNamespaceOnly=true` 时）才能将流量负载均衡到远程后端。即使未启用 EndpointSlice 同步，Cilium ingress controller 也能在 mesh 中工作；其他 ingress controller 可能需要 EndpointSlice 同步。1.19 新增指标：`cilium_agent_clustermesh_remote_cluster_endpoints`。

## 12. MCS-API（Multi-Cluster Services）

MCS-API 是 Kubernetes SIG-Multicluster API：`ServiceExport` 用于发布 Service，每个集群都会获得一个 `ServiceImport`，其 DNS 名称为 `<svc>.<ns>.svc.clusterset.local`。Cilium 会将导入项实现为名为 `derived-<hash>` 的派生 Service，并复用 Global Services 机制，因此两种机制可以兼容使用。

| 项目 | 值 |
|---|---|
| 成熟度 | 1.19 为 beta（CRD `multicluster.x-k8s.io/v1alpha1`）；1.20 为 stable（`v1beta1`，仍支持 `v1alpha1`） |
| 启用 | `clustermesh.mcsapi.enabled=true`（替代已移除的 `clustermesh.enableMCSAPISupport`） |
| CRD | 由 chart 安装（`clustermesh.mcsapi.installCRDs`，默认值 true） |
| CoreDNS | `clustermesh.mcsapi.corednsAutoConfigure.enabled`（需要 CoreDNS >= 1.12.2，该版本是 Kubernetes >= 1.35 的默认版本）。手动配置：ClusterRole `coredns-mcsapi`（对 `serviceimports` 具有 list/watch 权限），以及 CoreDNS 插件 `multicluster clusterset.local` |
| Namespace | 每个集群都必须存在该 Service 所属的 namespace |

```yaml
apiVersion: multicluster.x-k8s.io/v1beta1
kind: ServiceExport
metadata:
  name: rebel-base
spec:
  exportedLabels:
    app.kubernetes.io/name: rebel-base
  exportedAnnotations:
    service.cilium.io/affinity: local
```

跨导出项协调的属性：SessionAffinity、Ports（取并集）、Type（ClusterSetIP 或 Headless）、InternalTrafficPolicy、TrafficDistribution，以及 labels/annotations。出现冲突时，Cilium 会在 `ServiceExport` 状态中设置冲突 condition，并按创建时间先后处理，优先采用最早创建的对象，因此应修复冲突，不要依赖自动处理顺序。不支持按集群区分的 DNS 名称；请分别导出 `mysvc-eu` 和 `mysvc-us`。StatefulSet Pod 的主机名解析格式为 `<hostname>.<cluster>.<svc>.<ns>.svc.clusterset.local`。Gateway API 可将 `ServiceImport` 用作 `backendRef`。**[1.21 预发布版]** 前缀移除后名称超过 40 个字符的镜像 EndpointSlice 可能会在升级时重新创建，造成短暂中断。

## 13. 跨集群策略

- **默认范围（1.19 起）**：selector 只匹配本地集群中的 endpoint（`policy-default-local-cluster`，Helm 配置 `clustermesh.policyDefaultLocalCluster: true`）。直到 1.18 为止，默认范围是所有集群。从 1.18 升级前，请使用 `cilium clustermesh inspect-policy-default-local-cluster --all-namespaces`（或 `-p <namespace>`）进行审查；这里早先的一条说明称该命令的 CLI 问题已在 1.21 pre.3 源码树中修复，但尚未核实，因此请在你使用的 CLI 版本中确认命令输出。
- **使用标签 `io.cilium.k8s.policy.cluster` 选择远程集群：**

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: allow-cross-cluster
spec:
  endpointSelector:
    matchLabels:
      name: x-wing
  egress:
  - toEndpoints:
    - matchLabels:
        name: rebel-base
        io.cilium.k8s.policy.cluster: cluster2
```

要选择任意集群，请改用 `matchExpressions: [{key: io.cilium.k8s.policy.cluster, operator: Exists}]`。

- **Entity**：除非被限制为本地集群（1.18 选项），否则 `cluster` 包含 mesh 中的远程节点；1.20 新增 `cluster-mesh`，涵盖 mesh 集群中的所有 endpoint，并包含 `cluster` 中的全部内容。
- 策略不会复制到其他集群：必须在每个集群分别应用。
- Cluster Mesh 不支持 mutual authentication（SPIRE），且该功能会在 1.21 预发布版中彻底移除；根据本仓库的 service mesh 说明，ztunnel 也不支持与 Cluster Mesh 同时使用。参见 [mTLS、加密与身份](12-mtls-encryption-identity.md)。
- Host firewall 与 Cluster Mesh 组合使用时存在限制（`host.rst`）。数据平面加密与控制平面使用的 mTLS 相互独立；WireGuard 或 IPsec 必须在所有集群中以相同方式配置，并且集群之间必须开放 UDP 51871。此处未重新核实 Cluster Mesh 与加密组合使用时的具体注意事项。

## 14. 在 EKS 上运行 Cluster Mesh

上游的 `eks-clustermesh-prep.rst` 使用 `eksctl`、两个 CIDR 不重叠的 VPC（例如 `10.0.0.0/16` 和 `10.1.0.0/16`，并避开 `172.17.0.0/16`）、VPC peering，以及允许来自自身和对等 VPC 的流量的安全组。该指南还创建了带 Internet Gateway 的公共子网。对于本仓库，请按以下方式调整：

- 节点仅使用私有子网；节点不分配公共 IP 或 EIP。
- 建立 VPC peering（或使用 Transit Gateway），并在私有路由表中添加到对等 CIDR 的路由。
- 安全组规则引用两个集群的节点安全组（或私有 CIDR）；绝不要使用 `0.0.0.0/0` 或 `::/0`。
- 通过内部 NLB（`aws-load-balancer-scheme: internal`）或经 peering 链路的 NodePort 暴露 clustermesh-apiserver，并将 `loadBalancerSourceRanges` 限定为对等 VPC CIDR。
- ENI 模式会为 Pod 分配可由 VPC 路由的 IP，因此原生路由只需确保 `ipv4NativeRoutingCIDR` 覆盖两个 VPC 的 Pod 地址范围。Overlay 模式只需要节点间可达（UDP 8472）。
- 为每个 EKS 集群使用不同的 `cluster.name`/`cluster.id`，并设置相同的 `maxConnectedClusters`。ENI 模式下将 `cluster.id` 保持在 128 以下，因为除非设置 `extraConfig.allow-unsafe-policy-skb-usage=true`，否则 chart 会拒绝 128-255（以及 `maxConnectedClusters: 511` 时的 384-511）（`validate.yaml:160-168`）。

## 15. 实验

> 本次审查没有在真实集群上运行这些实验；仅根据上游源代码和文档进行了核对。请只在可随时销毁的集群中运行。

### 实验 1：双集群 Cluster Mesh

前置条件：两个可互相访问节点的临时集群（同一 Docker 主机上的两个 kind 集群，并设置不同的 `networking.podSubnet`/`serviceSubnet` 和 `disableDefaultCNI: true`；或两个位于已建立 peering 的 VPC 中的 EKS 集群）、Helm 3、Cilium CLI 0.20.1，以及 `$CLUSTER1`/`$CLUSTER2` context。

1. 在每个集群安装 Cilium 1.20.2，设置不同的 `cluster.name`、`cluster.id` 和不重叠的 Pod CIDR（cluster-pool 列表必须不同）。
2. 复制 CA：`kubectl --context $CLUSTER1 get secret -n kube-system cilium-ca -o yaml | kubectl --context $CLUSTER2 create -f -`。
3. 应用第 10.4 节的 values 文件。在没有负载均衡器的 kind 中，设置 `service.type: NodePort`，并在 `clustermesh.config.clusters.<name>.ips` 中列出节点 IP，端口设为 `32379`。
4. 运行 `cilium clustermesh status --context $CLUSTER1 --wait`，然后运行 `cilium connectivity test --context $CLUSTER1 --multi-cluster $CLUSTER2`。

验证：`cilium clustermesh status` 显示 clustermesh-apiserver 已就绪且远程集群已连接；`kubectl exec -n kube-system ds/cilium -c cilium-agent -- cilium-dbg status --all-clusters` 将远程集群列为就绪，并显示其 cluster ID，且所有 `synchronization status` 都为 true；`cilium-dbg node list` 中包含远程节点。

清理：在两个集群都运行 `helm uninstall cilium -n kube-system`，或删除临时集群。连接失败时回滚：移除 `-f clusters.yaml` 中的条目，然后使用相同 chart 版本再次运行 `helm upgrade`。

### 实验 2：全局 Service、`shared` 和 affinity

前置条件：完成实验 1。

1. 在两个集群中创建同名 namespace、Deployment 和 Service `rebel-base`，添加 `service.cilium.io/global: "true"`；让 Pod 返回所在集群的名称。
2. 在集群 1 的客户端 Pod 中循环执行 curl，并观察来自两个集群的响应。
3. 为集群 1 的 Service 添加注解 `service.cilium.io/affinity=local` 后重试；此时响应只来自集群 1。将本地后端缩放到零，观察流量是否切换到集群 2。
4. 在集群 2 中设置 `service.cilium.io/shared: "false"`，并观察集群 1 不再看到集群 2 的后端，而集群 2 仍可访问集群 1。

验证：agent 中的 `cilium-dbg service list --clustermesh-affinity` 显示首选后端；`cilium-dbg bpf lb list` 显示远程后端地址。

清理：在两个集群中删除该 namespace。

### 实验 3：MCS-API

前置条件：完成实验 1，并启用 `clustermesh.mcsapi.enabled=true` 和 `corednsAutoConfigure.enabled=true`（如果手动配置 CoreDNS，请重启 CoreDNS）。

1. 在两个集群中创建 namespace 和 Service，然后分别创建一个同名 `ServiceExport`。
2. 从 Pod 中解析 `rebel-base.<namespace>.svc.clusterset.local` 并通过 curl 访问。
3. 使两个集群公开的端口不同，并检查 `kubectl get serviceexport -o yaml` 中的冲突 condition。

验证：两个集群中都存在 `ServiceImport`，并出现名为 `derived-<hash>` 的派生 Service；DNS 名称可解析。

清理：删除 ServiceExport、Service 和 namespace。

### 实验 4：使用漂移检测进行升级演练

前置条件：临时集群运行 1.19.8，并从 values 文件安装；Prometheus metrics endpoint 可访问（或使用 `cilium-dbg metrics list`）。

1. 保存 values：`helm get values cilium -n kube-system -o yaml > old-values.yaml`。
2. 对 1.20.2 运行预检 chart，确认检查通过后将其删除。
3. 使用 `--version 1.20.2 -f old-values.yaml --set upgradeCompatibility=1.19` 执行升级。
4. 使用 `cilium config set --restart=false <key> <value>` 修改一个只能通过重启 agent 才生效的 ConfigMap 键，并读取漂移指标：`kubectl -n kube-system exec ds/cilium -c cilium-agent -- cilium-dbg metrics list | grep drift_checker_config_delta`。
5. 回滚：先运行 `helm history cilium -n kube-system`，再运行 `helm rollback cilium <REVISION> -n kube-system`。

验证：第 4 步后 `cilium_drift_checker_config_delta` 非零，agent 重启后回到 0；升级和回滚后 `cilium status` 均显示正常。

清理：删除临时集群。回滚说明：本实验用于演练回滚路径；不要在使用了仅存在于 1.20 的功能的集群上执行。

### 实验 5：按节点覆盖 CiliumNodeConfig

前置条件：任意 Cilium 1.20.2 集群，且至少有两个节点。

1. 为一个节点添加标签：`kubectl label node <node> io.cilium.test-override=true`。
2. 在 `kube-system` 中应用一个选择该标签的 `CiliumNodeConfig`，并设置一个无害的 `defaults` 键，例如 `debug: "true"`。
3. 分别删除带标签节点和未带标签节点上的 agent Pod。

验证：带标签节点上重建的 agent 会在有效配置中（`cilium-dbg config`）显示覆盖值；未带标签节点上的 agent 不显示该值。

清理：删除 CiliumNodeConfig、移除标签，并再次重建 agent Pod。

## 版本差异

| 项目 | 1.18 | 1.19 | 1.20 | 1.21 pre.3 |
|---|---|---|---|---|
| 最低内核版本 | 5.10 | 5.10 | 5.10 | 5.10（LLVM 21.1） |
| Gateway API CRD | 1.3.0 | 1.4 | 1.6.1 | 1.6.1 |
| Helm OCI chart | 否 | 是 | 是（推荐） | 是 |
| MCS-API | beta | beta（`v1alpha1`，自动安装 CRD） | stable（`v1beta1`） | `v1beta1` |
| Cluster Mesh 策略默认范围 | 所有集群 | 仅本地集群 | 仅本地集群；`cluster-mesh` entity | 仅本地集群 |
| authMode 默认值 | `legacy` | `migration` | `migration` | `cluster`（以及 `cluster-strict`） |
| KVStoreMesh | `enabled` 已弃用 | 默认启用 | 默认启用 | 始终启用 |
| 双向身份验证 | 存在 | 默认禁用 | 已弃用 | 已移除 |
| Kafka L7 / proxylib | 已弃用 | Kafka 已弃用 | 已移除 | 已移除 |
| BGPv1 | 已弃用 | 已移除 | - | - |
| Multi-pool IPAM | beta | stable | 另支持从 cluster-pool 迁移 | Azure IPAM 迁移到 multi-pool |
| Double Write | beta | beta | beta | beta；`migrate-identity` 已弃用 |
| configDriftDetection | 已回移 | 已回移 | 原生支持 | 相同 |
| ENI masquerade 默认值 | IPv4 改为 false | false | false | IPv6 masquerade 关闭 |

## 故障排除

| 症状 | 检查方法 |
|---|---|
| 远程集群未连接 | `cilium clustermesh status --wait`；`kubectl exec -n kube-system ds/cilium -c cilium-agent -- cilium-dbg troubleshoot clustermesh [cluster...]`（DNS、连通性、TLS、etcd 授权）；启用 KVStoreMesh 时还要运行 `kubectl exec -n kube-system deploy/clustermesh-apiserver -c kvstoremesh -- clustermesh-apiserver kvstoremesh-dbg troubleshoot` |
| 远程集群状态 | `cilium-dbg status --all-clusters`（节点、endpoint、身份、Service、MCS-API export、重连、`has-quorum`、`cluster-id`、`kvstoremesh`、同步状态）；`... kvstoremesh-dbg status --verbose` |
| 日志 | agent：`New remote cluster configuration`、`Connection to remote cluster established`、`Unable to establish etcd connection to remote cluster`；`kubectl logs -n kube-system deployment/clustermesh-apiserver -c apiserver` |
| TLS 错误 | CA 不同（复制 `cilium-ca`）、证书过期（使用 `helm` 方法一年后）、`authMode` 对应的 CN 不正确；Secrets：`cilium-clustermesh` 和 `cilium-kvstoremesh` |
| 无法解析 `*.mesh.cilium.io` | 在 DaemonSet（未使用 KVStoreMesh）或 clustermesh-apiserver Deployment（使用 KVStoreMesh）上设置 hostAliases，将 `cluster1.mesh.cilium.io` 映射到 LB IP |
| 端口 | 安全组必须通过引用或私有 CIDR 允许 TCP 2379 |
| 跨集群流量被拒绝 | 检查 `cilium-dbg identity list`（标签 `io.cilium.k8s.policy.cluster`）、`cilium-dbg bpf ipcache list`、`cilium-dbg service list`、`cilium-health status`；注意 1.19 起的本地集群默认策略范围，并确认两个 namespace 都设为 global |
| CIDR 重叠或 ID 重复 | `cilium-dbg node list` 显示冲突的节点范围；修复需要重新分配 IP，并重启工作负载 |
| 旧集群升级到 1.20 时卡住 | 使用 1.20.2 或更高版本（修复了 `CiliumNodeConfig v2alpha1` CRD 问题） |
| 配置更改未生效 | `cilium_drift_checker_config_delta > 0`：重启 agent |

## 验证限制与来源

本次审查没有在真实集群上执行实验；核对时使用了下方标签对应的上游源代码和文档。无法核实的事实列在这里，而不作为确定结论：

- Cilium 1.21 是否默认启用 BPF masquerading。pre.2 发行说明称其已启用，但 pre.3 源码树中 daemon 默认值为 `false`，chart 的 `bpf.masquerade` 默认值为 false，且 `upgrade-next.inc` 的“Changed Options”一节为空。
- Cluster Mesh 与 WireGuard/IPsec 组合使用时的确切限制尚未重新核实。
- EKS 上 chaining 模式的限制；移除 EKS 托管 kube-proxy add-on 的确切命令；Amazon Linux 2023 是否按名称列出。
- 超出 1.17.9-0 和 1.18.3-0 的 AWS 维护版 Cilium 构建版本。
- `bpf.tproxy` 和 ENI IPv6 除引用的“beta”外的成熟度信息。
- 1.19.0 的发布日期和 1.17 的确切 Kubernetes 测试矩阵。
- MCS-API 的“stable”标签来自 v1.20.0 发行说明正文；源码确认 beta 横幅已移除，且 CRD 为 `v1beta1`。
- Double Write 指标名称：上游升级页面与代码不一致（第 8.3 节）；此处采用 v1.20.2 的代码信息。
- Chart 默认 `kubeVersion` 是 chart 约束，而非已测试的 Kubernetes 版本范围。

来源：

- [Cilium v1.20.2 文档：operations/upgrade.rst](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/operations/upgrade.rst)
- [v1.20.2 升级说明](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/operations/upgrade-current.inc)
- [v1.20.2 Cluster Mesh 文档](https://github.com/cilium/cilium/tree/v1.20.2/Documentation/network/clustermesh)
- [v1.20.2 Cluster Mesh 故障排除](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/operations/troubleshooting_clustermesh.rst)
- [v1.20.2 Helm 安装和 EKS](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/installation/k8s-install-helm.rst)，[requirements-eks.rst](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/installation/requirements-eks.rst)
- [v1.20.2 ENI IPAM](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/concepts/ipam/eni.rst)
- [v1.20.2 系统要求](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/operations/system_requirements.rst)
- [v1.20.2 逐节点配置](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/configuration/per-node-config.rst)，[ConfigMap 漂移检测](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/configuration/configmap-drift-detection.rst)
- [v1.20.2 Helm values](https://github.com/cilium/cilium/blob/v1.20.2/install/kubernetes/cilium/values.yaml)
- [v1.20.2 Double Write 指标代码](https://github.com/cilium/cilium/blob/v1.20.2/operator/doublewrite/metrics.go)
- [v1.21.0-pre.3 升级说明](https://github.com/cilium/cilium/blob/v1.21.0-pre.3/Documentation/operations/upgrade-next.inc)，[values.yaml](https://github.com/cilium/cilium/blob/v1.21.0-pre.3/install/kubernetes/cilium/values.yaml)
- 发行说明：[v1.20.2](https://github.com/cilium/cilium/releases/tag/v1.20.2)、[v1.20.0](https://github.com/cilium/cilium/releases/tag/v1.20.0)、[v1.19.0](https://github.com/cilium/cilium/releases/tag/v1.19.0)、[v1.18.0](https://github.com/cilium/cilium/releases/tag/v1.18.0)、[v1.17.0](https://github.com/cilium/cilium/releases/tag/v1.17.0)、[v1.21.0-pre.3](https://github.com/cilium/cilium/releases/tag/v1.21.0-pre.3)
- AWS：EKS 用户指南中关于替代 CNI 插件、Auto Mode 网络和 hybrid node CNI 的页面。

## 小测

使用[第 13 部分小测](../../quizzes/networking/cilium/13-clustermesh-install-upgrade-quiz.md)检验自己。
