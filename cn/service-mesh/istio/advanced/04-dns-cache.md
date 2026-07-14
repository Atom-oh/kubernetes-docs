# DNS Proxy 和 DNS 缓存

> **支持的版本**: Istio 1.28+
> **最后更新**: February 23, 2026

通过 Istio 的 DNS 管理功能优化外部服务访问性能并控制 DNS 查询。

## 目录

1. [DNS Proxy 概述](#dns-proxy-overview)
2. [DNS Proxy 与 DNS 缓存](#dns-proxy-vs-dns-caching)
3. [DNS Proxy 配置](#dns-proxy-configuration)
4. [ServiceEntry 集成](#serviceentry-integration)
5. [DNS 缓存配置](#dns-caching-configuration)
6. [自动地址分配](#automatic-address-allocation)
7. [故障排除](#troubleshooting)
8. [最佳实践](#best-practices)

## DNS Proxy 概述

Istio DNS Proxy 是一项功能，其中 Envoy 作为 DNS 服务器拦截并处理应用程序的 DNS 请求。

### 主要功能

1. **DNS 查询拦截**：Envoy 在 UDP 端口 53 上处理 DNS 请求
2. **基于 ServiceEntry 的解析**：当外部服务注册为 ServiceEntry 时，自动生成 DNS 响应
3. **自动 IP 分配**：自动为外部服务分配虚拟 IP
4. **绕过 CoreDNS**：降低 Kubernetes DNS 服务器负载

### 架构

```mermaid
flowchart TB
    subgraph Pod[Application Pod]
        App[Application<br/>curl api.example.com]

        subgraph IPTables[iptables NAT]
            DNS_Rule[DNS Rule<br/>UDP 53 -> 15053]
            TCP_Rule[TCP Rule<br/>TCP -> 15001]
        end

        subgraph Envoy[Envoy Proxy]
            DNS_Listener[DNS Listener<br/>15053]
            DNS_Table[DNS Table<br/>ServiceEntry based]
            HTTP_Listener[HTTP Listener<br/>15001]
        end
    end

    subgraph Istiod[Istiod]
        XDS[xDS Server<br/>ServiceEntry config]
    end

    subgraph External[External]
        API[api.example.com<br/>Actual IP]
        CoreDNS[CoreDNS<br/>Cluster DNS]
    end

    App -->|1. DNS Query<br/>UDP 53| DNS_Rule
    DNS_Rule -->|2. Redirect<br/>15053| DNS_Listener
    DNS_Listener -->|3. Lookup| DNS_Table

    DNS_Table -->|4. Virtual IP<br/>240.240.0.1| DNS_Listener
    DNS_Listener -->|5. DNS Response| App

    App -->|6. HTTP Request<br/>240.240.0.1| TCP_Rule
    TCP_Rule -->|7. Redirect| HTTP_Listener
    HTTP_Listener -->|8. Convert to actual IP| API

    XDS -.->|ServiceEntry push| DNS_Table

    DNS_Listener -.->|Non-Istio domains| CoreDNS

    %% Style definitions
    classDef app fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef iptables fill:#FF9900,stroke:#333,stroke-width:1px,color:black;
    classDef envoy fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;
    classDef istiod fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef external fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;

    %% Apply classes
    class App app;
    class DNS_Rule,TCP_Rule iptables;
    class DNS_Listener,DNS_Table,HTTP_Listener envoy;
    class XDS istiod;
    class API,CoreDNS external;
```

## DNS Proxy 与 DNS 缓存

这两项功能具有不同的用途和行为：

| 特性 | DNS Proxy | DNS 缓存 |
|------|-----------|-------------|
| **角色** | 充当 DNS 服务器 | 缓存 DNS 查询结果 |
| **行为** | 拦截 DNS 查询并直接响应 | 在外部 DNS 查询后存储结果 |
| **配置** | `ISTIO_META_DNS_CAPTURE` | `dns_refresh_rate` |
| **目标** | 注册在 ServiceEntry 中的服务 | 所有外部 DNS 查询 |
| **IP 分配** | 自动虚拟 IP 分配 | 使用实际 DNS 响应 |
| **CoreDNS** | 可绕过 | 仍会使用 |
| **Istio 版本** | 1.8+ | 所有版本 |

### 组合使用

同时使用这两项功能可提供最佳性能：

```mermaid
flowchart LR
    App[Application]

    subgraph Envoy[Envoy Proxy]
        DNS_Proxy[DNS Proxy<br/>ServiceEntry services]
        DNS_Cache[DNS Cache<br/>Other external services]
    end

    SE[ServiceEntry<br/>api.example.com]
    CoreDNS[CoreDNS<br/>google.com]

    App -->|1. api.example.com| DNS_Proxy
    DNS_Proxy -->|Virtual IP| App

    App -->|2. google.com| DNS_Cache
    DNS_Cache -->|Cache miss| CoreDNS
    CoreDNS -->|Actual IP| DNS_Cache
    DNS_Cache -->|Cached IP| App

    SE -.->|Register| DNS_Proxy

    %% Style definitions
    classDef app fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef envoy fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;
    classDef external fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;

    %% Apply classes
    class App app;
    class DNS_Proxy,DNS_Cache envoy;
    class SE,CoreDNS external;
```

## DNS Proxy 配置

### 1. 全局启用

将 DNS Proxy 应用于所有 namespace：

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
        # Enable DNS Proxy
        ISTIO_META_DNS_CAPTURE: "true"
        # Enable automatic IP allocation
        ISTIO_META_DNS_AUTO_ALLOCATE: "true"
```

### 2. 按 namespace 启用

仅为特定 namespace 启用：

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: production
  labels:
    istio-injection: enabled
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: istio-sidecar-injector
  namespace: istio-system
data:
  values: |
    global:
      proxy:
        holdApplicationUntilProxyStarts: true
    sidecarInjectorWebhook:
      templates:
        custom: |
          spec:
            containers:
            - name: istio-proxy
              env:
              - name: ISTIO_META_DNS_CAPTURE
                value: "true"
              - name: ISTIO_META_DNS_AUTO_ALLOCATE
                value: "true"
```

### 3. 按 Pod 启用

仅为特定 Pod 启用：

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: myapp
  annotations:
    proxy.istio.io/config: |
      proxyMetadata:
        ISTIO_META_DNS_CAPTURE: "true"
        ISTIO_META_DNS_AUTO_ALLOCATE: "true"
spec:
  containers:
  - name: app
    image: myapp:v1
```

### 4. iptables 规则验证

启用 DNS Proxy 后，会添加以下 iptables 规则：

```bash
# Enter pod
kubectl exec -it <pod-name> -c istio-proxy -- /bin/bash

# Check DNS redirect rules
iptables -t nat -L ISTIO_OUTPUT -n -v

# Expected output
Chain ISTIO_OUTPUT (1 references)
pkts bytes target     prot opt in     out     source               destination
   0     0 RETURN     udp  --  *      *       0.0.0.0/0            127.0.0.53           udp dpt:53
   0     0 REDIRECT   udp  --  *      *       0.0.0.0/0            0.0.0.0/0            udp dpt:53 redir ports 15053
```

## ServiceEntry 集成

DNS Proxy 与 ServiceEntry 紧密集成。

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

**DNS Proxy 行为**：
1. 应用程序执行 `api.example.com` DNS 查询
2. Envoy DNS Proxy 返回虚拟 IP（例如 `240.240.0.1`）
3. 应用程序向虚拟 IP 发送请求
4. Envoy 转换为实际 IP 并传输

### 多 Host 注册

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: external-services
spec:
  hosts:
  - "*.example.com"  # Wildcard supported
  - api.partner.com
  - cdn.assets.com
  ports:
  - number: 443
    name: https
    protocol: HTTPS
  - number: 80
    name: http
    protocol: HTTP
  location: MESH_EXTERNAL
  resolution: DNS
```

### 显式 Endpoints

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: external-database
spec:
  hosts:
  - database.external.com
  addresses:
  - 203.0.113.0/24  # External network range
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

## DNS 缓存配置

DNS 缓存可提升外部 DNS 查询性能。

### 启用 Envoy DNS 缓存

```yaml
apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata:
  name: dns-cache-filter
  namespace: istio-system
spec:
  configPatches:
  - applyTo: CLUSTER
    match:
      context: SIDECAR_OUTBOUND
      cluster:
        service: "*.example.com"
    patch:
      operation: MERGE
      value:
        dns_refresh_rate: 30s  # DNS cache refresh interval
        dns_lookup_family: V4_ONLY  # Use IPv4 only
        dns_failure_refresh_rate:
          base_interval: 5s  # Retry interval on failure
          max_interval: 30s
```

### 高级 DNS 缓存配置

```yaml
apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata:
  name: advanced-dns-cache
  namespace: istio-system
spec:
  configPatches:
  - applyTo: CLUSTER
    match:
      context: SIDECAR_OUTBOUND
    patch:
      operation: MERGE
      value:
        # DNS cache TTL settings
        dns_refresh_rate: 60s

        # DNS lookup timeout
        dns_query_timeout: 5s

        # IP version priority
        dns_lookup_family: AUTO  # Auto select IPv4/IPv6

        # Cache policy on failure
        dns_failure_refresh_rate:
          base_interval: 2s
          max_interval: 10s

        # Respect DNS TTL
        respect_dns_ttl: true
```

### 仅应用于特定服务

```yaml
apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata:
  name: api-dns-cache
  namespace: default
spec:
  workloadSelector:
    labels:
      app: frontend
  configPatches:
  - applyTo: CLUSTER
    match:
      cluster:
        service: api.external.com
    patch:
      operation: MERGE
      value:
        dns_refresh_rate: 30s
        dns_lookup_family: V4_ONLY
```

## 自动地址分配

DNS Proxy 会自动为注册在 ServiceEntry 中的服务分配虚拟 IP。

### 自动分配行为

```mermaid
sequenceDiagram
    autonumber
    participant App as Application
    participant Envoy as Envoy<br/>DNS Proxy
    participant Istiod as Istiod
    participant External as api.example.com<br/>(Actual server)

    Note over Istiod: ServiceEntry registration
    Istiod->>Envoy: xDS config push<br/>(virtual IP allocated)

    App->>Envoy: DNS Query<br/>api.example.com
    Envoy->>Envoy: Virtual IP lookup<br/>240.240.0.1
    Envoy->>App: DNS Response<br/>240.240.0.1

    App->>Envoy: HTTP Request<br/>240.240.0.1:443
    Envoy->>Envoy: Actual host mapping<br/>api.example.com
    Envoy->>External: DNS lookup (actual IP)
    External->>Envoy: 203.0.113.10
    Envoy->>External: HTTP Request<br/>203.0.113.10:443
    External->>Envoy: Response
    Envoy->>App: Response
```

### 地址范围配置

默认使用 `240.240.0.0/16` 范围。如需更改：

```yaml
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  meshConfig:
    defaultConfig:
      proxyMetadata:
        ISTIO_META_DNS_CAPTURE: "true"
        ISTIO_META_DNS_AUTO_ALLOCATE: "true"
    # Change automatic allocation address range
    defaultServiceExportTo:
    - "*"
    # Address range (example, actually managed internally by Envoy)
    outboundTrafficPolicy:
      mode: ALLOW_ANY
```

### 验证已分配的 IP

```bash
# Check allocated virtual IP in Envoy config
istioctl proxy-config clusters <pod-name> -n <namespace> --fqdn api.example.com -o json

# Example output
{
  "name": "outbound|443||api.example.com",
  "type": "STRICT_DNS",
  "connectTimeout": "10s",
  "loadAssignment": {
    "clusterName": "outbound|443||api.example.com",
    "endpoints": [{
      "lbEndpoints": [{
        "endpoint": {
          "address": {
            "socketAddress": {
              "address": "240.240.0.1",  # Virtual IP
              "portValue": 443
            }
          }
        }
      }]
    }]
  }
}
```

## 故障排除

### 验证 DNS Proxy 运行情况

```bash
# 1. Check DNS Proxy environment variable
kubectl get pod <pod-name> -o jsonpath='{.spec.containers[?(@.name=="istio-proxy")].env[?(@.name=="ISTIO_META_DNS_CAPTURE")].value}'

# 2. Check iptables rules
kubectl exec -it <pod-name> -c istio-proxy -- iptables -t nat -L ISTIO_OUTPUT -n | grep 15053

# 3. Verify Envoy DNS Listener
istioctl proxy-config listeners <pod-name> --port 15053

# 4. DNS query test
kubectl exec -it <pod-name> -c app -- nslookup api.example.com

# 5. Check Envoy logs
kubectl logs <pod-name> -c istio-proxy | grep -i dns
```

### 常见问题

#### 问题 1：DNS 查询仍然发送到 CoreDNS

**原因**：DNS Proxy 未启用

**解决方案**：
```bash
# Check environment variable
kubectl get pod <pod-name> -o yaml | grep ISTIO_META_DNS_CAPTURE

# If not present, add annotation
kubectl patch deployment <deployment-name> -p '
spec:
  template:
    metadata:
      annotations:
        proxy.istio.io/config: |
          proxyMetadata:
            ISTIO_META_DNS_CAPTURE: "true"
'

# Restart pods
kubectl rollout restart deployment <deployment-name>
```

#### 问题 2：ServiceEntry 未反映在 DNS Proxy 中

**原因**：ServiceEntry 配置错误或 xDS 同步延迟

**解决方案**：
```bash
# Validate ServiceEntry
istioctl analyze serviceentry <name> -n <namespace>

# Check xDS sync
istioctl proxy-status

# Verify Envoy config
istioctl proxy-config clusters <pod-name> | grep <service-name>

# Force xDS resync
kubectl delete pod -n <namespace> <pod-name>
```

#### 问题 3：使用虚拟 IP 时连接失败

**原因**：地址冲突或路由问题

**解决方案**：
```bash
# Verify virtual IP allocation
istioctl proxy-config clusters <pod-name> --fqdn <service-host> -o json

# Check Listener config
istioctl proxy-config listeners <pod-name> --address 240.240.0.1

# Check Envoy logs
kubectl logs <pod-name> -c istio-proxy --tail=100 | grep -i "240.240"

# Test request
kubectl exec -it <pod-name> -c app -- curl -v http://240.240.0.1
```

### 调试工具

#### 使用 Envoy Admin API

```bash
# Port forward to pod
kubectl port-forward <pod-name> 15000:15000

# DNS Cache statistics
curl http://localhost:15000/stats | grep dns

# Cluster status
curl http://localhost:15000/clusters

# Full config dump
curl http://localhost:15000/config_dump > config.json
```

#### 数据包捕获

```bash
# Capture DNS traffic
kubectl exec -it <pod-name> -c istio-proxy -- tcpdump -i any -n port 53 -w /tmp/dns.pcap

# Download file
kubectl cp <pod-name>:/tmp/dns.pcap ./dns.pcap -c istio-proxy

# Analyze with Wireshark
wireshark dns.pcap
```

## 最佳实践

### 1. DNS Proxy 启用策略

**推荐方法**：渐进式发布

```mermaid
flowchart TD
    Start[Start] --> Test[Enable DNS Proxy<br/>in test environment]
    Test --> Validate{Validation<br/>successful?}
    Validate -->|No| Debug[Troubleshoot]
    Debug --> Test
    Validate -->|Yes| Stage[Apply to<br/>staging environment]
    Stage --> Monitor{Monitoring<br/>normal?}
    Monitor -->|No| Rollback[Rollback]
    Rollback --> Debug
    Monitor -->|Yes| Prod[Gradual application<br/>to production]
    Prod --> Complete[Complete]

    %% Style definitions
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;
    classDef success fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef warning fill:#FF9900,stroke:#333,stroke-width:1px,color:black;
    classDef error fill:#FF6B6B,stroke:#333,stroke-width:1px,color:white;

    %% Apply classes
    class Complete success;
    class Test,Stage,Prod warning;
    class Debug,Rollback error;
```

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
  - api.payment-provider.com
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
  - api.analytics-provider.com
  ports:
  - number: 443
    name: https
    protocol: HTTPS
  location: MESH_EXTERNAL
  resolution: DNS
```

### 3. DNS 缓存 TTL 配置

```yaml
# Adjust TTL based on service characteristics
apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata:
  name: dns-cache-ttl
  namespace: istio-system
spec:
  configPatches:
  # Static content (long TTL)
  - applyTo: CLUSTER
    match:
      cluster:
        service: cdn.static-assets.com
    patch:
      operation: MERGE
      value:
        dns_refresh_rate: 300s  # 5 minutes

  # Dynamic API (short TTL)
  - applyTo: CLUSTER
    match:
      cluster:
        service: api.dynamic-service.com
    patch:
      operation: MERGE
      value:
        dns_refresh_rate: 10s  # 10 seconds
```

### 4. 监控指标

```promql
# DNS Proxy activity
sum(rate(envoy_dns_cache_dns_query_attempt[5m])) by (pod)

# DNS Cache hit rate
sum(rate(envoy_dns_cache_hit[5m]))
/
sum(rate(envoy_dns_cache_dns_query_attempt[5m]))
* 100

# DNS lookup latency
histogram_quantile(0.99,
  sum(rate(envoy_dns_cache_dns_query_duration_bucket[5m])) by (le)
)

# DNS lookup failure rate
sum(rate(envoy_dns_cache_dns_query_failure[5m]))
/
sum(rate(envoy_dns_cache_dns_query_attempt[5m]))
* 100
```

### 5. 安全注意事项

```yaml
# Integrate DNS Proxy with AuthorizationPolicy
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: external-api-access
  namespace: default
spec:
  selector:
    matchLabels:
      app: frontend
  action: ALLOW
  rules:
  - to:
    - operation:
        hosts:
        - api.approved-partner.com  # Only approved external services
        - cdn.trusted-cdn.com
        ports:
        - "443"
---
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: deny-all-external
  namespace: default
spec:
  action: DENY
  rules:
  - to:
    - operation:
        notHosts:
        - "*.svc.cluster.local"  # Deny all requests not to cluster internal
```

### 6. 性能调优

```yaml
# Optimization for high performance environments
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  meshConfig:
    defaultConfig:
      proxyMetadata:
        ISTIO_META_DNS_CAPTURE: "true"
        ISTIO_META_DNS_AUTO_ALLOCATE: "true"
      concurrency: 4  # Envoy worker thread count
  components:
    pilot:
      k8s:
        resources:
          requests:
            cpu: 500m
            memory: 2Gi
          limits:
            cpu: 2000m
            memory: 4Gi
        hpaSpec:
          minReplicas: 2
          maxReplicas: 5
```

## 参考资料

### 官方文档
- [Istio DNS Proxy](https://istio.io/latest/docs/ops/configuration/traffic-management/dns-proxy/)
- [Envoy DNS 缓存](https://www.envoyproxy.io/docs/envoy/latest/intro/arch_overview/upstream/service_discovery#dns-cache)
- [ServiceEntry](https://istio.io/latest/docs/reference/config/networking/service-entry/)

### 相关文档
- [Istio 架构 - DNS 处理机制](../03-architecture.md#dns-processing-mechanism)
- [ServiceEntry](../traffic-management/12-service-entry.md)
- [出口控制](../traffic-management/11-egress-control.md)
