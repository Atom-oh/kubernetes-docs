# Cilium Service Mesh 最佳实践

> **评审基线**：Cilium 1.20.3 和 Cilium CLI 0.20.1。
> **最后评审时间**：October 16, 2026。有关 Kubernetes、EKS 和可选组件的兼容性检查，请参阅单独的[安装指南](./README.md)。

## 概述

运维计划必须将 CNI 归属、代理功能、策略实施、容量和恢复联系起来。以下数值是示例，应结合特定集群进行评审。它们不是经过生产测试的容量保证、CNI 迁移流程或完整的 EKS 安装方案。

## 生产部署检查清单

- [ ] 选择受支持的 Kubernetes/Cilium/平台组合、CPU 架构和节点操作系统。一般最低内核版本为 5.10，或有文档说明的等效版本，例如 RHEL 8.10 的 4.18；高级功能可能需要更新的内核。
- [ ] 记录当前 CNI、IPAM、Pod/Service/VPC CIDR、路由、MTU 和 kube-proxy 归属。在启用 kube-proxy 替换前，验证 API 服务器地址可达。
- [ ] 为每个工作负载选择 L7 归属方。Cilium Ingress/Gateway 需要满足其文档所述的 kube-proxy 替换和 L7 前提条件；与 Istio 共存时的设置则不同。
- [ ] 分别选择身份验证、加密和授权。在实施默认拒绝前，验证允许和拒绝的流量、DNS 以及必要的基础设施访问。
- [ ] 确定指标目标、实际标签、日志、告警路由和证书续订方式。测试缺失数据时的行为。
- [ ] 为副本放置和维护提供足够的合格节点。检查 Operator/Relay 就绪状态、干扰预算和 DaemonSet 更新策略。
- [ ] 记录经过测试的回滚点、保留的 chart/values/CRD 以及工作负载/策略清单。在有代表性的环境中演练。

### 需要评审的 Helm Values

将此**资源和可用性覆盖配置**与安装指南中的平台配置合并。它不会刻意选择通用的 IPAM 范围、禁用 kube-proxy 或启用所有可选安全功能。

```yaml
agent: true
resources:
  requests:
    cpu: 500m
    memory: 512Mi
  limits:
    cpu: 2000m
    memory: 2Gi
operator:
  replicas: 2
  podDisruptionBudget:
    enabled: true
    maxUnavailable: 1
  resources:
    requests:
      cpu: 100m
      memory: 128Mi
    limits:
      cpu: 1000m
      memory: 1Gi
l7Proxy: true
envoy:
  enabled: true
  updateStrategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 1
  resources:
    requests:
      cpu: 200m
      memory: 256Mi
    limits:
      cpu: 2000m
      memory: 2Gi
hubble:
  enabled: true
  relay:
    enabled: true
    replicas: 2
    podDisruptionBudget:
      enabled: true
      maxUnavailable: 1
    affinity:
      podAntiAffinity:
        requiredDuringSchedulingIgnoredDuringExecution:
        - topologyKey: kubernetes.io/hostname
          labelSelector:
            matchLabels:
              k8s-app: hubble-relay
    resources:
      requests:
        cpu: 100m
        memory: 128Mi
      limits:
        cpu: 1000m
        memory: 1Gi
updateStrategy:
  type: RollingUpdate
  rollingUpdate:
    maxUnavailable: 1
```

`agent` 是布尔值。Agent 资源 requests/limits 应配置在顶层 `resources` 下，而不是 `agent.resources`。原先两处相互冲突的资源定义已合并。这些 CPU/内存数值只是起始示例；应在实际策略数量、变更频率、流量和故障场景下进行测量。

Operator 的 chart 亲和性会让副本分散到不同主机。此处的 Relay 反亲和性也要求有两个合格节点。这并不能确保副本分布在不同可用区；请根据集群情况添加适当的拓扑要求。仅有两个副本，如果没有可调度的位置和正常工作的依赖项，并不能提供 HA。PDB 管理的是符合条件的自愿驱逐，不涵盖所有中断，也不约束 DaemonSet 控制器的滚动更新；直接删除 Pod 也会绕过驱逐保护。

外部 etcd 是一种具有自身运维要求的架构选择，并非达到某个节点数量阈值后就必须添加。保持所选的身份分配模式一致；如果要更改，请遵循有文档说明的迁移流程。

### 身份验证和加密

以下是一个**可选的**带外身份验证加 WireGuard 配置：

```yaml
encryption:
  enabled: true
  type: wireguard
  nodeEncryption: false
authentication:
  enabled: true
  mutual:
    spire:
      enabled: true
```

只有满足[安全指南](./03-security.md)中关于内核、端口、SPIRE 存储/身份和策略的前提条件时，才启用此配置。除了 SPIRE 设置外，还必须设置 `authentication.enabled`。必须由规则要求身份验证，才能强制实施身份验证。WireGuard 保护符合条件的节点间流量；基于 SPIRE 的带外身份验证不会让每个应用连接都变成 Istio 风格的 mTLS 会话。`nodeEncryption` 需要单独启用，本示例中保持为 false。

Cilium 1.20.3 还提供 **Beta 版 ztunnel 工作负载 mTLS**，并在安全指南中单独说明。它的默认内部 CA、命名空间加入方式以及 TCP/HBONE/策略限制，都与 SPIRE 带外路径不同。请明确选择设计；无论是复选框描述还是 Helm 功能标志，都不能证明安全覆盖范围等同。

## 容量规划指南

### 按组件测量

| 组件 | 需要测量的容量驱动因素 | 提高限制前的检查项 |
|---|---|---|
| Agent | 端点、身份、策略选择器/规则、连接变更频率、BPF map 和事件量 | 工作集、CPU/节流、map 压力、策略重新生成和丢包原因 |
| Envoy | 并发连接/流、TLS 处理、请求/响应大小、缓冲和过滤器开销 | 堆/RSS、CPU、排队、上游饱和情况，以及固定工作负载下的 p99 |
| Operator | IPAM/身份/节点变更频率和 API 延迟/速率限制 | 协调积压、EC2/Kubernetes 节流、分配失败 |
| Hubble Relay/UI | 观测流量、并发观察者、流缓冲区和查询范围 | 丢失事件、Relay 资源、查询延迟和副本放置 |

先前的节点数量表以及公式 `512Mi + Pods × 1Mi` 和 `256Mi + connections/second × 0.1Mi` 没有基准测试证据，因此不能作为通用的内存模型。峰值并发连接数、缓冲区生命周期、流量组合和策略基数都很重要；仅凭每秒请求数无法确定保留内存。根据实测的调度需求设置 requests，预留经过测试的余量，并在突发流量和丢失一个节点的情况下验证 limits。

### eBPF Map 容量规划

以下是一个明确的静态容量示例，不是在同一个 YAML 映射中列出多个备选方案：

```yaml
bpf:
  ctTcpMax: 2097152
  ctAnyMax: 1048576
  natMax: 2097152
  policyMapMax: 65536
```

当前 chart 的键为 `ctTcpMax`、`ctAnyMax` 和 `natMax`；旧值 `ctGlobalTcpMax`、`ctGlobalAnyMax` 和 `natGlobalMax` 会被忽略。Agent ConfigMap 标志仍使用 `bpf-ct-global-tcp-max` 等名称，因此不要把 chart 键与守护进程标志混淆。NAT 容量不得超过 TCP/其他 CT 总容量的三分之二；这些数值符合此限制。Map 条目上限并不保证应用会话的数量。

增大 map 会消耗节点/内核内存。调整 map 大小或更改其实现可能会中断状态和连接。检查渲染后的 ConfigMap 和实际 map 使用情况；不要根据节点数量推断容量，也不要把人类可读 CLI 输出的行数当作精确占用量。

## 性能调优

### eBPF 设置

```yaml
bpf:
  preallocateMaps: true
  mapDynamicSizeRatio: 0.0025
bpfClockProbe: false
```

预分配会以增加前期内存使用为代价，减少部分分配工作；它不是节省内存的开关。此替代方案使用动态容量比例。不要随意将其与静态 map 示例结合：显式容量会覆盖推导出的容量，分布式 LRU 也有额外限制。`bpfClockProbe` 是顶层键；更改现有 CT 状态的时钟表示方式时，必须遵循文档中的迁移注意事项。

`socketLB` 也是顶层键，不应嵌套在 `bpf` 下。对于与 Istio 共存的场景，其 `hostNamespaceOnly` 设置十分重要；不加区分地启用 socket 加速可能会绕过预期的代理拦截。旧设置 `bpf.lbBypassFIBLookup` 不是受支持的 chart 值。

已发布的调优指南中的 netkit/BIG TCP 配置文件有内核/NIC 和迁移前提条件（该配置文件要求内核 6.8）。现有 veth Pod 不能仅通过切换一个值就完成转换。请采用有文档说明的逐节点/新节点迁移方式，并在扩大范围前验证加密、路由和应用行为。

### 网络栈

首先读取节点设置：

```bash
sysctl net.core.somaxconn net.ipv4.tcp_max_syn_backlog \
  net.core.netdev_max_backlog net.ipv4.tcp_fin_timeout net.ipv4.tcp_tw_reuse
```

只有在确定相关队列或连接状态瓶颈，并检查目标内核的语义之后，才更改 sysctl。先前列出的全局 `sysctl -w` 命令并非针对特定工作负载的调优结果。特别是，`tcp_fin_timeout` 并不是通用的 TIME_WAIT 清理开关，TIME_WAIT 重用设置也不是通用的延迟修复方法。保留原始设置，并使用受管理的节点配置进行经过评审的滚动变更。

### Envoy

`CiliumEnvoyConfig.spec.resources` 接受特定的 xDS 资源类型，**不**接受 Bootstrap 对象。原先放在 CEC 中的 overload-manager Bootstrap 不会生效。单独的固定堆监视器也没有定义过载动作。

分别针对各自用途，使用 chart 的资源限制和完整的[连接池示例](./05-ingress-gateway.md#connection-pool-configuration)。过载管理器应放在进程 bootstrap 中，并包含受支持的动作和阈值。如果使用 `envoy.bootstrapConfigMap`，请保留 Cilium 所需的 bootstrap 接线，并根据确切的已发布 Envoy 镜像进行验证。替换整个 bootstrap 属于高级集成，并非安全的局部 CEC 补丁。

### 基准测试证据

先前的图表声称 native/Cilium/Istio 的 p99 值分别为 0.1/0.3/2.5 ms，但没有注明来源、版本、拓扑、负载、加密设置或复现数据，因此不再作为历史测量结果保留。如果存在证据，应保留真实的基准测试版本/日期；不要用新版本重新标注旧结果。

有用的对比应记录硬件、内核/CNI/mesh 版本、请求大小、并发数、连接数、TLS/策略/过滤器配置、预热时间、样本数、吞吐量、错误率和尾延迟。应比较行为相当的 L4 或 L7/安全配置，不要假设所有 Cilium 路径都是不经过 Envoy 的 mesh。

## 从 Sidecar Mesh 迁移

### 将 CNI 迁移与 Mesh 迁移分开

在现有 CNI 旁边安装第二个 CNI 并不足够。官方双 overlay 迁移流程要求使用不同的 Pod CIDR 和封装方式、逐节点控制、回收工作负载，并明确权衡策略强制执行方式。其限制包括未经测试的组合。请演练实际的平台场景；旧图中的“与现有 CNI 并行安装”通用步骤遗漏了关键要求。

如果 Cilium 已经提供网络功能，那么 mesh 共存就是另一项任务。Cilium 的 Istio 集成说明了 kube-proxy 保持启用的路径：

```yaml
kubeProxyReplacement: false
cni:
  exclusive: false
```

对于计划进行完整 kube-proxy 替换的路径：

```yaml
kubeProxyReplacement: true
socketLB:
  hostNamespaceOnly: true
cni:
  exclusive: false
```

保留所需的 API 服务器、CNI/IPAM 和平台设置。`cni.exclusive: false` 会保留 Istio CNI 等其他 CNI 配置；`socketLB.hostNamespaceOnly: true` 可避免干扰 Pod 级代理捕获。过时的 `tunnel: vxlan` 键不是当前的迁移方案。如果要单独选择 overlay，当前使用的键是 `routingMode` 和 `tunnelProtocol`，并需满足相应的路由/MTU 要求。

### 有计划地迁移工作负载

在做任何更改前，记录 `istio-injection`、修订版标签、Pod 注入注解、ambient 加入情况和现有 sidecar。命名空间标签会影响后续准入操作，但不会移除已经运行的 sidecar。修订版标签和单个 Pod 设置可能会覆盖过于简单的命名空间方案。在检查可用性并验证替代策略后，只重新创建选定的工作负载。

迁移期间，每个工作负载只保留一个 L7 策略归属方。Cilium 无法在 Istio 加密流量内部实施 HTTP 规则。仅为获得 HTTP 可见性而禁用 Istio mTLS 会改变安全性，并非自动转换步骤。Ambient HBONE 也会改变 Cilium 在 L4 上可观测的内容；如果仍使用这一路径，应由 Istio 负责工作负载身份和内部流量策略。

### 路由转换示例

前提条件：已就绪的 `app: reviews` Pod，带有 `version: v1` 或 `v2` 标签，并在 Pod 端口 9080 上提供 HTTP 服务。不同的 Service 可以明确选择版本：

```yaml
apiVersion: v1
kind: Service
metadata:
  name: reviews
  namespace: default
spec:
  selector:
    app: reviews
  ports:
  - name: http
    port: 9080
    targetPort: 9080
---
apiVersion: v1
kind: Service
metadata:
  name: reviews-v1
  namespace: default
spec:
  selector:
    app: reviews
    version: v1
  ports:
  - name: http
    port: 9080
    targetPort: 9080
---
apiVersion: v1
kind: Service
metadata:
  name: reviews-v2
  namespace: default
spec:
  selector:
    app: reviews
    version: v2
  ports:
  - name: http
    port: 9080
    targetPort: 9080
```

Istio 路由配置需要同时包含 VirtualService 和子集定义：

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: reviews-route
  namespace: default
spec:
  hosts:
  - reviews
  http:
  - match:
    - headers:
        end-user:
          exact: jason
    route:
    - destination:
        host: reviews
        subset: v2
  - route:
    - destination:
        host: reviews
        subset: v1
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews-subsets
  namespace: default
spec:
  host: reviews
  subsets:
  - name: v1
    labels:
      version: v1
  - name: v2
    labels:
      version: v2
```

对于 L7 归属已转移的工作负载，完整的 Cilium CEC 可以实现此类基于标头选择的行为：

```yaml
apiVersion: cilium.io/v2
kind: CiliumEnvoyConfig
metadata:
  name: reviews-route
  namespace: default
spec:
  services:
  - name: reviews
    namespace: default
    ports:
    - 9080
    listener: reviews-listener
  backendServices:
  - name: reviews-v1
    namespace: default
  - name: reviews-v2
    namespace: default
  resources:
  - '@type': type.googleapis.com/envoy.config.listener.v3.Listener
    name: reviews-listener
    filter_chains:
    - filters:
      - name: envoy.filters.network.http_connection_manager
        typed_config:
          '@type': type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
          stat_prefix: reviews-migration
          route_config:
            name: reviews-routes
            virtual_hosts:
            - name: reviews
              domains:
              - '*'
              routes:
              - match:
                  prefix: /
                  headers:
                  - name: end-user
                    string_match:
                      exact: jason
                route:
                  cluster: default/reviews-v2
              - match:
                  prefix: /
                route:
                  cluster: default/reviews-v1
          http_filters:
          - name: envoy.filters.http.router
            typed_config:
              '@type': type.googleapis.com/envoy.extensions.filters.http.router.v3.Router
  - '@type': type.googleapis.com/envoy.config.cluster.v3.Cluster
    name: default/reviews-v1
    type: EDS
    connect_timeout: 5s
  - '@type': type.googleapis.com/envoy.config.cluster.v3.Cluster
    name: default/reviews-v2
    type: EDS
    connect_timeout: 5s
```

该 CEC 包含 Listener、HCM/router、两个 EDS Cluster 和实际的后端 Service 引用。Cilium 会提供动态端点配置。`end-user: jason` 是不可信的路由输入，并非身份验证。此示例没有复制 Istio 的所有超时/重试/mTLS/遥测行为；请分别比较这些行为，并在保护写入操作时参考[重试指南](./02-traffic-management.md#retry-configuration)。不要将两种实现都附加到同一条活动流量路径上，并假设它们的归属方式等同。

### 授权并非机械式转换

对于由 Istio 管理、Pod 端口为 8080 的 `app: httpbin` 工作负载，要求传入流量使用 mTLS，并允许经过身份验证的特定 service-account 主体：

```yaml
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: httpbin-strict
  namespace: default
spec:
  selector:
    matchLabels:
      app: httpbin
  mtls:
    mode: STRICT
---
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: httpbin
  namespace: default
spec:
  selector:
    matchLabels:
      app: httpbin
  action: ALLOW
  rules:
  - from:
    - source:
        principals:
        - cluster.local/ns/default/sa/sleep
    to:
    - operation:
        methods:
        - GET
        paths:
        - /info*
        ports:
        - '8080'
```

针对同一命名空间/service-account 标签选择和 GET/路径意图的 Cilium 策略候选配置如下：

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: httpbin
  namespace: default
spec:
  endpointSelector:
    matchLabels:
      k8s:app: httpbin
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: default
        k8s:io.cilium.k8s.policy.serviceaccount: sleep
    authentication:
      mode: required
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
      rules:
        http:
        - method: ^GET$
          path: ^/info.*$
```

此配置要求单独安装 Cilium 身份验证系统；它不会使用 Istio 证书主体。两者的安全身份、信任域、身份验证交换和加密覆盖范围各不相同。端口指的是 **Pod 目标端口**，不能假设它就是 Service 端口。两种系统中的其他 allow 策略都可能扩大访问范围，而此 ingress 规则不会拒绝 Cilium egress。在认定迁移等效之前，应测试允许的 GET、拒绝的方法/路径、错误的 service account、缺少身份验证的情况以及加密/未加密路径。

### 回滚计划

在部署系统中保留原始工作负载模板、标签、策略、Secrets/证书归属和 Helm values。明确记录迁移归属的资源。首先恢复所选的旧流量/策略路径并验证其身份和强制执行情况，然后按经过测试的顺序，只删除已替换的迁移资源。

旧脚本会删除某个命名空间中的**所有 CiliumNetworkPolicy**，这可能会移除无关的默认拒绝保护，因此已将其删除。重新启用一个注入标签并重启所有 Deployments，也不足以处理修订版管理的注入、ambient 加入、StatefulSets 或 Jobs。回滚 CNI/IPAM 可能需要重新创建节点和 Pod，属于单独的恢复流程。

## 渐进式采用

如果 Cilium 只应提供 L3/L4 网络和策略，请明确禁用相关的 Cilium L7 功能：

```yaml
l7Proxy: false
envoy:
  enabled: false
ingressController:
  enabled: false
gatewayAPI:
  enabled: false
```

当 L7 仍处于启用状态时，单独设置 `envoy.enabled: false` 会选择嵌入式 Envoy 模式，并不会禁用所有 Cilium L7 行为。在移除相关功能前，应盘点现有 L7 策略、Ingress/Gateway 资源和 CEC。使用 Istio ambient 时，Cilium 看到的是 HBONE 传输流量，而不是像普通明文流量那样看到原始的内部工作负载流量。

| 阶段 | L7 归属和退出标准 |
|---|---|
| 建立网络 | 在当前 mesh 保持预期流量归属的同时，验证 Cilium CNI/L3/L4 行为 |
| 转移选定工作负载 | 按工作负载划分归属；通过否定测试比较路由、身份、加密、重试和遥测 |
| 退役旧组件 | 只有在验证所有依赖工作负载和恢复流程后，才移除旧组件 |

此前的迁移图重复了无差别删除策略的回滚方式，并过度简化了共存情况；本表取代了那些步骤。

## 监控和告警

### 明确的抓取标签

首先安装 Prometheus Operator CRD，并配置其 ServiceMonitor/PrometheusRule 选择器。此覆盖配置修正了示例 job 名称并添加了集群标签；请将 `example-cluster` 替换为实际集群标识，并相应调整 `release` 选择器：

```yaml
prometheus:
  enabled: true
  serviceMonitor:
    enabled: true
    labels:
      release: prometheus
    relabelings:
    - sourceLabels:
      - __meta_kubernetes_pod_node_name
      targetLabel: node
    - targetLabel: cluster
      replacement: example-cluster
    - targetLabel: job
      replacement: cilium-agent
envoy:
  prometheus:
    enabled: true
    serviceMonitor:
      enabled: true
      labels:
        release: prometheus
      relabelings:
      - sourceLabels:
        - __meta_kubernetes_pod_node_name
        targetLabel: node
      - targetLabel: cluster
        replacement: example-cluster
      - targetLabel: job
        replacement: cilium-envoy
```

Hubble HTTPv2 上下文和 recording rules 在[可观测性指南](./04-observability.md)中单独配置。只有满足必要可见性条件的流量才会产生 L7 观测数据。请使用可信的内部指标路径；这些值不会配置远程 Prometheus 可达性。

### 运维规则

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: cilium-operational-signals
  namespace: monitoring
  labels:
    release: prometheus
spec:
  groups:
  - name: cilium.operational
    rules:
    - alert: CiliumMetricsScrapeFailed
      expr: up{job=~"cilium-agent|cilium-envoy"} == 0
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: Known Cilium metrics target cannot be scraped
    - alert: HighObservedPacketDrops
      expr: sum by (cluster, node, direction, reason) (rate(cilium_drop_count_total[5m]))
        > 1000
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: High observed packet drop count
    - alert: HighBPFMapPressure
      expr: cilium_bpf_map_pressure > 0.8
      for: 10m
      labels:
        severity: warning
      annotations:
        summary: High pressure in an instrumented BPF map
```

抓取 `up` 失败表示目标访问失败，并不一定意味着 Agent/Envoy 进程已停止。如果服务发现移除了某个目标，其 `up` 序列可能会彻底消失；请另行对比预期的节点/DaemonSet 清单。`cilium_proxy_redirects` 统计的是已安装的重定向，数值为零也可能完全正常；它不能代表 Envoy 是否存活。

旧的 `cilium_datapath_conntrack_active/max` 比率使用了不存在的指标。CT GC 观测数据不是即时的全容量仪表。Map 压力指标仅涵盖已检测的 map 及其发出规则；请验证实际包含哪些 map。上述丢包和压力阈值仅为示例，必须根据流量、原因、持续时间和预期的策略拒绝情况进行校准。

### 导入仪表板

这是可在 Grafana UI 中导入的独立经典仪表板 JSON，不是 HTTP API 封装。请选择 Prometheus 数据源，并先安装可观测性指南中的 `cilium_hubble:*` recording rules：

```json
{
  "__inputs": [
    {
      "name": "DS_PROMETHEUS",
      "label": "Prometheus",
      "type": "datasource",
      "pluginId": "prometheus",
      "pluginName": "Prometheus"
    }
  ],
  "id": null,
  "uid": "cilium-operational",
  "title": "Cilium operational signals",
  "tags": [
    "cilium",
    "hubble"
  ],
  "schemaVersion": 38,
  "version": 1,
  "timezone": "browser",
  "time": {
    "from": "now-1h",
    "to": "now"
  },
  "refresh": "30s",
  "panels": [
    {
      "id": 10,
      "title": "Successfully scraped agent targets",
      "type": "stat",
      "gridPos": {
        "x": 0,
        "y": 0,
        "w": 12,
        "h": 8
      },
      "datasource": {
        "type": "prometheus",
        "uid": "${DS_PROMETHEUS}"
      },
      "targets": [
        {
          "refId": "A",
          "expr": "sum by (cluster) (up{job=\"cilium-agent\"})",
          "legendFormat": "{{cluster}}"
        }
      ]
    },
    {
      "id": 1,
      "title": "Observed HTTP responses/s",
      "type": "timeseries",
      "gridPos": {
        "x": 12,
        "y": 0,
        "w": 12,
        "h": 8
      },
      "datasource": {
        "type": "prometheus",
        "uid": "${DS_PROMETHEUS}"
      },
      "targets": [
        {
          "refId": "A",
          "expr": "cilium_hubble:http_responses:rate5m",
          "legendFormat": "{{cluster}} / {{destination_namespace}} / {{destination_workload}}"
        }
      ],
      "fieldConfig": {
        "defaults": {
          "unit": "reqps"
        },
        "overrides": []
      }
    },
    {
      "id": 2,
      "title": "Observed HTTP5xx (%)",
      "type": "timeseries",
      "gridPos": {
        "x": 0,
        "y": 8,
        "w": 12,
        "h": 8
      },
      "datasource": {
        "type": "prometheus",
        "uid": "${DS_PROMETHEUS}"
      },
      "targets": [
        {
          "refId": "A",
          "expr": "cilium_hubble:http_5xx_percent:rate5m",
          "legendFormat": "{{cluster}} / {{destination_namespace}} / {{destination_workload}}"
        }
      ],
      "fieldConfig": {
        "defaults": {
          "unit": "percent"
        },
        "overrides": []
      }
    },
    {
      "id": 3,
      "title": "Observed HTTP P99",
      "type": "timeseries",
      "gridPos": {
        "x": 12,
        "y": 8,
        "w": 12,
        "h": 8
      },
      "datasource": {
        "type": "prometheus",
        "uid": "${DS_PROMETHEUS}"
      },
      "targets": [
        {
          "refId": "A",
          "expr": "histogram_quantile(0.99, cilium_hubble:http_latency_bucket:rate5m)",
          "legendFormat": "{{cluster}} / {{destination_namespace}} / {{destination_workload}}"
        }
      ],
      "fieldConfig": {
        "defaults": {
          "unit": "s"
        },
        "overrides": []
      }
    }
  ]
}
```

健康状况面板统计的是成功抓取的 Agent 目标，而不是“健康的 Pod”。HTTP 面板遵循 recording rules 的服务端边界、命名空间/工作负载/集群范围和分子数据缺失时的行为。无数据并不等于没有故障；此仪表板依赖上述数据源和标签。

## 升级策略

### 滚动升级前先评审

Cilium 只会测试**相邻次要版本之间**的升级和回滚。首先将当前次要版本更新到最新补丁版本，并阅读所有中间版本发布说明中的必要变更。以下目标版本为 1.20.3；从旧版 1.16/1.17 直接跳转到该版本不受支持。

记录 `upgradeCompatibility` 所使用的**最初安装的次要版本**，不要随意选择目标版本/当前版本。导出现有用户 values，评审已重命名/移除的键，并将修改后的配置保存为 `reviewed-values.yaml`。如果该文件或导出的 values 包含敏感内容，请妥善保密：

```bash
set -eu
umask 077
CILIUM_TARGET_VERSION=1.20.3
: "${INITIAL_CILIUM_MINOR:?Set the initial installed Cilium minor, for example 1.19}"
helm get values cilium -n kube-system -o yaml > old-values.yaml
helm history cilium -n kube-system
helm repo add cilium https://helm.cilium.io/
helm repo update cilium
test -s reviewed-values.yaml
helm template cilium cilium/cilium -n kube-system \
  --version "$CILIUM_TARGET_VERSION" -f reviewed-values.yaml \
  --set-string "upgradeCompatibility=$INITIAL_CILIUM_MINOR" > candidate.yaml
```

执行下一步前，请评审生成的资源和官方预检流程。`helm diff` 是需要单独安装的可选插件，并非 Helm 内置功能。更改版本时应避免使用 `--reuse-values`；它可能会掩盖新引入的 chart 默认值。

只有在确认升级路径受支持，并已制定维护/恢复计划后，才可在同一个 shell/会话中执行经过评审的变更：

```bash
set -eu
: "${CILIUM_TARGET_VERSION:?Use the previously reviewed target version}"
: "${INITIAL_CILIUM_MINOR:?Use the previously reviewed initial installed minor}"
helm upgrade cilium cilium/cilium -n kube-system \
  --version "$CILIUM_TARGET_VERSION" -f reviewed-values.yaml \
  --set-string "upgradeCompatibility=$INITIAL_CILIUM_MINOR" --wait --timeout 10m
cilium status --wait
kubectl -n kube-system get daemonset cilium cilium-envoy
kubectl -n kube-system get deployment cilium-operator hubble-relay
```

`cilium connectivity test` 是一种有用的**主动**验证方式，会创建测试工作负载并产生网络流量；应在计划的测试环境中运行，不要把它当作只读状态命令。除了组件就绪情况外，还应检查特定于应用的策略否定测试和长连接。

### Canary 策略

仅有节点标签并不能选择不同版本的 Cilium。不要为了创建 Canary 而部署第二个重叠的 Cilium DaemonSet：Agent 会共享节点级网络资源和集群配置。请先在有代表性的测试集群中验证该版本。任何受控的逐节点滚动更新都必须使用受支持的单一归属机制，考虑 Operator/共享 ConfigMap 变更，并限制临时版本偏差。在稳定运行期间，所有 Cilium 组件都应运行相同版本。

### 回滚

检查新 CRD/功能/状态是否会妨碍安全降级后，选择一个**经过评审且兼容的** Helm 修订版本：

```bash
set -eu
helm history cilium -n kube-system
: "${CILIUM_ROLLBACK_REVISION:?Set the reviewed, compatible Helm revision}"
helm rollback cilium "$CILIUM_ROLLBACK_REVISION" \
  -n kube-system --wait --timeout 10m
cilium status --wait
```

不要盲目降级到 1.15，也不要假设 Helm 修订版本回滚可以撤销节点网络、CRD schema 和所有已使用的新功能。应随变更一并保留特定版本的回滚前提条件和恢复测试。

## 故障排查

### 节点和策略状态

```bash
cilium status --wait
kubectl -n kube-system get pods -l k8s-app=cilium -o wide
kubectl -n kube-system exec ds/cilium -- cilium-dbg endpoint list
kubectl -n kube-system exec ds/cilium -- cilium-dbg policy get
kubectl -n kube-system exec ds/cilium -- cilium-dbg service list
kubectl -n kube-system exec ds/cilium -- cilium-dbg bpf ct list global
```

主机上的 `cilium` CLI 用于管理安装；Agent 内部的 `cilium-dbg` 用于检查本地数据路径状态。`exec ds/cilium` 会选择一个 Pod，因此在事故期间应指定受影响节点上的实际 Pod。列出 CT 条目可能会产生大量输出；用 `wc -l` 统计行数并不能可靠测量占用量。

### Envoy 和延迟

```bash
kubectl -n kube-system exec ds/cilium -- cilium-dbg status --verbose
kubectl -n kube-system exec ds/cilium -- cilium-dbg envoy admin config listeners
kubectl -n kube-system exec ds/cilium -- cilium-dbg envoy admin config routes
kubectl -n kube-system exec ds/cilium -- cilium-dbg envoy admin config clusters
kubectl -n kube-system exec ds/cilium -- cilium-dbg envoy admin metrics
```

请使用受支持的 admin 命令/socket 路径，不要假设 9901 端口上有未经身份验证的 TCP 监听器，也不要假设容器内有 `curl` 二进制文件。区分没有 L7 重定向、上游不可用、策略拒绝、连接饱和和应用响应缓慢等情况。请使用 Ingress/Gateway 和可观测性指南中观测到的直方图，并采用正确的单位和标签。

### 临时调试和日志

```yaml
debug:
  enabled: true
  verbose: flow envoy policy
```

`debug.verbose` 是以空格分隔的字符串，不是由布尔值组成的映射。只在限定时间的调查期间启用必要的组，之后恢复原始日志级别。

```bash
kubectl -n kube-system logs -l k8s-app=cilium -c cilium-agent --since=30m --tail=1000
kubectl -n kube-system logs -l k8s-app=cilium-envoy -c cilium-envoy --since=30m --tail=1000
cilium sysdump --output-filename cilium-audit
```

单独的 Envoy DaemonSet 使用 `k8s-app=cilium-envoy` 选择器。sysdump 是一项需要集群访问权限的收集操作，可能包含敏感配置/日志；分享前请检查归档内容。它不是直接在主机上调用 `cilium-bugtool`。

## EKS 专项指南

### ENI 模式和 AWS VPC CNI 链接模式

这是两种不同的设计。Cilium ENI IPAM 通过 Operator 管理 ENI/地址；AWS VPC CNI 链接模式则由 AWS VPC CNI 负责地址分配，并有自身的 L7/加密限制。请使用对应的安装流程。

IPv4 ENI overlay 配置如下：

```yaml
eni:
  enabled: true
ipam:
  mode: eni
routingMode: native
ipv4:
  enabled: true
ipv6:
  enabled: false
cluster:
  name: example-cluster
```

`eni.enabled` 会选择 AWS Operator 行为和相关 chart 默认值。请保持集群名称唯一，以避免 ENI 垃圾回收归属不明确。不要在 ENI 模式下添加通用的 `10.0.0.0/8` 集群池范围，也不要在检查实际节点设备和路由要求前硬编码 masquerade 接口。

`enableAWSSecurityGroups` 不是 chart 值。ENI 安全组来自受支持的 `eni.nodeSpec.securityGroups`/`securityGroupTags`，或来自文档所述的继承行为。这并不意味着 Kubernetes 策略会自动转换成 AWS SecurityGroupPolicy 对象。

**通用 ENI IPAM 参考文档将 IPv6 标为 Beta**，其中包括双栈子网/前缀和 IAM 前提条件；而 1.20.3 EKS 安装页面仍称仅支持 IPv4。此示例特意使用 IPv4，并记录了该来源之间的差异。不要忽略 Beta 功能，也不要仅凭通用参考文档就声称这是经过全面验证的 EKS IPv6 配置方案。

EKS Auto Mode 和 Fargate 不支持这种替代 CNI DaemonSet 安装路径。EKS Hybrid Nodes 使用 AWS 自己支持的 Cilium 指南和兼容矩阵；不要将该支持声明套用到任意自行管理的 EC2 Cilium 版本。

### 节点操作系统和容量

EKS 已于 **November 26, 2025** 停止发布 EKS 优化的 AL2 AMI；1.32 是最后一个支持的 Kubernetes 系列版本。请选择适用且受支持的 AL2023 或 Bottlerocket AMI，并核实其实际内核/架构及 Cilium 功能要求。通用 Linux 兼容性条目中提及 AL2，并不代表当前仍支持相应的 EKS AMI 生命周期。

应根据实测的 CPU、内存、网络/数据包限制、ENI/IP 容量、可用性和成本选择实例系列和规格。先前固定推荐 m6i/c6i/r6i 的做法并非基准测试结果。如果使用混合架构，请在 AMD64 和 Arm64 上分别验证每个 DaemonSet 和工作负载镜像。

### IAM

通过受支持的安装身份机制，为 Cilium Operator 使用专用角色；分别评审其信任策略和凭证访问。旧策略遗漏了 `AttachNetworkInterface`、`DescribeInstanceTypes`、`DescribeRouteTables` 和 `CreateTags` 等必要操作，因此并不是完整的 ENI 分配器策略。

有版本标注的 ENI 参考文档列出了基本和条件性 API 权限。应考虑 ENI 垃圾回收、释放多余 IP、实例筛选器和可选的 IPv6 分配。根据 AWS 服务授权支持情况，将读取/列出和修改权限分开；对受支持的修改操作，应将范围限制在预期区域/资源/标签内。一些 describe 操作需要 `Resource: "*"`，因此仅凭通配符本身，既不能证明权限配置正确，也不能证明权限过宽。要完整制定适用于特定账户的最小权限策略，还需要实际 IAM/资源上下文和 API 验证；本指南并未声称已经配置了此类策略。

## 延伸阅读

如需了解完整前提条件和示例，请继续参阅[安全](./03-security.md)、[可观测性](./04-observability.md)和[Ingress/Gateway](./05-ingress-gateway.md)指南。

- [Cilium 1.20.3 Helm values](https://github.com/cilium/cilium/blob/v1.20.3/install/kubernetes/cilium/values.yaml)
- [系统要求](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/operations/system_requirements.rst)
- [性能调优](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/operations/performance/tuning.rst)
- [升级流程](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/operations/upgrade.rst)
- [升级和回滚限制](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/operations/upgrade-warning.rst)
- [Istio 集成](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/network/servicemesh/istio.rst)
- [CNI 迁移](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/installation/k8s-install-migration.rst)
- [CEC 资源解析器](https://github.com/cilium/cilium/blob/v1.20.3/pkg/ciliumenvoyconfig/cec_resource_parser.go)
- [ENI 分配、安全组和权限](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/network/concepts/ipam/eni.rst)
- [EKS 安装注意事项](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/installation/requirements-eks.rst)
- [EKS AL2 AMI 退役](https://docs.aws.amazon.com/eks/latest/userguide/eks-ami-deprecation-faqs.html)
- [EKS 替代 CNI 支持](https://docs.aws.amazon.com/eks/latest/userguide/alternate-cni-plugins.html)
- [Cilium Envoy 诊断](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/cmdref/cilium-dbg_envoy_admin_config.md)
- [Linux TCP sysctl](https://docs.kernel.org/networking/ip-sysctl.html)
- [Kubernetes 干扰预算](https://kubernetes.io/docs/concepts/workloads/pods/disruptions/)
- [IAM 资源级权限故障排查](https://docs.aws.amazon.com/IAM/latest/UserGuide/troubleshoot_policies.html)
