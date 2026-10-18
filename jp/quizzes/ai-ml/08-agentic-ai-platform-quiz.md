# EKS 上の Agentic AI Platform クイズ

現在の API、実行境界、検証上の制限に関する 20 問です。

## 1. PagedAttention は主に何を改善しますか？

<details>
<summary>回答と解説</summary>

KV-cache のブロック管理を改善し、メモリの無駄を減らします。モデルの重みを圧縮するものではなく、スループットが必ず 2～4 倍になるわけでもありません。
</details>

## 2. inference gateway は training executor とどのように異なりますか？

<details>
<summary>回答と解説</summary>

対応する gateway／plugin は推論のルーティング、アクセス制御、制限を扱います。Trainer／Ray などのシステムがトレーニングを実行します。gateway をインストールしただけで、すべてのセキュリティ機能や A/B 機能が有効になるわけではありません。
</details>

## 3. RAG vector store で一致させる必要があるものは何ですか？

<details>
<summary>回答と解説</summary>

実際の埋め込み次元、モデルのリビジョン、正規化方法、距離指標、取り込み／検索の動作を一致させます。tenant field だけでは分離になりません。サーバー側フィルターで、認証済みの検索範囲を強制してください。
</details>

## 4. LangGraph はどのような control model を提供しますか？

<details>
<summary>回答と解説</summary>

stateful node、edge、conditional routing、cycle です。graph だけでは、tool execution、persistent state、bounded retry は実装されません。
</details>

## 5. Langfuse と DCGM はどのように異なりますか？

<details>
<summary>回答と解説</summary>

Langfuse は計測コードを入れた呼び出し、trace、利用量、評価結果を追跡し、DCGM は GPU の device metric を報告します。token cost の見積もりは請求額ではなく、GPU 温度などのインフラ計測値とも異なります。
</details>

## 6. Kagent 0.10.1 はどのような API shape を使用しますか？

<details>
<summary>回答と解説</summary>

`spec.type` と declarative／BYO を使う `kagent.dev/v1alpha2` API です。架空の top-level `llm`、任意の `python`／`eval` tool definition、`permissions` field ではなく、`declarative.modelConfig` と `McpServer`／`Agent` の tool reference を使ってください。
</details>

## 7. MIG 内の time-slicing はどのような isolation を提供しますか？

<details>
<summary>回答と解説</summary>

MIG instance 間の分離と、1 つの instance 内での共有を区別してください。同一 instance 内で time-slicing しても、新たなメモリ／障害分離が得られたり、compute 能力が比例配分されたりする保証はありません。
</details>

## 8. continuous batching は request が決して待機しないことを意味しますか？

<details>
<summary>回答と解説</summary>

いいえ。scheduling は各 step で work を受け入れられますが、token budget、KV capacity、concurrency、queue limit により待機が発生する可能性があります。実際の workload の動作を測定してください。
</details>

## 9. chunk size 1000 が 1000 token を意味するのはいつですか？

<details>
<summary>回答と解説</summary>

選択した splitter が適切な tokenizer を使って token 数を計測する場合です。`RecursiveCharacterTextSplitter` は既定で文字数を使います。モデルの上限、意味上のまとまり、検索品質を合わせて評価してください。
</details>

## 10. vLLM autoscaling では何を確認する必要がありますか？

<details>
<summary>回答と解説</summary>

実際の `vllm:` メトリクス名、model／Pod label、adapter、queue／latency の指標、そして単一の scaling owner を確認します。GPU の割当量は GPU 使用率そのものではありません。同じ replica 数を HPA と KEDA が競合して制御しないようにしてください。
</details>

## 11. KV cache は何を保存しますか？

<details>
<summary>回答と解説</summary>

以前の token に対する key/value 表現を保持し、同じ計算の繰り返しを減らします。response caching とは異なるものです。GQA／MQA、sliding window など、モデルの architecture によって必要なメモリ量の計算は変わります。
</details>

## 12. 現在の Langfuse SDK では trace と span はどのように処理されますか？

<details>
<summary>回答と解説</summary>

`start_as_current_observation` を使って 1 つの trace の下に子 span／generation observation を作成し、`usage_details` を記録します。確認した SDK 4.15.2 には、旧 `trace()`／`generation()` メソッドはありません。secret や生データをログに記録する範囲も定義してください。
</details>

## 13. なぜ hybrid search は単なる 2 回の search call 以上のものなのですか？

<details>
<summary>回答と解説</summary>

RRF またはキャリブレーション済み score fusion、同等の authorization filter、deduplication、recall evaluation が必要です。異なる retriever の score は自動的に比較可能になるわけではありません。
</details>

## 14. 元の SqliteSaver example の何が間違っていましたか？

<details>
<summary>回答と解説</summary>

`from_conn_string` は context manager として使います。`:memory:` は永続化されず、PostgreSQL DSN は SQLite 用ではありません。履歴を読むだけでは replay／resume にならず、`thread_id` は認証情報ではありません。
</details>

## 15. TP と PP は何を partition しますか？

<details>
<summary>回答と解説</summary>

TP は layer 内の演算を分割し、PP は layer の段階を分割します。常に 2 の累乗にする、あるいはモデルサイズごとに GPU 数を固定するといった決め方ではなく、architecture、backend、network、memory の制約に基づいて選んでください。
</details>

## 16. 演習: 現在の vLLM deployment では何を検証すべきですか？

<details>
<summary>回答と解説</summary>

[vLLM ガイド](../../ai-ml/02-vllm-deployment.md)にある固定バージョンの image／model、GPU／cache／startupProbe、ClusterIP の例を使います。namespace、driver、device を準備してください。推論を実行しない schema check では、性能や可用性は確認できません。
</details>

## 17. 演習: Langfuse deployment と Python tracing では何を検証すべきですか？

<details>
<summary>回答と解説</summary>

[章のガイド](../../ai-ml/03-agentic-ai-platform.md)にある現在の SDK 例を使い、ファイルからの credential 読み込み、span の関連付け、flush／shutdown を検証します。Chart 2.1.0 には web／worker、Postgres、Valkey、object storage、ClickHouse、operator の前提条件が含まれます。既定の Secret 環境変数への受け渡しは、ファイルのみを許可するポリシーとは異なります。
</details>

## 18. 演習: evidence がない場合、RAG retry loop はどのように安全に終了すべきですか？

<details>
<summary>回答と解説</summary>

元の質問と `search_query` を分けたままにし、retry と recursion に上限を設定します。根拠に基づいて回答を生成し、予算内で検索クエリを書き換え、それでも根拠が見つからなければ回答を保留してください。この章では、ローカルの決定論的 callback を使い、これらの経路と SQLite を再度開く処理を検証しています。
</details>

## 19. 高度: financial consultation agent ではどの境界が重要ですか？

<details>
<summary>回答と解説</summary>

認証済みの tenant／account 範囲、検索権限、provider への egress、最小権限で冪等性があり承認済みの tool、機微情報の最小限のログ記録、監査、担当者への引き継ぎを設計してください。後続の branch で、既存の `requires_human=true` を `false` で上書きしてはいけません。`compliance_check` という関数名や LLM の判断だけでは、規制への準拠は証明されません。
</details>

## 20. 高度: multi-model routing、A/B、cost optimization はどのように検証すべきですか？

<details>
<summary>回答と解説</summary>

provider adapter／credential を使い、許可された provider、予算、品質の制約を満たす候補がなければ要求を拒否します。安定した A/B 割り当て、実際のルーティング処理、測定済みのガードレールを実装してください。キャッシュキーには tenant、認可状態、モデル、検索データのリビジョンを含めます。コスト見積もりにはルーティング呼び出し、retry、cache、GPU の固定費を含めてください。根拠のない削減率は実測結果ではありません。
</details>

[chapter に戻る](../../ai-ml/03-agentic-ai-platform.md)
