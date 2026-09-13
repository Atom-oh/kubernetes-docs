# Cilium Deep Dive: The Future of Cloud Native Networking

## Overview and Reviewed Baseline

This section covers Cilium networking, policy and observability. Examples are reviewed against **Cilium/Helm chart 1.20.1**, Cilium CLI **0.20.0** and Hubble CLI **1.19.4**. The Cilium 1.20 Kubernetes compatibility page lists **1.33–1.36** as tested; an upstream 1.37 release does not extend that matrix automatically. Supported hosts are AMD64/AArch64 Linux with kernel **5.10+**, or the documented distribution equivalent such as RHEL 8.10's backported 4.18 kernel. Individual features have additional requirements.

> **Last Updated**: September 12, 2026

### Historical Release Notes

The dates below are GitHub publication dates in UTC and describe those releases, not current installation pins. Feature backports differ between release lines.

| Date | Release | Verified highlights |
| --- | --- | --- |
| July 14, 2026 | [1.20.0-rc.0](https://github.com/cilium/cilium/releases/tag/v1.20.0-rc.0) | First 1.20 release candidate |
| July 16, 2026 | [1.19.6](https://github.com/cilium/cilium/releases/tag/v1.19.6), [1.18.12](https://github.com/cilium/cilium/releases/tag/v1.18.12), [1.17.18](https://github.com/cilium/cilium/releases/tag/v1.17.18) | Gateway access-log configuration is listed for 1.19.6/1.18.12; the restart-policy and ClusterMesh affinity fixes cited here are listed in 1.19.6, not all three releases |
| July 21, 2026 | [1.20.0-rc.1](https://github.com/cilium/cilium/releases/tag/v1.20.0-rc.1) | Second 1.20 release candidate |
| July 29, 2026 | [1.20.0](https://github.com/cilium/cilium/releases/tag/v1.20.0) | GA release; selected changes below |
| August 3, 2026 | [1.21.0-pre.0](https://github.com/cilium/cilium/releases/tag/v1.21.0-pre.0) | Next-cycle prerelease, not this guide's deployment baseline |
| August 18, 2026 | [1.20.1](https://github.com/cilium/cilium/releases/tag/v1.20.1) | ClusterMesh documentation and bug fixes, including restart/CIDR-policy handling |
| August 18, 2026 | [1.19.7](https://github.com/cilium/cilium/releases/tag/v1.19.7) | Includes ENI interface timing, Service/LB and other fixes |
| August 18, 2026 | [1.18.13](https://github.com/cilium/cilium/releases/tag/v1.18.13) | VRRP/IGMP host-firewall support and related fixes |

The 1.20.0 announcement reports **2,660+ new commits**, supported by a **community of 1,100+ contributors**. The latter is community size, not a count of authors in this release. Highlights include:

- Gateway API **1.6.1**, TCPRoute/UDPRoute, BackendTLSPolicy, ListenerSets, ExternalAuth and CORS support, subject to each feature's configuration and API maturity.
- Datapath plugins and opt-in `bpf.datapathMode=auto`; the announced default remains veth. Dual-stack clusters can configure an IPv6 egress gateway address.
- **Beta** IPv6 ENI IPAM and migration from cluster-pool to multi-pool without rebuilding the cluster. In-place migration does not guarantee no interruption.
- Traffic distribution hints, weighted Maglev backends and stable MCS integration; Kubernetes ClusterNetworkPolicy support and **beta** ztunnel-based workload identity.
- A reported `cilium-cni` binary reduction from roughly **77 MB to 16 MB**. ADS/Delta xDS improvements are in the 1.20 announcement; do not attribute them to the 1.18.13 patch notes. These are upstream release claims, not measurements repeated in this audit.

Review the [1.20 upgrade notes](https://docs.cilium.io/en/v1.20/operations/upgrade/#upgrade-notes) for removed/replaced legacy Mutual Authentication, Envoy Go extensions, Kafka-aware policies, the old CiliumNodeConfig API, libnetwork integration and custom CNI configuration changes.

### NetworkPolicy Security Advisory

[GHSA-fm8w-2m5w-9j7r / CVE-2026-56743](https://github.com/cilium/cilium/security/advisories/GHSA-fm8w-2m5w-9j7r) has a project advisory publication date of **July 6, 2026**. The project API and GitHub global advisory API expose different dates: the latter records September 3. Use the project disclosure date for this release chronology; the global record date is not a later fix release. It affects **1.19.0–1.19.4** under the advisory's custom-cluster-name conditions: a standard Kubernetes NetworkPolicy peer containing only `ipBlock` can unintentionally permit ingress from workloads in the selected Pod's namespace. **1.19.5** fixes this issue; use an appropriate current patched release for the deployment. The advisory says CiliumNetworkPolicy/ClusterwideNetworkPolicy and releases below 1.19.0 are not affected by this particular bug.

## Introduction

Cilium provides networking, security and observability for supported Linux Kubernetes environments. Routing, IPAM, encryption and Service handling are separate choices; selecting eBPF alone does not establish every feature or a performance guarantee. The old Docker libnetwork integration was removed in 1.20, so Docker/Mesos should not be listed here as interchangeable current installation targets.

### eBPF and Key Capabilities

The kernel verifies eBPF programs before loading them and can JIT-compile them for execution at supported hooks. This enables packet processing and observability without a custom kernel module; the verifier does not prove application or policy correctness. Actual throughput, latency and memory depend on the programs, platform and workload.

Cilium offers L3/L4 policy, L7 policy through Envoy/DNS proxy integration, optional WireGuard/IPsec, Service load balancing, Hubble flow visibility, ClusterMesh and BGP advertisement. XDP acceleration is optional and device/configuration dependent. L7 features may use per-node Envoy; workload identity through ztunnel has separate beta configuration. Installing the agent alone does not enable all mesh, encryption or multi-cluster behavior.

### Comparison with Other Networking Projects

| Project | Connectivity / IPAM | Policy and related capabilities |
| --- | --- | --- |
| Cilium | Native or overlay routing; IPAM modes including cloud ENI | eBPF dataplane, Cilium/Kubernetes policies, L7 integration, Hubble and optional encryption |
| Calico | Native/IPIP/VXLAN profiles with Calico or external IPAM | Linux Iptables/Nftables/BPF, supported Windows HNS; OSS WireGuard, staged policy and separate L7 integration |
| Flannel | Pod connectivity through selected backends such as VXLAN/host-gw/WireGuard | The routing daemon does not enforce NetworkPolicy; its chart can deploy the SIGs network-policy controller with `netpol.enabled`, or it can pair with another policy implementation |
| AWS VPC CNI | VPC ENI address allocation/networking | Native network policy on supported EC2 Linux nodes and separate SG-for-Pods functionality; EKS Auto Mode is a different managed implementation |

A routing mode is not the same category as a packet-processing implementation. Calico is not limited to iptables/IPVS, Flannel can use an encrypted backend, and AWS policy is not synonymous with security groups. Service meshes are optional layers, and cross-cluster VPC connectivity is not restricted to Transit Gateway. Use a measured workload and an explicit support matrix instead of universal performance rankings.

## Architecture

The **Kubernetes API server** stores Kubernetes/Cilium resources. Cilium agents watch the relevant state and program each node's dataplane; the Cilium Operator handles cluster-level responsibilities such as the selected IPAM and identity/controller work. There is no separate mandatory cluster-wide “Cilium API Server” deployment in this basic architecture. Agents have local APIs, and the optional ClusterMesh API server serves a different purpose.

| Component | Role |
| --- | --- |
| Cilium Agent | Node-local endpoint, policy, routing/Service state and eBPF management |
| Cilium Operator | Cluster-level reconciliation and mode-dependent allocation/controller work |
| Envoy | Userspace proxy for enabled L7 policy, ingress/Gateway and related features |
| Hubble server | Node-local flow API integrated with the agent |
| Hubble Relay / UI | Aggregate flow streams / display service maps and flows |
| Prometheus metrics endpoints | Separate statistics collection; Relay/UI is not the metrics scraping pipeline |
| cilium / cilium-dbg / hubble | Cluster management CLI / agent diagnostics / flow client respectively |

### Networking and Packet Paths

Native routing needs a reachable underlay; tunneling uses VXLAN or Geneve. AWS ENI and Azure IPAM are allocation/integration choices with their own platform requirements. Cilium's BGP Control Plane advertises reachability to routers and **does not program the datapath or provide internal cluster routing**.

There is no universal XDP→TC→Pod sequence. Socket load balancing can act before packets exist, TC/netkit hooks depend on the datapath, optional XDP accelerates selected traffic, and L7 traffic may pass through Envoy. Return traffic also depends on NAT, conntrack and DSR choices. See the networking and eBPF chapters for the chosen profile.

## Integration with Amazon EKS

Choose the actual networking and compute profile before installing anything. The example addon name/version `cilium` / `v1.17.0-eksbuild.1` was not a verified AWS distribution and is not an installation command here. Inspect the Region's actual add-on catalog, publisher, license and supported compute types if considering a packaged vendor add-on.

| EKS profile | What to verify |
| --- | --- |
| Ordinary EC2 nodes, Cilium ENI replaces VPC CNI | Upstream/partner-managed CNI; AWS's supported EC2 CNI is VPC CNI. Plan CNI ownership, IAM, addressing, routes, bootstrap and node migration |
| Ordinary EC2 nodes, AWS VPC CNI chaining | VPC CNI owns interfaces/IPAM; Cilium attaches its dataplane afterwards. Existing Pods need recreation, and L7/IPsec have documented limitations |
| Hybrid Nodes | Follow AWS's specialized CNI guide and AWS-maintained Cilium build matrix; upstream 1.20.1 is not automatically the supported AWS build |
| Auto Mode | Alternate CNI/policy plugins are unsupported; use the managed NodeClass/networking features |
| Fargate | Alternate CNI/DaemonSet installation is unsupported |
| Windows | The Cilium agent requirements are Linux; do not apply this recipe to Windows workers |

AWS's general alternate-CNI page and specialized Hybrid guide differ in their Calico support wording; an example moving repositories does not establish support termination. For Hybrid Nodes, confirm the exact distribution, capability set and support owner. For Auto Mode, node-local CoreDNS/system networking is also different from the ordinary EC2 setup in this guide; mixed non-Auto nodes still need the traditional DNS Deployment.

### Prepared EC2 Cluster with Cilium ENI

These are **Cilium Helm values for a prepared IPv4 EC2 cluster**, not a complete cluster-creation or in-place migration recipe. Before using them:

1. Choose a supported EKS/Kubernetes version and Linux AMI, and establish one CNI owner. Do not delete `aws-node` from an existing workload cluster as a shortcut.
2. Prepare node taints/scheduling so workloads wait until Cilium manages the node. Upstream EKS guidance uses `node.cilium.io/agent-not-ready=true:NoExecute`; assess eviction and bootstrap effects in the actual node lifecycle.
3. Prepare subnet capacity, ENI quotas/security groups, node metadata access and the operator's required EC2 permissions. The role ARN below is a placeholder for a correctly trusted **cilium-operator ServiceAccount** role, not a role created by the values file.
4. Retain working kube-proxy and DNS for this `kubeProxyReplacement: false` example. For replacement mode, follow the separate direct API/bootstrap-DNS requirements. Select max-Pods from the actual instance/IPAM capacity, not a universal 110.

Save as `cilium-eni-values.yaml` and replace the role/interface choices with reviewed values:

```yaml
eni:
  enabled: true
ipam:
  mode: eni
routingMode: native
kubeProxyReplacement: false
ipv4:
  enabled: true
ipv6:
  enabled: false
egressMasqueradeInterfaces: eth0
serviceAccounts:
  operator:
    annotations:
      eks.amazonaws.com/role-arn: arn:aws:iam::111122223333:role/CiliumOperatorENI
```

```bash
helm repo add cilium https://helm.cilium.io/
helm repo update cilium
helm template cilium cilium/cilium --version 1.20.1 \
  --namespace kube-system -f cilium-eni-values.yaml > cilium-eni-rendered.yaml

# After preparing the cluster and reviewing the rendered configuration:
helm install cilium cilium/cilium --version 1.20.1 \
  --namespace kube-system -f cilium-eni-values.yaml
```

Manage these settings through the installation owner. A replacement `cilium-config` containing only a few keys can remove other required settings; the old `tunnel=disabled` value is replaced by `routingMode: native`. ENI allocation/permissions and SNAT behavior still require runtime validation; a successful render is not proof of usable EC2 networking.

**IPv6 qualification:** the 1.20.1 ENI IPAM reference describes IPv6 as beta, while its EKS prerequisites page still states IPv4-only ENI integration. This guide keeps an IPv4 example and records that documentation inconsistency rather than treating either statement as proof of production EKS IPv6 compatibility. Review the current ENI/dual-stack subnet requirements before a separate IPv6 design.

### VPC CNI Chaining Alternative

The upstream chaining guide requires VPC CNI 1.11.2+ and documents this profile:

```yaml
cni:
  chainingMode: aws-cni
  exclusive: false
enableIPv4Masquerade: false
routingMode: native
kubeProxyReplacement: false
```

Use it as a **different configuration**, not an overlay on the ENI-replacement values. VPC CNI remains the allocator. Upgrade the actual managed add-on through its owner rather than applying a historical upstream DaemonSet. Avoid competing policy engines on the same endpoints. Existing Pods are not retroactively attached to Cilium when the CNI chain changes; recreate them under a planned rollout and verify endpoint management. Chaining has documented L7 policy/IPsec limitations, so do not assume every example later in this page works in that profile.

### ClusterMesh

ClusterMesh needs unique cluster identities, compatible versions, reachable/nonoverlapping Pod networks, authenticated API connectivity and an appropriate exposure model. A LoadBalancer Service can create cloud resources and needs a deliberate network/security design. Creating two public endpoints is not sufficient to connect clusters safely. Follow the maintained [ClusterMesh guide](../../service-mesh/cilium-service-mesh/01-architecture.md) and the advanced chapter for the chosen topology.

## Installation and Configuration

### Client Tools

Use the appropriate official Cilium CLI 0.20.0 and Hubble CLI 1.19.4 assets for the workstation OS/architecture, and verify the supplied checksums before extraction. Linux ARM64 and AMD64 differ; macOS uses the corresponding Darwin assets. CLI versions are separate from the Cilium agent/chart version. See the [verified CLI installation guidance](../../service-mesh/cilium-service-mesh/README.md).

```bash
cilium version --client
hubble version
```

### Non-Cloud Cluster-Pool Example

The following **alternative** is for a prepared ordinary Linux cluster with kube-proxy and DNS already working. Ensure the example `10.244.0.0/16` Pod range is compatible with the cluster and does not overlap Service, node, VPC or connected-network ranges. Do not use this pool configuration for ENI mode.

```yaml
routingMode: tunnel
tunnelProtocol: vxlan
kubeProxyReplacement: false
ipv4:
  enabled: true
ipv6:
  enabled: false
ipam:
  mode: cluster-pool
  operator:
    clusterPoolIPv4PodCIDRList:
    - 10.244.0.0/16
    clusterPoolIPv4MaskSize: 24
hubble:
  enabled: true
  relay:
    enabled: true
  ui:
    enabled: true
  metrics:
    enabled:
    - dns
    - drop
    - tcp
    - flow
    - icmp
    - httpV2
```

Save as `cilium-values.yaml`, render the pinned chart, then install only on the prepared cluster:

```bash
helm template cilium cilium/cilium --version 1.20.1 \
  --namespace kube-system -f cilium-values.yaml > cilium-rendered.yaml
helm install cilium cilium/cilium --version 1.20.1 \
  --namespace kube-system -f cilium-values.yaml
cilium status --wait
```

For an existing release, use its upgrade/GitOps process, preserve owned values and follow the version-specific upgrade procedure. Repeated `cilium install` examples are not a general way to change individual settings.

| Choice | Current configuration and prerequisite |
| --- | --- |
| VXLAN/Geneve | `routingMode: tunnel` plus `tunnelProtocol`; permit the chosen encapsulation and set MTU for the path |
| Native routing | `routingMode: native`; underlay must route the Pod addresses. `autoDirectNodeRoutes` needs suitable direct connectivity, not arbitrary multi-subnet routing |
| kube-proxy replacement | `kubeProxyReplacement: true` or `false`, not legacy `strict`; replacement requires reachable `k8sServiceHost`/`k8sServicePort` and the documented bootstrap plan |
| WireGuard | Enable supported encryption mode after checking kernel/platform and peer paths; it does not encrypt every possible traffic path automatically |
| IPsec | Requires the documented key Secret, key distribution/rotation and compatible mode; the Helm enable flag alone is incomplete |
| XDP/DSR/BBR | Separate device/kernel/topology-dependent choices, not a universal install preset |

## Network Policies

Kubernetes `networking.k8s.io/v1` NetworkPolicy and Cilium `cilium.io/v2` policies are distinct APIs. Multiple allow policies can combine. These examples use **separate prepared test namespaces** so the L4 allow does not silently bypass the L7 restriction. Inspect all policies selecting the actual endpoints before drawing conclusions.

### L4 Example

In `cilium-l4-demo`, this selects backend Pods and permits ingress from same-namespace frontend Pods on TCP 8080:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-frontend-to-backend
  namespace: cilium-l4-demo
spec:
  podSelector:
    matchLabels:
      app: backend
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: frontend
    ports:
    - port: 8080
      protocol: TCP
```

### HTTP Example

In a separate `cilium-l7-demo`, this selects backend Pods and restricts plaintext HTTP on TCP 8080 to the stated method/path from frontend Pods in that namespace. L7 proxy support must be available in the chosen CNI mode; encrypted HTTP is not automatically inspected without a supported termination configuration.

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: allow-product-read
  namespace: cilium-l7-demo
spec:
  endpointSelector:
    matchLabels:
      k8s:app: backend
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:app: frontend
        k8s:io.kubernetes.pod.namespace: cilium-l7-demo
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
      rules:
        http:
        - method: GET
          path: ^/api/v1/products$
```

Do not add a matching unrestricted L4 allow for the same peers/port: Cilium documents that such an allow removes the effect of the narrower L7 restrictions. L7 denial can return an HTTP 403 rather than a packet drop. Test allowed GET requests and denied methods/paths with real endpoint identities.

### DNS/FQDN Example

In `cilium-dns-demo`, this permits DNS queries to ordinary CoreDNS Pods and TCP 443 to addresses learned for `api.example.com`. The domain is an example; replace it with an approved destination. The broad `*.amazonaws.com` wildcard is not an account/resource boundary and is omitted.

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: allow-api-domain
  namespace: cilium-dns-demo
spec:
  endpointSelector:
    matchLabels:
      k8s:app: web
  egress:
  - toEndpoints:
    - matchLabels:
        k8s:k8s-app: kube-dns
        k8s:io.kubernetes.pod.namespace: kube-system
    toPorts:
    - ports:
      - port: '53'
        protocol: ANY
      rules:
        dns:
        - matchPattern: '*'
  - toFQDNs:
    - matchName: api.example.com
    toPorts:
    - ports:
      - port: '443'
        protocol: TCP
```

The DNS wildcard permits queries to the selected resolver, not connections to every returned address. It can still carry arbitrary DNS names; restrict query names where required, accounting for DNS search suffixes. NodeLocal DNS or a different resolver needs the correct destination selection. FQDN policy is DNS-derived IP authorization, not TLS hostname verification or HTTP URL authorization; shared IPs and application TLS/authentication still matter.

## Observability with Hubble

The cluster-pool values above enable Relay/UI and component metrics. For an existing installation, apply the intended Hubble values through its configuration owner; `cilium hubble enable --ui` is a supported convenience command, but `cilium hubble enable --metrics=...` is not a supported 0.20.0 CLI flag. Configure `hubble.metrics.enabled` in Helm values instead. Do not enable legacy `http` and `httpV2` handlers together.

Keep the Relay port-forward running in one terminal:

```bash
cilium hubble port-forward --port-forward 4245
```

In another terminal with Hubble CLI installed:

```bash
hubble observe --server 127.0.0.1:4245 --namespace cilium-l7-demo
hubble observe --server 127.0.0.1:4245 --protocol http
hubble observe --server 127.0.0.1:4245 --from-label k8s:app=frontend --to-label k8s:app=backend
hubble observe --server 127.0.0.1:4245 --verdict DROPPED
hubble observe --server 127.0.0.1:4245 --http-status 403
```

This local example assumes the default Relay server configuration; a TLS-enabled Relay needs the corresponding client trust/authentication. HTTP events require the traffic to traverse the configured L7 proxy. `DROPPED` is a datapath verdict, not every failed application request. Use `cilium hubble ui` for the UI port-forward, and configure Prometheus target discovery separately for metrics. Hubble flow streaming is not distributed application tracing by itself.

## Testing and Operations

Connectivity/performance commands create test workloads and may change policy or generate substantial traffic. Use a reviewed test namespace/environment and permissions; this audit did not execute them against a cluster.

```bash
cilium connectivity test --help
cilium connectivity perf --help
```

The performance subcommand is `cilium connectivity perf`; `connectivity test --test=performance` merely supplies a test-name filter and is not the performance runner. Record software versions, topology, traffic and raw results before comparing throughput/latency.

For inspection, distinguish the management CLI from **agent-side `cilium-dbg`**:

```bash
cilium status --verbose
kubectl get cnp,ccnp -A
kubectl get pods -n kube-system -l k8s-app=cilium -o wide

# Choose the agent Pod on the affected node.
CILIUM_POD=replace-with-actual-cilium-pod
kubectl exec -n kube-system "$CILIUM_POD" -c cilium-agent -- cilium-dbg endpoint list
kubectl exec -n kube-system "$CILIUM_POD" -c cilium-agent -- cilium-dbg map list
kubectl exec -n kube-system "$CILIUM_POD" -c cilium-agent -- cilium-dbg metrics list
kubectl logs -n kube-system "$CILIUM_POD" -c cilium-agent --since=15m --tail=200 --timestamps
```

`cilium endpoint list`, `cilium bpf maps list` and `cilium metrics list` are not equivalent commands in the management CLI. `cilium sysdump` can collect diagnostic material; protect the resulting infrastructure/log data. A Ready agent or successful scrape is not a substitute for application and negative policy tests.

### Operational Priorities

- Measure before enabling map preallocation, XDP, DSR, BBR or a fixed device pattern. These consume resources or change packet paths and require feature-specific checks.
- Introduce default-deny in a selected scope with DNS, API, identity and application dependencies explicitly allowed. Check new Pods and upgrade transitions as well as established connections.
- Keep encryption, certificate/key rotation, policy enforcement and observability as separate acceptance checks. Preserve a usable management/recovery path.
- Review the current platform matrix and supported upgrade path. Historical release announcements do not establish current deployment compatibility.

## Deep Dive Table of Contents

**[Introduction to Cilium and Basic Concepts](01-introduction.md)**
- Cilium Overview and History
- Container Networking Basics
- Understanding CNI (Container Network Interface)
- Cilium's Differentiating Features

**[eBPF Technology Deep Dive](02-ebpf.md)**
- Introduction to eBPF Technology and History
- How eBPF Works Inside the Kernel
- eBPF Program Types and Maps
- Utilizing eBPF in Cilium

**[Networking Models and VXLAN](03-networking.md)**
- Comparison of Container Networking Models
- VXLAN Technology Deep Dive
- Cilium's Overlay Networking
- Performance Optimization Techniques
- Routing Mechanisms (Encapsulation vs Native-Routing)
- Cloud Provider Networking (AWS ENI, Google Cloud)

**[IPAM and Network Policies](04-ipam-policy.md)**
- IP Address Management (IPAM) Strategies
- Kubernetes and Cilium IPAM Integration
- Network Policy Design and Implementation
- Multi-Cluster Scenarios
- IPAM Mode Deep Dive (Cluster Scope, Kubernetes Host Scope, Multi-Pool)
- Cloud Provider IPAM (Azure IPAM, AWS ENI, GKE)
- CRD-based IPAM

**[L2-L7 Networking and Load Balancing](05-l2-l7-networking.md)**
- Understanding OSI Model Layers (L2, L3, L4, L7)
- Cilium's Layer-specific Features
- Service Mesh Integration
- Load Balancing Architecture
- Masquerading Configuration and Implementation Modes
- IPv4 Fragment Handling

**[Security and Visibility](06-security-visibility.md)**
- Cilium's Security Features
- Network Visibility and Monitoring
- Hubble Architecture and Usage
- Real-time Threat Detection

**[Advanced Topics and Real-World Cases](07-advanced-topics.md)**
- Performance Tuning and Troubleshooting
- Large-Scale Deployment Strategies
- Real-World Use Case Studies
- Future Roadmap and Development Direction

## Additional Resources

- [Networking Concepts Deep Dive](networking-concepts.md)
- [Glossary and Abbreviations](glossary.md)

## References

- [Cilium 1.20 Kubernetes compatibility](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/network/kubernetes/compatibility.rst)
- [Cilium system requirements](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/operations/system_requirements.rst)
- [EKS prerequisites](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/installation/requirements-eks.rst)
- [Cilium ENI IPAM](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/network/concepts/ipam/eni.rst)
- [AWS alternate CNI support](https://docs.aws.amazon.com/eks/latest/userguide/alternate-cni-plugins.html)
- [AWS Hybrid Nodes CNI](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-cni.html)
- [Cilium L7 policy semantics](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/security/policy/layer7.rst)
- [Hubble project](https://github.com/cilium/hubble)
- [Flannel networking and policy integration](https://github.com/flannel-io/flannel)
- [Calico comparison terminology](../calico/glossary.md)

## Quiz

To test what you've learned in this section, try the [Cilium Deep Dive Quiz](../../quizzes/networking/cilium/01-introduction-quiz.md).
