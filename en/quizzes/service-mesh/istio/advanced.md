# Istio Advanced Topics Quiz

> **Supported Version**: Istio 1.28.0
> **EKS Version**: 1.34 (Kubernetes 1.28+)
> **Last Updated**: February 19, 2026

This quiz tests your understanding of Istio's advanced features.

## Multiple Choice Questions (1-5)

### Question 1: Ambient Mode vs Sidecar Mode

What is the **greatest advantage** of Istio Ambient Mode?

A. Provides more features
B. Significantly reduced resource usage
C. Faster installation speed
D. Better security

<details>
<summary>Show Answer</summary>

**Answer: B**

The greatest advantage of Ambient Mode is that **resource usage is reduced by more than 98%**.

**Explanation:**

**Sidecar Mode vs Ambient Mode Comparison:**

| Item | Sidecar Mode | Ambient Mode | Improvement |
|------|-------------|-------------|------|
| **Memory** | 50MB × Pod count | ztunnel + waypoint only | 98%+ reduction |
| **CPU** | 0.1 vCPU × Pod count | ztunnel + waypoint only | 98%+ reduction |
| **Pod restart** | Required | Not required | Simplified operations |
| **Deployment speed** | Slow (Sidecar injection) | Fast | 5-10x improvement |

**Resource comparison at 1000 Pod scale:**

```
Sidecar Mode:
- Memory: 1000 × 50MB = 50GB
- CPU: 1000 × 0.1 vCPU = 100 vCPU

Ambient Mode (10 nodes):
- Memory: (10 × 50MB) + 200MB = 700MB
- CPU: (10 × 0.1 vCPU) + 0.5 vCPU = 1.5 vCPU

Savings rate: 98.6% (memory), 98.5% (CPU)
```

**Ambient Mode Architecture:**

![Diagram showing pods on two nodes routing through a per-node ztunnel L4 proxy that carries mTLS to its peer node, with both ztunnels optionally forwarding to a shared waypoint proxy when L7 policy is needed.](../../../../assets/diagrams/rendered/en-quizzes-service-mesh-istio-advanced-0.svg)

**Enabling Ambient Mode:**

```bash
# Install Istio with Ambient Mode
istioctl install --set profile=ambient -y

# Add Namespace to Ambient Mode
kubectl label namespace default istio.io/dataplane-mode=ambient

# Verify
kubectl get pods -n istio-system | grep ztunnel
```

**Option Analysis:**
- A (X): Features are the same as Sidecar (some advanced features require waypoint)
- B (O): Resource usage reduced by more than 98%
- C (X): Installation speed is a secondary benefit
- D (X): Security level is the same (mTLS, AuthorizationPolicy both supported)

**Reference:**
- [Ambient Mode](../../../service-mesh/istio/advanced/01-ambient-mode.md)
</details>

---

### Question 2: Multi-cluster Mesh

In Istio Multi-cluster Mesh, what is responsible for **service discovery across clusters**?

A. Istiod
B. CoreDNS
C. East-West Gateway
D. Service Entry

<details>
<summary>Show Answer</summary>

**Answer: A**

**Istiod** collects and distributes service information from all clusters in a multi-cluster environment.

**Explanation:**

**Multi-cluster Mesh Architecture:**

![Diagram showing a shared primary Istiod distributing configuration to each cluster's local Istiod, which discovers its own services, while pods in the two clusters communicate directly across the cluster boundary.](../../../../assets/diagrams/rendered/en-quizzes-service-mesh-istio-advanced-1.svg)

**Istiod's Roles:**

1. **Service Discovery**:
   - Collects Kubernetes Services from all clusters
   - Maintains unified service registry
   - Distributes endpoint information to Envoy

2. **Configuration Distribution**:
   - Deploys VirtualService, DestinationRule to all clusters
   - Manages cross-cluster routing rules

3. **Certificate Management**:
   - Issues mTLS certificates for all clusters
   - Builds trust chain by sharing Root CA

**Multi-cluster Configuration Example:**

```yaml
# Primary cluster configuration
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  values:
    global:
      meshID: mesh1
      multiCluster:
        clusterName: cluster1
      network: network1

---
# Remote cluster access from Primary
apiVersion: v1
kind: Secret
metadata:
  name: istio-remote-secret-cluster2
  namespace: istio-system
  annotations:
    networking.istio.io/cluster: cluster2
type: Opaque
data:
  kubeconfig: <base64-encoded-kubeconfig>
```

**Option Analysis:**
- A (O): Istiod collects and distributes service information from all clusters
- B (X): CoreDNS only handles cluster-internal DNS
- C (X): East-West Gateway only handles traffic routing (not service discovery)
- D (X): ServiceEntry is a resource for manually registering external services

**Reference:**
- [Multi-cluster](../../../service-mesh/istio/advanced/02-multi-cluster.md)
</details>

---

### Question 3: EnvoyFilter Purpose

What is the **main purpose** of using EnvoyFilter?

A. Create Kubernetes Service
B. Auto-generate VirtualService
C. Customize Envoy proxy behavior
D. Change Istiod configuration

<details>
<summary>Show Answer</summary>

**Answer: C**

**EnvoyFilter** is an advanced resource for fine-grained customization of Envoy proxy behavior.

**Explanation:**

**EnvoyFilter Use Cases:**

1. **Add Custom Headers**:
```yaml
apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata:
  name: add-custom-header
  namespace: default
spec:
  workloadSelector:
    labels:
      app: reviews
  configPatches:
  - applyTo: HTTP_FILTER
    match:
      context: SIDECAR_OUTBOUND
      listener:
        filterChain:
          filter:
            name: "envoy.filters.network.http_connection_manager"
            subFilter:
              name: "envoy.filters.http.router"
    patch:
      operation: INSERT_BEFORE
      value:
        name: envoy.lua
        typed_config:
          "@type": type.googleapis.com/envoy.extensions.filters.http.lua.v3.Lua
          inline_code: |
            function envoy_on_request(request_handle)
              request_handle:headers():add("x-custom-header", "my-value")
            end
```

2. **Wasm Extension Integration**:
```yaml
apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata:
  name: wasm-filter
spec:
  configPatches:
  - applyTo: HTTP_FILTER
    match:
      context: SIDECAR_INBOUND
    patch:
      operation: INSERT_BEFORE
      value:
        name: envoy.filters.http.wasm
        typed_config:
          "@type": type.googleapis.com/envoy.extensions.filters.http.wasm.v3.Wasm
          config:
            vm_config:
              runtime: "envoy.wasm.runtime.v8"
              code:
                local:
                  filename: "/etc/istio/extensions/auth_filter.wasm"
```

3. **Rate Limiting Integration**:
```yaml
apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata:
  name: rate-limit-filter
spec:
  configPatches:
  - applyTo: HTTP_FILTER
    match:
      context: SIDECAR_INBOUND
      listener:
        filterChain:
          filter:
            name: "envoy.filters.network.http_connection_manager"
    patch:
      operation: INSERT_BEFORE
      value:
        name: envoy.filters.http.ratelimit
        typed_config:
          "@type": type.googleapis.com/envoy.extensions.filters.http.ratelimit.v3.RateLimit
          domain: productpage-ratelimit
          rate_limit_service:
            grpc_service:
              envoy_grpc:
                cluster_name: rate_limit_cluster
```

**EnvoyFilter Scope:**

```yaml
spec:
  # Apply to entire mesh
  workloadSelector: {}

  # Apply to specific workload only
  workloadSelector:
    labels:
      app: reviews
      version: v2

  # Apply to specific namespace only
  # (controlled by metadata.namespace)
```

**Cautions:**

Warning: **EnvoyFilter is very powerful but risky:**
- Requires deep understanding of Envoy internals
- Potential compatibility issues during Istio version upgrades
- Incorrect configuration can cause entire mesh failure

**Best Practices:**
1. Use VirtualService, DestinationRule when possible
2. Use EnvoyFilter only as a last resort
3. Thoroughly test in test environment
4. Limit scope with workloadSelector

**Option Analysis:**
- A (X): Kubernetes Service creation is done with kubectl
- B (X): VirtualService is created manually
- C (O): Fine-grained customization of Envoy proxy behavior
- D (X): Istiod configuration is changed with IstioOperator

**Reference:**
- [EnvoyFilter](../../../service-mesh/istio/advanced/03-envoy-filter.md)
</details>

---

### Question 4: Sidecar Injection

How do you **disable automatic Sidecar injection** in Istio?

A. Remove `istio-injection=enabled` label from Namespace
B. Add `sidecar.istio.io/inject="false"` annotation to Pod
C. Restart Istiod
D. Both A and B are possible

<details>
<summary>Show Answer</summary>

**Answer: D**

Sidecar injection can be controlled at both the Namespace level and Pod level.

**Explanation:**

**Sidecar Injection Control Methods:**

**1. Namespace Level (A - O):**

```bash
# Enable Sidecar injection
kubectl label namespace default istio-injection=enabled

# Disable Sidecar injection
kubectl label namespace default istio-injection-

# Or change label
kubectl label namespace default istio-injection=disabled --overwrite
```

**2. Pod Level (B - O):**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
spec:
  template:
    metadata:
      annotations:
        sidecar.istio.io/inject: "false"  # Disable Sidecar injection
    spec:
      containers:
      - name: myapp
        image: myapp:latest
```

**Sidecar Injection Priority:**

```
Pod annotation > Namespace label > Default

Examples:
1. Namespace: istio-injection=enabled
   Pod: sidecar.istio.io/inject="false"
   Result: Sidecar not injected (Pod annotation takes priority)

2. Namespace: istio-injection=disabled
   Pod: sidecar.istio.io/inject="true"
   Result: Sidecar injected (Pod annotation takes priority)

3. Namespace: no label
   Pod: no annotation
   Result: Sidecar not injected (default)
```

**Verifying Sidecar Injection:**

```bash
# Check if Sidecar was injected into Pod
kubectl get pods <pod-name> -o jsonpath='{.spec.containers[*].name}'
# Example output: myapp istio-proxy (2 = Sidecar present)

# Check Sidecar injection logs
kubectl logs -n istio-system -l app=istiod --tail=100 | grep injection

# Check Namespace settings
kubectl get namespace -L istio-injection
```

**Mixed Environment Example:**

```yaml
# Inject Sidecar for entire Namespace
apiVersion: v1
kind: Namespace
metadata:
  name: production
  labels:
    istio-injection: enabled

---
# Exclude specific Pod only (e.g., legacy system)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: legacy-app
  namespace: production
spec:
  template:
    metadata:
      annotations:
        sidecar.istio.io/inject: "false"
    spec:
      containers:
      - name: legacy
        image: legacy:v1

---
# Most Pods automatically get Sidecar injected
apiVersion: apps/v1
kind: Deployment
metadata:
  name: modern-app
  namespace: production
spec:
  template:
    spec:
      containers:
      - name: modern
        image: modern:v2
```

**Option Analysis:**
- A (O): Sidecar injection can be controlled at Namespace level
- B (O): Sidecar injection can be controlled at Pod level
- C (X): Restarting Istiod is not necessary
- D (O): Both A and B are valid methods

**Reference:**
- [Sidecar Injection](../../../service-mesh/istio/advanced/07-sidecar-injection.md)
</details>

---

### Question 5: Argo Rollouts Integration

When using Argo Rollouts with Istio, what is responsible for **traffic splitting**?

A. Argo Rollouts Controller
B. Istio VirtualService
C. Kubernetes Service
D. Istio Gateway

<details>
<summary>Show Answer</summary>

**Answer: B**

**Istio VirtualService** performs the actual traffic splitting, and Argo Rollouts automatically updates the weight values in VirtualService.

**Explanation:**

**Argo Rollouts + Istio Integration Architecture:**

![Diagram showing user traffic entering through an Istio Gateway and VirtualService that splits weight between a stable and canary pod, while an Argo Rollouts controller updates that weight and manages the pods based on success or failure verdicts from an AnalysisTemplate fed by Prometheus metrics.](../../../../assets/diagrams/rendered/en-quizzes-service-mesh-istio-advanced-2.svg)

**VirtualService Role:**

```yaml
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: reviews
spec:
  hosts:
  - reviews
  http:
  - name: primary  # route name referenced by Argo Rollouts
    route:
    - destination:
        host: reviews
        subset: stable
      weight: 100  # Automatically changed by Argo Rollouts
    - destination:
        host: reviews
        subset: canary
      weight: 0    # Automatically changed by Argo Rollouts
```

**Argo Rollouts Configuration:**

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: reviews
spec:
  strategy:
    canary:
      # Istio integration settings
      trafficRouting:
        istio:
          virtualService:
            name: reviews        # VirtualService name
            routes:
            - primary            # route name
          destinationRule:
            name: reviews        # DestinationRule name
            canarySubsetName: canary
            stableSubsetName: stable

      # Canary steps
      steps:
      - setWeight: 10   # Change VirtualService weight to 10
      - pause: {duration: 2m}
      - setWeight: 25   # Change VirtualService weight to 25
      - pause: {duration: 2m}
      - setWeight: 50
      - pause: {duration: 2m}
```

**Deployment Process:**

```
1. Argo Rollouts creates new version (v2) Pods
   |
2. Argo Rollouts sets VirtualService canary weight to 10
   |
3. Istio Envoy routes actual 10% traffic to v2
   |
4. AnalysisTemplate checks metrics (error rate, latency)
   |
5. On success, Argo Rollouts increases weight to 25
   |
6. Repeat...
   |
7. Finally weight 100 (complete transition)
```

**Responsibility Division:**

| Component | Role |
|---------|------|
| **Argo Rollouts** | - Pod creation/deletion<br/>- VirtualService weight update<br/>- Deployment strategy execution<br/>- Automatic rollback |
| **Istio VirtualService** | - Actual traffic splitting<br/>- Routing rule application<br/>- Envoy configuration generation |
| **Envoy Proxy** | - Traffic routing execution<br/>- Metrics collection |
| **Prometheus** | - Metrics storage<br/>- Provide data to AnalysisTemplate |

**Actual Traffic Flow:**

```bash
# 100 user requests
100 requests -> Istio Gateway
              |
         VirtualService
         (weight: stable=90, canary=10)
              |
         +----+----+
         |         |
        90        10
    Stable v1   Canary v2
```

**Option Analysis:**
- A (X): Argo Rollouts only updates VirtualService (doesn't directly split traffic)
- B (O): VirtualService performs actual traffic splitting
- C (X): Kubernetes Service only handles load balancing (not traffic splitting)
- D (X): Gateway is external traffic entry point (not traffic splitting)

**Reference:**
- [Argo Rollouts](../../../service-mesh/istio/advanced/08-argo-rollouts.md)
</details>

---

## Short Answer Questions (6-10)

### Question 6: Ambient Mode Cost Savings Analysis

Calculate the **cost savings** when switching from Sidecar Mode to Ambient Mode in an AWS EKS cluster. (Assumptions: 500 Pods, 5 nodes, r5.xlarge instances, 730 hours/month operation)

<details>
<summary>Sample Answer</summary>

**Answer:**

**Cost Savings Analysis:**

---

**1. Assumptions**

```
Cluster scale:
- Pod count: 500
- Node count: 5
- Instance type: r5.xlarge (4 vCPU, 32GB RAM)
- Instance cost: $0.252/hour
- Operating hours: 730 hours/month

Resource usage:
- Sidecar memory: 50MB/Pod
- Sidecar CPU: 0.1 vCPU/Pod
- ztunnel memory: 50MB/Node
- ztunnel CPU: 0.1 vCPU/Node
- waypoint memory: 200MB
- waypoint CPU: 0.5 vCPU
```

---

**2. Sidecar Mode Resource Calculation**

```
Memory usage:
= 500 Pods × 50MB
= 25,000MB
= 25GB

CPU usage:
= 500 Pods × 0.1 vCPU
= 50 vCPU
```

**Required instance count (r5.xlarge: 4 vCPU, 32GB RAM):**

```
CPU basis:
= 50 vCPU ÷ 4 vCPU/instance
= 12.5 instances
≈ 13 instances needed

Memory basis:
= 25GB ÷ 32GB/instance
= 0.78 instances
≈ 1 instance needed

Actual needed: max(13, 1) = 13 instances
```

**Sidecar Mode Monthly Cost:**

```
= 13 instances × $0.252/hour × 730 hours
= $2,395.56/month
```

---

**3. Ambient Mode Resource Calculation**

```
Memory usage:
= (5 nodes × 50MB) + 200MB
= 250MB + 200MB
= 450MB

CPU usage:
= (5 nodes × 0.1 vCPU) + 0.5 vCPU
= 0.5 vCPU + 0.5 vCPU
= 1.0 vCPU
```

**Required instance count:**

```
CPU basis:
= 1.0 vCPU ÷ 4 vCPU/instance
= 0.25 instances
≈ 1 instance needed

Memory basis:
= 0.45GB ÷ 32GB/instance
= 0.01 instances
≈ 1 instance needed

Actual needed: max(1, 1) = 1 instance
```

**Ambient Mode Monthly Cost:**

```
= 1 instance × $0.252/hour × 730 hours
= $183.96/month
```

---

**4. Cost Savings**

```
Monthly savings:
= $2,395.56 - $183.96
= $2,211.60/month

Savings rate:
= ($2,211.60 ÷ $2,395.56) × 100
= 92.3%

Annual savings:
= $2,211.60 × 12
= $26,539.20/year
```

---

**5. Resource Savings Summary**

| Item | Sidecar Mode | Ambient Mode | Savings |
|------|-------------|-------------|------|
| **Memory** | 25GB | 0.45GB | 24.55GB (98.2%) |
| **CPU** | 50 vCPU | 1.0 vCPU | 49 vCPU (98.0%) |
| **Instances** | 13 | 1 | 12 (92.3%) |
| **Monthly Cost** | $2,395.56 | $183.96 | $2,211.60 (92.3%) |
| **Annual Cost** | $28,746.72 | $2,207.52 | $26,539.20 (92.3%) |

---

**6. Additional Cost Savings Factors**

**Network costs:**
- Sidecar Mode: No localhost communication (all traffic passes through network)
- Ambient Mode: Improved efficiency with direct communication between ztunnels

**Operational costs:**
- No Pod restarts required (reduced deployment time)
- No Sidecar injection errors
- Reduced management complexity

**Performance improvements:**
- Improved Pod performance due to reduced memory pressure
- Reduced OOMKilled frequency
- Node resource headroom

---

**7. ROI (Return on Investment)**

```
Ambient Mode transition cost (one-time):
- Learning time: 40 hours × $100/hour = $4,000
- Testing and validation: 20 hours × $100/hour = $2,000
- Total transition cost: $6,000

Payback period:
= $6,000 ÷ $2,211.60/month
= 2.7 months

3-year total savings:
= ($26,539.20 × 3) - $6,000
= $73,617.60
```

---

**8. Practical Considerations**

**Advantages:**
- 92%+ cost savings
- Simplified operations
- Improved deployment speed
- Maximized resource efficiency

**Cautions:**
- Istio 1.28+ beta feature
- Additional waypoint deployment needed for L7 features
- Some advanced features require Sidecar mode
- Thorough testing required

**Reference:**
- [Ambient Mode](../../../service-mesh/istio/advanced/01-ambient-mode.md)
</details>

---

### Question 7: Multi-cluster Service Mesh Configuration

Explain how to integrate 2 EKS clusters (us-east-1, us-west-2) into **a single Istio Mesh**. Use the **Primary-Remote model** and include examples of cross-cluster service calls.

<details>
<summary>Sample Answer</summary>

**Answer:**

**Multi-cluster Istio Mesh Configuration:**

---

**1. Architecture Overview**

![Diagram showing a primary Istiod in one region distributing configuration and service discovery to a remote cluster's Istiod, while workload pods in each cluster reach each other only through mutually authenticated east-west gateways.](../../../../assets/diagrams/rendered/en-quizzes-service-mesh-istio-advanced-3.svg)

---

**2. Prerequisites**

```bash
# Set up kubeconfig with access to both clusters
export CTX_CLUSTER1=eks-us-east-1
export CTX_CLUSTER2=eks-us-west-2

# Verify contexts
kubectl config get-contexts

# Generate CA certificates (shared Root CA)
mkdir -p certs
cd certs

# Generate Root CA
make -f ../istio-1.28.0/tools/certs/Makefile.selfsigned.mk root-ca

# Generate intermediate certificates for each cluster
make -f ../istio-1.28.0/tools/certs/Makefile.selfsigned.mk cluster1-cacerts
make -f ../istio-1.28.0/tools/certs/Makefile.selfsigned.mk cluster2-cacerts
```

---

**3. Cluster 1 (Primary) Setup**

```bash
# Create CA certificate Secret
kubectl create namespace istio-system --context="${CTX_CLUSTER1}"
kubectl create secret generic cacerts -n istio-system \
  --from-file=cluster1/ca-cert.pem \
  --from-file=cluster1/ca-key.pem \
  --from-file=cluster1/root-cert.pem \
  --from-file=cluster1/cert-chain.pem \
  --context="${CTX_CLUSTER1}"

# Install Primary Istio
istioctl install --context="${CTX_CLUSTER1}" -f - <<EOF
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  values:
    global:
      meshID: mesh1
      multiCluster:
        clusterName: cluster1
      network: network1

  components:
    ingressGateways:
    - name: istio-eastwestgateway
      label:
        istio: eastwestgateway
        app: istio-eastwestgateway
        topology.istio.io/network: network1
      enabled: true
      k8s:
        env:
        - name: ISTIO_META_REQUESTED_NETWORK_VIEW
          value: network1
        service:
          type: LoadBalancer
          ports:
          - name: status-port
            port: 15021
            targetPort: 15021
          - name: tls
            port: 15443
            targetPort: 15443
          - name: tls-istiod
            port: 15012
            targetPort: 15012
          - name: tls-webhook
            port: 15017
            targetPort: 15017
EOF

# Expose East-West Gateway
kubectl apply --context="${CTX_CLUSTER1}" -n istio-system -f \
  samples/multicluster/expose-services.yaml
```

---

**4. Cluster 2 (Remote) Setup**

```bash
# Create CA certificate Secret
kubectl create namespace istio-system --context="${CTX_CLUSTER2}"
kubectl create secret generic cacerts -n istio-system \
  --from-file=cluster2/ca-cert.pem \
  --from-file=cluster2/ca-key.pem \
  --from-file=cluster2/root-cert.pem \
  --from-file=cluster2/cert-chain.pem \
  --context="${CTX_CLUSTER2}"

# Create Remote Secret (access cluster2 from cluster1)
istioctl create-remote-secret \
  --context="${CTX_CLUSTER2}" \
  --name=cluster2 | \
  kubectl apply -f - --context="${CTX_CLUSTER1}"

# Install Remote Istio
istioctl install --context="${CTX_CLUSTER2}" -f - <<EOF
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  values:
    global:
      meshID: mesh1
      multiCluster:
        clusterName: cluster2
      network: network2
      remotePilotAddress: <CLUSTER1_EAST_WEST_GATEWAY_IP>

  components:
    ingressGateways:
    - name: istio-eastwestgateway
      label:
        istio: eastwestgateway
        app: istio-eastwestgateway
        topology.istio.io/network: network2
      enabled: true
      k8s:
        env:
        - name: ISTIO_META_REQUESTED_NETWORK_VIEW
          value: network2
        service:
          type: LoadBalancer
          ports:
          - name: status-port
            port: 15021
          - name: tls
            port: 15443
          - name: tls-istiod
            port: 15012
          - name: tls-webhook
            port: 15017
EOF
```

---

**5. Service Deployment and Verification**

**Deploy Service A to Cluster 1:**

```yaml
# cluster1: service-a.yaml
apiVersion: v1
kind: Service
metadata:
  name: service-a
  labels:
    app: service-a
spec:
  ports:
  - port: 8080
    name: http
  selector:
    app: service-a

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: service-a
spec:
  replicas: 2
  selector:
    matchLabels:
      app: service-a
  template:
    metadata:
      labels:
        app: service-a
    spec:
      containers:
      - name: service-a
        image: nginx:latest
        ports:
        - containerPort: 8080
```

```bash
kubectl apply --context="${CTX_CLUSTER1}" -f service-a.yaml
```

**Deploy Service B to Cluster 2:**

```yaml
# cluster2: service-b.yaml
apiVersion: v1
kind: Service
metadata:
  name: service-b
  labels:
    app: service-b
spec:
  ports:
  - port: 8080
    name: http
  selector:
    app: service-b

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: service-b
spec:
  replicas: 2
  selector:
    matchLabels:
      app: service-b
  template:
    metadata:
      labels:
        app: service-b
    spec:
      containers:
      - name: service-b
        image: nginx:latest
        ports:
        - containerPort: 8080
```

```bash
kubectl apply --context="${CTX_CLUSTER2}" -f service-b.yaml
```

---

**6. Cross-cluster Service Call Test**

```bash
# Call cluster 2 service from cluster 1
kubectl exec --context="${CTX_CLUSTER1}" -it \
  $(kubectl get pod --context="${CTX_CLUSTER1}" -l app=service-a -o jsonpath='{.items[0].metadata.name}') \
  -- curl http://service-b.default.svc.cluster.local:8080

# Call cluster 1 service from cluster 2
kubectl exec --context="${CTX_CLUSTER2}" -it \
  $(kubectl get pod --context="${CTX_CLUSTER2}" -l app=service-b -o jsonpath='{.items[0].metadata.name}') \
  -- curl http://service-a.default.svc.cluster.local:8080
```

---

**7. Verify Service Discovery**

```bash
# Check Envoy configuration from cluster 1
istioctl --context="${CTX_CLUSTER1}" proxy-config endpoints \
  $(kubectl get pod --context="${CTX_CLUSTER1}" -l app=service-a -o jsonpath='{.items[0].metadata.name}') | \
  grep service-b

# Example output:
# service-b.default.svc.cluster.local:8080  HEALTHY  <cluster2-pod-ip>:8080
```

---

**8. Apply Traffic Policies**

```yaml
# Cross-cluster traffic routing
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: service-b
spec:
  hosts:
  - service-b.default.svc.cluster.local
  http:
  - match:
    - sourceLabels:
        app: service-a
    route:
    - destination:
        host: service-b.default.svc.cluster.local
        port:
          number: 8080
      weight: 80  # 80% to local cluster
    - destination:
        host: service-b.default.svc.cluster.local
        port:
          number: 8080
      weight: 20  # 20% to remote cluster

---
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: service-b
spec:
  host: service-b.default.svc.cluster.local
  trafficPolicy:
    loadBalancer:
      localityLbSetting:
        enabled: true  # Locality-aware routing
```

---

**9. Monitoring and Verification**

```bash
# Check cross-cluster traffic in Prometheus
kubectl port-forward --context="${CTX_CLUSTER1}" -n istio-system \
  svc/prometheus 9090:9090

# Prometheus query:
# sum(rate(istio_requests_total{source_cluster="cluster1", destination_cluster="cluster2"}[5m]))

# Visualize with Kiali
istioctl dashboard kiali --context="${CTX_CLUSTER1}"
```

---

**10. Cautions and Best Practices**

**Cautions:**
- Shared Root CA is required
- Consider network latency
- Strengthen East-West Gateway security
- Properly configure DNS resolution

**Best Practices:**
- Enable locality-aware routing
- Configure Circuit Breaker
- Maintain replicas per cluster
- Monitor cross-cluster traffic

**Reference:**
- [Multi-cluster](../../../service-mesh/istio/advanced/02-multi-cluster.md)
</details>

---

### Question 8: Custom Rate Limiting with EnvoyFilter

Implement **per-user Rate Limiting** (100 requests per minute) using EnvoyFilter for a specific path (`/api/premium/*`) only.

<details>
<summary>Sample Answer</summary>

**Answer:**

**EnvoyFilter-based Rate Limiting Implementation:**

---

**1. Architecture Overview**

![Diagram showing a client request passing through the Envoy proxy, which checks a Redis-backed rate-limit store before forwarding an allowed request to the backend service or rejecting it with a 429 response.](../../../../assets/diagrams/rendered/en-quizzes-service-mesh-istio-advanced-4.svg)

---

**2. Deploy Redis Rate Limit Server**

```yaml
# redis-ratelimit.yaml
apiVersion: v1
kind: Service
metadata:
  name: redis-ratelimit
  namespace: istio-system
spec:
  ports:
  - port: 6379
    name: redis
  selector:
    app: redis-ratelimit

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: redis-ratelimit
  namespace: istio-system
spec:
  replicas: 1
  selector:
    matchLabels:
      app: redis-ratelimit
  template:
    metadata:
      labels:
        app: redis-ratelimit
    spec:
      containers:
      - name: redis
        image: redis:7-alpine
        ports:
        - containerPort: 6379
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 500m
            memory: 512Mi

---
# Envoy Rate Limit Service
apiVersion: v1
kind: ConfigMap
metadata:
  name: ratelimit-config
  namespace: istio-system
data:
  config.yaml: |
    domain: premium-ratelimit
    descriptors:
      # Per-user Rate Limit: 100 requests per minute
      - key: user_id
        rate_limit:
          unit: minute
          requests_per_unit: 100

---
apiVersion: v1
kind: Service
metadata:
  name: ratelimit
  namespace: istio-system
spec:
  ports:
  - port: 8081
    name: http
  - port: 9091
    name: grpc
  selector:
    app: ratelimit

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ratelimit
  namespace: istio-system
spec:
  replicas: 2
  selector:
    matchLabels:
      app: ratelimit
  template:
    metadata:
      labels:
        app: ratelimit
    spec:
      containers:
      - name: ratelimit
        image: envoyproxy/ratelimit:master
        ports:
        - containerPort: 8081
        - containerPort: 9091
        env:
        - name: REDIS_URL
          value: redis-ratelimit.istio-system.svc.cluster.local:6379
        - name: USE_STATSD
          value: "false"
        - name: LOG_LEVEL
          value: debug
        - name: RUNTIME_ROOT
          value: /data
        - name: RUNTIME_SUBDIRECTORY
          value: ratelimit
        volumeMounts:
        - name: config-volume
          mountPath: /data/ratelimit/config
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 500m
            memory: 512Mi
      volumes:
      - name: config-volume
        configMap:
          name: ratelimit-config
```

```bash
kubectl apply -f redis-ratelimit.yaml
```

---

**3. EnvoyFilter Configuration**

```yaml
# envoyfilter-ratelimit.yaml
apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata:
  name: premium-ratelimit
  namespace: istio-system
spec:
  workloadSelector:
    labels:
      app: api-gateway

  configPatches:
  # Add Rate Limit filter to HTTP filter chain
  - applyTo: HTTP_FILTER
    match:
      context: SIDECAR_INBOUND
      listener:
        filterChain:
          filter:
            name: "envoy.filters.network.http_connection_manager"
            subFilter:
              name: "envoy.filters.http.router"
    patch:
      operation: INSERT_BEFORE
      value:
        name: envoy.filters.http.ratelimit
        typed_config:
          "@type": type.googleapis.com/envoy.extensions.filters.http.ratelimit.v3.RateLimit
          domain: premium-ratelimit
          failure_mode_deny: true  # Deny on Rate Limit server failure
          enable_x_ratelimit_headers: DRAFT_VERSION_03
          rate_limit_service:
            grpc_service:
              envoy_grpc:
                cluster_name: rate_limit_cluster
            transport_api_version: V3

  # Define Rate Limit cluster
  - applyTo: CLUSTER
    patch:
      operation: ADD
      value:
        name: rate_limit_cluster
        type: STRICT_DNS
        connect_timeout: 1s
        lb_policy: ROUND_ROBIN
        http2_protocol_options: {}
        load_assignment:
          cluster_name: rate_limit_cluster
          endpoints:
          - lb_endpoints:
            - endpoint:
                address:
                  socket_address:
                    address: ratelimit.istio-system.svc.cluster.local
                    port_value: 9091

  # Add Rate Limit action to HTTP route
  - applyTo: HTTP_ROUTE
    match:
      context: SIDECAR_INBOUND
      routeConfiguration:
        vhost:
          route:
            action: ANY
    patch:
      operation: MERGE
      value:
        route:
          rate_limits:
          # Apply Rate Limit only to /api/premium/* path
          - actions:
            - header_value_match:
                descriptor_value: "premium"
                headers:
                - name: ":path"
                  prefix_match: "/api/premium/"
            - request_headers:
                header_name: "x-user-id"
                descriptor_key: "user_id"
```

```bash
kubectl apply -f envoyfilter-ratelimit.yaml
```

---

**4. Testing**

```bash
# Normal requests (under 100 requests/minute per user)
for i in {1..50}; do
  curl -H "x-user-id: user123" \
       -H "Host: api.example.com" \
       http://<INGRESS_GATEWAY>/api/premium/data
  sleep 0.1
done

# Output: 200 OK (all successful)

# Rate Limit exceeded (over 100 requests/minute)
for i in {1..150}; do
  curl -H "x-user-id: user123" \
       -H "Host: api.example.com" \
       http://<INGRESS_GATEWAY>/api/premium/data
done

# Output:
# 1-100: 200 OK
# 101-150: 429 Too Many Requests

# Other users unaffected
curl -H "x-user-id: user456" \
     -H "Host: api.example.com" \
     http://<INGRESS_GATEWAY>/api/premium/data

# Output: 200 OK
```

---

**5. Check Rate Limit Headers**

```bash
curl -I -H "x-user-id: user123" \
     -H "Host: api.example.com" \
     http://<INGRESS_GATEWAY>/api/premium/data

# Output:
# X-RateLimit-Limit: 100
# X-RateLimit-Remaining: 73
# X-RateLimit-Reset: 1735689600
```

---

**6. Cautions and Best Practices**

**Cautions:**
- Redis high availability configuration needed (production)
- Define behavior on Rate Limit server failure (`failure_mode_deny`)
- Ensure reliability of user identification header (`x-user-id`)
- EnvoyFilter requires compatibility check during Istio version upgrades

**Best Practices:**
- Use Redis Sentinel or Cluster
- Rate Limit server replicas >= 2
- Proper monitoring and alerting
- Per-user exception handling (VIP users, etc.)

**Reference:**
- [EnvoyFilter](../../../service-mesh/istio/advanced/03-envoy-filter.md)
- [Rate Limiting](../../../service-mesh/istio/resilience/02-rate-limiting.md)
</details>

---

### Question 9: Argo Rollouts Blue/Green Deployment

Implement **Blue/Green deployment** using Argo Rollouts and Istio. Include **automated analysis** (AnalysisTemplate) and configure automatic rollback on failure.

<details>
<summary>Sample Answer</summary>

**Answer:**

**Argo Rollouts Blue/Green Deployment Implementation:**

---

**1. Blue/Green Deployment Concept**

![Diagram showing an Istio Gateway sending production traffic to an active service backed by the current blue version, and preview traffic to a preview service backed by the new green version, while an AnalysisTemplate gates whether the rollout promotes to a traffic switch that swaps active and preview, or rolls back.](../../../../assets/diagrams/rendered/en-quizzes-service-mesh-istio-advanced-5.svg)

---

**2. Create Kubernetes Services**

```yaml
# services.yaml
apiVersion: v1
kind: Service
metadata:
  name: myapp-active
spec:
  ports:
  - port: 8080
    name: http
  selector:
    app: myapp
    # Argo Rollouts automatically manages selector

---
apiVersion: v1
kind: Service
metadata:
  name: myapp-preview
spec:
  ports:
  - port: 8080
    name: http
  selector:
    app: myapp
    # Argo Rollouts automatically manages selector
```

```bash
kubectl apply -f services.yaml
```

---

**3. Istio Gateway and VirtualService**

```yaml
# gateway.yaml
apiVersion: networking.istio.io/v1beta1
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
    - myapp.example.com

---
# virtualservice.yaml
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: myapp
spec:
  hosts:
  - myapp.example.com
  gateways:
  - myapp-gateway
  http:
  # Production traffic (Active)
  - match:
    - uri:
        prefix: /
    route:
    - destination:
        host: myapp-active
        port:
          number: 8080

---
# preview-virtualservice.yaml
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: myapp-preview
spec:
  hosts:
  - myapp-preview.example.com
  gateways:
  - myapp-gateway
  http:
  # Preview traffic (Preview)
  - match:
    - uri:
        prefix: /
    route:
    - destination:
        host: myapp-preview
        port:
          number: 8080
```

```bash
kubectl apply -f gateway.yaml
```

---

**4. AnalysisTemplate Definition**

```yaml
# analysis-template.yaml
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: success-rate
spec:
  args:
  - name: service-name

  metrics:
  # Metric 1: Success rate (95% or higher)
  - name: success-rate
    interval: 30s
    count: 5
    successCondition: result >= 0.95
    failureLimit: 2
    provider:
      prometheus:
        address: http://prometheus.istio-system:9090
        query: |
          sum(rate(
            istio_requests_total{
              destination_service_name="{{args.service-name}}",
              response_code!~"5.*"
            }[2m]
          ))
          /
          sum(rate(
            istio_requests_total{
              destination_service_name="{{args.service-name}}"
            }[2m]
          ))

---
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: latency
spec:
  args:
  - name: service-name

  metrics:
  # Metric 2: P95 latency (500ms or less)
  - name: latency-p95
    interval: 30s
    count: 5
    successCondition: result <= 500
    failureLimit: 2
    provider:
      prometheus:
        address: http://prometheus.istio-system:9090
        query: |
          histogram_quantile(0.95,
            sum(rate(
              istio_request_duration_milliseconds_bucket{
                destination_service_name="{{args.service-name}}"
              }[2m]
            )) by (le)
          )

---
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: error-rate
spec:
  args:
  - name: service-name

  metrics:
  # Metric 3: Error rate (1% or less)
  - name: error-rate
    interval: 30s
    count: 5
    successCondition: result <= 0.01
    failureLimit: 2
    provider:
      prometheus:
        address: http://prometheus.istio-system:9090
        query: |
          sum(rate(
            istio_requests_total{
              destination_service_name="{{args.service-name}}",
              response_code=~"5.*"
            }[2m]
          ))
          /
          sum(rate(
            istio_requests_total{
              destination_service_name="{{args.service-name}}"
            }[2m]
          ))
```

```bash
kubectl apply -f analysis-template.yaml
```

---

**5. Rollout Resource Definition**

```yaml
# rollout.yaml
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: myapp
spec:
  replicas: 5
  revisionHistoryLimit: 2
  selector:
    matchLabels:
      app: myapp

  template:
    metadata:
      labels:
        app: myapp
    spec:
      containers:
      - name: myapp
        image: myapp:v1
        ports:
        - containerPort: 8080
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 500m
            memory: 512Mi

  # Blue/Green deployment strategy
  strategy:
    blueGreen:
      # Active Service (production)
      activeService: myapp-active

      # Preview Service (test)
      previewService: myapp-preview

      # Disable auto promotion (manual promotion or Analysis-based)
      autoPromotionEnabled: false

      # Wait time after Green deployment
      scaleDownDelaySeconds: 30

      # Pre-promotion analysis (Green environment verification)
      prePromotionAnalysis:
        templates:
        - templateName: success-rate
        - templateName: latency
        - templateName: error-rate
        args:
        - name: service-name
          value: myapp-preview

      # Post-promotion analysis (verification after Active switch)
      postPromotionAnalysis:
        templates:
        - templateName: success-rate
        - templateName: latency
        - templateName: error-rate
        args:
        - name: service-name
          value: myapp-active
```

```bash
kubectl apply -f rollout.yaml
```

---

**6. Deploy New Version**

```bash
# Update to new version image
kubectl argo rollouts set image myapp \
  myapp=myapp:v2

# Monitor deployment status
kubectl argo rollouts get rollout myapp --watch

# Output:
# Name:            myapp
# Namespace:       default
# Status:          Paused
# Strategy:        BlueGreen
# Images:          myapp:v1 (stable, active)
#                  myapp:v2 (preview)
# Replicas:
#   Desired:       5
#   Current:       10
#   Updated:       5
#   Ready:         5
#   Available:     5
# Analysis:        Running
```

---

**7. Automatic Rollback Scenarios**

**Scenario 1: prePromotionAnalysis Failure**

```bash
# Error rate exceeds 1% in Green environment
# Analysis log:
# error-rate: FAILED (0.03 > 0.01)
# failureLimit: 2/2

# Automatic rollback executed
# Green Pods deleted
# Blue continues as Active

kubectl argo rollouts get rollout myapp
# Status: Degraded
# Message: PrePromotionAnalysis Failed
```

**Scenario 2: postPromotionAnalysis Failure**

```bash
# Success rate below 95% after Active switch
# Analysis log:
# success-rate: FAILED (0.92 < 0.95)
# failureLimit: 2/2

# Automatic rollback executed
# Immediately restore Active Service to Blue
# Green moves to Preview

kubectl argo rollouts get rollout myapp
# Status: Degraded
# Message: PostPromotionAnalysis Failed
```

---

**8. Best Practices**

**Advantages:**
- Immediate rollback possible (switch transition)
- Minimal production impact
- Sufficient testing time secured
- Automated analysis and rollback

**Cautions:**
- 2x resources required (Blue + Green)
- Verify database schema compatibility
- Session management (if Sticky Session needed)

**Reference:**
- [Argo Rollouts](../../../service-mesh/istio/advanced/08-argo-rollouts.md)
</details>

---

### Question 10: DNS Caching Performance Optimization

Explain how to enable **DNS Caching** in Istio to improve external service call performance. Include **benchmark results**.

<details>
<summary>Sample Answer</summary>

**Answer:**

**Istio DNS Caching Implementation and Performance Measurement:**

---

**1. Need for DNS Caching**

**Problem: DNS Lookup Overhead**

```
DNS lookup occurs for each external API call:
1. Application -> Envoy: HTTP request
2. Envoy -> CoreDNS: DNS lookup (50-100ms)
3. CoreDNS -> Response: IP address
4. Envoy -> External API: HTTP request (100-200ms)

Total latency: 150-300ms
```

**Solution: Enable DNS Caching**

```
After DNS Caching:
1. Application -> Envoy: HTTP request
2. Envoy: Use cached IP (0ms)
3. Envoy -> External API: HTTP request (100-200ms)

Total latency: 100-200ms (33-50% improvement)
```

---

**2. Register External Service with ServiceEntry**

```yaml
# external-api-serviceentry.yaml
apiVersion: networking.istio.io/v1beta1
kind: ServiceEntry
metadata:
  name: external-api
spec:
  hosts:
  - api.github.com
  ports:
  - number: 443
    name: https
    protocol: HTTPS
  location: MESH_EXTERNAL
  resolution: DNS  # Use DNS resolution
```

```bash
kubectl apply -f external-api-serviceentry.yaml
```

---

**3. Enable DNS Caching with DestinationRule**

```yaml
# destinationrule-dns-cache.yaml
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: external-api
spec:
  host: api.github.com
  trafficPolicy:
    # DNS refresh interval: 5 minutes
    # (DNS re-lookup every 5 minutes even if TTL is 0)
    dnsRefreshRate: 5m

    # Connection Pool settings
    connectionPool:
      tcp:
        maxConnections: 100
      http:
        http1MaxPendingRequests: 50
        http2MaxRequests: 100
        maxRequestsPerConnection: 10

    # Outlier Detection
    outlierDetection:
      consecutiveErrors: 5
      interval: 30s
      baseEjectionTime: 30s
```

```bash
kubectl apply -f destinationrule-dns-cache.yaml
```

---

**4. Performance Benchmark**

**DNS Caching Disabled (Before):**

```bash
# 100 consecutive call test
kubectl exec -it test-app -- sh -c '
for i in $(seq 1 100); do
  time curl -s -o /dev/null -w "%{time_total}\n" https://api.github.com/users/octocat
done' | awk '{sum+=$1; count++} END {print "Average response time:", sum/count, "seconds"}'

# Output:
# Average response time: 0.287 seconds
```

**DNS Caching Enabled (After):**

```bash
# Same test after applying DestinationRule
kubectl exec -it test-app -- sh -c '
for i in $(seq 1 100); do
  time curl -s -o /dev/null -w "%{time_total}\n" https://api.github.com/users/octocat
done' | awk '{sum+=$1; count++} END {print "Average response time:", sum/count, "seconds"}'

# Output:
# Average response time: 0.152 seconds
```

**Performance Improvement:**

```
Before: 287ms
After: 152ms
Improvement: (287 - 152) / 287 = 47%

DNS lookup time saved: ~135ms
```

---

**5. Verify Envoy Statistics**

```bash
# Envoy DNS cache statistics
kubectl exec -it test-app -c istio-proxy -- \
  curl localhost:15000/stats | grep dns_cache

# Output:
# cluster.outbound|443||api.github.com.dns_cache_hits: 99
# cluster.outbound|443||api.github.com.dns_cache_misses: 1
# cluster.outbound|443||api.github.com.dns_refresh: 0

# Cache hit rate: 99 / (99 + 1) = 99%
```

---

**6. Comparison Table**

| Item | DNS Caching Disabled | DNS Caching Enabled | Improvement |
|------|---------------------|-------------------|------|
| **Average Response Time** | 287ms | 152ms | 47% reduction |
| **P95 Response Time** | 350ms | 180ms | 49% reduction |
| **P99 Response Time** | 420ms | 210ms | 50% reduction |
| **Throughput (RPS)** | 12.34 | 23.15 | 88% increase |
| **DNS Cache Hit Rate** | 0% | 99% | - |
| **Connection Reuse Rate** | 0% | 95% | - |

---

**7. Best Practices**

**Recommended Settings:**
- DNS refresh interval: 5-15 minutes (consider external service TTL)
- Enable Connection Pool (connection reuse)
- Use HTTP/2 (multiplexing)
- Enable Keep-Alive

**Cautions:**
- Reduce refresh interval for services with short TTL
- Consider cache invalidation time during DNS changes
- Test failover scenarios

**Reference:**
- [DNS Caching](../../../service-mesh/istio/advanced/04-dns-cache.md)
</details>

---

## Scoring

- Multiple Choice 1-5: 10 points each (Total 50 points)
- Short Answer 6-10: 10 points each (Total 50 points)
- **Total: 100 points**

**Evaluation Criteria:**
- 90-100 points: Excellent (Istio Advanced Features Expert)
- 80-89 points: Good (Advanced feature utilization possible)
- 70-79 points: Average (Additional study recommended)
- 60-69 points: Below Average (Basic concept review needed)
- 0-59 points: Re-study required

## Study Materials

- [Ambient Mode](../../../service-mesh/istio/advanced/01-ambient-mode.md)
- [Multi-cluster](../../../service-mesh/istio/advanced/02-multi-cluster.md)
- [EnvoyFilter](../../../service-mesh/istio/advanced/03-envoy-filter.md)
- [DNS Caching](../../../service-mesh/istio/advanced/04-dns-cache.md)
- [gRPC](../../../service-mesh/istio/advanced/05-grpc.md)
- [WebSocket](../../../service-mesh/istio/advanced/06-websocket.md)
- [Sidecar Injection](../../../service-mesh/istio/advanced/07-sidecar-injection.md)
- [Argo Rollouts](../../../service-mesh/istio/advanced/08-argo-rollouts.md)
