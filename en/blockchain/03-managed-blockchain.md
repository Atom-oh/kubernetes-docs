# Amazon Managed Blockchain

> **Last Updated**: September 12, 2026

## What This Document Covers

- Which burdens of [self-operation](./02-nodes-on-eks.md) Amazon Managed Blockchain (AMB) takes on, and what it cannot do
- Criteria for choosing managed versus self-operated — and one variable you must include in that judgment
- What the shift in AWS's ledger and blockchain portfolio implies for architecture decisions

## What AMB Consists Of

AMB is not one service but a bundle of components with different characters.

| Component | What it provides |
|---|---|
| **AMB Access — Hyperledger Fabric** | Private/consortium Fabric networks (members, peer nodes, channels) |
| **AMB Access — public chain nodes** | Nodes on public networks such as Ethereum and Bitcoin, managed |
| **AMB Query** | API access to data on supported public chains (without running nodes) |

The three solve different problems — building a consortium network, offloading node operations, and needing **data without nodes** at all.

::: warning Needs verification
AMB's **supported frameworks and chains, regional availability, and preview/GA status vary over time per component.** Confirmed changes include the end of support for the Ethereum Goerli testnet (April 1, 2024) and the Polygon Mumbai testnet (April 15, 2024), and Polygon PoS mainnet was at one point offered in **Public Preview**.

**Before finalizing a design, check the [AMB official documentation](https://docs.aws.amazon.com/managed-blockchain/) and regional availability directly.** This document does not assert the current support status of any specific chain.
:::

## What It Takes On

Contrasting with the burdens covered in the [self-operation document](./02-nodes-on-eks.md) makes the boundary clear.

| Burden when self-operating | With AMB |
|---|---|
| StatefulSet, volume, storage class design | **Handled** |
| Watching disk growth and expanding volumes | **Handled** |
| Initial sync and snapshot management | **Handled** |
| P2P exposure and advertised address configuration | **Handled** |
| Client version upgrades | **Handled** |
| Hard fork response | **Handled** (managed nodes) |
| Fabric certificate issuance infrastructure | **Largely handled** (managed CA) |
| Node availability and monitoring foundation | **Handled** |

**Hard fork response and disk growth management** are the substantive benefits in particular. [Fundamentals](./01-fundamentals.md) called a hard fork "a migration with a deadline" — and now that Ethereum has moved to a twice-yearly schedule, this is **a recurring operational burden.** Managed means AWS handles that schedule.

## What It Cannot Do

This is the crux of the decision.

| Item | Constraint |
|---|---|
| **Client choice** | Limited to the clients and versions AMB offers. You cannot directly control a [client diversity](./02-nodes-on-eks.md) strategy |
| **Fine-grained tuning** | Cache sizes, pruning modes, kernel parameters are not adjustable |
| **Supported chains** | Only what AMB supports. New or small chains are generally unsupported |
| **Archive mode** | Coverage may be limited |
| **Validator operation** | Managed nodes are generally for **queries and transaction submission**. Running a staking validator is a separate matter |
| **Region and network configuration** | Limited to AMB-supported regions and connectivity options |
| **Cost structure** | Per-node billing — heavy usage may be cheaper self-operated |

**Validator operation is an especially important distinction.** AMB Access public chain nodes are for reading chain data and submitting transactions; **participating as a PoS validator to earn staking rewards is a different set of requirements** (key management, signing availability, slashing risk). If staking is the goal, AMB does not solve it.

## Selection Criteria

| Situation | Recommendation |
|---|---|
| **Only reading** chain data | **AMB Query** — no node needed at all |
| Queries plus submission, limited operations staff | **AMB Access managed nodes** |
| Specific client or tuning needed | **Self-operate** |
| **Validator/staking** | **Self-operate** (or a specialized staking service) |
| Chain not supported by AMB | **Self-operate** |
| Consortium Fabric, fast start | **AMB Access Fabric** |
| Fine-grained control over Fabric | **Self-operate with an operator** |
| High traffic, cost optimization goal | **Self-operate** (comparison needed) |

### Decision order

**Step 1 — do you actually need a node?** If you only query data, AMB Query or a third-party RPC provider may be enough. Running nodes is a costly, burdensome choice, so **confirm the need first.**

**Step 2 — do you need control?** If you need any of client choice, tuning, archive, or validator participation, self-operate.

**Step 3 — cost?** Managed bills per node; self-operating costs instances, storage, and staff. There is a crossover where **managed wins with few nodes and self-operating wins with many.**

**Step 4 — can you mix?** Usually yes, and often sensible in practice — for instance, managed for general queries and self-operated for special purposes.

## The Shift in AWS's Ledger and Blockchain Portfolio — A Variable You Must Consider

This is the most important part of this document. **Deciding on technical comparison alone misses a risk.**

### The end of Amazon QLDB

Amazon QLDB (Quantum Ledger Database) was a managed ledger database providing **a cryptographically verifiable, immutable transaction log.** It was announced at re:Invent 2018 and went GA in 2019.

| Date | Event |
|---|---|
| 2018 | Announced at re:Invent |
| 2019 | GA |
| July 2024 | End of support announced |
| **July 31, 2025** | **Service ended** |

The migration path AWS offered was **Amazon Aurora PostgreSQL.** But there is an important point here — **moving to Aurora PostgreSQL loses the cryptographic verifiability that was QLDB's core value.** Ledger-like functionality can be implemented with extensions, but the part that "mathematically proves nothing was tampered with" is not replaced.

### What this implies

QLDB and AMB are different services, and **QLDB's end of support does not imply AMB's.** But there are lessons for architecture decisions.

| Lesson | Practical application |
|---|---|
| **Managed services can also be discontinued** | Especially low-adoption, special-purpose services |
| **A migration path may not be functionally equivalent** | "A replacement exists" is not "it provides the same thing" |
| **The notice period can be short** | Calculate the time your migration would need in advance |
| **Standard technology is easier to move off** | Built on an open-source protocol, you can move to self-operation |

::: warning Needs verification
**AMB's forward roadmap and service continuity plans could not be confirmed in this document.** No end-of-support announcement for AMB as a whole was found at the time of research — but that is not evidence of "no plans to discontinue," it means **"no announcement was found."**

**If you are designing a long-lived system, confirm the service roadmap directly with your AWS account team or solutions architect.** In environments with long system lifespans, such as financial services, this confirmation may matter more than the technical comparison.
:::

### Designing to reduce discontinuation risk

This risk cannot be eliminated, only **mitigated.**

| Mitigation | Content |
|---|---|
| **Stay on standard protocols** | With open protocols like Ethereum or Fabric, you can move to self-operation or another provider if the managed offering disappears |
| **An abstraction layer** | Keep the application from depending directly on AMB APIs. Abstracting the RPC interface makes swapping backends easy |
| **Data independence** | Keep chain data in your own index or warehouse too. Historical data survives a provider change |
| **Custody of your own keys** | Even with keys in AWS KMS/CloudHSM, secure an **export and backup strategy** |
| **Estimate migration time** | Measuring how long node resync and data migration take lets you judge whether you could respond within a notice period |

**The "abstraction layer" is the most effective response.** If the application speaks a standard RPC interface (Ethereum JSON-RPC and the like), the backend can be AMB, self-operated, or third-party. Coupling directly to AMB-specific APIs forfeits that flexibility.

## Integration With AWS Services

One of AMB's substantive benefits is AWS ecosystem integration.

| Integration | Use |
|---|---|
| **IAM** | Access control — IAM policies applied to chain node access |
| **CloudWatch** | Metrics and logs |
| **CloudTrail** | Auditing management API calls |
| **VPC endpoints / PrivateLink** | Private connectivity |
| **KMS** | Key management |

**IAM integration is particularly useful.** A self-operated node's RPC endpoint needs its own authentication scheme (or network-layer control only), whereas AMB can be controlled via IAM — meaning it is managed consistently with your internal permission model.

For private connectivity, concepts from the [VPC Lattice section](../service-mesh/vpc-lattice/README.md) may apply — though **whether AMB and Lattice integrate directly is a separate item to confirm** (the same character as the unconfirmed items in [VPC Lattice Constraints](../service-mesh/vpc-lattice/06-constraints.md)).

## Comparison With Self-Operation

| Item | AMB | Self-operated (EKS/EC2) |
|---|---|---|
| **Initial build time** | Short | Long (including sync) |
| **Operations staff** | Few | Many |
| **Hard fork response** | AWS | **You** |
| **Disk growth management** | AWS | **You** |
| **Client choice** | Limited | **Free** |
| **Tunable scope** | Limited | **Everything** |
| **Validator operation** | Difficult | **Possible** |
| **Supported chains** | AMB's list | **Unconstrained** |
| **Cost structure** | Per-node billing | Instances + storage + staff |
| **IAM integration** | **Built in** | Build it yourself |
| **Service discontinuation risk** | **Exists** | None (open source) |
| **Portability** | Possible on standard protocols | — |

## Summary

- AMB bundles **AMB Access Fabric** (consortium networks), **AMB Access public nodes** (node operations offloaded), and **AMB Query** (data without nodes), each solving a different problem.
- The substantive managed benefits are **hard fork response and disk growth management.** With Ethereum on a twice-yearly fork schedule, that burden is now recurring work.
- Among the things it cannot do, the most important distinction is **validator operation.** Managed nodes are for queries and submission; staking is a different requirement set.
- Decision order: **① do you really need a node → ② do you need control → ③ cost → ④ can you mix.** Many cases are filtered out at step 1.
- **QLDB ended on July 31, 2025**, and its migration path (Aurora PostgreSQL) **does not provide cryptographic verifiability.** It is a case study in managed services being discontinued and replacements not being functionally equivalent.
- The most effective mitigation is **standard protocols plus an abstraction layer.** Avoid coupling directly to AMB-specific APIs and you can change backends.
- **For a long-lived system, confirm the service roadmap directly with your AWS account team.** It may matter more than the technical comparison.

Next: [Financial Services Perspective](./04-financial-services.md) covers regulatory, privacy, and review-board issues.

## References

- [Amazon Managed Blockchain documentation](https://docs.aws.amazon.com/managed-blockchain/)
- [AMB Hyperledger Fabric Developer Guide](https://docs.aws.amazon.com/managed-blockchain/latest/hyperledger-fabric-dev/what-is-managed-blockchain.html)
- [Amazon Managed Blockchain FAQs](https://aws.amazon.com/managed-blockchain/faqs/)
- [AMB Query document history](https://docs.aws.amazon.com/managed-blockchain/latest/ambq-dg/doc-history.html)
- [AMB Access Polygon document history](https://docs.aws.amazon.com/managed-blockchain/latest/ambp-dg/doc-history.html)
- [Running Blockchain Nodes on EKS](./02-nodes-on-eks.md) — the burdens when self-operating
