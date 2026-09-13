# Enterprise Cloud Governance Overview Quiz

> This quiz tests your understanding of [Enterprise Cloud Governance Overview](../../governance/00-governance-overview.md).

---

1. What is the core idea behind judging Account, VPC, and EKS boundaries "independently"?
   - A) Always create all three boundaries together, based on team name
   - B) Decide each boundary independently, based on different criteria (security/quota/ownership, network/trust zone, runtime blast radius)
   - C) Use a single shared Account, VPC, and cluster for every workload
   - D) Only decide the VPC boundary and let the rest follow automatically

<details>
<summary>Show Answer</summary>

**Answer: B) Decide each boundary independently, based on different criteria (security/quota/ownership, network/trust zone, runtime blast radius)**

**Explanation:**
Account is judged by security/quota/cost ownership/lifecycle, VPC by network policy and trust zone, and EKS by runtime blast radius. The fixed formula that creates all three boundaries together per domain × environment combination is simpler, but treats fundamentally different boundaries as one.

</details>

---

2. Where must the primary IAM role of a Pod Identity association reside?
   - A) Any Account
   - B) The same Account as the cluster
   - C) Only the management Account
   - D) One Account per Region

<details>
<summary>Show Answer</summary>

**Answer: B) The same Account as the cluster**

**Explanation:**
The primary association role must be in the cluster Account. The target-role feature uses role chaining, while supported resource policies and IRSA provide other cross-account paths.

</details>

---

3. Why distinguish a stable Workload ID from mutable metadata?
   - A) To reduce AWS API call costs
   - B) So that recurring changes like reorgs and brand consolidations don't directly translate into infrastructure migrations
   - C) To simplify Kubernetes RBAC configuration
   - D) To consolidate all workloads into a single Account

<details>
<summary>Show Answer</summary>

**Answer: B) So that recurring changes like reorgs and brand consolidations don't directly translate into infrastructure migrations**

**Explanation:**
Teams change frequently with reorgs, while domains (business capabilities) are relatively stable. Tying Account or VPC boundaries directly to team/brand names turns every reorg into a migration, so it's recommended to attach domain, brand, team, CUJ, etc. as mutable metadata on a stable Workload ID.

</details>
