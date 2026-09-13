# vLLM デプロイメントクイズ

ベースライン: vLLM 0.29.0。過去の L4 結果は、現在の検証結果と区別します。

## クイズ問題

### 1. vLLM を正しく説明しているのはどれですか？

- A. Vector Language Model という名前のモデル
- B. サポート対象の生成/マルチモーダルおよびその他のモデルワークロード向けの推論エンジン
- C. データベース専用のオプティマイザー
- D. すべてのモデルの精度を自動的に向上させるトレーニングツール

<details>
<summary>回答を表示</summary>

**回答: B. サポート対象の生成/マルチモーダルおよびその他のモデルワークロード向けの推論エンジン**

vLLM はエンジンであり、そのように創作された名称の展開ではありません。PagedAttention とバッチ処理の利点はワークロードに依存します。固定の高速化やキューなしの実行は保証されません。
</details>

### 2. GPU メモリ要件はどのように見積もるべきですか？

- A. 70B は精度にかかわらず常に 80GB に収まる
- B. アーキテクチャ、精度、並列性を考慮して、重み、KV cache、activation/workspace、通信を加算する
- C. GPU あたり CPU コアが 4 個あれば、すべてのモデルの実行が保証される
- D. ホスト RAM を増やせば GPU 要件は不要になる

<details>
<summary>回答を表示</summary>

**回答: B. アーキテクチャ、精度、並列性を考慮して、重み、KV cache、activation/workspace、通信を加算する**

70B の FP16/BF16 の重みだけで約 140GB です。GQA/MQA では、MHA の hidden-size の式ではなく KV-head 数が必要です。現在の NVIDIA の capability 7.5 という最小要件と、追加の kernel 要件を確認してください。
</details>

### 3. ストレージについて正しい記述はどれですか？

- A. FSx for Lustre が常に最適である
- B. snapshot_download は S3 からダウンロードする
- C. ロード時間、並行性、コスト、保持期間に基づいて選択し、モデル revision と整合性を記録する
- D. emptyDir は container の再起動時に必ず消去される

<details>
<summary>回答を表示</summary>

**回答: C. ロード時間、並行性、コスト、保持期間に基づいて選択し、モデル revision と整合性を記録する**

emptyDir は container の再起動後も存続できますが、Pod の再作成後は存続しません。FSx の static/dynamic provisioning、EBS の access mode、同一の worker モデルパスを区別してください。Hugging Face のダウンロードと S3 転送は別のものです。
</details>

### 4. TP、PP、および独立した replica はどのように異なりますか？

- A. StatefulSet の replica を増やすと TP が自動的に再設定される
- B. TP は layer 内を分割し、PP は layer stage を分割し、独立した replica はそれぞれモデルをロードする
- C. TP は常に単一リクエストのレイテンシーを低減する
- D. すべてのマルチノードデプロイメントで --rank を使用する

<details>
<summary>回答を表示</summary>

**回答: B. TP は layer 内を分割し、PP は layer stage を分割し、独立した replica はそれぞれモデルをロードする**

0.29.0 の multiprocessing では --nnodes/--node-rank と headless worker を使用します。Ray には実際の cluster が必要です。environment、model、network/rendezvous、GPU を一致させてください。process topology は Kubernetes の replica 数ではありません。
</details>

### 5. 可用性について正しい記述はどれですか？

- A. PDB はすべての node 障害を通じて最小 replica 数を保証する
- B. maxUnavailable0 だけで無停止が保証される
- C. 独立した replica、probe、起動、予備 capacity、draining、stream をまとめて検証する
- D. 1 つの TP group を AZ をまたいで配置すると、常にパフォーマンスが向上する

<details>
<summary>回答を表示</summary>

**回答: C. 独立した replica、probe、起動、予備 capacity、draining、stream をまとめて検証する**

PDB は一部の自発的 eviction を制限します。例の Recreate strategy は追加の GPU を回避しますが、更新時のダウンタイムを引き起こします。startupProbe は初期化中の readiness/liveness を制御します。実際のロード時間を検証してください。
</details>

### 6. バッチ処理/cache について正しい記述はどれですか？

- A. すべてのリクエストはキューなしですぐに実行される
- B. スケジューリングは段階的に行われ、token/cache/capacity の制限下ではキューが形成される可能性がある
- C. Prefix caching は常に応答全体を再利用する
- D. --swap-space は 0.29 におけるデフォルトのメモリ拡張機能である

<details>
<summary>回答を表示</summary>

**回答: B. スケジューリングは段階的に行われ、token/cache/capacity の制限下ではキューが形成される可能性がある**

Prefix caching はサポート対象の prefix KV state を再利用します。Chunked prefill、max-num-seqs、token budget、context limit はそれぞれ異なります。CacheConfig のデフォルトでは gpu_memory_utilization は 0.92 です。例では 0.80 を設定しています。--swap-space は現在の CLI にはありません。
</details>

### 7. 現在の metrics 設定では何を使用すべきですか？

- A. 別の 8001 port と --enable-metrics=true
- B. API port 8000 の /metrics と、実際の vllm: の名前、label、unit
- C. 合計 GPU メモリの byte 数としての KV occupancy
- D. 低スループット障害として、すべての idle period で alert を出す

<details>
<summary>回答を表示</summary>

**回答: B. API port 8000 の /metrics と、実際の vllm: の名前、label、unit**

例には vllm:generation_tokens_total と vllm:e2e_request_latency_seconds_bucket があります。KV occupancy は比率であり、1 は 100% を意味します。model aggregation、gateway error/cancellation、TTFT、end-to-end latency を区別してください。
</details>

### 8. マルチノード networking について正しい記述はどれですか？

- A. API key はすべての内部 transport を暗号化する
- B. 任意にコピーした GID/mlx5 設定で EFA を構成できる
- C. サポート対象の device/driver、OFI NCCL/libfabric、private communication path を検証する
- D. 単一ノードの NCCL test により、マルチノード EFA のパフォーマンスが証明される

<details>
<summary>回答を表示</summary>

**回答: C. サポート対象の device/driver、OFI NCCL/libfabric、private communication path を検証する**

分散通信には信頼できる network が必要です。API authentication は、PyTorch/Ray/KV transport の security とは異なります。汎用の SR-IOV/InfiniBand template や創作された NCCL variable は、そのまま使える EKS 設定ではありません。
</details>

### 9. スケーリング/routing について正しい記述はどれですか？

- A. HTTP model header は JSON の model field を自動的に読み取る
- B. Session affinity はすべての KV cache を自動的に共有する
- C. 測定した bottleneck と model topology に基づいて replica、TP/PP、routing を選択する
- D. GPU があれば CPU と storage はパフォーマンスに影響しない

<details>
<summary>回答を表示</summary>

**回答: C. 測定した bottleneck と model topology に基づいて replica、TP/PP、routing を選択する**

Prefix、response、weight cache は異なります。CPU tokenization、networking、loading が bottleneck になる場合があります。HPA/KEDA と NodePool は、それぞれ metric、ownership、capacity 要件を持つ別の layer です。
</details>

### 10. 0.29.0 における API-key/security について正しい記述はどれですか？

- A. --api-key はすべての server endpoint を保護する
- B. 他の path と運用上の capability には、prefix authentication を超えた gateway、permission、network boundary が必要である
- C. CORS は authentication を置き換える
- D. 単一の regex ですべての prompt injection と PII 漏洩を防止できる

<details>
<summary>回答を表示</summary>

**回答: B. 他の path と運用上の capability には、prefix authentication を超えた gateway、permission、network boundary が必要である**

調査した middleware は /v1,/v2,/inference,/cohere の prefix を保護します。その他の path と OPTIONS はこれを回避します。Dynamic LoRA には明示的な opt-in と信頼できる operator path が必要です。Secret の RequestResponse auditing と、control-plane audit を有効にすると見せかける Pod annotation は、安全でない/効果のない例です。
</details>

### 11. 過去の L4 結果 5.65s→7.52s はどのように解釈すべきですか？

- A. レイテンシーは増加していない
- B. p50 は約 33.1% 増加した一方、そのテスト範囲では aggregate throughput が上昇した。raw log のない古い report は現行バージョンの証拠にはならない
- C. profiler によって memory bottleneck が証明された
- D. Continuous batching は prefill をスキップする

<details>
<summary>回答を表示</summary>

**回答: B. p50 は約 33.1% 増加した一方、そのテスト範囲では aggregate throughput が上昇した。raw log のない古い report は現行バージョンの証拠にはならない**

報告されたデータは 0.6.4.post1 の 1 回の実行結果です。この監査では raw request/server log は見つからず、再実行もしていません。ログに記録された最大 interval average は瞬間的な peak ではありません。roofline calculation は推定であり、profiler の証拠ではありません。
</details>

---

[学習資料に戻る](../../ai-ml/02-vllm-deployment.md)
