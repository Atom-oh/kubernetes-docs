# スケーリング戦略クイズ

> **関連ドキュメント**: [スケーリング戦略](../../ops/06-scaling-strategies.md)

## 選択問題

### 1. HPA でカスタムメトリクスを使うには何が必要ですか？

- A) Kubernetes 1.30 以上
- B) Prometheus Adapter などのカスタムメトリクスサーバー
- C) AWS Auto Scaling との統合
- D) Pod の手動スケーリング

<details>
<summary>解答を表示</summary>

**解答: B) Prometheus Adapter などのカスタムメトリクスサーバー**

**解説:**
カスタムメトリクスを使う HPA には、`custom.metrics.k8s.io` API を実装したメトリクスサーバーが必要です。Prometheus Adapter は Prometheus に問い合わせて、HPA が期待する形式でメトリクスを公開します。これにより、1 秒あたりのリクエスト数など、アプリケーション固有のメトリクスに基づいてスケーリングできます。

</details>

### 2. KEDA はネイティブな HPA の制御ループに何を追加しますか？

- A) CPU 使用率
- B) メモリ使用量
- C) イベントソース用の scaler と、activation／ゼロまでのスケーリング管理
- D) Pod の再起動回数

<details>
<summary>解答を表示</summary>

**解答: C) イベントソース用の scaler と、activation／ゼロまでのスケーリング管理**

**解説:**
KEDA（Kubernetes Event-Driven Autoscaling）には、AWS SQS、Kafka、RabbitMQ、データベースなどの外部システム向け scaler があります。対応するワークロードでは、HPA に外部メトリクスを提供し、activation とゼロからの遷移を管理します。HPA 自体も adapter 経由で外部メトリクスを利用できます。KEDA がないと HPA は外部メトリクスを読めない、という意味ではありません。

</details>

### 3. VPA の「Recreate」と「Off」モードはどう違いますか？

- A) Recreate は HPA を有効にし、Off は無効にする
- B) Recreate は Pod を退避・再作成することがあり、Off は推奨値だけを提示する
- C) Recreate は停止なく更新でき、Off は即時に反映される
- D) Recreate は Spot インスタンスを使い、Off は On-Demand を使う

<details>
<summary>解答を表示</summary>

**解答: B) Recreate は Pod を退避・再作成することがあり、Off は推奨値だけを提示する**

**解説:**
VPA 1.8.0 では `Auto` が非推奨になっており、現在は `Recreate` と同様に動作します。`Recreate` は Pod の退避と再作成によって更新することがあります。`Off` は推奨値を提示するだけなので、確認に使えます。明示的な `InPlaceOrRecreate` と、feature gate が必要な `InPlace` は、それぞれ異なるフォールバック動作を持つ別モードです。

</details>

### 4. Pod Deletion Cost とは何で、スケーリングにどう影響しますか？

- A) Pod の削除にかかる金銭的コスト
- B) scale-down 時に先に削除する Pod の選択に影響するアノテーション
- C) Pod の削除に必要な時間
- D) Pod 終了時のストレージコスト

<details>
<summary>解答を表示</summary>

**解答: B) scale-down 時に先に削除する Pod の選択に影響するアノテーション**

**解説:**
`controller.kubernetes.io/pod-deletion-cost` アノテーションで Pod にコスト値を割り当てます。ReplicaSet 内では、先に Pod の割り当て、フェーズ、Ready 状態を比較し、その後にコスト値の低い Pod が優先されます。これはベストエフォートの仕組みであり、退避、Spot インスタンスの回収、Job／StatefulSet の動作、異なる Deployment 間のスケーリングから Pod を保護するものではありません。

</details>

### 5. カスタムメトリクスを使う HPA では、希望レプリカ数をどの式で計算しますか？

- A) currentReplicas + 1
- B) desiredReplicas = ceil(currentReplicas * (currentMetricValue / desiredMetricValue))
- C) maxReplicas / 2
- D) currentMetricValue * targetUtilization

<details>
<summary>解答を表示</summary>

**解答: B) desiredReplicas = ceil(currentReplicas * (currentMetricValue / desiredMetricValue))**

**解説:**
HPA は現在のメトリクス値と目標値を比較し、比例計算で希望レプリカ数を求めます。この簡略式は、利用可能なメトリクスがあり、Pod が Ready であることを前提とします。許容範囲、データ欠落、最小／最大数、スケーリング動作の設定によって、実際の変更は抑制または制限されます。切り上げても Pod が必ず 1 つ増えるとは限りません。

</details>

### 6. Spot ノードの中断に対処する推奨方法は何ですか？

- A) 中断を無視する
- B) Pod Disruption Budget と、中断ハンドラーを使った graceful termination を組み合わせる
- C) ステートレスなワークロードだけを実行する
- D) Spot インスタンスを完全に無効化する

<details>
<summary>解答を表示</summary>

**解答: B) Pod Disruption Budget と、中断ハンドラーを使った graceful termination を組み合わせる**

**解説:**
ノードの動作モードに応じた方法を選びます。管理された Auto Mode、構成済みのセルフマネージド Karpenter、必要に応じた Node Termination Handler の完全な構成が該当します。重複した drain コントローラーは避けてください。PDB や猶予期間を設定しても Spot の回収は防げず、アプリケーションに必ず 2 分間の停止猶予が与えられる保証もありません。

</details>

### 7. KEDA の `pollingInterval` は何を設定しますか？

- A) Pod を再起動する頻度
- B) KEDA が外部メトリクスソースを確認する頻度
- C) スケーリング操作の間隔
- D) ヘルスチェックの頻度

<details>
<summary>解答を表示</summary>

**解答: B) KEDA が外部メトリクスソースを確認する頻度**

**解説:**
`pollingInterval` は、KEDA が外部 scaler（例: SQS、Prometheus）に問い合わせてメトリクス値を取得する頻度を定めます。間隔を短くすると反応は速くなりますが、メトリクスソースへの負荷が増えます。

</details>

### 8. 新しい Kubernetes バージョンで、再起動せずに VPA が Pod のサイズを変更できる機能は何ですか？

- A) Rolling update
- B) In-place Pod Vertical Scaling
- C) Blue/green デプロイ
- D) Canary release

<details>
<summary>解答を表示</summary>

**解答: B) In-place Pod Vertical Scaling**

**解説:**
In-place Pod resize は Kubernetes 1.27 で alpha、1.33 で beta、1.35 で stable になりました。対応する VPA モードで利用できますが、`resizePolicy` によってコンテナ再起動が必要になる場合があります。また、キャパシティや QoS の制約により、更新が延期または拒否されることがあります。

</details>

### 9. HPA で metrics-server ではなく Prometheus Adapter を使う利点は何ですか？

- A) 使用リソースが少ない
- B) CPU／メモリを超えたカスタムメトリクスと外部メトリクスを使える
- C) メトリクス収集が速い
- D) アラート機能が組み込まれている

<details>
<summary>解答を表示</summary>

**解答: B) CPU／メモリを超えたカスタムメトリクスと外部メトリクスを使える**

**解説:**
metrics-server が提供するのは CPU とメモリのメトリクスだけです。Prometheus Adapter は、構成済みで利用可能な系列を `custom.metrics.k8s.io` API 経由で公開します。これにより、HPA はリクエスト数、キュー深度、レイテンシーなどのアプリケーションメトリクスに基づいてスケーリングできます。

</details>

### 10. HPA と VPA を組み合わせるとき、何を考慮すべきですか？

- A) 両者を一緒には使えない
- B) 異なるリソース軸を管理するよう構成する（HPA は CPU、VPA はメモリなど）
- C) VPA を有効にしたら、常に HPA を無効にする
- D) 構成しなくても自動で連携する

<details>
<summary>解答を表示</summary>

**解答: B) 異なるリソース軸を管理するよう構成する（HPA は CPU、VPA はメモリなど）**

**解説:**
HPA と VPA が同じリソース軸を管理しようとすると、競合することがあります。VPA を推奨値の提示だけにする方法や、HPA は RPS／backlog などのワークロードメトリクスで動かし、VPA はサイズ調整を担う方法があります。`Initial` でも新しい Pod の requests は変わるため、CPU 使用率の分母との相互作用はなくなりません。再起動とスケジューリングへの影響も検証してください。

</details>
