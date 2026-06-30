# EKS Hybrid Nodes Gateway Quiz

1. What problem does the EKS Hybrid Nodes Gateway solve?
   - A) It replaces VPN/Direct Connect for control plane connectivity
   - B) It automates pod-level networking between VPC and hybrid nodes using VXLAN tunnels, eliminating manual pod routing
   - C) It provides a managed NAT gateway for hybrid nodes
   - D) It encrypts all traffic between cloud and on-premises

<details>
<summary>Show Answer</summary>

**Answer: B) It automates pod-level networking between VPC and hybrid nodes using VXLAN tunnels, eliminating manual pod routing**

**Explanation:**
The EKS Hybrid Nodes Gateway automates networking between EKS cluster VPC and Kubernetes Pods on Hybrid Nodes. It creates VXLAN tunnels between EC2-based gateway nodes and Cilium-managed hybrid nodes, and automatically maintains VPC route table entries. This eliminates the need for manual BGP configuration, static routes, or making on-premises pod networks routable from the VPC. Note that VPN/Direct Connect is still required for base node connectivity.

</details>

---

2. How does the gateway maintain high availability?
   - A) Active-active with load balancing across multiple gateways
   - B) Two gateway pods as a Deployment with Kubernetes Lease-based leader election
   - C) AWS-managed redundancy with automatic failover
   - D) Running on multiple Availability Zones with Route 53 health checks

<details>
<summary>Show Answer</summary>

**Answer: B) Two gateway pods as a Deployment with Kubernetes Lease-based leader election**

**Explanation:**
The gateway runs as a 2-pod Deployment on labeled EC2 nodes. A Kubernetes Lease-based leader election determines which pod is active. Only the leader performs leader-specific actions: managing VPC route table entries and the CiliumVTEPConfig CRD. When the leader fails, leadership transfers to the standby pod, which then updates VPC routes to point to its own ENI.

</details>

---

3. What is the role of CiliumVTEPConfig in the gateway architecture?
   - A) It configures Cilium network policies for hybrid nodes
   - B) It registers the gateway IP as a remote VTEP so Cilium agents on hybrid nodes forward VPC-bound traffic through the gateway's VXLAN tunnel
   - C) It manages Cilium version upgrades across the cluster
   - D) It provides encryption keys for VXLAN tunnels

<details>
<summary>Show Answer</summary>

**Answer: B) It registers the gateway IP as a remote VTEP so Cilium agents on hybrid nodes forward VPC-bound traffic through the gateway's VXLAN tunnel**

**Explanation:**
The gateway leader creates the CiliumVTEPConfig resource. Each on-premises hybrid node's Cilium agent reads this configuration and registers the gateway IP as a remote VTEP (VXLAN Tunnel Endpoint). This allows Cilium to know where to send VPC-bound traffic — through the gateway's VXLAN tunnel rather than trying to route it directly, which would fail without routable pod CIDRs.

</details>

---

4. What are the CNI prerequisites for using the Hybrid Nodes Gateway?
   - A) Any CNI on both cloud and hybrid nodes
   - B) Cilium on cloud nodes and VPC CNI on hybrid nodes
   - C) Cilium (with VTEP enabled) on hybrid nodes and VPC CNI on cloud nodes
   - D) VPC CNI on both cloud and hybrid nodes

<details>
<summary>Show Answer</summary>

**Answer: C) Cilium (with VTEP enabled) on hybrid nodes and VPC CNI on cloud nodes**

**Explanation:**
The gateway requires: (1) The EKS version of Cilium as the CNI on hybrid nodes with VTEP support enabled, so hybrid nodes can participate in VXLAN tunneling. (2) AWS VPC CNI on cloud nodes, as the gateway relies on VPC-native routing to forward traffic between the VPC and the VXLAN tunnel. Both CNIs work together through the gateway to enable seamless pod-to-pod communication.

</details>

---

5. What VXLAN configuration does the gateway use?
   - A) VNI 1 on UDP port 4789 (standard VXLAN)
   - B) VNI 2 on UDP port 8472 (Cilium default)
   - C) VNI 100 on UDP port 6081 (Geneve)
   - D) VNI 0 on UDP port 443 (HTTPS encapsulation)

<details>
<summary>Show Answer</summary>

**Answer: B) VNI 2 on UDP port 8472 (Cilium default)**

**Explanation:**
The gateway creates a VXLAN interface named `hybrid_vxlan0` with VNI (VXLAN Network Identifier) 2 on UDP port 8472, which is the Cilium default VXLAN port. It establishes a tunnel to each hybrid node by programming FDB (Forwarding Database) entries, ARP entries, and routes on the VXLAN interface. Security groups and on-premises firewalls must allow UDP 8472 bidirectionally.

</details>

---

6. How does the gateway manage VPC routing?
   - A) It uses BGP to advertise pod routes to the VPC router
   - B) It automatically creates and maintains VPC route table entries pointing hybrid pod CIDRs to the active gateway's primary ENI
   - C) It modifies the VPC's main route table to add NAT rules
   - D) It configures Transit Gateway route tables

<details>
<summary>Show Answer</summary>

**Answer: B) It automatically creates and maintains VPC route table entries pointing hybrid pod CIDRs to the active gateway's primary ENI**

**Explanation:**
The gateway's node controller watches CiliumNode objects and automatically adds or removes VXLAN tunnels as hybrid nodes join or leave. The leader pod maintains VPC route table entries, routing each hybrid pod CIDR to the active gateway instance's primary ENI. This is why the gateway's IAM role needs ec2:DescribeRouteTables, ec2:CreateRoute, and ec2:ReplaceRoute permissions.

</details>

---

7. What is the pricing model for the EKS Hybrid Nodes Gateway?
   - A) Per-hour charge based on data processed
   - B) Included in EKS Hybrid Nodes pricing at $0.10 per hybrid node per hour
   - C) No additional charge for the gateway itself, but EC2 instance costs for gateway nodes apply
   - D) Free for the first 3 months, then standard AWS networking charges

<details>
<summary>Show Answer</summary>

**Answer: C) No additional charge for the gateway itself, but EC2 instance costs for gateway nodes apply**

**Explanation:**
The EKS Hybrid Nodes Gateway is offered at no additional charge and is open source (available on GitHub). However, since the gateway runs on EC2 instances in your VPC, you pay standard EC2 instance costs for the gateway nodes. This makes it a cost-effective solution compared to managing complex BGP or static routing infrastructure manually.

</details>

---

8. When should you choose the gateway approach over manual pod routing (BGP/static routes)?
   - A) When you need the lowest possible latency between cloud and on-premises pods
   - B) When you want to simplify operations and avoid making on-premises pod networks routable, while enabling webhook communication and AWS service integration
   - C) When you have more than 1000 hybrid nodes
   - D) When using a non-Cilium CNI on hybrid nodes

<details>
<summary>Show Answer</summary>

**Answer: B) When you want to simplify operations and avoid making on-premises pod networks routable, while enabling webhook communication and AWS service integration**

**Explanation:**
The gateway is ideal when you want to avoid complex network infrastructure changes (BGP configuration, static route management). It automatically enables: (1) Control plane-to-webhook communication on hybrid nodes, (2) Pod-to-pod traffic between cloud and on-premises, (3) AWS service connectivity (ALB, NLB, Prometheus) to hybrid pods. The manual BGP approach may still be preferred when you already have BGP infrastructure or need to minimize the extra hop through the gateway.

</details>
