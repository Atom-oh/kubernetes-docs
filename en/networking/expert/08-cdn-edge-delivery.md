# 08. CDN and Edge Delivery Design

> **Last Updated**: November 19, 2026
> **Lab boundary**: Read-only observation. The exercise sends a few `curl` requests to a public CloudFront-served asset; this workbook creates no distribution, origin, VPC or load balancer.
> **Verification status**: The Amazon CloudFront Developer Guide, AWS Knowledge Center pages and RFC 9111/5861 were checked. While writing, headers from one public CloudFront-served asset were observed and **only Hit responses were seen** (no Miss was captured); no distribution was **configured or measured**.

After this workbook, you should be able to predict **where a request is answered** (edge POP, regional edge cache, Origin Shield or the origin), explain from response headers why it was answered there, and draw the edge-to-origin path so that the origin is reachable only through CloudFront.

This chapter assumes the basics. DNS caching and TTL behavior are in [Network Fundamentals Part 3](../../basics/06-network-fundamentals-part3.md), including [how an HTTP/1.1 message is structured](../../basics/06-network-fundamentals-part3.md#http11-message-structure); the TLS handshake, SNI and termination points are in [Part 2](../../basics/06-network-fundamentals-part2.md); and the CloudFront, ALB and ACM roles are mapped in [Part 4](../../basics/06-network-fundamentals-part4.md). Part 3 covers DNS caching but not HTTP caching, so section 6 defines the HTTP cache terms this chapter needs. Anycast routing with BGP builds on [workbook 02](02-routing-policy-convergence.md), and the private connectivity behind an origin on [workbook 07](07-wan-hybrid-connectivity.md).

**Readiness:** a shell with `curl` and an internet connection. No AWS account is needed. Building the reference design yourself incurs CloudFront requests and data transfer, invalidation paths beyond the free allowance, Origin Shield requests, load balancer hours and instance hours; **that cost and the cleanup are the learner's own**. Do not create resources outside an existing, approved lab account.

## 1. Read with a question to answer

Exam scope only decides what to read. Numbers and behaviors come from the official documents in the first column.

| Reading | Exam scope it maps to | Question to answer in your own words |
|---|---|---|
| [How CloudFront delivers content](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/HowCloudFrontWorks.html), [Origin Shield](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/origin-shield.html) | ANS-C01 Domain 1 Network Design, Task 1.1 (edge network services) | Which requests skip the regional edge cache, and which skip Origin Shield? |
| [Understand the cache key](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/understanding-the-cache-key.html), [Control origin requests with a policy](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/controlling-origin-requests.html) | ANS-C01 Domains 1 and 2 (Network Implementation) | What should the origin receive that must **not** be in the cache key? |
| [Manage how long content stays in the cache](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/Expiration.html), [RFC 9111](https://www.rfc-editor.org/rfc/rfc9111.html), [RFC 5861](https://www.rfc-editor.org/rfc/rfc5861.html) | ANS-C01 Domain 2; protocol principles | Who wins when the origin's `s-maxage` and the cache policy's maximum TTL disagree? |
| [Restrict access with VPC origins](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/private-content-vpc-origins.html), [Restrict access to an Amazon S3 origin](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/private-content-restricting-access-to-s3.html) | ANS-C01 Domain 4 Network Security, Compliance, and Governance | What makes the origin unreachable except through CloudFront? |
| [View CloudFront metrics](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/viewing-cloudfront-metrics.html), [Standard log fields](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/standard-logs-reference.html) | ANS-C01 Domain 3 Network Management and Operation | Which field tells a POP hit from an Origin Shield hit? |

After reading, draw viewer, POP, regional edge cache, Origin Shield (if used) and origin, with **cache tiers** and **connection legs** as different line styles. Each leg has its own TCP or QUIC connection and its own TLS session, so "HTTPS end to end" is a claim about every leg, not one.

## 2. Why a CDN

A CDN changes three things, and a design should say which one it is buying.

| Goal | Mechanism | Limit to state in a design |
|---|---|---|
| **Lower latency (RTT)** | The viewer's TCP/QUIC and TLS handshakes end at a nearby POP instead of a distant origin; a cache hit removes the origin round trip entirely | A miss still pays the POP-to-origin path. Part 2 showed that a full TLS 1.3 handshake costs about 1 RTT; that RTT is now the short viewer-to-POP one |
| **Origin offload** | Hits never reach the origin; regional edge caches, Origin Shield and request collapsing reduce the misses that do | The hit ratio depends on the cache key and TTLs you choose (sections 5 and 6), not on the CDN alone |
| **Absorption** | Traffic lands on a large distributed edge instead of one origin | Absorption protects the origin only if the origin cannot be reached around the CDN (section 9). Volumetric and L7 attack defenses are the topic of the next workbook, [edge security](./09-edge-security-waf-ddos.md) |

CloudFront routes each request to the edge location that can best serve it, typically the one with the lowest latency, and carries origin traffic over the AWS network.

## 3. Request steering: DNS-based and anycast

Something must decide **which POP** a viewer talks to. There are two common methods.

| Method | How the POP is chosen | Failover and granularity | Where it shows up |
|---|---|---|---|
| **DNS-based** | The CDN's authoritative DNS answers the viewer's resolver with the address of a suitable POP | Changes take effect as resolvers re-query, subject to cached answers (Part 3: lowering a TTL now does not shorten an answer already cached). The authoritative server sees the **resolver's** address, not the viewer's, unless the resolver passes client subnet information ([RFC 7871](https://www.rfc-editor.org/rfc/rfc7871.html)) | CloudFront default: "DNS routes the request to the CloudFront POP (edge location) that can best serve the request" |
| **Anycast** | Many sites announce the **same** prefix over BGP; ordinary routing delivers each packet to the topologically closest announcer ([RFC 4786](https://www.rfc-editor.org/rfc/rfc4786.html)) | Failover follows BGP withdrawal and convergence (workbook 02). RFC 4786 warns that node selection must stay stable for longer than a transaction, because a routing change can send the rest of a session to a different node | CloudFront **Anycast static IPs**: an opt-in list of dedicated static IPv4 (or IPv4 and IPv6) addresses, for allowlisting or for pointing an apex domain with A records; works with SNI |

**In practice:** with DNS steering, a viewer behind a distant resolver may land on a POP far from the viewer. With anycast, "closest" means fewest or most-preferred BGP hops, not lowest latency. Neither method guarantees that two consecutive requests reach the same POP or the same server, which matters for the exercise in section 11.

## 4. Cache hierarchy: POP, regional edge cache, Origin Shield, origin

**How a GET is served:**

1. DNS routes the viewer to a POP. If the object is cached and valid there, the POP returns it.
2. On a POP miss, the POP **typically** asks the nearest **regional edge cache**. Regional edge caches have a larger cache than an individual POP, so objects that are no longer popular enough to stay at a POP stay cached longer here.
3. On a regional miss, CloudFront forwards the request to the origin (through Origin Shield if enabled). The response returns via the regional edge cache to the POP, and **both** store a copy. CloudFront starts forwarding as soon as the first byte arrives.

![CDN cache MISS then HIT animation. ① Client A resolves the distribution name; DNS answers with the edge POP that has the lowest latency, and A sends GET /img/logo.png. ② The edge POP has no object for that cache key, so it is a MISS; it asks the regional edge cache, which also misses. ③ The origin, an internal ALB reached through a CloudFront VPC origin, returns 200 with Cache-Control: max-age=3600. ④ On the way back the regional edge cache and the POP each store a copy, and client A receives x-cache: Miss from cloudfront. ⑤ Client B asks the same POP for the same object: it is a HIT, the POP answers from its cache with Age: 42 and x-cache: Hit from cloudfront, and no request reaches the origin.](../../.gitbook/assets/en-networking-expert-08-cdn-edge-delivery-anim-0.svg)

**Requests that skip the regional edge cache** (Developer Guide):

- Proxy HTTP methods `PUT`, `POST`, `PATCH`, `OPTIONS` and `DELETE` go directly from the POP to the origin.
- Dynamic requests, as determined at request time, go directly to the origin.
- When the origin is an S3 bucket and the request's optimal regional edge cache is in the same Region as the bucket, the POP goes directly to the bucket.

Regional edge caches have feature parity with POPs: an invalidation removes the object from both.

**Origin Shield** is an optional extra layer between the regional edge caches and the origin. All requests from all CloudFront caching layers to the origin go through it, so each object can be fetched with as few as one origin request; requests made in the same Region as the origin bypass it. Choose the Origin Shield Region with the lowest latency to the origin (it is offered only where CloudFront has a regional edge cache). It is charged per request that goes to Origin Shield as an **incremental** layer: dynamic requests (`PUT`, `POST`, `PATCH`, `DELETE`, and `GET`/`HEAD` with a TTL under 3600 seconds or caching disabled) always count, while cacheable requests count only when they arrive from a regional edge cache in a different Region. AWS lists dynamic proxied content, low cacheability and infrequently requested content as poor fits.

**Request collapsing:** if more requests for the same cache key arrive while the first miss is still waiting on the origin, CloudFront pauses them and answers all of them with the first response. Only requests with the same cache key collapse. In logs, the first appears as `Miss` and the collapsed ones as `Hit`.

## 5. Cache key design and hit ratio

The **cache key** is the unique identifier of an object in the cache. A hit occurs when a request produces the same cache key as a prior request and that object is cached and valid. RFC 9111 defines the minimum key as the request method and target URI, with `Vary` adding request headers.

**CloudFront default:** the distribution's domain name and the URL path. Query strings, headers and cookies are **not** in the key by default. The Developer Guide shows two requests for `/content/stories/example-story.html` with different query strings, `User-Agent`, `Referer` and `session_id` cookie: the second is still a hit. Responses to `OPTIONS` are cached separately from `GET` and `HEAD`.

**Two policies, two jobs:**

| Policy | Controls | Rule |
|---|---|---|
| **Cache policy** | What goes into the cache key, plus min/default/max TTL | Include a value only when it changes the response |
| **Origin request policy** | What the origin receives on a miss, **without** adding it to the key | Everything in the cache key is automatically forwarded; use this policy for values the origin needs but the cache must not split on (analytics, telemetry) |

An origin request always includes the URL path, any body, and the headers CloudFront adds automatically such as `Host`, `User-Agent` and `X-Amz-Cf-Id`.

**What splits the key, and what to do instead:**

| Candidate | Problem | Alternative |
|---|---|---|
| `Accept-Language` | `en-US,en`, `en,en-US`, `en-US, en` and `en-US` all mean English but create separate objects | Put the language in the URL (`/en-US/...`) |
| `User-Agent` | Thousands of variants | Leave it out of the key |
| Session cookies | Unique per user, so each user gets a private copy | Leave them out of the key, or mark the response non-cacheable |
| Query strings the origin ignores | Duplicate objects | Exclude them, or include only named parameters |

**Hit ratio** is the proportion of viewer requests that are hits. Raise it by including only the minimum necessary values in the key, by longer TTLs where freshness allows, and with Origin Shield when viewers are spread across regions.

## 6. TTL, Cache-Control and invalidation

**HTTP cache terms used here** (RFC 9111): a stored response is **fresh** until its freshness lifetime passes, then **stale**. A shared cache (a CDN) computes the lifetime from the first of `s-maxage`, then `max-age`, then `Expires` minus `Date`. Using a stale response normally requires **validation** with the origin (a conditional request that can return `304 Not Modified`). The `Age` header is the sender's estimate of the seconds since the response was generated or validated at the origin; its presence implies the origin did not generate the response for this request. A response stays fresh while its freshness lifetime is greater than its current age, so the time left is the lifetime minus `Age`. `no-cache` means a stored response must not be reused without successful validation; `no-store` means do not store it.

**How CloudFront combines origin headers with the cache policy TTLs:**

| Origin sends | Minimum TTL = 0 | Minimum TTL > 0 |
|---|---|---|
| `Cache-Control: max-age` | CloudFront caches for the lesser of `max-age` and the maximum TTL | Clamped: below the minimum TTL uses the minimum; above the maximum uses the maximum |
| `max-age` **and** `s-maxage` | CloudFront uses `s-maxage` (capped by the maximum TTL); browsers use `max-age` | `s-maxage` clamped between minimum and maximum TTL |
| No `max-age` | Default TTL | The greater of minimum and default TTL |
| `Expires` | Until that date or the maximum TTL, whichever is sooner | Clamped between minimum and maximum TTL |
| `no-cache`, `no-store` and/or `private` | CloudFront and browsers respect the headers | CloudFront caches for the **minimum TTL** anyway |

Other rules:

- If both `max-age` and `Expires` are present, CloudFront uses only `max-age`.
- A viewer's `Cache-Control` or `Pragma` in a GET cannot force CloudFront back to the origin; CloudFront ignores them.
- Without a cache policy (legacy settings), the default TTL is 24 hours.
- **Trap:** with a minimum TTL above 0, an origin that sends `no-cache` still gets cached for the minimum TTL. If the origin later becomes unreachable and the minimum **or** maximum TTL is above 0, CloudFront serves the object it fetched earlier, so lowering only the minimum TTL does not stop it. Add `Cache-Control: stale-if-error=0` to the origin's response to make CloudFront return an error instead.

**Serving stale on purpose:** CloudFront supports the [RFC 5861](https://www.rfc-editor.org/rfc/rfc5861.html) extensions.

- `max-age=3600, stale-while-revalidate=600`: after one hour, CloudFront serves the stale copy for up to 10 minutes while it fetches a fresh one in the background.
- `max-age=3600, stale-if-error=86400`: if the origin is unreachable or returns a 5xx error after one hour, CloudFront keeps serving the stale copy for up to 24 hours.
- Either way, stale content is served only up to the lesser of the directive and the **maximum TTL**.

**Invalidation versus versioned file names:**

| | Invalidation | Versioned names (`app.3f9c.js`) |
|---|---|---|
| Effect | Removes the object from POPs and regional edge caches; the next request goes to the origin | A new URL is a new cache key; old and new coexist |
| Browser and corporate proxy caches | Not affected: users may keep the old copy until it expires there | The page references the new name, so every cache fetches it |
| Cost | First 1,000 invalidation paths per month free per account, then per path; a `*` wildcard path counts as one path however many files it removes | No invalidation charge; you still pay to transfer new versions to the edge |
| Rate quotas | 150 paths or tags per second and 1 wildcard invalidation per second (Developer Guide quotas page) | None |
| Rollback | Invalidate again | Point the page back to the old name |

AWS recommends versioned file names for files you update frequently. The CloudFront FAQ and a Knowledge Center article still describe the older "in progress at one time" limits (3,000 individual files and 15 wildcard paths per distribution); the Developer Guide quotas page is the current source, so check it on the day you design.

## 7. TLS at the edge and to the origin

The viewer leg and the origin leg are two separate TLS sessions (Part 2: termination does not encrypt the next hop).

**Viewer to CloudFront:**

- The viewer protocol policy can allow HTTP and HTTPS, redirect HTTP to HTTPS, or require HTTPS only.
- An ACM certificate for a CloudFront distribution must be requested or imported in **US East (N. Virginia)**; CloudFront distributes it to its locations.
- HTTP/2 requires a viewer that supports TLS 1.2 or later and SNI; HTTP/3 requires TLS 1.3 and SNI.

**CloudFront to the origin:**

- The origin protocol policy is HTTP only, HTTPS only, or match viewer (choose match viewer only when the viewer policy is redirect-to-HTTPS or HTTPS only).
- The origin certificate must match the origin domain name in the distribution, or the `Host` header if you forward it. CloudFront also sends that name as SNI. A certificate that does not match, is not from a trusted CA, has a broken chain or has expired makes CloudFront drop the connection and return `502` to the viewer.
- For an ALB origin, the certificate on the ALB lives in **the ALB's Region**, separate from the us-east-1 viewer certificate.
- With a **VPC origin**, CloudFront reaches the internal ALB by its ARN, not by a public DNS lookup; the hostname you configure is used for SNI and certificate matching only, so no public DNS record has to point at the internal ALB (AWS Networking blog, 2026).

**In practice:** record, per leg, the protocol, the certificate and its Region, the minimum TLS version and who renews the certificate. "HTTPS" in a design review means both rows are filled in.

## 8. Dynamic acceleration, HTTP/2 and HTTP/3

Not everything is cacheable, and a CDN still helps uncacheable traffic:

- **Short viewer handshakes:** the TCP/QUIC and TLS handshakes run against a nearby POP.
- **Persistent origin connections:** after a response, CloudFront keeps the origin connection open for several seconds (configurable keep-alive timeout for custom and VPC origins) so the next request skips a new TCP and TLS handshake.
- **AWS network:** traffic between the edge and an origin in an AWS Region stays on the AWS network.
- **Dynamic requests skip the regional edge cache** (section 4), so they are not slowed by an extra cache lookup.

**Protocol versions by leg:**

| Leg | Versions | Notes |
|---|---|---|
| Viewer ↔ CloudFront | HTTP/1.0 and 1.1 on by default; HTTP/2 and HTTP/3 can be turned on | HTTP/3 runs on QUIC over UDP, and CloudFront supports connection migration so a viewer can switch networks without losing the connection |
| CloudFront → custom origin | HTTP/1.1 | HTTP/2 multiplexing on the viewer side does not reach the origin; plan origin connection capacity accordingly |

HTTP/2 and HTTP/3 keep HTTP semantics and change framing (Part 3), so a cache key and TTL behave the same on every version.

## 9. CloudFront mapping and the edge-to-origin path

| Concept | CloudFront feature | Design note |
|---|---|---|
| Cache key and TTL | Cache policy | Minimum values in the key; TTLs per behavior |
| Forward without splitting the cache | Origin request policy | Values the origin needs but the cache must not vary on |
| Per-path behavior | Cache behaviors (path patterns) | For example `/assets/*` long TTL with versioned names, `/api/*` caching disabled |
| Private S3 origin | Origin access control (OAC) | Recommended over the legacy OAI |
| Private ALB, NLB or EC2 origin | VPC origin | The house reference design below |

**OAC for S3:** CloudFront signs origin requests and the bucket policy allows only that distribution. AWS recommends OAC over OAI because it supports S3 buckets in all Regions (including opt-in Regions launched after December 2022), SSE-KMS and dynamic requests (`PUT`, `DELETE`). With OAC, S3 Object Ownership must be **Bucket owner enforced** (the default for new buckets). An S3 **website endpoint** is a custom origin and cannot use OAC.

<a id="edge-origin-path"></a>

### Edge-to-origin path: VPC origin to an internal ALB

**The reference design:** CloudFront → **VPC origin** → **internal** ALB in private subnets → target group. The origin has no public address, and its only ingress is from CloudFront. Do not put an internet-facing load balancer behind CloudFront, and never add an inbound rule that admits a public CIDR to the origin.

![Edge-to-origin path animation. ① A viewer sends a cacheable GET /menu.json over HTTPS; TLS ends at the edge POP, and the request misses at both the POP and the regional edge cache. ② CloudFront connects to the origin through the VPC origin: a service-managed ENI in a private subnet (for example 10.0.11.25) opens the connection to the internal ALB (10.0.12.40). ③ The ALB security group admits only traffic from CloudFront-VPCOrigins-Service-SG (or the CloudFront origin-facing managed prefix list). ④ The ALB listener forwards to the target group, whose targets accept traffic only from the ALB security group. ⑤ An internet client tries to reach the ALB directly and fails: an internal ALB has only private addresses, so nothing on the internet routes to it and the attempt never reaches the VPC. The VPC has an internet gateway attached, but it is not used to route this path.](../../.gitbook/assets/en-networking-expert-08-cdn-edge-delivery-anim-1.svg)

**VPC origin requirements** (Developer Guide):

- **Origin types:** an ALB, an NLB or an EC2 instance in a private subnet, fully deployed and Active. Gateway Load Balancers and NLBs with TLS listeners cannot be origins, and an NLB must have a security group attached.
- **VPC:** the VPC must have an **internet gateway attached**; it denotes that the VPC can receive traffic from the internet but is **not used to route** to the origin, and no route table change is needed.
- **Subnet:** CloudFront creates a service-managed ENI in the private subnet, which needs at least one free IPv4 address (and one IPv6 address for dual-stack).
- **Security group:** the origin must have one. Allow inbound from either the **CloudFront managed prefix list** (`com.amazonaws.global.cloudfront.origin-facing`, plus the IPv6 list for dual-stack), which can be added beforehand, or the service-managed **`CloudFront-VPCOrigins-Service-SG`**, available after the VPC origin is created and more restrictive because it admits only your distributions. Do not edit that group or create your own with that name prefix.
- **Not supported:** gRPC, Lambda@Edge origin request and origin response triggers. Inbound NACL rules are not evaluated for CloudFront-to-origin traffic, but **outbound** NACL rules are evaluated on the return path and must allow ephemeral TCP ports 1024–65535 toward the CloudFront origin-facing ranges.
- **Quotas:** 25 VPC origins per account (adjustable) and 50 distributions per VPC origin.

**Why an internal ALB cannot be reached around CloudFront:** the nodes of an internal load balancer have only private IP addresses. Its DNS name is publicly resolvable, but it resolves to those private addresses, so only clients with access to the VPC can reach it. That is a routing property, not a filter, and it holds even if a security group rule is later loosened. If the ALB comes from a Kubernetes Ingress, the [AWS Load Balancer Controller](../03-aws-lb-controller.md) sets it with `alb.ingress.kubernetes.io/scheme: internal`.

**Prefix list or service security group:** the managed prefix list contains all CloudFront origin-facing servers, so it admits **any** distribution; the VPC origin service group admits only yours. As an inbound rule the prefix list counts with a weight of 55 rules toward the security group rule quota. [WAF, Edge and API Security](../../security/14-waf-edge-api-security.md) covers WAF placement and compares this design with the weaker public-ALB origin (prefix list plus a secret header), which the house reference design does not use; the next workbook, [edge security](./09-edge-security-waf-ddos.md), builds the attack-side view on top of this path.

## 10. Observability: what each signal proves

| Signal | Where | What it tells you |
|---|---|---|
| `x-cache` response header | Viewer response | `Hit from cloudfront`, `RefreshHit from cloudfront` (expired copy revalidated with the origin) or `Miss from cloudfront` |
| `Age` | Viewer response | Seconds since the copy was generated or validated at the origin; `Date` plus `Age` is roughly the current time on a hit |
| `x-amz-cf-pop` | Viewer response | The POP that answered; compare it across requests before concluding anything from a second Miss |
| `Via` | Viewer response | The intermediaries that handled the message ([RFC 9110](https://www.rfc-editor.org/rfc/rfc9110.html)); the server identifier can differ between two requests to the same POP |
| `x-edge-result-type` | Standard logs | `Hit`, `RefreshHit`, `Miss`, `LimitExceeded`, `CapacityExceeded`, `Error`, `Redirect`; WebSocket and gRPC are always `Miss` |
| `x-edge-detailed-result-type` | Standard logs | `OriginShieldHit` when Origin Shield served it (a request routed to the regional edge cache acting as Origin Shield is logged as `Hit`) |
| `time-to-first-byte` | Standard logs | Seconds from receiving the request to writing the first byte, measured on the server |
| Cache hit rate, origin latency | CloudWatch additional metrics (paid, up to 8 per distribution, published in us-east-1) | Hit rate counts only cacheable requests (`POST`, `PUT` and errors excluded); origin latency is first-byte latency for requests served from the origin |

**Why a second request can still be a Miss** (AWS Knowledge Center): each edge location caches only what it received, so a request that lands on another POP misses; an infrequently requested object can be evicted before it expires; headers, cookies or query strings in the cache key split requests; and the origin's `Cache-Control` or `Expires` can shorten the lifetime.

## 11. Exercise: read a miss and a hit from response headers

This is a read-only observation. Label results **observation of a third-party distribution**: you cannot see its cache policy, so every conclusion is an inference from headers.

**Choose a target:** any public static asset (an image, CSS or JavaScript file) whose response carries `x-cache: ... from cloudfront` and `x-amz-cf-pop`. Do not assume any particular site behaves a certain way; check the headers first. If you have your own approved distribution, use it, since you can then compare against its known policy.

```bash
URL='https://<cloudfront-served-host>/<path-to-static-asset>'
curl -sI "$URL" | grep -iE '^(HTTP|date|age|cache-control|x-cache|via|x-amz-cf-pop)'
sleep 5
curl -sI "$URL" | grep -iE '^(HTTP|date|age|cache-control|x-cache|via|x-amz-cf-pop)'
```

`curl -I` sends `HEAD`. The Developer Guide notes that only `OPTIONS` responses are cached separately from `GET` and `HEAD`, so the headers describe the same cached object a `GET` would use. To repeat with a real `GET` that discards the body, use `curl -s -o /dev/null -D - "$URL"`.

**Illustrative output** (shape only, not captured from a specific site; values will differ):

```text
HTTP/2 200
date: Thu, 19 Nov 2026 09:00:00 GMT
cache-control: max-age=86400
x-cache: Miss from cloudfront
via: 1.1 <edge-server-id-1>.cloudfront.net (CloudFront)
x-amz-cf-pop: <POP-code>

HTTP/2 200
date: Thu, 19 Nov 2026 09:00:00 GMT
cache-control: max-age=86400
x-cache: Hit from cloudfront
via: 1.1 <edge-server-id-2>.cloudfront.net (CloudFront)
x-amz-cf-pop: <POP-code>
age: 5
```

**Interpretation rules:**

| You see | Conclude | Check next |
|---|---|---|
| Miss, then Hit, same `x-amz-cf-pop` | The first request filled this POP's cache (or a regional cache that it then read); the second was served without the origin | `age` is about the gap between requests; `date` stays the same |
| Hit on the **first** request | Another viewer already populated the cache | `date` + `age` ≈ now; `age` close to `max-age` means it will expire soon |
| Miss, then Miss | Different POP, an eviction, a cache key that includes something that differs, or a non-cacheable response | Compare `x-amz-cf-pop`; read `cache-control` for `no-store`, `private` or `max-age=0` |
| `RefreshHit` | The copy had expired and was revalidated with the origin | Expect `age` to restart near 0 |
| `via` server identifier changes but the POP is the same | A different server in the same POP answered; the cached object was still found | Nothing to fix |

**Tasks:**

1. Run the two requests and record `x-amz-cf-pop`, `x-cache`, `age`, `date` and `cache-control` for each.
2. Compute `date` + `age` and compare with your clock. Explain the difference.
3. From `cache-control`, state how long a shared cache may treat the copy as fresh, and which value (`s-maxage` or `max-age`) a CDN would use. State what the distribution's minimum and maximum TTL could change, citing the table in section 6.
4. If the first request was already a Hit, explain why. A cache-busting query string does not reliably force a Miss: when the cache policy leaves query strings out of the key (the CloudFront default), `?x=1` hits the same object. If you try it, send at most one such request to someone else's site, and explain the result with the cache key.
5. **Design part (desk check):** for a site with `/assets/*` (versioned file names), `/index.html` and `/api/*`, write the cache behavior table: cache key contents, TTLs, origin request policy, invalidation plan and whether Origin Shield is worth its per-request cost. Then draw the origin path following section 9 and list its security group rules.

**Review criteria:**

- Every conclusion cites a header and a rule from sections 4–6 or 10.
- A second Miss is not reported as "caching is broken" before the POP codes are compared.
- The design part has no internet-facing load balancer, no public CIDR in any inbound rule, and `/api/*` either caches nothing or has a cache key that includes every value that changes the response.

## 12. Observing failure and recovery

Use this table to decide **what evidence would settle each verdict**. If you later reproduce a scenario in an approved existing environment, collect that evidence.

| Failure | Expected behavior | Evidence | What that evidence alone does not establish |
|---|---|---|---|
| Origin down, object still fresh | Hits continue; misses fail | `x-cache: Hit` with rising `age`; `Error` results for misses in logs | That every object is cached |
| Origin down, object stale, `stale-if-error` set | Stale copy served until the lesser of the directive and the maximum TTL | `age` beyond `max-age`; origin errors in logs | How long the outage lasted |
| Origin down, minimum or maximum TTL > 0, `no-cache` without `stale-if-error=0` | A previously fetched copy can be served (section 6 trap) | Responses where you expected errors | That this is acceptable for that content |
| Cache key grows (a header or cookie added) | Hit rate falls, origin latency and origin load rise | CloudWatch cache hit rate, origin request counts | Which value split the key (compare policies) |
| Origin certificate mismatch or expiry | `502` to viewers on misses | Viewer `502`; origin TLS errors | Whether hits were affected (they are not) |
| Security group change removes the CloudFront source | Misses fail to connect; hits continue | `504` on misses (an origin firewall or security rule that blocks CloudFront traffic returns 504); the SG rule history | That the internal ALB became reachable from the internet (it cannot: no public address) |
| Bad deployment fixed by invalidation | Edges refetch; browsers and proxies may keep the old copy | Invalidation status; `x-cache: Miss` then `Hit` | That users' browsers updated (only versioned names do that) |

**Recovery is a load event.** After an invalidation or an origin outage, many POPs miss at once. Regional edge caches, Origin Shield and request collapsing reduce the number of origin requests, but plan origin capacity for the refill. Zero observed errors only means the sampling did not catch any.

## 13. Deliverables and completion criteria

| Deliverable | Done when |
|---|---|
| Path drawing | Viewer, POP, regional edge cache, Origin Shield (if used) and origin are drawn, with cache tiers and connection legs distinguished, and the requests that skip the regional edge cache marked |
| Header observation | Two requests recorded with POP, `x-cache`, `age`, `date` and `cache-control`, each conclusion tied to a rule |
| Cache behavior table | Cache key, TTLs, origin request policy, invalidation or versioning plan per path, with the Origin Shield decision justified |
| Origin path and rules | VPC origin to an internal ALB, the security group rule source (service group or prefix list) and the per-leg TLS table |
| Failure table | Each row has the expected behavior, the evidence and its limit |

You are done when you can explain, with sources, how a request is steered to a POP, which tier answers it and why, how the cache key and TTL rules decide the hit ratio, the difference between invalidation and versioned names, and why the origin is unreachable except through CloudFront. Continue with the next workbook, [edge security](./09-edge-security-waf-ddos.md), for the attack side of the same path, review the WAF placement in [WAF, Edge and API Security](../../security/14-waf-edge-api-security.md), and take the [quiz](../../quizzes/networking/expert/08-cdn-edge-delivery-quiz.md).

## References

Amazon CloudFront Developer Guide

- [What is Amazon CloudFront?](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/Introduction.html) (lowest-latency routing, AWS network)
- [How CloudFront delivers content](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/HowCloudFrontWorks.html) (DNS routing to the POP, regional edge caches, requests that skip them)
- [Use Amazon CloudFront Origin Shield](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/origin-shield.html) (bypass, Regions, cost basis, `OriginShieldHit`)
- [Understand the cache key](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/understanding-the-cache-key.html), [Control origin requests with a policy](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/controlling-origin-requests.html)
- [Manage how long content stays in the cache (expiration)](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/Expiration.html) (TTL table, `stale-while-revalidate`, `stale-if-error`, minimum TTL warning)
- [Invalidate files to remove content](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/Invalidation.html), [Pay for file invalidation](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/PayingForInvalidation.html)
- [Quotas](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/cloudfront-limits.html) (invalidation rates, VPC origins, origin access controls)
- [Request and response behavior for custom origins](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/RequestAndResponseBehaviorCustomOrigin.html) (HTTP/1.1 to the origin, persistent connections, request collapsing, `Via`, origin protocol)
- [Distribution settings reference](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/DownloadDistValuesGeneral.html) (supported HTTP versions, HTTP/2 and HTTP/3 requirements)
- [Require HTTPS between CloudFront and your custom origin](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/using-https-cloudfront-to-custom-origin.html) (origin protocol policy, origin certificate names)
- [Restrict access to an Amazon S3 origin](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/private-content-restricting-access-to-s3.html) (OAC)
- [Restrict access with VPC origins](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/private-content-vpc-origins.html) (requirements, security groups, restrictions)
- [Locations and IP address ranges of CloudFront edge servers](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/LocationsOfEdgeServers.html) (managed prefix list)
- [Request Anycast static IPs](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/request-static-ips.html)
- [View CloudFront and edge function metrics](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/viewing-cloudfront-metrics.html) (cache hit rate, origin latency), [Standard log file fields](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/standard-logs-reference.html)
- [Restrict access to Application Load Balancers](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/restrict-access-to-load-balancer.html) (ALB certificate Region versus the us-east-1 viewer certificate)
- [HTTP 504 status code (Gateway Timeout)](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/http-504-gateway-timeout.html) (origin firewall blocking CloudFront)

Other AWS sources

- [How Elastic Load Balancing works](https://docs.aws.amazon.com/elasticloadbalancing/latest/userguide/how-elastic-load-balancing-works.html) (internal load balancer scheme)
- [AWS whitepaper: Origin HTTPS configuration](https://docs.aws.amazon.com/whitepapers/latest/secure-content-delivery-amazon-cloudfront/origin-https-configuration.html) (origin certificate conditions, SNI, `502`)
- [AWS Knowledge Center: What protocols does CloudFront support?](https://repost.aws/knowledge-center/cloudfront-supported-protocols) (HTTP/1.0 and 1.1 on by default, HTTP/1.1 to custom origins)
- [AWS Knowledge Center: X-Cache: Miss from CloudFront](https://repost.aws/knowledge-center/cloudfront-x-cachemiss-error), [Custom object caching and origin headers](https://repost.aws/knowledge-center/cloudfront-custom-object-caching) (`x-cache` values, `x-amz-cf-pop`)
- [AWS Knowledge Center: Associate a certificate in US East (N. Virginia)](https://repost.aws/knowledge-center/migrate-ssl-cert-us-east)
- [Amazon CloudFront FAQs](https://aws.amazon.com/cloudfront/faqs/) (older concurrent invalidation limits), [Amazon CloudFront pricing](https://aws.amazon.com/cloudfront/pricing/)
- [AWS Networking blog: Private AI agent over CloudFront VPC Origins](https://aws.amazon.com/blogs/networking-and-content-delivery/private-ai-agent-with-websocket-streaming-over-cloudfront-vpc-origins-and-the-next-generation-of-opensearch-serverless-for-knowledge-retrieval/) (VPC origin routing by ARN, origin certificate)
- [AWS Networking blog: managed prefix list for CloudFront](https://aws.amazon.com/blogs/networking-and-content-delivery/limit-access-to-your-origins-using-the-aws-managed-prefix-list-for-amazon-cloudfront/) (rule weight 55)

Standards

- [RFC 9111: HTTP Caching](https://www.rfc-editor.org/rfc/rfc9111.html) (cache key, freshness, `Age`, `no-cache`, `s-maxage`)
- [RFC 5861: HTTP Cache-Control Extensions for Stale Content](https://www.rfc-editor.org/rfc/rfc5861.html)
- [RFC 9110: HTTP Semantics](https://www.rfc-editor.org/rfc/rfc9110.html) (`Via`)
- [RFC 4786: Operation of Anycast Services](https://www.rfc-editor.org/rfc/rfc4786.html), [RFC 7871: Client Subnet in DNS Queries](https://www.rfc-editor.org/rfc/rfc7871.html)
- [RFC 1918](https://www.rfc-editor.org/rfc/rfc1918.html) (example addresses)

Exam scope (used only to choose topics)

- [AWS Certified Advanced Networking - Specialty (ANS-C01) exam guide](https://docs.aws.amazon.com/aws-certification/latest/advanced-networking-specialty-01/advanced-networking-specialty-01.html)
