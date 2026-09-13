# Istioメトリクス

> **対応バージョン**: Istio 1.31
> **最終更新**: September 11, 2026

> **検証範囲**: 演習設定は公式資料とオフライン検証器で確認し、クラスターはデプロイしていません。名前空間、ID、ストレージ、バックエンド、負荷の前提は各例で示し、対象環境で検証する必要があります。

Istioプロキシは観測通信のメトリクスを生成します。サイドカー/EnvoyのHTTP/TCPメトリクスと、PrometheusまたはOpenTelemetry Collectorによる収集を扱います。Ambient ztunnelのL4メトリクスは異なり、HTTPにはwaypointが必要です。

## 目次

1. [メトリクス概要](#metrics-overview)
2. [Istio標準メトリクス](#istio-standard-metrics)
3. [サーキットブレーカーメトリクス](#circuit-breaker-metrics)
4. [耐障害性メトリクス](#resilience-metrics)
5. [OpenTelemetry統合](#opentelemetry-integration)
6. [Prometheus統合](#prometheus-integration)
7. [Telemetry APIによるカスタマイズ](#customization-with-telemetry-api)
8. [実用メトリクスクエリ](#practical-metric-queries)
9. [メトリクス最適化](#metrics-optimization)
10. [トラブルシューティング](#troubleshooting)

## メトリクス概要 {#metrics-overview}

### ゴールデンシグナル

プロキシテレメトリーとノード/コンテナエクスポーターを組み合わせて測定します。

1. **レイテンシー**: 要求処理時間
2. **トラフィック**: システムスループット（RPS、帯域）
3. **エラー**: 失敗率とエラー種別
4. **飽和**: キュー/接続の圧力とKubernetesエクスポーターのCPU/メモリ

### メトリクス収集アーキテクチャ

EnvoyがPrometheusメトリクスを公開 → Prometheusが直接、またはOpenTelemetry CollectorのPrometheus receiverがスクレイプ → 設定済みメトリクスbackend → Grafana/Kiali。Istio OpenTelemetry拡張providerはトレースを設定し、OTLPメトリクス送信器ではありません。

## Istio標準メトリクス {#istio-standard-metrics}

### HTTP/gRPCメトリクス

Envoyは認識したHTTP/gRPC通信で生成します。報告プロキシごとに出るため、問いに合うreporterを1つ選びます。destination報告はホップの重複観測を避け、宛先に届かなかった上流失敗にはsource報告が必要です。サービス名は名前空間（必要ならクラスターも）とまとめます。

#### istio_requests_total

**型**: Counter
**説明**: 処理した総要求数

```promql
istio_requests_total{
  reporter="destination",  # Peer security policy populated at destination
  source_workload="productpage-v1",
  source_workload_namespace="default",
  source_principal="spiffe://cluster.local/ns/default/sa/bookinfo-productpage",
  source_app="productpage",
  source_version="v1",
  source_canonical_service="productpage",
  source_canonical_revision="v1",
  destination_workload="reviews-v1",
  destination_workload_namespace="default",
  destination_principal="spiffe://cluster.local/ns/default/sa/bookinfo-reviews",
  destination_app="reviews",
  destination_version="v1",
  destination_service="reviews.default.svc.cluster.local",
  destination_service_name="reviews",
  destination_service_namespace="default",
  destination_canonical_service="reviews",
  destination_canonical_revision="v1",
  request_protocol="http",
  response_code="200",
  response_flags="-",
  connection_security_policy="mutual_tls",
  grpc_response_status="",
  destination_cluster="",
  source_cluster=""
}
```

**主なラベル**:
- `response_code`: HTTP状態コード（200、404、500など）
- `response_flags`: Envoy応答フラグ
  - `UH`: 正常な上流なし
  - `UF`: 上流接続失敗
  - `UR`: 上流リモートリセット。`UT`: 上流要求タイムアウト
  - `DC`: 下流接続終了
  - `LR`: ローカルリセット
  - `URX`: 上流再試行上限超過（またはTCP最大接続試行数）
- `connection_security_policy`: mTLS状態（`mutual_tls`、`none`。source報告は`unknown`の場合あり）

#### istio_request_duration_milliseconds

**型**: Histogram
**説明**: 要求処理時間（ミリ秒）

```promql
istio_request_duration_milliseconds_bucket{le="10"}  # 10ms or less
istio_request_duration_milliseconds_bucket{le="50"}  # 50ms or less
istio_request_duration_milliseconds_bucket{le="100"} # 100ms or less
istio_request_duration_milliseconds_bucket{le="500"} # 500ms or less
istio_request_duration_milliseconds_sum            # Total time
istio_request_duration_milliseconds_count          # Total request count
```

#### istio_request_bytes

**型**: Histogram
**説明**: 要求本文サイズ（バイト）

```promql
istio_request_bytes_bucket  # Inspect actual le bounds
istio_request_bytes_bucket{le="+Inf"}  # All body sizes
istio_request_bytes_sum
istio_request_bytes_count
```

#### istio_response_bytes

**型**: Histogram
**説明**: 応答本文サイズ（バイト）

```promql
istio_response_bytes_bucket
istio_response_bytes_bucket{le="+Inf"}
istio_response_bytes_sum
istio_response_bytes_count
```

### TCPメトリクス

#### istio_tcp_connections_opened_total

**型**: Counter
**説明**: 開いたTCP接続数

```promql
istio_tcp_connections_opened_total{
  reporter="source",
  source_workload="mongodb-v1",
  destination_service="mongodb.default.svc.cluster.local"
}
```

#### istio_tcp_connections_closed_total

**型**: Counter
**説明**: 閉じたTCP接続数

#### istio_tcp_sent_bytes_total

**型**: Counter
**説明**: 送信バイト数

#### istio_tcp_received_bytes_total

**型**: Counter
**説明**: 受信バイト数

## サーキットブレーカーメトリクス {#circuit-breaker-metrics}

スクレイプ前に`proxyStatsMatcher`で必要Envoy統計を有効にします。デフォルトIstio bootstrapは`cluster_name`を抽出しますが、カスタムではラベルが変わり得ます。ブレーカーの`_open`は0/1ゲージで、イベントカウンターではありません。一部カウンターは通信後だけ現れます。

### 主なサーキットブレーカーメトリクス

#### 1. 上流接続プール超過

```promql
# Requests rejected due to connection pool overflow
envoy_cluster_upstream_cx_overflow{
  cluster_name="outbound|80||httpbin.default.svc.cluster.local"
}
```

**意味**: `maxConnections`上限超過

#### 2. サーキットブレーカー開状態（ゲージ）

```promql
# Gauge: 1 at capacity, 0 below limit
envoy_cluster_circuit_breakers_default_rq_open{
  cluster_name="outbound|80||httpbin.default.svc.cluster.local"
}
```

#### 3. 保留要求の超過

```promql
# Pending request count exceeded
envoy_cluster_upstream_rq_pending_overflow{
  cluster_name="outbound|80||httpbin.default.svc.cluster.local"
}
```

**意味**: 保留/アクティブ要求のブレーカー拒否。`rq_pending_open`、`rq_open`、生成しきい値を調べ、キュー圧力とアクティブ要求上限を区別します。

#### 4. 再試行予算の枯渇

```promql
# Retry budget exhausted
envoy_cluster_upstream_rq_retry_overflow{
  cluster_name="outbound|80||httpbin.default.svc.cluster.local"
}
```

#### 5. 応答フラグによるブレーカー検出

```promql
# Requests rejected by circuit breaker (response_flags="UO")
sum(rate(istio_requests_total{reporter="source",
  response_flags=~".*UO.*",
  destination_service="httpbin.default.svc.cluster.local"
}[5m]))
```

**応答フラグ詳細**:
- `UO`: 上流超過（ブレーカー開）
- `URX`: 上流再試行上限超過（またはTCP最大接続試行数）
- `UF`: 上流接続失敗
- `UH`: 正常な上流なし

### ブレーカー監視ダッシュボードクエリ

```promql
# Fraction of observed samples at capacity over five minutes (%).
100 * avg_over_time(envoy_cluster_circuit_breakers_default_rq_open[5m])

# Active connections and pending requests (per proxy/cluster).
envoy_cluster_upstream_cx_active
envoy_cluster_upstream_rq_pending_active

# Rejected request events over five minutes.
sum by (namespace, pod, cluster_name) (
  increase(envoy_cluster_upstream_rq_pending_overflow[5m])
)
```

標準の`circuit_breakers_default_cx_max`や`rq_pending_max`ゲージはありません。生成クラスター設定から上限を読みます。任意の`remaining_cx`/`remaining_pending`にはEnvoy `track_remaining`が必要で、メトリクス名を含めるだけでは有効になりません。使用率分母は一致する既知の設定上限から得る必要があります。

### ブレーカーのアラートルール

```yaml
groups:
- name: istio_circuit_breaker
  rules:
  - alert: CircuitBreakerAtCapacity
    expr: envoy_cluster_circuit_breakers_default_rq_open == 1
    for: 1m
    labels:
      severity: warning
    annotations:
      summary: Request breaker remains at capacity for {{ $labels.cluster_name }}
  - alert: ConnectionPoolOverflow
    expr: rate(envoy_cluster_upstream_cx_overflow[5m]) > 0
    for: 2m
    labels:
      severity: warning
    annotations:
      summary: Connection limit exceeded for {{ $labels.cluster_name }}
  - alert: PendingRequestsOverflow
    expr: rate(envoy_cluster_upstream_rq_pending_overflow[5m]) > 0
    for: 2m
    labels:
      severity: warning
    annotations:
      summary: Request circuit-breaking rejection for {{ $labels.cluster_name }}
```

## 耐障害性メトリクス {#resilience-metrics}

### 外れ値検出メトリクス

#### 1. 除外ホスト

```promql
# Number of hosts ejected by outlier detection
envoy_cluster_outlier_detection_ejections_active{
  cluster_name="outbound|80||httpbin.default.svc.cluster.local"
}
```

#### 2. 除外イベント

```promql
# Ejection event rate
rate(envoy_cluster_outlier_detection_ejections_enforced_total[5m])
```

**除外タイプ別**:
```promql
# Consecutive 5xx errors
envoy_cluster_outlier_detection_ejections_enforced_consecutive_5xx

# Success rate based
envoy_cluster_outlier_detection_ejections_enforced_success_rate

# Failure percentage based
envoy_cluster_outlier_detection_ejections_enforced_failure_percentage
```

検出と適用は異なります。外れ値を検出しても適用確率や最大除外率で除外されず提供し続ける場合があります。一部EnvoyアルゴリズムはIstio DestinationRuleから公開されません。系列がないことは設定アルゴリズムの健全性の証拠ではありません。

### 再試行メトリクス

```promql
# Number of retried requests
rate(envoy_cluster_upstream_rq_retry[5m])

# Retry success rate
rate(envoy_cluster_upstream_rq_retry_success[5m])
/
rate(envoy_cluster_upstream_rq_retry[5m])

# Retry budget exhausted
rate(envoy_cluster_upstream_rq_retry_overflow[5m])
```

### タイムアウトメトリクス

```promql
# Requests that timed out
sum(rate(istio_requests_total{reporter="source",
  response_flags=~".*UT.*"
}[5m])) by (destination_service)

# Timeout rate
sum(rate(istio_requests_total{reporter="source",response_flags=~".*UT.*"}[5m]))
/
sum(rate(istio_requests_total{reporter="source"}[5m]))
* 100
```

## OpenTelemetry統合 {#opentelemetry-integration}

### Istioメトリクス用Prometheus receiver

Istioの`opentelemetry`拡張providerは**トレース**を出力します。標準メッシュメトリクスにはPrometheus providerを維持し、OpenTelemetry Collectorの**Prometheus receiverで公開エンドポイントをスクレイプ**します。Collectorはメトリクス対応backendへOTLPで送れます。Tempoはトレースbackendで、メトリクス宛先ではありません。

例はCollector Contrib 0.160.0とPrometheusエクスポーターを使い、確認可能なデモ経路を作ります。先に`observability`を作成します。同一スクレイプ設定のレプリカは全対象を重複収集するため1レプリカです。本番拡張には対象割り当て/シャーディングが必要です。ServiceAccountはPod検出jobに必要なPod読み取りだけできます。平文プロキシメトリクス15090とistiod 15014へのアクセスを設定します。アプリメトリクスとambient ztunnelは収集しません。

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: otel-metrics
  namespace: observability
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: otel-metrics-pod-reader
rules:
- apiGroups:
  - ''
  resources:
  - pods
  verbs:
  - get
  - list
  - watch
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: otel-metrics-pod-reader
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: otel-metrics-pod-reader
subjects:
- kind: ServiceAccount
  name: otel-metrics
  namespace: observability
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: otel-metrics-config
  namespace: observability
data:
  config.yaml: |
    receivers:
      prometheus:
        config:
          global:
            scrape_interval: 15s
            evaluation_interval: 15s
          scrape_configs:
          - job_name: envoy-stats
            metrics_path: /stats/prometheus
            kubernetes_sd_configs:
            - role: pod
            relabel_configs:
            - source_labels:
              - __meta_kubernetes_pod_phase
              action: keep
              regex: Running
            - source_labels:
              - __meta_kubernetes_pod_container_name
              - __meta_kubernetes_pod_container_port_name
              action: keep
              regex: istio-proxy;.*-envoy-prom
            - source_labels:
              - __meta_kubernetes_namespace
              target_label: namespace
            - source_labels:
              - __meta_kubernetes_pod_name
              target_label: pod
          - job_name: istiod
            metrics_path: /metrics
            kubernetes_sd_configs:
            - role: pod
              namespaces:
                names:
                - istio-system
            relabel_configs:
            - source_labels:
              - __meta_kubernetes_pod_label_app
              - __meta_kubernetes_pod_container_port_name
              action: keep
              regex: istiod;http-monitoring
            - source_labels:
              - __meta_kubernetes_namespace
              target_label: namespace
            - source_labels:
              - __meta_kubernetes_pod_name
              target_label: pod
    processors:
      memory_limiter:
        check_interval: 1s
        limit_mib: 512
      batch:
        timeout: 10s
        send_batch_size: 1024
    exporters:
      prometheus:
        endpoint: 0.0.0.0:8889
        const_labels:
          environment: production
      debug:
        verbosity: basic
    service:
      pipelines:
        metrics:
          receivers:
          - prometheus
          processors:
          - memory_limiter
          - batch
          exporters:
          - prometheus
          - debug
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: otel-metrics
  namespace: observability
spec:
  replicas: 1
  selector:
    matchLabels:
      app: otel-metrics
  template:
    metadata:
      labels:
        app: otel-metrics
      annotations:
        sidecar.istio.io/inject: 'false'
    spec:
      serviceAccountName: otel-metrics
      containers:
      - name: otel-collector
        image: otel/opentelemetry-collector-contrib:0.160.0
        args:
        - --config=/etc/otel/config.yaml
        ports:
        - containerPort: 8889
          name: prometheus
        volumeMounts:
        - name: config
          mountPath: /etc/otel
          readOnly: true
        resources:
          requests:
            cpu: 200m
            memory: 512Mi
          limits:
            cpu: 1000m
            memory: 1Gi
      volumes:
      - name: config
        configMap:
          name: otel-metrics-config
---
apiVersion: v1
kind: Service
metadata:
  name: otel-metrics
  namespace: observability
  labels:
    app: otel-metrics
spec:
  selector:
    app: otel-metrics
  ports:
  - name: prometheus
    port: 8889
    targetPort: prometheus
```

廃止`logging`エクスポーターは`debug`に置換されています。検証後は診断出力を除去します。既存名に第2の`istio_`が付かないよう、`namespace: istio`は加えません。Kialiダッシュボード再利用前に出力ラベル/名前を確認します。Prometheus Operatorではラベル付きServiceを選びます。

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: otel-metrics
  namespace: observability
spec:
  selector:
    matchLabels:
      app: otel-metrics
  endpoints:
  - port: prometheus
    interval: 15s
    path: /metrics
    honorLabels: true
```

PrometheusはこのServiceMonitorと名前空間を選ぶ必要があります。`honorLabels`は元の`job`/`instance`を保持するため、Collectorは信頼するソースでなければなりません。同じ系列にはこの経路か下の直接スクレイプのどちらかを使い、両方は使いません。このServiceMonitorはPrometheusをインストールしません。

### 収集の確認

```bash
kubectl logs -n observability deployment/otel-metrics
# Keep this running in one terminal.
kubectl port-forward -n observability svc/otel-metrics 8889:8889
```

```bash
# In a second terminal, after generating test mesh traffic:
curl -fsS http://localhost:8889/metrics | rg '^istio_'
```

トレースOTLP receiver/exporterは[トレース章](02-tracing.md)で別設定します。プロキシデバッグログはメトリクス配信を証明しません。

## Prometheus統合 {#prometheus-integration}

### Prometheus設定

Pod list/watch権限を持つ導入済みPrometheusで使います。ConfigMap単体はデプロイ/再読み込みしません。Pod検出jobはIPv6も含むKubernetes検出アドレスを保持し、Envoyメトリクスかistiod監視ポートを正確に選びます。サイドカーとGatewayを含むため別Gateway jobは重複します。削除されたMixer `istio-telemetry` Serviceは対象ではありません。

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: prometheus-config
  namespace: istio-system
data:
  prometheus.yml: |
    global:
      scrape_interval: 15s
      evaluation_interval: 15s
    scrape_configs:
    - job_name: envoy-stats
      metrics_path: /stats/prometheus
      kubernetes_sd_configs:
      - role: pod
      relabel_configs:
      - source_labels:
        - __meta_kubernetes_pod_phase
        action: keep
        regex: Running
      - source_labels:
        - __meta_kubernetes_pod_container_name
        - __meta_kubernetes_pod_container_port_name
        action: keep
        regex: istio-proxy;.*-envoy-prom
      - source_labels:
        - __meta_kubernetes_namespace
        target_label: namespace
      - source_labels:
        - __meta_kubernetes_pod_name
        target_label: pod
    - job_name: istiod
      metrics_path: /metrics
      kubernetes_sd_configs:
      - role: pod
        namespaces:
          names:
          - istio-system
      relabel_configs:
      - source_labels:
        - __meta_kubernetes_pod_label_app
        - __meta_kubernetes_pod_container_port_name
        action: keep
        regex: istiod;http-monitoring
      - source_labels:
        - __meta_kubernetes_namespace
        target_label: namespace
      - source_labels:
        - __meta_kubernetes_pod_name
        target_label: pod
```

プロキシ専用スクレイプは15090の`/stats/prometheus`です。デフォルト統合エージェント/アプリメトリクスは`prometheus.io`アノテーションで15020の`/stats/prometheus`を使い、別の重複しないjobが必要です。エージェント証明書メトリクスにもそのエンドポイントが必要です。アプリがSTRICT mTLSでもこれらは平文なので、ネットワーク公開を制限します。別アプリエンドポイントのスクレイプは独自認証ポリシーに従います。

### Prometheus Operatorによる代替

手動jobの代わりに使います。Prometheusがラベル/名前空間を選ぶことを確認します。`namespaceSelector.any: true`はPodMonitorにアプリ名前空間を調べさせ、`port: http-envoy-prom`は実メトリクスコンテナポートを選びます。カスタムGatewayならポート名を合わせます。ServiceMonitorはDeploymentラベルでなくServiceを選びます。

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: istio-component-monitor
  namespace: istio-system
spec:
  selector:
    matchLabels:
      app: istiod
  endpoints:
  - port: http-monitoring
    interval: 15s
    path: /metrics
---
apiVersion: monitoring.coreos.com/v1
kind: PodMonitor
metadata:
  name: envoy-stats-monitor
  namespace: istio-system
spec:
  namespaceSelector:
    any: true
  selector:
    matchExpressions:
    - key: istio-prometheus-ignore
      operator: DoesNotExist
  podMetricsEndpoints:
  - port: http-envoy-prom
    path: /stats/prometheus
    interval: 15s
    relabelings:
    - sourceLabels:
      - __meta_kubernetes_pod_container_name
      action: keep
      regex: istio-proxy
```

### Prometheusクエリ最適化

```yaml
# Recording Rules to pre-compute frequently used queries
groups:
- name: istio_recording_rules
  interval: 30s
  rules:
  # Request rate by service
  - record: istio:service:request_rate:5m
    expr: |
      sum(rate(istio_requests_total{reporter="destination"}[5m])) by (destination_service_name, destination_service_namespace)

  # Error rate by service
  - record: istio:service:error_rate:5m
    expr: |
      sum(rate(istio_requests_total{reporter="destination",response_code=~"5.."}[5m])) by (destination_service_name, destination_service_namespace)
      /
      sum(rate(istio_requests_total{reporter="destination"}[5m])) by (destination_service_name, destination_service_namespace)

  # P95 latency by service
  - record: istio:service:latency_p95:5m
    expr: |
      histogram_quantile(0.95,
        sum(rate(istio_request_duration_milliseconds_bucket{reporter="destination"}[5m]))
        by (destination_service_name, destination_service_namespace, le)
      )

  # Circuit breaker state gauge
  - record: istio:circuit_breaker:at_capacity
    expr: |
      envoy_cluster_circuit_breakers_default_rq_open
```

## Telemetry APIによるカスタマイズ {#customization-with-telemetry-api}

### メトリクスのカスタマイズ

#### 1. 特定メトリクスだけ有効化

上書きは順番に評価します。最初にALL_METRICSを無効にし、必要なHTTPメトリクス2つを再有効化します。`mode`は`match`内です。独立例を全部適用せず、選択範囲ごとに1 Telemetryへ関連設定をマージします。

```yaml
apiVersion: telemetry.istio.io/v1
kind: Telemetry
metadata:
  name: custom-metrics
  namespace: istio-system
spec:
  metrics:
  - providers:
    - name: prometheus
    overrides:
    - match:
        metric: ALL_METRICS
        mode: CLIENT_AND_SERVER
      disabled: true
    - match:
        metric: REQUEST_COUNT
        mode: CLIENT_AND_SERVER
      disabled: false
    - match:
        metric: REQUEST_DURATION
        mode: CLIENT_AND_SERVER
      disabled: false
```

#### 2. カスタムラベルの追加

HTTPメトリクスで値を限定したCEL式を使います。request ID、任意User-Agent、タイミングヘッダーは無制限ラベルを生みます。`x-envoy-upstream-service-time`は時間で、上流クラスターIDではありません。CELは例のシェル型`| split()`構文を使いません。

```yaml
apiVersion: telemetry.istio.io/v1
kind: Telemetry
metadata:
  name: custom-tags
  namespace: prod
spec:
  metrics:
  - providers:
    - name: prometheus
    overrides:
    - match:
        metric: REQUEST_COUNT
      tagOverrides:
        api_version:
          value: 'request.url_path.startsWith("/api/v1/") ? "v1" : (request.url_path.startsWith("/api/v2/")
            ? "v2" : "other")'
        request_method:
          value: 'request.method in ["GET", "POST", "PUT", "DELETE"] ? request.method
            : "OTHER"'
```

#### 3. 名前空間固有メトリクス設定

```yaml
apiVersion: telemetry.istio.io/v1
kind: Telemetry
metadata:
  name: namespace-metrics
  namespace: production
spec:
  metrics:
  - providers:
    - name: prometheus
    overrides:
    - match:
        metric: REQUEST_COUNT
        mode: CLIENT_AND_SERVER
      tagOverrides:
        environment:
          value: '"production"'
```

#### 4. メトリクス無効化による性能改善

```yaml
apiVersion: telemetry.istio.io/v1
kind: Telemetry
metadata:
  name: disable-tcp-metrics
  namespace: istio-system
spec:
  metrics:
  - providers:
    - name: prometheus
    overrides:
    # Completely disable TCP metrics
    - match:
        metric: TCP_OPENED_CONNECTIONS
      disabled: true
    - match:
        metric: TCP_CLOSED_CONNECTIONS
      disabled: true
    - match:
        metric: TCP_SENT_BYTES
      disabled: true
    - match:
        metric: TCP_RECEIVED_BYTES
      disabled: true
```

## 実用メトリクスクエリ {#practical-metric-queries}

HTTP状態ベースのエラー比率は全gRPC失敗を捉えません。gRPCでは`grpc_response_status`とアプリの失敗定義を調べます。HTTP 200でも非ゼロgRPC状態を運べます。

### ゴールデンシグナルダッシュボード

#### 1. レイテンシー

```promql
# P50 latency
histogram_quantile(0.50,
  sum(rate(istio_request_duration_milliseconds_bucket{reporter="destination",
    destination_service_name="reviews", destination_service_namespace="default"
  }[5m])) by (le)
)

# P95 latency
histogram_quantile(0.95,
  sum(rate(istio_request_duration_milliseconds_bucket{reporter="destination",
    destination_service_name="reviews", destination_service_namespace="default"
  }[5m])) by (le)
)

# P99 latency
histogram_quantile(0.99,
  sum(rate(istio_request_duration_milliseconds_bucket{reporter="destination",
    destination_service_name="reviews", destination_service_namespace="default"
  }[5m])) by (le)
)

# Average latency by service
sum(rate(istio_request_duration_milliseconds_sum{reporter="destination"}[5m])) by (destination_service_name, destination_service_namespace)
/
sum(rate(istio_request_duration_milliseconds_count{reporter="destination"}[5m])) by (destination_service_name, destination_service_namespace)
```

#### 2. トラフィック

```promql
# Request rate by service (RPS)
sum(rate(istio_requests_total{reporter="destination"}[1m])) by (destination_service_name, destination_service_namespace)

# Total request rate
sum(rate(istio_requests_total{reporter="destination"}[1m]))

# Inbound traffic by service (bytes/sec)
sum(rate(istio_request_bytes_sum{reporter="destination"}[1m])) by (destination_service_name, destination_service_namespace)

# Outbound traffic by service (bytes/sec)
sum(rate(istio_response_bytes_sum{reporter="destination"}[1m])) by (destination_service_name, destination_service_namespace)

# Request distribution by protocol (not HTTP method)
sum(rate(istio_requests_total{reporter="destination"}[5m])) by (request_protocol, destination_service_name, destination_service_namespace)
```

#### 3. エラー

```promql
# Error rate (5xx errors)
sum(rate(istio_requests_total{response_code=~"5..", reporter="destination"}[5m])) by (destination_service_name, destination_service_namespace)
/
sum(rate(istio_requests_total{reporter="destination"}[5m])) by (destination_service_name, destination_service_namespace)
* 100

# Separate 4xx vs 5xx
sum(rate(istio_requests_total{response_code=~"4..", reporter="destination"}[5m])) by (destination_service_name, destination_service_namespace)
sum(rate(istio_requests_total{response_code=~"5..", reporter="destination"}[5m])) by (destination_service_name, destination_service_namespace)

# Track specific error codes
sum(rate(istio_requests_total{response_code="503", reporter="destination"}[5m])) by (destination_service_name, destination_service_namespace)

# Analyze error types via response flags
sum(rate(istio_requests_total{response_flags!~"-", reporter="destination"}[5m])) by (response_flags, destination_service_name, destination_service_namespace)
```

#### 4. 飽和

```promql
# Connection count and breaker state (not a utilization percentage).
envoy_cluster_upstream_cx_active
envoy_cluster_circuit_breakers_default_cx_open

# Active and pending requests.
envoy_cluster_upstream_rq_active
envoy_cluster_upstream_rq_pending_active

# Allocated proxy memory in bytes; compare with the container memory limit separately.
envoy_server_memory_allocated
```

### mTLS監視

```promql
# mTLS usage rate
sum(rate(istio_requests_total{
  connection_security_policy="mutual_tls",
  reporter="destination"
}[5m]))
/
sum(rate(istio_requests_total{reporter="destination"}[5m]))
* 100

# Detect non-mTLS traffic
sum(rate(istio_requests_total{
  connection_security_policy="none",
  reporter="destination"
}[5m])) by (source_workload, destination_workload)

# HTTP 401 observed on authenticated mesh traffic; this is not a TLS handshake failure.
sum by (destination_service_name, destination_service_namespace) (
  rate(istio_requests_total{reporter="destination",response_code="401",connection_security_policy="mutual_tls"}[5m])
)
```

### サービスメッシュ健全性ダッシュボード

```promql
# Scrape health, not a complete control-plane health check.
up{job="istiod"}

# Istiod xDS build/send error rate, by type.
sum by (type) (rate(pilot_xds_pushes{type=~".*(builderr|senderr)"}[5m]))

# Configuration convergence time, seconds (not push count).
histogram_quantile(0.95,
  sum by (le) (rate(pilot_proxy_convergence_time_bucket[5m]))
)

# Recently started Envoy process; uptime is elapsed seconds, not a timestamp.
envoy_server_uptime < 300
```

実プロキシ版は`istioctl version`、同期/NACK診断は`istioctl proxy-status`で確認します。プロセスの経過時間は設定鮮度ではなく、Envoy数値版ゲージは版ラベル分布ではありません。mTLS失敗は[mTLSガイド](../security/01-mtls.md)のTLS検証カウンターと証明書を調べます。

## メトリクス最適化 {#metrics-optimization}

### 高カーディナリティ問題の解決

#### 1. 不要ラベルの除去

```yaml
apiVersion: telemetry.istio.io/v1
kind: Telemetry
metadata:
  name: reduce-cardinality
  namespace: istio-system
spec:
  metrics:
  - providers:
    - name: prometheus
    overrides:
    - match:
        metric: ALL_METRICS
      tagOverrides:
        # Remove high cardinality labels
        request_id:
          operation: REMOVE
        user_agent:
          operation: REMOVE
```

#### 2. ラベル値の正規化

```yaml
apiVersion: telemetry.istio.io/v1
kind: Telemetry
metadata:
  name: normalize-labels
  namespace: prod
spec:
  metrics:
  - providers:
    - name: prometheus
    overrides:
    - match:
        metric: REQUEST_COUNT
      tagOverrides:
        # Normalize HTTP methods (GET, POST, PUT, DELETE, OTHER)
        request_method:
          value: 'request.method in ["GET", "POST", "PUT", "DELETE"] ? request.method : "OTHER"'
```

### Envoy統計の選択

`proxyStatsMatcher`は作成するEnvoy統計を選び、要求をサンプリングしません。必要な群だけを含め、必要な既存一致を保持し、bootstrap変更後は選択プロキシをロールアウトします。例は前のクエリに必要な統計を有効にします。

```yaml
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  meshConfig:
    defaultConfig:
      proxyStatsMatcher:
        inclusionRegexps:
        - ".*upstream_rq_timeout.*"
        - ".*upstream_cx_connect_timeout.*"
        - ".*upstream_cx_connect_fail.*"
        - ".*upstream_rq_pending_overflow.*"
        - ".*circuit_breakers.*"
        - ".*outlier_detection.*"
        - ".*upstream_cx_(active|overflow).*"
        - ".*upstream_rq_(active|retry|pending).*"
```

### Prometheus性能調整

デフォルトのスクレイプ間隔は1分です。15s/30sは意図的選択です。既存jobへマージする設定断片です。`metric_relabel_configs`は各job内で、ラベルだけでなくサンプルを破棄します。選択backendのremote-writeエンドポイント、認証/TLS、永続化を設定する必要があります。

```yaml
global:
  scrape_interval: 30s
  evaluation_interval: 30s
remote_write:
- url: http://victoria-metrics:8428/api/v1/write
  queue_config:
    capacity: 10000
    max_shards: 5
    min_shards: 1
    max_samples_per_send: 5000
scrape_configs:
- job_name: envoy-stats
  metrics_path: /stats/prometheus
  kubernetes_sd_configs:
  - role: pod
  relabel_configs:
  - source_labels:
    - __meta_kubernetes_pod_phase
    action: keep
    regex: Running
  - source_labels:
    - __meta_kubernetes_pod_container_name
    - __meta_kubernetes_pod_container_port_name
    action: keep
    regex: istio-proxy;.*-envoy-prom
  - source_labels:
    - __meta_kubernetes_namespace
    target_label: namespace
  - source_labels:
    - __meta_kubernetes_pod_name
    target_label: pod
  metric_relabel_configs:
  - source_labels:
    - __name__
    regex: istio_tcp_.*
    action: drop
```

## トラブルシューティング {#troubleshooting}

exec/curl例はcurl入りプロキシイメージが必要です。なければ`kubectl port-forward pod/<pod-name> 15090:15090`（エージェントは15020）を使い、別ターミナルで照会します。ここでのTelemetryはEnvoy用です。ambient L7ポリシーにはwaypoint接続、ztunnel L4には別収集を使います。

### メトリクスが収集されない場合

#### 1. Envoyメトリクスエンドポイントの確認

```bash
# Check Envoy admin port
kubectl exec -it <pod-name> -c istio-proxy -- curl localhost:15000/stats/prometheus | head -20

# Check metrics filter
istioctl proxy-config bootstrap <pod-name> -o json | jq '.bootstrap.statsConfig'
```

#### 2. Prometheusが対象を検出したか確認

```bash
# Check Targets page in Prometheus UI
kubectl port-forward -n istio-system svc/prometheus 9090:9090

# In browser: http://localhost:9090/targets
```

#### 3. Telemetry API設定の検証

```bash
# Check Telemetry resources
kubectl get telemetry -A

# Check specific Telemetry details
kubectl describe telemetry <name> -n <namespace>

# Check if reflected in Envoy config
istioctl proxy-config listeners <pod-name> -n <namespace> -o json
```

### メトリクスラベルがない場合

```bash
# 1. Check if Envoy generates correct labels
kubectl exec -it <pod-name> -c istio-proxy -- curl localhost:15000/stats/prometheus | grep istio_requests_total | head -1

# 2. Check Prometheus relabeling rules
kubectl get configmap prometheus-config -n istio-system -o yaml

# 3. Check ServiceMonitor/PodMonitor
kubectl get servicemonitor,podmonitor -n istio-system
```

### メトリクスのカーディナリティ急増

別ターミナルでPrometheusをport-forward後、アクティブ系列とTSDB統計を照会します。メトリクス名を数えることは時系列数ではありません。TSDB状態エンドポイントはラベル/値別カーディナリティも報告します。

```bash
curl -fsS http://localhost:9090/api/v1/status/tsdb | jq '.data'
curl -fsSG http://localhost:9090/api/v1/query \
  --data-urlencode 'query=count(istio_requests_total)' | jq '.data.result'
curl -fsSG http://localhost:9090/api/v1/query \
  --data-urlencode 'query=topk(10, count by (__name__) ({__name__=~"istio_.*"}))' | jq '.data.result'
```

### ブレーカーメトリクスが見えない場合

```bash
# 1. Check Envoy cluster statistics
istioctl proxy-config cluster <pod-name> --fqdn <service-fqdn> -o json | \
  jq '.[] | .circuitBreakers'

# 2. Check directly from Envoy admin
kubectl exec -it <pod-name> -c istio-proxy -- \
  curl "localhost:15000/clusters" | grep -A 10 "outbound|80||<service>"

# 3. Verify DestinationRule is correctly applied
istioctl analyze -n <namespace>
```

## 参考資料

- [Istioメトリクス](https://istio.io/latest/docs/reference/config/metrics/)
- [Istio可観測性](https://istio.io/latest/docs/tasks/observability/)
- [Prometheusクエリ例](https://prometheus.io/docs/prometheus/latest/querying/examples/)
- [Envoy統計](https://www.envoyproxy.io/docs/envoy/latest/configuration/upstream/cluster_manager/cluster_stats)
- [OpenTelemetry Collector](https://opentelemetry.io/docs/collector/)
- [Grafana Istioダッシュボード](https://grafana.com/grafana/dashboards/?search=istio)
