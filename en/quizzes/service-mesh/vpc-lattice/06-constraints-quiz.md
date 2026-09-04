# Constraints and Decision Points Quiz

This quiz tests your understanding of the six migration constraints, the order of decisions, and the billing structure.

## Multiple Choice Questions

1. Which of the six constraints are "constraints of principle that will not be resolved even if AWS adds features"?
   - A) The application impact of SigV4 signing and the Envoy iptables exception
   - B) The incompatibility of TLS Passthrough with IAM Auth Policy, and the lack of raw TCP support
   - C) Per-hop charges and the STS dependency
   - D) Failure domain concentration and quota limits

<details>

<summary>Show Answer</summary>

**Answer: B) The incompatibility of TLS Passthrough with IAM Auth Policy, and the lack of raw TCP support**

**Explanation:**
Both derive from one fact: you must terminate TLS to see headers, and without TLS there is no SNI. SigV4 verification presupposes parsing the `Authorization` header, so it is physically impossible without TLS termination; and plaintext TCP has no basis for routing at all. The remaining constraints (signing approach, iptables exception, billing, failure domain) are items you can manage through design and operations.
</details>

2. Which decision must be made first in the migration design?
   - A) Whether to sign with a shared library or an egress proxy
   - B) Whether regulation requires end-to-end encryption or workload mutual authentication — this splits HTTPS listener + IAM Auth from TLS Passthrough, and most later design decisions depend on it
   - C) The number of Lattice services and the estimated cost
   - D) The node Security Group's prefix list configuration

<details>

<summary>Show Answer</summary>

**Answer: B) Whether regulation requires end-to-end encryption or workload mutual authentication — this splits HTTPS listener + IAM Auth from TLS Passthrough, and most later design decisions depend on it**

**Explanation:**
This decision rests on organizational review standards rather than technology. Choosing TLS Passthrough forfeits all of IAM Auth and L7 routing, requires redesigning authorization in endpoint mTLS or the application, and pulls in the question of whether SPIRE stays. Choosing an HTTPS listener leads instead to the signing-approach decision. Confirming this late means unwinding every earlier design decision, so agree with security reviewers first.
</details>

3. What does "call chain depth dominates cost" mean for Lattice billing?
   - A) A deep chain increases the service provisioning charge
   - B) Charges are per hop, so in a four-hop chain a single user request produces four Lattice requests, and cost is proportional to request count × chain depth
   - C) Chain depth determines the cross-AZ charge
   - D) A deep chain hits quotas sooner

<details>

<summary>Show Answer</summary>

**Answer: B) Charges are per hop, so in a four-hop chain a single user request produces four Lattice requests, and cost is proportional to request count × chain depth**

**Explanation:**
The three billing axes are service provisioning (hourly), data processing (per GB, inter-AZ included), and request count (HTTP/HTTPS) or TCP connection count (TLS listeners). Request and data processing charges accrue at each hop, so chain depth becomes a cost multiplier. In AS-IS (App Mesh) there was no per-request charge and cost appeared as Envoy's compute consumption, so this migration shifts the cost model from "compute resources" to "request count" — making chatty communication and deep chains expensive.
</details>

4. Why is it emphasized that call chain depth data must be collected before migrating?
   - A) Because applications change after migration and the chains differ
   - B) Because after migration Lattice creates no trace spans, making the data hard to obtain
   - C) Because CloudWatch does not provide a chain depth metric
   - D) Because cost estimation is unnecessary after migration

<details>

<summary>Show Answer</summary>

**Answer: B) Because after migration Lattice creates no trace spans, making the data hard to obtain**

**Explanation:**
Lattice does not create X-Ray segments/spans and does not inject trace IDs. In AS-IS, Envoy produces spans so distributed tracing data reveals chain depth; after migration that data does not exist unless you add OpenTelemetry instrumentation to applications. Chain depth is a key input to cost estimation, so collect it now. For the same reason, collect per-service-pair RPS and data transfer volume while Envoy metrics are still available.
</details>

5. What configuration is recommended for an environment with plaintext TCP traffic?
   - A) Introduce TLS everywhere and move all of it to Lattice
   - B) Hybrid — HTTP/HTTPS/gRPC on Lattice, TCP with TLS on TLS Passthrough, plaintext TCP on an NLB or the existing path
   - C) Remove all plaintext TCP services
   - D) Enable Lattice's raw TCP listener

<details>

<summary>Show Answer</summary>

**Answer: B) Hybrid — HTTP/HTTPS/gRPC on Lattice, TCP with TLS on TLS Passthrough, plaintext TCP on an NLB or the existing path**

**Explanation:**
Trying to move everything to Lattice is the most common cause of migration delay. Pulling "introduce TLS for plaintext TCP services" into scope requires application changes and the schedule leaves your control. Since App Mesh end of support (September 30, 2026) imposes a deadline, it is practically important to separate what must move by then (HTTP traffic depending on App Mesh) from what need not move at all (plaintext TCP that never used App Mesh). D describes a feature that does not exist.
</details>

6. What is the trade-off of keeping intra-cluster communication off Lattice?
   - A) There is no trade-off; it is always advantageous
   - B) It helps cost and latency, but direct k8s Service DNS calls are not evaluated against auth policies, so authorization for internal traffic must be designed separately via NetworkPolicy or the application layer
   - C) Authorization is preserved but observability is lost
   - D) The Gateway API Controller stops working

<details>

<summary>Show Answer</summary>

**Answer: B) It helps cost and latency, but direct k8s Service DNS calls are not evaluated against auth policies, so authorization for internal traffic must be designed separately via NetworkPolicy or the application layer**

**Explanation:**
Lattice's strength is communication crossing cluster, VPC, and account boundaries; within the same cluster it offers little benefit while adding cost and latency, so routing only boundary-crossing traffic through it is often sensible. However, `IAMAuthPolicy` authorizes only traffic traveling through Gateways/HTTPRoutes/GRPCRoutes, so taking internal traffic off Lattice removes authorization for that segment. This is where cost optimization and authorization consistency conflict.
</details>

7. Which statement correctly describes the failure domain difference between AS-IS (sidecar) and TO-BE (Lattice)?
   - A) Lattice is managed, so failures do not occur
   - B) Sidecar failures are localized (one Envoy = one Pod) and the customer can intervene, whereas a Lattice failure affects all East-West traffic and the customer's direct remediation options are limited
   - C) The failure scope is identical in both models
   - D) The sidecar model has the broader failure scope

<details>

<summary>Show Answer</summary>

**Answer: B) Sidecar failures are localized (one Envoy = one Pod) and the customer can intervene, whereas a Lattice failure affects all East-West traffic and the customer's direct remediation options are limited**

**Explanation:**
A managed service has a lower probability of individual failure but a broader scope when failure occurs, with limited customer intervention. The sidecar model may fail more often but failures are localized and responses like Pod restarts, config rollback, or bypassing the sidecar are available. Adding IAM Auth makes STS a data path dependency: on refresh failure you cannot sign and unsigned requests are 403s. Mitigations are confirming credential cache lifetime, testing refresh-failure behavior, redundancy for critical paths, phased migration with a rollback path, and recalculating RTO/RPO.
</details>

8. Which of the following is marked as `Needs verification` because it could not be confirmed in official documentation?
   - A) That the SigV4 service name is `vpc-lattice-svcs`
   - B) Whether API Gateway natively supports a Lattice service network as a private integration target
   - C) That App Mesh end of support is September 30, 2026
   - D) That there are three listener protocols: HTTP/HTTPS/TLS_PASSTHROUGH

<details>

<summary>Show Answer</summary>

**Answer: B) Whether API Gateway natively supports a Lattice service network as a private integration target**

**Explanation:**
No evidence was found that API Gateway natively supports a Lattice service network as a private integration target. The confirmed patterns are API Gateway → VPC Link → ALB/NLB → Lattice, or going through a proxy/federation layer. The other `Needs verification` items are exact quota values, whether Lattice's Target selection considers the caller's AZ, the API behavior when setting an auth policy on a TLS_PASSTHROUGH listener, and ECH support. A, C, and D are all confirmed from primary sources.
</details>
