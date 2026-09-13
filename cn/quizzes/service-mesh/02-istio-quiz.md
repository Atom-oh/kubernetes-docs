# Istio 测验

> **最后更新**：2026 年 9 月 11 日 · 示例检查：Istio 1.31.0 / Argo Rollouts 1.10.0

本测验涵盖[持续维护的 Istio 指南](../../service-mesh/istio/README.md)。兼容性参阅[安装指南](../../service-mesh/istio/01-installation.md)；通用 Kubernetes 最低要求不是支持矩阵。示例用于学习，不是经生产测试的部署。将示意命名空间、主机名、身份和后端端点替换为已验证输入。

## 问题 1：服务网格基本概念

<details>
<summary>什么是服务网格，其主要功能有哪些？</summary>

服务网格为服务通信添加基础设施级控制和观察。其能力包括路由/负载均衡、具有明确预算的重试/超时、工作负载身份与传输安全、授权、指标、访问日志和追踪集成。

Istio 提供 Sidecar 和 Ambient 数据平面，两者 L4/L7 能力及策略附加方式不同。许多控制无需修改业务逻辑，但应用仍参与追踪上下文传播、优雅关闭和持久幂等性。网格不会自动使非幂等重试安全，也不会安装所有可观测性后端。

</details>

## 问题 2：Istio 架构

<details>
<summary>控制平面和数据平面各承担什么职责？</summary>

- **Istiod** 监视服务/配置状态，转换配置并分发到代理。Kubernetes 持久化 CRD 对象。工作负载证书签发/续订使用 Istiod 配置的 CA 集成。
- **Sidecar 模式**在每个已纳管应用 Pod 旁使用 Envoy 处理被拦截流量。
- **Ambient 模式**使用节点级 ztunnel 提供 L4 传输/身份，并用可选 Envoy waypoint 提供受支持 L7 功能。
- **网关**处理选定入站/出站路径。其 Deployment/控制器与路由配置资源相互独立。

“所有流量均被拦截”需要验证排除项、协议和纳管情况。不存在通用 85% 资源减少：应比较实际代理数量、requests/limits、用量、waypoint 容量、节点装箱和运维成本。参阅[架构](../../service-mesh/istio/03-architecture.md)及 [Ambient 资源模型](../../service-mesh/istio/advanced/01-ambient-mode.md)。

</details>

## 问题 3：流量管理和 Argo Rollouts 集成

<details>
<summary>Istio 路由和 Argo 分析如何配合金丝雀发布？</summary>

Argo 更改命名 Istio HTTP 路由上的权重，同时维护稳定版/金丝雀后端选择。Rollout 还需要选择器、Pod 模板、真实 Service、命名空间纳管和对应 VirtualService。以下**仅为 Rollout.spec 下的片段**，使用[完整发布指南](../../service-mesh/istio/advanced/08-argo-rollouts.md)中基于主机的示例：

```yaml
strategy:
  canary:
    stableService: test-stable
    canaryService: test-canary
    maxSurge: 1
    maxUnavailable: 0
    trafficRouting:
      istio:
        virtualService:
          name: test
          routes:
          - primary
    steps:
    - setWeight: 10
    - pause:
        duration: 5m
    - analysis:
        templates:
        - templateName: success-rate
        args:
        - name: service-name
          value: test-canary
        - name: namespace
          value: rollouts-demo
    - setWeight: 50
    - pause:
        duration: 5m
    - analysis:
        templates:
        - templateName: success-rate
        args:
        - name: service-name
          value: test-canary
        - name: namespace
          value: rollouts-demo
    - setWeight: 80
    - pause:
        duration: 5m
    - analysis:
        templates:
        - templateName: success-rate
        args:
        - name: service-name
          value: test-canary
        - name: namespace
          value: rollouts-demo
```

下方命名成功率模板执行次数有限。它同时检查**金丝雀 Service** 的请求量和 HTTP 可用性，使用单侧报告避免同时统计两个代理：

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: success-rate
  namespace: rollouts-demo
spec:
  args:
  - name: service-name
  - name: namespace
  metrics:
  - name: request-volume
    interval: 30s
    successCondition: len(result) == 1 && !isNaN(result[0]) && !isInf(result[0]) && result[0] >= 20
    failureLimit: 0
    provider:
      prometheus:
        address: http://prometheus.istio-system.svc.cluster.local:9090
        query: sum(increase(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}"}[2m]))
    count: 5
  - name: http-availability
    interval: 30s
    successCondition: len(result) == 1 && !isNaN(result[0]) && !isInf(result[0]) && result[0] >= 0.95
    failureLimit: 0
    provider:
      prometheus:
        address: http://prometheus.istio-system.svc.cluster.local:9090
        query: |-
          (sum(rate(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}",response_code!~"5..|0"}[2m])) or vector(0))
          /
          sum(rate(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}"}[2m]))
    count: 5
```

Prometheus 后端必须存在并抓取相关代理。Sidecar 示例要求源报告方 HTTP 指标和真实金丝雀流量；仅 Ambient L4 路径不提供这些 L7 测量。

Argo Prometheus 结果是数组，因此条件先检查长度，再检查 result[0]。空、NaN 和无限值不得通过。分子的零值回退处理全部失败的流量，而流量门槛防止将零/缺失流量判为健康。此处“可用性”排除 5xx 和状态码 0；不保证业务成功，也不代表仅 2xx 响应。

旧的标量 result >= 0.95、省略提供程序地址、缺失延迟模板和不完整 Rollout 并非完整自动化方案。failureLimit 统计**允许的失败次数**：2 允许两次，第三次失败；此示例使用 0。实际反应时间取决于测量间隔、控制器协调和路由传播，不是立即回滚承诺。

</details>

## 问题 4：安全功能

<details>
<summary>mTLS、授权和 JWT 验证有何区别？</summary>

PeerAuthentication 控制接受的入站工作负载 mTLS。不制定客户端出站 TLS 策略。以下命名空间策略假定调用方已准备好使用 STRICT；放入网格根命名空间会产生更广影响：

```yaml
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: default
  namespace: app
spec:
  mtls:
    mode: STRICT
```

对于**已纳入 Sidecar** 的后端 Pod，这些策略同时要求 frontend 工作负载身份、已验证 JWT 和允许的 GET 路径：

```yaml
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: backend-default-deny
  namespace: app
spec:
  selector:
    matchLabels:
      app: backend
---
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: backend-read
  namespace: app
spec:
  selector:
    matchLabels:
      app: backend
  action: ALLOW
  rules:
  - from:
    - source:
        principals:
        - cluster.local/ns/app/sa/frontend
        requestPrincipals:
        - '*'
    to:
    - operation:
        methods:
        - GET
        paths:
        - /api/*
---
apiVersion: security.istio.io/v1
kind: RequestAuthentication
metadata:
  name: backend-jwt
  namespace: app
spec:
  selector:
    matchLabels:
      app: backend
  jwtRules:
  - issuer: https://auth.example.com
    jwksUri: https://auth.example.com/.well-known/jwks.json
    audiences:
    - backend-api
```

第一条策略是针对所选后端的空 **ALLOW** 策略，在 ALLOW 规则匹配前提供默认拒绝行为。它不是覆盖后续允许规则的显式 DENY 操作。其他匹配 ALLOW 策略可扩大访问，因此应审核完整策略集。

RequestAuthentication 验证提供的 JWT，但单独使用时接受不带 JWT 的请求。此处由 requestPrincipals 条件使已验证 JWT 成为必需。签发者、JWKS URL 和受众是实际提供商的占位符。工作负载主体与 JWT 主体是不同身份。

Ambient 中 L7 策略要求受支持的 waypoint 附加；不要将基于 Sidecar 选择器的 HTTP 策略复制到 ztunnel。targetRefs、迁移和信任边界参阅[安全指南](../../service-mesh/istio/security/README.md)。

</details>

## 问题 5：网关和 Ingress

<details>
<summary>如何配置网关 TLS 终止和应用路由？</summary>

此示例使用 **Istio Gateway**，不是 Kubernetes Gateway API。网关 Deployment、匹配 Pod 标签和 Service 端口必须已配置。应用运行于 bookinfo，网关工作负载和凭证位于 istio-ingress：

```yaml
apiVersion: networking.istio.io/v1
kind: Gateway
metadata:
  name: bookinfo-gateway
  namespace: istio-ingress
spec:
  selector:
    istio: ingressgateway
  servers:
  - port:
      number: 443
      name: https
      protocol: HTTPS
    tls:
      mode: SIMPLE
      credentialName: bookinfo-secret
    hosts:
    - bookinfo.example.com
  - port:
      number: 80
      name: http
      protocol: HTTP
    hosts:
    - bookinfo.example.com
    tls:
      httpsRedirect: true
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: bookinfo
  namespace: bookinfo
spec:
  hosts:
  - bookinfo.example.com
  gateways:
  - istio-ingress/bookinfo-gateway
  http:
  - route:
    - destination:
        host: productpage.bookinfo.svc.cluster.local
        port:
          number: 9080
    timeout: 10s
    retries:
      attempts: 0
```

SIMPLE 终止下游 TLS，之后 VirtualService 使用 HTTP 路由。HTTP 监听器仅重定向准入的示例域名。路由显式禁用重试，包括写入。使用前替换自有域名及实际命名空间/Service/选择器值。

```bash
kubectl -n istio-ingress create secret tls bookinfo-secret \
  --key=bookinfo.key \
  --cert=bookinfo-fullchain.pem
```

此操作封装已有证书/密钥；不签发证书或建立客户端信任。检查 SAN、证书链、到期和网关凭证访问。Kubernetes Gateway API 使用 GatewayClass/Gateway/HTTPRoute 附加及控制器状态，而非此资源模式。

</details>

## 问题 6：可观测性工具

<details>
<summary>遥测组件测量什么，必须配置哪些内容？</summary>

Prometheus 采集指标；Grafana 渲染仪表板；Kiali 使用已配置遥测和网格状态；Jaeger 等追踪后端存储通过配置的提供程序/采集器发送的追踪。它们是集成，并非 Istio 默认配置档自动安装的工具。

以下查询为 app 中的 reviews 选择一条源报告方流。延迟输出单位为**秒**，流量为**请求/秒**，错误包含 5xx 和状态码 0：

```promql
# latency
histogram_quantile(0.95, sum by (le) (rate(istio_request_duration_milliseconds_bucket{reporter="source",destination_service_name="reviews",destination_service_namespace="app"}[5m]))) / 1000

# traffic
sum(rate(istio_requests_total{reporter="source",destination_service_name="reviews",destination_service_namespace="app"}[5m]))

# error
(sum(rate(istio_requests_total{reporter="source",destination_service_name="reviews",destination_service_namespace="app",response_code=~"5..|0"}[5m])) or vector(0)) / sum(rate(istio_requests_total{reporter="source",destination_service_name="reviews",destination_service_namespace="app"}[5m]))

# cpu
sum(rate(container_cpu_usage_seconds_total{namespace="app",container="istio-proxy",pod!=""}[5m]))
```

CPU 查询选择 **container** 标签，不是虚构的含 istio-proxy 的 Pod 名。结果是消耗的 CPU 核数，本身不是饱和百分比；需比较 limits/容量和节流。它需要对应 kubelet/cAdvisor 指标。空/零流量分母产生无数据/NaN 状态，不证明健康；错误分子回退仅在正总量存在时表示 0。

对于追踪，配置真实 OTLP gRPC 接收器和命名提供程序，再通过 Telemetry 选择：

```yaml
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  meshConfig:
    enableTracing: true
    extensionProviders:
    - name: otel
      opentelemetry:
        service: otel-collector.observability.svc.cluster.local
        port: 4317
---
apiVersion: telemetry.istio.io/v1
kind: Telemetry
metadata:
  name: tracing
  namespace: app
spec:
  tracing:
  - providers:
    - name: otel
    randomSamplingPercentage: 1.0
```

IstioOperator 块是 istioctl 安装输入。它不部署 Collector 或 Jaeger。1% 采样值是示意，不是通用目标；应用必须传播上下文。更改前检查后端协议、保留策略和采样成本。

仪表板命令仅连接到已安装、可发现的后端：

```bash
istioctl dashboard kiali
istioctl dashboard prometheus
istioctl dashboard grafana
istioctl dashboard jaeger
```

</details>

## 问题 7：Ambient 模式

<details>
<summary>Ambient 与 Sidecar 模式有何区别？</summary>

| 方面 | Sidecar | Ambient |
|---|---|---|
| 放置 | 每个已纳管应用 Pod 旁运行 Envoy | 节点级 ztunnel 加选定 waypoint |
| L4 传输 | 工作负载代理 | ztunnel/HBONE |
| L7 功能 | 受支持的 Envoy 功能和 API 范围 | 需要适当 waypoint 及受支持附加/API |
| 资源 | 取决于 Pod 数、工作负载和配置 | 取决于节点、waypoint 部署/容量和工作负载 |
| 采用 | 对目标 Pod 注入/重建 | CNI 和纳管前提条件；从现有 Sidecar 迁移仍需受控发布 |
| 性能 | 测量实际工作负载 | 分别测量 L4 和 L7 路径；无固定优势或节省百分比 |

使用 [Ambient 安装/迁移指南](../../service-mesh/istio/advanced/01-ambient-mode.md)。对任意共享安装应用 profile=ambient 并标记 default，不是安全完整的迁移流程。检查 CNI 兼容性、NetworkPolicy/HBONE、冲突 Sidecar 标签、waypoint 功能和实际纳管情况。

```bash
kubectl get namespace app --show-labels
istioctl ztunnel-config workloads -n istio-system
```

这些只读检查本身不纳管工作负载，也不证明 L7 策略执行。Service 数、Pod 数和固定“每节点 50MB”不足以预测用量或节省。

</details>

## 问题 8：韧性模式

<details>
<summary>异常检测、连接池限制和限速有何区别？</summary>

异常检测根据观察到的故障剔除不健康端点；连接池断路器约束连接、待处理请求或活动请求等选定资源。它们不施加每秒请求配额。

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews
  namespace: app
spec:
  host: reviews.app.svc.cluster.local
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 100
      http:
        http1MaxPendingRequests: 50
        http2MaxRequests: 100
    outlierDetection:
      consecutive5xxErrors: 5
      interval: 30s
      baseEjectionTime: 30s
      maxEjectionPercent: 50
```

consecutive5xxErrors 是当前字段。连续失败检测可即时执行；interval 不承诺每次剔除前等待 30 秒。baseEjectionTime 可随重复剔除增加，每代理端点/容量行为也很重要。maxEjectionPercent 不应被解读为全局可用性保证。

对于 9080 上的 **Sidecar 入站** HTTP 监听器，此示例本地令牌桶初始突发容量为 100，每秒补充 10 个令牌：

```yaml
apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata:
  name: reviews-local-rate-limit
  namespace: app
spec:
  workloadSelector:
    labels:
      app: reviews
  configPatches:
  - applyTo: HTTP_FILTER
    match:
      context: SIDECAR_INBOUND
      listener:
        portNumber: 9080
        filterChain:
          filter:
            name: envoy.filters.network.http_connection_manager
            subFilter:
              name: envoy.filters.http.router
    patch:
      operation: INSERT_BEFORE
      value:
        name: envoy.filters.http.local_ratelimit
        typed_config:
          '@type': type.googleapis.com/envoy.extensions.filters.http.local_ratelimit.v3.LocalRateLimit
          stat_prefix: http_local_rate_limiter
          token_bucket:
            max_tokens: 100
            tokens_per_fill: 10
            fill_interval: 1s
          filter_enabled:
            runtime_key: local_rate_limit_enabled
            default_value:
              numerator: 100
              denominator: HUNDRED
          filter_enforced:
            runtime_key: local_rate_limit_enforced
            default_value:
              numerator: 100
              denominator: HUNDRED
```

类型 URL、工作负载/监听器/路由器匹配及启用/执行比例都是此示例必要部分。已配置但未启用/执行的桶不是有效限制。限制默认局限于代理进程，因此副本会倍增总容量；不是网格全局配额。不支持在 waypoint 使用 EnvoyFilter。全局限制需要限速服务和匹配描述符；参阅[限速](../../service-mesh/istio/resilience/02-rate-limiting.md)。

</details>

## 问题 9：EKS 上的局部性负载均衡

<details>
<summary>局部性偏好提供什么，又不能保证什么？</summary>

局部性使用端点/来源拓扑信息优先选择合适目的地。此前 reviews DestinationRule 的这个**替代方案**使用区域/可用区优先级并结合异常检测：

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews
  namespace: app
spec:
  host: reviews.app.svc.cluster.local
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 100
      http:
        http1MaxPendingRequests: 50
        http2MaxRequests: 100
    outlierDetection:
      consecutive5xxErrors: 5
      interval: 30s
      baseEjectionTime: 30s
      maxEjectionPercent: 50
    loadBalancer:
      localityLbSetting:
        enabled: true
        failoverPriority:
        - topology.kubernetes.io/region
        - topology.kubernetes.io/zone
```

不要在一个局部性设置中同时使用 distribute 与 failover 或 failoverPriority。80/20 distribute 规则在健康时有意将 20% 流量发往远端；不是“仅故障时远程”。故障转移需要可达、已发现端点及足够容量。它无法访问被 Service 选择排除或注册表中不存在的远程可用区/集群。

```bash
kubectl get nodes -L topology.kubernetes.io/region,topology.kubernetes.io/zone
```

验证实际标签和代理端点局部性。AWS 账户之间可用区名称可能不同；跨账户比较物理可用区时使用适当 AZ ID 映射。成本取决于流量及确切 EC2/负载均衡器/网络路径；启用局部性不会自动得出通用 $0.01/GB 规则、固定延迟或 85% 节省。

</details>

## 问题 10：Amazon EKS 集成和最佳实践

<details>
<summary>在 EKS 上安装或运维 Istio 前必须检查什么？</summary>

1. 使用确切受支持的 Istio/Kubernetes/EKS 交集和固定 CLI/chart。没有内置 production 配置档。通过安装所有者使用已审核 Helm/istioctl 配置。
2. 识别负载均衡器控制器：AWS Load Balancer Controller、EKS Auto Mode 和旧预置方式具有不同所有权/设置。让 Service 选择器/端口匹配实际网关。决定在 NLB 或网关终止 TLS；不要意外将明文发到 TLS 监听器，也不要添加非预期双重 TLS。
3. 将 AWS 权限授予调用 AWS API 的组件，如负载均衡器控制器或遥测采集器。Envoy 不会仅因转发流量就需要 IAM 角色。为 IRSA 或受支持 EKS Pod Identity 集成配置信任和权限；仅注解不是完整设置。
4. 仅开放所需方向的网络路径。代理拦截端口不是应在安全组中无差别暴露的列表。适用时包含 webhook/xDS、健康检查和实际入口/Ambient 路径。
5. 根据工作负载证据规划 Istiod/代理资源，并提供调度/可用容量。PDB 处理特定自愿中断；仅副本数不确保可用区多样性，也不防护所有故障。
6. 分别配置指标、日志和追踪。单个 Fluent Bit cloudwatch_logs 输出片段不是 Container Insights，也不是完整 CRI 输入/解析器/IAM/日志流管道。

控制平面 HPA 和代理 requests/limits 的示意安装输入如下：

```yaml
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  components:
    pilot:
      k8s:
        resources:
          requests:
            cpu: 500m
            memory: 2Gi
        hpaSpec:
          minReplicas: 3
          maxReplicas: 5
  values:
    global:
      proxy:
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 500m
            memory: 1Gi
```

3–5 个副本和资源数量只是示例，不是已验证生产容量配置。检查 HPA 指标、放置和可用容量。用实际资源/计费测量评估 Ambient 和配置范围；不存在通用 85% 或 30–50% 节省保证。

完整流程参阅 [AWS 集成指南](../../service-mesh/istio/04-aws-integration.md)和[最佳实践](../../service-mesh/istio/best-practices.md)。

</details>

## 附加题：渐进式交付

<details>
<summary>什么使渐进式交付分析有用，其限制在哪里？</summary>

完整发布需要真实路由目标、稳定容量、明确分析参数，以及有限且有意义的测量策略。以下模板在金丝雀 Service 示例上添加请求量、HTTP 可用性和 P95 延迟：

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: comprehensive-analysis
  namespace: rollouts-demo
spec:
  args:
  - name: service-name
  - name: namespace
  metrics:
  - name: request-volume
    interval: 30s
    successCondition: len(result) == 1 && !isNaN(result[0]) && !isInf(result[0]) && result[0] >= 20
    failureLimit: 0
    provider:
      prometheus:
        address: http://prometheus.istio-system.svc.cluster.local:9090
        query: sum(increase(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}"}[2m]))
    count: 5
  - name: http-availability
    interval: 30s
    successCondition: len(result) == 1 && !isNaN(result[0]) && !isInf(result[0]) && result[0] >= 0.99
    failureLimit: 0
    provider:
      prometheus:
        address: http://prometheus.istio-system.svc.cluster.local:9090
        query: |-
          (sum(rate(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}",response_code!~"5..|0"}[2m])) or vector(0))
          /
          sum(rate(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}"}[2m]))
    count: 5
  - name: latency-p95
    interval: 30s
    successCondition: len(result) == 1 && !isNaN(result[0]) && !isInf(result[0]) && result[0] <= 0.5
    failureLimit: 0
    provider:
      prometheus:
        address: http://prometheus.istio-system.svc.cluster.local:9090
        query: |-
          histogram_quantile(0.95,
            sum by (le) (rate(istio_request_duration_milliseconds_bucket{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}"}[2m]))
          ) / 1000
    count: 5
  - name: http-error-rate
    interval: 30s
    successCondition: len(result) == 1 && !isNaN(result[0]) && !isInf(result[0]) && result[0] <= 0.01
    failureLimit: 0
    provider:
      prometheus:
        address: http://prometheus.istio-system.svc.cluster.local:9090
        query: |-
          (sum(rate(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}",response_code=~"5..|0"}[2m])) or vector(0))
          /
          sum(rate(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}"}[2m]))
    count: 5
```

在完整 Rollout 的匹配分析步骤中引用此模板。它不能替代不完整 Rollout 示例中缺失的选择器/模板/Service。阈值为示意；查询选择器、单位、流量和业务 SLO 必须一致。

测量失败、提供程序错误、结果不确定、中止和后续部署先前修订，是不同状态。检查 AnalysisRun/Rollout 状态；不要都称为即时回滚。中止不能撤销数据库写入或其他应用副作用。控制器间隔、稳定后端可用性和配置传播限制恢复速度。

自动化可减少重复决策，但没有指标门槛能确立通用安全部署，或保证无需人工诊断。测试无流量、缺失序列、全失败、NaN/无限值和恢复情况。[完整发布指南](../../service-mesh/istio/advanced/08-argo-rollouts.md)包含周边资源及验证边界。

</details>

## 自我评估

用 11 个答案确定需要复习的主题。测验高分不是生产运维就绪证据；还应在受控环境进行配置审核和实践验证。

## 学习资源

- [持续维护的 Istio 文档](../../service-mesh/istio/README.md)
- [Istio 官方文档](https://istio.io/latest/docs/)
- [Argo Rollouts Istio 集成](https://argo-rollouts.readthedocs.io/en/stable/features/traffic-management/istio/)
- [Argo 分析语义](https://argo-rollouts.readthedocs.io/en/stable/features/analysis/)
- [Prometheus 即时查询结果](https://argo-rollouts.readthedocs.io/en/stable/analysis/prometheus/)
- [Istio TLS 配置](https://istio.io/latest/docs/ops/configuration/traffic-management/tls-configuration/)
- [Istio API 参考](https://istio.io/latest/docs/reference/config/)
