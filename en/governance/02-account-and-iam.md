# Account Structure and IAM Boundaries

> **Last Updated**: September 9, 2026

## 1. Account Partitioning: What Should the Basis Be?

The most common candidates for how to split Accounts are team, brand, domain, and environment (production/non-production). But **an Account should be judged by the security requirements, service quotas, cost/ownership, and lifecycle that related workloads share — not by the team's name.** Teams change frequently through reorgs, while domains (business capabilities) are relatively stable Account candidates.

| Option | Configuration | Pros | Cons |
|---|---|---|---|
| Domain × Environment | A separate Production/Non-production Account per domain | Easy to tie cost, quota, permissions, and ownership to a domain | Even small domains carry fixed costs, and domain reorganization directly becomes a migration |
| Brand × Environment | Accounts per brand and environment, with multiple domains inside each | Manage brand-level cost, quota, permissions, separation, and transfers via Account boundaries | Ownership of shared features used across brands becomes ambiguous. Brand lifecycle changes directly trigger Account reorganization |
| Small number of central Workload Accounts | Workloads from multiple domains/teams placed together in a few shared Accounts | Simple initial operations, easy to onboard small workloads | Quota, permissions, and blast radius grow, and it becomes hard to split later |
| **Hybrid portfolio** | Small workloads go into shared Accounts; workloads with strong domain/regulatory/quota boundaries get dedicated Accounts | Combine shared, domain, and dedicated Accounts based on requirements | Weak judging criteria lead to a rapid increase in exceptions |

In practice, starting with a Hybrid portfolio and deciding shared vs. dedicated with a reproducible decision matrix each time is the common pattern (see [Decision Framework](./06-decision-framework-and-poc.md) for how to design that matrix).

Treat brand as metadata if only cost separation is needed, and promote it to an Account axis only when there's a strong boundary — regulatory, independent quota, permissions, or carve-out potential. A workload that aggregates data across domains and serves it via API can be a candidate for its own Workload Account if it has independent SLO, quota, data access, and lifecycle. **A separate Account doesn't necessarily mean a separate EKS cluster.**

> **A must-check item if carve-out is a real possibility**: RAM (Resource Access Manager)-based subnet sharing only works **within the same Organization**. If a particular organizational unit might realistically be carved out (spun off), a structure that keeps a Shared VPC while only splitting the Account can't handle that — the Shared VPC relationship breaks first at the moment of carve-out. In this case a dedicated VPC is effectively mandatory.

## 2. Account and EKS Runtime Relationship

Once Account partitioning is decided, you need to decide which Account's EKS cluster runs your Kubernetes workloads.

| Option | Configuration | Pros | Cons |
|---|---|---|---|
| Dedicated EKS per Workload Account | Each Workload Account owns its own EKS cluster | Account and runtime ownership/blast radius align | Even small workloads need a cluster, increasing the number of clusters to manage and idle capacity |
| **Workload Account + Shared Cluster Account** | Resources like Lambda/SQS/DB live in each Workload Account, while Kubernetes workloads run on shared EKS in a separate Cluster Account | Account boundaries and the number of EKS clusters to manage can be decided independently | Cross-account identity, networking, and cluster ownership become more complex |

No AWS constraint blocks the second pattern, but as explained in the [overview](./00-governance-overview.md), the constraint that **an EKS Pod Identity role can only exist in the same Account as the cluster means cross-account resource access is mandatory default structure for every workload, not an option.** The Shared Cluster's security groups and IAM roles always live in the participant Account (the workload's own Account holding the resources).

### EKS-related quotas — where there's headroom, and where you'll actually hit a wall

| Quota | Default | Adjustable |
|---|---|---|
| Clusters / Region | 100 | Yes |
| Managed node groups / cluster | 30 | Yes |
| Nodes / node group | 450 | Yes |
| Control plane security groups / cluster | 4 | No |
| CIDRs allowed to access the public endpoint / cluster | 40 | No |
| **Access entries / cluster** | **3,000** | **No** |

Most EKS quotas have headroom, but the **3,000 access-entries-per-cluster limit (not adjustable)** is a real ceiling you'll approach quickly if you issue individual CI/CD roles per workload × environment across dozens of teams. We recommend consolidating access paths into Permission Sets or team-level roles, and grouping access entries by principal type.

**30 managed node groups** may in practice be hit even sooner than access entries. A per-tenant node group isolation strategy hits its ceiling at 30 tenants. Consider Karpenter with taints/tolerations and NodePool-based isolation as an alternative (Karpenter's [ARC zonal shift integration](./03-eks-multi-account-multi-cluster.md) requires version 1.12 or later).

## 3. Human Access to AWS (Workforce IAM)

| Option | Configuration | Pros | Cons |
|---|---|---|---|
| **Identity Center + RBAC** | Users log in via Identity Center, access Accounts via role-based Permission Sets | Temporary credentials, central revocation/audit | Permission Sets can multiply across team × domain × environment combinations |
| RBAC + limited ABAC | Further restrict resource scope with tags within RBAC's per-role permission ceiling | Combines a permission ceiling with scalability | Requires testing both RBAC and ABAC, and controlling who can issue tags |
| ABAC-centric | Grant permissions mainly when user and resource tags match | Reduces policy duplication as Accounts/workloads grow | If tag authority is weak, permission creep and debugging difficulty grow |

We recommend excluding per-Account IAM users from the general option set entirely. Reserve them only as an exception for emergency access when Identity Center is unavailable, with explicit purpose, owner, usage conditions, credential storage, periodic review, and termination conditions documented.

### The actual ceilings for IAM Identity Center

| Quota | Default | Adjustable |
|---|---|---|
| Total permission sets | 3,500 | Yes |
| Provisioned permission sets per Account | 500 | Yes |
| Managed policies per permission set | 25 (though IAM's "10 managed policies per role" is the effective ceiling) | — |
| Inline policy size per permission set | 32,768 bytes | No |
| **Groups assignable to a permission set per Account** | **100** | **No** |
| Configurable Accounts | 7,000 | — |
| Overall API throttle | 20 TPS | — |

Of these, **"100 groups assignable per Account (not adjustable)" is the actual ceiling on pure RBAC scaling.** If you assign groups representing dozens of team × role combinations to a single Account accessed by many teams (e.g., a Shared Cluster Account, a central DB Account), you'll hit that limit.

> **Recommended decision rule**: Because of this constraint, "RBAC + limited ABAC" should be treated as **mandatory (not optional) for any Account accessed by multiple teams.** Add an "estimated number of groups accessing this Account" column to your decision matrix, and use 50 (half the limit) as the threshold for triggering either ABAC adoption or Account splitting.

## 4. Workload (Application/Automation) Access to AWS

The items below aren't mutually exclusive options — they're patterns you combine depending on the execution environment and whether cross-account access is needed.

| Method | Configuration | Suits |
|---|---|---|
| Runtime role | Attach an IAM role to an execution environment (EC2/Lambda/ECS, etc.) | Non-EKS workloads |
| **EKS Pod Identity** | Link a Pod to an IAM role via a Pod Identity association | Supported EKS workloads (recommended direction) |
| IRSA | Kubernetes service account tokens + an IAM OIDC provider | Existing clusters/toolchains requiring compatibility |
| **Cross-account target role** | The source role from any of the three above assumes a target role in the resource's Account | Any case requiring cross-account resource access |

Allow static access keys only as an exception for legacy integrations that don't support roles or federation, with explicit purpose, owner, expiration, and rotation documented.

As emphasized earlier, **a Pod Identity role can only exist in the same Account as the cluster.** With a Shared Cluster Account pattern, cross-account resource access is always a two-hop structure — "association role → target role (AssumeRole)." That means each workload needs 2 roles and 2 trust policies, and this structure scales linearly with the number of workloads — plan for this alongside the access-entry quota.

## 5. Kubernetes API Access

| Method | Configuration | Status |
|---|---|---|
| **EKS Access Entries** | Manage cluster access per IAM principal via Access Entries, using either an Access Policy or a Kubernetes group mapping for RBAC | Recommended direction |
| aws-auth ConfigMap | Manage IAM principal-to-Kubernetes identity mapping via the cluster's `aws-auth` ConfigMap | Keep only as an exception during legacy cluster migration |

**Important constraint**: if you use both an Access Policy and Kubernetes RBAC (group mapping) on an Access Entry, **the permissions from both paths are combined, and neither can restrict the other.** In other words, "designate a single primary grant path per principal, and automatically detect duplicate grants between the Access Policy and RBAC paths" isn't optional — it's mandatory control. Without automating it, permission creep will inevitably accumulate over time.

## Next

Once Account and IAM boundaries are settled, the next decision is how many EKS clusters to run and how to achieve availability → [Multi-Account, Multi-Cluster EKS Architecture](./03-eks-multi-account-multi-cluster.md)

## References

- [IAM Identity Center quotas](https://docs.aws.amazon.com/singlesignon/latest/userguide/limits.html)
- [IAM Identity Center ABAC](https://docs.aws.amazon.com/singlesignon/latest/userguide/abac.html)
- [EKS Access Entries](https://docs.aws.amazon.com/eks/latest/userguide/access-entries.html)
- [EKS IAM best practices](https://docs.aws.amazon.com/eks/latest/best-practices/identity-and-access-management.html)
- [EKS Pod Identity](https://docs.aws.amazon.com/eks/latest/userguide/pod-identities.html)
- [EKS Pod Identity target role](https://docs.aws.amazon.com/eks/latest/userguide/pod-id-assign-target-role.html)
- [IAM Roles for Service Accounts (IRSA)](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html)
- [EKS multi-account strategy](https://docs.aws.amazon.com/eks/latest/best-practices/multi-account-strategy.html)
- [EKS quotas](https://docs.aws.amazon.com/general/latest/gr/eks.html#limits_eks)
