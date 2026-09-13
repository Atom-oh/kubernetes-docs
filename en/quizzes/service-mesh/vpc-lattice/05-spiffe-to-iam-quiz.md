# Workload Identity Migration Quiz

This quiz tests your understanding of SPIFFE/SPIRE structure, the attestation principle, and the similarities and decisive differences versus IAM Auth.

## Multiple Choice Questions

1. Why does a SPIFFE ID contain no network information such as an IP address or hostname?
   - A) The URI format cannot express IP addresses
   - B) Identity must remain the same wherever the workload is scheduled and however its IP changes
   - C) Network information is carried separately in the SVID
   - D) Exposing IPs would be a security risk

<details>

<summary>Show Answer</summary>

**Answer: B) Identity must remain the same wherever the workload is scheduled and however its IP changes**

**Explanation:**
A SPIFFE ID takes the form `spiffe://<trust-domain>/<workload-path>`, where the path usually reflects namespace and ServiceAccount. Excluding network information is deliberate — a Pod may be rescheduled and get a new IP, but its identity must persist. This is the starting point of the shift from IP-based to identity-based control, the same direction of thinking as why destination-IP-based control becomes meaningless in Lattice's link-local range.
</details>

2. In SPIRE's Workload Attestation, at which point is the bootstrapping problem decisively resolved?
   - A) When the workload presents a pre-planted token
   - B) The Agent uses kernel-provided peer information under a trusted-kernel/attestor model and cross-checks workload selectors
   - C) When the Server signs the SVID
   - D) When Envoy receives the certificate over SDS

<details>

<summary>Show Answer</summary>

**Answer: B) The Agent uses kernel-provided peer information under a trusted-kernel/attestor model and cross-checks workload selectors**

**Explanation:**
This avoids asking the workload to bootstrap with a pre-shared application secret. It is not an unconditional guarantee against host compromise, bad selectors or incorrect attestor configuration.
</details>

3. Why are SVIDs designed with short lifetimes?
   - A) To save storage space
   - B) Short lifetimes bound credential usefulness but do not replace compromise response or authorization controls
   - C) To distribute the CA's signing load
   - D) To eliminate every runtime secret and all compromise-response requirements

<details>

<summary>Show Answer</summary>

**Answer: B) Short lifetimes bound credential usefulness but do not replace compromise response or authorization controls**

**Explanation:**
Review renewal, runtime storage, replay exposure and emergency-deny/revocation behavior. Expiring credentials still contain secrets and are not automatically safe until expiry.
</details>

4. What are the two structural similarities between SPIFFE/SPIRE and Lattice IAM Auth?
   - A) Both use X.509 certificates and both perform mTLS
   - B) Both can avoid baked-in long-lived secrets, while runtime private keys or temporary secret credentials still need protection
   - C) Both have the customer operate a CA and both authenticate per connection
   - D) Both support workloads outside AWS and both authenticate per request

<details>

<summary>Show Answer</summary>

**Answer: B) Both can avoid baked-in long-lived secrets, while runtime private keys or temporary secret credentials still need protection**

**Explanation:**
X.509-SVID delivery includes key material; IAM credentials include a secret access key and session token. Platform attestation changes provisioning, not the need to protect sockets/endpoints, memory and caches.
</details>

5. What is the practical implication of decisive difference (a), the change in authentication directionality?
   - A) Client proof weakens, so the application must compensate
   - B) Server identity proof drops to the level of a TLS server certificate, so the line of defense moves from workload mutual authentication to IAM control over Lattice resource creation
   - C) Bidirectional authentication is preserved, so there is no review impact
   - D) Authentication itself becomes unnecessary

<details>

<summary>Show Answer</summary>

**Answer: B) Server identity proof drops to the level of a TLS server certificate, so the line of defense moves from workload mutual authentication to IAM control over Lattice resource creation**

**Explanation:**
Client proof actually becomes finer-grained (per-request SigV4 verification). The problem is server proof: all the client can confirm is that the TLS certificate is valid and the domain matches, with no step confirming "is this really that team's service" within a workload identity system. The response is to strictly limit via IAM who can create Lattice Services, control service network associations, and monitor with CloudTrail. If your review documentation said "mutual authentication," that item must be rewritten.
</details>

6. Why is decisive difference (b), the transfer of root-of-trust ownership, a heavy item in financial-sector reviews?
   - A) AWS IAM is less secure than SPIRE
   - B) Many organizations' security standards require, or are read as requiring, that the root of trust of an authentication system be under their own control — and running your own CA was the most direct way to satisfy that
   - C) CloudTrail does not provide an audit trail
   - D) Authority over IAM policy decisions transfers to AWS

<details>

<summary>Show Answer</summary>

**Answer: B) Many organizations' security standards require, or are read as requiring, that the root of trust of an authentication system be under their own control — and running your own CA was the most direct way to satisfy that**

**Explanation:**
Adopting SPIRE was likely the result of passing that very review. Moving to Lattice IAM Auth means rebuilding the argument, with available grounds including the shared responsibility model, retained policy authority (the customer still defines who may call what via IAM), audit trails through CloudTrail and access logs, and the benefit that the customer holds no CA private key so key-leak risk is eliminated. But this is an argument that "control is exercised differently," not that "it is equivalent," and acceptance depends on organizational standards. D is wrong — policy authority stays with the customer.
</details>

7. In which situation might you need to keep operating SPIRE after migrating to Lattice?
   - A) Any case where IAM Auth is used
   - B) When the chosen architecture still needs SPIFFE endpoint identities, including endpoint mTLS or supported off-AWS workloads
   - C) When you use the Gateway API Controller
   - D) When you have a multi-cluster setup

<details>

<summary>Show Answer</summary>

**Answer: B) When the chosen architecture still needs SPIFFE endpoint identities, including endpoint mTLS or supported off-AWS workloads**

**Explanation:**
Keeping SPIRE is an architectural option, not a universal requirement for every off-AWS workload. Other credential providers and supported private network paths can be evaluated.
</details>
