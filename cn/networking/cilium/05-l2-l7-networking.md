# L2–L7 网络与负载均衡

> **审阅基线**：Cilium 1.20.3、CLI 0.20.1；Istio 示例使用 1.31 API。
> **最后审阅**：2026 年 10 月 16 日

## 实验环境设置

请使用[安装指南](README.md)和[网络指南](03-networking.md)准备一次性集群。检查平台/内核支持情况以及 kubectl 版本偏差。HTTP 实验需要两个可调度的 Linux 节点。DSR/Maglev 实验还需要预先准备的、无 kube-proxy 的集群、可访问的真实 API server 端点以及受支持的网络路径。

请为实验选择一套完整的安装参数。反复执行 `cilium install --config ...` 不是在线功能迁移流程；任意安装后直接删除 kube-proxy 也不是安全捷径。

## 理解 OSI 层

OSI 是一种概念模型，并不是七个 Cilium 进程，也不是固定顺序的一组策略挂钩。

| 层 | 作用/示例 | 与 Cilium 的关系 |
|---|---|---|
| L1 物理层 | 比特、介质、收发器、中继器 | 底层硬件/网络要求 |
| L2 数据链路层 | Ethernet 帧、MAC 寻址、网桥/交换机 | 数据包处理和显式配置的 L2 Service 通告 |
| L3 网络层 | IP 包、路由、ICMP | 路由、身份/CIDR 策略和受支持的分片处理 |
| L4 传输层 | TCP 报文段和可靠流；UDP 数据报不保证送达或顺序 | 端口/协议策略、连接状态、Service 转换 |
| L5 会话层 | 会话/对话组织 | 概念性功能，通常由应用/协议内部实现 |
| L6 表示层 | 表示形式、编码和加密转换 | TLS 常在概念上归入此层，并非 Linux 中普遍独立的一层 |
| L7 应用层 | HTTP、DNS、gRPC 等应用协议 | 受支持的代理策略；存在某种应用协议并不代表 Cilium 有对应策略解析器 |

### 各层实际功能

- **L2**：L2 Announcements 是 beta 功能，是针对符合条件的 Service IP、经配置后响应 ARP/NDP 的机制。它需要 kube-proxy 替代模式及合适的设备/本地网络可达性。被选举出的节点会接收该 Service 的流量；这不是任意 MAC/VLAN ACL 支持、通用 L2 网桥，也不保证捕获所有数据包。`externalTrafficPolicy: Local` 存在文档所述的不兼容；1.20.2 发布说明包含对此组合丢包问题的修复，因此应在实际使用的版本上验证行为。
- **L3**：IP/身份策略和路由有各自与模式相关的要求。多播是需单独启用的 beta 功能，要求使用 VXLAN；文档规定的内核最低版本为 AMD64 上的 5.10 和 AArch64 上的 6.0。不要假定它适用于所有路由模式。
- **L4**：TCP/UDP 端口策略、连接跟踪、socket/packet Service 负载均衡和受支持的亲和性工作在不同挂钩上。Socket 决策可能发生在数据包构建之前。
- **L7**：当前内置策略组为 HTTP 和 DNS。gRPC 使用受支持的 HTTP/2 路径。Kafka L7 规则已移除。TLS/SNI 功能需要按文档配置代理；不会自动检查加密的应用内容。

HTTP/gRPC 策略使用 Envoy；DNS 策略使用 Cilium DNS proxy。根据 values/升级兼容性，Envoy 可以是由 agent 管理的进程，也可以是独立的 `cilium-envoy` DaemonSet。启用 L7 的全新 1.20 Chart 默认更倾向于使用 DaemonSet，下面的配置也明确指定了它。添加策略不会覆盖所有安装设置。

## HTTP 策略实验

创建新的命名空间及匹配的工作负载。镜像/digest 和已知的服务器就绪路径来自官方 CLI 测试部署定义。

```bash
set -euo pipefail
kubectl create namespace cilium-l2l7-demo
kubectl label namespace cilium-l2l7-demo docs-audit-lab=cilium-l2l7-05
```

如果命名空间已存在则停止；请始终一致地改用新名称，不要复用其他运行留下的资源。

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

也要验证外部客户端基线连通性。Service 暴露端口 80，但后端监听 **8080**；Pod 入站策略使用的是后端端口。此配置替换了不存在/不匹配的旧应用设置，也替换了默认标签/入口点与示例不匹配的客户端 Pod。

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

策略生效后，指定客户端可以发起 GET `/` 请求。此规则只允许携带精确 `x-demo-tenant: team-a` 标头的 POST `/api/v1`；后端仍必须实现该 API 操作。只有在没有其他适用策略放行的情况下，其他方法/路径/对端才会被拒绝。除应用响应外，还要核实已生效策略和流记录证据。

该标头只是**演示用筛选条件，不是身份验证**。旧的 32 字符“令牌”条件不能验证身份、签名、签发方、有效期或授权。在发布的 translator 中，`headers` 字符串包含值时会按字面值匹配：`X-Auth-Token: ^[a-zA-Z0-9]{32}$` 并不是正则令牌验证器。要匹配预期的精确值/存在性要求，应显式使用 `headerMatches`；并在应用或适当的身份验证层中验证用户身份。

方法和路径支持正则表达式。Cilium 内置 HTTP 策略没有任意请求正文谓词。标头存在性、精确相等、URL 筛选和应用授权是不同的控制。

## Service Mesh 集成

Cilium 提供网络和受支持的网络策略；Istio 管理其配置的代理和网格行为。集成不会自动绕过 Istio sidecar、消除其 mTLS 成本、统一所有追踪，也不保证请求更快。

```text
Configuration: istiod --> Istio Envoy proxies
Request: app --> source sidecar --> Cilium/network --> destination sidecar --> app
```

### 保留 Istio 的流量拦截

当前 Cilium 集成指南提供 kube-proxy 共存方式，以及需谨慎配置的完全替代方式。共存配置片段如下：

**`istio-cilium-values.yaml`**

```yaml
kubeProxyReplacement: false
socketLB:
  hostNamespaceOnly: true
cni:
  exclusive: false
```

对于有意预先准备的完全替代配置，`kubeProxyReplacement: true` 还要求 API 端点可达并满足替代模式前提。保持 `socketLB.hostNamespaceOnly: true`，避免 Pod socket 转换绕过 Istio 拦截；共享节点 CNI 配置时保持 `cni.exclusive: false`。

Istio sidecar 重定向可以使用 init container 或 Istio CNI 节点 agent；ambient 使用其对应的节点/CNI 路径。请遵循[维护中的 Istio 安装指南](../../service-mesh/istio/01-installation.md)，并选定一种模式。Kubernetes API server 必须能够访问 Istio admission webhook。托管控制平面/overlay 网络可能需要文档所述的路由或 host-network 方案；不要对所有 overlay 集群一概建议 `istiod hostNetwork: true`。

### 保留 mTLS 并明确 L7 职责

不要对经过 Istio 加密的工作负载流量应用明文 Cilium HTTP 检查。此示例保留 Istio mTLS 和 L7 路由，并使用 Cilium **仅执行 L3/L4** 策略。为了让旧的组合式 L7 示例通过而禁用 mTLS，会改变安全设计。

以下是用于已准备好的 `istio-cilium-demo` 命名空间的 **sidecar 模式**配置，其中包含 `productpage` 和 `reviews` 工作负载、端口 9080 上的 reviews Service，以及标签为 `version: v1`/`v2` 的 reviews Pod。这不是完整的 Bookinfo 部署。

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

DestinationRule 定义了 VirtualService 所引用的 subset。`end-user: jason` 标头用于选择演示路由，不代表经过身份验证的身份。请验证 sidecar 注入成功、实际端点标签、subset 就绪状态和网格遥测。

不要将 9080 Cilium 规则当作 ambient 策略配方复用：ambient HBONE 使用 15008 端口上的加密隧道，并会改变可见流量/身份边界。此拓扑应采用相应 Istio 策略和特定平台的 Cilium 网络防护。

## 负载均衡架构

Cilium 的 Service map、backend map、reverse-NAT 状态和连接跟踪支持不同的转发阶段。L7 Envoy 负载均衡属于另一个组件；不要把它的算法列表与 BPF Service 数据路径混为一谈。

### BPF 转发模式与算法

| 设置/机制 | 含义与限制 |
|---|---|
| `loadBalancer.mode: snat` | 默认转发模式；适用的外部 Service 路径使用源地址转换/反向状态，而不是直接返回路径 |
| `dsr` | 远端后端响应可绕过入口负载均衡节点。网络必须允许该返回路径；它无法恢复已被上游代理转换的客户端 IP |
| `hybrid` | TCP 使用 DSR，UDP 使用 SNAT。这是有效的负载均衡行为，与无效的 tunnel/auto-direct-routing 组合不同 |
| 基于 Annotation 的转发 | 每个 Service 可选择启用的受支持行为；转发 Annotation 在创建时确定，修改可能破坏连接 |
| `loadBalancer.algorithm: random` | 默认 BPF 后端选择算法 |
| `maglev` | 对受支持的外部南北向路径执行一致性选择，包括受支持的 XDP 加速；普通 socket-LB 东西向连接不使用 Maglev |
| `sessionAffinity: ClientIP` | 独立的 Kubernetes Service 亲和性。对于外部流量，键为源 IP；对于适用的集群内 socket-LB 流量，则为客户端网络命名空间 cookie |

Maglev 不保证移除后端后会话仍能存活。各节点需要一致的后端状态、表大小和种子。默认表大小是 16381；下面使用的 65521 是允许的取值，不是通用建议。较大的表会占用更多内存。亲和性过期和连接状态与哈希是不同机制。

DSR 分派可以使用 native-routing IP 选项、文档所述 native/Geneve overlay 配置中的 Geneve，或仅限 native 的 IPIP/IP6IP6 路径。VXLAN overlay 不能与 Geneve DSR 分派互换。IPIP 有自己的端口/转换限制；选择前应核对版本指南。

XDP 加速需要受支持的设备/驱动。`native` 要求所选设备支持该模式；`best-effort` 会在受支持的设备上启用。仅写入旧的 `enable-xdp-acceleration` 键不会启用该功能，而且较早的 XDP 转发可能不会出现在 tcpdump 较晚的抓取点。

### Cilium 与 kube-proxy

| 方面 | 正确比较 |
|---|---|
| Linux Service 实现 | Cilium 使用 BPF 挂钩/map；kube-proxy 有 iptables 和 nftables 模式，且 IPVS 自 Kubernetes 1.35 起已弃用 |
| 平台 | 适用 Cilium 声明的 Linux/内核要求；Windows kernelspace kube-proxy 是另一种实现 |
| 连接状态 | Cilium BPF 连接/NAT 状态不同于 Linux netfilter conntrack；“可选与始终启用”的说法过于宽泛 |
| L7 | Cilium 集成受支持的代理；kube-proxy 的 Service 转发不是 HTTP 策略引擎 |
| 性能 | 应在相同工作负载和配置下测量；产品名称本身不能说明固定排名 |

不要因为底层 Linux IPVS 子系统具备 direct-routing 能力，就推断 kube-proxy 已配置 DSR。

## 已准备的 DSR/Maglev 实验

此配置用于全新且已准备好的、无 kube-proxy 的 **IPv4 Geneve overlay** 测试集群。它不会迁移现有 CNI、删除 kube-proxy，也不会配置云端的 anti-spoofing/路由控制。请使用不冲突的 Pod CIDR 并验证外部返回路径。

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

提供真实 API endpoint 和一个按集群持久保存的 Maglev 种子。种子是 12 个随机字节的 base64 编码；只生成一次，将其与集群 values 一并保存并重复使用，不要在每次升级时重新生成。

```bash
: "${API_SERVER_HOST:?Set the reachable real API server host, not its ClusterIP}"
: "${API_SERVER_PORT:?Set the actual API server port}"
: "${MAGLEV_SEED:?Set the persisted base64 encoding of 12 random bytes}"
helm repo add cilium https://helm.cilium.io/
helm repo update cilium
helm install cilium cilium/cilium --version 1.20.3 --namespace kube-system \
  --values lb-values.yaml \
  --set-string k8sServiceHost="$API_SERVER_HOST" \
  --set k8sServicePort="$API_SERVER_PORT" \
  --set-string maglev.hashSeed="$MAGLEV_SEED"
cilium status --wait
```

在所选集群中使用本指南创建的命名空间；如果换用了另一个一次性集群，请先在那里重复创建/标记命名空间的步骤。HTTP 策略应用与此外部 LB 后端使用不同标签，因此之前仅针对客户端的 HTTP 规则不会意外阻止此实验。

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

使用一个可达的入口节点，该节点必须与后端节点**不同**；并使用一个不受 Cilium 集群内 socket LB 影响的外部客户端。从该客户端使用实际值请求 `http://ENTRY_NODE_IP:NODEPORT/`。Pod 到 ClusterIP 的 curl 既不能证明外部 DSR，也不能证明 Maglev 行为。请核实请求/响应路径和后端/连接状态；不要仅凭 HTTP 请求成功就推断这些行为。

## Masquerading

Pod 出站 masquerading 会在所配置的外部路径需要时改变源地址。它不是加密或防火墙，也不同于 Service DNAT 和 DSR 转发。

以下片段仅在网络确实支持这些 Pod 源地址/返回路由时，才会将示例 `10.0.0.0/8` 目标范围排除在源地址 masquerading 之外：

**`masquerade-values.yaml`**

```yaml
bpf:
  masquerade: true
enableIPv4Masquerade: true
enableIPv6Masquerade: false
ipv4NativeRoutingCIDR: 10.0.0.0/8
```

`ipv4NativeRoutingCIDR` 表示假定可路由的范围，并指定相应的 masquerading 排除项。它不会安装路由，也不会将整个数据路径切换为 native routing。没有可用返回路由的宽泛排除项可能导致连通性故障。

- 此版本中的 BPF masquerading 依赖 BPF NodePort 功能，并且仅作用于加载 BPF 程序的设备。请检查所选设备；必要时使用文档所述的 `devices` 配置。
- iptables 实现使用其文档所述的 `egressMasqueradeInterfaces` 行为。不要将此字段或已移除的通用 `masquerade-interfaces`/`masquerade-all` 示例视为通用 BPF 控制项。
- IPv6 BPF masquerading 在文档中标记为 beta。任一实现都不会消除 Cilium 对平台/内核的要求，而且最终都在内核中处理流量。
- 节点地址例外、ip-masq-agent 排除项以及后续云/NAT Gateway 都会影响观察到的源地址。请使用受控的观察端以及节点侧状态/抓取；能够访问任意公共站点不能证明采用了某一种 NAT 实现。

在相关 agent 上运行：

```bash
kubectl -n kube-system get pods -l k8s-app=cilium -o wide
export CILIUM_POD=cilium-REPLACE-WITH-AGENT-ON-TARGET-NODE
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg status --verbose
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg bpf nat list
```

## 分片处理与 MTU

已发布的分片跟踪器使用有界 LRU map 存储数据报身份以及 L4 源/目标端口。它可以为缺少 L4 标头的后续分片恢复端口上下文；它**不是 BPF 负载重组引擎**，也不保证抵御分片攻击。

文档所述功能包括 IPv4 和 IPv6 跟踪，通过对应 flag 默认启用，并标记为 beta。有效的 IPv4 flag 仍是 `enable-ipv4-fragment-tracking`。`bpf-fragments-map-max` 控制已跟踪数据报 map 的容量；旧的 `fragment-tracking-timeout` 和 `max-fragments-per-flow` 设置不属于已发布配置约定。

通过 Chart 的 extra configuration map 配置示例如下：

**`fragment-values.yaml`**

```yaml
extraConfig:
  enable-ipv4-fragment-tracking: 'true'
  bpf-fragments-map-max: '8192'
```

8192 是容量示例，不是每条流允许的最大分片数。诊断容量时，应查看 `cilium_ipv4_frag_datagrams` / `cilium_ipv6_frag_datagrams` 及其压力情况；压力指标不代表重组成功，也不是攻击防护计数器。

应优先采用正确的数据包大小和正常工作的路径 MTU 发现机制。PMTUD 依赖相关错误信号和网络行为；它不能保证在所有情况下自动选择最佳大小。Cilium 的 `MTU` 是**底层网络覆盖值**。如[网络指南](03-networking.md)所述，IPv4 underlay 上普通 VXLAN 的开销为 50 字节，IPv6 下为 70 字节；在 1500 字节路径上盲目将基础 MTU 设为 1450，可能导致开销被扣除两次。

## 可观测性与故障排除

请检查正确的节点、实际 Envoy 部署模式、目标策略、已生效的 endpoint 状态和新产生的流量。使用 `cilium-dbg` 执行 agent 本地操作，使用独立 CLI 执行集群级操作。已移除的 `policy trace` 命令和强制重新生成 endpoint 都不是此诊断的起点。

在另一个终端中保持已启用的 Hubble Relay 端口转发运行，然后观察相关流量：

```bash
cilium hubble port-forward
```

```bash
hubble observe --namespace cilium-l2l7-demo --protocol http --last 20
hubble observe --namespace cilium-l2l7-demo --verdict DROPPED --last 20
```

HTTP 策略拒绝可能显示为 HTTP 403，而不是数据包 DROPPED verdict。单独出现超时也可能表示就绪、DNS、路由、TLS 或观测问题。应关联多个层面的证据，不要把每个错误都解读为策略已成功。

## 验证限制与来源

这些示例根据版本源代码/schema 进行了核对，并使用有限的本地 fixture；它们不是经过生产测试的平台，也不是实时集群基准测试。镜像执行、webhook 可达性、mTLS 流量、DSR 返回路径、NAT 行为和分片仍需在准备好的环境中验证。只清理本次运行中带标签的应用资源；不要把移除集群 CNI 作为实验清理的一部分。

- [Cilium kube-proxy 替代/DSR/Maglev](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/network/kubernetes/kubeproxy-free.rst)、[masquerading](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/network/concepts/masquerading.rst)、[分片处理](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/network/concepts/fragmentation.rst)、[分片 map 实现](https://github.com/cilium/cilium/blob/v1.20.3/pkg/maps/fragmap/fragmap.go)
- [L2 Announcements](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/network/l2-announcements.rst)、[多播](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/network/multicast.rst)、[HTTP 规则转换器](https://github.com/cilium/cilium/blob/v1.20.3/pkg/envoy/policy/envoy_l7_rules_translator.go)、[Envoy Chart 默认值](https://github.com/cilium/cilium/blob/v1.20.3/install/kubernetes/cilium/templates/_helpers.tpl)
- [Cilium/Istio 集成](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/network/servicemesh/istio.rst)、[Istio CNI/init-container 模式](https://istio.io/latest/docs/setup/additional-setup/cni/)、[Webhook 要求](https://istio.io/latest/docs/ops/configuration/mesh/webhook/)、[Istio 1.31 schema](https://github.com/istio/istio/blob/1.31.0/manifests/charts/base/files/crd-all.gen.yaml)
- [Kubernetes Service 代理模式/亲和性](https://kubernetes.io/docs/reference/networking/virtual-ips/)、[Cilium 1.20.3 values](https://github.com/cilium/cilium/blob/v1.20.3/install/kubernetes/cilium/values.yaml)

[返回主页](README.md)

## 测验

[复习 L2–L7 和负载均衡相关问题](../../quizzes/networking/cilium/05-l2-l7-networking-quiz.md)。
