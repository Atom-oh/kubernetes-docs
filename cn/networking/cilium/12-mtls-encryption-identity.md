# 第 12 部分：mTLS、透明加密与身份

> **审查基线**：Cilium 1.20.2（稳定版，2026-09-16）；Cilium CLI 0.20.1；Hubble CLI 1.20.2。标记为 **[1.21 预发布版]** 的内容来自 v1.21.0-pre.3，在 GA 前可能变化。
> **最后更新**：2026 年 10 月 15 日

Cilium 的安全模型包含三个容易混淆的层次。**身份和策略**依据标签，而非 IP，决定谁可以与谁通信。**透明加密**（WireGuard、IPsec）保护节点间线路上传输的数据。**工作负载 mTLS**（ztunnel）则将加密通道绑定到工作负载身份。本章从机制讲起，逐层说明这些功能，然后介绍已移除的 Mutual Authentication 功能、Service Mesh 选项、Hubble/Tetragon 和证书管理。

相关章节：[eBPF 数据路径内部机制](08-ebpf-datapath-internals.md)、[Overlay 和原生路由](09-overlay-native-routing.md)（隧道与 MTU 的相互影响）、[IPAM](10-ipam-deep-dive.md)、[BGP、LB 和出口流量](11-bgp-lb-egress-edge.md)、[ClusterMesh、安装和升级](13-clustermesh-install-upgrade.md)。策略基础见 [IPAM 和 Network Policy](04-ipam-policy.md)；本章会深入讲解。可观测性入门见[安全和可见性](06-security-visibility.md)。

## 功能成熟度和时间线一览

| 功能 | 1.18 | 1.19 | 1.20（稳定版） | 1.21 预发布版 |
|---|---|---|---|---|
| Mutual Authentication（SPIFFE/SPIRE、`authentication.mode: required`） | Beta | Beta，`authentication.enabled` 默认为 false | **已弃用**（文档标题仍为“Beta”） | **已移除** |
| ztunnel 透明加密（`encryption.type=ztunnel`） | - | Beta（新增） | Beta，新增 `ca.type` | Beta |
| WireGuard | 稳定 | 稳定 | 稳定 | 稳定 |
| IPsec | 稳定 | 稳定 | 稳定 | 稳定 |
| WireGuard `encryption.nodeEncryption` | 未核查 | 未核查 | Beta | **已弃用，计划在 1.22 移除** |
| Double Write 身份迁移 | 已有文档 | 已有文档 | 已有文档 | 弃用 `cilium-dbg preflight migrate-identity`，建议改用 Double Write |
| `identityManagementMode` | 未核查 | 未核查 | Beta | Beta |
| CiliumEndpointSlice | 未核查 | 未核查 | Beta | Beta |
| Kubernetes ClusterNetworkPolicy 支持 | - | - | 新增 alpha API（v1alpha2） | alpha |

最常被错误描述的是 Mutual Authentication 一行。准确的记录如下：

- 在 1.18、1.19 和 1.20 中均为 **Beta**（1.20 文档页面标题仍为“Mutual Authentication (Beta)”）。
- 在 1.20 中**弃用**：1.20 升级说明称其“现已弃用，未来版本将移除”，并指向 ztunnel。
- 在 1.21 中**移除**：1.21 升级说明称其“已在弃用后移除”，并要求升级前移除相关配置。
- 1.21 中为兼容 CRD 而保留 policy API 的 `authentication` 字段，但该字段**不再使用**。

## 身份模型

### 标签映射为数字身份

Cilium 不基于 IP 地址执行策略。每个端点（Pod）都会分配一个**安全身份**，即由与身份相关的标签派生出的数字 ID。标签集合相同的端点共享一个 ID，因此一条 policy map 条目可以覆盖某个 Deployment 的所有副本，且 Pod IP 变化不会影响策略判断。

```
Pod labels (k8s:app=web, k8s:io.kubernetes.pod.namespace=shop, ...)
        |  filter by identity-relevant labels
        v
label set  -->  allocator (CRD or kvstore)  -->  numeric identity, e.g. 31337
        |
        +--> CiliumEndpoint.status.identity (published)
        +--> ipcache:  podIP -> identity   (every node learns it)
        +--> source node stamps identity into the packet (tunnel metadata)
                or the destination node resolves srcIP via ipcache
        +--> destination node: policy map lookup (local endpoint, remote identity, port, proto)
```

在目标端，查询键为本地端点、远端身份、端口和协议。身份会随数据包传输（overlay 模式下放在隧道 metadata 中），也可以在原生路由模式下通过 ipcache 根据源 IP 恢复；因此，ipcache 条目过期或缺失通常是策略问题的症状。

### 32 位数字身份布局

作用域存放在第 24–31 位：

| 作用域 | 值 | 用途 |
|---|---|---|
| 全局 | 0 | 通过 CRD/kvstore allocator 分配的身份；第 0–23 位分配给身份 ID 和 cluster ID |
| 本地 | `1<<24` | 只存在于单个节点上的身份：由 CIDR 和 FQDN 派生的身份 |
| 远端节点 | `2<<24` | 用于按节点选择策略的节点身份 |

使用 ClusterMesh 时，低 24 位由身份和 cluster ID 共用：`max-connected-clusters` 为 255 时，身份占 16 位、cluster ID 占 8 位；为 511 时，分别占 15 位和 9 位。低于 256 的身份为保留值（`MinimalIdentity=256`）。常量见 v1.21.0-pre.3 中的 `pkg/identity/numericidentity.go`。ClusterMesh 容量规划见[第 13 部分](13-clustermesh-install-upgrade.md)。

### 保留身份和已知身份

保留身份取自数据路径常量（v1.21.0-pre.3 的 `pkg/datapath/types/types_generated.go`）：

| ID | 名称 | 含义 |
|---|---|---|
| 0 | unknown | 身份尚未解析 |
| 1 | host | 本地节点 |
| 2 | world | 集群外的所有对象（也是 `0.0.0.0/0` 的 CIDR 身份） |
| 3 | unmanaged | 不由 Cilium 管理的端点 |
| 4 | health | Cilium health 端点 |
| 5 | init | 标签尚未确定的端点（Pod 启动期间） |
| 6 | remote-node | 集群中的其他节点 |
| 7 | kube-apiserver | Kubernetes API Server |
| 8 | ingress | Cilium 管理的 ingress/Envoy |
| 9 / 10 | world-ipv4 / world-ipv6 | 按地址族拆分的 world |
| 11–14 | 聚合身份（cluster、clustermesh、world、remote-node） | 用于聚合 policy map，不直接应用于流量 |

上游术语页面只列出 ID 0–8，因此 9 和 10 只会出现在源码中。依据术语页面和 `numericidentity.go`，有些已知身份无需经过 kvstore 或 CRD 往返即可存在，包括 `kube-dns`（102）、EKS 上的 `kube-dns`（103）、`coredns`（104）、`cilium-operator`（105）和 EKS 上的 `coredns`（106）。它们对 EKS 很重要，因为默认 DNS Pod 会分配固定 ID。

请记住以下行为：标签尚未解析时，Pod 会处于 `reserved:init`；在 tunnel 模式下，抵达后端的南北向 Service 流量身份为 `reserved:world`；在原生路由模式下，如果数据包到达托管后端的节点，身份为 `world`，否则为 `remote-node`（因此 `fromEntities: cluster` 能匹配它）。请参阅 `Documentation/security/policy/caveats.rst`。

### 与身份相关的标签和身份变化

默认情况下，除排除清单中的标签外，所有标签都与身份相关；排除项示例：`io.kubernetes`、`kubernetes.io`、StatefulSet Pod 名称、`pod-template-hash`、`controller-revision-hash`、`annotation.*` 和 `topology.kubernetes.io`。匹配模式为从标签开头锚定的正则表达式。

- 加入任何**包含型**模式都会让 agent 切换到 allow-list 模式，并自动加入 `reserved:`、Pod namespace、namespace 标签、`policy.cluster`、service account 和 `app.kubernetes.io`。
- Helm 的 `labels:` 会在默认项上**追加**。若要精确替换清单，请使用 `--label-prefix-file`（agent flags 为 `--labels` 和 `--label-prefix-file`）。
- Agent 重启之前，现有身份不会变化；之后 operator 会清理旧身份。
- 每个 release 或 Pod 都会变化的标签（build SHA、时间戳）会为每个值各生成一个身份。这会增加身份、ipcache 条目和 policy map 条目数量。应将这类标签排除在身份之外。

来源：`Documentation/operations/performance/scalability/identity-relevant-labels.rst`。

### 身份分配模式

| Helm `identityAllocationMode` | 存储后端 | 说明 |
|---|---|---|
| `crd`（chart 默认值） | `CiliumIdentity`（cilium.io/v2，集群范围） | 不依赖外部服务 |
| `kvstore` | etcd | 已经运行 etcd 的大型集群 |
| `doublewrite-readkvstore` | 同时写入两处，从 kvstore 读取 | 迁移阶段 |
| `doublewrite-readcrd` | 同时写入两处，从 CRD 读取 | 迁移阶段 |

配置时要注意：**agent flag** 的默认值是 `kvstore`，但 **Helm chart** 默认设为 `crd`。应从 ConfigMap 读取生效值，不要只查看 `cilium-agent --help`。

**Double Write 迁移**（Beta）可在后端间迁移而不中断身份。kvstore 迁移到 CRD 时，依次设置 `doublewrite-readkvstore`、`doublewrite-readcrd`、`crd`。先部署 Operator，再部署 Agents（最后切换回 `crd` 时，按升级指南应先部署 Agents，再部署 Operator）。此顺序可逆。Operator gauges `doublewrite_{crd,kvstore,crd_only,kvstore_only}_identities` 可观测收敛情况，对外显示为 `cilium_operator_doublewrite_crd_identities`、`cilium_operator_doublewrite_kvstore_identities`、`cilium_operator_doublewrite_crd_only_identities` 和 `cilium_operator_doublewrite_kvstore_only_identities`（v1.20.2 `operator/doublewrite/metrics.go:13-33`；`Documentation/observability/metrics.rst` 列出的名称相同）。v1.20.2 升级指南（`Documentation/operations/upgrade.rst`）仍提到旧的 `cilium_operator_identity_*_count` 名称，但代码已不再注册这些名称；不要为它们设置告警。进入下一步前，等待两个 `*_only_identities` 值都降至零。1.21 中 `cilium-dbg preflight migrate-identity` 已弃用，建议改用 Double Write。来源：`Documentation/operations/upgrade.rst`。

### Operator 管理的身份（Beta）

Helm `identityManagementMode` 可设为 `agent`（默认）、`operator` 或 `both`（仅迁移期间使用）。设为 `operator` 后，由 operator 分配身份，避免多个 agent 同时创建重复 CIDR 身份。

1. 从 agent 切换到 operator：设置 `both`，重启 operator；再设置 `operator`，重启 agents。
2. 降级时：先让 agents 使用 `both`，再将 operator 改为 `agent`。
3. 更改与身份相关的标签模式后，同时重启 operator 和 agents（`both`）。

相关配置：chart 中的 `operator.identityGCInterval`（15m0s）和 `identityHeartbeatTimeout`（30m0s）；agent flags 为 `identity-allocation-timeout`（2m）、`identity-change-grace-period`（5s）和 `identity-restore-grace-period`（30s）。

### CiliumEndpoint、CiliumEndpointSlice 和 ipcache

- **CiliumEndpoint（CEP）**：每个 Cilium 管理的 Pod 对应一个对象，名称和 namespace 与 Pod 相同。Status 包含标签、身份 ID 和生效策略。`cilium-health-<node>` CEP 位于 `kube-system`。
- **CiliumEndpointSlice（CES，Beta；CRD 仍为 cilium.io/v2alpha1）**：operator 会将精简后的 CEP 批量写入 CES 对象，agents 则 watch CES。这样可以降低 API Server 负载，但学习新端点身份会有延迟。Helm `ciliumEndpointSlice.enabled`（默认 false）和 `rateLimits` 可配置此功能；namespace annotation `cilium.io/ces-namespace: priority` 可以提高某个 namespace 的优先级。与 Egress Gateway 不兼容。迁移时先升级 operator，再升级 agents；降级时先降级 agents。`--ces-slice-mode` flag 在 1.20 已移除。
- **ipcache**：BPF map `cilium_ipcache_v2` 将 IP 或 CIDR 映射到身份。使用 `cilium-dbg bpf ipcache list|get|match` 和 `cilium-dbg identity list|get` 检查。
- 每个端点都有一个 policy map，由 `--bpf-policy-map-max` 控制大小（默认 16384）。

策略中使用许多不同 CIDR 会创建大量本地作用域身份（每个 CIDR selector 一个），因此更推荐在下文使用 `CiliumCIDRGroup`。

### 检查身份状态

```bash
kubectl get ciliumidentities
kubectl get cep -A -o wide
kubectl -n kube-system exec ds/cilium -- cilium-dbg identity list
kubectl -n kube-system exec ds/cilium -- cilium-dbg bpf ipcache list
kubectl -n kube-system exec ds/cilium -- cilium-dbg endpoint list
```

## 深入了解策略模型

### 策略资源

| 资源 | 范围 | 说明 |
|---|---|---|
| Kubernetes `NetworkPolicy` | namespace | L3/L4 |
| `CiliumNetworkPolicy`（CNP，cilium.io/v2） | namespace | L3-L7、entities、FQDN、deny |
| `CiliumClusterwideNetworkPolicy`（CCNP） | 集群 | 也可通过 `nodeSelector` 设置 host policy |
| `ClusterNetworkPolicy`（policy.networking.k8s.io，v1alpha2） | 集群 | **1.20 新增**，alpha API；需明确启用 |
| `CiliumCIDRGroup` | 集群 | 规则可引用的命名 CIDR 集合 |

语义：规则构成 allow-list，并采用并集；执行是有状态的（允许回复流量）；只要有规则选择了某个端点的某个方向，该方向就会切换到默认拒绝。

### 执行模式、默认拒绝和审计模式

| 控制项 | 设置 | 效果 |
|---|---|---|
| `policyEnforcementMode`（flag `enable-policy`） | `default` / `always` / `never` | `default`：端点被选中前默认开放；`always`：所有端点默认拒绝；`never`：关闭策略 |
| 规则中的 `enableDefaultDeny: {ingress, egress}` | 按规则设置 | 规则选择端点时，不会让对应方向切换为默认拒绝 |
| Helm `enableNonDefaultDenyPolicies` | true | 在 chart 层启用这类规则 |
| 审计模式 | agent flag `--policy-audit-mode=true`（ConfigMap `policy-audit-mode`），或按端点启用 | 本来会丢弃的流量改为记录，verdict 为 `AUDIT`，而不真正丢弃 |
| `policyDenyResponse` | `none` / `icmp` | `icmp` 为实验功能，且仅对 egress 生效 |

注意：`enableDefaultDeny: false` **不适用于 L7**。没有同时允许所有其他流量的 L7 规则，仍会丢弃该端口上的其余流量。

集群级和按端点启用审计模式：

```bash
kubectl -n kube-system patch cm cilium-config --type merge \
  -p '{"data":{"policy-audit-mode":"true"}}'
kubectl -n kube-system rollout restart ds/cilium
# or for one endpoint (host endpoint included):
kubectl -n kube-system exec ds/cilium -- cilium-dbg endpoint config <ID> PolicyAuditMode=Enabled
hubble observe --verdict AUDIT
```

任何默认拒绝策略推广都应先使用审计模式；Hubble 中的 `AUDIT` verdict 可以显示强制执行时会丢弃哪些流量。来源：`Documentation/security/policy-creation.rst`。

### Entities

`host`、`remote-node`、`kube-apiserver`、`ingress`、`cluster`、`cluster-mesh`、`init`、`health`、`unmanaged`、`world`、`all`。`world` 等同于 `0.0.0.0/0`。在某些托管平台（上游提到 AKS、GKE）上，`kube-apiserver` ingress 可能无法工作。Agent flag `--allow-localhost=policy` 会禁用隐式的 host 到本地 Pod allow。

### 基于节点的选择和 CIDR

- `fromNodes`/`toNodes` 需要设置 `nodeSelectorLabels: true`（flag `--enable-node-selector-labels`）。节点随后会取得远端节点作用域身份。上游容量估算：使用 `policy-cidr-match-mode=nodes` 时，每 1000 个节点约需 1 MB。
- CIDR 规则（`fromCIDR`、`toCIDR`、带 `except` 的 `fromCIDRSet`、`toCIDRSet`）默认**不匹配 Pod 或节点**。`policyCIDRMatchMode`（`--policy-cidr-match-mode`，Beta）可启用 `pods` 和/或 `nodes`；`pods` 会增加身份数量。`values.yaml` 中的内联注释只提到 `nodes`，但文档允许两种值，因此应以文档为准。Kubernetes ClusterNetworkPolicy 一致性测试使用 `pods,nodes`。
- **CiliumCIDRGroup** 可以用一个命名对象保存许多 CIDR，约为每组使用一个身份，并在 Hubble flow 中附加组名。1.18–1.21 的 CRD 存储版本是 `cilium.io/v2`（仍提供 v2alpha1）；上游文档示例仍显示 `v2alpha1`，因此应使用 v2：

```yaml
apiVersion: cilium.io/v2
kind: CiliumCIDRGroup
metadata:
  name: vpn-example-1
  labels:
    role: vpn
spec:
  externalCIDRs:
  - 10.48.0.0/24
  - 10.16.0.0/24
---
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: from-vpn-example
  namespace: demo
spec:
  endpointSelector: {}
  ingress:
  - fromCIDRSet:
    - cidrGroupRef: vpn-example-1
```

可以通过 `cidrGroupRef: <name>` 或 `cidrGroupSelector.matchLabels` 引用。

### FQDN 策略和 DNS proxy

`toFQDNs` 可使用 `matchName` 或 `matchPattern`（`*` 匹配一个 label；`**.` 表示多级 label 前缀；`*.cilium.io` 不匹配 `cilium.io` 本身）。工作机制：每个 agent 中运行的 DNS proxy 会观察 DNS 响应，并将解析到的 IP 安装为 FQDN 派生的本地作用域身份。因此：

- 必须允许发往集群 DNS 的出口 DNS 规则（`toPorts.rules.dns`），确保 proxy 能看到响应。
- 同一条规则中的 `toFQDNs` 不能与其他 L3 selector 混用。
- Agent 重启时，DNS proxy 在该时间段内不可用。
- FQDN 是名称 allow-list，不是信誉检查。若 IPsec 与 L7 proxy 同时使用，需要设置 `--dnsproxy-enable-transparent-mode=true`。
- 每个 endpoint 每个 hostname 的 IP 数量上限存在文档/代码不一致。应读取当前版本 agent flag `tofqdns-endpoint-max-ip-per-hostname` 和 Helm `dnsProxy.endpointMaxIpPerHostname` 的生效值，不要依赖散文中的数字。
- `dnsProxy.preCache` / `--tofqdns-pre-cache` 在 1.20 弃用，计划于 1.21 移除。独立 DNS proxy 仍为 alpha。

### Deny 策略及优先级

`ingressDeny`/`egressDeny` 在 CNP、CCNP 和 Kubernetes NetworkPolicy 中均优先于所有 allow 规则。没有 L7 deny，也没有 `toFQDNs` deny。实际评估顺序：

| 顺序 | 规则类别 | 结果 |
|---|---|---|
| 1 | 命中 deny 规则 | 丢弃，不受任何 allow 规则影响 |
| 2 | 命中 allow 规则 | 转发 |
| 3 | 该方向上端点已被选中，但没有规则匹配 | 丢弃（默认拒绝） |
| 4 | 该方向上端点未被选中 | 转发（除非执行模式设为 `always`） |

对于 Kubernetes ClusterNetworkPolicy，层级顺序为：先 Admin tier，再 NetworkPolicy tier（Kubernetes NetworkPolicy、CNP、CCNP），最后 Baseline tier。通过 `k8sClusterNetworkPolicy.enabled=true` 启用（默认 false；flag `--enable-k8s-cluster-network-policy`），并从 network-policy-api 项目的 `release-0.2` 安装 CRD。该 API 在 Cilium 1.20 中为 alpha。

### 策略示例

**默认拒绝，但允许 DNS 和 FQDN egress**（namespace `demo`）。带 egress 规则的选择会让该方向切换到默认拒绝，因此必须显式允许 DNS，并添加 DNS 规则以确保 proxy 能看到 DNS 响应：

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: egress-fqdn
  namespace: demo
spec:
  endpointSelector:
    matchLabels:
      app: client
  egress:
  - toEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: kube-system
        k8s:k8s-app: kube-dns
    toPorts:
    - ports:
      - port: "53"
        protocol: ANY
      rules:
        dns:
        - matchPattern: "*"
  - toFQDNs:
    - matchName: "api.example.com"
    toPorts:
    - ports:
      - port: "443"
        protocol: TCP
```

在 EKS 上，DNS Pod 通常是标签为 `k8s-app: kube-dns` 的 `coredns`；如果你的发行版使用不同标签，应相应修改 selector。

**只允许集群内部流量，绝不允许来自 `world` 的流量**（这也会关闭“透明加密”一节所述的明文泄露窗口）：

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: cluster-only-ingress
  namespace: demo
spec:
  endpointSelector:
    matchLabels:
      app: server
  ingress:
  - fromEntities:
    - cluster
```

**拦截所有 DNS，但不启用默认拒绝**（直接采用上游简介页面的模式）：使用 `CiliumClusterwideNetworkPolicy` 并设置 `enableDefaultDeny: {egress: false, ingress: false}`，选择 `kube-system` 和 `kube-dns` 之外的所有 Pod，再允许到 `kube-dns` 且 `matchPattern: "*"` 的 DNS 流量。这样 DNS proxy 会进入路径（因此 Hubble 能看到 DNS 名称），但不会对其他流量开启默认拒绝。

**无论 allow 规则如何，都拒绝指定身份：**

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: deny-untrusted
  namespace: demo
spec:
  endpointSelector:
    matchLabels:
      app: server
  ingressDeny:
  - fromEndpoints:
    - matchLabels:
        trust: low
```

**Host policy 框架**（需要 `hostFirewall.enabled=true`；先对 host endpoint 启用审计模式，并优先放行 SSH/SSM、kubelet 和 API Server 路径）：

```yaml
apiVersion: cilium.io/v2
kind: CiliumClusterwideNetworkPolicy
metadata:
  name: host-ingress-from-cluster
spec:
  nodeSelector:
    matchLabels:
      node-role: worker
  ingress:
  - fromEntities:
    - cluster
    toPorts:
    - ports:
      - port: "10250"
        protocol: TCP
```

只要有 ingress 规则选择了 host endpoint，默认拒绝就会作用于该端点，因此这样的策略会丢弃匹配节点上的其余所有流量（包括 SSH）。通过 `cilium-dbg endpoint get -l reserved:host -o jsonpath='{[0].id}'` 获取 host endpoint ID，先对其设置 `PolicyAuditMode=Enabled`，然后运行 `hubble observe --verdict AUDIT` 观察再执行强制策略。

### 读取策略判定

```
cilium-dbg endpoint list                       # endpoint ID, identity, ingress/egress enforcement
cilium-dbg endpoint get <ID> -o json           # labels, identity, policy revision
cilium-dbg bpf policy get <ID>                 # the per-endpoint policy map (identity, port, proto, deny flag)
cilium-dbg policy selectors                    # which identities each selector currently matches
hubble observe --pod demo/server --verdict DROPPED -o json   # drop reason and (with correlation) the policy that matched
```

如果 selector 匹配到的身份少于预期，常见原因是与身份相关的标签不匹配（例如某个标签已从身份中排除），或者 namespace 范围的 CNP 在 selector 中隐式加入了 namespace。

### 1.20 对空策略的 CEL 拒绝

在 1.20 中，CNP 和 CCNP CRD 包含 CEL 规则 `has(self.spec) || has(self.specs)`，错误信息为 “spec or specs must be provided”。创建或更新时若两项都没有，准入阶段会拒绝该策略。现有空策略在被更新前不受影响。相关的较早变更：自 1.19 起 `FromRequires`/`ToRequires` 必须为空；Kafka/proxylib L7 策略则在 1.20 移除。

### Host policy

带有 `nodeSelector` 的 `CiliumClusterwideNetworkPolicy` 会成为 host policy。需要启用 `hostFirewall.enabled=true`（可选配置 `devices`）。该策略作用于 host namespace 和使用 host network 的 Pod，支持 L3/L4 以及 L7 DNS（Beta）。VRRP、IGMP、GRE、IPIP、IPV6、ESP 和 AH 需要 `--enable-extended-ip-protocols`。上游列出的已知问题：host policy 不适用于 IPsec，也不会应用到 host WireGuard interface；启用后，未知 L2 协议会被丢弃。L7 DNS host policy 可能影响 kubelet 拉取镜像和 agent 重启，因此应从审计模式开始。

### 1.21 预发布新增项 **[1.21 预发布版]**

CNP egress 的 `toPorts[].listener` 可将端口重定向到 CEC/CCEC Envoy listener（不能与同一端口上的 L7 规则组合；上游建议改用 Gateway API/GAMMA）。`--fixed-identity-mapping` 已弃用。

## 身份验证时间线：Mutual Authentication（已移除）

### 工作方式（1.18–1.20）

规则使用 `authentication: {mode: required}`。在数据路径中，带有该标志的 policy 命中会查询 BPF map `cilium_auth_map`（524288 个条目；键为本地身份、远端身份、远端节点和认证类型）。如果没有未过期条目，数据包会被丢弃（`DROP_POLICY_AUTH_REQUIRED`，-189），并向 agent 发送信号。`pkg/auth` manager 会通过带外 TLS 1.3 连接到**远端节点的 agent**，连接端口为 4250（`authentication.mutual.port`）；它从 SPIRE agent socket 获取 SPIFFE SVID（身份格式为 `spiffe://spiffe.cilium/identity/<numeric-id>`），验证对端证书，并将最早的到期时间写入 auth map。重传的数据包之后即可通过。重点：握手发生在**agent 之间**，不是逐连接建立，也不在数据路径中；除非另外启用了 WireGuard 或 IPsec，否则应用流量并未加密。已知限制：不支持 ClusterMesh；只测试过 SPIRE；不能与外部 mTLS 互操作。

### 时间线和迁移方式

| 版本 | 状态 | 操作 |
|---|---|---|
| 1.18、1.19 | Beta；1.19 中 `authentication.enabled` 默认为 false，带 `authentication` 的策略会静默转发而不认证（但会有验证警告） | 保留现状或迁移 |
| 1.20 | 已弃用（文档仍标为 Beta） | 规划迁移到 ztunnel（`encryption.type=ztunnel`），或迁移到网络加密加身份策略 |
| 1.21 | 已移除；agent `pkg/auth` 和 `mesh-auth-*` flags 已删除；policy 的 `authentication` 字段仍被接受但不使用 | **升级前**移除 `authentication.*` Helm 值和 SPIRE mutual-auth 配置 |

迁移指南：

1. 盘点所有使用 `authentication` 的策略：`kubectl get cnp,ccnp -A -o yaml | grep -n "authentication"`。
2. 明确实际需求。如果是“传输中加密”，请使用 WireGuard 或 IPsec（见下文[透明加密](#transparent-encryption)）；如果是“工作负载身份认证”，请使用 ztunnel mTLS 或 Service Mesh（例如 Istio）。
3. 不要假定 1.21 中该字段仍会强制认证：上游说明它仅为兼容而接受，实际不使用，因此依赖 `required` 的策略已不再要求认证。Agent 会如何在运行时报告这一情况，尚未验证。
4. 1.21 中 `authentication.mutual.spire.*` chart 值之所以仍保留，只是因为 ztunnel `ca.type=spire` 会复用 SPIRE 安装和 operator 的 SPIRE client；这些值已不再配置 mutual authentication。
5. 1.21 的 Hubble `dropEventEmitter.reasons` 不再列出 `auth_required`。

## ztunnel 工作负载 mTLS（自 1.19 起为 Beta）

### 架构

`encryption.type=ztunnel` 会让 Cilium 运行 Istio 的逐节点 L4 proxy（ztunnel 概念），并由 Cilium 自身作为控制平面。

```
 enrolled Pod A (netns)                         enrolled Pod B (netns)
  app --> iptables (in-pod) --> :15001           :15008 (HBONE in) --> ztunnel --> :15006 --> app
                                   |                  ^
                                   v                  |
                    node A ztunnel (DaemonSet, hostNetwork)  ==HBONE: HTTP/2 CONNECT over mTLS, TCP 15008==> node B ztunnel
                                   ^   xDS (workloads)   ^ CSR to Cilium CA
                                   |                     |
                     Cilium agent: xDS/ADS server, ZDS unix socket (/var/run/cilium/ztunnel.sock),
                                   built-in CA (IstioCertificateService), enrollment reconciler
```

- 每个节点运行一个 `ztunnel-cilium` DaemonSet（hostNetwork，容器名 `istio-proxy`）；1.20 和 1.21 使用镜像 `quay.io/cilium/ztunnel:v1.0.0`（1.19 使用 `docker.io/istio/ztunnel` 1.28.0-distroless）。
- Agent 通过 xDS 提供工作负载数据（来自 CEP），通过 ZDS unix socket 传递 Pod 网络命名空间文件描述符和 metadata，并为该节点上存在端点的 service account 签发工作负载 CSR。其 URI SAN 为 `spiffe://<trust domain>/ns/<ns>/sa/<sa>`。
- iptables 规则安装在**每个已加入 Pod 的 netns 内**：出站流量重定向到 15001，明文入站流量重定向到 15006；HBONE 入站 15008 不重定向（标记 0x539）。线上协议为 HBONE（基于 mTLS 的 HTTP/2 CONNECT），使用 **TCP 15008**。
- 与 Istio ambient 的差异：没有 istiod、waypoint 或 L7 功能；通过标签 `io.cilium/mtls-enabled=true` 加入，而不是 `istio.io/dataplane-mode=ambient`；CA 使用 Cilium 内部 CA 或 SPIRE。不要同时将同一批 Pod 接入两者。

### Secret、CA 类型和加入方式

安装前需生成 bootstrap 和 CA 密钥材料（上游仓库脚本为 `examples/kubernetes-ztunnel/generate-secrets.sh`）。`kube-system` 中的 Secret `cilium-ztunnel-secrets` 包含 `bootstrap-private.key`、`bootstrap-root.crt`、`ca-private.key`、`ca-root.crt`。上游说明了各自用途：bootstrap 密钥对用于保护 ztunnel 到 Cilium xDS 和证书服务器的连接；CA 密钥对是内存中临时工作负载证书的根 CA。

```yaml
# values-ztunnel.yaml
encryption:
  enabled: true
  type: ztunnel
  ztunnel:
    ca:
      type: internal   # default; "spire" is new in 1.20
```

| `encryption.ztunnel.ca.type` | 行为 |
|---|---|
| `internal`（默认） | Cilium 内置 CA 为工作负载证书签名；不需要 SPIRE reconciler |
| `spire`（1.20+） | 外部 SPIRE server 分配身份；operator 会为已加入 namespace 中的 service account 注册条目（parent 为 `/ztunnel`，路径为 `/ns/<ns>/sa/<sa>`） |

上游加密指南没有介绍 `spire` 模式；本次审查只验证了 operator 代码路径，没有端到端部署测试。请将其视为高级选项并单独测试。

加入或移除 namespace：

```bash
kubectl label namespace demo io.cilium/mtls-enabled=true
kubectl label namespace demo io.cilium/mtls-enabled-      # disenroll
```

namespace 中现有的所有 Pod（ztunnel Pod 除外）和之后新建的 Pod 都会加入。只能按 namespace 加入；host-network Pod 会跳过。

### 限制

| 限制 | 详情 |
|---|---|
| 两端都需加入 | 已加入到未加入的流量不受支持 |
| 仅支持 TCP | UDP 和其他协议不会重定向 |
| 策略交互 | 流量离开 Pod 前已加密，因此 L4 policy 看不到内层端口；只能按 HBONE 端口 15008 进行匹配 |
| 内核 | 需要 iptables 支持 |
| ClusterMesh | 不兼容；同时启用时会得到验证错误 |
| 加入范围 | 只能在 namespace 上设置标签，不能按 Pod 加入 |

在 EKS 上，对等节点位于同一 VPC，因此节点安全组必须允许节点间的 TCP 15008（安全组应引用自身，绝不能使用公共 CIDR）。

### 验证

```bash
kubectl -n kube-system describe cm cilium-config | grep enable-ztunnel -A2
kubectl get namespaces -l io.cilium/mtls-enabled=true
kubectl -n kube-system exec ds/cilium -- cilium-dbg statedb dump | jq '.["mtls-enrolled-namespaces"]'
# inside a Cilium Pod on the node hosting an enrolled Pod (install tcpdump first)
tcpdump -i eth0 port 15008      # use cilium_vxlan when tunnelling
```

## 透明加密 {#transparent-encryption}

通用规则：默认只加密跨节点的 Cilium 管理 Pod 流量；同节点流量始终不加密。节点尚未学习到目标端点时，出口流量可能以明文离开，因为判断使用相同的 ipcache/policy 机制。可通过 strict mode 或拒绝 `world` 的 egress policy 缓解。

### 加密数据包路径

```
Pod A (node 1) -> Pod B (node 2), WireGuard, tunnel mode

 Pod A veth --> bpf_lxc: policy ok, ipcache says dst is remote Cilium endpoint
            --> encryption marks the packet (dst is a managed remote endpoint)
            --> VXLAN/Geneve encapsulation (cilium_vxlan / cilium_geneve)
            --> routed into cilium_wg0 (WireGuard: UDP 51871, peer chosen by CiliumNode pubkey)
            --> NIC (outer IP: node 1 -> node 2)
 NIC (node 2) --> cilium_wg0 decrypt --> tunnel decapsulation --> bpf_lxc ingress policy --> Pod B

Native routing: the VXLAN/Geneve steps are absent; the inner packet is Pod A -> Pod B directly
inside WireGuard. IPsec uses the same decision point but the XFRM state for (src node, dst node)
applies ESP after encapsulation.
```

这是概念摘要，并非精确到 BPF 程序执行顺序的跟踪；程序布局见[第 8 部分](08-ebpf-datapath-internals.md)。由此可得两点。首先，“目标是否是受管理的远端端点”取决于 ipcache，因此尚未学习到的目标会被视为外部目标（存在泄露窗口）。其次，因为加密发生在策略判定和封装之后，物理 NIC 上的主机抓包只能看到密文，而在 `cilium_wg0` 上抓包会看到内层数据包。

### WireGuard（稳定）

机制：每个 agent 生成一对密钥，将公钥发布到 `CiliumNode` annotation `network.cilium.io/wg-pub-key`，并在设备 `cilium_wg0` 上为其他每个节点创建一个 WireGuard peer。每个节点使用 UDP 端口 **51871**。需要内核 WireGuard 支持（`CONFIG_WIREGUARD`、Linux 5.6 或更新版本，或安装外部模块）。Tunnel 模式下，Pod 流量会双重封装：先 VXLAN/Geneve，再 WireGuard，因此 MTU 很重要（见[第 9 部分](09-overlay-native-routing.md)）。

```yaml
encryption:
  enabled: true
  type: wireguard
  wireguard:
    persistentKeepalive: 0s
```

- 使用 CNI chaining（AWS VPC CNI）时，设置 `cni.enableRouteMTUForCNIChaining=true`，否则加密的 Pod 流量可能发生分片。
- ClusterMesh 要求所有集群都启用 WireGuard，并允许集群间 UDP 51871。
- 配置设备时出现丢包是一个已知问题（上游 gh-33159）。
- **节点间加密**（`encryption.nodeEncryption`，Beta）：可将加密扩展到主机流量。控制平面节点通过 `node-encryption-opt-out-labels` 退出。XDP 或非 Geneve DSR 的南北向路径存在缺口。**[1.21 预发布版]已弃用**，计划在 1.22 移除。

### Strict mode

| Helm 值 | 含义 |
|---|---|
| `encryption.strictMode.egress.enabled` | 丢弃节点发往 strict CIDR 的未加密流量 |
| `encryption.strictMode.egress.cidr` | 强制实施的 Pod CIDR（仅 IPv4；不保护 IPv6） |
| `encryption.strictMode.egress.allowRemoteNodeIdentities` | 使用隧道或节点 CIDR 与 Pod CIDR 重叠时需要 |
| `encryption.strictMode.ingress.enabled` | 丢弃未通过 WireGuard 到达的集群内部 ingress；**仅适用于 WireGuard** |

Ingress strict mode（1.19+）在 1.20.2 文档中支持 tunnel 和原生路由模式（1.19 升级说明曾称需要 tunnel）。限制：不支持 CNI chaining；不保护节点间流量；并且依赖 Cilium BPF 挂载到每个可能传输 Pod 流量的接口。

**1.20 中 flag 改名**：旧 flags `--enable-encryption-strict-mode`、`--encryption-strict-mode-cidr` 和 `--encryption-strict-mode-allow-remote-node-identities`（在 1.19 弃用）已**移除**。请改用 `--enable-encryption-strict-mode-egress`、`--encryption-strict-egress-cidr`、`--encryption-strict-egress-allow-remote-node-identities` 和 `--enable-encryption-strict-mode-ingress`。Helm 配置从 `encryption.strictMode.{enabled,cidr,allowRemoteNodeIdentities}` 改为 `encryption.strictMode.egress.*`。1.20 升级说明将 CIDR 值写为 `cidrs`，而 1.20.2 chart 的 `values.yaml` 使用 `cidr`；应以 chart 为准。

### IPsec（稳定）

机制：agent 使用 Secret 中的预共享密钥配置 Linux XFRM state 和 policy。任何 overlay 封装完成后，数据包再经 ESP 封装（自 1.18 起顺序固定；`encryptedOverlay` 选项已移除）。

```bash
kubectl create -n kube-system secret generic cilium-ipsec-keys \
  --from-literal=keys="3+ rfc4106(gcm(aes)) $(dd if=/dev/urandom count=20 bs=1 2>/dev/null | xxd -p -c 64) 128"
```

```yaml
encryption:
  enabled: true
  type: ipsec
  ipsec:
    secretName: cilium-ipsec-keys
    keyWatcher: true
    keyRotationDuration: 5m
```

- Secret 值格式：`key-id algorithm PSK-hex key-size`。密钥 ID 后的 `+` 会强制使用**每隧道派生密钥**；全局密钥在 1.16 已弃用（GHSA-pwqm-x5x6-5586）。
- 轮换：key ID 范围为 1..15，每次重新生成密钥都应递增，到 15 后回绕到 1（`encryption-ipsec.rst:206-218`；上游片段在 ID 达到 15 或更大时将 `KEYID` 重置为 0）。因此，简单地“用更大的 ID 更新”会在回绕时失败：ID 15 后，下一份 Secret 必须使用 ID 1。使用下一个 ID 更新 Secret；agents 会通过 `keyWatcher` 监控，并在 `keyRotationDuration` 加上最多其十分之一的 jitter 后移除旧密钥。升级期间不要轮换密钥。使用 ClusterMesh 时，每个集群都要轮换。
- 原生路由需要设置 `ipv4NativeRoutingCIDR`。不支持 CNI chaining。最多支持 65535 个节点；单条隧道的解密固定在一个 CPU 核心上。
- 使用 `cilium-dbg encrypt status`（查看正在使用的密钥及 XFRM 错误计数器）和 `tcpdump -l -n -i eth0 esp` 验证。节点安全组必须通过相互引用，允许节点间 ESP（IP 协议 50）；本次审查未验证 UDP 500/4500 的要求。
- **在 1.20 移除**：`encryption.ipsec.interface`（`--encrypt-interface`；自 1.18 起无操作）和 `encryption.ipsec.encryptedOverlay`。1.20.2 chart `values.yaml` 和 IPsec 指南仍提到 `interface`，这是上游文档不一致；不要设置。
- **Host policy 不适用于 IPsec**（上游 gh-41854）。

### MTU 开销

加密会增加 header 字节，从而降低可用 Pod MTU；tunnel 模式还会额外增加隧道 header。Cilium 会自动推导路由 MTU；使用 CNI chaining 时需设置 `cni.enableRouteMTUForCNIChaining`。第 9 部分依据 v1.20.2 的 `pkg/mtu/mtu.go` 计算字节数：WireGuard 为 95、默认 key size 下 IPsec 为 77、IPv4 underlay 上的 VXLAN 为 50；详见其 [MTU 计算部分](09-overlay-native-routing.md)。这些数值是计算结果，并非实测；应使用 `ping -M do -s <size>` 在 Pod 间确认，并检查 Cilium 设备上的 `ip link`。

### 选择方案

| 需求 | 选择 |
|---|---|
| 简单的 Pod 到 Pod 网络加密，不想管理密钥 | WireGuard |
| FIPS/合规要求，或内核没有 WireGuard 支持，且可以承担密钥轮换运维 | IPsec |
| 加密通道绑定工作负载身份、按 namespace 选择加入、只需 TCP | ztunnel |
| 跨集群（ClusterMesh） | WireGuard 或 IPsec（ztunnel 不兼容） |
| 感知 L7 的 mTLS、授权和 waypoint | Istio |

## Service Mesh TLS 选项

| 选项 | 提供能力 | 备注 |
|---|---|---|
| Istio sidecar | sidecar 间 mTLS、Istio 中的 L7 policy | Cilium 和 Istio 不应同时对 HTTP 流量执行 L7 policy；若这些 Pod 要使用 Cilium L7，应将 Istio `PeerAuthentication` 的 mTLS 设为 `DISABLE` |
| Istio ambient | ztunnel/HBONE 15008，可选 waypoint | Cilium 只能看到 15008 上的加密 L4 流量；要应用 Cilium L7，请移除 `istio.io/dataplane-mode` 或为 Pod 添加 annotation `ambient.istio.io/redirection: disabled` |
| Cilium ztunnel | 仅 L4 mTLS | 见上文 |
| Cilium 中的 Envoy TLS（CEC/Gateway API） | 在 Envoy 处终止/发起 TLS | 适用于 ingress/egress 可见性，不用于东西向 Service Mesh mTLS |

Istio 共存方式（上游 `network/servicemesh/istio.rst`）：建议设置 `kubeProxyReplacement=false`；如果启用了 replacement，则设置 `socketLB.hostNamespaceOnly=true` 和 `cni.exclusive=false`。overlay 上使用 sidecar 时，istiod 需要 `hostNetwork: true`。另见[第 5 部分](05-l2-l7-networking.md)。

**TLS 拦截**（CNP `toPorts` 中的 `terminatingTLS` / `originatingTLS`）：Envoy 使用内部 CA 的证书终止客户端 TLS（客户端必须信任该 CA），然后向目标重新发起 TLS。Secret 默认通过 SDS 传递（自 1.17 起）；Helm `tls.secretsNamespace.name` 默认值为 `cilium-secrets`，且 `tls.readSecretsOnlyFromSecretsNamespace` 为 true，因此 operator 会将被引用的 Secret 复制到该 namespace。这能让加密 egress 流量可用于 L7 policy，但不能替代 Mesh mTLS。

**Gateway API TLS**：HTTPS listener 可使用 Secret 终止 TLS；`BackendTLSPolicy`（gateway.networking.k8s.io/v1；`targetRefs` 指向 Service，`validation.caCertificateRefs` 指向 ConfigMap，另含 `hostname`）会加密 Envoy 到 backend 的流量。Cilium 1.20 要求 Gateway API v1.6.1 CRD；TLSRoute 为 v1，若之前使用过则需要 experimental channel，否则现有对象会消失。可通过 `cert-manager.io/issuer` annotation 集成 cert-manager。**暴露规则**：上游 Gateway/Ingress 示例会创建 `Service` 类型 `LoadBalancer`。在 EKS 上，应通过 CloudFront VPC origin 使用 internal scheme（`service.beta.kubernetes.io/aws-load-balancer-scheme: internal`）；不要面向互联网开放。本次审查没有针对 Cilium chart 验证这一点。另见[第 11 部分](11-bgp-lb-egress-edge.md)。

## Hubble 和 Tetragon

### Hubble 组件

Hubble server 在每个 agent 内运行（gRPC 监听 `hubble.listenAddress`，默认 `:4244`，并提供 unix socket `/var/run/cilium/hubble.sock`）。**Relay**（`hubble.relay.enabled`，默认 false；监听 4245）将所有节点汇总到一个 API 后端。**UI**（`hubble.ui.enabled`，默认 false）连接 Relay。Server 和 Relay 默认使用 mTLS（`hubble.tls.enabled: true`）。Relay 和 UI 应保持 ClusterIP（或放在 CloudFront VPC origin 后方的内部 LB），不要公开访问。

事件路径：数据路径事件 → 每个 agent 的 ring buffer（`hubble.eventBufferCapacity`，默认 4095；允许的值为 2^n-1，最大 65535）→ observers（CLI、Relay、exporter、metrics）。`hubble.networkPolicyCorrelation.enabled`（默认 true）会为 flow 附加允许或拒绝该流量的 policy。

### 指标

`hubble.metrics.enabled` 接受 handler 列表（例如 `dns`、`drop`、`tcp`、`flow`、`port-distribution`、`icmp`、`httpV2`、`flows-to-world`、`policy`；`sctp` 在 1.20 新增，v1.19.8 中没有该 handler）。端口为 9965。动态指标（`hubble.metrics.dynamic.enabled`、ConfigMap `cilium-dynamic-metrics-config`）可在不重启 agent 的情况下重新配置。L7 handler 只有对启用了 L7 visibility 的 Pod 才会产出数据。Kafka handler 在 1.20 移除。`hubble.metrics.portName` 是 **[1.21 预发布版]新增项**。

### Exporter

- 静态 exporter：`hubble.export.static.enabled`、`filePath`（默认 `/var/run/cilium/hubble/events.log`，也允许 `stdout`）、`fileMaxSizeMb`、`fileMaxBackups`、`fileCompress`、`allowList`、`denyList`、`fieldMask`；1.19 起支持 `fieldAggregate` 和 `aggregationInterval`。其生命周期与 agent 绑定。
- 动态 exporter：`hubble.export.dynamic.enabled`，以及 `config.content[]` 条目（`name`、`filePath`、`fieldMask`、`includeFilters`、`excludeFilters`、`end` 和轮转字段），存储在 ConfigMap `cilium-flowlog-config` 中，可在不重启的情况下应用（大约一分钟内生效）。

### 脱敏（L7）

`hubble.redact.enabled`（默认 false）、`http.urlQuery`（默认 false）、`http.userInfo`（默认 true），以及 `http.headers.allow` **或** `deny`（不能同时配置）。示例：拒绝记录 `Authorization` 和 `Proxy-Authorization`。Kafka 支持及 `apiKey` 脱敏均在 1.20 移除。

```yaml
hubble:
  redact:
    enabled: true
    http:
      urlQuery: true
      userInfo: true
      headers:
        deny:
        - Authorization
        - Proxy-Authorization
```

### 丢弃事件

`hubble.dropEventEmitter`（alpha）会针对被丢弃的流量生成 Kubernetes Event；`interval` 为 2m；1.20.2 的 `reasons` 默认值为 `auth_required` 和 `policy_denied`；1.21 不再列出 `auth_required`。

### Tetragon（概览）

Tetragon 是独立项目（不属于 Cilium repository）：基于 eBPF 的运行时安全观测与强制执行工具，通过 `TracingPolicy` 资源配置进程执行、文件和网络活动。Cilium 威胁模型文档建议使用它来提供运行时可见性。本次审查**未核实**其 CRD 版本和强制执行操作；此处仅作概览，详细信息请参阅 Tetragon 项目文档。

## 证书管理

| 组件 | 证书来源 | 轮换方式 |
|---|---|---|
| Hubble server、Relay、metrics | `hubble.tls.auto.method`：`helm`（默认）、`cronJob`、`certmanager` | `helm`：只有重新渲染 Helm 时才重新生成，不自动续订；`cronJob`：由 certgen CronJob 生成，计划为 `0 0 1 */4 *`；`certmanager`：由 cert-manager 续订，并设置 `certManagerIssuerRef` |
| ClusterMesh API server | 同样三种方法，使用 `clustermesh.apiserver.tls.auto` 下的配置 | 见[第 13 部分](13-clustermesh-install-upgrade.md) |
| ztunnel 工作负载 | 内部 CA 或 SPIRE | 有效期较短，保存在内存中 |
| IPsec / WireGuard | PSK Secret / 自动生成密钥对 | IPsec 手动轮换；WireGuard 自动轮换 |

需要了解的值（1.20.2 `values.yaml`）：`hubble.tls.auto.certValidityDuration` 默认为 **365** 天，共享自动生成 CA 的 `tls.ca.certValidityDuration` 默认为 **1095** 天。上游其他说明文字称叶证书默认有效期为三年；实际生效的是 chart 值。Server、Relay 证书和 CA 都支持热重载。

1.20 的变化：

- ClusterMesh 自动证书默认有效期为 1 年（`clustermesh.apiserver.tls.auto.certValidityDuration: 365`；1.19 中为 1095）。若使用 `helm` 方法，只会在渲染 chart 时续订，因此至少每年升级一次；`cronJob` 和 `certmanager` 会自动续订（ClusterMesh cronJob 每四个月重新生成证书）。
- `certgen.enforceCAValidityThroughoutLeavesDuration` 默认 true：如果 CA 会早于叶证书到期，certgen 会失败。设为 false 可关闭此检查。
- 移除了通过 Helm 值手动提供证书的支持：应预先创建 Secret，并设置 `tls.auto.enabled=false`。
- `clustermesh.apiserver.tls.server.{extraDnsNames,extraIpAddresses}` 已迁移到 `...tls.auto.server.*`。

用户提供的 Hubble 证书需要以下 SAN：`*.<cluster>.hubble-grpc.cilium.io`（server）、`*.hubble-relay.cilium.io`（Relay）、`*.hubble-ui.cilium.io`、`<cluster>.hubble-metrics.cilium.io`；Secret 中包含 `tls.crt`、`tls.key`、`ca.crt`。**[1.21 预发布版]每** Pod 证书支持项：`hubble.tls.disableDefaultVolumes`、`hubble.relay.tls.disableDefaultVolumes`、`hubble.ui.tls.disableDefaultVolumes` 和 `extraInitContainers`，可用于 Vault、cert-manager CSI 或 SPIFFE 来源；`clustermesh.apiserver.tls.authMode` 的默认值改为 `cluster`。

```yaml
hubble:
  tls:
    auto:
      enabled: true
      method: certmanager
      certManagerIssuerRef:
        group: cert-manager.io
        kind: ClusterIssuer
        name: hubble-issuer
```

## 实验

本次审查没有在运行中的集群执行下列实验（见“验证限制”）。请使用可丢弃的测试集群。所有安全组说明均假定节点间规则引用节点安全组本身；绝不要向 `0.0.0.0/0` 或 `::/0` 开放任何端口。

### 实验 1：身份、ipcache 和标签排除

前置条件：Cilium 1.20.2 集群、kubectl，以及通过 agent Pod 访问 `cilium-dbg`。

1. 创建 namespace，并创建两个 Deployment：`web`（`app=web`）和 `db`（`app=db`），各有 2 个副本。
2. 执行 `kubectl get ciliumidentities`：应看到 `web` 标签集合对应一个身份、`db` 对应另一个身份，各自身份由副本共享。
3. 执行 `kubectl -n kube-system exec ds/cilium -- cilium-dbg identity list`，记下 `web` 和 `db` 的 ID。
4. 选择一个 `web` Pod IP，运行 `cilium-dbg bpf ipcache list | grep <podIP>`：该条目的身份应与 `web` 身份相同。
5. 运行 `kubectl label pod <pod> release=r2 --overwrite` 给一个 `web` Pod 改标签。预期：该 Pod 会出现一个新身份，且 `kubectl get ciliumidentities` 的结果增加一项，说明标签变化会带来身份变化。
6. 清理：删除 namespace。如果曾通过 Helm 更改与身份相关的标签，使用 `helm upgrade` 回滚（只有集群已运行此 chart 版本 1.20.2 时才可使用 `--reuse-values`；否则应显式传入保存的 values），然后重启 agents（只有 agent 重启后身份才会变化）。

### 实验 2：WireGuard 和严格 ingress

前置条件：节点支持内核 WireGuard；节点安全组允许来自自身安全组的 UDP 51871。

1. 执行 `helm upgrade cilium cilium/cilium --version 1.20.2 -n kube-system --reuse-values --set encryption.enabled=true --set encryption.type=wireguard`；如果 rollout 没有重启 agents，则手动重启。只有集群已使用 1.20.2 chart 时才可用 `--reuse-values`（不能同时改变 chart 版本；参见上游 `upgrade.rst:206-221`）。如果当前是其他版本，应先保存 `helm get values cilium -n kube-system -o yaml`，检查改名的值，再用 `-f` 传入。
2. 执行 `kubectl -n kube-system exec ds/cilium -- cilium-dbg status | grep Encryption`。预期会有一行 `Wireguard [cilium_wg0 (...Port: 51871, Peers: N)]`，其中 N 等于节点数减一。
3. 在不同节点上的 Pod 之间产生流量，并在 agent Pod 中运行 `tcpdump -n -i cilium_wg0`。预期：`cilium_wg0` 上能看到明文 Pod 到 Pod 流量；物理 interface 上 UDP 51871 的抓包则只显示加密数据包。
4. 启用 strict mode：设置 `--set encryption.strictMode.egress.enabled=true --set encryption.strictMode.egress.cidr=<podCIDR> --set encryption.strictMode.ingress.enabled=true`。若使用隧道，还应设置 `allowRemoteNodeIdentities=true`。
5. 预期：常规 Pod 流量继续工作；绕过 WireGuard 的未加密 Pod 流量会被丢弃（要注入此类流量需要主机级工具，可选）。
6. 回滚：先将 strict 配置设为 false，再设置 `encryption.enabled=false` 并重启 agents。设备重新配置期间预计会短暂丢包（上游已知问题）。

### 实验 3：加入 ztunnel

前置条件：未启用 ClusterMesh，节点支持 iptables，节点安全组允许节点间 TCP 15008。

1. 在相同版本的 Cilium 源代码树中运行 `bash examples/kubernetes-ztunnel/generate-secrets.sh`（会在 `kube-system` 中创建 `cilium-ztunnel-secrets`）。
2. 使用 `encryption.enabled=true` 和 `encryption.type=ztunnel` 执行升级。检查 `kubectl -n kube-system get ds ztunnel-cilium` 和 `describe cm cilium-config | grep enable-ztunnel -A2`。
3. 创建 `mtls-on` 和 `mtls-off` namespace，每个 namespace 中部署一个 HTTP server 和 curl client。只给 `mtls-on` 添加标签：`kubectl label ns mtls-on io.cilium/mtls-enabled=true`。现有 Pod 会自动加入，无需重启。
4. 执行 `cilium-dbg statedb dump | jq '.["mtls-enrolled-namespaces"]'`，应列出 `mtls-on`。
5. 从 `mtls-on` 客户端访问另一节点上 `mtls-on` 的 server：在节点上运行 `tcpdump -i eth0 port 15008`，应看到 HBONE 数据包。
6. 从 `mtls-on` 客户端访问 `mtls-off` 的 server：预期失败，因为已加入和未加入之间的混合流量不受支持。
7. 清理：运行 `kubectl label ns mtls-on io.cilium/mtls-enabled-`，删除 namespace，然后设置 `encryption.enabled=false` 并删除 `cilium-ztunnel-secrets`。

### 实验 4：Policy 审计、CIDR group 和 deny

1. 创建 namespace `pol`，其中包含 `client` 和 `server` Pod（HTTP 端口 8080）。
2. 为 server endpoint 启用审计模式：`cilium-dbg endpoint config <ID> PolicyAuditMode=Enabled`。
3. 应用 CNP，只允许来自 `app=client`、访问 8080 端口的 ingress 到 `server`。从第三个 Pod curl server，并运行 `hubble observe --verdict AUDIT -n pol`：预期第三个 Pod 的 verdict 为 `AUDIT`，但请求仍成功。
4. 设置 `PolicyAuditMode=Disabled` 关闭审计模式；重试后请求应被丢弃（`hubble observe --verdict DROPPED`）。
5. 添加上文的 `CiliumCIDRGroup` 清单和使用 `cidrGroupRef` 的 egress `toCIDRSet` 规则；验证 `cilium-dbg identity list` 显示 CIDR 派生身份，且 flow 会标注该 group。
6. 为 `app=client` 添加 `ingressDeny` 规则；即使已有 allow 规则，客户端流量也应被丢弃（deny 优先）。
7. 清理：删除 namespace 和 CCG。

### 实验 5：Hubble 导出、脱敏和 cert-manager

前置条件：已安装 cert-manager 和 ClusterIssuer。

1. 启用 Relay 和动态导出：`hubble.relay.enabled=true`、`hubble.export.dynamic.enabled=true`、`hubble.redact.enabled=true`、`hubble.redact.http.urlQuery=true`，并设置 `hubble.tls.auto.method=certmanager` 和 `certManagerIssuerRef`。
2. 编辑 ConfigMap `cilium-flowlog-config`，添加一个带 `includeFilters` 条目的 exporter，例如 `source_pod: ["kube-system/"]`。预期 agent Pod 内的 Hubble 导出目录中会出现新文件，无需重启 agent（可能需要约一分钟）。
3. 生成带查询字符串和 `Authorization` header 的 L7 可见 HTTP 流量（需要为 Pod 配置 L7 policy）。预期 `hubble observe -o json` 显示查询和 header 值已脱敏。
4. 执行 `kubectl get certificate -n kube-system`：Hubble 证书应由 ClusterIssuer 签发。
5. 回滚：移除 exporter 条目，设置 `hubble.redact.enabled=false`，并恢复原证书方式。

## 版本差异

| 主题 | 1.18 | 1.19 | 1.20 | 1.21 预发布版 |
|---|---|---|---|---|
| Mutual Authentication | Beta | Beta；默认禁用（`authentication.enabled=false`） | 已弃用 | 已移除；policy 的 `authentication` 字段不再使用 |
| ztunnel | - | 新增（Beta）；启动校验已拒绝 ClusterMesh（`pkg/ztunnel/cell.go:46`） | `ca.type` 为 internal/spire；镜像 `quay.io/cilium/ztunnel` | Beta；`ca.type=spire` 复用 SPIRE chart |
| Strict mode flags | 只有 `strictMode.{enabled,cidr,allowRemoteNodeIdentities}` | 新增 `strictMode.egress.*` 和 `strictMode.ingress.*`；旧 flags 弃用 | 移除旧 flags（使用 `...-egress-*` 名称） | 无变化 |
| IPsec | `encryptedOverlay` 无操作 | - | 移除 `encryptedOverlay` 和 `ipsec.interface` | - |
| WireGuard `nodeEncryption` | 未核查 | 未核查 | Beta | 已弃用，计划于 1.22 移除 |
| Policy | Kafka/proxylib 弃用 | `FromRequires`/`ToRequires` 必须为空 | 移除 Kafka/proxylib；CEL 拒绝空 CNP/CCNP；新增 ClusterNetworkPolicy | `toPorts[].listener` 重定向 |
| Hubble | - | 新增导出 `fieldAggregate`/`aggregationInterval` | 移除 Kafka metrics 和脱敏；证书默认 1 年（ClusterMesh）；增加 certgen CA 有效期检查 | 每 Pod 证书、`portName`、UI `httpRoute` |
| Identity | Double Write 有文档 | 有文档 | 有文档 | 弃用 `preflight migrate-identity` |

## 故障排查

| 症状 | 可能原因 | 检查方法 |
|---|---|---|
| 新 Pod 的流量短暂被 policy 丢弃 | Pod 仍处于 `reserved:init`，或 ipcache 尚未传播 | `cilium-dbg endpoint list`、`cilium-dbg bpf ipcache get <ip>` |
| `fromEntities: cluster` 对 NodePort 流量的匹配结果出乎预期 | 根据路由模式，源身份可能为 `world` 或 `remote-node` | 查看上文 entities 说明；通过 `hubble observe` 检查身份 |
| 身份数量不断增长 | 易变标签被视为身份相关标签 | `kubectl get ciliumidentities \| wc -l`；排除该标签 |
| `kubectl apply` CNP 时被拒绝，并提示 “spec or specs must be provided” | 1.20 CEL 规则 | 提供 `spec` 或 `specs` |
| WireGuard peer 数不正确，或没有 `cilium_wg0` | 缺少内核模块，或节点间 UDP 51871 被阻止 | `cilium-dbg status \| grep Encryption`、检查节点安全组 |
| 使用加密时大数据包卡住 | 加密和隧道共同造成 MTU 过高 | 使用 `ping -M do` 测试；检查 CNI chaining flag |
| IPsec 错误计数上升 | 密钥不匹配或 XFRM state 过期 | `cilium-dbg encrypt status`；轮换密钥会清除过期 state |
| IPsec 环境中的 host policy 不生效 | 该组合不受支持 | 使用 WireGuard，或移除 host policy |
| namespace 已加入，但没有 HBONE 数据包 | 对端未同时加入、Pod 使用 host-network，或流量为 UDP | 检查 `statedb dump`、Pod 类型和协议 |
| 启用 ztunnel 后 agent 无法启动 | 同时启用了 ClusterMesh | 关闭其中一个功能 |
| 一年后 Hubble Relay 证书报错 | `helm` 方法不会自动续订 | 改用 `cronJob` 或 `certmanager`，或每年更新 Helm |
| 1.21 后带 `authentication` 的策略不再认证 | 功能已移除 | 按上文说明迁移 |

## 验证限制与来源

本次审查没有在实时集群中执行这些实验；核对依据为下方所列标签对应的上游源码和文档。Tetragon、ztunnel `ca.type=spire` 的端到端流程、IPsec ESP/UDP 防火墙要求，以及遗留策略 `authentication` 字段的运行时行为均未验证，文中已作标注。标记为 **[1.21 预发布版]** 的内容取自 v1.21.0-pre.3，正式发布前可能发生变化。对于上游内容中的不一致，本章没有照抄：每个主机名的 FQDN IP 数量限制（文档与代码默认值不一致）、Hubble 证书默认有效期的说明与 `values.yaml` 不一致、`CiliumCIDRGroup` 文档写为 `v2alpha1` 而存储版本为 `v2`，以及 `policyCIDRMatchMode` 的 values 注释。

- [1.20 升级说明](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/operations/upgrade-current.inc)、[Mutual Authentication（1.20）](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/servicemesh/mutual-authentication/mutual-authentication.rst)、[Helm values](https://github.com/cilium/cilium/blob/v1.20.2/install/kubernetes/cilium/values.yaml)、[策略概览](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/kubernetes/policy.rst)
- [透明加密](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/security/network/encryption.rst)、[WireGuard](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/security/network/encryption-wireguard.rst)、[IPsec](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/security/network/encryption-ipsec.rst)、[CNP CEL 规则](https://github.com/cilium/cilium/blob/v1.20.2/pkg/k8s/apis/cilium.io/v2/cnp_types.go)
- [1.21 升级说明（预发布版）](https://github.com/cilium/cilium/blob/v1.21.0-pre.3/Documentation/operations/upgrade-next.inc)、[ztunnel 指南（预发布版）](https://github.com/cilium/cilium/blob/v1.21.0-pre.3/Documentation/security/network/encryption-ztunnel.rst)、[身份分配与 Double Write](https://github.com/cilium/cilium/blob/v1.21.0-pre.3/Documentation/operations/upgrade.rst)、[数字身份](https://github.com/cilium/cilium/blob/v1.21.0-pre.3/pkg/identity/numericidentity.go)、[策略三层规则](https://github.com/cilium/cilium/blob/v1.21.0-pre.3/Documentation/security/policy/layer3.rst)、[Hubble TLS](https://github.com/cilium/cilium/blob/v1.21.0-pre.3/Documentation/observability/hubble/configuration/tls.rst)、[Hubble 导出](https://github.com/cilium/cilium/blob/v1.21.0-pre.3/Documentation/observability/hubble/configuration/export.rst)

## 测验

[检查你对 mTLS、加密和身份的理解](../../quizzes/networking/cilium/12-mtls-encryption-identity-quiz.md)。

[返回主页](README.md)
