# Istio Common Errors and Solutions

> **Supported Version**: Istio 1.28
> **Last Updated**: February 19, 2026

This document summarizes the most common errors encountered when using Istio and their solutions.

## Table of Contents

1. [Connection Errors During Pod Termination](#connection-errors-during-pod-termination)
2. [Sidecar Injection Issues](#sidecar-injection-issues)
3. [mTLS Connection Failure](#mtls-connection-failure)
4. [VirtualService Routing Failure](#virtualservice-routing-failure)
5. [Gateway Configuration Issues](#gateway-configuration-issues)
6. [Memory and Performance Issues](#memory-and-performance-issues)
7. [Certificate Expiration](#certificate-expiration)
8. [DNS Resolution Failure](#dns-resolution-failure)
9. [Envoy Initialization Timeout](#envoy-initialization-timeout)
10. [Debugging Tools](#debugging-tools)

## Connection Errors During Pod Termination

### Problem Description

When a pod terminates, the Envoy Sidecar terminates before the application, causing connection errors.

**Symptoms**:
```
Connection reset by peer
Broken pipe
EOF
HTTP 503 Service Unavailable
```

### Root Cause

![Sequence diagram showing Kubernetes sending SIGTERM to both the application and Envoy proxy at the same time; because Envoy terminates first while the application keeps running, a client request during that window gets connection refused before Kubernetes finally sends SIGKILL to both after the grace period.](../../../.gitbook/assets/en-service-mesh-istio-troubleshooting-common-errors-0.png)

**Root Causes**:
1. Envoy and application receive SIGTERM simultaneously
2. Envoy terminates faster than the application
3. Application is still processing requests but Envoy has already terminated, causing connection failure

### Solutions

#### Method 1: Set Envoy Proxy preStop Hook (Recommended)

Configure a preStop Hook for the Istio Proxy container to wait until all active connections are closed.

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

**How It Works**:
![Sequence diagram showing that once Envoy enters drain mode on SIGTERM it keeps serving existing connections for the full grace period, so a client request during shutdown still gets forwarded to the application and returned normally, and both Envoy and the application terminate cleanly afterward.](../../../.gitbook/assets/en-service-mesh-istio-troubleshooting-common-errors-1.png)

#### Method 2: Control Envoy Termination Behavior with Pod Annotation

You can fine-tune Envoy's termination behavior on a per-pod basis.

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

**Configuration Explanation**:
- `holdApplicationUntilProxyStarts: true`: Envoy starts before the application
- `terminationDrainDuration: 30s`: Envoy drains for 30 seconds during termination
- `terminationGracePeriodSeconds: 60`: Total pod termination grace period

#### Method 3: Global Configuration (IstioOperator)

Apply a consistent termination policy across the entire cluster.

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

**Recommended Settings**:
- `terminationDrainDuration`: 30 seconds (active connection drain time)
- `terminationGracePeriodSeconds`: 60 seconds (grace period before SIGKILL)
- Envoy checks active connections and performs graceful shutdown

### Verification Method

```bash
# 1. Check logs during pod termination
kubectl logs -f <pod-name> -c istio-proxy --previous

# 2. Check connection status during termination
kubectl exec <pod-name> -c istio-proxy -- netstat -an | grep ESTABLISHED

# 3. Check termination events
kubectl get events --field-selector involvedObject.name=<pod-name>
```

### Best Practices

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

**Checklist**:
- **Set Envoy terminationDrainDuration** (most important!)
- **holdApplicationUntilProxyStarts: true** (ensures startup order)
- **Set terminationGracePeriodSeconds sufficiently** (minimum 60 seconds)
- Set ReadinessProbe (quickly transition to unhealthy during termination)
- Implement application graceful shutdown (optional)
- Set up monitoring and logging

**Key Points**:
- **Don't add sleep to the application container!**
- **Configure Envoy to graceful shutdown in drain mode.**

## Sidecar Injection Issues

### Issue 1: Sidecar Not Injected

**Symptoms**:
```bash
kubectl get pod <pod-name> -o jsonpath='{.spec.containers[*].name}'
# Output: myapp (no istio-proxy)
```

**Causes and Solutions**:

#### 1. Missing Namespace Label

```bash
# Check
kubectl get namespace <namespace> --show-labels

# Solution
kubectl label namespace <namespace> istio-injection=enabled
```

#### 2. Injection Disabled by Pod Annotation

```yaml
# Incorrect configuration
apiVersion: v1
kind: Pod
metadata:
  annotations:
    sidecar.istio.io/inject: "false"  # <- Injection disabled
```

**Solution**:
```yaml
# Correct configuration
apiVersion: v1
kind: Pod
metadata:
  annotations:
    sidecar.istio.io/inject: "true"
```

#### 3. Verify Istio Sidecar Injector Operation

```bash
# Check sidecar injector webhook
kubectl get mutatingwebhookconfigurations

# Check Istio injector logs
kubectl logs -n istio-system -l app=sidecar-injector
```

### Issue 2: Sidecar Resource Shortage

**Symptoms**:
```
OOMKilled
CrashLoopBackOff
Error: container has runAsNonRoot and image has non-numeric user
```

**Solution**:

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

## mTLS Connection Failure

### Problem Description

**Symptoms**:
```
upstream connect error or disconnect/reset before headers
503 Service Unavailable
SSL routines:OPENSSL_internal:WRONG_VERSION_NUMBER
```

### Cause 1: PeerAuthentication Mode Mismatch

![Flowchart showing a client service in STRICT mTLS mode attempting an encrypted connection to a server service configured in DISABLE mode; the server demands a plaintext connection instead, and the mismatch surfaces to the client as a 503 upstream connect error.](../../../.gitbook/assets/en-service-mesh-istio-troubleshooting-common-errors-2.png)

**Solution**:

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

### Cause 2: DestinationRule and PeerAuthentication Conflict

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

**Solution**:
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

### Debugging Commands

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

## VirtualService Routing Failure

### Issue 1: Traffic Not Being Routed

**Symptoms**:
```
404 Not Found
default backend - 404
```

**Causes and Solutions**:

#### Incorrect Host Matching

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

**Solution**:
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

### Issue 2: Subset Not Found

**Symptoms**:
```
no healthy upstream
subset not found
```

**Cause**:
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

**Solution**:
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

### Debugging

```bash
# 1. Validate VirtualService
istioctl analyze -n <namespace>

# 2. Check routing rules
istioctl proxy-config routes <pod-name> -n <namespace>

# 3. Check VirtualService status
kubectl get virtualservice <name> -n <namespace> -o yaml
```

## Gateway Configuration Issues

### Issue 1: Traffic Not Reaching Gateway

**Symptoms**:
```bash
curl: (7) Failed to connect to example.com port 443: Connection refused
```

**Causes and Solutions**:

#### 1. Check Gateway Service

```bash
# Check Gateway Service status
kubectl get svc -n istio-system istio-ingressgateway

# Check External IP
kubectl get svc -n istio-system istio-ingressgateway -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'
```

#### 2. Verify Gateway and VirtualService Connection

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

**Solution**:
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

### Issue 2: HTTPS Certificate Error

**Symptoms**:
```
SSL certificate problem: self signed certificate
```

**Solution**:

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

## Memory and Performance Issues

### Issue 1: Envoy Memory Usage Increase

**Symptoms**:
```
OOMKilled
Memory usage > 1GB per pod
```

**Causes**:
- Too many listeners/clusters created
- Large ConfigMap/Secret
- Memory leak

**Solution**:

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

### Issue 2: High Latency

**Symptoms**:
- P99 latency > 1 second
- Frequent timeout errors

**Solution**:

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

## Certificate Expiration

### Problem Description

**Symptoms**:
```
x509: certificate has expired
SSL handshake failed
```

**Causes**:
- Istio CA certificate expired (default 10 years)
- Workload certificate expired (default 24 hours, auto-renewed)

**Solution**:

```bash
# 1. Check CA certificate
kubectl get secret istio-ca-secret -n istio-system -o jsonpath='{.data.ca-cert\.pem}' | base64 -d | openssl x509 -noout -dates

# 2. Check workload certificates
istioctl proxy-config secret <pod-name> -n <namespace>

# 3. Regenerate CA certificate
istioctl x ca root
```

## DNS Resolution Failure

### Problem Description

**Symptoms**:
```
no such host
DNS resolution failed
```

**Solution**:

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

## Envoy Initialization Timeout

### Problem Description

**Symptoms**:
```
waiting for Envoy proxy to be ready
Readiness probe failed
```

**Solution**:

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

## Debugging Tools

### istioctl Commands

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

### Common Log Checking

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

## References

### Official Documentation
- [Istio Debugging Guide](https://istio.io/latest/docs/ops/diagnostic-tools/)
- [Istio FAQ](https://istio.io/latest/about/faq/)
- [Common Problems](https://istio.io/latest/docs/ops/common-problems/)

### Related Documentation
- [Observability](../observability/README.md)
- [Security](../security/README.md)
- [Traffic Management](../traffic-management/README.md)

---

**Last Updated**: November 27, 2025
