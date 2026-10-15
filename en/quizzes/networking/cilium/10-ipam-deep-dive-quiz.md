# Part 10: IPAM Deep Dive Quiz

> **Cilium 1.20.2 (stable, 2026-09-16) · 2026-10-15**. Items marked [1.21 pre-release] come from v1.21.0-pre.3.

1. **A CNI ADD allocates a Pod IP through `POST /ipam`, then the CNI plugin crashes before the endpoint is created. When does the agent release that IP, without any restart?**
   - A) After the 10 minute expiration timer set at allocation expires
   - B) Only when the agent restarts and restores endpoints
   - C) Immediately, because the REST connection closed
   - D) After 180 seconds, the `--excess-ip-release-delay` default

   <details>
   <summary>Show Answer</summary>

   **Answer: A) After the 10 minute expiration timer set at allocation expires**

   **Explanation:**
   The CNI plugin requests the allocation with the expiration flag set, so the agent starts a 10 minute timer (`defaults.IPAMExpiration`). Endpoint creation stops the timer; if it never happens, the timer releases the IP. The 180 second value belongs to ENI excess-IP release in the operator.

   </details>

2. **With the 1.20.2 Helm defaults for cluster-pool (`10.0.0.0/8`, IPv4 mask size 24), how many nodes can receive a PodCIDR from that CIDR, and how many addresses does each node block hold?**
   - A) 16,384 nodes, 1,024 addresses each
   - B) 256 nodes, 65,536 addresses each
   - C) 65,536 nodes, 256 addresses each
   - D) 65,536 nodes, 254 usable addresses by definition of the mask

   <details>
   <summary>Show Answer</summary>

   **Answer: C) 65,536 nodes, 256 addresses each**

   **Explanation:**
   Nodes per pool CIDR is `2^(nodeMask - poolMask) = 2^(24 - 8) = 65,536`, and each block holds `2^(32 - 24) = 256` addresses. Usable Pod IPs are fewer because the network/broadcast addresses and the router, health and ingress addresses are taken out of the block.

   </details>

3. **What limits the gap between the pool prefix length and the node mask for an IPv6 cluster-pool in the 1.20.2 allocator?**
   - A) The gap must be at least 64 bits so each node gets a /64, regardless of pool size
   - B) The gap must not exceed 16 bits (`clusterSubnetMaxDiff`), because the allocator uses an uncompressed bitmap
   - C) There is no limit, only the node mask must not exceed /128, since the bitmap is compressed
   - D) The gap must be exactly 8 bits, matching the IPv4 default

   <details>
   <summary>Show Answer</summary>

   **Answer: B) The gap must not exceed 16 bits (`clusterSubnetMaxDiff`), because the allocator uses an uncompressed bitmap**

   **Explanation:**
   `pkg/ipam/cidrset` rejects an IPv6 node mask more than 16 bits longer than the pool prefix (`ErrCIDRSetSubNetTooBig`). IPv4 only requires the node mask to be at most 32. The Helm defaults `fd00::/104` with `/120` sit exactly at the 16-bit limit.

   </details>

4. **In multi-pool IPAM, which order does Cilium use to choose the pool for a new Pod?**
   - A) CiliumPodIPPool selectors, then Pod annotation, then namespace annotation, then the `default` pool unless `require-pool-match` is set
   - B) Always the `default` pool; annotations and selectors only affect masquerading and LB IPAM
   - C) Namespace annotation, then Pod annotation, then `default`; CiliumPodIPPool selectors are only used for LB IPAM
   - D) Pod annotation (`ipv4-pool`/`ipv6-pool` before `ip-pool`), then namespace annotation, then CiliumPodIPPool selectors, then `default` unless `require-pool-match` is set

   <details>
   <summary>Show Answer</summary>

   **Answer: D) Pod annotation (`ipv4-pool`/`ipv6-pool` before `ip-pool`), then namespace annotation, then CiliumPodIPPool selectors, then `default` unless `require-pool-match` is set**

   **Explanation:**
   Pod annotations win over namespace annotations, which win over `podSelector`/`namespaceSelector` matches. With no match, the pool named by `ipam-default-ip-pool` (default `default`) is used unless the Pod or namespace has `ipam.cilium.io/require-pool-match: "true"`, which blocks allocation. Selection happens once at Pod creation.

   </details>

5. **A Pod matches the selectors of two different CiliumPodIPPools for the same address family and has no pool annotation. What happens?**
   - A) Allocation fails with an error and an event, because exactly one pool per family must match
   - B) The pool whose name sorts first alphabetically is used, and an event is logged
   - C) The Pod receives one address from each matching pool and both are routed
   - D) The `default` pool is used as a tie-breaker and the selectors are ignored

   <details>
   <summary>Show Answer</summary>

   **Answer: A) Allocation fails with an error and an event, because exactly one pool per family must match**

   **Explanation:**
   Selector-based selection requires exactly one matching pool per family. Multiple matches produce an error (`multiple CiliumPodIPPools match pod ...`) and the Pod stays in `ContainerCreating`. Fix it by tightening the selectors or by annotating the Pod or namespace explicitly.

   </details>

6. **Which statement about ENI prefix delegation in Cilium 1.20.2 is correct?**
   - A) It works on any EC2 instance type and hands out /24 prefixes, falling back to /28 when the subnet is full
   - B) It works on any instance type and mixes /32 and /28 allocations freely on the same node, switching per Pod based on the subnet
   - C) It requires `ipam.mode=multi-pool` and a `CiliumPodIPPool` whose CIDRs list the prefixes to be delegated
   - D) Only on Nitro or bare-metal instances, it allocates /28 prefixes, is skipped on a node already holding secondary /32 IPs, and falls back to /32 when the subnet lacks prefixes

   <details>
   <summary>Show Answer</summary>

   **Answer: D) Only on Nitro or bare-metal instances, it allocates /28 prefixes, is skipped on a node already holding secondary /32 IPs, and falls back to /32 when the subnet lacks prefixes**

   **Explanation:**
   The operator checks for a Nitro hypervisor or bare metal, skips prefix mode on nodes that already have secondary IPs (no mixed mode), and on `InsufficientPrefixesInSubnet` stops allocating prefixes on that node and uses `AssignPrivateIpAddresses`. The unit is a /28 (16 addresses, /80 for IPv6). ENI mode has no CiliumPodIPPool.

   </details>

7. **How does the 1.20 ENI allocator hand EC2 interface state to the agent?**
   - A) The operator writes individual IPs to `spec.ipam.pool` and the agent reports usage in `status.ipam.used`, exactly as in 1.19, with no ENI status written
   - B) The agent calls the EC2 API directly with its own credentials and the operator only garbage-collects ENIs
   - C) The operator writes ENIs to `status.eni.enis`; the agent converts them to /32 and /28 CIDRs in `spec.ipam.pools.allocated` (pool `default`) and reports demand in `spec.ipam.pools.requested`
   - D) Each ENI becomes its own CiliumPodIPPool selected with the `ip-pool` annotation, created by the operator

   <details>
   <summary>Show Answer</summary>

   **Answer: C) The operator writes ENIs to `status.eni.enis`; the agent converts them to /32 and /28 CIDRs in `spec.ipam.pools.allocated` (pool `default`) and reports demand in `spec.ipam.pools.requested`**

   **Explanation:**
   1.20 moved ENI to the multi-pool allocator: only the operator calls EC2, the agent derives allocated CIDRs from the ENI inventory and writes requested capacity back. The `spec.ipam.pool` / `status.ipam.used` model is the 1.19 and 1.18 CRD allocator. ENI mode has no CiliumPodIPPool or `ip-pool` annotation.

   </details>

8. **[1.21 pre-release] You currently pass `--aws-use-primary-address` directly to the Cilium operator. What must you do before moving to 1.21?**
   - A) Nothing; the flag is only deprecated and still works as an operator flag in 1.21
   - B) Remove it and set `eni.nodeSpec.usePrimaryAddress=true` (agent flag `--eni-use-primary-address`)
   - C) Set it on the `CiliumPodIPPool` for the default pool under `spec.ipv4.pool[]`
   - D) Move it to the agent as `--aws-use-primary-address`, keeping the same name

   <details>
   <summary>Show Answer</summary>

   **Answer: B) Remove it and set `eni.nodeSpec.usePrimaryAddress=true` (agent flag `--eni-use-primary-address`)**

   **Explanation:**
   The operator flag is removed in 1.21 so that the per-node `CiliumNode.spec.eni.use-primary-address` is the single source of truth. Helm users are unaffected because the chart only ever wired the agent-side value. This is a pre-release change (v1.21.0-pre.3).

   </details>

9. **[1.21 pre-release] What is `spec.ipv4.pool[].reservedRanges` in `cilium.io/v2` `CiliumPodIPPool` used for?**
   - A) To exclude addresses from every node block so they can be handed out as static Service IPs by LB IPAM pools
   - B) To make `maskSize` mutable on a live pool without recreating existing node blocks
   - C) To reserve addresses for the router, health and ingress endpoints on every node block
   - D) To keep an old CIDR in `cidrs` so existing node blocks keep working while no new blocks are carved from it, enabling gradual migration to a new CIDR

   <details>
   <summary>Show Answer</summary>

   **Answer: D) To keep an old CIDR in `cidrs` so existing node blocks keep working while no new blocks are carved from it, enabling gradual migration to a new CIDR**

   **Explanation:**
   Reserving the whole old CIDR means Cilium preserves existing allocations but allocates new PodCIDR blocks only from the other CIDRs. After all node groups have migrated, the old CIDR and its `pool` entry are removed. Each `pool[].cidr` must be one of `cidrs`; `maskSize` stays immutable.

   </details>

10. **Two `CiliumLoadBalancerIPPool` resources contain overlapping blocks. What does LB IPAM do?**
   - A) It marks the later pool as Conflicting (`cilium.io/PoolConflict`) and allocates nothing from it
   - B) It rejects the second pool at admission through a validating webhook
   - C) It merges them into one pool and allocates from the union of their blocks
   - D) It splits the overlapping range evenly between the two pools by Service count

   <details>
   <summary>Show Answer</summary>

   **Answer: A) It marks the later pool as Conflicting (`cilium.io/PoolConflict`) and allocates nothing from it**

   **Explanation:**
   LB IPAM does not merge or reject overlapping pools. The later one is flagged Conflicting, shown in the `Conflicting` print column and the `lbipam_conflicting_pools` metric (the exact runtime prefix, `cilium_` or `cilium_operator_`, is unverified), and no allocation happens from it. Editing a live pool can also reassign existing Service IPs, so prefer adding a pool or setting `disabled: true`.

   </details>
