# Blockchain Fundamentals

> **Last Updated**: September 12, 2026

## What This Document Covers

- The problem blockchain tries to solve, and why the solution becomes a structure where "every node repeats the same work"
- The role of consensus, Merkle trees, P2P, and finality — and the constraint each creates for infrastructure operations
- Why a blockchain node must be treated differently from an ordinary stateful service

## Problem Statement — Agreeing Without a Trusted Arbiter

The starting point for understanding blockchain is not the technology but **the constraints.**

Consider an ordinary distributed system — say, a Kubernetes etcd cluster. etcd also reaches consensus across nodes, but on one premise: **the participating nodes are run by the same organization, and they fail but do not lie.** It handles nodes dying and networks partitioning (crash faults), but not a node deliberately asserting a different value.

Blockchain's premise is different.

| Item | etcd (Raft) | Blockchain |
|---|---|---|
| **Participants** | Same organization, known members | Mutually unknown parties, changing membership |
| **Faults assumed** | Crash faults (death, partition) | **Byzantine faults** (lying, collusion, attack) |
| **Eligibility** | Operator-designated | **Anyone**, on public chains |
| **Can it be reversed** | An operator can intervene | Only what the protocol allows |

This difference is the root of every design decision. **Once you assume participants may lie, you need a way to decide who is right.** That way is the consensus algorithm, and because the basis for that decision must be independently verifiable by everyone, **every node verifies every transaction itself.**

From this comes blockchain's fundamental property.

> **Blockchain is not a system designed for throughput.** It is a system that **deliberately accepts redundancy** in exchange for verifiability and tamper resistance.

Understand that, and every operational characteristic below follows naturally.

## Blocks and Chains — Why a "Chain"

A group of transactions forms a **block**, and each block contains **the hash of the immediately preceding block**.

```
Block N-1               Block N                 Block N+1
┌──────────────┐       ┌──────────────┐        ┌──────────────┐
│ prev_hash:.. │       │ prev_hash: ──┼────────│ prev_hash: ──┤
│ merkle_root  │   ┌───│ merkle_root  │        │ merkle_root  │
│ transactions │───┘   │ transactions │        │ transactions │
└──────────────┘       └──────────────┘        └──────────────┘
      hash ────────────────┘
```

The property this gives is **propagation of tampering.** Change one transaction in block N → block N's hash changes → block N+1's `prev_hash` no longer matches → everything after is invalid.

So **changing the past requires remaking everything after it**, faster than the rest of the network. That is what "immutable" actually means — not physically impossible, but **economically and computationally impractical.**

### Merkle trees — why they are needed

The question is how to summarize a block's transactions. You could simply concatenate and hash them all, but then **checking "is this transaction in this block" requires the whole block.**

A Merkle tree is a binary tree hashing transactions pairwise upward.

```
                merkle_root
               /            \
         H(AB)                H(CD)
        /     \              /     \
     H(A)    H(B)         H(C)    H(D)
      |        |            |        |
     tx A     tx B         tx C     tx D
```

The property that follows is the **Merkle proof.** To prove transaction C is in this block you need only **`H(D)` and `H(AB)`**, not the whole block. The receiver computes `H(C)` → `H(CD)` → `merkle_root` and compares.

Proof size grows as **log N** in the transaction count N. Even in a block with a million transactions, the proof is about 20 hashes.

**Practical significance**: this is what makes light clients possible. You can verify a specific transaction's inclusion without holding the whole chain. It is the basis for the choice "run a full node, or is light verification enough?" when integrating blockchain with existing systems.

## Consensus — Who Writes the Next Block

A consensus algorithm decides two things — **who proposes a block**, and **which side is canonical on a conflict**.

### Main approaches

| Approach | Proposer selection | What the cost really is | Examples |
|---|---|---|---|
| **PoW** (Proof of Work) | The node that first solves a computational puzzle | **Electricity and hardware** | Bitcoin |
| **PoS** (Proof of Stake) | Selected with probability proportional to stake | **Staked capital + slashing on violation** | Ethereum |
| **BFT family** | Votes from a known validator set | Membership management | Hyperledger Fabric (Raft), Tendermint |

### Why a cost is required

This question is the key to understanding consensus. **If proposing a block is free, you can create unlimited candidates and paralyze the network.** In an environment allowing anonymous participation, identity alone cannot stop this (a Sybil attack — one party creating many identities).

PoW makes the cost **computation**; PoS makes it **capital plus slashing risk**. The BFT family **restricts participants in the first place**, sidestepping the problem — which is why it suits consortium chains.

### This is where public and private split

| Type | Participation | Consensus | Throughput | Main use |
|---|---|---|---|---|
| **Public** (permissionless) | Anyone | PoW/PoS | Low | Public assets, interoperability |
| **Private/consortium** (permissioned) | Approved members | BFT/Raft | Relatively high | Inter-enterprise ledgers, regulated environments |

**This is why financial services choose consortium chains.** When participants are known, Sybil defense is unnecessary, and then consensus can be BFT voting without PoW's electricity or PoS's stake. Throughput rises and finality gets faster. The price is **giving up decentralization** — a party controlling membership exists. [Financial Services Perspective](./04-financial-services.md) covers that trade-off.

## Finality — The Most Important Concept Operationally

**Finality is "the point at which a transaction is guaranteed not to be reversed."** From an infrastructure perspective this is the most important concept, and it is frequently overlooked.

### Probabilistic vs absolute finality

| Type | Meaning | Example |
|---|---|---|
| **Probabilistic** | The more blocks pile up, the more the reversal probability decays exponentially. **Never exactly zero** | Bitcoin's PoW |
| **Absolute/economic** | Once protocol conditions are met, reversing incurs enormous loss | Ethereum PoS finalized checkpoints |
| **Immediate** | Settled at the end of a consensus round | BFT family |

### Why this is an operations problem

**The data a node returns may not be finalized yet.**

Ask a blockchain node "tell me the result of this transaction" and it answers **based on the latest chain it knows.** If that latest block is later reorganized (a reorg), the answer changes.

The real incident patterns this creates:

| Pattern | Result |
|---|---|
| Confirming a deposit against the latest block and acting on it | A reorg erases the deposit after the withdrawal already went out |
| A health check confirming only "node alive" | A node behind on sync **returns stale data** |
| A load balancer spreading across several nodes | Chain heights differ per node → **different answers to the same question** |

**So application design must include a "process after N confirmations" (confirmation depth), and that value depends on the chain's finality characteristics.** This cannot be solved by infrastructure alone — it is a contract with the application.

What infrastructure can do:

- **Include sync state in the health check** — define readiness as "within N blocks of the chain head," not "alive"
- **Monitor chain-height divergence across nodes** — remove from load balancing when divergence grows
- **Expose reorg occurrences as a metric** — so the application can respond

## P2P Networking — Why It Differs from Ordinary Services

Blockchain nodes communicate **peer-to-peer rather than client-server.** That creates friction with the Kubernetes networking model.

### Gossip protocols

When a new block or transaction appears, it is **propagated to neighboring peers**, who propagate to theirs. That is how everyone comes to know.

Characteristics:

- No central broker → no single point of failure
- **The same data arrives redundantly over several paths** → bandwidth is spent on duplicates
- Propagation takes time → each node's notion of "latest" differs (connecting back to the finality problem above)

### Friction in a Kubernetes environment

| What blockchain P2P needs | Kubernetes default |
|---|---|
| **Stable peer identity** (node ID, address) | Pod IPs change on restart |
| **Accepting inbound connections** — other peers connect to me | Pods are not directly reachable from outside by default |
| **Persistence of the peer list** | State is lost on Pod replacement |
| **Advertising a fixed port** | Service port mapping |

So blockchain nodes default to **StatefulSet + headless Service** — they need stable names and ordering. Accepting inbound P2P requires additional exposure design. [Running Blockchain Nodes on EKS](./02-nodes-on-eks.md) covers the specifics.

## State and Storage — Why Rebuilding Is Hard

A blockchain node keeps two things.

| Data | Nature | Size |
|---|---|---|
| **Block history** | Append-only log. The past is immutable | Grows continuously |
| **Current state** | Balances, contract storage. Derivable by replaying blocks | Grows, but smaller than history |

**The key property: state is replayable from history, but that replay takes a long time.**

Replaying and verifying every block from genesis (full sync) takes time proportional to the chain's age. Hence alternative sync methods exist.

| Method | What it does | Trade-off |
|---|---|---|
| **full sync** | Verify and replay everything from genesis | Highest confidence, **slowest** |
| **snap/fast sync** | Fetch a recent state snapshot from peers and verify only after | Much faster, trusts snapshot-providing peers |
| **checkpoint sync** | Start from a trusted checkpoint | Fastest, trusts the checkpoint's source |
| **Snapshot restore** | Restore an operator-kept data directory | Fast, requires managing snapshot freshness and consistency |

**Operational conclusion**: you must not lose state when replacing a Pod. Losing it means a long sync during which that node cannot serve. This is why a persistent volume is **not optional but mandatory** for a blockchain node.

### Archive nodes — a separate consideration

A node that can query "state at an arbitrary past point" is an archive node. It retains all intermediate state, so it needs **far more storage** than a regular node.

**A design judgment is needed here**: first confirm you actually need archive capability. Most applications need only recent state, and if historical queries are needed, handling them with an indexing service or data warehouse is more cost-effective.

## Key Management — Lose It and It Is Over

In blockchain, **identity and authority are the private key.** This creates a decisive difference from existing systems.

| Existing systems | Blockchain |
|---|---|
| Forget a password and reset it | **Lose the key and the assets/authority are gone permanently** |
| An administrator can freeze a compromised account | No party exists to reverse it (unless the protocol allows) |
| Audit logs allow after-the-fact tracing | A signed transaction, once final, cannot be reversed |

**So the nature of the backup strategy differs.** Chain data can be re-fetched from the network, so backing it up has low value. Keys, by contrast, **must be backed up**, and **the backup itself is an exposure risk.**

That is why HSMs and AWS KMS/CloudHSM matter in blockchain infrastructure. Validators in particular have the contradictory requirement that **the key must be online to sign yet must not leak.** [Financial Services Perspective](./04-financial-services.md) treats this problem.

## Operational Characteristics — What Follows From All This

Gathering the operational characteristics these concepts create:

| Blockchain's design | Resulting operational characteristic | Implication in Kubernetes |
|---|---|---|
| Every node verifies every transaction | **Adding nodes does not increase throughput** | Scale-out is for availability and read distribution, not throughput |
| State accumulates locally | **Pod replacement is very expensive** | StatefulSet + persistent volume mandatory, consider node affinity |
| Chain sync lags | **"Alive" and "able to serve" are different** | Include sync state in readiness |
| Finality is not immediate | **Latest data is not final data** | Confirmation depth as an application contract |
| P2P gossip | **Needs inbound connections and stable identity** | Headless Service, additional exposure design |
| Hard forks change the protocol | **The whole network switches at a fixed point, simultaneously** | Mismatched with the rolling-update model — planning required |
| Keys are authority | **Key loss = permanent loss** | KMS/HSM, separate backup strategies for keys and data |
| Redundant verification is the point | **Steady CPU and IOPS consumption** | A poor fit for burst-oriented resource settings |

**This table is the core of this section.** Every concrete recommendation in document 2 derives from it.

## Hard Forks — The Biggest Clash with the Kubernetes Operating Model

A protocol change that is not backward compatible is a **hard fork.** The whole network switches to new rules at a set block height or time, and **nodes that do not switch remain on a different chain.**

Where it clashes with Kubernetes conventional wisdom:

| Kubernetes convention | At a hard fork |
|---|---|
| Gradual transition via rolling update | **Everything must already be switched** at the set point |
| Canary a subset first | The canary node leaves the network at the fork |
| Roll back if there are problems | Rolling back leaves that node on the old chain |
| Upgrades are on the ops team's schedule | **The schedule is set externally** |

**Practical recommendation**: treat a hard fork not as a deployment but as **a migration with a deadline.** Subscribe to client release notes, upgrade well before the fork date, and validate on a testnet first.

Ethereum moved to a **twice-yearly hard fork schedule** starting in 2025 — meaning this migration has become **routine work.** [Running Blockchain Nodes on EKS](./02-nodes-on-eks.md) covers concrete cases and schedule management.

## Summary

- Blockchain's premise is **Byzantine faults** — the assumption that participants may lie. That is fundamentally different from etcd (crash faults).
- Because of that assumption, **every node verifies every transaction**, making it a system that **accepts redundancy for verifiability rather than throughput.**
- The `prev_hash` chain propagates tampering, and **Merkle trees** enable log-N-sized inclusion proofs (the basis for light clients).
- Consensus needs a cost because of **Sybil defense.** Restricting participants (consortium) removes that need, allowing BFT with better throughput and finality at the cost of decentralization.
- **Finality is the most important concept operationally.** Latest data is not final data, so put sync state in readiness and make confirmation depth an application contract.
- State is replayable but **replay takes a long time**, which is why persistent volumes are mandatory.
- **A hard fork is a migration with a deadline, not a deployment.** Ethereum's move to twice-yearly forks made this routine work.

Next: [Running Blockchain Nodes on EKS](./02-nodes-on-eks.md) translates these characteristics into actual configuration.

## References

- [Ethereum Developer Documentation](https://ethereum.org/developers/docs/) — consensus, nodes, clients
- [Ethereum — Proof of Stake](https://ethereum.org/developers/docs/consensus-mechanisms/pos/)
- [Hyperledger Fabric Documentation](https://hyperledger-fabric.readthedocs.io/) — the structure of a permissioned chain
- [Bitcoin Developer Guide](https://developer.bitcoin.org/devguide/) — PoW and Merkle trees
- [Cluster Architecture — etcd and Raft](../core/01-cluster-architecture.md) — comparison with crash-fault consensus
