# Part 11: BGP Control Plane, Load Balancer IPs and Egress

> **Review baseline**: Cilium 1.20.2 (stable, 2026-09-16); Cilium CLI 0.20.1; Hubble CLI 1.20.2. Items marked **[1.21 pre-release]** come from v1.21.0-pre.3 and may change before GA.
> **Last Updated**: October 15, 2026

This chapter covers everything that connects a Cilium cluster to the network **outside** the Pod network: advertising routes with the BGP Control Plane, allocating and announcing LoadBalancer IPs (LB IPAM, L2 announcements, Node IPAM), steering outbound traffic (Egress Gateway), intercepting traffic to node-local backends (Local Redirect Policy), preferring nearby backends (traffic distribution), and the L7 entry points (Ingress and Gateway API). It ends with two reference topologies: on-prem ToR switches with BGP, and EKS behind CloudFront.

Related chapters: [IPAM deep dive](10-ipam-deep-dive.md) (Pod IPAM, which decides what BGP can advertise), [overlay and native routing](09-overlay-native-routing.md), [eBPF datapath internals](08-ebpf-datapath-internals.md) (kube-proxy replacement, which the Service load balancing below relies on), [ClusterMesh and upgrade](13-clustermesh-install-upgrade.md).

## 1. Where north-south fits

Three separate jobs are often blurred together under "load balancer":

| Job | Question it answers | Cilium component |
|---|---|---|
| Address allocation | Which IP does this Service get? | LB IPAM (`CiliumLoadBalancerIPPool`), Node IPAM, cloud controller |
| Reachability | How does the outside network learn that IP lives on these nodes? | BGP Control Plane, L2 announcements, cloud load balancer |
| Load balancing | Once a packet reaches a node, which backend Pod gets it? | eBPF Service load balancing (kube-proxy replacement), Envoy for L7 |

The BGP Control Plane, L2 announcements and LB IPAM are therefore **independent** features that you combine. A common combination on-prem is `LB IPAM` (allocates the VIP) + `BGP Control Plane` (advertises it) + eBPF kube-proxy replacement (balances it). The `loadBalancerClass` on a Service decides which feature owns it (section 6).

**What BGP does not do.** The BGP Control Plane only *advertises* routes. It does not program the local datapath, and routes learned from peers are not installed into the kernel or eBPF maps. It cannot create intra-cluster reachability ([upstream overview](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/bgp-control-plane/bgp-control-plane.rst)). Pod-to-Pod routing between nodes is the job of overlay or native routing ([Part 9](09-overlay-native-routing.md)).

## 2. BGP Control Plane v2

**Maturity**: v2 (`cilium.io/v2` CRDs) is the only BGP Control Plane in 1.19, 1.20 and 1.21-pre. The v1 `CiliumBGPPeeringPolicy` was removed in 1.19 (section 2.9).

### 2.1 Architecture

```
                     user-authored (cluster-scoped, cilium.io/v2)
   +--------------------+   +-------------------+   +----------------------+
   | CiliumBGPCluster   |-->| CiliumBGPPeer     |   | CiliumBGPAdvertise-  |
   | Config             |   | Config            |<--| ment (matched by     |
   |  nodeSelector      |   |  timers, GR, MD5, |   |  LABEL from PeerCfg) |
   |  bgpInstances[]    |   |  families[]       |   +----------------------+
   |  peers[] -> ref    |   +-------------------+
   +---------+----------+
             | watched by cilium-operator
             v
   +--------------------+   (one per selected node, name == node name,
   | CiliumBGPNodeConfig|    read-only for users; status reports sessions)
   +---------+----------+   +--------------------------+
             | watched by   | CiliumBGPNodeConfig-     |  optional per-node
             | the node's   | Override (name == node)  |  routerID/ASN/source
             v agent        +--------------------------+
   +--------------------------------------------+
   | cilium-agent: BGP "router manager"         |
   |   one embedded GoBGP instance per bgpInstance
   |   inputs: NodeConfig, PeerConfig, Advert., |
   |   Secret, Services/EndpointSlices/backends,|
   |   CiliumNode PodCIDRs / CiliumPodIPPool    |
   +----------------------+---------------------+
                          | TCP/179 (agent dials out; active-only by default)
                          v
                    ToR / upstream router
```

Control flow (from [`pkg/bgp/README.md`](https://github.com/cilium/cilium/blob/v1.20.2/pkg/bgp/README.md)): the operator watches `CiliumBGPClusterConfig` and the `CiliumBGPPeerConfig`/`CiliumBGPAdvertisement` objects it references, and creates, updates or deletes one `CiliumBGPNodeConfig` per node that matches the cluster config's `nodeSelector`. Each agent watches only its own `CiliumBGPNodeConfig` plus the peer/advertisement configs, Secrets, Services and (for multi-pool) `CiliumPodIPPool`, and reconciles its GoBGP instances. The operator therefore must be running for config changes to propagate.

The speaker is GoBGP embedded in the agent. GoBGP is the only supported router implementation. The embedded library moved from `gobgp/v3` (1.19) to `gobgp/v4` (1.20.2 and 1.21.0-pre.3; `go.mod` of each tag). IPv4 and IPv6, single and dual stack are supported, but you can only advertise address families the agent itself is running.

### 2.2 Enabling

```yaml
bgpControlPlane:
  enabled: true              # default false
  statusReport:
    enabled: true            # default true; disable on very large clusters to cut API load
  routerIDAllocation:
    mode: default            # default | ip-pool
```

```bash
helm upgrade cilium cilium/cilium -n kube-system --reuse-values \
  --set bgpControlPlane.enabled=true
kubectl -n kube-system rollout restart ds/cilium deploy/cilium-operator
```

| Helm value | Agent/operator flag | Default | Meaning |
|---|---|---|---|
| `bgpControlPlane.enabled` | `--enable-bgp-control-plane` | `false` | Turns the feature on |
| `bgpControlPlane.secretsNamespace.name` / `.create` | `--bgp-secrets-namespace` | `kube-system` / `false` | Namespace where `authSecretRef` Secrets are read; the chart can create it |
| `bgpControlPlane.statusReport.enabled` | `--enable-bgp-control-plane-status-report` | `true` | Writes session state into `CiliumBGPNodeConfig.status`; disabling clears status |
| `bgpControlPlane.routerIDAllocation.mode` / `.ipPool` | `--bgp-router-id-allocation-mode` / `-ip-pool` | `default` / empty | Router-ID strategy (section 2.7) |
| `bgpControlPlane.legacyOriginAttribute.enabled` | `--enable-bgp-legacy-origin-attribute` | `false` | `LoadBalancerIP` routes carry ORIGIN `INCOMPLETE` (MetalLB compatible) instead of `IGP` |
| `enableNoServiceEndpointsRoutable` | `--enable-no-service-endpoints-routable` | `true` | Whether a Cluster-policy VIP with zero backends stays advertised (section 2.5) |

The `bgpControlPlane.*` values are identical in 1.18.14, 1.19.8, 1.20.2 and 1.21.0-pre.3 (diffed from each tag's `values.yaml`). **[1.21 pre-release]** the BGP flags were moved into a `pkg/bgp/config` module, so the same flags (including router-ID flags) now also appear in the operator's flag set; Helm usage is unchanged.

Listening on TCP/179 is optional. By default a `bgpInstance` has no `localPort`, so the agent is **active-only** and only dials out to peers. If you set `localPort: 179`, the agent needs `CAP_NET_BIND_SERVICE` via the chart's `securityContext.capabilities.ciliumAgent` list; a high port avoids the capability.

### 2.3 The five CRDs

All are cluster-scoped, `cilium.io/v2`. The `cilium.io/v2alpha1` copies of the same kinds are **deprecated** (still served in 1.20.2 and 1.21.0-pre.3 with `+kubebuilder:deprecatedversion`); write all new manifests as `cilium.io/v2`.

| Kind | Short name | Written by | Purpose |
|---|---|---|---|
| `CiliumBGPClusterConfig` | `cbgpcluster` | user | Which nodes run which BGP instances and peers |
| `CiliumBGPPeerConfig` | `cbgppeer` | user | Session parameters and which advertisements go to a peer |
| `CiliumBGPAdvertisement` | `cbgpadvert` | user | What to advertise and with which attributes |
| `CiliumBGPNodeConfig` | `cbgpnode` | operator (read-only for users) | Resolved per-node config plus session status |
| `CiliumBGPNodeConfigOverride` | `cbgpnodeoverride` | user | Per-node router ID, ASN, ports, source address |

The linkage is two different mechanisms, which is a common source of mistakes:

```
CiliumBGPClusterConfig.spec.bgpInstances[].peers[].peerConfigRef.name  --by NAME-->  CiliumBGPPeerConfig
CiliumBGPPeerConfig.spec.families[].advertisements (label selector)    --by LABELS-> CiliumBGPAdvertisement.metadata.labels
```

A peer config selects advertisements by matching the **labels on the `CiliumBGPAdvertisement` object**, not its spec. Several advertisement objects may match one peer. If no advertisement matches, the session comes up but nothing is advertised.

#### CiliumBGPClusterConfig

| Field | Type / limits | Notes |
|---|---|---|
| `spec.nodeSelector` | LabelSelector | Nil or empty selects **all** nodes. A node may match only one `CiliumBGPClusterConfig` |
| `spec.bgpInstances[]` | 1 to 16 entries, key `name` | One GoBGP instance each |
| `.name` | 1 to 255 chars, unique | Referenced by overrides and shown in metrics as `instance_name` |
| `.localASN` | 1 to 4294967295 | Optional here; an override may supply it per node |
| `.localPort` | 1 to 65535 | Unset means the instance does not listen |
| `.peers[]` | key `name` | |
| `.peers[].peerAddress` | IPv4 or IPv6 | Optional only with `autoDiscovery` |
| `.peers[].peerASN` | 0 to 4294967295, default 0 | 0 skips ASN validation of the peer's OPEN message |
| `.peers[].autoDiscovery` | `mode: DefaultGateway`, `defaultGateway.addressFamily: ipv4\|ipv6` | Peer is the node's default gateway (see below) |
| `.peers[].peerConfigRef.name` | string | **Only `name` exists in `cilium.io/v2`**; `group`/`kind` exist only in the deprecated v2alpha1 CRD |

Status conditions on the cluster config: `cilium.io/NoMatchingNode`, `cilium.io/MissingPeerConfigs`, `cilium.io/ConflictingClusterConfig` (two cluster configs selecting the same node: the operator rejects the later one).

**Auto-discovery (`DefaultGateway`).** The agent peers with the node's default gateway instead of a fixed `peerAddress`. The ToR must use dynamic neighbors (`bgp listen range` in FRR) and the same local ASN on every ToR. A link-local default gateway is not supported. With multiple default routes (multihoming) Cilium creates **one** session per address family, to the lower-metric route, and moves to the other on failure; it cannot hold two sessions for the same family this way. If you need two sessions, use static `peerAddress` entries.

#### CiliumBGPPeerConfig

| Field | Default / limits | Notes |
|---|---|---|
| `spec.transport.peerPort` | 179 (1 to 65535) | Remote port |
| `spec.transport.sourceInterface` | none | Source IP taken from this interface. It must have at most one eligible address per family (not loopback, multicast, or IPv6 link-local). If the interface is missing, Cilium falls back to egress-interface autodetection. Not in 1.18 docs; present 1.19+ |
| `spec.timers.connectRetryTimeSeconds` | 120 (min 1) | Jittered: effective retry in [N, 2N) |
| `spec.timers.holdTimeSeconds` | 90 (3 to 65535) | Changing hold or keepalive resets the session |
| `spec.timers.keepAliveTimeSeconds` | 30 (1 to 65535) | CRD rule: keepalive <= holdTime |
| `spec.authSecretRef` | none | Name of a Secret in the BGP secrets namespace; key `password` (RFC 2385 TCP MD5) |
| `spec.gracefulRestart.enabled` | required if block present | |
| `spec.gracefulRestart.restartTimeSeconds` | 120 (1 to 4095) | |
| `spec.ebgpMultihop` | 1 (1 to 255) | Default TTL 1; ignored for iBGP |
| `spec.families[]` | afi + safi + `advertisements` selector | Only `ipv4/unicast` and `ipv6/unicast` are supported. If `families` is omitted, both unicast families are negotiated with **no** advertisements |

Status condition: `cilium.io/MissingAuthSecret`.

> **Upstream doc correction.** The upstream configuration page says minimum "possible" values are `holdTimeSeconds=9` and `keepAliveTimeSeconds=3`. The CRD minimums are hold >= 3 and keepalive >= 1 (with keepalive <= hold). 9/3 is a recommended aggressive setting, not a floor.

#### CiliumBGPAdvertisement

`spec.advertisements[]` entries:

| Field | Notes |
|---|---|
| `advertisementType` | `PodCIDR`, `CiliumPodIPPool`, `Service`, `Interface` |
| `service.addresses[]` | At least one of `LoadBalancerIP`, `ClusterIP`, `ExternalIP`. Required for type `Service` |
| `service.aggregationLengthIPv4` / `IPv6` | 0 to 31 / 0 to 127; aggregate instead of /32 and /128 |
| `interface.name` | Required for type `Interface` |
| `selector` | LabelSelector over Services (or pools). Unset selects nothing for non-PodCIDR types. Must not be set for `PodCIDR` |
| `attributes.communities` | `standard[]`, `wellKnown[]`, `large[]` |
| `attributes.localPreference` | Sent only to iBGP peers |

CEL validation enforces: `Service` requires `service`, `Interface` requires `interface`, `PodCIDR` must not have `selector`.

#### CiliumBGPNodeConfig (operator output)

`spec` mirrors the resolved configuration (adding `routerID` and `localAddress`). `status.bgpInstances[].peers[]` carries `name`, `peerAddress`, `peerASN`, `peeringState`, `establishedTime`, `timers.appliedHoldTimeSeconds`/`appliedKeepaliveSeconds` and `routeCount[]` (afi, safi, received, advertised). A `cilium.io/BGPReconcileError` condition surfaces reconcile failures. This is the right source for automation and alerting because it needs no exec into the agent.

#### CiliumBGPNodeConfigOverride

`metadata.name` **must equal the node name**; instance and peer names must match those in the cluster config.

| Field | Notes |
|---|---|
| `spec.bgpInstances[].name` | Matches the cluster config instance |
| `.routerID` | IPv4 address string |
| `.localPort` | Listen port override |
| `.localASN` | 1 to 4294967295; enables per-node/per-rack ASNs |
| `.peers[].name` | Matches the cluster config peer |
| `.peers[].localAddress` | Forces the source address (and so the egress link); default is a route lookup toward the peer |
| `.peers[].localPort` | Source port used when connecting |

### 2.4 Peer settings in practice

**Timers.** Defaults are 120/90/30 (connect-retry/hold/keepalive). Without BFD, hold time is the only failure detector for non-directly-connected peers, so aggressive values such as 9/3 are common on ToR links. Trade-off: more keepalive load and more sensitivity to agent CPU stalls.

**Graceful Restart.** With `gracefulRestart.enabled: true` Cilium acts as the Restarting Speaker (RFC 4724, plus RFC 8538 graceful restart with Notification). When the agent restarts, the peer keeps the routes it learned until `restartTimeSeconds` elapses, so the data plane (which keeps running in eBPF) is not blackholed during an agent upgrade. Set `restartTimeSeconds` larger than the worst-case agent restart, which includes the image pull; pre-pull images before upgrades. The cost: if a node genuinely dies, GR keeps its routes for up to the restart time, so for `externalTrafficPolicy: Cluster` VIPs traffic can still be sent to a dead node for that period.

**Multihop.** `ebgpMultihop: N` sets the TTL for eBGP sessions to peers more than one hop away (a loopback-peered ToR, or a route server). iBGP is unaffected.

**MD5.**

```bash
kubectl -n kube-system create secret generic bgp-auth \
  --from-literal=password='<value from your secret store>'
```

Reference it with `authSecretRef: bgp-auth`. A wrong password shows up as `dial: i/o timeout`, not an authentication error, because the kernel drops segments with bad signatures. A missing Secret does not stop the session: Cilium proceeds with an **empty** password, logs an error and sets `cilium.io/MissingAuthSecret`. MD5 cannot work if the session crosses NAT.

**No BFD.** Cilium does not support BFD in any of 1.18 to 1.21-pre. Mitigations: low hold timers, a directly connected link (TCP closes immediately on link-down), Graceful Restart for the agent-restart case, and resilient hashing/Maglev (below).

### 2.5 Advertisements

#### PodCIDR

Advertises the node's allocated PodCIDR (not the whole pool). It only has an effect with IPAM modes that give each node a PodCIDR: `cluster-pool` and Kubernetes host scope. **With ENI, Azure and similar cloud IPAM, `PodCIDR` advertisement has no effect**: Pod IPs are VPC (or VNet) addresses, not a per-node prefix owned by Cilium, and the cloud fabric already routes them. See [IPAM deep dive](10-ipam-deep-dive.md).

#### CiliumPodIPPool

For multi-pool IPAM. `selector` matches pool labels; the special keys `io.cilium.podippool.namespace` and `io.cilium.podippool.name` select by pool identity. Only CIDRs actually allocated to a `CiliumNode` are advertised. In 1.20.2 the BGP code watches `v2alpha1.CiliumPodIPPool`; **[1.21 pre-release]** `CiliumPodIPPool` is promoted to `cilium.io/v2` and BGP follows (`pkg/bgp/manager/reconciler/pod_ip_pool.go` at v1.21.0-pre.3).

#### Service

Routes are exact `/32` or `/128` by default.

| Source | Taken from | Traffic policy honored |
|---|---|---|
| `LoadBalancerIP` | `.status.loadBalancer.ingress[].ip` | `externalTrafficPolicy` only |
| `ExternalIP` | `.spec.externalIPs` (with KPR requires `externalIPs.enabled`) | `externalTrafficPolicy` only |
| `ClusterIP` | `.spec.clusterIP(s)` (external access needs the "External access to ClusterIP services" BPF setting) | `internalTrafficPolicy` only |

Selector special keys: `io.kubernetes.service.namespace`, `io.kubernetes.service.name`.

**Traffic-policy interaction.**

| Policy | Advertised from |
|---|---|
| `Cluster` | every node selected by the cluster config |
| `Local` | only nodes with at least one local ready backend; the route follows the Pods |

With **zero backends**: `externalTrafficPolicy: Cluster` keeps the VIP advertised from all nodes if `--enable-no-service-endpoints-routable=true` (default), otherwise it is withdrawn; `Local` withdraws it.

**`loadBalancerClass`.** Cilium announces a Service only if its class is unset or `io.cilium/bgp-control-plane`. A Service owned by another class (for example `service.k8s.aws/nlb`) is ignored.

**Overlapping advertisements (1.18 and later).** If several advertisements match one Service, communities are the **union** and `localPreference` is the **maximum**. Before 1.18 the last match won.

**Aggregation.** `aggregationLengthIPv4/6` is ignored for Local traffic policy. Known issues: a routing loop for unassigned VIPs inside an aggregated range, and undefined behavior if two advertisements produce the same aggregate with different attributes ([cilium/cilium#37623](https://github.com/cilium/cilium/pull/37623), [#40585](https://github.com/cilium/cilium/issues/40585)).

**ECMP.** Advertise the same VIP from many nodes; the router's ECMP path limit applies. Node loss reshuffles flows unless the router uses resilient hashing; Maglev in Cilium keeps backend selection consistent between nodes for `Cluster` policy.

#### Interface (1.19 and later)

Advertises the addresses of a local interface as /32 and /128 routes. Excluded: loopback range, multicast, IPv6 link-local, v4-mapped. The interface must be administratively up and operationally `up` or `unknown`. Cilium does not configure the address; typical use is a dummy interface carrying a stable node or anycast address.

#### Attributes

| Attribute | Values |
|---|---|
| `communities.standard` | `"65000:99"` or a 4-byte decimal |
| `communities.wellKnown` | `internet`, `planned-shut`, `accept-own`, `route-filter-translated-v4`, `route-filter-v4`, `route-filter-translated-v6`, `route-filter-v6`, `llgr-stale`, `no-llgr`, `blackhole`, `no-export`, `no-advertise`, `no-export-subconfed`, `no-peer` |
| `communities.large` | `"A:B:C"` |
| `localPreference` | iBGP only; for eBGP peers the attribute is omitted |

Cilium builds GoBGP export policies per (peer, family, advertisement type), for example `65000-ipv4-PodCIDR`, plus an import policy `allow-local`. These are internal. **There is no user-facing route-policy, prefix-list, AS-prepend, MED or next-hop CRD in v2**; use communities as the hook and implement the policy on the ToR (route-maps keyed on communities).

### 2.6 Complete example: per-rack eBGP to two ToRs

Addresses and ASNs are examples.

```yaml
apiVersion: cilium.io/v2
kind: CiliumBGPClusterConfig
metadata: {name: rack0}
spec:
  nodeSelector: {matchLabels: {rack: rack0}}
  bgpInstances:
  - name: instance-65001
    localASN: 65001
    peers:
    - {name: tor1, peerASN: 65000, peerAddress: 10.10.0.1, peerConfigRef: {name: tor-peer}}
    - {name: tor2, peerASN: 65000, peerAddress: 10.10.0.2, peerConfigRef: {name: tor-peer}}
---
apiVersion: cilium.io/v2
kind: CiliumBGPPeerConfig
metadata: {name: tor-peer}
spec:
  timers: {connectRetryTimeSeconds: 5, holdTimeSeconds: 9, keepAliveTimeSeconds: 3}
  gracefulRestart: {enabled: true, restartTimeSeconds: 120}
  authSecretRef: bgp-auth
  families:
  - afi: ipv4
    safi: unicast
    advertisements: {matchLabels: {advertise: bgp}}
---
apiVersion: cilium.io/v2
kind: CiliumBGPAdvertisement
metadata: {name: svc-and-pods, labels: {advertise: bgp}}
spec:
  advertisements:
  - advertisementType: PodCIDR
    attributes: {communities: {standard: ["65001:100"]}}
  - advertisementType: Service
    service: {addresses: [LoadBalancerIP]}
    selector: {matchLabels: {bgp: "true"}}
    attributes: {communities: {large: ["65001:1:100"]}}
```

Per-node override (the node name goes in `metadata.name`):

```yaml
apiVersion: cilium.io/v2
kind: CiliumBGPNodeConfigOverride
metadata: {name: <node-name>}
spec:
  bgpInstances:
  - name: instance-65001
    routerID: "192.168.10.1"
    localPort: 1790
    localASN: 65010
    peers:
    - {name: tor1, localAddress: 10.10.0.11}
```

### 2.7 Router ID

| Mode | How the ID is chosen |
|---|---|
| `default` | The node's IPv4 address (IPv4 and dual-stack), or the lower 32 bits of the `cilium_host` MAC on IPv6-only nodes |
| `ip-pool` | Allocated from `bgpControlPlane.routerIDAllocation.ipPool` (an IPv4 CIDR) |
| manual (`NodeConfigOverride.routerID`) | Not validated in `default` mode; in `ip-pool` mode it must not collide when inside the pool |

### 2.8 Inspection

**Status first** (no exec needed):

```bash
kubectl get ciliumbgpclusterconfigs,ciliumbgppeerconfigs,ciliumbgpadvertisements,ciliumbgpnodeconfigs
kubectl get ciliumbgpnodeconfigs <node> \
  -o jsonpath='{.status.bgpInstances[*].peers[*].peeringState}'
kubectl describe ciliumbgpclusterconfig rack0
```

**CLI.** `cilium bgp peers [-o json|summary] [--node N]` and `cilium bgp routes <available|advertised|received> <afi> <safi>` work in 1.20.2. They call the agent REST API, which is **deprecated in 1.20** (see below), and the CLI in the 1.21.0-pre.3 in-tree sources still execs `cilium bgp peers -o json` in the agent pod.

**Hive shell (preferred from 1.20).** Upstream's 1.20 upgrade notes state that listing BGP peers, routes and route policies through the local REST API and `cilium-dbg bgp` commands is deprecated in favor of the BGP hive shell commands. The agent binary is `cilium-dbg`:

```bash
kubectl -n kube-system exec ds/cilium -- cilium-dbg shell -- bgp/peers
kubectl -n kube-system exec ds/cilium -- cilium-dbg shell -- bgp/routes out ipv4 unicast
kubectl -n kube-system exec ds/cilium -- cilium-dbg shell -- bgp/route-policies
```

| Command | Meaning |
|---|---|
| `bgp/peers [-f table\|table-json\|json\|detailed] [-o file] [--no-uptime]` | Session table |
| `bgp/routes <loc\|in\|out> <afi> <safi> [-a\|--with-attrs] [--no-age] [-f ...]` | `loc` = Loc-RIB, `in` = Adj-RIB-In, `out` = Adj-RIB-Out |
| `bgp/route-policies [-i instance]` | Export/import policies Cilium generated |

The same three commands exist in 1.20.2 and 1.21.0-pre.3 (`pkg/bgp/commands/cell.go`). The `cilium` CLI has no `shell` subcommand; use `cilium-dbg` inside the agent pod.

**Logs.** Agent `subsys=bgp-control-plane`; operator `subsys=bgp-cp-operator`.

**Metrics** (agent, prefix `cilium_bgp_control_plane_`): `session_state` (1 = established), `advertised_routes`, `received_routes` (labels `instance_name`, `local_asn`, `neighbor`, `neighbor_asn`, `afi`, `safi`), `reconcile_errors_total{instance_name}`, `reconcile_run_duration_seconds{instance_name}`. Operator: `cilium_operator_bgp_control_plane_reconcile_errors_total{resource_kind,resource_name}` and `..._reconcile_run_duration_seconds`.

> **Metric label change.** The 1.19.8 metrics page uses the label `vrouter`; 1.20.2 uses `instance_name`. The 1.20 upgrade notes do not mention the rename, so dashboards and alerts keyed on `vrouter` silently stop matching after 1.19 to 1.20. Update them as part of the upgrade.

### 2.9 v1 removal and the CRD version timeline

| Release | State |
|---|---|
| 1.18 | `CiliumBGPPeeringPolicy` (v1) deprecated; if both v1 and v2 match a node, the PeeringPolicy wins. v2alpha1 BGP v2 CRDs deprecated in favor of `cilium.io/v2` |
| 1.19 | v1 CRD **and** control plane (`pkg/bgpv1`) **removed**; migrate before upgrading |
| 1.20 | v2alpha1 copies of the v2 BGP CRDs still served but deprecated |
| 1.21-pre | Same |

The pre-1.19 `spec.transport.localPort` field of the v2alpha1 PeerConfig was removed; port configuration lives on the cluster config instance (`localPort`) and on the override.

### 2.10 Operations and failure scenarios

| Event | Behavior | Mitigation |
|---|---|---|
| Agent restart or upgrade | Session drops (the speaker is in the agent); datapath keeps forwarding | Graceful Restart, `restartTimeSeconds` > agent boot; pre-pull the new image |
| Node crash | Peer waits for hold time (plus restart time with GR) | Low hold timers; ECMP with resilient hashing |
| Link down, directly connected | TCP closes immediately | n/a |
| Link down, multi-hop | Hold timer (default 90s) | Lower hold time; no BFD available |
| Operator down | No new `CiliumBGPNodeConfig`; also no PodCIDR or LB IP allocation by the operator | Operator HA |
| Service loses all backends | See section 2.5 | Choose policy deliberately |

**Node shutdown runbook.** Drain the node; remove it from the cluster config by changing its label so the `nodeSelector` no longer matches (the session closes with a Notification); wait for the peer to withdraw (immediately, or after the stale timer with RFC 8538); expect some ECMP rehash resets.

**[1.21 pre-release]** The BGP controller waits for the host datapath BPF programs to attach and the LB maps to be populated before announcing any route (`pkg/bgp/agent/datapath_waiter.go`), closing a window after agent start where routes were advertised before they could be served. Not present in 1.20.

### 2.11 On-prem ToR reference topology

```
            [ upstream L3 / firewall ]
                 |            |
             ToR-A (AS65000) ToR-B (AS65000)    static neighbors or `bgp listen range`
              |  \  /  |     ECMP, resilient hashing, GR helper
      node1..N (Cilium AS65001, one CiliumBGPClusterConfig per rack)
        advertise: PodCIDR (cluster-pool / host-scope IPAM)
                 + Service LoadBalancerIP (from an LB IPAM pool)
        eTP: Cluster (all nodes; add Maglev) or Local (only nodes with backends)
```

Design checklist: one cluster config per rack (a node can match only one); two peers per rack; hold 9 / keepalive 3 with GR whose restart time exceeds agent boot; MD5 via `authSecretRef`; communities to distinguish Pod routes from Service routes for ToR route-maps; verify the ToR's maximum ECMP paths; no BFD.

### 2.12 BGP and AWS

In an EKS cluster using ENI IPAM, Pod IPs are VPC addresses and the VPC fabric already routes them; a node does not own a PodCIDR, so PodCIDR advertisement has no effect and the VPC has no BGP speaker that would accept node routes. BGP is therefore relevant on AWS mainly for EKS Hybrid Nodes running on-premises (see [hybrid nodes network configuration](../../eks-hybrid-nodes/02-network-configuration.md)), where the on-prem ToR is the peer. Existing hybrid-node examples in this repo use the `v2alpha1` APIs because they pin a 1.18 build; use `cilium.io/v2` on 1.19 and later.

## 3. LB IPAM

**Maturity**: stable CRD `cilium.io/v2` `CiliumLoadBalancerIPPool` (v2 is the storage version in 1.18.14 with v2alpha1 still served; v2alpha1 is first marked deprecated in 1.19.8). LB IPAM is built into the operator and dormant until the first pool is created (`--enable-lb-ipam`, default true). It allocates addresses only; it does not announce them.

```yaml
apiVersion: cilium.io/v2
kind: CiliumLoadBalancerIPPool
metadata: {name: blue-pool}
spec:
  blocks:
  - cidr: "10.0.10.0/24"
  - start: "10.0.20.100"
    stop: "10.0.20.200"
  serviceSelector:
    matchLabels: {bgp: "true"}
---
apiVersion: v1
kind: Service
metadata: {name: web, namespace: example, labels: {bgp: "true"}}
spec:
  type: LoadBalancer
  loadBalancerClass: io.cilium/bgp-control-plane
  ports: [{port: 80}]
  selector: {app: web}
```

Note `serviceSelector` is under `spec`, not under `blocks` (the upstream docs example mis-indents it).

| Pool field | Notes |
|---|---|
| `blocks[]` | `cidr`, or `start`+`stop` |
| `serviceSelector` | Special keys `io.kubernetes.service.namespace`/`.name` |
| `disabled` | Default false |
| `allowFirstLastIPs` | `Yes` or `No`; `No` reserves the first and last address of CIDR blocks only; ignored for /31, /32, /127, /128 and start/stop blocks |

Behaviors worth knowing:

- Overlapping CIDRs: the later pool is marked conflicting (`cilium.io/PoolConflict`). Status conditions `cilium.io/IPsTotal`, `IPsAvailable`, `IPsUsed`; `kubectl get ippools` shows them.
- Editing a pool can reassign IPs of existing Services.
- Class handling: a `LoadBalancer` Service with no class is served by LB IPAM by default. Helm `defaultLBServiceIPAM` is `lbipam` (default), `nodeipam` or `none`; with `none` only Services with a recognized class get an IP. A class Cilium does not recognize is ignored silently. The Service gets a condition `cilium.io/IPAMRequestSatisfied`.
- IP families follow `ipFamilyPolicy`: SingleStack (IPv4 if both are available), PreferDualStack, RequireDualStack.
- Request a specific address with `lbipam.cilium.io/ips: "a,b"` (the pool selector still applies; `.spec.loadBalancerIP` is deprecated). Do not request the first/last address of a pool.
- **Sharing**: `lbipam.cilium.io/sharing-key` and `lbipam.cilium.io/sharing-cross-namespace: "ns1,ns2"|"*"`. 1.20.2: Services can share if no port/protocol conflicts. **[1.21 pre-release]** stricter compatibility: no same port+protocol, same `externalTrafficPolicy`, with `Local` both must select the same Pods unless every Service sets `lbipam.cilium.io/sharing-permit-different-pods: "true"` (BGP and L2 are not L4-aware, so traffic can be dropped), same namespace unless cross-namespace is permitted.
- **1.19 datapath change**: N/S TCP/UDP to an LB-IPAM IP on a port no Service defines is dropped.
- Gateway API: `Gateway.spec.addresses` feeds LB IPAM; the `io.cilium/lb-ipam-ips` annotation in `spec.infrastructure.annotations` takes precedence and is slated for later deprecation.

Pod IPAM is a separate topic: see [IPAM deep dive](10-ipam-deep-dive.md).

## 4. L2 announcements

**Maturity**: beta in 1.20.2 and 1.21.0-pre.3. The CRD is still `cilium.io/v2alpha1` `CiliumL2AnnouncementPolicy`.

One elected node per Service answers ARP (IPv4) or NDP (IPv6) for the Service's external or LoadBalancer IPs, then load-balances with eBPF. It targets on-prem LANs without BGP. **It is not applicable inside an AWS VPC**: the VPC does not give VIPs L2 broadcast semantics or gratuitous-ARP failover. Use it on-prem or in hybrid sites only.

```yaml
l2announcements:
  enabled: true
  leaseDuration: 3s
  leaseRenewDeadline: 1s
  leaseRetryPeriod: 200ms
kubeProxyReplacement: true
k8sClientRateLimit: {qps: 32, burst: 64}
```

```yaml
apiVersion: cilium.io/v2alpha1
kind: CiliumL2AnnouncementPolicy
metadata: {name: policy1}
spec:
  serviceSelector: {matchLabels: {color: blue}}
  nodeSelector:
    matchExpressions:
    - {key: node-role.kubernetes.io/control-plane, operator: DoesNotExist}
  interfaces: ["^eth[0-9]+"]
  externalIPs: true
  loadBalancerIPs: true
```

| Field | Notes |
|---|---|
| `nodeSelector`, `serviceSelector` | Which nodes may announce; which Services |
| `interfaces[]` | Go regexes (OR). Not a security control. Devices must also be in Cilium's `--devices` set |
| `externalIPs`, `loadBalancerIPs` | Booleans, both default false |

The Service must have no `loadBalancerClass` or `io.cilium/l2-announcer`.

**Leader election.** One `coordination.k8s.io` Lease per Service named `cilium-l2announce-<ns>-<svc>` in Cilium's namespace; first-come-first-served, so load is uneven. A new leader sends a gratuitous ARP. Defaults: `leaseDuration` 15s, `leaseRenewDeadline` 5s, `leaseRetryPeriod` 2s. Constraints: duration > renewDeadline; renewDeadline strictly greater than 1.2 (the leader-election JitterFactor) x retryPeriod, otherwise the agent logs a warning and overrides the timers. Failover lands between `leaseDuration - leaseRenewDeadline` and `leaseDuration + leaseRenewDeadline`: 10 to 20 seconds with defaults, 2 to 4 seconds with 3s/1s/200ms.

**API load.** Each Service lease is renewed about every `leaseRenewDeadline`, so budget `QPS ~ number_of_services x (1 / leaseRenewDeadline)` (a rough estimate that ignores retries and reads). The default agent client limit is 10 QPS / burst 20 and is shared with all other agent API traffic: with the 5s default that is about 0.2 QPS per Service, so a few dozen led Services already use a large part of the budget, and with 1s timers about 10 Services use all of it. Raise `k8sClientRateLimit` before tightening timers. RBAC needs lease create/get/update/list/delete.

**Limits.** Incompatible with `externalTrafficPolicy: Local` (the elected node may have no Pod, traffic is dropped). One node receives all traffic for an IP, so there is no pre-cluster load balancing.

**L2 Pod announcements** are separate: `l2podAnnouncements.enabled` and `.interfacePattern` (regex) send GARP/NA for local Pod IPs. The old `--l2-pod-announcements-interface` flag was removed in 1.19.

Inspect: `kubectl -n kube-system get lease | grep cilium-l2announce`; `cilium-dbg shell -- db/show l2-announce`; `cilium-dbg shell -- db/show devices`; `arping` from another host on the LAN.

## 5. Node IPAM

Helm `nodeIPAM.enabled=true` (default false; operator `--enable-node-ipam`; restart the operator). Services with `loadBalancerClass: io.cilium/node` (or `defaultLBServiceIPAM: nodeipam`) get the nodes' addresses published into `.status.loadBalancer`: ExternalIP if present, else InternalIP, respecting `ipFamilies`. `Cluster` policy publishes all nodes; `Local` only nodes with EndpointSlice Pods. Nodes with label `node.kubernetes.io/exclude-from-external-load-balancers` or taint `ToBeDeletedByClusterAutoscaler` are skipped; annotation `io.cilium.nodeipam/match-node-labels` restricts nodes. It does not work with `Local` policy on Cilium Ingress/Gateway Services (synthetic EndpointSlice). Use it only where BGP and L2 are impossible, and only with private node addresses: publishing public node IPs would create a public entry point outside the CloudFront-only rule.

## 6. Which feature owns a Service?

| `loadBalancerClass` | Owner | Needs |
|---|---|---|
| unset | LB IPAM by default (`defaultLBServiceIPAM`) | A pool; plus BGP or L2 to be reachable |
| `io.cilium/bgp-control-plane` | LB IPAM + BGP advertisement | BGP Control Plane |
| `io.cilium/l2-announcer` | LB IPAM + L2 announcement | L2 announcements |
| `io.cilium/node` | Node IPAM | `nodeIPAM.enabled` |
| `service.k8s.aws/nlb` | AWS Load Balancer Controller | Ignored by Cilium BGP/LB IPAM |

## 7. Egress Gateway

**Maturity**: `CiliumEgressGatewayPolicy` is `cilium.io/v2` (cluster-scoped, short name `cegp`); not marked beta in the 1.20 docs.

Selected Pods' traffic to selected destination CIDRs is forwarded to a gateway node and SNATed to a stable source IP, so an external firewall sees a predictable address.

Requirements: `egressGateway.enabled=true`, `bpf.masquerade=true`, `kubeProxyReplacement=true`; restart agents **and** operator. Not compatible with identity mode `kvstore` (use `crd`), ClusterMesh (gateway must be in the same cluster), or CiliumEndpointSlice. `--enable-ipv4-egress-gateway` was removed in 1.19.

```yaml
apiVersion: cilium.io/v2
kind: CiliumEgressGatewayPolicy
metadata: {name: egress-sample}
spec:
  selectors:
  - podSelector:
      matchLabels: {org: empire, class: mediabot, io.kubernetes.pod.namespace: default}
  destinationCIDRs: ["192.0.2.0/24"]
  egressGateway:
    nodeSelector: {matchLabels: {egress-node: "true"}}
    egressIP: 10.168.60.100
```

| Field | Notes |
|---|---|
| `selectors[]` | `podSelector` and/or `namespaceSelector` (namespace via label `io.kubernetes.pod.namespace`); `nodeSelector` alone not allowed |
| `destinationCIDRs[]`, `excludedCIDRs[]` | IPv4 and IPv6; excluded must be subsets. Internal addresses (Pods, nodes, API server) are always excluded from EGW |
| `egressGateway.nodeSelector` | Required. Several matches: first by node-name order. **No match: traffic to the destination CIDRs is dropped** |
| `egressGateway.interface` / `egressIP` | Mutually exclusive (policy ignored if both). `interface` uses its first IPv4/IPv6; `egressIP` must exist on a Cilium-managed device; omitting both selects the default-route interface and its first IPv4/IPv6 addresses |
| `egressGateways[]` | Up to 64 entries; if non-empty, `egressGateway` is ignored |

Limitations:

- **No HA in 1.20.2 or 1.21.0-pre.3.** `egressGateways[]` is static multi-gateway: each source endpoint is pinned to one gateway by a hash of its CiliumEndpoint UID. Changing the set reassigns endpoints and breaks existing connections (cilium/cilium#39245). No health check or automatic failover of a dead gateway appears in the source of either version (searched `pkg/egressgateway`). The 1.21-pre CRD differs from 1.20.2 only in CIDR types.
- The gateway does not follow IP changes after selection; re-apply the policy.
- A missing configured IP drops traffic with reason "No Egress IP configured".
- A new Pod can send traffic with its own or node IP briefly before the policy is programmed.
- SNAT port budget per (egress IP, remote IP:port) is about 65535 minus the upper bound of the node-port range (default 32767), i.e. 32768 connections. Watch with `cilium-dbg shell -- db/show nat-stats`.

Inspect: `kubectl -n kube-system exec ds/cilium -- cilium-dbg bpf egress list` (source IP, destination CIDR, egress IP, gateway IP).

**On EKS.** The gateway node needs the egress address on an attached ENI (extra ENI or secondary private IP). Egress IPs are private VPC addresses; to reach the internet from them, route through a NAT gateway. Do not attach public IPs or EIPs to the gateway nodes. With ENI IPAM, `--egress-multi-home-ip-rule-compat` was removed in 1.19, so migrate off it in 1.18 first.

## 8. Local Redirect Policy

`CiliumLocalRedirectPolicy` (`cilium.io/v2`, namespaced) redirects traffic for a Service ClusterIP, or for an arbitrary IP:port, to node-local backend Pods.

Enable with `localRedirectPolicies.enabled=true` (the old `localRedirectPolicy` key is deprecated); restart operator and agent. An optional cluster-wide allow-list is `localRedirectPolicies.addressMatcherCIDRs` (the upstream doc's YAML shows a differently spelled key; the Helm key is `addressMatcherCIDRs`).

```yaml
apiVersion: cilium.io/v2
kind: CiliumLocalRedirectPolicy
metadata: {name: lrp-svc}
spec:
  redirectFrontend:
    serviceMatcher: {serviceName: my-service, namespace: default}
  redirectBackend:
    localEndpointSelector: {matchLabels: {app: proxy}}
    toPorts: [{port: "80", protocol: TCP}]
```

| Matcher | Use |
|---|---|
| `serviceMatcher` | ClusterIP Services only; replaces the Service entry with type `LocalRedirect` and node-local backends only |
| `addressMatcher{ip, toPorts[]}` | Non-Service IPs; refuses to override an existing ClusterIP frontend |

Rules: backend Pods must be in the policy's namespace; multi-port requires named ports; only **new** connections are redirected (restart clients); policies are not updatable (delete and recreate). Supported kube-proxy-replacement setups: full KPR; KPR with `socketLB.hostNamespaceOnly=true`; KPR off with `socketLB.enabled=true`; KPR off alone (Pod to ClusterIP only). The main use is node-local DNS (kube-dns frontend redirected to a node-local-dns Pod in its own network namespace). Inspect with `cilium-dbg lrp list`.

## 9. Service traffic distribution

`loadBalancer.serviceTopology` (default `false`, flag `--enable-service-topology`) makes kube-proxy replacement honor Topology Aware Routing hints **and** `spec.trafficDistribution`. `PreferSameZone` (and the deprecated alias `PreferClose`) uses EndpointSlice zone hints against the node's `topology.kubernetes.io/zone` label; `PreferSameNode` prefers backends on the local node and falls back to the default if none qualify. **[1.21 pre-release]** only active (ready) backends count as preference candidates. This is distinct from `externalTrafficPolicy`/`internalTrafficPolicy: Local`, which restrict rather than prefer. For multi-AZ EKS, `serviceTopology: true` plus `trafficDistribution: PreferSameZone` reduces cross-AZ traffic. Gateway API: `CiliumGatewayClassConfig.spec.service.trafficDistribution` passes through to the generated Service.

## 10. L7 entry points: Ingress and Gateway API

Prerequisites: `kubeProxyReplacement=true`, `l7Proxy=true` (default), TPROXY support (iptables by default; `bpf.tproxy=true` is beta and removes the iptables dependency), and LoadBalancer Service support (or host-network mode, 1.16+).

**How traffic flows.** eBPF intercepts packets to the Service port and redirects them (TPROXY) to the per-node Envoy. Traffic gets the special `ingress` identity, so policy applies twice: world to ingress, ingress to backend. Source IP is preserved with both `externalTrafficPolicy` values; with `Local` Cilium makes every node pass the health check port. Your `CiliumNetworkPolicy` must allow both hops. TLS passthrough means backends see Envoy's IP.

### Ingress

| Helm value | Default |
|---|---|
| `ingressController.enabled` / `.default` | `false` / `false` |
| `ingressController.loadbalancerMode` | `dedicated` (`shared` or `dedicated`; per-Ingress annotation `ingress.cilium.io/loadbalancer-mode`) |
| `ingressController.enforceHttps` | `true` |
| `ingressController.useRemoteAddress`, `.xffNumTrustedHops` | `true`, `0` |
| `ingressController.ingressLBAnnotationPrefixes` | `lbipam.cilium.io`, `nodeipam.cilium.io`, `service.beta.kubernetes.io`, `service.kubernetes.io`, `cloud.google.com` (propagated Ingress to Service) |
| `ingressController.service.*` (shared) | `name: cilium-ingress`, `type: LoadBalancer`, `externalTrafficPolicy: Cluster`, annotations, `loadBalancerClass` |
| `ingressController.hostNetwork.*` | `enabled: false`, `sharedListenerPort: 8080` |

### Gateway API

Cilium 1.20.2 and 1.21.0-pre.3 use **Gateway API v1.6.1** (1.19.8: v1.4.1; 1.18.14: v1.3.0). Supported kinds: GatewayClass, Gateway, HTTPRoute, GRPCRoute, TLSRoute, BackendTLSPolicy, ReferenceGrant, ListenerSet, TCPRoute, UDPRoute. Required CRDs: GatewayClass, Gateway, HTTPRoute, GRPCRoute, ReferenceGrant, BackendTLSPolicy, TLSRoute. TCPRoute, UDPRoute and ListenerSet are optional (the feature is disabled if absent). Install with `kubectl apply --server-side`.

> **Upgrade trap: Gateway API v1.6.1 and TLSRoute.** In v1.6.1 TLSRoute graduated from `v1alpha2` to `v1`. The 1.20 upgrade notes require v1.6.1 as the minimum. If you have existing TLSRoute objects, install the **experimental-channel** TLSRoute CRD from v1.6.1 (it still includes the `v1alpha2` version). Installing the **standard**-channel v1.6 TLSRoute CRD makes existing `v1alpha2` objects unreadable and they appear to disappear from etcd. Back up TLSRoutes and upgrade the Gateway API CRDs **before** upgrading Cilium to 1.20.

| Helm value | Default |
|---|---|
| `gatewayAPI.enabled` | `false` |
| `gatewayAPI.gatewayClass.create` | `auto` |
| `gatewayAPI.enableProxyProtocol`, `.enableAppProtocol`, `.enableAlpn` | `false` |
| `gatewayAPI.useRemoteAddress`, `.xffNumTrustedHops` | `true`, `0` |
| `gatewayAPI.externalTrafficPolicy` | `Cluster` (ignored with host network) |
| `gatewayAPI.secretsNamespace` | `create: true`, `name: cilium-secrets`, `sync: true` |
| `gatewayAPI.hostNetwork.enabled` / `.nodes.matchLabels` | `false` / `{}` |

The generated Service is named `cilium-gateway-<gateway>` and is `LoadBalancer` by default. Customize through `CiliumGatewayClassConfig` (`cilium.io/v2alpha1`, namespaced, referenced from `GatewayClass.parametersRef`; alpha): `spec.service{type, externalTrafficPolicy, loadBalancerClass, ipFamilies, ipFamilyPolicy, allocateLoadBalancerNodePorts, loadBalancerSourceRanges, loadBalancerSourceRangesPolicy, trafficDistribution}`, `envoy.serverHeaderTransformation`, `httpOptions.grpcWebTranslation.enabled`. Per Gateway, `spec.infrastructure.annotations` and `labels` are copied onto the generated Service, which is how you pass `service.beta.kubernetes.io/aws-load-balancer-*` annotations. `spec.infrastructure.parametersRef` is not supported.

Host-network mode (`gatewayAPI.hostNetwork.enabled=true`): Envoy listens on node interfaces; use ports above 1023 or grant `NET_BIND_SERVICE`; exclusive with LoadBalancer Service mode; incompatible with TCPRoute/UDPRoute; the Service becomes NodePort; at most 16 addresses appear in Gateway status.

### EKS pattern: CloudFront VPC origin to internal NLB to Cilium

The only public entry point is CloudFront. Nothing here is internet-facing.

```
Internet --> CloudFront --(VPC origin)--> INTERNAL NLB (private subnets)
         --> node NodePort --> Cilium Envoy (Ingress or Gateway) --> Pods
```

```yaml
kubeProxyReplacement: true
ingressController:
  enabled: true
  loadbalancerMode: shared
  service:
    type: LoadBalancer
    loadBalancerClass: service.k8s.aws/nlb
    allocateLoadBalancerNodePorts: true
    externalTrafficPolicy: Cluster
    annotations:
      service.beta.kubernetes.io/aws-load-balancer-scheme: internal
      service.beta.kubernetes.io/aws-load-balancer-nlb-target-type: instance
      service.beta.kubernetes.io/aws-load-balancer-security-groups: sg-<nlb-sg>
      service.beta.kubernetes.io/aws-load-balancer-manage-backend-security-group-rules: "true"
```

For the Gateway API variant, set `CiliumGatewayClassConfig.spec.service.loadBalancerClass: service.k8s.aws/nlb` and put the same `aws-load-balancer-*` annotations in `Gateway.spec.infrastructure.annotations`.

Rules for this pattern:

- `scheme: internal` is mandatory. Never `internet-facing`.
- Use `target-type: instance`. Cilium's shared Ingress Service uses a synthetic EndpointSlice, so `ip` targets do not resolve to Pods; see [Ingress and Gateway API](../../service-mesh/cilium-service-mesh/05-ingress-gateway.md).
- The load balancer's security group admits only CloudFront: either the service-managed security group `CloudFront-VPCOrigins-Service-SG` (created after you create the VPC origin; more restrictive, preferred; do not name your own group with that prefix) or the CloudFront managed prefix list `com.amazonaws.global.cloudfront.origin-facing` (plus `com.amazonaws.global.ipv6.cloudfront.origin-facing` for dual stack). No `0.0.0.0/0` or `::/0` ingress, and no public IPs or EIPs on nodes ([AWS: VPC origins](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/private-content-vpc-origins.html)).
- Node security groups admit the NLB's security group on the NodePort range, not a CIDR open to the internet.

## 11. SRv6 and static routing

SRv6 is **absent** as a supported feature. The 1.20.2 and 1.21.0-pre.3 sources have no documentation page, Helm key or CRD for it; only a hidden `--enable-srv6` agent flag, BPF hooks and `cilium-dbg bpf srv6` inspection commands remain, without an OSS control plane. Do not plan on it. For static routing, rely on native routing with `autoDirectNodeRoutes` or cloud route tables ([Part 9](09-overlay-native-routing.md)).

## Labs

> Labs 1 to 4 need a local lab (kind or a few VMs) with a router container such as FRR; Lab 5 targets a disposable sandbox AWS account via `--profile <SANDBOX_PROFILE>`. Expected results are described in words; none are captured output.

### Lab 1: BGP session with an FRR ToR

**Prerequisites**: a kind cluster with 2 workers on a Docker network shared with an FRR container (AS 65000, neighbors configured for the node IPs, remote AS 65001); Cilium with `bgpControlPlane.enabled=true`; the section 2.6 manifests adapted to your node IPs (drop `authSecretRef` or create the Secret first).

1. Label the workers `rack=rack0`; apply the ClusterConfig, PeerConfig and Advertisement.
2. `kubectl get ciliumbgpnodeconfigs` lists one per labeled node.
3. `kubectl get ciliumbgpnodeconfigs <node> -o jsonpath='{.status.bgpInstances[*].peers[*].peeringState}'` and `cilium-dbg shell -- bgp/peers` should report `established`; FRR `show bgp summary` should show the neighbors up.
4. `cilium-dbg shell -- bgp/routes out ipv4 unicast` shows the node's PodCIDR; FRR `show ip route bgp` shows it learned.
5. Delete the agent Pod on one node. With GR enabled, FRR should keep the routes (marked stale) until the restart time; without GR they disappear at once. Compare.

**Rollback/cleanup**: delete the three BGP resources; remove the node labels. Deleting the ClusterConfig makes the operator remove the NodeConfigs and sessions close.

### Lab 2: LB IPAM plus BGP, and traffic-policy interaction

**Prerequisites**: Lab 1 running.

1. Create the section 3 pool and Service (use a block inside a range your FRR container accepts).
2. `kubectl get svc web -n example` shows an EXTERNAL-IP from the pool; `kubectl get ippools` shows `IPsUsed` of 1.
3. `bgp/routes out ipv4 unicast` shows the /32 from every selected node. From the FRR container, `curl <VIP>`.
4. `kubectl patch svc web -n example -p '{"spec":{"externalTrafficPolicy":"Local"}}'`. The route should remain only on nodes with a ready Pod; scale the Deployment and watch it follow.

**Cleanup**: delete the Service, Deployment and pool.

### Lab 3: L2 announcements

**Prerequisites**: a kind cluster on a Linux bridge, KPR on, `l2announcements.enabled=true` with 3s/1s/200ms and a raised client rate limit; a client container on the same bridge.

1. Apply the L2 policy and a `LoadBalancer` Service from a pool.
2. `kubectl -n kube-system get lease | grep cilium-l2announce` shows a lease for the Service; `arping` from the client returns the leader node's MAC.
3. Delete the Cilium agent Pod on the leader node (or stop the node container) and time how long `arping` fails: expect on the order of seconds with these timers, 10 to 20 with defaults.

**Cleanup**: delete policy and Service. Rollback: set the lease values back to defaults.

### Lab 4: Egress Gateway

**Prerequisites**: KPR and `bpf.masquerade=true`, `egressGateway.enabled=true`, agents and operator restarted; an external web server container that logs client IPs; a node labeled `egress-node=true` with a secondary address on its device.

1. Apply a policy like section 7 with that address and the server's CIDR.
2. From a selected Pod, `curl` the server; its log should show the egress IP rather than the node or Pod IP.
3. `cilium-dbg bpf egress list` on the source node lists the entry. Remove the node label: traffic to the CIDR should be dropped (no gateway).

**Cleanup/rollback**: delete the policy; remove the label. This is disruptive to the selected traffic while applied.

### Lab 5: EKS internal NLB behind CloudFront (sandbox account)

**Prerequisites**: `aws sts get-caller-identity --profile <SANDBOX_PROFILE>` shows the expected sandbox account `<ACCOUNT_ID>` and your intended assumed role; an EKS cluster with Cilium and the AWS Load Balancer Controller; a CloudFront VPC origin already created.

1. Install with the section 10 Helm values (Gateway API variant if preferred).
2. `aws elbv2 describe-load-balancers --profile <SANDBOX_PROFILE> --query 'LoadBalancers[].[LoadBalancerName,Scheme]'` must show `internal` for the new NLB.
3. `aws ec2 describe-security-groups --profile <SANDBOX_PROFILE> --group-ids <nlb-sg> --query 'SecurityGroups[].IpPermissions'` must show only the CloudFront VPC-origin group or prefix list as sources, never `0.0.0.0/0` or `::/0`.
4. Set the NLB as the VPC origin's target; request through the CloudFront domain.

**Cleanup**: delete the Ingress or Gateway (the controller deletes the NLB), then verify the NLB is gone with a genuine not-found, not just a `deleting` state.

## Version Delta

| Area | 1.18 | 1.19 | 1.20 | 1.21-pre |
|---|---|---|---|---|
| BGP v1 `CiliumBGPPeeringPolicy` | deprecated | **removed** | removed | removed |
| BGP CRDs | v2 (and v2alpha1) | `cilium.io/v2` storage, v2alpha1 deprecated | same | same |
| BGP `Interface` advertisement, `transport.sourceInterface` | not in docs | present | present | present |
| GoBGP | n/a in this review | gobgp v3 (1.19.8) | gobgp v4 | gobgp v4 |
| BGP metrics label | n/a | `vrouter` (doc) | `instance_name` | `instance_name` |
| `cilium-dbg bgp` / REST listing | supported | supported | **deprecated**, use hive shell `bgp/*` | marked deprecated |
| BGP announce gating on datapath readiness | no | no | no | **yes** |
| `CiliumLoadBalancerIPPool` | v2 (storage), v2alpha1 still served | `cilium.io/v2` (v2alpha1 deprecated) | v2 | v2; stricter sharing rules |
| Gateway API CRDs | v1.3.0 | v1.4.1 | **v1.6.1** (TLSRoute trap) | v1.6.1 |
| `CiliumPodIPPool` API | v2alpha1 | v2alpha1 | v2alpha1 | **v2** |
| Egress Gateway | CRD v2 | `--enable-ipv4-egress-gateway`, `--egress-multi-home-ip-rule-compat` removed | no HA | no HA |
| L2 announcements | beta | beta | beta (CRD v2alpha1) | beta |
| SRv6 | absent | absent | absent | absent (hidden flag only) |

## Troubleshooting

| Symptom | Likely cause | Check |
|---|---|---|
| No `CiliumBGPNodeConfig` created | Operator not running or `nodeSelector` matches nothing | ClusterConfig conditions `NoMatchingNode`; operator logs `subsys=bgp-cp-operator` |
| Cluster config rejected | Another cluster config selects the same node | `ConflictingClusterConfig` |
| Session stuck, `dial: i/o timeout` | Wrong MD5 password, ACL, wrong source address | `authSecretRef`, `cilium.io/MissingAuthSecret`, `localAddress`/`sourceInterface` |
| Session up, no routes | PeerConfig `families[].advertisements` labels do not match advertisement labels | Compare labels; `bgp/route-policies` |
| PodCIDR not advertised on EKS | ENI IPAM has no per-node PodCIDR | [IPAM](10-ipam-deep-dive.md) |
| Service VIP not advertised | `loadBalancerClass` not `io.cilium/bgp-control-plane`/unset, selector misses, `Local` policy with no ready backend | Service YAML; `bgp/routes out` |
| Routes vanish at agent upgrade | No Graceful Restart or restart time too short | PeerConfig GR; pre-pull image |
| Grafana BGP panels empty after 1.20 | Label `vrouter` renamed `instance_name` | Update queries |
| LB IP stays `<pending>` | No pool, selector mismatch, pool conflict, unknown class | `kubectl get ippools`; Service condition |
| L2 VIP flaps or fails | `Local` policy, lease API throttling | Lease objects; raise `k8sClientRateLimit` |
| Egress traffic dropped | No node matches gateway `nodeSelector`, or IP missing on device | `bpf egress list`; drop reason |
| TLSRoutes vanished after Gateway API CRD upgrade | Standard-channel v1.6 CRD installed over v1alpha2 data | Restore from backup; use experimental-channel CRD |
| Gateway Service stuck | Missing required Gateway API CRDs, KPR off | Operator logs; `cilium status` |

## Validation Limits and Sources

The labs were not executed against a live cluster in this review and were checked against upstream source and documentation. Command syntax for `bgp/peers` and `bgp/routes` was verified from `pkg/bgp/commands`; real table output was not captured and is therefore not shown. Facts about BGP with EKS-native (non-hybrid) clusters, such as Transit Gateway Connect or VPC Route Server peering, were not researched and are omitted. Unverified: whether Egress Gateway gains health-based failover in 1.21 GA, and the exact 1.19 to 1.20 release that renamed the metric label (confirmed present in 1.20.2, absent from the 1.19.8 doc).

Sources (tag v1.20.2 unless noted):

- [BGP Control Plane overview](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/bgp-control-plane/bgp-control-plane.rst), [configuration](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/bgp-control-plane/bgp-control-plane-configuration.rst), [operation](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/bgp-control-plane/bgp-control-plane-operation.rst)
- [BGP CRD types](https://github.com/cilium/cilium/tree/v1.20.2/pkg/k8s/apis/cilium.io/v2), [hive shell commands](https://github.com/cilium/cilium/blob/v1.20.2/pkg/bgp/commands/cell.go)
- [LB IPAM](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/lb-ipam.rst), [L2 announcements](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/l2-announcements.rst), [Node IPAM](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/node-ipam.rst)
- [Egress Gateway](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/egress-gateway/egress-gateway.rst), [Local Redirect Policy](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/kubernetes/local-redirect-policy.rst)
- [Upgrade notes 1.20](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/operations/upgrade-current.inc), [Gateway API](https://github.com/cilium/cilium/tree/v1.20.2/Documentation/network/servicemesh/gateway-api)
- [v1.21.0-pre.3 BGP datapath waiter](https://github.com/cilium/cilium/blob/v1.21.0-pre.3/pkg/bgp/agent/datapath_waiter.go), [v1.21.0-pre.3 LB IPAM](https://github.com/cilium/cilium/blob/v1.21.0-pre.3/Documentation/network/lb-ipam.rst)

## Quiz

Test yourself with the [Part 11 quiz](../../quizzes/networking/cilium/11-bgp-lb-egress-edge-quiz.md).
