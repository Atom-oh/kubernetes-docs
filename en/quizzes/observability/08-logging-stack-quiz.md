# Logging Stack Quiz

This quiz tests your understanding of the Kubernetes logging stack (Grafana Loki, Grafana Tempo).

## Multiple Choice Questions

1. Which is correct about Grafana Loki's indexing method?
   - A) Full-text indexing of all log content
   - B) Index only labels (metadata), not log content
   - C) Index only first 100 characters of logs
   - D) Index using regex pattern matching

<details>

<summary>Show Answer</summary>

**Answer: B) Index only labels (metadata), not log content**

**Explanation:**
Loki uses a "label-based indexing" approach inspired by Prometheus. It doesn't index log content itself, only labels (namespace, pod, container, etc.). Log content is stored as compressed chunks, and at query time, filtering is done by labels first, then those chunks are scanned. This approach results in smaller index size compared to full-text indexing like Elasticsearch, reducing costs, but may require scanning more data when searching log content.
</details>

2. What makes Grafana Tempo different from other distributed tracing systems (Jaeger, Zipkin)?
   - A) Real-time trace data analysis
   - B) No indexing of trace data, only searchable by TraceID
   - C) Only supports OpenTelemetry format
   - D) Stores data only in memory

<details>

<summary>Show Answer</summary>

**Answer: B) No indexing of trace data, only searchable by TraceID**

**Explanation:**
Tempo's core design philosophy is "indexless distributed tracing". It doesn't index trace data, storing directly to object storage (S3, GCS, etc.), and search is only possible when you know the TraceID. This approach significantly reduces operational complexity and costs. To search traces by service name or tags, you need to first find the TraceID through Grafana's TraceQL or correlation with logs/metrics.
</details>

3. What is Promtail's main role?
   - A) Collect metrics and send to Prometheus
   - B) Read log files and send to Loki
   - C) Collect distributed trace data and send to Tempo
   - D) Monitor Kubernetes events

<details>

<summary>Show Answer</summary>

**Answer: B) Read log files and send to Loki**

**Explanation:**
Promtail is the log collection agent for Loki. In Kubernetes environments, it's deployed as a DaemonSet to tail container log files (/var/log/pods/) on each node, add Kubernetes metadata (namespace, pod, container labels), and send to Loki. It can also perform log parsing, filtering, and label addition through pipeline stages.
</details>

4. What is the correct LogQL syntax to filter lines containing "error" in log content?
   - A) {namespace="default"} where "error"
   - B) {namespace="default"} |= "error"
   - C) {namespace="default"} LIKE "error"
   - D) {namespace="default"} contains("error")

<details>

<summary>Show Answer</summary>

**Answer: B) {namespace="default"} |= "error"**

**Explanation:**
In LogQL, `|=` is the operator to filter lines containing the specified string. Conversely, `!=` selects lines that don't contain the string. For regex, use `|~` (contains) and `!~` (doesn't contain). Example: `{namespace="default"} |~ "error|warn"`. This filtering is performed by scanning log chunks after label selection.
</details>

5. What is the role of Loki's Distributor component?
   - A) Store log data in long-term storage
   - B) Receive logs from clients, validate, and distribute to Ingesters
   - C) Process user queries and return results
   - D) Compress and optimize stored logs

<details>

<summary>Show Answer</summary>

**Answer: B) Receive logs from clients, validate, and distribute to Ingesters**

**Explanation:**
Loki's Distributor is the first component to receive log streams from clients like Promtail. It validates received logs (label format, timestamp, etc.) and distributes to appropriate Ingester instances through hashing. This distribution uses consistent hashing to ensure the same log stream always goes to the same Ingester.
</details>

6. What telemetry signal types does OpenTelemetry Collector support?
   - A) Logs only
   - B) Metrics only
   - C) Traces only
   - D) Logs, Metrics, and Traces

<details>

<summary>Show Answer</summary>

**Answer: D) Logs, Metrics, and Traces**

**Explanation:**
OpenTelemetry Collector is a vendor-neutral telemetry data collector that can collect, process, and export all three core signal types: Logs, Metrics, and Traces. The Collector can receive data in various formats (OTLP, Jaeger, Zipkin, Prometheus, etc.) and export to multiple backends (Loki, Tempo, Prometheus, commercial APM, etc.), serving as a hub for observability pipelines.
</details>

7. What is correct about Loki's Chunk role and characteristics?
   - A) Memory buffer for real-time log streaming
   - B) Basic unit for storing log data in compressed form
   - C) Structure for storing index metadata
   - D) Temporary storage for caching query results

<details>

<summary>Show Answer</summary>

**Answer: B) Basic unit for storing log data in compressed form**

**Explanation:**
Loki's Chunks are the basic unit for bundling and compressing log lines with the same label set. Ingesters buffer logs in memory and create chunks when they reach a certain size or time, storing them in object storage. Chunks are compressed with gzip, snappy, lz4, etc. to reduce storage costs. The Compactor later merges smaller chunks into larger ones to improve query efficiency.
</details>

8. Which is NOT a receive protocol supported by Tempo?
   - A) Jaeger Thrift
   - B) Zipkin JSON
   - C) OpenTelemetry Protocol (OTLP)
   - D) Prometheus Remote Write

<details>

<summary>Show Answer</summary>

**Answer: D) Prometheus Remote Write**

**Explanation:**
Prometheus Remote Write is a protocol for sending metric data, not used in Tempo which is a tracing system. Tempo supports Jaeger (Thrift, gRPC), Zipkin (JSON, Thrift), and OTLP (gRPC, HTTP) for receiving distributed trace data. This diverse protocol support makes it easy to migrate to Tempo from existing Jaeger or Zipkin environments.
</details>

## Short Answer Questions

9. Explain why label cardinality should be kept low in Loki.

<details>

<summary>Show Answer</summary>

**Answer:**
High label cardinality increases index size, degrades query performance, and causes memory usage to spike.

**Explanation:**
Loki creates separate log streams for each label combination. Using fields with many unique values like user_id or request_id as labels can create millions of streams. This leads to exploding index size, Ingester memory exhaustion, and scanning many chunks during queries. The recommendation is to use only low cardinality labels like namespace, pod, container, app, env, and include unique identifiers in log content to filter with LogQL.
</details>

10. Explain how to implement trace-to-log correlation.

<details>

<summary>Show Answer</summary>

**Answer:**
Include TraceID in application logs and connect Tempo and Loki data sources in Grafana to query logs by TraceID.

**Explanation:**
Steps to implement trace-to-log correlation:
1. **Application Instrumentation**: Include current span's TraceID when outputting logs (e.g., `logger.info("Processing request", trace_id=span.context.trace_id)`)
2. **Grafana Data Source Configuration**: In Tempo data source settings, connect Loki data source in "Trace to logs" section and specify TraceID field name
3. **LogQL Query Template**: `{app="myapp"} | json | trace_id="${__span.traceId}"`
4. With this setup, you can jump directly to related logs when viewing traces in Grafana.
</details>

11. Explain two methods for setting retention policies in Loki.

<details>

<summary>Show Answer</summary>

**Answer:**
1. **Global Retention Period**: Set default retention period for all logs with `limits_config.retention_period`
2. **Per-Stream Retention Period**: Set different retention periods for specific label selectors with `limits_config.retention_stream`

**Explanation:**
Loki retention policy configuration example:
```yaml
limits_config:
  retention_period: 720h  # 30 day default retention
  retention_stream:
  - selector: '{namespace="production"}'
    priority: 1
    period: 2160h  # 90 day retention
  - selector: '{level="debug"}'
    priority: 2
    period: 168h   # 7 day retention
```
The Compactor deletes expired chunks according to these policies. compactor.retention_enabled: true setting is required. Per-stream retention optimizes costs by keeping important production logs longer and deleting debug logs quickly.
</details>

12. Explain the benefits of Grafana Alloy (formerly Grafana Agent) over Promtail.

<details>

<summary>Show Answer</summary>

**Answer:**
Grafana Alloy can collect logs, metrics, and traces in a single agent, reducing deployment complexity and saving resources.

**Explanation:**
Key benefits of Grafana Alloy:
1. **Unified Collection**: Provides functionality of Promtail (logs) + Prometheus Agent (metrics) + OpenTelemetry Collector (traces) in a single binary
2. **Dynamic Configuration**: Flexible pipeline definition with River configuration language
3. **Automatic Correlation**: Can automatically connect trace_id, span_id since collected from the same agent
4. **Resource Efficiency**: Saves memory/CPU by running one agent instead of multiple
5. **Community Integration**: More closely integrated with the OpenTelemetry ecosystem
</details>

## Hands-on Questions

13. Write a LogQL query to search error level logs in the production namespace and aggregate error count by app over 5 minutes.

<details>

<summary>Show Answer</summary>

**Answer:**
```logql
# Search error logs
{namespace="production"} | json | level="error"

# Aggregate error count by app over 5 minutes (metric query)
sum by (app) (
  count_over_time(
    {namespace="production"} | json | level="error" [5m]
  )
)

# Or using rate (errors per second)
sum by (app) (
  rate(
    {namespace="production"} |= "error" [5m]
  )
)
```

**Explanation:**
LogQL supports two types of queries:
1. **Log Queries**: Return log lines (e.g., first query)
2. **Metric Queries**: Calculate metrics from logs (e.g., count_over_time, rate)

`| json` parses JSON format logs and extracts fields as labels. `level="error"` filters by the parsed level field. `count_over_time` aggregates log line count over the specified period, and `sum by (app)` groups by app.
</details>

14. Write a basic Tempo configuration file. (OTLP gRPC receiver, S3 storage, 7 day retention)

<details>

<summary>Show Answer</summary>

**Answer:**
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: tempo-config
  namespace: tracing
data:
  tempo.yaml: |
    server:
      http_listen_port: 3200
      grpc_listen_port: 9095

    distributor:
      receivers:
        otlp:
          protocols:
            grpc:
              endpoint: 0.0.0.0:4317
            http:
              endpoint: 0.0.0.0:4318
        jaeger:
          protocols:
            grpc:
              endpoint: 0.0.0.0:14250
            thrift_http:
              endpoint: 0.0.0.0:14268

    ingester:
      trace_idle_period: 10s
      max_block_bytes: 1000000
      max_block_duration: 5m

    compactor:
      compaction:
        compaction_window: 1h
        max_block_bytes: 100000000
        block_retention: 168h  # 7 days
        compacted_block_retention: 1h

    storage:
      trace:
        backend: s3
        s3:
          bucket: tempo-traces
          endpoint: s3.amazonaws.com
          region: ap-northeast-2
          access_key: ${AWS_ACCESS_KEY_ID}
          secret_key: ${AWS_SECRET_ACCESS_KEY}
        wal:
          path: /var/tempo/wal
        local:
          path: /var/tempo/blocks

    querier:
      frontend_worker:
        frontend_address: tempo-query-frontend:9095
```

**Explanation:**
Key elements of Tempo configuration:
- **distributor.receivers**: Define trace protocols to support (OTLP, Jaeger, etc.)
- **ingester**: Settings for buffering trace data in memory (flush block when no new spans for idle_period)
- **compactor.block_retention**: Trace data retention period (168h = 7 days)
- **storage.trace.backend**: Backend storage type (s3, gcs, azure, local)
- WAL (Write-Ahead Log) is stored locally to prevent data loss during ingester restart
</details>

15. Write a Promtail pipeline_stages configuration to parse JSON logs and add labels. (Extract timestamp, level, message fields)

<details>

<summary>Show Answer</summary>

**Answer:**
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: promtail-config
  namespace: logging
data:
  promtail.yaml: |
    server:
      http_listen_port: 3101
      grpc_listen_port: 0

    positions:
      filename: /tmp/positions.yaml

    clients:
      - url: http://loki-gateway:3100/loki/api/v1/push

    scrape_configs:
      - job_name: kubernetes-pods
        kubernetes_sd_configs:
          - role: pod
        relabel_configs:
          - source_labels: [__meta_kubernetes_pod_label_app]
            target_label: app
          - source_labels: [__meta_kubernetes_namespace]
            target_label: namespace
          - source_labels: [__meta_kubernetes_pod_name]
            target_label: pod
          - source_labels: [__meta_kubernetes_container_name]
            target_label: container
        pipeline_stages:
          # JSON parsing
          - json:
              expressions:
                timestamp: timestamp
                level: level
                message: message
                trace_id: trace_id

          # Use timestamp field as log timestamp
          - timestamp:
              source: timestamp
              format: RFC3339Nano
              fallback_formats:
                - RFC3339
                - "2006-01-02T15:04:05.000Z"

          # Add level as label
          - labels:
              level:
              trace_id:

          # Use message as log line
          - output:
              source: message

          # Drop debug level logs (optional)
          - match:
              selector: '{level="debug"}'
              stages:
                - drop:
                    expression: ".*"
```

**Explanation:**
Promtail's pipeline_stages execute sequentially:
1. **json**: Parse JSON logs and extract fields
2. **timestamp**: Set extracted timestamp as Loki log timestamp (default is collection time)
3. **labels**: Add extracted fields as Loki labels (caution: avoid high cardinality fields)
4. **output**: Use specified field as log line (message only instead of full JSON)
5. **match + drop**: Can drop logs matching specific conditions

Adding trace_id as a label makes trace-to-log correlation easier in Grafana, but caution is needed as unique values can cause high cardinality.
</details>

---

**Scoring:**
- 13-15 correct: Excellent (Logging stack expert level)
- 10-12 correct: Good (practical application capable)
- 7-9 correct: Average (additional learning recommended)
- 4-6 correct: Basic (basic concepts review needed)
- 0-3 correct: Insufficient (full content re-study needed)
