# Decision Framework and PoC Design Quiz

> This quiz tests your understanding of [Decision Framework and PoC Design](../../governance/06-decision-framework-and-poc.md).

---

1. What does this document identify as "the biggest gap" among decision factors?
   - A) Tag naming conventions
   - B) CUJ-level RTO/RPO targets
   - C) The EKS version number
   - D) VPC CIDR size

<details>
<summary>Show Answer</summary>

**Answer: B) CUJ-level RTO/RPO targets**

**Explanation:**
Without RTO/RPO targets defined per CUJ, you can't judge whether an A/B EKS Runtime failover is fast enough, which data ownership model is actually recoverable, or whether AZ configuration differences matter. This target should be defined before anything else.

</details>

---

2. Which statement correctly describes ALB weighted target group's "fail-open" behavior?
   - A) Traffic is never sent to unhealthy targets
   - B) If there aren't enough healthy targets, traffic is sent to all registered targets, including unhealthy ones
   - C) The entire target group immediately becomes unavailable
   - D) It automatically fails over to another Region

<details>
<summary>Show Answer</summary>

**Answer: B) If there aren't enough healthy targets, traffic is sent to all registered targets, including unhealthy ones**

**Explanation:**
The claim that "it won't automatically fail over to unhealthy targets" is only half true — ALB's fail-open behavior kicks in when healthy targets run short, and this must be mitigated with `minimum_healthy_targets` settings. The default of "1 healthy target is enough" can be dangerous for large target groups.

</details>

---

3. Why is "decision matrix dry-run" run as PoC-0, before all other PoCs?
   - A) Because it's the cheapest option
   - B) Because every other option — independent boundary judgment, Hybrid configurations, etc. — sets "reproducible via a decision matrix" as its condition for validity, so no PoC result converts into a standard without one
   - C) Because it requires AWS SA approval
   - D) Because it's unrelated to the other PoCs

<details>
<summary>Show Answer</summary>

**Answer: B) Because every other option — independent boundary judgment, Hybrid configurations, etc. — sets "reproducible via a decision matrix" as its condition for validity, so no PoC result converts into a standard without one**

**Explanation:**
The decision matrix dry-run has two people independently apply the matrix to 10–15 representative workloads, targeting a disagreement rate under 20% and an exception rate under 15%. The resulting estimated Account/VPC/cluster counts determine the measurement targets for the remaining PoCs.

</details>

---

4. What's the strongest control for managing unused Regions?
   - A) SCP `aws:RequestedRegion` Deny
   - B) Enabling Security Hub CSPM
   - C) Disabling Region opt-in
   - D) Enabling GuardDuty

<details>
<summary>Show Answer</summary>

**Answer: C) Disabling Region opt-in**

**Explanation:**
SCP Deny is a preventive control, and Security Hub CSPM/GuardDuty are detective controls (they only process findings in Regions where enabled and don't retroactively collect), but disabling Region opt-in is the strongest available control.

</details>
