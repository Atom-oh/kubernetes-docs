# ClickHouse for Log Analytics

> **Last Updated**: February 23, 2026

ClickHouse is an open-source columnar database optimized for OLAP (Online Analytical Processing) workloads. It provides excellent query performance and compression ratios for large-scale log analytics.

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Kubernetes Deployment](#kubernetes-deployment)
4. [Log Ingestion Pipeline](#log-ingestion-pipeline)
5. [SQL Queries](#sql-queries)
6. [Grafana Integration](#grafana-integration)
7. [Performance Optimization](#performance-optimization)
8. [S3 Archiving and Long-term Retention](#s3-archiving-and-long-term-retention)
9. [HyperDX (ClickHouse Native Viewer)](#hyperdx-clickhouse-native-viewer)

---

## Overview

### ClickHouse Features

| Feature | Description |
|---------|-------------|
| **Columnar storage** | Data storage optimized for analytical queries |
| **High compression** | 10:1+ compression ratios for storage cost savings |
| **Fast queries** | Scan billions of rows in seconds |
| **SQL support** | Write queries in standard SQL |
| **Horizontal scaling** | Distributed processing via sharding |
| **Real-time ingestion** | Ingest millions of rows per second |

### Why Choose ClickHouse for Log Analytics

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

### Comparison with Other Solutions

| Item | ClickHouse | Elasticsearch | Loki |
|------|-----------|---------------|------|
| **Query language** | SQL | Query DSL | LogQL |
| **Storage method** | Columnar | Document-based | Chunk-based |
| **Compression ratio** | Very high | Low | High |
| **Full-text search** | Limited | Excellent | Limited |
| **Aggregation queries** | Excellent | Good | Basic |
| **Learning curve** | Low if SQL familiar | Medium | Low |
| **Operational complexity** | Medium | High | Low |

---

## Architecture

### ClickHouse Cluster Architecture

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

### Data Flow

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

---

## Kubernetes Deployment

### Install ClickHouse Operator

```bash
# Install Altinity ClickHouse Operator
kubectl apply -f https://raw.githubusercontent.com/Altinity/clickhouse-operator/master/deploy/operator/clickhouse-operator-install-bundle.yaml

# Verify installation
kubectl get pods -n kube-system | grep clickhouse
```

### ClickHouse Cluster Definition

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

### ZooKeeper (or ClickHouse Keeper) Deployment

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

---

## Log Ingestion Pipeline

### Buffer → Store → Distributed 3-Tier Design

> **Interactive Visualization**: See the [ClickHouse 3-Tier Pipeline Animation](../../../assets/clickhouse-3tier-pipeline.html) to visually explore the Buffer → Store → Distributed data flow.

In large-scale log environments (TB+ per day), concentrated INSERT requests create many small Parts, causing Merge overhead to spike. A 3-tier design using the Buffer engine solves this problem.

```
Buffer Table (Memory)  →  Store Table (ReplicatedMergeTree)  →  Distributed Table (Query Router)
    Receives INSERTs          Actual data storage                   Client query entry point
    Accumulates in memory     Flushes as large Parts                Distributes across shards
```

**Buffer Engine Role:**
- Accumulates INSERT requests in memory and flushes to the Store table when conditions (time/rows/bytes) are met
- Batches many small INSERTs during peak into large Parts → minimizes Merge overhead
- Prevents `Too many parts` errors from Part count explosion

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

> **Note**: Buffer table data resides in memory, so unflushed data may be lost if ClickHouse terminates abnormally. When used with Kafka, data can be recovered through reprocessing.

### Log Table Schema

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

### Ingestion via Vector

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

### Ingestion via FluentBit

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

### Buffering via Kafka (Large-scale Environments)

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

---

## SQL Queries

### Basic Queries

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

### Advanced Analytics Queries

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

### Real-time Dashboard Queries

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

---

## Grafana Integration

### ClickHouse Datasource Setup

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

### Grafana Dashboard Panels

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

### Alert Rules

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

---

## HyperDX (ClickHouse Native Viewer)

HyperDX is a native log viewer that queries ClickHouse directly. Unlike Grafana or Signoz, it leverages ClickHouse's columnar storage structure directly, delivering high performance for field-specific searches.

### Key Advantages

| Feature | Description |
|---------|-------------|
| **Field-specific search** | `ServiceName:payment` style searches are 20x+ faster than LIKE queries |
| **ClickHouse native** | Queries ClickHouse directly without separate indexing layers |
| **Auto schema detection** | Automatically recognizes Buffer/Store/View separated structures |
| **OTEL compatible** | Native support for OpenTelemetry log schema |

### Log Viewer Comparison

| Feature | Grafana | Signoz | HyperDX |
|---------|---------|--------|---------|
| **ClickHouse native** | Plugin required | Forces own schema | Native |
| **Field search speed** | Good | Good | Excellent (20x) |
| **Custom schema** | Supported | Limited | Full support |
| **Buffer/Store structure** | Manual config | Not supported | Auto-detected |
| **Deployment** | Standalone | Standalone | Standalone |
| **License** | AGPL-3.0 | Custom license | MIT |

> **Signoz Limitation**: Signoz enforces its own schema, which creates constraints in environments using Buffer → Store → Distributed 3-tier structures or custom Materialized columns.

---

## Performance Optimization

### Table Design Optimization

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

### Parts Optimization

ClickHouse's MergeTree engine creates Parts on INSERT and merges them in the background. The balance between Part size and count determines query performance and system stability.

**Part Size Trade-offs:**

| Part Characteristic | Large Size + Few Parts | Small Size + Many Parts |
|--------------------|----------------------|------------------------|
| **Merge overhead** | Memory spikes during merge | Frequent merges, CPU load |
| **Query performance** | Fewer Parts to scan = faster | Part-open overhead increases |
| **INSERT impact** | Large batches needed | Small batches possible |
| **Risk** | OOM possibility | `Too many parts` error |

**Operational Recommendations:**

| Item | Recommended Value |
|------|-------------------|
| Parts per partition | ~20 or fewer |
| Size per Part | 2-3GB |
| Active partitions | 24-48 with hourly partitioning |

**Monitoring Queries:**

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

### Query Optimization

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

### System Configuration Optimization

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

### Resource Guidelines

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

---

## S3 Archiving and Long-term Retention

Archiving log data to S3 in Parquet format before TTL expiration can reduce storage costs by approximately 90% compared to the original.

### Archiving Pipeline

```
ClickHouse (Hot)  ──Before TTL──▶  S3 Parquet + ZSTD  ──▶  Query directly via S3 engine
    90-day retention                  Long-term (unlimited)     No separate table definition needed
```

### Direct S3 Archiving

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

### Watermark-based Progress Tracking

For large-scale archiving, track progress with a watermark table.

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

**Archiving Delay Strategy:**
- Wait for Merge completion: 2 days (until Part merges stabilize)
- Reprocessing buffer: 1 day (for potential data corrections/re-ingestion)
- **Total delay: 3 days** — archive data only after 3 days from partition creation

### Querying Archived Data Directly

You can query archived Parquet files in S3 directly without creating separate tables.

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

> **Cost Impact**: 1TB raw logs → S3 Parquet + ZSTD compression ≈ 100GB (90% reduction). At S3 Standard pricing, long-term retention costs ~$2.3/TB per month.

---

## Quiz

Test your knowledge with the [ClickHouse Quiz](../../quizzes/observability/logging/04-clickhouse-quiz.md).
