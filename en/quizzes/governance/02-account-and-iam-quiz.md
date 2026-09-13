# Account Structure and IAM Boundaries Quiz

> This quiz tests your understanding of [Account Structure and IAM Boundaries](../../governance/02-account-and-iam.md).

---

1. What is the scope of Identity Center’s 100-group limit?
   - A) All groups in the Organization
   - B) All groups in an Account
   - C) Groups assigned to one permission set in one Account, or one application
   - D) Concurrent signed-in users

<details>
<summary>Show Answer</summary>

**Answer: C) Groups assigned to one permission set in one Account, or one application**

**Explanation:**
It applies per permission-set/Account combination, not the Account-wide sum across permission sets. It does not universally mandate ABAC.

</details>

---

2. What matters when planning a carve-out of an Account using Shared VPC?
   - A) All resources are deleted immediately
   - B) Plan migration for the same-Organization requirement and creation/replacement limits after unsharing
   - C) RAM subnets remain shared with external organizations
   - D) EKS automatically moves VPCs

<details>
<summary>Show Answer</summary>

**Answer: B) Plan migration for the same-Organization requirement and creation/replacement limits after unsharing**

**Explanation:**
Existing resources can continue after unsharing, while new creation and managed-service scaling/replacement may be affected. Prepare an independently operable path before leaving.

</details>

---

3. How can a Shared Cluster access another Account’s AWS resources?
   - A) Always issue IAM-user keys
   - B) Choose target-role chaining, supported resource policies, or IRSA as appropriate
   - C) Create exactly two roles for every workload
   - D) Editing aws-auth grants AWS permissions

<details>
<summary>Show Answer</summary>

**Answer: B) Choose target-role chaining, supported resource policies, or IRSA as appropriate**

**Explanation:**
The same-Account requirement for the primary Pod Identity role does not mandate a target role for every request. Distinguish the Cluster Account from the Account owning only a database.

</details>

---

4. What happens when Access Policies and Kubernetes RBAC are combined?
   - A) Only the latest applies
   - B) Allows combine and neither restricts the other
   - C) They cannot be combined
   - D) RBAC always overrides

<details>
<summary>Show Answer</summary>

**Answer: B) Allows combine and neither restricts the other**

**Explanation:**
Review intentional grants and overlaps. Automation helps, but is not an API prerequisite.

</details>
