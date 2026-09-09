# Shared VPC and Connectivity

> **Last Updated**: September 9, 2026

## 1. Shared VPC Owner/Participant Permissions — A Common Misunderstanding

When adopting a Shared VPC (sharing subnets across Accounts via AWS RAM), the most common misconception is that "sharing means both sides see things equally." In reality, owner and participant permissions differ significantly, resource by resource.

| Resource | Participant permission | Owner permission |
|---|---|---|
| Subnet | Describe only | Full |
| Route table | Describe only | Full |
| NACL | Describe only (for ones the owner created) | Full |
| **NAT Gateway** | **Cannot even describe** | Full |
| Internet Gateway | Describe only (Egress-only IGW: not even describe) | Full |
| TGW attachment | Cannot create | Owner only |
| ENI | Full for their own | Describe only for others' |
| Security Group | Full for their own + can use the owner's shared ones | Describe only for others' |
| Flow Logs | Only their own ENIs | Subnet + all ENIs possible (but flow logs created by a participant can't be described or deleted even by the owner) |

Two practical implications follow from this table.

**Flow Log visibility is asymmetric in both directions.** To control internal VPC traffic via SG/NACL/route/NetworkPolicy + Flow Logs, **the owner needs to own subnet-level flow logs, and creation of individual flow logs by participants should be blocked via SCP.** Otherwise you pay for duplicated logging while still lacking a complete traffic picture in any single Account.

**VPC/subnet tags are not shared with participants.** The AWS Load Balancer Controller's subnet auto-discovery relies on the `kubernetes.io/role/elb` and `kubernetes.io/role/internal-elb` tags, but in a Shared VPC these tags belong to the owner and aren't guaranteed to be visible in the participant Account. **In a Shared VPC + EKS combination, don't rely on subnet auto-discovery — standardize on explicitly annotating subnet IDs on Ingress/Service resources instead.**

Security groups only support Allow rules, and rules from multiple SGs are merged — a broad Allow in one SG can't be offset by a more restrictive central SG. Each SG allows 60 rules (inbound/outbound × IPv4/IPv6, each), each ENI allows 5 SGs, and there's a constraint of **"rule count × SGs per ENI ≤ 1,000."** Firewall Manager's common SG policies consume this same budget.

Quotas for resources a participant creates (5,000 ENIs per AZ, 2,500 SGs per Region) are **counted against the participant's own Account.** So these two quotas aren't a bottleneck in a Shared VPC. If you're worried about a participant controlling their own SGs too loosely, that's a permissions issue, not a quota issue — detect violations with a Firewall Manager audit policy.

## 2. The Real Ceiling on Shared VPC — It's Not the CIDR

It's tempting to focus on "how many IPv4 CIDRs can we attach" when designing a Shared VPC, but in reality, **other quotas hit far sooner.** In a typical large-scale hub-and-spoke setup (central Transit Gateway + Shared VPC), the order you'll hit limits looks like this.

| Rank | Quota | Default | Adjustable | Why it hits first |
|---|---|---|---|---|
| **1** | **Propagated routes per VPC route table** | **100** | **No** | Enabling route propagation from the central TGW hub stops working the moment VPC + on-prem prefixes exceed 100 combined. **The only non-adjustable item, and the real first bottleneck** |
| 2 | Participant Accounts per VPC | 100 | Yes | Reached early with team × environment combinations |
| 3 | Subnets an Account can be shared | 100 | Yes | Grows with AZ × trust zone × purpose combinations |
| 4 | NAU per VPC | 64,000 | Up to 256,000 | EKS Pods aren't ENIs, but their IPs count toward NAU. Reached at high Pod density |
| 5 | Subnets / route tables per VPC | 200 each | Yes | |
| 6 | IPv4 CIDRs per VPC | 5 | Up to 50 | In practice, the **last** limit you'll ever hit |

In other words, you'll hit the **100 propagated routes** limit long before running out of CIDR space. A workaround is advertising a default route (`0.0.0.0/0`) or using static routes, but that conflicts with route-based segmentation controls (forcing central inspection paths). **The first thing to measure in a Shared VPC PoC should be "current and projected propagated prefix count 3 years out."**

### Minimal Shared VPC Pool vs. Per-Workload-Group Shared VPCs

When comparing "one minimal configuration that pools all workloads into a single Shared VPC" against "multiple dedicated Shared VPCs, one per workload group," there's a perspective that's easy to miss.

- **A single VPC can have only one TGW attachment (not adjustable).** A single attachment caps throughput at up to 100 Gbps (each direction) / 7,500,000 PPS per AZ.
- In the minimal configuration, all workloads' on-prem/external traffic converges onto this single attachment — you share not just blast radius, but **bandwidth and PPS ceilings** too.
- The per-workload-group configuration gives each VPC its own attachment, splitting that throughput ceiling. **Being able to split the TGW throughput ceiling is the real practical reason to choose "multiple dedicated Shared VPCs."**

Ultimately, the choice between minimal and per-group configurations is better understood as a **trade-off between "central network pipeline change risk" and "VPC-level shared failure risk,"** rather than "cost vs. isolation." Both depend on the quality of the central pipeline, so the actual deciding factor is measuring "how fast can we detect and recover from a bad central route change" under both options. A hybrid — minimal configuration for general workloads, dedicated configuration for workloads with heavy on-prem/external connectivity, split by trust zone — is also worth considering.

### Key Transit Gateway quotas

| Quota | Default | Adjustable |
|---|---|---|
| TGWs / Account | 5 | Yes |
| Attachments / TGW | 5,000 | Yes |
| **TGWs / VPC** | **5** | **No** |
| TGW route tables / TGW | 20 | Yes |
| Total routes / TGW | 10,000 | Contact SA/TAM |
| **VPC attachments per VPC** | **1** | **No** |

**MTU mismatches also need checking.** TGW's MTU is 8,500 bytes, but VPN paths are 1,500 bytes. Moving on-prem VPN connectivity from VPC Peering to TGW can cause asymmetric packet drops in this segment due to the mismatch — you need to change both VPCs simultaneously, and TGW applies MSS clamping to every packet.

If using VPC Peering, the Peered NAU limit is 128,000 (up to 512,000), applied **to the sum of all peered VPCs within the same Region** (cross-Region peering isn't included).

## 3. AZ IDs and Shared VPC

AZ names (`ap-northeast-2a`, etc.) can map to different physical AZs across Accounts. Cross-account resource placement should use **AZ IDs (`apne2-az*`)**, not AZ names.

If you're using VPC CNI custom networking, this isn't merely a best practice — it's a **functional requirement**: `ENIConfig` resources must be built against the AZ ID mapping published by the central networking Account. If you're isolating a PII boundary via a secondary CIDR, you're likely to end up using custom networking as well, so confirm this relationship in advance.

## 4. Regional NAT Gateway

| Item | Behavior |
|---|---|
| Scaling | Auto scales up/down under a single ID, no public subnet required |
| Private NAT | Not supported |
| Scaling delay | Up to 60 minutes (cross-AZ traffic may occur during that window) |
| Zonal → Regional migration | Connection resets, IP changes possible |
| Constrained AZs | **Not supported** — check in advance |

Regional NAT Gateway offers better IP/connection limits than Zonal — Regional allows 32 IPs per AZ (Zonal: 8), and each IP gains 55,000 additional concurrent connections to the same destination (dest IP + port + protocol). This has a direct benefit for patterns where a **small number of destinations receive a large volume of connections** (e.g., payment processors, shipping integrations), by preventing port exhaustion.

You can choose Automatic mode (AWS manages IP/AZ scaling, recommended) or Manual mode (you manage it directly). **If you need a fixed egress IP registered on an external partner's allowlist, you need Manual mode or IPAM public IPv4 allocation policy integration.** Regional NAT Gateway route tables support TGW as a valid route, so central TGW inspection and Regional NAT can be combined — they're not mutually exclusive.

## 5. TGW + Network Firewall (Central Inspection)

There are two ways to centrally inspect east-west traffic.

- **Via an inspection VPC**: requires appliance mode + bidirectional routes.
- **TGW-attached Network Firewall**: appliance mode is always applied.

Network Firewall **doesn't support asymmetric routing.** If the TGW owner Account and the firewall owner Account differ, you'll run into constraints around delete permissions and visibility.

From AWS's perspective, there's no condition that makes central inspection mandatory. **A hybrid — distributed controls within a trust zone, central enforcement only between trust zones or on regulated paths** — is reasonable in most cases.

## 6. AWS APIs and VPC Endpoints

Endpoint (Gateway/Interface) support and endpoint policy support vary by service, Region, and feature. If you don't specify an endpoint policy, a default full-access policy applies. We recommend maintaining this coverage matrix by periodically dumping `aws ec2 describe-vpc-endpoint-services` and diffing it automatically, rather than manual research.

## 7. Route 53 Profiles and Hybrid DNS

A Route 53 Profile can be associated with a Private Hosted Zone, Resolver rules (forwarding/system), a DNS Firewall rule group, an **interface VPC endpoint**, and VPC Resolver query logging config. A VPC can have only one Profile attached.

**The priority rule is the part most likely to be misunderstood.** It's not "local VPC always wins" — it's **"the more specific name wins."**

| DNS query | Profile rule | VPC local rule | Rule applied |
|---|---|---|---|
| `example.com` | `example.com` | `example.com` | Local VPC (same name → local wins) |
| `test.example.com` | `test.example.com` | `example.com` | **Profile (more specific name wins)** |
| `marketing.example.com` | none | `marketing.example.com` | Local VPC |

As the second row shows, **a more specific name registered on the central Profile overrides the workload's local rule.** Without knowing this, workloads can suffer from unexplained name resolution failures. **We recommend formalizing the rule that "the central Profile never owns a name more specific than the namespace delegated to a workload."** In practice, a combination works well where namespace governance is central and subdomains beneath it are delegated to workload teams. Route 53 Profiles are supported in the Seoul Region.

## 8. VPC-to-VPC Connectivity Options

These aren't mutually exclusive — they're patterns chosen per edge based on traffic requirements.

| Option | Suits | Constraints |
|---|---|---|
| VPC Peering | Direct bidirectional connectivity between a small number of VPCs | Peered NAU 128,000 (→512,000) limit, no CIDR overlap, non-transitive |
| Transit Gateway | Many VPCs, on-prem, central inspection | Propagated routes capped at 100 (fixed), 1 attachment per VPC (fixed), 100 Gbps/7.5M PPS per AZ |
| PrivateLink | Exposing a specific service in one direction | Endpoint cost, ongoing provider/consumer operations |
| **VPC Lattice** | Application-level service networking/auth, **connecting VPCs with overlapping CIDRs** (no alternative) | See table below |
| Same-VPC local routing | Same trust zone, resources that can share a VPC | Shares route/DNS/IP failure |

### VPC Lattice constraints

Lattice is often described more casually than its real constraints warrant.

| Item | Value | Impact |
|---|---|---|
| Service network associations per VPC | **1 only** | Multiple networks require a service-network-type VPC endpoint |
| **Max connection lifetime for a Lattice service** | **10 minutes** | **Long-lived connections (gRPC streaming, WebSocket, long batch calls) are forcibly cut every 10 minutes** — the application must handle reconnection |
| Lattice service idle timeout | Default 60s (60–600s) | |
| Lattice resource idle timeout | 350s, no connection lifetime limit | TCP resources have fewer constraints |
| Bandwidth/RPS per service per AZ | 10 Gbps / 10,000 RPS (increasable) | |
| Listeners per service / rules per listener | 2 / 10 | |
| Service networks per Region | 50 | |
| MTU | 8,500 bytes | |

**Exclude segments using long-lived connections from Lattice.** Conversely, Lattice can be a better fit than Private NAT or CNI custom networking for connecting legacy/acquired environments with overlapping CIDRs (since it operates in link-local address space).

## 9. East-West Inspection Options

| Option | Configuration |
|---|---|
| Distributed policy controls | SG/NACL/route/NetworkPolicy + Flow Logs |
| Per-VPC distributed firewall | An independent firewall per VPC |
| Central TGW inspection | Inspecting traffic in bulk on the Transit Gateway path |
| **Hybrid** | Distributed within a trust zone, centralized between trust zones/regulated paths |

If you use a Shared VPC, distributed policy controls also need the "owner owns subnet flow logs + block individual flow log creation by participants via SCP" rule mentioned earlier.

## Next

Once VPC boundaries are settled, the remaining decision is how to draw data and security boundaries on top → [Data and Security Boundaries](./05-data-security-boundaries.md)

## References

- [VPC quotas](https://docs.aws.amazon.com/vpc/latest/userguide/amazon-vpc-limits.html)
- [Shared VPC owner/participant responsibilities](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-share-limitations.html)
- [Supported services for shared subnets](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-sharing-service-behavior.html)
- [Shared subnet AZ IDs](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-sharing-share-subnet-working-with.html)
- [Security group sharing](https://docs.aws.amazon.com/vpc/latest/userguide/security-group-sharing.html)
- [Security group rules](https://docs.aws.amazon.com/vpc/latest/userguide/security-group-rules.html)
- [Firewall Manager common SG policy](https://docs.aws.amazon.com/waf/latest/developerguide/security-group-policies-common.html)
- [Firewall Manager SG audit policy](https://docs.aws.amazon.com/waf/latest/developerguide/security-group-policies-audit.html)
- [Regional NAT Gateway](https://docs.aws.amazon.com/vpc/latest/userguide/nat-gateways-regional.html)
- [TGW quotas](https://docs.aws.amazon.com/vpc/latest/tgw/transit-gateway-quotas.html)
- [Transit Gateway overview](https://docs.aws.amazon.com/vpc/latest/tgw/tgw-transit-gateways.html)
- [TGW-attached Network Firewall](https://docs.aws.amazon.com/network-firewall/latest/developerguide/tgw-firewall.html)
- [Network Firewall asymmetric routing](https://docs.aws.amazon.com/network-firewall/latest/developerguide/asymmetric-routing.html)
- [VPC Lattice quotas](https://docs.aws.amazon.com/vpc-lattice/latest/ug/quotas.html)
- [VPC Lattice overview](https://docs.aws.amazon.com/vpc-lattice/latest/ug/what-is-vpc-lattice.html)
- [PrivateLink supported services](https://docs.aws.amazon.com/vpc/latest/privatelink/aws-services-privatelink-support.html)
- [VPC Peering](https://docs.aws.amazon.com/vpc/latest/peering/vpc-peering-basics.html)
- [VPC connectivity options whitepaper](https://docs.aws.amazon.com/whitepapers/latest/aws-vpc-connectivity-options/amazon-vpc-to-amazon-vpc-connectivity-options.html)
- [Centralized VPC inspection](https://docs.aws.amazon.com/whitepapers/latest/building-scalable-secure-multi-vpc-network-infrastructure/centralized-network-security-for-vpc-to-vpc-and-on-premises-to-vpc-traffic.html)
- [Route 53 Profiles](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/profiles.html)
- [Route 53 Resolver hybrid DNS](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/resolver.html)
