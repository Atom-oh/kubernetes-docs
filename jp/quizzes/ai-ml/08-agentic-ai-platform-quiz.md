# EKS 上の Agentic AI Platform クイズ

現在の API、実行境界、検証上の制限に関する 20 問です。

## 1. PagedAttention は主に何を改善しますか？

<details>
<summary>回答と解説</summary>

KV-cache のブロック管理とメモリの無駄を改善します。モデルの重みを圧縮するものでも、固定の 2～4 倍のスループットを保証するものでもありません。
</details>

## 2. inference gateway は training executor とどのように異なりますか？

<details>
<summary>回答と解説</summary>

サポート対象の gateway/plugin は inference のルーティング、アクセス、制限を処理します。Trainer/Ray やその他のシステムが training を実行します。gateway のインストールだけで、すべてのセキュリティ機能や A/B 機能が有効になるわけではありません。
</details>

## 3. RAG vector store で一致させる必要があるものは何ですか？

<details>
<summary>回答と解説</summary>

実際の embedding dimension、model revision、normalization、metric、ingestion/query の動作です。tenant field だけでは分離になりません。server-side filter による認証済み retrieval scope を強制してください。
</details>

## 4. LangGraph はどのような control model を提供しますか？

<details>
<summary>回答と解説</summary>

stateful node、edge、conditional routing、cycle です。graph だけでは、tool execution、persistent state、bounded retry は実装されません。
</details>

## 5. Langfuse と DCGM はどのように異なりますか？

<details>
<summary>回答と解説</summary>

Langfuse は instrumented call、trace、usage、evaluation を追跡し、DCGM は device metric を報告します。token-cost の見積もりは請求書ではなく、GPU temperature のような infrastructure measurement とも異なります。
</details>

## 6. Kagent 0.10.1 はどのような API shape を使用しますか？

<details>
<summary>回答と解説</summary>

spec.type と declarative/BYO を含む kagent.dev/v1alpha2 です。架空の top-level llm、任意の python/eval tool definition、permissions field ではなく、declarative.modelConfig と McpServer/Agent tool reference を使用してください。
</details>

## 7. MIG 内の time-slicing はどのような isolation を提供しますか？

<details>
<summary>回答と解説</summary>

MIG instance 間の isolation と、1 つの instance 内での共有を区別してください。1 つの instance 内で time-slice を使用するユーザーは、新しい memory/fault isolation や比例した compute の保証を得るわけではありません。
</details>

## 8. continuous batching は request が決して待機しないことを意味しますか？

<details>
<summary>回答と解説</summary>

いいえ。scheduling は各 step で work を受け入れられますが、token budget、KV capacity、concurrency、queue limit により待機が発生する可能性があります。実際の workload の動作を測定してください。
</details>

## 9. chunk size 1000 が 1000 token を意味するのはいつですか？

<details>
<summary>回答と解説</summary>

選択した splitter が適切な tokenizer で token を計測する場合です。RecursiveCharacterTextSplitter はデフォルトで character count を使用します。model limit、semantic unit、retrieval quality をまとめて評価してください。
</details>

## 10. vLLM autoscaling では何を確認する必要がありますか？

<details>
<summary>回答と解説</summary>

実際の vllm: metric name、model/Pod label、adapter、queue/latency signal、および 1 つの scaling owner です。allocation は GPU utilization ではありません。同じ replica を HPA/KEDA が競合して制御することを避けてください。
</details>

## 11. KV cache は何を保存しますか？

<details>
<summary>回答と解説</summary>

繰り返し計算を削減するための、以前の token の key/value representation です。response caching とは異なります。GQA/MQA、sliding window、その他の architecture により memory accounting は変化します。
</details>

## 12. 現在の Langfuse SDK では trace と span はどのように処理されますか？

<details>
<summary>回答と解説</summary>

start_as_current_observation を使用して 1 つの trace 配下に child span/generation observation を作成し、usage_details を記録します。確認した SDK 4.15.2 には、以前の trace()/generation() method はありません。secret/raw-data logging の境界も定義してください。
</details>

## 13. なぜ hybrid search は単なる 2 回の search call 以上のものなのですか？

<details>
<summary>回答と解説</summary>

RRF またはキャリブレーション済み score fusion、同等の authorization filter、deduplication、recall evaluation が必要です。異なる retriever の score は自動的に比較可能になるわけではありません。
</details>

## 14. 元の SqliteSaver example の何が間違っていましたか？

<details>
<summary>回答と解説</summary>

from_conn_string は context manager として使用します。:memory: は durable ではなく、PostgreSQL DSN は SQLite ではありません。history を読み取るだけでは replay/resume にならず、thread_id は authentication ではありません。
</details>

## 15. TP と PP は何を partition しますか？

<details>
<summary>回答と解説</summary>

TP は layer 内の operation を partition し、PP は layer stage を partition します。モデルサイズごとの普遍的な 2 の累乗や固定 GPU 数ではなく、architecture/backend/network/memory の制約に基づいて選択してください。
</details>

## 16. 演習: 現在の vLLM deployment では何を検証すべきですか？

<details>
<summary>回答と解説</summary>

[vLLM guide](../../ai-ml/02-vllm-deployment.md) の pinned image/model、GPU/cache/startupProbe、ClusterIP example を使用してください。namespace/driver/device を準備します。inference を伴わない schema check では、performance や availability を確立できません。
</details>

## 17. 演習: Langfuse deployment と Python tracing では何を検証すべきですか？

<details>
<summary>回答と解説</summary>

[chapter](../../ai-ml/03-agentic-ai-platform.md) の現在の SDK example、file credential、span linkage、flush/shutdown を使用してください。Chart 2.1.0 には web/worker、Postgres、Valkey、object storage、ClickHouse、operator prerequisite が含まれます。デフォルトの secret environment delivery は、file-only policy と異なります。
</details>

## 18. 演習: evidence がない場合、RAG retry loop はどのように安全に終了すべきですか？

<details>
<summary>回答と解説</summary>

元の question は search_query と分離したままにし、retry と recursion の上限を設定し、evidence を用いて generate し、budget 内で rewrite してから、何も見つからない場合は abstain してください。この chapter では、local deterministic callback を使用して、これらの path と SQLite の再オープンを検証しています。
</details>

## 19. 高度: financial consultation agent ではどの境界が重要ですか？

<details>
<summary>回答と解説</summary>

認証済みの tenant/account scope、retrieval permission、provider egress、least-privilege/idempotent/approved tool、最小限の sensitive logging、audit、human handoff を設計してください。後続の branch で、既存の requires_human=true を false で上書きしてはいけません。compliance_check function name や LLM decision は regulatory compliance を証明するものではありません。
</details>

## 20. 高度: multi-model routing、A/B、cost optimization はどのように検証すべきですか？

<details>
<summary>回答と解説</summary>

provider adapter/credential を使用し、allowed-provider、budget、quality の制約を満たす candidate がない場合は拒否します。安定した A/B assignment、実際の routing consumer、測定済みの guardrail を実装してください。cache key には tenant/authorization/model/retrieval revision を含めます。cost estimate には routing call、retry、cache、GPU fixed cost を含めます。架空の savings percentage は結果ではありません。
</details>

[chapter に戻る](../../ai-ml/03-agentic-ai-platform.md)
