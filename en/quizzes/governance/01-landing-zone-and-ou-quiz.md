# Landing Zone, OUs, and Organizational Control Quiz

> This quiz tests your understanding of [Landing Zone, OUs, and Organizational Control](../../governance/01-landing-zone-and-ou.md).

---

1. What is the prerequisite for activating `IdentityCenterBaseline` in Control Tower Landing Zone 4.0?
   - A) No baseline is required — it can be activated independently
   - B) `CentralSecurityRolesBaseline` must already be active, which in turn requires `CentralConfigBaseline`
   - C) `BackupCentralVaultBaseline` must already be active
   - D) The Security OU must be manually created first

<details>
<summary>Show Answer</summary>

**Answer: B) `CentralSecurityRolesBaseline` must already be active, which in turn requires `CentralConfigBaseline`**

**Explanation:**
Landing Zone 4.0's baseline activation dependency chain is `CentralConfigBaseline` → `CentralSecurityRolesBaseline` → `IdentityCenterBaseline`/`BackupAdminBaseline`/`BackupCentralVaultBaseline`. This means whether Config is enabled directly determines whether the Identity Center baseline is usable, so the two can't be treated as independent decisions.

</details>

---

2. Which statement correctly describes the Security OU in Control Tower Landing Zone 4.0?
   - A) Administrators can freely designate a Security OU, just like in 3.x
   - B) The OU containing the service integration Accounts is automatically designated as the Security OU
   - C) The Security OU has been fully deprecated as of 4.0
   - D) Every Account belongs to the Security OU by default

<details>
<summary>Show Answer</summary>

**Answer: B) The OU containing the service integration Accounts is automatically designated as the Security OU**

**Explanation:**
In 4.0, administrators no longer manually designate a Security OU — it's automatically assigned to the OU holding the service integration Accounts. This causes derived constraints, such as AWSControlTowerBaseline and the Config Baseline not being applicable to that OU, and general Accounts placed there not receiving baseline resources.

</details>

---

3. Why is the "Layered bundle" SCP attachment strategy favorable from a quota perspective?
   - A) Because SCP document size limits are larger
   - B) Because inherited policies don't consume the per-entity attachment limit (10)
   - C) Because it shares the same quota as RCP
   - D) Because Root has no limit on the number of SCPs

<details>
<summary>Show Answer</summary>

**Answer: B) Because inherited policies don't consume the per-entity attachment limit (10)**

**Explanation:**
The Layered bundle strategy keeps a minimal, exception-free SCP at Root and inherits per-OU policy bundles down the tree, actively leveraging inheritance to conserve the direct-attach limit per OU. In contrast, fully-specified per-OU direct attachment doesn't use inheritance, so a single OU can consume the entire 10-attachment limit on its own.

</details>

---

4. Why does RCP (Resource Control Policy) need to be treated differently from SCP?
   - A) RCP has a larger document size than SCP
   - B) RCP allows more total org-wide attachments than SCP
   - C) RCP only has 4 usable slots and its document size is half that of SCP, leaving no room for a layered-bundle-style strategy
   - D) RCP is a policy that grants permissions to a principal

<details>
<summary>Show Answer</summary>

**Answer: C) RCP only has 4 usable slots and its document size is half that of SCP, leaving no room for a layered-bundle-style strategy**

**Explanation:**
RCP allows at most 5 attachments per entity (including RCPFullAWSAccess, 4 usable) and a document size of 5,120 characters, half of SCP's. Because of this, RCP is recommended to be reserved for a small number of absolute organization-wide rules, like blocking external principal access or confused-deputy defense, leaving fine-grained control to SCPs and resource policies.

</details>
