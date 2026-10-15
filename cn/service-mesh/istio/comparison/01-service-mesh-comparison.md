# Service Mesh 解决方案比较

> **最后审核**: September 11, 2026
> **API/工件检查**: Istio 1.31.0; Linkerd edge-26.9.1; Kong Mesh/Kuma 2.14.4; Consul/chart 2.0.4

工件版本标识用于检查示例的来源。它们**不是共享 Kubernetes 兼容性矩阵**，也不能证明存在已部署的生产系统。下文保留原始 Istio 1.24/Linkerd 2.15/Kong Mesh 2.8/Consul 1.19 性能数据及其历史性、未验证状态。

## 目录

1. [架构](#architecture)
2. [性能证据](#performance-evidence)
3. [流量管理](#traffic-management)
4. [安全](#security)
5. [可观测性](#observability)
6. [多集群](#multicluster)
7. [安装与运维](#installation-and-operations)
8. [成本与许可](#cost-and-licensing)
9. [选型与验证](#selection-and-validation)

## 架构

Service Mesh 将选定的通信功能移入基础设施组件。流量拦截可以对应用代码透明，但协议选择、流量归属、工作负载身份和策略仍需要配置。分布式追踪还需要上下文传播/插桩。Mesh 不会让任意应用重试变得安全。

![概念性 sidecar 模式：控制平面配置服务之间的代理。周围文本定义所需的策略和遥测配置。](../../../.gitbook/assets/en-service-mesh-istio-comparison-01-service-mesh-comparison-0.png)

[查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-comparison-01-service-mesh-comparison-0.html)

该图展示已配置的 sidecar 部署；并不表示所有功能默认启用，或 ambient/Cilium 使用相同的每 Pod 拓扑。

### Istio

![Istiod 读取配置并向 Envoy sidecar 提供 xDS 配置，后者在已加入的工作负载之间承载流量。](../../../.gitbook/assets/en-service-mesh-istio-comparison-01-service-mesh-comparison-2.png)

[查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-comparison-01-service-mesh-comparison-2.html)

Istiod 合并了历史上与 Pilot、Citadel 和 Galley 相关的配置/发现及身份管理功能；这些名称并不代表另外三个当前部署。Sidecar 数据平面使用 Envoy。Ambient 对 L4 使用每节点 ztunnel，并对支持的 L7 处理使用单独的 Envoy waypoint。Ingress/egress gateway 实现显式选择的边界路径。

支持 Kubernetes 和有文档说明的 VM 集成，但存在网络/信任前提条件。Ambient core GA 不代表与 sidecar 功能对等：waypoint 策略附加、EnvoyFilter 支持和多集群成熟度不同。在估算资源或复杂度前，选择模式及所需 API 行为。

### Linkerd

![Linkerd Destination、Identity 和 Proxy Injector 组件为 Rust linkerd2-proxy sidecar 提供发现、工作负载证书和注入。](../../../.gitbook/assets/en-service-mesh-istio-comparison-01-service-mesh-comparison-3.png)

[查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-comparison-01-service-mesh-comparison-3.html)

Linkerd 使用专用 Rust 代理以及 Kubernetes 资源、注解和 CRD。当前功能包括 Gateway API 请求路由、超时/重试、按路由授权和本地限流。称它为仅注解或“只有基础功能”的 Mesh 并不准确。

使用 ExternalWorkload、外部机器上的代理、兼容的 SPIFFE/SPIRE 身份、DNS 和网络访问，已有文档说明非 Kubernetes Mesh 扩展。这并非“没有 VM 支持”，注册外部 IP 也不会自动安装或认证代理。

### Kong Mesh 和 Kuma

![Kong Mesh 控制平面配置 Kubernetes 和 VM 工作负载上的 Envoy 数据平面代理。多区模型使用全局控制平面。](../../../.gitbook/assets/en-service-mesh-istio-comparison-01-service-mesh-comparison-4.png)

[查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-comparison-01-service-mesh-comparison-4.html)

Kong Mesh 构建于 Kuma 之上。Kubernetes 模式使用 Kubernetes 资源/存储；Universal 模式支持 VM/裸金属环境并使用所配置的数据库。Kong 提供自托管和托管全局控制平面选项；版本功能和支持条款必须与上游 Kuma 分开检查。

在多区部署中，全局和区域控制平面通过 KDS 交换资源，每个区域则向其本地代理提供 xDS。跨区数据流量使用目标区域 ingress，以及配置时的本地区域 egress。全局控制平面不是自动的 Prometheus/追踪聚合后端。

Service 的发现本身并不指定 80% 本地/20% 远程的比例。旧端点加权与当前 MeshLoadBalancingStrategy locality 设置的默认值不同。应检查选定策略、可用端点和跨区/故障转移设置，而非把图中的权重当作固有行为。

适当时使用 MeshHTTPRoute、MeshTrafficPermission、MeshRetry、MeshTimeout、MeshMetric、MeshTrace 和 MeshAccessLog 等当前策略。TrafficRoute 和 TrafficPermission 是旧版/已弃用接口，不一定是在所检查版本中已移除的 API。一起迁移依赖策略；不要将旧 TrafficPermission 与 MeshTrafficPermission 混用。单个策略类型并不决定“全局”还是“仅区域”归属或传播。

全局控制平面故障时，现有数据流量可继续运行，但策略和远程 Service 变更会停止传播。区域控制平面故障会阻止新代理、配置更新和证书刷新。保留配置不等于无限期可用保证。应在实际故障条件下验证注册、更新、排空和到期。

### Consul Service Mesh

Consul 提供服务发现、配置和身份功能，并一等支持 Envoy。当前 Kubernetes 集成通常使用 consul-dataplane 管理 sidecar；旧的每节点 client-agent 图景并非唯一或默认 Kubernetes 架构。

官方代理概述还说明一个用于开发/测试的内置 L4 代理，并建议不要用于生产。它不应被描述为等同于 Envoy 的生产 L7 功能集，也不应在没有发布证据的情况下错误地称为已移除。Consul 除 Kubernetes 外还支持有文档说明的 VM 和其他运行时集成。

### 同一决策中的 Cilium

Cilium 将 eBPF 网络数据路径与 Envoy 等代理组合，用于 L7 解析/策略。它并非完全无代理的 L7 网络。Cilium 1.20.1 的带外双向认证为 Beta，使用带外握手；WireGuard/IPsec 加密是独立要求。有关实际功能和 Cluster Mesh 限制，请参阅 [Cilium mesh 指南](../../cilium-service-mesh/README.md)。

Cilium 1.20.1 还提供单独的 [ztunnel 透明加密 beta](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/security/network/encryption-ztunnel.rst)，通过 `encryption.type: ztunnel` 选择。它通过 namespace 加入提供 TCP 工作负载 mTLS；两个端点都必须加入。它不支持 ClusterMesh 和 host-networked Pod，已发布指南警告普通 L4 策略在此路径上不生效，除非目标为 HBONE 端口 15008。这是具有自身 CA/bootstrap 要求的独立部署选择。

## 性能证据

### 原始数据：历史且未验证

此前文字描述了一个 **三节点 EKS 1.28、m5.xlarge、100-Service、1,000-RPS** 测试，并列出 Istio 1.24、Linkerd 2.15、Kong Mesh 2.8 和 Consul 1.19。它未提供原始样本、可复现实验框架、精确 patch/proxy 版本或来源基准。这些数字不能建立当前产品排名：

| 原始条目 | p50 | p95 | p99 | CPU 声称 | 内存声称 |
|---|---:|---:|---:|---:|---:|
| 基线 |0.1 ms|0.2 ms|0.3 ms|—|—|
| Linkerd |+0.5 ms|+0.8 ms|+1.2 ms|+3–8%|+20–50 MB|
| Istio |+1.0 ms|+2.5 ms|+3.5 ms|+5–15%|+50–150 MB|
| Kong Mesh |+0.8 ms|+2.0 ms|+3.0 ms|+5–12%|+40–120 MB|
| Consul |+1.0 ms|+2.5 ms|+3.5 ms|+6–14%|+50–140 MB|

原始控制平面估算为：Istio 0.5–1 CPU/1–2 GB、Linkerd 0.1–0.3 CPU/200–500 MB、Kong 0.2–0.5 CPU/500 MB–1 GB、Consul 0.5–1 CPU/1–2 GB。每代理 CPU 估算从 Linkerd 的 20–100m 到 Istio/Consul 的 100–500m。这些是未经验证的输入，不是默认值、测量结果或容量建议。计数 Linkerd 的不同组件也不等同于计数某一组件的副本。

已移除的吞吐量图声称 Linkerd 保留基线吞吐量的 95–98%、Kong 90–95%、Istio/Consul 85–92%，但没有支持数据。它不能证明“Linkerd 最快”、固定资源百分比或最小集群规模。

### 可复现的比较

将实际产品/proxy/Kubernetes 版本、硬件和完整配置附于结果。匹配流量协议/payload/concurrency、TLS/认证、策略、遥测和资源限制。报告绝对基线和 Mesh 延迟分布、在定义的错误/SLO 限制下的吞吐量、每组件 CPU/内存，以及重复运行的变异性。

比较等效的 HA 和故障行为，包括 rollout、排空、连接复用、缺失遥测和控制平面丢失。将原始错误与重试后客户端可见结果分开测量。不要在未重新运行并保留实验的情况下把历史版本标签移到未来。

## 流量管理

| 能力 | 应具体比较的内容 |
|---|---|
| 加权/header 路由 | Istio VirtualService、Linkerd HTTPRoute、Kong MeshHTTPRoute、Consul router/splitter/resolver 行为 |
| Blue/Green 或 canary | 路由只是其中一部分；rollout controller 或部署工作流必须管理版本、分析和回滚 |
| 重试/超时 | 支持的请求/协议范围、默认策略、预算和应用幂等性 |
| 限流 | 本地与共享计数器、身份、故障策略和实际副本范围 |
| 故障/mirroring | 支持的 API/filter 和观察到的生成配置；镜像写入可能有副作用 |

Linkerd 确实通过 HTTPLocalRateLimitPolicy 支持本地限流，包括按身份限制和按请求属性的动态路由。本地每代理限制不是全局 Service 配额。Consul 和 Kong 功能可能取决于所选版本/API；粗略的“基础/企业/无”表格并不足够。

### 独立只读路由示例

请把这些作为**相应 Mesh 中的替代方案**，而非同一工作负载上的重叠 controller。它们假设 `mesh-demo` 中存在 `reviews` Pod、实际版本标签、9080 上的 HTTP listener 及匹配的 Mesh 加入。此 Service 形状提供显式端口；它不创建应用：

```yaml
apiVersion: v1
kind: Service
metadata:
  name: reviews
  namespace: mesh-demo
spec:
  selector:
    app: reviews
  ports:
  - name: http
    port: 9080
    targetPort: 9080
    appProtocol: http
---
apiVersion: v1
kind: Service
metadata:
  name: reviews-v1
  namespace: mesh-demo
spec:
  selector:
    app: reviews
    version: v1
  ports:
  - name: http
    port: 9080
    targetPort: 9080
    appProtocol: http
---
apiVersion: v1
kind: Service
metadata:
  name: reviews-v2
  namespace: mesh-demo
spec:
  selector:
    app: reviews
    version: v2
  ports:
  - name: http
    port: 9080
    targetPort: 9080
    appProtocol: http
```

以下比较针对只读 review 请求。路由写入前，应单独审计继承的 Mesh/client 重试和幂等性。路由 header 是客户端控制的输入，不是认证。

#### Istio

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: reviews
  namespace: mesh-demo
spec:
  hosts:
  - reviews
  http:
  - name: canary-header
    match:
    - headers:
        x-release:
          exact: canary
    route:
    - destination:
        host: reviews
        subset: v2
        port:
          number: 9080
      weight: 100
    retries:
      attempts: 0
  - name: weighted
    route:
    - destination:
        host: reviews
        subset: v1
        port:
          number: 9080
      weight: 90
    - destination:
        host: reviews
        subset: v2
        port:
          number: 9080
      weight: 10
    retries:
      attempts: 0
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews
  namespace: mesh-demo
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

两个路由都显式禁用 Mesh 重试。subset 标签必须匹配真实端点；流量权重不会创建或扩缩版本。若需要 Gateway 暴露，需其自身的 host/TLS 绑定。

#### Linkerd

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: reviews-outbound
  namespace: mesh-demo
spec:
  parentRefs:
  - group: ''
    kind: Service
    name: reviews
    port: 9080
  rules:
  - matches:
    - headers:
      - name: x-release
        type: Exact
        value: canary
    backendRefs:
    - group: ''
      kind: Service
      name: reviews-v2
      port: 9080
      weight: 100
  - backendRefs:
    - group: ''
      kind: Service
      name: reviews-v1
      port: 9080
      weight: 90
    - group: ''
      kind: Service
      name: reviews-v2
      port: 9080
      weight: 10
```

此 Gateway API producer 路由附加到 Service 并配置已加入 Mesh 的**客户端**。核心 Service group 是空字符串。它不需要已弃用的 SMI TrafficSplit 扩展。同一 Service 的现有 ServiceProfiles 优先于 outbound HTTPRoutes；应有意解决该归属。依赖它之前检查 Accepted/ResolvedRefs 和实际路由。

#### Kong Mesh

```yaml
apiVersion: kuma.io/v1alpha1
kind: MeshHTTPRoute
metadata:
  name: reviews-weighted
  namespace: mesh-demo
  labels:
    kuma.io/mesh: default
spec:
  targetRef:
    kind: Dataplane
    labels:
      app: productpage
  to:
  - targetRef:
      kind: MeshService
      name: reviews
      sectionName: http
    rules:
    - matches:
      - path:
          type: PathPrefix
          value: /
      default:
        backendRefs:
        - kind: MeshService
          name: reviews-v1
          port: 9080
          weight: 90
        - kind: MeshService
          name: reviews-v2
          port: 9080
          weight: 10
```

此处 `reviews`、`reviews-v1` 和 `reviews-v2` 表示**实际 MeshService 资源名称**，并非假设每个生成名称都等于 Kubernetes Service 名称。在已安装环境中解析其名称、namespace/port section 和后端就绪情况。所选调用方 Dataplane 必须带有 app 标签，HTTP Service 端口必须声明受支持协议。该示例更改权重，而非 locality 优先级或容量。

#### Consul

```yaml
apiVersion: consul.hashicorp.com/v1alpha1
kind: ServiceDefaults
metadata:
  name: reviews
  namespace: mesh-demo
spec:
  protocol: http
---
apiVersion: consul.hashicorp.com/v1alpha1
kind: ServiceResolver
metadata:
  name: reviews
  namespace: mesh-demo
spec:
  subsets:
    v1:
      filter: Service.Meta.version == v1
      onlyPassing: true
    v2:
      filter: Service.Meta.version == v2
      onlyPassing: true
---
apiVersion: consul.hashicorp.com/v1alpha1
kind: ServiceSplitter
metadata:
  name: reviews
  namespace: mesh-demo
spec:
  splits:
  - weight: 90
    service: reviews
    serviceSubset: v1
  - weight: 10
    service: reviews
    serviceSubset: v2
```

这些是 Consul config entry 的 Kubernetes CRD 形式，要求已配置 Consul controller/RBAC。Consul catalog 中的 Service metadata 必须实际包含 `version=v1/v2`；单独的 Kubernetes Pod 标签不能证明 catalog metadata。HTTP 协议和 resolver subset 完成拆分定义。审查 Kubernetes 到 Consul 的 namespace/Service 映射和健康端点，而非给同一 config entry 应用多个 owner。


## 安全

加密、peer 身份、调用方授权和应用认证是独立控制。已加入代理之间的自动 mTLS 不表示所有未加入 Mesh 的流量都会被拒绝，也不表示每个调用方都已授权。

### Istio：入站 mTLS 和请求授权

```yaml
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: reviews-strict
  namespace: mesh-demo
spec:
  selector:
    matchLabels:
      app: reviews
  mtls:
    mode: STRICT
---
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: reviews-read
  namespace: mesh-demo
spec:
  selector:
    matchLabels:
      app: reviews
  action: ALLOW
  rules:
  - from:
    - source:
        principals:
        - cluster.local/ns/mesh-demo/sa/productpage
    to:
    - operation:
        methods:
        - GET
        paths:
        - /reviews/*
```

此 sidecar 示例要求实际的 productpage ServiceAccount 身份和 reviews 工作负载。Auto mTLS 可选择适当的出站传输；不需要笼统的 `*.local` ISTIO_MUTUAL DestinationRule，且它可能破坏不相关/plaintext 目标。STRICT 是入站强制执行，而 ALLOW 策略控制所示身份/method/path。

AuthorizationPolicy 字符串匹配为精确、前缀、后缀或存在匹配；`*Mobile*` 不是通用的 substring-regex 匹配。User-Agent 也不是工作负载身份。Ambient L7 附加需要支持的 waypoint 策略模型，而非原样复制 sidecar selector。

### Linkerd：显式入站策略

```yaml
apiVersion: policy.linkerd.io/v1beta3
kind: Server
metadata:
  name: reviews-http
  namespace: mesh-demo
spec:
  podSelector:
    matchLabels:
      app: reviews
  port: 9080
  proxyProtocol: HTTP/1
  accessPolicy: deny
---
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: reviews-read
  namespace: mesh-demo
spec:
  parentRefs:
  - group: policy.linkerd.io
    kind: Server
    name: reviews-http
  rules:
  - matches:
    - method: GET
      path:
        type: PathPrefix
        value: /reviews/
---
apiVersion: policy.linkerd.io/v1alpha1
kind: AuthorizationPolicy
metadata:
  name: reviews-read
  namespace: mesh-demo
spec:
  targetRef:
    group: gateway.networking.k8s.io
    kind: HTTPRoute
    name: reviews-read
  requiredAuthenticationRefs:
  - kind: ServiceAccount
    name: productpage
```

Server 选择实际声明的 Pod 端口，此处默认拒绝。入站 HTTPRoute 选择 `/reviews/` 下的 GET 请求；AuthorizationPolicy 要求 productpage ServiceAccount。目标 API group 是显式的：省略 group 表示核心 group，而非推断的 Linkerd Server。缺少/错误引用不会创建授权许可。

所检查的 edge CRD 提供 Server v1beta3 及包括 v1beta1 在内的旧版本；并未声称旧 API 已移除。使用所选工件支持的 API 版本。namespace/Pod 默认 `all-unauthenticated` 策略不同于已加入 peer 之间的自动加密，也不同于此显式 Server 策略。

### Kong Mesh：以审慎权限启用 mTLS

基础安装不会自动加密所有 Service 流量。在现有工作负载上启用 mTLS 前规划权限，因为没有匹配权限的通信可能被阻止。最小 Mesh 配置为：

```yaml
apiVersion: kuma.io/v1alpha1
kind: Mesh
metadata:
  name: default
spec:
  mtls:
    enabledBackend: ca-1
    backends:
    - name: ca-1
      type: builtin
```

受限的 Service 级示例为：

```yaml
apiVersion: kuma.io/v1alpha1
kind: MeshTrafficPermission
metadata:
  name: productpage-to-reviews
  namespace: mesh-demo
  labels:
    kuma.io/mesh: default
spec:
  targetRef:
    kind: Dataplane
    labels:
      app: reviews
  from:
  - targetRef:
      kind: MeshSubset
      tags:
        kuma.io/service: productpage
    default:
      action: Allow
```

将 `productpage` 替换为实际源 `kuma.io/service` 身份标签，并验证目标 Dataplane 标签/namespace。它不保证等于裸 Kubernetes Service 名称。此权限是 Service 级授权，不等同于上述 Istio/Linkerd GET/path 规则。不要与旧 TrafficPermission 混用。在变更生产强制执行前，所需传输、身份和策略资源必须就绪。

### Consul：L7 Intentions

```yaml
apiVersion: consul.hashicorp.com/v1alpha1
kind: ServiceIntentions
metadata:
  name: reviews
  namespace: mesh-demo
spec:
  destination:
    name: reviews
  sources:
  - name: productpage
    permissions:
    - action: allow
      http:
        methods:
        - GET
        pathPrefix: /reviews/
```

Consul Service 身份和 HTTP 协议配置必须与 catalog 和实际代理相匹配。L7 权限说明“Consul 只有基础 Service 级授权”并不准确。不要把源的 L4 action 与其 L7 permissions 当作两者独立应用。审查其他 intention/default policy、namespace/partition 和 controller 映射。

Mesh config entry 的 TLS 最低版本会更改 TLS 设置；它不会加入应用、安装代理或创建完整的 CA/ACL 配置。Envoy 扩展和 escape-hatch API 还要求实际 Consul 发布版的权限；2.0.4 版本加强了 code-executing extension 的 mesh:write 要求。

## 可观测性

Metric 数量不是有意义的固定排名：启用的 stats、维度、策略、抓取和应用插桩都会影响信号和开销。EnvoyFilter 不是无限制的遥测扩展 API，所有 tracing backend 也不能在没有兼容协议/exporter 的情况下互换。

| Mesh | 配置并验证 |
|---|---|
| Istio | Telemetry API、实际 proxy/control-plane metric、access-log 格式、tracing provider 和 backend；可选 Kiali/Grafana 集成 |
| Linkerd | Proxy golden/per-route metric、所选 viz 或外部监控设置，以及已配置 proxy/application tracing |
| Kong Mesh | 使用支持的 backend 的 MeshMetric、MeshTrace 和 MeshAccessLog；GUI/control-plane 可用性和访问需单独配置 |
| Consul | Proxy/agent metric、已配置 tracing，以及具有真实 endpoint/authentication 设置的 UI metric provider |

对于端到端 trace，应跨应用调用传播上下文、按需启动/采样 trace，并配置 collector/backend 交付。Linkerd 明确记录这些要求；单独 proxy span 不是完整应用 trace。OpenTelemetry collector 可以桥接支持的协议，但其存在不能证明每种产品/backend 组合都可用。

相关组件已安装并授权时，有用的检查命令包括：

```bash
istioctl dashboard kiali -n istio-system
linkerd viz check
linkerd viz stat deploy -n mesh-demo
linkerd viz dashboard
```

这些命令不会安装 dashboard 或 backend。Kiali 的当前配置和兼容性必须单独检查；旧 accessible_namespaces 示例及旧 Istio bundled-addon 值不是当前安装方案。有关维护中的配置和验证限制，请参阅 [可观测性指南](../observability/README.md)。Kong GUI 不会因空 Mesh metrics backend 而启用，Consul UI metrics URL 必须能从实际 server 环境解析。

## 多集群

| 系统 | 发现/数据路径 | 重要边界 |
|---|---|---|
| Istio | 每个 primary 读取获授权的 Kubernetes API；跨网络流量使用已配置 east-west gateway | Remote secret 不会复制 CRD 或建立网络/信任。Sidecar 和 ambient 支持不同拓扑。 |
| Linkerd | 本地 mirrored Service 描述远程 Service；hierarchical 模式使用**目标** gateway；flat 模式支持直接 Pod 路径 | mirror 位于源集群。并非固有需要 source gateway。Federated Service 使用 flat 模型且不支持 headless member。 |
| Kong Mesh | KDS 交换 zone/Service 资源；目标 zone ingress 和可选源 zone egress 承载跨 zone 流量 | locality/failover 行为来自适用策略和可用端点；不存在固有 80/20 划分或无条件 failover。 |
| Consul | 具有发现和 mesh-gateway 路径的受支持 cluster peering 或 WAN-federation 模型 | 选择实际拓扑并配置 trust、导出 Service、授权和路由；名称本身不会加入集群。 |

![Consul WAN-federated datacenter 模式示意图，包含 Consul server 和 mesh gateway。Cluster peering 是单独配置模型。](../../../.gitbook/assets/en-service-mesh-istio-comparison-01-service-mesh-comparison-16.png)

[查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-comparison-01-service-mesh-comparison-16.html)

原始“Linkerd 最多约十个集群”和通用“数十个”限制没有 quota/load-test 来源。容量取决于实际 control/data-plane 拓扑、Service/endpoint 数量、更新率和资源。自动 Service 发现不是自动策略复制或应用/数据灾难恢复。

在两个方向检查 remote API/gateway 可达性、证书 trust、DNS、namespace/Service 身份、导出 Service 和故障行为。应优先使用[维护中的 Istio 多集群指南](../advanced/02-multi-cluster.md)，而不是原先带 meshID 标签和一个 secret 的两条安装命令：这些命令不是完整 Mesh 设置。

## 安装与运维

### 版本是独立输入

| 检查的来源/工件 | 兼容性证据和限制 |
|---|---|
| Istio 1.31.0 | 支持 Kubernetes 1.32–1.37；遵循其实际 upgrade/skew 规则和平台要求 |
| Linkerd edge-26.9.1 CLI/CRD | Edge 指导属于该工件。独立发布的 **2.20** 表列出 Kubernetes 1.31–1.35 和 Gateway API 1.2.1–1.5.1；不要把它们当作每个后续 edge/vendor build 的自动边界。 |
| Kong Mesh/chart 2.14.4 | 于 September 3 发布，含 Kuma 2.14.4。已发布 Kubernetes 验证表目前止于 2.13；不会从 chart render 推断 2.14 兼容性认证。支持表另列 2.13 LTS。 |
| Consul/chart 2.0.4 | 分别检查发布的 application 和 Helm 工件。chart 的 Kubernetes minimum 是 metadata，不是完整支持版本矩阵或 upgrade 评估。 |

Gateway API CRD 是 controller 共享的集群范围依赖项。没有检查每个 consumer 前，不要盲目安装 catalog 的最新版本或降级现有 bundle。

### Istio Revision 切换

使用匹配的 CLI 以及从已安装版本起受支持的 upgrade 路径。本文中的历史 1.24 标签不是直接跳到 1.31 的许可。保留审核过的安装值、gateway/CNI 设置和 revision 所有权。

一个说明性的 default-profile 输入可设定 control-plane 资源/HPA 边界：

```yaml
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  profile: default
  components:
    pilot:
      k8s:
        hpaSpec:
          minReplicas: 3
          maxReplicas: 10
        resources:
          requests:
            cpu: 2000m
            memory: 4Gi
```

没有内置 `production` profile。这些 CPU/内存/副本数是容量输入，不是生产容量保证。仅安装另一 revision 不会升级现有 proxy：

```bash
istioctl install -f reviewed-istio.yaml --revision 1-31-0
kubectl label namespace mesh-demo istio-injection-
kubectl label namespace mesh-demo istio.io/rev=1-31-0 --overwrite
: "${DEPLOYMENT:?Set the actual staged Deployment name}"
kubectl rollout restart deployment/"$DEPLOYMENT" -n mesh-demo
kubectl rollout status deployment/"$DEPLOYMENT" -n mesh-demo
```

切换前审查现有 namespace 和 Pod override。旧 injection label 可能优先于 revision 选择。只重启预定的工作负载队列；gateway 和 ambient 组件有自己的升级流程。Canary revision 不保证每次应用 rollout 都零错误。

### Linkerd 安装与升级

先选择明确的 edge 或 vendor 工件及其兼容 Gateway API。当前上游 CLI 工作流为：

```bash
linkerd check --pre
linkerd install --crds > linkerd-crds.yaml
kubectl apply -f linkerd-crds.yaml
linkerd install > linkerd-control-plane.yaml
kubectl apply -f linkerd-control-plane.yaml
linkerd check
```

这是面向实验室的 CLI 流；生产安装指南建议使用 Helm 以获得可重复性和审核过的 identity 设置。为 namespace 添加注解会为新创建的 Pod 启用注入，而不会立即向运行中 Pod 插入 proxy。按所选发布版流程升级 CRD/control plane，然后有意 rollout 工作负载以更新 data-plane proxy；不会隐含自动工作负载 rollout。

### Kong 和 Consul Chart 检查

这些命令获取并 render 精确检查的 chart 供审查；它们不会部署生产系统：

```bash
helm repo add kong-mesh https://kong.github.io/kong-mesh-charts
helm repo add hashicorp https://helm.releases.hashicorp.com
helm repo update kong-mesh hashicorp
helm show values kong-mesh/kong-mesh --version 2.14.4 > kong-values.reference.yaml
helm show values hashicorp/consul --version 2.0.4 > consul-values.reference.yaml
helm template kong-mesh kong-mesh/kong-mesh --version 2.14.4   --namespace kong-mesh-system --include-crds --values reviewed-kong-values.yaml
helm template consul hashicorp/consul --version 2.0.4   --namespace consul --include-crds --values reviewed-consul-values.yaml
```

审核过的 values 文件是环境特定输入，不是此比较提供的文件。遵循各产品安装指南前，确认 Kubernetes 支持、版本/许可、CA/ACL/bootstrap identity、存储、HA、injector/controller 设置及升级说明。成功 Helm render 既不能证明运行时就绪，也不能证明原地升级安全。

### 故障排除

```bash
istioctl proxy-status
istioctl analyze -n mesh-demo
istioctl proxy-config clusters "$POD" -n mesh-demo
linkerd check
linkerd viz stat deploy -n mesh-demo
kubectl get meshhttproutes,meshtrafficpermissions -n mesh-demo
kubectl get servicedefaults,serviceresolvers,servicesplitters -n mesh-demo
```

仅在目标已安装环境中运行产品专用命令。检查实际组件名称和日志，而不是假定每个 Consul sidecar 都有固定的历史 container 名。Tap/debug 日志可能暴露请求信息；限定并恢复临时诊断设置。根据真实工作流衡量团队工作，不要声称每个组织都能在八小时或五分钟内完成安装。


## 成本与许可

### 原始成本输入不是报价

原始 100-Pod/m5.xlarge 表给出 $300 基线及以下每月额外金额：

| 原始产品输入 | Control-plane CPU/内存 | Aggregate proxy CPU/内存 | 原额外每月金额 |
|---|---|---|---:|
| Linkerd |300m / 500 MB|2 vCPU / 5 GB|$50|
| Istio |1 vCPU / 2 GB|10 vCPU / 15 GB|$150|
| Kong Mesh |500m / 1 GB|8 vCPU / 12 GB|$120|
| Consul |1 vCPU / 2 GB|10 vCPU / 14 GB|$145|

没有 Region、节点数、运行时长、购买模型、分配公式或账单数据支持这些价格。资源请求不会自动购买部分 EC2 节点，释放的余量也不一定减少账单。仅将其保留为先前假设输入；不要用来选择最便宜的产品。

先前人员假设是 Istio/Linkerd/Kong/Consul 的初始设置 40/8/20/24 小时、每月运维 20/5/10/12 小时、每月故障排除 15/3/8/10 小时以及季度升级 8/2/4/5 小时。它们不是测量的团队生产率，初始设置也不是重复发生的每月成本。

有意义的成本模型使用实际保留容量、HA 和 autoscaling 限制、load balancer/transfer、存储/遥测、平台费用、支持订阅和观察到的工程工作量。比较相同工作负载、安全和可用性要求，并说明每个单位/费率/日期。仅从有依据的差异和迁移成本计算 ROI。

### 工件和产品许可

| 组件 | 必须保留的区别 |
|---|---|
| Istio | Apache 许可的上游项目；托管/商业发行版有各自条款和成本 |
| Linkerd | Apache 许可的上游项目；上游 edge 工件和 vendor stable 发行版是不同发布/支持选择 |
| Kuma / Kong Mesh | 上游 Kuma 与商业 Kong Mesh 产品不同；验证所选版本和支持合同 |
| Consul | 所检查的 **Consul 2.0.4 application** 许可为 Business Source License 1.1，具有所声明的使用授权和后续 MPL 变更条件，而非简单的当前 MPL-2.0 |

Consul Helm chart 为该工件声明 MPL 许可；它不会覆盖 application binary 的许可。审查精确工件/版本条款。Linkerd HA control-plane 配置并非天然仅限企业功能；必须将付费支持/SLA 和产品功能与上游能力区分。不要从一个 vendor 名称或带美元符号的排名推断支持。

## 选型与验证

| 情况 | 决定选择的问题 |
|---|---|
| 大型部署 | 需要哪些精确的路由/安全 API、endpoint/update 规模和 HA 行为？ |
| 小团队或快速开始 | 团队能运营哪种生命周期和故障排除工作流，包括 identity 和升级？ |
| 资源限制 | 等效策略工作负载实际消耗什么，包括所有 proxy、waypoint、gateway 和遥测？ |
| VM 或旧工作负载 | 有文档说明的 identity/network/runtime 集成是否合适？Istio 和 Linkerd 也有 VM 集成路径。 |
| 多云或多集群 | 需要哪些 trust、API、data-plane、策略分发和灾难恢复边界？ |
| 强可观测性 | 需要哪些 application/proxy 信号、collector/exporter 路径、保留和访问控制？ |

单独的 Service ExternalName 不会把 VM 加入 Mesh 或创建 proxy identity。数据平面 binary 还需要受支持的注册、凭据、网络重定向和实际 control-plane 连通性。同样，在两个 Istio 安装中设置 meshID/network 字符串并非完整的多集群设计。

使用具有实际工作负载和所需策略的有界 PoC，保留可复现测量并测试故障/恢复。[比较索引](README.md)和[Istio 与 VPC Lattice 指南](02-istio-vs-lattice.md)提供相关决策标准。产品选择不由 Service 数量、通用“功能最多”标签或未经支持的快速 ROI 声称决定。

## 官方参考资料

- [Istio 架构](https://istio.io/latest/docs/ops/deployment/architecture/) 和[支持的发布版](https://istio.io/latest/docs/releases/supported-releases/)
- [Istio VM 集成](https://istio.io/latest/docs/setup/install/virtual-machine/) 和[多集群](https://istio.io/latest/docs/setup/install/multicluster/)
- [Linkerd 发布版](https://linkerd.io/releases/)、[Kubernetes 兼容性](https://linkerd.io/docs/reference/k8s-versions/) 和 [Gateway API 兼容性](https://linkerd.io/docs/features/gateway-api/)
- [Linkerd 请求路由](https://linkerd.io/docs/features/request-routing/)、[HTTPRoute](https://linkerd.io/docs/reference/httproute/)、[授权](https://linkerd.io/docs/reference/authorization-policy/) 和[限流](https://linkerd.io/docs/features/rate-limiting/)
- [Linkerd 多集群](https://linkerd.io/docs/features/multicluster/)、[VM 扩展](https://linkerd.io/docs/tasks/adding-non-kubernetes-workloads/) 和[追踪](https://linkerd.io/docs/features/distributed-tracing/)
- [Kong Mesh 变更日志](https://developer.konghq.com/mesh/changelog/)、[支持](https://developer.konghq.com/mesh/support-policy/) 和[已验证版本](https://developer.konghq.com/mesh/version-compatibility/)
- [Kong MeshHTTPRoute](https://developer.konghq.com/mesh/policies/meshhttproute/)、[MeshTrafficPermission](https://developer.konghq.com/mesh/policies/meshtrafficpermission/) 和[负载均衡策略](https://developer.konghq.com/mesh/policies/meshloadbalancingstrategy/)
- [Kong 多区部署](https://developer.konghq.com/mesh/mesh-multizone-service-deployment/) 和[安装](https://developer.konghq.com/mesh/deploy-mesh-self-managed/)
- [Consul 代理](https://developer.hashicorp.com/consul/docs/connect/proxy)、[service defaults](https://developer.hashicorp.com/consul/docs/reference/config-entry/service-defaults)、[resolver](https://developer.hashicorp.com/consul/docs/reference/config-entry/service-resolver)、[splitter](https://developer.hashicorp.com/consul/docs/reference/config-entry/service-splitter) 和 [intentions](https://developer.hashicorp.com/consul/docs/reference/config-entry/service-intentions)
- [Consul 2.0.4 application 许可](https://raw.githubusercontent.com/hashicorp/consul/v2.0.4/LICENSE)
- [本指南中的 Istio 架构](../03-architecture.md)