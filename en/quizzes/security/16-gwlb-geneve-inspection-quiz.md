# GWLB and GENEVE Quiz

> **Last Updated**: October 15, 2026

[Read the chapter and primary sources](../../security/16-gwlb-geneve-inspection.md)

### 1. What does AWS document when all eligible GWLB targets are unhealthy?

- A) Deliver to unhealthy targets rather than directly bypassing appliances
- B) Route directly to the original destination
- C) Encrypt every packet
- D) Guarantee application availability

<details>
<summary>Show Answer</summary>

**Answer: A) Deliver to unhealthy targets rather than directly bypassing appliances**

**Explanation:** GWLB does not bypass appliances. AWS describes random per-flow target selection and drops until the selected target recovers. A health-only fault still forwarding is a PoC hypothesis; check each AZ's eligible targets and cross-zone setting.

</details>

### 2. What happens to a new flow when no targets remain registered?

- A) Direct bypass
- B) Traffic drops
- C) A new target is automatically created
- D) WAF handles the IP flow instead

<details>
<summary>Show Answer</summary>

**Answer: B) Traffic drops**

**Explanation:** New flows have no target; verify drops and recovery. Distinguish all-unhealthy and test existing flows separately under their failover/drain settings.

</details>

### 3. What happens to existing flows under no_rebalance?

- A) They always migrate with complete session state
- B) They are guaranteed to succeed
- C) They remain assigned, potentially blackholing at an unhealthy target
- D) They bypass inspection

<details>
<summary>Show Answer</summary>

**Answer: C) They remain assigned, potentially blackholing at an unhealthy target**

**Explanation:** Rebalance may redistribute but does not recreate independent appliance state. Both failover attributes must have the same value.

</details>

### 4. What does TGW appliance mode establish?

- A) Automatic IPS
- B) Automatic cross-firewall state replication
- C) Inspection of every VPC-local packet
- D) Consistent inspection-attachment AZ selection for both directions

<details>
<summary>Show Answer</summary>

**Answer: D) Consistent inspection-attachment AZ selection for both directions**

**Explanation:** Symmetric per-flow attachment/AZ selection differs from GWLB target stickiness and vendor session sharing. Appliance mode replaces TGW's default origin-AZ preference.

</details>

### 5. Can reduced two/three-tuple stickiness be combined with TGW appliance mode?

- A) No, according to the documented constraint
- B) Always
- C) Only because UDP 6081 is open
- D) Only if every target is unhealthy

<details>
<summary>Show Answer</summary>

**Answer: A) No, according to the documented constraint**

**Explanation:** Current AWS documentation requires five-tuple with TGW appliance mode. Review reduced-tuple load concentration and supported combinations.

</details>

### 6. Which security-group statement is correct?

- A) GWLB and GWLBE each require ALB-style SGs
- B) Neither supports those SG attachments; inspect appliance/workload ENIs, NACLs and routes
- C) Appliance SGs are irrelevant
- D) NACLs are stateful

<details>
<summary>Show Answer</summary>

**Answer: B) Neither supports those SG attachments; inspect appliance/workload ENIs, NACLs and routes**

**Explanation:** Do not invent a GWLB SG configuration. Health and outer GENEVE traffic still require actual path controls.

</details>

### 7. Why must the NAT subnet's return route be reviewed?

- A) Only DNS needs it
- B) It automatically follows the outbound route
- C) Responses after reverse translation must return through inspection consistently
- D) NAT automatically replicates firewall state

<details>
<summary>Show Answer</summary>

**Answer: C) Responses after reverse translation must return through inspection consistently**

**Explanation:** Outbound inspection alone is insufficient. Record tuples before/after translation and prevent loops.

</details>

### 8. Does GWLB solve every MTU issue with fragmentation/PMTUD?

- A) Yes, for every jumbo packet
- B) Yes, if health is green
- C) Yes, if target license is valid
- D) No; account for encapsulation and every segment's MTU

<details>
<summary>Show Answer</summary>

**Answer: D) No; account for encapsulation and every segment's MTU**

**Explanation:** AWS documents 8500-byte maximum packets and 68-byte overhead, without GWLB fragmentation/PMTUD. Test actual packet/protocol paths.

</details>
