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

2. How do ALB weighted forwarding and fail-open relate?
   - A) An unhealthy group always fails over to another
   - B) Automatic inter-group failover and unhealthy routing inside a group are distinct
   - C) Weights guarantee RTO
   - D) Targets replicate across Regions

<details>
<summary>Show Answer</summary>

**Answer: B) Automatic inter-group failover and unhealthy routing inside a group are distinct**

**Explanation:**
Weighted forwarding does not automatically transfer an empty/unhealthy group’s weight to another group. Evaluate the selected group’s DNS/routing health thresholds separately.

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
The decision matrix dry-run has two people independently apply the matrix to 10–15 representative workloads, using local example targets of disagreement under 20% and exceptions under 15%. The resulting estimated Account/VPC/cluster counts determine the measurement targets for the remaining PoCs.

</details>

---

4. Which statement correctly describes unused-Region controls?
   - A) Every default Region can be disabled
   - B) Combine SCPs, detection, supported opt-in disabling, and existing-resource cost checks
   - C) GuardDuty alone blocks APIs
   - D) Disabling a Region deletes all resources

<details>
<summary>Show Answer</summary>

**Answer: B) Combine SCPs, detection, supported opt-in disabling, and existing-resource cost checks**

**Explanation:**
Regions enabled by default cannot be disabled. Opt-in disabling does not delete existing resources or ensure charges stop, so plan cleanup and access controls together.

</details>
