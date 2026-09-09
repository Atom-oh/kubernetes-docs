# Decision Framework and PoC Design

> **Last Updated**: September 9, 2026

The Landing Zone, Account/IAM, EKS, VPC, and Data/Security boundaries covered so far should each be judged independently — but in practice, they all need to be reproducible from a single decision matrix. This document covers how to design that matrix, and how to validate the parts that require real measurement through PoCs.

## 1. Easily-Missed Decision Factors

No matter how carefully you design boundaries, Accounts, and network structure, you can't judge whether that design is actually correct without the following.

### CUJ-level RTO/RPO targets — the biggest gap

Without RTO (Recovery Time Objective)/RPO (Recovery Point Objective) targets defined per CUJ (critical user journey), you simply can't judge:

- Whether an A/B EKS Runtime failover is fast enough (the sum of DNS TTL + edge propagation + Route 53 propagation + health-detection delay)
- Which data ownership model — centralized or workload-owned — is actually recoverable (whether snapshot copy time counts against RTO)
- Whether the difference between 2-AZ and 3-AZ matters (whether SLOs hold in an N-1 state)
- Whether the added cost of cell-level isolation is justified

**Define a table of CUJ-level RTO/RPO/acceptable-error-rate targets before anything else.**

### On-call ownership during incidents

Even with security, quota, cost, lifecycle, and blast radius all factored into boundary decisions, missing "who responds first" means losing time during a 2am incident on a Shared Cluster where it's unclear whether the issue is CNI or the application. Add "primary responder" and "escalation path" columns to your decision matrix, and adopt the rule that **a boundary with more than one primary responder is a candidate for splitting.**

### Target Kubernetes version and upgrade strategy

The `trafficDistribution` field values, Karpenter's ARC zonal shift integration (1.12+), whether EKS Auto Mode is adopted (who owns node lifecycle), and the add-on compatibility matrix all depend on the EKS version. If the reason for running A/B EKS Runtime is upgrade isolation, you must formalize the allowed version skew, the rule for always upgrading one side first, and whether extended support is used.

### ALB weighted target group's fail-open behavior

The claim that "it won't automatically fail over to unhealthy targets" is only half true — in reality, **if there aren't enough healthy targets, ALB sends traffic to all registered targets, including unhealthy ones (fail-open).** There are two mitigation settings:

- `target_group_health.unhealthy_state_routing.minimum_healthy_targets.count` (or `.percentage`)
- `target_group_health.dns_failover.minimum_healthy_targets.count` (or `.percentage`)

AWS recommends "Unified configuration" — setting the same threshold on both. The default is "1 healthy target is enough to be considered healthy," which means a large target group can be judged healthy with only one member alive. We recommend gating traffic weight increases not on target health itself, but on whether **`minimum_healthy_targets.percentage`** (based on the CUJ's N-1 capacity) passes.

### Controlling unused Regions

Separate from your single-Region decision, you still need to address:

- **Prevention**: SCP `aws:RequestedRegion` Deny (with an exception list for global services)
- **Detection**: Security Hub CSPM and GuardDuty only process findings in Regions where they're enabled and don't retroactively collect — if you don't disable an unused Region, its activity simply isn't detected.
- **The strongest control**: disabling Region opt-in

### Cost observability and when tag enforcement happens

Attributing cross-AZ cost to a workload pair requires tags down to the ENI level, and they must be **enforced at resource creation time.** Tag Policy checks and enforces compliance, but doesn't cover every resource type. We recommend a triple structure: IaC template enforcement + SCP `aws:RequestTag` conditions + Tag Policy checks. Also account for the fact that owner tags aren't visible to participants in a Shared VPC ([Chapter 4](./04-shared-vpc-and-connectivity.md)) when designing cost attribution.

## 2. Designing the Decision Matrix

The options covered across these documents — independent boundary judgment, Hybrid Account portfolios, Shared+Dedicated EKS, mixed trust-zone VPCs, Hybrid data, Hybrid key ownership — all set **"reproducible via a decision matrix"** as their condition for validity. Without a decision matrix, no PoC result can be converted into a standard.

Recommended columns for the decision matrix:

| Column | Purpose |
|---|---|
| Does this need EKS? | Determines whether the EKS boundary is subordinate to the VPC boundary |
| Does this need cross-account resource access? | Determines whether the Pod Identity two-hop structure is needed |
| Does this use a service unsupported in shared subnets? | Determines exclusion from the Shared VPC locality strategy |
| Estimated number of groups accessing this Account | ABAC adoption / Account split threshold (50-group benchmark) |
| Primary responder / escalation path | A boundary with more than one primary responder is a split candidate |
| CUJ RTO/RPO | The basis for judgments across data and availability design |

## 3. PoC Design Patterns

Some items can't be finalized on paper and require real measurement. The PoCs below are listed in priority order.

### PoC-0: Decision matrix dry-run (run before all other PoCs)

- **Inputs**: 10–15 representative workloads (including CUJs, at least one PII workload, at least one common domain workload, at least two small internal tools, at least one external partner integration)
- **Procedure**: Have two people independently apply the decision matrix and compare results
- **Success criteria**: Disagreement rate under 20%, exception rate under 15%
- **By-product**: The judged results yield estimated counts of Accounts/VPCs/clusters, which determine the quota measurement targets for the rest of the PoCs

### PoC-1: Shared Cluster + Workload Account

| Measurement | Success criteria |
|---|---|
| Number of permission paths in the Pod Identity two-hop structure (association → target role) | Confirm 2 roles + 2 trust policies per workload, scaling linearly with workload count |
| ALB Controller subnet auto-discovery on a shared subnet | Whether tag-based auto-discovery fails → if so, standardize on explicit annotation |
| Access entry growth rate | (Increase per added workload) × target workload count < 3,000 |
| Managed node group count | Headroom against the 30-group limit when applying a tenant isolation strategy |
| Primary-response time between Cluster Account and Workload Account | Time to determine "CNI issue vs. application issue" |
| Detection/blocking time for overly broad participant SG Allow rules | Detection-to-block time via Firewall Manager audit policy |

### PoC-2: A/B EKS Runtime and AZ configuration (prerequisite: CUJ-level RTO/RPO defined)

| Measurement | Success criteria |
|---|---|
| Inject 3+ failures from the list in [Chapter 3](./03-eks-multi-account-multi-cluster.md) | Confirm each failure is actually contained to one cluster |
| ARC zonal autoshift practice run | Confirm each of A/B clusters can independently handle N-1 AZ peak load |
| CoreDNS N-1 throughput/latency | Latency increase rate, whether the 1,024 packet/s per ENI limit is reached |
| CUJ service graph AZ coverage | Every hop exists in every AZ (including pod affinity) |
| Stateful workload PV rebinding | Whether the Pod actually comes up in the healthy AZ |
| A→B failover end-to-end time | Measure edge failover and Route 53 record change separately |
| Rollback time | Measured separately from failover time |
| Cross-AZ bytes | Based on Flow Logs, before/after optimization comparison |
| Pre-provisioned capacity multiplier | Compare measured values against the 2x/1.5x hypothesis |

### PoC-3: Minimal Shared VPC / Shared VPC Pool

| Measurement | Success criteria |
|---|---|
| **Number of propagated TGW prefixes (current / projected in 3 years)** | Whether under 100; if exceeded, whether default-route fallback is viable |
| Participant Account growth rate | Against the 100 limit, for target team count |
| Shared subnets per Account | AZ × trust zone × purpose combinations vs. 100 |
| NAU usage | Reflecting Pod density, when the 64,000 → 256,000 adjustment becomes necessary |
| Time from route/DNS change request to owner fulfillment | Quantify the bottleneck |
| Flow log evidence completeness | Whether owner + participant logs together can reconstruct the full flow |
| Detection/recovery time for a bad central route change, in both minimal and dedicated configurations | Measure both options (this is the real deciding factor) |
| TGW attachment throughput | Headroom against 100 Gbps/7.5M PPS per AZ |

## 4. Relationship to AI-Driven Operations

This framework isn't limited to topology choices like Account/VPC/EKS — it can be extended into an operating principle applied to every ADR (Architecture Decision Record). Execution paths for automating infrastructure changes generally fall into:

- **IaC-only**: Changes only through human-authored, human-reviewed IaC. Highest reproducibility, but slow for urgent/exploratory work.
- **AI-assisted IaC**: An agent generates IaC change proposals, executed through the existing review → plan → apply process. Reduces authoring cost, but carries the risk of large generated diffs and drift from actual state.
- **Policy/Intent + Generated Plan**: An agent reads current state and generates an execution plan. Separates intent from backend, but weak intent schemas/state reconciliation lead to inconsistent results.
- **Agent-direct MCP/CLI/API**: An approved agent makes changes directly, then verifies. Fastest, but carries risks of overly broad permissions, partial failures, and prompt injection.
- **Risk-tiered Hybrid**: IaC for high-risk, persistent configuration changes; limited direct agent execution for low-risk, reversible work. This is the realistic direction for most organizations.

Whichever execution path you choose, at minimum it should satisfy: machine-readable intent, a pre-execution snapshot, a plan, deterministic policy checks, approval, a scoped temporary identity, a post-check, CloudTrail logging, actual state reconciliation, and a recovery contract.

> **Confirmed facts about AWS MCP Server**: AWS API calls are authorized using existing IAM credentials plus downstream service permissions, and are logged to CloudTrail. MCP condition context keys let you distinguish this access path. However, as of this writing, AWS MCP Server's service endpoint only exists in US East and Frankfurt — **the fact that it's absent from the Seoul Region is itself a decision factor.** You need to work with your security team to judge (a) whether this counts as a data-movement concern from a regulatory standpoint, and (b) whether relying on recovery tooling hosted in another Region during a Regional outage is a benefit or a risk.

## Related documents

- [Enterprise Cloud Governance Overview](./00-governance-overview.md)
- [Landing Zone, OUs, and Organizational Control](./01-landing-zone-and-ou.md)
- [Account Structure and IAM Boundaries](./02-account-and-iam.md)
- [Multi-Account, Multi-Cluster EKS Architecture](./03-eks-multi-account-multi-cluster.md)
- [Shared VPC and Connectivity](./04-shared-vpc-and-connectivity.md)
- [Data and Security Boundaries](./05-data-security-boundaries.md)

## References

- [ALB target group attributes](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/edit-target-group-attributes.html)
- [ALB target group health](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/target-group-health.html)
- [ALB rule action types (weighted)](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/rule-action-types.html)
- [Route 53 weighted routing](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/routing-policy-weighted.html)
- [Route 53 failover routing](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/routing-policy-failover.html)
- [AWS MCP Server](https://docs.aws.amazon.com/agent-toolkit/latest/userguide/mcp-server.html)
- [AWS MCP Server IAM](https://docs.aws.amazon.com/agent-toolkit/latest/userguide/security_iam_service-with-iam.html)
