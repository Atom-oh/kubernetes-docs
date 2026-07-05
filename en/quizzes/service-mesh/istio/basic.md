# Basic Quiz

> **Supported Version**: Istio 1.28.0 **EKS Version**: 1.34 (Kubernetes 1.28+) **Last Updated**: February 23, 2026

This quiz tests your understanding of Istio's basic concepts and architecture.

## Multiple Choice Questions (1-5)

### Question 1: Definition of Service Mesh

Which statement about Service Mesh is **NOT correct**?

A. It is an infrastructure layer that handles communication between microservices B. It can only be used by modifying application code C. It provides traffic control and observability between services D. It applies security and policies at the network level

<details>

<summary>Show Answer</summary>

**Answer: B**

One of the core advantages of Service Mesh is that it can control and observe communication between services **without changing application code**.

**Explanation:**

* A (O): Service Mesh is a dedicated infrastructure layer responsible for communication between services in microservice architecture
* B (X): It is transparently applied through sidecar proxies or Ambient Mode without changing application code
* C (O): It controls traffic with VirtualService, DestinationRule, etc., and automatically collects metrics/logs/traces
* D (O): It applies security policies at the network level with mTLS, Authorization Policy, etc.

**Reference:**

* [Istio Core Concepts](../../../service-mesh/istio/02-basic-concepts.md)
* [What is Service Mesh?](https://github.com/Atom-oh/kubernetes-docs/blob/main/en/service-mesh/02-istio.md#introduction)

</details>

***

### Question 2: Istio Architecture Components

In Istio's Control Plane, which is the **centralized component** responsible for service discovery, configuration management, and certificate management?

A. Envoy B. Istiod C. Pilot D. Citadel

<details>

<summary>Show Answer</summary>

**Answer: B**

**Istiod** is a single binary introduced in Istio 1.5 that integrates the previous Pilot, Citadel, and Galley components.

**Explanation:**

* A (X): Envoy is a Data Plane proxy that runs as a sidecar in each pod
* B (O): Istiod is the core of the Control Plane and handles:
  * Service Discovery
  * Configuration Management
  * Certificate Management
* C (X): Pilot was a component in Istio versions before 1.5, now integrated into Istiod
* D (X): Citadel was also a component in Istio versions before 1.5, now integrated into Istiod

**Istiod's Key Roles:**

```yaml
# Configurations managed by Istiod
1. Service Discovery: Kubernetes Service -> Envoy Cluster
2. Config Distribution: VirtualService, DestinationRule -> Envoy Config
3. Certificate Issuance: Service Account -> mTLS Certificate
```

**Reference:**

* [Istio Components](../../../service-mesh/istio/03-architecture.md)
* [Architecture Overview](https://github.com/Atom-oh/kubernetes-docs/blob/main/en/service-mesh/02-istio.md#architecture-overview)

</details>

***

### Question 3: Role of Envoy Proxy

Which is **NOT** a task performed by the Data Plane's Envoy proxy?

A. Traffic routing and load balancing B. mTLS encryption and authentication C. Kubernetes CRD validation and storage D. Metrics, logs, and trace collection

<details>

<summary>Show Answer</summary>

**Answer: C**

Kubernetes CRD validation and storage is the role of the Control Plane (Istiod).

**Explanation:**

* A (O): Envoy routes traffic and load balances according to VirtualService rules
* B (O): Envoy automatically encrypts service-to-service communication with mTLS and validates certificates
* C (X): CRD validation and storage is the role of Kubernetes API Server and Istiod
* D (O): Envoy collects metrics (Prometheus), logs (Access Log), and traces (Jaeger) for all requests

**Reference:**

* [Data Plane Structure](../../../service-mesh/istio/03-architecture.md#data-plane-envoy-proxy)

</details>

***

### Question 4: Istio Installation Profiles

Which profile is **recommended** when installing Istio in an Amazon EKS production environment?

A. default B. demo C. minimal D. production

<details>

<summary>Show Answer</summary>

**Answer: D**

For production environments, the **production** profile should be used.

**Explanation:**

**Istio Installation Profile Comparison:**

| Profile        | Purpose             | Characteristics                           |
| -------------- | ------------------- | ----------------------------------------- |
| **default**    | Development/Testing | Default configuration, medium resources   |
| **demo**       | Demo/Learning       | All features enabled, high resource usage |
| **minimal**    | Minimal Setup       | Control Plane only                        |
| **production** | Production          | HA configuration, high availability       |

**Production Profile Characteristics:**

```bash
# Production profile installation
istioctl install --set profile=production -y

# Key characteristics:
# - Istiod replica: 3 (HA)
# - PodDisruptionBudget configured
# - Resource limits properly set
# - Ingress/Egress Gateway included
```

**Production Checklist:**

* ✅ Control Plane HA (replica ≥ 3)
* ✅ mTLS STRICT mode
* ✅ PodDisruptionBudget configured
* ✅ Resource limits and HPA configured
* ✅ Monitoring stack ready

**Reference:**

* [Installation Guide](../../../service-mesh/istio/01-installation.md)
* [Best Practices](../../../service-mesh/istio/best-practices.md#production-checklist)

</details>

***

### Question 5: Istio CRD (Custom Resource Definition)

Which of the following is **NOT** a CRD for Istio's **traffic management**?

A. VirtualService B. DestinationRule C. PeerAuthentication D. Gateway

<details>

<summary>Show Answer</summary>

**Answer: C**

**PeerAuthentication** is a security-related CRD.

**Explanation:**

**Istio CRD Classification:**

**1. Traffic Management:**

* VirtualService: Define routing rules
* DestinationRule: Load balancing, subset definition
* Gateway: External traffic entry point
* ServiceEntry: External service definition
* Sidecar: Limit Envoy configuration scope

**2. Security:**

* PeerAuthentication: Service-to-service authentication (mTLS)
* RequestAuthentication: End-user authentication (JWT)
* AuthorizationPolicy: Access control

**3. Observability:**

* Telemetry: Metrics, logs, traces configuration

**Example:**

```yaml
# Traffic Management
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: reviews
spec:
  hosts:
  - reviews
  http:
  - route:
    - destination:
        host: reviews
        subset: v1

---
# Security
apiVersion: security.istio.io/v1beta1
kind: PeerAuthentication
metadata:
  name: default
spec:
  mtls:
    mode: STRICT
```

**Reference:**

* [Traffic Management](../../../service-mesh/istio/traffic-management/)
* [Security](../../../service-mesh/istio/security/)

</details>

***

## Short Answer Questions (6-10)

### Question 6: Sidecar Injection Mechanism

Explain two methods for automatically injecting Envoy Sidecar into Pods in Istio, and compare the pros and cons of each.

<details>

<summary>Show Answer</summary>

**Answer:**

Istio automatically injects Sidecars using two methods:

**1. Namespace-level Automatic Injection:**

```bash
# Add label to Namespace
kubectl label namespace default istio-injection=enabled

# All Pods deployed afterward will have automatic injection
kubectl apply -f deployment.yaml
```

**Pros:**

* Can be applied to entire Namespace at once
* Easy management
* Low chance of accidental omission

**Cons:**

* Applies to all Pods in the Namespace (selective exclusion needed)
* Existing Pods need restart

**2. Pod-level Selective Injection:**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
spec:
  template:
    metadata:
      labels:
        sidecar.istio.io/inject: "true"  # or "false"
    spec:
      containers:
      - name: myapp
        image: myapp:latest
```

**Pros:**

* Can selectively inject only specific Pods
* Fine-grained control possible
* No Namespace label required

**Cons:**

* Configuration needed for each Deployment
* Increased management points
* Chance of accidental omission

**Comparison Table:**

| Item                  | Namespace Level         | Pod Level          |
| --------------------- | ----------------------- | ------------------ |
| Scope                 | Entire Namespace        | Individual Pod     |
| Management Complexity | Low                     | High               |
| Selectivity           | Low (exclusion needed)  | High               |
| Recommended Use       | Production environments | Mixed environments |

**Production Recommendation:**

* Use Namespace level by default
* Only set `sidecar.istio.io/inject: "false"` for Pods that need exclusion

**Reference:**

* [Sidecar Injection](../../../service-mesh/istio/advanced/07-sidecar-injection.md)

</details>

***

### Question 7: Istio Resource Usage Optimization

Calculate and compare the **expected resource usage** when using Istio in a large-scale Kubernetes cluster with 1000 Pods between Sidecar Mode and Ambient Mode. (Assume ztunnel is deployed on 10 nodes and there is 1 waypoint)

<details>

<summary>Show Answer</summary>

**Answer:**

**Assumptions:**

* Number of Pods: 1000
* Number of Nodes: 10
* Sidecar Memory: 50MB/Pod
* ztunnel Memory: 50MB/Node
* waypoint Memory: 200MB

**1. Sidecar Mode Resource Usage:**

```
Memory Usage = Number of Pods × Sidecar Memory
             = 1000 × 50MB
             = 50,000MB
             = 50GB

CPU Usage = Number of Pods × Sidecar CPU
          = 1000 × 0.1 vCPU
          = 100 vCPU
```

**2. Ambient Mode Resource Usage:**

```
Memory Usage = (Number of Nodes × ztunnel Memory) + waypoint Memory
             = (10 × 50MB) + 200MB
             = 500MB + 200MB
             = 700MB

CPU Usage = (Number of Nodes × ztunnel CPU) + waypoint CPU
          = (10 × 0.1 vCPU) + 0.5 vCPU
          = 1.5 vCPU
```

**3. Comparison and Savings:**

| Item       | Sidecar Mode | Ambient Mode | Savings   | Savings Rate |
| ---------- | ------------ | ------------ | --------- | ------------ |
| **Memory** | 50GB         | 0.7GB        | 49.3GB    | **98.6%**    |
| **CPU**    | 100 vCPU     | 1.5 vCPU     | 98.5 vCPU | **98.5%**    |

**Cost Calculation (AWS EKS basis):**

```
# r5.xlarge: 4 vCPU, 32GB RAM, $0.252/hour

Sidecar Mode:
- CPU: 100 vCPU → 25 instances needed
- Memory: 50GB → 2 instances needed
- Required instances: max(25, 2) = 25
- Monthly cost: 25 × $0.252 × 24 × 30 = $4,536

Ambient Mode:
- CPU: 1.5 vCPU → 1 instance sufficient
- Memory: 0.7GB → 1 instance sufficient
- Required instances: 1
- Monthly cost: 1 × $0.252 × 24 × 30 = $181

Monthly cost savings: $4,536 - $181 = $4,355 (96%)
```

**Conclusion:**

* Ambient Mode provides **96% or more cost savings** in large-scale clusters
* At 1000 Pod scale, approximately **$4,300 monthly savings**
* Resource usage reduced by **more than 98%**

**Notes:**

* Additional waypoints needed when L7 features are required
* Ambient Mode is a beta feature in Istio 1.28+

**Reference:**

* [Ambient Mode](../../../service-mesh/istio/advanced/01-ambient-mode.md#resource-usage-comparison)
* [Cost Optimization](../../../service-mesh/istio/best-practices.md#cost-optimization)

</details>

***

### Question 8: mTLS Operation Mechanism

Explain step by step how mTLS works when two services (service-a and service-b) communicate in Istio. Include the roles of Istiod, Envoy, and Certificate.

<details>

<summary>Show Answer</summary>

**Answer:**

**mTLS (Mutual TLS) Operation Process:**

**Step 1: Certificate Issuance (Bootstrap)**

* When Pod starts, Envoy requests a certificate (CSR) from Istiod using its Service Account
* Istiod validates the Service Account and issues an X.509 certificate
* The certificate contains the Service Account ID (e.g., `cluster.local/ns/default/sa/service-a`)
* Certificate validity: 24 hours by default (auto-renewed)

**Step 2: Service-to-Service Communication (mTLS Handshake)**

```
Service A → Envoy A → [mTLS] → Envoy B → Service B
```

**Detailed Process:**

```yaml
# Service A calls Service B
1. Service A → Envoy A (localhost:outbound)
   - Application sends plaintext HTTP request

2. Envoy A: Outbound Processing
   - Check configuration received from Istiod
   - Check PeerAuthentication policy (STRICT mTLS)
   - Start connection to Service B's Envoy B

3. TLS Handshake (Envoy A ↔ Envoy B)
   a. Envoy A → Envoy B: ClientHello
      - Present own certificate
      - Present supported encryption algorithms

   b. Envoy B → Envoy A: ServerHello
      - Present own certificate
      - Selected encryption algorithm

   c. Mutual Certificate Validation
      - Envoy A: Validate Service B's certificate
      - Envoy B: Validate Service A's certificate
      - Verify signature with Istiod's Root CA

   d. Generate Encrypted Session Key
      - Create TLS 1.3 encrypted channel

4. Envoy B → Service B (localhost:inbound)
   - Deliver decrypted plaintext HTTP request

5. Service B → Envoy B → [mTLS] → Envoy A → Service A
   - Response uses same encrypted channel
```

**Roles of Each Component:**

**Istiod:**

* Acts as Root CA (certificate signing)
* Issues certificates based on Service Account
* Auto-renews certificates (every 24 hours)
* Distributes PeerAuthentication policies

**Envoy Sidecar:**

* Requests and renews certificates
* Performs TLS handshake
* Encrypts/decrypts traffic
* Validates certificates

**Certificate:**

* X.509 certificate format
* Subject Alternative Name (SAN): Service Account URI
* Validity: 24 hours (default)
* Auto-renewed

**Configuration Example:**

```yaml
# PeerAuthentication - STRICT mTLS
apiVersion: security.istio.io/v1beta1
kind: PeerAuthentication
metadata:
  name: default
  namespace: istio-system
spec:
  mtls:
    mode: STRICT  # Force all communication to mTLS
```

**Certificate Verification:**

```bash
# Check Pod's certificate
istioctl proxy-config secret <pod-name> -o json

# Example output:
{
  "name": "default",
  "tlsCertificate": {
    "certificateChain": "...",
    "privateKey": "...",
    "subjectAltNames": [
      "spiffe://cluster.local/ns/default/sa/service-a"
    ]
  }
}
```

**Security Benefits:**

1. **Confidentiality**: All communication encrypted
2. **Integrity**: Data tampering prevention
3. **Authentication**: Bidirectional identity verification
4. **Automation**: Applied without code changes

**Reference:**

* [mTLS](../../../service-mesh/istio/security/01-mtls.md)
* [Certificate Management](../../../service-mesh/istio/03-architecture.md#certificate-management)

</details>

***

### Question 9: Istio Debugging

Write a step-by-step debugging method for diagnosing problems when a newly deployed service cannot communicate in the Istio mesh. (At least 5 steps)

<details>

<summary>Show Answer</summary>

**Answer:**

**Istio Service Communication Debugging Checklist:**

**Step 1: Check Pod and Sidecar Status**

```bash
# Check if Pod is running normally
kubectl get pods -n <namespace>

# Check if Sidecar is injected (should have 2 containers)
kubectl get pods <pod-name> -n <namespace> -o jsonpath='{.spec.containers[*].name}'
# Expected output: myapp istio-proxy

# Detailed Sidecar injection check
kubectl describe pod <pod-name> -n <namespace> | grep -A 5 "Containers:"

# Check Pod logs
kubectl logs <pod-name> -n <namespace> -c myapp        # Application logs
kubectl logs <pod-name> -n <namespace> -c istio-proxy  # Envoy logs
```

**Diagnosis:**

* If only 1 container → Sidecar not injected
* If Pod is CrashLoopBackOff → Application or Sidecar initialization failed

**Resolution:**

```bash
# Check Namespace injection label
kubectl get namespace <namespace> --show-labels

# Add label if missing
kubectl label namespace <namespace> istio-injection=enabled

# Restart Pod
kubectl rollout restart deployment/<deployment-name> -n <namespace>
```

***

**Step 2: Check Service and Endpoint**

```bash
# Check Service exists
kubectl get svc <service-name> -n <namespace>

# Check Service Endpoint (is Pod IP registered)
kubectl get endpoints <service-name> -n <namespace>

# Service details
kubectl describe svc <service-name> -n <namespace>
```

**Diagnosis:**

* If Endpoint is empty → Service Selector and Pod Label mismatch
* Service port and Pod port mismatch

**Resolution:**

```bash
# Check Pod labels
kubectl get pods <pod-name> -n <namespace> --show-labels

# Check Service Selector
kubectl get svc <service-name> -n <namespace> -o yaml | grep -A 3 selector
```

***

**Step 3: Check Istio Configuration**

```bash
# Check VirtualService
kubectl get virtualservice -n <namespace>
kubectl describe virtualservice <vs-name> -n <namespace>

# Check DestinationRule
kubectl get destinationrule -n <namespace>
kubectl describe destinationrule <dr-name> -n <namespace>

# Check Gateway (for external access)
kubectl get gateway -n <namespace>

# Validate Istio configuration
istioctl analyze -n <namespace>
```

**Diagnosis:**

* Check `istioctl analyze` error messages
* Whether VirtualService host matches Service name
* Whether DestinationRule subset labels match Pod labels

**Resolution:**

```bash
# Auto-detect configuration errors
istioctl analyze -n <namespace>

# Example output:
# Error [IST0101] (VirtualService reviews.default)
# Referenced host not found: reviews
```

***

**Step 4: Check mTLS and Security Policies**

```bash
# Check PeerAuthentication policies
kubectl get peerauthentication -A

# Check mTLS mode for specific Pod
istioctl authn tls-check <pod-name>.<namespace> <service-name>.<namespace>.svc.cluster.local

# Check AuthorizationPolicy
kubectl get authorizationpolicy -n <namespace>
```

**Diagnosis:**

* mTLS mode mismatch (STRICT vs PERMISSIVE)
* AuthorizationPolicy blocking traffic

**Resolution:**

```bash
# Temporarily change to PERMISSIVE mode (for debugging)
kubectl apply -f - <<EOF
apiVersion: security.istio.io/v1beta1
kind: PeerAuthentication
metadata:
  name: default
  namespace: <namespace>
spec:
  mtls:
    mode: PERMISSIVE
EOF

# Temporarily delete AuthorizationPolicy
kubectl delete authorizationpolicy <policy-name> -n <namespace>
```

***

**Step 5: Check Envoy Configuration**

```bash
# Check Envoy cluster configuration (service discovery)
istioctl proxy-config clusters <pod-name> -n <namespace>

# Check Envoy listener configuration (inbound/outbound)
istioctl proxy-config listeners <pod-name> -n <namespace>

# Check Envoy route configuration
istioctl proxy-config routes <pod-name> -n <namespace>

# Check Envoy endpoints
istioctl proxy-config endpoints <pod-name> -n <namespace>
```

**Diagnosis:**

* If target service not in clusters → Istiod not recognizing the service
* If no listeners → Port configuration error
* If endpoints are UNHEALTHY → Pod not ready

***

**Step 6: Network Connection Test**

```bash
# Test directly from inside Pod
kubectl exec -it <source-pod> -n <namespace> -- curl http://<target-service>:<port>

# Test directly without going through Envoy (by Pod IP)
kubectl exec -it <source-pod> -n <namespace> -- curl http://<pod-ip>:<port>

# Check DNS resolution
kubectl exec -it <source-pod> -n <namespace> -- nslookup <service-name>

# Check statistics via Envoy Admin API
kubectl exec -it <pod-name> -n <namespace> -c istio-proxy -- curl localhost:15000/stats | grep <service-name>
```

***

**Step 7: Check Istiod Logs**

```bash
# Check Istiod logs (configuration push errors)
kubectl logs -n istio-system -l app=istiod --tail=100

# Check xDS configuration push status
istioctl proxy-status

# Specific Pod synchronization status
istioctl proxy-status <pod-name>.<namespace>
```

***

**Step 8: Check Metrics and Tracing**

```bash
# Check metrics in Prometheus
kubectl port-forward -n istio-system svc/prometheus 9090:9090

# Check traces in Jaeger
kubectl port-forward -n istio-system svc/tracing 16686:16686

# Check topology in Kiali
istioctl dashboard kiali
```

***

**Troubleshooting Flowchart:**

```
1. Pod/Sidecar normal?
   ├─ NO → Check Sidecar injection
   └─ YES → Step 2

2. Service/Endpoint normal?
   ├─ NO → Check Selector
   └─ YES → Step 3

3. Istio configuration normal?
   ├─ NO → Run istioctl analyze
   └─ YES → Step 4

4. mTLS/policies normal?
   ├─ NO → Test PERMISSIVE mode
   └─ YES → Step 5

5. Envoy configuration normal?
   ├─ NO → Restart Istiod
   └─ YES → Step 6

6. Network connection normal?
   ├─ NO → Check NetworkPolicy
   └─ YES → Analyze logs/metrics
```

**Reference:**

* [Istio Debugging Guide](https://istio.io/latest/docs/ops/diagnostic-tools/)

</details>

***

### Question 10: Istio Upgrade Strategy

Explain the **Canary Upgrade** strategy for upgrading Istio from 1.27.0 to 1.28.0 in a production environment. Include step-by-step commands and verification methods.

<details>

<summary>Show Answer</summary>

**Answer:**

**Istio Canary Upgrade Strategy:**

Canary Upgrade is a safe upgrade approach that runs both old and new Control Plane versions simultaneously and gradually migrates workloads.

***

**Preparation:**

```bash
# 1. Check current version
istioctl version

# 2. Create backup
kubectl get istiooperator -A -o yaml > istio-1.27-backup.yaml
kubectl get vs,dr,gw,se,pa,ra,ap -A -o yaml > istio-config-backup.yaml

# 3. Download new version
curl -L https://istio.io/downloadIstio | ISTIO_VERSION=1.28.0 sh -
cd istio-1.28.0
export PATH=$PWD/bin:$PATH

# 4. Check compatibility
istioctl x precheck
```

***

**Step 1: Install New Control Plane (using revision)**

```bash
# Install new version Control Plane using Revision
istioctl install --set revision=1-28-0 --set profile=production -y

# Verify installation
kubectl get pods -n istio-system -l app=istiod
# Example output:
# istiod-1-27-0-xxxx  (old version)
# istiod-1-28-0-xxxx  (new version)

# Check Revision
kubectl get mutatingwebhookconfigurations | grep istio
# Output:
# istio-sidecar-injector-1-27-0
# istio-sidecar-injector-1-28-0
```

**Important:** At this point, **two Control Planes** are running simultaneously.

***

**Step 2: Canary Validation with Test Namespace**

```bash
# Create test namespace
kubectl create namespace istio-upgrade-test

# Label for new version
kubectl label namespace istio-upgrade-test istio.io/rev=1-28-0

# Deploy test application
kubectl apply -n istio-upgrade-test -f samples/sleep/sleep.yaml
kubectl apply -n istio-upgrade-test -f samples/httpbin/httpbin.yaml

# Check Sidecar version (should be 1.28.0)
kubectl get pods -n istio-upgrade-test -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.containers[?(@.name=="istio-proxy")].image}{"\n"}{end}'

# Test communication
kubectl exec -n istio-upgrade-test deploy/sleep -- curl http://httpbin:8000/headers

# Check Envoy configuration
istioctl proxy-config clusters deploy/sleep.istio-upgrade-test
```

**Verification Checklist:**

* ✅ Is Sidecar injected with version 1.28.0?
* ✅ Is service-to-service communication normal?
* ✅ Is mTLS working correctly?
* ✅ Are metrics being collected?

***

**Step 3: Migrate Staging Namespace**

```bash
# Switch staging namespace to new version
kubectl label namespace staging istio.io/rev=1-28-0 --overwrite

# Remove existing label (if present)
kubectl label namespace staging istio-injection-

# Restart Pods (inject new version Sidecar)
kubectl rollout restart deployment -n staging

# Monitor restart status
kubectl rollout status deployment -n staging

# Verify version
kubectl get pods -n staging -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.containers[?(@.name=="istio-proxy")].image}{"\n"}{end}'
```

**Verification:**

```bash
# Check metrics
kubectl exec -n staging <pod-name> -c istio-proxy -- curl localhost:15000/stats/prometheus | grep istio_build

# Test communication
kubectl exec -n staging <pod-name> -- curl http://<service-name>

# Visual confirmation with Kiali
istioctl dashboard kiali
```

**Monitor for 24-48 hours:**

* Check Prometheus metrics
* Compare error rates and latency
* Check Istiod resource usage

***

**Step 4: Gradual Migration of Production Namespaces**

```bash
# List of production Namespaces
PROD_NAMESPACES="prod-api prod-web prod-worker"

# Migrate one at a time gradually
for ns in $PROD_NAMESPACES; do
  echo "Upgrading namespace: $ns"

  # Update label
  kubectl label namespace $ns istio.io/rev=1-28-0 --overwrite

  # Restart Pods
  kubectl rollout restart deployment -n $ns

  # Wait for completion
  kubectl rollout status deployment -n $ns

  # Verify
  echo "Verifying namespace: $ns"
  kubectl exec -n $ns <pod-name> -- curl http://<service-name>

  # Wait before next Namespace migration (observation)
  echo "Waiting 1 hour before next namespace..."
  sleep 3600
done
```

**Step-by-step Verification:**

```bash
# After each Namespace migration
# 1. Golden Signals
kubectl port-forward -n istio-system svc/prometheus 9090:9090
# Query in Prometheus:
# - istio_requests_total
# - istio_request_duration_milliseconds
# - istio_request_bytes

# 2. Control Plane status
istioctl proxy-status | grep $ns

# 3. Error logs
kubectl logs -n istio-system -l app=istiod,istio.io/rev=1-28-0 --tail=100
```

***

**Step 5: Remove Old Version**

```bash
# Verify all Namespaces have migrated to new version
kubectl get namespace -L istio.io/rev

# Verify no Pods using old version
kubectl get pods -A -o jsonpath='{range .items[*]}{.metadata.namespace}{"\t"}{.metadata.name}{"\t"}{.spec.containers[?(@.name=="istio-proxy")].image}{"\n"}{end}' | grep 1.27

# Remove old version Control Plane
istioctl uninstall --revision=1-27-0 -y

# Verify removal
kubectl get pods -n istio-system -l app=istiod

# Cleanup
kubectl delete mutatingwebhookconfigurations istio-sidecar-injector-1-27-0
kubectl delete validatingwebhookconfigurations istio-validator-1-27-0-istio-system
```

***

**Step 6: Gateway Upgrade (Optional)**

```bash
# Upgrade Gateway separately
kubectl patch deployment istio-ingressgateway -n istio-system \
  -p '{"spec":{"template":{"metadata":{"labels":{"istio.io/rev":"1-28-0"}}}}}'

kubectl rollout restart deployment istio-ingressgateway -n istio-system
kubectl rollout status deployment istio-ingressgateway -n istio-system
```

***

**Rollback Plan:**

```bash
# Immediate rollback if issues occur
# 1. Change Namespace label to old version
kubectl label namespace <namespace> istio.io/rev=1-27-0 --overwrite

# 2. Restart Pods
kubectl rollout restart deployment -n <namespace>

# 3. Remove new version Control Plane
istioctl uninstall --revision=1-28-0 -y
```

***

**Best Practices:**

1. **Phased Approach:**
   * Progress in stages: Test → Staging → Prod
   * Migrate one Namespace at a time
   * Allow sufficient observation time at each stage
2. **Monitoring:**
   * Monitor Golden Signals (Latency, Traffic, Errors, Saturation)
   * Check Istiod resource usage
   * Observe for 24-48 hours at each stage
3. **Automation:**
   * Integrate into CI/CD pipeline
   * Automate Smoke Tests
   * Prepare rollback scripts
4. **Communication:**
   * Share upgrade schedule with team
   * Review release notes
   * Document changes

**Reference:**

* [Canary Upgrade](https://istio.io/latest/docs/setup/upgrade/canary/)
* [Upgrade Strategy](../../../service-mesh/istio/best-practices.md#upgrade-strategy)

</details>

***

## Score Calculation

* Multiple Choice 1-5: 10 points each (Total 50 points)
* Short Answer 6-10: 10 points each (Total 50 points)
* **Total: 100 points**

**Evaluation Criteria:**

* 90-100 points: Excellent (Perfect understanding of Istio basic concepts)
* 80-89 points: Good (Capable of basic operations)
* 70-79 points: Average (Additional learning recommended)
* 60-69 points: Below Average (Review of basic concepts needed)
* 0-59 points: Re-learning needed

## Learning Resources

* [Istio Installation Guide](../../../service-mesh/istio/01-installation.md)
* [Core Concepts](../../../service-mesh/istio/02-basic-concepts.md)
* [Components](../../../service-mesh/istio/03-architecture.md)
* [Istio Official Documentation](https://istio.io/latest/docs/)
