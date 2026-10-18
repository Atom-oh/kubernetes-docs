# Part 8: eBPF Datapath Internals

> **Review baseline**: Cilium 1.20.2 (stable, 2026-09-16); Cilium CLI 0.20.1; Hubble CLI 1.20.2. Items marked **[1.21 pre-release]** come from v1.21.0-pre.3 and may change before GA.
> **Last Updated**: October 15, 2026

This chapter examines the Cilium datapath: which BPF programs run, where they attach, how they call each other, which maps they read, how the agent compiles and loads them, and how one packet is processed hop by hop. The generic eBPF primer (history, verifier, map types) stays in [Part 2: eBPF](02-ebpf.md). Overlay and routing behavior is in [Part 9](09-overlay-native-routing.md); IPAM in [Part 10](10-ipam-deep-dive.md).

> **Stale-blog warning: `cilium_tunnel_map` no longer exists.** Older posts and some upstream sample listings show a `cilium_tunnel_map` that mapped a Pod CIDR to a remote node IP. Cilium 1.17 still had it in BPF (`bpf/lib/encap.h`) and `cilium-dbg bpf tunnel list` dumped it. It was dropped from the datapath in 1.18 (the 1.18.14 BPF tree has no reference; the agent only unpins a leftover map), and the Go package was removed in 1.19. In Cilium 1.20.2 no BPF program references it. The remote node (tunnel endpoint) is stored in the **value** of `cilium_ipcache_v2` (field `tunnel_endpoint`, with the flag `flag_has_tunnel_ep`). There is no `cilium-dbg bpf tunnel list` command in 1.18 or 1.20. If a guide tells you to `bpftool map dump` the tunnel map to debug overlay routing, dump the ipcache instead (`cilium-dbg bpf ipcache list`). One upstream development doc still lists the map in a sample output; that does not mean the map is live.

## Learning Objectives

- Name each Cilium BPF object, its entry programs, and the device or cgroup hook each one attaches to.
- Explain why Cilium uses tail calls, and how policy for a destination endpoint is executed from the sender's program.
- Read the key/value layout of the policy, ipcache, conntrack, and service maps and size them with the right flags.
- Describe the agent-side flow: ELF template cache, `.rodata.config` constants, map pinning, attach, commit.
- Trace a Pod -> ClusterIP -> Pod connection and list the map lookups at every hop.
- Inspect a live node with `cilium-dbg bpf ...` and `bpftool`.

## 1. Program Set and Attach Points

Cilium compiles a small number of C sources under `bpf/`. Each produces one ELF object; each object has one or more **entry programs** (ELF section `tc/entry`, `xdp/entry`, `cgroup/...`) and many **tail programs** (section `tc/tail`). Program names shown by `bpftool prog show` carry the prefix `cil_`.

### 1.1 Entry programs in 1.20.2

| ELF object (source) | Entry program | Attached to | Purpose |
|---|---|---|---|
| `bpf_lxc.o` | `cil_from_container` | ingress of the host-side `lxc*` veth (that is, traffic leaving the Pod); on netkit, the primary hook of the netkit peer | Per-endpoint egress path: identity, CT, egress policy, service LB (per-packet mode), forward |
| `bpf_lxc.o` | `cil_to_container` | egress of the host-side `lxc*` (traffic toward the Pod, delivered through the stack) | Ingress policy for stack-delivered traffic (endpoint routes, L7 proxy returns). Attached only when the endpoint needs an egress program |
| `bpf_lxc.o` | `cil_lxc_policy`, `cil_lxc_policy_egress` | **not attached to a device**; stored in the global prog arrays `cilium_call_policy` / `cilium_egresscall_policy` | Destination-ingress and source-egress policy, called by other programs |
| `bpf_host.o` | `cil_from_netdev` | ingress of every native/external device | Host-bound and forwarded traffic, NodePort, identity from ipcache, host firewall |
| `bpf_host.o` | `cil_to_netdev` | egress of native devices (attached only when masquerading, NodePort, WireGuard or IPsec need it) | BPF masquerade, NodePort SNAT, EDT/bandwidth, encryption marks |
| `bpf_host.o` | `cil_from_host` | egress of `cilium_host` | Host stack -> Pod traffic |
| `bpf_host.o` | `cil_to_host` | ingress of `cilium_host` and `cilium_net` | Pod -> host traffic, host firewall |
| `bpf_host.o` | `cil_host_policy` | prog-array slot (host endpoint policy) | Host firewall policy |
| `bpf_overlay.o` | `cil_from_overlay`, `cil_to_overlay` | ingress / egress of `cilium_vxlan` or `cilium_geneve` | Reads the tunnel ID as the source identity |
| `bpf_wireguard.o` | `cil_from_wireguard`, `cil_to_wireguard` | `cilium_wg0` ingress (always) / egress (only when required) | Marks decrypted traffic |
| `bpf_xdp.o` | `cil_xdp_entry` | XDP on native devices | CIDR prefilter and NodePort/DSR acceleration |
| `bpf_sock.o` | `cil_sock4_connect`, `cil_sock4_sendmsg`, `cil_sock4_recvmsg`, `cil_sock4_getpeername`, `cil_sock4_pre_bind`, `cil_sock4_post_bind`, IPv6 equivalents, `cil_sock_release` | **cgroup v2** sock_addr / sock hooks at the cgroup root | Socket-level load balancing |
| `bpf_sock_term.o` | `cil_sock_{tcp,udp}_destroy_v{4,6}` | BPF iterators (`iter/tcp`, `iter/udp`) calling the `bpf_sock_destroy` kfunc | Terminate sockets connected to deleted backends; the agent falls back to netlink `sock_diag` if the kfunc is unavailable |
| `bpf_probes.o`, `bpf_alignchecker.o` | n/a | run once with `BPF_PROG_RUN` at startup | Kernel capability probes; C/Go struct layout check |

`bpf_network.c` (`cil_from_network`, IPsec decrypt on native-device ingress) exists in 1.18.14 and 1.19.8 and is **removed in 1.20**.

```
                       node A                                   node B
 pod C eth0 ----veth---- lxc_C           lxc_B ----veth---- pod B eth0
   |  cgroup/connect4          |             ^                     
   |  (bpf_sock.o)             | tcx ingress |  redirect_peer
   |                           v cil_from_container                 
   |                    +-------------------+   (tail calls, maps)
   |                    |   bpf_lxc.o       |-------+
   |                    +-------------------+       | encap / FIB redirect
   |                           |                     v
   |        cilium_host  <-----+          cilium_vxlan (cil_to_overlay)  ==underlay==>
   |        cil_from_host/cil_to_host        eth0 (cil_from_netdev / cil_to_netdev)
   |                                         eth0 XDP (cil_xdp_entry, optional)
```

### 1.2 tcx, legacy tc, netkit

For per-device programs the loader (`pkg/datapath/loader/tc.go`) chooses the mechanism in this order:

1. **tcx** (Helm `bpf.enableTCX: true`, the default): a `bpf_link` attached with `link.AttachTCX` at the tail anchor. The link is **pinned** under `/sys/fs/bpf/cilium/endpoints/<id>/links/` (endpoints) or `/sys/fs/bpf/cilium/devices/<dev>/links/` (devices). Updating a program updates the link atomically, so there is no window with a missing program during a reload. Requires kernel 6.6 or newer. After a successful tcx attach, stale legacy filters are removed.
2. **Legacy tc**: if the kernel returns "not supported" or `enableTCX: false`, the loader uses a `clsact` qdisc with `cls_bpf` in direct-action mode, and detaches any stale tcx link.
3. **Hard failure** only when neither works: the agent reports that it needs tc-bpf support or tcx (Linux 6.6 or newer).

**netkit** (maturity: **beta**): `bpf.datapathMode: veth | netkit | netkit-l2 | auto`. The default is `veth`. With netkit, the Pod-specific programs attach inside the netkit **peer** device; other devices still use tcx, and selecting netkit turns tcx on automatically. Source-enforced prerequisites (`canUseNetkit`): kernel probe passes (upstream docs say 6.8 or newer; the probe error text in the source mentions 6.7), BPF host routing (no `bpf.hostLegacyRouting`), BPF masquerade, kube-proxy replacement, and **no `bpf.tproxy`** (it needs `bpf_sk_assign`, valid only at tc ingress). `auto` is new in 1.20: it probes and falls back to veth with a warning. Once Pods use veth, switching to netkit or `auto` for them is refused; roll new node groups instead.

| Mechanism | Kernel | Pinned object | Reload behavior | Maturity in Cilium |
|---|---|---|---|---|
| Legacy tc (`clsact` + `cls_bpf`) | 5.10 baseline | filter on device | filter replace | stable, fallback |
| tcx | 6.6+ | `bpf_link` under `/sys/fs/bpf/cilium/...` | atomic link update | stable, default when available |
| netkit | 6.8+ (docs) | netkit link on peer | atomic link update | beta |

### 1.3 XDP and cgroup hooks

- **XDP** (`cil_xdp_entry`) is attached when `loadBalancer.acceleration` is `native` or `best-effort`. It runs a CIDR prefilter (`cilium_cidr_v4_fix`/`dyn` LPM maps) and the NodePort/DSR fast path. The loader retries up to four attach permutations (attach type and the `XDP_HAS_FRAGS` flag) when the driver returns `EINVAL`.
- **cgroup hooks** are attached once at the cgroup root (agent flag `--cgroup-root`, default `/run/cilium/cgroupv2`) with `bpf_link`, pinned under `/sys/fs/bpf/cilium/socketlb/links/cgroup`. They run in every Pod netns unless `socketLB.hostNamespaceOnly=true`.

## 2. Tail Calls and the Policy-Program Structure

### 2.1 Why tail calls

A tail call replaces the running program with another without returning. Cilium uses them for three reasons: the verifier limit on one program's complexity (1M instructions), the 512-byte stack, and the ability to keep large optional features out of the common path. The maximum chain length is 33 tail calls. Mixing bpf-to-bpf calls with tail calls requires kernel 5.10, one reason for the 5.10 baseline.

State crosses a tail call in two places: `skb->cb[]` (the `CB_*` slots, such as `CB_SRC_LABEL`) and per-CPU scratch maps `cilium_tail_call_buffer4/6`, which hold, for example, the conntrack tuple and result computed by the CT tail program.

### 2.2 Per-endpoint call arrays

Each endpoint has a private `PROG_ARRAY` named `cilium_calls_<endpoint-id, 5 digits>` (`cilium_calls_00312`). The host endpoint uses `cilium_calls_hostns_<id>`, and each native device uses `cilium_calls_netdev_<ifindex>`. Other loaders use `cilium_calls_overlay_2` (the overlay device, named with the reserved `world` identity 2), `cilium_calls_wireguard_<ifindex>` and `cilium_calls_xdp_<ifindex>`. They are declared with `CILIUM_CALL_SIZE` entries and a pin flag that means "replace the pin on every load; never reuse an old array".

| Version | `CILIUM_CALL_SIZE` |
|---|---|
| 1.18.14 | 48 |
| 1.19.8 | 49 |
| 1.20.2 | 50 |
| 1.21.0-pre.3 | 50 |

Slots are **static**: the call site is inline assembly with a constant slot number. The loader reads BTF decl-tags (`tail:cilium_calls/<idx>`) on each `tc/tail` program, fills the array, and **prunes tail programs that are unreachable** once the constants are applied (section 5). Slot groups in 1.20:

| Slots | Meaning |
|---|---|
| 1-2, 4-5 | drop/error notification, ICMPv6 neighbor solicitation, time-exceeded |
| 6 | ARP |
| 3 | unused (a numbering gap kept to avoid conflicts when backporting) |
| 7, 10 | IPv4 / IPv6 from-LXC (aliased for netdev, overlay, WireGuard entry) |
| 8-9 | IPv4-to-IPv6 and IPv6-to-IPv4 translation (`CILIUM_CALL_IPV46_RFC6052`, `CILIUM_CALL_IPV64_RFC6052`; NAT46/NAT64) |
| 11-14 | to-LXC policy only, to-endpoint |
| 15-25, 36-39 | NodePort NAT, rev-NAT, DSR, SNAT forward; from-host |
| 26-27 | from-LXC continuation (second half of the egress path, splits verifier complexity) |
| 28-33 | CT ingress / CT ingress policy-only / CT egress, IPv4 and IPv6 |
| 34-35, 40 | SRv6, inter-cluster rev-SNAT |
| 41-47 | continuation from host/netdev, "no service" ICMP unreachable, multicast delivery |
| 48-49 | policy-denied ICMP response (new in 1.20, used when `policy_deny_response` is enabled) |

### 2.3 Global policy program arrays

Policy is not in the per-endpoint call array. `cil_lxc_policy` and `cil_lxc_policy_egress` are inserted into two **global** prog arrays, indexed by endpoint ID and sized `ENDPOINTS_MAP_SIZE`:

| Array | Index | Runs |
|---|---|---|
| `cilium_call_policy` | destination endpoint ID | destination **ingress** policy |
| `cilium_egresscall_policy` | source endpoint ID | source **egress** policy |

The loader writes these slots **before** attaching the tc/tcx program (`PolicyMap.Update(ep id, PolicyProg)`). A sender that finishes its L3 rewrite for a local destination calls `tail_call_policy(ep->lxc_id)`. This matters because with BPF host routing the packet is moved into the destination Pod's netns with `bpf_redirect_peer`, which **skips the destination's tc egress hook**. Calling the destination's policy program from the sender is how same-node ingress policy is still enforced. If the slot is empty (endpoint terminating), the packet is dropped with `DROP_EP_NOT_READY`.

`cil_to_container` still exists for stack-delivered traffic, so destination ingress policy can run either from the sender's tail call or from that egress hook.

## 3. Policy Enforcement Path

### 3.1 Policy map

Each endpoint has `cilium_policy_v3_<id>` (1.20; `cilium_policy_v2_` in 1.18/1.19). Type `LPM_TRIE`, flags `BPF_F_NO_PREALLOC | BPF_F_RDONLY_PROG_COND`, size `--bpf-policy-map-max` (default 16384 per endpoint).

```
policy_key  { lpm prefixlen; u32 sec_label;   /* remote identity, 0 = wildcard */
              u8 egress:1;  u8 protocol;      /* 0 = any */
              be16 dport; }                   /* prefix match => port ranges */
policy_entry{ be16 proxy_port;                /* != 0 => redirect to L7 proxy */
              deny:1; lpm_prefix_length:5; auth_type:7; has_explicit_auth_type:1;
              u32 precedence; u32 cookie; }
```

The LPM prefix covers `sec_label` and `egress` exactly, `protocol` all-or-nothing, and `dport` as a bit prefix, which is how port ranges become a few entries.

### 3.2 Lookup algorithm

For a flow with remote identity `R`, protocol `P`, port `D`:

1. Specific lookup with `sec_label = R`. If the hit carries maximum precedence (a deny), stop.
2. Aggregate lookup: the identity's aggregate (for example a CIDR group) then `sec_label = 0` (wildcard L3).
3. Choose the higher `precedence` (deny over proxy redirect over allow), then the longer LPM prefix. No hit means `DROP_POLICY`.

The match type is reported in events (L3+L4, L3 only, L4 only, protocol only, all). ICMP type is carried in `dport` when ICMP rules are enabled, and "fragmentation needed" is always allowed.

### 3.3 Verdict and side effects

- Deny: `DROP_POLICY_DENY` and a drop event. Allow with `proxy_port != 0`: redirect to the proxy (section 3.5). Allow with `auth_type != 0`: `DROP_POLICY_AUTH_REQUIRED` unless `cilium_auth_map` has a valid entry.
- **Egress is enforced by the source endpoint** (`handle_ipv4_from_lxc`), only for `CT_NEW` and `CT_ESTABLISHED`; replies (`CT_REPLY`, `CT_RELATED`) skip policy. **Ingress is enforced by the destination** (`ipv4_policy()` in its policy program) and creates the ingress CT entry after the allow.
- A policy-verdict event is emitted on deny and on a new allowed connection. Hairpin traffic (Pod to its own service IP) skips policy.
- Optional per-entry counters go to `cilium_policystats` (`--bpf-policy-stats-map-max` 65536).

### 3.4 Policy changes do not recompile

Policy updates are map operations on `cilium_policy_v3_<id>` (`applyPolicyMapChangesLocked`). The object is rebuilt and reloaded only if the endpoint or node configuration hash changes. A `CiliumNetworkPolicy` edit therefore never triggers clang.

### 3.5 L7 and FQDN redirect

When `proxy_port != 0`, `ctx_redirect_to_proxy4()` sends the flow to Envoy or the DNS proxy. Two implementations exist:

| Method | How | Maturity |
|---|---|---|
| iptables TPROXY (default) | datapath sets `mark = MARK_MAGIC_TO_PROXY \| proxy_port << 16` and returns OK; `CILIUM_PRE_mangle` rules with `xt_socket`/`TPROXY` steer it to the listener | stable |
| `bpf.tproxy: true` | `bpf_sk_assign` assigns the listener socket at tc ingress | beta, default off, **incompatible with netkit** (agent refuses to start in 1.19.8, 1.20 and 1.21.0-pre.3; no such check found in the 1.18.14 source) |

Proxy ports come from `--proxy-portrange-min/max` (10000-20000). The CT entry records `proxy_redirect` so replies return to the proxy. L7 events do not come from BPF; Envoy and the DNS proxy report access-log records to the agent.

Mutual authentication (`auth_type`) is **deprecated in 1.20** (use ztunnel); **[1.21 pre-release]** removes `--bpf-auth-map-max` and `cilium_auth_map`, and the entry's auth bits become reserved.

## 4. Map Catalog

Global maps are pinned by name under `/sys/fs/bpf/tc/globals/`; links and plugin objects are under `/sys/fs/bpf/cilium/`. Helm: `bpf.root` (default `/sys/fs/bpf`), `bpf.autoMount.enabled`.

### 4.1 Core maps

| Map | Type | Key -> Value (essentials) | Notes |
|---|---|---|---|
| `cilium_lxc` | HASH | endpoint IP (+family, cluster_id) -> `{ifindex, lxc_id, flags, mac, node_mac, sec_id, parent_ifindex}` | local endpoints and host IPs; 65535 entries (`lxcmap.MaxEntries`) |
| `cilium_ipcache_v2` | LPM_TRIE | `{cluster_id, family, ip/prefix}` -> `{sec_identity, tunnel_endpoint, key, flag_skip_tunnel, flag_has_tunnel_ep, flag_ipv6_tunnel_ep, flag_remote_cluster}` | **identity and tunnel endpoint**; 512000 entries (`ipcachemap.MaxEntries`) |
| `cilium_policy_v3_<id>` | LPM_TRIE | see 3.1 | per endpoint |
| `cilium_calls_<id>`, `_hostns_`, `_netdev_` | PROG_ARRAY | slot -> program | private, replaced on each load |
| `cilium_call_policy`, `cilium_egresscall_policy` | PROG_ARRAY | endpoint ID -> policy program | global |
| `cilium_ct4_global`, `cilium_ct6_global` | LRU_HASH | 5-tuple + direction flags -> `ct_entry` | TCP |
| `cilium_ct_any4_global`, `cilium_ct_any6_global` | LRU_HASH | same | non-TCP |
| `cilium_snat_v4_external` (+`v6`) | LRU_HASH | CT tuple -> NAT entry (`to_saddr/to_sport` or `to_daddr/to_dport`) | masquerade, NodePort SNAT |
| `cilium_nodeport_neigh4/6` | LRU_HASH | next-hop IP -> MAC | |
| `cilium_node_map_v2` | HASH | `{family, ip}` -> `{node id, spi}` | IPsec/WireGuard/ClusterMesh node IDs (v1 removed in 1.19) |
| `cilium_devices` (new 1.20) | HASH | ifindex -> `{mac, l3}` | synced by the agent |
| `cilium_runtime_config` | ARRAY | index -> u64 (time offset, agent liveness) | `cilium-dbg bpf config list` |
| `cilium_metrics` | PERCPU_HASH | `{reason, direction, line, file}` -> `{count, bytes}` | feeds forward/drop counters |
| `cilium_events` | PERF_EVENT_ARRAY | CPU -> perf fd | monitor and Hubble source (section 8) |
| `cilium_signals` | PERF_EVENT_ARRAY | datapath -> agent signals | for example CT-full triggers GC |

Conntrack addresses are stored with source and destination swapped relative to the packet; the `ct_entry` holds lifetime, `rx/tx_closing`, `rev_nat_index`, `proxy_redirect`, `from_l7lb`, `from_tunnel`, `src_sec_id`, and the seen TCP flags. A single map holds egress, ingress and service-scope entries, separated by `tuple.flags`. Cluster Mesh adds per-cluster inner maps (`cilium_per_cluster_ct_*`) for overlapping IPs.

Timeouts (agent flags, 1.20.2): TCP established 2h13m20s, SYN 1m, FIN 10s, non-TCP 1m, service TCP 2h13m20s, service grace 1m.

### 4.2 Load-balancing maps

| Map | Type | Key -> Value | Notes |
|---|---|---|---|
| `cilium_lb4_services_v2` (+`6`) | HASH | `{address, dport, backend_slot, proto, scope}` -> `{backend_id or affinity/algorithm, count, rev_nat_index, flags, qcount}` | slot 0 is the frontend; slots 1..count hold backend IDs; `scope` separates external and internal (externalTrafficPolicy) |
| `cilium_lb4_backends_v3` (+`6`) | HASH | `backend_id` -> `{address, port, proto, flags, cluster_id, zone}` | |
| `cilium_lb4_reverse_nat` (+`6`) | HASH | `rev_nat_index` -> `{address, port}` | per-packet LB reply restore |
| `cilium_lb4_reverse_sk` (+`6`) | LRU_HASH | `{socket cookie, backend addr, port}` -> `{original service addr, port, rev_nat_index}` | socket-LB reverse translation |
| `cilium_lb4_affinity`, `cilium_lb_affinity_match` | LRU_HASH / HASH | client (IP or netns cookie) + rev_nat -> backend | `sessionAffinity` |
| `cilium_lb4_source_range` | LPM_TRIE | `{rev_nat_id, cidr}` -> flag | `loadBalancerSourceRanges` |
| `cilium_lb4_maglev` | HASH_OF_MAPS | `rev_nat_id` -> lookup-table array | `--bpf-lb-algorithm maglev`, table size `--bpf-lb-maglev-table-size` |
| `cilium_lb4_health` | LRU_HASH | socket cookie -> peer backend | LB health datapath; kernel 5.12 |

The upper 8 bits of the service's `affinity_timeout` field carry the selection algorithm (random or maglev).

### 4.3 Feature maps (one line each)

`cilium_ipmasq_v4/v6` (non-masquerade CIDRs), `cilium_ipv4_frag_datagrams` (8192 default), `cilium_vtep_map`, `cilium_srv6_*`, `cilium_egress_gw_policy_v4_v2` (renamed from `_v4` in 1.20), `cilium_l2_responder_v4/v6`, `cilium_mcast_*`, `cilium_cidr_v4_fix/dyn` (XDP prefilter), `cilium_encrypt_state`, `cilium_auth_map`, `cilium_policystats`, `cilium_ratelimit`, `cilium_throttle`, `cilium_lb_act`/`cilium_lb_fct` (active connection tracking, off by default), and per-CPU scratch maps (`cilium_tail_call_buffer4/6`, `cilium_nodeport_nat_buffer`, `cilium_xdp_scratch`, `cilium_percpu_trace_id`).

### 4.4 Sizing flags

| Flag (Helm) | Default (1.20.2) | Affects |
|---|---|---|
| `--bpf-map-dynamic-size-ratio` (`bpf.mapDynamicSizeRatio`) | 0.0025 (0.25% of RAM); **dynamic sizing is on by default** | CT TCP/any, NAT, socket reverse-NAT; the NodePort neighbor map follows the NAT size (the flag help says "CT, NAT and policy BPF maps", but the sizing code does not resize policy maps) |
| `--bpf-ct-global-tcp-max` (`bpf.ctTcpMax`) | 524288 | TCP CT |
| `--bpf-ct-global-any-max` (`bpf.ctAnyMax`) | 262144 | non-TCP CT |
| `--bpf-nat-global-max` (`bpf.natMax`) | 524288 | NAT; capped to 2/3 of the CT sum with a warning |
| `--bpf-neigh-global-max` (`bpf.neighMax`) | 524288 | NodePort neighbor |
| `--bpf-policy-map-max` (`bpf.policyMapMax`) | 16384 per endpoint (maximum 65536) | policy |
| `--bpf-fragments-map-max` | 8192 | fragments |
| `--bpf-node-map-max` | 16384 | node map |
| `--bpf-lb-map-max` (`bpf.lbMapMax`) | 65536 | fallback for six per-LB-map flags (`--bpf-lb-service-map-max`, `-service-backend-map-max`, `-rev-nat-map-max`, `-affinity-map-max`, `-source-range-map-max`, `-maglev-map-max`), each defaulting to 0 = use `lb-map-max`; present in source (`pkg/loadbalancer/config.go`) but not listed in the generated cmdref, which shows only `--bpf-lb-map-max` |
| `--bpf-sock-rev-map-max` | dynamic, defaults to CT-any size | socket reverse map |
| `bpf.distributedLRU.enabled` | false | per-CPU LRU free lists; use with larger maps |
| `bpf.preallocateMaps` | false | trades memory for lower insert latency |

Dynamic sizing computes `entries = default_entries * (ratio * RAM) / total_default_bytes`, clamped to a floor per map (CT TCP 128Ki, CT any 64Ki, NAT 128Ki, socket reverse 64Ki) and a ceiling of 16Mi (2^24). **Setting a flag explicitly disables dynamic sizing for that map only.** The agent logs `option <name> set by dynamic sizing to <N>` when it applies. Upstream's tuned performance profile uses ratio 0.08.

> Resizing a map recreates it, and entries are lost until repopulated. Resizing the LB maps or CT maps on a live node disrupts established connections. Plan resizes as a rolling node operation.

Monitor with `cilium_bpf_map_pressure{map_name}` (emitted above `--bpf-policy-map-pressure-metrics-threshold`, default 0.1), `cilium_bpf_map_capacity`, and `cilium_bpf_map_ops_total`.

## 5. From Agent to Kernel: Compile, Load, Attach

### 5.1 Flow

```
agent start
  |  write node headers  (StateDir/globals: node_config.h, netdev_config.h, ...)
  |  hash node config -> if changed, wipe template cache (StateDir/templates)
  v
template config hash (compile-time #defines only)
  |  cache hit?  -> reuse StateDir/templates/<sha>/bpf_lxc.o
  |  miss        -> clang -O2 --target=bpf -mcpu=v3|v2|v1 ... -> new ELF template
  v
LoadCollection (per endpoint / device)
  |  copy spec -> patch maps -> rename maps (cilium_calls -> cilium_calls_<id>, cilium_policy -> cilium_policy_v3_<id>)
  |  write .rodata.config (endpoint ID, IPs, MAC, ifindex, feature switches)
  |  dead-code analysis -> remove unused tail calls and maps
  |  fill tail-call arrays from BTF decl tags
  |  load into kernel (verifier); reuse pinned global maps, replace incompatible ones
  v
attach: policy progs into cilium_call_policy/egresscall_policy
        -> tcx/tc/netkit entry programs -> commit() map pins -> endpoint routes
```

### 5.2 ELF templates and `.rodata.config`

The expensive compile step still runs in the agent (the container image ships clang/LLVM; running the agent natively needs LLVM 18.1 or newer). To avoid recompiling per Pod, Cilium hashes only the **template configuration**: `#define ENABLE_*` flags that change code shape. All endpoints with the same flags share one object under `StateDir/templates/<sha>/`. List them with `cilium-dbg bpf sha list`.

Per-endpoint values are not compiled in. They are globals in the `.rodata.config` section declared with `DECLARE_CONFIG(type, name, desc)` and read with `CONFIG(name)`. The agent writes the values into a copy of the spec before load; the kernel freezes the read-only data, so the verifier sees the values as constants and **prunes dead branches**. This requires dead-code-elimination support (kernel 5.1 or newer). Go-side structs are generated by `dpgen` from BTF decl-tags (`pkg/datapath/config/*_config.go`). The effective constants are dumped per endpoint/device as JSON (for example `bpf_lxc.json`) in the state directory and are included in `cilium sysdump`.

Each release moves more `#define` switches into `.rodata.config`, which means fewer distinct templates and fewer recompiles. Counting `DECLARE_CONFIG`/`NODE_CONFIG` declarations with grep over the BPF tree gives 18 (1.18.14), 43 (1.19.8), 73 (1.20.2) and 104 (**[1.21 pre-release]**, v1.21.0-pre.3), using `grep -rE '^\s*(DECLARE_CONFIG|NODE_CONFIG)\(' bpf --include=*.h --include=*.c | wc -l` in each tag's checkout. Treat these counts as a rough trend, not an API.

### 5.3 Regeneration

On each endpoint regeneration the agent computes the endpoint header hash. If it equals the last one, only maps are synchronized (`RegenerateWithoutDatapath`, which is the policy-change case). Otherwise headers are written and the datapath is reloaded. Relevant metrics: `cilium_endpoint_regenerations_total`, `endpoint_regeneration_time_stats_seconds` (stages such as `bpfCompilation`, `bpfLoadProg`, `bpfWaitForELF`), and `cilium_endpoint_component_status` (new in 1.20).

Order matters: `commit()` of map pins must happen after all entry programs are attached, otherwise a new program could tail-call into an old array and "miss" a tail call.

### 5.4 Verifier testing

Cilium compile-tests the maximum-feature builds against kernels 5.10, 6.1 and net-next (`bpf/complexity-tests/`). Verifier failures at load time are logged with the full verifier output.

## 6. Kernel and Feature Matrix

### 6.1 Hard startup requirements (1.20.2)

The agent refuses to start without: `bpf()` and JIT; tc-bpf or tcx; `bpf_skb_change_tail`; `bpf_get_socket_cookie`; `bpf_get_current_cgroup_id`; `bpf_fib_lookup`; dead-code elimination; writable `skb->queue_mapping`; large (1M instruction) programs; `bpf_skb_adjust_room` with `BPF_ADJ_ROOM_MAC`; `bpf_jiffies64`; `BPF_MAP_LOOKUP_BATCH`; `bpf_get_netns_cookie`; `bpf_sk_assign`; `bpf_get_cgroup_classid`; `bpf_perf_event_output` in cgroup sock_addr; `bpf_csum_level`; `bpf_skb_change_head`; `bpf_redirect_neigh`; `bpf_redirect_peer`. This is why the documented minimum is **kernel 5.10** (RHEL 8.10 with 4.18 is an explicit exception because of Red Hat backports). The legacy per-helper header probing is now empty; the 5.10 baseline assumes all helpers.

Kernel config options listed upstream include `BPF`, `BPF_SYSCALL`, `BPF_JIT`, `NET_CLS_BPF`, `NET_CLS_ACT`, `NET_SCH_INGRESS`, `CGROUPS`, `CGROUP_BPF`, `DEBUG_INFO_BTF`, and feature extras such as `VXLAN`, `GENEVE`, `NET_SCH_FQ` (bandwidth manager) and `NETKIT`.

### 6.2 Optional accelerators

| Feature | Minimum kernel | Maturity / note |
|---|---|---|
| tcx links | 6.6 | default when available; legacy tc otherwise |
| netkit (`bpf.datapathMode`) | 6.8 (docs; source probe text says 6.7) | beta |
| IPv6 BIG TCP | 5.19 | needs supported NIC driver |
| IPv4 BIG TCP | 6.3 | |
| BBR for Bandwidth Manager | 5.18 | |
| LB health-check datapath | 5.12 | |
| Multicast | 5.10 on AMD64; 6.0 on AArch64 | |
| `bpf_sock_destroy` kfunc | not stated in source | falls back to netlink `sock_diag` automatically |

The datapath does not use CO-RE relocation helpers (a search of the 1.20.2 `bpf/` tree for `preserve_access_index` finds only a UAPI header comment): it builds against its own headers and the UAPI `__sk_buff`. BTF is used for map definitions, the `.rodata.config` data section and decl-tags, and `CONFIG_DEBUG_INFO_BTF=y` is required.

On EKS, check the real node kernel with `uname -r` and `cilium-dbg status` before enabling tcx- or netkit-dependent settings; this chapter does not assume which AMI ships which kernel.

## 7. Worked Trace: Pod -> Service -> Pod

Illustrative setup (numbers are examples; structures come from source): client Pod `C` 10.0.1.10, identity 4711, endpoint ID 312, on node A. Service `web` ClusterIP 10.100.0.20:80/TCP, `rev_nat_index` 42, two backends: B1 10.0.1.55 (node A, endpoint 87) and B2 10.0.2.77 (node B), both identity 9001. Settings: IPv4, veth, tcx, BPF host routing, `kubeProxyReplacement: true` (which forces socket-LB on), `socketLB.hostNamespaceOnly=false`.

### Hop 0: `connect()` in the Pod, `cgroup/connect4` (`cil_sock4_connect`)

1. Look up `cilium_lb4_services_v2` with `{10.100.0.20, 80, TCP, slot 0, scope 0}`. No entry: leave the sockaddr untouched. Entry with `count=2`.
2. Pick a slot: random for TCP (socket cookie for UDP). Look up the service key with that slot to get `backend_id`, then `cilium_lb4_backends_v3[backend_id]` to get 10.0.2.77:80. If `sessionAffinity` is set, `cilium_lb4_affinity` is consulted first.
3. Write `cilium_lb4_reverse_sk[{cookie, 10.0.2.77, 80}] = {10.100.0.20, 80, 42}`.
4. Rewrite `user_ip4/user_port` in the syscall. **No DNAT happens on the wire.** `tcpdump` inside the Pod shows the backend IP, a frequent surprise. A `trace_sock_notify` event is emitted when socket-LB tracing is on.

### Hop 1: SYN leaves the Pod, `cil_from_container` on the host-side veth (tcx ingress)

| Step | Action | Maps touched |
|---|---|---|
| 1 | clear metadata, `send_trace_notify(TRACE_FROM_LXC)` (subject to aggregation) | `cilium_events` |
| 2 | tail call slot 7 (IPv4 from-LXC) | `cilium_calls_00312` |
| 3 | per-packet LB skipped (socket-LB already translated) | none |
| 4 | tail call slot 30 (CT egress): lookup `CT_NEW`, tuple stored in per-CPU buffer | `cilium_ct4_global`, `cilium_tail_call_buffer4` |
| 5 | tail call slot 26 (`handle_ipv4_from_lxc`) | `cilium_calls_00312` |
| 6 | resolve destination identity: LPM lookup of 10.0.2.77 gives identity 9001 and (overlay) the node B tunnel endpoint; a miss means `world` | `cilium_ipcache_v2` |
| 7 | egress policy: `{egress=1, sec_label=9001, TCP, 80}`, two-pass lookup; allow or drop; a new allowed flow emits a policy-verdict event | `cilium_policy_v3_00312`, `cilium_events`, `cilium_metrics` on drop |
| 8 | if `proxy_port != 0`: mark for proxy, flag CT `proxy_redirect`, hand to the stack (section 3.5) | |
| 9 | `ct_create4(CT_EGRESS)`: insert entry, SYN lifetime 1m until ACK, then 2h13m20s | `cilium_ct4_global` (and CT-any for related ICMP) |
| 10 | choose the forwarding path (below) | |

Forwarding choices at step 10:

- **Destination on the same node** (B1): `cilium_lxc[dst]` returns `{ifindex, lxc_id=87, mac, node_mac}`; the L2 header is rewritten; metadata (`CB_SRC_LABEL=4711`, delivery flags) is set; then `tail_call_policy(87)` runs B1's `cil_lxc_policy` out of `cilium_call_policy` (Hop 3).
- **Remote, overlay**: `flag_has_tunnel_ep` is set in the ipcache value, so `bpf_skb_set_tunnel_key` sets `tunnel_id` = source identity 4711 and `remote_ipv4` = node B; the packet is redirected to `cilium_vxlan`/`cilium_geneve`, where `cil_to_overlay` runs before kernel encapsulation. Pod-to-pod traffic is not masqueraded.
- **Remote, native routing with BPF host routing**: `bpf_fib_lookup` then redirect to the NIC. With `bpf.hostLegacyRouting=true` the packet instead returns OK to the kernel stack and netfilter. There is no VNI; the receiver re-derives the source identity from ipcache by source IP (or from marks with IPsec/WireGuard).

### Hop 2 (remote only): node B receives

- Overlay: `cil_from_netdev` passes UDP 8472 (VXLAN) / 6081 (Geneve) to the stack; the kernel decapsulates onto `cilium_vxlan`; `cil_from_overlay` reads `bpf_skb_get_tunnel_key`, maps `tunnel_id` to the **source identity** (a host identity is rejected with `DROP_INVALID_IDENTITY`), stores it in `CB_SRC_LABEL`, emits `TRACE_FROM_OVERLAY`, then looks up `cilium_lxc[10.0.2.77]` and calls `tail_call_policy(ep)`.
- Native routing: `cil_from_netdev` performs the same steps with the source identity from `cilium_ipcache_v2[src ip]`.

### Hop 3: destination ingress policy and delivery

1. `cil_lxc_policy` runs the CT-ingress tail call: `cilium_ct4_global` lookup, `CT_NEW`.
2. Ingress policy: `cilium_policy_v3_00087` with `{egress=0, sec_label=4711, TCP, 80}`. Verdict event emitted.
3. `ct_create4(CT_INGRESS)` records `src_sec_id=4711`, `from_tunnel`, `proxy_redirect`.
4. Delivery: `bpf_redirect_peer` into the Pod netns (veth) or `redirect` (netkit), `TRACE_TO_LXC` event. The backend's stack answers with source 10.0.2.77; it never sees the ClusterIP.

### Hop 4: reply and close

- B's `cil_from_container` finds the ingress CT entry as `CT_REPLY`, so **policy is skipped**; the packet is encapsulated back with VNI 9001 (or routed natively). On node A, `tail_call_policy(312)` runs C's policy program; `CT_REPLY` skips policy; `redirect_peer` delivers to C.
- Socket-LB reverse: the app believes it talks to 10.100.0.20. `getpeername` and `recvmsg` hooks look up `cilium_lb4_reverse_sk[{cookie, 10.0.2.77, 80}]` and return the service address.
- Without socket-LB (host-namespace-only mode, L7 LB, SCTP): Hop 1 performs DNAT in `bpf_lxc` and stores `rev_nat_index` in the CT entry; replies use `cilium_lb4_reverse_nat[rev_nat_index]` to restore the source.
- FIN/RST sets `tx/rx_closing` and drops the lifetime to the FIN timeout (10s); agent CT GC deletes expired entries. `cilium_lb4_reverse_sk` entries linger until LRU eviction or `cil_sock_release`.

### Per-hop lookup checklist

| Hop | Program | Lookups / writes |
|---|---|---|
| 0 | `cil_sock4_connect` | `lb4_services_v2` x2, `lb4_backends_v3`, `lb4_affinity` (optional), write `lb4_reverse_sk` |
| 1 | `cil_from_container` + tails | `calls_<id>` x3, `tail_call_buffer4`, `ct4_global` (lookup, create), `ipcache_v2`, `policy_v3_<src>` (egress), `cilium_lxc`, `call_policy`, `events`, `metrics` |
| 2 | `cil_from_overlay` / `cil_from_netdev` | tunnel key or `ipcache_v2`, `cilium_lxc`, `call_policy` |
| 3 | `cil_lxc_policy` (destination) | `ct4_global`, `policy_v3_<dst>` (ingress), `ct4_global` create, `events` |
| 4 | reverse path, `recvmsg` | `ct4_global` (reply), `lb4_reverse_sk` or `lb4_reverse_nat` |

### 1.20 behavior change that affects this trace

With kube-proxy replacement and `socketLB.enabled=false` or `socketLB.hostNamespaceOnly=true`, Pod-to-NodePort connections inside the cluster are now load-balanced at the **client Pod's** tc hook. Client egress and backend ingress NetworkPolicies must allow the traffic accordingly.

## 8. Hubble Event Pipeline

```
BPF program --ctx_event_output--> cilium_events (PERF_EVENT_ARRAY, per CPU)
      |   trace_notify / drop_notify / policy_verdict_notify / debug / capture / trace_sock_notify
      v
agent monitor (pkg/monitor/agent): perf reader, 64 pages per CPU, opened only if a consumer exists
      |-- lost samples (kernel buffer overrun) -> MonitorStatus.Lost
      |-- unix-socket listeners (cilium-dbg monitor), queue --monitor-queue-size
      v
Hubble consumer -> observer queue (--hubble-event-queue-size)
      |   full => LostEvent source=OBSERVER_EVENTS_QUEUE, hubble_lost_events_total
      v
Hubble parser (identity/endpoint/service enrichment) -> ring buffer (--hubble-event-buffer-capacity)
      v
gRPC: hubble observe / Relay / UI
```

Facts to remember:

- The event map is a **perf event array in 1.20 and 1.21-pre.3**, not a BPF ring buffer.
- Volume control in the datapath: `bpf.monitorAggregation` (Helm default `medium`; agent flag default `None`). At `medium` and above, intra-node receive traces are suppressed and established flows report only when `bpf.monitorInterval` (5s) elapses or a flag in `bpf.monitorFlags` is seen. Per-class toggles: `bpf.events.drop.enabled`, `bpf.events.policyVerdict.enabled`, `bpf.events.trace.enabled` (all true by default), and an experimental rate limit `bpf.events.default.rateLimit` / `burstLimit` (both set or both zero).
- Flows in `hubble observe` live in an in-memory ring (`hubble.eventBufferCapacity`, must be 2^n - 1, default 4095, maximum 65535). They are best-effort: perf-buffer overruns and observer-queue overflow both lose events, and they are counted under different `source` labels (`perf_event_ring_buffer`, `observer_events_queue`).
- L7 events do not originate in BPF; they arrive as agent events from the proxies.

## 9. Inspection Tooling

### 9.1 cilium-dbg

```bash
CILIUM_POD=$(kubectl -n kube-system get pod -l k8s-app=cilium -o jsonpath='{.items[0].metadata.name}')
kc() { kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- "$@"; }

kc cilium-dbg status --verbose         # KPR, datapath mode (configured vs operational), BPF map pressure
kc cilium-dbg bpf fs show              # bpffs mount
kc cilium-dbg map list -v              # pinned maps and sizes
kc cilium-dbg bpf endpoint list        # cilium_lxc
kc cilium-dbg bpf ipcache list         # identity + tunnel endpoint per IP/CIDR
kc cilium-dbg bpf ct list global       # conntrack
kc cilium-dbg bpf nat list             # SNAT maps
kc cilium-dbg bpf lb list --frontends  # also --backends, --revnat, --source-ranges
kc cilium-dbg bpf lb maglev list       # only with Maglev
kc cilium-dbg bpf policy get --all -n  # every cilium_policy_v3_*, numeric identities
kc cilium-dbg bpf metrics list         # cilium_metrics
kc cilium-dbg bpf config list          # cilium_runtime_config
kc cilium-dbg bpf sha list             # compiled ELF templates
kc cilium-dbg monitor -t drop -t policy-verdict --related-to <ENDPOINT_ID>
```

`cilium-dbg map get <name>` shows the agent's cached view, not necessarily the kernel's; `cilium-dbg map events <name>` shows the update log. There is no `bpf tunnel` and no `bpf calls` subcommand.

### 9.2 bpftool (run on the node)

```bash
sudo bpftool net show                                     # tcx/tc/xdp/netkit attachments per device
sudo bpftool prog show | grep -E 'cil_|tail_'             # entry and tail programs
sudo bpftool map show pinned /sys/fs/bpf/tc/globals/cilium_ct4_global
sudo bpftool cgroup tree /run/cilium/cgroupv2             # socket-LB hooks
sudo ls /sys/fs/bpf/cilium/endpoints/*/links /sys/fs/bpf/cilium/devices/*/links
```

Treat pinned maps as read-only. Do not write raw bytes into Cilium maps; the agent's cached state would diverge. The agent image may not include `bpftool`; this review did not verify it. Run it from the node or a debug Pod if absent.

**[1.21 pre-release]** `--enable-bpf-stats` (Helm `bpf.stats.enabled`, default false) enables kernel run-time statistics and adds a `bpf/stats/report` hive command, exposed as `cilium-dbg bpf stats report` (`--sort avg|total|runs`, `--pod`, `--device`, `--json`), that shows per-program run counts and average run time.

## 10. Datapath Plugins (beta, new in 1.20)

Datapath Plugins let an external component run its own BPF programs around Cilium's entry points without forking the datapath.

- Enable with Helm `datapathPlugins.enabled=true` (default false; agent `--enable-datapath-plugins`); state directory `datapathPlugins.stateDir` (default `/var/run/cilium/plugins`).
- Register a plugin with the `CiliumDatapathPlugin` CRD (`cilium.io/v2alpha1`): `spec.attachmentPolicy: Always | BestEffort` and `spec.version`.
- The agent talks to each plugin over gRPC on `<stateDir>/<name>/plugin.sock` using the `PrepareCollection` and `InstrumentCollection` calls. Cilium generates a dispatcher so plugin programs of type `BPF_PROG_TYPE_EXT` (freplace) run before or after Cilium's entry programs for tc, XDP and cgroup sock hooks.
- The plugin Pod needs `SYS_ADMIN`. Any create, update or delete of a plugin CR triggers a full datapath reinitialization. There is no cross-version compatibility guarantee. Absent in 1.18 and 1.19.

Use it for experiments and vendor integrations, not as a general extension point for production changes yet.

## 11. Labs

Prerequisites for all labs: a disposable Linux cluster running Cilium 1.20.2 with kube-proxy replacement, node shell access (SSM or equivalent) and `kubectl`. Nothing here exposes anything outside the cluster.

### Lab 1: Map every Cilium program on a node

1. On a node, run `sudo bpftool net show` and `sudo bpftool prog show | grep cil_`.
2. List pinned links with `sudo ls /sys/fs/bpf/cilium/endpoints/*/links /sys/fs/bpf/cilium/devices/*/links`.
3. Run `kc cilium-dbg bpf sha list`.

Expected: `cil_from_netdev` on each native device, `cil_from_container` per `lxc*` device, `cil_to_host`/`cil_from_host` on `cilium_host`, and (overlay) `cil_from_overlay`/`cil_to_overlay` on `cilium_vxlan` or `cilium_geneve`. On kernels 6.6 or newer, per-endpoint link pins exist; on older kernels, `tc filter show dev <lxc> ingress` lists the legacy filter instead. Cleanup: none (read-only).

### Lab 2: Policy changes do not recompile

1. Note `kc cilium-dbg bpf sha list` and the endpoint's map with `kc cilium-dbg bpf policy get <ENDPOINT_ID>`.
2. Apply a `CiliumNetworkPolicy` allowing traffic from clients with a client label to TCP/80 on a test backend.
3. Re-run both commands.

Expected: a new ingress entry with the client's numeric identity appears in the backend endpoint's policy map; the template list is unchanged. Add an explicit deny rule and observe an entry with the deny flag. Cleanup: delete the policy objects. This should be rehearsed in a namespace with no other policies, because cluster-wide default-deny interacts.

### Lab 3: Follow one connection through the maps

1. Create a Deployment with two replicas and a ClusterIP Service in a test namespace, and a client Pod.
2. From the client, `curl` the ClusterIP. In another terminal run `cilium-dbg monitor -t trace -t policy-verdict --related-to <CLIENT_ENDPOINT_ID>` on the client's node.
3. Run `bpf lb list --frontends`, `--backends`, and `bpf ct list global | grep <backend ip>`.
4. Compare `tcpdump -ni eth0 port 80` in the client's netns with the Service IP.

Expected: the service frontend lists the backends; a CT entry exists for the chosen backend; with socket-LB on, the capture shows the backend IP, not the ClusterIP. Optional: with `socketLB.hostNamespaceOnly=true` the capture shows the ClusterIP (per-packet LB). That switch changes how traffic is load-balanced cluster-wide, so apply it only on a test cluster and revert by restoring the previous Helm value.

### Lab 4: Hubble loss accounting

1. Set `hubble.eventQueueSize` to a deliberately small value on a test cluster (rollback: restore the previous value, which restarts agents).
2. Generate load with a traffic tool in a test namespace.
3. Query the agent metrics for `hubble_lost_events_total` by `source`.

Expected: `observer_events_queue` increases when the queue overflows, and the agent logs "hubble events queue is full". Perf-buffer overruns would instead appear as `perf_event_ring_buffer`.

### Lab 5 (advanced): netkit on a fresh node group

Only on nodes with a kernel that supports netkit. Install or upgrade a new node group with `bpf.datapathMode=auto`, then check `cilium-dbg status` for configured versus operational mode, `ip -d link show` for the device type, and `bpftool net show` for netkit attachments. Setting `bpf.tproxy=true` together with netkit makes the agent refuse netkit in 1.19 and later (`auto` falls back to veth). Rollback: do not switch existing veth Pods in place; drain and replace nodes.

## Version Delta

| Item | 1.18.14 | 1.19.8 | 1.20.2 | 1.21.0-pre.3 |
|---|---|---|---|---|
| Minimum kernel (docs) | 5.10 (4.18 on RHEL 8.10) | 5.10 | 5.10 | 5.10 |
| `bpf_network.c` | present | present | **removed** | removed |
| `CILIUM_CALL_SIZE` | 48 | 49 | 50 | 50 |
| Config variables (grep count) | 18 | 43 | 73 | 104 |
| Policy map name | `cilium_policy_v2_` | `cilium_policy_v2_` | `cilium_policy_v3_` | `cilium_policy_v3_` (auth bits reserved) |
| Node map | v1 + v2 | v2 only | v2 | v2 |
| Egress gateway map | `..._v4` | `..._v4` | `..._v4_v2` | `..._v4_v2` |
| `cilium_devices` map | no | no | yes | yes |
| `--datapath-mode` values | veth, netkit, netkit-l2 | same | + `auto` | + `auto` |
| `bpf.tproxy` | beta (no netkit check found) | beta; refuses netkit | beta; refuses netkit | beta; refuses netkit |
| Datapath Plugins | no | no | yes (beta) | yes |
| Mutual auth map (`--bpf-auth-map-max`) | yes | yes | yes, mutual auth deprecated | removed |
| `--enable-bpf-stats` | no | no | no | yes |
| `--node-port-mode`, `--node-port-algorithm` | present | present | removed (use `--bpf-lb-mode`, `--bpf-lb-algorithm`) | removed |
| Policy-denied ICMP response | no | no | yes (tail slots 48-49) | yes |

The 1.21 upgrade notes in the pre-release tree still carry the 1.20 text, so no authoritative 1.21 delta exists yet.

## Troubleshooting

| Symptom | Likely cause | Check |
|---|---|---|
| Drops with `DROP_EP_NOT_READY` (code -203) | policy slot empty while an endpoint is being created or deleted | `cilium-dbg endpoint list`; transient during churn, persistent means regeneration failing |
| "Missed tail call" drops | array not populated or commit ordering broken after a failed reload | agent log for load errors; `cilium-dbg endpoint log <id>`; restart the agent Pod |
| New connections fail, `cilium_bpf_map_pressure` near 1 for a CT map | CT/NAT map full | `cilium-dbg map list -v`; raise `bpf.mapDynamicSizeRatio` or the explicit max; keep NAT at most 2/3 of CT; remember resize drops entries |
| Services stop matching after growth | LB map limit reached | `bpf.lbMapMax` (affects six maps); resize is disruptive |
| Agent will not start, "Require support for tcx links" or helper errors | kernel below baseline | `uname -r`, `cilium-dbg status`; move to a supported AMI |
| Programs on legacy tc instead of tcx | kernel older than 6.6 or `enableTCX: false` | `bpftool net show`, `tc filter show` |
| netkit refused | missing prerequisite (host routing, BPF masquerade, KPR, tproxy, kernel) | agent log reason; `cilium-dbg status` configured vs operational mode |
| Verifier rejection at load | unusual feature combination or kernel limit | full verifier log in agent stderr; compare with the 5.10/6.1/net-next tested builds |
| `hubble observe` misses flows | perf-buffer or observer-queue loss, aggregation too high, ring too small | `hubble_lost_events_total` by `source`; `bpf.monitorAggregation`; `hubble.eventBufferCapacity` |
| Old guide says dump `cilium_tunnel_map` | map removed | use `cilium-dbg bpf ipcache list` |
| Pod -> NodePort breaks after upgrade to 1.20 with socket-LB off or host-namespace-only | LB now at client Pod tc hook | allow in client egress and backend ingress policies |

## Validation Limits and Sources

The labs were not executed against a live cluster in this review; commands and flags were checked against upstream source and documentation. IDs, IPs and identities in the trace are illustrative. Source facts were read from the Cilium v1.20.2 tree (for example `bpf/bpf_lxc.c`, `bpf/lib/tailcall.h`, `bpf/lib/policy.h`, `bpf/lib/eps.h`, `pkg/datapath/loader/tc.go`, `pkg/bpf/collection.go`, `Documentation/cmdref/cilium-agent.md`); entry-line numbers move between releases, so verify against your exact tag. Not verified: whether `bpftool` ships in the agent image; the exact kernel version that introduced the `bpf_sock_destroy` kfunc; the **[1.21 pre-release]** stats report was read from source (`cilium-dbg/cmd/bpf_stats_report.go`) but not run.

- Cilium v1.20.2 system requirements: https://github.com/cilium/cilium/blob/v1.20.2/Documentation/operations/system_requirements.rst
- Maps reference: https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/ebpf/maps.rst (note: it writes `cilium_ct_{4,6}_global`; the real names are `cilium_ct4_global` and `cilium_ct6_global`)
- BPF sources: https://github.com/cilium/cilium/tree/v1.20.2/bpf
- Datapath loader: https://github.com/cilium/cilium/tree/v1.20.2/pkg/datapath/loader
- Agent flags: https://github.com/cilium/cilium/blob/v1.20.2/Documentation/cmdref/cilium-agent.md
- Datapath Plugins: https://github.com/cilium/cilium/blob/v1.20.2/Documentation/contributing/development/plugins.rst
- Upgrade notes: https://github.com/cilium/cilium/blob/v1.20.2/Documentation/operations/upgrade-current.inc
- Performance tuning (netkit, BIG TCP): https://github.com/cilium/cilium/blob/v1.20.2/Documentation/operations/performance/tuning.rst
- **[1.21 pre-release]** BPF stats: https://github.com/cilium/cilium/tree/v1.21.0-pre.3/pkg/bpf/stats

## Quiz

Test your understanding with the [Part 8 quiz](../../quizzes/networking/cilium/08-ebpf-datapath-internals-quiz.md).
