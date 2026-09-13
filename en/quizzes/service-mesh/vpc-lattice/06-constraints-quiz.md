# Constraints and Decision Points Quiz

This quiz tests your understanding of the six migration constraints, the order of decisions, and the billing structure.

## Multiple Choice Questions

1. Which statement correctly distinguishes TLS identity and TCP connectivity models?
   - A) The application impact of SigV4 signing and the Envoy iptables exception
   - B) Separate authenticated HTTP identity from anonymous TLS policy, and service listeners from TCP resource connectivity
   - C) Per-hop charges and the STS dependency
   - D) Failure domain concentration and quota limits

<details>

<summary>Show Answer</summary>

**Answer: B) Separate authenticated HTTP identity from anonymous TLS policy, and service listeners from TCP resource connectivity**

**Explanation:**
These are current API/trust-boundary choices. They do not prove that every TLS auth policy is impossible or that the entire Lattice product lacks TCP resource access.
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
This decision depends on organizational security requirements. TLS Passthrough prevents Lattice from authenticating SigV4 callers or inspecting HTTP fields for L7 routing; its auth policies are limited to anonymous principals. Authenticated workload identity and authorization therefore need an endpoint/application design, which may include mTLS and SPIRE. An HTTPS listener leads instead to the signing-approach decision. Agree on these boundaries with security reviewers before choosing the design.
</details>

3. How should Lattice cost be estimated?
   - A) A deep chain increases the service provisioning charge
   - B) Count actual service calls, including chain depth, fan-out and retries, alongside data volume and provisioned hours
   - C) Chain depth determines the cross-AZ charge
   - D) A deep chain hits quotas sooner

<details>

<summary>Show Answer</summary>

**Answer: B) Count actual service calls, including chain depth, fan-out and retries, alongside data volume and provisioned hours**

**Explanation:**
A simple four-call chain yields four requests only under that assumption. Hourly charges, transferred bytes, retries and access model also affect cost; no savings are measured here.
</details>

4. How should call-chain evidence be maintained?
   - A) Because applications change after migration and the chains differ
   - B) Preserve application traces across migration and correlate them with Lattice logs and request IDs
   - C) Because CloudWatch does not provide a chain depth metric
   - D) Because cost estimation is unnecessary after migration

<details>

<summary>Show Answer</summary>

**Answer: B) Preserve application traces across migration and correlate them with Lattice logs and request IDs**

**Explanation:**
Lattice lacks native spans; that does not erase application spans or make post-migration call-chain analysis impossible.
</details>

5. What configuration is recommended for an environment with plaintext TCP traffic?
   - A) Introduce TLS everywhere and move all of it to Lattice
   - B) Evaluate service HTTP/TLS listeners separately from TCP resource connectivity and existing private alternatives
   - C) Remove all plaintext TCP services
   - D) Enable Lattice's raw TCP listener

<details>

<summary>Show Answer</summary>

**Answer: B) Evaluate service HTTP/TLS listeners separately from TCP resource connectivity and existing private alternatives**

**Explanation:**
Resource configurations support TCP without inheriting service L7 routing/authentication. Match each protocol to the correct model and verify controller/API support.
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

7. How should failure domains be compared?
   - A) Lattice is managed, so failures do not occur
   - B) Both paths have local and shared dependencies; assess affected services, AZs, policies and recovery controls
   - C) The failure scope is identical in both models
   - D) The sidecar model has the broader failure scope

<details>

<summary>Show Answer</summary>

**Answer: B) Both paths have local and shared dependencies; assess affected services, AZs, policies and recovery controls**

**Explanation:**
A proxy failure can be local, but shared mesh config can fail broadly. A Lattice failure is not automatically all East-West traffic, and customer policy/target/controller remediation still exists.
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
No evidence was found that API Gateway natively accepts a Lattice service network as a private integration target. Support for an ALB/NLB listener behind a VPC Link does not establish a direct ALB/NLB → Lattice link-local path. Validate the exact API type, supported target/connectivity, and an explicitly implemented proxy or consumer with the required signing and failure behavior before calling a bridge supported. Check current account/Region quotas and measure backend target placement; DNS ingress AZ affinity does not guarantee a same-AZ backend. TLS anonymous-principal policy limits, controller attachment limits and the TLS-listener ECH/ESNI exclusion are documented separately and should not be described as wholly unconfirmed.
</details>
