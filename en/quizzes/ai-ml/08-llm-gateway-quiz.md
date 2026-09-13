# LLM Gateway (Inference Gateway) Quiz

This quiz checks the proposed design’s guarantees and limits: reservations, cache semantics, authorization, streaming, PII, guardrails and context-aware routing. It does not assert that every named gateway implements the design.

## Multiple Choice Questions

### 1. Why does a gateway reserve resources before dispatch and settle afterwards?

- A. SSE requires two authentications
- B. Final usage is unknown at admission, so concurrent requests need atomic quota and monetary reservations
- C. Every HTTP error is free
- D. An input-token estimate guarantees a hard monetary cap

<details>
<summary>Show Answer</summary>

**Answer: B. Final usage is unknown at admission, so concurrent requests need atomic quota and monetary reservations**

**Explanation:**
Reserve against each call’s inspected input and a conservative cost bound before dispatch, including billable router, filter, guardrail and retry calls. Main rejection does not erase auxiliary charges already incurred. A TPM debit alone does not reserve money. Replace reservations with actual charges idempotently; interrupted streams may lack final usage, so retain an appropriate reservation until reconciliation rather than assuming zero cost.

</details>

### 2. Which statement about prompt-cache preservation is correct?

- A. Every raw HTTP JSON byte is part of every provider cache key
- B. Preserve provider-specific prompt/token prefixes and supported cache controls; JSON envelope formatting alone need not invalidate reuse
- C. Coding-agent cache hit rates always exceed 90%
- D. Cross-protocol conversion can never warm a target cache

<details>
<summary>Show Answer</summary>

**Answer: B. Preserve provider-specific prompt/token prefixes and supported cache controls; JSON envelope formatting alone need not invalidate reuse**

**Explanation:**
Anthropic describes identical prompt segments through cache breakpoints; vLLM hashes token blocks and additional context. Stable conversion can produce reusable target-side prefixes. Required policy transformations take precedence over raw forwarding, and cache savings must be measured for the selected model, TTL and workload.

</details>

### 3. Why reauthorize after fallback or budget-tier substitution?

- A. Every fallback is automatically cheaper
- B. The new model/provider/region may not have passed the original authorization and privacy checks
- C. Circuit breakers grant temporary permissions
- D. A similar model name proves equivalent capabilities

<details>
<summary>Show Answer</summary>

**Answer: B. The new model/provider/region may not have passed the original authorization and privacy checks**

**Explanation:**
Recheck model, region, privacy, required capabilities and budget for the actual target. Keep the original model only if it still passes every check; otherwise deny. Alias resolution and lexical version ordering are not authorization.

</details>

### 4. When must transparent failover stop for a streamed response?

- A. Only after the first printable text token
- B. Once downstream headers or stateful/tool events commit the response, even before text tokens
- C. Only after the final usage event
- D. Never; two providers can safely share one response

<details>
<summary>Show Answer</summary>

**Answer: B. Once downstream headers or stateful/tool events commit the response, even before text tokens**

**Explanation:**
After commitment, a transparent retry can duplicate content or tool activity and incur additional charges. Terminate with the client protocol’s error semantics and record incomplete usage. Before commitment, retries still need attempt/deadline bounds and accounting for possible provider charges. Output must be inspected before release; buffering can increase user-visible TTFT.

</details>

### 5. How should privacy requirements interact with cache cost?

- A. Disable masking whenever the prefix cache misses
- B. Enforce required privacy controls, use scoped stable transformations where safe, and measure cache/latency impact
- C. Inspect only user text because tool arguments never contain PII
- D. Restore any placeholder supplied by the caller

<details>
<summary>Show Answer</summary>

**Answer: B. Enforce required privacy controls, use scoped stable transformations where safe, and measure cache/latency impact**

**Explanation:**
Sensitive data can occur in tools, results and attachments as well as text. Unsupported inspection must block or use an approved destination. Bind mappings to authenticated tenant/principal/session and authorize restoration; mapping loss can affect correctness. Detection has false negatives, so neither a gateway nor a classifier proves zero disclosure.

</details>

### 6. Which Bedrock Guardrails integration is appropriate?

- A. Creating a guardrail automatically applies it to all calls
- B. Use the selected API’s guardrail fields, validate scope and enforce approved IDs/versions where supported
- C. Use asynchronous mode to guarantee sensitive-information masking
- D. Use the same top-level JSON fields in every Bedrock API

<details>
<summary>Show Answer</summary>

**Answer: B. Use the selected API’s guardrail fields, validate scope and enforce approved IDs/versions where supported**

**Explanation:**
Converse uses guardrailConfig; InvokeModel uses guardrailIdentifier/guardrailVersion operation parameters (HTTP headers). guardContent can scope evaluation, and ApplyGuardrail evaluates content separately without model invocation. Appropriate IAM conditions and bypass prevention reinforce gateway policy. Async streaming can release content before inspection and does not support sensitive-information masking; logs/traces also need protection.

</details>

### 7. What matters when inserting a gateway policy prompt near a cache breakpoint?

- A. Every later request is guaranteed a cache hit
- B. Keep policy content stable in the intended cache boundary and deduplicate only authenticated gateway metadata
- C. A block after a cache marker always invalidates the earlier segment
- D. A caller-supplied matching hash proves the policy was enforced

<details>
<summary>Show Answer</summary>

**Answer: B. Keep policy content stable in the intended cache boundary and deduplicate only authenticated gateway metadata**

**Explanation:**
Cache reuse depends on identical supported segments, model requirements, minimum length, scope and TTL. A later block lies outside an earlier cached segment rather than necessarily invalidating it. A copied policy marker must not suppress mandatory insertion or scanning. Prompts are guidance, not executable authorization.

</details>

### 8. Where must tool authorization ultimately be enforced?

- A. Only in a system prompt
- B. Only through regex matching of dangerous shell strings
- C. At the tool executor, with gateway output checks as an additional layer
- D. Only after the provider returns final usage

<details>
<summary>Show Answer</summary>

**Answer: C. At the tool executor, with gateway output checks as an additional layer**

**Explanation:**
Gateways should buffer and validate complete tool-call arguments, but cannot cover bypasses or provider-side tools that have already executed. The executor needs authenticated identity, resource/argument authorization, schema validation, least privilege, sandboxing and sensitive-action approval. Model role labels and tool names alone are not trust proofs.

</details>

### 9. Which invariant supports conservative distributed monetary budgets?

- A. Every replica may independently spend the full team limit
- B. Spent plus outstanding reserved grants stays within the limit; reservations and reconciliation are durable and idempotent
- C. The sum of grants is automatically the worst-case overspend bound
- D. Expired grants can always be reissued immediately

<details>
<summary>Show Answer</summary>

**Answer: B. Spent plus outstanding reserved grants stays within the limit; reservations and reconciliation are durable and idempotent**

**Explanation:**
Grants deducted from available budget are reserved capacity, not an overspend allowance. Use conservative cost bounds, atomic local admission, durable IDs and reconciliation. Expiry stops new admissions but unresolved work or reports prevent safe reclamation. Metered helper, main-model and output-check calls consume the same budget through their own reservations. Monetary leases do not automatically globalize rate counters.

</details>

### 10. How may infrastructure context influence routing?

- A. A slow permitted region permits any faster region
- B. Health/load can select among already authorized destinations, never widen model/region/privacy permissions
- C. A source endpoint region proves all processing occurs there
- D. Classifier failure disables budget policy

<details>
<summary>Show Answer</summary>

**Answer: B. Health/load can select among already authorized destinations, never widen model/region/privacy permissions**

**Explanation:**
Apply health signals to availability/endpoint decisions inside the policy boundary. Bedrock inference profiles may route beyond the source region, so check all destinations. Final context fit must include transformed input plus the target’s output/reasoning allowance. Fallback to the original model is allowed only if every required check still passes.

</details>

### 11. How should a gateway handle token-counting endpoints?

- A. Always return HTTP 200, including for unauthorized requests
- B. Preserve authentication, authorization, validation errors and independent rate limits; label any optional approximate fallback
- C. Pretend a bytes/4 estimate is the provider’s exact count
- D. Ignore request size and CPU limits because counting is not inference

<details>
<summary>Show Answer</summary>

**Answer: B. Preserve authentication, authorization, validation errors and independent rate limits; label any optional approximate fallback**

**Explanation:**
Counting can have provider-specific validation failures and its own RPM limits. It is not an inference spend debit, but it consumes gateway/provider resources. Optional approximate fallback cannot override a denial, conceal its provenance or guarantee exact context fit. A product-specific compatibility shim is not a universal API requirement.

</details>

### 12. Why avoid user/key IDs and raw prompts in metrics labels?

- A. To make SSE compressed
- B. To bound cardinality and reduce identity/content disclosure; scrape access must still be restricted
- C. Because metrics can never contain team labels
- D. Because encryption eliminates all label risks

<details>
<summary>Show Answer</summary>

**Answer: B. To bound cardinality and reduce identity/content disclosure; scrape access must still be restricted**

**Explanation:**
Use reviewed bounded labels such as canonical model/provider and, where appropriate, configured team. Protect metrics/admin endpoints and avoid prompts in trace attributes or errors. Version semantic conventions and verify exporter naming. Low cardinality does not by itself authorize public access.

</details>
