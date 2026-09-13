# Observability Lab 01 Quiz

<span id="observability-lab-part-1-infrastructure-setup-quiz"></span>

> **Last Updated**: September 13, 2026

1. How should reviewed EKS version status be used?
   - A) 1.31 is necessarily already unsupported.
   - B) Use the reviewed1.36 standard-support baseline and recheck current Region/support status.
   - C) Minor versions are supported forever.
   - D) kubectl version skew never matters.

<details>
<summary>Show answer</summary>

**Answer: B) Use the reviewed1.36 standard-support baseline and recheck current Region/support status.**

Distinguish extended support from end of support and verify client/server compatibility.

</details>

---

2. What must be checked when reusing a VPC?
   - A) Only the VPC ID string.
   - B) Subnet AZs, address capacity, routes, DNS/SGs and nonoverlapping service CIDRs.
   - C) Make both service CIDRs identical.
   - D) NAT/endpoints are never needed.

<details>
<summary>Show answer</summary>

**Answer: B) Subnet AZs, address capacity, routes, DNS/SGs and nonoverlapping service CIDRs.**

The generator creates no network resources, so real connectivity prerequisites remain.

</details>

---

3. How should the public API client CIDR be configured?
   - A) Always0.0.0.0/0.
   - B) A narrow approved range matching the actual source.
   - C) Use an arbitrary documentation IP in production.
   - D) CIDR alone replaces authentication.

<details>
<summary>Show answer</summary>

**Answer: B) A narrow approved range matching the actual source.**

Verify private/public endpoints, source addresses and authentication together.

</details>

---

4. What are essential IRSA trust constraints?
   - A) Allow every ServiceAccount.
   - B) Correct OIDC provider and exact audience/namespace/ServiceAccount subject.
   - C) Put all permissions on the node role.
   - D) Hard-code an access key in the Pod.

<details>
<summary>Show answer</summary>

**Answer: B) Correct OIDC provider and exact audience/namespace/ServiceAccount subject.**

The provider ARN and issuer host/path must identify the same provider.

</details>

---

5. What is the Aurora access boundary?
   - A) A public writer open to the internet.
   - B) Private subnets and PostgreSQL5432 access from the actual service-client SG.
   - C) Similar SG names are enough.
   - D) A multi-AZ writer appears automatically.

<details>
<summary>Show answer</summary>

**Answer: B) Private subnets and PostgreSQL5432 access from the actual service-client SG.**

A single writer is a lab choice, not an HA guarantee.

</details>

---

6. Which DB account should the application use?
   - A) The master account in every Pod.
   - B) A separate runtime account with DML access to lab tables.
   - C) A public connection without a password.
   - D) Overwrite the existing password on every run.

<details>
<summary>Show answer</summary>

**Answer: B) A separate runtime account with DML access to lab tables.**

Bootstrap does not overwrite roles; verify candidate credentials after failure.

</details>

---

7. How should passwords containing special characters be supplied?
   - A) Concatenate directly into a DSN.
   - B) Pass the raw JSON value as URL.create’s password argument.
   - C) URL-encode repeatedly.
   - D) Print to logs for copying.

<details>
<summary>Show answer</summary>

**Answer: B) Pass the raw JSON value as URL.create’s password argument.**

Also verify TLS verify-full and the actual CA path.

</details>

---

8. What should follow a failed cluster creation?
   - A) Keep creating new names.
   - B) Inspect partial resources, state and ownership under the same name.
   - C) Assume no charge after a failure.
   - D) Delete every VPC.

<details>
<summary>Show answer</summary>

**Answer: B) Inspect partial resources, state and ownership under the same name.**

CLI failure does not prove no resources were created.

</details>

---

9. What does checking gp3 StorageClass involve?
   - A) A matching name always works.
   - B) Check EBS CSI, permissions, the actual class and volume cleanup.
   - C) Always overwrite the shared class.
   - D) PVC and snapshot deletion are identical.

<details>
<summary>Show answer</summary>

**Answer: B) Check EBS CSI, permissions, the actual class and volume cleanup.**

Distinguish shared-object changes from resource deletion responsibilities.

</details>

---

10. How should lab costs be estimated?
   - A) Always2.5USDperhour.
   - B) Include real Region, usage, retention, NAT/LBs/storage/snapshots.
   - C) Treat monthly AMG user pricing as an hourly workspace rate.
   - D) A NodePool limit is an absolute budget.

<details>
<summary>Show answer</summary>

**Answer: B) Include real Region, usage, retention, NAT/LBs/storage/snapshots.**

Do not claim fixed totals or unmeasured savings.

</details>

---

[Return to the guide](../../../labs/observability/01-infrastructure-setup-lab.md)
