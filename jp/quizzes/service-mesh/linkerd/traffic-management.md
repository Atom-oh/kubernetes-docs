# Linkerd Traffic Management クイズ

このクイズでは、Linkerd Traffic Management の理解度を確認します。

## クイズ問題

### 1. ServiceProfile で Route ごとに設定できないものはどれですか？

A. Timeout
B. Retryability
C. Load balancer algorithm
D. Path condition

<details>
<summary>回答を表示</summary>

**回答: C. Load balancer algorithm**

**解説:**
ServiceProfile では、Route ごとに timeout、retryability（isRetryable）、および path condition（method、pathRegex）を設定できます。Load balancer algorithm は、EWMA を使用する Linkerd のグローバル設定です。

</details>

### 2. Linkerd はどの Load balancing algorithm を使用しますか？

A. Round Robin
B. Least Connections
C. EWMA (Exponentially Weighted Moving Average)
D. Random

<details>
<summary>回答を表示</summary>

**回答: C. EWMA (Exponentially Weighted Moving Average)**

**解説:**
Linkerd は EWMA algorithm を使用し、より速い response latency を持つ endpoint を優先します。endpoint の状態にリアルタイムで適応し、遅い endpoint への traffic を自動的に削減します。

</details>

### 3. TrafficSplit はどの標準仕様に従っていますか？

A. CNCF
B. SMI (Service Mesh Interface)
C. OpenAPI
D. gRPC

<details>
<summary>回答を表示</summary>

**回答: B. SMI (Service Mesh Interface)**

**解説:**
TrafficSplit は、SMI (Service Mesh Interface) 標準に従う CRD です。SMI は、異なる mesh implementation 間の互換性を提供するために、service mesh 用の共通 interface を定義します。

</details>

### 4. retryBudget の retryRatio が 0.2 であることは何を意味しますか？

A. すべての request のうち 20% のみが retry される
B. 失敗した request のうち 20% のみが retry される
C. 元の request に対して最大 20% の追加 retry が許可される
D. Retry budget は 20 秒ごとにリセットされる

<details>
<summary>回答を表示</summary>

**回答: C. 元の request に対して最大 20% の追加 retry が許可される**

**解説:**
retryRatio が 0.2 の場合、元の request 数に対して最大 20% の追加 retry が許可されます。例: 100 request に対して最大 20 回の追加 retry が許可されます。これにより、retry による overload を防止します。

</details>

### 5. ServiceProfile を auto-generate する方法ではないものはどれですか？

A. OpenAPI/Swagger spec から generate する
B. live traffic tap から generate する
C. Protobuf definition から generate する
D. Kubernetes Service から auto-generate する

<details>
<summary>回答を表示</summary>

**回答: D. Kubernetes Service から auto-generate する**

**解説:**
ServiceProfile は、`linkerd profile --open-api`、`linkerd viz profile --tap`、および `linkerd profile --proto` command を使用して generate できます。Kubernetes Service から auto-generate されることはなく、明示的に定義する必要があります。

</details>

### 6. canary deployment において、TrafficSplit backend weight の合計はいくつにすべきですか？

A. 必ず 100 でなければならない
B. 必ず 1 でなければならない
C. 任意の値でよい（ratio として計算される）
D. 必ず 1000 でなければならない

<details>
<summary>回答を表示</summary>

**回答: C. 任意の値でよい（ratio として計算される）**

**解説:**
TrafficSplit weight は相対 ratio として計算されます。weight: 90 と weight: 10 は、weight: 9 と weight: 1 と同等です。合計を 100 にする必要はありません。

</details>

### 7. HTTPRoute (Gateway API) でサポートされていない routing condition はどれですか？

A. Header-based routing
B. Path-based routing
C. Cookie-based routing
D. Source IP-based routing

<details>
<summary>回答を表示</summary>

**回答: D. Source IP-based routing**

**解説:**
HTTPRoute は、header、path、method、cookie（header 経由）に基づく routing をサポートします。Source IP-based routing は L7 routing の範囲外であり、NetworkPolicy またはその他の mechanism によって処理されます。

</details>

### 8. Flagger を Linkerd と統合する際に使用される metrics server はどれですか？

A. Metrics Server
B. Prometheus
C. InfluxDB
D. Datadog

<details>
<summary>回答を表示</summary>

**回答: B. Prometheus**

**解説:**
Flagger は、canary analysis のために Linkerd Viz の Prometheus から metrics（success rate、latency など）を取得します。Flagger を install する際は、`--set metricsServer=http://prometheus.linkerd-viz:9090` を使用して接続します。

</details>

### 9. ServiceProfile の isRetryable が false である Route では何が起こりますか？

A. すべての request が失敗する
B. retry は発生しない
C. timeout が無視される
D. Route が無効になる

<details>
<summary>回答を表示</summary>

**回答: B. retry は発生しない**

**解説:**
isRetryable: false は、その Route 上の request が失敗しても retry されないことを意味します。これは、POST request のような non-idempotent operation に適しています。request 自体は通常どおり処理されます。

</details>

### 10. Linkerd では Circuit Breaker pattern はどのように実装されますか？

A. Circuit Breaker CRD
B. Failure Accrual
C. Rate Limiter
D. Timeout Policy

<details>
<summary>回答を表示</summary>

**回答: B. Failure Accrual**

**解説:**
Linkerd は、failure accrual を通じて circuit breaker pattern を実装します。連続した failure が発生すると endpoint を一時的に除外し、exponential backoff で retry し、成功すると通常の状態に戻ります。

</details>

### 11. traffic splitting を使用せずに mirror service へ traffic を送信するにはどうしますか？

A. TrafficMirror CRD を使用する
B. mirror service の DNS を直接呼び出す
C. すべての traffic は自動的に mirror される
D. Linkerd は traffic mirroring をサポートしていない

<details>
<summary>回答を表示</summary>

**回答: B. mirror service の DNS を直接呼び出す**

**解説:**
Linkerd 自体には、Istio のような traffic mirroring 機能はありません。multi-cluster mirror service（例: web-west）は、DNS 経由で直接呼び出すか、TrafficSplit weight を使用して設定する必要があります。

</details>

### 12. ServiceProfile の timeout が設定されていない Route では何が起こりますか？

A. デフォルトの 5 秒 timeout が適用される
B. timeout なし（無制限）
C. request が即座に失敗する
D. グローバル timeout が適用される

<details>
<summary>回答を表示</summary>

**回答: B. timeout なし（無制限）**

**解説:**
ServiceProfile で timeout が指定されていない Route は、timeout なしで無期限に待機します。これは streaming または long-running operation に適していますが、一般的には明示的に timeout を設定することが推奨されます。

</details>
