# Running Blockchain Nodes on EKS Quiz

This quiz tests your understanding of StatefulSet configuration, storage, health checks, and hard fork management.

## Multiple Choice Questions

1. What criterion is offered for deciding whether to run blockchain nodes on EKS?
   - A) Whether you have 10 or more nodes
   - B) Whether there is other workload around the node (indexers, APIs, monitoring) — a node standing alone is simpler on EC2
   - C) Whether the chain is public or private
   - D) Whether you run a validator

<details>

<summary>Show Answer</summary>

**Answer: B) Whether there is other workload around the node (indexers, APIs, monitoring) — a node standing alone is simpler on EC2**

**Explanation:**
Blockchain nodes fit poorly with some Kubernetes strengths (fast rescheduling, horizontal scaling, rolling updates). The reasons to still use EKS are operational standardization, managing multiple chains and environments, and integration with surrounding components. If indexers, APIs, and monitoring are already in the cluster, keeping the node with them is sensible; for running a single validator, EKS's abstraction adds complexity without benefit.
</details>

2. Why must `terminationGracePeriodSeconds` be generous for a blockchain node StatefulSet?
   - A) Image pulls take time
   - B) The client must flush in-memory state to disk on shutdown, and a forced kill can corrupt the database and require a resync
   - C) P2P peers must be notified of the shutdown
   - D) Volume detachment takes time

<details>

<summary>Show Answer</summary>

**Answer: B) The client must flush in-memory state to disk on shutdown, and a forced kill can corrupt the database and require a resync**

**Explanation:**
The default 30 seconds is usually insufficient. Blockchain clients cache state in memory and must flush it on shutdown. A forced kill (SIGKILL) can leave the DB mid-write and corrupted, requiring a resync that takes hours to days. For the same reason memory limits should be generous — an OOM kill is also a forced kill.
</details>

3. Why does IOPS bottleneck before capacity for blockchain node storage?
   - A) Chain data is stored compressed
   - B) Traversing and updating the state trie (Merkle Patricia Trie and similar) touches scattered keys — a random access pattern
   - C) Blocks are only ever written sequentially
   - D) Snapshots are taken frequently

<details>

<summary>Show Answer</summary>

**Answer: B) Traversing and updating the state trie (Merkle Patricia Trie and similar) touches scattered keys — a random access pattern**

**Explanation:**
A blockchain node's disk use is heavily random read and write. With capacity to spare but insufficient IOPS, sync falls behind, and a node that is behind cannot serve. That is why gp3's ability to **set IOPS and throughput independently of capacity** is the key advantage. gp2 fixes IOPS per unit of capacity, so raising IOPS meant buying capacity you did not need.
</details>

4. Why must sync state not go into the liveness probe?
   - A) Sync checks add RPC load
   - B) A lagging node gets restarted, falls further behind from the restart, and is restarted again — an infinite loop
   - C) liveness probes do not support the exec method
   - D) Sync state is only queryable in readiness

<details>

<summary>Show Answer</summary>

**Answer: B) A lagging node gets restarted, falls further behind from the restart, and is restarted again — an infinite loop**

**Explanation:**
Liveness should only check "is the process alive and responding." Putting sync there kills lagging nodes, and the restart delays sync further so they can never catch up. Conversely **readiness must include sync** — without it, a lagging node takes traffic and returns wrong data based on a stale chain. This split is the crux of blockchain node health checks.
</details>

5. You opened P2P inbound but no peers arrive. What is the classic cause?
   - A) A missing Security Group rule
   - B) The advertised address is not configured — the Pod IP seen inside the container differs from the externally reachable address, so other peers cannot connect
   - C) Only the UDP port was opened, not TCP
   - D) The peer limit is set to 0

<details>

<summary>Show Answer</summary>

**Answer: B) The advertised address is not configured — the Pod IP seen inside the container differs from the externally reachable address, so other peers cannot connect**

**Explanation:**
P2P protocols advertise their own address to peers. If the address seen inside the container (the Pod IP) differs from the externally reachable address (node public IP, LB address), peers cannot connect to the advertised address. Most clients offer an option like `--nat extip:<addr>`, and **without it, opening inbound brings no peers.** Since each Pod must advertise a different address, initialization logic using the StatefulSet ordinal or downward API is needed.
</details>

6. Why be careful with CPU limits on blockchain nodes while also dedicating nodes to them?
   - A) CPU limits affect memory usage
   - B) Dedicated nodes reduce tenant contention, but system daemons still require reservations and headroom
   - C) CPU limits are ignored on dedicated nodes
   - D) Guaranteed QoS requires dedicated nodes

<details>

<summary>Show Answer</summary>

**Answer: B) Dedicated nodes reduce tenant contention, but system daemons still require reservations and headroom**

**Explanation:**
Kubelet, CNI/CSI, monitoring and OS services remain. Test sustained load and node health even when application CPU limits are omitted.
</details>

7. What operational impact did Pectra's EIP-7251 have?
   - A) Node disk requirements halved
   - B) EIP-7251 permits eligible validator consolidation, but validator keys are not one-to-one with processes or VMs
   - C) The execution and consensus clients merged into one
   - D) The hard fork schedule dropped to once a year

<details>

<summary>Show Answer</summary>

**Answer: B) EIP-7251 permits eligible validator consolidation, but validator keys are not one-to-one with processes or VMs**

**Explanation:**
A validator client can manage many keys. Reduced validator records/key-management work does not prove proportional infrastructure or cost reduction.
</details>

8. Which maintenance action addresses Fabric MSP/TLS certificate expiry?
   - A) Orderer Raft consensus failure
   - B) Monitor MSP/TLS certificate expiry and rehearse renewal alongside channel, policy and consensus operations
   - C) Chaincode execution errors
   - D) Channel policy conflicts

<details>

<summary>Show Answer</summary>

**Answer: B) Monitor MSP/TLS certificate expiry and rehearse renewal alongside channel, policy and consensus operations**

**Explanation:**
Certificate expiry is a concrete risk, not a measured most-common-outage ranking in this material. Validate operator compatibility and peer transaction validation as well.
</details>

9. What verification is essential after a hard fork?
   - A) Restarting Pods
   - B) Comparing block hashes with other nodes and a public explorer to confirm you are on the same chain
   - C) Recalculating storage capacity
   - D) Resetting the peer list

<details>

<summary>Show Answer</summary>

**Answer: B) Comparing block hashes with other nodes and a public explorer to confirm you are on the same chain**

**Explanation:**
An incompatible client may stop following the canonical chain or diverge after activation; process liveness alone does not establish correctness. Compare hashes at the **same block height and finality state** across independent trusted nodes or explorers, accounting for normal propagation and sync lag. Combine that evidence with client version, fork recognition and synchronization checks rather than treating unrelated latest heads or one explorer as definitive.
</details>
