# Unified Studio Domain and Project Governance Quiz

## Multiple Choice Questions

1. Which statement correctly describes a project profile?

   - A) It only chooses GPU drivers
   - B) It combines blueprints and configures creation-time or on-demand tools
   - C) All capabilities guarantees immediate readiness of every tool
   - D) It replaces every IAM permission

<details>
<summary>Show Answer</summary>

**Answer: B**

Verify the intended profile ID, domain type and required blueprints/accounts/regions.

</details>

2. Do IAM DeleteProject permission and ordinary contributor membership guarantee deletion?

   - A) Always
   - B) No; verify the deletion path's owner/admin authority and other IAM/service policies
   - C) Yes, if the EKS namespace matches
   - D) Yes, if the project name is unique

<details>
<summary>Show Answer</summary>

**Answer: B**

Project ownership, API authorization and actual data/resource permissions are separate boundaries.

</details>

3. How should projectStatus=ACTIVE be interpreted?

   - A) Every environment and GPU tool is ready
   - B) It is the project state; check required environmentDeploymentDetails and tool access separately
   - C) All on-demand capabilities are already provisioned
   - D) Training succeeded

<details>
<summary>Show Answer</summary>

**Answer: B**

Distinguish intentionally unprovisioned on-demand tools from actual failures.

</details>

4. What belongs in a CreateProject membershipAssignments member?

   - A) Always both userIdentifier and groupIdentifier
   - B) Exactly one userIdentifier or groupIdentifier matching the intended profile
   - C) An IAM secret access key
   - D) Any IAM role ARN in place of a group profile ID

<details>
<summary>Show Answer</summary>

**Answer: B**

It is a tagged union. Same-request assignments do not promise atomic rollback of all environment provisioning; verify results.

</details>

5. How should remaining-project deletion be verified?

   - A) Treat AccessDenied as absence
   - B) Check authorized get/list scope, domain, filters/pagination and owned-resource inventory
   - C) An early-September record proves current state
   - D) Delete all shared buckets/roles with the same prefix after a tag failure

<details>
<summary>Show Answer</summary>

**Answer: B**

Historical records do not replace current verification. Cleanup must follow run ownership and retention policy.

</details>

---

[Return to Learning Materials](../../../data-on-eks/sagemaker-unified-studio/01-domains-projects-governance.md)
