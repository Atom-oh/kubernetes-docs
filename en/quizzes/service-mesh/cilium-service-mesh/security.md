# Cilium Service Mesh Security Quiz

This quiz tests your understanding of mTLS, network policies, encryption, identity-based security, and zero-trust networking in Cilium Service Mesh.

## Quiz Questions

### 1. What technology does Cilium Service Mesh use to implement transparent mTLS?

A. Istio sidecar
B. SPIFFE/SPIRE integration
C. Nginx proxy
D. HAProxy

<details>
<summary>Show Answer</summary>

**Answer: B. SPIFFE/SPIRE integration**

**Explanation:**
Cilium Service Mesh integrates with SPIFFE (Secure Production Identity Framework for Everyone) and SPIRE to implement transparent mTLS. This enables encrypted communication between workloads without application code changes.

</details>

### 2. How does CiliumNetworkPolicy behave when authentication mode is set to 'required'?

A. Allows all traffic without authentication
B. Only allows traffic that passes mutual authentication
C. Only logs warnings on authentication failure
D. Disables mTLS

<details>
<summary>Show Answer</summary>

**Answer: B. Only allows traffic that passes mutual authentication**

**Explanation:**
When authentication mode is set to 'required', only traffic that successfully completes mutual authentication is allowed. Traffic that fails authentication is blocked. This is essential for implementing a zero-trust security model.

</details>

### 3. Which is NOT an advantage of WireGuard encryption in Cilium?

A. High performance operating at kernel level
B. Automatic key management
C. IETF standard protocol
D. ChaCha20Poly1305 encryption

<details>
<summary>Show Answer</summary>

**Answer: C. IETF standard protocol**

**Explanation:**
WireGuard is not a standard protocol. IPsec is the IETF standard protocol. However, WireGuard is built into Linux kernel 5.6+ and provides high performance, automatic key management, and ChaCha20Poly1305 encryption.

</details>

### 4. What is the correct configuration to restrict specific paths and methods with L7 HTTP rules in CiliumNetworkPolicy?

A. Specify path and method in toEndpoints
B. Specify method and path in toPorts.rules.http
C. Specify directly in ingress.http
D. Define rules in spec.http

<details>
<summary>Show Answer</summary>

**Answer: B. Specify method and path in toPorts.rules.http**

**Explanation:**
In CiliumNetworkPolicy, L7 HTTP rules are defined under rules.http within the toPorts section. Here you can specify method (GET, POST, etc.) and path (with regex support) for fine-grained access control.

</details>

### 5. What is the main advantage of Cilium Identity-based security?

A. Not affected by IP address changes
B. More secure due to MAC address basis
C. Manual ID management is possible
D. VLAN tagging support

<details>
<summary>Show Answer</summary>

**Answer: A. Not affected by IP address changes**

**Explanation:**
Cilium Identity is generated based on Pod labels, so even if a Pod restarts and its IP address changes, it maintains the same Identity. This overcomes the limitations of IP-based security policies.

</details>

### 6. Which rules are used to restrict external domain access using DNS L7 policies in Cilium?

A. Combination of toFQDNs and dns rules
B. toEndpoints only
C. toCIDR only
D. toEntities only

<details>
<summary>Show Answer</summary>

**Answer: A. Combination of toFQDNs and dns rules**

**Explanation:**
External domain access restriction is configured in two steps: 1) Allow only specific domain queries with DNS L7 rules (toPorts.rules.dns), 2) Allow actual connections to those domains with toFQDNs. This combination provides fine-grained control over workload external access.

</details>

### 7. What traffic typically needs to be allowed when implementing a default deny policy with CiliumClusterwideNetworkPolicy?

A. All external traffic
B. DNS queries and host network traffic
C. All internet traffic
D. Specific IP ranges only

<details>
<summary>Show Answer</summary>

**Answer: B. DNS queries and host network traffic**

**Explanation:**
When implementing a default deny policy, at minimum you need to allow DNS queries to kube-dns (port 53/UDP) and host network traffic (reserved:host) for the cluster to function properly. Without these, service discovery and node communication would be impossible.

</details>

### 8. What is the role of workload attestation in SPIRE?

A. Certificate issuance
B. Verifying workload identity
C. Applying network policies
D. Traffic encryption

<details>
<summary>Show Answer</summary>

**Answer: B. Verifying workload identity**

**Explanation:**
Workload attestation is the process by which the SPIRE Agent verifies a workload's identity. In Kubernetes environments, it validates the Pod's service account, namespace, labels, etc. to issue the appropriate SVID (SPIFFE Verifiable Identity Document) to that workload.

</details>

### 9. How does Cilium behave when testing network policies in audit mode?

A. Blocks all traffic
B. Logs policy violations but allows traffic
C. Completely disables policies
D. Only sends alerts

<details>
<summary>Show Answer</summary>

**Answer: B. Logs policy violations but allows traffic**

**Explanation:**
In audit mode (cilium.io/audit-mode: "true" annotation), policy-violating traffic is not blocked, only logged. This allows you to evaluate the impact of new policies before applying them to production.

</details>

### 10. What is the correct policy for backend services when implementing microsegmentation in a 3-tier architecture?

A. Allow all traffic
B. Allow ingress only from frontend, allow egress only to database
C. Block all ingress
D. Allow internet access

<details>
<summary>Show Answer</summary>

**Answer: B. Allow ingress only from frontend, allow egress only to database**

**Explanation:**
In microsegmentation, backend services follow the principle of least privilege: allow ingress only from the frontend tier and allow egress only to the database tier. This clearly defines and controls traffic between each tier.

</details>

### 11. Which statement correctly describes the difference between IPsec and WireGuard encryption in Cilium?

A. Only IPsec operates in the kernel
B. WireGuard requires manual key management
C. IPsec is IETF standard, WireGuard is non-standard
D. Only WireGuard supports node-to-node encryption

<details>
<summary>Show Answer</summary>

**Answer: C. IPsec is IETF standard, WireGuard is non-standard**

**Explanation:**
IPsec is an IETF standard protocol, while WireGuard is non-standard. Both operate in the kernel, and WireGuard provides automatic key management. Both support node-to-node encryption.

</details>

### 12. Which command is used to monitor policy violations with Hubble?

A. hubble observe --verdict FORWARDED
B. hubble observe --verdict DROPPED
C. hubble policy list
D. hubble status --violations

<details>
<summary>Show Answer</summary>

**Answer: B. hubble observe --verdict DROPPED**

**Explanation:**
The `hubble observe --verdict DROPPED` command monitors traffic that has been denied (DROPPED) by network policies. This allows real-time detection and analysis of policy violations.

</details>
