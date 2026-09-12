# Part 7: Advanced Calico Topics

> **Supported Versions**: Calico 3.32.2 / Kubernetes 1.34–1.36 (tested range)
> **Last Updated**: September 12, 2026

## Overview

This chapter covers advanced Calico topics for production environments, including IPAM deep dive, WireGuard encryption, Egress Gateway, multi-cluster federation, Windows container support, and large-scale cluster design patterns.

## IPAM Deep Dive

This section describes **Calico IPAM**. Host-local and cloud-provider IPAM are different allocators; creating a Calico IPPool does not switch another CNI to Calico IPAM.

### Blocks, Affinity and Allocation Limits

Calico allocates addresses from blocks associated with nodes. An IPv4 `/26` contains 64 addresses and an IPv6 `/122` also contains 64; that is not a guarantee of 64 usable Pod addresses in every platform. Windows reserves four addresses per Calico-owned block.

![The datastore hands out fixed-size /26 blocks from the IPPool 10.244.0.0/16 to each node, and each node allocates individual pod IPs out of its own affine blocks, receiving another block when one is exhausted.](../../.gitbook/assets/en-networking-calico-07-advanced-topics-0.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-calico-07-advanced-topics-0.html)

> The diagram shows an allocation model, not a node-local cache that eliminates all datastore writes. A block's affinity is not necessarily released immediately when its last Pod disappears: allocations for tunnels/VMs and reconciliation/lifecycle state also matter.

With normal automatic allocation, Calico can use an existing affine block, claim another eligible block, or borrow where permitted. `strictAffinity`, `autoAllocateBlocks`, global/per-request block limits, pool selection and platform constraints can make allocation fail even when another pool still has free addresses.

![On pod creation, Calico tries the node's own affine block first, then claims an unclaimed block from the pool, then borrows from another node's block, and only fails when no free IP exists anywhere.](../../.gitbook/assets/en-networking-calico-07-advanced-topics-1.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-calico-07-advanced-topics-1.html)

> The simplified flow assumes eligible pools, automatic block allocation, permitted borrowing and no limiting cap. Windows does not support borrowing; do not use the figure as an unconditional guarantee that only total address exhaustion can fail.

Use `IPAMConfiguration/default` to inspect global settings. The reference web page lists a default block cap of 20, but the released **3.32.2 implementation and public CRD initialize `maxBlocksPerHost` to 0** when no configuration exists. Zero means no global block cap; per-request/platform limits still apply, and existing clusters retain their configured value. A positive global cap must be paired with `strictAffinity: true` in the reviewed IPAM configuration path.

### Choose Block Size before Pool Creation

The default is `/26` for IPv4 and `/122` for IPv6. Supported ranges are IPv4 `/20`–`/32` and IPv6 `/116`–`/128`. Choose by expected address demand, node count, routing aggregation and allocation overhead, not GPU bandwidth or a fixed “200 nodes means /28” rule.

```yaml
# Fresh-pool example; do not apply over an existing pool or overlapping pools.
apiVersion: projectcalico.org/v3
kind: IPPool
metadata:
  name: demo-ipv4-pool
spec:
  cidr: 10.244.0.0/16
  blockSize: 26
  ipipMode: Never
  vxlanMode: Always
  natOutgoing: true
  nodeSelector: all()
```

`blockSize` and pool CIDR cannot be changed in place. A new pool/migration must preserve the actual cluster's routing, Service/node CIDR boundaries and workload allocation plan; see [networking modes](03-networking-modes.md). Do not overlap this aggregate pool with the sub-pool example below.

### Host-Local IPAM

Host-local uses node-local allocation state and the Kubernetes-provided per-node PodCIDR configuration. The operator selects it under **`spec.cni.ipam.type: HostLocal`**:

```yaml
# Installation fragment: preserve other settings through the configuration owner.
apiVersion: operator.tigera.io/v1
kind: Installation
metadata:
  name: default
spec:
  cni:
    type: Calico
    ipam:
      type: HostLocal
```

There is no `calicoNetwork.hostLocalIPAMEnabled` switch. The Kubernetes controller/networking setup must already provide valid distinct node PodCIDRs; manually patching existing nodes is not an IPAM migration procedure. Do not assume a universal immediate/delayed release or scale ranking between the two allocators.

### Multiple Pools and Explicit Requests

Use disjoint pools with a documented purpose. The third example is manual-only so general workloads do not automatically consume the non-SNAT range:

```yaml
# Alternative to demo-ipv4-pool; these sub-pools must not overlap another pool.
apiVersion: projectcalico.org/v3
kind: IPPool
metadata:
  name: production-pool
spec:
  cidr: 10.244.0.0/18
  blockSize: 26
  vxlanMode: Always
  natOutgoing: true
  nodeSelector: node-type == 'production'
---
apiVersion: projectcalico.org/v3
kind: IPPool
metadata:
  name: development-pool
spec:
  cidr: 10.244.64.0/18
  blockSize: 28
  vxlanMode: Always
  natOutgoing: true
  nodeSelector: node-type == 'development'
---
apiVersion: projectcalico.org/v3
kind: IPPool
metadata:
  name: routed-workloads-pool
spec:
  cidr: 10.244.128.0/18
  blockSize: 26
  ipipMode: Never
  vxlanMode: Never
  natOutgoing: false
  assignmentMode: Manual
  allowedUses: [Workload]
```

`natOutgoing: false` needs a working external return route and may still be followed by upstream NAT. It does not create an egress gateway or stable per-namespace SNAT address. For LoadBalancer allocation, use the separate `allowedUses: [LoadBalancer]` workflow in the [BGP guide](04-bgp-deep-dive.md).

The following Pod needs a prepared namespace, matching node labels and a reviewed workload image replacing the placeholder:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: production-app
  namespace: calico-demo
  annotations:
    cni.projectcalico.org/ipv4pools: '["production-pool"]'
spec:
  nodeSelector:
    node-type: production
  containers:
    - name: app
      image: registry.example.com/team/app:approved
```

The annotation requests an IP pool; `nodeSelector` schedules the Pod. In the reviewed Calico IPAM code, an explicit pool request bypasses pool node/namespace selectors for compatibility, so those selectors are **not an authorization boundary**. Disabled or nonexistent pools still fail. Namespace annotations can supply defaults for Pods, but this does not turn pool selection into a network policy.

### IPv6 and Dual Stack

The Kubernetes cluster, CNI/IPAM, node addresses and underlay must already support the chosen IP families. Adding pools or a Felix flag alone does not convert a cluster's IP-family configuration.

```yaml
# A separate fresh dual-stack example.
apiVersion: projectcalico.org/v3
kind: IPPool
metadata:
  name: dual-ipv4-pool
spec:
  cidr: 10.244.0.0/16
  blockSize: 26
  vxlanMode: Always
  natOutgoing: true
---
apiVersion: projectcalico.org/v3
kind: IPPool
metadata:
  name: dual-ipv6-pool
spec:
  cidr: fd00:10:244::/48
  blockSize: 122
  ipipMode: Never
  vxlanMode: Always
  natOutgoing: false
```

IPv6 VXLAN is supported on the compatible Linux dataplane; IPv6 IP-in-IP is not. The ULA range above is not globally routable simply because it is IPv6. `natOutgoing: false` requires suitable return routing or another explicitly designed egress path.

Node address autodetection belongs to operator configuration (or the corresponding installation environment), not invented Felix fields:

```yaml
# Operator configuration fragment, not a replacement for the existing Installation.
apiVersion: operator.tigera.io/v1
kind: Installation
metadata:
  name: default
spec:
  calicoNetwork:
    nodeAddressAutodetectionV4:
      kubernetes: NodeInternalIP
    nodeAddressAutodetectionV6:
      kubernetes: NodeInternalIP
```

The Felix `ipv6Support` field is a boolean, not `Enabled`. It controls Felix processing and is not a replacement for the full dual-stack prerequisites.

### Investigate Exhaustion before Releasing Addresses

```bash
kubectl get ipamconfigurations.projectcalico.org default -o yaml
calicoctl ipam show
calicoctl ipam show --show-blocks
calicoctl ipam check --show-problem-ips -o ipam-report.json
```

Review pool eligibility, reservations, affinity, per-host limits and actual workload/tunnel/VM ownership. Do not release an address solely because a sample command calls it orphaned. `calicoctl ipam release --block` is not a supported reviewed CLI option.

The release tool supports `--from-report` and can intersect multiple reports; at least one must be fresh, and report-based cleanup carries allocation sequence information. Follow the versioned recovery procedure after verifying the reported allocations. Avoid `--force`, direct IPAMBlock/BlockAffinity deletion or arbitrary single-IP release as a general exhaustion fix.

## Inspect Node-Affine CIDR Blocks

`BlockAffinity` is managed by Calico IPAM and exposes state, node, CIDR, deletion and affinity type. It is not the same thing as `Node.spec.podCIDR`, and it is not a complete snapshot of every host route when borrowed or migrating addresses exist.

```bash
kubectl get blockaffinities.projectcalico.org \
  -o custom-columns='NAME:.metadata.name,CIDR:.spec.cidr,NODE:.spec.node,STATE:.spec.state,DELETED:.spec.deleted,TYPE:.spec.type'
kubectl get ippools.projectcalico.org \
  -o custom-columns='NAME:.metadata.name,CIDR:.spec.cidr,BLOCK_SIZE:.spec.blockSize'

# Review active host affinities; exclude deletion states and virtual affinities.
kubectl get blockaffinities.projectcalico.org -o json | jq -r \
  '.items[] | select(.spec.state == "confirmed" and .spec.deleted != true and ((.spec.type // "") == "" or .spec.type == "host")) | [.spec.cidr, .spec.node] | @tsv'
```

These are inventory outputs, not ready-to-execute `ip route add` commands. Routing also needs actual node next hops, current allocation state, pool export/encapsulation rules and any more-specific routes. Do not assume a placeholder node IP or all affinity records form a valid static routing plan.

For **EKS Hybrid Nodes**, the [specialized CNI guide](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-cni.html) documents AWS-maintained Cilium builds and moves Calico examples to the Hybrid Examples repository. AWS's [general alternate-CNI page](https://docs.aws.amazon.com/eks/latest/userguide/alternate-cni-plugins.html) still describes core Cilium/Calico support for Hybrid Nodes. These pages do not supply a consistent versioned Calico support matrix; moving examples alone does not establish that support ended. Confirm the exact distribution, capabilities and support owner for the planned deployment. This section covers Calico IPAM inventory, not a Hybrid installation recipe.

## WireGuard Encryption

WireGuard protects supported traffic **between capable, configured nodes**. It is not application-to-application TLS, and same-node Pod traffic does not traverse that inter-node tunnel. Traffic involving a node without WireGuard support may remain unencrypted. Check the actual CNI, IP family and workload/host traffic path before treating encryption as a requirement that has been met.

![Traffic leaves Pod A in plaintext, is encrypted by Node 1's WireGuard interface (wireguard.cali), crosses the underlay from eth0 to eth0 as an encrypted UDP 51820 WireGuard tunnel, and is decrypted by Node 2's WireGuard interface back to plaintext before reaching Pod B.](../../.gitbook/assets/en-networking-calico-07-advanced-topics-2.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-calico-07-advanced-topics-2.html)

> “Plaintext” in this diagram means not protected by the WireGuard tunnel on the local leg; the application may independently use TLS. The example shows the default IPv4 WireGuard port 51820. IPv6 has separate interface/port settings.

### Enable Only the Required IP Families

```yaml
# Example for an already compatible dual-stack Linux deployment.
apiVersion: projectcalico.org/v3
kind: FelixConfiguration
metadata:
  name: default
spec:
  wireguardEnabled: true
  wireguardEnabledV6: true
```

Use `wireguardEnabled` for IPv4 and `wireguardEnabledV6` for an enabled IPv6 path; do not enable IPv6 merely because the field exists. Preserve other Felix settings through the configuration owner and verify kernel support at both peers. There is no `WireguardCrossSubnet` operator IPPool encapsulation value.

Leave MTU auto-detection in place unless the actual underlay/encapsulation path requires an override. A 1500-byte IPv4 underlay with WireGuard's 60-byte overhead suggests 1440; IPv6 overhead and platform-specific paths differ. The [MTU discussion](03-networking-modes.md) explains why alternative encapsulation paths must not be blindly added together.

`wireguardHostEncryptionEnabled` concerns supported **inter-node host-originated/host-network** traffic, not encrypting a local host-to-Pod hop. Consult the platform's supported traffic matrix rather than applying it as a universal switch.

### Keys, Keepalives and Verification

Calico manages node keys and publishes public-key information for peers. WireGuard's protocol derives fresh session keys during handshakes; that is distinct from an administrator's node-identity rotation policy.

Persistent keepalives keep NAT/firewall state alive during idle periods. The familiar WireGuard example interval of 25 **seconds** is not a key-rotation interval. Neither `wireguardPersistentKeepAlive` nor `wireguardPersistentKeepalive` is a supported Felix field in the reviewed Open Source schema.

```bash
# On the intended node with wireguard-tools available:
WIREGUARD_INTERFACE=wireguard.cali
wg show "$WIREGUARD_INTERFACE" public-key
wg show "$WIREGUARD_INTERFACE" latest-handshakes
wg show "$WIREGUARD_INTERFACE" endpoints
wg show "$WIREGUARD_INTERFACE" transfer
```

```bash
# Kubernetes datastore: public identity information only.
kubectl get nodes -o json | jq -r \
  '.items[] | [.metadata.name, (.metadata.annotations["projectcalico.org/WireguardPublicKey"] // "-"), (.metadata.annotations["projectcalico.org/WireguardPublicKeyV6"] // "-")] | @tsv'
```

Choose the actual interface for the desired IP family. Public keys, handshakes and byte counters aid diagnosis but do not prove that every application flow uses encryption. Verify the intended traffic path and expected encrypted transport. `calicoctl node status` is not a WireGuard status table, and there is no need to print private keys for this check.

### Preserved Performance Records

The earlier locales provided different, unverified figures. No test date, hardware, acceleration configuration, software versions or raw results were supplied. Preserve them as historical reported values, not current Calico/WireGuard performance guarantees.

**Record A — earlier English guide:**

| Metric | WireGuard | IPsec (AES-GCM) |
| --- | --- | --- |
| Throughput change from baseline | −5 to −10% | −15 to −25% |
| Added latency | 0.1–0.3 ms | 0.5–1.0 ms |
| CPU usage change | +10–15% | +30–50% |


**Record B — earlier Korean guide:**

| Metric | WireGuard | IPsec (AES-GCM) |
| --- | --- | --- |
| Throughput as percentage of baseline | 95–98% | 85–90% |
| Latency change from baseline | +5–10% | +15–25% |
| Qualitative CPU description | Medium | High |


Record B used an unencrypted baseline of 100% and described unencrypted CPU usage as low. The percentage changes do not specify percentage points versus relative CPU change. These records must not be combined into one experiment.

### WireGuard and IPsec Trade-offs

WireGuard uses a deliberately constrained cryptographic design; IPsec is a framework with multiple implementations, algorithms and key-management choices. CPU cost, packet overhead, hardware offload, roaming and configuration complexity depend on those choices and the measured path. Unversioned source-line counts are not a security metric, and the reviewed Open Source Felix schema has no `ipsecEnabled` field.

For FIPS requirements, compare the selected product's current certification record, version and operating conditions.

## Egress Gateway

Calico Enterprise's egress gateway is a **transit Pod** that performs SNAT for selected clients. It has its own product/platform requirements; the Open Source baseline at the top of this chapter is not an Enterprise compatibility matrix.

The path is client egress policy → tunnel to gateway Pod → gateway SNAT → gateway egress policy → external network. NetworkPolicy Allow does not redirect packets or perform SNAT. `BGPConfiguration.serviceExternalIPs` advertises Service routes, rather than allocating workload egress identities.

### Current Commercial Configuration Shape

The documented on-premises Calico-CNI path requires a supported Enterprise installation, prepared namespaces/Pod-security permissions, routed egress addresses and UDP 4790 connectivity. GKE and Windows are excluded. AWS and Azure have separate procedures; do not transplant this pool into a cloud-provider CNI setup.

Through the existing default Felix configuration owner, enable `egressIPSupport` uniformly as `EnabledPerNamespace` or, where authorized, `EnabledPerNamespaceOrPerPod`. The gateway resource is **`operator.tigera.io/v1` EgressGateway**. The operator manages its image and configuration; do not invent a `calico/egress-gateway` Deployment.

```yaml
# Calico Enterprise example, not an Open Source gateway installation.
apiVersion: projectcalico.org/v3
kind: IPPool
metadata:
  name: egress-demo-pool
spec:
  cidr: 203.0.113.0/28
  blockSize: 32
  nodeSelector: "!all()"
  natOutgoing: false
---
apiVersion: operator.tigera.io/v1
kind: EgressGateway
metadata:
  name: approved-egress
  namespace: calico-egress
spec:
  replicas: 2
  ipPools:
    - cidr: 203.0.113.0/28
  template:
    metadata:
      labels:
        egress-code: approved
    spec:
      nodeSelector:
        kubernetes.io/os: linux
---
apiVersion: v1
kind: Namespace
metadata:
  name: calico-demo
  annotations:
    egress.projectcalico.org/selector: egress-code == 'approved'
    egress.projectcalico.org/namespaceSelector: projectcalico.org/name == 'calico-egress'
```

Replace the documentation CIDR with addresses you control and configure encapsulation/routing for the actual network. `/32` blocks avoid reserving a larger block for each gateway. `!all()` prevents automatic general allocation; explicitly requesting the pool can still use it, so annotation permissions must be controlled.

Two replicas require two available IPs and appropriate node/failure-domain placement; replicas alone do not guarantee availability. The namespace selector is necessary because gateway selection otherwise defaults to the client's namespace.

With `natOutgoing: false`, the gateway Pod IP survives that Calico NAT stage, but upstream NAT can still change it. Enabling gateway-pool NAT can instead expose the gateway node IP. Verify the source observed by the external receiver and allow the intended address set. Gateway replacement or upgrade can break existing connections.

### Policy and Identity Boundaries

Client egress policy sees the **external destination**. Allowing a client to contact the gateway Pod IP does not route or authorize its original external flow. At gateway egress, original client identity/source-port information has been translated. Destination CIDR/port policy remains useful, but domain-based policy at that hook is not supported.

Advanced `EgressGatewayPolicy` routing has its own destination/gateway selection and `maxNextHops` field. It is not the former invented `maxGatewaysPerClient` field on a `projectcalico.org/v3 EgressGateway`.

For Open Source, use an independently configured application proxy or underlay/cloud NAT solution where appropriate, and control allowed traffic separately. An Envoy Pod without bootstrap/listener/upstream configuration is not a functioning egress proxy. A stable source address supports an external allowlist; it does not by itself establish PCI DSS/HIPAA compliance or application authorization.

## Multi-Cluster Connectivity and Federation

Separate routed reachability, endpoint identity and Service discovery. BGP exchanges routes but does not distribute Kubernetes policies or DNS records. Typha distributes state within its deployment; it is not a lead instance reporting to the invented shared Federation Controller in the earlier diagram.

### Open Source Routed Connectivity

Prepare non-overlapping addresses, bidirectional routing, reachable next hops and policy in each cluster. Account for NAT: a remote Pod CIDR outside local Calico pools can be masqueraded by `natOutgoing`, changing the receiver's observed source. Plan appropriate exclusions and routing instead of assuming Pod identity survives.

```yaml
# Receiving cluster only, after routing/source preservation is verified.
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: default.remote-client-access
spec:
  order: 100
  namespaceSelector: kubernetes.io/metadata.name == 'calico-demo'
  selector: app == 'shared-service'
  types: [Ingress]
  ingress:
    - action: Allow
      protocol: TCP
      source:
        nets: [10.245.0.0/16]
      destination:
        ports: [8080]
```

This policy selects local receiving endpoints only. `GlobalNetworkPolicy` means cluster/datastore-wide scope, not automatic application to remote clusters. Verify sender egress, receiver ingress and actual source addresses. Policy distribution requires an explicitly managed workflow; it is not a BGP or Typha side effect.

### Enterprise Federation

The current Enterprise guide separates:

| Capability | What it does |
| --- | --- |
| Federated endpoint identity | Uses remote workload/host endpoint information as input to local policy calculation |
| Federated Services Controller | Reads Service/endpoint information through remote Kubernetes APIs and maintains selected local federated Services |
| Multi-cluster networking | Provides a supported overlay or works with separately configured routable Pod networks |

Federated endpoint identity **does not replicate network policies**. Remote policies are not automatically enforced locally; each cluster's policies remain locally applied. Routable Pod IPs and source preservation are prerequisites for identity and useful remote Service endpoints.

A commercial federated Service uses an annotation that selects **backing Services by labels**, not Pods:

```yaml
# Commercial controller integration; backing Services already exist.
apiVersion: v1
kind: Service
metadata:
  name: catalog-federated
  namespace: calico-demo
  annotations:
    federation.tigera.io/serviceSelector: app == 'catalog'
spec:
  type: ClusterIP
  ports:
    - name: http
      protocol: TCP
      port: 8080
```

Backing Services must be in the same namespace name across the selected clusters and expose matching port **names and protocols**. The federated Service omits `spec.selector`; its `targetPort` is not the backing-port selector. Do not manually manage its endpoint records.

Remote API credentials, controller installation, Kubernetes-version/EndpointSlice compatibility and network reachability are separate prerequisites. This example does not establish them or prove cross-cluster failover. Follow the product's current federation procedure and test the real paths; do not copy the guide's historical 2018 Endpoints output as a current deployment manifest.

## Windows Container Support

Calico supports Windows through **HNS**, with substantial feature/platform constraints. Linux nodes are still needed for the control components and Typha. A mixed cluster is not a way to combine the Calico eBPF dataplane with Windows.

### Version and Platform Intersection

For a Kubernetes 1.36 example within Calico 3.32's tested range, Windows Server 2022 is listed by both Kubernetes and Calico. Kubernetes 1.36 also lists Server 2025, while the Calico requirements page still includes older Server 1809 and Server 2022 entries. Do not assume either the old OS or every newly supported Kubernetes OS is validated by the selected Calico/provider combination. Match the host and container base-image OS/build and use compatible maintained runtime/kubelet/kube-proxy versions.

Kubernetes Windows Pods use process isolation, not Hyper-V container isolation. Calico's current documented installation uses operator-managed HostProcess containers. The old 3.29 ZIP/manual-service example and old runtime/kubelet versions in legacy instructions are not a current installation recipe.

| Area | Current Calico Windows constraints |
| --- | --- |
| Network | IPv4 VXLAN without CrossSubnet, or supported non-overlay BGP; not IPIP |
| VXLAN | UDP 4789; no Windows CrossSubnet/custom VXLAN MTU support in this guide |
| IPAM | No borrowing; four addresses reserved per Calico-owned block, so `/26` gives 60 Pod addresses; account for the Windows kube-proxy single-block constraint |
| Routing | Windows can use supported BGP peering but cannot be a route reflector or advertise Service IPs |
| Unsupported here | IPv6/dual stack, eBPF, WireGuard, host-endpoint policy, Istio application-layer policy |
| Managed platforms | EKS Windows uses VPC CNI; AKS uses Azure CNI; GKE is not interchangeable with a self-managed GCE cluster |

### Operator Configuration

Provision compatible Windows nodes first and verify Linux capacity for the controller/Typha HA profile. The Windows guide calls for three Linux workers for that profile. Prepare a stable direct API endpoint using `kubernetes-services-endpoint` in the operator namespace and use the actual Service CIDR, not an assumed kubeadm default.

This is the configuration shape for the **self-managed Calico-CNI VXLAN alternative**. Do not replace an existing installation's pool list with the example or apply it as the EKS/Azure CNI profile:

```yaml
# Self-managed Calico-CNI IPv4 VXLAN target configuration; preserve existing pools/settings.
apiVersion: operator.tigera.io/v1
kind: Installation
metadata:
  name: default
spec:
  serviceCIDRs:
    - 10.96.0.0/12
  cni:
    type: Calico
  calicoNetwork:
    linuxDataplane: Iptables
    windowsDataplane: HNS
    bgp: Disabled
    ipPools:
      - cidr: 10.244.0.0/16
        blockSize: 26
        encapsulation: VXLAN
        natOutgoing: Enabled
```

The valid field is `spec.calicoNetwork.windowsDataplane`, not root `spec.windowsDataplane` or `windowsIPAM`. VXLAN uses `VXLAN`, not `VXLANCrossSubnet`, with BGP disabled for this profile. A non-overlay BGP alternative uses different configuration; do not mix Linux IPIP pools with Windows peers.

```bash
kubectl get ipamconfigurations.projectcalico.org default -o yaml
# Required for the documented mixed Windows/Calico-IPAM installation:
kubectl patch ipamconfigurations.projectcalico.org default --type=merge \
  -p '{"spec":{"strictAffinity":true}}'
```

Strict affinity is required for the documented Calico-IPAM Windows setup. Plan block size before networking Pods: changing it later is not supported. Ensure kube-proxy is present on Windows with the appropriate version/owner. Migrating a legacy manual installation to HostProcess can remove old Calico services and replace files, so inventory and preserve its configuration first.

```bash
kubectl get nodes -l kubernetes.io/os=windows -o wide
kubectl get pods -n calico-system -l k8s-app=calico-node-windows -o wide
kubectl logs -n calico-system -l k8s-app=calico-node-windows -c felix --tail=100
```

This is configuration review, not a Windows provisioning or failover test. Test Pod/Service traffic and policy on both operating systems; Windows NAT changes may apply only to newly networked Pods and some HNS policy updates can reset connections.

### HNS and the Packet Path

![On a Windows node, traffic from the Windows containers converges on the Host Networking Service (HNS), which the Calico Node Windows Service programs with networking and policy, then passes through the Virtual Filtering Platform (VFP) for packet filtering before leaving via the physical NIC.](../../.gitbook/assets/en-networking-calico-07-advanced-topics-7.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-calico-07-advanced-topics-7.html)

> HNS/HCS manage networks and endpoints; virtual-switch/VFP mechanisms enforce the data path. Packets do not pass through a Calico userspace service as a forwarding proxy. The “Windows Service” box is a logical agent: current operator installations run these components in HostProcess containers.

## Calico Product Editions

Use the current edition and feature requirements rather than treating all observability/policy capabilities as Enterprise-only.

| Capability | Open Source 3.32 baseline | Commercial distinction |
| --- | --- | --- |
| Networking and policy | Calico networking, global/namespaced policy, multiple supported dataplanes | Additional product/platform integrations |
| Policy tiers/RBAC | Available, including Calico tier-aware authorization | Product management workflows and additional controls |
| HTTP policy | Available through configured Istio/Dikastes integration | Check the product-specific enforcement path |
| Flow visibility/UI | Goldmane/Whisker and staged-policy workflow are available | Additional analytics, reporting and management features |
| DNS domain policy | `domains` is absent from the reviewed OSS CRD | Documented commercial DNS policy |
| Egress/federation | Independent routing/proxy designs are possible; no invented OSS gateway/federation CR | Supported egress gateways, remote identity and federated Services |
| Support | Community/project support | Terms depend on the purchased support offering |

Calico Cloud is the managed SaaS product and Calico Enterprise is self-managed. The Cloud documentation also describes a Free Tier for single-cluster observability/policy management. Review current feature/retention/support terms; do not infer a universal 24/7 SLA, per-node price, identical dataplane feature set or internal SaaS dataflow from an unsourced comparison table.

## Large-Scale Cluster Design

Use measured endpoint count, policy complexity, update churn, client connections, CPU/RSS and convergence targets. A node-count table alone cannot establish production capacity.

### Operator Typha Scaling

The reviewed Tigera Operator **1.42.6** uses this calculation for its counted nodes:

```text
N <= 2: 1 replica
N <= 4: 2 replicas
otherwise: max(3, floor(N / 200) + 2)

100 nodes -> 3
500 nodes -> 4
1,000 nodes -> 7
2,000 nodes -> 12
5,000 nodes -> 27
```

This is the implementation's automatic replica target, not a benchmark proving “200 nodes per Typha.” Its node-count logic excludes explicitly unschedulable nodes and the relevant AKS virtual-node case; actual Linux placement/capacity must also accommodate the result.

Typha fans datastore updates out to Felix; it does not aggregate datastore writes or act as a cross-cluster federation controller. Preserve the operator's service account, RBAC, TLS mounts, placement and lifecycle behavior.

### Supported Overrides

The current `typhaDeployment` override does not expose `spec.replicas` or arbitrary container `env`. Do not replace the owned Deployment with the incomplete manual example merely to change the replica count. Use allowed override fields through the configuration owner:

```yaml
# Override shape only: these illustrative requests are not a capacity recommendation.
apiVersion: operator.tigera.io/v1
kind: Installation
metadata:
  name: default
spec:
  typhaDeployment:
    spec:
      template:
        spec:
          containers:
            - name: calico-typha
              resources:
                requests:
                  cpu: 500m
                  memory: 512Mi
```

Choose actual requests from observed usage and failure-domain capacity; the values above only demonstrate the field shape. Review limits, anti-affinity and topology constraints together, since an impossible placement rule can leave replicas Pending.

```bash
kubectl get installation.operator.tigera.io default -o yaml
kubectl -n calico-system get deployment calico-typha -o yaml
# Requires a working resource-metrics API:
kubectl -n calico-system top pods -l k8s-app=calico-typha
```

### Route Reflectors

![Route Reflector hierarchy for 1000+ nodes: three Tier 1 Route Reflectors peer with each other in an iBGP full mesh, and each reflects routes down to its own rack RR and worker node group instead of a full node-to-node mesh.](../../.gitbook/assets/en-networking-calico-07-advanced-topics-6.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-calico-07-advanced-topics-6.html)

> The drawing illustrates a hierarchy, not a complete resilient deployment: each rack has only one shown RR/uplink, and the labels are not a capacity guarantee. Cluster IDs and reflection relationships must match the intended hierarchy.

Follow the maintained [BGP transition procedure](04-bgp-deep-dive.md): prepare suitable RR nodes, use field-preserving node annotations, establish explicit sessions/routes, verify real traffic and only then remove the old mesh. The figure alone does not supply the required redundancy, next hops or policy.

### Felix Tuning Has Specific Effects

| Setting area | Meaning |
| --- | --- |
| Route/iptables refresh intervals | Re-check local dataplane state; not a generic Kubernetes API polling interval |
| `iptablesBackend: NFT` | Selects the iptables-nft frontend; not the same as Calico's native `Nftables` dataplane |
| Logging/flow logs | Observe the supported log pipeline and cost; do not add commercial-only file aggregation fields to OSS |
| Health timeouts | Control failure/readiness detection; longer values do not make programming faster |
| Marks, route-table ranges, failsafes | Affect shared host networking/control reachability; not generic memory/CPU tuning knobs |
| eBPF/DSR | A separate dataplane/network-path change with platform prerequisites, not a capacity preset |

`datastoreType`, `typhaAddr` and `typhaK8sServiceName` are not fields to add to the reviewed FelixConfiguration API. Old `...Secs`/`...Millis` field names in the earlier recipe were also not current API fields. Read the current resource and reference before changing its owner-managed settings.

### Datastore Choice

Kubernetes datastore avoids operating a separate Calico etcd service and is required by the current eBPF dataplane. Direct etcd can be appropriate for supported non-Kubernetes or separately designed installations, but “over 5,000 nodes requires etcd” and “etcd is always faster” are not supported conclusions.

A ConfigMap named `etcd-config` does not tune an etcd process unless the deployment consumes it. It also cannot tune the managed control-plane datastore of a cloud service. Direct etcd requires its own topology, TLS/authentication, backup, recovery and capacity plan.

The etcd tuning guide relates heartbeat/election settings to network and disk latency. Do not transplant a quota/snapshot/timeout preset without measuring the actual cluster. Keep control-plane configuration separate from Calico dataplane refresh intervals.

## Validation before Scaling Changes

1. Establish current allocation, route, policy and client-connection baselines.
2. Change the intended setting through its owner and preserve unrelated fields.
3. Observe resource usage, reconciliation lag, readiness and real positive/negative traffic paths.
4. Test the planned component/node/failure-domain loss and a rollback.

The previous CPU/memory/node-count ranges were unvalidated planning guesses, not measured capacity results. No large-cluster, Windows, gateway or datastore deployment was executed during this review.

## References

- [Calico IPPool API](https://docs.tigera.io/calico/latest/reference/resources/ippool)
- [IPAMConfiguration API](https://docs.tigera.io/calico/latest/reference/resources/ipamconfig)
- [BlockAffinity API](https://docs.tigera.io/calico/latest/reference/resources/blockaffinity)
- [Released IPAM defaults and allocation logic](https://raw.githubusercontent.com/projectcalico/calico/v3.32.2/libcalico-go/lib/ipam/ipam.go)
- [Current AWS Hybrid Nodes CNI support](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-cni.html)
- [WireGuard protocol](https://www.wireguard.com/protocol/)
- [WireGuard keepalive semantics](https://www.wireguard.com/quickstart/)
- [Calico encryption](https://docs.tigera.io/calico/latest/network-policy/encrypt-cluster-pod-traffic)
- [Enterprise Egress Gateway on premises](https://docs.tigera.io/calico-enterprise/latest/networking/egress/egress-gateway-on-prem)
- [Enterprise Egress Gateway on AWS](https://docs.tigera.io/calico-enterprise/latest/networking/egress/egress-gateway-aws)
- [Enterprise federation scope](https://docs.tigera.io/calico-enterprise/latest/multicluster/federation/overview)
- [Federated Services Controller](https://docs.tigera.io/calico-enterprise/latest/multicluster/federation/services-controller)
- [Calico Windows requirements](https://docs.tigera.io/calico/latest/getting-started/kubernetes/windows-calico/requirements)
- [Calico Windows operator workflow](https://docs.tigera.io/calico/latest/getting-started/kubernetes/windows-calico/operator)
- [Calico Windows limitations](https://docs.tigera.io/calico/latest/getting-started/kubernetes/windows-calico/limitations)
- [Windows networking architecture](https://learn.microsoft.com/en-us/virtualization/windowscontainers/container-networking/architecture)
- [Kubernetes 1.36 Windows documentation source](https://raw.githubusercontent.com/kubernetes/website/release-1.36/content/en/docs/concepts/windows/intro.md)
- [Current Calico product overview](https://docs.tigera.io/calico-cloud/about)
- [Operator 1.42.6 scaling function](https://raw.githubusercontent.com/tigera/operator/v1.42.6/pkg/common/autoscale.go)
- [Operator 1.42.6 Typha autoscaler](https://raw.githubusercontent.com/tigera/operator/v1.42.6/pkg/controller/installation/typha_autoscaler.go)
- [Operator API](https://docs.tigera.io/calico/latest/reference/installation/api)
- [Felix API](https://docs.tigera.io/calico/latest/reference/resources/felixconfig)
- [Component metrics](https://docs.tigera.io/calico/latest/operations/monitor/monitor-component-metrics)
- [etcd tuning](https://etcd.io/docs/v3.6/tuning/)
- [etcd configuration](https://etcd.io/docs/v3.6/op-guide/configuration/)

## Quiz

[Advanced Topics Quiz](../../quizzes/networking/calico/07-advanced-topics-quiz.md)
