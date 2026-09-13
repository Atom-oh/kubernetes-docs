# Linkerd Security Quiz

Based on the [security guide](../../../service-mesh/linkerd/04-security.md), reviewed September 11, 2026.

### 1. How does Linkerd enable mesh mTLS?

- A. Every service must implement Linkerd TLS itself
- B. Automatically for eligible TCP traffic between participating meshed Pods
- C. Any Kubernetes Secret encrypts every network path
- D. All UDP traffic is automatically protected

<details>
<summary>Show Answer</summary>

**Answer: B**

**Explanation:** Both proxies must participate and trust the chain. Unmeshed endpoints and skipped ports do not automatically receive Linkerd mTLS. The default can still accept plaintext inbound traffic; require authenticated access with appropriate policy.

</details>

### 2. What does a Server resource select?

- A. External DNS records
- B. An inbound port/protocol on matching Pods in its namespace
- C. A certificate Secret
- D. An outbound load-balancer algorithm

<details>
<summary>Show Answer</summary>

**Answer: B**

**Explanation:** Server selects a Pod/port target. Declare application ports and avoid overlapping Servers. Unmatched traffic defaults to deny unless accessPolicy changes that behavior. A Server on proxy admin port 4191 does not undo the admin port’s interception bypass.

</details>

### 3. What does meshTLS.serviceAccounts in ServerAuthorization describe?

- A. The server’s serviceAccountName
- B. Allowed authenticated client ServiceAccounts
- C. The account used to issue every certificate
- D. Only metric-collection accounts

<details>
<summary>Show Answer</summary>

**Answer: B**

**Explanation:** This grant accepts matching mesh client identities. Other grants may also broaden access. The selected release serves ServerAuthorization/v1beta1; AuthorizationPolicy can also directly reference a ServiceAccount without requiring this legacy grant.

</details>

### 4. How can intended business traffic be allowed under default-deny?

- A. Every request remains automatically allowed
- B. Define the target and matching authorization grants
- C. A generic namespace label grants any caller access
- D. An arbitrary ConfigMap whitelist is sufficient

<details>
<summary>Show Answer</summary>

**Answer: B**

**Explanation:** Server plus AuthorizationPolicy is a current pattern; ServerAuthorization is an older alternative. They are not a mandatory sequential pipeline. Multiple requiredAuthenticationRefs within one AuthorizationPolicy all need to match, and probe access needs appropriate treatment.

</details>

### 5. How should a trust anchor lifetime be chosen?

- A. Always exactly 24 hours
- B. Always unlimited
- C. From CA policy, planned rotation and recovery requirements; the CLI default is one year
- D. A universal mandatory 1–10 year recommendation applies to every cluster

<details>
<summary>Show Answer</summary>

**Answer: C**

**Explanation:** A manually supplied ten-year root is possible, not an automatic best practice. Track all chain expirations and ensure the issuer’s renewal/lifetime fits its CA. Root rotation requires overlap and distribution to every consumer, including linked clusters.

</details>

### 6. What does client.unauthenticated:true permit in a ServerAuthorization?

- A. Only authenticated identities matched by a wildcard
- B. Clients without requiring mesh authentication
- C. Only callers using a special external header
- D. Only the declared readiness URL, regardless of the target

<details>
<summary>Show Answer</summary>

**Answer: B**

**Explanation:** The setting permits access without mesh authentication across its target scope. It is not automatically limited to a health path. meshTLS.identities:["*"] is different: it broadly accepts meshed identities while still requiring mesh authentication.

</details>

### 7. What normally happens when a valid issuer is renewed under the same trusted root?

- A. Every proxy must immediately restart
- B. The root must always change too
- C. The owner updates the issuer Secret; Identity validates/reloads its files and proxies renew leaves normally
- D. The entire cluster restarts

<details>
<summary>Show Answer</summary>

**Answer: C**

**Explanation:** Check IssuerUpdated and investigate skipped/invalid updates. Existing leaves can remain under the old issuer until normal renewal while the chain stays valid. A blanket Identity restart is not mandatory for each issuer update; trust-anchor rotation is a separate staged process.

</details>

### 8. Which default policy requires authenticated mesh clients, including appropriately trusted multicluster clients?

- A. deny
- B. all-unauthenticated
- C. all-authenticated
- D. cluster-unauthenticated

<details>
<summary>Show Answer</summary>

**Answer: C**

**Explanation:** all-authenticated requires mesh authentication. It is not a narrow allowlist of specific callers. Explicit Server policies and authorization grants still matter, and namespace default annotations are applied when proxies are initialized.

</details>

### 9. Which is required when cert-manager issues Linkerd’s signing issuer certificate?

- A. isCA:false
- B. isCA:true, with suitable ECDSA P-256 credentials and a valid chain
- C. Only a digital-signature usage on an arbitrary leaf
- D. Always an RSA private key

<details>
<summary>Show Answer</summary>

**Answer: B**

**Explanation:** Identity requires an intermediate CA capable of signing workload certificates. Also make rotationPolicy explicit, verify Secret format/ownership and CA lifetime, and confirm Identity loads the result. A generic Vault leaf-signing path is not proven to supply a CA merely because the request says isCA:true.

</details>

### 10. What can linkerd viz edges show?

- A. Every edge router’s hardware state
- B. Observed resource edges and their mTLS/security state
- C. Proof that every possible or idle path is encrypted
- D. The complete end-user authentication audit

<details>
<summary>Show Answer</summary>

**Answer: B**

**Explanation:** The SECURED view is evidence about observed edges, not a complete network inventory. Use linkerd identity for public certificates and policy diagnostics/metrics for access decisions. Do not equate the CLI display with literal Prometheus TLS label values.

</details>

### 11. How do Linkerd and application security fit together?

- A. Mesh mTLS removes the need for application security
- B. Mesh workload/transport controls complement user, tenant and business authorization
- C. A permitted ServiceAccount proves every caller is an administrator
- D. Input validation is performed automatically by the mesh

<details>
<summary>Show Answer</summary>

**Answer: B**

**Explanation:** Linkerd contributes workload authentication, eligible transport encryption and inbound authorization. Applications still validate user credentials, permissions and input. Network/admission controls also cover proxy bypass or missing enrollment.

</details>

### 12. Which metric requires application-level instrumentation or another application-aware source?

- A. Proxy workload-certificate expiration
- B. Observed HTTP responses lacking mesh client identity
- C. Application login failures
- D. Proxy inbound authorization-denial counters

<details>
<summary>Show Answer</summary>

**Answer: C**

**Explanation:** Linkerd does not automatically know application login outcomes. For its own alerts, distinguish leaf expiration timestamps from issuer TTL duration, use rate-based scoped traffic ratios, retain identity labels and treat missing/idle telemetry separately.

</details>
