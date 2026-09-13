# Account Structure and IAM Boundaries

> **Last Updated**: September 13, 2026

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

> **Carve-out planning**: Subnet sharing is supported within one Organization. Prepare an independent network migration before leaving. Existing resources may continue after unsharing, but new creation and managed-service replacement/scaling can be affected. Unsharing does not immediately delete or stop every resource.

## 2. Account and EKS Runtime Relationship

Once Account partitioning is decided, you need to decide which Account's EKS cluster runs your Kubernetes workloads.

| Option | Configuration | Pros | Cons |
|---|---|---|---|
| Dedicated EKS per Workload Account | Each Workload Account owns its own EKS cluster | Account and runtime ownership/blast radius align | Even small workloads need a cluster, increasing the number of clusters to manage and idle capacity |
| **Workload Account + Shared Cluster Account** | Resources like Lambda/SQS/DB live in each Workload Account, while Kubernetes workloads run on shared EKS in a separate Cluster Account | Account boundaries and the number of EKS clusters to manage can be decided independently | Cross-account identity, networking, and cluster ownership become more complex |

In the second pattern, distinguish cluster-account IAM roles from access to another Account’s data. With Shared VPC, the participant creating EKS is the **Cluster Account**, which may differ from the Workload Account owning only a database or queue. Select Pod Identity target-role chaining, service resource policies, or IRSA as appropriate.

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

Thirty managed node groups is an adjustable default, not a fixed 30-tenant ceiling. Karpenter NodePools and taints/tolerations control placement and are not strong security boundaries by themselves. Assess applied quotas, permissions, shared kernels, and node-agent privileges together.

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
| Managed policies per permission set | 25; the separate IAM-role default of 10 must be increased as needed | Permission-set limit: no |
| Inline policy per permission set | 32,768 bytes; 10,240 non-whitespace bytes | No |
| **Groups assigned to one permission set in one Account** | **100** | **No** |
| Configurable Accounts | 7,000 | Yes |
| Identity Center API throttle | Collective 20 TPS; read increases via support | Check additional API-specific limits |

The 100-group limit applies to a **specific permission-set/Account combination**, not all groups in an Account. Do not add groups across different permission sets and treat 100 as the Account-wide RBAC ceiling.

> **Design proposal**: Measure assignments per permission set and policy duplication before comparing RBAC simplification, ABAC, and Account separation. A warning at 50 is an optional local threshold, not an AWS requirement or mandatory ABAC trigger.

## 4. Workload (Application/Automation) Access to AWS

The items below aren't mutually exclusive options — they're patterns you combine depending on the execution environment and whether cross-account access is needed.

| Method | Configuration | Suits |
|---|---|---|
| Runtime role | Attach an IAM role to an execution environment (EC2/Lambda/ECS, etc.) | Non-EKS workloads |
| **EKS Pod Identity** | Link a Pod to an IAM role via a Pod Identity association | Supported EKS workloads (recommended direction) |
| IRSA | Kubernetes service account tokens + an IAM OIDC provider | Existing clusters/toolchains requiring compatibility |
| **Cross-account target role** | Source role assumes a target-account role | Paths that need to execute with target-role permissions |

Allow static access keys only as an exception for legacy integrations that don't support roles or federation, with explicit purpose, owner, expiration, and rotation documented.

The primary Pod Identity association role is in the cluster Account. Setting targetRoleArn chains two roles, while supported resource policies can instead authorize that source role directly. IRSA can also federate directly to a target-account OIDC provider/role. Role reuse and session tag/policy design determine role counts; “exactly two per workload” is not universal. Workload roles for AWS APIs are counted separately from Access Entries for Kubernetes API access.

## 5. Kubernetes API Access

| Method | Configuration | Status |
|---|---|---|
| **EKS Access Entries** | Manage cluster access per IAM principal via Access Entries, using either an Access Policy or a Kubernetes group mapping for RBAC | Recommended direction |
| aws-auth ConfigMap | Manage IAM principal-to-Kubernetes identity mapping via the cluster's `aws-auth` ConfigMap | Keep only as an exception during legacy cluster migration |

**Permission union**: Access Policies and Kubernetes RBAC grants combine; neither restricts the other. Record each principal’s primary path and intentional additional grants, and review overlaps. Automated checks are useful implementation choices, not prerequisites for using the API.

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
- [EKS shared subnet requirements](https://docs.aws.amazon.com/eks/latest/userguide/network-reqs.html)
- [Unsharing subnets](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-sharing-share-subnet-working-with.html)
- [EKS resource-policy patterns](https://docs.aws.amazon.com/eks/latest/best-practices/subnets.html)
