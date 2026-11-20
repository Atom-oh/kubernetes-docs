# 09. Edge Security: WAF and DDoS Defense Quiz

> **Last Updated**: November 19, 2026

Return to the [workbook](../../../networking/expert/09-edge-security-waf-ddos.md).
Choose one answer per question and explain which rule in the workbook supports it.
These are design reasoning exercises, not claims that a web ACL was deployed.

1. A botnet sends a SYN flood at a CloudFront distribution whose origin is an internal ALB behind a VPC origin. Why does the ALB not receive a SYN flood?
   - A) The WAF web ACL blocks SYN packets with a rate-based rule.
   - B) At the edge, the Shield TCP SYN proxy verifies the handshake (stateless SYN cookies) before a connection reaches the service, and CloudFront keeps its own persistent connections to the origin.
   - C) The ALB security group drops SYN packets that arrive too fast.

<details>
<summary>Show Answer</summary>

**Answer: B) At the edge, the Shield TCP SYN proxy verifies the handshake (stateless SYN cookies) before a connection reaches the service, and CloudFront keeps its own persistent connections to the origin.**

**Explanation:** A SYN flood exhausts the listener's backlog of half-open connections. CloudFront is the listener here, and Shield's SYN proxy only passes connections that complete the handshake; a viewer's new connection is not a new origin connection. AWS WAF inspects HTTP requests, not TCP segments, and a security group is not a rate limiter.

</details>

2. What does a UDP reflection attack require from the attacker, and which network practice removes it?
   - A) A completed TCP handshake with the reflector; TLS everywhere removes it.
   - B) The ability to spoof the victim's address as the source; source address validation (BCP 38) removes it.
   - C) A valid HTTP request; a WAF rate-based rule removes it.

<details>
<summary>Show Answer</summary>

**Answer: B) The ability to spoof the victim's address as the source; source address validation (BCP 38) removes it.**

**Explanation:** The attacker sends small UDP requests (DNS, NTP, SSDP, CLDAP, Memcached and others) with the victim's address as the source, and the reflectors send much larger responses to the victim; for DNS the AWS whitepaper gives an amplification of 28 to 54 times. Networks that validate source addresses take away the spoofing.

</details>

3. A request matches a rule whose action is CAPTCHA, and it carries a valid, unexpired CAPTCHA token. What does AWS WAF do?
   - A) It blocks the request and sends a new puzzle.
   - B) It handles the request like Count and continues with the remaining rules.
   - C) It allows the request immediately and stops evaluation.

<details>
<summary>Show Answer</summary>

**Answer: B) It handles the request like Count and continues with the remaining rules.**

**Explanation:** CAPTCHA and Challenge are non-terminating with a valid, unexpired token and terminating (blocked, with a puzzle or silent challenge) when the token is missing, invalid or expired. Allow and Block always terminate; Count never does. Blocked requests get `403 (Forbidden)` by default.

</details>

4. Which rate-based rule configuration is **not** valid?
   - A) Evaluation window 300 seconds, limit 100, action Block.
   - B) Evaluation window 600 seconds, limit 10, action Count.
   - C) Evaluation window 300 seconds, limit 100, action Allow.

<details>
<summary>Show Answer</summary>

**Answer: C) Evaluation window 300 seconds, limit 100, action Allow.**

**Explanation:** A rate-based rule can use any rule action except Allow. The evaluation window is 60, 120, 300 or 600 seconds (300 by default), and the lowest limit is 10, so A and B are both valid.

</details>

5. During an HTTP flood, an engineer lowers the limit of a rate-based rule that is already blocking traffic. What should the team expect right after the change?
   - A) The new limit applies instantly with the old counts kept.
   - B) The change resets the rule's counts and can pause its rate limiting for up to a minute.
   - C) The rule stays inactive until the next full evaluation window has passed.

<details>
<summary>Show Answer</summary>

**Answer: B) The change resets the rule's counts and can pause its rate limiting for up to a minute.**

**Explanation:** Changing the limit, evaluation window, aggregation, forwarded IP configuration or scope resets the counts. Rate limiting is also approximate: limiting can start up to several minutes after the rate is exceeded and continue briefly after it falls. Plan rate-limit changes before an incident, not during one.

</details>

6. You want to see what each rule in `AWSManagedRulesCommonRuleSet` would block before enforcing it. Which setting gives you that?
   - A) Override the rule group's return action to Count.
   - B) Override each rule's action to Count with `RuleActionOverrides`.
   - C) Set the web ACL default action to Count.

<details>
<summary>Show Answer</summary>

**Answer: B) Override each rule's action to Count with `RuleActionOverrides`.**

**Explanation:** With a per-rule override, matching requests are handled as if that rule's action were Count, and the group keeps evaluating its other rules. A rule group return action override to Count does not change how the group evaluates: it stops at its first terminating match, so later rules in the group never run for that request. The default action is only Allow or Block.

</details>

7. Rule `block-bad-ua` at priority 50 is a label match statement for `awswaf:managed:aws:core-rule-set:NoUserAgent_Header`. The core rule set sits at priority 100 with that rule overridden to Count. Why does `block-bad-ua` never match?
   - A) Managed rule groups do not add labels.
   - B) A label is available only to rules evaluated after the rule that added it, and priority 50 runs before priority 100.
   - C) Labels from Count rules are discarded.

<details>
<summary>Show Answer</summary>

**Answer: B) A label is available only to rules evaluated after the rule that added it, and priority 50 runs before priority 100.**

**Explanation:** AWS WAF evaluates from the lowest numeric priority up, and a label stays on the request for the rest of that evaluation, where later rules read it with a label match statement. All AWS Managed Rules rule groups add labels, and setting a rule to Count so it only labels is the main labeling pattern. Move the label match rule below the group.

</details>

8. You create a web ACL with the CLI to protect a CloudFront distribution. Which statement is correct?
   - A) Use `--scope=REGIONAL` in the Region of the origin ALB, and associate the same web ACL with the ALB too.
   - B) Use `--scope=CLOUDFRONT --region=us-east-1`; this global web ACL cannot also be associated with the ALB.
   - C) Use `--scope=CLOUDFRONT` in any Region, because CloudFront is global.

<details>
<summary>Show Answer</summary>

**Answer: B) Use `--scope=CLOUDFRONT --region=us-east-1`; this global web ACL cannot also be associated with the ALB.**

**Explanation:** A web ACL for CloudFront is global with the hard-coded Region US East (N. Virginia); the API and SDKs use the `us-east-1` endpoint. A web ACL associated with a CloudFront distribution cannot be associated with another resource type, so an ALB needs its own `REGIONAL` web ACL if you want a second inspection.

</details>

9. A web ACL uses `AWSManagedRulesCommonRuleSet` (700 WCU), `AWSManagedRulesSQLiRuleSet` (200 WCU), `AWSManagedRulesKnownBadInputsRuleSet` (200 WCU) and a custom rule group created with a capacity of 500 WCU that currently holds rules worth 120 WCU. What is the result?
   - A) 1,220 WCU, within the base price.
   - B) 1,600 WCU: allowed, because the maximum is 5,000, but above the 1,500 WCU included in the base price, so extra fees apply.
   - C) Rejected, because a web ACL cannot exceed 1,500 WCU.

<details>
<summary>Show Answer</summary>

**Answer: B) 1,600 WCU: allowed, because the maximum is 5,000, but above the 1,500 WCU included in the base price, so extra fees apply.**

**Explanation:** Using a rule group in a web ACL costs the group's immutable capacity set at creation, not its current content, so the custom group counts as 500. 700 + 200 + 200 + 500 = 1,600. The base price includes 1,500 WCU, and capacity above that has tiered extra fees, up to the 5,000 WCU maximum.

</details>

10. A team subscribes to Shield Advanced and wants the Shield Response Team to contact them proactively during an attack. What must be in place?
   - A) Nothing more; the subscription includes it.
   - B) A Business Support or Enterprise Support plan for SRT access, and health-based detection with a Route 53 health check on the protected resource.
   - C) A regional web ACL on every ALB.

<details>
<summary>Show Answer</summary>

**Answer: B) A Business Support or Enterprise Support plan for SRT access, and health-based detection with a Route 53 health check on the protected resource.**

**Explanation:** The SRT requires one of those support plans. Proactive engagement is available only for resources with health-based detection, which uses Route 53 health checks. Shield Advanced also protects only the resources you add explicitly; Shield Standard is the automatic, no-cost layer.

</details>

11. A team proposes a public ALB as the origin, with its security group admitting the CloudFront origin-facing managed prefix list. Why does this course treat that as weaker than a VPC origin to an internal ALB?
   - A) The prefix list admits any CloudFront distribution, including one an attacker creates, while an internal ALB has no internet path at all.
   - B) The prefix list does not include CloudFront's IPv4 addresses.
   - C) A public ALB cannot use TLS.

<details>
<summary>Show Answer</summary>

**Answer: A) The prefix list admits any CloudFront distribution, including one an attacker creates, while an internal ALB has no internet path at all.**

**Explanation:** Edge controls apply only to requests that go through your distribution. A request from another distribution skips your web ACL and rate-based rules. Adding a secret header helps only while the secret stays private. Cloaking with an internal ALB is a routing property, so a looser security group later still does not make the origin reachable from the internet.

</details>

12. During a count-mode trial, which evidence reliably shows that a rule inside a managed rule group would have matched?
   - A) The sampled requests table in the web ACL view.
   - B) The `nonTerminatingMatchingRules` field and labels in WAF logs, plus label metrics.
   - C) The CloudFront standard log's status code.

<details>
<summary>Show Answer</summary>

**Answer: B) The `nonTerminatingMatchingRules` field and labels in WAF logs, plus label metrics.**

**Explanation:** WAF logs list Count matches under `nonTerminatingMatchingRules` and the labels added to each request. Samples for Count rules inside rule groups are not shown in the web ACL view, and Count-action rules inside rule groups do not emit web ACL dimension metrics. A Count match never changes the status code.

</details>

13. In the reference design, the Pod's NetworkPolicy admits ingress from an `ipBlock` with the ALB subnets rather than the client addresses. Why?
   - A) The ALB is a proxy, so the Pod IP target sees the ALB node's private address; the client address arrives in `X-Forwarded-For`.
   - B) NetworkPolicy cannot express IPv4 CIDR blocks.
   - C) CloudFront rewrites the client address to the VPC origin ENI only for HTTP/3.

<details>
<summary>Show Answer</summary>

**Answer: A) The ALB is a proxy, so the Pod IP target sees the ALB node's private address; the client address arrives in `X-Forwarded-For`.**

**Explanation:** The ELB guide says server access logs contain only the load balancer's address. The Kubernetes documentation warns that whether rewriting happens before or after NetworkPolicy processing depends on the plugin, cloud provider and Service implementation, so confirm the observed source on your CNI.

</details>

14. In the workbook's exercise, `rate-login` (window 300 s, limit 100, aggregate on IP, action Count) sees `198.51.100.20` send 640 `POST /login` requests in one 5-minute window. About how many requests from that address does the rule count, and why is the real number not exact?
   - A) 640, because Count counts every request that matches the scope-down statement.
   - B) About 540, the requests beyond the limit, and approximate because AWS WAF estimates the rate and detects a breach with a delay.
   - C) 100, because the limit caps the count.

<details>
<summary>Show Answer</summary>

**Answer: B) About 540, the requests beyond the limit, and approximate because AWS WAF estimates the rate and detects a breach with a delay.**

**Explanation:** A rate-based rule applies its action to further matching requests from an instance that exceeds the limit: 640 - 100 = 540. AWS WAF weights recent requests and limits near, not exactly at, the configured value. The trial reveals a false positive (a shared office NAT), which the plan removes with an IP set inside a `NotStatement` in the scope-down.

</details>

Completion: explain every answer with a rule from the workbook, and label your rule plan **worked scenario, not measured**.
