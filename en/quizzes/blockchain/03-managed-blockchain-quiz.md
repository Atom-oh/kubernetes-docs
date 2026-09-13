# Amazon Managed Blockchain Quiz

This quiz tests your understanding of AMB's components, the managed/self-operated boundary, and service discontinuation risk.

## Multiple Choice Questions

1. How should the AMB offerings be compared?
   - A) All three solve the same problem at different price points
   - B) Distinguish Fabric/dedicated nodes, serverless Access and Query APIs, with offering-specific billing and capabilities
   - C) They are split by development, staging, and production environments
   - D) They are split by public, private, and hybrid chains

<details>

<summary>Show Answer</summary>

**Answer: B) Distinguish Fabric/dedicated nodes, serverless Access and Query APIs, with offering-specific billing and capabilities**

**Explanation:**
AMB is not universally per-node billed. Dedicated resources, serverless RPC requests and indexed Query APIs have different pricing and coverage.
</details>

2. What is the most important thing AMB managed nodes do *not* solve?
   - A) CloudWatch metric collection
   - B) Validator operation — managed nodes are for queries and submission, while PoS staking is a different requirement set of key management, signing availability, and slashing risk
   - C) IAM-based access control
   - D) VPC private connectivity

<details>

<summary>Show Answer</summary>

**Answer: B) Validator operation — managed nodes are for queries and submission, while PoS staking is a different requirement set of key management, signing availability, and slashing risk**

**Explanation:**
AMB Access public chain nodes are for reading chain data and submitting transactions. Participating as a PoS validator to earn staking rewards is entirely different — the signing key must be online continuously, signing in two places means slashing and forfeited stake, and so strict active-passive with fencing is required. If staking is the goal, AMB does not solve it and you need self-operation or a specialized staking service.
</details>

3. What is presented as step 1 of the managed-vs-self-operated decision?
   - A) What does it cost
   - B) Do you actually need a node — if you only query data, AMB Query or a third-party RPC may suffice
   - C) Which chain will you use
   - D) How many operations staff do you have

<details>

<summary>Show Answer</summary>

**Answer: B) Do you actually need a node — if you only query data, AMB Query or a third-party RPC may suffice**

**Explanation:**
The decision order is ① do you really need a node → ② do you need control → ③ cost → ④ can you mix. Running nodes is a costly, burdensome choice so the need must be confirmed first, and **many cases are filtered out at step 1.** At step 2, needing any of client choice, tuning, archive, or validator participation means self-operating.
</details>

4. What lesson does the Amazon QLDB case offer for architecture decisions?
   - A) Managed services are always cheaper than self-operating
   - B) Managed services can also be discontinued, and the migration path offered may not be functionally equivalent — moving to Aurora PostgreSQL loses cryptographic verifiability
   - C) Ledger databases must be implemented only with blockchain
   - D) AWS services are guaranteed support for five years after GA

<details>

<summary>Show Answer</summary>

**Answer: B) Managed services can also be discontinued, and the migration path offered may not be functionally equivalent — moving to Aurora PostgreSQL loses cryptographic verifiability**

**Explanation:**
QLDB was announced in 2018, went GA in 2019, had end of support announced in July 2024, and **the service ended on July 31, 2025.** AWS's path was Aurora PostgreSQL — ledger-like functionality can be built with extensions, but QLDB's core value of "mathematically proving nothing was tampered with" is not replaced. The lessons: ① managed services carry discontinuation risk ② "a replacement exists" is not "it provides the same thing" ③ the notice period can be short ④ standard technology is easier to move off.
</details>

5. What is the most effective mitigation for service discontinuation risk?
   - A) Deploying to several cloud providers simultaneously
   - B) Standard protocols plus an abstraction layer — having the application speak a standard RPC interface lets you swap the backend between AMB, self-operated, and third-party
   - C) Not using managed services
   - D) Signing a long-term contract with AWS

<details>

<summary>Show Answer</summary>

**Answer: B) Standard protocols plus an abstraction layer — having the application speak a standard RPC interface lets you swap the backend between AMB, self-operated, and third-party**

**Explanation:**
If the application speaks a standard interface like Ethereum JSON-RPC, the backend can be anything. Coupling directly to AMB-specific APIs forfeits that flexibility. Other mitigations are keeping chain data in your own index or warehouse for data independence, securing key export and backup strategies, and measuring resync and data migration time in advance to judge whether you could respond within a notice period.
</details>

6. Why is AMB's IAM integration a substantive benefit?
   - A) IAM signs blockchain transactions for you
   - B) A self-operated node's RPC endpoint needs its own authentication scheme or network-layer-only control, while AMB can be controlled via IAM consistently with your internal permission model
   - C) IAM backs up keys automatically
   - D) IAM policies can modify chain data

<details>

<summary>Show Answer</summary>

**Answer: B) A self-operated node's RPC endpoint needs its own authentication scheme or network-layer-only control, while AMB can be controlled via IAM consistently with your internal permission model**

**Explanation:**
Access control on a self-operated node's RPC endpoint requires building an authentication scheme or relying only on network-layer controls like Security Groups or NetworkPolicy. AMB can be controlled with IAM policies, managed consistently with your internal permission model. Add CloudWatch metrics/logs, CloudTrail management API auditing, VPC endpoint/PrivateLink private connectivity, and KMS key management integration.
</details>

7. Which item is marked `Needs verification` in the AMB document?
   - A) That AMB Query serves data via API
   - B) AMB's supported chain list, regional availability, and preview/GA status, plus AMB's forward roadmap and service continuity plans
   - C) That QLDB ended on July 31, 2025
   - D) That AMB supports Hyperledger Fabric

<details>

<summary>Show Answer</summary>

**Answer: B) AMB's supported chain list, regional availability, and preview/GA status, plus AMB's forward roadmap and service continuity plans**

**Explanation:**
Supported chains and status vary over time — confirmed changes include the Ethereum Goerli testnet ending (April 1, 2024) and the Polygon Mumbai testnet ending (April 15, 2024), and Polygon PoS mainnet was at one point Public Preview. Also, no end-of-support announcement for AMB as a whole was found at the time of research, but that is not evidence of "no plans to discontinue" — it means "no announcement was found," so for a long-lived system confirm the roadmap directly with your AWS account team.
</details>
