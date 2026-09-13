# Agentic AI Platform on EKS Quiz

Twenty questions on current APIs, execution boundaries and validation limits.

## 1. What does PagedAttention primarily improve?

<details>
<summary>Answer and explanation</summary>

KV-cache block management and memory waste. It does not compress model weights or guarantee fixed 2–4x throughput.
</details>

## 2. How does an inference gateway differ from a training executor?

<details>
<summary>Answer and explanation</summary>

A supported gateway/plugin handles inference routing, access and limits. Trainer/Ray and other systems execute training. Gateway installation alone does not enable every security or A/B feature.
</details>

## 3. What must match in a RAG vector store?

<details>
<summary>Answer and explanation</summary>

Actual embedding dimension, model revision, normalization, metric and ingestion/query behavior. A tenant field alone is not isolation; enforce authenticated retrieval scope with server-side filters.
</details>

## 4. What control model does LangGraph provide?

<details>
<summary>Answer and explanation</summary>

Stateful nodes, edges, conditional routing and cycles. A graph alone does not implement tool execution, persistent state or bounded retries.
</details>

## 5. How do Langfuse and DCGM differ?

<details>
<summary>Answer and explanation</summary>

Langfuse tracks instrumented calls, traces, usage and evaluation; DCGM reports device metrics. Token-cost estimates are not invoices and differ from infrastructure measurements such as GPU temperature.
</details>

## 6. What API shape does Kagent 0.10.1 use?

<details>
<summary>Answer and explanation</summary>

kagent.dev/v1alpha2 with spec.type and declarative/BYO. Use declarative.modelConfig and McpServer/Agent tool references, not invented top-level llm, arbitrary python/eval tool definitions or permissions fields.
</details>

## 7. What isolation does time-slicing inside MIG provide?

<details>
<summary>Answer and explanation</summary>

Distinguish isolation between MIG instances from sharing inside one instance. Time-slice users within one instance do not gain new memory/fault isolation or proportional compute guarantees.
</details>

## 8. Does continuous batching mean requests never wait?

<details>
<summary>Answer and explanation</summary>

No. Scheduling can admit work each step but token budgets, KV capacity, concurrency and queue limits can cause waiting. Measure actual workload behavior.
</details>

## 9. When does chunk size 1000 mean 1000 tokens?

<details>
<summary>Answer and explanation</summary>

When the selected splitter measures tokens with the appropriate tokenizer. RecursiveCharacterTextSplitter defaults to character counts. Evaluate model limits, semantic units and retrieval quality together.
</details>

## 10. What must be checked for vLLM autoscaling?

<details>
<summary>Answer and explanation</summary>

Actual vllm: metric names, model/Pod labels, adapters, queue/latency signals and one scaling owner. Allocation is not GPU utilization; avoid competing HPA/KEDA control of the same replicas.
</details>

## 11. What does the KV cache store?

<details>
<summary>Answer and explanation</summary>

Key/value representations of earlier tokens to reduce repeated computation. It differs from response caching; GQA/MQA, sliding windows and other architectures change memory accounting.
</details>

## 12. How are traces and spans handled by the current Langfuse SDK?

<details>
<summary>Answer and explanation</summary>

Create child span/generation observations under one trace with start_as_current_observation and record usage_details. The inspected SDK 4.15.2 has no old trace()/generation() methods. Define secret/raw-data logging boundaries too.
</details>

## 13. Why is hybrid search more than two search calls?

<details>
<summary>Answer and explanation</summary>

It needs RRF or calibrated score fusion, equivalent authorization filters, deduplication and recall evaluation. Scores from different retrievers are not automatically comparable.
</details>

## 14. What was wrong with the original SqliteSaver example?

<details>
<summary>Answer and explanation</summary>

Use from_conn_string as a context manager. :memory: is not durable and a PostgreSQL DSN is not SQLite. Reading history alone does not replay/resume, and thread_id is not authentication.
</details>

## 15. What do TP and PP partition?

<details>
<summary>Answer and explanation</summary>

TP partitions operations within layers; PP partitions layer stages. Choose from architecture/backend/network/memory constraints, not universal powers of two or fixed GPUs per model size.
</details>

## 16. Exercise: what should a current vLLM deployment validate?

<details>
<summary>Answer and explanation</summary>

Use the pinned image/model, GPU/cache/startupProbe and ClusterIP example in the [vLLM guide](../../ai-ml/02-vllm-deployment.md). Prepare namespace/drivers/devices. Schema checks without inference do not establish performance or availability.
</details>

## 17. Exercise: what should Langfuse deployment and Python tracing validate?

<details>
<summary>Answer and explanation</summary>

Use the current SDK example in the [chapter](../../ai-ml/03-agentic-ai-platform.md), file credentials, span linkage and flush/shutdown. Chart 2.1.0 includes web/worker, Postgres, Valkey, object storage, ClickHouse and operator prerequisites. Default secret environment delivery differs from file-only policy.
</details>

## 18. Exercise: how should a RAG retry loop terminate safely without evidence?

<details>
<summary>Answer and explanation</summary>

Keep original question separate from search_query, set retry and recursion bounds, generate with evidence, rewrite within budget, then abstain when none is found. The chapter verifies these paths and SQLite reopening using local deterministic callbacks.
</details>

## 19. Advanced: what boundaries matter for a financial consultation agent?

<details>
<summary>Answer and explanation</summary>

Design authenticated tenant/account scope, retrieval permissions, provider egress, least-privilege/idempotent/approved tools, minimal sensitive logging, audit and human handoff. Do not overwrite an existing requires_human=true with false in a later branch. A compliance_check function name or LLM decision does not certify regulatory compliance.
</details>

## 20. Advanced: how should multi-model routing, A/B and cost optimization be validated?

<details>
<summary>Answer and explanation</summary>

Use provider adapters/credentials and reject when no candidate meets allowed-provider, budget and quality constraints. Implement stable A/B assignment, real routing consumers and measured guardrails. Cache keys include tenant/authorization/model/retrieval revisions; cost estimates include routing calls, retries, caches and GPU fixed costs. Invented savings percentages are not results.
</details>

[Return to the chapter](../../ai-ml/03-agentic-ai-platform.md)
