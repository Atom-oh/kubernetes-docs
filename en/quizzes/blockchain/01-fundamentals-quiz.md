# Blockchain Fundamentals Quiz

This quiz tests your understanding of consensus, Merkle trees, finality, and operational characteristics.

## Multiple Choice Questions

1. How should fault models be compared?
   - A) Blockchain is distributed while etcd is single-node
   - B) Compare the chosen consensus: etcd/Raft is CFT; some blockchains use BFT, while permissioned Fabric can also use CFT Raft
   - C) Blockchain provides strong consistency while etcd provides eventual consistency
   - D) etcd does not use cryptography

<details>

<summary>Show Answer</summary>

**Answer: B) Compare the chosen consensus: etcd/Raft is CFT; some blockchains use BFT, while permissioned Fabric can also use CFT Raft**

**Explanation:**
Fabric 3.x also offers SmartBFT. Permissioned membership and the word blockchain do not by themselves imply Byzantine fault tolerance.
</details>

2. Why do additional full-node replicas not automatically raise base-chain write capacity?
   - A) Cryptographic operations are slow
   - B) Replicated full-node validation does not automatically raise base-chain write capacity, although RPC reads can scale
   - C) P2P network bandwidth limits
   - D) Block size limits

<details>

<summary>Show Answer</summary>

**Answer: B) Replicated full-node validation does not automatically raise base-chain write capacity, although RPC reads can scale**

**Explanation:**
Full nodes, light clients and permissioned data-distribution models differ. Avoid saying every node always verifies every transaction or that replica count cannot affect any throughput.
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

7. How should hard-fork client upgrades be managed?
   - A) Container image size grows
   - B) Canary and roll out fork-compatible clients before activation; assess incompatible rollback separately afterward
   - C) Pod restart time increases
   - D) Network policies must be rewritten

<details>

<summary>Show Answer</summary>

**Answer: B) Canary and roll out fork-compatible clients before activation; assess incompatible rollback separately afterward**

**Explanation:**
The protocol activates at a defined point, but installing a compatible client early need not leave the current chain. Complete fleet readiness before the external deadline.
</details>

8. How does key management in blockchain differ decisively from password management in existing systems?
   - A) Keys are longer
   - B) Plan custody and recovery before use; private signing-key loss can be irreversible, and KMS private keys are not exportable
   - C) Keys must be rotated periodically
   - D) Keys are transmitted in plaintext

<details>

<summary>Show Answer</summary>

**Answer: B) Plan custody and recovery before use; private signing-key loss can be irreversible, and KMS private keys are not exportable**

**Explanation:**
Recovery depends on the key origin, contract/account controls and backup design. Protect validator slashing history and do not assume a managed HSM exposes its private key for migration.
</details>
