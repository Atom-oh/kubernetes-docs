# Part 9: Overlay and Native Routing Deep Dive Quiz

> **Cilium 1.20.2 · 2026-10-15**

## Tunnel Mechanics

1. **What does Cilium put in the 24-bit VNI of an encapsulated packet?**
   - A) The destination node ID
   - B) The source security identity of the sending endpoint
   - C) The Cilium cluster ID
   - D) A per-node random value that the receiver maps through `cilium_tunnel_map`

   <details>
   <summary>Show Answer</summary>

   **Answer: B) The source security identity of the sending endpoint**

   The VNI carries the source identity (with `world-ipv4`/`world-ipv6` sent as `world`, and `host` rewritten to `remote-node`). The receiver also has the ipcache, so the VNI is an optimization, not the only source of truth. `cilium_tunnel_map` was dropped from the datapath in 1.18 (the agent only unpins a leftover map) and its Go package was removed in 1.19; tunnel endpoints live in the ipcache value.

   </details>

2. **How does Geneve differ from VXLAN with respect to identity transport in Cilium?**
   - A) Geneve carries the identity in a TLV option; VXLAN carries it in the VNI
   - B) Geneve carries no identity; policy is evaluated only on the sender
   - C) Geneve uses the outer UDP source port to carry the identity
   - D) It does not differ: identity is in the VNI for both, and Geneve options are used only for the DSR service address and port

   <details>
   <summary>Show Answer</summary>

   **Answer: D) It does not differ: identity is in the VNI for both, and Geneve options are used only for the DSR service address and port**

   The only Geneve option Cilium inserts (class `0x014B`, type `0x81`) is for DSR. The outer source port range (`tunnelSourcePortRange`) only affects entropy and has no role in identity.

   </details>

3. **In tunnel mode, which component builds the outer UDP/IP headers?**
   - A) The `bpf_lxc` program, which writes the headers into the packet
   - B) The cilium-agent in user space
   - C) The kernel vxlan/geneve driver behind the flow-based `cilium_vxlan`/`cilium_geneve` device, after BPF sets the tunnel key and redirects to it
   - D) The NIC firmware

   <details>
   <summary>Show Answer</summary>

   **Answer: C) The kernel vxlan/geneve driver behind the flow-based `cilium_vxlan`/`cilium_geneve` device, after BPF sets the tunnel key and redirects to it**

   BPF calls `bpf_skb_set_tunnel_key` and redirects to the tunnel device's ifindex; encapsulation is done by the kernel driver. On the receive side the kernel decapsulates and `cil_from_overlay` reads the tunnel key.

   </details>

4. **What happens if you set `routingMode: tunnel` together with `autoDirectNodeRoutes: true` on Cilium 1.20.2?**
   - A) The agent exits with a fatal error because packets must go through the tunnel device
   - B) Cilium uses direct routes inside a subnet and tunnels between subnets
   - C) The flag is ignored with a warning
   - D) Cilium falls back to native routing

   <details>
   <summary>Show Answer</summary>

   **Answer: A) The agent exits with a fatal error because packets must go through the tunnel device**

   The check is `TunnelingEnabled() && EnableAutoDirectRouting` in `daemon_main.go`. There is no per-subnet fallback. The v1.21.0-pre.3 message is worded "requires native routing mode" but is still a fatal error.

   </details>

## MTU, Masquerading and Host Routing

5. **On a 1500-byte underlay with an IPv4 underlay, VXLAN and WireGuard both enabled, what route MTU does a Pod see?**
   - A) 1450
   - B) 1405
   - C) 1373
   - D) 1355

   <details>
   <summary>Show Answer</summary>

   **Answer: D) 1355**

   The route MTU is the base MTU minus (WireGuard 95 + tunnel 50). 1450 is VXLAN alone, 1405 is native routing with WireGuard, and 1373 is VXLAN with IPsec (50 + 77).

   </details>

6. **Which configuration is required to use DSR in `routingMode: tunnel`?**
   - A) VXLAN with `dsrDispatch: opt`
   - B) `tunnelProtocol: geneve` with `loadBalancer.dsrDispatch: geneve`
   - C) VXLAN with `loadBalancer.mode: hybrid`
   - D) Any tunnel protocol with `dsrDispatch: ipip` and no other change

   <details>
   <summary>Show Answer</summary>

   **Answer: B) `tunnelProtocol: geneve` with `loadBalancer.dsrDispatch: geneve`**

   The agent rejects `dsr`/`hybrid` with VXLAN tunneling, requires Geneve dispatch for DSR in tunnel mode, and requires the Geneve tunnel protocol for Geneve dispatch.

   </details>

7. **You set `bpf.datapathMode: auto` on a node whose kernel lacks netkit. What happens?**
   - A) The agent fails to start
   - B) The agent switches to `netkit-l2`
   - C) The agent falls back to veth and logs a warning; explicit `netkit` would have failed hard
   - D) The agent keeps retrying netkit and blocks Pod creation

   <details>
   <summary>Show Answer</summary>

   **Answer: C) The agent falls back to veth and logs a warning; explicit `netkit` would have failed hard**

   `auto` (new in 1.20) probes and demotes with the log "datapath autodiscovery failed, reverting from netkit to veth". Netkit also needs BPF masquerade, KPR and no legacy host routing.

   </details>

8. **BPF host routing is the default, but you left iptables masquerading on with kube-proxy replacement enabled. What does the agent do?**
   - A) Logs that BPF host routing requires BPF masquerade and silently falls back to legacy host routing
   - B) Refuses to start
   - C) Enables BPF masquerade automatically
   - D) Disables kube-proxy replacement

   <details>
   <summary>Show Answer</summary>

   **Answer: A) Logs that BPF host routing requires BPF masquerade and silently falls back to legacy host routing**

   Host routing is best effort. Features requested by name that need it (netkit, BBR for Pods, BIG TCP) fail hard instead. Verify with the `Host:` field of the `Routing:` line in `cilium-dbg status` (`Host: Legacy`).

   </details>

9. **What does `kubernetes.io/egress-bandwidth: "10M"` limit a Pod to when the bandwidth manager is enabled?**
   - A) 10 MB/s
   - B) 10 Mbit/s per replica set
   - C) Nothing, unless BBR is also enabled
   - D) 10 Mbit/s

   <details>
   <summary>Show Answer</summary>

   **Answer: D) 10 Mbit/s**

   The value is a Kubernetes quantity in bits. Egress is enforced with EDT and FQ per Pod; BBR is optional. With IPsec the manager is silently disabled.

   </details>

10. **With BPF masquerade and default settings, how is Pod-to-remote-node traffic treated?**
    - A) Always masqueraded
    - B) Never masqueraded
    - C) Not masqueraded in native routing, but masqueraded in tunnel mode (unless the ipcache entry has `skip_tunnel`)
    - D) Masqueraded only if the destination is outside RFC1918 ranges

    <details>
    <summary>Show Answer</summary>

    **Answer: C) Not masqueraded in native routing, but masqueraded in tunnel mode (unless the ipcache entry has `skip_tunnel`)**

    This is step 5 of the decision order in `bpf/lib/nat.h`. `enable-remote-node-masquerade=true` (1.19+, set via `extraConfig`) makes both modes masquerade.

    </details>
