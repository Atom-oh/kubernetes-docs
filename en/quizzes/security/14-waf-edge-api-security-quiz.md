# WAF and Origin Protection Quiz

> **Last Updated**: October 15, 2026

[Read the chapter and primary sources](../../security/14-waf-edge-api-security.md)

### 1. Which API Gateway resource supports the documented direct WAF association?

- A) REST API
- B) Every HTTP API
- C) Every WebSocket API
- D) Any NLB listener

<details>
<summary>Show Answer</summary>

**Answer: A) REST API**

**Explanation:** Use the supported-resource list. CloudFront protection in front of a resource is different from direct association.

</details>

### 2. What happens after an early broad Allow matches?

- A) Later rules always continue
- B) Evaluation terminates, possibly skipping later protection
- C) Only Count rules stop
- D) Default Block always overrides it

<details>
<summary>Show Answer</summary>

**Answer: B) Evaluation terminates, possibly skipping later protection**

**Explanation:** Allow and Block terminate; Count continues. Review rule priority and narrowly scoped exceptions.

</details>

### 3. Which body-limit comparison is correct?

- A) ALB always inspects 64 KB
- B) All resources have identical limits
- C) ALB is fixed at 8 KB; CloudFront defaults to 16 KB with supported increases to 64 KB
- D) Body limits equal upload limits

<details>
<summary>Show Answer</summary>

**Answer: C) ALB is fixed at 8 KB; CloudFront defaults to 16 KB with supported increases to 64 KB**

**Explanation:** Inspection sizes are distinct from application upload limits; gRPC body inspection is also excluded in the AWS documentation.

</details>

### 4. Does oversize MATCH always block the request?

- A) Yes, regardless of action
- B) Yes, even inside NOT
- C) Yes, even after an earlier Allow
- D) No; it matches the statement and final behavior depends on action/composition

<details>
<summary>Show Answer</summary>

**Answer: D) No; it matches the statement and final behavior depends on action/composition**

**Explanation:** Check action, logical composition and earlier terminating rules. MATCH is not an independent Block action.

</details>

### 5. Why is the CloudFront address range insufficient to identify your distribution?

- A) Other CloudFront paths can use the same infrastructure
- B) CloudFront cannot use HTTPS
- C) ALB has no listener rules
- D) All origin headers are cryptographic signatures

<details>
<summary>Show Answer</summary>

**Answer: A) Other CloudFront paths can use the same infrastructure**

**Explanation:** Combine network restrictions with a protected origin-header/listener condition or supported VPC-origin design, and test bypasses.

</details>

### 6. What happens to a direct forwarded-IP statement when its header is absent, without an enclosing NOT?

- A) Fallback always blocks
- B) The statement has no match; absence differs from malformed fallback
- C) The header is automatically authenticated
- D) It always uses the last address

<details>
<summary>Show Answer</summary>

**Answer: B) The statement has no match; absence differs from malformed fallback**

**Explanation:** Missing headers do not invoke malformed fallback. An enclosing NOT could invert no match into match. Geo/ASN/rate use the first address; IP sets use their configured FIRST/LAST/ANY selection.

</details>

### 7. Which statement about rate rules is correct?

- A) They are exact per-second quotas
- B) Changing the window preserves every counter
- C) Tracking is approximate and relevant setting changes reset counters
- D) Client-controlled aggregation keys prevent evasion

<details>
<summary>Show Answer</summary>

**Answer: C) Tracking is approximate and relevant setting changes reset counters**

**Explanation:** Test window, aggregation, resets, shared NAT and attacker-controlled key variation; enforce business quotas in the application.

</details>

### 8. What does WAF log redaction automatically establish?

- A) All sampled requests are redacted
- B) No sensitive data can appear anywhere
- C) No log loss is possible
- D) Only configured log-field handling; sampling/data protection need separate review

<details>
<summary>Show Answer</summary>

**Answer: D) Only configured log-field handling; sampling/data protection need separate review**

**Explanation:** Inspect actual collected data. Log redaction does not automatically protect request sampling or Security Lake collection.

</details>
