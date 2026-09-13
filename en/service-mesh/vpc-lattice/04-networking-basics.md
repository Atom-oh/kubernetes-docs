# Foundations — Link-Local and SNI

> **Scope**: VPC Lattice service/resource APIs and AWS Gateway API Controller; verify the selected release and installed CRDs.
> **Last Updated**: September 13, 2026

## What This Document Covers

- What link-local addresses are, why Lattice chose them, and the two operational problems that follow
- Why SNI must be sent in plaintext — the chicken-and-egg problem of certificate selection
- Distinguish service-listener visibility from TCP resource connectivity and its separate access model

## Link-Local Addresses

### What they are

A link-local address is one from a range that is **valid only within a single link** (the same broadcast domain). Not crossing a router is the definition.

| Range | Protocol | Scope | Standard |
|---|---|---|---|
| `169.254.0.0/16` | IPv4 | link-local | RFC 3927 |
| `fe80::/10` | IPv6 | link-local | RFC 4291 |

These ranges exist to satisfy the requirement that **"even with no DHCP server and no routing configuration, you must be able to talk to your immediate neighbors."** Consequently these addresses need not be globally unique and can be reused on every link.

### Where AWS already uses this

The pattern is already familiar to anyone who has used EC2.

| Address | Purpose |
|---|---|
| `169.254.169.254` | **EC2 Instance Metadata Service (IMDS)** — the instance's own metadata and IAM Role credentials |
| `169.254.170.2` | ECS task credential endpoint |
| `169.254.170.23` | **EKS Pod Identity Agent** (IPv4) |
| `fd00:ec2::23` | EKS Pod Identity Agent (IPv6) |
| `169.254.171.0/24` | **VPC Lattice** (IPv4) |

AWS assigns these addresses special behavior, but they do not all share one scope or implementation. IPv4 link-local, IPv6 ULA and node-agent endpoints must be distinguished. The address standards themselves do not imply hypervisor interception.

For Lattice, describe the **documented VPC-specific addressing behavior**, not a general definition of link-local addressing or an inferred AWS internal implementation.

### Lattice's ranges — IPv4 and IPv6 are different in kind

A VPC Lattice service's DNS name resolves to two kinds of addresses.

| Range | Kind | Nature |
|---|---|---|
| `169.254.171.0/24` | IPv4 | **link-local** (within `169.254.0.0/16`) |
| `fd00:ec2:80::/64` | IPv6 | **Unique Local Address (ULA)** (within `fc00::/7`, RFC 4193) — **not** link-local |

> IPv6 ULA is **not link-local and not the deprecated site-local address class**. ULA addresses can be routed within private networks and have global address scope; intended routing reachability is distinct from address scope. For Lattice, follow AWS DNS and connectivity documentation rather than deriving the implementation from the address prefix.

Despite the naming difference, the properties that matter operationally are shared by both ranges — **they are not globally unique, they are reused within each VPC, and they are intercepted by the infrastructure.**

### Why Lattice uses this approach

As covered in [document 01](./01-appmesh-vs-lattice.md), Lattice must handle traffic **without a sidecar.** If there is no sidecar, who intercepts the traffic? Link-local addresses are the answer.

The mechanism is:

1. The client resolves the Lattice service's DNS name
2. DNS returns an address in `169.254.171.x` (or the `fd00:ec2:80::` range)
3. The client connects to that address normally — **the application does not know Lattice exists**
4. Packets destined for that range are **directed to a Lattice ingress endpoint inside the VPC**
5. Lattice evaluates listener rules, picks a Target, and forwards to the actual Pod IP

Traffic traverses the infrastructure without touching application code, Pod specs, or iptables rules. **This address range is how Lattice keeps a traffic interception point while removing the sidecar.**

## Two Problems That Follow From Choosing Link-Local

The design is elegant but has costs. Both problems must be in your migration plan.

### Problem 1 — Conflict with Envoy iptables interception

Sidecar meshes (App Mesh, Istio) **have an init container install iptables rules** to steer Pod traffic into the proxy. Typically this takes the form "redirect all outbound traffic from this Pod to Envoy's port."

A broad outbound REDIRECT can capture Lattice traffic. Whether this is a problem depends on the mesh policy, configured routes and signing design. Verify those before adding an explicit CIDR bypass.

The fix is **registering an exception CIDR** — excluding the Lattice range from interception so that traffic bypasses Envoy.

| Mesh | How to register the exception |
|---|---|
| App Mesh | Add the Lattice range to the egress-ignore CIDR list in the App Mesh CNI/init container configuration |
| Istio | Add the Lattice range to the `traffic.sidecar.istio.io/excludeOutboundIPRanges` annotation |

During coexistence, verify the mesh outbound policy, registered external destinations, signing path and both address families. Some Envoy configurations forward unknown destinations, while restricted configurations reject them. A CIDR exclusion is one deliberate bypass design, not proof that every coexisting mesh fails without it.

The reverse use is also possible. The egress proxy pattern in [document 03](./03-auth-flow.md) uses iptables to select **only the Lattice range** and send it to the signing proxy — the same tool used for the opposite purpose.

### Problem 2 — Destination-IP-based observability and control become meaningless

Link-local addresses are **not globally unique and do not identify a service.** That breaks the assumptions of existing operational tooling.

| What breaks | Why |
|---|---|
| **Identifying the peer from flow log destination IPs** | The destination only ever shows as `169.254.171.x`. You cannot tell which Lattice service it was |
| **Destination-CIDR-based Security Group egress rules** | Every Lattice service is in the same range. You cannot allow/deny per service |
| **Destination-IP-based NetworkPolicy** | Same as above. Kubernetes NetworkPolicy `ipBlock` cannot distinguish Lattice services |
| **IP-based monitoring dashboards and alarms** | IP-only attribution is unreliable for stable service identity; enrich with DNS, request IDs and service-aware logs |
| **IP-range-based asset inventory** | Lattice services do not appear in the inventory as IPs |

**The alternative is to move the control layer.**

- **Express authorization with auth policies, not IPs** — principal, path, method, and header conditions ([document 03](./03-auth-flow.md))
- **Observe with Lattice access logs, not flow logs** — those record which service was called
- **Open Security Groups with managed prefix lists, not CIDRs** (below)

This is not a tooling swap but a **shift in the control model** — from "control by IP and port" to "control by identity and policy." A substantial part of the network team's existing operational assets simply does not work in this range. In financial-sector environments this can escalate into a question of organizational responsibility boundaries, so it should be agreed with the network team early.

### Open Security Groups with prefix lists

To receive traffic arriving from Lattice, node Security Groups must allow it. Rather than writing CIDRs directly, the correct approach is **AWS-managed prefix lists.**

| Prefix list name | Purpose |
|---|---|
| `com.amazonaws.<region>.vpc-lattice` | IPv4 |
| `com.amazonaws.<region>.ipv6.vpc-lattice` | IPv6 |

```bash
# Read-only lookup; apply the reviewed ingress rule through CDK/Terraform.
: "${AWS_REGION:?Set the reviewed AWS Region}"
aws ec2 describe-managed-prefix-lists --region "$AWS_REGION" \
  --query "PrefixLists[?PrefixListName=='com.amazonaws.$AWS_REGION.vpc-lattice'].{Id:PrefixListId,Name:PrefixListName}" \
  --output json
```

In reviewed IaC, allow the applicable Lattice prefix list **only on required target/health-check ports and protocols**, on the actual target SG (node or Pod SG as configured). Avoid all-protocol ingress. Separately verify client/service-network association SGs; no SG is changed by the lookup above.

## SNI — Server Name Indication

### Why the domain must be sent in plaintext

SNI is a TLS extension that carries **the domain name of the server you want to reach, in plaintext, inside the `ClientHello`.** Putting the destination domain in plaintext in the first message of an encryption protocol seems odd, but there is an unavoidable circularity.

**The chicken-and-egg problem:**

1. To start a TLS connection, the server must choose **which certificate to present**
2. Certificates are bound to domains (the certificate for `api.example.com` differs from `www.example.com`)
3. If one IP:port serves multiple domains, the server **must know which domain the client wants** in order to pick a certificate
4. But the domain the client wants is in the HTTP `Host` header, and **the `Host` header arrives encrypted inside TLS**
5. So **to start encryption you need the domain, and to learn the domain you need encryption to have started**

Ordinary TLS sends SNI in ClientHello so the server can select a certificate before reading HTTP. This is not the only conceivable design: ECH encrypts an inner ClientHello using a key obtained in advance. Lattice TLS passthrough currently requires visible SNI and does not support ECH/ESNI.

In short, **SNI's plaintext exposure is not a design mistake but a deliberate compromise to break the circularity.** And thanks to that compromise, **middleboxes that do not terminate TLS can still learn the destination domain** — the basis of TLS Passthrough routing.

### What Lattice does with SNI

On a TLS Passthrough listener, Lattice does not terminate TLS. So **on what basis does it pick a Target?** SNI. It reads the plaintext SNI field of the `ClientHello` and routes on that alone.

## HTTPS Listener vs TLS Passthrough — What Lattice Can See

| Information | HTTPS listener (TLS Terminate) | TLS Passthrough |
|---|---|---|
| **SNI (domain)** | ✅ | ✅ |
| **HTTP path** | ✅ | ❌ |
| **HTTP method** | ✅ | ❌ |
| **HTTP headers** | ✅ | ❌ |
| **Query string** | ✅ | ❌ |
| **`Authorization` header (SigV4)** | Readable; authenticated IAM requests supported | Encrypted; authenticated SigV4 identity unavailable |
| **Request body** | ✅ (passes through) | ❌ |
| **Path/header-based routing** | ✅ | ❌ (SNI only) |
| **Path/method/header condition keys** | ✅ | ❌ |
| **HTTP detail in access logs** | ✅ | Limited |
| **End-to-end encryption preserved** | ❌ (terminated once at Lattice) | ✅ |
| **Endpoint's own mTLS** | ❌ (Lattice does not request client certs) | ✅ (endpoint does it itself) |
| **Target Group protocol** | HTTP / HTTPS | **TCP** |
| **Gateway API resource** | `HTTPRoute` / `GRPCRoute` (`tls.mode: Terminate`) | `TLSRoute` (`tls.mode: Passthrough`) |

This table captures the single most important trade-off in this section.

> **TLS passthrough preserves endpoint TLS and can carry endpoint mTLS, but Lattice cannot inspect HTTP fields or authenticate their SigV4 headers.** Anonymous network-context auth policies are distinct from authenticated caller identity.

Choose the trust boundary **per listener/path**, not by claiming that one service can never have different listener types. TLS passthrough can use anonymous network-context policies; it does not provide signed caller identity. Configure the backend protocol separately: an HTTPS listener may forward HTTP or HTTPS, and Lattice does not validate target certificates on an HTTPS target connection.

## Protocols Lattice Supports

| Listener protocol | Application protocol | Target Group protocol |
|---|---|---|
| **HTTP** | HTTP/1.1 | HTTP |
| **HTTPS** | HTTP/1.1, HTTP/2, gRPC (**negotiated via ALPN**; HTTP/1.1 when ALPN is absent) | HTTP / HTTPS |
| **TLS_PASSTHROUGH** | (not interpreted by Lattice) | **TCP** |

**There is no standalone raw TCP listener.** TCP exists only as the Target Group protocol for TLS_PASSTHROUGH.

### Service listeners and TCP resource connectivity

VPC Lattice **service listeners** expose HTTP, HTTPS and TLS_PASSTHROUGH. Separately, **resource configurations and resource gateways support TCP resources**. Service-network auth policies do **not** apply to those resource configurations; evaluate their sharing, endpoint/network controls and resource authentication separately.

Choose the service model when you need supported HTTP routing/authentication, and evaluate resource connectivity for TCP access without those service features. The absence of a raw-TCP **service listener** is an API capability boundary, not a mathematical impossibility for networking.

- HTTP/HTTPS service routing uses supported application fields.
- TLS passthrough requires SNI matching the configured custom domain.
- TCP resource connectivity uses a resource configuration/resource gateway and its own association/access model.

For HTTP/2 and gRPC **service target protocol versions, AWS requires an HTTPS listener**; the target-group transport can be HTTP or HTTPS as supported. Do not confuse plaintext HTTP/2 on a backend with plaintext h2c client access to a service listener. A database that negotiates TLS only after initial plaintext messages also differs from a listener expecting ClientHello first.

> The published service-listener restriction does not exclude TCP resource access. Evaluate resource gateways, existing private connectivity or an NLB according to the required routing and authorization model.

See the current [resource configuration](https://docs.aws.amazon.com/vpc-lattice/latest/ug/resource-configuration.html) and [TLS listener](https://docs.aws.amazon.com/vpc-lattice/latest/ug/tls-listeners.html) references. Controller support for those AWS APIs must be checked separately from service availability.

## Security Note — Implications of Plaintext SNI

### What is exposed

TLS protects the content of communication, but **which domain you connected to is visible to observers on the path.** This is a general property of TLS and SNI, not a Lattice characteristic.

Since this is intra-VPC communication, external observers are not the concern, but two things are worth knowing.

- **Internal observers can see service call relationships.** Anyone able to observe traffic within the VPC can reconstruct the call graph from SNI.
- **Flow log destination IPs are meaningless but SNI is meaningful.** This also means the "destination-IP observability breaks" problem above can be partly compensated with SNI-based observability.

### ECH — the answer to plaintext SNI exposure

**Encrypted Client Hello (ECH)** is a standard that encrypts the `ClientHello` itself to prevent SNI exposure. It distributes the server's public key in advance via DNS and encrypts the sensitive parts of the `ClientHello` with it — **using DNS to sidestep** the chicken-and-egg problem described above.

::: note TLS passthrough requirement
AWS explicitly states that TLS listeners do not support ECH or ESNI, require a custom domain and use SNI to select the service. Check idle/lifetime limits and target TCP health checks before migrating long-lived protocols.
:::

### Impact on environments with SNI-based control appliances

Many organizations, including in the financial sector, operate **appliances that control traffic based on SNI** — allowed-domain whitelists, SNI-based logging, per-domain policy enforcement. Adopting Lattice affects such environments in two directions.

| Configuration | Impact from the SNI-appliance perspective |
|---|---|
| **HTTPS listener** | The SNI the client sends is the Lattice service's domain. You must **add the Lattice domain (`*.vpc-lattice-svcs.<region>.on.aws` or your custom domain) to existing whitelists.** Beyond that, the Lattice→Target segment is outside the appliance's visibility |
| **TLS Passthrough** | SNI is preserved end-to-end, so it pairs well with SNI-based control. But you give up IAM Auth |
| **link-local range** | Destination-IP-based control appliances are neutralized (see "Problem 2" above) |

**If you use a custom domain, this is where you meet the Host header pitfall from [document 03](./03-auth-flow.md).** If you attach a custom domain for SNI control but your signing logic still uses the Lattice-generated domain, you get 403s. Introducing a custom domain is a decision that must settle SNI control, the signed Host value, and certificate management together.

## Summary

- A link-local address is a **marker meaning "the infrastructure handles this packet."** It is the same family as IMDS and the Pod Identity Agent, and it is how Lattice intervenes in traffic without a sidecar.
- IPv4 is `169.254.171.0/24` (link-local), but **IPv6 is `fd00:ec2:80::/64`, a ULA rather than link-local.** Lattice traffic must route within the VPC, and link scope is insufficient.
- Validate coexistence routing and service-aware attribution; use reviewed prefix-list IaC and correlate network/application logs.
- SNI is plaintext because of the **chicken-and-egg problem of certificate selection** — a deliberate compromise that also makes TLS Passthrough routing possible.
- Without TLS termination Lattice cannot authenticate encrypted HTTP SigV4 headers; anonymous network-context policies and endpoint authentication remain separate controls.
- Raw TCP is not a service-listener protocol; TCP resource configurations are a separate supported connectivity model.

Next: [Workload Identity Migration](./05-spiffe-to-iam.md) examines how far IAM can take over what SPIRE was doing.

## References

- [Managing DNS resolution with Amazon VPC Lattice and VPC resources](https://aws.amazon.com/blogs/networking-and-content-delivery/managing-dns-resolution-with-amazon-vpc-lattice-and-vpc-resources/)
- [Amazon VPC Lattice DNS migration strategies and best practices](https://aws.amazon.com/blogs/networking-and-content-delivery/amazon-vpc-lattice-dns-migration-strategies-and-best-practices/)
- [AWS Gateway API Controller — Deploy the controller (prefix list setup)](https://www.gateway-api-controller.eks.aws.dev/latest/guides/deploy/)
- [AWS Gateway API Controller — TLS Passthrough](https://www.gateway-api-controller.eks.aws.dev/latest/guides/tls-passthrough/)
- [Enabling end-to-end encryption with Amazon VPC Lattice TLS passthrough](https://aws.amazon.com/blogs/networking-and-content-delivery/enabling-end-to-end-encryption-with-amazon-vpc-lattice-tls-passthrough/)
- [HTTPS listeners for VPC Lattice services](https://docs.aws.amazon.com/vpc-lattice/latest/ug/https-listeners.html)
- [RFC 3927 — IPv4 Link-Local Addresses](https://datatracker.ietf.org/doc/html/rfc3927) / [RFC 4193 — Unique Local IPv6 Unicast Addresses](https://datatracker.ietf.org/doc/html/rfc4193)
- [RFC 6066 — TLS Extensions: Server Name Indication](https://datatracker.ietf.org/doc/html/rfc6066)
- [Network Fundamentals Part 2: Transport Layer and TLS](../../basics/06-network-fundamentals-part2.md)


- [Target groups and protocol versions](https://docs.aws.amazon.com/vpc-lattice/latest/ug/target-groups.html) — HTTPS target certificate behavior and HTTP/2/gRPC listener requirements

TLS listener operating limits also matter: only a default forward rule is supported, Lambda targets are excluded, connection duration is limited to 10 minutes, and service idle timeout is configurable from 60–600 seconds. TCP target-group health checks are **disabled by default**; enabling them requires a supported probe protocol/version. Verify the current API/Region settings before adopting long-lived connections.