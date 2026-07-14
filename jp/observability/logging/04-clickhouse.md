# ClickHouse

> **最終更新**: June 30, 2026

ClickHouse は、OLAP（Online Analytical Processing）ワークロード向けに最適化されたオープンソースのカラムナデータベースです。大規模なログ分析に優れたクエリ性能と圧縮率を提供します。

## 目次

1. [概要](04-clickhouse.md#overview)
2. [アーキテクチャ](04-clickhouse.md#architecture)
3. [Kubernetes Deployment](04-clickhouse.md#kubernetes-deployment)
4. [ログ取り込みパイプライン](04-clickhouse.md#log-ingestion-pipeline)
5. [SQL クエリ](04-clickhouse.md#sql-queries)
6. [Grafana 統合](04-clickhouse.md#grafana-integration)
7. [パフォーマンス最適化](04-clickhouse.md#performance-optimization)
8. [S3 アーカイブと長期保持](04-clickhouse.md#s3-archiving-and-long-term-retention)
9. [HyperDX（ClickHouse ネイティブビューア）](04-clickhouse.md#hyperdx-clickhouse-native-viewer)

***

## 概要

### ClickHouse の機能

| 機能                 | 説明                                       |
| ----------------------- | ------------------------------------------------- |
| **カラムナストレージ**    | 分析クエリ向けに最適化されたデータストレージ     |
| **高圧縮**    | ストレージコストを削減する 10:1 以上の圧縮率 |
| **高速クエリ**        | 数十億行を数秒でスキャン                  |
| **SQL サポート**         | 標準 SQL でクエリを作成                     |
| **水平スケーリング**  | シャーディングによる分散処理               |
| **リアルタイム取り込み** | 1 秒あたり数百万行を取り込み                |

### ログ分析に ClickHouse を選ぶ理由

```
+-------------------------------------------------------------+
|                    Log Analytics Requirements                |
+-------------------------------------------------------------+
|  [x] Large-scale data (TB+ per day)                         |
|  [x] Complex aggregation queries (GROUP BY, JOIN)           |
|  [x] SQL-based analysis                                     |
|  [x] Low storage costs                                      |
|  [x] Fast query response (seconds)                          |
|  [x] BI tool integration                                    |
+-------------------------------------------------------------+
                          |
              ClickHouse is a suitable choice
```

### 他のソリューションとの比較

| 項目                       | ClickHouse          | Elasticsearch  | Loki        |
| -------------------------- | ------------------- | -------------- | ----------- |
| **クエリ言語**         | SQL                 | Query DSL      | LogQL       |
| **ストレージ方式**         | カラムナ            | ドキュメントベース | チャンクベース |
| **圧縮率**      | 非常に高い           | 低い            | 高い        |
| **全文検索**       | 制限あり             | 優れている      | 制限あり     |
| **集計クエリ**    | 優れている           | 良好            | 基本的       |
| **学習曲線**         | SQL に慣れていれば低い | 中程度         | 低い         |
| **運用の複雑さ** | 中程度              | 高い           | 低い         |

***

## アーキテクチャ

### ClickHouse Cluster アーキテクチャ

```mermaid
flowchart TB
    subgraph Collectors["Collectors"]
        FB[FluentBit]
        VECTOR[Vector]
        OTEL[OTEL Collector]
    end

    subgraph Kafka["Message Queue (Optional)"]
        KAFKA_TOPIC[Kafka Topic]
    end

    subgraph ClickHouse["ClickHouse Cluster"]
        subgraph Shard1["Shard 1"]
            R1_1[Replica 1]
            R1_2[Replica 2]
        end
        subgraph Shard2["Shard 2"]
            R2_1[Replica 1]
            R2_2[Replica 2]
        end
        subgraph Shard3["Shard 3"]
            R3_1[Replica 1]
            R3_2[Replica 2]
        end
        ZK[ZooKeeper/ClickHouse Keeper]
    end

    subgraph Storage["Storage"]
        S3[(S3 - Cold Data)]
        EBS[(EBS - Hot Data)]
    end

    subgraph Visualization["Visualization"]
        GRAFANA[Grafana]
        SUPERSET[Apache Superset]
    end

    FB --> KAFKA_TOPIC
    VECTOR --> KAFKA_TOPIC
    OTEL --> KAFKA_TOPIC

    KAFKA_TOPIC --> R1_1
    KAFKA_TOPIC --> R2_1
    KAFKA_TOPIC --> R3_1

    R1_1 <--> R1_2
    R2_1 <--> R2_2
    R3_1 <--> R3_2

    ZK --> Shard1
    ZK --> Shard2
    ZK --> Shard3

    R1_1 --> EBS
    R2_1 --> EBS
    R3_1 --> EBS

    EBS --> S3

    GRAFANA --> R1_1
    GRAFANA --> R2_1
    SUPERSET --> R3_1

    classDef collector fill:#4CAF50,stroke:#333,color:white
    classDef queue fill:#FF9800,stroke:#333,color:white
    classDef ch fill:#FFEB3B,stroke:#333
    classDef storage fill:#2196F3,stroke:#333,color:white
    classDef viz fill:#9C27B0,stroke:#333,color:white

    class FB,VECTOR,OTEL collector
    class KAFKA_TOPIC queue
    class R1_1,R1_2,R2_1,R2_2,R3_1,R3_2,ZK ch
    class S3,EBS storage
    class GRAFANA,SUPERSET viz
```

### データフロー

```mermaid
sequenceDiagram
    participant App as Application
    participant FB as FluentBit
    participant Kafka as Kafka (Optional)
    participant CH as ClickHouse
    participant S3 as S3 (Cold)

    App->>FB: Generate logs
    FB->>Kafka: Buffering
    Kafka->>CH: Kafka Engine ingestion
    CH->>CH: Store in MergeTree table

    Note over CH: Based on TTL policy

    CH->>S3: Move cold data
```

***

## Kubernetes Deployment

### ClickHouse Operator のインストール

```bash
# Install Altinity ClickHouse Operator
kubectl apply -f https://raw.githubusercontent.com/Altinity/clickhouse-operator/master/deploy/operator/clickhouse-operator-install-bundle.yaml

# Verify installation
kubectl get pods -n kube-system | grep clickhouse
```

### ClickHouse Cluster の定義

```yaml
# clickhouse-cluster.yaml
apiVersion: "clickhouse.altinity.com/v1"
kind: "ClickHouseInstallation"
metadata:
  name: logs-cluster
  namespace: clickhouse
spec:
  configuration:
    zookeeper:
      nodes:
        - host: zookeeper.clickhouse.svc.cluster.local
          port: 2181
    clusters:
      - name: logs
        layout:
          shardsCount: 3
          replicasCount: 2
        templates:
          podTemplate: clickhouse-pod
          volumeClaimTemplate: storage
          serviceTemplate: svc-template

    settings:
      # Log analytics optimized settings
      max_concurrent_queries: 100
      max_connections: 4096
      max_server_memory_usage_to_ram_ratio: 0.9
      background_pool_size: 16
      background_schedule_pool_size: 16

    files:
      config.d/storage.xml: |
        <clickhouse>
          <storage_configuration>
            <disks>
              <default>
                <keep_free_space_bytes>10737418240</keep_free_space_bytes>
              </default>
              <s3>
                <type>s3</type>
                <endpoint>https://s3.ap-northeast-2.amazonaws.com/my-clickhouse-data/</endpoint>
                <use_environment_credentials>true</use_environment_credentials>
              </s3>
            </disks>
            <policies>
              <tiered>
                <volumes>
                  <hot>
                    <disk>default</disk>
                  </hot>
                  <cold>
                    <disk>s3</disk>
                  </cold>
                </volumes>
                <move_factor>0.2</move_factor>
              </tiered>
            </policies>
          </storage_configuration>
        </clickhouse>

    users:
      admin/password: "secure-password-here"
      admin/networks/ip: "::/0"
      admin/profile: default
      admin/quota: default

      readonly/password: "readonly-password"
      readonly/networks/ip: "::/0"
      readonly/profile: readonly
      readonly/quota: default

    profiles:
      readonly/readonly: 1
      default/max_memory_usage: 10000000000
      default/max_execution_time: 300

  templates:
    podTemplates:
      - name: clickhouse-pod
        spec:
          containers:
            - name: clickhouse
              image: clickhouse/clickhouse-server:24.1
              resources:
                requests:
                  cpu: "2"
                  memory: "8Gi"
                limits:
                  cpu: "4"
                  memory: "16Gi"
              ports:
                - name: http
                  containerPort: 8123
                - name: tcp
                  containerPort: 9000
                - name: interserver
                  containerPort: 9009
          affinity:
            podAntiAffinity:
              preferredDuringSchedulingIgnoredDuringExecution:
                - weight: 100
                  podAffinityTerm:
                    labelSelector:
                      matchLabels:
                        clickhouse.altinity.com/cluster: logs
                    topologyKey: topology.kubernetes.io/zone

    volumeClaimTemplates:
      - name: storage
        spec:
          accessModes:
            - ReadWriteOnce
          storageClassName: gp3
          resources:
            requests:
              storage: 500Gi

    serviceTemplates:
      - name: svc-template
        spec:
          ports:
            - name: http
              port: 8123
            - name: tcp
              port: 9000
          type: ClusterIP
```

### ZooKeeper（または ClickHouse Keeper）の Deployment

```yaml
# zookeeper.yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: zookeeper
  namespace: clickhouse
spec:
  serviceName: zookeeper
  replicas: 3
  selector:
    matchLabels:
      app: zookeeper
  template:
    metadata:
      labels:
        app: zookeeper
    spec:
      containers:
        - name: zookeeper
          image: zookeeper:3.8
          ports:
            - containerPort: 2181
              name: client
            - containerPort: 2888
              name: follower
            - containerPort: 3888
              name: election
          env:
            - name: ZOO_MY_ID
              valueFrom:
                fieldRef:
                  fieldPath: metadata.name
            - name: ZOO_SERVERS
              value: "server.1=zookeeper-0.zookeeper:2888:3888;2181 server.2=zookeeper-1.zookeeper:2888:3888;2181 server.3=zookeeper-2.zookeeper:2888:3888;2181"
          resources:
            requests:
              cpu: 500m
              memory: 1Gi
            limits:
              cpu: 1
              memory: 2Gi
          volumeMounts:
            - name: data
              mountPath: /data
  volumeClaimTemplates:
    - metadata:
        name: data
      spec:
        accessModes: ["ReadWriteOnce"]
        storageClassName: gp3
        resources:
          requests:
            storage: 20Gi
---
apiVersion: v1
kind: Service
metadata:
  name: zookeeper
  namespace: clickhouse
spec:
  ports:
    - port: 2181
      name: client
  clusterIP: None
  selector:
    app: zookeeper
```

***

## ログ取り込みパイプライン

### Buffer → Store → Distributed の 3 層設計

> **インタラクティブな可視化**: [ClickHouse 3-Tier Pipeline Animation](https://github.com/Atom-oh/kubernetes-docs/blob/main/assets/clickhouse-3tier-pipeline.html) で、Buffer → Store → Distributed のデータフローを視覚的に確認できます。

大規模なログ環境（1 日あたり TB 以上）では、INSERT リクエストの集中により多数の小さな Part が作成され、Merge のオーバーヘッドが急増します。Buffer engine を使用する 3 層設計がこの問題を解決します。

```
Buffer Table (Memory)  →  Store Table (ReplicatedMergeTree)  →  Distributed Table (Query Router)
    Receives INSERTs          Actual data storage                   Client query entry point
    Accumulates in memory     Flushes as large Parts                Distributes across shards
```

**Buffer Engine の役割:**

* INSERT リクエストをメモリに蓄積し、条件（時間／行数／バイト数）を満たすと Store テーブルへフラッシュする
* ピーク時の多数の小さな INSERT を大きな Part にバッチ化し、Merge のオーバーヘッドを最小化する
* Part 数の急増による `Too many parts` エラーを防止する

```sql
-- 1. Store table (actual data storage)
CREATE TABLE logs.store_application_logs ON CLUSTER logs
(
    -- Schema same as application_logs
    ...
)
ENGINE = ReplicatedMergeTree('/clickhouse/tables/{shard}/logs.store_application_logs', '{replica}')
PARTITION BY (toYYYYMMDD(timestamp) * 100 + toHour(timestamp))
ORDER BY (namespace, service, timestamp)
TTL timestamp + INTERVAL 90 DAY
SETTINGS
    index_granularity = 8192,
    ttl_only_drop_parts = 1;

-- 2. Buffer table (receives INSERTs)
CREATE TABLE logs.buffer_application_logs AS logs.store_application_logs
ENGINE = Buffer(
    'logs',                    -- database
    'store_application_logs',  -- target table
    16,                        -- num_layers (parallel buffers)
    1,                         -- min_time (seconds) - flush after minimum 1s
    30,                        -- max_time (seconds) - flush after maximum 30s
    500000,                    -- min_rows
    5000000,                   -- max_rows
    500000000,                 -- min_bytes (~500MB)
    1000000000                 -- max_bytes (~1GB)
);

-- 3. Distributed table (query entry point)
CREATE TABLE logs.application_logs_distributed ON CLUSTER logs
AS logs.store_application_logs
ENGINE = Distributed(logs, logs, store_application_logs, rand());
```

> **注記**: Buffer テーブルのデータはメモリ上に存在するため、ClickHouse が異常終了するとフラッシュされていないデータが失われる可能性があります。Kafka と併用する場合は、再処理によってデータを復旧できます。

### ログテーブルスキーマ

```sql
-- Create log table (production-optimized version)
CREATE TABLE IF NOT EXISTS logs.application_logs ON CLUSTER logs
(
    -- DoubleDelta CODEC: optimal compression for time-series timestamps
    timestamp DateTime64(3) CODEC(DoubleDelta, LZ4),
    date Date DEFAULT toDate(timestamp),
    level LowCardinality(String),
    message String,
    logger String,

    -- Kubernetes metadata
    namespace LowCardinality(String),
    pod_name String,
    container_name LowCardinality(String),
    node_name LowCardinality(String),

    -- Trace information
    trace_id String,
    span_id String,

    -- Additional fields
    service LowCardinality(String),
    environment LowCardinality(String),

    -- Materialized columns: auto-extract frequently used fields from JSON at INSERT time
    -- Enables direct column access without JSON parsing at query time → major performance gain
    app_name String MATERIALIZED JSONExtractString(raw_json, 'app_name'),
    error_code String MATERIALIZED JSONExtractString(raw_json, 'error_code'),
    response_time Float64 MATERIALIZED JSONExtractFloat(raw_json, 'response_time_ms'),

    -- JSON raw (optional)
    raw_json String CODEC(ZSTD(3)),

    INDEX idx_trace_id trace_id TYPE bloom_filter GRANULARITY 4,
    INDEX idx_message message TYPE tokenbf_v1(10240, 3, 0) GRANULARITY 4
)
ENGINE = ReplicatedMergeTree('/clickhouse/tables/{shard}/logs.application_logs', '{replica}')
-- Hourly partitioning: finer granularity than monthly (toYYYYMM)
-- → Enables whole-Part deletion for TTL, more precise data management
PARTITION BY (toYYYYMMDD(date) * 100 + toHour(timestamp))
ORDER BY (namespace, service, timestamp)
TTL date + INTERVAL 90 DAY
SETTINGS
    index_granularity = 8192,
    -- Drop whole Parts: dramatically more efficient TTL processing vs row-level deletion
    ttl_only_drop_parts = 1;

-- Create distributed table
CREATE TABLE IF NOT EXISTS logs.application_logs_distributed ON CLUSTER logs
AS logs.application_logs
ENGINE = Distributed(logs, logs, application_logs, rand());
```

### Vector による取り込み

```yaml
# vector-config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: vector-config
  namespace: logging
data:
  vector.yaml: |
    sources:
      kubernetes_logs:
        type: kubernetes_logs
        auto_partial_merge: true
        ignore_older_secs: 600

    transforms:
      parse_json:
        type: remap
        inputs:
          - kubernetes_logs
        source: |
          # Attempt JSON parsing
          parsed, err = parse_json(.message)
          if err == null {
            . = merge(., parsed)
          }

          # Normalize fields
          .timestamp = .timestamp || now()
          .level = .level || "INFO"
          .namespace = .kubernetes.pod_namespace
          .pod_name = .kubernetes.pod_name
          .container_name = .kubernetes.container_name
          .node_name = .kubernetes.pod_node_name
          .service = .kubernetes.pod_labels.app || "unknown"
          .environment = .kubernetes.pod_labels.environment || "unknown"

      filter_noise:
        type: filter
        inputs:
          - parse_json
        condition: |
          !includes(["kube-system", "kube-public"], .namespace) &&
          !match(.message, r'healthcheck|readiness|liveness')

    sinks:
      clickhouse:
        type: clickhouse
        inputs:
          - filter_noise
        endpoint: http://clickhouse.clickhouse.svc.cluster.local:8123
        database: logs
        table: application_logs
        auth:
          strategy: basic
          user: admin
          password: ${CLICKHOUSE_PASSWORD}
        encoding:
          timestamp_format: unix
        batch:
          max_bytes: 10485760
          max_events: 10000
          timeout_secs: 5
        compression: gzip
        healthcheck:
          enabled: true
```

### FluentBit による取り込み

```yaml
# fluent-bit-clickhouse.yaml
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
        Merge_Log           On
        K8S-Logging.Parser  On

    [FILTER]
        Name    modify
        Match   *
        Add     environment production
        Add     cluster_name my-cluster

    [OUTPUT]
        Name          http
        Match         *
        Host          clickhouse.clickhouse.svc.cluster.local
        Port          8123
        URI           /?query=INSERT%20INTO%20logs.application_logs%20FORMAT%20JSONEachRow
        Format        json_lines
        json_date_key timestamp
        json_date_format iso8601
        Header        Authorization Basic YWRtaW46cGFzc3dvcmQ=

  parsers.conf: |
    [PARSER]
        Name        docker
        Format      json
        Time_Key    time
        Time_Format %Y-%m-%dT%H:%M:%S.%L
        Time_Keep   On
```

### Kafka によるバッファリング（大規模環境）

```sql
-- Kafka engine table
CREATE TABLE IF NOT EXISTS logs.kafka_logs ON CLUSTER logs
(
    timestamp DateTime64(3),
    level String,
    message String,
    namespace String,
    pod_name String,
    container_name String,
    service String,
    raw_json String
)
ENGINE = Kafka()
SETTINGS
    kafka_broker_list = 'kafka.kafka.svc.cluster.local:9092',
    kafka_topic_list = 'logs',
    kafka_group_name = 'clickhouse-consumer',
    kafka_format = 'JSONEachRow',
    kafka_num_consumers = 3,
    kafka_max_block_size = 65536;

-- Materialized View to store in actual table
CREATE MATERIALIZED VIEW IF NOT EXISTS logs.kafka_to_logs ON CLUSTER logs
TO logs.application_logs
AS SELECT
    timestamp,
    toDate(timestamp) as date,
    level,
    message,
    '' as logger,
    namespace,
    pod_name,
    container_name,
    '' as node_name,
    '' as trace_id,
    '' as span_id,
    service,
    'production' as environment,
    raw_json
FROM logs.kafka_logs;
```

***

## SQL クエリ

### 基本クエリ

```sql
-- Query recent error logs
SELECT
    timestamp,
    namespace,
    service,
    message
FROM logs.application_logs_distributed
WHERE level = 'ERROR'
  AND timestamp >= now() - INTERVAL 1 HOUR
ORDER BY timestamp DESC
LIMIT 100;

-- Errors by service
SELECT
    service,
    count() as error_count,
    uniq(pod_name) as affected_pods
FROM logs.application_logs_distributed
WHERE level = 'ERROR'
  AND date = today()
GROUP BY service
ORDER BY error_count DESC;

-- Log volume by time
SELECT
    toStartOfHour(timestamp) as hour,
    count() as log_count,
    sum(length(message)) as total_bytes
FROM logs.application_logs_distributed
WHERE date >= today() - 7
GROUP BY hour
ORDER BY hour;
```

### 高度な分析クエリ

```sql
-- Error rate trend (5-minute intervals)
SELECT
    toStartOfFiveMinutes(timestamp) as time_bucket,
    service,
    countIf(level = 'ERROR') as errors,
    count() as total,
    round(errors / total * 100, 2) as error_rate
FROM logs.application_logs_distributed
WHERE date = today()
  AND namespace = 'production'
GROUP BY time_bucket, service
HAVING total > 100
ORDER BY time_bucket, error_rate DESC;

-- Error message pattern analysis
SELECT
    extractAll(message, 'Exception|Error|Failed|Timeout')[1] as error_type,
    count() as occurrences,
    groupArray(10)(message) as sample_messages
FROM logs.application_logs_distributed
WHERE level = 'ERROR'
  AND date >= today() - 7
GROUP BY error_type
ORDER BY occurrences DESC
LIMIT 20;

-- Pod restart pattern detection
SELECT
    namespace,
    pod_name,
    min(timestamp) as first_seen,
    max(timestamp) as last_seen,
    count() as log_count,
    countIf(message LIKE '%CrashLoopBackOff%' OR message LIKE '%OOMKilled%') as crash_indicators
FROM logs.application_logs_distributed
WHERE date >= today() - 1
GROUP BY namespace, pod_name
HAVING crash_indicators > 0
ORDER BY crash_indicators DESC;

-- Slow request analysis (extract response_time from JSON logs)
SELECT
    service,
    quantile(0.50)(JSONExtractFloat(raw_json, 'response_time_ms')) as p50,
    quantile(0.90)(JSONExtractFloat(raw_json, 'response_time_ms')) as p90,
    quantile(0.99)(JSONExtractFloat(raw_json, 'response_time_ms')) as p99,
    count() as request_count
FROM logs.application_logs_distributed
WHERE date = today()
  AND JSONHas(raw_json, 'response_time_ms')
GROUP BY service
ORDER BY p99 DESC;

-- Distributed tracing by trace_id
SELECT
    timestamp,
    service,
    pod_name,
    span_id,
    level,
    message
FROM logs.application_logs_distributed
WHERE trace_id = 'abc123def456'
ORDER BY timestamp;
```

### リアルタイムダッシュボードクエリ

```sql
-- Real-time log stream (live tailing)
SELECT
    timestamp,
    level,
    namespace,
    service,
    substring(message, 1, 200) as message_preview
FROM logs.application_logs_distributed
WHERE timestamp >= now() - INTERVAL 5 MINUTE
ORDER BY timestamp DESC
LIMIT 100;

-- Service status summary
SELECT
    service,
    countIf(timestamp >= now() - INTERVAL 5 MINUTE) as logs_5m,
    countIf(level = 'ERROR' AND timestamp >= now() - INTERVAL 5 MINUTE) as errors_5m,
    countIf(level = 'ERROR' AND timestamp >= now() - INTERVAL 1 HOUR) as errors_1h
FROM logs.application_logs_distributed
WHERE date = today()
GROUP BY service
ORDER BY errors_5m DESC;
```

***

## Grafana 統合

### ClickHouse データソースのセットアップ

```yaml
# grafana-datasource.yaml
apiVersion: 1
datasources:
  - name: ClickHouse
    type: grafana-clickhouse-datasource
    url: http://clickhouse.clickhouse.svc.cluster.local:8123
    jsonData:
      defaultDatabase: logs
      dialTimeout: 10s
      queryTimeout: 300s
      validateSql: true
      protocol: http
    secureJsonData:
      username: readonly
      password: ${CLICKHOUSE_READONLY_PASSWORD}
```

### Grafana ダッシュボードパネル

```json
{
  "panels": [
    {
      "title": "Log Volume",
      "type": "timeseries",
      "datasource": "ClickHouse",
      "targets": [
        {
          "rawSql": "SELECT toStartOfMinute(timestamp) as time, count() as count FROM logs.application_logs_distributed WHERE $__timeFilter(timestamp) GROUP BY time ORDER BY time",
          "format": "time_series"
        }
      ]
    },
    {
      "title": "Error Rate by Service",
      "type": "barchart",
      "datasource": "ClickHouse",
      "targets": [
        {
          "rawSql": "SELECT service, countIf(level='ERROR') as errors, count() as total, round(errors/total*100, 2) as error_rate FROM logs.application_logs_distributed WHERE $__timeFilter(timestamp) GROUP BY service ORDER BY error_rate DESC LIMIT 10",
          "format": "table"
        }
      ]
    },
    {
      "title": "Log Stream",
      "type": "logs",
      "datasource": "ClickHouse",
      "targets": [
        {
          "rawSql": "SELECT timestamp as time, level, concat(namespace, '/', service) as labels, message as line FROM logs.application_logs_distributed WHERE $__timeFilter(timestamp) ORDER BY timestamp DESC LIMIT 500",
          "format": "logs"
        }
      ]
    }
  ]
}
```

### アラートルール

```yaml
# clickhouse-alert-rules.yaml
apiVersion: 1
groups:
  - name: clickhouse-logs
    rules:
      - alert: HighErrorRate
        expr: |
          clickhouse_custom_query{query="SELECT countIf(level='ERROR')/count()*100 FROM logs.application_logs_distributed WHERE timestamp >= now() - INTERVAL 5 MINUTE"} > 5
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High error rate detected"
          description: "Error rate is above 5% in the last 5 minutes"

      - alert: LogIngestionStopped
        expr: |
          clickhouse_custom_query{query="SELECT count() FROM logs.application_logs_distributed WHERE timestamp >= now() - INTERVAL 5 MINUTE"} == 0
        for: 10m
        labels:
          severity: critical
        annotations:
          summary: "Log ingestion stopped"
          description: "No logs received in the last 10 minutes"
```

***

## HyperDX（ClickHouse ネイティブビューア）

HyperDX は ClickHouse を直接クエリするネイティブログビューアです。Grafana や Signoz とは異なり、ClickHouse のカラムナストレージ構造を直接活用することで、フィールド固有の検索に高いパフォーマンスを提供します。

### 主な利点

| 機能                   | 説明                                                            |
| ------------------------- | ---------------------------------------------------------------------- |
| **フィールド固有検索** | `ServiceName:payment` 形式の検索は LIKE クエリより 20 倍以上高速 |
| **ClickHouse ネイティブ**     | 別個のインデックスレイヤーなしで ClickHouse を直接クエリする           |
| **自動スキーマ検出** | Buffer/Store/View 分離構造を自動的に認識する        |
| **OTEL 互換**       | OpenTelemetry ログスキーマをネイティブにサポートする                            |

### ログビューアの比較

| 機能                    | Grafana         | Signoz            | HyperDX         |
| -------------------------- | --------------- | ----------------- | --------------- |
| **ClickHouse ネイティブ**      | Plugin が必要 | 独自スキーマを強制 | ネイティブ          |
| **フィールド検索速度**     | 良好            | 良好              | 優れている（20 倍） |
| **カスタムスキーマ**          | サポート        | 制限あり           | 完全サポート    |
| **Buffer/Store 構造** | 手動設定   | 非対応     | 自動検出   |
| **Deployment**             | スタンドアロン      | スタンドアロン        | スタンドアロン        |
| **ライセンス**                | AGPL-3.0        | カスタムライセンス    | MIT             |

> **Signoz の制限**: Signoz は独自のスキーマを強制するため、Buffer → Store → Distributed の 3 層構造やカスタム Materialized カラムを使用する環境では制約が生じます。

***

## パフォーマンス最適化

### テーブル設計の最適化

```sql
-- Optimized table design
CREATE TABLE logs.optimized_logs
(
    -- Place frequently filtered columns first
    timestamp DateTime64(3),
    date Date DEFAULT toDate(timestamp),

    -- LowCardinality for low cardinality columns
    level LowCardinality(String),
    namespace LowCardinality(String),
    service LowCardinality(String),
    environment LowCardinality(String) DEFAULT 'production',

    -- Regular columns
    message String,
    pod_name String,

    -- Compression settings
    raw_json String CODEC(ZSTD(3))
)
ENGINE = MergeTree()
-- Sort key matching query patterns
PARTITION BY toYYYYMM(date)
ORDER BY (namespace, service, level, timestamp)
-- TTL settings
TTL date + INTERVAL 30 DAY DELETE,
    date + INTERVAL 7 DAY TO VOLUME 'cold'
SETTINGS
    index_granularity = 8192,
    min_bytes_for_wide_part = 10485760,
    min_rows_for_wide_part = 10000;
```

### Parts の最適化

ClickHouse の MergeTree engine は INSERT 時に Part を作成し、バックグラウンドでマージします。Part のサイズと数のバランスが、クエリ性能とシステムの安定性を決定します。

**Part サイズのトレードオフ:**

| Part の特性   | 大容量 + 少数の Parts       | 小容量 + 多数の Parts      |
| --------------------- | ---------------------------- | ---------------------------- |
| **Merge のオーバーヘッド**    | マージ中にメモリが急増   | 頻繁なマージ、CPU 負荷    |
| **クエリ性能** | スキャンする Parts が少ない = 高速 | Part を開くオーバーヘッドが増加 |
| **INSERT への影響**     | 大きなバッチが必要         | 小さなバッチが可能       |
| **リスク**              | OOM の可能性              | `Too many parts` エラー       |

**運用上の推奨事項:**

| 項目                | 推奨値              |
| ------------------- | ------------------------------ |
| パーティションあたりの Parts | \~20 以下                  |
| Part あたりのサイズ       | 2～3GB                          |
| アクティブなパーティション   | 時間単位のパーティショニングで 24～48 |

**モニタリングクエリ:**

```sql
-- Check Part count and size per partition
SELECT
    database,
    table,
    partition,
    count() AS part_count,
    formatReadableSize(sum(bytes_on_disk)) AS total_size,
    formatReadableSize(avg(bytes_on_disk)) AS avg_part_size,
    min(modification_time) AS oldest_part,
    max(modification_time) AS newest_part
FROM system.parts
WHERE active = 1
  AND database = 'logs'
GROUP BY database, table, partition
ORDER BY part_count DESC
LIMIT 20;

-- Detect Too many parts warnings
SELECT
    database,
    table,
    partition,
    count() AS part_count
FROM system.parts
WHERE active = 1
GROUP BY database, table, partition
HAVING part_count > 300
ORDER BY part_count DESC;
```

### クエリの最適化

```sql
-- Use PREWHERE (filter optimization)
SELECT *
FROM logs.application_logs_distributed
PREWHERE date = today()
WHERE level = 'ERROR'
  AND namespace = 'production'
LIMIT 100;

-- Use WITH clause instead of subqueries
WITH error_services AS (
    SELECT service
    FROM logs.application_logs_distributed
    WHERE level = 'ERROR'
      AND date = today()
    GROUP BY service
    HAVING count() > 100
)
SELECT
    l.service,
    count() as log_count,
    countIf(level = 'ERROR') as error_count
FROM logs.application_logs_distributed l
WHERE l.service IN (SELECT service FROM error_services)
  AND l.date = today()
GROUP BY l.service;

-- Sampling for fast large-scale analysis
SELECT
    service,
    count() * 10 as estimated_count  -- 10% sample
FROM logs.application_logs_distributed
SAMPLE 0.1
WHERE date >= today() - 7
GROUP BY service;
```

### システム設定の最適化

```xml
<!-- config.d/performance.xml -->
<clickhouse>
    <!-- Query processing -->
    <max_threads>16</max_threads>
    <max_memory_usage>10000000000</max_memory_usage>
    <max_bytes_before_external_group_by>5000000000</max_bytes_before_external_group_by>
    <max_bytes_before_external_sort>5000000000</max_bytes_before_external_sort>

    <!-- Merge settings -->
    <background_pool_size>16</background_pool_size>
    <background_schedule_pool_size>16</background_schedule_pool_size>

    <!-- Compression -->
    <compression>
        <case>
            <min_part_size>10000000000</min_part_size>
            <min_part_size_ratio>0.01</min_part_size_ratio>
            <method>zstd</method>
            <level>3</level>
        </case>
    </compression>

    <!-- Caching -->
    <mark_cache_size>5368709120</mark_cache_size>
    <uncompressed_cache_size>8589934592</uncompressed_cache_size>
</clickhouse>
```

### リソースガイドライン

> **参照**: AWS インスタンスタイプのパフォーマンスベンチマークについては、[AWS Instance Benchmark](https://benchmark.aws.atomai.click/) を参照してください。ClickHouse のワークロード特性（CPU 集約型クエリ、大容量メモリキャッシュ、高ディスク I/O）に適合するインスタンスを選択してください。

```yaml
# Recommended settings by scale

# Small (daily < 100GB)
resources:
  replicas: 3  # 1 shard, 3 replicas
  cpu: 4
  memory: 16Gi
  storage: 500Gi (gp3)

# Medium (daily 100GB - 1TB)
resources:
  shards: 3
  replicas_per_shard: 2
  cpu: 8
  memory: 32Gi
  storage: 2Ti (gp3)

# Large (daily > 1TB)
resources:
  shards: 10+
  replicas_per_shard: 2
  cpu: 16
  memory: 64Gi
  storage: 5Ti+ (io2)
  # S3 tiering required
```

***

## S3 アーカイブと長期保持

TTL の期限切れ前にログデータを Parquet 形式で S3 にアーカイブすると、元のデータと比べてストレージコストを約 90% 削減できます。

### アーカイブパイプライン

```
ClickHouse (Hot)  ──Before TTL──▶  S3 Parquet + ZSTD  ──▶  Query directly via S3 engine
    90-day retention                  Long-term (unlimited)     No separate table definition needed
```

### S3 への直接アーカイブ

```sql
-- Archive to S3 in Parquet format
INSERT INTO FUNCTION s3(
    'https://s3.ap-northeast-2.amazonaws.com/my-log-archive/logs/{_partition_id}/data.parquet',
    'Parquet',
    'timestamp DateTime64(3), level String, message String, namespace String, service String, raw_json String'
)
SETTINGS s3_truncate_on_insert=0
SELECT timestamp, level, message, namespace, service, raw_json
FROM logs.application_logs
WHERE date >= '2025-01-01' AND date < '2025-02-01';
```

### ウォーターマークベースの進捗追跡

大規模なアーカイブでは、ウォーターマークテーブルで進捗を追跡します。

```sql
-- Watermark table
CREATE TABLE logs.archive_watermark
(
    partition_id String,
    status Enum8('pending'=0, 'processing'=1, 'completed'=2, 'failed'=3),
    started_at DateTime DEFAULT now(),
    completed_at Nullable(DateTime),
    row_count UInt64 DEFAULT 0,
    error_message String DEFAULT ''
)
ENGINE = MergeTree()
ORDER BY (partition_id);
```

**アーカイブ遅延戦略:**

* Merge の完了を待機: 2 日（Part のマージが安定するまで）
* 再処理バッファ: 1 日（データ修正または再取り込みの可能性に備える）
* **合計遅延: 3 日** — パーティション作成から 3 日経過後にのみデータをアーカイブする

### アーカイブ済みデータを直接クエリする

個別のテーブルを作成せずに、S3 内のアーカイブ済み Parquet ファイルを直接クエリできます。

```sql
-- Query S3 archive directly (no table creation needed)
SELECT
    toStartOfHour(timestamp) AS hour,
    level,
    count() AS log_count
FROM s3(
    'https://s3.ap-northeast-2.amazonaws.com/my-log-archive/logs/*/data.parquet',
    'Parquet'
)
WHERE timestamp >= '2025-01-15' AND timestamp < '2025-01-16'
GROUP BY hour, level
ORDER BY hour;
```

> **コストへの影響**: 生ログ 1TB → S3 Parquet + ZSTD 圧縮 ≈ 100GB（90% 削減）。S3 Standard の料金では、長期保持のコストは月額 \~$2.3/TB です。

***

## クイズ

[ClickHouse クイズ](../../quizzes/observability/logging/04-clickhouse-quiz.md)で理解度を確認しましょう。
