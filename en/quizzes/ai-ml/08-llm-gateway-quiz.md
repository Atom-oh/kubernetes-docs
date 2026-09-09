# LLM Gateway (Inference Gateway) Quiz

This quiz tests your understanding of how an LLM gateway works: the control/data-plane split, two-phase governance, the cache invariant, the auto-routing layers, the PII guard, policy-prompt injection versus prompt-injection defense, and context-aware routing.

## Quiz Overview
- API gateway vs. LLM gateway
- Data plane / control plane split and budget leases
- Two-phase governance (PreCheck / Settle)
- The cache invariant and verbatim forwarding
- The seven auto-routing layers and their invariants
- The PII guard pipeline
- System prompt injection and prompt-injection defense
- Context awareness (prefix affinity, context windows)

## Multiple Choice Questions

### 1. Why is LLM gateway governance designed as two phases, PreCheck then Settle?

A. Streaming responses are compressed and cannot be parsed in one pass
B. The cost of a request (especially output tokens) is only known after the model finishes, yet the deny must be decided before the model is called
C. Provider APIs require two authentications per request
D. The audit hash chain needs two records per request

<details>
<summary>Show Answer</summary>

**Answer: B. The cost of a request (especially output tokens) is only known after the model finishes, yet the deny must be decided before the model is called**

**Explanation:**
An HTTP API gateway knows the cost (one request) at request time, but an LLM gateway's unit of cost is the token and the model decides the output count. PreCheck therefore judges rate, quota, and budget against an **estimate** (input tokens + `max_tokens`) and denies before any counter is charged; Settle debits quota with the **actual usage** the provider reports and trues up the difference (over-estimate ⇒ refund, under-estimate ⇒ the bucket goes negative). Debiting the estimate up front is an optimistic lock that stops concurrent requests from all observing "budget remaining."

</details>

### 2. Which statement correctly describes the "cache invariant"?

A. The gateway must cache every response and reuse it for identical questions
B. When the ingress protocol equals the provider protocol, the request body must be forwarded byte-for-byte (RawBody) so the prompt-cache prefix is not broken
C. The cache hit rate must always exceed 90 %
D. The gateway must always strip `cache_control` fields

<details>
<summary>Show Answer</summary>

**Answer: B. When the ingress protocol equals the provider protocol, the request body must be forwarded byte-for-byte (RawBody) so the prompt-cache prefix is not broken**

**Explanation:**
Anthropic's prompt cache and vLLM's prefix cache hash the **exact prefix** of the body (tools → system → messages). Merely parsing and re-serializing JSON (key order, whitespace, number formatting) changes the prefix and misses the whole cache. Coding-agent traffic is more than 90 % cache hits and a cache read costs 10 % of the base input rate, so breaking the invariant can multiply the bill by up to 10×. That is why body-mutating filters (PII masking, policy-prompt injection) must be explicit opt-ins with a cost warning.

</details>

### 3. Why must RBAC be checked **again** after a fallback or budget-tier substitution in auto routing?

A. The substituted model has a different price, so the budget must be recomputed
B. Targets appended by fallback or substitution never went through the original allow-list check, so without a re-check the fallback path becomes a privilege bypass
C. An open circuit breaker invalidates the RBAC cache
D. A provider change requires re-issuing the virtual key

<details>
<summary>Show Answer</summary>

**Answer: B. Targets appended by fallback or substitution never went through the original allow-list check, so without a re-check the fallback path becomes a privilege bypass**

**Explanation:**
The allow-list check runs against the model the client asked for. When L1 (unrouted-model fallback), L3 (budget-tier substitution), or L6 (chain extension on an upstream 404) then adds a new target, that target was never checked. If a team is allowed only `haiku` and a fallback appends `opus`, it goes through unchecked unless re-verified. Every ingress handler must therefore run a re-check such as `FilterModelAllowed` after routing, and substitution must obey the invariant "narrow only, never widen."

</details>

### 4. Why is gateway failover (retrying on another provider) for a streaming response allowed only **before the first token (TTFT)**?

A. SSE frame formats differ between providers and cannot be switched mid-stream
B. Retrying after the first token duplicates what the client already saw, double-bills tokens, and stitches two responses together
C. The circuit breaker does not change state after the first token
D. The audit record has already been written and cannot be modified

<details>
<summary>Show Answer</summary>

**Answer: B. Retrying after the first token duplicates what the client already saw, double-bills tokens, and stitches two responses together**

**Explanation:**
On a mid-stream failure the client has already rendered part of the answer. Regenerating from scratch on a new provider (1) bills the same input tokens twice, (2) splices two models' different outputs together, and (3) may conflict with `tool_use` blocks already emitted. The correct behavior is an `error` frame and a closed stream; the client decides whether to retry. Circuit breakers and priority chains intervene only until the first byte leaves.

</details>

### 5. Why is the PII masking filter designed as an "explicit opt-in with a runtime cost warning"?

A. Regex masking consumes a lot of CPU
B. Masking mutates the request body, which breaks the verbatim-forwarding cache invariant and can raise cost sharply through prompt-cache misses
C. Models cannot understand masked text
D. Legal consent is required from the user

<details>
<summary>Show Answer</summary>

**Answer: B. Masking mutates the request body, which breaks the verbatim-forwarding cache invariant and can raise cost sharply through prompt-cache misses**

**Explanation:**
Masking substitutes text, so re-serialization is unavoidable and the prefix changes. If every request produces a different placeholder (`<EMAIL_7f3a>`) every turn is a miss. Mitigations are (1) deterministic, session-scoped pseudonyms (`<EMAIL_1>`, same value ⇒ same placeholder) to stabilize the prefix, and (2) a header such as `x-<gateway>-cache-degraded` on masked teams' responses so the cost impact is visible. A gateway that masks silently leaves users discovering the reason on the invoice. A masker error must also fail closed — never forward the raw text.

</details>

### 6. What "bypass" problem must a gateway handle with respect to Amazon Bedrock Guardrails?

A. Guardrails do not work on streaming responses
B. A guardrail is a parameter of the `InvokeModel`/`Converse` API call, so unless the gateway sets `guardrailIdentifier` on the SDK call, a guardrail created in the console is never applied
C. Guardrail names differ per region and conflict with routing
D. Guardrails do not recognize virtual keys

<details>
<summary>Show Answer</summary>

**Answer: B. A guardrail is a parameter of the `InvokeModel`/`Converse` API call, so unless the gateway sets `guardrailIdentifier` on the SDK call, a guardrail created in the console is never applied**

**Explanation:**
Bedrock Guardrails are not applied "for free" by a proxy that forwards bytes; they are API-call parameters (`guardrailIdentifier`, `guardrailVersion`). With a gateway in the middle, the data plane's actual SDK call must set them. The safe design enforces a provider-level default guardrail and lets teams pick a *different* one, but offers no *off* switch. Gateway-side PII masking and provider-side guardrails complement rather than replace each other.

</details>

### 7. When the gateway injects an organizational policy prompt into an Anthropic Messages request, why must the policy block go at the **front** of the `system` array?

A. The model only recognizes the first block as the system prompt
B. The prompt-cache prefix is computed from the front, so identical bytes at the front keep the prefix stable and do not nullify the client's own `cache_control` breakpoints
C. Bedrock Converse ignores everything after the first block
D. OpenAI-compatible APIs do not support a `system` array

<details>
<summary>Show Answer</summary>

**Answer: B. The prompt-cache prefix is computed from the front, so identical bytes at the front keep the prefix stable and do not nullify the client's own `cache_control` breakpoints**

**Explanation:**
The prefix is computed tools → system → messages. A byte-identical policy block at the front makes the first request a cache write (1.25×) and all later ones reads (0.1×). Placing it **after** the client's `cache_control` block defeats the breakpoint the client chose. Companion rules: idempotency (do not add a second block with the same hash), never delete the client's system prompt (harnesses such as Claude Code depend on it), record the policy version and hash in audit, and remember that a system prompt is a nudge, not a security boundary.

</details>

### 8. Of the five prompt-injection defense layers, which one carries the "real enforcement," and why?

A. Policy prompt injection — because the model follows instructions
B. Trust-boundary marking (spotlighting) — because delimiters make the model impossible to fool
C. The tool-use allow-list — because whatever the model decides, a `tool_use` block that does not pass the gateway is never executed
D. The injection scanner — because every attack pattern can be caught with regex

<details>
<summary>Show Answer</summary>

**Answer: C. The tool-use allow-list — because whatever the model decides, a `tool_use` block that does not pass the gateway is never executed**

**Explanation:**
The model cannot distinguish trust levels inside a request (operator, application, user, external data), so policy-prompt injection and trust-boundary marking only raise the odds, and the injection scanner has false positives and negatives. The tool-use allow-list inspects the **response's** `tool_use` blocks and rejects tool names absent from the team policy or dangerous argument patterns (`curl … | sh`). It is a boundary enforced by the gateway regardless of the model's judgment, so even a fully successful indirect injection cannot get an execution command to the client. In a stream, only that `tool_use` block is buffered until all `input_json_delta` frames arrive.

</details>

### 9. In a distributed deployment with one data plane per node, which statement about the budget **lease** mechanism that keeps a team's hard cap "bounded" is correct?

A. Every data plane calls the control plane synchronously on each request to read the exact balance
B. Each data plane receives an allowance from the control plane as a lease and debits it locally; worst-case overspend is bounded by the sum of outstanding grants
C. The budget counter lives in Redis so all replicas agree exactly
D. When the control plane dies, all budget limits are lifted

<details>
<summary>Show Answer</summary>

**Answer: B. Each data plane receives an allowance from the control plane as a lease and debits it locally; worst-case overspend is bounded by the sum of outstanding grants**

**Explanation:**
A synchronous call per request (A) puts the control plane in the request path and creates a SPOF. With leases, each heartbeat reports "spent this period" and receives a fresh allowance, so the request path stays local and the overspend ceiling is `Σ outstanding grants`, not `N × limit`. If the control plane dies, leases expire and hard-cap teams fail closed with 402 — the one intended exception to "no SPOF," which is why policy must distinguish lease-backed hard-cap teams from soft-limit (warn) teams.

</details>

### 10. In a context-aware gateway, which routing layers may consume "infrastructure context" (provider latency, circuit-breaker state, pod KV-cache utilization), and which must not?

A. The policy (RBAC) layer, so slow regions are bypassed automatically
B. Only the availability (L6) and endpoint-picking (L7) layers; it must never change a policy (L2) decision
C. The name-resolution layer (L1), by rewriting aliases
D. Any layer, freely

<details>
<summary>Show Answer</summary>

**Answer: B. Only the availability (L6) and endpoint-picking (L7) layers; it must never change a policy (L2) decision**

**Explanation:**
Infrastructure signals answer the availability question "which provider/region/pod is healthy right now." If they changed the policy question "may this team use this region," the result would be "Bedrock was slow so we sent it to a region that is not allowed" — a compliance violation, not an incident. By the same principle, if the intent classifier (L4) is down the request goes to the model it asked for (the router must not be a SPOF), and session prefix affinity pins a conversation to one cache domain (pod or provider) to avoid cold caches.

</details>

### 11. Which rule must a gateway follow when proxying `count_tokens`-style endpoints?

A. Return 402 when the budget is exceeded so the client abandons the request
B. Apply RBAC and routing but touch no governance counter, and return 200 with an estimate even on failure
C. Never forward to the provider; divide the byte count by 4 instead
D. Return 400 when the context window is exceeded

<details>
<summary>Show Answer</summary>

**Answer: B. Apply RBAC and routing but touch no governance counter, and return 200 with an estimate even on failure**

**Explanation:**
Some coding agents crash their session when a `count_tokens` call returns a non-200. Counting tokens is not consumption, so rate, quota, and budget counters are not debited, and on an upstream failure the gateway still returns 200 with a heuristic estimate. The fast 400 for context-window overflow (naming both numbers) belongs on the actual generation request (`/v1/messages`) before PreCheck, never on `count_tokens`.

</details>

### 12. The rule "never put key ids or user ids into `/metrics` labels" protects which two properties?

A. Response speed and compression ratio
B. Prevention of cardinality explosion and prevention of secret/identity leakage
C. Grafana dashboard compatibility and color consistency
D. OTLP convertibility and trace linking

<details>
<summary>Show Answer</summary>

**Answer: B. Prevention of cardinality explosion and prevention of secret/identity leakage**

**Explanation:**
`/metrics` is usually exposed without authentication. Unbounded label values such as key ids, user ids, or the un-normalized requested model name explode the Prometheus series count and, at the same time, reveal who uses which model to anyone who can scrape. Label values are therefore restricted to values declared in config (team, canonical model, provider), and requests rejected before resolution collapse into a sentinel such as `_rejected`. For the same reason prompt text never enters trace span attributes, and upstream error bodies (which may contain ARNs) are scrubbed before relaying.

</details>
