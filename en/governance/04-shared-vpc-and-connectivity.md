# Shared VPC and Connectivity

> **Last Updated**: September 13, 2026

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

**Flow Log ownership is asymmetric.** Central owner-managed subnet/VPC logs can coexist with participant ENI logs, with explicit purpose, retention, and cost ownership. AWS does not require an SCP banning all participant logs. Flow Logs observe traffic; they do not block it.

**VPC/subnet tags are not shared with participants.** Test discovery using the actual Load Balancer Controller version, mode, and IAM permissions. Explicit subnet-ID annotations are a predictable option; this does not mean every discovery mode or version must fail.

Security groups only support Allow rules, and rules from multiple SGs are merged — a broad Allow in one SG can't be offset by a more restrictive central SG. The adjustable defaults are 60 rules per SG (inbound/outbound × IPv4/IPv6, each) and 5 SGs per ENI, and there's a constraint of **"rule count × SGs per ENI ≤ 1,000."** Firewall Manager's common SG policies consume this same budget.

Participant ENI/SG quotas are counted against that participant Account. The defaults of 5,000 ENIs/AZ and 2,500 SGs/Region can still bottleneck each Account and are adjustable. Assess capacity separately from SG authorization.

<span id="_2-the-real-ceiling-on-shared-vpc-—-it-s-not-the-cidr"></span>

## 2. Calculate Shared VPC Quotas by Their Actual Scope

Bottleneck order depends on the workload. Separate default and applied quotas, and project growth within each scope.

| Scope | Default quota | Interpretation |
|---|---|---|
| Non-propagated routes per VPC route table | 500 each for IPv4/IPv6; adjustable to 1,000 | Includes static routes targeting a TGW |
| Propagated routes per VPC route table | 100; fixed | VGW propagation limit, separate from TGW table totals |
| Combined static+dynamic routes across all TGW tables | 10,000 per TGW | Contact SA/TAM for increases |
| Participant Accounts per VPC | 100; adjustable | Sharing principals |
| Shared subnets per receiving Account | 100; adjustable | AZ/purpose combinations |
| NAU per VPC | 64,000; adjustable to 256,000 | Includes Pod IPs, ENIs, and managed-prefix-list entries |
| Subnets and route tables per VPC | 200 each; adjustable | Configuration count |
| IPv4 CIDRs per VPC | 5; adjustable to 50 | Also evaluate address consumption and fragmentation |

**TGW routes do not automatically propagate into VPC route tables.** The VPC owner adds static routes targeting the TGW; attachment propagation is managed in TGW route tables. Thus “more than 100 TGW prefixes stops Shared VPC” is incorrect. Whether a default route preserves or bypasses inspection depends on actual route associations and return paths.

### Minimal Shared VPC Pool vs. Per-Workload-Group Shared VPCs

When comparing "one minimal configuration that pools all workloads into a single Shared VPC" against "multiple dedicated Shared VPCs, one per workload group," there's a perspective that's easy to miss.

- **Only one VPC attachment is allowed for the same TGW–VPC pair.** A VPC can connect to up to 5 TGWs. Default attachment capacity is up to 100 Gbps each direction/7.5 MPPS per AZ; discuss additional capacity with SA/TAM.
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
| **Attachments for the same TGW–VPC pair** | **1** | **No** |

**Check MTU across the complete path.** TGW supports 8,500 bytes for VPC/DX/Connect/peering paths; VPN has separate tunnel limits. When migrating VPC peering to TGW, test both endpoints’ jumbo-frame settings and PMTUD. MSS clamping concerns TCP and does not solve MTU issues for every packet protocol such as UDP.

Peered NAU counts a VPC plus its directly peered VPCs in the same Region (default 128,000, maximum 512,000), not every VPC in the organization or a transitive connectivity graph.

## 3. AZ IDs and Shared VPC

AZ names (`ap-northeast-2a`, etc.) can map to different physical AZs across Accounts. Cross-account resource placement should use **AZ IDs (`apne2-az*`)**, not AZ names.

For VPC CNI custom networking, use AZ IDs to map owner subnets to participant nodes’ physical AZs. ENIConfig names must match the selected node annotation/label. With `ENI_CONFIG_LABEL_DEF=topology.kubernetes.io/zone`, use the node’s AZ name and put the subnet ID matching that AZ ID in the spec. Blindly naming ENIConfig with an AZ ID can break lookup. A secondary CIDR alone is not a security boundary.

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

Check endpoint and endpoint-policy support by service, Region, and feature. A default full-access endpoint policy does not grant new IAM permissions. Combine describe-vpc-endpoint-services inventory with service documentation, private-DNS checks, and actual allow/deny validation.

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
| Transit Gateway | Many VPCs, on-prem, central inspection | Count TGW table totals, VPC static routes, per-pair attachments, and throughput separately |
| PrivateLink | Exposing a specific service in one direction | Endpoint cost, ongoing provider/consumer operations |
| **VPC Lattice** | Application service/resource connectivity, including overlapping CIDR use cases | Compare protocols, auth, and cost with alternatives such as PrivateLink/NAT |
| Same-VPC local routing | Same trust zone, resources that can share a VPC | Shares route/DNS/IP failure |

### VPC Lattice constraints

Lattice is often described more casually than its real constraints warrant.

| Item | Value | Impact |
|---|---|---|
| Service network associations per VPC | **1 only** | Multiple networks require a service-network-type VPC endpoint |
| **Max connection lifetime for a Lattice service** | **10 minutes** | Test reconnect/retry/idempotency; distinguish resource connections |
| Lattice service idle timeout | Default 60s (60–600s) | |
| Lattice resource idle timeout | 350s, no connection lifetime limit | TCP resources have fewer constraints |
| Bandwidth/RPS per service per AZ | 10 Gbps / 10,000 RPS (increasable) | |
| Listeners per service / rules per listener | 2 / 10 | |
| Service networks per Region | 50 | |
| MTU | 8,500 bytes | |

Assess long-lived traffic separately for services and resources. A service’s 10-minute lifetime differs from a resource’s 350-second idle timeout. HTTP/HTTPS listeners do not natively support WebSockets; TLS listeners or Lattice resources provide alternative paths. Choose after validating protocols, reconnection, SNI, authorization, and load.

## 9. East-West Inspection Options

| Option | Configuration |
|---|---|
| Distributed policy controls | SG/NACL/route/NetworkPolicy + Flow Logs |
| Per-VPC distributed firewall | An independent firewall per VPC |
| Central TGW inspection | Inspecting traffic in bulk on the Transit Gateway path |
| **Hybrid** | Distributed within a trust zone, centralized between trust zones/regulated paths |

Document Shared VPC log ownership, access, retention, and duplicate cost. Owner and participant logs can be collected centrally; banning participant logs is not a prerequisite.

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
- [TGW route propagation FAQ](https://aws.amazon.com/transit-gateway/faqs/)
- [ENIConfig label mapping](https://docs.aws.amazon.com/eks/latest/best-practices/custom-networking.html)
- [Lattice listener protocols](https://docs.aws.amazon.com/vpc-lattice/latest/ug/listeners.html)
