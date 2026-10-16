# 高级主题和实际案例

> **审查基准**：Cilium 1.20.2、Cilium CLI 0.20.1 和 Hubble CLI 1.20.2。
> **最后审查**：2026 年 10 月 15 日。Cilium 1.20 的 Kubernetes 兼容性范围为 1.33–1.36；以下历史测量保留其原始环境。

## 实验环境设置

使用[安装前提条件](README.md)以及一个至少具有两个可调度 Linux 节点的一次性测试集群。在结果记录中保留 OS、kernel、Cilium 设置、拓扑、MTU、策略、加密和测试工作负载。请在其受支持的 API-server 版本偏差范围内使用 kubectl。以下命令需要 Helm、jq 以及 Cilium/Hubble CLI；`kubectl top` 还需要 metrics API。

### 性能测试环境设置

在更改前记录现有部署：

```bash
cilium version
cilium status --verbose
kubectl version
kubectl get nodes -o wide
kubectl -n kube-system get pods -l k8s-app=cilium -o wide
helm get values cilium --namespace kube-system -o yaml > cilium-current-values.yaml
```

当前 CLI 可以创建自身匹配的测试工作负载。仅当可以接受生成网络负载和创建测试资源时运行此命令：

```bash
cilium connectivity perf --test-namespace cilium-advanced-perf \
  --namespace-labels docs-audit-lab=cilium-advanced-07 \
  --duration 10s --samples 2 --crr --udp \
  --host-net=false --pod-net=true --same-node=true --other-node=true \
  --report-dir ./cilium-advanced-perf-results
```

默认的单并发运行使用 **`cilium-advanced-perf-1`**，即使参数中没有该后缀。测试前请确保该 namespace 未被使用。`--duration` 应用于每个场景/样本，而不是完整运行；调度、设置和各种案例的组合都会增加时间。该命令是主动工作负载测试，而不是只读诊断。

比较同节点与跨节点结果、TCP 请求/响应与 UDP，以及实际的 CPU/内存/丢包行为。每次仅做一项计划中的更改后重复测试。成功运行并不能证明应用 SLO、生产容量上限或每条策略路径。审计在未运行测试或创建集群的情况下验证了这些命令约定。

## 性能调优与故障排除

### 性能调优架构

![Cilium 性能需要调查的四个方面：kernel 行为、eBPF map、资源分配和所选网络路径。](../../.gitbook/assets/en-networking-cilium-07-advanced-topics-0.png)

[查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-cilium-07-advanced-topics-0.html)

该图将调查领域分组；它并不要求增大每项设置或禁用安全控制。

### 性能调优领域

| 领域 | 要测量的内容及设置所控制的对象 |
| --- | --- |
| Socket backlog | `net.core.somaxconn` 限制 socket listen backlog；`net.ipv4.tcp_max_syn_backlog` 关系到每个 listener 处于待处理状态的 SYN_RECV 请求。检查服务器的 accept 行为和相关网络 namespace。 |
| 邻居条目 | `net.ipv4.neigh.default.gc_thresh1`、`gc_thresh2` 和 `gc_thresh3` 是不同的垃圾回收阈值。不存在单一的 `gc_thresh` 设置。 |
| 连接跟踪 | Netfilter 的 `nf_conntrack_max` 与 Cilium 的 BPF CT map 是独立机制。增大前者不会调整后者的大小。 |
| BPF map | 检查 map 压力、插入失败、变动和内存。CT、NAT、LB 及每个 endpoint 的策略 map 具有不同的范围和大小调整规则。 |
| CPU 和内存 | 分别测量 agent、operator、Envoy 和 Hubble。requests 会影响调度；CPU limits 可能造成限流，memory limits 可能导致 OOM 终止。提高所有 limits 不是诊断。 |
| 网络路径 | 确定 native/tunnel 路由、MTU、masquerading、加密和 Service 转发。XDP 加速适用于受支持的路径和 driver；它不是 kube-proxy replacement 的必需项。 |

比较性能时，请保持安全和路由要求不变。通过移除所需加密或策略得到的更快结果不是等效配置。

### Map 大小调整

仅在测量压力后，将以下内容保存为**候选更改**。将其合并到完整、已版本控制的 release values；不要用一个小片段替换整个 Cilium ConfigMap。

```yaml
# map-sizing-values.yaml
bpf:
  mapDynamicSizeRatio: 0.005
```

`0.005` 是用于动态大小调整的名义**节点内存的 0.5%**输入，而非 5%，也不是所有 Cilium 内存的硬限制。例如，在 map 限制、舍入和其他分配之前，32 GiB × 0.005 为 163.84 MiB。受影响的大型 map 包括 CT、NAT、neighbor 和 socket reverse-NAT map；其他 map 和 userspace 内存仍然独立。

显式的 `bpf.ctTcpMax`、`bpf.ctAnyMax` 或 `bpf.natMax` 值会覆盖这些 map 的动态大小调整。请使 NAT 容量与 CT 容量兼容，并验证最终解析的启动大小。增大 map 可能消耗更多内存；替换 map 可能中断现有连接。

分布式 LRU（`bpf.distributedLRU.enabled`）使用每 CPU 池来降低争用，但会在内存/驱逐方面有所权衡。它需要动态大小调整，并在启用时重新创建 map。官方高性能配置文件不是通用的实时切换选项：请在准备好的新节点上引入此类 datapath 更改，或使用文档化的迁移过程。

旧的 `proxy-max-memory-percentage`、`proxy-max-threads`、`enable-xdp`、`tunnel: disabled` 和 `kube-proxy-replacement: strict` 示例并非当前配置配方。请使用受支持的 chart 设置，如 `envoy.resources`、`routingMode`、布尔值 `kubeProxyReplacement` 和 `loadBalancer.acceleration`，并满足其前提条件。

### Hubble 成本和事件丢失

更大的事件队列可以吸收突发流量，但它会使用内存，且不能解决持续的处理不足或降低 CPU 消耗：

```yaml
# hubble-queue-values.yaml
hubble:
  eventQueueSize: 32768
```

如果重复的 trace event 占主导处理，请单独评估更长的聚合间隔：

```yaml
# hubble-aggregation-values.yaml
bpf:
  monitorAggregation: medium
  monitorInterval: 10s
```

实际 chart 字段是 **`bpf.monitorInterval`**，而不是 `bpf.events.monitorInterval`。部署前检查渲染后的 `monitor-aggregation-interval`。增大聚合、事件速率限制和禁用事件类别都会减少可用于 monitor、Hubble metrics 和导出的观测结果。丢失的 Hubble event 本身并非丢弃的应用数据包；请同时检查可观测性丢失和 datapath 丢包。

### 高级 Datapath 前提条件

| 功能 | 要检查的前提条件和限制 |
| --- | --- |
| netkit | 在此基准中为 Beta；需要 Linux 6.8+ 和 BPF host routing。现有 veth Pod 无法仅通过 agent 重启来切换设备类型。 |
| BIG TCP | 需要针对协议族的 kernel/NIC 要求；组合调优配置文件要求 Linux 6.8+ 和受支持的 NIC。它不是通用 MTU 增大。 |
| BPF host routing | 需要兼容的 kube-proxy replacement 和 BPF masquerading。它会绕过 host netfilter hook；请检查依赖这些 hook 的 Istio 和其他集成。 |
| XDP Service 加速 | 需要 native XDP-capable 设备和受支持的外部 Service 转发路径。请使用 driver/platform 指南并验证运行状态。 |
| Bandwidth Manager | 每 Pod egress 使用 EDT；ingress 使用 eBPF token bucket。带宽 annotation 中的 `10M` 表示 10 Mbit/s，而不是 10 MB/s。 |
| Pod 的 BBR | 需要 Bandwidth Manager、Linux 5.18+ 和 BPF host routing；新建 Pod 会采用该设置。仅 host 的 BBR 是一个独立选项。 |

带宽强制执行对 egress L7 Cilium 策略和诸如 kind 的嵌套网络 namespace 存在文档化限制。这些条件不同于普通 Cilium 安装要求。不要将一个调优配置文件作为所有 service-mesh、cloud 或 kernel 组合都能工作的证据。

### 有针对性的故障排除命令

集群操作使用独立的 `cilium` CLI，并在相关 agent 内部使用 **`cilium-dbg`** 查询本地 endpoint、策略和 map。选择正在调查的节点，而不是随意查询第一个 agent：

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

Endpoint ID 对该 agent 而言是本地的。请使用其 endpoint list 中的 ID：

```bash
: "${CILIUM_POD:?Select the owning Cilium Pod first}"
: "${ENDPOINT_ID:?Read the endpoint ID from the selected agent endpoint list}"
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- \
  cilium-dbg endpoint get "$ENDPOINT_ID"
# Stream local BPF drop events; stop with Ctrl-C.
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- \
  cilium-dbg monitor --type drop
```

`cilium-dbg map list` 列出 agent 的 map manager 已知的打开 map；它不是所有 kernel BPF map 的清单。`cilium-dbg monitor` 显示发出的 BPF event 和可选的捕获 trace，而不是无损的每个数据包 tcpdump。大型 CT-map dump 的成本可能很高；运行 `cilium-dbg bpf ct list global` 前，请检查 metrics 和受影响的节点。

对于 Hubble，先建立[安全性和可见性](06-security-visibility.md)中描述的本地 Relay 连接：

```bash
hubble status
hubble observe --protocol tcp --verdict DROPPED --since 1h
hubble observe --protocol dns --from-label k8s:app=frontend --last 100
hubble observe --http-status '5+' --from-namespace production --last 100
```

`--type` 选择 event type，而不是 DNS record type A。如需区分查询类型，请使用 DNS flow 字段。HTTP 状态过滤器使用 `5+`，而不是 `5xx`。保留的历史记录和 event 可用性限制 `--since 1h`；它无法恢复一小时内被覆盖的 event。

### 常见故障排除场景

| 症状 | 要收集的证据 | 下一步决策 |
| --- | --- | --- |
| CT/NAT 压力 | Map 压力、插入/丢弃原因、连接变动、实际配置的大小 | 调整大小前调查变动/超时和内存余量。 |
| OOM 或 CPU 饱和 | 容器终止原因、内存/CPU 历史、限流、proxy 和 Hubble 负载 | 找出责任组件并更改其预算或工作负载。 |
| 意外的策略结果 | 正确的 namespace/labels、endpoint 策略 revision、proxy error 和 Hubble verdict | 检查方向、累加的 allow rule 和 deny 优先级；普通 allow 并非按优先级排序的 firewall 列表。 |
| 跨节点故障 | DNS、node/pod route、MTU、tunnel/encryption port 和平台 firewall | 验证正向和返回路径；仅有 BGP session 并不能证明 datapath 可达性。 |
| 升级回归 | 新旧 values、版本说明、所有组件版本、proxy 重连 | 使用准备好的受支持 rollback 路径并调查功能兼容性。 |

## 大规模部署策略

容量规划必须包括 node/Pod 密度、Service 和 backend、identity、策略扩展、API watch 流量、IPAM 分配和 flow volume。策略的 object 数量本身并不能决定其每 endpoint 的 map 成本。

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

中央管理集群不能替代每个受管集群中的 operator。请为每个集群的 operator 和 agent 调整大小；chart 的 operator replicas 和 anti-affinity 需要足够的合格节点。通过配置好的 collector 聚合 metrics/logs。ClusterMesh 需要自己的地址、identity、信任和可达性设计；它不会自动复制每个策略资源。

`ciliumEndpointSlice.enabled` 是一项 opt-in Cilium 功能，不同于 Kubernetes EndpointSlice。它不是旧的 `enable-endpoint-slice` ConfigMap flag。启用前请评估版本和功能兼容性；Egress Gateway 当前不能与 CiliumEndpointSlice 或 ClusterMesh 结合使用。

Egress Gateway 将所选流量 **SNAT** 为可预测的 gateway 地址；它不会保留原始 Pod source address。Gateway interface/IP 和路由必须已经配置，包括 AWS 上特定于平台的要求。它需要 BPF masquerading、kube-proxy replacement 和 CRD identity allocation。新启动的 Pod 可能会在 egress policy 生效前短暂发送流量；不要将它视为立即 fail-closed 的 source-IP 保证。

### 发布和恢复

将所需 values、策略、address-pool 定义以及必要的信任/key material 置于适当的版本控制和备份控制之下。演练恢复；ConfigMap 备份不是完整的 IPAM 或加密恢复计划。

对于 minor 升级，先达到当前 minor 的最新 patch，运行所需 preflight，然后**一次只升级一个 minor 版本**。按升级指南的说明保留初始 `upgradeCompatibility`，并迁移重命名/移除的 values。不要跨 minor 版本使用 `--reuse-values`。Agent、operator 和其他 Cilium 组件应收敛到同一版本。

升级期间，经过 userspace proxy 的流量可能重新连接；缓冲的 monitoring event 可能丢失。新功能/资源可能需要在 rollback 有效之前移除或迁移。通用的应用 blue/green 部署或 Helm rollback 不能保证可逆、零停机的 CNI 迁移。

## 实际使用案例研究

### 已记录的历史可扩展性实验

官方可扩展性报告描述了 Google Cloud 上的 **1,000 个 worker node**、三个 controller node 和 kernel **5.4.0-1009-gcp**。其设置未标明 Cilium 版本，因此不得将这些结果重新标记为 Cilium 1.20.2 benchmark。该报告讨论了其自身工作负载下的资源消耗和收敛情况；它不是当前支持矩阵或容量承诺。

其 health-check 更改和大规模 rollout concurrency 是实验选择。引用时请保留实际测试条件，并单独验证操作配置。

### 设计场景 1：大规模电子商务

对于大量 Service 和高请求量，请评估 eBPF Service 转发、identity/L7 策略、Hubble 和可选 ClusterMesh。在相同拓扑和保护要求下，测量 p95/p99 latency、throughput、error、每个请求的 CPU 以及策略收敛。没有具名实现或可重现测量支持此处通用的百分比改进。

### 设计场景 2：金融服务

将最小权限策略、适当范围的传输/应用加密和受控 flow export 与应用/API audit record 相结合。测试 key rotation、event loss、retention 和跨集群信任。仅 Hubble flow 并不构成完整的监管审计证据，也不保证更短的审计时间。

### 设计场景 3：电信和边缘

在真实流量下评估 NIC/driver 支持、CPU 调度、Service 转发路径、数据包大小、丢包和延迟。XDP 可能有利于符合条件的转发路径。它本身无法实现 5G user-plane function，也无法证明任意硬件上固定的数据包每秒速率。远程站点仍需要 underlay 和明确的故障/恢复测试。

## 未来路线图和开发方向

社区路线图明确表示**不承诺日期**。请针对特定能力跟踪 release note、已接受的设计和 issue，而不是将期望的集成列表视为交付承诺。

| 领域 | 要调查的问题 |
| --- | --- |
| eBPF 和 kernel | 建议的路径需要哪项 kernel feature、backport、NIC 和架构？CO-RE 不会提供缺失的 kernel capability。 |
| 网络和 IPv6 | 所选 release 支持哪些 IPAM、路由、策略和外部集成组合？ |
| 安全性和可观测性 | 这是 Cilium network policy、Beta workload authentication/encryption、Tetragon runtime enforcement，还是外部 detector/storage system？ |
| Cloud、mesh 和 serverless | 受管平台是否允许预期的 CNI/host hook？是否保留 mesh interception 和 authentication？ |
| Edge、IoT、5G 和 AI/ML | 需要哪些额外的 device、transport、runtime 或 accelerator integration？Kubernetes CNI 不会建立所有应用特定能力。 |

通过项目 issue、设计提案、文档和社区讨论参与其中。商业支持和受管发行版具有各自的功能/支持合同。

## 当前 BGP 配置

对于此基准，之前的 `CiliumBGPPeeringPolicy` 示例已过时。当前配置将 cluster/node 选择、peer 设置和通告的前缀拆分为三个 **`cilium.io/v2`** 资源。有关 BGP Control Plane、LoadBalancer IP 通告、Egress Gateway 和 edge pattern 的深入内容，请参见[BGP、LB、egress 和 edge](11-bgp-lb-egress-edge.md)；有关多集群，请参见[ClusterMesh 安装和升级](13-clustermesh-install-upgrade.md)。

这是隔离路由实验室的配置模型，而不是完整的 cloud-router 设置。它假定使用 cluster-pool 或 Kubernetes host-scope IPAM 进行 `PodCIDR` 通告、存在可达的 peer router、对应的 router 配置，并且 node 被有意标记为 `cilium-bgp=lab`。`192.0.2.1` 是文档地址；请将其替换为真实 peer IP，且不带 `/32`。Multi-pool IPAM 使用不同的通告类型和 pool 选择。

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

Peer 的 advertisement selector 匹配 `advertise: lab`，而 `peerConfigRef` 解析为 `lab-peer`。Graceful Restart 需要兼容的 peer 行为和适当的 timer；它无法保留失败的 datapath 或保证应用可用性。BGP 通告可达性，但**不会安装本地 datapath route**或创建 DNS record。

在路由实验室中准备并应用适当配置后，检查 Cilium 的状态和外部 router 接收的 route：

```bash
kubectl get ciliumbgpclusterconfigs,ciliumbgppeerconfigs,ciliumbgpadvertisements
cilium bgp peers
cilium bgp routes advertised ipv4 unicast
```

单独测试实际的正向/返回流量。不要将长期存在的 HTTP policy 或任意百分比增益描述为旧 release 的新功能。从 Cilium 1.18 或其他较早 minor 版本迁移时，请查阅准确的 release note。

## 后续步骤

使用[IPAM 和策略](04-ipam-policy.md)、[L2–L7 网络](05-l2-l7-networking.md)和[安全性/可见性](06-security-visibility.md)章节验证各个路径。将 benchmark 条件和限制与每项结果一并保留，然后演练分阶段 rollout 和恢复。

审查性能测试创建的准确 namespace 后，删除其资源：

```bash
set -eu
PERF_NS=cilium-advanced-perf-1
LAB_OWNER=$(kubectl get namespace "$PERF_NS" -o jsonpath='{.metadata.labels.docs-audit-lab}')
test "$LAB_OWNER" = cilium-advanced-07
kubectl delete namespace "$PERF_NS"
```

## 主要参考资料

- [调优指南](https://raw.githubusercontent.com/cilium/cilium/v1.20.2/Documentation/operations/performance/tuning.rst)
- [Chart values](https://raw.githubusercontent.com/cilium/cilium/v1.20.2/install/kubernetes/cilium/values.yaml)
- [Chart ConfigMap 模板](https://raw.githubusercontent.com/cilium/cilium/v1.20.2/install/kubernetes/cilium/templates/cilium-configmap.yaml)
- [Map 大小调整](https://raw.githubusercontent.com/cilium/cilium/v1.20.2/Documentation/network/ebpf/maps.rst)
- [Map 大小调整实现](https://raw.githubusercontent.com/cilium/cilium/v1.20.2/pkg/option/config.go)
- [升级指南](https://raw.githubusercontent.com/cilium/cilium/v1.20.2/Documentation/operations/upgrade.rst)
- [升级限制](https://raw.githubusercontent.com/cilium/cilium/v1.20.2/Documentation/operations/upgrade-warning.rst)
- [BGP 配置](https://raw.githubusercontent.com/cilium/cilium/v1.20.2/Documentation/network/bgp-control-plane/bgp-control-plane-configuration.rst)
- [BGP 操作](https://raw.githubusercontent.com/cilium/cilium/v1.20.2/Documentation/network/bgp-control-plane/bgp-control-plane-operation.rst)
- [Bandwidth Manager](https://raw.githubusercontent.com/cilium/cilium/v1.20.2/Documentation/network/kubernetes/bandwidth-manager.rst)
- [Egress Gateway](https://raw.githubusercontent.com/cilium/cilium/v1.20.2/Documentation/network/egress-gateway/egress-gateway.rst)
- [历史可扩展性报告](https://raw.githubusercontent.com/cilium/cilium/v1.20.2/Documentation/operations/performance/scalability/report.rst)
- [社区路线图](https://raw.githubusercontent.com/cilium/cilium/v1.20.2/Documentation/community/roadmap.rst)
- [Linux IP sysctl](https://www.kernel.org/doc/html/latest/networking/ip-sysctl.html)

[返回主页](README.md)

## 测验

查看[主题测验](../../quizzes/networking/cilium/07-advanced-topics-quiz.md)，复习操作边界和诊断命令。
