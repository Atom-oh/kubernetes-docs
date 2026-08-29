# Network Fundamentals Part 4 Quiz — The Journey and the Cloud

> **Last Updated**: August 28, 2026

Tests your understanding of a request's full journey and the cloud/Kubernetes mapping.

## Multiple Choice Questions

1. Which is the correct order of protocol operations when visiting `https://example.com`?
   - A) TLS → DNS → ARP → TCP → HTTP
   - B) DNS lookup → gateway ARP → IP routing/NAT → TCP/QUIC+TLS connection → HTTP request
   - C) ARP → TLS → DNS → NAT → HTTP
   - D) TCP connection → DNS lookup → TLS → routing → HTTP

<details>
<summary>Show Answer</summary>

**Answer: B) DNS lookup → gateway ARP → IP routing/NAT → TCP/QUIC+TLS connection → HTTP request**

**Explanation:**
You need the destination IP before you can build packets (DNS), the gateway MAC before you can send frames (ARP), and only after routing and NAT reach the peer can the transport connection and encryption (TCP/QUIC+TLS) be established — with HTTP flowing on top. Lower layers must work before upper layers can exist.

</details>

2. Which correctly pairs the Kubernetes component that translates a Service's ClusterIP into real pod IPs with its traditional networking counterpart?
   - A) CoreDNS — DHCP
   - B) kube-proxy — NAT + L4 load balancing
   - C) CNI plugin — TLS termination
   - D) NetworkPolicy — BGP routing

<details>
<summary>Show Answer</summary>

**Answer: B) kube-proxy — NAT + L4 load balancing**

**Explanation:**
kube-proxy uses iptables/IPVS (or eBPF depending on the CNI) rules to translate the virtual ClusterIP into real pod IPs and spread traffic across pods — traditionally, a combination of NAT and L4 load balancing. CoreDNS maps to DNS, the CNI's IPAM to DHCP/IP assignment, and NetworkPolicy to firewall rules.

</details>

3. For an EKS workload with heavy outbound traffic, what is the standard design for cutting NAT Gateway costs?
   - A) Consolidate to one NAT Gateway per region
   - B) Route AWS service traffic (S3, ECR, …) through VPC endpoints so it bypasses the NAT Gateway
   - C) Give every pod a public IP
   - D) Disable IPv6

<details>
<summary>Show Answer</summary>

**Answer: B) Route AWS service traffic (S3, ECR, …) through VPC endpoints so it bypasses the NAT Gateway**

**Explanation:**
NAT Gateway bills by data processed, so redirecting high-volume AWS service paths like S3 and ECR through VPC endpoints (gateway/interface) cuts costs substantially and reduces port-exhaustion risk. IP address planning, the outbound path, and the encryption termination point are the three decisions to settle early in design.

</details>

---

[Back to Study Material](../../basics/06-network-fundamentals-part4.md) | [Next Quiz: Cluster Architecture](../core/01-cluster-architecture-quiz.md)
