# Knative クイズ

1. Knative Serving では Scale-to-Zero はどのように機能しますか？
   - A) Pod を削除し、新しいリクエスト時に Deployment を再作成する
   - B) Autoscaler がレプリカを 0 から 1 にスケールする間、Activator がトラフィックをバッファする
   - C) Node を停止し、リクエスト時に Karpenter に新しい Node をプロビジョニングさせる
   - D) コンテナを一時停止し、リクエスト時に再開する

<details>
<summary>回答を表示</summary>

**回答: B) Autoscaler がレプリカを 0 から 1 にスケールする間、Activator がトラフィックをバッファする**

**解説:**
レプリカが 0 の場合、受信リクエストは Activator によってバッファされます。Activator は Autoscaler にスケールアップをリクエストし、Pod の準備ができると、バッファされたリクエストが転送されます。このプロセスが「コールドスタート」であり、`minScale` を設定して最小インスタンス数を維持することで防止できます。

</details>

---

2. KPA (Knative Pod Autoscaler) と HPA の主な違いは何ですか？
   - A) KPA は CPU ベースのみ、HPA はメモリベースのみ
   - B) KPA は concurrency に基づいてスケールし、Scale-to-Zero をサポートする一方、HPA は CPU/メモリに基づいてスケールする
   - C) KPA は Node をスケールし、HPA は Pod をスケールする
   - D) KPA は手動スケーリング、HPA は自動スケーリング

<details>
<summary>回答を表示</summary>

**回答: B) KPA は concurrency に基づいてスケールし、Scale-to-Zero をサポートする一方、HPA は CPU/メモリに基づいてスケールする**

**解説:**
KPA は Queue Proxy によって測定される同時リクエスト数または RPS に基づいてスケールし、Scale-to-Zero をネイティブにサポートします。HPA は CPU/メモリ metrics に基づいてスケールしますが、常に少なくとも 1 レプリカが必要です。

</details>

---

3. Knative Eventing の Broker/Trigger パターンにおける Trigger の役割は何ですか？
   - A) イベントを生成する source
   - B) Broker からイベントをフィルタリングし、特定の Service にルーティングする
   - C) イベント用の永続ストレージ
   - D) 外部システムにイベントを送信する gateway

<details>
<summary>回答を表示</summary>

**回答: B) Broker からイベントをフィルタリングし、特定の Service にルーティングする**

**解説:**
Trigger は Broker に登録され、属性（type、source など）に基づいて CloudEvents をフィルタリングします。一致するイベントのみが指定された Subscriber（Knative Service、Kubernetes Service など）に配信されます。単一の Broker に複数の Trigger を登録して、異なる Service にイベントをルーティングできます。

</details>

---

4. Knative Service で `containerConcurrency: 1` を設定すると何が起こりますか？
   - A) コンテナごとに 1 つの Pod のみが作成される
   - B) 各コンテナが一度に 1 つのリクエストを処理し、追加のリクエストは新しい Pod にルーティングされる
   - C) 1 秒あたり 1 つのリクエストのみが許可される
   - D) 1 つの Revision のみが維持される

<details>
<summary>回答を表示</summary>

**回答: B) 各コンテナが一度に 1 つのリクエストを処理し、追加のリクエストは新しい Pod にルーティングされる**

**解説:**
`containerConcurrency: 1` は、各 Pod 内の Queue Proxy がコンテナへ同時に 1 つのリクエストのみを転送するように設定します。追加のリクエストが到着すると、Autoscaler が新しい Pod を作成します。これは CPU 負荷の高いタスクやスレッドセーフではないアプリケーションに有用です。

</details>

---

5. KEDA と Knative を一緒に使用する適切なシナリオはどれですか？
   - A) 2 つのツールには互換性がないため、どちらか一方のみを使用する
   - B) HTTP workloads には Knative Serving を使用し、queue/stream ベースの非同期 workloads には KEDA を使用する
   - C) Scale-to-Zero には KEDA を使用し、event routing には Knative を使用する
   - D) Knative は内部的に KEDA を使用している

<details>
<summary>回答を表示</summary>

**回答: B) HTTP workloads には Knative Serving を使用し、queue/stream ベースの非同期 workloads には KEDA を使用する**

**解説:**
Knative Serving は、Scale-to-Zero と concurrency ベースのスケーリングを備えた HTTP リクエストベースの serverless workloads に最適化されています。KEDA は SQS、Kafka、Redis などのキュー metrics に基づくスケーリングに優れています。両方を一緒に使用することで、同期および非同期 workloads を最適にスケールできます。

</details>

---

6. Knative で traffic splitting を使用して Canary deployment（カナリアデプロイメント）を実装するにはどうしますか？
   - A) Deployment のレプリカ数を調整する
   - B) Knative Service の spec.traffic で Revision ごとのトラフィック比率を指定する
   - C) Istio VirtualService を手動で作成する
   - D) HPA minReplicas を調整する

<details>
<summary>回答を表示</summary>

**回答: B) Knative Service の spec.traffic で Revision ごとのトラフィック比率を指定する**

**解説:**
Knative Service の `spec.traffic` フィールドでは、Revision ごとのトラフィック比率を指定できます。たとえば、canary deployment では既存の Revision に 90%、新しい Revision に 10% を割り当てます。最新の Revision を参照するには `@latest` を使用するか、Revision 名を直接指定します。

</details>

---

7. Knative における Dead Letter Sink の目的は何ですか？
   - A) 削除された Knative Service をアーカイブする
   - B) イベント損失を防ぐため、失敗したイベントを別の送信先に送る
   - C) 期限切れの Revision をクリーンアップする
   - D) debug logs を保存する

<details>
<summary>回答を表示</summary>

**回答: B) イベント損失を防ぐため、失敗したイベントを別の送信先に送る**

**解説:**
Dead Letter Sink は、再試行後に配信が失敗した場合、イベントを指定された送信先（別の Knative Service、Kubernetes Service など）に転送します。これによりイベント損失を防ぎ、失敗したイベントの分析や再処理が可能になります。

</details>

---

8. Knative Serving で cold start を最小限に抑える最も効果的な方法は何ですか？
   - A) コンテナイメージサイズを無限に小さくする
   - B) `minScale` annotation で最小インスタンス数を維持し、高速起動 framework の軽量イメージを使用する
   - C) Scale-to-Zero を完全に無効化する
   - D) Node 数を常に最大に保つ

<details>
<summary>回答を表示</summary>

**回答: B) `minScale` annotation で最小インスタンス数を維持し、高速起動 framework の軽量イメージを使用する**

**解説:**
`autoscaling.knative.dev/min-scale` を 1 以上に設定すると cold start を防げます。これを軽量ベースイメージ（distroless、alpine）、GraalVM Native Image のような高速起動 framework、`initialScale` 設定と組み合わせることで、cold start のレイテンシーを最小化できます。

</details>
