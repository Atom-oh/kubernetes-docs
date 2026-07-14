# Istio 测验

> **支持的版本**: Istio 1.28.0
> **EKS 版本**: 1.34 (Kubernetes 1.28+)
> **最后更新**: February 19, 2026

本测验用于测试你对 Istio 服务网格的理解。

## 问题 1：服务网格基本概念

<details>
<summary>什么是服务网格，它的主要功能有哪些？</summary>

**答案：**
服务网格是一种处理服务间通信的基础设施层，使你无需修改应用程序代码即可控制和观测服务之间的通信。

**主要功能：**
1. **流量管理**：控制服务之间的流量
   - 路由、负载均衡、Canary 部署
   - 超时、重试、Circuit Breaker
   - 流量镜像和影子测试

2. **安全性**：服务间通信的加密和身份验证
   - 自动 mTLS（双向 TLS）
   - Authorization Policy（访问控制）
   - Request Authentication（JWT）

3. **可观测性**：服务间通信的可见性
   - 指标收集（Prometheus）
   - 分布式追踪（Jaeger/Zipkin）
   - 日志和可视化（Kiali、Grafana）

**Istio 特性：**
- 可透明地部署在现有的分布式应用程序之上
- 使用 Sidecar Proxy 模式（Envoy）
- 支持 Ambient Mode（无 Sidecar 架构）
- 通过声明式配置进行策略管理
</details>

## 问题 2：Istio 架构

<details>
<summary>Istio 1.28.0 中的主要组件和角色是什么？</summary>

**答案：**
**Control Plane：**
- **Istiod**：单一二进制文件中的统一 Control Plane
  - **Service Discovery**：维护网格 Service 注册表
  - **Configuration Management**：存储并分发 Istio 配置
  - **Certificate Management**：为 mTLS 生成和轮换证书

**Data Plane：**
- **Envoy Proxy**：以 Sidecar 形式部署，处理所有网络通信
  - 流量路由和负载均衡
  - mTLS 加密和身份验证
  - 指标、日志和追踪收集

**Ambient Mode（可选）：**
- **ztunnel**：Node 级别 Proxy（L4）
- **waypoint proxy**：可选的 L7 Proxy

**关键特性：**
- 单一二进制文件中的统一 Control Plane（Istiod）
- 可扩展且高可用的架构
- 基于 Kubernetes 原生 CRD 的配置
- 使用 Ambient Mode 可减少 85% 以上的资源消耗
</details>

## 问题 3：流量管理与 Argo Rollouts 集成

<details>
<summary>如何使用 Istio 和 Argo Rollouts 实现自动化 Canary 部署？</summary>

**答案：**
Argo Rollouts 与 Istio 集成，以提供基于指标的自动 Canary 部署。

**1. Rollout 资源定义：**
```yaml
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: reviews
spec:
  replicas: 5
  strategy:
    canary:
      # Istio traffic control
      trafficRouting:
        istio:
          virtualService:
            name: reviews-vsvc
            routes:
            - primary
          destinationRule:
            name: reviews-destrule
            canarySubsetName: canary
            stableSubsetName: stable

      # Staged deployment
      steps:
      - setWeight: 10    # 10% Canary
      - pause: {duration: 2m}
      - setWeight: 25    # 25% Canary
      - pause: {duration: 2m}
      - setWeight: 50    # 50% Canary
      - pause: {duration: 2m}

      # Automatic metrics analysis
      analysis:
        templates:
        - templateName: success-rate
        - templateName: latency
        startingStep: 1
```

**2. AnalysisTemplate - 自动回滚：**
```yaml
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: success-rate
spec:
  metrics:
  - name: success-rate
    successCondition: result >= 0.95  # 95% or higher
    failureLimit: 2  # Auto-rollback after 2 failures
    provider:
      prometheus:
        query: |
          sum(rate(istio_requests_total{
            response_code!~"5.*"
          }[2m])) / sum(rate(istio_requests_total[2m]))
```

**关键特性：**
- 基于指标的自动推进/回滚
- 逐步增加流量（10% → 25% → 50% → 100%）
- 实时 Prometheus 指标分析
- 发生故障时立即自动回滚
</details>

## 问题 4：安全功能

<details>
<summary>Istio 1.28.0 中的 mTLS 和 Authorization Policy 功能是什么？</summary>

**答案：**
**mTLS 优势：**
- 自动加密服务间通信
- 通过双向身份验证增强安全性
- 无需更改应用程序代码即可应用
- 自动签发和续期证书

**1. PeerAuthentication - mTLS 策略：**
```yaml
apiVersion: security.istio.io/v1beta1
kind: PeerAuthentication
metadata:
  name: default
  namespace: istio-system
spec:
  mtls:
    mode: STRICT  # STRICT recommended for production
```

**2. AuthorizationPolicy - 细粒度访问控制：**
```yaml
# Deny by default
apiVersion: security.istio.io/v1beta1
kind: AuthorizationPolicy
metadata:
  name: deny-all
spec: {}  # Deny all requests

---
# Allow specific
apiVersion: security.istio.io/v1beta1
kind: AuthorizationPolicy
metadata:
  name: allow-frontend
spec:
  selector:
    matchLabels:
      app: backend
  action: ALLOW
  rules:
  - from:
    - source:
        principals: ["cluster.local/ns/default/sa/frontend"]
    to:
    - operation:
        methods: ["GET", "POST"]
        paths: ["/api/*"]
```

**3. RequestAuthentication - JWT 验证：**
```yaml
apiVersion: security.istio.io/v1beta1
kind: RequestAuthentication
metadata:
  name: jwt-auth
spec:
  jwtRules:
  - issuer: "https://auth.example.com"
    jwksUri: "https://auth.example.com/.well-known/jwks.json"
```

**最佳实践：**
- 使用默认拒绝策略
- 应用最小权限原则
- 基于 Service Account 的身份验证
- Namespace 隔离
</details>

## 问题 5：Gateway 和 Ingress

<details>
<summary>Istio Gateway 的作用是什么，如何配置 TLS？</summary>

**答案：**
**Gateway 作用：**
- 外部流量进入集群内部 Service 的入口点
- Ingress/Egress 流量控制
- TLS 终止和证书管理
- Load Balancer 集成

**配置示例：**
```yaml
# Gateway Definition
apiVersion: networking.istio.io/v1beta1
kind: Gateway
metadata:
  name: bookinfo-gateway
spec:
  selector:
    istio: ingressgateway
  servers:
  # HTTPS (443)
  - port:
      number: 443
      name: https
      protocol: HTTPS
    tls:
      mode: SIMPLE
      credentialName: bookinfo-secret
    hosts:
    - bookinfo.example.com

  # HTTP (80) - Redirect to HTTPS
  - port:
      number: 80
      name: http
      protocol: HTTP
    hosts:
    - "*"
    tls:
      httpsRedirect: true

---
# VirtualService - Connect to Gateway
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: bookinfo-vs
spec:
  hosts:
  - bookinfo.example.com
  gateways:
  - bookinfo-gateway
  http:
  - match:
    - uri:
        prefix: /productpage
    route:
    - destination:
        host: productpage
        port:
          number: 9080
    timeout: 10s
    retries:
      attempts: 3
      perTryTimeout: 2s
```

**TLS 证书创建：**
```bash
# Create TLS certificate as Kubernetes Secret
kubectl create -n istio-system secret tls bookinfo-secret \
  --key=bookinfo.key \
  --cert=bookinfo.crt
```
</details>

## 问题 6：可观测性工具

<details>
<summary>Istio 1.28.0 提供哪些可观测性工具，它们的作用是什么？</summary>

**答案：**
**1. Prometheus - 指标收集：**
```promql
# Golden Signals Monitoring
# 1. Latency (P95)
histogram_quantile(0.95,
  sum(rate(istio_request_duration_milliseconds_bucket[5m])) by (le)
)

# 2. Traffic (Request count)
sum(rate(istio_requests_total[5m]))

# 3. Errors (Error rate)
sum(rate(istio_requests_total{response_code=~"5.."}[5m]))
/ sum(rate(istio_requests_total[5m]))

# 4. Saturation (CPU usage)
sum(rate(container_cpu_usage_seconds_total{pod=~".*istio-proxy.*"}[5m]))
```

**2. Jaeger - 分布式追踪：**
```yaml
# Enable Tracing
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  meshConfig:
    defaultConfig:
      tracing:
        sampling: 100.0  # 100% sampling
```

**3. Kiali - 服务网格可视化：**
- 实时拓扑可视化
- 流量流向分析
- 配置验证
- 性能指标展示

**4. Grafana - 仪表板：**
- Istio Service Dashboard
- Istio Workload Dashboard
- Istio Performance Dashboard
- 自定义仪表板创建

**访问方式：**
```bash
istioctl dashboard kiali
istioctl dashboard prometheus
istioctl dashboard grafana
istioctl dashboard jaeger
```
</details>

## 问题 7：Ambient Mode

<details>
<summary>Istio 1.28.0 中的 Ambient Mode 是什么，它与 Sidecar Mode 有何不同？</summary>

**答案：**
**Ambient Mode 概念：**
- 无 Sidecar 的服务网格架构
- ztunnel（Node 级 L4 Proxy）+ waypoint（可选 L7 Proxy）
- 减少 85% 以上的资源消耗

**架构比较：**

| 功能 | Sidecar Mode | Ambient Mode |
|---------|-------------|--------------|
| 部署方式 | 每个 Pod 注入 Envoy | 每个 Node 1 个 ztunnel |
| 资源使用量 | 高（每个 Pod 50-100MB） | 低（每个 Node 50MB） |
| 部署复杂度 | 高（需要重新部署） | 低（对应用程序透明） |
| L4 功能 | 支持 | 通过 ztunnel 支持 |
| L7 功能 | 完整支持 | 需要 waypoint |
| 性能 | 略慢 | 快（仅 L4） |

**Ambient Mode 激活：**
```bash
# Install Ambient Mode
istioctl install --set profile=ambient -y

# Enable Ambient Mode on Namespace
kubectl label namespace default istio.io/dataplane-mode=ambient
```

**使用场景：**
- 资源受限的环境
- 大规模集群（1000+ Pod）
- 仅需要 L4 功能时
- 逐步采用 Istio
</details>

## 问题 8：弹性模式

<details>
<summary>Istio 中的 Outlier Detection、Circuit Breaker 和 Rate Limiting 有何区别？</summary>

**答案：**
**1. Outlier Detection - 排除不健康实例：**
```yaml
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: reviews
spec:
  host: reviews
  trafficPolicy:
    outlierDetection:
      consecutiveErrors: 5       # 5 consecutive failures
      interval: 30s              # Evaluate every 30s
      baseEjectionTime: 30s      # 30s ejection
      maxEjectionPercent: 50     # Max 50% ejection
```

**2. Circuit Breaker - 防止过载：**
```yaml
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: reviews
spec:
  host: reviews
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 100
      http:
        http1MaxPendingRequests: 50
        maxRequestsPerConnection: 2
```

**3. Rate Limiting - 请求速率控制：**
```yaml
# Local Rate Limiting
apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata:
  name: local-rate-limit
spec:
  configPatches:
  - applyTo: HTTP_FILTER
    patch:
      operation: INSERT_BEFORE
      value:
        name: envoy.filters.http.local_ratelimit
        typed_config:
          stat_prefix: http_local_rate_limiter
          token_bucket:
            max_tokens: 100
            tokens_per_fill: 10
            fill_interval: 1s
```

**区别：**
- **Outlier Detection**：响应式（故障后排除）
- **Circuit Breaker**：预防式（限制连接）
- **Rate Limiting**：请求速率控制（令牌桶）

**组合使用：**
```yaml
trafficPolicy:
  connectionPool:     # Circuit Breaker
    tcp:
      maxConnections: 100
  outlierDetection:   # Outlier Detection
    consecutiveErrors: 5
```
</details>

## 问题 9：本地性负载均衡（Zone Aware Routing）

<details>
<summary>Istio 的本地性负载均衡功能是什么，如何与 AWS EKS 配合使用？</summary>

**答案：**
**本地性负载均衡概念：**
- 优先路由到同一 Availability Zone（AZ）中的 Service
- 降低网络延迟
- 节省跨 AZ 数据传输成本（约 85%）

**配置：**
```yaml
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: reviews
spec:
  host: reviews
  trafficPolicy:
    loadBalancer:
      localityLbSetting:
        enabled: true
        distribute:
        # Same AZ priority, other AZ for failover
        - from: us-east-1/us-east-1a/*
          to:
            "us-east-1/us-east-1a/*": 80  # Same AZ 80%
            "us-east-1/us-east-1b/*": 20  # Other AZ 20%

        # Failover policy
        failover:
        - from: us-east-1
          to: us-west-2
```

**AWS EKS 使用方式：**
1. **节省成本：**
   - 跨 AZ 流量：$0.01/GB
   - 同一 AZ 流量：免费
   - 通过 80% 同 AZ 路由显著节省成本

2. **性能提升：**
   - AZ 内延迟：约 1ms
   - 跨 AZ 延迟：约 2-3ms

3. **自动故障转移：**
   - AZ 故障时自动故障转移到其他 AZ
   - 与 Outlier Detection 结合使用

**Pod 拓扑配置：**
```yaml
# EKS nodes automatically set topology labels
topology.kubernetes.io/region: us-east-1
topology.kubernetes.io/zone: us-east-1a
```
</details>

## 问题 10：Amazon EKS 集成和最佳实践

<details>
<summary>将 Istio 1.28.0 与 Amazon EKS 1.34 集成时有哪些注意事项和最佳实践？</summary>

**答案：**
**1. 安装和配置：**
```bash
# Install Istioctl
curl -L https://istio.io/downloadIstio | sh -
cd istio-1.28.0
export PATH=$PWD/bin:$PATH

# Install with production profile
istioctl install --set profile=production -y
```

**2. AWS Load Balancer 集成：**
```yaml
apiVersion: v1
kind: Service
metadata:
  name: istio-ingressgateway
  namespace: istio-system
  annotations:
    # Network Load Balancer
    service.beta.kubernetes.io/aws-load-balancer-type: "nlb"
    service.beta.kubernetes.io/aws-load-balancer-cross-zone-load-balancing-enabled: "true"

    # TLS termination (ACM certificate)
    service.beta.kubernetes.io/aws-load-balancer-ssl-cert: "arn:aws:acm:region:account:certificate/id"
    service.beta.kubernetes.io/aws-load-balancer-ssl-ports: "443"
spec:
  type: LoadBalancer
```

**3. 资源优化：**
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
          minReplicas: 2
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
            memory: 1024Mi
```

**4. 安全配置：**
```yaml
# VPC Security Group settings
# - Istiod: 15010, 15012, 8080
# - Envoy: 15001, 15006, 15021, 15090
# - Gateway: 80, 443

# IAM Role (IRSA)
apiVersion: v1
kind: ServiceAccount
metadata:
  name: istio-ingressgateway
  namespace: istio-system
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::account:role/istio-gateway
```

**5. 监控集成：**
```yaml
# CloudWatch Container Insights
apiVersion: v1
kind: ConfigMap
metadata:
  name: fluent-bit-config
data:
  output.conf: |
    [OUTPUT]
        Name cloudwatch_logs
        Match *
        region us-east-1
        log_group_name /aws/eks/cluster/istio
```

**6. 最佳实践：**
- 使用生产配置文件
- Control Plane HA（副本数 >= 3）
- mTLS STRICT 模式
- PodDisruptionBudget 配置
- 启用本地性负载均衡
- Prometheus + Grafana 监控
- 定期版本升级（Canary 方法）

**7. 成本优化：**
- 考虑 Ambient Mode（减少 85% 的资源消耗）
- 本地性负载均衡（节省跨 AZ 成本）
- 限制 Sidecar Scope（减少 30-50% 内存）
</details>

## 加分问题：渐进式交付

<details>
<summary>如何使用 Istio + Argo Rollouts 实现全自动的渐进式交付？</summary>

**答案：**
渐进式交付是一种根据指标自动推进或回滚部署的方法。

**完整自动化示例：**
```yaml
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: myapp
spec:
  replicas: 10
  strategy:
    canary:
      trafficRouting:
        istio:
          virtualService:
            name: myapp-vsvc
            routes:
            - primary

      steps:
      # Stage 1: 10% Canary
      - setWeight: 10
      - pause: {duration: 1m}
      - analysis:
          templates:
          - templateName: success-rate
          - templateName: latency

      # Stage 2: 25% Canary (auto-progress)
      - setWeight: 25
      - pause: {duration: 1m}
      - analysis:
          templates:
          - templateName: success-rate
          - templateName: latency

      # Stage 3: 50% Canary (auto-progress)
      - setWeight: 50
      - pause: {duration: 2m}
      - analysis:
          templates:
          - templateName: success-rate
          - templateName: latency

      # Stage 4: 100% Canary (auto-complete)
```

**自动回滚条件：**
```yaml
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: success-rate
spec:
  metrics:
  - name: success-rate
    interval: 30s
    count: 4
    successCondition: result >= 0.95
    failureLimit: 2  # Immediate rollback after 2 failures
    provider:
      prometheus:
        query: |
          # Success rate < 95% or
          # Latency > 500ms or
          # Error rate > 5%
          # → Auto rollback
```

**主要优势：**
- 完全自动化（无需人工干预）
- 立即回滚（检测到故障后数秒内）
- 安全部署（基于指标的验证）
- 流程一致（标准化）
</details>

---

**评分：**
- 答对 10-11 题：优秀（Istio 专家级）
- 答对 8-9 题：良好（具备生产环境运维能力）
- 答对 6-7 题：一般（建议进一步学习）
- 答对 4-5 题：不足（需要复习基本概念）
- 答对 0-3 题：需要重新学习

**学习资源：**
- [Istio 官方文档](https://istio.io/latest/docs/)
- [Argo Rollouts 文档](https://argo-rollouts.readthedocs.io/)
- [EKS Workshop - Istio](https://www.eksworkshop.com/docs/security/servicemesh/)
- [本指南中的详细文档](../../service-mesh/istio/)
