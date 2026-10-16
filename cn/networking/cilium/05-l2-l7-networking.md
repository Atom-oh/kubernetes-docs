# L2–L7 网络与负载均衡

> **审查基线**：Cilium 1.20.2、CLI 0.20.1；Istio 示例使用 1.31 API。
> **最后审查**：October 15, 2026

## 实验环境设置

使用通过[安装](README.md)和[网络](03-networking.md)指南准备的一次性集群。检查平台/内核支持和 kubectl 版本偏差。HTTP 实验需要两个可调度的 Linux 节点。DSR/Maglev 实验还需要一个已准备好的无 kube-proxy 集群、可访问的真实 API-server 端点以及受支持的网络路径。

为实验选择完整的安装值。重复执行 `cilium install --config ...` 命令并不是实时功能迁移流程，并且在任意安装后删除 kube-proxy 并不是安全的捷径。

## 理解 OSI 分层

OSI 是一个概念模型，而不是七个 Cilium 进程或固定的策略钩子序列。

| 层级 | 角色 / 示例 | 与 Cilium 的关系 |
|---|---|---|
| L1 物理层 | 比特、介质、收发器、中继器 | 底层硬件/网络要求 |
| L2 数据链路层 | Ethernet 帧、MAC 寻址、桥接器/交换机 | 数据包处理和显式配置的 L2 Service 公告 |
| L3 网络层 | IP 数据包、路由、ICMP | 路由、身份/CIDR 策略和受支持的分片处理 |
| L4 传输层 | TCP 分段和可靠流；不保证交付/顺序的 UDP 数据报 | 端口/协议策略、连接状态、Service 转换 |
| L5 会话层 | 会话/对话组织 | 通常在应用程序/协议内部实现的概念功能 |
| L6 表示层 | 表示、编码和加密转换 | 从概念上讲 TLS 通常映射在此处，而非通用的独立 Linux 层 |
| L7 应用层 | HTTP、DNS、gRPC 和其他应用协议 | 受支持的代理策略；应用协议的存在并不意味着存在 Cilium 策略解析器 |

### 实际的分层特性

- **L2：**L2 Announcements 是 beta 功能，是为符合条件的 Service IP 配置的 ARP/NDP 响应机制。它需要 kube-proxy replacement 以及合适的设备/本地网络可达性。当选节点会接收该 Service 的流量；这并不提供任意 MAC/VLAN ACL 支持或通用 L2 bridge，也不承诺捕获每一个数据包。`externalTrafficPolicy: Local` 存在已记录的不兼容性。
- **L3：**IP/身份策略和路由具有模式特定的要求。组播是需要 VXLAN 的单独启用的 beta 功能；文档规定的最低内核版本在 AMD64 上为 5.10，在 AArch64 上为 6.0。不要假定它可在每种路由模式中工作。
- **L4：**TCP/UDP 端口策略、连接跟踪、socket/packet Service 负载均衡以及受支持的亲和性在不同的钩子上运行。socket 决策可能发生在数据包构建之前。
- **L7：**当前内置策略组为 HTTP 和 DNS。gRPC 使用受支持的 HTTP/2 路径。Kafka L7 规则已移除。TLS/SNI 功能需要其文档规定的代理配置；加密的应用内容不会自动变得可检查。

HTTP/gRPC 策略使用 Envoy；DNS 策略使用 Cilium 的 DNS proxy。根据 values/升级兼容性，Envoy 可以是由 agent 管理的进程，或专用的 `cilium-envoy` DaemonSet。启用 L7 的全新 1.20 chart 默认值倾向于 DaemonSet，且以下配置文件会显式设置它。添加策略不会覆盖所有安装设置。

## HTTP 策略实验

创建新的 namespace 和匹配的工作负载。镜像/digest 以及已知的服务器就绪路径来自官方 CLI 测试 Deployment 定义。

```bash
set -euo pipefail
kubectl create namespace cilium-l2l7-demo
kubectl label namespace cilium-l2l7-demo docs-audit-lab=cilium-l2l7-05
```

如果 namespace 已存在则停止；请一致地选择新名称，而不要复用其他运行的资源。

**`l7-app.yaml`**

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: client
  namespace: cilium-l2l7-demo
  labels:
    app: client
spec:
  automountServiceAccountToken: false
  containers:
  - name: client
    image: quay.io/cilium/alpine-curl:v1.10.0@sha256:913e8c9f3d960dde03882defa0edd3a919d529c2eb167caa7f54194528bde364
    command:
    - /usr/bin/pause
---
apiVersion: v1
kind: Pod
metadata:
  name: outsider
  namespace: cilium-l2l7-demo
  labels:
    app: outsider
spec:
  automountServiceAccountToken: false
  containers:
  - name: client
    image: quay.io/cilium/alpine-curl:v1.10.0@sha256:913e8c9f3d960dde03882defa0edd3a919d529c2eb167caa7f54194528bde364
    command:
    - /usr/bin/pause
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app1
  namespace: cilium-l2l7-demo
spec:
  replicas: 1
  selector:
    matchLabels:
      app: app1
  template:
    metadata:
      labels:
        app: app1
    spec:
      automountServiceAccountToken: false
      affinity:
        podAntiAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
          - labelSelector:
              matchLabels:
                app: client
            topologyKey: kubernetes.io/hostname
      containers:
      - name: http
        image: quay.io/cilium/json-mock:v1.4.1@sha256:6a66df90808a39c02e7a9d58af7bf0e54d8f8b7d4bc528f48c891969a7049195
        ports:
        - containerPort: 8080
          name: http
        readinessProbe:
          httpGet:
            path: /
            port: http
---
apiVersion: v1
kind: Service
metadata:
  name: app1-service
  namespace: cilium-l2l7-demo
spec:
  selector:
    app: app1
  ports:
  - name: http
    port: 80
    targetPort: http
    protocol: TCP
```


```bash
kubectl apply -f l7-app.yaml
kubectl -n cilium-l2l7-demo wait --for=condition=Ready pod/client pod/outsider --timeout=120s
kubectl -n cilium-l2l7-demo rollout status deployment/app1 --timeout=120s
kubectl -n cilium-l2l7-demo get pods,services -o wide
kubectl -n cilium-l2l7-demo exec client -- \
  curl --fail --silent --show-error --max-time 5 http://app1-service/
```

也要验证 outsider 的基线连通性。该 Service 暴露端口 80，但其后端监听 **8080**；Pod ingress 策略使用后端端口。这替代了不存在/不匹配的旧应用设置和默认标签/entrypoint 不符合示例的 client Pod。

**`app1-http.yaml`**

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: app1-http
  namespace: cilium-l2l7-demo
spec:
  endpointSelector:
    matchLabels:
      app: app1
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: cilium-l2l7-demo
        k8s:app: client
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
      rules:
        http:
        - method: ^GET$
          path: ^/$
        - method: ^POST$
          path: ^/api/v1$
          headerMatches:
          - name: x-demo-tenant
            value: team-a
```


```bash
kubectl apply -f app1-http.yaml
kubectl -n cilium-l2l7-demo get cnp app1-http -o yaml
```

策略实现后，具名 client 可以发出 GET `/` 请求。POST `/api/v1` 仅在带有完全匹配的 `x-demo-tenant: team-a` header 时才会被此规则允许；后端仍必须实现该 API 操作。只有在没有其他适用策略允许时，其他方法/路径/对端才会被拒绝。除应用响应外，还要验证已实现的策略和流证据。

该 header 是**演示过滤器，而非身份验证**。旧的 32 字符“token”条件不会验证身份、签名、issuer、expiry 或 authorization。在发布的 translator 中，包含值的 `headers` 字符串会按字面匹配该值：`X-Auth-Token: ^[a-zA-Z0-9]{32}$` 并不是正则 token 验证器。针对预期的精确值/存在性要求，请使用显式 `headerMatches`，并在应用程序/适当的 authentication 层中验证用户。

方法和路径支持正则表达式。内置 Cilium HTTP 策略没有任意 request-body predicate。header 存在性、完全相等、URL 过滤和应用 authorization 是不同的控制措施。

## Service Mesh 集成

Cilium 提供网络和受支持的网络策略，而 Istio 负责其已配置的代理和 mesh 行为。集成不会自动绕过 Istio sidecar、移除其 mTLS 成本、统一所有 trace，或保证请求更快。

```text
Configuration: istiod --> Istio Envoy proxies
Request: app --> source sidecar --> Cilium/network --> destination sidecar --> app
```

### 保留 Istio 的流量拦截

当前的 Cilium 集成指南提供 kube-proxy 共存模式和经过谨慎配置的完整 replacement 选项。共存配置片段为：

**`istio-cilium-values.yaml`**

```yaml
kubeProxyReplacement: false
socketLB:
  hostNamespaceOnly: true
cni:
  exclusive: false
```


对于有意准备的完整 replacement 设置，`kubeProxyReplacement: true` 还需要可访问的 API endpoint 和 replacement 前提条件。保留 `socketLB.hostNamespaceOnly: true`，以避免 Pod socket 转换绕过 Istio 拦截；共享节点 CNI 配置时使用 `cni.exclusive: false`。

Istio sidecar 重定向可以使用 init container 或 Istio CNI node agent；ambient 使用其相应的 node/CNI 路径。请遵循[维护中的 Istio 安装指南](../../service-mesh/istio/01-installation.md)，选择一种模式。Kubernetes API server 必须能够访问 Istio 的 admission webhook。受管 control-plane/overlay 网络可能需要已记录的路由或 host-network 解决方案；不要为每个 overlay 集群都指定 `istiod hostNetwork: true`。

### 保留 mTLS 并分配 L7 职责

不要将明文 Cilium HTTP 检查应用于 Istio 加密的工作负载流量。此示例在 Istio 中保留 Istio mTLS 和 L7 路由，并使用 Cilium **仅 L3/L4** 策略。仅为了使旧的组合 L7 示例通过而禁用 mTLS，会改变安全设计。

以下是为已准备好的 `istio-cilium-demo` namespace 配置的 **sidecar-mode**，其中包含 `productpage` 和 `reviews` 工作负载、端口为 9080 的 reviews Service，以及带有 `version: v1`/`v2` 标签的 reviews Pod。它不是完整的 Bookinfo Deployment。

**`istio-reviews.yaml`**

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: reviews-route
  namespace: istio-cilium-demo
spec:
  hosts:
  - reviews.istio-cilium-demo.svc.cluster.local
  http:
  - match:
    - headers:
        end-user:
          exact: jason
    route:
    - destination:
        host: reviews.istio-cilium-demo.svc.cluster.local
        subset: v2
        port:
          number: 9080
  - route:
    - destination:
        host: reviews.istio-cilium-demo.svc.cluster.local
        subset: v1
        port:
          number: 9080
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews-subsets
  namespace: istio-cilium-demo
spec:
  host: reviews.istio-cilium-demo.svc.cluster.local
  subsets:
  - name: v1
    labels:
      version: v1
  - name: v2
    labels:
      version: v2
---
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: default
  namespace: istio-cilium-demo
spec:
  mtls:
    mode: STRICT
---
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: reviews-l4
  namespace: istio-cilium-demo
spec:
  endpointSelector:
    matchLabels:
      app: reviews
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: istio-cilium-demo
        k8s:app: productpage
    toPorts:
    - ports:
      - port: '9080'
        protocol: TCP
```


DestinationRule 定义了 VirtualService 引用的 subset。`end-user: jason` header 选择一个演示路由；它不是经过验证的身份。验证成功的 sidecar 注入、实际 endpoint 标签、subset 就绪状态以及 mesh telemetry。

不要将 9080 Cilium 规则复用于 ambient 策略方案：ambient HBONE 在端口 15008 上使用加密隧道，并改变可见的流量/身份边界。请为该拓扑应用适当的 Istio 策略和平台特定的 Cilium 网络防护措施。

## 负载均衡架构

Cilium 的 service map、backend map、reverse-NAT 状态和连接跟踪支持不同的转发阶段。L7 Envoy 负载均衡是另一个组件；不要将其算法列表与 BPF Service datapath 混为一谈。

### BPF 转发模式与算法

| 设置 / 机制 | 含义和限制 |
|---|---|
| `loadBalancer.mode: snat` | 默认转发模式；适用的外部 Service 路径使用源地址转换/反向状态，而非直接返回路径 |
| `dsr` | 远程后端回复可以绕过 ingress 负载均衡节点。网络必须允许该返回路径；它不能恢复已被上游 proxy 转换的 client IP |
| `hybrid` | TCP 使用 DSR，UDP 使用 SNAT。这是有效的负载均衡行为，与无效的 tunnel/auto-direct-routing 组合不同 |
| 基于 Annotation 的转发 | 每个 Service 支持 opt-in 行为；转发 annotation 是创建时选择，变更它们可能中断连接 |
| `loadBalancer.algorithm: random` | 默认的 BPF 后端选择算法 |
| `maglev` | 用于受支持外部 N–S 路径的一致性选择，包括受支持的 XDP acceleration；普通 socket-LB E–W 连接不受 Maglev 约束 |
| `sessionAffinity: ClientIP` | 独立的 Kubernetes Service 亲和性。键为外部源 IP，或对于适用的集群内 socket-LB 流量，为 client 的 network-namespace cookie |

Maglev 并不保证在移除后端时会话仍然存活。节点需要一致的后端状态、表大小和 seed。默认表大小为 16381；以下使用的 65521 是允许值，而非通用建议。更大的表会消耗内存。亲和性到期和连接状态与哈希是分开的。

DSR 调度可使用 native-routing IP options、在已记录的 native/Geneve-overlay 配置下使用 Geneve，或使用已记录的仅 native IPIP/IP6IP6 路径。VXLAN overlay 不可与 Geneve DSR 调度互换。IPIP 有其自身的端口/转换限制；选择它之前请验证发行版指南。

XDP acceleration 需要受支持的设备/driver。`native` 要求所选设备支持它；`best-effort` 在受支持的位置启用它。仅写入旧的 `enable-xdp-acceleration` key 不会启用它，并且早期 XDP 转发可能无法在 tcpdump 的较晚捕获点看到。

### Cilium 与 kube-proxy

| 方面 | 正确比较 |
|---|---|
| Linux Service 实现 | Cilium 使用 BPF hook/map；kube-proxy 有 iptables 和 nftables 模式，另有自 Kubernetes 1.35 起弃用的 IPVS |
| 平台 | Cilium 规定的 Linux/内核要求适用；Windows kernelspace kube-proxy 是不同的实现 |
| 连接状态 | Cilium BPF 连接/NAT 状态不同于 Linux netfilter conntrack；“可选与始终”说法过于宽泛 |
| L7 | Cilium 集成受支持的 proxy；kube-proxy 的 Service 转发不是 HTTP 策略引擎 |
| 性能 | 在相同工作负载和配置下测量；任一产品名称都不能确定固定排名 |

不要仅因底层 Linux IPVS 子系统具有 direct-routing 能力，就推断 kube-proxy 的 DSR 配置。

## 已准备的 DSR/Maglev 实验

此 profile 用于全新的、已准备好的无 kube-proxy **IPv4 Geneve-overlay** 测试集群。它不会迁移现有 CNI、移除 kube-proxy 或配置 cloud anti-spoofing/routing 控制。使用不冲突的 Pod CIDR，并验证外部返回路径。

**`lb-values.yaml`**

```yaml
kubeProxyReplacement: true
routingMode: tunnel
tunnelProtocol: geneve
ipv4:
  enabled: true
ipv6:
  enabled: false
ipam:
  mode: cluster-pool
  operator:
    clusterPoolIPv4PodCIDRList:
    - 10.244.0.0/16
    clusterPoolIPv4MaskSize: 24
loadBalancer:
  mode: dsr
  dsrDispatch: geneve
  algorithm: maglev
  acceleration: disabled
maglev:
  tableSize: 65521
bpf:
  masquerade: true
enableIPv4Masquerade: true
enableIPv6Masquerade: false
l7Proxy: true
envoy:
  enabled: true
hubble:
  enabled: true
  relay:
    enabled: true
```


提供真实 API endpoint 和一个持久保存的每集群 Maglev seed。该 seed 是 12 个随机字节的 base64 编码；请生成一次，将其与 cluster values 一同存储并重复使用，而不要在每次升级时重新生成。

```bash
: "${API_SERVER_HOST:?Set the reachable real API server host, not its ClusterIP}"
: "${API_SERVER_PORT:?Set the actual API server port}"
: "${MAGLEV_SEED:?Set the persisted base64 encoding of 12 random bytes}"
helm repo add cilium https://helm.cilium.io/
helm repo update cilium
helm install cilium cilium/cilium --version 1.20.2 --namespace kube-system \
  --values lb-values.yaml \
  --set-string k8sServiceHost="$API_SERVER_HOST" \
  --set k8sServicePort="$API_SERVER_PORT" \
  --set-string maglev.hashSeed="$MAGLEV_SEED"
cilium status --wait
```

在所选 cluster 中使用本指南创建的 namespace；如果这是不同的一次性 cluster，请先在其中重复 namespace 创建/标记步骤。HTTP-policy 应用和此 external-LB backend 使用不同标签，因此早先仅针对 client 的 HTTP 规则不会意外阻止本实验。

**`lb-echo.yaml`**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: lb-echo
  namespace: cilium-l2l7-demo
spec:
  replicas: 1
  selector:
    matchLabels:
      app: lb-echo
  template:
    metadata:
      labels:
        app: lb-echo
    spec:
      automountServiceAccountToken: false
      containers:
      - name: http
        image: quay.io/cilium/json-mock:v1.4.1@sha256:6a66df90808a39c02e7a9d58af7bf0e54d8f8b7d4bc528f48c891969a7049195
        ports:
        - containerPort: 8080
          name: http
        readinessProbe:
          httpGet:
            path: /
            port: http
---
apiVersion: v1
kind: Service
metadata:
  name: lb-echo
  namespace: cilium-l2l7-demo
spec:
  type: NodePort
  selector:
    app: lb-echo
  ports:
  - name: http
    port: 80
    targetPort: http
    protocol: TCP
```


```bash
kubectl apply -f lb-echo.yaml
kubectl -n cilium-l2l7-demo rollout status deployment/lb-echo --timeout=120s
kubectl -n cilium-l2l7-demo get pods -l app=lb-echo -o wide
kubectl -n cilium-l2l7-demo get service lb-echo -o wide
NODEPORT=$(kubectl -n cilium-l2l7-demo get service lb-echo -o jsonpath='{.spec.ports[0].nodePort}')
```

使用一个与 backend node **不同**的可访问 ingress node，以及不受 Cilium 集群内 socket LB 影响的外部 client。从该 client 使用实际值请求 `http://ENTRY_NODE_IP:NODEPORT/`。从 Pod 对 ClusterIP 执行 curl 并不能证明外部 DSR 或 Maglev 行为。验证请求/响应路径和 backend/connection 状态；不要仅根据成功的 HTTP 响应推断它们。

## 地址伪装

Pod egress masquerading 会在已配置外部路径需要时更改源地址。它不是 encryption 或 firewall，并且不同于 Service DNAT 和 DSR forwarding。

以下片段仅在网络确实支持这些 Pod 源地址/返回路由时，才将示例 `10.0.0.0/8` 目标范围排除在源地址伪装之外：

**`masquerade-values.yaml`**

```yaml
bpf:
  masquerade: true
enableIPv4Masquerade: true
enableIPv6Masquerade: false
ipv4NativeRoutingCIDR: 10.0.0.0/8
```


`ipv4NativeRoutingCIDR` 表示假定的可路由范围及相应的地址伪装排除项。它不会安装路由，也不会将整个 datapath 切换为 native routing。在没有正常返回路由的情况下进行宽泛排除可能破坏连通性。

- BPF masquerading 在此版本中取决于 BPF NodePort 功能，并且仅适用于承载 BPF program 的设备。检查选定设备；必要时使用文档规定的 `devices` 配置。
- iptables 实现使用其文档规定的 `egressMasqueradeInterfaces` 行为。不要将该字段或已移除的通用 `masquerade-interfaces`/`masquerade-all` 示例视为通用 BPF 控制项。
- IPv6 BPF masquerading 被记录为 beta。两种实现都不会移除 Cilium 的平台/内核要求，并且最终都在 kernel 中处理流量。
- node-address exceptions、ip-masq-agent exclusions 以及后续 cloud/NAT gateways 会影响观察到的源地址。使用受控观察方以及 node-side 状态/捕获；访问任意公共站点不能证明特定 NAT 实现。

在相关 agent 上：

```bash
kubectl -n kube-system get pods -l k8s-app=cilium -o wide
export CILIUM_POD=cilium-REPLACE-WITH-AGENT-ON-TARGET-NODE
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg status --verbose
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg bpf nat list
```

## 分片处理与 MTU

发布的 fragment tracker 将 datagram identity 和 L4 source/destination ports 存储在有界 LRU map 中。它可以为缺少 L4 header 的后续 fragment 恢复端口上下文；它**不是 BPF payload-reassembly engine**，也不能保证抵御 fragment attack。

已记录的功能包括 IPv4 和 IPv6 tracking，通过相应 flag 默认启用，并标记为 beta。有效的 IPv4 flag 仍为 `enable-ipv4-fragment-tracking`。`bpf-fragments-map-max` 控制被跟踪 datagram 的 map capacity；旧的 `fragment-tracking-timeout` 和 `max-fragments-per-flow` 设置不是发布的配置约定。

使用 chart 的额外 configuration map 的显式示例：

**`fragment-values.yaml`**

```yaml
extraConfig:
  enable-ipv4-fragment-tracking: 'true'
  bpf-fragments-map-max: '8192'
```


8192 是 capacity 示例，而不是每个 flow 的最大 fragment 数。诊断 capacity 时，请检查 `cilium_ipv4_frag_datagrams` / `cilium_ipv6_frag_datagrams` 及其 pressure；pressure 并不是 reassembly-success 或 attack-prevention 计数器。

优先采用正确的数据包大小和可用的 path MTU discovery 路径。PMTUD 依赖相关的错误信号和网络行为；它并不保证在任何地方自动获得最佳大小。Cilium 的 `MTU` 是**底层网络覆盖值**。如[网络指南](03-networking.md)所述，在 IPv4 underlay 上普通 VXLAN 开销为 50 字节，在 IPv6 上为 70 字节；对 1500 字节路径盲目将 base 设为 1450 可能会重复扣除开销。

## 可观测性与故障排除

检查正确的 node、实际 Envoy deployment mode、预期策略、已实现的 endpoint 状态和最新流量。对于 agent-local 操作使用 `cilium-dbg`，对于 cluster 操作使用 standalone CLI。已移除的 `policy trace` 命令和强制 endpoint regeneration 并不是此诊断的起点。

在单独的 terminal 中保持已启用的 Hubble Relay port-forward 运行，然后观察相关 flow：

```bash
cilium hubble port-forward
```

```bash
hubble observe --namespace cilium-l2l7-demo --protocol http --last 20
hubble observe --namespace cilium-l2l7-demo --verdict DROPPED --last 20
```

HTTP 策略拒绝可能显示为 HTTP 403，而不是 packet DROPPED verdict。单独的 timeout 还可能意味着 readiness、DNS、routing、TLS 或 observation 问题。请关联各层，而不要将每个错误都解释为策略成功。

## 验证限制与来源

这些是经过 release-source/schema 检查的示例，带有有限的本地 fixture，而非已在生产环境测试的平台或 live-cluster benchmark。镜像执行、webhook 可达性、mTLS 流量、DSR 返回路径、NAT 行为和 fragmentation 仍需在准备好的环境中验证。仅清理本次运行带标签的应用资源；不要将移除 cluster CNI 作为实验清理。

- [Cilium kube-proxy replacement/DSR/Maglev](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/kubernetes/kubeproxy-free.rst)、[地址伪装](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/concepts/masquerading.rst)、[分片处理](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/concepts/fragmentation.rst)、[fragment map 实现](https://github.com/cilium/cilium/blob/v1.20.2/pkg/maps/fragmap/fragmap.go)
- [L2 Announcements](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/l2-announcements.rst)、[组播](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/multicast.rst)、[HTTP rule translator](https://github.com/cilium/cilium/blob/v1.20.2/pkg/envoy/policy/envoy_l7_rules_translator.go)、[Envoy chart 默认值](https://github.com/cilium/cilium/blob/v1.20.2/install/kubernetes/cilium/templates/_helpers.tpl)
- [Cilium/Istio 集成](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/servicemesh/istio.rst)、[Istio CNI/init-container 模式](https://istio.io/latest/docs/setup/additional-setup/cni/)、[webhook 要求](https://istio.io/latest/docs/ops/configuration/mesh/webhook/)、[Istio 1.31 schema](https://github.com/istio/istio/blob/1.31.0/manifests/charts/base/files/crd-all.gen.yaml)
- [Kubernetes Service proxy 模式/affinity](https://kubernetes.io/docs/reference/networking/virtual-ips/)、[Cilium 1.20.2 values](https://github.com/cilium/cilium/blob/v1.20.2/install/kubernetes/cilium/values.yaml)


[返回主页](README.md)

## 测验

[复习 L2–L7 和负载均衡问题](../../quizzes/networking/cilium/05-l2-l7-networking-quiz.md)。
