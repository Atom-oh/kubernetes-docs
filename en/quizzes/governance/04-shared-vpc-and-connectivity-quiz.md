# Shared VPC and Connectivity Quiz

> This quiz tests your understanding of [Shared VPC and Connectivity](../../governance/04-shared-vpc-and-connectivity.md).

---

1. In a large hub-and-spoke Shared VPC setup, which quota is actually hit first?
   - A) IPv4 CIDRs per VPC (5, adjustable up to 50)
   - B) Propagated routes per VPC route table (100, not adjustable)
   - C) Subnets per VPC (200)
   - D) NAU per VPC (64,000, adjustable up to 256,000)

<details>
<summary>Show Answer</summary>

**Answer: B) Propagated routes per VPC route table (100, not adjustable)**

**Explanation:**
Enabling route propagation from the central TGW hub stops working the moment VPC + on-prem prefixes exceed 100 combined. This is the only non-adjustable item and the real first bottleneck — the IPv4 CIDR limit is actually the last one you'll hit.

</details>

---

2. Which resource can a participant not describe at all in a Shared VPC?
   - A) Subnet
   - B) Security Group (their own)
   - C) NAT Gateway
   - D) Route table

<details>
<summary>Show Answer</summary>

**Answer: C) NAT Gateway**

**Explanation:**
A participant cannot even describe a NAT Gateway. This creates an auditability problem when the PII tier sits in a participant Account with a centrally-owned VPC — the data-owning team can't verify their own data's egress path.

</details>

---

3. What's recommended for AWS Load Balancer Controller's subnet auto-discovery in a Shared VPC + EKS combination?
   - A) It's always safe to rely on auto-discovery
   - B) Since VPC/subnet tags aren't shared with participants, standardize on explicitly annotating subnet IDs on Ingress/Service resources instead
   - C) Ingress must always be created in the owner Account
   - D) Subnets can only be discovered through the NAT Gateway

<details>
<summary>Show Answer</summary>

**Answer: B) Since VPC/subnet tags aren't shared with participants, standardize on explicitly annotating subnet IDs on Ingress/Service resources instead**

**Explanation:**
Tags like `kubernetes.io/role/elb` belong to the owner and aren't guaranteed to be visible in the participant Account. Don't rely on auto-discovery — explicit annotation is the safer standard.

</details>

---

4. Which VPC Lattice constraint is especially problematic for long-lived connections (gRPC streaming, WebSocket, etc.)?
   - A) Service network associations per VPC are limited to 1
   - B) The max connection lifetime for a Lattice service is 10 minutes
   - C) MTU is limited to 8,500 bytes
   - D) Service networks per Region are limited to 50

<details>
<summary>Show Answer</summary>

**Answer: B) The max connection lifetime for a Lattice service is 10 minutes**

**Explanation:**
A Lattice service forcibly cuts long-lived connections every 10 minutes, requiring the application to handle reconnection. Segments using long-lived connections should be excluded from Lattice, while it can be a good fit for legacy/acquired environments with overlapping CIDRs.

</details>

---

5. Which statement correctly describes Route 53 Profiles' DNS priority rule?
   - A) The local VPC rule always wins over the Profile
   - B) The Profile rule always wins over the local VPC
   - C) Local VPC wins when names match, but if the Profile has a more specific name registered, the Profile wins
   - D) Priority is determined randomly

<details>
<summary>Show Answer</summary>

**Answer: C) Local VPC wins when names match, but if the Profile has a more specific name registered, the Profile wins**

**Explanation:**
For example, if the local VPC has an `example.com` rule and the Profile has a more specific `test.example.com` rule, the Profile applies. This is why it's recommended to formalize that "the central Profile never owns a name more specific than the namespace delegated to a workload."

</details>
