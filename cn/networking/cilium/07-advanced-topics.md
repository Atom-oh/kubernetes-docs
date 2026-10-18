# 高级主题与真实案例

> **审查基线**：Cilium 1.20.3、Cilium CLI 0.20.1 和 Hubble CLI 1.20.2。
> **最后审阅**：2026 年 10 月 16 日。Cilium 1.20 的 Kubernetes 兼容范围为 1.33–1.36；以下历史测量数据保留其原始环境。

## 实验环境设置

请使用[安装先决条件](README.md)，并准备一个至少有两个可调度 Linux 节点的一次性测试集群。将操作系统、内核、Cilium 设置、拓扑、MTU、策略、加密和测试工作负载记录在结果中。使用处于其支持的 API 服务器版本偏差范围内的 kubectl。以下命令需要 Helm、jq 和 Cilium/Hubble CLI；`kubectl top` 还需要 metrics API。

### 性能测试环境设置

更改之前，先记录现有部署：

```bash
cilium version
cilium status --verbose
kubectl version
kubectl get nodes -o wide
kubectl -n kube-system get pods -l k8s-app=cilium -o wide
helm get values cilium --namespace kube-system -o yaml > cilium-current-values.yaml
```

当前 CLI 可以创建与自身匹配的测试工作负载。仅当生成网络负载和创建测试资源均可接受时，才运行此命令：

```bash
cilium connectivity perf --test-namespace cilium-advanced-perf \
  --namespace-labels docs-audit-lab=cilium-advanced-07 \
  --duration 10s --samples 2 --crr --udp \
  --host-net=false --pod-net=true --same-node=true --other-node=true \
  --report-dir ./cilium-advanced-perf-results
```

默认的单并发运行使用 **`cilium-advanced-perf-1`**，尽管参数中没有这个后缀。测试前请确认该命名空间未被使用。`--duration` 适用于每个场景/样本，而非整个运行过程；调度、准备以及多个测试用例的组合都会增加耗时。该命令会主动生成工作负载进行测试，并非只读诊断。

比较同节点和跨节点结果、TCP 请求/响应和 UDP，以及实际的 CPU/内存/丢包情况。每次只重复测试一个计划中的更改。测试成功并不能证明应用 SLO、生产环境容量上限或所有策略路径均满足要求。本次审查仅验证了这些命令约定，没有运行测试或配置集群。

## 性能调优与故障排查

### 性能调优架构

![Cilium 性能排查的四个方面：内核行为、eBPF 映射、资源分配和所选网络路径。](../../.gitbook/assets/en-networking-cilium-07-advanced-topics-0.png)

[查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-cilium-07-advanced-topics-0.html)

该图归纳了排查方向；它并不建议提高所有设置或禁用安全控制。

### 性能调优领域

| 领域 | 测量内容及设置控制的内容 |
| --- | --- |
| Socket backlog | `net.core.somaxconn` 限制 socket 监听 backlog；`net.ipv4.tcp_max_syn_backlog` 涉及每个监听器待处理的 SYN_RECV 请求。检查服务器的 accept 行为和相关网络命名空间。 |
| 邻居表项 | `net.ipv4.neigh.default.gc_thresh1`、`gc_thresh2` 和 `gc_thresh3` 是不同的垃圾回收阈值。不存在一个统一的 `gc_thresh` 设置。 |
| 连接跟踪 | Netfilter 的 `nf_conntrack_max` 与 Cilium 的 BPF CT 映射是两种独立机制。提高前者不会调整后者的大小。 |
| BPF 映射 | 检查映射压力、插入失败、变更频率和内存占用。CT、NAT、LB 和每端点策略映射的作用范围和容量规则各不相同。 |
| CPU 和内存 | 分别测量 agent、operator、Envoy 和 Hubble。requests 会影响调度；CPU limits 可能导致限流，memory limits 可能导致 OOM 终止。提高所有 limits 并不能替代诊断。 |
| 网络路径 | 确定原生/隧道式路由、MTU、伪装、加密和 Service 转发方式。XDP 加速适用于受支持的路径和驱动程序；它不是 kube-proxy replacement 的必要条件。 |

比较性能时，应保持安全和路由要求不变。通过移除必需的加密或策略获得的更快结果，并非等价配置。

### 映射容量设置

测得压力后，仅将以下内容保存为**候选更改**。请将其合并到完整且有版本管理的发行版 values 中；不要用一小段配置替换整个 Cilium ConfigMap。

```yaml
# map-sizing-values.yaml
bpf:
  mapDynamicSizeRatio: 0.005
```

`0.005` 是动态容量计算所用的标称值，即节点内存的 **0.5%**，不是 5%，也不是所有 Cilium 内存的硬性上限。例如，32 GiB × 0.005 在应用映射限制、舍入和其他分配之前为 163.84 MiB。受影响的大型映射包括 CT、NAT、邻居和 socket reverse-NAT 映射；其他映射和用户空间内存另行计算。

显式设置的 `bpf.ctTcpMax`、`bpf.ctAnyMax` 或 `bpf.natMax` 值会覆盖这些映射的动态容量设置。NAT 容量应与 CT 容量相匹配，并验证启动时最终解析出的容量。扩大映射会占用更多内存；替换映射可能会中断现有连接。

分布式 LRU（`bpf.distributedLRU.enabled`）使用每 CPU 池来减少争用，同时存在内存/驱逐方面的权衡。它要求启用动态容量设置，并且启用时会重新创建映射。官方高性能配置文件并不是适用于所有场景的在线切换项：应在准备好的新节点上引入这类数据路径变更，或使用文档规定的迁移流程。

旧的 `proxy-max-memory-percentage`、`proxy-max-threads`、`enable-xdp`、`tunnel: disabled` 和 `kube-proxy-replacement: strict` 示例并非当前配置方案。请使用受支持的 chart 设置，例如 `envoy.resources`、`routingMode`、布尔值 `kubeProxyReplacement` 和 `loadBalancer.acceleration`，并满足其先决条件。

### Hubble 开销与事件丢失

较大的事件队列可以吸收突发流量，但会占用内存，也无法解决持续的处理能力不足或降低 CPU 消耗：

```yaml
# hubble-queue-values.yaml
hubble:
  eventQueueSize: 32768
```

如果重复的 trace 事件占用了大部分处理能力，可单独评估是否延长聚合间隔：

```yaml
# hubble-aggregation-values.yaml
bpf:
  monitorAggregation: medium
  monitorInterval: 10s
```

实际的 chart 字段是 **`bpf.monitorInterval`**，不是 `bpf.events.monitorInterval`。部署前请检查渲染后的 `monitor-aggregation-interval`。提高聚合级别、限制事件速率和禁用事件类别都会减少可供监控、Hubble metrics 和导出的观测数据。Hubble 事件丢失本身并不表示应用数据包被丢弃；请同时检查可观测性数据丢失和数据路径丢包。

### 高级数据路径先决条件

| 功能 | 需要检查的先决条件和限制 |
| --- | --- |
| netkit | 在此基线中为 Beta；需要 Linux 6.8+ 和 BPF 主机路由。现有使用 veth 的 Pod 无法仅通过重启 agent 就切换设备类型。 |
| BIG TCP | 依赖特定的内核/NIC 要求；组合调优配置文件要求 Linux 6.8+ 和受支持的 NIC。它不是通用的 MTU 增大方案。 |
| BPF 主机路由 | 需要兼容的 kube-proxy replacement 和 BPF 伪装。它会绕过主机 netfilter hooks；请检查依赖这些 hooks 的 Istio 和其他集成。 |
| XDP Service 加速 | 需要支持原生 XDP 的设备，以及受支持的外部 Service 转发路径。请遵循驱动程序/平台指南，并验证运行状态。 |
| Bandwidth Manager | 每个 Pod 的出站流量使用 EDT；入站流量使用 eBPF token bucket。带宽注解中的 `10M` 表示 10 Mbit/s，而非 10 MB/s。 |
| Pod 的 BBR | 需要 Bandwidth Manager、Linux 5.18+ 和 BPF 主机路由；新创建的 Pod 会采用此设置。仅主机使用的 BBR 是另一项独立选项。 |

在 egress L7 Cilium 策略和 kind 等嵌套网络命名空间中，带宽控制有文档列明的限制。这些情况不同于普通 Cilium 安装要求。不要将某个调优配置文件当作所有 Service Mesh、云平台或内核组合均可正常工作的证据。

### 有针对性的故障排查命令

对于集群操作，请使用独立的 `cilium` CLI；对于本地端点、策略和映射，请在相关 agent 中使用 **`cilium-dbg`**。选择正在调查的节点，而不是随意查询第一个 agent：

```bash
set -euo pipefail
: "${NODE_NAME:?Set NODE_NAME to the node being investigated}"
CILIUM_POD=$(kubectl -n kube-system get pods -l k8s-app=cilium \
  --field-selector "spec.nodeName=$NODE_NAME,status.phase=Running" -o json |
  jq -er 'if (.items | length) == 1
then .items[0].metadata.name
else error("expected exactly one running Cilium Pod on the selected node")
end')
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg status --verbose
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg endpoint list
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg policy get
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg policy selectors
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg map list
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg bpf metrics list
kubectl -n kube-system logs "$CILIUM_POD" -c cilium-agent --since=10m --tail=200
```

端点 ID 仅在对应 agent 内有效。请使用其端点列表中的 ID：

```bash
: "${CILIUM_POD:?Select the owning Cilium Pod first}"
: "${ENDPOINT_ID:?Read the endpoint ID from the selected agent endpoint list}"
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- \
  cilium-dbg endpoint get "$ENDPOINT_ID"
# Stream local BPF drop events; stop with Ctrl-C.
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- \
  cilium-dbg monitor --type drop
```

`cilium-dbg map list` 会列出 agent 的映射管理器已知的打开映射；它并非所有内核 BPF 映射的清单。`cilium-dbg monitor` 显示已发出的 BPF 事件和可选的捕获轨迹，并非对每个数据包进行无损 tcpdump。导出大型 CT 映射可能开销很高；运行 `cilium-dbg bpf ct list global` 前，请先检查 metrics 和受影响的节点。

对于 Hubble，请先按照[安全与可见性](06-security-visibility.md)中的说明建立本地 Relay 连接：

```bash
hubble status
hubble observe --protocol tcp --verdict DROPPED --since 1h
hubble observe --protocol dns --from-label k8s:app=frontend --last 100
hubble observe --http-status '5+' --from-namespace production --last 100
```

`--type` 用于选择事件类型，而不是 DNS 记录类型 A。若要区分查询类型，请使用 DNS flow 字段。HTTP 状态筛选器使用 `5+`，而不是 `5xx`。`--since 1h` 的范围受保留历史记录和事件可用性的限制；它无法恢复已被覆盖的一小时前事件。

### 常见故障排查场景

| 症状 | 需要收集的证据 | 后续决策 |
| --- | --- | --- |
| CT/NAT 压力 | 映射压力、插入/丢弃原因、连接变更频率、实际配置的容量 | 扩容之前先调查连接变化、超时和内存余量。 |
| OOM 或 CPU 饱和 | 容器终止原因、内存/CPU 历史数据、限流情况、proxy 和 Hubble 负载 | 找出相关组件，并调整其资源预算或工作负载。 |
| 策略结果异常 | 正确的命名空间/标签、端点策略修订、proxy 错误和 Hubble 判定 | 检查方向、累加式 allow 规则和 deny 优先级；普通 allow 规则并非按优先级排序的防火墙列表。 |
| 跨节点故障 | DNS、节点/Pod 路由、MTU、隧道/加密端口和平台防火墙 | 验证正向和返回路径；仅有 BGP 会话并不能证明数据路径可达。 |
| 升级回归 | 升级前后 values、版本说明、所有组件版本、proxy 重新连接情况 | 使用已准备好的受支持回滚路径，并调查功能兼容性。 |

## 大规模部署策略

容量规划必须纳入节点/Pod 密度、Service 和后端、身份、策略展开、API watch 流量、IPAM 分配和 flow 数量。仅凭策略对象的数量无法确定其对每个端点映射的开销。

### 大规模部署架构

```text
Management / GitOps / shared monitoring
          | config and collected telemetry
          +-----------------------+
          v                       v
  Workload cluster A       Workload cluster B
  - Cilium Operator        - Cilium Operator
  - agent on each node     - agent on each node
  - local Hubble servers   - local Hubble servers
  - Relay/export setup     - Relay/export setup
          |                       |
          +--- optional ClusterMesh metadata/data paths
```

集中式管理集群不能替代每个受管理集群中的 operator。应分别为每个集群的 operator 和 agents 规划容量；chart 的 operator 副本数和反亲和性需要有足够符合条件的节点。通过已配置的收集器汇总 metrics/logs。ClusterMesh 需要独立的寻址、身份、信任和可达性设计；它不会自动复制所有策略资源。

`ciliumEndpointSlice.enabled` 是可选启用的 Cilium 功能，与 Kubernetes EndpointSlice 不同。它不是旧的 `enable-endpoint-slice` ConfigMap 标志。启用前请评估版本和功能兼容性；Egress Gateway 当前无法与 CiliumEndpointSlice 或 ClusterMesh 同时使用。

Egress Gateway 会将选定流量 **SNAT** 到可预测的网关地址；它不会保留原始 Pod 源地址。网关接口/IP 和路由必须预先配置，其中包括 AWS 上的平台特定要求。它需要 BPF 伪装、kube-proxy replacement 和 CRD 身份分配。新启动的 Pod 在 egress 策略生效前可能会短暂发送流量；不要将其视为可立即 fail-closed 的源 IP 保证。

### 发布与恢复

应对期望的 values、策略、地址池定义以及必要的信任/密钥材料进行适当的版本管理和备份控制。应演练恢复流程；备份 ConfigMap 并不构成完整的 IPAM 或密码材料恢复计划。

对于次要版本升级，先升级到当前次要版本的最新补丁版本，运行必要的预检，然后**每次只升级一个次要版本**。按升级指南的要求保留初始的 `upgradeCompatibility`，并迁移已重命名/移除的 values。不要跨次要版本使用 `--reuse-values`。Agents、operator 和其他 Cilium 组件应统一到同一版本。

升级期间，经用户空间 proxy 转发的流量可能会重新连接；缓冲的监控事件也可能丢失。回滚前可能需要移除或迁移新功能/资源。通用的应用 blue/green 部署或 Helm 回滚，并不能保证 CNI 迁移可逆且零停机。

## 真实应用案例研究

### 有文档记录的历史可扩展性实验

官方可扩展性报告描述了 Google Cloud 上的 **1,000 个工作节点**、三个控制器节点，以及内核 **5.4.0-1009-gcp**。其设置没有标明 Cilium 版本，因此不得将这些结果标注为 Cilium 1.20.3 基准测试。报告讨论了其特定工作负载下的资源消耗和收敛情况；它既不是当前支持矩阵，也不是容量承诺。

其中的健康检查更改和较高的发布并发数是实验选择。引用该报告时应保留实际测试条件，并另行验证适用于运维的配置。

### 设计场景 1：大型电子商务

对于大量 Service 和高请求量的场景，可评估 eBPF Service 转发、身份/L7 策略、Hubble 和可选的 ClusterMesh。在相同拓扑和防护要求下测量 p95/p99 延迟、吞吐量、错误、每个请求的 CPU 消耗和策略收敛情况。此处没有具名实现或可复现测量结果能够支持普遍适用的提升百分比。

### 设计场景 2：金融服务

结合最小权限策略、范围适当的传输层/应用层加密，以及与应用/API 审计记录配套的受控 flow 导出。测试密钥轮换、事件丢失、保留期限和跨集群信任。Hubble flows 本身并不构成完整的监管审计证据，也不保证缩短审计时间。

### 设计场景 3：电信和边缘

在真实流量条件下评估 NIC/驱动程序支持、CPU 调度、Service 转发路径、数据包大小、丢包和延迟。XDP 可能有助于符合条件的转发路径。仅凭 XDP 并不能实现 5G 用户面功能，也不能证明任意硬件都能达到固定的每秒数据包数。远程站点仍需要底层网络，并且必须明确测试故障和恢复。

## 未来路线图与发展方向

社区路线图明确**不承诺任何日期**。对于特定功能，应关注发行说明、已接受的设计和 issues，而不是将期望集成清单视为交付承诺。

| 领域 | 需要调查的问题 |
| --- | --- |
| eBPF 和内核 | 提议的路径需要哪些内核功能、回移补丁、NIC 和架构？CO-RE 不会提供缺失的内核能力。 |
| 网络和 IPv6 | 所选发行版支持哪些 IPAM、路由、策略和外部集成组合？ |
| 安全与可观测性 | 这是 Cilium 网络策略、Beta 工作负载身份验证/加密、Tetragon 运行时强制执行，还是外部检测器/存储系统？ |
| 云、网格和无服务器 | 托管平台是否允许使用预期的 CNI/主机 hooks？是否保留了网格拦截和身份验证？ |
| 边缘、IoT、5G 和 AI/ML | 还需要哪些设备、传输、运行时或加速器集成？Kubernetes CNI 并不能提供所有特定于应用的能力。 |

可通过项目 issues、设计提案、文档和社区讨论参与其中。商业支持和托管发行版各自有独立的功能/支持合同。

## 当前 BGP 配置

旧的 `CiliumBGPPeeringPolicy` 示例不适用于此基线。当前配置将集群/节点选择、peer 设置和通告前缀分别放在三个 **`cilium.io/v2`** 资源中。有关 BGP Control Plane、LoadBalancer IP 通告、Egress Gateway 和边缘模式的详细信息，请参阅[BGP、LB、egress 和边缘](11-bgp-lb-egress-edge.md)；有关多集群，请参阅[ClusterMesh 安装与升级](13-clustermesh-install-upgrade.md)。

这是一个用于隔离路由实验环境的配置模型，并非完整的云路由器设置。它假设使用 cluster-pool 或 Kubernetes host-scope IPAM 通告 `PodCIDR`、peer 路由器可达、路由器已完成相应配置，并且节点已按计划标记为 `cilium-bgp=lab`。`192.0.2.1` 是文档示例地址；请将其替换为真实的 peer IP，不带 `/32`。多池 IPAM 使用不同的通告类型和池选择方式。

```yaml
# bgp-values.yaml
bgpControlPlane:
  enabled: true
```
```yaml
# bgp-lab.yaml
apiVersion: cilium.io/v2
kind: CiliumBGPClusterConfig
metadata:
  name: lab-bgp
spec:
  nodeSelector:
    matchLabels:
      cilium-bgp: lab
  bgpInstances:
  - name: asn-64512
    localASN: 64512
    peers:
    - name: router-64513
      peerASN: 64513
      peerAddress: 192.0.2.1
      peerConfigRef:
        name: lab-peer
---
apiVersion: cilium.io/v2
kind: CiliumBGPPeerConfig
metadata:
  name: lab-peer
spec:
  timers:
    connectRetryTimeSeconds: 120
    holdTimeSeconds: 90
    keepAliveTimeSeconds: 30
  gracefulRestart:
    enabled: true
    restartTimeSeconds: 120
  families:
  - afi: ipv4
    safi: unicast
    advertisements:
      matchLabels:
        advertise: lab
---
apiVersion: cilium.io/v2
kind: CiliumBGPAdvertisement
metadata:
  name: lab-pod-cidrs
  labels:
    advertise: lab
spec:
  advertisements:
  - advertisementType: PodCIDR
```

peer 的通告选择器会匹配 `advertise: lab`，而 `peerConfigRef` 会解析为 `lab-peer`。Graceful Restart 需要 peer 行为兼容，并配置适当的计时器；它无法保留已失效的数据路径，也无法保证应用可用性。BGP 会通告可达性，但**不会安装本地数据路径路由**或创建 DNS 记录。

在路由实验环境中准备并应用合适的配置后，请检查 Cilium 状态和外部路由器收到的路由：

```bash
kubectl get ciliumbgpclusterconfigs,ciliumbgppeerconfigs,ciliumbgpadvertisements
cilium bgp peers
cilium bgp routes advertised ipv4 unicast
```

请另行测试实际的正向/返回流量。不要把存在已久的 HTTP 策略或任意百分比的性能提升描述为旧版本的新功能。从 Cilium 1.18 或更早的次要版本迁移时，请查阅确切版本的发行说明。

## 后续步骤

请使用[IPAM 和策略](04-ipam-policy.md)、[L2–L7 网络](05-l2-l7-networking.md)和[安全/可见性](06-security-visibility.md)章节验证各条路径。每项结果都应附带基准测试条件和限制，然后演练分阶段发布和恢复。

确认性能测试创建的确切命名空间后，删除其中的资源：

```bash
set -eu
PERF_NS=cilium-advanced-perf-1
LAB_OWNER=$(kubectl get namespace "$PERF_NS" -o jsonpath='{.metadata.labels.docs-audit-lab}')
test "$LAB_OWNER" = cilium-advanced-07
kubectl delete namespace "$PERF_NS"
```

## 主要参考资料

- [调优指南](https://raw.githubusercontent.com/cilium/cilium/v1.20.3/Documentation/operations/performance/tuning.rst)
- [Chart values](https://raw.githubusercontent.com/cilium/cilium/v1.20.3/install/kubernetes/cilium/values.yaml)
- [Chart ConfigMap 模板](https://raw.githubusercontent.com/cilium/cilium/v1.20.3/install/kubernetes/cilium/templates/cilium-configmap.yaml)
- [映射容量设置](https://raw.githubusercontent.com/cilium/cilium/v1.20.3/Documentation/network/ebpf/maps.rst)
- [映射容量设置实现](https://raw.githubusercontent.com/cilium/cilium/v1.20.3/pkg/option/config.go)
- [升级指南](https://raw.githubusercontent.com/cilium/cilium/v1.20.3/Documentation/operations/upgrade.rst)
- [升级限制](https://raw.githubusercontent.com/cilium/cilium/v1.20.3/Documentation/operations/upgrade-warning.rst)
- [BGP 配置](https://raw.githubusercontent.com/cilium/cilium/v1.20.3/Documentation/network/bgp-control-plane/bgp-control-plane-configuration.rst)
- [BGP 运维](https://raw.githubusercontent.com/cilium/cilium/v1.20.3/Documentation/network/bgp-control-plane/bgp-control-plane-operation.rst)
- [Bandwidth Manager](https://raw.githubusercontent.com/cilium/cilium/v1.20.3/Documentation/network/kubernetes/bandwidth-manager.rst)
- [Egress Gateway](https://raw.githubusercontent.com/cilium/cilium/v1.20.3/Documentation/network/egress-gateway/egress-gateway.rst)
- [历史可扩展性报告](https://raw.githubusercontent.com/cilium/cilium/v1.20.3/Documentation/operations/performance/scalability/report.rst)
- [社区路线图](https://raw.githubusercontent.com/cilium/cilium/v1.20.3/Documentation/community/roadmap.rst)
- [Linux IP sysctl](https://www.kernel.org/doc/html/latest/networking/ip-sysctl.html)

[返回主页](README.md)

## 测验

请通过[主题测验](../../quizzes/networking/cilium/07-advanced-topics-quiz.md)复习运维边界和诊断命令。
