# VictoriaMetrics

> **レビュー基準**: VictoriaMetrics 1.151.0 · stack chart 0.92.1
> **最終更新**: 2026年9月12日

## 目次

- [概要](#introduction)
- [アーキテクチャの選択肢](#architecture-options)
- [単一ノードモード](#single-node-mode)
- [クラスター モード](#cluster-mode)
- [vmagent](#vmagent)
- [vmalert](#vmalert)
- [MetricsQL](#metricsql)
- [Helm インストール](#helm-installation)
- [長期ストレージの設定](#long-term-storage-configuration)
- [ダウンサンプリング](#downsampling)
- [パフォーマンスの最適化](#performance-optimization)
- [ベストプラクティス](#best-practices)
- [トラブルシューティング](#troubleshooting)

## 概要 {#introduction}

VictoriaMetrics は時系列データを保存・検索します。収集には `vmagent`、ルール評価には `vmalert` という別のツールを使います。Prometheus の remote write を受け付け、Prometheus 互換のクエリーエンドポイントを提供します。**MetricsQL は PromQL と意図的に異なるため**、移行時には結果もすべての Prometheus API の対応状況も同一と決めつけず、実際のクエリーとデータを比較してください。

この章では VictoriaMetrics **1.151.0** と **victoria-metrics-k8s-stack 0.92.1** を扱います。ネイティブテストでは小さなローカルデータセットを使い、マニフェストとチャートを確認・レンダリングしました。EKS への実環境デプロイ、クラウドバックアップ、負荷テスト、障害復旧テストを行ったとは主張しません。

### 比較と測定

| 観点 | 比較する内容 |
|---|---|
| デプロイ構成 | Prometheus は scrape、ローカル TSDB、rule をまとめます。VictoriaMetrics は単一ノードの保存・検索と任意の agent を個別にデプロイできます。クラスター モードでは insert/storage/select に分かれます。 |
| 圧縮と速度 | 同じデータセット、取り込み速度、シリーズの変動、検索範囲、cache 状態、ハードウェアで測定します。ワークロードに依存しない「圧縮率 7 倍」「速度 20 倍」「コスト 70% 削減」の保証はありません。 |
| カーディナリティ | 容量は active series 数、変動、label、クエリのファンアウト、RAM、disk で決まります。どちらの製品にも、普遍的な「1,000 万対 1 億 series」の境界はありません。 |
| 保持期間 | Prometheus のデフォルト保持期間は最大値ではありません。VictoriaMetrics の保持期間は設定できますが、storage 容量には上限があります。 |
| クエリ言語 | MetricsQL は一般的な PromQL 式の多くに対応しますが、rate/increase、NaN、scalar、metric 名の扱いには文書化された違いがあります。 |
| tenant とアクセス | cluster tenant ID はデータ namespace を分離しますが、呼び出し元を認証しません。アクセスを制限し、vmauth などのレビュー済み認証・認可 gateway を使用してください。 |
| downsampling | Enterprise の storage downsampling、取り込み時の stream aggregation、派生 series を追加記録する方式を区別してください。 |

公開 benchmark には実際の software version、dataset、実施日を記載します。出典のない比較値を sizing の根拠にしないでください。

## アーキテクチャの選択肢 {#architecture-options}

| 要件 | 設計上の判断 |
|---|---|
| 1 台の server に収まり、運用の簡素さを重視する | 実測した容量と復旧目標を基に、まず単一ノードモードを評価します。 |
| read/write/storage を個別に拡張する必要がある、または単一 server の限界に達した | クエリのファンアウト、replication cost、運用の複雑さを考慮してクラスター モードを評価します。 |
| 障害に耐える | 独立した failure domain、冗長な取り込み、query routing、永続 storage、検証済みの復元を設計します。process を 2 つ起動したり disk を複製したりするだけでは、service HA は実現しません。 |
| 取り込み量が分かっている | samples/second、active series 数、変動、保持期間、query 負荷に換算します。**1 日あたり 1 億 sample は製品 mode を選ぶ基準ではありません**。 |

独立した単一ノード instance を 2 つ使うには、write の複製と query/failover の処理を明示的に設計する必要があります。HA の近道として複数の `vmsingle` process から同じ data directory を参照させないでください。

## 単一ノードモード {#single-node-mode}

storage と query を 1 つの process で行うと運用は簡素になりますが、すべての collector、alert、HA 機能を実装するわけではありません。容量は実測した workload によって決まります。

後述の raw manifest と Helm profile は、順番に適用するものではなく、**別々のデプロイ方式**です。namespace `monitoring`、Linux EC2 worker、必要な権限と volume binding を備えた既存の `gp3` StorageClass/EBS CSI 環境を前提とします。EKS Auto Mode の storage には独自の provisioner が使われます。Auto Mode、Fargate、Windows、Hybrid Nodes でも同じ class や driver が使えるとは限りません。resource 値は例です。Pod endpoint へのアクセスは信頼できる client に制限してください。ClusterIP は認証ではありません。

### StatefulSet のデプロイ

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: vmsingle
  namespace: monitoring
spec:
  serviceName: vmsingle
  replicas: 1
  selector:
    matchLabels:
      app: vmsingle
  template:
    metadata:
      labels:
        app: vmsingle
    spec:
      containers:
      - name: vmsingle
        image: victoriametrics/victoria-metrics:v1.151.0
        args:
        - --storageDataPath=/storage
        - --httpListenAddr=:8428
        - --retentionPeriod=1y
        - --search.latencyOffset=30s
        - --search.maxUniqueTimeseries=1000000
        - --search.maxSamplesPerQuery=1000000000
        - --memory.allowedPercent=60
        ports:
        - containerPort: 8428
          name: http
        resources:
          requests:
            cpu: 500m
            memory: 2Gi
          limits:
            cpu: 2000m
            memory: 8Gi
        volumeMounts:
        - name: storage
          mountPath: /storage
        livenessProbe:
          httpGet:
            path: /health
            port: 8428
          initialDelaySeconds: 30
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 8428
          initialDelaySeconds: 5
          periodSeconds: 15
      securityContext:
        fsGroup: 65534
        runAsNonRoot: true
        runAsUser: 65534
  volumeClaimTemplates:
  - metadata:
      name: storage
    spec:
      accessModes:
      - ReadWriteOnce
      storageClassName: gp3
      resources:
        requests:
          storage: 100Gi
---
apiVersion: v1
kind: Service
metadata:
  name: vmsingle
  namespace: monitoring
spec:
  selector:
    app: vmsingle
  ports:
  - port: 8428
    targetPort: 8428
    name: http
  type: ClusterIP
```

### 主な endpoint

| endpoint | 説明 |
|----------|-------------|
| `/api/v1/write` | Prometheus Remote Write |
| `/api/v1/query` | instant query |
| `/api/v1/query_range` | 範囲 query |
| `/api/v1/series` | series metadata |
| `/api/v1/labels` | label 一覧 |
| `/api/v1/label/{name}/values` | label 値一覧 |
| `/vmui` | 組み込み UI |
| `/metrics` | 自身の metric |

## クラスター モード {#cluster-mode}

大規模環境向けのスケーラブルな cluster 構成です。

### アーキテクチャ

![vmagent と Prometheus が vminsert 経由で vmstorage cluster に書き込み、Grafana と vmalert が vmselect 経由で vmstorage を query する構成図。vmstorage は書き込みと query の両経路で共有されます。](../../.gitbook/assets/en-observability-metrics-02-victoriametrics-2.png)

[🔍 インタラクティブな図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-observability-metrics-02-victoriametrics-2.html)

### コンポーネント

| コンポーネント | 役割 | スケーリング方法 |
|-----------|------|----------------|
| **vminsert** | write request の routing | 水平 scaling（Deployment） |
| **vmstorage** | data storage | 水平 scaling（StatefulSet） |
| **vmselect** | query 処理 | 水平 scaling（Deployment） |

矢印は応答ではなく**request**を表します。この raw manifest 例の 3 replica は topology 上の選択であり、普遍的な最小数や可用性の保証ではありません。各 storage member には個別の PVC が必要です。必須の node anti-affinity を使うには、配置可能な Kubernetes node が少なくとも 3 台必要です。

`vminsert -replicationFactor=2` は 2 copy の書き込みを要求します。関連データが実際にその replication factor で書き込まれている場合に限り、`vmselect` も整合するよう設定してください。この flag を増やしても過去データは遡及して複製されません。storage が利用できないと `vmselect` は partial response を返すことがあります。`-search.denyPartialResponse` は partial と判定された応答を拒否しますが、設定した replication factor も判定に影響します。劣化状態の書き込み、未複製の既存データ、複数障害は個別に検証してください。

`1ms` の dedup 設定は同じ timestamp の複製データを処理するもので、vmstorage と vmselect で一致させる必要があります。異なる時刻に動く HA scraper には意図した間隔と同一の識別 label が必要です。`30s` 間隔では各区間につき 1 sample を保持するため、正当な高解像度 sample が破棄されることがあります。これは圧縮の切り替えではありません。vmstorage を追加すると新規 write は再分散されますが、既存の全履歴データは移動しません。

### vmstorage のデプロイ

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: vmstorage
  namespace: monitoring
spec:
  serviceName: vmstorage
  replicas: 3
  selector:
    matchLabels:
      app: vmstorage
  template:
    metadata:
      labels:
        app: vmstorage
    spec:
      containers:
      - name: vmstorage
        image: victoriametrics/vmstorage:v1.151.0-cluster
        args:
        - --storageDataPath=/storage
        - --httpListenAddr=:8482
        - --vminsertAddr=:8400
        - --vmselectAddr=:8401
        - --retentionPeriod=1y
        - --dedup.minScrapeInterval=1ms
        ports:
        - containerPort: 8482
          name: http
        - containerPort: 8400
          name: vminsert
        - containerPort: 8401
          name: vmselect
        resources:
          requests:
            cpu: 500m
            memory: 2Gi
          limits:
            cpu: 2000m
            memory: 8Gi
        volumeMounts:
        - name: storage
          mountPath: /storage
        livenessProbe:
          httpGet:
            path: /health
            port: 8482
          initialDelaySeconds: 30
          periodSeconds: 30
      affinity:
        podAntiAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
          - labelSelector:
              matchLabels:
                app: vmstorage
            topologyKey: kubernetes.io/hostname
  volumeClaimTemplates:
  - metadata:
      name: storage
    spec:
      accessModes:
      - ReadWriteOnce
      storageClassName: gp3
      resources:
        requests:
          storage: 100Gi
---
apiVersion: v1
kind: Service
metadata:
  name: vmstorage
  namespace: monitoring
spec:
  selector:
    app: vmstorage
  clusterIP: None
  ports:
  - port: 8482
    name: http
  - port: 8400
    name: vminsert
  - port: 8401
    name: vmselect
```

### vminsert のデプロイ

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vminsert
  namespace: monitoring
spec:
  replicas: 3
  selector:
    matchLabels:
      app: vminsert
  template:
    metadata:
      labels:
        app: vminsert
    spec:
      containers:
      - name: vminsert
        image: victoriametrics/vminsert:v1.151.0-cluster
        args:
          - "--httpListenAddr=:8480"
          - "--storageNode=vmstorage-0.vmstorage:8400"
          - "--storageNode=vmstorage-1.vmstorage:8400"
          - "--storageNode=vmstorage-2.vmstorage:8400"
          - "--replicationFactor=2"
        ports:
        - containerPort: 8480
          name: http
        resources:
          requests:
            cpu: 200m
            memory: 256Mi
          limits:
            cpu: 1000m
            memory: 1Gi
        livenessProbe:
          httpGet:
            path: /health
            port: 8480
          initialDelaySeconds: 10
          periodSeconds: 30
---
apiVersion: v1
kind: Service
metadata:
  name: vminsert
  namespace: monitoring
spec:
  selector:
    app: vminsert
  ports:
  - port: 8480
    targetPort: 8480
    name: http
  type: ClusterIP
```

### vmselect のデプロイ

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vmselect
  namespace: monitoring
spec:
  replicas: 3
  selector:
    matchLabels:
      app: vmselect
  template:
    metadata:
      labels:
        app: vmselect
    spec:
      containers:
      - name: vmselect
        image: victoriametrics/vmselect:v1.151.0-cluster
        args:
        - --httpListenAddr=:8481
        - --storageNode=vmstorage-0.vmstorage:8401
        - --storageNode=vmstorage-1.vmstorage:8401
        - --storageNode=vmstorage-2.vmstorage:8401
        - --search.maxUniqueTimeseries=1000000
        - --search.maxSamplesPerQuery=1000000000
        - --replicationFactor=2
        - --dedup.minScrapeInterval=1ms
        - --search.denyPartialResponse
        ports:
        - containerPort: 8481
          name: http
        resources:
          requests:
            cpu: 200m
            memory: 512Mi
          limits:
            cpu: 1000m
            memory: 2Gi
        livenessProbe:
          httpGet:
            path: /health
            port: 8481
          initialDelaySeconds: 10
          periodSeconds: 30
---
apiVersion: v1
kind: Service
metadata:
  name: vmselect
  namespace: monitoring
spec:
  selector:
    app: vmselect
  ports:
  - port: 8481
    targetPort: 8481
    name: http
  type: ClusterIP
```

## vmagent

vmagent は metric の収集と転送を行う軽量 agent です。

### 主な機能

- Prometheus scrape 設定との互換性
- 複数の Remote Write 先に対応
- data の buffer と再送
- 少ない resource 使用量
- label の書き換えと filter

### デプロイ

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vmagent
  namespace: monitoring
spec:
  replicas: 1
  selector:
    matchLabels:
      app: vmagent
  template:
    metadata:
      labels:
        app: vmagent
    spec:
      serviceAccountName: vmagent
      containers:
      - name: vmagent
        image: victoriametrics/vmagent:v1.151.0
        args:
        - --promscrape.config=/etc/vmagent/prometheus.yml
        - --remoteWrite.url=http://vminsert:8480/insert/0/prometheus/api/v1/write
        - --remoteWrite.tmpDataPath=/tmp/vmagent-remotewrite-data
        - --remoteWrite.maxDiskUsagePerURL=1GB
        ports:
        - containerPort: 8429
          name: http
        resources:
          requests:
            cpu: 100m
            memory: 256Mi
          limits:
            cpu: 500m
            memory: 1Gi
        volumeMounts:
        - name: config
          mountPath: /etc/vmagent
        - name: tmpdata
          mountPath: /tmp/vmagent-remotewrite-data
      volumes:
      - name: config
        configMap:
          name: vmagent-config
      - name: tmpdata
        emptyDir:
          sizeLimit: 2Gi
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: vmagent-config
  namespace: monitoring
data:
  prometheus.yml: "global:\n  scrape_interval: 30s\n  scrape_timeout: 10s\nscrape_configs:\n- job_name: kubernetes-pods\n  kubernetes_sd_configs:\n  - role: pod\n    namespaces:\n      names:\n      - example-app\n  relabel_configs:\n  - source_labels:\n    - __meta_kubernetes_pod_phase\n    action: keep\n    regex: Running\n  - source_labels:\n    - __meta_kubernetes_pod_container_port_protocol\n    action: keep\n    regex: TCP\n  - source_labels:\n    - __meta_kubernetes_pod_container_port_name\n    action: keep\n    regex: metrics\n  - source_labels:\n    - __meta_kubernetes_pod_annotation_prometheus_io_scrape\n    action: keep\n    regex: 'true'\n  - source_labels:\n    - __meta_kubernetes_pod_annotation_prometheus_io_path\n    action: replace\n    regex: (/.*)\n    target_label: __metrics_path__\n  - source_labels:\n    - __meta_kubernetes_namespace\n    target_label: namespace\n  - source_labels:\n    - __meta_kubernetes_pod_name\n    target_label: pod\n"
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: vmagent
  namespace: monitoring
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: vmagent-pod-discovery
  namespace: example-app
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
kind: RoleBinding
metadata:
  name: vmagent-pod-discovery
  namespace: example-app
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: vmagent-pod-discovery
subjects:
- kind: ServiceAccount
  name: vmagent
  namespace: monitoring
```

この最小構成の agent は、既存の `example-app` namespace 内で TCP の `metrics` port と `prometheus.io/scrape: "true"` を持つ Running Pod だけを scrape します。discovery が IPv4/IPv6 address を取得するため、colon-splitting の書き換えは不要です。namespace の Role には Pod の get/list/watch だけを許可しています。Node/kubelet の scrape には、別途範囲を限定した RBAC と検証済みの serving certificate が必要です。sample を動かすためだけに TLS check を無効にしたり `nodes/proxy` 権限を付与したりしないでください。

任意の `prometheus.io/path` annotation は `/` で始まる場合に使われます。それ以外では scrape path は `/metrics` のままです。

サンプルのキューには `emptyDir` を使います。同じ Pod 内の container restart には耐えますが、**Pod の削除や置き換えには耐えません**。`remoteWrite.maxDiskUsagePerURL` に達すると最も古い queue data が破棄されます。永続的な buffer にはレビュー済みの persistent volume/StatefulSet または operator 設定を使い、URL ごとの queue 容量を設定して、retry、drop、空き容量を監視してください。queue は backup でも、データ損失のない配信の保証でもありません。

### vmagent の sharding

すべての member で同じ discovery/relabel 設定を使い、`0` から `membersCount-1` までの安定した ordinal を個別に割り当てます。`vmagent-0` のように ordinal で終わる StatefulSet 名も使えます。**Deployment の Pod 名はランダムなため、安定した shard 番号にはなりません**。上の 1 replica manifest に sharding flag がないのは意図的です。以下は引数の参照例であり、2 つ目の deploy 可能な workload ではありません。scrape replication と storage replication は別の機能です。scrape stream が重複する場合は互換性のある dedup が必要です。

```yaml
args:
  - "--promscrape.cluster.membersCount=3"    # Total number of vmagents
  - "--promscrape.cluster.memberNum=0"       # Current instance number (0, 1, 2)
  - "--promscrape.cluster.replicationFactor=2"  # How many instances scrape each target
```

## vmalert

vmalert は alert rule を評価して alert を生成する component です。

### デプロイ

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vmalert
  namespace: monitoring
spec:
  replicas: 1
  selector:
    matchLabels:
      app: vmalert
  template:
    metadata:
      labels:
        app: vmalert
    spec:
      containers:
      - name: vmalert
        image: victoriametrics/vmalert:v1.151.0
        args:
        - --datasource.url=http://vmselect:8481/select/0/prometheus
        - --remoteRead.url=http://vmselect:8481/select/0/prometheus
        - --remoteWrite.url=http://vminsert:8480/insert/0/prometheus
        - --notifier.url=http://alertmanager:9093
        - --rule=/etc/vmalert/rules/*.yaml
        - --evaluationInterval=30s
        - --external.url=http://vmalert:8880
        - --external.label=cluster=production
        ports:
        - containerPort: 8880
          name: http
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 500m
            memory: 512Mi
        volumeMounts:
        - name: rules
          mountPath: /etc/vmalert/rules
        livenessProbe:
          httpGet:
            path: /health
            port: 8880
          initialDelaySeconds: 10
          periodSeconds: 30
      volumes:
      - name: rules
        configMap:
          name: vmalert-rules
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: vmalert-rules
  namespace: monitoring
data:
  kubernetes.yaml: "groups:\n- name: kubernetes\n  interval: 30s\n  rules:\n  - alert: NodeMemoryHigh\n    expr: '(node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes)\n\n      / node_memory_MemTotal_bytes * 100 > 90\n\n      '\n    for: 5m\n    labels:\n      severity: warning\n    annotations:\n      summary: High memory usage on {{ $labels.instance }}\n      description: Memory usage is {{ printf \"%.2f\" $value }}%\n  - alert: PodRestartsHigh\n    expr: increase(kube_pod_container_status_restarts_total[1h]) > 5\n    for: 10m\n    labels:\n      severity: warning\n    annotations:\n      summary: 'Frequent restarts: {{ $labels.namespace }}/{{ $labels.pod }}'\n      description: Pod has restarted {{ $value }} times in the last hour\n- name: recording-rules\n  interval: 30s\n  rules:\n  - record: instance:node_cpu_utilization:ratio_rate5m\n    expr: 1 - avg by (instance) (rate(node_cpu_seconds_total{mode=\"idle\"}[5m]))\n  - record: instance:node_memory_utilization:ratio\n    expr:\
    \ '1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes\n\n      '\n"
```

この rule は node-exporter と kube-state-metrics がすでに scrape されている前提です。上記の最小 application Pod discovery はこれらを install しません。restart 回数だけでは `CrashLoopBackOff` の証拠にならないため、alert 名は `PodRestartsHigh` としています。CPU recording では counter の rate を使って比率を保存し、raw cumulative counter の平均は使いません。

`datasource.url` と `remoteRead.url` は query API の base を使い、`remoteWrite.url` は recording/alert-state series を保存する write base を使います。remoteRead という flag 名は、すべての Prometheus Remote Read protocol が実装されているという意味ではありません。Alertmanager が存在し、到達可能である必要があります。notification routing は別途設定します。evaluator の HA では external label、通知の deduplication、alert state の復元を確認してください。

## MetricsQL

MetricsQL は一般的な PromQL 構文に対応しますが、意図的な意味の違いがあります。`rate`/`increase` は lookbehind window より前の raw sample を考慮する場合があり、Prometheus と同じ方法で extrapolation するとは限りません。NaN の点は除外され、scalar/instant-vector や metric 名の扱いも異なることがあります。移行時には既知の入力 data で dashboard、alert 式、recording rule を比較してください。クエリ言語の互換性から Prometheus API 全体への互換性を推測しないでください。

### PromQL 形式の query

```promql
rate(http_requests_total[5m])
sum by (service) (rate(http_requests_total[5m]))
histogram_quantile(0.95, sum by (service, le) (rate(http_request_duration_seconds_bucket[5m])))
```

histogram rate を必要な識別 label と **`le` の両方**で集計してから quantile を計算します。個別に計算した quantile 同士から求めた quantile は、全体の request quantile ではありません。

### MetricsQL の拡張

以下の関数例では小さな合成 gauge `audit_gauge` を使います。自動的に利用できる exporter metric ではありません。

```promql
rate(http_requests_total)
keep_last_value(up)
missing_metric default 0
label_set(up, "env", "demo")
label_del(up, "instance")
label_copy(up, "instance", "node")
label_move(up, "instance", "node")
label_join(up, "dst", "-", "job", "instance")
label_transform(up, "job", "api", "frontend")
union(up{job="api"}, up{job="web"})
lag(audit_gauge[2m])
lifetime(audit_gauge[2m])
scrape_interval(audit_gauge[2m])
range_avg(audit_gauge)
range_max(audit_gauge)
range_min(audit_gauge)
range_sum(audit_gauge)
range_first(audit_gauge)
range_last(audit_gauge)
rollup(audit_gauge[2m])
rollup_rate(http_requests_total[5m])
rollup_delta(audit_gauge[2m])
zscore_over_time(audit_gauge[2m])
```

| 関数または operator | 実際の意味と適用範囲 |
|---|---|
| `rate(metric)` | window を省略すると query step と観測された scrape interval から導出されます。再現可能な rule には window を明示してください。 |
| `keep_last_value(q)` | 評価点の欠損を以前の値で埋めます。scrape 欠落を隠すことがあるため、可用性 alert を正常に見せる目的では使わないでください。 |
| `q1 default q2` | 対応する右辺の式で欠損点を埋めます。欠損 data が zero を意味するとは限らず、常に意図した service label が作られるわけでも、traffic が zero の比率に意味を持たせるわけでもありません。 |
| `label_set/copy/move/join/transform` | query 結果の label を変更します。保存履歴は書き換えません。regex の例は job label を変更するもので、IPv6 address を分割しません。 |
| `label_del` | 識別 label を削除します。出力 series の衝突を確認し、識別子をまとめる場合は明示的に集計してください。 |
| `union` | query 結果を結合します。数値の加算ではありません。 |
| `lag(metric[2m])` | window 内の最新 raw sample と評価時刻の差を秒で返します。2 つの sample 間隔ではありません。 |
| `lifetime(metric[2m])` | **その window 内**の最初と最後の raw sample の間隔を秒で返します。series の保存期間全体ではありません。 |
| `scrape_interval(metric[2m])` | その window の raw sample から間隔を推定します。scrape 設定を読み取るものではありません。 |
| `range_avg/max/min/sum/first/last(q)` | 選択した query range にある各結果 series の評価点に対して動作します。step/resolution が対象の点に影響します。保存履歴全体の集計ではありません。 |
| `rollup`、`rollup_rate`、`rollup_delta` | min/max/avg など複数の rollup 値を返します。追加される `rollup` label と metric type を考慮してください。 |
| `zscore_over_time` | gauge の window に対する統計的な z-score であり、校正済み異常確率でも 0～1 に収まる値でもありません。`anomaly_score` は 1.151.0 でサポートされる関数ではありません。 |

### エラー率、欠損データ、ヒストグラム

まず `status` dimension を一貫して除去します。分子を zero に置き換えるのは、**分母 series がある service に限られます**。分母では traffic が zero の対象を除外します。

```promql
(sum by (service) (rate(http_requests_total{status=~"5.."}[5m])) or 0 * sum by (service) (rate(http_requests_total[5m]))) / (sum by (service) (rate(http_requests_total[5m])) > 0)
```

この fixture は `service` ごとに集計します。cluster や namespace も service identity に含まれる場合は、分子と分母のすべての集計にそれらの label を一貫して含めてください。

ローカルの検証用データでは、正常（5xx なし）は **0**、全リクエストが 5xx の場合は **1**、失敗率 10% は **0.1** です。traffic が zero の場合と service が存在しない場合は値がありません。traffic と telemetry 欠損は別々に監視してください。集計せず status label 付き series を割ると、5xx 分子が同じ 5xx の分母にのみ一致し、真の service error rate ではなく 1 になることがあります。`default 0` を追加しても、これらのケースの代わりにはなりません。

```promql
histogram_share(0.5, sum by (service, le) (rate(http_request_duration_seconds_bucket[5m])))
count(up)
count by (job) (up)
```

上記の `histogram_share` は直近の window で 500 ms 以下だった request の割合を推定します。raw cumulative bucket は counter reset 後の累積を示します。`count(up)` が数えるのは選択された `up` series であり、database の総カーディナリティではありません。カーディナリティの確認には対象を絞った TSDB 診断を使ってください。

## Helm のインストール {#helm-installation}

operator ベースの **victoria-metrics-k8s-stack 0.92.1** では、values のルート階層で `vmsingle`、`vmcluster`、`vmagent`、`vmalert` を設定します。別個の `victoria-metrics-single` または `victoria-metrics-cluster` chart 向け values は、この stack を設定しません。Helm は未使用 key を受け入れることがあるため、render された custom resource を確認してください。

バージョンを固定したアーカイブには operator chart **0.67.3 / operator 0.74.1** が含まれ、VictoriaMetrics **1.151.0** を設定します。chart の Kubernetes `>=1.25.0-0` guard は製品や EKS の完全な support matrix ではありません。以下の `--kube-version 1.35.0` はレンダリング時の入力であり、API server のテストではありません。インストール前に、サポート対象 EKS version、CSI provisioner、既存 operator/CRD の所有関係を確認してください。

```bash
helm repo add vm https://victoriametrics.github.io/helm-charts/
helm repo update vm
helm pull vm/victoria-metrics-k8s-stack --version 0.92.1 --untar --untardir ./vendor
helm template vm-demo ./vendor/victoria-metrics-k8s-stack \
  --namespace monitoring --kube-version 1.35.0 --include-crds \
  -f values-single.yaml > rendered.yaml
```

### values-single.yaml

この starter profile は store と、release label が付いた `VMServiceScrape` object を選択する 1 replica の agent を有効にします。対象、権限、認証情報を設定するまで、無関係な collector、default rule、Grafana、通知 service は意図的に無効にしています。完全な cluster monitoring 構成でも、本番 HA profile でもありません。互換性のある storage provisioning を備えた `gp3` が必要です。resource 値は例です。

```yaml
fullnameOverride: vm-demo
victoria-metrics-operator:
  crds:
    cleanup:
      enabled: false
  operator:
    disable_prometheus_converter: true
grafana:
  enabled: false
defaultDashboards:
  enabled: false
defaultRules:
  enabled: false
alertmanager:
  enabled: false
vmalert:
  enabled: false
vmsingle:
  enabled: true
  spec:
    retentionPeriod: 90d
    storage:
      storageClassName: gp3
      accessModes:
      - ReadWriteOnce
      resources:
        requests:
          storage: 100Gi
    resources:
      requests:
        cpu: 500m
        memory: 2Gi
      limits:
        cpu: '2'
        memory: 8Gi
vmcluster:
  enabled: false
vmagent:
  enabled: true
  spec:
    replicaCount: 1
    selectAllByDefault: false
    serviceScrapeSelector:
      matchLabels:
        app.kubernetes.io/instance: vm-demo
    resources:
      requests:
        cpu: 100m
        memory: 256Mi
      limits:
        cpu: 500m
        memory: 1Gi
prometheus-node-exporter:
  enabled: false
kube-state-metrics:
  enabled: false
kubelet:
  enabled: false
kubeApiServer:
  enabled: false
kubeControllerManager:
  enabled: false
kubeDns:
  enabled: false
coreDns:
  enabled: false
kubeEtcd:
  enabled: false
kubeScheduler:
  enabled: false
kubeProxy:
  enabled: false
```

`serviceScrapeSelector` が選択するのは **VMServiceScrape metadata** です。scrape resource が Service/endpoint を選択するもので、application Pod を直接選ぶ selector ではありません。namespace の選択範囲と agent RBAC を一致させてください。EKS の node/kubelet/control-plane metric では、選択した platform で利用できる endpoint だけを有効にし、TLS を検証してください。managed control-plane endpoint、Auto Mode、Fargate、Windows で同じ target が利用できるとは限りません。

operator/CRD の所有者は 1 つにしてください。この profile は chart の CRD cleanup hook と Prometheus resource の変換を無効にしますが、CRD を任意に削除して安全という意味ではありません。別途管理されている operator を再利用する場合は、競合する controller をインストールせず、その所有関係に合わせて chart を構成してください。CRD upgrade と Helm release upgrade は別々にレビューしてください。

context、render 結果、権限、既存 resource を確認した後、同じ pin と values でインストールします。

```bash
helm upgrade --install vm-demo vm/victoria-metrics-k8s-stack \
  --version 0.92.1 --namespace monitoring --create-namespace \
  -f values-single.yaml
```

### クラスター overlay

**新規の独立した cluster mode deployment** では、この設定を starter profile に重ねます。データ移行として既存の single-node release を cluster mode に切り替えないでください。その CR を無効にすると稼働中の store が削除されることがあり、PVC や履歴 data も自動的に cluster へコピーされません。

```yaml
vmsingle:
  enabled: false
vmcluster:
  enabled: true
  spec:
    retentionPeriod: 90d
    replicationFactor: 2
    vmstorage:
      replicaCount: 3
      extraArgs:
        dedup.minScrapeInterval: 1ms
      storage:
        volumeClaimTemplate:
          spec:
            storageClassName: gp3
            accessModes:
            - ReadWriteOnce
            resources:
              requests:
                storage: 100Gi
      resources:
        requests:
          cpu: 500m
          memory: 2Gi
        limits:
          cpu: '2'
          memory: 8Gi
    vmselect:
      replicaCount: 2
      extraArgs:
        dedup.minScrapeInterval: 1ms
        search.denyPartialResponse: 'true'
      resources:
        requests:
          cpu: 200m
          memory: 512Mi
        limits:
          cpu: '1'
          memory: 2Gi
      storage:
        volumeClaimTemplate:
          spec:
            storageClassName: gp3
            accessModes:
            - ReadWriteOnce
            resources:
              requests:
                storage: 2Gi
    vminsert:
      replicaCount: 2
      resources:
        requests:
          cpu: 200m
          memory: 256Mi
        limits:
          cpu: '1'
          memory: 1Gi
```

`-f values-single.yaml -f values-cluster.yaml` で render します。ローカル検証では VMCluster、replication factor 2、storage 3 replica、一致する 1ms dedup 設定、cluster tenant-0 の write URL を確認しました。operator reconciliation、PVC binding、failure-domain 配置、実際の可用性は引き続き実環境での test が必要です。他の前提が満たされていれば、storage member 3 台は 1 台停止中も N=2 copy を保持するための `2*N-1` 台の条件を満たします。

Grafana では single-node base を参照する Prometheus datasource、または raw cluster 用の `http://vmselect:8481/select/0/prometheus` を利用できます。任意の Grafana chart を有効にする前に、認証、永続化、datasource access を設定してください。vmalert rule、Alertmanager の routing/receiver、exporter target を一緒に構成します。replica を有効にしただけでは alert delivery は成立しません。

## 長期ストレージの設定 {#long-term-storage-configuration}

### 保持期間とディスク容量

重複した `args` mapping や競合する flag を複数指定せず、保持期間の argument を**1 つだけ**選んでください。

```yaml
args:
  - "--retentionPeriod=90d"
```

1.151.0 の default は 1 か月（31 日）、最小値は 1 日です。単位のない数値は月として扱われるため、意図を明確にするには単位を指定してください。保持期間は storage byte 数を制限せず、短くしてもすぐに空き容量が増えるとは限りません。レビュー対象 binary は `storage.maxDiskSpace` flag をサポートしません。`storage.minFreeDiskSpaceBytes` は空き容量がしきい値を下回ると新しい data の受け入れを停止しますが、容量ベースの保持目標を維持するために data を削除するものではありません。merge、snapshot、一時的な workload 増加に備えて余裕を残してください。

### Snapshot のバックアップと復元

`vmbackup` は single-node/vmstorage process と**同じ storage directory**にある整合した snapshot を読み取ります。S3、GCS、Azure Blob、S3-compatible storage、ローカル filesystem を保存先にできます。ローカル snapshot だけでは独立した backup にならないため、remote copy、認証情報、復元手順を保護してください。

上の raw StatefulSet が作成する PVC は **`storage-vmsingle-0`**（`claim-template` + `StatefulSet` + ordinal）で、`vmsingle-storage-vmsingle-0` ではありません。operator が作成する名前は異なるため、実際の Pod volume/PVC を確認してください。任意の CronJob が別 node 上の EBS RWO volume を attach したり、別 Pod が作成した snapshot を読み取ったりできるとは限りません。レビュー済みの同居 backup sidecar/workflow を優先し、snapshot URL を該当 storage process に向けてください。

```bash
# Run only in the reviewed backup container with this storage directory mounted.
vmbackup -storageDataPath=/storage \
  -snapshot.createURL=http://127.0.0.1:8428/snapshot/create \
  -dst=s3://example-vm-backup/cluster-a/vmsingle-0/2026-09-12
```

上記 bucket/prefix は placeholder です。この command は storage snapshot を作成して backup object を書き込みますが、**AWS に対して実行していません**。1 つの保存先に複数 writer を同時に向けないでください。同じ保存先を再利用すると増分同期になりますが、それだけでは過去の状態を不変で保持できません。version 付き保存先と保持期間を定め、復旧を test してください。cluster mode では vminsert/vmselect や負荷分散された任意の member ではなく、**すべての vmstorage member を別々の prefix に**backup します。対象 database process を停止し、レビュー済み storage に互換性のある `vmrestore` workflow で復元してください。

実際の backup container と bucket/prefix には最小権限の workload identity を使い、AWS Region、TLS、network route も構成してください。レビュー対象 source は AWS SDK for Go v2 の default configuration chain を使います。EKS Pod Identity には Agent/association とサポート対象 Linux EC2 platform も必要です。IRSA もサポートされる統合方式です。ServiceAccount 名や S3 network 接続だけでは access は付与されません。選択した backup/retention workflow に必要な read/write/list/delete または KMS operation を確認してください。static AWS access key を chart、CronJob、image に注入しないでください。

## ダウンサンプリング {#downsampling}

Enterprise の storage downsampling と、OSS で**派生 series を追加記録すること**は別の操作です。recording rule は raw data を削除・圧縮せず、保存 series 数を増やすことがあります。取り込み時の stream aggregation も選択肢です。明示的な grouping、reset、入力を保持/破棄する意味を確認してから raw sample を破棄してください。

### 派生 series の記録

出力間隔を 5 分にする場合は、前の recording group**の代わりに**この group を使います。同じ record 名で両方を有効にしないでください。

CPU seconds は counter なので、idle の **rate** を計算してから利用率を導出します。以下の 1 時間式は、記録済みの 5 分ごとの比率観測値を平均します。histogram quantile は別々の series にしてください。同じ label の p50/p90/p99 式を `or` で結合すると、最初に一致した series だけが残り、ほかの値が失われます。

```yaml
groups:
- name: derived-series
  interval: 5m
  rules:
  - record: instance:node_cpu_utilization:ratio_rate5m
    expr: 1 - avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m]))
  - record: instance:node_cpu_utilization:ratio_avg1h
    expr: avg_over_time(instance:node_cpu_utilization:ratio_rate5m[1h])
  - record: service:http_request_duration_seconds:p50_5m
    expr: histogram_quantile(0.5, sum by (service, le) (rate(http_request_duration_seconds_bucket[5m])))
  - record: service:http_request_duration_seconds:p90_5m
    expr: histogram_quantile(0.9, sum by (service, le) (rate(http_request_duration_seconds_bucket[5m])))
  - record: service:http_request_duration_seconds:p99_5m
    expr: histogram_quantile(0.99, sum by (service, le) (rate(http_request_duration_seconds_bucket[5m])))
```

これらの p50/p90/p99 値は派生 gauge であり、元の histogram を再構成したり、任意の長い window にわたる正しい quantile を求めたりできません。後で集計する可能性がある場合は、rate/count/bucket 情報を保持してください。採用前に alert threshold、record interval、入力欠損、query の意味を test する必要があります。

## パフォーマンスの最適化 {#performance-optimization}

| 制御項目 | 実際に制限する対象 |
|---|---|
| `memory.allowedPercent` / `memory.allowedBytes` | 内部 cache を制限します。**process 全体の RSS ではありません**。query/ingestion/Go/OS memory のため、追加の余裕が必要です。 |
| `search.maxMemoryPerQuery` | 1 query です。同時 request と他の memory allocation も考慮してください。 |
| `search.maxUniqueTimeseries`、`search.maxSamplesPerQuery` | 想定外に大きな query を拒否します。取り込み時のカーディナリティは減りません。 |
| `search.maxQueryDuration`、`search.maxPointsPerTimeseries` | query 時間と出力を制限します。range step を大きくすると評価解像度が変わりますが、保存済み sample は変化しません。 |
| `storage.cacheSizeIndexDBDataBlocks`、`storage.cacheSizeIndexDBIndexBlocks` | 高度な cache 上書き設定です。自動 sizing を上書きする前に、cache miss、CPU、disk I/O を測定してください。 |
| `maxLabelsPerTimeseries`、`maxLabelValueLen` | レビュー対象 version は上限超過 series を拒否し、`vm_rows_ignored_total` を増やします。無害な label の切り詰めではありません。 |
| `dedup.minScrapeInterval` | 同じ label set の各区間から 1 点を保持します。一般的な圧縮設定ではなく、replication/scraper cadence に合わせて慎重に選んでください。 |

active series 数と変動、クエリのファンアウト、保持期間、queue の増加、cache 圧迫、disk 空き容量を測定してください。固定 resource 例や単一 benchmark だけでは、本番で安全な容量は決まりません。管理 endpoint と query endpoint は network および application access control で保護してください。

## ベストプラクティス {#best-practices}

replica 数を決める前に障害・復旧目標を定めてください。collector HA、storage replication、query 可用性、backup を分けて考えます。tenant routing/authentication、TLS、workload identity、PVC の所有者、upgrade/migration の責任を明示してください。insert failure、拒否された row、queue drop、遅い query、memory、disk を監視し、rule を書く前に各 component の `/metrics` endpoint が公開する実際の label を確認してください。

ローカルの 1.151.0 `/metrics` endpoint では、以下の metric 名が確認されました。scrape 後は実際の job/instance label で query の対象を絞ってください。

```promql
vm_app_version
rate(vm_rows_inserted_total[5m])
rate(vm_slow_queries_total[5m])
process_resident_memory_bytes
```

### 移行ガイド

1. 現在の scraper を維持したまま、レビュー済みの VictoriaMetrics remote-write 先を追加し、queue の状態とデータ到着を確認します。
2. 欠損/zero traffic、counter reset、histogram 集計を含む既知の入力で、両方の store に対して Grafana query と alert rule を実行します。
3. 履歴を import する場合は整合した Prometheus snapshot を作成・保持します。別途提供される `vmctl` を指定した宛先に対して実行し、保持期間、データ重複/dedup、rate limit、権限を考慮します。
4. 置き換え先 scraper/agent がすべての target を収集し、データが到着した後でのみ、古い write path を停止します。**Grafana datasource の変更は metric 収集の代わりにはなりません**。rollback 期間と backup の所有者を明確にしてください。

```yaml
remote_write:
  - url: http://vmsingle.monitoring.svc:8428/api/v1/write
```

```bash
vmctl prometheus --prom-snapshot=/backup/prometheus-snapshot \
  --vm-addr=http://vmsingle.monitoring.svc:8428
```

これらは設定とコマンドの参照例であり、この検証で移行を実行したわけではありません。上記 URL 名は raw single-node manifest を指します。Helm profile では実際に生成された Service を使ってください。cluster の import/write/query path は single-node と異なります。`vmctl` には `--vm-addr` で vminsert base を、`--vm-account-id` で対象 tenant を渡してください。remote-write URL を importer base の代わりに使わないでください。

## トラブルシューティング {#troubleshooting}

読み取り専用診断には既知の single-node Service とローカル port-forward を使います。operator/Helm deployment では Service 名を置き換えてください。

```bash
kubectl port-forward -n monitoring svc/vmsingle 8428:8428
```

```bash
curl --fail --silent --show-error http://127.0.0.1:8428/api/v1/status/tsdb
curl --fail --silent --show-error http://127.0.0.1:8428/api/v1/status/active_queries
curl --fail --silent --show-error http://127.0.0.1:8428/api/v1/status/top_queries
curl --fail --silent --show-error http://127.0.0.1:8428/metrics
```

TSDB status が示すのは series/cardinality であり、**filesystem の空き byte 数や完全な memory profile ではありません**。process/container memory、PVC/filesystem metric、queue size、storage health を別に確認してください。active/top-query endpoint は request を示し、有用な結果に profiling flag や一定の収集時間が必要なことがあります。query filter、range、step、同時実行数は負荷に大きく影響します。

disk が満杯の場合に必要なのは無差別な削除 command ではなく、storage/保持期間/取り込みの計画です。`delete_series`、`/snapshot/create`、`/internal/force_merge` は状態を変更する管理操作です。削除には有効で範囲を限定した selector と、backup/保持方針の承認が必要です。snapshot が disk block を保持することがあり、force-merge は I/O を消費し、作業用空き容量を必要とします。このため、貼り付けて実行できる読み取り専用診断 block には含めていません。storage 圧迫中に ingress を止めると有限の collector queue があふれることがあります。データ経路全体を調べてください。

## 参考資料

- [VictoriaMetrics 1.151.0](https://github.com/VictoriaMetrics/VictoriaMetrics/releases/tag/v1.151.0)
- [単一ノード](https://docs.victoriametrics.com/victoriametrics/single-server-victoriametrics/)
- [クラスター / replication](https://docs.victoriametrics.com/victoriametrics/cluster-victoriametrics/)
- [MetricsQL](https://docs.victoriametrics.com/victoriametrics/metricsql/)
- [vmagent](https://docs.victoriametrics.com/victoriametrics/vmagent/)
- [vmalert](https://docs.victoriametrics.com/victoriametrics/vmalert/)
- [vmbackup](https://docs.victoriametrics.com/victoriametrics/vmbackup/)
- [Prometheus snapshot の移行](https://docs.victoriametrics.com/victoriametrics/vmctl/prometheus/)
- [Stream aggregation](https://docs.victoriametrics.com/victoriametrics/stream-aggregation/)
- [Stack 0.92.1 の values](https://raw.githubusercontent.com/VictoriaMetrics/helm-charts/victoria-metrics-k8s-stack-0.92.1/charts/victoria-metrics-k8s-stack/values.yaml)
- [VMServiceScrape](https://docs.victoriametrics.com/operator/resources/vmservicescrape/)
- [EKS EBS CSI](https://docs.aws.amazon.com/eks/latest/userguide/ebs-csi.html)
- [Pod Identity SDK の要件](https://docs.aws.amazon.com/eks/latest/userguide/pod-id-minimum-sdk.html)
- [S3 backup の実装](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/v1.151.0/lib/backup/s3remote/s3.go)

## クイズ

[VictoriaMetrics クイズ](../../quizzes/observability/metrics/02-victoriametrics-quiz.md)
