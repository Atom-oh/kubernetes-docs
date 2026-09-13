# 可観測性スタックの設定と運用

> **最終更新**: September 11, 2026: Loki 3.7.7、Tempo 3.0.3、Alloy 1.19.2、
> OpenTelemetry Collector Contrib 0.160.0、kube-prometheus-stack 90.1.1。

この章では収集、ストレージ、権限、保持期間、シグナル間の移動を設定します。
前章の[完全なGo/Python計装とJava JSONログの例](./08-observability-analysis.md)を使用してください。
Grafanaをインストールするだけでは3つのシグナルは関連付けられません。

## 範囲と前提条件

| シグナル | 収集経路 | 保存とクエリ |
|---|---|---|
| ログ | アプリケーションJSON標準出力 → Alloy KubernetesログAPIソース | Loki → Grafana |
| トレース | アプリケーションOTLP → Collector → Tempo | Tempo → Grafana |
| メトリクス | Prometheusスクレイプ。任意でTempo生成メトリクスのremote write | Prometheus。任意でAMP |

例は`observability`名前空間を使います。その名前空間、Prometheus Operator CRD、
動作する`gp3` StorageClassを準備します。EKS Auto Modeと通常のEBS CSIドライバーは
異なるStorageClassプロビジョナーを使うため、クラス名の一致だけでは互換性は成立しません。
S3バケットとIRSAロールは別の前提条件です。アカウント、ロール、バケット、ワークスペースの
プレースホルダーを置き換えてください。用途別のバケットを使い、パブリックアクセスをブロックします。
Loki/Tempoロールは必要なバケット一覧とオブジェクトの読み取り/書き込み/削除に限定し、
SSE-KMSを使う場合は選択したKMSキー権限も含めます。

これらの設定は出発点です。内部の未認証HTTP、Kafka接続、リソースサイズ、保持期間は
普遍的な本番デフォルトではありません。環境に応じたネットワークアクセス、TLS/認証、容量、復旧を
検証してください。`ClusterIP`は認証を提供しません。

チャートのバージョンはアプリケーションのバージョンと異なります。LokiとTempoの例は現在の
`grafana-community`リポジトリを使います。旧`grafana/tempo`モノリシックチャートに
分散用valuesを与えても、分散デプロイにはなりません。

```bash
helm repo add grafana-community https://grafana-community.github.io/helm-charts
helm repo add grafana https://grafana.github.io/helm-charts
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
```

## Loki: デプロイモードとS3ストレージ

Lokiはストリームラベルにインデックスを付け、ログ内容をチャンクに保存します。内容検索は選択した
ストリームからデータを読むため、ラベル選択、時間範囲、チャンク/インデックスキャッシュがクエリコストに影響します。
圧縮率や固定の日次データ量の境界値には、ワークロード固有の測定が必要です。

| モード | 目的と制約 |
|---|---|
| Monolithic | コンポーネントを1プロセスで実行。HAには共有オブジェクトストレージ、レプリケーション、ルーティングが必要 |
| SimpleScalable | read/write/backendターゲットを分離。非推奨でLoki 4.0で削除予定 |
| Distributed | 独立コンポーネント。ネットワーク、リング、クエリ経路、ストレージの追加運用が必要 |

例はDistributedモードでingester 3つとcompactor 1つを使います。
`zoneAwareReplication: false`なので3レプリカだけではAZ分離は保証されません。
AZ/ノード配置、クォーラム、PDB、ローリング更新を併せて検証してください。初期検証の規模を減らすため
キャッシュは無効です。本番負荷テストでキャッシュ容量を選びます。

スキーマ日付は新規ストア用です。既存インストールの過去スキーマエントリを置き換えないでください。
保持したまま、将来日付のエントリ追加手順に従います。
`auth_enabled: false`はこの内部例で単一の`fake`テナントを選びます。
マルチテナント有効化ではユーザー認証は追加されません。認証プロキシがテナントヘッダーを検証・設定する必要があります。

```yaml
# loki-values.yaml
deploymentMode: Distributed
loki:
  image:
    tag: 3.7.7
  auth_enabled: false
  commonConfig:
    replication_factor: 3
  schemaConfig:
    configs:
    - from: '2026-09-01'
      store: tsdb
      object_store: s3
      schema: v13
      index:
        prefix: loki_index_
        period: 24h
  storage:
    type: s3
    bucketNames:
      chunks: REPLACE_WITH_UNIQUE_LOKI_CHUNKS_BUCKET
      ruler: REPLACE_WITH_UNIQUE_LOKI_RULER_BUCKET
    s3:
      region: ap-northeast-2
  ingester:
    chunk_encoding: snappy
  compactor:
    retention_enabled: true
    delete_request_store: s3
    retention_delete_delay: 2h
  limits_config:
    retention_period: 720h
    allow_structured_metadata: true
  analytics:
    reporting_enabled: false
serviceAccount:
  create: true
  name: loki
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/docs-loki-s3
singleBinary:
  replicas: 0
read:
  replicas: 0
write:
  replicas: 0
backend:
  replicas: 0
ingester:
  replicas: 3
  zoneAwareReplication:
    enabled: false
  persistence:
    enabled: true
    claims:
    - name: data
      accessModes: &id001
      - ReadWriteOnce
      size: 20Gi
      storageClass: gp3
distributor:
  replicas: 2
querier:
  replicas: 2
queryFrontend:
  replicas: 2
queryScheduler:
  replicas: 2
indexGateway:
  replicas: 2
compactor:
  replicas: 1
  persistence:
    enabled: true
    claims:
    - name: data
      accessModes: *id001
      size: 20Gi
      storageClass: gp3
gateway:
  enabled: true
  replicas: 2
chunksCache:
  enabled: false
resultsCache:
  enabled: false
sidecar:
  rules:
    enabled: false
```

```bash
helm template loki grafana-community/loki --version 18.12.2   --namespace observability -f loki-values.yaml > loki-rendered.yaml
helm upgrade --install loki grafana-community/loki --version 18.12.2   --namespace observability -f loki-values.yaml
```

チャート18.12.2では`persistence.claims`でingesterとcompactorのPVCを設定します。
リスト置換時は`accessModes`を含めます。Helm終了状態だけでなく、レンダリングされた
`volumeClaimTemplates`と実際のPVCバインドを確認します。ゲートウェイServiceのポートは**80**、
LokiプロセスのHTTPポートは**3100**です。

### 保持期間

24時間のインデックス期間を持つTSDB v13スキーマ、`compactor.retention_enabled`、
`delete_request_store`、`limits_config.retention_period`を一緒に設定します。削除は非同期で、
`retention_delete_delay`に従います。再起動をまたいでcompactorの削除マーカーと状態を保持してください。
保持設定の変更が既存データを遡及的に再編成すると想定しないでください。

テナントごとのオーバーライドはチャートの`loki.runtimeConfig.overrides`に置きます。
単一テナント例は`fake`を使います。次の断片はデフォルト30日を7日に上書きします。
保持要件を確認してから適用してください。

```yaml
loki:
  runtimeConfig:
    overrides:
      fake:
        retention_period: 168h
```

バケット全体のオブジェクトライフサイクル有効期限は、インデックス、削除要求、ruler設定を
壊す場合があります。ライフサイクルの安全策が必要ならチャンクプレフィックスに限定し、
保持期間と削除遅延の合計より長い有効期限を設定します。バージョニング/バックアップ費用と削除要件は
別々に評価します。バージョニング有効化は復旧テストではありません。

## Alloyのログ収集とラベル

Promtailは2026-03-02にEOLとなりました。新しい例はAlloyを使います。
この設定は[前章](./08-observability-analysis.md)の`observability`内の`app=correlation-api` Podを、
KubernetesログAPI経由で読み取ります。
ノードファイルのtailは行わず、hostPathマウントや`stage.cri`は不要です。

`Recreate`の単一Deploymentレプリカは、定常時とロールアウト時の重複を避けます。
HAではなく、更新で収集が中断する場合があります。拡張するにはAlloyクラスタリングとソースの
クラスタリング対応を一緒に設定するか、ノードごとに対象を限定します。各Podが全アプリケーションPodを
検出するDaemonSetでは収集が重複します。

```yaml
# alloy-rbac.yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: alloy-logs
  namespace: observability
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: alloy-logs
  namespace: observability
rules:
  - apiGroups: [""]
    resources: [pods]
    verbs: [get, list, watch]
  - apiGroups: [""]
    resources: [pods/log]
    verbs: [get]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: alloy-logs
  namespace: observability
subjects:
  - kind: ServiceAccount
    name: alloy-logs
    namespace: observability
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: alloy-logs
```

```alloy
// logs.alloy
// Kubernetes API log source: configure its ServiceAccount permissions first.
discovery.kubernetes "application" {
  role = "pod"
  namespaces {
    names = ["observability"]
  }
  selectors {
    role  = "pod"
    label = "app=correlation-api"
  }
}

discovery.relabel "application_logs" {
  targets = discovery.kubernetes.application.targets
  rule {
    source_labels = ["__meta_kubernetes_namespace"]
    target_label  = "namespace"
  }
  rule {
    source_labels = ["__meta_kubernetes_pod_label_app"]
    target_label  = "service_name"
  }
  rule {
    source_labels = ["__meta_kubernetes_pod_container_name"]
    target_label  = "container"
  }
}

loki.source.kubernetes "application" {
  targets    = discovery.relabel.application_logs.output
  forward_to = [loki.process.application.receiver]
}

loki.process "application" {
  stage.json {
    expressions = {
      level = "level",
    }
  }
  stage.labels {
    values = {
      level = "",
    }
  }
  // Keep the complete JSON body, including trace_id/span_id. They are not
  // indexed stream labels and remain available for parsing/correlation.
  forward_to = [loki.write.backend.receiver]
}

loki.write "backend" {
  endpoint {
    url = "http://loki-gateway.observability.svc:80/loki/api/v1/push"
  }
}
```

これらのvaluesを`alloy-values.yaml`として保存し、前のファイルを`--set-file`で注入します。
YAML文字列内でAlloy設定を重複させずに済みます。

```yaml
controller:
  type: deployment
  replicas: 1
  updateStrategy:
    type: Recreate
alloy:
  enableReporting: false
  configMap:
    content: ''
  resources:
    requests:
      cpu: 100m
      memory: 128Mi
    limits:
      memory: 512Mi
rbac:
  create: false
serviceAccount:
  create: false
  name: alloy-logs
crds:
  create: false
```

```bash
kubectl apply -f alloy-rbac.yaml
helm upgrade --install alloy grafana/alloy --version 1.12.1   --namespace observability -f alloy-values.yaml   --set-file alloy.configMap.content=logs.alloy
```

`namespace`、`service_name`、`container`など値の種類が限定されたラベルを優先します。
`trace_id`と`request_id`はJSON内容または構造化メタデータに残します。
Pod名は一律禁止ではありませんが、寿命と変更頻度がストリーム数に影響します。
ラベル組み合わせの積が重要で、固定ラベル数は安全保証ではありません。
この例は完全なJSON行を保持し、追加で`level`にインデックスを付けます。
無制限に増えるlevel値を正規化し、アプリケーションまたは収集層で個人データを削除します。

### LogQLとログアラート

数値集約前にJSON解析エラーと無効な数値フィールドを除外します。
以下のレイテンシーフィールドはミリ秒です。
`rate`は毎秒ログ行数、毎秒バイト数には`bytes_rate`を使います。

```logql
{service_name="correlation-api"} | json | __error__="" | level="ERROR"
```

```logql
sum(rate({service_name="correlation-api"}[5m]))
```

```logql
sum(bytes_rate({service_name="correlation-api"}[5m]))
```

```logql
avg_over_time({service_name="correlation-api"} | json | latency_ms >= 0 | __error__="" | unwrap latency_ms | __error__="" [5m])
```

```logql
quantile_over_time(0.95, {service_name="correlation-api"} | json | latency_ms >= 0 | __error__="" | unwrap latency_ms | __error__="" [5m])
```

Loki RulerはLogQLルールを評価し、Alertmanagerへアラートを送ります。PrometheusRuleにLogQLを入れたり、
任意の`loki_rule` ConfigMapラベルを付けたりしてもルールは読み込まれません。
上の基準設定ではrulerレプリカは0です。評価テスト前に、rulerデプロイ、ルールストア/APIまたはマウント、
評価間隔、Alertmanagerエンドポイントを設定します。

一般的な`"error"`や`"unauthorized"`の文字列があるだけでは、障害や攻撃は証明されません。
CrashLoopBackOffはアプリケーションログ頼みでなく、kube-state-metricsのコンテナ状態で確認します。
比率アラートには、分子/分母の範囲一致、解析エラー処理、ゼロトラフィック処理、エラー系列欠損時の動作が必要です。
[アラートルーティングと抑制のテスト](./07-observability-alerts.md)に結び付けてください。

## Tempo 3: モノリシックと分散運用

TempoはトレースID検索とTraceQL属性検索をサポートします。
metrics-generatorは選択したトレースからメトリクスを導出し、検索を有効にするスイッチではありません。

| コンポーネント | Tempo 3分散構成での責務 |
|---|---|
| Distributor | 受信スパンをKafkaへ書き込む |
| Block-builder | Kafkaを消費してオブジェクトストアのブロックを作成 |
| Live-store | 最近のデータのクエリを処理 |
| Backend-scheduler / backend-worker | ブロック保守、コンパクション、保持 |
| Query-frontend / querier | 最近のデータとオブジェクトストレージへのクエリ |

2.xのingesterとcompactorターゲット、およびスケーラブルな単一バイナリモードは削除されました。
モノリシックの単一プロセスモードにKafkaは不要です。
`replicas`を増やすことは、分散HAへ変換するサポートされた方法ではありません。

### 単一インスタンスの演習

`tempo-lab-values.yaml`はKafkaなしのローカルPVCを使います。プロセス/PVC障害で可用性が
中断する場合があります。この設定を分散S3デプロイのvaluesと混ぜないでください。
チャート3.0.0ではJaegerプロトコルを個別に`null`で無効にします。親を削除するとチャートの
レンダリングが壊れます。Serviceに旧ポートが残る場合がありますが、実際のreceiver設定と
ネットワークポリシーに従ってアクセスを制限します。

```yaml
# tempo-lab-values.yaml
replicas: 1
tempo:
  tag: 3.0.3
  reportingEnabled: false
  retention: 336h
  receivers:
    jaeger:
      protocols:
        grpc: null
        thrift_binary: null
        thrift_compact: null
        thrift_http: null
    otlp:
      protocols:
        grpc:
          endpoint: 0.0.0.0:4317
        http:
          endpoint: 0.0.0.0:4318
  resources:
    requests:
      cpu: 250m
      memory: 512Mi
    limits:
      memory: 2Gi
  metricsGenerator:
    enabled: true
    storage:
      path: /var/tempo/metrics
      remote_write:
      - url: http://prometheus-kube-prometheus-prometheus.observability.svc:9090/api/v1/write
        send_exemplars: true
  overrides:
    defaults:
      metrics_generator:
        processors:
        - service-graphs
        - span-metrics
persistence:
  enabled: true
  storageClassName: gp3
  size: 20Gi
```

```bash
helm upgrade --install tempo grafana-community/tempo --version 3.0.0   --namespace observability -f tempo-lab-values.yaml
```

### レビュー用の分散設定

このファイルは単一インスタンスチャートの代替であり、上書き用オーバーレイではありません。
KafkaとS3は存在する必要があります。例は隔離した検証環境の内部Kafkaエンドポイントを使います。
本番KafkaのTLS/認証要件をTempo 3.0.3のクライアント対応に照らして先に確認します。
このバージョンの`ingest.kafka`には任意の`tls`やMSK IAMフィールドはサポートされません。
SASLユーザー名/パスワード対応は転送暗号化を意味しません。

デフォルト`partitions_per_instance: 1`では、Kafkaパーティション3つにblock-builder 3つが必要です。
このチャート例はlive-storeも3つ使います。`auto_create_topic_default_partitions`を変えても
既存トピックのサイズは変わりません。自動作成を無効にした場合、実際のパーティション数、
レプリケーション、最小ISR、保持、容量を別途設定します。
block-builder/live-storeのvaluesに未対応の`persistence`キーを追加してもPVCは作られません。
チャートの実際のストレージ動作とKafka再生期間を使って復旧をテストします。

```yaml
# tempo-distributed-values.yaml
reportingEnabled: false
multitenancyEnabled: false
tempo:
  image:
    tag: 3.0.3
ingest:
  kafka:
    address: kafka.kafka.svc.cluster.local:9092
    topic: tempo-traces
    auto_create_topic_enabled: false
    auto_create_topic_default_partitions: 3
blockBuilder:
  replicas: 3
liveStore:
  replicas: 3
backendScheduler:
  enabled: true
  config:
    provider:
      compaction:
        compaction:
          block_retention: 336h
  persistence:
    enabled: true
    size: 20Gi
    storageClass: gp3
backendWorker:
  replicas: 2
  podDisruptionBudget:
    enabled: true
distributor:
  replicas: 2
querier:
  replicas: 2
queryFrontend:
  replicas: 2
traces:
  otlp:
    grpc:
      enabled: true
    http:
      enabled: true
storage:
  trace:
    backend: s3
    s3:
      bucket: REPLACE_WITH_UNIQUE_TEMPO_BUCKET
      endpoint: s3.ap-northeast-2.amazonaws.com
      region: ap-northeast-2
serviceAccount:
  create: true
  name: tempo
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/docs-tempo-s3
metricsGenerator:
  enabled: true
  kind: StatefulSet
  persistence:
    enabled: true
    storageClass: gp3
    size: 20Gi
  config:
    storage:
      remote_write:
      - url: http://prometheus-kube-prometheus-prometheus.observability.svc:9090/api/v1/write
        send_exemplars: true
overrides:
  defaults:
    metrics_generator:
      processors:
      - service-graphs
      - span-metrics
gateway:
  enabled: true
```

```bash
helm template tempo grafana-community/tempo-distributed --version 3.5.1   --namespace observability -f tempo-distributed-values.yaml > tempo-rendered.yaml
```

3.5.1のPDBテンプレートでデフォルトが欠けることを避けるため、`backendWorker.podDisruptionBudget.enabled`を
明示します。レンダリングではKafka接続、S3権限、スケジューリング、エンドツーエンドの書き込み/クエリは
テストされません。分散取り込みは`tempo-distributor:4318`、クエリは`tempo-query-frontend:3200`を使います。
以下のCollectorとGrafana両方の演習URLを更新してください。

### 2.xから3.xへの移行

モノリシックモードでは`tempo-cli migrate config --mode=monolithic`の出力を確認します。
分散モードでは並行デプロイ、検証、トラフィック移行を行います。
`ingester`、`ingester_client`、`compactor`、`metrics_generator_client`と削除された
`local_blocks`設定を取り除きます。過去ストレージはvParquet4以降のブロックを使う必要があります。

共有ストレージに2つのコンパクションシステムを同時に有効にしないでください。
3.xのデフォルトと全テナントオーバーライドで`compaction_disabled`を設定し、2.x compactor停止後に削除します。
テナントオーバーライドは省略したデフォルトフィールドを単純に継承しません。
切り替え前に過去と新しいトレースIDの両方を確認します。
TraceQLメトリクスにはRF1ブロック範囲などの移行制約があります。過去トレースが利用可能でも、
過去メトリクスの範囲が同一になるとは限りません。

## Collectorとサンプリング

この設定は1つのCollectorでテールサンプリングを検証します。アプリケーションはリソースに
`service.name`を設定する必要があります。Kubernetesメタデータは自動追加されません。
k8sattributes追加にはPod関連付け戦略と別RBACが必要です。
Kubernetesイベントはログシグナルで、`k8s_events`はトレースreceiverではありません。

機密属性の削除はテールバッファの前です。対象は列挙キーのみで、機密情報を含み得る
全ログ、イベント、属性をカバーしません。`db.statement`のハッシュ化だけでプライバシーや
シークレット保護が成立するわけではありません。

```yaml
# collector.yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318
processors:
  memory_limiter:
    check_interval: 1s
    limit_mib: 768
    spike_limit_mib: 128
  attributes/remove-secrets:
    actions:
      - key: http.request.header.authorization
        action: delete
      - key: db.statement
        action: delete
      - key: db.query.text
        action: delete
  tail_sampling:
    decision_wait: 30s
    num_traces: 20000
    expected_new_traces_per_sec: 500
    policies:
      - name: errors
        type: status_code
        status_code:
          status_codes: [ERROR]
      - name: slow
        type: latency
        latency:
          threshold_ms: 2000
      - name: baseline
        type: probabilistic
        probabilistic:
          sampling_percentage: 10
  batch:
    send_batch_size: 512
    send_batch_max_size: 1024
    timeout: 1s
exporters:
  otlphttp/tempo:
    endpoint: http://tempo.observability.svc:4318
    retry_on_failure:
      enabled: true
    sending_queue:
      enabled: true
      queue_size: 1000
extensions:
  health_check:
    endpoint: 0.0.0.0:13133
service:
  extensions: [health_check]
  pipelines:
    traces:
      receivers: [otlp]
      processors: [memory_limiter, attributes/remove-secrets, tail_sampling, batch]
      exporters: [otlphttp/tempo]
  telemetry:
    metrics:
      readers:
        - pull:
            exporter:
              prometheus:
                host: 0.0.0.0
                port: 8888
```

```yaml
# collector-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: otel-collector
  namespace: observability
spec:
  replicas: 1
  strategy:
    type: Recreate
  selector:
    matchLabels:
      app: otel-collector
  template:
    metadata:
      labels:
        app: otel-collector
    spec:
      automountServiceAccountToken: false
      containers:
        - name: collector
          image: otel/opentelemetry-collector-contrib:0.160.0
          args: ["--config=/etc/otel/collector.yaml"]
          resources:
            requests:
              cpu: 250m
              memory: 512Mi
            limits:
              memory: 1Gi
          ports:
            - {name: otlp-grpc, containerPort: 4317}
            - {name: otlp-http, containerPort: 4318}
            - {name: metrics, containerPort: 8888}
            - {name: health, containerPort: 13133}
          readinessProbe:
            httpGet:
              path: /
              port: health
          livenessProbe:
            httpGet:
              path: /
              port: health
          volumeMounts:
            - {name: config, mountPath: /etc/otel, readOnly: true}
      volumes:
        - name: config
          configMap:
            name: otel-collector
---
apiVersion: v1
kind: Service
metadata:
  name: otel-collector
  namespace: observability
spec:
  selector:
    app: otel-collector
  ports:
    - {name: otlp-grpc, port: 4317, targetPort: otlp-grpc}
    - {name: otlp-http, port: 4318, targetPort: otlp-http}
    - {name: metrics, port: 8888, targetPort: metrics}
```

```bash
kubectl create configmap otel-collector --namespace observability   --from-file=collector.yaml --dry-run=client -o yaml | kubectl apply -f -
kubectl apply -f collector-deployment.yaml
```

Collector Contrib 0.160.0は内部メトリクスに`service.telemetry.metrics.readers`を使います。
旧`metrics.address`、存在しない単独`rate_limiting`プロセッサー、削除された`loki`エクスポーターを
残さないでください。マニフェストはConfigMap、Service、ポートを接続します。
単一インスタンス演習は`Recreate`を使い、更新でバッファ内トレースやメモリ内キューを失う場合があります。

| 設定 | 意味 |
|---|---|
| ヘッドサンプリング | 開始時に判断。まだ不明な最終エラー/レイテンシーでは選択できない |
| テールサンプリング | `decision_wait`内に受信したスパンから判断。完全性は保証されない |
| エラー/レイテンシー/ベースラインポリシー | ここではOR結合。別のレート制限ポリシーは全体上限ではない |
| `spans_per_second` | 毎秒スパン数でありトレース数ではない。単独プロセッサーではない |
| `num_traces` | 保留トレースバッファ容量。あふれ、遅延データ、再起動でスパンを失い得る |
| `send_batch_size` | 送信トリガー。バッチサイズ上限は`send_batch_max_size` |

複数テールサンプラーでは、1トレースの全スパンを同じサンプラーに届けるトレースIDルーティングが必要です。
通常のランダムなService分散はトレースを分割する場合があります。テールサンプリングはヘッドで破棄した
スパンを復元できません。キュー上限、遅延スパン、受信失敗があるため、全エラートレース保持は保証できません。
`UNSET`はエラー状態ではなく、含めると大量の通常スパンを保持し得ます。
サービスグラフと生成メトリクスはサンプリング依存です。全リクエスト母集団を測定するには別途計装したメトリクスを使います。

## TraceQL、サービスグラフ、ログの関連付け

これらは個々のトレースの検索クエリです。`span:duration`はスパンを測り、トレース全体ではありません。
HTTP属性はSDKの意味規約バージョンに依存します。前章のテスト済みGo例は
`http.response.status_code`、デフォルトPython計装は`http.status_code`を使います。

```traceql
{ resource.service.name = "correlation-api" && span:status = error }
```

```traceql
{ resource.service.name = "correlation-api" && span:duration > 2s }
```

```traceql
{ resource.service.name = "api-gateway" } >> { resource.service.name = "order-service" }
```

```traceql
{ resource.service.name = "correlation-api" } | by(span:status) | count() > 1
```

`>>`は子孫、`>`は直接の子を意味します。`| by(...) | count()`はスパン集合を集約します。
`rate()`などのTraceQLメトリクス関数は時系列を返し、個別トレース検索とは異なります。
既知のIDにはGrafanaのトレースIDモードかTempoのトレースAPIを使い、
`{ trace:id = "abc123" }`のような無効な組み込み属性と不完全なIDを使わないでください。

Tempo例はデプロイ設定とオーバーライドの両方でservice-graphsとspan-metricsを接続し、
結果をPrometheus remote-write receiverへ送ります。
サービスグラフには適切なclient/server SpanKindと一貫したサービス名が必要です。
生の`http.target`、完全URL、ユーザーIDをディメンションにするとカーディナリティが膨らむ場合があります。

テスト済みの[Java MDC/LogbackとGo/Pythonのトレース/エグゼンプラー例](./08-observability-analysis.md)を再利用します。
`is_recording()`がfalseでも有効な未サンプリングコンテキストは存在し得ます。
スパンがないときに通常ログを破棄せず、`MDC.clear()`で無関係なMDC値を消さないでください。

## PrometheusとGrafana

次のkube-prometheus-stack valuesは、Tempo生成メトリクスのremote-write receiverと
エグゼンプラーストレージを有効にします。receiverはTempoなど信頼する送信者に制限します。
アプリケーションメトリクスには引き続きスクレイプ対象/ServiceMonitorと、前章の`correlation-api`で使う
メトリクス/ラベルの契約が必要です。

Grafanaは明示的な`prometheus`、`loki`、`tempo` UID、`tracesToLogsV2`、空白を許容する
32文字小文字トレースID正規表現、プロビジョニングの`$`エスケープを使います。
`serviceMap`の対象には、生成サービスグラフメトリクスが実際に存在する必要があります。

```yaml
# prometheus-values.yaml
prometheus:
  prometheusSpec:
    enableFeatures:
    - exemplar-storage
    exemplars:
      maxSize: 100000
    enableRemoteWriteReceiver: true
    retention: 7d
    walCompression: true
    storageSpec:
      volumeClaimTemplate:
        spec:
          storageClassName: gp3
          accessModes:
          - ReadWriteOnce
          resources:
            requests:
              storage: 50Gi
grafana:
  sidecar:
    dashboards:
      enabled: true
      label: grafana_dashboard
      labelValue: '1'
      searchNamespace: observability
    datasources:
      enabled: true
      defaultDatasourceEnabled: false
      alertmanager:
        enabled: false
  additionalDataSources:
  - name: Prometheus
    uid: prometheus
    type: prometheus
    access: proxy
    url: http://prometheus-kube-prometheus-prometheus.observability.svc:9090
    jsonData:
      httpMethod: POST
      exemplarTraceIdDestinations:
      - name: trace_id
        datasourceUid: tempo
        urlDisplayLabel: View trace
    isDefault: true
  - name: Loki
    uid: loki
    type: loki
    access: proxy
    url: http://loki-gateway.observability.svc:80
    jsonData:
      derivedFields:
      - name: TraceID
        matcherRegex: '"trace_id"\s*:\s*"([0-9a-f]{32})"'
        datasourceUid: tempo
        url: $${__value.raw}
        urlDisplayLabel: View trace
  - name: Tempo
    uid: tempo
    type: tempo
    access: proxy
    url: http://tempo.observability.svc:3200
    jsonData:
      tracesToLogsV2:
        datasourceUid: loki
        spanStartTimeShift: -5m
        spanEndTimeShift: 5m
        tags:
        - key: service.name
          value: service_name
        filterByTraceID: true
        filterBySpanID: false
        customQuery: false
      tracesToMetrics:
        datasourceUid: prometheus
        spanStartTimeShift: -5m
        spanEndTimeShift: 5m
        tags:
        - key: service.name
          value: service
        queries:
        - name: Request rate
          query: sum(rate(http_requests_total{$$__tags}[5m]))
      serviceMap:
        datasourceUid: prometheus
```

```bash
helm upgrade --install prometheus prometheus-community/kube-prometheus-stack   --version 90.1.1 --namespace observability -f prometheus-values.yaml
```

エグゼンプラーには、計装によるトレース/スパン関連付け、OpenMetrics公開、Prometheusのストレージ対応、
Grafana UIDマッピングが必要です。HTTP/2やヒストグラム設定だけでは作成されません。
サンプリング、保持、テナント、権限により、リンク先トレースが利用できない場合もあります。

ダッシュボード自動化では、選択したConfigMap値にダッシュボードJSON自体を入れます。
API応答の`dashboard`ラッパーを使ったり、provider YAMLをダッシュボードJSONとして扱ったりしないでください。
これらのvaluesは`observability`の`grafana_dashboard: "1"` ConfigMapを選択します。
手動管理provider/マウントと重複するサイドカー設定を混在させないでください。
前章の完全なダッシュボードJSONをこのConfigMapに置けます。

## AMP: 書き込み権限と読み取り権限の分離

AMPはPrometheus互換のストレージとクエリを提供します。設定済みコレクターやマネージドスクレイパーなしでは
クラスターメトリクスを収集しません。以下のTerraformはワークスペースと別々のIRSA writer/readerロールを作成します。
EKS OIDCプロバイダーは存在する必要があります。
CloudWatchメトリクスは別の収集経路なしでは自動で含まれません。

```hcl
# amp.tf
terraform {
  required_version = ">= 1.15.0, < 2.0.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "6.64.0"
    }
  }
}

provider "aws" {
  region = var.region
}

variable "region" {
  type    = string
  default = "ap-northeast-2"
}

variable "oidc_provider_arn" {
  type = string
}

variable "oidc_issuer" {
  type        = string
  description = "EKS OIDC issuer without https:// or a trailing slash."
  validation {
    condition     = can(regex("^oidc\\.eks\\.[a-z0-9-]+\\.amazonaws\\.com/id/[A-Za-z0-9]+$", var.oidc_issuer))
    error_message = "Use the cluster's exact OIDC issuer host/path without https://."
  }
}

resource "aws_prometheus_workspace" "docs" {
  alias = "docs-observability"
}

locals {
  clients = {
    writer = {
      service_account = "prometheus-amp"
      actions         = ["aps:RemoteWrite"]
    }
    reader = {
      service_account = "grafana-amp"
      actions         = ["aps:QueryMetrics", "aps:GetLabels", "aps:GetSeries", "aps:GetMetricMetadata"]
    }
  }
}

resource "aws_iam_role" "amp" {
  for_each = local.clients
  name     = "docs-amp-${each.key}"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Federated = var.oidc_provider_arn }
      Action    = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "${var.oidc_issuer}:sub" = "system:serviceaccount:observability:${each.value.service_account}"
          "${var.oidc_issuer}:aud" = "sts.amazonaws.com"
        }
      }
    }]
  })
}

resource "aws_iam_role_policy" "amp" {
  for_each = local.clients
  role     = aws_iam_role.amp[each.key].id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = each.value.actions
      Resource = aws_prometheus_workspace.docs.arn
    }]
  })
}

output "workspace_id" {
  value = aws_prometheus_workspace.docs.id
}

output "workspace_endpoint" {
  value = aws_prometheus_workspace.docs.prometheus_endpoint
}

output "client_role_arns" {
  value = { for k, v in aws_iam_role.amp : k => v.arn }
}
```

`oidc_provider_arn`とスキームなしの`oidc_issuer`は同じEKSクラスターを識別する必要があります。
writerは`observability:prometheus-amp`、readerは`observability:grafana-amp`を信頼し、
両方とも`aud=sts.amazonaws.com`に制限します。ポリシーはこのワークスペースARNだけを対象にします。
RemoteWriteがあってもQueryMetricsがないGrafanaロールはメトリクスをクエリできません。

以下は`prometheus-values.yaml`用AMPオーバーレイの中核です。
Helmは`additionalDataSources`リスト全体を置換するため、AMP追加前に基本3エントリを保持します。
例は引き続きローカルPrometheusも使います。

```yaml
prometheus:
  serviceAccount:
    create: true
    name: prometheus-amp
    annotations:
      eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/docs-amp-writer
  prometheusSpec:
    replicas: 2
    replicaExternalLabelName: __replica__
    externalLabels:
      cluster: production-seoul-prometheus
    remoteWrite:
    - url: https://aps-workspaces.ap-northeast-2.amazonaws.com/workspaces/REPLACE_WORKSPACE_ID/api/v1/remote_write
      sigv4:
        region: ap-northeast-2
      queueConfig:
        maxSamplesPerSend: 1000
        capacity: 5000
        maxShards: 20
grafana:
  serviceAccount:
    create: true
    name: grafana-amp
    annotations:
      eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/docs-amp-reader
  env:
    GF_AUTH_SIGV4_AUTH_ENABLED: 'true'
  additionalDataSources:
  - name: AMP
    uid: amp
    type: prometheus
    access: proxy
    url: https://aps-workspaces.ap-northeast-2.amazonaws.com/workspaces/REPLACE_WORKSPACE_ID/
    jsonData:
      httpMethod: POST
      sigV4Auth: true
      sigV4AuthType: default
      sigV4Region: ap-northeast-2
```

断片を`amp-overlay.yaml`として保存し、PyYAMLをインストールしたPythonでデータソースリストを
明示的に組み立てます。このプログラムはそのリストだけを結合し、Helmの一般的なマージ動作を再実装しません。
適用前にIAMロールARNとワークスペースエンドポイントを置き換えてください。

```python
import yaml
from pathlib import Path

base = yaml.safe_load(Path("prometheus-values.yaml").read_text())
overlay = yaml.safe_load(Path("amp-overlay.yaml").read_text())
overlay["grafana"]["additionalDataSources"] = (
    base["grafana"]["additionalDataSources"]
    + overlay["grafana"]["additionalDataSources"]
)
Path("amp-values.yaml").write_text(yaml.safe_dump(overlay, sort_keys=False))
```

```bash
helm template prometheus prometheus-community/kube-prometheus-stack   --version 90.1.1 --namespace observability   -f prometheus-values.yaml -f amp-values.yaml > amp-rendered.yaml
```

### HA、キュー、保持期間

AMPのHA重複排除は`cluster`と`__replica__`を使います。同じデータのレプリカには同じ
`cluster`と異なる`__replica__`値が必要です。スクレイプ範囲が違う独立Prometheusを1つのHAグループに
まとめるとデータを失う場合があります。メトリクス自身の`cluster`ラベルとの競合を確認します。
クラスター間のワークスペース/HAグループラベルを計画してください。別々のワークスペースは自動連携しません。

キューのシャード数と容量はスループットとメモリに影響します。WALと再試行は無制限のバッファや配信保証ではありません。
ローカル保持7日は、remote-write停止7日分の再送を保証しません。ラグ、失敗、拒否、WAL動作を監視し、
復旧をテストします。名前空間のkeepフィルターは、そのラベルがないノード/クラスターメトリクスを削除する場合があります。
`labeldrop`は以前区別されていた系列を衝突させ得ます。記録ルールは集約系列を追加し、
元のカーディナリティを自動削減しません。

AMPワークスペースの保持期間は最大1,095日まで設定可能です。150日が固定上限でThanosが必要という
主張は誤りです。保持期間を増やしても、期限切れメトリクスは復元できません。

| 項目 | AMP | Thanos |
|---|---|---|
| ストレージと運用 | マネージドストレージ。収集、IAM、クォータ、費用、ルールは利用者が担当 | オブジェクトストレージ統合とquery/store/compactorコンポーネントを運用 |
| 保持期間 | ワークスペース設定とサービス制限 | compactorポリシー、オブジェクトストレージ、予算 |
| HAと複数クラスター | 明示的HAラベルとワークスペース設計 | レプリカラベル、重複排除、ストア接続 |
| ダウンサンプリング | Thanos型の自動ダウンサンプリングを想定しない | compactorの解像度/保持とクエリ動作を確認 |

SigV4はAWSリクエストを認証し、TLS暗号化を代替しません。GrafanaプロセスのSigV4有効化、
認証情報、IRSA信頼、ワークスペースのクエリ権限を併せて検証してください。
Amazon Managed Grafanaと自己ホストGrafanaはロール設定の手順が異なります。

## 適用後

1. レンダリングしたイメージ、PVC、Serviceポート、ConfigMapマウント、ServiceAccountを確認します。
2. 各バックエンドでログ1件、トレース1件、直接計装したメトリクス1件をクエリします。
3. テナントと時間範囲も含め、Grafanaのトレース→ログ、ログ→トレース、エグゼンプラーのリンクを確認します。
4. 本番外でCollector再起動、Kafka再生、S3権限失敗、remote-writeの中断/復旧をテストします。
5. Lokiの保持期間による削除、Tempoブロック保守、警告、クォータ、費用を観察します。

このレビューでは、バージョン固定チャートのレンダリング、ネイティブLoki/Tempo/Collector/Alloy設定パーサー、
レンダリングされたPVC/Service/IDの確認、Terraformモックテストを使いました。
EKS/Kafka/S3をデプロイせず、実際のGrafanaログインとAWS読み取り/書き込みアクセスは証明していません。

## 公式参考資料

- [Lokiのデプロイモード](https://grafana.com/docs/loki/latest/get-started/deployment-modes/)
- [Lokiの保持期間](https://grafana.com/docs/loki/latest/operations/storage/retention/)
- [GrafanaコミュニティHelmチャート](https://github.com/grafana-community/helm-charts)
- [Promtailのライフサイクル](https://grafana.com/docs/loki/latest/send-data/promtail/)
- [Tempo 3への移行](https://grafana.com/docs/tempo/latest/set-up-for-tracing/setup-tempo/migrate-to-3/)
- [Tempo 3.0.3のKafka設定](https://github.com/grafana/tempo/blob/v3.0.3/pkg/ingest/config.go)
- [Collectorのテールサンプリング](https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/v0.160.0/processor/tailsamplingprocessor)
- [Collectorのバッチプロセッサー](https://github.com/open-telemetry/opentelemetry-collector/tree/v0.160.0/processor/batchprocessor)
- [AMPワークスペース設定](https://docs.aws.amazon.com/prometheus/latest/userguide/AMP-workspace-configuration.html)
- [AMPの高可用性](https://docs.aws.amazon.com/prometheus/latest/userguide/Send-high-availability-data.html)

---

< [前: 可観測性分析](./08-observability-analysis.md) | [目次](./README.md) | [次: リソース最適化](./10-resource-optimization.md) >
