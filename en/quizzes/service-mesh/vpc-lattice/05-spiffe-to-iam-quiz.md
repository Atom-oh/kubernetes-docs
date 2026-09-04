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
   - B) When the Agent obtains the peer process's PID from the kernel — an unforgeable kernel fact, which it then cross-checks against Kubernetes' records
   - C) When the Server signs the SVID
   - D) When Envoy receives the certificate over SDS

<details>

<summary>Show Answer</summary>

**Answer: B) When the Agent obtains the peer process's PID from the kernel — an unforgeable kernel fact, which it then cross-checks against Kubernetes' records**

**Explanation:**
The workload connects to the Workload API's UDS with no credentials. The Agent obtains the peer PID from the kernel, then walks PID → cgroup → container → Pod/namespace/ServiceAccount to build selectors and submits them to the Server. The workload never claims who it is; the kernel reports a fact and that fact is cross-checked against platform records. This is the principle that "identity is not presented but observed and adjudicated" — forging it would require compromising the kernel or the API server.
</details>

3. Why are SVIDs designed with short lifetimes?
   - A) To save storage space
   - B) To bound the useful window of a compromise without needing a revocation mechanism
   - C) To distribute the CA's signing load
   - D) To re-verify identity during each renewal

<details>

<summary>Show Answer</summary>

**Answer: B) To bound the useful window of a compromise without needing a revocation mechanism**

**Explanation:**
Certificate revocation mechanisms such as CRLs and OCSP are operationally awkward. If a credential expires within tens of minutes to a few hours, the useful window of a compromise is bounded without any revocation machinery. Importantly, STS temporary credentials are short-lived for the same reason — so the review argument "we do not use long-lived secrets" is satisfied equally in AS-IS and TO-BE and is not up for re-litigation during migration.
</details>

4. What are the two structural similarities between SPIFFE/SPIRE and Lattice IAM Auth?
   - A) Both use X.509 certificates and both perform mTLS
   - B) Both use short-lived credentials, and both are based on platform attestation so the workload holds no secret in advance
   - C) Both have the customer operate a CA and both authenticate per connection
   - D) Both support workloads outside AWS and both authenticate per request

<details>

<summary>Show Answer</summary>

**Answer: B) Both use short-lived credentials, and both are based on platform attestation so the workload holds no secret in advance**

**Explanation:**
The SPIRE Agent serving SVIDs over UDS and the Pod Identity Agent serving credentials on a link-local address are the same idea — a local infrastructure component adjudicates the workload and obtains credentials on its behalf. Node identity, workload adjudication, credential delivery, and renewal correspond row for row between the two systems. Thanks to this similarity, the review arguments "no long-lived secrets" and "workloads hold no secrets" both carry over unchanged.
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
   - B) When you have workloads outside AWS, or when you choose the TLS Passthrough configuration so endpoints must perform mTLS themselves
   - C) When you use the Gateway API Controller
   - D) When you have a multi-cluster setup

<details>

<summary>Show Answer</summary>

**Answer: B) When you have workloads outside AWS, or when you choose the TLS Passthrough configuration so endpoints must perform mTLS themselves**

**Explanation:**
IAM Auth requires reachability to IAM/STS, so it does not cover on-premises or other-cloud workloads, where SPIRE remains necessary. And if regulation requires end-to-end encryption or mutual authentication and you choose TLS Passthrough, endpoints must do mTLS themselves and SPIRE can supply those certificates. So a configuration where App Mesh is gone but SPIRE remains is possible — responding to App Mesh end of support and keeping SPIRE are separate decisions. If eliminating SPIRE's operational burden was a migration goal, check whether these conditions conflict with it.
</details>
