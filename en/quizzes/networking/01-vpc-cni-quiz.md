# Amazon VPC CNI Quiz

The following questions test your understanding of Amazon VPC CNI.

---

1. What is the primary role of IPAMD (L-IPAM Daemon) in VPC CNI?
   - A) Managing Pod DNS settings
   - B) Pre-allocating and managing ENIs and IP addresses
   - C) Applying Network Policies
   - D) Encrypting inter-node traffic

<details>
<summary>Show Answer</summary>

**Answer: B) Pre-allocating and managing ENIs and IP addresses**

**Explanation:**
IPAMD (L-IPAM Daemon) is a daemon running on each node that manages ENIs (Elastic Network Interfaces) and pre-allocates IP addresses so that IPs can be quickly assigned when Pods are created. The CNI Binary is called by kubelet, receives IPs from IPAMD, and sets up Pod network namespaces.

</details>

---

2. What is the key difference between Secondary IP mode and Prefix Delegation mode?
   - A) Secondary IP supports only IPv6, Prefix Delegation supports only IPv4
   - B) Secondary IP allocates individual IPs, Prefix Delegation allocates /28 prefixes (16 IPs)
   - C) Secondary IP is only for EKS, Prefix Delegation is only for self-managed clusters
   - D) Secondary IP uses overlay networks, Prefix Delegation uses direct routing

<details>
<summary>Show Answer</summary>

**Answer: B) Secondary IP allocates individual IPs, Prefix Delegation allocates /28 prefixes (16 IPs)**

**Explanation:**
Secondary IP mode assigns individual IP addresses one at a time to each ENI, while Prefix Delegation mode assigns /28 IPv4 prefixes (16 IPs) at once. This allows running more Pods per node and also improves IP allocation speed.

</details>

---

3. Why is the maximum Pod count for an m5.large instance 29 with VPC CNI?
   - A) Because Kubernetes has a default limit of 29
   - B) Maximum 3 ENIs × 10 IPs per ENI = 30, minus ENI count (3) for primary IPs
   - C) Limited by an AWS soft limit
   - D) Limited by VPC subnet size

<details>
<summary>Show Answer</summary>

**Answer: B) Maximum 3 ENIs × 10 IPs per ENI = 30, minus ENI count (3) for primary IPs**

**Explanation:**
The maximum Pod count in VPC CNI is calculated as (Number of ENIs × IPs per ENI) - Number of ENIs. The m5.large supports up to 3 ENIs with 10 IPv4 addresses per ENI. Since each ENI's Primary IP is used by the node, (3 × 10) - 3 = 27. The actual number may vary slightly due to host networking Pods and additional factors.

</details>

---

4. What is the purpose of the WARM_IP_TARGET environment variable?
   - A) Setting the maximum number of IPs that can be assigned to Pods
   - B) Setting the number of spare IPs to pre-allocate on each node
   - C) Limiting the total number of IPs across the cluster
   - D) Setting the TTL (Time To Live) for IP addresses

<details>
<summary>Show Answer</summary>

**Answer: B) Setting the number of spare IPs to pre-allocate on each node**

**Explanation:**
WARM_IP_TARGET controls the number of spare IPs that IPAMD pre-allocates on each node. This ensures IPs are available immediately when new Pods are created. A larger value speeds up Pod startup but uses more IPs, while a smaller value improves IP efficiency but may slow down Pod startup.

</details>

---

5. Which statement about VPC CNI's native Network Policy support is correct?
   - A) It uses Calico internally to enforce Network Policies
   - B) It supports native eBPF-based Network Policy starting from v1.14
   - C) Network Policy is not supported on EKS
   - D) It uses iptables to enforce Network Policies

<details>
<summary>Show Answer</summary>

**Answer: B) It supports native eBPF-based Network Policy starting from v1.14**

**Explanation:**
Starting from VPC CNI v1.14, native Kubernetes Network Policy based on eBPF is supported. Previously, a separate Network Policy engine like Calico was needed, but now VPC CNI itself can process standard Kubernetes NetworkPolicy resources.

</details>

---

6. What is the main purpose of using Custom Networking (ENIConfig)?
   - A) Customizing Pod DNS server settings
   - B) Assigning Pod IPs from a different subnet than the node
   - C) Installing custom CNI plugins
   - D) Renaming the node's network interface

<details>
<summary>Show Answer</summary>

**Answer: B) Assigning Pod IPs from a different subnet than the node**

**Explanation:**
Custom Networking uses ENIConfig CRDs to assign Pod IPs from a different subnet than the node. This is useful when node subnet IPs are insufficient, when different security groups need to be applied to Pods, or when node and Pod networks need separation. It is typically used with Secondary CIDRs (e.g., 100.64.0.0/16).

</details>

---

7. What are the roles of Trunk ENI and Branch ENI in per-Pod Security Group feature?
   - A) Trunk ENI handles external traffic, Branch ENI handles internal traffic
   - B) Trunk ENI is the node's main ENI hosting Branch ENIs, Branch ENIs are virtual ENIs assigned to each Pod
   - C) Trunk ENI is for IPv4, Branch ENI is for IPv6
   - D) Trunk ENI and Branch ENI perform identical roles

<details>
<summary>Show Answer</summary>

**Answer: B) Trunk ENI is the node's main ENI hosting Branch ENIs, Branch ENIs are virtual ENIs assigned to each Pod**

**Explanation:**
Per-Pod Security Groups use a Trunk/Branch ENI architecture. The Trunk ENI is the main ENI attached to the node that hosts multiple Branch ENIs. Branch ENIs are virtual network interfaces assigned to each Pod, enabling independent AWS Security Group enforcement. This allows fine-grained network security control at the Pod level.

</details>

---

8. Which is NOT an effective solution for IP exhaustion issues?
   - A) Enable Prefix Delegation
   - B) Add Secondary CIDR
   - C) Switch all Pods to host network mode
   - D) Use Custom Networking with dedicated Pod subnets

<details>
<summary>Show Answer</summary>

**Answer: C) Switch all Pods to host network mode**

**Explanation:**
Running all Pods in host network mode (`hostNetwork: true`) would technically resolve IP allocation issues, but it eliminates network isolation between Pods and can cause port conflicts, making it an impractical solution. Proper solutions for IP exhaustion include enabling Prefix Delegation, adding Secondary CIDRs, using Custom Networking, and tuning WARM_IP_TARGET.

</details>
