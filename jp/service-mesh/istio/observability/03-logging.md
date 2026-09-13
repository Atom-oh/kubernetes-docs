# Istioログ記録

> **対応バージョン**: Istio 1.31
> **最終更新**: September 11, 2026

> **検証範囲**: 演習設定は公式資料とオフライン検証器で確認し、クラスターはデプロイしていません。名前空間、ID、ストレージ、バックエンド、負荷の前提は各例で示し、対象環境で検証する必要があります。

設定したアクセスログは観測要求/接続のメタデータを記録します。Envoy/istiod診断やアプリログとは別で、全メッシュ活動や要求/応答本文全体は取得しません。例はサイドカー用です。ambient L7ログにはwaypoint接続が必要で、ztunnelには別L4ログがあります。

## 目次

1. [ログ記録概要](#logging-overview)
2. [アクセスログ設定](#access-log-configuration)
3. [Telemetry APIによるログカスタマイズ](#log-customization-with-telemetry-api)
4. [ログフィルタリングとサンプリング](#log-filtering-and-sampling)
5. [Envoyログレベル調整](#envoy-log-level-adjustment)
6. [Alloy + Loki統合](#alloy--loki-integration)
7. [Grafanaログダッシュボード](#grafana-log-dashboard)
8. [メトリクス/トレースとのログ統合](#log-integration-with-metricstraces)
9. [性能最適化](#performance-optimization)
10. [トラブルシューティング](#troubleshooting)

## ログ記録概要 {#logging-overview}

### Istioログのレイヤー

Envoy → 構造化標準出力 → Alloy Kubernetesログ収集 → Loki → Grafana。代替としてEnvoy OTLPアクセスログproviderがOpenTelemetry Collectorへ送ります。同じログは重複を避け1経路を選びます。Istiodが選択Telemetry/provider設定を配布します。

### ログの種類

1. **アクセスログ**: 設定したHTTP要求/TCP接続メタデータ
2. **Envoyプロキシログ**: Envoy内部動作ログ
3. **Istiodログ**: コントロールプレーンログ
4. **アプリケーションログ**: アプリ自身のログ

## アクセスログ設定 {#access-log-configuration}

### 1. アクセスログproviderの定義

`istioctl install -f logging-install.yaml`で以下のprovider定義の1つを既存Istio設定にマージします。他のメッシュ設定/providerを保持します。導入入力で、Kubernetes IstioOperatorリソースではありません。下のTelemetryで導入providerを選択します。textとJSONは代替形式です。

#### 基本テキスト形式

```yaml
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
metadata:
  name: logging
spec:
  meshConfig:
    extensionProviders:
    - name: mesh-text
      envoyFileAccessLog:
        path: /dev/stdout
        logFormat:
          text: '[%START_TIME%] "%REQ(:METHOD)% %REQ_WITHOUT_QUERY(:PATH)% %PROTOCOL%" %RESPONSE_CODE%
            %RESPONSE_FLAGS% %DURATION% trace=%TRACE_ID% request=%REQ(X-REQUEST-ID)%'
```

#### JSON形式（Loki例で使用）

```yaml
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
metadata:
  name: logging
spec:
  meshConfig:
    extensionProviders:
    - name: mesh-json
      envoyFileAccessLog:
        path: /dev/stdout
        logFormat:
          labels:
            log_type: access
            start_time: '%START_TIME%'
            method: '%REQ(:METHOD)%'
            path: '%REQ_WITHOUT_QUERY(X-ENVOY-ORIGINAL-PATH?:PATH)%'
            protocol: '%PROTOCOL%'
            response_code: '%RESPONSE_CODE%'
            response_code_details: '%RESPONSE_CODE_DETAILS%'
            response_flags: '%RESPONSE_FLAGS%'
            bytes_received: '%BYTES_RECEIVED%'
            bytes_sent: '%BYTES_SENT%'
            duration: '%DURATION%'
            request_id: '%REQ(X-REQUEST-ID)%'
            trace_id: '%TRACE_ID%'
            authority: '%REQ(:AUTHORITY)%'
            upstream_host: '%UPSTREAM_HOST%'
            upstream_cluster: '%UPSTREAM_CLUSTER%'
            route_name: '%ROUTE_NAME%'
            downstream_tls_version: '%DOWNSTREAM_TLS_VERSION%'
            peer_uri_san: '%DOWNSTREAM_PEER_URI_SAN%'
```

provider形式がJSONフィールドを作り、Telemetryフィルターが記録イベントを選びます。ログの`duration`はミリ秒、CELの`request.duration`は期間値です。`trace_id`はトレースが提供する実アクティブID、`request_id`は別の要求相関値です。クエリ文字列は省略します。追加ヘッダーは記録前に確認します。

ログ更新はプロキシ設定として配信され、全istiod/ワークロード再起動は通常の有効化手順ではありません。実効リスナーとテスト要求を確認します。後述のbootstrapログレベル変更には選択プロキシのロールアウトが必要です。

### 2. Telemetry APIによる細粒度制御

Telemetryは名前空間/ワークロードごとにログを選びます。例は選択肢であり、名前空間ごとにセレクターなしリソースが1つになるようマージします。このガイドはサービス受信ログにSERVERを使い、client/server重複ホップ計上を避けます。Gateway/送信診断は別CLIENTポリシーを使えますが、サービス要求レート計算に混ぜてはいけません。`mesh-text`の場合は`mesh-json`の代わりにそのproviderを選びます。

#### メッシュ全体のJSONアクセスログ有効化

```yaml
apiVersion: telemetry.istio.io/v1
kind: Telemetry
metadata:
  name: mesh-logging
  namespace: istio-system
spec:
  accessLogging:
  - match:
      mode: SERVER
    providers:
    - name: mesh-json
```

#### 名前空間ごとのログ設定

```yaml
apiVersion: telemetry.istio.io/v1
kind: Telemetry
metadata:
  name: production-logging
  namespace: production
spec:
  accessLogging:
  - match:
      mode: SERVER
    providers:
    - name: mesh-json
    # Log only errors and slow requests
    filter:
      expression: |
        response.code >= 400 ||
        request.duration > duration("1s")
```

#### ワークロードごとの詳細ログ

```yaml
apiVersion: telemetry.istio.io/v1
kind: Telemetry
metadata:
  name: payment-service-logging
  namespace: production
spec:
  selector:
    matchLabels:
      app: payment-service
  accessLogging:
  - match:
      mode: SERVER
    providers:
    - name: mesh-json
    # Log all requests + additional custom fields
    filter:
      expression: "true"
```

## Telemetry APIによるログカスタマイズ {#log-customization-with-telemetry-api}

### カスタムログprovider

#### 1. OpenTelemetry経由で送信

同じ標準出力をAlloyで集める代替です。providerを導入して名前空間Telemetryで選びます。

```yaml
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
metadata:
  name: logging
spec:
  meshConfig:
    extensionProviders:
    - name: otel-logging
      envoyOtelAls:
        service: otel-collector.observability.svc.cluster.local
        port: 4317
        logFormat:
          text: '%REQ(:METHOD)% %REQ_WITHOUT_QUERY(:PATH)% %RESPONSE_CODE%'
          labels:
            log_type: access
            start_time: '%START_TIME%'
            method: '%REQ(:METHOD)%'
            path: '%REQ_WITHOUT_QUERY(X-ENVOY-ORIGINAL-PATH?:PATH)%'
            protocol: '%PROTOCOL%'
            response_code: '%RESPONSE_CODE%'
            response_code_details: '%RESPONSE_CODE_DETAILS%'
            response_flags: '%RESPONSE_FLAGS%'
            bytes_received: '%BYTES_RECEIVED%'
            bytes_sent: '%BYTES_SENT%'
            duration: '%DURATION%'
            request_id: '%REQ(X-REQUEST-ID)%'
            trace_id: '%TRACE_ID%'
            authority: '%REQ(:AUTHORITY)%'
            upstream_host: '%UPSTREAM_HOST%'
            upstream_cluster: '%UPSTREAM_CLUSTER%'
            route_name: '%ROUTE_NAME%'
            downstream_tls_version: '%DOWNSTREAM_TLS_VERSION%'
            peer_uri_san: '%DOWNSTREAM_PEER_URI_SAN%'
```

```yaml
apiVersion: telemetry.istio.io/v1
kind: Telemetry
metadata:
  name: otel-access-logging
  namespace: production
spec:
  accessLogging:
  - match:
      mode: SERVER
    providers:
    - name: otel-logging
```

[トレースガイド](02-tracing.md)のcollectorはOTLP receiver、memory limiter、batch processorを定義済みです。このlogs pipeline/exporterをマージして再読み込み/再デプロイします。Loki 3.7.7は`/otlp/v1/logs`でOTLP/HTTPを受け、exporterが`/v1/logs`を追加します。TSDB v13は構造化メタデータ対応です。OTLP属性は標準出力JSON本文でなくメタデータになるため、`| json`例を無条件再利用せずクエリを調整します。

```yaml
exporters:
  otlp_http/loki:
    endpoint: http://loki.observability.svc.cluster.local:3100/otlp
service:
  pipelines:
    logs:
      receivers:
      - otlp
      processors:
      - memory_limiter
      - batch
      exporters:
      - otlp_http/loki
```

#### 2. ファイルログと共有ボリューム

providerのファイルパスだけではボリュームを作成/マウントしません。任意Pod例は注入プロキシに上限付き`emptyDir`をマウントします。アプリイメージを置き換えてください。別readerが同じボリュームをマウントしローテーション/送信を扱う必要があります。ファイルは`kubectl logs`に出ず、`emptyDir`はPodとともに失われます。主収集例は標準出力を使います。

```yaml
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
metadata:
  name: logging
spec:
  meshConfig:
    extensionProviders:
    - name: envoy-file-logger
      envoyFileAccessLog:
        path: /var/log/istio/access.log
        logFormat:
          labels:
            log_type: access
            start_time: '%START_TIME%'
            method: '%REQ(:METHOD)%'
            path: '%REQ_WITHOUT_QUERY(X-ENVOY-ORIGINAL-PATH?:PATH)%'
            protocol: '%PROTOCOL%'
            response_code: '%RESPONSE_CODE%'
            response_code_details: '%RESPONSE_CODE_DETAILS%'
            response_flags: '%RESPONSE_FLAGS%'
            bytes_received: '%BYTES_RECEIVED%'
            bytes_sent: '%BYTES_SENT%'
            duration: '%DURATION%'
            request_id: '%REQ(X-REQUEST-ID)%'
            trace_id: '%TRACE_ID%'
            authority: '%REQ(:AUTHORITY)%'
            upstream_host: '%UPSTREAM_HOST%'
            upstream_cluster: '%UPSTREAM_CLUSTER%'
            route_name: '%ROUTE_NAME%'
            downstream_tls_version: '%DOWNSTREAM_TLS_VERSION%'
            peer_uri_san: '%DOWNSTREAM_PEER_URI_SAN%'
```

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: file-logging-example
  namespace: production
  labels:
    app: file-logging-example
  annotations:
    sidecar.istio.io/inject: 'true'
    sidecar.istio.io/userVolumeMount: '[{"name":"istio-logs","mountPath":"/var/log/istio"}]'
spec:
  securityContext:
    fsGroup: 1337
  containers:
  - name: app
    image: registry.example.com/team/app:REPLACE_WITH_TESTED_TAG
  volumes:
  - name: istio-logs
    emptyDir:
      sizeLimit: 100Mi
---
apiVersion: telemetry.istio.io/v1
kind: Telemetry
metadata:
  name: file-logging
  namespace: production
spec:
  selector:
    matchLabels:
      app: file-logging-example
  accessLogging:
  - match:
      mode: SERVER
    providers:
    - name: envoy-file-logger
```

### ログ形式のカスタマイズ

#### CELによるイベントフィルタリング

```yaml
apiVersion: telemetry.istio.io/v1
kind: Telemetry
metadata:
  name: custom-log-format
  namespace: production
spec:
  accessLogging:
  - match:
      mode: SERVER
    providers:
    - name: mesh-json
    filter:
      expression: "true"
```

**利用可能な変数**:

| 変数 | 説明 | 例 |
|----------|-------------|---------|
| `request.method` | HTTPメソッド | GET, POST |
| `request.path` | 要求パス | /api/v1/users |
| `request.url_path` | URLパス（クエリを除く） | /api/v1/users |
| `request.headers` | 要求ヘッダー | `request.headers['user-agent']` |
| `response.code` | HTTP状態コード | 200, 404, 500 |
| `response.headers` | 応答ヘッダー | `response.headers['content-type']` |
| `response.flags` | 整数ビットマスク | `response.flags != 0` |
| `request.duration` | 要求の期間値 | `duration("1s")` |
| `connection.mtls` | mTLS使用 | true, false |
| `connection.uri_san_peer_certificate` | 存在する場合の下流ピアURI SAN | spiffe://... |
| `connection.uri_san_local_certificate` | 下流ローカル証明書URI SAN | spiffe://... |

## ログフィルタリングとサンプリング {#log-filtering-and-sampling}

### 1. 条件付きログ

#### エラーと遅い要求だけを記録

HTTP属性フィルターはHTTP通信に適用します。TCPログは接続属性か、HTTPフィールド欠損を明示的に扱う式を使います。CELはイベントを選択し、JSON形式は定義しません。

```yaml
apiVersion: telemetry.istio.io/v1
kind: Telemetry
metadata:
  name: error-slow-logging
  namespace: production
spec:
  accessLogging:
  - match:
      mode: SERVER
    providers:
    - name: mesh-json
    filter:
      expression: |
        response.code >= 400 ||
        response.code == 0 ||
        request.duration > duration("1s")
```

#### 特定パスの除外

```yaml
apiVersion: telemetry.istio.io/v1
kind: Telemetry
metadata:
  name: filter-health-checks
  namespace: production
spec:
  accessLogging:
  - match:
      mode: SERVER
    providers:
    - name: mesh-json
    filter:
      expression: |
        !(request.url_path.startsWith('/health') ||
          request.url_path.startsWith('/ready') ||
          request.url_path.startsWith('/live') ||
          request.url_path == '/metrics')
```

#### HTTPメソッドのフィルタリング

```yaml
apiVersion: telemetry.istio.io/v1
kind: Telemetry
metadata:
  name: critical-methods-only
  namespace: production
spec:
  accessLogging:
  - match:
      mode: SERVER
    providers:
    - name: mesh-json
    filter:
      expression: |
        request.method in ['POST', 'PUT', 'DELETE', 'PATCH']
```

#### 非mTLS通信だけ記録（セキュリティ監査）

```yaml
apiVersion: telemetry.istio.io/v1
kind: Telemetry
metadata:
  name: non-mtls-logging
  namespace: production
spec:
  accessLogging:
  - match:
      mode: SERVER
    providers:
    - name: mesh-json
    filter:
      expression: |
        !connection.mtls
```

### 2. Collectorでのサンプリング

Alloyの対応`stage.sampling`を使います。Telemetry CELに文書化された`random()`サンプリング関数はありません。均一10%保持には`loki.process`内へ次のstageを加えます。

```alloy
stage.sampling {
  rate = 0.1
  drop_counter_reason = "uniform_sampling"
}
```

成功かつ1秒未満のアクセスログを1%保持し、エラー/遅い/未分類ログを保持するには、JSON providerの整数フィールドを解析し、一時ラベルで分類、サンプル後に書き込み前にラベルを消します。主process stageをこの代替に置換し、`forward_to`は保持します。

```alloy
stage.json {
  expressions = { log_type = "log_type", response_code = "response_code", duration = "duration" }
}
stage.labels {
  values = { log_type = "log_type", sample_status = "response_code", sample_duration_ms = "duration" }
}
stage.match {
  selector = "{log_type=\"access\", sample_status=~\"[123][0-9]{2}\", sample_duration_ms=~\"[0-9]{1,3}\"}"
  stage.sampling {
    rate = 0.01
    drop_counter_reason = "normal_access_sampled"
  }
}
stage.label_drop {
  values = ["sample_status", "sample_duration_ms"]
}
```

`stage.match`はstreamセレクターと行フィルター対応で、完全なLogQLラベルフィルターパイプラインではありません。一時durationラベルはLokiへ届きません。Collectorサンプリングは取り込み/保存を減らし、プロキシ生成費用は減らしません。保持ログの件数、分位数、エラー率には偏りがあります。全通信SLIには未サンプリングIstioメトリクスを使います。下のダッシュボード/アラートは未サンプリングアクセスログが必要です。

### 3. 名前空間別のログ設定

```yaml
# Production: Log only errors
apiVersion: telemetry.istio.io/v1
kind: Telemetry
metadata:
  name: production-logging
  namespace: production
spec:
  accessLogging:
  - match:
      mode: SERVER
    providers:
    - name: mesh-json
    filter:
      expression: "response.code >= 400"
---
# Staging: Log all requests
apiVersion: telemetry.istio.io/v1
kind: Telemetry
metadata:
  name: staging-logging
  namespace: staging
spec:
  accessLogging:
  - match:
      mode: SERVER
    providers:
    - name: mesh-json
    filter:
      expression: "true"
---
# Development: Disable logging
apiVersion: telemetry.istio.io/v1
kind: Telemetry
metadata:
  name: dev-logging
  namespace: development
spec:
  accessLogging:
  - disabled: true
```

## Envoyログレベル調整 {#envoy-log-level-adjustment}

### ログレベルの動的変更

#### Envoy全体のログレベル

```bash
# Change to Debug level
istioctl proxy-config log <pod-name> -n <namespace> --level debug

# Restore to Info level
istioctl proxy-config log <pod-name> -n <namespace> --level info

# Change to Warning level
istioctl proxy-config log <pod-name> -n <namespace> --level warning
```

#### コンポーネント別ログレベル

```bash
# Debug HTTP connections only
istioctl proxy-config log <pod-name> -n <namespace> --level http:debug

# Debug Router and Connection components only
istioctl proxy-config log <pod-name> -n <namespace> --level router:debug,connection:debug

# Multiple component combinations
istioctl proxy-config log <pod-name> -n <namespace> \
  --level http:debug,router:info,upstream:debug,connection:trace
```

`istioctl proxy-config log <pod-name> -n <namespace>`でその版の対応コンポーネントを列挙します。全ビルドが下の全例を公開するわけではありません。

### 主なEnvoyログコンポーネント

| コンポーネント | 説明 | 用途 |
|-----------|-------------|----------|
| `admin` | 管理インターフェース | 管理APIデバッグ |
| `aws` | AWS統合 | AWSサービス問題 |
| `connection` | TCP接続 | 接続問題のデバッグ |
| `filter` | HTTPフィルター | フィルターチェーン分析 |
| `forward_proxy` | フォワードプロキシ | プロキシ動作追跡 |
| `grpc` | gRPC | gRPC通信問題 |
| `hc` | ヘルスチェック | ヘルスチェック失敗 |
| `http` | HTTP | HTTP要求/応答追跡 |
| `http2` | HTTP/2 | HTTP/2プロトコル問題 |
| `jwt` | JWT認証 | JWT検証 |
| `lua` | Luaスクリプト | Luaフィルターデバッグ |
| `main` | 主ロジック | 一般的Envoy動作 |
| `router` | ルーティング | 経路判断追跡 |
| `runtime` | ランタイム設定 | 動的設定変更 |
| `upstream` | 上流クラスター | backend接続問題 |
| `client` | HTTPクライアント | 送信要求 |
| `pool` | 接続プール | 接続プール管理 |
| `rbac` | RBACフィルター | 権限問題のデバッグ |

### 永続的なログレベル設定

導入valuesをマージし選択プロキシをロールアウトします。一時変更前に既存レベルを確認し、後で戻します。ログレベルはアクセスログを有効にしません。

```yaml
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
metadata:
  name: proxy-log-levels
spec:
  values:
    global:
      proxy:
        logLevel: info
        componentLogLevel: http:debug,router:info,upstream:debug
```

### 特定ワークロードだけにデバッグログを適用

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: my-app
  annotations:
    sidecar.istio.io/componentLogLevel: "http:debug,router:debug"
    sidecar.istio.io/logLevel: "debug"
spec:
  containers:
  - name: app
    image: registry.example.com/team/my-app:REPLACE_WITH_TESTED_TAG
```



## Alloy + Loki統合 {#alloy--loki-integration}

Promtailは**March 2, 2026**にサポート終了しました。新デプロイはAlloyなど対応クライアントを使います。例は旧PromtailファイルtailをAlloy Kubernetes APIログ収集へ置換し、Dockerパス、特権コンテナ、ノードFSマウントは不要です。

### 1. Lokiのインストール（単一バイナリ）

Loki 3.7.7、TSDB v13、ファイルシステム保存の、新規1レプリカ/1テナント例です。Simple Scalableでなく**単一バイナリ**です。先に`observability`を作ります。EKSでは動作するEBS CSIと`gp3`クラスが必要です。他環境は永続StorageClassを使います。FargateはEBSをマウントできないため、適切なEC2ノードか対応外部Lokiサービスを使います。

`auth_enabled: false`ではネットワークアクセスがテナントログへのアクセスになります。エンドポイントを非公開に保ち、本番は対応認証Gateway/TLSを設定します。既存Loki更新では過去schemaを保持します。下の2024開始日は有効で、リリース日ではありません。Compactor保持には永続状態と`delete_request_store`が必要です。

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: loki-config
  namespace: observability
data:
  loki.yaml: |
    auth_enabled: false
    server:
      http_listen_port: 3100
      grpc_listen_port: 9096
    common:
      path_prefix: /loki
      storage:
        filesystem:
          chunks_directory: /loki/chunks
          rules_directory: /loki/rules
      replication_factor: 1
      ring:
        kvstore:
          store: inmemory
    schema_config:
      configs:
      - from: 2024-01-01
        store: tsdb
        object_store: filesystem
        schema: v13
        index:
          prefix: index_
          period: 24h
    limits_config:
      retention_period: 168h
      ingestion_rate_mb: 16
      ingestion_burst_size_mb: 32
      max_query_length: 721h
      max_query_lookback: 721h
      max_streams_per_user: 10000
      max_global_streams_per_user: 0
      reject_old_samples: true
      reject_old_samples_max_age: 168h
    compactor:
      working_directory: /loki/compactor
      compaction_interval: 10m
      retention_enabled: true
      retention_delete_delay: 2h
      retention_delete_worker_count: 150
      delete_request_store: filesystem
    querier:
      max_concurrent: 4
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: loki
  namespace: observability
spec:
  serviceName: loki-headless
  replicas: 1
  selector:
    matchLabels:
      app: loki
  template:
    metadata:
      labels:
        app: loki
        sidecar.istio.io/inject: 'false'
    spec:
      containers:
      - name: loki
        image: grafana/loki:3.7.7
        args:
        - -config.file=/etc/loki/loki.yaml
        ports:
        - containerPort: 3100
          name: http
        - containerPort: 9096
          name: grpc
        volumeMounts:
        - name: config
          mountPath: /etc/loki
        - name: storage
          mountPath: /loki
        resources:
          requests:
            cpu: 500m
            memory: 1Gi
          limits:
            cpu: 2000m
            memory: 4Gi
        readinessProbe:
          httpGet:
            path: /ready
            port: http
          initialDelaySeconds: 10
          periodSeconds: 10
      volumes:
      - name: config
        configMap:
          name: loki-config
      securityContext:
        runAsUser: 10001
        runAsGroup: 10001
        fsGroup: 10001
        runAsNonRoot: true
  volumeClaimTemplates:
  - metadata:
      name: storage
    spec:
      accessModes:
      - ReadWriteOnce
      resources:
        requests:
          storage: 100Gi
      storageClassName: gp3
---
apiVersion: v1
kind: Service
metadata:
  name: loki
  namespace: observability
spec:
  selector:
    app: loki
  ports:
  - name: http
    port: 3100
    targetPort: 3100
  - name: grpc
    port: 9096
    targetPort: 9096
  type: ClusterIP
---
apiVersion: v1
kind: Service
metadata:
  name: loki-headless
  namespace: observability
spec:
  clusterIP: None
  selector:
    app: loki
  ports:
  - name: http
    port: 3100
    targetPort: http
```

### 2. AlloyでPodログを収集

RoleBinding適用前に下のアプリ名前空間を作るか、検出とBindingを既存名前空間に絞ります。AlloyはそれらだけでPodメタデータと`pods/log`を読みます。APIソースはCRI/Docker枠なしの内容を受け取ります。ファイルソースならランタイム解析とノードローカルファイルパスが必要です。

1レプリカ例はinitを除き、サイドカー、istiod、アプリログを集めます。ラベルはnamespace/pod/container/app/versionと限定`log_type`だけです。request ID、trace ID、path、durationはフィールドで、Loki索引ラベルではありません。上のJSON providerは`log_type="access"`を出し、同一コンテナ内のアクセスログと診断を区別します。

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: alloy
  namespace: observability
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: alloy-pod-logs
rules:
- apiGroups:
  - ''
  resources:
  - pods
  verbs:
  - get
  - list
  - watch
- apiGroups:
  - ''
  resources:
  - pods/log
  verbs:
  - get
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: alloy-pod-logs
  namespace: default
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: alloy-pod-logs
subjects:
- kind: ServiceAccount
  name: alloy
  namespace: observability
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: alloy-pod-logs
  namespace: app
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: alloy-pod-logs
subjects:
- kind: ServiceAccount
  name: alloy
  namespace: observability
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: alloy-pod-logs
  namespace: production
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: alloy-pod-logs
subjects:
- kind: ServiceAccount
  name: alloy
  namespace: observability
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: alloy-pod-logs
  namespace: staging
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: alloy-pod-logs
subjects:
- kind: ServiceAccount
  name: alloy
  namespace: observability
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: alloy-pod-logs
  namespace: istio-system
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: alloy-pod-logs
subjects:
- kind: ServiceAccount
  name: alloy
  namespace: observability
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: alloy-config
  namespace: observability
data:
  config.alloy: |
    discovery.kubernetes "pods" {
      role = "pod"
      namespaces {
        names = ["default", "app", "production", "staging", "istio-system"]
      }
    }

    discovery.relabel "logs" {
      targets = discovery.kubernetes.pods.targets
      rule {
        source_labels = ["__meta_kubernetes_pod_phase"]
        regex = "Running"
        action = "keep"
      }
      rule {
        source_labels = ["__meta_kubernetes_pod_container_name"]
        regex = "istio-init"
        action = "drop"
      }
      rule {
        source_labels = ["__meta_kubernetes_namespace"]
        target_label = "namespace"
      }
      rule {
        source_labels = ["__meta_kubernetes_pod_name"]
        target_label = "pod"
      }
      rule {
        source_labels = ["__meta_kubernetes_pod_container_name"]
        target_label = "container"
      }
      rule {
        source_labels = ["__meta_kubernetes_pod_label_app"]
        target_label = "app"
      }
      rule {
        source_labels = ["__meta_kubernetes_pod_label_version"]
        target_label = "version"
      }
    }

    loki.source.kubernetes "pods" {
      targets = discovery.relabel.logs.output
      forward_to = [loki.process.logs.receiver]
    }

    loki.process "logs" {
      stage.json {
        expressions = { log_type = "log_type" }
      }
      stage.labels {
        values = { log_type = "log_type" }
      }
      forward_to = [loki.write.local.receiver]
    }

    loki.write "local" {
      endpoint {
        url = "http://loki.observability.svc.cluster.local:3100/loki/api/v1/push"
        batch_wait = "1s"
        batch_size = "1MiB"
        min_backoff_period = "500ms"
        max_backoff_period = "5m"
        max_backoff_retries = 10
        remote_timeout = "10s"
      }
    }
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: alloy
  namespace: observability
spec:
  replicas: 1
  selector:
    matchLabels:
      app: alloy
  template:
    metadata:
      labels:
        app: alloy
        sidecar.istio.io/inject: 'false'
    spec:
      serviceAccountName: alloy
      containers:
      - name: alloy
        image: grafana/alloy:v1.19.2
        args:
        - run
        - --server.http.listen-addr=0.0.0.0:12345
        - --storage.path=/var/lib/alloy
        - /etc/alloy/config.alloy
        ports:
        - containerPort: 12345
          name: http-metrics
        volumeMounts:
        - name: config
          mountPath: /etc/alloy
          readOnly: true
        - name: state
          mountPath: /var/lib/alloy
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 500m
            memory: 512Mi
      volumes:
      - name: config
        configMap:
          name: alloy-config
      - name: state
        emptyDir:
          sizeLimit: 256Mi
```

API収集はFargateアプリPodのDaemonSet制限も避けますが、ノードログは収集しません。Kubernetes API/kubelet負荷が増えるため、大規模環境はノードローカル収集か対象所有権を調整したAlloy clusteringを評価します。全Podをtailする同一レプリカを単純追加しないでください。例の`emptyDir`状態と有限再試行は再起動/停止時の無損失配信を保証しません。本番は永続バッファ/WALと復旧テストを設定します。

### 3. LogQLクエリ例

標準出力JSON providerと未サンプリングSERVERアクセスログを使います。コンテナセレクターだけではプロキシ診断も含むため、`log_type="access"`で選択します。TCP接続ログはHTTP要求でないので、HTTP統計は空/`-`メソッドも除外します。数値比較は数値を使い、`__error__=""`で解析/変換失敗を集約前に除外します。

#### 基本クエリ

```logql
{namespace="production"}

{app="payment-service"}

{container="istio-proxy",log_type="access"}

{namespace="production"} |~ "(?i)error"

{container="istio-proxy",log_type="access"} | json | method!="" | method!="-" | response_code >= 500 | response_code < 600 | __error__=""
```

#### 高度なフィルタリング

```logql
{container="istio-proxy",log_type="access"} | json | method!="" | method!="-" | method="POST" | __error__=""

{container="istio-proxy",log_type="access"} | json | method!="" | method!="-" | duration > 1000 | __error__=""

{container="istio-proxy",log_type="access"} | json | method!="" | method!="-" | response_flags=~".*UO.*" | __error__=""

{container="istio-proxy",log_type="access"} | json | method!="" | method!="-" | response_flags=~".*URX.*" | __error__=""

{container="istio-proxy",log_type="access"} | json | method!="" | method!="-" | downstream_tls_version=~"(-)?" | __error__=""

{container="istio-proxy",log_type="access"} | json | method!="" | method!="-" | path=~"/api/v1/.*" | __error__=""
```

`UO`は上流超過、`URX`は再試行/接続試行の枯渇です。`downstream_tls_version`は記録接続の平文/TLSを識別し、`peer_uri_san`は利用可能なら認証済みピア情報を提供します。どちらも普遍的TLSハンドシェイク失敗カウンターではなく、HTTPアクセス記録の前に失敗することもあります。旧`connection_security_policy`クエリはこのログにないメトリクスラベルを参照していました。

#### 集約と統計

```logql
sum by (namespace, app) (rate({container="istio-proxy",log_type="access"} | json | method!="" | method!="-" | __error__="" [5m]))

sum by (response_code) (count_over_time({container="istio-proxy",log_type="access"} | json | method!="" | method!="-" | __error__="" [5m]))

quantile_over_time(0.95, {container="istio-proxy",log_type="access"} | json | method!="" | method!="-" | unwrap duration | __error__="" [5m]) by (namespace, app)

sum by (namespace, app) (rate({container="istio-proxy",log_type="access"} | json | method!="" | method!="-" | response_code >= 500 | response_code < 600 | __error__="" [5m])) / sum by (namespace, app) (rate({container="istio-proxy",log_type="access"} | json | method!="" | method!="-" | __error__="" [5m]))

avg_over_time({container="istio-proxy",log_type="access"} | json | method!="" | method!="-" | unwrap duration | __error__="" [5m]) by (namespace, app)
```

保持したログエントリを記述します。選択ログ、サンプリング、配信喪失、異なる呼び出し経路、Gatewayログが結果に影響します。サービス全体SLOにはメトリクス章の標準メトリクスを使います。

## Grafanaログダッシュボード {#grafana-log-dashboard}

### 1. Lokiデータソース追加

ファイルをGrafanaの`provisioning/datasources`へマウントするか、チャートの対応設定を使います。ConfigMapだけでは自動消費されません。`tempo` UIDは既存Tempoを参照する必要があります。相関にはJSON providerの`trace_id`を使い、要求UUIDはtrace IDではありません。空IDではリンクは作られません。

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: grafana-datasources
  namespace: observability
data:
  loki.yaml: |
    apiVersion: 1
    datasources:
    - name: Loki
      uid: loki
      type: loki
      access: proxy
      url: http://loki.observability.svc.cluster.local:3100
      jsonData:
        maxLines: 1000
        derivedFields:
        - datasourceUid: tempo
          matcherRegex: '"trace_id"\s*:\s*"([0-9a-fA-F]{32})"'
          name: TraceID
          url: $${__value.raw}
          urlDisplayLabel: View trace
```

### 2. Istioアクセスログダッシュボード

#### ダッシュボードJSON

以下のオブジェクトをインポートするかdashboard provider経由でマウントします。HTTP APIラッパーでなくファイルです。UID `loki`と`prometheus`が必要で、ログ`app`ラベルとcanonical-service値を合わせます。ヒートマップは実Prometheusヒストグラムバケットを使い、生ログdurationには`le`バケットラベルがありません。

```json
{
  "title": "Istio Access Logs",
  "tags": [
    "istio",
    "logs"
  ],
  "timezone": "browser",
  "panels": [
    {
      "title": "Logged HTTP Request Rate",
      "type": "timeseries",
      "targets": [
        {
          "expr": "sum by (namespace, app) (rate({container=\"istio-proxy\",log_type=\"access\",namespace=\"$namespace\",app=\"$service\"} | json | method!=\"\" | method!=\"-\" | __error__=\"\" [5m]))",
          "refId": "A",
          "datasource": {
            "type": "loki",
            "uid": "loki"
          }
        }
      ],
      "gridPos": {
        "h": 8,
        "w": 12,
        "x": 0,
        "y": 0
      },
      "id": 1,
      "datasource": {
        "type": "loki",
        "uid": "loki"
      }
    },
    {
      "title": "Response Code Distribution",
      "type": "piechart",
      "targets": [
        {
          "expr": "sum by (response_code) (count_over_time({container=\"istio-proxy\",log_type=\"access\",namespace=\"$namespace\",app=\"$service\"} | json | method!=\"\" | method!=\"-\" | __error__=\"\" [5m]))",
          "refId": "A",
          "datasource": {
            "type": "loki",
            "uid": "loki"
          }
        }
      ],
      "gridPos": {
        "h": 8,
        "w": 12,
        "x": 12,
        "y": 0
      },
      "id": 2,
      "datasource": {
        "type": "loki",
        "uid": "loki"
      }
    },
    {
      "title": "P50/P95/P99 Latency",
      "type": "timeseries",
      "targets": [
        {
          "expr": "quantile_over_time(0.5, {container=\"istio-proxy\",log_type=\"access\",namespace=\"$namespace\",app=\"$service\"} | json | method!=\"\" | method!=\"-\" | unwrap duration | __error__=\"\" [5m]) by (namespace, app)",
          "legendFormat": "P50",
          "refId": "A",
          "datasource": {
            "type": "loki",
            "uid": "loki"
          }
        },
        {
          "expr": "quantile_over_time(0.95, {container=\"istio-proxy\",log_type=\"access\",namespace=\"$namespace\",app=\"$service\"} | json | method!=\"\" | method!=\"-\" | unwrap duration | __error__=\"\" [5m]) by (namespace, app)",
          "legendFormat": "P95",
          "refId": "B",
          "datasource": {
            "type": "loki",
            "uid": "loki"
          }
        },
        {
          "expr": "quantile_over_time(0.99, {container=\"istio-proxy\",log_type=\"access\",namespace=\"$namespace\",app=\"$service\"} | json | method!=\"\" | method!=\"-\" | unwrap duration | __error__=\"\" [5m]) by (namespace, app)",
          "legendFormat": "P99",
          "refId": "C",
          "datasource": {
            "type": "loki",
            "uid": "loki"
          }
        }
      ],
      "gridPos": {
        "h": 8,
        "w": 24,
        "x": 0,
        "y": 8
      },
      "id": 3,
      "datasource": {
        "type": "loki",
        "uid": "loki"
      }
    },
    {
      "title": "HTTP Error Fraction in Retained Logs",
      "type": "stat",
      "targets": [
        {
          "expr": "sum by (namespace, app) (rate({container=\"istio-proxy\",log_type=\"access\",namespace=\"$namespace\",app=\"$service\"} | json | method!=\"\" | method!=\"-\" | response_code >= 500 | response_code < 600 | __error__=\"\" [5m])) / sum by (namespace, app) (rate({container=\"istio-proxy\",log_type=\"access\",namespace=\"$namespace\",app=\"$service\"} | json | method!=\"\" | method!=\"-\" | __error__=\"\" [5m]))",
          "refId": "A",
          "datasource": {
            "type": "loki",
            "uid": "loki"
          }
        }
      ],
      "gridPos": {
        "h": 4,
        "w": 6,
        "x": 0,
        "y": 16
      },
      "id": 4,
      "datasource": {
        "type": "loki",
        "uid": "loki"
      }
    },
    {
      "title": "Top 10 Routes by Average Logged Duration",
      "type": "table",
      "targets": [
        {
          "expr": "topk(10, avg_over_time({container=\"istio-proxy\",log_type=\"access\",namespace=\"$namespace\",app=\"$service\"} | json | method!=\"\" | method!=\"-\" | unwrap duration | __error__=\"\" [5m]) by (namespace, app, route_name, method))",
          "refId": "A",
          "datasource": {
            "type": "loki",
            "uid": "loki"
          }
        }
      ],
      "gridPos": {
        "h": 8,
        "w": 12,
        "x": 0,
        "y": 20
      },
      "id": 5,
      "datasource": {
        "type": "loki",
        "uid": "loki"
      }
    },
    {
      "title": "Error Logs",
      "type": "logs",
      "targets": [
        {
          "expr": "{container=\"istio-proxy\",log_type=\"access\",namespace=\"$namespace\",app=\"$service\"} | json | method!=\"\" | method!=\"-\" | response_code >= 400 | __error__=\"\"",
          "refId": "A",
          "datasource": {
            "type": "loki",
            "uid": "loki"
          }
        }
      ],
      "gridPos": {
        "h": 8,
        "w": 12,
        "x": 12,
        "y": 20
      },
      "id": 6,
      "datasource": {
        "type": "loki",
        "uid": "loki"
      }
    },
    {
      "title": "Upstream Overflow Events",
      "type": "logs",
      "targets": [
        {
          "expr": "{container=\"istio-proxy\",log_type=\"access\",namespace=\"$namespace\",app=\"$service\"} | json | method!=\"\" | method!=\"-\" | response_flags=~\".*UO.*\" | __error__=\"\"",
          "refId": "A",
          "datasource": {
            "type": "loki",
            "uid": "loki"
          }
        }
      ],
      "gridPos": {
        "h": 8,
        "w": 24,
        "x": 0,
        "y": 28
      },
      "id": 7,
      "datasource": {
        "type": "loki",
        "uid": "loki"
      }
    },
    {
      "title": "HTTP Duration Histogram (Prometheus)",
      "type": "heatmap",
      "targets": [
        {
          "expr": "sum by (le) (rate(istio_request_duration_milliseconds_bucket{reporter=\"destination\",destination_workload_namespace=\"$namespace\",destination_canonical_service=\"$service\"}[5m]))",
          "format": "heatmap",
          "refId": "A",
          "datasource": {
            "type": "prometheus",
            "uid": "prometheus"
          }
        }
      ],
      "gridPos": {
        "h": 8,
        "w": 24,
        "x": 0,
        "y": 36
      },
      "id": 8,
      "datasource": {
        "type": "prometheus",
        "uid": "prometheus"
      }
    }
  ],
  "templating": {
    "list": [
      {
        "name": "namespace",
        "type": "query",
        "query": "label_values({container=\"istio-proxy\"}, namespace)",
        "datasource": {
          "type": "loki",
          "uid": "loki"
        }
      },
      {
        "name": "service",
        "type": "query",
        "query": "label_values({container=\"istio-proxy\", namespace=\"$namespace\"}, app)",
        "datasource": {
          "type": "loki",
          "uid": "loki"
        }
      }
    ]
  },
  "uid": "istio-access-logs"
}
```

### 3. Loki Rulerアラート

Prometheus型の`groups`/`alert`/`expr` YAMLはLoki ruler設定です。Grafana管理アラートは文書化されたUID、condition、query-data形式を使うため、そちらではGrafanaからエクスポートします。Loki評価ではConfigMapを作り、ruler設定を`loki.yaml`へ、ボリューム断片を既存StatefulSetへマージし、設定/ストレージマウントを保持します。設定先のAlertmanagerは存在する必要があります。

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: loki-rules
  namespace: observability
data:
  istio-logging-alerts.yaml: |
    groups:
    - name: istio-logging-alerts
      interval: 1m
      rules:
      - alert: HighHTTPErrorFractionInLogs
        expr: sum by (namespace, app) (rate({container="istio-proxy",log_type="access"} | json | method!=""
          | method!="-" | response_code >= 500 | response_code < 600 | __error__="" [5m])) / sum by (namespace,
          app) (rate({container="istio-proxy",log_type="access"} | json | method!="" | method!="-" | __error__=""
          [5m])) > 0.05
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: Retained HTTP logs show more than 5% server errors
      - alert: CircuitBreakerOverflow
        expr: sum by (namespace, app) (count_over_time({container="istio-proxy",log_type="access"} | json
          | method!="" | method!="-" | response_flags=~".*UO.*" | __error__="" [1m])) > 10
        for: 1m
        labels:
          severity: warning
        annotations:
          summary: Upstream overflow events in access logs
      - alert: SlowLoggedRequests
        expr: quantile_over_time(0.95, {container="istio-proxy",log_type="access"} | json | method!="" | method!="-"
          | unwrap duration | __error__="" [5m]) by (namespace, app) > 2000
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: P95 of logged HTTP durations exceeds 2000ms
      - alert: PlaintextHTTPObserved
        expr: sum by (namespace, app) (count_over_time({container="istio-proxy",log_type="access"} | json
          | method!="" | method!="-" | downstream_tls_version=~"(-)?" | __error__="" [5m])) > 0
        for: 1m
        labels:
          severity: warning
        annotations:
          summary: HTTP access logs show a plaintext downstream connection
```

```yaml
ruler:
  storage:
    type: local
    local:
      directory: /etc/loki/rules
  rule_path: /loki/ruler-scratch
  alertmanager_url: http://alertmanager.observability.svc.cluster.local:9093
  ring:
    kvstore:
      store: inmemory
  enable_api: true
```

```yaml
spec:
  template:
    spec:
      containers:
      - name: loki
        volumeMounts:
        - name: loki-rules
          mountPath: /etc/loki/rules
          readOnly: true
      volumes:
      - name: loki-rules
        configMap:
          name: loki-rules
          items:
          - key: istio-logging-alerts.yaml
            path: fake/istio-logging-alerts.yaml
```

単一テナントLokiのIDは`fake`なので、ローカルルールを`fake/`下に置きます。ローカルルールストレージはruler APIでは読み取り専用です。アラートには全アクセスログストリームが必要で、エラーのみ/サンプル済みでは偏りのない比率や遅延分位数になりません。no-dataと配信失敗監視は別計画です。



## メトリクス/トレースとのログ統合 {#log-integration-with-metricstraces}

### 1. ログからトレースへ移動

上のLokiデータソースの`trace_id`派生フィールドを使います。トレースが有効でIDがあり、同じトレースをTempoが保持する時だけリンクします。要求の`x-request-id`はW3C trace IDと交換できません。サンプリングや保持により、有効ログがあってもトレースを取得できない場合があります。

### 2. メトリクス相関

Prometheusエグゼンプラーは実trace-IDラベルがあると**メトリクスからトレース**へリンクし、ログへのリンクは作りません。`exemplarTraceIdDestinations.name`を架空`TraceID`でなく、観測ラベル（通常`trace_id`）へ合わせます。メトリクス→ログには一致namespace/serviceラベルのGrafana correlations/data linksを設定します。データソース設定だけでエグゼンプラーは生まれません。

### 3. 統合ダッシュボードクエリ

全通信要求レートにはPrometheus、選択ワークロードのアクセス記録にはLokiパネルを使います。変数を一貫させます。Istioは普遍的`app`ラベルでなく`destination_canonical_service`/workload namespaceを使います。

```promql
sum(rate(istio_requests_total{reporter="destination",destination_workload_namespace="$namespace",destination_canonical_service="$service"}[5m]))
```

```logql
{container="istio-proxy",log_type="access",namespace="$namespace",app="$service"} | json | __error__=""
```

未エンコードJSONをURLへ埋め込まず、Grafana生成Exploreリンクかcorrelationsを使います。Lokiのappとメトリクスのserviceが同じワークロードを識別することを確認します。

## 性能最適化 {#performance-optimization}

### 1. ログ量削減

フィルター/Alloyサンプリング選択前に、ヘルスチェック、エラー、通常通信の実割合を測ります。普遍的50–90%や30–50%削減はありません。プロキシ側フィルターは生成ログ、collector側サンプルは下流取り込み/保存を減らします。全通信メトリクスと重要監査イベントはサンプルログから独立させます。

HTTPヘルスパス除外は既存Telemetryフィルターへマージできます。TCPログではHTTPフィールド欠損を考慮します。

```yaml
filter:
  expression: '!has(request.url_path) || !(request.url_path.startsWith("/health") || request.url_path.startsWith("/ready")
    || request.url_path.startsWith("/live") || request.url_path == "/metrics" || request.url_path == "/favicon.ico")'
```

### 2. Loki性能調整

```yaml
limits_config:
  # Ingestion limits; these do not directly set chunk size
  ingestion_rate_strategy: global
  ingestion_rate_mb: 32  # Example, size for the workload
  ingestion_burst_size_mb: 64  # Example burst budget

  # Query performance
  max_query_parallelism: 32
  max_query_series: 10000
  max_query_lookback: 720h

  # Stream limits
  max_streams_per_user: 10000
  max_global_streams_per_user: 0

  # Label cardinality limits
  max_label_names_per_series: 30
  max_label_value_length: 2048
```

### 3. Alloyバッチ処理と再試行

```alloy
// loki.write endpoint fragment: merge with the endpoint's existing URL.
batch_wait = "1s"
batch_size = "1MiB"
min_backoff_period = "500ms"
max_backoff_period = "5m"
max_backoff_retries = 10
remote_timeout = "10s"
```

## トラブルシューティング {#troubleshooting}

### アクセスログが見えない

実効動的リスナー、選択provider、既知テスト要求を確認します。内部プロキシログはアクセスログ設定を証明せず、最初のコンテナログ行がJSONとは限りません。

```bash
kubectl get telemetry -A
istioctl proxy-config listeners <pod-name> -n <namespace> -o json | \
  jq '.. | objects | select(has("accessLog")) | .accessLog'
kubectl logs <pod-name> -n <namespace> -c istio-proxy --tail=100 | \
  jq -R 'fromjson? | select(.log_type == "access")'
```

### Collector/ストレージへの配信失敗

Alloyの対象検出、RoleBinding、Podログ権限を確認します。APIソースにホストログファイルは不要です。自身のログ/メトリクスで破棄/再試行バッチを調べ、range-queryエンドポイントでLokiログを照会します。port-forwardは別ターミナルで実行します。

```bash
kubectl logs -n observability deployment/alloy --tail=100
kubectl port-forward -n observability deployment/alloy 12345:12345
# Another terminal:
curl -fsS http://localhost:12345/metrics | rg 'loki_(write|process)_'
# Separate terminal:
kubectl port-forward -n observability svc/loki 3100:3100
```

```bash
curl -fsSG http://localhost:3100/loki/api/v1/query_range \
  --data-urlencode 'query={container="istio-proxy",log_type="access"}' \
  --data-urlencode 'limit=20' | jq '.data.result'
```

### ログ量とカーディナリティ

`kubectl top`はリソース消費で、ログ量ではありません。保持ログからバイトレートを数え、限定時間の実ストリーム集合を調べます。`/labels`はラベル名数でストリーム数ではありません。大規模環境で無制限・高カーディナリティ`/series`照会を避けます。

```logql
topk(10, sum by (namespace, app) (bytes_rate({container="istio-proxy"} [5m])))

topk(10, sum by (namespace, app) (count_over_time({container="istio-proxy"} [1h])))
```

数値フィルター前に解析フィールドを確認します。`unwrap`後、集約前に`__error__`を除外します。サンプリング/フィルター/喪失したエントリは保持ログから再構成できません。

## 参考資料

- [Istioアクセスログ](https://istio.io/latest/docs/tasks/observability/logs/access-log/)
- [Telemetry API](https://istio.io/latest/docs/reference/config/telemetry/)
- [Envoyアクセスログ](https://www.envoyproxy.io/docs/envoy/latest/configuration/observability/access_log/usage)
- [Grafana Lokiドキュメント](https://grafana.com/docs/loki/latest/)
- [Alloy Kubernetesログソース](https://grafana.com/docs/alloy/latest/reference/components/loki/loki.source.kubernetes/)
- [Promtailライフサイクル](https://grafana.com/docs/loki/latest/send-data/promtail/)
- [LogQLクエリ言語](https://grafana.com/docs/loki/latest/query/)
- [CEL式言語](https://github.com/google/cel-spec)
