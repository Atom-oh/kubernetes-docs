# 可観測性アラートクイズ

> **関連ドキュメント**: [可観測性アラート](../../ops/07-observability-alerts.md)

## 選択式問題

### 1. コンテナの CPU throttling を検出する PromQL 式はどれですか？

- A) `container_cpu_usage_seconds_total`
- B) `rate(container_cpu_cfs_throttled_seconds_total[5m]) > 0`
- C) `container_memory_usage_bytes`
- D) `kube_pod_status_phase`

<details>
<summary>回答を表示</summary>

**回答: B) `rate(container_cpu_cfs_throttled_seconds_total[5m]) > 0`**

**解説:**
利用可能なCFS quotaを使い切ると、CPU throttlingが発生することがあります。`container_cpu_cfs_throttled_seconds_total` metricは、throttlingされていた時間を記録します。正のrateは、アプリケーションの性能に影響する可能性のあるthrottlingが現在起きていることを示します。ワークロードのquotaと性能状況を踏まえて解釈してください。

</details>

### 2. Alertmanager の `group_by` configuration の目的は何ですか？

- A) alert を削除すること
- B) 一致する label を持つ alert を単一の notification に集約すること
- C) alert severity を上げること
- D) alert を log に route すること

<details>
<summary>回答を表示</summary>

**回答: B) 一致する label を持つ alert を単一の notification に集約すること**

**解説:**
`group_by` は、指定された label 値を共有する複数の発火中 alert を単一の notification にまとめます。これにより、多数の類似 alert を trigger する incident（例: deployment 内のすべての pod が失敗している）中の alert fatigue を減らします。

</details>

### 3. Kubernetes NodeのReady状態を確認するのに役立つmetricはどれですか？

- A) `node_cpu_seconds_total`
- B) condition="Ready" の `kube_node_status_condition`
- C) `container_memory_usage_bytes`
- D) `node_filesystem_size_bytes`

<details>
<summary>回答を表示</summary>

**回答: B) condition="Ready" の `kube_node_status_condition`**

**解説:**
Ready conditionは、観測対象のNodeがReadyかどうかを示します。FalseやUnknownには複数の原因があり、終了や置き換えが起きた証拠にはなりません。インベントリ、Node/NodeClaimのcondition、実際のeventや監査ログと照合してください。

</details>

### 4. Prometheus alerting rule の `for` duration は何を指定しますか？

- A) alert を history に保持する期間
- B) firing する前に condition が true であり続ける必要がある期間
- C) alert evaluation interval
- D) notification timeout

<details>
<summary>回答を表示</summary>

**回答: B) firing する前に condition が true であり続ける必要がある期間**

**解説:**
`for` clause は、alert が「pending」から「firing」に遷移する前に、condition が継続して true でなければならない duration を指定します。これにより、短時間の spike による alert を防ぎ、false positive を減らします。

</details>

### 5. alert severity level はどのように定義すべきですか？

- A) すべての alert を critical にするべき
- B) business impact と required response time に基づく
- C) random に割り当てる
- D) metric name に基づく

<details>
<summary>回答を表示</summary>

**回答: B) business impact と required response time に基づく**

**解説:**
Severity は impact を反映するべきです。immediate response が必要な customer-facing outage には critical、数時間以内に attention が必要な degradation には warning、action を伴わない awareness には info を使用します。これにより、適切な routing と on-call escalation が可能になります。

</details>

### 6. 時間の経過に伴う増加 rate を計算する PromQL function はどれですか？

- A) `sum()`
- B) `rate()`
- C) `max()`
- D) `count()`

<details>
<summary>回答を表示</summary>

**回答: B) `rate()`**

**解説:**
`rate()` は、time range における 1 秒あたりの average rate of increase を計算します。counter 用に設計されており、counter reset を処理します。たとえば、`rate(http_requests_total[5m])` は 5 分間の平均 request per second を返します。

</details>

### 7. packet drop alert に推奨される approach は何ですか？

- A) 単一の packet drop でも alert する
- B) drop rate が threshold を超え、それが一定時間継続した場合に alert する
- C) packet drop では決して alert しない
- D) packet drop は log のみに記録する

<details>
<summary>回答を表示</summary>

**回答: B) drop rate が threshold を超え、それが一定時間継続した場合に alert する**

**解説:**
Network では occasional packet drop は正常です。Alert は、実際の問題を示す sustained elevated drop rate で trigger されるべきです。window（例: 5m）に対して `rate()` を threshold とともに使用することで、一時的な spike による alert を防ぎます。

</details>

### 8. Alertmanager routing において、`continue: true` は何をしますか？

- A) 以降の route 処理を停止する
- B) 現在の route の後で、alert が追加の route に一致することを許可する
- C) alert notification を繰り返す
- D) alert を silence する

<details>
<summary>回答を表示</summary>

**回答: B) 現在の route の後で、alert が追加の route に一致することを許可する**

**解説:**
`continue: true` を設定すると、現在のrouteに一致した後も、後続の兄弟routeとの照合が続きます。子routeがすでに一致している場合、root receiverが自動的なフォールバックになるわけではありません。担当チームのrouteに一致しないcritical alertも含め、ルーティングツリー全体をテストしてください。

</details>

### 9. ネットワークの送信スループットを測るのに役立つ式はどれですか？

- A) `container_cpu_usage_seconds_total`
- B) 実際の容量契約に合わせた単位で表した `rate(node_network_transmit_bytes_total[5m])`
- C) `kube_pod_container_status_running`
- D) `container_fs_writes_bytes_total`

<details>
<summary>回答を表示</summary>

**回答: B) 実際の容量契約に合わせた単位で表した `rate(node_network_transmit_bytes_total[5m])`**

**解説:**
`node_network_transmit_bytes_total` と `node_network_receive_bytes_total` はネットワークI/Oを記録します。rateの単位はbytes/sです。bits/sにするには8倍し、検証済みの基準値やバースト量、経路上の上限と比較してください。累積カウンターだけでは、仮想NICの公称速度だけでも、どこでも一律に10Gbpsだと仮定しても、飽和したことは判断できません。

</details>

### 10. Alertmanager の alert inhibition rule の目的は何ですか？

- A) alert priority を上げること
- B) parent alert が firing しているときに dependent alert を suppress すること
- C) alert を別の receiver に route すること
- D) 新しい alert を作成すること

<details>
<summary>回答を表示</summary>

**回答: B) parent alert が firing しているときに dependent alert を suppress すること**

**解説:**
Inhibitionは、設定されたsource/target matcherとequal labelに従って、一致する通知を抑制します。これだけで根本原因が特定されるわけではありません。ラベルが欠けている場合に無関係なアラートまで抑制しないよう、clusterやentityを識別する値が空でないことを必須にしてください。Prometheusでのアラート評価は続きます。

</details>
