# Enterprise Cloud Governance Overview

> **Last Updated**: September 9, 2026

## 1. The Problem This Section Addresses

The EKS, networking, and security documents so far assumed "one cluster, one VPC" and explained individual features on top of that. But in a large enterprise organization running dozens of teams and hundreds of engineers across multiple brands, domains, and services, the questions change.

- How many Accounts should we create?
- Should VPCs be shared or split?
- Should EKS clusters be dedicated per team, or shared?
- Do these three boundaries (Account/VPC/EKS) and the data boundary need to line up 1:1?

This section is based on an architecture standardization review that a large e-commerce organization actually running multi-account, multi-EKS infrastructure conducted with an AWS Solutions Architect. It contains no account IDs, costs, or organizational details of any specific company. It is generalized into principles based purely on **quotas, API behavior, and service constraints verified against official AWS documentation**. In other words, this isn't "this company did it this way" — it's a fact-based guide to "AWS services actually behave this way under these conditions."

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

## 3. Four Conditions Where AWS Forces Boundaries Together

Even with an independent-judgment principle in place, AWS service behavior itself forces certain boundaries to merge. These aren't optional — they're constraints that need to be locked in early in the design.

1. **An EKS cluster cannot span multiple VPCs.** If you want to split two clusters into separate failure domains (e.g., A/B cluster redundancy), those two clusters automatically end up in separate VPCs. The EKS boundary is always a subset of the VPC boundary.
2. **An EKS Pod Identity role can only exist in the same Account as the cluster.** If you want to run Kubernetes workloads in a separate "shared cluster Account" while resources (Lambda, SQS, RDS, etc.) live in each workload's own Account, cross-account access is always a two-hop structure: association role → target role. This isn't an optimization — it's mandatory structure.
3. **Even in a Shared VPC, EKS security groups and IAM roles must live in the participant Account.** Sharing the VPC doesn't change the fact that SG/IAM boundaries follow the Account boundary.
4. **Data boundaries split by service.** Some services are placed directly inside a VPC (RDS, etc.), while others have no VPC concept at all (S3, etc.). AWS explicitly maintains the list of services that can create resources in a Shared VPC subnet (see [Chapter 5](./05-data-security-boundaries.md)), and any workload using a service outside that list must be treated as an exception to the Shared VPC strategy.

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
