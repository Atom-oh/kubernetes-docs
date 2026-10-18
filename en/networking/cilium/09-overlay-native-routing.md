# Part 9: Overlay and Native Routing Deep Dive

> **Review baseline**: Cilium 1.20.2 (stable, 2026-09-16); Cilium CLI 0.20.1; Hubble CLI 1.20.2. Items marked **[1.21 pre-release]** come from v1.21.0-pre.3 and may change before GA.
> **Last Updated**: October 15, 2026

This chapter goes below the mode switch described in [Networking Models and VXLAN](03-networking.md). It explains what actually happens to a packet between two Pods on different nodes in tunnel mode and in native-routing mode, which BPF program does what, how security identity rides inside the encapsulation, how MTU and masquerading are decided, and which combinations the agent refuses to start with. It also places kube-proxy replacement, DSR, Maglev, socket-LB, host-routing, netkit, the bandwidth manager and encryption inside that same datapath, and ends with an EKS decision guide and a troubleshooting runbook.

Related chapters: [eBPF datapath internals](08-ebpf-datapath-internals.md) (program attach points, maps), [IPAM deep dive](10-ipam-deep-dive.md) (where Pod CIDRs come from), [BGP, load balancing, egress and edge](11-bgp-lb-egress-edge.md) (advertising Pod CIDRs, external LB), [mTLS, encryption and identity](12-mtls-encryption-identity.md) (WireGuard/IPsec details), [ClusterMesh, install and upgrade](13-clustermesh-install-upgrade.md).

## Table of Contents

1. Routing mode matrix
2. VXLAN vs Geneve in Cilium
3. How identity rides in the VNI
4. Control plane: from CiliumNode to a tunnel endpoint
5. Packet walks: same node, tunnel, native
6. Native routing: who provides the routes
7. Startup validations: hard failures and silent fallbacks
8. MTU math
9. Masquerading
10. Host routing: legacy vs BPF
11. Datapath device: veth vs netkit
12. Service load balancing in the datapath
13. Bandwidth manager, BBR and BIG TCP
14. Encryption interplay
15. VTEP and multicast (beta)
16. EKS decision guide
17. Inspection cheat sheet
18. Labs
19. Version Delta
20. Troubleshooting
21. Validation Limits and Sources

---

## 1. Routing mode matrix

`routingMode` accepts exactly two values in 1.20: `tunnel` (the default) and `native`. Everything else in this chapter is a consequence of that choice plus a few features that request a tunnel device on their own.

| Situation | Helm | Pod-to-Pod, different nodes | Who must route Pod CIDRs |
|---|---|---|---|
| Tunnel (default) | `routingMode: tunnel`, `tunnelProtocol: vxlan` (default) or `geneve` | BPF sets tunnel metadata, kernel `cilium_vxlan`/`cilium_geneve` encapsulates in UDP | Nobody; the underlay only needs node-to-node IP reachability plus UDP 8472/6081 |
| Native | `routingMode: native` | Packet leaves with its Pod IP, routed by the kernel (or by BPF FIB redirect with BPF host routing) | The network: cloud router/ENI, `autoDirectNodeRoutes`, BGP, or static routes |
| Native + feature-enabled tunnel | `routingMode: native` plus Egress Gateway or DSR with `dsrDispatch: geneve` | Ordinary Pod traffic is native; the feature creates a tunnel device for its own packets | Same as native; the tunnel only carries the feature's traffic |

The third row matters when you read `ip link`: a `cilium_geneve` device in a native-routing cluster is not a misconfiguration. In the code, Egress Gateway and DSR-with-Geneve are "tunnel enablers" that ask for the device even when `routingMode` is `native` (see the `tunnel` package in the agent, `pkg/datapath/tunnel/tunnel.go`).

Maturity (as stated by the 1.20.2 documentation): VXLAN/Geneve tunnel mode and native routing are stable. BGP is a route-advertisement mechanism, not a forwarding mode; see [BGP, load balancing, egress and edge](11-bgp-lb-egress-edge.md).

> **1.21 watch item.** The v1.21.0-pre.3 tree contains unfinished, undocumented scaffolding for another routing mode that is not exposed in the Helm chart. This chapter does not name or describe it. Re-read the 1.21 GA routing documentation before assuming `routingMode` still has two values there.

## 2. VXLAN vs Geneve in Cilium

Both are UDP encapsulations. Cilium uses a **flow-based (collect-metadata) kernel netdev** for either one, which means the kernel driver builds the outer headers from per-packet metadata that BPF attaches. Cilium does not build outer headers in BPF.

| Property | VXLAN | Geneve |
|---|---|---|
| Helm value | `tunnelProtocol: vxlan` (default) | `tunnelProtocol: geneve` |
| Default UDP destination port | 8472 | 6081 |
| Device | `cilium_vxlan` | `cilium_geneve` |
| Where identity travels | VNI (24 bit) | VNI (24 bit); same mechanism |
| Options/TLVs used by Cilium | none | only the DSR service address/port option (class `0x014B`, type `0x81`) |
| DSR support | not possible; agent refuses `dsr`/`hybrid` with VXLAN tunneling | `dsrDispatch: geneve` |
| Kernel config | `CONFIG_VXLAN` | `CONFIG_GENEVE` |

Both also need `CONFIG_FIB_RULES`. Port 8472 is the Linux kernel's historical VXLAN default, not the IANA-assigned 4789; Cilium keeps 8472 for compatibility. Override with `tunnelPort`, but note that changing the port recreates the device and causes a brief disruption, while an MTU change modifies the device in place.

Related tunables:

- `tunnelSourcePortRange: "0-0"` (default) lets the kernel driver pick the outer UDP source port range. A narrower range constrains the entropy underlay ECMP/filters see; it has no effect on identity.
- `underlayProtocol: auto|ipv4|ipv6` (added in 1.18). `auto` prefers IPv4 if enabled, else IPv6. An IPv6 underlay raises the tunnel overhead to 70 bytes and forbids XDP acceleration; Egress Gateway requires an IPv4 underlay.
- Switching `tunnelProtocol` deletes the other device and creates the new one, so plan it as a node-by-node disruptive change.

Security group/firewall requirement: UDP 8472 (VXLAN) or UDP 6081 (Geneve) between **all** nodes, plus TCP 4240 for health checks and ICMP echo. In AWS, express this with security-group-to-security-group references (the node SG referencing itself), never a CIDR open to the internet. WireGuard needs UDP 51871; IPsec needs ESP (IP protocol 50), which AWS security groups do not allow by default.

```yaml
# values: Geneve overlay (needed if you later want DSR dispatch via Geneve)
routingMode: tunnel
tunnelProtocol: geneve
```

## 3. How identity rides in the VNI

The 24-bit tunnel ID (the VNI) of every Cilium-encapsulated packet is the **source security identity** of the sending endpoint. This holds for VXLAN and for Geneve. Geneve options are not used for identity.

Rules from `bpf/lib/identity.h`, `bpf/lib/encap.h` and `bpf/bpf_overlay.c` (v1.20.2):

- In dual-stack clusters the reserved identities `world-ipv4` (9) and `world-ipv6` (10) are both sent as `world` (2); the receiver restores the right one from the inner L3 protocol.
- The `host` identity (1) is never sent. The sender rewrites it to `local-node`/`remote-node` (6) before encapsulation. A packet that arrives over the tunnel claiming `host` is dropped with `DROP_INVALID_IDENTITY`.
- The receiver still has the ipcache. Upstream describes identity carriage as an optimization that avoids one identity lookup on the remote node, not as the only source of truth. For traffic from remote nodes, `bpf_overlay.c` refines the identity via ipcache.

Consequences you can use:

1. On the wire the VNI equals the identity number you see in `cilium-dbg endpoint list` (column IDENTITY) or `cilium-dbg identity list`. Lab 1 verifies this.
2. Because the ingress policy decision runs on the destination node with the carried identity, ingress enforcement does not need to resolve the source IP again to a Pod.
3. VTEP integration (section 15) depends on this: external VTEP traffic must carry VNI 2 (`world`).

DSR in Geneve is the one place where options are used: the load-balancing node inserts a Geneve option holding the original service address and port so the backend node can rewrite replies. This adds 12 bytes, handled in the datapath (see section 8).

## 4. Control plane: from CiliumNode to a tunnel endpoint

Tunnel mode needs the sender to know, for any destination Pod IP, (a) its security identity and (b) the IP of the node that hosts it (the tunnel endpoint). Both live in one BPF LPM map:

```text
 Kubernetes API                       cilium-agent                       BPF
 --------------                       ------------                       ---
 CiliumNode (remote node IPs,   -->   node manager: node discovery
              podCIDRs)                 |- kernel route per remote PodCIDR
 CiliumEndpoint(Slice)/identity -->   ipcache listener                 cilium_ipcache_v2
   (Pod IP -> identity)                   writes {identity,   ------>  key: prefix
                                                  tunnel_endpoint,       value: identity,
                                                  encrypt key,                  tunnel endpoint,
                                                  flags}                        flags (skip_tunnel...)
```

- `cilium_ipcache_v2` is an LPM map. The value holds the identity, the tunnel endpoint (a remote node IPv4 or IPv6 address), the encryption key index and flags such as `skip_tunnel`. The listener only sets the tunnel endpoint when the host IP differs from the local node IP.
- For each remote PodCIDR the agent also installs a kernel route through `cilium_host` (`<podCIDR> via <cilium_host IP> dev cilium_host src <cilium_host IP> mtu <route MTU>`). The BPF encap decision uses the ipcache; the route is the fallback for host-originated traffic.
- **`cilium_tunnel_map` is gone.** In 1.17 it was still in BPF (`bpf/lib/encap.h`) and `cilium-dbg bpf tunnel list` dumped it. It was dropped from the datapath in 1.18 (the 1.18.14 BPF tree has no reference; the agent only unpins a leftover map), and the Go package was removed in 1.19. Tunnel endpoints live in the ipcache value, so inspect them with `cilium-dbg bpf ipcache list` (tunnel endpoint column), `cilium-dbg bpf nodeid list` and `cilium-dbg node list`.

## 5. Packet walks: same node, tunnel, native

Program names are from `bpf/bpf_lxc.c`, `bpf/bpf_overlay.c`, `bpf/lib/local_delivery.h` (v1.20.2). See [eBPF datapath internals](08-ebpf-datapath-internals.md) for attach mechanics.

### 5.1 Pod A (node 1) to Pod B (node 2), tunnel mode

```text
 node 1                                                          node 2
 ------                                                          ------
 Pod A eth0
   |  (veth/netkit peer on host)
   v
 [bpf_lxc: cil_from_container]
   1. service DNAT (socket-LB at connect(), or lb4_local per packet)
   2. conntrack lookup (cilium_ct4_global)
   3. ipcache lookup of dst -> dst identity + tunnel endpoint (node 2)
   4. egress policy (per-endpoint policy map, by identity)
   5. dst not local -> TUNNEL_MODE branch:
        set tunnel key { id = src identity, remote = node 2 IP }
        (bpf_skb_set_tunnel_key), redirect to ifindex of cilium_vxlan
   v
 [cilium_vxlan  (flow-based netdev)]
   cil_to_overlay on its egress: identity mark, SNAT handling,
   EDT bandwidth (if bandwidth manager is on)
   kernel vxlan driver builds outer Eth/IP/UDP(8472)/VXLAN(VNI)
   v
 NIC  ==== underlay IP network, UDP 8472 ====>  NIC
                                                  |
                                                  v
                                       kernel vxlan driver decapsulates
                                                  v
                                       [cilium_vxlan ingress: cil_from_overlay]
                                         validate ethertype, read tunnel key
                                         -> src_sec_identity
                                         tail call IPV4_FROM_OVERLAY (handle_ipv4):
                                           VTEP source check (must be world)
                                           remote-node identity refinement (ipcache)
                                           lookup destination endpoint
                                           ipv4_local_delivery(from_tunnel=true)
                                         tail call cilium_call_policy:
                                           ingress policy of Pod B using the carried identity
                                         redirect into Pod B's netns (redirect_peer with veth
                                           when BPF host routing is active)
                                                  v
                                                Pod B eth0
```

Key points:

- **The kernel encapsulates, BPF steers.** BPF sets the tunnel key (`BPF_F_ZERO_CSUM_TX`, TTL 64) and redirects to the tunnel device. This corrects a common simplification ("eBPF encapsulates the packet itself").
- Encryption is applied **after** encapsulation (IPsec since 1.18; WireGuard is a separate device), so the physical NIC sees ESP or WireGuard, not VXLAN, when encryption is on.
- Reply traffic returns symmetrically using the conntrack entry; the destination node encapsulates with Pod B's identity as the VNI.
- Pod traffic to a **remote node** address is not sent through the tunnel. In tunnel mode it is masqueraded (section 9).

### 5.2 Same node

`__lookup_ip4_endpoint` finds the destination local endpoint; `ipv4_local_delivery` tail-calls `cilium_call_policy` (ingress policy of the destination) and delivers by `bpf_redirect_peer` (veth with BPF host routing) or `bpf_redirect`. With netkit, Pod to Pod uses a plain `redirect` from egress to ingress. There is no encapsulation.

### 5.3 Pod A to Pod B, native routing

Steps 1-4 are identical. Step 5 does not tunnel:

- With **BPF host routing** (default when KPR and BPF masquerade are in place), `fib_redirect_v4` does a FIB lookup and redirects out of the NIC directly (`bpf_redirect_neigh` style), bypassing netfilter and the upper stack.
- With **legacy host routing**, the program returns `CTX_ACT_OK` (pass to stack) and the Linux kernel routes the packet using whatever routes exist: AWS ENI/per-endpoint routes, `autoDirectNodeRoutes`, BGP-learned routes, or a cloud router.

The outer network sees raw Pod IPs, which is why it must be able to route them and why anti-spoofing checks (for example the EC2 source/destination check on non-ENI instances) and security groups must permit them. On ENI-backed Pod IPs the VPC itself owns the addresses.

## 6. Native routing: who provides the routes

`routing-mode: native` hands non-local packets to the kernel and Cilium enables IP forwarding. Cilium does not teach the network where Pod CIDRs live; one of these does:

| Route provider | Helm | Notes |
|---|---|---|
| Cloud fabric | `eni.enabled` (AWS), `gke.enabled`, Azure IPAM | Pod IPs are native to the cloud network; per-endpoint routes (`enable-endpoint-routes`) are set by the chart |
| Direct node routes | `autoDirectNodeRoutes: true` | Installs `<remote podCIDR> via <remote node IP>`; all nodes must share one L2 segment |
| BGP | Cilium BGP control plane or external daemon | See [chapter 11](11-bgp-lb-egress-edge.md) |
| Static routes | none | Operator-managed |

`directRoutingSkipUnreachable` (default false) skips installing direct routes to nodes that are not on-link; it **requires** `autoDirectNodeRoutes` or the agent exits. It is not a tunnel fallback.

Helm guard: with native routing and `enableIPv4Masquerade` set to a truthy value, `helm template` fails with "ipv4NativeRoutingCIDR must be set when routingMode is native" unless one of these holds: `ipam.mode` is `eni` or `alibabacloud`, ip-masq-agent is enabled, or `nativeRoutingCIDRFromClusterPool: true` (new in 1.20; requires `ipam.mode=cluster-pool` with exactly one pool CIDR). The chart default for `enableIPv4Masquerade` is null (the agent's own default is true), so leaving it unset does **not** trip the guard even though the agent then masquerades. The IPv6 guard works the same way with `ipv6.enabled`, `enableIPv6Masquerade` (chart default true) and `ipv6NativeRoutingCIDR`.

```yaml
# values: native routing in a single L2 segment
routingMode: native
autoDirectNodeRoutes: true
ipv4NativeRoutingCIDR: 10.244.0.0/16   # must cover all Pod CIDRs
ipam:
  mode: cluster-pool
  operator:
    clusterPoolIPv4PodCIDRList: ["10.244.0.0/16"]
```

Native-routing CIDR semantics: destinations inside it are not masqueraded and are handed to the stack. If you do not set it, the default is the local node's PodCIDR. For ENI/Azure/AlibabaCloud the operator derives it from the cloud (the primary VPC CIDR only); if you specify a value it must be contained in a VPC CIDR or the agent fails with "None of the VPC CIDRs contains the specified native routing CIDR".

### AWS ENI datapath (how it routes)

With ENI IPAM the Pod IP is a secondary IP or prefix on an ENI. The agent installs per-endpoint routes and two ip rules per Pod IP: an ingress rule `to <podIP> lookup main` (priority 20, `RulePriorityIngress`) and an egress rule `from <podIP> lookup <ENI table>` (priority 111, `RulePriorityEgressv2`; the older priority 110 is used only in Azure IPAM mode). The `to <VPC CIDR>` selector is added to the egress rule (one rule per VPC CIDR) only when masquerade is on; ENI has masquerade off by default, so by default the egress rule has no `to` selector. The ENI table holds a default route via the ENI subnet's router. The router IP is taken from the ENI address space so ICMP packet-too-big messages can be generated. The operator has needed `ec2:DescribeRouteTables` since 1.18. Addressing details: [IPAM deep dive](10-ipam-deep-dive.md).

## 7. Startup validations: hard failures and silent fallbacks

Operators lose time because some bad combinations stop the agent while others only log a line and run with a weaker datapath. Know which is which.

### Hard failures (agent exits or Helm render fails)

| Configuration | Result |
|---|---|
| `routingMode: tunnel` + `autoDirectNodeRoutes: true` | Fatal: "auto-direct-node-routes cannot be used with tunneling. Packets must be routed through the tunnel device." (1.20.2) |
| `ipam: eni` + tunnel | Fatal: "Cannot specify IPAM mode eni in tunnel mode." |
| `directRoutingSkipUnreachable` without `autoDirectNodeRoutes` | Fatal |
| DSR or hybrid mode + VXLAN tunnel | Error: Node Port `dsr` mode cannot be used with `vxlan` tunneling |
| Tunnel + DSR/hybrid without `dsrDispatch: geneve` | Error: requires `geneve` dispatch |
| `dsrDispatch: geneve` without `tunnelProtocol: geneve` | Error: requires Geneve tunnel protocol |
| XDP acceleration + IPv6 underlay | Error |
| Native routing + `enableIPv4Masquerade` set truthy + no native CIDR and no exemption | Helm template failure (an unset value, chart default null, does not fail) |
| `bpf.datapathMode: netkit` (explicit) with unmet preconditions | Fails hard (section 11) |
| BBR without kernel 5.18 `skb_set_tstamp`, or BBR for Pods without BPF host routing | Agent error (section 13) |
| BIG TCP without BPF host routing / KPR / BPF masquerade, or with IPsec or DSR IPIP | Startup error |
| `enable-remote-node-masquerade` without BPF masquerade | Error |
| `ip-masq-agent` without BPF masquerade | Error |

With VXLAN and the per-service annotation mode (`bpf.lbModeAnnotation=true`), only `dsrDispatch: ipip` is accepted by the validator; the default global mode must stay `snat`.

**[1.21 pre-release]** The `autoDirectNodeRoutes` message reads "auto-direct-node-routes requires native routing mode." The condition is still "tunneling is enabled".

### Silent fallbacks (agent runs, weaker datapath)

| Configuration | What happens |
|---|---|
| BPF host routing (default) but iptables masquerade, or KPR off | Logs "BPF host routing requires bpf-masquerade / kube-proxy-replacement ... Falling back to legacy host routing"; legacy routing is used |
| `bpf.datapathMode: auto` and netkit preconditions unmet | Logs "datapath autodiscovery failed, reverting from netkit to veth"; veth is used |
| Bandwidth manager + IPsec | Manager disabled with a warning |
| BIG TCP on an unsupported kernel | Warns and disables |
| Multicast enabled on a kernel without the needed BPF helper | Logs "Disabled support for BPF Multicast" and stays off |
| CNI chaining | Chart forces legacy host routing and disables no-conntrack iptables rules |

The asymmetry is deliberate in the code: host routing and `auto` are "best effort", while features you ask for by name (netkit, BBR, BIG TCP) fail if they cannot be delivered. After any change, verify the effective state (section 17) instead of trusting values.

## 8. MTU math

**Detection.** The base MTU is the minimum MTU over the native devices Cilium selected, excluding `cilium_vxlan`, `cilium_geneve`, IPIP devices and dummy devices. `MTU: 0` (default) means "detect"; a non-zero Helm `MTU` is the **underlying network MTU**, not the final Pod MTU. A CNI-config MTU also overrides. Local detection does not prove the path MTU across routers.

**Pod device vs route MTU.** The Pod veth/netkit device MTU equals the base MTU; the route MTU inside the Pod is the base minus overhead. So `ip link` in a Pod can show 1500 while `ip route` shows `mtu 1450`.

Overheads from `pkg/mtu/mtu.go` (v1.20.2):

| Component | Bytes | Composition |
|---|---|---|
| Tunnel, IPv4 underlay | 50 | 20 IP + 8 UDP + 8 VXLAN + 14 inner Ethernet |
| Tunnel, IPv6 underlay | 70 | 40 IP + 8 + 8 + 14 |
| IPsec (128-bit GCM, default key size) | 77 | adjusted by key size |
| WireGuard | 95 | constant |
| Geneve DSR option | 12 | applied in the datapath, not in route MTU |

| Scenario (1500 underlay) | Route MTU in Pod | Computation |
|---|---|---|
| Native, no encryption | 1500 | base |
| Tunnel VXLAN, IPv4 underlay | 1450 | 1500 - 50 |
| Tunnel VXLAN, IPv6 underlay | 1430 | 1500 - 70 |
| Native + WireGuard | 1405 | 1500 - 95 |
| Native + IPsec | 1423 | 1500 - 77 |
| Tunnel + IPsec | 1373 | 1500 - (50 + 77) |
| Tunnel + WireGuard | 1355 | 1500 - (95 + 50) |

The numbers are computed from the constants and the `getRouteMTU` function; they were not measured on a cluster. With jumbo frames the overhead is the same absolute number, so it is proportionally much smaller (a 9001 underlay yields 8951 with VXLAN over IPv4).

Notes:

- **Geneve DSR** adds the 12-byte option. Because the option is inserted by the load balancing node, large packets can exceed the path MTU; TCP hybrid mode (DSR only for TCP SYN metadata, SNAT for UDP) exists partly to limit this.
- **`pmtuDiscovery.enabled`** (default false) sends ICMP fragmentation-needed to clients. `pmtuDiscovery.packetizationLayerPMTUDMode` (new in 1.19; values `always|blackhole|disabled|unset`; default `blackhole`) controls kernel RFC 4821 probing in Pod netns. Set `disabled` when you know the MTU.
- **CNI chaining**: `cni.enableRouteMTUForCNIChaining: true` pushes the route MTU into the chained plugin's Pods (needed, for example, for WireGuard over aws-cni).
- **IPv4/IPv6 fragments** are tracked by default (`enable-ipv4-fragment-tracking`, `enable-ipv6-fragment-tracking`; the table is `bpf-fragments-map-max`, default 8192; marked beta upstream). See [L2/L7 networking](05-l2-l7-networking.md).
- **XDP** on AWS requires an MTU low enough for ENA native XDP (upstream's example cites 3498); jumbo-frame nodes cannot use it without lowering the MTU.

Verify from a Pod: `kubectl exec <pod> -- ip route` and `ip link`; test with `ping -M do -s <size>` in both directions.

## 9. Masquerading

Masquerading rewrites the source of Pod traffic leaving the cluster to a node IP. Cilium has two implementations.

| | iptables (default) | BPF (`bpf.masquerade: true`) |
|---|---|---|
| Needs | iptables/ipset modules | KPR (BPF NodePort), device detection |
| Scope | All traffic leaving through a non-Cilium device unless restricted with `egressMasqueradeInterfaces` | Devices selected by detection or `devices`; exclusions by CIDR |
| Host routing | Forces legacy host routing (silent fallback) | Compatible with BPF host routing |
| Protocols | everything netfilter handles | TCP, UDP, ICMP (echo, echo-reply, frag-needed); IPv4 production, IPv6 beta |
| Extras | `enableMasqueradeRouteSource` | ip-masq-agent, `enableRemoteNodeMasquerade` |
| Port range | kernel | NodePort max + 1 .. 65535 (`bpf/lib/nat.h`); NAT table `bpf.natMax` default 524288 |

Defaults: `enableIPv4Masquerade: true`, except it defaults to **false** when `eni.enabled=true` (since 1.18). `enableIPv6Masquerade: true`; **[1.21 pre-release]** it becomes "true unless ENI IPAM". `egressMasqueradeInterfaces` only affects iptables masquerade, so it does nothing in an ENI profile with masquerade off.

### BPF masquerade decision order

From `bpf/lib/nat.h` (v1.20.2), evaluated per egress packet in this order:

1. Egress Gateway policy matches: SNAT to the gateway IP.
2. Destination in the SNAT exclusion CIDR (the native-routing CIDR, else the local PodCIDR): no masquerade.
3. Local endpoint flagged `SKIP_MASQ` (multi-pool IPAM): no masquerade.
4. Destination in `cilium_ipmasq_v4` (ip-masq-agent, LPM): no masquerade.
5. Destination is a **remote node** identity:
   - `enable-remote-node-masquerade=true`: SNAT.
   - else native routing: no masquerade.
   - else tunnel mode: SNAT, unless the ipcache entry carries `skip_tunnel`.
6. Source is a local endpoint: SNAT to the node address of the egress device; otherwise pass.

Two consequences. First, Pod to remote node traffic keeps its Pod IP in native routing but is masqueraded in tunnel mode: this changes what host firewalls and node-level `NetworkPolicy`/host policy see. Second, upstream's masquerading page words step 5 loosely ("packets destined to other cluster nodes" are excluded); the BPF code is the source for the table above.

`enable-remote-node-masquerade` (new in 1.19) has no dedicated Helm key in 1.20.2. Set it through `extraConfig: {enable-remote-node-masquerade: "true"}`. It requires BPF masquerade and weakens host-firewall ingress enforcement because the source becomes a node address.

### ip-masq-agent

```yaml
kubeProxyReplacement: true
bpf:
  masquerade: true
ipMasqAgent:
  enabled: true
  config:
    nonMasqueradeCIDRs: [10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16]
    masqLinkLocal: false
```

The chart renders a ConfigMap named `ip-masq-agent` with key `config` (JSON) in the release namespace; the agent watches the mounted file with fsnotify. Empty config means built-in non-masquerade CIDRs: 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16, 100.64.0.0/10, 192.0.0.0/24, 192.0.2.0/24, 192.88.99.0/24, 198.18.0.0/15, 198.51.100.0/24, 203.0.113.0/24, 240.0.0.0/4, plus 169.254.0.0/16 unless `masqLinkLocal` and fe80::/10 unless `masqLinkLocalIPv6`. The maps `cilium_ipmasq_v4/v6` hold 16384 entries each. With ip-masq-agent on, a native-routing CIDR is no longer mandatory.

Verify: `cilium-dbg status | grep Masquerading` (for example `BPF (ip-masq-agent) [eth0] <cidr> [IPv4: Enabled, IPv6: Disabled]`) and `cilium-dbg bpf ipmasq list`.

Known limits: BPF masquerade does not masquerade Pod traffic to a node's External IP (upstream issue 17177). **[1.21 pre-release]** `nodePort.extendedNATPortRange` (`--node-port-nat-range-ext`) extends the SNAT port range for large NAT tables.

Incompatibilities enforced at start: `--masquerade-interfaces`-style device selection and `enable-masquerade-to-route-source` cannot be combined with BPF masquerade.

## 10. Host routing: legacy vs BPF

| | Legacy host routing | BPF host routing |
|---|---|---|
| Flag | `bpf.hostLegacyRouting: true` | default when prerequisites hold |
| Path | Pod -> veth -> host netfilter/routing -> NIC | Pod -> BPF FIB lookup -> NIC; `redirect_peer` into Pod netns |
| netfilter/iptables | in path | bypassed |
| Needs | nothing special | KPR true and BPF masquerade (otherwise silent fallback) |
| Required by | n/a | netkit, BBR for Pods, BIG TCP, dynamic egress routing by FIB table annotation |

BPF host routing skips netfilter and the upper stack, so anything that relies on netfilter in the host namespace breaks. Known incompatibilities: Istio sidecar redirection (upstream issue 36022) and netfilter-reliant provider features such as GKE Workload Identity. The workaround is `bpf.hostLegacyRouting: true` or Local Redirect Policy. In 1.19+ host routing is automatically available with IPsec when KPR and BPF masquerade are on; the kernel must include the fix for CVE-2025-37959.

In legacy mode, reduce conntrack cost with `installNoConntrackIptablesRules: true` (native routing, IPv4, KPR with socket-LB, BPF masquerade). The chart forces it off for eni, azure, gke and CNI chaining.

Check the `Host:` field of the `Routing:` line in `cilium-dbg status` (`Host: BPF` or `Host: Legacy`). Cilium 1.20.2 prints no separate "Host Routing" line.

## 11. Datapath device: veth vs netkit

`bpf.datapathMode` accepts `veth` (default), `netkit`, `netkit-l2` and, new in 1.20, `auto`.

- `netkit` (L3 mode, no ARP, the variant upstream recommends) and `netkit-l2` attach BPF inside the peer and use tcx; supports BIG TCP. Documented as **beta** in 1.20.2; kernel 6.8+ (`CONFIG_NETKIT`) per the docs, while a code comment says 6.7+. Treat the docs as the floor and the runtime probe as the final word.
- Preconditions (`canUseNetkit`): netkit probe passes, no `bpf.hostLegacyRouting`, BPF masquerade enabled (not iptables), `kubeProxyReplacement: true`, no `bpf.tproxy` (incompatible since 1.19), and with `enableEndpointRoutes` the driver must support the scrub attribute (kernel 6.13 or backports).
- Explicit `netkit`/`netkit-l2` with unmet preconditions **fails hard**; `auto` demotes to veth with a warning and `cilium-dbg status` reports "Device Mode: netkit [Configured: auto]" style output showing configured versus operational mode.
- If a node already has veth Pods, switching (even with `auto`) errors. Use per-node configuration (`CiliumNodeConfig`) or drain the node first.

```yaml
# values: safe netkit probe
bpf:
  datapathMode: auto
  masquerade: true
kubeProxyReplacement: true
routingMode: native
```

Verify with `cilium-dbg status | grep -E "Device Mode|Routing|Attach Mode"` (host routing shows as `Host: BPF|Legacy` on the `Routing:` line). Upstream states veth may be deprecated once kernels are common and that the default may change; do not assume the default is permanent.

## 12. Service load balancing in the datapath

Where each service feature sits relative to the Pod-to-Pod walk in section 5:

```text
 client Pod -> connect()  --[socket-LB: cgroup connect4/sendmsg/recvmsg hooks]--> backend IP:port chosen
                |                                         (E/W, ClusterIP; before any packet exists)
                v
 packet leaves Pod -> bpf_lxc (lb4_local if socket-LB did not already translate)
                |
 external client -> NIC -> [XDP, optional: LB at driver level] -> bpf_host (from-netdev)
                       -> NodePort/LB lookup -> backend selection: random or Maglev
                       -> forward mode: SNAT, DSR (opt/ipip/geneve) or hybrid
                       -> backend local: deliver; remote: native route / tunnel (+Geneve option for DSR)
```

**kube-proxy replacement (KPR).** A boolean: `kubeProxyReplacement: true|false` (strict/partial are gone). `true` forces socket-LB on. Set `k8sServiceHost`/`k8sServicePort` because there is no kube-proxy to resolve the API ClusterIP. It covers ClusterIP, NodePort, LoadBalancer, externalIPs and hostPort, and works in tunnel and native mode. KPR=false still does per-packet ClusterIP load balancing. Removed in 1.19: `--enable-node-port`, `--enable-host-port`, `--enable-external-ips`; removed in 1.20: `--node-port-mode`, `--node-port-algorithm` (use `loadBalancer.mode`/`loadBalancer.algorithm`).

**Socket-LB.** `socketLB.enabled` (on with KPR) hooks `connect`/`sendmsg`/`recvmsg`/`getpeername`. `socketLB.hostNamespaceOnly: true` restricts it to the host namespace, needed for Istio sidecars, KubeVirt, Kata and gVisor (forced when `gatewayAPI.enabled`). `socketLB.terminatePodConnections` (default true) needs kernel `CONFIG_INET_DIAG*`. **1.20 behavior change**: with socket-LB off or `hostNamespaceOnly=true`, Pod to NodePort connections are DNAT'd at the client Pod's egress, so egress NetworkPolicy must allow the backends, not just the NodePort.

**Algorithm.** `loadBalancer.algorithm: random|maglev`. Maglev builds a per-service lookup table in the map-in-map `cilium_lb4_maglev` / `cilium_lb6_maglev` and hashes the 5-tuple (source port zeroed when ClientIP affinity is on) modulo the table size. It applies to north/south traffic only; east/west via socket-LB bypasses it. `maglev.tableSize` must be one of 251, 509, 1021, 2039, 4093, 8191, 16381, 32749, 65521 or 131071 (default 16381, sized for roughly 160 backends per service); `maglev.hashSeed` must be identical on all agents.

```bash
SEED=$(head -c12 /dev/urandom | base64 -w0)   # generate once, store it in your values/secret store
helm upgrade cilium cilium/cilium --version 1.20.2 -n kube-system --reuse-values \
  --set kubeProxyReplacement=true \
  --set loadBalancer.algorithm=maglev \
  --set maglev.tableSize=65521 \
  --set maglev.hashSeed=$SEED
```

Per-service override: `bpf.lbAlgorithmAnnotation=true` plus annotation `service.cilium.io/lb-algorithm: maglev` (creation time only). New in 1.20: EndpointSlice annotation `service.cilium.io/weight` (0-65535, Maglev only; 0 means maintenance).

**Forwarding mode.** `loadBalancer.mode: snat|dsr|hybrid`.

- `snat`: the node that received the request rewrites the source, so replies return through it.
- `dsr`: the backend replies directly to the client; the service IP/port is carried to the backend. `hybrid` uses DSR for TCP (service address encoded only in the SYN) and SNAT for UDP.
- Dispatch (`loadBalancer.dsrDispatch`, default `opt`): carrying method.

| `dsrDispatch` | Native routing | Tunnel (Geneve) | Tunnel (VXLAN) |
|---|---|---|---|
| `opt` (IP option / IPv6 destination option) | yes | no | no |
| `geneve` | yes (creates the Geneve device) | yes | no (VXLAN cannot do DSR) |
| `ipip` (documented in 1.20) | yes | no | validator exception in annotation mode only; not a documented working setup |

IPIP creates `cilium_ipip4/6`, requires the service port to equal the target port, supports an optional RSS source CIDR (`--bpf-lb-rss-ipv4-src-cidr`), and is incompatible with BIG TCP. Cloud fabrics may drop packets carrying IP options (`opt`); prefer `geneve` or `ipip` there. On AWS the EC2 source/destination check must be disabled for DSR. Tunnel mode with DSR therefore requires `tunnelProtocol: geneve` and `dsrDispatch: geneve`.

```yaml
# values: tunnel mode, kube-proxy-free, DSR via Geneve
routingMode: tunnel
tunnelProtocol: geneve
kubeProxyReplacement: true
k8sServiceHost: <API_SERVER_FQDN>      # host only, no scheme
k8sServicePort: 443
loadBalancer:
  mode: dsr
  dsrDispatch: geneve
```

Annotation mode: `bpf.lbModeAnnotation=true` makes `service.cilium.io/forwarding-mode: dsr|snat` configurable per Service and requires `loadBalancer.dsrDispatch` to be set explicitly. Any LoadBalancer Service you annotate on EKS must stay internal (`service.beta.kubernetes.io/aws-load-balancer-scheme: internal`); publish externally only through CloudFront and a VPC origin.

**XDP acceleration.** `loadBalancer.acceleration: disabled|native|best-effort`. It needs a native-XDP driver on all selected devices (else use `best-effort`); only the direct-routing device is accelerated; it is incompatible with an IPv6 underlay and auto-enables L2 neighbor discovery. Packets bounced back at XDP are invisible to `tcpdump`. N/S traffic accelerated by XDP or using non-Geneve DSR is not encrypted by WireGuard.

**Known issues worth knowing:** reverse socket map exhaustion, NFS/SMB kernel patches for socket-LB, backend-termination races (add a `preStop` sleep), TCP Fast Open breaking DSR, and an rp_filter warning for multi-device DSR. Cross-reference [L2/L7 networking](05-l2-l7-networking.md) for the comparison tables.

## 13. Bandwidth manager, BBR and BIG TCP

**Bandwidth manager.** `bandwidthManager.enabled` (default false), `bandwidthManager.bbr`, `bandwidthManager.bbrHostNamespaceOnly`. Annotations `kubernetes.io/egress-bandwidth` (EDT with FQ, applied at the Pod's host-side device and again at the tunnel device egress) and `kubernetes.io/ingress-bandwidth` (BPF token bucket). The values are Kubernetes quantities in **bits**: `"10M"` is 10 Mbit/s, not 10 MB/s. It is per Pod, not per replica set.

Side effects: sets host sysctls `net.core.default_qdisc=fq` and `net.ipv4.tcp_congestion_control` (`cubic` or `bbr`), raises baselines for `netdev_max_backlog` (>= 1000), `somaxconn` and `tcp_max_syn_backlog` (>= 4096), and installs FQ on external devices. Preconditions: BBR needs kernel 5.18; BBR for Pods needs BPF host routing (else error unless `bbrHostNamespaceOnly`); with IPsec the manager is silently disabled. Existing Pods keep their old congestion control; BBR applies to new Pods.

Verify: `cilium-dbg status | grep BandwidthManager` (for example `EDT with BPF [BBR] [eth0]`) and `cilium-dbg bpf bandwidth list`.

**BIG TCP.** `enableIPv4BIGTCP`, `enableIPv6BIGTCP` (both false). Kernels: IPv6 5.19+, IPv4 6.3+; NIC drivers listed upstream include mlx4, mlx5 and ice. Needs BPF host routing, KPR and BPF masquerade; incompatible with IPsec and DSR IPIP. Raises gso/gro max size to 192 KB without changing MTU; restart Pods after toggling. Upstream wording says "tunneling disabled", but the code permits BIG TCP over VXLAN/Geneve only when a kernel probe for UDP-tunnel BIG TCP passes; otherwise it fails with "BIG TCP in tunneling mode requires pending kernel support". The practical advice is native routing.

**Upstream's recommended performance profile** (not an in-place upgrade; use per-node configuration):

```bash
helm upgrade --install cilium cilium/cilium --version 1.20.2 -n kube-system \
  --set routingMode=native \
  --set bpf.datapathMode=netkit \
  --set bpf.masquerade=true \
  --set bpf.distributedLRU.enabled=true \
  --set bpf.mapDynamicSizeRatio=0.08 \
  --set ipv6.enabled=true --set enableIPv6BIGTCP=true \
  --set ipv4.enabled=true --set enableIPv4BIGTCP=true \
  --set kubeProxyReplacement=true \
  --set bpfClockProbe=true
```

Add `bandwidthManager.enabled=true` and `bandwidthManager.bbr=true` if you want the bandwidth manager. Note the interplay with section 7: netkit and BIG TCP in this profile require BPF host routing, so the profile only works with KPR and BPF masquerade as listed.

## 14. Encryption interplay

Only the datapath consequences are covered here; see [chapter 12](12-mtls-encryption-identity.md) for key management.

| | WireGuard | IPsec |
|---|---|---|
| Transport | UDP 51871 | ESP (IP protocol 50) |
| With tunnel mode | Double encapsulation: VXLAN/Geneve first, then WireGuard | Encryption applied **after** overlay encapsulation (always, since 1.18) |
| Route MTU @1500 | tunnel 1355, native 1405 | tunnel 1373, native 1423 |
| Strict mode | `encryption.strictMode.ingress.enabled` (1.19+) requires WireGuard (not IPsec) and is supported in both tunnel and native routing; `strictMode.egress.allowRemoteNodeIdentities` is an egress option, required when tunneling is used or when node and Pod CIDRs overlap in direct routing; `strictMode.egress.*` replaced the old keys, which were removed in 1.20 | n/a |
| Bandwidth manager | works | silently disabled |
| BIG TCP | works with caveats | startup error |
| Chaining | no encryption supported | no encryption supported |

Other facts: IPsec `encryptedOverlay` was a no-op from 1.18 and was removed in 1.20. IPsec requires `ipv4NativeRoutingCIDR` in any direct-routing configuration, supports fewer than 65535 nodes, and decrypts on a single core per tunnel. N/S traffic accelerated by XDP, or DSR other than Geneve, is not covered by WireGuard; DSR over Geneve is.

When capturing, remember the order: on the NIC you see UDP 51871 or ESP, not VXLAN/Geneve; on the Pod's host-side device you see plaintext. Capture at both points before concluding that encryption or encapsulation is missing.

## 15. VTEP and multicast (beta)

**VTEP integration** lets Pods exchange traffic with external VXLAN endpoints (for example a hardware VTEP).

- Helm: `vtep.enabled`, `vtep.endpoint`, `vtep.cidr`, `vtep.mask`, `vtep.mac`; `vtep.endpoint`, `vtep.cidr` and `vtep.mac` are space-separated lists of equal length (one entry per VTEP), while `vtep.mask` is a single mask applied to all CIDRs.
- Limits: at most 8 VTEPs; IPv4 only; sync interval `--vtep-sync-interval` (1m); not combined with IPsec; the VTEP device MTU is hard-coded to 1500 - 50.
- The VTEP device must use **VNI 2** (`world`). BPF drops overlay packets from a VTEP source address that carry a non-world identity (`DROP_INVALID_VNI`). On egress, `bpf_lxc` looks up `cilium_vtep_map` and encapsulates with destination identity `world`.
- Inspect with `cilium-dbg bpf vtep list`. Whether VTEP works over Geneve is not documented or validated; the documented setup is tunnel mode with VXLAN.

**Multicast.**

- Enable with `cilium config set multicast-enabled true` or `extraConfig: {multicast-enabled: "true"}`; there is no dedicated Helm value in 1.20.2.
- The docs require VXLAN mode and kernel 5.10+ on amd64 or 6.0+ on arm64. The code additionally probes for the `bpf_for_each_map_elem` helper (Linux 5.13+); if it is missing the agent logs a "Disabled support for BPF Multicast" message and stays off. Which rule wins on 5.10-5.12 is not verified here.
- IPv4 only, IGMP v2/v3 handled in `bpf_lxc`, limits of 1024 groups x 1024 subscribers, not with IPsec, and it must be configured on every node (`cilium-dbg bpf multicast group add <group>` and `... subscriber add <group> <remote CiliumInternalIP>`, or cluster-wide with `cilium multicast add --group-ip` as shown in upstream `multicast.rst`; that CLI command was not verified against the cilium-cli source).

## 16. EKS decision guide

| Option | Configuration | Choose when | Watch out for |
|---|---|---|---|
| **Cilium ENI IPAM** (replaces VPC CNI) | `eni.enabled=true`, `ipam.mode=eni`, `routingMode: native` (default with ENI), operator permissions via IRSA/Pod Identity, taint `node.cilium.io/agent-not-ready=true:NoExecute` | Pods need VPC-routable IPs, no SNAT inside the VPC, security groups/flow logs by Pod IP | Tunnel is forbidden with ENI; IPv4 masquerade defaults to off (1.18+); Pod density bound by ENI/IP capacity; operator needs `ec2:DescribeRouteTables`; AWS support covers VPC CNI on EC2 nodes only |
| **Overlay on EKS** | `ipam.mode=cluster-pool`, `routingMode: tunnel`, `eni.enabled=false` | Pod IP space is scarce in the VPC, or you want tunnel features | Pod IPs are not VPC-routable, so the managed control plane cannot reach them: **webhook backends (admission, conversion) must use `hostNetwork`**. Node SG: self-reference for UDP 8472 (or 6081). MTU 1450 (8951 on a 9001 underlay) |
| **VPC CNI chaining** | `cni.chainingMode=aws-cni`, `cni.exclusive=false`, `enableIPv4Masquerade=false`, `routingMode=native` | Keep VPC CNI IPAM and ENIs; add Cilium policy, LB and Hubble | Chart forces legacy host routing and disables no-conntrack iptables; no IPsec/WireGuard; limited L7; aws-node 1.11.2 or newer; restart Pods after enabling |
| **EKS Auto Mode / Fargate** | n/a | n/a | Alternate CNIs are not supported |
| **EKS Hybrid Nodes** | Cilium is a supported CNI | On-prem nodes | Pod CIDRs must be routable for webhooks; see the EKS Hybrid Nodes section of this repository |

The overlay-webhook statement is derived from AWS's hybrid-nodes guidance (Pod CIDRs must be routable for webhooks) and from how the Kubernetes control plane calls webhooks; validate it in Lab 5 before relying on it.

Cilium ENI profile (the inert `egressMasqueradeInterfaces` key is intentionally omitted: it does nothing while masquerade is off):

```yaml
eni:
  enabled: true
ipam:
  mode: eni
routingMode: native
# enableIPv4Masquerade: true   # only if Pods must reach non-VPC destinations without a NAT gateway
```

VPC CNI chaining:

```bash
helm upgrade --install cilium cilium/cilium --version 1.20.2 -n kube-system \
  --set cni.chainingMode=aws-cni \
  --set cni.exclusive=false \
  --set enableIPv4Masquerade=false \
  --set routingMode=native
```

EKS notes:

- Delete the `aws-node` DaemonSet before installing Cilium as the CNI (aws-node flushes routing tables) or restart Pods afterward.
- Secondary VPC CIDRs (for example 100.64.0.0/16): the autodetected native-routing CIDR is the **primary** VPC CIDR only. If masquerade is on and Pods live in a secondary range, set `ipv4NativeRoutingCIDR` to a covering range and check `cilium-dbg status | grep Masquerading`. This is derived from the code and not tested.
- ENI IPv6: `eni.rst` documents one /80 prefix per node and dual-stack subnets, while the EKS requirements page still says IPv4 only. Treat ENI IPv6 as unsettled upstream and confirm in your region.
- Source/destination check: documented as required to be disabled for DSR. For native routing on non-ENI EC2 it is the same constraint in principle (Pod IPs are not owned by the instance); this part is inference.
- Public path policy: only CloudFront reaches workloads, through an internal ALB/NLB behind a CloudFront VPC origin. Cilium examples here never need a public listener or a `0.0.0.0/0` rule.

## 17. Inspection cheat sheet

```bash
# Effective routing, device, host-routing, masquerade, KPR, bandwidth, BIG TCP, XDP
kubectl -n kube-system exec ds/cilium -c cilium-agent -- \
  cilium-dbg status --verbose | grep -E "Routing|Device Mode|Masquerading|KubeProxyReplacement|BandwidthManager|BIG TCP|XDP"

# Tunnel device (VNI mode, port, metadata-based)
ip -d link show cilium_vxlan        # or cilium_geneve
ip route | grep cilium_host         # remote PodCIDR routes (tunnel mode)

# Tunnel endpoints and node IDs (ipcache, not the old tunnel map)
cilium-dbg bpf ipcache list | grep -i <remote-node-ip>
cilium-dbg bpf nodeid list
cilium-dbg node list

# Identity numbers to compare with the VNI
cilium-dbg endpoint list
cilium-dbg identity list

# NAT and masquerade
cilium-dbg bpf nat list
cilium-dbg bpf ipmasq list

# Services
cilium-dbg service list
cilium-dbg bpf lb list
cilium-dbg bpf lb maglev list
cilium-dbg bpf socknat list

# Bandwidth, VTEP
cilium-dbg bpf bandwidth list
cilium-dbg bpf vtep list

# Datapath events
cilium-dbg monitor -v --type trace      # to-overlay / from-overlay trace points
cilium-dbg monitor --type drop

# Wire capture on the node (not on your laptop)
sudo tcpdump -nni any -c 50 'udp port 8472'      # Geneve: 'udp port 6081'
sudo tcpdump -nni <nic> -vv 'udp port 8472'       # -vv prints the VNI
```

`cilium-dbg status` prints a `Routing:` line similar to `Network: Tunnel [vxlan]  Host: BPF`. Commands that print a map's contents may differ in column layout between versions; do not script against the column positions.

## 18. Labs

Run these only on a disposable cluster (kind or a two-node EKS test cluster with self-referencing security groups). All were checked against upstream source and documentation; none were executed against a live cluster in this review. Expected results are described, not captured.

### Lab 1: Overlay anatomy and the VNI

**Prerequisites:** two schedulable Linux nodes, Cilium 1.20.2 with `routingMode: tunnel`, shell access on the nodes, UDP 8472 allowed between nodes.

1. `cilium-dbg status | grep Routing` on an agent: expect a tunnel network with the vxlan protocol.
2. `ip -d link show cilium_vxlan` on a node: a vxlan device with the flow-based (external) attribute and destination port 8472.
3. Start a server Pod on node 1 and a client Pod on node 2 (use nodeName or anti-affinity). Run `sudo tcpdump -nni <nic> -vv 'udp port 8472' -c 20` on the node while the client curls the server.
4. Note the `vni` in the decoded output. Compare it to the client Pod's identity from `cilium-dbg endpoint list` on node 2. Expect them to be equal for client-to-server packets and the server's identity for replies.
5. `helm upgrade ... --set tunnelProtocol=geneve`, restart agents, and observe that `cilium_vxlan` disappears, `cilium_geneve` appears, and the capture filter must change to port 6081.

**Cleanup/rollback:** set `tunnelProtocol` back to `vxlan` and restart agents. Changing the protocol recreates the device; expect brief connectivity loss between nodes while it happens.

### Lab 2: MTU with WireGuard over the tunnel

**Prerequisites:** Lab 1 cluster; UDP 51871 allowed between nodes (security-group self reference).

1. Enable `encryption.enabled=true`, `encryption.type=wireguard`; keep `MTU: 0`.
2. In a Pod run `ip route` and `ip link`. Expect the device MTU at the underlay value and a route MTU of 1355 on a 1500 underlay (95 + 50 overhead).
3. From one Pod run `ping -M do -s 1327 <other pod ip>` and `-s 1328`. Expect the first to succeed (1327 + 28 = 1355) and the second to fail with a fragmentation-needed style error.
4. `cilium-dbg status | grep Encryption` should report WireGuard.

**Cleanup:** disable encryption and restart agents; the route MTU returns to 1450 for new Pods (existing Pods keep their MTU until recreated).

### Lab 3: Masquerade decision tree

**Prerequisites:** KPR on, `bpf.masquerade=true`, a test echo server in the same VPC that logs the observed source IP, reachable only through security groups that reference the node SG.

1. Run Pod to echo server. Check the source observed: if the echo server IP lies outside the native-routing CIDR and ip-masq-agent list, it should be a node IP.
2. Enable `ipMasqAgent` with `nonMasqueradeCIDRs` containing the echo server's range, restart agents, repeat. Expect the Pod IP to be preserved (the VPC must be able to return traffic to Pod IPs; on overlay Pod IPs this will fail, which is the point).
3. `cilium-dbg bpf ipmasq list` lists the CIDRs; `cilium-dbg bpf nat list` shows active SNAT entries.
4. Pod to remote node: in native mode the source stays the Pod IP; in tunnel mode it is the node IP. Set `extraConfig: {enable-remote-node-masquerade: "true"}` and observe that native mode now masquerades too.

**Cleanup/rollback:** remove the ip-masq-agent block and the extraConfig key. Changing masquerade mode alters source addresses seen by firewalls; roll node by node.

### Lab 4: Kube-proxy-free service with Maglev and Geneve DSR

**Prerequisites:** a cluster installed without kube-proxy, `routingMode: tunnel`, `tunnelProtocol: geneve`, KPR true, `loadBalancer.mode: dsr`, `dsrDispatch: geneve`, `maglev` settings from section 12; a client host inside the VPC; a NodePort Service whose backend is on a different node than the one you contact. Use an internal network path only.

1. On the contacted node, `iptables-save | grep KUBE-SVC` should return nothing.
2. `cilium-dbg bpf lb list` shows the service; `cilium-dbg bpf lb maglev list` shows the lookup table.
3. Capture on the backend node with tcpdump on its NIC: the request arrives as Geneve (UDP 6081) carrying the DSR option; the reply leaves directly toward the client with the service IP as source.
4. Verify that setting `tunnelProtocol: vxlan` with `loadBalancer.mode: dsr` makes the agent fail at start (do this on a throwaway cluster, then revert).

**Cleanup:** revert the Helm values. Switching modes on a live cluster interrupts DSR flows.

### Lab 5: netkit/auto, host routing and EKS ENI

**Prerequisites:** (a) a node with kernel 6.8 or newer and one older node; (b) for the ENI portion, a throwaway EKS cluster created without `aws-node`.

1. With `bpf.datapathMode=auto`, `bpf.masquerade=true`, `kubeProxyReplacement=true`, compare `cilium-dbg status | grep -E "Device Mode|Routing"` on the new and old kernels. Expect `Device Mode` to show netkit on the new one and veth with a fallback log on the old one; the `Routing:` line shows `Host: BPF` on both. Do not switch a node that already runs veth Pods; drain it first.
2. Set `bpf.masquerade=false`: the `Routing:` line should end with `Host: Legacy` and an agent log line should state it fell back. Revert.
3. Apply `kubernetes.io/egress-bandwidth: "10M"` to a Pod with the bandwidth manager enabled and confirm `cilium-dbg bpf bandwidth list` lists it.
4. ENI: install with the ENI profile from section 16. `ip rule` should show, per Pod IP, an ingress rule `to <podIP> lookup main` (priority 20) and an egress rule `from <podIP> lookup <ENI table>` (priority 111), with per-ENI route tables; because ENI disables masquerade by default, the egress rule has no `to <VPC CIDR>` part unless you enable masquerade. Try `routingMode: tunnel` with ENI on a scratch cluster: expect the agent to refuse to start.
5. Overlay on EKS: deploy a validating webhook backed by a normal Pod on an overlay cluster and observe whether the API server can reach it; then move it to `hostNetwork`.

**Cleanup:** remove test workloads; revert Helm values; terminate the scratch cluster. Replacing the CNI on a populated cluster is out of scope and not a supported in-place migration here.

## 19. Version Delta

| Topic | 1.18 | 1.19 | 1.20 | 1.21-pre.3 |
|---|---|---|---|---|
| Kernel floor | 5.10 (4.18 RHEL 8.10) | same | same | same |
| `cilium_tunnel_map` | dropped from the datapath (agent unpins a leftover map); CLI gone | Go package **removed**; tunnel endpoint in ipcache value | n/a | n/a |
| `underlayProtocol` (IPv6 underlay) | **new** | stable | same | MTU calc uses the tunneling flag for IPv6 overhead |
| `enableIPv4Masquerade` with ENI | default **false** | same | same | same; IPv6 masquerade default becomes true unless ENI |
| `bpf.datapathMode` | veth, netkit, netkit-l2 | tproxy incompatible with netkit | **`auto`** added; configured vs operational mode in status | same |
| BPF host routing + IPsec | n/a | automatic with IPsec + KPR + BPF masquerade (needs CVE-2025-37959 fix) | same | same |
| `enable-remote-node-masquerade` | n/a | **new** | same | same |
| `packetizationLayerPMTUDMode` | n/a | **new**, default `blackhole` | same | same |
| WireGuard strict mode | old keys | `strictMode.ingress` **new** | old `strictMode.enabled/cidr` keys **removed** | same |
| IPsec `encryptedOverlay` | no-op | deprecated | **removed** | n/a |
| DSR dispatch | `opt`/`ipip`/`geneve` flag exists, IPIP undocumented | same | IPIP documented; per-service DSR/algorithm annotations; `bpf-lb-rss-*`; `service.cilium.io/weight` | same |
| Removed flags | n/a | `--enable-node-port/host-port/external-ips` | `--node-port-mode`, `--node-port-algorithm` | n/a |
| Socket-LB with Pod to NodePort | n/a | trace format change | client-egress DNAT when socketLB off or `hostNamespaceOnly` | same |
| `nativeRoutingCIDRFromClusterPool`, `nodePort.enableDynamicSourceLookup` | n/a | n/a | **new** | same |
| `nodePort.extendedNATPortRange` | n/a | n/a | n/a | **new [1.21 pre-release]** |
| `l2NeighDiscovery.enabled` default | false (was true) | same | same | same |
| autoDirectNodeRoutes + tunnel message | "cannot be used with tunneling" | same | same | "requires native routing mode" |

Maturity: stable: tunnel, native, BPF masquerade (IPv4), KPR, Maglev, DSR, XDP acceleration, bandwidth manager, BBR, BIG TCP. Beta: netkit, IPv6 BPF masquerade, VTEP, multicast, fragment tracking. Removed: `cilium_tunnel_map`, `encryptedOverlay`, `--node-port-mode`.

## 20. Troubleshooting

| Symptom | Likely cause | Check / fix |
|---|---|---|
| Agent exits at start with "cannot be used with tunneling" | `autoDirectNodeRoutes` with tunnel | Choose native routing, or remove the flag |
| Agent exits "Cannot specify IPAM mode eni in tunnel mode" | ENI IPAM with tunnel | Use `routingMode: native` |
| Cross-node Pod traffic fails, same-node works | UDP 8472/6081 blocked, wrong tunnel port, or node SG missing the self-reference | `tcpdump -nni <nic> 'udp port 8472'` on both nodes; check SG/NACL; confirm `Routing:` line |
| Large transfers stall, small requests work | MTU black hole (tunnel overhead, filtered ICMP) | Compare Pod `ip route` MTU with path MTU; `ping -M do -s`; consider `pmtuDiscovery` settings |
| Pod to external works from native Pods but source IP is a Pod IP and replies never return | Masquerade off (ENI default) or destination inside native-routing CIDR | `cilium-dbg status \| grep Masquerading`; enable masquerade or ip-masq-agent as intended |
| Pod to remote node source IP differs between clusters | Tunnel mode masquerades, native does not (section 9) | Decide intentionally; `enable-remote-node-masquerade` if you need uniformity |
| Agent log shows "Falling back to legacy host routing" | iptables masquerade or KPR off | Enable `bpf.masquerade` and KPR, or accept legacy |
| Istio sidecar traffic bypassed or broken | BPF host routing/socket-LB in Pod namespaces | `socketLB.hostNamespaceOnly=true`, or `bpf.hostLegacyRouting=true` |
| `bpf.datapathMode=netkit` fails | Missing kernel, legacy routing, iptables masquerade, KPR off, tproxy | Use `auto` to probe; satisfy preconditions |
| Agent refuses DSR | VXLAN tunnel, missing Geneve dispatch | Use `tunnelProtocol: geneve` and `dsrDispatch: geneve` |
| Service flows intermittently reset after node change | Maglev seed mismatch between agents | Make `maglev.hashSeed` identical everywhere |
| NodePort traffic missing in `tcpdump` | XDP acceleration | Capture elsewhere or disable acceleration for debugging |
| Webhook timeouts on EKS overlay | API server cannot reach non-VPC Pod IPs | Run webhook backends with `hostNetwork` |
| No encrypted packets on NIC | Bandwidth manager/IPsec/WireGuard interplay, or XDP/DSR non-Geneve path | Check `cilium-dbg status \| grep Encryption` and the encryption table in section 14 |

Generic procedure: (1) `cilium-dbg status --verbose` for effective settings; (2) `cilium-dbg monitor --type drop` for drop reasons (look for `DROP_INVALID_IDENTITY`, `DROP_INVALID_VNI`); (3) confirm the destination appears in `cilium-dbg bpf ipcache list` with the right tunnel endpoint; (4) capture on both nodes' NICs and on `cilium_vxlan`/`cilium_geneve`; (5) review agent logs from startup for fallback lines.

## 21. Validation Limits and Sources

The labs in this chapter were not executed against a live cluster in this review. They, and every behavior statement above, were checked against the upstream source and documentation at the tags below. Some items are inference and are labelled as such in the text: the EKS overlay webhook reachability, the EC2 source/destination check for native routing on non-ENI instances, the secondary-VPC-CIDR native-routing behavior, VTEP over Geneve, and the multicast kernel floor on kernels between 5.10 and 5.13 (unverified). An additional routing mode scaffolded in the 1.21 pre-release is deliberately not described.

Computed values (MTU table) are arithmetic from source constants, not measurements.

Sources (v1.20.2 unless noted):

- [Routing](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/concepts/routing.rst), [masquerading](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/concepts/masquerading.rst), [tuning](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/operations/performance/tuning.rst), [system requirements](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/operations/system_requirements.rst)
- [Kube-proxy replacement](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/kubernetes/kubeproxy-free.rst), [bandwidth manager](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/kubernetes/bandwidth-manager.rst), [VTEP](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/vtep.rst), [multicast](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/multicast.rst), [ENI IPAM](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/concepts/ipam/eni.rst), [AWS CNI chaining](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/installation/cni-chaining-aws-cni.rst)
- [Tunnel/overlay BPF](https://github.com/cilium/cilium/blob/v1.20.2/bpf/bpf_overlay.c), [lxc BPF](https://github.com/cilium/cilium/blob/v1.20.2/bpf/bpf_lxc.c), [identity helpers](https://github.com/cilium/cilium/blob/v1.20.2/bpf/lib/identity.h), [NAT](https://github.com/cilium/cilium/blob/v1.20.2/bpf/lib/nat.h), [tunnel options](https://github.com/cilium/cilium/blob/v1.20.2/bpf/lib/tunnel.h), [MTU](https://github.com/cilium/cilium/blob/v1.20.2/pkg/mtu/mtu.go), [startup validation](https://github.com/cilium/cilium/blob/v1.20.2/daemon/cmd/daemon_main.go), [KPR validation](https://github.com/cilium/cilium/blob/v1.20.2/pkg/kpr/initializer/kube_proxy_replacement.go), [Helm values](https://github.com/cilium/cilium/blob/v1.20.2/install/kubernetes/cilium/values.yaml)
- Pre-release: [daemon_main.go at v1.21.0-pre.3](https://github.com/cilium/cilium/blob/v1.21.0-pre.3/daemon/cmd/daemon_main.go), [values.yaml at v1.21.0-pre.3](https://github.com/cilium/cilium/blob/v1.21.0-pre.3/install/kubernetes/cilium/values.yaml)
- AWS: [EKS alternate CNI plugins](https://docs.aws.amazon.com/eks/latest/userguide/alternate-cni-plugins.html)

## Quiz

[Check your overlay and native routing understanding](../../quizzes/networking/cilium/09-overlay-native-routing-quiz.md).

[Return to Main Page](README.md)
