# Istio

> **Last Updated**: October 26, 2026

A practical guide for utilizing Istio Service Mesh on Amazon EKS.

### October 2026 security update: 1.31.3, 1.30.7 and 1.29.10

On October 22, 2026, security patch releases shipped for [ISTIO-SECURITY-2026-008](https://istio.io/latest/news/security/istio-security-2026-008/) (CVE-2026-111943): **1.31.3**, **1.30.7**, and **1.29.10** — the last an exceptional release, as 1.29 reached end of life on October 15, 2026. The private keys of eight eMudhra intermediate CA certificates were disclosed as compromised on October 20, 2026; Envoy, Go, and ztunnel do not enforce Certificate Transparency, so a holder of those keys could issue certificates for any domain trusted via the public CA bundles shipped in Istio images. The patches remove the compromised intermediates from the image CA bundles, build istiod, `istioctl`, and `pilot-agent` with Go 1.26.10 on 1.30/1.31 (which rejects chains containing the compromised keys), and update ztunnel's `rustls-webpki`. Configurations that trust the system CA bundle are potentially affected — for example a `DestinationRule` with `tls.mode: SIMPLE` and no `caCertificates`, or `RequestAuthentication` `jwksUri` fetches; Istio's own mesh mTLS certificates are not affected. Istio 1.32.0-beta.0 was published the same day.

### October 2026 review: supported releases

Istio 1.31.0 is GA; its [release announcement](https://istio.io/latest/news/releases/1.31.x/announcing-1.31/) was published on August 31, 2026. The current patch is **1.31.3**, published October 22 (see the October 2026 security update above). The 1.31.2 patch, published October 15, includes the [ISTIO-SECURITY-2026-007](https://istio.io/latest/news/security/istio-security-2026-007/) security fixes ([release announcement](https://istio.io/latest/news/releases/1.31.x/announcing-1.31.2/)). An earlier patch, 1.31.1, was published September 21; its [release announcement](https://istio.io/latest/news/releases/1.31.x/announcing-1.31.1/) documents a fix that prevents an unresolved `BackendTLSPolicy` CA reference from falling back to plaintext backend connections.

New-install commands in this guide use 1.31.2. Istio 1.31's published Kubernetes support range is 1.32–1.37; EKS standard support currently covers 1.34–1.37. Their standard-support overlap is 1.34–1.37; of the EKS extended-support versions (1.31–1.33), 1.32 and 1.33 are also within Istio 1.31's range. Recheck the [Istio support matrix](https://istio.io/latest/docs/releases/supported-releases/) and [EKS version lifecycle](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html) before installation.

Istio 1.30 and 1.29 remain listed as supported in the matrix at the time of this review; 1.29's end-of-life date is listed as October 12, 2026 (expected). Verify its status before installing or upgrading. Existing installations on those branches need at least 1.30.4 or 1.29.7 for [ISTIO-SECURITY-2026-006](https://istio.io/latest/news/security/istio-security-2026-006/), which covers Envoy vulnerabilities, a BackendTLSPolicy fail-open, and an EnvoyFilter control-plane denial of service. [ISTIO-SECURITY-2026-007](https://istio.io/latest/news/security/istio-security-2026-007/), published October 15, affects 1.31.0–1.31.1, 1.30.0–1.30.5, and 1.29.0–1.29.8; the first versions the matrix lists with no known CVEs are 1.31.2, 1.30.6, and 1.29.9. Istio 1.28 is out of support. Istio 1.31 charts use `https://blob.istio.io/istio-release/charts`; the previous Google-hosted repository no longer receives new releases.

### September 2026 update: 1.31.1, 1.30.5 and 1.29.8 patch releases

On September 21, 2026, patch releases shipped for all three supported branches: [1.31.1](https://istio.io/latest/news/releases/1.31.x/announcing-1.31.1/), 1.30.5 and 1.29.8. 1.31.1 includes the security fix [GHSA-qm8v-g4f9-qhjx](https://github.com/istio/istio/security/advisories/GHSA-qm8v-g4f9-qhjx) (CVSS 6.8, Moderate): `BackendTLSPolicy` fails open to plaintext on sidecar proxies when its CA reference is unresolved. Other fixes include the ambient-mode CNI node agent's auto-detected iptables backend (legacy vs nft) flipping between agent restarts, istiod CPU usage growing with the number of `AuthorizationPolicies`, and a memory leak in ambient multi-cluster mode when rotating a remote cluster's credentials. New installations and existing 1.31 installations should update to 1.31.1.

## Table of Contents

1. [Do You Really Need a Service Mesh?](#do-you-really-need-a-service-mesh)
2. [Installation and Initial Setup](01-installation.md)
3. [Basic Concepts](02-basic-concepts.md)
4. [Architecture](03-architecture.md)
5. [AWS Integration](04-aws-integration.md)
6. [Glossary](glossary.md)
7. [Traffic Management](traffic-management/README.md)
8. [Security](security/README.md)
9. [Observability](observability/README.md)
10. [Resilience](resilience/README.md)
11. [Advanced](advanced/README.md)
12. [Troubleshooting](troubleshooting/common-errors.md)
13. [Best Practices](best-practices.md)
14. [Alternative Comparison](comparison/README.md)

## What is Istio?

Istio is an open-source service mesh platform for connecting, securing, controlling, and observing microservices. It manages communication between services in complex microservice architectures and provides traffic control, security, and observability.

### Service Mesh Concept

<div align="center"><img src="https://istio.io/latest/img/service-mesh.svg" alt="Istio Service Mesh" width="800"></div>

A service mesh is an infrastructure layer that manages communication between microservices. Istio supports Envoy sidecars and ambient mode (node-level ztunnel plus optional L7 waypoints). Proxies handle traffic enrolled in the mesh; excluded traffic and unsupported protocols are outside that coverage. This provides the following capabilities without modifying application code:

* **Traffic Routing**: Intelligent routing, load balancing, Canary deployments
* **Security**: Automatic mTLS, authentication, authorization
* **Observability**: Metrics, logs, distributed tracing
* **Resilience**: Circuit Breaking, Retry, Timeout

### Practical Usage Examples

<p align="center"><img src="https://istio.io/latest/docs/examples/bookinfo/noistio.svg" alt="Application without Istio"><br><em>Application without Istio</em></p>

<p align="center"><img src="https://istio.io/latest/docs/examples/bookinfo/withistio.svg" alt="Application with Istio"><br><em>Application with Istio - Envoy Proxy deployed as Sidecar to each service</em></p>

These Bookinfo diagrams illustrate sidecar mode. Automatic injection adds Envoy only to newly created pods in namespaces or workloads that opt in; ambient mode does not inject a sidecar.

## Do You Really Need a Service Mesh?

The service-count thresholds and checklist scores below are discussion prompts, not Istio requirements. A small mesh can still be justified by security needs. The decision diagrams use the same illustrative thresholds.

A service mesh is a powerful tool, but it's not suitable for every situation. Careful consideration is needed before adoption.

### Decision Flow

![Decision flow for adopting a service mesh: checking microservices architecture, 10+ services, complex traffic/security/observability needs, and ops resources in turn leads to mesh recommended, not needed, alternatives, or careful review.](../../.gitbook/assets/en-service-mesh-istio-overview-0.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-overview-0.html)

### When Service Mesh is Needed ✅

#### 1. Complex Microservices Environment

![Side-by-side comparison of four services hand-wiring mTLS, retries, and logging without a mesh versus a Service Mesh automatically handling and controlling communication between the same four services.](../../.gitbook/assets/en-service-mesh-istio-overview-1.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-overview-1.html)

**Recommended Criteria**:

* ✅ 10 or more microservices
* ✅ Frequent inter-service communication (East-West traffic)
* ✅ Multiple programming languages used (Polyglot)
* ✅ Multiple teams developing services independently

#### 2. Zero Trust Security Requirements

**Service Mesh Provides**:

* Automatic mTLS encryption between services
* SPIFFE-based Identity management
* Fine-grained authentication/authorization policies
* Encrypted mesh traffic when mTLS is enforced; automatic mTLS alone does not reject plaintext clients

**Difficult to Achieve Without Alternatives**:

* Duplicate security logic implementation in each service
* Complexity of manual certificate management
* Inconsistent security policies

#### 3. Advanced Traffic Management

```yaml
# Canary Deployment (Traffic Distribution)
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
      weight: 90
    - destination:
        host: reviews
        subset: v2
      weight: 10  # Only 10% to new version
```

**When Needed**:

* Canary deployments, A/B testing
* Header/path-based routing
* Traffic Mirroring (Shadow Testing)
* Fault Injection (Chaos Engineering)
* Circuit Breaking, Retry, Timeout

#### 4. Unified Observability

**Service Mesh Advantages**:

* Automatic metric collection without application code modification
* Proxy-generated trace spans; applications must propagate trace headers to correlate requests
* Unified logging format
* Service topology visualization (Kiali)

### When Service Mesh is Not Needed ❌

#### 1. Simple Architecture

![A user request passing through a load balancer (Ingress Controller) to a single monolithic application and its database, simple enough that an ingress controller suffices without a service mesh.](../../.gitbook/assets/en-service-mesh-istio-overview-2.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-overview-2.html)

**Use Instead**:

* A maintained Kubernetes Gateway API or Ingress controller
* Simple load balancer
* Application-level implementation

#### 2. Few Microservices (<10)

**Overhead is Greater**:

* Service Mesh operational complexity > benefits gained
* 5-10 services can be managed manually
* NetworkPolicy can provide L3/L4 isolation when the CNI enforces it; it does not provide mTLS or HTTP authorization

**Alternative**:

```yaml
# L3/L4 ingress isolation; requires a NetworkPolicy-capable CNI
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-frontend-to-backend
spec:
  podSelector:
    matchLabels:
      app: backend
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: frontend
```

#### 3. Insufficient Operations Resources

**Service Mesh Operations Requirements**:

* Istio/Envoy expertise
* Control Plane monitoring and management
* Upgrade and patch management
* Troubleshooting capability (increased debugging complexity)

**Team Preparation Needed**:

* At least 1-2 Service Mesh experts
* Continuous learning and update tracking
* Sufficient test environment

#### 4. When Performance is Extremely Critical

**Service Mesh Overhead**:

Measure latency, CPU, and memory with representative traffic, proxy configuration, and telemetry settings. The [official performance page](https://istio.io/latest/docs/ops/deployment/performance-and-scalability/) records an Istio 1.24 benchmark; those historical results are not guarantees for other versions or workloads.

**Consider Alternatives**:

* Ambient mode (shared L4 proxies; savings depend on traffic and waypoint deployment)
* CNI-based solutions (Cilium)
* Application-level optimization

### Alternative Solutions Comparison

| Feature                    | Service Mesh                                 | CNI (Cilium)    | Ingress Controller | App-level                |
| -------------------------- | -------------------------------------------- | --------------- | ------------------ | ------------------------ |
| **L7 Traffic Management**  | ✅ Full support                               | ⚠️ Limited      | ⚠️ Ingress only    | ✅ Possible               |
| **mTLS Automation**        | ✅ Full support                               | ⚠️ Mutual authentication and encryption are separate      | ❌ Not supported    | ❌ Manual implementation  |
| **Distributed Tracing**    | ⚠️ Requires trace-context propagation                                  | ❌ Not supported | ❌ Not supported    | ⚠️ Manual implementation |
| **L3/L4 Policies**         | ✅ Supported                                  | ✅ Full support  | ❌ Not supported    | ❌ Not supported          |
| **Operational Complexity** | 🔴 High                                      | 🟡 Medium       | 🟢 Low             | 🟡 Medium                |
| **Resource Overhead**      | <p>🔴 High (Sidecar)<br>🟢 Low (Ambient)</p> | 🟢 Low          | 🟢 Low             | 🟢 None                  |
| **Suitable Scale**         | Requirements-dependent                                 | All scales      | Small scale        | Small scale              |

### CNI-Based Solution (Cilium)

Cilium provides many features at the **network level** based on eBPF:

![Comparison of Istio's L7 proxy-based service mesh and Cilium's eBPF kernel-level CNI, linked to the usage scenarios where complex L7 logic calls for a service mesh, policy and performance call for Cilium, and large enterprises use both.](../../.gitbook/assets/en-service-mesh-istio-overview-3.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-overview-3.html)

**When Cilium is More Suitable**:

* L3/L4 network policies are the main purpose
* Measured performance under the required policy/encryption settings meets the workload's needs
* Reusing an existing Cilium deployment whose supported features meet the requirements
* Network policy and observability are primary needs; Cilium out-of-band mutual authentication requires separate WireGuard/IPsec encryption for payload confidentiality

Cilium 1.20.1 also provides a separate [ztunnel transparent-encryption beta](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/security/network/encryption-ztunnel.rst), selected with `encryption.type: ztunnel`. It provides TCP workload mTLS with namespace enrollment; both endpoints must be enrolled. It excludes ClusterMesh and host-networked Pods, and the released guide warns that ordinary L4 policies do not work on this path except when targeting HBONE port 15008. This is a distinct deployment choice with its own CA/bootstrap requirements.

The diagram emphasizes the CNI role; Cilium also has L7 Envoy features. Component count and operational cost depend on the selected mode.

**Reference**: [Cilium Documentation](../../networking/cilium/README.md)

### Decision Checklist

Answer the following questions before adoption:

**Architecture**:

* [ ] Do you have 10 or more microservices?
* [ ] Is inter-service communication complex?
* [ ] Are multiple programming languages used?

**Security**:

* [ ] Is a Zero Trust security model needed?
* [ ] Is mTLS encryption between services mandatory?
* [ ] Is fine-grained access control needed?

**Traffic Management**:

* [ ] Are Canary deployments and A/B testing needed?
* [ ] Are advanced routing rules needed?
* [ ] Are Circuit Breaking and Retry needed for many services?

**Observability**:

* [ ] Is distributed tracing mandatory?
* [ ] Is unified metric collection needed?
* [ ] Is service topology visualization needed?

**Operations**:

* [ ] Do you have Service Mesh experts?
* [ ] Can you handle the operational complexity?
* [ ] Can you accept the resource overhead?

**Results**:

* ✅ 10 or more checked: Service Mesh strongly recommended
* 🟡 5-9 checked: Careful evaluation needed, start small (Ambient Mode recommended)
* ❌ 4 or fewer checked: Consider alternative solutions (CNI, Ingress, App-level)

### Gradual Adoption Strategy

If you determine that a Service Mesh is needed, adopt it gradually:

![Four-phase rollout moving from observability-only metric collection, to mTLS security, to canary traffic management, and finally to the full advanced feature set, with each phase gated by validation.](../../.gitbook/assets/en-service-mesh-istio-overview-4.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-overview-4.html)

**Recommended Order**:

1. **Pilot Project** (1-2 namespaces)
2. **Observability First** (metrics, logs, traces)
3. **Apply Security** (mTLS PERMISSIVE → STRICT)
4. **Traffic Management** (VirtualService, DestinationRule)
5. **Company-wide Expansion**

### Key Features

1.  **Traffic Management**

    VirtualService selects routes; DestinationRule defines subsets and destination traffic policies.

    * Intelligent routing and load balancing
    * A/B testing, Canary deployment, Blue/Green deployment
    * Circuit Breaking, Retry, Timeout control
    * Traffic Mirroring and Fault Injection
2.  **Security**

    <div align="center"><img src="https://istio.io/latest/docs/concepts/security/arch-sec.svg" alt="Security Architecture" width="600"></div>

    * Automatic mTLS encryption between services
    * Strong authentication and authorization
    * Fine-grained access control policies
    * Network isolation and security policies
3.  **Observability**

    <div align="center"><img src="https://istio.io/latest/docs/tasks/observability/kiali/kiali-graph.png" alt="Kiali Service Graph" width="700"></div>

    * Proxy metrics and configurable access logs and tracing
    * Prometheus, Grafana, Jaeger, Kiali integration
    * Service topology visualization
    * Real-time traffic monitoring
4. **Resilience**
   * Circuit Breaker pattern
   * Rate Limiting
   * Outlier Detection
   * Zone Aware Routing

### Istio Architecture

<div align="center"><img src="https://istio.io/latest/docs/ops/deployment/architecture/arch.svg" alt="Istio Architecture" width="700"></div>

Istio consists of a Control Plane and a Data Plane:

![Istio's Control Plane and Data Plane: istiod's Pilot pushes routing configuration and Citadel issues certificates to the Envoy sidecar in each pod, and the Envoys intercept application requests and exchange mTLS-encrypted traffic.](../../.gitbook/assets/en-service-mesh-istio-overview-5.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-overview-5.html)

**Control Plane (istiod)**:

* Service discovery and proxy configuration (historically Pilot)
* Certificate authority and identity management (historically Citadel)
* Configuration validation; Galley is a retired standalone component, not a separate current service

**Data Plane**:

* **Sidecar mode**: Envoy per enrolled pod
* **Ambient mode**: ztunnel per node for L4 security and optional waypoint proxies for L7 processing

### Benefits of Using Istio on Amazon EKS

1. **Easy Microservices Management**
   * Traffic management without application code modification
   * Consistent policy application with declarative configuration
   * Uses Kubernetes Native API
2. **Enhanced Security**
   * Automatic encryption between services
   * AWS API access through EKS Pod Identity or IRSA; Istio workload identity remains service-account based
   * Fine-grained permission control
3. **Improved Observability**
   * Integration with Amazon CloudWatch
   * Distributed tracing through AWS X-Ray
   * Detailed metrics and logs
4. **Integration with AWS Services**
   * Application Load Balancer (ALB) integration
   * AWS Certificate Manager (ACM) integration
   * Compatible with Amazon EBS CSI Driver

### Getting Started

[Gateway API guide](https://istio.io/latest/docs/tasks/traffic-management/ingress/gateway-api/)

If you're new to Istio, read the documents in the following order:

1. [**Installation and Initial Setup**](01-installation.md): Install Istio on EKS cluster
2. [**Basic Concepts**](02-basic-concepts.md): Understand Istio core concepts
3. [**Traffic Management**](traffic-management/README.md): Learn Gateway, VirtualService, DestinationRule
4. [**Security**](security/README.md): Configure mTLS, authentication, authorization
5. [**Observability**](observability/README.md): Collect metrics, logs, traces
6. [**Best Practices**](best-practices.md): Recommendations for production environments

### Hands-on Examples

These routing excerpts require matching Services and DestinationRule subsets (`v1`/`v2`); see the traffic-management chapters.

Each section includes working YAML examples. All examples are structured to be click-to-copy:

```yaml
# Example VirtualService
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
```

### References

* [Istio Official Documentation](https://istio.io/latest/docs/)
* [Istio GitHub](https://github.com/istio/istio)
* [Istio EKS platform guidance](https://istio.io/latest/docs/setup/platform-setup/amazon-eks/)
* [Istio Community](https://istio.io/latest/get-involved/)


* [Tracing and application header propagation](https://istio.io/latest/docs/tasks/observability/distributed-tracing/overview/)
* [Kubernetes NetworkPolicy capabilities](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
* [Cilium mutual authentication](https://docs.cilium.io/en/stable/network/servicemesh/mutual-authentication/mutual-authentication/)

### Quizzes

To test what you've learned in this chapter, try the following quizzes:

* [Traffic Management Quiz](../../quizzes/service-mesh/istio/traffic-management.md)
* [Security Quiz](../../quizzes/service-mesh/istio/security.md)
* [Observability Quiz](../../quizzes/service-mesh/istio/observability.md)
* [Resilience Quiz](../../quizzes/service-mesh/istio/resilience.md)
* [Advanced Quiz](../../quizzes/service-mesh/istio/advanced.md)
