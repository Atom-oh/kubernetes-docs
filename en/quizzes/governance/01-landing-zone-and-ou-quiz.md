# Landing Zone, OUs, and Organizational Control Quiz

> This quiz tests your understanding of [Landing Zone, OUs, and Organizational Control](../../governance/01-landing-zone-and-ou.md).

---

1. What precedes IdentityCenterBaseline activation in Control Tower 4.0?
   - A) No baseline
   - B) CentralSecurityRolesBaseline and its prerequisite CentralConfigBaseline
   - C) BackupCentralVaultBaseline
   - D) Identity Center itself requires Config in every environment

<details>
<summary>Show Answer</summary>

**Answer: B) CentralSecurityRolesBaseline and its prerequisite CentralConfigBaseline**

**Explanation:**
This is a dependency of the Control Tower-managed baseline, not a universal Config prerequisite for the Identity Center service.

</details>

---

2. Which statement describes the Control Tower 4.0 Security OU?
   - A) Every OU is a Security OU
   - B) The OU containing service-integration Accounts is designated the Security OU
   - C) Security OUs were removed
   - D) Every general Account there receives all baselines

<details>
<summary>Show Answer</summary>

**Answer: B) The OU containing service-integration Accounts is designated the Security OU**

**Explanation:**
Integration Accounts share a parent OU and are managed through the landing zone. AWSControlTowerBaseline/ConfigBaseline do not apply to that Security OU. Separate placement of general operations Accounts is a design choice.

</details>

---

3. Why can layered SCP bundles conserve direct-attachment quota?
   - A) Document limits disappear
   - B) Inherited policies do not consume the child’s direct attachments
   - C) Child allows override parent denies
   - D) Root has unlimited quota

<details>
<summary>Show Answer</summary>

**Answer: B) Inherited policies do not consume the child’s direct attachments**

**Explanation:**
The direct-attachment limit is 10 SCPs per entity. Inheritance does not consume these slots, but effective constraints from parent policies still apply.

</details>

---

4. Which statement correctly describes RCP attachments and inheritance?
   - A) They grant permissions directly
   - B) They cannot be inherited
   - C) RCPFullAWSAccess uses one of five slots; design the remaining direct slots and inheritance together
   - D) Their size limit equals SCPs

<details>
<summary>Show Answer</summary>

**Answer: C) RCPFullAWSAccess uses one of five slots; design the remaining direct slots and inheritance together**

**Explanation:**
Four direct slots remain and documents allow 5,120 characters. This budget does not prohibit layered inheritance. Check supported resources and principal exceptions.

</details>
