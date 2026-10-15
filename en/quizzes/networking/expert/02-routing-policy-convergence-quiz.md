# 02. Routing Policy and Measured Convergence — Quiz

> **Last Updated**: September 15, 2026

Return to the [workbook](../../../networking/expert/02-routing-policy-convergence.md).
Choose one answer per question and explain which observation would support it.
These are reasoning exercises, not claims that a lab was executed.

1. Why does the selected BGP lab also run OSPF inside AS65000?
   - A) OSPF replaces all BGP policy decisions.
   - B) OSPF supplies internal reachability, including the loopbacks used for iBGP.
   - C) OSPF distributes LOCAL_PREF to external providers.

<details>
<summary>Show Answer</summary>

**Answer: B**

**Explanation:** BGP distributes policy-bearing destination information; OSPF supplies internal routes in this design. Check the route to the actual BGP next hop as well as the OSPF adjacency. An adjacency alone does not prove the needed prefix is present.

</details>

2. An iBGP-learned prefix appears in the BGP table, but its NEXT_HOP cannot be resolved. What is the best next step?
   - A) Check the route to that next hop, next-hop policy and the kernel lookup.
   - B) Declare forwarding successful because the session is established.
   - C) Increase LOCAL_PREF until an unreachable next hop becomes reachable.

<details>
<summary>Show Answer</summary>

**Answer: A**

**Explanation:** Preference does not create reachability. Identify the actual NEXT_HOP and resolve it through the routing table to an interface/neighbor. Then compare eligibility, selected route, FIB and source-specific traffic evidence.

</details>

3. c2 learns one eligible route with LOCAL_PREF 200 through c1 and another with 100 through x2. Why might c2 prefer c1 despite an extra internal hop?
   - A) BGP always chooses the smallest IP address.
   - B) Weight 200 was automatically propagated from c1.
   - C) LOCAL_PREF expresses AS-internal policy and is considered before AS-path length in this FRR selection process.

<details>
<summary>Show Answer</summary>

**Answer: C**

**Explanation:** BGP selection is not simply an IGP hop-count calculation. LOCAL_PREF is communicated internally; weight is local to an implementation/router. Verify both paths are eligible and no earlier selection criterion or policy changes the premise.

</details>

4. What does a route reflector solve, and what must still be checked?
   - A) It creates all missing underlay routes, so clients need no IGP.
   - B) It reduces iBGP session requirements; clients still need usable next hops and forwarding evidence.
   - C) It guarantees every client sees every alternate path.

<details>
<summary>Show Answer</summary>

**Answer: B**

**Explanation:** Reflection changes advertisement rules and uses ORIGINATOR_ID/CLUSTER_LIST for loop prevention. It neither repairs next-hop reachability nor guarantees full alternative-path visibility. A reflector also need not carry the tenant data traffic.

</details>

5. Your proposed export filter permits exactly `192.168.42.0/24`. Which candidate must be rejected under that contract?
   - A) `192.168.42.0/25`, because exact prefix/length matching does not automatically include more-specifics.
   - B) Nothing; an allowlist permits all routes unless explicitly denied.
   - C) Only routes with a large MED.

<details>
<summary>Show Answer</summary>

**Answer: A**

**Explanation:** The contract permits one prefix and length. The `/25`, the provider's `192.168.100.0/24` and a default route fall outside it. Inspect actual advertisements separately: a written filter design is not an installed filter.

</details>

6. Which statement about BGP policy attributes is defensible?
   - A) An attached community always enforces its intended behavior.
   - B) MED is always compared across every neighboring AS.
   - C) Communities need interpreting policy, and MED comparison depends on receiver rules.

<details>
<summary>Show Answer</summary>

**Answer: C**

**Explanation:** Communities convey labels; receiving policy gives those labels operational meaning. MED and AS-path prepending influence selection only within the receiver's decision process. They are not unconditional instructions to another AS.

</details>

7. In this FRR/clab lab, which sequence correctly enters the routing CLI?
   - A) Run `show ip route` directly in the VM shell.
   - B) Run `netlab connect c1` from the lab directory, then `vtysh` in c1's Linux shell.
   - C) Run `ip route get` at the `c1(config-router)#` prompt.

<details>
<summary>Show Answer</summary>

**Answer: B**

**Explanation:** The connection opens the FRR container's Linux shell. `vtysh` supplies the FRR CLI; Linux `ip` and `ping` remain shell commands. The VM-side `netlab connect c1 --show ip route` is a verified alternative for a single FRR show command.

</details>

8. Before applying the workbook's policy change, c1 already has an explicit local preference of 150. What should you do?
   - A) Stop and establish the intended baseline instead of deleting an existing policy.
   - B) Assume 100 anyway because that is a common default.
   - C) Apply 200, then remove the setting and call that exact restoration.

<details>
<summary>Show Answer</summary>

**Answer: A**

**Explanation:** The supplied inverse assumes no explicit setting and effective preference 100. Removing a pre-existing 150 would not restore the original state. Known prestate is part of authorization and reproducibility, not an optional annotation.

</details>

9. Timestamped probes show no loss at 200 ms intervals during the peer shutdown. Which conclusion is justified?
   - A) Convergence was exactly zero milliseconds.
   - B) All applications and packet sizes were unaffected.
   - C) This sampling did not resolve an outage; retain route/FIB observations and report the measurement limit.

<details>
<summary>Show Answer</summary>

**Answer: C**

**Explanation:** Sampling can miss a short interruption. Administrative shutdown also differs from silent failure and timer expiry. Report the intervention, observed route/FIB changes, probe interval and sustained-recovery criterion rather than deriving a universal timer claim.

</details>

10. Which result set permits completion of the failure experiment?
   - A) BGP is established again, even though no probe output was saved.
   - B) The exact peer and policy changes are reversed, baseline routes/FIB/probes recover, and measurement limitations are recorded.
   - C) A wildcard clear and host-wide route flush made the output look normal.

<details>
<summary>Show Answer</summary>

**Answer: B**

**Explanation:** Restore c1's named peer first, then its introduced local-preference setting, and verify the original behavior. Missing telemetry is not success. Preserve the owned clone/revisions and report failures without unscoped cleanup or claiming the upstream c2=50 validator passed.

</details>

Completion: explain every answer and attach a baseline/change/failure/restoration matrix from the workbook, or label the practical work **not executed**.
