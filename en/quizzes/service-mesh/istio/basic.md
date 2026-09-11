# Basic Quiz

> **Reviewed Version**: Istio 1.31.0 **EKS Versions**: 1.34–1.36 **Last Updated**: September 11, 2026

This quiz tests your understanding of Istio's basic concepts and architecture.

## Multiple Choice Questions (1-5)

### Question 1: Definition of Service Mesh

Which statement about Service Mesh is **NOT correct**?

A. It is an infrastructure layer that handles communication between microservices\
B. It can only be used by modifying application code\
C. It provides traffic control and observability between services\
D. It applies security and policies at the network level

<details>

<summary>Show Answer</summary>

**Answer: B**

One of the core advantages of Service Mesh is that it can control and observe communication between services **without changing application code**.

**Explanation:**

* A (O): Service Mesh is a dedicated infrastructure layer responsible for communication between services in microservice architecture
* B (X): It is transparently applied through sidecar proxies or Ambient Mode without changing application code
* C (O): It controls traffic with VirtualService, DestinationRule, etc., and exposes metrics; logs/traces need configuration and applications must propagate trace context
* D (O): It applies security policies at the network level with mTLS, Authorization Policy, etc.

**Reference:**

* [Istio Core Concepts](../../../service-mesh/istio/02-basic-concepts.md)
* [What is Service Mesh?](../../../service-mesh/istio/README.md)

</details>

***

### Question 2: Istio Architecture Components

In Istio's Control Plane, which is the **centralized component** responsible for service discovery, configuration management, and certificate management?

A. Envoy\
B. Istiod\
C. Pilot\
D. Citadel

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
* [Architecture Overview](../../../service-mesh/istio/README.md)

</details>

***

### Question 3: Role of Envoy Proxy

Which is **NOT** a task performed by the Data Plane's Envoy proxy?

A. Traffic routing and load balancing\
B. mTLS encryption and authentication\
C. Kubernetes CRD validation and storage\
D. Metrics, logs, and trace collection

<details>

<summary>Show Answer</summary>

**Answer: C**

Kubernetes API Server stores resources and enforces schemas; istiod also validates Istio configuration through admission webhooks. Envoy does not store Kubernetes CRDs.

**Explanation:**

* A (O): Envoy routes traffic and load balances according to VirtualService rules
* B (O): Envoy automatically encrypts service-to-service communication with mTLS and validates certificates
* C (X): CRD validation and storage is the role of Kubernetes API Server and Istiod
* D (O): Envoy collects metrics (Prometheus), logs (Access Log), and traces (Jaeger) according to configured logging and trace sampling

**Reference:**

* [Data Plane Structure](../../../service-mesh/istio/03-architecture.md#data-plane-envoy-proxy)

</details>

***

### Question 4: Istio Installation Profiles

Which profile is **recommended** when installing Istio in an Amazon EKS production environment?

A. default\
B. demo\
C. minimal\
D. production

<details>

<summary>Show Answer</summary>

**Answer: A**

`default` is the production starting profile for the sidecar installation in this guide. There is no built-in `production` profile. Set replicas, resource requests, placement, PDBs, and security policies explicitly; selecting `default` alone does not make the deployment highly available.

| Profile | Purpose |
| --- | --- |
| default | Production starting settings; customize for the workload |
| demo | Demonstrations; verbose telemetry, not performance testing |
| minimal | Control plane only |
| production | Not a built-in profile |

```bash
istioctl install --set profile=default
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

A. VirtualService\
B. DestinationRule\
C. PeerAuthentication\
D. Gateway

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
apiVersion: networking.istio.io/v1
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
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: default
spec:
  mtls:
    mode: STRICT
```

**Reference:**

* [Traffic Management](../../../service-mesh/istio/traffic-management/README.md)
* [Security](../../../service-mesh/istio/security/README.md)

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
  selector:
    matchLabels:
      app: myapp
  template:
    metadata:
      labels:
        app: myapp
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

These are invented inputs for an arithmetic exercise, not measured Istio requirements or a sizing recommendation. Use decimal MB/GB consistently. Assume 0.1 vCPU per sidecar, 0.1 vCPU per ztunnel, and 0.5 vCPU for the waypoint.

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

**Interpretation:**

The assumed inputs yield 98.6% memory and 98.5% CPU reductions for the proxy totals only. They do not imply a 96% reduction in the AWS bill or that a 10-node, 1,000-pod cluster can run on one instance. Application resources, pod/IP limits, HA, replicas, throughput, and waypoint capacity are omitted. Benchmark the actual topology before sizing or estimating costs. Ambient core features have been GA since Istio 1.24.

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

* When the pod starts, the Istio agent creates a private key/CSR and authenticates to istiod with workload credentials; Envoy receives the certificate/key from the local agent via SDS
* Istiod validates the Service Account and issues an X.509 certificate
* The certificate contains the Service Account ID (e.g., `cluster.local/ns/default/sa/service-a`)
* Certificate validity: 24 hours by default (auto-renewed)

**Step 2: Service-to-Service Communication (mTLS Handshake)**

```
Service A → Envoy A → [mTLS] → Envoy B → Service B
```

**Detailed Process:**

```text
1. The source app sends HTTP; configured redirection sends it through Envoy A.
2. Auto mTLS/DestinationRule determines outbound TLS; destination PeerAuthentication
   determines whether Envoy B requires inbound mTLS.
3. ClientHello and ServerHello negotiate TLS parameters/key exchange.
   Certificates are sent in Certificate messages, not in ClientHello/ServerHello.
   The server requests the client certificate; each peer validates the other
   certificate and proof of key possession against the configured trust chain.
4. Envoy B applies authorization and forwards the decrypted request to Service B.
5. The response travels over the established TLS connection.
```

**Roles of Each Component:**

**Istiod:**

* Acts as the CA (may use an intermediate under an external root)
* Issues certificates based on Service Account
* Signs renewal requests before certificate expiry; lifetime is configurable
* Distributes PeerAuthentication policies

**Envoy Sidecar:**

* Receives certificates from the Istio agent over SDS
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
apiVersion: security.istio.io/v1
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
# Inspect certificate validity/status; private keys are not shown as plaintext
istioctl proxy-config secret <pod-name> -n <namespace>
istioctl proxy-config secret <pod-name> -n <namespace> -o json
```

**Security Benefits:**

1. **Confidentiality**: All communication encrypted
2. **Integrity**: Data tampering prevention
3. **Authentication**: Bidirectional identity verification
4. **Automation**: Applied without code changes

**Reference:**

* [mTLS](../../../service-mesh/istio/security/01-mtls.md)
* [Certificate Management](../../../service-mesh/istio/03-architecture.md#3-certificate-management-citadel-functionality)

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
kubectl get pods <pod-name> -n <namespace> -o jsonpath='{.spec.containers[*].name}{" "}{.spec.initContainers[*].name}'
# Expected output: myapp istio-proxy

# Detailed Sidecar injection check
kubectl describe pod <pod-name> -n <namespace> | grep -A 5 "Containers:"

# Check Pod logs
kubectl logs <pod-name> -n <namespace> -c myapp        # Application logs
kubectl logs <pod-name> -n <namespace> -c istio-proxy  # Envoy logs
```

**Diagnosis:**

* Check istio-proxy in containers or native sidecar initContainers; ambient workloads have no injected sidecar
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
kubectl get endpointslices -n <namespace> -l kubernetes.io/service-name=<service-name>

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
kubectl get gateways.networking.istio.io -n <namespace>

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
# Referenced gateway not found: missing-gateway
```

***

**Step 4: Check mTLS and Security Policies**

```bash
# Check PeerAuthentication policies
kubectl get peerauthentication -A

# Check mTLS mode for specific Pod
istioctl proxy-config secret <pod-name> -n <namespace>
istioctl proxy-config clusters <pod-name> -n <namespace> -o json
istioctl x authz check <pod-name> -n <namespace>

# Check AuthorizationPolicy
kubectl get authorizationpolicy -n <namespace>
```

**Diagnosis:**

* Plaintext client traffic reaching a STRICT destination, expired certificates, or incompatible trust
* AuthorizationPolicy blocking traffic

**Resolution:**

Inspect effective policies, workload identity, certificates, and Envoy denial logs. STRICT and PERMISSIVE servers can both accept mesh mTLS clients. Reproduce policy changes in an isolated test namespace; deleting live authorization policies or relaxing mTLS is not a default debugging step.



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

# Compare Pod-IP routing; this does not bypass the sidecar interception
kubectl exec -it <source-pod> -n <namespace> -- curl http://<pod-ip>:<port>

# Check DNS resolution
kubectl exec -it <source-pod> -n <namespace> -- nslookup <service-name>

# Check statistics via Envoy Admin API
istioctl dashboard envoy <pod-name> -n <namespace>
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

Telemetry addons must be installed separately. Run each blocking port-forward in its own terminal; substitute the actual service/namespace for your collector.

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
   ├─ NO → Inspect identity, certificates, and denial logs
   └─ YES → Step 5

5. Envoy configuration normal?
   ├─ NO → Inspect xDS status and istiod logs
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

Explain a canary upgrade from Istio 1.30.4 to 1.31.0 on a compatible EKS cluster. Include workload migration, gateway handling, verification, and rollback conditions.

<details>
<summary>Show Answer</summary>

Keep the old control plane until every workload and gateway has migrated and the rollback window has closed. This is an istioctl-managed sidecar example; Helm and ambient installations have their own upgrade procedures. Revision names below are examples and must match the actual installation.

**1. Prepare and back up**

Check the Istio/EKS support matrices and release upgrade notes. Preserve the existing installation file, chart versions if applicable, mesh resources, and CA/TLS secrets as described in the best-practices chapter. Download the target istioctl and run its precheck:

```bash
curl -fsSL https://istio.io/downloadIstio | ISTIO_VERSION=1.31.0 sh -
cd istio-1.31.0
export PATH="$PWD/bin:$PATH"
istioctl version
istioctl x precheck
```

**2. Install the canary control plane**

Prepare `canary-install.yaml` from the existing configuration, preserving mesh identity, trust, and resource settings. Set revision `1-31-0` and use `minimal` for a control-plane-only canary, with no gateway components enabled. Render and review before installation:

```bash
istioctl manifest generate -f canary-install.yaml > canary-rendered.yaml
istioctl install -f canary-install.yaml
kubectl rollout status deployment/istiod-1-31-0 -n istio-system
```

A `production` profile does not exist. A revision label does not select a binary version; the target istioctl/configuration does.

**3. Verify a test namespace**

```bash
kubectl create namespace istio-upgrade-test
kubectl label namespace istio-upgrade-test istio.io/rev=1-31-0
kubectl apply -n istio-upgrade-test -f samples/curl/curl.yaml
kubectl apply -n istio-upgrade-test -f samples/httpbin/httpbin.yaml
kubectl rollout status deployment/curl -n istio-upgrade-test
kubectl rollout status deployment/httpbin -n istio-upgrade-test
kubectl exec -n istio-upgrade-test deploy/curl -c curl -- curl -fsS http://httpbin:8000/headers
istioctl proxy-status
istioctl analyze -n istio-upgrade-test
```

Verify actual proxy image versions, sync status, mTLS/authorization behavior, errors, and latency before proceeding.

**4. Move staging, then one production namespace at a time**

Remove `istio-injection`, which otherwise takes precedence over the revision label. Restart controllers to create pods with the new proxy; include StatefulSets, DaemonSets, and future Jobs where applicable.

```bash
kubectl label namespace staging istio-injection- istio.io/rev=1-31-0 --overwrite
kubectl rollout restart deployment -n staging
kubectl rollout status deployment -n staging
istioctl proxy-status
```

Repeat only after successful application smoke tests and an observation period suited to the workload. A fixed sleep is not a health gate.

**5. Migrate gateways before removing the old control plane**

Upgrade gateways through their owning istioctl/Helm configuration, including the proxy image, revision, and any external load-balancer settings. Patching only a Deployment label is insufficient for a gateway with an explicit old image. Verify rollout, external requests, and proxy-status. The default istioctl profile can upgrade shared gateways in place; plan this behavior explicitly.

**6. Complete or roll back**

After verifying all proxies (including gateways and non-Deployment workloads) have left the old revision, remove it using the installation tool. Do not manually delete shared validation webhooks:

```bash
istioctl proxy-status
istioctl uninstall --revision=1-30-4
```

Before that removal, rollback means relabeling affected namespaces to the still-running old revision, restarting their workloads, restoring any upgraded gateways with the old release configuration, and validating traffic. Remove the new revision only when no proxies depend on it. If the old revision has already been removed, reinstall and validate it before relabeling workloads.

**References:**

- [Canary upgrade](https://istio.io/latest/docs/setup/upgrade/canary/)
- [Backup and operations guidance](../../../service-mesh/istio/best-practices.md)

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

* [Installation Configuration Profiles](https://istio.io/latest/docs/setup/additional-setup/config-profiles/)
* [Installing the Sidecar](https://istio.io/latest/docs/setup/additional-setup/sidecar-injection/)
* [Security](https://istio.io/latest/docs/concepts/security/)
* [Internet Engineering Task Force (IETF)                       E. Rescorla](https://www.rfc-editor.org/rfc/rfc8446.html)
* [Canary Upgrades](https://istio.io/latest/docs/setup/upgrade/canary/)
* [istioctl](https://istio.io/latest/docs/reference/commands/istioctl/)
* [EndpointSlices](https://kubernetes.io/docs/concepts/services-networking/endpoint-slices/)
* [Announcing Istio 1.24.0](https://istio.io/latest/news/releases/1.24.x/announcing-1.24/)
* [Performance and Scalability](https://istio.io/latest/docs/ops/deployment/performance-and-scalability/)
