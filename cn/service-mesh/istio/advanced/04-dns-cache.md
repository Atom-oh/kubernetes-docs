# DNS 代理与 DNS 缓存

> **验证基线**：Istio 1.31.0，Kubernetes 1.32–1.37
> **最后审核日期**：2026 年 10 月 16 日

通过 Istio 的 DNS 管理功能，优化外部服务访问性能并控制 DNS 查询。

## 目录

1. [DNS 代理概述](#dns-proxy-overview)
2. [DNS 代理与 DNS 缓存的区别](#dns-proxy-vs-dns-caching)
3. [DNS 代理配置](#dns-proxy-configuration)
4. [ServiceEntry 集成](#serviceentry-integration)
5. [DNS 缓存配置](#dns-caching-configuration)
6. [自动分配地址](#automatic-address-allocation)
7. [故障排查](#troubleshooting)
8. [最佳实践](#best-practices)

## DNS 代理概述 {#dns-proxy-overview}

在 sidecar 模式下，应用程序的 DNS 请求会被重定向到 **istio-agent 的 Go DNS 服务器**，而不是 Envoy HTTP/DNS 监听器。Agent 从 Istiod 提供的名称/IP 表中应答，并将未知名称转发到 `/etc/resolv.conf` 中的上游解析器。它支持 UDP 和 TCP DNS；sidecar 通常使用 DNS 端口 15053。

在 ambient 模式下，ztunnel 负责处理 DNS，且从 Istio 1.25 起默认启用流量捕获。sidecar 模式仍需显式启用。DNS-over-HTTPS/TLS 和应用程序管理的缓存与普通的 53 端口流量捕获是分开的。下文的 EnvoyFilter 和 Agent 诊断适用于 **sidecar 模式**。

## DNS 代理与 DNS 缓存的区别 {#dns-proxy-vs-dns-caching}

| 层 | 职责 | 配置 |
|---|---|---|
| 应用程序/OS 解析器缓存 | 应用程序名称、TTL 和负缓存 | 应用程序运行时、OS 和解析器 |
| Istio DNS 代理 | 本地网格名称/IP 表，以及其他名称的上游转发 | Sidecar `ISTIO_META_DNS_CAPTURE`，ambient CNI/ztunnel |
| Envoy DNS 服务发现 | 刷新基于 DNS 的上游集群的端点 | ServiceEntry 和生成的 DNS 集群配置 |
| Envoy 动态转发代理 DNS 缓存 | 根据请求 Host/SNI 解析动态目标 | 独立的 DYNAMIC_DNS/DFP 配置 |

`dns_refresh_rate` 不会启用对所有应用程序 DNS 响应的缓存。sidecar Agent 也不会将未知名称的上游响应保留为通用响应缓存。已知名称可以避免一次 CoreDNS 往返，但上游端点刷新仍会独立进行；同时启用这两种机制并不能保证性能达到最佳。

## DNS 代理配置 {#dns-proxy-configuration}

### 1. 全局启用

将此 `istioctl` 输入合并到现有安装配置中。它不是要通过 `kubectl apply` 应用到已移除的集群内 Operator 的资源。对于 Helm 安装，请将等效的 meshConfig 值合并到现有 chart 配置中。现有 sidecar 流量捕获规则会通过新注入或启动的 Pods 生效，因此应仅逐步发布经过审核的工作负载。

```yaml
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
metadata:
  name: istio
  namespace: istio-system
spec:
  meshConfig:
    defaultConfig:
      proxyMetadata:
        ISTIO_META_DNS_CAPTURE: "true"
```

当前的地址分配由 Istiod 控制器负责，且默认启用。新安装无需将旧版 `ISTIO_META_DNS_AUTO_ALLOCATE` 元数据作为前置条件。

### 2. 按命名空间启用

仅设置命名空间注入标签并不能启用 DNS 流量捕获。使用 GitOps/Kustomize/Helm，将以下片段合并到所选命名空间中的 Deployment Pod 模板。用部分值替换中央的 `istio-sidecar-injector` ConfigMap 并不是按命名空间配置。保留现有 `proxy.istio.io/config` 注解中的其他字段。

### 3. 按 Pod 启用

```yaml
# Existing Deployment: merge into spec.template, not a complete workload
metadata:
  annotations:
    proxy.istio.io/config: |
      proxyMetadata:
        ISTIO_META_DNS_CAPTURE: "true"
```

保留现有的旧版/修订版注入模式，并重新创建所选 Pods。这是模板片段，不是一个默认使用 `myapp:v1` 镜像的完整 Pod。对于 ambient Pods，请检查默认流量捕获行为，以及 `ambient.istio.io/dns-capture: "false"` 这一退出选项。

### 4. 验证重定向和响应

Pod 网络命名空间中的 DNS 重定向方式会因安装模式和 CNI 而异。不要假设代理镜像包含 bash/iptables/tcpdump 或拥有 net-admin 权限。请先检查下文所述的 Agent 名称表、DNS 查询和上游端点，而不是提升生产 Pod 的权限。如有需要，请在获批的诊断环境中检查 UDP/TCP 53 和 15053 的路径。

## ServiceEntry 集成 {#serviceentry-integration}

DNS 代理与 ServiceEntry 紧密协作。

### 基本 ServiceEntry

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: external-api
  namespace: default
spec:
  hosts:
  - api.example.com
  ports:
  - number: 443
    name: https
    protocol: HTTPS
  location: MESH_EXTERNAL
  resolution: DNS
```

**DNS 代理行为**：

1. 应用程序执行 `api.example.com` DNS 查询
2. Agent DNS 代理返回一个已分配的 VIP（例如 `240.240.0.1`）
3. 应用程序向虚拟 IP 发送请求
4. Envoy 将此目标路由到独立解析出的真实上游端点

### 注册多个 Host

使用不同的具体名称注册相互独立的上游服务。这些 example.com 名称仅为配置示例；请将其替换为真实且可通过 DNS/TLS 访问的后端。

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: partner-api
  namespace: default
spec:
  hosts: ["api.partner.example.com"]
  ports:
  - number: 443
    name: https
    protocol: HTTPS
  location: MESH_EXTERNAL
  resolution: DNS
---
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: assets-cdn
  namespace: default
spec:
  hosts: ["cdn.example.com"]
  ports:
  - number: 443
    name: https
    protocol: HTTPS
  location: MESH_EXTERNAL
  resolution: DNS
```

像 `*.example.com` 这样的通配符配合 `resolution: DNS`，且没有具体端点时，无法解析所有子域名。sidecar 将通配符流量转发到应用程序原始目标时，使用的是独立的 `resolution: NONE` 模式，并不会提供 DNS 应答。Istio 1.31 的 `DYNAMIC_DNS` 是一种独立的、基于 Host/SNI 的模式；ambient 模式需要 waypoint，且不支持原始 TCP。请依据当前 API 和生成的配置进行选择。

### 显式端点

`addresses` 用于指定面向客户端的 VIP；`endpoints` 用于指定真实后端。CIDR 前缀可以匹配流量，但它不是单个 DNS A/AAAA 应答。这些 TEST-NET 地址不会部署数据库；请使用真实且不冲突的 VIP/后端/TLS 配置。

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: external-database
  namespace: default
spec:
  hosts:
  - database.external.com
  addresses:
  - 198.51.100.10  # Explicit example VIP
  ports:
  - number: 3306
    name: mysql
    protocol: TCP
  location: MESH_EXTERNAL
  resolution: STATIC
  endpoints:
  - address: 203.0.113.10
  - address: 203.0.113.11
  - address: 203.0.113.12
```

## DNS 缓存配置 {#dns-caching-configuration}

### 基于 DNS 的上游刷新

Istio 1.31 会在普通 DNS 集群上设置 `respect_dns_ttl: true`，其默认 mesh `dnsRefreshRate` 为 60 秒。成功响应会采用 DNS TTL；失败响应/零 TTL 则遵循生成的解析器/集群设置。概念性 DNS 页面中“固定为 30 秒，且无法更改”的说法与此版本的源代码不符；请检查生效的配置。

此低层替代方案会修改 `default` 命名空间中 `app: frontend` 的 **一个 api.example.com:443 DNS 集群**。`cluster.service` 匹配实际的服务名称，而不是 glob 选择器。不要从根命名空间广泛地修补所有集群。

```yaml
apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata:
  name: external-api-dns-refresh
  namespace: default
spec:
  workloadSelector:
    labels:
      app: frontend
  configPatches:
  - applyTo: CLUSTER
    match:
      context: SIDECAR_OUTBOUND
      cluster:
        service: api.example.com
        portNumber: 443
    patch:
      operation: MERGE
      value:
        dns_refresh_rate: 30s
        respect_dns_ttl: true
        dns_failure_refresh_rate:
          base_interval: 5s
          max_interval: 30s
```

### TTL、失败刷新和解析器

设置 `respect_dns_ttl: true` 后，并不会强制每次成功查询都每 30 秒刷新一次。`dns_failure_refresh_rate` 控制失败后的重试时间，而不是记录 TTL 或过期响应的保留时间。`dns_query_timeout` 不是 Cluster 字段；请验证特定于解析器的类型化配置。保留 Istio 选定的 IP 地址族，不要无条件强制使用仅 IPv4/AUTO。

不要假设通过将默认标量值 `false` 赋给 `respect_dns_ttl: true`，就可以用 protobuf `MERGE` 清除现有值。Envoy 中有些集群 DNS 字段已弃用，但 Istio 1.31 仍会生成这种形式。升级时请重新检查 DNS 集群扩展和解析器配置。

### 检查已应用的配置

```bash
istioctl proxy-config clusters <client-pod> -n default --fqdn api.example.com -o json |
  jq '.[] | {name,type,dnsRefreshRate,respectDnsTtl,dnsFailureRefreshRate,dnsLookupFamily,typedDnsResolverConfig,loadAssignment}'
```

## 自动分配地址 {#automatic-address-allocation}

### 分配方和状态

默认启用的 Istiod IP 分配控制器会为符合条件的每个 ServiceEntry host 分配 VIP，并在 `status.addresses` 中记录 `host`/`value`。普通的 `resolution: DNS` 通配符不符合条件；`DYNAMIC_DNS` 通配符有独立的受支持路径。具有显式 `spec.addresses` 或 `networking.istio.io/enable-autoallocate-ip: "false"` 的条目不遵循相同的分配路径。

### 地址范围

发布版本的默认前缀为 IPv4 `240.240.0.0/16` 和 IPv6 `2001:2::/48`。这里展示的是**实际控制平面设置及其默认值**；请避免与用户网络、VPN 和 Service CIDR 冲突。

```yaml
# Advanced istioctl input: these are the released defaults, not new ranges.
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  values:
    pilot:
      env:
        PILOT_ENABLE_IP_AUTOALLOCATE: "true"
        PILOT_IP_AUTOALLOCATE_IPV4_PREFIX: "240.240.0.0/16"
        PILOT_IP_AUTOALLOCATE_IPV6_PREFIX: "2001:2::/48"
```

`defaultServiceExportTo` 控制可见性，`outboundTrafficPolicy` 则涉及未注册的出站流量；两者都不会更改分配前缀。更改现有 VIP 可能影响 DNS 缓存、连接和路由，因此不能据此证明前缀更改可以实现零停机迁移。不要手动编辑由控制器管理的状态。

### 验证已分配的地址

```bash
kubectl get serviceentry external-api -n default -o json |
  jq '{hosts:.spec.hosts, explicitAddresses:.spec.addresses, allocatedAddresses:.status.addresses}'

# Inspect the client's mapping and the actual upstream separately.
istioctl proxy-config listeners <client-pod> -n default
istioctl proxy-config clusters <client-pod> -n default --fqdn api.example.com -o json
istioctl proxy-config endpoints <client-pod> -n default --cluster 'outbound|443||api.example.com'
```

已分配的 VIP 用于应用程序 DNS 响应和目标匹配。DNS 集群的 `loadAssignment` 包含需要解析的真实后端主机名；运行时端点则包含已解析的地址。不要将 VIP 描述为真实的外部上游 IP。

## 故障排查 {#troubleshooting}

### 验证 DNS 代理运行情况

```bash
# Inspect classic or native sidecar metadata without assuming a shell in the image.
kubectl get pod <client-pod> -n default -o json |
  jq '[.spec.containers[], .spec.initContainers[]?] |
      .[] | select(.name == "istio-proxy") |
      {name,env:[.env[]? | select(.name == "ISTIO_META_DNS_CAPTURE")]}'

istioctl analyze -n default
istioctl proxy-status
kubectl get serviceentry external-api -n default -o yaml
kubectl logs -n default <client-pod> -c istio-proxy --tail=100

# Requires a reviewed diagnostic container with nslookup in this Pod's network namespace.
kubectl exec -n default <client-pod> -c <diagnostic-container> -- nslookup api.example.com
```

```bash
# Terminal 1: sidecar agent's local status server (not Envoy admin 15000)
kubectl port-forward -n default <client-pod> 15020:15020
```

```bash
# Terminal 2 while the forward remains active
curl --fail --silent http://127.0.0.1:15020/debug/ndsz |
  jq '.table["api.example.com"]'
curl --fail --silent http://127.0.0.1:15020/stats/prometheus |
  grep '^istio_agent_dns_'
```

Agent 的 `/debug/ndsz` 仅接受来自 localhost 的请求；DNS/名称表状态不可用时可能会返回 404。在 Envoy 的 15000 端口监听器转储中查找 Agent 的 15053 端口不是有效的检查方法。如果应用程序没有 nslookup，请遵循既定的诊断流程，而不是修改基础镜像或提升其权限。

### 常见问题

1. **查询仍然到达 CoreDNS**：转发未知名称是正常行为。区分本地表中存在和不存在的名称，并检查流量捕获、search/ndots、TCP 回退，以及应用程序的 DoH/TLS。
2. **找不到 ServiceEntry**：检查 `exportTo`、命名空间发现/Sidecar 范围、resolution、状态分配、注入/修订版本，以及 NDS/xDS 同步。使用 `istioctl analyze -n default`；资源类型/名称不是它的位置参数。不要一开始就删除 Pod 来“强制同步”。
3. **VIP 连接失败**：分别检查 VIP 匹配与上游 DNS/端点、网络路径、TLS Host/SNI 和证书。对 443 端口的 HTTPS 服务调用 `http://VIP` 并不是有效测试。

```bash
# Run inside an approved diagnostic container sharing the captured Pod network namespace.
# Replace VIP4 with the actual IPv4 status.addresses value, and keep the real Host/SNI.
VIP4=240.240.0.1
curl --fail --show-error --resolve "api.example.com:443:${VIP4}" https://api.example.com/
```

将示例 VIP 替换为实际分配的地址，并在被流量捕获的 Pod 网络命名空间中运行。不要假设此不可路由地址可以从另一台主机访问。保持证书验证启用，并将应用程序的 DNS 路径与直接 VIP 测试分开检查。

### Envoy Admin API 和数据包检查

```bash
# Terminal 1
kubectl port-forward -n default <client-pod> 15000:15000
```

```bash
# Terminal 2: Envoy endpoint discovery, distinct from agent name-table metrics
curl --fail --silent http://127.0.0.1:15000/clusters
curl --fail --silent http://127.0.0.1:15000/config_dump > envoy-config.json
```

如果需要抓包，请遵循获批的诊断容器/节点流程，在 Pod 网络命名空间中检查 UDP/TCP 53 和 15053。不要假设 istio-proxy 包含 tcpdump、tar 或抓包权限。DNS 名称可能包含敏感信息；请限制抓包时长/范围/保留时间，并在分析后遵循处置流程。

## 最佳实践 {#best-practices}

### 1. DNS 代理启用策略

**推荐方法**：逐步发布

![流程图展示了 DNS 代理从测试、预发布到生产环境的逐步发布过程，包含验证和监控关卡；失败时会转回故障排查或回滚。](../../../.gitbook/assets/en-service-mesh-istio-advanced-04-dns-cache-3.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-advanced-04-dns-cache-3.html)

### 2. ServiceEntry 管理

```yaml
# Create separate ServiceEntry per external service
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: payment-api
  namespace: default
  labels:
    app: payment
    team: platform
spec:
  hosts:
  - payments.example.com
  ports:
  - number: 443
    name: https
    protocol: HTTPS
  location: MESH_EXTERNAL
  resolution: DNS
---
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: analytics-api
  namespace: default
  labels:
    app: analytics
    team: data
spec:
  hosts:
  - analytics.example.com
  ports:
  - number: 443
    name: https
    protocol: HTTPS
  location: MESH_EXTERNAL
  resolution: DNS
```

### 3. DNS 缓存 TTL 配置

分别观察记录 TTL、应用程序缓存、Agent 名称表和 Envoy 端点刷新。不要仅按类别就给所有 CDN 设置 300 秒，或给所有 API 集群设置 10 秒。对于自己控制的 DNS 区域，应根据故障转移目标和查询负载选择 TTL。ServiceEntry `exportTo`/Sidecar 范围可以减少不必要的逐代理服务发现；两者都不是网络安全边界。

对于特定 DNS 集群的失败刷新，请使用上文按工作负载/主机/端口限定范围的示例，并验证其生效配置和失败行为。

### 4. 监控指标

这些是 Istio 1.31 **sidecar Agent** 的实际指标。其前提是 Prometheus 抓取端口 15020 的 `/stats/prometheus`，并附加 `namespace`/`pod` 目标标签。不要将它们与 ztunnel 或 Envoy DFP 缓存指标混为一谈。

```promql
# Application queries handled by the sidecar agent
sum by (namespace, pod) (
  rate(istio_agent_dns_requests_total{namespace="default"}[5m])
)

# Fraction forwarded upstream; not a DNS response-cache hit/miss ratio
100 *
sum by (namespace, pod) (
  rate(istio_agent_dns_upstream_requests_total{namespace="default"}[5m])
) /
sum by (namespace, pod) (
  rate(istio_agent_dns_requests_total{namespace="default"}[5m])
)

# Requests for which the agent synthesized SERVFAIL after upstream exchange failures
100 *
sum by (namespace, pod) (
  rate(istio_agent_dns_upstream_failures_total{namespace="default"}[5m])
) /
sum by (namespace, pod) (
  rate(istio_agent_dns_upstream_requests_total{namespace="default"}[5m])
)

# Upstream request duration p99, in seconds
histogram_quantile(0.99,
  sum by (le, namespace, pod) (
    rate(istio_agent_dns_upstream_request_duration_seconds_bucket{namespace="default"}[5m])
  )
)
```

`dns_upstream_failures_total` 统计的是 Agent 在上游交换失败后生成的 SERVFAIL。它不统计有效上游响应数据包中返回的每个 NXDOMAIN/SERVFAIL。没有请求时，比例/分位数可能为 NaN 或缺失；请同时检查流量和抓取状态。不要根据这些值臆造“缓存命中率”。

### 5. 安全注意事项

DNS 流量捕获、ServiceEntry 注册和 VIP 分配都不会强制执行外部允许列表。选择 sidecar 工作负载的 AuthorizationPolicy 会评估该工作负载的**入站**流量，而不是其出站 DNS/HTTPS 请求。命名空间范围的 `DENY/notHosts` 可能会阻断内部流量，或阻断缺少 HTTP 属性的 TCP 流量。

应通过适当的 CNI/NetworkPolicy、防火墙/安全组边界，以及在需要时通过具有授权机制且不可绕过的 egress gateway 来实施出站流量控制。TLS 透传路径无法检查 HTTP Host；SNI/目标约束和证书验证需要单独处理。请遵循 [出站流量控制](../traffic-management/11-egress-control.md) 中列出的全部前置条件。

### 6. 性能调优

在更改瓶颈之前，应同时测量 DNS 负载、失败率和查询时长，以及 Istiod 推送延迟和 sidecar Agent/Envoy 的 CPU/内存使用情况。Envoy 工作线程并发数不会决定 Agent 的 Go DNS 服务器规模；仅增加 Istiod 副本/HPA 并不能加速所有 DNS 路径。

应测试应用程序缓存/ndots、DNS TTL、ServiceEntry 数量/可见性、代理副本之间的周期性查询负载，以及故障恢复期间的过期端点/连接行为。未经过测量就设定固定的 CPU/内存/HPA 值并非生产环境优化。

## 参考资料

### 官方文档
- [Istio DNS 代理](https://istio.io/latest/docs/ops/configuration/traffic-management/dns-proxy/)
- [Envoy DNS 缓存](https://www.envoyproxy.io/docs/envoy/latest/intro/arch_overview/upstream/service_discovery)
- [ServiceEntry](https://istio.io/latest/docs/reference/config/networking/service-entry/)

- [Istio 1.31 DNS 服务器](https://raw.githubusercontent.com/istio/istio/1.31.0/pkg/dns/client/dns.go)
- [Istio 1.31 IP 分配和前缀](https://raw.githubusercontent.com/istio/istio/1.31.0/pilot/pkg/features/pilot.go)
- [Istio 1.31 分配状态](https://raw.githubusercontent.com/istio/istio/1.31.0/pilot/pkg/controllers/ipallocate/ipallocate.go)
- [Istio 1.31 DNS 集群生成](https://raw.githubusercontent.com/istio/istio/1.31.0/pilot/pkg/networking/core/cluster_builder.go)
- [Istio 1.31 mesh 默认值](https://raw.githubusercontent.com/istio/istio/1.31.0/pkg/config/mesh/mesh.go)
- [Istio 1.31 Agent DNS 指标](https://raw.githubusercontent.com/istio/istio/1.31.0/pkg/dns/client/monitoring.go)
- [Istio 1.31 Agent 状态端点](https://raw.githubusercontent.com/istio/istio/1.31.0/pilot/cmd/pilot-agent/status/server.go)
- [Envoy Cluster API](https://www.envoyproxy.io/docs/envoy/latest/api-v3/config/cluster/v3/cluster.proto)

### 相关文档
- [Istio 架构 - DNS 处理机制](../03-architecture.md)
- [ServiceEntry](../traffic-management/12-service-entry.md)
- [出站流量控制](../traffic-management/11-egress-control.md)
