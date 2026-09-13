# Financial Services Perspective Quiz

This quiz tests your understanding of the consortium choice, privacy, key management, and review-board issues.

## Multiple Choice Questions

1. What criterion is offered for judging whether a problem needs blockchain?
   - A) Whether the data volume is large enough
   - B) Whether you can write "why this problem must have no arbiter" in one sentence — if not, compare alternatives first
   - C) Whether there are five or more participating institutions
   - D) Whether real-time processing is required

<details>

<summary>Show Answer</summary>

**Answer: B) Whether you can write "why this problem must have no arbiter" in one sentence — if not, compare alternatives first**

**Explanation:**
Blockchain's essence is "agreeing without a trusted arbiter," paid for in throughput and complexity. If a single organization owns the data, or an arbiter exists whom everyone trusts, an ordinary database is better in every respect. **The case where only tamper detection is needed** is an especially common misconception — audit trails and integrity proofs can be achieved with signed append-only logs, hash chains, or object storage WORM features, with far simpler operations.
</details>

2. What must be assessed before claiming that a network choice satisfies financial compliance?
   - A) Throughput and fees
   - B) Assess counterparty identification and data-location obligations for the actual activity and jurisdiction
   - C) Governance and error handling
   - D) Development convenience and hiring

<details>

<summary>Show Answer</summary>

**Answer: B) Assess counterparty identification and data-location obligations for the actual activity and jurisdiction**

**Explanation:**
Public and permissioned systems can use different controls. Consortium membership alone proves neither KYC/AML nor privacy compliance; obtain the appropriate legal/compliance assessment.
</details>

3. What substantive value remains when choosing a consortium chain, and why should review define it that way?
   - A) Censorship resistance — a value regulators also recognize
   - B) Reduced inter-institution reconciliation cost — because writing "decentralized, operating without trust" collapses under the question "then who controls membership?"
   - C) Permissionless participation — because it guarantees scalability
   - D) No arbiter needed — because no operating party remains

<details>

<summary>Show Answer</summary>

**Answer: B) Reduced inter-institution reconciliation cost — because writing "decentralized, operating without trust" collapses under the question "then who controls membership?"**

**Explanation:**
Going consortium removes much of the public chain's value — censorship resistance, permissionless participation, no arbiter needed — because a party controls membership and that party is effectively an arbiter. What remains substantively is **"making institutions see the same data so reconciliation work disappears,"** which is real value. Defining value that way from the start is defensible in review.
</details>

4. What is the particular risk of storing data encrypted on a blockchain?
   - A) Performance degradation from encryption
   - B) Historical ciphertext copies may persist, and a key compromise can expose records encrypted under that key
   - C) Encrypted data is excluded from consensus
   - D) The encryption key is stored on the chain alongside

<details>

<summary>Show Answer</summary>

**Answer: B) Historical ciphertext copies may persist, and a key compromise can expose records encrypted under that key**

**Explanation:**
Re-encrypting new records does not erase old copies. Permissioned private-data purge has different semantics; validate retention, key lifecycle and legal requirements rather than asserting every chain has identical deletion behavior.
</details>

5. Where does PoS validator key management clash with ordinary HA wisdom?
   - A) Keys must be replicated to several regions
   - B) Uncoordinated signers can produce conflicting slashable messages for the same validator
   - C) HSMs do not support multiple instances
   - D) Key rotation requires downtime

<details>

<summary>Show Answer</summary>

**Answer: B) Uncoordinated signers can produce conflicting slashable messages for the same validator**

**Explanation:**
Use fencing and preserved slashing-protection history. A deliberately distributed signer needs proven coordination; duplicated identical signatures are not automatically equivalent to a slashable conflict.
</details>

6. What kind of answer does the review question "how do you reverse an incorrect transaction" require?
   - A) Present a technical procedure for rolling back the chain
   - B) Process, not technology — keep the original and issue a compensating transaction to correct the outcome, the same concept as a reversing entry in accounting
   - C) The consortium operator deletes the block
   - D) Explain that immutability is a strength so nothing needs reversing

<details>

<summary>Show Answer</summary>

**Answer: B) Process, not technology — keep the original and issue a compensating transaction to correct the outcome, the same concept as a reversing entry in accounting**

**Explanation:**
The immutability marketed as a strength is a problem in financial operations. Incorrect transactions, mistaken transfers, and system errors happen, and institutions have obligations and procedures to correct them. The answer is issuing a compensating transaction rather than "rolling back the chain," and review needs that procedure and its approval authority documented. This also connects to the absence of atomicity when integrating with existing infrastructure (Saga/outbox patterns).
</details>

7. Which two items are identified as most underprepared in financial-services review?
   - A) Performance measurement and cost estimation
   - B) Error correction procedures and an exit strategy
   - C) Network configuration and firewall policy
   - D) Development staffing and training plans

<details>

<summary>Show Answer</summary>

**Answer: B) Error correction procedures and an exit strategy**

**Explanation:**
For error correction, "it cannot be reversed" becomes a weakness in review, and the answer must be prepared as process (compensating transactions) rather than technology. The exit strategy is almost never prepared — on consortium dissolution, member withdrawal, or system shutdown, financial data carries retention obligations so **"we turned off the chain" is not the end.** The ledger's export format, retention party, withdrawing-member data handling, and record access must be in the consortium agreement, with the technical design supporting it.
</details>

8. What is the most substantive difficulty integrating with existing financial infrastructure, and the direction of response?
   - A) The throughput gap — solved by adding chain nodes
   - B) The absence of atomicity — an existing DB transaction and a chain transaction cannot be bound into one atomic unit, so eventual-consistency approaches like Saga/outbox must go into the design early
   - C) Time synchronization — solved with NTP configuration
   - D) Protocol differences — solved with a gateway translation

<details>

<summary>Show Answer</summary>

**Answer: B) The absence of atomicity — an existing DB transaction and a chain transaction cannot be bound into one atomic unit, so eventual-consistency approaches like Saga/outbox must go into the design early**

**Explanation:**
A failure between writing to the DB and submitting the chain transaction creates an inconsistency, and they cannot be bound in a distributed transaction. Saga or outbox patterns are needed, connected to the compensating-transaction procedure. Being an architecture decision, it must be **addressed early in design** — bolted on later, data consistency problems surface in production. Note the throughput gap is not solved by adding chain nodes — adding nodes does not increase throughput.
</details>

9. Which stage must come before technical validation in a realistic adoption path?
   - A) PoC and pilot
   - B) Agree participant roles, governance and the measurable benefit compared with simpler alternatives
   - C) Infrastructure sizing and cost estimation
   - D) Building the monitoring stack

<details>

<summary>Show Answer</summary>

**Answer: B) Agree participant roles, governance and the measurable benefit compared with simpler alternatives**

**Explanation:**
Do not assert that one institutional arrangement has universally zero value or automatic compliance. The review concerns explicit requirements, trust assumptions and operational responsibilities.
</details>
