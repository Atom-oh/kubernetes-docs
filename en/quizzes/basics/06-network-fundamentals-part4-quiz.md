# Network Fundamentals Part 4 Quiz — The Journey and the Cloud

> **Last Updated**: September 11, 2026

Tests your understanding of a request's full journey and the cloud/Kubernetes mapping.

## Multiple Choice Questions

1. For a new HTTPS connection, which is the correct conceptual dependency order (with caches and existing connections excluded)?
   - A) TLS → DNS → ARP → TCP → HTTP
   - B) Resolve the server address → use link/IP connectivity → TCP+TLS or QUIC handshake → HTTP request
   - C) ARP → TLS → DNS → NAT → HTTP
   - D) TCP connection → DNS lookup → TLS → routing → HTTP

<details>
<summary>Show Answer</summary>

**Answer: B) Resolve the server address → use link/IP connectivity → TCP+TLS or QUIC handshake → HTTP request**

**Explanation:**
This is a dependency summary, not a packet trace. DNS messages already use link/IP connectivity, and ARP or IPv6 Neighbor Discovery may occur during DNS or later traffic. NAT is optional and routing applies to every relevant packet. HTTP/3 uses QUIC with TLS1.3 integrated; HTTP/1.1 and HTTP/2 commonly use TCP with a separate TLS handshake for HTTPS.

</details>

2. In a cluster using kube-proxy, which pairing describes ordinary ClusterIP Service forwarding?
   - A) CoreDNS — DHCP
   - B) kube-proxy — NAT + L4 load balancing
   - C) CNI plugin — TLS termination
   - D) NetworkPolicy — BGP routing

<details>
<summary>Show Answer</summary>

**Answer: B) kube-proxy — NAT + L4 load balancing**

**Explanation:**
On Linux, kube-proxy programs iptables or nftables; its IPVS mode is deprecated since Kubernetes1.35. An eBPF-based Service implementation can replace kube-proxy, but is not a kube-proxy eBPF mode. Service/EndpointSlice state supplies eligible endpoints. Headless Services do not use a ClusterIP, and NetworkPolicy needs a supporting implementation.

</details>

3. Which option can reduce NAT Gateway processing for supported AWS service traffic, after checking endpoint dependencies and total cost?
   - A) Consolidate to one NAT Gateway per region
   - B) Use suitable VPC endpoints for supported service traffic, with the required DNS, routes and access policies
   - C) Give every pod a public IP
   - D) Disable IPv6

<details>
<summary>Show Answer</summary>

**Answer: B) Use suitable VPC endpoints for supported service traffic, with the required DNS, routes and access policies**

**Explanation:**
Endpoints can remove matching service traffic from the NAT path, but interface endpoints have hourly/data charges and topology matters. S3/DynamoDB gateway endpoints have no additional endpoint charge. Private ECR image pulls commonly need ecr.api and ecr.dkr interface endpoints plus an S3 path, private DNS and appropriate access. Pull-through-cache first pulls or external Windows layers can still need internet access. Calculate total cost and preserve required egress; savings and elimination of port exhaustion are not universal guarantees.

</details>

---

[Back to Study Material](../../basics/06-network-fundamentals-part4.md) | [Next Quiz: Cluster Architecture](../core/01-cluster-architecture-quiz.md)
