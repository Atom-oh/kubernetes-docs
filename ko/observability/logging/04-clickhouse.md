# ClickHouse

> **마지막 업데이트**: 2026년 6월 30일

ClickHouse는 OLAP(Online Analytical Processing) 워크로드에 최적화된 오픈소스 컬럼 기반 데이터베이스입니다. 대규모 로그 분석에서 뛰어난 쿼리 성능과 압축률을 제공합니다.

## 목차

1. [개요](04-clickhouse.md#개요)
2. [아키텍처](04-clickhouse.md#아키텍처)
3. [Kubernetes 배포](04-clickhouse.md#kubernetes-배포)
4. [로그 수집 파이프라인](04-clickhouse.md#로그-수집-파이프라인)
5. [SQL 쿼리](04-clickhouse.md#sql-쿼리)
6. [Grafana 연동](04-clickhouse.md#grafana-연동)
7. [성능 최적화](04-clickhouse.md#성능-최적화)
8. [S3 아카이빙 및 장기 보관](04-clickhouse.md#s3-아카이빙-및-장기-보관)
9. [HyperDX (ClickHouse 네이티브 뷰어)](04-clickhouse.md#hyperdx-clickhouse-네이티브-뷰어)

***

## 개요

### ClickHouse의 특징

| 특징           | 설명                       |
| ------------ | ------------------------ |
| **컬럼 기반 저장** | 분석 쿼리에 최적화된 데이터 저장 방식    |
| **높은 압축률**   | 10:1 이상의 압축률로 스토리지 비용 절감 |
| **빠른 쿼리**    | 수십억 행을 초 단위로 스캔          |
| **SQL 지원**   | 표준 SQL로 쿼리 작성            |
| **수평 확장**    | 샤딩을 통한 분산 처리             |
| **실시간 수집**   | 초당 수백만 행 수집 가능           |

### 로그 분석에 ClickHouse를 선택하는 이유

**로그 분석 요구사항:**

| 요구사항        | 설명                  |
| ----------- | ------------------- |
| 대규모 데이터     | 일 TB 이상             |
| 복잡한 집계 쿼리   | GROUP BY, JOIN      |
| SQL 기반 분석   | 표준 SQL 지원           |
| 낮은 스토리지 비용  | 높은 압축률              |
| 빠른 쿼리 응답    | 초 단위                |
| 기존 BI 도구 연동 | Grafana, Superset 등 |

위 요구사항에 해당한다면 **ClickHouse가 적합한 선택**입니다.

### 다른 솔루션과의 비교

| 항목         | ClickHouse  | Elasticsearch | Loki  |
| ---------- | ----------- | ------------- | ----- |
| **쿼리 언어**  | SQL         | Query DSL     | LogQL |
| **저장 방식**  | 컬럼 기반       | 문서 기반         | 청크 기반 |
| **압축률**    | 매우 높음       | 낮음            | 높음    |
| **전문 검색**  | 제한적         | 우수            | 제한적   |
| **집계 쿼리**  | 우수          | 양호            | 기본적   |
| **학습 곡선**  | SQL 친숙 시 낮음 | 중간            | 낮음    |
| **운영 복잡성** | 중간          | 높음            | 낮음    |

***

## 아키텍처

### ClickHouse 클러스터 아키텍처

![수집기가 Kafka Topic을 거쳐 3개 샤드(각 2개 레플리카)로 구성된 ClickHouse 클러스터에 로그를 적재하고, ZooKeeper/Keeper가 샤드별 레플리카 복제를 조정하며, 데이터가 EBS(Hot)에서 S3(Cold)로 이동하고 Grafana/Superset이 클러스터를 조회하는 흐름을 보여준다.](../../.gitbook/assets/ko-observability-logging-04-clickhouse-0.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-observability-logging-04-clickhouse-0.html)

### 데이터 흐름

![애플리케이션이 생성한 로그가 FluentBit와 Kafka를 거쳐 ClickHouse의 MergeTree 테이블에 저장되고, TTL 정책에 따라 일정 시간이 지나면 S3 Cold 스토리지로 이동하는 순서를 보여준다.](../../.gitbook/assets/ko-observability-logging-04-clickhouse-1.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-observability-logging-04-clickhouse-1.html)

***

## Kubernetes 배포

### ClickHouse Operator 설치

```bash
# Altinity ClickHouse Operator 설치
kubectl apply -f https://raw.githubusercontent.com/Altinity/clickhouse-operator/master/deploy/operator/clickhouse-operator-install-bundle.yaml

# 설치 확인
kubectl get pods -n kube-system | grep clickhouse
```

### ClickHouse 클러스터 정의

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
      # 로그 분석 최적화 설정
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

### ZooKeeper (또는 ClickHouse Keeper) 배포

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

## 로그 수집 파이프라인

### Buffer → Store → Distributed 3계층 설계

> **인터랙티브 시각화**: [ClickHouse 3-Tier Pipeline 애니메이션](https://github.com/Atom-oh/kubernetes-docs/blob/main/assets/clickhouse-3tier-pipeline.html)을 통해 Buffer → Store → Distributed 데이터 흐름을 시각적으로 확인할 수 있습니다.

대규모 로그 환경(일 TB 이상)에서는 INSERT 요청이 집중될 때 작은 Part가 대량 생성되어 Merge 부하가 급증합니다. Buffer 엔진을 활용한 3계층 설계로 이 문제를 해결할 수 있습니다.

```
Buffer 테이블 (메모리)  →  Store 테이블 (ReplicatedMergeTree)  →  Distributed 테이블 (분산 쿼리)
    INSERT 수신              실제 데이터 저장                      클라이언트 쿼리 진입점
    메모리에 누적             큰 Part 단위로 flush                  모든 샤드에 분산 쿼리
```

**Buffer 엔진 역할:**

* INSERT 요청을 메모리에 모았다가 일정 조건(시간/행수/바이트) 충족 시 Store 테이블로 flush
* 피크 시 대량의 작은 INSERT를 모아서 큰 Part로 생성 → Merge 부하 최소화
* Part 수 폭증으로 인한 `Too many parts` 에러 방지

```sql
-- 1. Store 테이블 (실제 데이터 저장)
CREATE TABLE logs.store_application_logs ON CLUSTER logs
(
    -- 스키마는 기존 application_logs와 동일
    ...
)
ENGINE = ReplicatedMergeTree('/clickhouse/tables/{shard}/logs.store_application_logs', '{replica}')
PARTITION BY (toYYYYMMDD(timestamp) * 100 + toHour(timestamp))
ORDER BY (namespace, service, timestamp)
TTL timestamp + INTERVAL 90 DAY
SETTINGS
    index_granularity = 8192,
    ttl_only_drop_parts = 1;

-- 2. Buffer 테이블 (INSERT 수신용)
CREATE TABLE logs.buffer_application_logs AS logs.store_application_logs
ENGINE = Buffer(
    'logs',                    -- 데이터베이스
    'store_application_logs',  -- 대상 테이블
    16,                        -- num_layers (병렬 버퍼 수)
    1,                         -- min_time (초) - 최소 1초 후 flush
    30,                        -- max_time (초) - 최대 30초 후 flush
    500000,                    -- min_rows
    5000000,                   -- max_rows
    500000000,                 -- min_bytes (~500MB)
    1000000000                 -- max_bytes (~1GB)
);

-- 3. Distributed 테이블 (쿼리 진입점)
CREATE TABLE logs.application_logs_distributed ON CLUSTER logs
AS logs.store_application_logs
ENGINE = Distributed(logs, logs, store_application_logs, rand());
```

> **주의**: Buffer 테이블의 데이터는 메모리에 있으므로, ClickHouse가 비정상 종료되면 flush되지 않은 데이터가 유실될 수 있습니다. Kafka와 함께 사용하면 재처리로 복구 가능합니다.

### 로그 테이블 스키마

```sql
-- 로그 테이블 생성 (운영 최적화 버전)
CREATE TABLE IF NOT EXISTS logs.application_logs ON CLUSTER logs
(
    -- DoubleDelta CODEC: 시계열 타임스탬프에 최적 압축
    timestamp DateTime64(3) CODEC(DoubleDelta, LZ4),
    date Date DEFAULT toDate(timestamp),
    level LowCardinality(String),
    message String,
    logger String,

    -- Kubernetes 메타데이터
    namespace LowCardinality(String),
    pod_name String,
    container_name LowCardinality(String),
    node_name LowCardinality(String),

    -- 추적 정보
    trace_id String,
    span_id String,

    -- 추가 필드
    service LowCardinality(String),
    environment LowCardinality(String),

    -- Materialized 컬럼: INSERT 시점에 JSON에서 자주 사용하는 필드를 자동 추출
    -- 쿼리 시 JSON 파싱 없이 직접 컬럼 접근 가능 → 성능 대폭 향상
    app_name String MATERIALIZED JSONExtractString(raw_json, 'app_name'),
    error_code String MATERIALIZED JSONExtractString(raw_json, 'error_code'),
    response_time Float64 MATERIALIZED JSONExtractFloat(raw_json, 'response_time_ms'),

    -- JSON 원본 (선택)
    raw_json String CODEC(ZSTD(3)),

    INDEX idx_trace_id trace_id TYPE bloom_filter GRANULARITY 4,
    INDEX idx_message message TYPE tokenbf_v1(10240, 3, 0) GRANULARITY 4
)
ENGINE = ReplicatedMergeTree('/clickhouse/tables/{shard}/logs.application_logs', '{replica}')
-- 시간 단위 파티셔닝: 월 단위(toYYYYMM) 대신 시간 단위로 세분화
-- → TTL 삭제 시 Part 단위 통째 삭제 가능, 더 정밀한 데이터 관리
PARTITION BY (toYYYYMMDD(date) * 100 + toHour(timestamp))
ORDER BY (namespace, service, timestamp)
TTL date + INTERVAL 90 DAY
SETTINGS
    index_granularity = 8192,
    -- Part 단위 통째 삭제: 행 단위 삭제 대비 TTL 처리 효율 극대화
    ttl_only_drop_parts = 1;

-- 분산 테이블 생성
CREATE TABLE IF NOT EXISTS logs.application_logs_distributed ON CLUSTER logs
AS logs.application_logs
ENGINE = Distributed(logs, logs, application_logs, rand());
```

### Vector를 통한 수집

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
          # JSON 파싱 시도
          parsed, err = parse_json(.message)
          if err == null {
            . = merge(., parsed)
          }

          # 필드 정규화
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

### FluentBit을 통한 수집

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

### Kafka를 통한 버퍼링 (대규모 환경)

```sql
-- Kafka 엔진 테이블
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

-- Materialized View로 실제 테이블에 저장
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

## SQL 쿼리

### 기본 쿼리

```sql
-- 최근 에러 로그 조회
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

-- 서비스별 에러 수
SELECT
    service,
    count() as error_count,
    uniq(pod_name) as affected_pods
FROM logs.application_logs_distributed
WHERE level = 'ERROR'
  AND date = today()
GROUP BY service
ORDER BY error_count DESC;

-- 시간대별 로그 볼륨
SELECT
    toStartOfHour(timestamp) as hour,
    count() as log_count,
    sum(length(message)) as total_bytes
FROM logs.application_logs_distributed
WHERE date >= today() - 7
GROUP BY hour
ORDER BY hour;
```

### 고급 분석 쿼리

```sql
-- 에러율 트렌드 (5분 간격)
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

-- 에러 메시지 패턴 분석
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

-- 파드 재시작 패턴 감지
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

-- 느린 요청 분석 (JSON 로그에서 response_time 추출)
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

-- 특정 trace_id로 분산 추적
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

### 실시간 대시보드용 쿼리

```sql
-- 실시간 로그 스트림 (라이브 테일링)
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

-- 서비스 상태 요약
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

## Grafana 연동

### ClickHouse 데이터소스 설정

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

### Grafana 대시보드 패널

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

### 알림 규칙

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

## HyperDX (ClickHouse 네이티브 뷰어)

HyperDX는 ClickHouse를 직접 쿼리하는 네이티브 로그 뷰어입니다. Grafana나 Signoz와 달리 ClickHouse의 컬럼형 저장 구조를 직접 활용하여 필드 지정 검색에서 높은 성능을 발휘합니다.

### 핵심 장점

| 기능                  | 설명                                                |
| ------------------- | ------------------------------------------------- |
| **필드 지정 검색**        | `ServiceName:payment` 형태의 검색이 LIKE 검색보다 20배 이상 빠름 |
| **ClickHouse 네이티브** | 별도 인덱싱 계층 없이 ClickHouse 직접 쿼리                     |
| **자동 스키마 감지**       | Buffer/Store/View 분리 구조 자동 인식                     |
| **OTEL 호환**         | OpenTelemetry 로그 스키마 네이티브 지원                      |

### 로그 뷰어 비교

| 기능                  | Grafana  | Signoz    | HyperDX  |
| ------------------- | -------- | --------- | -------- |
| **ClickHouse 네이티브** | 플러그인 필요  | 자체 스키마 강제 | 네이티브     |
| **필드 검색 속도**        | 양호       | 양호        | 우수 (20x) |
| **커스텀 스키마**         | 지원       | 제한적       | 완전 지원    |
| **Buffer/Store 구조** | 수동 설정    | 미지원       | 자동 감지    |
| **배포 방식**           | 독립 서비스   | 독립 서비스    | 독립 서비스   |
| **라이선스**            | AGPL-3.0 | 자체 라이선스   | MIT      |

> **Signoz 한계**: Signoz는 자체 정의 스키마를 강제하므로, Buffer → Store → Distributed 3계층 구조나 커스텀 Materialized 컬럼을 사용하는 환경에서는 제약이 있습니다.

***

## 성능 최적화

### 테이블 설계 최적화

```sql
-- 최적화된 테이블 설계
CREATE TABLE logs.optimized_logs
(
    -- 자주 필터링하는 컬럼을 앞에 배치
    timestamp DateTime64(3),
    date Date DEFAULT toDate(timestamp),

    -- LowCardinality로 카디널리티 낮은 컬럼 최적화
    level LowCardinality(String),
    namespace LowCardinality(String),
    service LowCardinality(String),
    environment LowCardinality(String) DEFAULT 'production',

    -- 일반 컬럼
    message String,
    pod_name String,

    -- 압축 설정
    raw_json String CODEC(ZSTD(3))
)
ENGINE = MergeTree()
-- 쿼리 패턴에 맞는 정렬 키
PARTITION BY toYYYYMM(date)
ORDER BY (namespace, service, level, timestamp)
-- TTL 설정
TTL date + INTERVAL 30 DAY DELETE,
    date + INTERVAL 7 DAY TO VOLUME 'cold'
SETTINGS
    index_granularity = 8192,
    min_bytes_for_wide_part = 10485760,
    min_rows_for_wide_part = 10000;
```

### Parts 최적화

ClickHouse의 MergeTree 엔진은 INSERT 시 Part를 생성하고, 백그라운드에서 Part를 병합(Merge)합니다. Part 크기와 개수의 균형이 쿼리 성능과 시스템 안정성을 좌우합니다.

**Part 크기별 트레이드오프:**

| Part 특성       | 크기 큼 + 개수 적음   | 크기 작음 + 개수 많음       |
| ------------- | -------------- | ------------------- |
| **Merge 부하**  | Merge 시 메모리 급증 | Merge 빈번, CPU 부하    |
| **쿼리 성능**     | 스캔할 Part 적어 빠름 | Part 열기 오버헤드 증가     |
| **INSERT 영향** | 큰 배치 필요        | 작은 배치 가능            |
| **위험**        | OOM 가능성        | `Too many parts` 에러 |

**운영 권장 기준:**

| 항목          | 권장값                    |
| ----------- | ---------------------- |
| 파티션당 Part 수 | \~20개 이하               |
| Part당 크기    | 2-3GB                  |
| 활성 파티션 수    | 시간 단위 파티셔닝 시 최근 24-48개 |

**모니터링 쿼리:**

```sql
-- 파티션별 Part 수와 크기 확인
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

-- Too many parts 경고 감지
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

### 쿼리 최적화

```sql
-- PREWHERE 사용 (필터 최적화)
SELECT *
FROM logs.application_logs_distributed
PREWHERE date = today()
WHERE level = 'ERROR'
  AND namespace = 'production'
LIMIT 100;

-- 서브쿼리 대신 WITH 절 사용
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

-- 샘플링으로 대규모 데이터 빠르게 분석
SELECT
    service,
    count() * 10 as estimated_count  -- 10% 샘플
FROM logs.application_logs_distributed
SAMPLE 0.1
WHERE date >= today() - 7
GROUP BY service;
```

### 시스템 설정 최적화

```xml
<!-- config.d/performance.xml -->
<clickhouse>
    <!-- 쿼리 처리 -->
    <max_threads>16</max_threads>
    <max_memory_usage>10000000000</max_memory_usage>
    <max_bytes_before_external_group_by>5000000000</max_bytes_before_external_group_by>
    <max_bytes_before_external_sort>5000000000</max_bytes_before_external_sort>

    <!-- 병합 설정 -->
    <background_pool_size>16</background_pool_size>
    <background_schedule_pool_size>16</background_schedule_pool_size>

    <!-- 압축 -->
    <compression>
        <case>
            <min_part_size>10000000000</min_part_size>
            <min_part_size_ratio>0.01</min_part_size_ratio>
            <method>zstd</method>
            <level>3</level>
        </case>
    </compression>

    <!-- 캐싱 -->
    <mark_cache_size>5368709120</mark_cache_size>
    <uncompressed_cache_size>8589934592</uncompressed_cache_size>
</clickhouse>
```

### 리소스 가이드라인

> **참고**: AWS 인스턴스 타입별 성능 벤치마크는 [AWS Instance Benchmark](https://benchmark.aws.atomai.click/)에서 확인할 수 있습니다. ClickHouse 워크로드 특성(CPU 집약적 쿼리, 대용량 메모리 캐시, 높은 디스크 I/O)에 맞는 인스턴스를 선택하세요.

```yaml
# 규모별 권장 설정

# Small (일일 < 100GB)
resources:
  replicas: 3  # 1 shard, 3 replicas
  cpu: 4
  memory: 16Gi
  storage: 500Gi (gp3)

# Medium (일일 100GB - 1TB)
resources:
  shards: 3
  replicas_per_shard: 2
  cpu: 8
  memory: 32Gi
  storage: 2Ti (gp3)

# Large (일일 > 1TB)
resources:
  shards: 10+
  replicas_per_shard: 2
  cpu: 16
  memory: 64Gi
  storage: 5Ti+ (io2)
  # S3 티어링 필수
```

***

## S3 아카이빙 및 장기 보관

TTL로 삭제되기 전의 로그 데이터를 S3에 Parquet 형식으로 아카이빙하면 원본 대비 약 90%의 스토리지 비용을 절감할 수 있습니다.

### 아카이빙 파이프라인

```
ClickHouse (Hot)  ──TTL 만료 전──▶  S3 Parquet + ZSTD  ──▶  필요시 S3 엔진으로 직접 쿼리
    90일 보존                         장기 보관 (무제한)          별도 테이블 정의 불필요
```

### S3 직접 아카이빙

```sql
-- S3로 Parquet 형식 아카이빙
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

### 워터마크 기반 진행 상태 추적

대규모 아카이빙에서는 워터마크 테이블로 진행 상태를 추적합니다.

```sql
-- 워터마크 테이블
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

**아카이빙 지연 전략:**

* Merge 완료 대기: 2일 (Part 병합이 안정화될 때까지)
* 재처리 여유: 1일 (데이터 수정/재수집 가능성 대비)
* **총 지연: 3일** — 파티션 생성 후 3일 경과한 데이터부터 아카이빙

### 아카이브 데이터 직접 쿼리

S3에 아카이빙된 Parquet 파일을 별도 테이블 정의 없이 직접 쿼리할 수 있습니다.

```sql
-- S3 아카이브 직접 쿼리 (테이블 생성 불필요)
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

> **비용 효과**: 1TB 원본 로그 → S3 Parquet + ZSTD 압축 시 약 100GB (90% 절감). S3 Standard 기준 월 $2.3/TB로 장기 보관 가능.

***

## 퀴즈

이 장에서 배운 내용을 테스트하려면 [ClickHouse 퀴즈](../../quizzes/observability/logging/04-clickhouse-quiz.md)를 풀어보세요.
