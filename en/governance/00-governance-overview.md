# Enterprise Cloud Governance Overview

> **Last Updated**: September 13, 2026

## 1. The Problem This Section Addresses

The EKS, networking, and security documents so far assumed "one cluster, one VPC" and explained individual features on top of that. But in a large enterprise organization running dozens of teams and hundreds of engineers across multiple brands, domains, and services, the questions change.

- How many Accounts should we create?
- Should VPCs be shared or split?
- Should EKS clusters be dedicated per team, or shared?
- Do these three boundaries (Account/VPC/EKS) and the data boundary need to line up 1:1?

This section covers standardization decisions for large multi-account, multi-EKS environments. Service constraints are checked against linked AWS documentation; hybrid designs, split criteria, and PoC thresholds are proposals for organizational validation. It does not establish a particular company’s private review findings or production success.

## 2. Why Account, VPC, EKS, and Data Boundaries Should Be Considered Separately

The most common mistake is creating Accounts per team or brand, and automatically attaching a dedicated VPC and dedicated EKS cluster to each Account — a **fixed 1:1 formula**. The rule is simple, but even a small workload ends up carrying the fixed cost of an entire cluster, and every organizational reshuffle turns into an infrastructure migration.

The alternative this section proposes is **judging each boundary independently**.

| Boundary | Judging criteria |
|---|---|
| Account | Security requirements, service quotas, cost/ownership, lifecycle |
| VPC | Network policy, trust zone, connectivity requirements |
| EKS | Runtime blast radius, tenant isolation requirements, SLO |
| Data | Data ownership, regulatory boundary, backup/recovery responsibility |

This makes fine-grained judgments possible, such as "this workload doesn't need its own VPC, but regulatory requirements mean it needs a dedicated Account." There's a cost, too — you now have to maintain judging criteria per boundary, and exceptions can multiply.

<span id="_3-four-conditions-where-aws-forces-boundaries-together"></span>

## 3. Service Constraints to Check When Connecting Boundaries

Independent decisions must still account for service placement and authorization constraints. These constraints do not automatically imply one mandatory organizational structure.

1. **An EKS cluster’s configured subnets must belong to one VPC.** Two independent clusters can use the same VPC. Separate VPCs are an additional decision about shared routing, DNS, and address-space failure domains.
2. **The primary IAM role in a Pod Identity association must be in the cluster Account.** The target-role feature uses association role → target role chaining. Alternatives include direct resource-policy access for services such as S3 and direct IRSA federation to a target-account role. Two roles are not mandatory for every cross-account request.
3. **In a Shared VPC, design EKS cluster/node IAM roles and associated SGs around the participant Account creating the cluster.** This may differ from the Workload Account owning a database or queue. Sharing a subnet does not transfer resource ownership.
4. **Data boundaries differ by service.** RDS instances use VPC subnets; S3 buckets are not placed in subnets. The Shared VPC support list explicitly allows for omissions, so absence alone does not establish lack of support ([Data and Security Boundaries](./05-data-security-boundaries.md)).

## 4. Shared-First vs. Dedicated-First

Once you've decided to judge boundaries independently, the next question is: for workloads with no reason to separate, do you default to shared resources or dedicated ones?

- **Shared-first**: Small workloads are accepted into shared Accounts/VPCs/clusters first. Faster to provision, less duplicated infrastructure, but risk of noisy-neighbor problems and ownerless shared resources accumulating over time.
- **Dedicated-first**: When separation is ambiguous, dedicated boundaries are evaluated first. Cost, ownership, and blast radius become clear, but fixed costs grow quickly.

In practice, a **hybrid that starts shared-first and switches to dedicated once regulatory, independent-quota, or strong-SLO requirements are confirmed** is a reasonable starting point. To avoid re-litigating this judgment call every time, [Decision Framework and PoC Design](./06-decision-framework-and-poc.md) later in this section covers how to build a reproducible decision matrix.

## 5. A Stable Workload ID and Mutable Metadata

Organizational reshuffles, brand consolidations, and team renames will keep happening. If Account or VPC boundaries are tied directly to team or brand names, every reorg becomes an infrastructure migration.

The recommended approach is to keep one **stable Workload ID**, and manage domain, brand, team, CUJ (critical user journey), environment, data class, and SLO as **mutable metadata** attached to that ID. Teams change with reorgs, but domains (business capabilities) are relatively stable, making domain a better basis for Account boundaries than team.

## 6. What's in This Section

| Document | Covers |
|---|---|
| [Landing Zone, OUs, and Organizational Control](./01-landing-zone-and-ou.md) | Control Tower's baseline dependency chain, OU design, SCP/RCP/Tag Policy roles |
| [Account Structure and IAM Boundaries](./02-account-and-iam.md) | Account partitioning, human/workload IAM, Kubernetes API access |
| [Multi-Account, Multi-Cluster EKS Architecture](./03-eks-multi-account-multi-cluster.md) | Shared/dedicated clusters, the real conditions for A/B EKS Runtime redundancy |
| [Shared VPC and Connectivity](./04-shared-vpc-and-connectivity.md) | The real quota bottleneck chain for Shared VPC, combining TGW/PrivateLink/Lattice |
| [Data and Security Boundaries](./05-data-security-boundaries.md) | Cross-account backup/restore constraints, isolating the PII data tier |
| [Decision Framework and PoC Design](./06-decision-framework-and-poc.md) | Building a decision matrix, easily-missed decision factors, PoC measurement metrics |

Each document prioritizes verified facts — "AWS services actually behave this way under this condition" — over opinion, and clearly marks the parts that still require organizational judgment.

## References

- [EKS networking requirements](https://docs.aws.amazon.com/eks/latest/userguide/network-reqs.html)
- [EKS multi-account resource-policy patterns](https://docs.aws.amazon.com/eks/latest/best-practices/subnets.html)
