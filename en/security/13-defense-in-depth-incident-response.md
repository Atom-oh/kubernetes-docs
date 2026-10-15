# Defense in Depth and Incident Response from Real Incidents

> **Review basis**: Official AWS, Kubernetes, Palo Alto Networks and Fortinet documentation, CISA alerts and NIST SP 800-61r3. Publication dates are distinct from the research date.
> **Last Updated**: October 15, 2026

A security design must cover entry, lateral movement, exfiltration and recovery. This chapter connects perimeter controls and incident handling to the existing [EKS security](./06-eks-security-best-practices.md), [NetworkPolicy](./04-network-policies.md) and [runtime security](./08-runtime-security.md) guides. Operational criteria and sequencing below are **design proposals** for this guide, not a guarantee provided by installing a product.

## 1. Verified incidents and design lessons

| Case and publication/retirement date | Scope established by primary sources | Design consequence |
|---|---|---|
| ingress-nginx CVE-2025-1974, 2025-03-24 | Attack through the validating admission controller reachable from the Pod network; historical fixes were 1.11.5 and 1.12.1 | Review webhook reachability and controller Secret permissions alongside external WAF protection |
| ingress-nginx retirement, 2026-03 | Kubernetes Steering/SRC warned on 2026-01-29 that security updates would stop after retirement | Migrate to a maintained implementation; historical CVE fixes are not a new 2026 version recommendation |
| PAN-OS CVE-2025-0108, 2025-02-12 | Management web authentication bypass with observed chaining attempts | Separate management access from public application paths |
| PAN-OS CVE-2026-0322, 2026-10-14 | Authenticated management-interface RCE as root; limited exploitation observed; PA-Series, VM-Series and Panorama affected | Protect administrator credentials, sessions and management reachability; distinguish product families |
| FortiCloud SSO CVE-2026-24858, CISA KEV addition 2026-01-27 | Cross-account access with FortiCloud SSO enabled, account/VPN changes and a new path affecting devices patched for earlier SSO CVEs | Audit administrative changes; SSO adoption alone is insufficient |
| FortiGate persistent access, 2025-04-10 | An SSL-VPN-related symbolic link could retain file-reading access after earlier vulnerabilities were patched | Track patching and removal of compromise as separate completion conditions |

Evidence: [Kubernetes CVE alert][S01], [retirement statement][S02], [PAN-OS 2025 advisory][S04], [2026 advisory][S03], [CISA KEV data][S06] and [Fortinet persistence analysis][S07]. Fortinet corrected its 2026 SSO analysis on January 28: **third-party SAML IdPs and FortiAuthenticator are not affected by that issue**. Do not repeat the initial broader “all SAML” wording. [S05]

CISA added CVE-2026-0322 on 2026-10-14 and CVE-2026-24858 on 2026-01-27. Review KEV listing with vendor affectedness when prioritizing. Do not generalize US federal remediation deadlines into universal legal obligations. [S06]

Disclosure does not establish that every installation was compromised. Check product, branch, hotfix, enabled features, exposure and evidence. Cloud NGFW and Prisma Access are excluded from the PAN-OS 2026 advisory; this exclusion does not extend to every CVE. An estimated patch date is distinct from confirmed release availability. [S03]

## 2. Control responsibilities and remaining coverage

| Control | Primary scope | Complementary controls |
|---|---|---|
| WAF | HTTP(S) requests to associated resources and configured matches | Application authentication/authorization, validation, upload inspection and origin restrictions |
| NGFW/IPS | Traversing network sessions and configured security profiles | TLS visibility, management protection, patching and bidirectional routing |
| GWLB/GWLBE | Insertion of GENEVE-compatible appliances and flow distribution | Appliance inspection policies, session handling, capacity and recovery |
| Kubernetes NetworkPolicy | Pod connections enforced by a supported CNI | hostNetwork/node/local-path checks and service authentication |
| mTLS/SPIFFE | Peer identity and transport protection | Service authorization, request validation and access records |
| Image/admission policies | Deployed images and workload configuration | Runtime detection, patching and secret management |

The [WAF resource list][S09] and [GWLB documentation][S24] establish their scope. NetworkPolicy needs an enforcing plugin; its API does not provide TLS or force every connection through a common gateway. [S34]

**An installed appliance and an inspected request require different evidence.** Proposed acceptance criteria establish:

1. **Path**: Did this request actually traverse the designated WAF or firewall?
2. **Policy**: Which rule, signature, decryption policy and exception applied?
3. **Outcome**: Do allow/deny decisions and application behavior match expectations?

## 3. Inventory traffic first

Use this threat-model template, fill actual principals, CIDRs and resource IDs, and mark unobserved paths as unverified.

| Flow | Entry or exit paths to investigate | Control and evidence |
|---|---|---|
| User → web/API | CloudFront, ALB, additional load balancers/domains/NodePorts | Web ACL association, legitimate requests, benign blocking canary and direct-origin result |
| Operator → management | PAN-OS/FortiGate, Panorama/FortiManager, EKS API, GitOps | Trusted management path, authentication, administrator/policy change records |
| API server → webhook | Control plane and admission Service | API-server access, ordinary workload restrictions, certificates and RBAC |
| Pod → external | Node SNAT, NAT Gateway, TGW, IPv4/IPv6, proxies | Allowed/denied destinations, addresses before/after translation and firewall sessions |
| Pod → Pod/database | Same node, same VPC, different VPC | CNI policies, database SGs, service authorization and bidirectional tests |
| Pod → AWS service | PrivateLink, S3/DynamoDB gateway endpoints, public endpoints | IAM/resource/endpoint policies and observed connection path |
| CI/CD → cluster | OIDC roles, registry, GitOps controller | Signatures/digests, least privilege and audited changes |

Central TGW inspection covers **traffic routed through TGW**. Do not assume it includes same-node Pod traffic, VPC-local routes, peering or separate endpoint paths. Check routing and the CNI together. [S29] [S30] [S34]

## 4. Architecture ownership

For public applications use [WAF and origin protection](./14-waf-edge-api-security.md). For outbound and inter-VPC inspection use [NGFW design](./15-ngfw-paloalto-fortinet.md) and [GWLB/GENEVE](./16-gwlb-geneve-inspection.md). Within the VPC, connect these controls to NetworkPolicy, security groups and mTLS.

An example division of ownership:

| Owner | Proposed responsibility | Change review |
|---|---|---|
| Application team | Authentication, authorization, schema and uploads | Application protection behind WAF exceptions |
| Platform team | EKS, controllers, CNI, admission and GitOps | Webhook, Pod and AWS permission boundaries |
| Network team | TGW, VPC routes, GWLBE, NAT and appliance capacity | Request/return paths, AZ failure and bypasses |
| Security team | Inspection policies, signatures, investigations and exception expiry | Blocking effectiveness, detection evidence and recovery |
| Incident commander | Containment, evidence and recovery decisions | Business impact, credential replacement and retesting |

Separate authority to change default paths from authority to grant inspection exceptions. Record emergency bypass scope, reason, expiration and recovery owner. This is an organizational proposal, not a finding from an inspected AWS account.

## 5. Detection evidence

| Behavior | Correlate | Limitation of a single source |
|---|---|---|
| Administrator login followed by account/policy creation | Appliance authentication/configuration audits, central manager and management-path records | A compromised appliance may provide less trustworthy local records |
| WAF removal/exception or inspection bypass | AWS changes, Web ACL associations, route/SG changes and application access | Zero blocks do not prove healthy enforcement |
| Controller compromise followed by Secret access | Kubernetes audit, controller RBAC and runtime behavior | Web access logs do not cover every webhook attack |
| Suspected exfiltration | CNI observations, firewall sessions, pre-NAT addresses and application/AWS API audit | VPC Flow Logs do not contain application payloads or authorization results |
| Reentry after patching | Administrator/VPN accounts, configuration differences and credential use | Version numbers do not prove removal of persistent access |

Fortinet documents administrator creation and configuration changes. EKS documents the metadata nature of Flow Logs and attribution difficulties when Pod addresses change. [S05] [S33]

GuardDuty threat detection, Inspector vulnerability management, Security Hub exposure/correlation and CSPM configuration checks have different purposes. Verify the coverage of services already in use, then correlate network, appliance and application records by time and resource identity. See [EKS security practices](./06-eks-security-best-practices.md) for service details.

## 6. Response to suspected compromise

NIST SP 800-61r3 connects detection, response and recovery to broader risk management. The following appliance/EKS procedure is this guide’s operational proposal. [S08]

1. **Classify**: Establish affected product, branch, feature, exposure and investigation scope. Distinguish vulnerable assets from assets with compromise evidence.
2. **Preserve evidence**: Record UTC times, configuration revisions, administrator/VPN accounts, authentication/system/threat logs and cloud changes. Contain concurrently when delaying containment would increase harm; document the decision.
3. **Contain**: Restrict affected management paths and workloads while identifying control-plane, DNS, logging and approved recovery dependencies.
4. **Remove access**: Follow vendor procedures for unauthorized accounts, settings and filesystem changes. Rebuild from verified images and known-clean configuration when required; do not blindly restore suspect settings.
5. **Replace secrets**: According to exposure, review administrator/VPN/LDAP/AD/API/cloud credentials, certificates and sessions. Changing one firewall password is insufficient.
6. **Demonstrate recovery**: Retest denied management access, legitimate business functions, benign blocking canaries, egress, AZ failure and log collection.
7. **Improve**: Analyze causes, exposure duration, exceptions, detection delays and change permissions; update controls and playbooks.

Fortinet recommends treating system/configuration as compromised when indicators are confirmed, restoring or auditing configuration and rotating connected credentials. Its persistence analysis also requires configuration review. [S05] [S07]

## 7. Adoption sequence and completion criteria

The following is an adaptable execution plan, not a vendor SLA or incident-remediation deadline.

| Stage | Work | Completion evidence |
|---|---|---|
| First | Inventory public management, retired ingress, actively exploited CVEs and origin bypasses | Asset/exposure/affected branch/owner records and corrective actions |
| Stage 1 | Validate WAF logging/rules, administrator-change detection and webhook/Pod boundaries | Allow/deny results and effective policy IDs |
| Stage 2 | Outbound/inter-VPC inspection, Palo Alto/Fortinet PoC and symmetric GWLB paths | Request/response captures, NAT placement and failure experiments |
| Stage 3 | Capacity, upgrades, recovery and exception lifecycle | SLO measurements, recovery exercises and reviewed change procedures |

Do not use blocking percentage alone. Track **inspection-path coverage, origin bypass tests, unauthorized administrator changes, missing logs, recovery time and legitimate-traffic errors** together. Leave performance and availability numbers unclaimed until measured.

## Continue learning

- [WAF, Edge and API Security](./14-waf-edge-api-security.md)
- [Palo Alto and Fortinet NGFW](./15-ngfw-paloalto-fortinet.md)
- [GWLB and GENEVE Inspection](./16-gwlb-geneve-inspection.md)
- [Chapter quiz](../quizzes/security/13-defense-in-depth-incident-response-quiz.md)

## References and Research Basis

Primary sources accessed on 2026-10-15. Recheck advisories and constraints for the selected product/branch before changes.

- [S01 — Kubernetes: CVE-2025-1974][S01]
- [S02 — Kubernetes: ingress-nginx retirement statement][S02]
- [S03 — Palo Alto: CVE-2026-0322][S03]
- [S04 — Palo Alto: CVE-2025-0108][S04]
- [S05 — Fortinet: Analysis of SSO abuse on FortiOS][S05]
- [S06 — CISA: Known Exploited Vulnerabilities Catalog][S06]
- [S07 — Fortinet: Analysis of threat actor activity][S07]
- [S08 — NIST SP 800-61r3][S08]
- [S09 — AWS WAF: Associating a web ACL][S09]
- [S24 — AWS: Gateway Load Balancers][S24]
- [S29 — AWS: Centralized inspection with GWLB and TGW][S29]
- [S30 — AWS: NAT Gateway scenarios][S30]
- [S33 — EKS: Network security][S33]
- [S34 — Kubernetes: Network Policies][S34]

[S01]: https://kubernetes.io/blog/2025/03/24/ingress-nginx-cve-2025-1974/
[S02]: https://kubernetes.io/blog/2026/01/29/ingress-nginx-statement/
[S03]: https://security.paloaltonetworks.com/CVE-2026-0322
[S04]: https://security.paloaltonetworks.com/CVE-2025-0108
[S05]: https://www.fortinet.com/blog/psirt-blogs/analysis-of-sso-abuse-on-fortios
[S06]: https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json
[S07]: https://www.fortinet.com/blog/psirt-blogs/analysis-of-threat-actor-activity
[S08]: https://csrc.nist.gov/pubs/sp/800/61/r3/final
[S09]: https://docs.aws.amazon.com/waf/latest/developerguide/web-acl-associating-aws-resource.html
[S24]: https://docs.aws.amazon.com/elasticloadbalancing/latest/gateway/gateway-load-balancers.html
[S29]: https://aws.amazon.com/blogs/networking-and-content-delivery/centralized-inspection-architecture-with-aws-gateway-load-balancer-and-aws-transit-gateway/
[S30]: https://docs.aws.amazon.com/vpc/latest/userguide/nat-gateway-scenarios.html
[S33]: https://docs.aws.amazon.com/eks/latest/best-practices/network-security.html
[S34]: https://kubernetes.io/docs/concepts/services-networking/network-policies/
