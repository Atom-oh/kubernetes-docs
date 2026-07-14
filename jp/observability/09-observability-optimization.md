# EKS Observability 最適化ガイド

> **サポート対象バージョン**: Amazon EKS 1.29+, OpenTelemetry 0.90+
> **最終更新**: February 2025

---

## 目次

1. [Observability の3つの柱の概要](#1-overview-of-the-three-pillars-of-observability)
2. [ロギングソリューションの比較](#2-logging-solution-comparison)
3. [メトリクスの収集とストレージ](#3-metrics-collection-and-storage)
4. [分散トレーシング](#4-distributed-tracing)
5. [eBPF ベースのノーコードモニタリング](#5-ebpf-based-no-code-monitoring)
6. [コストモニタリング](#6-cost-monitoring)
7. [統合 Observability ダッシュボード](#7-unified-observability-dashboard)
8. [運用上の課題と解決策](#8-operational-challenges-and-solutions)
9. [ベストプラクティスと次のステップ](#9-best-practices-and-next-steps)

---

## 1. Observability の3つの柱の概要

現代のクラウドネイティブ環境において、**observability** とは外部出力を通じてシステムの内部状態を理解する能力です。EKS 環境で効果的な observability を実現するには、3つの主要な柱を理解する必要があります。

### 1.1 Logging、Metrics、Tracing の関係

```mermaid
graph TB
    subgraph "Three Pillars of Observability"
        L[Logging]
        M[Metrics]
        T[Tracing]
    end

    subgraph "Data Characteristics"
        L --> L1[Event-based]
        L --> L2[Unstructured data]
        L --> L3[Optimal for debugging]

        M --> M1[Time-series data]
        M --> M2[Aggregated values]
        M --> M3[Optimal for alerting]

        T --> T1[Request flow tracking]
        T --> T2[Causality analysis]
        T --> T3[Optimal for performance analysis]
    end

    subgraph "Interconnections"
        L -.->|Exemplars| M
        M -.->|Context| T
        T -.->|Correlation ID| L
    end

    style L fill:#e1f5fe
    style M fill:#fff3e0
    style T fill:#f3e5f5
```

### 1.2 各柱の役割と選定基準

| 柱 | 主な役割 | 質問の種類 | データ量 | コスト特性 |
|---|---|---|---|---|
| **Logging** | イベント記録、監査、デバッグ | 「何が起きたか？」 | 高 | 高いストレージコスト |
| **Metrics** | システム状態のモニタリング、アラート | 「システムは健全か？」 | 中 | カーディナリティの影響を受けやすい |
| **Tracing** | リクエストフローの追跡、ボトルネック分析 | 「なぜ遅いのか？」 | 高（サンプリングが必要） | サンプリングレートに比例 |

### 1.3 EKS Observability の全体アーキテクチャ

```mermaid
graph TB
    subgraph "EKS Cluster"
        subgraph "Workloads"
            APP[Application Pod]
            SIDE[Sidecar/Agent]
        end

        subgraph "Collection Layer"
            FB[Fluent Bit<br/>DaemonSet]
            OTEL[OTel Collector<br/>DaemonSet]
            PROM[Prometheus]
        end

        subgraph "eBPF Layer"
            HUBBLE[Cilium Hubble]
            PIXIE[Pixie]
            COROOT[Coroot]
        end
    end

    subgraph "Storage Layer"
        subgraph "Log Storage"
            CWL[CloudWatch Logs]
            LOKI[Loki]
            OS[OpenSearch]
        end

        subgraph "Metrics Storage"
            AMP[Amazon Managed<br/>Prometheus]
            VM[VictoriaMetrics]
        end

        subgraph "Trace Storage"
            XRAY[X-Ray]
            TEMPO[Grafana Tempo]
            JAEGER[Jaeger]
        end
    end

    subgraph "Visualization Layer"
        GRAFANA[Grafana]
        CWD[CloudWatch<br/>Dashboard]
    end

    APP --> FB
    APP --> OTEL
    FB --> CWL
    FB --> LOKI
    FB --> OS
    OTEL --> AMP
    OTEL --> XRAY
    OTEL --> TEMPO
    PROM --> AMP
    PROM --> VM

    CWL --> GRAFANA
    LOKI --> GRAFANA
    AMP --> GRAFANA
    VM --> GRAFANA
    TEMPO --> GRAFANA

    style APP fill:#c8e6c9
    style GRAFANA fill:#ffecb3
```

---

## 2. ロギングソリューションの比較

### 2.1 ログストレージの比較

| 基準 | CloudWatch Logs | OpenSearch | Loki | ClickHouse |
|---|---|---|---|---|
| **コスト** | 取り込み: $0.50/GB<br/>ストレージ: $0.03/GB/月 | インスタンスコスト + EBS<br/>r6g.large: 約$150/月 | オブジェクトストレージコスト<br/>S3: $0.023/GB/月 | インスタンス + ストレージ<br/>高圧縮により削減 |
| **パフォーマンス** | 小規模に最適<br/>大規模ではレイテンシーあり | フルテキスト検索に最適化<br/>複雑なクエリに強い | ラベルベースの高速フィルタリング<br/>フルテキスト検索は限定的 | 分析クエリに最適化<br/>リアルタイム集計に優れる |
| **運用の複雑さ** | フルマネージド<br/>運用負荷は最小限 | クラスター管理が必要<br/>チューニングが複雑 | シンプルなアーキテクチャ<br/>運用が容易 | スキーマ管理が必要<br/>中程度の複雑さ |
| **クエリ機能** | Logs Insights<br/>基本的な分析 | Lucene クエリ<br/>強力なフルテキスト検索 | LogQL<br/>ラベルベースのフィルタリング | SQL ベース<br/>複雑な分析クエリ |
| **スケーラビリティ** | 自動スケーリング<br/>無制限 | 手動シャーディング<br/>ノード追加が必要 | 容易な水平スケーリング<br/>オブジェクトストレージを活用 | シャーディングをサポート<br/>ペタバイト規模 |
| **適したユースケース** | AWS ネイティブ環境<br/>シンプルなロギング | 複雑な検索要件<br/>セキュリティ/コンプライアンス | コスト効率重視<br/>Grafana 統合 | ログ分析/集計<br/>長期保持 |

### 2.2 ログエージェントの比較

| 基準 | Fluent Bit | Fluentd | Vector |
|---|---|---|---|
| **メモリ使用量** | 約15MB | 約60MB | 約30MB |
| **CPU 使用量** | 低 | 中 | 低 |
| **スループット** | 最大約200K msg/s | 最大約50K msg/s | 最大約300K msg/s |
| **言語** | C | Ruby/C | Rust |
| **プラグインエコシステム** | 限定的だがコア機能をサポート | 非常に豊富 | 拡大中 |
| **設定の複雑さ** | 低 | 中 | 中 |
| **EKS 統合** | ネイティブサポート | サポート | サポート |

### 2.3 EKS 向け Fluent Bit + Loki 設定例

```yaml
# fluent-bit-configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: fluent-bit-config
  namespace: logging
data:
  fluent-bit.conf: |
    [SERVICE]
        Flush         5
        Log_Level     info
        Daemon        off
        Parsers_File  parsers.conf
        HTTP_Server   On
        HTTP_Listen   0.0.0.0
        HTTP_Port     2020

    [INPUT]
        Name              tail
        Tag               kube.*
        Path              /var/log/containers/*.log
        Parser            docker
        DB                /var/log/flb_kube.db
        Mem_Buf_Limit     50MB
        Skip_Long_Lines   On
        Refresh_Interval  10

    [FILTER]
        Name                kubernetes
        Match               kube.*
        Kube_URL            https://kubernetes.default.svc:443
        Kube_CA_File        /var/run/secrets/kubernetes.io/serviceaccount/ca.crt
        Kube_Token_File     /var/run/secrets/kubernetes.io/serviceaccount/token
        Kube_Tag_Prefix     kube.var.log.containers.
        Merge_Log           On
        Keep_Log            Off
        K8S-Logging.Parser  On
        K8S-Logging.Exclude On

    [OUTPUT]
        Name                   loki
        Match                  *
        Host                   loki-gateway.logging.svc.cluster.local
        Port                   80
        Labels                 job=fluent-bit
        Label_Keys             $kubernetes['namespace_name'],$kubernetes['pod_name'],$kubernetes['container_name']
        Remove_Keys            kubernetes,stream
        Auto_Kubernetes_Labels on
        Line_Format            json

  parsers.conf: |
    [PARSER]
        Name        docker
        Format      json
        Time_Key    time
        Time_Format %Y-%m-%dT%H:%M:%S.%L
        Time_Keep   On

    [PARSER]
        Name        json
        Format      json
        Time_Key    timestamp
        Time_Format %Y-%m-%dT%H:%M:%S.%L
---
# fluent-bit-daemonset.yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: fluent-bit
  namespace: logging
  labels:
    app: fluent-bit
spec:
  selector:
    matchLabels:
      app: fluent-bit
  template:
    metadata:
      labels:
        app: fluent-bit
    spec:
      serviceAccountName: fluent-bit
      tolerations:
        - key: node-role.kubernetes.io/control-plane
          effect: NoSchedule
        - key: node-role.kubernetes.io/master
          effect: NoSchedule
      containers:
        - name: fluent-bit
          image: fluent/fluent-bit:2.2
          resources:
            limits:
              memory: 200Mi
              cpu: 200m
            requests:
              memory: 100Mi
              cpu: 100m
          volumeMounts:
            - name: varlog
              mountPath: /var/log
            - name: varlibdockercontainers
              mountPath: /var/lib/docker/containers
              readOnly: true
            - name: config
              mountPath: /fluent-bit/etc/
      volumes:
        - name: varlog
          hostPath:
            path: /var/log
        - name: varlibdockercontainers
          hostPath:
            path: /var/lib/docker/containers
        - name: config
          configMap:
            name: fluent-bit-config
```

```bash
# Install Loki (Helm)
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update

# Install Loki in Simple Scalable mode
helm install loki grafana/loki \
  --namespace logging \
  --create-namespace \
  --set loki.auth_enabled=false \
  --set loki.storage.type=s3 \
  --set loki.storage.s3.endpoint=s3.ap-northeast-2.amazonaws.com \
  --set loki.storage.s3.region=ap-northeast-2 \
  --set loki.storage.s3.bucketnames=my-loki-bucket \
  --set loki.storage.s3.insecure=false \
  --set serviceAccount.annotations."eks\.amazonaws\.com/role-arn"=arn:aws:iam::ACCOUNT:role/LokiS3Role
```

---

## 3. メトリクスの収集とストレージ

### 3.1 メトリクスストレージの比較

| 基準 | Prometheus | VictoriaMetrics | AMP (Amazon Managed Prometheus) |
|---|---|---|---|
| **スケーラビリティ** | 単一ノード<br/>垂直スケーリングのみ | クラスターモード<br/>水平スケーリング | 自動スケーリング<br/>無制限 |
| **コスト** | インフラコストのみ<br/>EC2/EBS | インフラコスト<br/>Prometheus より節約 | 取り込み: $0.90/10M サンプル<br/>ストレージ: $0.03/GB/月 |
| **HA** | 別途設定が必要<br/>Thanos/Cortex | 組み込みレプリケーション<br/>自動フェイルオーバー | フルマネージド HA<br/>Multi-AZ |
| **運用オーバーヘッド** | 高<br/>ストレージ/スケーリング管理 | 中<br/>シンプルな運用 | 低<br/>AWS 管理 |
| **長期ストレージ** | 別途ソリューションが必要 | 組み込みサポート | 無制限の保持 |
| **クエリパフォーマンス** | 優秀 | 非常に優秀<br/>（最適化エンジン） | 優秀 |
| **PromQL 互換性** | ネイティブ | 完全互換 + 拡張 | 完全互換 |

### 3.2 カーディナリティ管理戦略

**カーディナリティ**とは、一意の時系列の数を指します。高いカーディナリティはメモリ使用量とクエリパフォーマンスに直接影響します。

```yaml
# prometheus-config.yaml - Metric dropping and label optimization
apiVersion: v1
kind: ConfigMap
metadata:
  name: prometheus-config
  namespace: monitoring
data:
  prometheus.yml: |
    global:
      scrape_interval: 30s
      evaluation_interval: 30s

    scrape_configs:
      - job_name: 'kubernetes-pods'
        kubernetes_sd_configs:
          - role: pod
        relabel_configs:
          # Collect only specific namespaces
          - source_labels: [__meta_kubernetes_namespace]
            regex: 'kube-system|monitoring|production'
            action: keep

          # Remove unnecessary labels
          - regex: '__meta_kubernetes_pod_label_(.+)'
            action: labeldrop

          # Remove Pod UID (high cardinality cause)
          - regex: 'pod_template_hash|controller_revision_hash'
            action: labeldrop

        metric_relabel_configs:
          # Drop unnecessary metrics
          - source_labels: [__name__]
            regex: 'go_.*|promhttp_.*'
            action: drop

          # Limit histogram buckets (major high cardinality culprit)
          - source_labels: [__name__, le]
            regex: '.*_bucket;(0\.001|0\.005|0\.01|0\.05|0\.1|0\.5|1|5|10|30|60|120|300)'
            action: keep
```

### 3.3 Recording Rules によるクエリパフォーマンスの改善

Recording Rules は複雑なクエリを事前計算し、その結果を保存します。

```yaml
# prometheus-recording-rules.yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: recording-rules
  namespace: monitoring
spec:
  groups:
    - name: k8s.rules
      interval: 30s
      rules:
        # Pre-compute CPU utilization per node
        - record: node:cpu_utilization:ratio
          expr: |
            1 - avg by (node) (
              rate(node_cpu_seconds_total{mode="idle"}[5m])
            )

        # Memory utilization per node
        - record: node:memory_utilization:ratio
          expr: |
            1 - (
              node_memory_MemAvailable_bytes
              / node_memory_MemTotal_bytes
            )

        # CPU usage per namespace
        - record: namespace:container_cpu_usage_seconds_total:sum_rate
          expr: |
            sum by (namespace) (
              rate(container_cpu_usage_seconds_total{container!=""}[5m])
            )

        # Pod restart count (hourly)
        - record: namespace:pod_restarts:sum_increase1h
          expr: |
            sum by (namespace) (
              increase(kube_pod_container_status_restarts_total[1h])
            )

    - name: slo.rules
      interval: 30s
      rules:
        # Error rate per service
        - record: service:http_requests:error_rate5m
          expr: |
            sum by (service) (
              rate(http_requests_total{status=~"5.."}[5m])
            )
            /
            sum by (service) (
              rate(http_requests_total[5m])
            )

        # P99 latency per service
        - record: service:http_request_duration_seconds:p99
          expr: |
            histogram_quantile(0.99,
              sum by (service, le) (
                rate(http_request_duration_seconds_bucket[5m])
              )
            )
```

### 3.4 長期ストレージ戦略

```mermaid
graph LR
    subgraph "Short-term Storage (7 days)"
        PROM[Prometheus<br/>Local Storage]
    end

    subgraph "Long-term Storage Options"
        THANOS[Thanos<br/>S3-based]
        VM[VictoriaMetrics<br/>Native Storage]
        AMP[AMP<br/>AWS Managed]
    end

    subgraph "Query Layer"
        TQ[Thanos Query]
        VMQ[VictoriaMetrics<br/>vmselect]
        AMPQ[AMP<br/>Query Endpoint]
    end

    PROM -->|Remote Write| THANOS
    PROM -->|Remote Write| VM
    PROM -->|Remote Write| AMP

    THANOS --> TQ
    VM --> VMQ
    AMP --> AMPQ

    TQ --> GRAFANA[Grafana]
    VMQ --> GRAFANA
    AMPQ --> GRAFANA
```

---

## 4. 分散トレーシング

### 4.1 OpenTelemetry の概要とアーキテクチャ

OpenTelemetry（OTel）は、observability データ（トレース、メトリクス、ログ）を収集およびエクスポートするためのベンダー中立の標準です。

```mermaid
graph TB
    subgraph "Application Layer"
        APP1[Service A<br/>OTel SDK]
        APP2[Service B<br/>OTel SDK]
        APP3[Service C<br/>Auto-instrumentation]
    end

    subgraph "OTel Collector"
        subgraph "Receivers"
            OTLP[OTLP Receiver]
            JAEGER_R[Jaeger Receiver]
            ZIPKIN_R[Zipkin Receiver]
        end

        subgraph "Processors"
            BATCH[Batch Processor]
            ATTR[Attributes Processor]
            TAIL[Tail Sampling]
        end

        subgraph "Exporters"
            OTLP_E[OTLP Exporter]
            XRAY_E[X-Ray Exporter]
            PROM_E[Prometheus Exporter]
        end
    end

    subgraph "Backends"
        TEMPO[Grafana Tempo]
        XRAY[AWS X-Ray]
        JAEGER[Jaeger]
    end

    APP1 -->|OTLP| OTLP
    APP2 -->|OTLP| OTLP
    APP3 -->|OTLP| OTLP

    OTLP --> BATCH
    JAEGER_R --> BATCH
    ZIPKIN_R --> BATCH

    BATCH --> ATTR
    ATTR --> TAIL

    TAIL --> OTLP_E
    TAIL --> XRAY_E
    TAIL --> PROM_E

    OTLP_E --> TEMPO
    XRAY_E --> XRAY
    OTLP_E --> JAEGER
```

### 4.2 トレーシングバックエンドの比較

| 基準 | Grafana Tempo | Jaeger | AWS X-Ray |
|---|---|---|---|
| **アーキテクチャ** | オブジェクトストレージベース<br/>インデックスなし | Elasticsearch/Cassandra<br/>インデックスベース | AWS 管理<br/>サーバーレス |
| **コスト** | S3 ストレージコストのみ<br/>非常に低コスト | インフラコスト<br/>インデックスストレージ | トレースごとの料金<br/>$5/100万トレース |
| **スケーラビリティ** | 無制限<br/>水平スケーリング | ノード追加が必要<br/>インデックス管理 | 自動スケーリング<br/>無制限 |
| **クエリ方式** | TraceID の直接検索<br/>Exemplars 統合 | タグベースの検索<br/>時間範囲検索 | サービスマップ<br/>フィルター検索 |
| **Grafana 統合** | ネイティブ | サポート | 限定的 |
| **AWS 統合** | 別途設定 | 別途設定 | ネイティブ<br/>Lambda、ECS など |
| **適したユースケース** | コスト効率重視<br/>Grafana スタック | 複雑な検索要件<br/>セルフホストインフラ | AWS ネイティブ<br/>サーバーレス環境 |

### 4.3 サンプリング戦略

```yaml
# otel-collector-config.yaml - Sampling strategy configuration
apiVersion: v1
kind: ConfigMap
metadata:
  name: otel-collector-config
  namespace: observability
data:
  config.yaml: |
    receivers:
      otlp:
        protocols:
          grpc:
            endpoint: 0.0.0.0:4317
          http:
            endpoint: 0.0.0.0:4318

    processors:
      # Batch processing - performance optimization
      batch:
        timeout: 5s
        send_batch_size: 1000
        send_batch_max_size: 1500

      # Memory limit - OOM prevention
      memory_limiter:
        check_interval: 1s
        limit_mib: 1000
        spike_limit_mib: 200

      # Probabilistic sampling - Head Sampling
      probabilistic_sampler:
        hash_seed: 22
        sampling_percentage: 10  # 10% sampling

      # Tail Sampling - condition-based sampling
      tail_sampling:
        decision_wait: 10s
        num_traces: 100000
        policies:
          # Keep 100% of traces with errors
          - name: errors
            type: status_code
            status_code:
              status_codes: [ERROR]

          # Keep 100% of high-latency traces
          - name: slow-traces
            type: latency
            latency:
              threshold_ms: 1000

          # Keep 100% of traces from specific services
          - name: critical-services
            type: string_attribute
            string_attribute:
              key: service.name
              values: [payment-service, order-service]

          # Sample only 5% of the rest
          - name: default
            type: probabilistic
            probabilistic:
              sampling_percentage: 5

      # Add/remove attributes
      attributes:
        actions:
          - key: environment
            value: production
            action: upsert
          - key: sensitive_data
            action: delete

    exporters:
      otlp:
        endpoint: tempo-distributor.observability:4317
        tls:
          insecure: true

      awsxray:
        region: ap-northeast-2

      debug:
        verbosity: detailed

    service:
      pipelines:
        traces:
          receivers: [otlp]
          processors: [memory_limiter, batch, tail_sampling, attributes]
          exporters: [otlp, awsxray]
```

### 4.4 EKS 向け OTel Collector DaemonSet 設定

```yaml
# otel-collector-daemonset.yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: otel-collector
  namespace: observability
  labels:
    app: otel-collector
spec:
  selector:
    matchLabels:
      app: otel-collector
  template:
    metadata:
      labels:
        app: otel-collector
    spec:
      serviceAccountName: otel-collector
      containers:
        - name: collector
          image: otel/opentelemetry-collector-contrib:0.92.0
          args:
            - --config=/conf/config.yaml
          ports:
            - containerPort: 4317  # OTLP gRPC
              hostPort: 4317
            - containerPort: 4318  # OTLP HTTP
              hostPort: 4318
            - containerPort: 8888  # Metrics
          resources:
            limits:
              memory: 1Gi
              cpu: 500m
            requests:
              memory: 200Mi
              cpu: 100m
          volumeMounts:
            - name: config
              mountPath: /conf
          env:
            - name: K8S_NODE_NAME
              valueFrom:
                fieldRef:
                  fieldPath: spec.nodeName
            - name: K8S_POD_NAME
              valueFrom:
                fieldRef:
                  fieldPath: metadata.name
            - name: K8S_NAMESPACE
              valueFrom:
                fieldRef:
                  fieldPath: metadata.namespace
      volumes:
        - name: config
          configMap:
            name: otel-collector-config
      tolerations:
        - key: node-role.kubernetes.io/control-plane
          effect: NoSchedule
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
    - name: otlp-grpc
      port: 4317
      targetPort: 4317
    - name: otlp-http
      port: 4318
      targetPort: 4318
    - name: metrics
      port: 8888
      targetPort: 8888
```

アプリケーション向けの OTel SDK を使用した自動インストルメンテーション設定:

```yaml
# Adding auto-instrumentation to application Deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
  namespace: production
spec:
  template:
    metadata:
      annotations:
        # Enable OTel Operator auto-instrumentation
        instrumentation.opentelemetry.io/inject-java: "true"
        # Or for Python, Node.js, etc.
        # instrumentation.opentelemetry.io/inject-python: "true"
        # instrumentation.opentelemetry.io/inject-nodejs: "true"
    spec:
      containers:
        - name: app
          image: my-app:latest
          env:
            - name: OTEL_EXPORTER_OTLP_ENDPOINT
              value: "http://otel-collector.observability:4317"
            - name: OTEL_SERVICE_NAME
              value: "my-app"
            - name: OTEL_RESOURCE_ATTRIBUTES
              value: "service.namespace=production,deployment.environment=prod"
```

---

## 5. eBPF ベースのノーコードモニタリング

### 5.1 eBPF モニタリングが必要な理由

**eBPF（extended Berkeley Packet Filter）**は、Linux カーネル内で安全にプログラムを実行できるようにする技術です。eBPF ベースのモニタリングの最大の利点は、**コードを変更せずに** observability を実現できることです。

```mermaid
graph TB
    subgraph "Traditional Instrumentation"
        A1[Application Code] --> A2[Add SDK]
        A2 --> A3[Modify/Redeploy Code]
        A3 --> A4[Data Collection]
    end

    subgraph "eBPF Instrumentation"
        B1[Application Code] --> B2[No Changes]
        B3[eBPF Program] --> B4[Kernel-level Hooks]
        B4 --> B5[Data Collection]
        B2 -.-> B4
    end

    style A2 fill:#ffcdd2
    style A3 fill:#ffcdd2
    style B2 fill:#c8e6c9
    style B3 fill:#c8e6c9
```

| 特性 | 従来のインストルメンテーション | eBPF インストルメンテーション |
|---|---|---|
| **コード変更** | 必要 | 不要 |
| **デプロイへの影響** | 再デプロイが必要 | 別途デプロイ |
| **オーバーヘッド** | アプリケーションレベル | カーネルレベル（非常に低い） |
| **言語依存性** | 言語ごとに SDK サポートが必要 | 言語非依存 |
| **カバレッジ** | インストルメント済み部分のみ | システム全体 |
| **保守** | コードとともに管理 | 独立 |

### 5.2 Coroot: 自動サービスマップとレイテンシー分析

Coroot は eBPF を使用して、サービスマップを自動生成し、レイテンシーを分析します。

```yaml
# coroot-helm-values.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: coroot
---
# Install Coroot via Helm
# helm repo add coroot https://coroot.github.io/helm-charts
# helm install coroot coroot/coroot -n coroot -f coroot-helm-values.yaml

coroot:
  replicas: 1
  resources:
    requests:
      cpu: 200m
      memory: 1Gi
    limits:
      cpu: 1
      memory: 2Gi

  # Prometheus integration
  prometheus:
    url: "http://prometheus-server.monitoring:9090"

  # ClickHouse storage (logs/traces)
  clickhouse:
    enabled: true
    persistence:
      size: 100Gi
      storageClass: gp3

node-agent:
  # eBPF-based agent
  ebpf:
    enabled: true

  resources:
    requests:
      cpu: 100m
      memory: 100Mi
    limits:
      cpu: 500m
      memory: 500Mi

  tolerations:
    - operator: Exists
```

**Coroot の主な機能:**

- **自動サービスディスカバリー**: eBPF を通じてネットワーク接続を検出し、サービスマップを自動生成
- **レイテンシー分析**: 各サービス間のレイテンシーを自動測定
- **リソース使用状況の追跡**: サービスごとの CPU、メモリ、ディスク I/O を分析
- **ログ収集**: コードを変更せずにアプリケーションログを収集

### 5.3 Pixie（現在は New Relic）: Kubernetes 特化の Observability

Pixie は、Kubernetes 環境に特化した eBPF ベースの observability プラットフォームです。

```bash
# Install Pixie CLI
bash -c "$(curl -fsSL https://withpixie.ai/install.sh)"

# Deploy Pixie
px deploy

# Check cluster status
px get viziers

# Real-time HTTP traffic monitoring
px live http_data

# Per-service latency analysis
px live service_stats
```

**Pixie の主な機能:**

- **すぐに利用できるダッシュボード**: デプロイ直後から HTTP、DNS、MySQL、PostgreSQL などを自動モニタリング
- **PxL スクリプト**: Python に似たクエリ言語によるカスタム分析
- **ローカルデータストレージ**: 機密データがクラスター外に出ない
- **自動暗号化分析**: eBPF を介して TLS トラフィックを復号し分析

### 5.4 Cilium Hubble: ネットワークフローの観測

Cilium CNI を使用する EKS クラスターでは、Hubble がネットワークの可視性を提供します。

```yaml
# cilium-hubble-values.yaml
hubble:
  enabled: true

  relay:
    enabled: true
    resources:
      requests:
        cpu: 100m
        memory: 128Mi

  ui:
    enabled: true
    replicas: 1
    ingress:
      enabled: true
      annotations:
        kubernetes.io/ingress.class: nginx
      hosts:
        - hubble.example.com

  metrics:
    enabled:
      - dns
      - drop
      - tcp
      - flow
      - icmp
      - http
    serviceMonitor:
      enabled: true
```

```bash
# Real-time flow observation with Hubble CLI
hubble observe --namespace production

# Filter traffic to specific service
hubble observe --to-service production/api-server

# Monitor DNS requests
hubble observe --protocol dns

# Analyze dropped packets
hubble observe --verdict DROPPED
```

### 5.5 Kepler: エネルギー消費モニタリング

Kepler（Kubernetes Efficient Power Level Exporter）は、eBPF を使用してワークロードのエネルギー消費を測定します。

```yaml
# kepler-daemonset.yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: kepler
  namespace: kepler
spec:
  selector:
    matchLabels:
      app: kepler
  template:
    metadata:
      labels:
        app: kepler
    spec:
      serviceAccountName: kepler
      containers:
        - name: kepler
          image: quay.io/sustainable_computing_io/kepler:release-0.7
          securityContext:
            privileged: true
          ports:
            - containerPort: 9102
              name: metrics
          volumeMounts:
            - name: lib-modules
              mountPath: /lib/modules
            - name: tracing
              mountPath: /sys/kernel/tracing
            - name: kernel-src
              mountPath: /usr/src/kernels
          env:
            - name: NODE_NAME
              valueFrom:
                fieldRef:
                  fieldPath: spec.nodeName
      volumes:
        - name: lib-modules
          hostPath:
            path: /lib/modules
        - name: tracing
          hostPath:
            path: /sys/kernel/tracing
        - name: kernel-src
          hostPath:
            path: /usr/src/kernels
```

**Kepler メトリクスの例:**

```promql
# Energy consumption by namespace (joules)
sum by (namespace) (kepler_container_joules_total)

# Power consumption by Pod (watts)
rate(kepler_container_joules_total[5m]) * 1000

# Top 10 Pods consuming the most energy
topk(10, sum by (pod_name) (rate(kepler_container_joules_total[5m])))
```

---

## 6. コストモニタリング

### 6.1 KubeCost / OpenCost のインストールと設定

OpenCost は CNCF プロジェクトであり、Kubernetes コストモニタリングのオープンソース標準です。

```bash
# Install OpenCost
helm repo add opencost https://opencost.github.io/opencost-helm-chart
helm repo update

helm install opencost opencost/opencost \
  --namespace opencost \
  --create-namespace \
  --set opencost.prometheus.internal.enabled=false \
  --set opencost.prometheus.external.enabled=true \
  --set opencost.prometheus.external.url="http://prometheus-server.monitoring:9090" \
  --set opencost.ui.enabled=true
```

```yaml
# opencost-values.yaml - Detailed configuration
opencost:
  exporter:
    defaultClusterId: "eks-production"

    # AWS cost integration
    aws:
      spotDataRegion: ap-northeast-2
      spotDataBucket: "my-spot-data-bucket"
      athenaProjectID: "my-aws-project"
      athenaRegion: ap-northeast-2
      athenaDatabase: "athenacurcfn_my_cur"
      athenaTable: "my_cur"
      masterPayerARN: "arn:aws:iam::ACCOUNT:role/OpenCostRole"

  prometheus:
    external:
      enabled: true
      url: "http://prometheus-server.monitoring:9090"

  ui:
    enabled: true
    ingress:
      enabled: true
      annotations:
        kubernetes.io/ingress.class: nginx
      hosts:
        - host: opencost.example.com
          paths:
            - path: /
              pathType: Prefix
```

### 6.2 Namespace/チーム別のコスト配分

```yaml
# cost-allocation-labels.yaml
# Label standardization for team cost tracking
apiVersion: v1
kind: Namespace
metadata:
  name: team-alpha
  labels:
    cost-center: "engineering"
    team: "alpha"
    environment: "production"
---
# Apply cost labels to Pods
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-server
  namespace: team-alpha
spec:
  template:
    metadata:
      labels:
        cost-center: "engineering"
        team: "alpha"
        component: "api"
    spec:
      containers:
        - name: api
          resources:
            requests:
              cpu: 500m
              memory: 512Mi
            limits:
              cpu: 1000m
              memory: 1Gi
```

**OpenCost API によるコストクエリ:**

```bash
# Cost by namespace (last 7 days)
curl -s "http://opencost.opencost:9003/allocation/compute?window=7d&aggregate=namespace" | jq '.'

# Cost by team label
curl -s "http://opencost.opencost:9003/allocation/compute?window=7d&aggregate=label:team" | jq '.'

# Daily cost trend
curl -s "http://opencost.opencost:9003/allocation/compute?window=30d&step=1d&aggregate=namespace" | jq '.'
```

### 6.3 CloudWatch のコスト最適化

```yaml
# cloudwatch-log-retention.yaml
# Cost reduction through log retention period optimization
apiVersion: v1
kind: ConfigMap
metadata:
  name: fluent-bit-cloudwatch-config
  namespace: logging
data:
  fluent-bit.conf: |
    [OUTPUT]
        Name                cloudwatch_logs
        Match               *
        region              ap-northeast-2
        log_group_name      /eks/production/application
        log_stream_prefix   ${HOSTNAME}-
        auto_create_group   true
        # Set log retention period (cost optimization)
        log_retention_days  14

        # Batch settings for API call optimization
        log_format          json
        max_batch_size      1048576
        max_batch_put_limit 100
```

```bash
# Batch set CloudWatch Logs retention period
aws logs describe-log-groups --query 'logGroups[*].logGroupName' --output text | \
while read log_group; do
  aws logs put-retention-policy \
    --log-group-name "$log_group" \
    --retention-in-days 14
done

# Clean up unused log groups
aws logs describe-log-groups --query 'logGroups[?storedBytes==`0`].logGroupName' --output text | \
while read log_group; do
  echo "Deleting empty log group: $log_group"
  aws logs delete-log-group --log-group-name "$log_group"
done
```

### 6.4 ログ/メトリクスストレージのコスト削減戦略

```mermaid
graph TB
    subgraph "Cost Reduction Strategies"
        A[Data Collection] --> B{Priority Classification}

        B -->|High| C[Full Storage<br/>Long-term Retention]
        B -->|Medium| D[Sampling<br/>Medium-term Retention]
        B -->|Low| E[Aggregation Only<br/>Short-term Retention]

        C --> F[S3 Glacier<br/>Deep Archive]
        D --> G[S3 Standard-IA]
        E --> H[Memory/Local]
    end

    style C fill:#ffcdd2
    style D fill:#fff9c4
    style E fill:#c8e6c9
```

| 戦略 | 対象 | 期待される削減率 |
|---|---|---|
| **ログレベルフィルタリング** | DEBUG/TRACE ログを破棄 | 40-60% |
| **サンプリング** | 高頻度イベント | 30-50% |
| **圧縮** | すべてのログ/メトリクス | 60-80% |
| **階層型ストレージ** | 古いデータ | 70-90% |
| **保持期間の最適化** | 低優先度データ | 50-70% |

---

## 7. 統合 Observability ダッシュボード

### 7.1 Grafana ベースの統合ダッシュボード設定

```yaml
# grafana-datasources.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: grafana-datasources
  namespace: monitoring
data:
  datasources.yaml: |
    apiVersion: 1
    datasources:
      # Prometheus - Metrics
      - name: Prometheus
        type: prometheus
        access: proxy
        url: http://prometheus-server:9090
        isDefault: true
        jsonData:
          httpMethod: POST
          exemplarTraceIdDestinations:
            - name: traceID
              datasourceUid: tempo

      # Loki - Logs
      - name: Loki
        type: loki
        access: proxy
        url: http://loki-gateway:80
        jsonData:
          derivedFields:
            - name: TraceID
              matcherRegex: '"traceId":"([a-f0-9]+)"'
              url: '$${__value.raw}'
              datasourceUid: tempo

      # Tempo - Traces
      - name: Tempo
        type: tempo
        access: proxy
        url: http://tempo-query-frontend:3100
        uid: tempo
        jsonData:
          httpMethod: GET
          tracesToLogs:
            datasourceUid: loki
            tags: ['service.name', 'pod']
          serviceMap:
            datasourceUid: prometheus
          nodeGraph:
            enabled: true
          lokiSearch:
            datasourceUid: loki
```

### 7.2 Log -> Metrics -> Trace の相関（Exemplars）

Exemplars は、トレース ID をメトリクスのデータポイントにリンクする機能です。

```yaml
# prometheus-exemplars-config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: prometheus-config
  namespace: monitoring
data:
  prometheus.yml: |
    global:
      scrape_interval: 15s
      # Enable Exemplars
      enable_features:
        - exemplar-storage

    scrape_configs:
      - job_name: 'application'
        kubernetes_sd_configs:
          - role: pod
        relabel_configs:
          - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
            regex: 'true'
            action: keep
```

アプリケーションからの Exemplars のエクスポート（Go の例）:

```go
// Adding Exemplars to Prometheus histograms
import (
    "github.com/prometheus/client_golang/prometheus"
    "go.opentelemetry.io/otel/trace"
)

var httpDuration = prometheus.NewHistogramVec(
    prometheus.HistogramOpts{
        Name:    "http_request_duration_seconds",
        Help:    "HTTP request duration",
        Buckets: prometheus.DefBuckets,
    },
    []string{"method", "path", "status"},
)

func recordMetric(ctx context.Context, method, path, status string, duration float64) {
    span := trace.SpanFromContext(ctx)
    traceID := span.SpanContext().TraceID().String()

    httpDuration.WithLabelValues(method, path, status).(prometheus.ExemplarObserver).
        ObserveWithExemplar(duration, prometheus.Labels{"traceID": traceID})
}
```

### 7.3 アラート戦略: アラート疲れの防止

```yaml
# alertmanager-config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: alertmanager-config
  namespace: monitoring
data:
  alertmanager.yml: |
    global:
      resolve_timeout: 5m

    # Routing rules
    route:
      receiver: 'default'
      group_by: ['alertname', 'namespace', 'service']
      group_wait: 30s
      group_interval: 5m
      repeat_interval: 4h

      routes:
        # Routing by severity
        - match:
            severity: critical
          receiver: 'critical-alerts'
          group_wait: 10s
          repeat_interval: 1h

        - match:
            severity: warning
          receiver: 'warning-alerts'
          group_wait: 1m
          repeat_interval: 4h

        # Suppress alerts outside business hours
        - match:
            severity: info
          receiver: 'info-alerts'
          mute_time_intervals:
            - off-hours

    # Alert inhibition rules
    inhibit_rules:
      # Suppress individual service alerts when cluster is down
      - source_match:
          alertname: ClusterDown
        target_match_re:
          alertname: '.+'
        equal: ['cluster']

      # Suppress Pod alerts when node is down
      - source_match:
          alertname: NodeDown
        target_match_re:
          alertname: 'Pod.*'
        equal: ['node']

    # Define off-hours
    time_intervals:
      - name: off-hours
        time_intervals:
          - weekdays: ['saturday', 'sunday']
          - times:
              - start_time: '00:00'
                end_time: '09:00'
              - start_time: '18:00'
                end_time: '24:00'

    receivers:
      - name: 'default'
        slack_configs:
          - channel: '#alerts-default'

      - name: 'critical-alerts'
        slack_configs:
          - channel: '#alerts-critical'
        pagerduty_configs:
          - service_key: '<pagerduty-key>'

      - name: 'warning-alerts'
        slack_configs:
          - channel: '#alerts-warning'

      - name: 'info-alerts'
        slack_configs:
          - channel: '#alerts-info'
```

### 7.4 SLO/SLI ベースのモニタリング

```yaml
# slo-recording-rules.yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: slo-rules
  namespace: monitoring
spec:
  groups:
    - name: slo.rules
      rules:
        # Availability SLI: Successful request ratio
        - record: sli:availability:ratio
          expr: |
            sum(rate(http_requests_total{status!~"5.."}[5m]))
            /
            sum(rate(http_requests_total[5m]))

        # Latency SLI: P99 < 500ms ratio
        - record: sli:latency:ratio
          expr: |
            sum(rate(http_request_duration_seconds_bucket{le="0.5"}[5m]))
            /
            sum(rate(http_request_duration_seconds_count[5m]))

        # Error budget burn rate (30-day basis)
        - record: slo:error_budget:remaining
          expr: |
            1 - (
              (1 - sli:availability:ratio)
              /
              (1 - 0.999)  # 99.9% SLO target
            )

    - name: slo.alerts
      rules:
        # Warning when 50% of error budget consumed
        - alert: ErrorBudgetBurnRateHigh
          expr: slo:error_budget:remaining < 0.5
          for: 5m
          labels:
            severity: warning
          annotations:
            summary: "More than 50% of error budget consumed"
            description: "Remaining error budget: {{ $value | humanizePercentage }}"

        # Critical when 80% of error budget consumed
        - alert: ErrorBudgetBurnRateCritical
          expr: slo:error_budget:remaining < 0.2
          for: 5m
          labels:
            severity: critical
          annotations:
            summary: "More than 80% of error budget consumed"
            description: "Remaining error budget: {{ $value | humanizePercentage }}"
```

---

## 8. 運用上の課題と解決策

### 8.1 急増するログ/メトリクスストレージコストへの対応

| 問題 | 原因 | 解決策 |
|---|---|---|
| ログコストの急増 | 過剰な DEBUG ログ | ログレベルフィルタリング、サンプリング |
| メトリクスのカーディナリティ爆発 | Pod UID、タイムスタンプラベル | ラベルのクリーンアップ、メトリクスの破棄 |
| トレースストレージコスト | 100% サンプリング | Tail Sampling を適用 |
| 長期保持コスト | すべてのデータに同一の保持期間 | 階層型ストレージ |

```yaml
# cost-optimization-config.yaml
# Fluent Bit log filtering
[FILTER]
    Name     grep
    Match    *
    Exclude  log ^.*DEBUG.*$
    Exclude  log ^.*TRACE.*$

# High-frequency log sampling (10%)
[FILTER]
    Name          throttle
    Match         kube.var.log.containers.nginx*
    Rate          10
    Window        60
    Print_Status  true
```

### 8.2 EKS Auto Mode ノードモニタリング

EKS Auto Mode ではノードが自動管理されるため、特別なモニタリング戦略が必要です。

```yaml
# auto-mode-monitoring.yaml
# Managed Node Pool monitoring
apiVersion: monitoring.coreos.com/v1
kind: PodMonitor
metadata:
  name: auto-mode-nodes
  namespace: monitoring
spec:
  selector:
    matchLabels:
      eks.amazonaws.com/managed: "true"
  namespaceSelector:
    any: true
  podMetricsEndpoints:
    - port: metrics
      interval: 30s
---
# Enable CloudWatch Container Insights
# Recommended for use with EKS Auto Mode
apiVersion: v1
kind: ConfigMap
metadata:
  name: cwagent-config
  namespace: amazon-cloudwatch
data:
  cwagentconfig.json: |
    {
      "logs": {
        "metrics_collected": {
          "kubernetes": {
            "cluster_name": "eks-auto-cluster",
            "metrics_collection_interval": 60
          }
        }
      }
    }
```

### 8.3 ツール間のデータ相関分析

```mermaid
sequenceDiagram
    participant User
    participant Grafana
    participant Prometheus
    participant Loki
    participant Tempo

    User->>Grafana: Investigate slow API response
    Grafana->>Prometheus: Query P99 latency
    Prometheus-->>Grafana: Metrics + Exemplar (traceID)

    Grafana->>Tempo: Lookup trace by traceID
    Tempo-->>Grafana: Full request flow

    Note over Grafana: Identify bottleneck service

    Grafana->>Loki: Query service logs<br/>(traceID filter)
    Loki-->>Grafana: Related logs

    Grafana-->>User: Unified analysis results
```

### 8.4 大規模環境でのモニタリングシステムパフォーマンスの維持

```yaml
# high-scale-prometheus.yaml
apiVersion: monitoring.coreos.com/v1
kind: Prometheus
metadata:
  name: prometheus
  namespace: monitoring
spec:
  replicas: 2
  retention: 7d
  retentionSize: 100GB

  # Sharding for load distribution
  shards: 3

  resources:
    requests:
      cpu: 2
      memory: 8Gi
    limits:
      cpu: 4
      memory: 16Gi

  # Offload to external storage
  remoteWrite:
    - url: "http://victoriametrics:8428/api/v1/write"
      queueConfig:
        capacity: 10000
        maxShards: 30
        maxSamplesPerSend: 5000

  # Query performance optimization
  queryLogFile: /prometheus/query.log

  additionalArgs:
    # Query concurrency limit
    - name: query.max-concurrency
      value: "20"
    # Query timeout
    - name: query.timeout
      value: "2m"
```

### 8.5 高可用性 Observability スタックの設定

```mermaid
graph TB
    subgraph "Data Collection Layer (HA)"
        FB1[Fluent Bit<br/>Node 1]
        FB2[Fluent Bit<br/>Node 2]
        FB3[Fluent Bit<br/>Node N]
    end

    subgraph "Collector Layer (HA)"
        OTEL1[OTel Collector 1]
        OTEL2[OTel Collector 2]
        LB[Load Balancer]
    end

    subgraph "Storage Layer (HA)"
        subgraph "Loki HA"
            LOKI1[Loki Write 1]
            LOKI2[Loki Write 2]
            LOKI3[Loki Read 1]
            LOKI4[Loki Read 2]
        end

        subgraph "VictoriaMetrics HA"
            VM1[vminsert 1]
            VM2[vminsert 2]
            VM3[vmselect 1]
            VM4[vmselect 2]
            VMS[vmstorage x3]
        end
    end

    subgraph "Shared Storage"
        S3[(S3 Bucket)]
    end

    FB1 --> LB
    FB2 --> LB
    FB3 --> LB
    LB --> OTEL1
    LB --> OTEL2

    OTEL1 --> LOKI1
    OTEL2 --> LOKI2
    OTEL1 --> VM1
    OTEL2 --> VM2

    LOKI1 --> S3
    LOKI2 --> S3
    VM1 --> VMS
    VM2 --> VMS
```

---

## 9. ベストプラクティスと次のステップ

### 9.1 段階的な導入戦略

```mermaid
graph LR
    subgraph "Phase 1: Basic"
        A1[CloudWatch Logs]
        A2[CloudWatch Metrics]
        A3[Container Insights]
    end

    subgraph "Phase 2: Intermediate"
        B1[Prometheus + Grafana]
        B2[Fluent Bit + Loki]
        B3[X-Ray Tracing]
    end

    subgraph "Phase 3: Advanced"
        C1[VictoriaMetrics/AMP]
        C2[OpenTelemetry]
        C3[eBPF Monitoring]
        C4[Cost Monitoring]
    end

    A1 --> B2
    A2 --> B1
    A3 --> B3

    B1 --> C1
    B2 --> C2
    B3 --> C2
    C1 --> C4
    C2 --> C3
```

| フェーズ | コンポーネント | 期間 | コスト | 運用の複雑さ |
|---|---|---|---|---|
| **フェーズ 1（基本）** | CloudWatch ベース | 1-2日 | 低 | 低 |
| **フェーズ 2（中級）** | Grafana スタック | 1-2週間 | 中 | 中 |
| **フェーズ 3（上級）** | OpenTelemetry + eBPF | 2-4週間 | 高 | 高 |

### 9.2 コスト対効果分析

| ツールの組み合わせ | 推定月額コスト（100ノード） | 機能カバレッジ | ROI |
|---|---|---|---|
| CloudWatch フル | $500-1,000 | 基本 | 低 |
| Prometheus + Loki + Grafana | $200-400（インフラ） | 中級 | 中 |
| AMP + Tempo + eBPF | $300-600 | 上級 | 高 |
| 商用ソリューション（Datadog など） | $2,000-5,000 | 完全 | さまざま |

### 9.3 チェックリスト

**Observability 実装チェックリスト:**

- [ ] Logging、Metrics、Tracing の3つの柱すべてを実装する
- [ ] 柱間のデータ相関を設定する
- [ ] カーディナリティ管理ポリシーを確立する
- [ ] サンプリング戦略を定義して適用する
- [ ] コストモニタリングツールをデプロイする
- [ ] アラートルールを最適化する（アラート疲れを防止）
- [ ] SLO/SLI を定義してダッシュボードを設定する
- [ ] 長期ストレージ戦略を確立する
- [ ] 高可用性設定を完了する
- [ ] ドキュメント作成とチームトレーニングを行う

### 9.4 関連ドキュメントとクイズ

**関連ドキュメント:**

- [Prometheus 運用ガイド](./metrics/01-prometheus.md)
- [Grafana ダッシュボード設定](./grafana/README.md)

**関連クイズ:**

- [Observability 最適化クイズ](../quizzes/observability/09-observability-optimization-quiz.md)

---

## 参考資料

- [OpenTelemetry 公式ドキュメント](https://opentelemetry.io/docs/)
- [Grafana Loki ドキュメント](https://grafana.com/docs/loki/latest/)
- [Prometheus Operator](https://prometheus-operator.dev/)
- [AWS Observability ベストプラクティス](https://aws-observability.github.io/observability-best-practices/)
- [OpenCost プロジェクト](https://www.opencost.io/)
- [eBPF.io](https://ebpf.io/)
