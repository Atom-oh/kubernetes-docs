# Comparison Guide

> **Last reviewed**: September 11, 2026
> **Audience**: Architects, DevOps engineers and platform engineers

Compare the required traffic, identity, platform and operating contracts before selecting a mesh. Organization size, feature-star ratings or a fixed resource-overhead percentage do not establish suitability. Version support and release-channel choices must be checked separately from the architecture comparison.

## Contents

### 1. [Service Mesh Solution Comparison](01-service-mesh-comparison.md)

The detailed comparison covers Istio, Linkerd, Kong Mesh/Kuma and Consul service mesh. Also consider the maintained [Cilium service-mesh guide](../../cilium-service-mesh/README.md) when evaluating networking and mesh capabilities together.

Compare data/control planes, supported traffic policies, identity and encryption, observability, Kubernetes/VM support, multicluster topology, lifecycle and commercial distribution terms. Measure resource use under equivalent policies and traffic rather than assigning an inherent high/medium/low rank.

### 2. [Istio vs VPC Lattice](02-istio-vs-lattice.md)

Istio is a deployable mesh with Kubernetes and documented VM integration. VPC Lattice is an AWS-managed application networking service for services and resources, including supported EC2, container and Lambda targets. It does not require all applications to be serverless.

Compare protocol/routing behavior, identity at each TLS boundary, regional connectivity, owner responsibilities and actual billing dimensions. A managed network does not eliminate application, DNS, IAM, target-health or cost operations.

### 3. [Sidecar vs Ambient](03-sidecar-vs-ambient.md)

This guide includes recorded EKS experiments covering mTLS, NetworkPolicy, latency and rollout failures. Keep each experiment's actual versions, workload, measurement window and raw 503 results attached to its conclusion. Client-visible results after retries are a separate measurement; retries can hide failures and can duplicate non-idempotent operations.

Use those observations to design a test for the intended workload. They do not establish a universal ranking of sidecar versus waypoint reliability or a mandatory core/semi-core/peripheral placement rule.

## Selection Criteria

| Requirement | Candidate capabilities to evaluate | Evidence needed |
|---|---|---|
| Fine-grained L7 traffic and policy | Istio; also the exact Linkerd/Kong/Consul/Cilium features required | Supported APIs, protocol behavior, generated configuration and upgrade tests |
| A focused Kubernetes mesh | Linkerd or an appropriately scoped Istio deployment | Actual operating effort, identity lifecycle, feature coverage and equivalent-load measurements |
| Existing Cilium networking | Cilium's eBPF datapath and proxy-based L7 features | Kernel/CNI compatibility, enabled L7 features and separate authentication/encryption requirements |
| AWS service/resource connectivity | VPC Lattice | Regional network/endpoint path, target support, IAM/TLS contracts and service/resource-owner responsibilities |
| VM or hybrid workloads | Istio VM integration, Linkerd mesh expansion, Kong Universal mode or Consul's supported runtimes | Workload identity, DNS, IP/API reachability and runtime-specific limitations |
| Multicluster or multicloud | Supported topology of the selected mesh and any external networking | Trust boundaries, configuration distribution, data recovery, latency and transfer costs |
| Deep observability | The selected mesh plus appropriate metrics/logging/tracing backends | Actual telemetry labels, application trace propagation, sampling, retention and access controls |

These are candidates, not automatic product recommendations. A tracing backend or dashboard is an additional configured dependency; no mesh produces a complete application trace without the necessary context propagation/instrumentation.

## Quick Architecture Comparison

| Solution | Data plane | Platform and operating considerations |
|---|---|---|
| Istio | Envoy sidecars; ambient uses per-node ztunnel and optional Envoy waypoints | Kubernetes and documented VM integration; mode-specific feature/topology support; self-managed or vendor distributions |
| Linkerd | Rust linkerd2-proxy | Kubernetes plus documented non-Kubernetes mesh expansion using ExternalWorkload and compatible identity/networking; not “no VM support” |
| Kong Mesh | Envoy data-plane proxies | Kubernetes and Universal VM/bare-metal modes; self-hosted or managed global control-plane options, with edition-specific features |
| Consul service mesh | Envoy sidecars with Consul discovery/control plane | Documented Kubernetes, VM and other runtime integrations; verify the selected edition/version and proxy compatibility |
| Cilium | eBPF network datapath plus proxies such as Envoy for L7 | Verify enabled components and platform support; not an entirely proxy-free L7 implementation |

Cilium 1.20.1 documents mutual authentication as **Beta**, with an out-of-band handshake. Traffic encryption requires separate WireGuard/IPsec configuration; the authentication feature is not equivalent to automatically wrapping every application connection in an Istio-style TLS session. Its documented Cluster Mesh and external-mTLS limitations also matter.

Linkerd's project milestone version and installed artifact are different choices. The official release page lists Linkerd 2.20 and its corresponding edge release; the open-source project publishes edge artifacts, while stable artifacts come from vendors. Check release guidance, Kubernetes compatibility, update/support terms and any subscription cost. Do not infer the artifact/channel from an old documentation link.

### Istio and VPC Lattice

| Dimension | Istio | VPC Lattice |
|---|---|---|
| Deployment | Operated control/data planes or a chosen vendor distribution | AWS operates the networking service; users configure services/resources, access and targets |
| Platform | Kubernetes and VM integration with explicit network/trust prerequisites | AWS networking with supported service targets/resource configurations and documented client paths |
| Traffic/security model | Mode-specific mesh routing, workload identity and policies | Listener/rule/target and service auth-policy contracts; resource configurations have different controls |
| Operations | Proxy/control-plane lifecycle, capacity, certificates, policy and telemetry | IAM/sharing, DNS/endpoints, target health, controller integration, quotas and telemetry remain user work |
| Cost | Compute, load balancers, transfer, storage/telemetry and optional support | Applicable provisioned/usage billing dimensions, plus surrounding infrastructure and operations |
| Hybrid integration | Explicit gateway/trust/identity design | Explicit regional endpoint/network path and TLS/authentication boundary; not automatic cross-cloud mesh federation |

Feature ratings and one-vendor “enterprise support” cells are omitted: availability, licensing and support depend on the actual distribution/contract, and named integrations do not certify a configuration.

## Migration Guidance

### Linkerd to Istio

Inventory traffic APIs, retry/timeout behavior, authorization, identities, certificates and telemetry before translating configuration. Linkerd uses CRDs as well as annotations; migration is not a mechanical annotation-to-Istio-CRD conversion. Stage a service or namespace cohort with a tested coexistence path, and avoid overlapping traffic capture or injecting two mesh sidecars into the same Pod.

### Kubernetes to a Mesh

Start from an unmet requirement: workload identity, policy, resilience or observability. Service count alone is not a threshold for needing a mesh. Existing Services, a maintained Ingress/Gateway API implementation, NetworkPolicy and application instrumentation may already satisfy the requirement. Test injection or ambient enrollment, startup/drain, policy enforcement and rollback on a bounded workload.

### Istio and VPC Lattice

A hybrid can use Istio inside a cluster and Lattice across an explicitly configured service path. Map every TLS termination and caller identity. A Lattice IAM-authenticated request requires the documented signing/authorization path; mesh mTLS alone does not create SigV4 identity or end-to-end SPIFFE propagation. Do not run competing controllers over the same route, target or DNS resource.

## FAQ

<details>
<summary>Is a service mesh always necessary?</summary>

No. Establish which networking, identity, policy or observability requirement is not already met. A small service may need strong identity controls, while a larger system may already implement its required controls elsewhere. Evaluate the benefit against actual operating and resource cost.

</details>

<details>
<summary>Should I choose Istio or Linkerd?</summary>

Compare the exact routing/security/observability features, platform support and operational workflow. Linkerd is not restricted to “basic” features or Kubernetes-only workloads, and Istio's sidecar and ambient modes have different resource and feature profiles. Run the same representative workload and review release/support options before deciding.

</details>

<details>
<summary>When is VPC Lattice a candidate?</summary>

When its supported service/resource model and AWS networking/authentication contracts fit the application. Mixed containers, EC2 and Lambda can be relevant; “AWS-centric” or “serverless” alone is not enough. Confirm Region, client path, target type, protocol, identity and cost assumptions.

</details>

<details>
<summary>How much overhead should I expect?</summary>

No universal latency, CPU percentage or memory-per-Pod figure applies across these products. Measure equivalent policies, TLS, traffic, concurrency, node/proxy/waypoint counts and failure behavior. Keep a reproducible benchmark's original versions and raw data. Managed networking still adds a processing path, observability work and billable usage; it is not zero infrastructure impact.

</details>

<details>
<summary>Can several meshes coexist?</summary>

Separate clusters/workload cohorts or an explicit migration/hybrid boundary can coexist. Multiple interceptors on the same Pod/network path can conflict. Define traffic ownership, trust/identity translation, telemetry and rollback rather than assuming namespace separation makes the systems interoperable.

</details>

## Related Resources

- [Istio architecture](../03-architecture.md)
- [Traffic management](../traffic-management/README.md)
- [Security](../security/README.md)
- [Observability](../observability/README.md)
- [VPC Lattice](../../../networking/02-vpc-lattice.md)
- [Linkerd](../../linkerd/README.md)
- [Cilium service mesh](../../cilium-service-mesh/README.md)

## Official References

- [Istio documentation](https://istio.io/latest/docs/) and [VM integration](https://istio.io/latest/docs/setup/install/virtual-machine/)
- [Linkerd overview](https://linkerd.io/docs/overview/), [mesh expansion](https://linkerd.io/docs/tasks/adding-non-kubernetes-workloads/) and [release channels](https://linkerd.io/releases/)
- [Kong Mesh](https://developer.konghq.com/mesh/) and [architecture](https://developer.konghq.com/mesh/architecture/)
- [Consul service mesh](https://developer.hashicorp.com/consul/docs/connect)
- [Cilium 1.20.1 mesh architecture source](https://raw.githubusercontent.com/cilium/cilium/v1.20.1/Documentation/network/servicemesh/index.rst) and [mutual-authentication status](https://raw.githubusercontent.com/cilium/cilium/v1.20.1/Documentation/network/servicemesh/mutual-authentication/mutual-authentication.rst)
- [VPC Lattice components and responsibilities](https://docs.aws.amazon.com/vpc-lattice/latest/ug/what-is-vpc-lattice.html)
