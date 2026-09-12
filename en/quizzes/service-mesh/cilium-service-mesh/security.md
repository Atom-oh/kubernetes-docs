# Cilium Service Mesh Security Quiz

Reviewed against Cilium 1.20.1. The [security guide](../../../service-mesh/cilium-service-mesh/03-security.md) distinguishes out-of-band authentication, transport encryption and ztunnel beta, with primary references.

### 1. What does SPIRE provide for Cilium's out-of-band mutual authentication?

- **A.** An Istio sidecar for every Pod
- **B.** SVID identity credentials for the agent authentication mechanism
- **C.** Automatic encryption of all application traffic by itself
- **D.** A Kubernetes API-server replacement

<details>
<summary>Show Answer</summary>

**Answer: B. SVID identity credentials for the agent authentication mechanism**

For the out-of-band beta mechanism, SPIRE supplies SVID identity credentials and Cilium agents authenticate peers separately from the application connection. WireGuard/IPsec encryption is a separate choice. Cilium 1.20.1 also has a distinct ztunnel mTLS beta with its own CA/bootstrap, enrollment and policy limitations.

</details>

### 2. How does CiliumNetworkPolicy behave when authentication mode is set to 'required'?

- **A.** Allows all traffic without authentication
- **B.** Only allows traffic that passes mutual authentication
- **C.** Only logs warnings on authentication failure
- **D.** Disables mTLS

<details>
<summary>Show Answer</summary>

**Answer: B. Only allows traffic that passes mutual authentication**

The matched allow rule requires successful authentication; it is not a cluster-wide switch and does not itself TLS-encrypt the application payload. Other authorization and application authentication requirements remain. The API is authentication: {mode: required}, not an array.

</details>

### 3. Which traffic is not encrypted by Cilium WireGuard alone?

- **A.** Supported Pod traffic between different nodes
- **B.** Supported remote-node traffic with node encryption enabled
- **C.** Same-node Pod traffic and the external client-to-cluster leg
- **D.** A supported remote Pod path through a ClusterIP Service

<details>
<summary>Show Answer</summary>

**Answer: C. Same-node Pod traffic and the external client-to-cluster leg**

Cilium WireGuard does not encrypt same-node Pod traffic, and it does not encrypt the external client-to-cluster leg. Remote-node coverage depends on the selected mode and documented exceptions. Kernel support is required; the chart does not provide a userspaceFallback option.

</details>

### 4. What is the correct configuration to restrict specific paths and methods with L7 HTTP rules in CiliumNetworkPolicy?

- **A.** Specify path and method in toEndpoints
- **B.** Specify method and path in toPorts.rules.http
- **C.** Specify directly in ingress.http
- **D.** Define rules in spec.http

<details>
<summary>Show Answer</summary>

**Answer: B. Specify method and path in toPorts.rules.http**

HTTP rules are under ingress/egress toPorts.rules.http. They can match supported method/path/header fields, but header presence or a Bearer-looking string does not verify a JWT or authorize the end user.

</details>

### 5. What is a benefit of Cilium identity-based policy?

- **A.** Policy label selectors can remain stable across Pod IP changes
- **B.** It uses MAC addresses instead of labels
- **C.** Every numeric ID is permanent across all restarts
- **D.** It eliminates address-to-identity updates

<details>
<summary>Show Answer</summary>

**Answer: A. Policy label selectors can remain stable across Pod IP changes**

Policies use identity-relevant label sets rather than manually maintained Pod-IP lists. Several Pods can share an identity, but Cilium still updates address/identity state and may garbage-collect/reallocate IDs. A restart does not guarantee a permanent numeric identifier.

</details>

### 6. Which rules are used to restrict external domain access using DNS L7 policies in Cilium?

- **A.** Combination of toFQDNs and dns rules
- **B.** toEndpoints only
- **C.** toCIDR only
- **D.** toEntities only

<details>
<summary>Show Answer</summary>

**Answer: A. Combination of toFQDNs and dns rules**

DNS rules constrain queries to the selected resolver; toFQDNs and port rules separately control connections to learned addresses. Include actual UDP/TCP resolver behavior and search-list names. A Service name includes service and namespace labels, and DNS permission is not a universal connection grant.

</details>

### 7. What should be allowed when introducing default-deny policy?

- **A.** Every external destination
- **B.** Explicit workload dependencies, including the actual resolver/probes where needed
- **C.** All host traffic as a universal minimum
- **D.** All addresses that DNS has ever returned

<details>
<summary>Show Answer</summary>

**Answer: B. Explicit workload dependencies, including the actual resolver/probes where needed**

Allow only the dependencies demonstrated by the workload and topology, such as the actual DNS resolver on UDP/TCP53 and required probes. Blanket host-network access is not a universal minimum. Use explicit enableDefaultDeny flags when the Cilium policy has empty directional rule arrays.

</details>

### 8. What is the role of workload attestation in SPIRE?

- **A.** Certificate issuance
- **B.** Verifying workload identity
- **C.** Applying network policies
- **D.** Traffic encryption

<details>
<summary>Show Answer</summary>

**Answer: B. Verifying workload identity**

The SPIRE Agent performs workload attestation using configured attestors/selectors; the Server attests agents and signs SVIDs. Cilium's out-of-band integration also uses delegated identity retrieval and entries for Cilium security identities. This is not automatic application-payload encryption.

</details>

### 9. How does Cilium behave when testing network policies in audit mode?

- **A.** Blocks all traffic
- **B.** Logs policy violations but allows traffic
- **C.** Completely disables policies
- **D.** Only sends alerts

<details>
<summary>Show Answer</summary>

**Answer: B. Logs policy violations but allows traffic**

The actual mutable endpoint option PolicyAuditMode changes audited datapath policy enforcement for an isolated endpoint test. cilium.io/audit-mode is not a supported per-policy annotation. Restore enforcement after the test and verify L7 behavior separately; enableDefaultDeny:false is not a universal audit mode either.

</details>

### 10. What does a three-tier backend's least-privilege policy need to model?

- **A.** All traffic without restrictions
- **B.** Required frontend ingress, database egress and explicit dependencies such as DNS
- **C.** No ingress even from its frontend
- **D.** Unrestricted internet access

<details>
<summary>Show Answer</summary>

**Answer: B. Required frontend ingress, database egress and explicit dependencies such as DNS**

The backend allows its required frontend callers and database destinations plus explicit dependencies such as DNS. The guide's database policy explicitly enables egress default-deny with no egress allow rules. Stateful replies remain possible; network segmentation is not complete application authorization or data-loss prevention.

</details>

### 11. What does IPsec keyRotationDuration: 5m mean?

- **A.** Generate a fresh key every five minutes
- **B.** Rotate every workload certificate every five minutes
- **C.** Allow a transition/old-key-cleanup grace period after a key change
- **D.** Reuse one global key indefinitely

<details>
<summary>Show Answer</summary>

**Answer: C. Allow a transition/old-key-cleanup grace period after a key change**

IPsec keyRotationDuration controls the transition/old-key-removal grace period after key material changes. It does not generate keys periodically. Use the supported coordinated key/ID rotation procedure and the per-tunnel derived-key form with '+'. WireGuard instead manages node-generated key pairs.

</details>

### 12. Which Hubble command selects dropped flows before inspecting their reasons?

- **A.** hubble observe --verdict FORWARDED
- **B.** hubble observe --verdict DROPPED
- **C.** hubble policy list
- **D.** hubble status --violations

<details>
<summary>Show Answer</summary>

**Answer: B. hubble observe --verdict DROPPED**

DROPPED selects dropped flows from multiple causes. Add --drop-reason-desc POLICY_DENIED when examining reported policy-denied drops, and inspect L7/application failures separately. AUDIT is a separate verdict. --last is bounded history and may be returned per Hubble instance through Relay.

</details>
