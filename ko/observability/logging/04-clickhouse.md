# ClickHouse for Log Analytics

> **마지막 업데이트**: 2026년 2월 20일

ClickHouse는 OLAP(Online Analytical Processing) 워크로드에 최적화된 오픈소스 컬럼 기반 데이터베이스입니다. 대규모 로그 분석에서 뛰어난 쿼리 성능과 압축률을 제공합니다.

## 목차

1. [개요](#개요)
2. [아키텍처](#아키텍처)
3. [Kubernetes 배포](#kubernetes-배포)
4. [로그 수집 파이프라인](#로그-수집-파이프라인)
5. [SQL 쿼리](#sql-쿼리)
6. [Grafana 연동](#grafana-연동)
7. [성능 최적화](#성능-최적화)

---

## 개요

### ClickHouse의 특징

| 특징 | 설명 |
|------|------|
| **컬럼 기반 저장** | 분석 쿼리에 최적화된 데이터 저장 방식 |
| **높은 압축률** | 10:1 이상의 압축률로 스토리지 비용 절감 |
| **빠른 쿼리** | 수십억 행을 초 단위로 스캔 |
| **SQL 지원** | 표준 SQL로 쿼리 작성 |
| **수평 확장** | 샤딩을 통한 분산 처리 |
| **실시간 수집** | 초당 수백만 행 수집 가능 |

### 로그 분석에 ClickHouse를 선택하는 이유

**로그 분석 요구사항:**

| 요구사항 | 설명 |
|----------|------|
| 대규모 데이터 | 일 TB 이상 |
| 복잡한 집계 쿼리 | GROUP BY, JOIN |
| SQL 기반 분석 | 표준 SQL 지원 |
| 낮은 스토리지 비용 | 높은 압축률 |
| 빠른 쿼리 응답 | 초 단위 |
| 기존 BI 도구 연동 | Grafana, Superset 등 |

위 요구사항에 해당한다면 **ClickHouse가 적합한 선택**입니다.

### 다른 솔루션과의 비교

| 항목 | ClickHouse | Elasticsearch | Loki |
|------|-----------|---------------|------|
| **쿼리 언어** | SQL | Query DSL | LogQL |
| **저장 방식** | 컬럼 기반 | 문서 기반 | 청크 기반 |
| **압축률** | 매우 높음 | 낮음 | 높음 |
| **전문 검색** | 제한적 | 우수 | 제한적 |
| **집계 쿼리** | 우수 | 양호 | 기본적 |
| **학습 곡선** | SQL 친숙 시 낮음 | 중간 | 낮음 |
| **운영 복잡성** | 중간 | 높음 | 낮음 |

---

## 아키텍처

### ClickHouse 클러스터 아키텍처

```mermaid
flowchart TB
    subgraph Collectors["수집기"]
        FB[FluentBit]
        VECTOR[Vector]
        OTEL[OTEL Collector]
    end

    subgraph Kafka["메시지 큐 (선택)"]
        KAFKA_TOPIC[Kafka Topic]
    end

    subgraph ClickHouse["ClickHouse 클러스터"]
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

    subgraph Storage["스토리지"]
        S3[(S3 - Cold Data)]
        EBS[(EBS - Hot Data)]
    end

    subgraph Visualization["시각화"]
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

### 데이터 흐름

```mermaid
sequenceDiagram
    participant App as 애플리케이션
    participant FB as FluentBit
    participant Kafka as Kafka (선택)
    participant CH as ClickHouse
    participant S3 as S3 (Cold)

    App->>FB: 로그 생성
    FB->>Kafka: 버퍼링
    Kafka->>CH: Kafka Engine 수집
    CH->>CH: MergeTree 테이블 저장

    Note over CH: TTL 정책에 따라

    CH->>S3: Cold 데이터 이동
```

---

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

---

## 로그 수집 파이프라인

### 로그 테이블 스키마

```sql
-- 로그 테이블 생성
CREATE TABLE IF NOT EXISTS logs.application_logs ON CLUSTER logs
(
    timestamp DateTime64(3),
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

    -- JSON 원본 (선택)
    raw_json String CODEC(ZSTD(3)),

    INDEX idx_trace_id trace_id TYPE bloom_filter GRANULARITY 4,
    INDEX idx_message message TYPE tokenbf_v1(10240, 3, 0) GRANULARITY 4
)
ENGINE = ReplicatedMergeTree('/clickhouse/tables/{shard}/logs.application_logs', '{replica}')
PARTITION BY toYYYYMM(date)
ORDER BY (namespace, service, timestamp)
TTL date + INTERVAL 90 DAY
SETTINGS index_granularity = 8192;

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

---

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

---

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

---

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

---

## 퀴즈

이 장에서 배운 내용을 테스트하려면 [ClickHouse 퀴즈](../../quizzes/observability/logging/04-clickhouse-quiz.md)를 풀어보세요.
