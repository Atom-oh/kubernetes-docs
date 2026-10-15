# Part 10: IPAM Deep Dive

> **Review baseline**: Cilium 1.20.2 (stable, 2026-09-16); Cilium CLI 0.20.1; Hubble CLI 1.20.2. Items marked **[1.21 pre-release]** come from v1.21.0-pre.3 and may change before GA.
> **Last Updated**: October 15, 2026

[Part 4](04-ipam-policy.md) introduced the IPAM modes and their Helm fragments. This chapter goes underneath: who owns which address, what happens between `cilium-cni ADD` and a running endpoint, how to size a pool before you install, how the ENI allocator decides to call EC2, and how LB IPAM and Node IPAM differ from Pod IPAM. It is the companion to [Overlay and Native Routing](09-overlay-native-routing.md) (how the addresses are routed) and [BGP, Load Balancing, Egress and Edge](11-bgp-lb-egress-edge.md) (how LB addresses are advertised).

## What IPAM Is, and What It Is Not

Four different address families get allocated in a Kubernetes cluster by four different owners. Mixing them up is the most common source of "IPAM" bugs.

| Address | Owner | Cilium involvement |
|---|---|---|
| Pod (endpoint) IPs | Cilium IPAM (this chapter, the mode subsections) | Allocates, tracks and releases |
| Service ClusterIPs | kube-apiserver (`--service-cluster-ip-range`) | None; Cilium only programs them into the datapath |
| LoadBalancer Service IPs | LB IPAM (`CiliumLoadBalancerIPPool`) or a cloud controller | Operator-side allocation only; advertisement is separate (BGP Control Plane or L2 Announcements) |
| Node-as-load-balancer addresses | Node IPAM (`loadBalancerClass: io.cilium/node`) | Operator copies node addresses into the Service status |

`CiliumPodIPPool` never allocates ClusterIPs, and `CiliumLoadBalancerIPPool` never allocates Pod IPs. `CiliumCIDRGroup` (see CiliumCIDRGroup below) allocates nothing: it is a named set of CIDRs for policy.

## The Big Picture: the CiliumNode Handshake

Almost every mode is a conversation between two components through the `CiliumNode` custom resource (one per node, named like the node):

```
                        +-----------------------------+
                        |        CiliumNode <node>    |
                        |  spec.ipam.podCIDRs         |  cluster-pool
                        |  spec.ipam.pools.requested  |  multi-pool / eni (agent writes)
                        |  spec.ipam.pools.allocated  |  multi-pool / eni (operator writes)
                        |  spec.ipam.pool             |  crd (external allocator writes)
                        |  status.ipam.*              |  used IPs, operator-status.error
                        |  status.eni.enis            |  eni (operator writes)
                        +--------------+--------------+
                 watch/update          |          watch/update
        +------------------------+     |     +--------------------------+
        |  cilium-agent (node)   |<----+---->|  cilium-operator         |
        |  local pod-IP allocator|           |  node CIDRs, EC2/Azure   |
        |  CNI /ipam REST        |           |  API calls, pool alloc   |
        +------------------------+           +--------------------------+
```

The agent allocates individual Pod IPs out of whatever the node currently owns. The operator (or Kubernetes, or an external system, depending on the mode) decides what the node owns. The agent creates its own `CiliumNode` in `cluster-pool`, `multi-pool` and `eni` modes (agent option `auto-create-cilium-node-resource`, default true). The operator ignores any `CiliumNode` annotated `ipam.cilium.io/ignore: "true"`, which is the escape hatch for nodes managed by something else.

### Agent allocator wiring per mode (1.20.2)

| `ipam.mode` | Node capacity comes from | Agent-side allocator |
|---|---|---|
| `kubernetes` | `Node.spec.podCIDRs` (or annotations) | host-scope allocator over the node CIDR |
| `cluster-pool` (default) | operator, via `CiliumNode.spec.ipam.podCIDRs` | host-scope allocator over the node CIDR |
| `multi-pool` | operator, via `spec.ipam.pools.allocated` | multi-pool manager |
| `eni` | operator (EC2 API), via `status.eni.enis` converted to `spec.ipam.pools.allocated` | **ENI multi-pool allocator (new in 1.20)** |
| `crd`, `azure`, `alibabacloud` | `CiliumNode.spec.ipam.pool` | CRD allocator |
| `delegated-plugin` | another CNI IPAM plugin | no-op allocator |

Helm interactions to remember: `eni.enabled=true` forces `ipam: eni` regardless of `ipam.mode`; `ipam.mode=eni` without `eni.enabled` fails chart validation. There is no `gke` value: self-managed GKE uses `kubernetes`.

### Node-local addresses

Cilium takes addresses out of each node's range for itself: the `cilium_host` router IP, the health endpoint IP and (when Ingress is enabled) the ingress IP. In `cilium-dbg status --all-addresses` they appear as `(router)`, `(health)` and `(ingress)`. The host-scope allocator also excludes the first (network) and last (broadcast) address of the node CIDR. Capacity math (see Sizing math) must subtract these.

## Pod IP Lifecycle

The path from the kubelet to a running endpoint, for every mode except `delegated-plugin`:

```
kubelet -> CRI -> cilium-cni ADD
                     |
                     | 1. remove stale host-side interface name, if any
                     | 2. POST /ipam   (unix socket to cilium-agent)
                     |       owner = <namespace>/<pod>, expiration = true
                     v
                 cilium-agent: IpamPostIpamHandler
                     | 3. empty pool?  -> pick pool (annotations/selectors, multi-pool)
                     | 4. AllocateNextWithExpiration
                     |       -> response: IPv4/IPv6, pool, cidrs, gateway,
                     |          master-mac, interface-number, skip-masquerade,
                     |          expiration-uuid, host-addressing (router IP)
                     |       -> start 10 minute expiration timer
                     v
                 cilium-cni: create veth (or netkit), set IPs/routes in the pod netns
                     | 5. PUT /endpoint/{id}
                     v
                 cilium-agent: build endpoint, identity, datapath
                     | 6. endpoint creation stops the expiration timer
                     v
                 pod Running

 failure at any point after step 4 -> deferred DELETE /ipam/{ip}?pool=<pool>
 CNI DEL -> endpoint delete -> agent releases the IP (metric ipam_events_total{action="release"})
```

Key mechanics, each verified in the 1.20.2 source:

- **The REST calls** are `POST /ipam`, `POST /ipam/{ip}` and `DELETE /ipam/{ip}` on the agent API (`api/v1/openapi.yaml`). The CNI plugin calls `IPAMAllocate("", podName, "", true)`; the last argument is the expiration flag.
- **Expiration timer**: an IP allocated with expiration is auto-released after `defaults.IPAMExpiration`, 10 minutes, unless endpoint creation stops the timer. This closes the window where the CNI plugin crashes after allocating but before creating the endpoint, which would otherwise leak the address until the agent restarts.
- **Restore**: when the agent restarts, it re-claims the IPs of running endpoints (shown as `[restored]` in `cilium-dbg status --all-addresses`). The option `--bypass-ip-availability-upon-restore` exists only for ENI/Azure upgrade cases.
- **ENI-class modes** (`eni`, `azure`, `alibabacloud`): the response also carries the ENI MAC, gateway and CIDRs. The plugin sets the parent interface index from the MAC (ENI only) and the agent installs per-endpoint routing rules on the host. This is why those modes force endpoint routes.
- **`delegated-plugin`**: the CNI plugin itself runs `DelegateAdd` against the configured IPAM binary (for example Azure's `azure-ipam` on AKS) and marks the endpoint `ExternalIpam`, so the agent never frees that IP; the plugin calls `DelegateDel` on DEL. Cilium does no Pod IP accounting here.

Inspection:

```bash
# All addresses the agent knows, with owners (ns/pod); multi-pool shows pool/ip
kubectl -n kube-system exec ds/cilium -c cilium-agent -- cilium-dbg status --all-addresses

# Allocation summary line, for example "IPAM: IPv4: N/M allocated from <cidr>"
kubectl -n kube-system exec ds/cilium -c cilium-agent -- cilium-dbg status | grep -i ipam
```

A Pod stuck in `ContainerCreating` with the CNI error `unable to allocate IP via local cilium agent` means step 2-4 failed; the Troubleshooting section maps that to a root cause per mode.

## Mode Catalog and Decision Matrix

### Feature comparison

Adapted from the upstream IPAM concepts page for 1.20.2.

| Feature | Kubernetes host scope | Cluster scope (default) | Multi-pool | CRD-backed | AWS ENI | Azure IPAM | GKE (via host scope) |
|---|---|---|---|---|---|---|---|
| Tunnel routing | yes | yes | yes | no | no | no | no |
| Direct routing | yes | yes | yes | yes | yes | yes | yes |
| CIDR configuration | Kubernetes | Cilium | Cilium | external | AWS | Azure | GCP |
| Multiple CIDRs per cluster | no | yes | yes | n/a | n/a | n/a | n/a |
| Multiple CIDRs per node | no | no | yes | n/a | n/a | n/a | n/a |
| Dynamic CIDR/IP allocation | no | no | yes | yes | yes | yes | no |

Maturity: cluster-pool, kubernetes, crd and eni are stable. Multi-pool carried a "Beta" banner in 1.18 and the banner is gone from 1.19 onward (this chapter treats it as stable from 1.19; upstream does not use the word "GA"). ENI IPv6 is **beta** in 1.20. Cluster-pool to multi-pool online migration is new in 1.20.

### Decision matrix

This is guidance synthesized from the upstream documentation and the constraints of each platform, not an upstream table.

| Environment | Recommended IPAM | Why and what to watch |
|---|---|---|
| EKS, VPC-routable Pod IPs wanted (security-group targets, ALB/NLB IP targets, no SNAT) | `eni`, plus prefix delegation on Nitro | Needs operator IAM permissions, native routing, `aws-node` removed. Density is bounded by instance ENI/IP limits unless prefix delegation is used. IPv6 is beta. Not applicable to Fargate or EKS Auto Mode nodes |
| EKS, scarce VPC IPs or high density | `cluster-pool` with VXLAN (Helm default) or `multi-pool` | Pods SNAT to the node IP; the EKS control plane cannot reach Pod IPs, so admission webhooks must run on the host network or be reached via a Service |
| EKS Hybrid Nodes (on-prem nodes) | `cluster-pool` with VXLAN; pool list = the EKS "remote pod networks"; mask sized by Pods per node | AWS-supported configuration is IPv4 only, VXLAN, cluster-scope IPAM, BGP Control Plane. Do not change the pool list or mask after deploy. `eni` can never apply on-prem |
| On-prem, simple | `cluster-pool` with tunnel | Operator-managed, no dependency on kube-controller-manager node CIDRs |
| On-prem, routable Pods, several ranges per site or tenant | `multi-pool` + BGP `CiliumPodIPPool` advertisements, per-site default pool via `CiliumNodeConfig` | Needs `kubeProxyReplacement=true` and `bpf.masquerade=true`; pool CIDRs must not overlap |
| Cluster whose control plane already assigns node CIDRs (kubeadm with `--allocate-node-cidrs`, GKE) | `kubernetes` | Static, one CIDR per family per node |
| Addresses come from an external system | `crd` | Single IPs only, direct routing only |
| AKS | Azure CNI Powered by Cilium (`delegated-plugin`) or BYOCNI with any Cilium IPAM | Do not apply the upstream `azure` IPAM on AKS |
| Self-managed Azure VMs | `azure` | Resource-group and identity flags; reworked in 1.21 pre-release |

### Changing modes on a live cluster

Upstream's position: do not change the IPAM mode of a running cluster except through a documented migration, and "the safest path is a fresh cluster". The only documented online path is **cluster-pool to multi-pool** (see the migration subsection). Everything else (kubernetes to cluster-pool, anything to ENI, overlay to ENI) means a new cluster or a blue/green node group, because Pod IP ranges, routing and (on EKS) webhook reachability all change. Using `CiliumNodeConfig` to mix IPAM modes per node group is not documented upstream and this chapter does not recommend it.

## Kubernetes Host Scope and Cluster Scope

### Kubernetes host scope (`ipam.mode=kubernetes`)

At startup the agent waits for the node's PodCIDR for each enabled family, from `Node.spec.podCIDRs` / `spec.podCIDR` or the annotations `network.cilium.io/ipv4-pod-cidr` and `network.cilium.io/ipv6-pod-cidr` (plus `ipv4/6-cilium-host`, `ipv4/6-health-ip` and `ipv4/6-Ingress-ip`). `kube-controller-manager` must run with `--allocate-node-cidrs` (and `--cluster-cidr`, `--node-cidr-mask-size`).

```yaml
ipam:
  mode: kubernetes
k8s:
  requireIPv4PodCIDR: true     # only effective with ipam.mode=kubernetes
  requireIPv6PodCIDR: false
```

The agent auto-enables `k8s-require-ipv4-pod-cidr` when IPv4 is enabled in this mode, so the explicit setting is mostly documentation. Limits: one CIDR per node per family, fixed at node registration, no dynamic growth. Self-managed GKE uses this mode with `ipv4NativeRoutingCIDR` set to the cluster CIDR.

### Cluster scope / cluster-pool (default)

The operator owns node prefix allocation. Each node gets a CIDR written to `CiliumNode.spec.ipam.podCIDRs`; the agent blocks at startup until that field is populated for every enabled family, then runs the same host-scope allocator over it. The operator re-adopts existing allocations after a restart; a conflict produces `node has CIDRs allocated (...) that conflict with requested CIDRs`.

Helm values (1.20.2 defaults):

```yaml
ipam:
  mode: cluster-pool
  operator:
    clusterPoolIPv4PodCIDRList: ["10.0.0.0/8"]   # default
    clusterPoolIPv4MaskSize: 24                  # default
    clusterPoolIPv6PodCIDRList: ["fd00::/104"]   # default
    clusterPoolIPv6MaskSize: 120                 # Helm default (operator flag default is 112)
```

The rendered ConfigMap keys are `cluster-pool-ipv4-cidr` (space-joined list), `cluster-pool-ipv4-mask-size`, `cluster-pool-ipv6-cidr` and `cluster-pool-ipv6-mask-size`. The operator refuses to start when IPv4 is enabled with an empty list ("cluster-pool-ipv4-cidr must be provided when using ClusterPool") or when a list is set for a disabled family.

### Sizing math

The node CIDR allocator is `pkg/ipam/cidrset`. For each pool CIDR with prefix length `P` and node mask `M`:

```
nodes per pool CIDR      = 2^(M - P)
addresses per node       = 2^(32 - M)          (IPv4)     2^(128 - M) (IPv6)
usable Pod IPs per node  = addresses - 2 (network, broadcast) - up to 3 (router, health, ingress)
```

Constraints from the source: for IPv6, `M - P` must not exceed 16 (`clusterSubnetMaxDiff = 16`, error `ErrCIDRSetSubNetTooBig`) because the allocator keeps an uncompressed bitmap; IPv4 only requires `M <= 32`. Upstream guidance: a node mask of `/30` is the minimum and `/29` or larger is recommended.

| Pool CIDR | Node mask | Nodes | Addresses per node | Note |
|---|---|---|---|---|
| `10.0.0.0/8` (default) | `/24` | 65,536 | 256 | `2^(24-8)`; usable about 251 |
| `10.244.0.0/16` | `/24` | 256 | 256 | typical small cluster |
| `10.244.0.0/16` | `/26` | 1,024 | 64 | `2^(26-16)`; usable about 59 |
| `10.244.0.0/16` | `/28` | 4,096 | 16 | lab sizing; about 11 usable |
| `fd00::/104` (default) | `/120` | 65,536 | 256 | IPv6 default, difference is exactly 16 |
| `fd00:10:244::/96` | `/112` | 65,536 | 65,536 | maximum allowed difference of 16 |

The first four rows are computed from the formula above; "usable" subtracts the two reserved addresses and the three Cilium-owned addresses, so treat it as an upper bound. Per-node Pod density also depends on `maxPods` in the kubelet: size the mask for `maxPods` plus headroom for rolling updates (old and new Pods overlap).

Mutation rules (upstream, enforced by behaviour rather than validation):

- Never edit or remove an existing entry in `clusterPoolIPv4PodCIDRList`. Append a new CIDR to grow.
- `clusterPoolIPv4MaskSize` cannot change on a live cluster.
- Errors from the allocator (`allocator full`) appear at `CiliumNode.status.ipam.operator-status.error`.

```bash
kubectl get ciliumnodes -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.ipam.podCIDRs}{"\t"}{.status.ipam.operator-status}{"\n"}{end}'
```

Overlap hazard: the default `10.0.0.0/8` overlaps most corporate and VPC ranges. If it overlaps the node network you lose node connectivity. Always set the list explicitly.

**`nativeRoutingCIDRFromClusterPool`** (Helm, default false; new in 1.20: absent from the 1.18.14 and 1.19.8 `values.yaml`, present in 1.20.2 and 1.21): derives the native-routing CIDR from the pool, valid only with cluster-pool and exactly one CIDR per enabled family, otherwise the template fails.

### Dual-stack

```yaml
ipam:
  mode: cluster-pool
  operator:
    clusterPoolIPv4PodCIDRList: ["10.244.0.0/16"]
    clusterPoolIPv4MaskSize: 24
    clusterPoolIPv6PodCIDRList: ["fd00:10:244::/96"]
    clusterPoolIPv6MaskSize: 112       # 112 - 96 = 16, the maximum allowed
ipv4: { enabled: true }
ipv6: { enabled: true }
```

Setting `ipv6.enabled` does not create an IPv6 Service CIDR or underlay IPv6 connectivity. Per mode: host scope needs both `podCIDRs` entries and `k8s.requireIPv6PodCIDR`; multi-pool pools may carry `ipv4`, `ipv6` or both, and the family-specific annotations `ipam.cilium.io/ipv4-pool` and `ipam.cilium.io/ipv6-pool` exist for this; ENI IPv6 is beta (see Release, use-primary-address, IPv6); LB IPAM follows the Service's `ipFamilyPolicy` (see LB IPAM below). The AWS-supported EKS Hybrid Nodes configuration is IPv4 only.

## Multi-Pool IPAM

### Concept

Multi-pool replaces "one CIDR list for the whole cluster" with named **pools**, each a `CiliumPodIPPool`. A node can hold blocks from several pools at once, requested on demand by the agent. Use it for tenants with separate ranges, for routable subsets of Pods (BGP advertisement per pool), for per-site ranges, and for source-IP-preserving pools.

### Prerequisites and install

The upstream tutorial requires `kubeProxyReplacement=true` and `bpf.masquerade=true`. Known limitation: iptables-based masquerading needs `egressMasqueradeInterfaces` (upstream issue 22273), so eBPF masquerade is the supported path. Pool CIDRs must not overlap one another (the IP cache maps a prefix to one identity).

```yaml
ipam:
  mode: multi-pool
  multiPoolPreAllocation: "default=8,mars=4"
  operator:
    autoCreateCiliumPodIPPools:
      default:
        ipv4: { cidrs: ["10.10.0.0/16"], maskSize: 27 }
      mars:
        ipv4: { cidrs: ["10.20.0.0/16"], maskSize: 27 }
kubeProxyReplacement: true
bpf: { masquerade: true }
```

`autoCreateCiliumPodIPPools` only creates pools that do not exist; it never updates them. It maps to the operator flag `--auto-create-cilium-pod-ip-pools <pool>=ipv4-cidrs:...;ipv4-mask-size:...[;allow-first-ip:...][;allow-last-ip:...]`, whose grammar cannot express `podSelector`, `namespaceSelector` or (1.21) `pool[].reservedRanges`. Create those pools as custom resources.

### CiliumPodIPPool

```yaml
apiVersion: cilium.io/v2alpha1      # 1.20.x; use cilium.io/v2 from 1.21 [1.21 pre-release]
kind: CiliumPodIPPool
metadata:
  name: mars
spec:
  # allowFirstIP / allowLastIP are fields of spec (not of spec.ipv4); default false,
  # ignored for /31 /32 /127 /128
  ipv4:
    cidrs: ["10.20.0.0/16"]
    maskSize: 27
  podSelector:
    matchLabels:
      io.kubernetes.pod.namespace: tenant-mars   # synthetic label
  namespaceSelector:
    matchLabels:
      tenant: mars
```

Cluster-scoped, short name `cpip`. `maskSize`, `allowFirstIP` and `allowLastIP` are immutable (CEL `self == oldSelf`). The first and last address of each *allocated per-node block* are reserved unless `allowFirstIP` / `allowLastIP` are set. A pool with no block for a family is skipped for that family.

**API version note.** 1.20.2 serves `cilium.io/v2alpha1`. **[1.21 pre-release]** `cilium.io/v2` becomes the storage version and `v2alpha1` is deprecated; v2 also caps `cidrs` at 32 items and adds `spec.ipv4.pool[]` / `spec.ipv6.pool[]` (see Updating pools safely). Update manifests and tooling to v2 when you move to 1.21.

### Pool selection

Evaluated once, at Pod creation (changing an annotation on a running Pod has no effect). Precedence, from the source (`pkg/ipam/metadata/manager.go`) and docs:

1. **Pod annotation**: `ipam.cilium.io/ipv4-pool` / `ipam.cilium.io/ipv6-pool` (per family) take precedence over `ipam.cilium.io/ip-pool`.
2. **Namespace annotation**: the same keys on the Pod's namespace.
3. **`CiliumPodIPPool` selectors**: `podSelector` and `namespaceSelector` (both must match when both are set). Exactly one pool per family must match, otherwise allocation **fails** with an error and an event.
4. **Default pool**: `ipam-default-ip-pool` (default `default`), unless the Pod or namespace carries `ipam.cilium.io/require-pool-match: "true"`, in which case allocation is blocked.

The correct annotation key is `ipam.cilium.io/ip-pool` (`pkg/annotation/k8s.go`). Some upstream tutorial text writes `ipam.cilium.io/ipam-pool`; that key does nothing.

```bash
kubectl annotate namespace tenant-mars ipam.cilium.io/ip-pool=mars
```

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: pinned
  annotations:
    ipam.cilium.io/ip-pool: mars
spec:
  containers:
  - name: app
    image: registry.k8s.io/pause:3.10
```

### How the agent asks for capacity

The agent writes demand into `CiliumNode.spec.ipam.pools.requested[] {pool, needed{ipv4-addrs, ipv6-addrs}}`. The operator carves per-node blocks of the pool's `maskSize` until the node's available addresses meet `needed`, and appends them to `spec.ipam.pools.allocated[] {pool, cidrs[], allowFirstIP, allowLastIP}`. The agent removes blocks that are completely free and above demand. Errors go to `status.ipam.operator-status.error`.

The documented formula is `neededIPs = roundUp(inUse + pending + preAlloc, preAlloc)`. The code (`neededIPCeil` in `pkg/ipam/multipool_manager.go`) rounds to the next-but-one multiple, so with `preAlloc = P` a demand of 0 requests `P`, 1 through `P` requests `2P`, `P+1` requests `3P`. The effect is a buffer of at least one pre-allocation unit. The agent flag is `--ipam-multi-pool-pre-allocation` (Helm `ipam.multiPoolPreAllocation`); empty means `default=8` and other pools default to 0. The count applies per enabled family.

Because blocks are allocated at `maskSize` granularity, choose `maskSize` so a block is a few times larger than `preAlloc` (for example `/27` = 32 addresses with `preAlloc=8`), or nodes will repeatedly acquire and release many tiny blocks.

### Per-node default pool, masquerade, routing

**Per-node default pool** with `CiliumNodeConfig` (`cilium.io/v2`, namespace `kube-system`). Changes apply only after the agent Pod restarts.

```yaml
apiVersion: cilium.io/v2
kind: CiliumNodeConfig
metadata:
  name: ip-pool-dc1
  namespace: kube-system
spec:
  defaults:
    ipam-default-ip-pool: dc1-pool
  nodeSelector:
    matchLabels:
      topology.kubernetes.io/zone: dc1
```

Do not use this override on the pool named for a cluster-pool migration (see the cluster-pool to multi-pool migration subsection).

**Masquerade.** The agent option `--only-masquerade-default-pool` (requires eBPF masquerade) or the per-pool annotation `ipam.cilium.io/skip-masquerade="true"` on the `CiliumPodIPPool` preserves the Pod source IP for non-default pools; it affects new Pods. There is no dedicated Helm key for the agent option; use `extraConfig.only-masquerade-default-pool: "true"` (this exact path was not run in this review).

**Routing.** Pool CIDRs can be announced with the BGP Control Plane (`advertisementType: CiliumPodIPPool`, see [Part 11](11-bgp-lb-egress-edge.md)) or reached through `autoDirectNodeRoutes` on a shared L2 segment.

### Updating pools safely, and `reservedRanges` [1.21 pre-release]

Rules: new pools and extra CIDRs may be added live; a CIDR in use by a node must not be removed; an in-use pool must not be deleted (the operator logs `CIDR from pool still in use by node`). The 1.20 procedure to swap a CIDR is: edit the pool, restart the operator, then for each node group cordon, drain, delete its `CiliumNode` objects, restart agents and uncordon, one group at a time.

**[1.21 pre-release]** `cilium.io/v2` adds per-CIDR configuration with `reservedRanges`, so you can retire a CIDR without orphaning allocations:

```yaml
apiVersion: cilium.io/v2
kind: CiliumPodIPPool
metadata:
  name: default
spec:
  ipv4:
    cidrs: ["10.10.0.0/16", "10.20.0.0/16"]
    maskSize: 24
    pool:
    - cidr: 10.10.0.0/16
      reservedRanges:
      - start: 10.10.0.0
        end: 10.10.255.255
```

Existing node blocks from `10.10.0.0/16` keep working; new blocks come only from `10.20.0.0/16`. After every node group has migrated, remove the old CIDR from `cidrs` and the matching `pool` entry. Each `pool[].cidr` must be one of `cidrs` (CEL-validated).

### Cluster-pool to multi-pool online migration (1.20+)

Absent in 1.19 and earlier. Operator options: `enable-cluster-pool-to-multi-pool-migration` (default false), `multi-pool-migration-workers` (default 16), `ipam-default-ip-pool`.

Preconditions: the migration is one-way (no rollback); every existing Pod lands in the **default pool**; the default pool must exist before the operator restarts (a custom resource or `autoCreateCiliumPodIPPools`), must cover all allocated per-node CIDRs and use the same mask size; do not override the default pool name per node.

```bash
helm upgrade cilium cilium/cilium --version 1.20.2 -n kube-system --reuse-values \
  --set ipam.mode=multi-pool \
  --set ipam.operator.autoCreateCiliumPodIPPools.default.ipv4.cidrs='{10.0.0.0/8}' \
  --set ipam.operator.autoCreateCiliumPodIPPools.default.ipv4.maskSize=24 \
  --set-string extraConfig.enable-cluster-pool-to-multi-pool-migration=true \
  --set operator.rollOutPods=true \
  --set rollOutCiliumPods=false
```

Then: wait until each `CiliumNode` lists its existing PodCIDR under `spec.ipam.pools.allocated`; if the BGP Control Plane advertises PodCIDRs, change the `CiliumBGPAdvertisement` from `advertisementType: PodCIDR` to `CiliumPodIPPool` selecting the default pool **before** restarting agents (expect a transient route withdrawal, because agents still in cluster-pool mode stop advertising migrated allocations); then restart agents, all at once or incrementally. Mixed cluster-pool and multi-pool agents keep connectivity during the rollout. Do not schedule non-default-pool Pods until every agent has restarted.

### Limits and the BGP interplay

No overlapping CIDRs between pools; iptables masquerade is not supported without `egressMasqueradeInterfaces`; for disjoint pools consider `ip-masq-agent`. Pool CIDR changes to in-use ranges require the drain procedure above.

## CRD-Backed IPAM (`ipam.mode=crd`)

The agent watches the `CiliumNode` with its node name. `spec.ipam.pool` is a map `ip -> {owner, resource}` of available **single IPs** (CIDRs are not supported); used IPs are reported in `status.ipam.used`, with a status update at most once per 15 seconds (Helm `ipam.ciliumNodeUpdateRate`). IPv6 uses `spec.ipam.ipv6-pool` and `status.ipam.ipv6-used`. Direct routing only.

At startup the agent logs `Waiting for initial IP to become available in '<node>' custom resource` and needs at least one IP (at least two when health checking is on). RBAC needs full access to `ciliumnodes` and `ciliumnodes/status`. Upstream prose still says `available`/`inuse`; the schema is `pool`/`used`, so follow the installed CRD.

## AWS ENI IPAM

### Architecture (1.20.2)

The operator is the only component that calls the EC2 API. It writes the ENI inventory to `CiliumNode.status.eni.enis`. The agent converts that inventory into CIDRs in `spec.ipam.pools.allocated` for pool `default`: a secondary IP becomes a `/32`, a delegated prefix becomes a `/28` (IPv4) or `/80` (IPv6). The agent allocates Pod IPs locally and reports demand in `spec.ipam.pools.requested`. In 1.20 ENI mode there is no `CiliumPodIPPool` and no `ip-pool` annotation. In 1.19 and 1.18, ENI used the CRD allocator instead (`spec.ipam.pool`, `status.ipam.used`). A 1.19 to 1.20 rolling upgrade is supported: the operator distinguishes new agents by `spec.ipam.pools.requested` and the absence of `status.ipam.used`.

ENI mode forces native routing and endpoint routes (`eni.enabled=true` already sets them, so `routingMode: native` and `endpointRoutes.enabled` in a values file are redundant) and the agent refuses ENI combined with tunnelling. `enableIPv4Masquerade` defaults to false in ENI mode since 1.18. **[1.21 pre-release]** `enableIPv6Masquerade` also defaults to false in ENI mode.

### Install and node preparation

Remove the VPC CNI (`aws-node`) by patching its DaemonSet with an impossible `nodeSelector` (upstream uses `io.cilium/aws-node-enabled=true`) and install with `eni.enabled=true`. Create node groups with the startup taint `node.cilium.io/agent-not-ready=true:NoExecute` so workloads wait for the agent. Disable NetworkManager / systemd-networkd management of `eth*` interfaces other than `eth0`, otherwise the OS can strip secondary IPs (relevant on Amazon Linux 2023). If you replace the VPC CNI, flush `AWS-SNAT-CHAIN-*` and `AWS-CONNMARK-CHAIN-*` iptables chains.

IAM privileges for the operator (all listed upstream; scope by resource tags where possible): `ec2:DeleteNetworkInterface`, `DescribeInstanceTypes`, `DescribeNetworkInterfaces`, `DescribeSubnets`, `DescribeVpcs`, `DescribeRouteTables` (required since 1.18), `DescribeSecurityGroups`, `CreateNetworkInterface`, `AttachNetworkInterface`, `ModifyNetworkInterfaceAttribute`, `AssignPrivateIpAddresses`, `CreateTags`; plus `DescribeTags` (ENI garbage collection, on by default), `UnassignPrivateIpAddresses` (release), `AssignIpv6Addresses` (IPv6), `DescribeInstances` (when `--instance-tags-filter` is used). **[1.21 pre-release]** optional `GetSecurityGroupsForVpc` (falls back with one warning), and `DescribeManagedPrefixLists` / `GetManagedPrefixListEntries`. Upstream documents only the assign/unassign private-IP actions for prefix operations; confirm the exact IAM actions against the AWS documentation before writing a least-privilege policy. Supply credentials via `eni.iamRole` (IRSA) or the `cilium-aws` secret.

### Helm values

```yaml
eni:
  enabled: true
  iamRole: arn:aws:iam::<account-id>:role/cilium-operator
  awsEnablePrefixDelegation: true
  awsReleaseExcessIPs: true
  eniTags:
    team: platform
  gcInterval: 5m                        # "0s" disables ENI garbage collection
  nodeSpec:                             # per-node settings, since 1.19
    firstInterfaceIndex: 1              # keep eth0 for node traffic
    subnetTags: ["pod-subnet=true"]
    securityGroupTags: ["cilium-pod-sg=true"]
    excludeInterfaceTags: ["no-cilium=true"]
    deleteOnTermination: true
ipam:
  nodeSpec:
    ipamMinAllocate: 16
    ipamPreAllocate: 8
  operator:
    externalAPILimitQPS: 8
    externalAPILimitBurstSize: 40
```

Tag-list entries render as comma-joined `key=value` strings in the ConfigMap (for example `eni-subnet-tags`). Two kinds of filter exist and they are not interchangeable: the operator-level `eni.subnetIDsFilter`, `eni.subnetTagsFilter` and `eni.instanceTagsFilter` restrict which instances/subnets the operator manages and assume each instance already has an ENI in a matching subnet at deploy time; to steer only the ENIs Cilium **creates**, use the per-node `eni.nodeSpec` values (or the `eni` section of a custom CNI configuration, which takes precedence over Helm for the same field). The operator API limiter defaults are 4 QPS with burst 20.

Operator flags worth knowing (cmdref `cilium-operator-aws`): `--aws-enable-prefix-delegation`, `--aws-release-excess-ips`, `--excess-ip-release-delay` (default 180 seconds), `--eni-gc-interval` (5 minutes), `--eni-tags`, `--parallel-alloc-workers` (50), `--limit-ipam-api-qps`, `--limit-ipam-api-burst`, `--aws-max-results-per-call`.

### Allocation algorithm

Per-node knobs (in `CiliumNode.spec.ipam`): `min-allocate`, `pre-allocate` (treated as 8 when 0), `max-allocate`, `max-above-watermark` (no agent flag or Helm key: set it on the `CiliumNode` or in the CNI configuration `ipam` section), `static-ip-tags`. Formulas from `operator/pkg/ipam/nodemanager/node.go`:

```
deficit (needed) = max( preAllocate + used - available ,  minAllocate - available )
                   clamped to maxAllocate if set;  floor 0
excess  (only with --aws-release-excess-ips)
                 = max( available - used - preAllocate - maxAboveWatermark , 0 )
                   (while used is small, keep available >= minAllocate + maxAboveWatermark)
per-cycle allocation on the chosen ENI
                 = min( AvailableOnSubnet,
                        min( AvailableOnENI, needed + maxAboveWatermark + surgeAllocate ) )
   where surgeAllocate = pendingPods - needed
```

Worked example: `preAllocate=8`, `minAllocate=16`, a node with 10 available and 4 used: deficit = max(8 + 4 - 10, 16 - 10) = 6, so the operator assigns at least 6 more. Pre-allocate is lowered automatically on small instances to `min(8, (adapters - firstIndex) x (ipsPerENI - 1))`. The default `max-allocate` is the instance limit: `(adapters - firstInterfaceIndex) x (ipv4PerENI - 1)`, multiplied by 16 with prefix delegation. With `usePrimaryAddress` each ENI contributes one extra address.

Scheduling: deficit is evaluated on every `CiliumNode` update plus a full scan every minute; the work queue is processed on demand but at most once per second, largest deficit first, and allocation runs before release.

Where the IPs come from: the operator iterates attached ENIs with index >= `first-interface-index` that have free capacity and subnet addresses; if none, it creates an ENI. Subnet candidates are in the same VPC and AZ, narrowed by `subnet-ids` (takes priority) or `subnet-tags` (all must match), choosing the subnet with the most free addresses. With neither set it uses the node's primary-ENI subnet, then a subnet in the same route table, then the largest subnet in the VPC/AZ. Security groups: `spec.eni.security-groups`, else `security-group-tags`, else inherit eth0's groups. ENIs are described `Cilium-CNI (<instance-id>)` and tagged with the cluster tags plus `--eni-tags`. API calls: `CreateNetworkInterface`, `AttachNetworkInterface`, `ModifyNetworkInterfaceAttribute` (delete-on-termination, default true), `AssignPrivateIpAddresses`.

### Prefix delegation

`eni.awsEnablePrefixDelegation=true` (node opt-out: `eni.nodeSpec.disablePrefixDelegation`) makes the operator assign `/28` prefixes (16 addresses) instead of single secondary IPs, multiplying per-ENI capacity by 16. Constraints from the source:

- Effective only on **Nitro or bare-metal** instance types.
- No mixed mode: it is not used on a node that already holds secondary `/32` IPs on any ENI (the primary ENI IP is ignored for this check).
- Allocation uses `AssignENIPrefixes` with count `ceil(needed / 16)`. If the subnet returns `InsufficientPrefixesInSubnet`, the operator logs that it will not allocate prefixes on this node anymore and falls back to `/32` secondary IPs.
- The subnet needs contiguous free `/28` blocks; a fragmented subnet can run out of prefixes before it runs out of addresses (AWS-side behaviour; see the AWS prefix-delegation documentation).

### Release, use-primary-address, IPv6

**Release** (IPv4 only, requires `--aws-release-excess-ips=true`): the agent removes completely free CIDRs from `spec.ipam.pools.allocated`; the operator waits `--excess-ip-release-delay` (default 180 seconds), then calls `UnassignPrivateIpAddresses` (`/32`) or unassigns the prefix (`/28`). ENIs are **not** detached or deleted by release; stale ENIs are removed by ENI GC (tags `io.cilium/cilium-managed=true` and `io.cilium/cluster-name=<name>`). The 1.19-style `status.ipam.release-ips` handshake only applies to legacy CRD-allocator agents.

**`usePrimaryAddress`**: lets the ENI primary private IP be given to Pods (+1 per ENI). **[1.21 pre-release]** the operator flag `--aws-use-primary-address` is **removed**; set `eni.nodeSpec.usePrimaryAddress=true` (agent flag `--eni-use-primary-address`, stored in `CiliumNode.spec.eni.use-primary-address`). Helm users are unaffected because the chart only wired the agent side.

**IPv6 (beta in 1.20; the agent logs a beta warning)**: `ipam.mode=eni`, `eni.enabled=true`, `ipv6.enabled=true`. Each node gets exactly one delegated `/80` prefix, assigned at ENI creation or via `AssignIpv6Addresses` and never released; there are no watermarks; the subnet must be dual-stack, and IPv6-only subnets are unsupported because each ENI needs a primary IPv4 address. Upstream's EKS requirements page still says ENI is IPv4-only; the ENI page and the runtime beta warning are the more current source.

### ENI caveats

Pod density is bounded by `(ENIs - firstIndex) x (IPs per ENI - 1)` (x16 with prefixes). Pods share the node ENI security groups unless you configure `spec.eni.security-groups` per node group. Clusters using Cluster Mesh with cluster IDs 128-255 plus ENI hit a known policy-drop issue (see [Part 13](13-clustermesh-install-upgrade.md)). Removed in 1.20 (still present in 1.19): `CiliumNode.spec.eni.min-allocate`, `pre-allocate`, `max-above-watermark` and `instance-id`; the same values live under `spec.ipam`. Chaining on top of the VPC CNI is a different design and is not covered here.

## Azure, AKS and Alibaba Cloud

**AKS.** Azure CNI Powered by Cilium is managed: `ipam: delegated-plugin` with CNI configuration `"ipam": {"type": "azure-ipam"}` and `local-router-ipv4: 169.254.23.0`. Cilium assigns no Pod IPs. BYOCNI clusters can use any Cilium IPAM; Helm `azure.enabled` is incompatible with BYOCNI, use `aksbyocni.enabled`.

**Self-managed Azure (upstream `--ipam=azure`).** Operator flags `--azure-subscription-id`, `--azure-resource-group` (for VMSS, the resource group that contains the VMSS; a wrong group yields no addresses), `--azure-user-assigned-identity-id` (a client ID, not a resource ID) and `--azure-use-primary-address`; authentication is the DefaultAzureCredential chain. Per-node: `azure.nodeSpec.azureInterfaceName`. In 1.20 the operator publishes `status.azure.interfaces[]` with a new `subnet{id,cidr}` object (the flat `cidr` and `addresses[].subnet` are deprecated). **[1.21 pre-release]** Azure moves onto the shared cloud multi-pool framework (the same one as ENI): every `succeeded` address becomes a host prefix in the default pool, excess IPs are no longer released, and the agent waits up to 5 minutes for a valid IPv4 subnet CIDR, using it as the native-routing CIDR when `--ipv4-native-routing-cidr` is unset.

**Alibaba Cloud.** `ipam.mode=alibabacloud` with `alibabacloud.enabled` and per-node `alibabacloud.nodeSpec.{vSwitches,vSwitchTags,securityGroups,securityGroupTags}`; CRD allocator; the installation guide replaces Terway/Flannel and uses a `cilium-alibabacloud` secret. This chapter does not go beyond this; Alibaba limits and IPv6 behaviour were not examined.

## Beyond Pod IPs: LB IPAM, Node IPAM, CiliumCIDRGroup

### LB IPAM and `CiliumLoadBalancerIPPool`

LB IPAM allocates addresses for `type: LoadBalancer` Services. It runs in the operator (`operator/pkg/lbipam`), is always compiled in (Helm `enableLBIPAM`, default true) and stays dormant until the first pool exists. It **allocates only**: to make an address reachable you also need BGP Control Plane (`loadBalancerClass: io.cilium/bgp-control-plane`) or L2 Announcements (`io.cilium/l2-announcer`), covered in [Part 11](11-bgp-lb-egress-edge.md).

> **Security scope.** LB IPAM pools must be private ranges. LB IPAM VIPs are not reachable inside a VPC without BGP or routing integration, so on EKS use an internal AWS load balancer; the public path is always CloudFront to an internal ALB/NLB. LB IPAM fits on-prem and hybrid sites with BGP or L2 announcement. Upstream examples use public-looking ranges such as `20.0.0.0/8`; this chapter uses RFC 1918 ranges.

```yaml
apiVersion: cilium.io/v2
kind: CiliumLoadBalancerIPPool
metadata:
  name: blue-pool
spec:
  blocks:
  - cidr: 10.0.10.0/24
  - start: 10.0.20.100        # start and stop form ONE block; keep them in one list item
    stop: 10.0.20.200
  serviceSelector:
    matchLabels:
      color: blue
  allowFirstLastIPs: "No"     # default "Yes"; "No" reserves network/broadcast; cidr blocks only
  # disabled: true            # stop new allocations, keep existing ones
```

Facts: API `cilium.io/v2` (`v2alpha1` first marked deprecated in 1.19.8), cluster-scoped, short names `ippools`, `ippool`, `lbippool`, `lbippools`; print columns Disabled, Conflicting, IPs Available. `serviceSelector` accepts labels plus the synthetic labels `io.kubernetes.service.namespace` and `io.kubernetes.service.name`. Overlapping pools: the later one is marked Conflicting (condition `cilium.io/PoolConflict`) and allocates nothing. Pool conditions also include `cilium.io/IPsTotal`, `IPsAvailable`, `IPsUsed`. Editing a pool can reassign existing Service IPs (upstream issue 40358), so prefer adding a new pool or setting `disabled: true`.

Service handling: a `LoadBalancer` Service without a `loadBalancerClass` is served by LB IPAM unless Helm `defaultLBServiceIPAM` is `none` (values: `lbipam`, `nodeipam`, `none`); a Service with an unknown class is ignored. The Service condition `cilium.io/IPAMRequestSatisfied` reports reason `satisfied` or `no_pool`. Address families: single-stack by default (IPv4 when both are enabled), `PreferDualStack` tries both, `RequireDualStack` stays unsatisfied if a family is disabled.

Requesting specific addresses: annotation `lbipam.cilium.io/ips: "10.0.10.100,10.0.10.101"` (the legacy `.spec.loadBalancerIP` is deprecated). The pool's `serviceSelector` still applies, and you must not request the first or last address of a pool with `allowFirstLastIPs: "No"`.

Sharing an IP between Services:

```yaml
metadata:
  annotations:
    lbipam.cilium.io/sharing-key: "web-vip"
    lbipam.cilium.io/sharing-cross-namespace: "ns1,ns2"   # or "*"
```

In 1.20 two Services with the same sharing key share one IP when their ports/protocols do not conflict; conflicting ones receive different IPs from the same key's set. **[1.21 pre-release]** the compatibility check is stricter: Services must use the same `externalTrafficPolicy`, and with `Local` both must select the same Pods. The new annotation `lbipam.cilium.io/sharing-permit-different-pods: "true"` disables that safety check and is unsafe with Cilium BGP or L2 announcements (they are not L4 aware, so different nodes can answer for the same IP).

Metrics (documented with the prefix `cilium_`; the controller runs in the operator, whose registry may override the namespace, so the runtime prefix may be `cilium_operator_lbipam_*`. This was not verified at runtime: check your scrape for the actual names): `cilium_lbipam_conflicting_pools`, `cilium_lbipam_ips_available{pool}`, `cilium_lbipam_ips_used{pool}`, `cilium_lbipam_services_matching`, `cilium_lbipam_services_unsatisfied`.

Datapath note (1.19): north-south TCP/UDP to an LB IPAM or ClusterIP address is dropped when the port does not match a provisioned Service.

### Node IPAM

`nodeIPAM.enabled=true` (default false; sets `enable-node-ipam`) lets a Service with `loadBalancerClass: io.cilium/node` (or `defaultLBServiceIPAM: nodeipam`) publish node addresses as its load balancer ingress. After enabling on an existing install, restart the operator (`kubectl -n kube-system rollout restart deployment/cilium-operator`). The operator fills `status.loadBalancer.ingress` with each selected node's ExternalIP if present, else InternalIP, honouring `ipFamilies`. `externalTrafficPolicy: Cluster` uses all nodes; `Local` uses nodes hosting selected Pods (EndpointSlices required; not usable with Cilium Ingress/Gateway dummy endpoints). Nodes labelled `node.kubernetes.io/exclude-from-external-load-balancers` or tainted `ToBeDeletedByClusterAutoscaler` are excluded; the Service annotation `io.cilium.nodeipam/match-node-labels` restricts nodes by label.

Node IPAM publishes node addresses as service addresses. Use it only where node IPs are private; it is not a public-exposure mechanism on AWS.

### CiliumCIDRGroup

`CiliumCIDRGroup` is a named list of CIDRs (`spec.externalCIDRs`) that policies reference with `cidrGroupRef` or `cidrGroupSelector` instead of inlining CIDRs. A group gets one security identity regardless of size, which scales better for large lists, and Hubble annotates flows with the group name. It is cluster-scoped with short name `ccg`. Use `cilium.io/v2`; `v2alpha1` is deprecated (some upstream examples still show it).

```yaml
apiVersion: cilium.io/v2
kind: CiliumCIDRGroup
metadata:
  name: corp-ranges
  labels:
    tier: internal
spec:
  externalCIDRs:
  - 10.30.0.0/16
  - 192.168.100.0/24
---
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: egress-corp
spec:
  endpointSelector:
    matchLabels:
      app: batch
  egress:
  - toCIDRSet:
    - cidrGroupRef: corp-ranges
```

## Operations: Inspecting, Metrics, Upgrades

```bash
# per-node view of what each node owns
kubectl get ciliumnodes -o custom-columns=NAME:.metadata.name,CIDRS:.spec.ipam.podCIDRs
kubectl get ciliumnode <node> -o yaml        # .spec.ipam, .status.ipam, .status.eni.enis
kubectl get ciliumpodippools                 # multi-pool; short name cpip
kubectl get ippools                          # LB IPAM pools
kubectl -n kube-system logs deploy/cilium-operator | grep -i ipam
```

**Agent metrics:** `cilium_ipam_capacity{family,cidr}` (the `cidr` label is the node CIDR in cluster-pool and kubernetes modes, otherwise empty), `cilium_ipam_events_total{action,family}`, `cilium_ip_addresses{family}`.

**Operator metrics** (prefix `cilium_operator_`; enable with `operator.prometheus.enabled`): `ipam_available_ips{target_node}`, `ipam_used_ips`, `ipam_needed_ips`, `ipam_ip_allocation_ops{subnet_id}`, `ipam_ip_release_ops`, `ipam_interface_creation_ops`, `ipam_interface_candidates`, `ipam_empty_interface_slots`, `ipam_available_ips_per_subnet{subnet_id,availability_zone}`, `ipam_nodes{category=total|in-deficit|at-capacity}`, `ipam_resync_total`, `ipam_allocation_duration_seconds`, `ipam_release_duration_seconds`, `ipam_background_sync_duration_seconds`. The upstream metrics table is stale: it omits `interface_candidates`, `empty_interface_slots`, `available_ips_per_subnet` and `background_sync_duration_seconds`; the list above follows the source. Cloud API call metrics are not under `ipam_`: the subsystem is the cloud name, so on AWS they are `cilium_operator_ec2_api_duration_seconds{operation,response_code}` and `cilium_operator_ec2_api_rate_limit_duration_seconds{operation}` (Azure and Alibaba Cloud use their own subsystem). 1.20 removed `ipam_ips` and `ipam_available_interfaces`.

Suggested alerts: `ipam_nodes{category="at-capacity"} > 0`, a rising `ipam_nodes{category="in-deficit"}`, `ipam_available_ips_per_subnet` below a threshold per AZ, sustained `ec2_api_rate_limit_duration_seconds`, and `lbipam_conflicting_pools > 0`.

**Upgrade notes.** Rolling 1.19 to 1.20 is supported for ENI. **[1.21 pre-release]** the operator ClusterRole gains list/patch on `ciliumpodippools` (storage-version migration), and the `--aws-use-primary-address` operator flag is removed (see Release, use-primary-address, IPv6). If you pass it directly on the operator rather than through Helm, replace it with `eni.nodeSpec.usePrimaryAddress=true` before upgrading.

## Labs

> The labs were not executed against a live cluster in this review. They were checked against upstream source and documentation (see Validation Limits). Describe what you observe against the expected behaviour in words; do not expect identical formatting.

### Lab 1: Cluster-pool sizing and exhaustion (kind)

Prerequisites: kind with a two-worker cluster, Cilium installed from Helm with the default `cluster-pool`, kubectl, Helm.

1. Install with a deliberately small node mask:

   ```bash
   helm upgrade --install cilium cilium/cilium --version 1.20.2 -n kube-system \
     --set ipam.mode=cluster-pool \
     --set ipam.operator.clusterPoolIPv4PodCIDRList='{10.244.0.0/16}' \
     --set ipam.operator.clusterPoolIPv4MaskSize=28
   ```
2. Read each node's block: `kubectl get ciliumnodes -o custom-columns=NAME:.metadata.name,CIDRS:.spec.ipam.podCIDRs`. Each node owns a `/28` (16 addresses).
3. Pin a Deployment to one worker with a `nodeSelector` and scale it to 20 replicas.
4. Expected: the first Pods run; once the node's usable addresses (16 minus network, broadcast and the router/health/ingress addresses) are used, remaining Pods stay `ContainerCreating` with the CNI allocation error. `cilium-dbg status` shows the node range fully allocated.
5. Compute the expected limit with the Sizing math formula and compare to the observed count.

Cleanup: delete the Deployment. Rollback: the mask is immutable on a live cluster, so reinstall the cluster rather than editing the value.

### Lab 2: Multi-pool selection (kind)

Prerequisites: kind, Cilium 1.20.2 with `ipam.mode=multi-pool`, `kubeProxyReplacement=true`, `bpf.masquerade=true` and the `default` and `mars` pools from the multi-pool install values.

1. Create two namespaces. Annotate one: `kubectl annotate namespace ns-a ipam.cilium.io/ip-pool=mars`.
2. Run a Pod in each namespace and inspect `kubectl get pods -A -o wide`. Expected: the annotated namespace's Pod gets an address from `10.20.0.0/16`, the other from `10.10.0.0/16`.
3. Run a Pod in the unannotated namespace with the Pod annotation `ipam.cilium.io/ip-pool: mars`. Expected: the Pod annotation wins over the namespace default.
4. Annotate a third namespace `ipam.cilium.io/require-pool-match: "true"` without a matching pool and start a Pod. Expected: it stays pending with a pool-match error.
5. Inspect `kubectl get ciliumnode <n> -o yaml` and read `spec.ipam.pools.requested` and `allocated`; `cilium-dbg status --all-addresses` shows `pool/ip` entries.

Cleanup: delete the namespaces and, if desired, the cluster.

### Lab 3: Cluster-pool to multi-pool migration (kind)

Prerequisites: a kind cluster on 1.20.2 with cluster-pool and Pods running. This is one-way; use a disposable cluster.

1. Record `kubectl get ciliumnodes -o yaml | grep -A3 podCIDRs`.
2. Run the Helm upgrade from the cluster-pool to multi-pool migration subsection with a default pool that covers the recorded CIDRs and the same mask.
3. Wait for each node's PodCIDR to appear under `spec.ipam.pools.allocated`.
4. Restart agents (`kubectl -n kube-system rollout restart ds/cilium`). Expected: existing Pods keep their addresses and appear as restored; Pods can still reach each other across nodes during the rollout.

Rollback: not supported. Recreate the cluster.

### Lab 4: LB IPAM with L2 announcements (kind, private range)

Prerequisites: kind with `l2announcements.enabled=true` and `kubeProxyReplacement=true`; choose a free range inside the kind Docker network (private RFC 1918 space).

1. Apply a `CiliumLoadBalancerIPPool` with a small `start`/`stop` block and a `serviceSelector`.
2. Apply an L2 announcement policy (see Part 11) and a `LoadBalancer` Service whose labels match.
3. Expected: `kubectl get ippools` shows IPs available decreasing, the Service gets an external IP from the block, and the Service condition `cilium.io/IPAMRequestSatisfied` reports `satisfied`.
4. Create a second pool with an overlapping block. Expected: it is marked Conflicting and allocates nothing.
5. Set `disabled: true` on the first pool, create another Service. Expected: no new allocation from it while the existing Service keeps its IP.

Cleanup: delete the Services, pools and policy.

### Lab 5: EKS ENI mode with prefix delegation (sandbox account)

Prerequisites: a disposable EKS cluster in a private-subnet-only VPC, nodes on Nitro instance types, no public IPs on nodes, node security group admitting only the VPC/cluster security-group references (no `0.0.0.0/0` or `::/0`), operator IAM per the install and node preparation subsection, and the AWS CLI profile for the target sandbox account.

1. Create the node group with taint `node.cilium.io/agent-not-ready=true:NoExecute`. Disable the VPC CNI (do not install the managed add-on, or patch `aws-node` with the impossible node selector).
2. Install Cilium with `eni.enabled=true`, `eni.awsEnablePrefixDelegation=true`, `eni.awsReleaseExcessIPs=true`, `eni.iamRole` set, and the other values from the Helm values subsection.
3. Verify the inventory: `kubectl get ciliumnode <n> -o jsonpath='{.status.eni.enis}'` lists ENIs with prefixes; `aws ec2 describe-network-interfaces --filters Name=description,Values='Cilium-CNI*'` returns the same ENIs. Expected: `spec.ipam.pools.allocated` holds `/28` blocks.
4. Scale a Deployment past one `/28` (more than 16 Pods on a node). Expected: the operator allocates another prefix; `cilium_operator_ipam_available_ips` stays above `used + preAllocate`.
5. Scale back down and wait longer than 180 seconds. Expected: unused prefixes are released and the ENI remains attached.

Cleanup: scale to zero, uninstall Cilium, delete the node group and any leftover `Cilium-CNI` ENIs (ENI GC removes tagged orphans when enabled). Rollback: re-enable the VPC CNI add-on on a fresh node group; do not switch IPAM on the same live nodes.

### Lab 6: Node IPAM (kind)

Prerequisites: kind with Cilium and `nodeIPAM.enabled=true` (restart the operator after enabling).

1. Create a `LoadBalancer` Service with `loadBalancerClass: io.cilium/node`.
2. Expected: `status.loadBalancer.ingress` lists node InternalIPs (kind nodes have no ExternalIP).
3. Label one node `node.kubernetes.io/exclude-from-external-load-balancers`. Expected: that node's address drops out of the list.

Cleanup: delete the Service and label.

## Version Delta

| Topic | 1.18 | 1.19 | 1.20 | 1.21 pre-release |
|---|---|---|---|---|
| Multi-pool maturity | Beta banner | banner removed | stable | stable |
| Pool selection | `ip-pool` annotation only | + `ipv4-pool`/`ipv6-pool` annotations and `podSelector`/`namespaceSelector` (already in 1.18.14); `require-pool-match`, `skip-masquerade`, `--only-masquerade-default-pool` first appear in 1.19 | + `allowFirstIP`/`allowLastIP` | same + `pool[].reservedRanges` |
| `CiliumPodIPPool` API | v2alpha1 | v2alpha1 | v2alpha1 | v2 storage, v2alpha1 deprecated, `cidrs` max 32 |
| cluster-pool to multi-pool migration | no | no | new (`enable-cluster-pool-to-multi-pool-migration`) | same |
| ENI agent model | CRD allocator | CRD allocator | multi-pool allocator; IPv6 beta (`/80`); release via `pools.allocated` | cloud multi-pool framework shared with Azure |
| ENI per-node Helm (`eni.nodeSpec`, `ipam.nodeSpec`) | CNI conf only | added | same | same |
| ENI masquerade defaults | `enableIPv4Masquerade` false (new) | | | `enableIPv6Masquerade` false (new) |
| ENI IAM | + `DescribeRouteTables` | | | + optional `GetSecurityGroupsForVpc`, `DescribeManagedPrefixLists`, `GetManagedPrefixListEntries` |
| Operator `--aws-use-primary-address` | present | present | present | **removed** |
| `CiliumNode.spec.eni.{min,pre}-allocate`, `max-above-watermark`, `instance-id` | present | present | removed | removed |
| Operator IPAM metrics | per-node `available/used/needed_ips` and `interface_candidates` already present | same | `ipam_ips`, `ipam_available_interfaces` removed | |
| Azure IPAM | CRD allocator | CRD allocator | `status.azure.interfaces[].subnet` | multi-pool protocol; no excess release |
| `CiliumLoadBalancerIPPool` API | v2 | v2alpha1 deprecated | v2 | v2 |
| `CiliumCIDRGroup` API | v2alpha1 deprecated | v2 | v2 | v2 |
| LB IPAM sharing | key + cross-namespace | | port-conflict rule | stricter compatibility + `sharing-permit-different-pods` |

## Troubleshooting

Symptom: Pod stays `ContainerCreating`; `kubectl describe pod` shows `unable to allocate IP via local cilium agent`.

| Mode | Likely cause | Check | Fix |
|---|---|---|---|
| cluster-pool / kubernetes | node range full (`IPAM: IPv4: N/M allocated`) | `cilium-dbg status`, `--all-addresses` | reduce density, add nodes; mask is immutable, plan a new pool/cluster for a larger one |
| cluster-pool | pool exhausted | `status.ipam.operator-status.error` = `allocator full` | append a CIDR to the list (never edit entries) |
| cluster-pool | agent never starts | CiliumNode lacks `spec.ipam.podCIDRs` | check operator logs, overlapping CIDRs, conflict errors |
| kubernetes | no node PodCIDR | `kubectl get node -o jsonpath='{.spec.podCIDRs}'` | enable `--allocate-node-cidrs` |
| multi-pool | `needed` exceeds pool free space | `operator-status.error`: `failed to allocate ipv4 address for node ... from pool ...` | add CIDR to the pool or add a pool |
| multi-pool | pool not found or not yet synced | `kubectl get cpip`; errors `ErrPoolNotReadyYet`, `ErrManagerPoolsNotSynced` | create the pool before Pods; check the default pool exists |
| multi-pool | two pools match | error `multiple CiliumPodIPPools match pod` | tighten selectors |
| multi-pool | `require-pool-match` | annotation on Pod or namespace | add a matching pool or annotation |
| ENI | instance ENI/IP limit | `ipam_nodes{category="at-capacity"}` | larger instance, prefix delegation |
| ENI | subnet out of IPs | `ipam_available_ips_per_subnet` | add a subnet via tags/IDs; with PD check for fragmentation (fallback to `/32`) |
| ENI | EC2 throttling | `ec2_api_rate_limit_duration_seconds` | tune `externalAPILimitQPS` / `externalAPILimitBurstSize` |
| ENI | missing IAM action | operator log | add the action listed in the install and node preparation subsection |
| ENI | OS removed secondary IPs | NetworkManager / systemd-networkd logs | exclude `eth*` except `eth0` from management |
| any | CNI crash leaked an IP | IP absent from endpoints but held | wait for the 10 minute expiration; restart agent to reconcile |

For LB IPAM: Service has no external IP, check the pool's Conflicting flag, the `cilium.io/IPAMRequestSatisfied` condition, `serviceSelector` match, and that something (BGP or L2) advertises the address. Remember that IPAM modes are not toggles: a mismatch between the running mode and the Helm value after a change is the signal to stop and plan a migration, not to edit the ConfigMap.

## Validation Limits and Sources

The labs were not executed against a live cluster in this review. Commands, field names, defaults, formulas and flags were checked against the Cilium source and documentation at the cited tags. Items not verified: the IAM action names for prefix assignment and release (upstream lists only the private-IP actions); the Helm path for `only-masquerade-default-pool` (use `extraConfig`); Alibaba Cloud limits; and the 1.21 items, which come from the pre-release tag v1.21.0-pre.3. Version labels for Azure, `reservedRanges` and the cloud multi-pool framework may change before GA. The ENI examples target a private-subnet sandbox; no example here opens a security group to the internet, creates an internet-facing load balancer, or attaches a public IP to compute.

Sources (v1.20.2 unless noted):

- IPAM concepts: https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/concepts/ipam/index.rst
- Cluster scope: https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/concepts/ipam/cluster-pool.rst
- Multi-pool: https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/concepts/ipam/multi-pool.rst
- Cluster-pool to multi-pool migration: https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/concepts/ipam/cluster-pool-to-multi-pool.rst
- AWS ENI: https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/concepts/ipam/eni.rst
- LB IPAM: https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/lb-ipam.rst
- Node IPAM: https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/node-ipam.rst
- Annotations (`ip-pool` key): https://github.com/cilium/cilium/blob/v1.20.2/pkg/annotation/k8s.go
- Node CIDR allocator: https://github.com/cilium/cilium/blob/v1.20.2/pkg/ipam/cidrset/cidr_set.go
- Multi-pool manager: https://github.com/cilium/cilium/blob/v1.20.2/pkg/ipam/multipool_manager.go
- ENI node manager formulas: https://github.com/cilium/cilium/blob/v1.20.2/operator/pkg/ipam/nodemanager/node.go
- Metrics: https://github.com/cilium/cilium/blob/v1.20.2/Documentation/observability/metrics.rst
- [1.21 pre-release] multi-pool and `reservedRanges`: https://github.com/cilium/cilium/blob/v1.21.0-pre.3/Documentation/network/concepts/ipam/multi-pool.rst
- [1.21 pre-release] upgrade notes: https://github.com/cilium/cilium/blob/v1.21.0-pre.3/Documentation/operations/upgrade-next.inc
- [1.21 pre-release] LB IPAM sharing: https://github.com/cilium/cilium/blob/v1.21.0-pre.3/Documentation/network/lb-ipam.rst
- AWS, EKS Hybrid Nodes CNI: https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-cni.html

## Quiz

Test yourself with the [Part 10 quiz](../../quizzes/networking/cilium/10-ipam-deep-dive-quiz.md).
