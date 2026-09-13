# Data and Security Boundaries Quiz

> This quiz tests your understanding of [Data and Security Boundaries](../../governance/05-data-security-boundaries.md).

---

1. What follows from the inability to share a Multi-AZ DB cluster snapshot?
   - A) Every recovery path is impossible
   - B) That RDS sharing path is unavailable; validate engine-specific recovery alternatives
   - C) Workload-owned databases are mandatory
   - D) Every AWS Backup vault behaves identically

<details>
<summary>Show Answer</summary>

**Answer: B) That RDS sharing path is unavailable; validate engine-specific recovery alternatives**

**Explanation:**
One API restriction does not rule out every logical-backup or replication alternative. Validate support and RTO/RPO before choosing ownership.

</details>

---

2. What belongs in RTO for a recovery path requiring a post-incident copy?
   - A) Only tag naming
   - B) Copy, restore, and application validation time
   - C) Only historical retention
   - D) Only Security Hub score

<details>
<summary>Show Answer</summary>

**Answer: B) Copy, restore, and application validation time**

**Explanation:**
With pre-existing copies, copy cadence affects RPO. Distinguish shared air-gapped-vault restore paths that do not need a recipient copy.

</details>

---

3. Which authorization statement is correct after enabling cross-account backup?
   - A) Every user bypasses IAM denies
   - B) Review IAM, vault, KMS, copy-destination conditions, and RAM sharing together
   - C) Vaults become public
   - D) Copied backups are deleted on organizational exit

<details>
<summary>Show Answer</summary>

**Answer: B) Review IAM, vault, KMS, copy-destination conditions, and RAM sharing together**

**Explanation:**
Enabling a feature does not grant permission. Standard-vault copy and air-gapped-vault sharing are distinct paths; test approved destinations and source unavailability.

</details>

---

4. What does Security Hub CSPM’s Config dependency mean?
   - A) All controls work without Config
   - B) Most CSPM controls need recording; this is not an Identity Center service dependency
   - C) It replaces GuardDuty
   - D) Every AWS MCP request needs Config

<details>
<summary>Show Answer</summary>

**Answer: B) Most CSPM controls need recording; this is not an Identity Center service dependency**

**Explanation:**
Distinguish Control Tower-managed baseline dependencies from Identity Center service requirements. Check Security Hub capability scope and Region coverage.

</details>
