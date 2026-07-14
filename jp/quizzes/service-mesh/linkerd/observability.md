# Linkerd Observability クイズ

このクイズでは、Linkerd の observability 機能に関する理解度を確認します。

## クイズ問題

### 1. Linkerd によって自動的に収集される golden metric ではないものはどれですか？

A. Success rate
B. Request rate (RPS)
C. Latency
D. CPU usage

<details>
<summary>回答を表示</summary>

**回答: D. CPU usage**

**解説:**
Linkerd は、success rate、request rate (RPS)、latency（p50、p95、p99）の 3 つの golden metric を自動的に収集します。CPU usage は Kubernetes の metric であり、別途収集する必要があります。

</details>

### 2. `linkerd viz stat` コマンドの出力に含まれないものはどれですか？

A. SUCCESS (success rate)
B. RPS (request rate)
C. LATENCY_P99
D. ERROR_TYPE

<details>
<summary>回答を表示</summary>

**回答: D. ERROR_TYPE**

**解説:**
`linkerd viz stat` は MESHED、SUCCESS、RPS、LATENCY_P50/P95/P99 を表示します。エラータイプは `linkerd viz tap` またはログで確認する必要があります。

</details>

### 3. `linkerd viz tap` コマンドの目的は何ですか？

A. Network packet capture
B. リアルタイムの request stream を表示する
C. proxy configuration を変更する
D. certificate を更新する

<details>
<summary>回答を表示</summary>

**回答: B. リアルタイムの request stream を表示する**

**解説:**
`linkerd viz tap` は request をリアルタイムでストリーミングします。request method、path、status code、latency、mTLS status などを表示します。

</details>

### 4. ServiceProfile を定義することで、どの追加 metric を取得できますか？

A. Pod resource usage
B. route ごとの metric
C. Network bandwidth
D. Disk I/O

<details>
<summary>回答を表示</summary>

**回答: B. route ごとの metric**

**解説:**
ServiceProfile を定義すると、route ごと（例: GET /api/users、POST /api/orders）の success rate、request rate、latency metric を収集できるようになります。`linkerd viz routes` コマンドで確認できます。

</details>

### 5. Viz extension の Prometheus にアクセスするデフォルトの方法は何ですか？

A. NodePort service
B. LoadBalancer service
C. kubectl port-forward
D. Public URL

<details>
<summary>回答を表示</summary>

**回答: C. kubectl port-forward**

**解説:**
Viz の Prometheus は ClusterIP service としてデプロイされます。`kubectl port-forward -n linkerd-viz svc/prometheus 9090:9090` でアクセスします。セキュリティ上、外部公開は推奨されません。

</details>

### 6. distributed tracing の propagation に必要ではない header はどれですか？

A. x-b3-traceid
B. x-request-id
C. x-linkerd-proxy
D. x-b3-spanid

<details>
<summary>回答を表示</summary>

**回答: C. x-linkerd-proxy**

**解説:**
distributed tracing に必要な header: x-request-id、x-b3-traceid、x-b3-spanid、x-b3-parentspanid、x-b3-sampled、b3 など。x-linkerd-proxy は存在しません。

</details>

### 7. `linkerd viz top` コマンドは何を表示しますか？

A. 最も多くの resource を使用している Pod
B. 最もアクティブな request path
C. 主な error message
D. 最新の log entry

<details>
<summary>回答を表示</summary>

**回答: B. 最もアクティブな request path**

**解説:**
`linkerd viz top` は、最もアクティブな request path をリアルタイムで表示します。Source、Destination、Method、Path、Count、Latency、Success Rate などが表示されます。

</details>

### 8. proxy log level を設定する annotation はどれですか？

A. config.linkerd.io/log-level
B. config.linkerd.io/proxy-log-level
C. linkerd.io/proxy-log
D. proxy.linkerd.io/log-level

<details>
<summary>回答を表示</summary>

**回答: B. config.linkerd.io/proxy-log-level**

**解説:**
`config.linkerd.io/proxy-log-level` annotation は proxy log level を設定します。例: "warn,linkerd=info,linkerd_proxy=debug"

</details>

### 9. Linkerd の success rate を計算する正しい Prometheus query はどれですか？

A. `sum(response_total{classification="success"}) / sum(response_total)`
B. `rate(success_total[5m]) / rate(request_total[5m])`
C. `sum(rate(response_total{classification="success"}[5m])) / sum(rate(response_total[5m]))`
D. `avg(success_rate)`

<details>
<summary>回答を表示</summary>

**回答: C. `sum(rate(response_total{classification="success"}[5m])) / sum(rate(response_total[5m]))`**

**解説:**
success rate は、成功した response rate を合計 response rate で割って計算します。rate() 関数は時間範囲内の 1 秒あたりの rate を計算し、sum() は集計を行います。

</details>

### 10. Jaeger extension の主な機能は何ですか？

A. Metrics collection
B. Log aggregation
C. Distributed tracing
D. Traffic splitting

<details>
<summary>回答を表示</summary>

**回答: C. Distributed tracing**

**解説:**
Jaeger extension は distributed tracing を提供します。複数の Service を通過する request の完全な path を可視化し、各ステップの latency を分析します。

</details>

### 11. linkerd viz dashboard コマンドで提供されない view はどれですか？

A. Topology
B. Deployments
C. Pod Logs
D. Routes

<details>
<summary>回答を表示</summary>

**回答: C. Pod Logs**

**解説:**
Viz dashboard は Namespace、Deployments、Pods、TCP、Routes、Topology、Tap view を提供します。Pod log は kubectl logs または別の logging system で確認する必要があります。

</details>

### 12. external Grafana と統合する際に使用する Viz installation option はどれですか？

A. `--set grafana.external=true`
B. `--set grafana.enabled=false`
C. `--set grafana.url=external`
D. `--set monitoring=external`

<details>
<summary>回答を表示</summary>

**回答: B. `--set grafana.enabled=false`**

**解説:**
external Grafana を使用する場合は、Viz の組み込み Grafana を無効にします。`helm install linkerd-viz linkerd/linkerd-viz --set grafana.enabled=false` を使用するか、values file で設定します。

</details>
