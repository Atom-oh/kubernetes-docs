# Istio 最佳实践

本文档涵盖了在生产环境中成功运行 Istio 的最佳实践和建议。

## 目录

1. [性能优化](#performance-optimization)
2. [安全加固](#security-hardening)
3. [运维指南](#operations-guide)
4. [监控与可观测性](#monitoring-and-observability)
5. [生产环境检查清单](#production-checklist)

## 性能优化

### 1. Control Plane 资源优化

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
          limits:
            cpu: 1000m
            memory: 4Gi
        hpaSpec:
          minReplicas: 2
          maxReplicas: 5
          metrics:
          - type: Resource
            resource:
              name: cpu
              target:
                type: Utilization
                averageUtilization: 80
```

**建议**：
- Istiod 应至少有 2 个副本
- CPU：根据集群规模调整
- 内存：估算每个 Service 约 10KB

### 2. Data Plane 资源优化

```yaml
apiVersion: v1
kind: Pod
metadata:
  annotations:
    # Sidecar resource optimization
    sidecar.istio.io/proxyCPU: "100m"
    sidecar.istio.io/proxyMemory: "128Mi"
    sidecar.istio.io/proxyCPULimit: "200m"
    sidecar.istio.io/proxyMemoryLimit: "256Mi"
spec:
  containers:
  - name: myapp
    image: myapp:latest
```

**建议**：
- 常规工作负载：CPU 100m，内存 128Mi
- 高流量工作负载：CPU 500m，内存 512Mi
- Sidecar 并发度：`concurrency: 2`（默认值）

### 3. 连接池优化

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: optimized-pool
spec:
  host: myapp
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 100
        connectTimeout: 30ms
      http:
        http1MaxPendingRequests: 50
        http2MaxRequests: 100
        maxRequestsPerConnection: 2
        idleTimeout: 300s
```

**建议**：
- `maxConnections`：考虑工作负载的并发连接数
- `maxRequestsPerConnection`：HTTP/1.1 使用 1-2，HTTP/2 可使用更高值
- `idleTimeout`：如果需要长连接，则增加该值

### 4. 本地性负载均衡

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: locality-lb
spec:
  host: myapp
  trafficPolicy:
    loadBalancer:
      localityLbSetting:
        enabled: true
        distribute:
        - from: us-east-1/us-east-1a/*
          to:
            "us-east-1/us-east-1a/*": 80  # Same AZ priority
            "us-east-1/us-east-1b/*": 20
```

**优势**：
- 降低跨 AZ 成本（约 85%）
- 降低网络延迟
- 自动处理可用区故障

### 5. 限制 Sidecar 范围

```yaml
apiVersion: networking.istio.io/v1
kind: Sidecar
metadata:
  name: default
  namespace: default
spec:
  egress:
  - hosts:
    - "default/*"
    - "istio-system/*"
```

**优势**：
- 减小 Envoy 配置大小
- 降低内存使用量
- 加快配置推送

## 安全加固

### 1. 应用严格 mTLS

```yaml
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: default
  namespace: istio-system
spec:
  mtls:
    mode: STRICT  # STRICT recommended for production
```

**检查清单**：
- 对所有 Service 应用 STRICT mTLS
- 仅在迁移期间使用 PERMISSIVE
- 对外部 Service 使用 DISABLE（在 ServiceEntry 中处理）

### 2. 授权策略

```yaml
# Deny by default
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: deny-all
  namespace: default
spec: {}  # Deny all requests
---
# Allow specific
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: allow-frontend
  namespace: default
spec:
  selector:
    matchLabels:
      app: backend
  action: ALLOW
  rules:
  - from:
    - source:
        principals: ["cluster.local/ns/default/sa/frontend"]
```

**最佳实践**：
- 使用默认拒绝策略
- 应用最小权限原则
- 基于 Service Account 的认证
- Namespace 隔离

### 3. 出站流量控制

```yaml
# Block external traffic
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  meshConfig:
    outboundTrafficPolicy:
      mode: REGISTRY_ONLY  # Allow only explicit ServiceEntries
---
# Allowed external services
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: external-api
spec:
  hosts:
  - api.external.com
  ports:
  - number: 443
    name: https
    protocol: HTTPS
  location: MESH_EXTERNAL
  resolution: DNS
```

### 4. JWT 认证

```yaml
apiVersion: security.istio.io/v1
kind: RequestAuthentication
metadata:
  name: jwt-auth
spec:
  selector:
    matchLabels:
      app: api-service
  jwtRules:
  - issuer: "https://auth.example.com"
    jwksUri: "https://auth.example.com/.well-known/jwks.json"
---
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: require-jwt
spec:
  selector:
    matchLabels:
      app: api-service
  action: ALLOW
  rules:
  - when:
    - key: request.auth.claims[iss]
      values: ["https://auth.example.com"]
```

## 运维指南

### 1. 部署策略

#### 渐进式采用 Istio

```mermaid
flowchart LR
    Start[Start]
    Phase1[Phase 1<br/>Observability]
    Phase2[Phase 2<br/>mTLS PERMISSIVE]
    Phase3[Phase 3<br/>mTLS STRICT]
    Phase4[Phase 4<br/>Advanced Features]
    End[Full Adoption]

    Start --> Phase1
    Phase1 --> Phase2
    Phase2 --> Phase3
    Phase3 --> Phase4
    Phase4 --> End

    %% Style definition
    classDef phase fill:#326CE5,stroke:#333,stroke-width:1px,color:white;

    %% Class application
    class Start,Phase1,Phase2,Phase3,Phase4,End phase;
```

**阶段 1：可观测性（1-2 周）**
```bash
# Enable sidecar injection only
kubectl label namespace default istio-injection=enabled

# Verify metrics, logs, traces
# Evaluate performance impact
```

**阶段 2：mTLS PERMISSIVE（1-2 周）**
```yaml
# Enable PERMISSIVE mode
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: default
spec:
  mtls:
    mode: PERMISSIVE
```

**阶段 3：mTLS STRICT（1 周）**
```yaml
# Switch to STRICT mode
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: default
spec:
  mtls:
    mode: STRICT
```

**阶段 4：高级功能（持续进行）**
- 流量管理（Canary、Circuit Breaker）
- Authorization Policy
- 限流

### 2. 升级策略

#### Canary 升级

```bash
# 1. Install new version Control Plane
istioctl install --set revision=1-28-0 -y

# 2. Move test namespace
kubectl label namespace test istio.io/rev=1-28-0 --overwrite
kubectl rollout restart deployment -n test

# 3. Move production after verification
kubectl label namespace prod istio.io/rev=1-28-0 --overwrite
kubectl rollout restart deployment -n prod

# 4. Remove previous version
istioctl uninstall --revision=1-27-0 -y
```

### 3. 高可用性

```yaml
# Control Plane HA
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  components:
    pilot:
      k8s:
        replicaCount: 3
        podAntiAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
          - labelSelector:
              matchLabels:
                app: istiod
            topologyKey: kubernetes.io/hostname
```

**建议**：
- Istiod：至少 3 个副本
- 在各 AZ 之间均匀分布
- 设置 PodDisruptionBudget

### 4. 备份与恢复

```bash
# Backup Istio configuration
kubectl get istiooperator -A -o yaml > istio-operator-backup.yaml
kubectl get vs,dr,gw,se,pa,ra,ap -A -o yaml > istio-config-backup.yaml

# Recovery
kubectl apply -f istio-operator-backup.yaml
kubectl apply -f istio-config-backup.yaml
```

## 监控与可观测性

### 1. 黄金信号

```promql
# 1. Latency (P50, P95, P99)
histogram_quantile(0.95,
  sum(rate(istio_request_duration_milliseconds_bucket[5m])) by (le)
)

# 2. Traffic (Request count)
sum(rate(istio_requests_total[5m]))

# 3. Errors (Error rate)
sum(rate(istio_requests_total{response_code=~"5.."}[5m]))
/
sum(rate(istio_requests_total[5m]))

# 4. Saturation (Resource utilization)
sum(rate(container_cpu_usage_seconds_total{pod=~".*istio-proxy.*"}[5m]))
```

### 2. Control Plane 监控

```promql
# Pilot configuration push time
pilot_proxy_convergence_time

# xDS connection count
pilot_xds_pushes

# Memory usage
process_resident_memory_bytes{app="istiod"}
```

### 3. Data Plane 监控

```promql
# Envoy connection count
envoy_cluster_upstream_cx_active

# Circuit Breaker open
envoy_cluster_circuit_breakers_default_rq_open

# Outlier Detection
envoy_cluster_outlier_detection_ejections_active
```

### 4. 告警规则

```yaml
groups:
- name: istio
  rules:
  # High error rate
  - alert: HighErrorRate
    expr: |
      (sum(rate(istio_requests_total{response_code=~"5.."}[5m]))
      /
      sum(rate(istio_requests_total[5m]))) > 0.05
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High error rate detected"

  # High latency
  - alert: HighLatency
    expr: |
      histogram_quantile(0.95,
        sum(rate(istio_request_duration_milliseconds_bucket[5m])) by (le)
      ) > 1000
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High latency detected (P95 > 1s)"

  # Pilot not ready
  - alert: PilotNotReady
    expr: up{job="pilot"} == 0
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: "Pilot is not ready"
```

## 生产环境检查清单

### 安装前

- [ ] 验证 Kubernetes 版本兼容性（1.28+）
- [ ] 选择 Istio 版本（建议使用稳定版本）
- [ ] 计算资源需求
- [ ] 审查网络策略
- [ ] 制定备份与恢复计划

### 安装

- [ ] 使用生产环境 profile
- [ ] 配置 Control Plane HA（副本数 >= 3）
- [ ] 设置资源限制
- [ ] 设置 PodDisruptionBudget
- [ ] 准备监控栈

### 安全

- [ ] 启用 mTLS STRICT 模式
- [ ] 应用 Authorization Policy
- [ ] 控制出站流量
- [ ] 配置 JWT 认证（如需要）
- [ ] 集成 Network Policy

### 流量管理

- [ ] 配置 VirtualService
- [ ] 配置 DestinationRule
- [ ] 设置 Circuit Breaker
- [ ] 设置 Retry/Timeout
- [ ] 配置限流

### 可观测性

- [ ] 集成 Prometheus
- [ ] 设置 Grafana 仪表板
- [ ] 设置 Jaeger/Zipkin 追踪
- [ ] 安装 Kiali
- [ ] 设置告警规则

### 运维

- [ ] 制定升级计划
- [ ] 自动化备份
- [ ] 文档编写
- [ ] 编写值班指南
- [ ] 准备运行手册

### 性能

- [ ] 优化 Sidecar 资源
- [ ] 调优连接池
- [ ] 配置本地性负载均衡
- [ ] 限制 Sidecar 范围
- [ ] 执行性能测试

### 测试

- [ ] 功能测试
- [ ] 性能测试
- [ ] 灾难恢复测试
- [ ] 混沌工程
- [ ] 升级场景测试

## 常见反模式

### 应避免的事项

1. **一次性采用全部功能**
   ```
   Don't enable all Istio features on Day 1
   Do add features gradually (Observability -> Security -> Traffic Management)
   ```

2. **未设置资源限制**
   ```yaml
   Don't leave Sidecar without resource limits
   Do set appropriate requests/limits
   ```

3. **长期使用 PERMISSIVE 模式**
   ```
   Don't keep using PERMISSIVE
   Do transition to STRICT quickly
   ```

4. **滥用通配符匹配**
   ```yaml
   Don't: hosts: ["*"]  # All services
   Do: hosts: ["myapp.default.svc.cluster.local"]  # Explicit
   ```

5. **未监控即部署**
   ```
   Don't deploy to production without checking metrics
   Do require Golden Signals monitoring
   ```

## 成本优化

### 1. 考虑 Ambient Mode

```yaml
# Resource usage comparison
# Sidecar Mode: 100 pods x 50MB = 5GB
# Ambient Mode: 10 nodes x 50MB = 500MB

# 85%+ reduction possible
```

### 2. 本地性负载均衡

```yaml
# Cross-AZ cost savings
# AWS: $0.01-0.02 per GB
# Significant savings with 80% same AZ routing
```

### 3. 限制 Sidecar 范围

```yaml
# Remove unnecessary configuration
# 30-50% memory usage reduction possible
```

## 参考资料

### 官方文档
- [Istio 最佳实践](https://istio.io/latest/docs/ops/best-practices/)
- [性能与可扩展性](https://istio.io/latest/docs/ops/deployment/performance-and-scalability/)
- [安全最佳实践](https://istio.io/latest/docs/ops/best-practices/security/)

### 社区
- [Istio Discuss](https://discuss.istio.io/)
- [Istio Slack](https://istio.slack.com/)
- [GitHub Issues](https://github.com/istio/istio/issues)

### 其他资源
- [生产环境中的 Istio](https://www.tetrate.io/blog/istio-in-production/)
- [Service Mesh 模式](https://www.oreilly.com/library/view/service-mesh-patterns/9781492086444/)
