# Istio Best Practices

This document covers best practices and recommendations for successfully operating Istio in production environments.

## Table of Contents

1. [Performance Optimization](#performance-optimization)
2. [Security Hardening](#security-hardening)
3. [Operations Guide](#operations-guide)
4. [Monitoring and Observability](#monitoring-and-observability)
5. [Production Checklist](#production-checklist)

## Performance Optimization

### 1. Control Plane Resource Optimization

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

**Recommendations**:
- Istiod should have at least 2 replicas
- CPU: Adjust based on cluster size
- Memory: Estimate approximately 10KB per service

### 2. Data Plane Resource Optimization

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

**Recommendations**:
- Normal workloads: CPU 100m, Memory 128Mi
- High-traffic workloads: CPU 500m, Memory 512Mi
- Sidecar concurrency: `concurrency: 2` (default)

### 3. Connection Pool Optimization

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

**Recommendations**:
- `maxConnections`: Consider workload concurrent connections
- `maxRequestsPerConnection`: 1-2 for HTTP/1.1, higher for HTTP/2
- `idleTimeout`: Increase if long-lived connections are needed

### 4. Locality Load Balancing

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

**Benefits**:
- Cross-AZ cost reduction (~85%)
- Reduced network latency
- Automatic handling of availability zone failures

### 5. Sidecar Scope Limitation

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

**Benefits**:
- Reduced Envoy configuration size
- Reduced memory usage
- Faster configuration push

## Security Hardening

### 1. Apply Strict mTLS

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

**Checklist**:
- Apply STRICT mTLS to all services
- Use PERMISSIVE only during migration periods
- DISABLE for external services (handle in ServiceEntry)

### 2. Authorization Policy

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

**Best Practices**:
- Use deny-by-default policy
- Apply principle of least privilege
- Service Account-based authentication
- Namespace isolation

### 3. Egress Traffic Control

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

### 4. JWT Authentication

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

## Operations Guide

### 1. Deployment Strategy

#### Gradual Istio Adoption

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

**Phase 1: Observability (1-2 weeks)**
```bash
# Enable sidecar injection only
kubectl label namespace default istio-injection=enabled

# Verify metrics, logs, traces
# Evaluate performance impact
```

**Phase 2: mTLS PERMISSIVE (1-2 weeks)**
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

**Phase 3: mTLS STRICT (1 week)**
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

**Phase 4: Advanced Features (Ongoing)**
- Traffic Management (Canary, Circuit Breaker)
- Authorization Policy
- Rate Limiting

### 2. Upgrade Strategy

#### Canary Upgrade

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

### 3. High Availability

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

**Recommendations**:
- Istiod: Minimum 3 replicas
- Distribute evenly across AZs
- Set up PodDisruptionBudget

### 4. Backup and Recovery

```bash
# Backup Istio configuration
kubectl get istiooperator -A -o yaml > istio-operator-backup.yaml
kubectl get vs,dr,gw,se,pa,ra,ap -A -o yaml > istio-config-backup.yaml

# Recovery
kubectl apply -f istio-operator-backup.yaml
kubectl apply -f istio-config-backup.yaml
```

## Monitoring and Observability

### 1. Golden Signals

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

### 2. Control Plane Monitoring

```promql
# Pilot configuration push time
pilot_proxy_convergence_time

# xDS connection count
pilot_xds_pushes

# Memory usage
process_resident_memory_bytes{app="istiod"}
```

### 3. Data Plane Monitoring

```promql
# Envoy connection count
envoy_cluster_upstream_cx_active

# Circuit Breaker open
envoy_cluster_circuit_breakers_default_rq_open

# Outlier Detection
envoy_cluster_outlier_detection_ejections_active
```

### 4. Alerting Rules

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

## Production Checklist

### Pre-Installation

- [ ] Verify Kubernetes version compatibility (1.28+)
- [ ] Select Istio version (stable version recommended)
- [ ] Calculate resource requirements
- [ ] Review network policies
- [ ] Establish backup and recovery plan

### Installation

- [ ] Use production profile
- [ ] Configure Control Plane HA (replica >= 3)
- [ ] Set resource limits
- [ ] Set up PodDisruptionBudget
- [ ] Prepare monitoring stack

### Security

- [ ] Enable mTLS STRICT mode
- [ ] Apply Authorization Policy
- [ ] Control egress traffic
- [ ] Configure JWT authentication (if needed)
- [ ] Integrate Network Policy

### Traffic Management

- [ ] Configure VirtualService
- [ ] Configure DestinationRule
- [ ] Set up Circuit Breaker
- [ ] Set up Retry/Timeout
- [ ] Configure Rate Limiting

### Observability

- [ ] Integrate Prometheus
- [ ] Set up Grafana dashboards
- [ ] Set up Jaeger/Zipkin tracing
- [ ] Install Kiali
- [ ] Set up alerting rules

### Operations

- [ ] Establish upgrade plan
- [ ] Automate backups
- [ ] Documentation
- [ ] Write on-call guide
- [ ] Prepare runbook

### Performance

- [ ] Optimize Sidecar resources
- [ ] Tune Connection Pool
- [ ] Configure Locality Load Balancing
- [ ] Limit Sidecar Scope
- [ ] Perform performance testing

### Testing

- [ ] Functional testing
- [ ] Performance testing
- [ ] Disaster recovery testing
- [ ] Chaos engineering
- [ ] Upgrade scenario testing

## Common Anti-patterns

### Things to Avoid

1. **Adopting everything at once**
   ```
   Don't enable all Istio features on Day 1
   Do add features gradually (Observability -> Security -> Traffic Management)
   ```

2. **No resource limits**
   ```yaml
   Don't leave Sidecar without resource limits
   Do set appropriate requests/limits
   ```

3. **Long-term use of PERMISSIVE mode**
   ```
   Don't keep using PERMISSIVE
   Do transition to STRICT quickly
   ```

4. **Wildcard match abuse**
   ```yaml
   Don't: hosts: ["*"]  # All services
   Do: hosts: ["myapp.default.svc.cluster.local"]  # Explicit
   ```

5. **Deploying without monitoring**
   ```
   Don't deploy to production without checking metrics
   Do require Golden Signals monitoring
   ```

## Cost Optimization

### 1. Consider Ambient Mode

```yaml
# Resource usage comparison
# Sidecar Mode: 100 pods x 50MB = 5GB
# Ambient Mode: 10 nodes x 50MB = 500MB

# 85%+ reduction possible
```

### 2. Locality Load Balancing

```yaml
# Cross-AZ cost savings
# AWS: $0.01-0.02 per GB
# Significant savings with 80% same AZ routing
```

### 3. Sidecar Scope Limitation

```yaml
# Remove unnecessary configuration
# 30-50% memory usage reduction possible
```

## References

### Official Documentation
- [Istio Best Practices](https://istio.io/latest/docs/ops/best-practices/)
- [Performance and Scalability](https://istio.io/latest/docs/ops/deployment/performance-and-scalability/)
- [Security Best Practices](https://istio.io/latest/docs/ops/best-practices/security/)

### Community
- [Istio Discuss](https://discuss.istio.io/)
- [Istio Slack](https://istio.slack.com/)
- [GitHub Issues](https://github.com/istio/istio/issues)

### Additional Resources
- [Istio in Production](https://www.tetrate.io/blog/istio-in-production/)
- [Service Mesh Patterns](https://www.oreilly.com/library/view/service-mesh-patterns/9781492086444/)
