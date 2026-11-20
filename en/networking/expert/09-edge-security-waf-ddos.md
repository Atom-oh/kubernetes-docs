# 09. Edge Security: WAF and DDoS Defense

> **Last Updated**: November 19, 2026
> **Lab boundary**: Desk exercise only. You write a count-mode rule plan on paper; this workbook creates no web ACL, distribution, Shield subscription, load balancer or Kubernetes object, and sends no attack or load traffic to any system.
> **Verification status**: The AWS WAF, AWS Shield and Amazon CloudFront developer guides, the AWS WAF API reference, the AWS whitepaper on DDoS resiliency, RFC 4987 and the OWASP Top 10 2021 page were checked. No rule was deployed and no traffic was measured; the numbers in the exercise are a worked scenario, not observations.

After this workbook, you should be able to name the layer an attack targets, say **where on the path** it is stopped and by which control, build an AWS WAF rule plan that starts in count mode with measured expectations and a rollback trigger, and explain why an origin that the internet can reach on its own makes every edge control optional for the attacker.

This chapter builds on the edge-to-origin path from [workbook 08](./08-cdn-edge-delivery.md#edge-origin-path) (CloudFront → VPC origin → internal ALB) and does not re-teach it. Host firewalls on the server itself are in [beginner 06](../beginner/06-firewalls-host-security.md). WAF placement, rule-ordering pitfalls, request-body inspection limits, forwarded client IPs and the full log field list are in [WAF, Edge and API Security](../../security/14-waf-edge-api-security.md); this workbook links those sections instead of repeating them. Pod-level rules are in [Network Policies](../../security/04-network-policies.md), and the Ingress side is in [AWS Load Balancer Controller](../03-aws-lb-controller.md). The controller document's examples use `alb.ingress.kubernetes.io/scheme: internet-facing`; **in this course's edge design the ALB is internal** (`alb.ingress.kubernetes.io/scheme: internal`) and sits behind a CloudFront VPC origin, so read those examples with that one value changed. Anycast routing with BGP is in [workbook 02](./02-routing-policy-convergence.md), and the TCP handshake in [Network Fundamentals Part 2](../../basics/06-network-fundamentals-part2.md).

**Readiness:** a text editor and the AWS documentation. No AWS account is needed. Building the design yourself incurs AWS WAF charges (per web ACL, per rule and per million requests, plus extra fees for Bot Control, account takeover prevention, the Anti-DDoS rule group, CAPTCHA and Challenge, capacity above 1,500 WCUs and logging), CloudFront and load balancer charges, and, if you subscribe, AWS Shield Advanced (the pricing page lists a monthly fee starting at $3,000 with a one-year term). **That cost and the cleanup are the learner's own.** Never test with attack traffic, including against your own resources, outside a written and approved test plan.

## 1. Read with a question to answer

Exam scope only chooses what to read. Numbers and behavior come from the official pages in the first column.

| Read | Exam scope it maps to | Question to answer in your own words |
|---|---|---|
| [AWS Shield Standard overview](https://docs.aws.amazon.com/waf/latest/developerguide/ddos-standard-summary.html), [Shield mitigation logic for CloudFront and Route 53](https://docs.aws.amazon.com/waf/latest/developerguide/ddos-event-mitigation-logic-continuous-inspection.html) | ANS-C01 Domain 4 Network Security, Compliance, and Governance, Task 4.1 (securing inbound traffic flows with AWS WAF and AWS Shield) | Why does a SYN flood aimed at a CloudFront distribution not become a SYN flood at the origin? |
| [Using rule actions](https://docs.aws.amazon.com/waf/latest/developerguide/waf-rule-action.html), [Rate-based rule settings](https://docs.aws.amazon.com/waf/latest/developerguide/waf-rule-statement-type-rate-based-high-level-settings.html), [Web request labeling](https://docs.aws.amazon.com/waf/latest/developerguide/waf-labels.html) | Domain 4, Task 4.1 (threat models, mitigation strategies) | Which actions end the evaluation of a request, and which let later rules see it? |
| [AWS Shield Advanced capabilities](https://docs.aws.amazon.com/waf/latest/developerguide/ddos-advanced-summary-capabilities.html), [Anti-DDoS managed rule group](https://docs.aws.amazon.com/waf/latest/developerguide/aws-managed-rule-groups-anti-ddos.html) | Domain 4, Task 4.1 | What does Shield Advanced add that Shield Standard does not, and what does it require first? |
| [Testing and tuning protections](https://docs.aws.amazon.com/waf/latest/developerguide/web-acl-testing.html), [Logging web ACL traffic](https://docs.aws.amazon.com/waf/latest/developerguide/logging.html), [Viewing sampled requests](https://docs.aws.amazon.com/waf/latest/developerguide/web-acl-testing-view-sample.html) | Domain 4, Task 4.2 (validate and audit security with monitoring and logging) | Which log field shows that a rule in Count mode would have matched? |
| [OWASP Top 10 2021](https://owasp.org/Top10/2021/) | Domain 4, Task 4.1 (common security threats) | Which of the ten categories can an edge WAF reduce, and which can only the application fix? |

After reading, draw the path from the client to the Pod and mark on it where each attack in section 2 stops. A design review that cannot point to the stopping place for an attack has not covered that attack.

## 2. Threat layers: what each attack exhausts

Attacks are easier to place when you ask what resource they try to use up: link bandwidth, connection state, CPU for TLS, or application work.

| Layer | Attack | Mechanism | What it exhausts |
|---|---|---|---|
| L3 | **UDP reflection** | The attacker spoofs the victim's address as the source of small UDP requests to third-party servers (DNS, NTP, SSDP, CLDAP, Memcached, CharGen, QOTD), which send much larger responses to the victim. For DNS the AWS whitepaper gives an amplification factor of 28 to 54 times | Link and network capacity |
| L4 | **SYN flood** | Many SYNs that never complete the three-way handshake ([Part 2](../../basics/06-network-fundamentals-part2.md)) | The listener's backlog of half-open connections ([RFC 4987](https://www.rfc-editor.org/rfc/rfc4987.html) §2.2); the attack does not need to fill the link |
| L6 | **TLS abuse** | Unreadable data presented as a handshake, endless renegotiation, or rapid session open and close | CPU on the side that terminates TLS |
| L7 | **HTTP flood** | Requests that look like a valid user's, sometimes imitating human browsing | Application capacity; low volumes can be enough |
| L7 | **Cache-busting** | An HTTP flood that varies the query string so the CDN must forward every request ([workbook 08](./08-cdn-edge-delivery.md) section 5) | Origin capacity behind the cache |
| L7 | **Exploit attempts** | Payloads for known vulnerability classes (section 4) | Confidentiality and integrity, not capacity |
| L7 | **Bots, scrapers, credential stuffing** | Automated content theft and login attempts with leaked username and password pairs | Business logic and accounts; the whitepaper notes these are not strictly DDoS but look like it |

Two consequences follow. First, a reflection attack needs the ability to spoof source addresses, and networks that apply source address validation ([BCP 38](https://www.rfc-editor.org/info/bcp38)) remove it. Second, an L7 attack is well-formed traffic, so nothing that checks only packet validity can stop it: it needs a control that reads the request.

## 3. Where each attack is stopped

| Attack | Stopped at | Mechanism | Owner |
|---|---|---|---|
| UDP reflection | CloudFront edge | Shield mitigations pass only traffic that is valid for web applications; CloudFront accepts only well-formed connections | AWS (automatic) |
| SYN flood | CloudFront edge | The Shield TCP SYN proxy verifies the handshake (stateless SYN cookies) before a connection reaches the service | AWS (automatic) |
| TLS abuse | CloudFront edge | TLS terminates at the edge, so the origin sees only well-formed requests ([workbook 08](./08-cdn-edge-delivery.md) section 7) | AWS (automatic) |
| HTTP flood, cache-busting | WAF web ACL at the edge | Rate-based rules, the Anti-DDoS managed rule group, Challenge | You |
| Exploit attempts | WAF web ACL, then the application | Managed rule groups as a first filter; input validation and authorization in the application | You |
| Credential stuffing | WAF (account takeover prevention), then the application | Stolen-credential checks and login volume limits; MFA and lockout policy in the application | You |
| Anything aimed at the origin directly | **Nowhere**, unless the origin has no public path | Origin cloaking (section 8) | You |

**SYN cookies** let a listener keep no state for a connection in SYN-RECEIVED: the server encodes what it needs in the sequence number of its SYN-ACK and rebuilds the state when a valid ACK returns ([RFC 4987](https://www.rfc-editor.org/rfc/rfc4987.html) §3.6). The AWS whitepaper describes the edge services' stateless SYN flood mitigation as verifying incoming connections with SYN cookies before passing them on, and notes that modern operating systems enable SYN cookies by default. CloudFront also keeps persistent connections to the origin, so a viewer's new connection is not a new origin connection. Neither AWS WAF nor a security group replaces this: AWS WAF inspects HTTP requests, so it acts only after a connection exists, and a security group admits or denies by source, protocol and port without limiting the rate.

**Absorption** needs capacity larger than the flood. The AWS page on Shield mitigation for CloudFront says CloudFront uses a combination of DNS traffic direction and anycast routing to mitigate attacks close to the source and isolate faults. That is consistent with workbook 08: DNS steers each viewer to a POP, and the attack traffic lands on many POPs instead of one origin. Shield mitigation is integrated with the edge services, and the whitepaper states that this reduces the time to mitigate from minutes to under a second.

**Cost of rejected traffic:** the whitepaper states that you are not charged for HTTP requests or data transfer out for requests that CloudFront or AWS WAF rejects. A request that the WAF blocks costs WAF request inspection, not origin capacity.

**Practical point:** the edge stops volume; it does not decide who may do what. AWS WAF reduces the exploit and abuse surface, but [authorization stays in the application](../../security/14-waf-edge-api-security.md) (section 1 of that chapter). A design where the WAF is the only check on a business action has a single point of failure.

## 4. OWASP Top 10 2021 and what an edge WAF can do

The [OWASP Top 10 2021](https://owasp.org/Top10/2021/) has ten web application risk categories, A01 to A10. OWASP has since published a 2025 edition; this workbook uses the 2021 list. AWS describes its core rule set as protection against "some of the high risk and commonly occurring vulnerabilities" described in OWASP publications such as the Top 10. Treat managed rules as a filter for known request patterns, not as coverage of a category.

| 2021 category | Edge WAF contribution (AWS managed rule group examples) | What only the application or platform can do |
|---|---|---|
| A01 Broken Access Control | Little: the request looks legitimate | Object-level authorization on every request |
| A02 Cryptographic Failures | None at the WAF | TLS on every leg ([workbook 08](./08-cdn-edge-delivery.md) section 7), key and data handling |
| A03 Injection | SQL injection rules (`AWSManagedRulesSQLiRuleSet`, 200 WCU), cross-site scripting rules in the core rule set | Parameterized queries, output encoding |
| A04 Insecure Design | None | Threat modeling, business limits |
| A05 Security Misconfiguration | Indirect | Configuration review; a publicly reachable origin is a misconfiguration of the edge design (section 8) |
| A06 Vulnerable and Outdated Components | Known bad inputs (`AWSManagedRulesKnownBadInputsRuleSet`, 200 WCU), for example the Log4j and Java deserialization patterns | Patching; a WAF rule only buys time |
| A07 Identification and Authentication Failures | Account takeover prevention (`AWSManagedRulesATPRuleSet`, 50 WCU, paid) | MFA, lockout, session handling |
| A08 Software and Data Integrity Failures | None | Signed artifacts, supply-chain controls |
| A09 Security Logging and Monitoring Failures | WAF logs and metrics are one input (section 9) | Correlation and alerting across layers |
| A10 Server-Side Request Forgery (SSRF) | Core rule set rules that look for attempts to exfiltrate EC2 metadata (`EC2MetaDataSSRF_*`) | Egress control and URL validation in the application |

The core rule set (`AWSManagedRulesCommonRuleSet`) costs 700 WCU. It also enforces size limits, for example `SizeRestrictions_BODY` blocks request bodies over 8 KB, which is a common source of false positives for upload paths (section 10).

## 5. The AWS WAF model

**Web ACL.** The AWS WAF console now calls a web ACL a **protection pack (web ACL)**; this workbook uses "web ACL". A web ACL holds rules and rule groups and a **default action** (Allow or Block) for any request that no rule terminates. Each resource is associated with at most one web ACL, and one web ACL can protect many resources.

**Scope.** A web ACL for CloudFront is **global**: it has the hard-coded Region US East (N. Virginia). Through the CLI you pass `--scope=CLOUDFRONT --region=us-east-1`, and through the API and SDKs you use the `us-east-1` endpoint. A web ACL associated with a CloudFront distribution cannot also be associated with another resource type; a regional resource such as an ALB needs a separate `REGIONAL` web ACL in its own Region.

**Rules, rule groups and order.** A rule is a statement plus an action. A rule group is a reusable set of rules, either your own or a **managed rule group** (AWS Managed Rules, AWS Marketplace sellers). AWS WAF evaluates rules from the lowest numeric priority up until a rule terminates the evaluation or the rules run out; inside a rule group it uses that group's own priorities. Ordering pitfalls (a broad early Allow, exempting a whole group) are in [security/14 section 3](../../security/14-waf-edge-api-security.md).

**Actions:**

| Action | Ends evaluation? | Behavior |
|---|---|---|
| Allow | Yes | Forwards the request to the protected resource; your own rules can insert custom request headers |
| Block | Yes | The protected resource answers `403 (Forbidden)` by default; your own rules can define a custom response |
| Count | No | Counts the match and continues with the next rule; can add labels and custom request headers |
| CAPTCHA | Depends on the token | Valid, unexpired token: behaves like Count. Missing, invalid or expired token: blocks and sends a CAPTCHA puzzle when the client can show it |
| Challenge | Depends on the token | Same token logic, with a silent browser challenge instead of a puzzle |

CAPTCHA and Challenge run only when browsers access HTTPS endpoints in a secure context, and both carry extra fees. An API client that is not a browser cannot answer them, so test machine APIs separately; AWS WAF also provides application integration SDKs that add tokens to requests from apps. AWS has also added a **Monetize** action (HTTP `402 Payment Required`, CloudFront web ACLs only, terminating, not allowed in rate-based rules); it is outside this workbook's scope.

**Rate-based rules.** A rate-based rule counts requests for each **aggregation instance** (for example each source IP) over an **evaluation window** of 60, 120, 300 or 600 seconds (default 300) and applies its action to further matching requests from an instance that exceeds the **limit** (minimum 10). The action can be anything except Allow. A **scope-down statement** limits which requests are counted and acted on, for example only `POST` to `/login`. The behavior to design around:

- AWS WAF estimates the rate with an algorithm that weights recent requests more, so it limits near the configured value, not exactly at it.
- The guide says the rate is checked frequently and independently of the window; the API reference says about every 10 seconds. Requests can arrive too fast for up to several minutes before limiting starts, and limiting can continue after the rate falls, usually for under 30 seconds.
- Changing the limit, window, aggregation, forwarded IP configuration or scope **resets the counts** and can pause rate limiting for up to a minute.
- A rate-based statement cannot be nested inside another statement (for example a `NotStatement`), but its scope-down statement can contain one.
- With aggregation on IP alone, `GetRateBasedStatementManagedKeys` lists the addresses currently being limited.

Which client address to aggregate on along CloudFront → ALB → Ingress is covered in [security/14 section 5](../../security/14-waf-edge-api-security.md).

**Labels.** A label is metadata that a matching rule adds to the request; it remains for the rest of that web ACL's evaluation, and later rules read it with a **label match statement**. Your labels have the form `awswaf:<account id>:<rulegroup or webacl>:<name>:<namespace>:...:<label name>`, and managed rule group labels the form `awswaf:managed:<vendor>:<rule group name>:...`, for example `awswaf:managed:aws:core-rule-set:NoUserAgent_Header`. All AWS Managed Rules rule groups add labels. The main pattern is: set a rule to Count so it only labels, then add a later rule that decides on the label combination. Labels also produce CloudWatch label metrics.

**Overriding managed rules.** Two different switches exist:

| Override | What happens | Use for testing? |
|---|---|---|
| **Rule action override** (`RuleActionOverrides`, per rule inside the group) | Matching requests are handled exactly as if that rule's action were the override, for example Count; the group keeps evaluating its other rules | Yes, this is the documented way to test a rule group |
| **Rule group return action override to Count** | The group evaluates normally and stops at its first terminating match; only the result returned to the web ACL becomes Count | No: the guide says it does not change how the group evaluates, so later rules in the group never run for that request |

`RuleActionOverrides` replaced the older `ExcludedRules` setting in October 2022.

**Capacity (WCU).** Web ACL capacity units measure the operating resources rules need; they do not change how traffic is inspected. Simple statements cost less than, for example, regex pattern sets or JSON body inspection. A rule group has an **immutable capacity** set at creation (maximum 5,000 WCU), and using a group in a web ACL costs that capacity, not its current content. A web ACL can use up to 5,000 WCU; the base price includes 1,500, and capacity above that has tiered extra fees. The `CheckCapacity` API returns the capacity of a rule list before you deploy it.

**Propagation.** Changes take from a few seconds to a number of minutes to reach every location, so for a short time one location can apply the new action while another still applies the old one.

## 6. AWS Shield Standard and Shield Advanced

| | Shield Standard | Shield Advanced |
|---|---|---|
| Cost and activation | Automatic for every AWS customer at no additional charge | Subscription; the pricing page lists a monthly fee starting at $3,000 with a one-year term that renews automatically. Protects only the resources you add explicitly (or through an AWS Firewall Manager Shield Advanced policy) |
| Coverage | The most common, frequently occurring network and transport layer attacks; CloudFront distributions, Route 53 hosted zones and Global Accelerator standard accelerators receive protection against all known network and transport layer attacks | CloudFront, Route 53 hosted zones, Global Accelerator standard accelerators, Elastic IP addresses (and the EC2 instances and NLBs behind them), ALBs and Classic Load Balancers |
| Application layer (L7) | None by itself; L7 is the WAF's job | Uses AWS WAF web ACLs; standard WAF fees for protected resources are covered up to 1,500 WCU and the default body size. Bot Control, CAPTCHA, capacity above 1,500 WCU and larger body inspection are not covered |
| Automatic L7 mitigation | None | See the next paragraph |
| Response team | None | **Shield Response Team (SRT)** for help during an attack and custom mitigations; requires a Business Support or Enterprise Support plan (the DDoS resiliency whitepaper words it as Business Support+ or Enterprise Support) |
| Detection | Automatic | Health-based detection with Route 53 health checks, which **proactive engagement** (the SRT contacts you) requires |
| Cost protection | None | Shield Advanced service credits for some scaling charges caused by an attack |
| Visibility | None beyond service metrics | Event details through the console, API and CloudWatch metrics; protection groups |

**Automatic L7 mitigation in 2026.** Since March 26, 2026, the **Anti-DDoS managed rule group** (`AWSManagedRulesAntiDDoSRuleSet`, 50 WCU, extra fees) is AWS's default solution for HTTP request floods, and it supersedes Shield Advanced's Layer 7 automatic mitigation, which existing customers can keep using. The rule group compares traffic with the resource's baseline, labels every request during an event (`awswaf:managed:aws:anti-ddos:event-detected`) and suspected sources by confidence (`low-`, `medium-`, `high-suspicion-ddos-request`), sends a silent Challenge as a soft mitigation (only `GET` requests can be labelled challengeable), and blocks as a hard mitigation. The legacy Shield Advanced feature adds a 150 WCU rule group, needs 24 hours to 30 days to learn a baseline, can count or block, and works less well on an ALB behind a CDN because the CDN may not forward the original client attributes; AWS recommends enabling it on the CloudFront distribution instead.

## 7. Defense in depth on the reference path

![Edge security animation. ① A botnet sends an L3/L4 flood (UDP reflection and SYN flood) at the CloudFront edge; Shield absorbs it there and nothing reaches the origin. ② A bot sends a well-formed HTTPS flood on /login; it passes the L3/L4 checks, but a rate-based rule in the WAF web ACL, example name rate-login, blocks it and the client receives 403 Forbidden. ③ A legitimate GET passes Shield, and because no WAF rule terminates its evaluation, the web ACL default action Allow forwards it. ④ CloudFront connects through a VPC origin: a service-managed ENI in a private subnet, 10.0.11.25, opens a connection to an internal ALB, 10.0.12.40, whose security group admits only CloudFront-VPCOrigins-Service-SG or the origin-facing prefix list. ⑤ The ALB, created from an Ingress with scheme internal, forwards to a Pod IP, 10.0.13.31, whose NetworkPolicy admits only the ALB subnet, and the Pod returns 200. There is no internet-facing load balancer and no inbound rule that admits a public CIDR.](../../.gitbook/assets/en-networking-expert-09-edge-security-waf-ddos-anim-0.svg)

| Layer | Control | Admits | Evidence it worked |
|---|---|---|---|
| Edge network | Shield Standard, CloudFront (DNS steering, anycast, SYN proxy, TLS at the edge) | Well-formed HTTP(S) connections | Origin load unchanged during a network-layer event; Shield Advanced event data if subscribed |
| Edge application | Global web ACL (`CLOUDFRONT` scope, us-east-1) | Requests no rule terminates, then the default action | WAF logs `terminatingRuleId`, `action`, labels |
| Origin path | VPC origin to an internal ALB ([workbook 08](./08-cdn-edge-delivery.md#edge-origin-path)) | Only CloudFront; the ALB has private addresses only | No internet route exists to test against |
| ALB security group | Inbound only from `CloudFront-VPCOrigins-Service-SG` (your distribution) or the managed prefix list `com.amazonaws.global.cloudfront.origin-facing` (any distribution) | CloudFront's VPC origin ENIs | Security group rules; expect ALB access logs to show only addresses from the VPC origin subnet |
| Ingress | AWS Load Balancer Controller with `alb.ingress.kubernetes.io/scheme: internal` and `target-type: ip` ([AWS Load Balancer Controller](../03-aws-lb-controller.md)) | Listener rules you defined | Ingress events, target health |
| Pod | NetworkPolicy ingress from an `ipBlock` with the ALB subnets ([Network Policies](../../security/04-network-policies.md#kubernetes-networkpolicy-spec)) | Connections from the ALB nodes | Denied connections in the CNI's policy logs, if enabled |
| Host | Host firewall ([beginner 06](../beginner/06-firewalls-host-security.md)) | Ports the node must serve | Firewall counters |
| Application | Authentication and authorization | The user's permitted actions | Application audit log |

**Which source address the Pod sees.** An ALB is a proxy: the ELB guide says server access logs contain only the load balancer's IP address, and the client's address arrives in `X-Forwarded-For`, which is trustworthy only when properly secured systems added it. A Pod IP target therefore sees the ALB node's private address, which is why the NetworkPolicy above names the ALB subnets. The Kubernetes documentation warns that whether address rewriting happens before or after NetworkPolicy processing depends on the network plugin, cloud provider and Service implementation, so confirm the observed source on your CNI before you rely on the rule, and recall that NetworkPolicy has no effect without a plugin that enforces it.

**One web ACL or two.** The CloudFront web ACL cannot also be associated with the ALB. If you add a regional web ACL on the ALB, it is a second, separate inspection with its own logs and costs; [security/14 section 2](../../security/14-waf-edge-api-security.md) discusses when that is worth it.

## 8. Origin cloaking: why a reachable origin bypasses the edge

Every control in the edge rows of the table above applies **only to requests that go through the distribution**. If an attacker learns an address or DNS name at which the origin answers from the internet, they send requests there and skip Shield's edge absorption, the global web ACL, the rate-based rules and CloudFront's TLS termination all at once. The origin then faces raw SYN floods and HTTP floods with only its own capacity, and the WAF logs show nothing.

**Cloaking** means the origin has no internet path at all. In the reference design this is a routing property, not a filter: the internal ALB has only private addresses, so a looser security group later still does not make it reachable from the internet ([workbook 08](./08-cdn-edge-delivery.md#edge-origin-path)). Compare the weaker design that [security/14 option A](../../security/14-waf-edge-api-security.md) describes, a public ALB that admits the CloudFront prefix list and checks a secret header: the prefix list admits **any** CloudFront distribution, including one an attacker creates, and the header is a shared secret that stops working once disclosed. This course does not use that design.

**Bypass inventory for a review:** old DNS records that still point to an earlier public origin, other load balancers or Services of type `LoadBalancer` in the same cluster, NodePorts, management endpoints, and test environments that serve the same application. A private origin label on one path does not prove that no other path exists.

## 9. Logging and metrics: what each signal proves

| Signal | Where | What it tells you | Limit |
|---|---|---|---|
| WAF logs | CloudWatch Logs log group, S3 bucket or Amazon Data Firehose stream whose name begins with `aws-waf-logs-` | Per request: `terminatingRuleId` and `action`, Count matches in `nonTerminatingMatchingRules`, `ruleGroupId`, `labels` | Charged separately; you can filter which requests to keep and redact fields (shown as `xxx`) |
| CloudWatch metrics | AWS WAF metrics | Matches grouped by action (a Count rule's matches appear as Count metrics), label metrics for every label | Count-action rules inside rule groups do not emit web ACL dimension metrics, only Rule, RuleGroup and Region dimensions |
| Sampled requests | Web ACL console tab or `GetSampledRequests` | Up to 100 requests that matched a rule and 100 that took the default action, from the previous three hours, with the rule, action and URI | Needs sampling enabled; samples for Count rules inside rule groups are not shown in the web ACL view; redaction in logging does not apply to sampling |
| Traffic overview dashboards | WAF console | Near real-time summaries of the CloudWatch metrics | Summaries, not request evidence |
| Shield Advanced events | Shield console, API, CloudWatch | Detected events and mitigations on protected resources | Subscription only |
| CloudFront logs | [workbook 08 section 10](./08-cdn-edge-delivery.md) | Status codes and result types per request at the edge | The matching rule is in the WAF logs, so correlate the two |

The full list of WAF log fields is in [security/14 section 6](../../security/14-waf-edge-api-security.md). For rules in Count, **logs and label metrics** are the reliable evidence, because sampled requests and web ACL metrics can hide Count matches inside managed rule groups.

## 10. Exercise: a count-mode rule plan with a rollback trigger

Desk exercise. You write a plan that someone could execute later in an approved account; you do not deploy it. Mark the result **worked scenario, not measured**.

**Scenario.** A shop serves `/assets/*`, `/login` (`POST`, browser form), `/api/*` (a mobile app, not a browser) and `/api/upload` (images up to 5 MB) through the reference path in section 7. Seven days of CloudFront logs give this baseline:

| Path | Volume | Per-IP peak in any 5 minutes | Notes |
|---|---|---|---|
| `POST /login` | 1.2 million per day, success rate 96% | p99 of 18 requests; one address, `198.51.100.20`, peaks at 640 | `198.51.100.20` is a partner's office NAT that many employees share |
| `/api/upload` | 40,000 per day | p99 of 6 | Every request body is larger than 8 KB |
| `/api/*` (other) | 9 million per day | p99 of 120 | Mobile app, cannot run Challenge or CAPTCHA |

The web ACL's default action is Allow.

**Plan (fill in or check each row):**

| Priority | Rule | Trial action | Expected matches during the trial | Decision before Block |
|---|---|---|---|---|
| 10 | `AWSManagedRulesCommonRuleSet` with every rule overridden to Count through `RuleActionOverrides` | Count (per rule) | `SizeRestrictions_BODY` on essentially all 40,000 daily `/api/upload` requests (bodies over 8 KB); other rules near zero for real users | Exclude `/api/upload` from the group with a scope-down statement, or keep `SizeRestrictions_BODY` in Count and add a label match rule for other paths |
| 20 | `AWSManagedRulesSQLiRuleSet`, rules overridden to Count | Count (per rule) | Near zero from real users | Investigate every match from a known client before promotion |
| 30 | `rate-login`: rate-based, aggregate on IP, window 300 s, limit 100, scope-down `POST` and path starting `/login` | Count | Ordinary users never match (p99 18 is far below 100); `198.51.100.20` matches whenever it exceeds 100: for one isolated 5-minute burst of 640 after a quiet period, about 540 counted requests (the ones beyond the limit); if it stays above 100 for longer, nearly all of its later requests are counted, because the rule keeps acting until the estimated rate falls below the limit | False positive: add `NOT` (IP set containing `198.51.100.20`) inside the scope-down, or a separate higher limit for that address |

A fragment for row 30 follows. It shows the rule **after** the false-positive decision, with the `PartnerNat` exclusion added; during the trial described in the table the `NotStatement` is absent. It is **one rule inside a web ACL**, not a complete web ACL or a deployment command; `PartnerNat` is an IP set you would create.

```json
{
  "Name": "rate-login",
  "Priority": 30,
  "Statement": {
    "RateBasedStatement": {
      "Limit": 100,
      "EvaluationWindowSec": 300,
      "AggregateKeyType": "IP",
      "ScopeDownStatement": {
        "AndStatement": {
          "Statements": [
            { "ByteMatchStatement": { "SearchString": "POST", "FieldToMatch": { "Method": {} },
                "TextTransformations": [{ "Priority": 0, "Type": "NONE" }], "PositionalConstraint": "EXACTLY" } },
            { "ByteMatchStatement": { "SearchString": "/login", "FieldToMatch": { "UriPath": {} },
                "TextTransformations": [{ "Priority": 0, "Type": "NONE" }], "PositionalConstraint": "STARTS_WITH" } },
            { "NotStatement": { "Statement": { "IPSetReferenceStatement": {
                "ARN": "arn:aws:wafv2:us-east-1:111122223333:global/ipset/PartnerNat/<id>" } } } }
          ]
        }
      }
    }
  },
  "Action": { "Count": {} },
  "VisibilityConfig": { "SampledRequestsEnabled": true, "CloudWatchMetricsEnabled": true, "MetricName": "rate-login" }
}
```

**Tasks:**

1. Complete the plan: for each row write the evidence you will read (log field, metric or label), the trial length, and who decides.
2. Explain why row 10 uses per-rule `RuleActionOverrides` and not the rule group return action override (section 5).
3. Calculate the expected Count matches for `rate-login` with and without the `PartnerNat` exclusion, for one isolated burst and for a sustained peak, and state why the real number will differ (approximate counting, detection delay, limiting that continues briefly after the rate falls).
4. Write a **rollback trigger** for each rule you promote to Block. It must contain a measurable threshold, a time window, an owner and the exact action. Example: "After `rate-login` moves to Block, if the `/login` success rate stays more than 2 percentage points below the 96% baseline for 10 consecutive minutes, or any request from the synthetic login check is blocked, the on-call engineer sets `rate-login` back to Count and records the change." Note that the rollback itself propagates over seconds to minutes and, for a rate-based rule, resets its counts.
5. Decide what the mobile `/api/*` traffic gets instead of Challenge or CAPTCHA, and why.
6. Decide whether the Anti-DDoS managed rule group belongs in the plan, and in what position relative to row 30.

**Review criteria:**

- Every expected number is derived from the baseline table, with the arithmetic shown.
- Each Block promotion has an evidence source that can see Count matches inside managed rule groups (logs or labels, not only sampled requests).
- The plan changes one rule at a time and leaves time for propagation before judging the result.
- Nothing in the plan exposes the origin, adds an internet-facing load balancer or admits a public CIDR.

## 11. Observing failure and recovery

This table is an exercise in **which evidence confirms each diagnosis**. If you later reproduce a scenario in an approved environment, collect exactly this evidence.

| Failure | Expected behavior | Evidence | What that evidence does not prove |
|---|---|---|---|
| A managed rule blocks legitimate uploads | `403` on `/api/upload` right after promotion | WAF logs `terminatingRuleId` = the group, rule `SizeRestrictions_BODY`; CloudFront `403` rate up | That other rules in the group are safe |
| A rate limit was changed during an attack | Limiting pauses for up to a minute | Change record; Count or Block metrics drop, then return | That the new limit is right |
| Rollback from Block to Count | Some locations still block for a short time | Block metric declines over seconds to minutes | That every location has the new setting at a given instant |
| Direct requests to an exposed origin | Origin overloaded while WAF metrics stay flat | Origin access logs show sources that are not CloudFront ENIs | Which path the attacker found (inventory from section 8) |
| L3/L4 flood on the distribution | Origin unaffected | Origin metrics flat; Shield Advanced event if subscribed | That the application layer is safe |
| Anti-DDoS event | Every request, legitimate or not, gets `event-detected` | Label metrics | That a labelled request was malicious (only the suspicion labels say that) |
| Challenge applied to the mobile API | App requests fail | WAF logs show the Challenge rule as the terminating rule for app traffic; app error rate rises | That the clients are bots |

**Recovery is a change, too.** Each rollback is a web ACL update with the same propagation behavior as the change that caused the incident. Write the rollback command and its owner into the plan before the Block change, not during the incident.

## 12. Deliverables and completion criteria

| Deliverable | Completion criteria |
|---|---|
| Threat map | Every attack from section 2 placed on the path with its stopping control and owner |
| Shield decision | Standard only, or Advanced with the features you will use, their prerequisites (support plan, health checks) and cost |
| Rule plan | Priorities, trial actions, expected matches with arithmetic, false-positive decisions and per-rule rollback triggers |
| Origin path review | Cloaking confirmed for the reference path, the bypass inventory checked, and no internet-facing load balancer or public-CIDR ingress |
| Evidence plan | For each rule, the log field or metric that proves it matched and its known blind spots |

You are done when you can explain, with sources, which layer each attack targets and where it stops, how AWS WAF evaluates rules and actions, why count-mode testing uses per-rule overrides, what Shield Advanced adds over Standard, and why the origin must have no public path. Review the WAF placement in [WAF, Edge and API Security](../../security/14-waf-edge-api-security.md), revisit the origin path in [workbook 08](./08-cdn-edge-delivery.md#edge-origin-path), and take the [quiz](../../quizzes/networking/expert/09-edge-security-waf-ddos-quiz.md).

## References

AWS WAF Developer Guide

- [Using rule actions in AWS WAF](https://docs.aws.amazon.com/waf/latest/developerguide/waf-rule-action.html) (Allow, Block and its default `403`, Count, CAPTCHA, Challenge, Monetize)
- [Setting rule priority](https://docs.aws.amazon.com/waf/latest/developerguide/web-acl-processing-order.html)
- [Rate-based rule high-level settings](https://docs.aws.amazon.com/waf/latest/developerguide/waf-rule-statement-type-rate-based-high-level-settings.html), [Rate-based rule caveats](https://docs.aws.amazon.com/waf/latest/developerguide/waf-rule-statement-type-rate-based-caveats.html)
- [Web request labeling](https://docs.aws.amazon.com/waf/latest/developerguide/waf-labels.html), [Label syntax and naming requirements](https://docs.aws.amazon.com/waf/latest/developerguide/waf-rule-label-requirements.html)
- [Overriding rule group actions](https://docs.aws.amazon.com/waf/latest/developerguide/web-acl-rule-group-override-options.html)
- [Web ACL capacity units (WCUs)](https://docs.aws.amazon.com/waf/latest/developerguide/aws-waf-capacity-units.html)
- [Associating or disassociating protection with an AWS resource](https://docs.aws.amazon.com/waf/latest/developerguide/web-acl-associating-aws-resource.html) (global web ACL in US East (N. Virginia), one web ACL per resource)
- [Baseline rule groups](https://docs.aws.amazon.com/waf/latest/developerguide/aws-managed-rule-groups-baseline.html) (core rule set, known bad inputs), [Use-case specific rule groups](https://docs.aws.amazon.com/waf/latest/developerguide/aws-managed-rule-groups-use-case.html) (SQL database), [Account takeover prevention rule group](https://docs.aws.amazon.com/waf/latest/developerguide/aws-managed-rule-groups-atp.html), [Anti-DDoS rule group](https://docs.aws.amazon.com/waf/latest/developerguide/aws-managed-rule-groups-anti-ddos.html)
- [Testing and tuning your AWS WAF protections](https://docs.aws.amazon.com/waf/latest/developerguide/web-acl-testing.html), [Monitoring and tuning](https://docs.aws.amazon.com/waf/latest/developerguide/web-acl-testing-activities.html) (count mode, false-positive mitigations, propagation)
- [Logging web ACL traffic](https://docs.aws.amazon.com/waf/latest/developerguide/logging.html), [Logging destinations](https://docs.aws.amazon.com/waf/latest/developerguide/logging-destinations.html), [Configuring logging](https://docs.aws.amazon.com/waf/latest/developerguide/logging-management-configure.html) (`aws-waf-logs-` prefix, redaction, filters)
- [Viewing a sample of web requests](https://docs.aws.amazon.com/waf/latest/developerguide/web-acl-testing-view-sample.html)

AWS Shield (in the same guide)

- [AWS Shield](https://docs.aws.amazon.com/waf/latest/developerguide/shield-chapter.html), [Shield Standard overview](https://docs.aws.amazon.com/waf/latest/developerguide/ddos-standard-summary.html)
- [Shield mitigation logic for CloudFront and Route 53](https://docs.aws.amazon.com/waf/latest/developerguide/ddos-event-mitigation-logic-continuous-inspection.html) (valid web traffic only, TCP SYN proxy, TLS at the edge, DNS and anycast)
- [Shield Advanced overview](https://docs.aws.amazon.com/waf/latest/developerguide/ddos-advanced-summary.html), [capabilities and options](https://docs.aws.amazon.com/waf/latest/developerguide/ddos-advanced-summary-capabilities.html), [protected resources](https://docs.aws.amazon.com/waf/latest/developerguide/ddos-advanced-summary-protected-resources.html)
- [Automating application layer DDoS mitigation with Shield Advanced](https://docs.aws.amazon.com/waf/latest/developerguide/ddos-automatic-app-layer-response.html) (Anti-DDoS rule group default since March 26, 2026; 150 WCU; baseline 24 hours to 30 days; ALB behind a CDN)
- [AWS Shield pricing](https://aws.amazon.com/shield/pricing/)

Other AWS sources

- [AWS WAF API Reference: CreateWebACL](https://docs.aws.amazon.com/waf/latest/APIReference/API_CreateWebACL.html) (`CLOUDFRONT` scope and `us-east-1`, default action), [RateBasedStatement](https://docs.aws.amazon.com/waf/latest/APIReference/API_RateBasedStatement.html) (limit range, window, rate check about every 10 seconds, nesting)
- [AWS Best Practices for DDoS Resiliency: infrastructure layer attacks](https://docs.aws.amazon.com/whitepapers/latest/aws-best-practices-ddos-resiliency/infrastructure-layer-attacks.html), [UDP reflection attacks](https://docs.aws.amazon.com/whitepapers/latest/aws-best-practices-ddos-resiliency/udp-reflection-attacks.html), [SYN flood attacks](https://docs.aws.amazon.com/whitepapers/latest/aws-best-practices-ddos-resiliency/syn-flood-attacks.html), [application layer attacks](https://docs.aws.amazon.com/whitepapers/latest/aws-best-practices-ddos-resiliency/application-layer-attacks.html), [mitigation techniques](https://docs.aws.amazon.com/whitepapers/latest/aws-best-practices-ddos-resiliency/mitigation-techniques.html), [web application delivery at the edge (BP1)](https://docs.aws.amazon.com/whitepapers/latest/aws-best-practices-ddos-resiliency/web-application-delivery-at-the-edge-bp1.html)
- [Amazon CloudFront Developer Guide: Use AWS WAF protections](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/distribution-web-awswaf.html), [Restrict access with VPC origins](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/private-content-vpc-origins.html)
- [Elastic Load Balancing: HTTP headers and Application Load Balancers](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/x-forwarded-headers.html) (load balancer address in server logs, `X-Forwarded-For`)

Standards and other primary sources

- [RFC 4987: TCP SYN Flooding Attacks and Common Mitigations](https://www.rfc-editor.org/rfc/rfc4987.html) (§2.2, §3.6)
- [BCP 38](https://www.rfc-editor.org/info/bcp38) (source address validation)
- [OWASP Top 10 2021](https://owasp.org/Top10/2021/)
- [Kubernetes: Network Policies](https://kubernetes.io/docs/concepts/services-networking/network-policies/) (`ipBlock`, source rewriting, plugin requirement)
- [RFC 1918](https://www.rfc-editor.org/rfc/rfc1918.html), [RFC 5737](https://www.rfc-editor.org/rfc/rfc5737.html) (example addresses)

Exam scope (used only to choose topics)

- [AWS Certified Advanced Networking - Specialty (ANS-C01): Domain 4](https://docs.aws.amazon.com/aws-certification/latest/advanced-networking-specialty-01/advanced-networking-specialty-01-domain4.html)
