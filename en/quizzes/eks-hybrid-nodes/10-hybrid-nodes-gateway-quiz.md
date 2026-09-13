# EKS Hybrid Nodes Gateway Quiz

> **Last Updated**: September 13, 2026

1. What problem does the EKS Hybrid Nodes Gateway solve?
   - A) It replaces VPN/Direct Connect for control plane connectivity
   - B) It automates the gateway-managed Pod routes and VXLAN forwarding between VPC and Hybrid nodes
   - C) It provides a managed NAT gateway for hybrid nodes
   - D) It encrypts all traffic between cloud and on-premises

<details>
<summary>Show Answer</summary>

**Answer: B) It automates the gateway-managed Pod routes and VXLAN forwarding between VPC and Hybrid nodes**

**Explanation:**
The gateway programs aggregate VPC Pod-CIDR routes and local VXLAN forwarding state. The underlay must still route between gateway and Hybrid node IPs over the approved private connection. Review route-table ownership, return paths and security rules; installation does not remove every manual network task, and uninstall does not delete AWS routes.

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
The chart defaults to two replicas with required host anti-affinity and preferred AZ anti-affinity. Both maintain local tunnel entries; only the leader updates VPC routes and CiliumVTEPConfig. Lease expiry, route replacement, Cilium convergence and application recovery can interrupt traffic. More standby replicas do not distribute throughput, and a PDB does not guarantee leader-first or standby-first replacement.

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
Gateway 1.0.2 manages the cilium.io/v2 object named hybrid-gateway. Its spec.endpoints entries contain name, tunnelEndpoint, cidr and mac. The endpoint uses the current leader node IP and actual VXLAN interface MAC. It is not an encryption-key resource, and VNI is not one of these CRD fields.

</details>

---

4. What are the CNI prerequisites for using the Hybrid Nodes Gateway?
   - A) Any CNI on both cloud and hybrid nodes
   - B) Cilium on cloud nodes and VPC CNI on hybrid nodes
   - C) AWS-maintained Cilium with VTEP enabled and L7 disabled, plus the correct cloud-node networking configuration
   - D) VPC CNI on both cloud and hybrid nodes

<details>
<summary>Show Answer</summary>

**Answer: C) AWS-maintained Cilium with VTEP enabled and L7 disabled, plus the correct cloud-node networking configuration**

**Explanation:**
Use an AWS-maintained Cilium branch/version meeting the gateway VTEP minimum, with vtep.enabled=true and l7Proxy=false. Cilium Ingress/Gateway API L7 features cannot share that configuration. Managed/self-managed cloud nodes using aws-node need Hybrid Pod CIDRs excluded from SNAT for ClusterIP traffic to Hybrid endpoints. Auto Mode supplies built-in networking; do not install or configure an aws-node DaemonSet for it. A direct Pod-IP test alone does not verify ClusterIP behavior.

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
The default interface is hybrid_vxlan0 with VNI 2 and UDP 8472. Version 1.0.2 does not assign an IP to that interface. It derives deterministic MACs and installs FDB/neighbor/onlink route entries using each Hybrid node internal IP and Pod CIDR. Allow the required underlay UDP path in both directions. VXLAN encapsulation does not encrypt the traffic.

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
The leader setup creates or replaces routes for configured aggregate podCIDRs, then updates CiliumVTEPConfig. CiliumNode events separately update local per-node tunnel entries on every gateway replica. Runtime permissions are DescribeRouteTables, DescribeInstances, CreateRoute and ReplaceRoute. It does not call DeleteRoute; after retiring the gateway, operators must review and remove or restore only the routes they own.

</details>

---

7. What is the pricing model for the EKS Hybrid Nodes Gateway?
   - A) Per-hour charge based on data processed
   - B) Included in EKS Hybrid Nodes pricing at $0.10 per hybrid node per hour
   - C) No gateway software charge; EC2 and other applicable infrastructure/traffic charges still apply
   - D) Free for the first 3 months, then standard AWS networking charges

<details>
<summary>Show Answer</summary>

**Answer: C) No gateway software charge; EC2 and other applicable infrastructure/traffic charges still apply**

**Explanation:**
There is no additional gateway software charge. EC2, applicable Auto Mode management fees, storage, cross-AZ data transfer, private connectivity and observability can still cost money, in addition to the cluster and Hybrid Nodes charges. The total depends on deployment and traffic; this is not a universal cost-saving guarantee.

</details>

---

8. When should you choose the gateway approach over manual pod routing (BGP/static routes)?
   - A) When you need the lowest possible latency between cloud and on-premises pods
   - B) When the AWS Cilium/VTEP profile and gateway hop suit the design and simplify Pod-route management
   - C) When you have more than 1000 hybrid nodes
   - D) When using a non-Cilium CNI on hybrid nodes

<details>
<summary>Show Answer</summary>

**Answer: B) When the AWS Cilium/VTEP profile and gateway hop suit the design and simplify Pod-route management**

**Explanation:**
The gateway can simplify Pod route management when the required AWS Cilium/VTEP profile and an additional active-standby hop suit the design. Webhooks and ALB/NLB targets still require their own routing, return path, remote Pod configuration, health checks and security rules. Manual routable Pod networks can also support these paths. Existing BGP/static routing or different CNI/L7 needs can favor another design.

</details>
