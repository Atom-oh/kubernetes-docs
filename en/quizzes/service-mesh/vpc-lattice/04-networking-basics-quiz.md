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
The IPv4 range falls inside `169.254.0.0/16` (RFC 3927, link-local), but the IPv6 range is not `fe80::/10` (link-local) — it is `fd00:ec2:80::/64` inside the `fc00::/7` ULA range (RFC 4193). The difference is scope: link-local has link scope and cannot cross a router, while a ULA has site scope and routes within a private network. Lattice traffic must travel within the VPC to reach an ingress endpoint, so link scope would be insufficient.
</details>

2. What is the fundamental reason Lattice uses a link-local address range?
   - A) To conserve IP addresses
   - B) To secure a point where the infrastructure intercepts traffic without a sidecar — the range is a marker meaning "the infrastructure handles this packet"
   - C) To cope with IPv4 address exhaustion
   - D) To make the client explicitly aware of the destination

<details>

<summary>Show Answer</summary>

**Answer: B) To secure a point where the infrastructure intercepts traffic without a sidecar — the range is a marker meaning "the infrastructure handles this packet"**

**Explanation:**
If there is no sidecar, something must intercept the traffic, and link-local addresses are the answer. This is the same family as EC2 IMDS (`169.254.169.254`) and the EKS Pod Identity Agent (`169.254.170.23`) — the common property being that the address routes nowhere and the infrastructure intercepts and handles it. The client sends an ordinary HTTP request and the application does not know Lattice exists: traffic traverses the infrastructure without touching code, Pod specs, or iptables.
</details>

3. What commonly causes all Lattice calls to fail when App Mesh and Lattice run side by side?
   - A) Exceeding Lattice quotas
   - B) The iptables rules installed by the App Mesh init container also intercept Lattice-bound traffic into Envoy, with no exception CIDR registered
   - C) A Gateway API CRD version mismatch
   - D) A Target Group protocol misconfiguration

<details>

<summary>Show Answer</summary>

**Answer: B) The iptables rules installed by the App Mesh init container also intercept Lattice-bound traffic into Envoy, with no exception CIDR registered**

**Explanation:**
Sidecar meshes install iptables rules that redirect all outbound traffic from the Pod to Envoy's port. Lattice-bound traffic is outbound too, so Envoy intercepts it — but Envoy cannot find that destination in its configuration and the request fails. The fix is excluding the Lattice range (`169.254.171.0/24`, plus `fd00:ec2:80::/64` if you use IPv6) from interception. Istio uses the `traffic.sidecar.istio.io/excludeOutboundIPRanges` annotation.
</details>

4. Why does destination-IP-based observability and control become meaningless after adopting Lattice, and what is the alternative?
   - A) Destination IPs become encrypted — there is no alternative
   - B) Every Lattice service appears in the same link-local range and does not identify a service — move authorization to auth policies, observability to access logs, and Security Groups to managed prefix lists
   - C) Flow logs get disabled — enabling them solves it
   - D) The VPC CNI reuses IPs — changing the IP allocation policy solves it

<details>

<summary>Show Answer</summary>

**Answer: B) Every Lattice service appears in the same link-local range and does not identify a service — move authorization to auth policies, observability to access logs, and Security Groups to managed prefix lists**

**Explanation:**
Link-local addresses are not globally unique and do not identify a service, so flow log destination IPs cannot tell you the peer, and destination-CIDR SG egress rules or NetworkPolicy `ipBlock` cannot distinguish services. The alternative is moving the control layer: authorization via auth policy principal/path/method/header conditions, observability via Lattice access logs, and Security Groups via the `com.amazonaws.<region>.vpc-lattice` prefix list. This is a shift from "control by IP and port" to "control by identity and policy."
</details>

5. Why is SNI carried in plaintext in the TLS `ClientHello`?
   - A) It is a leftover vulnerability from early TLS design
   - B) The chicken-and-egg problem of certificate selection — to start encryption you need the domain, but the domain is inside the encrypted `Host` header, so sending it in plaintext before encryption starts breaks the loop
   - C) SNI encryption was skipped for performance
   - D) It was deliberately exposed to allow firewall traversal

<details>

<summary>Show Answer</summary>

**Answer: B) The chicken-and-egg problem of certificate selection — to start encryption you need the domain, but the domain is inside the encrypted `Host` header, so sending it in plaintext before encryption starts breaks the loop**

**Explanation:**
Serving multiple domains from one IP:port requires the server to pick a certificate, which requires knowing the domain the client wants. But that domain is in the HTTP `Host` header, which arrives encrypted inside TLS. The only way to break the circularity is to send the domain in plaintext in the `ClientHello` before encryption begins. So it is a deliberate compromise, not a design mistake — and thanks to it, middleboxes that do not terminate TLS can still learn the destination domain, which is what makes TLS Passthrough routing possible.
</details>

6. What is the fundamental reason Lattice does not support a standalone raw TCP listener?
   - A) TCP is not a supported protocol on the AWS network
   - B) Without TLS there is no `ClientHello` and therefore no SNI, leaving no basis for routing — and the destination IP is link-local, which identifies no service
   - C) An NLB already does this, so it would be redundant
   - D) Security regulations prohibit plaintext communication

<details>

<summary>Show Answer</summary>

**Answer: B) Without TLS there is no `ClientHello` and therefore no SNI, leaving no basis for routing — and the destination IP is link-local, which identifies no service**

**Explanation:**
The minimum unit of what Lattice does is deciding which Target a connection goes to, and that decision needs evidence. HTTP/HTTPS has abundant evidence (path, headers, method); TLS Passthrough has one piece (SNI); raw TCP has none — only a port number, and a port alone cannot multiplex several services. Because this is a constraint of principle it is unlikely to be resolved, so plaintext TCP services need a hybrid configuration with something like an NLB.
</details>

7. Which statement correctly describes the trade-off between an HTTPS listener and TLS Passthrough?
   - A) TLS Passthrough is superior in every respect
   - B) Preserving end-to-end encryption means giving up L7 routing and IAM Auth; using L7 routing and IAM Auth means accepting that TLS is terminated once at Lattice
   - C) Both can be applied to the same service simultaneously
   - D) An HTTPS listener cannot see SNI

<details>

<summary>Show Answer</summary>

**Answer: B) Preserving end-to-end encryption means giving up L7 routing and IAM Auth; using L7 routing and IAM Auth means accepting that TLS is terminated once at Lattice**

**Explanation:**
An HTTPS listener terminates TLS, so it can see path, headers, method, and the `Authorization` header — enabling L7 routing and IAM Auth — but creates a point where traffic is plaintext at Lattice. TLS Passthrough preserves end-to-end encryption and the endpoint's own mTLS, but Lattice sees only SNI, so L7 routing and IAM Auth are impossible. You must pick one; you cannot have both on the same service. Note that SNI is visible in both modes.
</details>
