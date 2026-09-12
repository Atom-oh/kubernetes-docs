# Blockchain Fundamentals Quiz

This quiz tests your understanding of consensus, Merkle trees, finality, and operational characteristics.

## Multiple Choice Questions

1. What is the fundamental difference in premise between blockchain and etcd (Raft)?
   - A) Blockchain is distributed while etcd is single-node
   - B) etcd assumes only crash faults (death, partition) while blockchain assumes Byzantine faults (lying, collusion)
   - C) Blockchain provides strong consistency while etcd provides eventual consistency
   - D) etcd does not use cryptography

<details>

<summary>Show Answer</summary>

**Answer: B) etcd assumes only crash faults (death, partition) while blockchain assumes Byzantine faults (lying, collusion)**

**Explanation:**
etcd's premise is that participating nodes are run by the same organization and fail but do not lie. Blockchain assumes mutually unknown parties who may deliberately assert different values. This difference is the root of every design decision — assuming lying participants requires a way to decide who is right, and since that basis must be independently verifiable by everyone, every node verifies every transaction itself.
</details>

2. What supports the claim "blockchain is not a system designed for throughput"?
   - A) Cryptographic operations are slow
   - B) It deliberately has every node redundantly verify every transaction, for the sake of verifiability and tamper resistance
   - C) P2P network bandwidth limits
   - D) Block size limits

<details>

<summary>Show Answer</summary>

**Answer: B) It deliberately has every node redundantly verify every transaction, for the sake of verifiability and tamper resistance**

**Explanation:**
Assuming Byzantine faults means the basis for decisions must be independently verifiable by everyone, so every node verifies every transaction. This redundancy is not a side effect but **deliberate design.** From it follows directly the operational characteristic "adding nodes does not increase throughput" — adding nodes only adds parties repeating the same work. Scale-out is therefore for availability and read distribution, not throughput.
</details>

3. What is the key benefit a Merkle tree provides?
   - A) It compresses block size
   - B) A Merkle proof of inclusion grows as log N in transaction count N, enabling verification without the full chain — the basis for light clients
   - C) It guarantees transaction ordering
   - D) It speeds up consensus

<details>

<summary>Show Answer</summary>

**Answer: B) A Merkle proof of inclusion grows as log N in transaction count N, enabling verification without the full chain — the basis for light clients**

**Explanation:**
Thanks to hashing transactions pairwise upward in a binary tree, proving a transaction's inclusion needs only the sibling hashes. Even in a block with a million transactions, the proof is about 20 hashes. This makes light clients possible and is the basis for the choice "run a full node, or is light verification enough?" when integrating blockchain with existing systems.
</details>

4. What is the fundamental reason consensus requires a cost (PoW's electricity, PoS's stake)?
   - A) To reward validators
   - B) Sybil defense — without a cost, one party can create unlimited identities and block candidates and paralyze the network
   - C) To regulate block production rate
   - D) To conserve network bandwidth

<details>

<summary>Show Answer</summary>

**Answer: B) Sybil defense — without a cost, one party can create unlimited identities and block candidates and paralyze the network**

**Explanation:**
In an environment allowing anonymous participation, identity alone cannot stop one party creating many identities (a Sybil attack). PoW makes the cost computation; PoS makes it capital plus slashing risk. The BFT family **restricts participants in the first place**, sidestepping the problem and allowing consensus by voting without PoW's electricity or PoS's stake. That is the technical basis for financial services choosing consortium chains.
</details>

5. Why is finality the most important concept for infrastructure operations?
   - A) It determines consensus speed
   - B) The latest data a node returns may not be finalized, so the answer changes on a reorg
   - C) It determines block size
   - D) It determines node storage capacity

<details>

<summary>Show Answer</summary>

**Answer: B) The latest data a node returns may not be finalized, so the answer changes on a reorg**

**Explanation:**
A node answers based on the latest chain it knows, and if that block is later reorganized the answer changes. This leads to real incidents — confirming a deposit against the latest block and acting on it, only for a reorg to erase it; or a load balancer spreading across nodes whose chain heights differ, giving different answers to the same question. So confirmation depth is mandatory in the application, and infrastructure must put sync state in readiness and monitor chain-height divergence.
</details>

6. Why is a persistent volume mandatory for a blockchain node?
   - A) Chain data cannot be recovered from the network
   - B) State is replayable from history, but that replay takes a long time during which the node cannot serve
   - C) Kubernetes requires persistent volumes for StatefulSets
   - D) Keys are stored in the data directory

<details>

<summary>Show Answer</summary>

**Answer: B) State is replayable from history, but that replay takes a long time during which the node cannot serve**

**Explanation:**
A node's state (balances, contract storage) can be derived by replaying block history, so it is theoretically rebuildable. But a full sync verifying and replaying from genesis takes time proportional to the chain's age, and at hundreds of GB to several TB that can be days. Losing state on Pod replacement means the node cannot serve during that time, so a persistent volume is not optional but mandatory.
</details>

7. Where does a hard fork clash with the Kubernetes operating model?
   - A) Container image size grows
   - B) Rolling updates, canaries, and rollbacks all break down, and the whole network must already be switched at a fixed point
   - C) Pod restart time increases
   - D) Network policies must be rewritten

<details>

<summary>Show Answer</summary>

**Answer: B) Rolling updates, canaries, and rollbacks all break down, and the whole network must already be switched at a fixed point**

**Explanation:**
A canary node leaves the network at the fork, rolling back leaves that node on the old chain, and the upgrade schedule is set externally. So a hard fork must be treated as **a migration with a deadline** rather than a deployment. Since Ethereum moved to a twice-yearly hard fork schedule in 2025, this migration has become **routine work.**
</details>

8. How does key management in blockchain differ decisively from password management in existing systems?
   - A) Keys are longer
   - B) Losing a key permanently forfeits assets and authority with no party able to reverse it, making backups absolute while the backup itself is an exposure risk
   - C) Keys must be rotated periodically
   - D) Keys are transmitted in plaintext

<details>

<summary>Show Answer</summary>

**Answer: B) Losing a key permanently forfeits assets and authority with no party able to reverse it, making backups absolute while the backup itself is an exposure risk**

**Explanation:**
Existing systems let you reset a forgotten password and let an administrator freeze a compromised account; in blockchain no party can reverse it unless the protocol allows. So the nature of backup strategy differs — chain data can be re-fetched from the network so backing it up has low value, while keys must be backed up and that backup becomes an exposure path. This is why HSMs and KMS/CloudHSM matter, and validators face the contradictory requirement of a key that must be online to sign yet must not leak.
</details>
