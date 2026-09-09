# Account Structure and IAM Boundaries Quiz

> This quiz tests your understanding of [Account Structure and IAM Boundaries](../../governance/02-account-and-iam.md).

---

1. What non-adjustable quota becomes the real ceiling on scaling pure RBAC in IAM Identity Center?
   - A) Total permission sets: 3,500
   - B) Provisioned permission sets per Account: 500
   - C) Groups assignable to a permission set per Account: 100
   - D) Overall API throttle: 20 TPS

<details>
<summary>Show Answer</summary>

**Answer: C) Groups assignable to a permission set per Account: 100**

**Explanation:**
This quota is not adjustable, and assigning groups representing dozens of team × role combinations to an Account accessed by many teams (like a Shared Cluster Account) hits this ceiling. Because of this constraint, "RBAC + limited ABAC" must be treated as mandatory — not optional — for any Account accessed by multiple teams.

</details>

---

2. Why is it risky to split only the Account while keeping a Shared VPC for an organizational unit with real carve-out potential?
   - A) Shared VPC doesn't support multiple Accounts to begin with
   - B) RAM-based subnet sharing only works within the same Organization, so the Shared VPC relationship breaks first at the moment of carve-out
   - C) IAM Identity Center can't recognize a carved-out organization
   - D) The EKS cluster is automatically deleted

<details>
<summary>Show Answer</summary>

**Answer: B) RAM-based subnet sharing only works within the same Organization, so the Shared VPC relationship breaks first at the moment of carve-out**

**Explanation:**
RAM (Resource Access Manager) subnet sharing only works within the same Organization. If carve-out is a real possibility, a structure that keeps a Shared VPC while only splitting the Account can't handle that, and a dedicated VPC is effectively mandatory.

</details>

---

3. In a Workload Account + Shared Cluster Account pattern, what structure is mandatory for cross-account resource access?
   - A) Direct access to every Account through a single role
   - B) A two-hop structure: association role → target role (AssumeRole)
   - C) An IAM user access key issued per workload
   - D) Direct mapping via the aws-auth ConfigMap

<details>
<summary>Show Answer</summary>

**Answer: B) A two-hop structure: association role → target role (AssumeRole)**

**Explanation:**
Because an EKS Pod Identity role can only exist in the same Account as the cluster, accessing another Account's resources in the Shared Cluster Account pattern always requires the association role to assume a target role. This is mandatory structure, not an optimization.

</details>

---

4. What should you watch out for when combining an Access Policy with Kubernetes RBAC (group mapping) on an EKS Access Entry?
   - A) Only whichever was attached most recently applies
   - B) Permissions from both paths are combined, and neither can restrict the other
   - C) The two methods can't be used together at all
   - D) RBAC always overrides the Access Policy

<details>
<summary>Show Answer</summary>

**Answer: B) Permissions from both paths are combined, and neither can restrict the other**

**Explanation:**
Combining an Access Policy and RBAC merges their permissions. This makes it mandatory to designate a single primary grant path per principal and automatically detect duplicate grants between the two paths — without automating it, permission creep will inevitably accumulate over time.

</details>
