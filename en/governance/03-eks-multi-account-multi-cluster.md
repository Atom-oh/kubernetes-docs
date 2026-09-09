# Multi-Account, Multi-Cluster EKS Architecture

> **Last Updated**: September 9, 2026

## 1. Cluster Consolidation Approaches

There are four broad ways to place workloads from multiple teams/domains onto EKS.

| Approach | Configuration |
|---|---|
| Single core EKS | All workloads on one cluster |
| Central EKS per environment | One cluster per production/non-production |
| EKS per domain | A dedicated cluster per domain |
| **Shared + Dedicated** | General workloads on a shared cluster; only workloads with strong tenant/quota/SLO requirements get a dedicated cluster |

Shared + Dedicated is a realistic starting point for most organizations. The real challenge is defining "when do we split off a dedicated cluster" as a measurable signal, rather than a gut call.

| Signal | How to measure | Split threshold |
|---|---|---|
| Managed node group count | EKS API | 25 / 30 |
| Access entry count | EKS API | 2,000 / 3,000 |
| Control plane API throttling | CloudWatch, 429 logs | Sustained 429s |
| etcd size / object count | `apiserver_storage_size_bytes` | Approaching AWS's recommended limits |
| NAU (Network Address Usage) per VPC | VPC console / CloudWatch | 50,000 / 64,000 (or 200,000 / 256,000) |
| Upgrade blast radius | Number of CUJs deployed on the cluster | Consider splitting if 2+ CUJs |
| Add-on release cadence conflicts | Divergence in per-team add-on version requirements | Split when conflicting requirements emerge |

The goal isn't to split once you're near these thresholds — it's to **automate the split decision itself** using these thresholds as triggers.

## 2. A/B EKS Runtime: Splitting the Blast Radius Across Two Clusters

Deploying the same CUJ (critical user journey) to two independent EKS clusters, so that a failure on one cluster still leaves the other serving traffic, is commonly called an "A/B EKS Runtime." This is **not an official AWS-recommended pattern — it's a working hypothesis the organization must validate itself.** To actually improve availability, you need to satisfy the conditions below first.

### Define what you're protecting against, first

The EKS managed control plane is already multi-AZ, and ARC (Application Recovery Controller) zonal shift/autoshift acts **only on the data plane.** In other words, the value of A/B redundancy isn't "AZ failure protection" — it's protection against **failures the organization itself creates.**

- Failed cluster upgrades
- Add-on (CNI/CoreDNS/CSI) regressions
- Admission webhook errors
- Bad cluster-wide policy rollouts
- Control plane API throttling

Document this failure list explicitly, and use "does this failure actually get contained to one side after splitting into A/B?" as the PoC's success criterion. An abstract claim of "improved availability" can't be verified.

### CoreDNS is the most common single point of failure

Across both A/B setups and AZ redundancy, CoreDNS is the most common single point of failure. Things to check:

- Whether `replicaCount` and `topologySpreadConstraints` actually spread replicas across AZs
- Whether the CoreDNS add-on's autoscaling (`{"autoScaling":{"enabled":true}}`) or an HPA/cluster-proportional-autoscaler is applied
- QPS/latency changes when one AZ is removed

**A single ENI on an EC2 instance can send at most 1,024 packets/sec to Route 53 Resolver (not adjustable).** On high-pod-density nodes, this limit can become the actual root cause of DNS failures. Consider adopting NodeLocal DNS.

### ARC zonal shift can cause outages if you haven't pre-provisioned spare capacity

AWS's documentation explicitly warns about this. When a zonal shift happens, the following occurs automatically.

1. The entire AZ's nodes are cordoned (blocked from new scheduling)
2. Managed node group AZ rebalancing stops
3. Pods in that AZ are removed from the EndpointSlice
4. Nodes/Pods themselves are not terminated or evicted (they return immediately once the shift is lifted)
5. ALBs/NLBs registered with ARC route only to healthy AZs

**Fail-safe behavior**: if a workload's endpoints exist only in the impaired AZ, EKS keeps sending traffic to that AZ anyway. In other words, **a workload deployed to only a single AZ is not protected by zonal shift.**

Technical constraints to check as well:

- **Doesn't work on EKS Fargate.**
- Self-managed Karpenter support requires **1.12 or later.**
- EKS Auto Mode integrates with no additional configuration, automatically handling voluntary disruptions like halting node provisioning and consolidation/drift.
- Stateful workloads require separate judgment — a new Pod in a healthy AZ cannot attach to an EBS volume (PV) bound to the impaired AZ. **Regardless of AZ count, workloads using PVCs are pinned to zonal EBS.**

> **Recommended design rule**: state explicitly that "clusters targeted by ARC zonal autoshift must not host single-AZ workloads." If a single-AZ workload is mixed into the same cluster, an autoshift practice run will disrupt it.

### The pitfall in pre-provisioned capacity multiplier math

The math of "2-AZ needs roughly 2x, 3-AZ (N-1 basis) needs roughly 1.5x pre-provisioned capacity" is arithmetically correct, but easy to get wrong in three ways.

1. **Node addition lead time (scaling lag)** — the standard mitigation is Pod priority combined with over-provisioning (placeholder pods) to eliminate scheduling delay.
2. **The risk that new capacity in the healthy AZ can be constrained by other customers' demand** — this isn't speculation; AWS's documentation explicitly notes the "compute capacity constraint risk that new nodes might not be added to a healthy AZ during zonal impairment."
3. **AZ co-location of interdependent Pods** — topology spread alone isn't enough; you need pod affinity as well. Verify every hop in the CUJ's service graph exists in every AZ.

### Cross-AZ cost optimization

Approach this in the order of measure → optimize → compare residual cost.

1. Identify the top cost paths using Flow Logs and ENI/AZ mapping (CUR alone can't tell you the source/destination AZ pair).
2. Apply, in order: same-zone routing, `trafficDistribution` (field name and values changed to `PreferSameZone`/`PreferSameNode` in newer Kubernetes versions — **pin your target EKS version first, then document using that version's field names**), topology spread, ALB IP targets, NAT/endpoint zonal locality, and data locality.
3. Compare the residual cross-AZ cost after applying these.

Disabling ALB target group cross-zone load balancing can reduce cost, but with significant trade-offs — no sticky sessions, no Lambda targets, and **if any AZ in the target group has zero healthy targets, all requests landing in that AZ get 503s.** AWS recommends keeping the default (enabled) unless you can guarantee per-AZ capacity.

### Upgrade strategy is tied directly to the reason A/B exists

If the actual reason for running an A/B EKS Runtime is upgrade isolation, you need to formalize:

- The allowed version skew between A and B clusters
- A rule for always upgrading one side first
- Whether extended support is used

Without this, A/B is nothing more than "two clusters," and the redundancy loses its purpose.

### Worker AZ count and control plane subnets are separate concepts

Creating a cluster requires subnets in at least two distinct AZs, but worker nodes can be placed in just a single AZ. This means EKS itself doesn't prohibit a "single-AZ worker configuration" — judge that separately from the zonal-shift exception rule mentioned above.

## 3. Full Workload Cell — An Alternative for Stronger Isolation

If you need stronger isolation than an A/B EKS Runtime provides, you can split and replicate ingress, compute, data, and required dependencies together as a "Cell" unit, containing blast radius within the Cell. Partitioning, consistency, capacity, and operational cost grow substantially, so this is realistic **only for workloads that can support independent data partitioning and replication.**

## Next

EKS availability design can't be considered separately from the VPC structure underneath it → [Shared VPC and Connectivity](./04-shared-vpc-and-connectivity.md)

## References

- [EKS quotas](https://docs.aws.amazon.com/general/latest/gr/eks.html#limits_eks)
- [EKS subnets and Multi-AZ](https://docs.aws.amazon.com/eks/latest/best-practices/subnets.html)
- [EKS network cost optimization](https://docs.aws.amazon.com/eks/latest/best-practices/cost-opt-networking.html)
- [EKS zonal shift](https://docs.aws.amazon.com/eks/latest/userguide/zone-shift.html)
- [EKS tenant isolation](https://docs.aws.amazon.com/eks/latest/best-practices/tenant-isolation.html)
- [Static stability using Availability Zones](https://aws.amazon.com/builders-library/static-stability-using-availability-zones/)
- [Well-Architected: Multi-AZ](https://docs.aws.amazon.com/wellarchitected/latest/framework/rel_fault_isolation_multiaz_region_system.html)
- [ALB target group attributes](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/edit-target-group-attributes.html)
- [ALB target group health](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/target-group-health.html)
