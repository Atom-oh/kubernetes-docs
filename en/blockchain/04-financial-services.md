# Financial Services Perspective

> **Last Updated**: September 13, 2026

## What This Document Covers

- Why financial services go to consortium rather than public chains, and what that choice actually leaves you
- Where privacy requirements collide with the premise that "everyone sees the same ledger," and the available resolutions
- Which items in key management, regulation, and integration with existing infrastructure become real review-board issues

## First: Filtering Out Cases Where Blockchain Is Not the Answer

The most frequent problem in financial-services blockchain evaluations is **proceeding when the technology does not fit the problem.** This document starts with that screen.

As seen in [Fundamentals](./01-fundamentals.md), blockchain's essence is **"agreeing without a trusted arbiter."** The price is throughput and complexity. So:

| Situation | Is blockchain right? |
|---|---|
| A single organization owns and controls the data | **No** — an ordinary database is better in every respect |
| An arbiter exists and everyone trusts them | **No** — the arbiter's database suffices |
| Only tamper detection is needed | **Usually no** — hash chains, signed logs, or WORM storage suffice |
| Multiple mutually distrusting institutions update **shared state** | **Worth evaluating** |
| Third parties must be able to **verify independently** | **Worth evaluating** |
| Inter-institution reconciliation cost is genuinely large | **Worth evaluating** |

**"Only tamper detection is needed" is an especially common misconception.** If the goal is an audit trail or integrity proof, you can achieve it without blockchain — a signed append-only log, a hash chain, or object storage WORM (Write Once Read Many) features — with far simpler operations.

[The Amazon QLDB case](./03-managed-blockchain.md) is instructive here. QLDB provided precisely "a cryptographically verifiable ledger with a central trusted party," on the premise that **many problems are satisfied by that.** The service ended, but the problem definition remains valid — many requirements do not need full decentralized consensus.

**Practical recommendation**: if you cannot write "why this problem must have no arbiter" in one sentence, compare the non-blockchain alternatives first.

## Why Consortium

Financial services choose consortium (permissioned) chains over public ones not for one reason but because of several constraints combined.

| Constraint | The problem on a public chain | In a consortium |
|---|---|---|
| **Participant identification (KYC/AML)** | Transacting with anonymous parties — conflicts with anti-money-laundering obligations | Members are identity-verified institutions |
| **Data sovereignty and location** | Data replicated to nodes worldwide | Only on nodes the participating institutions control |
| **Throughput and latency** | Low throughput, probabilistic finality | Immediate finality via BFT, higher throughput |
| **Governance** | Cannot control protocol changes | The consortium decides |
| **Fee volatility** | Cost varies with network congestion | Infrastructure cost only |
| **Error handling** | Incorrect transactions cannot be reversed | Governance procedures can respond |

**The first two are decisive.** Financial institutions have a legal obligation to identify counterparties and must control the location of and access to customer data. Public chains structurally conflict with both.

### What choosing consortium actually leaves you

Here is where honesty is required. Going consortium **removes much of blockchain's original value proposition.**

| Public chain value | In a consortium |
|---|---|
| Censorship resistance | ✗ A party controls membership |
| Permissionless participation | ✗ Approval required |
| No arbiter needed | △ **The consortium operator is effectively an arbiter** |
| Tamper resistance | △ A colluding majority of members can do it |
| Independent verification | ○ Valid among members |
| **Reduced inter-institution reconciliation cost** | **○ Remains** |
| **A single version of shared state** | **○ Remains** |

So a consortium chain's substantive value narrows to **"making institutions see the same data so reconciliation work disappears."** That is real value, but it is a different story from "decentralized" or "trustless."

**This distinction matters in review.** Write "decentralized, operating without trust" in a proposal and the review asks "then who controls membership?" — and if the answer is "the consortium secretariat," the logic collapses. **Defining the value as "reduced inter-institution reconciliation cost" from the start is defensible.**

## Privacy — The Hardest Problem

### The fundamental tension

Blockchain's premise is **"everyone sees the same ledger and verifies it themselves."** A financial transaction's requirement is **"third parties who are not counterparties must not see my transaction."**

**These conflict directly.** To verify you must see; to preserve privacy it must not be seen.

There are ways to resolve the tension, each with a different price.

### Approaches and trade-offs

| Approach | Principle | Price |
|---|---|---|
| **Channel separation** (Fabric) | A separate ledger per transaction group. Only channel members hold the data | Operational complexity per channel. **Atomic transactions across channels are hard** |
| **Private Data Collection** (Fabric) | Only hashes on the ledger; actual data only on authorized peers | Data distribution and lifecycle burden |
| **Zero-knowledge proofs (ZKP)** | **Prove a statement true** without revealing its content | Computational cost, circuit design difficulty, verifiability review |
| **Off-chain storage** | Sensitive data off-chain, only hashes/pointers on-chain | The off-chain store's availability and integrity become a new dependency |
| **Encrypted storage** | Ciphertext on the chain | **Key management becomes access control** — a key leak exposes the entire past |

### Which to choose

**Channel separation is the most common starting point.** The concept is simple, Fabric provides it natively, and "who can see what" is explicit and easy to explain in review.

Its limit is **transactions across channels.** With an A-B channel and a B-C channel, a transaction moving value A→C is hard to process atomically. If your business flow has that shape, the design needs rethinking.

**The trap in encrypted storage** deserves emphasis. **A blockchain cannot delete data.** Ciphertext remains on the ledger permanently, and a key leak **exposes the entire past retroactively.** With an ordinary database you could delete or re-encrypt; here you cannot. Designs that put long-retention data on-chain encrypted must explicitly evaluate this risk.

**ZKP is powerful but hard to get through review.** Explaining "proving truth without revealing content" to a reviewer and assuring the correctness of the implementation are separate challenges. If the scheme requires a trusted setup, that setup's trustworthiness becomes an issue too.

### Conflict with the right to erasure

Privacy regulation's deletion requirements conflict with blockchain immutability.

**The usual response is "do not put personal data on the chain"** — keep only identifiers or hashes on-chain and personal data off-chain where it can be deleted. But a hash is still lookupable by someone who knows the original (rainbow-table attacks), so this is combined with deleting the salt or key to make recovery practically impossible (crypto-shredding).

::: warning Needs verification
**The legal interpretation of privacy regulations' (Korea's PIPA, GDPR, etc.) deletion requirements versus blockchain immutability varies by jurisdiction and case, and this document is not legal advice.**

Whether hashes or ciphertext constitute personal data, and whether crypto-shredding satisfies a deletion obligation, must be **confirmed with your legal/compliance function and regulators' interpretations.** That confirmation comes before technical design.
:::

## Key Management — The Heaviest Item in Financial Services

[Fundamentals](./01-fundamentals.md) said "keys are authority and losing them is final." Here is why that is especially heavy in financial services.

### Contradictory requirements

| Requirement | The conflicting requirement |
|---|---|
| The key must be **online** to sign transactions | The key must be **isolated** |
| Availability — a signing delay means service interruption | Multi-approval — no single party may sign |
| Backups mandatory — loss is permanent | Backups are an exposure path |
| Auditable — who signed what | The key itself must not be exposed |

This contradiction is **the hardest part to design** in financial-services blockchain.

### Available mechanisms

| Mechanism | What it provides | Limits |
|---|---|---|
| **HSM** (CloudHSM, on-premises HSM) | Keys never leave the hardware. FIPS certified | Verify supported curves/algorithms. Cost |
| **AWS KMS** | Managed keys, IAM integration, CloudTrail auditing | Verify whether it supports the signature algorithms the blockchain requires |
| **MPC** (Multi-Party Computation) | Keys held **distributed**, shares combined to sign — no complete key exists anywhere | Implementation complexity, vendor dependency |
| **Multisig** | N-of-M signatures required at the protocol level | Needs chain/contract support. Higher transaction cost |
| **Cold/hot separation** | Bulk offline, only small amounts online | Operational procedure burden |

### Support by curve — it splits along the layer

**This is the assumption that most often collapses in key management design.** A plan built on "we will use KMS" breaks on algorithm support — and the key point is that **Ethereum's two layers use different curves.**

| Layer | Curve | Used for | AWS KMS / CloudHSM |
|---|---|---|---|
| **Execution layer** (accounts, transactions) | **secp256k1** | Transaction signing, EOA accounts | **✅ Supported** — KMS key spec `ECC_SECG_P256K1`, usage restricted to `SIGN_VERIFY` |
| **Consensus layer** (validators) | **BLS12-381** | Block proposal and attestation signing | **❌ Not supported** |

**The execution layer is a solved problem.** Create an `ECC_SECG_P256K1` key in KMS, use it with `SIGN_VERIFY`, and you can sign Ethereum transactions. AWS documents this pattern in official blog posts. Bitcoin uses the same curve.

**The consensus layer is the problem.** BLS12-381 is not among KMS's key specs and CloudHSM does not support it either. **So a design that puts validator signing keys in KMS/HSM simply does not work.**

AWS's proposed alternative is **Nitro Enclaves** — running a signer such as Web3Signer inside an isolated execution environment so the key never leaves the enclave. Key generation (EIP-2335 format BLS12-381 keystores) also needs a separate approach.

**Design implication**: on top of the validator key contradiction covered above (continuously online + isolated + no double signing), there is one more constraint — **the standard answer of "protect the key in an HSM" does not apply.** If you are evaluating validator operations, this is the first branch point away from a KMS-based design.

::: warning Needs verification
The support status above is as of the time of research, and **HSM support for BLS12-381 has been a long-discussed topic in the industry, so it may change.** Support by curve for protocols other than Ethereum (chains using Ed25519, for example) also needs separate confirmation.

**Before designing, check the current list in the [KMS key spec reference](https://docs.aws.amazon.com/kms/latest/developerguide/symm-asymm-choose-key-spec.html) and always verify with a PoC that the actual signature validates on the target chain.**
:::

### The special case of validator keys

Running a PoS validator adds a problem.

- **The signing key must be online continuously** — signing opportunities arrive every slot
- **Signing in two places at once means slashing** — stake is forfeited. Especially dangerous in HA configurations
- So **"redundancy for high availability" itself creates the risk**

This runs directly against ordinary HA wisdom. It must be **strictly active-passive rather than active-active**, and failover must guarantee the old node has definitively stopped signing (fencing). If you are evaluating validator operations, this design is the central challenge.

## Regulation and Review Issues

The questions that actually come up in financial-services review:

| Issue | The question | The answer to prepare |
|---|---|---|
| **Necessity** | Why not an ordinary database? | "Why this must have no arbiter" in one sentence |
| **Participant control** | Who controls membership, and how? | Governance structure and join/leave procedures |
| **Data location** | Where is data replicated? | Node locations and regional control measures |
| **Access control** | Who can see what? | Channel/PDC design, encryption policy |
| **Deletion requests** | How do you respond to personal-data deletion? | A design that keeps personal data off-chain |
| **Key management** | Where are keys and who can reach them? | HSM/KMS/MPC structure and separation of duties |
| **Error correction** | How do you reverse an incorrect transaction? | Governance procedure. **Must be answered with process, not technology** |
| **Availability** | On node or consortium failure? | Failure domains, independent operation per member |
| **Auditing** | What does an auditor check, and how? | Audit access method, logs |
| **Upgrades** | Who decides protocol changes? | Consortium governance |
| **Termination plan** | If the service is shut down, what about the data? | **An exit strategy** |
| **Vendor/service lock-in** | If the managed service is discontinued? | Standard protocols, abstraction layer ([AMB document](./03-managed-blockchain.md)) |

### The two items most often underprepared

**① Error correction — "it cannot be reversed" becomes a weakness in review.**

The immutability marketed as blockchain's strength is **a problem** in financial operations. Incorrect transactions, mistaken transfers, and system errors do happen, and financial institutions have obligations and procedures to correct them.

**The answer is process, not technology.** The standard approach is not "roll back the chain" but **"issue a compensating transaction"** — the original remains and an offsetting transaction is added to correct the outcome. It is the same concept as a reversing entry in accounting. Document that procedure and its approval authority for review.

**② Exit strategy — almost never prepared.**

What happens to data and obligations when a consortium dissolves, a member withdraws, or the system is shut down? Financial data carries retention obligations, so **"we turned off the chain" is not the end.**

What to prepare: the ledger's export format, who retains it, how a withdrawing member's data is handled, and how records are accessed. **This should be stated in the consortium agreement**, and the technical design must support it.

## Integration With Existing Financial Infrastructure

The reality is that blockchain sits **alongside** existing systems rather than replacing them. Practical problems arise at the integration points.

| Integration problem | Content |
|---|---|
| **Finality mismatch** | Existing systems treat a DB commit as final. A chain needs confirmation depth → **state management at the boundary** |
| **No atomicity** | An existing DB transaction and a chain transaction **cannot be bound into one atomic unit** |
| **Throughput gap** | Existing systems are far faster → the chain becomes the bottleneck. Queueing/batching needed |
| **Reversibility difference** | Existing systems can roll back, chains cannot → failure-scenario design is asymmetric |
| **Time synchronization** | Reconciling block time with existing system time |

**"No atomicity" is the most substantive problem.** If a failure occurs between writing to the DB and submitting the chain transaction, you get an inconsistency. Since they cannot be bound in a distributed transaction, you need eventual-consistency approaches such as **the Saga or outbox pattern**, connected to the **compensating transaction procedure** above.

This is an architecture decision, so **address it early in design.** Bolted on later, data consistency problems surface in production.

## A Realistic Adoption Path

| Stage | Content |
|---|---|
| **1. Validate the problem** | Confirm blockchain is needed. Compare alternatives (ordinary DB, signed logs, WORM) |
| **2. Secure participating institutions** | **With only one institution, blockchain has no value.** Willingness from at least 2–3 institutions is a precondition |
| **3. Agree on governance** | Before technology. Membership, decision-making, disputes, exit |
| **4. Design privacy** | Channel/PDC structure. Together with reviewers |
| **5. Legal/compliance confirmation** | Deletion requests, data location, audit requirements |
| **6. PoC** | Technical validation plus **measuring performance and operational burden** |
| **7. Pilot** | Real transactions in limited scope |
| **8. Operations** | [Node operations](./02-nodes-on-eks.md), monitoring, certificate renewal, hard fork/upgrades |

The point of this table is that **stages 2 and 3 come before technology.** Even a successful technical validation goes nowhere without participating institutions or agreed governance. In practice, many financial-services blockchain projects stopped at this stage.

## Summary

- **Filter out cases where blockchain is not the answer first.** If you cannot write "why this must have no arbiter" in one sentence, compare alternatives. If only tamper detection is needed, signed logs or WORM suffice.
- The decisive reasons financial services go consortium are **KYC/AML obligations and data sovereignty.** Throughput and governance are secondary benefits.
- Choosing consortium **removes much of blockchain's original value.** What remains substantively is **"reduced inter-institution reconciliation cost,"** and defining value that way is defensible in review.
- Privacy and verifiability **conflict directly.** Channel separation is the common starting point, limited by cross-channel atomicity. **Encrypted storage risks retroactive exposure of the entire past** on key leak, and data cannot be deleted.
- Key management requirements are **mutually contradictory.** For PoS validators especially, **double signing means slashing**, so ordinary HA wisdom (active-active) creates risk.
- The two items most underprepared in review are **error correction** (the answer is a compensating-transaction procedure, not technology) and **an exit strategy** (retention obligations mean "we turned it off" is not the end).
- The core difficulty integrating with existing infrastructure is **the absence of atomicity.** Put eventual-consistency approaches like Saga/outbox into the design early.
- On the adoption path, **securing participating institutions and agreeing governance come before technology.**

## References

- [Hyperledger Fabric — Private data](https://hyperledger-fabric.readthedocs.io/en/latest/private-data/private-data.html)
- [Hyperledger Fabric — Channels](https://hyperledger-fabric.readthedocs.io/en/latest/channels.html)
- [AWS CloudHSM documentation](https://docs.aws.amazon.com/cloudhsm/) / [AWS KMS documentation](https://docs.aws.amazon.com/kms/)
- [AWS KMS key spec reference](https://docs.aws.amazon.com/kms/latest/developerguide/symm-asymm-choose-key-spec.html) — includes `ECC_SECG_P256K1`
- [Use AWS KMS to securely manage Ethereum accounts (AWS Web3 Blog)](https://aws.amazon.com/blogs/web3/use-key-management-service-aws-kms-to-securely-manage-ethereum-accounts-part-1/)
- [AWS Nitro Enclaves for running Ethereum validators (AWS Web3 Blog)](https://aws.amazon.com/blogs/web3/aws-nitro-enclaves-for-running-ethereum-validators-part-1/) — the alternative given BLS12-381 is unsupported
- [Amazon Managed Blockchain](./03-managed-blockchain.md) — discontinuation risk and mitigation
- [Blockchain Fundamentals](./01-fundamentals.md) — consensus and finality
- [Running Blockchain Nodes on EKS](./02-nodes-on-eks.md) — operations
- [EKS Security](../eks/05-eks-security.md) / [Security](../core/06-security.md) — general security controls
