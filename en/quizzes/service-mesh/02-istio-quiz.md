# Istio Quiz

> **Supported Version**: Istio 1.28.0
> **EKS Version**: 1.34 (Kubernetes 1.28+)
> **Last Updated**: February 19, 2026

This quiz tests your understanding of the Istio service mesh.

## Question 1: Service Mesh Basic Concepts

<details>
<summary>What is a service mesh and what are its main features?</summary>

**Answer:**
A service mesh is an infrastructure layer that handles service-to-service communication, enabling you to control and observe communication between services without modifying application code.

**Main Features:**
1. **Traffic Management**: Control traffic flow between services
   - Routing, load balancing, canary deployments
   - Timeout, Retry, Circuit Breaker
   - Traffic mirroring and shadow testing

2. **Security**: Encryption and authentication for service-to-service communication
   - Automatic mTLS (mutual TLS)
   - Authorization Policy (access control)
   - Request Authentication (JWT)

3. **Observability**: Visibility into service-to-service communication
   - Metrics collection (Prometheus)
   - Distributed tracing (Jaeger/Zipkin)
   - Logging and visualization (Kiali, Grafana)

**Istio Characteristics:**
- Transparently layers onto existing distributed applications
- Uses sidecar proxy pattern (Envoy)
- Supports Ambient Mode (sidecar-less architecture)
- Policy management through declarative configuration
</details>

## Question 2: Istio Architecture

<details>
<summary>What are the main components and roles in Istio 1.28.0?</summary>

**Answer:**
**Control Plane:**
- **Istiod**: Unified control plane in a single binary
  - **Service Discovery**: Maintains mesh service registry
  - **Configuration Management**: Stores and distributes Istio configuration
  - **Certificate Management**: Generates and rotates certificates for mTLS

**Data Plane:**
- **Envoy Proxy**: Deployed as sidecar, mediates all network communication
  - Traffic routing and load balancing
  - mTLS encryption and authentication
  - Metrics, logs, and traces collection

**Ambient Mode (optional):**
- **ztunnel**: Node-level proxy (L4)
- **waypoint proxy**: Optional L7 proxy

**Key Features:**
- Unified control plane in single binary (Istiod)
- Scalable and highly available architecture
- Kubernetes-native CRD-based configuration
- 85%+ resource reduction possible with Ambient Mode
</details>

## Question 3: Traffic Management and Argo Rollouts Integration

<details>
<summary>How do you implement automated canary deployments using Istio and Argo Rollouts?</summary>

**Answer:**
Argo Rollouts integrates with Istio to provide metrics-based automatic canary deployments.

**1. Rollout Resource Definition:**
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

**2. AnalysisTemplate - Automatic Rollback:**
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

**Key Features:**
- Metrics-based automatic progression/rollback
- Gradual traffic increase (10% → 25% → 50% → 100%)
- Real-time Prometheus metrics analysis
- Immediate automatic rollback on failure
</details>

## Question 4: Security Features

<details>
<summary>What are mTLS and Authorization Policy features in Istio 1.28.0?</summary>

**Answer:**
**mTLS Benefits:**
- Automatic encryption of service-to-service communication
- Enhanced security through mutual authentication
- Applied without application code changes
- Automatic certificate issuance and renewal

**1. PeerAuthentication - mTLS Policy:**
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

**2. AuthorizationPolicy - Fine-grained Access Control:**
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

**3. RequestAuthentication - JWT Validation:**
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

**Best Practices:**
- Use deny-by-default policies
- Apply least privilege principle
- Service Account-based authentication
- Namespace isolation
</details>

## Question 5: Gateway and Ingress

<details>
<summary>What is the role of Istio Gateway and how do you configure TLS?</summary>

**Answer:**
**Gateway Role:**
- Entry point for external traffic into cluster internal services
- Ingress/Egress traffic control
- TLS termination and certificate management
- Load balancer integration

**Configuration Example:**
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

**TLS Certificate Creation:**
```bash
# Create TLS certificate as Kubernetes Secret
kubectl create -n istio-system secret tls bookinfo-secret \
  --key=bookinfo.key \
  --cert=bookinfo.crt
```
</details>

## Question 6: Observability Tools

<details>
<summary>What observability tools does Istio 1.28.0 provide and what are their roles?</summary>

**Answer:**
**1. Prometheus - Metrics Collection:**
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

**2. Jaeger - Distributed Tracing:**
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

**3. Kiali - Service Mesh Visualization:**
- Real-time topology visualization
- Traffic flow analysis
- Configuration validation
- Performance metrics display

**4. Grafana - Dashboards:**
- Istio Service Dashboard
- Istio Workload Dashboard
- Istio Performance Dashboard
- Custom dashboard creation

**Access Method:**
```bash
istioctl dashboard kiali
istioctl dashboard prometheus
istioctl dashboard grafana
istioctl dashboard jaeger
```
</details>

## Question 7: Ambient Mode

<details>
<summary>What is Ambient Mode in Istio 1.28.0 and how does it differ from Sidecar Mode?</summary>

**Answer:**
**Ambient Mode Concept:**
- Sidecar-less service mesh architecture
- ztunnel (node-level L4 proxy) + waypoint (optional L7 proxy)
- 85%+ resource reduction

**Architecture Comparison:**

| Feature | Sidecar Mode | Ambient Mode |
|---------|-------------|--------------|
| Deployment | Envoy injection per pod | 1 ztunnel per node |
| Resource Usage | High (50-100MB per pod) | Low (50MB per node) |
| Deployment Complexity | High (redeployment needed) | Low (transparent application) |
| L4 Features | Supported | Supported via ztunnel |
| L7 Features | Full support | Requires waypoint |
| Performance | Slightly slower | Fast (L4 only) |

**Ambient Mode Activation:**
```bash
# Install Ambient Mode
istioctl install --set profile=ambient -y

# Enable Ambient Mode on Namespace
kubectl label namespace default istio.io/dataplane-mode=ambient
```

**Use Cases:**
- Resource-constrained environments
- Large-scale clusters (1000+ pods)
- When only L4 features are needed
- Gradual Istio adoption
</details>

## Question 8: Resilience Patterns

<details>
<summary>What are the differences between Outlier Detection, Circuit Breaker, and Rate Limiting in Istio?</summary>

**Answer:**
**1. Outlier Detection - Exclude Unhealthy Instances:**
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

**2. Circuit Breaker - Prevent Overload:**
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

**3. Rate Limiting - Request Rate Control:**
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

**Differences:**
- **Outlier Detection**: Reactive (exclude after failure)
- **Circuit Breaker**: Preventive (limit connections)
- **Rate Limiting**: Request rate control (token bucket)

**Combined Usage:**
```yaml
trafficPolicy:
  connectionPool:     # Circuit Breaker
    tcp:
      maxConnections: 100
  outlierDetection:   # Outlier Detection
    consecutiveErrors: 5
```
</details>

## Question 9: Locality Load Balancing (Zone Aware Routing)

<details>
<summary>What is Istio's Locality Load Balancing feature and how is it used with AWS EKS?</summary>

**Answer:**
**Locality Load Balancing Concept:**
- Priority routing to services in the same Availability Zone (AZ)
- Reduced network latency
- Cross-AZ data transfer cost savings (~85%)

**Configuration:**
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

**AWS EKS Usage:**
1. **Cost Savings:**
   - Cross-AZ traffic: $0.01/GB
   - Same AZ traffic: Free
   - Significant cost savings with 80% same-AZ routing

2. **Performance Improvement:**
   - Intra-AZ latency: ~1ms
   - Cross-AZ latency: ~2-3ms

3. **Automatic Failover:**
   - Automatic failover to other AZ on AZ failure
   - Combined with Outlier Detection

**Pod Topology Configuration:**
```yaml
# EKS nodes automatically set topology labels
topology.kubernetes.io/region: us-east-1
topology.kubernetes.io/zone: us-east-1a
```
</details>

## Question 10: Amazon EKS Integration and Best Practices

<details>
<summary>What are the considerations and best practices when integrating Istio 1.28.0 with Amazon EKS 1.34?</summary>

**Answer:**
**1. Installation and Configuration:**
```bash
# Install Istioctl
curl -L https://istio.io/downloadIstio | sh -
cd istio-1.28.0
export PATH=$PWD/bin:$PATH

# Install with production profile
istioctl install --set profile=production -y
```

**2. AWS Load Balancer Integration:**
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

**3. Resource Optimization:**
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

**4. Security Configuration:**
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

**5. Monitoring Integration:**
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

**6. Best Practices:**
- Use production profile
- Control Plane HA (replica >= 3)
- mTLS STRICT mode
- PodDisruptionBudget configuration
- Enable Locality Load Balancing
- Prometheus + Grafana monitoring
- Regular version upgrades (Canary approach)

**7. Cost Optimization:**
- Consider Ambient Mode (85% resource reduction)
- Locality Load Balancing (cross-AZ cost savings)
- Sidecar Scope limitation (30-50% memory reduction)
</details>

## Bonus Question: Progressive Delivery

<details>
<summary>How do you implement fully automated Progressive Delivery with Istio + Argo Rollouts?</summary>

**Answer:**
Progressive Delivery is an approach that automatically progresses or rolls back deployments based on metrics.

**Complete Automation Example:**
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

**Automatic Rollback Conditions:**
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

**Key Benefits:**
- Full automation (no human intervention needed)
- Immediate rollback (within seconds of failure detection)
- Safe deployments (metrics-based verification)
- Consistent process (standardized)
</details>

---

**Scoring:**
- 10-11 correct: Excellent (Istio expert level)
- 8-9 correct: Good (production operations capable)
- 6-7 correct: Average (additional learning recommended)
- 4-5 correct: Insufficient (basic concepts review needed)
- 0-3 correct: Re-study needed

**Learning Resources:**
- [Istio Official Documentation](https://istio.io/latest/docs/)
- [Argo Rollouts Documentation](https://argo-rollouts.readthedocs.io/)
- [EKS Workshop - Istio](https://www.eksworkshop.com/docs/security/servicemesh/)
- [Detailed documentation in this guide](../../service-mesh/istio/README.md)
