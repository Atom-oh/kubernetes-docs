# Istio

> **Last Updated**: August 31, 2026

A practical guide for utilizing Istio Service Mesh on Amazon EKS.

### August 2026 Update: Istio 1.30.4 / 1.29.7 Security Patch Releases

On August 27, 2026, the Istio 1.30.4 and 1.29.7 patch releases were published. These releases **contain security fixes ([ISTIO-SECURITY-2026-006](https://istio.io/latest/news/security/istio-security-2026-006/)), so upgrading promptly is recommended**:

- **13 Envoy CVEs fixed**: including a heap use-after-free in HTTP/2 trailer handling (CVE-2026-73513), an RBAC bypass via `ignore_path_parameters_in_path_matching` (CVE-2026-73553), and HTTP/2 memory exhaustion via discarded duplicate Host headers (CVE-2026-73550)
- **1 Istio CVE fixed**: `BackendTLSPolicy` failing open to plaintext on sidecar proxies when its CA reference is unresolved (GHSA-qm8v-g4f9-qhjx)
- Plus numerous stability fixes, such as a multicluster bug where a remote cluster's network gateway/endpoints could disappear after credential rotation

Meanwhile, release candidates for the next version, 1.31, continued from rc.2 through rc.4 between August 25-27, so the official release is close. See the [1.30.4 official announcement](https://istio.io/latest/news/releases/1.30.x/announcing-1.30.4/) for details.

### August 2026 Update: Istio 1.31 Enters RC

On August 19, 2026, 1.31.0-beta.2 was followed the same day by the first release candidate, [1.31.0-rc.0](https://github.com/istio/istio/releases), moving the next minor version, 1.31, into the release-candidate stage. An RC is a pre-release for final validation just before GA — a signal that the official release is close. Keep using GA releases in production.

### August 2026 Update: Istio 1.31 Enters Beta

The release process for the next minor version, Istio 1.31, is underway: 1.31.0-alpha.2 was published on August 11, 2026, followed by 1.31.0-beta.0 on August 13 and 1.31.0-beta.1 on August 14. Alpha/beta builds are pre-releases for early validation, not production use — only pick them up if you want to test new features ahead of the GA release. See the [Istio releases page](https://github.com/istio/istio/releases) for details.

### July 2026 Update: Istio 1.30.3 / 1.29.6 Patch Releases

On July 16, 2026, the Istio 1.30.3 and 1.29.6 patch releases were published. Highlights of 1.30.3:

- Improved istiod scalability in ambient mode by scoping XDS pushes from workload/service address changes to only the affected waypoints
- Fixed a bug where istiod did not pick up updated remote cluster secrets (e.g. during credential/token rotation) until restarted
- The pilot node untaint controller's taint name is now customizable via the `PILOT_NODE_UNTAINT_CONTROLLERS_TAINT_NAME` environment variable

See the [official announcement](https://istio.io/latest/news/releases/1.30.x/announcing-1.30.3/) for details.

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

A service mesh is an infrastructure layer that manages communication between microservices. Istio deploys a Sidecar Proxy (Envoy) alongside each service to intercept and control all network traffic. This provides the following capabilities without modifying application code:

* **Traffic Routing**: Intelligent routing, load balancing, Canary deployments
* **Security**: Automatic mTLS, authentication, authorization
* **Observability**: Metrics, logs, distributed tracing
* **Resilience**: Circuit Breaking, Retry, Timeout

### Practical Usage Examples

<p align="center"><img src="https://istio.io/latest/docs/examples/bookinfo/noistio.svg" alt="Application without Istio"><br><em>Application without Istio</em></p>

<p align="center"><img src="https://istio.io/latest/docs/examples/bookinfo/withistio.svg" alt="Application with Istio"><br><em>Application with Istio - Envoy Proxy deployed as Sidecar to each service</em></p>

When Istio is applied, an Envoy Proxy is automatically deployed as a sidecar container to each microservice, transparently intercepting and controlling all network traffic.

## Do You Really Need a Service Mesh?

A service mesh is a powerful tool, but it's not suitable for every situation. Careful consideration is needed before adoption.

### Decision Flow

![Decision flow for adopting a service mesh: checking microservices architecture, 10+ services, complex traffic/security/observability needs, and ops resources in turn leads to mesh recommended, not needed, alternatives, or careful review.](../../.gitbook/assets/en-service-mesh-istio-readme-0.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-readme-0.html)

### When Service Mesh is Needed ✅

#### 1. Complex Microservices Environment

![Side-by-side comparison of four services hand-wiring mTLS, retries, and logging without a mesh versus a Service Mesh automatically handling and controlling communication between the same four services.](../../.gitbook/assets/en-service-mesh-istio-readme-1.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-readme-1.html)

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
* Guaranteed encrypted communication

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
* Automatic Distributed Tracing implementation
* Unified logging format
* Service topology visualization (Kiali)

### When Service Mesh is Not Needed ❌

#### 1. Simple Architecture

![A user request passing through a load balancer (Ingress Controller) to a single monolithic application and its database — simple enough that an ingress controller suffices without a service mesh.](../../.gitbook/assets/en-service-mesh-istio-readme-2.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-readme-2.html)

**Use Instead**:

* Kubernetes Ingress Controller (NGINX, Traefik)
* Simple load balancer
* Application-level implementation

#### 2. Few Microservices (<10)

**Overhead is Greater**:

* Service Mesh operational complexity > benefits gained
* 5-10 services can be managed manually
* NetworkPolicy provides sufficient security

**Alternative**:

```yaml
# Kubernetes NetworkPolicy is sufficient
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

* Latency: +1-3ms (P50), +5-10ms (P99)
* CPU: +10-20% per pod
* Memory: +50-100MB per pod (Sidecar mode)

**Consider Alternatives**:

* Ambient Mode (90% reduction in resource usage)
* CNI-based solutions (Cilium)
* Application-level optimization

### Alternative Solutions Comparison

| Feature                    | Service Mesh                                 | CNI (Cilium)    | Ingress Controller | App-level                |
| -------------------------- | -------------------------------------------- | --------------- | ------------------ | ------------------------ |
| **L7 Traffic Management**  | ✅ Full support                               | ⚠️ Limited      | ⚠️ Ingress only    | ✅ Possible               |
| **mTLS Automation**        | ✅ Full support                               | ✅ Possible      | ❌ Not supported    | ❌ Manual implementation  |
| **Distributed Tracing**    | ✅ Automatic                                  | ❌ Not supported | ❌ Not supported    | ⚠️ Manual implementation |
| **L3/L4 Policies**         | ✅ Supported                                  | ✅ Full support  | ❌ Not supported    | ❌ Not supported          |
| **Operational Complexity** | 🔴 High                                      | 🟡 Medium       | 🟢 Low             | 🟡 Medium                |
| **Resource Overhead**      | <p>🔴 High (Sidecar)<br>🟢 Low (Ambient)</p> | 🟢 Low          | 🟢 Low             | 🟢 None                  |
| **Suitable Scale**         | 10+ services                                 | All scales      | Small scale        | Small scale              |

### CNI-Based Solution (Cilium)

Cilium provides many features at the **network level** based on eBPF:

![Comparison of Istio's L7 proxy-based service mesh and Cilium's eBPF kernel-level CNI, linked to the usage scenarios where complex L7 logic calls for a service mesh, policy and performance call for Cilium, and large enterprises use both.](../../.gitbook/assets/en-service-mesh-istio-readme-3.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-readme-3.html)

**When Cilium is More Suitable**:

* L3/L4 network policies are the main purpose
* High performance is a core requirement
* Avoiding Service Mesh operational burden
* Only simple mTLS and observability needed

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

* [ ] Are Canary deployments, A/B testing needed?
* [ ] Are advanced routing rules needed?
* [ ] Are Circuit Breaking, Retry needed for many services?

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

![Four-phase rollout moving from observability-only metric collection, to mTLS security, to canary traffic management, and finally to the full advanced feature set — each phase gated by validation.](../../.gitbook/assets/en-service-mesh-istio-readme-4.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-readme-4.html)

**Recommended Order**:

1. **Pilot Project** (1-2 namespaces)
2. **Observability First** (metrics, logs, traces)
3. **Apply Security** (mTLS PERMISSIVE → STRICT)
4. **Traffic Management** (VirtualService, DestinationRule)
5. **Company-wide Expansion**

### Key Features

1.  **Traffic Management**

    <div align="center"><img src="https://istio.io/latest/docs/concepts/traffic-management/request-routing.svg" alt="Traffic Routing" width="500"></div>

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

    * Automatic metrics, logs, and trace generation
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

![Istio's Control Plane and Data Plane: istiod's Pilot pushes routing configuration and Citadel issues certificates to the Envoy sidecar in each pod, and the Envoys intercept application requests and exchange mTLS-encrypted traffic.](../../.gitbook/assets/en-service-mesh-istio-readme-5.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-readme-5.html)

**Control Plane (istiod)**:

* **Pilot**: Service discovery, traffic routing rule management
* **Citadel**: Certificate generation and management, mTLS enablement
* **Galley**: Configuration validation and deployment

**Data Plane**:

* **Envoy Proxy**: Deployed as a sidecar to each pod, intercepting and controlling all network traffic

### Benefits of Using Istio on Amazon EKS

1. **Easy Microservices Management**
   * Traffic management without application code modification
   * Consistent policy application with declarative configuration
   * Uses Kubernetes Native API
2. **Enhanced Security**
   * Automatic encryption between services
   * Authentication integrated with AWS IAM
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

<div align="center"><img src="https://istio.io/latest/docs/tasks/traffic-management/ingress/ingress-gateway-example/gateway-api-topology.svg" alt="Gateway API Architecture" width="600"></div>

If you're new to Istio, read the documents in the following order:

1. [**Installation and Initial Setup**](01-installation.md): Install Istio on EKS cluster
2. [**Basic Concepts**](02-basic-concepts.md): Understand Istio core concepts
3. [**Traffic Management**](traffic-management/README.md): Learn Gateway, VirtualService, DestinationRule
4. [**Security**](security/README.md): Configure mTLS, authentication, authorization
5. [**Observability**](observability/README.md): Collect metrics, logs, traces
6. [**Best Practices**](best-practices.md): Recommendations for production environments

### Hands-on Examples

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
* [AWS EKS Workshop - Istio](https://www.eksworkshop.com/intermediate/330_servicemesh_using_istio/)
* [Istio Community](https://discuss.istio.io/)

### Quizzes

To test what you've learned in this chapter, try the following quizzes:

* [Traffic Management Quiz](../../quizzes/service-mesh/istio/traffic-management.md)
* [Security Quiz](../../quizzes/service-mesh/istio/security.md)
* [Observability Quiz](../../quizzes/service-mesh/istio/observability.md)
* [Resilience Quiz](../../quizzes/service-mesh/istio/resilience.md)
* [Advanced Quiz](../../quizzes/service-mesh/istio/advanced.md)
