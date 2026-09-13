# Workload Identity Migration — SPIFFE to IAM

> **Scope**: VPC Lattice service/resource APIs and AWS Gateway API Controller; verify the selected release and installed CRDs.
> **Last Updated**: September 13, 2026

## What This Document Covers

- How SPIFFE/SPIRE solved the workload identity problem — in particular, how attestation resolves the bootstrapping problem
- The similarities between SPIFFE-based mTLS and Lattice IAM Auth (short-lived credentials plus platform attestation) and the **two decisive differences**
- Why those differences become the central issue in financial-sector security reviews

## The Starting Problem — How Does a Workload Prove Itself?

When service A calls service B, B needs to know "did this request really come from A?" The problem is hard because of **how you deliver the secret needed for the proof in the first place.**

To hand a secret (a certificate, an API key) to a workload, you must know that workload really is that workload — and to know that, you need a secret. This is the **bootstrapping problem**, and the traditional workarounds all just move the problem.

| Workaround | Where it moves the problem |
|---|---|
| Bake certificates into the image | Image leak = identity leak. Renewal requires a rebuild |
| Mount as a Secret | Everyone who can read the Secret can forge that identity |
| Inject at deploy time | The CI/CD system holds the master key for every identity |

SPIFFE/SPIRE and Lattice IAM Auth **both solve this by having the platform vouch for the workload.** That is why their structures are strikingly similar. And because they are similar, **exactly where they differ** becomes the focus of the review.

## The Three SPIFFE Elements

SPIFFE (Secure Production Identity Framework For Everyone) is a **standard** for workload identity — a specification, not an implementation.

### ① SPIFFE ID — the name of the identity

Identifies a workload as a URI.

```text
spiffe://<trust-domain>/<workload-path>

e.g.: spiffe://finance.example.com/ns/prodcatalog/sa/prodcatalog-sa
```

The `trust-domain` is **the name of a trust boundary.** Workloads in the same trust domain share a common root of trust (the same CA). The path portion is freely designed by the organization; in Kubernetes environments it usually reflects namespace and ServiceAccount.

Notably, **there is no network information in the name** — no IP, no hostname, no port. This is deliberate: wherever a workload is scheduled and however its IP changes, the identity stays the same. The shift from "IP-based control to identity-based control" seen in [document 04](./04-networking-basics.md) begins here.

### ② SVID — the credential proving the identity

**SPIFFE Verifiable Identity Document.** It carries a SPIFFE ID in a verifiable document, in one of two forms.

| Form | Contents | Primary use |
|---|---|---|
| **X.509-SVID** | An X.509 certificate with the SPIFFE ID in a SAN URI, plus a private key | mTLS mutual authentication |
| **JWT-SVID** | A JWT with the SPIFFE ID in the `sub` claim | Passing identity in HTTP headers, L7 authorization |

**The key property is a short lifetime.** SVIDs are typically issued for tens of minutes to a few hours and renewed automatically. Short lifetimes matter because they **sidestep the revocation problem.** CRLs and OCSP are operationally awkward; if a credential expires soon anyway, the useful window of a compromise is bounded without any revocation mechanism.

### ③ Workload API — the delivery channel for the identity

The interface through which a workload obtains its SVID. Critically, **it is exposed over a Unix Domain Socket (UDS).**

Why UDS is the essence of this design: **the workload presents no credentials at all when it connects to the socket.** Instead the kernel reliably provides the peer process's information (PID, UID, GID), and the SPIRE Agent uses that to **investigate directly** who the peer is.

In other words, this is **not "present a secret to prove identity" but "the platform observes and adjudicates identity."** That is where the bootstrapping problem is solved.

## SPIRE Components

SPIRE is the reference implementation of SPIFFE.

```mermaid
graph TB
    subgraph SRV["SPIRE Server (root of trust)"]
        CA["CA<br/>signs SVIDs"]
        REG["Registration Entries<br/>selector → SPIFFE ID"]
        NA["Node Attestor<br/>(server side)"]
    end

    subgraph NODE["Kubernetes node"]
        AG["SPIRE Agent<br/>(DaemonSet)"]
        WA["Workload API<br/>(Unix Domain Socket)"]
        subgraph POD["Pod"]
            APP["app container"]
            ENV["Envoy sidecar"]
        end
        AG --- WA
    end

    KUBE["kube-apiserver<br/>TokenReview / Pod info"]

    NA <==>|"1. Node Attestation<br/>prove node identity"| AG
    AG -->|"2. Workload Attestation<br/>kernel PID → container → Pod lookup"| KUBE
    APP -.->|"3. request SVID<br/>no credentials presented"| WA
    ENV -.->|"3. request SVID via SDS"| WA
    AG -->|"4. submit selectors"| REG
    REG --> CA
    CA -->|"5. signed X.509 SVID"| AG
    AG -->|"6. deliver SVID<br/>+ auto-renew"| ENV
    ENV ==>|"7. mTLS with SVID<br/>verify peer SVID"| PEER["peer workload's<br/>Envoy"]

    style SRV fill:#eef4fb,stroke:#4a6fa5
    style NODE fill:#f3f7f0,stroke:#6a8f5a
```

| Component | Role |
|---|---|
| **SPIRE Server** | **The root of trust.** Holds the CA and signs/issues SVIDs. Manages Registration Entries (which selectors receive which SPIFFE ID) |
| **SPIRE Agent** (DaemonSet) | Runs on each node. Proves the node's own identity to the Server, then investigates that node's workloads and obtains, delivers, and renews SVIDs on their behalf |
| **Attestation** | The identity adjudication procedure. Two stages: Node Attestation and Workload Attestation |
| **Envoy SDS integration** | Envoy receives certificates from the Agent over the **Secret Discovery Service** protocol. Application code knows nothing about mTLS |

### How attestation resolves the bootstrapping problem

This is the core of SPIRE and the reference point when comparing with IAM.

**Node Attestation** — the Agent proves to the Server "I am this node." The evidence used is **not a pre-planted secret but a platform-issued attestation.** On AWS this is the EC2 instance's signed IMDS document or instance identity document. The Server can validate that evidence against AWS, so no pre-shared secret needs to be placed on the node.

**Workload Attestation** — the Agent investigates workloads on the node:

1. The workload connects to the UDS — **with no credentials**
2. The Agent obtains the peer process's PID from the kernel — **unforgeable.** It is a fact the kernel reports
3. From the PID it reads the cgroup to determine which container this is
4. It queries kubelet/kube-apiserver to confirm that container's Pod, namespace, ServiceAccount, and labels
5. It combines these attributes into **selectors** and submits them to the Server
6. The Server finds the matching SPIFFE ID in the Registration Entries and issues an SVID

**Step 2 is where the bootstrapping problem dissolves.** The workload does not claim who it is. It does not need to. The kernel reports a fact, and that fact is cross-checked against the platform's (Kubernetes') records. **To forge it you would have to compromise the kernel or the Kubernetes API server, and at that level of compromise everything else has already fallen.**

In one sentence: **identity is not presented — it is observed and adjudicated.**

## Comparison With IAM Auth

The Lattice IAM Auth procedure is in [document 03](./03-auth-flow.md). Item by item:

| Item | SPIFFE/SPIRE (AS-IS) | Lattice IAM Auth (TO-BE) |
|---|---|---|
| **Name of identity** | SPIFFE ID (`spiffe://<trust-domain>/ns/<ns>/sa/<sa>`) | IAM Role ARN / assumed-role session ARN |
| **Form of credential** | X.509-SVID or JWT-SVID | STS temporary credentials (access key + secret + session token) |
| **Means of proof** | Proof of certificate private key possession (TLS handshake) | SigV4 request signature (proof of secret key possession) |
| **Scope of proof** | **Connection** — once at setup | **Request** — every request |
| **Who attests** | SPIRE Agent (node) + SPIRE Server | EKS Pod Identity Agent + EKS Auth API |
| **Attestation evidence** | Kernel PID → cgroup → Pod/ServiceAccount lookup | `ServiceAccount` ↔ Role association (EKS Auth API) or OIDC token (IRSA) |
| **Verification method** | The peer's Envoy validates the SVID chain against the trust bundle | Lattice recomputes/compares the signature, then evaluates three policies |
| **Root of trust** | **A SPIRE Server CA operated by the customer** | **AWS IAM / STS** |
| **Credential lifetime** | Tens of minutes to hours, auto-renewed | STS temporary credentials, auto-refreshed |
| **How authorization is expressed** | Envoy authorization filters (SPIFFE ID based) | Three IAM policies (identity-based + service network + service) |
| **Observability** | Envoy metrics/logs (per SPIFFE ID) | Lattice access logs (per principal, no spans) |
| **Operational burden** | **High** — SPIRE Server HA, CA key management, CA rotation, Registration Entry management, Agent deployment/upgrades, trust bundle distribution | **Low** — Pod Identity Agent add-on plus ServiceAccount↔Role association. No CA or key management |
| **Multi-cluster** | Requires trust domain design and federation | Role reuse via Pod Identity, minimal per-cluster setup |
| **Workloads outside AWS** | Possible with suitable SPIRE attestors | Requires a suitable IAM credential provider and supported Lattice connectivity; not an inherent IAM prohibition |

## Similarities — Why This Migration Is Feasible

The comparison table makes them look like entirely different systems, but **structurally they are the same pattern.** That is what makes the migration coherent.

### ① Both use short-lived credentials

Both SVIDs and STS temporary credentials are short-lived and auto-renewed. Both were designed that way for the same reason — **to bound the useful window of a compromise without a revocation mechanism.**

Both approaches can avoid distributing long-lived application secrets, but the review must still cover credential lifetime, renewal, compromise response and authorization. Short lifetime does not remove revocation or emergency-deny requirements.

### ② Both are based on platform attestation

The workload does not hold a secret in advance; the platform vouches for it.

| Stage | SPIRE | EKS Pod Identity |
|---|---|---|
| Node identity | Node Attestation (EC2 identity document, etc.) | The node Role's `AssumeRoleForPodIdentity` permission |
| Workload adjudication | Kernel PID → cgroup → Pod/SA | The Pod's ServiceAccount ↔ Role association |
| Credential delivery | Workload API (UDS) | Pod Identity Agent (link-local address) |
| Credential renewal | Agent renews the SVID | SDK refreshes credentials |

These approaches both use platform evidence, but their selectors, token validation, credential exposure and trust boundaries differ. Validate the actual attestor or credential provider rather than declaring the models equivalent.

**No pre-provisioned long-lived secret is not the same as no runtime secret.** X.509-SVID delivery includes private-key material, and temporary IAM credentials include a secret access key/session token. Protect agent sockets/endpoints, memory, logs and credential caches; attestation is only as strong as its configured trust assumptions.

## Two Decisive Differences

Since there are many similarities, what actually gets debated in a review is **where they differ.** These two are structural differences that operational convenience does not resolve.

### Difference (a) — Bidirectional mutual authentication vs unidirectional plus request authentication

**AS-IS is bidirectional.**

In an mTLS handshake, client and server verify **each other's** SVID. The client confirms "is the peer I connected to really the payments service" by SPIFFE ID, and the server confirms "is the peer connecting to me really the orders service." Both sides prove themselves within the workload identity system.

**TO-BE is asymmetric.**

| Direction | AS-IS | TO-BE |
|---|---|---|
| Client → server (client proves) | SVID mutual authentication | **SigV4 request signature** (per request, finer-grained) |
| Server → client (server proves) | SVID mutual authentication | **TLS server certificate** (ordinary TLS level) |

SigV4 authenticates each request’s signed fields, whereas mTLS authenticates the TLS peer; either design can also apply per-request authorization. Neither is universally stronger. Lattice requires `UNSIGNED-PAYLOAD`, so protect payloads with TLS and consider replay and credential-theft risks explicitly.

**The problem is server proof.** All the client can confirm is "this TLS certificate is valid and the domain matches." **There is no step that confirms "is this really the service that team operates" within a workload identity system.**

The question that actually comes up in a review is:

> Could unauthorized changes to DNS, certificates, service associations or target registration redirect this workload’s traffic? Review those control-plane permissions along with endpoint authentication. A matching display name alone does not transfer an existing generated service DNS identity.

The honest answer is **"not within the workload identity system — you must prevent it with IAM controls over the service network and Lattice resources."** In other words, **the line of defense moves from workload-to-workload mutual authentication to control over resource creation permissions.**

This is not a bad answer. Strictly limiting via IAM who can create Lattice Services, controlling service network associations, and monitoring resource creation with CloudTrail does manage the practical risk. But **if your review documentation said "mutual authentication," that item must be rewritten and the basis for control presented at a different layer.** Discovering this late in the migration causes major schedule slippage.

### Difference (b) — Ownership of the root of trust

**This is the heavier item in financial-sector reviews.**

| Item | AS-IS | TO-BE |
|---|---|---|
| **Root of trust** | A SPIRE Server CA operated by the customer | AWS IAM / STS |
| **CA private key ownership** | Customer or configured upstream CA | No customer Lattice CA; temporary IAM secret credentials still exist |
| **Who issues identity** | The customer's CA, per customer-defined Registration Entries | AWS STS |
| **Who decides issuance rules** | Fully controlled by the customer | Customer controls via IAM; AWS executes |
| **Audit trail** | SPIRE Server logs (customer-held) | CloudTrail (an AWS service) |
| **Who decides CA rotation** | Customer | (N/A) |
| **Works outside AWS** | Depends on attestors and connectivity | Possible with an appropriate credential provider and supported private connectivity; not provided by Pod Identity automatically |
| **Operational burden** | Borne by the customer | Borne by AWS |

The trade-off is explicit: **you hand the operational burden to AWS in exchange for handing over ownership of the root of trust.**

This item is heavy in the financial sector because of regulation and review practice. Many organizations' security standards explicitly require **"the root of trust of an authentication system must be under our own control,"** or contain clauses read that way. Running your own CA was the most direct way to satisfy that requirement, and adopting SPIRE was likely the result of passing that very review.

Moving to Lattice IAM Auth means rebuilding that argument. Available grounds:

| Argument | Content |
|---|---|
| **Shared responsibility model** | IAM/STS are controls AWS already operates under multiple certified regulatory frameworks |
| **Policy authority retained** | Who may call what remains fully defined by the customer through IAM policies |
| **Audit trail secured** | CloudTrail provides credential issuance and API call history; Lattice access logs provide data path history |
| **Reduced CA operation** | AWS handles its service PKI, while the customer still protects temporary credentials, roles, tokens and endpoint keys |
| **Lifetime and attestation preserved** | The two similarities above are still satisfied |

**But this is an argument that "control is exercised differently," not that "it is equivalent."** Whether a reviewer accepts the former depends on organizational standards, and it is not a problem technology can resolve.

### Position as a financial-sector review issue

Summarizing how the review issues line up:

| Item | Review status | Basis |
|---|---|---|
| Avoid baked-in long-lived secrets | Verify configuration | Both can use automatically renewed short-lived credentials |
| Runtime secret exposure | Review required | Short-lived private keys/tokens still require protection |
| Per-request authorization | Compare configured policies | mTLS identity can also feed request-level authorization; SigV4 is not the only way |
| Client identity proof | Changed mechanism | TLS peer proof and request signing have different coverage and threat assumptions |
| **Server identity proof** | ⚠️ **Weakened — compensating control required** | From workload identity system down to TLS server certificate level. Defense moves to IAM control over resource creation |
| **Root of trust ownership** | ⚠️ **Transferred — argument must be rewritten** | Customer CA → AWS IAM/STS |
| End-to-end encryption | Choose the trust boundary | HTTPS terminates at Lattice; passthrough preserves endpoint TLS but not authenticated HTTP SigV4 identity |
| Observability (tracing) | ⚠️ **Weakened** | Envoy spans disappear. Application instrumentation required ([document 01](./01-appmesh-vs-lattice.md)) |
| Workloads outside AWS | Separate design | Evaluate credentials and supported network access rather than assuming impossibility |

Review the changed trust and operational boundaries with the responsible security team. Endpoint mTLS, Lattice authenticated HTTP and anonymous network-context policy provide different controls; choose from actual requirements without asserting that one configuration meets every organization’s review standards.

### The option of keeping SPIRE

Migration does not necessarily mean decommissioning SPIRE.

- For workloads outside AWS, SPIRE may remain useful; other credential/identity approaches can also be evaluated.
- **If you choose the TLS Passthrough configuration**, endpoints must perform mTLS themselves, and SPIRE can keep supplying those certificates
- In that case you end up with a configuration where **App Mesh is gone but SPIRE remains** — responding to App Mesh end of support and keeping SPIRE are separate decisions

If eliminating SPIRE's operational burden was one of the goals of the migration, check first whether the above conditions conflict with that goal.

## Summary

- The three SPIFFE elements are **SPIFFE ID** (a URI-form name), **SVID** (short-lived X.509/JWT), and **Workload API** (over UDS).
- SPIRE's attestation resolves bootstrapping because **identity is not presented but observed and adjudicated.** The PID the kernel reports cannot be forged.
- Both can use short-lived credentials and platform evidence; runtime secrets and policy differences still need review.
- The decisive differences are two: **(a) bidirectional mutual authentication becomes unidirectional plus request authentication, weakening server identity proof**, and **(b) the root of trust transfers from a customer CA to AWS IAM/STS.**
- Neither is resolved by technology; both require organizational judgment. **Review them with security reviewers before starting, because the answer changes the architecture.**

Next: [Constraints and Decision Points](./06-constraints.md) collects the items you must settle before finalizing a design.

## References

- [SPIFFE documentation](https://spiffe.io/docs/latest/spiffe-about/overview/)
- [SPIFFE ID specification](https://github.com/spiffe/spiffe/blob/main/standards/SPIFFE-ID.md) / [X.509-SVID specification](https://github.com/spiffe/spiffe/blob/main/standards/X509-SVID.md)
- [SPIRE Concepts — Attestation](https://spiffe.io/docs/latest/spire-about/spire-concepts/)
- [EKS Pod Identity](https://docs.aws.amazon.com/eks/latest/userguide/pod-identities.html)
- [Secure Cross-Cluster Communication in EKS with VPC Lattice and Pod Identity IAM Session Tags](https://aws.amazon.com/blogs/containers/secure-cross-cluster-communication-in-eks-with-vpc-lattice-and-pod-identity-iam-session-tags/)
- [Istio Security — mTLS](../istio/security/01-mtls.md) — how sidecar-based mutual authentication works
