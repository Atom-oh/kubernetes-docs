# Cilium Service Mesh Overview

> **Reviewed**: September 11, 2026 · Cilium/chart 1.20.1 · CLI 0.20.0 · Hubble CLI 1.19.4

Cilium combines Kubernetes networking, eBPF policy/load balancing and optional application-layer proxy features. Selected L7 traffic is handled by Cilium's Envoy integration; removing per-application sidecars does not remove the proxy, kernel requirements or operational components.

## Architecture and Security Boundaries

![Logical comparison with Istio sidecar mode: Cilium uses the eBPF datapath and redirects selected L7 traffic to a shared Envoy. This is not an encryption/performance guarantee or a diagram of Istio ambient mode.](../../.gitbook/assets/en-service-mesh-cilium-service-mesh-readme-0.png)

[View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-cilium-service-mesh-readme-0.html)

Envoy can run as a process with the Cilium agent or as the separately managed `cilium-envoy` DaemonSet. The selected chart's normal rendered configuration uses the dedicated DaemonSet. Actual placement and the number of L7 hops depend on the enabled features/policies; not every packet traverses Envoy.

| Component | Role |
|---|---|
| Cilium agent | Node datapath, endpoint identities and policy enforcement |
| Cilium operator | IPAM and other cluster/controller responsibilities for the selected mode |
| Envoy | Matching L7 policy, ingress and Gateway API processing |
| Hubble | Flow observations; L7 records require the relevant proxy visibility |
| Hubble Relay / UI | Additional aggregation and visualization components |
| SPIRE, when configured | Identity infrastructure for the beta mutual-authentication feature |

### Mutual authentication is not automatic traffic encryption

Cilium 1.20.1 documents **out-of-band mutual authentication as beta and incomplete**. Its mTLS-based identity handshake occurs out of band between agents for Cilium security identities. That does not wrap every application connection in the same TLS transport model as an Istio or Linkerd workload proxy.

WireGuard/IPsec are separate encryption mechanisms with their own supported modes and scope. WireGuard is not TLS, and enabling SPIRE alone does not encrypt application data or activate authentication rules for every endpoint. The selected release also documents that mutual authentication is not compatible with ClusterMesh or an external mesh mTLS solution.

Cilium 1.20.1 also provides a separate [ztunnel transparent-encryption beta](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/security/network/encryption-ztunnel.rst), selected with `encryption.type: ztunnel`. It provides TCP workload mTLS with namespace enrollment; both endpoints must be enrolled. It excludes ClusterMesh and host-networked Pods, and the released guide warns that ordinary L4 policies do not work on this path except when targeting HBONE port 15008. This is a distinct deployment choice with its own CA/bootstrap requirements.

Review the [security guide](03-security.md) and the released security model/limitations before adopting this beta path. Treat routing, authentication, authorization and encryption as distinct requirements.

Cilium can also provide the underlying CNI for an Istio deployment. That networking integration does not make their authentication mechanisms interchangeable; review mode-specific socket load-balancing, CNI coexistence and L7 policy ownership.

## Compare Capabilities and Measured Costs

| Topic | Cilium | Istio | Linkerd |
|---|---|---|---|
| Dataplane model | eBPF plus shared Envoy for selected L7 work | Sidecar mode, or ambient ztunnel/waypoint roles | Per-Pod proxy, including native sidecar placement |
| Pod networking | Provides or chains with a CNI, depending on mode | Needs an underlying Pod network; its CNI redirects mesh traffic | Needs an underlying Pod network; optional CNI redirects mesh traffic |
| Policy | Kubernetes/Cilium network policy and L7 features | Mesh authorization/routing with a separate network-policy layer | Server/route authorization and outbound routing, not L4-only policy |
| Gateway API | Opt-in controller and documented conformance/features | Gateway and mesh-routing roles | Supported Service/Server-parent route roles |
| Security | Out-of-band authentication with separate encryption; distinct ztunnel mTLS beta with restrictions | Workload mesh mTLS plus policy | Workload mesh mTLS plus policy |

No product has a universal CPU, memory or latency ranking independent of workload and configuration. The former fixed per-node/per-Pod numbers and 100-Pod memory diagram were not an attributed benchmark and omitted components, node count and workload details. Compare measured incremental cost against the same baseline, including agents/proxies, controllers, telemetry and identity infrastructure.

Cilium can be useful when its networking model and required L7 features fit the environment, especially when Cilium is already operated there. Evaluate CNI migration, kernel/platform support, shared-node failure impact, security requirements and existing policy dependencies. Neither “sidecarless” nor “eBPF” proves a latency or cost target for financial/real-time workloads.

See the maintained [service-mesh comparison](../istio/comparison/01-service-mesh-comparison.md) for broader capability boundaries.

## Version and Platform Prerequisites

For the selected release:

- The general Kubernetes e2e compatibility list is **1.33–1.36**. The released EKS CI file lists **1.33–1.35**, with 1.35 as its default. These are distinct evidence sets; newer/provider-unlisted combinations require separate validation.
- The Helm chart's permissive `kubeVersion >=1.21.0-0` is not the tested support matrix, and a newer Kubernetes release is not automatically covered.
- Hosts require supported AMD64/AArch64 Linux and normally kernel 5.10 or later, or a documented backport equivalent. L7 redirection and other advanced features have additional kernel/module requirements.
- The Gateway API reference is **v1.6.1** for this Cilium release. Check required/optional CRDs and the 1.20 TLSRoute upgrade notes before changing them; do not substitute the latest catalog version without compatibility review.

```bash
cilium version --client
cilium version
cilium status --wait --wait-duration 5m
kubectl -n kube-system get daemonset cilium
# For the dedicated Envoy mode selected below:
kubectl -n kube-system get daemonset cilium-envoy
```

The CLI's own version and the running Cilium image version are different information. Keep full status output and failures; a grep matching “Envoy” or “Hubble” does not certify readiness. An absent dedicated Envoy DaemonSet can be expected in embedded mode.

### EKS installation choices

| Mode/platform | Required distinction |
|---|---|
| Cilium AWS ENI mode | Cilium manages ENI IPAM/native routing; requires IAM, routing and node/Pod enrollment planning. The general 1.20.1 ENI reference documents IPv6 Beta, while the EKS installation page still says IPv4-only; use the IPv4 example here and verify the platform-specific IPv6 prerequisites/support separately |
| AWS VPC CNI chaining | AWS VPC CNI retains interface/IPAM responsibility; Cilium attaches its datapath afterward; advanced L7/IPsec limitations must be evaluated |
| EKS Fargate | Alternate CNIs are not supported; AWS VPC CNI is required |
| EKS Auto Mode | Alternate CNI and network-policy plugins are not supported |
| EKS Hybrid Nodes | Follow the separate AWS-supported Cilium versions/configuration/capability guidance, not EC2 ENI arguments |

AWS support for EC2-node CNI is limited to Amazon VPC CNI; alternate compatible CNIs require their own operational/vendor support. The separate Hybrid Nodes support boundary must not be inferred from a generic Cilium compatibility table.

A one-line Helm install is not a migration plan for an existing AWS VPC CNI cluster. Address API bootstrap access, kube-proxy replacement, CNI ownership, IAM, node readiness taints and recreation of pre-existing unmanaged Pods through a tested procedure. This audit did not create clusters or replace their CNI.

## Enable Selected Features

For an already correctly installed Cilium deployment, save this feature overlay as `cilium-mesh-features.yaml`:

```yaml
l7Proxy: true
envoy:
  enabled: true
hubble:
  enabled: true
  relay:
    enabled: true
  ui:
    enabled: true
```

The supported L7 flag is `l7Proxy`; `proxy.enabled` is not its replacement. The native chart check confirmed that `proxy.enabled:false` leaves L7 enabled, while `l7Proxy:false` disables it.

```bash
set -euo pipefail
umask 077
helm repo add cilium https://helm.cilium.io/
helm repo update cilium
# Preview only: reviewed-cni-values.yaml must describe the existing intended CNI mode.
helm template cilium cilium/cilium --version 1.20.1 \
  --namespace kube-system --kube-version 1.35.0 \
  -f reviewed-cni-values.yaml -f cilium-mesh-features.yaml \
  > cilium-mesh-rendered.yaml
```

This previews an example compatible Kubernetes version and merges with the installation's reviewed CNI values. Inspect the result and follow the release's supported upgrade procedure under the existing owner. It is not a complete CNI install or permission to change networking mode.

| Optional capability | Additional requirements |
|---|---|
| Gateway API | kube-proxy replacement, L7 proxy, the required v1.6.1 CRDs and an appropriate load-balancer/host-network design |
| Ingress controller | Its supported configuration and exposure model; not automatically all mesh traffic |
| Hubble metrics | The selected metric families and a configured collector; Relay/UI do not create Prometheus by themselves |
| Mutual authentication | Beta review, explicit enablement, SPIRE/storage/connectivity, applicable authentication policy and separately evaluated encryption |

For an **isolated beta-authentication evaluation**, the missing top-level flag in the old example must be included:

```yaml
authentication:
  enabled: true
  mutual:
    spire:
      enabled: true
      install:
        enabled: true
```

The chart rejects SPIRE integration without `authentication.enabled:true`. The supplied SPIRE server uses persistent storage by default, so suitable PVC provisioning is a prerequisite. This fragment does not establish production security, cross-cluster authentication or encrypted application traffic.

## L7 Policy and Observation Example

Prepare a Cilium-managed HTTP application labeled `app:productpage` in `bookinfo`, plus a Cilium-managed client labeled `app:frontend` in the same namespace. If using Bookinfo, deploy its complete required application dependencies; a productpage-only Deployment is not the complete Bookinfo application. Use verified images and readiness appropriate to the application.

The following policy selects that endpoint and permits the shown client/method/path combinations. It does not create either workload:

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: productpage-l7
  namespace: bookinfo
spec:
  endpointSelector:
    matchLabels:
      k8s:app: productpage
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:app: frontend
        k8s:io.kubernetes.pod.namespace: bookinfo
    toPorts:
    - ports:
      - port: '9080'
        protocol: TCP
      rules:
        http:
        - method: GET
          path: ^/productpage$
        - method: GET
          path: ^/health$
```

Evaluate other policies and the expected default-deny effect before applying it through the policy owner. The example permits two paths, not every static asset or dependency needed by a full browser workflow. Authentication/encryption are separate from this L7 allow policy.

```bash
# Keep this terminal running; configure the intended kube context first.
cilium hubble port-forward --port-forward 4245

# In another terminal, use the selected Hubble CLI:
hubble status --server localhost:4245
hubble observe --server localhost:4245 --namespace bookinfo --protocol http --follow
# Service-name filters are an alternative to --namespace in this CLI.
hubble observe --server localhost:4245 --to-service bookinfo/productpage
```

The selected Hubble CLI rejects combining `--namespace` with `--to-service`. Use either the namespace observation or a namespaced service-name prefix. L7 records need actual matching traffic and proxy visibility; drops occurring before the L7 proxy may require broader flow/drop inspection. No observed flows is not proof of an allowed, denied or healthy application path.

## Document Structure and References

| Guide | Scope |
|---|---|
| [Architecture](01-architecture.md) | Datapath, Envoy and API model |
| [Traffic management](02-traffic-management.md) | Routing and load balancing |
| [Security](03-security.md) | Policy, authentication and encryption boundaries |
| [Observability](04-observability.md) | Hubble and metrics |
| [Ingress/Gateway](05-ingress-gateway.md) | External traffic and Gateway API |
| [Best practices](06-best-practices.md) | Operations, migration and validation |

- [Released Kubernetes compatibility](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/network/kubernetes/compatibility.rst)
- [System requirements](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/operations/system_requirements.rst)
- [Cilium networking with Istio](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/network/servicemesh/istio.rst)
- [Envoy modes](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/security/network/proxy/envoy.rst)
- [Mutual-authentication limits](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/network/servicemesh/mutual-authentication/mutual-authentication.rst)
- [Gateway API prerequisites](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/network/servicemesh/gateway-api/installation.rst)
- [EKS ENI requirements](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/installation/requirements-eks.rst) and [AWS VPC CNI chaining](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/installation/cni-chaining-aws-cni.rst)
- [EKS alternate CNIs](https://docs.aws.amazon.com/eks/latest/userguide/alternate-cni-plugins.html) and [Hybrid Nodes CNI](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-cni.html)
- [Cilium 1.20.1 ENI IPAM / IPv6 Beta](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/network/concepts/ipam/eni.rst)
