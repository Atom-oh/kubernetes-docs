# Data and Security Boundaries Quiz

> This quiz tests your understanding of [Data and Security Boundaries](../../governance/05-data-security-boundaries.md).

---

1. How does the Multi-AZ DB cluster snapshot-sharing constraint differ from the other cross-account constraints?
   - A) It only differs in cost
   - B) It's the only constraint that actually forces a choice between centralized and workload-owned data
   - C) It only occurs in the Seoul Region
   - D) It only occurs if you don't use AWS Backup

<details>
<summary>Show Answer</summary>

**Answer: B) It's the only constraint that actually forces a choice between centralized and workload-owned data**

**Explanation:**
Multi-AZ DB cluster snapshots can't be shared, meaning there's no cross-account recovery path at all — making workload-owned data effectively mandatory in that case. The other cross-account backup constraints are common guardrails that apply equally to either ownership model.

</details>

---

2. What element must be included in RTO calculations but is commonly overlooked?
   - A) IAM policy simulation time
   - B) The time it takes to copy a snapshot into a manual snapshot
   - C) VPC route table update time
   - D) Security Hub finding generation time

<details>
<summary>Show Answer</summary>

**Answer: B) The time it takes to copy a snapshot into a manual snapshot**

**Explanation:**
RDS automated backups can't be shared, so moving them cross-account requires copying into a manual snapshot first. This copy time is non-trivial for a terabyte-scale database and must be included in the RTO calculation.

</details>

---

3. What risk must a security team confirm when cross-account backup is enabled?
   - A) Backup costs double
   - B) Any member Account user in the org can set their own Account as a destination, creating a risk that PII backups get copied to unauthorized Accounts
   - C) Backups aren't automatically encrypted
   - D) The backup vault automatically becomes public

<details>
<summary>Show Answer</summary>

**Answer: B) Any member Account user in the org can set their own Account as a destination, creating a risk that PII backups get copied to unauthorized Accounts**

**Explanation:**
To prevent this, enforce `backup:CopyTargets`/`backup:CopyTargetOrgPaths` conditions on `backup:CopyFromBackupVault` to require approved vaults/OUs. The backup copy path exists as a separate channel even if IAM, KMS, resource policies, and VPC endpoint policies are all locked down.

</details>

---

4. What does the fact that "Security Hub CSPM requires AWS Config for most controls" imply?
   - A) All control findings are generated normally regardless of Config
   - B) Whether Config is enabled becomes the common prerequisite for three decisions: Landing Zone, Identity Center, and Security Hub CSPM
   - C) Config is completely unrelated to Security Hub CSPM
   - D) It can replace GuardDuty

<details>
<summary>Show Answer</summary>

**Answer: B) Whether Config is enabled becomes the common prerequisite for three decisions: Landing Zone, Identity Center, and Security Hub CSPM**

**Explanation:**
If Config is disabled, most Security Hub CSPM control findings won't be generated. Combined with the Landing Zone baseline dependency chain, whether Config is enabled ends up constraining three important decisions at once.

</details>
