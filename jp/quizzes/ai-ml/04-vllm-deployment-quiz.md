# vLLM デプロイメントクイズ

対象バージョン: vLLM 0.29.0。過去の L4 の結果と現行の検証結果を区別しています。

## クイズ問題

### 1. vLLM を正しく説明しているのはどれですか？

- A. Vector Language Model という名前のモデル
- B. 対応する生成 AI、マルチモーダルなどのモデルワークロード向けの推論エンジン
- C. データベース専用のオプティマイザー
- D. すべてのモデルの精度を自動的に向上させるトレーニングツール

<details>
<summary>回答を表示</summary>

**回答: B. 対応する生成 AI、マルチモーダルなどのモデルワークロード向けの推論エンジン**

vLLM は推論エンジンであり、「Vector Language Model」の略称ではありません。PagedAttention とバッチ処理の効果はワークロードによって異なります。決まった倍率の高速化や、キューが発生しない動作は保証されません。
</details>

### 2. GPU メモリ要件はどのように見積もるべきですか？

- A. 70B は精度にかかわらず常に 80GB に収まる
- B. モデル構成、精度、並列化方式を考慮し、重み、KV キャッシュ、活性化メモリ／作業領域、通信に必要なメモリを合算する
- C. GPU あたり CPU コアが 4 個あれば、すべてのモデルの実行が保証される
- D. ホスト RAM を増やせば GPU 要件は不要になる

<details>
<summary>回答を表示</summary>

**回答: B. モデル構成、精度、並列化方式を考慮し、重み、KV キャッシュ、活性化メモリ／作業領域、通信に必要なメモリを合算する**

70B モデルの FP16/BF16 の重みだけで約 140GB 必要です。GQA/MQA では、MHA の隠れ次元に基づく式ではなく、KV ヘッド数を使って計算します。NVIDIA の現行要件である compute capability 7.5 以上と、追加の kernel 要件を確認してください。
</details>

### 3. ストレージについて正しい記述はどれですか？

- A. FSx for Lustre が常に最適である
- B. snapshot_download は S3 からダウンロードする
- C. ロード時間、並行性、コスト、保持期間に基づいて選択し、モデル revision と整合性を記録する
- D. emptyDir は container の再起動時に必ず消去される

<details>
<summary>回答を表示</summary>

**回答: C. ロード時間、並行性、コスト、保持期間に基づいて選択し、モデル revision と整合性を記録する**

emptyDir はコンテナを再起動しても維持されますが、Pod を作り直すと失われます。FSx の静的／動的プロビジョニング、EBS のアクセスモード、各 worker でモデルのパスを統一する必要性を区別してください。Hugging Face のダウンロードと S3 転送は別のものです。
</details>

### 4. TP、PP、独立したレプリカはどのように異なりますか？

- A. StatefulSet の replica を増やすと TP が自動的に再設定される
- B. TP は層内の処理を分割し、PP は層を複数の段階に分け、独立したレプリカはそれぞれモデルをロードする
- C. TP は常に単一リクエストのレイテンシーを低減する
- D. すべてのマルチノードデプロイメントで --rank を使用する

<details>
<summary>回答を表示</summary>

**回答: B. TP は層内の処理を分割し、PP は層を複数の段階に分け、独立したレプリカはそれぞれモデルをロードする**

0.29.0 のマルチプロセス構成では --nnodes/--node-rank と headless worker を使用します。Ray を使う場合は、実際に稼働する Ray クラスターが必要です。環境、モデル、ネットワーク／ランデブー設定、GPU を揃えてください。プロセスの並列構成は Kubernetes のレプリカ数とは別です。
</details>

### 5. 可用性について正しい記述はどれですか？

- A. PDB はすべての node 障害を通じて最小 replica 数を保証する
- B. maxUnavailable0 だけで無停止が保証される
- C. 独立したレプリカ、probe、起動処理、予備容量、ノード退避（draining）、ストリーミング要求をまとめて検証する
- D. 1 つの TP group を AZ をまたいで配置すると、常にパフォーマンスが向上する

<details>
<summary>回答を表示</summary>

**回答: C. 独立したレプリカ、probe、起動処理、予備容量、ノード退避（draining）、ストリーミング要求をまとめて検証する**

PDB は一部の計画的な Pod 退避を制限します。例の Recreate 戦略は追加の GPU を使わずに済みますが、更新時にダウンタイムが発生します。startupProbe は初期化中の readiness/liveness probe を制御します。実際のモデル読み込み時間を検証してください。
</details>

### 6. バッチ処理とキャッシュについて正しい記述はどれですか？

- A. すべてのリクエストはキューなしですぐに実行される
- B. スケジューリングは段階的に行われ、トークン数、キャッシュ、容量の制限によってキューが形成されることがある
- C. Prefix caching は常に応答全体を再利用する
- D. --swap-space は 0.29 におけるデフォルトのメモリ拡張機能である

<details>
<summary>回答を表示</summary>

**回答: B. スケジューリングは段階的に行われ、トークン数、キャッシュ、容量の制限によってキューが形成されることがある**

Prefix caching は、対応する prefix の KV state を再利用します。Chunked prefill、max-num-seqs、token budget、context limit はそれぞれ別の設定です。CacheConfig のデフォルトでは gpu_memory_utilization は 0.92 で、例では 0.80 に設定しています。--swap-space は現行 CLI に存在しません。
</details>

### 7. 現在のメトリクス設定では何を使用すべきですか？

- A. 別の 8001 port と --enable-metrics=true
- B. API port 8000 の /metrics と、実際の vllm: の名前、label、unit
- C. 合計 GPU メモリの byte 数としての KV occupancy
- D. 低スループット障害として、すべての idle period で alert を出す

<details>
<summary>回答を表示</summary>

**回答: B. API ポート 8000 の /metrics と、実際の vllm: メトリクス名、ラベル、単位**

例として vllm:generation_tokens_total と vllm:e2e_request_latency_seconds_bucket があります。KV cache 使用率は比率で、1 は 100% を意味します。モデル単位の集計、gateway のエラー／キャンセル、TTFT、エンドツーエンドのレイテンシーを区別してください。
</details>

### 8. マルチノードネットワークについて正しい記述はどれですか？

- A. API key はすべての内部 transport を暗号化する
- B. 任意にコピーした GID/mlx5 設定で EFA を構成できる
- C. サポート対象の device/driver、OFI NCCL/libfabric、private communication path を検証する
- D. 単一ノードの NCCL test により、マルチノード EFA のパフォーマンスが証明される

<details>
<summary>回答を表示</summary>

**回答: C. 対応する device/driver、OFI NCCL/libfabric、プライベートな通信経路を検証する**

分散通信には信頼できるネットワークが必要です。API 認証だけでは、PyTorch/Ray/KV の通信経路は保護されません。汎用の SR-IOV/InfiniBand テンプレートや実在しない NCCL 変数は、そのまま利用できる EKS 設定ではありません。
</details>

### 9. スケーリング／ルーティングについて正しい記述はどれですか？

- A. HTTP model header は JSON の model field を自動的に読み取る
- B. Session affinity はすべての KV cache を自動的に共有する
- C. 測定した bottleneck と model topology に基づいて replica、TP/PP、routing を選択する
- D. GPU があれば CPU と storage はパフォーマンスに影響しない

<details>
<summary>回答を表示</summary>

**回答: C. 測定したボトルネックとモデル構成に基づいて replica、TP/PP、routing を選択する**

Prefix cache、応答 cache、重み cache はそれぞれ異なります。CPU による tokenization、ネットワーク、モデル読み込みがボトルネックになる場合もあります。HPA/KEDA と NodePool は別のレイヤーであり、それぞれ異なるメトリクス、管理主体、容量要件を持ちます。
</details>

### 10. 0.29.0 における API-key/security について正しい記述はどれですか？

- A. --api-key はすべての server endpoint を保護する
- B. 他の path と運用上の capability には、prefix authentication を超えた gateway、permission、network boundary が必要である
- C. CORS は authentication を置き換える
- D. 単一の regex ですべての prompt injection と PII 漏洩を防止できる

<details>
<summary>回答を表示</summary>

**回答: B. 他の path と運用上の capability には、prefix authentication を超えた gateway、permission、network boundary が必要である**

調査対象の middleware が認証するのは /v1、/v2、/inference、/cohere の各 prefix です。それ以外の path と OPTIONS リクエストには適用されません。Dynamic LoRA には明示的な opt-in と、信頼された運用者だけが使える経路が必要です。Secret の RequestResponse 監査や、Pod annotation を付ければ control-plane 監査が有効になるかのような例は、安全でないか、効果がありません。
</details>

### 11. 過去の L4 結果 5.65s→7.52s はどのように解釈すべきですか？

- A. レイテンシーは増加していない
- B. p50 は約 33.1% 増加した一方、そのテスト範囲では aggregate throughput が上昇した。raw log のない古い report は現行バージョンの証拠にはならない
- C. profiler によって memory bottleneck が証明された
- D. Continuous batching は prefill をスキップする

<details>
<summary>回答を表示</summary>

**回答: B. p50 は約 33.1% 増加した一方、そのテスト範囲では集約スループットが上昇した。生ログのない古いレポートは現行バージョンの証拠にはならない**

報告されたデータは 0.6.4.post1 での 1 回の実行結果です。この監査ではリクエスト／サーバーの生ログを確認できず、再実行もしていません。ログに記録された最大の区間平均は、瞬間的なピーク値ではありません。roofline 計算は推定であり、プロファイラーによる測定結果ではありません。
</details>

---

[学習資料に戻る](../../ai-ml/02-vllm-deployment.md)
