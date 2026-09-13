# IAM Authentication Flow in Detail

> **Scope**: VPC Lattice service/resource APIs and AWS Gateway API Controller; verify the selected release and installed CRDs.
> **Last Updated**: September 13, 2026

## What This Document Covers

- The four stages a request passes through under Lattice IAM Auth — credential acquisition, request signing, Lattice verification, policy evaluation
- Distinguish credential, signing, policy and network failures using evidence; no failure-frequency ranking is claimed
- What it means to move from connection-scoped mutual authentication to **request-scoped signature verification**

## Why Request Signing?

App Mesh's mTLS checks each side's certificate **once, when the connection is established**, and trusts that connection from then on. Identity is bound to the connection.

Lattice made a different choice: **sign every request and verify every request.** Understanding why makes the later constraints follow naturally.

IAM request signing is one documented identity mechanism shared by AWS compute clients. Lambda can also use certificates with appropriate secret/rotation handling, so do not claim that client certificates there are impossible or use that as an explanation of undocumented AWS design decisions.

So Lattice chose to reuse "the identity system every AWS compute platform already has," and that system operates per **API request**, not per connection. Everything else in this document follows from that choice.

## The Four-Stage Sequence

```mermaid
sequenceDiagram
    autonumber
    participant App as "app container<br/>(Pod)"
    participant Agent as "Pod Identity Agent<br/>(169.254.170.23)"
    participant STS as "EKS Auth API"
    participant Lat as "VPC Lattice<br/>Listener"
    participant IAM as "IAM policy evaluation"
    participant Tgt as "Target<br/>(receiving Pod)"

    rect rgb(235, 243, 252)
    Note over App,STS: Stage 1 — credential acquisition
    App->>Agent: request credentials
    Agent->>STS: AssumeRoleForPodIdentity
    STS-->>Agent: temporary credentials<br/>(AccessKeyId, SecretKey, SessionToken)
    Agent-->>App: temporary credentials (cached)
    end

    rect rgb(238, 249, 240)
    Note over App: Stage 2 — request signing
    App->>App: canonical method/path/query/headers<br/>x-amz-content-sha256: UNSIGNED-PAYLOAD
    App->>App: derive signing key<br/>HMAC-SHA256 x4<br/>service = vpc-lattice-svcs
    App->>App: Authorization header +<br/>x-amz-date + x-amz-security-token
    end

    rect rgb(253, 246, 233)
    Note over App,Lat: Stage 3 — Lattice verification
    App->>Lat: HTTPS request<br/>(dst: 169.254.171.0/24)
    Lat->>Lat: terminate TLS
    Lat->>Lat: parse headers, recompute signature, compare
    end

    rect rgb(252, 238, 238)
    Note over Lat,IAM: Stage 4 — logical evaluation<br/>not a depicted remote IAM RPC
    Lat->>IAM: principal + action(Invoke) + resource + condition
    IAM->>IAM: identity-based policy
    IAM->>IAM: service network auth policy
    IAM->>IAM: service auth policy
    IAM-->>Lat: Allow / Deny
    end

    Lat->>Tgt: forward request
    Tgt-->>Lat: response
    Lat-->>App: response
```

Mapping where a 403 can originate at each stage:

```mermaid
graph LR
    S1["Stage 1<br/>credential acquisition"] --> S2["Stage 2<br/>request signing"]
    S2 --> S3["Stage 3<br/>Lattice verification"]
    S3 --> S4["Stage 4<br/>policy evaluation"]
    S4 --> OK["authorized<br/>target response may vary"]

    S1 -.->|"credential acquisition failure"| E1["local error<br/>request may never be sent"]
    S2 -.->|"Host header mismatch<br/>x-amz-date skew<br/>wrong service name"| E2["403<br/>signature mismatch"]
    S3 -.->|"invalid or expired signed request"| E3["403<br/>verification failed"]
    S4 -.->|"missing identity-based policy<br/>missing auth policy"| E4["403<br/>AccessDenied"]

    style E1 fill:#fdecea,stroke:#d93025
    style E2 fill:#fdecea,stroke:#d93025
    style E3 fill:#fdecea,stroke:#d93025
    style E4 fill:#fdecea,stroke:#d93025
    style OK fill:#e8f5e9,stroke:#1e8e3e
```

## Stage 1 — Credential Acquisition

SigV4 signing needs an access key, a secret key, and a session token. A Pod obtains these in one of two ways.

### EKS Pod Identity vs IRSA

| Item | EKS Pod Identity (recommended) | IRSA |
|---|---|---|
| **Trust relationship setup** | Mediated by the EKS Auth API. Role trust policy references the `pods.eks.amazonaws.com` service principal | Register a per-cluster OIDC provider in IAM and write OIDC conditions into the Role trust policy |
| **Work per additional cluster** | Roles can be reused | Register an OIDC provider and amend trust policies for every cluster |
| **Credential delivery path** | Pod Identity Agent (a node DaemonSet) serves them on a link-local address | Projected service account token → SDK calls `AssumeRoleWithWebIdentity` |
| **Binding mechanism** | `ServiceAccount` ↔ Role association managed via the EKS API | `ServiceAccount` annotation `eks.amazonaws.com/role-arn` |
| **Session tags** | Pod/cluster context can be passed as session tags → usable in conditional authorization | Limited |
| **Prerequisites** | Pod Identity Agent add-on installed + node Role has `AssumeRoleForPodIdentity` | OIDC provider association |

**The practical reason to prefer Pod Identity is multi-cluster.** One of the main motivations for adopting Lattice is cross-cluster communication, and IRSA requires registering an OIDC provider per cluster and managing Role trust policies for as many clusters as you have. Pod Identity does not carry that burden.

### The STS temporary credential dependency

Both approaches ultimately arrive at **temporary credentials issued by STS.** This is an important property of the architecture.

- Credentials **expire.** The SDK caches them and refreshes before expiry, but the refresh path must be alive.
- If the configured credential provider cannot refresh, signing can fail locally; an already-signed expired request can also be rejected. IRSA uses STS, while Pod Identity obtains credentials through the Agent/EKS Auth path.
- In other words, **STS becomes a dependency of the East-West data path.** This mirrors where SPIRE Server sat in AS-IS, but the owner shifts from the customer to AWS (documents [05](./05-spiffe-to-iam.md) and [06](./06-constraints.md)).

The latency implication was covered in [document 02](./02-latency.md) — if refresh blocks the request path, it appears in the p99 tail.

## Stage 2 — Request Signing

### Canonical request → signing key → Authorization header

SigV4 signing proceeds in three steps.

**First, build the canonical request.** Canonicalize method, path, query and signed headers. For Lattice, include **`x-amz-content-sha256: UNSIGNED-PAYLOAD`**; payload signing is not supported. Use HTTPS to protect the body in transit and add application-level integrity when required.

**Second, derive the signing key.** Starting from the secret key, apply HMAC-SHA256 four times in sequence: date → region → **service name** → terminating string. The service name for Lattice is **`vpc-lattice-svcs`**.

Because this service name is an input to the signature itself, **getting it wrong means the signature will not verify.** It is easy to confuse with `vpc-lattice` (the service name for the Lattice control plane API), but data plane requests must be signed with `vpc-lattice-svcs`. This is consistent with the service DNS name itself, which takes the form `<service>-<id>.<hash>.vpc-lattice-svcs.<region>.on.aws`.

**Third, attach the headers.** The `Authorization` header carries the algorithm, credential scope, the list of signed headers (`SignedHeaders`), and the signature value; `x-amz-date` carries the request time; and when using temporary credentials, `x-amz-security-token` carries the session token.

### Three practical pitfalls

#### ① The Host header is signed — beware with custom domains

In SigV4, the `Host` header is **always included in the signature.** Which host the request is addressed to is bound into the signature.

This becomes a problem with **custom domains.** If you attach a customer domain (`api.internal.example.com`) to a Lattice service, the client sends requests to that domain and therefore signs with `Host: api.internal.example.com`. If the value the verifying side expects differs, the signature does not match. Conversely, if you signed with the Lattice-generated domain but the actual request's Host is the custom domain, it also does not match.

**The core rule: the Host value used when signing must match the actual request's Host header.** When introducing a custom domain, explicitly confirm which value your signing logic uses. This problem surfaces **at the moment you attach the custom domain**, not at the start of migration, which is why it is easy to miss.

#### ② x-amz-date clock skew

The general AWS SigV4 guide says that requests **in most cases** must arrive within five minutes of their timestamp. Keep clocks synchronized and inspect the actual expiry/skew error; this is not a separately measured Lattice-specific guarantee.

That makes **node clock synchronization a precondition for authentication.** On EC2/EKS nodes using the Amazon Time Sync Service this is usually a non-issue, but it becomes a problem when:

- Node or hybrid-host time synchronization is misconfigured
- An application signs with an incorrect timestamp or timezone
- The host resumes with clock drift

This failure is **intermittent and node-scoped**, making it awkward to diagnose. If "only Pods on one particular node get 403s," check clock synchronization first.

#### ③ Intermediate proxies mutating headers — sign at the last hop

Because the signature is bound to request content, **if anything modifies a signed element after signing, verification breaks.**

Things that actually cause this:

- Proxies that change signed paths or the actual `Host` value
- Proxies that add/remove query parameters or alter values/encoding; merely reordering equivalent parameters does not necessarily change the canonical query
- Body mutation is not detected by Lattice SigV4 when using the required `UNSIGNED-PAYLOAD`; protect it with TLS and application controls

**The rule: sign at the last hop before Lattice.** No layer that modifies the request may sit between signing and Lattice.

This matters especially **when signing via an egress proxy.** The aws-samples reference implementation demonstrates the pattern — a `sigv4proxy` sidecar listening on 8080, with an init container using iptables to redirect **only traffic destined for `169.254.171.0/24` (the Lattice range)** to local port 8080. The proxy signs and the request goes straight out to Lattice, so nothing sits in between to mutate it. Avoid configurations where a signed request is then handled by another proxy.

## Stage 3 — Lattice Verification

On an HTTPS listener, Lattice **terminates TLS, parses the headers**, recomputes the signature in the `Authorization` header, and compares.

The single most important constraint of this architecture hides here.

> **Signature verification requires reading headers, and reading headers requires terminating TLS.**

**TLS Passthrough does not terminate TLS, so Lattice cannot see the `Authorization` header** and cannot authenticate the caller's SigV4 request signature. This is the constraint discussed in [document 06](./06-constraints.md). It does not prohibit every auth policy: TLS listeners support policies limited to anonymous principals, which do not establish authenticated caller identity.

The controller documents policy attachments for Gateway, HTTPRoute and GRPCRoute; check the installed CRD for supported attachment targets. **That controller restriction is not a statement that every VPC Lattice TLS auth policy is rejected.**

::: tip Documented TLS behavior
AWS permits TLS-passthrough auth policies based on **anonymous principals**, without authenticated SigV4 identity or HTTP header/path inspection. TLS listeners require a custom domain matching plaintext SNI and TCP target groups; ECH/ESNI is not supported. This repository does not recommend wildcard-principal policy examples. See the [TLS listener reference](https://docs.aws.amazon.com/vpc-lattice/latest/ug/tls-listeners.html).
:::

Authenticated request signing and anonymous network-context authorization are different controls. Design the endpoint authentication and the applicable service-network/service policies explicitly.

One more pitfall: **auth policies are only active when authType is `AWS_IAM`.** With `NONE`, an attached policy is inert. This is the most common cause of "I attached a policy but anyone can still get through."

## Stage 4 — Policy Evaluation

For an authenticated principal, evaluate the caller permissions and each applicable Lattice resource policy. **Only resources configured with `AWS_IAM` enforce their auth policy; `NONE` skips that resource policy.** Explicit denies and other IAM controls still apply. Do not turn the three-policy diagram into a universal rule for anonymous or differently configured requests.

| Policy | Attached to | Question it answers | Owner | Gateway API resource |
|---|---|---|---|---|
| **identity-based policy** | The caller's IAM Role | "Does this Role have permission to perform `vpc-lattice-svcs:Invoke`?" | Application / platform team | — (directly in IAM) |
| **service network auth policy** | Service Network | "Is this principal allowed into this service network?" (coarse-grained) | Network / cloud administrator | `IAMAuthPolicy` → `Gateway` |
| **service auth policy** | Lattice Service | "Is this principal allowed to call this service?" (fine-grained) | Service-owning team | `IAMAuthPolicy` → `HTTPRoute`/`GRPCRoute` |

For **service invocation auth policies**, the action is `vpc-lattice-svcs:Invoke`. Resource configurations use a separate access model and do not inherit service-network auth policies.

### Available condition keys

These keys can be used as conditions in auth policies. Which keys are present at evaluation time depends on the protocol and on whether the request was SigV4-signed.

| Condition key | Filters by |
|---|---|
| `vpc-lattice-svcs:Port` | The service port the request was made to |
| `vpc-lattice-svcs:RequestMethod` | The request method |
| `vpc-lattice-svcs:RequestPath` | The path portion of the request URL |
| `vpc-lattice-svcs:RequestHeader/<header-name>` | A header name-value pair in the request |
| `vpc-lattice-svcs:RequestQueryString/<key-name>` | A query string key-value pair in the request URL |
| `vpc-lattice-svcs:ServiceArn` | The ARN of the target Lattice service |
| `vpc-lattice-svcs:ServiceNetworkArn` | The ARN of the service network |
| `vpc-lattice-svcs:SourceVpc` | The VPC the request originated from |
| `vpc-lattice-svcs:SourceVpcOwnerAccount` | The account owning the source VPC |

IAM global condition keys such as `aws:PrincipalOrgID` and `aws:PrincipalTag/<key>` can also be used alongside these.

::: warning Needs verification
The list above is compiled from the [service authorization reference](https://docs.aws.amazon.com/service-authorization/latest/reference/list_vpc-lattice-svcs.html) and policy examples in the Gateway API Controller documentation. Lattice gains features over time, so **confirm the current list in that reference before finalizing a design.**
:::

Having path, method, and header conditions is practically useful — you can enforce a rule like "only these Roles may call `POST /refund` on the payments service" outside application code. That said, **putting path-based authorization into auth policies means API changes trigger policy changes**, so decide deliberately which layer expresses authorization.

### The dominant 403 failure pattern

A missing `vpc-lattice-svcs:Invoke` permission is **one documented cause** of an authenticated request failing. No incident-frequency dataset was supplied, so it is not ranked as the most common cause.

It is common because it is counterintuitive. It is natural to think "the service's auth policy allows this Role, so we're done" — but **the calling Role itself also needs Invoke permission.** A resource policy alone does not get you through.

Here is the actual error message from the reference implementation:

```text
AccessDeniedException: User: arn:aws:sts::111122223333:assumed-role/eksctl-...-Role1-yz1hNJittmXj/1726632845600682009
is not authorized to perform: vpc-lattice-svcs:Invoke
on resource: arn:aws:vpc-lattice:us-west-2:111122223333:service/svc-0b13d4b53748cbdc7/catalogdetail
because no identity-based policy allows the vpc-lattice-svcs:Invoke action
```

The last clause — **`because no identity-based policy allows...`** — is the key to diagnosis. The message tells you which policy is missing, so read it first when you hit a 403.

### 403 diagnosis order

| Order | What to check | How |
|---|---|---|
| 1 | The last clause of the error message | `no identity-based policy` → caller Role permissions; otherwise → auth policy |
| 2 | Lattice access logs and the returned error | Correlate request ID, caller logs, policy and network evidence |
| 3 | Was the request actually signed? | An unsigned request and a failed signature are different problems. Check egress proxy logs |
| 4 | Is authType `AWS_IAM`? | With `NONE`, policies are inert |
| 5 | Node clock | If only one node fails, suspect `x-amz-date` skew |
| 6 | Host header | If you just introduced a custom domain, start here |

### An easily missed pitfall: calling the k8s Service DNS directly bypasses authorization

The AWS Gateway API Controller documentation states this explicitly:

> `IAMAuthPolicy` can only perform authorization for traffic that travels **through Gateways, HTTPRoutes, and GRPCRoutes.** The authorization will not take effect if the client sends traffic directly to the k8s service DNS.

Calling `http://proddetail.prodcatalog-ns.svc.cluster.local` directly **bypasses the Lattice data path**, so its auth policy does not evaluate that request. This is a design boundary, not a measured ranking of incident causes.

During the migration window, when the AS-IS path (direct in-cluster calls) and the TO-BE path (via Lattice) coexist, **there are simultaneously paths where authorization applies and paths where it does not.** You need compensating controls such as NetworkPolicy to block direct in-cluster calls, and that belongs in the migration plan.

## AS-IS Comparison

| Item | AS-IS: App Mesh + SPIRE mTLS | TO-BE: Lattice IAM Auth |
|---|---|---|
| **Authentication scope** | **Connection** — once at connection setup | **Request** — every request |
| **Directionality** | **Bidirectional mutual authentication** (both client and server prove identity) | **Unidirectional** — the client proves itself. The server proves only via its TLS server certificate |
| **Form of identity** | SPIFFE ID in an X.509 SVID (a URI) | IAM Role ARN / assumed-role session ARN |
| **Means of proof** | Short-lived X.509 certificate (proof of private key possession) | SigV4 signature (proof of secret key possession) |
| **Who verifies** | The peer workload's Envoy | Lattice (AWS-managed infrastructure) |
| **Root of trust** | A SPIRE Server CA operated by the customer | AWS IAM / STS |
| **Where authorization happens** | The receiving Envoy's authorization filter | Lattice's triple policy evaluation |
| **Where TLS terminates** | The receiving Pod's Envoy | Lattice (HTTPS listener) |
| **On credential expiry** | SVID auto-renewal (SPIRE Agent) | STS credential auto-refresh (SDK) |
| **Observability** | Envoy metrics + logs | Lattice access logs (no spans) |

### The two most important rows

**The "Directionality" row** is the crux of the review board issue. mTLS had the server prove its identity too. Under Lattice IAM Auth, server-side identity proof is at the level of a TLS server certificate, and there is no step that confirms "is this really the service that team operates" within a workload identity system. Details are in [document 05](./05-spiffe-to-iam.md).

The client-to-Lattice HTTPS connection terminates at Lattice. The target protocol is a separate setting: HTTP is plaintext on that segment, and HTTPS adds encryption without Lattice validating the target certificate. Endpoint TLS/mTLS through passthrough changes the trust boundary and cannot expose encrypted HTTP SigV4 identity to Lattice.

## Summary

- Lattice chose request signing to reuse the **IAM/STS foundation that EKS, ECS, EC2, and Lambda already share.** That system operates per request, not per connection.
- The signing service name is **`vpc-lattice-svcs`**, and since it is an input to the signature, getting it wrong means verification fails.
- Three practical pitfalls: **the Host header is signed** (beware with custom domains), **x-amz-date 5-minute skew** (node clock sync), and **sign at the last hop** (no mutating proxies in between).
- TLS passthrough cannot authenticate encrypted HTTP SigV4 headers, but AWS supports anonymous network-context auth policies for that path.
- Missing Invoke permission is one possible 403 cause; use the returned reason and correlated logs rather than an unsupported frequency ranking.
- **Calling the k8s Service DNS directly bypasses auth policy evaluation.** Compensating controls are needed during migration.

Next: [Foundations — Link-Local and SNI](./04-networking-basics.md) goes one layer below "why you must terminate TLS to see headers."

## References

- [Control access to VPC Lattice services using auth policies](https://docs.aws.amazon.com/vpc-lattice/latest/ug/auth-policies.html)
- [Actions, resources, and condition keys for Amazon VPC Lattice Services](https://docs.aws.amazon.com/service-authorization/latest/reference/list_vpc-lattice-svcs.html)
- [AWS Gateway API Controller — IAMAuthPolicy API Reference](https://www.gateway-api-controller.eks.aws.dev/latest/api-types/iam-auth-policy/)
- [aws-samples — Securing the network and implementing AWS IAM authentication](https://github.com/aws-samples/migrating-from-aws-app-mesh-to-amazon-vpc-lattice/blob/main/vpc-lattice-config/IAMAUTH.md)
- [Implement AWS IAM authentication with Amazon VPC Lattice and Amazon EKS](https://aws.amazon.com/blogs/containers/implement-aws-iam-authentication-with-amazon-vpc-lattice-and-amazon-eks/)
- [EKS Pod Identity](https://docs.aws.amazon.com/eks/latest/userguide/pod-identities.html) / [IAM Roles for Service Accounts](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html)
- [Signing AWS API requests (SigV4)](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_sigv.html)


- [Lattice SigV4 authenticated requests](https://docs.aws.amazon.com/vpc-lattice/latest/ug/sigv4-authenticated-requests.html) — required unsigned payload header and validity window
