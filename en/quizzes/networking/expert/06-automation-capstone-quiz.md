# Automation and Final Assessment Quiz

[Workbook](../../../networking/expert/06-automation-capstone.md)

1. What can happen when expected values are changed in the same update merely to match observations?

   - A) TCP always gets faster
   - B) Regressions or policy violations can be concealed
   - C) Original evidence is no longer needed
   - D) Validation always becomes stricter

<details>
<summary>Show Answer</summary>

**Answer: B**

**Explanation:** Review intent separately and record its revision/hash. Arbitrarily adjusting expectation and observation together makes validation self-confirming.

</details>

2. What does the time BGP returns to Established establish?

   - A) Service convergence completed at exactly that time
   - B) Every VRF is isolated
   - C) Control-plane state; forwarding and service recovery need separate measurement
   - D) Every packet was delivered without loss

<details>
<summary>Show Answer</summary>

**Answer: C**

**Explanation:** Advertisement, selection, FIB and probe recovery times can differ. Align observation points and time axes.

</details>

3. Only a timeout was collected for a forbidden flow. How should it be normalized?

   - A) Keep it unknown without policy-denial evidence
   - B) Always mark deny
   - C) Always mark allow
   - D) Delete the flow record

<details>
<summary>Show Answer</summary>

**Answer: A**

**Explanation:** Routing, listener or return-path failure can cause a timeout. Policy evidence must be correlated with the probe to establish denial.

</details>

4. The synthetic example prints CONSISTENT_RECORD. What was checked?

   - A) Real-device forwarding success
   - B) Production rollout approval
   - C) Authenticity of original PCAPs
   - D) Agreement of supplied intent and required record conditions

<details>
<summary>Show Answer</summary>

**Answer: D**

**Explanation:** The checker validates consistency. A synthetic label or artifact name does not attest to actual traffic or collection.

</details>

5. Only 203.0.113.0/24 is approved for advertisement, but observations also contain 0.0.0.0/0. What should happen?

   - A) Pass because more routes are better
   - B) Reject the unexpected advertisement
   - C) Automatically add it to intent
   - D) Always ignore default routes

<details>
<summary>Show Answer</summary>

**Answer: B**

**Explanation:** This contract compares the exact set advertised to one peer. Unexpected advertisements must not be hidden.

</details>

6. An artifact reference string exists. What remains to be verified?

   - A) Nothing
   - B) The original can be deleted
   - C) Existence, hash, time, collector, vantage point and actual contents
   - D) Expand every account permission

<details>
<summary>Show Answer</summary>

**Answer: C**

**Explanation:** A reference and trustworthy evidence are different things. The example does not independently inspect originals.

</details>

7. Can FRR peer advertisements and the whole Linux FIB be compared as the same prefix list?

   - A) Their scopes differ and need separate normalization and intent
   - B) They are always identical
   - C) Equal counts are enough
   - D) ECMP always has one path

<details>
<summary>Show Answer</summary>

**Answer: A**

**Explanation:** Control-plane advertisements and forwarding state are different datasets. Validate attributes or multipath information lost in set conversion separately.

</details>

8. What must be checked after recovery?

   - A) Only that the process is alive
   - B) One positive flow is enough
   - C) Only the aggregate score
   - D) Allowed flows, isolation and management access against the original criteria

<details>
<summary>Show Answer</summary>

**Answer: D**

**Explanation:** Restoration is not complete merely because a configuration was copied. Recheck both required and forbidden behavior using the same observations.

</details>
