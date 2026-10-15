# Part 8: eBPF Datapath Internals Quiz

> **Cilium 1.20.2 · 2026-10-15**

1. **In Cilium 1.20, which attach mechanism is used for per-device programs when the kernel supports it, and what happens otherwise?**
   - A) Legacy `clsact` filters always; tcx is only used with netkit
   - B) tcx `bpf_link` (kernel 6.6 or newer); otherwise `clsact` + `cls_bpf` direct-action
   - C) XDP on every veth; otherwise the agent refuses to start
   - D) cgroup hooks on every interface; otherwise iptables

   <details>
   <summary>Show Answer</summary>

   **Answer: B) tcx `bpf_link` (kernel 6.6 or newer); otherwise `clsact` + `cls_bpf` direct-action**

   `bpf.enableTCX` defaults to true. The link is pinned under `/sys/fs/bpf/cilium/...` and updated atomically on reload. The agent only fails when neither tc-bpf nor tcx works.

   </details>

2. **Same-node pod-to-pod traffic uses BPF host routing and `bpf_redirect_peer`. Where is the destination pod's ingress policy enforced?**
   - A) In the sender's `bpf_lxc` program, which tail-calls `cilium_call_policy[destination endpoint ID]`
   - B) In the destination veth's tc egress hook, using the policy map pinned for the sender endpoint
   - C) In an iptables chain in the destination netns, installed by the agent for each endpoint
   - D) In the XDP program on the node's NIC, before the packet reaches any veth

   <details>
   <summary>Show Answer</summary>

   **Answer: A) In the sender's `bpf_lxc` program, which tail-calls `cilium_call_policy[destination endpoint ID]`**

   `redirect_peer` skips the destination's tc egress hook, so the destination's `cil_lxc_policy` is stored in a global prog array and called by the sender. An empty slot produces `DROP_EP_NOT_READY`.

   </details>

3. **What are the type and key structure of the per-endpoint policy map `cilium_policy_v3_<id>`?**
   - A) HASH keyed by the remote Pod IP address and destination port
   - B) ARRAY indexed by port number, with one slot per protocol
   - C) PROG_ARRAY indexed by policy rule number, tail-calling one program per rule
   - D) LPM_TRIE keyed by identity, direction, protocol and a port prefix

   <details>
   <summary>Show Answer</summary>

   **Answer: D) LPM_TRIE keyed by identity, direction, protocol and a port prefix**

   The key has `sec_label`, an `egress` bit, `protocol` and `dport`. The port prefix lets a port range be stored as a few entries, and a `sec_label` of 0 acts as an L3 wildcard.

   </details>

4. **A tutorial tells you to inspect `cilium_tunnel_map` to find the remote node for an overlay destination in Cilium 1.20. What is correct?**
   - A) Use `cilium-dbg bpf tunnel list` to dump the node-to-endpoint table
   - B) The map exists but is only populated when IPsec or WireGuard encryption is enabled
   - C) The map no longer exists; the tunnel endpoint is a field in the `cilium_ipcache_v2` value
   - D) The map is now per-endpoint, named `cilium_tunnel_map_<id>`, with one entry per node

   <details>
   <summary>Show Answer</summary>

   **Answer: C) The map no longer exists; the tunnel endpoint is a field in the `cilium_ipcache_v2` value**

   No 1.20 BPF code references `cilium_tunnel_map`. `cilium_ipcache_v2` (LPM_TRIE) returns `sec_identity` and `tunnel_endpoint` with `flag_has_tunnel_ep`. Use `cilium-dbg bpf ipcache list`.

   </details>

5. **What is the default of `--bpf-map-dynamic-size-ratio` in 1.20.2, and which maps does it size?**
   - A) 0.0025 of RAM; CT, NAT, NodePort neighbor and socket reverse-NAT maps
   - B) 0 (disabled); only the policy maps, sized by `--bpf-policy-map-max`
   - C) 0.25 of RAM; every BPF map including LB maps and the ipcache
   - D) 0.0025 of RAM; only the ipcache and the policy maps

   <details>
   <summary>Show Answer</summary>

   **Answer: A) 0.0025 of RAM; CT, NAT, NodePort neighbor and socket reverse-NAT maps**

   Dynamic sizing is on by default. Setting a size flag such as `--bpf-ct-global-tcp-max` disables dynamic sizing for that map only. LB maps use `--bpf-lb-map-max` instead.

   </details>

6. **What does `--bpf-lb-map-max` (default 65536) control?**
   - A) Only the `cilium_lb4_services_v2` map, leaving backends and rev-NAT at their own defaults
   - B) The number of backends per Service, rejecting additional endpoints once exceeded
   - C) The Maglev lookup table size, which must be a prime number from a fixed list
   - D) The fallback size for six per-LB-map flags (services, backends, rev-NAT, affinity, source-range, Maglev)

   <details>
   <summary>Show Answer</summary>

   **Answer: D) The fallback size for six per-LB-map flags (services, backends, rev-NAT, affinity, source-range, Maglev)**

   Each of the six per-map flags defaults to 0, meaning "use `lb-map-max`". The Maglev table size is a separate flag. Resizing recreates the maps and disrupts connections until they repopulate.

   </details>

7. **With socket-LB enabled, where is a ClusterIP translated, and how does the application still see the Service address on replies?**
   - A) At the veth by DNAT for every packet; `cilium_lb4_reverse_nat` restores it on the reply path
   - B) At `connect()`/`sendmsg()` by cgroup hooks; `recvmsg`/`getpeername` hooks use `cilium_lb4_reverse_sk` to restore it
   - C) By kube-proxy iptables DNAT in the host netns; conntrack restores the original address
   - D) At the NIC by XDP before the stack sees the packet; the Hubble relay restores it

   <details>
   <summary>Show Answer</summary>

   **Answer: B) At `connect()`/`sendmsg()` by cgroup hooks; `recvmsg`/`getpeername` hooks use `cilium_lb4_reverse_sk` to restore it**

   No DNAT happens on the wire, so `tcpdump` in the pod shows the backend IP. The per-packet path with `cilium_lb4_reverse_nat` is used only when socket-LB is not applicable (for example host-namespace-only mode, L7 LB, SCTP).

   </details>

8. **A packet arrives on `cilium_vxlan` in overlay mode. How does `cil_from_overlay` learn the source identity?**
   - A) It reads the tunnel ID (VNI) with `bpf_skb_get_tunnel_key`, which the sender set to its source identity
   - B) It looks up the outer source IP in `cilium_lxc`, which maps node IPs to identities
   - C) It reads an HTTP header that the local Envoy proxy injected into the request
   - D) It parses the identity from the source Pod name using the endpoint label cache

   <details>
   <summary>Show Answer</summary>

   **Answer: A) It reads the tunnel ID (VNI) with `bpf_skb_get_tunnel_key`, which the sender set to its source identity**

   An identity of host in the tunnel ID is rejected with `DROP_INVALID_IDENTITY`. In native routing there is no VNI, so the source identity comes from `cilium_ipcache_v2` by source IP (or from marks with IPsec/WireGuard).

   </details>

9. **An administrator edits a CiliumNetworkPolicy. What does the agent do to the datapath?**
   - A) Recompiles `bpf_lxc.c` with clang for each affected endpoint and reloads the program on its veth
   - B) Replaces the pinned tcx links on all devices so that the new policy takes effect atomically
   - C) Updates entries in `cilium_policy_v3_<id>`; it reloads programs only if the endpoint or node config hash changes
   - D) Restarts the Cilium agent Pod so that all endpoints regenerate their programs

   <details>
   <summary>Show Answer</summary>

   **Answer: C) Updates entries in `cilium_policy_v3_<id>`; it reloads programs only if the endpoint or node config hash changes**

   Policy changes are map operations (`RegenerateWithoutDatapath`). Template objects are cached per template-config hash, and per-endpoint values live in `.rodata.config`.

   </details>

10. **Which statement about the Hubble event pipeline in 1.20 is correct?**
    - A) BPF writes to a ring buffer that Hubble Relay reads directly from each node's BPF filesystem
    - B) Events go to `cilium_events` (perf array), then the agent monitor and a Hubble queue, into an in-memory ring (4095 flows)
    - C) Flows are persisted to disk by the agent and replayed to Hubble Relay after a restart
    - D) L7 events are emitted by the `bpf_lxc` tail programs when the proxy redirect map matches

    <details>
    <summary>Show Answer</summary>

    **Answer: B) Events go to `cilium_events` (perf array), then the agent monitor and a Hubble queue, into an in-memory ring (4095 flows)**

    Losses can occur at the perf buffer (`perf_event_ring_buffer`) or at the observer queue (`observer_events_queue`). L7 records come from Envoy and the DNS proxy as agent events, not from BPF.

    </details>
