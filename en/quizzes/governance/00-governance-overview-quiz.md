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

2. What constraint applies to the location of an EKS Pod Identity role?
   - A) It can be placed freely in a different Account from the cluster
   - B) It can only exist in the same Account as the cluster
   - C) It's automatically replicated to every Account in the Organization
   - D) Only one can exist per Region

<details>
<summary>Show Answer</summary>

**Answer: B) It can only exist in the same Account as the cluster**

**Explanation:**
An EKS Pod Identity role can only exist in the same Account as the cluster. If Kubernetes workloads run in a separate Shared Cluster Account while resources live in each workload's own Account, cross-account access is mandatory two-hop structure: association role → target role.

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
