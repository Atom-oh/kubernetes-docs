# Foundations — Link-Local and SNI Quiz

This quiz tests your understanding of link-local/ULA addressing, how SNI works, and Lattice's protocol support.

## Multiple Choice Questions

1. Which statement about the address ranges a VPC Lattice service DNS name resolves to is correct?
   - A) Both IPv4 `169.254.171.0/24` and IPv6 `fe80::/10` are link-local
   - B) IPv4 `169.254.171.0/24` is link-local, while IPv6 `fd00:ec2:80::/64` is not link-local but a Unique Local Address (ULA)
   - C) Both ranges are globally unique public addresses
   - D) IPv6 is not supported

<details>

<summary>Show Answer</summary>

**Answer: B) IPv4 `169.254.171.0/24` is link-local, while IPv6 `fd00:ec2:80::/64` is not link-local but a Unique Local Address (ULA)**

**Explanation:**
The IPv4 range falls inside `169.254.0.0/16` (RFC 3927, link-local), but the IPv6 range is not `fe80::/10` (link-local) — it is `fd00:ec2:80::/64` inside the `fc00::/7` ULA range (RFC 4193). Link-local addresses have link scope. ULAs have global address scope under RFC 6724, but are intended for private routing rather than global Internet reachability; they are not the deprecated site-local address class. These address classifications do not by themselves describe AWS's special Lattice ingress implementation.
</details>

2. How should the Lattice address ranges be interpreted?
   - A) To conserve IP addresses
   - B) Use AWS-documented service-specific addressing; do not turn the prefix into a general definition of link-local interception
   - C) To cope with IPv4 address exhaustion
   - D) To make the client explicitly aware of the destination

<details>

<summary>Show Answer</summary>

**Answer: B) Use AWS-documented service-specific addressing; do not turn the prefix into a general definition of link-local interception**

**Explanation:**
The service-specific route and association determine reachability. ULA is not link-local or the deprecated site-local class; address scope and routing reachability differ.
</details>

3. Lattice-bound requests appear in Envoy logs during coexistence. What should be checked next?
   - A) Exceeding Lattice quotas
   - B) Check whether mesh interception and the configured outbound route/signing policy explain the failure
   - C) A Gateway API CRD version mismatch
   - D) A Target Group protocol misconfiguration

<details>

<summary>Show Answer</summary>

**Answer: B) Check whether mesh interception and the configured outbound route/signing policy explain the failure**

**Explanation:**
Some Envoy policies reject unknown destinations and others forward them. Inspect rules and logs, then test the chosen bypass or forwarding design; coexistence does not imply inevitable failure.
</details>

4. Why is destination IP alone insufficient for stable service identity and authorization?
   - A) Destination IPs become encrypted — there is no alternative
   - B) Use service-aware identity, DNS/request correlation and reviewed network rules rather than relying on IP alone
   - C) Flow logs get disabled — enabling them solves it
   - D) The VPC CNI reuses IPs — changing the IP allocation policy solves it

<details>

<summary>Show Answer</summary>

**Answer: B) Use service-aware identity, DNS/request correlation and reviewed network rules rather than relying on IP alone**

**Explanation:**
Service identity is not a stable per-service CIDR security boundary. Network evidence remains useful when combined with auth policies, service logs and request IDs. SG changes must use reviewed IaC.
</details>

5. What is the correct SNI/ECH distinction?
   - A) It is a leftover vulnerability from early TLS design
   - B) Ordinary TLS exposes SNI to select a certificate; ECH is another design, but Lattice TLS passthrough does not support it
   - C) SNI encryption was skipped for performance
   - D) It was deliberately exposed to allow firewall traversal

<details>

<summary>Show Answer</summary>

**Answer: B) Ordinary TLS exposes SNI to select a certificate; ECH is another design, but Lattice TLS passthrough does not support it**

**Explanation:**
TLS passthrough requires a custom domain matching SNI. AWS explicitly excludes ECH/ESNI there, so do not state that plaintext SNI is universally unavoidable or that Lattice support is merely unknown.
</details>

6. Which statement about raw TCP in VPC Lattice is correct?
   - A) TCP is not a supported protocol on the AWS network
   - B) Raw TCP is absent from service listeners, but TCP resource configurations/resource gateways are a separate supported model
   - C) An NLB already does this, so it would be redundant
   - D) Security regulations prohibit plaintext communication

<details>

<summary>Show Answer</summary>

**Answer: B) Raw TCP is absent from service listeners, but TCP resource configurations/resource gateways are a separate supported model**

**Explanation:**
Do not call this a product-wide mathematical impossibility. Compare the separate resource-connectivity access model, controller support and routing needs; do not classify h2c gRPC as arbitrary raw TCP.
</details>

7. Which statement correctly describes the trade-off between an HTTPS listener and TLS Passthrough?
   - A) TLS Passthrough is superior in every respect
   - B) Passthrough preserves endpoint TLS but cannot inspect HTTP SigV4 identity; anonymous network-context policies are a different control
   - C) Both listener types authenticate encrypted HTTP SigV4 headers without decryption
   - D) An HTTPS listener cannot see SNI

<details>

<summary>Show Answer</summary>

**Answer: B) Passthrough preserves endpoint TLS but cannot inspect HTTP SigV4 identity; anonymous network-context policies are a different control**

**Explanation:**
The loss is authenticated HTTP identity and L7 inspection, not every form of auth policy. Select listener and endpoint controls explicitly; backend HTTPS encryption does not mean Lattice validates target certificates.
</details>
