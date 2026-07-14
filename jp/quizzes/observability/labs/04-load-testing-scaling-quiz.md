# Observability ラボ パート 4: 負荷テストとオートスケーリング クイズ

> **最終更新**: February 22, 2026

Observability エンドツーエンドラボ パート 4 で扱った負荷テストとオートスケーリングの概念についての理解を確認しましょう。

---

1. k6 における Virtual User (VU) とは何ですか。また、段階的な負荷パターンはどのように設定しますか？
   - A) VU はネットワーク接続であり、フェーズは JSON ファイルで設定する
   - B) VU はテストスクリプトを同時実行するシミュレートされたユーザーを表し、フェーズはターゲット VU 数と期間を含む stages を使用して設定する
   - C) VU は CPU スレッドであり、フェーズはコマンドラインフラグでのみ設定する
   - D) VU はリクエストキューであり、フェーズには個別のテストスクリプトが必要である

<details>
<summary>回答を表示</summary>

**回答: B) VU はテストスクリプトを同時実行するシミュレートされたユーザーを表し、フェーズはターゲット VU 数と期間を含む stages を使用して設定する**

**解説:**
k6 では、Virtual User (VU) はテストスクリプトを実行する独立した実行コンテキストであり、各 VU はリクエストを行う実際のユーザーをシミュレートします。段階的な負荷パターンでは、`options` ブロックの `stages` オプションを使用します。各ステージでは、`target`（VU 数）と `duration`（そのターゲットに到達するまでの時間）を定義します。たとえば、2 分間で 100 VU まで増加させ、5 分間維持した後、減少させます。これにより、段階的なランプアップ、定常状態、スパイクテストなどの現実的な負荷プロファイルを実現できます。

</details>

---

2. 負荷テストにおける k6 と Locust の主な違いは何ですか？
   - A) k6 は Python で書かれており、Locust は Go で書かれている
   - B) k6 はパフォーマンスのために Go ランタイムと JavaScript のテストスクリプトを使用する一方、Locust は分散アーキテクチャと Python を使用する
   - C) Locust は HTTP/1.1 のみをサポートし、k6 はすべてのプロトコルをサポートする
   - D) k6 には GUI が必要であり、Locust は CLI 専用である

<details>
<summary>回答を表示</summary>

**回答: B) k6 はパフォーマンスのために Go ランタイムと JavaScript のテストスクリプトを使用する一方、Locust は分散アーキテクチャと Python を使用する**

**解説:**
k6 は Go ベースのランタイムによる高いパフォーマンスを提供しつつ、テストスクリプトには馴染みのある JavaScript/ES6 を使用でき、組み込みメトリクスと優れた CI/CD 統合を備えています。Locust はテストスクリプトに Python を使用するため、Python 開発者にとって扱いやすく、複雑なテストロジックにも非常に柔軟に対応できます。また、リアルタイム監視用の Web UI と容易な分散テスト機能を備えています。一般に、k6 はインスタンスあたりより高い負荷を処理でき、Locust はテストロジックの柔軟性とより視覚的な体験を提供します。

</details>

---

3. KEDA の SQS scaler は、いつ Pod をスケールするかをどのように判断しますか？
   - A) 既存 Pod の CPU 使用率に基づいてスケールする
   - B) SQS キューメトリクスをクエリし、キューメッセージ数と Pod ごとに設定したターゲット値の比率に基づいて Pod をスケールする
   - C) キュー内のメッセージの経過時間に基づいてスケールする
   - D) スケジュールされた時間枠でのみスケールする

<details>
<summary>回答を表示</summary>

**回答: B) SQS キューメトリクスをクエリし、キューメッセージ数と Pod ごとに設定したターゲット値の比率に基づいて Pod をスケールする**

**解説:**
KEDA の SQS scaler は定期的に SQS に対してキュー深度メトリクスをクエリします。必要なレプリカ数は次のように計算されます: `queue_length / queueLength_target`。たとえば、メッセージが 100 件で `queueLength: 10` の場合、KEDA は 10 Pod をターゲットにします。また、`minReplicaCount` と `maxReplicaCount` の範囲も遵守します。キューが空の場合は、設定されていればゼロまでスケールでき、メッセージの到着に応じてスケールアップします。この scaler は SQS メトリクスへのアクセスに IAM 認証情報（IRSA 経由）を使用します。

</details>

---

4. KEDA の Prometheus scaler は、スケーリング判断のためにどのようにメトリクスをクエリしますか？
   - A) Prometheus の組み込みメトリクスのみをサポートする
   - B) Prometheus サーバーに対して設定済みの PromQL クエリを実行し、返された値をしきい値と比較してスケールする
   - C) Prometheus 内に特別な KEDA metrics exporter が必要である
   - D) counter メトリクスのみをクエリでき、gauge はクエリできない

<details>
<summary>回答を表示</summary>

**回答: B) Prometheus サーバーに対して設定済みの PromQL クエリを実行し、返された値をしきい値と比較してスケールする**

**解説:**
KEDA Prometheus scaler は、設定された Prometheus エンドポイントに対して有効な任意の PromQL クエリを実行します。`serverAddress`、`query`（PromQL）、および `threshold` を指定します。KEDA は `query_result / threshold = replica_count` となるように Pod をスケールします。これにより、ビジネスメトリクス（リクエスト数/秒、キュー深度）、カスタムアプリケーションメトリクス、またはクエリ可能な任意のデータに基づくスケーリングが可能になります。認証では、保護された Prometheus インスタンスに対して bearer token または TLS をサポートします。

</details>

---

5. Karpenter は Pending Pod をどのように検出し、適切な Node をプロビジョニングしますか？
   - A) PodScheduled=False の Pod を Kubernetes API でポーリングし、その要件を NodePool テンプレートと照合する
   - B) Pod が annotations を介して Karpenter プロビジョニングを明示的にリクエストする必要がある
   - C) クラスターの CPU 使用率を監視し、事前に Node をプロビジョニングする
   - D) プロビジョニング前に Horizontal Pod Autoscaler のシグナルを待機する

<details>
<summary>回答を表示</summary>

**回答: A) PodScheduled=False の Pod を Kubernetes API でポーリングし、その要件を NodePool テンプレートと照合する**

**解説:**
Karpenter はスケジュール不能な Pod（既存の Node では要件を満たせないため Pending となっている Pod）を監視します。検出されると、Pod の要件（リソースリクエスト、node selector、toleration、トポロジー制約）を分析し、設定済み NodePool から最適な EC2 インスタンスをプロビジョニングします。Karpenter の bin-packing アルゴリズムは Pending Pod を効率的にグループ化し、要件を満たしながらコストを最小化するインスタンスタイプを選択します。この「just-in-time」プロビジョニングは、Cluster Autoscaler の node group ベースのアプローチより高速です。

</details>

---

6. Karpenter の Consolidation ポリシーは、コスト最適化のために何を行いますか？
   - A) 既存の Node 内でのみ Pod を集約する
   - B) 低使用率または空の Node を特定し、ワークロードを移行して Node 総数を減らし、不要な Node を終了する
   - C) 複数の Node のログを集約する
   - D) スケジュールされたメンテナンス時間枠でのみ機能する

<details>
<summary>回答を表示</summary>

**回答: B) 低使用率または空の Node を特定し、ワークロードを移行して Node 総数を減らし、不要な Node を終了する**

**解説:**
Karpenter の consolidation は、クラスターの効率を継続的に評価します。空の Node を即座に終了する、要件を満たしつつより安価な代替 Node に置き換える、複数の低使用率 Node 上のワークロードをより少数の Node に集約するといった方法で、コスト削減の機会を特定します。consolidation は Pod Disruption Budget を尊重し、graceful termination を使用します。この自動的な適正サイジングにより、必要なキャパシティに対してのみ支払うことができ、インテリジェントなスケールダウンでスケールアップを補完します。

</details>

---

7. 負荷テスト中に Grafana ダッシュボードで観測すべき主要な RED メトリクスは何ですか？
   - A) RAM、Ethernet、Disk
   - B) Rate（リクエスト数/秒）、Errors（エラー率/件数）、Duration（レイテンシ分布）
   - C) Replicas、Events、Deployments
   - D) Reads、Executions、Deletions

<details>
<summary>回答を表示</summary>

**回答: B) Rate（リクエスト数/秒）、Errors（エラー率/件数）、Duration（レイテンシ分布）**

**解説:**
RED メトリクスは、サービス監視の標準的な方法論です。Rate はスループット（リクエスト数/秒）を測定し、Errors は失敗率または件数（4xx、5xx レスポンス）を追跡し、Duration はレイテンシ分布（p50、p95、p99 のレスポンスタイム）を捉えます。負荷テスト中、これらのメトリクスはストレス下でシステムがどのように動作するかを明らかにします。スループットは頭打ちになるか、エラーは急増するか、レイテンシは劣化するかを確認できます。RED ダッシュボードはサービスの健全性を即座に可視化し、限界点の特定に役立ちます。

</details>

---

8. Prometheus メトリクスを使用して、スケーリングイベント中の Pod 数の変化をどのように追跡できますか？
   - A) `kube_pod_created` のタイムスタンプのみを使用する
   - B) `kube_deployment_status_replicas` を使用して現在のレプリカ数を追跡し、`kube_deployment_spec_replicas` と比較して必要な数を確認する
   - C) Pod 数メトリクスは Prometheus では利用できない
   - D) Pod ごとに集計した `container_cpu_usage` を使用する

<details>
<summary>回答を表示</summary>

**回答: B) `kube_deployment_status_replicas` を使用して現在のレプリカ数を追跡し、`kube_deployment_spec_replicas` と比較して必要な数を確認する**

**解説:**
kube-state-metrics は Deployment のレプリカ情報を公開します。`kube_deployment_spec_replicas` は必要なレプリカ数（HPA/KEDA がターゲットとする数）を示し、`kube_deployment_status_replicas` は現在 Ready なレプリカ数を示し、`kube_deployment_status_replicas_available` は利用可能なレプリカ数を示します。これらを時系列でグラフ化すると、実際のレプリカが必要な数にどれだけ速く一致するか、振動の有無、スケールアップ/ダウンのタイミングといったスケーリング動作を明らかにできます。HPA 固有のメトリクスについては、`kube_horizontalpodautoscaler_*` メトリクスが追加の詳細を提供します。

</details>

---

9. `stabilizationWindowSeconds` 設定は、KEDA のスケーリング動作においてどのような役割を果たしますか？
   - A) Pod が終了前に実行されなければならない最小時間を設定する
   - B) スケールダウン時に、その期間の最も高い推奨値を考慮することで急激な振動を防ぐためのルックバックウィンドウを定義する
   - C) メトリクスクエリ間の間隔を設定する
   - D) Pod 起動の最大時間を設定する

<details>
<summary>回答を表示</summary>

**回答: B) スケールダウン時に、その期間の最も高い推奨値を考慮することで急激な振動を防ぐためのルックバックウィンドウを定義する**

**解説:**
`stabilizationWindowSeconds` は、スケールダウン時のスラッシングを防ぎます。スケールダウン時、KEDA は過去 N 秒間（安定化ウィンドウ）のすべてのスケール推奨値を確認し、最も高い値を使用します。これにより、短時間のメトリクス低下がスケールダウンを引き起こし、負荷が戻ると直後にスケールアップが続くような状況を防止します。たとえば、300 秒のウィンドウでは、メトリクスが 5 分間一貫して低い場合にのみスケールダウンが発生します。通常、負荷増加への迅速な対応を確保するため、スケールアップは安定化されません。

</details>

---

10. キューベースのワークロードアーキテクチャにおいて、SQS Queue Depth は Pod のスケーリングとどのように相関しますか？
    - A) Queue Depth と Pod 数は常に反比例する
    - B) Queue Depth が増加すると、KEDA はメッセージをより速く処理するために Pod をスケールアップして Queue Depth を減らし、キューが空になるにつれて Pod をスケールダウンする
    - C) Queue Depth はメモリ割り当てにのみ影響し、Pod 数には影響しない
    - D) Pod のスケーリングは Queue Depth と独立して行われる

<details>
<summary>回答を表示</summary>

**回答: B) Queue Depth が増加すると、KEDA はメッセージをより速く処理するために Pod をスケールアップして Queue Depth を減らし、キューが空になるにつれて Pod をスケールダウンする**

**解説:**
キューベースのアーキテクチャでは、フィードバックループが存在します。受信メッセージが Queue Depth を増加させ、KEDA がこれを検出して consumer Pod をスケールアップし、より多くの Pod がメッセージをより速く処理することで（スループットが増加し）、Queue Depth が減少し、最終的にキューを処理可能な状態になると KEDA が Pod をスケールダウンします。`queueLength` しきい値は、Pod あたりのターゲットメッセージ数を決定します。Queue Depth と Pod 数を併せて観測すると、処理キャパシティを把握できます。最大 Pod 数に達しても Queue Depth が増加する場合は、最適化またはより高い制限値が必要なボトルネックを発見したことになります。

</details>
