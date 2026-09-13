# Shared VPC and Connectivity Quiz

> This quiz tests your understanding of [Shared VPC and Connectivity](../../governance/04-shared-vpc-and-connectivity.md).

---

1. How does TGW propagation relate to VPC route tables?
   - A) 100 TGW prefixes is a fixed Shared VPC ceiling
   - B) TGW routes are not automatically propagated; the owner adds VPC static routes targeting the TGW
   - C) All tables share one quota
   - D) CIDR quota can never be reached first

<details>
<summary>Show Answer</summary>

**Answer: B) TGW routes are not automatically propagated; the owner adds VPC static routes targeting the TGW**

**Explanation:**
TGW tables have a combined default 10,000 routes; VPC non-propagated routes default to 500. Do not confuse the VGW propagated-route 100 limit with TGW totals.

</details>

---

2. Which owner resource cannot a Shared VPC participant describe?
   - A) Subnet
   - B) Its own security group
   - C) NAT Gateway
   - D) Route table

<details>
<summary>Show Answer</summary>

**Answer: C) NAT Gateway**

**Explanation:**
Participants cannot describe owner NAT gateways. Central inventories, logs, and delegated read paths can still provide audit evidence.

</details>

---

3. How should LBC subnet discovery be designed for Shared VPC?
   - A) Assume every version succeeds
   - B) Validate controller mode, permissions, and tag visibility; consider explicit subnet IDs
   - C) Always have the owner create Ingress
   - D) Discover only through NAT gateways

<details>
<summary>Show Answer</summary>

**Answer: B) Validate controller mode, permissions, and tag visibility; consider explicit subnet IDs**

**Explanation:**
Owner tags are not automatically shared. Explicit subnets are predictable, but this does not establish failure of every discovery mode.

</details>

---

4. Which statement correctly describes long-lived VPC Lattice connections?
   - A) Services and resources both have a 10-minute lifetime
   - B) Distinguish the 10-minute service lifetime from 350-second resource idle timeout; test protocol/reconnect behavior
   - C) HTTP listeners natively support every WebSocket
   - D) No path supports long-lived traffic

<details>
<summary>Show Answer</summary>

**Answer: B) Distinguish the 10-minute service lifetime from 350-second resource idle timeout; test protocol/reconnect behavior**

**Explanation:**
Resources do not have the same lifetime limit. TLS listeners or resource paths can serve WebSockets, subject to protocol and authorization requirements.

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
