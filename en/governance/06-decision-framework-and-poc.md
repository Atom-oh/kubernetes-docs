# Decision Framework and PoC Design

> **Last Updated**: September 13, 2026

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

<span id="alb-weighted-target-group-s-fail-open-behavior"></span>

### Separate weighted forwarding from target-group fail-open

A weighted forward action does not automatically fail over to another target group because a weighted group is empty or unhealthy. **Fail-open within the selected group** is separate: below its healthy-target threshold, a load-balancer node may route to accessible unhealthy targets. Review DNS and routing failover through these attributes:

- `target_group_health.unhealthy_state_routing.minimum_healthy_targets.count` (or `.percentage`)
- `target_group_health.dns_failover.minimum_healthy_targets.count` (or `.percentage`)

Unified configuration applies the same threshold to both actions. DNS failover thresholds must be at least routing-failover thresholds; either count or percentage can trigger an action when both are set. Percentages use registered-target counts, not proven CUJ throughput or N-1 SLO capacity. Gate weight changes on actual load, error rate, and latency as well.

### Controlling unused Regions

Separate from your single-Region decision, you still need to address:

- **Prevention**: SCP `aws:RequestedRegion` Deny (with an exception list for global services)
- **Detection**: Review CloudTrail, GuardDuty, and Security Hub CSPM coverage in allowed/usable Regions. Disabling one product does not make all activity undetectable.
- **Opt-in Regions**: Unused opt-in Regions can be disabled; Regions enabled by default cannot. Disabling a Region does not delete existing resources or stop their charges. Combine cleanup, SCPs, and detection.

### Cost observability and when tag enforcement happens

Validate cross-AZ attribution by joining Flow Logs, ENI/IP mappings, Kubernetes workload identity, and CUR billing categories. Not every ENI supports user tags or RequestTag conditions at creation. Apply tag policies, IaC, and supported SCP conditions according to service-specific coverage.

## 2. Designing the Decision Matrix

The options covered across these documents — independent boundary judgment, Hybrid Account portfolios, Shared+Dedicated EKS, mixed trust-zone VPCs, Hybrid data, Hybrid key ownership — all set **"reproducible via a decision matrix"** as their condition for validity. Without a decision matrix, no PoC result can be converted into a standard.

Recommended columns for the decision matrix:

| Column | Purpose |
|---|---|
| Does this need EKS? | Determines whether the EKS boundary is subordinate to the VPC boundary |
| Cross-account resource access | Choose target-role chaining, resource policy, or IRSA as appropriate |
| Does this use a service unsupported in shared subnets? | Determines exclusion from the Shared VPC locality strategy |
| Groups per permission-set/Account pair | Check the actual 100 limit and growth;50 is an optional local warning |
| Primary responder / escalation path | A boundary with more than one primary responder is a split candidate |
| CUJ RTO/RPO | The basis for judgments across data and availability design |

## 3. PoC Design Patterns

Some items can't be finalized on paper and require real measurement. The PoCs below are listed in priority order.

### PoC-0: Decision matrix dry-run (run before all other PoCs)

- **Inputs**: 10–15 representative workloads (including CUJs, at least one PII workload, at least one common domain workload, at least two small internal tools, at least one external partner integration)
- **Procedure**: Have two people independently apply the decision matrix and compare results
- **Example success criteria**: Disagreement under 20%, exceptions under 15%; tune these local hypotheses
- **By-product**: The judged results yield estimated counts of Accounts/VPCs/clusters, which determine the quota measurement targets for the rest of the PoCs

### PoC-1: Shared Cluster + Workload Account

| Measurement | Success criteria |
|---|---|
| Pod Identity/resource-policy/IRSA permission paths | Validate source/target reuse, scope, revocation, KMS, and resource policy; no fixed 2-role formula |
| ALB Controller subnet auto-discovery on a shared subnet | Whether tag-based auto-discovery fails → if so, standardize on explicit annotation |
| Access entry growth rate | (Increase per added workload) × target workload count < 3,000 |
| Managed node group count | Headroom against default 30 and applied quota; distinguish placement from security isolation |
| Primary-response time between Cluster Account and Workload Account | Time to determine "CNI issue vs. application issue" |
| Detection/blocking time for overly broad participant SG Allow rules | Detection-to-block time via Firewall Manager audit policy |

### PoC-2: A/B EKS Runtime and AZ configuration (prerequisite: CUJ-level RTO/RPO defined)

| Measurement | Success criteria |
|---|---|
| Inject 3+ failures from the list in [Chapter 3](./03-eks-multi-account-multi-cluster.md) | Confirm each failure is actually contained to one cluster |
| ARC zonal autoshift practice run | Confirm each of A/B clusters can independently handle N-1 AZ peak load |
| CoreDNS N-1 throughput/latency | Latency increase rate, whether the 1,024 packet/s per ENI limit is reached |
| CUJ service graph AZ coverage | Validate dependency reachability, capacity, and fallback from surviving AZs |
| Stateful recovery | Validate EBS AZ constraints, alternative storage/replication, recovery time, and data loss |
| A→B failover end-to-end time | Measure edge failover and Route 53 record change separately |
| Rollback time | Measured separately from failover time |
| Cross-AZ bytes | Based on Flow Logs, before/after optimization comparison |
| Pre-provisioned capacity multiplier | Compare measured values against the 2x/1.5x hypothesis |

### PoC-3: Minimal Shared VPC / Shared VPC Pool

| Measurement | Success criteria |
|---|---|
| **TGW/VPC routes(current/3-year projection)** | Separate TGW table total 10,000 from VPC non-propagated 500/adjustable 1,000; distinguish VGW 100 |
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

For each execution path, define controls appropriate to its risk: machine-readable intent, a pre-execution snapshot, a plan, deterministic policy checks, approval, a scoped temporary identity, a post-check, CloudTrail logging, actual state reconciliation, and a recovery contract.

> **AWS MCP Server scope**: The current endpoint table lists us-east-1 and eu-central-1. Endpoint location differs from the Region of a managed resource. API execution uses IAM and downstream permissions, with CloudTrail records available for review. Assess endpoint, authentication, logging, and data paths against organizational requirements; absence of a Seoul endpoint alone does not establish a regulatory violation.

## Related documents

- [Enterprise Cloud Governance Overview](./00-governance-overview.md)
- [Landing Zone, OUs, and Organizational Control](./01-landing-zone-and-ou.md)
- [Account Structure and IAM Boundaries](./02-account-and-iam.md)
- [Multi-Account, Multi-Cluster EKS Architecture](./03-eks-multi-account-multi-cluster.md)
- [Shared VPC and Connectivity](./04-shared-vpc-and-connectivity.md)
- [Data and Security Boundaries](./05-data-security-boundaries.md)

## References

- [ALB target group attributes](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/edit-target-group-attributes.html)
- [ALB target group health](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/load-balancer-target-groups.html#target-group-health)
- [ALB rule action types (weighted)](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/rule-action-types.html)
- [Route 53 weighted routing](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/routing-policy-weighted.html)
- [Route 53 failover routing](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/routing-policy-failover.html)
- [AWS MCP Server](https://docs.aws.amazon.com/agent-toolkit/latest/userguide/mcp-server.html)
- [AWS MCP Server IAM](https://docs.aws.amazon.com/agent-toolkit/latest/userguide/security_iam_service-with-iam.html)
- [AWS MCP regional endpoints](https://docs.aws.amazon.com/general/latest/gr/aws-mcp.html)
- [Charges in disabled Regions](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/checklistforunwantedcharges.html)
