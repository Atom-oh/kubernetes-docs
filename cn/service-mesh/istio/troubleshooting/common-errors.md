# Istio 常见错误与解决方案

> **支持的版本**: Istio 1.28
> **最后更新**: February 19, 2026

本文总结了使用 Istio 时最常遇到的错误及其解决方案。

## 目录

1. [Pod 终止期间的连接错误](#connection-errors-during-pod-termination)
2. [Sidecar 注入问题](#sidecar-injection-issues)
3. [mTLS 连接失败](#mtls-connection-failure)
4. [VirtualService 路由失败](#virtualservice-routing-failure)
5. [Gateway 配置问题](#gateway-configuration-issues)
6. [内存和性能问题](#memory-and-performance-issues)
7. [证书过期](#certificate-expiration)
8. [DNS 解析失败](#dns-resolution-failure)
9. [Envoy 初始化超时](#envoy-initialization-timeout)
10. [调试工具](#debugging-tools)

## Pod 终止期间的连接错误

### 问题描述

当 Pod 终止时，Envoy Sidecar 会在应用程序之前终止，从而导致连接错误。

**症状**:
```
Connection reset by peer
Broken pipe
EOF
HTTP 503 Service Unavailable
```

### 根本原因

```mermaid
sequenceDiagram
    autonumber
    participant K8s as Kubernetes
    participant App as Application
    participant Envoy as Envoy Proxy
    participant Client as Client

    Note over K8s,Client: Pod termination starts (kubectl delete pod)

    K8s->>App: Send SIGTERM
    K8s->>Envoy: Send SIGTERM

    rect rgb(255, 200, 200)
        Note over Envoy: Problem: Envoy terminates first
        Envoy->>Envoy: Starts terminating immediately
    end

    Client->>Envoy: Send request
    Envoy-->>Client: Connection refused

    rect rgb(200, 255, 200)
        Note over App: App is still running
        App->>App: Processing requests...
    end

    Note over K8s: After 30 seconds (terminationGracePeriodSeconds)
    K8s->>App: SIGKILL (force termination)
    K8s->>Envoy: SIGKILL (force termination)
```

**根本原因**:
1. Envoy 和应用程序同时接收 SIGTERM
2. Envoy 比应用程序终止得更快
3. 应用程序仍在处理请求，但 Envoy 已经终止，导致连接失败

### 解决方案

#### 方法 1：设置 Envoy Proxy preStop Hook（推荐）

为 Istio Proxy 容器配置 preStop Hook，使其等待所有活跃连接关闭。

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
spec:
  template:
    metadata:
      annotations:
        # Envoy waits for active connections to close
        proxy.istio.io/config: |
          terminationDrainDuration: 30s
    spec:
      terminationGracePeriodSeconds: 60
      containers:
      - name: myapp
        image: myapp:latest
        ports:
        - containerPort: 8080
```

**工作原理**:
```mermaid
sequenceDiagram
    autonumber
    participant K8s as Kubernetes
    participant App as Application
    participant Envoy as Envoy Proxy
    participant Client as Client

    Note over K8s,Client: Pod termination starts

    K8s->>App: Send SIGTERM
    K8s->>Envoy: Send SIGTERM

    rect rgb(200, 255, 200)
        Note over Envoy: Enters Drain mode
        Envoy->>Envoy: Reject new connections<br/>Maintain existing connections<br/>Wait 30 seconds
    end

    Client->>Envoy: Send request
    Envoy->>App: Forward request
    App->>Envoy: Response
    Envoy->>Client: Normal response

    Note over Envoy: Confirm active connections closed
    Envoy->>Envoy: Normal termination

    Note over App: App also terminates normally
    App->>App: Graceful Shutdown
```

#### 方法 2：通过 Pod Annotation 控制 Envoy 终止行为

您可以按 Pod 精细调整 Envoy 的终止行为。

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
spec:
  template:
    metadata:
      annotations:
        # Envoy waits for application startup
        proxy.istio.io/config: |
          holdApplicationUntilProxyStarts: true
          terminationDrainDuration: 30s
        # Envoy termination timeout
        sidecar.istio.io/terminationGracePeriodSeconds: "60"
    spec:
      terminationGracePeriodSeconds: 60
      containers:
      - name: myapp
        image: myapp:latest
```

**配置说明**:
- `holdApplicationUntilProxyStarts: true`: Envoy 会在应用程序之前启动
- `terminationDrainDuration: 30s`: Envoy 在终止期间会进行 30 秒的连接排空
- `terminationGracePeriodSeconds: 60`: Pod 终止的总宽限期

#### 方法 3：全局配置（IstioOperator）

在整个集群中应用一致的终止策略。

```yaml
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
metadata:
  name: istio-controlplane
spec:
  meshConfig:
    defaultConfig:
      terminationDrainDuration: 30s
      holdApplicationUntilProxyStarts: true
  values:
    global:
      proxy:
        lifecycle:
          preStop:
            exec:
              command:
              - /bin/sh
              - -c
              - |
                # Start Envoy drain
                curl -X POST http://localhost:15000/drain_listeners?graceful
                # Wait for active connections
                while [ $(netstat -plunt | grep tcp | grep -v TIME_WAIT | wc -l | xargs) -ne 0 ]; do
                  sleep 1;
                done
```

**推荐设置**:
- `terminationDrainDuration`: 30 秒（活跃连接排空时间）
- `terminationGracePeriodSeconds`: 60 秒（SIGKILL 之前的宽限期）
- Envoy 检查活跃连接并执行优雅关闭

### 验证方法

```bash
# 1. Check logs during pod termination
kubectl logs -f <pod-name> -c istio-proxy --previous

# 2. Check connection status during termination
kubectl exec <pod-name> -c istio-proxy -- netstat -an | grep ESTABLISHED

# 3. Check termination events
kubectl get events --field-selector involvedObject.name=<pod-name>
```

### 最佳实践

```yaml
# Recommended configuration template
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
spec:
  template:
    metadata:
      annotations:
        # Envoy termination behavior control
        proxy.istio.io/config: |
          holdApplicationUntilProxyStarts: true
          terminationDrainDuration: 30s
    spec:
      terminationGracePeriodSeconds: 60
      containers:
      - name: myapp
        image: myapp:latest
        ports:
        - containerPort: 8080
        readinessProbe:
          httpGet:
            path: /health
            port: 8080
          periodSeconds: 5
          successThreshold: 1
          failureThreshold: 3
        # Optional: application graceful shutdown
        lifecycle:
          preStop:
            exec:
              command:
              - /bin/sh
              - -c
              - |
                # Disable readiness (optional)
                touch /tmp/not-ready
                # Wait for application requests to complete
                sleep 5
```

**检查清单**:
- **设置 Envoy terminationDrainDuration**（最重要！）
- **holdApplicationUntilProxyStarts: true**（确保启动顺序）
- **充分设置 terminationGracePeriodSeconds**（至少 60 秒）
- 设置 ReadinessProbe（在终止期间快速转换为不健康状态）
- 实现应用程序的优雅关闭（可选）
- 设置监控和日志记录

**要点**:
- **不要在应用程序容器中添加 sleep！**
- **配置 Envoy 在 drain 模式下优雅关闭。**

## Sidecar 注入问题

### 问题 1：未注入 Sidecar

**症状**:
```bash
kubectl get pod <pod-name> -o jsonpath='{.spec.containers[*].name}'
# Output: myapp (no istio-proxy)
```

**原因和解决方案**:

#### 1. 缺少 Namespace Label

```bash
# Check
kubectl get namespace <namespace> --show-labels

# Solution
kubectl label namespace <namespace> istio-injection=enabled
```

#### 2. 通过 Pod Annotation 禁用了注入

```yaml
# Incorrect configuration
apiVersion: v1
kind: Pod
metadata:
  annotations:
    sidecar.istio.io/inject: "false"  # <- Injection disabled
```

**解决方案**:
```yaml
# Correct configuration
apiVersion: v1
kind: Pod
metadata:
  annotations:
    sidecar.istio.io/inject: "true"
```

#### 3. 验证 Istio Sidecar Injector 是否正常运行

```bash
# Check sidecar injector webhook
kubectl get mutatingwebhookconfigurations

# Check Istio injector logs
kubectl logs -n istio-system -l app=sidecar-injector
```

### 问题 2：Sidecar 资源不足

**症状**:
```
OOMKilled
CrashLoopBackOff
Error: container has runAsNonRoot and image has non-numeric user
```

**解决方案**:

```yaml
apiVersion: v1
kind: Pod
metadata:
  annotations:
    sidecar.istio.io/proxyCPU: "200m"
    sidecar.istio.io/proxyMemory: "256Mi"
    sidecar.istio.io/proxyCPULimit: "1000m"
    sidecar.istio.io/proxyMemoryLimit: "512Mi"
spec:
  containers:
  - name: myapp
    image: myapp:latest
```

## mTLS 连接失败

### 问题描述

**症状**:
```
upstream connect error or disconnect/reset before headers
503 Service Unavailable
SSL routines:OPENSSL_internal:WRONG_VERSION_NUMBER
```

### 原因 1：PeerAuthentication 模式不匹配

```mermaid
flowchart TD
    Client[Client Service<br/>mTLS STRICT]
    Server[Server Service<br/>mTLS DISABLE]

    Client -->|mTLS connection attempt| Server
    Server -.->|Requires plaintext connection| Client

    Error[503 Error<br/>upstream connect error]

    Server -.-> Error

    classDef error fill:#FF6B6B,stroke:#333,stroke-width:2px,color:white;
    class Error error;
```

**解决方案**:

```yaml
# Apply consistent mTLS policy across namespace
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: default
  namespace: istio-system
spec:
  mtls:
    mode: STRICT  # All services STRICT mode
```

### 原因 2：DestinationRule 与 PeerAuthentication 冲突

```yaml
# Incorrect example
---
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: default
spec:
  mtls:
    mode: STRICT
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: myapp
spec:
  host: myapp
  trafficPolicy:
    tls:
      mode: DISABLE  # <- Conflict!
```

**解决方案**:
```yaml
# Correct example
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: myapp
spec:
  host: myapp
  trafficPolicy:
    tls:
      mode: ISTIO_MUTUAL  # Matches PeerAuthentication
```

### 调试命令

```bash
# 1. Check mTLS status
istioctl x describe pod <pod-name> -n <namespace>

# 2. Check PeerAuthentication policies
kubectl get peerauthentication -A

# 3. Check DestinationRule TLS settings
kubectl get destinationrule -A -o yaml | grep -A 5 "tls:"

# 4. Check Envoy cluster TLS settings
istioctl proxy-config clusters <pod-name> -n <namespace> --fqdn <service-name>
```

## VirtualService 路由失败

### 问题 1：流量未被路由

**症状**:
```
404 Not Found
default backend - 404
```

**原因和解决方案**:

#### Host 匹配错误

```yaml
# Incorrect example
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: myapp
spec:
  hosts:
  - myapp.example.com  # <- DNS name
  http:
  - route:
    - destination:
        host: myapp  # <- Kubernetes Service name
```

**解决方案**:
```yaml
# Correct example
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: myapp
  namespace: default
spec:
  hosts:
  - myapp  # Exactly matches Kubernetes Service name
  - myapp.default.svc.cluster.local  # Also add FQDN
  http:
  - route:
    - destination:
        host: myapp
```

### 问题 2：找不到 Subset

**症状**:
```
no healthy upstream
subset not found
```

**原因**:
```yaml
# VirtualService exists but DestinationRule is missing
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: myapp
spec:
  http:
  - route:
    - destination:
        host: myapp
        subset: v1  # <- Subset not defined
```

**解决方案**:
```yaml
# Add DestinationRule
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: myapp
spec:
  host: myapp
  subsets:
  - name: v1
    labels:
      version: v1
  - name: v2
    labels:
      version: v2
```

### 调试

```bash
# 1. Validate VirtualService
istioctl analyze -n <namespace>

# 2. Check routing rules
istioctl proxy-config routes <pod-name> -n <namespace>

# 3. Check VirtualService status
kubectl get virtualservice <name> -n <namespace> -o yaml
```

## Gateway 配置问题

### 问题 1：流量未到达 Gateway

**症状**:
```bash
curl: (7) Failed to connect to example.com port 443: Connection refused
```

**原因和解决方案**:

#### 1. 检查 Gateway Service

```bash
# Check Gateway Service status
kubectl get svc -n istio-system istio-ingressgateway

# Check External IP
kubectl get svc -n istio-system istio-ingressgateway -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'
```

#### 2. 验证 Gateway 和 VirtualService 的连接

```yaml
# Incorrect example
---
apiVersion: networking.istio.io/v1
kind: Gateway
metadata:
  name: myapp-gateway
spec:
  selector:
    istio: ingressgateway
  servers:
  - port:
      number: 80
      name: http
      protocol: HTTP
    hosts:
    - "example.com"
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: myapp
spec:
  hosts:
  - "example.com"
  gateways:
  - my-gateway  # <- Gateway name typo!
```

**解决方案**:
```yaml
# Correct example
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: myapp
spec:
  hosts:
  - "example.com"
  gateways:
  - myapp-gateway  # Exactly matches Gateway name
```

### 问题 2：HTTPS 证书错误

**症状**:
```
SSL certificate problem: self signed certificate
```

**解决方案**:

```yaml
apiVersion: networking.istio.io/v1
kind: Gateway
metadata:
  name: myapp-gateway
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
      credentialName: myapp-tls-secret  # <- Specify exact Secret name
    hosts:
    - "example.com"
```

```bash
# Create TLS Secret
kubectl create secret tls myapp-tls-secret \
  --cert=path/to/cert.pem \
  --key=path/to/key.pem \
  -n istio-system
```

## 内存和性能问题

### 问题 1：Envoy 内存使用量增加

**症状**:
```
OOMKilled
Memory usage > 1GB per pod
```

**原因**:
- 创建了过多的 listener/cluster
- ConfigMap/Secret 过大
- 内存泄漏

**解决方案**:

```yaml
# Limit scope with Sidecar resource
apiVersion: networking.istio.io/v1
kind: Sidecar
metadata:
  name: default
  namespace: default
spec:
  egress:
  - hosts:
    - "./*"  # Same namespace only
    - "istio-system/*"  # istio-system only
```

```yaml
# Envoy resource limits
apiVersion: v1
kind: Pod
metadata:
  annotations:
    sidecar.istio.io/proxyMemory: "512Mi"
    sidecar.istio.io/proxyMemoryLimit: "1Gi"
```

### 问题 2：高延迟

**症状**:
- P99 延迟 > 1 秒
- 经常发生超时错误

**解决方案**:

```yaml
# Set timeout in VirtualService
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: myapp
spec:
  http:
  - route:
    - destination:
        host: myapp
    timeout: 5s  # Total request timeout
    retries:
      attempts: 3
      perTryTimeout: 2s  # Timeout per retry
```

## 证书过期

### 问题描述

**症状**:
```
x509: certificate has expired
SSL handshake failed
```

**原因**:
- Istio CA 证书已过期（默认 10 年）
- Workload 证书已过期（默认 24 小时，自动续期）

**解决方案**:

```bash
# 1. Check CA certificate
kubectl get secret istio-ca-secret -n istio-system -o jsonpath='{.data.ca-cert\.pem}' | base64 -d | openssl x509 -noout -dates

# 2. Check workload certificates
istioctl proxy-config secret <pod-name> -n <namespace>

# 3. Regenerate CA certificate
istioctl x ca root
```

## DNS 解析失败

### 问题描述

**症状**:
```
no such host
DNS resolution failed
```

**解决方案**:

```yaml
# Register external service with ServiceEntry
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: external-api
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

## Envoy 初始化超时

### 问题描述

**症状**:
```
waiting for Envoy proxy to be ready
Readiness probe failed
```

**解决方案**:

```yaml
apiVersion: v1
kind: Pod
metadata:
  annotations:
    proxy.istio.io/config: |
      holdApplicationUntilProxyStarts: true
spec:
  containers:
  - name: myapp
    image: myapp:latest
    readinessProbe:
      initialDelaySeconds: 10  # Wait for Envoy initialization
```

## 调试工具

### istioctl 命令

```bash
# 1. Analyze pod status
istioctl x describe pod <pod-name> -n <namespace>

# 2. Validate configuration
istioctl analyze -A

# 3. Check Envoy configuration
istioctl proxy-config all <pod-name> -n <namespace>

# 4. Change Envoy log level
istioctl proxy-config log <pod-name> --level debug

# 5. Generate bug report
istioctl bug-report
```

### Envoy Admin API

```bash
# Port-forward to Envoy admin port
kubectl port-forward <pod-name> 15000:15000

# 1. Check cluster status
curl localhost:15000/clusters

# 2. Check statistics
curl localhost:15000/stats/prometheus

# 3. Configuration dump
curl localhost:15000/config_dump

# 4. Change logging level
curl -X POST localhost:15000/logging?level=debug
```

### 常见日志检查

```bash
# Application logs
kubectl logs <pod-name> -c <container-name>

# Envoy logs
kubectl logs <pod-name> -c istio-proxy

# Previous container logs (if restarted)
kubectl logs <pod-name> -c istio-proxy --previous

# Real-time logs
kubectl logs -f <pod-name> -c istio-proxy
```

## 参考资料

### 官方文档
- [Istio 调试指南](https://istio.io/latest/docs/ops/diagnostic-tools/)
- [Istio 常见问题](https://istio.io/latest/about/faq/)
- [常见问题](https://istio.io/latest/docs/ops/common-problems/)

### 相关文档
- [可观测性](../observability/README.md)
- [安全](../security/README.md)
- [流量管理](../traffic-management/README.md)

---

**最后更新**: November 27, 2025
